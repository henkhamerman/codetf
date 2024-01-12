Refactoring Types: ['Move Class', 'Rename Package']
ntext.java
/*
 * [The "BSD license"]
 *  Copyright (c) 2012 Terence Parr
 *  Copyright (c) 2012 Sam Harwell
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *  1. Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *  2. Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *  3. The name of the author may not be used to endorse or promote products
 *     derived from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 *  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 *  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 *  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 *  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 *  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
package org.antlr.v4.runtime;

import org.antlr.v4.runtime.misc.Interval;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.ParseTreeVisitor;
import org.antlr.v4.runtime.tree.RuleNode;
import org.antlr.v4.runtime.tree.Trees;
import org.antlr.v4.runtime.tree.gui.TreeViewer;

import javax.print.PrintException;
import javax.swing.*;
import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Future;

/** /** A rule context is a record of a single rule invocation.
 *
 *  We form a stack of these context objects using the parent
 *  pointer. A parent pointer of null indicates that the current
 *  context is the bottom of the stack. The ParserRuleContext subclass
 *  as a children list so that we can turn this data structure into a
 *  tree.
 *
 *  The root node always has a null pointer and invokingState of -1.
 *
 *  Upon entry to parsing, the first invoked rule function creates a
 *  context object (asubclass specialized for that rule such as
 *  SContext) and makes it the root of a parse tree, recorded by field
 *  Parser._ctx.
 *
 *  public final SContext s() throws RecognitionException {
 *      SContext _localctx = new SContext(_ctx, getState()); <-- create new node
 *      enterRule(_localctx, 0, RULE_s);                     <-- push it
 *      ...
 *      exitRule();                                          <-- pop back to _localctx
 *      return _localctx;
 *  }
 *
 *  A subsequent rule invocation of r from the start rule s pushes a
 *  new context object for r whose parent points at s and use invoking
 *  state is the state with r emanating as edge label.
 *
 *  The invokingState fields from a context object to the root
 *  together form a stack of rule indication states where the root
 *  (bottom of the stack) has a -1 sentinel value. If we invoke start
 *  symbol s then call r1, which calls r2, the  would look like
 *  this:
 *
 *     SContext[-1]   <- root node (bottom of the stack)
 *     R1Context[p]   <- p in rule s called r1
 *     R2Context[q]   <- q in rule r1 called r2
 *
 *  So the top of the stack, _ctx, represents a call to the current
 *  rule and it holds the return address from another rule that invoke
 *  to this rule. To invoke a rule, we must always have a current context.
 *
 *  The parent contexts are useful for computing lookahead sets and
 *  getting error information.
 *
 *  These objects are used during parsing and prediction.
 *  For the special case of parsers, we use the subclass
 *  ParserRuleContext.
 *
 *  @see ParserRuleContext
 */
public class RuleContext implements RuleNode {
	public static final ParserRuleContext EMPTY = new ParserRuleContext();

	/** What context invoked this rule? */
	public RuleContext parent;

	/** What state invoked the rule associated with this context?
	 *  The "return address" is the followState of invokingState
	 *  If parent is null, this should be -1 this context object represents
	 *  the start rule.
	 */
	public int invokingState = -1;

	public RuleContext() {}

	public RuleContext(RuleContext parent, int invokingState) {
		this.parent = parent;
		//if ( parent!=null ) System.out.println("invoke "+stateNumber+" from "+parent);
		this.invokingState = invokingState;
	}

	public int depth() {
		int n = 0;
		RuleContext p = this;
		while ( p!=null ) {
			p = p.parent;
			n++;
		}
		return n;
	}

	/** A context is empty if there is no invoking state; meaning nobody called
	 *  current context.
	 */
	public boolean isEmpty() {
		return invokingState == -1;
	}

	// satisfy the ParseTree / SyntaxTree interface

	@Override
	public Interval getSourceInterval() {
		return Interval.INVALID;
	}

	@Override
	public RuleContext getRuleContext() { return this; }

	@Override
	public RuleContext getParent() { return parent; }

	@Override
	public RuleContext getPayload() { return this; }

	/** Return the combined text of all child nodes. This method only considers
	 *  tokens which have been added to the parse tree.
	 *  <p>
	 *  Since tokens on hidden channels (e.g. whitespace or comments) are not
	 *  added to the parse trees, they will not appear in the output of this
	 *  method.
	 */
	@Override
	public String getText() {
		if (getChildCount() == 0) {
			return "";
		}

		StringBuilder builder = new StringBuilder();
		for (int i = 0; i < getChildCount(); i++) {
			builder.append(getChild(i).getText());
		}

		return builder.toString();
	}

	public int getRuleIndex() { return -1; }

	@Override
	public ParseTree getChild(int i) {
		return null;
	}

	@Override
	public int getChildCount() {
		return 0;
	}

	@Override
	public <T> T accept(ParseTreeVisitor<? extends T> visitor) { return visitor.visitChildren(this); }

	/** Call this method to view a parse tree in a dialog box visually. */
	public Future<JDialog> inspect(Parser parser) {
		List<String> ruleNames = parser != null ? Arrays.asList(parser.getRuleNames()) : null;
		return inspect(ruleNames);
	}

