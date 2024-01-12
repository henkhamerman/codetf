Refactoring Types: ['Extract Method']
runtime/tree/Trees.java
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

import org.antlr.v4.runtime.Parser;
import org.antlr.v4.runtime.ParserRuleContext;
import org.antlr.v4.runtime.Token;
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

	public static List<ParseTree> descendants(ParseTree t){
		List<ParseTree> nodes = new ArrayList<ParseTree>();
		nodes.add(t);

		int n = t.getChildCount();
		for (int i = 0 ; i < n ; i++){
			nodes.addAll(descendants(t.getChild(i)));
		}
		return nodes;
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

	private Trees() {
	}
}


File: runtime/Java/src/org/antlr/v4/runtime/tree/xpath/XPathWildcardAnywhereElement.java
package org.antlr.v4.runtime.tree.xpath;

import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.Trees;

import java.util.ArrayList;
import java.util.Collection;

public class XPathWildcardAnywhereElement extends XPathElement {
	public XPathWildcardAnywhereElement() {
		super(XPath.WILDCARD);
	}

	@Override
	public Collection<ParseTree> evaluate(ParseTree t) {
		if ( invert ) return new ArrayList<ParseTree>(); // !* is weird but valid (empty)
		return Trees.descendants(t);
	}
}


File: tool/src/org/antlr/v4/tool/GrammarParserInterpreter.java
package org.antlr.v4.tool;

import org.antlr.v4.runtime.BailErrorStrategy;
import org.antlr.v4.runtime.InterpreterRuleContext;
import org.antlr.v4.runtime.Parser;
import org.antlr.v4.runtime.ParserInterpreter;
import org.antlr.v4.runtime.ParserRuleContext;
import org.antlr.v4.runtime.RecognitionException;
import org.antlr.v4.runtime.TokenStream;
import org.antlr.v4.runtime.Vocabulary;
import org.antlr.v4.runtime.atn.ATN;
import org.antlr.v4.runtime.atn.ATNDeserializer;
import org.antlr.v4.runtime.atn.ATNSerializer;
import org.antlr.v4.runtime.atn.ATNState;
import org.antlr.v4.runtime.atn.DecisionState;
import org.antlr.v4.runtime.atn.PredictionMode;
import org.antlr.v4.runtime.atn.RuleStartState;
import org.antlr.v4.runtime.atn.StarLoopEntryState;
import org.antlr.v4.runtime.tree.Trees;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.BitSet;
import java.util.Collection;
import java.util.List;

/** A heavier weight {@link ParserInterpreter} that creates parse trees
 *  that track alternative numbers for subtree roots.
 *
 * @since 4.5.1
 *
 */
public class GrammarParserInterpreter extends ParserInterpreter {
	/** The grammar associated with this interpreter. Unlike the
	 *  {@link ParserInterpreter} from the standard distribution,
	 *  this can reference Grammar, which is in the tools area not
	 *  purely runtime.
	 */
	protected final Grammar g;

	protected BitSet decisionStatesThatSetOuterAltNumInContext;

	/** Cache {@link LeftRecursiveRule#getPrimaryAlts()} and
	 *  {@link LeftRecursiveRule#getRecursiveOpAlts()} for states in
	 *  {@link #decisionStatesThatSetOuterAltNumInContext}. It only
	 *  caches decisions in left-recursive rules.
	 */
	protected int[][] stateToAltsMap;

	public GrammarParserInterpreter(Grammar g,
									String grammarFileName,
									Vocabulary vocabulary,
									Collection<String> ruleNames,
									ATN atn,
									TokenStream input) {
		super(grammarFileName, vocabulary, ruleNames, atn, input);
		this.g = g;
	}

	public GrammarParserInterpreter(Grammar g, ATN atn, TokenStream input) {
		super(g.fileName, g.getVocabulary(),
			  Arrays.asList(g.getRuleNames()),
			  atn, // must run ATN through serializer to set some state flags
			  input);
		this.g = g;
		decisionStatesThatSetOuterAltNumInContext = findOuterMostDecisionStates();
		stateToAltsMap = new int[g.atn.getNumberOfDecisions()][];
	}

