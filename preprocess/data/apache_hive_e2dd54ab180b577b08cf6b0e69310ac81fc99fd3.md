Refactoring Types: ['Extract Method']
hive/ql/optimizer/ConstantPropagate.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements. See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership. The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hive.ql.optimizer;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.ql.exec.FileSinkOperator;
import org.apache.hadoop.hive.ql.exec.FilterOperator;
import org.apache.hadoop.hive.ql.exec.GroupByOperator;
import org.apache.hadoop.hive.ql.exec.JoinOperator;
import org.apache.hadoop.hive.ql.exec.Operator;
import org.apache.hadoop.hive.ql.exec.ReduceSinkOperator;
import org.apache.hadoop.hive.ql.exec.ScriptOperator;
import org.apache.hadoop.hive.ql.exec.SelectOperator;
import org.apache.hadoop.hive.ql.exec.TableScanOperator;
import org.apache.hadoop.hive.ql.lib.DefaultGraphWalker;
import org.apache.hadoop.hive.ql.lib.DefaultRuleDispatcher;
import org.apache.hadoop.hive.ql.lib.Dispatcher;
import org.apache.hadoop.hive.ql.lib.GraphWalker;
import org.apache.hadoop.hive.ql.lib.Node;
import org.apache.hadoop.hive.ql.lib.NodeProcessor;
import org.apache.hadoop.hive.ql.lib.Rule;
import org.apache.hadoop.hive.ql.lib.RuleRegExp;
import org.apache.hadoop.hive.ql.parse.ParseContext;
import org.apache.hadoop.hive.ql.parse.SemanticException;

/**
 * Implementation of one of the rule-based optimization steps. ConstantPropagate traverse the DAG
 * from root to child. For each conditional expression, process as follows:
 *
 * 1. Fold constant expression: if the expression is a UDF and all parameters are constant.
 *
 * 2. Shortcut expression: if the expression is a logical operator and it can be shortcut by
 * some constants of its parameters.
 *
 * 3. Propagate expression: if the expression is an assignment like column=constant, the expression
 * will be propagate to parents to see if further folding operation is possible.
 */
public class ConstantPropagate implements Transform {

  private static final Log LOG = LogFactory.getLog(ConstantPropagate.class);
  protected ParseContext pGraphContext;

  public ConstantPropagate() {}

  /**
   * Transform the query tree.
   *
   * @param pactx
   *        the current parse context
   */
  @Override
  public ParseContext transform(ParseContext pactx) throws SemanticException {
    pGraphContext = pactx;

    // generate pruned column list for all relevant operators
    ConstantPropagateProcCtx cppCtx = new ConstantPropagateProcCtx();

    // create a walker which walks the tree in a DFS manner while maintaining
    // the operator stack. The dispatcher
    // generates the plan from the operator tree
    Map<Rule, NodeProcessor> opRules = new LinkedHashMap<Rule, NodeProcessor>();

    opRules.put(new RuleRegExp("R1", FilterOperator.getOperatorName() + "%"),
        ConstantPropagateProcFactory.getFilterProc());
    opRules.put(new RuleRegExp("R2", GroupByOperator.getOperatorName() + "%"),
        ConstantPropagateProcFactory.getGroupByProc());
    opRules.put(new RuleRegExp("R3", SelectOperator.getOperatorName() + "%"),
        ConstantPropagateProcFactory.getSelectProc());
    opRules.put(new RuleRegExp("R4", FileSinkOperator.getOperatorName() + "%"),
        ConstantPropagateProcFactory.getFileSinkProc());
    opRules.put(new RuleRegExp("R5", ReduceSinkOperator.getOperatorName() + "%"),
        ConstantPropagateProcFactory.getReduceSinkProc());
    opRules.put(new RuleRegExp("R6", JoinOperator.getOperatorName() + "%"),
        ConstantPropagateProcFactory.getJoinProc());
    opRules.put(new RuleRegExp("R7", TableScanOperator.getOperatorName() + "%"),
        ConstantPropagateProcFactory.getTableScanProc());
    opRules.put(new RuleRegExp("R8", ScriptOperator.getOperatorName() + "%"),
        ConstantPropagateProcFactory.getStopProc());

    // The dispatcher fires the processor corresponding to the closest matching
    // rule and passes the context along
    Dispatcher disp = new DefaultRuleDispatcher(ConstantPropagateProcFactory
        .getDefaultProc(), opRules, cppCtx);
    GraphWalker ogw = new ConstantPropagateWalker(disp);

    // Create a list of operator nodes to start the walking.
    ArrayList<Node> topNodes = new ArrayList<Node>();
    topNodes.addAll(pGraphContext.getTopOps().values());
    ogw.startWalking(topNodes, null);
    for (Operator<? extends Serializable> opToDelete : cppCtx.getOpToDelete()) {
      if (opToDelete.getParentOperators() == null || opToDelete.getParentOperators().size() != 1) {
        throw new RuntimeException("Error pruning operator " + opToDelete
            + ". It should have only 1 parent.");
      }
      opToDelete.getParentOperators().get(0).removeChildAndAdoptItsChildren(opToDelete);
    }
    return pGraphContext;
  }


  /**
   * Walks the op tree in root first order.
   */
  public static class ConstantPropagateWalker extends DefaultGraphWalker {

    public ConstantPropagateWalker(Dispatcher disp) {
      super(disp);
    }

    @Override
    public void walk(Node nd) throws SemanticException {

      List<Node> parents = ((Operator) nd).getParentOperators();
      if ((parents == null)
          || getDispatchedList().containsAll(parents)) {
        opStack.push(nd);

        // all children are done or no need to walk the children
        dispatch(nd, opStack);
        opStack.pop();
      } else {
        getToWalk().removeAll(parents);
        getToWalk().add(0, nd);
        getToWalk().addAll(0, parents);
        return;
      }

      // move all the children to the front of queue
      List<? extends Node> children = nd.getChildren();
      if (children != null) {
        getToWalk().removeAll(children);
        getToWalk().addAll(children);
      }
    }
  }

}


File: ql/src/java/org/apache/hadoop/hive/ql/optimizer/ConstantPropagateProcCtx.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements. See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership. The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hive.ql.optimizer;


import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.ql.exec.ColumnInfo;
import org.apache.hadoop.hive.ql.exec.Operator;
import org.apache.hadoop.hive.ql.exec.RowSchema;
import org.apache.hadoop.hive.ql.exec.UnionOperator;
import org.apache.hadoop.hive.ql.lib.NodeProcessorCtx;
import org.apache.hadoop.hive.ql.plan.ExprNodeDesc;

/**
 * This class implements the processor context for Constant Propagate.
 * 
 * ConstantPropagateProcCtx keeps track of propagated constants in a column->const map for each
 * operator, enabling constants to be revolved across operators.
 */
public class ConstantPropagateProcCtx implements NodeProcessorCtx {

  private static final org.apache.commons.logging.Log LOG = LogFactory
      .getLog(ConstantPropagateProcCtx.class);

  private final Map<Operator<? extends Serializable>, Map<ColumnInfo, ExprNodeDesc>> opToConstantExprs;
  private final List<Operator<? extends Serializable>> opToDelete;

  public ConstantPropagateProcCtx() {
    opToConstantExprs =
        new HashMap<Operator<? extends Serializable>, Map<ColumnInfo, ExprNodeDesc>>();
    opToDelete = new ArrayList<Operator<? extends Serializable>>();
  }

  public Map<Operator<? extends Serializable>, Map<ColumnInfo, ExprNodeDesc>> getOpToConstantExprs() {
    return opToConstantExprs;
  }

  /**
   * Resolve a ColumnInfo based on given RowResolver.
   * 
   * @param ci
   * @param rr
   * @param parentRR 
   * @return
   * @throws SemanticException
   */
  private ColumnInfo resolve(ColumnInfo ci, RowSchema rs, RowSchema parentRS) {
    // Resolve new ColumnInfo from <tableAlias, alias>
    String alias = ci.getAlias();
    if (alias == null) {
      alias = ci.getInternalName();
    }
    String tblAlias = ci.getTabAlias();
    ColumnInfo rci = rs.getColumnInfo(tblAlias, alias);
    if (rci == null && rs.getTableNames().size() == 1 &&
            parentRS.getTableNames().size() == 1) {
      rci = rs.getColumnInfo(rs.getTableNames().iterator().next(),
              alias);
    }
    if (rci == null) {
      return null;
    }
    LOG.debug("Resolved "
        + ci.getTabAlias() + "." + ci.getAlias() + " as "
        + rci.getTabAlias() + "." + rci.getAlias() + " with rs: " + rs);
    return rci;
  }