	public Future<JDialog> inspect(List<String> ruleNames) {
		TreeViewer viewer = new TreeViewer(ruleNames, this);
		return viewer.open();
	}

	/** Save this tree in a postscript file */
	public void save(Parser parser, String fileName)
		throws IOException, PrintException
	{
		List<String> ruleNames = parser != null ? Arrays.asList(parser.getRuleNames()) : null;
		save(ruleNames, fileName);
	}

	/** Save this tree in a postscript file using a particular font name and size */
	public void save(Parser parser, String fileName,
					 String fontName, int fontSize)
		throws IOException
	{
		List<String> ruleNames = parser != null ? Arrays.asList(parser.getRuleNames()) : null;
		save(ruleNames, fileName, fontName, fontSize);
	}

	/** Save this tree in a postscript file */
	public void save(List<String> ruleNames, String fileName)
		throws IOException, PrintException
	{
		Trees.writePS(this, ruleNames, fileName);
	}

	/** Save this tree in a postscript file using a particular font name and size */
	public void save(List<String> ruleNames, String fileName,
					 String fontName, int fontSize)
		throws IOException
	{
		Trees.writePS(this, ruleNames, fileName, fontName, fontSize);
	}

	/** Print out a whole tree, not just a node, in LISP format
	 *  (root child1 .. childN). Print just a node if this is a leaf.
	 *  We have to know the recognizer so we can get rule names.
	 */
	@Override
	public String toStringTree(Parser recog) {
		return Trees.toStringTree(this, recog);
	}

	/** Print out a whole tree, not just a node, in LISP format
	 *  (root child1 .. childN). Print just a node if this is a leaf.
	 */
	public String toStringTree(List<String> ruleNames) {
		return Trees.toStringTree(this, ruleNames);
	}

	@Override
	public String toStringTree() {
		return toStringTree((List<String>)null);
	}

	@Override
	public String toString() {
		return toString((List<String>)null, (RuleContext)null);
	}

	public final String toString(Recognizer<?,?> recog) {
		return toString(recog, ParserRuleContext.EMPTY);
	}

	public final String toString(List<String> ruleNames) {
		return toString(ruleNames, null);
	}

	// recog null unless ParserRuleContext, in which case we use subclass toString(...)
	public String toString(Recognizer<?,?> recog, RuleContext stop) {
		String[] ruleNames = recog != null ? recog.getRuleNames() : null;
		List<String> ruleNamesList = ruleNames != null ? Arrays.asList(ruleNames) : null;
		return toString(ruleNamesList, stop);
	}

	public String toString(List<String> ruleNames, RuleContext stop) {
		StringBuilder buf = new StringBuilder();
		RuleContext p = this;
		buf.append("[");
		while (p != null && p != stop) {
			if (ruleNames == null) {
				if (!p.isEmpty()) {
					buf.append(p.invokingState);
				}
			}
			else {
				int ruleIndex = p.getRuleIndex();
				String ruleName = ruleIndex >= 0 && ruleIndex < ruleNames.size() ? ruleNames.get(ruleIndex) : Integer.toString(ruleIndex);
				buf.append(ruleName);
			}

			if (p.parent != null && (ruleNames != null || !p.parent.isEmpty())) {
				buf.append(" ");
			}

			p = p.parent;
		}

		buf.append("]");
		return buf.toString();
	}
}


File: runtime/Java/src/org/antlr/v4/runtime/tree/Trees.java
/*
 * [The "BSD license"]
 *  Copyright (c) 2012 Terence Parr
 *  Copyright (c) 2012 Sam Harwell
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *  1. Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *  2. Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *  3. The name of the author may not be used to endorse or promote products
 *     derived from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 *  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 *  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 *  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 *  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 *  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

package org.antlr.v4.runtime.tree;

import org.antlr.v4.runtime.CommonToken;
import org.antlr.v4.runtime.Parser;
import org.antlr.v4.runtime.ParserRuleContext;
import org.antlr.v4.runtime.Token;
import org.antlr.v4.runtime.misc.Interval;
import org.antlr.v4.runtime.misc.Predicate;
import org.antlr.v4.runtime.misc.Utils;
import org.antlr.v4.runtime.tree.gui.TreePostScriptGenerator;
import org.antlr.v4.runtime.tree.gui.TreeTextProvider;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.List;

/** A set of utility routines useful for all kinds of ANTLR trees. */
public class Trees {

	public static String getPS(Tree t, List<String> ruleNames,
							   String fontName, int fontSize)
	{
		TreePostScriptGenerator psgen =
			new TreePostScriptGenerator(ruleNames, t, fontName, fontSize);
		return psgen.getPS();
	}

	public static String getPS(Tree t, List<String> ruleNames) {
		return getPS(t, ruleNames, "Helvetica", 11);
	}

	public static void writePS(Tree t, List<String> ruleNames,
							   String fileName,
							   String fontName, int fontSize)
		throws IOException
	{
		String ps = getPS(t, ruleNames, fontName, fontSize);
		FileWriter f = new FileWriter(fileName);
		BufferedWriter bw = new BufferedWriter(f);
		try {
			bw.write(ps);
		}
		finally {
			bw.close();
		}
	}

