Refactoring Types: ['Extract Method']
nner/Planner.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner;

import com.carrotsearch.hppc.IntObjectOpenHashMap;
import com.carrotsearch.hppc.procedures.ObjectProcedure;
import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import io.crate.analyze.*;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.analyze.relations.TableRelation;
import io.crate.analyze.where.DocKeys;
import io.crate.core.collections.TreeMapBuilder;
import io.crate.exceptions.UnhandledServerException;
import io.crate.metadata.*;
import io.crate.metadata.doc.DocSysColumns;
import io.crate.metadata.table.TableInfo;
import io.crate.operation.aggregation.impl.CountAggregation;
import io.crate.planner.consumer.ConsumerContext;
import io.crate.planner.consumer.ConsumingPlanner;
import io.crate.planner.consumer.UpdateConsumer;
import io.crate.planner.node.ddl.*;
import io.crate.planner.node.dml.ESDeleteByQueryNode;
import io.crate.planner.node.dml.ESDeleteNode;
import io.crate.planner.node.dml.SymbolBasedUpsertByIdNode;
import io.crate.planner.node.dml.Upsert;
import io.crate.planner.node.dql.CollectAndMerge;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.FileUriCollectNode;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.node.management.KillPlan;
import io.crate.planner.projection.Projection;
import io.crate.planner.projection.SourceIndexWriterProjection;
import io.crate.planner.projection.WriterProjection;
import io.crate.planner.symbol.InputColumn;
import io.crate.planner.symbol.Reference;
import io.crate.planner.symbol.Symbol;
import io.crate.types.DataType;
import io.crate.types.DataTypes;
import org.apache.lucene.util.BytesRef;
import org.elasticsearch.cluster.ClusterService;
import org.elasticsearch.cluster.node.DiscoveryNodes;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.inject.Singleton;
import org.elasticsearch.common.settings.ImmutableSettings;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.shard.ShardId;

import javax.annotation.Nullable;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

import static com.google.common.base.MoreObjects.firstNonNull;

@Singleton
public class Planner extends AnalyzedStatementVisitor<Planner.Context, Plan> {

    private final ConsumingPlanner consumingPlanner;
    private final ClusterService clusterService;
    private UpdateConsumer updateConsumer;

    public static class Context {

        private final IntObjectOpenHashMap<ShardId> jobSearchContextIdToShard = new IntObjectOpenHashMap<>();
        private final IntObjectOpenHashMap<String> jobSearchContextIdToNode = new IntObjectOpenHashMap<>();
        private final ClusterService clusterService;
        private int jobSearchContextIdBaseSeq = 0;
        private int executionNodeId = 0;

        public Context(ClusterService clusterService) {
            this.clusterService = clusterService;
        }

        public ClusterService clusterService() {
            return clusterService;
        }

        /**
         * Increase current {@link #jobSearchContextIdBaseSeq} by number of shards affected by given
         * <code>routing</code> parameter and register a {@link org.elasticsearch.index.shard.ShardId}
         * under each incremented jobSearchContextId.
         * The current {@link #jobSearchContextIdBaseSeq} is set on the {@link io.crate.metadata.Routing} instance,
         * in order to be able to re-generate jobSearchContextId's for every shard in a deterministic way.
         *
         * Skip generating jobSearchContextId's if {@link io.crate.metadata.Routing#jobSearchContextIdBase} is already
         * set on the given <code>routing</code>.
         */
        public void allocateJobSearchContextIds(Routing routing) {
            if (routing.jobSearchContextIdBase() > -1 || routing.hasLocations() == false
                    || routing.numShards() == 0) {
                return;
            }
            int jobSearchContextId = jobSearchContextIdBaseSeq;
            jobSearchContextIdBaseSeq += routing.numShards();
            routing.jobSearchContextIdBase(jobSearchContextId);
            for (Map.Entry<String, Map<String, List<Integer>>> nodeEntry : routing.locations().entrySet()) {
                String nodeId = nodeEntry.getKey();
                Map<String, List<Integer>> nodeRouting = nodeEntry.getValue();
                if (nodeRouting != null) {
                    for (Map.Entry<String, List<Integer>> entry : nodeRouting.entrySet()) {
                        for (Integer shardId : entry.getValue()) {
                            jobSearchContextIdToShard.put(jobSearchContextId, new ShardId(entry.getKey(), shardId));
                            jobSearchContextIdToNode.put(jobSearchContextId, nodeId);
                            jobSearchContextId++;
                        }
                    }
                }
            }
        }

        @Nullable
        public ShardId shardId(int jobSearchContextId) {
            return jobSearchContextIdToShard.get(jobSearchContextId);
        }

        public IntObjectOpenHashMap<ShardId> jobSearchContextIdToShard() {
            return jobSearchContextIdToShard;
        }

        @Nullable
        public String nodeId(int jobSearchContextId) {
            return jobSearchContextIdToNode.get(jobSearchContextId);
        }

        public IntObjectOpenHashMap<String> jobSearchContextIdToNode() {
            return jobSearchContextIdToNode;
        }

        public int nextExecutionNodeId() {
            return executionNodeId++;
        }
    }

    @Inject
    public Planner(ClusterService clusterService, ConsumingPlanner consumingPlanner, UpdateConsumer updateConsumer) {
        this.clusterService = clusterService;
        this.updateConsumer = updateConsumer;
        this.consumingPlanner = consumingPlanner;
    }

    /**
     * dispatch plan creation based on analysis type
     *
     * @param analysis analysis to create plan from
     * @return plan
     */
    public Plan plan(Analysis analysis) {
        AnalyzedStatement analyzedStatement = analysis.analyzedStatement();
        return process(analyzedStatement, new Context(clusterService));
    }

    @Override
    protected Plan visitAnalyzedStatement(AnalyzedStatement analyzedStatement, Context context) {
        throw new UnsupportedOperationException(String.format("AnalyzedStatement \"%s\" not supported.", analyzedStatement));
    }

    @Override
    protected Plan visitSelectStatement(SelectAnalyzedStatement statement, Context context) {
        return consumingPlanner.plan(statement.relation(), context);
    }

    @Override
    protected Plan visitInsertFromValuesStatement(InsertFromValuesAnalyzedStatement statement, Context context) {
        Preconditions.checkState(!statement.sourceMaps().isEmpty(), "no values given");
        return processInsertStatement(statement, context);
    }

    @Override
    protected Plan visitInsertFromSubQueryStatement(InsertFromSubQueryAnalyzedStatement statement, Context context) {
        return consumingPlanner.plan(statement, context);
    }

    @Override
    protected Plan visitUpdateStatement(UpdateAnalyzedStatement statement, Context context) {
        ConsumerContext consumerContext = new ConsumerContext(statement, context);
        if (updateConsumer.consume(statement, consumerContext)) {
            return ((PlannedAnalyzedRelation) consumerContext.rootRelation()).plan();
        }
        throw new IllegalArgumentException("Couldn't plan Update statement");
    }

    @Override
    protected Plan visitDeleteStatement(DeleteAnalyzedStatement analyzedStatement, Context context) {
        IterablePlan plan = new IterablePlan();
        TableRelation tableRelation = analyzedStatement.analyzedRelation();
        List<WhereClause> whereClauses = new ArrayList<>(analyzedStatement.whereClauses().size());
        List<DocKeys.DocKey> docKeys = new ArrayList<>(analyzedStatement.whereClauses().size());
        for (WhereClause whereClause : analyzedStatement.whereClauses()) {
            if (whereClause.noMatch()) {
                continue;
            }
            if (whereClause.docKeys().isPresent() && whereClause.docKeys().get().size() == 1) {
                docKeys.add(whereClause.docKeys().get().getOnlyKey());
            } else if (!whereClause.noMatch()) {
                whereClauses.add(whereClause);
            }
        }
        if (!docKeys.isEmpty()) {
            plan.add(new ESDeleteNode(context.nextExecutionNodeId(), tableRelation.tableInfo(), docKeys));
        } else if (!whereClauses.isEmpty()) {
            createESDeleteByQueryNode(tableRelation.tableInfo(), whereClauses, plan, context);
        }

        if (plan.isEmpty()) {
            return NoopPlan.INSTANCE;
        }
        return plan;
    }

    @Override
    protected Plan visitCopyStatement(final CopyAnalyzedStatement analysis, Context context) {
        switch (analysis.mode()) {
            case FROM:
                return copyFromPlan(analysis, context);
            case TO:
                return copyToPlan(analysis, context);
            default:
                throw new UnsupportedOperationException("mode not supported: " + analysis.mode());
        }
    }

    private Plan copyToPlan(CopyAnalyzedStatement analysis, Context context) {
        TableInfo tableInfo = analysis.table();
        WriterProjection projection = new WriterProjection();
        projection.uri(analysis.uri());
        projection.isDirectoryUri(analysis.directoryUri());
        projection.settings(analysis.settings());

        List<Symbol> outputs;
        if (analysis.selectedColumns() != null && !analysis.selectedColumns().isEmpty()) {
            outputs = new ArrayList<>(analysis.selectedColumns().size());
            List<Symbol> columnSymbols = new ArrayList<>(analysis.selectedColumns().size());
            for (int i = 0; i < analysis.selectedColumns().size(); i++) {
                outputs.add(DocReferenceConverter.convertIfPossible(analysis.selectedColumns().get(i), analysis.table()));
                columnSymbols.add(new InputColumn(i, null));
            }
            projection.inputs(columnSymbols);
        } else {
            Reference sourceRef;
            if (analysis.table().isPartitioned() && analysis.partitionIdent() == null) {
                // table is partitioned, insert partitioned columns into the output
                sourceRef = new Reference(analysis.table().getReferenceInfo(DocSysColumns.DOC));
                Map<ColumnIdent, Symbol> overwrites = new HashMap<>();
                for (ReferenceInfo referenceInfo : analysis.table().partitionedByColumns()) {
                    overwrites.put(referenceInfo.ident().columnIdent(), new Reference(referenceInfo));
                }
                projection.overwrites(overwrites);
            } else {
                sourceRef = new Reference(analysis.table().getReferenceInfo(DocSysColumns.RAW));
            }
            outputs = ImmutableList.<Symbol>of(sourceRef);
        }
        CollectNode collectNode = PlanNodeBuilder.collect(
                tableInfo,
                context,
                WhereClause.MATCH_ALL,
                outputs,
                ImmutableList.<Projection>of(projection),
                analysis.partitionIdent()
        );

        MergeNode mergeNode = PlanNodeBuilder.localMerge(
                ImmutableList.<Projection>of(CountAggregation.PARTIAL_COUNT_AGGREGATION_PROJECTION), collectNode, context);
        return new CollectAndMerge(collectNode, mergeNode);
    }

    private Plan copyFromPlan(CopyAnalyzedStatement analysis, Context context) {
        /**
         * copy from has two "modes":
         *
         * 1: non-partitioned tables or partitioned tables with partition ident --> import into single es index
         *    -> collect raw source and import as is
         *
         * 2: partitioned table without partition ident
         *    -> collect document and partition by values
         *    -> exclude partitioned by columns from document
         *    -> insert into es index (partition determined by partition by value)
         */

        TableInfo table = analysis.table();
        int clusteredByPrimaryKeyIdx = table.primaryKey().indexOf(analysis.table().clusteredBy());
        List<String> partitionedByNames;
        String partitionIdent = null;

        List<BytesRef> partitionValues;
        if (analysis.partitionIdent() == null) {

            if (table.isPartitioned()) {
                partitionedByNames = Lists.newArrayList(
                        Lists.transform(table.partitionedBy(), ColumnIdent.GET_FQN_NAME_FUNCTION));
            } else {
                partitionedByNames = Collections.emptyList();
            }
            partitionValues = ImmutableList.of();
        } else {
            assert table.isPartitioned() : "table must be partitioned if partitionIdent is set";
            // partitionIdent is present -> possible to index raw source into concrete es index
            PartitionName partitionName = PartitionName.fromPartitionIdent(table.ident().schema(), table.ident().name(), analysis.partitionIdent());
            partitionValues = partitionName.values();

            partitionIdent = partitionName.ident();
            partitionedByNames = Collections.emptyList();
        }

        SourceIndexWriterProjection sourceIndexWriterProjection = new SourceIndexWriterProjection(
                table.ident(),
                partitionIdent,
                new Reference(table.getReferenceInfo(DocSysColumns.RAW)),
                table.primaryKey(),
                table.partitionedBy(),
                partitionValues,
                table.clusteredBy(),
                clusteredByPrimaryKeyIdx,
                analysis.settings(),
                null,
                partitionedByNames.size() > 0 ? partitionedByNames.toArray(new String[partitionedByNames.size()]) : null,
                table.isPartitioned() // autoCreateIndices
        );
        List<Projection> projections = Arrays.<Projection>asList(sourceIndexWriterProjection);
        partitionedByNames.removeAll(Lists.transform(table.primaryKey(), ColumnIdent.GET_FQN_NAME_FUNCTION));
        int referencesSize = table.primaryKey().size() + partitionedByNames.size() + 1;
        referencesSize = clusteredByPrimaryKeyIdx == -1 ? referencesSize + 1 : referencesSize;

        List<Symbol> toCollect = new ArrayList<>(referencesSize);
        // add primaryKey columns
        for (ColumnIdent primaryKey : table.primaryKey()) {
            toCollect.add(new Reference(table.getReferenceInfo(primaryKey)));
        }

        // add partitioned columns (if not part of primaryKey)
        for (String partitionedColumn : partitionedByNames) {
            toCollect.add(
                    new Reference(table.getReferenceInfo(ColumnIdent.fromPath(partitionedColumn)))
            );
        }
        // add clusteredBy column (if not part of primaryKey)
        if (clusteredByPrimaryKeyIdx == -1) {
            toCollect.add(
                    new Reference(table.getReferenceInfo(table.clusteredBy())));
        }
        // finally add _raw or _doc
        if (table.isPartitioned() && analysis.partitionIdent() == null) {
            toCollect.add(new Reference(table.getReferenceInfo(DocSysColumns.DOC)));
        } else {
            toCollect.add(new Reference(table.getReferenceInfo(DocSysColumns.RAW)));
        }

        DiscoveryNodes allNodes = clusterService.state().nodes();
        FileUriCollectNode collectNode = new FileUriCollectNode(
                context.nextExecutionNodeId(),
                "copyFrom",
                generateRouting(allNodes, analysis.settings().getAsInt("num_readers", allNodes.getSize())),
                analysis.uri(),
                toCollect,
                projections,
                analysis.settings().get("compression", null),
                analysis.settings().getAsBoolean("shared", null)
        );
        PlanNodeBuilder.setOutputTypes(collectNode);

        return new CollectAndMerge(collectNode, PlanNodeBuilder.localMerge(
                ImmutableList.<Projection>of(CountAggregation.PARTIAL_COUNT_AGGREGATION_PROJECTION), collectNode, context));
    }

    private Routing generateRouting(DiscoveryNodes allNodes, int maxNodes) {
        final AtomicInteger counter = new AtomicInteger(maxNodes);
        final Map<String, Map<String, List<Integer>>> locations = new TreeMap<>();
        allNodes.dataNodes().keys().forEach(new ObjectProcedure<String>() {
            @Override
            public void apply(String value) {
                if (counter.getAndDecrement() > 0) {
                    locations.put(value, TreeMapBuilder.<String, List<Integer>>newMapBuilder().map());
                }
            }
        });
        return new Routing(locations);
    }

    @Override
    protected Plan visitDDLAnalyzedStatement(AbstractDDLAnalyzedStatement statement, Context context) {
        return new IterablePlan(new GenericDDLNode(statement));
    }

    @Override
    public Plan visitDropBlobTableStatement(DropBlobTableAnalyzedStatement analysis, Context context) {
        if (analysis.noop()) {
            return NoopPlan.INSTANCE;
        }
        return visitDDLAnalyzedStatement(analysis, context);
    }

    @Override
    protected Plan visitDropTableStatement(DropTableAnalyzedStatement analysis, Context context) {
        if (analysis.noop()) {
            return NoopPlan.INSTANCE;
        }
        return new IterablePlan(new DropTableNode(analysis.table()));
    }

    @Override
    protected Plan visitCreateTableStatement(CreateTableAnalyzedStatement analysis, Context context) {
        if (analysis.noOp()) {
            return NoopPlan.INSTANCE;
        }
        TableIdent tableIdent = analysis.tableIdent();

        CreateTableNode createTableNode;
        if (analysis.isPartitioned()) {
            createTableNode = CreateTableNode.createPartitionedTableNode(
                    tableIdent,
                    analysis.ifNotExists(),
                    analysis.tableParameter().settings().getByPrefix("index."),
                    analysis.mapping(),
                    analysis.templateName(),
                    analysis.templatePrefix()
            );
        } else {
            createTableNode = CreateTableNode.createTableNode(
                    tableIdent,
                    analysis.ifNotExists(),
                    analysis.tableParameter().settings(),
                    analysis.mapping()
            );
        }
        return new IterablePlan(createTableNode);
    }

    @Override
    protected Plan visitCreateAnalyzerStatement(CreateAnalyzerAnalyzedStatement analysis, Context context) {
        Settings analyzerSettings;
        try {
            analyzerSettings = analysis.buildSettings();
        } catch (IOException ioe) {
            throw new UnhandledServerException("Could not build analyzer Settings", ioe);
        }

        ESClusterUpdateSettingsNode node = new ESClusterUpdateSettingsNode(analyzerSettings);
        return new IterablePlan(node);
    }

    @Override
    public Plan visitSetStatement(SetAnalyzedStatement analysis, Context context) {
        ESClusterUpdateSettingsNode node = null;
        if (analysis.isReset()) {
            // always reset persistent AND transient settings
            if (analysis.settingsToRemove() != null) {
                node = new ESClusterUpdateSettingsNode(analysis.settingsToRemove(), analysis.settingsToRemove());
            }
        } else {
            if (analysis.settings() != null) {
                if (analysis.isPersistent()) {
                    node = new ESClusterUpdateSettingsNode(analysis.settings());
                } else {
                    node = new ESClusterUpdateSettingsNode(ImmutableSettings.EMPTY, analysis.settings());
                }
            }
        }
        return node != null ? new IterablePlan(node) : NoopPlan.INSTANCE;
    }

    @Override
    public Plan visitKillAnalyzedStatement(KillAnalyzedStatement analysis, Context context) {
        return KillPlan.INSTANCE;
    }

    private void createESDeleteByQueryNode(TableInfo tableInfo,
                                           List<WhereClause> whereClauses,
                                           IterablePlan plan,
                                           Context context) {

        List<String[]> indicesList = new ArrayList<>(whereClauses.size());
        for (WhereClause whereClause : whereClauses) {
            String[] indices = indices(tableInfo, whereClauses.get(0));
            if (indices.length > 0) {
                if (!whereClause.hasQuery() && tableInfo.isPartitioned()) {
                    plan.add(new ESDeletePartitionNode(indices));
                } else {
                    indicesList.add(indices);
                }
            }
        }
        // TODO: if we allow queries like 'partitionColumn=X or column=Y' which is currently
        // forbidden through analysis, we must issue deleteByQuery request in addition
        // to above deleteIndex request(s)
        if (!indicesList.isEmpty()) {
            plan.add(new ESDeleteByQueryNode(context.nextExecutionNodeId(), indicesList, whereClauses));
        }
    }

    private Upsert processInsertStatement(InsertFromValuesAnalyzedStatement analysis, Context context) {
        String[] onDuplicateKeyAssignmentsColumns = null;
        if (analysis.onDuplicateKeyAssignmentsColumns().size() > 0) {
            onDuplicateKeyAssignmentsColumns = analysis.onDuplicateKeyAssignmentsColumns().get(0);
        }
        SymbolBasedUpsertByIdNode upsertByIdNode = new SymbolBasedUpsertByIdNode(
                context.nextExecutionNodeId(),
                analysis.tableInfo().isPartitioned(),
                analysis.isBulkRequest(),
                onDuplicateKeyAssignmentsColumns,
                analysis.columns().toArray(new Reference[analysis.columns().size()])
        );
        if (analysis.tableInfo().isPartitioned()) {
            List<String> partitions = analysis.generatePartitions();
            String[] indices = partitions.toArray(new String[partitions.size()]);
            for (int i = 0; i < indices.length; i++) {
                Symbol[] onDuplicateKeyAssignments = null;
                if (analysis.onDuplicateKeyAssignmentsColumns().size() > i) {
                    onDuplicateKeyAssignments = analysis.onDuplicateKeyAssignments().get(i);
                }
                upsertByIdNode.add(
                        indices[i],
                        analysis.ids().get(i),
                        analysis.routingValues().get(i),
                        onDuplicateKeyAssignments,
                        null,
                        analysis.sourceMaps().get(i));
            }
        } else {
            for (int i = 0; i < analysis.ids().size(); i++) {
                Symbol[] onDuplicateKeyAssignments = null;
                if (analysis.onDuplicateKeyAssignments().size() > i) {
                    onDuplicateKeyAssignments = analysis.onDuplicateKeyAssignments().get(i);
                }
                upsertByIdNode.add(
                        analysis.tableInfo().ident().esName(),
                        analysis.ids().get(i),
                        analysis.routingValues().get(i),
                        onDuplicateKeyAssignments,
                        null,
                        analysis.sourceMaps().get(i));
            }
        }

        return new Upsert(ImmutableList.<Plan>of(new IterablePlan(upsertByIdNode)));
    }

    static List<DataType> extractDataTypes(List<Projection> projections, @Nullable List<DataType> inputTypes) {
        if (projections.size() == 0) {
            return inputTypes;
        }
        int projectionIdx = projections.size() - 1;
        Projection lastProjection = projections.get(projectionIdx);
        List<DataType> types = new ArrayList<>(lastProjection.outputs().size());
        List<DataType> dataTypes = firstNonNull(inputTypes, ImmutableList.<DataType>of());

        for (int c = 0; c < lastProjection.outputs().size(); c++) {
            types.add(resolveType(projections, projectionIdx, c, dataTypes));
        }
        return types;
    }