  /**
   * Get propagated constant map from parents.
   * 
   * Traverse all parents of current operator, if there is propagated constant (determined by
   * assignment expression like column=constant value), resolve the column using RowResolver and add
   * it to current constant map.
   * 
   * @param op
   *        operator getting the propagated constants.
   * @return map of ColumnInfo to ExprNodeDesc. The values of that map must be either
   *         ExprNodeConstantDesc or ExprNodeNullDesc.
   */
  public Map<ColumnInfo, ExprNodeDesc> getPropagatedConstants(
      Operator<? extends Serializable> op) {
    Map<ColumnInfo, ExprNodeDesc> constants = new HashMap<ColumnInfo, ExprNodeDesc>();
    if (op.getSchema() == null) {
      return constants;
    }
    RowSchema rs = op.getSchema();
    LOG.debug("Getting constants of op:" + op + " with rs:" + rs);

    if (op.getParentOperators() == null) {
      return constants;
    }

    if (op instanceof UnionOperator) {
      String alias = rs.getSignature().get(0).getTabAlias();
      // find intersection
      Map<ColumnInfo, ExprNodeDesc> intersection = null;
      for (Operator<?> parent : op.getParentOperators()) {
        Map<ColumnInfo, ExprNodeDesc> unionConst = opToConstantExprs.get(parent);
        LOG.debug("Constant of op " + parent.getOperatorId() + " " + unionConst);
        if (intersection == null) {
          intersection = new HashMap<ColumnInfo, ExprNodeDesc>();
          for (Entry<ColumnInfo, ExprNodeDesc> e : unionConst.entrySet()) {
            ColumnInfo ci = new ColumnInfo(e.getKey());
            ci.setTabAlias(alias);
            intersection.put(ci, e.getValue());
          }
        } else {
          Iterator<Entry<ColumnInfo, ExprNodeDesc>> itr = intersection.entrySet().iterator();
          while (itr.hasNext()) {
            Entry<ColumnInfo, ExprNodeDesc> e = itr.next();
            boolean found = false;
            for (Entry<ColumnInfo, ExprNodeDesc> f : opToConstantExprs.get(parent).entrySet()) {
              if (e.getKey().getInternalName().equals(f.getKey().getInternalName())) {
                if (e.getValue().isSame(f.getValue())) {
                  found = true;
                }
                break;
              }
            }
            if (!found) {
              itr.remove();
            }
          }
        }
        if (intersection.isEmpty()) {
          return intersection;
        }
      }
      LOG.debug("Propagated union constants:" + intersection);
      return intersection;
    }

    for (Operator<? extends Serializable> parent : op.getParentOperators()) {
      Map<ColumnInfo, ExprNodeDesc> c = opToConstantExprs.get(parent);
      for (Entry<ColumnInfo, ExprNodeDesc> e : c.entrySet()) {
        ColumnInfo ci = e.getKey();
        ColumnInfo rci = null;
        ExprNodeDesc constant = e.getValue();
        rci = resolve(ci, rs, parent.getSchema());
        if (rci != null) {
          constants.put(rci, constant);
        } else {
          LOG.debug("Can't resolve " + ci.getTabAlias() + "." + ci.getAlias() +
                  "(" + ci.getInternalName() + ") from rs:" + rs);
        }
      }
    }

    LOG.debug("Offerring constants " + constants.keySet()
        + " to operator " + op.toString());

    return constants;
  }

  public void addOpToDelete(Operator<? extends Serializable> op) {
    opToDelete.add(op);
  }

  public List<Operator<? extends Serializable>> getOpToDelete() {
    return opToDelete;
  }
}


File: ql/src/java/org/apache/hadoop/hive/ql/optimizer/ConstantPropagateProcFactory.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one or more contributor license
 * agreements. See the NOTICE file distributed with this work for additional information regarding
 * copyright ownership. The ASF licenses this file to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package org.apache.hadoop.hive.ql.optimizer;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.Stack;

import org.apache.commons.lang.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.ql.exec.ColumnInfo;
import org.apache.hadoop.hive.ql.exec.FileSinkOperator;
import org.apache.hadoop.hive.ql.exec.FilterOperator;
import org.apache.hadoop.hive.ql.exec.FunctionRegistry;
import org.apache.hadoop.hive.ql.exec.GroupByOperator;
import org.apache.hadoop.hive.ql.exec.JoinOperator;
import org.apache.hadoop.hive.ql.exec.Operator;
import org.apache.hadoop.hive.ql.exec.ReduceSinkOperator;
import org.apache.hadoop.hive.ql.exec.RowSchema;
import org.apache.hadoop.hive.ql.exec.SelectOperator;
import org.apache.hadoop.hive.ql.exec.TableScanOperator;
import org.apache.hadoop.hive.ql.exec.UDF;
import org.apache.hadoop.hive.ql.exec.UDFArgumentException;
import org.apache.hadoop.hive.ql.exec.Utilities;
import org.apache.hadoop.hive.ql.lib.Node;
import org.apache.hadoop.hive.ql.lib.NodeProcessor;
import org.apache.hadoop.hive.ql.lib.NodeProcessorCtx;
import org.apache.hadoop.hive.ql.metadata.HiveException;
import org.apache.hadoop.hive.ql.parse.SemanticException;
import org.apache.hadoop.hive.ql.plan.DynamicPartitionCtx;
import org.apache.hadoop.hive.ql.plan.ExprNodeColumnDesc;
import org.apache.hadoop.hive.ql.plan.ExprNodeConstantDesc;
import org.apache.hadoop.hive.ql.plan.ExprNodeDesc;
import org.apache.hadoop.hive.ql.plan.ExprNodeGenericFuncDesc;
import org.apache.hadoop.hive.ql.plan.FileSinkDesc;
import org.apache.hadoop.hive.ql.plan.GroupByDesc;
import org.apache.hadoop.hive.ql.plan.JoinCondDesc;
import org.apache.hadoop.hive.ql.plan.JoinDesc;
import org.apache.hadoop.hive.ql.plan.OperatorDesc;
import org.apache.hadoop.hive.ql.plan.ReduceSinkDesc;
import org.apache.hadoop.hive.ql.plan.TableScanDesc;
import org.apache.hadoop.hive.ql.udf.UDFType;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDF;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDF.DeferredJavaObject;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFBaseCompare;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFBridge;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFCase;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFOPAnd;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFOPEqual;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFOPNot;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFOPNotEqual;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFOPNotNull;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFOPNull;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFOPOr;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDFWhen;
import org.apache.hadoop.hive.serde.serdeConstants;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspector;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspectorConverters;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspectorConverters.Converter;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspectorUtils;
import org.apache.hadoop.hive.serde2.objectinspector.PrimitiveObjectInspector;
import org.apache.hadoop.hive.serde2.objectinspector.PrimitiveObjectInspector.PrimitiveCategory;
import org.apache.hadoop.hive.serde2.objectinspector.primitive.PrimitiveObjectInspectorFactory;
import org.apache.hadoop.hive.serde2.objectinspector.primitive.PrimitiveObjectInspectorUtils;
import org.apache.hadoop.hive.serde2.typeinfo.PrimitiveTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfoUtils;

import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Lists;

/**
 * Factory for generating the different node processors used by ConstantPropagate.
 */
public final class ConstantPropagateProcFactory {
  protected static final Log LOG = LogFactory.getLog(ConstantPropagateProcFactory.class.getName());
  protected static Set<Class<?>> propagatableUdfs = new HashSet<Class<?>>();

  static {
    propagatableUdfs.add(GenericUDFOPAnd.class);
  };

  private ConstantPropagateProcFactory() {
    // prevent instantiation
  }

  /**
   * Get ColumnInfo from column expression.
   *
   * @param rr
   * @param desc
   * @return
   */
  public static ColumnInfo resolveColumn(RowSchema rs,
      ExprNodeColumnDesc desc) {
    ColumnInfo ci = rs.getColumnInfo(desc.getTabAlias(), desc.getColumn());
    if (ci == null) {
      ci = rs.getColumnInfo(desc.getColumn());
    }
    if (ci == null) {
      return null;
    }
    return ci;
  }

  private static final Set<PrimitiveCategory> unSupportedTypes = ImmutableSet
      .<PrimitiveCategory>builder()
      .add(PrimitiveCategory.DECIMAL)
      .add(PrimitiveCategory.VARCHAR)
      .add(PrimitiveCategory.CHAR).build();

  /**
   * Cast type from expression type to expected type ti.
   *
   * @param desc constant expression
   * @param ti expected type info
   * @return cast constant, or null if the type cast failed.
   */
  private static ExprNodeConstantDesc typeCast(ExprNodeDesc desc, TypeInfo ti) {
    if (desc instanceof ExprNodeConstantDesc && null == ((ExprNodeConstantDesc)desc).getValue()) {
      return null;
    }
    if (!(ti instanceof PrimitiveTypeInfo) || !(desc.getTypeInfo() instanceof PrimitiveTypeInfo)) {
      return null;
    }

    PrimitiveTypeInfo priti = (PrimitiveTypeInfo) ti;
    PrimitiveTypeInfo descti = (PrimitiveTypeInfo) desc.getTypeInfo();

    if (unSupportedTypes.contains(priti.getPrimitiveCategory())
        || unSupportedTypes.contains(descti.getPrimitiveCategory())) {
      // FIXME: support template types. It currently has conflict with
      // ExprNodeConstantDesc
      return null;
    }
    LOG.debug("Casting " + desc + " to type " + ti);
    ExprNodeConstantDesc c = (ExprNodeConstantDesc) desc;
    if (null != c.getFoldedFromVal() && priti.getTypeName().equals(serdeConstants.STRING_TYPE_NAME)) {
      // avoid double casting to preserve original string representation of constant.
      return new ExprNodeConstantDesc(c.getFoldedFromVal());
    }
    ObjectInspector origOI =
        TypeInfoUtils.getStandardJavaObjectInspectorFromTypeInfo(desc.getTypeInfo());
    ObjectInspector oi =
        TypeInfoUtils.getStandardJavaObjectInspectorFromTypeInfo(ti);
    Converter converter = ObjectInspectorConverters.getConverter(origOI, oi);
    Object convObj = converter.convert(c.getValue());

    // Convert integer related types because converters are not sufficient
    if (convObj instanceof Integer) {
      switch (priti.getPrimitiveCategory()) {
        case BYTE:
          convObj = new Byte((byte) (((Integer) convObj).intValue()));
          break;
        case SHORT:
          convObj = new Short((short) ((Integer) convObj).intValue());
          break;
        case LONG:
          convObj = new Long(((Integer) convObj).intValue());
        default:
      }
    }
    return new ExprNodeConstantDesc(ti, convObj);
  }