	public static void writePS(Tree t, List<String> ruleNames, String fileName)
		throws IOException
	{
		writePS(t, ruleNames, fileName, "Helvetica", 11);
	}

	/** Print out a whole tree in LISP form. {@link #getNodeText} is used on the
	 *  node payloads to get the text for the nodes.  Detect
	 *  parse trees and extract data appropriately.
	 */
	public static String toStringTree(Tree t) {
		return toStringTree(t, (List<String>)null);
	}

	/** Print out a whole tree in LISP form. {@link #getNodeText} is used on the
	 *  node payloads to get the text for the nodes.  Detect
	 *  parse trees and extract data appropriately.
	 */
	public static String toStringTree(Tree t, Parser recog) {
		String[] ruleNames = recog != null ? recog.getRuleNames() : null;
		List<String> ruleNamesList = ruleNames != null ? Arrays.asList(ruleNames) : null;
		return toStringTree(t, ruleNamesList);
	}

	/** Print out a whole tree in LISP form. Arg nodeTextProvider is used on the
	 *  node payloads to get the text for the nodes.
	 *
	 *  @since 4.5.1
	 */
	public static String toStringTree(Tree t, TreeTextProvider nodeTextProvider) {
		if ( t==null ) return "null";
		String s = Utils.escapeWhitespace(nodeTextProvider.getText(t), false);
		if ( t.getChildCount()==0 ) return s;
		StringBuilder buf = new StringBuilder();
		buf.append("(");
		s = Utils.escapeWhitespace(nodeTextProvider.getText(t), false);
		buf.append(s);
		buf.append(' ');
		for (int i = 0; i<t.getChildCount(); i++) {
			if ( i>0 ) buf.append(' ');
			buf.append(toStringTree(t.getChild(i), nodeTextProvider));
		}
		buf.append(")");
		return buf.toString();
	}

	/** Print out a whole tree in LISP form. {@link #getNodeText} is used on the
	 *  node payloads to get the text for the nodes.
	 */
	public static String toStringTree(final Tree t, final List<String> ruleNames) {
		return toStringTree(t, new TreeTextProvider() {
			@Override
			public String getText(Tree node) {
				return getNodeText(node, ruleNames);
			}
		});
	}

	public static String getNodeText(Tree t, Parser recog) {
		String[] ruleNames = recog != null ? recog.getRuleNames() : null;
		List<String> ruleNamesList = ruleNames != null ? Arrays.asList(ruleNames) : null;
		return getNodeText(t, ruleNamesList);
	}

	public static String getNodeText(Tree t, List<String> ruleNames) {
		if ( ruleNames!=null ) {
			if ( t instanceof RuleNode ) {
				int ruleIndex = ((RuleNode)t).getRuleContext().getRuleIndex();
				String ruleName = ruleNames.get(ruleIndex);
				return ruleName;
			}
			else if ( t instanceof ErrorNode) {
				return t.toString();
			}
			else if ( t instanceof TerminalNode) {
				Token symbol = ((TerminalNode)t).getSymbol();
				if (symbol != null) {
					String s = symbol.getText();
					return s;
				}
			}
		}
		// no recog for rule names
		Object payload = t.getPayload();
		if ( payload instanceof Token ) {
			return ((Token)payload).getText();
		}
		return t.getPayload().toString();
	}

	/** Return ordered list of all children of this node */
	public static List<Tree> getChildren(Tree t) {
		List<Tree> kids = new ArrayList<Tree>();
		for (int i=0; i<t.getChildCount(); i++) {
			kids.add(t.getChild(i));
		}
		return kids;
	}

	/** Return a list of all ancestors of this node.  The first node of
	 *  list is the root and the last is the parent of this node.
	 *
	 *  @since 4.5.1
	 */
	public static List<? extends Tree> getAncestors(Tree t) {
		if ( t.getParent()==null ) return Collections.emptyList();
		List<Tree> ancestors = new ArrayList<Tree>();
		t = t.getParent();
		while ( t!=null ) {
			ancestors.add(0, t); // insert at start
			t = t.getParent();
		}
		return ancestors;
	}

	/** Return true if t is u's parent or a node on path to root from u.
	 *  Use == not equals().
	 *
	 *  @since 4.5.1
	 */
	public static boolean isAncestorOf(Tree t, Tree u) {
		if ( t==null || u==null || t.getParent()==null ) return false;
		Tree p = u.getParent();
		while ( p!=null ) {
			if ( t == p ) return true;
			p = p.getParent();
		}
		return false;
	}

	public static Collection<ParseTree> findAllTokenNodes(ParseTree t, int ttype) {
		return findAllNodes(t, ttype, true);
	}

	public static Collection<ParseTree> findAllRuleNodes(ParseTree t, int ruleIndex) {
		return findAllNodes(t, ruleIndex, false);
	}

	public static List<ParseTree> findAllNodes(ParseTree t, int index, boolean findTokens) {
		List<ParseTree> nodes = new ArrayList<ParseTree>();
		_findAllNodes(t, index, findTokens, nodes);
		return nodes;
	}

