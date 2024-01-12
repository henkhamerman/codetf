Refactoring Types: ['Pull Up Method']
chnologies/orient/core/command/OBasicCommandContext.java
/*
 *
 *  *  Copyright 2014 Orient Technologies LTD (info(at)orientechnologies.com)
 *  *
 *  *  Licensed under the Apache License, Version 2.0 (the "License");
 *  *  you may not use this file except in compliance with the License.
 *  *  You may obtain a copy of the License at
 *  *
 *  *       http://www.apache.org/licenses/LICENSE-2.0
 *  *
 *  *  Unless required by applicable law or agreed to in writing, software
 *  *  distributed under the License is distributed on an "AS IS" BASIS,
 *  *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  *  See the License for the specific language governing permissions and
 *  *  limitations under the License.
 *  *
 *  * For more information: http://www.orientechnologies.com
 *
 */
package com.orientechnologies.orient.core.command;

import com.orientechnologies.common.concur.OTimeoutException;
import com.orientechnologies.orient.core.metadata.schema.OType;
import com.orientechnologies.orient.core.record.impl.ODocumentHelper;
import com.orientechnologies.orient.core.serialization.serializer.OStringSerializerHelper;

import java.util.HashMap;
import java.util.Map;

/**
 * Basic implementation of OCommandContext interface that stores variables in a map. Supports parent/child context to build a tree
 * of contexts. If a variable is not found on current object the search is applied recursively on child contexts.
 * 
 * @author Luca Garulli (l.garulli--at--orientechnologies.com)
 * 
 */
public class OBasicCommandContext implements OCommandContext {
  public static final String                                                         EXECUTION_BEGUN       = "EXECUTION_BEGUN";
  public static final String                                                         TIMEOUT_MS            = "TIMEOUT_MS";
  public static final String                                                         TIMEOUT_STRATEGY      = "TIMEOUT_STARTEGY";
  public static final String                                                         INVALID_COMPARE_COUNT = "INVALID_COMPARE_COUNT";

  protected boolean                                                                  recordMetrics         = false;
  protected OCommandContext                                                          parent;
  protected OCommandContext                                                          child;
  protected Map<String, Object>                                                      variables;

  // MANAGES THE TIMEOUT
  private long                                                                       executionStartedOn;
  private long                                                                       timeoutMs;
  private com.orientechnologies.orient.core.command.OCommandContext.TIMEOUT_STRATEGY timeoutStrategy;

  public OBasicCommandContext() {
  }

  public Object getVariable(String iName) {
    return getVariable(iName, null);
  }

  public Object getVariable(String iName, final Object iDefault) {
    if (iName == null)
      return iDefault;

    Object result = null;

    if (iName.startsWith("$"))
      iName = iName.substring(1);

    int pos = OStringSerializerHelper.getLowerIndexOf(iName, 0, ".", "[");

    String firstPart;
    String lastPart;
    if (pos > -1) {
      firstPart = iName.substring(0, pos);
      if (iName.charAt(pos) == '.')
        pos++;
      lastPart = iName.substring(pos);
      if (firstPart.equalsIgnoreCase("PARENT") && parent != null) {
        // UP TO THE PARENT
        if (lastPart.startsWith("$"))
          result = parent.getVariable(lastPart.substring(1));
        else
          result = ODocumentHelper.getFieldValue(parent, lastPart);

        return result != null ? result : iDefault;

      } else if (firstPart.equalsIgnoreCase("ROOT")) {
        OCommandContext p = this;
        while (p.getParent() != null)
          p = p.getParent();

        if (lastPart.startsWith("$"))
          result = p.getVariable(lastPart.substring(1));
        else
          result = ODocumentHelper.getFieldValue(p, lastPart, this);

        return result != null ? result : iDefault;
      }
    } else {
      firstPart = iName;
      lastPart = null;
    }

    if (firstPart.equalsIgnoreCase("CONTEXT"))
      result = getVariables();
    else if (firstPart.equalsIgnoreCase("PARENT"))
      result = parent;
    else if (firstPart.equalsIgnoreCase("ROOT")) {
      OCommandContext p = this;
      while (p.getParent() != null)
        p = p.getParent();
      result = p;
    } else {
      if (variables != null && variables.containsKey(firstPart))
        result = variables.get(firstPart);
      else if (child != null)
        result = child.getVariable(firstPart);
    }

    if (pos > -1)
      result = ODocumentHelper.getFieldValue(result, lastPart, this);

    return result != null ? result : iDefault;
  }

  public OCommandContext setVariable(String iName, final Object iValue) {
    if (iName == null)
      return null;

    if (iName.startsWith("$"))
      iName = iName.substring(1);

    init();

    int pos = OStringSerializerHelper.getHigherIndexOf(iName, 0, ".", "[");
    if (pos > -1) {
      Object nested = getVariable(iName.substring(0, pos));
      if (nested != null && nested instanceof OCommandContext)
        ((OCommandContext) nested).setVariable(iName.substring(pos + 1), iValue);
    } else
      variables.put(iName, iValue);
    return this;
  }

  @Override
  public OCommandContext incrementVariable(String iName) {
    if (iName != null) {
      if (iName.startsWith("$"))
        iName = iName.substring(1);

      init();

      int pos = OStringSerializerHelper.getHigherIndexOf(iName, 0, ".", "[");
      if (pos > -1) {
        Object nested = getVariable(iName.substring(0, pos));
        if (nested != null && nested instanceof OCommandContext)
          ((OCommandContext) nested).incrementVariable(iName.substring(pos + 1));
      } else {
        final Object v = variables.get(iName);
        if (v == null)
          variables.put(iName, 1);
        else if (v instanceof Number)
          variables.put(iName, OType.increment((Number) v, 1));
        else
          throw new IllegalArgumentException("Variable '" + iName + "' is not a number, but: " + v.getClass());
      }
    }
    return this;
  }

  public long updateMetric(final String iName, final long iValue) {
    if (!recordMetrics)
      return -1;

    init();
    Long value = (Long) variables.get(iName);
    if (value == null)
      value = iValue;
    else
      value = new Long(value.longValue() + iValue);
    variables.put(iName, value);
    return value.longValue();
  }

  /**
   * Returns a read-only map with all the variables.
   */
  public Map<String, Object> getVariables() {
    final HashMap<String, Object> map = new HashMap<String, Object>();
    if (child != null)
      map.putAll(child.getVariables());

    if (variables != null)
      map.putAll(variables);

    return map;
  }

  /**
   * Set the inherited context avoiding to copy all the values every time.
   * 
   * @return
   */
  public OCommandContext setChild(final OCommandContext iContext) {
    if (iContext == null) {
      if (child != null) {
        // REMOVE IT
        child.setParent(null);
        child = null;
      }

    } else if (child != iContext) {
      // ADD IT
      child = iContext;
      iContext.setParent(this);
    }
    return this;
  }

  public OCommandContext getParent() {
    return parent;
  }

  public OCommandContext setParent(final OCommandContext iParentContext) {
    if (parent != iParentContext) {
      parent = iParentContext;
      if (parent != null)
        parent.setChild(this);
    }
    return this;
  }

  @Override
  public String toString() {
    return getVariables().toString();
  }

  public boolean isRecordingMetrics() {
    return recordMetrics;
  }

