Refactoring Types: ['Extract Interface']
va/org/apache/drill/exec/store/hbase/HBaseStoragePlugin.java
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
package org.apache.drill.exec.store.hbase;

import java.io.IOException;
import java.util.Set;

import org.apache.calcite.schema.SchemaPlus;

import org.apache.drill.common.JSONOptions;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.store.AbstractStoragePlugin;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.store.StoragePluginOptimizerRule;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.collect.ImmutableSet;

public class HBaseStoragePlugin extends AbstractStoragePlugin {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(HBaseStoragePlugin.class);

  private final DrillbitContext context;
  private final HBaseStoragePluginConfig engineConfig;
  private final HBaseSchemaFactory schemaFactory;

  @SuppressWarnings("unused")
  private final String name;

  public HBaseStoragePlugin(HBaseStoragePluginConfig configuration, DrillbitContext context, String name)
      throws IOException {
    this.context = context;
    this.schemaFactory = new HBaseSchemaFactory(this, name);
    this.engineConfig = configuration;
    this.name = name;
  }

  public DrillbitContext getContext() {
    return this.context;
  }

  @Override
  public boolean supportsRead() {
    return true;
  }

  @Override
  public HBaseGroupScan getPhysicalScan(String userName, JSONOptions selection) throws IOException {
    HBaseScanSpec scanSpec = selection.getListWith(new ObjectMapper(), new TypeReference<HBaseScanSpec>() {});
    return new HBaseGroupScan(userName, this, scanSpec, null);
  }

  @Override
  public void registerSchemas(SchemaConfig schemaConfig, SchemaPlus parent) throws IOException {
    schemaFactory.registerSchemas(schemaConfig, parent);
  }

  @Override
  public HBaseStoragePluginConfig getConfig() {
    return engineConfig;
  }

  @Override
  public Set<StoragePluginOptimizerRule> getOptimizerRules() {
    return ImmutableSet.of(HBasePushFilterIntoScan.FILTER_ON_SCAN, HBasePushFilterIntoScan.FILTER_ON_PROJECT);
  }

}

File: contrib/storage-hive/core/src/main/java/org/apache/drill/exec/store/hive/HiveStoragePlugin.java
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
package org.apache.drill.exec.store.hive;

import java.io.IOException;
import java.util.List;
import java.util.Set;
import com.google.common.collect.ImmutableSet;

import org.apache.calcite.schema.Schema.TableType;
import org.apache.calcite.schema.SchemaPlus;

import org.apache.drill.common.JSONOptions;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.planner.sql.logical.HivePushPartitionFilterIntoScan;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.store.AbstractStoragePlugin;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.store.StoragePluginOptimizerRule;
import org.apache.drill.exec.store.hive.schema.HiveSchemaFactory;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

public class HiveStoragePlugin extends AbstractStoragePlugin {

  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(HiveStoragePlugin.class);

  private final HiveStoragePluginConfig config;
  private final HiveSchemaFactory schemaFactory;
  private final DrillbitContext context;
  private final String name;

  public HiveStoragePlugin(HiveStoragePluginConfig config, DrillbitContext context, String name) throws ExecutionSetupException {
    this.config = config;
    this.context = context;
    this.schemaFactory = new HiveSchemaFactory(this, name, config.getHiveConfigOverride());
    this.name = name;
  }

  public HiveStoragePluginConfig getConfig() {
    return config;
  }

  public String getName(){
    return name;
  }

  public DrillbitContext getContext() {
    return context;
  }

  @Override
  public HiveScan getPhysicalScan(String userName, JSONOptions selection, List<SchemaPath> columns) throws IOException {
    HiveReadEntry hiveReadEntry = selection.getListWith(new ObjectMapper(), new TypeReference<HiveReadEntry>(){});
    try {
      if (hiveReadEntry.getJdbcTableType() == TableType.VIEW) {
        throw new UnsupportedOperationException(
            "Querying views created in Hive from Drill is not supported in current version.");
      }

      return new HiveScan(userName, hiveReadEntry, this, columns);
    } catch (ExecutionSetupException e) {
      throw new IOException(e);
    }
  }

  @Override
  public void registerSchemas(SchemaConfig schemaConfig, SchemaPlus parent) throws IOException {
    schemaFactory.registerSchemas(schemaConfig, parent);
  }
  public Set<StoragePluginOptimizerRule> getOptimizerRules() {
    return ImmutableSet.of(HivePushPartitionFilterIntoScan.HIVE_FILTER_ON_PROJECT, HivePushPartitionFilterIntoScan.HIVE_FILTER_ON_SCAN);
  }

}


File: contrib/storage-mongo/src/main/java/org/apache/drill/exec/store/mongo/MongoStoragePlugin.java
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
package org.apache.drill.exec.store.mongo;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import org.apache.calcite.schema.SchemaPlus;
import org.apache.drill.common.JSONOptions;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.exec.physical.base.AbstractGroupScan;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.store.AbstractStoragePlugin;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.store.StoragePluginOptimizerRule;
import org.apache.drill.exec.store.mongo.schema.MongoSchemaFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.RemovalListener;
import com.google.common.cache.RemovalNotification;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Lists;
import com.mongodb.MongoClient;
import com.mongodb.MongoClientURI;
import com.mongodb.MongoCredential;
import com.mongodb.ServerAddress;

public class MongoStoragePlugin extends AbstractStoragePlugin {
  static final Logger logger = LoggerFactory
      .getLogger(MongoStoragePlugin.class);

  private final DrillbitContext context;
  private final MongoStoragePluginConfig mongoConfig;
  private final MongoSchemaFactory schemaFactory;
  private final Cache<MongoCnxnKey, MongoClient> addressClientMap;
  private final MongoClientURI clientURI;

  public MongoStoragePlugin(MongoStoragePluginConfig mongoConfig,
      DrillbitContext context, String name) throws IOException,
      ExecutionSetupException {
    this.context = context;
    this.mongoConfig = mongoConfig;
    this.clientURI = new MongoClientURI(this.mongoConfig.getConnection());
    this.addressClientMap = CacheBuilder.newBuilder()
        .expireAfterAccess(24, TimeUnit.HOURS)
        .removalListener(new AddressCloser()).build();
    this.schemaFactory = new MongoSchemaFactory(this, name);
  }

  public DrillbitContext getContext() {
    return this.context;
  }

  @Override
  public MongoStoragePluginConfig getConfig() {
    return mongoConfig;
  }

  @Override
  public void registerSchemas(SchemaConfig schemaConfig, SchemaPlus parent) throws IOException {
    schemaFactory.registerSchemas(schemaConfig, parent);
  }

  @Override
  public boolean supportsRead() {
    return true;
  }

  @Override
  public AbstractGroupScan getPhysicalScan(String userName, JSONOptions selection) throws IOException {
    MongoScanSpec mongoScanSpec = selection.getListWith(new ObjectMapper(), new TypeReference<MongoScanSpec>() {});
    return new MongoGroupScan(userName, this, mongoScanSpec, null);
  }

  public Set<StoragePluginOptimizerRule> getOptimizerRules() {
    return ImmutableSet.of(MongoPushDownFilterForScan.INSTANCE);
  }


  private class AddressCloser implements
      RemovalListener<MongoCnxnKey, MongoClient> {
    @Override
    public synchronized void onRemoval(
        RemovalNotification<MongoCnxnKey, MongoClient> removal) {
      removal.getValue().close();
      logger.debug("Closed connection to {}.", removal.getKey().toString());
    }
  }

  public MongoClient getClient(String host) {
    return getClient(Collections.singletonList(new ServerAddress(host)));
  }

  public MongoClient getClient() {
    List<String> hosts = clientURI.getHosts();
    List<ServerAddress> addresses = Lists.newArrayList();
    for (String host : hosts) {
      addresses.add(new ServerAddress(host));
    }
    return getClient(addresses);
  }