  public static ExprNodeDesc foldExpr(ExprNodeGenericFuncDesc funcDesc) {

    GenericUDF udf = funcDesc.getGenericUDF();
    if (!isDeterministicUdf(udf)) {
      return funcDesc;
    }
    return evaluateFunction(funcDesc.getGenericUDF(),funcDesc.getChildren(), funcDesc.getChildren());
  }
  /**
   * Fold input expression desc.
   *
   * This function recursively checks if any subexpression of a specified expression
   * can be evaluated to be constant and replaces such subexpression with the constant.
   * If the expression is a derterministic UDF and all the subexpressions are constants,
   * the value will be calculated immediately (during compilation time vs. runtime).
   * e.g.:
   *   concat(year, month) => 200112 for year=2001, month=12 since concat is deterministic UDF
   *   unix_timestamp(time) => unix_timestamp(123) for time=123 since unix_timestamp is nonderministic UDF
   * @param desc folding expression
   * @param constants current propagated constant map
   * @param cppCtx
   * @param op processing operator
   * @param propagate if true, assignment expressions will be added to constants.
   * @return fold expression
   * @throws UDFArgumentException
   */
  private static ExprNodeDesc foldExpr(ExprNodeDesc desc, Map<ColumnInfo, ExprNodeDesc> constants,
      ConstantPropagateProcCtx cppCtx, Operator<? extends Serializable> op, int tag,
      boolean propagate) throws UDFArgumentException {
    if (desc instanceof ExprNodeGenericFuncDesc) {
      ExprNodeGenericFuncDesc funcDesc = (ExprNodeGenericFuncDesc) desc;

      GenericUDF udf = funcDesc.getGenericUDF();

      boolean propagateNext = propagate && propagatableUdfs.contains(udf.getClass());
      List<ExprNodeDesc> newExprs = new ArrayList<ExprNodeDesc>();
      for (ExprNodeDesc childExpr : desc.getChildren()) {
        newExprs.add(foldExpr(childExpr, constants, cppCtx, op, tag, propagateNext));
      }

      // Don't evalulate nondeterministic function since the value can only calculate during runtime.
      if (!isDeterministicUdf(udf)) {
        LOG.debug("Function " + udf.getClass() + " is undeterministic. Don't evalulating immediately.");
        ((ExprNodeGenericFuncDesc) desc).setChildren(newExprs);
        return desc;
      } else {
        // If all child expressions of deterministic function are constants, evaluate such UDF immediately
        ExprNodeDesc constant = evaluateFunction(udf, newExprs, desc.getChildren());
        if (constant != null) {
          LOG.debug("Folding expression:" + desc + " -> " + constant);
          return constant;
        } else {
          // Check if the function can be short cut.
          ExprNodeDesc shortcut = shortcutFunction(udf, newExprs, op);
          if (shortcut != null) {
            LOG.debug("Folding expression:" + desc + " -> " + shortcut);
            return shortcut;
          }
          ((ExprNodeGenericFuncDesc) desc).setChildren(newExprs);
        }

        // If in some selected binary operators (=, is null, etc), one of the
        // expressions are
        // constant, add them to colToConstants as half-deterministic columns.
        if (propagate) {
          propagate(udf, newExprs, op.getSchema(), constants);
        }
      }

      return desc;
    } else if (desc instanceof ExprNodeColumnDesc) {
      if (op.getParentOperators() == null || op.getParentOperators().isEmpty()) {
        return desc;
      }
      Operator<? extends Serializable> parent = op.getParentOperators().get(tag);
      ExprNodeDesc col = evaluateColumn((ExprNodeColumnDesc) desc, cppCtx, parent);
      if (col != null) {
        LOG.debug("Folding expression:" + desc + " -> " + col);
        return col;
      }
    }
    return desc;
  }

  private static boolean isDeterministicUdf(GenericUDF udf) {
    UDFType udfType = udf.getClass().getAnnotation(UDFType.class);
    if (udf instanceof GenericUDFBridge) {
      udfType = ((GenericUDFBridge) udf).getUdfClass().getAnnotation(UDFType.class);
    }
    if (udfType.deterministic() == false) {
      return false;
    }

    // If udf is requiring additional jars, we can't determine the result in
    // compile time.
    String[] files;
    String[] jars;
    if (udf instanceof GenericUDFBridge) {
      GenericUDFBridge bridge = (GenericUDFBridge) udf;
      String udfClassName = bridge.getUdfClassName();
      try {
        UDF udfInternal =
            (UDF) Class.forName(bridge.getUdfClassName(), true, Utilities.getSessionSpecifiedClassLoader())
                .newInstance();
        files = udfInternal.getRequiredFiles();
        jars = udfInternal.getRequiredJars();
      } catch (Exception e) {
        LOG.error("The UDF implementation class '" + udfClassName
            + "' is not present in the class path");
        return false;
      }
    } else {
      files = udf.getRequiredFiles();
      jars = udf.getRequiredJars();
    }
    if (files != null || jars != null) {
      return false;
    }
    return true;
  }

  /**
   * Propagate assignment expression, adding an entry into constant map constants.
   *
   * @param udf expression UDF, currently only 2 UDFs are supported: '=' and 'is null'.
   * @param newExprs child expressions (parameters).
   * @param cppCtx
   * @param op
   * @param constants
   */
  private static void propagate(GenericUDF udf, List<ExprNodeDesc> newExprs, RowSchema rs,
      Map<ColumnInfo, ExprNodeDesc> constants) {
    if (udf instanceof GenericUDFOPEqual) {
      ExprNodeDesc lOperand = newExprs.get(0);
      ExprNodeDesc rOperand = newExprs.get(1);
      ExprNodeConstantDesc v;
      if (lOperand instanceof ExprNodeConstantDesc) {
        v = (ExprNodeConstantDesc) lOperand;
      } else if (rOperand instanceof ExprNodeConstantDesc) {
        v = (ExprNodeConstantDesc) rOperand;
      } else {
        // we need a constant on one side.
        return;
      }
      // If both sides are constants, there is nothing to propagate
      ExprNodeColumnDesc c = getColumnExpr(lOperand);
      if (null == c) {
        c = getColumnExpr(rOperand);
      }
      if (null == c) {
        // we need a column expression on other side.
        return;
      }
      ColumnInfo ci = resolveColumn(rs, c);
      if (ci != null) {
        LOG.debug("Filter " + udf + " is identified as a value assignment, propagate it.");
        if (!v.getTypeInfo().equals(ci.getType())) {
          v = typeCast(v, ci.getType());
        }
        if (v != null) {
          constants.put(ci, v);
        }
      }
    } else if (udf instanceof GenericUDFOPNull) {
      ExprNodeDesc operand = newExprs.get(0);
      if (operand instanceof ExprNodeColumnDesc) {
        LOG.debug("Filter " + udf + " is identified as a value assignment, propagate it.");
        ExprNodeColumnDesc c = (ExprNodeColumnDesc) operand;
        ColumnInfo ci = resolveColumn(rs, c);
        if (ci != null) {
          constants.put(ci, new ExprNodeConstantDesc(ci.getType(), null));
        }
      }
    }
  }

  private static ExprNodeColumnDesc getColumnExpr(ExprNodeDesc expr) {
    while (FunctionRegistry.isOpCast(expr)) {
      expr = expr.getChildren().get(0);
    }
    return (expr instanceof ExprNodeColumnDesc) ? (ExprNodeColumnDesc)expr : null;
  }