	@Override
	protected InterpreterRuleContext createInterpreterRuleContext(ParserRuleContext parent,
																  int invokingStateNumber,
																  int ruleIndex)
	{
		return new GrammarInterpreterRuleContext(parent, invokingStateNumber, ruleIndex);
	}

	@Override
	public void reset() {
		super.reset();
		overrideDecisionRoot = null;
	}

	/** identify the ATN states where we need to set the outer alt number.
	 *  For regular rules, that's the block at the target to rule start state.
	 *  For left-recursive rules, we track the primary block, which looks just
	 *  like a regular rule's outer block, and the star loop block (always
	 *  there even if 1 alt).
	 */
	public BitSet findOuterMostDecisionStates() {
		BitSet track = new BitSet(atn.states.size());
		int numberOfDecisions = atn.getNumberOfDecisions();
		for (int i = 0; i < numberOfDecisions; i++) {
			DecisionState decisionState = atn.getDecisionState(i);
			RuleStartState startState = atn.ruleToStartState[decisionState.ruleIndex];
			// Look for StarLoopEntryState that is in any left recursive rule
			if ( decisionState instanceof StarLoopEntryState) {
				StarLoopEntryState loopEntry = (StarLoopEntryState)decisionState;
				if ( loopEntry.isPrecedenceDecision ) {
					// Recursive alts always result in a (...)* in the transformed
					// left recursive rule and that always has a BasicBlockStartState
					// even if just 1 recursive alt exists.
					ATNState blockStart = loopEntry.transition(0).target;
					// track the StarBlockStartState associated with the recursive alternatives
					track.set(blockStart.stateNumber);
				}
			}
			else if ( startState.transition(0).target == decisionState ) {
				// always track outermost block for any rule if it exists
				track.set(decisionState.stateNumber);
			}
		}
		return track;
	}

	/** Override this method so that we can record which alternative
	 *  was taken at each decision point. For non-left recursive rules,
	 *  it's simple. Set decisionStatesThatSetOuterAltNumInContext
	 *  indicates which decision states should set the outer alternative number.
	 *
	 *  Left recursive rules are much more complicated to deal with:
	 *  there is typically a decision for the primary alternatives and a
	 *  decision to choose between the recursive operator alternatives.
	 *  For example, the following left recursive rule has two primary and 2
	 *  recursive alternatives.</p>
	 *
		 e : e '*' e
		   | '-' INT
		   | e '+' e
		   | ID
		   ;

	 *  <p>ANTLR rewrites that rule to be</p>

		 e[int precedence]
			 : ('-' INT | ID)
			 ( {...}? '*' e[5]
			 | {...}? '+' e[3]
			 )*
			;

	 *
	 *  <p>So, there are two decisions associated with picking the outermost alt.
	 *  This complicates our tracking significantly. The outermost alternative number
	 *  is a function of the decision (ATN state) within a left recursive rule and the
	 *  predicted alternative coming back from adaptivePredict().
	 *
	 *  We use stateToAltsMap as a cache to avoid expensive calls to
	 *  getRecursiveOpAlts().
	 */
	@Override
	protected int visitDecisionState(DecisionState p) {
		int predictedAlt = super.visitDecisionState(p);
		if( p.getNumberOfTransitions() > 1) {
//			System.out.println("decision "+p.decision+": "+predictedAlt);
			if( p.decision == this.overrideDecision &&
				this._input.index() == this.overrideDecisionInputIndex )
			{
				overrideDecisionRoot = (GrammarInterpreterRuleContext)getContext();
			}
		}

		GrammarInterpreterRuleContext ctx = (GrammarInterpreterRuleContext)_ctx;
		if ( decisionStatesThatSetOuterAltNumInContext.get(p.stateNumber) ) {
			ctx.outerAltNum = predictedAlt;
			Rule r = g.getRule(p.ruleIndex);
			if ( atn.ruleToStartState[r.index].isLeftRecursiveRule ) {
				int[] alts = stateToAltsMap[p.stateNumber];
				LeftRecursiveRule lr = (LeftRecursiveRule) g.getRule(p.ruleIndex);
				if (p.getStateType() == ATNState.BLOCK_START) {
					if ( alts==null ) {
						alts = lr.getPrimaryAlts();
						stateToAltsMap[p.stateNumber] = alts; // cache it
					}
				}
				else if ( p.getStateType() == ATNState.STAR_BLOCK_START ) {
					if ( alts==null ) {
						alts = lr.getRecursiveOpAlts();
						stateToAltsMap[p.stateNumber] = alts; // cache it
					}
				}
				ctx.outerAltNum = alts[predictedAlt];
			}
		}

		return predictedAlt;
	}