    private static DataType resolveType(List<Projection> projections, int projectionIdx, int columnIdx, List<DataType> inputTypes) {
        Projection projection = projections.get(projectionIdx);
        Symbol symbol = projection.outputs().get(columnIdx);
        DataType type = symbol.valueType();
        if (type == null || (type.equals(DataTypes.UNDEFINED) && symbol instanceof InputColumn)) {
            if (projectionIdx > 0) {
                if (symbol instanceof InputColumn) {
                    columnIdx = ((InputColumn) symbol).index();
                }
                return resolveType(projections, projectionIdx - 1, columnIdx, inputTypes);
            } else {
                assert symbol instanceof InputColumn; // otherwise type shouldn't be null
                return inputTypes.get(((InputColumn) symbol).index());
            }
        }

        return type;
    }


    /**
     * return the ES index names the query should go to
     */
    public static String[] indices(TableInfo tableInfo, WhereClause whereClause) {
        String[] indices;

        if (whereClause.noMatch()) {
            indices = org.elasticsearch.common.Strings.EMPTY_ARRAY;
        } else if (!tableInfo.isPartitioned()) {
            // table name for non-partitioned tables
            indices = new String[]{tableInfo.ident().esName()};
        } else if (whereClause.partitions().isEmpty()) {
            if (whereClause.noMatch()) {
                return new String[0];
            }

            // all partitions
            indices = new String[tableInfo.partitions().size()];
            int i = 0;
            for (PartitionName partitionName: tableInfo.partitions()) {
                indices[i] = partitionName.stringValue();
                i++;
            }
        } else {
            indices = whereClause.partitions().toArray(new String[whereClause.partitions().size()]);
        }
        return indices;
    }
}



File: sql/src/main/java/io/crate/planner/consumer/Consumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import io.crate.analyze.relations.AnalyzedRelation;

public interface Consumer {

    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context);
}


File: sql/src/main/java/io/crate/planner/consumer/ConsumerContext.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;


import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.exceptions.ValidationException;
import io.crate.planner.Planner;
import org.elasticsearch.common.Nullable;

public class ConsumerContext {

    private AnalyzedRelation rootRelation;
    private ValidationException validationException;
    private Planner.Context plannerContext;

    public ConsumerContext(AnalyzedRelation rootRelation, Planner.Context plannerContext) {
        this.rootRelation = rootRelation;
        this.plannerContext = plannerContext;
    }

    public void rootRelation(AnalyzedRelation relation) {
        this.rootRelation = relation;
    }

    public AnalyzedRelation rootRelation() {
        return rootRelation;
    }

    public void validationException(ValidationException validationException){
        this.validationException = validationException;
    }

    @Nullable
    public ValidationException validationException(){
        return validationException;
    }

    public Planner.Context plannerContext() {
        return plannerContext;
    }
}


File: sql/src/main/java/io/crate/planner/consumer/ConsumingPlanner.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.exceptions.ValidationException;
import io.crate.planner.Plan;
import io.crate.planner.Planner;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.inject.Singleton;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.List;

@Singleton
public class ConsumingPlanner {

    private final List<Consumer> consumers = new ArrayList<>();

    @Inject
    public ConsumingPlanner() {
        consumers.add(new NonDistributedGroupByConsumer());
        consumers.add(new ReduceOnCollectorGroupByConsumer());
        consumers.add(new DistributedGroupByConsumer());
        consumers.add(new CountConsumer());
        consumers.add(new GlobalAggregateConsumer());
        consumers.add(new ESGetConsumer());
        consumers.add(new QueryThenFetchConsumer());
        consumers.add(new InsertFromSubQueryConsumer());
        consumers.add(new QueryAndFetchConsumer());
    }

    @Nullable
    public Plan plan(AnalyzedRelation rootRelation, Planner.Context plannerContext) {
        ConsumerContext consumerContext = new ConsumerContext(rootRelation, plannerContext);
        for (int i = 0; i < consumers.size(); i++) {
            Consumer consumer = consumers.get(i);
            if (consumer.consume(consumerContext.rootRelation(), consumerContext)) {
                if (consumerContext.rootRelation() instanceof PlannedAnalyzedRelation) {
                    Plan plan = ((PlannedAnalyzedRelation) consumerContext.rootRelation()).plan();
                    assert plan != null;
                    return plan;
                } else {
                    i = 0;
                }
            }
        }
        ValidationException validationException = consumerContext.validationException();
        if (validationException != null) {
            throw validationException;
        }
        return null;
    }
}


File: sql/src/main/java/io/crate/planner/consumer/CountConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import io.crate.analyze.QueriedTable;
import io.crate.analyze.QuerySpec;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.exceptions.VersionInvalidException;
import io.crate.metadata.Routing;
import io.crate.metadata.table.TableInfo;
import io.crate.operation.aggregation.impl.CountAggregation;
import io.crate.planner.Planner;
import io.crate.planner.node.NoopPlannedAnalyzedRelation;
import io.crate.planner.node.dql.CountNode;
import io.crate.planner.node.dql.CountPlan;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.projection.Projection;
import io.crate.planner.symbol.Function;
import io.crate.planner.symbol.Symbol;
import io.crate.types.DataType;
import io.crate.types.DataTypes;

import java.util.Collections;
import java.util.List;

import static com.google.common.base.MoreObjects.firstNonNull;

public class CountConsumer implements Consumer {

    private static final Visitor VISITOR = new Visitor();

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        AnalyzedRelation analyzedRelation = VISITOR.process(rootRelation, context);
        if (analyzedRelation != null) {
            context.rootRelation(analyzedRelation);
            return true;
        }
        return false;
    }

    private static class Visitor extends AnalyzedRelationVisitor<ConsumerContext, PlannedAnalyzedRelation> {

        @Override
        public PlannedAnalyzedRelation visitQueriedTable(QueriedTable table, ConsumerContext context) {
            QuerySpec querySpec = table.querySpec();
            if (!querySpec.hasAggregates() || querySpec.groupBy()!=null) {
                return null;
            }
            TableInfo tableInfo = table.tableRelation().tableInfo();
            if (tableInfo.schemaInfo().systemSchema()) {
                return null;
            }
            if (!hasOnlyGlobalCount(querySpec.outputs())) {
                return null;
            }
            if(querySpec.where().hasVersions()){
                context.validationException(new VersionInvalidException());
                return null;
            }

            if (firstNonNull(querySpec.limit(), 1) < 1 ||
                    querySpec.offset() > 0){
                return new NoopPlannedAnalyzedRelation(table);
            }

            Routing routing = tableInfo.getRouting(querySpec.where(), null);
            Planner.Context plannerContext = context.plannerContext();
            CountNode countNode = new CountNode(plannerContext.nextExecutionNodeId(), routing, querySpec.where());
            MergeNode mergeNode = new MergeNode(
                    plannerContext.nextExecutionNodeId(),
                    "count-merge",
                    countNode.executionNodes().size());
            mergeNode.inputTypes(Collections.<DataType>singletonList(DataTypes.LONG));
            mergeNode.projections(Collections.<Projection>singletonList(
                    CountAggregation.PARTIAL_COUNT_AGGREGATION_PROJECTION));
            return new CountPlan(countNode, mergeNode);
        }

        @Override
        protected PlannedAnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, ConsumerContext context) {
            return null;
        }

        private boolean hasOnlyGlobalCount(List<Symbol> symbols) {
            if (symbols.size() != 1) {
                return false;
            }
            Symbol symbol = symbols.get(0);
            if (!(symbol instanceof Function)) {
                return false;
            }
            Function function = (Function) symbol;
            return function.info().equals(CountAggregation.COUNT_STAR_FUNCTION);
        }
    }
}


File: sql/src/main/java/io/crate/planner/consumer/DistributedGroupByConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import com.google.common.base.MoreObjects;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import io.crate.Constants;
import io.crate.analyze.HavingClause;
import io.crate.analyze.InsertFromSubQueryAnalyzedStatement;
import io.crate.analyze.OrderBy;
import io.crate.analyze.QueriedTable;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.exceptions.VersionInvalidException;
import io.crate.metadata.Routing;
import io.crate.metadata.table.TableInfo;
import io.crate.planner.PlanNodeBuilder;
import io.crate.planner.node.NoopPlannedAnalyzedRelation;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.DistributedGroupBy;
import io.crate.planner.node.dql.GroupByConsumer;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.projection.GroupProjection;
import io.crate.planner.projection.Projection;
import io.crate.planner.projection.TopNProjection;
import io.crate.planner.projection.builder.ProjectionBuilder;
import io.crate.planner.projection.builder.SplitPoints;
import io.crate.planner.symbol.Aggregation;
import io.crate.planner.symbol.Symbol;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;

public class DistributedGroupByConsumer implements Consumer {

    private static final Visitor VISITOR = new Visitor();

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        Context ctx = new Context(context);
        context.rootRelation(VISITOR.process(context.rootRelation(), ctx));
        return ctx.result;
    }

    private static class Context {
        ConsumerContext consumerContext;
        boolean result = false;

        public Context(ConsumerContext context) {
            this.consumerContext = context;
        }
    }

    private static class Visitor extends AnalyzedRelationVisitor<Context, AnalyzedRelation> {

        @Override
        public AnalyzedRelation visitQueriedTable(QueriedTable table, Context context) {
            List<Symbol> groupBy = table.querySpec().groupBy();
            if (groupBy == null) {
                return table;
            }

            TableInfo tableInfo = table.tableRelation().tableInfo();
            if(table.querySpec().where().hasVersions()){
                context.consumerContext.validationException(new VersionInvalidException());
                return table;
            }

            Routing routing = tableInfo.getRouting(table.querySpec().where(), null);

            GroupByConsumer.validateGroupBySymbols(table.tableRelation(), table.querySpec().groupBy());

            ProjectionBuilder projectionBuilder = new ProjectionBuilder(table.querySpec());

            SplitPoints splitPoints = projectionBuilder.getSplitPoints();

            // start: Map/Collect side
            GroupProjection groupProjection = projectionBuilder.groupProjection(
                    splitPoints.leaves(),
                    table.querySpec().groupBy(),
                    splitPoints.aggregates(),
                    Aggregation.Step.ITER,
                    Aggregation.Step.PARTIAL);

            CollectNode collectNode = PlanNodeBuilder.distributingCollect(
                    tableInfo,
                    context.consumerContext.plannerContext(),
                    table.querySpec().where(),
                    splitPoints.leaves(),
                    Lists.newArrayList(routing.nodes()),
                    ImmutableList.<Projection>of(groupProjection)
            );
            // end: Map/Collect side

            // start: Reducer
            List<Symbol> collectOutputs = new ArrayList<>(
                    groupBy.size() +
                            splitPoints.aggregates().size());
            collectOutputs.addAll(groupBy);
            collectOutputs.addAll(splitPoints.aggregates());

            List<Projection> reducerProjections = new LinkedList<>();
            reducerProjections.add(projectionBuilder.groupProjection(
                    collectOutputs,
                    table.querySpec().groupBy(),
                    splitPoints.aggregates(),
                    Aggregation.Step.PARTIAL,
                    Aggregation.Step.FINAL)
            );

            OrderBy orderBy = table.querySpec().orderBy();
            if (orderBy != null) {
                table.tableRelation().validateOrderBy(orderBy);
            }

            HavingClause havingClause = table.querySpec().having();
            if (havingClause != null) {
                if (havingClause.noMatch()) {
                    return new NoopPlannedAnalyzedRelation(table);
                } else if (havingClause.hasQuery()) {
                    reducerProjections.add(projectionBuilder.filterProjection(
                            collectOutputs,
                            havingClause.query()
                    ));
                }
            }

            boolean isRootRelation = context.consumerContext.rootRelation() == table;
            if (isRootRelation) {
                reducerProjections.add(projectionBuilder.topNProjection(
                        collectOutputs,
                        orderBy,
                        0,
                        MoreObjects.firstNonNull(table.querySpec().limit(),
                                Constants.DEFAULT_SELECT_LIMIT) + table.querySpec().offset(),
                        table.querySpec().outputs()));
            }
            MergeNode mergeNode = PlanNodeBuilder.distributedMerge(
                    collectNode,
                    context.consumerContext.plannerContext(),
                    reducerProjections
            );
            // end: Reducer

            MergeNode localMergeNode = null;
            String localNodeId = context.consumerContext.plannerContext().clusterService().state().nodes().localNodeId();
            if(isRootRelation) {
                TopNProjection topN = projectionBuilder.topNProjection(
                        table.querySpec().outputs(),
                        orderBy,
                        table.querySpec().offset(),
                        table.querySpec().limit(),
                        null);
                localMergeNode = PlanNodeBuilder.localMerge(ImmutableList.<Projection>of(topN),
                        mergeNode, context.consumerContext.plannerContext());
                localMergeNode.executionNodes(Sets.newHashSet(localNodeId));

                mergeNode.downstreamNodes(localMergeNode.executionNodes());
                mergeNode.downstreamExecutionNodeId(localMergeNode.executionNodeId());
            } else {
                mergeNode.downstreamNodes(Sets.newHashSet(localNodeId));
                mergeNode.downstreamExecutionNodeId(mergeNode.executionNodeId() + 1);
            }
            context.result = true;

            collectNode.downstreamExecutionNodeId(mergeNode.executionNodeId());
            return new DistributedGroupBy(
                    collectNode,
                    mergeNode,
                    localMergeNode
            );
        }

        @Override
        public AnalyzedRelation visitInsertFromQuery(InsertFromSubQueryAnalyzedStatement insertFromSubQueryAnalyzedStatement, Context context) {
            InsertFromSubQueryConsumer.planInnerRelation(insertFromSubQueryAnalyzedStatement, context, this);
            return insertFromSubQueryAnalyzedStatement;
        }

        @Override
        protected AnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, Context context) {
            return relation;
        }

    }
}


File: sql/src/main/java/io/crate/planner/consumer/ESGetConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;


import io.crate.analyze.OrderBy;
import io.crate.analyze.QueriedTable;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.exceptions.VersionInvalidException;
import io.crate.metadata.table.TableInfo;
import io.crate.planner.RowGranularity;
import io.crate.planner.node.NoopPlannedAnalyzedRelation;
import io.crate.planner.node.dql.ESGetNode;

public class ESGetConsumer implements Consumer {

    private static final Visitor VISITOR = new Visitor();

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        PlannedAnalyzedRelation relation = VISITOR.process(rootRelation, context);
        if (relation == null) {
            return false;
        }
        context.rootRelation(relation);
        return true;
    }

    private static class Visitor extends AnalyzedRelationVisitor<ConsumerContext, PlannedAnalyzedRelation> {

        @Override
        public PlannedAnalyzedRelation visitQueriedTable(QueriedTable table, ConsumerContext context) {
            if (table.querySpec().hasAggregates() || table.querySpec().groupBy()!=null) {
                return null;
            }
            TableInfo tableInfo = table.tableRelation().tableInfo();
            if (tableInfo.isAlias()
                    || tableInfo.schemaInfo().systemSchema()
                    || tableInfo.rowGranularity() != RowGranularity.DOC) {
                return null;
            }

            if (!table.querySpec().where().docKeys().isPresent()) {
                return null;
            }

            if(table.querySpec().where().docKeys().get().withVersions()){
                context.validationException(new VersionInvalidException());
                return null;
            }
            Integer limit = table.querySpec().limit();
            if (limit != null){
                if (limit == 0){
                    return new NoopPlannedAnalyzedRelation(table);
                }
            }

            OrderBy orderBy = table.querySpec().orderBy();
            if (orderBy != null){
                table.tableRelation().validateOrderBy(orderBy);
            }
            return new ESGetNode(context.plannerContext().nextExecutionNodeId(), tableInfo, table.querySpec());
        }

        @Override
        protected PlannedAnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, ConsumerContext context) {
            return null;
        }
    }
}


File: sql/src/main/java/io/crate/planner/consumer/GlobalAggregateConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import com.google.common.collect.ImmutableList;
import io.crate.analyze.*;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.analyze.relations.TableRelation;
import io.crate.exceptions.VersionInvalidException;
import io.crate.metadata.FunctionInfo;
import io.crate.metadata.ReferenceInfo;
import io.crate.planner.PlanNodeBuilder;
import io.crate.planner.node.NoopPlannedAnalyzedRelation;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.GlobalAggregate;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.projection.AggregationProjection;
import io.crate.planner.projection.Projection;
import io.crate.planner.projection.TopNProjection;
import io.crate.planner.projection.builder.ProjectionBuilder;
import io.crate.planner.projection.builder.SplitPoints;
import io.crate.planner.symbol.*;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import static com.google.common.base.MoreObjects.firstNonNull;


public class GlobalAggregateConsumer implements Consumer {

    private static final Visitor VISITOR = new Visitor();
    private static final AggregationOutputValidator AGGREGATION_OUTPUT_VALIDATOR = new AggregationOutputValidator();

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        AnalyzedRelation analyzedRelation = VISITOR.process(rootRelation, context);
        if (analyzedRelation != null) {
            context.rootRelation(analyzedRelation);
            return true;
        }
        return false;
    }

    private static class Visitor extends AnalyzedRelationVisitor<ConsumerContext, PlannedAnalyzedRelation> {

        @Override
        public PlannedAnalyzedRelation visitQueriedTable(QueriedTable table, ConsumerContext context) {
            if (table.querySpec().groupBy()!=null || !table.querySpec().hasAggregates()) {
                return null;
            }
            if (firstNonNull(table.querySpec().limit(), 1) < 1 || table.querySpec().offset() > 0){
                return new NoopPlannedAnalyzedRelation(table);
            }

            if (table.querySpec().where().hasVersions()){
                context.validationException(new VersionInvalidException());
                return null;
            }
            return globalAggregates(table, table.tableRelation(),  table.querySpec().where(), context);
        }

        @Override
        public PlannedAnalyzedRelation visitInsertFromQuery(InsertFromSubQueryAnalyzedStatement insertFromSubQueryAnalyzedStatement, ConsumerContext context) {
            InsertFromSubQueryConsumer.planInnerRelation(insertFromSubQueryAnalyzedStatement, context, this);
            return null;
        }

        @Override
        protected PlannedAnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, ConsumerContext context) {
            return null;
        }
    }

    private static boolean noGroupBy(List<Symbol> groupBy) {
        return groupBy == null || groupBy.isEmpty();
    }

    public static PlannedAnalyzedRelation globalAggregates(QueriedTable table,
                                                           TableRelation tableRelation,
                                                           WhereClause whereClause,
                                                           ConsumerContext context) {
        assert noGroupBy(table.querySpec().groupBy()) : "must not have group by clause for global aggregate queries";
        validateAggregationOutputs(tableRelation, table.querySpec().outputs());
        // global aggregate: collect and partial aggregate on C and final agg on H

        ProjectionBuilder projectionBuilder = new ProjectionBuilder(table.querySpec());
        SplitPoints splitPoints = projectionBuilder.getSplitPoints();

        AggregationProjection ap = projectionBuilder.aggregationProjection(
                splitPoints.leaves(),
                splitPoints.aggregates(),
                Aggregation.Step.ITER,
                Aggregation.Step.PARTIAL);

        CollectNode collectNode = PlanNodeBuilder.collect(
                tableRelation.tableInfo(),
                context.plannerContext(),
                whereClause,
                splitPoints.leaves(),
                ImmutableList.<Projection>of(ap)
        );

        //// the handler stuff
        List<Projection> projections = new ArrayList<>();
        projections.add(projectionBuilder.aggregationProjection(
                splitPoints.aggregates(),
                splitPoints.aggregates(),
                Aggregation.Step.PARTIAL,
                Aggregation.Step.FINAL));

        HavingClause havingClause = table.querySpec().having();
        if(havingClause != null){
            if (havingClause.noMatch()) {
                return new NoopPlannedAnalyzedRelation(table);
            } else if (havingClause.hasQuery()){
                projections.add(projectionBuilder.filterProjection(
                        splitPoints.aggregates(),
                        havingClause.query()
                ));
            }
        }

        TopNProjection topNProjection = projectionBuilder.topNProjection(
                splitPoints.aggregates(),
                null, 0, 1,
                table.querySpec().outputs()
                );
        projections.add(topNProjection);
        MergeNode localMergeNode = PlanNodeBuilder.localMerge(projections, collectNode,
                context.plannerContext());
        return new GlobalAggregate(collectNode, localMergeNode);
    }

    private static void validateAggregationOutputs(TableRelation tableRelation, Collection<? extends Symbol> outputSymbols) {
        OutputValidatorContext context = new OutputValidatorContext(tableRelation);
        for (Symbol outputSymbol : outputSymbols) {
            context.insideAggregation = false;
            AGGREGATION_OUTPUT_VALIDATOR.process(outputSymbol, context);
        }
    }

    private static class OutputValidatorContext {
        private final TableRelation tableRelation;
        private boolean insideAggregation = false;

        public OutputValidatorContext(TableRelation tableRelation) {
            this.tableRelation = tableRelation;
        }
    }

    private static class AggregationOutputValidator extends SymbolVisitor<OutputValidatorContext, Void> {

        @Override
        public Void visitFunction(Function symbol, OutputValidatorContext context) {
            context.insideAggregation = context.insideAggregation || symbol.info().type().equals(FunctionInfo.Type.AGGREGATE);
            for (Symbol argument : symbol.arguments()) {
                process(argument, context);
            }
            context.insideAggregation = false;
            return null;
        }

        @Override
        public Void visitReference(Reference symbol, OutputValidatorContext context) {
            if (context.insideAggregation) {
                ReferenceInfo.IndexType indexType = symbol.info().indexType();
                if (indexType == ReferenceInfo.IndexType.ANALYZED) {
                    throw new IllegalArgumentException(String.format(
                            "Cannot select analyzed column '%s' within grouping or aggregations", SymbolFormatter.format(symbol)));
                } else if (indexType == ReferenceInfo.IndexType.NO) {
                    throw new IllegalArgumentException(String.format(
                            "Cannot select non-indexed column '%s' within grouping or aggregations", SymbolFormatter.format(symbol)));
                }
            }
            return null;
        }

        @Override
        public Void visitField(Field field, OutputValidatorContext context) {
            return process(context.tableRelation.resolveField(field), context);
        }

        @Override
        protected Void visitSymbol(Symbol symbol, OutputValidatorContext context) {
            return null;
        }
    }
}


File: sql/src/main/java/io/crate/planner/consumer/InsertFromSubQueryConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;