  public OCommandContext setRecordingMetrics(final boolean recordMetrics) {
    this.recordMetrics = recordMetrics;
    return this;
  }

  @Override
  public void beginExecution(final long iTimeout, final TIMEOUT_STRATEGY iStrategy) {
    if (iTimeout > 0) {
      executionStartedOn = System.currentTimeMillis();
      timeoutMs = iTimeout;
      timeoutStrategy = iStrategy;
    }
  }

  public boolean checkTimeout() {
    if (timeoutMs > 0) {
      if (System.currentTimeMillis() - executionStartedOn > timeoutMs) {
        // TIMEOUT!
        switch (timeoutStrategy) {
        case RETURN:
          return false;
        case EXCEPTION:
          throw new OTimeoutException("Command execution timeout exceed (" + timeoutMs + "ms)");
        }
      }
    } else if (parent != null)
      // CHECK THE TIMER OF PARENT CONTEXT
      return parent.checkTimeout();

    return true;
  }

  private void init() {
    if (variables == null)
      variables = new HashMap<String, Object>();
  }

}


File: core/src/main/java/com/orientechnologies/orient/core/command/OCommandContext.java
/*
  *
  *  *  Copyright 2014 Orient Technologies LTD (info(at)orientechnologies.com)
  *  *
  *  *  Licensed under the Apache License, Version 2.0 (the "License");
  *  *  you may not use this file except in compliance with the License.
  *  *  You may obtain a copy of the License at
  *  *
  *  *       http://www.apache.org/licenses/LICENSE-2.0
  *  *
  *  *  Unless required by applicable law or agreed to in writing, software
  *  *  distributed under the License is distributed on an "AS IS" BASIS,
  *  *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  *  *  See the License for the specific language governing permissions and
  *  *  limitations under the License.
  *  *
  *  * For more information: http://www.orientechnologies.com
  *
  */
package com.orientechnologies.orient.core.command;

import com.orientechnologies.common.concur.OTimeoutException;

import java.util.Map;

/**
 * Basic interface for commands. Manages the context variables during execution.
 * 
 * @author Luca Garulli (l.garulli--at--orientechnologies.com)
 * 
 */
public interface OCommandContext {
  public enum TIMEOUT_STRATEGY {
    RETURN, EXCEPTION
  }

  public Object getVariable(String iName);

  public Object getVariable(String iName, Object iDefaultValue);

  public OCommandContext setVariable(String iName, Object iValue);

  public OCommandContext incrementVariable(String getNeighbors);

  public Map<String, Object> getVariables();

  public OCommandContext getParent();

  public OCommandContext setParent(OCommandContext iParentContext);

  public OCommandContext setChild(OCommandContext context);

  /**
   * Updates a counter. Used to record metrics.
   * 
   * @param iName
   *          Metric's name
   * @param iValue
   *          delta to add or subtract
   * @return
   */
  public long updateMetric(String iName, long iValue);

  public boolean isRecordingMetrics();

  public OCommandContext setRecordingMetrics(boolean recordMetrics);

  public void beginExecution(long timeoutMs, TIMEOUT_STRATEGY iStrategy);

  /**
   * Check if timeout is elapsed, if defined.
   * 
   * @return false if it the timeout is elapsed and strategy is "return"
   * @exception OTimeoutException
   *              if the strategy is "exception" (default)
   */
  public boolean checkTimeout();
}


File: core/src/main/java/com/orientechnologies/orient/core/sql/parser/OEqualsCompareOperator.java
/* Generated By:JJTree: Do not edit this line. OEqualsCompareOperator.java Version 4.3 */
/* JavaCCOptions:MULTI=true,NODE_USES_PARSER=false,VISITOR=true,TRACK_TOKENS=true,NODE_PREFIX=O,NODE_EXTENDS=,NODE_FACTORY=,SUPPORT_CLASS_VISIBILITY_PUBLIC=true */
package com.orientechnologies.orient.core.sql.parser;

public class OEqualsCompareOperator extends SimpleNode implements OBinaryCompareOperator {
  public OEqualsCompareOperator(int id) {
    super(id);
  }

  public OEqualsCompareOperator(OrientSql p, int id) {
    super(p, id);
  }

  /** Accept the visitor. **/
  public Object jjtAccept(OrientSqlVisitor visitor, Object data) {
    return visitor.visit(this, data);
  }

  @Override
  public boolean execute(Object left, Object right) {
    if (left == null) {
      return right == null;
    }
    return left.equals(right);// TODO type conversions
  }

  @Override
  public String toString() {
    return "=";
  }
}
/* JavaCC - OriginalChecksum=bd2ec5d13a1d171779c2bdbc9d3a56bc (do not edit this line) */


File: core/src/main/java/com/orientechnologies/orient/core/sql/parser/OExpression.java
/* Generated By:JJTree: Do not edit this line. OExpression.java Version 4.3 */
/* JavaCCOptions:MULTI=true,NODE_USES_PARSER=false,VISITOR=true,TRACK_TOKENS=true,NODE_PREFIX=O,NODE_EXTENDS=,NODE_FACTORY=,SUPPORT_CLASS_VISIBILITY_PUBLIC=true */
package com.orientechnologies.orient.core.sql.parser;

import com.orientechnologies.orient.core.command.OCommandContext;
import com.orientechnologies.orient.core.db.record.OIdentifiable;

import java.util.Map;

public class OExpression extends SimpleNode {

  protected Boolean singleQuotes;
  protected Boolean doubleQuotes;

  public OExpression(int id) {
    super(id);
  }

  public OExpression(OrientSql p, int id) {
    super(p, id);
  }

  /** Accept the visitor. **/
  public Object jjtAccept(OrientSqlVisitor visitor, Object data) {
    return visitor.visit(this, data);
  }


  public Object execute(OIdentifiable iCurrentRecord, OCommandContext ctx) {
    if (value instanceof ORid) {
      return null;// TODO
    } else if (value instanceof OInputParameter) {
      return null;// TODO
    } else if (value instanceof OMathExpression) {
      return ((OMathExpression) value).execute(iCurrentRecord, ctx);
//      return null;// TODO ((OMathExpression) value).execute();
    } else if (value instanceof OJson) {
      return null;// TODO
    } else if (value instanceof String) {
      return value;
    } else if (value instanceof Number) {
      return value;
    }

    return value;

  }

  public String getDefaultAlias() {

    if (value instanceof String) {
      return (String) value;
    }
    // TODO create an interface for this;

    // if (value instanceof ORid) {
    // return null;// TODO
    // } else if (value instanceof OInputParameter) {
    // return null;// TODO
    // } else if (value instanceof OMathExpression) {
    // return null;// TODO
    // } else if (value instanceof OJson) {
    // return null;// TODO
    // }

    return "" + value;

  }

  @Override
  public String toString() {
    if (value == null) {
      return "null";
    } else if (value instanceof SimpleNode) {
      return value.toString();
    } else if (value instanceof String) {
      if (Boolean.TRUE.equals(singleQuotes)) {
        return "'" + value + "'";
      }
      return "\"" + value + "\"";
    } else {
      return "" + value;
    }
  }

  public static String encode(String s) {
    return s.replaceAll("\"", "\\\\\"");
  }

