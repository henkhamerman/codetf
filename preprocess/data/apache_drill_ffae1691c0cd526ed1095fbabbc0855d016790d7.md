Refactoring Types: ['Extract Method']
rg/apache/drill/exec/planner/sql/handlers/CreateTableHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.AbstractList;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import org.apache.calcite.plan.RelOptCluster;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.rel.type.RelDataTypeField;
import org.apache.calcite.rex.RexBuilder;
import org.apache.calcite.rex.RexInputRef;
import org.apache.calcite.rex.RexNode;
import org.apache.calcite.rex.RexUtil;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;

import org.apache.calcite.util.Pair;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.common.types.TypeProtos;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.planner.logical.DrillRel;
import org.apache.drill.exec.planner.logical.DrillScreenRel;
import org.apache.drill.exec.planner.logical.DrillStoreRel;
import org.apache.drill.exec.planner.logical.DrillWriterRel;
import org.apache.drill.exec.planner.physical.Prel;
import org.apache.drill.exec.planner.physical.ProjectAllowDupPrel;
import org.apache.drill.exec.planner.physical.ProjectPrel;
import org.apache.drill.exec.planner.physical.WriterPrel;
import org.apache.drill.exec.planner.physical.visitor.BasePrelVisitor;
import org.apache.drill.exec.planner.sql.DrillSqlOperator;
import org.apache.drill.exec.planner.sql.DrillSqlWorker;
import org.apache.drill.exec.planner.sql.SchemaUtilites;
import org.apache.drill.exec.planner.sql.parser.SqlCreateTable;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.util.Pointer;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.drill.exec.work.foreman.SqlUnsupportedException;

public class CreateTableHandler extends DefaultSqlHandler {
  public CreateTableHandler(SqlHandlerConfig config, Pointer<String> textPlan) {
    super(config, textPlan);
  }

  @Override
  public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
    SqlCreateTable sqlCreateTable = unwrap(sqlNode, SqlCreateTable.class);

    final String newTblName = sqlCreateTable.getName();
    final RelNode newTblRelNode =
        SqlHandlerUtil.resolveNewTableRel(false, planner, sqlCreateTable.getFieldNames(), sqlCreateTable.getQuery());


    final AbstractSchema drillSchema =
        SchemaUtilites.resolveToMutableDrillSchema(context.getNewDefaultSchema(), sqlCreateTable.getSchemaPath());
    final String schemaPath = drillSchema.getFullSchemaName();

    if (SqlHandlerUtil.getTableFromSchema(drillSchema, newTblName) != null) {
      throw UserException.validationError()
          .message("A table or view with given name [%s] already exists in schema [%s]", newTblName, schemaPath)
          .build();
    }

    final RelNode newTblRelNodeWithPCol = SqlHandlerUtil.qualifyPartitionCol(newTblRelNode, sqlCreateTable.getPartitionColumns());

    log("Optiq Logical", newTblRelNodeWithPCol);

    // Convert the query to Drill Logical plan and insert a writer operator on top.
    DrillRel drel = convertToDrel(newTblRelNodeWithPCol, drillSchema, newTblName, sqlCreateTable.getPartitionColumns());
    log("Drill Logical", drel);
    Prel prel = convertToPrel(drel, newTblRelNode.getRowType(), sqlCreateTable.getPartitionColumns());
    log("Drill Physical", prel);
    PhysicalOperator pop = convertToPop(prel);
    PhysicalPlan plan = convertToPlan(pop);
    log("Drill Plan", plan);

    return plan;
  }

  private DrillRel convertToDrel(RelNode relNode, AbstractSchema schema, String tableName, List<String> partitionColumns)
      throws RelConversionException {
    RelNode convertedRelNode = planner.transform(DrillSqlWorker.LOGICAL_RULES,
        relNode.getTraitSet().plus(DrillRel.DRILL_LOGICAL), relNode);

    if (convertedRelNode instanceof DrillStoreRel) {
      throw new UnsupportedOperationException();
    }

    DrillWriterRel writerRel = new DrillWriterRel(convertedRelNode.getCluster(), convertedRelNode.getTraitSet(),
        convertedRelNode, schema.createNewTable(tableName, partitionColumns));
    return new DrillScreenRel(writerRel.getCluster(), writerRel.getTraitSet(), writerRel);
  }

  private Prel convertToPrel(RelNode drel, RelDataType inputRowType, List<String> partitionColumns)
      throws RelConversionException, SqlUnsupportedException {
    Prel prel = convertToPrel(drel);

    prel = prel.accept(new ProjectForWriterVisitor(inputRowType, partitionColumns), null);

    return prel;
  }

  /**
   * A PrelVisitor which will insert a project under Writer.
   *
   * For CTAS : create table t1 partition by (con_A) select * from T1;
   *   A Project with Item expr will be inserted, in addition to *.  We need insert another Project to remove
   *   this additional expression.
   *
   * In addition, to make execution's implementation easier,  a special field is added to Project :
   *     PARTITION_COLUMN_IDENTIFIER = newPartitionValue(Partition_colA)
   *                                    || newPartitionValue(Partition_colB)
   *                                    || ...
   *                                    || newPartitionValue(Partition_colN).
   */
  private class ProjectForWriterVisitor extends BasePrelVisitor<Prel, Void, RuntimeException> {

    private final RelDataType queryRowType;
    private final List<String> partitionColumns;

    ProjectForWriterVisitor(RelDataType queryRowType, List<String> partitionColumns) {
      this.queryRowType = queryRowType;
      this.partitionColumns = partitionColumns;
    }

    @Override
    public Prel visitPrel(Prel prel, Void value) throws RuntimeException {
      List<RelNode> children = Lists.newArrayList();
      for(Prel child : prel){
        child = child.accept(this, null);
        children.add(child);
      }

      return (Prel) prel.copy(prel.getTraitSet(), children);

    }

    @Override
    public Prel visitWriter(WriterPrel prel, Void value) throws RuntimeException {

      final Prel child = ((Prel)prel.getInput()).accept(this, null);

      final RelDataType childRowType = child.getRowType();

      final RelOptCluster cluster = prel.getCluster();

      final List<RexNode> exprs = Lists.newArrayListWithExpectedSize(queryRowType.getFieldCount() + 1);
      final List<String> fieldnames = new ArrayList<String>(queryRowType.getFieldNames());

      for (final RelDataTypeField field : queryRowType.getFieldList()) {
        exprs.add(RexInputRef.of(field.getIndex(), queryRowType));
      }

      // No partition columns.
      if (partitionColumns.size() == 0) {
        final ProjectPrel projectUnderWriter = new ProjectAllowDupPrel(cluster,
            cluster.getPlanner().emptyTraitSet().plus(Prel.DRILL_PHYSICAL), child, exprs, queryRowType);

        return (Prel) prel.copy(projectUnderWriter.getTraitSet(),
            Collections.singletonList( (RelNode) projectUnderWriter));
      } else {
        // find list of partiiton columns.
        final List<RexNode> partitionColumnExprs = Lists.newArrayListWithExpectedSize(partitionColumns.size());
        for (final String colName : partitionColumns) {
          final RelDataTypeField field = childRowType.getField(colName, false, false);

          if (field == null) {
            throw UserException.validationError()
                .message("Partition column %s is not in the SELECT list of CTAS!", colName)
                .build();
          }

          partitionColumnExprs.add(RexInputRef.of(field.getIndex(), childRowType));
        }

        // Add partition column comparator to Project's field name list.
        fieldnames.add(WriterPrel.PARTITION_COMPARATOR_FIELD);

        // Add partition column comparator to Project's expression list.
        final RexNode partionColComp = createPartitionColComparator(prel.getCluster().getRexBuilder(), partitionColumnExprs);
        exprs.add(partionColComp);


        final RelDataType rowTypeWithPCComp = RexUtil.createStructType(cluster.getTypeFactory(), exprs, fieldnames);

        final ProjectPrel projectUnderWriter = new ProjectAllowDupPrel(cluster,
            cluster.getPlanner().emptyTraitSet().plus(Prel.DRILL_PHYSICAL), child, exprs, rowTypeWithPCComp);

        return (Prel) prel.copy(projectUnderWriter.getTraitSet(),
            Collections.singletonList( (RelNode) projectUnderWriter));
      }
    }

  }

  private RexNode createPartitionColComparator(final RexBuilder rexBuilder, List<RexNode> inputs) {
    final DrillSqlOperator op = new DrillSqlOperator(WriterPrel.PARTITION_COMPARATOR_FUNC, 1, true);

    final List<RexNode> compFuncs = Lists.newArrayListWithExpectedSize(inputs.size());

    for (final RexNode input : inputs) {
      compFuncs.add(rexBuilder.makeCall(op, ImmutableList.of(input)));
    }

    return RexUtil.composeDisjunction(rexBuilder, compFuncs, false);
  }

}