import com.google.common.collect.ImmutableList;
import io.crate.analyze.InsertFromSubQueryAnalyzedStatement;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.operation.aggregation.impl.CountAggregation;
import io.crate.planner.PlanNodeBuilder;
import io.crate.planner.node.dml.InsertFromSubQuery;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.projection.AggregationProjection;
import io.crate.planner.projection.ColumnIndexWriterProjection;
import io.crate.planner.projection.Projection;
import org.elasticsearch.common.settings.ImmutableSettings;


public class InsertFromSubQueryConsumer implements Consumer {

    private final Visitor visitor;

    public InsertFromSubQueryConsumer(){
        visitor = new Visitor();
    }

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        Context ctx = new Context(context);
        context.rootRelation(visitor.process(context.rootRelation(), ctx));
        return ctx.result;
    }

    private static class Context {
        ConsumerContext consumerContext;
        boolean result = false;

        public Context(ConsumerContext context){
            this.consumerContext = context;
        }
    }

    private static class Visitor extends AnalyzedRelationVisitor<Context, AnalyzedRelation> {

        @Override
        public AnalyzedRelation visitInsertFromQuery(InsertFromSubQueryAnalyzedStatement insertFromSubQueryAnalyzedStatement, Context context) {

            ColumnIndexWriterProjection indexWriterProjection = new ColumnIndexWriterProjection(
                    insertFromSubQueryAnalyzedStatement.tableInfo().ident(),
                    null,
                    insertFromSubQueryAnalyzedStatement.tableInfo().primaryKey(),
                    insertFromSubQueryAnalyzedStatement.columns(),
                    insertFromSubQueryAnalyzedStatement.onDuplicateKeyAssignments(),
                    insertFromSubQueryAnalyzedStatement.primaryKeyColumnIndices(),
                    insertFromSubQueryAnalyzedStatement.partitionedByIndices(),
                    insertFromSubQueryAnalyzedStatement.routingColumn(),
                    insertFromSubQueryAnalyzedStatement.routingColumnIndex(),
                    ImmutableSettings.EMPTY,
                    insertFromSubQueryAnalyzedStatement.tableInfo().isPartitioned()
            );

            AnalyzedRelation innerRelation = insertFromSubQueryAnalyzedStatement.subQueryRelation();
            if (innerRelation instanceof PlannedAnalyzedRelation) {
                PlannedAnalyzedRelation analyzedRelation = (PlannedAnalyzedRelation)innerRelation;
                analyzedRelation.addProjection(indexWriterProjection);

                MergeNode mergeNode = null;
                if (analyzedRelation.resultIsDistributed()) {
                    // add local merge Node which aggregates the distributed results
                    AggregationProjection aggregationProjection = CountAggregation.PARTIAL_COUNT_AGGREGATION_PROJECTION;
                    mergeNode = PlanNodeBuilder.localMerge(
                            ImmutableList.<Projection>of(aggregationProjection),
                            analyzedRelation.resultNode(),
                            context.consumerContext.plannerContext());
                }
                context.result = true;
                return new InsertFromSubQuery(((PlannedAnalyzedRelation) innerRelation).plan(), mergeNode);
            } else {
                return insertFromSubQueryAnalyzedStatement;
            }
        }

        @Override
        protected AnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, Context context) {
            return relation;
        }
    }

    public static <C, R> void planInnerRelation(InsertFromSubQueryAnalyzedStatement insertFromSubQueryAnalyzedStatement,
                                                C context, AnalyzedRelationVisitor<C,R> visitor) {
        if (insertFromSubQueryAnalyzedStatement.subQueryRelation() instanceof PlannedAnalyzedRelation) {
            // inner relation is already Planned
            return;
        }
        R innerRelation = visitor.process(insertFromSubQueryAnalyzedStatement.subQueryRelation(), context);
        if (innerRelation != null && innerRelation instanceof PlannedAnalyzedRelation) {
            insertFromSubQueryAnalyzedStatement.subQueryRelation((PlannedAnalyzedRelation)innerRelation);
        }
    }


}


File: sql/src/main/java/io/crate/planner/consumer/NonDistributedGroupByConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */
package io.crate.planner.consumer;

import com.google.common.collect.ImmutableList;
import io.crate.analyze.*;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.exceptions.VersionInvalidException;
import io.crate.metadata.Routing;
import io.crate.metadata.table.TableInfo;
import io.crate.planner.PlanNodeBuilder;
import io.crate.planner.node.NoopPlannedAnalyzedRelation;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.GroupByConsumer;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.node.dql.NonDistributedGroupBy;
import io.crate.planner.projection.GroupProjection;
import io.crate.planner.projection.Projection;
import io.crate.planner.projection.builder.ProjectionBuilder;
import io.crate.planner.projection.builder.SplitPoints;
import io.crate.planner.symbol.Aggregation;
import io.crate.planner.symbol.Symbol;

import java.util.ArrayList;
import java.util.List;

public class NonDistributedGroupByConsumer implements Consumer {

    private static final Visitor VISITOR = new Visitor();

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        Context ctx = new Context(context);
        context.rootRelation(VISITOR.process(context.rootRelation(), ctx));
        return ctx.result;
    }

    private static class Context {
        ConsumerContext consumerContext;
        boolean result = false;

        public Context(ConsumerContext context) {
            this.consumerContext = context;
        }
    }

    private static class Visitor extends AnalyzedRelationVisitor<Context, AnalyzedRelation> {

        @Override
        public AnalyzedRelation visitQueriedTable(QueriedTable table, Context context) {
            if (table.querySpec().groupBy() == null) {
                return table;
            }
            TableInfo tableInfo = table.tableRelation().tableInfo();

            if (table.querySpec().where().hasVersions()) {
                context.consumerContext.validationException(new VersionInvalidException());
                return table;
            }

            Routing routing = tableInfo.getRouting(table.querySpec().where(), null);

            if (GroupByConsumer.requiresDistribution(tableInfo, routing) && !(tableInfo.schemaInfo().systemSchema())) {
                return table;
            }

            context.result = true;
            return nonDistributedGroupBy(table, context);
        }

        @Override
        public AnalyzedRelation visitInsertFromQuery(InsertFromSubQueryAnalyzedStatement insertFromSubQueryAnalyzedStatement, Context context) {
            InsertFromSubQueryConsumer.planInnerRelation(insertFromSubQueryAnalyzedStatement, context, this);
            return insertFromSubQueryAnalyzedStatement;

        }

        @Override
        protected AnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, Context context) {
            return relation;
        }

        /**
         * Group by on System Tables (never needs distribution)
         * or Group by on user tables (RowGranulariy.DOC) with only one node.
         *
         * produces:
         *
         * SELECT:
         * Collect ( GroupProjection ITER -> PARTIAL )
         * LocalMerge ( GroupProjection PARTIAL -> FINAL, [FilterProjection], TopN )
         *
         */
        private AnalyzedRelation nonDistributedGroupBy(QueriedTable table, Context context) {
            TableInfo tableInfo = table.tableRelation().tableInfo();

            GroupByConsumer.validateGroupBySymbols(table.tableRelation(), table.querySpec().groupBy());
            List<Symbol> groupBy = table.querySpec().groupBy();

            ProjectionBuilder projectionBuilder = new ProjectionBuilder(table.querySpec());
            SplitPoints splitPoints = projectionBuilder.getSplitPoints();

            // mapper / collect
            GroupProjection groupProjection = projectionBuilder.groupProjection(
                    splitPoints.leaves(),
                    table.querySpec().groupBy(),
                    splitPoints.aggregates(),
                    Aggregation.Step.ITER,
                    Aggregation.Step.PARTIAL);

            CollectNode collectNode = PlanNodeBuilder.collect(
                    tableInfo,
                    context.consumerContext.plannerContext(),
                    table.querySpec().where(),
                    splitPoints.leaves(),
                    ImmutableList.<Projection>of(groupProjection)
            );
            // handler
            List<Symbol> collectOutputs = new ArrayList<>(
                    groupBy.size() +
                            splitPoints.aggregates().size());
            collectOutputs.addAll(groupBy);
            collectOutputs.addAll(splitPoints.aggregates());


            OrderBy orderBy = table.querySpec().orderBy();
            if (orderBy != null) {
                table.tableRelation().validateOrderBy(orderBy);
            }

            List<Projection> projections = new ArrayList<>();
            projections.add(projectionBuilder.groupProjection(
                    collectOutputs,
                    table.querySpec().groupBy(),
                    splitPoints.aggregates(),
                    Aggregation.Step.PARTIAL,
                    Aggregation.Step.FINAL
            ));

            HavingClause havingClause = table.querySpec().having();
            if (havingClause != null) {
                if (havingClause.noMatch()) {
                    return new NoopPlannedAnalyzedRelation(table);
                } else if (havingClause.hasQuery()){
                    projections.add(projectionBuilder.filterProjection(
                            collectOutputs,
                            havingClause.query()
                    ));
                }
            }

            /**
             * If this is not the rootRelation this is a subquery (e.g. Insert by Query),
             * so ordering and limiting is done by the rootRelation if required.
             *
             * If the querySpec outputs don't match the collectOutputs the query contains
             * aggregations or scalar functions which can only be resolved by a TopNProjection,
             * so a TopNProjection must be added.
             */
            boolean outputsMatch = table.querySpec().outputs().size() == collectOutputs.size() &&
                                    collectOutputs.containsAll(table.querySpec().outputs());
            if (context.consumerContext.rootRelation() == table || !outputsMatch){
                projections.add(projectionBuilder.topNProjection(
                        collectOutputs,
                        orderBy,
                        table.querySpec().offset(),
                        table.querySpec().limit(),
                        table.querySpec().outputs()
                ));
            }
            MergeNode localMergeNode = PlanNodeBuilder.localMerge(projections, collectNode,
                    context.consumerContext.plannerContext());
            return new NonDistributedGroupBy(collectNode, localMergeNode);
        }
    }

}


File: sql/src/main/java/io/crate/planner/consumer/QueryAndFetchConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import com.google.common.collect.ImmutableList;
import io.crate.Constants;
import io.crate.analyze.*;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.analyze.relations.TableRelation;
import io.crate.exceptions.UnsupportedFeatureException;
import io.crate.exceptions.VersionInvalidException;
import io.crate.metadata.DocReferenceConverter;
import io.crate.metadata.FunctionIdent;
import io.crate.metadata.Functions;
import io.crate.metadata.table.TableInfo;
import io.crate.operation.aggregation.impl.SumAggregation;
import io.crate.operation.predicate.MatchPredicate;
import io.crate.planner.PlanNodeBuilder;
import io.crate.planner.node.dql.QueryAndFetch;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.projection.AggregationProjection;
import io.crate.planner.projection.Projection;
import io.crate.planner.projection.TopNProjection;
import io.crate.planner.symbol.*;
import io.crate.types.DataType;
import io.crate.types.DataTypes;
import io.crate.types.LongType;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import static com.google.common.base.MoreObjects.firstNonNull;

public class QueryAndFetchConsumer implements Consumer {

    private static final Visitor VISITOR = new Visitor();

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        Context ctx = new Context(context);
        context.rootRelation(VISITOR.process(context.rootRelation(), ctx));
        return ctx.result;
    }

    private static class Context {
        ConsumerContext consumerContext;
        boolean result = false;

        public Context(ConsumerContext context) {
            this.consumerContext = context;
        }
    }

    private static class Visitor extends AnalyzedRelationVisitor<Context, AnalyzedRelation> {

        @Override
        public AnalyzedRelation visitQueriedTable(QueriedTable table, Context context) {
            TableRelation tableRelation = table.tableRelation();
            if(table.querySpec().where().hasVersions()){
                context.consumerContext.validationException(new VersionInvalidException());
                return table;
            }
            TableInfo tableInfo = tableRelation.tableInfo();

            if (tableInfo.schemaInfo().systemSchema() && table.querySpec().where().hasQuery()) {
                ensureNoLuceneOnlyPredicates(table.querySpec().where().query());
            }
            if (table.querySpec().hasAggregates()) {
                context.result = true;
                return GlobalAggregateConsumer.globalAggregates(table, tableRelation, table.querySpec().where(), context.consumerContext);
            } else {
               context.result = true;
               return normalSelect(table, table.querySpec().where(), tableRelation, context);
            }
        }

        @Override
        public AnalyzedRelation visitInsertFromQuery(InsertFromSubQueryAnalyzedStatement insertFromSubQueryAnalyzedStatement,
                                                     Context context) {
            InsertFromSubQueryConsumer.planInnerRelation(insertFromSubQueryAnalyzedStatement, context, this);
            return insertFromSubQueryAnalyzedStatement;
        }

        @Override
        protected AnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, Context context) {
            return relation;
        }

        private void ensureNoLuceneOnlyPredicates(Symbol query) {
            NoPredicateVisitor noPredicateVisitor = new NoPredicateVisitor();
            noPredicateVisitor.process(query, null);
        }

        private static class NoPredicateVisitor extends SymbolVisitor<Void, Void> {
            @Override
            public Void visitFunction(Function symbol, Void context) {
                if (symbol.info().ident().name().equals(MatchPredicate.NAME)) {
                    throw new UnsupportedFeatureException("Cannot use match predicate on system tables");
                }
                for (Symbol argument : symbol.arguments()) {
                    process(argument, context);
                }
                return null;
            }
        }

        private AnalyzedRelation normalSelect(QueriedTable table,
                                              WhereClause whereClause,
                                              TableRelation tableRelation,
                                              Context context){
            QuerySpec querySpec = table.querySpec();
            TableInfo tableInfo = tableRelation.tableInfo();

            List<Symbol> outputSymbols;
            if (tableInfo.schemaInfo().systemSchema()) {
                outputSymbols = tableRelation.resolve(querySpec.outputs());
            } else {
                outputSymbols = new ArrayList<>(querySpec.outputs().size());
                for (Symbol symbol : querySpec.outputs()) {
                    outputSymbols.add(DocReferenceConverter.convertIfPossible(tableRelation.resolve(symbol), tableInfo));
                }
            }
            CollectNode collectNode;
            MergeNode mergeNode = null;
            OrderBy orderBy = querySpec.orderBy();
            if (context.consumerContext.rootRelation() != table) {
                // insert directly from shards
                assert !querySpec.isLimited() : "insert from sub query with limit or order by is not supported. " +
                        "Analyzer should have thrown an exception already.";

                ImmutableList<Projection> projections = ImmutableList.<Projection>of();
                collectNode = PlanNodeBuilder.collect(tableInfo,
                        context.consumerContext.plannerContext(),
                        whereClause, outputSymbols, projections);
            } else if (querySpec.isLimited() || orderBy != null) {
                /**
                 * select id, name, order by id, date
                 *
                 * toCollect:       [id, name, date]            // includes order by symbols, that aren't already selected
                 * allOutputs:      [in(0), in(1), in(2)]       // for topN projection on shards/collectNode
                 * orderByInputs:   [in(0), in(2)]              // for topN projection on shards/collectNode AND handler
                 * finalOutputs:    [in(0), in(1)]              // for topN output on handler -> changes output to what should be returned.
                 */
                List<Symbol> toCollect;
                List<Symbol> orderByInputColumns = null;
                if (orderBy != null){
                    List<Symbol> orderBySymbols = tableRelation.resolve(orderBy.orderBySymbols());
                    toCollect = new ArrayList<>(outputSymbols.size() + orderBySymbols.size());
                    toCollect.addAll(outputSymbols);
                    // note: can only de-dup order by symbols due to non-deterministic functions like select random(), random()
                    for (Symbol orderBySymbol : orderBySymbols) {
                        if (!toCollect.contains(orderBySymbol)) {
                            toCollect.add(orderBySymbol);
                        }
                    }
                    orderByInputColumns = new ArrayList<>();
                    for (Symbol symbol : orderBySymbols) {
                        orderByInputColumns.add(new InputColumn(toCollect.indexOf(symbol), symbol.valueType()));
                    }
                } else {
                    toCollect = new ArrayList<>(outputSymbols.size());
                    toCollect.addAll(outputSymbols);
                }

                List<Symbol> allOutputs = new ArrayList<>(toCollect.size());        // outputs from collector
                for (int i = 0; i < toCollect.size(); i++) {
                    allOutputs.add(new InputColumn(i, toCollect.get(i).valueType()));
                }
                List<Symbol> finalOutputs = new ArrayList<>(outputSymbols.size());  // final outputs on handler after sort
                for (int i = 0; i < outputSymbols.size(); i++) {
                    finalOutputs.add(new InputColumn(i, outputSymbols.get(i).valueType()));
                }

                // if we have an offset we have to get as much docs from every node as we have offset+limit
                // otherwise results will be wrong
                TopNProjection tnp;
                int limit = firstNonNull(querySpec.limit(), Constants.DEFAULT_SELECT_LIMIT);
                if (orderBy == null){
                    tnp = new TopNProjection(querySpec.offset() + limit, 0);
                } else {
                    tnp = new TopNProjection(querySpec.offset() + limit, 0,
                            orderByInputColumns,
                            orderBy.reverseFlags(),
                            orderBy.nullsFirst()
                    );
                }
                tnp.outputs(allOutputs);
                collectNode = PlanNodeBuilder.collect(tableInfo,
                        context.consumerContext.plannerContext(),
                        whereClause, toCollect, ImmutableList.<Projection>of(tnp));

                // MERGE
                tnp = new TopNProjection(limit, querySpec.offset());
                tnp.outputs(finalOutputs);
                if (orderBy == null) {
                    // no sorting needed
                    mergeNode = PlanNodeBuilder.localMerge(ImmutableList.<Projection>of(tnp), collectNode,
                            context.consumerContext.plannerContext());
                } else {
                    // no order by needed in TopN as we already sorted on collector
                    // and we merge sorted with SortedBucketMerger
                    mergeNode = PlanNodeBuilder.sortedLocalMerge(
                            ImmutableList.<Projection>of(tnp),
                            orderBy,
                            allOutputs,
                            orderByInputColumns,
                            collectNode,
                            context.consumerContext.plannerContext()
                    );
                }
            } else {
                collectNode = PlanNodeBuilder.collect(tableInfo,
                        context.consumerContext.plannerContext(),
                        whereClause, outputSymbols, ImmutableList.<Projection>of());
                mergeNode = PlanNodeBuilder.localMerge(
                        ImmutableList.<Projection>of(), collectNode,
                        context.consumerContext.plannerContext());
            }
            return new QueryAndFetch(collectNode, mergeNode);
        }
    }
}