  public void replaceParameters(Map<Object, Object> params) {
    if (value instanceof OInputParameter) {
      value = ((OInputParameter) value).bindFromInputParams(params);
    } else if (value instanceof OBaseExpression) {
      ((OBaseExpression) value).replaceParameters(params);
    }
  }
}
/* JavaCC - OriginalChecksum=9c860224b121acdc89522ae97010be01 (do not edit this line) */


File: core/src/main/java/com/orientechnologies/orient/core/sql/parser/OMatchStatement.java
/* Generated By:JJTree: Do not edit this line. OMatchStatement.java Version 4.3 */
/* JavaCCOptions:MULTI=true,NODE_USES_PARSER=false,VISITOR=true,TRACK_TOKENS=true,NODE_PREFIX=O,NODE_EXTENDS=,NODE_FACTORY=,SUPPORT_CLASS_VISIBILITY_PUBLIC=true */
package com.orientechnologies.orient.core.sql.parser;

import com.orientechnologies.common.listener.OProgressListener;
import com.orientechnologies.orient.core.command.*;
import com.orientechnologies.orient.core.db.document.ODatabaseDocument;
import com.orientechnologies.orient.core.db.record.OIdentifiable;
import com.orientechnologies.orient.core.exception.OCommandExecutionException;
import com.orientechnologies.orient.core.metadata.schema.OClass;
import com.orientechnologies.orient.core.metadata.schema.OSchema;
import com.orientechnologies.orient.core.metadata.security.ORole;
import com.orientechnologies.orient.core.metadata.security.ORule;
import com.orientechnologies.orient.core.record.ORecord;
import com.orientechnologies.orient.core.record.impl.ODocument;
import com.orientechnologies.orient.core.sql.OCommandSQLParsingException;
import com.orientechnologies.orient.core.sql.OIterableRecordSource;
import com.orientechnologies.orient.core.sql.filter.OSQLTarget;
import com.orientechnologies.orient.core.sql.query.OResultSet;
import com.orientechnologies.orient.core.sql.query.OSQLAsynchQuery;
import com.orientechnologies.orient.core.sql.query.OSQLSynchQuery;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.*;

public class OMatchStatement extends OStatement implements OCommandExecutor, OIterableRecordSource {

  String                             DEFAULT_ALIAS_PREFIX = "$ORIENT_DEFAULT_ALIAS_";

  private OSQLAsynchQuery<ODocument> request;

  long                               threshold            = 5;

  @Override
  public Iterator<OIdentifiable> iterator(Map<Object, Object> iArgs) {
    if (context == null) {
      context = new OBasicCommandContext();
    }
    Object result = execute(iArgs);
    return ((Iterable) result).iterator();
  }

  class MatchContext {
    String                     root;
    Map<String, Iterable>      candidates   = new HashMap<String, Iterable>();
    Map<String, OIdentifiable> matched      = new HashMap<String, OIdentifiable>();
    Map<PatternEdge, Boolean>  matchedEdges = new IdentityHashMap<PatternEdge, Boolean>();

    public MatchContext copy(String alias, OIdentifiable value) {
      MatchContext result = new MatchContext();
      result.root = alias;

      result.candidates.putAll(candidates);
      result.candidates.remove(alias);

      result.matched.putAll(matched);
      result.matched.put(alias, value);

      result.matchedEdges.putAll(matchedEdges);
      return result;
    }
  }

  class Pattern {
    Map<String, PatternNode> aliasToNode = new HashMap<String, PatternNode>();
    int                      numOfEdges  = 0;

    void addExpression(OMatchExpression expression) {
      PatternNode originNode = getOrCreateNode(expression.origin);

      for (OMatchPathItem item : expression.items) {
        String nextAlias = item.filter.getAlias();
        PatternNode nextNode = getOrCreateNode(item.filter);

        numOfEdges += originNode.addEdge(item, nextNode);
        originNode = nextNode;
      }
    }

    private PatternNode getOrCreateNode(OMatchFilter origin) {
      PatternNode originNode = get(origin.getAlias());
      if (originNode == null) {
        originNode = new PatternNode();
        originNode.alias = origin.getAlias();
        aliasToNode.put(originNode.alias, originNode);
      }
      return originNode;
    }

    PatternNode get(String alias) {
      return aliasToNode.get(alias);
    }

    int getNumOfEdges() {
      return numOfEdges;
    }
  }

  class PatternNode {
    String           alias;
    Set<PatternEdge> out        = new HashSet<PatternEdge>();
    Set<PatternEdge> in         = new HashSet<PatternEdge>();
    int              centrality = 0;

    int addEdge(OMatchPathItem item, PatternNode to) {
      PatternEdge edge = new PatternEdge();
      edge.item = item;
      edge.out = this;
      edge.in = to;
      this.out.add(edge);
      to.in.add(edge);
      return 1;
    }
  }

  class PatternEdge {
    PatternNode    in;
    PatternNode    out;
    OMatchPathItem item;
  }

  public static final String       KEYWORD_MATCH    = "MATCH";
  // parsed data
  protected List<OMatchExpression> matchExpressions = new ArrayList<OMatchExpression>();
  protected List<OIdentifier>      returnItems      = new ArrayList<OIdentifier>();

  protected Pattern                pattern;

  // execution data
  private OCommandContext          context;
  private OProgressListener        progressListener;

  public OMatchStatement() {
    super(-1);
  }

  public OMatchStatement(int id) {
    super(id);
  }

  public OMatchStatement(OrientSql p, int id) {
    super(p, id);
  }

  /**
   * Accept the visitor. *
   */
  public Object jjtAccept(OrientSqlVisitor visitor, Object data) {
    return visitor.visit(this, data);
  }

  @Override
  public <RET extends OCommandExecutor> RET parse(OCommandRequest iRequest) {
    final OCommandRequestText textRequest = (OCommandRequestText) iRequest;
    if (iRequest instanceof OSQLSynchQuery) {
      request = (OSQLSynchQuery<ODocument>) iRequest;
    } else if (iRequest instanceof OSQLAsynchQuery) {
      request = (OSQLAsynchQuery<ODocument>) iRequest;
    } else {
      // BUILD A QUERY OBJECT FROM THE COMMAND REQUEST
      request = new OSQLSynchQuery<ODocument>(textRequest.getText());
      if (textRequest.getResultListener() != null) {
        request.setResultListener(textRequest.getResultListener());
      }
    }
    String queryText = textRequest.getText();

    // please, do not look at this... refactor this ASAP with new executor structure
    final InputStream is = new ByteArrayInputStream(queryText.getBytes());
    final OrientSql osql = new OrientSql(is);
    try {
      OMatchStatement result = (OMatchStatement) osql.parse();
      this.matchExpressions = result.matchExpressions;
      this.returnItems = result.returnItems;
    } catch (ParseException e) {
      throw new OCommandSQLParsingException(e.getMessage(), e);
    }

    assignDefaultAliases(this.matchExpressions);
    pattern = new Pattern();
    for (OMatchExpression expr : this.matchExpressions) {
      pattern.addExpression(expr);
    }
    // TODO CHECK CORRECT RETURN STATEMENT!

    return (RET) this;
  }

  private void assignDefaultAliases(List<OMatchExpression> matchExpressions) {

    int counter = 0;
    for (OMatchExpression expression : matchExpressions) {
      if (expression.origin.getAlias() == null) {
        expression.origin.setAlias(DEFAULT_ALIAS_PREFIX + (counter++));
      }

      for (OMatchPathItem item : expression.items) {
        if (item.filter == null) {
          item.filter = new OMatchFilter(-1);
        }
        if (item.filter.getAlias() == null) {
          item.filter.setAlias(DEFAULT_ALIAS_PREFIX + (counter++));
        }
      }
    }
  }