	/** Given an ambiguous parse information, return the list of ambiguous parse trees.
	 *  An ambiguity occurs when a specific token sequence can be recognized
	 *  in more than one way by the grammar. These ambiguities are detected only
	 *  at decision points.
	 *
	 *  The list of trees includes the actual interpretation (that for
	 *  the minimum alternative number) and all ambiguous alternatives.
	 *  The actual interpretation is always first.
	 *
	 *  This method reuses the same physical input token stream used to
	 *  detect the ambiguity by the original parser in the first place.
	 *  This method resets/seeks within but does not alter originalParser.
	 *
	 *  The trees are rooted at the node whose start..stop token indices
	 *  include the start and stop indices of this ambiguity event. That is,
	 *  the trees returned will always include the complete ambiguous subphrase
	 *  identified by the ambiguity event.  The subtrees returned will
	 *  also always contain the node associated with the overridden decision.
	 *
	 *  Be aware that this method does NOT notify error or parse listeners as
	 *  it would trigger duplicate or otherwise unwanted events.
	 *
	 *  This uses a temporary ParserATNSimulator and a ParserInterpreter
	 *  so we don't mess up any statistics, event lists, etc...
	 *  The parse tree constructed while identifying/making ambiguityInfo is
	 *  not affected by this method as it creates a new parser interp to
	 *  get the ambiguous interpretations.
	 *
	 *  Nodes in the returned ambig trees are independent of the original parse
	 *  tree (constructed while identifying/creating ambiguityInfo).
	 *
	 *  @since 4.5.1
	 *
	 *  @param g              From which grammar should we drive alternative
	 *                        numbers and alternative labels.
	 *
	 *  @param originalParser The parser used to create ambiguityInfo; it
	 *                        is not modified by this routine and can be either
	 *                        a generated or interpreted parser. It's token
	 *                        stream *is* reset/seek()'d.
	 *  @param tokens		  A stream of tokens to use with the temporary parser.
	 *                        This will often be just the token stream within the
	 *                        original parser but here it is for flexibility.
	 *
	 *  @param decision       Which decision to try different alternatives for.
	 *
	 *  @param alts           The set of alternatives to try while re-parsing.
	 *
	 *  @param startIndex	  The index of the first token of the ambiguous
	 *                        input or other input of interest.
	 *
	 *  @param stopIndex      The index of the last token of the ambiguous input.
	 *                        The start and stop indexes are used primarily to
	 *                        identify how much of the resulting parse tree
	 *                        to return.
	 *
	 *  @param startRuleIndex The start rule for the entire grammar, not
	 *                        the ambiguous decision. We re-parse the entire input
	 *                        and so we need the original start rule.
	 *
	 *  @return               The list of all possible interpretations of
	 *                        the input for the decision in ambiguityInfo.
	 *                        The actual interpretation chosen by the parser
	 *                        is always given first because this method
	 *                        retests the input in alternative order and
	 *                        ANTLR always resolves ambiguities by choosing
	 *                        the first alternative that matches the input.
	 *                        The subtree returned
	 *
	 *  @throws RecognitionException Throws upon syntax error while matching
	 *                               ambig input.
	 */
	public static List<ParserRuleContext> getAllPossibleParseTrees(Grammar g,
																   Parser originalParser,
																   TokenStream tokens,
																   int decision,
																   BitSet alts,
																   int startIndex,
																   int stopIndex,
																   int startRuleIndex)
		throws RecognitionException
	{
		List<ParserRuleContext> trees = new ArrayList<ParserRuleContext>();
		// Create a new parser interpreter to parse the ambiguous subphrase
		ParserInterpreter parser;
		if (originalParser instanceof ParserInterpreter) {
			parser = new GrammarParserInterpreter(g, originalParser.getATN(), originalParser.getTokenStream());
		}
		else { // must've been a generated parser
			char[] serializedAtn = ATNSerializer.getSerializedAsChars(originalParser.getATN());
			ATN deserialized = new ATNDeserializer().deserialize(serializedAtn);
			parser = new ParserInterpreter(originalParser.getGrammarFileName(),
										   originalParser.getVocabulary(),
										   Arrays.asList(originalParser.getRuleNames()),
										   deserialized,
										   tokens);
		}

		parser.setInputStream(tokens);

		// Make sure that we don't get any error messages from using this temporary parser
		parser.setErrorHandler(new BailErrorStrategy());
		parser.removeErrorListeners();
		parser.removeParseListeners();
		parser.getInterpreter().setPredictionMode(PredictionMode.LL_EXACT_AMBIG_DETECTION);

		// get ambig trees
		int alt = alts.nextSetBit(0);
		while (alt >= 0) {
			// re-parse entire input for all ambiguous alternatives
			// (don't have to do first as it's been parsed, but do again for simplicity
			//  using this temp parser.)
			parser.reset();
			parser.getTokenStream().seek(0); // rewind the input all the way for re-parsing
			parser.addDecisionOverride(decision, startIndex, alt);
			ParserRuleContext t = parser.parse(startRuleIndex);
			GrammarInterpreterRuleContext ambigSubTree =
				(GrammarInterpreterRuleContext) Trees.getRootOfSubtreeEnclosingRegion(t, startIndex, stopIndex);
			// Use higher of overridden decision tree or tree enclosing all tokens
			if ( Trees.isAncestorOf(parser.getOverrideDecisionRoot(), ambigSubTree) ) {
				ambigSubTree = (GrammarInterpreterRuleContext)parser.getOverrideDecisionRoot();
			}
			trees.add(ambigSubTree);
			alt = alts.nextSetBit(alt + 1);
		}

		return trees;
	}

}


