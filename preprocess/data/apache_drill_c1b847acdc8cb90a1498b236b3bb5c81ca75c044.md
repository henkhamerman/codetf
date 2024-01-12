Refactoring Types: ['Extract Method', 'Pull Up Attribute', 'Move Class']
re/hive/HiveScan.java
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
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

import org.apache.commons.codec.binary.Base64;
import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.physical.EndpointAffinity;
import org.apache.drill.exec.physical.base.AbstractGroupScan;
import org.apache.drill.exec.physical.base.GroupScan;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.physical.base.ScanStats;
import org.apache.drill.exec.physical.base.ScanStats.GroupScanProperty;
import org.apache.drill.exec.physical.base.SubScan;
import org.apache.drill.exec.proto.CoordinationProtos;
import org.apache.drill.exec.proto.CoordinationProtos.DrillbitEndpoint;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.drill.exec.store.hive.HiveTable.HivePartition;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hive.metastore.MetaStoreUtils;
import org.apache.hadoop.hive.metastore.api.FieldSchema;
import org.apache.hadoop.hive.metastore.api.Partition;
import org.apache.hadoop.hive.metastore.api.StorageDescriptor;
import org.apache.hadoop.hive.metastore.api.Table;
import org.apache.hadoop.mapred.FileInputFormat;
import org.apache.hadoop.mapred.InputFormat;
import org.apache.hadoop.mapred.InputSplit;
import org.apache.hadoop.mapred.JobConf;

import com.fasterxml.jackson.annotation.JacksonInject;
import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonTypeName;
import com.google.common.base.Preconditions;
import com.google.common.collect.Lists;
import com.google.common.io.ByteArrayDataOutput;
import com.google.common.io.ByteStreams;

@JsonTypeName("hive-scan")
public class HiveScan extends AbstractGroupScan {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(HiveScan.class);

  @JsonProperty("hive-table")
  public HiveReadEntry hiveReadEntry;
  @JsonIgnore
  private List<InputSplit> inputSplits = Lists.newArrayList();
  @JsonIgnore
  public HiveStoragePlugin storagePlugin;
  @JsonProperty("storage-plugin")
  public String storagePluginName;

  @JsonIgnore
  private final Collection<DrillbitEndpoint> endpoints;

  @JsonProperty("columns")
  public List<SchemaPath> columns;

  @JsonIgnore
  List<List<InputSplit>> mappings;

  @JsonIgnore
  Map<InputSplit, Partition> partitionMap = new HashMap();

  /*
   * total number of rows (obtained from metadata store)
   */
  @JsonIgnore
  private long rowCount = 0;

  @JsonCreator
  public HiveScan(@JsonProperty("userName") final String userName,
                  @JsonProperty("hive-table") final HiveReadEntry hiveReadEntry,
                  @JsonProperty("storage-plugin") final String storagePluginName,
                  @JsonProperty("columns") final List<SchemaPath> columns,
                  @JacksonInject final StoragePluginRegistry pluginRegistry) throws ExecutionSetupException {
    super(userName);
    this.hiveReadEntry = hiveReadEntry;
    this.storagePluginName = storagePluginName;
    this.storagePlugin = (HiveStoragePlugin) pluginRegistry.getPlugin(storagePluginName);
    this.columns = columns;
    getSplits();
    endpoints = storagePlugin.getContext().getBits();
  }

  public HiveScan(final String userName, final HiveReadEntry hiveReadEntry, final HiveStoragePlugin storagePlugin, final List<SchemaPath> columns) throws ExecutionSetupException {
    super(userName);
    this.hiveReadEntry = hiveReadEntry;
    this.columns = columns;
    this.storagePlugin = storagePlugin;
    getSplits();
    endpoints = storagePlugin.getContext().getBits();
    this.storagePluginName = storagePlugin.getName();
  }

  private HiveScan(final HiveScan that) {
    super(that);
    this.columns = that.columns;
    this.endpoints = that.endpoints;
    this.hiveReadEntry = that.hiveReadEntry;
    this.inputSplits = that.inputSplits;
    this.mappings = that.mappings;
    this.partitionMap = that.partitionMap;
    this.storagePlugin = that.storagePlugin;
    this.storagePluginName = that.storagePluginName;
    this.rowCount = that.rowCount;
  }

  public List<SchemaPath> getColumns() {
    return columns;
  }

  private void getSplits() throws ExecutionSetupException {
    try {
      final List<Partition> partitions = hiveReadEntry.getPartitions();
      final Table table = hiveReadEntry.getTable();
      if (partitions == null || partitions.size() == 0) {
        final Properties properties = MetaStoreUtils.getTableMetadata(table);
        splitInput(properties, table.getSd(), null);
      } else {
        for (final Partition partition : partitions) {
          final Properties properties = MetaStoreUtils.getPartitionMetadata(partition, table);
          splitInput(properties, partition.getSd(), partition);
        }
      }
    } catch (ReflectiveOperationException | IOException e) {
      throw new ExecutionSetupException(e);
    }
  }

  /* Split the input given in StorageDescriptor */
  private void splitInput(final Properties properties, final StorageDescriptor sd, final Partition partition)
      throws ReflectiveOperationException, IOException {
    final JobConf job = new JobConf();
    for (final Object obj : properties.keySet()) {
      job.set((String) obj, (String) properties.get(obj));
    }
    for (final Map.Entry<String, String> entry : hiveReadEntry.hiveConfigOverride.entrySet()) {
      job.set(entry.getKey(), entry.getValue());
    }
    InputFormat<?, ?> format = (InputFormat<?, ?>)
        Class.forName(sd.getInputFormat()).getConstructor().newInstance();
    job.setInputFormat(format.getClass());
    final Path path = new Path(sd.getLocation());
    final FileSystem fs = path.getFileSystem(job);

    // Use new JobConf that has FS configuration
    final JobConf jobWithFsConf = new JobConf(fs.getConf());
    if (fs.exists(path)) {
      FileInputFormat.addInputPath(jobWithFsConf, path);
      format = jobWithFsConf.getInputFormat();
      for (final InputSplit split : format.getSplits(jobWithFsConf, 1)) {
        inputSplits.add(split);
        partitionMap.put(split, partition);
      }
    }
    final String numRowsProp = properties.getProperty("numRows");
    logger.trace("HiveScan num rows property = {}", numRowsProp);
    if (numRowsProp != null) {
      final long numRows = Long.valueOf(numRowsProp);
      // starting from hive-0.13, when no statistics are available, this property is set to -1
      // it's important to note that the value returned by hive may not be up to date
      if (numRows > 0) {
        rowCount += numRows;
      }
    }
  }

  @Override
  public void applyAssignments(final List<CoordinationProtos.DrillbitEndpoint> endpoints) {
    mappings = Lists.newArrayList();
    for (int i = 0; i < endpoints.size(); i++) {
      mappings.add(new ArrayList<InputSplit>());
    }
    final int count = endpoints.size();
    for (int i = 0; i < inputSplits.size(); i++) {
      mappings.get(i % count).add(inputSplits.get(i));
    }
  }

  public static String serializeInputSplit(final InputSplit split) throws IOException {
    final ByteArrayDataOutput byteArrayOutputStream =  ByteStreams.newDataOutput();
    split.write(byteArrayOutputStream);
    final String encoded = Base64.encodeBase64String(byteArrayOutputStream.toByteArray());
    logger.debug("Encoded split string for split {} : {}", split, encoded);
    return encoded;
  }

  @Override
  public SubScan getSpecificScan(final int minorFragmentId) throws ExecutionSetupException {
    try {
      final List<InputSplit> splits = mappings.get(minorFragmentId);
      List<HivePartition> parts = Lists.newArrayList();
      final List<String> encodedInputSplits = Lists.newArrayList();
      final List<String> splitTypes = Lists.newArrayList();
      for (final InputSplit split : splits) {
        HivePartition partition = null;
        if (partitionMap.get(split) != null) {
          partition = new HivePartition(partitionMap.get(split));
        }
        parts.add(partition);
        encodedInputSplits.add(serializeInputSplit(split));
        splitTypes.add(split.getClass().getName());
      }
      if (parts.contains(null)) {
        parts = null;
      }

      final HiveReadEntry subEntry = new HiveReadEntry(hiveReadEntry.table, parts, hiveReadEntry.hiveConfigOverride);
      return new HiveSubScan(getUserName(), encodedInputSplits, subEntry, splitTypes, columns);
    } catch (IOException | ReflectiveOperationException e) {
      throw new ExecutionSetupException(e);
    }
  }

  @Override
  public int getMaxParallelizationWidth() {
    return inputSplits.size();
  }

  @Override
  public List<EndpointAffinity> getOperatorAffinity() {
    final Map<String, DrillbitEndpoint> endpointMap = new HashMap<>();
    for (final DrillbitEndpoint endpoint : endpoints) {
      endpointMap.put(endpoint.getAddress(), endpoint);
      logger.debug("endpoing address: {}", endpoint.getAddress());
    }
    final Map<DrillbitEndpoint, EndpointAffinity> affinityMap = new HashMap<>();
    try {
      long totalSize = 0;
      for (final InputSplit split : inputSplits) {
        totalSize += Math.max(1, split.getLength());
      }
      for (final InputSplit split : inputSplits) {
        final float affinity = ((float) Math.max(1, split.getLength())) / totalSize;
        for (final String loc : split.getLocations()) {
          logger.debug("split location: {}", loc);
          final DrillbitEndpoint endpoint = endpointMap.get(loc);
          if (endpoint != null) {
            if (affinityMap.containsKey(endpoint)) {
              affinityMap.get(endpoint).addAffinity(affinity);
            } else {
              affinityMap.put(endpoint, new EndpointAffinity(endpoint, affinity));
            }
          }
        }
      }
    } catch (final IOException e) {
      throw new DrillRuntimeException(e);
    }
    for (final DrillbitEndpoint ep : affinityMap.keySet()) {
      Preconditions.checkNotNull(ep);
    }
    for (final EndpointAffinity a : affinityMap.values()) {
      Preconditions.checkNotNull(a.getEndpoint());
    }
    return Lists.newArrayList(affinityMap.values());
  }

  @Override
  public ScanStats getScanStats() {
    try {
      long data =0;
      for (final InputSplit split : inputSplits) {
          data += split.getLength();
      }

      long estRowCount = rowCount;
      if (estRowCount == 0) {
        // having a rowCount of 0 can mean the statistics were never computed
        estRowCount = data/1024;
      }
      logger.debug("estimated row count = {}, stats row count = {}", estRowCount, rowCount);
      return new ScanStats(GroupScanProperty.NO_EXACT_ROW_COUNT, estRowCount, 1, data);
    } catch (final IOException e) {
      throw new DrillRuntimeException(e);
    }
  }

  @Override
  public PhysicalOperator getNewWithChildren(final List<PhysicalOperator> children) throws ExecutionSetupException {
    return new HiveScan(this);
  }

  @Override
  public String getDigest() {
    return toString();
  }

  @Override
  public String toString() {
    return "HiveScan [table=" + hiveReadEntry.getHiveTableWrapper()
        + ", inputSplits=" + inputSplits
        + ", columns=" + columns
        + ", partitions= " + hiveReadEntry.getHivePartitionWrappers() +"]";
  }

  @Override
  public GroupScan clone(final List<SchemaPath> columns) {
    final HiveScan newScan = new HiveScan(this);
    newScan.columns = columns;
    return newScan;
  }

  @Override
  public boolean canPushdownProjects(final List<SchemaPath> columns) {
    return true;
  }

  // Return true if the current table is partitioned false otherwise
  public boolean supportsPartitionFilterPushdown() {
    final List<FieldSchema> partitionKeys = hiveReadEntry.getTable().getPartitionKeys();
    if (partitionKeys == null || partitionKeys.size() == 0) {
      return false;
    }
    return true;
  }
}


File: contrib/storage-hive/core/src/main/java/org/apache/drill/exec/store/hive/schema/DrillHiveTable.java
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
package org.apache.drill.exec.store.hive.schema;

import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.List;

import org.apache.drill.exec.planner.logical.DrillTable;
import org.apache.drill.exec.store.hive.HiveReadEntry;
import org.apache.drill.exec.store.hive.HiveStoragePlugin;
import org.apache.hadoop.hive.metastore.api.FieldSchema;
import org.apache.hadoop.hive.ql.metadata.Table;
import org.apache.hadoop.hive.serde2.typeinfo.DecimalTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.ListTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.MapTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.PrimitiveTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.StructTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfoUtils;
import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.rel.type.RelDataTypeFactory;
import org.apache.calcite.sql.SqlCollation;
import org.apache.calcite.sql.type.SqlTypeName;