  @Override
  public Object execute(Map<Object, Object> iArgs) {
    return execute(iArgs, this.request);
  }

  public Object execute(Map<Object, Object> iArgs, OSQLAsynchQuery<ODocument> request) {
    try {
      Map<String, OWhereClause> aliasFilters = new HashMap<String, OWhereClause>();
      Map<String, String> aliasClasses = new HashMap<String, String>();
      for (OMatchExpression expr : this.matchExpressions) {
        addAliases(expr, aliasFilters, aliasClasses);
      }

      Map<String, Long> estimatedRootEntries = estimateRootEntries(aliasClasses, aliasFilters);
      if (estimatedRootEntries.values().contains(0l)) {
        return new OResultSet();// some aliases do not match on any classes
      }

      calculateMatch(estimatedRootEntries, new MatchContext(), aliasClasses, aliasFilters, this.context, request);
      return getResult(request);
    } finally {

      if (request.getResultListener() != null) {
        request.getResultListener().end();
      }
    }

  }

  protected Object getResult(OSQLAsynchQuery<ODocument> request) {
    if (request instanceof OSQLSynchQuery)
      return ((OSQLSynchQuery<ODocument>) request).getResult();

    return null;
  }

  private boolean calculateMatch(Map<String, Long> estimatedRootEntries, MatchContext matchContext,
      Map<String, String> aliasClasses, Map<String, OWhereClause> aliasFilters, OCommandContext iCommandContext,
      OSQLAsynchQuery<ODocument> request) {
    return calculateMatch(pattern, estimatedRootEntries, matchContext, aliasClasses, aliasFilters, iCommandContext, request);

  }

  private boolean calculateMatch(Pattern pattern, Map<String, Long> estimatedRootEntries, MatchContext matchContext,
      Map<String, String> aliasClasses, Map<String, OWhereClause> aliasFilters, OCommandContext iCommandContext,
      OSQLAsynchQuery<ODocument> request) {

    List<MatchContext> activeContexts = new LinkedList<MatchContext>();

    MatchContext rootContext = new MatchContext();

    String smallestAlias = null;
    Long smallestAmount = Long.MAX_VALUE;
    boolean rootFound = false;
    // find starting nodes with few entries
    for (Map.Entry<String, Long> entryPoint : estimatedRootEntries.entrySet()) {
      if (entryPoint.getValue() < threshold) {
        String nextAlias = entryPoint.getKey();
        Iterable<OIdentifiable> matches = calculateMatches(nextAlias, aliasFilters, iCommandContext, aliasClasses);

        Set<OIdentifiable> ids = new HashSet<OIdentifiable>();
        if (!matches.iterator().hasNext()) {
          return true;
        }

        rootContext.candidates.put(nextAlias, matches);
        long thisAmount;
        if (matches instanceof Collection) {
          thisAmount = (long) ((Collection) matches).size();
        } else {
          thisAmount = estimatedRootEntries.get(nextAlias);
        }
        if (thisAmount <= smallestAmount) {
          smallestAlias = nextAlias;
          smallestAmount = thisAmount;
        }
        rootFound = true;
      }
    }
    // no nodes under threshold, guess the smallest one
    if (!rootFound) {
      String nextAlias = getNextAlias(estimatedRootEntries, matchContext);
      Iterable<OIdentifiable> matches = calculateMatches(nextAlias, aliasFilters, iCommandContext, aliasClasses);
      if (!matches.iterator().hasNext()) {
        return true;
      }
      smallestAlias = nextAlias;
      rootContext.candidates.put(nextAlias, matches);
    }

    Iterable<OIdentifiable> allCandidates = rootContext.candidates.get(smallestAlias);

    for (OIdentifiable id : allCandidates) {
      MatchContext childContext = rootContext.copy(smallestAlias, id);
      activeContexts.add(childContext);
    }

    while (!activeContexts.isEmpty()) {
      if (!processContext(pattern, estimatedRootEntries, activeContexts.remove(0), aliasClasses, aliasFilters, iCommandContext,
          request)) {
        return true;
      }
    }
    return true;
  }

  private Iterable<OIdentifiable> calculateMatches(String nextAlias, Map<String, OWhereClause> aliasFilters,
      OCommandContext iCommandContext, Map<String, String> aliasClasses) {
    Iterable<OIdentifiable> it = query(aliasClasses.get(nextAlias), aliasFilters.get(nextAlias), iCommandContext);
    Set<OIdentifiable> result = new HashSet<OIdentifiable>();
    // TODO dirty work around, review it. The iterable returned by the query just does not work.
    for (OIdentifiable id : it) {
      result.add(id.getIdentity());
    }

    return result;
  }

  private boolean processContext(Pattern pattern, Map<String, Long> estimatedRootEntries, MatchContext matchContext,
      Map<String, String> aliasClasses, Map<String, OWhereClause> aliasFilters, OCommandContext iCommandContext,
      OSQLAsynchQuery<ODocument> request) {

    if (pattern.getNumOfEdges() == matchContext.matchedEdges.size()) {
      addResult(matchContext, request);
      return true;
    }
    PatternNode rootNode = pattern.get(matchContext.root);
    Iterator<PatternEdge> edgeIterator = rootNode.out.iterator();
    while (edgeIterator.hasNext()) {
      PatternEdge outEdge = edgeIterator.next();

      if (!matchContext.matchedEdges.containsKey(outEdge)) {

        Object rightValues = executeTraversal(matchContext, iCommandContext, outEdge);
        if (!(rightValues instanceof Iterable)) {
          rightValues = Collections.singleton(rightValues);
        }
        for (OIdentifiable rightValue : (Iterable<OIdentifiable>) rightValues) {
          Iterable<OIdentifiable> prevMatchedRightValues = matchContext.candidates.get(outEdge.in.alias);

          if (prevMatchedRightValues != null && prevMatchedRightValues.iterator().hasNext()) {// just matching against known values
            for (OIdentifiable id : prevMatchedRightValues) {
              if (id.getIdentity().equals(rightValue.getIdentity())) {
                MatchContext childContext = matchContext.copy(outEdge.in.alias, id);
                if (edgeIterator.hasNext()) {
                  childContext.root = rootNode.alias;
                } else {
                  childContext.root = calculateNextRoot(pattern, childContext);
                }
                childContext.matchedEdges.put(outEdge, true);
                if (!processContext(pattern, estimatedRootEntries, childContext, aliasClasses, aliasFilters, iCommandContext,
                    request)) {
                  return false;
                }
              }
            }
          } else {// searching for neighbors
            OWhereClause where = aliasFilters.get(outEdge.in.alias);
            if (where == null || where.matchesFilters(rightValue, iCommandContext)) {
              MatchContext childContext = matchContext.copy(outEdge.in.alias, rightValue.getIdentity());
              if (edgeIterator.hasNext()) {
                childContext.root = rootNode.alias;
              } else {
                childContext.root = calculateNextRoot(pattern, childContext);
              }
              childContext.matchedEdges.put(outEdge, true);
              if (!processContext(pattern, estimatedRootEntries, childContext, aliasClasses, aliasFilters, iCommandContext, request)) {
                return false;
              }
            }
          }
        }
      }
    }
    edgeIterator = rootNode.in.iterator();
    while (edgeIterator.hasNext()) {
      PatternEdge inEdge = edgeIterator.next();
      if (!inEdge.item.isBidirectional()) {
        continue;
      }
      edgeIterator.remove();
      if (!matchContext.matchedEdges.containsKey(inEdge)) {
        Object leftValues = inEdge.item.method.executeReverse(matchContext.matched.get(matchContext.root), iCommandContext);
        if (!(leftValues instanceof Iterable)) {
          leftValues = Collections.singleton(leftValues);
        }
        for (OIdentifiable leftValue : (Iterable<OIdentifiable>) leftValues) {
          Iterable<OIdentifiable> prevMatchedRightValues = matchContext.candidates.get(inEdge.out.alias);

          if (prevMatchedRightValues.iterator().hasNext()) {// just matching against known values
            for (OIdentifiable id : prevMatchedRightValues) {
              if (id.getIdentity().equals(leftValue.getIdentity())) {
                MatchContext childContext = matchContext.copy(inEdge.out.alias, id);
                if (edgeIterator.hasNext()) {
                  childContext.root = rootNode.alias;
                } else {
                  childContext.root = calculateNextRoot(pattern, childContext);
                }
                childContext.matchedEdges.put(inEdge, true);

                if (!processContext(pattern, estimatedRootEntries, childContext, aliasClasses, aliasFilters, iCommandContext,
                    request)) {
                  return false;
                }
              }
            }
          } else {// searching for neighbors
            OWhereClause where = aliasFilters.get(inEdge.out.alias);
            if (where == null || where.matchesFilters(leftValue, iCommandContext)) {
              MatchContext childContext = matchContext.copy(inEdge.out.alias, leftValue.getIdentity());
              if (edgeIterator.hasNext()) {
                childContext.root = rootNode.alias;
              } else {
                childContext.root = calculateNextRoot(pattern, childContext);
              }
              childContext.matchedEdges.put(inEdge, true);
              if (!processContext(pattern, estimatedRootEntries, childContext, aliasClasses, aliasFilters, iCommandContext, request)) {
                return false;
              }
            }
          }
        }
      }
    }

    return true;
  }

