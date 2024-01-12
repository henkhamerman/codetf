Refactoring Types: ['Move Method', 'Move Attribute']
eratorFactory.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hive.ql.exec;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.ql.exec.vector.VectorAppMasterEventOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorFileSinkOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorFilterOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorGroupByOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorLimitOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorMapJoinOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorReduceSinkOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorSMBMapJoinOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorSelectOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorizationContext;
import org.apache.hadoop.hive.ql.metadata.HiveException;
import org.apache.hadoop.hive.ql.plan.AppMasterEventDesc;
import org.apache.hadoop.hive.ql.plan.CollectDesc;
import org.apache.hadoop.hive.ql.plan.CommonMergeJoinDesc;
import org.apache.hadoop.hive.ql.plan.DemuxDesc;
import org.apache.hadoop.hive.ql.plan.DummyStoreDesc;
import org.apache.hadoop.hive.ql.plan.DynamicPruningEventDesc;
import org.apache.hadoop.hive.ql.plan.ExprNodeDesc;
import org.apache.hadoop.hive.ql.plan.FileSinkDesc;
import org.apache.hadoop.hive.ql.plan.FilterDesc;
import org.apache.hadoop.hive.ql.plan.ForwardDesc;
import org.apache.hadoop.hive.ql.plan.GroupByDesc;
import org.apache.hadoop.hive.ql.plan.HashTableDummyDesc;
import org.apache.hadoop.hive.ql.plan.HashTableSinkDesc;
import org.apache.hadoop.hive.ql.plan.JoinDesc;
import org.apache.hadoop.hive.ql.plan.LateralViewForwardDesc;
import org.apache.hadoop.hive.ql.plan.LateralViewJoinDesc;
import org.apache.hadoop.hive.ql.plan.LimitDesc;
import org.apache.hadoop.hive.ql.plan.ListSinkDesc;
import org.apache.hadoop.hive.ql.plan.MapJoinDesc;
import org.apache.hadoop.hive.ql.plan.MuxDesc;
import org.apache.hadoop.hive.ql.plan.OperatorDesc;
import org.apache.hadoop.hive.ql.plan.OrcFileMergeDesc;
import org.apache.hadoop.hive.ql.plan.PTFDesc;
import org.apache.hadoop.hive.ql.plan.RCFileMergeDesc;
import org.apache.hadoop.hive.ql.plan.ReduceSinkDesc;
import org.apache.hadoop.hive.ql.plan.SMBJoinDesc;
import org.apache.hadoop.hive.ql.plan.ScriptDesc;
import org.apache.hadoop.hive.ql.plan.SelectDesc;
import org.apache.hadoop.hive.ql.plan.SparkHashTableSinkDesc;
import org.apache.hadoop.hive.ql.plan.TableScanDesc;
import org.apache.hadoop.hive.ql.plan.UDTFDesc;
import org.apache.hadoop.hive.ql.plan.UnionDesc;

/**
 * OperatorFactory.
 *
 */
@SuppressWarnings({ "rawtypes", "unchecked" })
public final class OperatorFactory {
  protected static transient final Log LOG = LogFactory.getLog(OperatorFactory.class);
  private static final List<OpTuple> opvec;
  private static final List<OpTuple> vectorOpvec;

  static {
    opvec = new ArrayList<OpTuple>();
    opvec.add(new OpTuple<FilterDesc>(FilterDesc.class, FilterOperator.class));
    opvec.add(new OpTuple<SelectDesc>(SelectDesc.class, SelectOperator.class));
    opvec.add(new OpTuple<ForwardDesc>(ForwardDesc.class, ForwardOperator.class));
    opvec.add(new OpTuple<FileSinkDesc>(FileSinkDesc.class, FileSinkOperator.class));
    opvec.add(new OpTuple<CollectDesc>(CollectDesc.class, CollectOperator.class));
    opvec.add(new OpTuple<ScriptDesc>(ScriptDesc.class, ScriptOperator.class));
    opvec.add(new OpTuple<PTFDesc>(PTFDesc.class, PTFOperator.class));
    opvec.add(new OpTuple<ReduceSinkDesc>(ReduceSinkDesc.class, ReduceSinkOperator.class));
    opvec.add(new OpTuple<GroupByDesc>(GroupByDesc.class, GroupByOperator.class));
    opvec.add(new OpTuple<JoinDesc>(JoinDesc.class, JoinOperator.class));
    opvec.add(new OpTuple<MapJoinDesc>(MapJoinDesc.class, MapJoinOperator.class));
    opvec.add(new OpTuple<SMBJoinDesc>(SMBJoinDesc.class, SMBMapJoinOperator.class));
    opvec.add(new OpTuple<LimitDesc>(LimitDesc.class, LimitOperator.class));
    opvec.add(new OpTuple<TableScanDesc>(TableScanDesc.class, TableScanOperator.class));
    opvec.add(new OpTuple<UnionDesc>(UnionDesc.class, UnionOperator.class));
    opvec.add(new OpTuple<UDTFDesc>(UDTFDesc.class, UDTFOperator.class));
    opvec.add(new OpTuple<LateralViewJoinDesc>(LateralViewJoinDesc.class,
        LateralViewJoinOperator.class));
    opvec.add(new OpTuple<LateralViewForwardDesc>(LateralViewForwardDesc.class,
        LateralViewForwardOperator.class));
    opvec.add(new OpTuple<HashTableDummyDesc>(HashTableDummyDesc.class,
        HashTableDummyOperator.class));
    opvec.add(new OpTuple<HashTableSinkDesc>(HashTableSinkDesc.class,
        HashTableSinkOperator.class));
    opvec.add(new OpTuple<SparkHashTableSinkDesc>(SparkHashTableSinkDesc.class,
        SparkHashTableSinkOperator.class));
    opvec.add(new OpTuple<DummyStoreDesc>(DummyStoreDesc.class,
        DummyStoreOperator.class));
    opvec.add(new OpTuple<DemuxDesc>(DemuxDesc.class,
        DemuxOperator.class));
    opvec.add(new OpTuple<MuxDesc>(MuxDesc.class,
        MuxOperator.class));
    opvec.add(new OpTuple<AppMasterEventDesc>(AppMasterEventDesc.class,
        AppMasterEventOperator.class));
    opvec.add(new OpTuple<DynamicPruningEventDesc>(DynamicPruningEventDesc.class,
        AppMasterEventOperator.class));
    opvec.add(new OpTuple<RCFileMergeDesc>(RCFileMergeDesc.class,
        RCFileMergeOperator.class));
    opvec.add(new OpTuple<OrcFileMergeDesc>(OrcFileMergeDesc.class,
        OrcFileMergeOperator.class));
    opvec.add(new OpTuple<CommonMergeJoinDesc>(CommonMergeJoinDesc.class,
        CommonMergeJoinOperator.class));
    opvec.add(new OpTuple<ListSinkDesc>(ListSinkDesc.class,
        ListSinkOperator.class));
  }

  static {
    vectorOpvec = new ArrayList<OpTuple>();
    vectorOpvec.add(new OpTuple<AppMasterEventDesc>(AppMasterEventDesc.class,
        VectorAppMasterEventOperator.class));
    vectorOpvec.add(new OpTuple<DynamicPruningEventDesc>(DynamicPruningEventDesc.class,
        VectorAppMasterEventOperator.class));
    vectorOpvec.add(new OpTuple<SelectDesc>(SelectDesc.class, VectorSelectOperator.class));
    vectorOpvec.add(new OpTuple<GroupByDesc>(GroupByDesc.class, VectorGroupByOperator.class));
    vectorOpvec.add(new OpTuple<MapJoinDesc>(MapJoinDesc.class, VectorMapJoinOperator.class));
    vectorOpvec.add(new OpTuple<SMBJoinDesc>(SMBJoinDesc.class, VectorSMBMapJoinOperator.class));
    vectorOpvec.add(new OpTuple<ReduceSinkDesc>(ReduceSinkDesc.class,
        VectorReduceSinkOperator.class));
    vectorOpvec.add(new OpTuple<FileSinkDesc>(FileSinkDesc.class, VectorFileSinkOperator.class));
    vectorOpvec.add(new OpTuple<FilterDesc>(FilterDesc.class, VectorFilterOperator.class));
    vectorOpvec.add(new OpTuple<LimitDesc>(LimitDesc.class, VectorLimitOperator.class));
  }

  private static final class OpTuple<T extends OperatorDesc> {
    private final Class<T> descClass;
    private final Class<? extends Operator<?>> opClass;

    public OpTuple(Class<T> descClass, Class<? extends Operator<?>> opClass) {
      this.descClass = descClass;
      this.opClass = opClass;
    }
  }

  public static <T extends OperatorDesc> Operator<T> getVectorOperator(
    Class<? extends Operator<?>> opClass, T conf, VectorizationContext vContext) throws HiveException {
    try {
      Operator<T> op = (Operator<T>) opClass.getDeclaredConstructor(
          VectorizationContext.class, OperatorDesc.class).newInstance(
          vContext, conf);
      return op;
    } catch (Exception e) {
      e.printStackTrace();
      throw new HiveException(e);
    }
  }

  public static <T extends OperatorDesc> Operator<T> getVectorOperator(T conf,
      VectorizationContext vContext) throws HiveException {
    Class<T> descClass = (Class<T>) conf.getClass();
    for (OpTuple o : vectorOpvec) {
      if (o.descClass == descClass) {
        return getVectorOperator(o.opClass, conf, vContext);
      }
    }
    throw new HiveException("No vector operator for descriptor class "
        + descClass.getName());
  }

  public static <T extends OperatorDesc> Operator<T> get(Class<T> opClass) {

    for (OpTuple o : opvec) {
      if (o.descClass == opClass) {
        try {
          Operator<T> op = (Operator<T>) o.opClass.newInstance();
          return op;
        } catch (Exception e) {
          e.printStackTrace();
          throw new RuntimeException(e);
        }
      }
    }
    throw new RuntimeException("No operator for descriptor class "
        + opClass.getName());
  }

  public static <T extends OperatorDesc> Operator<T> get(Class<T> opClass,
      RowSchema rwsch) {

    Operator<T> ret = get(opClass);
    ret.setSchema(rwsch);
    return ret;
  }

  /**
   * Returns an operator given the conf and a list of children operators.
   */
  public static <T extends OperatorDesc> Operator<T> get(T conf,
    Operator<? extends OperatorDesc>... oplist) {
    Operator<T> ret = get((Class<T>) conf.getClass());
    ret.setConf(conf);
    makeChild(ret, oplist);
    return (ret);
  }

  /**
   * Returns an operator given the conf and a list of children operators.
   */
  public static void makeChild(
    Operator<? extends OperatorDesc> ret,
    Operator<? extends OperatorDesc>... oplist) {
    if (oplist.length == 0) {
      return;
    }

    ArrayList<Operator<? extends OperatorDesc>> clist =
      new ArrayList<Operator<? extends OperatorDesc>>();
    for (Operator<? extends OperatorDesc> op : oplist) {
      clist.add(op);
    }
    ret.setChildOperators(clist);

    // Add this parent to the children
    for (Operator<? extends OperatorDesc> op : oplist) {
      List<Operator<? extends OperatorDesc>> parents = op.getParentOperators();
      parents.add(ret);
      op.setParentOperators(parents);
    }
  }

  /**
   * Returns an operator given the conf and a list of children operators.
   */
  public static <T extends OperatorDesc> Operator<T> get(T conf,
      RowSchema rwsch, Operator... oplist) {
    Operator<T> ret = get(conf, oplist);
    ret.setSchema(rwsch);
    return (ret);
  }

  /**
   * Returns an operator given the conf and a list of parent operators.
   */
  public static <T extends OperatorDesc> Operator<T> getAndMakeChild(T conf,
      Operator... oplist) {
    Operator<T> ret = get((Class<T>) conf.getClass());
    ret.setConf(conf);
    if (oplist.length == 0) {
      return (ret);
    }

    // Add the new operator as child of each of the passed in operators
    for (Operator op : oplist) {
      List<Operator> children = op.getChildOperators();
      children.add(ret);
      op.setChildOperators(children);
    }

    // add parents for the newly created operator
    List<Operator<? extends OperatorDesc>> parent =
      new ArrayList<Operator<? extends OperatorDesc>>();
    for (Operator op : oplist) {
      parent.add(op);
    }

    ret.setParentOperators(parent);

    return (ret);
  }

  /**
   * Returns an operator given the conf and a list of parent operators.
   */
  public static <T extends OperatorDesc> Operator<T> getAndMakeChild(T conf,
      List<Operator<? extends OperatorDesc>> oplist) {
    Operator<T> ret = get((Class<T>) conf.getClass());
    ret.setConf(conf);
    if (oplist.size() == 0) {
      return ret;
    }

    // Add the new operator as child of each of the passed in operators
    for (Operator op : oplist) {
      List<Operator> children = op.getChildOperators();
      children.add(ret);
    }

    // add parents for the newly created operator
    List<Operator<? extends OperatorDesc>> parent =
      new ArrayList<Operator<? extends OperatorDesc>>();
    for (Operator op : oplist) {
      parent.add(op);
    }

    ret.setParentOperators(parent);

    return ret;
  }

  /**
   * Returns an operator given the conf and a list of parent operators.
   */
  public static <T extends OperatorDesc> Operator<T> getAndMakeChild(T conf,
      RowSchema rwsch, Operator... oplist) {
    Operator<T> ret = getAndMakeChild(conf, oplist);
    ret.setSchema(rwsch);
    return ret;
  }

  /**
   * Returns an operator given the conf and a list of parent operators.
   */
  public static <T extends OperatorDesc> Operator<T> getAndMakeChild(T conf,
      RowSchema rwsch, Map<String, ExprNodeDesc> colExprMap, Operator... oplist) {
    Operator<T> ret = getAndMakeChild(conf, rwsch, oplist);
    ret.setColumnExprMap(colExprMap);
    return (ret);
  }

  /**
   * Returns an operator given the conf and a list of parent operators.
   */
  public static <T extends OperatorDesc> Operator<T> getAndMakeChild(T conf,
      RowSchema rwsch, List<Operator<? extends OperatorDesc>> oplist) {
    Operator<T> ret = getAndMakeChild(conf, oplist);
    ret.setSchema(rwsch);
    return (ret);
  }

 /**
   * Returns an operator given the conf and a list of parent operators.
   */
  public static <T extends OperatorDesc> Operator<T> getAndMakeChild(T conf,
      RowSchema rwsch, Map<String, ExprNodeDesc> colExprMap, List<Operator<? extends OperatorDesc>> oplist) {
    Operator<T> ret = getAndMakeChild(conf, rwsch, oplist);
    ret.setColumnExprMap(colExprMap);
    return (ret);
  }

  private OperatorFactory() {
    // prevent instantiation
  }
}


File: ql/src/java/org/apache/hadoop/hive/ql/exec/SparkHashTableSinkOperator.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.hadoop.hive.ql.exec;

import java.io.BufferedOutputStream;
import java.io.ObjectOutputStream;
import java.io.OutputStream;
import java.io.Serializable;
import java.util.Collection;
import java.util.Set;
import java.util.concurrent.Future;

import org.apache.commons.io.FileExistsException;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hive.ql.exec.persistence.MapJoinPersistableTableContainer;
import org.apache.hadoop.hive.ql.exec.persistence.MapJoinTableContainerSerDe;
import org.apache.hadoop.hive.ql.log.PerfLogger;
import org.apache.hadoop.hive.ql.metadata.HiveException;
import org.apache.hadoop.hive.ql.plan.BucketMapJoinContext;
import org.apache.hadoop.hive.ql.plan.MapredLocalWork;
import org.apache.hadoop.hive.ql.plan.SparkBucketMapJoinContext;
import org.apache.hadoop.hive.ql.plan.SparkHashTableSinkDesc;
import org.apache.hadoop.hive.ql.plan.api.OperatorType;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspector;