import com.google.common.collect.Lists;

public class DrillHiveTable extends DrillTable{
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(DrillHiveTable.class);

  protected final Table hiveTable;

  public DrillHiveTable(String storageEngineName, HiveStoragePlugin plugin, HiveReadEntry readEntry) {
    super(storageEngineName, plugin, readEntry);
    this.hiveTable = new Table(readEntry.getTable());
  }

  @Override
  public RelDataType getRowType(RelDataTypeFactory typeFactory) {
    List<RelDataType> typeList = Lists.newArrayList();
    List<String> fieldNameList = Lists.newArrayList();

    List<FieldSchema> hiveFields = hiveTable.getCols();
    for(FieldSchema hiveField : hiveFields) {
      fieldNameList.add(hiveField.getName());
      typeList.add(getNullableRelDataTypeFromHiveType(
          typeFactory, TypeInfoUtils.getTypeInfoFromTypeString(hiveField.getType())));
    }

    for (FieldSchema field : hiveTable.getPartitionKeys()) {
      fieldNameList.add(field.getName());
      typeList.add(getNullableRelDataTypeFromHiveType(
          typeFactory, TypeInfoUtils.getTypeInfoFromTypeString(field.getType())));
    }

    return typeFactory.createStructType(typeList, fieldNameList);
  }

  private RelDataType getNullableRelDataTypeFromHiveType(RelDataTypeFactory typeFactory, TypeInfo typeInfo) {
    RelDataType relDataType = getRelDataTypeFromHiveType(typeFactory, typeInfo);
    return typeFactory.createTypeWithNullability(relDataType, true);
  }

  private RelDataType getRelDataTypeFromHivePrimitiveType(RelDataTypeFactory typeFactory, PrimitiveTypeInfo pTypeInfo) {
    switch(pTypeInfo.getPrimitiveCategory()) {
      case BOOLEAN:
        return typeFactory.createSqlType(SqlTypeName.BOOLEAN);

      case BYTE:
      case SHORT:
        return typeFactory.createSqlType(SqlTypeName.INTEGER);

      case INT:
        return typeFactory.createSqlType(SqlTypeName.INTEGER);

      case LONG:
        return typeFactory.createSqlType(SqlTypeName.BIGINT);

      case FLOAT:
        return typeFactory.createSqlType(SqlTypeName.FLOAT);

      case DOUBLE:
        return typeFactory.createSqlType(SqlTypeName.DOUBLE);

      case DATE:
        return typeFactory.createSqlType(SqlTypeName.DATE);

      case TIMESTAMP:
        return typeFactory.createSqlType(SqlTypeName.TIMESTAMP);

      case BINARY:
        return typeFactory.createSqlType(SqlTypeName.BINARY);

      case DECIMAL: {
        DecimalTypeInfo decimalTypeInfo = (DecimalTypeInfo)pTypeInfo;
        return typeFactory.createSqlType(SqlTypeName.DECIMAL, decimalTypeInfo.precision(), decimalTypeInfo.scale());
      }

      case STRING:
      case VARCHAR: {
        int maxLen = TypeInfoUtils.getCharacterLengthForType(pTypeInfo);
        return typeFactory.createTypeWithCharsetAndCollation(
          typeFactory.createSqlType(SqlTypeName.VARCHAR, maxLen), /*input type*/
          Charset.forName("ISO-8859-1"), /*unicode char set*/
          SqlCollation.IMPLICIT /* TODO: need to decide if implicit is the correct one */
        );
      }

      case UNKNOWN:
      case VOID:
      default:
        throwUnsupportedHiveDataTypeError(pTypeInfo.getPrimitiveCategory().toString());
    }

    return null;
  }

  private RelDataType getRelDataTypeFromHiveType(RelDataTypeFactory typeFactory, TypeInfo typeInfo) {
    switch(typeInfo.getCategory()) {
      case PRIMITIVE:
        return getRelDataTypeFromHivePrimitiveType(typeFactory, ((PrimitiveTypeInfo) typeInfo));

      case LIST: {
        ListTypeInfo listTypeInfo = (ListTypeInfo)typeInfo;
        RelDataType listElemTypeInfo = getRelDataTypeFromHiveType(typeFactory, listTypeInfo.getListElementTypeInfo());
        return typeFactory.createArrayType(listElemTypeInfo, -1);
      }

      case MAP: {
        MapTypeInfo mapTypeInfo = (MapTypeInfo)typeInfo;
        RelDataType keyType = getRelDataTypeFromHiveType(typeFactory, mapTypeInfo.getMapKeyTypeInfo());
        RelDataType valueType = getRelDataTypeFromHiveType(typeFactory, mapTypeInfo.getMapValueTypeInfo());
        return typeFactory.createMapType(keyType, valueType);
      }

      case STRUCT: {
        StructTypeInfo structTypeInfo = (StructTypeInfo)typeInfo;
        ArrayList<String> fieldNames = structTypeInfo.getAllStructFieldNames();
        ArrayList<TypeInfo> fieldHiveTypeInfoList = structTypeInfo.getAllStructFieldTypeInfos();
        List<RelDataType> fieldRelDataTypeList = Lists.newArrayList();
        for(TypeInfo fieldHiveType : fieldHiveTypeInfoList) {
          fieldRelDataTypeList.add(getRelDataTypeFromHiveType(typeFactory, fieldHiveType));
        }
        return typeFactory.createStructType(fieldRelDataTypeList, fieldNames);
      }

      case UNION:
        logger.warn("There is no UNION data type in SQL. Converting it to Sql type OTHER to avoid " +
            "breaking INFORMATION_SCHEMA queries");
        return typeFactory.createSqlType(SqlTypeName.OTHER);
    }

    throwUnsupportedHiveDataTypeError(typeInfo.getCategory().toString());
    return null;
  }

  private void throwUnsupportedHiveDataTypeError(String hiveType) {
    StringBuilder errMsg = new StringBuilder();
    errMsg.append(String.format("Unsupported Hive data type %s. ", hiveType));
    errMsg.append(System.getProperty("line.separator"));
    errMsg.append("Following Hive data types are supported in Drill INFORMATION_SCHEMA: ");
    errMsg.append("BOOLEAN, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, DATE, TIMESTAMP, BINARY, DECIMAL, STRING, " +
        "VARCHAR, LIST, MAP, STRUCT and UNION");

    throw new RuntimeException(errMsg.toString());
  }
}


File: contrib/storage-hive/core/src/main/java/org/apache/drill/exec/store/hive/schema/DrillHiveViewTable.java
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
package org.apache.drill.exec.store.hive.schema;

import org.apache.calcite.schema.Schema.TableType;

import org.apache.drill.exec.planner.logical.DrillViewInfoProvider;
import org.apache.drill.exec.store.hive.HiveReadEntry;
import org.apache.drill.exec.store.hive.HiveStoragePlugin;

public class DrillHiveViewTable extends DrillHiveTable implements DrillViewInfoProvider {

  public DrillHiveViewTable(String storageEngineName, HiveStoragePlugin plugin, HiveReadEntry readEntry) {
    super(storageEngineName, plugin, readEntry);
  }

  @Override
  public TableType getJdbcTableType() {
    return TableType.VIEW;
  }

  @Override
  public String getViewSql() {
    return hiveTable.getViewExpandedText();
  }
}


File: contrib/storage-hive/core/src/main/java/org/apache/drill/exec/store/hive/schema/HiveSchemaFactory.java
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
package org.apache.drill.exec.store.hive.schema;

import java.io.IOException;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;

import org.apache.calcite.schema.Schema;
import org.apache.calcite.schema.SchemaPlus;

import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.exec.planner.logical.DrillTable;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.store.SchemaFactory;
import org.apache.drill.exec.store.hive.HiveReadEntry;
import org.apache.drill.exec.store.hive.HiveStoragePlugin;
import org.apache.drill.exec.store.hive.HiveStoragePluginConfig;
import org.apache.drill.exec.store.hive.HiveTable;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.metastore.HiveMetaStoreClient;
import org.apache.hadoop.hive.metastore.api.MetaException;
import org.apache.hadoop.hive.metastore.api.Partition;
import org.apache.hadoop.hive.metastore.api.Table;
import org.apache.hadoop.hive.metastore.api.UnknownTableException;
import org.apache.thrift.TException;

import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import com.google.common.collect.Sets;

public class HiveSchemaFactory implements SchemaFactory {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(HiveSchemaFactory.class);

  private static final String DATABASES = "databases";

  private final HiveMetaStoreClient mClient;
  private LoadingCache<String, List<String>> databases;
  private LoadingCache<String, List<String>> tableNameLoader;
  private LoadingCache<String, LoadingCache<String, HiveReadEntry>> tableLoaders;
  private HiveStoragePlugin plugin;
  private final String schemaName;
  private final Map<String, String> hiveConfigOverride;

  public HiveSchemaFactory(HiveStoragePlugin plugin, String name, Map<String, String> hiveConfigOverride) throws ExecutionSetupException {
    this.schemaName = name;
    this.plugin = plugin;

    this.hiveConfigOverride = hiveConfigOverride;
    HiveConf hiveConf = new HiveConf();
    if (hiveConfigOverride != null) {
      for (Map.Entry<String, String> entry : hiveConfigOverride.entrySet()) {
        hiveConf.set(entry.getKey(), entry.getValue());
      }
    }

    try {
      this.mClient = new HiveMetaStoreClient(hiveConf);
    } catch (MetaException e) {
      throw new ExecutionSetupException("Failure setting up Hive metastore client.", e);
    }

    databases = CacheBuilder //
        .newBuilder() //
        .expireAfterAccess(1, TimeUnit.MINUTES) //
        .build(new DatabaseLoader());

    tableNameLoader = CacheBuilder //
        .newBuilder() //
        .expireAfterAccess(1, TimeUnit.MINUTES) //
        .build(new TableNameLoader());

    tableLoaders = CacheBuilder //
        .newBuilder() //
        .expireAfterAccess(4, TimeUnit.HOURS) //
        .maximumSize(20) //
        .build(new TableLoaderLoader());
  }

  private class TableNameLoader extends CacheLoader<String, List<String>> {

    @Override
    public List<String> load(String dbName) throws Exception {
      try {
        return mClient.getAllTables(dbName);
      } catch (TException e) {
        logger.warn("Failure while attempting to get hive tables", e);
        mClient.reconnect();
        return mClient.getAllTables(dbName);
      }
    }

  }

  private class DatabaseLoader extends CacheLoader<String, List<String>> {

    @Override
    public List<String> load(String key) throws Exception {
      if (!DATABASES.equals(key)) {
        throw new UnsupportedOperationException();
      }
      try {
        return mClient.getAllDatabases();
      } catch (TException e) {
        logger.warn("Failure while attempting to get hive tables", e);
        mClient.reconnect();
        return mClient.getAllDatabases();
      }
    }
  }

  private class TableLoaderLoader extends CacheLoader<String, LoadingCache<String, HiveReadEntry>> {

    @Override
    public LoadingCache<String, HiveReadEntry> load(String key) throws Exception {
      return CacheBuilder.newBuilder().expireAfterAccess(1, TimeUnit.MINUTES).build(new TableLoader(key));
    }

  }

  private class TableLoader extends CacheLoader<String, HiveReadEntry> {

    private final String dbName;

    public TableLoader(String dbName) {
      super();
      this.dbName = dbName;
    }

    @Override
    public HiveReadEntry load(String key) throws Exception {
      Table t = null;
      try {
        t = mClient.getTable(dbName, key);
      } catch (TException e) {
        mClient.reconnect();
        t = mClient.getTable(dbName, key);
      }

      if (t == null) {
        throw new UnknownTableException(String.format("Unable to find table '%s'.", key));
      }

      List<Partition> partitions = null;
      try {
        partitions = mClient.listPartitions(dbName, key, Short.MAX_VALUE);
      } catch (TException e) {
        mClient.reconnect();
        partitions = mClient.listPartitions(dbName, key, Short.MAX_VALUE);
      }

      List<HiveTable.HivePartition> hivePartitions = Lists.newArrayList();
      for (Partition part : partitions) {
        hivePartitions.add(new HiveTable.HivePartition(part));
      }

      if (hivePartitions.size() == 0) {
        hivePartitions = null;
      }
      return new HiveReadEntry(new HiveTable(t), hivePartitions, hiveConfigOverride);

    }

  }