	public static void _findAllNodes(ParseTree t, int index, boolean findTokens,
									 List<? super ParseTree> nodes)
	{
		// check this node (the root) first
		if ( findTokens && t instanceof TerminalNode ) {
			TerminalNode tnode = (TerminalNode)t;
			if ( tnode.getSymbol().getType()==index ) nodes.add(t);
		}
		else if ( !findTokens && t instanceof ParserRuleContext ) {
			ParserRuleContext ctx = (ParserRuleContext)t;
			if ( ctx.getRuleIndex() == index ) nodes.add(t);
		}
		// check children
		for (int i = 0; i < t.getChildCount(); i++){
			_findAllNodes(t.getChild(i), index, findTokens, nodes);
		}
	}

	/** Get all descendents; includes t itself.
	 *
	 * @since 4.5.1
 	 */
	public static List<ParseTree> getDescendants(ParseTree t) {
		List<ParseTree> nodes = new ArrayList<ParseTree>();
		nodes.add(t);

		int n = t.getChildCount();
		for (int i = 0 ; i < n ; i++){
			nodes.addAll(getDescendants(t.getChild(i)));
		}
		return nodes;
	}

	/** @deprecated */
	public static List<ParseTree> descendants(ParseTree t) {
		return getDescendants(t);
	}

	/** Find smallest subtree of t enclosing range startTokenIndex..stopTokenIndex
	 *  inclusively using postorder traversal.  Recursive depth-first-search.
	 *
	 *  @since 4.5.1
	 */
	public static ParserRuleContext getRootOfSubtreeEnclosingRegion(ParseTree t,
																	int startTokenIndex, // inclusive
																	int stopTokenIndex)  // inclusive
	{
		int n = t.getChildCount();
		for (int i = 0; i<n; i++) {
			ParseTree child = t.getChild(i);
			ParserRuleContext r = getRootOfSubtreeEnclosingRegion(child, startTokenIndex, stopTokenIndex);
			if ( r!=null ) return r;
		}
		if ( t instanceof ParserRuleContext ) {
			ParserRuleContext r = (ParserRuleContext) t;
			if ( startTokenIndex>=r.getStart().getTokenIndex() && // is range fully contained in t?
				 (r.getStop()==null || stopTokenIndex<=r.getStop().getTokenIndex()) )
			{
				// note: r.getStop()==null likely implies that we bailed out of parser and there's nothing to the right
				return r;
			}
		}
		return null;
	}

	/** Replace any subtree siblings of root that are completely to left
	 *  or right of lookahead range with a CommonToken(Token.INVALID_TYPE,"...")
	 *  node. The source interval for t is not altered to suit smaller range!
	 *
	 *  WARNING: destructive to t.
	 *
	 *  @since 4.5.1
	 */
	public static void stripChildrenOutOfRange(ParserRuleContext t,
											   ParserRuleContext root,
											   int startIndex,
											   int stopIndex)
	{
		if ( t==null ) return;
		for (int i = 0; i < t.getChildCount(); i++) {
			ParseTree child = t.getChild(i);
			Interval range = child.getSourceInterval();
			if ( child instanceof ParserRuleContext && (range.b < startIndex || range.a > stopIndex) ) {
				if ( isAncestorOf(child, root) ) { // replace only if subtree doesn't have displayed root
					CommonToken abbrev = new CommonToken(Token.INVALID_TYPE, "...");
					t.children.set(i, new TerminalNodeImpl(abbrev));
				}
			}
		}
	}

	/** Return first node satisfying the pred
	 *
 	 *  @since 4.5.1
	 */
	public static Tree findNodeSuchThat(Tree t, Predicate<Tree> pred) {
		if ( pred.test(t) ) return t;

		int n = t.getChildCount();
		for (int i = 0 ; i < n ; i++){
			Tree u = findNodeSuchThat(t.getChild(i), pred);
			if ( u!=null ) return u;
		}
		return null;
	}

	private Trees() {
	}
}


File: tool-testsuite/test/org/antlr/v4/test/tool/InterpreterTreeTextProvider.java
package org.antlr.v4.test.tool;

import org.antlr.v4.runtime.tree.ErrorNode;
import org.antlr.v4.runtime.tree.Tree;
import org.antlr.v4.runtime.tree.Trees;
import org.antlr.v4.runtime.tree.gui.TreeTextProvider;
import org.antlr.v4.tool.GrammarInterpreterRuleContext;

import java.util.Arrays;
import java.util.List;

public class InterpreterTreeTextProvider implements TreeTextProvider {
	public List<String> ruleNames;
	public InterpreterTreeTextProvider(String[] ruleNames) {this.ruleNames = Arrays.asList(ruleNames);}

	@Override
	public String getText(Tree node) {
		if ( node==null ) return "null";
		String nodeText = Trees.getNodeText(node, ruleNames);
		if ( node instanceof GrammarInterpreterRuleContext) {
			GrammarInterpreterRuleContext ctx = (GrammarInterpreterRuleContext) node;
			return nodeText+":"+ctx.getOuterAltNum();
		}
		if ( node instanceof ErrorNode) {
			return "<error "+nodeText+">";
		}
		return nodeText;
	}
}