File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/DefaultSqlHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import org.apache.calcite.plan.RelOptPlanner;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.plan.RelTraitSet;
import org.apache.calcite.plan.hep.HepPlanner;
import org.apache.calcite.rel.RelNode;
import com.google.common.collect.ImmutableList;
import org.apache.calcite.plan.RelOptRule;
import org.apache.calcite.plan.hep.HepMatchOrder;
import org.apache.calcite.plan.hep.HepProgram;
import org.apache.calcite.plan.hep.HepProgramBuilder;
import org.apache.calcite.rel.RelShuttleImpl;
import org.apache.calcite.rel.core.Filter;
import org.apache.calcite.rel.core.Join;
import org.apache.calcite.rel.core.Project;
import org.apache.calcite.rel.core.RelFactories;
import org.apache.calcite.rel.core.TableFunctionScan;
import org.apache.calcite.rel.core.TableScan;
import org.apache.calcite.rel.logical.LogicalJoin;
import org.apache.calcite.rel.logical.LogicalProject;
import org.apache.calcite.rel.logical.LogicalValues;
import org.apache.calcite.rel.metadata.CachingRelMetadataProvider;
import org.apache.calcite.rel.metadata.ChainedRelMetadataProvider;
import org.apache.calcite.rel.metadata.DefaultRelMetadataProvider;
import org.apache.calcite.rel.metadata.RelMetadataProvider;
import org.apache.calcite.rel.rules.FilterAggregateTransposeRule;
import org.apache.calcite.rel.rules.FilterJoinRule;
import org.apache.calcite.rel.rules.FilterMergeRule;
import org.apache.calcite.rel.rules.FilterProjectTransposeRule;
import org.apache.calcite.rel.rules.JoinPushThroughJoinRule;
import org.apache.calcite.rel.rules.JoinPushTransitivePredicatesRule;
import org.apache.calcite.rel.rules.JoinToMultiJoinRule;
import org.apache.calcite.rel.rules.LoptOptimizeJoinRule;
import org.apache.calcite.rel.rules.ProjectMergeRule;
import org.apache.calcite.rel.rules.ProjectRemoveRule;
import org.apache.calcite.rel.rules.SemiJoinFilterTransposeRule;
import org.apache.calcite.rel.rules.SemiJoinJoinTransposeRule;
import org.apache.calcite.rel.rules.SemiJoinProjectTransposeRule;
import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.rex.RexBuilder;
import org.apache.calcite.rex.RexNode;
import org.apache.calcite.rex.RexUtil;
import org.apache.calcite.sql.SqlExplainLevel;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.TypedSqlNode;
import org.apache.calcite.sql.validate.SqlValidatorUtil;
import org.apache.calcite.sql2rel.RelFieldTrimmer;
import org.apache.calcite.tools.Planner;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;
import org.apache.drill.common.JSONOptions;
import org.apache.drill.common.logical.PlanProperties;
import org.apache.drill.common.logical.PlanProperties.Generator.ResultMode;
import org.apache.drill.common.logical.PlanProperties.PlanPropertiesBuilder;
import org.apache.drill.common.logical.PlanProperties.PlanType;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.physical.base.AbstractPhysicalVisitor;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.physical.impl.join.JoinUtils;
import org.apache.drill.exec.planner.cost.DrillDefaultRelMetadataProvider;
import org.apache.drill.exec.planner.logical.DrillFilterJoinRules;
import org.apache.drill.exec.planner.logical.DrillJoinRel;
import org.apache.drill.exec.planner.logical.DrillMergeProjectRule;
import org.apache.drill.exec.planner.logical.DrillProjectRel;
import org.apache.drill.exec.planner.logical.DrillPushFilterPastProjectRule;
import org.apache.drill.exec.planner.logical.DrillPushProjectPastFilterRule;
import org.apache.drill.exec.planner.logical.DrillRel;
import org.apache.drill.exec.planner.logical.DrillRelFactories;
import org.apache.drill.exec.planner.logical.DrillScreenRel;
import org.apache.drill.exec.planner.logical.DrillStoreRel;
import org.apache.drill.exec.planner.logical.PreProcessLogicalRel;
import org.apache.drill.exec.planner.physical.DrillDistributionTrait;
import org.apache.drill.exec.planner.physical.PhysicalPlanCreator;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.planner.physical.Prel;
import org.apache.drill.exec.planner.physical.explain.PrelSequencer;
import org.apache.drill.exec.planner.physical.visitor.ComplexToJsonPrelVisitor;
import org.apache.drill.exec.planner.physical.visitor.ExcessiveExchangeIdentifier;
import org.apache.drill.exec.planner.physical.visitor.FinalColumnReorderer;
import org.apache.drill.exec.planner.physical.visitor.InsertLocalExchangeVisitor;
import org.apache.drill.exec.planner.physical.visitor.JoinPrelRenameVisitor;
import org.apache.drill.exec.planner.physical.visitor.MemoryEstimationVisitor;
import org.apache.drill.exec.planner.physical.visitor.RelUniqifier;
import org.apache.drill.exec.planner.physical.visitor.RewriteProjectToFlatten;
import org.apache.drill.exec.planner.physical.visitor.SelectionVectorPrelVisitor;
import org.apache.drill.exec.planner.physical.visitor.SplitUpComplexExpressions;
import org.apache.drill.exec.planner.physical.visitor.StarColumnConverter;
import org.apache.drill.exec.planner.physical.visitor.SwapHashJoinVisitor;
import org.apache.drill.exec.planner.sql.DrillSqlWorker;
import org.apache.drill.exec.planner.sql.parser.UnsupportedOperatorsVisitor;
import org.apache.drill.exec.server.options.OptionManager;
import org.apache.drill.exec.server.options.OptionValue;
import org.apache.drill.exec.util.Pointer;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.drill.exec.work.foreman.SqlUnsupportedException;
import org.apache.drill.exec.work.foreman.UnsupportedRelOperatorException;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.google.common.base.Preconditions;
import com.google.common.collect.Lists;