File: sql/src/main/java/io/crate/planner/consumer/QueryThenFetchConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import com.google.common.collect.ImmutableList;
import io.crate.Constants;
import io.crate.analyze.OrderBy;
import io.crate.analyze.QueriedTable;
import io.crate.analyze.QuerySpec;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.exceptions.VersionInvalidException;
import io.crate.metadata.ColumnIdent;
import io.crate.metadata.DocReferenceConverter;
import io.crate.metadata.ReferenceInfo;
import io.crate.metadata.ScoreReferenceDetector;
import io.crate.metadata.doc.DocSysColumns;
import io.crate.metadata.table.TableInfo;
import io.crate.operation.projectors.FetchProjector;
import io.crate.planner.PlanNodeBuilder;
import io.crate.planner.RowGranularity;
import io.crate.planner.node.NoopPlannedAnalyzedRelation;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.node.dql.QueryThenFetch;
import io.crate.planner.projection.FetchProjection;
import io.crate.planner.projection.MergeProjection;
import io.crate.planner.projection.Projection;
import io.crate.planner.projection.TopNProjection;
import io.crate.planner.projection.builder.ProjectionBuilder;
import io.crate.planner.projection.builder.SplitPoints;
import io.crate.planner.symbol.*;
import io.crate.types.DataTypes;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class QueryThenFetchConsumer implements Consumer {

    private static final Visitor VISITOR = new Visitor();
    private static final OutputOrderReferenceCollector OUTPUT_ORDER_REFERENCE_COLLECTOR = new OutputOrderReferenceCollector();
    private static final ReferencesCollector REFERENCES_COLLECTOR = new ReferencesCollector();
    private static final ScoreReferenceDetector SCORE_REFERENCE_DETECTOR = new ScoreReferenceDetector();
    private static final ColumnIdent DOC_ID_COLUMN_IDENT = new ColumnIdent(DocSysColumns.DOCID.name());
    private static final InputColumn DEFAULT_DOC_ID_INPUT_COLUMN = new InputColumn(0, DataTypes.STRING);

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        PlannedAnalyzedRelation plannedAnalyzedRelation = VISITOR.process(rootRelation, context);
        if (plannedAnalyzedRelation == null) {
            return false;
        }
        context.rootRelation(plannedAnalyzedRelation);
        return true;
    }

    private static class Visitor extends AnalyzedRelationVisitor<ConsumerContext, PlannedAnalyzedRelation> {

        @Override
        public PlannedAnalyzedRelation visitQueriedTable(QueriedTable table, ConsumerContext context) {
            QuerySpec querySpec = table.querySpec();
            if (querySpec.hasAggregates() || querySpec.groupBy()!=null) {
                return null;
            }
            TableInfo tableInfo = table.tableRelation().tableInfo();
            if (tableInfo.schemaInfo().systemSchema() || tableInfo.rowGranularity() != RowGranularity.DOC) {
                return null;
            }

            if(querySpec.where().hasVersions()){
                context.validationException(new VersionInvalidException());
                return null;
            }

            if (querySpec.where().noMatch()) {
                return new NoopPlannedAnalyzedRelation(table);
            }

            boolean outputsAreAllOrdered = false;
            boolean needFetchProjection = REFERENCES_COLLECTOR.collect(querySpec.outputs()).containsAnyReference();
            List<Projection> collectProjections = new ArrayList<>();
            List<Projection> mergeProjections = new ArrayList<>();
            List<Symbol> collectSymbols = new ArrayList<>();
            List<Symbol> outputSymbols = new ArrayList<>();
            ReferenceInfo docIdRefInfo = tableInfo.getReferenceInfo(DOC_ID_COLUMN_IDENT);

            ProjectionBuilder projectionBuilder = new ProjectionBuilder(querySpec);
            SplitPoints splitPoints = projectionBuilder.getSplitPoints();

            // MAP/COLLECT related
            OrderBy orderBy = querySpec.orderBy();
            if (orderBy != null) {
                table.tableRelation().validateOrderBy(orderBy);

                // detect if all output columns are used in orderBy,
                // if so, no fetch projection is needed
                // TODO: if no dedicated fetchPhase is needed we should stick to QAF instead
                OutputOrderReferenceContext outputOrderContext =
                        OUTPUT_ORDER_REFERENCE_COLLECTOR.collect(splitPoints.leaves());
                outputOrderContext.collectOrderBy = true;
                OUTPUT_ORDER_REFERENCE_COLLECTOR.collect(orderBy.orderBySymbols(), outputOrderContext);
                outputsAreAllOrdered = outputOrderContext.outputsAreAllOrdered();
                if (outputsAreAllOrdered) {
                    collectSymbols = splitPoints.toCollect();
                } else {
                    collectSymbols.addAll(orderBy.orderBySymbols());
                }
            }

            needFetchProjection = needFetchProjection & !outputsAreAllOrdered;

            if (needFetchProjection) {
                collectSymbols.add(0, new Reference(docIdRefInfo));
                for (Symbol symbol : querySpec.outputs()) {
                    // _score can only be resolved during collect
                    if (SCORE_REFERENCE_DETECTOR.detect(symbol) && !collectSymbols.contains(symbol)) {
                        collectSymbols.add(symbol);
                    }
                    outputSymbols.add(DocReferenceConverter.convertIfPossible(symbol, tableInfo));
                }
            } else {
                // no fetch projection needed, resolve all symbols during collect
                collectSymbols = splitPoints.toCollect();
            }
            if (orderBy != null) {
                MergeProjection mergeProjection = projectionBuilder.mergeProjection(
                        collectSymbols,
                        orderBy);
                collectProjections.add(mergeProjection);
            }

            Integer limit = querySpec.limit();
            // apply default limit if relation is root relation
            if ( limit == null && context.rootRelation() == table) {
                limit = Constants.DEFAULT_SELECT_LIMIT;
            }

            CollectNode collectNode = PlanNodeBuilder.collect(
                    tableInfo,
                    context.plannerContext(),
                    querySpec.where(),
                    collectSymbols,
                    ImmutableList.<Projection>of(),
                    orderBy,
                    limit == null ? null : limit + querySpec.offset()
            );


            collectNode.keepContextForFetcher(needFetchProjection);
            collectNode.projections(collectProjections);
            // MAP/COLLECT related END

            // HANDLER/MERGE/FETCH related
            TopNProjection topNProjection;
            if (needFetchProjection) {
                topNProjection = projectionBuilder.topNProjection(
                        collectSymbols,
                        null,
                        querySpec.offset(),
                        querySpec.limit(),
                        null);
                mergeProjections.add(topNProjection);

                // by default don't split fetch requests into pages/chunks,
                // only if record set is higher than default limit
                int bulkSize = FetchProjector.NO_BULK_REQUESTS;
                if (topNProjection.limit() > Constants.DEFAULT_SELECT_LIMIT) {
                    bulkSize = Constants.DEFAULT_SELECT_LIMIT;
                }

                FetchProjection fetchProjection = new FetchProjection(
                        collectNode.executionNodeId(),
                        DEFAULT_DOC_ID_INPUT_COLUMN, collectSymbols, outputSymbols,
                        tableInfo.partitionedByColumns(),
                        collectNode.executionNodes(),
                        bulkSize,
                        querySpec.isLimited(),
                        context.plannerContext().jobSearchContextIdToNode(),
                        context.plannerContext().jobSearchContextIdToShard()
                );
                mergeProjections.add(fetchProjection);
            } else {
                topNProjection = projectionBuilder.topNProjection(
                        collectSymbols,
                        null,
                        querySpec.offset(),
                        querySpec.limit(),
                        querySpec.outputs());
                mergeProjections.add(topNProjection);
            }

            MergeNode localMergeNode;
            if (orderBy != null) {
                localMergeNode = PlanNodeBuilder.sortedLocalMerge(
                        mergeProjections,
                        orderBy,
                        collectSymbols,
                        null,
                        collectNode,
                        context.plannerContext());
            } else {
                localMergeNode = PlanNodeBuilder.localMerge(
                        mergeProjections,
                        collectNode,
                        context.plannerContext());
            }
            // HANDLER/MERGE/FETCH related END

            if (limit != null && limit + querySpec.offset() > Constants.PAGE_SIZE) {
                collectNode.downstreamNodes(Collections.singletonList(context.plannerContext().clusterService().localNode().id()));
                collectNode.downstreamExecutionNodeId(localMergeNode.executionNodeId());
            }
            return new QueryThenFetch(collectNode, localMergeNode);
        }

        @Override
        protected PlannedAnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, ConsumerContext context) {
            return null;
        }
    }

    static class OutputOrderReferenceContext {

        private List<Reference> outputReferences = new ArrayList<>();
        private List<Reference> orderByReferences = new ArrayList<>();
        public boolean collectOrderBy = false;

        public void addReference(Reference reference) {
            if (collectOrderBy) {
                orderByReferences.add(reference);
            } else {
                outputReferences.add(reference);
            }
        }

        public boolean outputsAreAllOrdered() {
            return orderByReferences.containsAll(outputReferences);
        }

    }

    static class OutputOrderReferenceCollector extends SymbolVisitor<OutputOrderReferenceContext, Void> {

        public OutputOrderReferenceContext collect(List<Symbol> symbols) {
            OutputOrderReferenceContext context = new OutputOrderReferenceContext();
            collect(symbols, context);
            return context;
        }

        public void collect(List<Symbol> symbols, OutputOrderReferenceContext context) {
            for (Symbol symbol : symbols) {
                process(symbol, context);
            }
        }

        @Override
        public Void visitAggregation(Aggregation aggregation, OutputOrderReferenceContext context) {
            for (Symbol symbol : aggregation.inputs()) {
                process(symbol, context);
            }
            return null;
        }

        @Override
        public Void visitReference(Reference symbol, OutputOrderReferenceContext context) {
            context.addReference(symbol);
            return null;
        }

        @Override
        public Void visitDynamicReference(DynamicReference symbol, OutputOrderReferenceContext context) {
            return visitReference(symbol, context);
        }

        @Override
        public Void visitFunction(Function function, OutputOrderReferenceContext context) {
            for (Symbol symbol : function.arguments()) {
                process(symbol, context);
            }
            return null;
        }
    }

    static class ReferencesCollectorContext {
        private List<Reference> outputReferences = new ArrayList<>();

        public void addReference(Reference reference) {
            outputReferences.add(reference);
        }

        public boolean containsAnyReference() {
            return !outputReferences.isEmpty();
        }
    }

    static class ReferencesCollector extends SymbolVisitor<ReferencesCollectorContext, Void> {

        public ReferencesCollectorContext collect(List<Symbol> symbols) {
            ReferencesCollectorContext context = new ReferencesCollectorContext();
            collect(symbols, context);
            return context;
        }

        public void collect(List<Symbol> symbols, ReferencesCollectorContext context) {
            for (Symbol symbol : symbols) {
                process(symbol, context);
            }
        }

        @Override
        public Void visitAggregation(Aggregation aggregation, ReferencesCollectorContext context) {
            for (Symbol symbol : aggregation.inputs()) {
                process(symbol, context);
            }
            return null;
        }

        @Override
        public Void visitReference(Reference symbol, ReferencesCollectorContext context) {
            context.addReference(symbol);
            return null;
        }

        @Override
        public Void visitDynamicReference(DynamicReference symbol, ReferencesCollectorContext context) {
            return visitReference(symbol, context);
        }

        @Override
        public Void visitFunction(Function function, ReferencesCollectorContext context) {
            for (Symbol symbol : function.arguments()) {
                process(symbol, context);
            }
            return null;
        }

    }
}


File: sql/src/main/java/io/crate/planner/consumer/ReduceOnCollectorGroupByConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import com.google.common.collect.ImmutableList;
import io.crate.Constants;
import io.crate.analyze.HavingClause;
import io.crate.analyze.InsertFromSubQueryAnalyzedStatement;
import io.crate.analyze.OrderBy;
import io.crate.analyze.QueriedTable;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.analyze.relations.TableRelation;
import io.crate.exceptions.VersionInvalidException;
import io.crate.metadata.table.TableInfo;
import io.crate.operation.projectors.TopN;
import io.crate.planner.PlanNodeBuilder;
import io.crate.planner.RowGranularity;
import io.crate.planner.node.NoopPlannedAnalyzedRelation;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.GroupByConsumer;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.node.dql.NonDistributedGroupBy;
import io.crate.planner.projection.FilterProjection;
import io.crate.planner.projection.GroupProjection;
import io.crate.planner.projection.Projection;
import io.crate.planner.projection.builder.ProjectionBuilder;
import io.crate.planner.projection.builder.SplitPoints;
import io.crate.planner.symbol.Aggregation;
import io.crate.planner.symbol.Symbol;

import java.util.ArrayList;
import java.util.List;

import static com.google.common.base.MoreObjects.firstNonNull;

public class ReduceOnCollectorGroupByConsumer implements Consumer {

    private static final Visitor VISITOR = new Visitor();

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        Context ctx = new Context(context);
        context.rootRelation(VISITOR.process(context.rootRelation(), ctx));
        return ctx.result;
    }

    private static class Context {
        ConsumerContext consumerContext;
        boolean result = false;

        public Context(ConsumerContext context) {
            this.consumerContext = context;
        }
    }

    private static class Visitor extends AnalyzedRelationVisitor<Context, AnalyzedRelation> {

        @Override
        public AnalyzedRelation visitQueriedTable(QueriedTable table, Context context) {
            if (table.querySpec().groupBy() == null) {
                return table;
            }

            if (!GroupByConsumer.groupedByClusteredColumnOrPrimaryKeys(
                    table.tableRelation(), table.querySpec().where(), table.querySpec().groupBy())) {
                return table;
            }

            if (table.querySpec().where().hasVersions()) {
                context.consumerContext.validationException(new VersionInvalidException());
                return table;
            }
            context.result = true;
            return optimizedReduceOnCollectorGroupBy(table, table.tableRelation(), context.consumerContext);
        }

        @Override
        public AnalyzedRelation visitInsertFromQuery(InsertFromSubQueryAnalyzedStatement insertFromSubQueryAnalyzedStatement, Context context) {
            InsertFromSubQueryConsumer.planInnerRelation(insertFromSubQueryAnalyzedStatement, context, this);
            return insertFromSubQueryAnalyzedStatement;
        }

        @Override
        protected AnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, Context context) {
            return relation;
        }

        /**
         * grouping on doc tables by clustered column or primary keys, no distribution needed
         * only one aggregation step as the mappers (shards) have row-authority
         *
         * produces:
         *
         * SELECT:
         * CollectNode ( GroupProjection, [FilterProjection], [TopN] )
         * LocalMergeNode ( TopN )
         */
        private AnalyzedRelation optimizedReduceOnCollectorGroupBy(QueriedTable table, TableRelation tableRelation, ConsumerContext context) {
            assert GroupByConsumer.groupedByClusteredColumnOrPrimaryKeys(
                    tableRelation, table.querySpec().where(), table.querySpec().groupBy()) : "not grouped by clustered column or primary keys";
            TableInfo tableInfo = tableRelation.tableInfo();
            GroupByConsumer.validateGroupBySymbols(tableRelation, table.querySpec().groupBy());
            List<Symbol> groupBy = table.querySpec().groupBy();

            boolean ignoreSorting = context.rootRelation() != table
                    && table.querySpec().limit() == null
                    && table.querySpec().offset() == TopN.NO_OFFSET;

            ProjectionBuilder projectionBuilder = new ProjectionBuilder(table.querySpec());
            SplitPoints splitPoints = projectionBuilder.getSplitPoints();

            // mapper / collect
            List<Symbol> collectOutputs = new ArrayList<>(
                    groupBy.size() +
                            splitPoints.aggregates().size());
            collectOutputs.addAll(groupBy);
            collectOutputs.addAll(splitPoints.aggregates());

            OrderBy orderBy = table.querySpec().orderBy();
            if (orderBy != null) {
                table.tableRelation().validateOrderBy(orderBy);
            }

            List<Projection> projections = new ArrayList<>();
            GroupProjection groupProjection = projectionBuilder.groupProjection(
                    splitPoints.leaves(),
                    table.querySpec().groupBy(),
                    splitPoints.aggregates(),
                    Aggregation.Step.ITER,
                    Aggregation.Step.FINAL
            );
            groupProjection.setRequiredGranularity(RowGranularity.SHARD);
            projections.add(groupProjection);

            HavingClause havingClause = table.querySpec().having();
            if (havingClause != null) {
                if (havingClause.noMatch()) {
                    return new NoopPlannedAnalyzedRelation(table);
                } else if (havingClause.hasQuery()) {
                    FilterProjection fp = projectionBuilder.filterProjection(
                            collectOutputs,
                            havingClause.query()
                    );
                    fp.requiredGranularity(RowGranularity.SHARD);
                    projections.add(fp);
                }
            }
            // mapper / collect
            // use topN on collector if needed
            boolean outputsMatch = table.querySpec().outputs().size() == collectOutputs.size() &&
                    collectOutputs.containsAll(table.querySpec().outputs());
            boolean collectorTopN = table.querySpec().limit() != null || table.querySpec().offset() > 0 || !outputsMatch;

            if (collectorTopN) {
                projections.add(projectionBuilder.topNProjection(
                        collectOutputs,
                        orderBy,
                        0, // no offset
                        firstNonNull(table.querySpec().limit(), Constants.DEFAULT_SELECT_LIMIT) + table.querySpec().offset(),
                        table.querySpec().outputs()
                ));
            }

            CollectNode collectNode = PlanNodeBuilder.collect(
                    tableInfo,
                    context.plannerContext(),
                    table.querySpec().where(),
                    splitPoints.leaves(),
                    ImmutableList.copyOf(projections)
            );

            // handler
            List<Projection> handlerProjections = new ArrayList<>();
            MergeNode localMergeNode;
            if (!ignoreSorting && collectorTopN && orderBy != null && orderBy.isSorted()) {
                // handler receives sorted results from collect nodes
                // we can do the sorting with a sorting bucket merger
                handlerProjections.add(
                        projectionBuilder.topNProjection(
                                table.querySpec().outputs(),
                                null, // omit order by
                                table.querySpec().offset(),
                                firstNonNull(table.querySpec().limit(), Constants.DEFAULT_SELECT_LIMIT),
                                table.querySpec().outputs()
                        )
                );
                localMergeNode = PlanNodeBuilder.sortedLocalMerge(
                        handlerProjections, orderBy, table.querySpec().outputs(), null,
                        collectNode, context.plannerContext());
            } else {
                handlerProjections.add(
                        projectionBuilder.topNProjection(
                                collectorTopN ? table.querySpec().outputs() : collectOutputs,
                                orderBy,
                                table.querySpec().offset(),
                                firstNonNull(table.querySpec().limit(), Constants.DEFAULT_SELECT_LIMIT),
                                table.querySpec().outputs()
                        )
                );
                // fallback - unsorted local merge
                localMergeNode = PlanNodeBuilder.localMerge(handlerProjections, collectNode,
                        context.plannerContext());
            }
            return new NonDistributedGroupBy(collectNode, localMergeNode);
        }


    }
}


File: sql/src/main/java/io/crate/planner/consumer/UpdateConsumer.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.planner.consumer;

import com.google.common.collect.ImmutableList;
import io.crate.analyze.UpdateAnalyzedStatement;
import io.crate.analyze.VersionRewriter;
import io.crate.analyze.WhereClause;
import io.crate.analyze.relations.AnalyzedRelation;
import io.crate.analyze.relations.AnalyzedRelationVisitor;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.analyze.relations.TableRelation;
import io.crate.analyze.where.DocKeys;
import io.crate.metadata.PartitionName;
import io.crate.metadata.ReferenceIdent;
import io.crate.metadata.ReferenceInfo;
import io.crate.metadata.table.TableInfo;
import io.crate.operation.aggregation.impl.CountAggregation;
import io.crate.planner.*;
import io.crate.planner.node.NoopPlannedAnalyzedRelation;
import io.crate.planner.node.dml.SymbolBasedUpsertByIdNode;
import io.crate.planner.node.dml.Upsert;
import io.crate.planner.node.dql.CollectAndMerge;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.projection.Projection;
import io.crate.planner.projection.UpdateProjection;
import io.crate.planner.symbol.InputColumn;
import io.crate.planner.symbol.Reference;
import io.crate.planner.symbol.Symbol;
import io.crate.planner.symbol.ValueSymbolVisitor;
import io.crate.types.DataTypes;
import org.elasticsearch.cluster.routing.operation.plain.Preference;
import org.elasticsearch.common.collect.Tuple;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.inject.Singleton;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

@Singleton
public class UpdateConsumer implements Consumer {

    private final Visitor visitor;

    @Inject
    public UpdateConsumer() {
        visitor = new Visitor();
    }

    @Override
    public boolean consume(AnalyzedRelation rootRelation, ConsumerContext context) {
        PlannedAnalyzedRelation plannedAnalyzedRelation = visitor.process(rootRelation, context);
        if (plannedAnalyzedRelation == null) {
            return false;
        }
        context.rootRelation(plannedAnalyzedRelation);
        return true;
    }

    class Visitor extends AnalyzedRelationVisitor<ConsumerContext, PlannedAnalyzedRelation> {

        @Override
        public PlannedAnalyzedRelation visitUpdateAnalyzedStatement(UpdateAnalyzedStatement statement, ConsumerContext context) {
            assert statement.sourceRelation() instanceof TableRelation : "sourceRelation of update statement must be a TableRelation";
            TableRelation tableRelation = (TableRelation) statement.sourceRelation();
            TableInfo tableInfo = tableRelation.tableInfo();

            if (tableInfo.schemaInfo().systemSchema() || tableInfo.rowGranularity() != RowGranularity.DOC) {
                return null;
            }

            List<Plan> childNodes = new ArrayList<>(statement.nestedStatements().size());
            SymbolBasedUpsertByIdNode upsertByIdNode = null;
            for (UpdateAnalyzedStatement.NestedAnalyzedStatement nestedAnalysis : statement.nestedStatements()) {
                WhereClause whereClause = nestedAnalysis.whereClause();
                if (whereClause.noMatch()){
                    continue;
                }
                if (whereClause.docKeys().isPresent()) {
                    if (upsertByIdNode == null) {
                        Tuple<String[], Symbol[]> assignments = convertAssignments(nestedAnalysis.assignments());
                        upsertByIdNode = new SymbolBasedUpsertByIdNode(context.plannerContext().nextExecutionNodeId(), false, statement.nestedStatements().size() > 1, assignments.v1(), null);
                        childNodes.add(new IterablePlan(upsertByIdNode));
                    }
                    upsertById(nestedAnalysis, tableInfo, whereClause, upsertByIdNode);
                } else {
                    Plan plan = upsertByQuery(nestedAnalysis, context, tableInfo, whereClause);
                    if (plan != null) {
                        childNodes.add(plan);
                    }
                }
            }
            if (childNodes.size() > 0){
                return new Upsert(childNodes);
            } else {
                return new NoopPlannedAnalyzedRelation(statement);
            }
        }

        private Plan upsertByQuery(UpdateAnalyzedStatement.NestedAnalyzedStatement nestedAnalysis,
                                   ConsumerContext consumerContext,
                                   TableInfo tableInfo,
                                   WhereClause whereClause) {

            Symbol versionSymbol = null;
            if(whereClause.hasVersions()){
                versionSymbol = VersionRewriter.get(whereClause.query());
                whereClause = new WhereClause(whereClause.query(), whereClause.docKeys().orNull(), whereClause.partitions());
            }


            if (!whereClause.noMatch() || !(tableInfo.isPartitioned() && whereClause.partitions().isEmpty())) {
                // for updates, we always need to collect the `_uid`
                Reference uidReference = new Reference(
                        new ReferenceInfo(
                                new ReferenceIdent(tableInfo.ident(), "_uid"),
                                RowGranularity.DOC, DataTypes.STRING));

                Tuple<String[], Symbol[]> assignments = convertAssignments(nestedAnalysis.assignments());

                Long version = null;
                if (versionSymbol != null){
                    version = ValueSymbolVisitor.LONG.process(versionSymbol);
                }

                UpdateProjection updateProjection = new UpdateProjection(
                        new InputColumn(0, DataTypes.STRING),
                        assignments.v1(),
                        assignments.v2(),
                        version);

                CollectNode collectNode = PlanNodeBuilder.collect(
                        tableInfo,
                        consumerContext.plannerContext(),
                        whereClause,
                        ImmutableList.<Symbol>of(uidReference),
                        ImmutableList.<Projection>of(updateProjection),
                        null,
                        Preference.PRIMARY.type()
                );
                MergeNode mergeNode = PlanNodeBuilder.localMerge(
                        ImmutableList.<Projection>of(CountAggregation.PARTIAL_COUNT_AGGREGATION_PROJECTION), collectNode,
                        consumerContext.plannerContext());
                return new CollectAndMerge(collectNode, mergeNode);
            } else {
                return null;
            }
        }

        private void upsertById(UpdateAnalyzedStatement.NestedAnalyzedStatement nestedAnalysis,
                                             TableInfo tableInfo,
                                             WhereClause whereClause,
                                             SymbolBasedUpsertByIdNode upsertByIdNode) {
            String[] indices = Planner.indices(tableInfo, whereClause);
            assert tableInfo.isPartitioned() || indices.length == 1;

            Tuple<String[], Symbol[]> assignments = convertAssignments(nestedAnalysis.assignments());


            for (DocKeys.DocKey key : whereClause.docKeys().get()) {
                String index;
                if (key.partitionValues().isPresent()) {
                    index = new PartitionName(tableInfo.ident(), key.partitionValues().get()).stringValue();
                } else {
                    index = indices[0];
                }
                upsertByIdNode.add(
                        index,
                        key.id(),
                        key.routing(),
                        assignments.v2(),
                        key.version().orNull());
            }
        }


        private Tuple<String[], Symbol[]> convertAssignments(Map<Reference, Symbol> assignments) {
            String[] assignmentColumns = new String[assignments.size()];
            Symbol[] assignmentSymbols = new Symbol[assignments.size()];
            Iterator<Reference> it = assignments.keySet().iterator();
            int i = 0;
            while(it.hasNext()) {
                Reference key = it.next();
                assignmentColumns[i] = key.ident().columnIdent().fqn();
                assignmentSymbols[i] = assignments.get(key);
                i++;
            }
            return new Tuple<>(assignmentColumns, assignmentSymbols);
        }