  private static ExprNodeDesc shortcutFunction(GenericUDF udf, List<ExprNodeDesc> newExprs,
    Operator<? extends Serializable> op) throws UDFArgumentException {

    if (udf instanceof GenericUDFOPEqual) {
     assert newExprs.size() == 2;
     boolean foundUDFInFirst = false;
     ExprNodeGenericFuncDesc caseOrWhenexpr = null;
     if (newExprs.get(0) instanceof ExprNodeGenericFuncDesc) {
       caseOrWhenexpr = (ExprNodeGenericFuncDesc) newExprs.get(0);
       if (caseOrWhenexpr.getGenericUDF() instanceof GenericUDFWhen || caseOrWhenexpr.getGenericUDF() instanceof GenericUDFCase) {
         foundUDFInFirst = true;
       }
     }
     if (!foundUDFInFirst && newExprs.get(1) instanceof ExprNodeGenericFuncDesc) {
       caseOrWhenexpr = (ExprNodeGenericFuncDesc) newExprs.get(1);
       if (!(caseOrWhenexpr.getGenericUDF() instanceof GenericUDFWhen || caseOrWhenexpr.getGenericUDF() instanceof GenericUDFCase)) {
         return null;
       }
     }
     if (null == caseOrWhenexpr) {
       // we didn't find case or when udf
       return null;
     }
     GenericUDF childUDF = caseOrWhenexpr.getGenericUDF();
     List<ExprNodeDesc> children = caseOrWhenexpr.getChildren();
     int i;
     if (childUDF instanceof GenericUDFWhen) {
       for (i = 1; i < children.size(); i+=2) {
        children.set(i, ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPEqual(),
            Lists.newArrayList(children.get(i),newExprs.get(foundUDFInFirst ? 1 : 0))));
      }
       if(children.size() % 2 == 1) {
         i = children.size()-1;
         children.set(i, ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPEqual(),
             Lists.newArrayList(children.get(i),newExprs.get(foundUDFInFirst ? 1 : 0))));
       }
       return caseOrWhenexpr;
     } else if (childUDF instanceof GenericUDFCase) {
       for (i = 2; i < children.size(); i+=2) {
         children.set(i, ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPEqual(),
             Lists.newArrayList(children.get(i),newExprs.get(foundUDFInFirst ? 1 : 0))));
       }
        if(children.size() % 2 == 0) {
          i = children.size()-1;
          children.set(i, ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPEqual(),
              Lists.newArrayList(children.get(i),newExprs.get(foundUDFInFirst ? 1 : 0))));
        }
        return caseOrWhenexpr;
     } else {
       // cant happen
       return null;
     }
    }
    if (udf instanceof GenericUDFOPAnd) {
      for (int i = 0; i < 2; i++) {
        ExprNodeDesc childExpr = newExprs.get(i);
        ExprNodeDesc other = newExprs.get(Math.abs(i - 1));
        if (childExpr instanceof ExprNodeConstantDesc) {
          ExprNodeConstantDesc c = (ExprNodeConstantDesc) childExpr;
          if (Boolean.TRUE.equals(c.getValue())) {

            // if true, prune it
            return other;
          } else {

            // if false return false
            return childExpr;
          }
        } else // Try to fold (key = 86) and (key is not null) to (key = 86)
        if (childExpr instanceof ExprNodeGenericFuncDesc &&
            ((ExprNodeGenericFuncDesc)childExpr).getGenericUDF() instanceof GenericUDFOPNotNull &&
            childExpr.getChildren().get(0) instanceof ExprNodeColumnDesc && other instanceof ExprNodeGenericFuncDesc
            && ((ExprNodeGenericFuncDesc)other).getGenericUDF() instanceof GenericUDFBaseCompare
            && other.getChildren().size() == 2) {
          ExprNodeColumnDesc colDesc = getColumnExpr(other.getChildren().get(0));
          if (null == colDesc) {
            colDesc = getColumnExpr(other.getChildren().get(1));
          }
          if (null != colDesc && colDesc.isSame(childExpr.getChildren().get(0))) {
            return other;
          }
        }
      }
    }

    if (udf instanceof GenericUDFOPOr) {
      for (int i = 0; i < 2; i++) {
        ExprNodeDesc childExpr = newExprs.get(i);
        if (childExpr instanceof ExprNodeConstantDesc) {
          ExprNodeConstantDesc c = (ExprNodeConstantDesc) childExpr;
          if (Boolean.FALSE.equals(c.getValue())) {

            // if false, prune it
            return newExprs.get(Math.abs(i - 1));
          } else {

            // if true return true
            return childExpr;
          }
        }
      }
    }

    if (udf instanceof GenericUDFWhen) {
      if (!(newExprs.size() == 2 || newExprs.size() == 3)) {
        // In general, when can have unlimited # of branches,
        // we currently only handle either 1 or 2 branch.
        return null;
      }
      ExprNodeDesc thenExpr = newExprs.get(1);
      ExprNodeDesc elseExpr = newExprs.size() == 3 ? newExprs.get(2) :
        new ExprNodeConstantDesc(newExprs.get(1).getTypeInfo(),null);

      ExprNodeDesc whenExpr = newExprs.get(0);
      if (whenExpr instanceof ExprNodeConstantDesc) {
        Boolean whenVal = (Boolean)((ExprNodeConstantDesc) whenExpr).getValue();
        return (whenVal == null || Boolean.FALSE.equals(whenVal)) ? elseExpr : thenExpr;
      }

      if (thenExpr instanceof ExprNodeConstantDesc && elseExpr instanceof ExprNodeConstantDesc) {
        ExprNodeConstantDesc constThen = (ExprNodeConstantDesc) thenExpr;
        ExprNodeConstantDesc constElse = (ExprNodeConstantDesc) elseExpr;
        Object thenVal = constThen.getValue();
        Object elseVal = constElse.getValue();
        if (thenVal == null) {
          if (elseVal == null) {
            // both branches are null.
            return thenExpr;
          } else if (op instanceof FilterOperator) {
            // we can still fold, since here null is equivalent to false.
            return Boolean.TRUE.equals(elseVal) ?
              ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPNot(), newExprs.subList(0, 1)) : Boolean.FALSE.equals(elseVal) ?
              elseExpr : null;
          } else {
            // can't do much, expression is not in context of filter, so we can't treat null as equivalent to false here.
            return null;
          }
        } else if (elseVal == null && op instanceof FilterOperator) {
          return Boolean.TRUE.equals(thenVal) ? whenExpr : Boolean.FALSE.equals(thenVal) ? thenExpr : null;
        } else if(thenVal.equals(elseVal)){
          return thenExpr;
        } else if (thenVal instanceof Boolean && elseVal instanceof Boolean) {
          return Boolean.TRUE.equals(thenVal) ? whenExpr :
            ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPNot(), newExprs.subList(0, 1));
        } else {
          return null;
        }
      }
    }
    if (udf instanceof GenericUDFCase) {
      // HIVE-9644 Attempt to fold expression like :
      // where (case ss_sold_date when '1998-01-01' then 1=1 else null=1 end);
      // where ss_sold_date= '1998-01-01' ;
      if (!(newExprs.size() == 3 || newExprs.size() == 4)) {
        // In general case can have unlimited # of branches,
        // we currently only handle either 1 or 2 branch.
        return null;
      }
      ExprNodeDesc thenExpr = newExprs.get(2);
      ExprNodeDesc elseExpr = newExprs.size() == 4 ? newExprs.get(3) :
        new ExprNodeConstantDesc(newExprs.get(2).getTypeInfo(),null);

      if (thenExpr instanceof ExprNodeConstantDesc && elseExpr instanceof ExprNodeConstantDesc) {
        ExprNodeConstantDesc constThen = (ExprNodeConstantDesc) thenExpr;
        ExprNodeConstantDesc constElse = (ExprNodeConstantDesc) elseExpr;
        Object thenVal = constThen.getValue();
        Object elseVal = constElse.getValue();
        if (thenVal == null) {
          if (null == elseVal) {
            return thenExpr;
          } else if (op instanceof FilterOperator) {
            return Boolean.TRUE.equals(elseVal) ? ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPNotEqual(), newExprs.subList(0, 2)) :
              Boolean.FALSE.equals(elseVal) ? elseExpr : null;
          } else {
            return null;
          }
        } else if (null == elseVal && op instanceof FilterOperator) {
            return Boolean.TRUE.equals(thenVal) ? ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPEqual(), newExprs.subList(0, 2)) :
              Boolean.FALSE.equals(thenVal) ? thenExpr : null;
        } else if(thenVal.equals(elseVal)){
          return thenExpr;
        } else if (thenVal instanceof Boolean && elseVal instanceof Boolean) {
          return Boolean.TRUE.equals(thenVal) ? ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPEqual(), newExprs.subList(0, 2)) :
            ExprNodeGenericFuncDesc.newInstance(new GenericUDFOPNotEqual(), newExprs.subList(0, 2));
        } else {
          return null;
        }
      }
    }

    return null;
  }

  /**
   * Evaluate column, replace the deterministic columns with constants if possible
   *
   * @param desc
   * @param ctx
   * @param op
   * @param colToConstants
   * @return
   */
  private static ExprNodeDesc evaluateColumn(ExprNodeColumnDesc desc,
    ConstantPropagateProcCtx cppCtx, Operator<? extends Serializable> parent) {
    RowSchema rs = parent.getSchema();
    ColumnInfo ci = rs.getColumnInfo(desc.getColumn());
    if (ci == null) {
      LOG.error("Reverse look up of column " + desc + " error!");
      ci = rs.getColumnInfo(desc.getTabAlias(), desc.getColumn());
    }
    if (ci == null) {
      LOG.error("Can't resolve " + desc.getTabAlias() + "." + desc.getColumn());
      return null;
    }
    ExprNodeDesc constant = null;
    // Additional work for union operator, see union27.q
    if (ci.getAlias() == null) {
      for (Entry<ColumnInfo, ExprNodeDesc> e : cppCtx.getOpToConstantExprs().get(parent).entrySet()) {
        if (e.getKey().getInternalName().equals(ci.getInternalName())) {
          constant = e.getValue();
          break;
        }
      }
    } else {
      constant = cppCtx.getOpToConstantExprs().get(parent).get(ci);
    }
    if (constant != null) {
      if (constant instanceof ExprNodeConstantDesc
          && !constant.getTypeInfo().equals(desc.getTypeInfo())) {
        return typeCast(constant, desc.getTypeInfo());
      }
      return constant;
    } else {
      return null;
    }
  }

  /**
   * Evaluate UDF
   *
   * @param udf UDF object
   * @param exprs
   * @param oldExprs
   * @return null if expression cannot be evaluated (not all parameters are constants). Or evaluated
   *         ExprNodeConstantDesc if possible.
   * @throws HiveException
   */
  private static ExprNodeDesc evaluateFunction(GenericUDF udf, List<ExprNodeDesc> exprs,
      List<ExprNodeDesc> oldExprs) {
    DeferredJavaObject[] arguments = new DeferredJavaObject[exprs.size()];
    ObjectInspector[] argois = new ObjectInspector[exprs.size()];
    for (int i = 0; i < exprs.size(); i++) {
      ExprNodeDesc desc = exprs.get(i);
      if (desc instanceof ExprNodeConstantDesc) {
        ExprNodeConstantDesc constant = (ExprNodeConstantDesc) exprs.get(i);
        if (!constant.getTypeInfo().equals(oldExprs.get(i).getTypeInfo())) {
          constant = typeCast(constant, oldExprs.get(i).getTypeInfo());
          if (constant == null) {
            return null;
          }
        }
        Object value = constant.getValue();
        PrimitiveTypeInfo pti = (PrimitiveTypeInfo) constant.getTypeInfo();
        Object writableValue = null == value ? value :
            PrimitiveObjectInspectorFactory.getPrimitiveJavaObjectInspector(pti)
                .getPrimitiveWritableObject(value);
        arguments[i] = new DeferredJavaObject(writableValue);
        argois[i] =
            ObjectInspectorUtils.getConstantObjectInspector(constant.getWritableObjectInspector(),
                writableValue);

      } else if (desc instanceof ExprNodeGenericFuncDesc) {
        ExprNodeDesc evaluatedFn = foldExpr((ExprNodeGenericFuncDesc)desc);
        if (null == evaluatedFn || !(evaluatedFn instanceof ExprNodeConstantDesc)) {
          return null;
        }
        ExprNodeConstantDesc constant = (ExprNodeConstantDesc) evaluatedFn;
        Object writableValue = PrimitiveObjectInspectorFactory.getPrimitiveJavaObjectInspector(
          (PrimitiveTypeInfo) constant.getTypeInfo()).getPrimitiveWritableObject(constant.getValue());
        arguments[i] = new DeferredJavaObject(writableValue);
        argois[i] = ObjectInspectorUtils.getConstantObjectInspector(constant.getWritableObjectInspector(), writableValue);
      } else {
        return null;
      }
    }

    try {
      ObjectInspector oi = udf.initialize(argois);
      Object o = udf.evaluate(arguments);
      LOG.debug(udf.getClass().getName() + "(" + exprs + ")=" + o);
      if (o == null) {
        return new ExprNodeConstantDesc(TypeInfoUtils.getTypeInfoFromObjectInspector(oi), o);
      }
      Class<?> clz = o.getClass();
      if (PrimitiveObjectInspectorUtils.isPrimitiveWritableClass(clz)) {
        PrimitiveObjectInspector poi = (PrimitiveObjectInspector) oi;
        TypeInfo typeInfo = poi.getTypeInfo();
        o = poi.getPrimitiveJavaObject(o);
        if (typeInfo.getTypeName().contains(serdeConstants.DECIMAL_TYPE_NAME) ||
            typeInfo.getTypeName().contains(serdeConstants.VARCHAR_TYPE_NAME) ||
            typeInfo.getTypeName().contains(serdeConstants.CHAR_TYPE_NAME)) {
          return new ExprNodeConstantDesc(typeInfo, o);
        }
      } else if (PrimitiveObjectInspectorUtils.isPrimitiveJavaClass(clz)) {

      } else {
        LOG.error("Unable to evaluate " + udf + ". Return value unrecoginizable.");
        return null;
      }
      String constStr = null;
      if(arguments.length == 1 && FunctionRegistry.isOpCast(udf)) {
        // remember original string representation of constant.
        constStr = arguments[0].get().toString();
      }
      return new ExprNodeConstantDesc(o).setFoldedFromVal(constStr);
    } catch (HiveException e) {
      LOG.error("Evaluation function " + udf.getClass()
          + " failed in Constant Propagatation Optimizer.");
      throw new RuntimeException(e);
    }
  }

  /**
   * Change operator row schema, replace column with constant if it is.
   *
   * @param op
   * @param constants
   * @throws SemanticException
   */
  private static void foldOperator(Operator<? extends Serializable> op,
      ConstantPropagateProcCtx cppCtx) throws SemanticException {
    RowSchema schema = op.getSchema();
    Map<ColumnInfo, ExprNodeDesc> constants = cppCtx.getOpToConstantExprs().get(op);
    if (schema != null && schema.getSignature() != null) {
      for (ColumnInfo col : schema.getSignature()) {
        ExprNodeDesc constant = constants.get(col);
        if (constant != null) {
          LOG.debug("Replacing column " + col + " with constant " + constant + " in " + op);
          if (!col.getType().equals(constant.getTypeInfo())) {
            constant = typeCast(constant, col.getType());
          }
          if (constant != null) {
            col.setObjectinspector(constant.getWritableObjectInspector());
          }
        }
      }
    }

    Map<String, ExprNodeDesc> colExprMap = op.getColumnExprMap();
    if (colExprMap != null) {
      for (Entry<ColumnInfo, ExprNodeDesc> e : constants.entrySet()) {
        String internalName = e.getKey().getInternalName();
        if (colExprMap.containsKey(internalName)) {
          colExprMap.put(internalName, e.getValue());
        }
      }
    }
  }

  /**
   * Node Processor for Constant Propagation on Filter Operators. The processor is to fold
   * conditional expressions and extract assignment expressions and propagate them.
   */
  public static class ConstantPropagateFilterProc implements NodeProcessor {
    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      FilterOperator op = (FilterOperator) nd;
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      Map<ColumnInfo, ExprNodeDesc> constants = cppCtx.getPropagatedConstants(op);
      cppCtx.getOpToConstantExprs().put(op, constants);

      ExprNodeDesc condn = op.getConf().getPredicate();
      LOG.debug("Old filter FIL[" + op.getIdentifier() + "] conditions:" + condn.getExprString());
      ExprNodeDesc newCondn = foldExpr(condn, constants, cppCtx, op, 0, true);
      if (newCondn instanceof ExprNodeConstantDesc) {
        ExprNodeConstantDesc c = (ExprNodeConstantDesc) newCondn;
        if (Boolean.TRUE.equals(c.getValue())) {
          cppCtx.addOpToDelete(op);
          LOG.debug("Filter expression " + condn + " holds true. Will delete it.");
        } else if (Boolean.FALSE.equals(c.getValue())) {
          LOG.warn("Filter expression " + condn + " holds false!");
        }
      }
      if (newCondn instanceof ExprNodeConstantDesc && ((ExprNodeConstantDesc)newCondn).getValue() == null) {
        // where null is same as where false
        newCondn = new ExprNodeConstantDesc(Boolean.FALSE);
      }
      LOG.debug("New filter FIL[" + op.getIdentifier() + "] conditions:" + newCondn.getExprString());

      // merge it with the downstream col list
      op.getConf().setPredicate(newCondn);
      foldOperator(op, cppCtx);
      return null;
    }

  }

  /**
   * Factory method to get the ConstantPropagateFilterProc class.
   *
   * @return ConstantPropagateFilterProc
   */
  public static ConstantPropagateFilterProc getFilterProc() {
    return new ConstantPropagateFilterProc();
  }

  /**
   * Node Processor for Constant Propagate for Group By Operators.
   */
  public static class ConstantPropagateGroupByProc implements NodeProcessor {
    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      GroupByOperator op = (GroupByOperator) nd;
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      Map<ColumnInfo, ExprNodeDesc> colToConstants = cppCtx.getPropagatedConstants(op);
      cppCtx.getOpToConstantExprs().put(op, colToConstants);

      if (colToConstants.isEmpty()) {
        return null;
      }

      GroupByDesc conf = op.getConf();
      ArrayList<ExprNodeDesc> keys = conf.getKeys();
      for (int i = 0; i < keys.size(); i++) {
        ExprNodeDesc key = keys.get(i);
        ExprNodeDesc newkey = foldExpr(key, colToConstants, cppCtx, op, 0, false);
        keys.set(i, newkey);
      }
      foldOperator(op, cppCtx);
      return null;
    }
  }

  /**
   * Factory method to get the ConstantPropagateGroupByProc class.
   *
   * @return ConstantPropagateGroupByProc
   */
  public static ConstantPropagateGroupByProc getGroupByProc() {
    return new ConstantPropagateGroupByProc();
  }

  /**
   * The Default Node Processor for Constant Propagation.
   */
  public static class ConstantPropagateDefaultProc implements NodeProcessor {
    @Override
    @SuppressWarnings("unchecked")
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      Operator<? extends Serializable> op = (Operator<? extends Serializable>) nd;
      Map<ColumnInfo, ExprNodeDesc> constants = cppCtx.getPropagatedConstants(op);
      cppCtx.getOpToConstantExprs().put(op, constants);
      if (constants.isEmpty()) {
        return null;
      }
      foldOperator(op, cppCtx);
      return null;
    }
  }

  /**
   * Factory method to get the ConstantPropagateDefaultProc class.
   *
   * @return ConstantPropagateDefaultProc
   */
  public static ConstantPropagateDefaultProc getDefaultProc() {
    return new ConstantPropagateDefaultProc();
  }

  /**
   * The Node Processor for Constant Propagation for Select Operators.
   */
  public static class ConstantPropagateSelectProc implements NodeProcessor {
    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      SelectOperator op = (SelectOperator) nd;
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      Map<ColumnInfo, ExprNodeDesc> constants = cppCtx.getPropagatedConstants(op);
      cppCtx.getOpToConstantExprs().put(op, constants);
      foldOperator(op, cppCtx);
      List<ExprNodeDesc> colList = op.getConf().getColList();
      List<String> columnNames = op.getConf().getOutputColumnNames();
      Map<String, ExprNodeDesc> columnExprMap = op.getColumnExprMap();
      if (colList != null) {
        for (int i = 0; i < colList.size(); i++) {
          ExprNodeDesc newCol = foldExpr(colList.get(i), constants, cppCtx, op, 0, false);
          if (!(colList.get(i) instanceof ExprNodeConstantDesc) && newCol instanceof ExprNodeConstantDesc) {
            // Lets try to store original column name, if this column got folded
            // This is useful for optimizations like GroupByOptimizer
            String colName = colList.get(i).getExprString();
            if (HiveConf.getPositionFromInternalName(colName) == -1) {
              // if its not an internal name, this is what we want.
              ((ExprNodeConstantDesc)newCol).setFoldedFromCol(colName);
            } else {
              // If it was internal column, lets try to get name from columnExprMap
              ExprNodeDesc desc = columnExprMap.get(colName);
              if (desc instanceof ExprNodeConstantDesc) {
                ((ExprNodeConstantDesc)newCol).setFoldedFromCol(((ExprNodeConstantDesc)desc).getFoldedFromCol());
              }
            }
          }
          colList.set(i, newCol);
          if (columnExprMap != null) {
            columnExprMap.put(columnNames.get(i), newCol);
          }
        }
        LOG.debug("New column list:(" + StringUtils.join(colList, " ") + ")");
      }
      return null;
    }
  }

  /**
   * The Factory method to get the ConstantPropagateSelectProc class.
   *
   * @return ConstantPropagateSelectProc
   */
  public static ConstantPropagateSelectProc getSelectProc() {
    return new ConstantPropagateSelectProc();
  }

  /**
   * The Node Processor for constant propagation for FileSink Operators. In addition to constant
   * propagation, this processor also prunes dynamic partitions to static partitions if possible.
   */
  public static class ConstantPropagateFileSinkProc implements NodeProcessor {
    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      FileSinkOperator op = (FileSinkOperator) nd;
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      Map<ColumnInfo, ExprNodeDesc> constants = cppCtx.getPropagatedConstants(op);
      cppCtx.getOpToConstantExprs().put(op, constants);
      if (constants.isEmpty()) {
        return null;
      }
      FileSinkDesc fsdesc = op.getConf();
      DynamicPartitionCtx dpCtx = fsdesc.getDynPartCtx();
      if (dpCtx != null) {

        // If all dynamic partitions are propagated as constant, remove DP.
        Set<String> inputs = dpCtx.getInputToDPCols().keySet();

        // Assume only 1 parent for FS operator
        Operator<? extends Serializable> parent = op.getParentOperators().get(0);
        Map<ColumnInfo, ExprNodeDesc> parentConstants = cppCtx.getPropagatedConstants(parent);
        RowSchema rs = parent.getSchema();
        boolean allConstant = true;
        for (String input : inputs) {
          ColumnInfo ci = rs.getColumnInfo(input);
          if (parentConstants.get(ci) == null) {
            allConstant = false;
            break;
          }
        }
        if (allConstant) {
          pruneDP(fsdesc);
        }
      }
      foldOperator(op, cppCtx);
      return null;
    }

    private void pruneDP(FileSinkDesc fsdesc) {
      // FIXME: Support pruning dynamic partitioning.
      LOG.info("DP can be rewritten to SP!");
    }
  }

  public static NodeProcessor getFileSinkProc() {
    return new ConstantPropagateFileSinkProc();
  }

  /**
   * The Node Processor for Constant Propagation for Operators which is designed to stop propagate.
   * Currently these kinds of Operators include UnionOperator and ScriptOperator.
   */
  public static class ConstantPropagateStopProc implements NodeProcessor {
    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      Operator<?> op = (Operator<?>) nd;
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      cppCtx.getOpToConstantExprs().put(op, new HashMap<ColumnInfo, ExprNodeDesc>());
      LOG.debug("Stop propagate constants on op " + op.getOperatorId());
      return null;
    }
  }

  public static NodeProcessor getStopProc() {
    return new ConstantPropagateStopProc();
  }

  /**
   * The Node Processor for Constant Propagation for ReduceSink Operators. If the RS Operator is for
   * a join, then only those constants from inner join tables, or from the 'inner side' of a outer
   * join (left table for left outer join and vice versa) can be propagated.
   */
  public static class ConstantPropagateReduceSinkProc implements NodeProcessor {
    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      ReduceSinkOperator op = (ReduceSinkOperator) nd;
      ReduceSinkDesc rsDesc = op.getConf();
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      Map<ColumnInfo, ExprNodeDesc> constants = cppCtx.getPropagatedConstants(op);

      cppCtx.getOpToConstantExprs().put(op, constants);
      if (constants.isEmpty()) {
        return null;
      }

      if (op.getChildOperators().size() == 1
          && op.getChildOperators().get(0) instanceof JoinOperator) {
        JoinOperator joinOp = (JoinOperator) op.getChildOperators().get(0);
        if (skipFolding(joinOp.getConf())) {
          LOG.debug("Skip folding in outer join " + op);
          cppCtx.getOpToConstantExprs().put(op, new HashMap<ColumnInfo, ExprNodeDesc>());
          return null;
        }
      }

      if (rsDesc.getDistinctColumnIndices() != null
          && !rsDesc.getDistinctColumnIndices().isEmpty()) {
        LOG.debug("Skip folding in distinct subqueries " + op);
        cppCtx.getOpToConstantExprs().put(op, new HashMap<ColumnInfo, ExprNodeDesc>());
        return null;
      }

      // key columns
      ArrayList<ExprNodeDesc> newKeyEpxrs = new ArrayList<ExprNodeDesc>();
      for (ExprNodeDesc desc : rsDesc.getKeyCols()) {
        ExprNodeDesc newDesc = foldExpr(desc, constants, cppCtx, op, 0, false);
        if (newDesc != desc && desc instanceof ExprNodeColumnDesc && newDesc instanceof ExprNodeConstantDesc) {
          ((ExprNodeConstantDesc)newDesc).setFoldedFromCol(((ExprNodeColumnDesc)desc).getColumn());
        }
        newKeyEpxrs.add(newDesc);
      }
      rsDesc.setKeyCols(newKeyEpxrs);

      // partition columns
      ArrayList<ExprNodeDesc> newPartExprs = new ArrayList<ExprNodeDesc>();
      for (ExprNodeDesc desc : rsDesc.getPartitionCols()) {
        ExprNodeDesc expr = foldExpr(desc, constants, cppCtx, op, 0, false);
        if (expr != desc && desc instanceof ExprNodeColumnDesc
            && expr instanceof ExprNodeConstantDesc) {
          ((ExprNodeConstantDesc) expr).setFoldedFromCol(((ExprNodeColumnDesc) desc).getColumn());
        }
        newPartExprs.add(expr);
      }
      rsDesc.setPartitionCols(newPartExprs);

      // value columns
      ArrayList<ExprNodeDesc> newValExprs = new ArrayList<ExprNodeDesc>();
      for (ExprNodeDesc desc : rsDesc.getValueCols()) {
        newValExprs.add(foldExpr(desc, constants, cppCtx, op, 0, false));
      }
      rsDesc.setValueCols(newValExprs);
      foldOperator(op, cppCtx);
      return null;
    }

    /**
     * Skip folding constants if there is outer join in join tree.
     * @param joinDesc
     * @return true if to skip.
     */
    private boolean skipFolding(JoinDesc joinDesc) {
      for (JoinCondDesc cond : joinDesc.getConds()) {
        if (cond.getType() == JoinDesc.INNER_JOIN || cond.getType() == JoinDesc.UNIQUE_JOIN) {
          continue;
        }
        return true;
      }
      return false;
    }

  }

  public static NodeProcessor getReduceSinkProc() {
    return new ConstantPropagateReduceSinkProc();
  }

  /**
   * The Node Processor for Constant Propagation for Join Operators.
   */
  public static class ConstantPropagateJoinProc implements NodeProcessor {
    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      JoinOperator op = (JoinOperator) nd;
      JoinDesc conf = op.getConf();
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      Map<ColumnInfo, ExprNodeDesc> constants = cppCtx.getPropagatedConstants(op);
      cppCtx.getOpToConstantExprs().put(op, constants);
      if (constants.isEmpty()) {
        return null;
      }

      // Note: the following code (removing folded constants in exprs) is deeply coupled with
      //    ColumnPruner optimizer.
      // Assuming ColumnPrunner will remove constant columns so we don't deal with output columns.
      //    Except one case that the join operator is followed by a redistribution (RS operator).
      if (op.getChildOperators().size() == 1
          && op.getChildOperators().get(0) instanceof ReduceSinkOperator) {
        LOG.debug("Skip JOIN-RS structure.");
        return null;
      }
      LOG.info("Old exprs " + conf.getExprs());
      Iterator<Entry<Byte, List<ExprNodeDesc>>> itr = conf.getExprs().entrySet().iterator();
      while (itr.hasNext()) {
        Entry<Byte, List<ExprNodeDesc>> e = itr.next();
        int tag = e.getKey();
        List<ExprNodeDesc> exprs = e.getValue();
        if (exprs == null) {
          continue;
        }
        List<ExprNodeDesc> newExprs = new ArrayList<ExprNodeDesc>();
        for (ExprNodeDesc expr : exprs) {
          ExprNodeDesc newExpr = foldExpr(expr, constants, cppCtx, op, tag, false);
          if (newExpr instanceof ExprNodeConstantDesc) {
            LOG.info("expr " + newExpr + " fold from " + expr + " is removed.");
            continue;
          }
          newExprs.add(newExpr);
        }
        e.setValue(newExprs);
      }
      LOG.info("New exprs " + conf.getExprs());

      for (List<ExprNodeDesc> v : conf.getFilters().values()) {
        for (int i = 0; i < v.size(); i++) {
          ExprNodeDesc expr = foldExpr(v.get(i), constants, cppCtx, op, 0, false);
          v.set(i, expr);
        }
      }
      foldOperator(op, cppCtx);
      return null;
    }

  }

  public static NodeProcessor getJoinProc() {
    return new ConstantPropagateJoinProc();
  }

  /**
   * The Node Processor for Constant Propagation for Table Scan Operators.
   */
  public static class ConstantPropagateTableScanProc implements NodeProcessor {
    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx ctx, Object... nodeOutputs)
        throws SemanticException {
      TableScanOperator op = (TableScanOperator) nd;
      TableScanDesc conf = op.getConf();
      ConstantPropagateProcCtx cppCtx = (ConstantPropagateProcCtx) ctx;
      Map<ColumnInfo, ExprNodeDesc> constants = cppCtx.getPropagatedConstants(op);
      cppCtx.getOpToConstantExprs().put(op, constants);
      ExprNodeGenericFuncDesc pred = conf.getFilterExpr();
      if (pred == null) {
        return null;
      }

      ExprNodeDesc constant = foldExpr(pred, constants, cppCtx, op, 0, false);
      if (constant instanceof ExprNodeGenericFuncDesc) {
        conf.setFilterExpr((ExprNodeGenericFuncDesc) constant);
      } else {
        conf.setFilterExpr(null);
      }
      return null;
    }
  }

  public static NodeProcessor getTableScanProc() {
    return new ConstantPropagateTableScanProc();
  }
}