File: tool-testsuite/test/org/antlr/v4/test/tool/TestAmbigParseTrees.java
package org.antlr.v4.test.tool;

import org.antlr.v4.runtime.ANTLRInputStream;
import org.antlr.v4.runtime.CommonTokenStream;
import org.antlr.v4.runtime.LexerInterpreter;
import org.antlr.v4.runtime.ParserInterpreter;
import org.antlr.v4.runtime.ParserRuleContext;
import org.antlr.v4.runtime.atn.ATNState;
import org.antlr.v4.runtime.atn.AmbiguityInfo;
import org.antlr.v4.runtime.atn.BasicBlockStartState;
import org.antlr.v4.runtime.atn.DecisionInfo;
import org.antlr.v4.runtime.atn.DecisionState;
import org.antlr.v4.runtime.atn.PredictionMode;
import org.antlr.v4.runtime.atn.RuleStartState;
import org.antlr.v4.runtime.atn.Transition;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.Trees;
import org.antlr.v4.tool.Grammar;
import org.antlr.v4.tool.GrammarParserInterpreter;
import org.antlr.v4.tool.LexerGrammar;
import org.junit.Test;

import java.util.List;

import static org.junit.Assert.assertEquals;

public class TestAmbigParseTrees {
	@Test public void testParseDecisionWithinAmbiguousStartRule() throws Exception {
		LexerGrammar lg = new LexerGrammar(
			"lexer grammar L;\n" +
			"A : 'a' ;\n" +
			"B : 'b' ;\n" +
			"C : 'c' ;\n");
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : A x C" +
			"  | A B C" +
			"  ;" +
			"x : B ; \n",
			lg);