        @Override
        protected PlannedAnalyzedRelation visitAnalyzedRelation(AnalyzedRelation relation, ConsumerContext context) {
            return null;
        }
    }
}


File: sql/src/test/java/io/crate/integrationtests/FetchOperationIntegrationTest.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.integrationtests;

import com.carrotsearch.hppc.LongArrayList;
import com.google.common.base.Predicates;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;
import com.google.common.util.concurrent.FutureCallback;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import io.crate.action.job.ContextPreparer;
import io.crate.analyze.Analysis;
import io.crate.analyze.Analyzer;
import io.crate.analyze.ParameterContext;
import io.crate.analyze.WhereClause;
import io.crate.analyze.relations.PlannedAnalyzedRelation;
import io.crate.core.collections.Bucket;
import io.crate.core.collections.Row;
import io.crate.executor.Job;
import io.crate.executor.TaskResult;
import io.crate.executor.transport.NodeFetchRequest;
import io.crate.executor.transport.NodeFetchResponse;
import io.crate.executor.transport.TransportExecutor;
import io.crate.executor.transport.TransportFetchNodeAction;
import io.crate.jobs.JobContextService;
import io.crate.jobs.JobExecutionContext;
import io.crate.metadata.ColumnIdent;
import io.crate.metadata.Functions;
import io.crate.metadata.ReferenceInfo;
import io.crate.metadata.doc.DocSchemaInfo;
import io.crate.metadata.table.TableInfo;
import io.crate.operation.fetch.RowInputSymbolVisitor;
import io.crate.planner.Plan;
import io.crate.planner.Planner;
import io.crate.planner.RowGranularity;
import io.crate.planner.consumer.ConsumerContext;
import io.crate.planner.consumer.QueryThenFetchConsumer;
import io.crate.planner.node.dql.CollectNode;
import io.crate.planner.node.dql.MergeNode;
import io.crate.planner.node.dql.QueryThenFetch;
import io.crate.planner.projection.FetchProjection;
import io.crate.planner.projection.Projection;
import io.crate.planner.symbol.Reference;
import io.crate.planner.symbol.Symbol;
import io.crate.sql.parser.SqlParser;
import io.crate.types.DataType;
import org.apache.lucene.util.BytesRef;
import org.elasticsearch.action.ActionListener;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.*;
import java.util.concurrent.CountDownLatch;

import static org.hamcrest.Matchers.*;
import static org.hamcrest.core.Is.is;

@ElasticsearchIntegrationTest.ClusterScope(numDataNodes = 2)
public class FetchOperationIntegrationTest extends SQLTransportIntegrationTest {

    Setup setup = new Setup(sqlExecutor);
    TransportExecutor executor;
    DocSchemaInfo docSchemaInfo;

    @Before
    public void transportSetUp() {
        executor = internalCluster().getInstance(TransportExecutor.class);
        docSchemaInfo = internalCluster().getInstance(DocSchemaInfo.class);
    }

    @After
    public void transportTearDown() {
        executor = null;
        docSchemaInfo = null;
    }

    private void setUpCharacters() {
        sqlExecutor.exec("create table characters (id int primary key, name string) " +
                "clustered into 2 shards with(number_of_replicas=0)");
        sqlExecutor.ensureYellowOrGreen();
        sqlExecutor.exec("insert into characters (id, name) values (?, ?)",
                new Object[][]{
                        new Object[]{1, "Arthur"},
                        new Object[]{2, "Ford"},
                }
        );
        sqlExecutor.refresh("characters");
    }

    private Plan analyzeAndPlan(String stmt) {
        Analysis analysis = analyze(stmt);
        Planner planner = internalCluster().getInstance(Planner.class);
        return planner.plan(analysis);
    }

    private Analysis analyze(String stmt) {
        Analyzer analyzer = internalCluster().getInstance(Analyzer.class);
        return analyzer.analyze(
                SqlParser.createStatement(stmt),
                new ParameterContext(new Object[0], new Object[0][], null)
        );
    }

    private CollectNode createCollectNode(Planner.Context plannerContext, boolean keepContextForFetcher) {
        TableInfo tableInfo = docSchemaInfo.getTableInfo("characters");

        ReferenceInfo docIdRefInfo = tableInfo.getReferenceInfo(new ColumnIdent("_docid"));
        Symbol docIdRef = new Reference(docIdRefInfo);
        List<Symbol> toCollect = ImmutableList.of(docIdRef);

        List<DataType> outputTypes = new ArrayList<>(toCollect.size());
        for (Symbol symbol : toCollect) {
            outputTypes.add(symbol.valueType());
        }
        CollectNode collectNode = new CollectNode(
                plannerContext.nextExecutionNodeId(),
                "collect",
                tableInfo.getRouting(WhereClause.MATCH_ALL, null));
        collectNode.toCollect(toCollect);
        collectNode.outputTypes(outputTypes);
        collectNode.maxRowGranularity(RowGranularity.DOC);
        collectNode.keepContextForFetcher(keepContextForFetcher);
        collectNode.jobId(UUID.randomUUID());
        plannerContext.allocateJobSearchContextIds(collectNode.routing());

        return collectNode;
    }

    private List<Bucket> getBuckets(CollectNode collectNode) throws InterruptedException, java.util.concurrent.ExecutionException {
        List<Bucket> results = new ArrayList<>();
        for (String nodeName : internalCluster().getNodeNames()) {
            ContextPreparer contextPreparer = internalCluster().getInstance(ContextPreparer.class, nodeName);
            JobContextService contextService = internalCluster().getInstance(JobContextService.class, nodeName);

            JobExecutionContext.Builder builder = contextService.newBuilder(collectNode.jobId());
            ListenableFuture<Bucket> future = contextPreparer.prepare(collectNode.jobId(), collectNode, builder);
            assert future != null;

            JobExecutionContext context = contextService.createContext(builder);
            context.start();
            results.add(future.get());
        }
        return results;
    }

    @Test
    public void testCollectDocId() throws Exception {
        setUpCharacters();
        Planner.Context plannerContext = new Planner.Context(clusterService());
        CollectNode collectNode = createCollectNode(plannerContext, false);

        List<Bucket> results = getBuckets(collectNode);

        assertThat(results.size(), is(2));
        int seenJobSearchContextId = -1;
        for (Bucket rows : results) {
            assertThat(rows.size(), is(1));
            Object docIdCol = rows.iterator().next().get(0);
            assertNotNull(docIdCol);
            assertThat(docIdCol, instanceOf(Long.class));
            long docId = (long)docIdCol;
            // unpack jobSearchContextId and reader doc id from docId
            int jobSearchContextId = (int)(docId >> 32);
            int doc = (int)docId;
            assertThat(doc, is(0));
            assertThat(jobSearchContextId, greaterThan(-1));
            if (seenJobSearchContextId == -1) {
                assertThat(jobSearchContextId, anyOf(is(0), is(1)));
                seenJobSearchContextId = jobSearchContextId;
            } else {
                assertThat(jobSearchContextId, is(seenJobSearchContextId == 0 ? 1 : 0));
            }
        }
    }

    @Test
    public void testFetchAction() throws Exception {
        setUpCharacters();

        Analysis analysis = analyze("select id, name from characters");
        QueryThenFetchConsumer queryThenFetchConsumer = internalCluster().getInstance(QueryThenFetchConsumer.class);
        Planner.Context plannerContext = new Planner.Context(clusterService());
        ConsumerContext consumerContext = new ConsumerContext(analysis.rootRelation(), plannerContext);
        queryThenFetchConsumer.consume(analysis.rootRelation(), consumerContext);

        QueryThenFetch plan = ((QueryThenFetch) ((PlannedAnalyzedRelation) consumerContext.rootRelation()).plan());
        UUID jobId = UUID.randomUUID();
        plan.collectNode().jobId(jobId);

        List<Bucket> results = getBuckets(plan.collectNode());


        TransportFetchNodeAction transportFetchNodeAction = internalCluster().getInstance(TransportFetchNodeAction.class);

        // extract docIds by nodeId and jobSearchContextId
        Map<String, LongArrayList> jobSearchContextDocIds = new HashMap<>();
        for (Bucket rows : results) {
            long docId = (long)rows.iterator().next().get(0);
            // unpack jobSearchContextId and reader doc id from docId
            int jobSearchContextId = (int)(docId >> 32);
            String nodeId = plannerContext.nodeId(jobSearchContextId);
            LongArrayList docIdsPerNode = jobSearchContextDocIds.get(nodeId);
            if (docIdsPerNode == null) {
                docIdsPerNode = new LongArrayList();
                jobSearchContextDocIds.put(nodeId, docIdsPerNode);
            }
            docIdsPerNode.add(docId);
        }

        Iterable<Projection> projections = Iterables.filter(plan.mergeNode().projections(), Predicates.instanceOf(FetchProjection.class));
        FetchProjection fetchProjection = (FetchProjection )Iterables.getOnlyElement(projections);
        RowInputSymbolVisitor rowInputSymbolVisitor = new RowInputSymbolVisitor(internalCluster().getInstance(Functions.class));
        RowInputSymbolVisitor.Context context = rowInputSymbolVisitor.extractImplementations(fetchProjection.outputSymbols());

        final CountDownLatch latch = new CountDownLatch(jobSearchContextDocIds.size());
        final List<Row> rows = new ArrayList<>();
        for (Map.Entry<String, LongArrayList> nodeEntry : jobSearchContextDocIds.entrySet()) {
            NodeFetchRequest nodeFetchRequest = new NodeFetchRequest();
            nodeFetchRequest.jobId(plan.collectNode().jobId());
            nodeFetchRequest.executionNodeId(plan.collectNode().executionNodeId());
            nodeFetchRequest.toFetchReferences(context.references());
            nodeFetchRequest.closeContext(true);
            nodeFetchRequest.jobSearchContextDocIds(nodeEntry.getValue());

            transportFetchNodeAction.execute(nodeEntry.getKey(), nodeFetchRequest, new ActionListener<NodeFetchResponse>() {
                @Override
                public void onResponse(NodeFetchResponse nodeFetchResponse) {
                    for (Row row : nodeFetchResponse.rows()) {
                        rows.add(row);
                    }
                    latch.countDown();
                }

                @Override
                public void onFailure(Throwable e) {
                    latch.countDown();
                    fail(e.getMessage());
                }
            });
        }
        latch.await();

        assertThat(rows.size(), is(2));
        for (Row row : rows) {
            assertThat((Integer) row.get(0), anyOf(is(1), is(2)));
            assertThat((BytesRef) row.get(1), anyOf(is(new BytesRef("Arthur")), is(new BytesRef("Ford"))));
        }
    }

    @Test
    public void testFetchProjection() throws Exception {
        setUpCharacters();

        Plan plan = analyzeAndPlan("select id, name, substr(name, 2) from characters order by id");
        assertThat(plan, instanceOf(QueryThenFetch.class));
        QueryThenFetch qtf = (QueryThenFetch) plan;

        assertThat(qtf.collectNode().keepContextForFetcher(), is(true));
        assertThat(((FetchProjection) qtf.mergeNode().projections().get(1)).jobSearchContextIdToNode(), notNullValue());
        assertThat(((FetchProjection) qtf.mergeNode().projections().get(1)).jobSearchContextIdToShard(), notNullValue());

        Job job = executor.newJob(plan);
        ListenableFuture<List<TaskResult>> results = Futures.allAsList(executor.execute(job));

        final List<Object[]> resultingRows = new ArrayList<>();
        final CountDownLatch latch = new CountDownLatch(1);
        Futures.addCallback(results, new FutureCallback<List<TaskResult>>() {
            @Override
            public void onSuccess(List<TaskResult> resultList) {
                for (Row row : resultList.get(0).rows()) {
                    resultingRows.add(row.materialize());
                }
                latch.countDown();
            }

            @Override
            public void onFailure(Throwable t) {
                latch.countDown();
                fail(t.getMessage());
            }
        });

        latch.await();
        assertThat(resultingRows.size(), is(2));
        assertThat(resultingRows.get(0).length, is(3));
        assertThat((Integer) resultingRows.get(0)[0], is(1));
        assertThat((BytesRef) resultingRows.get(0)[1], is(new BytesRef("Arthur")));
        assertThat((BytesRef) resultingRows.get(0)[2], is(new BytesRef("rthur")));
        assertThat((Integer) resultingRows.get(1)[0], is(2));
        assertThat((BytesRef) resultingRows.get(1)[1], is(new BytesRef("Ford")));
        assertThat((BytesRef) resultingRows.get(1)[2], is(new BytesRef("ord")));
    }

    @Test
    public void testFetchProjectionWithBulkSize() throws Exception {
        /**
         * Setup scenario where more docs per node exists than the configured bulkSize,
         * so multiple request to one node must be done and merged together.
         */
        setup.setUpLocations();
        sqlExecutor.refresh("locations");
        int bulkSize = 2;

        Plan plan = analyzeAndPlan("select position, name from locations order by position");
        assertThat(plan, instanceOf(QueryThenFetch.class));

        rewriteFetchProjectionToBulkSize(bulkSize, ((QueryThenFetch) plan).mergeNode());

        Job job = executor.newJob(plan);
        ListenableFuture<List<TaskResult>> results = Futures.allAsList(executor.execute(job));

        final List<Object[]> resultingRows = new ArrayList<>();
        final CountDownLatch latch = new CountDownLatch(1);
        Futures.addCallback(results, new FutureCallback<List<TaskResult>>() {
            @Override
            public void onSuccess(List<TaskResult> resultList) {
                for (Row row : resultList.get(0).rows()) {
                    resultingRows.add(row.materialize());
                }
                latch.countDown();
            }

            @Override
            public void onFailure(Throwable t) {
                latch.countDown();
                fail(t.getMessage());
            }
        });
        latch.await();

        assertThat(resultingRows.size(), is(13));
        assertThat(resultingRows.get(0).length, is(2));
        assertThat((Integer) resultingRows.get(0)[0], is(1));
        assertThat((Integer) resultingRows.get(12)[0], is(6));
    }

    private void rewriteFetchProjectionToBulkSize(int bulkSize, MergeNode mergeNode) {
        List<Projection> newProjections = new ArrayList<>(mergeNode.projections().size());
        for (Projection projection : mergeNode.projections()) {
            if (projection instanceof FetchProjection) {
                FetchProjection fetchProjection = (FetchProjection) projection;
                newProjections.add(new FetchProjection(
                        fetchProjection.executionNodeId(),
                        fetchProjection.docIdSymbol(),
                        fetchProjection.inputSymbols(),
                        fetchProjection.outputSymbols(),
                        fetchProjection.partitionedBy(),
                        fetchProjection.executionNodes(),
                        bulkSize,
                        fetchProjection.closeContexts(),
                        fetchProjection.jobSearchContextIdToNode(),
                        fetchProjection.jobSearchContextIdToShard()));
            } else {
                newProjections.add(projection);
            }
        }
        mergeNode.projections(newProjections);
    }
}

File: sql/src/test/java/io/crate/integrationtests/TransportSQLActionTest.java
/*
 * Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership.  Crate licenses
 * this file to you under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.  You may
 * obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * However, if you have executed another commercial license agreement
 * with Crate these terms will supersede the license and you may use the
 * software solely pursuant to the terms of the relevant commercial agreement.
 */

package io.crate.integrationtests;

import com.google.common.base.Joiner;
import com.google.common.base.Predicate;
import io.crate.TimestampFormat;
import io.crate.action.sql.SQLActionException;
import io.crate.action.sql.SQLBulkResponse;
import io.crate.executor.TaskResult;
import io.crate.testing.TestingHelpers;
import org.apache.commons.collections.map.HashedMap;
import org.apache.lucene.util.BytesRef;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthStatus;
import org.elasticsearch.action.admin.indices.exists.indices.IndicesExistsRequest;
import org.elasticsearch.common.collect.MapBuilder;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.common.xcontent.XContentFactory;
import org.hamcrest.Matchers;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import javax.annotation.Nullable;
import java.security.Timestamp;
import java.util.*;
import java.util.concurrent.TimeUnit;

import static org.hamcrest.Matchers.*;
import static org.hamcrest.core.Is.is;

public class TransportSQLActionTest extends SQLTransportIntegrationTest {

    private Setup setup = new Setup(sqlExecutor);

    @Rule
    public ExpectedException expectedException = ExpectedException.none();


    private <T> List<T> getCol(Object[][] result, int idx) {
        ArrayList<T> res = new ArrayList<>(result.length);
        for (Object[] row : result) {
            res.add((T) row[idx]);
        }
        return res;
    }

    @Test
    public void testSelectKeepsOrder() throws Exception {
        createIndex("test");
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setSource("{}").execute().actionGet();
        refresh();
        execute("select \"_id\" as b, \"_version\" as a from test");
        assertArrayEquals(new String[]{"b", "a"}, response.cols());
        assertEquals(1, response.rowCount());
        assertThat(response.duration(), greaterThanOrEqualTo(0L));
    }

    @Test
    public void testSelectCountStar() throws Exception {
        execute("create table test (\"type\" string) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into test (name) values (?)", new Object[]{"Arthur"});
        execute("insert into test (name) values (?)", new Object[]{"Trillian"});
        refresh();
        execute("select count(*) from test");
        assertEquals(1, response.rowCount());
        assertEquals(2L, response.rows()[0][0]);
    }

    @Test
    public void testSelectZeroLimit() throws Exception {
        execute("create table test (\"type\" string) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into test (name) values (?)", new Object[]{"Arthur"});
        execute("insert into test (name) values (?)", new Object[]{"Trillian"});
        refresh();
        execute("select * from test limit 0");
        assertEquals(0L, response.rowCount());
    }


    @Test
    public void testSelectCountStarWithWhereClause() throws Exception {
        execute("create table test (name string) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into test (name) values (?)", new Object[]{"Arthur"});
        execute("insert into test (name) values (?)", new Object[]{"Trillian"});
        refresh();
        execute("select count(*) from test where name = 'Trillian'");
        assertEquals(1, response.rowCount());
        assertEquals(1L, response.rows()[0][0]);
    }

    @Test
    public void testSelectStar() throws Exception {
        execute("create table test (\"firstName\" string, \"lastName\" string)");
        waitForRelocation(ClusterHealthStatus.GREEN);
        execute("select * from test");
        assertArrayEquals(new String[]{"firstName", "lastName"}, response.cols());
        assertEquals(0, response.rowCount());
    }

    @Test
    public void testSelectStarEmptyMapping() throws Exception {
        prepareCreate("test").execute().actionGet();
        ensureYellow();
        execute("select * from test");
        assertArrayEquals(new String[]{}, response.cols());
        assertEquals(0, response.rowCount());
    }

    @Test
    public void testGroupByOnAnalyzedColumn() throws Exception {
        expectedException.expect(SQLActionException.class);
        expectedException.expectMessage("Cannot GROUP BY 'test1.col1': grouping on analyzed/fulltext columns is not possible");

        execute("create table test1 (col1 string index using fulltext)");
        ensureYellow();
        execute("insert into test1 (col1) values ('abc def, ghi. jkl')");
        refresh();
        execute("select count(col1) from test1 group by col1");
    }


    @Test
    public void testSelectStarWithOther() throws Exception {
        prepareCreate("test")
                .addMapping("default",
                        "firstName", "type=string",
                        "lastName", "type=string")
                .execute().actionGet();
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setRefresh(true)
                .setSource("{\"firstName\":\"Youri\",\"lastName\":\"Zoon\"}")
                .execute().actionGet();
        execute("select \"_version\", *, \"_id\" from test");
        assertArrayEquals(new String[]{"_version", "firstName", "lastName", "_id"},
                response.cols());
        assertEquals(1, response.rowCount());
        assertArrayEquals(new Object[]{1L, "Youri", "Zoon", "id1"}, response.rows()[0]);
    }

    @Test
    public void testSelectWithParams() throws Exception {
        execute("create table test (first_name string, last_name string, age double) with (number_of_replicas = 0)");
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setRefresh(true)
                .setSource("{\"first_name\":\"Youri\",\"last_name\":\"Zoon\", \"age\": 38}")
                .execute().actionGet();

        Object[] args = new Object[]{"id1"};
        execute("select first_name, last_name from test where \"_id\" = $1", args);
        assertArrayEquals(new Object[]{"Youri", "Zoon"}, response.rows()[0]);

        args = new Object[]{"Zoon"};
        execute("select first_name, last_name from test where last_name = $1", args);
        assertArrayEquals(new Object[]{"Youri", "Zoon"}, response.rows()[0]);

        args = new Object[]{38, "Zoon"};
        execute("select first_name, last_name from test where age = $1 and last_name = $2", args);
        assertArrayEquals(new Object[]{"Youri", "Zoon"}, response.rows()[0]);

        args = new Object[]{38, "Zoon"};
        execute("select first_name, last_name from test where age = ? and last_name = ?", args);
        assertArrayEquals(new Object[]{"Youri", "Zoon"}, response.rows()[0]);
    }

    @Test
    public void testSelectStarWithOtherAndAlias() throws Exception {
        prepareCreate("test")
                .addMapping("default",
                        "firstName", "type=string",
                        "lastName", "type=string")
                .execute().actionGet();
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setRefresh(true)
                .setSource("{\"firstName\":\"Youri\",\"lastName\":\"Zoon\"}")
                .execute().actionGet();
        execute("select *, \"_version\", \"_version\" as v from test");
        assertArrayEquals(new String[]{"firstName", "lastName", "_version", "v"},
                response.cols());
        assertEquals(1, response.rowCount());
        assertArrayEquals(new Object[]{"Youri", "Zoon", 1L, 1L}, response.rows()[0]);
    }

    @Test
    public void testFilterByEmptyString() throws Exception {
        prepareCreate("test")
                .addMapping("default",
                        "name", "type=string,index=not_analyzed")
                .execute().actionGet();
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setRefresh(true)
                .setSource("{\"name\":\"\"}")
                .execute().actionGet();
        client().prepareIndex("test", "default", "id2").setRefresh(true)
                .setSource("{\"name\":\"Ruben Lenten\"}")
                .execute().actionGet();

        execute("select name from test where name = ''");
        assertEquals(1, response.rowCount());
        assertEquals("", response.rows()[0][0]);

        execute("select name from test where name != ''");
        assertEquals(1, response.rowCount());
        assertEquals("Ruben Lenten", response.rows()[0][0]);

    }