File: ql/src/java/org/apache/hadoop/hive/ql/parse/TezCompiler.java
/**
 *  Licensed to the Apache Software Foundation (ASF) under one
 *  or more contributor license agreements.  See the NOTICE file
 *  distributed with this work for additional information
 *  regarding copyright ownership.  The ASF licenses this file
 *  to you under the Apache License, Version 2.0 (the
 *  "License"); you may not use this file except in compliance
 *  with the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package org.apache.hadoop.hive.ql.parse;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Stack;
import java.util.concurrent.atomic.AtomicInteger;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.conf.HiveConf.ConfVars;
import org.apache.hadoop.hive.ql.Context;
import org.apache.hadoop.hive.ql.exec.AppMasterEventOperator;
import org.apache.hadoop.hive.ql.exec.CommonMergeJoinOperator;
import org.apache.hadoop.hive.ql.exec.ConditionalTask;
import org.apache.hadoop.hive.ql.exec.DummyStoreOperator;
import org.apache.hadoop.hive.ql.exec.FileSinkOperator;
import org.apache.hadoop.hive.ql.exec.FilterOperator;
import org.apache.hadoop.hive.ql.exec.JoinOperator;
import org.apache.hadoop.hive.ql.exec.MapJoinOperator;
import org.apache.hadoop.hive.ql.exec.Operator;
import org.apache.hadoop.hive.ql.exec.ReduceSinkOperator;
import org.apache.hadoop.hive.ql.exec.TableScanOperator;
import org.apache.hadoop.hive.ql.exec.Task;
import org.apache.hadoop.hive.ql.exec.UnionOperator;
import org.apache.hadoop.hive.ql.exec.tez.TezTask;
import org.apache.hadoop.hive.ql.hooks.ReadEntity;
import org.apache.hadoop.hive.ql.hooks.WriteEntity;
import org.apache.hadoop.hive.ql.lib.CompositeProcessor;
import org.apache.hadoop.hive.ql.lib.DefaultRuleDispatcher;
import org.apache.hadoop.hive.ql.lib.Dispatcher;
import org.apache.hadoop.hive.ql.lib.ForwardWalker;
import org.apache.hadoop.hive.ql.lib.GraphWalker;
import org.apache.hadoop.hive.ql.lib.Node;
import org.apache.hadoop.hive.ql.lib.NodeProcessor;
import org.apache.hadoop.hive.ql.lib.Rule;
import org.apache.hadoop.hive.ql.lib.RuleRegExp;
import org.apache.hadoop.hive.ql.metadata.Hive;
import org.apache.hadoop.hive.ql.optimizer.ConstantPropagate;
import org.apache.hadoop.hive.ql.optimizer.ConvertJoinMapJoin;
import org.apache.hadoop.hive.ql.optimizer.DynamicPartitionPruningOptimization;
import org.apache.hadoop.hive.ql.optimizer.MergeJoinProc;
import org.apache.hadoop.hive.ql.optimizer.ReduceSinkMapJoinProc;
import org.apache.hadoop.hive.ql.optimizer.RemoveDynamicPruningBySize;
import org.apache.hadoop.hive.ql.optimizer.SetReducerParallelism;
import org.apache.hadoop.hive.ql.optimizer.metainfo.annotation.AnnotateWithOpTraits;
import org.apache.hadoop.hive.ql.optimizer.physical.CrossProductCheck;
import org.apache.hadoop.hive.ql.optimizer.physical.MetadataOnlyOptimizer;
import org.apache.hadoop.hive.ql.optimizer.physical.NullScanOptimizer;
import org.apache.hadoop.hive.ql.optimizer.physical.PhysicalContext;
import org.apache.hadoop.hive.ql.optimizer.physical.StageIDsRearranger;
import org.apache.hadoop.hive.ql.optimizer.physical.Vectorizer;
import org.apache.hadoop.hive.ql.optimizer.stats.annotation.AnnotateWithStatistics;
import org.apache.hadoop.hive.ql.plan.BaseWork;
import org.apache.hadoop.hive.ql.plan.DynamicPruningEventDesc;
import org.apache.hadoop.hive.ql.plan.MapWork;
import org.apache.hadoop.hive.ql.plan.MoveWork;
import org.apache.hadoop.hive.ql.plan.OperatorDesc;
import org.apache.hadoop.hive.ql.plan.TezWork;
import org.apache.hadoop.hive.ql.session.SessionState.LogHelper;

/**
 * TezCompiler translates the operator plan into TezTasks.
 */