		testInterpAtSpecificAlt(lg, g, "s", 1, "abc", "(s:1 a (x:1 b) c)");
		testInterpAtSpecificAlt(lg, g, "s", 2, "abc", "(s:2 a b c)");
	}

	@Test public void testAmbigAltsAtRoot() throws Exception {
		LexerGrammar lg = new LexerGrammar(
			"lexer grammar L;\n" +
			"A : 'a' ;\n" +
			"B : 'b' ;\n" +
			"C : 'c' ;\n");
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : A x C" +
			"  | A B C" +
			"  ;" +
			"x : B ; \n",
			lg);

		String startRule = "s";
		String input = "abc";
		String expectedAmbigAlts = "{1, 2}";
		int decision = 0;
		String expectedOverallTree = "(s:1 a (x:1 b) c)";
		String[] expectedParseTrees = {"(s:1 a (x:1 b) c)",
									   "(s:2 a b c)"};

		testAmbiguousTrees(lg, g, startRule, input, decision,
						   expectedAmbigAlts,
						   expectedOverallTree, expectedParseTrees);
	}

	@Test public void testAmbigAltsNotAtRoot() throws Exception {
		LexerGrammar lg = new LexerGrammar(
			"lexer grammar L;\n" +
			"A : 'a' ;\n" +
			"B : 'b' ;\n" +
			"C : 'c' ;\n");
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : x ;" +
			"x : y ;" +
			"y : A z C" +
			"  | A B C" +
			"  ;" +
			"z : B ; \n",
			lg);

		String startRule = "s";
		String input = "abc";
		String expectedAmbigAlts = "{1, 2}";
		int decision = 0;
		String expectedOverallTree = "(s:1 (x:1 (y:1 a (z:1 b) c)))";
		String[] expectedParseTrees = {"(y:1 a (z:1 b) c)",
									   "(y:2 a b c)"};

		testAmbiguousTrees(lg, g, startRule, input, decision,
						   expectedAmbigAlts,
						   expectedOverallTree, expectedParseTrees);
	}

	@Test public void testAmbigAltDipsIntoOuterContextToRoot() throws Exception {
		LexerGrammar lg = new LexerGrammar(
			"lexer grammar L;\n" +
			"SELF : 'self' ;\n" +
			"ID : [a-z]+ ;\n" +
			"DOT : '.' ;\n");
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"e : p (DOT ID)* ;\n"+
			"p : SELF" +
			"  | SELF DOT ID" +
			"  ;",
			lg);

		String startRule = "e";
		String input = "self.x";
		String expectedAmbigAlts = "{1, 2}";
		int decision = 1; // decision in p
		String expectedOverallTree = "(e:1 (p:1 self) . x)";
		String[] expectedParseTrees = {"(e:1 (p:1 self) . x)",
									   "(p:2 self . x)"};

		testAmbiguousTrees(lg, g, startRule, input, decision,
						   expectedAmbigAlts,
						   expectedOverallTree, expectedParseTrees);
	}

	@Test public void testAmbigAltDipsIntoOuterContextBelowRoot() throws Exception {
		LexerGrammar lg = new LexerGrammar(
			"lexer grammar L;\n" +
			"SELF : 'self' ;\n" +
			"ID : [a-z]+ ;\n" +
			"DOT : '.' ;\n");
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : e ;\n"+
			"e : p (DOT ID)* ;\n"+
			"p : SELF" +
			"  | SELF DOT ID" +
			"  ;",
			lg);

		String startRule = "s";
		String input = "self.x";
		String expectedAmbigAlts = "{1, 2}";
		int decision = 1; // decision in p
		String expectedOverallTree = "(s:1 (e:1 (p:1 self) . x))";
		String[] expectedParseTrees = {"(e:1 (p:1 self) . x)", // shouldn't include s
									   "(p:2 self . x)"};      // shouldn't include e

		testAmbiguousTrees(lg, g, startRule, input, decision,
						   expectedAmbigAlts,
						   expectedOverallTree, expectedParseTrees);
	}

	@Test public void testAmbigAltInLeftRecursiveBelowStartRule() throws Exception {
		LexerGrammar lg = new LexerGrammar(
			"lexer grammar L;\n" +
			"SELF : 'self' ;\n" +
			"ID : [a-z]+ ;\n" +
			"DOT : '.' ;\n");
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : e ;\n" +
			"e : p | e DOT ID ;\n"+
			"p : SELF" +
			"  | SELF DOT ID" +
			"  ;",
			lg);

		String startRule = "s";
		String input = "self.x";
		String expectedAmbigAlts = "{1, 2}";
		int decision = 1; // decision in p
		String expectedOverallTree = "(s:1 (e:2 (e:1 (p:1 self)) . x))";
		String[] expectedParseTrees = {"(e:2 (e:1 (p:1 self)) . x)",
									   "(p:2 self . x)"};

		testAmbiguousTrees(lg, g, startRule, input, decision,
						   expectedAmbigAlts,
						   expectedOverallTree, expectedParseTrees);
	}

	@Test public void testAmbigAltInLeftRecursiveStartRule() throws Exception {
		LexerGrammar lg = new LexerGrammar(
			"lexer grammar L;\n" +
			"SELF : 'self' ;\n" +
			"ID : [a-z]+ ;\n" +
			"DOT : '.' ;\n");
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"e : p | e DOT ID ;\n"+
			"p : SELF" +
			"  | SELF DOT ID" +
			"  ;",
			lg);

		String startRule = "e";
		String input = "self.x";
		String expectedAmbigAlts = "{1, 2}";
		int decision = 1; // decision in p
		String expectedOverallTree = "(e:2 (e:1 (p:1 self)) . x)";
		String[] expectedParseTrees = {"(e:2 (e:1 (p:1 self)) . x)",
									   "(p:2 self . x)"}; // shows just enough for self.x

		testAmbiguousTrees(lg, g, startRule, input, decision,
						   expectedAmbigAlts,
						   expectedOverallTree, expectedParseTrees);
	}

	public void testAmbiguousTrees(LexerGrammar lg, Grammar g,
								   String startRule, String input, int decision,
								   String expectedAmbigAlts,
								   String overallTree,
								   String[] expectedParseTrees)
	{
		InterpreterTreeTextProvider nodeTextProvider = new InterpreterTreeTextProvider(g.getRuleNames());

		LexerInterpreter lexEngine = lg.createLexerInterpreter(new ANTLRInputStream(input));
		CommonTokenStream tokens = new CommonTokenStream(lexEngine);
		final GrammarParserInterpreter parser = g.createGrammarParserInterpreter(tokens);
		parser.setProfile(true);
		parser.getInterpreter().setPredictionMode(PredictionMode.LL_EXACT_AMBIG_DETECTION);

		// PARSE
		int ruleIndex = g.rules.get(startRule).index;
		ParserRuleContext parseTree = parser.parse(ruleIndex);
		assertEquals(overallTree, Trees.toStringTree(parseTree, nodeTextProvider));
		System.out.println();

		DecisionInfo[] decisionInfo = parser.getParseInfo().getDecisionInfo();
		List<AmbiguityInfo> ambiguities = decisionInfo[decision].ambiguities;
		assertEquals(1, ambiguities.size());
		AmbiguityInfo ambiguityInfo = ambiguities.get(0);

		List<ParserRuleContext> ambiguousParseTrees =
			GrammarParserInterpreter.getAllPossibleParseTrees(g,
															  parser,
															  tokens,
															  decision,
															  ambiguityInfo.ambigAlts,
															  ambiguityInfo.startIndex,
															  ambiguityInfo.stopIndex,
															  ruleIndex);
		assertEquals(expectedAmbigAlts, ambiguityInfo.ambigAlts.toString());
		assertEquals(ambiguityInfo.ambigAlts.cardinality(), ambiguousParseTrees.size());

		for (int i = 0; i<ambiguousParseTrees.size(); i++) {
			ParserRuleContext t = ambiguousParseTrees.get(i);
			assertEquals(expectedParseTrees[i], Trees.toStringTree(t, nodeTextProvider));
		}
	}

	void testInterpAtSpecificAlt(LexerGrammar lg, Grammar g,
								 String startRule, int startAlt,
								 String input,
								 String expectedParseTree)
	{
		LexerInterpreter lexEngine = lg.createLexerInterpreter(new ANTLRInputStream(input));
		CommonTokenStream tokens = new CommonTokenStream(lexEngine);
		ParserInterpreter parser = g.createGrammarParserInterpreter(tokens);
		RuleStartState ruleStartState = g.atn.ruleToStartState[g.getRule(startRule).index];
		Transition tr = ruleStartState.transition(0);
		ATNState t2 = tr.target;
		if ( !(t2 instanceof BasicBlockStartState) ) {
			throw new IllegalArgumentException("rule has no decision: "+startRule);
		}
		parser.addDecisionOverride(((DecisionState)t2).decision, 0, startAlt);
		ParseTree t = parser.parse(g.rules.get(startRule).index);
		InterpreterTreeTextProvider nodeTextProvider = new InterpreterTreeTextProvider(g.getRuleNames());
		assertEquals(expectedParseTree, Trees.toStringTree(t, nodeTextProvider));
	}
}