    @Test
    public void testFilterByNull() throws Exception {
        execute("create table test (name string, o object(ignored))");
        ensureYellow();

        client().prepareIndex("test", "default", "id1").setRefresh(true)
                .setSource("{}")
                .execute().actionGet();
        client().prepareIndex("test", "default", "id2").setRefresh(true)
                .setSource("{\"name\":\"Ruben Lenten\"}")
                .execute().actionGet();
        client().prepareIndex("test", "default", "id3").setRefresh(true)
                .setSource("{\"name\":\"\"}")
                .execute().actionGet();

        execute("select \"_id\" from test where name is null");
        assertEquals(1, response.rowCount());
        assertEquals("id1", response.rows()[0][0]);

        execute("select \"_id\" from test where name is not null order by \"_uid\"");
        assertEquals(2, response.rowCount());
        assertEquals("id2", response.rows()[0][0]);

        // missing field of ignored object is null returns no match, so we cannot filter by it
        execute("select \"_id\" from test where o['invalid'] is null");
        assertEquals(0, response.rowCount());

        execute("select name from test where name is not null and name!=''");
        assertEquals(1, response.rowCount());
        assertEquals("Ruben Lenten", response.rows()[0][0]);

    }

    @Test
    public void testFilterByBoolean() throws Exception {
        prepareCreate("test")
                .addMapping("default",
                        "sunshine", "type=boolean,index=not_analyzed")
                .execute().actionGet();
        ensureYellow();

        execute("insert into test values (?)", new Object[]{true});
        refresh();

        execute("select sunshine from test where sunshine = true");
        assertEquals(1, response.rowCount());
        assertEquals(true, response.rows()[0][0]);

        execute("update test set sunshine=false where sunshine = true");
        assertEquals(1, response.rowCount());
        refresh();

        execute("select sunshine from test where sunshine = ?", new Object[]{false});
        assertEquals(1, response.rowCount());
        assertEquals(false, response.rows()[0][0]);
    }


    /**
     * Queries are case sensitive by default, however column names without quotes are converted
     * to lowercase which is the same behaviour as in postgres
     * see also http://www.thenextage.com/wordpress/postgresql-case-sensitivity-part-1-the-ddl/
     *
     * @throws Exception
     */
    @Test
    public void testColsAreCaseSensitive() throws Exception {
        execute("create table test (\"firstname\" string, \"firstName\" string) " +
                "with (number_of_replicas = 0)");
        ensureYellow();
        execute("insert into test (\"firstname\", \"firstName\") values ('LowerCase', 'CamelCase')");
        refresh();

        execute("select FIRSTNAME, \"firstname\", \"firstName\" from test");
        assertArrayEquals(new String[]{"firstname", "firstname", "firstName"}, response.cols());
        assertEquals(1, response.rowCount());
        assertEquals("LowerCase", response.rows()[0][0]);
        assertEquals("LowerCase", response.rows()[0][1]);
        assertEquals("CamelCase", response.rows()[0][2]);
    }


    @Test
    public void testIdSelectWithResult() throws Exception {
        createIndex("test");
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setSource("{}").execute().actionGet();
        refresh();
        execute("select \"_id\" from test");
        assertArrayEquals(new String[]{"_id"}, response.cols());
        assertEquals(1, response.rowCount());
        assertEquals(1, response.rows()[0].length);
        assertEquals("id1", response.rows()[0][0]);
    }

    @Test
    public void testDelete() throws Exception {
        createIndex("test");
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setSource("{}").execute().actionGet();
        refresh();
        execute("delete from test");
        assertEquals(-1, response.rowCount());
        assertThat(response.duration(), greaterThanOrEqualTo(0L));
        execute("select \"_id\" from test");
        assertEquals(0, response.rowCount());
    }

    @Test
    public void testDeleteWithWhere() throws Exception {
        createIndex("test");
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setSource("{}").execute().actionGet();
        client().prepareIndex("test", "default", "id2").setSource("{}").execute().actionGet();
        client().prepareIndex("test", "default", "id3").setSource("{}").execute().actionGet();
        refresh();
        execute("delete from test where \"_id\" = 'id1'");
        assertEquals(1, response.rowCount());
        refresh();
        execute("select \"_id\" from test");
        assertEquals(2, response.rowCount());
    }

    @Test
    public void testSqlRequestWithLimit() throws Exception {
        createIndex("test");
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setSource("{}").execute().actionGet();
        client().prepareIndex("test", "default", "id2").setSource("{}").execute().actionGet();
        refresh();
        execute("select \"_id\" from test limit 1");
        assertEquals(1, response.rowCount());
    }


    @Test
    public void testSqlRequestWithLimitAndOffset() throws Exception {
        execute("create table test (id string primary key) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into test (id) values (?), (?), (?)", new Object[]{"id1", "id2", "id3"});
        refresh();
        execute("select \"id\" from test order by id limit 1 offset 1");
        assertEquals(1, response.rowCount());
        assertThat((String)response.rows()[0][0], is("id2"));
    }


    @Test
    public void testSqlRequestWithFilter() throws Exception {
        createIndex("test");
        ensureYellow();
        client().prepareIndex("test", "default", "id1").setSource("{}").execute().actionGet();
        client().prepareIndex("test", "default", "id2").setSource("{}").execute().actionGet();
        refresh();
        execute("select _id from test where _id='id1'");
        assertEquals(1, response.rowCount());
        assertEquals("id1", response.rows()[0][0]);
    }

    @Test
    public void testSqlRequestWithNotEqual() throws Exception {
        execute("create table test (id string primary key) with (number_of_replicas = 0)");
        ensureYellow();
        execute("insert into test (id) values (?)", new Object[][] {
                new Object[] { "id1" },
                new Object[] { "id2" }
        });
        refresh();
        execute("select id from test where id != 'id1'");
        assertEquals(1, response.rowCount());
        assertEquals("id2", response.rows()[0][0]);
    }


    @Test
    public void testSqlRequestWithOneOrFilter() throws Exception {
        execute("create table test (id string) with (number_of_replicas = 0)");
        ensureYellow();
        execute("insert into test (id) values ('id1'), ('id2'), ('id3')");
        refresh();
        execute("select id from test where id='id1' or id='id3'");
        assertEquals(2, response.rowCount());
        assertThat(this.<String>getCol(response.rows(), 0), containsInAnyOrder("id1", "id3"));
    }

    @Test
    public void testSqlRequestWithOneMultipleOrFilter() throws Exception {
        execute("create table test (id string) with (number_of_replicas = 0)");
        ensureYellow();
        execute("insert into test (id) values ('id1'), ('id2'), ('id3'), ('id4')");
        refresh();
        execute("select id from test where id='id1' or id='id2' or id='id4'");
        assertEquals(3, response.rowCount());
        List<String> col1 = this.getCol(response.rows(), 0);
        assertThat(col1, containsInAnyOrder("id1", "id2", "id4"));
    }

    @Test
    public void testSqlRequestWithDateFilter() throws Exception {
        prepareCreate("test")
                .addMapping("default", XContentFactory.jsonBuilder()
                        .startObject()
                        .startObject("default")
                        .startObject("properties")
                        .startObject("date")
                        .field("type", "date")
                        .endObject()
                        .endObject()
                        .endObject().endObject())
                .execute().actionGet();
        ensureYellow();
        client().prepareIndex("test", "default", "id1")
                .setSource("{\"date\": " +
                        TimestampFormat.parseTimestampString("2013-10-01") + "}")
                .execute().actionGet();
        client().prepareIndex("test", "default", "id2")
                .setSource("{\"date\": " +
                        TimestampFormat.parseTimestampString("2013-10-02") + "}")
                .execute().actionGet();
        refresh();
        execute(
                "select date from test where date = '2013-10-01'");
        assertEquals(1, response.rowCount());
        assertEquals(1380585600000L, response.rows()[0][0]);
    }

    @Test
    public void testSqlRequestWithDateGtFilter() throws Exception {
        prepareCreate("test")
                .addMapping("default",
                        "date", "type=date")
                .execute().actionGet();
        ensureYellow();
        client().prepareIndex("test", "default", "id1")
                .setSource("{\"date\": " +
                        TimestampFormat.parseTimestampString("2013-10-01") + "}")
                .execute().actionGet();
        client().prepareIndex("test", "default", "id2")
                .setSource("{\"date\":" +
                        TimestampFormat.parseTimestampString("2013-10-02") + "}")
                .execute().actionGet();
        refresh();
        execute(
                "select date from test where date > '2013-10-01'");
        assertEquals(1, response.rowCount());
        assertEquals(1380672000000L, response.rows()[0][0]);
    }

    @Test
    public void testSqlRequestWithNumericGtFilter() throws Exception {
        prepareCreate("test")
                .addMapping("default",
                        "i", "type=long")
                .execute().actionGet();
        ensureYellow();
        client().prepareIndex("test", "default", "id1")
                .setSource("{\"i\":10}")
                .execute().actionGet();
        client().prepareIndex("test", "default", "id2")
                .setSource("{\"i\":20}")
                .execute().actionGet();
        refresh();
        execute(
                "select i from test where i > 10");
        assertEquals(1, response.rowCount());
        assertEquals(20L, response.rows()[0][0]);
    }


    @Test
    @SuppressWarnings("unchecked")
    public void testArraySupport() throws Exception {
        execute("create table t1 (id int primary key, strings array(string), integers array(integer)) with (number_of_replicas=0)");
        ensureYellow();

        execute("insert into t1 (id, strings, integers) values (?, ?, ?)",
                new Object[]{
                        1,
                        new String[]{"foo", "bar"},
                        new Integer[]{1, 2, 3}
                }
        );
        refresh();

        execute("select id, strings, integers from t1");
        assertThat(response.rowCount(), is(1L));
        assertThat((Integer) response.rows()[0][0], is(1));
        assertThat(((String) ((Object[]) response.rows()[0][1])[0]), is("foo"));
        assertThat(((String) ((Object[]) response.rows()[0][1])[1]), is("bar"));
        assertThat(((Integer) ((Object[]) response.rows()[0][2])[0]), is(1));
        assertThat(((Integer) ((Object[]) response.rows()[0][2])[1]), is(2));
        assertThat(((Integer) ((Object[]) response.rows()[0][2])[2]), is(3));
    }

    @Test
    @SuppressWarnings("unchecked")
    public void testArrayInsideObject() throws Exception {
        execute("create table t1 (id int primary key, details object as (names array(string))) with (number_of_replicas=0)");
        ensureYellow();

        Map<String, Object> details = new HashMap<>();
        details.put("names", new Object[]{"Arthur", "Trillian"});
        execute("insert into t1 (id, details) values (?, ?)", new Object[]{1, details});
        refresh();

        execute("select details['names'] from t1");
        assertThat(response.rowCount(), is(1L));
        assertThat(((String) ((Object[]) response.rows()[0][0])[0]), is("Arthur"));
        assertThat(((String) ((Object[]) response.rows()[0][0])[1]), is("Trillian"));
    }

    @Test
    public void testArrayInsideObjectArray() throws Exception {
        execute("create table t1 (id int primary key, details array(object as (names array(string)))) with (number_of_replicas=0)");
        ensureYellow();

        Map<String, Object> detail1 = new HashMap<>();
        detail1.put("names", new Object[]{"Arthur", "Trillian"});

        Map<String, Object> detail2 = new HashMap<>();
        detail2.put("names", new Object[]{"Ford", "Slarti"});

        List<Map<String, Object>> details = Arrays.asList(detail1, detail2);

        execute("insert into t1 (id, details) values (?, ?)", new Object[]{1, details});
        refresh();

        expectedException.expect(SQLActionException.class);
        expectedException.expectMessage("cannot query for arrays inside object arrays explicitly");

        execute("select details['names'] from t1");

    }

    @Test
    public void testFullPathRequirement() throws Exception {
        // verifies that the "fullPath" setting in the es mapping is no longer required
        execute("create table t1 (id int primary key, details object as (id int, more_details object as (id int))) with (number_of_replicas=0)");
        ensureYellow();

        Map<String, Object> more_details = new HashMap<>();
        more_details.put("id", 2);

        Map<String, Object> details = new HashMap<>();
        details.put("id", 1);
        details.put("more_details", more_details);

        execute("insert into t1 (id, details) values (2, ?)", new Object[]{details});
        execute("refresh table t1");

        execute("select details from t1 where details['id'] = 2");
        assertThat(response.rowCount(), is(0L));
    }

    @Test
    @SuppressWarnings("unchecked")
    public void testArraySupportWithNullValues() throws Exception {
        execute("create table t1 (id int primary key, strings array(string)) with (number_of_replicas=0)");
        ensureYellow();

        execute("insert into t1 (id, strings) values (?, ?)",
                new Object[]{
                        1,
                        new String[]{"foo", null, "bar"},
                }
        );
        refresh();

        execute("select id, strings from t1");
        assertThat(response.rowCount(), is(1L));
        assertThat((Integer) response.rows()[0][0], is(1));
        assertThat(((String) ((Object[]) response.rows()[0][1])[0]), is("foo"));
        assertThat(((Object[]) response.rows()[0][1])[1], nullValue());
        assertThat(((String) ((Object[]) response.rows()[0][1])[2]), is("bar"));
    }

    @Test
    public void testObjectArrayInsertAndSelect() throws Exception {
        execute("create table t1 (" +
                "  id int primary key, " +
                "  objects array(" +
                "   object as (" +
                "     name string, " +
                "     age int" +
                "   )" +
                "  )" +
                ") with (number_of_replicas=0)");
        ensureYellow();

        Map<String, Object> obj1 = new MapBuilder<String, Object>().put("name", "foo").put("age", 1).map();
        Map<String, Object> obj2 = new MapBuilder<String, Object>().put("name", "bar").put("age", 2).map();

        Object[] args = new Object[]{1, new Object[]{obj1, obj2}};
        execute("insert into t1 (id, objects) values (?, ?)", args);
        refresh();

        execute("select objects from t1");
        assertThat(response.rowCount(), is(1L));

        Object[] objResults = ((Object[]) response.rows()[0][0]);
        Map<String, Object> obj1Result = ((Map) objResults[0]);
        assertThat((String) obj1Result.get("name"), is("foo"));
        assertThat((Integer) obj1Result.get("age"), is(1));

        Map<String, Object> obj2Result = ((Map) objResults[1]);
        assertThat((String) obj2Result.get("name"), is("bar"));
        assertThat((Integer) obj2Result.get("age"), is(2));

        execute("select objects['name'] from t1");
        assertThat(response.rowCount(), is(1L));

        String[] names = Arrays.copyOf(((Object[]) response.rows()[0][0]), 2, String[].class);
        assertThat(names[0], is("foo"));
        assertThat(names[1], is("bar"));

        execute("select objects['name'] from t1 where ? = ANY (objects['name'])", new Object[]{"foo"});
        assertThat(response.rowCount(), is(1L));
    }

    @Test
    public void testGetResponseWithObjectColumn() throws Exception {
        XContentBuilder mapping = XContentFactory.jsonBuilder().startObject()
                .startObject("default")
                .startObject("_meta").field("primary_keys", "id").endObject()
                .startObject("properties")
                .startObject("id")
                .field("type", "string")
                .field("index", "not_analyzed")
                .endObject()
                .startObject("data")
                .field("type", "object")
                .field("index", "not_analyzed")
                .field("dynamic", false)
                .endObject()
                .endObject()
                .endObject()
                .endObject();

        prepareCreate("test")
                .addMapping("default", mapping)
                .execute().actionGet();
        ensureYellow();

        Map<String, Object> data = new HashMap<>();
        data.put("foo", "bar");
        execute("insert into test (id, data) values (?, ?)", new Object[]{"1", data});
        refresh();

        execute("select data from test where id = ?", new Object[]{"1"});
        assertEquals(data, response.rows()[0][0]);
    }

    @Test
    public void testSelectToGetRequestByPlanner() throws Exception {
        this.setup.createTestTableWithPrimaryKey();

        execute("insert into test (pk_col, message) values ('124', 'bar1')");
        assertEquals(1, response.rowCount());
        refresh();
        waitNoPendingTasksOnAll(); // wait for mapping update as foo is being added

        execute("select pk_col, message from test where pk_col='124'");
        assertEquals(1, response.rowCount());
        assertEquals("124", response.rows()[0][0]);
        assertThat(response.duration(), greaterThanOrEqualTo(0L));
    }

    @Test
    public void testDeleteToDeleteRequestByPlanner() throws Exception {
        this.setup.createTestTableWithPrimaryKey();

        execute("insert into test (pk_col, message) values ('123', 'bar')");
        assertEquals(1, response.rowCount());
        refresh();

        execute("delete from test where pk_col='123'");
        assertEquals(1, response.rowCount());
        assertThat(response.duration(), greaterThanOrEqualTo(0L));
        refresh();

        execute("select * from test where pk_col='123'");
        assertEquals(0, response.rowCount());
    }

    @Test
    public void testSelectToRoutedRequestByPlanner() throws Exception {
        this.setup.createTestTableWithPrimaryKey();

        execute("insert into test (pk_col, message) values ('1', 'foo')");
        execute("insert into test (pk_col, message) values ('2', 'bar')");
        execute("insert into test (pk_col, message) values ('3', 'baz')");
        refresh();

        execute("SELECT * FROM test WHERE pk_col='1' OR pk_col='2'");
        assertEquals(2, response.rowCount());
        assertThat(response.duration(), greaterThanOrEqualTo(0L));

        execute("SELECT * FROM test WHERE pk_col=? OR pk_col=?", new Object[]{"1", "2"});
        assertEquals(2, response.rowCount());

        awaitBusy(new Predicate<Object>() {
            @Override
            public boolean apply(@Nullable Object input) {
                execute("SELECT * FROM test WHERE (pk_col=? OR pk_col=?) OR pk_col=?", new Object[]{"1", "2", "3"});
                return response.rowCount() == 3
                        && Joiner.on(',').join(Arrays.asList(response.cols())).equals("message,pk_col");
            }
        }, 10, TimeUnit.SECONDS);

    }

    @Test
    public void testSelectToRoutedRequestByPlannerMissingDocuments() throws Exception {
        this.setup.createTestTableWithPrimaryKey();

        execute("insert into test (pk_col, message) values ('1', 'foo')");
        execute("insert into test (pk_col, message) values ('2', 'bar')");
        execute("insert into test (pk_col, message) values ('3', 'baz')");
        refresh();

        execute("SELECT pk_col, message FROM test WHERE pk_col='4' OR pk_col='3'");
        assertEquals(1, response.rowCount());
        assertThat(Arrays.asList(response.rows()[0]), hasItems(new Object[]{"3", "baz"}));
        assertThat(response.duration(), greaterThanOrEqualTo(0L));

        execute("SELECT pk_col, message FROM test WHERE pk_col='4' OR pk_col='99'");
        assertEquals(0, response.rowCount());
    }

    @Test
    public void testSelectToRoutedRequestByPlannerWhereIn() throws Exception {
        this.setup.createTestTableWithPrimaryKey();

        execute("insert into test (pk_col, message) values ('1', 'foo')");
        execute("insert into test (pk_col, message) values ('2', 'bar')");
        execute("insert into test (pk_col, message) values ('3', 'baz')");
        refresh();

        execute("SELECT * FROM test WHERE pk_col IN (?,?,?)", new Object[]{"1", "2", "3"});
        assertEquals(3, response.rowCount());
        assertThat(response.duration(), greaterThanOrEqualTo(0L));
    }

    @Test
    public void testDeleteToRoutedRequestByPlannerWhereIn() throws Exception {
        this.setup.createTestTableWithPrimaryKey();

        execute("insert into test (pk_col, message) values ('1', 'foo')");
        execute("insert into test (pk_col, message) values ('2', 'bar')");
        execute("insert into test (pk_col, message) values ('3', 'baz')");
        refresh();

        execute("DELETE FROM test WHERE pk_col IN (?, ?, ?)", new Object[]{"1", "2", "4"});
        assertThat(response.duration(), greaterThanOrEqualTo(0L));
        refresh();

        execute("SELECT pk_col FROM test");
        assertThat(response.rowCount(), is(1L));
        assertEquals(response.rows()[0][0], "3");

    }


    @Test
    public void testDeleteToRoutedRequestByPlannerWhereOr() throws Exception {
        this.setup.createTestTableWithPrimaryKey();
        execute("insert into test (pk_col, message) values ('1', 'foo'), ('2', 'bar'), ('3', 'baz')");
        refresh();
        execute("DELETE FROM test WHERE pk_col=? or pk_col=? or pk_col=?", new Object[]{"1", "2", "4"});
        assertThat(response.duration(), greaterThanOrEqualTo(0L));
        refresh();
        execute("SELECT pk_col FROM test");
        assertThat(response.rowCount(), is(1L));
        assertEquals(response.rows()[0][0], "3");
    }

    @Test
    public void testUpdateToRoutedRequestByPlannerWhereOr() throws Exception {
        this.setup.createTestTableWithPrimaryKey();
        execute("insert into test (pk_col, message) values ('1', 'foo'), ('2', 'bar'), ('3', 'baz')");
        refresh();
        execute("update test set message='new' WHERE pk_col='1' or pk_col='2' or pk_col='4'");
        assertThat(response.rowCount(), is(2L));
        assertThat(response.duration(), greaterThanOrEqualTo(0L));
        refresh();
        execute("SELECT distinct message FROM test");
        assertThat(response.rowCount(), is(2L));
    }