public class TezCompiler extends TaskCompiler {

  protected final Log LOG = LogFactory.getLog(TezCompiler.class);

  public TezCompiler() {
  }

  @Override
  public void init(HiveConf conf, LogHelper console, Hive db) {
    super.init(conf, console, db);

    // Tez requires us to use RPC for the query plan
    HiveConf.setBoolVar(conf, ConfVars.HIVE_RPC_QUERY_PLAN, true);

    // We require the use of recursive input dirs for union processing
    conf.setBoolean("mapred.input.dir.recursive", true);
    HiveConf.setBoolVar(conf, ConfVars.HIVE_HADOOP_SUPPORTS_SUBDIRECTORIES, true);
  }

  @Override
  protected void optimizeOperatorPlan(ParseContext pCtx, Set<ReadEntity> inputs,
      Set<WriteEntity> outputs) throws SemanticException {

    // Create the context for the walker
    OptimizeTezProcContext procCtx = new OptimizeTezProcContext(conf, pCtx, inputs, outputs);

    // setup dynamic partition pruning where possible
    runDynamicPartitionPruning(procCtx, inputs, outputs);

    // setup stats in the operator plan
    runStatsAnnotation(procCtx);

    // run the optimizations that use stats for optimization
    runStatsDependentOptimizations(procCtx, inputs, outputs);

    // after the stats phase we might have some cyclic dependencies that we need
    // to take care of.
    runCycleAnalysisForPartitionPruning(procCtx, inputs, outputs);

  }