File: tool-testsuite/test/org/antlr/v4/test/tool/TestGrammarParserInterpreter.java
/*
 * [The "BSD license"]
 *  Copyright (c) 2012 Terence Parr
 *  Copyright (c) 2012 Sam Harwell
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *  1. Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *  2. Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *  3. The name of the author may not be used to endorse or promote products
 *     derived from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 *  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 *  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 *  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 *  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 *  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
package org.antlr.v4.test.tool;

import org.antlr.v4.runtime.ANTLRInputStream;
import org.antlr.v4.runtime.CommonTokenStream;
import org.antlr.v4.runtime.InterpreterRuleContext;
import org.antlr.v4.runtime.LexerInterpreter;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.Trees;
import org.antlr.v4.tool.Grammar;
import org.antlr.v4.tool.GrammarParserInterpreter;
import org.antlr.v4.tool.LexerGrammar;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

/** Tests to ensure GrammarParserInterpreter subclass of ParserInterpreter
 *  hasn't messed anything up.
 */
public class TestGrammarParserInterpreter {
	public static final String lexerText = "lexer grammar L;\n" +
										   "PLUS : '+' ;\n" +
										   "MULT : '*' ;\n" +
										   "ID : [a-z]+ ;\n" +
										   "INT : [0-9]+ ;\n" +
										   "WS : [ \\r\\t\\n]+ ;\n";

	@Test
	public void testAlts() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : ID\n"+
			"  | INT{;}\n"+
			"  ;\n",
			lg);
		testInterp(lg, g, "s", "a",		"(s:1 a)");
		testInterp(lg, g, "s", "3", 	"(s:2 3)");
	}

	@Test
	public void testAltsAsSet() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : ID\n"+
			"  | INT\n"+
			"  ;\n",
			lg);
		testInterp(lg, g, "s", "a",		"(s:1 a)");
		testInterp(lg, g, "s", "3", 	"(s:1 3)");
	}

	@Test
	public void testAltsWithLabels() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : ID  # foo\n" +
			"  | INT # bar\n" +
			"  ;\n",
			lg);
		// it won't show the labels here because my simple node text provider above just shows the alternative
		testInterp(lg, g, "s", "a",		"(s:1 a)");
		testInterp(lg, g, "s", "3", 	"(s:2 3)");
	}

	@Test
	public void testOneAlt() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : ID\n"+
			"  ;\n",
			lg);
		testInterp(lg, g, "s", "a",		"(s:1 a)");
	}


	@Test
	public void testLeftRecursionWithMultiplePrimaryAndRecursiveOps() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : e EOF ;\n" +
			"e : e MULT e\n" +
			"  | e PLUS e\n" +
			"  | INT\n" +
			"  | ID\n" +
			"  ;\n",
			lg);

		testInterp(lg, g, "s", "a",		"(s:1 (e:4 a) <EOF>)");
		testInterp(lg, g, "e", "a",		"(e:4 a)");
		testInterp(lg, g, "e", "34",	"(e:3 34)");
		testInterp(lg, g, "e", "a+1",	"(e:2 (e:4 a) + (e:3 1))");
		testInterp(lg, g, "e", "1+2*a",	"(e:2 (e:3 1) + (e:1 (e:3 2) * (e:4 a)))");
	}

	InterpreterRuleContext testInterp(LexerGrammar lg, Grammar g,
	                                  String startRule, String input,
	                                  String expectedParseTree)
	{
		LexerInterpreter lexEngine = lg.createLexerInterpreter(new ANTLRInputStream(input));
		CommonTokenStream tokens = new CommonTokenStream(lexEngine);
		GrammarParserInterpreter parser = g.createGrammarParserInterpreter(tokens);
		ParseTree t = parser.parse(g.rules.get(startRule).index);
		InterpreterTreeTextProvider nodeTextProvider = new InterpreterTreeTextProvider(g.getRuleNames());
		String treeStr = Trees.toStringTree(t, nodeTextProvider);
		System.out.println("parse tree: "+treeStr);
		assertEquals(expectedParseTree, treeStr);
		return (InterpreterRuleContext)t;
	}
}


File: tool-testsuite/test/org/antlr/v4/test/tool/TestLookaheadTrees.java
package org.antlr.v4.test.tool;