  @Override
  public void registerSchemas(SchemaConfig schemaConfig, SchemaPlus parent) throws IOException {
    HiveSchema schema = new HiveSchema(schemaName);
    SchemaPlus hPlus = parent.add(schemaName, schema);
    schema.setHolder(hPlus);
  }

  class HiveSchema extends AbstractSchema {

    private HiveDatabaseSchema defaultSchema;

    public HiveSchema(String name) {
      super(ImmutableList.<String>of(), name);
      getSubSchema("default");
    }

    @Override
    public AbstractSchema getSubSchema(String name) {
      List<String> tables;
      try {
        List<String> dbs = databases.get(DATABASES);
        if (!dbs.contains(name)) {
          logger.debug(String.format("Database '%s' doesn't exists in Hive storage '%s'", name, schemaName));
          return null;
        }
        tables = tableNameLoader.get(name);
        HiveDatabaseSchema schema = new HiveDatabaseSchema(tables, this, name);
        if (name.equals("default")) {
          this.defaultSchema = schema;
        }
        return schema;
      } catch (ExecutionException e) {
        logger.warn("Failure while attempting to access HiveDatabase '{}'.", name, e.getCause());
        return null;
      }

    }


    void setHolder(SchemaPlus plusOfThis) {
      for (String s : getSubSchemaNames()) {
        plusOfThis.add(s, getSubSchema(s));
      }
    }

    @Override
    public boolean showInInformationSchema() {
      return false;
    }

    @Override
    public Set<String> getSubSchemaNames() {
      try {
        List<String> dbs = databases.get(DATABASES);
        return Sets.newHashSet(dbs);
      } catch (ExecutionException e) {
        logger.warn("Failure while getting Hive database list.", e);
      }
      return super.getSubSchemaNames();
    }

    @Override
    public org.apache.calcite.schema.Table getTable(String name) {
      if (defaultSchema == null) {
        return super.getTable(name);
      }
      return defaultSchema.getTable(name);
    }

    @Override
    public Set<String> getTableNames() {
      if (defaultSchema == null) {
        return super.getTableNames();
      }
      return defaultSchema.getTableNames();
    }

    List<String> getTableNames(String dbName) {
      try{
        return tableNameLoader.get(dbName);
      } catch (ExecutionException e) {
        logger.warn("Failure while loading table names for database '{}'.", dbName, e.getCause());
        return Collections.emptyList();
      }
    }

    DrillTable getDrillTable(String dbName, String t) {
      HiveReadEntry entry = getSelectionBaseOnName(dbName, t);
      if (entry == null) {
        return null;
      }

      if (entry.getJdbcTableType() == TableType.VIEW) {
        return new DrillHiveViewTable(schemaName, plugin, entry);
      } else {
        return new DrillHiveTable(schemaName, plugin, entry);
      }
    }

    HiveReadEntry getSelectionBaseOnName(String dbName, String t) {
      if (dbName == null) {
        dbName = "default";
      }
      try{
        return tableLoaders.get(dbName).get(t);
      }catch(ExecutionException e) {
        logger.warn("Exception occurred while trying to read table. {}.{}", dbName, t, e.getCause());
        return null;
      }
    }

    @Override
    public AbstractSchema getDefaultSchema() {
      return defaultSchema;
    }

    @Override
    public String getTypeName() {
      return HiveStoragePluginConfig.NAME;
    }

  }

}


File: contrib/storage-hive/core/src/test/java/org/apache/drill/exec/store/hive/HiveTestDataGenerator.java
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

import java.io.File;
import java.io.PrintWriter;
import java.sql.Date;
import java.sql.Timestamp;
import java.util.Map;

import com.google.common.io.Files;
import org.apache.commons.io.FileUtils;
import org.apache.drill.BaseTestQuery;
import org.apache.drill.common.exceptions.DrillException;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.conf.HiveConf.ConfVars;
import org.apache.hadoop.hive.ql.CommandNeedRetryException;
import org.apache.hadoop.hive.ql.Driver;
import org.apache.hadoop.hive.ql.processors.CommandProcessorResponse;
import org.apache.hadoop.hive.ql.session.SessionState;

import com.google.common.collect.Maps;

public class HiveTestDataGenerator {
  private static final String HIVE_TEST_PLUGIN_NAME = "hive";
  private static final int RETRIES = 5;
  private static HiveTestDataGenerator instance;

  private final String dbDir;
  private final String whDir;
  private final Map<String, String> config;

  public static synchronized HiveTestDataGenerator getInstance() throws Exception {
    if (instance == null) {
      final File db = Files.createTempDir();
      db.deleteOnExit();
      final String dbDir = db.getAbsolutePath() + File.separator + "metastore_db";

      final File wh = Files.createTempDir();
      wh.deleteOnExit();
      final String whDir = wh.getAbsolutePath();

      instance = new HiveTestDataGenerator(dbDir, whDir);
      instance.generateTestData();
    }

    return instance;
  }

  private HiveTestDataGenerator(final String dbDir, final String whDir) {
    this.dbDir = dbDir;
    this.whDir = whDir;

    config = Maps.newHashMap();
    config.put("hive.metastore.uris", "");
    config.put("javax.jdo.option.ConnectionURL", String.format("jdbc:derby:;databaseName=%s;create=true", dbDir));
    config.put("hive.metastore.warehouse.dir", whDir);
    config.put(FileSystem.FS_DEFAULT_NAME_KEY, "file:///");
  }

  /**
   * Add Hive test storage plugin to the given plugin registry.
   * @throws Exception
   */
  public void addHiveTestPlugin(final StoragePluginRegistry pluginRegistry) throws Exception {
    HiveStoragePluginConfig pluginConfig = new HiveStoragePluginConfig(config);
    pluginConfig.setEnabled(true);

    pluginRegistry.createOrUpdate(HIVE_TEST_PLUGIN_NAME, pluginConfig, true);
  }

  /**
   * Update the current HiveStoragePlugin in given plugin registry with given <i>configOverride</i>.
   *
   * @param configOverride
   * @throws DrillException if fails to update or no Hive plugin currently exists in given plugin registry.
   */
  public void updatePluginConfig(final StoragePluginRegistry pluginRegistry, Map<String, String> configOverride)
      throws DrillException {
    HiveStoragePlugin storagePlugin = (HiveStoragePlugin) pluginRegistry.getPlugin(HIVE_TEST_PLUGIN_NAME);
    if (storagePlugin == null) {
      throw new DrillException(
          "Hive test storage plugin doesn't exist. Add a plugin using addHiveTestPlugin()");
    }

    HiveStoragePluginConfig newPluginConfig = storagePlugin.getConfig();
    newPluginConfig.getHiveConfigOverride().putAll(configOverride);

    pluginRegistry.createOrUpdate(HIVE_TEST_PLUGIN_NAME, newPluginConfig, true);
  }

  /**
   * Delete the Hive test plugin from registry.
   */
  public void deleteHiveTestPlugin(final StoragePluginRegistry pluginRegistry) {
    pluginRegistry.deletePlugin(HIVE_TEST_PLUGIN_NAME);
  }

