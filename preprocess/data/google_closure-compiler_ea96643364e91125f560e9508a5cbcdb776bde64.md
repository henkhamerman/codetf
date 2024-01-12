Refactoring Types: ['Extract Method']
mp/CodeGenerator.java
/*
 * Copyright 2004 The Closure Compiler Authors.
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

import static java.nio.charset.StandardCharsets.US_ASCII;

import com.google.common.base.Preconditions;
import com.google.javascript.jscomp.CompilerOptions.LanguageMode;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.Token;
import com.google.javascript.rhino.TokenStream;

import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.charset.CharsetEncoder;
import java.util.HashMap;
import java.util.Map;

/**
 * CodeGenerator generates codes from a parse tree, sending it to the specified
 * CodeConsumer.
 *
 */
class CodeGenerator {
  private static final String LT_ESCAPED = "\\x3c";
  private static final String GT_ESCAPED = "\\x3e";

  // A memoizer for formatting strings as JS strings.
  private final Map<String, String> escapedJsStrings = new HashMap<>();

  private static final char[] HEX_CHARS
      = { '0', '1', '2', '3', '4', '5', '6', '7',
          '8', '9', 'a', 'b', 'c', 'd', 'e', 'f' };

  private final CodeConsumer cc;

  private final CharsetEncoder outputCharsetEncoder;

  private final boolean preferSingleQuotes;
  private final boolean preserveTypeAnnotations;
  private final boolean trustedStrings;
  private final LanguageMode languageMode;

  private CodeGenerator(CodeConsumer consumer) {
    cc = consumer;
    outputCharsetEncoder = null;
    preferSingleQuotes = false;
    trustedStrings = true;
    languageMode = LanguageMode.ECMASCRIPT5;
    preserveTypeAnnotations = false;
  }

  static CodeGenerator forCostEstimation(CodeConsumer consumer) {
    return new CodeGenerator(consumer);
  }

  CodeGenerator(
      CodeConsumer consumer,
      CompilerOptions options) {
    cc = consumer;

    Charset outputCharset = options.getOutputCharset();
    if (outputCharset == null || outputCharset == US_ASCII) {
      // If we want our default (pretending to be UTF-8, but escaping anything
      // outside of straight ASCII), then don't use the encoder, but
      // just special-case the code.  This keeps the normal path through
      // the code identical to how it's been for years.
      this.outputCharsetEncoder = null;
    } else {
      this.outputCharsetEncoder = outputCharset.newEncoder();
    }
    this.preferSingleQuotes = options.preferSingleQuotes;
    this.trustedStrings = options.trustedStrings;
    this.languageMode = options.getLanguageOut();
    this.preserveTypeAnnotations = options.preserveTypeAnnotations;
  }

  /**
   * Insert a ECMASCRIPT 5 strict annotation.
   */
  public void tagAsStrict() {
    add("'use strict';");
  }

  void add(String str) {
    cc.add(str);
  }

  private void addIdentifier(String identifier) {
    cc.addIdentifier(identifierEscape(identifier));
  }

  void add(Node n) {
    add(n, Context.OTHER);
  }

  void add(Node n, Context context) {
    if (!cc.continueProcessing()) {
      return;
    }

    if (preserveTypeAnnotations && n.getJSDocInfo() != null) {
      add(JSDocInfoPrinter.print(n.getJSDocInfo()));
    }

    int type = n.getType();
    String opstr = NodeUtil.opToStr(type);
    int childCount = n.getChildCount();
    Node first = n.getFirstChild();
    Node last = n.getLastChild();

    // Handle all binary operators
    if (opstr != null && first != last) {
      Preconditions.checkState(
          childCount == 2,
          "Bad binary operator \"%s\": expected 2 arguments but got %s",
          opstr, childCount);
      int p = NodeUtil.precedence(type);

      // For right-hand-side of operations, only pass context if it's
      // the IN_FOR_INIT_CLAUSE one.
      Context rhsContext = getContextForNoInOperator(context);

      if (NodeUtil.isAssignmentOp(n) && NodeUtil.isAssignmentOp(last)) {
        // Assignments are the only right-associative binary operators
        addExpr(first, p, context);
        cc.addOp(opstr, true);
        addExpr(last, p, rhsContext);
      } else {
        unrollBinaryOperator(n, type, opstr, context, rhsContext, p, p + 1);
      }
      return;
    }

    cc.startSourceMapping(n);

    switch (type) {
      case Token.TRY:
        {
          Preconditions.checkState(
              first.getNext().isBlock() && !first.getNext().hasMoreThanOneChild());
          Preconditions.checkState(childCount >= 2 && childCount <= 3);

          add("try");
          add(first, Context.PRESERVE_BLOCK);

          // second child contains the catch block, or nothing if there
          // isn't a catch block
          Node catchblock = first.getNext().getFirstChild();
          if (catchblock != null) {
            add(catchblock);
          }

          if (childCount == 3) {
            cc.maybeInsertSpace();
            add("finally");
            add(last, Context.PRESERVE_BLOCK);
          }
          break;
        }

      case Token.CATCH:
        Preconditions.checkState(childCount == 2);
        cc.maybeInsertSpace();
        add("catch");
        cc.maybeInsertSpace();
        add("(");
        add(first);
        add(")");
        add(last, Context.PRESERVE_BLOCK);
        break;

      case Token.THROW:
        Preconditions.checkState(childCount == 1);
        add("throw");
        cc.maybeInsertSpace();
        add(first);

        // Must have a ';' after a throw statement, otherwise safari can't
        // parse this.
        cc.endStatement(true);
        break;

      case Token.RETURN:
        add("return");
        if (childCount == 1) {
          cc.maybeInsertSpace();
          add(first);
        } else {
          Preconditions.checkState(childCount == 0);
        }
        cc.endStatement();
        break;

      case Token.VAR:
        if (first != null) {
          add("var ");
          addList(first, false, getContextForNoInOperator(context), ",");
        }
        break;

      case Token.CONST:
        add("const ");
        addList(first, false, getContextForNoInOperator(context), ",");
        break;

      case Token.LET:
        add("let ");
        addList(first, false, getContextForNoInOperator(context), ",");
        break;

      case Token.LABEL_NAME:
        Preconditions.checkState(!n.getString().isEmpty());
        addIdentifier(n.getString());
        break;

      case Token.NAME:
        addIdentifier(n.getString());
        maybeAddTypeDecl(n);

        if (first != null && !first.isEmpty()) {
          Preconditions.checkState(childCount == 1);
          cc.addOp("=", true);
          if (first.isComma()) {
            addExpr(first, NodeUtil.precedence(Token.ASSIGN), Context.OTHER);
          } else {
            // Add expression, consider nearby code at lowest level of
            // precedence.
            addExpr(first, 0, getContextForNoInOperator(context));
          }
        }
        break;

      case Token.ARRAYLIT:
        add("[");
        addArrayList(first);
        add("]");
        break;

      case Token.ARRAY_PATTERN:
        addArrayPattern(n);
        break;

      case Token.PARAM_LIST:
        add("(");
        addList(first);
        add(")");
        break;

      case Token.DEFAULT_VALUE:
        add(first);
        maybeAddTypeDecl(n);
        cc.addOp("=", true);
        add(first.getNext());
        break;

      case Token.COMMA:
        Preconditions.checkState(childCount == 2);
        unrollBinaryOperator(
            n, Token.COMMA, ",", context, getContextForNoInOperator(context), 0, 0);
        break;

      case Token.NUMBER:
        Preconditions.checkState(childCount == 0);
        cc.addNumber(n.getDouble());
        break;

      case Token.TYPEOF:
      case Token.VOID:
      case Token.NOT:
      case Token.BITNOT:
      case Token.POS:
        {
          // All of these unary operators are right-associative
          Preconditions.checkState(childCount == 1);
          cc.addOp(NodeUtil.opToStrNoFail(type), false);
          addExpr(first, NodeUtil.precedence(type), Context.OTHER);
          break;
        }

      case Token.NEG:
        {
          Preconditions.checkState(childCount == 1);

          // It's important to our sanity checker that the code
          // we print produces the same AST as the code we parse back.
          // NEG is a weird case because Rhino parses "- -2" as "2".
          if (n.getFirstChild().isNumber()) {
            cc.addNumber(-n.getFirstChild().getDouble());
          } else {
            cc.addOp(NodeUtil.opToStrNoFail(type), false);
            addExpr(first, NodeUtil.precedence(type), Context.OTHER);
          }

          break;
        }

      case Token.HOOK:
        {
          Preconditions.checkState(childCount == 3);
          int p = NodeUtil.precedence(type);
          Context rhsContext = getContextForNoInOperator(context);
          addExpr(first, p + 1, context);
          cc.addOp("?", true);
          addExpr(first.getNext(), 1, rhsContext);
          cc.addOp(":", true);
          addExpr(last, 1, rhsContext);
          break;
        }

      case Token.REGEXP:
        if (!first.isString() || !last.isString()) {
          throw new Error("Expected children to be strings");
        }

        String regexp = regexpEscape(first.getString(), outputCharsetEncoder);

        // I only use one .add because whitespace matters
        if (childCount == 2) {
          add(regexp + last.getString());
        } else {
          Preconditions.checkState(childCount == 1);
          add(regexp);
        }
        break;

      case Token.FUNCTION:
        if (n.getClass() != Node.class) {
          throw new Error("Unexpected Node subclass.");
        }
        Preconditions.checkState(childCount == 3);

        boolean isArrow = n.isArrowFunction();
        // Arrow functions are complete expressions, so don't need parentheses
        // if they are in an expression result.
        boolean notSingleExpr = n.getParent() == null || !n.getParent().isExprResult();
        boolean funcNeedsParens = (context == Context.START_OF_EXPR) && (!isArrow || notSingleExpr);
        if (funcNeedsParens) {
          add("(");
        }

        if (!isArrow) {
          add("function");
        }
        if (n.isGeneratorFunction()) {
          add("*");
        }

        add(first);

        add(first.getNext()); // param list

        maybeAddTypeDecl(n);
        if (isArrow) {
          cc.addOp("=>", true);
        }
        add(last, Context.PRESERVE_BLOCK);
        cc.endFunction(context == Context.STATEMENT);

        if (funcNeedsParens) {
          add(")");
        }
        break;

      case Token.REST:
        add("...");
        add(n.getString());
        maybeAddTypeDecl(n);
        break;

      case Token.SPREAD:
        add("...");
        add(n.getFirstChild());
        break;

      case Token.EXPORT:
        add("export");
        if (n.getBooleanProp(Node.EXPORT_DEFAULT)) {
          add("default");
        }
        if (n.getBooleanProp(Node.EXPORT_ALL_FROM)) {
          add("*");
          Preconditions.checkState(first != null && first.isEmpty());
        } else {
          add(first);
        }
        if (childCount == 2) {
          add("from");
          add(last);
        }
        cc.endStatement();
        break;

      case Token.MODULE:
        add("module");
        add(first);
        add("from");
        add(last);
        cc.endStatement();
        break;

      case Token.IMPORT:
        add("import");

        Node second = first.getNext();
        if (!first.isEmpty()) {
          add(first);
          if (!second.isEmpty()) {
            cc.listSeparator();
          }
        }
        if (!second.isEmpty()) {
          add(second);
        }
        if (!first.isEmpty() || !second.isEmpty()) {
          add("from");
        }
        add(last);
        cc.endStatement();
        break;

      case Token.EXPORT_SPECS:
      case Token.IMPORT_SPECS:
        add("{");
        for (Node c = first; c != null; c = c.getNext()) {
          if (c != first) {
            cc.listSeparator();
          }
          add(c);
        }
        add("}");
        break;

      case Token.EXPORT_SPEC:
      case Token.IMPORT_SPEC:
        add(first);
        if (first != last) {
          add("as");
          add(last);
        }
        break;

      case Token.IMPORT_STAR:
        add("*");
        add("as");
        add(n.getString());
        break;

        // CLASS -> NAME,EXPR|EMPTY,BLOCK
      case Token.CLASS:
        {
          Preconditions.checkState(childCount == 3);
          boolean classNeedsParens = (context == Context.START_OF_EXPR);
          if (classNeedsParens) {
            add("(");
          }

          Node name = first;
          Node superClass = first.getNext();
          Node members = last;

          add("class");
          if (!name.isEmpty()) {
            add(name);
          }
          if (!superClass.isEmpty()) {
            add("extends");
            add(superClass);
          }
          add(members);
          cc.endClass(context == Context.STATEMENT);

          if (classNeedsParens) {
            add(")");
          }
        }
        break;

      case Token.CLASS_MEMBERS:
      case Token.INTERFACE_MEMBERS:
        cc.beginBlock();
        for (Node c = first; c != null; c = c.getNext()) {
          add(c);
          cc.endLine();
        }
        cc.endBlock(false);
        break;
      case Token.ENUM_MEMBERS:
        cc.beginBlock();
        for (Node c = first; c != null; c = c.getNext()) {
          add(c);
          if (c.getNext() != null) {
            add(",");
          }
          cc.endLine();
        }
        cc.endBlock(false);
        break;
      case Token.GETTER_DEF:
      case Token.SETTER_DEF:
      case Token.MEMBER_FUNCTION_DEF:
      case Token.MEMBER_VARIABLE_DEF:
        {
          n.getParent().toStringTree();
          Preconditions.checkState(
              n.getParent().isObjectLit()
                  || n.getParent().isClassMembers()
                  || n.getParent().isInterfaceMembers());

          if (n.isStaticMember()) {
            add("static ");
          }

          if (!n.isMemberVariableDef() && n.getFirstChild().isGeneratorFunction()) {
            Preconditions.checkState(type == Token.MEMBER_FUNCTION_DEF);
            add("*");
          }

          switch (type) {
            case Token.GETTER_DEF:
              // Get methods have no parameters.
              Preconditions.checkState(!first.getChildAtIndex(1).hasChildren());
              add("get ");
              break;
            case Token.SETTER_DEF:
              // Set methods have one parameter.
              Preconditions.checkState(first.getChildAtIndex(1).hasOneChild());
              add("set ");
              break;
            case Token.MEMBER_FUNCTION_DEF:
            case Token.MEMBER_VARIABLE_DEF:
              // nothing to do.
              break;
          }

          // The name is on the GET or SET node.
          String name = n.getString();
          if (n.isMemberVariableDef()) {
            add(n.getString());
            maybeAddTypeDecl(n);
            add(";");
          } else {
            Preconditions.checkState(childCount == 1);
            Preconditions.checkState(first.isFunction());

            // The function referenced by the definition should always be unnamed.
            Preconditions.checkState(first.getFirstChild().getString().isEmpty());

            Node fn = first;
            Node parameters = fn.getChildAtIndex(1);
            Node body = fn.getLastChild();

            // Add the property name.
            if (!n.isQuotedString()
                && TokenStream.isJSIdentifier(name)
                &&
                // do not encode literally any non-literal characters that were
                // Unicode escaped.
                NodeUtil.isLatin(name)) {
              add(name);
            } else {
              // Determine if the string is a simple number.
              double d = getSimpleNumber(name);
              if (!Double.isNaN(d)) {
                cc.addNumber(d);
              } else {
                addJsString(n);
              }
            }
            add(parameters);
            maybeAddTypeDecl(fn);
            add(body, Context.PRESERVE_BLOCK);
          }
          break;
        }

      case Token.SCRIPT:
      case Token.BLOCK:
        {
          if (n.getClass() != Node.class) {
            throw new Error("Unexpected Node subclass.");
          }
          boolean preserveBlock = context == Context.PRESERVE_BLOCK;
          if (preserveBlock) {
            cc.beginBlock();
          }

          boolean preferLineBreaks =
              type == Token.SCRIPT
                  || (type == Token.BLOCK
                      && !preserveBlock
                      && n.getParent() != null
                      && n.getParent().isScript());
          for (Node c = first; c != null; c = c.getNext()) {
            add(c, Context.STATEMENT);

            // VAR doesn't include ';' since it gets used in expressions
            if (NodeUtil.isNameDeclaration(c)) {
              cc.endStatement();
            }

            if (c.isFunction() || c.isClass()) {
              cc.maybeLineBreak();
            }

            // Prefer to break lines in between top-level statements
            // because top-level statements are more homogeneous.
            if (preferLineBreaks) {
              cc.notePreferredLineBreak();
            }
          }
          if (preserveBlock) {
            cc.endBlock(cc.breakAfterBlockFor(n, context == Context.STATEMENT));
          }
          break;
        }

      case Token.FOR:
        if (childCount == 4) {
          add("for");
          cc.maybeInsertSpace();
          add("(");
          if (NodeUtil.isNameDeclaration(first)) {
            add(first, Context.IN_FOR_INIT_CLAUSE);
          } else {
            addExpr(first, 0, Context.IN_FOR_INIT_CLAUSE);
          }
          add(";");
          add(first.getNext());
          add(";");
          add(first.getNext().getNext());
          add(")");
          addNonEmptyStatement(last, getContextForNonEmptyExpression(context), false);
        } else {
          Preconditions.checkState(childCount == 3);
          add("for");
          cc.maybeInsertSpace();
          add("(");
          add(first);
          add("in");
          add(first.getNext());
          add(")");
          addNonEmptyStatement(last, getContextForNonEmptyExpression(context), false);
        }
        break;

      case Token.FOR_OF:
        // A "for-of" inside an array comprehension only has two children.
        Preconditions.checkState(childCount == 3);
        add("for");
        cc.maybeInsertSpace();
        add("(");
        add(first);
        add("of");
        add(first.getNext());
        add(")");
        addNonEmptyStatement(last, getContextForNonEmptyExpression(context), false);
        break;

      case Token.DO:
        Preconditions.checkState(childCount == 2);
        add("do");
        addNonEmptyStatement(first, Context.OTHER, false);
        cc.maybeInsertSpace();
        add("while");
        cc.maybeInsertSpace();
        add("(");
        add(last);
        add(")");
        cc.endStatement();
        break;

      case Token.WHILE:
        Preconditions.checkState(childCount == 2);
        add("while");
        cc.maybeInsertSpace();
        add("(");
        add(first);
        add(")");
        addNonEmptyStatement(last, getContextForNonEmptyExpression(context), false);
        break;

      case Token.EMPTY:
        Preconditions.checkState(childCount == 0);
        break;

      case Token.GETPROP:
        {
          Preconditions.checkState(
              childCount == 2, "Bad GETPROP: expected 2 children, but got %s", childCount);
          Preconditions.checkState(last.isString(), "Bad GETPROP: RHS should be STRING");
          boolean needsParens = (first.isNumber());
          if (needsParens) {
            add("(");
          }
          addExpr(first, NodeUtil.precedence(type), context);
          if (needsParens) {
            add(")");
          }
          if (this.languageMode == LanguageMode.ECMASCRIPT3
              && TokenStream.isKeyword(last.getString())) {
            // Check for ECMASCRIPT3 keywords.
            add("[");
            add(last);
            add("]");
          } else {
            add(".");
            addIdentifier(last.getString());
          }
          break;
        }

      case Token.GETELEM:
        Preconditions.checkState(
            childCount == 2, "Bad GETELEM: expected 2 children but got %s", childCount);
        addExpr(first, NodeUtil.precedence(type), context);
        add("[");
        add(first.getNext());
        add("]");
        break;

      case Token.WITH:
        Preconditions.checkState(childCount == 2);
        add("with(");
        add(first);
        add(")");
        addNonEmptyStatement(last, getContextForNonEmptyExpression(context), false);
        break;

      case Token.INC:
      case Token.DEC:
        {
          Preconditions.checkState(childCount == 1);
          String o = type == Token.INC ? "++" : "--";
          boolean postProp = n.getBooleanProp(Node.INCRDECR_PROP);
          if (postProp) {
            addExpr(first, NodeUtil.precedence(type), context);
            cc.addOp(o, false);
          } else {
            cc.addOp(o, false);
            add(first);
          }
          break;
        }

      case Token.CALL:
        // We have two special cases here:
        // 1) If the left hand side of the call is a direct reference to eval,
        // then it must have a DIRECT_EVAL annotation. If it does not, then
        // that means it was originally an indirect call to eval, and that
        // indirectness must be preserved.
        // 2) If the left hand side of the call is a property reference,
        // then the call must not a FREE_CALL annotation. If it does, then
        // that means it was originally an call without an explicit this and
        // that must be preserved.
        if (isIndirectEval(first) || n.getBooleanProp(Node.FREE_CALL) && NodeUtil.isGet(first)) {
          add("(0,");
          addExpr(first, NodeUtil.precedence(Token.COMMA), Context.OTHER);
          add(")");
        } else {
          addExpr(first, NodeUtil.precedence(type), context);
        }
        Node args = first.getNext();
        add("(");
        addList(args);
        add(")");
        break;

      case Token.IF:
        boolean hasElse = childCount == 3;
        boolean ambiguousElseClause = context == Context.BEFORE_DANGLING_ELSE && !hasElse;
        if (ambiguousElseClause) {
          cc.beginBlock();
        }

        add("if");
        cc.maybeInsertSpace();
        add("(");
        add(first);
        add(")");

        // An "if" node inside an array comprehension only has one child.
        if (childCount == 1) {
          break;
        }

        if (hasElse) {
          addNonEmptyStatement(first.getNext(), Context.BEFORE_DANGLING_ELSE, false);
          cc.maybeInsertSpace();
          add("else");
          addNonEmptyStatement(last, getContextForNonEmptyExpression(context), false);
        } else {
          addNonEmptyStatement(first.getNext(), Context.OTHER, false);
          Preconditions.checkState(childCount == 2);
        }

        if (ambiguousElseClause) {
          cc.endBlock();
        }
        break;

      case Token.NULL:
        Preconditions.checkState(childCount == 0);
        cc.addConstant("null");
        break;

      case Token.THIS:
        Preconditions.checkState(childCount == 0);
        add("this");
        break;

      case Token.SUPER:
        Preconditions.checkState(childCount == 0);
        add("super");
        break;

      case Token.YIELD:
        Preconditions.checkState(childCount == 1);
        add("yield");
        cc.maybeInsertSpace();
        if (n.isYieldFor()) {
          add("*");
        }
        addExpr(first, NodeUtil.precedence(type), Context.OTHER);
        break;

      case Token.FALSE:
        Preconditions.checkState(childCount == 0);
        cc.addConstant("false");
        break;

      case Token.TRUE:
        Preconditions.checkState(childCount == 0);
        cc.addConstant("true");
        break;

      case Token.CONTINUE:
        Preconditions.checkState(childCount <= 1);
        add("continue");
        if (childCount == 1) {
          if (!first.isLabelName()) {
            throw new Error("Unexpected token type. Should be LABEL_NAME.");
          }
          add(" ");
          add(first);
        }
        cc.endStatement();
        break;

      case Token.DEBUGGER:
        Preconditions.checkState(childCount == 0);
        add("debugger");
        cc.endStatement();
        break;

      case Token.BREAK:
        Preconditions.checkState(childCount <= 1);
        add("break");
        if (childCount == 1) {
          if (!first.isLabelName()) {
            throw new Error("Unexpected token type. Should be LABEL_NAME.");
          }
          add(" ");
          add(first);
        }
        cc.endStatement();
        break;

      case Token.EXPR_RESULT:
        Preconditions.checkState(childCount == 1);
        add(first, Context.START_OF_EXPR);
        cc.endStatement();
        break;

      case Token.NEW:
        add("new ");
        int precedence = NodeUtil.precedence(type);

        // If the first child contains a CALL, then claim higher precedence
        // to force parentheses. Otherwise, when parsed, NEW will bind to the
        // first viable parentheses (don't traverse into functions).
        if (NodeUtil.containsType(first, Token.CALL, NodeUtil.MATCH_NOT_FUNCTION)) {
          precedence = NodeUtil.precedence(first.getType()) + 1;
        }
        addExpr(first, precedence, Context.OTHER);

        // '()' is optional when no arguments are present
        Node next = first.getNext();
        if (next != null) {
          add("(");
          addList(next);
          add(")");
        }
        break;

      case Token.STRING_KEY:
        addStringKey(n);
        break;

      case Token.STRING:
        Preconditions.checkState(childCount == 0, "A string may not have children");
        // The string is already processed, don't escape it.
        if (n.getBooleanProp(Node.COOKED_STRING)) {
          add("\"" + n.getString() + "\"");
        } else {
          addJsString(n);
        }
        break;

      case Token.DELPROP:
        Preconditions.checkState(childCount == 1);
        add("delete ");
        add(first);
        break;

      case Token.OBJECTLIT:
        {
          boolean needsParens = (context == Context.START_OF_EXPR);
          if (needsParens) {
            add("(");
          }
          add("{");
          for (Node c = first; c != null; c = c.getNext()) {
            if (c != first) {
              cc.listSeparator();
            }

            Preconditions.checkState(
                c.isComputedProp()
                    || c.isGetterDef()
                    || c.isSetterDef()
                    || c.isStringKey()
                    || c.isMemberFunctionDef());
            add(c);
          }
          add("}");
          if (needsParens) {
            add(")");
          }
          break;
        }

      case Token.COMPUTED_PROP:
        if (n.getBooleanProp(Node.COMPUTED_PROP_GETTER)) {
          add("get ");
        } else if (n.getBooleanProp(Node.COMPUTED_PROP_SETTER)) {
          add("set ");
        } else if (last.getBooleanProp(Node.GENERATOR_FN)) {
          add("*");
        }
        add("[");
        add(first);
        add("]");
        // TODO(martinprobst): There's currently no syntax for properties in object literals that
        // have type declarations on them (a la `{foo: number: 12}`). This comes up for, e.g.,
        // function parameters with default values. Support when figured out.
        maybeAddTypeDecl(n);
        if (n.getBooleanProp(Node.COMPUTED_PROP_METHOD)
            || n.getBooleanProp(Node.COMPUTED_PROP_GETTER)
            || n.getBooleanProp(Node.COMPUTED_PROP_SETTER)) {
          Node function = first.getNext();
          Node params = function.getFirstChild().getNext();
          Node body = function.getLastChild();

          add(params);
          add(body, Context.PRESERVE_BLOCK);
        } else {
          // This is a field or object literal property.
          boolean isInClass = n.getParent().getType() == Token.CLASS_MEMBERS;
          Node initializer = first.getNext();
          if (initializer != null) {
            // Object literal value.
            Preconditions.checkState(
                !isInClass, "initializers should only exist in object literals, not classes");
            cc.addOp(":", false);
            add(initializer);
          } else {
            // Computed properties must either have an initializer or be computed member-variable
            // properties that exist for their type declaration.
            Preconditions.checkState(n.getBooleanProp(Node.COMPUTED_PROP_VARIABLE));
          }
          if (isInClass) {
            add(";");
          }
        }
        break;

      case Token.OBJECT_PATTERN:
        addObjectPattern(n, context);
        break;

      case Token.SWITCH:
        add("switch(");
        add(first);
        add(")");
        cc.beginBlock();
        addAllSiblings(first.getNext());
        cc.endBlock(context == Context.STATEMENT);
        break;

      case Token.CASE:
        Preconditions.checkState(childCount == 2);
        add("case ");
        add(first);
        addCaseBody(last);
        break;

      case Token.DEFAULT_CASE:
        Preconditions.checkState(childCount == 1);
        add("default");
        addCaseBody(first);
        break;

      case Token.LABEL:
        Preconditions.checkState(childCount == 2);
        if (!first.isLabelName()) {
          throw new Error("Unexpected token type. Should be LABEL_NAME.");
        }
        add(first);
        add(":");
        if (!last.isBlock()) {
          cc.maybeInsertSpace();
        }
        addNonEmptyStatement(last, getContextForNonEmptyExpression(context), true);
        break;

      case Token.CAST:
        add("(");
        add(first);
        add(")");
        break;

      case Token.TEMPLATELIT:
        if (!first.isString()) {
          add(first, Context.START_OF_EXPR);
          first = first.getNext();
        }
        add("`");
        for (Node c = first; c != null; c = c.getNext()) {
          if (c.isString()) {
            add(c.getString());
          } else {
            // Can't use add() since isWordChar('$') == true and cc would add
            // an extra space.
            cc.append("${");
            add(c.getFirstChild(), Context.START_OF_EXPR);
            add("}");
          }
        }
        add("`");
        break;

        // Type Declaration ASTs.
      case Token.STRING_TYPE:
        add("string");
        break;
      case Token.BOOLEAN_TYPE:
        add("boolean");
        break;
      case Token.NUMBER_TYPE:
        add("number");
        break;
      case Token.ANY_TYPE:
        add("any");
        break;
      case Token.VOID_TYPE:
        add("void");
        break;
      case Token.NAMED_TYPE:
        // Children are a chain of getprop nodes.
        add(first);
        break;
      case Token.ARRAY_TYPE:
        addExpr(first, NodeUtil.precedence(Token.ARRAY_TYPE), context);
        add("[]");
        break;
      case Token.FUNCTION_TYPE:
        Node returnType = first;
        add("(");
        addList(first.getNext());
        add(")");
        cc.addOp("=>", true);
        add(returnType);
        break;
      case Token.OPTIONAL_PARAMETER:
        // The '?' token was printed in #maybeAddTypeDecl because it
        // must come before the colon
        add(first);
        break;
      case Token.REST_PARAMETER_TYPE:
        add("...");
        add(first);
        break;
      case Token.UNION_TYPE:
        addList(first, "|");
        break;
      case Token.RECORD_TYPE:
        add("{");
        addList(first, false, Context.STATEMENT, ";");
        add("}");
        break;
      case Token.PARAMETERIZED_TYPE:
        // First child is the type that's parameterized, later children are the arguments.
        add(first);
        add("<");
        addList(first.getNext());
        add(">");
        break;
        // CLASS -> NAME,EXPR|EMPTY,BLOCK
      case Token.INTERFACE:
        {
          Preconditions.checkState(childCount == 3);
          Node name = first;
          Node superTypes = first.getNext();
          Node members = last;

          add("interface");
          add(name);
          if (!superTypes.isEmpty()) {
            add("extends");
            for (Node child = superTypes.getFirstChild(); child != null; child = child.getNext()) {
              if (child != n.getFirstChild()) {
                add(",");
              }
              add(child);
            }
          }
          add(members);
        }
        break;
      case Token.ENUM:
        {
          Preconditions.checkState(childCount == 2);
          Node name = first;
          Node members = last;
          add("enum");
          add(name);
          add(members);
          break;
        }
      default:
        throw new RuntimeException("Unknown type " + Token.name(type) + "\n" + n.toStringTree());
    }

    cc.endSourceMapping(n);
  }

  private void maybeAddTypeDecl(Node n) {
    if (n.getDeclaredTypeExpression() != null) {
      if (n.getDeclaredTypeExpression().getType() == Token.OPTIONAL_PARAMETER) {
        add("?");
      }
      add(":");
      cc.maybeInsertSpace();
      add(n.getDeclaredTypeExpression());
    }
  }

  /**
   * We could use addList recursively here, but sometimes we produce
   * very deeply nested operators and run out of stack space, so we
   * just unroll the recursion when possible.
   *
   * We assume nodes are left-recursive.
   */
  private void unrollBinaryOperator(
      Node n, int op, String opStr, Context context,
      Context rhsContext, int leftPrecedence, int rightPrecedence) {
    Node firstNonOperator = n.getFirstChild();
    while (firstNonOperator.getType() == op) {
      firstNonOperator = firstNonOperator.getFirstChild();
    }

    addExpr(firstNonOperator, leftPrecedence, context);

    Node current = firstNonOperator;
    do {
      current = current.getParent();
      cc.addOp(opStr, true);
      addExpr(current.getFirstChild().getNext(), rightPrecedence, rhsContext);
    } while (current != n);
  }

  static boolean isSimpleNumber(String s) {
    int len = s.length();
    if (len == 0) {
      return false;
    }
    for (int index = 0; index < len; index++) {
      char c = s.charAt(index);
      if (c < '0' || c > '9') {
        return false;
      }
    }
    return len == 1 || s.charAt(0) != '0';
  }

  static double getSimpleNumber(String s) {
    if (isSimpleNumber(s)) {
      try {
        long l = Long.parseLong(s);
        if (l < NodeUtil.MAX_POSITIVE_INTEGER_NUMBER) {
          return l;
        }
      } catch (NumberFormatException e) {
        // The number was too long to parse. Fall through to NaN.
      }
    }
    return Double.NaN;
  }

  /**
   * @return Whether the name is an indirect eval.
   */
  private static boolean isIndirectEval(Node n) {
    return n.isName() && "eval".equals(n.getString()) &&
        !n.getBooleanProp(Node.DIRECT_EVAL);
  }

  /**
   * Adds a block or expression, substituting a VOID with an empty statement.
   * This is used for "for (...);" and "if (...);" type statements.
   *
   * @param n The node to print.
   * @param context The context to determine how the node should be printed.
   */
  private void addNonEmptyStatement(
      Node n, Context context, boolean allowNonBlockChild) {
    Node nodeToProcess = n;

    if (!allowNonBlockChild && !n.isBlock()) {
      throw new Error("Missing BLOCK child.");
    }

    // Strip unneeded blocks, that is blocks with <2 children unless
    // the CodePrinter specifically wants to keep them.
    if (n.isBlock()) {
      int count = getNonEmptyChildCount(n, 2);
      if (count == 0) {
        if (cc.shouldPreserveExtraBlocks()) {
          cc.beginBlock();
          cc.endBlock(cc.breakAfterBlockFor(n, context == Context.STATEMENT));
        } else {
          cc.endStatement(true);
        }
        return;
      }

      if (count == 1) {
        // Hack around a couple of browser bugs:
        //   Safari needs a block around function declarations.
        //   IE6/7 needs a block around DOs.
        Node firstAndOnlyChild = getFirstNonEmptyChild(n);
        boolean alwaysWrapInBlock = cc.shouldPreserveExtraBlocks();
        if (alwaysWrapInBlock || isBlockDeclOrDo(firstAndOnlyChild)) {
          cc.beginBlock();
          add(firstAndOnlyChild, Context.STATEMENT);
          cc.maybeLineBreak();
          cc.endBlock(cc.breakAfterBlockFor(n, context == Context.STATEMENT));
          return;
        } else {
          // Continue with the only child.
          nodeToProcess = firstAndOnlyChild;
        }
      }

      if (count > 1) {
        context = Context.PRESERVE_BLOCK;
      }
    }

    if (nodeToProcess.isEmpty()) {
      cc.endStatement(true);
    } else {
      add(nodeToProcess, context);

      // VAR doesn't include ';' since it gets used in expressions - so any
      // VAR in a statement context needs a call to endStatement() here.
      if (nodeToProcess.isVar()) {
        cc.endStatement();
      }
    }
  }

  /**
   * @return Whether the Node is a DO or a declaration that is only allowed
   * in restricted contexts.
   */
  private static boolean isBlockDeclOrDo(Node n) {
    if (n.isLabel()) {
      Node labeledStatement = n.getLastChild();
      if (!labeledStatement.isBlock()) {
        return isBlockDeclOrDo(labeledStatement);
      } else {
        // For labels with block children, we need to ensure that a
        // labeled FUNCTION or DO isn't generated when extraneous BLOCKs
        // are skipped.
        if (getNonEmptyChildCount(n, 2) == 1) {
          return isBlockDeclOrDo(getFirstNonEmptyChild(n));
        } else {
          // Either a empty statement or an block with more than one child,
          // way it isn't a FUNCTION or DO.
          return false;
        }
      }
    } else {
      switch (n.getType()){
        case Token.LET:
        case Token.CONST:
        case Token.FUNCTION:
        case Token.CLASS:
        case Token.DO:
          return true;
        default:
          return false;
      }
    }
  }

  private void addExpr(Node n, int minPrecedence, Context context) {
    if ((NodeUtil.precedence(n.getType()) < minPrecedence) ||
        ((context == Context.IN_FOR_INIT_CLAUSE) && n.isIn())){
      add("(");
      add(n, Context.OTHER);
      add(")");
    } else {
      add(n, context);
    }
  }

  void addList(Node firstInList) {
    addList(firstInList, true, Context.OTHER, ",");
  }

  void addList(Node firstInList, String separator) {
    addList(firstInList, true, Context.OTHER, separator);
  }

  void addList(Node firstInList, boolean isArrayOrFunctionArgument,
      Context lhsContext, String separator) {
    for (Node n = firstInList; n != null; n = n.getNext()) {
      boolean isFirst = n == firstInList;
      if (isFirst) {
        addExpr(n, isArrayOrFunctionArgument ? 1 : 0, lhsContext);
      } else {
        cc.addOp(separator, true);
        addExpr(n, isArrayOrFunctionArgument ? 1 : 0,
            getContextForNoInOperator(lhsContext));
      }
    }
  }

  void addStringKey(Node n) {
    String key = n.getString();
    // Object literal property names don't have to be quoted if they
    // are not JavaScript keywords
    if (!n.isQuotedString()
        && !(languageMode == LanguageMode.ECMASCRIPT3
            && TokenStream.isKeyword(key))
        && TokenStream.isJSIdentifier(key)
        // do not encode literally any non-literal characters that
        // were Unicode escaped.
        && NodeUtil.isLatin(key)) {
      add(key);
    } else {
      // Determine if the string is a simple number.
      double d = getSimpleNumber(key);
      if (!Double.isNaN(d)) {
        cc.addNumber(d);
      } else {
        addJsString(n);
      }
    }
    if (n.hasChildren()) {
      add(":");
      addExpr(n.getFirstChild(), 1, Context.OTHER);
    }
  }

  /**
   * Determines whether the given child of a destructuring pattern is the initializer for
   * that pattern. If the pattern is in a var/let/const statement, then the last child of the
   * pattern is the initializer, e.g. the tree for
   * {@code var {x:y} = z} looks like:
   * <pre>
   * VAR
   *   OBJECT_PATTERN
   *     STRING_KEY x
   *       NAME y
   *     NAME z
   * </pre>
   * The exception is when the var/let/const is the first child of a for-in or for-of loop, in
   * which case all the children belong to the pattern itself, e.g. the VAR node in
   * {@code for (var {x: y, z} of []);} looks like
   * <pre>
   * VAR
   *   OBJECT_PATTERN
   *     STRING_KEY x
   *       NAME y
   *     STRING_KEY z
   * </pre>
   * and the "z" node is *not* an initializer.
   */
  private boolean isPatternInitializer(Node n) {
    Node parent = n.getParent();
    Preconditions.checkState(parent.isDestructuringPattern());
    if (n != parent.getLastChild()) {
      return false;
    }
    Node decl = parent.getParent();

    if (!NodeUtil.isNameDeclaration(decl)) {
      return false;
    }
    if (NodeUtil.isEnhancedFor(decl.getParent()) && decl == decl.getParent().getFirstChild()) {
      return false;
    }
    return true;
  }

  void addArrayPattern(Node n) {
    boolean hasInitializer = false;
    add("[");
    for (Node child = n.getFirstChild(); child != null; child = child.getNext()) {
      if (isPatternInitializer(child)) {
        hasInitializer = true;
        add("]");
        add("=");
      } else if (child != n.getFirstChild()) {
        add(",");
      }

      add(child);
    }
    if (!hasInitializer) {
      add("]");
    }
  }

  void addObjectPattern(Node n, Context context) {
    boolean hasInitializer = false;
    boolean needsParens = (context == Context.START_OF_EXPR);
    if (needsParens) {
      add("(");
    }

    add("{");
    for (Node child = n.getFirstChild(); child != null; child = child.getNext()) {
      if (isPatternInitializer(child)) {
        hasInitializer = true;
        add("}");
        add("=");
      } else if (child != n.getFirstChild()) {
        add(",");
      }

      add(child);
    }
    if (!hasInitializer) {
      add("}");
    }

    if (needsParens) {
      add(")");
    }
  }

  /**
   * This function adds a comma-separated list as is specified by an ARRAYLIT
   * node with the associated skipIndexes array.  This is a space optimization
   * since we avoid creating a whole Node object for each empty array literal
   * slot.
   * @param firstInList The first in the node list (chained through the next
   * property).
   */
  void addArrayList(Node firstInList) {
    boolean lastWasEmpty = false;
    for (Node n = firstInList; n != null; n = n.getNext()) {
      if (n != firstInList) {
        cc.listSeparator();
      }
      addExpr(n, 1, Context.OTHER);
      lastWasEmpty = n.isEmpty();
    }

    if (lastWasEmpty) {
      cc.listSeparator();
    }
  }

  void addCaseBody(Node caseBody) {
    cc.beginCaseBody();
    add(caseBody);
    cc.endCaseBody();
  }

  void addAllSiblings(Node n) {
    for (Node c = n; c != null; c = c.getNext()) {
      add(c);
    }
  }

  /** Outputs a JS string, using the optimal (single/double) quote character */
  private void addJsString(Node n) {
    String s = n.getString();
    boolean useSlashV = n.getBooleanProp(Node.SLASH_V);
    if (useSlashV) {
      add(jsString(n.getString(), useSlashV));
    } else {
      String cached = escapedJsStrings.get(s);
      if (cached == null) {
        cached = jsString(n.getString(), useSlashV);
        escapedJsStrings.put(s, cached);
      }
      add(cached);
    }
  }

  private String jsString(String s, boolean useSlashV) {
    int singleq = 0, doubleq = 0;

    // could count the quotes and pick the optimal quote character
    for (int i = 0; i < s.length(); i++) {
      switch (s.charAt(i)) {
        case '"': doubleq++; break;
        case '\'': singleq++; break;
      }
    }

    String doublequote, singlequote;
    char quote;
    if (preferSingleQuotes ?
        (singleq <= doubleq) : (singleq < doubleq)) {
      // more double quotes so enclose in single quotes.
      quote = '\'';
      doublequote = "\"";
      singlequote = "\\\'";
    } else {
      // more single quotes so escape the doubles
      quote = '\"';
      doublequote = "\\\"";
      singlequote = "\'";
    }

    return strEscape(s, quote, doublequote, singlequote, "\\\\",
        outputCharsetEncoder, useSlashV, false);
  }

  /** Escapes regular expression */
  String regexpEscape(String s, CharsetEncoder outputCharsetEncoder) {
    return strEscape(s, '/', "\"", "'", "\\", outputCharsetEncoder, false, true);
  }

  /* If the user doesn't want to specify an output charset encoder, assume
     they want Latin/ASCII characters only.
   */
  String regexpEscape(String s) {
    return regexpEscape(s, null);
  }

  /** Helper to escape JavaScript string as well as regular expression */
  private String strEscape(
      String s,
      char quote,
      String doublequoteEscape,
      String singlequoteEscape,
      String backslashEscape,
      CharsetEncoder outputCharsetEncoder,
      boolean useSlashV,
      boolean isRegexp) {
    StringBuilder sb = new StringBuilder(s.length() + 2);
    sb.append(quote);
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      switch (c) {
        case '\0': sb.append("\\x00"); break;
        case '\u000B':
          if (useSlashV) {
            sb.append("\\v");
          } else {
            sb.append("\\x0B");
          }
          break;
        // From the SingleEscapeCharacter grammar production.
        case '\b': sb.append("\\b"); break;
        case '\f': sb.append("\\f"); break;
        case '\n': sb.append("\\n"); break;
        case '\r': sb.append("\\r"); break;
        case '\t': sb.append("\\t"); break;
        case '\\': sb.append(backslashEscape); break;
        case '\"': sb.append(doublequoteEscape); break;
        case '\'': sb.append(singlequoteEscape); break;

        // From LineTerminators (ES5 Section 7.3, Table 3)
        case '\u2028': sb.append("\\u2028"); break;
        case '\u2029': sb.append("\\u2029"); break;

        case '=':
          // '=' is a syntactically signficant regexp character.
          if (trustedStrings || isRegexp) {
            sb.append(c);
          } else {
            sb.append("\\x3d");
          }
          break;

        case '&':
          if (trustedStrings || isRegexp) {
            sb.append(c);
          } else {
            sb.append("\\x26");
          }
          break;

        case '>':
          if (!trustedStrings && !isRegexp) {
            sb.append(GT_ESCAPED);
            break;
          }

          // Break --> into --\> or ]]> into ]]\>
          //
          // This is just to prevent developers from shooting themselves in the
          // foot, and does not provide the level of security that you get
          // with trustedString == false.
          if (i >= 2 &&
              ((s.charAt(i - 1) == '-' && s.charAt(i - 2) == '-') ||
               (s.charAt(i - 1) == ']' && s.charAt(i - 2) == ']'))) {
            sb.append(GT_ESCAPED);
          } else {
            sb.append(c);
          }
          break;
        case '<':
          if (!trustedStrings && !isRegexp) {
            sb.append(LT_ESCAPED);
            break;
          }

          // Break </script into <\/script
          // As above, this is just to prevent developers from doing this
          // accidentally.
          final String endScript = "/script";

          // Break <!-- into <\!--
          final String startComment = "!--";

          if (s.regionMatches(true, i + 1, endScript, 0,
                              endScript.length())) {
            sb.append(LT_ESCAPED);
          } else if (s.regionMatches(false, i + 1, startComment, 0,
                                     startComment.length())) {
            sb.append(LT_ESCAPED);
          } else {
            sb.append(c);
          }
          break;
        default:
          // If we're given an outputCharsetEncoder, then check if the
          //  character can be represented in this character set.
          if (outputCharsetEncoder != null) {
            if (outputCharsetEncoder.canEncode(c)) {
              sb.append(c);
            } else {
              // Unicode-escape the character.
              appendHexJavaScriptRepresentation(sb, c);
            }
          } else {
            // No charsetEncoder provided - pass straight Latin characters
            // through, and escape the rest.  Doing the explicit character
            // check is measurably faster than using the CharsetEncoder.
            if (c > 0x1f && c < 0x7f) {
              sb.append(c);
            } else {
              // Other characters can be misinterpreted by some JS parsers,
              // or perhaps mangled by proxies along the way,
              // so we play it safe and Unicode escape them.
              appendHexJavaScriptRepresentation(sb, c);
            }
          }
      }
    }
    sb.append(quote);
    return sb.toString();
  }

  static String identifierEscape(String s) {
    // First check if escaping is needed at all -- in most cases it isn't.
    if (NodeUtil.isLatin(s)) {
      return s;
    }

    // Now going through the string to escape non-Latin characters if needed.
    StringBuilder sb = new StringBuilder();
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      // Identifiers should always go to Latin1/ ASCII characters because
      // different browser's rules for valid identifier characters are
      // crazy.
      if (c > 0x1F && c < 0x7F) {
        sb.append(c);
      } else {
        appendHexJavaScriptRepresentation(sb, c);
      }
    }
    return sb.toString();
  }
  /**
   * @param maxCount The maximum number of children to look for.
   * @return The number of children of this node that are non empty up to
   * maxCount.
   */
  private static int getNonEmptyChildCount(Node n, int maxCount) {
    int i = 0;
    Node c = n.getFirstChild();
    for (; c != null && i < maxCount; c = c.getNext()) {
      if (c.isBlock()) {
        i += getNonEmptyChildCount(c, maxCount - i);
      } else if (!c.isEmpty()) {
        i++;
      }
    }
    return i;
  }

  /** Gets the first non-empty child of the given node. */
  private static Node getFirstNonEmptyChild(Node n) {
    for (Node c = n.getFirstChild(); c != null; c = c.getNext()) {
      if (c.isBlock()) {
        Node result = getFirstNonEmptyChild(c);
        if (result != null) {
          return result;
        }
      } else if (!c.isEmpty()) {
        return c;
      }
    }
    return null;
  }

  // Information on the current context. Used for disambiguating special cases.
  // For example, a "{" could indicate the start of an object literal or a
  // block, depending on the current context.
  enum Context {
    STATEMENT,
    BEFORE_DANGLING_ELSE, // a hack to resolve the else-clause ambiguity
    START_OF_EXPR,
    PRESERVE_BLOCK,
    // Are we inside the init clause of a for loop?  If so, the containing
    // expression can't contain an in operator.  Pass this context flag down
    // until we reach expressions which no longer have the limitation.
    IN_FOR_INIT_CLAUSE,
    OTHER
  }

  private static Context getContextForNonEmptyExpression(Context currentContext) {
    return currentContext == Context.BEFORE_DANGLING_ELSE ?
        Context.BEFORE_DANGLING_ELSE : Context.OTHER;
  }

  /**
   * If we're in a IN_FOR_INIT_CLAUSE, we can't permit in operators in the
   * expression.  Pass on the IN_FOR_INIT_CLAUSE flag through subexpressions.
   */
  private static Context getContextForNoInOperator(Context context) {
    return (context == Context.IN_FOR_INIT_CLAUSE
        ? Context.IN_FOR_INIT_CLAUSE : Context.OTHER);
  }

  /**
   * @see #appendHexJavaScriptRepresentation(int, Appendable)
   */
  private static void appendHexJavaScriptRepresentation(
      StringBuilder sb, char c) {
    try {
      appendHexJavaScriptRepresentation(c, sb);
    } catch (IOException ex) {
      // StringBuilder does not throw IOException.
      throw new RuntimeException(ex);
    }
  }

  /**
   * Returns a JavaScript representation of the character in a hex escaped
   * format.
   *
   * @param codePoint The code point to append.
   * @param out The buffer to which the hex representation should be appended.
   */
  private static void appendHexJavaScriptRepresentation(
      int codePoint, Appendable out)
      throws IOException {
    if (Character.isSupplementaryCodePoint(codePoint)) {
      // Handle supplementary Unicode values which are not representable in
      // JavaScript.  We deal with these by escaping them as two 4B sequences
      // so that they will round-trip properly when sent from Java to JavaScript
      // and back.
      char[] surrogates = Character.toChars(codePoint);
      appendHexJavaScriptRepresentation(surrogates[0], out);
      appendHexJavaScriptRepresentation(surrogates[1], out);
      return;
    }
    out.append("\\u")
        .append(HEX_CHARS[(codePoint >>> 12) & 0xf])
        .append(HEX_CHARS[(codePoint >>> 8) & 0xf])
        .append(HEX_CHARS[(codePoint >>> 4) & 0xf])
        .append(HEX_CHARS[codePoint & 0xf]);
  }
}


File: src/com/google/javascript/jscomp/NodeUtil.java
/*
 * Copyright 2004 The Closure Compiler Authors.
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

import com.google.common.base.Preconditions;
import com.google.common.base.Predicate;
import com.google.common.base.Predicates;
import com.google.common.base.Splitter;
import com.google.common.collect.ImmutableSet;
import com.google.javascript.jscomp.CompilerOptions.LanguageMode;
import com.google.javascript.rhino.IR;
import com.google.javascript.rhino.InputId;
import com.google.javascript.rhino.JSDocInfo;
import com.google.javascript.rhino.JSDocInfoBuilder;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.StaticSourceFile;
import com.google.javascript.rhino.Token;
import com.google.javascript.rhino.TokenStream;
import com.google.javascript.rhino.jstype.TernaryValue;

import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.annotation.Nullable;

/**
 * NodeUtil contains generally useful AST utilities.
 *
 * @author nicksantos@google.com (Nick Santos)
 * @author johnlenz@google.com (John Lenz)
 */
public final class NodeUtil {
  static final long MAX_POSITIVE_INTEGER_NUMBER = 1L << 53;

  static final String JSC_PROPERTY_NAME_FN = "JSCompiler_renameProperty";

  static final char LARGEST_BASIC_LATIN = 0x7f;

  /** the set of builtin constructors that don't have side effects. */
  private static final Set<String> CONSTRUCTORS_WITHOUT_SIDE_EFFECTS =
      ImmutableSet.of(
        "Array",
        "Date",
        "Error",
        "Object",
        "RegExp",
        "XMLHttpRequest");

  // Utility class; do not instantiate.
  private NodeUtil() {}

  /**
   * Gets the boolean value of a node that represents a expression. This method
   * effectively emulates the <code>Boolean()</code> JavaScript cast function.
   * Note: unlike getPureBooleanValue this function does not return UNKNOWN
   * for expressions with side-effects.
   */
  static TernaryValue getImpureBooleanValue(Node n) {
    switch (n.getType()) {
      case Token.ASSIGN:
      case Token.COMMA:
        // For ASSIGN and COMMA the value is the value of the RHS.
        return getImpureBooleanValue(n.getLastChild());
      case Token.NOT:
        TernaryValue value = getImpureBooleanValue(n.getLastChild());
        return value.not();
      case Token.AND: {
        TernaryValue lhs = getImpureBooleanValue(n.getFirstChild());
        TernaryValue rhs = getImpureBooleanValue(n.getLastChild());
        return lhs.and(rhs);
      }
      case Token.OR:  {
        TernaryValue lhs = getImpureBooleanValue(n.getFirstChild());
        TernaryValue rhs = getImpureBooleanValue(n.getLastChild());
        return lhs.or(rhs);
      }
      case Token.HOOK:  {
        TernaryValue trueValue = getImpureBooleanValue(
            n.getFirstChild().getNext());
        TernaryValue falseValue = getImpureBooleanValue(n.getLastChild());
        if (trueValue.equals(falseValue)) {
          return trueValue;
        } else {
          return TernaryValue.UNKNOWN;
        }
      }
      case Token.ARRAYLIT:
      case Token.OBJECTLIT:
        // ignoring side-effects
        return TernaryValue.TRUE;

      case Token.VOID:
        return TernaryValue.FALSE;

      default:
        return getPureBooleanValue(n);
    }
  }

  /**
   * Gets the boolean value of a node that represents a literal. This method
   * effectively emulates the <code>Boolean()</code> JavaScript cast function
   * except it return UNKNOWN for known values with side-effects, use
   * getImpureBooleanValue if you don't care about side-effects.
   */
  static TernaryValue getPureBooleanValue(Node n) {
    switch (n.getType()) {
      case Token.STRING:
        return TernaryValue.forBoolean(n.getString().length() > 0);

      case Token.NUMBER:
        return TernaryValue.forBoolean(n.getDouble() != 0);

      case Token.NOT:
        return getPureBooleanValue(n.getLastChild()).not();

      case Token.NULL:
      case Token.FALSE:
        return TernaryValue.FALSE;

      case Token.VOID:
        if (!mayHaveSideEffects(n.getFirstChild())) {
          return TernaryValue.FALSE;
        }
        break;

      case Token.NAME:
        String name = n.getString();
        if ("undefined".equals(name)
            || "NaN".equals(name)) {
          // We assume here that programs don't change the value of the keyword
          // undefined to something other than the value undefined.
          return TernaryValue.FALSE;
        } else if ("Infinity".equals(name)) {
          return TernaryValue.TRUE;
        }
        break;

      case Token.TRUE:
      case Token.REGEXP:
        return TernaryValue.TRUE;

      case Token.ARRAYLIT:
      case Token.OBJECTLIT:
        if (!mayHaveSideEffects(n)) {
          return TernaryValue.TRUE;
        }
        break;
    }

    return TernaryValue.UNKNOWN;
  }

  /**
   * Gets the value of a node as a String, or null if it cannot be converted.
   * When it returns a non-null String, this method effectively emulates the
   * <code>String()</code> JavaScript cast function.
   */
  static String getStringValue(Node n) {
    // TODO(user): regex literals as well.
    switch (n.getType()) {
      case Token.STRING:
      case Token.STRING_KEY:
        return n.getString();

      case Token.NAME:
        String name = n.getString();
        if ("undefined".equals(name)
            || "Infinity".equals(name)
            || "NaN".equals(name)) {
          return name;
        }
        break;

      case Token.NUMBER:
        return getStringValue(n.getDouble());

      case Token.FALSE:
        return "false";

      case Token.TRUE:
        return "true";

      case Token.NULL:
        return "null";

      case Token.VOID:
        return "undefined";

      case Token.NOT:
        TernaryValue child = getPureBooleanValue(n.getFirstChild());
        if (child != TernaryValue.UNKNOWN) {
          return child.toBoolean(true) ? "false" : "true"; // reversed.
        }
        break;

      case Token.ARRAYLIT:
        return arrayToString(n);

      case Token.OBJECTLIT:
        return "[object Object]";
    }
    return null;
  }

  static String getStringValue(double value) {
    long longValue = (long) value;

    // Return "1" instead of "1.0"
    if (longValue == value) {
      return Long.toString(longValue);
    } else {
      return Double.toString(value);
    }
  }

  /**
   * When converting arrays to string using Array.prototype.toString or
   * Array.prototype.join, the rules for conversion to String are different
   * than converting each element individually.  Specifically, "null" and
   * "undefined" are converted to an empty string.
   * @param n A node that is a member of an Array.
   * @return The string representation.
   */
  static String getArrayElementStringValue(Node n) {
    return (NodeUtil.isNullOrUndefined(n) || n.isEmpty())
        ? "" : getStringValue(n);
  }

  static String arrayToString(Node literal) {
    Node first = literal.getFirstChild();
    StringBuilder result = new StringBuilder();
    for (Node n = first; n != null; n = n.getNext()) {
      String childValue = getArrayElementStringValue(n);
      if (childValue == null) {
        return null;
      }
      if (n != first) {
        result.append(',');
      }
      result.append(childValue);
    }
    return result.toString();
  }

  /**
   * Gets the value of a node as a Number, or null if it cannot be converted.
   * When it returns a non-null Double, this method effectively emulates the
   * <code>Number()</code> JavaScript cast function.
   */
  static Double getNumberValue(Node n) {
    switch (n.getType()) {
      case Token.TRUE:
        return 1.0;

      case Token.FALSE:
      case Token.NULL:
        return 0.0;

      case Token.NUMBER:
        return n.getDouble();

      case Token.VOID:
        if (mayHaveSideEffects(n.getFirstChild())) {
          return null;
        } else {
          return Double.NaN;
        }

      case Token.NAME:
        // Check for known constants
        String name = n.getString();
        if (name.equals("undefined")) {
          return Double.NaN;
        }
        if (name.equals("NaN")) {
          return Double.NaN;
        }
        if (name.equals("Infinity")) {
          return Double.POSITIVE_INFINITY;
        }
        return null;

      case Token.NEG:
        if (n.getChildCount() == 1 && n.getFirstChild().isName()
            && n.getFirstChild().getString().equals("Infinity")) {
          return Double.NEGATIVE_INFINITY;
        }
        return null;

      case Token.NOT:
        TernaryValue child = getPureBooleanValue(n.getFirstChild());
        if (child != TernaryValue.UNKNOWN) {
          return child.toBoolean(true) ? 0.0 : 1.0; // reversed.
        }
        break;

      case Token.STRING:
        return getStringNumberValue(n.getString());

      case Token.ARRAYLIT:
      case Token.OBJECTLIT:
        String value = getStringValue(n);
        return value != null ? getStringNumberValue(value) : null;
    }

    return null;
  }

  static Double getStringNumberValue(String rawJsString) {
    if (rawJsString.contains("\u000b")) {
      // vertical tab is not always whitespace
      return null;
    }

    String s = trimJsWhiteSpace(rawJsString);
    // return ScriptRuntime.toNumber(s);
    if (s.isEmpty()) {
      return 0.0;
    }

    if (s.length() > 2
        && s.charAt(0) == '0'
        && (s.charAt(1) == 'x' || s.charAt(1) == 'X')) {
      // Attempt to convert hex numbers.
      try {
        return Double.valueOf(Integer.parseInt(s.substring(2), 16));
      } catch (NumberFormatException e) {
        return Double.NaN;
      }
    }

    if (s.length() > 3
        && (s.charAt(0) == '-' || s.charAt(0) == '+')
        && s.charAt(1) == '0'
        && (s.charAt(2) == 'x' || s.charAt(2) == 'X')) {
      // hex numbers with explicit signs vary between browsers.
      return null;
    }

    // Firefox and IE treat the "Infinity" differently. Firefox is case
    // insensitive, but IE treats "infinity" as NaN.  So leave it alone.
    if (s.equals("infinity")
        || s.equals("-infinity")
        || s.equals("+infinity")) {
      return null;
    }

    try {
      return Double.parseDouble(s);
    } catch (NumberFormatException e) {
      return Double.NaN;
    }
  }

  static String trimJsWhiteSpace(String s) {
    int start = 0;
    int end = s.length();
    while (end > 0
        && isStrWhiteSpaceChar(s.charAt(end - 1)) == TernaryValue.TRUE) {
      end--;
    }
    while (start < end
        && isStrWhiteSpaceChar(s.charAt(start)) == TernaryValue.TRUE) {
      start++;
    }
    return s.substring(start, end);
  }

  /**
   * Copied from Rhino's ScriptRuntime
   */
  public static TernaryValue isStrWhiteSpaceChar(int c) {
    switch (c) {
      case '\u000B': // <VT>
        return TernaryValue.UNKNOWN;  // IE says "no", ECMAScript says "yes"
      case ' ': // <SP>
      case '\n': // <LF>
      case '\r': // <CR>
      case '\t': // <TAB>
      case '\u00A0': // <NBSP>
      case '\u000C': // <FF>
      case '\u2028': // <LS>
      case '\u2029': // <PS>
      case '\uFEFF': // <BOM>
        return TernaryValue.TRUE;
      default:
        return (Character.getType(c) == Character.SPACE_SEPARATOR)
            ? TernaryValue.TRUE : TernaryValue.FALSE;
    }
  }

  /**
   * Gets the node of a class's name. This method recognizes five forms:
   * <ul>
   * <li>{@code class name {...}}</li>
   * <li>{@code var name = class {...}}</li>
   * <li>{@code qualified.name = class {...}}</li>
   * <li>{@code var name2 = class name1 {...}}</li>
   * <li>{@code qualified.name2 = class name1 {...}}</li>
   * </ul>
   * In two last cases with named function expressions, the second name is
   * returned (the variable or qualified name).
   *
   * @param clazz A class node
   * @return the node best representing the class's name
   */
  static Node getClassNameNode(Node clazz) {
    Preconditions.checkState(clazz.isClass());
    return getNameNode(clazz);
  }

  static String getClassName(Node n) {
    Node nameNode = getClassNameNode(n);
    return nameNode == null ? null : nameNode.getQualifiedName();
  }

  /**
   * Gets the node of a function's name. This method recognizes five forms:
   * <ul>
   * <li>{@code function name() ...}</li>
   * <li>{@code var name = function() ...}</li>
   * <li>{@code qualified.name = function() ...}</li>
   * <li>{@code var name2 = function name1() ...}</li>
   * <li>{@code qualified.name2 = function name1() ...}</li>
   * </ul>
   * In two last cases with named function expressions, the second name is
   * returned (the variable or qualified name).
   *
   * @param n A function node
   * @return the node best representing the function's name
   */
  static Node getFunctionNameNode(Node n) {
    Preconditions.checkState(n.isFunction());
    return getNameNode(n);
  }

  public static String getFunctionName(Node n) {
    Node nameNode = getFunctionNameNode(n);
    return nameNode == null ? null : nameNode.getQualifiedName();
  }

  /** Implementation for getFunctionNameNode and getClassNameNode. */
  private static Node getNameNode(Node n) {
    Node parent = n.getParent();
    switch (parent.getType()) {
      case Token.NAME:
        // var name = function() ...
        // var name2 = function name1() ...
        return parent;

      case Token.ASSIGN:
        // qualified.name = function() ...
        // qualified.name2 = function name1() ...
        return parent.getFirstChild();

      default:
        // function name() ...
        Node funNameNode = n.getFirstChild();
        // Don't return the name node for anonymous functions/classes.
        // TODO(tbreisacher): Currently we do two kinds of "empty" checks because
        // anonymous classes have an EMPTY name node while anonymous functions
        // have a STRING node with an empty string. Consider making these the same.
        return (funNameNode.isEmpty() || funNameNode.getString().isEmpty())
            ? null : funNameNode;
    }
  }

  /**
   * Gets the function's name. This method recognizes the forms:
   * <ul>
   * <li>{@code &#123;'name': function() ...&#125;}</li>
   * <li>{@code &#123;name: function() ...&#125;}</li>
   * <li>{@code function name() ...}</li>
   * <li>{@code var name = function() ...}</li>
   * <li>{@code qualified.name = function() ...}</li>
   * <li>{@code var name2 = function name1() ...}</li>
   * <li>{@code qualified.name2 = function name1() ...}</li>
   * </ul>
   *
   * @param n a node whose type is {@link Token#FUNCTION}
   * @return the function's name, or {@code null} if it has no name
   */
  public static String getNearestFunctionName(Node n) {
    if (!n.isFunction()) {
      return null;
    }

    String name = getFunctionName(n);
    if (name != null) {
      return name;
    }

    // Check for the form { 'x' : function() { } }
    Node parent = n.getParent();
    switch (parent.getType()) {
      case Token.SETTER_DEF:
      case Token.GETTER_DEF:
      case Token.STRING_KEY:
        // Return the name of the literal's key.
        return parent.getString();
      case Token.NUMBER:
        return getStringValue(parent);
    }

    return null;
  }


  /**
   * Returns true if this is an immutable value.
   */
  static boolean isImmutableValue(Node n) {
    switch (n.getType()) {
      case Token.STRING:
      case Token.NUMBER:
      case Token.NULL:
      case Token.TRUE:
      case Token.FALSE:
        return true;
      case Token.CAST:
      case Token.NOT:
        return isImmutableValue(n.getFirstChild());
      case Token.VOID:
      case Token.NEG:
        return isImmutableValue(n.getFirstChild());
      case Token.NAME:
        String name = n.getString();
        // We assume here that programs don't change the value of the keyword
        // undefined to something other than the value undefined.
        return "undefined".equals(name)
            || "Infinity".equals(name)
            || "NaN".equals(name);
    }

    return false;
  }

  /**
   * Returns true if the operator on this node is symmetric
   */
  static boolean isSymmetricOperation(Node n) {
    switch (n.getType()) {
      case Token.EQ: // equal
      case Token.NE: // not equal
      case Token.SHEQ: // exactly equal
      case Token.SHNE: // exactly not equal
      case Token.MUL: // multiply, unlike add it only works on numbers
                      // or results NaN if any of the operators is not a number
        return true;
    }
    return false;
  }

  /**
   * Returns true if the operator on this node is relational.
   * the returned set does not include the equalities.
   */
  static boolean isRelationalOperation(Node n) {
    switch (n.getType()) {
      case Token.GT: // equal
      case Token.GE: // not equal
      case Token.LT: // exactly equal
      case Token.LE: // exactly not equal
        return true;
    }
    return false;
  }

  static boolean isAssignmentTarget(Node n) {
    Node parent = n.getParent();
    if ((isAssignmentOp(parent) && parent.getFirstChild() == n)
        || parent.isInc()
        || parent.isDec()
        || (isForIn(parent) && parent.getFirstChild() == n)) {
      // If GETPROP/GETELEM is used as assignment target the object literal is
      // acting as a temporary we can't fold it here:
      //    "{a:x}.a += 1" is not "x += 1"
      return true;
    }
    return false;
  }

  /**
   * Returns the inverse of an operator if it is invertible.
   * ex. '>' ==> '<'
   */
  static int getInverseOperator(int type) {
    switch (type) {
      case Token.GT:
        return Token.LT;
      case Token.LT:
        return Token.GT;
      case Token.GE:
        return Token.LE;
      case Token.LE:
        return Token.GE;
    }
    return Token.ERROR;
  }

  /**
   * Returns true if this is a literal value. We define a literal value
   * as any node that evaluates to the same thing regardless of when or
   * where it is evaluated. So /xyz/ and [3, 5] are literals, but
   * the name a is not.
   *
   * <p>Function literals do not meet this definition, because they
   * lexically capture variables. For example, if you have
   * <code>
   * function() { return a; }
   * </code>
   * If it is evaluated in a different scope, then it
   * captures a different variable. Even if the function did not read
   * any captured variables directly, it would still fail this definition,
   * because it affects the lifecycle of variables in the enclosing scope.
   *
   * <p>However, a function literal with respect to a particular scope is
   * a literal.
   *
   * @param includeFunctions If true, all function expressions will be
   *     treated as literals.
   */
  static boolean isLiteralValue(Node n, boolean includeFunctions) {
    switch (n.getType()) {
      case Token.CAST:
        return isLiteralValue(n.getFirstChild(), includeFunctions);

      case Token.ARRAYLIT:
        for (Node child = n.getFirstChild(); child != null;
             child = child.getNext()) {
          if ((!child.isEmpty()) && !isLiteralValue(child, includeFunctions)) {
            return false;
          }
        }
        return true;

      case Token.REGEXP:
        // Return true only if all children are const.
        for (Node child = n.getFirstChild(); child != null;
             child = child.getNext()) {
          if (!isLiteralValue(child, includeFunctions)) {
            return false;
          }
        }
        return true;

      case Token.OBJECTLIT:
        // Return true only if all values are const.
        for (Node child = n.getFirstChild(); child != null;
             child = child.getNext()) {
          if (!isLiteralValue(child.getFirstChild(), includeFunctions)) {
            return false;
          }
        }
        return true;

      case Token.FUNCTION:
        return includeFunctions && !NodeUtil.isFunctionDeclaration(n);

      default:
        return isImmutableValue(n);
    }
  }

  /**
   * Determines whether the given value may be assigned to a define.
   *
   * @param val The value being assigned.
   * @param defines The list of names of existing defines.
   */
  static boolean isValidDefineValue(Node val, Set<String> defines) {
    switch (val.getType()) {
      case Token.STRING:
      case Token.NUMBER:
      case Token.TRUE:
      case Token.FALSE:
        return true;

      // Binary operators are only valid if both children are valid.
      case Token.AND:
      case Token.OR:
      case Token.ADD:
      case Token.BITAND:
      case Token.BITNOT:
      case Token.BITOR:
      case Token.BITXOR:
      case Token.DIV:
      case Token.EQ:
      case Token.GE:
      case Token.GT:
      case Token.LE:
      case Token.LSH:
      case Token.LT:
      case Token.MOD:
      case Token.MUL:
      case Token.NE:
      case Token.RSH:
      case Token.SHEQ:
      case Token.SHNE:
      case Token.SUB:
      case Token.URSH:
        return isValidDefineValue(val.getFirstChild(), defines)
            && isValidDefineValue(val.getLastChild(), defines);

      // Unary operators are valid if the child is valid.
      case Token.NOT:
      case Token.NEG:
      case Token.POS:
        return isValidDefineValue(val.getFirstChild(), defines);

      // Names are valid if and only if they are defines themselves.
      case Token.NAME:
      case Token.GETPROP:
        if (val.isQualifiedName()) {
          return defines.contains(val.getQualifiedName());
        }
    }
    return false;
  }

  /**
   * Returns whether this a BLOCK node with no children.
   *
   * @param block The node.
   */
  static boolean isEmptyBlock(Node block) {
    if (!block.isBlock()) {
      return false;
    }

    for (Node n = block.getFirstChild(); n != null; n = n.getNext()) {
      if (!n.isEmpty()) {
        return false;
      }
    }
    return true;
  }

  static boolean isSimpleOperator(Node n) {
    return isSimpleOperatorType(n.getType());
  }

  /**
   * A "simple" operator is one whose children are expressions,
   * has no direct side-effects (unlike '+='), and has no
   * conditional aspects (unlike '||').
   */
  static boolean isSimpleOperatorType(int type) {
    switch (type) {
      case Token.ADD:
      case Token.BITAND:
      case Token.BITNOT:
      case Token.BITOR:
      case Token.BITXOR:
      case Token.COMMA:
      case Token.DIV:
      case Token.EQ:
      case Token.GE:
      case Token.GETELEM:
      case Token.GETPROP:
      case Token.GT:
      case Token.INSTANCEOF:
      case Token.LE:
      case Token.LSH:
      case Token.LT:
      case Token.MOD:
      case Token.MUL:
      case Token.NE:
      case Token.NOT:
      case Token.RSH:
      case Token.SHEQ:
      case Token.SHNE:
      case Token.SUB:
      case Token.TYPEOF:
      case Token.VOID:
      case Token.POS:
      case Token.NEG:
      case Token.URSH:
        return true;

      default:
        return false;
    }
  }

  static boolean isTypedefDecl(Node n) {
    if (n.isVar()
        || n.isName() && n.getParent().isVar()
        || n.isGetProp() && n.getParent().isExprResult()) {
      JSDocInfo jsdoc = getBestJSDocInfo(n);
      return jsdoc != null && jsdoc.hasTypedefType();
    }
    return false;
  }

  static boolean isEnumDecl(Node n) {
    if (n.isVar()
        || n.isName() && n.getParent().isVar()
        || (n.isGetProp() && n.getParent().isAssign()
            && n.getParent().getParent().isExprResult())
        || (n.isAssign() && n.getParent().isExprResult())) {
      JSDocInfo jsdoc = getBestJSDocInfo(n);
      return jsdoc != null && jsdoc.hasEnumParameterType();
    }
    return false;
  }

  static boolean isAliasedNominalTypeDecl(Node n) {
    if (n.isName()) {
      n = n.getParent();
    }
    if (n.isVar() && n.getChildCount() == 1) {
      Node name = n.getFirstChild();
      Node init = name.getFirstChild();
      JSDocInfo jsdoc = getBestJSDocInfo(n);
      return jsdoc != null
          && (jsdoc.isConstructor() || jsdoc.isInterface())
          && init != null
          && init.isQualifiedName();
    }
    Node parent = n.getParent();
    if (n.isGetProp() && n.isQualifiedName()
        && parent.isAssign() && parent.getParent().isExprResult()) {
      JSDocInfo jsdoc = getBestJSDocInfo(n);
      return jsdoc != null
          && (jsdoc.isConstructor() || jsdoc.isInterface())
          && parent.getLastChild().isQualifiedName();
    }
    return false;
  }

  static Node getInitializer(Node n) {
    Preconditions.checkArgument(n.isQualifiedName() || n.isStringKey());
    switch (n.getParent().getType()) {
      case Token.ASSIGN:
        return n.getNext();
      case Token.VAR:
      case Token.OBJECTLIT:
        return n.getFirstChild();
      default:
        return null;
    }
  }

  /**
   * Returns true iff this node defines a namespace, such as goog or goog.math.
   */
  static boolean isNamespaceDecl(Node n) {
    JSDocInfo jsdoc = getBestJSDocInfo(n);
    if (jsdoc == null || !jsdoc.isConstant()
        || !jsdoc.getTypeNodes().isEmpty()) {
      return false;
    }
    Node qnameNode;
    Node initializer;
    if (n.getParent().isVar()) {
      qnameNode = n;
      initializer = n.getFirstChild();
    } else if (n.isExprResult()) {
      Node expr = n.getFirstChild();
      if (!expr.isAssign() || !expr.getFirstChild().isGetProp()) {
        return false;
      }
      qnameNode = expr.getFirstChild();
      initializer = expr.getLastChild();
    } else if (n.isGetProp()) {
      Node parent = n.getParent();
      if (!parent.isAssign() || !parent.getParent().isExprResult()) {
        return false;
      }
      qnameNode = n;
      initializer = parent.getLastChild();
    } else {
      return false;
    }
    if (initializer == null || qnameNode == null) {
      return false;
    }
    if (initializer.isObjectLit()) {
      return true;
    }
    return initializer.isOr()
        && qnameNode.matchesQualifiedName(initializer.getFirstChild())
        && initializer.getLastChild().isObjectLit();
  }

  /**
   * Creates an EXPR_RESULT.
   *
   * @param child The expression itself.
   * @return Newly created EXPR node with the child as subexpression.
   */
  static Node newExpr(Node child) {
    return IR.exprResult(child).srcref(child);
  }

  /**
   * Returns true if the node may create new mutable state, or change existing
   * state.
   *
   * @see <a href="http://www.xkcd.org/326/">XKCD Cartoon</a>
   */
  static boolean mayEffectMutableState(Node n) {
    return mayEffectMutableState(n, null);
  }

  static boolean mayEffectMutableState(Node n, AbstractCompiler compiler) {
    return checkForStateChangeHelper(n, true, compiler);
  }

  /**
   * Returns true if the node which may have side effects when executed.
   */
  public static boolean mayHaveSideEffects(Node n) {
    return mayHaveSideEffects(n, null);
  }

  public static boolean mayHaveSideEffects(Node n, AbstractCompiler compiler) {
    return checkForStateChangeHelper(n, false, compiler);
  }

  /**
   * Returns true if some node in n's subtree changes application state.
   * If {@code checkForNewObjects} is true, we assume that newly created
   * mutable objects (like object literals) change state. Otherwise, we assume
   * that they have no side effects.
   */
  private static boolean checkForStateChangeHelper(
      Node n, boolean checkForNewObjects, AbstractCompiler compiler) {
    // Rather than id which ops may have side effects, id the ones
    // that we know to be safe
    switch (n.getType()) {
      // other side-effect free statements and expressions
      case Token.CAST:
      case Token.AND:
      case Token.BLOCK:
      case Token.EXPR_RESULT:
      case Token.HOOK:
      case Token.IF:
      case Token.IN:
      case Token.PARAM_LIST:
      case Token.NUMBER:
      case Token.OR:
      case Token.THIS:
      case Token.TRUE:
      case Token.FALSE:
      case Token.NULL:
      case Token.STRING:
      case Token.STRING_KEY:
      case Token.SWITCH:
      case Token.TRY:
      case Token.EMPTY:
        break;

      // Throws are by definition side effects, and yields are similar.
      case Token.THROW:
      case Token.YIELD:
        return true;

      case Token.OBJECTLIT:
        if (checkForNewObjects) {
          return true;
        }
        for (Node c = n.getFirstChild(); c != null; c = c.getNext()) {
          if (checkForStateChangeHelper(
                  c.getFirstChild(), checkForNewObjects, compiler)) {
            return true;
          }
        }
        return false;

      case Token.ARRAYLIT:
      case Token.REGEXP:
        if (checkForNewObjects) {
          return true;
        }
        break;

      case Token.VAR:    // empty var statement (no declaration)
      case Token.NAME:   // variable by itself
        if (n.getFirstChild() != null) {
          return true;
        }
        break;

      case Token.FUNCTION:
        // Function expressions don't have side-effects, but function
        // declarations change the namespace. Either way, we don't need to
        // check the children, since they aren't executed at declaration time.
        return checkForNewObjects || !isFunctionExpression(n);

      case Token.NEW:
        if (checkForNewObjects) {
          return true;
        }

        if (!constructorCallHasSideEffects(n)) {
          // loop below will see if the constructor parameters have
          // side-effects
          break;
        }
        return true;

      case Token.CALL:
        // calls to functions that have no side effects have the no
        // side effect property set.
        if (!functionCallHasSideEffects(n, compiler)) {
          // loop below will see if the function parameters have
          // side-effects
          break;
        }
        return true;

      default:
        if (isSimpleOperator(n)) {
          break;
        }

        if (isAssignmentOp(n)) {
          Node assignTarget = n.getFirstChild();
          if (assignTarget.isName()) {
            return true;
          }

          // Assignments will have side effects if
          // a) The RHS has side effects, or
          // b) The LHS has side effects, or
          // c) A name on the LHS will exist beyond the life of this statement.
          if (checkForStateChangeHelper(
                  n.getFirstChild(), checkForNewObjects, compiler) ||
              checkForStateChangeHelper(
                  n.getLastChild(), checkForNewObjects, compiler)) {
            return true;
          }

          if (isGet(assignTarget)) {
            // If the object being assigned to is a local object, don't
            // consider this a side-effect as it can't be referenced
            // elsewhere.  Don't do this recursively as the property might
            // be an alias of another object, unlike a literal below.
            Node current = assignTarget.getFirstChild();
            if (evaluatesToLocalValue(current)) {
              return false;
            }

            // A literal value as defined by "isLiteralValue" is guaranteed
            // not to be an alias, or any components which are aliases of
            // other objects.
            // If the root object is a literal don't consider this a
            // side-effect.
            while (isGet(current)) {
              current = current.getFirstChild();
            }

            return !isLiteralValue(current, true);
          } else {
            // TODO(johnlenz): remove this code and make this an exception. This
            // is here only for legacy reasons, the AST is not valid but
            // preserve existing behavior.
            return !isLiteralValue(assignTarget, true);
          }
        }

        return true;
    }

    for (Node c = n.getFirstChild(); c != null; c = c.getNext()) {
      if (checkForStateChangeHelper(c, checkForNewObjects, compiler)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Do calls to this constructor have side effects?
   *
   * @param callNode - constructor call node
   */
  static boolean constructorCallHasSideEffects(Node callNode) {
    return constructorCallHasSideEffects(callNode, null);
  }

  static boolean constructorCallHasSideEffects(
      Node callNode, AbstractCompiler compiler) {
    if (!callNode.isNew()) {
      throw new IllegalStateException(
          "Expected NEW node, got " + Token.name(callNode.getType()));
    }

    if (callNode.isNoSideEffectsCall()) {
      return false;
    }

    if (callNode.isOnlyModifiesArgumentsCall() &&
        allArgsUnescapedLocal(callNode)) {
      return false;
    }

    Node nameNode = callNode.getFirstChild();
    return !nameNode.isName() || !CONSTRUCTORS_WITHOUT_SIDE_EFFECTS.contains(nameNode.getString());
  }

  // A list of built-in object creation or primitive type cast functions that
  // can also be called as constructors but lack side-effects.
  // TODO(johnlenz): consider adding an extern annotation for this.
  private static final Set<String> BUILTIN_FUNCTIONS_WITHOUT_SIDEEFFECTS =
      ImmutableSet.of(
          "Object", "Array", "String", "Number", "Boolean", "RegExp", "Error");
  private static final Set<String> OBJECT_METHODS_WITHOUT_SIDEEFFECTS =
      ImmutableSet.of("toString", "valueOf");
  private static final Set<String> REGEXP_METHODS =
      ImmutableSet.of("test", "exec");
  private static final Set<String> STRING_REGEXP_METHODS =
      ImmutableSet.of("match", "replace", "search", "split");

  /**
   * Returns true if calls to this function have side effects.
   *
   * @param callNode - function call node
   */
  static boolean functionCallHasSideEffects(Node callNode) {
    return functionCallHasSideEffects(callNode, null);
  }

  /**
   * Returns true if calls to this function have side effects.
   *
   * @param callNode The call node to inspected.
   * @param compiler A compiler object to provide program state changing
   *     context information. Can be null.
   */
  static boolean functionCallHasSideEffects(
      Node callNode, @Nullable AbstractCompiler compiler) {
    if (!callNode.isCall()) {
      throw new IllegalStateException(
          "Expected CALL node, got " + Token.name(callNode.getType()));
    }

    if (callNode.isNoSideEffectsCall()) {
      return false;
    }

    if (callNode.isOnlyModifiesArgumentsCall() &&
        allArgsUnescapedLocal(callNode)) {
      return false;
    }

    Node nameNode = callNode.getFirstChild();

    // Built-in functions with no side effects.
    if (nameNode.isName()) {
      String name = nameNode.getString();
      if (BUILTIN_FUNCTIONS_WITHOUT_SIDEEFFECTS.contains(name)) {
        return false;
      }
    } else if (nameNode.isGetProp()) {
      if (callNode.hasOneChild()
          && OBJECT_METHODS_WITHOUT_SIDEEFFECTS.contains(
                nameNode.getLastChild().getString())) {
        return false;
      }

      if (callNode.isOnlyModifiesThisCall()
          && evaluatesToLocalValue(nameNode.getFirstChild())) {
        return false;
      }

      // Math.floor has no side-effects.
      // TODO(nicksantos): This is a terrible terrible hack, until
      // I create a definitionProvider that understands namespacing.
      if (nameNode.getFirstChild().isName()) {
        if ("Math.floor".equals(nameNode.getQualifiedName())) {
          return false;
        }
      }

      if (compiler != null && !compiler.hasRegExpGlobalReferences()) {
        if (nameNode.getFirstChild().isRegExp()
            && REGEXP_METHODS.contains(nameNode.getLastChild().getString())) {
          return false;
        } else if (nameNode.getFirstChild().isString()
            && STRING_REGEXP_METHODS.contains(
                nameNode.getLastChild().getString())) {
          Node param = nameNode.getNext();
          if (param != null &&
              (param.isString() || param.isRegExp())) {
            return false;
          }
        }
      }
    }

    return true;
  }

  /**
   * @return Whether the call has a local result.
   */
  static boolean callHasLocalResult(Node n) {
    Preconditions.checkState(n.isCall());
    return (n.getSideEffectFlags() & Node.FLAG_LOCAL_RESULTS) > 0;
  }

  /**
   * @return Whether the new has a local result.
   */
  static boolean newHasLocalResult(Node n) {
    Preconditions.checkState(n.isNew());
    return n.isOnlyModifiesThisCall();
  }

  /**
   * Returns true if the current node's type implies side effects.
   *
   * <p>This is a non-recursive version of the may have side effects
   * check; used to check wherever the current node's type is one of
   * the reason's why a subtree has side effects.
   */
  static boolean nodeTypeMayHaveSideEffects(Node n) {
    return nodeTypeMayHaveSideEffects(n, null);
  }

  static boolean nodeTypeMayHaveSideEffects(Node n, AbstractCompiler compiler) {
    if (isAssignmentOp(n)) {
      return true;
    }

    switch(n.getType()) {
      case Token.DELPROP:
      case Token.DEC:
      case Token.INC:
      case Token.YIELD:
      case Token.THROW:
        return true;
      case Token.CALL:
        return NodeUtil.functionCallHasSideEffects(n, compiler);
      case Token.NEW:
        return NodeUtil.constructorCallHasSideEffects(n, compiler);
      case Token.NAME:
        // A variable definition.
        return n.hasChildren();
      default:
        return false;
    }
  }

  static boolean allArgsUnescapedLocal(Node callOrNew) {
    for (Node arg = callOrNew.getFirstChild().getNext();
         arg != null; arg = arg.getNext()) {
      if (!evaluatesToLocalValue(arg)) {
        return false;
      }
    }
    return true;
  }

  /**
   * @return Whether the tree can be affected by side-effects or
   * has side-effects.
   */
  static boolean canBeSideEffected(Node n) {
    Set<String> emptySet = Collections.emptySet();
    return canBeSideEffected(n, emptySet, null);
  }

  /**
   * @param knownConstants A set of names known to be constant value at
   * node 'n' (such as locals that are last written before n can execute).
   * @return Whether the tree can be affected by side-effects or
   * has side-effects.
   */
  // TODO(nick): Get rid of the knownConstants argument in favor of using
  // scope with InferConsts.
  static boolean canBeSideEffected(
      Node n, Set<String> knownConstants, Scope scope) {
    switch (n.getType()) {
      case Token.YIELD:
      case Token.CALL:
      case Token.NEW:
        // Function calls or constructor can reference changed values.
        // TODO(johnlenz): Add some mechanism for determining that functions
        // are unaffected by side effects.
        return true;
      case Token.NAME:
        // Non-constant names values may have been changed.
        return !isConstantVar(n, scope)
            && !knownConstants.contains(n.getString());

      // Properties on constant NAMEs can still be side-effected.
      case Token.GETPROP:
      case Token.GETELEM:
        return true;

      case Token.FUNCTION:
        // Function expression are not changed by side-effects,
        // and function declarations are not part of expressions.
        Preconditions.checkState(isFunctionExpression(n));
        return false;
    }

    for (Node c = n.getFirstChild(); c != null; c = c.getNext()) {
      if (canBeSideEffected(c, knownConstants, scope)) {
        return true;
      }
    }

    return false;
  }

  /*
   *  0 comma ,
   *  1 assignment = += -= *= /= %= <<= >>= >>>= &= ^= |=
   *  2 conditional ?:
   *  3 logical-or ||
   *  4 logical-and &&
   *  5 bitwise-or |
   *  6 bitwise-xor ^
   *  7 bitwise-and &
   *  8 equality == !=
   *  9 relational < <= > >=
   * 10 bitwise shift << >> >>>
   * 11 addition/subtraction + -
   * 12 multiply/divide * / %
   * 13 negation/increment ! ~ - ++ --
   * 14 call, member () [] .
   */
  static int precedence(int type) {
    switch (type) {
      case Token.COMMA:  return 0;
      case Token.ASSIGN_BITOR:
      case Token.ASSIGN_BITXOR:
      case Token.ASSIGN_BITAND:
      case Token.ASSIGN_LSH:
      case Token.ASSIGN_RSH:
      case Token.ASSIGN_URSH:
      case Token.ASSIGN_ADD:
      case Token.ASSIGN_SUB:
      case Token.ASSIGN_MUL:
      case Token.ASSIGN_DIV:
      case Token.ASSIGN_MOD:
      case Token.ASSIGN: return 1;
      case Token.YIELD:  return 2;
      case Token.HOOK:   return 3;  // ?: operator
      case Token.OR:     return 4;
      case Token.AND:    return 5;
      case Token.BITOR:  return 6;
      case Token.BITXOR: return 7;
      case Token.BITAND: return 8;
      case Token.EQ:
      case Token.NE:
      case Token.SHEQ:
      case Token.SHNE:   return 9;
      case Token.LT:
      case Token.GT:
      case Token.LE:
      case Token.GE:
      case Token.INSTANCEOF:
      case Token.IN:     return 10;
      case Token.LSH:
      case Token.RSH:
      case Token.URSH:   return 11;
      case Token.SUB:
      case Token.ADD:    return 12;
      case Token.MUL:
      case Token.MOD:
      case Token.DIV:    return 13;
      case Token.INC:
      case Token.DEC:
      case Token.NEW:
      case Token.DELPROP:
      case Token.TYPEOF:
      case Token.VOID:
      case Token.NOT:
      case Token.BITNOT:
      case Token.POS:
      case Token.NEG:    return 14;

      case Token.CALL:
      case Token.GETELEM:
      case Token.GETPROP:
      // Data values
      case Token.ARRAYLIT:
      case Token.ARRAY_PATTERN:
      case Token.DEFAULT_VALUE:
      case Token.EMPTY:  // TODO(johnlenz): remove this.
      case Token.FALSE:
      case Token.FUNCTION:
      case Token.CLASS:
      case Token.NAME:
      case Token.NULL:
      case Token.NUMBER:
      case Token.OBJECTLIT:
      case Token.OBJECT_PATTERN:
      case Token.REGEXP:
      case Token.REST:
      case Token.SPREAD:
      case Token.STRING:
      case Token.STRING_KEY:
      case Token.THIS:
      case Token.SUPER:
      case Token.TRUE:
      case Token.TEMPLATELIT:
      // Tokens from the type declaration AST
      case Token.UNION_TYPE:
        return 15;
      case Token.FUNCTION_TYPE:
        return 16;
      case Token.ARRAY_TYPE:
      case Token.PARAMETERIZED_TYPE:
        return 17;
      case Token.STRING_TYPE:
      case Token.NUMBER_TYPE:
      case Token.BOOLEAN_TYPE:
      case Token.ANY_TYPE:
      case Token.RECORD_TYPE:
      case Token.NULLABLE_TYPE:
      case Token.NAMED_TYPE:
      case Token.UNDEFINED_TYPE:
      case Token.REST_PARAMETER_TYPE:
        return 18;
      case Token.CAST:
        return 19;

      default:
        throw new IllegalStateException("Unknown precedence for "
            + Token.name(type) + " (type " + type + ")");
    }
  }

  static boolean isUndefined(Node n) {
    switch (n.getType()) {
      case Token.VOID:
        return true;
      case Token.NAME:
        return n.getString().equals("undefined");
    }
    return false;
  }

  static boolean isNullOrUndefined(Node n) {
    return n.isNull() || isUndefined(n);
  }

  static final Predicate<Node> IMMUTABLE_PREDICATE = new Predicate<Node>() {
    @Override
    public boolean apply(Node n) {
      return isImmutableValue(n);
    }
  };

  static boolean isImmutableResult(Node n) {
    return allResultsMatch(n, IMMUTABLE_PREDICATE);
  }

  /**
   * Apply the supplied predicate against
   * all possible result Nodes of the expression.
   */
  static boolean allResultsMatch(Node n, Predicate<Node> p) {
    switch (n.getType()) {
      case Token.CAST:
        return allResultsMatch(n.getFirstChild(), p);
      case Token.ASSIGN:
      case Token.COMMA:
        return allResultsMatch(n.getLastChild(), p);
      case Token.AND:
      case Token.OR:
        return allResultsMatch(n.getFirstChild(), p)
            && allResultsMatch(n.getLastChild(), p);
      case Token.HOOK:
        return allResultsMatch(n.getFirstChild().getNext(), p)
            && allResultsMatch(n.getLastChild(), p);
      default:
        return p.apply(n);
    }
  }

  enum ValueType {
    UNDETERMINED,
    NULL,
    VOID,
    NUMBER,
    STRING,
    BOOLEAN
    // TODO(johnlenz): Array,Object,RegExp
  }

  /**
   * Apply the supplied predicate against
   * all possible result Nodes of the expression.
   */
  static ValueType getKnownValueType(Node n) {
    switch (n.getType()) {
      case Token.CAST:
        return getKnownValueType(n.getFirstChild());
      case Token.ASSIGN:
      case Token.COMMA:
        return getKnownValueType(n.getLastChild());
      case Token.AND:
      case Token.OR:
        return and(
            getKnownValueType(n.getFirstChild()),
            getKnownValueType(n.getLastChild()));
      case Token.HOOK:
        return and(
            getKnownValueType(n.getFirstChild().getNext()),
            getKnownValueType(n.getLastChild()));

      case Token.ADD: {
        ValueType last = getKnownValueType(n.getLastChild());
        if (last == ValueType.STRING) {
          return ValueType.STRING;
        }
        ValueType first = getKnownValueType(n.getFirstChild());
        if (first == ValueType.STRING) {
          return ValueType.STRING;
        }

        if (!mayBeString(first) && !mayBeString(last)) {
          // ADD used with compilations of null, undefined, boolean and number always result
          // in numbers.
          return ValueType.NUMBER;
        }

        // There are some pretty weird cases for object types:
        //   {} + [] === "0"
        //   [] + {} ==== "[object Object]"

        return ValueType.UNDETERMINED;
      }

      case Token.NAME:
        String name = n.getString();
        if (name.equals("undefined")) {
          return ValueType.VOID;
        }
        if (name.equals("NaN")) {
          return ValueType.NUMBER;
        }
        if (name.equals("Infinity")) {
          return ValueType.NUMBER;
        }
        return ValueType.UNDETERMINED;

      case Token.BITNOT:
      case Token.BITOR:
      case Token.BITXOR:
      case Token.BITAND:
      case Token.LSH:
      case Token.RSH:
      case Token.URSH:
      case Token.SUB:
      case Token.MUL:
      case Token.MOD:
      case Token.DIV:
      case Token.INC:
      case Token.DEC:
      case Token.POS:
      case Token.NEG:
      case Token.NUMBER:
        return ValueType.NUMBER;

      // Primitives
      case Token.TRUE:
      case Token.FALSE:
      // Comparisons
      case Token.EQ:
      case Token.NE:
      case Token.SHEQ:
      case Token.SHNE:
      case Token.LT:
      case Token.GT:
      case Token.LE:
      case Token.GE:
      // Queries
      case Token.IN:
      case Token.INSTANCEOF:
      // Inversion
      case Token.NOT:
      // delete operator returns a boolean.
      case Token.DELPROP:
        return ValueType.BOOLEAN;

      case Token.TYPEOF:
      case Token.STRING:
        return ValueType.STRING;

      case Token.NULL:
        return ValueType.NULL;

      case Token.VOID:
        return ValueType.VOID;

      default:
        return ValueType.UNDETERMINED;
    }
  }

  static ValueType and(ValueType a, ValueType b) {
    return (a == b) ? a : ValueType.UNDETERMINED;
  }

  /**
   * Returns true if the result of node evaluation is always a number
   */
  static boolean isNumericResult(Node n) {
    return getKnownValueType(n) == ValueType.NUMBER;
  }

  /**
   * @return Whether the result of node evaluation is always a boolean
   */
  static boolean isBooleanResult(Node n) {
    return getKnownValueType(n) == ValueType.BOOLEAN;
  }

  /**
   * @return Whether the result of node evaluation is always a string
   */
  static boolean isStringResult(Node n) {
    return getKnownValueType(n) == ValueType.STRING;
  }

  /**
   * @return Whether the results is possibly a string.
   */
  static boolean mayBeString(Node n) {
    return mayBeString(getKnownValueType(n));
  }

  /**
   * @return Whether the results is possibly a string.
   */
  static boolean mayBeString(ValueType type) {
    switch (type) {
      case BOOLEAN:
      case NULL:
      case NUMBER:
      case VOID:
        return false;
      case UNDETERMINED:
      case STRING:
        return true;
      default:
        throw new IllegalStateException("unexpected");
    }
  }

  /**
   * Returns true if the operator is associative.
   * e.g. (a * b) * c = a * (b * c)
   * Note: "+" is not associative because it is also the concatenation
   * for strings. e.g. "a" + (1 + 2) is not "a" + 1 + 2
   */
  static boolean isAssociative(int type) {
    switch (type) {
      case Token.MUL:
      case Token.AND:
      case Token.OR:
      case Token.BITOR:
      case Token.BITXOR:
      case Token.BITAND:
        return true;
      default:
        return false;
    }
  }

  /**
   * Returns true if the operator is commutative.
   * e.g. (a * b) * c = c * (b * a)
   * Note 1: "+" is not commutative because it is also the concatenation
   * for strings. e.g. "a" + (1 + 2) is not "a" + 1 + 2
   * Note 2: only operations on literals and pure functions are commutative.
   */
  static boolean isCommutative(int type) {
    switch (type) {
      case Token.MUL:
      case Token.BITOR:
      case Token.BITXOR:
      case Token.BITAND:
        return true;
      default:
        return false;
    }
  }

  public static boolean isAssignmentOp(Node n) {
    switch (n.getType()){
      case Token.ASSIGN:
      case Token.ASSIGN_BITOR:
      case Token.ASSIGN_BITXOR:
      case Token.ASSIGN_BITAND:
      case Token.ASSIGN_LSH:
      case Token.ASSIGN_RSH:
      case Token.ASSIGN_URSH:
      case Token.ASSIGN_ADD:
      case Token.ASSIGN_SUB:
      case Token.ASSIGN_MUL:
      case Token.ASSIGN_DIV:
      case Token.ASSIGN_MOD:
        return true;
    }
    return false;
  }

  static int getOpFromAssignmentOp(Node n) {
    switch (n.getType()){
      case Token.ASSIGN_BITOR:
        return Token.BITOR;
      case Token.ASSIGN_BITXOR:
        return Token.BITXOR;
      case Token.ASSIGN_BITAND:
        return Token.BITAND;
      case Token.ASSIGN_LSH:
        return Token.LSH;
      case Token.ASSIGN_RSH:
        return Token.RSH;
      case Token.ASSIGN_URSH:
        return Token.URSH;
      case Token.ASSIGN_ADD:
        return Token.ADD;
      case Token.ASSIGN_SUB:
        return Token.SUB;
      case Token.ASSIGN_MUL:
        return Token.MUL;
      case Token.ASSIGN_DIV:
        return Token.DIV;
      case Token.ASSIGN_MOD:
        return Token.MOD;
    }
    throw new IllegalArgumentException("Not an assignment op:" + n);
  }

  /**
   * Determines if the given node contains a function statement or function
   * expression.
   */
  static boolean containsFunction(Node n) {
    return containsType(n, Token.FUNCTION);
  }

  /**
   * Gets the closest ancestor to the given node of the provided type.
   */
  static Node getEnclosingType(Node n, int type) {
    Node curr = n;
    while (curr.getType() != type) {
      curr = curr.getParent();
      if (curr == null) {
        return curr;
      }
    }
    return curr;
  }

  /**
   * Finds the class member function containing the given node.
   */
  static Node getEnclosingClassMemberFunction(Node n) {
    return getEnclosingType(n, Token.MEMBER_FUNCTION_DEF);
  }

  /**
   * Finds the class containing the given node.
   */
  static Node getEnclosingClass(Node n) {
    return getEnclosingType(n, Token.CLASS);
  }

  /**
   * Finds the function containing the given node.
   */
  public static Node getEnclosingFunction(Node n) {
    return getEnclosingType(n, Token.FUNCTION);
  }

  /**
   * Finds the script containing the given node.
   */
  public static Node getEnclosingScript(Node n) {
    return getEnclosingType(n, Token.SCRIPT);
  }

  public static boolean isInFunction(Node n) {
    return getEnclosingFunction(n) != null;
  }

  public static Node getEnclosingStatement(Node n) {
    Node curr = n;
    while (curr != null && !isStatement(curr)) {
      curr = curr.getParent();
    }
    return curr;
  }

  /**
   * @return The first property in the objlit that matches the key.
   */
  @Nullable static Node getFirstPropMatchingKey(Node objlit, String keyName) {
    Preconditions.checkState(objlit.isObjectLit());
    for (Node keyNode : objlit.children()) {
      if (keyNode.isStringKey() && keyNode.getString().equals(keyName)) {
        return keyNode.getFirstChild();
      }
    }
    return null;
  }

  /**
   * Returns true if the shallow scope contains references to 'this' keyword
   */
  static boolean referencesThis(Node n) {
    Node start = (n.isFunction()) ? n.getLastChild() : n;
    return containsType(start, Token.THIS, MATCH_NOT_FUNCTION);
  }

  /**
   * Returns true if the current scope contains references to the 'super' keyword.
   * Note that if there are classes declared inside the current class, super calls which
   * reference those classes are not reported.
   */
  static boolean referencesSuper(Node n) {
    Node curr = n.getFirstChild();
    while (curr != null) {
      if (containsType(curr, Token.SUPER, MATCH_NOT_CLASS)) {
        return true;
      }
      curr = curr.getNext();
    }
    return false;
  }

  /**
   * Is this a GETPROP or GETELEM node?
   */
  static boolean isGet(Node n) {
    return n.isGetProp() || n.isGetElem();
  }

  /**
   * Is this node the name of a variable being declared?
   *
   * @param n The node
   * @return True if {@code n} is NAME and {@code parent} is VAR
   */
  static boolean isVarDeclaration(Node n) {
    // There is no need to verify that parent != null because a NAME node
    // always has a parent in a valid parse tree.
    return n.isName() && n.getParent().isVar();
  }

  /**
   * Is this node a name declaration?
   *
   * @param n The node
   * @return True if {@code n} is VAR, LET or CONST
   */
  public static boolean isNameDeclaration(Node n) {
    return n.isVar() || n.isLet() || n.isConst();
  }

  /**
   * @param n The node
   * @return True if {@code n} is a VAR, LET or CONST that contains a
   *     destructuring pattern.
   */
  static boolean isDestructuringDeclaration(Node n) {
    if (isNameDeclaration(n)) {
      for (Node c = n.getFirstChild(); c != null; c = c.getNext()) {
        if (c.isArrayPattern() || c.isObjectPattern()) {
          return true;
        }
      }
    }
    return false;
  }

  /**
   * Is this node declaring a block-scoped variable?
   */
  static boolean isLexicalDeclaration(Node n) {
    return n.isLet() || n.isConst()
        || isFunctionDeclaration(n) || isClassDeclaration(n);
  }

  /**
   * For an assignment or variable declaration get the assigned value.
   * @return The value node representing the new value.
   */
  public static Node getAssignedValue(Node n) {
    Preconditions.checkState(n.isName());
    Node parent = n.getParent();
    if (parent.isVar()) {
      return n.getFirstChild();
    } else if (parent.isAssign() && parent.getFirstChild() == n) {
      return n.getNext();
    } else {
      return null;
    }
  }

  /**
   * Is this node an assignment expression statement?
   *
   * @param n The node
   * @return True if {@code n} is EXPR_RESULT and {@code n}'s
   *     first child is ASSIGN
   */
  static boolean isExprAssign(Node n) {
    return n.isExprResult()
        && n.getFirstChild().isAssign();
  }

  /**
   * Is this node a call expression statement?
   *
   * @param n The node
   * @return True if {@code n} is EXPR_RESULT and {@code n}'s
   *     first child is CALL
   */
  static boolean isExprCall(Node n) {
    return n.isExprResult()
        && n.getFirstChild().isCall();
  }

  static boolean isVanillaFor(Node n) {
    return n.isFor() && n.getChildCount() == 4;
  }

  static boolean isEnhancedFor(Node n) {
    return n.isForOf() || isForIn(n);
  }

  /**
   * @return Whether the node represents a FOR-IN loop.
   */
  public static boolean isForIn(Node n) {
    return n.isFor() && n.getChildCount() == 3;
  }

  /**
   * Determines whether the given node is a FOR, DO, or WHILE node.
   */
  static boolean isLoopStructure(Node n) {
    switch (n.getType()) {
      case Token.FOR:
      case Token.FOR_OF:
      case Token.DO:
      case Token.WHILE:
        return true;
      default:
        return false;
    }
  }

  /**
   * @param n The node to inspect.
   * @return If the node, is a FOR, WHILE, or DO, it returns the node for
   * the code BLOCK, null otherwise.
   */
  static Node getLoopCodeBlock(Node n) {
    switch (n.getType()) {
      case Token.FOR:
      case Token.FOR_OF:
      case Token.WHILE:
        return n.getLastChild();
      case Token.DO:
        return n.getFirstChild();
      default:
        return null;
    }
  }

  /**
   * @return Whether the specified node has a loop parent that
   * is within the current scope.
   */
  static boolean isWithinLoop(Node n) {
    for (Node parent : n.getAncestors()) {
      if (NodeUtil.isLoopStructure(parent)) {
        return true;
      }

      if (parent.isFunction()) {
        break;
      }
    }
    return false;
  }

  /**
   * Determines whether the given node is a FOR, DO, WHILE, WITH, or IF node.
   */
  static boolean isControlStructure(Node n) {
    switch (n.getType()) {
      case Token.FOR:
      case Token.FOR_OF:
      case Token.DO:
      case Token.WHILE:
      case Token.WITH:
      case Token.IF:
      case Token.LABEL:
      case Token.TRY:
      case Token.CATCH:
      case Token.SWITCH:
      case Token.CASE:
      case Token.DEFAULT_CASE:
        return true;
      default:
        return false;
    }
  }

  /**
   * Determines whether the given node is code node for FOR, DO,
   * WHILE, WITH, or IF node.
   */
  static boolean isControlStructureCodeBlock(Node parent, Node n) {
    switch (parent.getType()) {
      case Token.FOR:
      case Token.FOR_OF:
      case Token.WHILE:
      case Token.LABEL:
      case Token.WITH:
        return parent.getLastChild() == n;
      case Token.DO:
        return parent.getFirstChild() == n;
      case Token.IF:
        return parent.getFirstChild() != n;
      case Token.TRY:
        return parent.getFirstChild() == n || parent.getLastChild() == n;
      case Token.CATCH:
        return parent.getLastChild() == n;
      case Token.SWITCH:
      case Token.CASE:
        return parent.getFirstChild() != n;
      case Token.DEFAULT_CASE:
        return true;
      default:
        Preconditions.checkState(isControlStructure(parent));
        return false;
    }
  }

  /**
   * Gets the condition of an ON_TRUE / ON_FALSE CFG edge.
   * @param n a node with an outgoing conditional CFG edge
   * @return the condition node or null if the condition is not obviously a node
   */
  static Node getConditionExpression(Node n) {
    switch (n.getType()) {
      case Token.IF:
      case Token.WHILE:
        return n.getFirstChild();
      case Token.DO:
        return n.getLastChild();
      case Token.FOR:
        switch (n.getChildCount()) {
          case 3:
            return null;
          case 4:
            return n.getFirstChild().getNext();
        }
        throw new IllegalArgumentException("malformed 'for' statement " + n);
      case Token.CASE:
        return null;
    }
    throw new IllegalArgumentException(n + " does not have a condition.");
  }

  /**
   * @return Whether the node is of a type that contain other statements.
   */
  static boolean isStatementBlock(Node n) {
    return n.isScript() || n.isBlock();
  }

  /**
   * A block scope is created by a non-synthetic block node, a for loop node,
   * or a for-of loop node.
   *
   * <p>Note: for functions, we use two separate scopes for parameters and
   * declarations in the body. We need to make sure default parameters cannot
   * reference var / function declarations in the body.
   *
   * @return Whether the node creates a block scope.
   */
  static boolean createsBlockScope(Node n) {
    switch (n.getType()) {
      case Token.BLOCK:
        Node parent = n.getParent();
        if (parent == null || parent.isCatch()) {
          return false;
        }
        Node child = n.getFirstChild();
        return child != null && !child.isScript();
      case Token.FOR:
      case Token.FOR_OF:
        return true;
    }
    return false;
  }

  /**
   * @return Whether the node is used as a statement.
   */
  static boolean isStatement(Node n) {
    return isStatementParent(n.getParent());
  }

  static boolean isStatementParent(Node parent) {
    // It is not possible to determine definitely if a node is a statement
    // or not if it is not part of the AST.  A FUNCTION node can be
    // either part of an expression or a statement.
    Preconditions.checkState(parent != null);
    switch (parent.getType()) {
      case Token.SCRIPT:
      case Token.BLOCK:
      case Token.LABEL:
        return true;
      default:
        return false;
    }
  }

  /** Whether the node is part of a switch statement. */
  static boolean isSwitchCase(Node n) {
    return n.isCase() || n.isDefaultCase();
  }

  /**
   * @return Whether the name is a reference to a variable, function or
   *       function parameter (not a label or a empty function expression name).
   */
  static boolean isReferenceName(Node n) {
    return n.isName() && !n.getString().isEmpty();
  }

  /** Whether the child node is the FINALLY block of a try. */
  static boolean isTryFinallyNode(Node parent, Node child) {
    return parent.isTry() && parent.getChildCount() == 3
        && child == parent.getLastChild();
  }

  /** Whether the node is a CATCH container BLOCK. */
  static boolean isTryCatchNodeContainer(Node n) {
    Node parent = n.getParent();
    return parent.isTry()
        && parent.getFirstChild().getNext() == n;
  }

  /** Safely remove children while maintaining a valid node structure. */
  static void removeChild(Node parent, Node node) {
    if (isTryFinallyNode(parent, node)) {
      if (NodeUtil.hasCatchHandler(getCatchBlock(parent))) {
        // A finally can only be removed if there is a catch.
        parent.removeChild(node);
      } else {
        // Otherwise, only its children can be removed.
        node.detachChildren();
      }
    } else if (node.isCatch()) {
      // The CATCH can can only be removed if there is a finally clause.
      Node tryNode = node.getParent().getParent();
      Preconditions.checkState(NodeUtil.hasFinally(tryNode));
      node.detachFromParent();
    } else if (isTryCatchNodeContainer(node)) {
      // The container node itself can't be removed, but the contained CATCH
      // can if there is a 'finally' clause
      Node tryNode = node.getParent();
      Preconditions.checkState(NodeUtil.hasFinally(tryNode));
      node.detachChildren();
    } else if (node.isBlock()) {
      // Simply empty the block.  This maintains source location and
      // "synthetic"-ness.
      node.detachChildren();
    } else if (isStatementBlock(parent)
        || isSwitchCase(node)) {
      // A statement in a block can simply be removed.
      parent.removeChild(node);
    } else if (parent.isVar()) {
      if (parent.hasMoreThanOneChild()) {
        parent.removeChild(node);
      } else {
        // Remove the node from the parent, so it can be reused.
        parent.removeChild(node);
        // This would leave an empty VAR, remove the VAR itself.
        removeChild(parent.getParent(), parent);
      }
    } else if (parent.isLabel()
        && node == parent.getLastChild()) {
      // Remove the node from the parent, so it can be reused.
      parent.removeChild(node);
      // A LABEL without children can not be referred to, remove it.
      removeChild(parent.getParent(), parent);
    } else if (parent.isFor()
        && parent.getChildCount() == 4) {
      // Only Token.FOR can have an Token.EMPTY other control structure
      // need something for the condition. Others need to be replaced
      // or the structure removed.
      parent.replaceChild(node, IR.empty());
    } else {
      throw new IllegalStateException("Invalid attempt to remove node: " + node + " of " + parent);
    }
  }

  /**
   * Add a finally block if one does not exist.
   */
  static void maybeAddFinally(Node tryNode) {
    Preconditions.checkState(tryNode.isTry());
    if (!NodeUtil.hasFinally(tryNode)) {
      tryNode.addChildrenToBack(IR.block().srcref(tryNode));
    }
  }

  /**
   * Merge a block with its parent block.
   * @return Whether the block was removed.
   */
  static boolean tryMergeBlock(Node block) {
    Preconditions.checkState(block.isBlock());
    Node parent = block.getParent();
    // Try to remove the block if its parent is a block/script or if its
    // parent is label and it has exactly one child.
    if (isStatementBlock(parent)) {
      Node previous = block;
      while (block.hasChildren()) {
        Node child = block.removeFirstChild();
        parent.addChildAfter(child, previous);
        previous = child;
      }
      parent.removeChild(block);
      return true;
    } else {
      return false;
    }
  }

  /**
   * @param node A node
   * @return Whether the call is a NEW or CALL node.
   */
  static boolean isCallOrNew(Node node) {
    return node.isCall() || node.isNew();
  }

  /**
   * Return a BLOCK node for the given FUNCTION node.
   */
  static Node getFunctionBody(Node fn) {
    Preconditions.checkArgument(fn.isFunction());
    return fn.getLastChild();
  }

  /**
   * Is this node a function declaration? A function declaration is a function
   * that has a name that is added to the current scope (i.e. a function that
   * is not part of a expression; see {@link #isFunctionExpression}).
   */
  static boolean isFunctionDeclaration(Node n) {
    return n.isFunction() && isStatement(n);
  }

  /**
   * see {@link #isClassDeclaration}
   */
  static boolean isClassDeclaration(Node n) {
    return n.isClass() && isStatement(n);
  }

  /**
   * Is this node a hoisted function declaration? A function declaration in the
   * scope root is hoisted to the top of the scope.
   * See {@link #isFunctionDeclaration}).
   */
  public static boolean isHoistedFunctionDeclaration(Node n) {
    return isFunctionDeclaration(n)
        && (n.getParent().isScript()
            || n.getParent().getParent().isFunction());
  }

  static boolean isBlockScopedFunctionDeclaration(Node n) {
    if (!isFunctionDeclaration(n)) {
      return false;
    }
    Node current = n.getParent();
    while (current != null) {
      if (current.isBlock()) {
        return !current.getParent().isFunction();
      } else if (current.isFunction() || current.isScript()) {
        return false;
      } else {
        Preconditions.checkArgument(current.isLabel());
        current = current.getParent();
      }
    }
    return false;
  }

  /**
   * Is a FUNCTION node an function expression? An function expression is one
   * that has either no name or a name that is not added to the current scope.
   *
   * <p>Some examples of function expressions:
   * <pre>
   * (function () {})
   * (function f() {})()
   * [ function f() {} ]
   * var f = function f() {};
   * for (function f() {};;) {}
   * </pre>
   *
   * <p>Some examples of functions that are <em>not</em> expressions:
   * <pre>
   * function f() {}
   * if (x); else function f() {}
   * for (;;) { function f() {} }
   * </pre>
   *
   * @param n A node
   * @return Whether n is a function used within an expression.
   */
  static boolean isFunctionExpression(Node n) {
    return n.isFunction() && !isStatement(n);
  }

  /**
   * see {@link #isFunctionExpression}
   *
   * @param n A node
   * @return Whether n is a class used within an expression.
   */
  static boolean isClassExpression(Node n) {
    return n.isClass() && !isStatement(n);
  }

  /**
   * Returns whether this is a bleeding function (an anonymous named function
   * that bleeds into the inner scope).
   */
  static boolean isBleedingFunctionName(Node n) {
    return n.isName() && !n.getString().isEmpty() &&
        isFunctionExpression(n.getParent());
  }

  /**
   * Determines if a node is a function expression that has an empty body.
   *
   * @param node a node
   * @return whether the given node is a function expression that is empty
   */
  static boolean isEmptyFunctionExpression(Node node) {
    return isFunctionExpression(node) && isEmptyBlock(node.getLastChild());
  }

  /**
   * Determines if a function takes a variable number of arguments by
   * looking for references to the "arguments" var_args object.
   */
  static boolean isVarArgsFunction(Node function) {
    // TODO(johnlenz): rename this function
    Preconditions.checkArgument(function.isFunction());
    return isNameReferenced(
        function.getLastChild(),
        "arguments",
        MATCH_NOT_FUNCTION);
  }

  /**
   * @return Whether node is a call to methodName.
   *    a.f(...)
   *    a['f'](...)
   */
  static boolean isObjectCallMethod(Node callNode, String methodName) {
    if (callNode.isCall()) {
      Node functionIndentifyingExpression = callNode.getFirstChild();
      if (isGet(functionIndentifyingExpression)) {
        Node last = functionIndentifyingExpression.getLastChild();
        if (last != null && last.isString()) {
          String propName = last.getString();
          return (propName.equals(methodName));
        }
      }
    }
    return false;
  }


  /**
   * @return Whether the callNode represents an expression in the form of:
   *    x.call(...)
   *    x['call'](...)
   */
  static boolean isFunctionObjectCall(Node callNode) {
    return isObjectCallMethod(callNode, "call");
  }

  /**
   * @return Whether the callNode represents an expression in the form of:
   *    x.apply(...)
   *    x['apply'](...)
   */
  static boolean isFunctionObjectApply(Node callNode) {
    return isObjectCallMethod(callNode, "apply");
  }

  static boolean isGoogBind(Node n) {
    return n.isGetProp() && n.matchesQualifiedName("goog.bind");
  }

  static boolean isGoogPartial(Node n) {
    return n.isGetProp() && n.matchesQualifiedName("goog.partial");
  }

  // Does not use type info. For example, it returns false for f.bind(...)
  // because it cannot know whether f is a function.
  static boolean isFunctionBind(Node expr) {
    if (!expr.isGetProp()) {
      return false;
    }
    if (isGoogBind(expr) || isGoogPartial(expr)) {
      return true;
    }
    return expr.getFirstChild().isFunction()
        && expr.getLastChild().getString().equals("bind");
  }

  /**
   * Determines whether this node is strictly on the left hand side of an assign
   * or var initialization. Notably, this does not include all L-values, only
   * statements where the node is used only as an L-value.
   *
   * @param n The node
   * @param parent Parent of the node
   * @return True if n is the left hand of an assign
   */
  static boolean isVarOrSimpleAssignLhs(Node n, Node parent) {
    return (parent.isAssign() && parent.getFirstChild() == n) ||
           parent.isVar();
  }

  /**
   * Determines whether this node is used as an L-value. Notice that sometimes
   * names are used as both L-values and R-values.
   *
   * <p>We treat "var x;" as a pseudo-L-value, which kind of makes sense if you
   * treat it as "assignment to 'undefined' at the top of the scope". But if
   * we're honest with ourselves, it doesn't make sense, and we only do this
   * because it makes sense to treat this as syntactically similar to
   * "var x = 0;".
   *
   * @param n The node
   * @return True if n is an L-value.
   */
  public static boolean isLValue(Node n) {
    Preconditions.checkArgument(n.isName() || n.isGetProp() ||
        n.isGetElem());
    Node parent = n.getParent();
    if (parent == null) {
      return false;
    }
    return (NodeUtil.isAssignmentOp(parent) && parent.getFirstChild() == n)
        || (NodeUtil.isForIn(parent) && parent.getFirstChild() == n)
        || parent.isVar() || parent.isLet() || parent.isConst()
        || (parent.isFunction() && parent.getFirstChild() == n)
        || parent.isDec()
        || parent.isInc()
        || parent.isParamList()
        || parent.isCatch();
  }

  /**
   * Determines whether a node represents an object literal key
   * (e.g. key1 in {key1: value1, key2: value2}).
   *
   * @param node A node
   */
  static boolean isObjectLitKey(Node node) {
    switch (node.getType()) {
      case Token.STRING_KEY:
      case Token.GETTER_DEF:
      case Token.SETTER_DEF:
        return true;
    }
    return false;
  }

  /**
   * Get the name of an object literal key.
   *
   * @param key A node
   */
  static String getObjectLitKeyName(Node key) {
    switch (key.getType()) {
      case Token.STRING_KEY:
      case Token.GETTER_DEF:
      case Token.SETTER_DEF:
        return key.getString();
    }
    throw new IllegalStateException("Unexpected node type: " + key);
  }

  /**
   * Determines whether a node represents an object literal get or set key
   * (e.g. key1 in {get key1() {}, set key2(a){}).
   *
   * @param node A node
   */
  static boolean isGetOrSetKey(Node node) {
    switch (node.getType()) {
      case Token.GETTER_DEF:
      case Token.SETTER_DEF:
        return true;
    }
    return false;
  }

  /**
   * Converts an operator's token value (see {@link Token}) to a string
   * representation.
   *
   * @param operator the operator's token value to convert
   * @return the string representation or {@code null} if the token value is
   * not an operator
   */
  public static String opToStr(int operator) {
    switch (operator) {
      case Token.BITOR: return "|";
      case Token.OR: return "||";
      case Token.BITXOR: return "^";
      case Token.AND: return "&&";
      case Token.BITAND: return "&";
      case Token.SHEQ: return "===";
      case Token.EQ: return "==";
      case Token.NOT: return "!";
      case Token.NE: return "!=";
      case Token.SHNE: return "!==";
      case Token.LSH: return "<<";
      case Token.IN: return "in";
      case Token.LE: return "<=";
      case Token.LT: return "<";
      case Token.URSH: return ">>>";
      case Token.RSH: return ">>";
      case Token.GE: return ">=";
      case Token.GT: return ">";
      case Token.MUL: return "*";
      case Token.DIV: return "/";
      case Token.MOD: return "%";
      case Token.BITNOT: return "~";
      case Token.ADD: return "+";
      case Token.SUB: return "-";
      case Token.POS: return "+";
      case Token.NEG: return "-";
      case Token.ASSIGN: return "=";
      case Token.ASSIGN_BITOR: return "|=";
      case Token.ASSIGN_BITXOR: return "^=";
      case Token.ASSIGN_BITAND: return "&=";
      case Token.ASSIGN_LSH: return "<<=";
      case Token.ASSIGN_RSH: return ">>=";
      case Token.ASSIGN_URSH: return ">>>=";
      case Token.ASSIGN_ADD: return "+=";
      case Token.ASSIGN_SUB: return "-=";
      case Token.ASSIGN_MUL: return "*=";
      case Token.ASSIGN_DIV: return "/=";
      case Token.ASSIGN_MOD: return "%=";
      case Token.VOID: return "void";
      case Token.TYPEOF: return "typeof";
      case Token.INSTANCEOF: return "instanceof";
      default: return null;
    }
  }

  /**
   * Converts an operator's token value (see {@link Token}) to a string
   * representation or fails.
   *
   * @param operator the operator's token value to convert
   * @return the string representation
   * @throws Error if the token value is not an operator
   */
  static String opToStrNoFail(int operator) {
    String res = opToStr(operator);
    if (res == null) {
      throw new Error("Unknown op " + operator + ": " +
                      Token.name(operator));
    }
    return res;
  }

  /**
   * @return true if n or any of its children are of the specified type
   */
  static boolean containsType(Node node,
                              int type,
                              Predicate<Node> traverseChildrenPred) {
    return has(node, new MatchNodeType(type), traverseChildrenPred);
  }

  /**
   * @return true if n or any of its children are of the specified type
   */
  static boolean containsType(Node node, int type) {
    return containsType(node, type, Predicates.<Node>alwaysTrue());
  }


  /**
   * Given a node tree, finds all the VAR declarations in that tree that are
   * not in an inner scope. Then adds a new VAR node at the top of the current
   * scope that redeclares them, if necessary.
   */
  static void redeclareVarsInsideBranch(Node branch) {
    Collection<Node> vars = getVarsDeclaredInBranch(branch);
    if (vars.isEmpty()) {
      return;
    }

    Node parent = getAddingRoot(branch);
    for (Node nameNode : vars) {
      Node var = IR.var(
          IR.name(nameNode.getString())
              .srcref(nameNode))
          .srcref(nameNode);
      copyNameAnnotations(nameNode, var.getFirstChild());
      parent.addChildToFront(var);
    }
  }

  /**
   * Copy any annotations that follow a named value.
   * @param source
   * @param destination
   */
  static void copyNameAnnotations(Node source, Node destination) {
    if (source.getBooleanProp(Node.IS_CONSTANT_NAME)) {
      destination.putBooleanProp(Node.IS_CONSTANT_NAME, true);
    }
  }

  /**
   * Gets a Node at the top of the current scope where we can add new var
   * declarations as children.
   */
  private static Node getAddingRoot(Node n) {
    Node addingRoot = null;
    Node ancestor = n;
    while (null != (ancestor = ancestor.getParent())) {
      int type = ancestor.getType();
      if (type == Token.SCRIPT) {
        addingRoot = ancestor;
        break;
      } else if (type == Token.FUNCTION) {
        addingRoot = ancestor.getLastChild();
        break;
      }
    }

    // make sure that the adding root looks ok
    Preconditions.checkState(addingRoot.isBlock() ||
        addingRoot.isScript());
    Preconditions.checkState(addingRoot.getFirstChild() == null ||
        !addingRoot.getFirstChild().isScript());
    return addingRoot;
  }

  /**
   * Creates a node representing a qualified name.
   *
   * @param name A qualified name (e.g. "foo" or "foo.bar.baz")
   * @return A NAME or GETPROP node
   */
  public static Node newQName(AbstractCompiler compiler, String name) {
    int endPos = name.indexOf('.');
    if (endPos == -1) {
      return newName(compiler, name);
    }
    Node node;
    String nodeName = name.substring(0, endPos);
    if ("this".equals(nodeName)) {
      node = IR.thisNode();
    } else {
      node = newName(compiler, nodeName);
    }
    int startPos;
    do {
      startPos = endPos + 1;
      endPos = name.indexOf('.', startPos);
      String part = (endPos == -1
                     ? name.substring(startPos)
                     : name.substring(startPos, endPos));
      Node propNode = IR.string(part);
      if (compiler.getCodingConvention().isConstantKey(part)) {
        propNode.putBooleanProp(Node.IS_CONSTANT_NAME, true);
      }
      node = IR.getprop(node, propNode);
    } while (endPos != -1);

    return node;
  }

  /**
   * Creates a property access on the {@code context} tree.
   */
  public static Node newPropertyAccess(AbstractCompiler compiler, Node context, String name) {
    Node propNode = IR.getprop(context, IR.string(name));
    if (compiler.getCodingConvention().isConstantKey(name)) {
      propNode.putBooleanProp(Node.IS_CONSTANT_NAME, true);
    }
    return propNode;
  }

  /**
   * Creates a node representing a qualified name.
   *
   * @param name A qualified name (e.g. "foo" or "foo.bar.baz")
   * @return A VAR node, or an EXPR_RESULT node containing an ASSIGN or NAME node.
   */
  public static Node newQNameDeclaration(
      AbstractCompiler compiler, String name, Node value, JSDocInfo info) {
    Node result;
    Node nameNode = newQName(compiler, name);
    if (nameNode.isName()) {
      result = IR.var(nameNode, value);
      result.setJSDocInfo(info);
    } else if (value != null) {
      result = IR.exprResult(IR.assign(nameNode, value));
      result.getFirstChild().setJSDocInfo(info);
    } else {
      result = IR.exprResult(nameNode);
      result.getFirstChild().setJSDocInfo(info);
    }
    return result;
  }

  /**
   * Creates a node representing a qualified name, copying over the source
   * location information from the basis node and assigning the given original
   * name to the node.
   *
   * @param name A qualified name (e.g. "foo" or "foo.bar.baz")
   * @param basisNode The node that represents the name as currently found in
   *     the AST.
   * @param originalName The original name of the item being represented by the
   *     NAME node. Used for debugging information.
   *
   * @return A NAME or GETPROP node
   */
  static Node newQName(
      AbstractCompiler compiler, String name, Node basisNode,
      String originalName) {
    Node node = newQName(compiler, name);
    setDebugInformation(node, basisNode, originalName);
    return node;
  }

  /**
   * Gets the root node of a qualified name. Must be either NAME or THIS.
   */
  static Node getRootOfQualifiedName(Node qName) {
    for (Node current = qName; true;
         current = current.getFirstChild()) {
      if (current.isName() || current.isThis()) {
        return current;
      }
      Preconditions.checkState(current.isGetProp());
    }
  }

  /**
   * Sets the debug information (source file info and original name)
   * on the given node.
   *
   * @param node The node on which to set the debug information.
   * @param basisNode The basis node from which to copy the source file info.
   * @param originalName The original name of the node.
   */
  static void setDebugInformation(Node node, Node basisNode,
                                  String originalName) {
    node.copyInformationFromForTree(basisNode);
    node.putProp(Node.ORIGINALNAME_PROP, originalName);
  }

  private static Node newName(AbstractCompiler compiler, String name) {
    Node nameNode = IR.name(name);
    if (compiler.getCodingConvention().isConstant(name)) {
      nameNode.putBooleanProp(Node.IS_CONSTANT_NAME, true);
    }
    return nameNode;
  }

  /**
   * Creates a new node representing an *existing* name, copying over the source
   * location information from the basis node.
   *
   * @param name The name for the new NAME node.
   * @param srcref The node that represents the name as currently found in
   *     the AST.
   *
   * @return The node created.
   */
  static Node newName(AbstractCompiler compiler, String name, Node srcref) {
    return newName(compiler, name).srcref(srcref);
  }

  /**
   * Creates a new node representing an *existing* name, copying over the source
   * location information from the basis node and assigning the given original
   * name to the node.
   *
   * @param name The name for the new NAME node.
   * @param basisNode The node that represents the name as currently found in
   *     the AST.
   * @param originalName The original name of the item being represented by the
   *     NAME node. Used for debugging information.
   *
   * @return The node created.
   */
  static Node newName(
      AbstractCompiler compiler, String name,
      Node basisNode, String originalName) {
    Node nameNode = newName(compiler, name, basisNode);
    nameNode.putProp(Node.ORIGINALNAME_PROP, originalName);
    return nameNode;
  }

  /** Test if all characters in the string are in the Basic Latin (aka ASCII)
   * character set - that they have UTF-16 values equal to or below 0x7f.
   * This check can find which identifiers with Unicode characters need to be
   * escaped in order to allow resulting files to be processed by non-Unicode
   * aware UNIX tools and editors.
   * *
   * See http://en.wikipedia.org/wiki/Latin_characters_in_Unicode
   * for more on Basic Latin.
   *
   * @param s The string to be checked for ASCII-goodness.
   *
   * @return True if all characters in the string are in Basic Latin set.
   */
  static boolean isLatin(String s) {
    int len = s.length();
    for (int index = 0; index < len; index++) {
      char c = s.charAt(index);
      if (c > LARGEST_BASIC_LATIN) {
        return false;
      }
    }
    return true;
  }

  /**
   * Determines whether the given name is a valid variable name.
   */
  static boolean isValidSimpleName(String name) {
    return TokenStream.isJSIdentifier(name) &&
        !TokenStream.isKeyword(name) &&
        // no Unicode escaped characters - some browsers are less tolerant
        // of Unicode characters that might be valid according to the
        // language spec.
        // Note that by this point, Unicode escapes have been converted
        // to UTF-16 characters, so we're only searching for character
        // values, not escapes.
        isLatin(name);
  }

  @Deprecated
  public static boolean isValidQualifiedName(String name) {
    return isValidQualifiedName(LanguageMode.ECMASCRIPT3, name);
  }


  /**
   * Determines whether the given name is a valid qualified name.
   */
  public static boolean isValidQualifiedName(LanguageMode mode, String name) {
    if (name.endsWith(".") || name.startsWith(".")) {
      return false;
    }

    List<String> parts = Splitter.on('.').splitToList(name);
    for (String part : parts) {
      if (!isValidPropertyName(mode, part)) {
        return false;
      }
    }
    return isValidSimpleName(parts.get(0));
  }

  @Deprecated
  static boolean isValidPropertyName(String name) {
    return isValidSimpleName(name);
  }

  /**
   * Determines whether the given name can appear on the right side of
   * the dot operator. Many properties (like reserved words) cannot, in ES3.
   */
  static boolean isValidPropertyName(LanguageMode mode, String name) {
    if (isValidSimpleName(name)) {
      return true;
    } else {
      return mode.isEs5OrHigher() && TokenStream.isKeyword(name);
    }
  }

  private static class VarCollector implements Visitor {
    final Map<String, Node> vars = new LinkedHashMap<>();

    @Override
    public void visit(Node n) {
      if (n.isName()) {
        Node parent = n.getParent();
        if (parent != null && parent.isVar()) {
          String name = n.getString();
          if (!vars.containsKey(name)) {
            vars.put(name, n);
          }
        }
      }
    }
  }

  /**
   * Retrieves vars declared in the current node tree, excluding descent scopes.
   */
  static Collection<Node> getVarsDeclaredInBranch(Node root) {
    VarCollector collector = new VarCollector();
    visitPreOrder(
        root,
        collector,
        MATCH_NOT_FUNCTION);
    return collector.vars.values();
  }

  /**
   * @return {@code true} if the node an assignment to a prototype property of
   *     some constructor.
   */
  public static boolean isPrototypePropertyDeclaration(Node n) {
    return isExprAssign(n) &&
        isPrototypeProperty(n.getFirstChild().getFirstChild());
  }

  /**
   * @return Whether the node represents a qualified prototype property.
   */
  static boolean isPrototypeProperty(Node n) {
    if (!n.isGetProp()) {
      return false;
    }
    n = n.getFirstChild();
    while (n.isGetProp()) {
      if (n.getLastChild().getString().equals("prototype")) {
        return n.isQualifiedName();
      }
      n = n.getFirstChild();
    }
    return false;
  }

  /**
   * @return Whether the node represents a prototype method.
   */
  static boolean isPrototypeMethod(Node n) {
    if (!n.isFunction()) {
      return false;
    }
    Node assignNode = n.getParent();
    if (!assignNode.isAssign()) {
      return false;
    }
    return isPrototypePropertyDeclaration(assignNode.getParent());
  }

  static boolean isPrototypeAssignment(Node getProp) {
    if (!getProp.isGetProp()) {
      return false;
    }
    Node parent = getProp.getParent();
    return parent.isAssign() && parent.getFirstChild() == getProp
        && parent.getFirstChild().getLastChild().getString().equals("prototype")
        && parent.getLastChild().isObjectLit();
  }

  /**
   * Determines whether this node is testing for the existence of a property.
   * If true, we will not emit warnings about a missing property.
   *
   * @param propAccess The GETPROP or GETELEM being tested.
   */
  static boolean isPropertyTest(AbstractCompiler compiler, Node propAccess) {
    Node parent = propAccess.getParent();
    switch (parent.getType()) {
      case Token.CALL:
        return parent.getFirstChild() != propAccess
            && compiler.getCodingConvention().isPropertyTestFunction(parent);

      case Token.IF:
      case Token.WHILE:
      case Token.DO:
      case Token.FOR:
        return NodeUtil.getConditionExpression(parent) == propAccess;

      case Token.INSTANCEOF:
      case Token.TYPEOF:
        return true;

      case Token.AND:
      case Token.HOOK:
        return parent.getFirstChild() == propAccess;

      case Token.NOT:
        return parent.getParent().isOr()
            && parent.getParent().getFirstChild() == parent;

      case Token.CAST:
        return isPropertyTest(compiler, parent);
    }
    return false;
  }

  /**
   * @return The class name part of a qualified prototype name.
   */
  static Node getPrototypeClassName(Node qName) {
    Node cur = qName;
    while (cur.isGetProp()) {
      if (cur.getLastChild().getString().equals("prototype")) {
        return cur.getFirstChild();
      } else {
        cur = cur.getFirstChild();
      }
    }
    return null;
  }

  /**
   * @return The string property name part of a qualified prototype name.
   */
  static String getPrototypePropertyName(Node qName) {
    String qNameStr = qName.getQualifiedName();
    int prototypeIdx = qNameStr.lastIndexOf(".prototype.");
    int memberIndex = prototypeIdx + ".prototype".length() + 1;
    return qNameStr.substring(memberIndex);
  }

  /**
   * Create a node for an empty result expression:
   *   "void 0"
   */
  static Node newUndefinedNode(Node srcReferenceNode) {
    Node node = IR.voidNode(IR.number(0));
    if (srcReferenceNode != null) {
        node.copyInformationFromForTree(srcReferenceNode);
    }
    return node;
  }

  /**
   * Create a VAR node containing the given name and initial value expression.
   */
  static Node newVarNode(String name, Node value) {
    Node nodeName = IR.name(name);
    if (value != null) {
      Preconditions.checkState(value.getNext() == null);
      nodeName.addChildToBack(value);
      nodeName.srcref(value);
    }
    Node var = IR.var(nodeName).srcref(nodeName);

    return var;
  }

  /**
   * A predicate for matching name nodes with the specified node.
   */
  private static class MatchNameNode implements Predicate<Node>{
    final String name;

    MatchNameNode(String name){
      this.name = name;
    }

    @Override
    public boolean apply(Node n) {
      return n.isName() && n.getString().equals(name);
    }
  }

  /**
   * A predicate for matching nodes with the specified type.
   */
  static class MatchNodeType implements Predicate<Node>{
    final int type;

    MatchNodeType(int type){
      this.type = type;
    }

    @Override
    public boolean apply(Node n) {
      return n.getType() == type;
    }
  }


  /**
   * A predicate for matching var or function declarations.
   */
  static class MatchDeclaration implements Predicate<Node> {
    @Override
    public boolean apply(Node n) {
      return isFunctionDeclaration(n) || n.isVar();
    }
  }

  /**
   * A predicate for matching anything except function nodes.
   */
  private static class MatchNotFunction implements Predicate<Node>{
    @Override
    public boolean apply(Node n) {
      return !n.isFunction();
    }
  }

  /**
   * A predicate for matching anything except class nodes.
   */
  private static class MatchNotClass implements Predicate<Node> {
    @Override
    public boolean apply(Node n) {
      return !n.isClass();
    }
  }

  static final Predicate<Node> MATCH_NOT_FUNCTION = new MatchNotFunction();

  static final Predicate<Node> MATCH_NOT_CLASS = new MatchNotClass();

  /**
   * A predicate for matching statements without exiting the current scope.
   */
  static class MatchShallowStatement implements Predicate<Node>{
    @Override
    public boolean apply(Node n) {
      Node parent = n.getParent();
      return n.isBlock()
          || (!n.isFunction() && (parent == null
              || isControlStructure(parent)
              || isStatementBlock(parent)));
    }
  }

  /**
   * Finds the number of times a type is referenced within the node tree.
   */
  static int getNodeTypeReferenceCount(
      Node node, int type, Predicate<Node> traverseChildrenPred) {
    return getCount(node, new MatchNodeType(type), traverseChildrenPred);
  }

  /**
   * Whether a simple name is referenced within the node tree.
   */
  static boolean isNameReferenced(Node node,
                                  String name,
                                  Predicate<Node> traverseChildrenPred) {
    return has(node, new MatchNameNode(name), traverseChildrenPred);
  }

  /**
   * Whether a simple name is referenced within the node tree.
   */
  static boolean isNameReferenced(Node node, String name) {
    return isNameReferenced(node, name, Predicates.<Node>alwaysTrue());
  }

  /**
   * Finds the number of times a simple name is referenced within the node tree.
   */
  static int getNameReferenceCount(Node node, String name) {
    return getCount(
        node, new MatchNameNode(name), Predicates.<Node>alwaysTrue());
  }

  /**
   * @return Whether the predicate is true for the node or any of its children.
   */
  static boolean has(Node node,
                     Predicate<Node> pred,
                     Predicate<Node> traverseChildrenPred) {
    if (pred.apply(node)) {
      return true;
    }

    if (!traverseChildrenPred.apply(node)) {
      return false;
    }

    for (Node c = node.getFirstChild(); c != null; c = c.getNext()) {
      if (has(c, pred, traverseChildrenPred)) {
        return true;
      }
    }

    return false;
  }

  /**
   * @return The number of times the the predicate is true for the node
   * or any of its children.
   */
  static int getCount(
      Node n, Predicate<Node> pred, Predicate<Node> traverseChildrenPred) {
    int total = 0;

    if (pred.apply(n)) {
      total++;
    }

    if (traverseChildrenPred.apply(n)) {
      for (Node c = n.getFirstChild(); c != null; c = c.getNext()) {
        total += getCount(c, pred, traverseChildrenPred);
      }
    }

    return total;
  }

  /**
   * Interface for use with the visit method.
   * @see #visit
   */
  public static interface Visitor {
    void visit(Node node);
  }

  /**
   * A pre-order traversal, calling Visitor.visit for each child matching
   * the predicate.
   */
  public static void visitPreOrder(Node node,
                     Visitor visitor,
                     Predicate<Node> traverseChildrenPred) {
    visitor.visit(node);

    if (traverseChildrenPred.apply(node)) {
      for (Node c = node.getFirstChild(); c != null; c = c.getNext()) {
        visitPreOrder(c, visitor, traverseChildrenPred);
      }
    }
  }

  /**
   * A post-order traversal, calling Visitor.visit for each child matching
   * the predicate.
   */
  static void visitPostOrder(Node node,
                     Visitor visitor,
                     Predicate<Node> traverseChildrenPred) {
    if (traverseChildrenPred.apply(node)) {
      for (Node c = node.getFirstChild(); c != null; c = c.getNext()) {
        visitPostOrder(c, visitor, traverseChildrenPred);
      }
    }

    visitor.visit(node);
  }

  /**
   * @return Whether a TRY node has a finally block.
   */
  static boolean hasFinally(Node n) {
    Preconditions.checkArgument(n.isTry());
    return n.getChildCount() == 3;
  }

  /**
   * @return The BLOCK node containing the CATCH node (if any)
   * of a TRY.
   */
  static Node getCatchBlock(Node n) {
    Preconditions.checkArgument(n.isTry());
    return n.getFirstChild().getNext();
  }

  /**
   * @return Whether BLOCK (from a TRY node) contains a CATCH.
   * @see NodeUtil#getCatchBlock
   */
  static boolean hasCatchHandler(Node n) {
    Preconditions.checkArgument(n.isBlock());
    return n.hasChildren() && n.getFirstChild().isCatch();
  }

  /**
    * @param fnNode The function.
    * @return The Node containing the Function parameters.
    */
  public static Node getFunctionParameters(Node fnNode) {
    // Function NODE: [ FUNCTION -> NAME, LP -> ARG1, ARG2, ... ]
    Preconditions.checkArgument(fnNode.isFunction());
    return fnNode.getFirstChild().getNext();
  }

  static boolean hasConstAnnotation(Node node) {
    JSDocInfo jsdoc = getBestJSDocInfo(node);
    return jsdoc != null && jsdoc.isConstant() && !jsdoc.isDefine();
  }

  static boolean isConstantVar(Node node, Scope scope) {
    if (isConstantName(node)) {
      return true;
    }

    if (!node.isName() || scope == null) {
      return false;
    }

    Var var = scope.getVar(node.getString());
    return var != null && (var.isInferredConst() || var.isConst());
  }

  /**
   * <p>Determines whether a variable is constant:
   * <ol>
   * <li>In Normalize, any name that matches the
   *     {@link CodingConvention#isConstant(String)} is annotated with an
   *     IS_CONSTANT_NAME property.
   * </ol>
   *
   * @param node A NAME or STRING node
   * @return True if a name node represents a constant variable
   */
  static boolean isConstantName(Node node) {
    return node.getBooleanProp(Node.IS_CONSTANT_NAME);
  }

  /** Whether the given name is constant by coding convention. */
  static boolean isConstantByConvention(
      CodingConvention convention, Node node) {
    Node parent = node.getParent();
    if (parent.isGetProp() && node == parent.getLastChild()) {
      return convention.isConstantKey(node.getString());
    } else if (isObjectLitKey(node)) {
      return convention.isConstantKey(node.getString());
    } else if (node.isName()) {
      return convention.isConstant(node.getString());
    }
    return false;
  }

  /**
   * Temporary function to determine if a node is constant
   * in the old or new world. This does not check its inputs
   * carefully because it will go away once we switch to the new
   * world.
   */
  static boolean isConstantDeclaration(
      CodingConvention convention, JSDocInfo info, Node node) {
    if (info != null && info.isConstant()) {
      return true;
    }

    if (node.getBooleanProp(Node.IS_CONSTANT_VAR)) {
      return true;
    }

    switch (node.getType()) {
      case Token.NAME:
        return NodeUtil.isConstantByConvention(convention, node);
      case Token.GETPROP:
        return node.isQualifiedName()
            && NodeUtil.isConstantByConvention(convention, node.getLastChild());
    }
    return false;
  }

  static boolean functionHasInlineJsdocs(Node fn) {
    if (!fn.isFunction()) {
      return false;
    }
    // Check inline return annotation
    if (fn.getFirstChild().getJSDocInfo() != null) {
      return true;
    }
    // Check inline parameter annotations
    Node param = fn.getChildAtIndex(1).getFirstChild();
    while (param != null) {
      if (param.getJSDocInfo() != null) {
        return true;
      }
      param = param.getNext();
    }
    return false;
  }

  /**
   * @param n The node.
   * @return The source name property on the node or its ancestors.
   */
  public static String getSourceName(Node n) {
    String sourceName = null;
    while (sourceName == null && n != null) {
      sourceName = n.getSourceFileName();
      n = n.getParent();
    }
    return sourceName;
  }

  /**
   * @param n The node.
   * @return The source name property on the node or its ancestors.
   */
  public static StaticSourceFile getSourceFile(Node n) {
    StaticSourceFile sourceName = null;
    while (sourceName == null && n != null) {
      sourceName = n.getStaticSourceFile();
      n = n.getParent();
    }
    return sourceName;
  }

  /**
   * @param n The node.
   * @return The InputId property on the node or its ancestors.
   */
  public static InputId getInputId(Node n) {
    while (n != null && !n.isScript()) {
      n = n.getParent();
    }

    return (n != null && n.isScript()) ? n.getInputId() : null;
  }

  /**
   * A new CALL node with the "FREE_CALL" set based on call target.
   */
  static Node newCallNode(Node callTarget, Node... parameters) {
    boolean isFreeCall = !isGet(callTarget);
    Node call = IR.call(callTarget);
    call.putBooleanProp(Node.FREE_CALL, isFreeCall);
    for (Node parameter : parameters) {
      call.addChildToBack(parameter);
    }
    return call;
  }

  /**
   * @return Whether the node is known to be a value that is not referenced
   * elsewhere.
   */
  static boolean evaluatesToLocalValue(Node value) {
    return evaluatesToLocalValue(value, Predicates.<Node>alwaysFalse());
  }

  /**
   * @param locals A predicate to apply to unknown local values.
   * @return Whether the node is known to be a value that is not a reference
   *     outside the expression scope.
   */
  static boolean evaluatesToLocalValue(Node value, Predicate<Node> locals) {
    switch (value.getType()) {
      case Token.CAST:
        return evaluatesToLocalValue(value.getFirstChild(), locals);
      case Token.ASSIGN:
        // A result that is aliased by a non-local name, is the effectively the
        // same as returning a non-local name, but this doesn't matter if the
        // value is immutable.
        return NodeUtil.isImmutableValue(value.getLastChild())
            || (locals.apply(value)
                && evaluatesToLocalValue(value.getLastChild(), locals));
      case Token.COMMA:
        return evaluatesToLocalValue(value.getLastChild(), locals);
      case Token.AND:
      case Token.OR:
        return evaluatesToLocalValue(value.getFirstChild(), locals)
           && evaluatesToLocalValue(value.getLastChild(), locals);
      case Token.HOOK:
        return evaluatesToLocalValue(value.getFirstChild().getNext(), locals)
           && evaluatesToLocalValue(value.getLastChild(), locals);
      case Token.INC:
      case Token.DEC:
        if (value.getBooleanProp(Node.INCRDECR_PROP)) {
          return evaluatesToLocalValue(value.getFirstChild(), locals);
        } else {
          return true;
        }
      case Token.THIS:
        return locals.apply(value);
      case Token.NAME:
        return isImmutableValue(value) || locals.apply(value);
      case Token.GETELEM:
      case Token.GETPROP:
        // There is no information about the locality of object properties.
        return locals.apply(value);
      case Token.CALL:
        return callHasLocalResult(value)
            || isToStringMethodCall(value)
            || locals.apply(value);
      case Token.NEW:
        return newHasLocalResult(value)
               || locals.apply(value);
      case Token.FUNCTION:
      case Token.REGEXP:
      case Token.ARRAYLIT:
      case Token.OBJECTLIT:
        // Literals objects with non-literal children are allowed.
        return true;
      case Token.DELPROP:
      case Token.IN:
        // TODO(johnlenz): should IN operator be included in #isSimpleOperator?
        return true;
      default:
        // Other op force a local value:
        //  x = '' + g (x is now an local string)
        //  x -= g (x is now an local number)
        if (isAssignmentOp(value)
            || isSimpleOperator(value)
            || isImmutableValue(value)) {
          return true;
        }

        throw new IllegalStateException(
            "Unexpected expression node" + value +
            "\n parent:" + value.getParent());
    }
  }

  /**
   * Given the first sibling, this returns the nth
   * sibling or null if no such sibling exists.
   * This is like "getChildAtIndex" but returns null for non-existent indexes.
   */
  private static Node getNthSibling(Node first, int index) {
    Node sibling = first;
    while (index != 0 && sibling != null) {
      sibling = sibling.getNext();
      index--;
    }
    return sibling;
  }

  /**
   * Given the function, this returns the nth
   * argument or null if no such parameter exists.
   */
  static Node getArgumentForFunction(Node function, int index) {
    Preconditions.checkState(function.isFunction());
    return getNthSibling(
        function.getFirstChild().getNext().getFirstChild(), index);
  }

  /**
   * Given the new or call, this returns the nth
   * argument of the call or null if no such argument exists.
   */
  static Node getArgumentForCallOrNew(Node call, int index) {
    Preconditions.checkState(isCallOrNew(call));
    return getNthSibling(
      call.getFirstChild().getNext(), index);
  }

  /**
   * Returns whether this is a target of a call or new.
   */
  static boolean isCallOrNewTarget(Node target) {
    Node parent = target.getParent();
    return parent != null
        && NodeUtil.isCallOrNew(parent)
        && parent.getFirstChild() == target;
  }

  private static boolean isToStringMethodCall(Node call) {
    Node getNode = call.getFirstChild();
    if (isGet(getNode)) {
      Node propNode = getNode.getLastChild();
      return propNode.isString() && "toString".equals(propNode.getString());
    }
    return false;
  }

  /** Find the best JSDoc for the given node. */
  @Nullable
  public static JSDocInfo getBestJSDocInfo(Node n) {
    JSDocInfo info = n.getJSDocInfo();
    if (info == null) {
      Node parent = n.getParent();
      if (parent == null) {
        return null;
      }

      if (parent.isName()) {
        return getBestJSDocInfo(parent);
      } else if (parent.isAssign()) {
        return getBestJSDocInfo(parent);
      } else if (isObjectLitKey(parent)) {
        return parent.getJSDocInfo();
      } else if (parent.isFunction()) {
        // FUNCTION may be inside ASSIGN
        return getBestJSDocInfo(parent);
      } else if (parent.isVar() && parent.hasOneChild()) {
        return parent.getJSDocInfo();
      } else if ((parent.isHook() && parent.getFirstChild() != n)
                 || parent.isOr()
                 || parent.isAnd()
                 || (parent.isComma() && parent.getFirstChild() != n)) {
        return getBestJSDocInfo(parent);
      }
    }
    return info;
  }

  /** Find the l-value that the given r-value is being assigned to. */
  static Node getBestLValue(Node n) {
    Node parent = n.getParent();
    boolean isFunctionDeclaration = isFunctionDeclaration(n);
    if (isFunctionDeclaration) {
      return n.getFirstChild();
    } else if (parent.isName()) {
      return parent;
    } else if (parent.isAssign()) {
      return parent.getFirstChild();
    } else if (isObjectLitKey(parent)) {
      return parent;
    } else if (
        (parent.isHook() && parent.getFirstChild() != n) ||
        parent.isOr() ||
        parent.isAnd() ||
        (parent.isComma() && parent.getFirstChild() != n)) {
      return getBestLValue(parent);
    } else if (parent.isCast()) {
      return getBestLValue(parent);
    }
    return null;
  }

  /** Gets the r-value of a node returned by getBestLValue. */
  static Node getRValueOfLValue(Node n) {
    Node parent = n.getParent();
    switch (parent.getType()) {
      case Token.ASSIGN:
        return n.getNext();
      case Token.VAR:
      case Token.LET:
      case Token.CONST:
        return n.getFirstChild();
      case Token.FUNCTION:
        return parent;
    }
    return null;
  }

  /** Get the owner of the given l-value node. */
  static Node getBestLValueOwner(@Nullable Node lValue) {
    if (lValue == null || lValue.getParent() == null) {
      return null;
    }
    if (isObjectLitKey(lValue)) {
      return getBestLValue(lValue.getParent());
    } else if (isGet(lValue)) {
      return lValue.getFirstChild();
    }

    return null;
  }

  /** Get the name of the given l-value node. */
  static String getBestLValueName(@Nullable Node lValue) {
    if (lValue == null || lValue.getParent() == null) {
      return null;
    }
    if (isObjectLitKey(lValue)) {
      Node owner = getBestLValue(lValue.getParent());
      if (owner != null) {
        String ownerName = getBestLValueName(owner);
        if (ownerName != null) {
          return ownerName + "." + getObjectLitKeyName(lValue);
        }
      }
      return null;
    }
    return lValue.getQualifiedName();
  }

  /**
   * @return false iff the result of the expression is not consumed.
   */
  static boolean isExpressionResultUsed(Node expr) {
    // TODO(johnlenz): consider sharing some code with trySimpleUnusedResult.
    Node parent = expr.getParent();
    switch (parent.getType()) {
      case Token.BLOCK:
      case Token.EXPR_RESULT:
        return false;
      case Token.CAST:
        return isExpressionResultUsed(parent);
      case Token.HOOK:
      case Token.AND:
      case Token.OR:
        return (expr == parent.getFirstChild()) || isExpressionResultUsed(parent);
      case Token.COMMA:
        Node gramps = parent.getParent();
        if (gramps.isCall() &&
            parent == gramps.getFirstChild()) {
          // Semantically, a direct call to eval is different from an indirect
          // call to an eval. See ECMA-262 S15.1.2.1. So it's OK for the first
          // expression to a comma to be a no-op if it's used to indirect
          // an eval. This we pretend that this is "used".
          if (expr == parent.getFirstChild() &&
              parent.getChildCount() == 2 &&
              expr.getNext().isName() &&
              "eval".equals(expr.getNext().getString())) {
            return true;
          }
        }

        return (expr == parent.getFirstChild())
            ? false : isExpressionResultUsed(parent);
      case Token.FOR:
        if (!NodeUtil.isForIn(parent)) {
          // Only an expression whose result is in the condition part of the
          // expression is used.
          return (parent.getChildAtIndex(1) == expr);
        }
        break;
    }
    return true;
  }

  /**
   * @param n The expression to check.
   * @return Whether the expression is unconditionally executed only once in the
   *     containing execution scope.
   */
  static boolean isExecutedExactlyOnce(Node n) {
    inspect: do {
      Node parent = n.getParent();
      switch (parent.getType()) {
        case Token.IF:
        case Token.HOOK:
        case Token.AND:
        case Token.OR:
          if (parent.getFirstChild() != n) {
            return false;
          }
          // other ancestors may be conditional
          continue inspect;
        case Token.FOR:
          if (NodeUtil.isForIn(parent)) {
            if (parent.getChildAtIndex(1) != n) {
              return false;
            }
          } else {
            if (parent.getFirstChild() != n) {
              return false;
            }
          }
          // other ancestors may be conditional
          continue inspect;
        case Token.WHILE:
        case Token.DO:
          return false;
        case Token.TRY:
          // Consider all code under a try/catch to be conditionally executed.
          if (!hasFinally(parent) || parent.getLastChild() != n) {
            return false;
          }
          continue inspect;
        case Token.CASE:
        case Token.DEFAULT_CASE:
          return false;
        case Token.SCRIPT:
        case Token.FUNCTION:
          // Done, we've reached the scope root.
          break inspect;
      }
    } while ((n = n.getParent()) != null);
    return true;
  }

  /**
   * @return An appropriate AST node for the boolean value.
   */
  static Node booleanNode(boolean value) {
    return value ? IR.trueNode() : IR.falseNode();
  }

  /**
   * @return An appropriate AST node for the double value.
   */
  static Node numberNode(double value, Node srcref) {
    Node result;
    if (Double.isNaN(value)) {
      result = IR.name("NaN");
    } else if (value == Double.POSITIVE_INFINITY) {
      result = IR.name("Infinity");
    } else if (value == Double.NEGATIVE_INFINITY) {
      result = IR.neg(IR.name("Infinity"));
    } else {
      result = IR.number(value);
    }
    if (srcref != null) {
      result.srcrefTree(srcref);
    }
    return result;
  }

  static boolean isNaN(Node n) {
    return (n.isName() && n.getString().equals("NaN")) || (n.getType() == Token.DIV
               && n.getFirstChild().isNumber() && n.getFirstChild().getDouble() == 0
               && n.getLastChild().isNumber() && n.getLastChild().getDouble() == 0);
  }

  /**
   * Given an AST and its copy, map the root node of each scope of main to the
   * corresponding root node of clone
   */
  public static Map<Node, Node> mapMainToClone(Node main, Node clone) {
    Preconditions.checkState(main.isEquivalentTo(clone));
    Map<Node, Node> mtoc = new HashMap<>();
    mtoc.put(main, clone);
    mtocHelper(mtoc, main, clone);
    return mtoc;
  }

  private static void mtocHelper(Map<Node, Node> map, Node main, Node clone) {
    if (main.isFunction()) {
      map.put(main, clone);
    }
    Node mchild = main.getFirstChild(), cchild = clone.getFirstChild();
    while (mchild != null) {
      mtocHelper(map, mchild, cchild);
      mchild = mchild.getNext();
      cchild = cchild.getNext();
    }
  }

  /** Checks that the scope roots marked as changed have indeed changed */
  public static void verifyScopeChanges(Map<Node, Node> map,
      Node main, boolean verifyUnchangedNodes,
      AbstractCompiler compiler) {
    // compiler is passed only to call compiler.toSource during debugging to see
    // mismatches in scopes

    // If verifyUnchangedNodes is false, we are comparing the initial AST to the
    // final AST. Don't check unmarked nodes b/c they may have been changed by
    // non-loopable passes.
    // If verifyUnchangedNodes is true, we are comparing the ASTs before & after
    // a pass. Check all scope roots.
    final Map<Node, Node> mtoc = map;
    final boolean checkUnchanged = verifyUnchangedNodes;
    Node clone = mtoc.get(main);
    if (main.getChangeTime() > clone.getChangeTime()) {
      Preconditions.checkState(!isEquivalentToExcludingFunctions(main, clone));
    } else if (checkUnchanged) {
      Preconditions.checkState(isEquivalentToExcludingFunctions(main, clone));
    }
    visitPreOrder(main,
        new Visitor() {
          @Override
          public void visit(Node n) {
            if (n.isFunction() && mtoc.containsKey(n)) {
              Node clone = mtoc.get(n);
              if (n.getChangeTime() > clone.getChangeTime()) {
                Preconditions.checkState(
                    !isEquivalentToExcludingFunctions(n, clone));
              } else if (checkUnchanged) {
                Preconditions.checkState(
                    isEquivalentToExcludingFunctions(n, clone));
              }
            }
          }
        },
        Predicates.<Node>alwaysTrue());
  }

  static int countAstSizeUpToLimit(Node n, final int limit) {
    // Java doesn't allow accessing mutable local variables from another class.
    final int[] wrappedSize = {0};
    visitPreOrder(
        n,
        new Visitor() {
          @Override
          public void visit(Node n) {
            wrappedSize[0]++;
          }
        },
        new Predicate<Node>() {
          @Override
            public boolean apply(Node n) {
            return wrappedSize[0] < limit;
          }
        });
    return wrappedSize[0];
  }

  /**
   * @return Whether the two node are equivalent while ignoring
   * differences any descendant functions differences.
   */
  private static boolean isEquivalentToExcludingFunctions(
      Node thisNode, Node thatNode) {
    if (thisNode == null || thatNode == null) {
      return thisNode == null && thatNode == null;
    }
    if (!thisNode.isEquivalentToShallow(thatNode)) {
      return false;
    }
    if (thisNode.getChildCount() != thatNode.getChildCount()) {
      return false;
    }
    Node thisChild = thisNode.getFirstChild();
    Node thatChild = thatNode.getFirstChild();
    while (thisChild != null && thatChild != null) {
      if (thisChild.isFunction()) {
        //  don't compare function name, parameters or bodies.
        return thatChild.isFunction();
      }
      if (!isEquivalentToExcludingFunctions(thisChild, thatChild)) {
        return false;
      }
      thisChild = thisChild.getNext();
      thatChild = thatChild.getNext();
    }
    return true;
  }

  static JSDocInfo createConstantJsDoc() {
    JSDocInfoBuilder builder = new JSDocInfoBuilder(false);
    builder.recordConstancy();
    return builder.build();
  }

  static int toInt32(double d) {
    int id = (int) d;
    if (id == d) {
        // This covers -0.0 as well
        return id;
    }

    if (Double.isNaN(d)
        || d == Double.POSITIVE_INFINITY
        || d == Double.NEGATIVE_INFINITY) {
        return 0;
    }

    d = (d >= 0) ? Math.floor(d) : Math.ceil(d);

    double two32 = 4294967296.0;
    d = Math.IEEEremainder(d, two32);
    // (double)(long)d == d should hold here

    long l = (long) d;
    // returning (int)d does not work as d can be outside int range
    // but the result must always be 32 lower bits of l
    return (int) l;
  }
}


File: src/com/google/javascript/jscomp/parsing/IRFactory.java
/*
 * Copyright 2013 The Closure Compiler Authors.
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
import static com.google.javascript.rhino.TypeDeclarationsIR.parameterizedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.stringType;
import static com.google.javascript.rhino.TypeDeclarationsIR.undefinedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.unionType;
import static com.google.javascript.rhino.TypeDeclarationsIR.voidType;

import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Lists;
import com.google.common.collect.UnmodifiableIterator;
import com.google.javascript.jscomp.parsing.Config.LanguageMode;
import com.google.javascript.jscomp.parsing.parser.IdentifierToken;
import com.google.javascript.jscomp.parsing.parser.LiteralToken;
import com.google.javascript.jscomp.parsing.parser.TokenType;
import com.google.javascript.jscomp.parsing.parser.trees.ArrayLiteralExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ArrayPatternTree;
import com.google.javascript.jscomp.parsing.parser.trees.ArrayTypeTree;
import com.google.javascript.jscomp.parsing.parser.trees.AssignmentRestElementTree;
import com.google.javascript.jscomp.parsing.parser.trees.BinaryOperatorTree;
import com.google.javascript.jscomp.parsing.parser.trees.BlockTree;
import com.google.javascript.jscomp.parsing.parser.trees.BreakStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.CallExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.CaseClauseTree;
import com.google.javascript.jscomp.parsing.parser.trees.CatchTree;
import com.google.javascript.jscomp.parsing.parser.trees.ClassDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.CommaExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.Comment;
import com.google.javascript.jscomp.parsing.parser.trees.ComprehensionForTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComprehensionIfTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComprehensionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertyDefinitionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertyGetterTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertyMemberVariableTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertyMethodTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertySetterTree;
import com.google.javascript.jscomp.parsing.parser.trees.ConditionalExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ContinueStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.DebuggerStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.DefaultClauseTree;
import com.google.javascript.jscomp.parsing.parser.trees.DefaultParameterTree;
import com.google.javascript.jscomp.parsing.parser.trees.DoWhileStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.EmptyStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.EnumDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.ExportDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.ExportSpecifierTree;
import com.google.javascript.jscomp.parsing.parser.trees.ExpressionStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.FinallyTree;
import com.google.javascript.jscomp.parsing.parser.trees.ForInStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.ForOfStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.ForStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.FormalParameterListTree;
import com.google.javascript.jscomp.parsing.parser.trees.FunctionDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.FunctionTypeTree;
import com.google.javascript.jscomp.parsing.parser.trees.GetAccessorTree;
import com.google.javascript.jscomp.parsing.parser.trees.IdentifierExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.IfStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.ImportDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.ImportSpecifierTree;
import com.google.javascript.jscomp.parsing.parser.trees.InterfaceDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.LabelledStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.LiteralExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.MemberExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.MemberLookupExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.MemberVariableTree;
import com.google.javascript.jscomp.parsing.parser.trees.MissingPrimaryExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ModuleImportTree;
import com.google.javascript.jscomp.parsing.parser.trees.NewExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.NullTree;
import com.google.javascript.jscomp.parsing.parser.trees.ObjectLiteralExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ObjectPatternTree;
import com.google.javascript.jscomp.parsing.parser.trees.ParameterizedTypeTree;
import com.google.javascript.jscomp.parsing.parser.trees.ParenExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ParseTree;
import com.google.javascript.jscomp.parsing.parser.trees.ParseTreeType;
import com.google.javascript.jscomp.parsing.parser.trees.PostfixExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ProgramTree;
import com.google.javascript.jscomp.parsing.parser.trees.PropertyNameAssignmentTree;
import com.google.javascript.jscomp.parsing.parser.trees.RestParameterTree;
import com.google.javascript.jscomp.parsing.parser.trees.ReturnStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.SetAccessorTree;
import com.google.javascript.jscomp.parsing.parser.trees.SpreadExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.SuperExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.SwitchStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.TemplateLiteralExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.TemplateLiteralPortionTree;
import com.google.javascript.jscomp.parsing.parser.trees.TemplateSubstitutionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ThisExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ThrowStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.TryStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.TypeNameTree;
import com.google.javascript.jscomp.parsing.parser.trees.TypedParameterTree;
import com.google.javascript.jscomp.parsing.parser.trees.UnaryExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.UnionTypeTree;
import com.google.javascript.jscomp.parsing.parser.trees.VariableDeclarationListTree;
import com.google.javascript.jscomp.parsing.parser.trees.VariableDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.VariableStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.WhileStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.WithStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.YieldExpressionTree;
import com.google.javascript.jscomp.parsing.parser.util.SourcePosition;
import com.google.javascript.jscomp.parsing.parser.util.SourceRange;
import com.google.javascript.rhino.ErrorReporter;
import com.google.javascript.rhino.IR;
import com.google.javascript.rhino.JSDocInfo;
import com.google.javascript.rhino.JSDocInfoBuilder;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.Node.TypeDeclarationNode;
import com.google.javascript.rhino.StaticSourceFile;
import com.google.javascript.rhino.Token;
import com.google.javascript.rhino.TokenStream;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * IRFactory transforms the external AST to the internal AST.
 */
class IRFactory {

  static final String GETTER_ERROR_MESSAGE =
      "getters are not supported in older versions of JavaScript. " +
      "If you are targeting newer versions of JavaScript, " +
      "set the appropriate language_in option.";

  static final String SETTER_ERROR_MESSAGE =
      "setters are not supported in older versions of JavaScript. " +
      "If you are targeting newer versions of JavaScript, " +
      "set the appropriate language_in option.";

  static final String SUSPICIOUS_COMMENT_WARNING =
      "Non-JSDoc comment has annotations. " +
      "Did you mean to start it with '/**'?";

  static final String MISPLACED_TYPE_ANNOTATION =
      "Type annotations are not allowed here. Are you missing parentheses?";

  static final String MISPLACED_FUNCTION_ANNOTATION =
      "This JSDoc is not attached to a function node. Are you missing parentheses?";

  static final String MISPLACED_MSG_ANNOTATION =
      "@desc, @hidden, and @meaning annotations should only be on message nodes.";

  static final String INVALID_ES3_PROP_NAME =
      "Keywords and reserved words are not allowed as unquoted property " +
      "names in older versions of JavaScript. " +
      "If you are targeting newer versions of JavaScript, " +
      "set the appropriate language_in option.";

  static final String INVALID_ES5_STRICT_OCTAL =
      "Octal integer literals are not supported in Ecmascript 5 strict mode.";

  static final String INVALID_NUMBER_LITERAL =
      "Invalid number literal.";

  static final String STRING_CONTINUATION_ERROR =
      "String continuations are not supported in this language mode.";

  static final String STRING_CONTINUATION_WARNING =
      "String continuations are not recommended. See"
      + " https://google-styleguide.googlecode.com/svn/trunk/javascriptguide.xml#Multiline_string_literals";

  static final String BINARY_NUMBER_LITERAL_WARNING =
      "Binary integer literals are not supported in this language mode.";

  static final String OCTAL_NUMBER_LITERAL_WARNING =
      "Octal integer literals are not supported in this language mode.";

  static final String OCTAL_STRING_LITERAL_WARNING =
      "Octal literals in strings are not supported in this language mode.";

  static final String DUPLICATE_PARAMETER =
      "Duplicate parameter name \"%s\"";

  static final String DUPLICATE_LABEL =
      "Duplicate label \"%s\"";

  static final String UNLABELED_BREAK =
      "unlabelled break must be inside loop or switch";

  static final String UNEXPECTED_CONTINUE = "continue must be inside loop";

  static final String UNEXPECTED_LABLED_CONTINUE =
      "continue can only use labeles of iteration statements";

  static final String UNEXPECTED_RETURN = "return must be inside function";

  static final String UNDEFINED_LABEL = "undefined label \"%s\"";

  static final String ANNOTATION_DEPRECATED =
      "The %s annotation is deprecated.%s";

  private final String sourceString;
  private final List<Integer> newlines;
  private final StaticSourceFile sourceFile;
  private final String sourceName;
  private final Config config;
  private final ErrorReporter errorReporter;
  private final TransformDispatcher transformDispatcher;

  private static final ImmutableSet<String> ALLOWED_DIRECTIVES =
      ImmutableSet.of("use strict");

  private static final ImmutableSet<String> ES5_RESERVED_KEYWORDS =
      ImmutableSet.of(
          // From Section 7.6.1.2
          "class", "const", "enum", "export", "extends", "import", "super");
  private static final ImmutableSet<String> ES5_STRICT_RESERVED_KEYWORDS =
      ImmutableSet.of(
          // From Section 7.6.1.2
          "class", "const", "enum", "export", "extends", "import", "super",
          "implements", "interface", "let", "package", "private", "protected",
          "public", "static", "yield");

  private final Set<String> reservedKeywords;
  private final Set<Comment> parsedComments = new HashSet<>();

  // @license text gets appended onto the fileLevelJsDocBuilder as found,
  // and stored in JSDocInfo for placeholder node.
  JSDocInfoBuilder fileLevelJsDocBuilder;
  JSDocInfo fileOverviewInfo = null;

  // Use a template node for properties set on all nodes to minimize the
  // memory footprint associated with these.
  private final Node templateNode;

  private final UnmodifiableIterator<Comment> nextCommentIter;

  private Comment currentComment;

  private boolean currentFileIsExterns = false;
  private boolean hasTypeSyntax = false;
  private boolean hasJsDocTypeAnnotations = false;

  private IRFactory(String sourceString,
                    StaticSourceFile sourceFile,
                    Config config,
                    ErrorReporter errorReporter,
                    ImmutableList<Comment> comments) {
    this.sourceString = sourceString;
    this.nextCommentIter = comments.iterator();
    this.currentComment = nextCommentIter.hasNext() ? nextCommentIter.next() : null;
    this.newlines = new ArrayList<>();
    this.sourceFile = sourceFile;
    this.fileLevelJsDocBuilder = new JSDocInfoBuilder(
        config.parseJsDocDocumentation);

    // Pre-generate all the newlines in the file.
    for (int charNo = 0; true; charNo++) {
      charNo = sourceString.indexOf('\n', charNo);
      if (charNo == -1) {
        break;
      }
      newlines.add(Integer.valueOf(charNo));
    }

    // Sometimes this will be null in tests.
    this.sourceName = sourceFile == null ? null : sourceFile.getName();

    this.config = config;
    this.errorReporter = errorReporter;
    this.transformDispatcher = new TransformDispatcher();
    // The template node properties are applied to all nodes in this transform.
    this.templateNode = createTemplateNode();

    switch (config.languageMode) {
      case ECMASCRIPT3:
        reservedKeywords = null; // use TokenStream.isKeyword instead
        break;
      case ECMASCRIPT5:
        reservedKeywords = ES5_RESERVED_KEYWORDS;
        break;
      case ECMASCRIPT5_STRICT:
        reservedKeywords = ES5_STRICT_RESERVED_KEYWORDS;
        break;
      case ECMASCRIPT6:
        reservedKeywords = ES5_RESERVED_KEYWORDS;
        break;
      case ECMASCRIPT6_STRICT:
        reservedKeywords = ES5_STRICT_RESERVED_KEYWORDS;
        break;
      case ECMASCRIPT6_TYPED:
        reservedKeywords = ES5_STRICT_RESERVED_KEYWORDS;
        break;
      default:
        throw new IllegalStateException("unknown language mode: " + config.languageMode);
    }
  }

  // Create a template node to use as a source of common attributes, this allows
  // the prop structure to be shared among all the node from this source file.
  // This reduces the cost of these properties to O(nodes) to O(files).
  private Node createTemplateNode() {
    // The Node type choice is arbitrary.
    Node templateNode = new Node(Token.SCRIPT);
    templateNode.setStaticSourceFile(sourceFile);
    return templateNode;
  }

  public static Node transformTree(ProgramTree tree,
                                   StaticSourceFile sourceFile,
                                   String sourceString,
                                   Config config,
                                   ErrorReporter errorReporter) {
    IRFactory irFactory = new IRFactory(sourceString, sourceFile,
        config, errorReporter, tree.sourceComments);

    // don't call transform as we don't want standard jsdoc handling.
    Node n = irFactory.justTransform(tree);
    irFactory.setSourceInfo(n, tree);

    if (tree.sourceComments != null) {
      for (Comment comment : tree.sourceComments) {
        if (comment.type == Comment.Type.JSDOC &&
            !irFactory.parsedComments.contains(comment)) {
          irFactory.handlePossibleFileOverviewJsDoc(comment);
        } else if (comment.type == Comment.Type.BLOCK) {
          irFactory.handleBlockComment(comment);
        }
      }
    }

    irFactory.setFileOverviewJsDoc(n);

    irFactory.validateAll(n);

    return n;
  }

  private void validateAll(Node n) {
    validate(n);
    for (Node c = n.getFirstChild(); c != null; c = c.getNext()) {
      validateAll(c);
    }
  }

  private void validate(Node n) {
    validateJsDoc(n);
    validateParameters(n);
    validateBreakContinue(n);
    validateReturn(n);
    validateLabel(n);
  }

  private void validateBreakContinue(Node n) {
    if (n.isBreak() || n.isContinue()) {
      Node labelName = n.getFirstChild();
      if (labelName != null) {
        Node parent = n.getParent();
        while (!parent.isLabel() || !labelsMatch(parent, labelName)) {
          if (parent.isFunction() || parent.isScript()) {
            // report missing label
            errorReporter.error(
                String.format(UNDEFINED_LABEL, labelName.getString()),
                sourceName,
                n.getLineno(), n.getCharno());
            break;
          }
          parent = parent.getParent();
        }
        if (parent.isLabel() && labelsMatch(parent, labelName)) {
          if (n.isContinue() && !isContinueTarget(parent.getLastChild())) {
            // report invalid continue target
            errorReporter.error(
                UNEXPECTED_LABLED_CONTINUE,
                sourceName,
                n.getLineno(), n.getCharno());
          }
        }
      } else {
        if (n.isContinue()) {
          Node parent = n.getParent();
          while (!isContinueTarget(parent)) {
            if (parent.isFunction() || parent.isScript()) {
              // report invalid continue
              errorReporter.error(
                  UNEXPECTED_CONTINUE,
                  sourceName,
                  n.getLineno(), n.getCharno());
              break;
            }
            parent = parent.getParent();
          }
        } else {
          Node parent = n.getParent();
          while (!isBreakTarget(parent)) {
            if (parent.isFunction() || parent.isScript()) {
              // report invalid break
              errorReporter.error(
                  UNLABELED_BREAK,
                  sourceName,
                  n.getLineno(), n.getCharno());
              break;
            }
            parent = parent.getParent();
          }
        }
      }
    }
  }

  private void validateReturn(Node n) {
    if (n.isReturn()) {
      Node parent = n;
      while ((parent = parent.getParent()) != null) {
        if (parent.isFunction()) {
          return;
        }
      }
      errorReporter.error(UNEXPECTED_RETURN,
          sourceName, n.getLineno(), n.getCharno());
    }
  }

  private static boolean isBreakTarget(Node n) {
    switch (n.getType()) {
      case Token.FOR:
      case Token.FOR_OF:
      case Token.WHILE:
      case Token.DO:
      case Token.SWITCH:
        return true;
    }
    return false;
  }

  private static boolean isContinueTarget(Node n) {
    switch (n.getType()) {
      case Token.FOR:
      case Token.FOR_OF:
      case Token.WHILE:
      case Token.DO:
        return true;
    }
    return false;
  }


  private static boolean labelsMatch(Node label, Node labelName) {
    return label.getFirstChild().getString().equals(labelName.getString());
  }

  private void validateParameters(Node n) {
    if (n.isParamList()) {
      Node c = n.getFirstChild();
      for (; c != null; c = c.getNext()) {
        if (!c.isName()) {
          continue;
        }
        Node sibling = c.getNext();
        for (; sibling != null; sibling = sibling.getNext()) {
          if (sibling.isName() && c.getString().equals(sibling.getString())) {
            errorReporter.warning(
                String.format(DUPLICATE_PARAMETER, c.getString()),
                sourceName,
                n.getLineno(), n.getCharno());
          }
        }
      }
    }
  }

  private void validateJsDoc(Node n) {
    validateTypeAnnotations(n);
    validateFunctionJsDoc(n);
    validateMsgJsDoc(n);
    validateDeprecatedJsDoc(n);
  }

  /**
   * Checks that deprecated annotations such as @expose are not present
   */
  private void validateDeprecatedJsDoc(Node n) {
    JSDocInfo info = n.getJSDocInfo();
    if (info == null) {
      return;
    }
    if (info.isExpose()) {
      errorReporter.warning(
          String.format(ANNOTATION_DEPRECATED, "@expose",
              " Use @nocollapse or @export instead."),
          sourceName,
          n.getLineno(), n.getCharno());
    }
  }

  /**
   * Checks that annotations for messages ({@code @desc}, {@code @hidden}, and {@code @meaning})
   * are in the proper place, namely on names starting with MSG_ which indicates they should be
   * extracted for translation. A later pass checks that the right side is a call to goog.getMsg.
   */
  private void validateMsgJsDoc(Node n) {
    JSDocInfo info = n.getJSDocInfo();
    if (info == null) {
      return;
    }
    if (info.getDescription() != null || info.isHidden() || info.getMeaning() != null) {
      boolean descOkay = false;
      switch (n.getType()) {
        case Token.ASSIGN: {
          Node lhs = n.getFirstChild();
          if (lhs.isName()) {
            descOkay = lhs.getString().startsWith("MSG_");
          } else if (lhs.isQualifiedName()) {
            descOkay = lhs.getLastChild().getString().startsWith("MSG_");
          }
          break;
        }
        case Token.VAR:
        case Token.LET:
        case Token.CONST:
          descOkay = n.getFirstChild().getString().startsWith("MSG_");
          break;
        case Token.STRING_KEY:
          descOkay = n.getString().startsWith("MSG_");
          break;
      }
      if (!descOkay) {
        errorReporter.warning(MISPLACED_MSG_ANNOTATION,
            sourceName, n.getLineno(), n.getCharno());
      }
    }
  }

  private JSDocInfo recordJsDoc(SourceRange location, JSDocInfo info) {
    if (info != null && info.hasTypeInformation()) {
      hasJsDocTypeAnnotations = true;
      if (hasTypeSyntax) {
        errorReporter.error("Bad type syntax"
            + " - can only have JSDoc or inline type annotations, not both",
            sourceName, lineno(location.start), charno(location.start));
      }
    }
    return info;
  }

  private void recordTypeSyntax(SourceRange location) {
    hasTypeSyntax = true;
    if (hasJsDocTypeAnnotations) {
      errorReporter.error("Bad type syntax"
          + " - can only have JSDoc or inline type annotations, not both",
          sourceName, lineno(location.start), charno(location.start));
    }
  }

  /**
   * Checks that JSDoc intended for a function is actually attached to a
   * function.
   */
  private void validateFunctionJsDoc(Node n) {
    JSDocInfo info = n.getJSDocInfo();
    if (info == null) {
      return;
    }
    if (info.containsFunctionDeclaration() && !info.hasType()) {
      // This JSDoc should be attached to a FUNCTION node, or an assignment
      // with a function as the RHS, etc.
      switch (n.getType()) {
        case Token.FUNCTION:
        case Token.VAR:
        case Token.LET:
        case Token.CONST:
        case Token.GETTER_DEF:
        case Token.SETTER_DEF:
        case Token.MEMBER_FUNCTION_DEF:
        case Token.STRING_KEY:
        case Token.EXPORT:
          return;
        case Token.GETELEM:
        case Token.GETPROP:
          if (n.getFirstChild().isQualifiedName()) {
            return;
          }
          break;
        case Token.ASSIGN: {
          // TODO(tbreisacher): Check that the RHS of the assignment is a
          // function. Note that it can be a FUNCTION node, but it can also be
          // a call to goog.abstractMethod, goog.functions.constant, etc.
          return;
        }
      }
      errorReporter.warning(MISPLACED_FUNCTION_ANNOTATION,
          sourceName,
          n.getLineno(), n.getCharno());
    }
  }

  /**
   * Check that JSDoc with a {@code @type} annotation is in a valid place.
   */
  @SuppressWarnings("incomplete-switch")
  private void validateTypeAnnotations(Node n) {
    JSDocInfo info = n.getJSDocInfo();
    if (info != null && info.hasType()) {
      boolean valid = false;
      switch (n.getType()) {
        // Casts, variable declarations, and exports are valid.
        case Token.CAST:
        case Token.VAR:
        case Token.LET:
        case Token.CONST:
        case Token.EXPORT:
          valid = true;
          break;
        // Function declarations are valid
        case Token.FUNCTION:
          valid = isFunctionDeclaration(n);
          break;
        // Object literal properties, catch declarations and variable
        // initializers are valid.
        case Token.NAME:
        case Token.DEFAULT_VALUE:
          Node parent = n.getParent();
          switch (parent.getType()) {
            case Token.STRING_KEY:
            case Token.GETTER_DEF:
            case Token.SETTER_DEF:
            case Token.CATCH:
            case Token.FUNCTION:
            case Token.VAR:
            case Token.LET:
            case Token.CONST:
            case Token.PARAM_LIST:
              valid = true;
              break;
          }
          break;
        // Object literal properties are valid
        case Token.STRING_KEY:
        case Token.GETTER_DEF:
        case Token.SETTER_DEF:
          valid = true;
          break;
        // Property assignments are valid, if at the root of an expression.
        case Token.ASSIGN:
          valid = n.getParent().isExprResult()
            && (n.getFirstChild().isGetProp() || n.getFirstChild().isGetElem());
          break;
        case Token.GETPROP:
          valid = n.getParent().isExprResult() && n.isQualifiedName();
          break;
        case Token.CALL:
          valid = info.isDefine();
          break;
      }

      if (!valid) {
        errorReporter.warning(MISPLACED_TYPE_ANNOTATION,
            sourceName,
            n.getLineno(), n.getCharno());
      }
    }
  }

  private void validateLabel(Node n) {
    if (n.isLabel()) {
      Node labelName = n.getFirstChild();
      for (Node parent = n.getParent();
           parent != null && !parent.isFunction(); parent = parent.getParent()) {
        if (parent.isLabel() && labelsMatch(parent, labelName)) {
          errorReporter.error(
              String.format(DUPLICATE_LABEL, labelName.getString()),
              sourceName,
              n.getLineno(), n.getCharno());
          break;
        }
      }
    }
  }

  private void setFileOverviewJsDoc(Node irNode) {
    // Only after we've seen all @fileoverview entries, attach the
    // last one to the root node, and copy the found license strings
    // to that node.
    JSDocInfo rootNodeJsDoc = fileLevelJsDocBuilder.build();
    if (rootNodeJsDoc != null) {
      irNode.setJSDocInfo(rootNodeJsDoc);
    }

    if (fileOverviewInfo != null) {
      if ((irNode.getJSDocInfo() != null) &&
          (irNode.getJSDocInfo().getLicense() != null)) {
        JSDocInfoBuilder builder = JSDocInfoBuilder.copyFrom(fileOverviewInfo);
        builder.recordLicense(irNode.getJSDocInfo().getLicense());
        fileOverviewInfo = builder.build();
      }
      irNode.setJSDocInfo(fileOverviewInfo);
    }
  }

  private Node transformBlock(ParseTree node) {
    Node irNode = transform(node);
    if (!irNode.isBlock()) {
      if (irNode.isEmpty()) {
        irNode.setType(Token.BLOCK);
      } else {
        Node newBlock = newNode(Token.BLOCK, irNode);
        setSourceInfo(newBlock, irNode);
        irNode = newBlock;
      }
      irNode.setIsAddedBlock(true);
    }
    return irNode;
  }

  /**
   * Check to see if the given block comment looks like it should be JSDoc.
   */
  private void handleBlockComment(Comment comment) {
    Pattern p = Pattern.compile("(/|(\n[ \t]*))\\*[ \t]*@[a-zA-Z]+[ \t\n{]");
    if (p.matcher(comment.value).find()) {
      errorReporter.warning(
          SUSPICIOUS_COMMENT_WARNING,
          sourceName,
          lineno(comment.location.start),
          charno(comment.location.start));
    }
  }

  /**
   * @return true if the jsDocParser represents a fileoverview.
   */
  private boolean handlePossibleFileOverviewJsDoc(
      JsDocInfoParser jsDocParser) {
    if (jsDocParser.getFileOverviewJSDocInfo() != fileOverviewInfo) {
      fileOverviewInfo = jsDocParser.getFileOverviewJSDocInfo();
      if (fileOverviewInfo.isExterns()) {
        this.currentFileIsExterns = true;
      }
      return true;
    }
    return false;
  }

  private void handlePossibleFileOverviewJsDoc(Comment comment) {
    JsDocInfoParser jsDocParser = createJsDocInfoParser(comment);
    parsedComments.add(comment);
    handlePossibleFileOverviewJsDoc(jsDocParser);
  }

  private Comment getJsDoc(SourceRange location) {
    Comment closestPreviousComment = null;
    while (currentComment != null &&
        currentComment.location.end.offset <= location.start.offset) {
      if (currentComment.type == Comment.Type.JSDOC) {
        closestPreviousComment = currentComment;
      }
      if (this.nextCommentIter.hasNext()) {
        currentComment = this.nextCommentIter.next();
      } else {
        currentComment = null;
      }
    }

    return closestPreviousComment;
  }

  private Comment getJsDoc(ParseTree tree) {
    return getJsDoc(tree.location);
  }

  private Comment getJsDoc(
      com.google.javascript.jscomp.parsing.parser.Token token) {
    return getJsDoc(token.location);
  }

  private JSDocInfo handleJsDoc(Comment comment) {
    if (comment != null) {
      JsDocInfoParser jsDocParser = createJsDocInfoParser(comment);
      parsedComments.add(comment);
      if (!handlePossibleFileOverviewJsDoc(jsDocParser)) {
        return recordJsDoc(comment.location,
            jsDocParser.retrieveAndResetParsedJSDocInfo());
      }
    }
    return null;
  }

  private JSDocInfo handleJsDoc(ParseTree node) {
    if (!shouldAttachJSDocHere(node)) {
      return null;
    }
    return handleJsDoc(getJsDoc(node));
  }

  private boolean shouldAttachJSDocHere(ParseTree tree) {
    switch (tree.type) {
      case EXPRESSION_STATEMENT:
        return false;
      case LABELLED_STATEMENT:
        return false;
      case CALL_EXPRESSION:
      case CONDITIONAL_EXPRESSION:
      case BINARY_OPERATOR:
      case MEMBER_EXPRESSION:
      case MEMBER_LOOKUP_EXPRESSION:
      case POSTFIX_EXPRESSION:
        ParseTree nearest = findNearestNode(tree);
        if (nearest.type == ParseTreeType.PAREN_EXPRESSION) {
          return false;
        }
        return true;
      default:
        return true;
    }
  }

  private static ParseTree findNearestNode(ParseTree tree) {
    while (true) {
      switch (tree.type) {
        case EXPRESSION_STATEMENT:
          tree = tree.asExpressionStatement().expression;
          continue;
        case CALL_EXPRESSION:
          tree = tree.asCallExpression().operand;
          continue;
        case BINARY_OPERATOR:
          tree = tree.asBinaryOperator().left;
          continue;
        case CONDITIONAL_EXPRESSION:
          tree = tree.asConditionalExpression().condition;
          continue;
        case MEMBER_EXPRESSION:
          tree = tree.asMemberExpression().operand;
          continue;
        case MEMBER_LOOKUP_EXPRESSION:
          tree = tree.asMemberLookupExpression().operand;
          continue;
        case POSTFIX_EXPRESSION:
          tree = tree.asPostfixExpression().operand;
          continue;
        default:
          return tree;
      }
    }
  }

  private JSDocInfo handleJsDoc(
      com.google.javascript.jscomp.parsing.parser.Token token) {
    return handleJsDoc(getJsDoc(token));
  }

  private boolean isFunctionDeclaration(Node n) {
    return n.isFunction() && isStmtContainer(n.getParent());
  }

  private static boolean isStmtContainer(Node n) {
    return n.isBlock() || n.isScript();
  }

  private Node transform(ParseTree tree) {
    JSDocInfo info = handleJsDoc(tree);
    Node node = justTransform(tree);
    if (info != null) {
      node = maybeInjectCastNode(tree, info, node);
      node.setJSDocInfo(info);
    }
    setSourceInfo(node, tree);
    return node;
  }

  private Node maybeInjectCastNode(ParseTree node, JSDocInfo info, Node irNode) {
    if (node.type == ParseTreeType.PAREN_EXPRESSION
        && info.hasType()) {
      irNode = newNode(Token.CAST, irNode);
    }
    return irNode;
  }

  /**
   * NAMEs in parameters or variable declarations are special, because they can
   * have inline type docs attached.
   *
   * function f(/** string &#42;/ x) {}
   * annotates 'x' as a string.
   *
   * @see <a href="http://code.google.com/p/jsdoc-toolkit/wiki/InlineDocs">
   *   Using Inline Doc Comments</a>
   */
  private Node transformNodeWithInlineJsDoc(
      ParseTree node, boolean optionalInline) {
    JSDocInfo info = handleInlineJsDoc(node, optionalInline);
    Node irNode = justTransform(node);
    if (info != null) {
      irNode.setJSDocInfo(info);
    }
    setSourceInfo(irNode, node);
    return irNode;
  }

  private JSDocInfo handleInlineJsDoc(ParseTree node, boolean optional) {
    return handleInlineJsDoc(node.location, optional);
  }

  private JSDocInfo handleInlineJsDoc(
      com.google.javascript.jscomp.parsing.parser.Token token,
      boolean optional) {
    return handleInlineJsDoc(token.location, optional);
  }

  private JSDocInfo handleInlineJsDoc(
      SourceRange location,
      boolean optional) {
    Comment comment = getJsDoc(location);
    if (comment != null && (!optional || !comment.value.contains("@"))) {
      return recordJsDoc(location, parseInlineTypeDoc(comment));
    } else {
      return handleJsDoc(comment);
    }
  }

  private Node transformNumberAsString(LiteralToken token) {
    double value = normalizeNumber(token);
    Node irNode = newStringNode(getStringValue(value));
    JSDocInfo jsDocInfo = handleJsDoc(token);
    if (jsDocInfo != null) {
      irNode.setJSDocInfo(jsDocInfo);
    }
    setSourceInfo(irNode, token);
    return irNode;
  }

  private static String getStringValue(double value) {
    long longValue = (long) value;

    // Return "1" instead of "1.0"
    if (longValue == value) {
      return Long.toString(longValue);
    } else {
      return Double.toString(value);
    }
  }

  private static int lineno(ParseTree node) {
    // location lines start at zero, our AST starts at 1.
    return lineno(node.location.start);
  }

  private static int charno(ParseTree node) {
    return charno(node.location.start);
  }

  private static int lineno(SourcePosition location) {
    // location lines start at zero, our AST starts at 1.
    return location.line + 1;
  }

  private static int charno(SourcePosition location) {
    return location.column;
  }

  private void setSourceInfo(Node node, Node ref) {
    node.setLineno(ref.getLineno());
    node.setCharno(ref.getCharno());
    maybeSetLengthFrom(node, ref);
  }

  private void setSourceInfo(Node irNode, ParseTree node) {
    if (irNode.getLineno() == -1) {
      setSourceInfo(irNode, node.location.start, node.location.end);
    }
  }

  private void setSourceInfo(
      Node irNode, com.google.javascript.jscomp.parsing.parser.Token token) {
    setSourceInfo(irNode, token.location.start, token.location.end);
  }

  private void setSourceInfo(
      Node node, SourcePosition start, SourcePosition end) {
    if (node.getLineno() == -1) {
      // If we didn't already set the line, then set it now. This avoids
      // cases like ParenthesizedExpression where we just return a previous
      // node, but don't want the new node to get its parent's line number.
      int lineno = lineno(start);
      node.setLineno(lineno);
      int charno = charno(start);
      node.setCharno(charno);
      maybeSetLength(node, start, end);
    }
  }

  /**
   * Creates a JsDocInfoParser and parses the JsDoc string.
   *
   * Used both for handling individual JSDoc comments and for handling
   * file-level JSDoc comments (@fileoverview and @license).
   *
   * @param node The JsDoc Comment node to parse.
   * @return A JsDocInfoParser. Will contain either fileoverview JsDoc, or
   *     normal JsDoc, or no JsDoc (if the method parses to the wrong level).
   */
  private JsDocInfoParser createJsDocInfoParser(Comment node) {
    String comment = node.value;
    int lineno = lineno(node.location.start);
    int charno = charno(node.location.start);
    int position = node.location.start.offset;

    // The JsDocInfoParser expects the comment without the initial '/**'.
    int numOpeningChars = 3;
    JsDocInfoParser jsdocParser =
      new JsDocInfoParser(
          new JsDocTokenStream(comment.substring(numOpeningChars),
                               lineno,
                               charno + numOpeningChars),
          comment,
          position,
          sourceFile,
          config,
          errorReporter);
    jsdocParser.setFileLevelJsDocBuilder(fileLevelJsDocBuilder);
    jsdocParser.setFileOverviewJSDocInfo(fileOverviewInfo);
    jsdocParser.parse();
    return jsdocParser;
  }

  /**
   * Parses inline type info.
   */
  private JSDocInfo parseInlineTypeDoc(Comment node) {
    String comment = node.value;
    int lineno = lineno(node.location.start);
    int charno = charno(node.location.start);

    // The JsDocInfoParser expects the comment without the initial '/**'.
    int numOpeningChars = 3;
    JsDocInfoParser parser =
      new JsDocInfoParser(
          new JsDocTokenStream(comment.substring(numOpeningChars),
              lineno,
              charno + numOpeningChars),
          comment,
          node.location.start.offset,
          sourceFile,
          config,
          errorReporter);
    return parser.parseInlineTypeDoc();
  }

  // Set the length on the node if we're in IDE mode.
  private void maybeSetLength(
      Node node, SourcePosition start, SourcePosition end) {
    if (config.isIdeMode) {
      node.setLength(end.offset - start.offset);
    }
  }

  private void maybeSetLengthFrom(Node node, Node ref) {
    if (config.isIdeMode) {
      node.setLength(ref.getLength());
    }
  }

  private Node justTransform(ParseTree node) {
    return transformDispatcher.process(node);
  }

  private class TransformDispatcher {

    /**
     * Transforms the given node and then sets its type to Token.STRING if it
     * was Token.NAME. If its type was already Token.STRING, then quotes it.
     * Used for properties, as the old AST uses String tokens, while the new one
     * uses Name tokens for unquoted strings. For example, in
     * var o = {'a' : 1, b: 2};
     * the string 'a' is quoted, while the name b is turned into a string, but
     * unquoted.
     */
    private Node processObjectLitKeyAsString(
        com.google.javascript.jscomp.parsing.parser.Token token) {
      Node ret;
      if (token == null) {
        return createMissingExpressionNode();
      } else if (token.type == TokenType.IDENTIFIER) {
        ret = processName(token.asIdentifier(), true);
      } else if (token.type == TokenType.NUMBER) {
        ret = transformNumberAsString(token.asLiteral());
        ret.putBooleanProp(Node.QUOTED_PROP, true);
      } else {
        ret = processString(token.asLiteral());
        ret.putBooleanProp(Node.QUOTED_PROP, true);
      }
      Preconditions.checkState(ret.isString());
      return ret;
    }

    Node processComprehension(ComprehensionTree tree) {
      return unsupportedLanguageFeature(tree, "array/generator comprehensions");
    }

    Node processComprehensionFor(ComprehensionForTree tree) {
      return unsupportedLanguageFeature(tree, "array/generator comprehensions");
    }

    Node processComprehensionIf(ComprehensionIfTree tree) {
      return unsupportedLanguageFeature(tree, "array/generator comprehensions");
    }

    Node processArrayLiteral(ArrayLiteralExpressionTree tree) {
      Node node = newNode(Token.ARRAYLIT);
      for (ParseTree child : tree.elements) {
        Node c = transform(child);
        node.addChildToBack(c);
      }
      return node;
    }

    Node processArrayPattern(ArrayPatternTree tree) {
      maybeWarnEs6Feature(tree, "destructuring");

      Node node = newNode(Token.ARRAY_PATTERN);
      for (ParseTree child : tree.elements) {
        node.addChildToBack(transform(child));
      }
      return node;
    }

    Node processObjectPattern(ObjectPatternTree tree) {
      maybeWarnEs6Feature(tree, "destructuring");

      Node node = newNode(Token.OBJECT_PATTERN);
      for (ParseTree child : tree.fields) {
        node.addChildToBack(transform(child));
      }
      return node;
    }

    Node processAssignmentRestElement(AssignmentRestElementTree tree) {
      return newStringNode(Token.REST, tree.identifier.value);
    }

    Node processAstRoot(ProgramTree rootNode) {
      Node node = newNode(Token.SCRIPT);
      for (ParseTree child : rootNode.sourceElements) {
        node.addChildToBack(transform(child));
      }
      parseDirectives(node);
      return node;
    }

    /**
     * Parse the directives, encode them in the AST, and remove their nodes.
     *
     * For information on ES5 directives, see section 14.1 of
     * ECMA-262, Edition 5.
     *
     * It would be nice if Rhino would eventually take care of this for
     * us, but right now their directive-processing is a one-off.
     */
    private void parseDirectives(Node node) {
      // Remove all the directives, and encode them in the AST.
      Set<String> directives = null;
      while (isDirective(node.getFirstChild())) {
        String directive = node.removeFirstChild().getFirstChild().getString();
        if (directives == null) {
          directives = new HashSet<>();
        }
        directives.add(directive);
      }

      if (directives != null) {
        node.setDirectives(directives);
      }
    }

    private boolean isDirective(Node n) {
      if (n == null) {
        return false;
      }
      int nType = n.getType();
      return nType == Token.EXPR_RESULT &&
          n.getFirstChild().isString() &&
          ALLOWED_DIRECTIVES.contains(n.getFirstChild().getString());
    }

    Node processBlock(BlockTree blockNode) {
      Node node = newNode(Token.BLOCK);
      for (ParseTree child : blockNode.statements) {
        node.addChildToBack(transform(child));
      }
      return node;
    }

    Node processBreakStatement(BreakStatementTree statementNode) {
      Node node = newNode(Token.BREAK);
      if (statementNode.getLabel() != null) {
        Node labelName = transformLabelName(statementNode.name);
        node.addChildToBack(labelName);
      }
      return node;
    }

    Node transformLabelName(IdentifierToken token) {
      Node label =  newStringNode(Token.LABEL_NAME, token.value);
      setSourceInfo(label, token);
      return label;
    }

    Node processConditionalExpression(ConditionalExpressionTree exprNode) {
      return newNode(
          Token.HOOK,
          transform(exprNode.condition),
          transform(exprNode.left),
          transform(exprNode.right));
    }

    Node processContinueStatement(ContinueStatementTree statementNode) {
      Node node = newNode(Token.CONTINUE);
      if (statementNode.getLabel() != null) {
        Node labelName = transformLabelName(statementNode.name);
        node.addChildToBack(labelName);
      }
      return node;
    }

    Node processDoLoop(DoWhileStatementTree loopNode) {
      return newNode(
          Token.DO,
          transformBlock(loopNode.body),
          transform(loopNode.condition));
    }

    Node processElementGet(MemberLookupExpressionTree getNode) {
      return newNode(
          Token.GETELEM,
          transform(getNode.operand),
          transform(getNode.memberExpression));
    }

    Node processEmptyStatement(EmptyStatementTree exprNode) {
      return newNode(Token.EMPTY);
    }

    Node processExpressionStatement(ExpressionStatementTree statementNode) {
      Node node = newNode(Token.EXPR_RESULT);
      node.addChildToBack(transform(statementNode.expression));
      return node;
    }

    Node processForInLoop(ForInStatementTree loopNode) {
      Node initializer = transform(loopNode.initializer);
      ImmutableSet<Integer> invalidInitializers =
          ImmutableSet.of(Token.ARRAYLIT, Token.OBJECTLIT);
      if (invalidInitializers.contains(initializer.getType())) {
        errorReporter.error("Invalid LHS for a for-in loop", sourceName,
            lineno(loopNode.initializer), charno(loopNode.initializer));
      }
      return newNode(
          Token.FOR,
          initializer,
          transform(loopNode.collection),
          transformBlock(loopNode.body));
    }

    Node processForOf(ForOfStatementTree loopNode) {
      Node initializer = transform(loopNode.initializer);
      ImmutableSet<Integer> invalidInitializers =
          ImmutableSet.of(Token.ARRAYLIT, Token.OBJECTLIT);
      if (invalidInitializers.contains(initializer.getType())) {
        errorReporter.error("Invalid LHS for a for-of loop", sourceName,
            lineno(loopNode.initializer), charno(loopNode.initializer));
      }
      return newNode(
          Token.FOR_OF,
          initializer,
          transform(loopNode.collection),
          transformBlock(loopNode.body));
    }

    Node processForLoop(ForStatementTree loopNode) {
      Node node = newNode(
          Token.FOR,
          transformOrEmpty(loopNode.initializer, loopNode),
          transformOrEmpty(loopNode.condition, loopNode),
          transformOrEmpty(loopNode.increment, loopNode));
      node.addChildToBack(transformBlock(loopNode.body));
      return node;
    }

    Node transformOrEmpty(ParseTree tree, ParseTree parent) {
      if (tree == null) {
        Node n = newNode(Token.EMPTY);
        setSourceInfo(n, parent);
        return n;
      }
      return transform(tree);
    }

    Node transformOrEmpty(IdentifierToken token, ParseTree parent) {
      if (token == null) {
        Node n = newNode(Token.EMPTY);
        setSourceInfo(n, parent);
        return n;
      }
      return processName(token);
    }

    Node processFunctionCall(CallExpressionTree callNode) {
      Node node = newNode(Token.CALL,
                           transform(callNode.operand));
      for (ParseTree child : callNode.arguments.arguments) {
        node.addChildToBack(transform(child));
      }
      return node;
    }

    Node processFunction(FunctionDeclarationTree functionTree) {
      boolean isDeclaration = (functionTree.kind == FunctionDeclarationTree.Kind.DECLARATION);
      boolean isMember = (functionTree.kind == FunctionDeclarationTree.Kind.MEMBER);
      boolean isArrow = (functionTree.kind == FunctionDeclarationTree.Kind.ARROW);
      boolean isGenerator = functionTree.isGenerator;

      if (!isEs6Mode()) {
        if (isGenerator) {
          maybeWarnEs6Feature(functionTree, "generators");
        }

        if (isMember) {
          maybeWarnEs6Feature(functionTree, "member declarations");
        }

        if (isArrow) {
          maybeWarnEs6Feature(functionTree, "short function syntax");
        }
      }

      IdentifierToken name = functionTree.name;
      Node newName;
      if (name != null) {
        newName = processNameWithInlineJSDoc(name);
      } else {
        if (isDeclaration || isMember) {
          errorReporter.error(
            "unnamed function statement",
            sourceName,
            lineno(functionTree), charno(functionTree));

          // Return the bare minimum to put the AST in a valid state.
          newName = createMissingNameNode();
        } else {
          newName = newStringNode(Token.NAME, "");
        }

        // Old Rhino tagged the empty name node with the line number of the
        // declaration.
        setSourceInfo(newName, functionTree);
      }

      Node node = newNode(Token.FUNCTION);
      if (!isMember) {
        node.addChildToBack(newName);
      } else {
        Node emptyName = newStringNode(Token.NAME, "");
        setSourceInfo(emptyName, functionTree);
        node.addChildToBack(emptyName);
      }
      node.addChildToBack(transform(functionTree.formalParameterList));

      if (functionTree.returnType != null) {
        recordJsDoc(functionTree.returnType.location, node.getJSDocInfo());
        node.setDeclaredTypeExpression(convertTypeTree(functionTree.returnType));
      }

      Node bodyNode = transform(functionTree.functionBody);
      if (!isArrow && !bodyNode.isBlock()) {
        // When in ideMode the parser tries to parse some constructs the
        // compiler doesn't support, repair it here.
        Preconditions.checkState(config.isIdeMode);
        bodyNode = IR.block();
      }
      parseDirectives(bodyNode);
      node.addChildToBack(bodyNode);

      node.setIsGeneratorFunction(isGenerator);
      node.setIsArrowFunction(isArrow);

      Node result;

      if (functionTree.kind == FunctionDeclarationTree.Kind.MEMBER) {
        setSourceInfo(node, functionTree);
        Node member = newStringNode(Token.MEMBER_FUNCTION_DEF, name.value);
        member.addChildToBack(node);
        member.setStaticMember(functionTree.isStatic);
        result = member;
      } else {
        result = node;
      }

      return result;
    }

    Node processFormalParameterList(FormalParameterListTree tree) {
      Node params = newNode(Token.PARAM_LIST);
      for (ParseTree param : tree.parameters) {
        Node paramNode = transformNodeWithInlineJsDoc(param, false);
        // Children must be simple names, default parameters, rest
        // parameters, or destructuring patterns.
        Preconditions.checkState(paramNode.isName() || paramNode.isRest()
            || paramNode.isArrayPattern() || paramNode.isObjectPattern()
            || paramNode.isDefaultValue());
        params.addChildToBack(paramNode);
      }
      return params;
    }

    Node processDefaultParameter(DefaultParameterTree tree) {
      maybeWarnEs6Feature(tree, "default parameters");
      return newNode(Token.DEFAULT_VALUE,
          transform(tree.lhs), transform(tree.defaultValue));
    }

    Node processRestParameter(RestParameterTree tree) {
      maybeWarnEs6Feature(tree, "rest parameters");

      return newStringNode(Token.REST, tree.identifier.value);
    }

    Node processSpreadExpression(SpreadExpressionTree tree) {
      maybeWarnEs6Feature(tree, "spread expression");

      return newNode(Token.SPREAD, transform(tree.expression));
    }

    Node processIfStatement(IfStatementTree statementNode) {
      Node node = newNode(Token.IF);
      node.addChildToBack(transform(statementNode.condition));
      node.addChildToBack(transformBlock(statementNode.ifClause));
      if (statementNode.elseClause != null) {
        node.addChildToBack(transformBlock(statementNode.elseClause));
      }
      return node;
    }

    Node processBinaryExpression(BinaryOperatorTree exprNode) {
      return newNode(
          transformBinaryTokenType(exprNode.operator.type),
          transform(exprNode.left),
          transform(exprNode.right));
    }

    Node processDebuggerStatement(DebuggerStatementTree node) {
      return newNode(Token.DEBUGGER);
    }

    Node processThisExpression(ThisExpressionTree node) {
      return newNode(Token.THIS);
    }

    Node processLabeledStatement(LabelledStatementTree labelTree) {
      return newNode(Token.LABEL,
          transformLabelName(labelTree.name),
          transform(labelTree.statement));
    }

    Node processName(IdentifierExpressionTree nameNode) {
      return processName(nameNode, false);
    }

    Node processName(IdentifierExpressionTree nameNode, boolean asString) {
      return processName(nameNode.identifierToken, asString);
    }

    Node processName(IdentifierToken identifierToken) {
      return processName(identifierToken, false);
    }

    Node processName(IdentifierToken identifierToken, boolean asString) {
      Node node;
      if (asString) {
        node = newStringNode(Token.STRING, identifierToken.value);
      } else {
        JSDocInfo info = handleJsDoc(identifierToken);
        if (isReservedKeyword(identifierToken.toString())) {
          errorReporter.error(
            "identifier is a reserved word",
            sourceName,
            lineno(identifierToken.location.start),
            charno(identifierToken.location.start));
        }
        node = newStringNode(Token.NAME, identifierToken.value);
        if (info != null) {
          node.setJSDocInfo(info);
        }
      }
      setSourceInfo(node, identifierToken);
      return node;
    }

    Node processString(LiteralToken token) {
      Preconditions.checkArgument(token.type == TokenType.STRING);
      Node node = newStringNode(Token.STRING, normalizeString(token, false));
      setSourceInfo(node, token);
      return node;
    }

    Node processTemplateLiteralToken(LiteralToken token) {
      Preconditions.checkArgument(
          token.type == TokenType.NO_SUBSTITUTION_TEMPLATE
          || token.type == TokenType.TEMPLATE_HEAD
          || token.type == TokenType.TEMPLATE_MIDDLE
          || token.type == TokenType.TEMPLATE_TAIL);
      Node node = newStringNode(normalizeString(token, true));
      node.putProp(Node.RAW_STRING_VALUE, token.value);
      setSourceInfo(node, token);
      return node;
    }

    Node processNameWithInlineJSDoc(IdentifierToken identifierToken) {
      JSDocInfo info = handleInlineJsDoc(identifierToken, true);
      if (isReservedKeyword(identifierToken.toString())) {
        errorReporter.error(
          "identifier is a reserved word",
          sourceName,
          lineno(identifierToken.location.start),
          charno(identifierToken.location.start));
      }
      Node node = newStringNode(Token.NAME, identifierToken.toString());
      if (info != null) {
        node.setJSDocInfo(info);
      }
      setSourceInfo(node, identifierToken);
      return node;
    }

    private boolean isAllowedProp(String identifier) {
      if (config.languageMode == LanguageMode.ECMASCRIPT3) {
        return !TokenStream.isKeyword(identifier);
      }
      return true;
    }

    private boolean isReservedKeyword(String identifier) {
      if (config.languageMode == LanguageMode.ECMASCRIPT3) {
        return TokenStream.isKeyword(identifier);
      }
      return reservedKeywords != null && reservedKeywords.contains(identifier);
    }

    Node processNewExpression(NewExpressionTree exprNode) {
      Node node = newNode(
          Token.NEW,
          transform(exprNode.operand));
      if (exprNode.arguments != null) {
        for (ParseTree arg : exprNode.arguments.arguments) {
          node.addChildToBack(transform(arg));
        }
      }
      return node;
    }

    Node processNumberLiteral(LiteralExpressionTree literalNode) {
      double value = normalizeNumber(literalNode.literalToken.asLiteral());
      Node number = newNumberNode(value);
      setSourceInfo(number, literalNode);
      return number;
    }

    Node processObjectLiteral(ObjectLiteralExpressionTree objTree) {
      Node node = newNode(Token.OBJECTLIT);
      boolean maybeWarn = false;
      for (ParseTree el : objTree.propertyNameAndValues) {
        if (config.languageMode == LanguageMode.ECMASCRIPT3) {
          if (el.type == ParseTreeType.GET_ACCESSOR) {
            reportGetter(el);
            continue;
          } else if (el.type == ParseTreeType.SET_ACCESSOR) {
            reportSetter(el);
            continue;
          }
        }

        Node key = transform(el);
        if (!key.isComputedProp()
            && !key.isQuotedString()
            && !currentFileIsExterns
            && !isAllowedProp(key.getString())) {
          errorReporter.warning(INVALID_ES3_PROP_NAME, sourceName,
              key.getLineno(), key.getCharno());
        }
        if (key.getFirstChild() == null) {
          maybeWarn = true;
        }

        node.addChildToBack(key);
      }
      if (maybeWarn) {
        maybeWarnEs6Feature(objTree, "extended object literals");
      }
      return node;
    }

    Node processComputedPropertyDefinition(ComputedPropertyDefinitionTree tree) {
      maybeWarnEs6Feature(tree, "computed property");

      return newNode(Token.COMPUTED_PROP,
          transform(tree.property), transform(tree.value));
    }

    Node processComputedPropertyMemberVariable(ComputedPropertyMemberVariableTree tree) {
      maybeWarnEs6Feature(tree, "computed property");
      maybeWarnTypeSyntax(tree, "computed property");

      Node n = newNode(Token.COMPUTED_PROP, transform(tree.property));
      maybeProcessType(n, tree.declaredType);
      n.putBooleanProp(Node.COMPUTED_PROP_VARIABLE, true);
      n.setStaticMember(tree.isStatic);
      return n;
    }

    Node processComputedPropertyMethod(ComputedPropertyMethodTree tree) {
      maybeWarnEs6Feature(tree, "computed property");

      Node n = newNode(Token.COMPUTED_PROP,
          transform(tree.property), transform(tree.method));
      n.putBooleanProp(Node.COMPUTED_PROP_METHOD, true);
      if (tree.method.asFunctionDeclaration().isStatic) {
        n.setStaticMember(true);
      }
      return n;
    }

    Node processComputedPropertyGetter(ComputedPropertyGetterTree tree) {
      maybeWarnEs6Feature(tree, "computed property");

      Node key = transform(tree.property);
      Node body = transform(tree.body);
      Node function = IR.function(IR.name(""), IR.paramList(), body);
      function.useSourceInfoIfMissingFromForTree(body);
      Node n = newNode(Token.COMPUTED_PROP, key, function);
      n.putBooleanProp(Node.COMPUTED_PROP_GETTER, true);
      return n;
    }

    Node processComputedPropertySetter(ComputedPropertySetterTree tree) {
      maybeWarnEs6Feature(tree, "computed property");

      Node key = transform(tree.property);
      Node body = transform(tree.body);
      Node paramList = IR.paramList(safeProcessName(tree.parameter));
      Node function = IR.function(IR.name(""), paramList, body);
      function.useSourceInfoIfMissingFromForTree(body);
      Node n = newNode(Token.COMPUTED_PROP, key, function);
      n.putBooleanProp(Node.COMPUTED_PROP_SETTER, true);
      return n;
    }

    Node processGetAccessor(GetAccessorTree tree) {
      Node key = processObjectLitKeyAsString(tree.propertyName);
      key.setType(Token.GETTER_DEF);
      Node body = transform(tree.body);
      Node dummyName = IR.name("");
      setSourceInfo(dummyName, tree.body);
      Node paramList = IR.paramList();
      setSourceInfo(paramList, tree.body);
      Node value = IR.function(dummyName, paramList, body);
      setSourceInfo(value, tree.body);
      key.addChildToFront(value);
      key.setStaticMember(tree.isStatic);
      return key;
    }

    Node processSetAccessor(SetAccessorTree tree) {
      Node key = processObjectLitKeyAsString(tree.propertyName);
      key.setType(Token.SETTER_DEF);
      Node body = transform(tree.body);
      Node dummyName = IR.name("");
      setSourceInfo(dummyName, tree.propertyName);
      Node paramList = IR.paramList(
          safeProcessName(tree.parameter));
      setSourceInfo(paramList, tree.parameter);
      Node value = IR.function(dummyName, paramList, body);
      setSourceInfo(value, tree.body);
      key.addChildToFront(value);
      key.setStaticMember(tree.isStatic);
      return key;
    }

    Node processPropertyNameAssignment(PropertyNameAssignmentTree tree) {
      Node key = processObjectLitKeyAsString(tree.name);
      key.setType(Token.STRING_KEY);
      if (tree.value != null) {
        key.addChildToFront(transform(tree.value));
      }
      return key;
    }

    private Node safeProcessName(IdentifierToken identifierToken) {
      if (identifierToken == null) {
        return createMissingExpressionNode();
      } else {
        return processName(identifierToken);
      }
    }

    Node processParenthesizedExpression(ParenExpressionTree exprNode) {
      return transform(exprNode.expression);
    }

    Node processPropertyGet(MemberExpressionTree getNode) {
      Node leftChild = transform(getNode.operand);
      IdentifierToken nodeProp = getNode.memberName;
      Node rightChild = processObjectLitKeyAsString(nodeProp);
      if (!rightChild.isQuotedString()
          && !currentFileIsExterns
          && !isAllowedProp(
            rightChild.getString())) {
        errorReporter.warning(INVALID_ES3_PROP_NAME, sourceName,
            rightChild.getLineno(), rightChild.getCharno());
      }
      return newNode(Token.GETPROP, leftChild, rightChild);
    }

    Node processRegExpLiteral(LiteralExpressionTree literalTree) {
      LiteralToken token = literalTree.literalToken.asLiteral();
      Node literalStringNode = newStringNode(normalizeRegex(token));
      // TODO(johnlenz): fix the source location.
      setSourceInfo(literalStringNode, token);
      Node node = newNode(Token.REGEXP, literalStringNode);

      String rawRegex = token.value;
      int lastSlash = rawRegex.lastIndexOf('/');
      String flags = "";
      if (lastSlash < rawRegex.length()) {
        flags = rawRegex.substring(lastSlash + 1);
      }
      validateRegExpFlags(literalTree, flags);

      if (!flags.isEmpty()) {
        Node flagsNode = newStringNode(flags);
        // TODO(johnlenz): fix the source location.
        setSourceInfo(flagsNode, token);
        node.addChildToBack(flagsNode);
      }
      return node;
    }

    private void validateRegExpFlags(LiteralExpressionTree tree, String flags) {
      for (char flag : Lists.charactersOf(flags)) {
        switch (flag) {
          case 'g': case 'i': case 'm':
            break;
          case 'u': case 'y':
            maybeWarnEs6Feature(tree, "new RegExp flag '" + flag + "'");
            break;
          default:
            errorReporter.error(
                "Invalid RegExp flag '" + flag + "'",
                sourceName,
                lineno(tree), charno(tree));
        }
      }
    }

    Node processReturnStatement(ReturnStatementTree statementNode) {
      Node node = newNode(Token.RETURN);
      if (statementNode.expression != null) {
        node.addChildToBack(transform(statementNode.expression));
      }
      return node;
    }

    Node processStringLiteral(LiteralExpressionTree literalTree) {
      LiteralToken token = literalTree.literalToken.asLiteral();

      Node n = processString(token);
      String value = n.getString();
      if (value.indexOf('\u000B') != -1) {
        // NOTE(nicksantos): In JavaScript, there are 3 ways to
        // represent a vertical tab: \v, \x0B, \u000B.
        // The \v notation was added later, and is not understood
        // on IE. So we need to preserve it as-is. This is really
        // obnoxious, because we do not have a good way to represent
        // how the original string was encoded without making the
        // representation of strings much more complicated.
        //
        // To handle this, we look at the original source test, and
        // mark the string as \v-encoded or not. If a string is
        // \v encoded, then all the vertical tabs in that string
        // will be encoded with a \v.
        int start = token.location.start.offset;
        int end = token.location.end.offset;
        if (start < sourceString.length() &&
            (sourceString.substring(
                start, Math.min(sourceString.length(), end)).contains("\\v"))) {
          n.putBooleanProp(Node.SLASH_V, true);
        }
      }
      return n;
    }

    Node processTemplateLiteral(TemplateLiteralExpressionTree tree) {
      maybeWarnEs6Feature(tree, "template literals");
      Node node = tree.operand == null
          ? newNode(Token.TEMPLATELIT)
          : newNode(Token.TEMPLATELIT, transform(tree.operand));
      for (ParseTree child : tree.elements) {
        node.addChildToBack(transform(child));
      }
      return node;
    }

    Node processTemplateLiteralPortion(TemplateLiteralPortionTree tree) {
      return processTemplateLiteralToken(tree.value.asLiteral());
    }

    Node processTemplateSubstitution(TemplateSubstitutionTree tree) {
      return newNode(Token.TEMPLATELIT_SUB, transform(tree.expression));
    }

    Node processSwitchCase(CaseClauseTree caseNode) {
      ParseTree expr = caseNode.expression;
      Node node = newNode(Token.CASE, transform(expr));
      Node block = newNode(Token.BLOCK);
      block.putBooleanProp(Node.SYNTHETIC_BLOCK_PROP, true);
      setSourceInfo(block, caseNode);
      if (caseNode.statements != null) {
        for (ParseTree child : caseNode.statements) {
          block.addChildToBack(transform(child));
        }
      }
      node.addChildToBack(block);
      return node;
    }

    Node processSwitchDefault(DefaultClauseTree caseNode) {
      Node node = newNode(Token.DEFAULT_CASE);
      Node block = newNode(Token.BLOCK);
      block.putBooleanProp(Node.SYNTHETIC_BLOCK_PROP, true);
      setSourceInfo(block, caseNode);
      if (caseNode.statements != null) {
        for (ParseTree child : caseNode.statements) {
          block.addChildToBack(transform(child));
        }
      }
      node.addChildToBack(block);
      return node;
    }

    Node processSwitchStatement(SwitchStatementTree statementNode) {
      Node node = newNode(Token.SWITCH,
          transform(statementNode.expression));
      for (ParseTree child : statementNode.caseClauses) {
        node.addChildToBack(transform(child));
      }
      return node;
    }

    Node processThrowStatement(ThrowStatementTree statementNode) {
      return newNode(Token.THROW,
          transform(statementNode.value));
    }

    Node processTryStatement(TryStatementTree statementNode) {
      Node node = newNode(Token.TRY,
          transformBlock(statementNode.body));
      Node block = newNode(Token.BLOCK);
      boolean lineSet = false;

      ParseTree cc = statementNode.catchBlock;
      if (cc != null) {
        // Mark the enclosing block at the same line as the first catch
        // clause.
        setSourceInfo(block, cc);
        lineSet = true;
        block.addChildToBack(transform(cc));
      }

      node.addChildToBack(block);

      ParseTree finallyBlock = statementNode.finallyBlock;
      if (finallyBlock != null) {
        node.addChildToBack(transformBlock(finallyBlock));
      }

      // If we didn't set the line on the catch clause, then
      // we've got an empty catch clause.  Set its line to be the same
      // as the finally block (to match Old Rhino's behavior.)
      if (!lineSet && (finallyBlock != null)) {
        setSourceInfo(block, finallyBlock);
      }

      return node;
    }

    Node processCatchClause(CatchTree clauseNode) {
      return newNode(Token.CATCH,
          transform(clauseNode.exception),
          transformBlock(clauseNode.catchBody));
    }

    Node processFinally(FinallyTree finallyNode) {
      return transformBlock(finallyNode.block);
    }

    Node processUnaryExpression(UnaryExpressionTree exprNode) {
      int type = transformUnaryTokenType(exprNode.operator.type);
      Node operand = transform(exprNode.operand);
      if (type == Token.NEG && operand.isNumber()) {
        operand.setDouble(-operand.getDouble());
        return operand;
      } else {
        if (type == Token.DELPROP &&
            !(operand.isGetProp() ||
              operand.isGetElem() ||
              operand.isName())) {
          String msg =
              "Invalid delete operand. Only properties can be deleted.";
          errorReporter.error(
              msg,
              sourceName,
              operand.getLineno(), 0);
        }

        return newNode(type, operand);
      }
    }

    Node processPostfixExpression(PostfixExpressionTree exprNode) {
      int type = transformPostfixTokenType(exprNode.operator.type);
      Node node = newNode(type, transform(exprNode.operand));
      node.putBooleanProp(Node.INCRDECR_PROP, true);
      return node;
    }

    Node processVariableStatement(VariableStatementTree stmt) {
      // skip the special handling so the doc is attached in the right place.
      return justTransform(stmt.declarations);
    }

    Node processVariableDeclarationList(VariableDeclarationListTree decl) {
      int declType;
      switch (decl.declarationType) {
        case CONST:
          if (!config.acceptConstKeyword) {
            maybeWarnEs6Feature(decl, "const declarations");
          }

          if (isEs6Mode()) {
            declType = Token.CONST;
          } else {
            // Code uses the 'const' keyword which is non-standard in ES5 and
            // below. Just treat it as though it was a 'var'.
            // TODO(tbreisacher): Treat this node as though it had an @const
            // annotation.
            declType = Token.VAR;
          }
          break;
        case LET:
          maybeWarnEs6Feature(decl, "let declarations");
          declType = Token.LET;
          break;
        case VAR:
          declType = Token.VAR;
          break;
        default:
          throw new IllegalStateException();
      }

      Node node = newNode(declType);
      for (VariableDeclarationTree child : decl.declarations) {
        node.addChildToBack(
            transformNodeWithInlineJsDoc(child, true));
      }
      return node;
    }

    Node processVariableDeclaration(VariableDeclarationTree decl) {
      Node node = transformNodeWithInlineJsDoc(decl.lvalue, true);
      if (decl.initializer != null) {
        Node initializer = transform(decl.initializer);
        node.addChildToBack(initializer);
      }
      maybeProcessType(node, decl.declaredType);
      return node;
    }

    Node processWhileLoop(WhileStatementTree stmt) {
      return newNode(
          Token.WHILE,
          transform(stmt.condition),
          transformBlock(stmt.body));
    }

    Node processWithStatement(WithStatementTree stmt) {
      return newNode(
          Token.WITH,
          transform(stmt.expression),
          transformBlock(stmt.body));
    }

    Node processMissingExpression(MissingPrimaryExpressionTree tree) {
      // This will already have been reported as an error by the parser.
      // Try to create something valid that ide mode might be able to
      // continue with.
      return createMissingExpressionNode();
    }

    private Node createMissingNameNode() {
      return newStringNode(Token.NAME, "__missing_name__");
    }

    private Node createMissingExpressionNode() {
      return newStringNode(Token.NAME, "__missing_expression__");
    }

    Node processIllegalToken(ParseTree node) {
      errorReporter.error(
          "Unsupported syntax: " + node.type, sourceName, lineno(node), 0);
      return newNode(Token.EMPTY);
    }

    void reportGetter(ParseTree node) {
      errorReporter.error(
          GETTER_ERROR_MESSAGE,
          sourceName,
          lineno(node), 0);
    }

    void reportSetter(ParseTree node) {
      errorReporter.error(
          SETTER_ERROR_MESSAGE,
          sourceName,
          lineno(node), 0);
    }

    Node processBooleanLiteral(LiteralExpressionTree literal) {
      return newNode(transformBooleanTokenType(
          literal.literalToken.type));
    }

    Node processNullLiteral(LiteralExpressionTree literal) {
      return newNode(Token.NULL);
    }

    Node processNull(NullTree literal) {
      // NOTE: This is not a NULL literal but a placeholder node such as in
      // an array with "holes".
      return newNode(Token.EMPTY);
    }

    Node processCommaExpression(CommaExpressionTree tree) {
      Node root = newNode(Token.COMMA);
      SourcePosition start = tree.expressions.get(0).location.start;
      SourcePosition end = tree.expressions.get(1).location.end;
      setSourceInfo(root, start, end);
      for (ParseTree expr : tree.expressions) {
        int count = root.getChildCount();
        if (count < 2) {
          root.addChildrenToBack(transform(expr));
        } else {
          end = expr.location.end;
          root = newNode(Token.COMMA, root, transform(expr));
          setSourceInfo(root, start, end);
        }
      }
      return root;
    }

    Node processClassDeclaration(ClassDeclarationTree tree) {
      maybeWarnEs6Feature(tree, "class");

      Node name = transformOrEmpty(tree.name, tree);
      Node superClass = transformOrEmpty(tree.superClass, tree);

      Node body = newNode(Token.CLASS_MEMBERS);
      setSourceInfo(body, tree);
      for (ParseTree child : tree.elements) {
        body.addChildToBack(transform(child));
      }

      return newNode(Token.CLASS, name, superClass, body);
    }

    Node processInterfaceDeclaration(InterfaceDeclarationTree tree) {
      maybeWarnTypeSyntax(tree, "interface");

      Node name = processName(tree.name);
      Node superInterfaces = transformListOrEmpty(Token.INTERFACE_EXTENDS, tree.superInterfaces);

      Node body = newNode(Token.INTERFACE_MEMBERS);
      setSourceInfo(body, tree);
      for (ParseTree child : tree.elements) {
        body.addChildToBack(transform(child));
      }

      return newNode(Token.INTERFACE, name, superInterfaces, body);
    }

    Node processEnumDeclaration(EnumDeclarationTree tree) {
      maybeWarnTypeSyntax(tree, "enum");

      Node name = processName(tree.name);
      Node body = newNode(Token.ENUM_MEMBERS);
      setSourceInfo(body, tree);
      for (ParseTree child : tree.members) {
        body.addChildrenToBack(transform(child));
      }

      return newNode(Token.ENUM, name, body);
    }

    Node processSuper(SuperExpressionTree tree) {
      maybeWarnEs6Feature(tree, "super");
      return newNode(Token.SUPER);
    }

    Node processMemberVariable(MemberVariableTree tree) {
      Node member = newStringNode(Token.MEMBER_VARIABLE_DEF, tree.name.value);
      maybeProcessType(member, tree.declaredType);
      member.setStaticMember(tree.isStatic);
      return member;
    }

    Node processYield(YieldExpressionTree tree) {
      Node yield = newNode(Token.YIELD);
      if (tree.expression != null) {
        yield.addChildToBack(transform(tree.expression));
      }
      yield.setYieldFor(tree.isYieldFor);
      return yield;
    }

    Node processExportDecl(ExportDeclarationTree tree) {
      maybeWarnEs6Feature(tree, "modules");
      Node decls = null;
      if (tree.isExportAll) {
        Preconditions.checkState(
            tree.declaration == null &&
            tree.exportSpecifierList == null);
      } else if (tree.declaration != null) {
        Preconditions.checkState(tree.exportSpecifierList == null);
        decls = transform(tree.declaration);
      } else {
        decls = transformList(Token.EXPORT_SPECS, tree.exportSpecifierList);
      }
      if (decls == null) {
        decls = newNode(Token.EMPTY);
      }
      setSourceInfo(decls, tree);
      Node export = newNode(Token.EXPORT, decls);
      if (tree.from != null) {
        Node from = processString(tree.from);
        export.addChildToBack(from);
      }

      export.putBooleanProp(Node.EXPORT_ALL_FROM, tree.isExportAll);
      export.putBooleanProp(Node.EXPORT_DEFAULT, tree.isDefault);
      return export;
    }

    Node processExportSpec(ExportSpecifierTree tree) {
      Node exportSpec = newNode(Token.EXPORT_SPEC,
          processName(tree.importedName));
      if (tree.destinationName != null) {
        exportSpec.addChildToBack(processName(tree.destinationName));
      }
      return exportSpec;
    }

    Node processImportDecl(ImportDeclarationTree tree) {
      maybeWarnEs6Feature(tree, "modules");

      Node firstChild = transformOrEmpty(tree.defaultBindingIdentifier, tree);
      Node secondChild = (tree.nameSpaceImportIdentifier != null)
          ? newStringNode(Token.IMPORT_STAR, tree.nameSpaceImportIdentifier.value)
          : transformListOrEmpty(Token.IMPORT_SPECS, tree.importSpecifierList);
      Node thirdChild = processString(tree.moduleSpecifier);

      return newNode(Token.IMPORT, firstChild, secondChild, thirdChild);
    }

    Node processImportSpec(ImportSpecifierTree tree) {
      Node importSpec = newNode(Token.IMPORT_SPEC,
          processName(tree.importedName));
      if (tree.destinationName != null) {
        importSpec.addChildToBack(processName(tree.destinationName));
      }
      return importSpec;
    }

    Node processModuleImport(ModuleImportTree tree) {
      maybeWarnEs6Feature(tree, "modules");
      Node module = newNode(Token.MODULE,
          processName(tree.name),
          processString(tree.from));
      return module;
    }

    Node processTypeName(TypeNameTree tree) {
      Node typeNode;
      if (tree.segments.size() == 1) {
        String typeName = tree.segments.get(0);
        switch (typeName) {
          case "any":
            typeNode = anyType();
            break;
          case "number":
            typeNode = numberType();
            break;
          case "boolean":
            typeNode = booleanType();
            break;
          case "string":
            typeNode = stringType();
            break;
          case "void":
            typeNode = voidType();
            break;
          case "undefined":
            typeNode = undefinedType();
            break;
          default:
            typeNode = namedType(tree.segments);
            break;
        }
      } else {
        typeNode = namedType(tree.segments);
      }
      setSourceInfo(typeNode, tree);
      return typeNode;
    }

    Node processTypedParameter(TypedParameterTree typeAnnotation) {
      maybeWarnTypeSyntax(typeAnnotation);
      Node param = process(typeAnnotation.param);
      maybeProcessType(param, typeAnnotation.typeAnnotation);
      return param;
    }

    private void maybeProcessType(Node typeTarget, ParseTree typeTree) {
      if (typeTree == null) {
        return;
      }
      recordJsDoc(typeTree.location, typeTarget.getJSDocInfo());
      Node typeExpression = convertTypeTree(typeTree);
      typeTarget.setDeclaredTypeExpression(typeExpression);
    }

    private Node convertTypeTree(ParseTree typeTree) {
      maybeWarnTypeSyntax(typeTree);
      return process(typeTree);
    }

    Node processParameterizedType(ParameterizedTypeTree tree) {
      ImmutableList.Builder<TypeDeclarationNode> arguments = ImmutableList.builder();
      for (ParseTree arg : tree.typeArguments) {
        arguments.add((TypeDeclarationNode) process(arg));
      }
      TypeDeclarationNode typeName = (TypeDeclarationNode) process(tree.typeName);
      return parameterizedType(typeName, arguments.build());
    }

    Node processArrayType(ArrayTypeTree tree) {
      return arrayType(process(tree.elementType));
    }

    Node processUnionType(UnionTypeTree tree) {
      ImmutableList.Builder<TypeDeclarationNode> options = ImmutableList.builder();
      for (ParseTree option : tree.types) {
        options.add((TypeDeclarationNode) process(option));
      }
      return unionType(options.build());
    }

    Node processFunctionType(FunctionTypeTree tree) {
      LinkedHashMap<String, TypeDeclarationNode> parameters = new LinkedHashMap<>();
      for (ParseTree param : tree.formalParameterList.parameters) {
        TypedParameterTree typedParam = param.asTypedParameter();
        parameters.put(
            typedParam.param.asIdentifierExpression().identifierToken.toString(),
            (TypeDeclarationNode) process(typedParam.typeAnnotation));
      }
      return functionType(process(tree.returnType), parameters, null, null);
    }

    private Node transformList(
        int type, ImmutableList<ParseTree> list) {
      Node n = newNode(type);
      for (ParseTree tree : list) {
        n.addChildToBack(transform(tree));
      }
      return n;
    }

    private Node transformListOrEmpty(
        int type, ImmutableList<ParseTree> list) {
      if (list == null || list.isEmpty()) {
        return newNode(Token.EMPTY);
      } else {
        return transformList(type, list);
      }
    }

    void maybeWarnEs6Feature(ParseTree node, String feature) {
      if (!isEs6Mode()) {
        errorReporter.warning(
            "this language feature is only supported in es6 mode: " + feature,
            sourceName,
            lineno(node), charno(node));
      }
    }

    void maybeWarnTypeSyntax(ParseTree node, String feature) {
      if (config.languageMode != LanguageMode.ECMASCRIPT6_TYPED) {
        errorReporter.warning(
            "type syntax is only supported in ES6 typed mode: " + feature,
            sourceName,
            lineno(node),
            charno(node));
      }
      recordTypeSyntax(node.location);
    }

    void maybeWarnTypeSyntax(ParseTree node) {
      maybeWarnTypeSyntax(node, "type annotation");
    }

    Node unsupportedLanguageFeature(ParseTree node, String feature) {
      errorReporter.error(
          "unsupported language feature: " + feature,
          sourceName,
          lineno(node), charno(node));
      return createMissingExpressionNode();
    }

    Node processLiteralExpression(LiteralExpressionTree expr) {
      switch (expr.literalToken.type) {
        case NUMBER:
          return processNumberLiteral(expr);
        case STRING:
          return processStringLiteral(expr);
        case FALSE:
        case TRUE:
          return processBooleanLiteral(expr);
        case NULL:
          return processNullLiteral(expr);
        case REGULAR_EXPRESSION:
          return processRegExpLiteral(expr);
        default:
          throw new IllegalStateException("Unexpected literal type: "
              + expr.literalToken.getClass() + " type: "
              + expr.literalToken.type);
      }
    }

    public Node process(ParseTree node) {
      switch (node.type) {
        case BINARY_OPERATOR:
          return processBinaryExpression(node.asBinaryOperator());
        case ARRAY_LITERAL_EXPRESSION:
          return processArrayLiteral(node.asArrayLiteralExpression());
        case TEMPLATE_LITERAL_EXPRESSION:
          return processTemplateLiteral(node.asTemplateLiteralExpression());
        case TEMPLATE_LITERAL_PORTION:
          return processTemplateLiteralPortion(node.asTemplateLiteralPortion());
        case TEMPLATE_SUBSTITUTION:
          return processTemplateSubstitution(node.asTemplateSubstitution());
        case UNARY_EXPRESSION:
          return processUnaryExpression(node.asUnaryExpression());
        case BLOCK:
          return processBlock(node.asBlock());
        case BREAK_STATEMENT:
          return processBreakStatement(node.asBreakStatement());
        case CALL_EXPRESSION:
          return processFunctionCall(node.asCallExpression());
        case CASE_CLAUSE:
          return processSwitchCase(node.asCaseClause());
        case DEFAULT_CLAUSE:
          return processSwitchDefault(node.asDefaultClause());
        case CATCH:
          return processCatchClause(node.asCatch());
        case CONTINUE_STATEMENT:
          return processContinueStatement(node.asContinueStatement());
        case DO_WHILE_STATEMENT:
          return processDoLoop(node.asDoWhileStatement());
        case EMPTY_STATEMENT:
          return processEmptyStatement(node.asEmptyStatement());
        case EXPRESSION_STATEMENT:
          return processExpressionStatement(node.asExpressionStatement());
        case DEBUGGER_STATEMENT:
          return processDebuggerStatement(node.asDebuggerStatement());
        case THIS_EXPRESSION:
          return processThisExpression(node.asThisExpression());
        case FOR_STATEMENT:
          return processForLoop(node.asForStatement());
        case FOR_IN_STATEMENT:
          return processForInLoop(node.asForInStatement());
        case FUNCTION_DECLARATION:
          return processFunction(node.asFunctionDeclaration());
        case MEMBER_LOOKUP_EXPRESSION:
          return processElementGet(node.asMemberLookupExpression());
        case MEMBER_EXPRESSION:
          return processPropertyGet(node.asMemberExpression());
        case CONDITIONAL_EXPRESSION:
          return processConditionalExpression(node.asConditionalExpression());
        case IF_STATEMENT:
          return processIfStatement(node.asIfStatement());
        case LABELLED_STATEMENT:
          return processLabeledStatement(node.asLabelledStatement());
        case PAREN_EXPRESSION:
          return processParenthesizedExpression(node.asParenExpression());
        case IDENTIFIER_EXPRESSION:
          return processName(node.asIdentifierExpression());
        case NEW_EXPRESSION:
          return processNewExpression(node.asNewExpression());
        case OBJECT_LITERAL_EXPRESSION:
          return processObjectLiteral(node.asObjectLiteralExpression());
        case COMPUTED_PROPERTY_DEFINITION:
          return processComputedPropertyDefinition(node.asComputedPropertyDefinition());
        case COMPUTED_PROPERTY_GETTER:
          return processComputedPropertyGetter(node.asComputedPropertyGetter());
        case COMPUTED_PROPERTY_MEMBER_VARIABLE:
          return processComputedPropertyMemberVariable(node.asComputedPropertyMemberVariable());
        case COMPUTED_PROPERTY_METHOD:
          return processComputedPropertyMethod(node.asComputedPropertyMethod());
        case COMPUTED_PROPERTY_SETTER:
          return processComputedPropertySetter(node.asComputedPropertySetter());
        case RETURN_STATEMENT:
          return processReturnStatement(node.asReturnStatement());
        case POSTFIX_EXPRESSION:
          return processPostfixExpression(node.asPostfixExpression());
        case PROGRAM:
          return processAstRoot(node.asProgram());
        case LITERAL_EXPRESSION: // STRING, NUMBER, TRUE, FALSE, NULL, REGEXP
          return processLiteralExpression(node.asLiteralExpression());
        case SWITCH_STATEMENT:
          return processSwitchStatement(node.asSwitchStatement());
        case THROW_STATEMENT:
          return processThrowStatement(node.asThrowStatement());
        case TRY_STATEMENT:
          return processTryStatement(node.asTryStatement());
        case VARIABLE_STATEMENT: // var const let
          return processVariableStatement(node.asVariableStatement());
        case VARIABLE_DECLARATION_LIST:
          return processVariableDeclarationList(node.asVariableDeclarationList());
        case VARIABLE_DECLARATION:
          return processVariableDeclaration(node.asVariableDeclaration());
        case WHILE_STATEMENT:
          return processWhileLoop(node.asWhileStatement());
        case WITH_STATEMENT:
          return processWithStatement(node.asWithStatement());

        case COMMA_EXPRESSION:
          return processCommaExpression(node.asCommaExpression());
        case NULL: // this is not the null literal
          return processNull(node.asNull());
        case FINALLY:
          return processFinally(node.asFinally());

        case MISSING_PRIMARY_EXPRESSION:
          return processMissingExpression(node.asMissingPrimaryExpression());

        case PROPERTY_NAME_ASSIGNMENT:
          return processPropertyNameAssignment(node.asPropertyNameAssignment());
        case GET_ACCESSOR:
          return processGetAccessor(node.asGetAccessor());
        case SET_ACCESSOR:
          return processSetAccessor(node.asSetAccessor());
        case FORMAL_PARAMETER_LIST:
          return processFormalParameterList(node.asFormalParameterList());

        case CLASS_DECLARATION:
          return processClassDeclaration(node.asClassDeclaration());
        case SUPER_EXPRESSION:
          return processSuper(node.asSuperExpression());
        case YIELD_EXPRESSION:
          return processYield(node.asYieldStatement());
        case FOR_OF_STATEMENT:
          return processForOf(node.asForOfStatement());

        case EXPORT_DECLARATION:
          return processExportDecl(node.asExportDeclaration());
        case EXPORT_SPECIFIER:
          return processExportSpec(node.asExportSpecifier());
        case IMPORT_DECLARATION:
          return processImportDecl(node.asImportDeclaration());
        case IMPORT_SPECIFIER:
          return processImportSpec(node.asImportSpecifier());
        case MODULE_IMPORT:
          return processModuleImport(node.asModuleImport());

        case ARRAY_PATTERN:
          return processArrayPattern(node.asArrayPattern());
        case OBJECT_PATTERN:
          return processObjectPattern(node.asObjectPattern());
        case ASSIGNMENT_REST_ELEMENT:
          return processAssignmentRestElement(node.asAssignmentRestElement());

        case COMPREHENSION:
          return processComprehension(node.asComprehension());
        case COMPREHENSION_FOR:
          return processComprehensionFor(node.asComprehensionFor());
        case COMPREHENSION_IF:
          return processComprehensionIf(node.asComprehensionIf());

        case DEFAULT_PARAMETER:
          return processDefaultParameter(node.asDefaultParameter());
        case REST_PARAMETER:
          return processRestParameter(node.asRestParameter());
        case SPREAD_EXPRESSION:
          return processSpreadExpression(node.asSpreadExpression());

          // TODO(johnlenz): handle these or remove parser support
        case ARGUMENT_LIST:
          break;

        // ES6 Typed
        case TYPE_NAME:
          return processTypeName(node.asTypeName());
        case TYPE_ANNOTATION:
          return processTypedParameter(node.asTypedParameter());
        case PARAMETERIZED_TYPE_TREE:
          return processParameterizedType(node.asParameterizedType());
        case ARRAY_TYPE:
          return processArrayType(node.asArrayType());
        case UNION_TYPE:
          return processUnionType(node.asUnionType());
        case FUNCTION_TYPE:
          return processFunctionType(node.asFunctionType());
        case MEMBER_VARIABLE:
          return processMemberVariable(node.asMemberVariable());

        case INTERFACE_DECLARATION:
          return processInterfaceDeclaration(node.asInterfaceDeclaration());
        case ENUM_DECLARATION:
          return processEnumDeclaration(node.asEnumDeclaration());

        default:
          break;
      }
      return processIllegalToken(node);
    }
  }

  private String normalizeRegex(LiteralToken token) {
    String value = token.value;
    int lastSlash = value.lastIndexOf('/');
    return value.substring(1, lastSlash);
  }


  private String normalizeString(LiteralToken token, boolean templateLiteral) {
    String value = token.value;
    if (templateLiteral) {
      // <CR><LF> and <CR> are normalized as <LF> for raw string value
      value = value.replaceAll("(?<!\\\\)\r(\n)?", "\n");
    }
    int start = templateLiteral ? 0 : 1; // skip the leading quote
    int cur = value.indexOf('\\');
    if (cur == -1) {
      // short circuit no escapes.
      return templateLiteral ? value : value.substring(1, value.length() - 1);
    }
    StringBuilder result = new StringBuilder();
    while (cur != -1) {
      if (cur - start > 0) {
        result.append(value, start, cur);
      }
      cur += 1; // skip the escape char.
      char c = value.charAt(cur);
      switch (c) {
        case '\'':
        case '"':
        case '\\':
          result.append(c);
          break;
        case 'b':
          result.append('\b');
          break;
        case 'f':
          result.append('\f');
          break;
        case 'n':
          result.append('\n');
          break;
        case 'r':
          result.append('\r');
          break;
        case 't':
          result.append('\t');
          break;
        case 'v':
          result.append('\u000B');
          break;
        case '\n':
          if (isEs5OrBetterMode()) {
            errorReporter.warning(STRING_CONTINUATION_WARNING,
                sourceName,
                lineno(token.location.start), charno(token.location.start));
          } else {
            errorReporter.error(STRING_CONTINUATION_ERROR,
                sourceName,
                lineno(token.location.start), charno(token.location.start));
          }
          // line continuation, skip the line break
          break;
        case '0': case '1': case '2': case '3': case '4': case '5': case '6': case '7':
          char next1 = value.charAt(cur + 1);

          if (inStrictContext()) {
            if (c == '0' && !isOctalDigit(next1)) {
              // No warning: "\0" followed by a character which is not an octal digit
              // is allowed in strict mode.
            } else {
              errorReporter.warning(OCTAL_STRING_LITERAL_WARNING,
                  sourceName,
                  lineno(token.location.start), charno(token.location.start));
            }
          }

          if (!isOctalDigit(next1)) {
            result.append((char) octaldigit(c));
          } else {
            char next2 = value.charAt(cur + 2);
            if (!isOctalDigit(next2)) {
              result.append((char) (8 * octaldigit(c) + octaldigit(next1)));
              cur += 1;
            } else {
              result.append((char)
                  (8 * 8 * octaldigit(c) + 8 * octaldigit(next1) + octaldigit(next2)));
              cur += 2;
            }
          }

          break;
        case 'x':
          result.append((char) (
              hexdigit(value.charAt(cur + 1)) * 0x10
              + hexdigit(value.charAt(cur + 2))));
          cur += 2;
          break;
        case 'u':
          int escapeEnd;
          String hexDigits;
          if (value.charAt(cur + 1) != '{') {
            // Simple escape with exactly four hex digits: \\uXXXX
            escapeEnd = cur + 5;
            hexDigits = value.substring(cur + 1, escapeEnd);
          } else {
            // Escape with braces can have any number of hex digits: \\u{XXXXXXX}
            escapeEnd = cur + 2;
            while (Character.digit(value.charAt(escapeEnd), 0x10) >= 0) {
              escapeEnd++;
            }
            hexDigits = value.substring(cur + 2, escapeEnd);
            escapeEnd++;
          }
          result.append(Character.toChars(Integer.parseInt(hexDigits, 0x10)));
          cur = escapeEnd - 1;
          break;
        default:
          // TODO(tbreisacher): Add a warning because the user probably
          // intended to type an escape sequence.
          result.append(c);
          break;
      }
      start = cur + 1;
      cur = value.indexOf('\\', start);
    }
    // skip the trailing quote.
    result.append(value, start, templateLiteral ? value.length() : value.length() - 1);

    return result.toString();
  }

  boolean isEs6Mode() {
    return config.languageMode == LanguageMode.ECMASCRIPT6
        || config.languageMode == LanguageMode.ECMASCRIPT6_STRICT
        || config.languageMode == LanguageMode.ECMASCRIPT6_TYPED;
  }

  boolean isEs5OrBetterMode() {
    return config.languageMode != LanguageMode.ECMASCRIPT3;
  }

  private boolean inStrictContext() {
    // TODO(johnlenz): in ECMASCRIPT5/6 is a "mixed" mode and we should track the context
    // that we are in, if we want to support it.
    return config.languageMode == LanguageMode.ECMASCRIPT5_STRICT
        || config.languageMode == LanguageMode.ECMASCRIPT6_STRICT
        || config.languageMode == LanguageMode.ECMASCRIPT6_TYPED;
  }

  double normalizeNumber(LiteralToken token) {
    String value = token.value;
    SourceRange location = token.location;
    int length = value.length();
    Preconditions.checkState(length > 0);
    Preconditions.checkState(value.charAt(0) != '-'
        && value.charAt(0) != '+');
    if (value.charAt(0) == '.') {
      return Double.valueOf('0' + value);
    } else if (value.charAt(0) == '0' && length > 1) {
      // TODO(johnlenz): accept octal numbers in es3 etc.
      switch (value.charAt(1)) {
        case '.':
        case 'e':
        case 'E':
          return Double.valueOf(value);
        case 'b':
        case 'B': {
          if (!isEs6Mode()) {
            errorReporter.warning(BINARY_NUMBER_LITERAL_WARNING,
                sourceName,
                lineno(token.location.start), charno(token.location.start));
          }
          double v = 0;
          int c = 1;
          while (++c < length) {
            v = (v * 2) + binarydigit(value.charAt(c));
          }
          return v;
        }
        case 'o':
        case 'O': {
          if (!isEs6Mode()) {
            errorReporter.warning(OCTAL_NUMBER_LITERAL_WARNING,
                sourceName,
                lineno(token.location.start), charno(token.location.start));
          }
          double v = 0;
          int c = 1;
          while (++c < length) {
            v = (v * 8) + octaldigit(value.charAt(c));
          }
          return v;
        }
        case 'x':
        case 'X': {
          double v = 0;
          int c = 1;
          while (++c < length) {
            v = (v * 0x10) + hexdigit(value.charAt(c));
          }
          return v;
        }
        case '0': case '1': case '2': case '3':
        case '4': case '5': case '6': case '7':
          errorReporter.warning(INVALID_ES5_STRICT_OCTAL, sourceName,
              lineno(location.start), charno(location.start));
          if (!inStrictContext()) {
            double v = 0;
            int c = 0;
            while (++c < length) {
              v = (v * 8) + octaldigit(value.charAt(c));
            }
            return v;
          } else {
            return Double.valueOf(value);
          }
        default:
          errorReporter.error(INVALID_NUMBER_LITERAL, sourceName,
              lineno(location.start), charno(location.start));
          return 0;
      }
    } else {
      return Double.valueOf(value);
    }
  }

  private static int binarydigit(char c) {
    if (c >= '0' && c <= '1') {
      return (c - '0');
    }
    throw new IllegalStateException("unexpected: " + c);
  }

  private static boolean isOctalDigit(char c) {
    return c >= '0' && c <= '7';
  }

  private static int octaldigit(char c) {
    if (isOctalDigit(c)) {
      return (c - '0');
    }
    throw new IllegalStateException("unexpected: " + c);
  }

  private static int hexdigit(char c) {
    switch (c) {
      case '0': return 0;
      case '1': return 1;
      case '2': return 2;
      case '3': return 3;
      case '4': return 4;
      case '5': return 5;
      case '6': return 6;
      case '7': return 7;
      case '8': return 8;
      case '9': return 9;
      case 'a': case 'A': return 10;
      case 'b': case 'B': return 11;
      case 'c': case 'C': return 12;
      case 'd': case 'D': return 13;
      case 'e': case 'E': return 14;
      case 'f': case 'F': return 15;
    }
    throw new IllegalStateException("unexpected: " + c);
  }

  private static int transformBooleanTokenType(TokenType token) {
    switch (token) {
      case TRUE:
        return Token.TRUE;
      case FALSE:
        return Token.FALSE;

      default:
        throw new IllegalStateException(String.valueOf(token));
    }
  }

  private static int transformPostfixTokenType(TokenType token) {
    switch (token) {
      case PLUS_PLUS:
        return Token.INC;
      case MINUS_MINUS:
        return Token.DEC;

      default:
        throw new IllegalStateException(String.valueOf(token));
    }
  }

  private static int transformUnaryTokenType(TokenType token) {
    switch (token) {
      case BANG:
        return Token.NOT;
      case TILDE:
        return Token.BITNOT;
      case PLUS:
        return Token.POS;
      case MINUS:
        return Token.NEG;
      case DELETE:
        return Token.DELPROP;
      case TYPEOF:
        return Token.TYPEOF;

      case PLUS_PLUS:
        return Token.INC;
      case MINUS_MINUS:
        return Token.DEC;

      case VOID:
        return Token.VOID;

      default:
        throw new IllegalStateException(String.valueOf(token));
    }
  }

  private static int transformBinaryTokenType(TokenType token) {
    switch (token) {
      case BAR:
        return Token.BITOR;
      case CARET:
        return Token.BITXOR;
      case AMPERSAND:
        return Token.BITAND;
      case EQUAL_EQUAL:
        return Token.EQ;
      case NOT_EQUAL:
        return Token.NE;
      case OPEN_ANGLE:
        return Token.LT;
      case LESS_EQUAL:
        return Token.LE;
      case CLOSE_ANGLE:
        return Token.GT;
      case GREATER_EQUAL:
        return Token.GE;
      case LEFT_SHIFT:
        return Token.LSH;
      case RIGHT_SHIFT:
        return Token.RSH;
      case UNSIGNED_RIGHT_SHIFT:
        return Token.URSH;
      case PLUS:
        return Token.ADD;
      case MINUS:
        return Token.SUB;
      case STAR:
        return Token.MUL;
      case SLASH:
        return Token.DIV;
      case PERCENT:
        return Token.MOD;

      case EQUAL_EQUAL_EQUAL:
        return Token.SHEQ;
      case NOT_EQUAL_EQUAL:
        return Token.SHNE;

      case IN:
        return Token.IN;
      case INSTANCEOF:
        return Token.INSTANCEOF;
      case COMMA:
        return Token.COMMA;

      case EQUAL:
        return Token.ASSIGN;
      case BAR_EQUAL:
        return Token.ASSIGN_BITOR;
      case CARET_EQUAL:
        return Token.ASSIGN_BITXOR;
      case AMPERSAND_EQUAL:
        return Token.ASSIGN_BITAND;
      case LEFT_SHIFT_EQUAL:
        return Token.ASSIGN_LSH;
      case RIGHT_SHIFT_EQUAL:
        return Token.ASSIGN_RSH;
      case UNSIGNED_RIGHT_SHIFT_EQUAL:
        return Token.ASSIGN_URSH;
      case PLUS_EQUAL:
        return Token.ASSIGN_ADD;
      case MINUS_EQUAL:
        return Token.ASSIGN_SUB;
      case STAR_EQUAL:
        return Token.ASSIGN_MUL;
      case SLASH_EQUAL:
        return Token.ASSIGN_DIV;
      case PERCENT_EQUAL:
        return Token.ASSIGN_MOD;

      case OR:
        return Token.OR;
      case AND:
        return Token.AND;

      default:
        throw new IllegalStateException(String.valueOf(token));
    }
  }

  // Simple helper to create nodes and set the initial node properties.
  private Node newNode(int type) {
    return new Node(type).clonePropsFrom(templateNode);
  }

  private Node newNode(int type, Node child1) {
    return new Node(type, child1).clonePropsFrom(templateNode);
  }

  private Node newNode(int type, Node child1, Node child2) {
    return new Node(type, child1, child2).clonePropsFrom(templateNode);
  }

  private Node newNode(int type, Node child1, Node child2, Node child3) {
    return new Node(type, child1, child2, child3).clonePropsFrom(templateNode);
  }

  private Node newStringNode(String value) {
    return IR.string(value).clonePropsFrom(templateNode);
  }

  private Node newStringNode(int type, String value) {
    return Node.newString(type, value).clonePropsFrom(templateNode);
  }

  private Node newNumberNode(Double value) {
    return IR.number(value).clonePropsFrom(templateNode);
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
 * Produces ASTs which represent JavaScript type declarations, both those
 * created from closure-style type declarations in a JSDoc node (via a
 * conversion from the rhino AST produced in
 * {@link IRFactory}) as well as those created from TypeScript-style inline type
 * declarations.
 *
 * <p>This is an alternative to the AST found in the root property of
 * JSTypeExpression, which is a crufty AST that reuses language tokens.
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
        LinkedHashMap<String, TypeDeclarationNode> parameters = new LinkedHashMap<>();
        String restName = null;
        TypeDeclarationNode restType = null;
        for (Node child2 : n.children()) {
          if (child2.isParamList()) {
            int paramIdx = 1;
            for (Node param : child2.children()) {
              String paramName = "p" + paramIdx++;
              if (param.getType() == Token.ELLIPSIS) {
                restName = paramName;
                if (param.getFirstChild() != null) {
                  restType = convertTypeNodeAST(param.getFirstChild());
                }
              } else {
                parameters.put(paramName, convertTypeNodeAST(param));
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
        return functionType(returnType, parameters, restName, restType);
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


File: src/com/google/javascript/jscomp/parsing/parser/Parser.java
/*
 * Copyright 2011 The Closure Compiler Authors.
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

package com.google.javascript.jscomp.parsing.parser;

import com.google.common.base.Predicate;
import com.google.common.base.Predicates;
import com.google.common.collect.ImmutableList;
import com.google.javascript.jscomp.parsing.parser.trees.ArgumentListTree;
import com.google.javascript.jscomp.parsing.parser.trees.ArrayLiteralExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ArrayPatternTree;
import com.google.javascript.jscomp.parsing.parser.trees.ArrayTypeTree;
import com.google.javascript.jscomp.parsing.parser.trees.AssignmentRestElementTree;
import com.google.javascript.jscomp.parsing.parser.trees.BinaryOperatorTree;
import com.google.javascript.jscomp.parsing.parser.trees.BlockTree;
import com.google.javascript.jscomp.parsing.parser.trees.BreakStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.CallExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.CaseClauseTree;
import com.google.javascript.jscomp.parsing.parser.trees.CatchTree;
import com.google.javascript.jscomp.parsing.parser.trees.ClassDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.CommaExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.Comment;
import com.google.javascript.jscomp.parsing.parser.trees.ComprehensionForTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComprehensionIfTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComprehensionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertyDefinitionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertyGetterTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertyMemberVariableTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertyMethodTree;
import com.google.javascript.jscomp.parsing.parser.trees.ComputedPropertySetterTree;
import com.google.javascript.jscomp.parsing.parser.trees.ConditionalExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ContinueStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.DebuggerStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.DefaultClauseTree;
import com.google.javascript.jscomp.parsing.parser.trees.DefaultParameterTree;
import com.google.javascript.jscomp.parsing.parser.trees.DoWhileStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.EmptyStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.EnumDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.ExportDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.ExportSpecifierTree;
import com.google.javascript.jscomp.parsing.parser.trees.ExpressionStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.FinallyTree;
import com.google.javascript.jscomp.parsing.parser.trees.ForInStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.ForOfStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.ForStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.FormalParameterListTree;
import com.google.javascript.jscomp.parsing.parser.trees.FunctionDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.FunctionTypeTree;
import com.google.javascript.jscomp.parsing.parser.trees.GetAccessorTree;
import com.google.javascript.jscomp.parsing.parser.trees.IdentifierExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.IfStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.ImportDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.ImportSpecifierTree;
import com.google.javascript.jscomp.parsing.parser.trees.InterfaceDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.LabelledStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.LiteralExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.MemberExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.MemberLookupExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.MemberVariableTree;
import com.google.javascript.jscomp.parsing.parser.trees.MissingPrimaryExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.NewExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.NullTree;
import com.google.javascript.jscomp.parsing.parser.trees.ObjectLiteralExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ObjectPatternTree;
import com.google.javascript.jscomp.parsing.parser.trees.ParameterizedTypeTree;
import com.google.javascript.jscomp.parsing.parser.trees.ParenExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ParseTree;
import com.google.javascript.jscomp.parsing.parser.trees.ParseTreeType;
import com.google.javascript.jscomp.parsing.parser.trees.PostfixExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ProgramTree;
import com.google.javascript.jscomp.parsing.parser.trees.PropertyNameAssignmentTree;
import com.google.javascript.jscomp.parsing.parser.trees.RestParameterTree;
import com.google.javascript.jscomp.parsing.parser.trees.ReturnStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.SetAccessorTree;
import com.google.javascript.jscomp.parsing.parser.trees.SpreadExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.SuperExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.SwitchStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.TemplateLiteralExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.TemplateLiteralPortionTree;
import com.google.javascript.jscomp.parsing.parser.trees.TemplateSubstitutionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ThisExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.ThrowStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.TryStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.TypeNameTree;
import com.google.javascript.jscomp.parsing.parser.trees.TypedParameterTree;
import com.google.javascript.jscomp.parsing.parser.trees.UnaryExpressionTree;
import com.google.javascript.jscomp.parsing.parser.trees.UnionTypeTree;
import com.google.javascript.jscomp.parsing.parser.trees.VariableDeclarationListTree;
import com.google.javascript.jscomp.parsing.parser.trees.VariableDeclarationTree;
import com.google.javascript.jscomp.parsing.parser.trees.VariableStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.WhileStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.WithStatementTree;
import com.google.javascript.jscomp.parsing.parser.trees.YieldExpressionTree;
import com.google.javascript.jscomp.parsing.parser.util.ErrorReporter;
import com.google.javascript.jscomp.parsing.parser.util.LookaheadErrorReporter;
import com.google.javascript.jscomp.parsing.parser.util.LookaheadErrorReporter.ParseException;
import com.google.javascript.jscomp.parsing.parser.util.SourcePosition;
import com.google.javascript.jscomp.parsing.parser.util.SourceRange;
import com.google.javascript.jscomp.parsing.parser.util.Timer;

import java.util.ArrayDeque;
import java.util.EnumSet;
import java.util.List;

/**
 * Parses a javascript file.
 *
 * <p>The various parseX() methods never return null - even when parse errors are encountered.
 * Typically parseX() will return a XTree ParseTree. Each ParseTree that is created includes its
 * source location. The typical pattern for a parseX() method is:
 *
 * <pre>
 * XTree parseX() {
 *   SourcePosition start = getTreeStartLocation();
 *   parse X grammar element and its children
 *   return new XTree(getTreeLocation(start), children);
 * }
 * </pre>
 *
 * <p>parseX() methods must consume at least 1 token - even in error cases. This prevents infinite
 * loops in the parser.
 *
 * <p>Many parseX() methods are matched by a 'boolean peekX()' method which will return true if
 * the beginning of an X appears at the current location. There are also peek() methods which
 * examine the next token. peek() methods must not consume any tokens.
 *
 * <p>The eat() method consumes a token and reports an error if the consumed token is not of the
 * expected type. The eatOpt() methods consume the next token iff the next token is of the expected
 * type and return the consumed token or null if no token was consumed.
 *
 * <p>When parse errors are encountered, an error should be reported and the parse should return a
 * best guess at the current parse tree.
 *
 * <p>When parsing lists, the preferred pattern is:
 * <pre>
 *   eat(LIST_START);
 *   ImmutableList.Builder&lt;ParseTree> elements = ImmutableList.builder();
 *   while (peekListElement()) {
 *     elements.add(parseListElement());
 *   }
 *   eat(LIST_END);
 * </pre>
 */
public class Parser {
  private final Scanner scanner;
  private final ErrorReporter errorReporter;
  private Token lastToken;
  private final Config config;
  private final CommentRecorder commentRecorder = new CommentRecorder();
  private final ArrayDeque<Boolean> inGeneratorContext = new ArrayDeque<>();

  public Parser(
      Config config, ErrorReporter errorReporter,
      SourceFile source, int offset, boolean initialGeneratorContext) {
    this.config = config;
    this.errorReporter = errorReporter;
    this.scanner = new Scanner(errorReporter, commentRecorder, source, offset);
    this.inGeneratorContext.add(initialGeneratorContext);
  }

  public Parser(
      Config config, ErrorReporter errorReporter,
      SourceFile source, int offset) {
    this(config, errorReporter, source, offset, false);
  }

  public Parser(Config config, ErrorReporter errorReporter, SourceFile source) {
    this(config, errorReporter, source, 0);
  }

  public static class Config {
    public static enum Mode {
      ES3,
      ES5,
      ES5_STRICT,
      ES6,
      ES6_STRICT,
      ES6_TYPED,
    }

    public final boolean atLeast6;
    public final boolean atLeast5;
    public final boolean isStrictMode;
    public final boolean warnTrailingCommas;
    public final boolean warnLineContinuations;
    public final boolean warnES6NumberLiteral;

    public Config(Mode mode) {
      atLeast6 = mode == Mode.ES6 || mode == Mode.ES6_STRICT
          || mode == Mode.ES6_TYPED;
      atLeast5 = atLeast6 || mode == Mode.ES5 || mode == Mode.ES5_STRICT;
      this.isStrictMode = mode == Mode.ES5_STRICT || mode == Mode.ES6_STRICT
          || mode == Mode.ES6_TYPED;

      // Generally, we allow everything that is valid in any mode
      // we only warn about things that are not represented in the AST.
      this.warnTrailingCommas = !atLeast5;
      this.warnLineContinuations = !atLeast6;
      this.warnES6NumberLiteral = !atLeast6;
    }
  }

  private static class CommentRecorder implements Scanner.CommentRecorder{
    private ImmutableList.Builder<Comment> comments =
        ImmutableList.builder();
    @Override
    public void recordComment(
        Comment.Type type, SourceRange range, String value) {
      comments.add(new Comment(value, range, type));
    }

    private ImmutableList<Comment> getComments() {
      return comments.build();
    }
  }

  public List<Comment> getComments() {
    return commentRecorder.getComments();
  }

  // 14 Program
  public ProgramTree parseProgram() {
    Timer t = new Timer("Parse Program");
    try {
      SourcePosition start = getTreeStartLocation();
      ImmutableList<ParseTree> sourceElements = parseGlobalSourceElements();
      eat(TokenType.END_OF_FILE);
      t.end();
      return new ProgramTree(
          getTreeLocation(start), sourceElements, commentRecorder.getComments());
    } catch (StackOverflowError e) {
      reportError("Too deep recursion while parsing");
      return null;
    }
  }

  private ImmutableList<ParseTree> parseGlobalSourceElements() {
    ImmutableList.Builder<ParseTree> result = ImmutableList.builder();

    while (!peek(TokenType.END_OF_FILE)) {
      result.add(parseScriptElement());
    }

    return result.build();
  }

  // ImportDeclaration
  // ExportDeclaration
  // SourceElement
  private ParseTree parseScriptElement() {
    if (peekImportDeclaration()) {
      return parseImportDeclaration();
    }

    if (peekExportDeclaration()) {
      return parseExportDeclaration();
    }

    return parseSourceElement();
  }

  // https://people.mozilla.org/~jorendorff/es6-draft.html#sec-imports
  private boolean peekImportDeclaration() {
    return peek(TokenType.IMPORT);
  }

  private ParseTree parseImportDeclaration() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.IMPORT);

    // import ModuleSpecifier ;
    if (peek(TokenType.STRING)) {
      LiteralToken moduleSpecifier = eat(TokenType.STRING).asLiteral();
      eatPossibleImplicitSemiColon();

      return new ImportDeclarationTree(
          getTreeLocation(start), null, null, null, moduleSpecifier);
    }

    // import ImportedDefaultBinding from ModuleSpecifier
    // import NameSpaceImport from ModuleSpecifier
    // import NamedImports from ModuleSpecifier ;
    // import ImportedDefaultBinding , NameSpaceImport from ModuleSpecifier ;
    // import ImportedDefaultBinding , NamedImports from ModuleSpecifier ;
    IdentifierToken defaultBindingIdentifier = null;
    IdentifierToken nameSpaceImportIdentifier = null;
    ImmutableList<ParseTree> identifierSet = null;

    boolean parseExplicitNames = true;
    if (peekId()) {
      defaultBindingIdentifier = eatId();
      if (peek(TokenType.COMMA)) {
        eat(TokenType.COMMA);
      } else {
        parseExplicitNames = false;
      }
    }

    if (parseExplicitNames) {
      if (peek(TokenType.STAR)) {
        eat(TokenType.STAR);
        eatPredefinedString(PredefinedName.AS);
        nameSpaceImportIdentifier = eatId();
      } else {
        identifierSet = parseImportSpecifierSet();
      }
    }

    eatPredefinedString(PredefinedName.FROM);
    Token moduleStr = eat(TokenType.STRING);
    LiteralToken moduleSpecifier = (moduleStr == null)
        ? null : moduleStr.asLiteral();
    eatPossibleImplicitSemiColon();

    return new ImportDeclarationTree(
        getTreeLocation(start),
        defaultBindingIdentifier, identifierSet, nameSpaceImportIdentifier, moduleSpecifier);
  }

  //  ImportSpecifierSet ::= '{' (ImportSpecifier (',' ImportSpecifier)* (,)? )?  '}'
  private ImmutableList<ParseTree> parseImportSpecifierSet() {
    ImmutableList.Builder<ParseTree> elements;
    elements = ImmutableList.builder();
    eat(TokenType.OPEN_CURLY);
    while (peekId()) {
      elements.add(parseImportSpecifier());
      if (!peek(TokenType.CLOSE_CURLY)) {
        eat(TokenType.COMMA);
      }
    }
    eat(TokenType.CLOSE_CURLY);
    return elements.build();
  }

  //  ImportSpecifier ::= Identifier ('as' Identifier)?
  private ParseTree parseImportSpecifier() {
    SourcePosition start = getTreeStartLocation();
    IdentifierToken importedName = eatId();
    IdentifierToken destinationName = null;
    if (peekPredefinedString(PredefinedName.AS)){
      eatPredefinedString(PredefinedName.AS);
      destinationName = eatId();
    }
    return new ImportSpecifierTree(
        getTreeLocation(start), importedName, destinationName);
  }

  // export  VariableStatement
  // export  FunctionDeclaration
  // export  ConstStatement
  // export  ClassDeclaration
  // export  default expression
  // etc
  private boolean peekExportDeclaration() {
    return peek(TokenType.EXPORT);
  }

  /*
  ExportDeclaration :
    export * FromClause ;
    export ExportClause [NoReference] FromClause ;
    export ExportClause ;
    export VariableStatement
    export Declaration[Default]
    export default AssignmentExpression ;
  ExportClause [NoReference] :
    { }
    { ExportsList [?NoReference] }
    { ExportsList [?NoReference] , }
  ExportsList [NoReference] :
    ExportSpecifier [?NoReference]
    ExportsList [?NoReference] , ExportSpecifier [?NoReference]
  ExportSpecifier [NoReference] :
    [~NoReference] IdentifierReference
    [~NoReference] IdentifierReference as IdentifierName
    [+NoReference] IdentifierName
    [+NoReference] IdentifierName as IdentifierName
   */
  private ParseTree parseExportDeclaration() {
    SourcePosition start = getTreeStartLocation();
    boolean isDefault = false;
    boolean isExportAll = false;
    boolean isExportSpecifier = false;
    eat(TokenType.EXPORT);
    ParseTree export = null;
    ImmutableList<ParseTree> exportSpecifierList = null;
    switch (peekType()) {
    case STAR:
      isExportAll = true;
      nextToken();
      break;
    case FUNCTION:
      export = parseFunctionDeclaration();
      break;
    case CLASS:
      export = parseClassDeclaration();
      break;
    case DEFAULT:
      isDefault = true;
      nextToken();
      export = parseExpression();
      break;
    case OPEN_CURLY:
      isExportSpecifier = true;
      exportSpecifierList = parseExportSpecifierSet();
      break;
    default:
      // unreachable, parse as a var decl to get a parse error.
    case VAR:
    case LET:
    case CONST:
      export = parseVariableDeclarationList();
      break;
    }

    LiteralToken moduleSpecifier = null;
    if (isExportAll ||
        (isExportSpecifier && peekPredefinedString(PredefinedName.FROM))) {
      eatPredefinedString(PredefinedName.FROM);
      moduleSpecifier = eat(TokenType.STRING).asLiteral();
    }

    eatPossibleImplicitSemiColon();

    return new ExportDeclarationTree(
        getTreeLocation(start), isDefault, isExportAll,
        export, exportSpecifierList, moduleSpecifier);
  }

  //  ExportSpecifierSet ::= '{' (ExportSpecifier (',' ExportSpecifier)* (,)? )?  '}'
  private ImmutableList<ParseTree> parseExportSpecifierSet() {
    ImmutableList.Builder<ParseTree> elements;
    elements = ImmutableList.builder();
    eat(TokenType.OPEN_CURLY);
    while (peekId()) {
      elements.add(parseExportSpecifier());
      if (!peek(TokenType.CLOSE_CURLY)) {
        eat(TokenType.COMMA);
      }
    }
    eat(TokenType.CLOSE_CURLY);
    return elements.build();
  }

  //  ExportSpecifier ::= Identifier ('as' Identifier)?
  private ParseTree parseExportSpecifier() {
    SourcePosition start = getTreeStartLocation();
    IdentifierToken importedName = eatId();
    IdentifierToken destinationName = null;
    if (peekPredefinedString(PredefinedName.AS)){
      eatPredefinedString(PredefinedName.AS);
      destinationName = eatId();
    }
    return new ExportSpecifierTree(
        getTreeLocation(start), importedName, destinationName);
  }

  private boolean peekClassDeclaration() {
    return peek(TokenType.CLASS);
  }

  private boolean peekInterfaceDeclaration() {
    return peek(TokenType.INTERFACE);
  }

  private boolean peekEnumDeclaration() {
    return peek(TokenType.ENUM);
  }

  private ParseTree parseClassDeclaration() {
    return parseClass(false);
  }

  private ParseTree parseClassExpression() {
    return parseClass(true);
  }

  private ParseTree parseInterfaceDeclaration() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.INTERFACE);
    IdentifierToken name = eatId();
    ImmutableList.Builder<ParseTree> superTypes = ImmutableList.builder();
    if (peek(TokenType.EXTENDS)) {
      eat(TokenType.EXTENDS);
      ParseTree type = parseType();
      superTypes.add(type);

      while (peek(TokenType.COMMA)) {
        eat(TokenType.COMMA);
        type = parseType();
        if (type != null) {
          superTypes.add(type);
        }
      }
    }
    eat(TokenType.OPEN_CURLY);
    ImmutableList<ParseTree> elements = parseClassElements();
    eat(TokenType.CLOSE_CURLY);
    return new InterfaceDeclarationTree(getTreeLocation(start), name, superTypes.build(), elements);
  }

  private ParseTree parseEnumDeclaration() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.ENUM);
    IdentifierToken name = eatId();
    eat(TokenType.OPEN_CURLY);
    ImmutableList<ParseTree> members = parseEnumMembers();
    eat(TokenType.CLOSE_CURLY);
    return new EnumDeclarationTree(getTreeLocation(start), name, members);
  }

  private ImmutableList<ParseTree> parseEnumMembers() {
    SourceRange range = getTreeLocation(getTreeStartLocation());
    IdentifierToken propertyName;
    ParseTree member = null;
    ImmutableList.Builder<ParseTree> result = ImmutableList.builder();

    while (peekId()) {
      propertyName = parseIdentifierExpression().identifierToken;
      member = new PropertyNameAssignmentTree(range, propertyName, null);
      result.add(member);
      if (!peek(TokenType.CLOSE_CURLY)) {
        eat(TokenType.COMMA);
      }
    }
    return result.build();
  }

  private ParseTree parseClass(boolean isExpression) {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.CLASS);
    IdentifierToken name = null;
    if (!isExpression || peekId()) {
      name = eatId();
    }
    ParseTree superClass = null;
    if (peek(TokenType.EXTENDS)) {
      eat(TokenType.EXTENDS);
      superClass = parseExpression();
    }
    eat(TokenType.OPEN_CURLY);
    ImmutableList<ParseTree> elements = parseClassElements();
    eat(TokenType.CLOSE_CURLY);
    return new ClassDeclarationTree(getTreeLocation(start), name, superClass, elements);
  }

  private ImmutableList<ParseTree> parseClassElements() {
    ImmutableList.Builder<ParseTree> result = ImmutableList.builder();

    while (peekClassElement()) {
      result.add(parseClassElement());
    }

    return result.build();
  }

  private boolean peekClassElement() {
    Token token = peekToken();
    switch (token.type) {
      case IDENTIFIER:
      case STAR:
      case STATIC:
      case OPEN_SQUARE:
      case SEMI_COLON:
        return true;
      default:
        return Keywords.isKeyword(token.type);
    }
  }

  private ParseTree parseClassElement() {
    if (peek(TokenType.SEMI_COLON)) {
      return parseEmptyStatement();
    }
    if (peekGetAccessor(true)) {
      return parseGetAccessor();
    }
    if (peekSetAccessor(true)) {
      return parseSetAccessor();
    }
    return parseClassMemberDeclaration(true);
  }

  private ParseTree parseClassMemberDeclaration(boolean allowStatic) {
    SourcePosition start = getTreeStartLocation();
    boolean isStatic = false;
    if (allowStatic && peek(TokenType.STATIC) && peekType(1) != TokenType.OPEN_PAREN) {
      eat(TokenType.STATIC);
      isStatic = true;
    }
    boolean isGenerator = eatOpt(TokenType.STAR) != null;

    ParseTree nameExpr;
    IdentifierToken name;
    TokenType type = peekType();
    if (type == TokenType.IDENTIFIER || Keywords.isKeyword(type)) {
      nameExpr = null;
      name = eatIdOrKeywordAsId();
    } else {
      nameExpr = parseComputedPropertyName();
      name = null;
    }

    if (peek(TokenType.OPEN_PAREN)) {
      // Member function.
      FunctionDeclarationTree.Kind kind =
          nameExpr == null ? FunctionDeclarationTree.Kind.MEMBER
              : FunctionDeclarationTree.Kind.EXPRESSION;
      ParseTree function = parseFunctionTail(start, name, isStatic, isGenerator, kind);
      if (kind == FunctionDeclarationTree.Kind.MEMBER) {
        return function;
      } else {
        return new ComputedPropertyMethodTree(getTreeLocation(start), nameExpr, function);
      }
    } else {
      // Member variable.
      if (isGenerator) {
        reportError("Member variable cannot be prefixed by '*' (generator function)");
      }
      ParseTree declaredType = null;
      if (peek(TokenType.COLON)) {
        declaredType = parseTypeAnnotation();
      }
      if (peek(TokenType.EQUAL)) {
        reportError("Member variable initializers ('=') are not supported");
      }
      eat(TokenType.SEMI_COLON);
      if (nameExpr == null) {
        return new MemberVariableTree(getTreeLocation(start), name, isStatic, declaredType);
      } else {
        return new ComputedPropertyMemberVariableTree(getTreeLocation(start), nameExpr, isStatic,
            declaredType);
      }
    }
  }

  private FunctionDeclarationTree parseFunctionTail(
      SourcePosition start, IdentifierToken name,
      boolean isStatic, boolean isGenerator,
      FunctionDeclarationTree.Kind kind) {

    inGeneratorContext.addLast(isGenerator);

    FormalParameterListTree formalParameterList = parseFormalParameterList();

    ParseTree returnType = null;
    if (peek(TokenType.COLON)) {
      returnType = parseTypeAnnotation();
    }

    BlockTree functionBody = parseFunctionBody();
    FunctionDeclarationTree declaration =  new FunctionDeclarationTree(
        getTreeLocation(start), name, isStatic, isGenerator,
        kind, formalParameterList, returnType, functionBody);

    inGeneratorContext.removeLast();

    return declaration;
  }


  private ParseTree parseSourceElement() {
    if (peekFunction()) {
      return parseFunctionDeclaration();
    }

    if (peekClassDeclaration()) {
      return parseClassDeclaration();
    }

    if (peekInterfaceDeclaration()) {
      return parseInterfaceDeclaration();
    }

    if (peekEnumDeclaration()) {
      return parseEnumDeclaration();
    }

    // Harmony let block scoped bindings. let can only appear in
    // a block, not as a standalone statement: if() let x ... illegal
    if (peek(TokenType.LET)) {
      return parseVariableStatement();
    }
    // const and var are handled inside parseStatement

    return parseStatementStandard();
  }

  private boolean peekSourceElement() {
    return peekFunction() || peekStatementStandard() || peekDeclaration();
  }

  private boolean peekFunction() {
    return peekFunction(0);
  }

  private boolean peekDeclaration() {
    return peek(TokenType.LET)
        || peekClassDeclaration()
        || peekInterfaceDeclaration()
        || peekEnumDeclaration();
  }

  private boolean peekFunction(int index) {
    // TODO(johnlenz): short function syntax
    return peek(index, TokenType.FUNCTION);
  }

  private ParseTree parseArrowFunction(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();

    inGeneratorContext.addLast(false);

    FormalParameterListTree formalParameterList;
    if (peekId()) {
      ParseTree param = parseIdentifierExpression();
      formalParameterList = new FormalParameterListTree(getTreeLocation(start),
          ImmutableList.of(param));
    } else {
      formalParameterList = parseFormalParameterList();
    }

    ParseTree returnType = null;
    if (peek(TokenType.COLON)) {
      returnType = parseTypeAnnotation();
    }

    if (peekImplicitSemiColon()) {
      reportError("No newline allowed before '=>'");
    }
    eat(TokenType.ARROW);
    ParseTree functionBody;
    if (peek(TokenType.OPEN_CURLY)) {
      functionBody = parseFunctionBody();
    } else {
      functionBody = parseAssignment(expressionIn);
    }

    FunctionDeclarationTree declaration =  new FunctionDeclarationTree(
        getTreeLocation(start), null, false, false,
        FunctionDeclarationTree.Kind.ARROW,
        formalParameterList, returnType, functionBody);

    inGeneratorContext.removeLast();

    return declaration;
  }

  private boolean peekArrowFunction() {
    if (peekId() && peekType(1) == TokenType.ARROW) {
      return true;
    } else {
      return peekArrowFunctionWithParenthesizedParameterList();
    }
  }

  private boolean peekArrowFunctionWithParenthesizedParameterList() {
    if (peek(TokenType.OPEN_PAREN)) {
      // TODO(johnlenz): determine if we can parse this without the
      // overhead of forking the parser.
      Parser p = createLookaheadParser();
      try {
        p.parseFormalParameterList();
        if (p.peek(TokenType.COLON)) {
          p.parseTypeAnnotation();
        }
        return p.peek(TokenType.ARROW);
      } catch (ParseException e) {
        return false;
      }
    }
    return false;
  }

  // 13 Function Definition
  private ParseTree parseFunctionDeclaration() {
    SourcePosition start = getTreeStartLocation();
    eat(Keywords.FUNCTION.type);
    boolean isGenerator = eatOpt(TokenType.STAR) != null;
    IdentifierToken name = eatId();

    return parseFunctionTail(
        start, name, false, isGenerator,
        FunctionDeclarationTree.Kind.DECLARATION);
  }

  private ParseTree parseFunctionExpression() {
    SourcePosition start = getTreeStartLocation();
    eat(Keywords.FUNCTION.type);
    boolean isGenerator = eatOpt(TokenType.STAR) != null;
    IdentifierToken name = eatIdOpt();

    return parseFunctionTail(
        start, name, false, isGenerator,
        FunctionDeclarationTree.Kind.EXPRESSION);
  }

  private FormalParameterListTree parseFormalParameterList() {
    SourcePosition listStart = getTreeStartLocation();
    eat(TokenType.OPEN_PAREN);

    // FormalParameterList :
    //   ... Identifier
    //   FormalParameterListNoRest
    //   FormalParameterListNoRest , ... Identifier
    //
    // FormalParameterListNoRest :
    //   Identifier
    //   Identifier = AssignmentExprssion
    //   FormalParameterListNoRest , Identifier
    ImmutableList.Builder<ParseTree> result = ImmutableList.builder();

    while (peek(TokenType.SPREAD) || peekId()
        || peek(TokenType.OPEN_SQUARE) || peek(TokenType.OPEN_CURLY)) {

      SourcePosition start = getTreeStartLocation();

      if (peek(TokenType.SPREAD)) {
        eat(TokenType.SPREAD);
        result.add(new RestParameterTree(getTreeLocation(start), eatId()));

        // Rest parameters must be the last parameter; so we must be done.
        break;
      }

      ParseTree parameter;
      ParseTree typeAnnotation = null;
      SourceRange typeLocation = null;
      if (peekId()) {
        parameter = parseIdentifierExpression();
        if (peek(TokenType.COLON)) {
          SourcePosition typeStart = getTreeStartLocation();
          typeAnnotation = parseTypeAnnotation();
          typeLocation = getTreeLocation(typeStart);
        }
      } else if (peek(TokenType.OPEN_SQUARE)) {
        parameter = parseArrayPattern(PatternKind.INITIALIZER);
      } else {
        parameter = parseObjectPattern(PatternKind.INITIALIZER);
      }

      if (peek(TokenType.EQUAL)) {
        eat(TokenType.EQUAL);
        ParseTree defaultValue = parseAssignmentExpression();
        parameter = new DefaultParameterTree(getTreeLocation(start), parameter, defaultValue);
      }

      if (typeAnnotation != null) {
        // Must be a direct child of the parameter list.
        parameter = new TypedParameterTree(typeLocation, parameter, typeAnnotation);
      }

      result.add(parameter);

      if (!peek(TokenType.CLOSE_PAREN)) {
        Token comma = eat(TokenType.COMMA);
        if (peek(TokenType.CLOSE_PAREN)) {
          reportError(comma, "Invalid trailing comma in formal parameter list");
        }
      }
    }

    eat(TokenType.CLOSE_PAREN);

    return new FormalParameterListTree(
        getTreeLocation(listStart), result.build());
  }

  private ParseTree parseTypeAnnotation() {
    eat(TokenType.COLON);
    return parseType();
  }

  private ParseTree parseType() {
    SourcePosition start = getTreeStartLocation();
    if (!peekId() && !peek(TokenType.VOID) && !peek(TokenType.OPEN_PAREN)) {
      reportError("Unexpected token '%s' in type expression", peekType());
      return new TypeNameTree(getTreeLocation(start), ImmutableList.of("error"));
    }

    ParseTree typeExpression = parseFunctionTypeExpression();
    if (!peek(TokenType.BAR)) {
      return typeExpression;
    }
    ImmutableList.Builder<ParseTree> unionType = ImmutableList.builder();
    unionType.add(typeExpression);
    do {
      eat(TokenType.BAR);
      unionType.add(parseArrayTypeExpression());
    } while (peek(TokenType.BAR));
    return new UnionTypeTree(getTreeLocation(start), unionType.build());
  }

  private ParseTree parseFunctionTypeExpression() {
    SourcePosition start = getTreeStartLocation();
    ParseTree typeExpression = null;
    if (peekArrowFunctionWithParenthesizedParameterList()) {
      FormalParameterListTree formalParameterList;
      formalParameterList = parseFormalParameterList();
      eat(TokenType.ARROW);
      ParseTree returnType = parseType();
      typeExpression = new FunctionTypeTree(
          getTreeLocation(start), formalParameterList, returnType);
    } else {
      typeExpression = parseArrayTypeExpression();
    }
    return typeExpression;
  }

  private ParseTree parseArrayTypeExpression() {
    SourcePosition start = getTreeStartLocation();
    ParseTree typeExpression = parseParenTypeExpression();
    if (!peekImplicitSemiColon() && peek(TokenType.OPEN_SQUARE)) {
      eat(TokenType.OPEN_SQUARE);
      eat(TokenType.CLOSE_SQUARE);
      typeExpression =
          new ArrayTypeTree(getTreeLocation(start), typeExpression);
    }
    return typeExpression;
  }

  private ParseTree parseParenTypeExpression() {
    ParseTree typeExpression;
    if (peek(TokenType.OPEN_PAREN)) {
      eat(TokenType.OPEN_PAREN);
      typeExpression = parseType();
      eat(TokenType.CLOSE_PAREN);
    } else {
      typeExpression = parseTypeReference();
    }
    return typeExpression;
  }

  private ParseTree parseTypeReference() {
    SourcePosition start = getTreeStartLocation();

    TypeNameTree typeName = parseTypeName();
    if (!peek(TokenType.OPEN_ANGLE)) {
      return typeName;
    }

    return parseTypeArgumentList(start, typeName);
  }

  private ParseTree parseTypeArgumentList(SourcePosition start, TypeNameTree typeName) {
    // < TypeArgumentList >
    // TypeArgumentList , TypeArgument
    eat(TokenType.OPEN_ANGLE);
    ImmutableList.Builder<ParseTree> typeArguments = ImmutableList.builder();
    ParseTree type = parseType();
    typeArguments.add(type);

    while (peek(TokenType.COMMA)) {
      eat(TokenType.COMMA);
      type = parseType();
      if (type != null) {
        typeArguments.add(type);
      }
    }
    eat(TokenType.CLOSE_ANGLE);

    return new ParameterizedTypeTree(getTreeLocation(start), typeName, typeArguments.build());
  }

  private TypeNameTree parseTypeName() {
    SourcePosition start = getTreeStartLocation();
    IdentifierToken token = eatIdOrKeywordAsId();  // for 'void'.

    ImmutableList.Builder<String> identifiers = ImmutableList.builder();
    identifiers.add(token != null ? token.value : "");  // null if errors while parsing
    while (peek(TokenType.PERIOD)) {
      // ModuleName . Identifier
      eat(TokenType.PERIOD);
      token = eatId();
      if (token == null) {
        break;
      }
      identifiers.add(token.value);
    }
    return new TypeNameTree(getTreeLocation(start), identifiers.build());
  }

  private BlockTree parseFunctionBody() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.OPEN_CURLY);
    ImmutableList<ParseTree> result = parseSourceElementList();
    eat(TokenType.CLOSE_CURLY);
    return new BlockTree(getTreeLocation(start), result);
  }

  private ImmutableList<ParseTree> parseSourceElementList() {
    ImmutableList.Builder<ParseTree> result = ImmutableList.builder();

    while (peekSourceElement()) {
      result.add(parseSourceElement());
    }

    return result.build();
  }

  private SpreadExpressionTree parseSpreadExpression() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.SPREAD);
    ParseTree operand = parseAssignmentExpression();
    return new SpreadExpressionTree(getTreeLocation(start), operand);
  }

  // 12 Statements

  /**
   * In V8, all source elements may appear where statements occur in the grammar.
   */
  private ParseTree parseStatement() {
    return parseSourceElement();
  }

  /**
   * This function reflects the ECMA standard. Most places use peekStatement instead.
   */
  private ParseTree parseStatementStandard() {
    switch (peekType()) {
    case OPEN_CURLY:
      return parseBlock();
    case CONST:
    case VAR:
      return parseVariableStatement();
    case SEMI_COLON:
      return parseEmptyStatement();
    case IF:
      return parseIfStatement();
    case DO:
      return parseDoWhileStatement();
    case WHILE:
      return parseWhileStatement();
    case FOR:
      return parseForStatement();
    case CONTINUE:
      return parseContinueStatement();
    case BREAK:
      return parseBreakStatement();
    case RETURN:
      return parseReturnStatement();
    case WITH:
      return parseWithStatement();
    case SWITCH:
      return parseSwitchStatement();
    case THROW:
      return parseThrowStatement();
    case TRY:
      return parseTryStatement();
    case DEBUGGER:
      return parseDebuggerStatement();
    default:
      if (peekLabelledStatement()) {
        return parseLabelledStatement();
      }
      return parseExpressionStatement();
    }
  }

  /**
   * In V8 all source elements may appear where statements appear in the grammar.
   */
  private boolean peekStatement() {
    return peekSourceElement();
  }

  /**
   * This function reflects the ECMA standard. Most places use peekStatement instead.
   */
  private boolean peekStatementStandard() {
    switch (peekType()) {
    case OPEN_CURLY:
    case VAR:
    case CONST:
    case SEMI_COLON:
    case IF:
    case DO:
    case WHILE:
    case FOR:
    case CONTINUE:
    case BREAK:
    case RETURN:
    case WITH:
    case SWITCH:
    case THROW:
    case TRY:
    case DEBUGGER:
    case YIELD:
    case IDENTIFIER:
    case THIS:
    case CLASS:
    case SUPER:
    case NUMBER:
    case STRING:
    case NO_SUBSTITUTION_TEMPLATE:
    case TEMPLATE_HEAD:
    case NULL:
    case TRUE:
    case SLASH: // regular expression literal
    case SLASH_EQUAL: // regular expression literal
    case FALSE:
    case OPEN_SQUARE:
    case OPEN_PAREN:
    case NEW:
    case DELETE:
    case VOID:
    case TYPEOF:
    case PLUS_PLUS:
    case MINUS_MINUS:
    case PLUS:
    case MINUS:
    case TILDE:
    case BANG:
      return true;
    default:
      return false;
    }
  }

  // 12.1 Block
  private BlockTree parseBlock() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.OPEN_CURLY);
    // Spec says Statement list. However functions are also embedded in the wild.
    ImmutableList<ParseTree> result = parseSourceElementList();
    eat(TokenType.CLOSE_CURLY);
    return new BlockTree(getTreeLocation(start), result);
  }

  private ImmutableList<ParseTree> parseStatementList() {
    ImmutableList.Builder<ParseTree> result = ImmutableList.builder();
    while (peekStatement()) {
      result.add(parseStatement());
    }
    return result.build();
  }

  // 12.2 Variable Statement
  private VariableStatementTree parseVariableStatement() {
    SourcePosition start = getTreeStartLocation();
    VariableDeclarationListTree declarations = parseVariableDeclarationList();
    eatPossibleImplicitSemiColon();
    return new VariableStatementTree(getTreeLocation(start), declarations);
  }

  private VariableDeclarationListTree parseVariableDeclarationList() {
    return parseVariableDeclarationList(Expression.NORMAL);
  }

  private VariableDeclarationListTree parseVariableDeclarationListNoIn() {
    return parseVariableDeclarationList(Expression.NO_IN);
  }

  private VariableDeclarationListTree parseVariableDeclarationList(
      Expression expressionIn) {
    TokenType token = peekType();

    switch (token) {
    case CONST:
    case LET:
    case VAR:
      eat(token);
      break;
    default:
      reportError(peekToken(), "expected declaration");
      return null;
    }

    SourcePosition start = getTreeStartLocation();
    ImmutableList.Builder<VariableDeclarationTree> declarations =
        ImmutableList.builder();

    declarations.add(parseVariableDeclaration(token, expressionIn));
    while (peek(TokenType.COMMA)) {
      eat(TokenType.COMMA);
      declarations.add(parseVariableDeclaration(token, expressionIn));
    }
    return new VariableDeclarationListTree(
        getTreeLocation(start), token, declarations.build());
  }

  private VariableDeclarationTree parseVariableDeclaration(
      final TokenType binding, Expression expressionIn) {

    SourcePosition start = getTreeStartLocation();
    ParseTree lvalue;
    ParseTree typeAnnotation = null;
    if (peekPatternStart()) {
      lvalue = parsePattern(PatternKind.INITIALIZER);
    } else {
      lvalue = parseIdentifierExpression();
      if (peek(TokenType.COLON)) {
        typeAnnotation = parseTypeAnnotation();
      }
    }

    ParseTree initializer = null;
    if (peek(TokenType.EQUAL)) {
      initializer = parseInitializer(expressionIn);
    } else if (expressionIn != Expression.NO_IN) {
      // NOTE(blickly): this is a bit of a hack, declarations outside of for statements allow "in",
      // and by chance, also must have initializers for const/destructuring. Vanilla for loops
      // also require intializers, but are handled separately in checkVanillaForInitializers
      maybeReportNoInitializer(binding, lvalue);
    }
    return new VariableDeclarationTree(getTreeLocation(start), lvalue, typeAnnotation, initializer);
  }

  private ParseTree parseInitializer(Expression expressionIn) {
    eat(TokenType.EQUAL);
    return parseAssignment(expressionIn);
  }

  // 12.3 Empty Statement
  private EmptyStatementTree parseEmptyStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.SEMI_COLON);
    return new EmptyStatementTree(getTreeLocation(start));
  }

  // 12.4 Expression Statement
  private ExpressionStatementTree parseExpressionStatement() {
    SourcePosition start = getTreeStartLocation();
    ParseTree expression = parseExpression();
    eatPossibleImplicitSemiColon();
    return new ExpressionStatementTree(getTreeLocation(start), expression);
  }

  // 12.5 If Statement
  private IfStatementTree parseIfStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.IF);
    eat(TokenType.OPEN_PAREN);
    ParseTree condition = parseExpression();
    eat(TokenType.CLOSE_PAREN);
    ParseTree ifClause = parseStatement();
    ParseTree elseClause = null;
    if (peek(TokenType.ELSE)) {
      eat(TokenType.ELSE);
      elseClause = parseStatement();
    }
    return new IfStatementTree(getTreeLocation(start), condition, ifClause, elseClause);
  }

  // 12.6 Iteration Statements

  // 12.6.1 The do-while Statement
  private ParseTree parseDoWhileStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.DO);
    ParseTree body = parseStatement();
    eat(TokenType.WHILE);
    eat(TokenType.OPEN_PAREN);
    ParseTree condition = parseExpression();
    eat(TokenType.CLOSE_PAREN);
    // The semicolon after the "do-while" is optional.
    if (peek(TokenType.SEMI_COLON)) {
      eat(TokenType.SEMI_COLON);
    }
    return new DoWhileStatementTree(getTreeLocation(start), body, condition);
  }

  // 12.6.2 The while Statement
  private ParseTree parseWhileStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.WHILE);
    eat(TokenType.OPEN_PAREN);
    ParseTree condition = parseExpression();
    eat(TokenType.CLOSE_PAREN);
    ParseTree body = parseStatement();
    return new WhileStatementTree(getTreeLocation(start), condition, body);
  }

  // 12.6.3 The for Statement
  // 12.6.4 The for-in Statement
  // The for-of Statement
  private ParseTree parseForStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.FOR);
    eat(TokenType.OPEN_PAREN);
    if (peekVariableDeclarationList()) {
      VariableDeclarationListTree variables = parseVariableDeclarationListNoIn();
      if (peek(TokenType.IN)) {
        // for-in: only one declaration allowed
        if (variables.declarations.size() > 1) {
          reportError("for-in statement may not have more than one variable declaration");
        }
        VariableDeclarationTree declaration = variables.declarations.get(0);
        if (declaration.initializer != null) {
          // An initializer is allowed here in ES5 and below, but not in ES6.
          // Warn about it, to encourage people to eliminate it from their code.
          // http://esdiscuss.org/topic/initializer-expression-on-for-in-syntax-subject
          if (config.atLeast6) {
            reportError("for-in statement may not have initializer");
          } else {
            errorReporter.reportWarning(declaration.location.start,
                "for-in statement should not have initializer");
          }
        }

        return parseForInStatement(start, variables);
      } else if (peekPredefinedString(PredefinedName.OF)) {
        // for-of: only one declaration allowed
        if (variables.declarations.size() > 1) {
          reportError("for-of statement may not have more than one variable declaration");
        }
        // for-of: initializer is illegal
        VariableDeclarationTree declaration = variables.declarations.get(0);
        if (declaration.initializer != null) {
          reportError("for-of statement may not have initializer");
        }

        return parseForOfStatement(start, variables);
      } else {
        // "Vanilla" for statement: const/destructuring must have initializer
        checkVanillaForInitializers(variables);
        return parseForStatement(start, variables);
      }
    }

    if (peek(TokenType.SEMI_COLON)) {
      return parseForStatement(start, null);
    }

    Predicate<Token> followPred = new Predicate<Token>() {
      @Override
      public boolean apply(Token t) {
        return EnumSet.of(TokenType.IN, TokenType.EQUAL).contains(t.type)
            || (t.type == TokenType.IDENTIFIER
                && t.asIdentifier().value.equals(PredefinedName.OF));
      }
    };
    ParseTree initializer = peekPattern(PatternKind.ANY, followPred)
        ? parsePattern(PatternKind.ANY)
        : parseExpressionNoIn();

    if (peek(TokenType.IN) || peekPredefinedString(PredefinedName.OF)) {
      if (initializer.type != ParseTreeType.BINARY_OPERATOR
          && initializer.type != ParseTreeType.COMMA_EXPRESSION) {
        if (peek(TokenType.IN)) {
          return parseForInStatement(start, initializer);
        } else {
          return parseForOfStatement(start, initializer);
        }
      }
    }

    return parseForStatement(start, initializer);
  }

  // The for-of Statement
  // for  (  { let | var }?  identifier  of  expression  )  statement
  private ParseTree parseForOfStatement(
      SourcePosition start, ParseTree initializer) {
    eatPredefinedString(PredefinedName.OF);
    ParseTree collection = parseExpression();
    eat(TokenType.CLOSE_PAREN);
    ParseTree body = parseStatement();
    return new ForOfStatementTree(
        getTreeLocation(start), initializer, collection, body);
  }

  /** Checks variable declarations in for statements. */
  private void checkVanillaForInitializers(VariableDeclarationListTree variables) {
    for (VariableDeclarationTree declaration : variables.declarations) {
      if (declaration.initializer == null) {
        maybeReportNoInitializer(variables.declarationType, declaration.lvalue);
      }
    }
  }

  /** Reports if declaration requires an initializer, assuming initializer is absent. */
  private void maybeReportNoInitializer(TokenType token, ParseTree lvalue) {
    if (token == TokenType.CONST) {
      reportError("const variables must have an initializer");
    } else if (lvalue.isPattern()) {
      reportError("destructuring must have an initializer");
    }
  }

  private boolean peekVariableDeclarationList() {
    switch(peekType()) {
      case VAR:
      case CONST:
      case LET:
        return true;
      default:
        return false;
    }
  }

  // 12.6.3 The for Statement
  private ParseTree parseForStatement(SourcePosition start, ParseTree initializer) {
    if (initializer == null) {
      initializer = new NullTree(getTreeLocation(getTreeStartLocation()));
    }
    eat(TokenType.SEMI_COLON);

    ParseTree condition;
    if (!peek(TokenType.SEMI_COLON)) {
      condition = parseExpression();
    } else {
      condition = new NullTree(getTreeLocation(getTreeStartLocation()));
    }
    eat(TokenType.SEMI_COLON);

    ParseTree increment;
    if (!peek(TokenType.CLOSE_PAREN)) {
      increment = parseExpression();
    } else {
      increment = new NullTree(getTreeLocation(getTreeStartLocation()));
    }
    eat(TokenType.CLOSE_PAREN);
    ParseTree body = parseStatement();
    return new ForStatementTree(getTreeLocation(start), initializer, condition, increment, body);
  }

  // 12.6.4 The for-in Statement
  private ParseTree parseForInStatement(SourcePosition start, ParseTree initializer) {
    eat(TokenType.IN);
    ParseTree collection = parseExpression();
    eat(TokenType.CLOSE_PAREN);
    ParseTree body = parseStatement();
    return new ForInStatementTree(getTreeLocation(start), initializer, collection, body);
  }

  // 12.7 The continue Statement
  private ParseTree parseContinueStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.CONTINUE);
    IdentifierToken name = null;
    if (!peekImplicitSemiColon()) {
      name = eatIdOpt();
    }
    eatPossibleImplicitSemiColon();
    return new ContinueStatementTree(getTreeLocation(start), name);
  }

  // 12.8 The break Statement
  private ParseTree parseBreakStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.BREAK);
    IdentifierToken name = null;
    if (!peekImplicitSemiColon()) {
      name = eatIdOpt();
    }
    eatPossibleImplicitSemiColon();
    return new BreakStatementTree(getTreeLocation(start), name);
  }

  //12.9 The return Statement
  private ParseTree parseReturnStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.RETURN);
    ParseTree expression = null;
    if (!peekImplicitSemiColon()) {
      expression = parseExpression();
    }
    eatPossibleImplicitSemiColon();
    return new ReturnStatementTree(getTreeLocation(start), expression);
  }

  // 12.10 The with Statement
  private ParseTree parseWithStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.WITH);
    eat(TokenType.OPEN_PAREN);
    ParseTree expression = parseExpression();
    eat(TokenType.CLOSE_PAREN);
    ParseTree body = parseStatement();
    return new WithStatementTree(getTreeLocation(start), expression, body);
  }

  // 12.11 The switch Statement
  private ParseTree parseSwitchStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.SWITCH);
    eat(TokenType.OPEN_PAREN);
    ParseTree expression = parseExpression();
    eat(TokenType.CLOSE_PAREN);
    eat(TokenType.OPEN_CURLY);
    ImmutableList<ParseTree> caseClauses = parseCaseClauses();
    eat(TokenType.CLOSE_CURLY);
    return new SwitchStatementTree(getTreeLocation(start), expression, caseClauses);
  }

  private ImmutableList<ParseTree> parseCaseClauses() {
    boolean foundDefaultClause = false;
    ImmutableList.Builder<ParseTree> result = ImmutableList.builder();

    while (true) {
      SourcePosition start = getTreeStartLocation();
      switch (peekType()) {
      case CASE:
        eat(TokenType.CASE);
        ParseTree expression = parseExpression();
        eat(TokenType.COLON);
        ImmutableList<ParseTree> statements = parseCaseStatementsOpt();
        result.add(new CaseClauseTree(getTreeLocation(start), expression, statements));
        break;
      case DEFAULT:
        if (foundDefaultClause) {
          reportError("Switch statements may have at most one default clause");
        } else {
          foundDefaultClause = true;
        }
        eat(TokenType.DEFAULT);
        eat(TokenType.COLON);
        result.add(new DefaultClauseTree(getTreeLocation(start), parseCaseStatementsOpt()));
        break;
      default:
        return result.build();
      }
    }
  }

  private ImmutableList<ParseTree> parseCaseStatementsOpt() {
    return parseStatementList();
  }

  // 12.12 Labelled Statement
  private ParseTree parseLabelledStatement() {
    SourcePosition start = getTreeStartLocation();
    IdentifierToken name = eatId();
    eat(TokenType.COLON);
    return new LabelledStatementTree(getTreeLocation(start), name, parseStatement());
  }

  private boolean peekLabelledStatement() {
    return peekId()
      && peek(1, TokenType.COLON);
  }

  // 12.13 Throw Statement
  private ParseTree parseThrowStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.THROW);
    ParseTree value = null;
    if (peekImplicitSemiColon()) {
      reportError("semicolon/newline not allowed after 'throw'");
    } else {
      value = parseExpression();
    }
    eatPossibleImplicitSemiColon();
    return new ThrowStatementTree(getTreeLocation(start), value);
  }

  // 12.14 Try Statement
  private ParseTree parseTryStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.TRY);
    ParseTree body = parseBlock();
    ParseTree catchBlock = null;
    if (peek(TokenType.CATCH)) {
      catchBlock = parseCatch();
    }
    ParseTree finallyBlock = null;
    if (peek(TokenType.FINALLY)) {
      finallyBlock = parseFinallyBlock();
    }
    if (catchBlock == null && finallyBlock == null) {
      reportError("'catch' or 'finally' expected.");
    }
    return new TryStatementTree(getTreeLocation(start), body, catchBlock, finallyBlock);
  }

  private CatchTree parseCatch() {
    SourcePosition start = getTreeStartLocation();
    CatchTree catchBlock;
    eat(TokenType.CATCH);
    eat(TokenType.OPEN_PAREN);
    ParseTree exception;
    if (peekPatternStart()) {
      exception = parsePattern(PatternKind.INITIALIZER);
    } else {
      exception = parseIdentifierExpression();
    }
    eat(TokenType.CLOSE_PAREN);
    BlockTree catchBody = parseBlock();
    catchBlock = new CatchTree(getTreeLocation(start), exception, catchBody);
    return catchBlock;
  }

  private FinallyTree parseFinallyBlock() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.FINALLY);
    BlockTree finallyBlock = parseBlock();
    return new FinallyTree(getTreeLocation(start), finallyBlock);
  }

  // 12.15 The Debugger Statement
  private ParseTree parseDebuggerStatement() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.DEBUGGER);
    eatPossibleImplicitSemiColon();

    return new DebuggerStatementTree(getTreeLocation(start));
  }

  // 11.1 Primary Expressions
  private ParseTree parsePrimaryExpression() {
    switch (peekType()) {
    case CLASS:
      return parseClassExpression();
    case SUPER:
      return parseSuperExpression();
    case THIS:
      return parseThisExpression();
    case IDENTIFIER:
      return parseIdentifierExpression();
    case NUMBER:
    case STRING:
    case TRUE:
    case FALSE:
    case NULL:
      return parseLiteralExpression();
    case NO_SUBSTITUTION_TEMPLATE:
    case TEMPLATE_HEAD:
      return parseTemplateLiteral(null);
    case OPEN_SQUARE:
      return parseArrayInitializer();
    case OPEN_CURLY:
      return parseObjectLiteral();
    case OPEN_PAREN:
      return parseParenExpression();
    case SLASH:
    case SLASH_EQUAL:
      return parseRegularExpressionLiteral();
    default:
      return parseMissingPrimaryExpression();
    }
  }

  private SuperExpressionTree parseSuperExpression() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.SUPER);
    return new SuperExpressionTree(getTreeLocation(start));
  }

  private ThisExpressionTree parseThisExpression() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.THIS);
    return new ThisExpressionTree(getTreeLocation(start));
  }

  private IdentifierExpressionTree parseIdentifierExpression() {
    SourcePosition start = getTreeStartLocation();
    IdentifierToken identifier = eatId();
    return new IdentifierExpressionTree(getTreeLocation(start), identifier);
  }

  private LiteralExpressionTree parseLiteralExpression() {
    SourcePosition start = getTreeStartLocation();
    Token literal = nextLiteralToken();
    return new LiteralExpressionTree(getTreeLocation(start), literal);
  }

  /**
   * Constructs a template literal expression tree. "operand" is used to handle
   * the case like "foo`bar`", which is a CallExpression or MemberExpression that
   * calls the function foo() with the template literal as the argument (with extra
   * handling). In this case, operand would be "foo", which is the callsite.
   *
   * <p>We store this operand in the TemplateLiteralExpressionTree and
   * generate a CALL node if it's not null later when transpiling.
   *
   * @param operand A non-null value would represent the callsite
   * @return The template literal expression
   */
  private TemplateLiteralExpressionTree parseTemplateLiteral(ParseTree operand) {
    SourcePosition start = operand == null
        ? getTreeStartLocation()
        : operand.location.start;
    Token token = nextToken();
    ImmutableList.Builder<ParseTree> elements = ImmutableList.builder();
    elements.add(new TemplateLiteralPortionTree(token.location, token));
    if (token.type == TokenType.NO_SUBSTITUTION_TEMPLATE) {
      return new TemplateLiteralExpressionTree(
          getTreeLocation(start), operand, elements.build());
    }

    // `abc${
    ParseTree expression = parseExpression();
    elements.add(new TemplateSubstitutionTree(expression.location, expression));
    while (!errorReporter.hadError()) {
      token = nextTemplateLiteralToken();
      if (token.type == TokenType.ERROR || token.type == TokenType.END_OF_FILE) {
        break;
      }

      elements.add(new TemplateLiteralPortionTree(token.location, token));
      if (token.type == TokenType.TEMPLATE_TAIL) {
        break;
      }

      expression = parseExpression();
      elements.add(new TemplateSubstitutionTree(expression.location, expression));
    }

    return new TemplateLiteralExpressionTree(
        getTreeLocation(start), operand, elements.build());
  }

  private Token nextLiteralToken() {
    return nextToken();
  }

  private ParseTree parseRegularExpressionLiteral() {
    SourcePosition start = getTreeStartLocation();
    LiteralToken literal = nextRegularExpressionLiteralToken();
    return new LiteralExpressionTree(getTreeLocation(start), literal);
  }

  private ParseTree parseArrayInitializer() {
    if (peekType(1) == TokenType.FOR) {
      return parseArrayComprehension();
    } else {
      return parseArrayLiteral();
    }
  }

  private ParseTree parseGeneratorComprehension() {
    return parseComprehension(
        ComprehensionTree.ComprehensionType.GENERATOR,
        TokenType.OPEN_PAREN, TokenType.CLOSE_PAREN);
  }

  private ParseTree parseArrayComprehension() {
    return parseComprehension(
        ComprehensionTree.ComprehensionType.ARRAY,
        TokenType.OPEN_SQUARE, TokenType.CLOSE_SQUARE);
  }

  private ParseTree parseComprehension(
      ComprehensionTree.ComprehensionType type,
      TokenType startToken, TokenType endToken) {
    SourcePosition start = getTreeStartLocation();
    eat(startToken);

    ImmutableList.Builder<ParseTree> children = ImmutableList.builder();
    while (peek(TokenType.FOR) || peek(TokenType.IF)) {
      if (peek(TokenType.FOR)) {
        children.add(parseComprehensionFor());
      } else {
        children.add(parseComprehensionIf());
      }
    }

    ParseTree tailExpression = parseAssignmentExpression();
    eat(endToken);

    return new ComprehensionTree(
        getTreeLocation(start),
        type,
        children.build(),
        tailExpression);
  }

  private ParseTree parseComprehensionFor() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.FOR);
    eat(TokenType.OPEN_PAREN);

    ParseTree initializer;
    if (peekId()) {
      initializer = parseIdentifierExpression();
    } else {
      initializer = parsePattern(PatternKind.ANY);
    }

    eatPredefinedString(PredefinedName.OF);
    ParseTree collection = parseAssignmentExpression();
    eat(TokenType.CLOSE_PAREN);
    return new ComprehensionForTree(
        getTreeLocation(start), initializer, collection);
  }

  private ParseTree parseComprehensionIf() {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.IF);
    eat(TokenType.OPEN_PAREN);
    ParseTree initializer = parseAssignmentExpression();
    eat(TokenType.CLOSE_PAREN);
    return new ComprehensionIfTree(
        getTreeLocation(start), initializer);
  }

  // 11.1.4 Array Literal Expression
  private ParseTree parseArrayLiteral() {
    // ArrayLiteral :
    //   [ Elisionopt ]
    //   [ ElementList ]
    //   [ ElementList , Elisionopt ]
    //
    // ElementList :
    //   Elisionopt AssignmentOrSpreadExpression
    //   ElementList , Elisionopt AssignmentOrSpreadExpression
    //
    // Elision :
    //   ,
    //   Elision ,

    SourcePosition start = getTreeStartLocation();
    ImmutableList.Builder<ParseTree> elements = ImmutableList.builder();

    eat(TokenType.OPEN_SQUARE);
    Token trailingCommaToken = null;
    while (peek(TokenType.COMMA) || peek(TokenType.SPREAD) || peekAssignmentExpression()) {
      trailingCommaToken = null;
      if (peek(TokenType.COMMA)) {
        elements.add(new NullTree(getTreeLocation(getTreeStartLocation())));
      } else {
        if (peek(TokenType.SPREAD)) {
          elements.add(parseSpreadExpression());
        } else {
          elements.add(parseAssignmentExpression());
        }
      }
      if (!peek(TokenType.CLOSE_SQUARE)) {
        trailingCommaToken = eat(TokenType.COMMA);
      }
    }
    eat(TokenType.CLOSE_SQUARE);

    maybeReportTrailingComma(trailingCommaToken);

    return new ArrayLiteralExpressionTree(
        getTreeLocation(start), elements.build());
  }

  // 11.1.4 Object Literal Expression
  private ParseTree parseObjectLiteral() {
    SourcePosition start = getTreeStartLocation();
    ImmutableList.Builder<ParseTree> result = ImmutableList.builder();

    eat(TokenType.OPEN_CURLY);
    Token commaToken = null;
    while (peekPropertyNameOrComputedProp(0) || peek(TokenType.STAR)) {
      commaToken = null;
      result.add(parsePropertyAssignment());
      commaToken = eatOpt(TokenType.COMMA);
      if (commaToken == null) {
        break;
      }
    }
    eat(TokenType.CLOSE_CURLY);

    maybeReportTrailingComma(commaToken);

    return new ObjectLiteralExpressionTree(getTreeLocation(start), result.build());
  }

  void maybeReportTrailingComma(Token commaToken) {
    if (commaToken != null && config.warnTrailingCommas) {
      // In ES3 mode warn about trailing commas which aren't accepted by
      // older browsers (such as IE8).
      errorReporter.reportWarning(commaToken.location.start,
          "Trailing comma is not legal in an ECMA-262 object initializer");
    }
  }

  private boolean peekPropertyNameOrComputedProp(int tokenIndex) {
    return peekPropertyName(tokenIndex)
        || peekType(tokenIndex) == TokenType.OPEN_SQUARE;
  }

  private boolean peekPropertyName(int tokenIndex) {
    TokenType type = peekType(tokenIndex);
    switch (type) {
    case IDENTIFIER:
    case STRING:
    case NUMBER:
      return true;
    default:
      return Keywords.isKeyword(type);
    }
  }

  private ParseTree parsePropertyAssignment() {
    TokenType type = peekType();
    if (type == TokenType.STAR) {
      return parsePropertyAssignmentGenerator();
    } else if (type == TokenType.STRING
        || type == TokenType.NUMBER
        || type == TokenType.IDENTIFIER
        || Keywords.isKeyword(type)) {
      if (peekGetAccessor(false)) {
        return parseGetAccessor();
      } else if (peekSetAccessor(false)) {
        return parseSetAccessor();
      } else if (peekType(1) == TokenType.OPEN_PAREN) {
        return parseClassMemberDeclaration(false);
      } else {
        return parsePropertyNameAssignment();
      }
    } else if (type == TokenType.OPEN_SQUARE) {
      SourcePosition start = getTreeStartLocation();
      ParseTree name = parseComputedPropertyName();

      if (peek(TokenType.COLON)) {
        eat(TokenType.COLON);
        ParseTree value = parseAssignmentExpression();
        return new ComputedPropertyDefinitionTree(getTreeLocation(start), name, value);
      } else {
        ParseTree value = parseFunctionTail(
            start, null, false, false, FunctionDeclarationTree.Kind.EXPRESSION);
        return new ComputedPropertyMethodTree(getTreeLocation(start), name, value);
      }
    } else {
      throw new RuntimeException("unreachable");
    }
  }

  private ParseTree parsePropertyAssignmentGenerator() {
    TokenType type = peekType(1);
    if (type == TokenType.STRING
        || type == TokenType.NUMBER
        || type == TokenType.IDENTIFIER
        || Keywords.isKeyword(type)) {
      // parseMethodDeclaration will consume the '*'.
      return parseClassMemberDeclaration(false);
    } else {
      SourcePosition start = getTreeStartLocation();
      eat(TokenType.STAR);
      ParseTree name = parseComputedPropertyName();

      ParseTree value = parseFunctionTail(
          start, null, false, true, FunctionDeclarationTree.Kind.EXPRESSION);
      return new ComputedPropertyMethodTree(getTreeLocation(start), name, value);
    }
  }

  private ParseTree parseComputedPropertyName() {

    eat(TokenType.OPEN_SQUARE);
    ParseTree assign = parseAssignmentExpression();
    eat(TokenType.CLOSE_SQUARE);
    return assign;
  }

  private boolean peekGetAccessor(boolean allowStatic) {
    int index = allowStatic && peek(TokenType.STATIC) ? 1 : 0;
    return peekPredefinedString(index, PredefinedName.GET)
        && peekPropertyNameOrComputedProp(index + 1);
  }

  private boolean peekPredefinedString(String string) {
    return peekPredefinedString(0, string);
  }

  private Token eatPredefinedString(String string) {
    Token token = eatId();
    if (token == null || !token.asIdentifier().value.equals(string)) {
      reportExpectedError(token, string);
      return null;
    }
    return token;
  }

  private boolean peekPredefinedString(int index, String string) {
    return peek(index, TokenType.IDENTIFIER)
        && ((IdentifierToken) peekToken(index)).value.equals(string);
  }

  private ParseTree parseGetAccessor() {
    SourcePosition start = getTreeStartLocation();
    boolean isStatic = eatOpt(TokenType.STATIC) != null;
    eatPredefinedString(PredefinedName.GET);

    if (peekPropertyName(0)) {
      Token propertyName = eatObjectLiteralPropertyName();
      eat(TokenType.OPEN_PAREN);
      eat(TokenType.CLOSE_PAREN);
      BlockTree body = parseFunctionBody();
      return new GetAccessorTree(getTreeLocation(start), propertyName, isStatic, body);
    } else {
      ParseTree property = parseComputedPropertyName();
      eat(TokenType.OPEN_PAREN);
      eat(TokenType.CLOSE_PAREN);
      BlockTree body = parseFunctionBody();
      return new ComputedPropertyGetterTree(
          getTreeLocation(start), property, isStatic, body);
    }
  }

  private boolean peekSetAccessor(boolean allowStatic) {
    int index = allowStatic && peek(TokenType.STATIC) ? 1 : 0;
    return peekPredefinedString(index, PredefinedName.SET)
        && peekPropertyNameOrComputedProp(index + 1);
  }

  private ParseTree parseSetAccessor() {
    SourcePosition start = getTreeStartLocation();
    boolean isStatic = eatOpt(TokenType.STATIC) != null;
    eatPredefinedString(PredefinedName.SET);
    if (peekPropertyName(0)) {
      Token propertyName = eatObjectLiteralPropertyName();
      eat(TokenType.OPEN_PAREN);
      IdentifierToken parameter = eatId();
      eat(TokenType.CLOSE_PAREN);
      BlockTree body = parseFunctionBody();
      return new SetAccessorTree(
          getTreeLocation(start), propertyName, isStatic, parameter, body);
    } else {
      ParseTree property = parseComputedPropertyName();
      eat(TokenType.OPEN_PAREN);
      IdentifierToken parameter = eatId();
      eat(TokenType.CLOSE_PAREN);
      BlockTree body = parseFunctionBody();
      return new ComputedPropertySetterTree(
          getTreeLocation(start), property, isStatic, parameter, body);
    }
  }

  private ParseTree parsePropertyNameAssignment() {
    SourcePosition start = getTreeStartLocation();
    Token name = eatObjectLiteralPropertyName();
    Token colon = eatOpt(TokenType.COLON);
    if (colon == null) {
      if (name.type != TokenType.IDENTIFIER) {
        reportExpectedError(peekToken(), TokenType.COLON);
      } else if (Keywords.isKeyword(name.asIdentifier().value)) {
        reportError(name, "Cannot use keyword in short object literal");
      }
    }
    ParseTree value = colon == null ? null : parseAssignmentExpression();
    return new PropertyNameAssignmentTree(getTreeLocation(start), name, value);
  }

  private ParseTree parseParenExpression() {
    if (peekType(1) == TokenType.FOR) {
      return parseGeneratorComprehension();
    }

    SourcePosition start = getTreeStartLocation();
    eat(TokenType.OPEN_PAREN);
    ParseTree result = parseExpression();
    eat(TokenType.CLOSE_PAREN);
    return new ParenExpressionTree(getTreeLocation(start), result);
  }

  private ParseTree parseMissingPrimaryExpression() {
    SourcePosition start = getTreeStartLocation();
    nextToken();
    reportError("primary expression expected");
    return new MissingPrimaryExpressionTree(getTreeLocation(start));
  }

  /**
   * Differentiates between parsing for 'In' vs. 'NoIn'
   * Variants of expression grammars.
   */
  private enum Expression {
    NO_IN,
    NORMAL,
  }

  // 11.14 Expressions
  private ParseTree parseExpressionNoIn() {
    return parse(Expression.NO_IN);
  }

  private ParseTree parseExpression() {
    return parse(Expression.NORMAL);
  }

  private boolean peekExpression() {
    switch (peekType()) {
      case BANG:
      case CLASS:
      case DELETE:
      case FALSE:
      case FUNCTION:
      case IDENTIFIER:
      case MINUS:
      case MINUS_MINUS:
      case NEW:
      case NULL:
      case NUMBER:
      case OPEN_CURLY:
      case OPEN_PAREN:
      case OPEN_SQUARE:
      case PLUS:
      case PLUS_PLUS:
      case SLASH: // regular expression literal
      case SLASH_EQUAL:
      case STRING:
      case NO_SUBSTITUTION_TEMPLATE:
      case TEMPLATE_HEAD:
      case SUPER:
      case THIS:
      case TILDE:
      case TRUE:
      case TYPEOF:
      case VOID:
      case YIELD:
        return true;
      default:
        return false;
    }
  }

  private ParseTree parse(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree result = parseAssignment(expressionIn);
    if (peek(TokenType.COMMA)) {
      ImmutableList.Builder<ParseTree> exprs = ImmutableList.builder();
      exprs.add(result);
      while (peek(TokenType.COMMA)) {
        eat(TokenType.COMMA);
        exprs.add(parseAssignment(expressionIn));
      }
      return new CommaExpressionTree(getTreeLocation(start), exprs.build());
    }
    return result;
  }

  // 11.13 Assignment expressions
  private ParseTree parseAssignmentExpression() {
    return parseAssignment(Expression.NORMAL);
  }

  private boolean peekAssignmentExpression() {
    return peekExpression();
  }

  private ParseTree parseAssignment(Expression expressionIn) {
    if (peek(TokenType.YIELD) && inGeneratorContext()) {
      return parseYield(expressionIn);
    }

    if (peekArrowFunction()) {
      return parseArrowFunction(expressionIn);
    }

    SourcePosition start = getTreeStartLocation();
    ParseTree left = peekParenPatternAssignment()
        ? parseParenPattern()
        : parseConditional(expressionIn);

    if (peekAssignmentOperator()) {
      if (!left.isValidAssignmentTarget()) {
        reportError("invalid assignment target");
      }
      Token operator = nextToken();
      ParseTree right = parseAssignment(expressionIn);
      return new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  private boolean peekAssignmentOperator() {
    switch (peekType()) {
    case EQUAL:
    case STAR_EQUAL:
    case SLASH_EQUAL:
    case PERCENT_EQUAL:
    case PLUS_EQUAL:
    case MINUS_EQUAL:
    case LEFT_SHIFT_EQUAL:
    case RIGHT_SHIFT_EQUAL:
    case UNSIGNED_RIGHT_SHIFT_EQUAL:
    case AMPERSAND_EQUAL:
    case CARET_EQUAL:
    case BAR_EQUAL:
      return true;
    default:
      return false;
    }
  }

  private boolean inGeneratorContext() {
    // disallow yield outside of generators
    return inGeneratorContext.peekLast();
  }

  // yield [no line terminator] (*)? AssignExpression
  // https://people.mozilla.org/~jorendorff/es6-draft.html#sec-generator-function-definitions-runtime-semantics-evaluation
  private ParseTree parseYield(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    eat(TokenType.YIELD);
    boolean isYieldFor = false;
    ParseTree expression = null;
    if (!peekImplicitSemiColon()) {
      isYieldFor = eatOpt(TokenType.STAR) != null;
      if (peekAssignmentExpression()) {
        expression = parseAssignment(expressionIn);
      }
    }
    return new YieldExpressionTree(
        getTreeLocation(start), isYieldFor, expression);
  }

  // 11.12 Conditional Expression
  private ParseTree parseConditional(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree condition = parseLogicalOR(expressionIn);
    if (peek(TokenType.QUESTION)) {
      eat(TokenType.QUESTION);
      ParseTree left = parseAssignment(expressionIn);
      eat(TokenType.COLON);
      ParseTree right = parseAssignment(expressionIn);
      return new ConditionalExpressionTree(
          getTreeLocation(start), condition, left, right);
    }
    return condition;
  }

  // 11.11 Logical OR
  private ParseTree parseLogicalOR(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseLogicalAND(expressionIn);
    while (peek(TokenType.OR)){
      Token operator = eat(TokenType.OR);
      ParseTree right = parseLogicalAND(expressionIn);
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  // 11.11 Logical AND
  private ParseTree parseLogicalAND(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseBitwiseOR(expressionIn);
    while (peek(TokenType.AND)){
      Token operator = eat(TokenType.AND);
      ParseTree right = parseBitwiseOR(expressionIn);
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  // 11.10 Bitwise OR
  private ParseTree parseBitwiseOR(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseBitwiseXOR(expressionIn);
    while (peek(TokenType.BAR)){
      Token operator = eat(TokenType.BAR);
      ParseTree right = parseBitwiseXOR(expressionIn);
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  // 11.10 Bitwise XOR
  private ParseTree parseBitwiseXOR(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseBitwiseAND(expressionIn);
    while (peek(TokenType.CARET)){
      Token operator = eat(TokenType.CARET);
      ParseTree right = parseBitwiseAND(expressionIn);
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  // 11.10 Bitwise AND
  private ParseTree parseBitwiseAND(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseEquality(expressionIn);
    while (peek(TokenType.AMPERSAND)){
      Token operator = eat(TokenType.AMPERSAND);
      ParseTree right = parseEquality(expressionIn);
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  // 11.9 Equality Expression
  private ParseTree parseEquality(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseRelational(expressionIn);
    while (peekEqualityOperator()){
      Token operator = nextToken();
      ParseTree right = parseRelational(expressionIn);
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  private boolean peekEqualityOperator() {
    switch (peekType()) {
    case EQUAL_EQUAL:
    case NOT_EQUAL:
    case EQUAL_EQUAL_EQUAL:
    case NOT_EQUAL_EQUAL:
      return true;
    default:
      return false;
    }
  }

  // 11.8 Relational
  private ParseTree parseRelational(Expression expressionIn) {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseShiftExpression();
    while (peekRelationalOperator(expressionIn)){
      Token operator = nextToken();
      ParseTree right = parseShiftExpression();
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  private boolean peekRelationalOperator(Expression expressionIn) {
    switch (peekType()) {
    case OPEN_ANGLE:
    case CLOSE_ANGLE:
    case GREATER_EQUAL:
    case LESS_EQUAL:
    case INSTANCEOF:
      return true;
    case IN:
      return expressionIn == Expression.NORMAL;
    default:
      return false;
    }
  }

  // 11.7 Shift Expression
  private ParseTree parseShiftExpression() {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseAdditiveExpression();
    while (peekShiftOperator()){
      Token operator = nextToken();
      ParseTree right = parseAdditiveExpression();
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  private boolean peekShiftOperator() {
    switch (peekType()) {
    case LEFT_SHIFT:
    case RIGHT_SHIFT:
    case UNSIGNED_RIGHT_SHIFT:
      return true;
    default:
      return false;
    }
  }

  // 11.6 Additive Expression
  private ParseTree parseAdditiveExpression() {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseMultiplicativeExpression();
    while (peekAdditiveOperator()){
      Token operator = nextToken();
      ParseTree right = parseMultiplicativeExpression();
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  private boolean peekAdditiveOperator() {
    switch (peekType()) {
    case PLUS:
    case MINUS:
      return true;
    default:
      return false;
    }
  }

  // 11.5 Multiplicative Expression
  private ParseTree parseMultiplicativeExpression() {
    SourcePosition start = getTreeStartLocation();
    ParseTree left = parseUnaryExpression();
    while (peekMultiplicativeOperator()){
      Token operator = nextToken();
      ParseTree right = parseUnaryExpression();
      left = new BinaryOperatorTree(getTreeLocation(start), left, operator, right);
    }
    return left;
  }

  private boolean peekMultiplicativeOperator() {
    switch (peekType()) {
    case STAR:
    case SLASH:
    case PERCENT:
      return true;
    default:
      return false;
    }
  }

  // 11.4 Unary Operator
  private ParseTree parseUnaryExpression() {
    SourcePosition start = getTreeStartLocation();
    if (peekUnaryOperator()) {
      Token operator = nextToken();
      ParseTree operand = parseUnaryExpression();
      return new UnaryExpressionTree(getTreeLocation(start), operator, operand);
    }
    return parsePostfixExpression();
  }

  private boolean peekUnaryOperator() {
    switch (peekType()) {
    case DELETE:
    case VOID:
    case TYPEOF:
    case PLUS_PLUS:
    case MINUS_MINUS:
    case PLUS:
    case MINUS:
    case TILDE:
    case BANG:
      return true;
    default:
      return false;
    }
  }

  // 11.3 Postfix Expression
  private ParseTree parsePostfixExpression() {
    SourcePosition start = getTreeStartLocation();
    ParseTree operand = parseLeftHandSideExpression();
    while (peekPostfixOperator()) {
      Token operator = nextToken();
      operand = new PostfixExpressionTree(getTreeLocation(start), operand, operator);
    }
    return operand;
  }

  private boolean peekPostfixOperator() {
    if (peekImplicitSemiColon()) {
      return false;
    }
    switch (peekType()) {
    case PLUS_PLUS:
    case MINUS_MINUS:
      return true;
    default:
      return false;
    }
  }

  // 11.2 Left hand side expression
  //
  // Also inlines the call expression productions
  @SuppressWarnings("incomplete-switch")
  private ParseTree parseLeftHandSideExpression() {
    SourcePosition start = getTreeStartLocation();
    ParseTree operand = parseNewExpression();

    // this test is equivalent to is member expression
    if (!(operand instanceof NewExpressionTree)
        || ((NewExpressionTree) operand).arguments != null) {

      // The Call expression productions
      while (peekCallSuffix()) {
        switch (peekType()) {
        case OPEN_PAREN:
          ArgumentListTree arguments = parseArguments();
          operand = new CallExpressionTree(getTreeLocation(start), operand, arguments);
          break;
        case OPEN_SQUARE:
          eat(TokenType.OPEN_SQUARE);
          ParseTree member = parseExpression();
          eat(TokenType.CLOSE_SQUARE);
          operand = new MemberLookupExpressionTree(getTreeLocation(start), operand, member);
          break;
        case PERIOD:
          eat(TokenType.PERIOD);
          IdentifierToken id = eatIdOrKeywordAsId();
          operand = new MemberExpressionTree(getTreeLocation(start), operand, id);
          break;
        case NO_SUBSTITUTION_TEMPLATE:
        case TEMPLATE_HEAD:
          operand = parseTemplateLiteral(operand);
        }
      }
    }
    return operand;
  }

  private boolean peekCallSuffix() {
    return peek(TokenType.OPEN_PAREN)
        || peek(TokenType.OPEN_SQUARE)
        || peek(TokenType.PERIOD)
        || peek(TokenType.NO_SUBSTITUTION_TEMPLATE)
        || peek(TokenType.TEMPLATE_HEAD);
  }

  // 11.2 Member Expression without the new production
  private ParseTree parseMemberExpressionNoNew() {
    SourcePosition start = getTreeStartLocation();
    ParseTree operand;
    if (peekFunction()) {
      operand = parseFunctionExpression();
    } else {
      operand = parsePrimaryExpression();
    }
    while (peekMemberExpressionSuffix()) {
      switch (peekType()) {
        case OPEN_SQUARE:
          eat(TokenType.OPEN_SQUARE);
          ParseTree member = parseExpression();
          eat(TokenType.CLOSE_SQUARE);
          operand = new MemberLookupExpressionTree(
              getTreeLocation(start), operand, member);
          break;
        case PERIOD:
          eat(TokenType.PERIOD);
          IdentifierToken id = eatIdOrKeywordAsId();
          operand = new MemberExpressionTree(getTreeLocation(start), operand, id);
          break;
        case NO_SUBSTITUTION_TEMPLATE:
        case TEMPLATE_HEAD:
          operand = parseTemplateLiteral(operand);
          break;
        default:
          throw new RuntimeException("unreachable");
      }
    }
    return operand;
  }

  private boolean peekMemberExpressionSuffix() {
    return peek(TokenType.OPEN_SQUARE) || peek(TokenType.PERIOD)
        || peek(TokenType.NO_SUBSTITUTION_TEMPLATE)
        || peek(TokenType.TEMPLATE_HEAD);
  }

  // 11.2 New Expression
  private ParseTree parseNewExpression() {
    if (peek(TokenType.NEW)) {
      SourcePosition start = getTreeStartLocation();
      eat(TokenType.NEW);
      ParseTree operand = parseNewExpression();
      ArgumentListTree arguments = null;
      if (peek(TokenType.OPEN_PAREN)) {
        arguments = parseArguments();
      }
      return new NewExpressionTree(getTreeLocation(start), operand, arguments);
    } else {
      return parseMemberExpressionNoNew();
    }
  }

  private ArgumentListTree parseArguments() {
    // ArgumentList :
    //   AssignmentOrSpreadExpression
    //   ArgumentList , AssignmentOrSpreadExpression
    //
    // AssignmentOrSpreadExpression :
    //   ... AssignmentExpression
    //   AssignmentExpression

    SourcePosition start = getTreeStartLocation();
    ImmutableList.Builder<ParseTree> arguments = ImmutableList.builder();

    eat(TokenType.OPEN_PAREN);
    while (peekAssignmentOrSpread()) {
      arguments.add(parseAssignmentOrSpread());

      if (!peek(TokenType.CLOSE_PAREN)) {
        eat(TokenType.COMMA);
        if (peek(TokenType.CLOSE_PAREN)) {
          reportError("Invalid trailing comma in arguments list");
        }
      }
    }
    eat(TokenType.CLOSE_PAREN);
    return new ArgumentListTree(getTreeLocation(start), arguments.build());
  }

  /**
   * Whether we have a spread expression or an assignment next.
   *
   * <p>This does not peek the operand for the spread expression. This means that
   * {@link #parseAssignmentOrSpread} might still fail when this returns true.
   */
  private boolean peekAssignmentOrSpread() {
    return peek(TokenType.SPREAD) || peekAssignmentExpression();
  }

  private ParseTree parseAssignmentOrSpread() {
    if (peek(TokenType.SPREAD)) {
      return parseSpreadExpression();
    }
    return parseAssignmentExpression();
  }

  // Destructuring (aka pattern matching); see
  // http://wiki.ecmascript.org/doku.php?id=harmony:destructuring

  // Kinds of destructuring patterns
  private enum PatternKind {
    // A var, let, const; catch head; or formal parameter list--only
    // identifiers are allowed as lvalues
    INITIALIZER,
    // An assignment or for-in initializer--any lvalue is allowed
    ANY,
  }

  private boolean peekParenPatternAssignment() {
    return peekParenPattern(PatternKind.ANY, assignmentFollowSet);
  }

  private boolean peekParenPatternStart() {
    int index = 0;
    while (peek(index, TokenType.OPEN_PAREN)) {
      index++;
    }
    return peekPatternStart(index);
  }

  private boolean peekPatternStart() {
    return peekPatternStart(0);
  }

  private boolean peekPatternStart(int index) {
    return peek(index, TokenType.OPEN_SQUARE) || peek(index, TokenType.OPEN_CURLY);
  }

  private ParseTree parseParenPattern() {
    return parseParenPattern(PatternKind.ANY);
  }

  private ParseTree parseParenPattern(PatternKind kind) {
    if (peek(TokenType.OPEN_PAREN)) {
      SourcePosition start = getTreeStartLocation();
      eat(TokenType.OPEN_PAREN);
      ParseTree result = parseParenPattern(kind);
      eat(TokenType.CLOSE_PAREN);
      return new ParenExpressionTree(this.getTreeLocation(start), result);
    } else {
      return parsePattern(kind);
    }
  }

  private boolean peekPattern(PatternKind kind) {
    return peekPattern(kind, Predicates.<Token>alwaysTrue());
  }

  private boolean peekPattern(PatternKind kind, Predicate<Token> follow) {
    if (!peekPatternStart()) {
      return false;
    }
    Parser p = createLookaheadParser();
    try {
      p.parsePattern(kind);
      return follow.apply(p.peekToken());
    } catch (ParseException e) {
      return false;
    }
  }

  private boolean peekParenPattern(PatternKind kind, EnumSet<TokenType> follow) {
    if (!peekParenPatternStart()) {
      return false;
    }
    Parser p = createLookaheadParser();
    try {
      p.parseParenPattern(kind);
      return follow.contains(p.peekType());
    } catch (ParseException e) {
      return false;
    }
  }

  private ParseTree parsePattern(PatternKind kind) {
    switch (peekType()) {
      case OPEN_SQUARE:
        return parseArrayPattern(kind);
      case OPEN_CURLY:
      default:
        return parseObjectPattern(kind);
    }
  }

  private boolean peekPatternElement() {
    return peekExpression() || peek(TokenType.SPREAD);
  }

  private static final EnumSet<TokenType> assignmentFollowSet =
      EnumSet.of(TokenType.EQUAL);

  // Element ::= Pattern | LValue | ... LValue
  private ParseTree parseArrayPatternElement(PatternKind kind) {
    SourcePosition start = getTreeStartLocation();
    ParseTree lvalue;
    boolean rest = false;

    // [ or { are preferably the start of a sub-pattern
    if (peekParenPatternStart()) {
      lvalue = parseParenPattern(kind);
    } else {
      // An element that's not a sub-pattern

      if (peek(TokenType.SPREAD)) {
        eat(TokenType.SPREAD);
        rest = true;
      }

      lvalue = parseLeftHandSideExpression();
    }

    if (rest && lvalue.type != ParseTreeType.IDENTIFIER_EXPRESSION) {
      reportError("lvalues in rest elements must be identifiers");
      return lvalue;
    }

    if (rest) {
      return new AssignmentRestElementTree(
          getTreeLocation(start),
          lvalue.asIdentifierExpression().identifierToken);
    }

    Token eq = eatOpt(TokenType.EQUAL);
    if (eq != null) {
      ParseTree defaultValue = parseAssignmentExpression();
      return new DefaultParameterTree(getTreeLocation(start),
          lvalue, defaultValue);
    }
    return lvalue;
  }

  // Pattern ::= ... | "[" Element? ("," Element?)* "]"
  private ParseTree parseArrayPattern(PatternKind kind) {
    SourcePosition start = getTreeStartLocation();
    ImmutableList.Builder<ParseTree> elements = ImmutableList.builder();
    eat(TokenType.OPEN_SQUARE);
    while (peek(TokenType.COMMA) || peekPatternElement()) {
      if (peek(TokenType.COMMA)) {
        eat(TokenType.COMMA);
        elements.add(new NullTree(getTreeLocation(getTreeStartLocation())));
      } else {
        ParseTree element = parseArrayPatternElement(kind);
        elements.add(element);

        if (element.isAssignmentRestElement()) {
          // Rest can only appear in the posterior, so we must be done
          break;
        } else if (peek(TokenType.COMMA)) {
          // Consume the comma separator
          eat(TokenType.COMMA);
          if (peek(TokenType.CLOSE_SQUARE)) {
            reportError("Array pattern may not end with a comma");
            break;
          }
        } else {
          // Otherwise we must be done
          break;
        }
      }
    }
    eat(TokenType.CLOSE_SQUARE);
    return new ArrayPatternTree(getTreeLocation(start), elements.build());
  }

  // Pattern ::= "{" (Field ("," Field)* ","?)? "}" | ...
  private ParseTree parseObjectPattern(PatternKind kind) {
    SourcePosition start = getTreeStartLocation();
    ImmutableList.Builder<ParseTree> fields = ImmutableList.builder();
    eat(TokenType.OPEN_CURLY);
    while (peekObjectPatternField()) {
      fields.add(parseObjectPatternField(kind));
      if (peek(TokenType.COMMA)) {
        // Consume the comma separator
        eat(TokenType.COMMA);
      } else {
        // Otherwise we must be done
        break;
      }
    }
    eat(TokenType.CLOSE_CURLY);
    return new ObjectPatternTree(getTreeLocation(start), fields.build());
  }

  private boolean peekObjectPatternField() {
    return peekPropertyNameOrComputedProp(0);
  }

  private ParseTree parseObjectPatternField(PatternKind kind) {
    SourcePosition start = getTreeStartLocation();
    if (peekType() == TokenType.OPEN_SQUARE) {
      ParseTree key = parseComputedPropertyName();
      eat(TokenType.COLON);
      ParseTree value = parseObjectPatternFieldTail(kind);
      return new ComputedPropertyDefinitionTree(getTreeLocation(start), key, value);
    }

    Token name;
    if (peekId() || Keywords.isKeyword(peekType())) {
      name = eatIdOrKeywordAsId();
      if (!peek(TokenType.COLON)) {
        IdentifierToken idToken = (IdentifierToken) name;
        if (Keywords.isKeyword(idToken.value)) {
          reportError("cannot use keyword '" + name + "' here.");
        }
        if (peek(TokenType.EQUAL)) {
          IdentifierExpressionTree idTree = new IdentifierExpressionTree(
              getTreeLocation(start), idToken);
          eat(TokenType.EQUAL);
          ParseTree defaultValue = parseAssignmentExpression();
          return new DefaultParameterTree(getTreeLocation(start), idTree, defaultValue);
        }
        return new PropertyNameAssignmentTree(getTreeLocation(start), name, null);
      }
    } else {
      name = parseLiteralExpression().literalToken;
    }

    eat(TokenType.COLON);
    ParseTree value = parseObjectPatternFieldTail(kind);
    return new PropertyNameAssignmentTree(getTreeLocation(start), name, value);
  }

  /**
   * Parses the "tail" of an object pattern field, i.e. the part after the ':'
   */
  private ParseTree parseObjectPatternFieldTail(PatternKind kind) {
    SourcePosition start = getTreeStartLocation();
    ParseTree value;
    if (peekPattern(kind)) {
      value = parsePattern(kind);
    } else {
      value = (kind == PatternKind.ANY)
          ? parseLeftHandSideExpression()
          : parseIdentifierExpression();
      if (!value.isValidAssignmentTarget()) {
        reportError("invalid assignment target");
      }
    }
    if (peek(TokenType.EQUAL)) {
      eat(TokenType.EQUAL);
      ParseTree defaultValue = parseAssignmentExpression();
      return new DefaultParameterTree(getTreeLocation(start), value, defaultValue);
    }
    return value;
  }

  /**
   * Consume a (possibly implicit) semi-colon. Reports an error if a semi-colon is not present.
   */
  private void eatPossibleImplicitSemiColon() {
    if (peek(TokenType.SEMI_COLON) && peekToken().location.start.line == getLastLine()) {
      eat(TokenType.SEMI_COLON);
      return;
    }
    if (peekImplicitSemiColon()) {
      return;
    }

    reportError("Semi-colon expected");
  }

  /**
   * Returns true if an implicit or explicit semi colon is at the current location.
   */
  private boolean peekImplicitSemiColon() {
    return getNextLine() > getLastLine()
        || peek(TokenType.SEMI_COLON)
        || peek(TokenType.CLOSE_CURLY)
        || peek(TokenType.END_OF_FILE);
  }

  /**
   * Returns the line number of the most recently consumed token.
   */
  private int getLastLine() {
    return lastToken.location.end.line;
  }

  /**
   * Returns the line number of the next token.
   */
  private int getNextLine() {
    return peekToken().location.start.line;
  }

  /**
   * Consumes the next token if it is of the expected type. Otherwise returns null.
   * Never reports errors.
   *
   * @param expectedTokenType
   * @return The consumed token, or null if the next token is not of the expected type.
   */
  private Token eatOpt(TokenType expectedTokenType) {
    if (peek(expectedTokenType)) {
      return eat(expectedTokenType);
    }
    return null;
  }

  private boolean inStrictContext() {
    // TODO(johnlenz): track entering strict scripts/modules/functions.
    return config.isStrictMode;
  }

  private boolean peekId() {
    return peekId(0);
  }

  private boolean peekId(int index) {
    TokenType type = peekType(index);
    return type == TokenType.IDENTIFIER ||
        (!inStrictContext() && Keywords.isStrictKeyword(type));
  }

  /**
   * Shorthand for eatOpt(TokenType.IDENTIFIER)
   */
  private IdentifierToken eatIdOpt() {
    return (peekId()) ? eatIdOrKeywordAsId() : null;
  }

  /**
   * Consumes an identifier token that is not a reserved word.
   * @see "http://www.ecma-international.org/ecma-262/5.1/#sec-7.6"
   */
  private IdentifierToken eatId() {
    if (peekId()) {
      return eatIdOrKeywordAsId();
    } else {
      reportExpectedError(peekToken(), TokenType.IDENTIFIER);
      return null;
    }
  }

  private Token eatObjectLiteralPropertyName() {
    Token token = peekToken();
    switch (token.type) {
      case STRING:
      case NUMBER:
        return nextToken();
      case IDENTIFIER:
      default:
        return eatIdOrKeywordAsId();
    }
  }

  /**
   * Consumes an identifier token that may be a reserved word, i.e.
   * an IdentifierName, not necessarily an Identifier.
   * @see "http://www.ecma-international.org/ecma-262/5.1/#sec-7.6"
   */
  private IdentifierToken eatIdOrKeywordAsId() {
    Token token = nextToken();
    if (token.type == TokenType.IDENTIFIER) {
      return (IdentifierToken) token;
    } else if (Keywords.isKeyword(token.type)) {
      return new IdentifierToken(
          token.location, Keywords.get(token.type).toString());
    } else {
      reportExpectedError(token, TokenType.IDENTIFIER);
    }
    return null;
  }

  /**
   * Consumes the next token. If the consumed token is not of the expected type then
   * report an error and return null. Otherwise return the consumed token.
   *
   * @param expectedTokenType
   * @return The consumed token, or null if the next token is not of the expected type.
   */
  private Token eat(TokenType expectedTokenType) {
    Token token = nextToken();
    if (token.type != expectedTokenType) {
      reportExpectedError(token, expectedTokenType);
      return null;
    }
    return token;
  }

  /**
   * Report a 'X' expected error message.
   * @param token The location to report the message at.
   * @param expected The thing that was expected.
   */
  private void reportExpectedError(Token token, Object expected) {
    reportError(token, "'%s' expected", expected);
  }

  /**
   * Returns a SourcePosition for the start of a parse tree that starts at the current location.
   */
  private SourcePosition getTreeStartLocation() {
    return peekToken().location.start;
  }

  /**
   * Returns a SourcePosition for the end of a parse tree that ends at the current location.
   */
  private SourcePosition getTreeEndLocation() {
    return lastToken.location.end;
  }

  /**
   * Returns a SourceRange for a parse tree that starts at {start} and ends at the current
   * location.
   */
  private SourceRange getTreeLocation(SourcePosition start) {
    return new SourceRange(start, getTreeEndLocation());
  }

  /**
   * Consumes the next token and returns it. Will return a never ending stream of
   * TokenType.END_OF_FILE at the end of the file so callers don't have to check for EOF
   * explicitly.
   *
   * <p>Tokenizing is contextual. nextToken() will never return a regular expression literal.
   */
  private Token nextToken() {
    lastToken = scanner.nextToken();
    return lastToken;
  }

  /**
   * Consumes a regular expression literal token and returns it.
   */
  private LiteralToken nextRegularExpressionLiteralToken() {
    LiteralToken lastToken = scanner.nextRegularExpressionLiteralToken();
    this.lastToken = lastToken;
    return lastToken;
  }

  /**
   * Consumes a template literal token and returns it.
   */
  private LiteralToken nextTemplateLiteralToken() {
    LiteralToken lastToken = scanner.nextTemplateLiteralToken();
    this.lastToken = lastToken;
    return lastToken;
  }

  /**
   * Returns true if the next token is of the expected type. Does not consume the token.
   */
  private boolean peek(TokenType expectedType) {
    return peek(0, expectedType);
  }

  /**
   * Returns true if the index-th next token is of the expected type. Does not consume
   * any tokens.
   */
  private boolean peek(int index, TokenType expectedType) {
    return peekType(index) == expectedType;
  }

  /**
   * Returns the TokenType of the next token. Does not consume any tokens.
   */
  private TokenType peekType() {
    return peekType(0);
  }

  /**
   * Returns the TokenType of the index-th next token. Does not consume any tokens.
   */
  private TokenType peekType(int index) {
    return peekToken(index).type;
  }

  /**
   * Returns the next token. Does not consume any tokens.
   */
  private Token peekToken() {
    return peekToken(0);
  }

  /**
   * Returns the index-th next token. Does not consume any tokens.
   */
  private Token peekToken(int index) {
    return scanner.peekToken(index);
  }

  /**
   * Forks the parser at the current point and returns a new
   * parser for speculative parsing.
   */
  private Parser createLookaheadParser() {
    return new Parser(config,
        new LookaheadErrorReporter(),
        this.scanner.getFile(),
        this.scanner.getOffset(),
        inGeneratorContext());
  }

  /**
   * Reports an error message at a given token.
   * @param token The location to report the message at.
   * @param message The message to report in String.format style.
   * @param arguments The arguments to fill in the message format.
   */
  private void reportError(Token token, String message, Object... arguments) {
    if (token == null) {
      reportError(message, arguments);
    } else {
      errorReporter.reportError(token.getStart(), message, arguments);
    }
  }

  /**
   * Reports an error at the current location.
   * @param message The message to report in String.format style.
   * @param arguments The arguments to fill in the message format.
   */
  private void reportError(String message, Object... arguments) {
    errorReporter.reportError(scanner.getPosition(), message, arguments);
  }
}


File: src/com/google/javascript/jscomp/parsing/parser/trees/ParseTree.java
/*
 * Copyright 2011 The Closure Compiler Authors.
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

package com.google.javascript.jscomp.parsing.parser.trees;

import com.google.javascript.jscomp.parsing.parser.util.SourceRange;

/**
 * An abstract syntax tree for JavaScript parse trees.
 * Immutable.
 * A plain old data structure. Should include data members and simple accessors only.
 *
 * Derived classes should have a 'Tree' suffix. Each concrete derived class should have a
 * ParseTreeType whose name matches the derived class name.
 *
 * A parse tree derived from source should have a non-null location. A parse tree that is
 * synthesized by the compiler may have a null location.
 *
 * When adding a new subclass of ParseTree you must also do the following:
 *   - add a new entry to ParseTreeType
 *   - add ParseTree.asXTree()
 */
public class ParseTree {
  public final ParseTreeType type;
  public final SourceRange location;

  protected ParseTree(ParseTreeType type, SourceRange location) {
    this.type = type;
    this.location = location;
  }

  public ArgumentListTree asArgumentList() { return (ArgumentListTree) this; }
  public ArrayLiteralExpressionTree asArrayLiteralExpression() {
    return (ArrayLiteralExpressionTree) this; }
  public ArrayPatternTree asArrayPattern() { return (ArrayPatternTree) this; }
  public AssignmentRestElementTree asAssignmentRestElement() {
    return (AssignmentRestElementTree) this; }
  public BinaryOperatorTree asBinaryOperator() { return (BinaryOperatorTree) this; }
  public BlockTree asBlock() { return (BlockTree) this; }
  public BreakStatementTree asBreakStatement() { return (BreakStatementTree) this; }
  public CallExpressionTree asCallExpression() { return (CallExpressionTree) this; }
  public CaseClauseTree asCaseClause() { return (CaseClauseTree) this; }
  public CatchTree asCatch() { return (CatchTree) this; }
  public ClassDeclarationTree asClassDeclaration() { return (ClassDeclarationTree) this; }
  public CommaExpressionTree asCommaExpression() { return (CommaExpressionTree) this; }
  public ComprehensionIfTree asComprehensionIf() { return (ComprehensionIfTree) this; }
  public ComprehensionForTree asComprehensionFor() { return (ComprehensionForTree) this; }
  public ComprehensionTree asComprehension() { return (ComprehensionTree) this; }
  public ComputedPropertyDefinitionTree asComputedPropertyDefinition() {
    return (ComputedPropertyDefinitionTree) this; }
  public ComputedPropertyGetterTree asComputedPropertyGetter() {
    return (ComputedPropertyGetterTree) this; }
  public ComputedPropertyMethodTree asComputedPropertyMethod() {
    return (ComputedPropertyMethodTree) this; }
  public ComputedPropertyMemberVariableTree asComputedPropertyMemberVariable() {
    return (ComputedPropertyMemberVariableTree) this; }
  public ComputedPropertySetterTree asComputedPropertySetter() {
    return (ComputedPropertySetterTree) this; }
  public ConditionalExpressionTree asConditionalExpression() {
    return (ConditionalExpressionTree) this; }
  public ContinueStatementTree asContinueStatement() { return (ContinueStatementTree) this; }
  public DebuggerStatementTree asDebuggerStatement() { return (DebuggerStatementTree) this; }
  public DefaultClauseTree asDefaultClause() { return (DefaultClauseTree) this; }
  public DefaultParameterTree asDefaultParameter() { return (DefaultParameterTree) this; }
  public DoWhileStatementTree asDoWhileStatement() { return (DoWhileStatementTree) this; }
  public EmptyStatementTree asEmptyStatement() { return (EmptyStatementTree) this; }
  public ExportDeclarationTree asExportDeclaration() { return (ExportDeclarationTree) this; }
  public ExportSpecifierTree asExportSpecifier() { return (ExportSpecifierTree) this; }
  public ExpressionStatementTree asExpressionStatement() { return (ExpressionStatementTree) this; }
  public FinallyTree asFinally() { return (FinallyTree) this; }
  public ForOfStatementTree asForOfStatement() { return (ForOfStatementTree) this; }
  public ForInStatementTree asForInStatement() { return (ForInStatementTree) this; }
  public FormalParameterListTree asFormalParameterList() { return (FormalParameterListTree) this; }
  public ForStatementTree asForStatement() { return (ForStatementTree) this; }
  public FunctionDeclarationTree asFunctionDeclaration() { return (FunctionDeclarationTree) this; }
  public GetAccessorTree asGetAccessor() { return (GetAccessorTree) this; }
  public IdentifierExpressionTree asIdentifierExpression() {
    return (IdentifierExpressionTree) this; }
  public IfStatementTree asIfStatement() { return (IfStatementTree) this; }
  public ImportDeclarationTree asImportDeclaration() { return (ImportDeclarationTree) this; }
  public ImportSpecifierTree asImportSpecifier() { return (ImportSpecifierTree) this; }
  public LabelledStatementTree asLabelledStatement() { return (LabelledStatementTree) this; }
  public LiteralExpressionTree asLiteralExpression() { return (LiteralExpressionTree) this; }
  public MemberExpressionTree asMemberExpression() { return (MemberExpressionTree) this; }
  public MemberLookupExpressionTree asMemberLookupExpression() {
    return (MemberLookupExpressionTree) this; }
  public MemberVariableTree asMemberVariable() { return (MemberVariableTree) this; }
  public MissingPrimaryExpressionTree asMissingPrimaryExpression() {
    return (MissingPrimaryExpressionTree) this; }
  public ModuleImportTree asModuleImport() { return (ModuleImportTree) this; }
  public NewExpressionTree asNewExpression() { return (NewExpressionTree) this; }
  public NullTree asNull() { return (NullTree) this; }
  public ObjectLiteralExpressionTree asObjectLiteralExpression() {
    return (ObjectLiteralExpressionTree) this; }
  public ObjectPatternTree asObjectPattern() { return (ObjectPatternTree) this; }
  public ParenExpressionTree asParenExpression() { return (ParenExpressionTree) this; }
  public PostfixExpressionTree asPostfixExpression() { return (PostfixExpressionTree) this; }
  public ProgramTree asProgram() { return (ProgramTree) this; }
  public PropertyNameAssignmentTree asPropertyNameAssignment() {
    return (PropertyNameAssignmentTree) this; }
  public RestParameterTree asRestParameter() { return (RestParameterTree) this; }
  public ReturnStatementTree asReturnStatement() { return (ReturnStatementTree) this; }
  public SetAccessorTree asSetAccessor() { return (SetAccessorTree) this; }
  public SpreadExpressionTree asSpreadExpression() { return (SpreadExpressionTree) this; }
  public SuperExpressionTree asSuperExpression() { return (SuperExpressionTree) this; }
  public SwitchStatementTree asSwitchStatement() { return (SwitchStatementTree) this; }
  public TemplateLiteralExpressionTree asTemplateLiteralExpression() {
    return (TemplateLiteralExpressionTree) this; }
  public TemplateLiteralPortionTree asTemplateLiteralPortion() {
    return (TemplateLiteralPortionTree) this; }
  public TemplateSubstitutionTree asTemplateSubstitution() {
    return (TemplateSubstitutionTree) this; }
  public ThisExpressionTree asThisExpression() { return (ThisExpressionTree) this; }
  public ThrowStatementTree asThrowStatement() { return (ThrowStatementTree) this; }
  public TryStatementTree asTryStatement() { return (TryStatementTree) this; }
  public TypeNameTree asTypeName() { return (TypeNameTree) this; }
  public TypedParameterTree asTypedParameter() { return (TypedParameterTree) this; }
  public ParameterizedTypeTree asParameterizedType() { return (ParameterizedTypeTree) this; }
  public ArrayTypeTree asArrayType() { return (ArrayTypeTree) this; }
  public UnionTypeTree asUnionType() { return (UnionTypeTree) this; }
  public FunctionTypeTree asFunctionType() { return (FunctionTypeTree) this; }
  public UnaryExpressionTree asUnaryExpression() { return (UnaryExpressionTree) this; }
  public VariableDeclarationListTree asVariableDeclarationList() {
    return (VariableDeclarationListTree) this; }
  public VariableDeclarationTree asVariableDeclaration() {
    return (VariableDeclarationTree) this; }
  public VariableStatementTree asVariableStatement() { return (VariableStatementTree) this; }
  public WhileStatementTree asWhileStatement() { return (WhileStatementTree) this; }
  public WithStatementTree asWithStatement() { return (WithStatementTree) this; }
  public YieldExpressionTree asYieldStatement() { return (YieldExpressionTree) this; }
  public InterfaceDeclarationTree asInterfaceDeclaration() {
    return (InterfaceDeclarationTree) this;
  }
  public EnumDeclarationTree asEnumDeclaration() {
    return (EnumDeclarationTree) this;
  }

  public boolean isPattern() {
    ParseTree parseTree = this;
    while (parseTree.type == ParseTreeType.PAREN_EXPRESSION) {
      parseTree = parseTree.asParenExpression().expression;
    }

    switch (parseTree.type) {
      case ARRAY_PATTERN:
      case OBJECT_PATTERN:
        return true;
      default:
        return false;
    }
  }

  public boolean isValidAssignmentTarget() {
    ParseTree parseTree = this;
    while (parseTree.type == ParseTreeType.PAREN_EXPRESSION) {
      parseTree = parseTree.asParenExpression().expression;
    }

    switch(parseTree.type) {
      case IDENTIFIER_EXPRESSION:
      case MEMBER_EXPRESSION:
      case MEMBER_LOOKUP_EXPRESSION:
      case ARRAY_PATTERN:
      case OBJECT_PATTERN:
      case DEFAULT_PARAMETER:
        return true;
      default:
        return false;
    }
  }

  // TODO: enable classes and traits
  public boolean isAssignmentExpression() {
    switch (this.type) {
    case FUNCTION_DECLARATION:
    case BINARY_OPERATOR:
    case THIS_EXPRESSION:
    case IDENTIFIER_EXPRESSION:
    case LITERAL_EXPRESSION:
    case ARRAY_LITERAL_EXPRESSION:
    case OBJECT_LITERAL_EXPRESSION:
    case MISSING_PRIMARY_EXPRESSION:
    case CONDITIONAL_EXPRESSION:
    case UNARY_EXPRESSION:
    case POSTFIX_EXPRESSION:
    case MEMBER_EXPRESSION:
    case NEW_EXPRESSION:
    case CALL_EXPRESSION:
    case MEMBER_LOOKUP_EXPRESSION:
    case PAREN_EXPRESSION:
    case SUPER_EXPRESSION:
    case TEMPLATE_LITERAL_EXPRESSION:
      return true;
    default:
      return false;
    }
  }

  public boolean isRestParameter() {
    return this.type == ParseTreeType.REST_PARAMETER;
  }

  public boolean isAssignmentRestElement() {
    return this.type == ParseTreeType.ASSIGNMENT_REST_ELEMENT;
  }

  /**
   * This function reflects the ECMA standard, or what we would expect to become the ECMA standard.
   * Most places use isStatement instead which reflects where code on the web diverges from the
   * standard.
   */
  public boolean isStatementStandard() {
    switch (this.type) {
    case BLOCK:
    case VARIABLE_STATEMENT:
    case EMPTY_STATEMENT:
    case EXPRESSION_STATEMENT:
    case IF_STATEMENT:
    case DO_WHILE_STATEMENT:
    case WHILE_STATEMENT:
    case FOR_OF_STATEMENT:
    case FOR_IN_STATEMENT:
    case FOR_STATEMENT:
    case CONTINUE_STATEMENT:
    case BREAK_STATEMENT:
    case RETURN_STATEMENT:
    case YIELD_EXPRESSION:
    case WITH_STATEMENT:
    case SWITCH_STATEMENT:
    case LABELLED_STATEMENT:
    case THROW_STATEMENT:
    case TRY_STATEMENT:
    case DEBUGGER_STATEMENT:
      return true;
    default:
      return false;
    }
  }

  public boolean isSourceElement() {
    return isStatementStandard() || this.type == ParseTreeType.FUNCTION_DECLARATION;
  }

  @Override public String toString() {
    return type + "@" + location;
  }
}


File: src/com/google/javascript/jscomp/parsing/parser/trees/ParseTreeType.java
/*
 * Copyright 2011 The Closure Compiler Authors.
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

package com.google.javascript.jscomp.parsing.parser.trees;

/**
 * The types of concrete parse trees.
 *
 * The name of the ParseTreeType must match the name of the class that it applies to.
 * For example the DerivedTree class should use ParseTreeType.DERIVED.
 */
public enum ParseTreeType {
  PROGRAM,
  FUNCTION_DECLARATION,
  BLOCK,
  VARIABLE_STATEMENT,
  VARIABLE_DECLARATION,
  EMPTY_STATEMENT,
  EXPRESSION_STATEMENT,
  IF_STATEMENT,
  DO_WHILE_STATEMENT,
  WHILE_STATEMENT,
  FOR_IN_STATEMENT,
  FOR_STATEMENT,
  VARIABLE_DECLARATION_LIST,
  CONTINUE_STATEMENT,
  BREAK_STATEMENT,
  RETURN_STATEMENT,
  WITH_STATEMENT,
  CASE_CLAUSE,
  DEFAULT_CLAUSE,
  SWITCH_STATEMENT,
  LABELLED_STATEMENT,
  THROW_STATEMENT,
  CATCH,
  TRY_STATEMENT,
  DEBUGGER_STATEMENT,
  THIS_EXPRESSION,
  IDENTIFIER_EXPRESSION,
  LITERAL_EXPRESSION,
  ARRAY_LITERAL_EXPRESSION,
  OBJECT_LITERAL_EXPRESSION,
  COMPREHENSION,
  COMPREHENSION_IF,
  COMPREHENSION_FOR,
  GET_ACCESSOR,
  SET_ACCESSOR,
  PROPERTY_NAME_ASSIGNMENT,
  COMPUTED_PROPERTY_DEFINITION,
  COMPUTED_PROPERTY_GETTER,
  COMPUTED_PROPERTY_METHOD,
  COMPUTED_PROPERTY_SETTER,
  MISSING_PRIMARY_EXPRESSION,
  COMMA_EXPRESSION,
  BINARY_OPERATOR,
  CONDITIONAL_EXPRESSION,
  UNARY_EXPRESSION,
  POSTFIX_EXPRESSION,
  MEMBER_EXPRESSION,
  NEW_EXPRESSION,
  ARGUMENT_LIST,
  CALL_EXPRESSION,
  CLASS_DECLARATION,
  INTERFACE_DECLARATION,
  ENUM_DECLARATION,
  MEMBER_LOOKUP_EXPRESSION,
  PAREN_EXPRESSION,
  FINALLY,
  SUPER_EXPRESSION,
  ARRAY_PATTERN,
  ASSIGNMENT_REST_ELEMENT,
  OBJECT_PATTERN,
  FORMAL_PARAMETER_LIST,
  SPREAD_EXPRESSION,
  NULL,
  REST_PARAMETER,
  MODULE_IMPORT,
  EXPORT_DECLARATION,
  EXPORT_SPECIFIER,
  IMPORT_DECLARATION,
  IMPORT_SPECIFIER,
  FOR_OF_STATEMENT,
  YIELD_EXPRESSION,
  DEFAULT_PARAMETER,
  TEMPLATE_LITERAL_EXPRESSION,
  TEMPLATE_LITERAL_PORTION,
  TEMPLATE_SUBSTITUTION,
  TYPE_NAME,
  TYPE_ANNOTATION,
  PARAMETERIZED_TYPE_TREE,
  ARRAY_TYPE,
  UNION_TYPE,
  FUNCTION_TYPE,
  MEMBER_VARIABLE,
  COMPUTED_PROPERTY_MEMBER_VARIABLE,
}


File: src/com/google/javascript/jscomp/parsing/parser/trees/TypedParameterTree.java
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

package com.google.javascript.jscomp.parsing.parser.trees;

import com.google.javascript.jscomp.parsing.parser.util.SourceRange;

/**
 * A parameter with a type specified.
 */
public class TypedParameterTree extends ParseTree {

  public final ParseTree param;
  public final ParseTree typeAnnotation;

  public TypedParameterTree(SourceRange location, ParseTree param, ParseTree typeAnnotation) {
    super(ParseTreeType.TYPE_ANNOTATION, location);
    this.param = param;
    this.typeAnnotation = typeAnnotation;
  }
}


File: src/com/google/javascript/rhino/Node.java
/*
 *
 * ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Rhino code, released
 * May 6, 1999.
 *
 * The Initial Developer of the Original Code is
 * Netscape Communications Corporation.
 * Portions created by the Initial Developer are Copyright (C) 1997-1999
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Norris Boyd
 *   Roger Lawrence
 *   Mike McCabe
 *
 * Alternatively, the contents of this file may be used under the terms of
 * the GNU General Public License Version 2 or later (the "GPL"), in which
 * case the provisions of the GPL are applicable instead of those above. If
 * you wish to allow use of your version of this file only under the terms of
 * the GPL and not to allow others to use your version of this file under the
 * MPL, indicate your decision by deleting the provisions above and replacing
 * them with the notice and other provisions required by the GPL. If you do
 * not delete the provisions above, a recipient may use your version of this
 * file under either the MPL or the GPL.
 *
 * ***** END LICENSE BLOCK ***** */

package com.google.javascript.rhino;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Objects;
import com.google.common.base.Preconditions;
import com.google.javascript.rhino.jstype.JSType;

import java.io.IOException;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.NoSuchElementException;
import java.util.Set;

/**
 * This class implements the root of the intermediate representation.
 *
 */

public class Node implements Cloneable, Serializable {

  private static final long serialVersionUID = 1L;

  public static final int
      JSDOC_INFO_PROP   = 29,     // contains a TokenStream.JSDocInfo object
      VAR_ARGS_NAME     = 30,     // the name node is a variable length
                                  // argument placeholder.
      INCRDECR_PROP      = 32,    // pre or post type of increment/decrement
      QUOTED_PROP        = 36,    // set to indicate a quoted object lit key
      OPT_ARG_NAME       = 37,    // The name node is an optional argument.
      SYNTHETIC_BLOCK_PROP = 38,  // A synthetic block. Used to make
                                  // processing simpler, and does not
                                  // represent a real block in the source.
      ADDED_BLOCK        = 39,    // Used to indicate BLOCK that is added
      ORIGINALNAME_PROP  = 40,    // The original name of the node, before
                                  // renaming.
      SIDE_EFFECT_FLAGS  = 42,    // Function or constructor call side effect
                                  // flags
      // Coding convention props
      IS_CONSTANT_NAME   = 43,    // The variable or property is constant.
      IS_NAMESPACE       = 46,    // The variable creates a namespace.
      DIRECTIVES         = 48,    // The ES5 directives on this node.
      DIRECT_EVAL        = 49,    // ES5 distinguishes between direct and
                                  // indirect calls to eval.
      FREE_CALL          = 50,    // A CALL without an explicit "this" value.
      STATIC_SOURCE_FILE = 51,    // A StaticSourceFile indicating the file
                                  // where this node lives.
      LENGTH             = 52,    // The length of the code represented by
                                  // this node.
      INPUT_ID           = 53,    // The id of the input associated with this
                                  // node.
      SLASH_V            = 54,    // Whether a STRING node contains a \v
                                  // vertical tab escape. This is a total hack.
                                  // See comments in IRFactory about this.
      INFERRED_FUNCTION  = 55,    // Marks a function whose parameter types
                                  // have been inferred.
      CHANGE_TIME        = 56,    // For passes that work only on changed funs.
      REFLECTED_OBJECT   = 57,    // An object that's used for goog.object.reflect-style reflection.
      STATIC_MEMBER      = 58,    // Set if class member definition is static
      GENERATOR_FN       = 59,    // Set if the node is a Generator function or
                                  // member method.
      ARROW_FN           = 60,
      YIELD_FOR          = 61,    // Set if a yield is a "yield all"
      EXPORT_DEFAULT     = 62,    // Set if a export is a "default" export
      EXPORT_ALL_FROM    = 63,    // Set if an export is a "*"
      IS_CONSTANT_VAR    = 64,    // A lexical variable is inferred const
      GENERATOR_MARKER   = 65,    // Used by the ES6-to-ES3 translator.
      GENERATOR_SAFE     = 66,    // Used by the ES6-to-ES3 translator.

      COOKED_STRING      = 70,    // Used to support ES6 tagged template literal.
      RAW_STRING_VALUE   = 71,    // Used to support ES6 tagged template literal.
      COMPUTED_PROP_METHOD = 72,  // A computed property that has the method
                                  // syntax ( [prop]() {...} ) rather than the
                                  // property definition syntax ( [prop]: value ).
      COMPUTED_PROP_GETTER = 73,  // A computed property in a getter, e.g.
                                  // var obj = { get [prop]() {...} };
      COMPUTED_PROP_SETTER = 74,  // A computed property in a setter, e.g.
                                  // var obj = { set [prop](val) {...} };
      COMPUTED_PROP_VARIABLE = 75, // A computed property that's a variable, e.g. [prop]: string;
      ANALYZED_DURING_GTI  = 76,  // In GlobalTypeInfo, we mark some AST nodes
                                  // to avoid analyzing them during
                                  // NewTypeInference. We remove this attribute
                                  // in the fwd direction of NewTypeInference.
      CONSTANT_PROPERTY_DEF = 77, // Used to communicate information between
                                  // GlobalTypeInfo and NewTypeInference.
                                  // We use this to tag getprop nodes that
                                  // declare properties.
      DECLARED_TYPE_EXPR = 78,    // Used to attach TypeDeclarationNode ASTs to
                                  // Nodes which represent a typed NAME or
                                  // FUNCTION.
                                  //
      TYPE_BEFORE_CAST = 79;      // The type of an expression before the cast.
                                  // This will be present only if the expression is casted.


  public static final int   // flags for INCRDECR_PROP
      DECR_FLAG = 0x1,
      POST_FLAG = 0x2;

  private static final String propToString(int propType) {
      switch (propType) {
        case VAR_ARGS_NAME:      return "var_args_name";

        case JSDOC_INFO_PROP:    return "jsdoc_info";

        case INCRDECR_PROP:      return "incrdecr";
        case QUOTED_PROP:        return "quoted";
        case OPT_ARG_NAME:       return "opt_arg";

        case SYNTHETIC_BLOCK_PROP: return "synthetic";
        case ADDED_BLOCK:        return "added_block";
        case ORIGINALNAME_PROP:  return "originalname";
        case SIDE_EFFECT_FLAGS:  return "side_effect_flags";

        case IS_CONSTANT_NAME:   return "is_constant_name";
        case IS_NAMESPACE:       return "is_namespace";
        case DIRECTIVES:         return "directives";
        case DIRECT_EVAL:        return "direct_eval";
        case FREE_CALL:          return "free_call";
        case STATIC_SOURCE_FILE: return "source_file";
        case INPUT_ID:           return "input_id";
        case LENGTH:             return "length";
        case SLASH_V:            return "slash_v";
        case INFERRED_FUNCTION:  return "inferred";
        case CHANGE_TIME:        return "change_time";
        case REFLECTED_OBJECT:   return "reflected_object";
        case STATIC_MEMBER:      return "static_member";
        case GENERATOR_FN:       return "generator_fn";
        case ARROW_FN:           return "arrow_fn";
        case YIELD_FOR:          return "yield_for";
        case EXPORT_DEFAULT:     return "export_default";
        case EXPORT_ALL_FROM:    return "export_all_from";
        case IS_CONSTANT_VAR:    return "is_constant_var";
        case GENERATOR_MARKER:   return "is_generator_marker";
        case GENERATOR_SAFE:     return "is_generator_safe";
        case COOKED_STRING:      return "cooked_string";
        case RAW_STRING_VALUE:   return "raw_string_value";
        case COMPUTED_PROP_METHOD: return "computed_prop_method";
        case COMPUTED_PROP_GETTER: return "computed_prop_getter";
        case COMPUTED_PROP_SETTER: return "computed_prop_setter";
        case COMPUTED_PROP_VARIABLE: return "computed_prop_variable";
        case ANALYZED_DURING_GTI:  return "analyzed_during_gti";
        case CONSTANT_PROPERTY_DEF: return "constant_property_def";
        case DECLARED_TYPE_EXPR: return "declared_type_expr";
        case TYPE_BEFORE_CAST: return "type_before_cast";
        default:
          throw new IllegalStateException("unexpected prop id " + propType);
      }
  }

  /**
   * Represents a node in the type declaration AST.
   */
  public static class TypeDeclarationNode extends Node {

    private static final long serialVersionUID = 1L;

    public TypeDeclarationNode(int nodeType) {
      super(nodeType);
    }

    public TypeDeclarationNode(int nodeType, Node child) {
      super(nodeType, child);
    }

    public TypeDeclarationNode(int nodeType, Node left, Node right) {
      super(nodeType, left, right);
    }

    public TypeDeclarationNode(int nodeType, Node left, Node mid, Node right) {
      super(nodeType, left, mid, right);
    }
  }

  private static class NumberNode extends Node {

    private static final long serialVersionUID = 1L;

    NumberNode(double number) {
      super(Token.NUMBER);
      this.number = number;
    }

    public NumberNode(double number, int lineno, int charno) {
      super(Token.NUMBER, lineno, charno);
      this.number = number;
    }

    @Override
    public double getDouble() {
      return this.number;
    }

    @Override
    public void setDouble(double d) {
      this.number = d;
    }

    @Override
    boolean isEquivalentTo(
        Node node, boolean compareType, boolean recur, boolean jsDoc) {
      boolean equiv = super.isEquivalentTo(node, compareType, recur, jsDoc);
      if (equiv) {
        double thisValue = getDouble();
        double thatValue = ((NumberNode) node).getDouble();
        if (thisValue == thatValue) {
          // detect the difference between 0.0 and -0.0.
          return (thisValue != 0.0) || (1 / thisValue == 1 / thatValue);
        }
      }
      return false;
    }

    private double number;
  }

  private static class StringNode extends Node {

    private static final long serialVersionUID = 1L;

    StringNode(int type, String str) {
      super(type);
      if (null == str) {
        throw new IllegalArgumentException("StringNode: str is null");
      }
      this.str = str;
    }

    StringNode(int type, String str, int lineno, int charno) {
      super(type, lineno, charno);
      if (null == str) {
        throw new IllegalArgumentException("StringNode: str is null");
      }
      this.str = str;
    }

    /**
     * returns the string content.
     * @return non null.
     */
    @Override
    public String getString() {
      return this.str;
    }

    /**
     * sets the string content.
     * @param str the new value.  Non null.
     */
    @Override
    public void setString(String str) {
      if (null == str) {
        throw new IllegalArgumentException("StringNode: str is null");
      }
      this.str = str;
    }

    @Override
    boolean isEquivalentTo(
        Node node, boolean compareType, boolean recur, boolean jsDoc) {
      return (super.isEquivalentTo(node, compareType, recur, jsDoc)
          && this.str.equals(((StringNode) node).str));
    }

    /**
     * If the property is not defined, this was not a quoted key.  The
     * QUOTED_PROP int property is only assigned to STRING tokens used as
     * object lit keys.
     * @return true if this was a quoted string key in an object literal.
     */
    @Override
    public boolean isQuotedString() {
      return getBooleanProp(QUOTED_PROP);
    }

    /**
     * This should only be called for STRING nodes created in object lits.
     */
    @Override
    public void setQuotedString() {
      putBooleanProp(QUOTED_PROP, true);
    }

    private String str;
  }

  // PropListItems must be immutable so that they can be shared.
  private interface PropListItem {
    int getType();
    PropListItem getNext();
    PropListItem chain(PropListItem next);
    Object getObjectValue();
    int getIntValue();
  }

  private abstract static class AbstractPropListItem
      implements PropListItem, Serializable {
    private static final long serialVersionUID = 1L;

    private final PropListItem next;
    private final int propType;

    AbstractPropListItem(int propType, PropListItem next) {
      this.propType = propType;
      this.next = next;
    }

    @Override
    public int getType() {
      return propType;
    }

    @Override
    public PropListItem getNext() {
      return next;
    }

    @Override
    public abstract PropListItem chain(PropListItem next);
  }

  // A base class for Object storing props
  private static class ObjectPropListItem
      extends AbstractPropListItem {
    private static final long serialVersionUID = 1L;

    private final Object objectValue;

    ObjectPropListItem(int propType, Object objectValue, PropListItem next) {
      super(propType, next);
      this.objectValue = objectValue;
    }

    @Override
    public int getIntValue() {
      throw new UnsupportedOperationException();
    }

    @Override
    public Object getObjectValue() {
      return objectValue;
    }

    @Override
    public String toString() {
      return String.valueOf(objectValue);
    }

    @Override
    public PropListItem chain(PropListItem next) {
      return new ObjectPropListItem(getType(), objectValue, next);
    }
  }

  // A base class for int storing props
  private static class IntPropListItem extends AbstractPropListItem {
    private static final long serialVersionUID = 1L;

    final int intValue;

    IntPropListItem(int propType, int intValue, PropListItem next) {
      super(propType, next);
      this.intValue = intValue;
    }

    @Override
    public int getIntValue() {
      return intValue;
    }

    @Override
    public Object getObjectValue() {
      throw new UnsupportedOperationException();
    }

    @Override
    public String toString() {
      return String.valueOf(intValue);
    }

    @Override
    public PropListItem chain(PropListItem next) {
      return new IntPropListItem(getType(), intValue, next);
    }
  }

  public Node(int nodeType) {
    type = nodeType;
    parent = null;
    sourcePosition = -1;
  }

  public Node(int nodeType, Node child) {
    Preconditions.checkArgument(child.parent == null,
        "new child has existing parent");
    Preconditions.checkArgument(child.next == null,
        "new child has existing sibling");

    type = nodeType;
    parent = null;
    first = last = child;
    child.next = null;
    child.parent = this;
    sourcePosition = -1;
  }

  public Node(int nodeType, Node left, Node right) {
    Preconditions.checkArgument(left.parent == null,
        "first new child has existing parent");
    Preconditions.checkArgument(left.next == null,
        "first new child has existing sibling");
    Preconditions.checkArgument(right.parent == null,
        "second new child has existing parent");
    Preconditions.checkArgument(right.next == null,
        "second new child has existing sibling");
    type = nodeType;
    parent = null;
    first = left;
    last = right;
    left.next = right;
    left.parent = this;
    right.next = null;
    right.parent = this;
    sourcePosition = -1;
  }

  public Node(int nodeType, Node left, Node mid, Node right) {
    Preconditions.checkArgument(left.parent == null);
    Preconditions.checkArgument(left.next == null);
    Preconditions.checkArgument(mid.parent == null);
    Preconditions.checkArgument(mid.next == null);
    Preconditions.checkArgument(right.parent == null);
    Preconditions.checkArgument(right.next == null);
    type = nodeType;
    parent = null;
    first = left;
    last = right;
    left.next = mid;
    left.parent = this;
    mid.next = right;
    mid.parent = this;
    right.next = null;
    right.parent = this;
    sourcePosition = -1;
  }

  public Node(int nodeType, Node left, Node mid, Node mid2, Node right) {
    Preconditions.checkArgument(left.parent == null);
    Preconditions.checkArgument(left.next == null);
    Preconditions.checkArgument(mid.parent == null);
    Preconditions.checkArgument(mid.next == null);
    Preconditions.checkArgument(mid2.parent == null);
    Preconditions.checkArgument(mid2.next == null);
    Preconditions.checkArgument(right.parent == null);
    Preconditions.checkArgument(right.next == null);
    type = nodeType;
    parent = null;
    first = left;
    last = right;
    left.next = mid;
    left.parent = this;
    mid.next = mid2;
    mid.parent = this;
    mid2.next = right;
    mid2.parent = this;
    right.next = null;
    right.parent = this;
    sourcePosition = -1;
  }

  public Node(int nodeType, int lineno, int charno) {
    type = nodeType;
    parent = null;
    sourcePosition = mergeLineCharNo(lineno, charno);
  }

  public Node(int nodeType, Node child, int lineno, int charno) {
    this(nodeType, child);
    sourcePosition = mergeLineCharNo(lineno, charno);
  }

  public Node(int nodeType, Node left, Node right, int lineno, int charno) {
    this(nodeType, left, right);
    sourcePosition = mergeLineCharNo(lineno, charno);
  }

  public Node(int nodeType, Node left, Node mid, Node right,
      int lineno, int charno) {
    this(nodeType, left, mid, right);
    sourcePosition = mergeLineCharNo(lineno, charno);
  }

  public Node(int nodeType, Node left, Node mid, Node mid2, Node right,
      int lineno, int charno) {
    this(nodeType, left, mid, mid2, right);
    sourcePosition = mergeLineCharNo(lineno, charno);
  }

  public Node(int nodeType, Node[] children, int lineno, int charno) {
    this(nodeType, children);
    sourcePosition = mergeLineCharNo(lineno, charno);
  }

  public Node(int nodeType, Node[] children) {
    this.type = nodeType;
    parent = null;
    if (children.length != 0) {
      this.first = children[0];
      this.last = children[children.length - 1];

      for (int i = 1; i < children.length; i++) {
        if (null != children[i - 1].next) {
          // fail early on loops. implies same node in array twice
          throw new IllegalArgumentException("duplicate child");
        }
        children[i - 1].next = children[i];
        Preconditions.checkArgument(children[i - 1].parent == null);
        children[i - 1].parent = this;
      }
      Preconditions.checkArgument(children[children.length - 1].parent == null);
      children[children.length - 1].parent = this;

      if (null != this.last.next) {
        // fail early on loops. implies same node in array twice
        throw new IllegalArgumentException("duplicate child");
      }
    }
  }

  public static Node newNumber(double number) {
    return new NumberNode(number);
  }

  public static Node newNumber(double number, int lineno, int charno) {
    return new NumberNode(number, lineno, charno);
  }

  public static Node newString(String str) {
    return new StringNode(Token.STRING, str);
  }

  public static Node newString(int type, String str) {
    return new StringNode(type, str);
  }

  public static Node newString(String str, int lineno, int charno) {
    return new StringNode(Token.STRING, str, lineno, charno);
  }

  public static Node newString(int type, String str, int lineno, int charno) {
    return new StringNode(type, str, lineno, charno);
  }

  public int getType() {
    return type;
  }

  public void setType(int type) {
    this.type = type;
  }

  public boolean hasChildren() {
    return first != null;
  }

  public Node getFirstChild() {
    return first;
  }

  public Node getLastChild() {
    return last;
  }

  public Node getNext() {
    return next;
  }

  public Node getChildBefore(Node child) {
    if (child == first) {
      return null;
    }
    Node n = first;
    if (n == null) {
      throw new RuntimeException("node is not a child");
    }

    while (n.next != child) {
      n = n.next;
      if (n == null) {
        throw new RuntimeException("node is not a child");
      }
    }
    return n;
  }

  public Node getChildAtIndex(int i) {
    Node n = first;
    while (i > 0) {
      n = n.next;
      i--;
    }
    return n;
  }

  public int getIndexOfChild(Node child) {
    Node n = first;
    int i = 0;
    while (n != null) {
      if (child == n) {
        return i;
      }

      n = n.next;
      i++;
    }
    return -1;
  }

  public Node getLastSibling() {
    Node n = this;
    while (n.next != null) {
      n = n.next;
    }
    return n;
  }

  public void addChildToFront(Node child) {
    Preconditions.checkArgument(child.parent == null);
    Preconditions.checkArgument(child.next == null);
    child.parent = this;
    child.next = first;
    first = child;
    if (last == null) {
      last = child;
    }
  }

  public void addChildToBack(Node child) {
    Preconditions.checkArgument(child.parent == null);
    Preconditions.checkArgument(child.next == null);
    child.parent = this;
    child.next = null;
    if (last == null) {
      first = last = child;
      return;
    }
    last.next = child;
    last = child;
  }

  public void addChildrenToFront(Node children) {
    for (Node child = children; child != null; child = child.next) {
      Preconditions.checkArgument(child.parent == null);
      child.parent = this;
    }
    Node lastSib = children.getLastSibling();
    lastSib.next = first;
    first = children;
    if (last == null) {
      last = lastSib;
    }
  }

  public void addChildrenToBack(Node children) {
    addChildrenAfter(children, getLastChild());
  }

  /**
   * Add 'child' before 'node'.
   */
  public void addChildBefore(Node newChild, Node node) {
    Preconditions.checkArgument(node != null && node.parent == this,
        "The existing child node of the parent should not be null.");
    Preconditions.checkArgument(newChild.next == null,
        "The new child node has siblings.");
    Preconditions.checkArgument(newChild.parent == null,
        "The new child node already has a parent.");
    if (first == node) {
      newChild.parent = this;
      newChild.next = first;
      first = newChild;
      return;
    }
    Node prev = getChildBefore(node);
    addChildAfter(newChild, prev);
  }

  /**
   * Add 'child' after 'node'.
   */
  public void addChildAfter(Node newChild, Node node) {
    Preconditions.checkArgument(newChild.next == null,
        "The new child node has siblings.");
    addChildrenAfter(newChild, node);
  }

  /**
   * Add all children after 'node'.
   */
  public void addChildrenAfter(Node children, Node node) {
    Preconditions.checkArgument(node == null || node.parent == this);
    for (Node child = children; child != null; child = child.next) {
      Preconditions.checkArgument(child.parent == null);
      child.parent = this;
    }

    Node lastSibling = children.getLastSibling();
    if (node != null) {
      Node oldNext = node.next;
      node.next = children;
      lastSibling.next = oldNext;
      if (node == last) {
        last = lastSibling;
      }
    } else {
      // Append to the beginning.
      if (first != null) {
        lastSibling.next = first;
      } else {
        last = lastSibling;
      }
      first = children;
    }
  }

  /**
   * Detach a child from its parent and siblings.
   */
  public void removeChild(Node child) {
    Node prev = getChildBefore(child);
    if (prev == null) {
      first = first.next;
    } else {
      prev.next = child.next;
    }
    if (child == last) {
      last = prev;
    }
    child.next = null;
    child.parent = null;
  }

  /**
   * Detaches child from Node and replaces it with newChild.
   */
  public void replaceChild(Node child, Node newChild) {
    Preconditions.checkArgument(newChild.next == null,
        "The new child node has siblings.");
    Preconditions.checkArgument(newChild.parent == null,
        "The new child node already has a parent.");

    // Copy over important information.
    newChild.copyInformationFrom(child);

    newChild.next = child.next;
    newChild.parent = this;
    if (child == first) {
      first = newChild;
    } else {
      Node prev = getChildBefore(child);
      prev.next = newChild;
    }
    if (child == last) {
      last = newChild;
    }
    child.next = null;
    child.parent = null;
  }

  public void replaceChildAfter(Node prevChild, Node newChild) {
    Preconditions.checkArgument(prevChild.parent == this,
        "prev is not a child of this node.");

    Preconditions.checkArgument(newChild.next == null,
        "The new child node has siblings.");
    Preconditions.checkArgument(newChild.parent == null,
        "The new child node already has a parent.");

    // Copy over important information.
    newChild.copyInformationFrom(prevChild);

    Node child = prevChild.next;
    newChild.next = child.next;
    newChild.parent = this;
    prevChild.next = newChild;
    if (child == last) {
      last = newChild;
    }
    child.next = null;
    child.parent = null;
  }

  @VisibleForTesting
  PropListItem lookupProperty(int propType) {
    PropListItem x = propListHead;
    while (x != null && propType != x.getType()) {
      x = x.getNext();
    }
    return x;
  }

  /**
   * Clone the properties from the provided node without copying
   * the property object.  The receiving node may not have any
   * existing properties.
   * @param other The node to clone properties from.
   * @return this node.
   */
  public Node clonePropsFrom(Node other) {
    Preconditions.checkState(this.propListHead == null,
        "Node has existing properties.");
    this.propListHead = other.propListHead;
    return this;
  }

  public void removeProp(int propType) {
    PropListItem result = removeProp(propListHead, propType);
    if (result != propListHead) {
      propListHead = result;
    }
  }

  /**
   * @param item The item to inspect
   * @param propType The property to look for
   * @return The replacement list if the property was removed, or
   *   'item' otherwise.
   */
  private PropListItem removeProp(PropListItem item, int propType) {
    if (item == null) {
      return null;
    } else if (item.getType() == propType) {
      return item.getNext();
    } else {
      PropListItem result = removeProp(item.getNext(), propType);
      if (result != item.getNext()) {
        return item.chain(result);
      } else {
        return item;
      }
    }
  }

  public Object getProp(int propType) {
    PropListItem item = lookupProperty(propType);
    if (item == null) {
      return null;
    }
    return item.getObjectValue();
  }

  public boolean getBooleanProp(int propType) {
    return getIntProp(propType) != 0;
  }

  /**
   * Returns the integer value for the property, or 0 if the property
   * is not defined.
   */
  public int getIntProp(int propType) {
    PropListItem item = lookupProperty(propType);
    if (item == null) {
      return 0;
    }
    return item.getIntValue();
  }

  public int getExistingIntProp(int propType) {
    PropListItem item = lookupProperty(propType);
    if (item == null) {
      throw new IllegalStateException("missing prop: " + propType);
    }
    return item.getIntValue();
  }

  public void putProp(int propType, Object value) {
    removeProp(propType);
    if (value != null) {
      propListHead = createProp(propType, value, propListHead);
    }
  }

  public void putBooleanProp(int propType, boolean value) {
    putIntProp(propType, value ? 1 : 0);
  }

  public void putIntProp(int propType, int value) {
    removeProp(propType);
    if (value != 0) {
      propListHead = createProp(propType, value, propListHead);
    }
  }

  /**
   * TODO(alexeagle): this should take a TypeDeclarationNode
   * @param typeExpression
   */
  public void setDeclaredTypeExpression(Node typeExpression) {
    putProp(DECLARED_TYPE_EXPR, typeExpression);
  }

  /**
   * Returns the syntactical type specified on this node. Not to be confused
   * with {@link #getJSType()} which returns the compiler-inferred type.
   */
  public TypeDeclarationNode getDeclaredTypeExpression() {
    return (TypeDeclarationNode) getProp(DECLARED_TYPE_EXPR);
  }

  PropListItem createProp(int propType, Object value, PropListItem next) {
    return new ObjectPropListItem(propType, value, next);
  }

  PropListItem createProp(int propType, int value, PropListItem next) {
    return new IntPropListItem(propType, value, next);
  }

  /**
   * Returns the type of this node before casting. This annotation will only exist on the first
   * child of a CAST node after type checking.
   */
  public JSType getJSTypeBeforeCast() {
    return (JSType) getProp(TYPE_BEFORE_CAST);
  }

  // Gets all the property types, in sorted order.
  private int[] getSortedPropTypes() {
    int count = 0;
    for (PropListItem x = propListHead; x != null; x = x.getNext()) {
      count++;
    }

    int[] keys = new int[count];
    for (PropListItem x = propListHead; x != null; x = x.getNext()) {
      count--;
      keys[count] = x.getType();
    }

    Arrays.sort(keys);
    return keys;
  }

  /** Can only be called when <tt>getType() == TokenStream.NUMBER</tt> */
  public double getDouble() throws UnsupportedOperationException {
    if (this.getType() == Token.NUMBER) {
      throw new IllegalStateException(
          "Number node not created with Node.newNumber");
    } else {
      throw new UnsupportedOperationException(this + " is not a number node");
    }
  }

  /**
   * Can only be called when <tt>getType() == Token.NUMBER</tt>
   * @param value value to set.
   */
  public void setDouble(double value) throws UnsupportedOperationException {
    if (this.getType() == Token.NUMBER) {
      throw new IllegalStateException(
          "Number node not created with Node.newNumber");
    } else {
      throw new UnsupportedOperationException(this + " is not a string node");
    }
  }

  /** Can only be called when node has String context. */
  public String getString() throws UnsupportedOperationException {
    if (this.getType() == Token.STRING) {
      throw new IllegalStateException(
          "String node not created with Node.newString");
    } else {
      throw new UnsupportedOperationException(this + " is not a string node");
    }
  }

  /**
   * Can only be called for a Token.STRING or Token.NAME.
   * @param value the value to set.
   */
  public void setString(String value) throws UnsupportedOperationException {
    if (this.getType() == Token.STRING || this.getType() == Token.NAME) {
      throw new IllegalStateException(
          "String node not created with Node.newString");
    } else {
      throw new UnsupportedOperationException(this + " is not a string node");
    }
  }

  @Override
  public String toString() {
    return toString(true, true, true);
  }

  public String toString(
      boolean printSource,
      boolean printAnnotations,
      boolean printType) {
    StringBuilder sb = new StringBuilder();
    toString(sb, printSource, printAnnotations, printType);
    return sb.toString();
  }

  private void toString(
      StringBuilder sb,
      boolean printSource,
      boolean printAnnotations,
      boolean printType) {
    sb.append(Token.name(type));
    if (this instanceof StringNode) {
      sb.append(' ');
      sb.append(getString());
    } else if (type == Token.FUNCTION) {
      sb.append(' ');
      // In the case of JsDoc trees, the first child is often not a string
      // which causes exceptions to be thrown when calling toString or
      // toStringTree.
      if (first == null || first.getType() != Token.NAME) {
        sb.append("<invalid>");
      } else {
        sb.append(first.getString());
      }
    } else if (type == Token.NUMBER) {
      sb.append(' ');
      sb.append(getDouble());
    }
    if (printSource) {
      int lineno = getLineno();
      if (lineno != -1) {
        sb.append(' ');
        sb.append(lineno);
      }
    }

    if (printAnnotations) {
      int[] keys = getSortedPropTypes();
      for (int i = 0; i < keys.length; i++) {
        int type = keys[i];
        PropListItem x = lookupProperty(type);
        sb.append(" [");
        sb.append(propToString(type));
        sb.append(": ");
        String value;
        switch (type) {
          default:
            value = x.toString();
            break;
        }
        sb.append(value);
        sb.append(']');
      }
    }

    if (printType) {
      if (typei != null) {
        String typeString = typei.toString();
        if (typeString != null) {
          sb.append(" : ");
          sb.append(typeString);
        }
      }
    }
  }


  public String toStringTree() {
    return toStringTreeImpl();
  }

  private String toStringTreeImpl() {
    try {
      StringBuilder s = new StringBuilder();
      appendStringTree(s);
      return s.toString();
    } catch (IOException e) {
      throw new RuntimeException("Should not happen\n" + e);
    }
  }

  public void appendStringTree(Appendable appendable) throws IOException {
    toStringTreeHelper(this, 0, appendable);
  }

  private static void toStringTreeHelper(Node n, int level, Appendable sb)
      throws IOException {
    for (int i = 0; i != level; ++i) {
      sb.append("    ");
    }
    sb.append(n.toString());
    sb.append('\n');
    for (Node cursor = n.getFirstChild();
         cursor != null;
         cursor = cursor.getNext()) {
      toStringTreeHelper(cursor, level + 1, sb);
    }
  }

  int type;              // type of the node; Token.NAME for example
  Node next;             // next sibling
  private Node first;    // first element of a linked list of children
  private Node last;     // last element of a linked list of children

  /**
   * Linked list of properties. Since vast majority of nodes would have
   * no more then 2 properties, linked list saves memory and provides
   * fast lookup. If this does not holds, propListHead can be replaced
   * by UintMap.
   */
  private PropListItem propListHead;

  /**
   * COLUMN_BITS represents how many of the lower-order bits of
   * sourcePosition are reserved for storing the column number.
   * Bits above these store the line number.
   * This gives us decent position information for everything except
   * files already passed through a minimizer, where lines might
   * be longer than 4096 characters.
   */
  public static final int COLUMN_BITS = 12;

  /**
   * MAX_COLUMN_NUMBER represents the maximum column number that can
   * be represented.  JSCompiler's modifications to Rhino cause all
   * tokens located beyond the maximum column to MAX_COLUMN_NUMBER.
   */
  public static final int MAX_COLUMN_NUMBER = (1 << COLUMN_BITS) - 1;

  /**
   * COLUMN_MASK stores a value where bits storing the column number
   * are set, and bits storing the line are not set.  It's handy for
   * separating column number from line number.
   */
  public static final int COLUMN_MASK = MAX_COLUMN_NUMBER;

  /**
   * Source position of this node. The position is encoded with the
   * column number in the low 12 bits of the integer, and the line
   * number in the rest.  Create some handy constants so we can change this
   * size if we want.
   */
  private int sourcePosition;

  private TypeI typei;

  private Node parent;

  //==========================================================================
  // Source position management

  public void setStaticSourceFile(StaticSourceFile file) {
    this.putProp(STATIC_SOURCE_FILE, file);
  }

  /** Sets the source file to a non-extern file of the given name. */
  public void setSourceFileForTesting(String name) {
    this.putProp(STATIC_SOURCE_FILE, new SimpleSourceFile(name, false));
  }

  public String getSourceFileName() {
    StaticSourceFile file = getStaticSourceFile();
    return file == null ? null : file.getName();
  }

  /** Returns the source file associated with this input. May be null */
  public StaticSourceFile getStaticSourceFile() {
    return ((StaticSourceFile) this.getProp(STATIC_SOURCE_FILE));
  }

  /**
   * @param inputId
   */
  public void setInputId(InputId inputId) {
    this.putProp(INPUT_ID, inputId);
  }

  /**
   * @return The Id of the CompilerInput associated with this Node.
   */
  public InputId getInputId() {
    return ((InputId) this.getProp(INPUT_ID));
  }

  public boolean isFromExterns() {
    StaticSourceFile file = getStaticSourceFile();
    return file == null ? false : file.isExtern();
  }

  public int getLength() {
    return getIntProp(LENGTH);
  }

  public void setLength(int length) {
    putIntProp(LENGTH, length);
  }

  public int getLineno() {
    return extractLineno(sourcePosition);
  }

  public int getCharno() {
    return extractCharno(sourcePosition);
  }

  public int getSourceOffset() {
    StaticSourceFile file = getStaticSourceFile();
    if (file == null) {
      return -1;
    }
    int lineno = getLineno();
    if (lineno == -1) {
      return -1;
    }
    return file.getLineOffset(lineno) + getCharno();
  }

  public int getSourcePosition() {
    return sourcePosition;
  }

  public void setLineno(int lineno) {
      int charno = getCharno();
      if (charno == -1) {
        charno = 0;
      }
      sourcePosition = mergeLineCharNo(lineno, charno);
  }

  public void setCharno(int charno) {
      sourcePosition = mergeLineCharNo(getLineno(), charno);
  }

  public void setSourceEncodedPosition(int sourcePosition) {
    this.sourcePosition = sourcePosition;
  }

  public void setSourceEncodedPositionForTree(int sourcePosition) {
    this.sourcePosition = sourcePosition;

    for (Node child = getFirstChild();
         child != null; child = child.getNext()) {
      child.setSourceEncodedPositionForTree(sourcePosition);
    }
  }

  /**
   * Merges the line number and character number in one integer. The Character
   * number takes the first 12 bits and the line number takes the rest. If
   * the character number is greater than <code>2<sup>12</sup>-1</code> it is
   * adjusted to <code>2<sup>12</sup>-1</code>.
   */
  protected static int mergeLineCharNo(int lineno, int charno) {
    if (lineno < 0 || charno < 0) {
      return -1;
    } else if ((charno & ~COLUMN_MASK) != 0) {
      return lineno << COLUMN_BITS | COLUMN_MASK;
    } else {
      return lineno << COLUMN_BITS | (charno & COLUMN_MASK);
    }
  }

  /**
   * Extracts the line number and character number from a merged line char
   * number (see {@link #mergeLineCharNo(int, int)}).
   */
  protected static int extractLineno(int lineCharNo) {
    if (lineCharNo == -1) {
      return -1;
    } else {
      return lineCharNo >>> COLUMN_BITS;
    }
  }

  /**
   * Extracts the character number and character number from a merged line
   * char number (see {@link #mergeLineCharNo(int, int)}).
   */
  protected static int extractCharno(int lineCharNo) {
    if (lineCharNo == -1) {
      return -1;
    } else {
      return lineCharNo & COLUMN_MASK;
    }
  }

  //==========================================================================
  // Iteration

  /**
   * <p>Return an iterable object that iterates over this node's children.
   * The iterator does not support the optional operation
   * {@link Iterator#remove()}.</p>
   *
   * <p>To iterate over a node's children, one can write</p>
   * <pre>Node n = ...;
   * for (Node child : n.children()) { ...</pre>
   */
  public Iterable<Node> children() {
    if (first == null) {
      return Collections.emptySet();
    } else {
      return new SiblingNodeIterable(first);
    }
  }

  /**
   * <p>Return an iterable object that iterates over this node's siblings,
   * <b>including this Node</b>. The iterator does not support the optional
   * operation {@link Iterator#remove()}.</p>
   *
   * <p>To iterate over a node's siblings including itself, one can write</p>
   * <pre>Node n = ...;
   * for (Node sibling : n.siblings()) { ...</pre>
   */
  public Iterable<Node> siblings() {
    return new SiblingNodeIterable(this);
  }

  /**
   * @see Node#siblings()
   */
  private static final class SiblingNodeIterable
      implements Iterable<Node>, Iterator<Node> {
    private final Node start;
    private Node current;
    private boolean used;

    SiblingNodeIterable(Node start) {
      this.start = start;
      this.current = start;
      this.used = false;
    }

    @Override
    public Iterator<Node> iterator() {
      if (!used) {
        used = true;
        return this;
      } else {
        // We have already used the current object as an iterator;
        // we must create a new SiblingNodeIterable based on this
        // iterable's start node.
        //
        // Since the primary use case for Node.children is in for
        // loops, this branch is extremely unlikely.
        return (new SiblingNodeIterable(start)).iterator();
      }
    }

    @Override
    public boolean hasNext() {
      return current != null;
    }

    @Override
    public Node next() {
      if (current == null) {
        throw new NoSuchElementException();
      }
      try {
        return current;
      } finally {
        current = current.getNext();
      }
    }

    @Override
    public void remove() {
      throw new UnsupportedOperationException();
    }
  }

  // ==========================================================================
  // Accessors

  PropListItem getPropListHeadForTesting() {
    return propListHead;
  }

  public Node getParent() {
    return parent;
  }

  /**
   * Gets the ancestor node relative to this.
   *
   * @param level 0 = this, 1 = the parent, etc.
   */
  public Node getAncestor(int level) {
    Preconditions.checkArgument(level >= 0);
    Node node = this;
    while (node != null && level-- > 0) {
      node = node.getParent();
    }
    return node;
  }

  /**
   * Iterates all of the node's ancestors excluding itself.
   */
  public AncestorIterable getAncestors() {
    return new AncestorIterable(this.getParent());
  }

  /**
   * Iterator to go up the ancestor tree.
   */
  public static class AncestorIterable implements Iterable<Node> {
    private Node cur;

    /**
     * @param cur The node to start.
     */
    AncestorIterable(Node cur) {
      this.cur = cur;
    }

    @Override
    public Iterator<Node> iterator() {
      return new Iterator<Node>() {
        @Override
        public boolean hasNext() {
          return cur != null;
        }

        @Override
        public Node next() {
          if (!hasNext()) {
            throw new NoSuchElementException();
          }
          Node n = cur;
          cur = cur.getParent();
          return n;
        }

        @Override
        public void remove() {
          throw new UnsupportedOperationException();
        }
      };
    }
  }

  /**
   * Check for one child more efficiently than by iterating over all the
   * children as is done with Node.getChildCount().
   *
   * @return Whether the node has exactly one child.
   */
  public boolean hasOneChild() {
    return first != null && first == last;
  }

  /**
   * Check for more than one child more efficiently than by iterating over all
   * the children as is done with Node.getChildCount().
   *
   * @return Whether the node more than one child.
   */
  public boolean hasMoreThanOneChild() {
    return first != null && first != last;
  }

  public int getChildCount() {
    int c = 0;
    for (Node n = first; n != null; n = n.next) {
      c++;
    }
    return c;
  }

  // Intended for testing and verification only.
  public boolean hasChild(Node child) {
    for (Node n = first; n != null; n = n.getNext()) {
      if (child == n) {
        return true;
      }
    }
    return false;
  }

  /**
   * Checks if the subtree under this node is the same as another subtree.
   * Returns null if it's equal, or a message describing the differences.
   * Should be called with {@code this} as the "expected" node and
   * {@code actual} as the "actual" node.
   */
  @VisibleForTesting
  public String checkTreeEquals(Node actual) {
      NodeMismatch diff = checkTreeEqualsImpl(actual);
      if (diff != null) {
        return "Node tree inequality:" +
            "\nTree1:\n" + toStringTree() +
            "\n\nTree2:\n" + actual.toStringTree() +
            "\n\nSubtree1: " + diff.nodeA.toStringTree() +
            "\n\nSubtree2: " + diff.nodeB.toStringTree();
      }
      return null;
  }

  /**
   * Checks if the subtree under this node is the same as another subtree.
   * Returns null if it's equal, or a message describing the differences.
   * Considers two nodes to be unequal if their JSDocInfo doesn't match.
   * Should be called with {@code this} as the "expected" node and
   * {@code actual} as the "actual" node.
   *
   * @see JSDocInfo#equals(Object)
   */
  @VisibleForTesting
  public String checkTreeEqualsIncludingJsDoc(Node actual) {
      NodeMismatch diff = checkTreeEqualsImpl(actual, true);
      if (diff != null) {
        if (diff.nodeA.isEquivalentTo(diff.nodeB, false, true, false)) {
          // The only difference is that the JSDoc is different on
          // the subtree.
          String jsDoc1 = diff.nodeA.getJSDocInfo() == null ?
              "(none)" :
              diff.nodeA.getJSDocInfo().toStringVerbose();

          String jsDoc2 = diff.nodeB.getJSDocInfo() == null ?
              "(none)" :
              diff.nodeB.getJSDocInfo().toStringVerbose();

          return "Node tree inequality:" +
              "\nTree:\n" + toStringTree() +
              "\n\nJSDoc differs on subtree: " + diff.nodeA +
              "\nExpected JSDoc: " + jsDoc1 +
              "\nActual JSDoc  : " + jsDoc2;
        }
        return "Node tree inequality:" +
            "\nExpected tree:\n" + toStringTree() +
            "\n\nActual tree:\n" + actual.toStringTree() +
            "\n\nExpected subtree: " + diff.nodeA.toStringTree() +
            "\n\nActual subtree: " + diff.nodeB.toStringTree();
      }
      return null;
  }

  /**
   * Compare this node to node2 recursively and return the first pair of nodes
   * that differs doing a preorder depth-first traversal. Package private for
   * testing. Returns null if the nodes are equivalent.
   */
  NodeMismatch checkTreeEqualsImpl(Node node2) {
    return checkTreeEqualsImpl(node2, false);
  }

  /**
   * Compare this node to node2 recursively and return the first pair of nodes
   * that differs doing a preorder depth-first traversal.
   * @param jsDoc Whether to check for differences in JSDoc.
   */
  private NodeMismatch checkTreeEqualsImpl(Node node2, boolean jsDoc) {
    if (!isEquivalentTo(node2, false, false, jsDoc)) {
      return new NodeMismatch(this, node2);
    }

    NodeMismatch res = null;
    Node n, n2;
    for (n = first, n2 = node2.first;
         n != null;
         n = n.next, n2 = n2.next) {
      res = n.checkTreeEqualsImpl(n2, jsDoc);
      if (res != null) {
        return res;
      }
    }
    return res;
  }

  /** Returns true if this node is equivalent semantically to another */
  public boolean isEquivalentTo(Node node) {
    return isEquivalentTo(node, false, true, false);
  }

  /** Checks equivalence without going into child nodes */
  public boolean isEquivalentToShallow(Node node) {
    return isEquivalentTo(node, false, false, false);
  }

  /**
   * Returns true if this node is equivalent semantically to another and
   * the types are equivalent.
   */
  public boolean isEquivalentToTyped(Node node) {
    return isEquivalentTo(node, true, true, true);
  }

  /**
   * @param compareType Whether to compare the JSTypes of the nodes.
   * @param recurse Whether to compare the children of the current node, if
   *    not only the the count of the children are compared.
   * @param jsDoc Whether to check that the JsDoc of the nodes are equivalent.
   * @return Whether this node is equivalent semantically to the provided node.
   */
  boolean isEquivalentTo(
      Node node, boolean compareType, boolean recurse, boolean jsDoc) {
    if (type != node.getType()
        || getChildCount() != node.getChildCount()
        || this.getClass() != node.getClass()) {
      return false;
    }

    if (compareType && !JSType.isEquivalent(getJSType(), node.getJSType())) {
      return false;
    }

    if (jsDoc && !JSDocInfo.areEquivalent(getJSDocInfo(), node.getJSDocInfo())) {
      return false;
    }

    TypeDeclarationNode thisTDN = this.getDeclaredTypeExpression();
    TypeDeclarationNode thatTDN = node.getDeclaredTypeExpression();
    if ((thisTDN != null || thatTDN != null) &&
        (thisTDN == null || thatTDN == null
            || !thisTDN.isEquivalentTo(thatTDN, compareType, recurse, jsDoc))) {
      return false;
    }

    if (type == Token.INC || type == Token.DEC) {
      int post1 = this.getIntProp(INCRDECR_PROP);
      int post2 = node.getIntProp(INCRDECR_PROP);
      if (post1 != post2) {
        return false;
      }
    } else if (type == Token.STRING || type == Token.STRING_KEY) {
      if (type == Token.STRING_KEY) {
        int quoted1 = this.getIntProp(QUOTED_PROP);
        int quoted2 = node.getIntProp(QUOTED_PROP);
        if (quoted1 != quoted2) {
          return false;
        }
      }

      int slashV1 = this.getIntProp(SLASH_V);
      int slashV2 = node.getIntProp(SLASH_V);
      if (slashV1 != slashV2) {
        return false;
      }
    } else if (type == Token.CALL) {
      if (this.getBooleanProp(FREE_CALL) != node.getBooleanProp(FREE_CALL)) {
        return false;
      }
    } else if (type == Token.FUNCTION) {
      if (this.isArrowFunction() != node.isArrowFunction()) {
        return false;
      }
    }

    if (recurse) {
      Node n, n2;
      for (n = first, n2 = node.first;
           n != null;
           n = n.next, n2 = n2.next) {
        if (!n.isEquivalentTo(n2, compareType, recurse, jsDoc)) {
          return false;
        }
      }
    }

    return true;
  }

  /**
   * This function takes a set of GETPROP nodes and produces a string that is
   * each property separated by dots. If the node ultimately under the left
   * sub-tree is not a simple name, this is not a valid qualified name.
   *
   * @return a null if this is not a qualified name, or a dot-separated string
   *         of the name and properties.
   */
  public String getQualifiedName() {
    if (type == Token.NAME) {
      String name = getString();
      return name.isEmpty() ? null : name;
    } else if (type == Token.GETPROP) {
      String left = getFirstChild().getQualifiedName();
      if (left == null) {
        return null;
      }
      return left + "." + getLastChild().getString();
    } else if (type == Token.THIS) {
      return "this";
    } else if (type == Token.SUPER) {
      return "super";
    } else {
      return null;
    }
  }

  /**
   * Returns whether a node corresponds to a simple or a qualified name, such as
   * <code>x</code> or <code>a.b.c</code> or <code>this.a</code>.
   */
  public boolean isQualifiedName() {
    switch (getType()) {
      case Token.NAME:
        return !getString().isEmpty();
      case Token.THIS:
        return true;
      case Token.GETPROP:
        return getFirstChild().isQualifiedName();
      default:
        return false;
    }
  }

  /**
   * Returns whether a node matches a simple or a qualified name, such as
   * <code>x</code> or <code>a.b.c</code> or <code>this.a</code>.
   */
  public boolean matchesQualifiedName(String name) {
    return name != null && matchesQualifiedName(name, name.length());
  }

  /**
   * Returns whether a node matches a simple or a qualified name, such as
   * <code>x</code> or <code>a.b.c</code> or <code>this.a</code>.
   */
  private boolean matchesQualifiedName(String qname, int endIndex) {
    int start = qname.lastIndexOf('.', endIndex - 1) + 1;

    switch (getType()) {
      case Token.NAME:
        String name = getString();
        return start == 0 && !name.isEmpty() &&
           name.length() == endIndex && qname.startsWith(name);
      case Token.THIS:
        return start == 0 && 4 == endIndex && qname.startsWith("this");
      case Token.SUPER:
        return start == 0 && 5 == endIndex && qname.startsWith("super");
      case Token.GETPROP:
        String prop = getLastChild().getString();
        return start > 1
            && prop.length() == endIndex - start
            && prop.regionMatches(0, qname, start, endIndex - start)
            && getFirstChild().matchesQualifiedName(qname, start - 1);
      default:
        return false;
    }
  }

  /**
   * Returns whether a node matches a simple or a qualified name, such as
   * <code>x</code> or <code>a.b.c</code> or <code>this.a</code>.
   */
  public boolean matchesQualifiedName(Node n) {
    if (n == null || n.type != type) {
      return false;
    }
    switch (type) {
      case Token.NAME:
        return !getString().isEmpty() && getString().equals(n.getString());
      case Token.THIS:
        return true;
      case Token.SUPER:
        return true;
      case Token.GETPROP:
        return getLastChild().getString().equals(n.getLastChild().getString())
            && getFirstChild().matchesQualifiedName(n.getFirstChild());
      default:
        return false;
    }
  }

  /**
   * Returns whether a node corresponds to a simple or a qualified name without
   * a "this" reference, such as <code>a.b.c</code>, but not <code>this.a</code>
   * .
   */
  public boolean isUnscopedQualifiedName() {
    switch (getType()) {
      case Token.NAME:
        return !getString().isEmpty();
      case Token.GETPROP:
        return getFirstChild().isUnscopedQualifiedName();
      default:
        return false;
    }
  }

  public boolean isValidAssignmentTarget() {
    switch (getType()) {
      // TODO(tbreisacher): Remove CAST from this list, and disallow
      // the cryptic case from cl/41958159.
      case Token.CAST:
      case Token.DEFAULT_VALUE:
      case Token.NAME:
      case Token.GETPROP:
      case Token.GETELEM:
      case Token.ARRAY_PATTERN:
      case Token.OBJECT_PATTERN:
        return true;
      default:
        return false;
    }
  }

  // ==========================================================================
  // Mutators

  /**
   * Removes this node from its parent. Equivalent to:
   * node.getParent().removeChild();
   */
  public Node detachFromParent() {
    Preconditions.checkState(parent != null);
    parent.removeChild(this);
    return this;
  }

  /**
   * Removes the first child of Node. Equivalent to:
   * node.removeChild(node.getFirstChild());
   *
   * @return The removed Node.
   */
  public Node removeFirstChild() {
    Node child = first;
    if (child != null) {
      removeChild(child);
    }
    return child;
  }

  /**
   * @return A Node that is the head of the list of children.
   */
  public Node removeChildren() {
    Node children = first;
    for (Node child = first; child != null; child = child.getNext()) {
      child.parent = null;
    }
    first = null;
    last = null;
    return children;
  }

  /**
   * Removes all children from this node and isolates the children from each
   * other.
   */
  public void detachChildren() {
    for (Node child = first; child != null;) {
      Node nextChild = child.getNext();
      child.parent = null;
      child.next = null;
      child = nextChild;
    }
    first = null;
    last = null;
  }

  public Node removeChildAfter(Node prev) {
    Preconditions.checkArgument(prev.parent == this,
        "prev is not a child of this node.");
    Preconditions.checkArgument(prev.next != null,
        "no next sibling.");

    Node child = prev.next;
    prev.next = child.next;
    if (child == last) {
      last = prev;
    }
    child.next = null;
    child.parent = null;
    return child;
  }

  /**
   * @return A detached clone of the Node, specifically excluding its children.
   */
  public Node cloneNode() {
    Node result;
    try {
      result = (Node) super.clone();
      // PropListItem lists are immutable and can be shared so there is no
      // need to clone them here.
      result.next = null;
      result.first = null;
      result.last = null;
      result.parent = null;
    } catch (CloneNotSupportedException e) {
      throw new RuntimeException(e.getMessage());
    }
    return result;
  }

  /**
   * @return A detached clone of the Node and all its children.
   */
  public Node cloneTree() {
    Node result = cloneNode();
    for (Node n2 = getFirstChild(); n2 != null; n2 = n2.getNext()) {
      Node n2clone = n2.cloneTree();
      n2clone.parent = result;
      if (result.last != null) {
        result.last.next = n2clone;
      }
      if (result.first == null) {
        result.first = n2clone;
      }
      result.last = n2clone;
    }
    return result;
  }

  /**
   * Copies source file and name information from the other
   * node given to the current node. Used for maintaining
   * debug information across node append and remove operations.
   * @return this
   */
  // TODO(nicksantos): The semantics of this method are ill-defined. Delete it.
  public Node copyInformationFrom(Node other) {
    if (getProp(ORIGINALNAME_PROP) == null) {
      putProp(ORIGINALNAME_PROP, other.getProp(ORIGINALNAME_PROP));
    }

    if (getProp(STATIC_SOURCE_FILE) == null) {
      putProp(STATIC_SOURCE_FILE, other.getProp(STATIC_SOURCE_FILE));
      sourcePosition = other.sourcePosition;
    }

    return this;
  }

  /**
   * Copies source file and name information from the other node to the
   * entire tree rooted at this node.
   * @return this
   */
  // TODO(nicksantos): The semantics of this method are ill-defined. Delete it.
  public Node copyInformationFromForTree(Node other) {
    copyInformationFrom(other);
    for (Node child = getFirstChild();
         child != null; child = child.getNext()) {
      child.copyInformationFromForTree(other);
    }

    return this;
  }

  /**
   * Overwrite all the source information in this node with
   * that of {@code other}.
   */
  public Node useSourceInfoFrom(Node other) {
    putProp(ORIGINALNAME_PROP, other.getProp(ORIGINALNAME_PROP));
    putProp(STATIC_SOURCE_FILE, other.getProp(STATIC_SOURCE_FILE));
    sourcePosition = other.sourcePosition;
    setLength(other.getLength());
    return this;
  }

  public Node srcref(Node other) {
    return useSourceInfoFrom(other);
  }

  /**
   * Overwrite all the source information in this node and its subtree with
   * that of {@code other}.
   */
  public Node useSourceInfoFromForTree(Node other) {
    useSourceInfoFrom(other);
    for (Node child = getFirstChild();
         child != null; child = child.getNext()) {
      child.useSourceInfoFromForTree(other);
    }

    return this;
  }

  public Node srcrefTree(Node other) {
    return useSourceInfoFromForTree(other);
  }

  /**
   * Overwrite all the source information in this node with
   * that of {@code other} iff the source info is missing.
   */
  public Node useSourceInfoIfMissingFrom(Node other) {
    if (getProp(ORIGINALNAME_PROP) == null) {
      putProp(ORIGINALNAME_PROP, other.getProp(ORIGINALNAME_PROP));
    }

    if (getProp(STATIC_SOURCE_FILE) == null) {
      putProp(STATIC_SOURCE_FILE, other.getProp(STATIC_SOURCE_FILE));
      sourcePosition = other.sourcePosition;
      setLength(other.getLength());
    }

    return this;
  }

  /**
   * Overwrite all the source information in this node and its subtree with
   * that of {@code other} iff the source info is missing.
   */
  public Node useSourceInfoIfMissingFromForTree(Node other) {
    useSourceInfoIfMissingFrom(other);
    for (Node child = getFirstChild();
         child != null; child = child.getNext()) {
      child.useSourceInfoIfMissingFromForTree(other);
    }

    return this;
  }

  //==========================================================================
  // Custom annotations

  /**
   * Returns the compiled inferred type on this node. Not to be confused
   * with {@link #getDeclaredTypeExpression()} which returns the syntactically
   * specified type.
   */
  public JSType getJSType() {
    return typei instanceof JSType ? (JSType) typei : null;
  }

  public void setJSType(JSType jsType) {
    this.typei = jsType;
  }

  public TypeI getTypeI() {
    // For the time being, we only want to return the type iff it's an old type.
    return getJSType();
  }

  public void setTypeI(TypeI type) {
    this.typei = type;
  }

  /**
   * Get the {@link JSDocInfo} attached to this node.
   * @return the information or {@code null} if no JSDoc is attached to this
   * node
   */
  public JSDocInfo getJSDocInfo() {
    return (JSDocInfo) getProp(JSDOC_INFO_PROP);
  }

  /**
   * Sets the {@link JSDocInfo} attached to this node.
   */
  public Node setJSDocInfo(JSDocInfo info) {
    putProp(JSDOC_INFO_PROP, info);
    return this;
  }

  /** This node was last changed at {@code time} */
  public void setChangeTime(int time) {
    putIntProp(CHANGE_TIME, time);
  }

  /** Returns the time of the last change for this node */
  public int getChangeTime() {
    return getIntProp(CHANGE_TIME);
  }

  /**
   * Sets whether this node is a variable length argument node. This
   * method is meaningful only on {@link Token#NAME} nodes
   * used to define a {@link Token#FUNCTION}'s argument list.
   */
  public void setVarArgs(boolean varArgs) {
    putBooleanProp(VAR_ARGS_NAME, varArgs);
  }

  /**
   * Returns whether this node is a variable length argument node. This
   * method's return value is meaningful only on {@link Token#NAME} nodes
   * used to define a {@link Token#FUNCTION}'s argument list.
   */
  public boolean isVarArgs() {
    return getBooleanProp(VAR_ARGS_NAME);
  }

  /**
   * Sets whether this node is an optional argument node. This
   * method is meaningful only on {@link Token#NAME} nodes
   * used to define a {@link Token#FUNCTION}'s argument list.
   */
  public void setOptionalArg(boolean optionalArg) {
    putBooleanProp(OPT_ARG_NAME, optionalArg);
  }

  /**
   * Returns whether this node is an optional argument node. This
   * method's return value is meaningful only on {@link Token#NAME} nodes
   * used to define a {@link Token#FUNCTION}'s argument list.
   */
  public boolean isOptionalArg() {
    return getBooleanProp(OPT_ARG_NAME);
  }

  /**
   * Sets whether this is a synthetic block that should not be considered
   * a real source block.
   */
  public void setIsSyntheticBlock(boolean val) {
    putBooleanProp(SYNTHETIC_BLOCK_PROP, val);
  }

  /**
   * Returns whether this is a synthetic block that should not be considered
   * a real source block.
   */
  public boolean isSyntheticBlock() {
    return getBooleanProp(SYNTHETIC_BLOCK_PROP);
  }

  /**
   * Sets the ES5 directives on this node.
   */
  public void setDirectives(Set<String> val) {
    putProp(DIRECTIVES, val);
  }

  /**
   * Returns the set of ES5 directives for this node.
   */
  @SuppressWarnings("unchecked")
  public Set<String> getDirectives() {
    return (Set<String>) getProp(DIRECTIVES);
  }

  /**
   * Sets whether this is an added block that should not be considered
   * a real source block. Eg: In "if (true) x;", the "x;" is put under an added
   * block in the AST.
   */
  public void setIsAddedBlock(boolean val) {
    putBooleanProp(ADDED_BLOCK, val);
  }

  /**
   * Returns whether this is an added block that should not be considered
   * a real source block.
   */
  public boolean isAddedBlock() {
    return getBooleanProp(ADDED_BLOCK);
  }

  /**
   * Sets whether this node is a static member node. This
   * method is meaningful only on {@link Token#GETTER_DEF},
   * {@link Token#SETTER_DEF} or {@link Token#MEMBER_FUNCTION_DEF} nodes contained
   * within {@link Token#CLASS}.
   */
  public void setStaticMember(boolean isStatic) {
    putBooleanProp(STATIC_MEMBER, isStatic);
  }

  /**
   * Returns whether this node is a static member node. This
   * method is meaningful only on {@link Token#GETTER_DEF},
   * {@link Token#SETTER_DEF} or {@link Token#MEMBER_FUNCTION_DEF} nodes contained
   * within {@link Token#CLASS}.
   */
  public boolean isStaticMember() {
    return getBooleanProp(STATIC_MEMBER);
  }

  /**
   * Sets whether this node is a generator node. This
   * method is meaningful only on {@link Token#FUNCTION} or
   * {@link Token#MEMBER_FUNCTION_DEF} nodes.
   */
  public void setIsGeneratorFunction(boolean isGenerator) {
    putBooleanProp(GENERATOR_FN, isGenerator);
  }

  /**
   * Returns whether this node is a generator function node.
   */
  public boolean isGeneratorFunction() {
    return getBooleanProp(GENERATOR_FN);
  }

  /**
   * Sets whether this node is a marker used in the translation of generators.
   */
  public void setGeneratorMarker(boolean isGeneratorMarker) {
    putBooleanProp(GENERATOR_MARKER, isGeneratorMarker);
  }

  /**
   * Returns whether this node is a marker used in the translation of generators.
   */
  public boolean isGeneratorMarker() {
    return getBooleanProp(GENERATOR_MARKER);
  }

  /**
   * @see #isGeneratorSafe()
   */
  public void setGeneratorSafe(boolean isGeneratorSafe) {
    putBooleanProp(GENERATOR_SAFE, isGeneratorSafe);
  }

  /**
   * Used when translating ES6 generators. If this returns true, this Node
   * was generated by the compiler, and it is safe to copy this node to the
   * transpiled output with no further changes.
   */
  public boolean isGeneratorSafe() {
    return getBooleanProp(GENERATOR_SAFE);
  }

  /**
   * Sets whether this node is a arrow function node. This
   * method is meaningful only on {@link Token#FUNCTION}
   */
  public void setIsArrowFunction(boolean isArrow) {
    putBooleanProp(ARROW_FN, isArrow);
  }

  /**
   * Returns whether this node is a arrow function node.
   */
  public boolean isArrowFunction() {
    return getBooleanProp(ARROW_FN);
  }

  /**
   * Sets whether this node is a generator node. This
   * method is meaningful only on {@link Token#FUNCTION} or
   * {@link Token#MEMBER_FUNCTION_DEF} nodes.
   */
  public void setYieldFor(boolean isGenerator) {
    putBooleanProp(YIELD_FOR, isGenerator);
  }

  /**
   * Returns whether this node is a generator node. This
   * method is meaningful only on {@link Token#FUNCTION} or
   * {@link Token#MEMBER_FUNCTION_DEF} nodes.
   */
  public boolean isYieldFor() {
    return getBooleanProp(YIELD_FOR);
  }

  // There are four values of interest:
  //   global state changes
  //   this state changes
  //   arguments state changes
  //   whether the call throws an exception
  //   locality of the result
  // We want a value of 0 to mean "global state changes and
  // unknown locality of result".

  public static final int FLAG_GLOBAL_STATE_UNMODIFIED = 1;
  public static final int FLAG_THIS_UNMODIFIED = 2;
  public static final int FLAG_ARGUMENTS_UNMODIFIED = 4;
  public static final int FLAG_NO_THROWS = 8;
  public static final int FLAG_LOCAL_RESULTS = 16;

  public static final int SIDE_EFFECTS_FLAGS_MASK = 31;

  public static final int SIDE_EFFECTS_ALL = 0;
  public static final int NO_SIDE_EFFECTS =
    FLAG_GLOBAL_STATE_UNMODIFIED
    | FLAG_THIS_UNMODIFIED
    | FLAG_ARGUMENTS_UNMODIFIED
    | FLAG_NO_THROWS;

  /**
   * Marks this function or constructor call's side effect flags.
   * This property is only meaningful for {@link Token#CALL} and
   * {@link Token#NEW} nodes.
   */
  public void setSideEffectFlags(int flags) {
    Preconditions.checkArgument(
        getType() == Token.CALL || getType() == Token.NEW,
        "setIsNoSideEffectsCall only supports CALL and NEW nodes, got %s",
        Token.name(getType()));

    putIntProp(SIDE_EFFECT_FLAGS, flags);
  }

  public void setSideEffectFlags(SideEffectFlags flags) {
    setSideEffectFlags(flags.valueOf());
  }

  /**
   * Returns the side effects flags for this node.
   */
  public int getSideEffectFlags() {
    return getIntProp(SIDE_EFFECT_FLAGS);
  }

  /**
   * A helper class for getting and setting the side-effect flags.
   * @author johnlenz@google.com (John Lenz)
   */
  public static class SideEffectFlags {
    private int value = Node.SIDE_EFFECTS_ALL;

    public SideEffectFlags() {
    }

    public SideEffectFlags(int value) {
      this.value = value;
    }

    public int valueOf() {
      return value;
    }

    /** All side-effect occur and the returned results are non-local. */
    public SideEffectFlags setAllFlags() {
      value = Node.SIDE_EFFECTS_ALL;
      return this;
    }

    /** No side-effects occur and the returned results are local. */
    public SideEffectFlags clearAllFlags() {
      value = Node.NO_SIDE_EFFECTS | Node.FLAG_LOCAL_RESULTS;
      return this;
    }

    public boolean areAllFlagsSet() {
      return value == Node.SIDE_EFFECTS_ALL;
    }

    /**
     * Preserve the return result flag, but clear the others:
     *   no global state change, no throws, no this change, no arguments change
     */
    public void clearSideEffectFlags() {
      value |= Node.NO_SIDE_EFFECTS;
    }

    public SideEffectFlags setMutatesGlobalState() {
      // Modify global means everything must be assumed to be modified.
      removeFlag(Node.FLAG_GLOBAL_STATE_UNMODIFIED);
      removeFlag(Node.FLAG_ARGUMENTS_UNMODIFIED);
      removeFlag(Node.FLAG_THIS_UNMODIFIED);
      return this;
    }

    public SideEffectFlags setThrows() {
      removeFlag(Node.FLAG_NO_THROWS);
      return this;
    }

    public SideEffectFlags setMutatesThis() {
      removeFlag(Node.FLAG_THIS_UNMODIFIED);
      return this;
    }

    public SideEffectFlags setMutatesArguments() {
      removeFlag(Node.FLAG_ARGUMENTS_UNMODIFIED);
      return this;
    }

    public SideEffectFlags setReturnsTainted() {
      removeFlag(Node.FLAG_LOCAL_RESULTS);
      return this;
    }

    private void removeFlag(int flag) {
      value &= ~flag;
    }
  }

  /**
   * @return Whether the only side-effect is "modifies this"
   */
  public boolean isOnlyModifiesThisCall() {
    return areBitFlagsSet(
        getSideEffectFlags() & Node.NO_SIDE_EFFECTS,
        Node.FLAG_GLOBAL_STATE_UNMODIFIED
            | Node.FLAG_ARGUMENTS_UNMODIFIED
            | Node.FLAG_NO_THROWS);
  }

  /**
   * @return Whether the only side-effect is "modifies arguments"
   */
  public boolean isOnlyModifiesArgumentsCall() {
    return areBitFlagsSet(
        getSideEffectFlags() & Node.NO_SIDE_EFFECTS,
        Node.FLAG_GLOBAL_STATE_UNMODIFIED
            | Node.FLAG_THIS_UNMODIFIED
            | Node.FLAG_NO_THROWS);
  }

  /**
   * Returns true if this node is a function or constructor call that
   * has no side effects.
   */
  public boolean isNoSideEffectsCall() {
    return areBitFlagsSet(getSideEffectFlags(), NO_SIDE_EFFECTS);
  }

  /**
   * Returns true if this node is a function or constructor call that
   * returns a primitive or a local object (an object that has no other
   * references).
   */
  public boolean isLocalResultCall() {
    return areBitFlagsSet(getSideEffectFlags(), FLAG_LOCAL_RESULTS);
  }

  /** Returns true if this is a new/call that may mutate its arguments. */
  public boolean mayMutateArguments() {
    return !areBitFlagsSet(getSideEffectFlags(), FLAG_ARGUMENTS_UNMODIFIED);
  }

  /** Returns true if this is a new/call that may mutate global state or throw. */
  public boolean mayMutateGlobalStateOrThrow() {
    return !areBitFlagsSet(getSideEffectFlags(),
        FLAG_GLOBAL_STATE_UNMODIFIED | FLAG_NO_THROWS);
  }

  /**
   * returns true if all the flags are set in value.
   */
  private boolean areBitFlagsSet(int value, int flags) {
    return (value & flags) == flags;
  }

  /**
   * This should only be called for STRING nodes children of OBJECTLIT.
   */
  public boolean isQuotedString() {
    return false;
  }

  /**
   * This should only be called for STRING nodes children of OBJECTLIT.
   */
  public void setQuotedString() {
    throw new IllegalStateException("not a StringNode");
  }

  static class NodeMismatch {
    final Node nodeA;
    final Node nodeB;

    NodeMismatch(Node nodeA, Node nodeB) {
      this.nodeA = nodeA;
      this.nodeB = nodeB;
    }

    @Override
    public boolean equals(Object object) {
      if (object instanceof NodeMismatch) {
        NodeMismatch that = (NodeMismatch) object;
        return that.nodeA.equals(this.nodeA) && that.nodeB.equals(this.nodeB);
      }
      return false;
    }

    @Override
    public int hashCode() {
      return Objects.hashCode(nodeA, nodeB);
    }
  }


  /*** AST type check methods ***/

  public boolean isAdd() {
    return this.getType() == Token.ADD;
  }

  public boolean isAnd() {
    return this.getType() == Token.AND;
  }

  public boolean isArrayLit() {
    return this.getType() == Token.ARRAYLIT;
  }

  public boolean isArrayPattern() {
    return this.getType() == Token.ARRAY_PATTERN;
  }

  public boolean isAssign() {
    return this.getType() == Token.ASSIGN;
  }

  public boolean isAssignAdd() {
    return this.getType() == Token.ASSIGN_ADD;
  }

  public boolean isBlock() {
    return this.getType() == Token.BLOCK;
  }

  public boolean isBreak() {
    return this.getType() == Token.BREAK;
  }

  public boolean isCall() {
    return this.getType() == Token.CALL;
  }

  public boolean isCase() {
    return this.getType() == Token.CASE;
  }

  public boolean isCast() {
    return this.getType() == Token.CAST;
  }

  public boolean isCatch() {
    return this.getType() == Token.CATCH;
  }

  public boolean isClass() {
    return this.getType() == Token.CLASS;
  }

  public boolean isClassMembers() {
    return this.getType() == Token.CLASS_MEMBERS;
  }

  public boolean isComma() {
    return this.getType() == Token.COMMA;
  }

  public boolean isComputedProp() {
    return this.getType() == Token.COMPUTED_PROP;
  }

  public boolean isContinue() {
    return this.getType() == Token.CONTINUE;
  }

  public boolean isConst() {
    return this.getType() == Token.CONST;
  }

  public boolean isDebugger() {
    return this.getType() == Token.DEBUGGER;
  }

  public boolean isDec() {
    return this.getType() == Token.DEC;
  }

  public boolean isDefaultCase() {
    return this.getType() == Token.DEFAULT_CASE;
  }

  public boolean isDefaultValue() {
    return this.getType() == Token.DEFAULT_VALUE;
  }

  public boolean isDelProp() {
    return this.getType() == Token.DELPROP;
  }

  public boolean isDestructuringPattern() {
    return isObjectPattern() || isArrayPattern();
  }

  public boolean isDo() {
    return this.getType() == Token.DO;
  }

  public boolean isEmpty() {
    return this.getType() == Token.EMPTY;
  }

  public boolean isExport() {
    return this.getType() == Token.EXPORT;
  }

  public boolean isExprResult() {
    return this.getType() == Token.EXPR_RESULT;
  }

  public boolean isFalse() {
    return this.getType() == Token.FALSE;
  }

  public boolean isFor() {
    return this.getType() == Token.FOR;
  }

  public boolean isForOf() {
    return this.getType() == Token.FOR_OF;
  }

  public boolean isFunction() {
    return this.getType() == Token.FUNCTION;
  }

  public boolean isGetterDef() {
    return this.getType() == Token.GETTER_DEF;
  }

  public boolean isGetElem() {
    return this.getType() == Token.GETELEM;
  }

  public boolean isGetProp() {
    return this.getType() == Token.GETPROP;
  }

  public boolean isHook() {
    return this.getType() == Token.HOOK;
  }

  public boolean isIf() {
    return this.getType() == Token.IF;
  }

  public boolean isImport() {
    return this.getType() == Token.IMPORT;
  }

  public boolean isIn() {
    return this.getType() == Token.IN;
  }

  public boolean isInc() {
    return this.getType() == Token.INC;
  }

  public boolean isInstanceOf() {
    return this.getType() == Token.INSTANCEOF;
  }

  public boolean isInterfaceMembers() {
    return this.getType() == Token.INTERFACE_MEMBERS;
  }

  public boolean isLabel() {
    return this.getType() == Token.LABEL;
  }

  public boolean isLabelName() {
    return this.getType() == Token.LABEL_NAME;
  }

  public boolean isLet() {
    return this.getType() == Token.LET;
  }

  public boolean isMemberFunctionDef() {
    return this.getType() == Token.MEMBER_FUNCTION_DEF;
  }

  public boolean isMemberVariableDef() {
    return this.getType() == Token.MEMBER_VARIABLE_DEF;
  }

  public boolean isName() {
    return this.getType() == Token.NAME;
  }

  public boolean isNE() {
    return this.getType() == Token.NE;
  }

  public boolean isNew() {
    return this.getType() == Token.NEW;
  }

  public boolean isNot() {
    return this.getType() == Token.NOT;
  }

  public boolean isNull() {
    return this.getType() == Token.NULL;
  }

  public boolean isNumber() {
    return this.getType() == Token.NUMBER;
  }

  public boolean isObjectLit() {
    return this.getType() == Token.OBJECTLIT;
  }

  public boolean isObjectPattern() {
    return this.getType() == Token.OBJECT_PATTERN;
  }

  public boolean isOr() {
    return this.getType() == Token.OR;
  }

  public boolean isParamList() {
    return this.getType() == Token.PARAM_LIST;
  }

  public boolean isRegExp() {
    return this.getType() == Token.REGEXP;
  }

  public boolean isRest() {
    return this.getType() == Token.REST;
  }

  public boolean isReturn() {
    return this.getType() == Token.RETURN;
  }

  public boolean isScript() {
    return this.getType() == Token.SCRIPT;
  }

  public boolean isSetterDef() {
    return this.getType() == Token.SETTER_DEF;
  }

  public boolean isSpread() {
    return this.getType() == Token.SPREAD;
  }

  public boolean isString() {
    return this.getType() == Token.STRING;
  }

  public boolean isStringKey() {
    return this.getType() == Token.STRING_KEY;
  }

  public boolean isSuper() {
    return this.getType() == Token.SUPER;
  }

  public boolean isSwitch() {
    return this.getType() == Token.SWITCH;
  }

  public boolean isThis() {
    return this.getType() == Token.THIS;
  }

  public boolean isThrow() {
    return this.getType() == Token.THROW;
  }

  public boolean isTrue() {
    return this.getType() == Token.TRUE;
  }

  public boolean isTry() {
    return this.getType() == Token.TRY;
  }

  public boolean isTypeOf() {
    return this.getType() == Token.TYPEOF;
  }

  public boolean isVar() {
    return this.getType() == Token.VAR;
  }

  public boolean isVoid() {
    return this.getType() == Token.VOID;
  }

  public boolean isWhile() {
    return this.getType() == Token.WHILE;
  }

  public boolean isWith() {
    return this.getType() == Token.WITH;
  }

  public boolean isYield() {
    return this.getType() == Token.YIELD;
  }
}


File: src/com/google/javascript/rhino/TypeDeclarationsIR.java
/*
 *
 * ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Rhino code, released
 * May 6, 1999.
 *
 * The Initial Developer of the Original Code is
 * Netscape Communications Corporation.
 * Portions created by the Initial Developer are Copyright (C) 1997-1999
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Michael Zhou
 *
 * Alternatively, the contents of this file may be used under the terms of
 * the GNU General Public License Version 2 or later (the "GPL"), in which
 * case the provisions of the GPL are applicable instead of those above. If
 * you wish to allow use of your version of this file only under the terms of
 * the GPL and not to allow others to use your version of this file under the
 * MPL, indicate your decision by deleting the provisions above and replacing
 * them with the notice and other provisions required by the GPL. If you do
 * not delete the provisions above, a recipient may use your version of this
 * file under either the MPL or the GPL.
 *
 * ***** END LICENSE BLOCK ***** */

package com.google.javascript.rhino;

import com.google.common.base.Preconditions;
import com.google.common.base.Splitter;
import com.google.common.collect.Iterables;
import com.google.javascript.rhino.Node.TypeDeclarationNode;

import java.util.Arrays;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * An AST construction helper class for TypeDeclarationNode
 * @author alexeagle@google.com (Alex Eagle)
 * @author moz@google.com (Michael Zhou)
 */
public class TypeDeclarationsIR {

  /**
   * @return a new node representing the string built-in type.
   */
  public static TypeDeclarationNode stringType() {
    return new TypeDeclarationNode(Token.STRING_TYPE);
  }

  /**
   * @return a new node representing the number built-in type.
   */
  public static TypeDeclarationNode numberType() {
    return new TypeDeclarationNode(Token.NUMBER_TYPE);
  }

  /**
   * @return a new node representing the boolean built-in type.
   */
  public static TypeDeclarationNode booleanType() {
    return new TypeDeclarationNode(Token.BOOLEAN_TYPE);
  }

  /**
   * We assume that types are non-nullable by default. Wrap a type in nullable
   * to indicate that it should be allowed to take a null value.
   * NB: this is not currently supported in TypeScript so it is not printed
   * in the CodeGenerator for ES6_TYPED.
   * @return a new node indicating that the nested type is nullable
   */
  public static TypeDeclarationNode nullable(TypeDeclarationNode type) {
    return new TypeDeclarationNode(Token.NULLABLE_TYPE, type);
  }

  /**
   * Equivalent to the UNKNOWN type in Closure, expressed with {@code {?}}
   * @return a new node representing any type, without type checking.
   */
  public static TypeDeclarationNode anyType() {
    return new TypeDeclarationNode(Token.ANY_TYPE);
  }

  /**
   * @return a new node representing the Void type as defined by TypeScript.
   */
  public static TypeDeclarationNode voidType() {
    return new TypeDeclarationNode(Token.VOID_TYPE);
  }

  /**
   * @return a new node representing the Undefined type as defined by TypeScript.
   */
  public static TypeDeclarationNode undefinedType() {
    return new TypeDeclarationNode(Token.UNDEFINED_TYPE);
  }

  /**
   * Splits a '.' separated qualified name into a tree of type segments.
   *
   * @param typeName a qualified name such as "goog.ui.Window"
   * @return a new node representing the type
   * @see #namedType(Iterable)
   */
  public static TypeDeclarationNode namedType(String typeName) {
    return namedType(Splitter.on('.').split(typeName));
  }

  /**
   * Produces a tree structure similar to the Rhino AST of a qualified name
   * expression, under a top-level NAMED_TYPE node.
   *
   * <p>Example:
   * <pre>
   * NAMED_TYPE
   *   NAME goog
   *     STRING ui
   *       STRING Window
   * </pre>
   */
  public static TypeDeclarationNode namedType(Iterable<String> segments) {
    Iterator<String> segmentsIt = segments.iterator();
    Node node = IR.name(segmentsIt.next());
    while (segmentsIt.hasNext()) {
      node = IR.getprop(node, IR.string(segmentsIt.next()));
    }
    return new TypeDeclarationNode(Token.NAMED_TYPE, node);
  }

  /**
   * Represents a structural type.
   * Closure calls this a Record Type and accepts the syntax
   * {@code {myNum: number, myObject}}
   *
   * <p>Example:
   * <pre>
   * RECORD_TYPE
   *   STRING_KEY myNum
   *     NUMBER_TYPE
   *   STRING_KEY myObject
   * </pre>
   * @param properties a map from property name to property type
   * @return a new node representing the record type
   */
  public static TypeDeclarationNode recordType(
      LinkedHashMap<String, TypeDeclarationNode> properties) {
    TypeDeclarationNode node = new TypeDeclarationNode(Token.RECORD_TYPE);
    for (Map.Entry<String, TypeDeclarationNode> prop : properties.entrySet()) {
      if (prop.getValue() == null) {
        node.addChildToBack(IR.stringKey(prop.getKey()));
      } else {
        Node stringKey = IR.stringKey(prop.getKey());
        stringKey.addChildToFront(prop.getValue());
        node.addChildToBack(stringKey);
      }
    }
    return node;
  }

  /**
   * Represents a function type.
   * Closure has syntax like {@code {function(string, boolean):number}}
   * Closure doesn't include parameter names. If the parameter types are unnamed,
   * arbitrary names can be substituted, eg. p1, p2, etc.
   *
   * <p>Example:
   * <pre>
   * FUNCTION_TYPE
   *   NUMBER_TYPE
   *   STRING_KEY p1
   *     STRING_TYPE
   *   STRING_KEY p2
   *     BOOLEAN_TYPE
   * </pre>
   * @param returnType the type returned by the function, possibly UNKNOWN_TYPE
   * @param parameters the types of the parameters.
   * @param restName the name of the rest parameter, if any.
   * @param restType the type of the rest parameter, if any.
   */
  public static TypeDeclarationNode functionType(
      Node returnType, LinkedHashMap<String, TypeDeclarationNode> parameters,
      String restName, TypeDeclarationNode restType) {
    TypeDeclarationNode node = new TypeDeclarationNode(Token.FUNCTION_TYPE, returnType);
    for (Map.Entry<String, TypeDeclarationNode> parameter : parameters.entrySet()) {
      Node stringKey = IR.stringKey(parameter.getKey());
      stringKey.addChildToFront(parameter.getValue());
      node.addChildToBack(stringKey);
    }
    if (restName != null) {
      Node rest = IR.stringKey(restName);
      if (restType != null) {
        rest.addChildToBack(arrayType(restType));
      }
      node.addChildToBack(restParams(rest));
    }
    return node;
  }

  /**
   * Represents a parameterized, or generic, type.
   * Closure calls this a Type Application and accepts syntax like
   * {@code {Object.<string, number>}}
   *
   * <p>Example:
   * <pre>
   * PARAMETERIZED_TYPE
   *   NAMED_TYPE
   *     NAME Object
   *   STRING_TYPE
   *   NUMBER_TYPE
   * </pre>
   * @param baseType
   * @param typeParameters
   */
  public static TypeDeclarationNode parameterizedType(
      TypeDeclarationNode baseType, Iterable<TypeDeclarationNode> typeParameters) {
    if (Iterables.isEmpty(typeParameters)) {
      return baseType;
    }
    TypeDeclarationNode node = new TypeDeclarationNode(Token.PARAMETERIZED_TYPE, baseType);
    for (Node typeParameter : typeParameters) {
      node.addChildToBack(typeParameter);
    }
    return node;
  }

  /**
   * Represents an array type. In Closure, this is represented by a
   * {@link #parameterizedType(TypeDeclarationNode, Iterable) parameterized type} of {@code Array}
   * with {@code elementType} as the sole type parameter.
   *
   * <p>Example
   * <pre>
   * ARRAY_TYPE
   *   elementType
   * </pre>
   */
  public static TypeDeclarationNode arrayType(Node elementType) {
    return new TypeDeclarationNode(Token.ARRAY_TYPE, elementType);
  }

  /**
   * Represents a union type, which can be one of the given types.
   * Closure accepts syntax like {@code {(number|boolean)}}
   *
   * <p>Example:
   * <pre>
   * UNION_TYPE
   *   NUMBER_TYPE
   *   BOOLEAN_TYPE
   * </pre>
   * @param options the types which are accepted
   * @return a new node representing the union type
   */
  public static TypeDeclarationNode unionType(Iterable<TypeDeclarationNode> options) {
    Preconditions.checkArgument(!Iterables.isEmpty(options),
        "union must have at least one option");
    TypeDeclarationNode node = new TypeDeclarationNode(Token.UNION_TYPE);
    for (Node option : options) {
      node.addChildToBack(option);
    }
    return node;
  }

  public static TypeDeclarationNode unionType(TypeDeclarationNode... options) {
    return unionType(Arrays.asList(options));
  }

  /**
   * Represents a function parameter type which may be repeated.
   * Closure calls this Variable Parameters and accepts a syntax like
   * {@code {function(string, ...number): number}}
   *
   * <p>
   * <pre>
   * FUNCTION_TYPE
   *   NUMBER_TYPE
   *   STRING_KEY p1
   *     STRING_TYPE
   *   REST_PARAMETER_TYPE
   *     STRING_KEY p2
   *       NUMBER_TYPE
   * </pre>
   * @param type an array type that is seen inside the function body
   * @return a new node representing the function parameter type
   */
  public static TypeDeclarationNode restParams(Node type) {
    TypeDeclarationNode node = new TypeDeclarationNode(Token.REST_PARAMETER_TYPE);
    if (type != null) {
      node.addChildToBack(type);
    }
    return node;
  }

  /**
   * Represents a function parameter that is optional.
   * In closure syntax, this is {@code function(?string=, number=)}
   * In TypeScript syntax, it is
   * {@code (firstName: string, lastName?: string)=>string}
   * @param parameterType the type of the parameter
   * @return a new node representing the function parameter type
   */
  public static TypeDeclarationNode optionalParameter(TypeDeclarationNode parameterType) {
    return new TypeDeclarationNode(Token.OPTIONAL_PARAMETER, parameterType);
  }
}


File: test/com/google/javascript/jscomp/Es6InlineTypesNotYetParsedTest.java
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

import static com.google.common.truth.Truth.THROW_ASSERTION_ERROR;
import static com.google.common.truth.Truth.assertThat;
import static java.util.Arrays.asList;

import com.google.common.truth.FailureStrategy;
import com.google.common.truth.Subject;
import com.google.javascript.jscomp.CompilerOptions.LanguageMode;
import com.google.javascript.jscomp.testing.TestErrorManager;
import com.google.javascript.rhino.Node;

/**
 * This test is temporary. It asserts that the CodeGenerator produces the
 * right ES6_TYPED sources, even though those sources don't yet parse.
 * All these test cases should be migrated to a round-trip test as the parser
 * catches up.
 *
 * @author alexeagle@google.com (Alex Eagle)
 */

public final class Es6InlineTypesNotYetParsedTest extends CompilerTestCase {

  private Compiler compiler;

  @Override
  public void setUp() {
    setAcceptedLanguage(LanguageMode.ECMASCRIPT6);
    enableAstValidation(true);
    compiler = createCompiler();
  }

  @Override
  protected CompilerOptions getOptions() {
    CompilerOptions options = super.getOptions();
    options.setLanguageOut(LanguageMode.ECMASCRIPT6_TYPED);
    return options;
  }

  @Override
  public CompilerPass getProcessor(Compiler compiler) {
    return new ConvertToTypedES6(compiler);
  }

  @Override
  protected int getNumRepetitions() {
    return 1;
  }

  public void testNullType() {
    assertSource("/** @type {null} */ var n;")
        .transpilesTo("var n;");
  }

  public void testUntypedVarargs() {
    assertSource("/** @param {function(this:T, ...)} fn */ function f(fn) {}")
        .transpilesTo("function f(fn: (...p1) => any) {\n}\n;");
  }

  public void testAnyTypeVarargsParam() {
    assertSource("/** @param {...*} v */ function f(v){}")
        .transpilesTo("function f(...v: any[]) {\n}\n;");
  }

  public void testUnionWithUndefined() {
    assertSource("/** @param {Object|undefined} v */ function f(v){}")
        .transpilesTo("function f(v: Object) {\n}\n;");
  }

  public void testUnionWithNullAndUndefined() {
    assertSource("/** @param {null|undefined} v */ function f(v){}")
        .transpilesTo("function f(v) {\n}\n;");
  }

  public void testFunctionType() {
    assertSource("/** @type {function(string,number):boolean} */ var n;")
        .transpilesTo("var n: (p1:string, p2:number) => boolean;");
  }

  public void testTypeUnion() {
    assertSource("/** @type {(number|boolean)} */ var n;")
        .transpilesTo("var n: number | boolean;");
  }

  public void testArrayType() {
    assertSource("/** @type {Array.<string>} */ var s;")
        .transpilesTo("var s: string[];");
    assertSource("/** @type {!Array.<!$jscomp.typecheck.Checker>} */ var s;")
        .transpilesTo("var s: $jscomp.typecheck.Checker[];");
  }

  public void testRecordType() {
    assertSource("/** @type {{myNum: number, myObject}} */ var s;")
        .transpilesTo("var s: {myNum:number ; myObject};");
  }

  public void testParameterizedType() {
    assertSource("/** @type {MyCollection.<string>} */ var s;")
        .transpilesTo("var s: MyCollection<string>;");
    assertSource("/** @type {Object.<string, number>}  */ var s;")
        .transpilesTo("var s: Object<string, number>;");
    assertSource("/** @type {Object.<number>}  */ var s;")
        .transpilesTo("var s: Object<number>;");
  }

  public void testParameterizedTypeWithVoid() throws Exception {
    assertSource("/** @return {!goog.async.Deferred.<void>} */ f = function() {};")
        .transpilesTo("f = function(): goog.async.Deferred {\n};");
  }

  public void testOptionalParameterTypeWithUndefined() throws Exception {
    assertSource("/** @param {(null|undefined)=} opt_ignored */ f = function(opt_ignored) {};")
        .transpilesTo("f = function(opt_ignored) {\n};");
  }

  private SourceTranslationSubject assertSource(String... s) {
    return new SourceTranslationSubject(THROW_ASSERTION_ERROR, s);
  }

  private class SourceTranslationSubject
      extends Subject<SourceTranslationSubject, String[]> {

    public SourceTranslationSubject(FailureStrategy failureStrategy, String[] s)
    {
      super(failureStrategy, s);
    }

    private String doCompile(String... lines) {
      compiler.init(
          externsInputs,
          asList(SourceFile.fromCode("expected", LINE_JOINER.join(lines))),
          getOptions());
      compiler.setErrorManager(new TestErrorManager());
      Node root = compiler.parseInputs();
      getProcessor(compiler).process(root.getFirstChild(), root.getLastChild());
      return compiler.toSource();
    }

    public void transpilesTo(String... lines) {
      assertThat(doCompile(getSubject()).trim())
          .isEqualTo("'use strict';" + LINE_JOINER.join(lines));
    }
  }
}


File: test/com/google/javascript/jscomp/parsing/NewParserTest.java
/*
 * Copyright 2014 The Closure Compiler Authors.
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

import static com.google.common.truth.Truth.assertThat;
import static com.google.javascript.jscomp.parsing.IRFactory.MISPLACED_FUNCTION_ANNOTATION;
import static com.google.javascript.jscomp.parsing.IRFactory.MISPLACED_MSG_ANNOTATION;
import static com.google.javascript.jscomp.parsing.IRFactory.MISPLACED_TYPE_ANNOTATION;
import static com.google.javascript.jscomp.testing.NodeSubject.assertNode;

import com.google.common.base.Joiner;
import com.google.common.collect.ImmutableList;
import com.google.javascript.jscomp.parsing.Config.LanguageMode;
import com.google.javascript.jscomp.parsing.ParserRunner.ParseResult;
import com.google.javascript.rhino.JSDocInfo;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.SimpleSourceFile;
import com.google.javascript.rhino.StaticSourceFile;
import com.google.javascript.rhino.Token;
import com.google.javascript.rhino.testing.BaseJSTypeTestCase;
import com.google.javascript.rhino.testing.TestErrorReporter;

import java.util.List;

public final class NewParserTest extends BaseJSTypeTestCase {
  private static final String SUSPICIOUS_COMMENT_WARNING =
      IRFactory.SUSPICIOUS_COMMENT_WARNING;

  private static final String TRAILING_COMMA_MESSAGE =
      "Trailing comma is not legal in an ECMA-262 object initializer";

  private static final String MISSING_GT_MESSAGE =
      "Bad type annotation. missing closing >";

  private static final String UNLABELED_BREAK =
      "unlabelled break must be inside loop or switch";

  private static final String UNEXPECTED_CONTINUE =
      "continue must be inside loop";

  private static final String UNEXPECTED_RETURN =
      "return must be inside function";

  private static final String UNEXPECTED_LABELED_CONTINUE =
      "continue can only use labeles of iteration statements";

  private static final String UNDEFINED_LABEL = "undefined label";

  private static final String HTML_COMMENT_WARNING = "In some cases, '<!--' " +
      "and '-->' are treated as a '//' " +
      "for legacy reasons. Removing this from your code is " +
      "safe for all browsers currently in use.";

  private static final String ANNOTATION_DEPRECATED_WARNING =
      "The %s annotation is deprecated.%s";

  private Config.LanguageMode mode;
  private boolean isIdeMode = false;

  @Override
  protected void setUp() throws Exception {
    super.setUp();
    mode = LanguageMode.ECMASCRIPT3;
    isIdeMode = false;
  }

  public void testFunction() {
    parse("var f = function(x,y,z) { return 0; }");
    parse("function f(x,y,z) { return 0; }");

    parseError("var f = function(x,y,z,) {}",
        "Invalid trailing comma in formal parameter list");
    parseError("function f(x,y,z,) {}",
        "Invalid trailing comma in formal parameter list");
  }

  public void testWhile() {
    parse("while(1) { break; }");
  }

  public void testNestedWhile() {
    parse("while(1) { while(1) { break; } }");
  }

  public void testBreak() {
    parseError("break;", UNLABELED_BREAK);
  }

  public void testContinue() {
    parseError("continue;", UNEXPECTED_CONTINUE);
  }

  public void testBreakCrossFunction() {
    parseError("while(1) { function f() { break; } }", UNLABELED_BREAK);
  }

  public void testBreakCrossFunctionInFor() {
    parseError("while(1) {for(var f = function () { break; };;) {}}", UNLABELED_BREAK);
  }

  public void testBreakInForOf() {
    parse(""
        + "for (var x of [1, 2, 3]) {\n"
        + "  if (x == 2) break;\n"
        + "}");
  }

  public void testContinueToSwitch() {
    parseError("switch(1) {case(1): continue; }", UNEXPECTED_CONTINUE);
  }

  public void testContinueToSwitchWithNoCases() {
    parse("switch(1){}");
  }

  public void testContinueToSwitchWithTwoCases() {
    parseError("switch(1){case(1):break;case(2):continue;}", UNEXPECTED_CONTINUE);
  }

  public void testContinueToSwitchWithDefault() {
    parseError("switch(1){case(1):break;case(2):default:continue;}", UNEXPECTED_CONTINUE);
  }

  public void testContinueToLabelSwitch() {
    parseError(
        "while(1) {a: switch(1) {case(1): continue a; }}",
        UNEXPECTED_LABELED_CONTINUE);
  }

  public void testContinueOutsideSwitch() {
    parse("b: while(1) { a: switch(1) { case(1): continue b; } }");
  }

  public void testContinueNotCrossFunction1() {
    parse("a:switch(1){case(1):function f(){a:while(1){continue a;}}}");
  }

  public void testContinueNotCrossFunction2() {
    parseError(
        "a:switch(1){case(1):function f(){while(1){continue a;}}}",
        UNDEFINED_LABEL + " \"a\"");
  }

  public void testContinueInForOf() {
    parse(""
        + "for (var x of [1, 2, 3]) {\n"
        + "  if (x == 2) continue;\n"
        + "}");
  }

  public void testReturn() {
    parse("function foo() { return 1; }");
    parseError("return;", UNEXPECTED_RETURN);
    parseError("return 1;", UNEXPECTED_RETURN);
  }

  public void testThrow() {
    parse("throw Error();");
    parse("throw new Error();");
    parse("throw '';");
    parseError("throw;", "semicolon/newline not allowed after 'throw'");
    parseError("throw\nError();", "semicolon/newline not allowed after 'throw'");
  }

  public void testLabel1() {
    parse("foo:bar");
  }

  public void testLabel2() {
    parse("{foo:bar}");
  }

  public void testLabel3() {
    parse("foo:bar:baz");
  }

  public void testDuplicateLabelWithoutBraces() {
    parseError("foo:foo:bar", "Duplicate label \"foo\"");
  }

  public void testDuplicateLabelWithBraces() {
    parseError("foo:{bar;foo:baz}", "Duplicate label \"foo\"");
  }

  public void testDuplicateLabelWithFor() {
    parseError("foo:for(;;){foo:bar}", "Duplicate label \"foo\"");
  }

  public void testNonDuplicateLabelSiblings() {
    parse("foo:1;foo:2");
  }

  public void testNonDuplicateLabelCrossFunction() {
    parse("foo:(function(){foo:2})");
  }

  public void testLinenoCharnoAssign1() throws Exception {
    Node assign = parse("a = b").getFirstChild().getFirstChild();

    assertThat(assign.getType()).isEqualTo(Token.ASSIGN);
    assertThat(assign.getLineno()).isEqualTo(1);
    assertThat(assign.getCharno()).isEqualTo(0);
  }

  public void testLinenoCharnoAssign2() throws Exception {
    Node assign = parse("\n a.g.h.k    =  45").getFirstChild().getFirstChild();

    assertThat(assign.getType()).isEqualTo(Token.ASSIGN);
    assertThat(assign.getLineno()).isEqualTo(2);
    assertThat(assign.getCharno()).isEqualTo(1);
  }

  public void testLinenoCharnoCall() throws Exception {
    Node call = parse("\n foo(123);").getFirstChild().getFirstChild();

    assertThat(call.getType()).isEqualTo(Token.CALL);
    assertThat(call.getLineno()).isEqualTo(2);
    assertThat(call.getCharno()).isEqualTo(1);
  }

  public void testLinenoCharnoGetProp1() throws Exception {
    Node getprop = parse("\n foo.bar").getFirstChild().getFirstChild();

    assertThat(getprop.getType()).isEqualTo(Token.GETPROP);
    assertThat(getprop.getLineno()).isEqualTo(2);
    assertThat(getprop.getCharno()).isEqualTo(1);

    Node name = getprop.getFirstChild().getNext();
    assertThat(name.getType()).isEqualTo(Token.STRING);
    assertThat(name.getLineno()).isEqualTo(2);
    assertThat(name.getCharno()).isEqualTo(5);
  }

  public void testLinenoCharnoGetProp2() throws Exception {
    Node getprop = parse("\n foo.\nbar").getFirstChild().getFirstChild();

    assertThat(getprop.getType()).isEqualTo(Token.GETPROP);
    assertThat(getprop.getLineno()).isEqualTo(2);
    assertThat(getprop.getCharno()).isEqualTo(1);

    Node name = getprop.getFirstChild().getNext();
    assertThat(name.getType()).isEqualTo(Token.STRING);
    assertThat(name.getLineno()).isEqualTo(3);
    assertThat(name.getCharno()).isEqualTo(0);
  }

  public void testLinenoCharnoGetelem1() throws Exception {
    Node call = parse("\n foo[123]").getFirstChild().getFirstChild();

    assertThat(call.getType()).isEqualTo(Token.GETELEM);
    assertThat(call.getLineno()).isEqualTo(2);
    assertThat(call.getCharno()).isEqualTo(1);
  }

  public void testLinenoCharnoGetelem2() throws Exception {
    Node call = parse("\n   \n foo()[123]").getFirstChild().getFirstChild();

    assertThat(call.getType()).isEqualTo(Token.GETELEM);
    assertThat(call.getLineno()).isEqualTo(3);
    assertThat(call.getCharno()).isEqualTo(1);
  }

  public void testLinenoCharnoGetelem3() throws Exception {
    Node call = parse("\n   \n (8 + kl)[123]").getFirstChild().getFirstChild();

    assertThat(call.getType()).isEqualTo(Token.GETELEM);
    assertThat(call.getLineno()).isEqualTo(3);
    assertThat(call.getCharno()).isEqualTo(1);
  }

  public void testLinenoCharnoForComparison() throws Exception {
    Node lt =
      parse("for (; i < j;){}").getFirstChild().getFirstChild().getNext();

    assertThat(lt.getType()).isEqualTo(Token.LT);
    assertThat(lt.getLineno()).isEqualTo(1);
    assertThat(lt.getCharno()).isEqualTo(7);
  }

  public void testLinenoCharnoHook() throws Exception {
    Node n = parse("\n a ? 9 : 0").getFirstChild().getFirstChild();

    assertThat(n.getType()).isEqualTo(Token.HOOK);
    assertThat(n.getLineno()).isEqualTo(2);
    assertThat(n.getCharno()).isEqualTo(1);
  }

  public void testLinenoCharnoArrayLiteral() throws Exception {
    Node n = parse("\n  [8, 9]").getFirstChild().getFirstChild();

    assertThat(n.getType()).isEqualTo(Token.ARRAYLIT);
    assertThat(n.getLineno()).isEqualTo(2);
    assertThat(n.getCharno()).isEqualTo(2);

    n = n.getFirstChild();

    assertThat(n.getType()).isEqualTo(Token.NUMBER);
    assertThat(n.getLineno()).isEqualTo(2);
    assertThat(n.getCharno()).isEqualTo(3);

    n = n.getNext();

    assertThat(n.getType()).isEqualTo(Token.NUMBER);
    assertThat(n.getLineno()).isEqualTo(2);
    assertThat(n.getCharno()).isEqualTo(6);
  }

  public void testLinenoCharnoObjectLiteral() throws Exception {
    Node n = parse("\n\n var a = {a:0\n,b :1};")
        .getFirstChild().getFirstChild().getFirstChild();

    assertThat(n.getType()).isEqualTo(Token.OBJECTLIT);
    assertThat(n.getLineno()).isEqualTo(3);
    assertThat(n.getCharno()).isEqualTo(9);

    Node key = n.getFirstChild();

    assertThat(key.getType()).isEqualTo(Token.STRING_KEY);
    assertThat(key.getLineno()).isEqualTo(3);
    assertThat(key.getCharno()).isEqualTo(10);

    Node value = key.getFirstChild();

    assertThat(value.getType()).isEqualTo(Token.NUMBER);
    assertThat(value.getLineno()).isEqualTo(3);
    assertThat(value.getCharno()).isEqualTo(12);

    key = key.getNext();

    assertThat(key.getType()).isEqualTo(Token.STRING_KEY);
    assertThat(key.getLineno()).isEqualTo(4);
    assertThat(key.getCharno()).isEqualTo(1);

    value = key.getFirstChild();

    assertThat(value.getType()).isEqualTo(Token.NUMBER);
    assertThat(value.getLineno()).isEqualTo(4);
    assertThat(value.getCharno()).isEqualTo(4);
  }

  public void testLinenoCharnoAdd() throws Exception {
    testLinenoCharnoBinop("+");
  }

  public void testLinenoCharnoSub() throws Exception {
    testLinenoCharnoBinop("-");
  }

  public void testLinenoCharnoMul() throws Exception {
    testLinenoCharnoBinop("*");
  }

  public void testLinenoCharnoDiv() throws Exception {
    testLinenoCharnoBinop("/");
  }

  public void testLinenoCharnoMod() throws Exception {
    testLinenoCharnoBinop("%");
  }

  public void testLinenoCharnoShift() throws Exception {
    testLinenoCharnoBinop("<<");
  }

  public void testLinenoCharnoBinaryAnd() throws Exception {
    testLinenoCharnoBinop("&");
  }

  public void testLinenoCharnoAnd() throws Exception {
    testLinenoCharnoBinop("&&");
  }

  public void testLinenoCharnoBinaryOr() throws Exception {
    testLinenoCharnoBinop("|");
  }

  public void testLinenoCharnoOr() throws Exception {
    testLinenoCharnoBinop("||");
  }

  public void testLinenoCharnoLt() throws Exception {
    testLinenoCharnoBinop("<");
  }

  public void testLinenoCharnoLe() throws Exception {
    testLinenoCharnoBinop("<=");
  }

  public void testLinenoCharnoGt() throws Exception {
    testLinenoCharnoBinop(">");
  }

  public void testLinenoCharnoGe() throws Exception {
    testLinenoCharnoBinop(">=");
  }

  private void testLinenoCharnoBinop(String binop) {
    Node op = parse("var a = 89 " + binop + " 76;").getFirstChild().
        getFirstChild().getFirstChild();

    assertThat(op.getLineno()).isEqualTo(1);
    assertThat(op.getCharno()).isEqualTo(8);
  }

  public void testJSDocAttachment1() {
    Node varNode = parse("/** @type number */var a;").getFirstChild();

    // VAR
    assertThat(varNode.getType()).isEqualTo(Token.VAR);
    JSDocInfo varInfo = varNode.getJSDocInfo();
    assertThat(varInfo).isNotNull();
    assertTypeEquals(NUMBER_TYPE, varInfo.getType());

    // VAR NAME
    Node varNameNode = varNode.getFirstChild();
    assertThat(varNameNode.getType()).isEqualTo(Token.NAME);
    assertThat(varNameNode.getJSDocInfo()).isNull();

    mode = LanguageMode.ECMASCRIPT6;

    Node letNode = parse("/** @type number */let a;").getFirstChild();

    // LET
    assertThat(letNode.getType()).isEqualTo(Token.LET);
    JSDocInfo letInfo = letNode.getJSDocInfo();
    assertThat(letInfo).isNotNull();
    assertTypeEquals(NUMBER_TYPE, letInfo.getType());

    // LET NAME
    Node letNameNode = letNode.getFirstChild();
    assertThat(letNameNode.getType()).isEqualTo(Token.NAME);
    assertThat(letNameNode.getJSDocInfo()).isNull();

    Node constNode = parse("/** @type number */const a = 0;").getFirstChild();

    // CONST
    assertThat(constNode.getType()).isEqualTo(Token.CONST);
    JSDocInfo constInfo = constNode.getJSDocInfo();
    assertThat(constInfo).isNotNull();
    assertTypeEquals(NUMBER_TYPE, constInfo.getType());

    // LET NAME
    Node constNameNode = constNode.getFirstChild();
    assertThat(constNameNode.getType()).isEqualTo(Token.NAME);
    assertThat(constNameNode.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment2() {
    Node varNode = parse("/** @type number */var a,b;").getFirstChild();

    // VAR
    assertThat(varNode.getType()).isEqualTo(Token.VAR);
    JSDocInfo info = varNode.getJSDocInfo();
    assertThat(info).isNotNull();
    assertTypeEquals(NUMBER_TYPE, info.getType());

    // First NAME
    Node nameNode1 = varNode.getFirstChild();
    assertThat(nameNode1.getType()).isEqualTo(Token.NAME);
    assertThat(nameNode1.getJSDocInfo()).isNull();

    // Second NAME
    Node nameNode2 = nameNode1.getNext();
    assertThat(nameNode2.getType()).isEqualTo(Token.NAME);
    assertThat(nameNode2.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment3() {
    Node assignNode = parse(
        "/** @type number */goog.FOO = 5;").getFirstChild().getFirstChild();
    assertThat(assignNode.getType()).isEqualTo(Token.ASSIGN);
    JSDocInfo info = assignNode.getJSDocInfo();
    assertThat(info).isNotNull();
    assertTypeEquals(NUMBER_TYPE, info.getType());
  }

  public void testJSDocAttachment4() {
    Node varNode = parse(
        "var a, /** @define {number} */ b = 5;").getFirstChild();

    // ASSIGN
    assertThat(varNode.getType()).isEqualTo(Token.VAR);
    assertThat(varNode.getJSDocInfo()).isNull();

    // a
    Node a = varNode.getFirstChild();
    assertThat(a.getJSDocInfo()).isNull();

    // b
    Node b = a.getNext();
    JSDocInfo info = b.getJSDocInfo();
    assertThat(info).isNotNull();
    assertThat(info.isDefine()).isTrue();
    assertTypeEquals(NUMBER_TYPE, info.getType());
  }

  public void testJSDocAttachment5() {
    Node varNode = parse(
        "var /** @type number */a, /** @define {number} */b = 5;")
        .getFirstChild();

    // ASSIGN
    assertThat(varNode.getType()).isEqualTo(Token.VAR);
    assertThat(varNode.getJSDocInfo()).isNull();

    // a
    Node a = varNode.getFirstChild();
    assertThat(a.getJSDocInfo()).isNotNull();
    JSDocInfo info = a.getJSDocInfo();
    assertThat(info).isNotNull();
    assertThat(info.isDefine()).isFalse();
    assertTypeEquals(NUMBER_TYPE, info.getType());

    // b
    Node b = a.getNext();
    info = b.getJSDocInfo();
    assertThat(info).isNotNull();
    assertThat(info.isDefine()).isTrue();
    assertTypeEquals(NUMBER_TYPE, info.getType());
  }

  /**
   * Tests that a JSDoc comment in an unexpected place of the code does not
   * propagate to following code due to {@link JSDocInfo} aggregation.
   */
  public void testJSDocAttachment6() throws Exception {
    Node functionNode = parseWarning(
        "var a = /** @param {number} index */5;"
        + "/** @return boolean */function f(index){}",
        MISPLACED_FUNCTION_ANNOTATION)
        .getFirstChild().getNext();

    assertThat(functionNode.getType()).isEqualTo(Token.FUNCTION);
    JSDocInfo info = functionNode.getJSDocInfo();
    assertThat(info).isNotNull();
    assertThat(info.hasParameter("index")).isFalse();
    assertThat(info.hasReturnType()).isTrue();
    assertTypeEquals(UNKNOWN_TYPE, info.getReturnType());
  }

  public void testJSDocAttachment7() {
    Node varNode = parse("/** */var a;").getFirstChild();

    // VAR
    assertThat(varNode.getType()).isEqualTo(Token.VAR);

    // NAME
    Node nameNode = varNode.getFirstChild();
    assertThat(nameNode.getType()).isEqualTo(Token.NAME);
    assertThat(nameNode.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment8() {
    Node varNode = parse("/** x */var a;").getFirstChild();

    // VAR
    assertThat(varNode.getType()).isEqualTo(Token.VAR);

    // NAME
    Node nameNode = varNode.getFirstChild();
    assertThat(nameNode.getType()).isEqualTo(Token.NAME);
    assertThat(nameNode.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment9() {
    Node varNode = parse("/** \n x */var a;").getFirstChild();

    // VAR
    assertThat(varNode.getType()).isEqualTo(Token.VAR);

    // NAME
    Node nameNode = varNode.getFirstChild();
    assertThat(nameNode.getType()).isEqualTo(Token.NAME);
    assertThat(nameNode.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment10() {
    Node varNode = parse("/** x\n */var a;").getFirstChild();

    // VAR
    assertThat(varNode.getType()).isEqualTo(Token.VAR);

    // NAME
    Node nameNode = varNode.getFirstChild();
    assertThat(nameNode.getType()).isEqualTo(Token.NAME);
    assertThat(nameNode.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment11() {
    Node varNode =
       parse("/** @type {{x : number, 'y' : string, z}} */var a;")
        .getFirstChild();

    // VAR
    assertThat(varNode.getType()).isEqualTo(Token.VAR);
    JSDocInfo info = varNode.getJSDocInfo();
    assertThat(info).isNotNull();

    assertTypeEquals(
        createRecordTypeBuilder()
            .addProperty("x", NUMBER_TYPE, null)
            .addProperty("y", STRING_TYPE, null)
            .addProperty("z", UNKNOWN_TYPE, null)
            .build(),
        info.getType());

    // NAME
    Node nameNode = varNode.getFirstChild();
    assertThat(nameNode.getType()).isEqualTo(Token.NAME);
    assertThat(nameNode.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment12() {
    Node varNode =
       parse("var a = {/** @type {Object} */ b: c};")
        .getFirstChild();
    Node objectLitNode = varNode.getFirstChild().getFirstChild();
    assertThat(objectLitNode.getType()).isEqualTo(Token.OBJECTLIT);
    assertThat(objectLitNode.getFirstChild().getJSDocInfo()).isNotNull();
  }

  public void testJSDocAttachment13() {
    Node varNode = parse("/** foo */ var a;").getFirstChild();
    assertThat(varNode.getJSDocInfo()).isNotNull();
  }

  public void testJSDocAttachment14() {
    Node varNode = parse("/** */ var a;").getFirstChild();
    assertThat(varNode.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment15() {
    Node varNode = parse("/** \n * \n */ var a;").getFirstChild();
    assertThat(varNode.getJSDocInfo()).isNull();
  }

  public void testJSDocAttachment16() {
    Node exprCall =
        parse("/** @private */ x(); function f() {};").getFirstChild();
    assertThat(exprCall.getType()).isEqualTo(Token.EXPR_RESULT);
    assertThat(exprCall.getNext().getJSDocInfo()).isNull();
    assertThat(exprCall.getFirstChild().getJSDocInfo()).isNotNull();
  }

  public void testJSDocAttachment17() {
    Node fn =
        parseWarning(
            "function f() { " +
            "  return /** @type {string} */ (g(1 /** @desc x */));" +
            "};", MISPLACED_MSG_ANNOTATION).getFirstChild();
    assertThat(fn.getType()).isEqualTo(Token.FUNCTION);
    Node cast = fn.getLastChild().getFirstChild().getFirstChild();
    assertThat(cast.getType()).isEqualTo(Token.CAST);
  }

  public void testJSDocAttachment18() {
    Node fn =
        parse(
            "function f() { " +
            "  var x = /** @type {string} */ (y);" +
            "};").getFirstChild();
    assertThat(fn.getType()).isEqualTo(Token.FUNCTION);
    Node cast = fn.getLastChild().getFirstChild().getFirstChild().getFirstChild();
    assertThat(cast.getType()).isEqualTo(Token.CAST);
  }

  public void testJSDocAttachment19() {
    Node fn =
        parseWarning(
            "function f() { " +
            "  /** @type {string} */" +
            "  return;" +
            "};",
            MISPLACED_TYPE_ANNOTATION).getFirstChild();
    assertThat(fn.getType()).isEqualTo(Token.FUNCTION);

    Node ret = fn.getLastChild().getFirstChild();
    assertThat(ret.getType()).isEqualTo(Token.RETURN);
    assertThat(ret.getJSDocInfo()).isNotNull();
  }

  public void testJSDocAttachment20() {
    Node fn =
        parseWarning(
            "function f() { " +
            "  /** @type {string} */" +
            "  if (true) return;" +
            "};", MISPLACED_TYPE_ANNOTATION).getFirstChild();
    assertThat(fn.getType()).isEqualTo(Token.FUNCTION);

    Node ret = fn.getLastChild().getFirstChild();
    assertThat(ret.getType()).isEqualTo(Token.IF);
    assertThat(ret.getJSDocInfo()).isNotNull();
  }

  public void testJSDocAttachment21() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("/** @param {string} x */ const f = function() {};");
    parse("/** @param {string} x */ let f = function() {};");
  }

  // Tests that JSDoc gets attached to export nodes, and there are no warnings.
  // See https://github.com/google/closure-compiler/issues/781
  public void testJSDocAttachment22() {
    mode = LanguageMode.ECMASCRIPT6;

    Node n = parse("/** @param {string} x */ export function f(x) {};");
    Node export = n.getFirstChild();

    assertNode(export).hasType(Token.EXPORT);
    assertThat(export.getJSDocInfo()).isNotNull();
    assertThat(export.getJSDocInfo().hasParameter("x")).isTrue();
  }

  public void testInlineJSDocAttachment1() {
    Node fn = parse("function f(/** string */ x) {}").getFirstChild();
    assertThat(fn.isFunction()).isTrue();

    JSDocInfo info = fn.getFirstChild().getNext().getFirstChild().getJSDocInfo();
    assertThat(info).isNotNull();
    assertTypeEquals(STRING_TYPE, info.getType());
  }

  public void testInlineJSDocAttachment2() {
    Node fn = parse(
        "function f(/** ? */ x) {}").getFirstChild();
    assertThat(fn.isFunction()).isTrue();

    JSDocInfo info = fn.getFirstChild().getNext().getFirstChild().getJSDocInfo();
    assertThat(info).isNotNull();
    assertTypeEquals(UNKNOWN_TYPE, info.getType());
  }

  public void testInlineJSDocAttachment3() {
    parseWarning(
        "function f(/** @type {string} */ x) {}",
        "Bad type annotation. type not recognized due to syntax error");
  }

  public void testInlineJSDocAttachment4() {
    parseWarning(
        "function f(/**\n" +
        " * @type {string}\n" +
        " */ x) {}",
        "Bad type annotation. type not recognized due to syntax error");
  }

  public void testInlineJSDocAttachment5() {
    Node vardecl = parse("var /** string */ x = 'asdf';").getFirstChild();
    JSDocInfo info = vardecl.getFirstChild().getJSDocInfo();
    assertThat(info).isNotNull();
    assertThat(info.hasType()).isTrue();
    assertTypeEquals(STRING_TYPE, info.getType());
  }

  public void testInlineJSDocAttachment6() {
    Node fn = parse("function f(/** {attr: number} */ x) {}").getFirstChild();
    assertThat(fn.isFunction()).isTrue();

    JSDocInfo info = fn.getFirstChild().getNext().getFirstChild().getJSDocInfo();
    assertThat(info).isNotNull();
    assertTypeEquals(
        createRecordTypeBuilder().addProperty("attr", NUMBER_TYPE, null).build(), info.getType());
  }

  public void testInlineJSDocWithOptionalType() {
    Node fn = parse("function f(/** string= */ x) {}").getFirstChild();
    assertThat(fn.isFunction()).isTrue();

    JSDocInfo info = fn.getFirstChild().getNext().getFirstChild().getJSDocInfo();
    assertThat(info.getType().isOptionalArg()).isTrue();
  }

  public void testInlineJSDocWithVarArgs() {
    Node fn = parse("function f(/** ...string */ x) {}").getFirstChild();
    assertThat(fn.isFunction()).isTrue();

    JSDocInfo info = fn.getFirstChild().getNext().getFirstChild().getJSDocInfo();
    assertThat(info.getType().isVarArgs()).isTrue();
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing1() throws Exception {
    assertNodeEquality(
        parse("var a = [1,2]"),
        parseWarning("/** @type Array.<number*/var a = [1,2]",
            MISSING_GT_MESSAGE));
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing2() throws Exception {
    assertNodeEquality(
        parse("var a = [1,2]"),
        parseWarning("/** @type {Array.<number}*/var a = [1,2]",
            MISSING_GT_MESSAGE));
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing3() throws Exception {
    assertNodeEquality(
        parse("C.prototype.say=function(nums) {alert(nums.join(','));};"),
        parseWarning("/** @param {Array.<number} nums */" +
            "C.prototype.say=function(nums) {alert(nums.join(','));};",
            MISSING_GT_MESSAGE));
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing4() throws Exception {
    assertNodeEquality(
        parse("C.prototype.say=function(nums) {alert(nums.join(','));};"),
        parse("/** @return boolean */" +
            "C.prototype.say=function(nums) {alert(nums.join(','));};"));
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing5() throws Exception {
    assertNodeEquality(
        parse("C.prototype.say=function(nums) {alert(nums.join(','));};"),
        parse("/** @param boolean this is some string*/" +
            "C.prototype.say=function(nums) {alert(nums.join(','));};"));
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing6() throws Exception {
    assertNodeEquality(
        parse("C.prototype.say=function(nums) {alert(nums.join(','));};"),
        parseWarning("/** @param {bool!*%E$} */" +
            "C.prototype.say=function(nums) {alert(nums.join(','));};",
            "Bad type annotation. expected closing }",
            "Bad type annotation. expecting a variable name in a @param tag"));
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing7() throws Exception {
    isIdeMode = true;

    assertNodeEquality(
        parse("C.prototype.say=function(nums) {alert(nums.join(','));};"),
        parseWarning("/** @see */" +
            "C.prototype.say=function(nums) {alert(nums.join(','));};",
              "@see tag missing description"));
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing8() throws Exception {
    isIdeMode = true;

    assertNodeEquality(
        parse("C.prototype.say=function(nums) {alert(nums.join(','));};"),
        parseWarning("/** @author */" +
            "C.prototype.say=function(nums) {alert(nums.join(','));};",
              "@author tag missing author"));
  }

  public void testIncorrectJSDocDoesNotAlterJSParsing9() throws Exception {
    assertNodeEquality(
        parse("C.prototype.say=function(nums) {alert(nums.join(','));};"),
        parseWarning("/** @someillegaltag */" +
              "C.prototype.say=function(nums) {alert(nums.join(','));};",
              "illegal use of unknown JSDoc tag \"someillegaltag\";"
              + " ignoring it"));
  }

  public void testMisplacedDescAnnotation_noWarning() {
    parse("/** @desc Foo. */ var MSG_BAR = goog.getMsg('hello');");
    parse("/** @desc Foo. */ x.y.z.MSG_BAR = goog.getMsg('hello');");
    parse("/** @desc Foo. */ MSG_BAR = goog.getMsg('hello');");
    parse("var msgs = {/** @desc x */ MSG_X: goog.getMsg('x')}");
  }

  public void testMisplacedDescAnnotation() {
    parseWarning("/** @desc Foo. */ var bar = goog.getMsg('hello');",
        MISPLACED_MSG_ANNOTATION);
    parseWarning("/** @desc Foo. */ x.y.z.bar = goog.getMsg('hello');",
        MISPLACED_MSG_ANNOTATION);
    parseWarning("var msgs = {/** @desc x */ x: goog.getMsg('x')}",
        MISPLACED_MSG_ANNOTATION);
    parseWarning("/** @desc Foo. */ bar = goog.getMsg('x');",
        MISPLACED_MSG_ANNOTATION);
  }

  public void testUnescapedSlashInRegexpCharClass() {
    parse("var foo = /[/]/;");
    parse("var foo = /[hi there/]/;");
    parse("var foo = /[/yo dude]/;");
    parse("var foo = /\\/[@#$/watashi/wa/suteevu/desu]/;");
  }

  /**
   * Test for https://github.com/google/closure-compiler/issues/389.
   */
  public void testMalformedRegexp() {
    // Simple repro case
    String js = "var x = com\\";
    parseError(js, "Invalid escape sequence");

    // The original repro case as reported.
    js = Joiner.on('\n').join(
        "(function() {",
        "  var url=\"\";",
        "  switch(true)",
        "  {",
        "    case /a.com\\/g|l.i/N/.test(url):",
        "      return \"\";",
        "    case /b.com\\/T/.test(url):",
        "      return \"\";",
        "  }",
        "}",
        ")();");
    parseError(js, "primary expression expected");
  }

  private void assertNodeEquality(Node expected, Node found) {
    String message = expected.checkTreeEquals(found);
    if (message != null) {
      fail(message);
    }
  }

  @SuppressWarnings("unchecked")
  public void testParse() {
    mode = LanguageMode.ECMASCRIPT5;
    Node a = Node.newString(Token.NAME, "a");
    a.addChildToFront(Node.newString(Token.NAME, "b"));
    List<ParserResult> testCases = ImmutableList.of(
        new ParserResult(
            "3;",
            createScript(new Node(Token.EXPR_RESULT, Node.newNumber(3.0)))),
        new ParserResult(
            "var a = b;",
             createScript(new Node(Token.VAR, a)))
        );

    for (ParserResult testCase : testCases) {
      assertNodeEquality(testCase.node, parse(testCase.code));
    }
  }

  public void testAutomaticSemicolonInsertion() {
    // var statements
    assertNodeEquality(
        parse("var x = 1\nvar y = 2"),
        parse("var x = 1; var y = 2;"));
    assertNodeEquality(
        parse("var x = 1\n, y = 2"),
        parse("var x = 1, y = 2;"));

    // assign statements
    assertNodeEquality(
        parse("x = 1\ny = 2"),
        parse("x = 1; y = 2;"));

    // This fails because an EMPTY statement
    // is inserted after the 'x=1'.
    // TODO(tbreisacher): Fix and re-enable.
    //assertNodeEquality(
    //    parse("x = 1\n;y = 2"),
    //    parse("x = 1; y = 2;"));

    // if/else statements
    assertNodeEquality(
        parse("if (x)\n;else{}"),
        parse("if (x) {} else {}"));
  }

  /**
   * Test all the ASI examples from
   * http://www.ecma-international.org/ecma-262/5.1/#sec-7.9.2
   */
  public void testAutomaticSemicolonInsertionExamplesFromSpec() {
    parseError("{ 1 2 } 3", "Semi-colon expected");

    assertNodeEquality(
        parse("{ 1\n2 } 3"),
        parse("{ 1; 2; } 3;"));

    parseError("for (a; b\n)", "';' expected");

    assertNodeEquality(
        parse("function f() { return\na + b }"),
        parse("function f() { return; a + b; }"));

    assertNodeEquality(
        parse("a = b\n++c"),
        parse("a = b; ++c;"));

    parseError("if (a > b)\nelse c = d", "primary expression expected");

    assertNodeEquality(
        parse("a = b + c\n(d + e).print()"),
        parse("a = b + c(d + e).print()"));
  }

  private Node createScript(Node n) {
    Node script = new Node(Token.SCRIPT);
    script.addChildToBack(n);
    return script;
  }

  public void testMethodInObjectLiteral() {
    testMethodInObjectLiteral("var a = {b() {}};");
    testMethodInObjectLiteral("var a = {b() { alert('b'); }};");

    // Static methods not allowed in object literals.
    parseError("var a = {static b() { alert('b'); }};",
        "Cannot use keyword in short object literal");
  }

  private void testMethodInObjectLiteral(String js) {
    mode = LanguageMode.ECMASCRIPT6;
    parse(js);

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning(js, "this language feature is only supported in es6 mode:"
        + " member declarations");
  }

  public void testExtendedObjectLiteral() {
    testExtendedObjectLiteral("var a = {b};");
    testExtendedObjectLiteral("var a = {b, c};");
    testExtendedObjectLiteral("var a = {b, c: d, e};");

    parseError("var a = { '!@#$%' };", "':' expected");
    parseError("var a = { 123 };", "':' expected");
    parseError("var a = { let };", "Cannot use keyword in short object literal");
    parseError("var a = { else };", "Cannot use keyword in short object literal");
  }

  private void testExtendedObjectLiteral(String js) {
    mode = LanguageMode.ECMASCRIPT6;
    parse(js);

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning(js, "this language feature is only supported in es6 mode:"
        + " extended object literals");
  }

  public void testComputedPropertiesObjLit() {
    // Method
    testComputedProperty(Joiner.on('\n').join(
        "var x = {",
        "  [prop + '_']() {}",
        "}"));

    // Getter
    testComputedProperty(Joiner.on('\n').join(
        "var x = {",
        "  get [prop + '_']() {}",
        "}"));

    // Setter
    testComputedProperty(Joiner.on('\n').join(
        "var x = {",
        "  set [prop + '_'](val) {}",
        "}"));

    // Generator method
    mode = LanguageMode.ECMASCRIPT6;
    parse(Joiner.on('\n').join(
        "var x = {",
        "  *[prop + '_']() {}",
        "}"));

  }

  public void testComputedMethodClass() {
    mode = LanguageMode.ECMASCRIPT6;
    parse(Joiner.on('\n').join(
        "class X {",
        "  [prop + '_']() {}",
        "}"));

    parse(Joiner.on('\n').join(
        "class X {",
        "  static [prop + '_']() {}",
        "}"));
  }

  public void testComputedProperty() {
    testComputedProperty(Joiner.on('\n').join(
        "var prop = 'some complex expression';",
        "",
        "var x = {",
        "  [prop]: 'foo'",
        "}"));

    testComputedProperty(Joiner.on('\n').join(
        "var prop = 'some complex expression';",
        "",
        "var x = {",
        "  [prop + '!']: 'foo'",
        "}"));

    testComputedProperty(Joiner.on('\n').join(
        "var prop;",
        "",
        "var x = {",
        "  [prop = 'some expr']: 'foo'",
        "}"));

    testComputedProperty(Joiner.on('\n').join(
        "var x = {",
        "  [1 << 8]: 'foo'",
        "}"));

    String js = Joiner.on('\n').join(
        "var x = {",
        "  [1 << 8]: 'foo',",
        "  [1 << 7]: 'bar'",
        "}");
    mode = LanguageMode.ECMASCRIPT6;
    parse(js);
    mode = LanguageMode.ECMASCRIPT5;
    String warning = "this language feature is only supported in es6 mode:"
        + " computed property";
    parseWarning(js, warning, warning);
  }

  private void testComputedProperty(String js) {
    mode = LanguageMode.ECMASCRIPT6;
    parse(js);

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning(js, "this language feature is only supported in es6 mode:"
        + " computed property");
  }

  public void testTrailingCommaWarning1() {
    parse("var a = ['foo', 'bar'];");
  }

  public void testTrailingCommaWarning2() {
    parse("var a = ['foo',,'bar'];");
  }

  public void testTrailingCommaWarning3() {
    parseWarning("var a = ['foo', 'bar',];", TRAILING_COMMA_MESSAGE);
    mode = LanguageMode.ECMASCRIPT5;
    parse("var a = ['foo', 'bar',];");
  }

  public void testTrailingCommaWarning4() {
    parseWarning("var a = [,];", TRAILING_COMMA_MESSAGE);
    mode = LanguageMode.ECMASCRIPT5;
    parse("var a = [,];");
  }

  public void testTrailingCommaWarning5() {
    parse("var a = {'foo': 'bar'};");
  }

  public void testTrailingCommaWarning6() {
    parseWarning("var a = {'foo': 'bar',};", TRAILING_COMMA_MESSAGE);
    mode = LanguageMode.ECMASCRIPT5;
    parse("var a = {'foo': 'bar',};");
  }

  public void testTrailingCommaWarning7() {
    parseError("var a = {,};",
        "'}' expected");
  }

  public void testSuspiciousBlockCommentWarning1() {
    parseWarning("/* @type {number} */ var x = 3;", SUSPICIOUS_COMMENT_WARNING);
  }

  public void testSuspiciousBlockCommentWarning2() {
    parseWarning("/* \n * @type {number} */ var x = 3;",
        SUSPICIOUS_COMMENT_WARNING);
  }

  public void testSuspiciousBlockCommentWarning3() {
    parseWarning("/* \n *@type {number} */ var x = 3;",
        SUSPICIOUS_COMMENT_WARNING);
  }

  public void testSuspiciousBlockCommentWarning4() {
    parseWarning(
        "  /*\n" +
        "   * @type {number}\n" +
        "   */\n" +
        "  var x = 3;",
        SUSPICIOUS_COMMENT_WARNING);
  }

  public void testSuspiciousBlockCommentWarning5() {
    parseWarning(
        "  /*\n" +
        "   * some random text here\n" +
        "   * @type {number}\n" +
        "   */\n" +
        "  var x = 3;",
        SUSPICIOUS_COMMENT_WARNING);
  }

  public void testSuspiciousBlockCommentWarning6() {
    parseWarning("/* @type{number} */ var x = 3;", SUSPICIOUS_COMMENT_WARNING);
  }

  public void testSuspiciousBlockCommentWarning7() {
    // jsdoc tags contain letters only, no underscores etc.
    parse("/* @cc_on */ var x = 3;");
  }

  public void testSuspiciousBlockCommentWarning8() {
    // a jsdoc tag can't be immediately followed by a paren
    parse("/* @TODO(username) */ var x = 3;");
  }

  public void testCatchClauseForbidden() {
    parseError("try { } catch (e if true) {}",
        "')' expected");
  }

  public void testConstForbidden() {
    parseWarning("const x = 3;",
        "this language feature is only supported in es6 mode: " +
        "const declarations");
  }

  public void testAnonymousFunctionExpression() {
    mode = LanguageMode.ECMASCRIPT5;
    parseError("function () {}", "'identifier' expected");

    mode = LanguageMode.ECMASCRIPT6;
    parseError("function () {}", "'identifier' expected");
  }

  public void testArrayDestructuringVar() {
    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("var [x,y] = foo();",
        "this language feature is only supported in es6 mode: destructuring");
    parseWarning("[x,y] = foo();",
        "this language feature is only supported in es6 mode: destructuring");

    mode = LanguageMode.ECMASCRIPT6;
    parse("var [x,y] = foo();");
    parse("[x,y] = foo();");
  }

  public void testArrayDestructuringInitializer() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var [x=1,y] = foo();");
    parse("[x=1,y] = foo();");
    parse("var [x,y=2] = foo();");
    parse("[x,y=2] = foo();");

    parse("[[a] = ['b']] = [];");
  }

  public void testArrayDestructuringTrailingComma() {
    mode = LanguageMode.ECMASCRIPT6;
    parseError("var [x,] = ['x',];", "Array pattern may not end with a comma");
  }

  public void testArrayDestructuringRest() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var [first, ...rest] = foo();");
    parse("let [first, ...rest] = foo();");
    parse("const [first, ...rest] = foo();");

    parseError("var [first, ...more, last] = foo();", "']' expected");
    parseError("var [first, ...[re, st]] = foo();", "lvalues in rest elements must be identifiers");

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("var [first, ...rest] = foo();",
        "this language feature is only supported in es6 mode: destructuring");
  }

  public void testArrayDestructuringFnDeclaration() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("function f([x, y]) { use(x); use(y); }");
    parse("function f([x, [y, z]]) {}");
    parse("function f([x, y] = [1, 2]) { use(x); use(y); }");
    parse("function f([x, x]) {}");
  }

  public void testObjectDestructuringVar() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var {x, y} = foo();");
    parse("var {x: x, y: y} = foo();");
    parse("var {x: {y, z}} = foo();");
    parse("var {x: {y: {z}}} = foo();");

    // Useless, but legal.
    parse("var {} = foo();");
  }

  public void testObjectDestructuringVarWithInitializer() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var {x = 1} = foo();");
    parse("var {x: {y = 1}} = foo();");
    parse("var {x: y = 1} = foo();");
    parse("var {x: v1 = 5, y: v2 = 'str'} = foo();");
    parse("var {k1: {k2 : x} = bar(), k3: y} = foo();");
  }

  public void testObjectDestructuringAssign() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("({x, y}) = foo();");
    parse("({x, y} = foo());");
    parse("({x: x, y: y}) = foo();");
    parse("({x: x, y: y} = foo());");
    parse("({x: {y, z}}) = foo();");
    parse("({x: {y, z}} = foo());");
    parse("({k1: {k2 : x} = bar(), k3: y}) = foo();");
    parse("({k1: {k2 : x} = bar(), k3: y} = foo());");

    // Useless, but legal.
    parse("({}) = foo();");
    parse("({} = foo());");
  }

  public void testObjectDestructuringAssignWithInitializer() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("({x = 1}) = foo();");
    parse("({x = 1} = foo());");
    parse("({x: {y = 1}}) = foo();");
    parse("({x: {y = 1}} = foo());");
    parse("({x: y = 1}) = foo();");
    parse("({x: y = 1} = foo());");
    parse("({x: v1 = 5, y: v2 = 'str'}) = foo();");
    parse("({x: v1 = 5, y: v2 = 'str'} = foo());");
    parse("({k1: {k2 : x} = bar(), k3: y}) = foo();");
    parse("({k1: {k2 : x} = bar(), k3: y} = foo());");
  }

  public void testObjectDestructuringWithInitializerInvalid() {
    parseError("var {{x}} = foo();", "'}' expected");
    parseError("({{x}}) = foo();", "'}' expected");
    parseError("({{a} = {a: 'b'}}) = foo();", "'}' expected");
    parseError("({{a : b} = {a: 'b'}}) = foo();", "'}' expected");
  }

  public void testObjectDestructuringFnDeclaration() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("function f({x, y}) { use(x); use(y); }");
    parse("function f({w, x: {y, z}}) {}");
    parse("function f({x, y} = {x:1, y:2}) {}");
    parse("function f({x, x}) {}");
  }

  public void testObjectDestructuringComputedProp() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var {[x]: y} = z;");
    parse("var { [foo()] : [x,y,z] = bar() } = baz();");
    parseError("var {[x]} = z;", "':' expected");
  }

  public void testObjectDestructuringStringAndNumberKeys() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var {'s': x} = foo();");
    parse("var {3: x} = foo();");

    parseError("var { 'hello world' } = foo();", "':' expected");
    parseError("var { 4 } = foo();", "':' expected");
    parseError("var { 'hello' = 'world' } = foo();", "':' expected");
    parseError("var { 2 = 5 } = foo();", "':' expected");
  }

  public void testObjectDestructuringKeywordKeys() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var {if: x, else: y} = foo();");
    parse("var {while: x=1, for: y} = foo();");
    parseError("var {while} = foo();", "cannot use keyword 'while' here.");
    parseError("var {implements} = foo();", "cannot use keyword 'implements' here.");
  }

  public void testObjectDestructuringComplexTarget() {
    mode = LanguageMode.ECMASCRIPT6;
    parseError("var {foo: bar.x} = baz();", "'}' expected");
    parse("({foo: bar.x} = baz());");
    parse("for ({foo: bar.x} in baz());");

    parseError("var {foo: bar[x]} = baz();", "'}' expected");
    parse("({foo: bar[x]} = baz());");
    parse("for ({foo: bar[x]} in baz());");
  }

  public void testObjectDestructuringExtraParens() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("({x}) = y;");
    parse("(({x})) = y;");
    parse("((({x}))) = y;");

    parse("([x]) = y;");
    parse("[x, (y)] = z;");
    parse("[x, ([y])] = z;");
    parse("[x, (([y]))] = z;");
  }

  public void testMixedDestructuring() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var {x: [y, z]} = foo();");
    parse("var [x, {y, z}] = foo();");

    parse("({x: [y, z]} = foo());");
    parse("[x, {y, z}] = foo();");

    parse("function f({x: [y, z]}) {}");
    parse("function f([x, {y, z}]) {}");
  }

  public void testMixedDestructuringWithInitializer() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("var {x: [y, z] = [1, 2]} = foo();");
    parse("var [x, {y, z} = {y: 3, z: 4}] = foo();");

    parse("({x: [y, z] = [1, 2]} = foo());");
    parse("[x, {y, z} = {y: 3, z: 4}] = foo();");

    parse("function f({x: [y, z] = [1, 2]}) {}");
    parse("function f([x, {y, z} = {y: 3, z: 4}]) {}");
  }

  public void testDestructuringNoRHS() {
    mode = LanguageMode.ECMASCRIPT6;
    parseError("var {x: y};", "destructuring must have an initializer");
    parseError("let {x: y};", "destructuring must have an initializer");
    parseError("const {x: y};", "const variables must have an initializer");

    parseError("var {x};", "destructuring must have an initializer");
    parseError("let {x};", "destructuring must have an initializer");
    parseError("const {x};", "const variables must have an initializer");

    parseError("var [x, y];", "destructuring must have an initializer");
    parseError("let [x, y];", "destructuring must have an initializer");
    parseError("const [x, y];", "const variables must have an initializer");
  }

  public void testComprehensions() {
    mode = LanguageMode.ECMASCRIPT6;
    String error = "unsupported language feature:"
        + " array/generator comprehensions";

    // array comprehensions
    parseError("[for (x of y) z];", error);
    parseError("[for ({x,y} of z) x+y];", error);
    parseError("[for (x of y) if (x<10) z];", error);
    parseError("[for (a = 5 of v) a];", "'identifier' expected");

    // generator comprehensions
    parseError("(for (x of y) z);", error);
    parseError("(for ({x,y} of z) x+y);", error);
    parseError("(for (x of y) if (x<10) z);", error);
    parseError("(for (a = 5 of v) a);", "'identifier' expected");
  }

  public void testLetForbidden1() {
    parseWarning("let x = 3;",
        "this language feature is only supported in es6 mode:"
        + " let declarations");
  }

  public void testLetForbidden2() {
    parseWarning("function f() { let x = 3; };",
        "this language feature is only supported in es6 mode:"
        + " let declarations");
  }

  public void testLetForbidden3() {
    mode = LanguageMode.ECMASCRIPT5_STRICT;
    parseError("function f() { var let = 3; }",
        "'identifier' expected");

    mode = LanguageMode.ECMASCRIPT6_STRICT;
    parseError("function f() { var let = 3; }",
        "'identifier' expected");
  }

  public void testYieldForbidden() {
    parseError("function f() { yield 3; }",
        "primary expression expected");
  }

  public void testGenerator() {
    mode = LanguageMode.ECMASCRIPT6_STRICT;
    parse("var obj = { *f() { yield 3; } };");
    parse("function* f() { yield 3; }");
    parse("function f() { return function* g() {} }");

    mode = LanguageMode.ECMASCRIPT5_STRICT;
    parseWarning("function* f() { yield 3; }",
        "this language feature is only supported in es6 mode: generators");
    parseWarning("var obj = { * f() { yield 3; } };",
        "this language feature is only supported in es6 mode: generators",
        "this language feature is only supported in es6 mode: member declarations");
  }

  public void testBracelessFunctionForbidden() {
    parseError("var sq = function(x) x * x;",
        "'{' expected");
  }

  public void testGeneratorsForbidden() {
    parseError("var i = (x for (x in obj));",
        "')' expected");
  }

  public void testGettersForbidden1() {
    parseError("var x = {get foo() { return 3; }};",
        IRFactory.GETTER_ERROR_MESSAGE);
  }

  public void testGettersForbidden2() {
    parseError("var x = {get foo bar() { return 3; }};",
        "'(' expected");
  }

  public void testGettersForbidden3() {
    parseError("var x = {a getter:function b() { return 3; }};",
        "'}' expected");
  }

  public void testGettersForbidden4() {
    parseError("var x = {\"a\" getter:function b() { return 3; }};",
        "':' expected");
  }

  public void testGettersForbidden5() {
    parseError("var x = {a: 2, get foo() { return 3; }};",
        IRFactory.GETTER_ERROR_MESSAGE);
  }

  public void testGettersForbidden6() {
    parseError("var x = {get 'foo'() { return 3; }};",
        IRFactory.GETTER_ERROR_MESSAGE);
  }

  public void testSettersForbidden() {
    parseError("var x = {set foo(a) { y = 3; }};",
        IRFactory.SETTER_ERROR_MESSAGE);
  }

  public void testSettersForbidden2() {
    // TODO(johnlenz): maybe just report the first error, when not in IDE mode?
    parseError("var x = {a setter:function b() { return 3; }};",
        "'}' expected");
  }

  public void testFileOverviewJSDoc1() {
    isIdeMode = true;

    Node n = parse("/** @fileoverview Hi mom! */ function Foo() {}");
    assertThat(n.getFirstChild().getType()).isEqualTo(Token.FUNCTION);
    assertThat(n.getJSDocInfo()).isNotNull();
    assertThat(n.getFirstChild().getJSDocInfo()).isNull();
    assertThat(n.getJSDocInfo().getFileOverview()).isEqualTo("Hi mom!");
  }

  public void testFileOverviewJSDocDoesNotHoseParsing() {
    assertThat(parse("/** @fileoverview Hi mom! \n */ function Foo() {}").getFirstChild().getType())
        .isEqualTo(Token.FUNCTION);
    assertThat(
        parse("/** @fileoverview Hi mom! \n * * * */ function Foo() {}").getFirstChild().getType())
        .isEqualTo(Token.FUNCTION);
    assertThat(parse("/** @fileoverview \n * x */ function Foo() {}").getFirstChild().getType())
        .isEqualTo(Token.FUNCTION);
    assertThat(parse("/** @fileoverview \n * x \n */ function Foo() {}").getFirstChild().getType())
        .isEqualTo(Token.FUNCTION);
  }

  public void testFileOverviewJSDoc2() {
    isIdeMode = true;

    Node n = parse("/** @fileoverview Hi mom! */"
        + " /** @constructor */ function Foo() {}");
    assertThat(n.getJSDocInfo()).isNotNull();
    assertThat(n.getJSDocInfo().getFileOverview()).isEqualTo("Hi mom!");
    assertThat(n.getFirstChild().getJSDocInfo()).isNotNull();
    assertThat(n.getFirstChild().getJSDocInfo().hasFileOverview()).isFalse();
    assertThat(n.getFirstChild().getJSDocInfo().isConstructor()).isTrue();
  }

  public void testObjectLiteralDoc1() {
    Node n = parse("var x = {/** @type {number} */ 1: 2};");

    Node objectLit = n.getFirstChild().getFirstChild().getFirstChild();
    assertThat(objectLit.getType()).isEqualTo(Token.OBJECTLIT);

    Node number = objectLit.getFirstChild();
    assertThat(number.getType()).isEqualTo(Token.STRING_KEY);
    assertThat(number.getJSDocInfo()).isNotNull();
  }

  public void testDuplicatedParam() {
    parseWarning("function foo(x, x) {}", "Duplicate parameter name \"x\"");
  }

  public void testLetAsIdentifier() {
    mode = LanguageMode.ECMASCRIPT3;
    parse("var let");

    mode = LanguageMode.ECMASCRIPT5;
    parse("var let");

    mode = LanguageMode.ECMASCRIPT5_STRICT;
    parseError("var let", "'identifier' expected");

    mode = LanguageMode.ECMASCRIPT6;
    parse("var let");

    mode = LanguageMode.ECMASCRIPT6_STRICT;
    parseError("var let", "'identifier' expected");
  }

  public void testLet() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("let x;");
    parse("let x = 1;");
    parse("let x, y = 2;");
    parse("let x = 1, y = 2;");
  }

  public void testConst() {
    mode = LanguageMode.ECMASCRIPT6;

    parseError("const x;", "const variables must have an initializer");
    parse("const x = 1;");
    parseError("const x, y = 2;", "const variables must have an initializer");
    parse("const x = 1, y = 2;");
  }

  public void testYield1() {
    mode = LanguageMode.ECMASCRIPT3;
    parse("var yield");

    mode = LanguageMode.ECMASCRIPT5;
    parse("var yield");

    mode = LanguageMode.ECMASCRIPT5_STRICT;
    parseError("var yield", "'identifier' expected");

    mode = LanguageMode.ECMASCRIPT6;
    parse("var yield");

    mode = LanguageMode.ECMASCRIPT6_STRICT;
    parseError("var yield", "'identifier' expected");
  }

  public void testYield2() {
    mode = LanguageMode.ECMASCRIPT6_STRICT;
    parse("function * f() { yield; }");
    parse("function * f() { yield /a/i; }");

    parseError("function * f() { 1 + yield; }", "primary expression expected");
    parseError("function * f() { 1 + yield 2; }", "primary expression expected");
    parseError("function * f() { yield 1 + yield 2; }", "primary expression expected");
    parseError("function * f() { yield(1) + yield(2); }", "primary expression expected");
    parse("function * f() { (yield 1) + (yield 2); }"); // OK
    parse("function * f() { yield * yield; }"); // OK  (yield * (yield))
    parseError("function * f() { yield + yield; }", "primary expression expected");
    parse("function * f() { (yield) + (yield); }"); // OK
    parse("function * f() { return yield; }"); // OK
    parse("function * f() { return yield 1; }"); // OK
  }

  public void testYield3() {
    mode = LanguageMode.ECMASCRIPT6_STRICT;
    // TODO(johnlenz): validate "yield" parsing. Firefox rejects this
    // use of "yield".
    parseError("function * f() { yield , yield; }");
  }

  public void testStringLineContinuation() {
    mode = LanguageMode.ECMASCRIPT3;
    Node n = parseError("'one\\\ntwo';",
        "String continuations are not supported in this language mode.");
    assertThat(n.getFirstChild().getFirstChild().getString()).isEqualTo("onetwo");

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("'one\\\ntwo';", "String continuations are not recommended. See"
        + " https://google-styleguide.googlecode.com/svn/trunk/javascriptguide.xml#Multiline_string_literals");
    assertThat(n.getFirstChild().getFirstChild().getString()).isEqualTo("onetwo");

    mode = LanguageMode.ECMASCRIPT6;
    parseWarning("'one\\\ntwo';", "String continuations are not recommended. See"
        + " https://google-styleguide.googlecode.com/svn/trunk/javascriptguide.xml#Multiline_string_literals");
    assertThat(n.getFirstChild().getFirstChild().getString()).isEqualTo("onetwo");
  }

  public void testStringLiteral() {
    Node n = parse("'foo'");
    Node stringNode = n.getFirstChild().getFirstChild();
    assertThat(stringNode.getType()).isEqualTo(Token.STRING);
    assertThat(stringNode.getString()).isEqualTo("foo");
  }

  private Node testTemplateLiteral(String s) {
    mode = LanguageMode.ECMASCRIPT5;
    parseWarning(s,
        "this language feature is only supported in es6 mode: template literals");

    mode = LanguageMode.ECMASCRIPT6;
    return parse(s);
  }

  public void testUseTemplateLiteral() {
    testTemplateLiteral("f`hello world`;");
    testTemplateLiteral("`hello ${name} ${world}`.length;");
  }

  public void testTemplateLiteral() {
    testTemplateLiteral("``");
    testTemplateLiteral("`\"`");
    testTemplateLiteral("`\\\"`");
    testTemplateLiteral("`\\``");
    testTemplateLiteral("`hello world`;");
    testTemplateLiteral("`hello\nworld`;");
    testTemplateLiteral("`string containing \\`escaped\\` backticks`;");
    testTemplateLiteral("{ `in block` }");
    testTemplateLiteral("{ `in ${block}` }");
  }

  public void testTemplateLiteralWithLineContinuation() {
    mode = LanguageMode.ECMASCRIPT6;
    Node n = parseWarning("`string \\\ncontinuation`",
        "String continuations are not recommended. See"
        + " https://google-styleguide.googlecode.com/svn/trunk/javascriptguide.xml#Multiline_string_literals");
    Node templateLiteral = n.getFirstChild().getFirstChild();
    Node stringNode = templateLiteral.getFirstChild();
    assertThat(stringNode.getType()).isEqualTo(Token.STRING);
    assertThat(stringNode.getString()).isEqualTo("string continuation");
  }

  public void testTemplateLiteralSubstitution() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("`hello ${name}`;");
    parse("`hello ${name} ${world}`;");
    parse("`hello ${name }`");
    parseError("`hello ${name", "Expected '}' after expression in template literal");
    parseError("`hello ${name tail}", "Expected '}' after expression in template literal");
  }

  public void testUnterminatedTemplateLiteral() {
    mode = LanguageMode.ECMASCRIPT6;
    parseError("`hello",
        "Unterminated template literal");
    parseError("`hello\\`",
        "Unterminated template literal");
  }

  public void testIncorrectEscapeSequenceInTemplateLiteral() {
    parseError("`hello\\x",
        "Hex digit expected");
    parseError("`hello\\x`",
        "Hex digit expected");
  }

  public void testExponentialLiterals() {
    parse("0e0");
    parse("0E0");
    parse("0E1");
    parse("1E0");
    parse("1E-0");
    parse("10E10");
    parse("10E-10");
    parse("1.0E1");
    parseError("01E0",
        "Semi-colon expected");
    parseError("0E",
        "Exponent part must contain at least one digit");
    parseError("1E-",
        "Exponent part must contain at least one digit");
    parseError("1E1.1",
        "Semi-colon expected");
  }

  public void testBinaryLiterals() {
    mode = LanguageMode.ECMASCRIPT3;
    parseWarning("0b0001;",
        "Binary integer literals are not supported in this language mode.");
    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("0b0001;",
        "Binary integer literals are not supported in this language mode.");
    mode = LanguageMode.ECMASCRIPT6;
    parse("0b0001;");
  }

  public void testOctalLiterals() {
    mode = LanguageMode.ECMASCRIPT3;
    parseWarning("0o0001;",
        "Octal integer literals are not supported in this language mode.");
    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("0o0001;",
        "Octal integer literals are not supported in this language mode.");
    mode = LanguageMode.ECMASCRIPT6;
    parse("0o0001;");
  }

  public void testOldStyleOctalLiterals() {
    mode = LanguageMode.ECMASCRIPT3;
    parseWarning("0001;",
        "Octal integer literals are not supported in Ecmascript 5 strict mode.");

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("0001;",
        "Octal integer literals are not supported in Ecmascript 5 strict mode.");

    mode = LanguageMode.ECMASCRIPT6;
    parseWarning("0001;",
        "Octal integer literals are not supported in Ecmascript 5 strict mode.");
  }

  // TODO(tbreisacher): We need much clearer error messages for this case.
  public void testInvalidOctalLiterals() {
    mode = LanguageMode.ECMASCRIPT3;
    parseError("0o08;",
        "Semi-colon expected");

    mode = LanguageMode.ECMASCRIPT5;
    parseError("0o08;",
        "Semi-colon expected");

    mode = LanguageMode.ECMASCRIPT6;
    parseError("0o08;",
        "Semi-colon expected");
  }

  public void testInvalidOldStyleOctalLiterals() {
    mode = LanguageMode.ECMASCRIPT3;
    parseError("08;",
        "Invalid number literal.");

    mode = LanguageMode.ECMASCRIPT5;
    parseError("08;",
        "Invalid number literal.");

    mode = LanguageMode.ECMASCRIPT6;
    parseError("08;",
        "Invalid number literal.");
  }

  public void testGetter() {
    mode = LanguageMode.ECMASCRIPT3;
    parseError("var x = {get 1(){}};",
        IRFactory.GETTER_ERROR_MESSAGE);
    parseError("var x = {get 'a'(){}};",
        IRFactory.GETTER_ERROR_MESSAGE);
    parseError("var x = {get a(){}};",
        IRFactory.GETTER_ERROR_MESSAGE);
    mode = LanguageMode.ECMASCRIPT5;
    parse("var x = {get 1(){}};");
    parse("var x = {get 'a'(){}};");
    parse("var x = {get a(){}};");
    parseError("var x = {get a(b){}};", "')' expected");
  }

  public void testSetter() {
    mode = LanguageMode.ECMASCRIPT3;
    parseError("var x = {set 1(x){}};",
        IRFactory.SETTER_ERROR_MESSAGE);
    parseError("var x = {set 'a'(x){}};",
        IRFactory.SETTER_ERROR_MESSAGE);
    parseError("var x = {set a(x){}};",
        IRFactory.SETTER_ERROR_MESSAGE);
    mode = LanguageMode.ECMASCRIPT5;
    parse("var x = {set 1(x){}};");
    parse("var x = {set 'a'(x){}};");
    parse("var x = {set a(x){}};");
    parseError("var x = {set a(){}};",
        "'identifier' expected");
  }

  public void testLamestWarningEver() {
    // This used to be a warning.
    parse("var x = /** @type {undefined} */ (y);");
    parse("var x = /** @type {void} */ (y);");
  }

  public void testUnfinishedComment() {
    parseError("/** this is a comment ", "unterminated comment");
  }

  public void testHtmlStartCommentAtStartOfLine() {
    parseWarning("<!-- This text is ignored.\nalert(1)", HTML_COMMENT_WARNING);
  }

  public void testHtmlStartComment() {
    parseWarning("alert(1) <!-- This text is ignored.\nalert(2)",
        HTML_COMMENT_WARNING);
  }

  public void testHtmlEndCommentAtStartOfLine() {
    parseWarning("alert(1)\n --> This text is ignored.", HTML_COMMENT_WARNING);
  }

  // "-->" is not the start of a comment, when it is not at the beginning
  // of a line.
  public void testHtmlEndComment() {
    parse("while (x --> 0) {\n  alert(1)\n}");
  }

  public void testParseBlockDescription() {
    isIdeMode = true;

    Node n = parse("/** This is a variable. */ var x;");
    Node var = n.getFirstChild();
    assertThat(var.getJSDocInfo()).isNotNull();
    assertThat(var.getJSDocInfo().getBlockDescription()).isEqualTo("This is a variable.");
  }

  public void testUnnamedFunctionStatement() {
    // Statements
    parseError("function() {};", "'identifier' expected");
    parseError("if (true) { function() {}; }", "'identifier' expected");
    parse("function f() {};");
    // Expressions
    parse("(function f() {});");
    parse("(function () {});");
  }

  public void testReservedKeywords() {
    mode = LanguageMode.ECMASCRIPT3;

    parseError("var boolean;", "identifier is a reserved word");
    parseError("function boolean() {};",
        "identifier is a reserved word");
    parseError("boolean = 1;", "identifier is a reserved word");

    parseError("class = 1;", "'identifier' expected");
    parseError("public = 2;", "primary expression expected");

    mode = LanguageMode.ECMASCRIPT5;

    parse("var boolean;");
    parse("function boolean() {};");
    parse("boolean = 1;");

    parseError("class = 1;", "'identifier' expected");
    // TODO(johnlenz): reenable
    //parse("public = 2;");

    mode = LanguageMode.ECMASCRIPT5_STRICT;

    parse("var boolean;");
    parse("function boolean() {};");
    parse("boolean = 1;");
    parseError("public = 2;", "primary expression expected");

    parseError("class = 1;", "'identifier' expected");
  }

  public void testKeywordsAsProperties() {
    mode = LanguageMode.ECMASCRIPT3;

    parseWarning("var x = {function: 1};", IRFactory.INVALID_ES3_PROP_NAME);
    parseWarning("x.function;", IRFactory.INVALID_ES3_PROP_NAME);
    parseError("var x = {get x(){} };",
        IRFactory.GETTER_ERROR_MESSAGE);
    parseError("var x = {get function(){} };", IRFactory.GETTER_ERROR_MESSAGE);
    parseError("var x = {get 'function'(){} };",
        IRFactory.GETTER_ERROR_MESSAGE);
    parseError("var x = {get 1(){} };",
        IRFactory.GETTER_ERROR_MESSAGE);
    parseError("var x = {set function(a){} };", IRFactory.SETTER_ERROR_MESSAGE);
    parseError("var x = {set 'function'(a){} };",
        IRFactory.SETTER_ERROR_MESSAGE);
    parseError("var x = {set 1(a){} };",
        IRFactory.SETTER_ERROR_MESSAGE);
    parseWarning("var x = {class: 1};", IRFactory.INVALID_ES3_PROP_NAME);
    parse("var x = {'class': 1};");
    parseWarning("x.class;", IRFactory.INVALID_ES3_PROP_NAME);
    parse("x['class'];");
    parse("var x = {let: 1};");  // 'let' is not reserved in ES3
    parse("x.let;");
    parse("var x = {yield: 1};"); // 'yield' is not reserved in ES3
    parse("x.yield;");
    parseWarning("x.prototype.catch = function() {};",
        IRFactory.INVALID_ES3_PROP_NAME);
    parseWarning("x().catch();", IRFactory.INVALID_ES3_PROP_NAME);

    mode = LanguageMode.ECMASCRIPT5;

    parse("var x = {function: 1};");
    parse("x.function;");
    parse("var x = {get function(){} };");
    parse("var x = {get 'function'(){} };");
    parse("var x = {get 1(){} };");
    parse("var x = {set function(a){} };");
    parse("var x = {set 'function'(a){} };");
    parse("var x = {set 1(a){} };");
    parse("var x = {class: 1};");
    parse("x.class;");
    parse("var x = {let: 1};");
    parse("x.let;");
    parse("var x = {yield: 1};");
    parse("x.yield;");
    parse("x.prototype.catch = function() {};");
    parse("x().catch();");

    mode = LanguageMode.ECMASCRIPT5_STRICT;

    parse("var x = {function: 1};");
    parse("x.function;");
    parse("var x = {get function(){} };");
    parse("var x = {get 'function'(){} };");
    parse("var x = {get 1(){} };");
    parse("var x = {set function(a){} };");
    parse("var x = {set 'function'(a){} };");
    parse("var x = {set 1(a){} };");
    parse("var x = {class: 1};");
    parse("x.class;");
    parse("var x = {let: 1};");
    parse("x.let;");
    parse("var x = {yield: 1};");
    parse("x.yield;");
    parse("x.prototype.catch = function() {};");
    parse("x().catch();");
  }

  public void testKeywordsAsPropertiesInExterns1() {
    mode = LanguageMode.ECMASCRIPT3;

    parse("/** @fileoverview\n@externs\n*/\n var x = {function: 1};");
  }

  public void testKeywordsAsPropertiesInExterns2() {
    mode = LanguageMode.ECMASCRIPT3;

    parse("/** @fileoverview\n@externs\n*/\n var x = {}; x.function + 1;");
  }

  public void testUnicodeInIdentifiers() {
    parse("var \\u00fb");
    parse("Js\\u00C7ompiler");
    parse("Js\\u0043ompiler");
  }

  public void testUnicodePointEscapeInIdentifiers() {
    parse("var \\u{0043}");
    parse("Js\\u{0043}ompiler");
    parse("Js\\u{765}ompiler");
  }

  public void testUnicodePointEscapeStringLiterals() {
    parse("var i = \'\\u0043ompiler\'");
    parse("var i = \'\\u{43}ompiler\'");
    parse("var i = \'\\u{1f42a}ompiler\'");
    parse("var i = \'\\u{2603}ompiler\'");
    parse("var i = \'\\u{1}ompiler\'");
  }

  public void testInvalidUnicodePointEscapeInIdentifiers() {
    parseError("var \\u{defg", "Invalid escape sequence");
    parseError("var \\u{defgRestOfIdentifier", "Invalid escape sequence");
    parseError("var \\u{DEFG}", "Invalid escape sequence");
    parseError("Js\\u{}ompiler", "Invalid escape sequence");
    // Legal unicode but invalid in identifier
    parseError("Js\\u{99}ompiler", "Invalid escape sequence");
    parseError("Js\\u{10000}ompiler", "Invalid escape sequence");
  }

  public void testInvalidUnicodePointEscapeStringLiterals() {
    parseError("var i = \'\\u{defg\'", "Hex digit expected");
    parseError("var i = \'\\u{defgRestOfIdentifier\'", "Hex digit expected");
    parseError("var i = \'\\u{DEFG}\'", "Hex digit expected");
    parseError("var i = \'Js\\u{}ompiler\'", "Empty unicode escape");
    parseError("var i = \'\\u{345", "Hex digit expected");
  }

  public void testInvalidEscape() {
    parseError("var \\x39abc", "Invalid escape sequence");
    parseError("var abc\\t", "Invalid escape sequence");
  }

  public void testEOFInUnicodeEscape() {
    parseError("var \\u1", "Invalid escape sequence");
    parseError("var \\u12", "Invalid escape sequence");
    parseError("var \\u123", "Invalid escape sequence");
  }

  public void testEndOfIdentifierInUnicodeEscape() {
    parseError("var \\u1 = 1;", "Invalid escape sequence");
    parseError("var \\u12 = 2;", "Invalid escape sequence");
    parseError("var \\u123 = 3;", "Invalid escape sequence");
  }

  public void testInvalidUnicodeEscape() {
    parseError("var \\uDEFG", "Invalid escape sequence");
  }

  public void testUnicodeEscapeInvalidIdentifierStart() {
    parseError("var \\u0037yler",
        "Character '7' (U+0037) is not a valid identifier start char");
    parseError("var \\u{37}yler",
        "Character '7' (U+0037) is not a valid identifier start char");
    parseError("var \\u0020space",
        "Invalid escape sequence");
  }

  public void testUnicodeEscapeInvalidIdentifierChar() {
    parseError("var sp\\u0020ce",
        "Invalid escape sequence");
  }

  /**
   * It is illegal to use a keyword as an identifier, even if you use
   * unicode escapes to obscure the fact that you are trying do that.
   */
  public void testKeywordAsIdentifier() {
    parseError("var while;", "'identifier' expected");
    parseError("var wh\\u0069le;", "'identifier' expected");
  }

  public void testGetPropFunctionName() {
    parseError("function a.b() {}",
        "'(' expected");
    parseError("var x = function a.b() {}",
        "'(' expected");
  }

  public void testGetPropFunctionNameIdeMode() {
    // In IDE mode, we try to fix up the tree, but sometimes
    // this leads to even more errors.
    isIdeMode = true;
    parseError("function a.b() {}",
        "'(' expected",
        "',' expected",
        "Invalid trailing comma in formal parameter list");
    parseError("var x = function a.b() {}",
        "'(' expected",
        "',' expected",
        "Invalid trailing comma in formal parameter list");
  }

  public void testIdeModePartialTree() {
    Node partialTree = parseError("function Foo() {} f.",
        "'identifier' expected");
    assertThat(partialTree).isNull();

    isIdeMode = true;
    partialTree = parseError("function Foo() {} f.",
        "'identifier' expected");
    assertThat(partialTree).isNotNull();
  }

  public void testForEach() {
    parseError(
        "function f(stamp, status) {\n" +
        "  for each ( var curTiming in this.timeLog.timings ) {\n" +
        "    if ( curTiming.callId == stamp ) {\n" +
        "      curTiming.flag = status;\n" +
        "      break;\n" +
        "    }\n" +
        "  }\n" +
        "};",
        "'(' expected");
  }

  public void testMisplacedTypeAnnotation1() {
    // misuse with COMMA
    parseWarning(
        "var o = {};" +
        "/** @type {string} */ o.prop1 = 1, o.prop2 = 2;",
        MISPLACED_TYPE_ANNOTATION);
  }

  public void testMisplacedTypeAnnotation2() {
    // missing parentheses for the cast.
    parseWarning(
        "var o = /** @type {string} */ getValue();",
        MISPLACED_TYPE_ANNOTATION);
  }

  public void testMisplacedTypeAnnotation3() {
    // missing parentheses for the cast.
    parseWarning(
        "var o = 1 + /** @type {string} */ value;",
        MISPLACED_TYPE_ANNOTATION);
  }

  public void testMisplacedTypeAnnotation4() {
    // missing parentheses for the cast.
    parseWarning(
        "var o = /** @type {!Array.<string>} */ ['hello', 'you'];",
        MISPLACED_TYPE_ANNOTATION);
  }

  public void testMisplacedTypeAnnotation5() {
    // missing parentheses for the cast.
    parseWarning(
        "var o = (/** @type {!Foo} */ {});",
        MISPLACED_TYPE_ANNOTATION);
  }

  public void testMisplacedTypeAnnotation6() {
    parseWarning("var o = /** @type {function():string} */ function() {return 'str';}",
        MISPLACED_TYPE_ANNOTATION);
  }

  public void testValidTypeAnnotation1() {
    parse("/** @type {string} */ var o = 'str';");
    parse("var /** @type {string} */ o = 'str', /** @type {number} */ p = 0;");
    parse("/** @type {function():string} */ function o() { return 'str'; }");
    parse("var o = {}; /** @type {string} */ o.prop = 'str';");
    parse("var o = {}; /** @type {string} */ o['prop'] = 'str';");
    parse("var o = { /** @type {string} */ prop : 'str' };");
    parse("var o = { /** @type {string} */ 'prop' : 'str' };");
    parse("var o = { /** @type {string} */ 1 : 'str' };");
  }

  public void testValidTypeAnnotation2() {
    mode = LanguageMode.ECMASCRIPT5;
    parse("var o = { /** @type {string} */ get prop() { return 'str' }};");
    parse("var o = { /** @type {string} */ set prop(s) {}};");
  }

  public void testValidTypeAnnotation3() {
    // This one we don't currently support in the type checker but
    // we would like to.
    parse("try {} catch (/** @type {Error} */ e) {}");
  }

  public void testValidTypeAnnotation4() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("/** @type {number} */ export var x = 3;");
  }

  public void testParsingAssociativity() {
    assertNodeEquality(parse("x * y * z"), parse("(x * y) * z"));
    assertNodeEquality(parse("x + y + z"), parse("(x + y) + z"));
    assertNodeEquality(parse("x | y | z"), parse("(x | y) | z"));
    assertNodeEquality(parse("x & y & z"), parse("(x & y) & z"));
    assertNodeEquality(parse("x ^ y ^ z"), parse("(x ^ y) ^ z"));
    assertNodeEquality(parse("x || y || z"), parse("(x || y) || z"));
    assertNodeEquality(parse("x && y && z"), parse("(x && y) && z"));
  }

  public void testIssue1116() {
    parse("/**/");
  }

  public void testUnterminatedStringLiteral() {
    parseError("var unterm = 'forgot closing quote",
        "Unterminated string literal");

    parseError("var unterm = 'forgot closing quote\n"
        + "alert(unterm);",
        "Unterminated string literal");
  }

  /**
   * @bug 14231379
   */
  public void testUnterminatedRegExp() {
    parseError("var unterm = /forgot trailing slash",
        "Expected '/' in regular expression literal");

    parseError("var unterm = /forgot trailing slash\n" +
        "alert(unterm);",
        "Expected '/' in regular expression literal");
  }

  public void testRegExp() {
    assertNodeEquality(parse("/a/"), script(expr(regex("a"))));
    assertNodeEquality(parse("/\\\\/"), script(expr(regex("\\\\"))));
    assertNodeEquality(parse("/\\s/"), script(expr(regex("\\s"))));
    assertNodeEquality(parse("/\\u000A/"), script(expr(regex("\\u000A"))));
    assertNodeEquality(parse("/[\\]]/"), script(expr(regex("[\\]]"))));
  }

  public void testRegExpFlags() {
    // Various valid combinations.
    parse("/a/");
    parse("/a/i");
    parse("/a/g");
    parse("/a/m");
    parse("/a/ig");
    parse("/a/gm");
    parse("/a/mgi");

    // Invalid combinations
    parseError("/a/a", "Invalid RegExp flag 'a'");
    parseError("/a/b", "Invalid RegExp flag 'b'");
    parseError("/a/abc",
        "Invalid RegExp flag 'a'",
        "Invalid RegExp flag 'b'",
        "Invalid RegExp flag 'c'");
  }

  /**
   * New RegExp flags added in ES6.
   */
  public void testES6RegExpFlags() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("/a/y");
    parse("/a/u");

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("/a/y",
        "this language feature is only supported in es6 mode: new RegExp flag 'y'");
    parseWarning("/a/u",
        "this language feature is only supported in es6 mode: new RegExp flag 'u'");
    parseWarning("/a/yu",
        "this language feature is only supported in es6 mode: new RegExp flag 'y'",
        "this language feature is only supported in es6 mode: new RegExp flag 'u'");
  }

  public void testDefaultParameters() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("function f(a, b=0) {}");
    parse("function f(a, b=0, c) {}");

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("function f(a, b=0) {}",
        "this language feature is only supported in es6 mode: default parameters");
  }

  public void testDefaultParametersWithRestParameters() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("function f(a=0, ...b) {}");
    parse("function f(a, b=0, ...c) {}");
    parse("function f(a, b=0, c=1, ...d) {}");
  }

  public void testClass1() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("class C {}");

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("class C {}",
        "this language feature is only supported in es6 mode: class");

    mode = LanguageMode.ECMASCRIPT3;
    parseWarning("class C {}",
        "this language feature is only supported in es6 mode: class");

  }

  public void testClass2() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("class C {}");

    parse("class C {\n" +
          "  member() {}\n" +
          "  get field() {}\n" +
          "  set field(a) {}\n" +
          "}\n");

    parse("class C {\n" +
        "  static member() {}\n" +
        "  static get field() {}\n" +
        "  static set field(a) {}\n" +
        "}\n");
  }

  public void testClass3() {
    mode = LanguageMode.ECMASCRIPT6;
    parse("class C {\n" +
          "  member() {};\n" +
          "  get field() {};\n" +
          "  set field(a) {};\n" +
          "}\n");

    parse("class C {\n" +
        "  static member() {};\n" +
        "  static get field() {};\n" +
        "  static set field(a) {};\n" +
        "}\n");
  }

  public void testClassKeywordsAsMethodNames() {
    mode = LanguageMode.ECMASCRIPT6;
    parse(Joiner.on('\n').join(
        "class KeywordMethods {",
        "  continue() {}",
        "  throw() {}",
        "  else() {}",
        "}"));
  }

  public void testSuper1() {
    mode = LanguageMode.ECMASCRIPT6;

    // TODO(johnlenz): super in global scope should be a syntax error
    parse("super;");

    parse("function f() {super;};");

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("super;",
        "this language feature is only supported in es6 mode: super");

    mode = LanguageMode.ECMASCRIPT3;
    parseWarning("super;",
        "this language feature is only supported in es6 mode: super");
  }

  public void testArrow1() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("()=>1;");
    parse("()=>{}");
    parse("(a,b) => a + b;");
    parse("a => b");
    parse("a => { return b }");
    parse("a => b");

    mode = LanguageMode.ECMASCRIPT5;
    parseWarning("a => b",
        "this language feature is only supported in es6 mode: " +
        "short function syntax");

    mode = LanguageMode.ECMASCRIPT3;
    parseWarning("a => b;",
        "this language feature is only supported in es6 mode: " +
        "short function syntax");
  }

  public void testArrowInvalid() {
    mode = LanguageMode.ECMASCRIPT6;
    parseError("*()=>1;", "primary expression expected");
    parseError("var f = x\n=>2", "No newline allowed before '=>'");
    parseError("f = (x,y)\n=>2;", "No newline allowed before '=>'");
    parseError("f( (x,y)\n=>2)", "No newline allowed before '=>'");
  }

  public void testFor_ES5() {
    parse("for (var x; x != 10; x = next()) {}");
    parse("for (var x; x != 10; x = next());");
    parse("for (var x = 0; x != 10; x++) {}");
    parse("for (var x = 0; x != 10; x++);");

    parse("var x; for (x; x != 10; x = next()) {}");
    parse("var x; for (x; x != 10; x = next());");

    parseError("for (x in {};;) {}", "')' expected");
  }

  public void testFor_ES6() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("for (let x; x != 10; x = next()) {}");
    parse("for (let x; x != 10; x = next());");
    parse("for (let x = 0; x != 10; x++) {}");
    parse("for (let x = 0; x != 10; x++);");

    parseError("for (const x; x != 10; x = next()) {}", "const variables must have an initializer");
    parseError("for (const x; x != 10; x = next());", "const variables must have an initializer");
    parse("for (const x = 0; x != 10; x++) {}");
    parse("for (const x = 0; x != 10; x++);");
  }

  public void testForIn_ES6() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("for (a in b) c;");
    parse("for (var a in b) c;");
    parse("for (let a in b) c;");
    parse("for (const a in b) c;");

    parseError("for (a,b in c) d;", "';' expected");
    parseError("for (var a,b in c) d;",
        "for-in statement may not have more than one variable declaration");
    parseError("for (let a,b in c) d;",
        "for-in statement may not have more than one variable declaration");
    parseError("for (const a,b in c) d;",
        "for-in statement may not have more than one variable declaration");

    parseError("for (a=1 in b) c;", "';' expected");
    parseError("for (let a=1 in b) c;",
        "for-in statement may not have initializer");
    parseError("for (const a=1 in b) c;",
        "for-in statement may not have initializer");
    parseError("for (var a=1 in b) c;",
        "for-in statement may not have initializer");
  }

  public void testForIn_ES5() {
    mode = LanguageMode.ECMASCRIPT5;

    parse("for (a in b) c;");
    parse("for (var a in b) c;");

    parseError("for (a=1 in b) c;", "';' expected");
    parseWarning("for (var a=1 in b) c;",
        "for-in statement should not have initializer");
  }

  public void testForInDestructuring() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("for ({a} in b) c;");
    parse("for (var {a} in b) c;");
    parse("for (let {a} in b) c;");
    parse("for (const {a} in b) c;");

    parse("for ({a: b} in c) d;");
    parse("for (var {a: b} in c) d;");
    parse("for (let {a: b} in c) d;");
    parse("for (const {a: b} in c) d;");

    parse("for ([a] in b) c;");
    parse("for (var [a] in b) c;");
    parse("for (let [a] in b) c;");
    parse("for (const [a] in b) c;");

    parseError("for ({a: b} = foo() in c) d;", "';' expected");
    parseError("for (let {a: b} = foo() in c) d;",
        "for-in statement may not have initializer");
    parseError("for (const {a: b} = foo() in c) d;",
        "for-in statement may not have initializer");
    parseError("for (var {a: b} = foo() in c) d;",
        "for-in statement may not have initializer");

    parseError("for ([a] = foo() in b) c;",
        "';' expected");
    parseError("for (let [a] = foo() in b) c;",
        "for-in statement may not have initializer");
    parseError("for (const [a] = foo() in b) c;",
        "for-in statement may not have initializer");
    parseError("for (var [a] = foo() in b) c;",
        "for-in statement may not have initializer");
  }

  public void testForOf1() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("for(a of b) c;");
    parse("for(var a of b) c;");
    parse("for(let a of b) c;");
    parse("for(const a of b) c;");
  }

  public void testForOf2() {
    mode = LanguageMode.ECMASCRIPT6;

    parseError("for(a=1 of b) c;", "';' expected");
    parseError("for(var a=1 of b) c;",
        "for-of statement may not have initializer");
    parseError("for(let a=1 of b) c;",
        "for-of statement may not have initializer");
    parseError("for(const a=1 of b) c;",
        "for-of statement may not have initializer");
  }

  public void testForOf3() {
    mode = LanguageMode.ECMASCRIPT6;

    parseError("for(var a, b of c) d;",
        "for-of statement may not have more than one variable declaration");
    parseError("for(let a, b of c) d;",
        "for-of statement may not have more than one variable declaration");
    parseError("for(const a, b of c) d;",
        "for-of statement may not have more than one variable declaration");
  }

  public void testForOf4() {
    mode = LanguageMode.ECMASCRIPT6;

    parseError("for(a, b of c) d;", "';' expected");
  }

  public void testDestructuringInForLoops() {
    mode = LanguageMode.ECMASCRIPT6;

    // Destructuring forbids an initializer in for-in/for-of
    parseError("for (var {x: y} = foo() in bar()) {}",
        "for-in statement may not have initializer");
    parseError("for (let {x: y} = foo() in bar()) {}",
        "for-in statement may not have initializer");
    parseError("for (const {x: y} = foo() in bar()) {}",
        "for-in statement may not have initializer");

    parseError("for (var {x: y} = foo() of bar()) {}",
        "for-of statement may not have initializer");
    parseError("for (let {x: y} = foo() of bar()) {}",
        "for-of statement may not have initializer");
    parseError("for (const {x: y} = foo() of bar()) {}",
        "for-of statement may not have initializer");

    // but requires it in a vanilla for loop
    parseError("for (var {x: y};;) {}", "destructuring must have an initializer");
    parseError("for (let {x: y};;) {}", "destructuring must have an initializer");
    parseError("for (const {x: y};;) {}", "const variables must have an initializer");
  }

  public void testInvalidDestructuring() {
    mode = LanguageMode.ECMASCRIPT6;

    // {x: 5} and {x: 'str'} are valid object literals but not valid patterns.
    parseError("for ({x: 5} in foo()) {}", "Invalid LHS for a for-in loop");
    parseError("for ({x: 'str'} in foo()) {}", "Invalid LHS for a for-in loop");
    parseError("var {x: 5} = foo();", "'identifier' expected");
    parseError("var {x: 'str'} = foo();", "'identifier' expected");
    parseError("({x: 5} = foo());", "invalid assignment target");
    parseError("({x: 'str'} = foo());", "invalid assignment target");

    // {method(){}} is a valid object literal but not a valid object pattern.
    parseError("function f({method(){}}) {}", "'}' expected");
    parseError("function f({method(){}} = foo()) {}", "'}' expected");
  }

  public void testForOfPatterns() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("for({x} of b) c;");
    parse("for({x: y} of b) c;");
    parse("for([x, y] of b) c;");
    parse("for([x, ...y] of b) c;");

    parse("for(let {x} of b) c;");
    parse("for(let {x: y} of b) c;");
    parse("for(let [x, y] of b) c;");
    parse("for(let [x, ...y] of b) c;");

    parse("for(const {x} of b) c;");
    parse("for(const {x: y} of b) c;");
    parse("for(const [x, y] of b) c;");
    parse("for(const [x, ...y] of b) c;");

    parse("for(var {x} of b) c;");
    parse("for(var {x: y} of b) c;");
    parse("for(var [x, y] of b) c;");
    parse("for(var [x, ...y] of b) c;");
  }

  public void testForOfPatternsWithInitializer() {
    mode = LanguageMode.ECMASCRIPT6;

    parseError("for({x}=a of b) c;", "';' expected");
    parseError("for({x: y}=a of b) c;", "';' expected");
    parseError("for([x, y]=a of b) c;", "';' expected");
    parseError("for([x, ...y]=a of b) c;", "';' expected");

    parseError("for(let {x}=a of b) c;", "for-of statement may not have initializer");
    parseError("for(let {x: y}=a of b) c;", "for-of statement may not have initializer");
    parseError("for(let [x, y]=a of b) c;", "for-of statement may not have initializer");
    parseError("for(let [x, ...y]=a of b) c;", "for-of statement may not have initializer");

    parseError("for(const {x}=a of b) c;", "for-of statement may not have initializer");
    parseError("for(const {x: y}=a of b) c;", "for-of statement may not have initializer");
    parseError("for(const [x, y]=a of b) c;", "for-of statement may not have initializer");
    parseError("for(const [x, ...y]=a of b) c;", "for-of statement may not have initializer");
  }

  public void testImport() {
    mode = LanguageMode.ECMASCRIPT6;

    parse("import 'someModule'");
    parse("import d from './someModule'");
    parse("import {} from './someModule'");
    parse("import {x, y} from './someModule'");
    parse("import {x as x1, y as y1} from './someModule'");
    parse("import {x as x1, y as y1, } from './someModule'");
    parse("import * as sm from './someModule'");
  }

  public void testShebang() {
    parse("#!/usr/bin/node\n var x = 1;");
    parseError("var x = 1; \n #!/usr/bin/node",
        "primary expression expected");
  }


  public void testLookaheadGithubIssue699() {
    long start = System.currentTimeMillis();
    parse(
        "[1,[1,[1,[1,[1,[1,\n" +
        "[1,[1,[1,[1,[1,[1,\n" +
        "[1,[1,[1,[1,[1,[1,\n" +
        "[1,[1,[1,[1,[1,[1,\n" +
        "[1,[1,[1,[1,[1,[1,\n" +
        "[1,[1,\n" +
        "[1]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]] ");

    long stop = System.currentTimeMillis();

    assertThat(stop - start).named("runtime").isLessThan(5000L);
  }

  public void testInvalidHandling1() {
    parse(""
        + "/**\n"
        + " * @fileoverview Definition.\n"
        + " * @mods {ns.bar}\n"
        + " * @modName mod\n"
        + " *\n"
        + " * @extends {ns.bar}\n"
        + " * @author someone\n"
        + " */\n"
        + "\n"
        + "goog.provide('ns.foo');\n"
        + "");
  }

  public void testExposeDeprecated() {
    parseWarning("/** @expose */ var x = 0;",
        String.format(ANNOTATION_DEPRECATED_WARNING, "@expose",
            " Use @nocollapse or @export instead."));
  }

  private Node script(Node stmt) {
    Node n = new Node(Token.SCRIPT, stmt);
    n.setIsSyntheticBlock(true);
    return n;
  }

  private Node expr(Node n) {
    return new Node(Token.EXPR_RESULT, n);
  }

  private Node regex(String regex) {
    return new Node(Token.REGEXP, Node.newString(regex));
  }

  /**
   * Verify that the given code has the given parse errors.
   * @return If in IDE mode, returns a partial tree.
   */
  private Node parseError(String source, String... errors) {
    TestErrorReporter testErrorReporter = new TestErrorReporter(errors, null);
    ParseResult result = ParserRunner.parse(
        new SimpleSourceFile("input", false),
        source,
        ParserRunner.createConfig(isIdeMode, mode, false, null),
        testErrorReporter);
    Node script = result.ast;

    // verifying that all errors were seen
    testErrorReporter.assertHasEncounteredAllErrors();
    testErrorReporter.assertHasEncounteredAllWarnings();

    return script;
  }


  /**
   * Verify that the given code has the given parse warnings.
   * @return The parse tree.
   */
  private Node parseWarning(String string, String... warnings) {
    TestErrorReporter testErrorReporter = new TestErrorReporter(null, warnings);
    StaticSourceFile file = new SimpleSourceFile("input", false);
    Node script = ParserRunner.parse(
        file,
        string,
        ParserRunner.createConfig(isIdeMode, mode, false, null),
        testErrorReporter).ast;

    // verifying that all warnings were seen
    testErrorReporter.assertHasEncounteredAllErrors();
    testErrorReporter.assertHasEncounteredAllWarnings();

    return script;
  }

  /**
   * Verify that the given code has no parse warnings or errors.
   * @return The parse tree.
   */
  private Node parse(String string) {
    return parseWarning(string);
  }

  private static class ParserResult {
    private final String code;
    private final Node node;

    private ParserResult(String code, Node node) {
      this.code = code;
      this.node = node;
    }
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
import static com.google.javascript.rhino.Token.REST_PARAMETER_TYPE;
import static com.google.javascript.rhino.Token.STRING_TYPE;
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
    Node stringKey = IR.stringKey("p1");
    stringKey.addChildToFront(stringType());
    Node stringKey1 = IR.stringKey("p2");
    stringKey1.addChildToFront(booleanType());
    assertParseTypeAndConvert("function(string, boolean)")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, anyType(), stringKey, stringKey1));
  }

  public void testConvertFunctionReturnType() throws Exception {
    assertParseTypeAndConvert("function(): number")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, numberType()));
  }

  public void testConvertFunctionThisType() throws Exception {
    Node stringKey1 = IR.stringKey("p1");
    stringKey1.addChildToFront(stringType());
    assertParseTypeAndConvert("function(this:goog.ui.Menu, string)")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, anyType(), stringKey1));
  }

  public void testConvertFunctionNewType() throws Exception {
    Node stringKey1 = IR.stringKey("p1");
    stringKey1.addChildToFront(stringType());
    assertParseTypeAndConvert("function(new:goog.ui.Menu, string)")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, anyType(), stringKey1));
  }

  public void testConvertVariableParameters() throws Exception {
    Node stringKey1 = IR.stringKey("p1");
    stringKey1.addChildToFront(stringType());
    Node stringKey2 = IR.stringKey("p2");
    stringKey2.addChildToFront(arrayType(numberType()));
    assertParseTypeAndConvert("function(string, ...number): number")
        .isEqualTo(new TypeDeclarationNode(FUNCTION_TYPE, numberType(),
            stringKey1, new TypeDeclarationNode(REST_PARAMETER_TYPE, stringKey2)));
  }

  public void testConvertOptionalFunctionParameters() throws Exception {
    LinkedHashMap<String, TypeDeclarationNode> parameters = new LinkedHashMap<>();
    parameters.put("p1", optionalParameter(stringType()));
    parameters.put("p2", optionalParameter(numberType()));
    assertParseTypeAndConvert("function(?string=, number=)")
        .isEqualTo(functionType(anyType(), parameters, null, null));
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


File: test/com/google/javascript/jscomp/parsing/TypeSyntaxTest.java
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

import static com.google.common.truth.Truth.assertThat;
import static com.google.javascript.jscomp.testing.NodeSubject.assertNode;
import static com.google.javascript.rhino.TypeDeclarationsIR.anyType;
import static com.google.javascript.rhino.TypeDeclarationsIR.arrayType;
import static com.google.javascript.rhino.TypeDeclarationsIR.booleanType;
import static com.google.javascript.rhino.TypeDeclarationsIR.namedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.numberType;
import static com.google.javascript.rhino.TypeDeclarationsIR.parameterizedType;
import static com.google.javascript.rhino.TypeDeclarationsIR.stringType;
import static com.google.javascript.rhino.TypeDeclarationsIR.voidType;

import com.google.common.collect.ImmutableList;
import com.google.javascript.jscomp.CodePrinter;
import com.google.javascript.jscomp.Compiler;
import com.google.javascript.jscomp.CompilerOptions;
import com.google.javascript.jscomp.CompilerOptions.LanguageMode;
import com.google.javascript.jscomp.SourceFile;
import com.google.javascript.jscomp.testing.TestErrorManager;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.Node.TypeDeclarationNode;
import com.google.javascript.rhino.Token;

import junit.framework.TestCase;

/**
 * Tests the AST generated when parsing code that includes type declarations
 * in the syntax.
 * <p>
 * (It tests both parsing from source to a parse tree, and conversion from a
 * parse tree to an AST in {@link IRFactory}
 * and {@link TypeDeclarationsIRFactory}.)
 *
 * @author martinprobst@google.com (Martin Probst)
 */
public final class TypeSyntaxTest extends TestCase {

  private TestErrorManager testErrorManager;

  @Override
  protected void setUp() throws Exception {
    super.setUp();
    testErrorManager = new TestErrorManager();
  }

  private void expectErrors(String... errors) {
    testErrorManager.expectErrors(errors);
  }

  private void testNotEs6Typed(String source, String... features) {
    for (int i = 0; i < features.length; i++) {
      features[i] =
          "type syntax is only supported in ES6 typed mode: "
              + features[i]
              + ". Use --language_in=ECMASCRIPT6_TYPED to enable ES6 typed features.";
    }
    expectErrors(features);
    parse(source, LanguageMode.ECMASCRIPT6);
    expectErrors(features);
    parse(source, LanguageMode.ECMASCRIPT6_STRICT);
  }

  public void testVariableDeclaration() {
    assertVarType("any", anyType(), "var foo: any = 'hello';");
    assertVarType("number", numberType(), "var foo: number = 'hello';");
    assertVarType("boolean", booleanType(), "var foo: boolean = 'hello';");
    assertVarType("string", stringType(), "var foo: string = 'hello';");
    assertVarType("void", voidType(), "var foo: void = 'hello';");
    assertVarType("named type", namedType("hello"), "var foo: hello = 'hello';");
  }

  public void testVariableDeclaration_keyword() {
    expectErrors("Parse error. Unexpected token 'catch' in type expression");
    parse("var foo: catch;");
    expectErrors("Parse error. Unexpected token 'implements' in type expression");
    parse("var foo: implements;"); // strict mode keyword
  }

  public void testVariableDeclaration_errorIncomplete() {
    expectErrors("Parse error. Unexpected token '=' in type expression");
    parse("var foo: = 'hello';");
  }

  public void testTypeInDocAndSyntax() {
    expectErrors("Parse error. Bad type syntax - "
        + "can only have JSDoc or inline type annotations, not both");
    parse("var /** string */ foo: string = 'hello';");
  }

  public void testFunctionParamDeclaration() {
    Node fn = parse("function foo(x: string) {\n}").getFirstChild();
    Node param = fn.getFirstChild().getNext().getFirstChild();
    assertDeclaredType("string type", stringType(), param);
  }

  public void testFunctionParamDeclaration_defaultValue() {
    Node fn = parse("function foo(x: string = 'hello') {\n}").getFirstChild();
    Node param = fn.getFirstChild().getNext().getFirstChild();
    assertDeclaredType("string type", stringType(), param);
  }

  public void testFunctionParamDeclaration_destructuringArray() {
    // TODO(martinprobst): implement.
    expectErrors("Parse error. ',' expected");
    parse("function foo([x]: string) {}");
  }

  public void testFunctionParamDeclaration_destructuringArrayInner() {
    // TODO(martinprobst): implement.
    expectErrors("Parse error. ']' expected");
    parse("function foo([x: string]) {}");
  }

  public void testFunctionParamDeclaration_destructuringObject() {
    // TODO(martinprobst): implement.
    expectErrors("Parse error. ',' expected");
    parse("function foo({x}: string) {}");
  }

  public void testFunctionParamDeclaration_arrow() {
    Node fn = parse("(x: string) => 'hello' + x;").getFirstChild().getFirstChild();
    Node param = fn.getFirstChild().getNext().getFirstChild();
    assertDeclaredType("string type", stringType(), param);
  }

  public void testFunctionReturn() {
    Node fn = parse("function foo(): string {\n  return 'hello';\n}").getFirstChild();
    assertDeclaredType("string type", stringType(), fn);
  }

  public void testFunctionReturn_arrow() {
    Node fn = parse("(): string => 'hello';").getFirstChild().getFirstChild();
    assertDeclaredType("string type", stringType(), fn);
  }

  public void testFunctionReturn_typeInDocAndSyntax() throws Exception {
    expectErrors("Parse error. Bad type syntax - "
        + "can only have JSDoc or inline type annotations, not both");
    parse("function /** string */ foo(): string { return 'hello'; }");
  }

  public void testFunctionReturn_typeInJsdocOnly() throws Exception {
    parse("function /** string */ foo() { return 'hello'; }",
        "function/** string */foo() {\n  return 'hello';\n}");
  }

  public void testCompositeType() {
    Node varDecl = parse("var foo: mymod.ns.Type;").getFirstChild();
    TypeDeclarationNode expected = namedType(ImmutableList.of("mymod", "ns", "Type"));
    assertDeclaredType("mymod.ns.Type", expected, varDecl.getFirstChild());
  }

  public void testCompositeType_trailingDot() {
    expectErrors("Parse error. 'identifier' expected");
    parse("var foo: mymod.Type.;");
  }

  public void testArrayType() {
    TypeDeclarationNode arrayOfString = arrayType(stringType());
    assertVarType("string[]", arrayOfString, "var foo: string[];");
  }

  public void testArrayType_empty() {
    expectErrors("Parse error. Unexpected token '[' in type expression");
    parse("var x: [];");
  }

  public void testArrayType_missingClose() {
    expectErrors("Parse error. ']' expected");
    parse("var foo: string[;");
  }

  public void testArrayType_qualifiedType() {
    TypeDeclarationNode arrayOfString = arrayType(namedType("mymod.ns.Type"));
    assertVarType("string[]", arrayOfString, "var foo: mymod.ns.Type[];");
  }

  public void testArrayType_trailingParameterizedType() {
    expectErrors("Parse error. Semi-colon expected");
    parse("var x: Foo[]<Bar>;");
  }

  public void testParameterizedType() {
    TypeDeclarationNode parameterizedType =
        parameterizedType(
            namedType("my.parameterized.Type"),
            ImmutableList.of(
                namedType("ns.A"),
                namedType("ns.B")));
    assertVarType("parameterized type 2 args", parameterizedType,
        "var x: my.parameterized.Type<ns.A, ns.B>;");
  }

  public void testParameterizedType_empty() {
    expectErrors("Parse error. Unexpected token '>' in type expression");
    parse("var x: my.parameterized.Type<ns.A, >;");
  }

  public void testParameterizedType_noArgs() {
    expectErrors("Parse error. Unexpected token '>' in type expression");
    parse("var x: my.parameterized.Type<>;");
  }

  public void testParameterizedType_trailing1() {
    expectErrors("Parse error. '>' expected");
    parse("var x: my.parameterized.Type<ns.A;");
  }

  public void testParameterizedType_trailing2() {
    expectErrors("Parse error. Unexpected token ';' in type expression");
    parse("var x: my.parameterized.Type<ns.A,;");
  }

  public void testParameterizedArrayType() {
    parse("var x: Foo<Bar>[];");
  }

  public void testUnionType() {
    parse("var x: string | number[];");
    parse("var x: number[] | string;");
    parse("var x: Array<Foo> | number[];");
    parse("var x: (string | number)[];");

    Node ast = parse("var x: string | number[] | Array<Foo>;");
    TypeDeclarationNode union = (TypeDeclarationNode)
        (ast.getFirstChild().getFirstChild().getProp(Node.DECLARED_TYPE_EXPR));
    assertEquals(3, union.getChildCount());
  }

  public void testUnionType_empty() {
    expectErrors("Parse error. Unexpected token '|' in type expression");
    parse("var x: |;");
    expectErrors("Parse error. 'identifier' expected");
    parse("var x: number |;");
    expectErrors("Parse error. Unexpected token '|' in type expression");
    parse("var x: | number;");
  }

  public void testUnionType_trailingParameterizedType() {
    expectErrors("Parse error. Semi-colon expected");
    parse("var x: (Foo|Bar)<T>;");
  }

  public void testUnionType_notEs6Typed() {
    testNotEs6Typed("var x: string | number[] | Array<Foo>;", "type annotation");
  }

  public void testParenType_empty() {
    expectErrors("Parse error. Unexpected token ')' in type expression");
    parse("var x: ();");
  }

  public void testFunctionType() {
    parse("var n: (p1:string) => boolean;");
    parse("var n: (p1:string, p2:number) => boolean;");
    parse("var n: () => () => number;");
    parse("(number): () => number => number;");

    Node ast = parse("var n: (p1:string, p2:number) => boolean[];");
    TypeDeclarationNode function = (TypeDeclarationNode)
        (ast.getFirstChild().getFirstChild().getProp(Node.DECLARED_TYPE_EXPR));
    assertNode(function).hasType(Token.FUNCTION_TYPE);

    Node ast2 = parse("var n: (p1:string, p2:number) => boolean | number;");
    TypeDeclarationNode function2 = (TypeDeclarationNode)
        (ast2.getFirstChild().getFirstChild().getProp(Node.DECLARED_TYPE_EXPR));
    assertNode(function2).hasType(Token.FUNCTION_TYPE);

    Node ast3 = parse("var n: (p1:string, p2:number) => Array<Foo>;");
    TypeDeclarationNode function3 = (TypeDeclarationNode)
        (ast3.getFirstChild().getFirstChild().getProp(Node.DECLARED_TYPE_EXPR));
    assertNode(function3).hasType(Token.FUNCTION_TYPE);
  }

  public void testFunctionType_incomplete() {
    expectErrors("Parse error. Unexpected token ';' in type expression");
    parse("var n: (p1:string) =>;");
    expectErrors("Parse error. Unexpected token '{' in type expression");
    parse("var n: (p1:string) => {};");
    expectErrors("Parse error. Unexpected token '=>' in type expression");
    parse("var n: => boolean;");
  }

  public void testFunctionType_missingParens() {
    expectErrors("Parse error. Semi-colon expected");
    parse("var n: p1 => boolean;");
    expectErrors("Parse error. Semi-colon expected");
    parse("var n: p1:string => boolean;");
    expectErrors("Parse error. Semi-colon expected");
    parse("var n: p1:string, p2:number => boolean;");
  }

  public void testInterface() {
    parse("interface I {\n  foo: string;\n}");
  }

  public void testInterface_notEs6Typed() {
    testNotEs6Typed("interface I { foo: string;}", "interface", "type annotation");
  }

  public void testInterface_disallowExpression() {
    expectErrors("Parse error. primary expression expected");
    parse("var i = interface {};");
  }

  public void testInterfaceMember() {
    Node ast = parse("interface I {\n  foo;\n}");
    Node classMembers = ast.getFirstChild().getLastChild();
    assertTreeEquals(
        "has foo variable",
        Node.newString(Token.MEMBER_VARIABLE_DEF, "foo"),
        classMembers.getFirstChild());
  }

  public void testEnum() {
    parse("enum E {\n  a,\n  b,\n  c\n}");
  }

  public void testEnum_notEs6Typed() {
    testNotEs6Typed("enum E {a, b, c}", "enum");
  }

  public void testMemberVariable() throws Exception {
    // Just make sure it round trips, no types for the moment.
    Node ast = parse("class Foo {\n  foo;\n}");
    Node classMembers = ast.getFirstChild().getLastChild();
    assertTreeEquals("has foo variable", Node.newString(Token.MEMBER_VARIABLE_DEF, "foo"),
        classMembers.getFirstChild());
  }

  public void testMemberVariable_generator() throws Exception {
    expectErrors("Parse error. Member variable cannot be prefixed by '*' (generator function)");
    parse("class X { *foo: number; }");
  }

  public void testComputedPropertyMemberVariable() throws Exception {
    parse("class Foo {\n  ['foo'];\n}");
  }

  public void testMemberVariable_type() {
    Node classDecl = parse("class X {\n  m1: string;\n  m2: number;\n}").getFirstChild();
    Node members = classDecl.getChildAtIndex(2);
    Node memberVariable = members.getFirstChild();
    assertDeclaredType("string field type", stringType(), memberVariable);
  }

  public void testMethodType() {
    Node classDecl = parse(
        "class X {\n"
        + "  m(p: number): string {\n"
        + "    return p + x;\n"
        + "  }\n"
        + "}").getFirstChild();
    Node members = classDecl.getChildAtIndex(2);
    Node method = members.getFirstChild().getFirstChild();
    assertDeclaredType("string return type", stringType(), method);
  }

  private void assertVarType(String message, TypeDeclarationNode expectedType, String source) {
    Node varDecl = parse(source, source).getFirstChild();
    assertDeclaredType(message, expectedType, varDecl.getFirstChild());
  }

  private void assertDeclaredType(String message, TypeDeclarationNode expectedType, Node typed) {
    assertTreeEquals(message, expectedType, typed.getDeclaredTypeExpression());
  }

  private void assertTreeEquals(String message, Node expected, Node actual) {
    String treeDiff = expected.checkTreeEquals(actual);
    assertNull(message + ": " + treeDiff, treeDiff);
  }

  private Node parse(String source, String expected, LanguageMode languageIn) {
    CompilerOptions options = new CompilerOptions();
    options.setLanguageIn(languageIn);
    options.setLanguageOut(LanguageMode.ECMASCRIPT6_TYPED);
    options.setPreserveTypeAnnotations(true);
    options.setPrettyPrint(true);
    options.setLineLengthThreshold(80);
    options.setPreferSingleQuotes(true);

    Compiler compiler = new Compiler();
    compiler.setErrorManager(testErrorManager);
    compiler.initOptions(options);

    Node script = compiler.parse(SourceFile.fromCode("[test]", source));

    // Verifying that all warnings were seen
    assertTrue("Missing an error", testErrorManager.hasEncounteredAllErrors());
    assertTrue("Missing a warning", testErrorManager.hasEncounteredAllWarnings());

    if (script != null && testErrorManager.getErrorCount() == 0) {
      // if it can be parsed, it should round trip.
      String actual = new CodePrinter.Builder(script)
          .setCompilerOptions(options)
          .setTypeRegistry(compiler.getTypeIRegistry())
          .build()  // does the actual printing.
          .trim();
      assertThat(actual).isEqualTo(expected);
    }

    return script;
  }

  private Node parse(String source, LanguageMode languageIn) {
    return parse(source, source, languageIn);
  }

  private Node parse(String source) {
    return parse(source, source, LanguageMode.ECMASCRIPT6_TYPED);
  }

  private Node parse(String source, String expected) {
    return parse(source, expected, LanguageMode.ECMASCRIPT6_TYPED);
  }
}