  private String calculateNextRoot(Pattern pattern, MatchContext ctx) {
    return ctx.root;// TODO...?
  }

  private Object executeTraversal(MatchContext matchContext, OCommandContext iCommandContext, PatternEdge outEdge) {
    Iterable<OIdentifiable> queryResult = (Iterable) outEdge.item.method.execute(matchContext.matched.get(matchContext.root),
        iCommandContext);
    if (outEdge.item.filter == null || outEdge.item.filter.getFilter() == null) {
      return queryResult;
    }
    OWhereClause filter = outEdge.item.filter.getFilter();
    Set<OIdentifiable> result = new HashSet<OIdentifiable>();

    for (OIdentifiable origin : queryResult) {
      if (filter.matchesFilters(origin, iCommandContext)) {
        result.add(origin);
      }
    }
    return result;
  }

  private void addResult(MatchContext matchContext, OSQLAsynchQuery<ODocument> request) {
    if (returnsMatches()) {
      ODocument doc = getDatabase().newInstance();
      for (Map.Entry<String, OIdentifiable> entry : matchContext.matched.entrySet()) {
        if (isExplicitAlias(entry.getKey())) {
          doc.field(entry.getKey(), entry.getValue());
        }
      }
      Object result = getResult(request);

      if (request.getResultListener() != null) {
        request.getResultListener().result(doc);
      }
    } else if (returnsPaths()) {
      ODocument doc = getDatabase().newInstance();
      for (Map.Entry<String, OIdentifiable> entry : matchContext.matched.entrySet()) {
        doc.field(entry.getKey(), entry.getValue());
      }
      Object result = getResult(request);

      if (request.getResultListener() != null) {
        request.getResultListener().result(doc);
      }
    }
  }

  private boolean isExplicitAlias(String key) {
    if (key.startsWith(DEFAULT_ALIAS_PREFIX)) {
      return false;
    }
    return true;
  }

  private boolean returnsMatches() {
    for (OIdentifier item : returnItems) {
      if (item.getValue().equals("$matches")) {
        return true;
      }
    }
    return false;
  }

  private boolean returnsPaths() {
    for (OIdentifier item : returnItems) {
      if (item.getValue().equals("$paths")) {
        return true;
      }
    }
    return false;
  }

  private Iterable<OIdentifiable> query(String className, OWhereClause oWhereClause, OCommandContext ctx) {
    final ODatabaseDocument database = getDatabase();
    OClass schemaClass = database.getMetadata().getSchema().getClass(className);
    database.checkSecurity(ORule.ResourceGeneric.CLASS, ORole.PERMISSION_READ, schemaClass.getName().toLowerCase());

    Iterable<ORecord> baseIterable = fetchFromIndex(schemaClass, oWhereClause);
    // if (baseIterable == null) {
    // baseIterable = new ORecordIteratorClass<ORecord>((ODatabaseDocumentInternal) database, (ODatabaseDocumentInternal) database,
    // className, true, true);
    // }
    // Iterable<OIdentifiable> result = new FilteredIterator(baseIterable, oWhereClause);

    String text;

    if (oWhereClause == null) {
      text = "(select from " + className + ")";
    } else {
      text = "(select from " + className + " where " + oWhereClause.toString() + ")";
    }
    OSQLTarget target = new OSQLTarget(text, ctx, "where");

    return (Iterable) target.getTargetRecords();
  }

  private Iterable<ORecord> fetchFromIndex(OClass schemaClass, OWhereClause oWhereClause) {
    return null;// TODO
  }

  private String getNextAlias(Map<String, Long> estimatedRootEntries, MatchContext matchContext) {
    Map.Entry<String, Long> lowerValue = null;
    for (Map.Entry<String, Long> entry : estimatedRootEntries.entrySet()) {
      if (matchContext.matched.containsKey(entry.getKey())) {
        continue;
      }
      if (lowerValue == null) {
        lowerValue = entry;
      } else if (lowerValue.getValue() > entry.getValue()) {
        lowerValue = entry;
      }
    }

    return lowerValue.getKey();
  }

  private Map<String, Long> estimateRootEntries(Map<String, String> aliasClasses, Map<String, OWhereClause> aliasFilters) {
    Set<String> allAliases = new HashSet<String>();
    allAliases.addAll(aliasClasses.keySet());
    allAliases.addAll(aliasFilters.keySet());

    OSchema schema = getDatabase().getMetadata().getSchema();

    Map<String, Long> result = new HashMap<String, Long>();
    for (String alias : allAliases) {
      String className = aliasClasses.get(alias);
      if (className == null) {
        continue;
      }

      if (!schema.existsClass(className)) {
        throw new OCommandExecutionException("class not defined: " + className);
      }
      OClass oClass = schema.getClass(className);
      long upperBound;
      OWhereClause filter = aliasFilters.get(alias);
      if (filter != null) {
        upperBound = filter.estimate(oClass);
      } else {
        upperBound = oClass.count();
      }
      result.put(alias, upperBound);
    }
    return result;
  }