  private void generateTestData() throws Exception {
    HiveConf conf = new HiveConf(SessionState.class);

    conf.set("javax.jdo.option.ConnectionURL", String.format("jdbc:derby:;databaseName=%s;create=true", dbDir));
    conf.set(FileSystem.FS_DEFAULT_NAME_KEY, "file:///");
    conf.set("hive.metastore.warehouse.dir", whDir);
    conf.set("mapred.job.tracker", "local");
    conf.set("hive.exec.scratchdir",  Files.createTempDir().getAbsolutePath() + File.separator + "scratch_dir");

    SessionState ss = new SessionState(conf);
    SessionState.start(ss);
    Driver hiveDriver = new Driver(conf);

    // generate (key, value) test data
    String testDataFile = generateTestDataFile();

    // Create a (key, value) schema table with Text SerDe which is available in hive-serdes.jar
    executeQuery(hiveDriver, "CREATE TABLE IF NOT EXISTS default.kv(key INT, value STRING) " +
        "ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' STORED AS TEXTFILE");
    executeQuery(hiveDriver, "LOAD DATA LOCAL INPATH '" + testDataFile + "' OVERWRITE INTO TABLE default.kv");

    // Create a (key, value) schema table in non-default database with RegexSerDe which is available in hive-contrib.jar
    // Table with RegExSerde is expected to have columns of STRING type only.
    executeQuery(hiveDriver, "CREATE DATABASE IF NOT EXISTS db1");
    executeQuery(hiveDriver, "CREATE TABLE db1.kv_db1(key STRING, value STRING) " +
        "ROW FORMAT SERDE 'org.apache.hadoop.hive.contrib.serde2.RegexSerDe' " +
        "WITH SERDEPROPERTIES (" +
        "  \"input.regex\" = \"([0-9]*), (.*_[0-9]*)\", " +
        "  \"output.format.string\" = \"%1$s, %2$s\"" +
        ") ");
    executeQuery(hiveDriver, "INSERT INTO TABLE db1.kv_db1 SELECT * FROM default.kv");

    // Create an Avro format based table backed by schema in a separate file
    final String avroCreateQuery = String.format("CREATE TABLE db1.avro " +
        "ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.avro.AvroSerDe' " +
        "STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.avro.AvroContainerInputFormat' " +
        "OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.avro.AvroContainerOutputFormat' " +
        "TBLPROPERTIES ('avro.schema.url'='file:///%s')", getSchemaFile("avro_test_schema.json"));

    executeQuery(hiveDriver, avroCreateQuery);
    executeQuery(hiveDriver, "INSERT INTO TABLE db1.avro SELECT * FROM default.kv");

    executeQuery(hiveDriver, "USE default");

    // create a table with no data
    executeQuery(hiveDriver, "CREATE TABLE IF NOT EXISTS empty_table(a INT, b STRING)");
    // delete the table location of empty table
    File emptyTableLocation = new File(whDir, "empty_table");
    if (emptyTableLocation.exists()) {
      FileUtils.forceDelete(emptyTableLocation);
    }

    // create a Hive table that has columns with data types which are supported for reading in Drill.
    testDataFile = generateAllTypesDataFile();
    executeQuery(hiveDriver,
        "CREATE TABLE IF NOT EXISTS readtest (" +
        "  binary_field BINARY," +
        "  boolean_field BOOLEAN," +
        "  tinyint_field TINYINT," +
        "  decimal0_field DECIMAL," +
        "  decimal9_field DECIMAL(6, 2)," +
        "  decimal18_field DECIMAL(15, 5)," +
        "  decimal28_field DECIMAL(23, 1)," +
        "  decimal38_field DECIMAL(30, 3)," +
        "  double_field DOUBLE," +
        "  float_field FLOAT," +
        "  int_field INT," +
        "  bigint_field BIGINT," +
        "  smallint_field SMALLINT," +
        "  string_field STRING," +
        "  varchar_field VARCHAR(50)," +
        "  timestamp_field TIMESTAMP," +
        "  date_field DATE" +
        ") PARTITIONED BY (" +
        "  binary_part BINARY," +
        "  boolean_part BOOLEAN," +
        "  tinyint_part TINYINT," +
        "  decimal0_part DECIMAL," +
        "  decimal9_part DECIMAL(6, 2)," +
        "  decimal18_part DECIMAL(15, 5)," +
        "  decimal28_part DECIMAL(23, 1)," +
        "  decimal38_part DECIMAL(30, 3)," +
        "  double_part DOUBLE," +
        "  float_part FLOAT," +
        "  int_part INT," +
        "  bigint_part BIGINT," +
        "  smallint_part SMALLINT," +
        "  string_part STRING," +
        "  varchar_part VARCHAR(50)," +
        "  timestamp_part TIMESTAMP," +
        "  date_part DATE" +
        ") ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' " +
        "TBLPROPERTIES ('serialization.null.format'='') "
    );

    // Add a partition to table 'readtest'
    executeQuery(hiveDriver,
        "ALTER TABLE readtest ADD IF NOT EXISTS PARTITION ( " +
        "  binary_part='binary', " +
        "  boolean_part='true', " +
        "  tinyint_part='64', " +
        "  decimal0_part='36.9', " +
        "  decimal9_part='36.9', " +
        "  decimal18_part='3289379872.945645', " +
        "  decimal28_part='39579334534534.35345', " +
        "  decimal38_part='363945093845093890.9', " +
        "  double_part='8.345', " +
        "  float_part='4.67', " +
        "  int_part='123456', " +
        "  bigint_part='234235', " +
        "  smallint_part='3455', " +
        "  string_part='string', " +
        "  varchar_part='varchar', " +
        "  timestamp_part='2013-07-05 17:01:00', " +
        "  date_part='2013-07-05')"
    );

    // Load data into table 'readtest'
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' OVERWRITE INTO TABLE default.readtest PARTITION (" +
        "  binary_part='binary', " +
        "  boolean_part='true', " +
        "  tinyint_part='64', " +
        "  decimal0_part='36.9', " +
        "  decimal9_part='36.9', " +
        "  decimal18_part='3289379872.945645', " +
        "  decimal28_part='39579334534534.35345', " +
        "  decimal38_part='363945093845093890.9', " +
        "  double_part='8.345', " +
        "  float_part='4.67', " +
        "  int_part='123456', " +
        "  bigint_part='234235', " +
        "  smallint_part='3455', " +
        "  string_part='string', " +
        "  varchar_part='varchar', " +
        "  timestamp_part='2013-07-05 17:01:00', " +
        "  date_part='2013-07-05')", testDataFile));

    // create a table that has all Hive types. This is to test how hive tables metadata is populated in
    // Drill's INFORMATION_SCHEMA.
    executeQuery(hiveDriver,
        "CREATE TABLE IF NOT EXISTS infoschematest(" +
        "booleanType BOOLEAN, " +
        "tinyintType TINYINT, " +
        "smallintType SMALLINT, " +
        "intType INT, " +
        "bigintType BIGINT, " +
        "floatType FLOAT, " +
        "doubleType DOUBLE, " +
        "dateType DATE, " +
        "timestampType TIMESTAMP, " +
        "binaryType BINARY, " +
        "decimalType DECIMAL(38, 2), " +
        "stringType STRING, " +
        "varCharType VARCHAR(20), " +
        "listType ARRAY<STRING>, " +
        "mapType MAP<STRING,INT>, " +
        "structType STRUCT<sint:INT,sboolean:BOOLEAN,sstring:STRING>, " +
        "uniontypeType UNIONTYPE<int, double, array<string>>)"
    );

    // create a Hive view to test how its metadata is populated in Drill's INFORMATION_SCHEMA
    executeQuery(hiveDriver, "CREATE VIEW IF NOT EXISTS hiveview AS SELECT * FROM kv");

    // Generate data with date and timestamp data type
    String testDateDataFile = generateTestDataFileWithDate();

    // create partitioned hive table to test partition pruning
    executeQuery(hiveDriver,
        "CREATE TABLE IF NOT EXISTS default.partition_pruning_test(a DATE, b TIMESTAMP) "+
        "partitioned by (c int, d int, e int) ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' STORED AS TEXTFILE");
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' INTO TABLE default.partition_pruning_test partition(c=1, d=1, e=1)", testDateDataFile));
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' INTO TABLE default.partition_pruning_test partition(c=1, d=1, e=2)", testDateDataFile));
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' INTO TABLE default.partition_pruning_test partition(c=1, d=2, e=1)", testDateDataFile));
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' INTO TABLE default.partition_pruning_test partition(c=1, d=1, e=2)", testDateDataFile));
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' INTO TABLE default.partition_pruning_test partition(c=2, d=1, e=1)", testDateDataFile));
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' INTO TABLE default.partition_pruning_test partition(c=2, d=1, e=2)", testDateDataFile));
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' INTO TABLE default.partition_pruning_test partition(c=2, d=3, e=1)", testDateDataFile));
    executeQuery(hiveDriver,
        String.format("LOAD DATA LOCAL INPATH '%s' INTO TABLE default.partition_pruning_test partition(c=2, d=3, e=2)", testDateDataFile));

    ss.close();
  }

  private File getTempFile() throws Exception {
    return java.nio.file.Files.createTempFile("drill-hive-test", ".txt").toFile();
  }

  private String generateTestDataFile() throws Exception {
    final File file = getTempFile();
    PrintWriter printWriter = new PrintWriter(file);
    for (int i=1; i<=5; i++) {
      printWriter.println (String.format("%d, key_%d", i, i));
    }
    printWriter.close();

    return file.getPath();
  }

  private String getSchemaFile(final String resource) throws Exception {
    final File file = getTempFile();
    PrintWriter printWriter = new PrintWriter(file);
    printWriter.write(BaseTestQuery.getFile(resource));
    printWriter.close();

    return file.getPath();
  }

  private String generateTestDataFileWithDate() throws Exception {
    final File file = getTempFile();

    PrintWriter printWriter = new PrintWriter(file);
    for (int i=1; i<=5; i++) {
      Date date = new Date(System.currentTimeMillis());
      Timestamp ts = new Timestamp(System.currentTimeMillis());
      printWriter.println (String.format("%s,%s", date.toString(), ts.toString()));
    }
    printWriter.close();

    return file.getPath();
  }

  private String generateAllTypesDataFile() throws Exception {
    File file = getTempFile();

    PrintWriter printWriter = new PrintWriter(file);
    printWriter.println("YmluYXJ5ZmllbGQ=,false,34,65.99,2347.923,2758725827.9999,29375892739852.7689," +
        "89853749534593985.7834783,8.345,4.67,123456,234235,3455,stringfield,varcharfield," +
        "2013-07-05 17:01:00,2013-07-05");
    printWriter.println(",,,,,,,,,,,,,,,,");
    printWriter.close();

    return file.getPath();
  }

  private void executeQuery(Driver hiveDriver, String query) {
    CommandProcessorResponse response = null;
    boolean failed = false;
    int retryCount = RETRIES;

    try {
      response = hiveDriver.run(query);
    } catch(CommandNeedRetryException ex) {
      if (--retryCount == 0) {
        failed = true;
      }
    }

    if (failed || response.getResponseCode() != 0 ) {
      throw new RuntimeException(String.format("Failed to execute command '%s', errorMsg = '%s'",
        query, (response != null ? response.getErrorMessage() : "")));
    }
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

import io.netty.buffer.DrillBuf;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.jdbc.SimpleCalciteSchema;

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
  public SchemaPlus getRootSchema(String userName) {
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
        // TODO(DRILL-1942) the new allocator has this capability built-in, so this can be removed once that is available
        bufferManager.close();
        allocator.close();
      }
    } finally {
      closed = true;
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/AbstractSchema.java
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
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Set;

import org.apache.calcite.linq4j.tree.DefaultExpression;
import org.apache.calcite.linq4j.tree.Expression;
import org.apache.calcite.schema.Function;
import org.apache.calcite.schema.Schema;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.schema.Table;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.dotdrill.View;
import org.apache.drill.exec.planner.logical.CreateTableEntry;

import com.google.common.base.Joiner;
import com.google.common.collect.Lists;

public abstract class AbstractSchema implements Schema, SchemaPartitionExplorer {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(AbstractSchema.class);

  protected final List<String> schemaPath;
  protected final String name;
  private static final Expression EXPRESSION = new DefaultExpression(Object.class);

  public AbstractSchema(List<String> parentSchemaPath, String name) {
    schemaPath = Lists.newArrayList();
    schemaPath.addAll(parentSchemaPath);
    schemaPath.add(name);
    this.name = name;
  }

  @Override
  public Iterable<String> getSubPartitions(String table,
                                           List<String> partitionColumns,
                                           List<String> partitionValues
                                          ) throws PartitionNotFoundException {
    throw new UnsupportedOperationException(
        String.format("Schema of type: %s " +
                      "does not support retrieving sub-partition information.",
                      this.getClass().getSimpleName()));
  }

  public String getName() {
    return name;
  }

  public List<String> getSchemaPath() {
    return schemaPath;
  }

  public String getFullSchemaName() {
    return Joiner.on(".").join(schemaPath);
  }

  public abstract String getTypeName();

  /**
   * The schema can be a top level schema which doesn't have its own tables, but refers
   * to one of the default sub schemas for table look up.
   *
   * Default implementation returns itself.
   *
   * Ex. "dfs" schema refers to the tables in "default" workspace when querying for
   * tables in "dfs" schema.
   *
   * @return Return the default schema where tables are created or retrieved from.
   */
  public AbstractSchema getDefaultSchema() {
    return this;
  }

  /**
   * Create a new view given definition.
   * @param view View info including name, definition etc.
   * @return Returns true if an existing view is replaced with the given view. False otherwise.
   * @throws IOException
   */
  public boolean createView(View view) throws IOException {
    throw UserException.unsupportedError()
        .message("Creating new view is not supported in schema [%s]", getSchemaPath())
        .build(logger);
  }

  /**
   * Drop the view with given name.
   *
   * @param viewName
   * @throws IOException
   */
  public void dropView(String viewName) throws IOException {
    throw UserException.unsupportedError()
        .message("Dropping a view is supported in schema [%s]", getSchemaPath())
        .build(logger);
  }

  /**
   *
   * @param tableName : new table name.
   * @param partitionColumns : list of partition columns. Empty list if there is no partition columns.
   * @return
   */
  public CreateTableEntry createNewTable(String tableName, List<String> partitionColumns) {
    throw UserException.unsupportedError()
        .message("Creating new tables is not supported in schema [%s]", getSchemaPath())
        .build(logger);
  }

  /**
   * Reports whether to show items from this schema in INFORMATION_SCHEMA
   * tables.
   * (Controls ... TODO:  Doc.:  Mention what this typically controls or
   * affects.)
   * <p>
   *   This base implementation returns {@code true}.
   * </p>
   */
  public boolean showInInformationSchema() {
    return true;
  }

  @Override
  public Collection<Function> getFunctions(String name) {
    return Collections.emptyList();
  }

  @Override
  public Set<String> getFunctionNames() {
    return Collections.emptySet();
  }

  @Override
  public AbstractSchema getSubSchema(String name) {
    return null;
  }

  @Override
  public Set<String> getSubSchemaNames() {
    return Collections.emptySet();
  }

  @Override
  public boolean isMutable() {
    return false;
  }

  @Override
  public Table getTable(String name){
    return null;
  }

  @Override
  public Set<String> getTableNames() {
    return Collections.emptySet();
  }

  @Override
  public Expression getExpression(SchemaPlus parentSchema, String name) {
    return EXPRESSION;
  }

  @Override
  public boolean contentsHaveChangedSince(long lastCheck, long now) {
    return true;
  }


}


File: exec/java-exec/src/main/java/org/apache/drill/exec/util/ImpersonationUtil.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.util;

import com.google.common.base.Strings;
import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.exec.ops.OperatorStats;
import org.apache.drill.exec.store.dfs.DrillFileSystem;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.security.UserGroupInformation;

import java.io.IOException;
import java.security.PrivilegedExceptionAction;

/**
 * Utilities for impersonation purpose.
 */
public class ImpersonationUtil {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ImpersonationUtil.class);

  /**
   * Create and return proxy user {@link org.apache.hadoop.security.UserGroupInformation} of operator owner if operator
   * owner is valid. Otherwise create and return proxy user {@link org.apache.hadoop.security.UserGroupInformation} for
   * query user.
   *
   * @param opUserName Name of the user whom to impersonate while setting up the operator.
   * @param queryUserName Name of the user who issues the query. If <i>opUserName</i> is invalid,
   *                      then this parameter must be valid user name.
   * @return
   */
  public static UserGroupInformation createProxyUgi(String opUserName, String queryUserName) {
    if (!Strings.isNullOrEmpty(opUserName)) {
      return createProxyUgi(opUserName);
    }

    if (Strings.isNullOrEmpty(queryUserName)) {
      // TODO(DRILL-2097): Tests that use SimpleRootExec have don't assign any query user name in FragmentContext.
      // Disable throwing exception to modifying the long list of test files.
      // throw new DrillRuntimeException("Invalid value for query user name");
      return getProcessUserUGI();
    }

    return createProxyUgi(queryUserName);
  }

  /**
   * Create and return proxy user {@link org.apache.hadoop.security.UserGroupInformation} for give user name.
   *
   * TODO: we may want to cache the {@link org.apache.hadoop.security.UserGroupInformation} instances as we try to
   * create different instances for the same user which is an unnecessary overhead.
   *
   * @param proxyUserName Proxy user name (must be valid)
   * @return
   */
  public static UserGroupInformation createProxyUgi(String proxyUserName) {
    try {
      if (Strings.isNullOrEmpty(proxyUserName)) {
        throw new DrillRuntimeException("Invalid value for proxy user name");
      }

      // If the request proxy user is same as process user name, return the process UGI.
      if (proxyUserName.equals(getProcessUserName())) {
        return getProcessUserUGI();
      }

      return UserGroupInformation.createProxyUser(proxyUserName, UserGroupInformation.getLoginUser());
    } catch(IOException e) {
      final String errMsg = "Failed to create proxy user UserGroupInformation object: " + e.getMessage();
      logger.error(errMsg, e);
      throw new DrillRuntimeException(errMsg, e);
    }
  }

  /**
   * If the given user name is empty, return the current process user name. This is a temporary change to avoid
   * modifying long list of tests files which have GroupScan operator with no user name property.
   * @param userName User name found in GroupScan POP definition.
   */
  public static String resolveUserName(String userName) {
    if (!Strings.isNullOrEmpty(userName)) {
      return userName;
    }
    return getProcessUserName();
  }

  /**
   * Return the name of the user who is running the Drillbit.
   *
   * @return Drillbit process user.
   */
  public static String getProcessUserName() {
    return getProcessUserUGI().getUserName();
  }

  /**
   * Return the {@link org.apache.hadoop.security.UserGroupInformation} of user who is running the Drillbit.
   *
   * @return Drillbit process user {@link org.apache.hadoop.security.UserGroupInformation}.
   */
  public static UserGroupInformation getProcessUserUGI() {
    try {
      return UserGroupInformation.getLoginUser();
    } catch (IOException e) {
      final String errMsg = "Failed to get process user UserGroupInformation object.";
      logger.error(errMsg, e);
      throw new DrillRuntimeException(errMsg, e);
    }
  }

  /**
   * Create DrillFileSystem for given <i>proxyUserName</i> and configuration.
   *
   * @param proxyUserName Name of the user whom to impersonate while accessing the FileSystem contents.
   * @param fsConf FileSystem configuration.
   * @return
   */
  public static DrillFileSystem createFileSystem(String proxyUserName, Configuration fsConf) {
    return createFileSystem(proxyUserName, fsConf, null);
  }

  /**
   * Create DrillFileSystem for given <i>proxyUserName</i>, configuration and stats.
   *
   * @param proxyUserName Name of the user whom to impersonate while accessing the FileSystem contents.
   * @param fsConf FileSystem configuration.
   * @param stats OperatorStats for DrillFileSystem (optional)
   * @return
   */
  public static DrillFileSystem createFileSystem(String proxyUserName, Configuration fsConf, OperatorStats stats) {
    return createFileSystem(createProxyUgi(proxyUserName), fsConf, stats);
  }

  /** Helper method to create DrillFileSystem */
  private static DrillFileSystem createFileSystem(UserGroupInformation proxyUserUgi, final Configuration fsConf,
      final OperatorStats stats) {
    DrillFileSystem fs;
    try {
      fs = proxyUserUgi.doAs(new PrivilegedExceptionAction<DrillFileSystem>() {
        public DrillFileSystem run() throws Exception {
          logger.debug("Creating DrillFileSystem for proxy user: " + UserGroupInformation.getCurrentUser());
          return new DrillFileSystem(fsConf, stats);
        }
      });
    } catch (InterruptedException | IOException e) {
      final String errMsg = "Failed to create DrillFileSystem for proxy user: " + e.getMessage();
      logger.error(errMsg, e);
      throw new DrillRuntimeException(errMsg, e);
    }

    return fs;
  }
}