  public synchronized MongoClient getClient(List<ServerAddress> addresses) {
    // Take the first replica from the replicated servers
    final ServerAddress serverAddress = addresses.get(0);
    final MongoCredential credential = clientURI.getCredentials();
    String userName = credential == null ? null : credential.getUserName();
    MongoCnxnKey key = new MongoCnxnKey(serverAddress, userName);
    MongoClient client = addressClientMap.getIfPresent(key);
    if (client == null) {
      if (credential != null) {
        List<MongoCredential> credentialList = Arrays.asList(credential);
        client = new MongoClient(addresses, credentialList, clientURI.getOptions());
      } else {
        client = new MongoClient(addresses, clientURI.getOptions());
      }
      addressClientMap.put(key, client);
      logger.debug("Created connection to {}.", key.toString());
      logger.debug("Number of open connections {}.", addressClientMap.size());
    }
    return client;
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/expr/ExpressionTreeMaterializer.java
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
package org.apache.drill.exec.expr;

import java.util.Arrays;
import java.util.List;

import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.expression.BooleanOperator;
import org.apache.drill.common.expression.CastExpression;
import org.apache.drill.common.expression.ConvertExpression;
import org.apache.drill.common.expression.ErrorCollector;
import org.apache.drill.common.expression.ErrorCollectorImpl;
import org.apache.drill.common.expression.ExpressionPosition;
import org.apache.drill.common.expression.FunctionCall;
import org.apache.drill.common.expression.FunctionHolderExpression;
import org.apache.drill.common.expression.IfExpression;
import org.apache.drill.common.expression.LogicalExpression;
import org.apache.drill.common.expression.NullExpression;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.common.expression.TypedNullConstant;
import org.apache.drill.common.expression.ValueExpressions;
import org.apache.drill.common.expression.ValueExpressions.BooleanExpression;
import org.apache.drill.common.expression.ValueExpressions.DateExpression;
import org.apache.drill.common.expression.ValueExpressions.Decimal18Expression;
import org.apache.drill.common.expression.ValueExpressions.Decimal28Expression;
import org.apache.drill.common.expression.ValueExpressions.Decimal38Expression;
import org.apache.drill.common.expression.ValueExpressions.Decimal9Expression;
import org.apache.drill.common.expression.ValueExpressions.DoubleExpression;
import org.apache.drill.common.expression.ValueExpressions.FloatExpression;
import org.apache.drill.common.expression.ValueExpressions.IntExpression;
import org.apache.drill.common.expression.ValueExpressions.IntervalDayExpression;
import org.apache.drill.common.expression.ValueExpressions.IntervalYearExpression;
import org.apache.drill.common.expression.ValueExpressions.LongExpression;
import org.apache.drill.common.expression.ValueExpressions.QuotedString;
import org.apache.drill.common.expression.ValueExpressions.TimeExpression;
import org.apache.drill.common.expression.ValueExpressions.TimeStampExpression;
import org.apache.drill.common.expression.fn.CastFunctions;
import org.apache.drill.common.expression.visitors.AbstractExprVisitor;
import org.apache.drill.common.expression.visitors.ConditionalExprOptimizer;
import org.apache.drill.common.expression.visitors.ExpressionValidator;
import org.apache.drill.common.types.TypeProtos;
import org.apache.drill.common.types.TypeProtos.DataMode;
import org.apache.drill.common.types.TypeProtos.MajorType;
import org.apache.drill.common.types.TypeProtos.MinorType;
import org.apache.drill.common.types.Types;
import org.apache.drill.common.util.CoreDecimalUtility;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.expr.annotations.FunctionTemplate;
import org.apache.drill.exec.expr.fn.AbstractFuncHolder;
import org.apache.drill.exec.expr.fn.DrillComplexWriterFuncHolder;
import org.apache.drill.exec.expr.fn.DrillFuncHolder;
import org.apache.drill.exec.expr.fn.FunctionImplementationRegistry;
import org.apache.drill.exec.record.TypedFieldId;
import org.apache.drill.exec.record.VectorAccessible;
import org.apache.drill.exec.resolver.FunctionResolver;
import org.apache.drill.exec.resolver.FunctionResolverFactory;
import org.apache.drill.exec.resolver.TypeCastRules;

import com.google.common.base.Optional;
import com.google.common.base.Predicate;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import org.apache.drill.exec.vector.VarCharVector;

public class ExpressionTreeMaterializer {

  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ExpressionTreeMaterializer.class);

  private ExpressionTreeMaterializer() {
  };

  public static LogicalExpression materialize(LogicalExpression expr, VectorAccessible batch, ErrorCollector errorCollector, FunctionImplementationRegistry registry) {
    return ExpressionTreeMaterializer.materialize(expr, batch, errorCollector, registry, false);
  }

  public static LogicalExpression materializeAndCheckErrors(LogicalExpression expr, VectorAccessible batch, FunctionImplementationRegistry registry) throws SchemaChangeException {
    ErrorCollector collector = new ErrorCollectorImpl();
    LogicalExpression e = ExpressionTreeMaterializer.materialize(expr, batch, collector, registry, false);
    if (collector.hasErrors()) {
      throw new SchemaChangeException(String.format("Failure while trying to materialize incoming schema.  Errors:\n %s.", collector.toErrorString()));
    }
    return e;
  }

  public static LogicalExpression materialize(LogicalExpression expr, VectorAccessible batch, ErrorCollector errorCollector, FunctionImplementationRegistry registry,
      boolean allowComplexWriterExpr) {
    LogicalExpression out =  expr.accept(new MaterializeVisitor(batch, errorCollector, allowComplexWriterExpr), registry);

    if (!errorCollector.hasErrors()) {
      out = out.accept(ConditionalExprOptimizer.INSTANCE, null);
    }

    if (out instanceof NullExpression) {
      return new TypedNullConstant(Types.optional(MinorType.INT));
    } else {
      return out;
    }
  }

  public static LogicalExpression convertToNullableType(LogicalExpression fromExpr, MinorType toType, FunctionImplementationRegistry registry, ErrorCollector errorCollector) {
    String funcName = "convertToNullable" + toType.toString();
    List<LogicalExpression> args = Lists.newArrayList();
    args.add(fromExpr);
    FunctionCall funcCall = new FunctionCall(funcName, args, ExpressionPosition.UNKNOWN);
    FunctionResolver resolver = FunctionResolverFactory.getResolver(funcCall);

    DrillFuncHolder matchedConvertToNullableFuncHolder = registry.findDrillFunction(resolver, funcCall);
    if (matchedConvertToNullableFuncHolder == null) {
      logFunctionResolutionError(errorCollector, funcCall);
      return NullExpression.INSTANCE;
    }

    return matchedConvertToNullableFuncHolder.getExpr(funcName, args, ExpressionPosition.UNKNOWN);
  }


  public static LogicalExpression addCastExpression(LogicalExpression fromExpr, MajorType toType, FunctionImplementationRegistry registry, ErrorCollector errorCollector) {
    String castFuncName = CastFunctions.getCastFunc(toType.getMinorType());
    List<LogicalExpression> castArgs = Lists.newArrayList();
    castArgs.add(fromExpr);  //input_expr

    if (!Types.isFixedWidthType(toType)) {

      /* We are implicitly casting to VARCHAR so we don't have a max length,
       * using an arbitrary value. We trim down the size of the stored bytes
       * to the actual size so this size doesn't really matter.
       */
      castArgs.add(new ValueExpressions.LongExpression(TypeHelper.VARCHAR_DEFAULT_CAST_LEN, null));
    }
    else if (CoreDecimalUtility.isDecimalType(toType)) {
      // Add the scale and precision to the arguments of the implicit cast
      castArgs.add(new ValueExpressions.LongExpression(toType.getPrecision(), null));
      castArgs.add(new ValueExpressions.LongExpression(toType.getScale(), null));
    }
    FunctionCall castCall = new FunctionCall(castFuncName, castArgs, ExpressionPosition.UNKNOWN);
    FunctionResolver resolver = FunctionResolverFactory.getExactResolver(castCall);
    DrillFuncHolder matchedCastFuncHolder = registry.findDrillFunction(resolver, castCall);

    if (matchedCastFuncHolder == null) {
      logFunctionResolutionError(errorCollector, castCall);
      return NullExpression.INSTANCE;
    }
    return matchedCastFuncHolder.getExpr(castFuncName, castArgs, ExpressionPosition.UNKNOWN);
  }

  private static void logFunctionResolutionError(ErrorCollector errorCollector, FunctionCall call) {
    // add error to collector
    StringBuilder sb = new StringBuilder();
    sb.append("Missing function implementation: ");
    sb.append("[");
    sb.append(call.getName());
    sb.append("(");
    boolean first = true;
    for(LogicalExpression e : call.args) {
      TypeProtos.MajorType mt = e.getMajorType();
      if (first) {
        first = false;
      } else {
        sb.append(", ");
      }
      sb.append(mt.getMinorType().name());
      sb.append("-");
      sb.append(mt.getMode().name());
    }
    sb.append(")");
    sb.append("]");

    errorCollector.addGeneralError(call.getPosition(), sb.toString());
  }

  private static class MaterializeVisitor extends AbstractExprVisitor<LogicalExpression, FunctionImplementationRegistry, RuntimeException> {
    private ExpressionValidator validator = new ExpressionValidator();
    private final ErrorCollector errorCollector;
    private final VectorAccessible batch;
    private final boolean allowComplexWriter;

    public MaterializeVisitor(VectorAccessible batch, ErrorCollector errorCollector, boolean allowComplexWriter) {
      this.batch = batch;
      this.errorCollector = errorCollector;
      this.allowComplexWriter = allowComplexWriter;
    }

    private LogicalExpression validateNewExpr(LogicalExpression newExpr) {
      newExpr.accept(validator, errorCollector);
      return newExpr;
    }

    @Override
    public LogicalExpression visitUnknown(LogicalExpression e, FunctionImplementationRegistry registry)
      throws RuntimeException {
      return e;
    }

    @Override
    public LogicalExpression visitFunctionHolderExpression(FunctionHolderExpression holder, FunctionImplementationRegistry value) throws RuntimeException {
      // a function holder is already materialized, no need to rematerialize.  generally this won't be used unless we materialize a partial tree and rematerialize the whole tree.
      return holder;
    }

    @Override
    public LogicalExpression visitBooleanOperator(BooleanOperator op, FunctionImplementationRegistry registry) {
      List<LogicalExpression> args = Lists.newArrayList();
      for (int i = 0; i < op.args.size(); ++i) {
        LogicalExpression newExpr = op.args.get(i).accept(this, registry);
        assert newExpr != null : String.format("Materialization of %s return a null expression.", op.args.get(i));
        args.add(newExpr);
      }

      //replace with a new function call, since its argument could be changed.
      return new BooleanOperator(op.getName(), args, op.getPosition());
    }

    @Override
    public LogicalExpression visitFunctionCall(FunctionCall call, FunctionImplementationRegistry registry) {
      List<LogicalExpression> args = Lists.newArrayList();
      for (int i = 0; i < call.args.size(); ++i) {
        LogicalExpression newExpr = call.args.get(i).accept(this, registry);
        assert newExpr != null : String.format("Materialization of %s returned a null expression.", call.args.get(i));
        args.add(newExpr);
      }

      //replace with a new function call, since its argument could be changed.
      call = new FunctionCall(call.getName(), args, call.getPosition());

      FunctionResolver resolver = FunctionResolverFactory.getResolver(call);
      DrillFuncHolder matchedFuncHolder = registry.findDrillFunction(resolver, call);

      if (matchedFuncHolder instanceof DrillComplexWriterFuncHolder && ! allowComplexWriter) {
        errorCollector.addGeneralError(call.getPosition(), "Only ProjectRecordBatch could have complex writer function. You are using complex writer function " + call.getName() + " in a non-project operation!");
      }

      //new arg lists, possible with implicit cast inserted.
      List<LogicalExpression> argsWithCast = Lists.newArrayList();

      if (matchedFuncHolder!=null) {
        //Compare parm type against arg type. Insert cast on top of arg, whenever necessary.
        for (int i = 0; i < call.args.size(); ++i) {

          LogicalExpression currentArg = call.args.get(i);

          TypeProtos.MajorType parmType = matchedFuncHolder.getParmMajorType(i);

          //Case 1: If  1) the argument is NullExpression
          //            2) the parameter of matchedFuncHolder allows null input, or func's null_handling is NULL_IF_NULL (means null and non-null are exchangable).
          //        then replace NullExpression with a TypedNullConstant
          if (currentArg.equals(NullExpression.INSTANCE) &&
            ( parmType.getMode().equals(TypeProtos.DataMode.OPTIONAL) ||
              matchedFuncHolder.getNullHandling() == FunctionTemplate.NullHandling.NULL_IF_NULL)) {
            argsWithCast.add(new TypedNullConstant(parmType));
          } else if (Types.softEquals(parmType, currentArg.getMajorType(), matchedFuncHolder.getNullHandling() == FunctionTemplate.NullHandling.NULL_IF_NULL) ||
                     matchedFuncHolder.isFieldReader(i)) {
            //Case 2: argument and parameter matches, or parameter is FieldReader.  Do nothing.
            argsWithCast.add(currentArg);
          } else {
            //Case 3: insert cast if param type is different from arg type.
            if (CoreDecimalUtility.isDecimalType(parmType)) {
              // We are implicitly promoting a decimal type, set the required scale and precision
              parmType = MajorType.newBuilder().setMinorType(parmType.getMinorType()).setMode(parmType.getMode()).
                  setScale(currentArg.getMajorType().getScale()).setPrecision(currentArg.getMajorType().getPrecision()).build();
            }
            argsWithCast.add(addCastExpression(currentArg, parmType, registry, errorCollector));
          }
        }

        return matchedFuncHolder.getExpr(call.getName(), argsWithCast, call.getPosition());
      }

      // as no drill func is found, search for a non-Drill function.
      AbstractFuncHolder matchedNonDrillFuncHolder = registry.findNonDrillFunction(call);
      if (matchedNonDrillFuncHolder != null) {
        // Insert implicit cast function holder expressions if required
        List<LogicalExpression> extArgsWithCast = Lists.newArrayList();

        for (int i = 0; i < call.args.size(); ++i) {
          LogicalExpression currentArg = call.args.get(i);
          TypeProtos.MajorType parmType = matchedNonDrillFuncHolder.getParmMajorType(i);

          if (Types.softEquals(parmType, currentArg.getMajorType(), true)) {
            extArgsWithCast.add(currentArg);
          } else {
            // Insert cast if param type is different from arg type.
            if (CoreDecimalUtility.isDecimalType(parmType)) {
              // We are implicitly promoting a decimal type, set the required scale and precision
              parmType = MajorType.newBuilder().setMinorType(parmType.getMinorType()).setMode(parmType.getMode()).
                  setScale(currentArg.getMajorType().getScale()).setPrecision(currentArg.getMajorType().getPrecision()).build();
            }
            extArgsWithCast.add(addCastExpression(call.args.get(i), parmType, registry, errorCollector));
          }
        }

        return matchedNonDrillFuncHolder.getExpr(call.getName(), extArgsWithCast, call.getPosition());
      }

      logFunctionResolutionError(errorCollector, call);
      return NullExpression.INSTANCE;
    }

    @Override
    public LogicalExpression visitIfExpression(IfExpression ifExpr, FunctionImplementationRegistry registry) {
      IfExpression.IfCondition conditions = ifExpr.ifCondition;
      LogicalExpression newElseExpr = ifExpr.elseExpression.accept(this, registry);

      LogicalExpression newCondition = conditions.condition.accept(this, registry);
      LogicalExpression newExpr = conditions.expression.accept(this, registry);
      conditions = new IfExpression.IfCondition(newCondition, newExpr);

      MinorType thenType = conditions.expression.getMajorType().getMinorType();
      MinorType elseType = newElseExpr.getMajorType().getMinorType();

      // Check if we need a cast
      if (thenType != elseType && !(thenType == MinorType.NULL || elseType == MinorType.NULL)) {

        MinorType leastRestrictive = TypeCastRules.getLeastRestrictiveType((Arrays.asList(thenType, elseType)));
        if (leastRestrictive != thenType) {
          // Implicitly cast the then expression
          conditions = new IfExpression.IfCondition(newCondition,
          addCastExpression(conditions.expression, newElseExpr.getMajorType(), registry, errorCollector));
        } else if (leastRestrictive != elseType) {
          // Implicitly cast the else expression
          newElseExpr = addCastExpression(newElseExpr, conditions.expression.getMajorType(), registry, errorCollector);
        } else {
          /* Cannot cast one of the two expressions to make the output type of if and else expression
           * to be the same. Raise error.
           */
          throw new DrillRuntimeException("Case expression should have similar output type on all its branches");
        }
      }

      // Resolve NullExpression into TypedNullConstant by visiting all conditions
      // We need to do this because we want to give the correct MajorType to the Null constant
      List<LogicalExpression> allExpressions = Lists.newArrayList();
      allExpressions.add(conditions.expression);
      allExpressions.add(newElseExpr);

      boolean containsNullExpr = Iterables.any(allExpressions, new Predicate<LogicalExpression>() {
        @Override
        public boolean apply(LogicalExpression input) {
          return input instanceof NullExpression;
        }
      });

      if (containsNullExpr) {
        Optional<LogicalExpression> nonNullExpr = Iterables.tryFind(allExpressions,
          new Predicate<LogicalExpression>() {
            @Override
            public boolean apply(LogicalExpression input) {
              return !input.getMajorType().getMinorType().equals(TypeProtos.MinorType.NULL);
            }
          }
        );

        if(nonNullExpr.isPresent()) {
          MajorType type = nonNullExpr.get().getMajorType();
          conditions = new IfExpression.IfCondition(conditions.condition, rewriteNullExpression(conditions.expression, type));

          newElseExpr = rewriteNullExpression(newElseExpr, type);
        }
      }

      // If the type of the IF expression is nullable, apply a convertToNullable*Holder function for "THEN"/"ELSE"
      // expressions whose type is not nullable.
      if (IfExpression.newBuilder().setElse(newElseExpr).setIfCondition(conditions).build().getMajorType().getMode()
          == DataMode.OPTIONAL) {
          IfExpression.IfCondition condition = conditions;
          if (condition.expression.getMajorType().getMode() != DataMode.OPTIONAL) {
            conditions = new IfExpression.IfCondition(condition.condition, getConvertToNullableExpr(ImmutableList.of(condition.expression),
                                                      condition.expression.getMajorType().getMinorType(), registry));
         }

        if (newElseExpr.getMajorType().getMode() != DataMode.OPTIONAL) {
          newElseExpr = getConvertToNullableExpr(ImmutableList.of(newElseExpr),
              newElseExpr.getMajorType().getMinorType(), registry);
        }
      }

      return validateNewExpr(IfExpression.newBuilder().setElse(newElseExpr).setIfCondition(conditions).build());
    }

    private LogicalExpression getConvertToNullableExpr(List<LogicalExpression> args, MinorType minorType,
        FunctionImplementationRegistry registry) {
      String funcName = "convertToNullable" + minorType.toString();
      FunctionCall funcCall = new FunctionCall(funcName, args, ExpressionPosition.UNKNOWN);
      FunctionResolver resolver = FunctionResolverFactory.getResolver(funcCall);

      DrillFuncHolder matchedConvertToNullableFuncHolder = registry.findDrillFunction(resolver, funcCall);

      if (matchedConvertToNullableFuncHolder == null) {
        logFunctionResolutionError(errorCollector, funcCall);
        return NullExpression.INSTANCE;
      }

      return matchedConvertToNullableFuncHolder.getExpr(funcName, args, ExpressionPosition.UNKNOWN);
    }

    private LogicalExpression rewriteNullExpression(LogicalExpression expr, MajorType type) {
      if(expr instanceof NullExpression) {
        return new TypedNullConstant(type);
      } else {
        return expr;
      }
    }

    @Override
    public LogicalExpression visitSchemaPath(SchemaPath path, FunctionImplementationRegistry value) {
//      logger.debug("Visiting schema path {}", path);
      TypedFieldId tfId = batch.getValueVectorId(path);
      if (tfId == null) {
        logger.warn("Unable to find value vector of path {}, returning null instance.", path);
        return NullExpression.INSTANCE;
      } else {
        ValueVectorReadExpression e = new ValueVectorReadExpression(tfId);
        return e;
      }
    }

    @Override
    public LogicalExpression visitIntConstant(IntExpression intExpr, FunctionImplementationRegistry value) {
      return intExpr;
    }

    @Override
    public LogicalExpression visitFloatConstant(FloatExpression fExpr, FunctionImplementationRegistry value) {
      return fExpr;
    }

    @Override
    public LogicalExpression visitLongConstant(LongExpression intExpr, FunctionImplementationRegistry registry) {
      return intExpr;
    }

    @Override
    public LogicalExpression visitDateConstant(DateExpression intExpr, FunctionImplementationRegistry registry) {
      return intExpr;
    }

    @Override
    public LogicalExpression visitTimeConstant(TimeExpression intExpr, FunctionImplementationRegistry registry) {
      return intExpr;
    }

    @Override
    public LogicalExpression visitTimeStampConstant(TimeStampExpression intExpr, FunctionImplementationRegistry registry) {
      return intExpr;
    }

    @Override
    public LogicalExpression visitNullConstant(TypedNullConstant nullConstant, FunctionImplementationRegistry value) throws RuntimeException {
      return nullConstant;
    }

    @Override
    public LogicalExpression visitIntervalYearConstant(IntervalYearExpression intExpr, FunctionImplementationRegistry registry) {
      return intExpr;
    }

    @Override
    public LogicalExpression visitIntervalDayConstant(IntervalDayExpression intExpr, FunctionImplementationRegistry registry) {
      return intExpr;
    }

    @Override
    public LogicalExpression visitDecimal9Constant(Decimal9Expression decExpr, FunctionImplementationRegistry registry) {
      return decExpr;
    }

    @Override
    public LogicalExpression visitDecimal18Constant(Decimal18Expression decExpr, FunctionImplementationRegistry registry) {
      return decExpr;
    }

    @Override
    public LogicalExpression visitDecimal28Constant(Decimal28Expression decExpr, FunctionImplementationRegistry registry) {
      return decExpr;
    }

    @Override
    public LogicalExpression visitDecimal38Constant(Decimal38Expression decExpr, FunctionImplementationRegistry registry) {
      return decExpr;
    }

    @Override
    public LogicalExpression visitDoubleConstant(DoubleExpression dExpr, FunctionImplementationRegistry registry) {
      return dExpr;
    }

    @Override
    public LogicalExpression visitBooleanConstant(BooleanExpression e, FunctionImplementationRegistry registry) {
      return e;
    }

    @Override
    public LogicalExpression visitQuotedStringConstant(QuotedString e, FunctionImplementationRegistry registry) {
      return e;
    }

    @Override
    public LogicalExpression visitConvertExpression(ConvertExpression e, FunctionImplementationRegistry value) {
      String convertFunctionName = e.getConvertFunction() + e.getEncodingType();

      List<LogicalExpression> newArgs = Lists.newArrayList();
      newArgs.add(e.getInput());  //input_expr

      FunctionCall fc = new FunctionCall(convertFunctionName, newArgs, e.getPosition());
      return fc.accept(this, value);
    }

    @Override
    public LogicalExpression visitCastExpression(CastExpression e, FunctionImplementationRegistry value) {

      // if the cast is pointless, remove it.
      LogicalExpression input = e.getInput().accept(this,  value);

      MajorType newMajor = e.getMajorType(); // Output type
      MinorType newMinor = input.getMajorType().getMinorType(); // Input type

      if (castEqual(e.getPosition(), input.getMajorType(), newMajor)) {
        return input; // don't do pointless cast.
      }

      if (newMinor == MinorType.LATE) {
        // if the type still isn't fully bound, leave as cast expression.
        return new CastExpression(input, e.getMajorType(), e.getPosition());
      } else if (newMinor == MinorType.NULL) {
        // if input is a NULL expression, remove cast expression and return a TypedNullConstant directly.
        return new TypedNullConstant(Types.optional(e.getMajorType().getMinorType()));
      } else {
        // if the type is fully bound, convert to functioncall and materialze the function.
        MajorType type = e.getMajorType();

        // Get the cast function name from the map
        String castFuncWithType = CastFunctions.getCastFunc(type.getMinorType());

        List<LogicalExpression> newArgs = Lists.newArrayList();
        newArgs.add(e.getInput());  //input_expr

        //VarLen type
        if (!Types.isFixedWidthType(type)) {
          newArgs.add(new ValueExpressions.LongExpression(type.getWidth(), null));
        }  if (CoreDecimalUtility.isDecimalType(type)) {
            newArgs.add(new ValueExpressions.LongExpression(type.getPrecision(), null));
            newArgs.add(new ValueExpressions.LongExpression(type.getScale(), null));
        }
        FunctionCall fc = new FunctionCall(castFuncWithType, newArgs, e.getPosition());
        return fc.accept(this, value);
      }
    }

    private boolean castEqual(ExpressionPosition pos, MajorType from, MajorType to) {
      if (!from.getMinorType().equals(to.getMinorType())) {
        return false;
      }
      switch(from.getMinorType()) {
      case FLOAT4:
      case FLOAT8:
      case INT:
      case BIGINT:
      case BIT:
      case TINYINT:
      case SMALLINT:
      case UINT1:
      case UINT2:
      case UINT4:
      case UINT8:
      case TIME:
      case TIMESTAMP:
      case TIMESTAMPTZ:
      case DATE:
      case INTERVAL:
      case INTERVALDAY:
      case INTERVALYEAR:
        // nothing else matters.
        return true;
      case DECIMAL9:
      case DECIMAL18:
      case DECIMAL28DENSE:
      case DECIMAL28SPARSE:
      case DECIMAL38DENSE:
      case DECIMAL38SPARSE:
        if (to.getScale() == from.getScale() && to.getPrecision() == from.getPrecision()) {
          return true;
        }
        return false;

      case FIXED16CHAR:
      case FIXEDBINARY:
      case FIXEDCHAR:
        // width always matters
        this.errorCollector.addGeneralError(pos, "Casting fixed width types are not yet supported..");
        return false;

      case VAR16CHAR:
      case VARBINARY:
      case VARCHAR:
        // We could avoid redundant cast:
        // 1) when "to" length is no smaller than "from" length and "from" length is known (>0),
        // 2) or "to" length is unknown (0 means unknown length?).
        // Case 1 and case 2 mean that cast will do nothing.
        // In other cases, cast is required to trim the "from" according to "to" length.
        if ( (to.getWidth() >= from.getWidth() && from.getWidth() > 0) || to.getWidth() == 0) {
          return true;
        } else {
          return false;
        }

      default:
        errorCollector.addGeneralError(pos, String.format("Casting rules are unknown for type %s.", from));
        return false;
      }
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/expr/fn/FunctionImplementationRegistry.java
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
package org.apache.drill.exec.expr.fn;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.common.expression.FunctionCall;
import org.apache.drill.common.expression.fn.CastFunctions;
import org.apache.drill.common.types.TypeProtos;
import org.apache.drill.common.types.TypeProtos.MajorType;
import org.apache.drill.common.util.PathScanner;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.planner.sql.DrillOperatorTable;
import org.apache.drill.exec.resolver.FunctionResolver;

import com.google.common.base.Stopwatch;
import com.google.common.collect.Lists;
import org.apache.drill.exec.server.options.OptionManager;

public class FunctionImplementationRegistry {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(FunctionImplementationRegistry.class);

  private DrillFunctionRegistry drillFuncRegistry;
  private List<PluggableFunctionRegistry> pluggableFuncRegistries = Lists.newArrayList();
  private OptionManager optionManager = null;

  public FunctionImplementationRegistry(DrillConfig config){
    Stopwatch w = new Stopwatch().start();

    logger.debug("Generating function registry.");
    drillFuncRegistry = new DrillFunctionRegistry(config);

    Set<Class<? extends PluggableFunctionRegistry>> registryClasses = PathScanner.scanForImplementations(
        PluggableFunctionRegistry.class, config.getStringList(ExecConstants.FUNCTION_PACKAGES));

    for (Class<? extends PluggableFunctionRegistry> clazz : registryClasses) {
      for (Constructor<?> c : clazz.getConstructors()) {
        Class<?>[] params = c.getParameterTypes();
        if (params.length != 1 || params[0] != DrillConfig.class) {
          logger.warn("Skipping PluggableFunctionRegistry constructor {} for class {} since it doesn't implement a " +
              "[constructor(DrillConfig)]", c, clazz);
          continue;
        }

        try {
          PluggableFunctionRegistry registry = (PluggableFunctionRegistry)c.newInstance(config);
          pluggableFuncRegistries.add(registry);
        } catch(InstantiationException | IllegalAccessException | IllegalArgumentException | InvocationTargetException e) {
          logger.warn("Unable to instantiate PluggableFunctionRegistry class '{}'. Skipping it.", clazz, e);
        }

        break;
      }
    }
    logger.info("Function registry loaded.  {} functions loaded in {} ms.", drillFuncRegistry.size(), w.elapsed(TimeUnit.MILLISECONDS));
  }

  public FunctionImplementationRegistry(DrillConfig config, OptionManager optionManager) {
    this(config);
    this.optionManager = optionManager;
  }

  /**
   * Register functions in given operator table.
   * @param operatorTable
   */
  public void register(DrillOperatorTable operatorTable) {
    // Register Drill functions first and move to pluggable function registries.
    drillFuncRegistry.register(operatorTable);

    for(PluggableFunctionRegistry registry : pluggableFuncRegistries) {
      registry.register(operatorTable);
    }
  }

  /**
   * Using the given <code>functionResolver</code> find Drill function implementation for given
   * <code>functionCall</code>
   *
   * @param functionResolver
   * @param functionCall
   * @return
   */
  public DrillFuncHolder findDrillFunction(FunctionResolver functionResolver, FunctionCall functionCall) {
    return functionResolver.getBestMatch(drillFuncRegistry.getMethods(functionReplacement(functionCall)), functionCall);
  }

  // Check if this Function Replacement is needed; if yes, return a new name. otherwise, return the original name
  private String functionReplacement(FunctionCall functionCall) {
    String funcName = functionCall.getName();
    if (optionManager != null
        && optionManager.getOption(ExecConstants.CAST_TO_NULLABLE_NUMERIC).bool_val
        && CastFunctions.isReplacementNeeded(functionCall.args.get(0).getMajorType().getMinorType(),
                                             funcName)) {
      org.apache.drill.common.types.TypeProtos.DataMode dataMode =
          functionCall.args.get(0).getMajorType().getMode();
      funcName = CastFunctions.getReplacingCastFunction(funcName, dataMode);
    }

    return funcName;
  }

  /**
   * Find the Drill function implementation that matches the name, arg types and return type.
   * @param name
   * @param argTypes
   * @param returnType
   * @return
   */
  public DrillFuncHolder findExactMatchingDrillFunction(String name, List<MajorType> argTypes, MajorType returnType) {
    for (DrillFuncHolder h : drillFuncRegistry.getMethods(name)) {
      if (h.matches(returnType, argTypes)) {
        return h;
      }
    }

    return null;
  }

  /**
   * Find function implementation for given <code>functionCall</code> in non-Drill function registries such as Hive UDF
   * registry.
   *
   * Note: Order of searching is same as order of {@link org.apache.drill.exec.expr.fn.PluggableFunctionRegistry}
   * implementations found on classpath.
   *
   * @param functionCall
   * @return
   */
  public AbstractFuncHolder findNonDrillFunction(FunctionCall functionCall) {
    for(PluggableFunctionRegistry registry : pluggableFuncRegistries) {
      AbstractFuncHolder h = registry.getFunction(functionCall);
      if (h != null) {
        return h;
      }
    }

    return null;
  }

  // Method to find if the output type of a drill function if of complex type
  public boolean isFunctionComplexOutput(String name) {
    List<DrillFuncHolder> methods = drillFuncRegistry.getMethods(name);
    for (DrillFuncHolder holder : methods) {
      if (holder.getReturnValue().isComplexWriter()) {
        return true;
      }
    }
    return false;
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/ops/QueryContext.java
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
package org.apache.drill.exec.ops;

import java.io.IOException;
import java.util.Collection;
import java.util.List;

import com.google.common.collect.Lists;
import io.netty.buffer.DrillBuf;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.jdbc.SimpleCalciteSchema;

import org.apache.drill.common.AutoCloseables;
import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.expr.fn.FunctionImplementationRegistry;
import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.planner.sql.DrillOperatorTable;
import org.apache.drill.exec.proto.BitControl.QueryContextInformation;
import org.apache.drill.exec.proto.CoordinationProtos.DrillbitEndpoint;
import org.apache.drill.exec.rpc.user.UserSession;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.server.options.OptionManager;
import org.apache.drill.exec.server.options.QueryOptionManager;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.store.PartitionExplorer;
import org.apache.drill.exec.store.PartitionExplorerImpl;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.drill.exec.testing.ExecutionControls;
import org.apache.drill.exec.util.ImpersonationUtil;
import org.apache.drill.exec.util.Utilities;

// TODO except for a couple of tests, this is only created by Foreman
// TODO the many methods that just return drillbitContext.getXxx() should be replaced with getDrillbitContext()
// TODO - consider re-name to PlanningContext, as the query execution context actually appears
// in fragment contexts
public class QueryContext implements AutoCloseable, UdfUtilities {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(QueryContext.class);

  private static final int INITIAL_OFF_HEAP_ALLOCATION_IN_BYTES = 1024 * 1024;
  private static final int MAX_OFF_HEAP_ALLOCATION_IN_BYTES = 256 * 1024 * 1024;

  private final DrillbitContext drillbitContext;
  private final UserSession session;
  private final OptionManager queryOptions;
  private final PlannerSettings plannerSettings;
  private final DrillOperatorTable table;
  private final ExecutionControls executionControls;

  private final BufferAllocator allocator;
  private final BufferManager bufferManager;
  private final ContextInformation contextInformation;
  private final QueryContextInformation queryContextInfo;
  private final ViewExpansionContext viewExpansionContext;

  private final List<SchemaPlus> schemaTreesToClose;

  /*
   * Flag to indicate if close has been called, after calling close the first
   * time this is set to true and the close method becomes a no-op.
   */
  private boolean closed = false;

  public QueryContext(final UserSession session, final DrillbitContext drillbitContext) {
    this.drillbitContext = drillbitContext;
    this.session = session;
    queryOptions = new QueryOptionManager(session.getOptions());
    executionControls = new ExecutionControls(queryOptions, drillbitContext.getEndpoint());
    plannerSettings = new PlannerSettings(queryOptions, getFunctionRegistry());
    plannerSettings.setNumEndPoints(drillbitContext.getBits().size());
    table = new DrillOperatorTable(getFunctionRegistry());

    queryContextInfo = Utilities.createQueryContextInfo(session.getDefaultSchemaName());
    contextInformation = new ContextInformation(session.getCredentials(), queryContextInfo);

    try {
      allocator = drillbitContext.getAllocator().getChildAllocator(null, INITIAL_OFF_HEAP_ALLOCATION_IN_BYTES,
          MAX_OFF_HEAP_ALLOCATION_IN_BYTES, false);
    } catch (OutOfMemoryException e) {
      throw new DrillRuntimeException("Error creating off-heap allocator for planning context.",e);
    }
    // TODO(DRILL-1942) the new allocator has this capability built-in, so this can be removed once that is available
    bufferManager = new BufferManager(this.allocator, null);
    viewExpansionContext = new ViewExpansionContext(this);
    schemaTreesToClose = Lists.newArrayList();
  }

  public PlannerSettings getPlannerSettings() {
    return plannerSettings;
  }

  public UserSession getSession() {
    return session;
  }

  public BufferAllocator getAllocator() {
    return allocator;
  }

  /**
   * Return reference to default schema instance in a schema tree. Each {@link org.apache.calcite.schema.SchemaPlus}
   * instance can refer to its parent and its children. From the returned reference to default schema instance,
   * clients can traverse the entire schema tree and know the default schema where to look up the tables first.
   *
   * @return Reference to default schema instance in a schema tree.
   */
  public SchemaPlus getNewDefaultSchema() {
    final SchemaPlus rootSchema = getRootSchema();
    final SchemaPlus defaultSchema = session.getDefaultSchema(rootSchema);
    if (defaultSchema == null) {
      return rootSchema;
    }

    return defaultSchema;
  }

  /**
   * Get root schema with schema owner as the user who issued the query that is managed by this QueryContext.
   * @return Root of the schema tree.
   */
  public SchemaPlus getRootSchema() {
    return getRootSchema(getQueryUserName());
  }

  /**
   * Return root schema with schema owner as the given user.
   *
   * @param userName User who owns the schema tree.
   * @return Root of the schema tree.
   */
  public SchemaPlus getRootSchema(final String userName) {
    final String schemaUser = isImpersonationEnabled() ? userName : ImpersonationUtil.getProcessUserName();
    final SchemaConfig schemaConfig = SchemaConfig.newBuilder(schemaUser, this).build();
    return getRootSchema(schemaConfig);
  }

  /**
   *  Create and return a SchemaTree with given <i>schemaConfig</i>.
   * @param schemaConfig
   * @return
   */
  public SchemaPlus getRootSchema(SchemaConfig schemaConfig) {
    try {
      final SchemaPlus rootSchema = SimpleCalciteSchema.createRootSchema(false);
      drillbitContext.getSchemaFactory().registerSchemas(schemaConfig, rootSchema);
      schemaTreesToClose.add(rootSchema);
      return rootSchema;
    } catch(IOException e) {
      // We can't proceed further without a schema, throw a runtime exception.
      final String errMsg = String.format("Failed to create schema tree: %s", e.getMessage());
      logger.error(errMsg, e);
      throw new DrillRuntimeException(errMsg, e);
    }
  }

  /**
   * Get the user name of the user who issued the query that is managed by this QueryContext.
   * @return
   */
  public String getQueryUserName() {
    return session.getCredentials().getUserName();
  }

  public OptionManager getOptions() {
    return queryOptions;
  }

  public ExecutionControls getExecutionControls() {
    return executionControls;
  }

  public DrillbitEndpoint getCurrentEndpoint() {
    return drillbitContext.getEndpoint();
  }

  public StoragePluginRegistry getStorage() {
    return drillbitContext.getStorage();
  }

  public Collection<DrillbitEndpoint> getActiveEndpoints() {
    return drillbitContext.getBits();
  }

  public DrillConfig getConfig() {
    return drillbitContext.getConfig();
  }

  public FunctionImplementationRegistry getFunctionRegistry() {
    return drillbitContext.getFunctionImplementationRegistry();
  }

  public ViewExpansionContext getViewExpansionContext() {
    return viewExpansionContext;
  }

  public boolean isImpersonationEnabled() {
     return getConfig().getBoolean(ExecConstants.IMPERSONATION_ENABLED);
  }

  public DrillOperatorTable getDrillOperatorTable() {
    return table;
  }

  public QueryContextInformation getQueryContextInfo() {
    return queryContextInfo;
  }

  @Override
  public ContextInformation getContextInformation() {
    return contextInformation;
  }

  @Override
  public DrillBuf getManagedBuffer() {
    return bufferManager.getManagedBuffer();
  }

  @Override
  public PartitionExplorer getPartitionExplorer() {
    return new PartitionExplorerImpl(getRootSchema());
  }

  @Override
  public void close() throws Exception {
    try {
      if (!closed) {
        List<AutoCloseable> toClose = Lists.newArrayList();

        // TODO(DRILL-1942) the new allocator has this capability built-in, so we can remove bufferManager and
        // allocator from the toClose list.
        toClose.add(bufferManager);
        toClose.add(allocator);

        for(SchemaPlus tree : schemaTreesToClose) {
          addSchemasToCloseList(tree, toClose);
        }

        AutoCloseables.close(toClose.toArray(new AutoCloseable[0]));
      }
    } finally {
      closed = true;
    }
  }

  private void addSchemasToCloseList(final SchemaPlus tree, final List<AutoCloseable> toClose) {
    for(String subSchemaName : tree.getSubSchemaNames()) {
      addSchemasToCloseList(tree.getSubSchema(subSchemaName), toClose);
    }

    try {
      AbstractSchema drillSchemaImpl =  tree.unwrap(AbstractSchema.class);
      toClose.add(drillSchemaImpl);
    } catch (ClassCastException e) {
      // Ignore as the SchemaPlus is not an implementation of Drill schema.
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/logical/DrillRuleSets.java
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
package org.apache.drill.exec.planner.logical;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import org.apache.calcite.rel.rules.AggregateExpandDistinctAggregatesRule;
import org.apache.calcite.rel.rules.AggregateRemoveRule;
import org.apache.calcite.rel.rules.FilterSetOpTransposeRule;
import org.apache.calcite.rel.rules.JoinPushThroughJoinRule;
import org.apache.calcite.rel.rules.ProjectRemoveRule;
import org.apache.calcite.rel.rules.ReduceExpressionsRule;
import org.apache.calcite.rel.rules.SortRemoveRule;
import org.apache.calcite.rel.rules.UnionToDistinctRule;
import org.apache.calcite.tools.RuleSet;

import org.apache.calcite.rel.rules.FilterMergeRule;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.planner.logical.partition.PruneScanRule;
import org.apache.drill.exec.planner.physical.ConvertCountToDirectScan;
import org.apache.drill.exec.planner.physical.FilterPrule;
import org.apache.drill.exec.planner.physical.HashAggPrule;
import org.apache.drill.exec.planner.physical.HashJoinPrule;
import org.apache.drill.exec.planner.physical.LimitPrule;
import org.apache.drill.exec.planner.physical.MergeJoinPrule;
import org.apache.drill.exec.planner.physical.NestedLoopJoinPrule;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.planner.physical.ProjectPrule;
import org.apache.drill.exec.planner.physical.PushLimitToTopN;
import org.apache.drill.exec.planner.physical.ScanPrule;
import org.apache.drill.exec.planner.physical.ScreenPrule;
import org.apache.drill.exec.planner.physical.SortConvertPrule;
import org.apache.drill.exec.planner.physical.SortPrule;
import org.apache.drill.exec.planner.physical.StreamAggPrule;
import org.apache.drill.exec.planner.physical.ValuesPrule;
import org.apache.drill.exec.planner.physical.WindowPrule;
import org.apache.drill.exec.planner.physical.UnionAllPrule;
import org.apache.drill.exec.planner.physical.WriterPrule;
import org.apache.calcite.rel.core.RelFactories;
import org.apache.calcite.plan.RelOptRule;
import org.apache.calcite.plan.volcano.AbstractConverter.ExpandConversionRule;

import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSet.Builder;

public class DrillRuleSets {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(DrillRuleSets.class);

  public static RuleSet DRILL_BASIC_RULES = null;

  /**
   * Get a list of logical rules that can be turned on or off by session/system options.
   *
   * If a rule is intended to always be included with the logical set, it should be added
   * to the immutable list created in the getDrillBasicRules() method below.
   *
   * @param queryContext - used to get the list of planner settings, other rules may
   *                     also in the future need to get other query state from this,
   *                     such as the available list of UDFs (as is used by the
   *                     DrillMergeProjectRule created in getDrillBasicRules())
   * @return - a list of rules that have been filtered to leave out
   *         rules that have been turned off by system or session settings
   */
  public static RuleSet getDrillUserConfigurableLogicalRules(QueryContext queryContext) {
    PlannerSettings ps = queryContext.getPlannerSettings();

    // This list is used to store rules that can be turned on an off
    // by user facing planning options
    Builder userConfigurableRules = ImmutableSet.<RelOptRule>builder();

    if (ps.isConstantFoldingEnabled()) {
      // TODO - DRILL-2218
      userConfigurableRules.add(ReduceExpressionsRule.PROJECT_INSTANCE);

      userConfigurableRules.add(DrillReduceExpressionsRule.FILTER_INSTANCE_DRILL);
      userConfigurableRules.add(DrillReduceExpressionsRule.CALC_INSTANCE_DRILL);
    }

    return new DrillRuleSet(userConfigurableRules.build());
  }

  /**
   * Get an immutable list of rules that will always be used when running
   * logical planning.
   *
   * This would be a static member, rather than a method, but some of
   * the rules need a reference to state that isn't available at class
   * load time. The current example is the DrillMergeProjectRule which
   * needs access to the registry of Drill UDFs, which is populated by
   * scanning the class path a Drillbit startup.
   *
   * If a logical rule needs to be user configurable, such as turning
   * it on and off with a system/session option, add it in the
   * getDrillUserConfigurableLogicalRules() method instead of here.
   *
   * @param context - shared state used during planning, currently used here
   *                to gain access to the fucntion registry described above.
   * @return - a RuleSet containing the logical rules that will always
   *           be used, either by VolcanoPlanner directly, or
   *           used VolcanoPlanner as pre-processing for LOPTPlanner.
   *
   * Note : Join permutation rule is excluded here.
   */
  public static RuleSet getDrillBasicRules(QueryContext context) {
    if (DRILL_BASIC_RULES == null) {

      DRILL_BASIC_RULES = new DrillRuleSet(ImmutableSet.<RelOptRule> builder().add( //
      // Add support for Distinct Union (by using Union-All followed by Distinct)
      UnionToDistinctRule.INSTANCE,

      // Add support for WHERE style joins.
      DrillFilterJoinRules.DRILL_FILTER_ON_JOIN,
      DrillFilterJoinRules.DRILL_JOIN,
      // End support for WHERE style joins.

      /*
       Filter push-down related rules
       */
      DrillPushFilterPastProjectRule.INSTANCE,
      FilterSetOpTransposeRule.INSTANCE,

      FilterMergeRule.INSTANCE,
      AggregateRemoveRule.INSTANCE,
      ProjectRemoveRule.NAME_CALC_INSTANCE,
      SortRemoveRule.INSTANCE,

      DrillMergeProjectRule.getInstance(true, RelFactories.DEFAULT_PROJECT_FACTORY, context.getFunctionRegistry()),
      AggregateExpandDistinctAggregatesRule.INSTANCE,
      DrillReduceAggregatesRule.INSTANCE,

      /*
       Projection push-down related rules
       */
      DrillPushProjectPastFilterRule.INSTANCE,
      DrillPushProjectPastJoinRule.INSTANCE,
      DrillPushProjIntoScan.INSTANCE,
      DrillProjectSetOpTransposeRule.INSTANCE,

      PruneScanRule.getFilterOnProject(context),
      PruneScanRule.getFilterOnScan(context),
      PruneScanRule.getFilterOnProjectParquet(context),
      PruneScanRule.getFilterOnScanParquet(context),

      /*
       Convert from Calcite Logical to Drill Logical Rules.
       */
      ExpandConversionRule.INSTANCE,
      DrillScanRule.INSTANCE,
      DrillFilterRule.INSTANCE,
      DrillProjectRule.INSTANCE,
      DrillWindowRule.INSTANCE,
      DrillAggregateRule.INSTANCE,

      DrillLimitRule.INSTANCE,
      DrillSortRule.INSTANCE,
      DrillJoinRule.INSTANCE,
      DrillUnionAllRule.INSTANCE,
      DrillValuesRule.INSTANCE
      )
      .build());
    }

    return DRILL_BASIC_RULES;
  }

  // Ruleset for join permutation, used only in VolcanoPlanner.
  public static RuleSet getJoinPermRules(QueryContext context) {
    return new DrillRuleSet(ImmutableSet.<RelOptRule> builder().add( //
        JoinPushThroughJoinRule.RIGHT,
        JoinPushThroughJoinRule.LEFT
        ).build());
  }

  public static final RuleSet DRILL_PHYSICAL_DISK = new DrillRuleSet(ImmutableSet.of( //
      ProjectPrule.INSTANCE

    ));

  public static final RuleSet getPhysicalRules(QueryContext qcontext) {
    List<RelOptRule> ruleList = new ArrayList<RelOptRule>();

    PlannerSettings ps = qcontext.getPlannerSettings();

    ruleList.add(ConvertCountToDirectScan.AGG_ON_PROJ_ON_SCAN);
    ruleList.add(ConvertCountToDirectScan.AGG_ON_SCAN);
    ruleList.add(SortConvertPrule.INSTANCE);
    ruleList.add(SortPrule.INSTANCE);
    ruleList.add(ProjectPrule.INSTANCE);
    ruleList.add(ScanPrule.INSTANCE);
    ruleList.add(ScreenPrule.INSTANCE);
    ruleList.add(ExpandConversionRule.INSTANCE);
    ruleList.add(FilterPrule.INSTANCE);
    ruleList.add(LimitPrule.INSTANCE);
    ruleList.add(WriterPrule.INSTANCE);
    ruleList.add(WindowPrule.INSTANCE);
    ruleList.add(PushLimitToTopN.INSTANCE);
    ruleList.add(UnionAllPrule.INSTANCE);
    ruleList.add(ValuesPrule.INSTANCE);

    if (ps.isHashAggEnabled()) {
      ruleList.add(HashAggPrule.INSTANCE);
    }

    if (ps.isStreamAggEnabled()) {
      ruleList.add(StreamAggPrule.INSTANCE);
    }

    if (ps.isHashJoinEnabled()) {
      ruleList.add(HashJoinPrule.DIST_INSTANCE);

      if(ps.isBroadcastJoinEnabled()){
        ruleList.add(HashJoinPrule.BROADCAST_INSTANCE);
      }
    }

    if (ps.isMergeJoinEnabled()) {
      ruleList.add(MergeJoinPrule.DIST_INSTANCE);

      if(ps.isBroadcastJoinEnabled()){
        ruleList.add(MergeJoinPrule.BROADCAST_INSTANCE);
      }

    }

    // NLJ plans consist of broadcasting the right child, hence we need
    // broadcast join enabled.
    if (ps.isNestedLoopJoinEnabled() && ps.isBroadcastJoinEnabled()) {
      ruleList.add(NestedLoopJoinPrule.INSTANCE);
    }

    return new DrillRuleSet(ImmutableSet.copyOf(ruleList));
  }

  public static RuleSet create(ImmutableSet<RelOptRule> rules) {
    return new DrillRuleSet(rules);
  }

  public static RuleSet mergedRuleSets(RuleSet...ruleSets) {
    Builder<RelOptRule> relOptRuleSetBuilder = ImmutableSet.builder();
    for (RuleSet ruleSet : ruleSets) {
      for (RelOptRule relOptRule : ruleSet) {
        relOptRuleSetBuilder.add(relOptRule);
      }
    }
    return new DrillRuleSet(relOptRuleSetBuilder.build());
  }

  private static class DrillRuleSet implements RuleSet{
    final ImmutableSet<RelOptRule> rules;

    public DrillRuleSet(ImmutableSet<RelOptRule> rules) {
      super();
      this.rules = rules;
    }

    @Override
    public Iterator<RelOptRule> iterator() {
      return rules.iterator();
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/logical/partition/PruneScanRule.java
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
package org.apache.drill.exec.planner.logical.partition;

import java.util.ArrayList;
import java.util.BitSet;
 import java.util.Collections;
 import java.util.Iterator;
 import java.util.List;
 import java.util.Map;

 import org.apache.calcite.rex.RexUtil;
 import org.apache.calcite.util.BitSets;

 import org.apache.drill.common.expression.ErrorCollectorImpl;
 import org.apache.drill.common.expression.LogicalExpression;
 import org.apache.drill.common.expression.SchemaPath;
 import org.apache.drill.common.types.TypeProtos.MajorType;
 import org.apache.drill.common.types.TypeProtos.MinorType;
 import org.apache.drill.common.types.Types;
 import org.apache.drill.exec.expr.ExpressionTreeMaterializer;
 import org.apache.drill.exec.expr.TypeHelper;
 import org.apache.drill.exec.expr.fn.interpreter.InterpreterEvaluator;
 import org.apache.drill.exec.memory.BufferAllocator;
 import org.apache.drill.exec.ops.QueryContext;
 import org.apache.drill.exec.physical.base.FileGroupScan;
 import org.apache.drill.exec.physical.base.GroupScan;
 import org.apache.drill.exec.planner.FileSystemPartitionDescriptor;
import org.apache.drill.exec.planner.ParquetPartitionDescriptor;
import org.apache.drill.exec.planner.PartitionDescriptor;
 import org.apache.drill.exec.planner.logical.DrillFilterRel;
 import org.apache.drill.exec.planner.logical.DrillOptiq;
 import org.apache.drill.exec.planner.logical.DrillParseContext;
 import org.apache.drill.exec.planner.logical.DrillProjectRel;
 import org.apache.drill.exec.planner.logical.DrillRel;
 import org.apache.drill.exec.planner.logical.DrillScanRel;
 import org.apache.drill.exec.planner.logical.RelOptHelper;
 import org.apache.drill.exec.planner.physical.PlannerSettings;
 import org.apache.drill.exec.planner.physical.PrelUtil;
 import org.apache.drill.exec.record.MaterializedField;
 import org.apache.drill.exec.record.VectorContainer;
 import org.apache.drill.exec.store.dfs.FileSelection;
import org.apache.drill.exec.store.dfs.FormatSelection;
import org.apache.drill.exec.store.parquet.ParquetGroupScan;
import org.apache.drill.exec.vector.NullableBitVector;
 import org.apache.drill.exec.vector.NullableVarCharVector;
 import org.apache.calcite.rel.RelNode;
 import org.apache.calcite.plan.RelOptRule;
 import org.apache.calcite.plan.RelOptRuleCall;
 import org.apache.calcite.plan.RelOptRuleOperand;
 import org.apache.calcite.plan.RelOptUtil;
 import org.apache.calcite.rex.RexNode;

 import com.google.common.base.Charsets;
 import com.google.common.collect.Lists;
 import com.google.common.collect.Maps;
 import org.apache.drill.exec.vector.ValueVector;

public abstract class PruneScanRule extends RelOptRule {
   static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(PruneScanRule.class);

   public static final RelOptRule getFilterOnProject(QueryContext context){
       return new PruneScanRule(
           RelOptHelper.some(DrillFilterRel.class, RelOptHelper.some(DrillProjectRel.class, RelOptHelper.any(DrillScanRel.class))),
           "PruneScanRule:Filter_On_Project",
           context) {

       @Override
         public boolean matches(RelOptRuleCall call) {
           final DrillScanRel scan = (DrillScanRel) call.rel(2);
           GroupScan groupScan = scan.getGroupScan();
           // this rule is applicable only for dfs based partition pruning
           return groupScan instanceof FileGroupScan && groupScan.supportsPartitionFilterPushdown();
         }

       @Override
       public void onMatch(RelOptRuleCall call) {
         final DrillFilterRel filterRel = (DrillFilterRel) call.rel(0);
         final DrillProjectRel projectRel = (DrillProjectRel) call.rel(1);
         final DrillScanRel scanRel = (DrillScanRel) call.rel(2);
         doOnMatch(call, filterRel, projectRel, scanRel);
       };

         @Override
         protected PartitionDescriptor getPartitionDescriptor(PlannerSettings settings, DrillScanRel scanRel) {
           return new FileSystemPartitionDescriptor(settings.getFsPartitionColumnLabel());
         }

         @Override
         protected void populatePartitionVectors(ValueVector[] vectors, List<PathPartition> partitions, BitSet partitionColumnBitSet, Map<Integer, String> fieldNameMap, GroupScan groupScan) {
           int record = 0;
           for(Iterator<PathPartition> iter = partitions.iterator(); iter.hasNext(); record++){
             final PathPartition partition = iter.next();
             for(int partitionColumnIndex : BitSets.toIter(partitionColumnBitSet)){
               if(partition.dirs[partitionColumnIndex] == null){
                 ((NullableVarCharVector) vectors[partitionColumnIndex]).getMutator().setNull(record);
               }else{
                 byte[] bytes = partition.dirs[partitionColumnIndex].getBytes(Charsets.UTF_8);
                 ((NullableVarCharVector) vectors[partitionColumnIndex]).getMutator().setSafe(record, bytes, 0, bytes.length);
               }
             }
           }

           for(ValueVector v : vectors){
             if(v == null){
               continue;
             }
             v.getMutator().setValueCount(partitions.size());
           }
         }

         @Override
         protected MajorType getVectorType(GroupScan groupScan, SchemaPath column) {
           return Types.optional(MinorType.VARCHAR);
         }

         @Override
         protected List<String> getFiles(DrillScanRel scanRel) {
           return ((FormatSelection)scanRel.getDrillTable().getSelection()).getAsFiles();
         }
       };
   }

   public static final RelOptRule getFilterOnScan(QueryContext context){
     return new PruneScanRule(
           RelOptHelper.some(DrillFilterRel.class, RelOptHelper.any(DrillScanRel.class)),
           "PruneScanRule:Filter_On_Scan", context) {

       @Override
         public boolean matches(RelOptRuleCall call) {
           final DrillScanRel scan = (DrillScanRel) call.rel(1);
           GroupScan groupScan = scan.getGroupScan();
           // this rule is applicable only for dfs based partition pruning
           return groupScan instanceof FileGroupScan && groupScan.supportsPartitionFilterPushdown();
         }

       @Override
       public void onMatch(RelOptRuleCall call) {
         final DrillFilterRel filterRel = (DrillFilterRel) call.rel(0);
         final DrillScanRel scanRel = (DrillScanRel) call.rel(1);
         doOnMatch(call, filterRel, null, scanRel);
       }

       @Override
       protected PartitionDescriptor getPartitionDescriptor(PlannerSettings settings, DrillScanRel scanRel) {
         return new FileSystemPartitionDescriptor(settings.getFsPartitionColumnLabel());
       }

       @Override
       protected void populatePartitionVectors(ValueVector[] vectors, List<PathPartition> partitions, BitSet partitionColumnBitSet, Map<Integer, String> fieldNameMap, GroupScan groupScan) {
         int record = 0;
         for(Iterator<PathPartition> iter = partitions.iterator(); iter.hasNext(); record++){
           final PathPartition partition = iter.next();
           for(int partitionColumnIndex : BitSets.toIter(partitionColumnBitSet)){
             if(partition.dirs[partitionColumnIndex] == null){
               ((NullableVarCharVector) vectors[partitionColumnIndex]).getMutator().setNull(record);
             }else{
               byte[] bytes = partition.dirs[partitionColumnIndex].getBytes(Charsets.UTF_8);
               ((NullableVarCharVector) vectors[partitionColumnIndex]).getMutator().setSafe(record, bytes, 0, bytes.length);
             }
           }
         }

         for(ValueVector v : vectors){
           if(v == null){
             continue;
           }
           v.getMutator().setValueCount(partitions.size());
         }
       }

       @Override
        protected MajorType getVectorType(GroupScan groupScan, SchemaPath column) {
          return Types.optional(MinorType.VARCHAR);
        }

       @Override
       protected List<String> getFiles(DrillScanRel scanRel) {
         return ((FormatSelection)scanRel.getDrillTable().getSelection()).getAsFiles();
       }
     };
   }

  public static final RelOptRule getFilterOnProjectParquet(QueryContext context){
    return new PruneScanRule(
        RelOptHelper.some(DrillFilterRel.class, RelOptHelper.some(DrillProjectRel.class, RelOptHelper.any(DrillScanRel.class))),
        "PruneScanRule:Filter_On_Project_Parquet",
        context) {

      @Override
      public boolean matches(RelOptRuleCall call) {
        final DrillScanRel scan = (DrillScanRel) call.rel(2);
        GroupScan groupScan = scan.getGroupScan();
        // this rule is applicable only for dfs based partition pruning
        return groupScan instanceof FileGroupScan && groupScan.supportsPartitionFilterPushdown();
      }

      @Override
      public void onMatch(RelOptRuleCall call) {
        final DrillFilterRel filterRel = (DrillFilterRel) call.rel(0);
        final DrillProjectRel projectRel = (DrillProjectRel) call.rel(1);
        final DrillScanRel scanRel = (DrillScanRel) call.rel(2);
        doOnMatch(call, filterRel, projectRel, scanRel);
      };

      @Override
      protected PartitionDescriptor getPartitionDescriptor(PlannerSettings settings, DrillScanRel scanRel) {
        return new ParquetPartitionDescriptor(scanRel.getGroupScan().getPartitionColumns());
      }

      @Override
      protected void populatePartitionVectors(ValueVector[] vectors, List<PathPartition> partitions, BitSet partitionColumnBitSet, Map<Integer, String> fieldNameMap, GroupScan groupScan) {
        int record = 0;
        for(Iterator<PathPartition> iter = partitions.iterator(); iter.hasNext(); record++){
          final PathPartition partition = iter.next();
          for(int partitionColumnIndex : BitSets.toIter(partitionColumnBitSet)){
            SchemaPath column = SchemaPath.getSimplePath(fieldNameMap.get(partitionColumnIndex));
            ((ParquetGroupScan)groupScan).populatePruningVector(vectors[partitionColumnIndex], record, column, partition.file);
          }
        }

        for(ValueVector v : vectors){
          if(v == null){
            continue;
          }
          v.getMutator().setValueCount(partitions.size());
        }
      }

      @Override
      protected MajorType getVectorType(GroupScan groupScan, SchemaPath column) {
        return ((ParquetGroupScan)groupScan).getTypeForColumn(column);
      }

      @Override
      protected List<String> getFiles(DrillScanRel scanRel) {
        ParquetGroupScan groupScan = (ParquetGroupScan) scanRel.getGroupScan();
        return new ArrayList(groupScan.getFileSet());
      }
    };
  }

  // Using separate rules for Parquet column based partition pruning. In the future, we may want to see if we can combine these into
  // a single rule which handles both types of pruning

  public static final RelOptRule getFilterOnScanParquet(QueryContext context){
    return new PruneScanRule(
        RelOptHelper.some(DrillFilterRel.class, RelOptHelper.any(DrillScanRel.class)),
        "PruneScanRule:Filter_On_Scan_Parquet", context) {

      @Override
      public boolean matches(RelOptRuleCall call) {
        final DrillScanRel scan = (DrillScanRel) call.rel(1);
        GroupScan groupScan = scan.getGroupScan();
        // this rule is applicable only for dfs based partition pruning
        return groupScan instanceof FileGroupScan && groupScan.supportsPartitionFilterPushdown();
      }

      @Override
      public void onMatch(RelOptRuleCall call) {
        final DrillFilterRel filterRel = (DrillFilterRel) call.rel(0);
        final DrillScanRel scanRel = (DrillScanRel) call.rel(1);
        doOnMatch(call, filterRel, null, scanRel);
      }

      @Override
      protected PartitionDescriptor getPartitionDescriptor(PlannerSettings settings, DrillScanRel scanRel) {
        return new ParquetPartitionDescriptor(scanRel.getGroupScan().getPartitionColumns());
      }

      @Override
      protected void populatePartitionVectors(ValueVector[] vectors, List<PathPartition> partitions, BitSet partitionColumnBitSet, Map<Integer, String> fieldNameMap, GroupScan groupScan) {
        int record = 0;
        for(Iterator<PathPartition> iter = partitions.iterator(); iter.hasNext(); record++){
          final PathPartition partition = iter.next();
          for(int partitionColumnIndex : BitSets.toIter(partitionColumnBitSet)){
            SchemaPath column = SchemaPath.getSimplePath(fieldNameMap.get(partitionColumnIndex));
            ((ParquetGroupScan)groupScan).populatePruningVector(vectors[partitionColumnIndex], record, column, partition.file);
          }
        }

        for(ValueVector v : vectors){
          if(v == null){
            continue;
          }
          v.getMutator().setValueCount(partitions.size());
        }
      }

      @Override
      protected MajorType getVectorType(GroupScan groupScan, SchemaPath column) {
        return ((ParquetGroupScan)groupScan).getTypeForColumn(column);
      }

      @Override
      protected List<String> getFiles(DrillScanRel scanRel) {
        ParquetGroupScan groupScan = (ParquetGroupScan) scanRel.getGroupScan();
        return new ArrayList(groupScan.getFileSet());
      }
    };
  }

   final QueryContext context;

   private PruneScanRule(RelOptRuleOperand operand, String id, QueryContext context) {
     super(operand, id);
     this.context = context;
   }

   protected abstract PartitionDescriptor getPartitionDescriptor(PlannerSettings settings, DrillScanRel scanRel);

   protected void doOnMatch(RelOptRuleCall call, DrillFilterRel filterRel, DrillProjectRel projectRel, DrillScanRel scanRel) {
     final PlannerSettings settings = PrelUtil.getPlannerSettings(call.getPlanner());
     PartitionDescriptor descriptor = getPartitionDescriptor(settings, scanRel);
     final BufferAllocator allocator = context.getAllocator();


     RexNode condition = null;
     if(projectRel == null){
       condition = filterRel.getCondition();
     }else{
       // get the filter as if it were below the projection.
       condition = RelOptUtil.pushFilterPastProject(filterRel.getCondition(), projectRel);
     }

     RewriteAsBinaryOperators visitor = new RewriteAsBinaryOperators(true, filterRel.getCluster().getRexBuilder());
     condition = condition.accept(visitor);

     Map<Integer, String> fieldNameMap = Maps.newHashMap();
     List<String> fieldNames = scanRel.getRowType().getFieldNames();
     BitSet columnBitset = new BitSet();
     BitSet partitionColumnBitSet = new BitSet();

     {
       int relColIndex = 0;
       for(String field : fieldNames){
         final Integer partitionIndex = descriptor.getIdIfValid(field);
         if(partitionIndex != null){
           fieldNameMap.put(partitionIndex, field);
           partitionColumnBitSet.set(partitionIndex);
           columnBitset.set(relColIndex);
         }
         relColIndex++;
       }
     }

     if(partitionColumnBitSet.isEmpty()){
       return;
     }

     FindPartitionConditions c = new FindPartitionConditions(columnBitset, filterRel.getCluster().getRexBuilder());
     c.analyze(condition);
     RexNode pruneCondition = c.getFinalCondition();

     if(pruneCondition == null){
       return;
     }


     // set up the partitions
     final GroupScan groupScan = scanRel.getGroupScan();
     final FormatSelection origSelection = (FormatSelection)scanRel.getDrillTable().getSelection();
     final List<String> files = getFiles(scanRel);
     final String selectionRoot = origSelection.getSelection().selectionRoot;
     List<PathPartition> partitions = Lists.newLinkedList();

     // let's only deal with one batch of files for now.
     if(files.size() > Character.MAX_VALUE){
       return;
     }

     for(String f : files){
       partitions.add(new PathPartition(descriptor.getMaxHierarchyLevel(), selectionRoot, f));
     }

     final NullableBitVector output = new NullableBitVector(MaterializedField.create("", Types.optional(MinorType.BIT)), allocator);
     final VectorContainer container = new VectorContainer();

     try{
       final ValueVector[] vectors = new ValueVector[descriptor.getMaxHierarchyLevel()];
       for(int partitionColumnIndex : BitSets.toIter(partitionColumnBitSet)){
         SchemaPath column = SchemaPath.getSimplePath(fieldNameMap.get(partitionColumnIndex));
         MajorType type = getVectorType(groupScan, column);
         MaterializedField field = MaterializedField.create(column, type);
         ValueVector v = TypeHelper.getNewVector(field, allocator);
         v.allocateNew();
         vectors[partitionColumnIndex] = v;
         container.add(v);
       }

       // populate partition vectors.

       populatePartitionVectors(vectors, partitions, partitionColumnBitSet, fieldNameMap, groupScan);

       // materialize the expression
       logger.debug("Attempting to prune {}", pruneCondition);
       LogicalExpression expr = DrillOptiq.toDrill(new DrillParseContext(settings), scanRel, pruneCondition);
       ErrorCollectorImpl errors = new ErrorCollectorImpl();
       LogicalExpression materializedExpr = ExpressionTreeMaterializer.materialize(expr, container, errors, context.getFunctionRegistry());
       if (errors.getErrorCount() != 0) {
         logger.warn("Failure while materializing expression [{}].  Errors: {}", expr, errors);
       }

       output.allocateNew(partitions.size());
       InterpreterEvaluator.evaluate(partitions.size(), context, container, output, materializedExpr);
       int record = 0;

       List<String> newFiles = Lists.newArrayList();
       for(Iterator<PathPartition> iter = partitions.iterator(); iter.hasNext(); record++){
         PathPartition part = iter.next();
         if(!output.getAccessor().isNull(record) && output.getAccessor().get(record) == 1){
           newFiles.add(part.file);
         }
       }

       boolean canDropFilter = true;

       if(newFiles.isEmpty()){
         newFiles.add(files.get(0));
         canDropFilter = false;
       }

       if(newFiles.size() == files.size()){
         return;
       }

       logger.debug("Pruned {} => {}", files, newFiles);


       List<RexNode> conjuncts = RelOptUtil.conjunctions(condition);
       List<RexNode> pruneConjuncts = RelOptUtil.conjunctions(pruneCondition);
       conjuncts.removeAll(pruneConjuncts);
       RexNode newCondition = RexUtil.composeConjunction(filterRel.getCluster().getRexBuilder(), conjuncts, false);

       RewriteCombineBinaryOperators reverseVisitor = new RewriteCombineBinaryOperators(true, filterRel.getCluster().getRexBuilder());

       condition = condition.accept(reverseVisitor);
       pruneCondition = pruneCondition.accept(reverseVisitor);

       final FileSelection newFileSelection = new FileSelection(newFiles, selectionRoot, true);
       final FileGroupScan newScan = ((FileGroupScan)scanRel.getGroupScan()).clone(newFileSelection);
       final DrillScanRel newScanRel =
           new DrillScanRel(scanRel.getCluster(),
               scanRel.getTraitSet().plus(DrillRel.DRILL_LOGICAL),
               scanRel.getTable(),
               newScan,
               scanRel.getRowType(),
               scanRel.getColumns());

       RelNode inputRel = newScanRel;

       if(projectRel != null){
         inputRel = projectRel.copy(projectRel.getTraitSet(), Collections.singletonList(inputRel));
       }

       if (newCondition.isAlwaysTrue() && canDropFilter) {
         call.transformTo(inputRel);
       } else {
         final RelNode newFilter = filterRel.copy(filterRel.getTraitSet(), Collections.singletonList(inputRel));
         call.transformTo(newFilter);
       }

     }catch(Exception e){
       logger.warn("Exception while trying to prune partition.", e);
     }finally{
       container.clear();
       if(output !=null){
         output.clear();
       }
     }
   }

   protected abstract void populatePartitionVectors(ValueVector[] vectors, List<PathPartition> partitions, BitSet partitionColumnBitSet, Map<Integer, String> fieldNameMap, GroupScan groupScan);

   protected abstract MajorType getVectorType(GroupScan groupScan, SchemaPath column);

   protected abstract List<String> getFiles(DrillScanRel scanRel);

   private static class PathPartition {
        final String[] dirs;
        final String file;

        public PathPartition(int max, String selectionRoot, String file){
          this.file = file;
          this.dirs = new String[max];
          int start = file.indexOf(selectionRoot) + selectionRoot.length();
          String postPath = file.substring(start);
          if (postPath.length() == 0) {
            return;
          }
          if(postPath.charAt(0) == '/'){
            postPath = postPath.substring(1);
          }
          String[] mostDirs = postPath.split("/");
          int maxLoop = Math.min(max, mostDirs.length - 1);
          for(int i =0; i < maxLoop; i++){
            this.dirs[i] = mostDirs[i];
          }
        }


      }

 }


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/DrillSqlWorker.java
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
package org.apache.drill.exec.planner.sql;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.calcite.config.Lex;
import org.apache.calcite.rel.rules.ProjectToWindowRule;
import org.apache.calcite.tools.FrameworkConfig;
import org.apache.calcite.tools.Frameworks;
import org.apache.calcite.tools.Planner;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.RuleSet;
import org.apache.calcite.tools.ValidationException;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.planner.cost.DrillCostBase;
import org.apache.drill.exec.planner.logical.DrillConstExecutor;
import org.apache.drill.exec.planner.logical.DrillRuleSets;
import org.apache.drill.exec.planner.physical.DrillDistributionTraitDef;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.planner.sql.handlers.AbstractSqlHandler;
import org.apache.drill.exec.planner.sql.handlers.DefaultSqlHandler;
import org.apache.drill.exec.planner.sql.handlers.ExplainHandler;
import org.apache.drill.exec.planner.sql.handlers.SetOptionHandler;
import org.apache.drill.exec.planner.sql.handlers.SqlHandlerConfig;
import org.apache.drill.exec.planner.sql.parser.DrillSqlCall;
import org.apache.drill.exec.planner.sql.parser.SqlCreateTable;
import org.apache.drill.exec.planner.sql.parser.impl.DrillParserWithCompoundIdConverter;
import org.apache.drill.exec.planner.types.DrillRelDataTypeSystem;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.drill.exec.testing.ControlsInjector;
import org.apache.drill.exec.testing.ControlsInjectorFactory;
import org.apache.drill.exec.util.Pointer;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.calcite.rel.RelCollationTraitDef;
import org.apache.calcite.rel.rules.ReduceExpressionsRule;
import org.apache.calcite.plan.ConventionTraitDef;
import org.apache.calcite.plan.RelOptCostFactory;
import org.apache.calcite.plan.RelTraitDef;
import org.apache.calcite.plan.hep.HepPlanner;
import org.apache.calcite.plan.hep.HepProgramBuilder;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.parser.SqlParseException;
import org.apache.calcite.sql.parser.SqlParser;
import org.apache.drill.exec.work.foreman.SqlUnsupportedException;
import org.apache.hadoop.security.AccessControlException;

public class DrillSqlWorker {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(DrillSqlWorker.class);
  private static final ControlsInjector injector = ControlsInjectorFactory.getInjector(DrillSqlWorker.class);

  private final Planner planner;
  private final HepPlanner hepPlanner;
  public final static int LOGICAL_RULES = 0;
  public final static int PHYSICAL_MEM_RULES = 1;
  public final static int LOGICAL_CONVERT_RULES = 2;

  private final QueryContext context;

  public DrillSqlWorker(QueryContext context) {
    final List<RelTraitDef> traitDefs = new ArrayList<RelTraitDef>();

    traitDefs.add(ConventionTraitDef.INSTANCE);
    traitDefs.add(DrillDistributionTraitDef.INSTANCE);
    traitDefs.add(RelCollationTraitDef.INSTANCE);
    this.context = context;
    RelOptCostFactory costFactory = (context.getPlannerSettings().useDefaultCosting()) ?
        null : new DrillCostBase.DrillCostFactory() ;
    int idMaxLength = (int)context.getPlannerSettings().getIdentifierMaxLength();

    FrameworkConfig config = Frameworks.newConfigBuilder() //
        .parserConfig(SqlParser.configBuilder()
            .setLex(Lex.MYSQL)
            .setIdentifierMaxLength(idMaxLength)
            .setParserFactory(DrillParserWithCompoundIdConverter.FACTORY)
            .build()) //
        .defaultSchema(context.getNewDefaultSchema()) //
        .operatorTable(context.getDrillOperatorTable()) //
        .traitDefs(traitDefs) //
        .convertletTable(new DrillConvertletTable()) //
        .context(context.getPlannerSettings()) //
        .ruleSets(getRules(context)) //
        .costFactory(costFactory) //
        .executor(new DrillConstExecutor(context.getFunctionRegistry(), context, context.getPlannerSettings()))
        .typeSystem(DrillRelDataTypeSystem.DRILL_REL_DATATYPE_SYSTEM) //
        .build();
    this.planner = Frameworks.getPlanner(config);
    HepProgramBuilder builder = new HepProgramBuilder();
    builder.addRuleClass(ReduceExpressionsRule.class);
    builder.addRuleClass(ProjectToWindowRule.class);
    this.hepPlanner = new HepPlanner(builder.build());
    hepPlanner.addRule(ReduceExpressionsRule.CALC_INSTANCE);
    hepPlanner.addRule(ProjectToWindowRule.PROJECT);
  }

  private RuleSet[] getRules(QueryContext context) {
    StoragePluginRegistry storagePluginRegistry = context.getStorage();
    RuleSet drillLogicalRules = DrillRuleSets.mergedRuleSets(
        DrillRuleSets.getDrillBasicRules(context),
        DrillRuleSets.getJoinPermRules(context),
        DrillRuleSets.getDrillUserConfigurableLogicalRules(context));
    RuleSet drillPhysicalMem = DrillRuleSets.mergedRuleSets(
        DrillRuleSets.getPhysicalRules(context),
        storagePluginRegistry.getStoragePluginRuleSet());

    // Following is used in LOPT join OPT.
    RuleSet logicalConvertRules = DrillRuleSets.mergedRuleSets(
        DrillRuleSets.getDrillBasicRules(context),
        DrillRuleSets.getDrillUserConfigurableLogicalRules(context));

    RuleSet[] allRules = new RuleSet[] {drillLogicalRules, drillPhysicalMem, logicalConvertRules};

    return allRules;
  }

  public PhysicalPlan getPlan(String sql) throws SqlParseException, ValidationException, ForemanSetupException{
    return getPlan(sql, null);
  }

  public PhysicalPlan getPlan(String sql, Pointer<String> textPlan) throws ForemanSetupException {
    final PlannerSettings ps = this.context.getPlannerSettings();

    SqlNode sqlNode;
    try {
      injector.injectChecked(context.getExecutionControls(), "sql-parsing", ForemanSetupException.class);
      sqlNode = planner.parse(sql);
    } catch (SqlParseException e) {
      throw UserException.parseError(e).build(logger);
    }

    AbstractSqlHandler handler;
    SqlHandlerConfig config = new SqlHandlerConfig(hepPlanner, planner, context);

    // TODO: make this use path scanning or something similar.
    switch(sqlNode.getKind()){
    case EXPLAIN:
      handler = new ExplainHandler(config);
      break;
    case SET_OPTION:
      handler = new SetOptionHandler(context);
      break;
    case OTHER:
      if(sqlNode instanceof SqlCreateTable) {
        handler = ((DrillSqlCall)sqlNode).getSqlHandler(config, textPlan);
        break;
      }

      if (sqlNode instanceof DrillSqlCall) {
        handler = ((DrillSqlCall)sqlNode).getSqlHandler(config);
        break;
      }
      // fallthrough
    default:
      handler = new DefaultSqlHandler(config, textPlan);
    }

    try {
      return handler.getPlan(sqlNode);
    } catch(ValidationException e) {
      String errorMessage = e.getCause() != null ? e.getCause().getMessage() : e.getMessage();
      throw UserException.parseError(e)
        .message(errorMessage)
        .build(logger);
    } catch (AccessControlException e) {
      throw UserException.permissionError(e)
        .build(logger);
    } catch(SqlUnsupportedException e) {
      throw UserException.unsupportedError(e)
        .build(logger);
    } catch (IOException | RelConversionException e) {
      throw new QueryInputException("Failure handling SQL.", e);
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/AbstractStoragePlugin.java
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
package org.apache.drill.exec.store;

import java.io.IOException;
import java.util.List;
import java.util.Set;

import org.apache.drill.common.JSONOptions;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.physical.base.AbstractGroupScan;

import com.google.common.collect.ImmutableSet;

public abstract class AbstractStoragePlugin implements StoragePlugin{
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(AbstractStoragePlugin.class);

  protected AbstractStoragePlugin(){
  }

  @Override
  public boolean supportsRead() {
    return false;
  }

  @Override
  public boolean supportsWrite() {
    return false;
  }

  @Override
  public Set<StoragePluginOptimizerRule> getOptimizerRules() {
    return ImmutableSet.of();
  }

  @Override
  public AbstractGroupScan getPhysicalScan(String userName, JSONOptions selection) throws IOException {
    return getPhysicalScan(userName, selection, AbstractGroupScan.ALL_COLUMNS);
  }

  @Override
  public AbstractGroupScan getPhysicalScan(String userName, JSONOptions selection, List<SchemaPath> columns) throws IOException {
    throw new UnsupportedOperationException();
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/StoragePlugin.java
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
package org.apache.drill.exec.store;

import java.io.IOException;
import java.util.List;
import java.util.Set;

import org.apache.drill.common.JSONOptions;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.common.logical.StoragePluginConfig;
import org.apache.drill.exec.physical.base.AbstractGroupScan;

public interface StoragePlugin extends SchemaFactory {
  public boolean supportsRead();

  public boolean supportsWrite();

  public Set<StoragePluginOptimizerRule> getOptimizerRules();

  /**
   * Get the physical scan operator for the particular GroupScan (read) node.
   *
   * @param userName User whom to impersonate when when reading the contents as part of Scan.
   * @param selection The configured storage engine specific selection.
   * @return
   * @throws IOException
   */
  public AbstractGroupScan getPhysicalScan(String userName, JSONOptions selection) throws IOException;

  /**
   * Get the physical scan operator for the particular GroupScan (read) node.
   *
   * @param userName User whom to impersonate when when reading the contents as part of Scan.
   * @param selection The configured storage engine specific selection.
   * @param columns (optional) The list of column names to scan from the data source.
   * @return
   * @throws IOException
   */
  public AbstractGroupScan getPhysicalScan(String userName, JSONOptions selection, List<SchemaPath> columns)
      throws IOException;

  public StoragePluginConfig getConfig();

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/StoragePluginRegistry.java
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
package org.apache.drill.exec.store;

import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.net.URL;
import java.util.Collection;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.TimeUnit;

import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.tools.RuleSet;

import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.logical.FormatPluginConfig;
import org.apache.drill.common.logical.StoragePluginConfig;
import org.apache.drill.common.util.PathScanner;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.exception.DrillbitStartupException;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.ops.ViewExpansionContext;
import org.apache.drill.exec.planner.logical.DrillRuleSets;
import org.apache.drill.exec.planner.logical.StoragePlugins;
import org.apache.drill.exec.rpc.user.UserSession;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.store.dfs.FileSystemPlugin;
import org.apache.drill.exec.store.dfs.FormatPlugin;
import org.apache.drill.exec.store.ischema.InfoSchemaConfig;
import org.apache.drill.exec.store.ischema.InfoSchemaStoragePlugin;
import org.apache.drill.exec.store.sys.PStore;
import org.apache.drill.exec.store.sys.PStoreConfig;
import org.apache.drill.exec.store.sys.SystemTablePlugin;
import org.apache.drill.exec.store.sys.SystemTablePluginConfig;
import org.apache.calcite.plan.RelOptRule;

import com.google.common.base.Charsets;
import com.google.common.base.Stopwatch;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSet.Builder;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;
import com.google.common.io.Resources;

public class StoragePluginRegistry implements Iterable<Map.Entry<String, StoragePlugin>> {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(StoragePluginRegistry.class);

  public static final String SYS_PLUGIN = "sys";

  public static final String INFORMATION_SCHEMA_PLUGIN = "INFORMATION_SCHEMA";

  private Map<Object, Constructor<? extends StoragePlugin>> availablePlugins = new HashMap<Object, Constructor<? extends StoragePlugin>>();
  private ConcurrentMap<String, StoragePlugin> plugins;

  private DrillbitContext context;
  private final DrillSchemaFactory schemaFactory = new DrillSchemaFactory();
  private final PStore<StoragePluginConfig> pluginSystemTable;
  private final Object updateLock = new Object();
  private volatile long lastUpdate = 0;
  private static final long UPDATE_FREQUENCY = 2 * 60 * 1000;

  public StoragePluginRegistry(DrillbitContext context) {
    try {
      this.context = context;
      this.pluginSystemTable = context //
          .getPersistentStoreProvider() //
          .getStore(PStoreConfig //
              .newJacksonBuilder(context.getConfig().getMapper(), StoragePluginConfig.class) //
              .name("sys.storage_plugins") //
              .build());
    } catch (IOException | RuntimeException e) {
      logger.error("Failure while loading storage plugin registry.", e);
      throw new RuntimeException("Faiure while reading and loading storage plugin configuration.", e);
    }
  }

  public PStore<StoragePluginConfig> getStore() {
    return pluginSystemTable;
  }

  @SuppressWarnings("unchecked")
  public void init() throws DrillbitStartupException {
    DrillConfig config = context.getConfig();
    Collection<Class<? extends StoragePlugin>> plugins = PathScanner.scanForImplementations(StoragePlugin.class, config.getStringList(ExecConstants.STORAGE_ENGINE_SCAN_PACKAGES));
    logger.debug("Loading storage plugins {}", plugins);
    for (Class<? extends StoragePlugin> plugin : plugins) {
      int i = 0;
      for (Constructor<?> c : plugin.getConstructors()) {
        Class<?>[] params = c.getParameterTypes();
        if(params.length != 3
            || params[1] != DrillbitContext.class
            || !StoragePluginConfig.class.isAssignableFrom(params[0])
            || params[2] != String.class) {
          logger.info("Skipping StoragePlugin constructor {} for plugin class {} since it doesn't implement a [constructor(StoragePluginConfig, DrillbitContext, String)]", c, plugin);
          continue;
        }
        availablePlugins.put(params[0], (Constructor<? extends StoragePlugin>) c);
        i++;
      }
      if (i == 0) {
        logger.debug("Skipping registration of StoragePlugin {} as it doesn't have a constructor with the parameters of (StorangePluginConfig, Config)", plugin.getCanonicalName());
      }
    }

    // create registered plugins defined in "storage-plugins.json"
    this.plugins = Maps.newConcurrentMap();
    this.plugins.putAll(createPlugins());

  }

  private Map<String, StoragePlugin> createPlugins() throws DrillbitStartupException {
    try {
      /*
       * Check if the storage plugins system table has any entries.  If not, load the boostrap-storage-plugin file into the system table.
       */
      if (!pluginSystemTable.iterator().hasNext()) {
        // bootstrap load the config since no plugins are stored.
        logger.info("No storage plugin instances configured in persistent store, loading bootstrap configuration.");
        Collection<URL> urls = PathScanner.forResource(ExecConstants.BOOTSTRAP_STORAGE_PLUGINS_FILE, false, Resources.class.getClassLoader());
        if (urls != null && ! urls.isEmpty()) {
          logger.info("Loading the storage plugin configs from URLs {}.", urls);
          Map<String, URL> pluginURLMap = Maps.newHashMap();
          for (URL url :urls) {
            String pluginsData = Resources.toString(url, Charsets.UTF_8);
            StoragePlugins plugins = context.getConfig().getMapper().readValue(pluginsData, StoragePlugins.class);
            for (Map.Entry<String, StoragePluginConfig> config : plugins) {
              if (!pluginSystemTable.putIfAbsent(config.getKey(), config.getValue())) {
                logger.warn("Duplicate plugin instance '{}' defined in [{}, {}], ignoring the later one.",
                            config.getKey(), pluginURLMap.get(config.getKey()), url);
                continue;
              }
              pluginURLMap.put(config.getKey(), url);
            }
          }
        } else {
          throw new IOException("Failure finding " + ExecConstants.BOOTSTRAP_STORAGE_PLUGINS_FILE);
        }
      }

      Map<String, StoragePlugin> activePlugins = new HashMap<String, StoragePlugin>();
      for (Map.Entry<String, StoragePluginConfig> entry : pluginSystemTable) {
        String name = entry.getKey();
        StoragePluginConfig config = entry.getValue();
        if (config.isEnabled()) {
          try {
            StoragePlugin plugin = create(name, config);
            activePlugins.put(name, plugin);
          } catch (ExecutionSetupException e) {
            logger.error("Failure while setting up StoragePlugin with name: '{}', disabling.", name, e);
            config.setEnabled(false);
            pluginSystemTable.put(name, config);
          }
        }
      }

      activePlugins.put(INFORMATION_SCHEMA_PLUGIN, new InfoSchemaStoragePlugin(new InfoSchemaConfig(), context, INFORMATION_SCHEMA_PLUGIN));
      activePlugins.put(SYS_PLUGIN, new SystemTablePlugin(SystemTablePluginConfig.INSTANCE, context, SYS_PLUGIN));

      return activePlugins;
    } catch (IOException e) {
      logger.error("Failure setting up storage plugins.  Drillbit exiting.", e);
      throw new IllegalStateException(e);
    }
  }

  public void deletePlugin(String name) {
    plugins.remove(name);
    pluginSystemTable.delete(name);
  }

  public StoragePlugin createOrUpdate(String name, StoragePluginConfig config, boolean persist) throws ExecutionSetupException {
    StoragePlugin oldPlugin = plugins.get(name);

    StoragePlugin newPlugin = create(name, config);
    boolean ok = true;
    if (oldPlugin != null) {
      if (config.isEnabled()) {
        ok = plugins.replace(name, oldPlugin, newPlugin);
      } else {
        ok = plugins.remove(name, oldPlugin);
      }
    } else if (config.isEnabled()) {
      ok = (null == plugins.putIfAbsent(name, newPlugin));
    }

    if(!ok) {
      throw new ExecutionSetupException("Two processes tried to change a plugin at the same time.");
    }

    if (persist) {
      pluginSystemTable.put(name, config);
    }

    return newPlugin;
  }

  public StoragePlugin getPlugin(String name) throws ExecutionSetupException {
    StoragePlugin plugin = plugins.get(name);
    if (name.equals(SYS_PLUGIN) || name.equals(INFORMATION_SCHEMA_PLUGIN)) {
      return plugin;
    }

    // since we lazily manage the list of plugins per server, we need to update this once we know that it is time.
    StoragePluginConfig config = this.pluginSystemTable.get(name);
    if (config == null) {
      if (plugin != null) {
        plugins.remove(name);
      }
      return null;
    } else {
      if (plugin == null || !plugin.getConfig().equals(config)) {
        plugin = createOrUpdate(name, config, false);
      }
      return plugin;
    }
  }

  public StoragePlugin getPlugin(StoragePluginConfig config) throws ExecutionSetupException {
    if (config instanceof NamedStoragePluginConfig) {
      return getPlugin(((NamedStoragePluginConfig) config).name);
    } else {
      // TODO: for now, we'll throw away transient configs. we really ought to clean these up.
      return create(null, config);
    }
  }

  public FormatPlugin getFormatPlugin(StoragePluginConfig storageConfig, FormatPluginConfig formatConfig) throws ExecutionSetupException {
    StoragePlugin p = getPlugin(storageConfig);
    if (!(p instanceof FileSystemPlugin)) {
      throw new ExecutionSetupException(String.format("You tried to request a format plugin for a storage plugin that wasn't of type FileSystemPlugin.  The actual type of plugin was %s.", p.getClass().getName()));
    }
    FileSystemPlugin storage = (FileSystemPlugin) p;
    return storage.getFormatPlugin(formatConfig);
  }

  private StoragePlugin create(String name, StoragePluginConfig pluginConfig) throws ExecutionSetupException {
    StoragePlugin plugin = null;
    Constructor<? extends StoragePlugin> c = availablePlugins.get(pluginConfig.getClass());
    if (c == null) {
      throw new ExecutionSetupException(String.format("Failure finding StoragePlugin constructor for config %s",
          pluginConfig));
    }
    try {
      plugin = c.newInstance(pluginConfig, context, name);
      return plugin;
    } catch (InstantiationException | IllegalAccessException | IllegalArgumentException | InvocationTargetException e) {
      Throwable t = e instanceof InvocationTargetException ? ((InvocationTargetException) e).getTargetException() : e;
      if (t instanceof ExecutionSetupException) {
        throw ((ExecutionSetupException) t);
      }
      throw new ExecutionSetupException(String.format(
          "Failure setting up new storage plugin configuration for config %s", pluginConfig), t);
    }
  }

  @Override
  public Iterator<Entry<String, StoragePlugin>> iterator() {
    return plugins.entrySet().iterator();
  }

  public RuleSet getStoragePluginRuleSet() {
    // query registered engines for optimizer rules and build the storage plugin RuleSet
    Builder<RelOptRule> setBuilder = ImmutableSet.builder();
    for (StoragePlugin plugin : this.plugins.values()) {
      Set<StoragePluginOptimizerRule> rules = plugin.getOptimizerRules();
      if (rules != null && rules.size() > 0) {
        setBuilder.addAll(rules);
      }
    }

    return DrillRuleSets.create(setBuilder.build());
  }

  public DrillSchemaFactory getSchemaFactory() {
    return schemaFactory;
  }

  public class DrillSchemaFactory implements SchemaFactory {

    @Override
    public void registerSchemas(SchemaConfig schemaConfig, SchemaPlus parent) throws IOException {
      Stopwatch watch = new Stopwatch();
      watch.start();

      try {
        Set<String> currentPluginNames = Sets.newHashSet(plugins.keySet());
        // iterate through the plugin instances in the persistence store adding
        // any new ones and refreshing those whose configuration has changed
        for (Map.Entry<String, StoragePluginConfig> config : pluginSystemTable) {
          if (config.getValue().isEnabled()) {
            getPlugin(config.getKey());
            currentPluginNames.remove(config.getKey());
          }
        }
        // remove those which are no longer in the registry
        for (String pluginName : currentPluginNames) {
          if (pluginName.equals(SYS_PLUGIN) || pluginName.equals(INFORMATION_SCHEMA_PLUGIN)) {
            continue;
          }
          plugins.remove(pluginName);
        }

        // finally register schemas with the refreshed plugins
        for (StoragePlugin plugin : plugins.values()) {
          plugin.registerSchemas(schemaConfig, parent);
        }
      } catch (ExecutionSetupException e) {
        throw new DrillRuntimeException("Failure while updating storage plugins", e);
      }

      // Add second level schema as top level schema with name qualified with parent schema name
      // Ex: "dfs" schema has "default" and "tmp" as sub schemas. Add following extra schemas "dfs.default" and
      // "dfs.tmp" under root schema.
      //
      // Before change, schema tree looks like below:
      // "root"
      //    -- "dfs"
      //          -- "default"
      //          -- "tmp"
      //    -- "hive"
      //          -- "default"
      //          -- "hivedb1"
      //
      // After the change, the schema tree looks like below:
      // "root"
      //    -- "dfs"
      //          -- "default"
      //          -- "tmp"
      //    -- "dfs.default"
      //    -- "dfs.tmp"
      //    -- "hive"
      //          -- "default"
      //          -- "hivedb1"
      //    -- "hive.default"
      //    -- "hive.hivedb1"
      List<SchemaPlus> secondLevelSchemas = Lists.newArrayList();
      for (String firstLevelSchemaName : parent.getSubSchemaNames()) {
        SchemaPlus firstLevelSchema = parent.getSubSchema(firstLevelSchemaName);
        for (String secondLevelSchemaName : firstLevelSchema.getSubSchemaNames()) {
          secondLevelSchemas.add(firstLevelSchema.getSubSchema(secondLevelSchemaName));
        }
      }

      for (SchemaPlus schema : secondLevelSchemas) {
        AbstractSchema drillSchema;
        try {
          drillSchema = schema.unwrap(AbstractSchema.class);
        } catch (ClassCastException e) {
          throw new RuntimeException(String.format("Schema '%s' is not expected under root schema", schema.getName()));
        }
        SubSchemaWrapper wrapper = new SubSchemaWrapper(drillSchema);
        parent.add(wrapper.getName(), wrapper);
      }

      logger.debug("Took {} ms to register schemas.", watch.elapsed(TimeUnit.MILLISECONDS));
    }

  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/dfs/FileSystemPlugin.java
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
package org.apache.drill.exec.store.dfs;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.calcite.schema.SchemaPlus;

import org.apache.drill.common.JSONOptions;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.common.logical.FormatPluginConfig;
import org.apache.drill.common.logical.StoragePluginConfig;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.base.AbstractGroupScan;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.store.AbstractStoragePlugin;
import org.apache.drill.exec.store.ClassPathFileSystem;
import org.apache.drill.exec.store.LocalSyncableFileSystem;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.store.StoragePluginOptimizerRule;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileSystem;

import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSet.Builder;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;

import static org.apache.drill.exec.store.dfs.FileSystemSchemaFactory.DEFAULT_WS_NAME;

/**
 * A Storage engine associated with a Hadoop FileSystem Implementation. Examples include HDFS, MapRFS, QuantacastFileSystem,
 * LocalFileSystem, as well Apache Drill specific CachedFileSystem, ClassPathFileSystem and LocalSyncableFileSystem.
 * Tables are file names, directories and path patterns. This storage engine delegates to FSFormatEngines but shares
 * references to the FileSystem configuration and path management.
 */
public class FileSystemPlugin extends AbstractStoragePlugin{
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(FileSystemPlugin.class);

  private final FileSystemSchemaFactory schemaFactory;
  private final Map<String, FormatPlugin> formatPluginsByName;
  private final Map<FormatPluginConfig, FormatPlugin> formatPluginsByConfig;
  private final FileSystemConfig config;
  private final DrillbitContext context;
  private final Configuration fsConf;

  public FileSystemPlugin(FileSystemConfig config, DrillbitContext context, String name) throws ExecutionSetupException{
    try {
      this.config = config;
      this.context = context;

      fsConf = new Configuration();
      fsConf.set(FileSystem.FS_DEFAULT_NAME_KEY, config.connection);
      fsConf.set("fs.classpath.impl", ClassPathFileSystem.class.getName());
      fsConf.set("fs.drill-local.impl", LocalSyncableFileSystem.class.getName());

      formatPluginsByName = FormatCreator.getFormatPlugins(context, fsConf, config);
      List<FormatMatcher> matchers = Lists.newArrayList();
      formatPluginsByConfig = Maps.newHashMap();
      for (FormatPlugin p : formatPluginsByName.values()) {
        matchers.add(p.getMatcher());
        formatPluginsByConfig.put(p.getConfig(), p);
      }

      final boolean noWorkspace = config.workspaces == null || config.workspaces.isEmpty();
      List<WorkspaceSchemaFactory> factories = Lists.newArrayList();
      if (!noWorkspace) {
        for (Map.Entry<String, WorkspaceConfig> space : config.workspaces.entrySet()) {
          factories.add(new WorkspaceSchemaFactory(context.getConfig(), this, space.getKey(), name, space.getValue(), matchers));
        }
      }

      // if the "default" workspace is not given add one.
      if (noWorkspace || !config.workspaces.containsKey(DEFAULT_WS_NAME)) {
        factories.add(new WorkspaceSchemaFactory(context.getConfig(), this, DEFAULT_WS_NAME, name, WorkspaceConfig.DEFAULT, matchers));
      }

      this.schemaFactory = new FileSystemSchemaFactory(name, factories);
    } catch (IOException e) {
      throw new ExecutionSetupException("Failure setting up file system plugin.", e);
    }
  }

  @Override
  public boolean supportsRead() {
    return true;
  }

  @Override
  public StoragePluginConfig getConfig() {
    return config;
  }

  @Override
  public AbstractGroupScan getPhysicalScan(String userName, JSONOptions selection, List<SchemaPath> columns)
      throws IOException {
    FormatSelection formatSelection = selection.getWith(context.getConfig(), FormatSelection.class);
    FormatPlugin plugin;
    if (formatSelection.getFormat() instanceof NamedFormatPluginConfig) {
      plugin = formatPluginsByName.get( ((NamedFormatPluginConfig) formatSelection.getFormat()).name);
    } else {
      plugin = formatPluginsByConfig.get(formatSelection.getFormat());
    }
    if (plugin == null) {
      throw new IOException(String.format("Failure getting requested format plugin named '%s'.  It was not one of the format plugins registered.", formatSelection.getFormat()));
    }
    return plugin.getGroupScan(userName, formatSelection.getSelection(), columns);
  }

  @Override
  public void registerSchemas(SchemaConfig schemaConfig, SchemaPlus parent) throws IOException {
    schemaFactory.registerSchemas(schemaConfig, parent);
  }

  public FormatPlugin getFormatPlugin(String name) {
    return formatPluginsByName.get(name);
  }

  public FormatPlugin getFormatPlugin(FormatPluginConfig config) {
    if (config instanceof NamedFormatPluginConfig) {
      return formatPluginsByName.get(((NamedFormatPluginConfig) config).name);
    } else {
      return formatPluginsByConfig.get(config);
    }
  }

  @Override
  public Set<StoragePluginOptimizerRule> getOptimizerRules() {
    Builder<StoragePluginOptimizerRule> setBuilder = ImmutableSet.builder();
    for(FormatPlugin plugin : this.formatPluginsByName.values()){
      Set<StoragePluginOptimizerRule> rules = plugin.getOptimizerRules();
      if(rules != null && rules.size() > 0){
        setBuilder.addAll(rules);
      }
    }
    return setBuilder.build();
  }

  public Configuration getFsConf() {
    return fsConf;
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/ischema/InfoSchemaStoragePlugin.java
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
package org.apache.drill.exec.store.ischema;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.google.common.collect.ImmutableSet;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.schema.Table;

import static org.apache.drill.exec.store.ischema.InfoSchemaConstants.*;
import org.apache.drill.common.JSONOptions;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.common.logical.StoragePluginConfig;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.store.AbstractStoragePlugin;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.store.StoragePluginOptimizerRule;

public class InfoSchemaStoragePlugin extends AbstractStoragePlugin {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(InfoSchemaStoragePlugin.class);

  private final InfoSchemaConfig config;
  private final DrillbitContext context;
  private final String name;

  public InfoSchemaStoragePlugin(InfoSchemaConfig config, DrillbitContext context, String name){
    this.config = config;
    this.context = context;
    this.name = name;
  }

  @Override
  public boolean supportsRead() {
    return true;
  }

  @Override
  public InfoSchemaGroupScan getPhysicalScan(String userName, JSONOptions selection, List<SchemaPath> columns)
      throws IOException {
    SelectedTable table = selection.getWith(context.getConfig(),  SelectedTable.class);
    return new InfoSchemaGroupScan(table);
  }

  @Override
  public StoragePluginConfig getConfig() {
    return this.config;
  }

  @Override
  public void registerSchemas(SchemaConfig schemaConfig, SchemaPlus parent) throws IOException {
    ISchema s = new ISchema(parent, this);
    parent.add(s.getName(), s);
  }

  /**
   * Representation of the INFORMATION_SCHEMA schema.
   */
  private class ISchema extends AbstractSchema{
    private Map<String, InfoSchemaDrillTable> tables;
    public ISchema(SchemaPlus parent, InfoSchemaStoragePlugin plugin){
      super(ImmutableList.<String>of(), IS_SCHEMA_NAME);
      Map<String, InfoSchemaDrillTable> tbls = Maps.newHashMap();
      for(SelectedTable tbl : SelectedTable.values()){
        tbls.put(tbl.name(), new InfoSchemaDrillTable(plugin, IS_SCHEMA_NAME, tbl, config));
      }
      this.tables = ImmutableMap.copyOf(tbls);
    }

    @Override
    public Table getTable(String name) {
      return tables.get(name);
    }

    @Override
    public Set<String> getTableNames() {
      return tables.keySet();
    }

    @Override
    public String getTypeName() {
      return InfoSchemaConfig.NAME;
    }
  }

  @Override
  public Set<StoragePluginOptimizerRule> getOptimizerRules() {
    return ImmutableSet.of(
        InfoSchemaPushFilterIntoRecordGenerator.IS_FILTER_ON_PROJECT,
        InfoSchemaPushFilterIntoRecordGenerator.IS_FILTER_ON_SCAN);
  }
}