  private void addAliases(OMatchExpression expr, Map<String, OWhereClause> aliasFilters, Map<String, String> aliasClasses) {
    addAliases(expr.origin, aliasFilters, aliasClasses);
    for (OMatchPathItem item : expr.items) {
      if (item.filter != null) {
        addAliases(item.filter, aliasFilters, aliasClasses);
      }
    }
  }

  private void addAliases(OMatchFilter matchFilter, Map<String, OWhereClause> aliasFilters, Map<String, String> aliasClasses) {
    String alias = matchFilter.getAlias();
    OWhereClause filter = matchFilter.getFilter();
    if (alias != null) {
      if (filter != null && filter.baseExpression != null) {
        OWhereClause previousFilter = aliasFilters.get(alias);
        if (previousFilter == null) {
          previousFilter = new OWhereClause(-1);
          previousFilter.baseExpression = new OAndBlock(-1);
          aliasFilters.put(alias, previousFilter);
        }
        OAndBlock filterBlock = (OAndBlock) previousFilter.baseExpression;
        if (filter != null && filter.baseExpression != null) {
          filterBlock.subBlocks.add(filter.baseExpression);
        }
      }

      String clazz = matchFilter.getClassName();
      if (clazz != null) {
        String previousClass = aliasClasses.get(alias);
        if (previousClass == null) {
          aliasClasses.put(alias, clazz);
        } else {
          String lower = getLowerSubclass(clazz, previousClass);
          if (lower == null) {
            throw new OCommandExecutionException("classes defined for alias " + alias + " (" + clazz + ", " + previousClass
                + ") are not in the same hierarchy");
          }
          aliasClasses.put(alias, lower);
        }
      }
    }
  }

  private String getLowerSubclass(String className1, String className2) {
    OSchema schema = getDatabase().getMetadata().getSchema();
    OClass class1 = schema.getClass(className1);
    OClass class2 = schema.getClass(className2);
    if (class1.isSubClassOf(class2)) {
      return class1.getName();
    }
    if (class2.isSubClassOf(class1)) {
      return class2.getName();
    }
    return null;
  }

  @Override
  public <RET extends OCommandExecutor> RET setProgressListener(OProgressListener progressListener) {

    this.progressListener = progressListener;
    return (RET) this;
  }

  @Override
  public <RET extends OCommandExecutor> RET setLimit(int iLimit) {
    // TODO
    return (RET) this;
    // throw new UnsupportedOperationException();
  }

  @Override
  public String getFetchPlan() {
    return null;
  }

  @Override
  public Map<Object, Object> getParameters() {
    return null;
  }

  @Override
  public OCommandContext getContext() {
    return context;
  }

  @Override
  public void setContext(OCommandContext context) {
    this.context = context;
  }

  @Override
  public boolean isIdempotent() {
    return true;
  }

  @Override
  public Set<String> getInvolvedClusters() {
    return Collections.EMPTY_SET;
  }

  @Override
  public int getSecurityOperationType() {
    return ORole.PERMISSION_READ;
  }

  @Override
  public boolean involveSchema() {
    return false;
  }

  @Override
  public long getTimeout() {
    return -1;
  }

  @Override
  public String getSyntax() {
    return "MATCH <match-statement> [, <match-statement] RETURN <alias>[, <alias>]";
  }

  @Override
  public boolean isLocalExecution() {
    return false;
  }

  @Override
  public String toString() {
    StringBuilder result = new StringBuilder();
    result.append(KEYWORD_MATCH);
    result.append(" ");
    boolean first = true;
    for (OMatchExpression expr : this.matchExpressions) {
      if (!first) {
        result.append(", ");
      }
      result.append(expr.toString());
      first = false;
    }
    result.append(" RETURN ");
    first = true;
    for (OIdentifier expr : this.returnItems) {
      if (!first) {
        result.append(", ");
      }
      result.append(expr.toString());
      first = false;
    }
    return result.toString();
  }
}
/* JavaCC - OriginalChecksum=6ff0afbe9d31f08b72159fcf24070c9f (do not edit this line) */


File: core/src/main/java/com/orientechnologies/orient/core/sql/parser/OMathExpression.java
/* Generated By:JJTree: Do not edit this line. OMathExpression.java Version 4.3 */
/* JavaCCOptions:MULTI=true,NODE_USES_PARSER=false,VISITOR=true,TRACK_TOKENS=true,NODE_PREFIX=O,NODE_EXTENDS=,NODE_FACTORY=,SUPPORT_CLASS_VISIBILITY_PUBLIC=true */
package com.orientechnologies.orient.core.sql.parser;