public class DefaultSqlHandler extends AbstractSqlHandler {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(DefaultSqlHandler.class);

  protected final SqlHandlerConfig config;
  protected final QueryContext context;
  protected final HepPlanner hepPlanner;
  protected final Planner planner;
  private Pointer<String> textPlan;
  private final long targetSliceSize;

  public DefaultSqlHandler(SqlHandlerConfig config) {
    this(config, null);
  }

  public DefaultSqlHandler(SqlHandlerConfig config, Pointer<String> textPlan) {
    super();
    this.planner = config.getPlanner();
    this.context = config.getContext();
    this.hepPlanner = config.getHepPlanner();
    this.config = config;
    this.textPlan = textPlan;
    targetSliceSize = context.getOptions().getOption(ExecConstants.SLICE_TARGET).num_val;
  }

  protected void log(String name, RelNode node) {
    if (logger.isDebugEnabled()) {
      logger.debug(name + " : \n" + RelOptUtil.toString(node, SqlExplainLevel.ALL_ATTRIBUTES));
    }
  }

  protected void log(String name, Prel node) {
    String plan = PrelSequencer.printWithIds(node, SqlExplainLevel.ALL_ATTRIBUTES);
    if(textPlan != null){
      textPlan.value = plan;
    }

    if (logger.isDebugEnabled()) {
      logger.debug(name + " : \n" + plan);
    }
  }

  protected void log(String name, PhysicalPlan plan) throws JsonProcessingException {
    if (logger.isDebugEnabled()) {
      String planText = plan.unparse(context.getConfig().getMapper().writer());
      logger.debug(name + " : \n" + planText);
    }
  }

  @Override
  public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
    SqlNode rewrittenSqlNode = rewrite(sqlNode);
    TypedSqlNode validatedTypedSqlNode = validateNode(rewrittenSqlNode);
    SqlNode validated = validatedTypedSqlNode.getSqlNode();
    RelDataType validatedRowType = validatedTypedSqlNode.getType();

    RelNode rel = convertToRel(validated);
    rel = preprocessNode(rel);


    log("Optiq Logical", rel);
    DrillRel drel = convertToDrel(rel, validatedRowType);