File: exec/java-exec/src/test/java/org/apache/drill/BaseTestQuery.java
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
package org.apache.drill;

import java.io.IOException;
import java.net.URL;
import java.util.Arrays;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.ExecTest;
import org.apache.drill.exec.client.DrillClient;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.memory.TopLevelAllocator;
import org.apache.drill.exec.proto.UserBitShared.QueryId;
import org.apache.drill.exec.proto.UserBitShared.QueryResult.QueryState;
import org.apache.drill.exec.proto.UserBitShared.QueryType;
import org.apache.drill.exec.record.RecordBatchLoader;
import org.apache.drill.exec.rpc.user.ConnectionThrottle;
import org.apache.drill.exec.rpc.user.QueryDataBatch;
import org.apache.drill.exec.rpc.user.UserResultsListener;
import org.apache.drill.exec.server.Drillbit;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.server.RemoteServiceSet;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.drill.exec.util.JsonStringArrayList;
import org.apache.drill.exec.util.JsonStringHashMap;
import org.apache.drill.exec.util.TestUtilities;
import org.apache.drill.exec.util.VectorUtil;
import org.apache.hadoop.io.Text;
import org.junit.AfterClass;
import org.junit.BeforeClass;
import org.junit.rules.TestRule;
import org.junit.rules.TestWatcher;
import org.junit.runner.Description;

import com.google.common.base.Charsets;
import com.google.common.base.Preconditions;
import com.google.common.io.Resources;

import static org.hamcrest.core.StringContains.containsString;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertThat;

public class BaseTestQuery extends ExecTest {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(BaseTestQuery.class);

  protected static final String TEMP_SCHEMA = "dfs_test.tmp";

  private static final String ENABLE_FULL_CACHE = "drill.exec.test.use-full-cache";
  private static final int MAX_WIDTH_PER_NODE = 2;

  @SuppressWarnings("serial")
  private static final Properties TEST_CONFIGURATIONS = new Properties() {
    {
      put(ExecConstants.SYS_STORE_PROVIDER_LOCAL_ENABLE_WRITE, "false");
      put(ExecConstants.HTTP_ENABLE, "false");
    }
  };

  public final TestRule resetWatcher = new TestWatcher() {
    @Override
    protected void failed(Throwable e, Description description) {
      try {
        resetClientAndBit();
      } catch (Exception e1) {
        throw new RuntimeException("Failure while resetting client.", e1);
      }
    }
  };

  protected static DrillClient client;
  protected static Drillbit[] bits;
  protected static RemoteServiceSet serviceSet;
  protected static DrillConfig config;
  protected static BufferAllocator allocator;

  /**
   * Number of Drillbits in test cluster. Default is 1.
   *
   * Tests can update the cluster size through {@link #updateTestCluster(int, DrillConfig)}
   */
  private static int drillbitCount = 1;

  /**
   * Location of the dfs_test.tmp schema on local filesystem.
   */
  private static String dfsTestTmpSchemaLocation;

  private int[] columnWidths = new int[] { 8 };

  @BeforeClass
  public static void setupDefaultTestCluster() throws Exception {
    config = DrillConfig.create(TEST_CONFIGURATIONS);
    openClient();
  }

  protected static void updateTestCluster(int newDrillbitCount, DrillConfig newConfig) {
    Preconditions.checkArgument(newDrillbitCount > 0, "Number of Drillbits must be at least one");
    if (drillbitCount != newDrillbitCount || config != null) {
      // TODO: Currently we have to shutdown the existing Drillbit cluster before starting a new one with the given
      // Drillbit count. Revisit later to avoid stopping the cluster.
      try {
        closeClient();
        drillbitCount = newDrillbitCount;
        if (newConfig != null) {
          // For next test class, updated DrillConfig will be replaced by default DrillConfig in BaseTestQuery as part
          // of the @BeforeClass method of test class.
          config = newConfig;
        }
        openClient();
      } catch(Exception e) {
        throw new RuntimeException("Failure while updating the test Drillbit cluster.", e);
      }
    }
  }

  /**
   * Useful for tests that require a DrillbitContext to get/add storage plugins, options etc.
   *
   * @return DrillbitContext of first Drillbit in the cluster.
   */
  protected static DrillbitContext getDrillbitContext() {
    Preconditions.checkState(bits != null && bits[0] != null, "Drillbits are not setup.");
    return bits[0].getContext();
  }

  protected static Properties cloneDefaultTestConfigProperties() {
    final Properties props = new Properties();
    for(String propName : TEST_CONFIGURATIONS.stringPropertyNames()) {
      props.put(propName, TEST_CONFIGURATIONS.getProperty(propName));
    }

    return props;
  }

  protected static String getDfsTestTmpSchemaLocation() {
    return dfsTestTmpSchemaLocation;
  }

  private static void resetClientAndBit() throws Exception{
    closeClient();
    openClient();
  }

  private static void openClient() throws Exception {
    allocator = new TopLevelAllocator(config);
    if (config.hasPath(ENABLE_FULL_CACHE) && config.getBoolean(ENABLE_FULL_CACHE)) {
      serviceSet = RemoteServiceSet.getServiceSetWithFullCache(config, allocator);
    } else {
      serviceSet = RemoteServiceSet.getLocalServiceSet();
    }

    dfsTestTmpSchemaLocation = TestUtilities.createTempDir();

    bits = new Drillbit[drillbitCount];
    for(int i = 0; i < drillbitCount; i++) {
      bits[i] = new Drillbit(config, serviceSet);
      bits[i].run();

      final StoragePluginRegistry pluginRegistry = bits[i].getContext().getStorage();
      TestUtilities.updateDfsTestTmpSchemaLocation(pluginRegistry, dfsTestTmpSchemaLocation);
      TestUtilities.makeDfsTmpSchemaImmutable(pluginRegistry);
    }

    client = QueryTestUtil.createClient(config,  serviceSet, MAX_WIDTH_PER_NODE, null);
  }

  /**
   * Close the current <i>client</i> and open a new client using the given <i>properties</i>. All tests executed
   * after this method call use the new <i>client</i>.
   *
   * @param properties
   */
  public static void updateClient(Properties properties) throws Exception {
    Preconditions.checkState(bits != null && bits[0] != null, "Drillbits are not setup.");
    if (client != null) {
      client.close();
      client = null;
    }

    client = QueryTestUtil.createClient(config, serviceSet, MAX_WIDTH_PER_NODE, properties);
  }

  /*
   * Close the current <i>client</i> and open a new client for the given user. All tests executed
   * after this method call use the new <i>client</i>.
   * @param user
   */
  public static void updateClient(String user) throws Exception {
    final Properties props = new Properties();
    props.setProperty("user", user);
    updateClient(props);
  }

  protected static BufferAllocator getAllocator() {
    return allocator;
  }

  public static TestBuilder newTest() {
    return testBuilder();
  }

  public static TestBuilder testBuilder() {
    return new TestBuilder(allocator);
  }

  @AfterClass
  public static void closeClient() throws IOException, InterruptedException {
    if (client != null) {
      client.close();
    }

    if (bits != null) {
      for(Drillbit bit : bits) {
        if (bit != null) {
          bit.close();
        }
      }
    }

    if(serviceSet != null) {
      serviceSet.close();
    }
    if (allocator != null) {
      allocator.close();
    }
  }

  @AfterClass
  public static void resetDrillbitCount() {
    // some test classes assume this value to be 1 and will fail if run along other tests that increase it
    drillbitCount = 1;
  }

  protected static void runSQL(String sql) throws Exception {
    SilentListener listener = new SilentListener();
    testWithListener(QueryType.SQL, sql, listener);
    listener.waitForCompletion();
  }

  protected static List<QueryDataBatch> testSqlWithResults(String sql) throws Exception{
    return testRunAndReturn(QueryType.SQL, sql);
  }

  protected static List<QueryDataBatch> testLogicalWithResults(String logical) throws Exception{
    return testRunAndReturn(QueryType.LOGICAL, logical);
  }

  protected static List<QueryDataBatch> testPhysicalWithResults(String physical) throws Exception{
    return testRunAndReturn(QueryType.PHYSICAL, physical);
  }

  public static List<QueryDataBatch>  testRunAndReturn(QueryType type, String query) throws Exception{
    query = QueryTestUtil.normalizeQuery(query);
    return client.runQuery(type, query);
  }

  public static int testRunAndPrint(final QueryType type, final String query) throws Exception {
    return QueryTestUtil.testRunAndPrint(client, type, query);
  }

  protected static void testWithListener(QueryType type, String query, UserResultsListener resultListener) {
    QueryTestUtil.testWithListener(client, type, query, resultListener);
  }

  protected static void testNoResult(String query, Object... args) throws Exception {
    testNoResult(1, query, args);
  }

  protected static void testNoResult(int interation, String query, Object... args) throws Exception {
    query = String.format(query, args);
    logger.debug("Running query:\n--------------\n" + query);
    for (int i = 0; i < interation; i++) {
      List<QueryDataBatch> results = client.runQuery(QueryType.SQL, query);
      for (QueryDataBatch queryDataBatch : results) {
        queryDataBatch.release();
      }
    }
  }

  public static void test(String query, Object... args) throws Exception {
    QueryTestUtil.test(client, String.format(query, args));
  }

  public static void test(final String query) throws Exception {
    QueryTestUtil.test(client, query);
  }