    @Test
    public void testSelectWithWhereLike() throws Exception {
        this.setup.groupBySetup();

        execute("select name from characters where name like '%ltz'");
        assertEquals(2L, response.rowCount());

        execute("select count(*) from characters where name like 'Jeltz'");
        assertEquals(1L, response.rows()[0][0]);

        execute("select count(*) from characters where race like '%o%'");
        assertEquals(3L, response.rows()[0][0]);

        Map<String, Object> emptyMap = new HashMap<>();
        Map<String, Object> details = new HashMap<>();
        details.put("age", 30);
        details.put("job", "soldier");
        execute("insert into characters (race, gender, name, details) values (?, ?, ?, ?)",
                new Object[]{"Vo*", "male", "Kwaltzz", emptyMap}
        );
        execute("insert into characters (race, gender, name, details) values (?, ?, ?, ?)",
                new Object[]{"Vo?", "male", "Kwaltzzz", emptyMap}
        );
        execute("insert into characters (race, gender, name, details) values (?, ?, ?, ?)",
                new Object[]{"Vo!", "male", "Kwaltzzzz", details}
        );
        execute("insert into characters (race, gender, name, details) values (?, ?, ?, ?)",
                new Object[]{"Vo%", "male", "Kwaltzzzz", details}
        );
        refresh();

        execute("select race from characters where race like 'Vo*'");
        assertEquals(1L, response.rowCount());
        assertEquals("Vo*", response.rows()[0][0]);

        execute("select race from characters where race like ?", new Object[]{"Vo?"});
        assertEquals(1L, response.rowCount());
        assertEquals("Vo?", response.rows()[0][0]);

        execute("select race from characters where race like 'Vo!'");
        assertEquals(1L, response.rowCount());
        assertEquals("Vo!", response.rows()[0][0]);

        execute("select race from characters where race like 'Vo\\%'");
        assertEquals(1L, response.rowCount());
        assertEquals("Vo%", response.rows()[0][0]);

        execute("select race from characters where race like 'Vo_'");
        assertEquals(4L, response.rowCount());

        execute("select race from characters where details['job'] like 'sol%'");
        assertEquals(2L, response.rowCount());
    }

    @Test
    public void testSelectMatch() throws Exception {
        execute("create table quotes (quote string)");
        ensureYellow();
        assertTrue(client().admin().indices().exists(new IndicesExistsRequest("quotes"))
                .actionGet().isExists());

        execute("insert into quotes values (?)", new Object[]{"don't panic"});
        refresh();

        execute("select quote from quotes where match(quote, ?)", new Object[]{"don't panic"});
        assertEquals(1L, response.rowCount());
        assertEquals("don't panic", response.rows()[0][0]);

    }

    @Test
    public void testSelectNotMatch() throws Exception {
        execute("create table quotes (quote string) with (number_of_replicas = 0)");
        ensureYellow();
        assertTrue(client().admin().indices().exists(new IndicesExistsRequest("quotes"))
                .actionGet().isExists());

        execute("insert into quotes values (?), (?)", new Object[]{"don't panic", "hello"});
        refresh();

        execute("select quote from quotes where not match(quote, ?)",
                new Object[]{"don't panic"});
        assertEquals(1L, response.rowCount());
        assertEquals("hello", response.rows()[0][0]);
    }

    @Test
    public void testSelectOrderByScore() throws Exception {
        execute("create table quotes (quote string index off," +
                "index quote_ft using fulltext(quote))");
        ensureYellow();
        execute("insert into quotes values (?)",
                new Object[]{"Would it save you a lot of time if I just gave up and went mad now?"}
        );
        execute("insert into quotes values (?)",
                new Object[]{"Time is an illusion. Lunchtime doubly so"}
        );
        refresh();

        execute("select * from quotes");
        execute("select quote, \"_score\" from quotes where match(quote_ft, ?) " +
                        "order by \"_score\" desc",
                new Object[]{"time", "time"}
        );
        assertEquals(2L, response.rowCount());
        assertEquals("Time is an illusion. Lunchtime doubly so", response.rows()[0][0]);
    }

    @Test
    public void testSelectScoreMatchAll() throws Exception {
        execute("create table quotes (quote string) with (number_of_replicas = 0)");
        ensureYellow();
        assertTrue(client().admin().indices().exists(new IndicesExistsRequest("quotes"))
                .actionGet().isExists());

        execute("insert into quotes values (?), (?)",
                new Object[]{"Would it save you a lot of time if I just gave up and went mad now?",
                        "Time is an illusion. Lunchtime doubly so"}
        );
        refresh();

        execute("select quote, \"_score\" from quotes");
        assertEquals(2L, response.rowCount());
        assertEquals(1.0f, response.rows()[0][1]);
        assertEquals(1.0f, response.rows()[1][1]);
    }

    @Test
    public void testSelectWhereScore() throws Exception {
        execute("create table quotes (quote string, " +
                "index quote_ft using fulltext(quote)) with (number_of_replicas = 0)");
        ensureYellow();
        assertTrue(client().admin().indices().exists(new IndicesExistsRequest("quotes"))
                .actionGet().isExists());

        execute("insert into quotes values (?), (?)",
                new Object[]{"Would it save you a lot of time if I just gave up and went mad now?",
                        "Time is an illusion. Lunchtime doubly so. Take your time."}
        );
        refresh();

        execute("select quote, \"_score\" from quotes where match(quote_ft, 'time') " +
                "and \"_score\" >= 0.98");
        assertEquals(1L, response.rowCount());
        assertThat((Float) response.rows()[0][1], greaterThanOrEqualTo(0.98f));
    }

    @Test
    public void testSelectMatchAnd() throws Exception {
        execute("create table quotes (id int, quote string, " +
                "index quote_fulltext using fulltext(quote) with (analyzer='english')) with (number_of_replicas = 0)");
        ensureYellow();
        assertTrue(client().admin().indices().exists(new IndicesExistsRequest("quotes"))
                .actionGet().isExists());

        execute("insert into quotes (id, quote) values (?, ?), (?, ?)",
                new Object[]{
                        1, "Would it save you a lot of time if I just gave up and went mad now?",
                        2, "Time is an illusion. Lunchtime doubly so"}
        );
        refresh();

        execute("select quote from quotes where match(quote_fulltext, 'time') and id = 1");
        assertEquals(1L, response.rowCount());
    }

    private void nonExistingColumnSetup() {
        execute("create table quotes (" +
                "id integer primary key, " +
                "quote string index off, " +
                "o object(ignored), " +
                "index quote_fulltext using fulltext(quote) with (analyzer='snowball')" +
                ") clustered by (id) into 3 shards with (number_of_replicas = 0)");
        ensureYellow();
        execute("insert into quotes (id, quote) values (1, '\"Nothing particularly exciting," +
                "\" it admitted, \"but they are alternatives.\"')");
        execute("insert into quotes (id, quote) values (2, '\"Have another drink," +
                "\" said Trillian. \"Enjoy yourself.\"')");
        refresh();
    }

    @Test
    public void selectNonExistingColumn() throws Exception {
        nonExistingColumnSetup();
        execute("select o['notExisting'] from quotes");
        assertEquals(2L, response.rowCount());
        assertEquals("o['notExisting']", response.cols()[0]);
        assertNull(response.rows()[0][0]);
        assertNull(response.rows()[1][0]);
    }

    @Test
    public void selectNonExistingAndExistingColumns() throws Exception {
        nonExistingColumnSetup();
        execute("select o['unknown'], id from quotes order by id asc");
        assertEquals(2L, response.rowCount());
        assertEquals("o['unknown']", response.cols()[0]);
        assertEquals("id", response.cols()[1]);
        assertNull(response.rows()[0][0]);
        assertEquals(1, response.rows()[0][1]);
        assertNull(response.rows()[1][0]);
        assertEquals(2, response.rows()[1][1]);
    }

    @Test
    public void selectWhereNonExistingColumn() throws Exception {
        nonExistingColumnSetup();
        execute("select * from quotes where o['something'] > 0");
        assertEquals(0L, response.rowCount());
    }

    @Test
    public void selectWhereDynamicColumnIsNull() throws Exception {
        nonExistingColumnSetup();
        // dynamic references type is undefined, so we just don't know if it matches
        execute("select * from quotes where o['something'] IS NULL");
        assertEquals(0, response.rowCount());
    }

    @Test
    public void selectWhereNonExistingColumnWhereIn() throws Exception {
        nonExistingColumnSetup();
        execute("select * from quotes where o['something'] IN(1,2,3)");
        assertEquals(0L, response.rowCount());
    }

    @Test
    public void selectWhereNonExistingColumnLike() throws Exception {
        nonExistingColumnSetup();
        execute("select * from quotes where o['something'] Like '%bla'");
        assertEquals(0L, response.rowCount());
    }

    @Test
    public void selectWhereNonExistingColumnMatchFunction() throws Exception {
        nonExistingColumnSetup();

        expectedException.expect(SQLActionException.class);
        expectedException.expectMessage("Can only use MATCH on columns of type STRING, not on 'null'");

        execute("select * from quotes where match(o['something'], 'bla')");
    }

    @Test
    public void testSelectCountDistinctZero() throws Exception {
        execute("create table test (col1 int) with (number_of_replicas=0)");
        ensureYellow();

        execute("select count(distinct col1) from test");

        assertEquals(1, response.rowCount());
        assertEquals(0L, response.rows()[0][0]);
    }

    @Test
    public void testRefresh() throws Exception {
        execute("create table test (id int primary key, name string)");
        ensureYellow();
        execute("insert into test (id, name) values (0, 'Trillian'), (1, 'Ford'), (2, 'Zaphod')");
        execute("select count(*) from test");
        assertThat((Long) response.rows()[0][0], lessThan(3L));

        execute("refresh table test");
        assertFalse(response.hasRowCount());
        assertThat(response.rows(), is(TaskResult.EMPTY_OBJS));

        execute("select count(*) from test");
        assertThat((Long) response.rows()[0][0], is(3L));
    }

    @Test
    public void testInsertSelectWithClusteredBy() throws Exception {
        execute("create table quotes (id integer, quote string) clustered by(id) " +
                "with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into quotes (id, quote) values(?, ?)",
                new Object[]{1, "I'd far rather be happy than right any day."});
        assertEquals(1L, response.rowCount());
        refresh();

        execute("select \"_id\", id, quote from quotes where id=1");
        assertEquals(1L, response.rowCount());

        // Validate generated _id, must be: <generatedRandom>
        assertNotNull(response.rows()[0][0]);
        assertThat(((String) response.rows()[0][0]).length(), greaterThan(0));
    }

    @Test
    public void testInsertSelectWithAutoGeneratedId() throws Exception {
        execute("create table quotes (id integer, quote string)" +
                "with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into quotes (id, quote) values(?, ?)",
                new Object[]{1, "I'd far rather be happy than right any day."});
        assertEquals(1L, response.rowCount());
        refresh();

        execute("select \"_id\", id, quote from quotes where id=1");
        assertEquals(1L, response.rowCount());

        // Validate generated _id, must be: <generatedRandom>
        assertNotNull(response.rows()[0][0]);
        assertThat(((String) response.rows()[0][0]).length(), greaterThan(0));
    }

    @Test
    public void testInsertSelectWithPrimaryKey() throws Exception {
        execute("create table quotes (id integer primary key, quote string)" +
                "with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into quotes (id, quote) values(?, ?)",
                new Object[]{1, "I'd far rather be happy than right any day."});
        assertEquals(1L, response.rowCount());
        refresh();

        execute("select \"_id\", id, quote from quotes where id=1");
        assertEquals(1L, response.rowCount());

        // Validate generated _id.
        // Must equal to id because its the primary key
        String _id = (String) response.rows()[0][0];
        Integer id = (Integer) response.rows()[0][1];
        assertEquals(id.toString(), _id);
    }

    @Test
    public void testInsertSelectWithMultiplePrimaryKey() throws Exception {
        execute("create table quotes (id integer primary key, author string primary key, " +
                "quote string) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into quotes (id, author, quote) values(?, ?, ?)",
                new Object[]{1, "Ford", "I'd far rather be happy than right any day."});
        assertEquals(1L, response.rowCount());
        refresh();

        execute("select \"_id\", id from quotes where id=1 and author='Ford'");
        assertEquals(1L, response.rowCount());
        assertThat((String) response.rows()[0][0], is("AgExBEZvcmQ="));
        assertThat((Integer) response.rows()[0][1], is(1));
    }

    @Test
    public void testInsertSelectWithMultiplePrimaryKeyAndClusteredBy() throws Exception {
        execute("create table quotes (id integer primary key, author string primary key, " +
                "quote string) clustered by(author) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into quotes (id, author, quote) values(?, ?, ?)",
                new Object[]{1, "Ford", "I'd far rather be happy than right any day."});
        assertEquals(1L, response.rowCount());
        refresh();

        execute("select \"_id\", id from quotes where id=1 and author='Ford'");
        assertEquals(1L, response.rowCount());
        assertThat((String) response.rows()[0][0], is("AgRGb3JkATE="));
        assertThat((Integer) response.rows()[0][1], is(1));
    }

    @Test
    public void testInsertSelectWithMultiplePrimaryOnePkSame() throws Exception {
        execute("create table quotes (id integer primary key, author string primary key, " +
                "quote string) clustered by(author) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into quotes (id, author, quote) values (?, ?, ?), (?, ?, ?)",
                new Object[]{1, "Ford", "I'd far rather be happy than right any day.",
                        1, "Douglas", "Don't panic"}
        );
        assertEquals(2L, response.rowCount());
        refresh();

        execute("select \"_id\", id from quotes where id=1 order by author");
        assertEquals(2L, response.rowCount());
        assertThat((String) response.rows()[0][0], is("AgdEb3VnbGFzATE="));
        assertThat((Integer) response.rows()[0][1], is(1));
        assertThat((String) response.rows()[1][0], is("AgRGb3JkATE="));
        assertThat((Integer) response.rows()[1][1], is(1));
    }

    @Test
    public void testDeleteByIdWithMultiplePrimaryKey() throws Exception {
        execute("create table quotes (id integer primary key, author string primary key, " +
                "quote string) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into quotes (id, author, quote) values (?, ?, ?), (?, ?, ?)",
                new Object[]{1, "Ford", "I'd far rather be happy than right any day.",
                        1, "Douglas", "Don't panic"}
        );
        assertEquals(2L, response.rowCount());
        refresh();

        execute("delete from quotes where id=1 and author='Ford'");
        assertEquals(1L, response.rowCount());
        refresh();

        execute("select quote from quotes where id=1");
        assertEquals(1L, response.rowCount());
    }

    @Test
    public void testDeleteByQueryWithMultiplePrimaryKey() throws Exception {
        execute("create table quotes (id integer primary key, author string primary key, " +
                "quote string) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into quotes (id, author, quote) values (?, ?, ?), (?, ?, ?)",
                new Object[]{1, "Ford", "I'd far rather be happy than right any day.",
                        1, "Douglas", "Don't panic"}
        );
        assertEquals(2L, response.rowCount());
        refresh();

        execute("delete from quotes where id=1");
        // no rowCount available for deleteByQuery requests
        assertEquals(-1L, response.rowCount());
        refresh();

        execute("select quote from quotes where id=1");
        assertEquals(0L, response.rowCount());
    }

    @Test
    public void testSelectWhereBoolean() {
        execute("create table a (v boolean)");
        ensureYellow();

        execute("insert into a values (true)");
        execute("insert into a values (true)");
        execute("insert into a values (true)");
        execute("insert into a values (false)");
        execute("insert into a values (false)");
        refresh();

        execute("select v from a where v");
        assertEquals(3L, response.rowCount());

        execute("select v from a where not v");
        assertEquals(2L, response.rowCount());

        execute("select v from a where v or not v");
        assertEquals(5L, response.rowCount());

        execute("select v from a where v and not v");
        assertEquals(0L, response.rowCount());
    }

    @Test
    public void testSelectWhereBooleanPK() {
        execute("create table b (v boolean primary key) clustered by (v)");
        ensureYellow();

        execute("insert into b values (true)");
        execute("insert into b values (false)");
        refresh();

        execute("select v from b where v");
        assertEquals(1L, response.rowCount());

        execute("select v from b where not v");
        assertEquals(1L, response.rowCount());

        execute("select v from b where v or not v");
        assertEquals(2L, response.rowCount());

        execute("select v from b where v and not v");
        assertEquals(0L, response.rowCount());
    }



    @Test
    public void testBulkOperations() throws Exception {
        execute("create table test (id integer primary key, name string) with (number_of_replicas = 0)");
        ensureYellow();
        SQLBulkResponse bulkResp = execute("insert into test (id, name) values (?, ?), (?, ?)",
                new Object[][] {
                        {1, "Earth", 2, "Saturn"},    // bulk row 1
                        {3, "Moon", 4, "Mars"}        // bulk row 2
                });
        assertThat(bulkResp.results().length, is(4));
        for (SQLBulkResponse.Result result : bulkResp.results()) {
            assertThat(result.rowCount(), is(1L));
        }
        refresh();

        bulkResp = execute("insert into test (id, name) values (?, ?), (?, ?)",
            new Object[][] {
                {1, "Earth", 2, "Saturn"},    // bulk row 1
                {3, "Moon", 4, "Mars"}        // bulk row 2
            });
        assertThat(bulkResp.results().length, is(4));
        for (SQLBulkResponse.Result result : bulkResp.results()) {
            assertThat(result.rowCount(), is(-2L));
        }

        execute("select name from test order by id asc");
        assertEquals("Earth\nSaturn\nMoon\nMars\n", TestingHelpers.printedTable(response.rows()));

        // test bulk update-by-id
        bulkResp = execute("update test set name = concat(name, '-updated') where id = ?", new Object[][]{
                new Object[]{2},
                new Object[]{3},
                new Object[]{4},
        });
        assertThat(bulkResp.results().length, is(3));
        for (SQLBulkResponse.Result result : bulkResp.results()) {
            assertThat(result.rowCount(), is(1L));
        }
        refresh();

        execute("select count(*) from test where name like '%-updated'");
        assertThat((Long) response.rows()[0][0], is(3L));

        // test bulk of delete-by-id
        bulkResp = execute("delete from test where id = ?", new Object[][] {
                new Object[] { 1 },
                new Object[] { 3 }
        });
        assertThat(bulkResp.results().length, is(2));
        for (SQLBulkResponse.Result result : bulkResp.results()) {
            assertThat(result.rowCount(), is(1L));
        }
        refresh();

        execute("select count(*) from test");
        assertThat((Long) response.rows()[0][0], is(2L));

        // test bulk of delete-by-query
        bulkResp = execute("delete from test where name = ?", new Object[][] {
                new Object[] { "Saturn-updated" },
                new Object[] { "Mars-updated" }
        });
        assertThat(bulkResp.results().length, is(2));
        for (SQLBulkResponse.Result result : bulkResp.results()) {
            assertThat(result.rowCount(), is(-1L));
        }
        refresh();

        execute("select count(*) from test");
        assertThat((Long) response.rows()[0][0], is(0L));

    }

    @Test
    public void testSelectFormatFunction() throws Exception {
        this.setup.setUpLocations();
        ensureYellow();
        refresh();

        execute("select format('%s is a %s', name, kind) as sentence from locations order by name");
        assertThat(response.rowCount(), is(13L));
        assertArrayEquals(response.cols(), new String[]{"sentence"});
        assertThat(response.rows()[0].length, is(1));
        assertThat((String) response.rows()[0][0], is(" is a Planet"));
        assertThat((String) response.rows()[1][0], is("Aldebaran is a Star System"));
        assertThat((String) response.rows()[2][0], is("Algol is a Star System"));
        // ...

    }

    @Test
    public void testAnyArray() throws Exception {
        this.setup.setUpArrayTables();

        execute("select count(*) from any_table where 'Berlin' = ANY (names)");
        assertThat((Long) response.rows()[0][0], is(2L));

        execute("select id, names from any_table where 'Berlin' = ANY (names) order by id");
        assertThat(response.rowCount(), is(2L));
        assertThat((Integer) response.rows()[0][0], is(1));
        assertThat((Integer) response.rows()[1][0], is(3));

        execute("select id from any_table where 'Berlin' != ANY (names) order by id");
        assertThat(response.rowCount(), is(3L));
        assertThat((Integer) response.rows()[0][0], is(1));
        assertThat((Integer) response.rows()[1][0], is(2));
        assertThat((Integer) response.rows()[2][0], is(3));

        execute("select count(id) from any_table where 0.0 < ANY (temps)");
        assertThat((Long) response.rows()[0][0], is(2L));

        execute("select id, names from any_table where 0.0 < ANY (temps) order by id");
        assertThat(response.rowCount(), is(2L));
        assertThat((Integer) response.rows()[0][0], is(2));
        assertThat((Integer) response.rows()[1][0], is(3));

        execute("select count(*) from any_table where 0.0 > ANY (temps)");
        assertThat((Long) response.rows()[0][0], is(2L));

        execute("select id, names from any_table where 0.0 > ANY (temps) order by id");
        assertThat(response.rowCount(), is(2L));
        assertThat((Integer) response.rows()[0][0], is(2));
        assertThat((Integer) response.rows()[1][0], is(3));

        execute("select id, names from any_table where 'Ber%' LIKE ANY (names) order by id");
        assertThat(response.rowCount(), is(2L));
        assertThat((Integer) response.rows()[0][0], is(1));
        assertThat((Integer) response.rows()[1][0], is(3));

    }

    @Test
    public void testNotAnyArray() throws Exception {
        this.setup.setUpArrayTables();

        execute("select id from any_table where NOT 'Hangelsberg' = ANY (names) order by id");
        assertThat(response.rowCount(), is(3L));
        assertThat((Integer) response.rows()[0][0], is(1));
        assertThat((Integer) response.rows()[1][0], is(2));
        assertThat((Integer) response.rows()[2][0], is(4)); // null values matched because of negation

        execute("select id from any_table where 'Hangelsberg' != ANY (names) order by id");
        assertThat(response.rowCount(), is(3L));
        assertThat((Integer) response.rows()[0][0], is(1));
        assertThat((Integer) response.rows()[1][0], is(2));
        assertThat((Integer) response.rows()[2][0], is(3));
    }

    @Test
    public void testAnyLike() throws Exception {
        this.setup.setUpArrayTables();

        execute("select id from any_table where 'kuh%' LIKE ANY (tags) order by id");
        assertThat(response.rowCount(), is(2L));
        assertThat((Integer) response.rows()[0][0], is(3));
        assertThat((Integer) response.rows()[1][0], is(4));

        execute("select id from any_table where 'kuh%' NOT LIKE ANY (tags) order by id");
        assertThat(response.rowCount(), is(3L));
        assertThat((Integer) response.rows()[0][0], is(1));
        assertThat((Integer) response.rows()[1][0], is(2));
        assertThat((Integer) response.rows()[2][0], is(3));

    }