  private void runCycleAnalysisForPartitionPruning(OptimizeTezProcContext procCtx,
      Set<ReadEntity> inputs, Set<WriteEntity> outputs) throws SemanticException {

    if (!procCtx.conf.getBoolVar(ConfVars.TEZ_DYNAMIC_PARTITION_PRUNING)) {
      return;
    }

    boolean cycleFree = false;
    while (!cycleFree) {
      cycleFree = true;
      Set<Set<Operator<?>>> components = getComponents(procCtx);
      for (Set<Operator<?>> component : components) {
        if (LOG.isDebugEnabled()) {
          LOG.debug("Component: ");
          for (Operator<?> co : component) {
            LOG.debug("Operator: " + co.getName() + ", " + co.getIdentifier());
          }
        }
        if (component.size() != 1) {
          LOG.info("Found cycle in operator plan...");
          cycleFree = false;
          removeEventOperator(component, procCtx);
          break;
        }
      }
      LOG.info("Cycle free: " + cycleFree);
    }
  }

  private void removeEventOperator(Set<Operator<?>> component, OptimizeTezProcContext context) {
    AppMasterEventOperator victim = null;
    for (Operator<?> o : component) {
      if (o instanceof AppMasterEventOperator) {
        if (victim == null
            || o.getConf().getStatistics().getDataSize() < victim.getConf().getStatistics()
                .getDataSize()) {
          victim = (AppMasterEventOperator) o;
        }
      }
    }

    if (victim == null ||
        (!context.pruningOpsRemovedByPriorOpt.isEmpty() &&
         context.pruningOpsRemovedByPriorOpt.contains(victim))) {
      return;
    }

    GenTezUtils.getUtils().removeBranch(victim);
    // at this point we've found the fork in the op pipeline that has the pruning as a child plan.
    LOG.info("Disabling dynamic pruning for: "
        + ((DynamicPruningEventDesc) victim.getConf()).getTableScan().toString()
        + ". Needed to break cyclic dependency");
  }

  // Tarjan's algo
  private Set<Set<Operator<?>>> getComponents(OptimizeTezProcContext procCtx) {
    Deque<Operator<?>> deque = new LinkedList<Operator<?>>();
    deque.addAll(procCtx.parseContext.getTopOps().values());

    AtomicInteger index = new AtomicInteger();
    Map<Operator<?>, Integer> indexes = new HashMap<Operator<?>, Integer>();
    Map<Operator<?>, Integer> lowLinks = new HashMap<Operator<?>, Integer>();
    Stack<Operator<?>> nodes = new Stack<Operator<?>>();
    Set<Set<Operator<?>>> components = new HashSet<Set<Operator<?>>>();

    for (Operator<?> o : deque) {
      if (!indexes.containsKey(o)) {
        connect(o, index, nodes, indexes, lowLinks, components);
      }
    }

    return components;
  }

  private void connect(Operator<?> o, AtomicInteger index, Stack<Operator<?>> nodes,
      Map<Operator<?>, Integer> indexes, Map<Operator<?>, Integer> lowLinks,
      Set<Set<Operator<?>>> components) {

    indexes.put(o, index.get());
    lowLinks.put(o, index.get());
    index.incrementAndGet();
    nodes.push(o);

    List<Operator<?>> children;
    if (o instanceof AppMasterEventOperator) {
      children = new ArrayList<Operator<?>>();
      children.addAll(o.getChildOperators());
      TableScanOperator ts = ((DynamicPruningEventDesc) o.getConf()).getTableScan();
      LOG.debug("Adding special edge: " + o.getName() + " --> " + ts.toString());
      children.add(ts);
    } else {
      children = o.getChildOperators();
    }

    for (Operator<?> child : children) {
      if (!indexes.containsKey(child)) {
        connect(child, index, nodes, indexes, lowLinks, components);
        lowLinks.put(o, Math.min(lowLinks.get(o), lowLinks.get(child)));
      } else if (nodes.contains(child)) {
        lowLinks.put(o, Math.min(lowLinks.get(o), indexes.get(child)));
      }
    }

    if (lowLinks.get(o).equals(indexes.get(o))) {
      Set<Operator<?>> component = new HashSet<Operator<?>>();
      components.add(component);
      Operator<?> current;
      do {
        current = nodes.pop();
        component.add(current);
      } while (current != o);
    }
  }

  private void runStatsAnnotation(OptimizeTezProcContext procCtx) throws SemanticException {
    new AnnotateWithStatistics().transform(procCtx.parseContext);
    new AnnotateWithOpTraits().transform(procCtx.parseContext);
  }