public class SparkHashTableSinkOperator
    extends TerminalOperator<SparkHashTableSinkDesc> implements Serializable {
  private static final int MIN_REPLICATION = 10;
  private static final long serialVersionUID = 1L;
  private final String CLASS_NAME = this.getClass().getName();
  private final PerfLogger perfLogger = PerfLogger.getPerfLogger();
  protected static final Log LOG = LogFactory.getLog(SparkHashTableSinkOperator.class.getName());

  private final HashTableSinkOperator htsOperator;

  // The position of this table
  private byte tag;

  public SparkHashTableSinkOperator() {
    htsOperator = new HashTableSinkOperator();
  }

  @Override
  protected Collection<Future<?>> initializeOp(Configuration hconf) throws HiveException {
    Collection<Future<?>> result = super.initializeOp(hconf);
    ObjectInspector[] inputOIs = new ObjectInspector[conf.getTagLength()];
    inputOIs[tag] = inputObjInspectors[0];
    conf.setTagOrder(new Byte[]{ tag });
    htsOperator.setConf(conf);
    htsOperator.initialize(hconf, inputOIs);
    return result;
  }

  @Override
  public void process(Object row, int tag) throws HiveException {
    // Ignore the tag passed in, which should be 0, not what we want
    htsOperator.process(row, this.tag);
  }

  @Override
  public void closeOp(boolean abort) throws HiveException {
    try {
      MapJoinPersistableTableContainer[] mapJoinTables = htsOperator.mapJoinTables;
      if (mapJoinTables == null || mapJoinTables.length < tag
          || mapJoinTables[tag] == null) {
        LOG.debug("mapJoinTable is null");
      } else if (abort) {
        if (LOG.isDebugEnabled()) {
          LOG.debug("Aborting, skip dumping side-table for tag: " + tag);
        }
      } else {
        String method = PerfLogger.SPARK_FLUSH_HASHTABLE + getName();
        perfLogger.PerfLogBegin(CLASS_NAME, method);
        try {
          flushToFile(mapJoinTables[tag], tag);
        } finally {
          perfLogger.PerfLogEnd(CLASS_NAME, method);
        }
      }
      super.closeOp(abort);
    } catch (HiveException e) {
      throw e;
    } catch (Exception e) {
      throw new HiveException(e);
    }
  }

  protected void flushToFile(MapJoinPersistableTableContainer tableContainer,
      byte tag) throws Exception {
    MapredLocalWork localWork = getExecContext().getLocalWork();
    BucketMapJoinContext mapJoinCtx = localWork.getBucketMapjoinContext();
    Path inputPath = getExecContext().getCurrentInputPath();
    String bigInputPath = null;
    if (inputPath != null && mapJoinCtx != null) {
      Set<String> aliases =
        ((SparkBucketMapJoinContext)mapJoinCtx).getPosToAliasMap().get((int)tag);
      bigInputPath = mapJoinCtx.getMappingBigFile(
        aliases.iterator().next(), inputPath.toString());
    }

    // get tmp file URI
    Path tmpURI = localWork.getTmpHDFSPath();
    LOG.info("Temp URI for side table: " + tmpURI);
    // get current bucket file name
    String fileName = localWork.getBucketFileName(bigInputPath);
    // get the tmp URI path; it will be a hdfs path if not local mode
    String dumpFilePrefix = conf.getDumpFilePrefix();
    Path path = Utilities.generatePath(tmpURI, dumpFilePrefix, tag, fileName);
    FileSystem fs = path.getFileSystem(htsOperator.getConfiguration());
    short replication = fs.getDefaultReplication(path);

    fs.mkdirs(path);  // Create the folder and its parents if not there
    while (true) {
      path = new Path(path, getOperatorId()
        + "-" + Math.abs(Utilities.randGen.nextInt()));
      try {
        // This will guarantee file name uniqueness.
        if (fs.createNewFile(path)) {
          break;
        }
      } catch (FileExistsException e) {
        // No problem, use a new name
      }
    }
    // TODO find out numOfPartitions for the big table
    int numOfPartitions = replication;
    replication = (short) Math.max(MIN_REPLICATION, numOfPartitions);
    htsOperator.console.printInfo(Utilities.now() + "\tDump the side-table for tag: " + tag
      + " with group count: " + tableContainer.size() + " into file: " + path);
    // get the hashtable file and path
    OutputStream os = null;
    ObjectOutputStream out = null;
    try {
      os = fs.create(path, replication);
      out = new ObjectOutputStream(new BufferedOutputStream(os, 4096));
      MapJoinTableContainerSerDe mapJoinTableSerde = htsOperator.mapJoinTableSerdes[tag];
      mapJoinTableSerde.persist(out, tableContainer);
      FileStatus status = fs.getFileStatus(path);
      htsOperator.console.printInfo(Utilities.now() + "\tUploaded 1 File to: " + path
        + " (" + status.getLen() + " bytes)");
    } catch (Exception e) {
      // Failed to dump the side-table, remove the partial file
      try {
        fs.delete(path, false);
      } catch (Exception ex) {
        LOG.warn("Got exception in deleting partial side-table dump for tag: "
          + tag + ", file " + path, ex);
      }
      throw e;
    } finally {
      if (out != null) {
        out.close();
      } else if (os != null) {
        os.close();
      }
    }
    tableContainer.clear();
  }

  public void setTag(byte tag) {
    this.tag = tag;
  }

  /**
   * Implements the getName function for the Node Interface.
   *
   * @return the name of the operator
   */
  @Override
  public String getName() {
    return HashTableSinkOperator.getOperatorName();
  }

  @Override
  public OperatorType getType() {
    return OperatorType.HASHTABLESINK;
  }
}


File: ql/src/java/org/apache/hadoop/hive/ql/optimizer/OperatorComparatorFactory.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 * <p/>
 * http://www.apache.org/licenses/LICENSE-2.0
 * <p/>
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hive.ql.optimizer;

import java.util.List;
import java.util.Map;

import com.google.common.base.Preconditions;
import com.google.common.collect.Maps;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.ql.exec.CollectOperator;
import org.apache.hadoop.hive.ql.exec.CommonMergeJoinOperator;
import org.apache.hadoop.hive.ql.exec.DemuxOperator;
import org.apache.hadoop.hive.ql.exec.FileSinkOperator;
import org.apache.hadoop.hive.ql.exec.FilterOperator;
import org.apache.hadoop.hive.ql.exec.ForwardOperator;
import org.apache.hadoop.hive.ql.exec.GroupByOperator;
import org.apache.hadoop.hive.ql.exec.HashTableSinkOperator;
import org.apache.hadoop.hive.ql.exec.JoinOperator;
import org.apache.hadoop.hive.ql.exec.LateralViewForwardOperator;
import org.apache.hadoop.hive.ql.exec.LateralViewJoinOperator;
import org.apache.hadoop.hive.ql.exec.LimitOperator;
import org.apache.hadoop.hive.ql.exec.ListSinkOperator;
import org.apache.hadoop.hive.ql.exec.MapJoinOperator;
import org.apache.hadoop.hive.ql.exec.MuxOperator;
import org.apache.hadoop.hive.ql.exec.Operator;
import org.apache.hadoop.hive.ql.exec.PTFOperator;
import org.apache.hadoop.hive.ql.exec.ReduceSinkOperator;
import org.apache.hadoop.hive.ql.exec.SMBMapJoinOperator;
import org.apache.hadoop.hive.ql.exec.ScriptOperator;
import org.apache.hadoop.hive.ql.exec.SelectOperator;
import org.apache.hadoop.hive.ql.exec.SparkHashTableSinkOperator;
import org.apache.hadoop.hive.ql.exec.TableScanOperator;
import org.apache.hadoop.hive.ql.exec.TemporaryHashSinkOperator;
import org.apache.hadoop.hive.ql.exec.UDTFOperator;
import org.apache.hadoop.hive.ql.exec.UnionOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorFilterOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorGroupByOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorLimitOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorSelectOperator;
import org.apache.hadoop.hive.ql.plan.ExprNodeDesc;
import org.apache.hadoop.hive.ql.plan.FileSinkDesc;
import org.apache.hadoop.hive.ql.plan.FilterDesc;
import org.apache.hadoop.hive.ql.plan.GroupByDesc;
import org.apache.hadoop.hive.ql.plan.HashTableSinkDesc;
import org.apache.hadoop.hive.ql.plan.JoinDesc;
import org.apache.hadoop.hive.ql.plan.LateralViewJoinDesc;
import org.apache.hadoop.hive.ql.plan.LimitDesc;
import org.apache.hadoop.hive.ql.plan.MapJoinDesc;
import org.apache.hadoop.hive.ql.plan.ReduceSinkDesc;
import org.apache.hadoop.hive.ql.plan.SMBJoinDesc;
import org.apache.hadoop.hive.ql.plan.ScriptDesc;
import org.apache.hadoop.hive.ql.plan.SelectDesc;
import org.apache.hadoop.hive.ql.plan.SparkHashTableSinkDesc;
import org.apache.hadoop.hive.ql.plan.TableScanDesc;
import org.apache.hadoop.hive.ql.plan.UDTFDesc;

public class OperatorComparatorFactory {
  private static final Map<Class<?>, OperatorComparator> comparatorMapping = Maps.newHashMap();
  private static final Log LOG = LogFactory.getLog(OperatorComparatorFactory.class);

  static {
    comparatorMapping.put(TableScanOperator.class, new TableScanOperatorComparator());
    comparatorMapping.put(SelectOperator.class, new SelectOperatorComparator());
    comparatorMapping.put(FilterOperator.class, new FilterOperatorComparator());
    comparatorMapping.put(GroupByOperator.class, new GroupByOperatorComparator());
    comparatorMapping.put(ReduceSinkOperator.class, new ReduceSinkOperatorComparator());
    comparatorMapping.put(FileSinkOperator.class, new FileSinkOperatorComparator());
    comparatorMapping.put(JoinOperator.class, new JoinOperatorComparator());
    comparatorMapping.put(MapJoinOperator.class, new MapJoinOperatorComparator());
    comparatorMapping.put(SMBMapJoinOperator.class, new SMBMapJoinOperatorComparator());
    comparatorMapping.put(LimitOperator.class, new LimitOperatorComparator());
    comparatorMapping.put(SparkHashTableSinkOperator.class, new SparkHashTableSinkOperatorComparator());
    comparatorMapping.put(LateralViewJoinOperator.class, new LateralViewJoinOperatorComparator());
    comparatorMapping.put(VectorGroupByOperator.class, new GroupByOperatorComparator());
    comparatorMapping.put(CommonMergeJoinOperator.class, new MapJoinOperatorComparator());
    comparatorMapping.put(VectorFilterOperator.class, new FilterOperatorComparator());
    comparatorMapping.put(UDTFOperator.class, new UDTFOperatorComparator());
    comparatorMapping.put(VectorSelectOperator.class, new SelectOperatorComparator());
    comparatorMapping.put(VectorLimitOperator.class, new LimitOperatorComparator());
    comparatorMapping.put(ScriptOperator.class, new ScriptOperatorComparator());
    comparatorMapping.put(TemporaryHashSinkOperator.class, new HashTableSinkOperatorComparator());
    // these operators does not have state, so they always equal with the same kind.
    comparatorMapping.put(UnionOperator.class, new AlwaysTrueOperatorComparator());
    comparatorMapping.put(ForwardOperator.class, new AlwaysTrueOperatorComparator());
    comparatorMapping.put(LateralViewForwardOperator.class, new AlwaysTrueOperatorComparator());
    comparatorMapping.put(DemuxOperator.class, new AlwaysTrueOperatorComparator());
    comparatorMapping.put(MuxOperator.class, new AlwaysTrueOperatorComparator());
    comparatorMapping.put(ListSinkOperator.class, new AlwaysTrueOperatorComparator());
    comparatorMapping.put(CollectOperator.class, new AlwaysTrueOperatorComparator());
    // do not support PTFOperator comparing now.
    comparatorMapping.put(PTFOperator.class, AlwaysFalseOperatorComparator.getInstance());
  }

  public static OperatorComparator getOperatorComparator(Class<? extends Operator> operatorClass) {
    OperatorComparator operatorComparator = comparatorMapping.get(operatorClass);
    if (operatorComparator == null) {
      LOG.warn("No OperatorComparator is registered for " + operatorClass.getName() +
          ". Default to always false comparator.");
      return AlwaysFalseOperatorComparator.getInstance();
    }

    return operatorComparator;
  }

  public interface OperatorComparator<T extends Operator<?>> {
    boolean equals(T op1, T op2);
  }

  static class AlwaysTrueOperatorComparator implements OperatorComparator<Operator<?>> {

    @Override
    public boolean equals(Operator<?> op1, Operator<?> op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      return true;
    }
  }

  static class AlwaysFalseOperatorComparator implements OperatorComparator<Operator<?>> {
    // the outer class is responsible for maintaining the comparator singleton
    private AlwaysFalseOperatorComparator() {
    }

    private static final AlwaysFalseOperatorComparator instance =
        new AlwaysFalseOperatorComparator();

    public static AlwaysFalseOperatorComparator getInstance() {
      return instance;
    }

    @Override
    public boolean equals(Operator<?> op1, Operator<?> op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      return false;
    }
  }

  static class TableScanOperatorComparator implements OperatorComparator<TableScanOperator> {