    @Test
    public void testInsertAndSelectIpType() throws Exception {
        execute("create table ip_table (fqdn string, addr ip) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into ip_table (fqdn, addr) values ('localhost', '127.0.0.1'), ('crate.io', '23.235.33.143')");
        execute("refresh table ip_table");

        execute("select addr from ip_table where addr = '23.235.33.143'");
        assertThat(response.rowCount(), is(1L));
        assertThat((String) response.rows()[0][0], is("23.235.33.143"));

        execute("select addr from ip_table where addr > '127.0.0.1'");
        assertThat(response.rowCount(), is(0L));
        execute("select addr from ip_table where addr > 2130706433"); // 2130706433 == 127.0.0.1
        assertThat(response.rowCount(), is(0L));

        execute("select addr from ip_table where addr < '127.0.0.1'");
        assertThat(response.rowCount(), is(1L));
        assertThat((String) response.rows()[0][0], is("23.235.33.143"));
        execute("select addr from ip_table where addr < 2130706433"); // 2130706433 == 127.0.0.1
        assertThat(response.rowCount(), is(1L));
        assertThat((String) response.rows()[0][0], is("23.235.33.143"));

        execute("select addr from ip_table where addr <= '127.0.0.1'");
        assertThat(response.rowCount(), is(2L));

        execute("select addr from ip_table where addr >= '23.235.33.143'");
        assertThat(response.rowCount(), is(2L));

        execute("select addr from ip_table where addr IS NULL");
        assertThat(response.rowCount(), is(0L));

        execute("select addr from ip_table where addr IS NOT NULL");
        assertThat(response.rowCount(), is(2L));

    }

    @Test
    public void testGroupByOnIpType() throws Exception {
        execute("create table t (i ip) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into t (i) values ('192.168.1.2'), ('192.168.1.2'), ('192.168.1.3')");
        execute("refresh table t");
        execute("select i, count(*) from t group by 1 order by count(*) desc");

        assertThat(response.rowCount(), is(2L));
        assertThat((String) response.rows()[0][0], is("192.168.1.2"));
        assertThat((Long) response.rows()[0][1], is(2L));
        assertThat((String) response.rows()[1][0], is("192.168.1.3"));
        assertThat((Long) response.rows()[1][1], is(1L));
    }

    @Test
    public void testDeleteOnIpType() throws Exception {
        execute("create table ip_table (fqdn string, addr ip) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into ip_table (fqdn, addr) values ('localhost', '127.0.0.1'), ('crate.io', '23.235.33.143')");
        execute("refresh table ip_table");
        execute("delete from ip_table where addr = '127.0.0.1'");
        assertThat(response.rowCount(), is(-1L));
        execute("select addr from ip_table");
        assertThat(response.rowCount(), is(1L));
        assertThat((String) response.rows()[0][0], is("23.235.33.143"));
    }

    @Test
    public void testInsertAndSelectGeoType() throws Exception {
        execute("create table geo_point_table (id int primary key, p geo_point) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into geo_point_table (id, p) values (?, ?)", new Object[]{1, new Double[]{47.22, 12.09}});
        execute("insert into geo_point_table (id, p) values (?, ?)", new Object[]{2, new Double[]{57.22, 7.12}});
        refresh();

        execute("select p from geo_point_table order by id desc");

        assertThat(response.rowCount(), is(2L));
        assertThat(((Double[]) response.rows()[0][0]), Matchers.arrayContaining(57.22, 7.12));
        assertThat(((Double[]) response.rows()[1][0]), Matchers.arrayContaining(47.22, 12.09));
    }

    @Test
    public void testGeoTypeQueries() throws Exception {
        // setup
        execute("create table t (id int primary key, i int, p geo_point) " +
                "clustered into 1 shards " +
                "with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into t (id, i, p) values (1, 1, 'POINT (10 20)')");
        execute("insert into t (id, i, p) values (2, 1, 'POINT (11 21)')");
        refresh();

        // order by
        execute("select distance(p, 'POINT (11 21)') from t order by 1");
        assertThat(response.rowCount(), is(2L));

        Double result1 = (Double) response.rows()[0][0];
        Double result2 = (Double) response.rows()[1][0];

        assertThat(result1, is(0.0d));
        assertThat(result2, is(152462.70754934277));

        String stmtOrderBy = "SELECT id " +
                "FROM t " +
                "ORDER BY distance(p, 'POINT(30.0 30.0)')";
        execute(stmtOrderBy);
        assertThat(response.rowCount(), is(2L));
        String expectedOrderBy =
                "2\n" +
                        "1\n";
        assertEquals(expectedOrderBy, TestingHelpers.printedTable(response.rows()));

        // aggregation (max())
        String stmtAggregate = "SELECT i, max(distance(p, 'POINT(30.0 30.0)')) " +
                "FROM t " +
                "GROUP BY i";
        execute(stmtAggregate);
        assertThat(response.rowCount(), is(1L));
        String expectedAggregate = "1| 2297790.338709135\n";
        assertEquals(expectedAggregate, TestingHelpers.printedTable(response.rows()));

        // queries
        execute("select p from t where distance(p, 'POINT (11 21)') > 0.0");
        Double[] row = Arrays.copyOf((Object[])response.rows()[0][0], 2, Double[].class);
        assertThat(row[0], is(10.0d));
        assertThat(row[1], is(20.0d));

        execute("select p from t where distance(p, 'POINT (11 21)') < 10.0");
        row = Arrays.copyOf((Object[])response.rows()[0][0], 2, Double[].class);
        assertThat(row[0], is(11.0d));
        assertThat(row[1], is(21.0d));

        execute("select p from t where distance(p, 'POINT (11 21)') < 10.0 or distance(p, 'POINT (11 21)') > 10.0");
        assertThat(response.rowCount(), is(2L));

        execute("select p from t where distance(p, 'POINT (10 20)') = 0");
        assertThat(response.rowCount(), is(1L));
    }

    @Test
    public void testWithinQuery() throws Exception {
        execute("create table t (id int primary key, p geo_point) " +
                "clustered into 1 shards " +
                "with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into t (id, p) values (1, 'POINT (10 10)')");
        refresh();

        execute("select within(p, 'POLYGON (( 5 5, 30 5, 30 30, 5 30, 5 5 ))') from t");
        assertThat((Boolean) response.rows()[0][0], is(true));

        execute("select * from t where within(p, 'POLYGON (( 5 5, 30 5, 30 30, 5 30, 5 5 ))')");
        assertThat(response.rowCount(), is(1L));
        execute("select * from t where within(p, 'POLYGON (( 5 5, 30 5, 30 30, 5 35, 5 5 ))') = false");
        assertThat(response.rowCount(), is(0L));
    }

    @Test
    public void testTwoSubStrOnSameColumn() throws Exception {
        this.setup.groupBySetup();
        execute("select name, substr(name, 4, 4), substr(name, 3, 5) from sys.nodes order by name");
        assertThat((String) response.rows()[0][0], is("node_s0"));
        assertThat((String) response.rows()[0][1], is("e_s0"));
        assertThat((String) response.rows()[0][2], is("de_s0"));
        assertThat((String) response.rows()[1][0], is("node_s1"));
        assertThat((String) response.rows()[1][1], is("e_s1"));
        assertThat((String) response.rows()[1][2], is("de_s1"));

    }


    @Test
    public void testSelectArithMetricOperatorInOrderBy() throws Exception {
        execute("create table t (i integer, l long, d double) clustered into 3 shards with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into t (i, l, d) values (1, 2, 90.5), (2, 5, 90.5), (193384, 31234594433, 99.0), (10, 21, 99.0), (-1, 4, 99.0)");
        refresh();

        execute("select i, i%3 from t order by i%3, l");
        assertThat(response.rowCount(), is(5L));
        assertThat(TestingHelpers.printedTable(response.rows()), is(
                "-1| -1\n" +
                        "1| 1\n" +
                        "10| 1\n" +
                        "193384| 1\n" +
                        "2| 2\n"));
    }

    @Test
    public void testSelectFailingSearchScript() throws Exception {
        expectedException.expect(SQLActionException.class);
        expectedException.expectMessage("log(x, b): given arguments would result in: 'NaN'");

        execute("create table t (i integer, l long, d double) clustered into 1 shards with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into t (i, l, d) values (1, 2, 90.5)");
        refresh();

        execute("select log(d, l) from t where log(d, -1) >= 0");
    }

    @Test
    public void testSelectGroupByFailingSearchScript() throws Exception {
        expectedException.expect(SQLActionException.class);
        expectedException.expectMessage("log(x, b): given arguments would result in: 'NaN'");

        execute("create table t (i integer, l long, d double) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into t (i, l, d) values (1, 2, 90.5), (0, 4, 100)");
        execute("refresh table t");

        execute("select log(d, l) from t where log(d, -1) >= 0 group by log(d, l)");
    }

    @Test
    public void testNumericScriptOnAllTypes() throws Exception {
        // this test validates that no exception is thrown
        execute("create table t (b byte, s short, i integer, l long, f float, d double, t timestamp) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into t (b, s, i, l, f, d, t) values (1, 2, 3, 4, 5.7, 6.3, '2014-07-30')");
        refresh();

        String[] functionCalls = new String[]{
                "abs(%s)",
                "ceil(%s)",
                "floor(%s)",
                "ln(%s)",
                "log(%s)",
                "log(%s, 2)",
                "random()",
                "round(%s)",
                "sqrt(%s)"
        };

        for (String functionCall : functionCalls) {
            String byteCall = String.format(Locale.ENGLISH, functionCall, "b");
            execute(String.format(Locale.ENGLISH, "select %s, b from t where %s < 2", byteCall, byteCall));

            String shortCall = String.format(Locale.ENGLISH, functionCall, "s");
            execute(String.format(Locale.ENGLISH, "select %s, s from t where %s < 2", shortCall, shortCall));

            String intCall = String.format(Locale.ENGLISH, functionCall, "i");
            execute(String.format(Locale.ENGLISH, "select %s, i from t where %s < 2", intCall, intCall));

            String longCall = String.format(Locale.ENGLISH, functionCall, "l");
            execute(String.format(Locale.ENGLISH, "select %s, l from t where %s < 2", longCall, longCall));

            String floatCall = String.format(Locale.ENGLISH, functionCall, "f");
            execute(String.format(Locale.ENGLISH, "select %s, f from t where %s < 2", floatCall, floatCall));

            String doubleCall = String.format(Locale.ENGLISH, functionCall, "d");
            execute(String.format(Locale.ENGLISH, "select %s, d from t where %s < 2", doubleCall, doubleCall));
        }
    }

    @Test
    public void testMatchNotOnSubColumn() throws Exception {
        execute("create table matchbox (" +
                "  s string index using fulltext with (analyzer='german')," +
                "  o object as (" +
                "    s string index using fulltext with (analyzer='german')," +
                "    m string index using fulltext with (analyzer='german')" +
                "  )," +
                "  o_ignored object(ignored)" +
                ") with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into matchbox (s, o) values ('Arthur Dent', {s='Zaphod Beeblebroox', m='Ford Prefect'})");
        refresh();
        execute("select * from matchbox where match(s, 'Arthur')");
        assertThat(response.rowCount(), is(1L));

        execute("select * from matchbox where match(o['s'], 'Arthur')");
        assertThat(response.rowCount(), is(0L));

        execute("select * from matchbox where match(o['s'], 'Zaphod')");
        assertThat(response.rowCount(), is(1L));

        execute("select * from matchbox where match(s, 'Zaphod')");
        assertThat(response.rowCount(), is(0L));

        execute("select * from matchbox where match(o['m'], 'Ford')");
        assertThat(response.rowCount(), is(1L));

        expectedException.expect(SQLActionException.class);
        expectedException.expectMessage("Can only use MATCH on columns of type STRING, not on 'null'");

        execute("select * from matchbox where match(o_ignored['a'], 'Ford')");
        assertThat(response.rowCount(), is(0L));
    }

    @Test
    public void testSelectWhereMultiColumnMatchDifferentTypesDifferentScore() throws Exception {
        this.setup.setUpLocations();
        refresh();
        execute("select name, description, kind, _score from locations " +
                "where match((kind, name_description_ft 0.5), 'Planet earth') using most_fields with (analyzer='english') order by _score desc");
        assertThat(response.rowCount(), is(5L));
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("Alpha Centauri| 4.1 light-years northwest of earth| Star System| 0.049483635\n" +
                        "| This Planet doesn't really exist| Planet| 0.04724514\nAllosimanius Syneca| Allosimanius Syneca is a planet noted for ice, snow, mind-hurtling beauty and stunning cold.| Planet| 0.021473126\n" +
                        "Bartledan| An Earthlike planet on which Arthur Dent lived for a short time, Bartledan is inhabited by Bartledanians, a race that appears human but only physically.| Planet| 0.018788986\n" +
                        "Galactic Sector QQ7 Active J Gamma| Galactic Sector QQ7 Active J Gamma contains the Sun Zarss, the planet Preliumtarn of the famed Sevorbeupstry and Quentulus Quazgar Mountains.| Galaxy| 0.017716927\n"));

        execute("select name, description, kind, _score from locations " +
                "where match((kind, name_description_ft 0.5), 'Planet earth') using cross_fields order by _score desc");
        assertThat(response.rowCount(), is(5L));
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("Alpha Centauri| 4.1 light-years northwest of earth| Star System| 0.06658964\n" +
                        "| This Planet doesn't really exist| Planet| 0.06235056\n" +
                        "Allosimanius Syneca| Allosimanius Syneca is a planet noted for ice, snow, mind-hurtling beauty and stunning cold.| Planet| 0.02889618\n" +
                        "Bartledan| An Earthlike planet on which Arthur Dent lived for a short time, Bartledan is inhabited by Bartledanians, a race that appears human but only physically.| Planet| 0.025284158\n" +
                        "Galactic Sector QQ7 Active J Gamma| Galactic Sector QQ7 Active J Gamma contains the Sun Zarss, the planet Preliumtarn of the famed Sevorbeupstry and Quentulus Quazgar Mountains.| Galaxy| 0.02338146\n"));
    }

    @Test
    public void testSimpleMatchWithBoost() throws Exception {
        execute("create table characters ( " +
                "  id int primary key, " +
                "  name string, " +
                "  quote string, " +
                "  INDEX name_ft using fulltext(name) with (analyzer = 'english'), " +
                "  INDEX quote_ft using fulltext(quote) with (analyzer = 'english') " +
                ") clustered into 5 shards ");
        ensureYellow();
        execute("insert into characters (id, name, quote) values (?, ?, ?)", new Object[][]{
                new Object[]{1, "Arthur", "It's terribly small, tiny little country."},
                new Object[]{2, "Trillian", " No, it's a country. Off the coast of Africa."},
                new Object[]{3, "Marvin", " It won't work, I have an exceptionally large mind." }
        });
        refresh();
        execute("select characters.name AS characters_name, _score " +
                "from characters " +
                "where match(characters.quote_ft 1.0, 'country') order by _score desc");
        assertThat(response.rows().length, is(2));
        assertThat((String) response.rows()[0][0], is("Trillian"));
        assertThat((float) response.rows()[0][1], is(0.15342641f));
        assertThat((String) response.rows()[1][0], is("Arthur"));
        assertThat((float) response.rows()[1][1], is(0.13424811f));
    }

    @Test
    public void testMatchTypes() throws Exception {
        this.setup.setUpLocations();
        refresh();
        execute("select name, _score from locations where match((kind 0.8, name_description_ft 0.6), 'planet earth') using best_fields order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("Alpha Centauri| 0.22184466\n| 0.21719791\nAllosimanius Syneca| 0.09626817\nBartledan| 0.08423465\nGalactic Sector QQ7 Active J Gamma| 0.08144922\n"));

        execute("select name, _score from locations where match((kind 0.6, name_description_ft 0.8), 'planet earth') using most_fields order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("Alpha Centauri| 0.12094267\n| 0.1035407\nAllosimanius Syneca| 0.05248235\nBartledan| 0.045922056\nGalactic Sector QQ7 Active J Gamma| 0.038827762\n"));

        execute("select name, _score from locations where match((kind 0.4, name_description_ft 1.0), 'planet earth') using cross_fields order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("Alpha Centauri| 0.14147125\n| 0.116184436\nAllosimanius Syneca| 0.061390605\nBartledan| 0.05371678\nGalactic Sector QQ7 Active J Gamma| 0.043569162\n"));

        execute("select name, _score from locations where match((kind 1.0, name_description_ft 0.4), 'Alpha Centauri') using phrase");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("Alpha Centauri| 0.94653714\n"));

        execute("select name, _score from locations where match(name_description_ft, 'Alpha Centauri') using phrase_prefix");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("Alpha Centauri| 1.5739591\n"));
    }

    @Test
    public void testMatchOptions() throws Exception {
        this.setup.setUpLocations();
        refresh();

        execute("select name, _score from locations where match((kind, name_description_ft), 'galaxy') " +
                "using best_fields with (analyzer='english') order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("End of the Galaxy| 0.7260999\nAltair| 0.2895972\nNorth West Ripple| 0.25339755\nOuter Eastern Rim| 0.2246257\n"));

        execute("select name, _score from locations where match((kind, name_description_ft), 'galaxy') " +
                "using best_fields with (fuzziness=0.5) order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("Outer Eastern Rim| 1.4109559\nEnd of the Galaxy| 1.4109559\nNorth West Ripple| 1.2808706\nGalactic Sector QQ7 Active J Gamma| 1.2808706\nAltair| 0.3842612\nAlgol| 0.25617412\n"));

        execute("select name, _score from locations where match((kind, name_description_ft), 'gala') " +
                "using best_fields with (operator='or', minimum_should_match=2) order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is(""));

        execute("select name, _score from locations where match((kind, name_description_ft), 'gala') " +
                "using phrase_prefix with (slop=1) order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("End of the Galaxy| 0.75176084\nOuter Eastern Rim| 0.5898516\nGalactic Sector QQ7 Active J Gamma| 0.34636837\nAlgol| 0.32655922\nAltair| 0.32655922\nNorth West Ripple| 0.2857393\n"));

        execute("select name, _score from locations where match((kind, name_description_ft), 'galaxy') " +
                "using phrase with (tie_breaker=2.0) order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("End of the Galaxy| 0.4618873\nAltair| 0.18054473\nNorth West Ripple| 0.15797664\nOuter Eastern Rim| 0.1428891\n"));

        execute("select name, _score from locations where match((kind, name_description_ft), 'galaxy') " +
                "using best_fields with (zero_terms_query='all') order by _score desc");
        assertThat(TestingHelpers.printedTable(response.rows()),
                is("End of the Galaxy| 0.7260999\nAltair| 0.2895972\nNorth West Ripple| 0.25339755\nOuter Eastern Rim| 0.2246257\n"));
    }

    @Test
    public void testWhereColumnEqColumnAndFunctionEqFunction() throws Exception {
        this.setup.setUpLocations();
        ensureYellow();
        refresh();

        execute("select name from locations where name = name");
        assertThat(response.rowCount(), is(13L));

        execute("select name from locations where substr(name, 1, 1) = substr(name, 1, 1)");
        assertThat(response.rowCount(), is(13L));
    }

    @Test
    public void testNewColumn() throws Exception {
        execute("create table t (name string) with (number_of_replicas=0)");
        ensureYellow();
        execute("insert into t (name, score) values ('Ford', 1.2)");
    }

    @Test
    public void testESGetSourceColumns() throws Exception {
        this.setup.setUpLocations();
        ensureYellow();
        refresh();

        execute("select _id, _version from locations where id=2");
        assertNotNull(response.rows()[0][0]);
        assertNotNull(response.rows()[0][1]);

        execute("select _id, name from locations where id=2");
        assertNotNull(response.rows()[0][0]);
        assertNotNull(response.rows()[0][1]);

        execute("select _id, _doc from locations where id=2");
        assertNotNull(response.rows()[0][0]);
        assertNotNull(response.rows()[0][1]);

        execute("select _doc, id from locations where id in (2,3) order by id");
        assertEquals(TestingHelpers.printedTable(response.rows()), "{date=308534400000, race=null, kind=Galaxy, " +
                "name=Outer Eastern Rim, description=The Outer Eastern Rim of the Galaxy where the Guide has " +
                "supplanted the Encyclopedia Galactica among its more relaxed civilisations., id=2, position=2}| 2\n" +
                "{date=1367366400000, race=null, kind=Galaxy, name=Galactic Sector QQ7 Active J Gamma, "+
                "description=Galactic Sector QQ7 Active J Gamma contains the Sun Zarss, the planet Preliumtarn of " +
                "the famed Sevorbeupstry and Quentulus Quazgar Mountains., id=3, position=4}| 3\n");

        execute("select name, kind from locations where id in (2,3) order by id");
        assertEquals(TestingHelpers.printedTable(response.rows()), "Outer Eastern Rim| Galaxy\n" +
                "Galactic Sector QQ7 Active J Gamma| Galaxy\n");

        execute("select name, kind, _id from locations where id in (2,3) order by id");
        assertEquals(TestingHelpers.printedTable(response.rows()), "Outer Eastern Rim| Galaxy| 2\n" +
                "Galactic Sector QQ7 Active J Gamma| Galaxy| 3\n");

        execute("select _raw, id from locations where id in (2,3) order by id");
        assertEquals(TestingHelpers.printedTable(response.rows()), "{\"id\":\"2\",\"name\":\"Outer Eastern Rim\"," +
                "\"date\":308534400000,\"kind\":\"Galaxy\",\"position\":2,\"description\":\"The Outer Eastern Rim " +
                "of the Galaxy where the Guide has supplanted the Encyclopedia Galactica among its more relaxed " +
                "civilisations.\",\"race\":null}| 2\n" +
                "{\"id\":\"3\",\"name\":\"Galactic Sector QQ7 Active J Gamma\",\"date\":1367366400000," +
                "\"kind\":\"Galaxy\",\"position\":4,\"description\":\"Galactic Sector QQ7 Active J Gamma contains " +
                "the Sun Zarss, the planet Preliumtarn of the famed Sevorbeupstry and Quentulus Quazgar Mountains." +
                "\",\"race\":null}| 3\n");
    }
}