  protected static int testLogical(String query) throws Exception{
    return testRunAndPrint(QueryType.LOGICAL, query);
  }

  protected static int testPhysical(String query) throws Exception{
    return testRunAndPrint(QueryType.PHYSICAL, query);
  }

  protected static int testSql(String query) throws Exception{
    return testRunAndPrint(QueryType.SQL, query);
  }

  protected static void testPhysicalFromFile(String file) throws Exception{
    testPhysical(getFile(file));
  }

  protected static List<QueryDataBatch> testPhysicalFromFileWithResults(String file) throws Exception {
    return testRunAndReturn(QueryType.PHYSICAL, getFile(file));
  }

  protected static void testLogicalFromFile(String file) throws Exception{
    testLogical(getFile(file));
  }

  protected static void testSqlFromFile(String file) throws Exception{
    test(getFile(file));
  }

  /**
   * Utility method which tests given query produces a {@link UserException} and the exception message contains
   * the given message.
   * @param testSqlQuery Test query
   * @param expectedErrorMsg Expected error message.
   */
  protected static void errorMsgTestHelper(final String testSqlQuery, final String expectedErrorMsg) throws Exception {
    UserException expException = null;
    try {
      test(testSqlQuery);
    } catch (final UserException ex) {
      expException = ex;
    }

    assertNotNull("Expected a UserException", expException);
    assertThat(expException.getMessage(), containsString(expectedErrorMsg));
  }

  public static String getFile(String resource) throws IOException{
    URL url = Resources.getResource(resource);
    if (url == null) {
      throw new IOException(String.format("Unable to find path %s.", resource));
    }
    return Resources.toString(url, Charsets.UTF_8);
  }

  private static class SilentListener implements UserResultsListener {
    private volatile UserException exception;
    private AtomicInteger count = new AtomicInteger();
    private CountDownLatch latch = new CountDownLatch(1);

    @Override
    public void submissionFailed(UserException ex) {
      exception = ex;
      System.out.println("Query failed: " + ex.getMessage());
      latch.countDown();
    }

    @Override
    public void queryCompleted(QueryState state) {
      System.out.println("Query completed successfully with row count: " + count.get());
      latch.countDown();
    }

    @Override
    public void dataArrived(QueryDataBatch result, ConnectionThrottle throttle) {
      int rows = result.getHeader().getRowCount();
      if (result.getData() != null) {
        count.addAndGet(rows);
      }
      result.release();
    }

    @Override
    public void queryIdArrived(QueryId queryId) {}

    public int waitForCompletion() throws Exception {
      latch.await();
      if (exception != null) {
        throw exception;
      }
      return count.get();
    }
  }

  protected void setColumnWidth(int columnWidth) {
    this.columnWidths = new int[] { columnWidth };
  }

  protected void setColumnWidths(int[] columnWidths) {
    this.columnWidths = columnWidths;
  }

  protected int printResult(List<QueryDataBatch> results) throws SchemaChangeException {
    int rowCount = 0;
    RecordBatchLoader loader = new RecordBatchLoader(getAllocator());
    for(QueryDataBatch result : results) {
      rowCount += result.getHeader().getRowCount();
      loader.load(result.getHeader().getDef(), result.getData());
      // TODO:  Clean:  DRILL-2933:  That load(...) no longer throws
      // SchemaChangeException, so check/clean throw clause above.
      if (loader.getRecordCount() <= 0) {
        continue;
      }
      VectorUtil.showVectorAccessibleContent(loader, columnWidths);
      loader.clear();
      result.release();
    }
    System.out.println("Total record count: " + rowCount);
    return rowCount;
  }

  protected static String getResultString(List<QueryDataBatch> results, String delimiter)
      throws SchemaChangeException {
    StringBuilder formattedResults = new StringBuilder();
    boolean includeHeader = true;
    RecordBatchLoader loader = new RecordBatchLoader(getAllocator());
    for(QueryDataBatch result : results) {
      loader.load(result.getHeader().getDef(), result.getData());
      if (loader.getRecordCount() <= 0) {
        continue;
      }
      VectorUtil.appendVectorAccessibleContent(loader, formattedResults, delimiter, includeHeader);
      if (!includeHeader) {
        includeHeader = false;
      }
      loader.clear();
      result.release();
    }

    return formattedResults.toString();
  }
}


File: exec/java-exec/src/test/java/org/apache/drill/exec/impersonation/BaseTestImpersonation.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.impersonation;

import com.google.common.base.Preconditions;
import com.google.common.base.Strings;
import org.apache.commons.io.FileUtils;
import org.apache.drill.PlanTestBase;
import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.store.dfs.WorkspaceConfig;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.fs.permission.FsPermission;
import org.apache.hadoop.hdfs.MiniDFSCluster;

import java.io.File;
import java.util.Map;
import java.util.Properties;

public class BaseTestImpersonation extends PlanTestBase {
  protected static final String processUser = System.getProperty("user.name");

  protected static MiniDFSCluster dfsCluster;
  protected static Configuration conf;
  protected static String miniDfsStoragePath;

  /**
   * Start a MiniDFS cluster backed Drillbit cluster with impersonation enabled.
   * @param testClass
   * @throws Exception
   */
  protected static void startMiniDfsCluster(String testClass) throws Exception {
    startMiniDfsCluster(testClass, true);
  }

  /**
   * Start a MiniDFS cluster backed Drillbit cluster
   * @param testClass
   * @param isImpersonationEnabled Enable impersonation in the cluster?
   * @throws Exception
   */
  protected static void startMiniDfsCluster(
      final String testClass, final boolean isImpersonationEnabled) throws Exception {
    Preconditions.checkArgument(!Strings.isNullOrEmpty(testClass), "Expected a non-null and non-empty test class name");
    conf = new Configuration();

    // Set the MiniDfs base dir to be the temp directory of the test, so that all files created within the MiniDfs
    // are properly cleanup when test exits.
    miniDfsStoragePath = System.getProperty("java.io.tmpdir") + Path.SEPARATOR + testClass;
    conf.set("hdfs.minidfs.basedir", miniDfsStoragePath);

    if (isImpersonationEnabled) {
      // Set the proxyuser settings so that the user who is running the Drillbits/MiniDfs can impersonate other users.
      conf.set(String.format("hadoop.proxyuser.%s.hosts", processUser), "*");
      conf.set(String.format("hadoop.proxyuser.%s.groups", processUser), "*");
    }

    // Start the MiniDfs cluster
    dfsCluster = new MiniDFSCluster.Builder(conf)
        .numDataNodes(3)
        .format(true)
        .build();

    final Properties props = cloneDefaultTestConfigProperties();
    props.setProperty(ExecConstants.IMPERSONATION_ENABLED, Boolean.toString(isImpersonationEnabled));

    updateTestCluster(1, DrillConfig.create(props));
  }

  protected static void createAndAddWorkspace(FileSystem fs, String name, String path, short permissions, String owner,
      String group,
      Map<String, WorkspaceConfig> workspaces) throws Exception {
    final Path dirPath = new Path(path);
    FileSystem.mkdirs(fs, dirPath, new FsPermission(permissions));
    fs.setOwner(dirPath, owner, group);
    final WorkspaceConfig ws = new WorkspaceConfig(path, true, "parquet");
    workspaces.put(name, ws);
  }

  protected static void stopMiniDfsCluster() throws Exception {
    if (dfsCluster != null) {
      dfsCluster.shutdown();
      dfsCluster = null;
    }

    if (miniDfsStoragePath != null) {
      FileUtils.deleteQuietly(new File(miniDfsStoragePath));
    }
  }
}


File: exec/java-exec/src/test/java/org/apache/drill/exec/impersonation/TestImpersonationDisabledWithMiniDFS.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.impersonation;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.drill.exec.store.dfs.FileSystemConfig;
import org.apache.drill.exec.store.dfs.WorkspaceConfig;
import org.apache.hadoop.fs.FileSystem;
import org.junit.AfterClass;
import org.junit.BeforeClass;
import org.junit.Test;

import java.util.Map;

public class TestImpersonationDisabledWithMiniDFS extends BaseTestImpersonation {
  private static final String MINIDFS_STORAGE_PLUGIN_NAME =
      "minidfs" + TestImpersonationDisabledWithMiniDFS.class.getSimpleName();

  @BeforeClass
  public static void addMiniDfsBasedStorage() throws Exception {
    startMiniDfsCluster(TestImpersonationDisabledWithMiniDFS.class.getSimpleName(), false);

    // Create a HDFS based storage plugin based on local storage plugin and add it to plugin registry (connection string
    // for mini dfs is varies for each run).
    final StoragePluginRegistry pluginRegistry = getDrillbitContext().getStorage();
    final FileSystemConfig lfsPluginConfig = (FileSystemConfig) pluginRegistry.getPlugin("dfs_test").getConfig();

    final FileSystemConfig miniDfsPluginConfig = new FileSystemConfig();
    miniDfsPluginConfig.connection = conf.get(FileSystem.FS_DEFAULT_NAME_KEY);

    Map<String, WorkspaceConfig> workspaces = Maps.newHashMap(lfsPluginConfig.workspaces);
    createAndAddWorkspace(dfsCluster.getFileSystem(), "dfstemp", "/tmp", (short)0777, processUser, processUser, workspaces);

    miniDfsPluginConfig.workspaces = workspaces;
    miniDfsPluginConfig.formats = ImmutableMap.copyOf(lfsPluginConfig.formats);
    miniDfsPluginConfig.setEnabled(true);

    pluginRegistry.createOrUpdate(MINIDFS_STORAGE_PLUGIN_NAME, miniDfsPluginConfig, true);

    // Create test table in minidfs.tmp schema for use in test queries
    test(String.format("CREATE TABLE %s.dfstemp.dfsRegion AS SELECT * FROM cp.`region.json`", MINIDFS_STORAGE_PLUGIN_NAME));
  }

  @Test // DRILL-3037
  public void testSimpleQuery() throws Exception {
    final String query =
        String.format("SELECT sales_city, sales_country FROM dfstemp.dfsRegion ORDER BY region_id DESC LIMIT 2");

    testBuilder()
        .optionSettingQueriesForTestQuery(String.format("USE %s", MINIDFS_STORAGE_PLUGIN_NAME))
        .sqlQuery(query)
        .unOrdered()
        .baselineColumns("sales_city", "sales_country")
        .baselineValues("Santa Fe", "Mexico")
        .baselineValues("Santa Anita", "Mexico")
        .go();
  }

  @AfterClass
  public static void removeMiniDfsBasedStorage() throws Exception {
    getDrillbitContext().getStorage().deletePlugin(MINIDFS_STORAGE_PLUGIN_NAME);
    stopMiniDfsCluster();
  }
}


File: exec/java-exec/src/test/java/org/apache/drill/exec/impersonation/TestImpersonationMetadata.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.impersonation;

import com.google.common.base.Joiner;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.exceptions.UserRemoteException;
import org.apache.drill.exec.rpc.RpcException;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.drill.exec.store.dfs.FileSystemConfig;
import org.apache.drill.exec.store.dfs.WorkspaceConfig;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.fs.permission.FsPermission;
import org.apache.hadoop.security.UserGroupInformation;
import org.junit.AfterClass;
import org.junit.BeforeClass;
import org.junit.Test;

import java.util.Map;

import static org.hamcrest.core.StringContains.containsString;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertThat;

/**
 * Tests impersonation on metadata related queries as SHOW FILES, SHOW TABLES, CREATE VIEW and CREATE TABLE
 */
public class TestImpersonationMetadata extends BaseTestImpersonation {
  private static final String MINIDFS_STORAGE_PLUGIN_NAME = "minidfs" + TestImpersonationMetadata.class.getSimpleName();

  private static final String user1 = "drillTestUser1";
  private static final String user2 = "drillTestUser2";

  private static final String group0 = "drillTestGrp0";
  private static final String group1 = "drillTestGrp1";

  static {
    UserGroupInformation.createUserForTesting(user1, new String[]{ group1, group0 });
    UserGroupInformation.createUserForTesting(user2, new String[]{ group1 });
  }