File: tool/test/org/antlr/v4/test/tool/TestAmbigParseTrees.java
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

		testInterpAtSpecificAlt(lg, g, "s", 1, "abc", "(s a (x b) c)");
		testInterpAtSpecificAlt(lg, g, "s", 2, "abc", "(s a b c)");
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
		String expectedOverallTree = "(s a (x b) c)";
		String[] expectedParseTrees = {"(s a (x b) c)","(s a b c)"};

		testInterp(lg, g, startRule, input, decision,
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
			"s : a ;" +
			"a : b ;" +
			"b : A x C" +
			"  | A B C" +
			"  ;" +
			"x : B ; \n",
			lg);

		String startRule = "s";
		String input = "abc";
		String expectedAmbigAlts = "{1, 2}";
		int decision = 0;
		String expectedOverallTree = "(s (a (b a (x b) c)))";
		String[] expectedParseTrees = {"(b a (x b) c)","(b a b c)"};

		testInterp(lg, g, startRule, input, decision,
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
//			"s : e ;\n"+
			"e : p (DOT ID)* ;\n"+
			"p : SELF" +
			"  | SELF DOT ID" +
			"  ;",
			lg);

		String startRule = "e";
		String input = "self.x";
		String expectedAmbigAlts = "{1, 2}";
		int decision = 1; // decision in s
		String expectedOverallTree = "(e (p self) . x)";
		String[] expectedParseTrees = {"(e (p self) . x)","(p self . x)"};

		testInterp(lg, g, startRule, input, decision,
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
		int decision = 1; // decision in s
		String expectedOverallTree = "(s (e (p self) . x))";
		String[] expectedParseTrees = {"(e (p self) . x)","(p self . x)"};

		testInterp(lg, g, startRule, input, decision,
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
		int decision = 1; // decision in s
		String expectedOverallTree = "(s (e (e (p self)) . x))";
		String[] expectedParseTrees = {"(e (e (p self)) . x)","(p self . x)"};

		testInterp(lg, g, startRule, input, decision,
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
		int decision = 1; // decision in s
		String expectedOverallTree = "(e (e (p self)) . x)";
		String[] expectedParseTrees = {"(e (e (p self)) . x)","(p self . x)"};

		testInterp(lg, g, startRule, input, decision,
				   expectedAmbigAlts,
				   expectedOverallTree, expectedParseTrees);
	}

	public void testInterp(LexerGrammar lg, Grammar g,
						   String startRule, String input, int decision,
						   String expectedAmbigAlts,
						   String overallTree,
						   String[] expectedParseTrees)
	{
		LexerInterpreter lexEngine = lg.createLexerInterpreter(new ANTLRInputStream(input));
		CommonTokenStream tokens = new CommonTokenStream(lexEngine);
		final GrammarParserInterpreter parser = g.createGrammarParserInterpreter(tokens);
		parser.setProfile(true);
		parser.getInterpreter().setPredictionMode(PredictionMode.LL_EXACT_AMBIG_DETECTION);

		// PARSE
		int ruleIndex = g.rules.get(startRule).index;
		ParserRuleContext parseTree = parser.parse(ruleIndex);
		assertEquals(overallTree, parseTree.toStringTree(parser));
		System.out.println();

		DecisionInfo[] decisionInfo = parser.getParseInfo().getDecisionInfo();
		List<AmbiguityInfo> ambiguities = decisionInfo[decision].ambiguities;
		assertEquals(1, ambiguities.size());
		AmbiguityInfo ambiguityInfo = ambiguities.get(0);

		List<ParserRuleContext> ambiguousParseTrees =
			GrammarParserInterpreter.getAllPossibleParseTrees(g,
															  parser,
															  tokens,
															  ambiguityInfo.decision,
															  ambiguityInfo.ambigAlts,
															  ambiguityInfo.startIndex,
															  ambiguityInfo.stopIndex,
															  ruleIndex);
		assertEquals(expectedAmbigAlts, ambiguityInfo.ambigAlts.toString());

		assertEquals(ambiguityInfo.ambigAlts.cardinality(), ambiguousParseTrees.size());
		for (int i = 0; i<ambiguousParseTrees.size(); i++) {
			ParserRuleContext t = ambiguousParseTrees.get(i);
			assertEquals(expectedParseTrees[i], t.toStringTree(parser));
		}
	}

	void testInterpAtSpecificAlt(LexerGrammar lg, Grammar g,
								 String startRule, int startAlt,
								 String input,
								 String expectedParseTree)
	{
		LexerInterpreter lexEngine = lg.createLexerInterpreter(new ANTLRInputStream(input));
		CommonTokenStream tokens = new CommonTokenStream(lexEngine);
		ParserInterpreter parser = g.createParserInterpreter(tokens);
		RuleStartState ruleStartState = g.atn.ruleToStartState[g.getRule(startRule).index];
		Transition tr = ruleStartState.transition(0);
		ATNState t2 = tr.target;
		if ( !(t2 instanceof BasicBlockStartState) ) {
			throw new IllegalArgumentException("rule has no decision: "+startRule);
		}
		parser.addDecisionOverride(((DecisionState)t2).decision, 0, startAlt);
		ParseTree t = parser.parse(g.rules.get(startRule).index);
		assertEquals(expectedParseTree, t.toStringTree(parser));
	}
}