import com.orientechnologies.orient.core.command.OCommandContext;
import com.orientechnologies.orient.core.db.record.OIdentifiable;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class OMathExpression extends SimpleNode {

  public enum Operator {
    PLUS {
      @Override
      public Number apply(Integer left, Integer right) {
        final Integer sum = left + right;
        if (sum < 0 && left.intValue() > 0 && right.intValue() > 0)
          // SPECIAL CASE: UPGRADE TO LONG
          return left.longValue() + right;
        return sum;
      }

      @Override
      public Number apply(Long left, Long right) {
        return left + right;
      }

      @Override
      public Number apply(Float left, Float right) {
        return left + right;
      }

      @Override
      public Number apply(Double left, Double right) {
        return left + right;
      }

      @Override
      public Number apply(BigDecimal left, BigDecimal right) {
        return left.add(right);
      }
    },
    MINUS {
      @Override
      public Number apply(Integer left, Integer right) {
        int result = left - right;
        if (result > 0 && left.intValue() < 0 && right.intValue() > 0)
          // SPECIAL CASE: UPGRADE TO LONG
          return left.longValue() - right;

        return result;
      }

      @Override
      public Number apply(Long left, Long right) {
        return left - right;
      }

      @Override
      public Number apply(Float left, Float right) {
        return left - right;
      }

      @Override
      public Number apply(Double left, Double right) {
        return left - right;
      }

      @Override
      public Number apply(BigDecimal left, BigDecimal right) {
        return left.subtract(right);
      }
    },
    STAR {
      @Override
      public Number apply(Integer left, Integer right) {
        return left * right;
      }

      @Override
      public Number apply(Long left, Long right) {
        return left * right;
      }

      @Override
      public Number apply(Float left, Float right) {
        return left * right;
      }

      @Override
      public Number apply(Double left, Double right) {
        return left * right;
      }

      @Override
      public Number apply(BigDecimal left, BigDecimal right) {
        return left.multiply(right);
      }
    },
    SLASH {
      @Override
      public Number apply(Integer left, Integer right) {
        return left / right;
      }

      @Override
      public Number apply(Long left, Long right) {
        return left / right;
      }

      @Override
      public Number apply(Float left, Float right) {
        return left / right;
      }

      @Override
      public Number apply(Double left, Double right) {
        return left / right;
      }

      @Override
      public Number apply(BigDecimal left, BigDecimal right) {
        return left.divide(right, BigDecimal.ROUND_HALF_UP);
      }
    },
    REM {
      @Override
      public Number apply(Integer left, Integer right) {
        return left % right;
      }

      @Override
      public Number apply(Long left, Long right) {
        return left % right;
      }

      @Override
      public Number apply(Float left, Float right) {
        return left % right;
      }

      @Override
      public Number apply(Double left, Double right) {
        return left % right;
      }

      @Override
      public Number apply(BigDecimal left, BigDecimal right) {
        return left.remainder(right);
      }
    };

    public abstract Number apply(Integer left, Integer right);

    public abstract Number apply(Long left, Long right);

    public abstract Number apply(Float left, Float right);

    public abstract Number apply(Double left, Double right);

    public abstract Number apply(BigDecimal left, BigDecimal right);

  }

  protected List<OMathExpression> childExpressions = new ArrayList<OMathExpression>();
  protected List<Operator>        operators        = new ArrayList<Operator>();

  public OMathExpression(int id) {
    super(id);
  }

  public OMathExpression(OrientSql p, int id) {
    super(p, id);
  }

  public void replaceParameters(Map<Object, Object> params) {
    if (childExpressions != null) {
      for (OMathExpression expr : childExpressions) {
        expr.replaceParameters(params);
      }
    }
  }

  public Object execute(OIdentifiable iCurrentRecord, OCommandContext ctx) {
    if (childExpressions.size() == 0) {
      return null;
    }

    OMathExpression nextExpression = childExpressions.get(0);
    Object nextValue = nextExpression.execute(iCurrentRecord, ctx);
    for (int i = 0; i < operators.size() && i + 1 < childExpressions.size(); i++) {
      Operator nextOperator = operators.get(i);
      Object rightValue = childExpressions.get(i + 1).execute(iCurrentRecord, ctx);
      nextValue = apply(nextValue, nextOperator, rightValue);
    }
    return null;
  }

  /** Accept the visitor. **/
  public Object jjtAccept(OrientSqlVisitor visitor, Object data) {
    return visitor.visit(this, data);
  }

  public List<OMathExpression> getChildExpressions() {
    return childExpressions;
  }

  public void setChildExpressions(List<OMathExpression> childExpressions) {
    this.childExpressions = childExpressions;
  }

  @Override
  public String toString() {
    StringBuilder result = new StringBuilder();

    for (int i = 0; i < childExpressions.size(); i++) {
      if (i > 0) {
        result.append(" ");
        switch (operators.get(i - 1)) {
        case PLUS:
          result.append("+");
          break;
        case MINUS:
          result.append("-");
          break;
        case STAR:
          result.append("*");
          break;
        case SLASH:
          result.append("/");
          break;
        case REM:
          result.append("%");
          break;
        }
        result.append(" ");
      }
      result.append(childExpressions.get(i).toString());
    }
    return result.toString();
  }

  public Object apply(final Object a, final Operator operation, final Object b) {
    if (b == null) {
      return a;
    }
    if (a == null) {
      return b;
    }
    if (a instanceof Number && b instanceof Number) {
      return apply((Number) a, operation, (Number) b);
    }
    throw new IllegalArgumentException("Cannot apply operaton " + operation + " to value '" + a + "' (" + a.getClass() + ") with '"
        + b + "' (" + b.getClass() + ")");

  }

  public Number apply(final Number a, final Operator operation, final Number b) {
    if (a == null || b == null)
      throw new IllegalArgumentException("Cannot increment a null value");

    if (a instanceof Integer || a instanceof Short) {
      if (b instanceof Integer || b instanceof Short) {
        return operation.apply(a.intValue(), b.intValue());
      } else if (b instanceof Long) {
        return operation.apply(a.longValue(), b.longValue());
      } else if (b instanceof Float)
        return operation.apply(a.floatValue(), b.floatValue());
      else if (b instanceof Double)
        return operation.apply(a.doubleValue(), b.doubleValue());
      else if (b instanceof BigDecimal)
        return operation.apply(new BigDecimal((Integer) a), (BigDecimal) b);
    } else if (a instanceof Long) {
      if (b instanceof Integer || b instanceof Long || b instanceof Short)
        return operation.apply(a.longValue(), b.longValue());
      else if (b instanceof Float)
        return operation.apply(a.floatValue(), b.floatValue());
      else if (b instanceof Double)
        return operation.apply(a.doubleValue(), b.doubleValue());
      else if (b instanceof BigDecimal)
        return operation.apply(new BigDecimal((Long) a), (BigDecimal) b);
    } else if (a instanceof Float) {
      if (b instanceof Short || b instanceof Integer || b instanceof Long || b instanceof Float)
        return operation.apply(a.floatValue(), b.floatValue());
      else if (b instanceof Double)
        return operation.apply(a.doubleValue(), b.doubleValue());
      else if (b instanceof BigDecimal)
        return operation.apply(new BigDecimal((Float) a), (BigDecimal) b);

    } else if (a instanceof Double) {
      if (b instanceof Short || b instanceof Integer || b instanceof Long || b instanceof Float || b instanceof Double)
        return operation.apply(a.doubleValue(), b.doubleValue());
      else if (b instanceof BigDecimal)
        return operation.apply(new BigDecimal((Double) a), (BigDecimal) b);

    } else if (a instanceof BigDecimal) {
      if (b instanceof Integer)
        return operation.apply((BigDecimal) a, new BigDecimal((Integer) b));
      else if (b instanceof Long)
        return operation.apply((BigDecimal) a, new BigDecimal((Long) b));
      else if (b instanceof Short)
        return operation.apply((BigDecimal) a, new BigDecimal((Short) b));
      else if (b instanceof Float)
        return operation.apply((BigDecimal) a, new BigDecimal((Float) b));
      else if (b instanceof Double)
        return operation.apply((BigDecimal) a, new BigDecimal((Double) b));
      else if (b instanceof BigDecimal)
        return operation.apply((BigDecimal) a, (BigDecimal) b);
    }

    throw new IllegalArgumentException("Cannot increment value '" + a + "' (" + a.getClass() + ") with '" + b + "' ("
        + b.getClass() + ")");
  }
}
/* JavaCC - OriginalChecksum=c255bea24e12493e1005ba2a4d1dbb9d (do not edit this line) */


File: core/src/main/java/com/orientechnologies/orient/core/sql/parser/OStatement.java
/* Generated By:JJTree: Do not edit this line. OStatement.java Version 4.3 */
/* JavaCCOptions:MULTI=true,NODE_USES_PARSER=false,VISITOR=true,TRACK_TOKENS=true,NODE_PREFIX=O,NODE_EXTENDS=,NODE_FACTORY=,SUPPORT_CLASS_VISIBILITY_PUBLIC=true */
package com.orientechnologies.orient.core.sql.parser;

import com.orientechnologies.orient.core.command.OCommandRequest;
import com.orientechnologies.orient.core.db.ODatabaseDocumentInternal;
import com.orientechnologies.orient.core.db.ODatabaseRecordThreadLocal;
import com.orientechnologies.orient.core.sql.OCommandExecutorSQLAbstract;

import java.util.Map;

public class OStatement extends SimpleNode {

  public static final String CUSTOM_STRICT_SQL = "strictSql";

  public OStatement(int id) {
    super(id);
  }

  public OStatement(OrientSql p, int id) {
    super(p, id);
  }

  /** Accept the visitor. **/
  public Object jjtAccept(OrientSqlVisitor visitor, Object data) {
    return visitor.visit(this, data);
  }

  public OCommandExecutorSQLAbstract buildExecutor(final OCommandRequest iRequest) {
    return null; // TODO make it abstract
  }