  @BeforeClass
  public static void addMiniDfsBasedStorage() throws Exception {
    startMiniDfsCluster(TestImpersonationMetadata.class.getSimpleName());

    final StoragePluginRegistry pluginRegistry = getDrillbitContext().getStorage();
    final FileSystemConfig lfsPluginConfig = (FileSystemConfig) pluginRegistry.getPlugin("dfs").getConfig();

    final FileSystemConfig miniDfsPluginConfig = new FileSystemConfig();
    miniDfsPluginConfig.connection = conf.get(FileSystem.FS_DEFAULT_NAME_KEY);

    Map<String, WorkspaceConfig> workspaces = Maps.newHashMap(lfsPluginConfig.workspaces);

    createTestWorkspaces(workspaces);

    miniDfsPluginConfig.workspaces = workspaces;
    miniDfsPluginConfig.formats = ImmutableMap.copyOf(lfsPluginConfig.formats);
    miniDfsPluginConfig.setEnabled(true);

    pluginRegistry.createOrUpdate(MINIDFS_STORAGE_PLUGIN_NAME, miniDfsPluginConfig, true);
  }

  private static void createTestWorkspaces(Map<String, WorkspaceConfig> workspaces) throws Exception {
    // Create "/tmp" folder and set permissions to "777"
    final FileSystem fs = dfsCluster.getFileSystem();
    final Path tmpPath = new Path("/tmp");
    fs.delete(tmpPath, true);
    FileSystem.mkdirs(fs, tmpPath, new FsPermission((short)0777));

    // Create /drillTestGrp0_700 directory with permissions 700 (owned by user running the tests)
    createAndAddWorkspace(fs, "drillTestGrp0_700", "/drillTestGrp0_700", (short)0700, processUser, group0, workspaces);

    // Create /drillTestGrp0_750 directory with permissions 750 (owned by user running the tests)
    createAndAddWorkspace(fs, "drillTestGrp0_750", "/drillTestGrp0_750", (short)0750, processUser, group0, workspaces);

    // Create /drillTestGrp0_755 directory with permissions 755 (owned by user running the tests)
    createAndAddWorkspace(fs, "drillTestGrp0_755", "/drillTestGrp0_755", (short)0755, processUser, group0, workspaces);

    // Create /drillTestGrp0_770 directory with permissions 770 (owned by user running the tests)
    createAndAddWorkspace(fs, "drillTestGrp0_770", "/drillTestGrp0_770", (short)0770, processUser, group0, workspaces);

    // Create /drillTestGrp0_777 directory with permissions 777 (owned by user running the tests)
    createAndAddWorkspace(fs, "drillTestGrp0_777", "/drillTestGrp0_777", (short)0777, processUser, group0, workspaces);

    // Create /drillTestGrp1_700 directory with permissions 700 (owned by user1)
    createAndAddWorkspace(fs, "drillTestGrp1_700", "/drillTestGrp1_700", (short)0700, user1, group1, workspaces);
  }

  @Test // DRILL-3037
  public void testImpersonatingProcessUser() throws Exception {
    updateClient(processUser);

    // Process user start the mini dfs, he has read/write permissions by default
    final String viewName = String.format("%s.drillTestGrp0_700.testView", MINIDFS_STORAGE_PLUGIN_NAME);
    try {
      test("CREATE VIEW " + viewName + " AS SELECT * FROM cp.`region.json`");
      test("SELECT * FROM " + viewName + " LIMIT 2");
    } finally {
      test("DROP VIEW " + viewName);
    }
  }

  @Test
  public void testShowFilesInWSWithUserAndGroupPermissionsForQueryUser() throws Exception {
    updateClient(user1);

    // Try show tables in schema "drillTestGrp1_700" which is owned by "user1"
    test(String.format("SHOW FILES IN %s.drillTestGrp1_700", MINIDFS_STORAGE_PLUGIN_NAME));

    // Try show tables in schema "drillTestGrp0_750" which is owned by "processUser" and has group permissions for
    // "user1"
    test(String.format("SHOW FILES IN %s.drillTestGrp0_750", MINIDFS_STORAGE_PLUGIN_NAME));
  }

  @Test
  public void testShowFilesInWSWithOtherPermissionsForQueryUser() throws Exception {
    updateClient(user2);
    // Try show tables in schema "drillTestGrp0_755" which is owned by "processUser" and group0. "user2" is not part
    // of the "group0"
    test(String.format("SHOW FILES IN %s.drillTestGrp0_755", MINIDFS_STORAGE_PLUGIN_NAME));
  }

  @Test
  public void testShowFilesInWSWithNoPermissionsForQueryUser() throws Exception {
    UserRemoteException ex = null;

    updateClient(user2);
    try {
      // Try show tables in schema "drillTestGrp1_700" which is owned by "user1"
      test(String.format("SHOW FILES IN %s.drillTestGrp1_700", MINIDFS_STORAGE_PLUGIN_NAME));
    } catch(UserRemoteException e) {
      ex = e;
    }

    assertNotNull("UserRemoteException is expected", ex);
    assertThat(ex.getMessage(),
        containsString("Permission denied: user=drillTestUser2, " +
        "access=READ_EXECUTE, inode=\"/drillTestGrp1_700\":drillTestUser1:drillTestGrp1:drwx------"));
  }

  @Test
  public void testShowSchemasSanityCheck() throws Exception {
    test("SHOW SCHEMAS");
  }

  @Test
  public void testCreateViewInDirWithUserPermissionsForQueryUser() throws Exception {
    final String viewSchema = MINIDFS_STORAGE_PLUGIN_NAME + ".drillTestGrp1_700"; // Workspace dir owned by "user1"
    testCreateViewTestHelper(user1, viewSchema, "view1");
  }

  @Test
  public void testCreateViewInDirWithGroupPermissionsForQueryUser() throws Exception {
    // Workspace dir owned by "processUser", workspace group is "group0" and "user1" is part of "group0"
    final String viewSchema = MINIDFS_STORAGE_PLUGIN_NAME + ".drillTestGrp0_770";
    testCreateViewTestHelper(user1, viewSchema, "view1");
  }

  @Test
  public void testCreateViewInDirWithOtherPermissionsForQueryUser() throws Exception {
    // Workspace dir owned by "processUser", workspace group is "group0" and "user2" is not part of "group0"
    final String viewSchema = MINIDFS_STORAGE_PLUGIN_NAME + ".drillTestGrp0_777";
    testCreateViewTestHelper(user2, viewSchema, "view1");
  }

  private static void testCreateViewTestHelper(String user, String viewSchema,
      String viewName) throws Exception {
    try {
      updateClient(user);

      test("USE " + viewSchema);

      test("CREATE VIEW " + viewName + " AS SELECT " +
          "c_custkey, c_nationkey FROM cp.`tpch/customer.parquet` ORDER BY c_custkey;");

      testBuilder()
          .sqlQuery("SHOW TABLES")
          .unOrdered()
          .baselineColumns("TABLE_SCHEMA", "TABLE_NAME")
          .baselineValues(viewSchema, viewName)
          .go();

      test("SHOW FILES");

      testBuilder()
          .sqlQuery("SELECT * FROM " + viewName + " LIMIT 1")
          .ordered()
          .baselineColumns("c_custkey", "c_nationkey")
          .baselineValues(1, 15)
          .go();

    } finally {
      test("DROP VIEW " + viewSchema + "." + viewName);
    }
  }

  @Test
  public void testCreateViewInWSWithNoPermissionsForQueryUser() throws Exception {
    // Workspace dir owned by "processUser", workspace group is "group0" and "user2" is not part of "group0"
    final String viewSchema = MINIDFS_STORAGE_PLUGIN_NAME + ".drillTestGrp0_755";
    final String viewName = "view1";

    updateClient(user2);

    test("USE " + viewSchema);

    final String query = "CREATE VIEW " + viewName + " AS SELECT " +
        "c_custkey, c_nationkey FROM cp.`tpch/customer.parquet` ORDER BY c_custkey;";
    final String expErrorMsg = "PERMISSION ERROR: Permission denied: user=drillTestUser2, access=WRITE, " +
        "inode=\"/drillTestGrp0_755\"";
    errorMsgTestHelper(query, expErrorMsg);

    // SHOW TABLES is expected to return no records as view creation fails above.
    testBuilder()
        .sqlQuery("SHOW TABLES")
        .expectsEmptyResultSet()
        .go();

    test("SHOW FILES");
  }

  @Test
  public void testCreateTableInDirWithUserPermissionsForQueryUser() throws Exception {
    final String tableWS = "drillTestGrp1_700"; // Workspace dir owned by "user1"
    testCreateTableTestHelper(user1, tableWS, "table1");
  }

  @Test
  public void testCreateTableInDirWithGroupPermissionsForQueryUser() throws Exception {
    // Workspace dir owned by "processUser", workspace group is "group0" and "user1" is part of "group0"
    final String tableWS = "drillTestGrp0_770";
    testCreateTableTestHelper(user1, tableWS, "table1");
  }

  @Test
  public void testCreateTableInDirWithOtherPermissionsForQueryUser() throws Exception {
    // Workspace dir owned by "processUser", workspace group is "group0" and "user2" is not part of "group0"
    final String tableWS = "drillTestGrp0_777";
    testCreateTableTestHelper(user2, tableWS, "table1");
  }

  private static void testCreateTableTestHelper(String user, String tableWS,
      String tableName) throws Exception {
    try {
      updateClient(user);

      test("USE " + Joiner.on(".").join(MINIDFS_STORAGE_PLUGIN_NAME, tableWS));

      test("CREATE TABLE " + tableName + " AS SELECT " +
          "c_custkey, c_nationkey FROM cp.`tpch/customer.parquet` ORDER BY c_custkey;");

      test("SHOW FILES");

      testBuilder()
          .sqlQuery("SELECT * FROM " + tableName + " LIMIT 1")
          .ordered()
          .baselineColumns("c_custkey", "c_nationkey")
          .baselineValues(1, 15)
          .go();

    } finally {
      // There is no drop table, we need to delete the table directory through FileSystem object
      final FileSystem fs = dfsCluster.getFileSystem();
      final Path tablePath = new Path(Path.SEPARATOR + tableWS + Path.SEPARATOR + tableName);
      if (fs.exists(tablePath)) {
        fs.delete(tablePath, true);
      }
    }
  }

  @Test
  public void testCreateTableInWSWithNoPermissionsForQueryUser() throws Exception {
    // Workspace dir owned by "processUser", workspace group is "group0" and "user2" is not part of "group0"
    final String tableWS = "drillTestGrp0_755";
    final String tableName = "table1";

    UserRemoteException ex = null;

    try {
      updateClient(user2);

      test("USE " + Joiner.on(".").join(MINIDFS_STORAGE_PLUGIN_NAME, tableWS));

      test("CREATE TABLE " + tableName + " AS SELECT " +
          "c_custkey, c_nationkey FROM cp.`tpch/customer.parquet` ORDER BY c_custkey;");
    } catch(UserRemoteException e) {
      ex = e;
    }

    assertNotNull("UserRemoteException is expected", ex);
    assertThat(ex.getMessage(),
        containsString("Permission denied: user=drillTestUser2, access=WRITE, inode=\"/drillTestGrp0_755\""));
  }

  @AfterClass
  public static void removeMiniDfsBasedStorage() throws Exception {
    getDrillbitContext().getStorage().deletePlugin(MINIDFS_STORAGE_PLUGIN_NAME);
    stopMiniDfsCluster();
  }
}


File: exec/java-exec/src/test/java/org/apache/drill/exec/impersonation/TestImpersonationQueries.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.impersonation;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import org.apache.drill.common.exceptions.UserRemoteException;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.dotdrill.DotDrillType;
import org.apache.drill.exec.rpc.RpcException;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.drill.exec.store.dfs.FileSystemConfig;
import org.apache.drill.exec.store.dfs.WorkspaceConfig;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.fs.permission.FsPermission;
import org.apache.hadoop.security.UserGroupInformation;
import org.junit.AfterClass;
import org.junit.BeforeClass;
import org.junit.Test;

import java.util.Map;

import static org.hamcrest.core.StringContains.containsString;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertThat;

/**
 * Test queries involving direct impersonation and multilevel impersonation including join queries where each side is
 * a nested view.
 */
public class TestImpersonationQueries extends BaseTestImpersonation {
  private static final String MINIDFS_STORAGE_PLUGIN_NAME = "minidfs" + TestImpersonationQueries.class.getSimpleName();

  private static final String[] org1Users = { "user0_1", "user1_1", "user2_1", "user3_1", "user4_1", "user5_1" };
  private static final String[] org1Groups = { "group0_1", "group1_1", "group2_1", "group3_1", "group4_1", "group5_1" };
  private static final String[] org2Users = { "user0_2", "user1_2", "user2_2", "user3_2", "user4_2", "user5_2" };
  private static final String[] org2Groups = { "group0_2", "group1_2", "group2_2", "group3_2", "group4_2", "group5_2" };