import org.antlr.v4.runtime.ANTLRInputStream;
import org.antlr.v4.runtime.CommonTokenStream;
import org.antlr.v4.runtime.LexerInterpreter;
import org.antlr.v4.runtime.ParserRuleContext;
import org.antlr.v4.runtime.atn.DecisionInfo;
import org.antlr.v4.runtime.atn.LookaheadEventInfo;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.Trees;
import org.antlr.v4.tool.Grammar;
import org.antlr.v4.tool.GrammarParserInterpreter;
import org.antlr.v4.tool.LexerGrammar;
import org.junit.Test;

import java.util.List;

import static org.junit.Assert.assertEquals;

public class TestLookaheadTrees {
	public static final String lexerText =
		"lexer grammar L;\n" +
		"DOT  : '.' ;\n" +
		"SEMI : ';' ;\n" +
		"BANG : '!' ;\n" +
		"PLUS : '+' ;\n" +
		"LPAREN : '(' ;\n" +
		"RPAREN : ')' ;\n" +
		"MULT : '*' ;\n" +
		"ID : [a-z]+ ;\n" +
		"INT : [0-9]+ ;\n" +
		"WS : [ \\r\\t\\n]+ ;\n";

	@Test
	public void testAlts() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : e SEMI EOF ;\n" +
			"e : ID DOT ID\n"+
			"  | ID LPAREN RPAREN\n"+
			"  ;\n",
			lg);

		String startRuleName = "s";
		int decision = 0;

		testLookaheadTrees(lg, g, "a.b;", startRuleName, decision,
						   new String[] {"(e:1 a . b)", "(e:2 a <error .>)"});
	}

	@Test
	public void testAlts2() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : e? SEMI EOF ;\n" +
			"e : ID\n" +
			"  | e BANG" +
			"  ;\n",
			lg);

		String startRuleName = "s";
		int decision = 1; // (...)* in e.

		testLookaheadTrees(lg, g, "a;", startRuleName, decision,
						   new String[] {"(e:2 (e:1 a) <error ;>)", // Decision for alt 1 is error as no ! char, but alt 2 (exit) is good.
										 "(s:1 (e:1 a) ; <EOF>)"}); // root s:1 is included to show ';' node
	}

	@Test
	public void testIncludeEOF() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : e ;\n" +
			"e : ID DOT ID EOF\n"+
			"  | ID DOT ID EOF\n"+
			"  ;\n",
			lg);

		int decision = 0;
		testLookaheadTrees(lg, g, "a.b", "s", decision,
						   new String[] {"(e:1 a . b <EOF>)", "(e:2 a . b <EOF>)"});
	}

	@Test
	public void testCallLeftRecursiveRule() throws Exception {
		LexerGrammar lg = new LexerGrammar(lexerText);
		Grammar g = new Grammar(
			"parser grammar T;\n" +
			"s : a BANG EOF;\n" +
			"a : e SEMI \n" +
			"  | ID SEMI \n" +
			"  ;" +
			"e : e MULT e\n" +
			"  | e PLUS e\n" +
			"  | e DOT e\n" +
			"  | ID\n" +
			"  | INT\n" +
			"  ;\n",
			lg);

		int decision = 0;
		testLookaheadTrees(lg, g, "x;!", "s", decision,
						   new String[] {"(a:1 (e:4 x) ;)",
										 "(a:2 x ;)"}); // shouldn't include BANG, EOF
		decision = 2; // (...)* in e
		testLookaheadTrees(lg, g, "x+1;!", "s", decision,
						   new String[] {"(e:1 (e:4 x) <error +>)",
										 "(e:2 (e:4 x) + (e:5 1))",
										 "(e:3 (e:4 x) <error +>)"});
	}

	public void testLookaheadTrees(LexerGrammar lg, Grammar g,
								   String input,
								   String startRuleName,
								   int decision,
								   String[] expectedTrees)
	{
		int startRuleIndex = g.getRule(startRuleName).index;
		InterpreterTreeTextProvider nodeTextProvider =
					new InterpreterTreeTextProvider(g.getRuleNames());

		LexerInterpreter lexEngine = lg.createLexerInterpreter(new ANTLRInputStream(input));
		CommonTokenStream tokens = new CommonTokenStream(lexEngine);
		GrammarParserInterpreter parser = g.createGrammarParserInterpreter(tokens);
		parser.setProfile(true);
		ParseTree t = parser.parse(startRuleIndex);

		DecisionInfo decisionInfo = parser.getParseInfo().getDecisionInfo()[decision];
		LookaheadEventInfo lookaheadEventInfo = decisionInfo.SLL_MaxLookEvent;

		List<ParserRuleContext> lookaheadParseTrees =
			GrammarParserInterpreter.getLookaheadParseTrees(g, parser, tokens, startRuleIndex, lookaheadEventInfo.decision,
															lookaheadEventInfo.startIndex, lookaheadEventInfo.stopIndex);

		assertEquals(expectedTrees.length, lookaheadParseTrees.size());
		for (int i = 0; i < lookaheadParseTrees.size(); i++) {
			ParserRuleContext lt = lookaheadParseTrees.get(i);
			assertEquals(expectedTrees[i], Trees.toStringTree(lt, nodeTextProvider));
		}
	}
}