    log("Drill Logical", drel);
    Prel prel = convertToPrel(drel);
    log("Drill Physical", prel);
    PhysicalOperator pop = convertToPop(prel);
    PhysicalPlan plan = convertToPlan(pop);
    log("Drill Plan", plan);
    return plan;
  }

  protected DrillRel addRenamedProject(DrillRel rel, RelDataType validatedRowType) {
    RelDataType t = rel.getRowType();

    RexBuilder b = rel.getCluster().getRexBuilder();
    List<RexNode> projections = Lists.newArrayList();
    int projectCount = t.getFieldList().size();

    for (int i =0; i < projectCount; i++) {
      projections.add(b.makeInputRef(rel, i));
    }

    final List<String> fieldNames2 = SqlValidatorUtil.uniquify(validatedRowType.getFieldNames(), SqlValidatorUtil.F_SUGGESTER2);

    RelDataType newRowType = RexUtil.createStructType(rel.getCluster().getTypeFactory(), projections, fieldNames2);

    DrillProjectRel topProj = DrillProjectRel.create(rel.getCluster(), rel.getTraitSet(), rel, projections, newRowType);

    if (ProjectRemoveRule.isTrivial(topProj, true)) {
      return rel;
    } else{
      return topProj;
    }
    //return RelOptUtil.createProject(rel, projections, fieldNames2);

  }


  protected TypedSqlNode validateNode(SqlNode sqlNode) throws ValidationException, RelConversionException, ForemanSetupException {
    TypedSqlNode typedSqlNode = planner.validateAndGetType(sqlNode);

    SqlNode sqlNodeValidated = typedSqlNode.getSqlNode();

    // Check if the unsupported functionality is used
    UnsupportedOperatorsVisitor visitor = UnsupportedOperatorsVisitor.createVisitor(context);
    try {
      sqlNodeValidated.accept(visitor);
    } catch (UnsupportedOperationException ex) {
      // If the exception due to the unsupported functionalities
      visitor.convertException();

      // If it is not, let this exception move forward to higher logic
      throw ex;
    }

    return typedSqlNode;
  }

  protected RelNode convertToRel(SqlNode node) throws RelConversionException {
    RelNode convertedNode = planner.convert(node);
    hepPlanner.setRoot(convertedNode);
    RelNode rel = hepPlanner.findBestExp();

    return rel;
  }

  protected RelNode preprocessNode(RelNode rel) throws SqlUnsupportedException {
    /*
     * Traverse the tree to do the following pre-processing tasks: 1. replace the convert_from, convert_to function to
     * actual implementations Eg: convert_from(EXPR, 'JSON') be converted to convert_fromjson(EXPR); TODO: Ideally all
     * function rewrites would move here instead of DrillOptiq.
     *
     * 2. see where the tree contains unsupported functions; throw SqlUnsupportedException if there is any.
     */

    PreProcessLogicalRel visitor = PreProcessLogicalRel.createVisitor(planner.getTypeFactory(),
        context.getDrillOperatorTable());
    try {
      rel = rel.accept(visitor);
    } catch (UnsupportedOperationException ex) {
      visitor.convertException();
      throw ex;
    }

    return rel;
  }

  protected DrillRel convertToDrel(RelNode relNode, RelDataType validatedRowType) throws RelConversionException, SqlUnsupportedException {
    try {
      RelNode convertedRelNode;

      if (! context.getPlannerSettings().isHepJoinOptEnabled()) {
        convertedRelNode = logicalPlanningVolcano(relNode);
      } else {
        convertedRelNode = logicalPlanningVolcanoAndLopt(relNode);
      }

      if (convertedRelNode instanceof DrillStoreRel) {
        throw new UnsupportedOperationException();
      } else {

        // If the query contains a limit 0 clause, disable distributed mode since it is overkill for determining schema.
        if (FindLimit0Visitor.containsLimit0(convertedRelNode)) {
          context.getPlannerSettings().forceSingleMode();
        }

        // Put a non-trivial topProject to ensure the final output field name is preserved, when necessary.
        DrillRel topPreservedNameProj = addRenamedProject((DrillRel) convertedRelNode, validatedRowType);
        return new DrillScreenRel(topPreservedNameProj.getCluster(), topPreservedNameProj.getTraitSet(),
            topPreservedNameProj);
      }
    } catch (RelOptPlanner.CannotPlanException ex) {
      logger.error(ex.getMessage());

      if(JoinUtils.checkCartesianJoin(relNode, new ArrayList<Integer>(), new ArrayList<Integer>())) {
        throw new UnsupportedRelOperatorException("This query cannot be planned possibly due to either a cartesian join or an inequality join");
      } else {
        throw ex;
      }
    }
  }


  protected Prel convertToPrel(RelNode drel) throws RelConversionException, SqlUnsupportedException {
    Preconditions.checkArgument(drel.getConvention() == DrillRel.DRILL_LOGICAL);
    RelTraitSet traits = drel.getTraitSet().plus(Prel.DRILL_PHYSICAL).plus(DrillDistributionTrait.SINGLETON);
    Prel phyRelNode;
    try {
      phyRelNode = (Prel) planner.transform(DrillSqlWorker.PHYSICAL_MEM_RULES, traits, drel);
    } catch (RelOptPlanner.CannotPlanException ex) {
      logger.error(ex.getMessage());

      if(JoinUtils.checkCartesianJoin(drel, new ArrayList<Integer>(), new ArrayList<Integer>())) {
        throw new UnsupportedRelOperatorException("This query cannot be planned possibly due to either a cartesian join or an inequality join");
      } else {
        throw ex;
      }
    }

    OptionManager queryOptions = context.getOptions();

    if (context.getPlannerSettings().isMemoryEstimationEnabled()
      && !MemoryEstimationVisitor.enoughMemory(phyRelNode, queryOptions, context.getActiveEndpoints().size())) {
      log("Not enough memory for this plan", phyRelNode);
      logger.debug("Re-planning without hash operations.");

      queryOptions.setOption(OptionValue.createBoolean(OptionValue.OptionType.QUERY, PlannerSettings.HASHJOIN.getOptionName(), false));
      queryOptions.setOption(OptionValue.createBoolean(OptionValue.OptionType.QUERY, PlannerSettings.HASHAGG.getOptionName(), false));

      try {
        phyRelNode = (Prel) planner.transform(DrillSqlWorker.PHYSICAL_MEM_RULES, traits, drel);
      } catch (RelOptPlanner.CannotPlanException ex) {
        logger.error(ex.getMessage());

        if(JoinUtils.checkCartesianJoin(drel, new ArrayList<Integer>(), new ArrayList<Integer>())) {
          throw new UnsupportedRelOperatorException("This query cannot be planned possibly due to either a cartesian join or an inequality join");
        } else {
          throw ex;
        }
      }
    }

    /*  The order of the following transformation is important */

    /*
     * 0.) For select * from join query, we need insert project on top of scan and a top project just
     * under screen operator. The project on top of scan will rename from * to T1*, while the top project
     * will rename T1* to *, before it output the final result. Only the top project will allow
     * duplicate columns, since user could "explicitly" ask for duplicate columns ( select *, col, *).
     * The rest of projects will remove the duplicate column when we generate POP in json format.
     */
    phyRelNode = StarColumnConverter.insertRenameProject(phyRelNode);

    /*
     * 1.)
     * Join might cause naming conflicts from its left and right child.
     * In such case, we have to insert Project to rename the conflicting names.
     */
    phyRelNode = JoinPrelRenameVisitor.insertRenameProject(phyRelNode);

    /*
     * 1.1) Swap left / right for INNER hash join, if left's row count is < (1 + margin) right's row count.
     * We want to have smaller dataset on the right side, since hash table builds on right side.
     */
    if (context.getPlannerSettings().isHashJoinSwapEnabled()) {
      phyRelNode = SwapHashJoinVisitor.swapHashJoin(phyRelNode, new Double(context.getPlannerSettings().getHashJoinSwapMarginFactor()));
    }

    /*
     * 1.2) Break up all expressions with complex outputs into their own project operations
     */
    phyRelNode = ((Prel) phyRelNode).accept(new SplitUpComplexExpressions(planner.getTypeFactory(), context.getDrillOperatorTable(), context.getPlannerSettings().functionImplementationRegistry), null);

    /*
     * 1.3) Projections that contain reference to flatten are rewritten as Flatten operators followed by Project
     */
    phyRelNode = ((Prel) phyRelNode).accept(new RewriteProjectToFlatten(planner.getTypeFactory(), context.getDrillOperatorTable()), null);

    /*
     * 2.)
     * Since our operators work via names rather than indices, we have to make to reorder any
     * output before we return data to the user as we may have accidentally shuffled things.
     * This adds a trivial project to reorder columns prior to output.
     */
    phyRelNode = FinalColumnReorderer.addFinalColumnOrdering(phyRelNode);

    /*
     * 3.)
     * If two fragments are both estimated to be parallelization one, remove the exchange
     * separating them
     */
    phyRelNode = ExcessiveExchangeIdentifier.removeExcessiveEchanges(phyRelNode, targetSliceSize);


    /* 4.)
     * Add ProducerConsumer after each scan if the option is set
     * Use the configured queueSize
     */
    /* DRILL-1617 Disabling ProducerConsumer as it produces incorrect results
    if (context.getOptions().getOption(PlannerSettings.PRODUCER_CONSUMER.getOptionName()).bool_val) {
      long queueSize = context.getOptions().getOption(PlannerSettings.PRODUCER_CONSUMER_QUEUE_SIZE.getOptionName()).num_val;
      phyRelNode = ProducerConsumerPrelVisitor.addProducerConsumerToScans(phyRelNode, (int) queueSize);
    }
    */


    /* 5.)
     * if the client does not support complex types (Map, Repeated)
     * insert a project which which would convert
     */
    if (!context.getSession().isSupportComplexTypes()) {
      logger.debug("Client does not support complex types, add ComplexToJson operator.");
      phyRelNode = ComplexToJsonPrelVisitor.addComplexToJsonPrel(phyRelNode);
    }


    /* 6.)
     * Insert LocalExchange (mux and/or demux) nodes
     */
    phyRelNode = InsertLocalExchangeVisitor.insertLocalExchanges(phyRelNode, queryOptions);


    /* 7.)
     * Next, we add any required selection vector removers given the supported encodings of each
     * operator. This will ultimately move to a new trait but we're managing here for now to avoid
     * introducing new issues in planning before the next release
     */
    phyRelNode = SelectionVectorPrelVisitor.addSelectionRemoversWhereNecessary(phyRelNode);

    /* 8.)
     * Finally, Make sure that the no rels are repeats.
     * This could happen in the case of querying the same table twice as Optiq may canonicalize these.
     */
    phyRelNode = RelUniqifier.uniqifyGraph(phyRelNode);

    return phyRelNode;
  }

  protected PhysicalOperator convertToPop(Prel prel) throws IOException {
    PhysicalPlanCreator creator = new PhysicalPlanCreator(context, PrelSequencer.getIdMap(prel));
    PhysicalOperator op = prel.getPhysicalOperator(creator);
    return op;
  }

  protected PhysicalPlan convertToPlan(PhysicalOperator op) {
    PlanPropertiesBuilder propsBuilder = PlanProperties.builder();
    propsBuilder.type(PlanType.APACHE_DRILL_PHYSICAL);
    propsBuilder.version(1);
    propsBuilder.options(new JSONOptions(context.getOptions().getOptionList()));
    propsBuilder.resultMode(ResultMode.EXEC);
    propsBuilder.generator(this.getClass().getSimpleName(), "");
    return new PhysicalPlan(propsBuilder.build(), getPops(op));
  }

  public static List<PhysicalOperator> getPops(PhysicalOperator root) {
    List<PhysicalOperator> ops = Lists.newArrayList();
    PopCollector c = new PopCollector();
    root.accept(c, ops);
    return ops;
  }

  private static class PopCollector extends
      AbstractPhysicalVisitor<Void, Collection<PhysicalOperator>, RuntimeException> {

    @Override
    public Void visitOp(PhysicalOperator op, Collection<PhysicalOperator> collection) throws RuntimeException {
      collection.add(op);
      for (PhysicalOperator o : op) {
        o.accept(this, collection);
      }
      return null;
    }

  }

  /**
   * Rewrite the parse tree. Used before validating the parse tree. Useful if a particular statement needs to converted
   * into another statement.
   *
   * @param node
   * @return Rewritten sql parse tree
   * @throws RelConversionException
   */
  public SqlNode rewrite(SqlNode node) throws RelConversionException, ForemanSetupException {
    return node;
  }

  private RelNode logicalPlanningVolcano(RelNode relNode) throws RelConversionException, SqlUnsupportedException {
    return planner.transform(DrillSqlWorker.LOGICAL_RULES, relNode.getTraitSet().plus(DrillRel.DRILL_LOGICAL), relNode);
  }

  /**
   * Do logical planning using both VolcanoPlanner and LOPT HepPlanner.
   * @param relNode
   * @return
   * @throws RelConversionException
   * @throws SqlUnsupportedException
   */
  private RelNode logicalPlanningVolcanoAndLopt(RelNode relNode) throws RelConversionException, SqlUnsupportedException {

    final RelNode convertedRelNode = planner.transform(DrillSqlWorker.LOGICAL_CONVERT_RULES, relNode.getTraitSet().plus(DrillRel.DRILL_LOGICAL), relNode);
    log("VolCalciteRel", convertedRelNode);

    final RelNode loptNode = getLoptJoinOrderTree(
        convertedRelNode,
        DrillJoinRel.class,
        DrillRelFactories.DRILL_LOGICAL_JOIN_FACTORY,
        DrillRelFactories.DRILL_LOGICAL_FILTER_FACTORY,
        DrillRelFactories.DRILL_LOGICAL_PROJECT_FACTORY);

    log("HepCalciteRel", loptNode);

    return loptNode;
  }


  /**
   * Appy Join Order Optimizations using Hep Planner.
   */
  public RelNode getLoptJoinOrderTree(RelNode root,
                                      Class<? extends Join> joinClass,
                                             RelFactories.JoinFactory joinFactory,
                                             RelFactories.FilterFactory filterFactory,
                                             RelFactories.ProjectFactory projectFactory) {
    final HepProgramBuilder hepPgmBldr = new HepProgramBuilder()
        .addMatchOrder(HepMatchOrder.BOTTOM_UP)
        .addRuleInstance(new JoinToMultiJoinRule(joinClass))
        .addRuleInstance(new LoptOptimizeJoinRule(joinFactory, projectFactory, filterFactory))
        .addRuleInstance(ProjectRemoveRule.INSTANCE);
        // .addRuleInstance(new ProjectMergeRule(true, projectFactory));

        // .addRuleInstance(DrillMergeProjectRule.getInstance(true, projectFactory, this.context.getFunctionRegistry()));


    final HepProgram hepPgm = hepPgmBldr.build();
    final HepPlanner hepPlanner = new HepPlanner(hepPgm);

    final List<RelMetadataProvider> list = Lists.newArrayList();
    list.add(DrillDefaultRelMetadataProvider.INSTANCE);
    hepPlanner.registerMetadataProviders(list);
    final RelMetadataProvider cachingMetaDataProvider = new CachingRelMetadataProvider(ChainedRelMetadataProvider.of(list), hepPlanner);

    // Modify RelMetaProvider for every RelNode in the SQL operator Rel tree.
    root.accept(new MetaDataProviderModifier(cachingMetaDataProvider));

    hepPlanner.setRoot(root);

    RelNode calciteOptimizedPlan = hepPlanner.findBestExp();

    return calciteOptimizedPlan;
  }


  public static class MetaDataProviderModifier extends RelShuttleImpl {
    private final RelMetadataProvider metadataProvider;

    public MetaDataProviderModifier(RelMetadataProvider metadataProvider) {
      this.metadataProvider = metadataProvider;
    }

    @Override
    public RelNode visit(TableScan scan) {
      scan.getCluster().setMetadataProvider(metadataProvider);
      return super.visit(scan);
    }

    @Override
    public RelNode visit(TableFunctionScan scan) {
      scan.getCluster().setMetadataProvider(metadataProvider);
      return super.visit(scan);
    }

    @Override
    public RelNode visit(LogicalValues values) {
      values.getCluster().setMetadataProvider(metadataProvider);
      return super.visit(values);
    }

    @Override
    protected RelNode visitChild(RelNode parent, int i, RelNode child) {
      child.accept(this);
      parent.getCluster().setMetadataProvider(metadataProvider);
      return parent;
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/ExplainHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;

import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.sql.TypedSqlNode;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;

import org.apache.drill.common.logical.LogicalPlan;
import org.apache.drill.common.logical.PlanProperties.Generator.ResultMode;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.planner.logical.DrillImplementor;
import org.apache.drill.exec.planner.logical.DrillParseContext;
import org.apache.drill.exec.planner.logical.DrillRel;
import org.apache.drill.exec.planner.physical.Prel;
import org.apache.drill.exec.planner.physical.explain.PrelSequencer;
import org.apache.drill.exec.planner.sql.DirectPlan;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.sql.SqlExplain;
import org.apache.calcite.sql.SqlExplainLevel;
import org.apache.calcite.sql.SqlLiteral;
import org.apache.calcite.sql.SqlNode;

public class ExplainHandler extends DefaultSqlHandler {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ExplainHandler.class);

  private ResultMode mode;
  private SqlExplainLevel level = SqlExplainLevel.ALL_ATTRIBUTES;
  public ExplainHandler(SqlHandlerConfig config) {
    super(config);
  }

  @Override
  public PhysicalPlan getPlan(SqlNode node) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
    SqlNode sqlNode = rewrite(node);
    TypedSqlNode validatedTypedSqlNode = validateNode(sqlNode);
    SqlNode validated = validatedTypedSqlNode.getSqlNode();
    RelDataType validatedRowType = validatedTypedSqlNode.getType();

    RelNode rel = convertToRel(validated);
    rel = preprocessNode(rel);

    log("Optiq Logical", rel);
    DrillRel drel = convertToDrel(rel, validatedRowType);
    log("Drill Logical", drel);

    if (mode == ResultMode.LOGICAL) {
      LogicalExplain logicalResult = new LogicalExplain(drel, level, context);
      return DirectPlan.createDirectPlan(context, logicalResult);
    }

    Prel prel = convertToPrel(drel);
    log("Drill Physical", prel);
    PhysicalOperator pop = convertToPop(prel);
    PhysicalPlan plan = convertToPlan(pop);
    log("Drill Plan", plan);
    PhysicalExplain physicalResult = new PhysicalExplain(prel, plan, level, context);
    return DirectPlan.createDirectPlan(context, physicalResult);
  }

  @Override
  public SqlNode rewrite(SqlNode sqlNode) throws RelConversionException, ForemanSetupException {
    SqlExplain node = unwrap(sqlNode, SqlExplain.class);
    SqlLiteral op = node.operand(2);
    SqlExplain.Depth depth = (SqlExplain.Depth) op.getValue();
    if (node.getDetailLevel() != null) {
      level = node.getDetailLevel();
    }
    switch (depth) {
    case LOGICAL:
      mode = ResultMode.LOGICAL;
      break;
    case PHYSICAL:
      mode = ResultMode.PHYSICAL;
      break;
    default:
      throw new UnsupportedOperationException("Unknown depth " + depth);
    }

    return node.operand(0);
  }


  public static class LogicalExplain{
    public String text;
    public String json;

    public LogicalExplain(RelNode node, SqlExplainLevel level, QueryContext context) {
      this.text = RelOptUtil.toString(node, level);
      DrillImplementor implementor = new DrillImplementor(new DrillParseContext(context.getPlannerSettings()), ResultMode.LOGICAL);
      implementor.go( (DrillRel) node);
      LogicalPlan plan = implementor.getPlan();
      this.json = plan.unparse(context.getConfig());
    }
  }

  public static class PhysicalExplain{
    public String text;
    public String json;

    public PhysicalExplain(RelNode node, PhysicalPlan plan, SqlExplainLevel level, QueryContext context) {
      this.text = PrelSequencer.printWithIds((Prel) node, level);
      this.json = plan.unparse(context.getConfig().getMapper().writer());
    }
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/SqlHandlerUtil.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import org.apache.calcite.rel.type.RelDataTypeField;
import org.apache.calcite.rex.RexBuilder;
import org.apache.calcite.rex.RexInputRef;
import org.apache.calcite.rex.RexLiteral;
import org.apache.calcite.rex.RexNode;
import org.apache.calcite.schema.Table;
import org.apache.calcite.sql.SqlNodeList;
import org.apache.calcite.sql.SqlWriter;
import org.apache.calcite.sql.TypedSqlNode;
import org.apache.calcite.sql.fun.SqlStdOperatorTable;
import org.apache.calcite.tools.Planner;
import org.apache.calcite.tools.RelConversionException;
import org.apache.drill.common.exceptions.DrillException;
import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.planner.StarColumnHelper;
import org.apache.drill.exec.planner.common.DrillRelOptUtil;
import org.apache.drill.exec.planner.sql.DirectPlan;
import org.apache.drill.exec.planner.types.DrillFixedRelDataTypeImpl;
import org.apache.drill.exec.store.AbstractSchema;

import org.apache.calcite.tools.ValidationException;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.sql.SqlNode;
import org.apache.drill.exec.store.ischema.Records;

import java.util.AbstractList;
import java.util.HashSet;
import java.util.List;

public class SqlHandlerUtil {

  /**
   * Resolve final RelNode of the new table (or view) for given table field list and new table definition.
   *
   * @param isNewTableView Is the new table created a view? This doesn't affect the functionality, but it helps format
   *                       better error messages.
   * @param planner Planner instance.
   * @param tableFieldNames List of fields specified in new table/view field list. These are the fields given just after
   *                        new table name.
   *                        Ex. CREATE TABLE newTblName(col1, medianOfCol2, avgOfCol3) AS
   *                        SELECT col1, median(col2), avg(col3) FROM sourcetbl GROUP BY col1;
   * @param newTableQueryDef  Sql tree of definition of the new table or view (query after the AS keyword). This tree is
   *                          modified, so it is responsibility of caller's to make a copy if needed.
   * @throws ValidationException If table's fields list and field list specified in table definition are not valid.
   * @throws RelConversionException If failed to convert the table definition into a RelNode.
   */
  public static RelNode resolveNewTableRel(boolean isNewTableView, Planner planner, List<String> tableFieldNames,
      SqlNode newTableQueryDef) throws ValidationException, RelConversionException {


    TypedSqlNode validatedSqlNodeWithType = planner.validateAndGetType(newTableQueryDef);

    // Get the row type of view definition query.
    // Reason for getting the row type from validated SqlNode than RelNode is because SqlNode -> RelNode involves
    // renaming duplicate fields which is not desired when creating a view or table.
    // For ex: SELECT region_id, region_id FROM cp.`region.json` LIMIT 1 returns
    //  +------------+------------+
    //  | region_id  | region_id0 |
    //  +------------+------------+
    //  | 0          | 0          |
    //  +------------+------------+
    // which is not desired when creating new views or tables.
    final RelDataType queryRowType = validatedSqlNodeWithType.getType();
    final RelNode validatedQueryRelNode = planner.convert(validatedSqlNodeWithType.getSqlNode());

    if (tableFieldNames.size() > 0) {
      // Field count should match.
      if (tableFieldNames.size() != queryRowType.getFieldCount()) {
        final String tblType = isNewTableView ? "view" : "table";
        throw UserException.validationError()
            .message("%s's field list and the %s's query field list have different counts.", tblType, tblType)
            .build();
      }

      // CTAS's query field list shouldn't have "*" when table's field list is specified.
      for (String field : queryRowType.getFieldNames()) {
        if (field.equals("*")) {
          final String tblType = isNewTableView ? "view" : "table";
          throw UserException.validationError()
              .message("%s's query field list has a '*', which is invalid when %s's field list is specified.",
                  tblType, tblType)
              .build();
        }
      }

      // validate the given field names to make sure there are no duplicates
      ensureNoDuplicateColumnNames(tableFieldNames);

      // CTAS statement has table field list (ex. below), add a project rel to rename the query fields.
      // Ex. CREATE TABLE tblname(col1, medianOfCol2, avgOfCol3) AS
      //        SELECT col1, median(col2), avg(col3) FROM sourcetbl GROUP BY col1 ;
      // Similary for CREATE VIEW.

      return DrillRelOptUtil.createRename(validatedQueryRelNode, tableFieldNames);
    }

    // As the column names of the view are derived from SELECT query, make sure the query has no duplicate column names
    ensureNoDuplicateColumnNames(queryRowType.getFieldNames());

    return validatedQueryRelNode;
  }

  private static void ensureNoDuplicateColumnNames(List<String> fieldNames) throws ValidationException {
    final HashSet<String> fieldHashSet = Sets.newHashSetWithExpectedSize(fieldNames.size());
    for(String field : fieldNames) {
      if (fieldHashSet.contains(field.toLowerCase())) {
        throw new ValidationException(String.format("Duplicate column name [%s]", field));
      }
      fieldHashSet.add(field.toLowerCase());
    }
  }

  /**
   *  Resolve the partition columns specified in "PARTITION BY" clause of CTAS statement.
   *
   *  A partition column is resolved, either (1) the same column appear in the select list of CTAS
   *  or (2) CTAS has a * in select list.
   *
   *  In the second case, a PROJECT with ITEM expression would be created and returned.
   *  Throw validation error if a partition column is not resolved correctly.
   *
   * @param input : the RelNode represents the select statement in CTAS.
   * @param partitionColumns : the list of partition columns.
   * @return : 1) the original RelNode input, if all partition columns are in select list of CTAS
   *           2) a New Project, if a partition column is resolved to * column in select list
   *           3) validation error, if partition column is not resolved.
   */
  public static RelNode qualifyPartitionCol(RelNode input, List<String> partitionColumns) {

    final RelDataType inputRowType = input.getRowType();

    final List<RexNode> colRefStarExprs = Lists.newArrayList();
    final List<String> colRefStarNames = Lists.newArrayList();
    final RexBuilder builder = input.getCluster().getRexBuilder();
    final int originalFieldSize = inputRowType.getFieldCount();

    for (final String col : partitionColumns) {
      final RelDataTypeField field = inputRowType.getField(col, false, false);

      if (field == null) {
        throw UserException.validationError()
            .message("Partition column %s is not in the SELECT list of CTAS!", col)
            .build();
      } else {
        if (field.getName().startsWith(StarColumnHelper.STAR_COLUMN)) {
          colRefStarNames.add(col);

          final List<RexNode> operands = Lists.newArrayList();
          operands.add(new RexInputRef(field.getIndex(), field.getType()));
          operands.add(builder.makeLiteral(col));
          final RexNode item = builder.makeCall(SqlStdOperatorTable.ITEM, operands);
          colRefStarExprs.add(item);
        }
      }
    }

    if (colRefStarExprs.isEmpty()) {
      return input;
    } else {
      final List<String> names =
          new AbstractList<String>() {
            @Override
            public String get(int index) {
              if (index < originalFieldSize) {
                return inputRowType.getFieldNames().get(index);
              } else {
                return colRefStarNames.get(index - originalFieldSize);
              }
            }

            @Override
            public int size() {
              return originalFieldSize + colRefStarExprs.size();
            }
          };

      final List<RexNode> refs =
          new AbstractList<RexNode>() {
            public int size() {
              return originalFieldSize + colRefStarExprs.size();
            }

            public RexNode get(int index) {
              if (index < originalFieldSize) {
                return RexInputRef.of(index, inputRowType.getFieldList());
              } else {
                return colRefStarExprs.get(index - originalFieldSize);
              }
            }
          };

      return RelOptUtil.createProject(input, refs, names, false);
    }
  }

  public static Table getTableFromSchema(AbstractSchema drillSchema, String tblName) {
    try {
      return drillSchema.getTable(tblName);
    } catch (Exception e) {
      // TODO: Move to better exception types.
      throw new DrillRuntimeException(
          String.format("Failure while trying to check if a table or view with given name [%s] already exists " +
              "in schema [%s]: %s", tblName, drillSchema.getFullSchemaName(), e.getMessage()), e);
    }
  }

  public static void unparseSqlNodeList(SqlWriter writer, int leftPrec, int rightPrec, SqlNodeList fieldList) {
    writer.keyword("(");
    fieldList.get(0).unparse(writer, leftPrec, rightPrec);
    for (int i = 1; i<fieldList.size(); i++) {
      writer.keyword(",");
      fieldList.get(i).unparse(writer, leftPrec, rightPrec);
    }
    writer.keyword(")");
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/ViewHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;

import org.apache.calcite.schema.Schema;
import org.apache.calcite.schema.Schema.TableType;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.schema.Table;
import org.apache.calcite.tools.Planner;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.dotdrill.View;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.planner.sql.DirectPlan;
import org.apache.drill.exec.planner.sql.SchemaUtilites;
import org.apache.drill.exec.planner.sql.parser.SqlCreateView;
import org.apache.drill.exec.planner.sql.parser.SqlDropView;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.sql.SqlNode;

public abstract class ViewHandler extends AbstractSqlHandler {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ViewHandler.class);

  protected Planner planner;
  protected QueryContext context;

  public ViewHandler(Planner planner, QueryContext context) {
    this.planner = planner;
    this.context = context;
  }

  /** Handler for Create View DDL command */
  public static class CreateView extends ViewHandler {

    public CreateView(Planner planner, QueryContext context) {
      super(planner, context);
    }

    @Override
    public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
      SqlCreateView createView = unwrap(sqlNode, SqlCreateView.class);

      final String newViewName = createView.getName();

      // Store the viewSql as view def SqlNode is modified as part of the resolving the new table definition below.
      final String viewSql = createView.getQuery().toString();

      final RelNode newViewRelNode =
          SqlHandlerUtil.resolveNewTableRel(true, planner, createView.getFieldNames(), createView.getQuery());

      final SchemaPlus defaultSchema = context.getNewDefaultSchema();
      final AbstractSchema drillSchema = SchemaUtilites.resolveToMutableDrillSchema(defaultSchema, createView.getSchemaPath());

      final String schemaPath = drillSchema.getFullSchemaName();
      final View view = new View(newViewName, viewSql, newViewRelNode.getRowType(),
          SchemaUtilites.getSchemaPathAsList(defaultSchema));

      final Table existingTable = SqlHandlerUtil.getTableFromSchema(drillSchema, newViewName);

      if (existingTable != null) {
        if (existingTable.getJdbcTableType() != Schema.TableType.VIEW) {
          // existing table is not a view
          throw UserException.validationError()
              .message("A non-view table with given name [%s] already exists in schema [%s]",
                  newViewName, schemaPath)
              .build();
        }

        if (existingTable.getJdbcTableType() == Schema.TableType.VIEW && !createView.getReplace()) {
          // existing table is a view and create view has no "REPLACE" clause
          throw UserException.validationError()
              .message("A view with given name [%s] already exists in schema [%s]",
                  newViewName, schemaPath)
              .build();
        }
      }

      final boolean replaced = drillSchema.createView(view);
      final String summary = String.format("View '%s' %s successfully in '%s' schema",
          createView.getName(), replaced ? "replaced" : "created", schemaPath);

      return DirectPlan.createDirectPlan(context, true, summary);
    }
  }

  /** Handler for Drop View DDL command. */
  public static class DropView extends ViewHandler {
    public DropView(QueryContext context) {
      super(null, context);
    }

    @Override
    public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
      SqlDropView dropView = unwrap(sqlNode, SqlDropView.class);
      final String viewToDrop = dropView.getName();
      final AbstractSchema drillSchema =
          SchemaUtilites.resolveToMutableDrillSchema(context.getNewDefaultSchema(), dropView.getSchemaPath());

      final String schemaPath = drillSchema.getFullSchemaName();

      final Table existingTable = SqlHandlerUtil.getTableFromSchema(drillSchema, viewToDrop);
      if (existingTable != null && existingTable.getJdbcTableType() != Schema.TableType.VIEW) {
        throw UserException.validationError()
            .message("[%s] is not a VIEW in schema [%s]", viewToDrop, schemaPath)
            .build();
      } else if (existingTable == null) {
        throw UserException.validationError()
            .message("Unknown view [%s] in schema [%s].", viewToDrop, schemaPath)
            .build();
      }

      drillSchema.dropView(viewToDrop);

      return DirectPlan.createDirectPlan(context, true,
          String.format("View [%s] deleted successfully from schema [%s].", viewToDrop, schemaPath));
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/parser/SqlCreateView.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.parser;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import org.apache.drill.exec.planner.sql.handlers.AbstractSqlHandler;
import org.apache.drill.exec.planner.sql.handlers.SqlHandlerConfig;
import org.apache.drill.exec.planner.sql.handlers.SqlHandlerUtil;
import org.apache.drill.exec.planner.sql.handlers.ViewHandler;
import org.apache.calcite.sql.SqlCall;
import org.apache.calcite.sql.SqlIdentifier;
import org.apache.calcite.sql.SqlKind;
import org.apache.calcite.sql.SqlLiteral;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.SqlNodeList;
import org.apache.calcite.sql.SqlOperator;
import org.apache.calcite.sql.SqlSpecialOperator;
import org.apache.calcite.sql.SqlWriter;
import org.apache.calcite.sql.parser.SqlParserPos;

import java.util.List;

public class SqlCreateView extends DrillSqlCall {
  public static final SqlSpecialOperator OPERATOR = new SqlSpecialOperator("CREATE_VIEW", SqlKind.OTHER) {
    @Override
    public SqlCall createCall(SqlLiteral functionQualifier, SqlParserPos pos, SqlNode... operands) {
      return new SqlCreateView(pos, (SqlIdentifier) operands[0], (SqlNodeList) operands[1], operands[2], (SqlLiteral) operands[3]);
    }
  };

  private SqlIdentifier viewName;
  private SqlNodeList fieldList;
  private SqlNode query;
  private boolean replaceView;

  public SqlCreateView(SqlParserPos pos, SqlIdentifier viewName, SqlNodeList fieldList,
      SqlNode query, SqlLiteral replaceView) {
    this(pos, viewName, fieldList, query, replaceView.booleanValue());
  }

  public SqlCreateView(SqlParserPos pos, SqlIdentifier viewName, SqlNodeList fieldList,
                       SqlNode query, boolean replaceView) {
    super(pos);
    this.viewName = viewName;
    this.query = query;
    this.replaceView = replaceView;
    this.fieldList = fieldList;
  }

  @Override
  public SqlOperator getOperator() {
    return OPERATOR;
  }

  @Override
  public List<SqlNode> getOperandList() {
    List<SqlNode> ops = Lists.newArrayList();
    ops.add(viewName);
    ops.add(fieldList);
    ops.add(query);
    ops.add(SqlLiteral.createBoolean(replaceView, SqlParserPos.ZERO));
    return ops;
  }

  @Override
  public void unparse(SqlWriter writer, int leftPrec, int rightPrec) {
    writer.keyword("CREATE");
    if (replaceView) {
      writer.keyword("OR");
      writer.keyword("REPLACE");
    }
    writer.keyword("VIEW");
    viewName.unparse(writer, leftPrec, rightPrec);
    if (fieldList.size() > 0) {
      SqlHandlerUtil.unparseSqlNodeList(writer, leftPrec, rightPrec, fieldList);
    }
    writer.keyword("AS");
    query.unparse(writer, leftPrec, rightPrec);
  }

  @Override
  public AbstractSqlHandler getSqlHandler(SqlHandlerConfig config) {
    return new ViewHandler.CreateView(config.getPlanner(), config.getContext());
  }

  public List<String> getSchemaPath() {
    if (viewName.isSimple()) {
      return ImmutableList.of();
    }

    return viewName.names.subList(0, viewName.names.size()-1);
  }

  public String getName() {
    if (viewName.isSimple()) {
      return viewName.getSimple();
    }

    return viewName.names.get(viewName.names.size() - 1);
  }

  public List<String> getFieldNames() {
    List<String> fieldNames = Lists.newArrayList();
    for (SqlNode node : fieldList.getList()) {
      fieldNames.add(node.toString());
    }
    return fieldNames;
  }

  public SqlNode getQuery() { return query; }
  public boolean getReplace() { return replaceView; }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/parser/SqlDropView.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.parser;

import java.util.Collections;
import java.util.List;

import org.apache.calcite.tools.Planner;

import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.planner.sql.handlers.AbstractSqlHandler;
import org.apache.drill.exec.planner.sql.handlers.SqlHandlerConfig;
import org.apache.drill.exec.planner.sql.handlers.ViewHandler.DropView;
import org.apache.calcite.plan.hep.HepPlanner;
import org.apache.calcite.sql.SqlCall;
import org.apache.calcite.sql.SqlIdentifier;
import org.apache.calcite.sql.SqlKind;
import org.apache.calcite.sql.SqlLiteral;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.SqlOperator;
import org.apache.calcite.sql.SqlSpecialOperator;
import org.apache.calcite.sql.SqlWriter;
import org.apache.calcite.sql.parser.SqlParserPos;

import com.google.common.collect.ImmutableList;

public class SqlDropView extends DrillSqlCall {
  public static final SqlSpecialOperator OPERATOR = new SqlSpecialOperator("DROP_VIEW", SqlKind.OTHER) {
    @Override
    public SqlCall createCall(SqlLiteral functionQualifier, SqlParserPos pos, SqlNode... operands) {
      return new SqlDropView(pos, (SqlIdentifier) operands[0]);
    }
  };

  private SqlIdentifier viewName;

  public SqlDropView(SqlParserPos pos, SqlIdentifier viewName) {
    super(pos);
    this.viewName = viewName;
  }

  @Override
  public SqlOperator getOperator() {
    return OPERATOR;
  }

  @Override
  public List<SqlNode> getOperandList() {
    return Collections.singletonList((SqlNode)viewName);
  }

  @Override
  public void unparse(SqlWriter writer, int leftPrec, int rightPrec) {
    writer.keyword("DROP");
    writer.keyword("VIEW");
    viewName.unparse(writer, leftPrec, rightPrec);
  }

  @Override
  public AbstractSqlHandler getSqlHandler(SqlHandlerConfig config) {
    return new DropView(config.getContext());
  }

  public List<String> getSchemaPath() {
    if (viewName.isSimple()) {
      return ImmutableList.of();
    }

    return viewName.names.subList(0, viewName.names.size()-1);
  }

  public String getName() {
    if (viewName.isSimple()) {
      return viewName.getSimple();
    }

    return viewName.names.get(viewName.names.size() - 1);
  }

}