  static {
    // "user0_1" belongs to "groups0_1". From "user1_1" onwards each user belongs to corresponding group and the group
    // before it, i.e "user1_1" belongs to "group1_1" and "group0_1" and so on.
    UserGroupInformation.createUserForTesting(org1Users[0], new String[] { org1Groups[0] });
    for(int i=1; i<org1Users.length; i++) {
      UserGroupInformation.createUserForTesting(org1Users[i], new String[] { org1Groups[i], org1Groups[i-1] });
    }

    UserGroupInformation.createUserForTesting(org2Users[0], new String[] { org2Groups[0] });
    for(int i=1; i<org2Users.length; i++) {
      UserGroupInformation.createUserForTesting(org2Users[i], new String[] { org2Groups[i], org2Groups[i-1] });
    }
  }

  @BeforeClass
  public static void addMiniDfsBasedStorageAndGenerateTestData() throws Exception {
    startMiniDfsCluster(TestImpersonationQueries.class.getSimpleName());

    final StoragePluginRegistry pluginRegistry = getDrillbitContext().getStorage();
    final FileSystemConfig lfsPluginConfig = (FileSystemConfig) pluginRegistry.getPlugin("dfs").getConfig();

    final FileSystemConfig miniDfsPluginConfig = new FileSystemConfig();
    miniDfsPluginConfig.connection = conf.get(FileSystem.FS_DEFAULT_NAME_KEY);

    Map<String, WorkspaceConfig> workspaces = Maps.newHashMap(lfsPluginConfig.workspaces);

    createTestWorkspaces(workspaces);

    miniDfsPluginConfig.workspaces = workspaces;
    miniDfsPluginConfig.formats = ImmutableMap.copyOf(lfsPluginConfig.formats);
    miniDfsPluginConfig.setEnabled(true);

    pluginRegistry.createOrUpdate(MINIDFS_STORAGE_PLUGIN_NAME, miniDfsPluginConfig, true);

    // Create test tables/views

    // Create copy of "lineitem" table in /user/user0_1 owned by user0_1:group0_1 with permissions 750. Only user0_1
    // has access to data in created "lineitem" table.
    createTestTable(org1Users[0], org1Groups[0], "lineitem");

    // Create copy of "orders" table in /user/user0_2 owned by user0_2:group0_2 with permissions 750. Only user0_2
    // has access to data in created "orders" table.
    createTestTable(org2Users[0], org2Groups[0], "orders");

    createNestedTestViewsOnLineItem();
    createNestedTestViewsOnOrders();
  }

  private static String getUserHome(String user) {
    return "/user/" + user;
  }

  // Return the user workspace for given user.
  private static String getWSSchema(String user) {
    return MINIDFS_STORAGE_PLUGIN_NAME + "." + user;
  }

  private static void createTestWorkspaces(Map<String, WorkspaceConfig> workspaces) throws Exception {
    // Create "/tmp" folder and set permissions to "777"
    final FileSystem fs = dfsCluster.getFileSystem();
    final Path tmpPath = new Path("/tmp");
    fs.delete(tmpPath, true);
    FileSystem.mkdirs(fs, tmpPath, new FsPermission((short)0777));

    // create user directory (ex. "/user/user0_1", with ownership "user0_1:group0_1" and perms 755) for every user.
    for(int i=0; i<org1Users.length; i++) {
      final String user = org1Users[i];
      final String group = org1Groups[i];
      createAndAddWorkspace(fs, user, getUserHome(user), (short)0755, user, group, workspaces);
    }

    // create user directory (ex. "/user/user0_2", with ownership "user0_2:group0_2" and perms 755) for every user.
    for(int i=0; i<org2Users.length; i++) {
      final String user = org2Users[i];
      final String group = org2Groups[i];
      createAndAddWorkspace(fs, user, getUserHome(user), (short)0755, user, group, workspaces);
    }
  }

  private static void createTestTable(String user, String group, String tableName) throws Exception {
    updateClient(user);
    test("USE " + getWSSchema(user));
    test(String.format("CREATE TABLE %s as SELECT * FROM cp.`tpch/%s.parquet`;", tableName, tableName));

    // Change the ownership and permissions manually. Currently there is no option to specify the default permissions
    // and ownership for new tables.
    final Path tablePath = new Path(getUserHome(user), tableName);
    final FileSystem fs = dfsCluster.getFileSystem();

    fs.setOwner(tablePath, user, group);
    fs.setPermission(tablePath, new FsPermission((short)0750));
  }

  private static void createNestedTestViewsOnLineItem() throws Exception {
    // Input table "lineitem"
    // /user/user0_1     lineitem      750    user0_1:group0_1

    // Create a view on top of lineitem table
    // /user/user1_1    u1_lineitem    750    user1_1:group1_1
    createView(org1Users[1], org1Groups[1], (short)0750, "u1_lineitem", getWSSchema(org1Users[0]), "lineitem");

    // Create a view on top of u1_lineitem view
    // /user/user2_1    u2_lineitem    750    user2_1:group2_1
    createView(org1Users[2], org1Groups[2], (short)0750, "u2_lineitem", getWSSchema(org1Users[1]), "u1_lineitem");

    // Create a view on top of u2_lineitem view
    // /user/user2_1    u22_lineitem    750    user2_1:group2_1
    createView(org1Users[2], org1Groups[2], (short)0750, "u22_lineitem", getWSSchema(org1Users[2]), "u2_lineitem");

    // Create a view on top of u22_lineitem view
    // /user/user3_1    u3_lineitem    750    user3_1:group3_1
    createView(org1Users[3], org1Groups[3], (short)0750, "u3_lineitem", getWSSchema(org1Users[2]), "u22_lineitem");

    // Create a view on top of u3_lineitem view
    // /user/user4_1    u4_lineitem    755    user4_1:group4_1
    createView(org1Users[4], org1Groups[4], (short)0755, "u4_lineitem", getWSSchema(org1Users[3]), "u3_lineitem");
  }

  private static void createNestedTestViewsOnOrders() throws Exception {
    // Input table "orders"
    // /user/user0_2     orders      750    user0_2:group0_2

    // Create a view on top of orders table
    // /user/user1_2    u1_orders    750    user1_2:group1_2
    createView(org2Users[1], org2Groups[1], (short)0750, "u1_orders", getWSSchema(org2Users[0]), "orders");

    // Create a view on top of u1_orders view
    // /user/user2_2    u2_orders    750    user2_2:group2_2
    createView(org2Users[2], org2Groups[2], (short)0750, "u2_orders", getWSSchema(org2Users[1]), "u1_orders");

    // Create a view on top of u2_orders view
    // /user/user2_2    u22_orders    750    user2_2:group2_2
    createView(org2Users[2], org2Groups[2], (short)0750, "u22_orders", getWSSchema(org2Users[2]), "u2_orders");

    // Create a view on top of u22_orders view (permissions of this view (755) are different from permissions of the
    // corresponding view in "lineitem" nested views to have a join query of "lineitem" and "orders" nested views
    // without exceeding the maximum number of allowed user hops in chained impersonation.
    // /user/user3_2    u3_orders    750    user3_2:group3_2
    createView(org2Users[3], org2Groups[3], (short)0755, "u3_orders", getWSSchema(org2Users[2]), "u22_orders");

    // Create a view on top of u3_orders view
    // /user/user4_2    u4_orders    755    user4_2:group4_2
    createView(org2Users[4], org2Groups[4], (short)0755, "u4_orders", getWSSchema(org2Users[3]), "u3_orders");
  }

  private static void createView(final String viewOwner, final String viewGroup, final short viewPerms,
      final String newViewName, final String fromSourceSchema, final String fromSourceTableName) throws Exception {
    updateClient(viewOwner);
    test(String.format("ALTER SESSION SET `%s`='%o';", ExecConstants.NEW_VIEW_DEFAULT_PERMS_KEY, viewPerms));
    test(String.format("CREATE VIEW %s.%s AS SELECT * FROM %s.%s;",
        getWSSchema(viewOwner), newViewName, fromSourceSchema, fromSourceTableName));

    // Verify the view file created has the expected permissions and ownership
    Path viewFilePath = new Path(getUserHome(viewOwner), newViewName + DotDrillType.VIEW.getEnding());
    FileStatus status = dfsCluster.getFileSystem().getFileStatus(viewFilePath);
    assertEquals(viewGroup, status.getGroup());
    assertEquals(viewOwner, status.getOwner());
    assertEquals(viewPerms, status.getPermission().toShort());
  }

  @Test
  public void testDirectImpersonation_HasUserReadPermissions() throws Exception {
    // Table lineitem is owned by "user0_1:group0_1" with permissions 750. Try to read the table as "user0_1". We
    // shouldn't expect any errors.
    updateClient(org1Users[0]);
    test(String.format("SELECT * FROM %s.lineitem ORDER BY l_orderkey LIMIT 1", getWSSchema(org1Users[0])));
  }

  @Test
  public void testDirectImpersonation_HasGroupReadPermissions() throws Exception {
    // Table lineitem is owned by "user0_1:group0_1" with permissions 750. Try to read the table as "user1_1". We
    // shouldn't expect any errors as "user1_1" is part of the "group0_1"
    updateClient(org1Users[1]);
    test(String.format("SELECT * FROM %s.lineitem ORDER BY l_orderkey LIMIT 1", getWSSchema(org1Users[0])));
  }

  @Test
  public void testDirectImpersonation_NoReadPermissions() throws Exception {
    UserRemoteException ex = null;
    try {
      // Table lineitem is owned by "user0_1:group0_1" with permissions 750. Now try to read the table as "user2_1". We
      // should expect a permission denied error as "user2_1" is not part of the "group0_1"
      updateClient(org1Users[2]);
      test(String.format("SELECT * FROM %s.lineitem ORDER BY l_orderkey LIMIT 1", getWSSchema(org1Users[0])));
    } catch(UserRemoteException e) {
      ex = e;
    }

    assertNotNull("UserRemoteException is expected", ex);
    assertThat(ex.getMessage(), containsString("PERMISSION ERROR: " +
            "Not authorized to read table [lineitem] in schema [minidfsTestImpersonationQueries.user0_1]"));
  }


  @Test
  public void testMultiLevelImpersonationEqualToMaxUserHops() throws Exception {
    updateClient(org1Users[4]);
    test(String.format("SELECT * from %s.u4_lineitem LIMIT 1;", getWSSchema(org1Users[4])));
  }

  @Test
  public void testMultiLevelImpersonationExceedsMaxUserHops() throws Exception {
    UserRemoteException ex = null;

    try {
      updateClient(org1Users[5]);
      test(String.format("SELECT * from %s.u4_lineitem LIMIT 1;", getWSSchema(org1Users[4])));
    } catch(UserRemoteException e) {
      ex = e;
    }

    assertNotNull("UserRemoteException is expected", ex);
    assertThat(ex.getMessage(),
        containsString("Cannot issue token for view expansion as issuing the token exceeds the maximum allowed number " +
            "of user hops (3) in chained impersonation"));
  }

  @Test
  public void testMultiLevelImpersonationJoinEachSideReachesMaxUserHops() throws Exception {
    updateClient(org1Users[4]);
    test(String.format("SELECT * from %s.u4_lineitem l JOIN %s.u3_orders o ON l.l_orderkey = o.o_orderkey LIMIT 1;",
        getWSSchema(org1Users[4]), getWSSchema(org2Users[3])));
  }

  @Test
  public void testMultiLevelImpersonationJoinOneSideExceedsMaxUserHops() throws Exception {
    UserRemoteException ex = null;

    try {
      updateClient(org1Users[4]);
      test(String.format("SELECT * from %s.u4_lineitem l JOIN %s.u4_orders o ON l.l_orderkey = o.o_orderkey LIMIT 1;",
          getWSSchema(org1Users[4]), getWSSchema(org2Users[4])));
    } catch(UserRemoteException e) {
      ex = e;
    }

    assertNotNull("UserRemoteException is expected", ex);
    assertThat(ex.getMessage(),
        containsString("Cannot issue token for view expansion as issuing the token exceeds the maximum allowed number " +
            "of user hops (3) in chained impersonation"));
  }

  @AfterClass
  public static void removeMiniDfsBasedStorage() throws Exception {
    getDrillbitContext().getStorage().deletePlugin(MINIDFS_STORAGE_PLUGIN_NAME);
    stopMiniDfsCluster();
  }
}