  private void runStatsDependentOptimizations(OptimizeTezProcContext procCtx,
      Set<ReadEntity> inputs, Set<WriteEntity> outputs) throws SemanticException {

    // Sequence of TableScan operators to be walked
    Deque<Operator<?>> deque = new LinkedList<Operator<?>>();
    deque.addAll(procCtx.parseContext.getTopOps().values());

    // create a walker which walks the tree in a DFS manner while maintaining
    // the operator stack.
    Map<Rule, NodeProcessor> opRules = new LinkedHashMap<Rule, NodeProcessor>();
    opRules.put(new RuleRegExp("Set parallelism - ReduceSink",
        ReduceSinkOperator.getOperatorName() + "%"),
        new SetReducerParallelism());

    opRules.put(new RuleRegExp("Convert Join to Map-join",
        JoinOperator.getOperatorName() + "%"), new ConvertJoinMapJoin());

    opRules.put(
        new RuleRegExp("Remove dynamic pruning by size",
        AppMasterEventOperator.getOperatorName() + "%"),
        new RemoveDynamicPruningBySize());

    // The dispatcher fires the processor corresponding to the closest matching
    // rule and passes the context along
    Dispatcher disp = new DefaultRuleDispatcher(null, opRules, procCtx);
    List<Node> topNodes = new ArrayList<Node>();
    topNodes.addAll(procCtx.parseContext.getTopOps().values());
    GraphWalker ogw = new ForwardWalker(disp);
    ogw.startWalking(topNodes, null);
  }

  private void runDynamicPartitionPruning(OptimizeTezProcContext procCtx, Set<ReadEntity> inputs,
      Set<WriteEntity> outputs) throws SemanticException {

    if (!procCtx.conf.getBoolVar(ConfVars.TEZ_DYNAMIC_PARTITION_PRUNING)) {
      return;
    }

    // Sequence of TableScan operators to be walked
    Deque<Operator<?>> deque = new LinkedList<Operator<?>>();
    deque.addAll(procCtx.parseContext.getTopOps().values());

    Map<Rule, NodeProcessor> opRules = new LinkedHashMap<Rule, NodeProcessor>();
    opRules.put(
        new RuleRegExp(new String("Dynamic Partition Pruning"), FilterOperator.getOperatorName()
            + "%"), new DynamicPartitionPruningOptimization());

    // The dispatcher fires the processor corresponding to the closest matching
    // rule and passes the context along
    Dispatcher disp = new DefaultRuleDispatcher(null, opRules, procCtx);
    List<Node> topNodes = new ArrayList<Node>();
    topNodes.addAll(procCtx.parseContext.getTopOps().values());
    GraphWalker ogw = new ForwardWalker(disp);
    ogw.startWalking(topNodes, null);

    // need a new run of the constant folding because we might have created lots
    // of "and true and true" conditions.
    if(procCtx.conf.getBoolVar(ConfVars.HIVEOPTCONSTANTPROPAGATION)) {
      new ConstantPropagate().transform(procCtx.parseContext);
    }
  }

  @Override
  protected void generateTaskTree(List<Task<? extends Serializable>> rootTasks, ParseContext pCtx,
      List<Task<MoveWork>> mvTask, Set<ReadEntity> inputs, Set<WriteEntity> outputs)
      throws SemanticException {

    GenTezUtils.getUtils().resetSequenceNumber();

    ParseContext tempParseContext = getParseContext(pCtx, rootTasks);
    GenTezWork genTezWork = new GenTezWork(GenTezUtils.getUtils());

    GenTezProcContext procCtx = new GenTezProcContext(
        conf, tempParseContext, mvTask, rootTasks, inputs, outputs);

    // create a walker which walks the tree in a DFS manner while maintaining
    // the operator stack.
    // The dispatcher generates the plan from the operator tree
    Map<Rule, NodeProcessor> opRules = new LinkedHashMap<Rule, NodeProcessor>();
    opRules.put(new RuleRegExp("Split Work - ReduceSink",
        ReduceSinkOperator.getOperatorName() + "%"),
        genTezWork);

    opRules.put(new RuleRegExp("No more walking on ReduceSink-MapJoin",
        MapJoinOperator.getOperatorName() + "%"), new ReduceSinkMapJoinProc());

    opRules.put(new RuleRegExp("Recoginze a Sorted Merge Join operator to setup the right edge and"
        + " stop traversing the DummyStore-MapJoin", CommonMergeJoinOperator.getOperatorName()
        + "%"), new MergeJoinProc());

    opRules.put(new RuleRegExp("Split Work + Move/Merge - FileSink",
        FileSinkOperator.getOperatorName() + "%"),
        new CompositeProcessor(new FileSinkProcessor(), genTezWork));

    opRules.put(new RuleRegExp("Split work - DummyStore", DummyStoreOperator.getOperatorName()
        + "%"), genTezWork);

    opRules.put(new RuleRegExp("Handle Potential Analyze Command",
        TableScanOperator.getOperatorName() + "%"),
        new ProcessAnalyzeTable(GenTezUtils.getUtils()));

    opRules.put(new RuleRegExp("Remember union",
        UnionOperator.getOperatorName() + "%"),
        new UnionProcessor());

    opRules.put(new RuleRegExp("AppMasterEventOperator",
        AppMasterEventOperator.getOperatorName() + "%"),
        new AppMasterEventProcessor());

    // The dispatcher fires the processor corresponding to the closest matching
    // rule and passes the context along
    Dispatcher disp = new DefaultRuleDispatcher(null, opRules, procCtx);
    List<Node> topNodes = new ArrayList<Node>();
    topNodes.addAll(pCtx.getTopOps().values());
    GraphWalker ogw = new GenTezWorkWalker(disp, procCtx);
    ogw.startWalking(topNodes, null);

    // we need to clone some operator plans and remove union operators still
    for (BaseWork w: procCtx.workWithUnionOperators) {
      GenTezUtils.getUtils().removeUnionOperators(conf, procCtx, w);
    }

    // then we make sure the file sink operators are set up right
    for (FileSinkOperator fileSink: procCtx.fileSinkSet) {
      GenTezUtils.getUtils().processFileSink(procCtx, fileSink);
    }

    // and finally we hook up any events that need to be sent to the tez AM
    LOG.debug("There are " + procCtx.eventOperatorSet.size() + " app master events.");
    for (AppMasterEventOperator event : procCtx.eventOperatorSet) {
      LOG.debug("Handling AppMasterEventOperator: " + event);
      GenTezUtils.getUtils().processAppMasterEvent(procCtx, event);
    }
  }

  @Override
  protected void setInputFormat(Task<? extends Serializable> task) {
    if (task instanceof TezTask) {
      TezWork work = ((TezTask)task).getWork();
      List<BaseWork> all = work.getAllWork();
      for (BaseWork w: all) {
        if (w instanceof MapWork) {
          MapWork mapWork = (MapWork) w;
          HashMap<String, Operator<? extends OperatorDesc>> opMap = mapWork.getAliasToWork();
          if (!opMap.isEmpty()) {
            for (Operator<? extends OperatorDesc> op : opMap.values()) {
              setInputFormat(mapWork, op);
            }
          }
        }
      }
    } else if (task instanceof ConditionalTask) {
      List<Task<? extends Serializable>> listTasks
        = ((ConditionalTask) task).getListTasks();
      for (Task<? extends Serializable> tsk : listTasks) {
        setInputFormat(tsk);
      }
    }

    if (task.getChildTasks() != null) {
      for (Task<? extends Serializable> childTask : task.getChildTasks()) {
        setInputFormat(childTask);
      }
    }
  }

  private void setInputFormat(MapWork work, Operator<? extends OperatorDesc> op) {
    if (op == null) {
      return;
    }
    if (op.isUseBucketizedHiveInputFormat()) {
      work.setUseBucketizedHiveInputFormat(true);
      return;
    }

    if (op.getChildOperators() != null) {
      for (Operator<? extends OperatorDesc> childOp : op.getChildOperators()) {
        setInputFormat(work, childOp);
      }
    }
  }

  @Override
  protected void decideExecMode(List<Task<? extends Serializable>> rootTasks, Context ctx,
      GlobalLimitCtx globalLimitCtx)
      throws SemanticException {
    // currently all Tez work is on the cluster
    return;
  }

  @Override
  protected void optimizeTaskPlan(List<Task<? extends Serializable>> rootTasks, ParseContext pCtx,
      Context ctx) throws SemanticException {
    PhysicalContext physicalCtx = new PhysicalContext(conf, pCtx, pCtx.getContext(), rootTasks,
       pCtx.getFetchTask());

    if (conf.getBoolVar(HiveConf.ConfVars.HIVENULLSCANOPTIMIZE)) {
      physicalCtx = new NullScanOptimizer().resolve(physicalCtx);
    } else {
      LOG.debug("Skipping null scan query optimization");
    }

    if (conf.getBoolVar(HiveConf.ConfVars.HIVEMETADATAONLYQUERIES)) {
      physicalCtx = new MetadataOnlyOptimizer().resolve(physicalCtx);
    } else {
      LOG.debug("Skipping metadata only query optimization");
    }

    if (conf.getBoolVar(HiveConf.ConfVars.HIVE_CHECK_CROSS_PRODUCT)) {
      physicalCtx = new CrossProductCheck().resolve(physicalCtx);
    } else {
      LOG.debug("Skipping cross product analysis");
    }

    if (conf.getBoolVar(HiveConf.ConfVars.HIVE_VECTORIZATION_ENABLED)) {
      physicalCtx = new Vectorizer().resolve(physicalCtx);
    } else {
      LOG.debug("Skipping vectorization");
    }

    if (!"none".equalsIgnoreCase(conf.getVar(HiveConf.ConfVars.HIVESTAGEIDREARRANGE))) {
      physicalCtx = new StageIDsRearranger().resolve(physicalCtx);
    } else {
      LOG.debug("Skipping stage id rearranger");
    }
    return;
  }
}