  public static ODatabaseDocumentInternal getDatabase() {
    return ODatabaseRecordThreadLocal.INSTANCE.get();
  }

  public void replaceParameters(Map<Object, Object> params) {

  }

}
/* JavaCC - OriginalChecksum=589c4dcc8287f430e46d8eb12b0412c5 (do not edit this line) */


File: core/src/main/java/com/orientechnologies/orient/core/sql/parser/SimpleNode.java
/* Generated By:JJTree: Do not edit this line. SimpleNode.java Version 4.3 */
/* JavaCCOptions:MULTI=true,NODE_USES_PARSER=false,VISITOR=true,TRACK_TOKENS=true,NODE_PREFIX=O,NODE_EXTENDS=,NODE_FACTORY=,SUPPORT_CLASS_VISIBILITY_PUBLIC=true */
package com.orientechnologies.orient.core.sql.parser;

public
class SimpleNode implements Node {

  protected Node parent;
  protected Node[] children;
  protected int id;
  protected Object value;
  protected OrientSql parser;
  protected Token firstToken;
  protected Token lastToken;

  public SimpleNode(int i) {
    id = i;
  }

  public SimpleNode(OrientSql p, int i) {
    this(i);
    parser = p;
  }

  public void jjtOpen() {
  }

  public void jjtClose() {
  }

  public void jjtSetParent(Node n) { parent = n; }
  public Node jjtGetParent() { return parent; }

  public void jjtAddChild(Node n, int i) {
    if (children == null) {
      children = new Node[i + 1];
    } else if (i >= children.length) {
      Node c[] = new Node[i + 1];
      System.arraycopy(children, 0, c, 0, children.length);
      children = c;
    }
    children[i] = n;
  }

  public Node jjtGetChild(int i) {
    return children[i];
  }

  public int jjtGetNumChildren() {
    return (children == null) ? 0 : children.length;
  }

  public void jjtSetValue(Object value) { this.value = value; }
  public Object jjtGetValue() { return value; }

  public Token jjtGetFirstToken() { return firstToken; }
  public void jjtSetFirstToken(Token token) { this.firstToken = token; }
  public Token jjtGetLastToken() { return lastToken; }
  public void jjtSetLastToken(Token token) { this.lastToken = token; }

  /** Accept the visitor. **/
  public Object jjtAccept(OrientSqlVisitor visitor, Object data)
{
    return visitor.visit(this, data);
  }

  /** Accept the visitor. **/
  public Object childrenAccept(OrientSqlVisitor visitor, Object data)
{
    if (children != null) {
      for (int i = 0; i < children.length; ++i) {
        children[i].jjtAccept(visitor, data);
      }
    }
    return data;
  }

  /* You can override these two methods in subclasses of SimpleNode to
     customize the way the node appears when the tree is dumped.  If
     your output uses more than one line you should override
     toString(String), otherwise overriding toString() is probably all
     you need to do. */

  public String toString() { return OrientSqlTreeConstants.jjtNodeName[id]; }
  public String toString(String prefix) { return prefix + toString(); }

  /* Override this method if you want to customize how the node dumps
     out its children. */

  public void dump(String prefix) {
    System.out.println(toString(prefix));
    if (children != null) {
      for (int i = 0; i < children.length; ++i) {
        SimpleNode n = (SimpleNode)children[i];
        if (n != null) {
          n.dump(prefix + " ");
        }
      }
    }
  }
}

/* JavaCC - OriginalChecksum=d5ed710e8a3f29d574adbb1d37e08f3b (do not edit this line) */


File: graphdb/src/test/java/com/orientechnologies/orient/graph/sql/OMatchStatementExecutionTest.java
package com.orientechnologies.orient.graph.sql;

import com.orientechnologies.common.profiler.OProfilerMBean;
import com.orientechnologies.orient.core.Orient;
import com.orientechnologies.orient.core.db.document.ODatabaseDocumentTx;
import com.orientechnologies.orient.core.record.impl.ODocument;
import com.orientechnologies.orient.core.sql.OCommandSQL;
import org.junit.AfterClass;
import org.junit.BeforeClass;
import org.junit.Test;

import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

public class OMatchStatementExecutionTest {
  private static String DB_STORAGE = "memory";
  private static String DB_NAME    = "OMatchStatementExecutionTest";

  static ODatabaseDocumentTx   db;

  @BeforeClass
  public static void beforeClass() throws Exception {
    db = new ODatabaseDocumentTx(DB_STORAGE + ":" + DB_NAME);
    db.create();
    getProfilerInstance().startRecording();

    db.command(new OCommandSQL("CREATE class V")).execute();
    db.command(new OCommandSQL("CREATE class E")).execute();
    db.command(new OCommandSQL("CREATE class Person extends V")).execute();
    db.command(new OCommandSQL("CREATE class Friend extends E")).execute();
    db.command(new OCommandSQL("CREATE VERTEX Person set name = 'n1'")).execute();
    db.command(new OCommandSQL("CREATE VERTEX Person set name = 'n2'")).execute();
    db.command(new OCommandSQL("CREATE VERTEX Person set name = 'n3'")).execute();
    db.command(new OCommandSQL("CREATE VERTEX Person set name = 'n4'")).execute();
    db.command(new OCommandSQL("CREATE VERTEX Person set name = 'n5'")).execute();
    db.command(new OCommandSQL("CREATE VERTEX Person set name = 'n6'")).execute();

    String[][] friendList = new String[][] { { "n1", "n2" }, { "n1", "n3" }, { "n2", "n4" }, { "n4", "n5" }, { "n4", "n6" } };

    for (String[] pair : friendList) {
      db.command(
          new OCommandSQL("CREATE EDGE Friend from (select from Person where name = ?) to (select from Person where name = ?)"))
          .execute(pair[0], pair[1]);
    }

  }

  @AfterClass
  public static void afterClass() throws Exception {
    if (db.isClosed()) {
      db.open("admin", "admin");
    }
    // db.command(new OCommandSQL("drop class foo")).execute();
    // db.getMetadata().getSchema().reload();
    db.close();
  }

  @Test
  public void testCommonFriends() throws Exception {

    List<ODocument> qResult = db
        .command(
            new OCommandSQL(
                "select friend.name as name from (match {class:Person, where:(name = 'n1')}.both('Friend'){as:friend}.both('Friend'){class: Person, where:(name = 'n4')} return $matches)"))
        .execute();
    assertEquals(1, qResult.size());
    assertEquals("n2", qResult.get(0).field("name"));
  }

  @Test
  public void testFriendsOfFriends() throws Exception {

    List<ODocument> qResult = db
        .command(
            new OCommandSQL(
                "select friend.name as name from (match {class:Person, where:(name = 'n1')}.out('Friend').out('Friend'){as:friend} return $matches)"))
        .execute();
    assertEquals(1, qResult.size());
    assertEquals("n4", qResult.get(0).field("name"));
  }
  private long indexUsages(ODatabaseDocumentTx db) {
    final long oldIndexUsage;
    try {
      oldIndexUsage = getProfilerInstance().getCounter("db." + DB_NAME + ".query.indexUsed");
      return oldIndexUsage == -1 ? 0 : oldIndexUsage;
    } catch (Exception e) {
      fail();
    }
    return -1l;
  }

  private static OProfilerMBean getProfilerInstance() throws Exception {
    return Orient.instance().getProfiler();

  }
}