    @Override
    public boolean equals(TableScanOperator op1, TableScanOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      TableScanDesc op1Conf = op1.getConf();
      TableScanDesc op2Conf = op2.getConf();

      if (compareString(op1Conf.getAlias(), op2Conf.getAlias()) &&
        compareExprNodeDesc(op1Conf.getFilterExpr(), op2Conf.getFilterExpr()) &&
        op1Conf.getRowLimit() == op2Conf.getRowLimit() &&
        op1Conf.isGatherStats() == op2Conf.isGatherStats()) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class SelectOperatorComparator implements OperatorComparator<SelectOperator> {

    @Override
    public boolean equals(SelectOperator op1, SelectOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      SelectDesc op1Conf = op1.getConf();
      SelectDesc op2Conf = op2.getConf();

      if (compareString(op1Conf.getColListString(), op2Conf.getColListString()) &&
        compareObject(op1Conf.getOutputColumnNames(), op2Conf.getOutputColumnNames()) &&
        compareString(op1Conf.explainNoCompute(), op2Conf.explainNoCompute())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class FilterOperatorComparator implements OperatorComparator<FilterOperator> {

    @Override
    public boolean equals(FilterOperator op1, FilterOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      FilterDesc op1Conf = op1.getConf();
      FilterDesc op2Conf = op2.getConf();

      if (compareString(op1Conf.getPredicateString(), op2Conf.getPredicateString()) &&
        (op1Conf.getIsSamplingPred() == op2Conf.getIsSamplingPred()) &&
        compareString(op1Conf.getSampleDescExpr(), op2Conf.getSampleDescExpr())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class GroupByOperatorComparator implements OperatorComparator<GroupByOperator> {

    @Override
    public boolean equals(GroupByOperator op1, GroupByOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      GroupByDesc op1Conf = op1.getConf();
      GroupByDesc op2Conf = op2.getConf();

      if (compareString(op1Conf.getModeString(), op2Conf.getModeString()) &&
        compareString(op1Conf.getKeyString(), op2Conf.getKeyString()) &&
        compareObject(op1Conf.getOutputColumnNames(), op2Conf.getOutputColumnNames()) &&
        op1Conf.pruneGroupingSetId() == op2Conf.pruneGroupingSetId() &&
        compareObject(op1Conf.getAggregatorStrings(), op2Conf.getAggregatorStrings()) &&
        op1Conf.getBucketGroup() == op2Conf.getBucketGroup()) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class ReduceSinkOperatorComparator implements OperatorComparator<ReduceSinkOperator> {

    @Override
    public boolean equals(ReduceSinkOperator op1, ReduceSinkOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      ReduceSinkDesc op1Conf = op1.getConf();
      ReduceSinkDesc op2Conf = op2.getConf();

      if (compareExprNodeDescList(op1Conf.getKeyCols(), op2Conf.getKeyCols()) &&
        compareExprNodeDescList(op1Conf.getValueCols(), op2Conf.getValueCols()) &&
        compareExprNodeDescList(op1Conf.getPartitionCols(), op2Conf.getPartitionCols()) &&
        op1Conf.getTag() == op2Conf.getTag() &&
        compareString(op1Conf.getOrder(), op2Conf.getOrder()) &&
        op1Conf.getTopN() == op2Conf.getTopN() &&
        op1Conf.isAutoParallel() == op2Conf.isAutoParallel()) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class FileSinkOperatorComparator implements OperatorComparator<FileSinkOperator> {

    @Override
    public boolean equals(FileSinkOperator op1, FileSinkOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      FileSinkDesc op1Conf = op1.getConf();
      FileSinkDesc op2Conf = op2.getConf();

      if (compareObject(op1Conf.getDirName(), op2Conf.getDirName()) &&
        compareObject(op1Conf.getTableInfo(), op2Conf.getTableInfo()) &&
        op1Conf.getCompressed() == op2Conf.getCompressed() &&
        op1Conf.getDestTableId() == op2Conf.getDestTableId() &&
        op1Conf.isMultiFileSpray() == op2Conf.isMultiFileSpray() &&
        op1Conf.getTotalFiles() == op2Conf.getTotalFiles() &&
        op1Conf.getNumFiles() == op2Conf.getNumFiles() &&
        compareString(op1Conf.getStaticSpec(), op2Conf.getStaticSpec()) &&
        op1Conf.isGatherStats() == op2Conf.isGatherStats() &&
        compareString(op1Conf.getStatsAggPrefix(), op2Conf.getStatsAggPrefix())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class JoinOperatorComparator implements OperatorComparator<JoinOperator> {

    @Override
    public boolean equals(JoinOperator op1, JoinOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      JoinDesc desc1 = op1.getConf();
      JoinDesc desc2 = op2.getConf();

      if (compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        compareObject(desc1.getFiltersStringMap(), desc2.getFiltersStringMap()) &&
        compareObject(desc1.getOutputColumnNames(), desc2.getOutputColumnNames()) &&
        compareObject(desc1.getCondsList(), desc2.getCondsList()) &&
        desc1.getHandleSkewJoin() == desc2.getHandleSkewJoin() &&
        compareString(desc1.getNullSafeString(), desc2.getNullSafeString())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class MapJoinOperatorComparator implements OperatorComparator<MapJoinOperator> {

    @Override
    public boolean equals(MapJoinOperator op1, MapJoinOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      MapJoinDesc desc1 = op1.getConf();
      MapJoinDesc desc2 = op2.getConf();

      if (compareObject(desc1.getParentToInput(), desc2.getParentToInput()) &&
        compareString(desc1.getKeyCountsExplainDesc(), desc2.getKeyCountsExplainDesc()) &&
        compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        desc1.getPosBigTable() == desc2.getPosBigTable() &&
        desc1.isBucketMapJoin() == desc2.isBucketMapJoin() &&
        compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        compareObject(desc1.getFiltersStringMap(), desc2.getFiltersStringMap()) &&
        compareObject(desc1.getOutputColumnNames(), desc2.getOutputColumnNames()) &&
        compareObject(desc1.getCondsList(), desc2.getCondsList()) &&
        desc1.getHandleSkewJoin() == desc2.getHandleSkewJoin() &&
        compareString(desc1.getNullSafeString(), desc2.getNullSafeString())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class SMBMapJoinOperatorComparator implements OperatorComparator<SMBMapJoinOperator> {

    @Override
    public boolean equals(SMBMapJoinOperator op1, SMBMapJoinOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      SMBJoinDesc desc1 = op1.getConf();
      SMBJoinDesc desc2 = op2.getConf();

      if (compareObject(desc1.getParentToInput(), desc2.getParentToInput()) &&
        compareString(desc1.getKeyCountsExplainDesc(), desc2.getKeyCountsExplainDesc()) &&
        compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        desc1.getPosBigTable() == desc2.getPosBigTable() &&
        desc1.isBucketMapJoin() == desc2.isBucketMapJoin() &&
        compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        compareObject(desc1.getFiltersStringMap(), desc2.getFiltersStringMap()) &&
        compareObject(desc1.getOutputColumnNames(), desc2.getOutputColumnNames()) &&
        compareObject(desc1.getCondsList(), desc2.getCondsList()) &&
        desc1.getHandleSkewJoin() == desc2.getHandleSkewJoin() &&
        compareString(desc1.getNullSafeString(), desc2.getNullSafeString())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class LimitOperatorComparator implements OperatorComparator<LimitOperator> {

    @Override
    public boolean equals(LimitOperator op1, LimitOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      LimitDesc desc1 = op1.getConf();
      LimitDesc desc2 = op2.getConf();

      return desc1.getLimit() == desc2.getLimit();
    }
  }

  static class SparkHashTableSinkOperatorComparator implements OperatorComparator<SparkHashTableSinkOperator> {

    @Override
    public boolean equals(SparkHashTableSinkOperator op1, SparkHashTableSinkOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      SparkHashTableSinkDesc desc1 = op1.getConf();
      SparkHashTableSinkDesc desc2 = op2.getConf();

      if (compareObject(desc1.getFilterMapString(), desc2.getFilterMapString()) &&
        compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        desc1.getPosBigTable() == desc2.getPosBigTable() &&
        compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        compareObject(desc1.getFiltersStringMap(), desc2.getFiltersStringMap()) &&
        compareObject(desc1.getOutputColumnNames(), desc2.getOutputColumnNames()) &&
        compareObject(desc1.getCondsList(), desc2.getCondsList()) &&
        desc1.getHandleSkewJoin() == desc2.getHandleSkewJoin() &&
        compareString(desc1.getNullSafeString(), desc2.getNullSafeString())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class HashTableSinkOperatorComparator implements OperatorComparator<HashTableSinkOperator> {

    @Override
    public boolean equals(HashTableSinkOperator op1, HashTableSinkOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      HashTableSinkDesc desc1 = op1.getConf();
      HashTableSinkDesc desc2 = op2.getConf();

      if (compareObject(desc1.getFilterMapString(), desc2.getFilterMapString()) &&
        compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        desc1.getPosBigTable() == desc2.getPosBigTable() &&
        compareObject(desc1.getKeysString(), desc2.getKeysString()) &&
        compareObject(desc1.getFiltersStringMap(), desc2.getFiltersStringMap()) &&
        compareObject(desc1.getOutputColumnNames(), desc2.getOutputColumnNames()) &&
        compareObject(desc1.getCondsList(), desc2.getCondsList()) &&
        desc1.getHandleSkewJoin() == desc2.getHandleSkewJoin() &&
        compareString(desc1.getNullSafeString(), desc2.getNullSafeString())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class LateralViewJoinOperatorComparator implements OperatorComparator<LateralViewJoinOperator> {

    @Override
    public boolean equals(LateralViewJoinOperator op1, LateralViewJoinOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      LateralViewJoinDesc desc1 = op1.getConf();
      LateralViewJoinDesc desc2 = op2.getConf();

      return compareObject(desc1.getOutputInternalColNames(), desc2.getOutputInternalColNames());
    }
  }

  static class ScriptOperatorComparator implements OperatorComparator<ScriptOperator> {

    @Override
    public boolean equals(ScriptOperator op1, ScriptOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      ScriptDesc desc1 = op1.getConf();
      ScriptDesc desc2 = op2.getConf();

      if (compareString(desc1.getScriptCmd(), desc2.getScriptCmd()) &&
        compareObject(desc1.getScriptOutputInfo(), desc2.getScriptOutputInfo())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static class UDTFOperatorComparator implements OperatorComparator<UDTFOperator> {

    @Override
    public boolean equals(UDTFOperator op1, UDTFOperator op2) {
      Preconditions.checkNotNull(op1);
      Preconditions.checkNotNull(op2);
      UDTFDesc desc1 = op1.getConf();
      UDTFDesc desc2 = op2.getConf();

      if (compareString(desc1.getUDTFName(), desc2.getUDTFName()) &&
        compareString(desc1.isOuterLateralView(), desc2.isOuterLateralView())) {
        return true;
      } else {
        return false;
      }
    }
  }

  static boolean compareString(String first, String second) {
    return compareObject(first, second);
  }

  /*
   * Compare Objects which implements its own meaningful equals methods.
   */
  static boolean compareObject(Object first, Object second) {
    return first == null ? second == null : first.equals(second);
  }

  static boolean compareExprNodeDesc(ExprNodeDesc first, ExprNodeDesc second) {
    return first == null ? second == null : first.isSame(second);
  }

  static boolean compareExprNodeDescList(List<ExprNodeDesc> first, List<ExprNodeDesc> second) {
    if (first == null && second == null) {
      return true;
    }
    if ((first == null && second != null) || (first != null && second == null)) {
      return false;
    }
    if (first.size() != second.size()) {
      return false;
    } else {
      for (int i = 0; i < first.size(); i++) {
        if (!first.get(i).isSame(second.get(i))) {
          return false;
        }
      }
    }
    return true;
  }
}

File: ql/src/java/org/apache/hadoop/hive/ql/optimizer/physical/GenSparkSkewJoinProcessor.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hive.ql.optimizer.physical;

import com.google.common.base.Preconditions;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.ql.exec.ColumnInfo;
import org.apache.hadoop.hive.ql.exec.ConditionalTask;
import org.apache.hadoop.hive.ql.exec.HashTableDummyOperator;
import org.apache.hadoop.hive.ql.exec.JoinOperator;
import org.apache.hadoop.hive.ql.exec.MapJoinOperator;
import org.apache.hadoop.hive.ql.exec.Operator;
import org.apache.hadoop.hive.ql.exec.OperatorFactory;
import org.apache.hadoop.hive.ql.exec.RowSchema;
import org.apache.hadoop.hive.ql.exec.SparkHashTableSinkOperator;
import org.apache.hadoop.hive.ql.exec.TableScanOperator;
import org.apache.hadoop.hive.ql.exec.Task;
import org.apache.hadoop.hive.ql.exec.TaskFactory;
import org.apache.hadoop.hive.ql.exec.Utilities;
import org.apache.hadoop.hive.ql.exec.spark.SparkTask;
import org.apache.hadoop.hive.ql.io.HiveInputFormat;
import org.apache.hadoop.hive.ql.optimizer.GenMapRedUtils;
import org.apache.hadoop.hive.ql.parse.ParseContext;
import org.apache.hadoop.hive.ql.parse.SemanticException;
import org.apache.hadoop.hive.ql.parse.spark.GenSparkUtils;
import org.apache.hadoop.hive.ql.plan.BaseWork;
import org.apache.hadoop.hive.ql.plan.ConditionalResolverSkewJoin;
import org.apache.hadoop.hive.ql.plan.ConditionalWork;
import org.apache.hadoop.hive.ql.plan.ExprNodeColumnDesc;
import org.apache.hadoop.hive.ql.plan.ExprNodeDesc;
import org.apache.hadoop.hive.ql.plan.HashTableDummyDesc;
import org.apache.hadoop.hive.ql.plan.JoinDesc;
import org.apache.hadoop.hive.ql.plan.MapJoinDesc;
import org.apache.hadoop.hive.ql.plan.MapWork;
import org.apache.hadoop.hive.ql.plan.OperatorDesc;
import org.apache.hadoop.hive.ql.plan.PartitionDesc;
import org.apache.hadoop.hive.ql.plan.PlanUtils;
import org.apache.hadoop.hive.ql.plan.ReduceWork;
import org.apache.hadoop.hive.ql.plan.SparkEdgeProperty;
import org.apache.hadoop.hive.ql.plan.SparkHashTableSinkDesc;
import org.apache.hadoop.hive.ql.plan.SparkWork;
import org.apache.hadoop.hive.ql.plan.TableDesc;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfoFactory;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Copied from GenMRSkewJoinProcessor. It's used for spark task
 *
 */
public class GenSparkSkewJoinProcessor {
  private static final Log LOG = LogFactory.getLog(GenSparkSkewJoinProcessor.class.getName());

  private GenSparkSkewJoinProcessor() {
    // prevent instantiation
  }

  @SuppressWarnings("unchecked")
  public static void processSkewJoin(JoinOperator joinOp, Task<? extends Serializable> currTask,
      ReduceWork reduceWork, ParseContext parseCtx) throws SemanticException {

    SparkWork currentWork = ((SparkTask) currTask).getWork();
    if (currentWork.getChildren(reduceWork).size() > 0) {
      LOG.warn("Skip runtime skew join as the ReduceWork has child work and hasn't been split.");
      return;
    }

    List<Task<? extends Serializable>> children = currTask.getChildTasks();

    Task<? extends Serializable> child =
        children != null && children.size() == 1 ? children.get(0) : null;

    Path baseTmpDir = parseCtx.getContext().getMRTmpPath();

    JoinDesc joinDescriptor = joinOp.getConf();
    Map<Byte, List<ExprNodeDesc>> joinValues = joinDescriptor.getExprs();
    int numAliases = joinValues.size();

    Map<Byte, Path> bigKeysDirMap = new HashMap<Byte, Path>();
    Map<Byte, Map<Byte, Path>> smallKeysDirMap = new HashMap<Byte, Map<Byte, Path>>();
    Map<Byte, Path> skewJoinJobResultsDir = new HashMap<Byte, Path>();
    Byte[] tags = joinDescriptor.getTagOrder();
    // for each joining table, set dir for big key and small keys properly
    for (int i = 0; i < numAliases; i++) {
      Byte alias = tags[i];
      bigKeysDirMap.put(alias, GenMRSkewJoinProcessor.getBigKeysDir(baseTmpDir, alias));
      Map<Byte, Path> smallKeysMap = new HashMap<Byte, Path>();
      smallKeysDirMap.put(alias, smallKeysMap);
      for (Byte src2 : tags) {
        if (!src2.equals(alias)) {
          smallKeysMap.put(src2, GenMRSkewJoinProcessor.getSmallKeysDir(baseTmpDir, alias, src2));
        }
      }
      skewJoinJobResultsDir.put(alias,
          GenMRSkewJoinProcessor.getBigKeysSkewJoinResultDir(baseTmpDir, alias));
    }

    joinDescriptor.setHandleSkewJoin(true);
    joinDescriptor.setBigKeysDirMap(bigKeysDirMap);
    joinDescriptor.setSmallKeysDirMap(smallKeysDirMap);
    joinDescriptor.setSkewKeyDefinition(HiveConf.getIntVar(parseCtx.getConf(),
        HiveConf.ConfVars.HIVESKEWJOINKEY));

    // create proper table/column desc for spilled tables
    TableDesc keyTblDesc = (TableDesc) reduceWork.getKeyDesc().clone();
    List<String> joinKeys = Utilities
        .getColumnNames(keyTblDesc.getProperties());
    List<String> joinKeyTypes = Utilities.getColumnTypes(keyTblDesc
        .getProperties());

    Map<Byte, TableDesc> tableDescList = new HashMap<Byte, TableDesc>();
    Map<Byte, RowSchema> rowSchemaList = new HashMap<Byte, RowSchema>();
    Map<Byte, List<ExprNodeDesc>> newJoinValues = new HashMap<Byte, List<ExprNodeDesc>>();
    Map<Byte, List<ExprNodeDesc>> newJoinKeys = new HashMap<Byte, List<ExprNodeDesc>>();
    // used for create mapJoinDesc, should be in order
    List<TableDesc> newJoinValueTblDesc = new ArrayList<TableDesc>();

    for (int i = 0; i < tags.length; i++) {
      newJoinValueTblDesc.add(null);
    }

    for (int i = 0; i < numAliases; i++) {
      Byte alias = tags[i];
      List<ExprNodeDesc> valueCols = joinValues.get(alias);
      String colNames = "";
      String colTypes = "";
      int columnSize = valueCols.size();
      List<ExprNodeDesc> newValueExpr = new ArrayList<ExprNodeDesc>();
      List<ExprNodeDesc> newKeyExpr = new ArrayList<ExprNodeDesc>();
      ArrayList<ColumnInfo> columnInfos = new ArrayList<ColumnInfo>();

      boolean first = true;
      for (int k = 0; k < columnSize; k++) {
        TypeInfo type = valueCols.get(k).getTypeInfo();
        String newColName = i + "_VALUE_" + k; // any name, it does not matter.
        ColumnInfo columnInfo = new ColumnInfo(newColName, type, alias.toString(), false);
        columnInfos.add(columnInfo);
        newValueExpr.add(new ExprNodeColumnDesc(
            columnInfo.getType(), columnInfo.getInternalName(),
            columnInfo.getTabAlias(), false));
        if (!first) {
          colNames = colNames + ",";
          colTypes = colTypes + ",";
        }
        first = false;
        colNames = colNames + newColName;
        colTypes = colTypes + valueCols.get(k).getTypeString();
      }

      // we are putting join keys at last part of the spilled table
      for (int k = 0; k < joinKeys.size(); k++) {
        if (!first) {
          colNames = colNames + ",";
          colTypes = colTypes + ",";
        }
        first = false;
        colNames = colNames + joinKeys.get(k);
        colTypes = colTypes + joinKeyTypes.get(k);
        ColumnInfo columnInfo = new ColumnInfo(joinKeys.get(k), TypeInfoFactory
            .getPrimitiveTypeInfo(joinKeyTypes.get(k)), alias.toString(), false);
        columnInfos.add(columnInfo);
        newKeyExpr.add(new ExprNodeColumnDesc(
            columnInfo.getType(), columnInfo.getInternalName(),
            columnInfo.getTabAlias(), false));
      }

      newJoinValues.put(alias, newValueExpr);
      newJoinKeys.put(alias, newKeyExpr);
      tableDescList.put(alias, Utilities.getTableDesc(colNames, colTypes));
      rowSchemaList.put(alias, new RowSchema(columnInfos));

      // construct value table Desc
      String valueColNames = "";
      String valueColTypes = "";
      first = true;
      for (int k = 0; k < columnSize; k++) {
        String newColName = i + "_VALUE_" + k; // any name, it does not matter.
        if (!first) {
          valueColNames = valueColNames + ",";
          valueColTypes = valueColTypes + ",";
        }
        valueColNames = valueColNames + newColName;
        valueColTypes = valueColTypes + valueCols.get(k).getTypeString();
        first = false;
      }
      newJoinValueTblDesc.set((byte) i, Utilities.getTableDesc(
          valueColNames, valueColTypes));
    }

    joinDescriptor.setSkewKeysValuesTables(tableDescList);
    joinDescriptor.setKeyTableDesc(keyTblDesc);

    // create N-1 map join tasks
    HashMap<Path, Task<? extends Serializable>> bigKeysDirToTaskMap =
        new HashMap<Path, Task<? extends Serializable>>();
    List<Serializable> listWorks = new ArrayList<Serializable>();
    List<Task<? extends Serializable>> listTasks = new ArrayList<Task<? extends Serializable>>();
    for (int i = 0; i < numAliases - 1; i++) {
      Byte src = tags[i];
      HiveConf hiveConf = new HiveConf(parseCtx.getConf(),
          GenSparkSkewJoinProcessor.class);
      SparkWork sparkWork = new SparkWork(parseCtx.getConf().getVar(HiveConf.ConfVars.HIVEQUERYID));
      Task<? extends Serializable> skewJoinMapJoinTask = TaskFactory.get(sparkWork, hiveConf);
      skewJoinMapJoinTask.setFetchSource(currTask.isFetchSource());

      // create N TableScans
      Operator<? extends OperatorDesc>[] parentOps = new TableScanOperator[tags.length];
      for (int k = 0; k < tags.length; k++) {
        Operator<? extends OperatorDesc> ts =
            GenMapRedUtils.createTemporaryTableScanOperator(rowSchemaList.get((byte) k));
        ((TableScanOperator) ts).setTableDesc(tableDescList.get((byte) k));
        parentOps[k] = ts;
      }

      // create the MapJoinOperator
      String dumpFilePrefix = "mapfile" + PlanUtils.getCountForMapJoinDumpFilePrefix();
      MapJoinDesc mapJoinDescriptor = new MapJoinDesc(newJoinKeys, keyTblDesc,
          newJoinValues, newJoinValueTblDesc, newJoinValueTblDesc, joinDescriptor
          .getOutputColumnNames(), i, joinDescriptor.getConds(),
          joinDescriptor.getFilters(), joinDescriptor.getNoOuterJoin(), dumpFilePrefix);
      mapJoinDescriptor.setTagOrder(tags);
      mapJoinDescriptor.setHandleSkewJoin(false);
      mapJoinDescriptor.setNullSafes(joinDescriptor.getNullSafes());
      // temporarily, mark it as child of all the TS
      MapJoinOperator mapJoinOp = (MapJoinOperator) OperatorFactory
          .getAndMakeChild(mapJoinDescriptor, null, parentOps);

      // clone the original join operator, and replace it with the MJ
      // this makes sure MJ has the same downstream operator plan as the original join
      List<Operator<?>> reducerList = new ArrayList<Operator<?>>();
      reducerList.add(reduceWork.getReducer());
      Operator<? extends OperatorDesc> reducer = Utilities.cloneOperatorTree(
          parseCtx.getConf(), reducerList).get(0);
      Preconditions.checkArgument(reducer instanceof JoinOperator,
          "Reducer should be join operator, but actually is " + reducer.getName());
      JoinOperator cloneJoinOp = (JoinOperator) reducer;
      List<Operator<? extends OperatorDesc>> childOps = cloneJoinOp
          .getChildOperators();
      for (Operator<? extends OperatorDesc> childOp : childOps) {
        childOp.replaceParent(cloneJoinOp, mapJoinOp);
      }
      mapJoinOp.setChildOperators(childOps);

      // set memory usage for the MJ operator
      setMemUsage(mapJoinOp, skewJoinMapJoinTask, parseCtx);

      // create N MapWorks and add them to the SparkWork
      MapWork bigMapWork = null;
      Map<Byte, Path> smallTblDirs = smallKeysDirMap.get(src);
      for (int j = 0; j < tags.length; j++) {
        MapWork mapWork = PlanUtils.getMapRedWork().getMapWork();
        sparkWork.add(mapWork);
        // This code has been only added for testing
        boolean mapperCannotSpanPartns =
            parseCtx.getConf().getBoolVar(
                HiveConf.ConfVars.HIVE_MAPPER_CANNOT_SPAN_MULTIPLE_PARTITIONS);
        mapWork.setMapperCannotSpanPartns(mapperCannotSpanPartns);
        Operator<? extends OperatorDesc> tableScan = parentOps[j];
        String alias = tags[j].toString();
        ArrayList<String> aliases = new ArrayList<String>();
        aliases.add(alias);
        Path path;
        if (j == i) {
          path = bigKeysDirMap.get(tags[j]);
          bigKeysDirToTaskMap.put(path, skewJoinMapJoinTask);
          bigMapWork = mapWork;
        } else {
          path = smallTblDirs.get(tags[j]);
        }
        mapWork.getPathToAliases().put(path.toString(), aliases);
        mapWork.getAliasToWork().put(alias, tableScan);
        PartitionDesc partitionDesc = new PartitionDesc(tableDescList.get(tags[j]), null);
        mapWork.getPathToPartitionInfo().put(path.toString(), partitionDesc);
        mapWork.getAliasToPartnInfo().put(alias, partitionDesc);
        mapWork.setName("Map " + GenSparkUtils.getUtils().getNextSeqNumber());
      }
      // connect all small dir map work to the big dir map work
      Preconditions.checkArgument(bigMapWork != null, "Haven't identified big dir MapWork");
      // these 2 flags are intended only for the big-key map work
      bigMapWork.setNumMapTasks(HiveConf.getIntVar(hiveConf,
          HiveConf.ConfVars.HIVESKEWJOINMAPJOINNUMMAPTASK));
      bigMapWork.setMinSplitSize(HiveConf.getLongVar(hiveConf,
          HiveConf.ConfVars.HIVESKEWJOINMAPJOINMINSPLIT));
      // use HiveInputFormat so that we can control the number of map tasks
      bigMapWork.setInputformat(HiveInputFormat.class.getName());
      for (BaseWork work : sparkWork.getRoots()) {
        Preconditions.checkArgument(work instanceof MapWork,
            "All root work should be MapWork, but got " + work.getClass().getSimpleName());
        if (work != bigMapWork) {
          sparkWork.connect(work, bigMapWork,
              new SparkEdgeProperty(SparkEdgeProperty.SHUFFLE_NONE));
        }
      }

      // insert SparkHashTableSink and Dummy operators
      for (int j = 0; j < tags.length; j++) {
        if (j != i) {
          insertSHTS(tags[j], (TableScanOperator) parentOps[j], bigMapWork);
        }
      }

      listWorks.add(skewJoinMapJoinTask.getWork());
      listTasks.add(skewJoinMapJoinTask);
    }
    if (children != null) {
      for (Task<? extends Serializable> tsk : listTasks) {
        for (Task<? extends Serializable> oldChild : children) {
          tsk.addDependentTask(oldChild);
        }
      }
    }
    if (child != null) {
      currTask.removeDependentTask(child);
      listTasks.add(child);
      listWorks.add(child.getWork());
    }
    ConditionalResolverSkewJoin.ConditionalResolverSkewJoinCtx context =
        new ConditionalResolverSkewJoin.ConditionalResolverSkewJoinCtx(bigKeysDirToTaskMap, child);

    ConditionalWork cndWork = new ConditionalWork(listWorks);
    ConditionalTask cndTsk = (ConditionalTask) TaskFactory.get(cndWork, parseCtx.getConf());
    cndTsk.setListTasks(listTasks);
    cndTsk.setResolver(new ConditionalResolverSkewJoin());
    cndTsk.setResolverCtx(context);
    currTask.setChildTasks(new ArrayList<Task<? extends Serializable>>());
    currTask.addDependentTask(cndTsk);
  }

  /**
   * Insert SparkHashTableSink and HashTableDummy between small dir TS and MJ.
   */
  @SuppressWarnings("unchecked")
  private static void insertSHTS(byte tag, TableScanOperator tableScan, MapWork bigMapWork) {
    Preconditions.checkArgument(tableScan.getChildOperators().size() == 1
        && tableScan.getChildOperators().get(0) instanceof MapJoinOperator);
    HashTableDummyDesc desc = new HashTableDummyDesc();
    HashTableDummyOperator dummyOp = (HashTableDummyOperator) OperatorFactory.get(desc);
    dummyOp.getConf().setTbl(tableScan.getTableDesc());
    MapJoinOperator mapJoinOp = (MapJoinOperator) tableScan.getChildOperators().get(0);
    mapJoinOp.replaceParent(tableScan, dummyOp);
    List<Operator<? extends OperatorDesc>> mapJoinChildren =
        new ArrayList<Operator<? extends OperatorDesc>>();
    mapJoinChildren.add(mapJoinOp);
    dummyOp.setChildOperators(mapJoinChildren);
    bigMapWork.addDummyOp(dummyOp);
    MapJoinDesc mjDesc = mapJoinOp.getConf();
    // mapjoin should not be affected by join reordering
    mjDesc.resetOrder();
    SparkHashTableSinkDesc hashTableSinkDesc = new SparkHashTableSinkDesc(mjDesc);
    SparkHashTableSinkOperator hashTableSinkOp =
        (SparkHashTableSinkOperator) OperatorFactory.get(hashTableSinkDesc);
    int[] valueIndex = mjDesc.getValueIndex(tag);
    if (valueIndex != null) {
      List<ExprNodeDesc> newValues = new ArrayList<ExprNodeDesc>();
      List<ExprNodeDesc> values = hashTableSinkDesc.getExprs().get(tag);
      for (int index = 0; index < values.size(); index++) {
        if (valueIndex[index] < 0) {
          newValues.add(values.get(index));
        }
      }
      hashTableSinkDesc.getExprs().put(tag, newValues);
    }
    tableScan.replaceChild(mapJoinOp, hashTableSinkOp);
    List<Operator<? extends OperatorDesc>> tableScanParents =
        new ArrayList<Operator<? extends OperatorDesc>>();
    tableScanParents.add(tableScan);
    hashTableSinkOp.setParentOperators(tableScanParents);
    hashTableSinkOp.setTag(tag);
  }

  private static void setMemUsage(MapJoinOperator mapJoinOp, Task<? extends Serializable> task,
      ParseContext parseContext) {
    MapJoinResolver.LocalMapJoinProcCtx context =
        new MapJoinResolver.LocalMapJoinProcCtx(task, parseContext);
    try {
      new LocalMapJoinProcFactory.LocalMapJoinProcessor().hasGroupBy(mapJoinOp,
          context);
    } catch (Exception e) {
      LOG.warn("Error setting memory usage.", e);
      return;
    }
    MapJoinDesc mapJoinDesc = mapJoinOp.getConf();
    HiveConf conf = context.getParseCtx().getConf();
    float hashtableMemoryUsage;
    if (context.isFollowedByGroupBy()) {
      hashtableMemoryUsage = conf.getFloatVar(
          HiveConf.ConfVars.HIVEHASHTABLEFOLLOWBYGBYMAXMEMORYUSAGE);
    } else {
      hashtableMemoryUsage = conf.getFloatVar(
          HiveConf.ConfVars.HIVEHASHTABLEMAXMEMORYUSAGE);
    }
    mapJoinDesc.setHashTableMemoryUsage(hashtableMemoryUsage);
  }
}


File: ql/src/java/org/apache/hadoop/hive/ql/optimizer/physical/Vectorizer.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hive.ql.optimizer.physical;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.Stack;
import java.util.regex.Pattern;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.metastore.api.hive_metastoreConstants;
import org.apache.hadoop.hive.ql.exec.*;
import org.apache.hadoop.hive.ql.exec.mr.MapRedTask;
import org.apache.hadoop.hive.ql.exec.persistence.MapJoinKey;
import org.apache.hadoop.hive.ql.exec.spark.SparkTask;
import org.apache.hadoop.hive.ql.exec.tez.TezTask;
import org.apache.hadoop.hive.ql.exec.vector.VectorExpressionDescriptor;
import org.apache.hadoop.hive.ql.exec.vector.VectorGroupByOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinInnerBigOnlyLongOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinInnerBigOnlyMultiKeyOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinInnerBigOnlyStringOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinInnerLongOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinInnerMultiKeyOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinInnerStringOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinLeftSemiLongOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinLeftSemiMultiKeyOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinLeftSemiStringOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinOuterLongOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinOuterMultiKeyOperator;
import org.apache.hadoop.hive.ql.exec.vector.mapjoin.VectorMapJoinOuterStringOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorMapJoinOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorMapJoinOuterFilteredOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorSMBMapJoinOperator;
import org.apache.hadoop.hive.ql.exec.vector.VectorizationContext;
import org.apache.hadoop.hive.ql.exec.vector.VectorizationContextRegion;
import org.apache.hadoop.hive.ql.exec.vector.VectorizedInputFormatInterface;
import org.apache.hadoop.hive.ql.exec.vector.expressions.aggregates.VectorAggregateExpression;
import org.apache.hadoop.hive.ql.lib.DefaultGraphWalker;
import org.apache.hadoop.hive.ql.lib.DefaultRuleDispatcher;
import org.apache.hadoop.hive.ql.lib.Dispatcher;
import org.apache.hadoop.hive.ql.lib.GraphWalker;
import org.apache.hadoop.hive.ql.lib.Node;
import org.apache.hadoop.hive.ql.lib.NodeProcessor;
import org.apache.hadoop.hive.ql.lib.NodeProcessorCtx;
import org.apache.hadoop.hive.ql.lib.PreOrderWalker;
import org.apache.hadoop.hive.ql.lib.Rule;
import org.apache.hadoop.hive.ql.lib.RuleRegExp;
import org.apache.hadoop.hive.ql.lib.TaskGraphWalker;
import org.apache.hadoop.hive.ql.metadata.HiveException;
import org.apache.hadoop.hive.ql.metadata.VirtualColumn;
import org.apache.hadoop.hive.ql.parse.SemanticException;
import org.apache.hadoop.hive.ql.plan.AbstractOperatorDesc;
import org.apache.hadoop.hive.ql.plan.AggregationDesc;
import org.apache.hadoop.hive.ql.plan.BaseWork;
import org.apache.hadoop.hive.ql.plan.ExprNodeColumnDesc;
import org.apache.hadoop.hive.ql.plan.ExprNodeDesc;
import org.apache.hadoop.hive.ql.plan.ExprNodeGenericFuncDesc;
import org.apache.hadoop.hive.ql.plan.GroupByDesc;
import org.apache.hadoop.hive.ql.plan.JoinDesc;
import org.apache.hadoop.hive.ql.plan.MapJoinDesc;
import org.apache.hadoop.hive.ql.plan.MapWork;
import org.apache.hadoop.hive.ql.plan.OperatorDesc;
import org.apache.hadoop.hive.ql.plan.PartitionDesc;
import org.apache.hadoop.hive.ql.plan.ReduceWork;
import org.apache.hadoop.hive.ql.plan.SMBJoinDesc;
import org.apache.hadoop.hive.ql.plan.SparkWork;
import org.apache.hadoop.hive.ql.plan.TableScanDesc;
import org.apache.hadoop.hive.ql.plan.TezWork;
import org.apache.hadoop.hive.ql.plan.VectorGroupByDesc;
import org.apache.hadoop.hive.ql.plan.VectorMapJoinDesc;
import org.apache.hadoop.hive.ql.plan.VectorMapJoinDesc.HashTableImplementationType;
import org.apache.hadoop.hive.ql.plan.VectorMapJoinDesc.HashTableKeyType;
import org.apache.hadoop.hive.ql.plan.VectorMapJoinDesc.HashTableKind;
import org.apache.hadoop.hive.ql.plan.api.OperatorType;
import org.apache.hadoop.hive.ql.udf.UDFAcos;
import org.apache.hadoop.hive.ql.udf.UDFAsin;
import org.apache.hadoop.hive.ql.udf.UDFAtan;
import org.apache.hadoop.hive.ql.udf.UDFBin;
import org.apache.hadoop.hive.ql.udf.UDFConv;
import org.apache.hadoop.hive.ql.udf.UDFCos;
import org.apache.hadoop.hive.ql.udf.UDFDayOfMonth;
import org.apache.hadoop.hive.ql.udf.UDFDegrees;
import org.apache.hadoop.hive.ql.udf.UDFExp;
import org.apache.hadoop.hive.ql.udf.UDFHex;
import org.apache.hadoop.hive.ql.udf.UDFHour;
import org.apache.hadoop.hive.ql.udf.UDFLength;
import org.apache.hadoop.hive.ql.udf.UDFLike;
import org.apache.hadoop.hive.ql.udf.UDFLn;
import org.apache.hadoop.hive.ql.udf.UDFLog;
import org.apache.hadoop.hive.ql.udf.UDFLog10;
import org.apache.hadoop.hive.ql.udf.UDFLog2;
import org.apache.hadoop.hive.ql.udf.UDFMinute;
import org.apache.hadoop.hive.ql.udf.UDFMonth;
import org.apache.hadoop.hive.ql.udf.UDFRadians;
import org.apache.hadoop.hive.ql.udf.UDFRand;
import org.apache.hadoop.hive.ql.udf.UDFSecond;
import org.apache.hadoop.hive.ql.udf.UDFSign;
import org.apache.hadoop.hive.ql.udf.UDFSin;
import org.apache.hadoop.hive.ql.udf.UDFSqrt;
import org.apache.hadoop.hive.ql.udf.UDFSubstr;
import org.apache.hadoop.hive.ql.udf.UDFTan;
import org.apache.hadoop.hive.ql.udf.UDFToBoolean;
import org.apache.hadoop.hive.ql.udf.UDFToByte;
import org.apache.hadoop.hive.ql.udf.UDFToDouble;
import org.apache.hadoop.hive.ql.udf.UDFToFloat;
import org.apache.hadoop.hive.ql.udf.UDFToInteger;
import org.apache.hadoop.hive.ql.udf.UDFToLong;
import org.apache.hadoop.hive.ql.udf.UDFToShort;
import org.apache.hadoop.hive.ql.udf.UDFToString;
import org.apache.hadoop.hive.ql.udf.UDFWeekOfYear;
import org.apache.hadoop.hive.ql.udf.UDFYear;
import org.apache.hadoop.hive.ql.udf.generic.*;
import org.apache.hadoop.hive.serde.serdeConstants;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspector;
import org.apache.hadoop.hive.serde2.objectinspector.StructField;
import org.apache.hadoop.hive.serde2.objectinspector.StructObjectInspector;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfoUtils;

public class Vectorizer implements PhysicalPlanResolver {

  protected static transient final Log LOG = LogFactory.getLog(Vectorizer.class);

  Pattern supportedDataTypesPattern;
  List<Task<? extends Serializable>> vectorizableTasks =
      new ArrayList<Task<? extends Serializable>>();
  Set<Class<?>> supportedGenericUDFs = new HashSet<Class<?>>();

  Set<String> supportedAggregationUdfs = new HashSet<String>();

  private PhysicalContext physicalContext = null;
  private HiveConf hiveConf;

  public Vectorizer() {

    StringBuilder patternBuilder = new StringBuilder();
    patternBuilder.append("int");
    patternBuilder.append("|smallint");
    patternBuilder.append("|tinyint");
    patternBuilder.append("|bigint");
    patternBuilder.append("|integer");
    patternBuilder.append("|long");
    patternBuilder.append("|short");
    patternBuilder.append("|timestamp");
    patternBuilder.append("|" + serdeConstants.INTERVAL_YEAR_MONTH_TYPE_NAME);
    patternBuilder.append("|" + serdeConstants.INTERVAL_DAY_TIME_TYPE_NAME);
    patternBuilder.append("|boolean");
    patternBuilder.append("|binary");
    patternBuilder.append("|string");
    patternBuilder.append("|byte");
    patternBuilder.append("|float");
    patternBuilder.append("|double");
    patternBuilder.append("|date");
    patternBuilder.append("|void");

    // Decimal types can be specified with different precision and scales e.g. decimal(10,5),
    // as opposed to other data types which can be represented by constant strings.
    // The regex matches only the "decimal" prefix of the type.
    patternBuilder.append("|decimal.*");

    // CHAR and VARCHAR types can be specified with maximum length.
    patternBuilder.append("|char.*");
    patternBuilder.append("|varchar.*");

    supportedDataTypesPattern = Pattern.compile(patternBuilder.toString());

    supportedGenericUDFs.add(GenericUDFOPPlus.class);
    supportedGenericUDFs.add(GenericUDFOPMinus.class);
    supportedGenericUDFs.add(GenericUDFOPMultiply.class);
    supportedGenericUDFs.add(GenericUDFOPDivide.class);
    supportedGenericUDFs.add(GenericUDFOPMod.class);
    supportedGenericUDFs.add(GenericUDFOPNegative.class);
    supportedGenericUDFs.add(GenericUDFOPPositive.class);

    supportedGenericUDFs.add(GenericUDFOPEqualOrLessThan.class);
    supportedGenericUDFs.add(GenericUDFOPEqualOrGreaterThan.class);
    supportedGenericUDFs.add(GenericUDFOPGreaterThan.class);
    supportedGenericUDFs.add(GenericUDFOPLessThan.class);
    supportedGenericUDFs.add(GenericUDFOPNot.class);
    supportedGenericUDFs.add(GenericUDFOPNotEqual.class);
    supportedGenericUDFs.add(GenericUDFOPNotNull.class);
    supportedGenericUDFs.add(GenericUDFOPNull.class);
    supportedGenericUDFs.add(GenericUDFOPOr.class);
    supportedGenericUDFs.add(GenericUDFOPAnd.class);
    supportedGenericUDFs.add(GenericUDFOPEqual.class);
    supportedGenericUDFs.add(UDFLength.class);

    supportedGenericUDFs.add(UDFYear.class);
    supportedGenericUDFs.add(UDFMonth.class);
    supportedGenericUDFs.add(UDFDayOfMonth.class);
    supportedGenericUDFs.add(UDFHour.class);
    supportedGenericUDFs.add(UDFMinute.class);
    supportedGenericUDFs.add(UDFSecond.class);
    supportedGenericUDFs.add(UDFWeekOfYear.class);
    supportedGenericUDFs.add(GenericUDFToUnixTimeStamp.class);

    supportedGenericUDFs.add(GenericUDFDateAdd.class);
    supportedGenericUDFs.add(GenericUDFDateSub.class);
    supportedGenericUDFs.add(GenericUDFDate.class);
    supportedGenericUDFs.add(GenericUDFDateDiff.class);

    supportedGenericUDFs.add(UDFLike.class);
    supportedGenericUDFs.add(GenericUDFRegExp.class);
    supportedGenericUDFs.add(UDFSubstr.class);
    supportedGenericUDFs.add(GenericUDFLTrim.class);
    supportedGenericUDFs.add(GenericUDFRTrim.class);
    supportedGenericUDFs.add(GenericUDFTrim.class);

    supportedGenericUDFs.add(UDFSin.class);
    supportedGenericUDFs.add(UDFCos.class);
    supportedGenericUDFs.add(UDFTan.class);
    supportedGenericUDFs.add(UDFAsin.class);
    supportedGenericUDFs.add(UDFAcos.class);
    supportedGenericUDFs.add(UDFAtan.class);
    supportedGenericUDFs.add(UDFDegrees.class);
    supportedGenericUDFs.add(UDFRadians.class);
    supportedGenericUDFs.add(GenericUDFFloor.class);
    supportedGenericUDFs.add(GenericUDFCeil.class);
    supportedGenericUDFs.add(UDFExp.class);
    supportedGenericUDFs.add(UDFLn.class);
    supportedGenericUDFs.add(UDFLog2.class);
    supportedGenericUDFs.add(UDFLog10.class);
    supportedGenericUDFs.add(UDFLog.class);
    supportedGenericUDFs.add(GenericUDFPower.class);
    supportedGenericUDFs.add(GenericUDFRound.class);
    supportedGenericUDFs.add(GenericUDFPosMod.class);
    supportedGenericUDFs.add(UDFSqrt.class);
    supportedGenericUDFs.add(UDFSign.class);
    supportedGenericUDFs.add(UDFRand.class);
    supportedGenericUDFs.add(UDFBin.class);
    supportedGenericUDFs.add(UDFHex.class);
    supportedGenericUDFs.add(UDFConv.class);

    supportedGenericUDFs.add(GenericUDFLower.class);
    supportedGenericUDFs.add(GenericUDFUpper.class);
    supportedGenericUDFs.add(GenericUDFConcat.class);
    supportedGenericUDFs.add(GenericUDFAbs.class);
    supportedGenericUDFs.add(GenericUDFBetween.class);
    supportedGenericUDFs.add(GenericUDFIn.class);
    supportedGenericUDFs.add(GenericUDFCase.class);
    supportedGenericUDFs.add(GenericUDFWhen.class);
    supportedGenericUDFs.add(GenericUDFCoalesce.class);
    supportedGenericUDFs.add(GenericUDFElt.class);
    supportedGenericUDFs.add(GenericUDFInitCap.class);

    // For type casts
    supportedGenericUDFs.add(UDFToLong.class);
    supportedGenericUDFs.add(UDFToInteger.class);
    supportedGenericUDFs.add(UDFToShort.class);
    supportedGenericUDFs.add(UDFToByte.class);
    supportedGenericUDFs.add(UDFToBoolean.class);
    supportedGenericUDFs.add(UDFToFloat.class);
    supportedGenericUDFs.add(UDFToDouble.class);
    supportedGenericUDFs.add(UDFToString.class);
    supportedGenericUDFs.add(GenericUDFTimestamp.class);
    supportedGenericUDFs.add(GenericUDFToDecimal.class);
    supportedGenericUDFs.add(GenericUDFToDate.class);
    supportedGenericUDFs.add(GenericUDFToChar.class);
    supportedGenericUDFs.add(GenericUDFToVarchar.class);
    supportedGenericUDFs.add(GenericUDFToIntervalYearMonth.class);
    supportedGenericUDFs.add(GenericUDFToIntervalDayTime.class);

    // For conditional expressions
    supportedGenericUDFs.add(GenericUDFIf.class);

    supportedAggregationUdfs.add("min");
    supportedAggregationUdfs.add("max");
    supportedAggregationUdfs.add("count");
    supportedAggregationUdfs.add("sum");
    supportedAggregationUdfs.add("avg");
    supportedAggregationUdfs.add("variance");
    supportedAggregationUdfs.add("var_pop");
    supportedAggregationUdfs.add("var_samp");
    supportedAggregationUdfs.add("std");
    supportedAggregationUdfs.add("stddev");
    supportedAggregationUdfs.add("stddev_pop");
    supportedAggregationUdfs.add("stddev_samp");
  }

  class VectorizationDispatcher implements Dispatcher {

    private final PhysicalContext physicalContext;

    private List<String> reduceColumnNames;
    private List<TypeInfo> reduceTypeInfos;

    public VectorizationDispatcher(PhysicalContext physicalContext) {
      this.physicalContext = physicalContext;
      reduceColumnNames = null;
      reduceTypeInfos = null;
    }

    @Override
    public Object dispatch(Node nd, Stack<Node> stack, Object... nodeOutputs)
        throws SemanticException {
      Task<? extends Serializable> currTask = (Task<? extends Serializable>) nd;
      if (currTask instanceof MapRedTask) {
        convertMapWork(((MapRedTask) currTask).getWork().getMapWork(), false);
      } else if (currTask instanceof TezTask) {
        TezWork work = ((TezTask) currTask).getWork();
        for (BaseWork w: work.getAllWork()) {
          if (w instanceof MapWork) {
            convertMapWork((MapWork) w, true);
          } else if (w instanceof ReduceWork) {
            // We are only vectorizing Reduce under Tez.
            if (HiveConf.getBoolVar(hiveConf,
                        HiveConf.ConfVars.HIVE_VECTORIZATION_REDUCE_ENABLED)) {
              convertReduceWork((ReduceWork) w, true);
            }
          }
        }
      } else if (currTask instanceof SparkTask) {
        SparkWork sparkWork = (SparkWork) currTask.getWork();
        for (BaseWork baseWork : sparkWork.getAllWork()) {
          if (baseWork instanceof MapWork) {
            convertMapWork((MapWork) baseWork, false);
          } else if (baseWork instanceof ReduceWork
              && HiveConf.getBoolVar(hiveConf,
                  HiveConf.ConfVars.HIVE_VECTORIZATION_REDUCE_ENABLED)) {
            convertReduceWork((ReduceWork) baseWork, false);
          }
        }
      }
      return null;
    }

    private void convertMapWork(MapWork mapWork, boolean isTez) throws SemanticException {
      boolean ret = validateMapWork(mapWork, isTez);
      if (ret) {
        vectorizeMapWork(mapWork, isTez);
      }
    }

    private void addMapWorkRules(Map<Rule, NodeProcessor> opRules, NodeProcessor np) {
      opRules.put(new RuleRegExp("R1", TableScanOperator.getOperatorName() + ".*"
          + FileSinkOperator.getOperatorName()), np);
      opRules.put(new RuleRegExp("R2", TableScanOperator.getOperatorName() + ".*"
          + ReduceSinkOperator.getOperatorName()), np);
    }

    private boolean validateMapWork(MapWork mapWork, boolean isTez) throws SemanticException {
      LOG.info("Validating MapWork...");

      // Eliminate MR plans with more than one TableScanOperator.
      LinkedHashMap<String, Operator<? extends OperatorDesc>> aliasToWork = mapWork.getAliasToWork();
      if ((aliasToWork == null) || (aliasToWork.size() == 0)) {
        return false;
      }
      int tableScanCount = 0;
      for (Operator<?> op : aliasToWork.values()) {
        if (op == null) {
          LOG.warn("Map work has invalid aliases to work with. Fail validation!");
          return false;
        }
        if (op instanceof TableScanOperator) {
          tableScanCount++;
        }
      }
      if (tableScanCount > 1) {
        LOG.warn("Map work has more than 1 TableScanOperator aliases to work with. Fail validation!");
        return false;
      }

      // Validate the input format
      for (String path : mapWork.getPathToPartitionInfo().keySet()) {
        PartitionDesc pd = mapWork.getPathToPartitionInfo().get(path);
        List<Class<?>> interfaceList =
            Arrays.asList(pd.getInputFileFormatClass().getInterfaces());
        if (!interfaceList.contains(VectorizedInputFormatInterface.class)) {
          LOG.info("Input format: " + pd.getInputFileFormatClassName()
              + ", doesn't provide vectorized input");
          return false;
        }
      }
      Map<Rule, NodeProcessor> opRules = new LinkedHashMap<Rule, NodeProcessor>();
      MapWorkValidationNodeProcessor vnp = new MapWorkValidationNodeProcessor(mapWork, isTez);
      addMapWorkRules(opRules, vnp);
      Dispatcher disp = new DefaultRuleDispatcher(vnp, opRules, null);
      GraphWalker ogw = new DefaultGraphWalker(disp);

      // iterator the mapper operator tree
      ArrayList<Node> topNodes = new ArrayList<Node>();
      topNodes.addAll(mapWork.getAliasToWork().values());
      HashMap<Node, Object> nodeOutput = new HashMap<Node, Object>();
      ogw.startWalking(topNodes, nodeOutput);
      for (Node n : nodeOutput.keySet()) {
        if (nodeOutput.get(n) != null) {
          if (!((Boolean)nodeOutput.get(n)).booleanValue()) {
            return false;
          }
        }
      }
      return true;
    }

    private void vectorizeMapWork(MapWork mapWork, boolean isTez) throws SemanticException {
      LOG.info("Vectorizing MapWork...");
      mapWork.setVectorMode(true);
      Map<Rule, NodeProcessor> opRules = new LinkedHashMap<Rule, NodeProcessor>();
      MapWorkVectorizationNodeProcessor vnp = new MapWorkVectorizationNodeProcessor(mapWork, isTez);
      addMapWorkRules(opRules, vnp);
      Dispatcher disp = new DefaultRuleDispatcher(vnp, opRules, null);
      GraphWalker ogw = new PreOrderWalker(disp);
      // iterator the mapper operator tree
      ArrayList<Node> topNodes = new ArrayList<Node>();
      topNodes.addAll(mapWork.getAliasToWork().values());
      HashMap<Node, Object> nodeOutput = new HashMap<Node, Object>();
      ogw.startWalking(topNodes, nodeOutput);

      mapWork.setVectorColumnNameMap(vnp.getVectorColumnNameMap());
      mapWork.setVectorColumnTypeMap(vnp.getVectorColumnTypeMap());
      mapWork.setVectorScratchColumnTypeMap(vnp.getVectorScratchColumnTypeMap());

      if (LOG.isDebugEnabled()) {
        debugDisplayAllMaps(mapWork);
      }

      return;
    }

    private void convertReduceWork(ReduceWork reduceWork, boolean isTez) throws SemanticException {
      boolean ret = validateReduceWork(reduceWork);
      if (ret) {
        vectorizeReduceWork(reduceWork, isTez);
      }
    }

    private boolean getOnlyStructObjectInspectors(ReduceWork reduceWork) throws SemanticException {
      try {
        // Check key ObjectInspector.
        ObjectInspector keyObjectInspector = reduceWork.getKeyObjectInspector();
        if (keyObjectInspector == null || !(keyObjectInspector instanceof StructObjectInspector)) {
          return false;
        }
        StructObjectInspector keyStructObjectInspector = (StructObjectInspector)keyObjectInspector;
        List<? extends StructField> keyFields = keyStructObjectInspector.getAllStructFieldRefs();

        // Tez doesn't use tagging...
        if (reduceWork.getNeedsTagging()) {
          return false;
        }

        // Check value ObjectInspector.
        ObjectInspector valueObjectInspector = reduceWork.getValueObjectInspector();
        if (valueObjectInspector == null ||
                !(valueObjectInspector instanceof StructObjectInspector)) {
          return false;
        }
        StructObjectInspector valueStructObjectInspector = (StructObjectInspector)valueObjectInspector;
        List<? extends StructField> valueFields = valueStructObjectInspector.getAllStructFieldRefs();

        reduceColumnNames = new ArrayList<String>();
        reduceTypeInfos = new ArrayList<TypeInfo>();

        for (StructField field: keyFields) {
          reduceColumnNames.add(Utilities.ReduceField.KEY.toString() + "." + field.getFieldName());
          reduceTypeInfos.add(TypeInfoUtils.getTypeInfoFromTypeString(field.getFieldObjectInspector().getTypeName()));
        }
        for (StructField field: valueFields) {
          reduceColumnNames.add(Utilities.ReduceField.VALUE.toString() + "." + field.getFieldName());
          reduceTypeInfos.add(TypeInfoUtils.getTypeInfoFromTypeString(field.getFieldObjectInspector().getTypeName()));
        }
      } catch (Exception e) {
        throw new SemanticException(e);
      }
      return true;
    }

    private void addReduceWorkRules(Map<Rule, NodeProcessor> opRules, NodeProcessor np) {
      opRules.put(new RuleRegExp("R1", GroupByOperator.getOperatorName() + ".*"), np);
      opRules.put(new RuleRegExp("R2", SelectOperator.getOperatorName() + ".*"), np);
    }

    private boolean validateReduceWork(ReduceWork reduceWork) throws SemanticException {
      LOG.info("Validating ReduceWork...");

      // Validate input to ReduceWork.
      if (!getOnlyStructObjectInspectors(reduceWork)) {
        return false;
      }
      // Now check the reduce operator tree.
      Map<Rule, NodeProcessor> opRules = new LinkedHashMap<Rule, NodeProcessor>();
      ReduceWorkValidationNodeProcessor vnp = new ReduceWorkValidationNodeProcessor();
      addReduceWorkRules(opRules, vnp);
      Dispatcher disp = new DefaultRuleDispatcher(vnp, opRules, null);
      GraphWalker ogw = new DefaultGraphWalker(disp);
      // iterator the reduce operator tree
      ArrayList<Node> topNodes = new ArrayList<Node>();
      topNodes.add(reduceWork.getReducer());
      HashMap<Node, Object> nodeOutput = new HashMap<Node, Object>();
      ogw.startWalking(topNodes, nodeOutput);
      for (Node n : nodeOutput.keySet()) {
        if (nodeOutput.get(n) != null) {
          if (!((Boolean)nodeOutput.get(n)).booleanValue()) {
            return false;
          }
        }
      }
      return true;
    }

    private void vectorizeReduceWork(ReduceWork reduceWork, boolean isTez) throws SemanticException {
      LOG.info("Vectorizing ReduceWork...");
      reduceWork.setVectorMode(true);

      // For some reason, the DefaultGraphWalker does not descend down from the reducer Operator as
      // expected.  We need to descend down, otherwise it breaks our algorithm that determines
      // VectorizationContext...  Do we use PreOrderWalker instead of DefaultGraphWalker.
      Map<Rule, NodeProcessor> opRules = new LinkedHashMap<Rule, NodeProcessor>();
      ReduceWorkVectorizationNodeProcessor vnp =
              new ReduceWorkVectorizationNodeProcessor(reduceColumnNames, reduceTypeInfos, isTez);
      addReduceWorkRules(opRules, vnp);
      Dispatcher disp = new DefaultRuleDispatcher(vnp, opRules, null);
      GraphWalker ogw = new PreOrderWalker(disp);
      // iterator the reduce operator tree
      ArrayList<Node> topNodes = new ArrayList<Node>();
      topNodes.add(reduceWork.getReducer());
      LOG.info("vectorizeReduceWork reducer Operator: " +
              reduceWork.getReducer().getName() + "...");
      HashMap<Node, Object> nodeOutput = new HashMap<Node, Object>();
      ogw.startWalking(topNodes, nodeOutput);

      // Necessary since we are vectorizing the root operator in reduce.
      reduceWork.setReducer(vnp.getRootVectorOp());

      reduceWork.setVectorColumnNameMap(vnp.getVectorColumnNameMap());
      reduceWork.setVectorColumnTypeMap(vnp.getVectorColumnTypeMap());
      reduceWork.setVectorScratchColumnTypeMap(vnp.getVectorScratchColumnTypeMap());

      if (LOG.isDebugEnabled()) {
        debugDisplayAllMaps(reduceWork);
      }
    }
  }

  class MapWorkValidationNodeProcessor implements NodeProcessor {

    private final MapWork mapWork;
    private final boolean isTez;

    public MapWorkValidationNodeProcessor(MapWork mapWork, boolean isTez) {
      this.mapWork = mapWork;
      this.isTez = isTez;
    }

    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx procCtx,
        Object... nodeOutputs) throws SemanticException {
      for (Node n : stack) {
        Operator<? extends OperatorDesc> op = (Operator<? extends OperatorDesc>) n;
        if (nonVectorizableChildOfGroupBy(op)) {
          return new Boolean(true);
        }
        boolean ret = validateMapWorkOperator(op, mapWork, isTez);
        if (!ret) {
          LOG.info("MapWork Operator: " + op.getName() + " could not be vectorized.");
          return new Boolean(false);
        }
      }
      return new Boolean(true);
    }
  }

  class ReduceWorkValidationNodeProcessor implements NodeProcessor {

    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx procCtx,
        Object... nodeOutputs) throws SemanticException {
      for (Node n : stack) {
        Operator<? extends OperatorDesc> op = (Operator<? extends OperatorDesc>) n;
        if (nonVectorizableChildOfGroupBy(op)) {
          return new Boolean(true);
        }
        boolean ret = validateReduceWorkOperator(op);
        if (!ret) {
          LOG.info("ReduceWork Operator: " + op.getName() + " could not be vectorized.");
          return new Boolean(false);
        }
      }
      return new Boolean(true);
    }
  }

  // This class has common code used by both MapWorkVectorizationNodeProcessor and
  // ReduceWorkVectorizationNodeProcessor.
  class VectorizationNodeProcessor implements NodeProcessor {

    // The vectorization context for the Map or Reduce task.
    protected VectorizationContext taskVectorizationContext;

    // The input projection column type name map for the Map or Reduce task.
    protected Map<Integer, String> taskColumnTypeNameMap;

    VectorizationNodeProcessor() {
      taskColumnTypeNameMap = new HashMap<Integer, String>();
    }

    public Map<String, Integer> getVectorColumnNameMap() {
      return taskVectorizationContext.getProjectionColumnMap();
    }

    public Map<Integer, String> getVectorColumnTypeMap() {
      return taskColumnTypeNameMap;
    }

    public Map<Integer, String> getVectorScratchColumnTypeMap() {
      return taskVectorizationContext.getScratchColumnTypeMap();
    }

    protected final Set<Operator<? extends OperatorDesc>> opsDone =
        new HashSet<Operator<? extends OperatorDesc>>();

    protected final Map<Operator<? extends OperatorDesc>, Operator<? extends OperatorDesc>> opToVectorOpMap =
        new HashMap<Operator<? extends OperatorDesc>, Operator<? extends OperatorDesc>>();

    public VectorizationContext walkStackToFindVectorizationContext(Stack<Node> stack,
            Operator<? extends OperatorDesc> op) throws SemanticException {
      VectorizationContext vContext = null;
      if (stack.size() <= 1) {
        throw new SemanticException(
            String.format("Expected operator stack for operator %s to have at least 2 operators",
                  op.getName()));
      }
      // Walk down the stack of operators until we found one willing to give us a context.
      // At the bottom will be the root operator, guaranteed to have a context
      int i= stack.size()-2;
      while (vContext == null) {
        if (i < 0) {
          return null;
        }
        Operator<? extends OperatorDesc> opParent = (Operator<? extends OperatorDesc>) stack.get(i);
        Operator<? extends OperatorDesc> vectorOpParent = opToVectorOpMap.get(opParent);
        if (vectorOpParent != null) {
          if (vectorOpParent instanceof VectorizationContextRegion) {
            VectorizationContextRegion vcRegion = (VectorizationContextRegion) vectorOpParent;
            vContext = vcRegion.getOuputVectorizationContext();
            LOG.info("walkStackToFindVectorizationContext " + vectorOpParent.getName() + " has new vectorization context " + vContext.toString());
          } else {
            LOG.info("walkStackToFindVectorizationContext " + vectorOpParent.getName() + " does not have new vectorization context");
          }
        } else {
          LOG.info("walkStackToFindVectorizationContext " + opParent.getName() + " is not vectorized");
        }
        --i;
      }
      return vContext;
    }

    public Operator<? extends OperatorDesc> doVectorize(Operator<? extends OperatorDesc> op,
            VectorizationContext vContext, boolean isTez) throws SemanticException {
      Operator<? extends OperatorDesc> vectorOp = op;
      try {
        if (!opsDone.contains(op)) {
          vectorOp = vectorizeOperator(op, vContext, isTez);
          opsDone.add(op);
          if (vectorOp != op) {
            opToVectorOpMap.put(op, vectorOp);
            opsDone.add(vectorOp);
          }
        }
      } catch (HiveException e) {
        throw new SemanticException(e);
      }
      return vectorOp;
    }

    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx procCtx,
        Object... nodeOutputs) throws SemanticException {
      throw new SemanticException("Must be overridden");
    }
  }

  class MapWorkVectorizationNodeProcessor extends VectorizationNodeProcessor {

    private final MapWork mWork;
    private final boolean isTez;

    public MapWorkVectorizationNodeProcessor(MapWork mWork, boolean isTez) {
      super();
      this.mWork = mWork;
      this.isTez = isTez;
    }

    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx procCtx,
        Object... nodeOutputs) throws SemanticException {

      Operator<? extends OperatorDesc> op = (Operator<? extends OperatorDesc>) nd;

      VectorizationContext vContext = null;

      if (op instanceof TableScanOperator) {
        if (taskVectorizationContext == null) {
          taskVectorizationContext = getVectorizationContext(op.getSchema(), op.getName(),
                  taskColumnTypeNameMap);
        }
        vContext = taskVectorizationContext;
      } else {
        LOG.info("MapWorkVectorizationNodeProcessor process going to walk the operator stack to get vectorization context for " + op.getName());
        vContext = walkStackToFindVectorizationContext(stack, op);
        if (vContext == null) {
          // No operator has "pushed" a new context -- so use the task vectorization context.
          vContext = taskVectorizationContext;
        }
      }

      assert vContext != null;
      LOG.info("MapWorkVectorizationNodeProcessor process operator " + op.getName() + " using vectorization context" + vContext.toString());

      // When Vectorized GROUPBY outputs rows instead of vectorized row batchs, we don't
      // vectorize the operators below it.
      if (nonVectorizableChildOfGroupBy(op)) {
        // No need to vectorize
        if (!opsDone.contains(op)) {
            opsDone.add(op);
          }
        return null;
      }

      Operator<? extends OperatorDesc> vectorOp = doVectorize(op, vContext, isTez);

      if (LOG.isDebugEnabled()) {
        if (vectorOp instanceof VectorizationContextRegion) {
          VectorizationContextRegion vcRegion = (VectorizationContextRegion) vectorOp;
          VectorizationContext vNewContext = vcRegion.getOuputVectorizationContext();
          LOG.debug("Vectorized MapWork operator " + vectorOp.getName() + " added vectorization context " + vNewContext.toString());
        }
      }

      return null;
    }
  }

  class ReduceWorkVectorizationNodeProcessor extends VectorizationNodeProcessor {

    private final List<String> reduceColumnNames;
    private final List<TypeInfo> reduceTypeInfos;

    private boolean isTez;

    private Operator<? extends OperatorDesc> rootVectorOp;

    public Operator<? extends OperatorDesc> getRootVectorOp() {
      return rootVectorOp;
    }

    public ReduceWorkVectorizationNodeProcessor(List<String> reduceColumnNames,
            List<TypeInfo> reduceTypeInfos, boolean isTez) {
      super();
      this.reduceColumnNames =  reduceColumnNames;
      this.reduceTypeInfos = reduceTypeInfos;
      rootVectorOp = null;
      this.isTez = isTez;
    }

    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx procCtx,
        Object... nodeOutputs) throws SemanticException {

      Operator<? extends OperatorDesc> op = (Operator<? extends OperatorDesc>) nd;

      VectorizationContext vContext = null;

      boolean saveRootVectorOp = false;

      if (op.getParentOperators().size() == 0) {
        LOG.info("ReduceWorkVectorizationNodeProcessor process reduceColumnNames " + reduceColumnNames.toString());

        vContext = new VectorizationContext("__Reduce_Shuffle__", reduceColumnNames);
        taskVectorizationContext = vContext;
        int i = 0;
        for (TypeInfo typeInfo : reduceTypeInfos) {
          taskColumnTypeNameMap.put(i, typeInfo.getTypeName());
          i++;
        }
        saveRootVectorOp = true;

        if (LOG.isDebugEnabled()) {
          LOG.debug("Vectorized ReduceWork reduce shuffle vectorization context " + vContext.toString());
        }
      } else {
        LOG.info("ReduceWorkVectorizationNodeProcessor process going to walk the operator stack to get vectorization context for " + op.getName());
        vContext = walkStackToFindVectorizationContext(stack, op);
        if (vContext == null) {
          // If we didn't find a context among the operators, assume the top -- reduce shuffle's
          // vectorization context.
          vContext = taskVectorizationContext;
        }
      }

      assert vContext != null;
      LOG.info("ReduceWorkVectorizationNodeProcessor process operator " + op.getName() + " using vectorization context" + vContext.toString());

      // When Vectorized GROUPBY outputs rows instead of vectorized row batchs, we don't
      // vectorize the operators below it.
      if (nonVectorizableChildOfGroupBy(op)) {
        // No need to vectorize
        if (!opsDone.contains(op)) {
          opsDone.add(op);
        }
        return null;
      }

      Operator<? extends OperatorDesc> vectorOp = doVectorize(op, vContext, isTez);

      if (LOG.isDebugEnabled()) {
        if (vectorOp instanceof VectorizationContextRegion) {
          VectorizationContextRegion vcRegion = (VectorizationContextRegion) vectorOp;
          VectorizationContext vNewContext = vcRegion.getOuputVectorizationContext();
          LOG.debug("Vectorized ReduceWork operator " + vectorOp.getName() + " added vectorization context " + vNewContext.toString());
        }
      }
      if (vectorOp instanceof VectorGroupByOperator) {
        VectorGroupByOperator groupBy = (VectorGroupByOperator) vectorOp;
        VectorGroupByDesc vectorDesc = groupBy.getConf().getVectorDesc();
        vectorDesc.setVectorGroupBatches(true);
      }
      if (saveRootVectorOp && op != vectorOp) {
        rootVectorOp = vectorOp;
      }

      return null;
    }
  }

  private static class ValidatorVectorizationContext extends VectorizationContext {
    private ValidatorVectorizationContext() {
      super("No Name");
    }

    @Override
    protected int getInputColumnIndex(String name) {
      return 0;
    }

    @Override
    protected int getInputColumnIndex(ExprNodeColumnDesc colExpr) {
      return 0;
    }
  }

  @Override
  public PhysicalContext resolve(PhysicalContext physicalContext) throws SemanticException {
    this.physicalContext  = physicalContext;
    hiveConf = physicalContext.getConf();

    boolean vectorPath = HiveConf.getBoolVar(hiveConf,
        HiveConf.ConfVars.HIVE_VECTORIZATION_ENABLED);
    if (!vectorPath) {
      LOG.info("Vectorization is disabled");
      return physicalContext;
    }
    // create dispatcher and graph walker
    Dispatcher disp = new VectorizationDispatcher(physicalContext);
    TaskGraphWalker ogw = new TaskGraphWalker(disp);

    // get all the tasks nodes from root task
    ArrayList<Node> topNodes = new ArrayList<Node>();
    topNodes.addAll(physicalContext.getRootTasks());

    // begin to walk through the task tree.
    ogw.startWalking(topNodes, null);
    return physicalContext;
  }

  boolean validateMapWorkOperator(Operator<? extends OperatorDesc> op, MapWork mWork, boolean isTez) {
    boolean ret = false;
    switch (op.getType()) {
      case MAPJOIN:
        if (op instanceof MapJoinOperator) {
          ret = validateMapJoinOperator((MapJoinOperator) op);
        } else if (op instanceof SMBMapJoinOperator) {
          ret = validateSMBMapJoinOperator((SMBMapJoinOperator) op);
        }
        break;
      case GROUPBY:
        ret = validateGroupByOperator((GroupByOperator) op, false, isTez);
        break;
      case FILTER:
        ret = validateFilterOperator((FilterOperator) op);
        break;
      case SELECT:
        ret = validateSelectOperator((SelectOperator) op);
        break;
      case REDUCESINK:
        ret = validateReduceSinkOperator((ReduceSinkOperator) op);
        break;
      case TABLESCAN:
        ret = validateTableScanOperator((TableScanOperator) op, mWork);
        break;
      case FILESINK:
      case LIMIT:
      case EVENT:
        ret = true;
        break;
      default:
        ret = false;
        break;
    }
    return ret;
  }

  boolean validateReduceWorkOperator(Operator<? extends OperatorDesc> op) {
    boolean ret = false;
    switch (op.getType()) {
      case MAPJOIN:
        // Does MAPJOIN actually get planned in Reduce?
        if (op instanceof MapJoinOperator) {
          ret = validateMapJoinOperator((MapJoinOperator) op);
        } else if (op instanceof SMBMapJoinOperator) {
          ret = validateSMBMapJoinOperator((SMBMapJoinOperator) op);
        }
        break;
      case GROUPBY:
        if (HiveConf.getBoolVar(hiveConf,
                    HiveConf.ConfVars.HIVE_VECTORIZATION_REDUCE_GROUPBY_ENABLED)) {
          ret = validateGroupByOperator((GroupByOperator) op, true, true);
        } else {
          ret = false;
        }
        break;
      case FILTER:
        ret = validateFilterOperator((FilterOperator) op);
        break;
      case SELECT:
        ret = validateSelectOperator((SelectOperator) op);
        break;
      case REDUCESINK:
        ret = validateReduceSinkOperator((ReduceSinkOperator) op);
        break;
      case FILESINK:
        ret = validateFileSinkOperator((FileSinkOperator) op);
        break;
      case LIMIT:
      case EVENT:
        ret = true;
        break;
      default:
        ret = false;
        break;
    }
    return ret;
  }

  public Boolean nonVectorizableChildOfGroupBy(Operator<? extends OperatorDesc> op) {
    Operator<? extends OperatorDesc> currentOp = op;
    while (currentOp.getParentOperators().size() > 0) {
      currentOp = currentOp.getParentOperators().get(0);
      if (currentOp.getType().equals(OperatorType.GROUPBY)) {
        GroupByDesc desc = (GroupByDesc)currentOp.getConf();
        boolean isVectorOutput = desc.getVectorDesc().isVectorOutput();
        if (isVectorOutput) {
          // This GROUP BY does vectorize its output.
          return false;
        }
        return true;
      }
    }
    return false;
  }

  private boolean validateSMBMapJoinOperator(SMBMapJoinOperator op) {
    SMBJoinDesc desc = op.getConf();
    // Validation is the same as for map join, since the 'small' tables are not vectorized
    return validateMapJoinDesc(desc);
  }

  private boolean validateTableScanOperator(TableScanOperator op, MapWork mWork) {
    TableScanDesc desc = op.getConf();
    if (desc.isGatherStats()) {
      return false;
    }

    String columns = "";
    String types = "";
    String partitionColumns = "";
    String partitionTypes = "";
    boolean haveInfo = false;

    // This over-reaches slightly, since we can have > 1 table-scan  per map-work.
    // It needs path to partition, path to alias, then check the alias == the same table-scan, to be accurate.
    // That said, that is a TODO item to be fixed when we support >1 TableScans per vectorized pipeline later.
    LinkedHashMap<String, PartitionDesc> partitionDescs = mWork.getPathToPartitionInfo();

    // For vectorization, compare each partition information for against the others.
    // We assume the table information will be from one of the partitions, so it will
    // work to focus on the partition information and not compare against the TableScanOperator
    // columns (in the VectorizationContext)....
    for (Map.Entry<String, PartitionDesc> entry : partitionDescs.entrySet()) {
      PartitionDesc partDesc = entry.getValue();
      if (partDesc.getPartSpec() == null || partDesc.getPartSpec().isEmpty()) {
        // No partition information -- we match because we would default to using the table description.
        continue;
      }
      Properties partProps = partDesc.getProperties();
      if (!haveInfo) {
        columns = partProps.getProperty(hive_metastoreConstants.META_TABLE_COLUMNS);
        types = partProps.getProperty(hive_metastoreConstants.META_TABLE_COLUMN_TYPES);
        partitionColumns = partProps.getProperty(hive_metastoreConstants.META_TABLE_PARTITION_COLUMNS);
        partitionTypes = partProps.getProperty(hive_metastoreConstants.META_TABLE_PARTITION_COLUMN_TYPES);
        haveInfo = true;
      } else {
        String nextColumns = partProps.getProperty(hive_metastoreConstants.META_TABLE_COLUMNS);
        String nextTypes = partProps.getProperty(hive_metastoreConstants.META_TABLE_COLUMN_TYPES);
        String nextPartitionColumns = partProps.getProperty(hive_metastoreConstants.META_TABLE_PARTITION_COLUMNS);
        String nextPartitionTypes = partProps.getProperty(hive_metastoreConstants.META_TABLE_PARTITION_COLUMN_TYPES);
        if (!columns.equalsIgnoreCase(nextColumns)) {
          LOG.info(
                  String.format("Could not vectorize partition %s.  Its column names %s do not match the other column names %s",
                            entry.getKey(), nextColumns, columns));
          return false;
        }
        if (!types.equalsIgnoreCase(nextTypes)) {
          LOG.info(
                  String.format("Could not vectorize partition %s.  Its column types %s do not match the other column types %s",
                              entry.getKey(), nextTypes, types));
          return false;
        }
        if (!partitionColumns.equalsIgnoreCase(nextPartitionColumns)) {
          LOG.info(
                 String.format("Could not vectorize partition %s.  Its partition column names %s do not match the other partition column names %s",
                              entry.getKey(), nextPartitionColumns, partitionColumns));
          return false;
        }
        if (!partitionTypes.equalsIgnoreCase(nextPartitionTypes)) {
          LOG.info(
                 String.format("Could not vectorize partition %s.  Its partition column types %s do not match the other partition column types %s",
                                entry.getKey(), nextPartitionTypes, partitionTypes));
          return false;
        }
      }
    }
    return true;
  }

  private boolean validateMapJoinOperator(MapJoinOperator op) {
    MapJoinDesc desc = op.getConf();
    return validateMapJoinDesc(desc);
  }

  private boolean validateMapJoinDesc(MapJoinDesc desc) {
    byte posBigTable = (byte) desc.getPosBigTable();
    List<ExprNodeDesc> filterExprs = desc.getFilters().get(posBigTable);
    if (!validateExprNodeDesc(filterExprs, VectorExpressionDescriptor.Mode.FILTER)) {
      LOG.info("Cannot vectorize map work filter expression");
      return false;
    }
    List<ExprNodeDesc> keyExprs = desc.getKeys().get(posBigTable);
    if (!validateExprNodeDesc(keyExprs)) {
      LOG.info("Cannot vectorize map work key expression");
      return false;
    }
    List<ExprNodeDesc> valueExprs = desc.getExprs().get(posBigTable);
    if (!validateExprNodeDesc(valueExprs)) {
      LOG.info("Cannot vectorize map work value expression");
      return false;
    }
    return true;
  }

  private boolean validateReduceSinkOperator(ReduceSinkOperator op) {
    List<ExprNodeDesc> keyDescs = op.getConf().getKeyCols();
    List<ExprNodeDesc> partitionDescs = op.getConf().getPartitionCols();
    List<ExprNodeDesc> valueDesc = op.getConf().getValueCols();
    return validateExprNodeDesc(keyDescs) && validateExprNodeDesc(partitionDescs) &&
        validateExprNodeDesc(valueDesc);
  }

  private boolean validateSelectOperator(SelectOperator op) {
    List<ExprNodeDesc> descList = op.getConf().getColList();
    for (ExprNodeDesc desc : descList) {
      boolean ret = validateExprNodeDesc(desc);
      if (!ret) {
        LOG.info("Cannot vectorize select expression: " + desc.toString());
        return false;
      }
    }
    return true;
  }

  private boolean validateFilterOperator(FilterOperator op) {
    ExprNodeDesc desc = op.getConf().getPredicate();
    return validateExprNodeDesc(desc, VectorExpressionDescriptor.Mode.FILTER);
  }

  private boolean validateGroupByOperator(GroupByOperator op, boolean isReduce, boolean isTez) {
    GroupByDesc desc = op.getConf();
    VectorGroupByDesc vectorDesc = desc.getVectorDesc();

    if (desc.isGroupingSetsPresent()) {
      LOG.info("Grouping sets not supported in vector mode");
      return false;
    }
    if (desc.pruneGroupingSetId()) {
      LOG.info("Pruning grouping set id not supported in vector mode");
      return false;
    }
    boolean ret = validateExprNodeDesc(desc.getKeys());
    if (!ret) {
      LOG.info("Cannot vectorize groupby key expression");
      return false;
    }
    ret = validateAggregationDesc(desc.getAggregators(), isReduce);
    if (!ret) {
      LOG.info("Cannot vectorize groupby aggregate expression");
      return false;
    }
    if (isReduce) {
      if (desc.isDistinct()) {
        LOG.info("Distinct not supported in reduce vector mode");
        return false;
      }
      // Sort-based GroupBy?
      if (desc.getMode() != GroupByDesc.Mode.COMPLETE &&
          desc.getMode() != GroupByDesc.Mode.PARTIAL1 &&
          desc.getMode() != GroupByDesc.Mode.PARTIAL2 &&
          desc.getMode() != GroupByDesc.Mode.MERGEPARTIAL) {
        LOG.info("Reduce vector mode not supported when input for GROUP BY not sorted");
        return false;
      }
      LOG.info("Reduce GROUP BY mode is " + desc.getMode().name());
      if (!aggregatorsOutputIsPrimitive(desc.getAggregators(), isReduce)) {
        LOG.info("Reduce vector mode only supported when aggregate outputs are primitive types");
        return false;
      }
      if (desc.getKeys().size() > 0) {
        if (op.getParentOperators().size() > 0) {
          LOG.info("Reduce vector mode can only handle a key group GROUP BY operator when it is fed by reduce-shuffle");
          return false;
        }
        LOG.info("Reduce-side GROUP BY will process key groups");
        vectorDesc.setVectorGroupBatches(true);
      } else {
        LOG.info("Reduce-side GROUP BY will do global aggregation");
      }
      vectorDesc.setVectorOutput(true);
      vectorDesc.setIsReduce(true);
    }
    return true;
  }

  private boolean validateFileSinkOperator(FileSinkOperator op) {
   return true;
  }

  private boolean validateExprNodeDesc(List<ExprNodeDesc> descs) {
    return validateExprNodeDesc(descs, VectorExpressionDescriptor.Mode.PROJECTION);
  }

  private boolean validateExprNodeDesc(List<ExprNodeDesc> descs,
          VectorExpressionDescriptor.Mode mode) {
    for (ExprNodeDesc d : descs) {
      boolean ret = validateExprNodeDesc(d, mode);
      if (!ret) {
        return false;
      }
    }
    return true;
  }

  private boolean validateAggregationDesc(List<AggregationDesc> descs, boolean isReduce) {
    for (AggregationDesc d : descs) {
      boolean ret = validateAggregationDesc(d, isReduce);
      if (!ret) {
        return false;
      }
    }
    return true;
  }

  private boolean validateExprNodeDescRecursive(ExprNodeDesc desc, VectorExpressionDescriptor.Mode mode) {
    if (desc instanceof ExprNodeColumnDesc) {
      ExprNodeColumnDesc c = (ExprNodeColumnDesc) desc;
      // Currently, we do not support vectorized virtual columns (see HIVE-5570).
      if (VirtualColumn.VIRTUAL_COLUMN_NAMES.contains(c.getColumn())) {
        LOG.info("Cannot vectorize virtual column " + c.getColumn());
        return false;
      }
    }
    String typeName = desc.getTypeInfo().getTypeName();
    boolean ret = validateDataType(typeName, mode);
    if (!ret) {
      LOG.info("Cannot vectorize " + desc.toString() + " of type " + typeName);
      return false;
    }
    if (desc instanceof ExprNodeGenericFuncDesc) {
      ExprNodeGenericFuncDesc d = (ExprNodeGenericFuncDesc) desc;
      boolean r = validateGenericUdf(d);
      if (!r) {
        return false;
      }
    }
    if (desc.getChildren() != null) {
      for (ExprNodeDesc d: desc.getChildren()) {
        // Don't restrict child expressions for projection.  Always use looser FILTER mode.
        boolean r = validateExprNodeDescRecursive(d, VectorExpressionDescriptor.Mode.FILTER);
        if (!r) {
          return false;
        }
      }
    }
    return true;
  }

  private boolean validateExprNodeDesc(ExprNodeDesc desc) {
    return validateExprNodeDesc(desc, VectorExpressionDescriptor.Mode.PROJECTION);
  }

  boolean validateExprNodeDesc(ExprNodeDesc desc, VectorExpressionDescriptor.Mode mode) {
    if (!validateExprNodeDescRecursive(desc, mode)) {
      return false;
    }
    try {
      VectorizationContext vc = new ValidatorVectorizationContext();
      if (vc.getVectorExpression(desc, mode) == null) {
        // TODO: this cannot happen - VectorizationContext throws in such cases.
        LOG.info("getVectorExpression returned null");
        return false;
      }
    } catch (Exception e) {
      LOG.info("Failed to vectorize", e);
      return false;
    }
    return true;
  }

  private boolean validateGenericUdf(ExprNodeGenericFuncDesc genericUDFExpr) {
    if (VectorizationContext.isCustomUDF(genericUDFExpr)) {
      return true;
    }
    GenericUDF genericUDF = genericUDFExpr.getGenericUDF();
    if (genericUDF instanceof GenericUDFBridge) {
      Class<? extends UDF> udf = ((GenericUDFBridge) genericUDF).getUdfClass();
      return supportedGenericUDFs.contains(udf);
    } else {
      return supportedGenericUDFs.contains(genericUDF.getClass());
    }
  }

  private boolean validateAggregationDesc(AggregationDesc aggDesc, boolean isReduce) {
    String udfName = aggDesc.getGenericUDAFName().toLowerCase();
    if (!supportedAggregationUdfs.contains(udfName)) {
      LOG.info("Cannot vectorize groupby aggregate expression: UDF " + udfName + " not supported");
      return false;
    }
    if (aggDesc.getParameters() != null && !validateExprNodeDesc(aggDesc.getParameters())) {
      LOG.info("Cannot vectorize groupby aggregate expression: UDF parameters not supported");
      return false;
    }
    // See if we can vectorize the aggregation.
    try {
      VectorizationContext vc = new ValidatorVectorizationContext();
      if (vc.getAggregatorExpression(aggDesc, isReduce) == null) {
        // TODO: this cannot happen - VectorizationContext throws in such cases.
        LOG.info("getAggregatorExpression returned null");
        return false;
      }
    } catch (Exception e) {
      LOG.info("Failed to vectorize", e);
      return false;
    }
    return true;
  }

  private boolean aggregatorsOutputIsPrimitive(List<AggregationDesc> descs, boolean isReduce) {
    for (AggregationDesc d : descs) {
      boolean ret = aggregatorsOutputIsPrimitive(d, isReduce);
      if (!ret) {
        return false;
      }
    }
    return true;
  }

  private boolean aggregatorsOutputIsPrimitive(AggregationDesc aggDesc, boolean isReduce) {
    VectorizationContext vc = new ValidatorVectorizationContext();
    VectorAggregateExpression vectorAggrExpr;
    try {
        vectorAggrExpr = vc.getAggregatorExpression(aggDesc, isReduce);
    } catch (Exception e) {
      // We should have already attempted to vectorize in validateAggregationDesc.
      LOG.info("Vectorization of aggreation should have succeeded ", e);
      return false;
    }

    ObjectInspector outputObjInspector = vectorAggrExpr.getOutputObjectInspector();
    if (outputObjInspector.getCategory() == ObjectInspector.Category.PRIMITIVE) {
      return true;
    }
    return false;
  }

  private boolean validateDataType(String type, VectorExpressionDescriptor.Mode mode) {
    type = type.toLowerCase();
    boolean result = supportedDataTypesPattern.matcher(type).matches();
    if (result && mode == VectorExpressionDescriptor.Mode.PROJECTION && type.equals("void")) {
      return false;
    }
    return result;
  }

  private VectorizationContext getVectorizationContext(RowSchema rowSchema, String contextName,
    Map<Integer, String> typeNameMap) {

    VectorizationContext vContext = new VectorizationContext(contextName);

    // Add all non-virtual columns to make a vectorization context for
    // the TableScan operator.
    int i = 0;
    for (ColumnInfo c : rowSchema.getSignature()) {
      // Earlier, validation code should have eliminated virtual columns usage (HIVE-5560).
      if (!isVirtualColumn(c)) {
        vContext.addInitialColumn(c.getInternalName());
        typeNameMap.put(i, c.getTypeName());
        i++;
      }
    }
    vContext.finishedAddingInitialColumns();

    return vContext;
  }

  private void fixupParentChildOperators(Operator<? extends OperatorDesc> op,
          Operator<? extends OperatorDesc> vectorOp) {
    if (op.getParentOperators() != null) {
      vectorOp.setParentOperators(op.getParentOperators());
      for (Operator<? extends OperatorDesc> p : op.getParentOperators()) {
        p.replaceChild(op, vectorOp);
      }
    }
    if (op.getChildOperators() != null) {
      vectorOp.setChildOperators(op.getChildOperators());
      for (Operator<? extends OperatorDesc> c : op.getChildOperators()) {
        c.replaceParent(op, vectorOp);
      }
    }
  }

  private boolean isBigTableOnlyResults(MapJoinDesc desc) {
    Byte[] order = desc.getTagOrder();
    byte posBigTable = (byte) desc.getPosBigTable();
    Byte posSingleVectorMapJoinSmallTable = (order[0] == posBigTable ? order[1] : order[0]);

    int[] smallTableIndices;
    int smallTableIndicesSize;
    List<ExprNodeDesc> smallTableExprs = desc.getExprs().get(posSingleVectorMapJoinSmallTable);
    if (desc.getValueIndices() != null && desc.getValueIndices().get(posSingleVectorMapJoinSmallTable) != null) {
      smallTableIndices = desc.getValueIndices().get(posSingleVectorMapJoinSmallTable);
      LOG.info("Vectorizer isBigTableOnlyResults smallTableIndices " + Arrays.toString(smallTableIndices));
      smallTableIndicesSize = smallTableIndices.length;
    } else {
      smallTableIndices = null;
      LOG.info("Vectorizer isBigTableOnlyResults smallTableIndices EMPTY");
      smallTableIndicesSize = 0;
    }

    List<Integer> smallTableRetainList = desc.getRetainList().get(posSingleVectorMapJoinSmallTable);
    LOG.info("Vectorizer isBigTableOnlyResults smallTableRetainList " + smallTableRetainList);
    int smallTableRetainSize = smallTableRetainList.size();

    if (smallTableIndicesSize > 0) {
      // Small table indices has priority over retain.
      for (int i = 0; i < smallTableIndicesSize; i++) {
        if (smallTableIndices[i] < 0) {
          // Negative numbers indicate a column to be (deserialize) read from the small table's
          // LazyBinary value row.
          LOG.info("Vectorizer isBigTableOnlyResults smallTableIndices[i] < 0 returning false");
          return false;
        }
      }
    } else if (smallTableRetainSize > 0) {
      LOG.info("Vectorizer isBigTableOnlyResults smallTableRetainSize > 0 returning false");
      return false;
    }

    LOG.info("Vectorizer isBigTableOnlyResults returning true");
    return true;
  }

  Operator<? extends OperatorDesc> specializeMapJoinOperator(Operator<? extends OperatorDesc> op,
        VectorizationContext vContext, MapJoinDesc desc) throws HiveException {
    Operator<? extends OperatorDesc> vectorOp = null;
    Class<? extends Operator<?>> opClass = null;

    boolean isOuterJoin = !desc.getNoOuterJoin();

    VectorMapJoinDesc.HashTableImplementationType hashTableImplementationType = HashTableImplementationType.NONE;
    VectorMapJoinDesc.HashTableKind hashTableKind = HashTableKind.NONE;
    VectorMapJoinDesc.HashTableKeyType hashTableKeyType = HashTableKeyType.NONE;

    if (HiveConf.getBoolVar(hiveConf,
              HiveConf.ConfVars.HIVE_VECTORIZATION_MAPJOIN_NATIVE_FAST_HASHTABLE_ENABLED)) {
      hashTableImplementationType = HashTableImplementationType.FAST;
    } else {
      // Restrict to using BytesBytesMultiHashMap via MapJoinBytesTableContainer or
      // HybridHashTableContainer.
      hashTableImplementationType = HashTableImplementationType.OPTIMIZED;
    }

    int joinType = desc.getConds()[0].getType();

    boolean isInnerBigOnly = false;
    if (joinType == JoinDesc.INNER_JOIN && isBigTableOnlyResults(desc)) {
      isInnerBigOnly = true;
    }

    // By default, we can always use the multi-key class.
    hashTableKeyType = HashTableKeyType.MULTI_KEY;

    if (!HiveConf.getBoolVar(hiveConf,
        HiveConf.ConfVars.HIVE_VECTORIZATION_MAPJOIN_NATIVE_MULTIKEY_ONLY_ENABLED)) {

      // Look for single column optimization.
      byte posBigTable = (byte) desc.getPosBigTable();
      Map<Byte, List<ExprNodeDesc>> keyExprs = desc.getKeys();
      List<ExprNodeDesc> bigTableKeyExprs = keyExprs.get(posBigTable);
      if (bigTableKeyExprs.size() == 1) {
        String typeName = bigTableKeyExprs.get(0).getTypeString();
        LOG.info("Vectorizer vectorizeOperator map join typeName " + typeName);
        if (typeName.equals("boolean")) {
          hashTableKeyType = HashTableKeyType.BOOLEAN;
        } else if (typeName.equals("tinyint")) {
          hashTableKeyType = HashTableKeyType.BYTE;
        } else if (typeName.equals("smallint")) {
          hashTableKeyType = HashTableKeyType.SHORT;
        } else if (typeName.equals("int")) {
          hashTableKeyType = HashTableKeyType.INT;
        } else if (typeName.equals("bigint") || typeName.equals("long")) {
          hashTableKeyType = HashTableKeyType.LONG;
        } else if (VectorizationContext.isStringFamily(typeName)) {
          hashTableKeyType = HashTableKeyType.STRING;
        }
      }
    }

    switch (joinType) {
    case JoinDesc.INNER_JOIN:
      if (!isInnerBigOnly) {
        hashTableKind = HashTableKind.HASH_MAP;
      } else {
        hashTableKind = HashTableKind.HASH_MULTISET;
      }
      break;
    case JoinDesc.LEFT_OUTER_JOIN:
    case JoinDesc.RIGHT_OUTER_JOIN:
      hashTableKind = HashTableKind.HASH_MAP;
      break;
    case JoinDesc.LEFT_SEMI_JOIN:
      hashTableKind = HashTableKind.HASH_SET;
      break;
    default:
      throw new HiveException("Unknown join type " + joinType);
    }

    LOG.info("Vectorizer vectorizeOperator map join hashTableKind " + hashTableKind.name() + " hashTableKeyType " + hashTableKeyType.name());

    switch (hashTableKeyType) {
    case BOOLEAN:
    case BYTE:
    case SHORT:
    case INT:
    case LONG:
      switch (joinType) {
      case JoinDesc.INNER_JOIN:
        if (!isInnerBigOnly) {
          opClass = VectorMapJoinInnerLongOperator.class;
        } else {
          opClass = VectorMapJoinInnerBigOnlyLongOperator.class;
        }
        break;
      case JoinDesc.LEFT_OUTER_JOIN:
      case JoinDesc.RIGHT_OUTER_JOIN:
        opClass = VectorMapJoinOuterLongOperator.class;
        break;
      case JoinDesc.LEFT_SEMI_JOIN:
        opClass = VectorMapJoinLeftSemiLongOperator.class;
        break;
      default:
        throw new HiveException("Unknown join type " + joinType);
      }
      break;
    case STRING:
      switch (joinType) {
      case JoinDesc.INNER_JOIN:
        if (!isInnerBigOnly) {
          opClass = VectorMapJoinInnerStringOperator.class;
        } else {
          opClass = VectorMapJoinInnerBigOnlyStringOperator.class;
        }
        break;
      case JoinDesc.LEFT_OUTER_JOIN:
      case JoinDesc.RIGHT_OUTER_JOIN:
        opClass = VectorMapJoinOuterStringOperator.class;
        break;
      case JoinDesc.LEFT_SEMI_JOIN:
        opClass = VectorMapJoinLeftSemiStringOperator.class;
        break;
      default:
        throw new HiveException("Unknown join type " + joinType);
      }
      break;
    case MULTI_KEY:
      switch (joinType) {
      case JoinDesc.INNER_JOIN:
        if (!isInnerBigOnly) {
          opClass = VectorMapJoinInnerMultiKeyOperator.class;
        } else {
          opClass = VectorMapJoinInnerBigOnlyMultiKeyOperator.class;
        }
        break;
      case JoinDesc.LEFT_OUTER_JOIN:
      case JoinDesc.RIGHT_OUTER_JOIN:
        opClass = VectorMapJoinOuterMultiKeyOperator.class;
        break;
      case JoinDesc.LEFT_SEMI_JOIN:
        opClass = VectorMapJoinLeftSemiMultiKeyOperator.class;
        break;
      default:
        throw new HiveException("Unknown join type " + joinType);
      }
      break;
    }

    vectorOp = OperatorFactory.getVectorOperator(opClass, op.getConf(), vContext);
    LOG.info("Vectorizer vectorizeOperator map join class " + vectorOp.getClass().getSimpleName());

    boolean minMaxEnabled = HiveConf.getBoolVar(hiveConf,
        HiveConf.ConfVars.HIVE_VECTORIZATION_MAPJOIN_NATIVE_MINMAX_ENABLED);

    VectorMapJoinDesc vectorDesc = desc.getVectorDesc();
    vectorDesc.setHashTableImplementationType(hashTableImplementationType);
    vectorDesc.setHashTableKind(hashTableKind);
    vectorDesc.setHashTableKeyType(hashTableKeyType);
    vectorDesc.setMinMaxEnabled(minMaxEnabled);
    return vectorOp;
  }

  private boolean onExpressionHasNullSafes(MapJoinDesc desc) {
    boolean[] nullSafes = desc.getNullSafes();
    for (boolean nullSafe : nullSafes) {
      if (nullSafe) {
        return true;
      }
    }
    return false;
  }

  private boolean canSpecializeMapJoin(Operator<? extends OperatorDesc> op, MapJoinDesc desc,
      boolean isTez) {

    boolean specialize = false;

    if (op instanceof MapJoinOperator &&
        HiveConf.getBoolVar(hiveConf,
            HiveConf.ConfVars.HIVE_VECTORIZATION_MAPJOIN_NATIVE_ENABLED)) {

      // Currently, only under Tez and non-N-way joins.
      if (isTez && desc.getConds().length == 1 && !onExpressionHasNullSafes(desc)) {

        // Ok, all basic restrictions satisfied so far...
        specialize = true;

        if (!HiveConf.getBoolVar(hiveConf,
            HiveConf.ConfVars.HIVE_VECTORIZATION_MAPJOIN_NATIVE_FAST_HASHTABLE_ENABLED)) {

          // We are using the optimized hash table we have further
          // restrictions (using optimized and key type).

          if (!HiveConf.getBoolVar(hiveConf,
              HiveConf.ConfVars.HIVEMAPJOINUSEOPTIMIZEDTABLE)) {
            specialize = false;
          } else {
            byte posBigTable = (byte) desc.getPosBigTable();
            Map<Byte, List<ExprNodeDesc>> keyExprs = desc.getKeys();
            List<ExprNodeDesc> bigTableKeyExprs = keyExprs.get(posBigTable);
            for (ExprNodeDesc exprNodeDesc : bigTableKeyExprs) {
              String typeName = exprNodeDesc.getTypeString();
              if (!MapJoinKey.isSupportedField(typeName)) {
                specialize = false;
                break;
              }
            }
          }
        } else {

          // With the fast hash table implementation, we currently do not support
          // Hybrid Grace Hash Join.

          if (HiveConf.getBoolVar(hiveConf,
              HiveConf.ConfVars.HIVEUSEHYBRIDGRACEHASHJOIN)) {
            specialize = false;
          }
        }
      }
    }
    return specialize;
  }

  Operator<? extends OperatorDesc> vectorizeOperator(Operator<? extends OperatorDesc> op,
      VectorizationContext vContext, boolean isTez) throws HiveException {
    Operator<? extends OperatorDesc> vectorOp = null;

    switch (op.getType()) {
      case MAPJOIN:
        {
          MapJoinDesc desc = (MapJoinDesc) op.getConf();
          boolean specialize = canSpecializeMapJoin(op, desc, isTez);

          if (!specialize) {

            Class<? extends Operator<?>> opClass = null;
            if (op instanceof MapJoinOperator) {

              // *NON-NATIVE* vector map differences for LEFT OUTER JOIN and Filtered...

              List<ExprNodeDesc> bigTableFilters = desc.getFilters().get((byte) desc.getPosBigTable());
              boolean isOuterAndFiltered = (!desc.isNoOuterJoin() && bigTableFilters.size() > 0);
              if (!isOuterAndFiltered) {
                opClass = VectorMapJoinOperator.class;
              } else {
                opClass = VectorMapJoinOuterFilteredOperator.class;
              }
            } else if (op instanceof SMBMapJoinOperator) {
              opClass = VectorSMBMapJoinOperator.class;
            }

            vectorOp = OperatorFactory.getVectorOperator(opClass, op.getConf(), vContext);

          } else {

            // TEMPORARY Until Native Vector Map Join with Hybrid passes tests...
            // HiveConf.setBoolVar(physicalContext.getConf(),
            //    HiveConf.ConfVars.HIVEUSEHYBRIDGRACEHASHJOIN, false);

            vectorOp = specializeMapJoinOperator(op, vContext, desc);
          }
        }
        break;
      case GROUPBY:
      case FILTER:
      case SELECT:
      case FILESINK:
      case REDUCESINK:
      case LIMIT:
      case EXTRACT:
      case EVENT:
        vectorOp = OperatorFactory.getVectorOperator(op.getConf(), vContext);
        break;
      default:
        vectorOp = op;
        break;
    }

    LOG.info("vectorizeOperator " + (vectorOp == null ? "NULL" : vectorOp.getClass().getName()));
    LOG.info("vectorizeOperator " + (vectorOp == null || vectorOp.getConf() == null ? "NULL" : vectorOp.getConf().getClass().getName()));

    if (vectorOp != op) {
      fixupParentChildOperators(op, vectorOp);
      ((AbstractOperatorDesc) vectorOp.getConf()).setVectorMode(true);
    }
    return vectorOp;
  }

  private boolean isVirtualColumn(ColumnInfo column) {

    // Not using method column.getIsVirtualCol() because partitioning columns are also
    // treated as virtual columns in ColumnInfo.
    if (VirtualColumn.VIRTUAL_COLUMN_NAMES.contains(column.getInternalName())) {
        return true;
    }
    return false;
  }

  public void debugDisplayAllMaps(BaseWork work) {

    Map<String, Integer> columnNameMap = work.getVectorColumnNameMap();
    Map<Integer, String> columnTypeMap = work.getVectorColumnTypeMap();
    Map<Integer, String> scratchColumnTypeMap = work.getVectorScratchColumnTypeMap();

    LOG.debug("debugDisplayAllMaps columnNameMap " + columnNameMap.toString());
    LOG.debug("debugDisplayAllMaps columnTypeMap " + columnTypeMap.toString());
    LOG.debug("debugDisplayAllMaps scratchColumnTypeMap " + scratchColumnTypeMap.toString());
  }
}


File: ql/src/java/org/apache/hadoop/hive/ql/optimizer/spark/SparkReduceSinkMapJoinProc.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hive.ql.optimizer.spark;

import com.google.common.base.Preconditions;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.ql.exec.GroupByOperator;
import org.apache.hadoop.hive.ql.exec.HashTableDummyOperator;
import org.apache.hadoop.hive.ql.exec.MapJoinOperator;
import org.apache.hadoop.hive.ql.exec.Operator;
import org.apache.hadoop.hive.ql.exec.OperatorFactory;
import org.apache.hadoop.hive.ql.exec.ReduceSinkOperator;
import org.apache.hadoop.hive.ql.exec.RowSchema;
import org.apache.hadoop.hive.ql.exec.SparkHashTableSinkOperator;
import org.apache.hadoop.hive.ql.lib.DefaultGraphWalker;
import org.apache.hadoop.hive.ql.lib.DefaultRuleDispatcher;
import org.apache.hadoop.hive.ql.lib.Dispatcher;
import org.apache.hadoop.hive.ql.lib.GraphWalker;
import org.apache.hadoop.hive.ql.lib.Node;
import org.apache.hadoop.hive.ql.lib.NodeProcessor;
import org.apache.hadoop.hive.ql.lib.NodeProcessorCtx;
import org.apache.hadoop.hive.ql.lib.Rule;
import org.apache.hadoop.hive.ql.lib.RuleRegExp;
import org.apache.hadoop.hive.ql.parse.SemanticException;
import org.apache.hadoop.hive.ql.parse.spark.GenSparkProcContext;
import org.apache.hadoop.hive.ql.plan.BaseWork;
import org.apache.hadoop.hive.ql.plan.ExprNodeDesc;
import org.apache.hadoop.hive.ql.plan.HashTableDummyDesc;
import org.apache.hadoop.hive.ql.plan.MapJoinDesc;
import org.apache.hadoop.hive.ql.plan.OperatorDesc;
import org.apache.hadoop.hive.ql.plan.PlanUtils;
import org.apache.hadoop.hive.ql.plan.SparkEdgeProperty;
import org.apache.hadoop.hive.ql.plan.SparkHashTableSinkDesc;
import org.apache.hadoop.hive.ql.plan.SparkWork;
import org.apache.hadoop.hive.ql.plan.TableDesc;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Stack;

public class SparkReduceSinkMapJoinProc implements NodeProcessor {

  public static final Log LOG = LogFactory.getLog(SparkReduceSinkMapJoinProc.class.getName());

  public static class SparkMapJoinFollowedByGroupByProcessor implements NodeProcessor {
    private boolean hasGroupBy = false;

    @Override
    public Object process(Node nd, Stack<Node> stack, NodeProcessorCtx procCtx,
                          Object... nodeOutputs) throws SemanticException {
      GenSparkProcContext context = (GenSparkProcContext) procCtx;
      hasGroupBy = true;
      GroupByOperator op = (GroupByOperator) nd;
      float groupByMemoryUsage = context.conf.getFloatVar(
          HiveConf.ConfVars.HIVEMAPJOINFOLLOWEDBYMAPAGGRHASHMEMORY);
      op.getConf().setGroupByMemoryUsage(groupByMemoryUsage);
      return null;
    }

    public boolean getHasGroupBy() {
      return hasGroupBy;
    }
  }

  private boolean hasGroupBy(Operator<? extends OperatorDesc> mapjoinOp,
                             GenSparkProcContext context) throws SemanticException {
    List<Operator<? extends OperatorDesc>> childOps = mapjoinOp.getChildOperators();
    Map<Rule, NodeProcessor> rules = new LinkedHashMap<Rule, NodeProcessor>();
    SparkMapJoinFollowedByGroupByProcessor processor = new SparkMapJoinFollowedByGroupByProcessor();
    rules.put(new RuleRegExp("GBY", GroupByOperator.getOperatorName() + "%"), processor);
    Dispatcher disp = new DefaultRuleDispatcher(null, rules, context);
    GraphWalker ogw = new DefaultGraphWalker(disp);
    ArrayList<Node> topNodes = new ArrayList<Node>();
    topNodes.addAll(childOps);
    ogw.startWalking(topNodes, null);
    return processor.getHasGroupBy();
  }

  /* (non-Javadoc)
   * This processor addresses the RS-MJ case that occurs in spark on the small/hash
   * table side of things. The work that RS will be a part of must be connected
   * to the MJ work via be a broadcast edge.
   * We should not walk down the tree when we encounter this pattern because:
   * the type of work (map work or reduce work) needs to be determined
   * on the basis of the big table side because it may be a mapwork (no need for shuffle)
   * or reduce work.
   */
  @SuppressWarnings("unchecked")
  @Override
  public Object process(Node nd, Stack<Node> stack,
                        NodeProcessorCtx procContext, Object... nodeOutputs)
      throws SemanticException {
    GenSparkProcContext context = (GenSparkProcContext) procContext;

    if (!nd.getClass().equals(MapJoinOperator.class)) {
      return null;
    }

    MapJoinOperator mapJoinOp = (MapJoinOperator)nd;

    if (stack.size() < 2 || !(stack.get(stack.size() - 2) instanceof ReduceSinkOperator)) {
      context.currentMapJoinOperators.add(mapJoinOp);
      return null;
    }

    context.preceedingWork = null;
    context.currentRootOperator = null;

    ReduceSinkOperator parentRS = (ReduceSinkOperator)stack.get(stack.size() - 2);
    // remove the tag for in-memory side of mapjoin
    parentRS.getConf().setSkipTag(true);
    parentRS.setSkipTag(true);
    // remember the original parent list before we start modifying it.
    if (!context.mapJoinParentMap.containsKey(mapJoinOp)) {
      List<Operator<?>> parents = new ArrayList<Operator<?>>(mapJoinOp.getParentOperators());
      context.mapJoinParentMap.put(mapJoinOp, parents);
    }

    List<BaseWork> mapJoinWork;

    /*
     *  If there was a pre-existing work generated for the big-table mapjoin side,
     *  we need to hook the work generated for the RS (associated with the RS-MJ pattern)
     *  with the pre-existing work.
     *
     *  Otherwise, we need to associate that the mapjoin op
     *  to be linked to the RS work (associated with the RS-MJ pattern).
     *
     */
    mapJoinWork = context.mapJoinWorkMap.get(mapJoinOp);
    int workMapSize = context.childToWorkMap.get(parentRS).size();
    Preconditions.checkArgument(workMapSize == 1,
        "AssertionError: expected context.childToWorkMap.get(parentRS).size() to be 1, but was " + workMapSize);
    BaseWork parentWork = context.childToWorkMap.get(parentRS).get(0);

    // set the link between mapjoin and parent vertex
    int pos = context.mapJoinParentMap.get(mapJoinOp).indexOf(parentRS);
    if (pos == -1) {
      throw new SemanticException("Cannot find position of parent in mapjoin");
    }
    LOG.debug("Mapjoin "+mapJoinOp+", pos: "+pos+" --> "+parentWork.getName());
    mapJoinOp.getConf().getParentToInput().put(pos, parentWork.getName());

    SparkEdgeProperty edgeProp = new SparkEdgeProperty(SparkEdgeProperty.SHUFFLE_NONE);

    if (mapJoinWork != null) {
      for (BaseWork myWork: mapJoinWork) {
        // link the work with the work associated with the reduce sink that triggered this rule
        SparkWork sparkWork = context.currentTask.getWork();
        LOG.debug("connecting "+parentWork.getName()+" with "+myWork.getName());
        sparkWork.connect(parentWork, myWork, edgeProp);
      }
    }

    // remember in case we need to connect additional work later
    Map<BaseWork, SparkEdgeProperty> linkWorkMap = null;
    if (context.linkOpWithWorkMap.containsKey(mapJoinOp)) {
      linkWorkMap = context.linkOpWithWorkMap.get(mapJoinOp);
    } else {
      linkWorkMap = new HashMap<BaseWork, SparkEdgeProperty>();
    }
    linkWorkMap.put(parentWork, edgeProp);
    context.linkOpWithWorkMap.put(mapJoinOp, linkWorkMap);

    List<ReduceSinkOperator> reduceSinks
      = context.linkWorkWithReduceSinkMap.get(parentWork);
    if (reduceSinks == null) {
      reduceSinks = new ArrayList<ReduceSinkOperator>();
    }
    reduceSinks.add(parentRS);
    context.linkWorkWithReduceSinkMap.put(parentWork, reduceSinks);

    // create the dummy operators
    List<Operator<?>> dummyOperators = new ArrayList<Operator<?>>();

    // create an new operator: HashTableDummyOperator, which share the table desc
    HashTableDummyDesc desc = new HashTableDummyDesc();
    HashTableDummyOperator dummyOp = (HashTableDummyOperator) OperatorFactory.get(desc);
    TableDesc tbl;

    // need to create the correct table descriptor for key/value
    RowSchema rowSchema = parentRS.getParentOperators().get(0).getSchema();
    tbl = PlanUtils.getReduceValueTableDesc(PlanUtils.getFieldSchemasFromRowSchema(rowSchema, ""));
    dummyOp.getConf().setTbl(tbl);

    Map<Byte, List<ExprNodeDesc>> keyExprMap = mapJoinOp.getConf().getKeys();
    List<ExprNodeDesc> keyCols = keyExprMap.get(Byte.valueOf((byte) 0));
    StringBuilder keyOrder = new StringBuilder();
    for (int i = 0; i < keyCols.size(); i++) {
      keyOrder.append("+");
    }
    TableDesc keyTableDesc = PlanUtils.getReduceKeyTableDesc(PlanUtils
        .getFieldSchemasFromColumnList(keyCols, "mapjoinkey"), keyOrder.toString());
    mapJoinOp.getConf().setKeyTableDesc(keyTableDesc);

    // let the dummy op be the parent of mapjoin op
    mapJoinOp.replaceParent(parentRS, dummyOp);
    List<Operator<? extends OperatorDesc>> dummyChildren =
      new ArrayList<Operator<? extends OperatorDesc>>();
    dummyChildren.add(mapJoinOp);
    dummyOp.setChildOperators(dummyChildren);
    dummyOperators.add(dummyOp);

    // cut the operator tree so as to not retain connections from the parent RS downstream
    List<Operator<? extends OperatorDesc>> childOperators = parentRS.getChildOperators();
    int childIndex = childOperators.indexOf(mapJoinOp);
    childOperators.remove(childIndex);

    // the "work" needs to know about the dummy operators. They have to be separately initialized
    // at task startup
    if (mapJoinWork != null) {
      for (BaseWork myWork: mapJoinWork) {
        myWork.addDummyOp(dummyOp);
      }
    }
    if (context.linkChildOpWithDummyOp.containsKey(mapJoinOp)) {
      for (Operator<?> op: context.linkChildOpWithDummyOp.get(mapJoinOp)) {
        dummyOperators.add(op);
      }
    }
    context.linkChildOpWithDummyOp.put(mapJoinOp, dummyOperators);

    // replace ReduceSinkOp with HashTableSinkOp for the RSops which are parents of MJop
    MapJoinDesc mjDesc = mapJoinOp.getConf();
    HiveConf conf = context.conf;

    // Unlike in MR, we may call this method multiple times, for each
    // small table HTS. But, since it's idempotent, it should be OK.
    mjDesc.resetOrder();

    float hashtableMemoryUsage;
    if (hasGroupBy(mapJoinOp, context)) {
      hashtableMemoryUsage = conf.getFloatVar(
          HiveConf.ConfVars.HIVEHASHTABLEFOLLOWBYGBYMAXMEMORYUSAGE);
    } else {
      hashtableMemoryUsage = conf.getFloatVar(
          HiveConf.ConfVars.HIVEHASHTABLEMAXMEMORYUSAGE);
    }
    mjDesc.setHashTableMemoryUsage(hashtableMemoryUsage);

    SparkHashTableSinkDesc hashTableSinkDesc = new SparkHashTableSinkDesc(mjDesc);
    SparkHashTableSinkOperator hashTableSinkOp =
      (SparkHashTableSinkOperator) OperatorFactory.get(hashTableSinkDesc);

    byte tag = (byte) pos;
    int[] valueIndex = mjDesc.getValueIndex(tag);
    if (valueIndex != null) {
      List<ExprNodeDesc> newValues = new ArrayList<ExprNodeDesc>();
      List<ExprNodeDesc> values = hashTableSinkDesc.getExprs().get(tag);
      for (int index = 0; index < values.size(); index++) {
        if (valueIndex[index] < 0) {
          newValues.add(values.get(index));
        }
      }
      hashTableSinkDesc.getExprs().put(tag, newValues);
    }

    //get all parents of reduce sink
    List<Operator<? extends OperatorDesc>> rsParentOps = parentRS.getParentOperators();
    for (Operator<? extends OperatorDesc> parent : rsParentOps) {
      parent.replaceChild(parentRS, hashTableSinkOp);
    }
    hashTableSinkOp.setParentOperators(rsParentOps);
    hashTableSinkOp.setTag(tag);
    return true;
  }
}


File: ql/src/java/org/apache/hadoop/hive/ql/plan/SparkHashTableSinkDesc.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hive.ql.plan;

/**
 * Map Join operator Descriptor implementation.
 *
 */
@Explain(displayName = "Spark HashTable Sink Operator")
public class SparkHashTableSinkDesc extends HashTableSinkDesc {
  private static final long serialVersionUID = 1L;

  public SparkHashTableSinkDesc() {
  }

  public SparkHashTableSinkDesc(MapJoinDesc clone) {
    super(clone);
  }
}
