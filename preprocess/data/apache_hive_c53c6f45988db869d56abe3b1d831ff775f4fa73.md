Refactoring Types: ['Extract Method']
oop/hive/conf/HiveConf.java
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

package org.apache.hadoop.hive.conf;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintStream;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Properties;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.security.auth.login.LoginException;

import org.apache.commons.lang.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hive.common.classification.InterfaceAudience.LimitedPrivate;
import org.apache.hadoop.hive.conf.Validator.PatternSet;
import org.apache.hadoop.hive.conf.Validator.RangeValidator;
import org.apache.hadoop.hive.conf.Validator.RatioValidator;
import org.apache.hadoop.hive.conf.Validator.StringSet;
import org.apache.hadoop.hive.conf.Validator.TimeValidator;
import org.apache.hadoop.hive.shims.ShimLoader;
import org.apache.hadoop.hive.shims.Utils;
import org.apache.hadoop.mapred.JobConf;
import org.apache.hadoop.security.UserGroupInformation;
import org.apache.hadoop.util.Shell;
import org.apache.hive.common.HiveCompat;

import com.google.common.base.Joiner;

/**
 * Hive Configuration.
 */
public class HiveConf extends Configuration {
  protected String hiveJar;
  protected Properties origProp;
  protected String auxJars;
  private static final Log l4j = LogFactory.getLog(HiveConf.class);
  private static boolean loadMetastoreConfig = false;
  private static boolean loadHiveServer2Config = false;
  private static URL hiveDefaultURL = null;
  private static URL hiveSiteURL = null;
  private static URL hivemetastoreSiteUrl = null;
  private static URL hiveServer2SiteUrl = null;

  private static byte[] confVarByteArray = null;


  private static final Map<String, ConfVars> vars = new HashMap<String, ConfVars>();
  private static final Map<String, ConfVars> metaConfs = new HashMap<String, ConfVars>();
  private final List<String> restrictList = new ArrayList<String>();

  private Pattern modWhiteListPattern = null;
  private volatile boolean isSparkConfigUpdated = false;

  public boolean getSparkConfigUpdated() {
    return isSparkConfigUpdated;
  }

  public void setSparkConfigUpdated(boolean isSparkConfigUpdated) {
    this.isSparkConfigUpdated = isSparkConfigUpdated;
  }

  static {
    ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
    if (classLoader == null) {
      classLoader = HiveConf.class.getClassLoader();
    }

    hiveDefaultURL = classLoader.getResource("hive-default.xml");

    // Look for hive-site.xml on the CLASSPATH and log its location if found.
    hiveSiteURL = classLoader.getResource("hive-site.xml");
    hivemetastoreSiteUrl = classLoader.getResource("hivemetastore-site.xml");
    hiveServer2SiteUrl = classLoader.getResource("hiveserver2-site.xml");

    for (ConfVars confVar : ConfVars.values()) {
      vars.put(confVar.varname, confVar);
    }
  }

  /**
   * Metastore related options that the db is initialized against. When a conf
   * var in this is list is changed, the metastore instance for the CLI will
   * be recreated so that the change will take effect.
   */
  public static final HiveConf.ConfVars[] metaVars = {
      HiveConf.ConfVars.METASTOREWAREHOUSE,
      HiveConf.ConfVars.METASTOREURIS,
      HiveConf.ConfVars.METASTORE_SERVER_PORT,
      HiveConf.ConfVars.METASTORETHRIFTCONNECTIONRETRIES,
      HiveConf.ConfVars.METASTORETHRIFTFAILURERETRIES,
      HiveConf.ConfVars.METASTORE_CLIENT_CONNECT_RETRY_DELAY,
      HiveConf.ConfVars.METASTORE_CLIENT_SOCKET_TIMEOUT,
      HiveConf.ConfVars.METASTORE_CLIENT_SOCKET_LIFETIME,
      HiveConf.ConfVars.METASTOREPWD,
      HiveConf.ConfVars.METASTORECONNECTURLHOOK,
      HiveConf.ConfVars.METASTORECONNECTURLKEY,
      HiveConf.ConfVars.METASTORESERVERMINTHREADS,
      HiveConf.ConfVars.METASTORESERVERMAXTHREADS,
      HiveConf.ConfVars.METASTORE_TCP_KEEP_ALIVE,
      HiveConf.ConfVars.METASTORE_INT_ORIGINAL,
      HiveConf.ConfVars.METASTORE_INT_ARCHIVED,
      HiveConf.ConfVars.METASTORE_INT_EXTRACTED,
      HiveConf.ConfVars.METASTORE_KERBEROS_KEYTAB_FILE,
      HiveConf.ConfVars.METASTORE_KERBEROS_PRINCIPAL,
      HiveConf.ConfVars.METASTORE_USE_THRIFT_SASL,
      HiveConf.ConfVars.METASTORE_CACHE_PINOBJTYPES,
      HiveConf.ConfVars.METASTORE_CONNECTION_POOLING_TYPE,
      HiveConf.ConfVars.METASTORE_VALIDATE_TABLES,
      HiveConf.ConfVars.METASTORE_VALIDATE_COLUMNS,
      HiveConf.ConfVars.METASTORE_VALIDATE_CONSTRAINTS,
      HiveConf.ConfVars.METASTORE_STORE_MANAGER_TYPE,
      HiveConf.ConfVars.METASTORE_AUTO_CREATE_SCHEMA,
      HiveConf.ConfVars.METASTORE_AUTO_START_MECHANISM_MODE,
      HiveConf.ConfVars.METASTORE_TRANSACTION_ISOLATION,
      HiveConf.ConfVars.METASTORE_CACHE_LEVEL2,
      HiveConf.ConfVars.METASTORE_CACHE_LEVEL2_TYPE,
      HiveConf.ConfVars.METASTORE_IDENTIFIER_FACTORY,
      HiveConf.ConfVars.METASTORE_PLUGIN_REGISTRY_BUNDLE_CHECK,
      HiveConf.ConfVars.METASTORE_AUTHORIZATION_STORAGE_AUTH_CHECKS,
      HiveConf.ConfVars.METASTORE_BATCH_RETRIEVE_MAX,
      HiveConf.ConfVars.METASTORE_EVENT_LISTENERS,
      HiveConf.ConfVars.METASTORE_EVENT_CLEAN_FREQ,
      HiveConf.ConfVars.METASTORE_EVENT_EXPIRY_DURATION,
      HiveConf.ConfVars.METASTORE_FILTER_HOOK,
      HiveConf.ConfVars.METASTORE_RAW_STORE_IMPL,
      HiveConf.ConfVars.METASTORE_END_FUNCTION_LISTENERS,
      HiveConf.ConfVars.METASTORE_PART_INHERIT_TBL_PROPS,
      HiveConf.ConfVars.METASTORE_BATCH_RETRIEVE_TABLE_PARTITION_MAX,
      HiveConf.ConfVars.METASTORE_INIT_HOOKS,
      HiveConf.ConfVars.METASTORE_PRE_EVENT_LISTENERS,
      HiveConf.ConfVars.HMSHANDLERATTEMPTS,
      HiveConf.ConfVars.HMSHANDLERINTERVAL,
      HiveConf.ConfVars.HMSHANDLERFORCERELOADCONF,
      HiveConf.ConfVars.METASTORE_PARTITION_NAME_WHITELIST_PATTERN,
      HiveConf.ConfVars.METASTORE_ORM_RETRIEVE_MAPNULLS_AS_EMPTY_STRINGS,
      HiveConf.ConfVars.METASTORE_DISALLOW_INCOMPATIBLE_COL_TYPE_CHANGES,
      HiveConf.ConfVars.USERS_IN_ADMIN_ROLE,
      HiveConf.ConfVars.HIVE_AUTHORIZATION_MANAGER,
      HiveConf.ConfVars.HIVE_TXN_MANAGER,
      HiveConf.ConfVars.HIVE_TXN_TIMEOUT,
      HiveConf.ConfVars.HIVE_TXN_MAX_OPEN_BATCH,
      HiveConf.ConfVars.HIVE_METASTORE_STATS_NDV_DENSITY_FUNCTION,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_ENABLED,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_SIZE,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_MAX_PARTITIONS,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_FPP,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_MAX_VARIANCE,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_TTL,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_MAX_WRITER_WAIT,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_MAX_READER_WAIT,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_MAX_FULL,
      HiveConf.ConfVars.METASTORE_AGGREGATE_STATS_CACHE_CLEAN_UNTIL
      };

  /**
   * User configurable Metastore vars
   */
  public static final HiveConf.ConfVars[] metaConfVars = {
      HiveConf.ConfVars.METASTORE_TRY_DIRECT_SQL,
      HiveConf.ConfVars.METASTORE_TRY_DIRECT_SQL_DDL,
      HiveConf.ConfVars.METASTORE_CLIENT_SOCKET_TIMEOUT
  };

  static {
    for (ConfVars confVar : metaConfVars) {
      metaConfs.put(confVar.varname, confVar);
    }
  }

  /**
   * dbVars are the parameters can be set per database. If these
   * parameters are set as a database property, when switching to that
   * database, the HiveConf variable will be changed. The change of these
   * parameters will effectively change the DFS and MapReduce clusters
   * for different databases.
   */
  public static final HiveConf.ConfVars[] dbVars = {
    HiveConf.ConfVars.HADOOPBIN,
    HiveConf.ConfVars.METASTOREWAREHOUSE,
    HiveConf.ConfVars.SCRATCHDIR
  };

  /**
   * ConfVars.
   *
   * These are the default configuration properties for Hive. Each HiveConf
   * object is initialized as follows:
   *
   * 1) Hadoop configuration properties are applied.
   * 2) ConfVar properties with non-null values are overlayed.
   * 3) hive-site.xml properties are overlayed.
   *
   * WARNING: think twice before adding any Hadoop configuration properties
   * with non-null values to this list as they will override any values defined
   * in the underlying Hadoop configuration.
   */
  public static enum ConfVars {
    // QL execution stuff
    SCRIPTWRAPPER("hive.exec.script.wrapper", null, ""),
    PLAN("hive.exec.plan", "", ""),
    PLAN_SERIALIZATION("hive.plan.serialization.format", "kryo",
        "Query plan format serialization between client and task nodes. \n" +
        "Two supported values are : kryo and javaXML. Kryo is default."),
    STAGINGDIR("hive.exec.stagingdir", ".hive-staging",
        "Directory name that will be created inside table locations in order to support HDFS encryption. " +
        "This is replaces ${hive.exec.scratchdir} for query results with the exception of read-only tables. " +
        "In all cases ${hive.exec.scratchdir} is still used for other temporary files, such as job plans."),
    SCRATCHDIR("hive.exec.scratchdir", "/tmp/hive",
        "HDFS root scratch dir for Hive jobs which gets created with write all (733) permission. " +
        "For each connecting user, an HDFS scratch dir: ${hive.exec.scratchdir}/<username> is created, " +
        "with ${hive.scratch.dir.permission}."),
    LOCALSCRATCHDIR("hive.exec.local.scratchdir",
        "${system:java.io.tmpdir}" + File.separator + "${system:user.name}",
        "Local scratch space for Hive jobs"),
    DOWNLOADED_RESOURCES_DIR("hive.downloaded.resources.dir",
        "${system:java.io.tmpdir}" + File.separator + "${hive.session.id}_resources",
        "Temporary local directory for added resources in the remote file system."),
    SCRATCHDIRPERMISSION("hive.scratch.dir.permission", "700",
        "The permission for the user specific scratch directories that get created."),
    SUBMITVIACHILD("hive.exec.submitviachild", false, ""),
    SUBMITLOCALTASKVIACHILD("hive.exec.submit.local.task.via.child", true,
        "Determines whether local tasks (typically mapjoin hashtable generation phase) runs in \n" +
        "separate JVM (true recommended) or not. \n" +
        "Avoids the overhead of spawning new JVM, but can lead to out-of-memory issues."),
    SCRIPTERRORLIMIT("hive.exec.script.maxerrsize", 100000,
        "Maximum number of bytes a script is allowed to emit to standard error (per map-reduce task). \n" +
        "This prevents runaway scripts from filling logs partitions to capacity"),
    ALLOWPARTIALCONSUMP("hive.exec.script.allow.partial.consumption", false,
        "When enabled, this option allows a user script to exit successfully without consuming \n" +
        "all the data from the standard input."),
    STREAMREPORTERPERFIX("stream.stderr.reporter.prefix", "reporter:",
        "Streaming jobs that log to standard error with this prefix can log counter or status information."),
    STREAMREPORTERENABLED("stream.stderr.reporter.enabled", true,
        "Enable consumption of status and counter messages for streaming jobs."),
    COMPRESSRESULT("hive.exec.compress.output", false,
        "This controls whether the final outputs of a query (to a local/HDFS file or a Hive table) is compressed. \n" +
        "The compression codec and other options are determined from Hadoop config variables mapred.output.compress*"),
    COMPRESSINTERMEDIATE("hive.exec.compress.intermediate", false,
        "This controls whether intermediate files produced by Hive between multiple map-reduce jobs are compressed. \n" +
        "The compression codec and other options are determined from Hadoop config variables mapred.output.compress*"),
    COMPRESSINTERMEDIATECODEC("hive.intermediate.compression.codec", "", ""),
    COMPRESSINTERMEDIATETYPE("hive.intermediate.compression.type", "", ""),
    BYTESPERREDUCER("hive.exec.reducers.bytes.per.reducer", (long) (256 * 1000 * 1000),
        "size per reducer.The default is 256Mb, i.e if the input size is 1G, it will use 4 reducers."),
    MAXREDUCERS("hive.exec.reducers.max", 1009,
        "max number of reducers will be used. If the one specified in the configuration parameter mapred.reduce.tasks is\n" +
        "negative, Hive will use this one as the max number of reducers when automatically determine number of reducers."),
    PREEXECHOOKS("hive.exec.pre.hooks", "",
        "Comma-separated list of pre-execution hooks to be invoked for each statement. \n" +
        "A pre-execution hook is specified as the name of a Java class which implements the \n" +
        "org.apache.hadoop.hive.ql.hooks.ExecuteWithHookContext interface."),
    POSTEXECHOOKS("hive.exec.post.hooks", "",
        "Comma-separated list of post-execution hooks to be invoked for each statement. \n" +
        "A post-execution hook is specified as the name of a Java class which implements the \n" +
        "org.apache.hadoop.hive.ql.hooks.ExecuteWithHookContext interface."),
    ONFAILUREHOOKS("hive.exec.failure.hooks", "",
        "Comma-separated list of on-failure hooks to be invoked for each statement. \n" +
        "An on-failure hook is specified as the name of Java class which implements the \n" +
        "org.apache.hadoop.hive.ql.hooks.ExecuteWithHookContext interface."),
    QUERYREDACTORHOOKS("hive.exec.query.redactor.hooks", "",
        "Comma-separated list of hooks to be invoked for each query which can \n" +
        "tranform the query before it's placed in the job.xml file. Must be a Java class which \n" +
        "extends from the org.apache.hadoop.hive.ql.hooks.Redactor abstract class."),
    CLIENTSTATSPUBLISHERS("hive.client.stats.publishers", "",
        "Comma-separated list of statistics publishers to be invoked on counters on each job. \n" +
        "A client stats publisher is specified as the name of a Java class which implements the \n" +
        "org.apache.hadoop.hive.ql.stats.ClientStatsPublisher interface."),
    EXECPARALLEL("hive.exec.parallel", false, "Whether to execute jobs in parallel"),
    EXECPARALLETHREADNUMBER("hive.exec.parallel.thread.number", 8,
        "How many jobs at most can be executed in parallel"),
    HIVESPECULATIVEEXECREDUCERS("hive.mapred.reduce.tasks.speculative.execution", true,
        "Whether speculative execution for reducers should be turned on. "),
    HIVECOUNTERSPULLINTERVAL("hive.exec.counters.pull.interval", 1000L,
        "The interval with which to poll the JobTracker for the counters the running job. \n" +
        "The smaller it is the more load there will be on the jobtracker, the higher it is the less granular the caught will be."),
    DYNAMICPARTITIONING("hive.exec.dynamic.partition", true,
        "Whether or not to allow dynamic partitions in DML/DDL."),
    DYNAMICPARTITIONINGMODE("hive.exec.dynamic.partition.mode", "strict",
        "In strict mode, the user must specify at least one static partition\n" +
        "in case the user accidentally overwrites all partitions.\n" +
        "In nonstrict mode all partitions are allowed to be dynamic."),
    DYNAMICPARTITIONMAXPARTS("hive.exec.max.dynamic.partitions", 1000,
        "Maximum number of dynamic partitions allowed to be created in total."),
    DYNAMICPARTITIONMAXPARTSPERNODE("hive.exec.max.dynamic.partitions.pernode", 100,
        "Maximum number of dynamic partitions allowed to be created in each mapper/reducer node."),
    MAXCREATEDFILES("hive.exec.max.created.files", 100000L,
        "Maximum number of HDFS files created by all mappers/reducers in a MapReduce job."),
    DEFAULTPARTITIONNAME("hive.exec.default.partition.name", "__HIVE_DEFAULT_PARTITION__",
        "The default partition name in case the dynamic partition column value is null/empty string or any other values that cannot be escaped. \n" +
        "This value must not contain any special character used in HDFS URI (e.g., ':', '%', '/' etc). \n" +
        "The user has to be aware that the dynamic partition value should not contain this value to avoid confusions."),
    DEFAULT_ZOOKEEPER_PARTITION_NAME("hive.lockmgr.zookeeper.default.partition.name", "__HIVE_DEFAULT_ZOOKEEPER_PARTITION__", ""),

    // Whether to show a link to the most failed task + debugging tips
    SHOW_JOB_FAIL_DEBUG_INFO("hive.exec.show.job.failure.debug.info", true,
        "If a job fails, whether to provide a link in the CLI to the task with the\n" +
        "most failures, along with debugging hints if applicable."),
    JOB_DEBUG_CAPTURE_STACKTRACES("hive.exec.job.debug.capture.stacktraces", true,
        "Whether or not stack traces parsed from the task logs of a sampled failed task \n" +
        "for each failed job should be stored in the SessionState"),
    JOB_DEBUG_TIMEOUT("hive.exec.job.debug.timeout", 30000, ""),
    TASKLOG_DEBUG_TIMEOUT("hive.exec.tasklog.debug.timeout", 20000, ""),
    OUTPUT_FILE_EXTENSION("hive.output.file.extension", null,
        "String used as a file extension for output files. \n" +
        "If not set, defaults to the codec extension for text files (e.g. \".gz\"), or no extension otherwise."),

    HIVE_IN_TEST("hive.in.test", false, "internal usage only, true in test mode", true),

    HIVE_IN_TEZ_TEST("hive.in.tez.test", false, "internal use only, true when in testing tez",
        true),

    LOCALMODEAUTO("hive.exec.mode.local.auto", false,
        "Let Hive determine whether to run in local mode automatically"),
    LOCALMODEMAXBYTES("hive.exec.mode.local.auto.inputbytes.max", 134217728L,
        "When hive.exec.mode.local.auto is true, input bytes should less than this for local mode."),
    LOCALMODEMAXINPUTFILES("hive.exec.mode.local.auto.input.files.max", 4,
        "When hive.exec.mode.local.auto is true, the number of tasks should less than this for local mode."),

    DROPIGNORESNONEXISTENT("hive.exec.drop.ignorenonexistent", true,
        "Do not report an error if DROP TABLE/VIEW/Index/Function specifies a non-existent table/view/index/function"),

    HIVEIGNOREMAPJOINHINT("hive.ignore.mapjoin.hint", true, "Ignore the mapjoin hint"),

    HIVE_FILE_MAX_FOOTER("hive.file.max.footer", 100,
        "maximum number of lines for footer user can define for a table file"),

    HIVE_RESULTSET_USE_UNIQUE_COLUMN_NAMES("hive.resultset.use.unique.column.names", true,
        "Make column names unique in the result set by qualifying column names with table alias if needed.\n" +
        "Table alias will be added to column names for queries of type \"select *\" or \n" +
        "if query explicitly uses table alias \"select r1.x..\"."),

    // Hadoop Configuration Properties
    // Properties with null values are ignored and exist only for the purpose of giving us
    // a symbolic name to reference in the Hive source code. Properties with non-null
    // values will override any values set in the underlying Hadoop configuration.
    HADOOPBIN("hadoop.bin.path", findHadoopBinary(), "", true),
    HIVE_FS_HAR_IMPL("fs.har.impl", "org.apache.hadoop.hive.shims.HiveHarFileSystem",
        "The implementation for accessing Hadoop Archives. Note that this won't be applicable to Hadoop versions less than 0.20"),
    HADOOPFS(ShimLoader.getHadoopShims().getHadoopConfNames().get("HADOOPFS"), null, "", true),
    HADOOPMAPFILENAME(ShimLoader.getHadoopShims().getHadoopConfNames().get("HADOOPMAPFILENAME"), null, "", true),
    HADOOPMAPREDINPUTDIR(ShimLoader.getHadoopShims().getHadoopConfNames().get("HADOOPMAPREDINPUTDIR"), null, "", true),
    HADOOPMAPREDINPUTDIRRECURSIVE(ShimLoader.getHadoopShims().getHadoopConfNames().get("HADOOPMAPREDINPUTDIRRECURSIVE"), false, "", true),
    MAPREDMAXSPLITSIZE(ShimLoader.getHadoopShims().getHadoopConfNames().get("MAPREDMAXSPLITSIZE"), 256000000L, "", true),
    MAPREDMINSPLITSIZE(ShimLoader.getHadoopShims().getHadoopConfNames().get("MAPREDMINSPLITSIZE"), 1L, "", true),
    MAPREDMINSPLITSIZEPERNODE(ShimLoader.getHadoopShims().getHadoopConfNames().get("MAPREDMINSPLITSIZEPERNODE"), 1L, "", true),
    MAPREDMINSPLITSIZEPERRACK(ShimLoader.getHadoopShims().getHadoopConfNames().get("MAPREDMINSPLITSIZEPERRACK"), 1L, "", true),
    // The number of reduce tasks per job. Hadoop sets this value to 1 by default
    // By setting this property to -1, Hive will automatically determine the correct
    // number of reducers.
    HADOOPNUMREDUCERS(ShimLoader.getHadoopShims().getHadoopConfNames().get("HADOOPNUMREDUCERS"), -1, "", true),
    HADOOPJOBNAME(ShimLoader.getHadoopShims().getHadoopConfNames().get("HADOOPJOBNAME"), null, "", true),
    HADOOPSPECULATIVEEXECREDUCERS(ShimLoader.getHadoopShims().getHadoopConfNames().get("HADOOPSPECULATIVEEXECREDUCERS"), true, "", true),
    MAPREDSETUPCLEANUPNEEDED(ShimLoader.getHadoopShims().getHadoopConfNames().get("MAPREDSETUPCLEANUPNEEDED"), false, "", true),
    MAPREDTASKCLEANUPNEEDED(ShimLoader.getHadoopShims().getHadoopConfNames().get("MAPREDTASKCLEANUPNEEDED"), false, "", true),

    // Metastore stuff. Be sure to update HiveConf.metaVars when you add something here!
    METASTOREWAREHOUSE("hive.metastore.warehouse.dir", "/user/hive/warehouse",
        "location of default database for the warehouse"),
    METASTOREURIS("hive.metastore.uris", "",
        "Thrift URI for the remote metastore. Used by metastore client to connect to remote metastore."),

    METASTORE_FASTPATH("hive.metastore.fastpath", false,
        "Used to avoid all of the proxies and object copies in the metastore.  Note, if this is " +
            "set, you MUST use a local metastore (hive.metastore.uris must be empty) otherwise " +
            "undefined and most likely undesired behavior will result"),
    METASTORE_HBASE_CATALOG_CACHE_SIZE("hive.metastore.hbase.catalog.cache.size", 50000, "Maximum number of " +
        "objects we will place in the hbase metastore catalog cache.  The objects will be divided up by " +
        "types that we need to cache."),
    METASTORE_HBASE_AGGREGATE_STATS_CACHE_SIZE("hive.metastore.hbase.aggregate.stats.cache.size", 10000,
        "Maximum number of aggregate stats nodes that we will place in the hbase metastore aggregate stats cache."),
    METASTORE_HBASE_AGGREGATE_STATS_CACHE_MAX_PARTITIONS("hive.metastore.hbase.aggregate.stats.max.partitions", 10000,
        "Maximum number of partitions that are aggregated per cache node."),
    METASTORE_HBASE_AGGREGATE_STATS_CACHE_FALSE_POSITIVE_PROBABILITY("hive.metastore.hbase.aggregate.stats.false.positive.probability",
        (float) 0.01, "Maximum false positive probability for the Bloom Filter used in each aggregate stats cache node (default 1%)."),
    METASTORE_HBASE_AGGREGATE_STATS_CACHE_MAX_VARIANCE("hive.metastore.hbase.aggregate.stats.max.variance", (float) 0.1,
        "Maximum tolerable variance in number of partitions between a cached node and our request (default 10%)."),
    METASTORE_HBASE_CACHE_TIME_TO_LIVE("hive.metastore.hbase.cache.ttl", "600s", new TimeValidator(TimeUnit.SECONDS),
        "Number of seconds for a cached node to be active in the cache before they become stale."),
    METASTORE_HBASE_CACHE_MAX_WRITER_WAIT("hive.metastore.hbase.cache.max.writer.wait", "5000ms", new TimeValidator(TimeUnit.MILLISECONDS),
        "Number of milliseconds a writer will wait to acquire the writelock before giving up."),
    METASTORE_HBASE_CACHE_MAX_READER_WAIT("hive.metastore.hbase.cache.max.reader.wait", "1000ms", new TimeValidator(TimeUnit.MILLISECONDS),
         "Number of milliseconds a reader will wait to acquire the readlock before giving up."),
    METASTORE_HBASE_CACHE_MAX_FULL("hive.metastore.hbase.cache.max.full", (float) 0.9,
         "Maximum cache full % after which the cache cleaner thread kicks in."),
    METASTORE_HBASE_CACHE_CLEAN_UNTIL("hive.metastore.hbase.cache.clean.until", (float) 0.8,
          "The cleaner thread cleans until cache reaches this % full size."),
    METASTORE_HBASE_CONNECTION_CLASS("hive.metastore.hbase.connection.class",
        "org.apache.hadoop.hive.metastore.hbase.VanillaHBaseConnection",
        "Class used to connection to HBase"),

    METASTORETHRIFTCONNECTIONRETRIES("hive.metastore.connect.retries", 3,
        "Number of retries while opening a connection to metastore"),
    METASTORETHRIFTFAILURERETRIES("hive.metastore.failure.retries", 1,
        "Number of retries upon failure of Thrift metastore calls"),
    METASTORE_SERVER_PORT("hive.metastore.port", 9083, "Hive metastore listener port"),
    METASTORE_CLIENT_CONNECT_RETRY_DELAY("hive.metastore.client.connect.retry.delay", "1s",
        new TimeValidator(TimeUnit.SECONDS),
        "Number of seconds for the client to wait between consecutive connection attempts"),
    METASTORE_CLIENT_SOCKET_TIMEOUT("hive.metastore.client.socket.timeout", "600s",
        new TimeValidator(TimeUnit.SECONDS),
        "MetaStore Client socket timeout in seconds"),
    METASTORE_CLIENT_SOCKET_LIFETIME("hive.metastore.client.socket.lifetime", "0s",
        new TimeValidator(TimeUnit.SECONDS),
        "MetaStore Client socket lifetime in seconds. After this time is exceeded, client\n" +
        "reconnects on the next MetaStore operation. A value of 0s means the connection\n" +
        "has an infinite lifetime."),
    METASTOREPWD("javax.jdo.option.ConnectionPassword", "mine",
        "password to use against metastore database"),
    METASTORECONNECTURLHOOK("hive.metastore.ds.connection.url.hook", "",
        "Name of the hook to use for retrieving the JDO connection URL. If empty, the value in javax.jdo.option.ConnectionURL is used"),
    METASTOREMULTITHREADED("javax.jdo.option.Multithreaded", true,
        "Set this to true if multiple threads access metastore through JDO concurrently."),
    METASTORECONNECTURLKEY("javax.jdo.option.ConnectionURL",
        "jdbc:derby:;databaseName=metastore_db;create=true",
        "JDBC connect string for a JDBC metastore"),
    HMSHANDLERATTEMPTS("hive.hmshandler.retry.attempts", 10,
        "The number of times to retry a HMSHandler call if there were a connection error."),
    HMSHANDLERINTERVAL("hive.hmshandler.retry.interval", "2000ms",
        new TimeValidator(TimeUnit.MILLISECONDS), "The time between HMSHandler retry attempts on failure."),
    HMSHANDLERFORCERELOADCONF("hive.hmshandler.force.reload.conf", false,
        "Whether to force reloading of the HMSHandler configuration (including\n" +
        "the connection URL, before the next metastore query that accesses the\n" +
        "datastore. Once reloaded, this value is reset to false. Used for\n" +
        "testing only."),
    METASTORESERVERMAXMESSAGESIZE("hive.metastore.server.max.message.size", 100*1024*1024,
        "Maximum message size in bytes a HMS will accept."),
    METASTORESERVERMINTHREADS("hive.metastore.server.min.threads", 200,
        "Minimum number of worker threads in the Thrift server's pool."),
    METASTORESERVERMAXTHREADS("hive.metastore.server.max.threads", 1000,
        "Maximum number of worker threads in the Thrift server's pool."),
    METASTORE_TCP_KEEP_ALIVE("hive.metastore.server.tcp.keepalive", true,
        "Whether to enable TCP keepalive for the metastore server. Keepalive will prevent accumulation of half-open connections."),

    METASTORE_INT_ORIGINAL("hive.metastore.archive.intermediate.original",
        "_INTERMEDIATE_ORIGINAL",
        "Intermediate dir suffixes used for archiving. Not important what they\n" +
        "are, as long as collisions are avoided"),
    METASTORE_INT_ARCHIVED("hive.metastore.archive.intermediate.archived",
        "_INTERMEDIATE_ARCHIVED", ""),
    METASTORE_INT_EXTRACTED("hive.metastore.archive.intermediate.extracted",
        "_INTERMEDIATE_EXTRACTED", ""),
    METASTORE_KERBEROS_KEYTAB_FILE("hive.metastore.kerberos.keytab.file", "",
        "The path to the Kerberos Keytab file containing the metastore Thrift server's service principal."),
    METASTORE_KERBEROS_PRINCIPAL("hive.metastore.kerberos.principal",
        "hive-metastore/_HOST@EXAMPLE.COM",
        "The service principal for the metastore Thrift server. \n" +
        "The special string _HOST will be replaced automatically with the correct host name."),
    METASTORE_USE_THRIFT_SASL("hive.metastore.sasl.enabled", false,
        "If true, the metastore Thrift interface will be secured with SASL. Clients must authenticate with Kerberos."),
    METASTORE_USE_THRIFT_FRAMED_TRANSPORT("hive.metastore.thrift.framed.transport.enabled", false,
        "If true, the metastore Thrift interface will use TFramedTransport. When false (default) a standard TTransport is used."),
    METASTORE_USE_THRIFT_COMPACT_PROTOCOL("hive.metastore.thrift.compact.protocol.enabled", false,
        "If true, the metastore Thrift interface will use TCompactProtocol. When false (default) TBinaryProtocol will be used.\n" +
        "Setting it to true will break compatibility with older clients running TBinaryProtocol."),
    METASTORE_CLUSTER_DELEGATION_TOKEN_STORE_CLS("hive.cluster.delegation.token.store.class",
        "org.apache.hadoop.hive.thrift.MemoryTokenStore",
        "The delegation token store implementation. Set to org.apache.hadoop.hive.thrift.ZooKeeperTokenStore for load-balanced cluster."),
    METASTORE_CLUSTER_DELEGATION_TOKEN_STORE_ZK_CONNECTSTR(
        "hive.cluster.delegation.token.store.zookeeper.connectString", "",
        "The ZooKeeper token store connect string. You can re-use the configuration value\n" +
        "set in hive.zookeeper.quorum, by leaving this parameter unset."),
    METASTORE_CLUSTER_DELEGATION_TOKEN_STORE_ZK_ZNODE(
        "hive.cluster.delegation.token.store.zookeeper.znode", "/hivedelegation",
        "The root path for token store data. Note that this is used by both HiveServer2 and\n" +
        "MetaStore to store delegation Token. One directory gets created for each of them.\n" +
        "The final directory names would have the servername appended to it (HIVESERVER2,\n" +
        "METASTORE)."),
    METASTORE_CLUSTER_DELEGATION_TOKEN_STORE_ZK_ACL(
        "hive.cluster.delegation.token.store.zookeeper.acl", "",
        "ACL for token store entries. Comma separated list of ACL entries. For example:\n" +
        "sasl:hive/host1@MY.DOMAIN:cdrwa,sasl:hive/host2@MY.DOMAIN:cdrwa\n" +
        "Defaults to all permissions for the hiveserver2/metastore process user."),
    METASTORE_CACHE_PINOBJTYPES("hive.metastore.cache.pinobjtypes", "Table,StorageDescriptor,SerDeInfo,Partition,Database,Type,FieldSchema,Order",
        "List of comma separated metastore object types that should be pinned in the cache"),
    METASTORE_CONNECTION_POOLING_TYPE("datanucleus.connectionPoolingType", "BONECP",
        "Specify connection pool library for datanucleus"),
    METASTORE_VALIDATE_TABLES("datanucleus.validateTables", false,
        "validates existing schema against code. turn this on if you want to verify existing schema"),
    METASTORE_VALIDATE_COLUMNS("datanucleus.validateColumns", false,
        "validates existing schema against code. turn this on if you want to verify existing schema"),
    METASTORE_VALIDATE_CONSTRAINTS("datanucleus.validateConstraints", false,
        "validates existing schema against code. turn this on if you want to verify existing schema"),
    METASTORE_STORE_MANAGER_TYPE("datanucleus.storeManagerType", "rdbms", "metadata store type"),
    METASTORE_AUTO_CREATE_SCHEMA("datanucleus.autoCreateSchema", true,
        "creates necessary schema on a startup if one doesn't exist. set this to false, after creating it once"),
    METASTORE_FIXED_DATASTORE("datanucleus.fixedDatastore", false, ""),
    METASTORE_SCHEMA_VERIFICATION("hive.metastore.schema.verification", false,
        "Enforce metastore schema version consistency.\n" +
        "True: Verify that version information stored in metastore matches with one from Hive jars.  Also disable automatic\n" +
        "      schema migration attempt. Users are required to manually migrate schema after Hive upgrade which ensures\n" +
        "      proper metastore schema migration. (Default)\n" +
        "False: Warn if the version information stored in metastore doesn't match with one from in Hive jars."),
    METASTORE_SCHEMA_VERIFICATION_RECORD_VERSION("hive.metastore.schema.verification.record.version", true,
      "When true the current MS version is recorded in the VERSION table. If this is disabled and verification is\n" +
      " enabled the MS will be unusable."),
    METASTORE_AUTO_START_MECHANISM_MODE("datanucleus.autoStartMechanismMode", "checked",
        "throw exception if metadata tables are incorrect"),
    METASTORE_TRANSACTION_ISOLATION("datanucleus.transactionIsolation", "read-committed",
        "Default transaction isolation level for identity generation."),
    METASTORE_CACHE_LEVEL2("datanucleus.cache.level2", false,
        "Use a level 2 cache. Turn this off if metadata is changed independently of Hive metastore server"),
    METASTORE_CACHE_LEVEL2_TYPE("datanucleus.cache.level2.type", "none", ""),
    METASTORE_IDENTIFIER_FACTORY("datanucleus.identifierFactory", "datanucleus1",
        "Name of the identifier factory to use when generating table/column names etc. \n" +
        "'datanucleus1' is used for backward compatibility with DataNucleus v1"),
    METASTORE_USE_LEGACY_VALUE_STRATEGY("datanucleus.rdbms.useLegacyNativeValueStrategy", true, ""),
    METASTORE_PLUGIN_REGISTRY_BUNDLE_CHECK("datanucleus.plugin.pluginRegistryBundleCheck", "LOG",
        "Defines what happens when plugin bundles are found and are duplicated [EXCEPTION|LOG|NONE]"),
    METASTORE_BATCH_RETRIEVE_MAX("hive.metastore.batch.retrieve.max", 300,
        "Maximum number of objects (tables/partitions) can be retrieved from metastore in one batch. \n" +
        "The higher the number, the less the number of round trips is needed to the Hive metastore server, \n" +
        "but it may also cause higher memory requirement at the client side."),
    METASTORE_BATCH_RETRIEVE_TABLE_PARTITION_MAX(
        "hive.metastore.batch.retrieve.table.partition.max", 1000,
        "Maximum number of table partitions that metastore internally retrieves in one batch."),

    METASTORE_INIT_HOOKS("hive.metastore.init.hooks", "",
        "A comma separated list of hooks to be invoked at the beginning of HMSHandler initialization. \n" +
        "An init hook is specified as the name of Java class which extends org.apache.hadoop.hive.metastore.MetaStoreInitListener."),
    METASTORE_PRE_EVENT_LISTENERS("hive.metastore.pre.event.listeners", "",
        "List of comma separated listeners for metastore events."),
    METASTORE_EVENT_LISTENERS("hive.metastore.event.listeners", "", ""),
    METASTORE_EVENT_DB_LISTENER_TTL("hive.metastore.event.db.listener.timetolive", "86400s",
        new TimeValidator(TimeUnit.SECONDS),
        "time after which events will be removed from the database listener queue"),
    METASTORE_AUTHORIZATION_STORAGE_AUTH_CHECKS("hive.metastore.authorization.storage.checks", false,
        "Should the metastore do authorization checks against the underlying storage (usually hdfs) \n" +
        "for operations like drop-partition (disallow the drop-partition if the user in\n" +
        "question doesn't have permissions to delete the corresponding directory\n" +
        "on the storage)."),
    METASTORE_EVENT_CLEAN_FREQ("hive.metastore.event.clean.freq", "0s",
        new TimeValidator(TimeUnit.SECONDS),
        "Frequency at which timer task runs to purge expired events in metastore."),
    METASTORE_EVENT_EXPIRY_DURATION("hive.metastore.event.expiry.duration", "0s",
        new TimeValidator(TimeUnit.SECONDS),
        "Duration after which events expire from events table"),
    METASTORE_EXECUTE_SET_UGI("hive.metastore.execute.setugi", true,
        "In unsecure mode, setting this property to true will cause the metastore to execute DFS operations using \n" +
        "the client's reported user and group permissions. Note that this property must be set on \n" +
        "both the client and server sides. Further note that its best effort. \n" +
        "If client sets its to true and server sets it to false, client setting will be ignored."),
    METASTORE_PARTITION_NAME_WHITELIST_PATTERN("hive.metastore.partition.name.whitelist.pattern", "",
        "Partition names will be checked against this regex pattern and rejected if not matched."),

    METASTORE_INTEGER_JDO_PUSHDOWN("hive.metastore.integral.jdo.pushdown", false,
        "Allow JDO query pushdown for integral partition columns in metastore. Off by default. This\n" +
        "improves metastore perf for integral columns, especially if there's a large number of partitions.\n" +
        "However, it doesn't work correctly with integral values that are not normalized (e.g. have\n" +
        "leading zeroes, like 0012). If metastore direct SQL is enabled and works, this optimization\n" +
        "is also irrelevant."),
    METASTORE_TRY_DIRECT_SQL("hive.metastore.try.direct.sql", true,
        "Whether the Hive metastore should try to use direct SQL queries instead of the\n" +
        "DataNucleus for certain read paths. This can improve metastore performance when\n" +
        "fetching many partitions or column statistics by orders of magnitude; however, it\n" +
        "is not guaranteed to work on all RDBMS-es and all versions. In case of SQL failures,\n" +
        "the metastore will fall back to the DataNucleus, so it's safe even if SQL doesn't\n" +
        "work for all queries on your datastore. If all SQL queries fail (for example, your\n" +
        "metastore is backed by MongoDB), you might want to disable this to save the\n" +
        "try-and-fall-back cost."),
    METASTORE_DIRECT_SQL_PARTITION_BATCH_SIZE("hive.metastore.direct.sql.batch.size", 0,
        "Batch size for partition and other object retrieval from the underlying DB in direct\n" +
        "SQL. For some DBs like Oracle and MSSQL, there are hardcoded or perf-based limitations\n" +
        "that necessitate this. For DBs that can handle the queries, this isn't necessary and\n" +
        "may impede performance. -1 means no batching, 0 means automatic batching."),
    METASTORE_TRY_DIRECT_SQL_DDL("hive.metastore.try.direct.sql.ddl", true,
        "Same as hive.metastore.try.direct.sql, for read statements within a transaction that\n" +
        "modifies metastore data. Due to non-standard behavior in Postgres, if a direct SQL\n" +
        "select query has incorrect syntax or something similar inside a transaction, the\n" +
        "entire transaction will fail and fall-back to DataNucleus will not be possible. You\n" +
        "should disable the usage of direct SQL inside transactions if that happens in your case."),
    METASTORE_ORM_RETRIEVE_MAPNULLS_AS_EMPTY_STRINGS("hive.metastore.orm.retrieveMapNullsAsEmptyStrings",false,
        "Thrift does not support nulls in maps, so any nulls present in maps retrieved from ORM must " +
        "either be pruned or converted to empty strings. Some backing dbs such as Oracle persist empty strings " +
        "as nulls, so we should set this parameter if we wish to reverse that behaviour. For others, " +
        "pruning is the correct behaviour"),
    METASTORE_DISALLOW_INCOMPATIBLE_COL_TYPE_CHANGES(
        "hive.metastore.disallow.incompatible.col.type.changes", false,
        "If true (default is false), ALTER TABLE operations which change the type of a\n" +
        "column (say STRING) to an incompatible type (say MAP) are disallowed.\n" +
        "RCFile default SerDe (ColumnarSerDe) serializes the values in such a way that the\n" +
        "datatypes can be converted from string to any type. The map is also serialized as\n" +
        "a string, which can be read as a string as well. However, with any binary\n" +
        "serialization, this is not true. Blocking the ALTER TABLE prevents ClassCastExceptions\n" +
        "when subsequently trying to access old partitions.\n" +
        "\n" +
        "Primitive types like INT, STRING, BIGINT, etc., are compatible with each other and are\n" +
        "not blocked.\n" +
        "\n" +
        "See HIVE-4409 for more details."),

    NEWTABLEDEFAULTPARA("hive.table.parameters.default", "",
        "Default property values for newly created tables"),
    DDL_CTL_PARAMETERS_WHITELIST("hive.ddl.createtablelike.properties.whitelist", "",
        "Table Properties to copy over when executing a Create Table Like."),
    METASTORE_RAW_STORE_IMPL("hive.metastore.rawstore.impl", "org.apache.hadoop.hive.metastore.ObjectStore",
        "Name of the class that implements org.apache.hadoop.hive.metastore.rawstore interface. \n" +
        "This class is used to store and retrieval of raw metadata objects such as table, database"),
    METASTORE_CONNECTION_DRIVER("javax.jdo.option.ConnectionDriverName", "org.apache.derby.jdbc.EmbeddedDriver",
        "Driver class name for a JDBC metastore"),
    METASTORE_MANAGER_FACTORY_CLASS("javax.jdo.PersistenceManagerFactoryClass",
        "org.datanucleus.api.jdo.JDOPersistenceManagerFactory",
        "class implementing the jdo persistence"),
    METASTORE_EXPRESSION_PROXY_CLASS("hive.metastore.expression.proxy",
        "org.apache.hadoop.hive.ql.optimizer.ppr.PartitionExpressionForMetastore", ""),
    METASTORE_DETACH_ALL_ON_COMMIT("javax.jdo.option.DetachAllOnCommit", true,
        "Detaches all objects from session so that they can be used after transaction is committed"),
    METASTORE_NON_TRANSACTIONAL_READ("javax.jdo.option.NonTransactionalRead", true,
        "Reads outside of transactions"),
    METASTORE_CONNECTION_USER_NAME("javax.jdo.option.ConnectionUserName", "APP",
        "Username to use against metastore database"),
    METASTORE_END_FUNCTION_LISTENERS("hive.metastore.end.function.listeners", "",
        "List of comma separated listeners for the end of metastore functions."),
    METASTORE_PART_INHERIT_TBL_PROPS("hive.metastore.partition.inherit.table.properties", "",
        "List of comma separated keys occurring in table properties which will get inherited to newly created partitions. \n" +
        "* implies all the keys will get inherited."),
    METASTORE_FILTER_HOOK("hive.metastore.filter.hook", "org.apache.hadoop.hive.metastore.DefaultMetaStoreFilterHookImpl",
        "Metastore hook class for filtering the metadata read results. If hive.security.authorization.manager"
        + "is set to instance of HiveAuthorizerFactory, then this value is ignored."),
    FIRE_EVENTS_FOR_DML("hive.metastore.dml.events", false, "If true, the metastore will be asked" +
        " to fire events for DML operations"),
    METASTORE_CLIENT_DROP_PARTITIONS_WITH_EXPRESSIONS("hive.metastore.client.drop.partitions.using.expressions", true,
        "Choose whether dropping partitions with HCatClient pushes the partition-predicate to the metastore, " +
            "or drops partitions iteratively"),

    METASTORE_AGGREGATE_STATS_CACHE_ENABLED("hive.metastore.aggregate.stats.cache.enabled", true,
        "Whether aggregate stats caching is enabled or not."),
    METASTORE_AGGREGATE_STATS_CACHE_SIZE("hive.metastore.aggregate.stats.cache.size", 10000,
        "Maximum number of aggregate stats nodes that we will place in the metastore aggregate stats cache."),
    METASTORE_AGGREGATE_STATS_CACHE_MAX_PARTITIONS("hive.metastore.aggregate.stats.cache.max.partitions", 10000,
        "Maximum number of partitions that are aggregated per cache node."),
    METASTORE_AGGREGATE_STATS_CACHE_FPP("hive.metastore.aggregate.stats.cache.fpp", (float) 0.01,
        "Maximum false positive probability for the Bloom Filter used in each aggregate stats cache node (default 1%)."),
    METASTORE_AGGREGATE_STATS_CACHE_MAX_VARIANCE("hive.metastore.aggregate.stats.cache.max.variance", (float) 0.01,
        "Maximum tolerable variance in number of partitions between a cached node and our request (default 1%)."),
    METASTORE_AGGREGATE_STATS_CACHE_TTL("hive.metastore.aggregate.stats.cache.ttl", "600s", new TimeValidator(TimeUnit.SECONDS),
        "Number of seconds for a cached node to be active in the cache before they become stale."),
    METASTORE_AGGREGATE_STATS_CACHE_MAX_WRITER_WAIT("hive.metastore.aggregate.stats.cache.max.writer.wait", "5000ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Number of milliseconds a writer will wait to acquire the writelock before giving up."),
    METASTORE_AGGREGATE_STATS_CACHE_MAX_READER_WAIT("hive.metastore.aggregate.stats.cache.max.reader.wait", "1000ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Number of milliseconds a reader will wait to acquire the readlock before giving up."),
    METASTORE_AGGREGATE_STATS_CACHE_MAX_FULL("hive.metastore.aggregate.stats.cache.max.full", (float) 0.9,
        "Maximum cache full % after which the cache cleaner thread kicks in."),
    METASTORE_AGGREGATE_STATS_CACHE_CLEAN_UNTIL("hive.metastore.aggregate.stats.cache.clean.until", (float) 0.8,
        "The cleaner thread cleans until cache reaches this % full size."),
    METASTORE_METRICS("hive.metastore.metrics.enabled", false, "Enable metrics on the metastore."),

    // Parameters for exporting metadata on table drop (requires the use of the)
    // org.apache.hadoop.hive.ql.parse.MetaDataExportListener preevent listener
    METADATA_EXPORT_LOCATION("hive.metadata.export.location", "",
        "When used in conjunction with the org.apache.hadoop.hive.ql.parse.MetaDataExportListener pre event listener, \n" +
        "it is the location to which the metadata will be exported. The default is an empty string, which results in the \n" +
        "metadata being exported to the current user's home directory on HDFS."),
    MOVE_EXPORTED_METADATA_TO_TRASH("hive.metadata.move.exported.metadata.to.trash", true,
        "When used in conjunction with the org.apache.hadoop.hive.ql.parse.MetaDataExportListener pre event listener, \n" +
        "this setting determines if the metadata that is exported will subsequently be moved to the user's trash directory \n" +
        "alongside the dropped table data. This ensures that the metadata will be cleaned up along with the dropped table data."),

    // CLI
    CLIIGNOREERRORS("hive.cli.errors.ignore", false, ""),
    CLIPRINTCURRENTDB("hive.cli.print.current.db", false,
        "Whether to include the current database in the Hive prompt."),
    CLIPROMPT("hive.cli.prompt", "hive",
        "Command line prompt configuration value. Other hiveconf can be used in this configuration value. \n" +
        "Variable substitution will only be invoked at the Hive CLI startup."),
    CLIPRETTYOUTPUTNUMCOLS("hive.cli.pretty.output.num.cols", -1,
        "The number of columns to use when formatting output generated by the DESCRIBE PRETTY table_name command.\n" +
        "If the value of this property is -1, then Hive will use the auto-detected terminal width."),

    HIVE_METASTORE_FS_HANDLER_CLS("hive.metastore.fs.handler.class", "org.apache.hadoop.hive.metastore.HiveMetaStoreFsImpl", ""),

    // Things we log in the jobconf

    // session identifier
    HIVESESSIONID("hive.session.id", "", ""),
    // whether session is running in silent mode or not
    HIVESESSIONSILENT("hive.session.silent", false, ""),

    HIVE_SESSION_HISTORY_ENABLED("hive.session.history.enabled", false,
        "Whether to log Hive query, query plan, runtime statistics etc."),

    HIVEQUERYSTRING("hive.query.string", "",
        "Query being executed (might be multiple per a session)"),

    HIVEQUERYID("hive.query.id", "",
        "ID for query being executed (might be multiple per a session)"),

    HIVEJOBNAMELENGTH("hive.jobname.length", 50, "max jobname length"),

    // hive jar
    HIVEJAR("hive.jar.path", "",
        "The location of hive_cli.jar that is used when submitting jobs in a separate jvm."),
    HIVEAUXJARS("hive.aux.jars.path", "",
        "The location of the plugin jars that contain implementations of user defined functions and serdes."),

    // reloadable jars
    HIVERELOADABLEJARS("hive.reloadable.aux.jars.path", "",
        "Jars can be renewed by executing reload command. And these jars can be "
            + "used as the auxiliary classes like creating a UDF or SerDe."),

    // hive added files and jars
    HIVEADDEDFILES("hive.added.files.path", "", "This an internal parameter."),
    HIVEADDEDJARS("hive.added.jars.path", "", "This an internal parameter."),
    HIVEADDEDARCHIVES("hive.added.archives.path", "", "This an internal parameter."),

    HIVE_CURRENT_DATABASE("hive.current.database", "", "Database name used by current session. Internal usage only.", true),

    // for hive script operator
    HIVES_AUTO_PROGRESS_TIMEOUT("hive.auto.progress.timeout", "0s",
        new TimeValidator(TimeUnit.SECONDS),
        "How long to run autoprogressor for the script/UDTF operators.\n" +
        "Set to 0 for forever."),
    HIVESCRIPTAUTOPROGRESS("hive.script.auto.progress", false,
        "Whether Hive Transform/Map/Reduce Clause should automatically send progress information to TaskTracker \n" +
        "to avoid the task getting killed because of inactivity.  Hive sends progress information when the script is \n" +
        "outputting to stderr.  This option removes the need of periodically producing stderr messages, \n" +
        "but users should be cautious because this may prevent infinite loops in the scripts to be killed by TaskTracker."),
    HIVESCRIPTIDENVVAR("hive.script.operator.id.env.var", "HIVE_SCRIPT_OPERATOR_ID",
        "Name of the environment variable that holds the unique script operator ID in the user's \n" +
        "transform function (the custom mapper/reducer that the user has specified in the query)"),
    HIVESCRIPTTRUNCATEENV("hive.script.operator.truncate.env", false,
        "Truncate each environment variable for external script in scripts operator to 20KB (to fit system limits)"),
    HIVESCRIPT_ENV_BLACKLIST("hive.script.operator.env.blacklist",
        "hive.txn.valid.txns,hive.script.operator.env.blacklist",
        "Comma separated list of keys from the configuration file not to convert to environment " +
        "variables when envoking the script operator"),
    HIVEMAPREDMODE("hive.mapred.mode", "nonstrict",
        "The mode in which the Hive operations are being performed. \n" +
        "In strict mode, some risky queries are not allowed to run. They include:\n" +
        "  Cartesian Product.\n" +
        "  No partition being picked up for a query.\n" +
        "  Comparing bigints and strings.\n" +
        "  Comparing bigints and doubles.\n" +
        "  Orderby without limit."),
    HIVEALIAS("hive.alias", "", ""),
    HIVEMAPSIDEAGGREGATE("hive.map.aggr", true, "Whether to use map-side aggregation in Hive Group By queries"),
    HIVEGROUPBYSKEW("hive.groupby.skewindata", false, "Whether there is skew in data to optimize group by queries"),
    HIVEJOINEMITINTERVAL("hive.join.emit.interval", 1000,
        "How many rows in the right-most join operand Hive should buffer before emitting the join result."),
    HIVEJOINCACHESIZE("hive.join.cache.size", 25000,
        "How many rows in the joining tables (except the streaming table) should be cached in memory."),

    // CBO related
    HIVE_CBO_ENABLED("hive.cbo.enable", true, "Flag to control enabling Cost Based Optimizations using Calcite framework."),
    HIVE_CBO_RETPATH_HIVEOP("hive.cbo.returnpath.hiveop", false, "Flag to control calcite plan to hive operator conversion"),
    HIVE_CBO_EXTENDED_COST_MODEL("hive.cbo.costmodel.extended", false, "Flag to control enabling the extended cost model based on"
                                 + "CPU, IO and cardinality. Otherwise, the cost model is based on cardinality."),
    HIVE_CBO_COST_MODEL_CPU("hive.cbo.costmodel.cpu", "0.000001", "Default cost of a comparison"),
    HIVE_CBO_COST_MODEL_NET("hive.cbo.costmodel.network", "150.0", "Default cost of a transfering a byte over network;"
                                                                  + " expressed as multiple of CPU cost"),
    HIVE_CBO_COST_MODEL_LFS_WRITE("hive.cbo.costmodel.local.fs.write", "4.0", "Default cost of writing a byte to local FS;"
                                                                             + " expressed as multiple of NETWORK cost"),
    HIVE_CBO_COST_MODEL_LFS_READ("hive.cbo.costmodel.local.fs.read", "4.0", "Default cost of reading a byte from local FS;"
                                                                           + " expressed as multiple of NETWORK cost"),
    HIVE_CBO_COST_MODEL_HDFS_WRITE("hive.cbo.costmodel.hdfs.write", "10.0", "Default cost of writing a byte to HDFS;"
                                                                 + " expressed as multiple of Local FS write cost"),
    HIVE_CBO_COST_MODEL_HDFS_READ("hive.cbo.costmodel.hdfs.read", "1.5", "Default cost of reading a byte from HDFS;"
                                                                 + " expressed as multiple of Local FS read cost"),


    // hive.mapjoin.bucket.cache.size has been replaced by hive.smbjoin.cache.row,
    // need to remove by hive .13. Also, do not change default (see SMB operator)
    HIVEMAPJOINBUCKETCACHESIZE("hive.mapjoin.bucket.cache.size", 100, ""),

    HIVEMAPJOINUSEOPTIMIZEDTABLE("hive.mapjoin.optimized.hashtable", true,
        "Whether Hive should use memory-optimized hash table for MapJoin. Only works on Tez,\n" +
        "because memory-optimized hashtable cannot be serialized."),
    HIVEUSEHYBRIDGRACEHASHJOIN("hive.mapjoin.hybridgrace.hashtable", true, "Whether to use hybrid" +
        "grace hash join as the join method for mapjoin. Tez only."),
    HIVEHYBRIDGRACEHASHJOINMEMCHECKFREQ("hive.mapjoin.hybridgrace.memcheckfrequency", 1024, "For " +
        "hybrid grace hash join, how often (how many rows apart) we check if memory is full. " +
        "This number should be power of 2."),
    HIVEHYBRIDGRACEHASHJOINMINWBSIZE("hive.mapjoin.hybridgrace.minwbsize", 524288, "For hybrid grace" +
        "Hash join, the minimum write buffer size used by optimized hashtable. Default is 512 KB."),
    HIVEHYBRIDGRACEHASHJOINMINNUMPARTITIONS("hive.mapjoin.hybridgrace.minnumpartitions", 16, "For" +
        "Hybrid grace hash join, the minimum number of partitions to create."),
    HIVEHASHTABLEWBSIZE("hive.mapjoin.optimized.hashtable.wbsize", 8 * 1024 * 1024,
        "Optimized hashtable (see hive.mapjoin.optimized.hashtable) uses a chain of buffers to\n" +
        "store data. This is one buffer size. HT may be slightly faster if this is larger, but for small\n" +
        "joins unnecessary memory will be allocated and then trimmed."),

    HIVESMBJOINCACHEROWS("hive.smbjoin.cache.rows", 10000,
        "How many rows with the same key value should be cached in memory per smb joined table."),
    HIVEGROUPBYMAPINTERVAL("hive.groupby.mapaggr.checkinterval", 100000,
        "Number of rows after which size of the grouping keys/aggregation classes is performed"),
    HIVEMAPAGGRHASHMEMORY("hive.map.aggr.hash.percentmemory", (float) 0.5,
        "Portion of total memory to be used by map-side group aggregation hash table"),
    HIVEMAPJOINFOLLOWEDBYMAPAGGRHASHMEMORY("hive.mapjoin.followby.map.aggr.hash.percentmemory", (float) 0.3,
        "Portion of total memory to be used by map-side group aggregation hash table, when this group by is followed by map join"),
    HIVEMAPAGGRMEMORYTHRESHOLD("hive.map.aggr.hash.force.flush.memory.threshold", (float) 0.9,
        "The max memory to be used by map-side group aggregation hash table.\n" +
        "If the memory usage is higher than this number, force to flush data"),
    HIVEMAPAGGRHASHMINREDUCTION("hive.map.aggr.hash.min.reduction", (float) 0.5,
        "Hash aggregation will be turned off if the ratio between hash  table size and input rows is bigger than this number. \n" +
        "Set to 1 to make sure hash aggregation is never turned off."),
    HIVEMULTIGROUPBYSINGLEREDUCER("hive.multigroupby.singlereducer", true,
        "Whether to optimize multi group by query to generate single M/R  job plan. If the multi group by query has \n" +
        "common group by keys, it will be optimized to generate single M/R job."),
    HIVE_MAP_GROUPBY_SORT("hive.map.groupby.sorted", false,
        "If the bucketing/sorting properties of the table exactly match the grouping key, whether to perform \n" +
        "the group by in the mapper by using BucketizedHiveInputFormat. The only downside to this\n" +
        "is that it limits the number of mappers to the number of files."),
    HIVE_MAP_GROUPBY_SORT_TESTMODE("hive.map.groupby.sorted.testmode", false,
        "If the bucketing/sorting properties of the table exactly match the grouping key, whether to perform \n" +
        "the group by in the mapper by using BucketizedHiveInputFormat. If the test mode is set, the plan\n" +
        "is not converted, but a query property is set to denote the same."),
    HIVE_GROUPBY_ORDERBY_POSITION_ALIAS("hive.groupby.orderby.position.alias", false,
        "Whether to enable using Column Position Alias in Group By or Order By"),
    HIVE_NEW_JOB_GROUPING_SET_CARDINALITY("hive.new.job.grouping.set.cardinality", 30,
        "Whether a new map-reduce job should be launched for grouping sets/rollups/cubes.\n" +
        "For a query like: select a, b, c, count(1) from T group by a, b, c with rollup;\n" +
        "4 rows are created per row: (a, b, c), (a, b, null), (a, null, null), (null, null, null).\n" +
        "This can lead to explosion across map-reduce boundary if the cardinality of T is very high,\n" +
        "and map-side aggregation does not do a very good job. \n" +
        "\n" +
        "This parameter decides if Hive should add an additional map-reduce job. If the grouping set\n" +
        "cardinality (4 in the example above), is more than this value, a new MR job is added under the\n" +
        "assumption that the original group by will reduce the data size."),

    // Max filesize used to do a single copy (after that, distcp is used)
    HIVE_EXEC_COPYFILE_MAXSIZE("hive.exec.copyfile.maxsize", 32L * 1024 * 1024 /*32M*/,
        "Maximum file size (in Mb) that Hive uses to do single HDFS copies between directories." +
        "Distributed copies (distcp) will be used instead for bigger files so that copies can be done faster."),

    // for hive udtf operator
    HIVEUDTFAUTOPROGRESS("hive.udtf.auto.progress", false,
        "Whether Hive should automatically send progress information to TaskTracker \n" +
        "when using UDTF's to prevent the task getting killed because of inactivity.  Users should be cautious \n" +
        "because this may prevent TaskTracker from killing tasks with infinite loops."),

    HIVEDEFAULTFILEFORMAT("hive.default.fileformat", "TextFile", new StringSet("TextFile", "SequenceFile", "RCfile", "ORC"),
        "Default file format for CREATE TABLE statement. Users can explicitly override it by CREATE TABLE ... STORED AS [FORMAT]"),
    HIVEDEFAULTMANAGEDFILEFORMAT("hive.default.fileformat.managed", "none",
	new StringSet("none", "TextFile", "SequenceFile", "RCfile", "ORC"),
	"Default file format for CREATE TABLE statement applied to managed tables only. External tables will be \n" +
	"created with format specified by hive.default.fileformat. Leaving this null will result in using hive.default.fileformat \n" +
	"for all tables."),
    HIVEQUERYRESULTFILEFORMAT("hive.query.result.fileformat", "TextFile", new StringSet("TextFile", "SequenceFile", "RCfile"),
        "Default file format for storing result of the query."),
    HIVECHECKFILEFORMAT("hive.fileformat.check", true, "Whether to check file format or not when loading data files"),

    // default serde for rcfile
    HIVEDEFAULTRCFILESERDE("hive.default.rcfile.serde",
        "org.apache.hadoop.hive.serde2.columnar.LazyBinaryColumnarSerDe",
        "The default SerDe Hive will use for the RCFile format"),

    HIVEDEFAULTSERDE("hive.default.serde",
        "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
        "The default SerDe Hive will use for storage formats that do not specify a SerDe."),

    SERDESUSINGMETASTOREFORSCHEMA("hive.serdes.using.metastore.for.schema",
        "org.apache.hadoop.hive.ql.io.orc.OrcSerde,org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe," +
        "org.apache.hadoop.hive.serde2.columnar.ColumnarSerDe,org.apache.hadoop.hive.serde2.dynamic_type.DynamicSerDe," +
        "org.apache.hadoop.hive.serde2.MetadataTypedColumnsetSerDe,org.apache.hadoop.hive.serde2.columnar.LazyBinaryColumnarSerDe," +
        "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe,org.apache.hadoop.hive.serde2.lazybinary.LazyBinarySerDe",
        "SerDes retriving schema from metastore. This an internal parameter. Check with the hive dev. team"),

    HIVEHISTORYFILELOC("hive.querylog.location",
        "${system:java.io.tmpdir}" + File.separator + "${system:user.name}",
        "Location of Hive run time structured log file"),

    HIVE_LOG_INCREMENTAL_PLAN_PROGRESS("hive.querylog.enable.plan.progress", true,
        "Whether to log the plan's progress every time a job's progress is checked.\n" +
        "These logs are written to the location specified by hive.querylog.location"),

    HIVE_LOG_INCREMENTAL_PLAN_PROGRESS_INTERVAL("hive.querylog.plan.progress.interval", "60000ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "The interval to wait between logging the plan's progress.\n" +
        "If there is a whole number percentage change in the progress of the mappers or the reducers,\n" +
        "the progress is logged regardless of this value.\n" +
        "The actual interval will be the ceiling of (this value divided by the value of\n" +
        "hive.exec.counters.pull.interval) multiplied by the value of hive.exec.counters.pull.interval\n" +
        "I.e. if it is not divide evenly by the value of hive.exec.counters.pull.interval it will be\n" +
        "logged less frequently than specified.\n" +
        "This only has an effect if hive.querylog.enable.plan.progress is set to true."),

    HIVESCRIPTSERDE("hive.script.serde", "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
        "The default SerDe for transmitting input data to and reading output data from the user scripts. "),
    HIVESCRIPTRECORDREADER("hive.script.recordreader",
        "org.apache.hadoop.hive.ql.exec.TextRecordReader",
        "The default record reader for reading data from the user scripts. "),
    HIVESCRIPTRECORDWRITER("hive.script.recordwriter",
        "org.apache.hadoop.hive.ql.exec.TextRecordWriter",
        "The default record writer for writing data to the user scripts. "),
    HIVESCRIPTESCAPE("hive.transform.escape.input", false,
        "This adds an option to escape special chars (newlines, carriage returns and\n" +
        "tabs) when they are passed to the user script. This is useful if the Hive tables\n" +
        "can contain data that contains special characters."),
    HIVEBINARYRECORDMAX("hive.binary.record.max.length", 1000,
        "Read from a binary stream and treat each hive.binary.record.max.length bytes as a record. \n" +
        "The last record before the end of stream can have less than hive.binary.record.max.length bytes"),

    // HWI
    HIVEHWILISTENHOST("hive.hwi.listen.host", "0.0.0.0", "This is the host address the Hive Web Interface will listen on"),
    HIVEHWILISTENPORT("hive.hwi.listen.port", "9999", "This is the port the Hive Web Interface will listen on"),
    HIVEHWIWARFILE("hive.hwi.war.file", "${env:HWI_WAR_FILE}",
        "This sets the path to the HWI war file, relative to ${HIVE_HOME}. "),

    HIVEHADOOPMAXMEM("hive.mapred.local.mem", 0, "mapper/reducer memory in local mode"),

    //small table file size
    HIVESMALLTABLESFILESIZE("hive.mapjoin.smalltable.filesize", 25000000L,
        "The threshold for the input file size of the small tables; if the file size is smaller \n" +
        "than this threshold, it will try to convert the common join into map join"),

    HIVESAMPLERANDOMNUM("hive.sample.seednumber", 0,
        "A number used to percentage sampling. By changing this number, user will change the subsets of data sampled."),

    // test mode in hive mode
    HIVETESTMODE("hive.test.mode", false,
        "Whether Hive is running in test mode. If yes, it turns on sampling and prefixes the output tablename.",
        false),
    HIVETESTMODEPREFIX("hive.test.mode.prefix", "test_",
        "In test mode, specfies prefixes for the output table", false),
    HIVETESTMODESAMPLEFREQ("hive.test.mode.samplefreq", 32,
        "In test mode, specfies sampling frequency for table, which is not bucketed,\n" +
        "For example, the following query:\n" +
        "  INSERT OVERWRITE TABLE dest SELECT col1 from src\n" +
        "would be converted to\n" +
        "  INSERT OVERWRITE TABLE test_dest\n" +
        "  SELECT col1 from src TABLESAMPLE (BUCKET 1 out of 32 on rand(1))", false),
    HIVETESTMODENOSAMPLE("hive.test.mode.nosamplelist", "",
        "In test mode, specifies comma separated table names which would not apply sampling", false),
    HIVETESTMODEDUMMYSTATAGGR("hive.test.dummystats.aggregator", "", "internal variable for test", false),
    HIVETESTMODEDUMMYSTATPUB("hive.test.dummystats.publisher", "", "internal variable for test", false),
    HIVETESTCURRENTTIMESTAMP("hive.test.currenttimestamp", null, "current timestamp for test", false),

    HIVEMERGEMAPFILES("hive.merge.mapfiles", true,
        "Merge small files at the end of a map-only job"),
    HIVEMERGEMAPREDFILES("hive.merge.mapredfiles", false,
        "Merge small files at the end of a map-reduce job"),
    HIVEMERGETEZFILES("hive.merge.tezfiles", false, "Merge small files at the end of a Tez DAG"),
    HIVEMERGESPARKFILES("hive.merge.sparkfiles", false, "Merge small files at the end of a Spark DAG Transformation"),
    HIVEMERGEMAPFILESSIZE("hive.merge.size.per.task", (long) (256 * 1000 * 1000),
        "Size of merged files at the end of the job"),
    HIVEMERGEMAPFILESAVGSIZE("hive.merge.smallfiles.avgsize", (long) (16 * 1000 * 1000),
        "When the average output file size of a job is less than this number, Hive will start an additional \n" +
        "map-reduce job to merge the output files into bigger files. This is only done for map-only jobs \n" +
        "if hive.merge.mapfiles is true, and for map-reduce jobs if hive.merge.mapredfiles is true."),
    HIVEMERGERCFILEBLOCKLEVEL("hive.merge.rcfile.block.level", true, ""),
    HIVEMERGEORCFILESTRIPELEVEL("hive.merge.orcfile.stripe.level", true,
        "When hive.merge.mapfiles, hive.merge.mapredfiles or hive.merge.tezfiles is enabled\n" +
        "while writing a table with ORC file format, enabling this config will do stripe-level\n" +
        "fast merge for small ORC files. Note that enabling this config will not honor the\n" +
        "padding tolerance config (hive.exec.orc.block.padding.tolerance)."),

    HIVEUSEEXPLICITRCFILEHEADER("hive.exec.rcfile.use.explicit.header", true,
        "If this is set the header for RCFiles will simply be RCF.  If this is not\n" +
        "set the header will be that borrowed from sequence files, e.g. SEQ- followed\n" +
        "by the input and output RCFile formats."),
    HIVEUSERCFILESYNCCACHE("hive.exec.rcfile.use.sync.cache", true, ""),

    HIVE_RCFILE_RECORD_INTERVAL("hive.io.rcfile.record.interval", Integer.MAX_VALUE, ""),
    HIVE_RCFILE_COLUMN_NUMBER_CONF("hive.io.rcfile.column.number.conf", 0, ""),
    HIVE_RCFILE_TOLERATE_CORRUPTIONS("hive.io.rcfile.tolerate.corruptions", false, ""),
    HIVE_RCFILE_RECORD_BUFFER_SIZE("hive.io.rcfile.record.buffer.size", 4194304, ""),   // 4M

    PARQUET_MEMORY_POOL_RATIO("parquet.memory.pool.ratio", 0.5f,
        "Maximum fraction of heap that can be used by Parquet file writers in one task.\n" +
        "It is for avoiding OutOfMemory error in tasks. Work with Parquet 1.6.0 and above.\n" +
        "This config parameter is defined in Parquet, so that it does not start with 'hive.'."),
    HIVE_PARQUET_TIMESTAMP_SKIP_CONVERSION("hive.parquet.timestamp.skip.conversion", true,
      "Current Hive implementation of parquet stores timestamps to UTC, this flag allows skipping of the conversion" +
      "on reading parquet files from other tools"),
    HIVE_INT_TIMESTAMP_CONVERSION_IN_SECONDS("hive.int.timestamp.conversion.in.seconds", false,
        "Boolean/tinyint/smallint/int/bigint value is interpreted as milliseconds during the timestamp conversion.\n" +
        "Set this flag to true to interpret the value as seconds to be consistent with float/double." ),
    HIVE_ORC_FILE_MEMORY_POOL("hive.exec.orc.memory.pool", 0.5f,
        "Maximum fraction of heap that can be used by ORC file writers"),
    HIVE_ORC_WRITE_FORMAT("hive.exec.orc.write.format", null,
        "Define the version of the file to write. Possible values are 0.11 and 0.12.\n" +
        "If this parameter is not defined, ORC will use the run length encoding (RLE)\n" +
        "introduced in Hive 0.12. Any value other than 0.11 results in the 0.12 encoding."),
    HIVE_ORC_DEFAULT_STRIPE_SIZE("hive.exec.orc.default.stripe.size",
        64L * 1024 * 1024,
        "Define the default ORC stripe size, in bytes."),
    HIVE_ORC_DEFAULT_BLOCK_SIZE("hive.exec.orc.default.block.size", 256L * 1024 * 1024,
        "Define the default file system block size for ORC files."),

    HIVE_ORC_DICTIONARY_KEY_SIZE_THRESHOLD("hive.exec.orc.dictionary.key.size.threshold", 0.8f,
        "If the number of keys in a dictionary is greater than this fraction of the total number of\n" +
        "non-null rows, turn off dictionary encoding.  Use 1 to always use dictionary encoding."),
    HIVE_ORC_DEFAULT_ROW_INDEX_STRIDE("hive.exec.orc.default.row.index.stride", 10000,
        "Define the default ORC index stride in number of rows. (Stride is the number of rows\n" +
        "an index entry represents.)"),
    HIVE_ORC_ROW_INDEX_STRIDE_DICTIONARY_CHECK("hive.orc.row.index.stride.dictionary.check", true,
        "If enabled dictionary check will happen after first row index stride (default 10000 rows)\n" +
        "else dictionary check will happen before writing first stripe. In both cases, the decision\n" +
        "to use dictionary or not will be retained thereafter."),
    HIVE_ORC_DEFAULT_BUFFER_SIZE("hive.exec.orc.default.buffer.size", 256 * 1024,
        "Define the default ORC buffer size, in bytes."),
    HIVE_ORC_DEFAULT_BLOCK_PADDING("hive.exec.orc.default.block.padding", true,
        "Define the default block padding, which pads stripes to the HDFS block boundaries."),
    HIVE_ORC_BLOCK_PADDING_TOLERANCE("hive.exec.orc.block.padding.tolerance", 0.05f,
        "Define the tolerance for block padding as a decimal fraction of stripe size (for\n" +
        "example, the default value 0.05 is 5% of the stripe size). For the defaults of 64Mb\n" +
        "ORC stripe and 256Mb HDFS blocks, the default block padding tolerance of 5% will\n" +
        "reserve a maximum of 3.2Mb for padding within the 256Mb block. In that case, if the\n" +
        "available size within the block is more than 3.2Mb, a new smaller stripe will be\n" +
        "inserted to fit within that space. This will make sure that no stripe written will\n" +
        "cross block boundaries and cause remote reads within a node local task."),
    HIVE_ORC_DEFAULT_COMPRESS("hive.exec.orc.default.compress", "ZLIB", "Define the default compression codec for ORC file"),

    HIVE_ORC_ENCODING_STRATEGY("hive.exec.orc.encoding.strategy", "SPEED", new StringSet("SPEED", "COMPRESSION"),
        "Define the encoding strategy to use while writing data. Changing this will\n" +
        "only affect the light weight encoding for integers. This flag will not\n" +
        "change the compression level of higher level compression codec (like ZLIB)."),

    HIVE_ORC_COMPRESSION_STRATEGY("hive.exec.orc.compression.strategy", "SPEED", new StringSet("SPEED", "COMPRESSION"),
         "Define the compression strategy to use while writing data. \n" +
         "This changes the compression level of higher level compression codec (like ZLIB)."),

    HIVE_ORC_SPLIT_STRATEGY("hive.exec.orc.split.strategy", "HYBRID", new StringSet("HYBRID", "BI", "ETL"),
        "This is not a user level config. BI strategy is used when the requirement is to spend less time in split generation" +
        " as opposed to query execution (split generation does not read or cache file footers)." +
        " ETL strategy is used when spending little more time in split generation is acceptable" +
        " (split generation reads and caches file footers). HYBRID chooses between the above strategies" +
        " based on heuristics."),

    HIVE_ORC_INCLUDE_FILE_FOOTER_IN_SPLITS("hive.orc.splits.include.file.footer", false,
        "If turned on splits generated by orc will include metadata about the stripes in the file. This\n" +
        "data is read remotely (from the client or HS2 machine) and sent to all the tasks."),
    HIVE_ORC_CACHE_STRIPE_DETAILS_SIZE("hive.orc.cache.stripe.details.size", 10000,
        "Max cache size for keeping meta info about orc splits cached in the client."),
    HIVE_ORC_COMPUTE_SPLITS_NUM_THREADS("hive.orc.compute.splits.num.threads", 10,
        "How many threads orc should use to create splits in parallel."),
    HIVE_ORC_SKIP_CORRUPT_DATA("hive.exec.orc.skip.corrupt.data", false,
        "If ORC reader encounters corrupt data, this value will be used to determine\n" +
        "whether to skip the corrupt data or throw exception. The default behavior is to throw exception."),

    HIVE_ORC_ZEROCOPY("hive.exec.orc.zerocopy", false,
        "Use zerocopy reads with ORC. (This requires Hadoop 2.3 or later.)"),

    HIVE_LAZYSIMPLE_EXTENDED_BOOLEAN_LITERAL("hive.lazysimple.extended_boolean_literal", false,
        "LazySimpleSerde uses this property to determine if it treats 'T', 't', 'F', 'f',\n" +
        "'1', and '0' as extened, legal boolean literal, in addition to 'TRUE' and 'FALSE'.\n" +
        "The default is false, which means only 'TRUE' and 'FALSE' are treated as legal\n" +
        "boolean literal."),

    HIVESKEWJOIN("hive.optimize.skewjoin", false,
        "Whether to enable skew join optimization. \n" +
        "The algorithm is as follows: At runtime, detect the keys with a large skew. Instead of\n" +
        "processing those keys, store them temporarily in an HDFS directory. In a follow-up map-reduce\n" +
        "job, process those skewed keys. The same key need not be skewed for all the tables, and so,\n" +
        "the follow-up map-reduce job (for the skewed keys) would be much faster, since it would be a\n" +
        "map-join."),
    HIVECONVERTJOIN("hive.auto.convert.join", true,
        "Whether Hive enables the optimization about converting common join into mapjoin based on the input file size"),
    HIVECONVERTJOINNOCONDITIONALTASK("hive.auto.convert.join.noconditionaltask", true,
        "Whether Hive enables the optimization about converting common join into mapjoin based on the input file size. \n" +
        "If this parameter is on, and the sum of size for n-1 of the tables/partitions for a n-way join is smaller than the\n" +
        "specified size, the join is directly converted to a mapjoin (there is no conditional task)."),

    HIVECONVERTJOINNOCONDITIONALTASKTHRESHOLD("hive.auto.convert.join.noconditionaltask.size",
        10000000L,
        "If hive.auto.convert.join.noconditionaltask is off, this parameter does not take affect. \n" +
        "However, if it is on, and the sum of size for n-1 of the tables/partitions for a n-way join is smaller than this size, \n" +
        "the join is directly converted to a mapjoin(there is no conditional task). The default is 10MB"),
    HIVECONVERTJOINUSENONSTAGED("hive.auto.convert.join.use.nonstaged", false,
        "For conditional joins, if input stream from a small alias can be directly applied to join operator without \n" +
        "filtering or projection, the alias need not to be pre-staged in distributed cache via mapred local task.\n" +
        "Currently, this is not working with vectorization or tez execution engine."),
    HIVESKEWJOINKEY("hive.skewjoin.key", 100000,
        "Determine if we get a skew key in join. If we see more than the specified number of rows with the same key in join operator,\n" +
        "we think the key as a skew join key. "),
    HIVESKEWJOINMAPJOINNUMMAPTASK("hive.skewjoin.mapjoin.map.tasks", 10000,
        "Determine the number of map task used in the follow up map join job for a skew join.\n" +
        "It should be used together with hive.skewjoin.mapjoin.min.split to perform a fine grained control."),
    HIVESKEWJOINMAPJOINMINSPLIT("hive.skewjoin.mapjoin.min.split", 33554432L,
        "Determine the number of map task at most used in the follow up map join job for a skew join by specifying \n" +
        "the minimum split size. It should be used together with hive.skewjoin.mapjoin.map.tasks to perform a fine grained control."),

    HIVESENDHEARTBEAT("hive.heartbeat.interval", 1000,
        "Send a heartbeat after this interval - used by mapjoin and filter operators"),
    HIVELIMITMAXROWSIZE("hive.limit.row.max.size", 100000L,
        "When trying a smaller subset of data for simple LIMIT, how much size we need to guarantee each row to have at least."),
    HIVELIMITOPTLIMITFILE("hive.limit.optimize.limit.file", 10,
        "When trying a smaller subset of data for simple LIMIT, maximum number of files we can sample."),
    HIVELIMITOPTENABLE("hive.limit.optimize.enable", false,
        "Whether to enable to optimization to trying a smaller subset of data for simple LIMIT first."),
    HIVELIMITOPTMAXFETCH("hive.limit.optimize.fetch.max", 50000,
        "Maximum number of rows allowed for a smaller subset of data for simple LIMIT, if it is a fetch query. \n" +
        "Insert queries are not restricted by this limit."),
    HIVELIMITPUSHDOWNMEMORYUSAGE("hive.limit.pushdown.memory.usage", -1f,
        "The max memory to be used for hash in RS operator for top K selection."),
    HIVELIMITTABLESCANPARTITION("hive.limit.query.max.table.partition", -1,
        "This controls how many partitions can be scanned for each partitioned table.\n" +
        "The default value \"-1\" means no limit."),

    HIVEHASHTABLEKEYCOUNTADJUSTMENT("hive.hashtable.key.count.adjustment", 1.0f,
        "Adjustment to mapjoin hashtable size derived from table and column statistics; the estimate" +
        " of the number of keys is divided by this value. If the value is 0, statistics are not used" +
        "and hive.hashtable.initialCapacity is used instead."),
    HIVEHASHTABLETHRESHOLD("hive.hashtable.initialCapacity", 100000, "Initial capacity of " +
        "mapjoin hashtable if statistics are absent, or if hive.hashtable.stats.key.estimate.adjustment is set to 0"),
    HIVEHASHTABLELOADFACTOR("hive.hashtable.loadfactor", (float) 0.75, ""),
    HIVEHASHTABLEFOLLOWBYGBYMAXMEMORYUSAGE("hive.mapjoin.followby.gby.localtask.max.memory.usage", (float) 0.55,
        "This number means how much memory the local task can take to hold the key/value into an in-memory hash table \n" +
        "when this map join is followed by a group by. If the local task's memory usage is more than this number, \n" +
        "the local task will abort by itself. It means the data of the small table is too large to be held in memory."),
    HIVEHASHTABLEMAXMEMORYUSAGE("hive.mapjoin.localtask.max.memory.usage", (float) 0.90,
        "This number means how much memory the local task can take to hold the key/value into an in-memory hash table. \n" +
        "If the local task's memory usage is more than this number, the local task will abort by itself. \n" +
        "It means the data of the small table is too large to be held in memory."),
    HIVEHASHTABLESCALE("hive.mapjoin.check.memory.rows", (long)100000,
        "The number means after how many rows processed it needs to check the memory usage"),

    HIVEDEBUGLOCALTASK("hive.debug.localtask",false, ""),

    HIVEINPUTFORMAT("hive.input.format", "org.apache.hadoop.hive.ql.io.CombineHiveInputFormat",
        "The default input format. Set this to HiveInputFormat if you encounter problems with CombineHiveInputFormat."),
    HIVETEZINPUTFORMAT("hive.tez.input.format", "org.apache.hadoop.hive.ql.io.HiveInputFormat",
        "The default input format for tez. Tez groups splits in the AM."),

    HIVETEZCONTAINERSIZE("hive.tez.container.size", -1,
        "By default Tez will spawn containers of the size of a mapper. This can be used to overwrite."),
    HIVETEZCPUVCORES("hive.tez.cpu.vcores", -1,
        "By default Tez will ask for however many cpus map-reduce is configured to use per container.\n" +
        "This can be used to overwrite."),
    HIVETEZJAVAOPTS("hive.tez.java.opts", null,
        "By default Tez will use the Java options from map tasks. This can be used to overwrite."),
    HIVETEZLOGLEVEL("hive.tez.log.level", "INFO",
        "The log level to use for tasks executing as part of the DAG.\n" +
        "Used only if hive.tez.java.opts is used to configure Java options."),

    HIVEENFORCEBUCKETING("hive.enforce.bucketing", false,
        "Whether bucketing is enforced. If true, while inserting into the table, bucketing is enforced."),
    HIVEENFORCESORTING("hive.enforce.sorting", false,
        "Whether sorting is enforced. If true, while inserting into the table, sorting is enforced."),
    HIVEOPTIMIZEBUCKETINGSORTING("hive.optimize.bucketingsorting", true,
        "If hive.enforce.bucketing or hive.enforce.sorting is true, don't create a reducer for enforcing \n" +
        "bucketing/sorting for queries of the form: \n" +
        "insert overwrite table T2 select * from T1;\n" +
        "where T1 and T2 are bucketed/sorted by the same keys into the same number of buckets."),
    HIVEPARTITIONER("hive.mapred.partitioner", "org.apache.hadoop.hive.ql.io.DefaultHivePartitioner", ""),
    HIVEENFORCESORTMERGEBUCKETMAPJOIN("hive.enforce.sortmergebucketmapjoin", false,
        "If the user asked for sort-merge bucketed map-side join, and it cannot be performed, should the query fail or not ?"),
    HIVEENFORCEBUCKETMAPJOIN("hive.enforce.bucketmapjoin", false,
        "If the user asked for bucketed map-side join, and it cannot be performed, \n" +
        "should the query fail or not ? For example, if the buckets in the tables being joined are\n" +
        "not a multiple of each other, bucketed map-side join cannot be performed, and the\n" +
        "query will fail if hive.enforce.bucketmapjoin is set to true."),

    HIVE_AUTO_SORTMERGE_JOIN("hive.auto.convert.sortmerge.join", false,
        "Will the join be automatically converted to a sort-merge join, if the joined tables pass the criteria for sort-merge join."),
    HIVE_AUTO_SORTMERGE_JOIN_BIGTABLE_SELECTOR(
        "hive.auto.convert.sortmerge.join.bigtable.selection.policy",
        "org.apache.hadoop.hive.ql.optimizer.AvgPartitionSizeBasedBigTableSelectorForAutoSMJ",
        "The policy to choose the big table for automatic conversion to sort-merge join. \n" +
        "By default, the table with the largest partitions is assigned the big table. All policies are:\n" +
        ". based on position of the table - the leftmost table is selected\n" +
        "org.apache.hadoop.hive.ql.optimizer.LeftmostBigTableSMJ.\n" +
        ". based on total size (all the partitions selected in the query) of the table \n" +
        "org.apache.hadoop.hive.ql.optimizer.TableSizeBasedBigTableSelectorForAutoSMJ.\n" +
        ". based on average size (all the partitions selected in the query) of the table \n" +
        "org.apache.hadoop.hive.ql.optimizer.AvgPartitionSizeBasedBigTableSelectorForAutoSMJ.\n" +
        "New policies can be added in future."),
    HIVE_AUTO_SORTMERGE_JOIN_TOMAPJOIN(
        "hive.auto.convert.sortmerge.join.to.mapjoin", false,
        "If hive.auto.convert.sortmerge.join is set to true, and a join was converted to a sort-merge join, \n" +
        "this parameter decides whether each table should be tried as a big table, and effectively a map-join should be\n" +
        "tried. That would create a conditional task with n+1 children for a n-way join (1 child for each table as the\n" +
        "big table), and the backup task will be the sort-merge join. In some cases, a map-join would be faster than a\n" +
        "sort-merge join, if there is no advantage of having the output bucketed and sorted. For example, if a very big sorted\n" +
        "and bucketed table with few files (say 10 files) are being joined with a very small sorter and bucketed table\n" +
        "with few files (10 files), the sort-merge join will only use 10 mappers, and a simple map-only join might be faster\n" +
        "if the complete small table can fit in memory, and a map-join can be performed."),

    HIVESCRIPTOPERATORTRUST("hive.exec.script.trust", false, ""),
    HIVEROWOFFSET("hive.exec.rowoffset", false,
        "Whether to provide the row offset virtual column"),

    HIVE_COMBINE_INPUT_FORMAT_SUPPORTS_SPLITTABLE("hive.hadoop.supports.splittable.combineinputformat", false, ""),

    // Optimizer
    HIVEOPTINDEXFILTER("hive.optimize.index.filter", false,
        "Whether to enable automatic use of indexes"),
    HIVEINDEXAUTOUPDATE("hive.optimize.index.autoupdate", false,
        "Whether to update stale indexes automatically"),
    HIVEOPTPPD("hive.optimize.ppd", true,
        "Whether to enable predicate pushdown"),
    HIVEPPDRECOGNIZETRANSITIVITY("hive.ppd.recognizetransivity", true,
        "Whether to transitively replicate predicate filters over equijoin conditions."),
    HIVEPPDREMOVEDUPLICATEFILTERS("hive.ppd.remove.duplicatefilters", true,
        "Whether to push predicates down into storage handlers.  Ignored when hive.optimize.ppd is false."),
    // Constant propagation optimizer
    HIVEOPTCONSTANTPROPAGATION("hive.optimize.constant.propagation", true, "Whether to enable constant propagation optimizer"),
    HIVEIDENTITYPROJECTREMOVER("hive.optimize.remove.identity.project", true, "Removes identity project from operator tree"),
    HIVEMETADATAONLYQUERIES("hive.optimize.metadataonly", true, ""),
    HIVENULLSCANOPTIMIZE("hive.optimize.null.scan", true, "Dont scan relations which are guaranteed to not generate any rows"),
    HIVEOPTPPD_STORAGE("hive.optimize.ppd.storage", true,
        "Whether to push predicates down to storage handlers"),
    HIVEOPTGROUPBY("hive.optimize.groupby", true,
        "Whether to enable the bucketed group by from bucketed partitions/tables."),
    HIVEOPTBUCKETMAPJOIN("hive.optimize.bucketmapjoin", false,
        "Whether to try bucket mapjoin"),
    HIVEOPTSORTMERGEBUCKETMAPJOIN("hive.optimize.bucketmapjoin.sortedmerge", false,
        "Whether to try sorted bucket merge map join"),
    HIVEOPTREDUCEDEDUPLICATION("hive.optimize.reducededuplication", true,
        "Remove extra map-reduce jobs if the data is already clustered by the same key which needs to be used again. \n" +
        "This should always be set to true. Since it is a new feature, it has been made configurable."),
    HIVEOPTREDUCEDEDUPLICATIONMINREDUCER("hive.optimize.reducededuplication.min.reducer", 4,
        "Reduce deduplication merges two RSs by moving key/parts/reducer-num of the child RS to parent RS. \n" +
        "That means if reducer-num of the child RS is fixed (order by or forced bucketing) and small, it can make very slow, single MR.\n" +
        "The optimization will be automatically disabled if number of reducers would be less than specified value."),

    HIVEOPTSORTDYNAMICPARTITION("hive.optimize.sort.dynamic.partition", false,
        "When enabled dynamic partitioning column will be globally sorted.\n" +
        "This way we can keep only one record writer open for each partition value\n" +
        "in the reducer thereby reducing the memory pressure on reducers."),

    HIVESAMPLINGFORORDERBY("hive.optimize.sampling.orderby", false, "Uses sampling on order-by clause for parallel execution."),
    HIVESAMPLINGNUMBERFORORDERBY("hive.optimize.sampling.orderby.number", 1000, "Total number of samples to be obtained."),
    HIVESAMPLINGPERCENTFORORDERBY("hive.optimize.sampling.orderby.percent", 0.1f, new RatioValidator(),
        "Probability with which a row will be chosen."),
    HIVEOPTIMIZEDISTINCTREWRITE("hive.optimize.distinct.rewrite", true, "When applicable this "
        + "optimization rewrites distinct aggregates from a single stage to multi-stage "
        + "aggregation. This may not be optimal in all cases. Ideally, whether to trigger it or "
        + "not should be cost based decision. Until Hive formalizes cost model for this, this is config driven."),
    // whether to optimize union followed by select followed by filesink
    // It creates sub-directories in the final output, so should not be turned on in systems
    // where MAPREDUCE-1501 is not present
    HIVE_OPTIMIZE_UNION_REMOVE("hive.optimize.union.remove", false,
        "Whether to remove the union and push the operators between union and the filesink above union. \n" +
        "This avoids an extra scan of the output by union. This is independently useful for union\n" +
        "queries, and specially useful when hive.optimize.skewjoin.compiletime is set to true, since an\n" +
        "extra union is inserted.\n" +
        "\n" +
        "The merge is triggered if either of hive.merge.mapfiles or hive.merge.mapredfiles is set to true.\n" +
        "If the user has set hive.merge.mapfiles to true and hive.merge.mapredfiles to false, the idea was the\n" +
        "number of reducers are few, so the number of files anyway are small. However, with this optimization,\n" +
        "we are increasing the number of files possibly by a big margin. So, we merge aggressively."),
    HIVEOPTCORRELATION("hive.optimize.correlation", false, "exploit intra-query correlations."),

    HIVE_HADOOP_SUPPORTS_SUBDIRECTORIES("hive.mapred.supports.subdirectories", false,
        "Whether the version of Hadoop which is running supports sub-directories for tables/partitions. \n" +
        "Many Hive optimizations can be applied if the Hadoop version supports sub-directories for\n" +
        "tables/partitions. It was added by MAPREDUCE-1501"),

    HIVE_OPTIMIZE_SKEWJOIN_COMPILETIME("hive.optimize.skewjoin.compiletime", false,
        "Whether to create a separate plan for skewed keys for the tables in the join.\n" +
        "This is based on the skewed keys stored in the metadata. At compile time, the plan is broken\n" +
        "into different joins: one for the skewed keys, and the other for the remaining keys. And then,\n" +
        "a union is performed for the 2 joins generated above. So unless the same skewed key is present\n" +
        "in both the joined tables, the join for the skewed key will be performed as a map-side join.\n" +
        "\n" +
        "The main difference between this parameter and hive.optimize.skewjoin is that this parameter\n" +
        "uses the skew information stored in the metastore to optimize the plan at compile time itself.\n" +
        "If there is no skew information in the metadata, this parameter will not have any affect.\n" +
        "Both hive.optimize.skewjoin.compiletime and hive.optimize.skewjoin should be set to true.\n" +
        "Ideally, hive.optimize.skewjoin should be renamed as hive.optimize.skewjoin.runtime, but not doing\n" +
        "so for backward compatibility.\n" +
        "\n" +
        "If the skew information is correctly stored in the metadata, hive.optimize.skewjoin.compiletime\n" +
        "would change the query plan to take care of it, and hive.optimize.skewjoin will be a no-op."),

    // Indexes
    HIVEOPTINDEXFILTER_COMPACT_MINSIZE("hive.optimize.index.filter.compact.minsize", (long) 5 * 1024 * 1024 * 1024,
        "Minimum size (in bytes) of the inputs on which a compact index is automatically used."), // 5G
    HIVEOPTINDEXFILTER_COMPACT_MAXSIZE("hive.optimize.index.filter.compact.maxsize", (long) -1,
        "Maximum size (in bytes) of the inputs on which a compact index is automatically used.  A negative number is equivalent to infinity."), // infinity
    HIVE_INDEX_COMPACT_QUERY_MAX_ENTRIES("hive.index.compact.query.max.entries", (long) 10000000,
        "The maximum number of index entries to read during a query that uses the compact index. Negative value is equivalent to infinity."), // 10M
    HIVE_INDEX_COMPACT_QUERY_MAX_SIZE("hive.index.compact.query.max.size", (long) 10 * 1024 * 1024 * 1024,
        "The maximum number of bytes that a query using the compact index can read. Negative value is equivalent to infinity."), // 10G
    HIVE_INDEX_COMPACT_BINARY_SEARCH("hive.index.compact.binary.search", true,
        "Whether or not to use a binary search to find the entries in an index table that match the filter, where possible"),

    // Statistics
    HIVESTATSAUTOGATHER("hive.stats.autogather", true,
        "A flag to gather statistics automatically during the INSERT OVERWRITE command."),
    HIVESTATSDBCLASS("hive.stats.dbclass", "fs", new PatternSet("jdbc(:.*)", "hbase", "counter", "custom", "fs"),
        "The storage that stores temporary Hive statistics. In filesystem based statistics collection ('fs'), \n" +
        "each task writes statistics it has collected in a file on the filesystem, which will be aggregated \n" +
        "after the job has finished. Supported values are fs (filesystem), jdbc:database (where database \n" +
        "can be derby, mysql, etc.), hbase, counter, and custom as defined in StatsSetupConst.java."), // StatsSetupConst.StatDB
    HIVESTATSJDBCDRIVER("hive.stats.jdbcdriver",
        "org.apache.derby.jdbc.EmbeddedDriver",
        "The JDBC driver for the database that stores temporary Hive statistics."),
    HIVESTATSDBCONNECTIONSTRING("hive.stats.dbconnectionstring",
        "jdbc:derby:;databaseName=TempStatsStore;create=true",
        "The default connection string for the database that stores temporary Hive statistics."), // automatically create database
    HIVE_STATS_DEFAULT_PUBLISHER("hive.stats.default.publisher", "",
        "The Java class (implementing the StatsPublisher interface) that is used by default if hive.stats.dbclass is custom type."),
    HIVE_STATS_DEFAULT_AGGREGATOR("hive.stats.default.aggregator", "",
        "The Java class (implementing the StatsAggregator interface) that is used by default if hive.stats.dbclass is custom type."),
    HIVE_STATS_JDBC_TIMEOUT("hive.stats.jdbc.timeout", "30s", new TimeValidator(TimeUnit.SECONDS),
        "Timeout value used by JDBC connection and statements."),
    HIVE_STATS_ATOMIC("hive.stats.atomic", false,
        "whether to update metastore stats only if all stats are available"),
    HIVE_STATS_RETRIES_MAX("hive.stats.retries.max", 0,
        "Maximum number of retries when stats publisher/aggregator got an exception updating intermediate database. \n" +
        "Default is no tries on failures."),
    HIVE_STATS_RETRIES_WAIT("hive.stats.retries.wait", "3000ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "The base waiting window before the next retry. The actual wait time is calculated by " +
        "baseWindow * failures baseWindow * (failure + 1) * (random number between [0.0,1.0])."),
    HIVE_STATS_COLLECT_RAWDATASIZE("hive.stats.collect.rawdatasize", true,
        "should the raw data size be collected when analyzing tables"),
    CLIENT_STATS_COUNTERS("hive.client.stats.counters", "",
        "Subset of counters that should be of interest for hive.client.stats.publishers (when one wants to limit their publishing). \n" +
        "Non-display names should be used"),
    //Subset of counters that should be of interest for hive.client.stats.publishers (when one wants to limit their publishing). Non-display names should be used".
    HIVE_STATS_RELIABLE("hive.stats.reliable", false,
        "Whether queries will fail because stats cannot be collected completely accurately. \n" +
        "If this is set to true, reading/writing from/into a partition may fail because the stats\n" +
        "could not be computed accurately."),
    HIVE_STATS_COLLECT_PART_LEVEL_STATS("hive.analyze.stmt.collect.partlevel.stats", true,
        "analyze table T compute statistics for columns. Queries like these should compute partition"
        + "level stats for partitioned table even when no part spec is specified."),
    HIVE_STATS_GATHER_NUM_THREADS("hive.stats.gather.num.threads", 10,
        "Number of threads used by partialscan/noscan analyze command for partitioned tables.\n" +
        "This is applicable only for file formats that implement StatsProvidingRecordReader (like ORC)."),
    // Collect table access keys information for operators that can benefit from bucketing
    HIVE_STATS_COLLECT_TABLEKEYS("hive.stats.collect.tablekeys", false,
        "Whether join and group by keys on tables are derived and maintained in the QueryPlan.\n" +
        "This is useful to identify how tables are accessed and to determine if they should be bucketed."),
    // Collect column access information
    HIVE_STATS_COLLECT_SCANCOLS("hive.stats.collect.scancols", false,
        "Whether column accesses are tracked in the QueryPlan.\n" +
        "This is useful to identify how tables are accessed and to determine if there are wasted columns that can be trimmed."),
    // standard error allowed for ndv estimates. A lower value indicates higher accuracy and a
    // higher compute cost.
    HIVE_STATS_NDV_ERROR("hive.stats.ndv.error", (float)20.0,
        "Standard error expressed in percentage. Provides a tradeoff between accuracy and compute cost. \n" +
        "A lower value for error indicates higher accuracy and a higher compute cost."),
    HIVE_METASTORE_STATS_NDV_DENSITY_FUNCTION("hive.metastore.stats.ndv.densityfunction", false,
        "Whether to use density function to estimate the NDV for the whole table based on the NDV of partitions"),
    HIVE_STATS_KEY_PREFIX_MAX_LENGTH("hive.stats.key.prefix.max.length", 150,
        "Determines if when the prefix of the key used for intermediate stats collection\n" +
        "exceeds a certain length, a hash of the key is used instead.  If the value < 0 then hashing"),
    HIVE_STATS_KEY_PREFIX_RESERVE_LENGTH("hive.stats.key.prefix.reserve.length", 24,
        "Reserved length for postfix of stats key. Currently only meaningful for counter type which should\n" +
        "keep length of full stats key smaller than max length configured by hive.stats.key.prefix.max.length.\n" +
        "For counter type, it should be bigger than the length of LB spec if exists."),
    HIVE_STATS_KEY_PREFIX("hive.stats.key.prefix", "", "", true), // internal usage only
    // if length of variable length data type cannot be determined this length will be used.
    HIVE_STATS_MAX_VARIABLE_LENGTH("hive.stats.max.variable.length", 100,
        "To estimate the size of data flowing through operators in Hive/Tez(for reducer estimation etc.),\n" +
        "average row size is multiplied with the total number of rows coming out of each operator.\n" +
        "Average row size is computed from average column size of all columns in the row. In the absence\n" +
        "of column statistics, for variable length columns (like string, bytes etc.), this value will be\n" +
        "used. For fixed length columns their corresponding Java equivalent sizes are used\n" +
        "(float - 4 bytes, double - 8 bytes etc.)."),
    // if number of elements in list cannot be determined, this value will be used
    HIVE_STATS_LIST_NUM_ENTRIES("hive.stats.list.num.entries", 10,
        "To estimate the size of data flowing through operators in Hive/Tez(for reducer estimation etc.),\n" +
        "average row size is multiplied with the total number of rows coming out of each operator.\n" +
        "Average row size is computed from average column size of all columns in the row. In the absence\n" +
        "of column statistics and for variable length complex columns like list, the average number of\n" +
        "entries/values can be specified using this config."),
    // if number of elements in map cannot be determined, this value will be used
    HIVE_STATS_MAP_NUM_ENTRIES("hive.stats.map.num.entries", 10,
        "To estimate the size of data flowing through operators in Hive/Tez(for reducer estimation etc.),\n" +
        "average row size is multiplied with the total number of rows coming out of each operator.\n" +
        "Average row size is computed from average column size of all columns in the row. In the absence\n" +
        "of column statistics and for variable length complex columns like map, the average number of\n" +
        "entries/values can be specified using this config."),
    // statistics annotation fetches stats for each partition, which can be expensive. turning
    // this off will result in basic sizes being fetched from namenode instead
    HIVE_STATS_FETCH_PARTITION_STATS("hive.stats.fetch.partition.stats", true,
        "Annotation of operator tree with statistics information requires partition level basic\n" +
        "statistics like number of rows, data size and file size. Partition statistics are fetched from\n" +
        "metastore. Fetching partition statistics for each needed partition can be expensive when the\n" +
        "number of partitions is high. This flag can be used to disable fetching of partition statistics\n" +
        "from metastore. When this flag is disabled, Hive will make calls to filesystem to get file sizes\n" +
        "and will estimate the number of rows from row schema."),
    // statistics annotation fetches column statistics for all required columns which can
    // be very expensive sometimes
    HIVE_STATS_FETCH_COLUMN_STATS("hive.stats.fetch.column.stats", false,
        "Annotation of operator tree with statistics information requires column statistics.\n" +
        "Column statistics are fetched from metastore. Fetching column statistics for each needed column\n" +
        "can be expensive when the number of columns is high. This flag can be used to disable fetching\n" +
        "of column statistics from metastore."),
    // in the absence of column statistics, the estimated number of rows/data size that will
    // be emitted from join operator will depend on this factor
    HIVE_STATS_JOIN_FACTOR("hive.stats.join.factor", (float) 1.1,
        "Hive/Tez optimizer estimates the data size flowing through each of the operators. JOIN operator\n" +
        "uses column statistics to estimate the number of rows flowing out of it and hence the data size.\n" +
        "In the absence of column statistics, this factor determines the amount of rows that flows out\n" +
        "of JOIN operator."),
    // in the absence of uncompressed/raw data size, total file size will be used for statistics
    // annotation. But the file may be compressed, encoded and serialized which may be lesser in size
    // than the actual uncompressed/raw data size. This factor will be multiplied to file size to estimate
    // the raw data size.
    HIVE_STATS_DESERIALIZATION_FACTOR("hive.stats.deserialization.factor", (float) 1.0,
        "Hive/Tez optimizer estimates the data size flowing through each of the operators. In the absence\n" +
        "of basic statistics like number of rows and data size, file size is used to estimate the number\n" +
        "of rows and data size. Since files in tables/partitions are serialized (and optionally\n" +
        "compressed) the estimates of number of rows and data size cannot be reliably determined.\n" +
        "This factor is multiplied with the file size to account for serialization and compression."),

    // Concurrency
    HIVE_SUPPORT_CONCURRENCY("hive.support.concurrency", false,
        "Whether Hive supports concurrency control or not. \n" +
        "A ZooKeeper instance must be up and running when using zookeeper Hive lock manager "),
    HIVE_LOCK_MANAGER("hive.lock.manager", "org.apache.hadoop.hive.ql.lockmgr.zookeeper.ZooKeeperHiveLockManager", ""),
    HIVE_LOCK_NUMRETRIES("hive.lock.numretries", 100,
        "The number of times you want to try to get all the locks"),
    HIVE_UNLOCK_NUMRETRIES("hive.unlock.numretries", 10,
        "The number of times you want to retry to do one unlock"),
    HIVE_LOCK_SLEEP_BETWEEN_RETRIES("hive.lock.sleep.between.retries", "60s",
        new TimeValidator(TimeUnit.SECONDS),
        "The sleep time between various retries"),
    HIVE_LOCK_MAPRED_ONLY("hive.lock.mapred.only.operation", false,
        "This param is to control whether or not only do lock on queries\n" +
        "that need to execute at least one mapred job."),

     // Zookeeper related configs
    HIVE_ZOOKEEPER_QUORUM("hive.zookeeper.quorum", "",
        "List of ZooKeeper servers to talk to. This is needed for: \n" +
        "1. Read/write locks - when hive.lock.manager is set to \n" +
        "org.apache.hadoop.hive.ql.lockmgr.zookeeper.ZooKeeperHiveLockManager, \n" +
        "2. When HiveServer2 supports service discovery via Zookeeper.\n" +
        "3. For delegation token storage if zookeeper store is used, if\n" +
        "hive.cluster.delegation.token.store.zookeeper.connectString is not set"),

    HIVE_ZOOKEEPER_CLIENT_PORT("hive.zookeeper.client.port", "2181",
        "The port of ZooKeeper servers to talk to.\n" +
        "If the list of Zookeeper servers specified in hive.zookeeper.quorum\n" +
        "does not contain port numbers, this value is used."),
    HIVE_ZOOKEEPER_SESSION_TIMEOUT("hive.zookeeper.session.timeout", "1200000ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "ZooKeeper client's session timeout (in milliseconds). The client is disconnected, and as a result, all locks released, \n" +
        "if a heartbeat is not sent in the timeout."),
    HIVE_ZOOKEEPER_NAMESPACE("hive.zookeeper.namespace", "hive_zookeeper_namespace",
        "The parent node under which all ZooKeeper nodes are created."),
    HIVE_ZOOKEEPER_CLEAN_EXTRA_NODES("hive.zookeeper.clean.extra.nodes", false,
        "Clean extra nodes at the end of the session."),
    HIVE_ZOOKEEPER_CONNECTION_MAX_RETRIES("hive.zookeeper.connection.max.retries", 3,
        "Max number of times to retry when connecting to the ZooKeeper server."),
    HIVE_ZOOKEEPER_CONNECTION_BASESLEEPTIME("hive.zookeeper.connection.basesleeptime", "1000ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Initial amount of time (in milliseconds) to wait between retries\n" +
        "when connecting to the ZooKeeper server when using ExponentialBackoffRetry policy."),

    // Transactions
    HIVE_TXN_MANAGER("hive.txn.manager",
        "org.apache.hadoop.hive.ql.lockmgr.DummyTxnManager",
        "Set to org.apache.hadoop.hive.ql.lockmgr.DbTxnManager as part of turning on Hive\n" +
        "transactions, which also requires appropriate settings for hive.compactor.initiator.on,\n" +
        "hive.compactor.worker.threads, hive.support.concurrency (true), hive.enforce.bucketing\n" +
        "(true), and hive.exec.dynamic.partition.mode (nonstrict).\n" +
        "The default DummyTxnManager replicates pre-Hive-0.13 behavior and provides\n" +
        "no transactions."),
    HIVE_TXN_TIMEOUT("hive.txn.timeout", "300s", new TimeValidator(TimeUnit.SECONDS),
        "time after which transactions are declared aborted if the client has not sent a heartbeat."),

    HIVE_TXN_MAX_OPEN_BATCH("hive.txn.max.open.batch", 1000,
        "Maximum number of transactions that can be fetched in one call to open_txns().\n" +
        "This controls how many transactions streaming agents such as Flume or Storm open\n" +
        "simultaneously. The streaming agent then writes that number of entries into a single\n" +
        "file (per Flume agent or Storm bolt). Thus increasing this value decreases the number\n" +
        "of delta files created by streaming agents. But it also increases the number of open\n" +
        "transactions that Hive has to track at any given time, which may negatively affect\n" +
        "read performance."),

    HIVE_COMPACTOR_INITIATOR_ON("hive.compactor.initiator.on", false,
        "Whether to run the initiator and cleaner threads on this metastore instance or not.\n" +
        "Set this to true on one instance of the Thrift metastore service as part of turning\n" +
        "on Hive transactions. For a complete list of parameters required for turning on\n" +
        "transactions, see hive.txn.manager."),

    HIVE_COMPACTOR_WORKER_THREADS("hive.compactor.worker.threads", 0,
        "How many compactor worker threads to run on this metastore instance. Set this to a\n" +
        "positive number on one or more instances of the Thrift metastore service as part of\n" +
        "turning on Hive transactions. For a complete list of parameters required for turning\n" +
        "on transactions, see hive.txn.manager.\n" +
        "Worker threads spawn MapReduce jobs to do compactions. They do not do the compactions\n" +
        "themselves. Increasing the number of worker threads will decrease the time it takes\n" +
        "tables or partitions to be compacted once they are determined to need compaction.\n" +
        "It will also increase the background load on the Hadoop cluster as more MapReduce jobs\n" +
        "will be running in the background."),

    HIVE_COMPACTOR_WORKER_TIMEOUT("hive.compactor.worker.timeout", "86400s",
        new TimeValidator(TimeUnit.SECONDS),
        "Time in seconds after which a compaction job will be declared failed and the\n" +
        "compaction re-queued."),

    HIVE_COMPACTOR_CHECK_INTERVAL("hive.compactor.check.interval", "300s",
        new TimeValidator(TimeUnit.SECONDS),
        "Time in seconds between checks to see if any tables or partitions need to be\n" +
        "compacted. This should be kept high because each check for compaction requires\n" +
        "many calls against the NameNode.\n" +
        "Decreasing this value will reduce the time it takes for compaction to be started\n" +
        "for a table or partition that requires compaction. However, checking if compaction\n" +
        "is needed requires several calls to the NameNode for each table or partition that\n" +
        "has had a transaction done on it since the last major compaction. So decreasing this\n" +
        "value will increase the load on the NameNode."),

    HIVE_COMPACTOR_DELTA_NUM_THRESHOLD("hive.compactor.delta.num.threshold", 10,
        "Number of delta directories in a table or partition that will trigger a minor\n" +
        "compaction."),

    HIVE_COMPACTOR_DELTA_PCT_THRESHOLD("hive.compactor.delta.pct.threshold", 0.1f,
        "Percentage (fractional) size of the delta files relative to the base that will trigger\n" +
        "a major compaction. (1.0 = 100%, so the default 0.1 = 10%.)"),

    HIVE_COMPACTOR_ABORTEDTXN_THRESHOLD("hive.compactor.abortedtxn.threshold", 1000,
        "Number of aborted transactions involving a given table or partition that will trigger\n" +
        "a major compaction."),

    HIVE_COMPACTOR_CLEANER_RUN_INTERVAL("hive.compactor.cleaner.run.interval", "5000ms",
        new TimeValidator(TimeUnit.MILLISECONDS), "Time between runs of the cleaner thread"),

    // For HBase storage handler
    HIVE_HBASE_WAL_ENABLED("hive.hbase.wal.enabled", true,
        "Whether writes to HBase should be forced to the write-ahead log. \n" +
        "Disabling this improves HBase write performance at the risk of lost writes in case of a crash."),
    HIVE_HBASE_GENERATE_HFILES("hive.hbase.generatehfiles", false,
        "True when HBaseStorageHandler should generate hfiles instead of operate against the online table."),
    HIVE_HBASE_SNAPSHOT_NAME("hive.hbase.snapshot.name", null, "The HBase table snapshot name to use."),
    HIVE_HBASE_SNAPSHOT_RESTORE_DIR("hive.hbase.snapshot.restoredir", "/tmp", "The directory in which to " +
        "restore the HBase table snapshot."),

    // For har files
    HIVEARCHIVEENABLED("hive.archive.enabled", false, "Whether archiving operations are permitted"),

    HIVEOPTGBYUSINGINDEX("hive.optimize.index.groupby", false,
        "Whether to enable optimization of group-by queries using Aggregate indexes."),

    HIVEOUTERJOINSUPPORTSFILTERS("hive.outerjoin.supports.filters", true, ""),

    HIVEFETCHTASKCONVERSION("hive.fetch.task.conversion", "more", new StringSet("none", "minimal", "more"),
        "Some select queries can be converted to single FETCH task minimizing latency.\n" +
        "Currently the query should be single sourced not having any subquery and should not have\n" +
        "any aggregations or distincts (which incurs RS), lateral views and joins.\n" +
        "0. none : disable hive.fetch.task.conversion\n" +
        "1. minimal : SELECT STAR, FILTER on partition columns, LIMIT only\n" +
        "2. more    : SELECT, FILTER, LIMIT only (support TABLESAMPLE and virtual columns)"
    ),
    HIVEFETCHTASKCONVERSIONTHRESHOLD("hive.fetch.task.conversion.threshold", 1073741824L,
        "Input threshold for applying hive.fetch.task.conversion. If target table is native, input length\n" +
        "is calculated by summation of file lengths. If it's not native, storage handler for the table\n" +
        "can optionally implement org.apache.hadoop.hive.ql.metadata.InputEstimator interface."),

    HIVEFETCHTASKAGGR("hive.fetch.task.aggr", false,
        "Aggregation queries with no group-by clause (for example, select count(*) from src) execute\n" +
        "final aggregations in single reduce task. If this is set true, Hive delegates final aggregation\n" +
        "stage to fetch task, possibly decreasing the query time."),

    HIVEOPTIMIZEMETADATAQUERIES("hive.compute.query.using.stats", false,
        "When set to true Hive will answer a few queries like count(1) purely using stats\n" +
        "stored in metastore. For basic stats collection turn on the config hive.stats.autogather to true.\n" +
        "For more advanced stats collection need to run analyze table queries."),

    // Serde for FetchTask
    HIVEFETCHOUTPUTSERDE("hive.fetch.output.serde", "org.apache.hadoop.hive.serde2.DelimitedJSONSerDe",
        "The SerDe used by FetchTask to serialize the fetch output."),

    HIVEEXPREVALUATIONCACHE("hive.cache.expr.evaluation", true,
        "If true, the evaluation result of a deterministic expression referenced twice or more\n" +
        "will be cached.\n" +
        "For example, in a filter condition like '.. where key + 10 = 100 or key + 10 = 0'\n" +
        "the expression 'key + 10' will be evaluated/cached once and reused for the following\n" +
        "expression ('key + 10 = 0'). Currently, this is applied only to expressions in select\n" +
        "or filter operators."),

    // Hive Variables
    HIVEVARIABLESUBSTITUTE("hive.variable.substitute", true,
        "This enables substitution using syntax like ${var} ${system:var} and ${env:var}."),
    HIVEVARIABLESUBSTITUTEDEPTH("hive.variable.substitute.depth", 40,
        "The maximum replacements the substitution engine will do."),

    HIVECONFVALIDATION("hive.conf.validation", true,
        "Enables type checking for registered Hive configurations"),

    SEMANTIC_ANALYZER_HOOK("hive.semantic.analyzer.hook", "", ""),
    HIVE_TEST_AUTHORIZATION_SQLSTD_HS2_MODE(
        "hive.test.authz.sstd.hs2.mode", false, "test hs2 mode from .q tests", true),
    HIVE_AUTHORIZATION_ENABLED("hive.security.authorization.enabled", false,
        "enable or disable the Hive client authorization"),
    HIVE_AUTHORIZATION_MANAGER("hive.security.authorization.manager",
        "org.apache.hadoop.hive.ql.security.authorization.DefaultHiveAuthorizationProvider",
        "The Hive client authorization manager class name. The user defined authorization class should implement \n" +
        "interface org.apache.hadoop.hive.ql.security.authorization.HiveAuthorizationProvider."),
    HIVE_AUTHENTICATOR_MANAGER("hive.security.authenticator.manager",
        "org.apache.hadoop.hive.ql.security.HadoopDefaultAuthenticator",
        "hive client authenticator manager class name. The user defined authenticator should implement \n" +
        "interface org.apache.hadoop.hive.ql.security.HiveAuthenticationProvider."),
    HIVE_METASTORE_AUTHORIZATION_MANAGER("hive.security.metastore.authorization.manager",
        "org.apache.hadoop.hive.ql.security.authorization.DefaultHiveMetastoreAuthorizationProvider",
        "Names of authorization manager classes (comma separated) to be used in the metastore\n" +
        "for authorization. The user defined authorization class should implement interface\n" +
        "org.apache.hadoop.hive.ql.security.authorization.HiveMetastoreAuthorizationProvider.\n" +
        "All authorization manager classes have to successfully authorize the metastore API\n" +
        "call for the command execution to be allowed."),
    HIVE_METASTORE_AUTHORIZATION_AUTH_READS("hive.security.metastore.authorization.auth.reads", true,
        "If this is true, metastore authorizer authorizes read actions on database, table"),
    HIVE_METASTORE_AUTHENTICATOR_MANAGER("hive.security.metastore.authenticator.manager",
        "org.apache.hadoop.hive.ql.security.HadoopDefaultMetastoreAuthenticator",
        "authenticator manager class name to be used in the metastore for authentication. \n" +
        "The user defined authenticator should implement interface org.apache.hadoop.hive.ql.security.HiveAuthenticationProvider."),
    HIVE_AUTHORIZATION_TABLE_USER_GRANTS("hive.security.authorization.createtable.user.grants", "",
        "the privileges automatically granted to some users whenever a table gets created.\n" +
        "An example like \"userX,userY:select;userZ:create\" will grant select privilege to userX and userY,\n" +
        "and grant create privilege to userZ whenever a new table created."),
    HIVE_AUTHORIZATION_TABLE_GROUP_GRANTS("hive.security.authorization.createtable.group.grants",
        "",
        "the privileges automatically granted to some groups whenever a table gets created.\n" +
        "An example like \"groupX,groupY:select;groupZ:create\" will grant select privilege to groupX and groupY,\n" +
        "and grant create privilege to groupZ whenever a new table created."),
    HIVE_AUTHORIZATION_TABLE_ROLE_GRANTS("hive.security.authorization.createtable.role.grants", "",
        "the privileges automatically granted to some roles whenever a table gets created.\n" +
        "An example like \"roleX,roleY:select;roleZ:create\" will grant select privilege to roleX and roleY,\n" +
        "and grant create privilege to roleZ whenever a new table created."),
    HIVE_AUTHORIZATION_TABLE_OWNER_GRANTS("hive.security.authorization.createtable.owner.grants",
        "",
        "The privileges automatically granted to the owner whenever a table gets created.\n" +
        "An example like \"select,drop\" will grant select and drop privilege to the owner\n" +
        "of the table. Note that the default gives the creator of a table no access to the\n" +
        "table (but see HIVE-8067)."),
    HIVE_AUTHORIZATION_TASK_FACTORY("hive.security.authorization.task.factory",
        "org.apache.hadoop.hive.ql.parse.authorization.HiveAuthorizationTaskFactoryImpl",
        "Authorization DDL task factory implementation"),

    // if this is not set default value is set during config initialization
    // Default value can't be set in this constructor as it would refer names in other ConfVars
    // whose constructor would not have been called
    HIVE_AUTHORIZATION_SQL_STD_AUTH_CONFIG_WHITELIST(
        "hive.security.authorization.sqlstd.confwhitelist", "",
        "List of comma separated Java regexes. Configurations parameters that match these\n" +
        "regexes can be modified by user when SQL standard authorization is enabled.\n" +
        "To get the default value, use the 'set <param>' command.\n" +
        "Note that the hive.conf.restricted.list checks are still enforced after the white list\n" +
        "check"),

    HIVE_AUTHORIZATION_SQL_STD_AUTH_CONFIG_WHITELIST_APPEND(
        "hive.security.authorization.sqlstd.confwhitelist.append", "",
        "List of comma separated Java regexes, to be appended to list set in\n" +
        "hive.security.authorization.sqlstd.confwhitelist. Using this list instead\n" +
        "of updating the original list means that you can append to the defaults\n" +
        "set by SQL standard authorization instead of replacing it entirely."),

    HIVE_CLI_PRINT_HEADER("hive.cli.print.header", false, "Whether to print the names of the columns in query output."),

    HIVE_ERROR_ON_EMPTY_PARTITION("hive.error.on.empty.partition", false,
        "Whether to throw an exception if dynamic partition insert generates empty results."),

    HIVE_INDEX_COMPACT_FILE("hive.index.compact.file", "", "internal variable"),
    HIVE_INDEX_BLOCKFILTER_FILE("hive.index.blockfilter.file", "", "internal variable"),
    HIVE_INDEX_IGNORE_HDFS_LOC("hive.index.compact.file.ignore.hdfs", false,
        "When true the HDFS location stored in the index file will be ignored at runtime.\n" +
        "If the data got moved or the name of the cluster got changed, the index data should still be usable."),

    HIVE_EXIM_URI_SCHEME_WL("hive.exim.uri.scheme.whitelist", "hdfs,pfile",
        "A comma separated list of acceptable URI schemes for import and export."),
    // temporary variable for testing. This is added just to turn off this feature in case of a bug in
    // deployment. It has not been documented in hive-default.xml intentionally, this should be removed
    // once the feature is stable
    HIVE_EXIM_RESTRICT_IMPORTS_INTO_REPLICATED_TABLES("hive.exim.strict.repl.tables",true,
        "Parameter that determines if 'regular' (non-replication) export dumps can be\n" +
        "imported on to tables that are the target of replication. If this parameter is\n" +
        "set, regular imports will check if the destination table(if it exists) has a " +
        "'repl.last.id' set on it. If so, it will fail."),
    HIVE_REPL_TASK_FACTORY("hive.repl.task.factory",
        "org.apache.hive.hcatalog.api.repl.exim.EximReplicationTaskFactory",
        "Parameter that can be used to override which ReplicationTaskFactory will be\n" +
        "used to instantiate ReplicationTask events. Override for third party repl plugins"),
    HIVE_MAPPER_CANNOT_SPAN_MULTIPLE_PARTITIONS("hive.mapper.cannot.span.multiple.partitions", false, ""),
    HIVE_REWORK_MAPREDWORK("hive.rework.mapredwork", false,
        "should rework the mapred work or not.\n" +
        "This is first introduced by SymlinkTextInputFormat to replace symlink files with real paths at compile time."),
    HIVE_CONCATENATE_CHECK_INDEX ("hive.exec.concatenate.check.index", true,
        "If this is set to true, Hive will throw error when doing\n" +
        "'alter table tbl_name [partSpec] concatenate' on a table/partition\n" +
        "that has indexes on it. The reason the user want to set this to true\n" +
        "is because it can help user to avoid handling all index drop, recreation,\n" +
        "rebuild work. This is very helpful for tables with thousands of partitions."),
    HIVE_IO_EXCEPTION_HANDLERS("hive.io.exception.handlers", "",
        "A list of io exception handler class names. This is used\n" +
        "to construct a list exception handlers to handle exceptions thrown\n" +
        "by record readers"),

    // operation log configuration
    HIVE_SERVER2_LOGGING_OPERATION_ENABLED("hive.server2.logging.operation.enabled", true,
        "When true, HS2 will save operation logs and make them available for clients"),
    HIVE_SERVER2_LOGGING_OPERATION_LOG_LOCATION("hive.server2.logging.operation.log.location",
        "${system:java.io.tmpdir}" + File.separator + "${system:user.name}" + File.separator +
            "operation_logs",
        "Top level directory where operation logs are stored if logging functionality is enabled"),
    HIVE_SERVER2_LOGGING_OPERATION_LEVEL("hive.server2.logging.operation.level", "EXECUTION",
        new StringSet("NONE", "EXECUTION", "PERFORMANCE", "VERBOSE"),
        "HS2 operation logging mode available to clients to be set at session level.\n" +
        "For this to work, hive.server2.logging.operation.enabled should be set to true.\n" +
        "  NONE: Ignore any logging\n" +
        "  EXECUTION: Log completion of tasks\n" +
        "  PERFORMANCE: Execution + Performance logs \n" +
        "  VERBOSE: All logs" ),
    HIVE_SERVER2_METRICS_ENABLED("hive.server2.metrics.enabled", false, "Enable metrics on the HiveServer2."),
    // logging configuration
    HIVE_LOG4J_FILE("hive.log4j.file", "",
        "Hive log4j configuration file.\n" +
        "If the property is not set, then logging will be initialized using hive-log4j.properties found on the classpath.\n" +
        "If the property is set, the value must be a valid URI (java.net.URI, e.g. \"file:///tmp/my-logging.properties\"), \n" +
        "which you can then extract a URL from and pass to PropertyConfigurator.configure(URL)."),
    HIVE_EXEC_LOG4J_FILE("hive.exec.log4j.file", "",
        "Hive log4j configuration file for execution mode(sub command).\n" +
        "If the property is not set, then logging will be initialized using hive-exec-log4j.properties found on the classpath.\n" +
        "If the property is set, the value must be a valid URI (java.net.URI, e.g. \"file:///tmp/my-logging.properties\"), \n" +
        "which you can then extract a URL from and pass to PropertyConfigurator.configure(URL)."),

    HIVE_LOG_EXPLAIN_OUTPUT("hive.log.explain.output", false,
        "Whether to log explain output for every query.\n" +
        "When enabled, will log EXPLAIN EXTENDED output for the query at INFO log4j log level."),
    HIVE_EXPLAIN_USER("hive.explain.user", false,
        "Whether to show explain result at user level.\n" +
        "When enabled, will log EXPLAIN output for the query at user level."),

    // prefix used to auto generated column aliases (this should be started with '_')
    HIVE_AUTOGEN_COLUMNALIAS_PREFIX_LABEL("hive.autogen.columnalias.prefix.label", "_c",
        "String used as a prefix when auto generating column alias.\n" +
        "By default the prefix label will be appended with a column position number to form the column alias. \n" +
        "Auto generation would happen if an aggregate function is used in a select clause without an explicit alias."),
    HIVE_AUTOGEN_COLUMNALIAS_PREFIX_INCLUDEFUNCNAME(
        "hive.autogen.columnalias.prefix.includefuncname", false,
        "Whether to include function name in the column alias auto generated by Hive."),
    HIVE_METRICS_CLASS("hive.service.metrics.class",
        "org.apache.hadoop.hive.common.metrics.metrics2.CodahaleMetrics",
        new StringSet(
            "org.apache.hadoop.hive.common.metrics.metrics2.CodahaleMetrics",
            "org.apache.hadoop.hive.common.metrics.LegacyMetrics"),
        "Hive metrics subsystem implementation class."),
    HIVE_METRICS_REPORTER("hive.service.metrics.reporter", "JSON_FILE, JMX",
        "Reporter type for metric class org.apache.hadoop.hive.common.metrics.metrics2.CodahaleMetrics, comma separated list of JMX, CONSOLE, JSON_FILE"),
    HIVE_METRICS_JSON_FILE_LOCATION("hive.service.metrics.file.location", "file:///tmp/my-logging.properties",
        "For metric class org.apache.hadoop.hive.common.metrics.metrics2.CodahaleMetrics JSON_FILE reporter, the location of JSON metrics file.  " +
        "This file will get overwritten at every interval."),
    HIVE_METRICS_JSON_FILE_INTERVAL("hive.service.metrics.file.frequency", "5s",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "For metric class org.apache.hadoop.hive.common.metrics.metrics2.CodahaleMetrics JSON_FILE reporter, " +
        "the frequency of updating JSON metrics file."),
    HIVE_PERF_LOGGER("hive.exec.perf.logger", "org.apache.hadoop.hive.ql.log.PerfLogger",
        "The class responsible for logging client side performance metrics. \n" +
        "Must be a subclass of org.apache.hadoop.hive.ql.log.PerfLogger"),
    HIVE_START_CLEANUP_SCRATCHDIR("hive.start.cleanup.scratchdir", false,
        "To cleanup the Hive scratchdir when starting the Hive Server"),
    HIVE_INSERT_INTO_MULTILEVEL_DIRS("hive.insert.into.multilevel.dirs", false,
        "Where to insert into multilevel directories like\n" +
        "\"insert directory '/HIVEFT25686/chinna/' from table\""),
    HIVE_WAREHOUSE_SUBDIR_INHERIT_PERMS("hive.warehouse.subdir.inherit.perms", true,
        "Set this to false if the table directories should be created\n" +
        "with the permissions derived from dfs umask instead of\n" +
        "inheriting the permission of the warehouse or database directory."),
    HIVE_INSERT_INTO_EXTERNAL_TABLES("hive.insert.into.external.tables", true,
        "whether insert into external tables is allowed"),
    HIVE_TEMPORARY_TABLE_STORAGE(
        "hive.exec.temporary.table.storage", "default", new StringSet("memory",
         "ssd", "default"), "Define the storage policy for temporary tables." +
         "Choices between memory, ssd and default"),

    HIVE_DRIVER_RUN_HOOKS("hive.exec.driver.run.hooks", "",
        "A comma separated list of hooks which implement HiveDriverRunHook. Will be run at the beginning " +
        "and end of Driver.run, these will be run in the order specified."),
    HIVE_DDL_OUTPUT_FORMAT("hive.ddl.output.format", null,
        "The data format to use for DDL output.  One of \"text\" (for human\n" +
        "readable text) or \"json\" (for a json object)."),
    HIVE_ENTITY_SEPARATOR("hive.entity.separator", "@",
        "Separator used to construct names of tables and partitions. For example, dbname@tablename@partitionname"),
    HIVE_CAPTURE_TRANSFORM_ENTITY("hive.entity.capture.transform", false,
        "Compiler to capture transform URI referred in the query"),
    HIVE_DISPLAY_PARTITION_COLUMNS_SEPARATELY("hive.display.partition.cols.separately", true,
        "In older Hive version (0.10 and earlier) no distinction was made between\n" +
        "partition columns or non-partition columns while displaying columns in describe\n" +
        "table. From 0.12 onwards, they are displayed separately. This flag will let you\n" +
        "get old behavior, if desired. See, test-case in patch for HIVE-6689."),

    HIVE_SSL_PROTOCOL_BLACKLIST("hive.ssl.protocol.blacklist", "SSLv2,SSLv3",
        "SSL Versions to disable for all Hive Servers"),

     // HiveServer2 specific configs
    HIVE_SERVER2_MAX_START_ATTEMPTS("hive.server2.max.start.attempts", 30L, new RangeValidator(0L, null),
        "Number of times HiveServer2 will attempt to start before exiting, sleeping 60 seconds " +
        "between retries. \n The default of 30 will keep trying for 30 minutes."),
    HIVE_SERVER2_SUPPORT_DYNAMIC_SERVICE_DISCOVERY("hive.server2.support.dynamic.service.discovery", false,
        "Whether HiveServer2 supports dynamic service discovery for its clients. " +
        "To support this, each instance of HiveServer2 currently uses ZooKeeper to register itself, " +
        "when it is brought up. JDBC/ODBC clients should use the ZooKeeper ensemble: " +
        "hive.zookeeper.quorum in their connection string."),
    HIVE_SERVER2_ZOOKEEPER_NAMESPACE("hive.server2.zookeeper.namespace", "hiveserver2",
        "The parent node in ZooKeeper used by HiveServer2 when supporting dynamic service discovery."),
    // HiveServer2 global init file location
    HIVE_SERVER2_GLOBAL_INIT_FILE_LOCATION("hive.server2.global.init.file.location", "${env:HIVE_CONF_DIR}",
        "Either the location of a HS2 global init file or a directory containing a .hiverc file. If the \n" +
        "property is set, the value must be a valid path to an init file or directory where the init file is located."),
    HIVE_SERVER2_TRANSPORT_MODE("hive.server2.transport.mode", "binary", new StringSet("binary", "http"),
        "Transport mode of HiveServer2."),
    HIVE_SERVER2_THRIFT_BIND_HOST("hive.server2.thrift.bind.host", "",
        "Bind host on which to run the HiveServer2 Thrift service."),

    // http (over thrift) transport settings
    HIVE_SERVER2_THRIFT_HTTP_PORT("hive.server2.thrift.http.port", 10001,
        "Port number of HiveServer2 Thrift interface when hive.server2.transport.mode is 'http'."),
    HIVE_SERVER2_THRIFT_HTTP_PATH("hive.server2.thrift.http.path", "cliservice",
        "Path component of URL endpoint when in HTTP mode."),
    HIVE_SERVER2_THRIFT_MAX_MESSAGE_SIZE("hive.server2.thrift.max.message.size", 100*1024*1024,
        "Maximum message size in bytes a HS2 server will accept."),
    HIVE_SERVER2_THRIFT_HTTP_MAX_IDLE_TIME("hive.server2.thrift.http.max.idle.time", "1800s",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Maximum idle time for a connection on the server when in HTTP mode."),
    HIVE_SERVER2_THRIFT_HTTP_WORKER_KEEPALIVE_TIME("hive.server2.thrift.http.worker.keepalive.time", "60s",
        new TimeValidator(TimeUnit.SECONDS),
        "Keepalive time for an idle http worker thread. When the number of workers exceeds min workers, " +
        "excessive threads are killed after this time interval."),

    // Cookie based authentication
    HIVE_SERVER2_THRIFT_HTTP_COOKIE_AUTH_ENABLED("hive.server2.thrift.http.cookie.auth.enabled", true,
        "When true, HiveServer2 in HTTP transport mode, will use cookie based authentication mechanism."),
    HIVE_SERVER2_THRIFT_HTTP_COOKIE_MAX_AGE("hive.server2.thrift.http.cookie.max.age", "86400s",
        new TimeValidator(TimeUnit.SECONDS),
        "Maximum age in seconds for server side cookie used by HS2 in HTTP mode."),
    HIVE_SERVER2_THRIFT_HTTP_COOKIE_DOMAIN("hive.server2.thrift.http.cookie.domain", null,
        "Domain for the HS2 generated cookies"),
    HIVE_SERVER2_THRIFT_HTTP_COOKIE_PATH("hive.server2.thrift.http.cookie.path", null,
        "Path for the HS2 generated cookies"),
    HIVE_SERVER2_THRIFT_HTTP_COOKIE_IS_SECURE("hive.server2.thrift.http.cookie.is.secure", true,
        "Secure attribute of the HS2 generated cookie."),
    HIVE_SERVER2_THRIFT_HTTP_COOKIE_IS_HTTPONLY("hive.server2.thrift.http.cookie.is.httponly", true,
        "HttpOnly attribute of the HS2 generated cookie."),

    // binary transport settings
    HIVE_SERVER2_THRIFT_PORT("hive.server2.thrift.port", 10000,
        "Port number of HiveServer2 Thrift interface when hive.server2.transport.mode is 'binary'."),
    HIVE_SERVER2_THRIFT_SASL_QOP("hive.server2.thrift.sasl.qop", "auth",
        new StringSet("auth", "auth-int", "auth-conf"),
        "Sasl QOP value; set it to one of following values to enable higher levels of\n" +
        "protection for HiveServer2 communication with clients.\n" +
        "Setting hadoop.rpc.protection to a higher level than HiveServer2 does not\n" +
        "make sense in most situations. HiveServer2 ignores hadoop.rpc.protection in favor\n" +
        "of hive.server2.thrift.sasl.qop.\n" +
        "  \"auth\" - authentication only (default)\n" +
        "  \"auth-int\" - authentication plus integrity protection\n" +
        "  \"auth-conf\" - authentication plus integrity and confidentiality protection\n" +
        "This is applicable only if HiveServer2 is configured to use Kerberos authentication."),
    HIVE_SERVER2_THRIFT_MIN_WORKER_THREADS("hive.server2.thrift.min.worker.threads", 5,
        "Minimum number of Thrift worker threads"),
    HIVE_SERVER2_THRIFT_MAX_WORKER_THREADS("hive.server2.thrift.max.worker.threads", 500,
        "Maximum number of Thrift worker threads"),
    HIVE_SERVER2_THRIFT_LOGIN_BEBACKOFF_SLOT_LENGTH(
        "hive.server2.thrift.exponential.backoff.slot.length", "100ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Binary exponential backoff slot time for Thrift clients during login to HiveServer2,\n" +
        "for retries until hitting Thrift client timeout"),
    HIVE_SERVER2_THRIFT_LOGIN_TIMEOUT("hive.server2.thrift.login.timeout", "20s",
        new TimeValidator(TimeUnit.SECONDS), "Timeout for Thrift clients during login to HiveServer2"),
    HIVE_SERVER2_THRIFT_WORKER_KEEPALIVE_TIME("hive.server2.thrift.worker.keepalive.time", "60s",
        new TimeValidator(TimeUnit.SECONDS),
        "Keepalive time (in seconds) for an idle worker thread. When the number of workers exceeds min workers, " +
        "excessive threads are killed after this time interval."),
    // Configuration for async thread pool in SessionManager
    HIVE_SERVER2_ASYNC_EXEC_THREADS("hive.server2.async.exec.threads", 100,
        "Number of threads in the async thread pool for HiveServer2"),
    HIVE_SERVER2_ASYNC_EXEC_SHUTDOWN_TIMEOUT("hive.server2.async.exec.shutdown.timeout", "10s",
        new TimeValidator(TimeUnit.SECONDS),
        "How long HiveServer2 shutdown will wait for async threads to terminate."),
    HIVE_SERVER2_ASYNC_EXEC_WAIT_QUEUE_SIZE("hive.server2.async.exec.wait.queue.size", 100,
        "Size of the wait queue for async thread pool in HiveServer2.\n" +
        "After hitting this limit, the async thread pool will reject new requests."),
    HIVE_SERVER2_ASYNC_EXEC_KEEPALIVE_TIME("hive.server2.async.exec.keepalive.time", "10s",
        new TimeValidator(TimeUnit.SECONDS),
        "Time that an idle HiveServer2 async thread (from the thread pool) will wait for a new task\n" +
        "to arrive before terminating"),
    HIVE_SERVER2_LONG_POLLING_TIMEOUT("hive.server2.long.polling.timeout", "5000ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Time that HiveServer2 will wait before responding to asynchronous calls that use long polling"),

    // HiveServer2 auth configuration
    HIVE_SERVER2_AUTHENTICATION("hive.server2.authentication", "NONE",
      new StringSet("NOSASL", "NONE", "LDAP", "KERBEROS", "PAM", "CUSTOM"),
        "Client authentication types.\n" +
        "  NONE: no authentication check\n" +
        "  LDAP: LDAP/AD based authentication\n" +
        "  KERBEROS: Kerberos/GSSAPI authentication\n" +
        "  CUSTOM: Custom authentication provider\n" +
        "          (Use with property hive.server2.custom.authentication.class)\n" +
        "  PAM: Pluggable authentication module\n" +
        "  NOSASL:  Raw transport"),
    HIVE_SERVER2_ALLOW_USER_SUBSTITUTION("hive.server2.allow.user.substitution", true,
        "Allow alternate user to be specified as part of HiveServer2 open connection request."),
    HIVE_SERVER2_KERBEROS_KEYTAB("hive.server2.authentication.kerberos.keytab", "",
        "Kerberos keytab file for server principal"),
    HIVE_SERVER2_KERBEROS_PRINCIPAL("hive.server2.authentication.kerberos.principal", "",
        "Kerberos server principal"),
    HIVE_SERVER2_SPNEGO_KEYTAB("hive.server2.authentication.spnego.keytab", "",
        "keytab file for SPNego principal, optional,\n" +
        "typical value would look like /etc/security/keytabs/spnego.service.keytab,\n" +
        "This keytab would be used by HiveServer2 when Kerberos security is enabled and \n" +
        "HTTP transport mode is used.\n" +
        "This needs to be set only if SPNEGO is to be used in authentication.\n" +
        "SPNego authentication would be honored only if valid\n" +
        "  hive.server2.authentication.spnego.principal\n" +
        "and\n" +
        "  hive.server2.authentication.spnego.keytab\n" +
        "are specified."),
    HIVE_SERVER2_SPNEGO_PRINCIPAL("hive.server2.authentication.spnego.principal", "",
        "SPNego service principal, optional,\n" +
        "typical value would look like HTTP/_HOST@EXAMPLE.COM\n" +
        "SPNego service principal would be used by HiveServer2 when Kerberos security is enabled\n" +
        "and HTTP transport mode is used.\n" +
        "This needs to be set only if SPNEGO is to be used in authentication."),
    HIVE_SERVER2_PLAIN_LDAP_URL("hive.server2.authentication.ldap.url", null,
        "LDAP connection URL(s),\n" +
         "this value could contain URLs to mutiple LDAP servers instances for HA,\n" +
         "each LDAP URL is separated by a SPACE character. URLs are used in the \n" +
         " order specified until a connection is successful."),
    HIVE_SERVER2_PLAIN_LDAP_BASEDN("hive.server2.authentication.ldap.baseDN", null, "LDAP base DN"),
    HIVE_SERVER2_PLAIN_LDAP_DOMAIN("hive.server2.authentication.ldap.Domain", null, ""),
    HIVE_SERVER2_CUSTOM_AUTHENTICATION_CLASS("hive.server2.custom.authentication.class", null,
        "Custom authentication class. Used when property\n" +
        "'hive.server2.authentication' is set to 'CUSTOM'. Provided class\n" +
        "must be a proper implementation of the interface\n" +
        "org.apache.hive.service.auth.PasswdAuthenticationProvider. HiveServer2\n" +
        "will call its Authenticate(user, passed) method to authenticate requests.\n" +
        "The implementation may optionally implement Hadoop's\n" +
        "org.apache.hadoop.conf.Configurable class to grab Hive's Configuration object."),
    HIVE_SERVER2_PAM_SERVICES("hive.server2.authentication.pam.services", null,
      "List of the underlying pam services that should be used when auth type is PAM\n" +
      "A file with the same name must exist in /etc/pam.d"),

    HIVE_SERVER2_ENABLE_DOAS("hive.server2.enable.doAs", true,
        "Setting this property to true will have HiveServer2 execute\n" +
        "Hive operations as the user making the calls to it."),
    HIVE_SERVER2_TABLE_TYPE_MAPPING("hive.server2.table.type.mapping", "CLASSIC", new StringSet("CLASSIC", "HIVE"),
        "This setting reflects how HiveServer2 will report the table types for JDBC and other\n" +
        "client implementations that retrieve the available tables and supported table types\n" +
        "  HIVE : Exposes Hive's native table types like MANAGED_TABLE, EXTERNAL_TABLE, VIRTUAL_VIEW\n" +
        "  CLASSIC : More generic types like TABLE and VIEW"),
    HIVE_SERVER2_SESSION_HOOK("hive.server2.session.hook", "", ""),
    HIVE_SERVER2_USE_SSL("hive.server2.use.SSL", false,
        "Set this to true for using SSL encryption in HiveServer2."),
    HIVE_SERVER2_SSL_KEYSTORE_PATH("hive.server2.keystore.path", "",
        "SSL certificate keystore location."),
    HIVE_SERVER2_SSL_KEYSTORE_PASSWORD("hive.server2.keystore.password", "",
        "SSL certificate keystore password."),
    HIVE_SERVER2_MAP_FAIR_SCHEDULER_QUEUE("hive.server2.map.fair.scheduler.queue", true,
        "If the YARN fair scheduler is configured and HiveServer2 is running in non-impersonation mode,\n" +
        "this setting determines the user for fair scheduler queue mapping.\n" +
        "If set to true (default), the logged-in user determines the fair scheduler queue\n" +
        "for submitted jobs, so that map reduce resource usage can be tracked by user.\n" +
        "If set to false, all Hive jobs go to the 'hive' user's queue."),
    HIVE_SERVER2_BUILTIN_UDF_WHITELIST("hive.server2.builtin.udf.whitelist", "",
        "Comma separated list of builtin udf names allowed in queries.\n" +
        "An empty whitelist allows all builtin udfs to be executed. " +
        " The udf black list takes precedence over udf white list"),
    HIVE_SERVER2_BUILTIN_UDF_BLACKLIST("hive.server2.builtin.udf.blacklist", "",
         "Comma separated list of udfs names. These udfs will not be allowed in queries." +
         " The udf black list takes precedence over udf white list"),

    HIVE_SECURITY_COMMAND_WHITELIST("hive.security.command.whitelist", "set,reset,dfs,add,list,delete,reload,compile",
        "Comma separated list of non-SQL Hive commands users are authorized to execute"),

    HIVE_SERVER2_SESSION_CHECK_INTERVAL("hive.server2.session.check.interval", "6h",
        new TimeValidator(TimeUnit.MILLISECONDS, 3000l, true, null, false),
        "The check interval for session/operation timeout, which can be disabled by setting to zero or negative value."),
    HIVE_SERVER2_IDLE_SESSION_TIMEOUT("hive.server2.idle.session.timeout", "7d",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Session will be closed when it's not accessed for this duration, which can be disabled by setting to zero or negative value."),
    HIVE_SERVER2_IDLE_OPERATION_TIMEOUT("hive.server2.idle.operation.timeout", "5d",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Operation will be closed when it's not accessed for this duration of time, which can be disabled by setting to zero value.\n" +
        "  With positive value, it's checked for operations in terminal state only (FINISHED, CANCELED, CLOSED, ERROR).\n" +
        "  With negative value, it's checked for all of the operations regardless of state."),
    HIVE_SERVER2_IDLE_SESSION_CHECK_OPERATION("hive.server2.idle.session.check.operation", true,
        "Session will be considered to be idle only if there is no activity, and there is no pending operation.\n" +
        " This setting takes effect only if session idle timeout (hive.server2.idle.session.timeout) and checking\n" +
        "(hive.server2.session.check.interval) are enabled."),

    HIVE_CONF_RESTRICTED_LIST("hive.conf.restricted.list",
        "hive.security.authenticator.manager,hive.security.authorization.manager,hive.users.in.admin.role",
        "Comma separated list of configuration options which are immutable at runtime"),

    // If this is set all move tasks at the end of a multi-insert query will only begin once all
    // outputs are ready
    HIVE_MULTI_INSERT_MOVE_TASKS_SHARE_DEPENDENCIES(
        "hive.multi.insert.move.tasks.share.dependencies", false,
        "If this is set all move tasks for tables/partitions (not directories) at the end of a\n" +
        "multi-insert query will only begin once the dependencies for all these move tasks have been\n" +
        "met.\n" +
        "Advantages: If concurrency is enabled, the locks will only be released once the query has\n" +
        "            finished, so with this config enabled, the time when the table/partition is\n" +
        "            generated will be much closer to when the lock on it is released.\n" +
        "Disadvantages: If concurrency is not enabled, with this disabled, the tables/partitions which\n" +
        "               are produced by this query and finish earlier will be available for querying\n" +
        "               much earlier.  Since the locks are only released once the query finishes, this\n" +
        "               does not apply if concurrency is enabled."),

    HIVE_INFER_BUCKET_SORT("hive.exec.infer.bucket.sort", false,
        "If this is set, when writing partitions, the metadata will include the bucketing/sorting\n" +
        "properties with which the data was written if any (this will not overwrite the metadata\n" +
        "inherited from the table if the table is bucketed/sorted)"),

    HIVE_INFER_BUCKET_SORT_NUM_BUCKETS_POWER_TWO(
        "hive.exec.infer.bucket.sort.num.buckets.power.two", false,
        "If this is set, when setting the number of reducers for the map reduce task which writes the\n" +
        "final output files, it will choose a number which is a power of two, unless the user specifies\n" +
        "the number of reducers to use using mapred.reduce.tasks.  The number of reducers\n" +
        "may be set to a power of two, only to be followed by a merge task meaning preventing\n" +
        "anything from being inferred.\n" +
        "With hive.exec.infer.bucket.sort set to true:\n" +
        "Advantages:  If this is not set, the number of buckets for partitions will seem arbitrary,\n" +
        "             which means that the number of mappers used for optimized joins, for example, will\n" +
        "             be very low.  With this set, since the number of buckets used for any partition is\n" +
        "             a power of two, the number of mappers used for optimized joins will be the least\n" +
        "             number of buckets used by any partition being joined.\n" +
        "Disadvantages: This may mean a much larger or much smaller number of reducers being used in the\n" +
        "               final map reduce job, e.g. if a job was originally going to take 257 reducers,\n" +
        "               it will now take 512 reducers, similarly if the max number of reducers is 511,\n" +
        "               and a job was going to use this many, it will now use 256 reducers."),

    HIVEOPTLISTBUCKETING("hive.optimize.listbucketing", false,
        "Enable list bucketing optimizer. Default value is false so that we disable it by default."),

    // Allow TCP Keep alive socket option for for HiveServer or a maximum timeout for the socket.
    SERVER_READ_SOCKET_TIMEOUT("hive.server.read.socket.timeout", "10s",
        new TimeValidator(TimeUnit.SECONDS),
        "Timeout for the HiveServer to close the connection if no response from the client. By default, 10 seconds."),
    SERVER_TCP_KEEP_ALIVE("hive.server.tcp.keepalive", true,
        "Whether to enable TCP keepalive for the Hive Server. Keepalive will prevent accumulation of half-open connections."),

    HIVE_DECODE_PARTITION_NAME("hive.decode.partition.name", false,
        "Whether to show the unquoted partition names in query results."),

    HIVE_EXECUTION_ENGINE("hive.execution.engine", "mr", new StringSet("mr", "tez", "spark"),
        "Chooses execution engine. Options are: mr (Map reduce, default), tez (hadoop 2 only), spark"),
    HIVE_JAR_DIRECTORY("hive.jar.directory", null,
        "This is the location hive in tez mode will look for to find a site wide \n" +
        "installed hive instance."),
    HIVE_USER_INSTALL_DIR("hive.user.install.directory", "hdfs:///user/",
        "If hive (in tez mode only) cannot find a usable hive jar in \"hive.jar.directory\", \n" +
        "it will upload the hive jar to \"hive.user.install.directory/user.name\"\n" +
        "and use it to run queries."),

    // Vectorization enabled
    HIVE_VECTORIZATION_ENABLED("hive.vectorized.execution.enabled", false,
        "This flag should be set to true to enable vectorized mode of query execution.\n" +
        "The default value is false."),
    HIVE_VECTORIZATION_REDUCE_ENABLED("hive.vectorized.execution.reduce.enabled", true,
        "This flag should be set to true to enable vectorized mode of the reduce-side of query execution.\n" +
        "The default value is true."),
    HIVE_VECTORIZATION_REDUCE_GROUPBY_ENABLED("hive.vectorized.execution.reduce.groupby.enabled", true,
        "This flag should be set to true to enable vectorized mode of the reduce-side GROUP BY query execution.\n" +
        "The default value is true."),
    HIVE_VECTORIZATION_MAPJOIN_NATIVE_ENABLED("hive.vectorized.execution.mapjoin.native.enabled", true,
         "This flag should be set to true to enable native (i.e. non-pass through) vectorization\n" +
         "of queries using MapJoin.\n" +
         "The default value is true."),
    HIVE_VECTORIZATION_MAPJOIN_NATIVE_MULTIKEY_ONLY_ENABLED("hive.vectorized.execution.mapjoin.native.multikey.only.enabled", false,
         "This flag should be set to true to restrict use of native vector map join hash tables to\n" +
         "the MultiKey in queries using MapJoin.\n" +
         "The default value is false."),
    HIVE_VECTORIZATION_MAPJOIN_NATIVE_MINMAX_ENABLED("hive.vectorized.execution.mapjoin.minmax.enabled", false,
         "This flag should be set to true to enable vector map join hash tables to\n" +
         "use max / max filtering for integer join queries using MapJoin.\n" +
         "The default value is false."),
    HIVE_VECTORIZATION_MAPJOIN_NATIVE_OVERFLOW_REPEATED_THRESHOLD("hive.vectorized.execution.mapjoin.overflow.repeated.threshold", -1,
         "The number of small table rows for a match in vector map join hash tables\n" +
         "where we use the repeated field optimization in overflow vectorized row batch for join queries using MapJoin.\n" +
         "A value of -1 means do use the join result optimization.  Otherwise, threshold value can be 0 to maximum integer."),
    HIVE_VECTORIZATION_MAPJOIN_NATIVE_FAST_HASHTABLE_ENABLED("hive.vectorized.execution.mapjoin.native.fast.hashtable.enabled", false,
         "This flag should be set to true to enable use of native fast vector map join hash tables in\n" +
         "queries using MapJoin.\n" +
         "The default value is false."),
    HIVE_VECTORIZATION_GROUPBY_CHECKINTERVAL("hive.vectorized.groupby.checkinterval", 100000,
        "Number of entries added to the group by aggregation hash before a recomputation of average entry size is performed."),
    HIVE_VECTORIZATION_GROUPBY_MAXENTRIES("hive.vectorized.groupby.maxentries", 1000000,
        "Max number of entries in the vector group by aggregation hashtables. \n" +
        "Exceeding this will trigger a flush irrelevant of memory pressure condition."),
    HIVE_VECTORIZATION_GROUPBY_FLUSH_PERCENT("hive.vectorized.groupby.flush.percent", (float) 0.1,
        "Percent of entries in the group by aggregation hash flushed when the memory threshold is exceeded."),

    HIVE_TYPE_CHECK_ON_INSERT("hive.typecheck.on.insert", true, "This property has been extended to control "
        + "whether to check, convert, and normalize partition value to conform to its column type in "
        + "partition operations including but not limited to insert, such as alter, describe etc."),

    HIVE_HADOOP_CLASSPATH("hive.hadoop.classpath", null,
        "For Windows OS, we need to pass HIVE_HADOOP_CLASSPATH Java parameter while starting HiveServer2 \n" +
        "using \"-hiveconf hive.hadoop.classpath=%HIVE_LIB%\"."),

    HIVE_RPC_QUERY_PLAN("hive.rpc.query.plan", false,
        "Whether to send the query plan via local resource or RPC"),
    HIVE_AM_SPLIT_GENERATION("hive.compute.splits.in.am", true,
        "Whether to generate the splits locally or in the AM (tez only)"),

    HIVE_PREWARM_ENABLED("hive.prewarm.enabled", false, "Enables container prewarm for Tez (Hadoop 2 only)"),
    HIVE_PREWARM_NUM_CONTAINERS("hive.prewarm.numcontainers", 10, "Controls the number of containers to prewarm for Tez (Hadoop 2 only)"),

    HIVESTAGEIDREARRANGE("hive.stageid.rearrange", "none", new StringSet("none", "idonly", "traverse", "execution"), ""),
    HIVEEXPLAINDEPENDENCYAPPENDTASKTYPES("hive.explain.dependency.append.tasktype", false, ""),

    HIVECOUNTERGROUP("hive.counters.group.name", "HIVE",
        "The name of counter group for internal Hive variables (CREATED_FILE, FATAL_ERROR, etc.)"),

    HIVE_SERVER2_TEZ_DEFAULT_QUEUES("hive.server2.tez.default.queues", "",
        "A list of comma separated values corresponding to YARN queues of the same name.\n" +
        "When HiveServer2 is launched in Tez mode, this configuration needs to be set\n" +
        "for multiple Tez sessions to run in parallel on the cluster."),
    HIVE_SERVER2_TEZ_SESSIONS_PER_DEFAULT_QUEUE("hive.server2.tez.sessions.per.default.queue", 1,
        "A positive integer that determines the number of Tez sessions that should be\n" +
        "launched on each of the queues specified by \"hive.server2.tez.default.queues\".\n" +
        "Determines the parallelism on each queue."),
    HIVE_SERVER2_TEZ_INITIALIZE_DEFAULT_SESSIONS("hive.server2.tez.initialize.default.sessions", false,
        "This flag is used in HiveServer2 to enable a user to use HiveServer2 without\n" +
        "turning on Tez for HiveServer2. The user could potentially want to run queries\n" +
        "over Tez without the pool of sessions."),

    HIVE_QUOTEDID_SUPPORT("hive.support.quoted.identifiers", "column",
        new StringSet("none", "column"),
        "Whether to use quoted identifier. 'none' or 'column' can be used. \n" +
        "  none: default(past) behavior. Implies only alphaNumeric and underscore are valid characters in identifiers.\n" +
        "  column: implies column names can contain any character."
    ),
    HIVE_SUPPORT_SQL11_RESERVED_KEYWORDS("hive.support.sql11.reserved.keywords", true,
        "This flag should be set to true to enable support for SQL2011 reserved keywords.\n" +
        "The default value is true."),
    // role names are case-insensitive
    USERS_IN_ADMIN_ROLE("hive.users.in.admin.role", "", false,
        "Comma separated list of users who are in admin role for bootstrapping.\n" +
        "More users can be added in ADMIN role later."),

    HIVE_COMPAT("hive.compat", HiveCompat.DEFAULT_COMPAT_LEVEL,
        "Enable (configurable) deprecated behaviors by setting desired level of backward compatibility.\n" +
        "Setting to 0.12:\n" +
        "  Maintains division behavior: int / int = double"),
    HIVE_CONVERT_JOIN_BUCKET_MAPJOIN_TEZ("hive.convert.join.bucket.mapjoin.tez", false,
        "Whether joins can be automatically converted to bucket map joins in hive \n" +
        "when tez is used as the execution engine."),

    HIVE_CHECK_CROSS_PRODUCT("hive.exec.check.crossproducts", true,
        "Check if a plan contains a Cross Product. If there is one, output a warning to the Session's console."),
    HIVE_LOCALIZE_RESOURCE_WAIT_INTERVAL("hive.localize.resource.wait.interval", "5000ms",
        new TimeValidator(TimeUnit.MILLISECONDS),
        "Time to wait for another thread to localize the same resource for hive-tez."),
    HIVE_LOCALIZE_RESOURCE_NUM_WAIT_ATTEMPTS("hive.localize.resource.num.wait.attempts", 5,
        "The number of attempts waiting for localizing a resource in hive-tez."),
    TEZ_AUTO_REDUCER_PARALLELISM("hive.tez.auto.reducer.parallelism", false,
        "Turn on Tez' auto reducer parallelism feature. When enabled, Hive will still estimate data sizes\n" +
        "and set parallelism estimates. Tez will sample source vertices' output sizes and adjust the estimates at runtime as\n" +
        "necessary."),
    TEZ_MAX_PARTITION_FACTOR("hive.tez.max.partition.factor", 2f,
        "When auto reducer parallelism is enabled this factor will be used to over-partition data in shuffle edges."),
    TEZ_MIN_PARTITION_FACTOR("hive.tez.min.partition.factor", 0.25f,
        "When auto reducer parallelism is enabled this factor will be used to put a lower limit to the number\n" +
        "of reducers that tez specifies."),
    TEZ_DYNAMIC_PARTITION_PRUNING(
        "hive.tez.dynamic.partition.pruning", true,
        "When dynamic pruning is enabled, joins on partition keys will be processed by sending\n" +
        "events from the processing vertices to the Tez application master. These events will be\n" +
        "used to prune unnecessary partitions."),
    TEZ_DYNAMIC_PARTITION_PRUNING_MAX_EVENT_SIZE("hive.tez.dynamic.partition.pruning.max.event.size", 1*1024*1024L,
        "Maximum size of events sent by processors in dynamic pruning. If this size is crossed no pruning will take place."),
    TEZ_DYNAMIC_PARTITION_PRUNING_MAX_DATA_SIZE("hive.tez.dynamic.partition.pruning.max.data.size", 100*1024*1024L,
        "Maximum total data size of events in dynamic pruning."),
    TEZ_SMB_NUMBER_WAVES(
        "hive.tez.smb.number.waves",
        (float) 0.5,
        "The number of waves in which to run the SMB join. Account for cluster being occupied. Ideally should be 1 wave."),
    TEZ_EXEC_SUMMARY(
        "hive.tez.exec.print.summary",
        false,
        "Display breakdown of execution steps, for every query executed by the shell."),
    TEZ_EXEC_INPLACE_PROGRESS(
        "hive.tez.exec.inplace.progress",
        true,
        "Updates tez job execution progress in-place in the terminal."),
    SPARK_CLIENT_FUTURE_TIMEOUT("hive.spark.client.future.timeout",
      "60s", new TimeValidator(TimeUnit.SECONDS),
      "Timeout for requests from Hive client to remote Spark driver."),
    SPARK_JOB_MONITOR_TIMEOUT("hive.spark.job.monitor.timeout",
      "60s", new TimeValidator(TimeUnit.SECONDS),
      "Timeout for job monitor to get Spark job state."),
    SPARK_RPC_CLIENT_CONNECT_TIMEOUT("hive.spark.client.connect.timeout",
      "1000ms", new TimeValidator(TimeUnit.MILLISECONDS),
      "Timeout for remote Spark driver in connecting back to Hive client."),
    SPARK_RPC_CLIENT_HANDSHAKE_TIMEOUT("hive.spark.client.server.connect.timeout",
      "90000ms", new TimeValidator(TimeUnit.MILLISECONDS),
      "Timeout for handshake between Hive client and remote Spark driver.  Checked by both processes."),
    SPARK_RPC_SECRET_RANDOM_BITS("hive.spark.client.secret.bits", "256",
      "Number of bits of randomness in the generated secret for communication between Hive client and remote Spark driver. " +
      "Rounded down to the nearest multiple of 8."),
    SPARK_RPC_MAX_THREADS("hive.spark.client.rpc.threads", 8,
      "Maximum number of threads for remote Spark driver's RPC event loop."),
    SPARK_RPC_MAX_MESSAGE_SIZE("hive.spark.client.rpc.max.size", 50 * 1024 * 1024,
      "Maximum message size in bytes for communication between Hive client and remote Spark driver. Default is 50MB."),
    SPARK_RPC_CHANNEL_LOG_LEVEL("hive.spark.client.channel.log.level", null,
      "Channel logging level for remote Spark driver.  One of {DEBUG, ERROR, INFO, TRACE, WARN}."),
    SPARK_RPC_SASL_MECHANISM("hive.spark.client.rpc.sasl.mechanisms", "DIGEST-MD5",
      "Name of the SASL mechanism to use for authentication."),
    NWAYJOINREORDER("hive.reorder.nway.joins", true,
      "Runs reordering of tables within single n-way join (i.e.: picks streamtable)"),
    HIVE_LOG_N_RECORDS("hive.log.every.n.records", 0L, new RangeValidator(0L, null),
      "If value is greater than 0 logs in fixed intervals of size n rather than exponentially."),
    HIVE_MSCK_PATH_VALIDATION("hive.msck.path.validation", "throw",
        new StringSet("throw", "skip", "ignore"), "The approach msck should take with HDFS " +
       "directories that are partition-like but contain unsupported characters. 'throw' (an " +
       "exception) is the default; 'skip' will skip the invalid directories and still repair the" +
       " others; 'ignore' will skip the validation (legacy behavior, causes bugs in many cases)");


    public final String varname;
    private final String defaultExpr;

    public final String defaultStrVal;
    public final int defaultIntVal;
    public final long defaultLongVal;
    public final float defaultFloatVal;
    public final boolean defaultBoolVal;

    private final Class<?> valClass;
    private final VarType valType;

    private final Validator validator;

    private final String description;

    private final boolean excluded;
    private final boolean caseSensitive;

    ConfVars(String varname, Object defaultVal, String description) {
      this(varname, defaultVal, null, description, true, false);
    }

    ConfVars(String varname, Object defaultVal, String description, boolean excluded) {
      this(varname, defaultVal, null, description, true, excluded);
    }

    ConfVars(String varname, String defaultVal, boolean caseSensitive, String description) {
      this(varname, defaultVal, null, description, caseSensitive, false);
    }

    ConfVars(String varname, Object defaultVal, Validator validator, String description) {
      this(varname, defaultVal, validator, description, true, false);
    }

    ConfVars(String varname, Object defaultVal, Validator validator, String description, boolean caseSensitive, boolean excluded) {
      this.varname = varname;
      this.validator = validator;
      this.description = description;
      this.defaultExpr = defaultVal == null ? null : String.valueOf(defaultVal);
      this.excluded = excluded;
      this.caseSensitive = caseSensitive;
      if (defaultVal == null || defaultVal instanceof String) {
        this.valClass = String.class;
        this.valType = VarType.STRING;
        this.defaultStrVal = SystemVariables.substitute((String)defaultVal);
        this.defaultIntVal = -1;
        this.defaultLongVal = -1;
        this.defaultFloatVal = -1;
        this.defaultBoolVal = false;
      } else if (defaultVal instanceof Integer) {
        this.valClass = Integer.class;
        this.valType = VarType.INT;
        this.defaultStrVal = null;
        this.defaultIntVal = (Integer)defaultVal;
        this.defaultLongVal = -1;
        this.defaultFloatVal = -1;
        this.defaultBoolVal = false;
      } else if (defaultVal instanceof Long) {
        this.valClass = Long.class;
        this.valType = VarType.LONG;
        this.defaultStrVal = null;
        this.defaultIntVal = -1;
        this.defaultLongVal = (Long)defaultVal;
        this.defaultFloatVal = -1;
        this.defaultBoolVal = false;
      } else if (defaultVal instanceof Float) {
        this.valClass = Float.class;
        this.valType = VarType.FLOAT;
        this.defaultStrVal = null;
        this.defaultIntVal = -1;
        this.defaultLongVal = -1;
        this.defaultFloatVal = (Float)defaultVal;
        this.defaultBoolVal = false;
      } else if (defaultVal instanceof Boolean) {
        this.valClass = Boolean.class;
        this.valType = VarType.BOOLEAN;
        this.defaultStrVal = null;
        this.defaultIntVal = -1;
        this.defaultLongVal = -1;
        this.defaultFloatVal = -1;
        this.defaultBoolVal = (Boolean)defaultVal;
      } else {
        throw new IllegalArgumentException("Not supported type value " + defaultVal.getClass() +
            " for name " + varname);
      }
    }

    public boolean isType(String value) {
      return valType.isType(value);
    }

    public Validator getValidator() {
      return validator;
    }

    public String validate(String value) {
      return validator == null ? null : validator.validate(value);
    }

    public String validatorDescription() {
      return validator == null ? null : validator.toDescription();
    }

    public String typeString() {
      String type = valType.typeString();
      if (valType == VarType.STRING && validator != null) {
        if (validator instanceof TimeValidator) {
          type += "(TIME)";
        }
      }
      return type;
    }

    public String getRawDescription() {
      return description;
    }

    public String getDescription() {
      String validator = validatorDescription();
      if (validator != null) {
        return validator + ".\n" + description;
      }
      return description;
    }

    public boolean isExcluded() {
      return excluded;
    }

    public boolean isCaseSensitive() {
      return caseSensitive;
    }

    @Override
    public String toString() {
      return varname;
    }

    private static String findHadoopBinary() {
      String val = System.getenv("HADOOP_HOME");
      // In Hadoop 1.X and Hadoop 2.X HADOOP_HOME is gone and replaced with HADOOP_PREFIX
      if (val == null) {
        val = System.getenv("HADOOP_PREFIX");
      }
      // and if all else fails we can at least try /usr/bin/hadoop
      val = (val == null ? File.separator + "usr" : val)
        + File.separator + "bin" + File.separator + "hadoop";
      // Launch hadoop command file on windows.
      return val + (Shell.WINDOWS ? ".cmd" : "");
    }

    public String getDefaultValue() {
      return valType.defaultValueString(this);
    }

    public String getDefaultExpr() {
      return defaultExpr;
    }

    enum VarType {
      STRING {
        @Override
        void checkType(String value) throws Exception { }
        @Override
        String defaultValueString(ConfVars confVar) { return confVar.defaultStrVal; }
      },
      INT {
        @Override
        void checkType(String value) throws Exception { Integer.valueOf(value); }
      },
      LONG {
        @Override
        void checkType(String value) throws Exception { Long.valueOf(value); }
      },
      FLOAT {
        @Override
        void checkType(String value) throws Exception { Float.valueOf(value); }
      },
      BOOLEAN {
        @Override
        void checkType(String value) throws Exception { Boolean.valueOf(value); }
      };

      boolean isType(String value) {
        try { checkType(value); } catch (Exception e) { return false; }
        return true;
      }
      String typeString() { return name().toUpperCase();}
      String defaultValueString(ConfVars confVar) { return confVar.defaultExpr; }
      abstract void checkType(String value) throws Exception;
    }
  }

  /**
   * Writes the default ConfVars out to a byte array and returns an input
   * stream wrapping that byte array.
   *
   * We need this in order to initialize the ConfVar properties
   * in the underling Configuration object using the addResource(InputStream)
   * method.
   *
   * It is important to use a LoopingByteArrayInputStream because it turns out
   * addResource(InputStream) is broken since Configuration tries to read the
   * entire contents of the same InputStream repeatedly without resetting it.
   * LoopingByteArrayInputStream has special logic to handle this.
   */
  private static synchronized InputStream getConfVarInputStream() {
    if (confVarByteArray == null) {
      try {
        // Create a Hadoop configuration without inheriting default settings.
        Configuration conf = new Configuration(false);

        applyDefaultNonNullConfVars(conf);

        ByteArrayOutputStream confVarBaos = new ByteArrayOutputStream();
        conf.writeXml(confVarBaos);
        confVarByteArray = confVarBaos.toByteArray();
      } catch (Exception e) {
        // We're pretty screwed if we can't load the default conf vars
        throw new RuntimeException("Failed to initialize default Hive configuration variables!", e);
      }
    }
    return new LoopingByteArrayInputStream(confVarByteArray);
  }

  public void verifyAndSet(String name, String value) throws IllegalArgumentException {
    if (modWhiteListPattern != null) {
      Matcher wlMatcher = modWhiteListPattern.matcher(name);
      if (!wlMatcher.matches()) {
        throw new IllegalArgumentException("Cannot modify " + name + " at runtime. "
            + "It is not in list of params that are allowed to be modified at runtime");
      }
    }
    if (restrictList.contains(name)) {
      throw new IllegalArgumentException("Cannot modify " + name + " at runtime. It is in the list"
          + "of parameters that can't be modified at runtime");
    }
    String oldValue = name != null ? get(name) : null;
    if (name == null || value == null || !value.equals(oldValue)) {
      // When either name or value is null, the set method below will fail,
      // and throw IllegalArgumentException
      set(name, value);
      isSparkConfigUpdated = isSparkRelatedConfig(name);
    }
  }

  /**
   * check whether spark related property is updated, which includes spark configurations,
   * RSC configurations and yarn configuration in Spark on YARN mode.
   * @param name
   * @return
   */
  private boolean isSparkRelatedConfig(String name) {
    boolean result = false;
    if (name.startsWith("spark")) { // Spark property.
      result = true;
    } else if (name.startsWith("yarn")) { // YARN property in Spark on YARN mode.
      String sparkMaster = get("spark.master");
      if (sparkMaster != null &&
        (sparkMaster.equals("yarn-client") || sparkMaster.equals("yarn-cluster"))) {
        result = true;
      }
    } else if (name.startsWith("hive.spark")) { // Remote Spark Context property.
      result = true;
    }

    return result;
  }

  public static int getIntVar(Configuration conf, ConfVars var) {
    assert (var.valClass == Integer.class) : var.varname;
    return conf.getInt(var.varname, var.defaultIntVal);
  }

  public static void setIntVar(Configuration conf, ConfVars var, int val) {
    assert (var.valClass == Integer.class) : var.varname;
    conf.setInt(var.varname, val);
  }

  public int getIntVar(ConfVars var) {
    return getIntVar(this, var);
  }

  public void setIntVar(ConfVars var, int val) {
    setIntVar(this, var, val);
  }

  public static long getTimeVar(Configuration conf, ConfVars var, TimeUnit outUnit) {
    return toTime(getVar(conf, var), getDefaultTimeUnit(var), outUnit);
  }

  public static void setTimeVar(Configuration conf, ConfVars var, long time, TimeUnit timeunit) {
    assert (var.valClass == String.class) : var.varname;
    conf.set(var.varname, time + stringFor(timeunit));
  }

  public long getTimeVar(ConfVars var, TimeUnit outUnit) {
    return getTimeVar(this, var, outUnit);
  }

  public void setTimeVar(ConfVars var, long time, TimeUnit outUnit) {
    setTimeVar(this, var, time, outUnit);
  }

  private static TimeUnit getDefaultTimeUnit(ConfVars var) {
    TimeUnit inputUnit = null;
    if (var.validator instanceof TimeValidator) {
      inputUnit = ((TimeValidator)var.validator).getTimeUnit();
    }
    return inputUnit;
  }

  public static long toTime(String value, TimeUnit inputUnit, TimeUnit outUnit) {
    String[] parsed = parseTime(value.trim());
    return outUnit.convert(Long.valueOf(parsed[0].trim().trim()), unitFor(parsed[1].trim(), inputUnit));
  }

  private static String[] parseTime(String value) {
    char[] chars = value.toCharArray();
    int i = 0;
    for (; i < chars.length && (chars[i] == '-' || Character.isDigit(chars[i])); i++) {
    }
    return new String[] {value.substring(0, i), value.substring(i)};
  }

  public static TimeUnit unitFor(String unit, TimeUnit defaultUnit) {
    unit = unit.trim().toLowerCase();
    if (unit.isEmpty() || unit.equals("l")) {
      if (defaultUnit == null) {
        throw new IllegalArgumentException("Time unit is not specified");
      }
      return defaultUnit;
    } else if (unit.equals("d") || unit.startsWith("day")) {
      return TimeUnit.DAYS;
    } else if (unit.equals("h") || unit.startsWith("hour")) {
      return TimeUnit.HOURS;
    } else if (unit.equals("m") || unit.startsWith("min")) {
      return TimeUnit.MINUTES;
    } else if (unit.equals("s") || unit.startsWith("sec")) {
      return TimeUnit.SECONDS;
    } else if (unit.equals("ms") || unit.startsWith("msec")) {
      return TimeUnit.MILLISECONDS;
    } else if (unit.equals("us") || unit.startsWith("usec")) {
      return TimeUnit.MICROSECONDS;
    } else if (unit.equals("ns") || unit.startsWith("nsec")) {
      return TimeUnit.NANOSECONDS;
    }
    throw new IllegalArgumentException("Invalid time unit " + unit);
  }

  public static String stringFor(TimeUnit timeunit) {
    switch (timeunit) {
      case DAYS: return "day";
      case HOURS: return "hour";
      case MINUTES: return "min";
      case SECONDS: return "sec";
      case MILLISECONDS: return "msec";
      case MICROSECONDS: return "usec";
      case NANOSECONDS: return "nsec";
    }
    throw new IllegalArgumentException("Invalid timeunit " + timeunit);
  }

  public static long getLongVar(Configuration conf, ConfVars var) {
    assert (var.valClass == Long.class) : var.varname;
    return conf.getLong(var.varname, var.defaultLongVal);
  }

  public static long getLongVar(Configuration conf, ConfVars var, long defaultVal) {
    return conf.getLong(var.varname, defaultVal);
  }

  public static void setLongVar(Configuration conf, ConfVars var, long val) {
    assert (var.valClass == Long.class) : var.varname;
    conf.setLong(var.varname, val);
  }

  public long getLongVar(ConfVars var) {
    return getLongVar(this, var);
  }

  public void setLongVar(ConfVars var, long val) {
    setLongVar(this, var, val);
  }

  public static float getFloatVar(Configuration conf, ConfVars var) {
    assert (var.valClass == Float.class) : var.varname;
    return conf.getFloat(var.varname, var.defaultFloatVal);
  }

  public static float getFloatVar(Configuration conf, ConfVars var, float defaultVal) {
    return conf.getFloat(var.varname, defaultVal);
  }

  public static void setFloatVar(Configuration conf, ConfVars var, float val) {
    assert (var.valClass == Float.class) : var.varname;
    conf.setFloat(var.varname, val);
  }

  public float getFloatVar(ConfVars var) {
    return getFloatVar(this, var);
  }

  public void setFloatVar(ConfVars var, float val) {
    setFloatVar(this, var, val);
  }

  public static boolean getBoolVar(Configuration conf, ConfVars var) {
    assert (var.valClass == Boolean.class) : var.varname;
    return conf.getBoolean(var.varname, var.defaultBoolVal);
  }

  public static boolean getBoolVar(Configuration conf, ConfVars var, boolean defaultVal) {
    return conf.getBoolean(var.varname, defaultVal);
  }

  public static void setBoolVar(Configuration conf, ConfVars var, boolean val) {
    assert (var.valClass == Boolean.class) : var.varname;
    conf.setBoolean(var.varname, val);
  }

  public boolean getBoolVar(ConfVars var) {
    return getBoolVar(this, var);
  }

  public void setBoolVar(ConfVars var, boolean val) {
    setBoolVar(this, var, val);
  }

  public static String getVar(Configuration conf, ConfVars var) {
    assert (var.valClass == String.class) : var.varname;
    return conf.get(var.varname, var.defaultStrVal);
  }

  public static String getVar(Configuration conf, ConfVars var, String defaultVal) {
    return conf.get(var.varname, defaultVal);
  }

  public static void setVar(Configuration conf, ConfVars var, String val) {
    assert (var.valClass == String.class) : var.varname;
    conf.set(var.varname, val);
  }

  public static ConfVars getConfVars(String name) {
    return vars.get(name);
  }

  public static ConfVars getMetaConf(String name) {
    return metaConfs.get(name);
  }

  public String getVar(ConfVars var) {
    return getVar(this, var);
  }

  public void setVar(ConfVars var, String val) {
    setVar(this, var, val);
  }

  public void logVars(PrintStream ps) {
    for (ConfVars one : ConfVars.values()) {
      ps.println(one.varname + "=" + ((get(one.varname) != null) ? get(one.varname) : ""));
    }
  }

  public HiveConf() {
    super();
    initialize(this.getClass());
  }

  public HiveConf(Class<?> cls) {
    super();
    initialize(cls);
  }

  public HiveConf(Configuration other, Class<?> cls) {
    super(other);
    initialize(cls);
  }

  /**
   * Copy constructor
   */
  public HiveConf(HiveConf other) {
    super(other);
    hiveJar = other.hiveJar;
    auxJars = other.auxJars;
    origProp = (Properties)other.origProp.clone();
    restrictList.addAll(other.restrictList);
    modWhiteListPattern = other.modWhiteListPattern;
  }

  public Properties getAllProperties() {
    return getProperties(this);
  }

  private static Properties getProperties(Configuration conf) {
    Iterator<Map.Entry<String, String>> iter = conf.iterator();
    Properties p = new Properties();
    while (iter.hasNext()) {
      Map.Entry<String, String> e = iter.next();
      p.setProperty(e.getKey(), e.getValue());
    }
    return p;
  }

  private void initialize(Class<?> cls) {
    hiveJar = (new JobConf(cls)).getJar();

    // preserve the original configuration
    origProp = getAllProperties();

    // Overlay the ConfVars. Note that this ignores ConfVars with null values
    addResource(getConfVarInputStream());

    // Overlay hive-site.xml if it exists
    if (hiveSiteURL != null) {
      addResource(hiveSiteURL);
    }

    // if embedded metastore is to be used as per config so far
    // then this is considered like the metastore server case
    String msUri = this.getVar(HiveConf.ConfVars.METASTOREURIS);
    if(HiveConfUtil.isEmbeddedMetaStore(msUri)){
      setLoadMetastoreConfig(true);
    }

    // load hivemetastore-site.xml if this is metastore and file exists
    if (isLoadMetastoreConfig() && hivemetastoreSiteUrl != null) {
      addResource(hivemetastoreSiteUrl);
    }

    // load hiveserver2-site.xml if this is hiveserver2 and file exists
    // metastore can be embedded within hiveserver2, in such cases
    // the conf params in hiveserver2-site.xml will override whats defined
    // in hivemetastore-site.xml
    if (isLoadHiveServer2Config() && hiveServer2SiteUrl != null) {
      addResource(hiveServer2SiteUrl);
    }

    // Overlay the values of any system properties whose names appear in the list of ConfVars
    applySystemProperties();

    if ((this.get("hive.metastore.ds.retry.attempts") != null) ||
      this.get("hive.metastore.ds.retry.interval") != null) {
        l4j.warn("DEPRECATED: hive.metastore.ds.retry.* no longer has any effect.  " +
        "Use hive.hmshandler.retry.* instead");
    }

    // if the running class was loaded directly (through eclipse) rather than through a
    // jar then this would be needed
    if (hiveJar == null) {
      hiveJar = this.get(ConfVars.HIVEJAR.varname);
    }

    if (auxJars == null) {
      auxJars = this.get(ConfVars.HIVEAUXJARS.varname);
    }

    if (getBoolVar(ConfVars.METASTORE_SCHEMA_VERIFICATION)) {
      setBoolVar(ConfVars.METASTORE_AUTO_CREATE_SCHEMA, false);
      setBoolVar(ConfVars.METASTORE_FIXED_DATASTORE, true);
    }

    if (getBoolVar(HiveConf.ConfVars.HIVECONFVALIDATION)) {
      List<String> trimmed = new ArrayList<String>();
      for (Map.Entry<String,String> entry : this) {
        String key = entry.getKey();
        if (key == null || !key.startsWith("hive.")) {
          continue;
        }
        ConfVars var = HiveConf.getConfVars(key);
        if (var == null) {
          var = HiveConf.getConfVars(key.trim());
          if (var != null) {
            trimmed.add(key);
          }
        }
        if (var == null) {
          l4j.warn("HiveConf of name " + key + " does not exist");
        } else if (!var.isType(entry.getValue())) {
          l4j.warn("HiveConf " + var.varname + " expects " + var.typeString() + " type value");
        }
      }
      for (String key : trimmed) {
        set(key.trim(), getRaw(key));
        unset(key);
      }
    }

    setupSQLStdAuthWhiteList();

    // setup list of conf vars that are not allowed to change runtime
    setupRestrictList();

  }

  /**
   * If the config whitelist param for sql standard authorization is not set, set it up here.
   */
  private void setupSQLStdAuthWhiteList() {
    String whiteListParamsStr = getVar(ConfVars.HIVE_AUTHORIZATION_SQL_STD_AUTH_CONFIG_WHITELIST);
    if (whiteListParamsStr == null || whiteListParamsStr.trim().isEmpty()) {
      // set the default configs in whitelist
      whiteListParamsStr = getSQLStdAuthDefaultWhiteListPattern();
    }
    setVar(ConfVars.HIVE_AUTHORIZATION_SQL_STD_AUTH_CONFIG_WHITELIST, whiteListParamsStr);
  }

  private static String getSQLStdAuthDefaultWhiteListPattern() {
    // create the default white list from list of safe config params
    // and regex list
    String confVarPatternStr = Joiner.on("|").join(convertVarsToRegex(sqlStdAuthSafeVarNames));
    String regexPatternStr = Joiner.on("|").join(sqlStdAuthSafeVarNameRegexes);
    return regexPatternStr + "|" + confVarPatternStr;
  }

  /**
   * @param paramList  list of parameter strings
   * @return list of parameter strings with "." replaced by "\."
   */
  private static String[] convertVarsToRegex(String[] paramList) {
    String[] regexes = new String[paramList.length];
    for(int i=0; i<paramList.length; i++) {
      regexes[i] = paramList[i].replace(".", "\\." );
    }
    return regexes;
  }

  /**
   * Default list of modifiable config parameters for sql standard authorization
   * For internal use only.
   */
  private static final String [] sqlStdAuthSafeVarNames = new String [] {
    ConfVars.BYTESPERREDUCER.varname,
    ConfVars.CLIENT_STATS_COUNTERS.varname,
    ConfVars.DEFAULTPARTITIONNAME.varname,
    ConfVars.DROPIGNORESNONEXISTENT.varname,
    ConfVars.HIVECOUNTERGROUP.varname,
    ConfVars.HIVEDEFAULTMANAGEDFILEFORMAT.varname,
    ConfVars.HIVEENFORCEBUCKETING.varname,
    ConfVars.HIVEENFORCEBUCKETMAPJOIN.varname,
    ConfVars.HIVEENFORCESORTING.varname,
    ConfVars.HIVEENFORCESORTMERGEBUCKETMAPJOIN.varname,
    ConfVars.HIVEEXPREVALUATIONCACHE.varname,
    ConfVars.HIVEHASHTABLELOADFACTOR.varname,
    ConfVars.HIVEHASHTABLETHRESHOLD.varname,
    ConfVars.HIVEIGNOREMAPJOINHINT.varname,
    ConfVars.HIVELIMITMAXROWSIZE.varname,
    ConfVars.HIVEMAPREDMODE.varname,
    ConfVars.HIVEMAPSIDEAGGREGATE.varname,
    ConfVars.HIVEOPTIMIZEMETADATAQUERIES.varname,
    ConfVars.HIVEROWOFFSET.varname,
    ConfVars.HIVEVARIABLESUBSTITUTE.varname,
    ConfVars.HIVEVARIABLESUBSTITUTEDEPTH.varname,
    ConfVars.HIVE_AUTOGEN_COLUMNALIAS_PREFIX_INCLUDEFUNCNAME.varname,
    ConfVars.HIVE_AUTOGEN_COLUMNALIAS_PREFIX_LABEL.varname,
    ConfVars.HIVE_CHECK_CROSS_PRODUCT.varname,
    ConfVars.HIVE_COMPAT.varname,
    ConfVars.HIVE_CONCATENATE_CHECK_INDEX.varname,
    ConfVars.HIVE_DISPLAY_PARTITION_COLUMNS_SEPARATELY.varname,
    ConfVars.HIVE_ERROR_ON_EMPTY_PARTITION.varname,
    ConfVars.HIVE_EXECUTION_ENGINE.varname,
    ConfVars.HIVE_EXIM_URI_SCHEME_WL.varname,
    ConfVars.HIVE_FILE_MAX_FOOTER.varname,
    ConfVars.HIVE_HADOOP_SUPPORTS_SUBDIRECTORIES.varname,
    ConfVars.HIVE_INSERT_INTO_MULTILEVEL_DIRS.varname,
    ConfVars.HIVE_LOCALIZE_RESOURCE_NUM_WAIT_ATTEMPTS.varname,
    ConfVars.HIVE_MULTI_INSERT_MOVE_TASKS_SHARE_DEPENDENCIES.varname,
    ConfVars.HIVE_QUOTEDID_SUPPORT.varname,
    ConfVars.HIVE_RESULTSET_USE_UNIQUE_COLUMN_NAMES.varname,
    ConfVars.HIVE_STATS_COLLECT_PART_LEVEL_STATS.varname,
    ConfVars.HIVE_SERVER2_LOGGING_OPERATION_LEVEL.varname,
    ConfVars.HIVE_SUPPORT_SQL11_RESERVED_KEYWORDS.varname,
    ConfVars.JOB_DEBUG_CAPTURE_STACKTRACES.varname,
    ConfVars.JOB_DEBUG_TIMEOUT.varname,
    ConfVars.MAXCREATEDFILES.varname,
    ConfVars.MAXREDUCERS.varname,
    ConfVars.NWAYJOINREORDER.varname,
    ConfVars.OUTPUT_FILE_EXTENSION.varname,
    ConfVars.SHOW_JOB_FAIL_DEBUG_INFO.varname,
    ConfVars.TASKLOG_DEBUG_TIMEOUT.varname,
  };

  /**
   * Default list of regexes for config parameters that are modifiable with
   * sql standard authorization enabled
   */
  static final String [] sqlStdAuthSafeVarNameRegexes = new String [] {
    "hive\\.auto\\..*",
    "hive\\.cbo\\..*",
    "hive\\.convert\\..*",
    "hive\\.exec\\.dynamic\\.partition.*",
    "hive\\.exec\\..*\\.dynamic\\.partitions\\..*",
    "hive\\.exec\\.compress\\..*",
    "hive\\.exec\\.infer\\..*",
    "hive\\.exec\\.mode.local\\..*",
    "hive\\.exec\\.orc\\..*",
    "hive\\.exec\\.parallel.*",
    "hive\\.explain\\..*",
    "hive\\.fetch.task\\..*",
    "hive\\.groupby\\..*",
    "hive\\.hbase\\..*",
    "hive\\.index\\..*",
    "hive\\.index\\..*",
    "hive\\.intermediate\\..*",
    "hive\\.join\\..*",
    "hive\\.limit\\..*",
    "hive\\.log\\..*",
    "hive\\.mapjoin\\..*",
    "hive\\.merge\\..*",
    "hive\\.optimize\\..*",
    "hive\\.orc\\..*",
    "hive\\.outerjoin\\..*",
    "hive\\.parquet\\..*",
    "hive\\.ppd\\..*",
    "hive\\.prewarm\\..*",
    "hive\\.server2\\.proxy\\.user",
    "hive\\.skewjoin\\..*",
    "hive\\.smbjoin\\..*",
    "hive\\.stats\\..*",
    "hive\\.tez\\..*",
    "hive\\.vectorized\\..*",
    "mapred\\.map\\..*",
    "mapred\\.reduce\\..*",
    "mapred\\.output\\.compression\\.codec",
    "mapred\\.job\\.queuename",
    "mapred\\.output\\.compression\\.type",
    "mapred\\.min\\.split\\.size",
    "mapreduce\\.job\\.reduce\\.slowstart\\.completedmaps",
    "mapreduce\\.job\\.queuename",
    "mapreduce\\.input\\.fileinputformat\\.split\\.minsize",
    "mapreduce\\.map\\..*",
    "mapreduce\\.reduce\\..*",
    "mapreduce\\.output\\.fileoutputformat\\.compress\\.codec",
    "mapreduce\\.output\\.fileoutputformat\\.compress\\.type",
    "tez\\.am\\..*",
    "tez\\.task\\..*",
    "tez\\.runtime\\..*",
    "tez.queue.name",
  };



  /**
   * Apply system properties to this object if the property name is defined in ConfVars
   * and the value is non-null and not an empty string.
   */
  private void applySystemProperties() {
    Map<String, String> systemProperties = getConfSystemProperties();
    for (Entry<String, String> systemProperty : systemProperties.entrySet()) {
      this.set(systemProperty.getKey(), systemProperty.getValue());
    }
  }

  /**
   * This method returns a mapping from config variable name to its value for all config variables
   * which have been set using System properties
   */
  public static Map<String, String> getConfSystemProperties() {
    Map<String, String> systemProperties = new HashMap<String, String>();

    for (ConfVars oneVar : ConfVars.values()) {
      if (System.getProperty(oneVar.varname) != null) {
        if (System.getProperty(oneVar.varname).length() > 0) {
          systemProperties.put(oneVar.varname, System.getProperty(oneVar.varname));
        }
      }
    }

    return systemProperties;
  }

  /**
   * Overlays ConfVar properties with non-null values
   */
  private static void applyDefaultNonNullConfVars(Configuration conf) {
    for (ConfVars var : ConfVars.values()) {
      String defaultValue = var.getDefaultValue();
      if (defaultValue == null) {
        // Don't override ConfVars with null values
        continue;
      }
      conf.set(var.varname, defaultValue);
    }
  }

  public Properties getChangedProperties() {
    Properties ret = new Properties();
    Properties newProp = getAllProperties();

    for (Object one : newProp.keySet()) {
      String oneProp = (String) one;
      String oldValue = origProp.getProperty(oneProp);
      if (!StringUtils.equals(oldValue, newProp.getProperty(oneProp))) {
        ret.setProperty(oneProp, newProp.getProperty(oneProp));
      }
    }
    return (ret);
  }

  public String getJar() {
    return hiveJar;
  }

  /**
   * @return the auxJars
   */
  public String getAuxJars() {
    return auxJars;
  }

  /**
   * @param auxJars the auxJars to set
   */
  public void setAuxJars(String auxJars) {
    this.auxJars = auxJars;
    setVar(this, ConfVars.HIVEAUXJARS, auxJars);
  }

  public URL getHiveDefaultLocation() {
    return hiveDefaultURL;
  }

  public static void setHiveSiteLocation(URL location) {
    hiveSiteURL = location;
  }

  public static URL getHiveSiteLocation() {
    return hiveSiteURL;
  }

  public static URL getMetastoreSiteLocation() {
    return hivemetastoreSiteUrl;
  }

  public static URL getHiveServer2SiteLocation() {
    return hiveServer2SiteUrl;
  }

  /**
   * @return the user name set in hadoop.job.ugi param or the current user from System
   * @throws IOException
   */
  public String getUser() throws IOException {
    try {
      UserGroupInformation ugi = Utils.getUGI();
      return ugi.getUserName();
    } catch (LoginException le) {
      throw new IOException(le);
    }
  }

  public static String getColumnInternalName(int pos) {
    return "_col" + pos;
  }

  public static int getPositionFromInternalName(String internalName) {
    Pattern internalPattern = Pattern.compile("_col([0-9]+)");
    Matcher m = internalPattern.matcher(internalName);
    if (!m.matches()){
      return -1;
    } else {
      return Integer.parseInt(m.group(1));
    }
  }

  /**
   * Append comma separated list of config vars to the restrict List
   * @param restrictListStr
   */
  public void addToRestrictList(String restrictListStr) {
    if (restrictListStr == null) {
      return;
    }
    String oldList = this.getVar(ConfVars.HIVE_CONF_RESTRICTED_LIST);
    if (oldList == null || oldList.isEmpty()) {
      this.setVar(ConfVars.HIVE_CONF_RESTRICTED_LIST, restrictListStr);
    } else {
      this.setVar(ConfVars.HIVE_CONF_RESTRICTED_LIST, oldList + "," + restrictListStr);
    }
    setupRestrictList();
  }

  /**
   * Set white list of parameters that are allowed to be modified
   *
   * @param paramNameRegex
   */
  @LimitedPrivate(value = { "Currently only for use by HiveAuthorizer" })
  public void setModifiableWhiteListRegex(String paramNameRegex) {
    if (paramNameRegex == null) {
      return;
    }
    modWhiteListPattern = Pattern.compile(paramNameRegex);
  }

  /**
   * Add the HIVE_CONF_RESTRICTED_LIST values to restrictList,
   * including HIVE_CONF_RESTRICTED_LIST itself
   */
  private void setupRestrictList() {
    String restrictListStr = this.getVar(ConfVars.HIVE_CONF_RESTRICTED_LIST);
    restrictList.clear();
    if (restrictListStr != null) {
      for (String entry : restrictListStr.split(",")) {
        restrictList.add(entry.trim());
      }
    }
    restrictList.add(ConfVars.HIVE_IN_TEST.varname);
    restrictList.add(ConfVars.HIVE_CONF_RESTRICTED_LIST.varname);
  }

  public static boolean isLoadMetastoreConfig() {
    return loadMetastoreConfig;
  }

  public static void setLoadMetastoreConfig(boolean loadMetastoreConfig) {
    HiveConf.loadMetastoreConfig = loadMetastoreConfig;
  }

  public static boolean isLoadHiveServer2Config() {
    return loadHiveServer2Config;
  }

  public static void setLoadHiveServer2Config(boolean loadHiveServer2Config) {
    HiveConf.loadHiveServer2Config = loadHiveServer2Config;
  }
}


File: common/src/java/org/apache/hive/common/util/BloomFilter.java
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

package org.apache.hive.common.util;

import static com.google.common.base.Preconditions.checkArgument;

import java.util.Arrays;

/**
 * BloomFilter is a probabilistic data structure for set membership check. BloomFilters are
 * highly space efficient when compared to using a HashSet. Because of the probabilistic nature of
 * bloom filter false positive (element not present in bloom filter but test() says true) are
 * possible but false negatives are not possible (if element is present then test() will never
 * say false). The false positive probability is configurable (default: 5%) depending on which
 * storage requirement may increase or decrease. Lower the false positive probability greater
 * is the space requirement.
 * Bloom filters are sensitive to number of elements that will be inserted in the bloom filter.
 * During the creation of bloom filter expected number of entries must be specified. If the number
 * of insertions exceed the specified initial number of entries then false positive probability will
 * increase accordingly.
 *
 * Internally, this implementation of bloom filter uses Murmur3 fast non-cryptographic hash
 * algorithm. Although Murmur2 is slightly faster than Murmur3 in Java, it suffers from hash
 * collisions for specific sequence of repeating bytes. Check the following link for more info
 * https://code.google.com/p/smhasher/wiki/MurmurHash2Flaw
 */
public class BloomFilter {
  public static final double DEFAULT_FPP = 0.05;
  protected BitSet bitSet;
  protected int numBits;
  protected int numHashFunctions;

  public BloomFilter() {
  }

  public BloomFilter(long expectedEntries) {
    this(expectedEntries, DEFAULT_FPP);
  }

  public BloomFilter(long expectedEntries, double fpp) {
    checkArgument(expectedEntries > 0, "expectedEntries should be > 0");
    checkArgument(fpp > 0.0 && fpp < 1.0, "False positive probability should be > 0.0 & < 1.0");
    int nb = optimalNumOfBits(expectedEntries, fpp);
    // make 'm' multiple of 64
    this.numBits = nb + (Long.SIZE - (nb % Long.SIZE));
    this.numHashFunctions = optimalNumOfHashFunctions(expectedEntries, numBits);
    this.bitSet = new BitSet(numBits);
  }

  static int optimalNumOfHashFunctions(long n, long m) {
    return Math.max(1, (int) Math.round((double) m / n * Math.log(2)));
  }

  static int optimalNumOfBits(long n, double p) {
    return (int) (-n * Math.log(p) / (Math.log(2) * Math.log(2)));
  }

  public void add(byte[] val) {
    if (val == null) {
      addBytes(val, -1);
    } else {
      addBytes(val, val.length);
    }
  }

  public void addBytes(byte[] val, int length) {
    // We use the trick mentioned in "Less Hashing, Same Performance: Building a Better Bloom Filter"
    // by Kirsch et.al. From abstract 'only two hash functions are necessary to effectively
    // implement a Bloom filter without any loss in the asymptotic false positive probability'

    // Lets split up 64-bit hashcode into two 32-bit hash codes and employ the technique mentioned
    // in the above paper
    long hash64 = val == null ? Murmur3.NULL_HASHCODE : Murmur3.hash64(val, length);
    addHash(hash64);
  }

  private void addHash(long hash64) {
    int hash1 = (int) hash64;
    int hash2 = (int) (hash64 >>> 32);

    for (int i = 1; i <= numHashFunctions; i++) {
      int combinedHash = hash1 + (i * hash2);
      // hashcode should be positive, flip all the bits if it's negative
      if (combinedHash < 0) {
        combinedHash = ~combinedHash;
      }
      int pos = combinedHash % numBits;
      bitSet.set(pos);
    }
  }

  public void addString(String val) {
    if (val == null) {
      add(null);
    } else {
      add(val.getBytes());
    }
  }

  public void addLong(long val) {
    addHash(getLongHash(val));
  }

  public void addDouble(double val) {
    addLong(Double.doubleToLongBits(val));
  }

  public boolean test(byte[] val) {
    if (val == null) {
      return testBytes(val, -1);
    }
    return testBytes(val, val.length);
  }

  public boolean testBytes(byte[] val, int length) {
    long hash64 = val == null ? Murmur3.NULL_HASHCODE : Murmur3.hash64(val, length);
    return testHash(hash64);
  }

  private boolean testHash(long hash64) {
    int hash1 = (int) hash64;
    int hash2 = (int) (hash64 >>> 32);

    for (int i = 1; i <= numHashFunctions; i++) {
      int combinedHash = hash1 + (i * hash2);
      // hashcode should be positive, flip all the bits if it's negative
      if (combinedHash < 0) {
        combinedHash = ~combinedHash;
      }
      int pos = combinedHash % numBits;
      if (!bitSet.get(pos)) {
        return false;
      }
    }
    return true;
  }

  public boolean testString(String val) {
    if (val == null) {
      return test(null);
    } else {
      return test(val.getBytes());
    }
  }

  public boolean testLong(long val) {
    return testHash(getLongHash(val));
  }

  // Thomas Wang's integer hash function
  // http://web.archive.org/web/20071223173210/http://www.concentric.net/~Ttwang/tech/inthash.htm
  private long getLongHash(long key) {
    key = (~key) + (key << 21); // key = (key << 21) - key - 1;
    key = key ^ (key >> 24);
    key = (key + (key << 3)) + (key << 8); // key * 265
    key = key ^ (key >> 14);
    key = (key + (key << 2)) + (key << 4); // key * 21
    key = key ^ (key >> 28);
    key = key + (key << 31);
    return key;
  }

  public boolean testDouble(double val) {
    return testLong(Double.doubleToLongBits(val));
  }

  public long sizeInBytes() {
    return getBitSize() / 8;
  }

  public int getBitSize() {
    return bitSet.getData().length * Long.SIZE;
  }

  public int getNumHashFunctions() {
    return numHashFunctions;
  }

  public long[] getBitSet() {
    return bitSet.getData();
  }

  @Override
  public String toString() {
    return "m: " + numBits + " k: " + numHashFunctions;
  }

  /**
   * Merge the specified bloom filter with current bloom filter.
   *
   * @param that - bloom filter to merge
   */
  public void merge(BloomFilter that) {
    if (this != that && this.numBits == that.numBits && this.numHashFunctions == that.numHashFunctions) {
      this.bitSet.putAll(that.bitSet);
    } else {
      throw new IllegalArgumentException("BloomFilters are not compatible for merging." +
          " this - " + this.toString() + " that - " + that.toString());
    }
  }

  public void reset() {
    this.bitSet.clear();
  }

  /**
   * Bare metal bit set implementation. For performance reasons, this implementation does not check
   * for index bounds nor expand the bit set size if the specified index is greater than the size.
   */
  public class BitSet {
    private final long[] data;

    public BitSet(long bits) {
      this(new long[(int) Math.ceil((double) bits / (double) Long.SIZE)]);
    }

    /**
     * Deserialize long array as bit set.
     *
     * @param data - bit array
     */
    public BitSet(long[] data) {
      assert data.length > 0 : "data length is zero!";
      this.data = data;
    }

    /**
     * Sets the bit at specified index.
     *
     * @param index - position
     */
    public void set(int index) {
      data[index >>> 6] |= (1L << index);
    }

    /**
     * Returns true if the bit is set in the specified index.
     *
     * @param index - position
     * @return - value at the bit position
     */
    public boolean get(int index) {
      return (data[index >>> 6] & (1L << index)) != 0;
    }

    /**
     * Number of bits
     */
    public long bitSize() {
      return (long) data.length * Long.SIZE;
    }

    public long[] getData() {
      return data;
    }

    /**
     * Combines the two BitArrays using bitwise OR.
     */
    public void putAll(BitSet array) {
      assert data.length == array.data.length :
          "BitArrays must be of equal length (" + data.length + "!= " + array.data.length + ")";
      for (int i = 0; i < data.length; i++) {
        data[i] |= array.data[i];
      }
    }

    /**
     * Clear the bit set.
     */
    public void clear() {
      Arrays.fill(data, 0);
    }
  }
}


File: metastore/src/gen/protobuf/gen-java/org/apache/hadoop/hive/metastore/hbase/HbaseMetastoreProto.java


File: metastore/src/java/org/apache/hadoop/hive/metastore/hbase/Counter.java
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
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.hadoop.hive.metastore.hbase;

/**
 * A simple metric to count how many times something occurs.
 */
class Counter {
  private final String name;
  private long cnt;

  Counter(String name) {
    this.name = name;
    cnt = 0;
  }

  void incr() {
    cnt++;
  }

  void clear() {
    cnt = 0;
  }

  String dump() {
    StringBuilder bldr = new StringBuilder("Dumping metric: ");
    bldr.append(name).append(' ').append(cnt);
    return bldr.toString();
  }

}


File: metastore/src/java/org/apache/hadoop/hive/metastore/hbase/HBaseReadWrite.java
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
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.hadoop.hive.metastore.hbase;

import com.google.common.annotations.VisibleForTesting;
import org.apache.commons.codec.binary.Base64;
import org.apache.commons.lang.ArrayUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.client.Delete;
import org.apache.hadoop.hbase.client.Get;
import org.apache.hadoop.hbase.client.HTableInterface;
import org.apache.hadoop.hbase.client.Put;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.filter.CompareFilter;
import org.apache.hadoop.hbase.filter.Filter;
import org.apache.hadoop.hbase.filter.RegexStringComparator;
import org.apache.hadoop.hbase.filter.RowFilter;
import org.apache.hadoop.hive.common.ObjectPair;
import org.apache.hive.common.util.BloomFilter;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.metastore.AggregateStatsCache;
import org.apache.hadoop.hive.metastore.api.AggrStats;
import org.apache.hadoop.hive.metastore.api.ColumnStatistics;
import org.apache.hadoop.hive.metastore.api.ColumnStatisticsDesc;
import org.apache.hadoop.hive.metastore.api.ColumnStatisticsObj;
import org.apache.hadoop.hive.metastore.api.Database;
import org.apache.hadoop.hive.metastore.api.Function;
import org.apache.hadoop.hive.metastore.api.NoSuchObjectException;
import org.apache.hadoop.hive.metastore.api.Partition;
import org.apache.hadoop.hive.metastore.api.PrincipalPrivilegeSet;
import org.apache.hadoop.hive.metastore.api.PrincipalType;
import org.apache.hadoop.hive.metastore.api.Role;
import org.apache.hadoop.hive.metastore.api.StorageDescriptor;
import org.apache.hadoop.hive.metastore.api.Table;
import org.apache.hadoop.hive.metastore.hbase.stats.ColumnStatsAggregator;
import org.apache.hadoop.hive.metastore.hbase.stats.ColumnStatsAggregatorFactory;

import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;


/**
 * Class to manage storing object in and reading them from HBase.
 */
class HBaseReadWrite {

  @VisibleForTesting final static String DB_TABLE = "HBMS_DBS";
  @VisibleForTesting final static String FUNC_TABLE = "HBMS_FUNCS";
  @VisibleForTesting final static String GLOBAL_PRIVS_TABLE = "HBMS_GLOBAL_PRIVS";
  @VisibleForTesting final static String PART_TABLE = "HBMS_PARTITIONS";
  @VisibleForTesting final static String ROLE_TABLE = "HBMS_ROLES";
  @VisibleForTesting final static String SD_TABLE = "HBMS_SDS";
  @VisibleForTesting final static String TABLE_TABLE = "HBMS_TBLS";
  @VisibleForTesting final static String USER_TO_ROLE_TABLE = "HBMS_USER_TO_ROLE";
  @VisibleForTesting final static byte[] CATALOG_CF = "c".getBytes(HBaseUtils.ENCODING);
  @VisibleForTesting final static byte[] STATS_CF = "s".getBytes(HBaseUtils.ENCODING);
  @VisibleForTesting final static String NO_CACHE_CONF = "no.use.cache";
  /**
   * List of tables in HBase
   */
  final static String[] tableNames = { DB_TABLE, FUNC_TABLE, GLOBAL_PRIVS_TABLE, PART_TABLE,
                                       USER_TO_ROLE_TABLE, ROLE_TABLE, SD_TABLE, TABLE_TABLE  };
  final static Map<String, List<byte[]>> columnFamilies =
      new HashMap<String, List<byte[]>> (tableNames.length);

  static {
    columnFamilies.put(DB_TABLE, Arrays.asList(CATALOG_CF));
    columnFamilies.put(FUNC_TABLE, Arrays.asList(CATALOG_CF));
    columnFamilies.put(GLOBAL_PRIVS_TABLE, Arrays.asList(CATALOG_CF));
    columnFamilies.put(PART_TABLE, Arrays.asList(CATALOG_CF, STATS_CF));
    columnFamilies.put(USER_TO_ROLE_TABLE, Arrays.asList(CATALOG_CF));
    columnFamilies.put(ROLE_TABLE, Arrays.asList(CATALOG_CF));
    columnFamilies.put(SD_TABLE, Arrays.asList(CATALOG_CF));
    columnFamilies.put(TABLE_TABLE, Arrays.asList(CATALOG_CF, STATS_CF));
  }

  private final static byte[] CATALOG_COL = "cat".getBytes(HBaseUtils.ENCODING);
  private final static byte[] ROLES_COL = "roles".getBytes(HBaseUtils.ENCODING);
  private final static byte[] REF_COUNT_COL = "ref".getBytes(HBaseUtils.ENCODING);
  private final static byte[] GLOBAL_PRIVS_KEY = "globalprivs".getBytes(HBaseUtils.ENCODING);
  private final static int TABLES_TO_CACHE = 10;

  @VisibleForTesting final static String TEST_CONN = "test_connection";
  private static HBaseConnection testConn;

  static final private Log LOG = LogFactory.getLog(HBaseReadWrite.class.getName());

  private static ThreadLocal<HBaseReadWrite> self = new ThreadLocal<HBaseReadWrite>() {
    @Override
    protected HBaseReadWrite initialValue() {
      if (staticConf == null) {
        throw new RuntimeException("Attempt to create HBaseReadWrite with no configuration set");
      }
      return new HBaseReadWrite(staticConf);
    }
  };

  private static boolean tablesCreated = false;
  private static Configuration staticConf = null;

  private final Configuration conf;
  private HBaseConnection conn;
  private MessageDigest md;
  private ObjectCache<ObjectPair<String, String>, Table> tableCache;
  private ObjectCache<ByteArrayWrapper, StorageDescriptor> sdCache;
  private PartitionCache partCache;
  private AggregateStatsCache aggrStatsCache;
  private Counter tableHits;
  private Counter tableMisses;
  private Counter tableOverflows;
  private Counter partHits;
  private Counter partMisses;
  private Counter partOverflows;
  private Counter sdHits;
  private Counter sdMisses;
  private Counter sdOverflows;
  private List<Counter> counters;
  // roleCache doesn't use ObjectCache because I don't want to limit the size.  I am assuming
  // that the number of roles will always be small (< 100) so caching the whole thing should not
  // be painful.
  private final Map<String, HbaseMetastoreProto.RoleGrantInfoList> roleCache;
  boolean entireRoleTableInCache;

  /**
   * Get the instance of HBaseReadWrite for the current thread.  This is intended to be used by
   * {@link org.apache.hadoop.hive.metastore.hbase.HBaseStore} since it creates the thread local
   * version of this class.
   * @param configuration Configuration object
   * @return thread's instance of HBaseReadWrite
   */
  static HBaseReadWrite getInstance(Configuration configuration) {
    staticConf = configuration;
    return self.get();
  }

  /**
   * Get the instance of HBaseReadWrite for the current thread.  This is inteded to be used after
   * the thread has been initialized.  Woe betide you if that's not the case.
   * @return thread's instance of HBaseReadWrite
   */
  static HBaseReadWrite getInstance() {
    return self.get();
  }

  private HBaseReadWrite(Configuration configuration) {
    conf = configuration;
    HBaseConfiguration.addHbaseResources(conf);

    try {
      String connClass = HiveConf.getVar(conf, HiveConf.ConfVars.METASTORE_HBASE_CONNECTION_CLASS);
      if (TEST_CONN.equals(connClass)) {
        conn = testConn;
        LOG.debug("Using test connection.");
      } else {
        LOG.debug("Instantiating connection class " + connClass);
        Class c = Class.forName(connClass);
        Object o = c.newInstance();
        if (HBaseConnection.class.isAssignableFrom(o.getClass())) {
          conn = (HBaseConnection) o;
        } else {
          throw new IOException(connClass + " is not an instance of HBaseConnection.");
        }
        conn.setConf(conf);
        conn.connect();
      }
    } catch (Exception e) {
      throw new RuntimeException(e);
    }

    try {
      md = MessageDigest.getInstance("MD5");
    } catch (NoSuchAlgorithmException e) {
      throw new RuntimeException(e);
    }
    int totalCatalogObjectsToCache =
        HiveConf.getIntVar(conf, HiveConf.ConfVars.METASTORE_HBASE_CATALOG_CACHE_SIZE);

    tableHits = new Counter("table cache hits");
    tableMisses = new Counter("table cache misses");
    tableOverflows = new Counter("table cache overflows");
    partHits = new Counter("partition cache hits");
    partMisses = new Counter("partition cache misses");
    partOverflows = new Counter("partition cache overflows");
    sdHits = new Counter("storage descriptor cache hits");
    sdMisses = new Counter("storage descriptor cache misses");
    sdOverflows = new Counter("storage descriptor cache overflows");
    counters = new ArrayList<Counter>();
    counters.add(tableHits);
    counters.add(tableMisses);
    counters.add(tableOverflows);
    counters.add(partHits);
    counters.add(partMisses);
    counters.add(partOverflows);
    counters.add(sdHits);
    counters.add(sdMisses);
    counters.add(sdOverflows);

    // Give 1% of catalog cache space to storage descriptors
    // (storage descriptors are shared, so 99% should be the same for a given table)
    int sdsCacheSize = totalCatalogObjectsToCache / 100;
    if (conf.getBoolean(NO_CACHE_CONF, false)) {
      tableCache = new BogusObjectCache<ObjectPair<String, String>, Table>();
      sdCache = new BogusObjectCache<ByteArrayWrapper, StorageDescriptor>();
      partCache = new BogusPartitionCache();
    } else {
      tableCache = new ObjectCache<ObjectPair<String, String>, Table>(TABLES_TO_CACHE, tableHits,
          tableMisses, tableOverflows);
      sdCache = new ObjectCache<ByteArrayWrapper, StorageDescriptor>(sdsCacheSize, sdHits,
          sdMisses, sdOverflows);
      partCache = new PartitionCache(totalCatalogObjectsToCache, partHits, partMisses, partOverflows);
      aggrStatsCache = AggregateStatsCache.getInstance(conf);
    }
    roleCache = new HashMap<String, HbaseMetastoreProto.RoleGrantInfoList>();
    entireRoleTableInCache = false;
  }

  // Synchronize this so not everyone's doing it at once.
  static synchronized void createTablesIfNotExist() throws IOException {
    if (!tablesCreated) {
      for (String name : tableNames) {
        if (self.get().conn.getHBaseTable(name, true) == null) {
          List<byte[]> families = columnFamilies.get(name);
          self.get().conn.createHBaseTable(name, families);
          /*
          List<byte[]> columnFamilies = new ArrayList<byte[]>();
          columnFamilies.add(CATALOG_CF);
          if (TABLE_TABLE.equals(name) || PART_TABLE.equals(name)) {
            columnFamilies.add(STATS_CF);
          }
          self.get().conn.createHBaseTable(name, columnFamilies);
          */
        }
      }
      tablesCreated = true;
    }
  }

  /**********************************************************************************************
   * Transaction related methods
   *********************************************************************************************/

  /**
   * Begin a transaction
   */
  void begin() {
    try {
      conn.beginTransaction();
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  /**
   * Commit a transaction
   */
  void commit() {
    try {
      conn.commitTransaction();
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  void rollback() {
    try {
      conn.rollbackTransaction();
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  void close() throws IOException {
    conn.close();
  }

  /**********************************************************************************************
   * Database related methods
   *********************************************************************************************/

  /**
   * Fetch a database object
   * @param name name of the database to fetch
   * @return the database object, or null if there is no such database
   * @throws IOException
   */
  Database getDb(String name) throws IOException {
    byte[] key = HBaseUtils.buildKey(name);
    byte[] serialized = read(DB_TABLE, key, CATALOG_CF, CATALOG_COL);
    if (serialized == null) return null;
    return HBaseUtils.deserializeDatabase(name, serialized);
  }

  /**
   * Get a list of databases.
   * @param regex Regular expression to use in searching for database names.  It is expected to
   *              be a Java regular expression.  If it is null then all databases will be returned.
   * @return list of databases matching the regular expression.
   * @throws IOException
   */
  List<Database> scanDatabases(String regex) throws IOException {
    Filter filter = null;
    if (regex != null) {
      filter = new RowFilter(CompareFilter.CompareOp.EQUAL, new RegexStringComparator(regex));
    }
    Iterator<Result> iter =
        scan(DB_TABLE, CATALOG_CF, CATALOG_COL, filter);
    List<Database> databases = new ArrayList<Database>();
    while (iter.hasNext()) {
      Result result = iter.next();
      databases.add(HBaseUtils.deserializeDatabase(result.getRow(),
          result.getValue(CATALOG_CF, CATALOG_COL)));
    }
    return databases;
  }

  /**
   * Store a database object
   * @param database database object to store
   * @throws IOException
   */
  void putDb(Database database) throws IOException {
    byte[][] serialized = HBaseUtils.serializeDatabase(database);
    store(DB_TABLE, serialized[0], CATALOG_CF, CATALOG_COL, serialized[1]);
  }

  /**
   * Drop a database
   * @param name name of db to drop
   * @throws IOException
   */
  void deleteDb(String name) throws IOException {
    byte[] key = HBaseUtils.buildKey(name);
    delete(DB_TABLE, key, null, null);
  }

  /**********************************************************************************************
   * Function related methods
   *********************************************************************************************/

  /**
   * Fetch a function object
   * @param dbName name of the database the function is in
   * @param functionName name of the function to fetch
   * @return the function object, or null if there is no such function
   * @throws IOException
   */
  Function getFunction(String dbName, String functionName) throws IOException {
    byte[] key = HBaseUtils.buildKey(dbName, functionName);
    byte[] serialized = read(FUNC_TABLE, key, CATALOG_CF, CATALOG_COL);
    if (serialized == null) return null;
    return HBaseUtils.deserializeFunction(dbName, functionName, serialized);
  }

  /**
   * Get a list of functions.
   * @param dbName Name of the database to search in.
   * @param regex Regular expression to use in searching for function names.  It is expected to
   *              be a Java regular expression.  If it is null then all functions will be returned.
   * @return list of functions matching the regular expression.
   * @throws IOException
   */
  List<Function> scanFunctions(String dbName, String regex) throws IOException {
    byte[] keyPrefix = null;
    if (dbName != null) {
      keyPrefix = HBaseUtils.buildKeyWithTrailingSeparator(dbName);
    }
    Filter filter = null;
    if (regex != null) {
      filter = new RowFilter(CompareFilter.CompareOp.EQUAL, new RegexStringComparator(regex));
    }
    Iterator<Result> iter =
        scan(FUNC_TABLE, keyPrefix, HBaseUtils.getEndPrefix(keyPrefix), CATALOG_CF, CATALOG_COL, filter);
    List<Function> functions = new ArrayList<Function>();
    while (iter.hasNext()) {
      Result result = iter.next();
      functions.add(HBaseUtils.deserializeFunction(result.getRow(),
                                                   result.getValue(CATALOG_CF, CATALOG_COL)));
    }
    return functions;
  }

  /**
   * Store a function object
   * @param function function object to store
   * @throws IOException
   */
  void putFunction(Function function) throws IOException {
    byte[][] serialized = HBaseUtils.serializeFunction(function);
    store(FUNC_TABLE, serialized[0], CATALOG_CF, CATALOG_COL, serialized[1]);
  }

  /**
   * Drop a function
   * @param dbName name of database the function is in
   * @param functionName name of function to drop
   * @throws IOException
   */
  void deleteFunction(String dbName, String functionName) throws IOException {
    byte[] key = HBaseUtils.buildKey(dbName, functionName);
    delete(FUNC_TABLE, key, null, null);
  }

  /**********************************************************************************************
   * Global privilege related methods
   *********************************************************************************************/

  /**
   * Fetch the global privileges object
   * @return
   * @throws IOException
   */
  PrincipalPrivilegeSet getGlobalPrivs() throws IOException {
    byte[] key = GLOBAL_PRIVS_KEY;
    byte[] serialized = read(GLOBAL_PRIVS_TABLE, key, CATALOG_CF, CATALOG_COL);
    if (serialized == null) return null;
    return HBaseUtils.deserializePrincipalPrivilegeSet(serialized);
  }

  /**
   * Store the global privileges object
   * @throws IOException
   */
  void putGlobalPrivs(PrincipalPrivilegeSet privs) throws IOException {
    byte[] key = GLOBAL_PRIVS_KEY;
    byte[] serialized = HBaseUtils.serializePrincipalPrivilegeSet(privs);
    store(GLOBAL_PRIVS_TABLE, key, CATALOG_CF, CATALOG_COL, serialized);
  }

  /**********************************************************************************************
   * Partition related methods
   *********************************************************************************************/

  /**
   * Fetch one partition
   * @param dbName database table is in
   * @param tableName table partition is in
   * @param partVals list of values that specify the partition, given in the same order as the
   *                 columns they belong to
   * @return The partition objec,t or null if there is no such partition
   * @throws IOException
   */
  Partition getPartition(String dbName, String tableName, List<String> partVals)
      throws IOException {
    return getPartition(dbName, tableName, partVals, true);
  }

  /**
   * Get a set of specific partitions.  This cannot be used to do a scan, each partition must be
   * completely specified.  This does not use the partition cache.
   * @param dbName database table is in
   * @param tableName table partitions are in
   * @param partValLists list of list of values, each list should uniquely identify one partition
   * @return a list of partition objects.
   * @throws IOException
   */
   List<Partition> getPartitions(String dbName, String tableName, List<List<String>> partValLists)
       throws IOException {
     List<Partition> parts = new ArrayList<Partition>(partValLists.size());
     List<Get> gets = new ArrayList<Get>(partValLists.size());
     for (List<String> partVals : partValLists) {
       byte[] key = HBaseUtils.buildPartitionKey(dbName, tableName, partVals);
       Get get = new Get(key);
       get.addColumn(CATALOG_CF, CATALOG_COL);
       gets.add(get);
     }
     HTableInterface htab = conn.getHBaseTable(PART_TABLE);
     Result[] results = htab.get(gets);
     for (int i = 0; i < results.length; i++) {
       HBaseUtils.StorageDescriptorParts sdParts =
           HBaseUtils.deserializePartition(dbName, tableName, partValLists.get(i),
               results[i].getValue(CATALOG_CF, CATALOG_COL));
       StorageDescriptor sd = getStorageDescriptor(sdParts.sdHash);
       HBaseUtils.assembleStorageDescriptor(sd, sdParts);
       parts.add(sdParts.containingPartition);
     }

     return parts;
  }

  /**
   * Add a partition.  This should only be called for new partitions.  For altering existing
   * partitions this should not be called as it will blindly increment the ref counter for the
   * storage descriptor.
   * @param partition partition object to add
   * @throws IOException
   */
  void putPartition(Partition partition) throws IOException {
    byte[] hash = putStorageDescriptor(partition.getSd());
    byte[][] serialized = HBaseUtils.serializePartition(partition, hash);
    store(PART_TABLE, serialized[0], CATALOG_CF, CATALOG_COL, serialized[1]);
    partCache.put(partition.getDbName(), partition.getTableName(), partition);
  }

  /**
   * Replace an existing partition.
   * @param oldPart partition to be replaced
   * @param newPart partitiion to replace it with
   * @throws IOException
   */
  void replacePartition(Partition oldPart, Partition newPart) throws IOException {
    byte[] hash;
    byte[] oldHash = HBaseUtils.hashStorageDescriptor(oldPart.getSd(), md);
    byte[] newHash = HBaseUtils.hashStorageDescriptor(newPart.getSd(), md);
    if (Arrays.equals(oldHash, newHash)) {
      hash = oldHash;
    } else {
      decrementStorageDescriptorRefCount(oldPart.getSd());
      hash = putStorageDescriptor(newPart.getSd());
    }
    byte[][] serialized = HBaseUtils.serializePartition(newPart, hash);
    store(PART_TABLE, serialized[0], CATALOG_CF, CATALOG_COL, serialized[1]);
    partCache.put(newPart.getDbName(), newPart.getTableName(), newPart);
    if (!oldPart.getTableName().equals(newPart.getTableName())) {
      deletePartition(oldPart.getDbName(), oldPart.getTableName(), oldPart.getValues());
    }
  }

  /**
   * Add a group of partitions.  This should only be used when all partitions are new.  It
   * blindly increments the ref count on the storage descriptor.
   * @param partitions list of partitions to add
   * @throws IOException
   */
  void putPartitions(List<Partition> partitions) throws IOException {
    List<Put> puts = new ArrayList<Put>(partitions.size());
    for (Partition partition : partitions) {
      byte[] hash = putStorageDescriptor(partition.getSd());
      byte[][] serialized = HBaseUtils.serializePartition(partition, hash);
      Put p = new Put(serialized[0]);
      p.add(CATALOG_CF, CATALOG_COL, serialized[1]);
      puts.add(p);
      partCache.put(partition.getDbName(), partition.getTableName(), partition);
    }
    HTableInterface htab = conn.getHBaseTable(PART_TABLE);
    htab.put(puts);
    conn.flush(htab);
  }

  void replacePartitions(List<Partition> oldParts, List<Partition> newParts) throws IOException {
    if (oldParts.size() != newParts.size()) {
      throw new RuntimeException("Number of old and new partitions must match.");
    }
    List<Put> puts = new ArrayList<>(newParts.size());
    for (int i = 0; i < newParts.size(); i++) {
      byte[] hash;
      byte[] oldHash = HBaseUtils.hashStorageDescriptor(oldParts.get(i).getSd(), md);
      byte[] newHash = HBaseUtils.hashStorageDescriptor(newParts.get(i).getSd(), md);
      if (Arrays.equals(oldHash, newHash)) {
        hash = oldHash;
      } else {
        decrementStorageDescriptorRefCount(oldParts.get(i).getSd());
        hash = putStorageDescriptor(newParts.get(i).getSd());
      }
      byte[][] serialized = HBaseUtils.serializePartition(newParts.get(i), hash);
      Put p = new Put(serialized[0]);
      p.add(CATALOG_CF, CATALOG_COL, serialized[1]);
      puts.add(p);
      partCache.put(newParts.get(i).getDbName(), newParts.get(i).getTableName(), newParts.get(i));
      if (!newParts.get(i).getTableName().equals(oldParts.get(i).getTableName())) {
        // We need to remove the old record as well.
        deletePartition(oldParts.get(i).getDbName(), oldParts.get(i).getTableName(),
            oldParts.get(i).getValues(), false);
      }
    }
    HTableInterface htab = conn.getHBaseTable(PART_TABLE);
    htab.put(puts);
    conn.flush(htab);
  }

  /**
   * Find all the partitions in a table.
   * @param dbName name of the database the table is in
   * @param tableName table name
   * @param maxPartitions max partitions to fetch.  If negative all partitions will be returned.
   * @return List of partitions that match the criteria.
   * @throws IOException
   */
  List<Partition> scanPartitionsInTable(String dbName, String tableName, int maxPartitions)
      throws IOException {
    if (maxPartitions < 0) maxPartitions = Integer.MAX_VALUE;
    Collection<Partition> cached = partCache.getAllForTable(dbName, tableName);
    if (cached != null) {
      return maxPartitions < cached.size()
          ? new ArrayList<Partition>(cached).subList(0, maxPartitions)
          : new ArrayList<Partition>(cached);
    }
    byte[] keyPrefix = HBaseUtils.buildKeyWithTrailingSeparator(dbName, tableName);
    List<Partition> parts = scanPartitionsWithFilter(keyPrefix, HBaseUtils.getEndPrefix(keyPrefix), -1, null);
    partCache.put(dbName, tableName, parts, true);
    return maxPartitions < parts.size() ? parts.subList(0, maxPartitions) : parts;
  }

  /**
   * Scan partitions based on partial key information.
   * @param dbName name of database, required
   * @param tableName name of table, required
   * @param partVals partial specification of values.  Any values that are unknown can instead be
   *                 a '*'.  For example, if a table had two partition columns date
   *                 and region (in that order), and partitions ('today', 'na'), ('today', 'eu'),
   *                 ('tomorrow', 'na'), ('tomorrow', 'eu') then passing ['today', '*'] would return
   *                 ('today', 'na') and ('today', 'eu') while passing ['*', 'eu'] would return
   *                 ('today', 'eu') and ('tomorrow', 'eu').  Also the list can terminate early,
   *                 which will be the equivalent of adding '*' for all non-included values.
   *                 I.e. ['today'] is the same as ['today', '*'].
   * @param maxPartitions Maximum number of entries to return.
   * @return list of partitions that match the specified information
   * @throws IOException
   * @throws org.apache.hadoop.hive.metastore.api.NoSuchObjectException if the table containing
   * the partitions can't be found.
   */
  List<Partition> scanPartitions(String dbName, String tableName, List<String> partVals,
                                 int maxPartitions) throws IOException, NoSuchObjectException {
    // First, build as much of the key as we can so that we make the scan as tight as possible.
    List<String> keyElements = new ArrayList<String>();
    keyElements.add(dbName);
    keyElements.add(tableName);

    int firstStar = -1;
    for (int i = 0; i < partVals.size(); i++) {
      if ("*".equals(partVals.get(i))) {
        firstStar = i;
        break;
      } else {
        keyElements.add(partVals.get(i));
      }
    }

    byte[] keyPrefix;
    // We need to fetch the table to determine if the user fully specified the partitions or
    // not, as it affects how we build the key.
    Table table = getTable(dbName, tableName);
    if (table == null) {
      throw new NoSuchObjectException("Unable to find table " + dbName + "." + tableName);
    }
    if (partVals.size() == table.getPartitionKeys().size()) {
      keyPrefix = HBaseUtils.buildKey(keyElements.toArray(new String[keyElements.size()]));
    } else {
      keyPrefix = HBaseUtils.buildKeyWithTrailingSeparator(keyElements.toArray(
          new String[keyElements.size()]));
    }

    // Now, build a filter out of the remaining keys
    String regex = null;
    if (!(partVals.size() == table.getPartitionKeys().size() && firstStar == -1)) {
      StringBuilder buf = new StringBuilder(".*");
      for (int i = Math.max(0, firstStar);
           i < table.getPartitionKeys().size() && i < partVals.size(); i++) {
        buf.append(HBaseUtils.KEY_SEPARATOR);
        if ("*".equals(partVals.get(i))) {
          buf.append("[^");
          buf.append(HBaseUtils.KEY_SEPARATOR);
          buf.append("]+");
        } else {
          buf.append(partVals.get(i));
        }
      }
      if (partVals.size() < table.getPartitionKeys().size()) {
        buf.append(HBaseUtils.KEY_SEPARATOR);
        buf.append(".*");
      }
      regex = buf.toString();
    }

    Filter filter = null;
    if (regex != null) {
      filter = new RowFilter(CompareFilter.CompareOp.EQUAL, new RegexStringComparator(regex));
    }

    if (LOG.isDebugEnabled()) {
      LOG.debug("Scanning partitions with prefix <" + new String(keyPrefix) + "> and filter <" +
          regex + ">");
    }

    List<Partition> parts = scanPartitionsWithFilter(keyPrefix, HBaseUtils.getEndPrefix(keyPrefix), maxPartitions, filter);
    partCache.put(dbName, tableName, parts, false);
    return parts;
  }

  List<Partition> scanPartitions(String dbName, String tableName, byte[] keyStart, byte[] keyEnd,
      Filter filter, int maxPartitions) throws IOException, NoSuchObjectException {
    List<String> keyElements = new ArrayList<String>();
    keyElements.add(dbName);
    keyElements.add(tableName);

    byte[] keyPrefix =
        HBaseUtils.buildKeyWithTrailingSeparator(keyElements.toArray(new String[keyElements.size()]));
    byte[] startRow = ArrayUtils.addAll(keyPrefix, keyStart);
    byte[] endRow;
    if (keyEnd == null || keyEnd.length == 0) {
      // stop when current db+table entries are over
      endRow = HBaseUtils.getEndPrefix(keyPrefix);
    } else {
      endRow = ArrayUtils.addAll(keyPrefix, keyEnd);
    }

    if (LOG.isDebugEnabled()) {
      LOG.debug("Scanning partitions with start row <" + new String(startRow) + "> and end row <"
          + new String(endRow) + ">");
    }
    return scanPartitionsWithFilter(startRow, endRow, maxPartitions, filter);
  }



  /**
   * Delete a partition
   * @param dbName database name that table is in
   * @param tableName table partition is in
   * @param partVals partition values that define this partition, in the same order as the
   *                 partition columns they are values for
   * @throws IOException
   */
  void deletePartition(String dbName, String tableName, List<String> partVals) throws IOException {
    deletePartition(dbName, tableName, partVals, true);
  }

  private void deletePartition(String dbName, String tableName, List<String> partVals,
                               boolean decrementRefCnt) throws IOException {
    // Find the partition so I can get the storage descriptor and drop it
    partCache.remove(dbName, tableName, partVals);
    if (decrementRefCnt) {
      Partition p = getPartition(dbName, tableName, partVals, false);
      decrementStorageDescriptorRefCount(p.getSd());
    }
    byte[] key = HBaseUtils.buildPartitionKey(dbName, tableName, partVals);
    delete(PART_TABLE, key, null, null);
  }

  private Partition getPartition(String dbName, String tableName, List<String> partVals,
                                 boolean populateCache) throws IOException {
    Partition cached = partCache.get(dbName, tableName, partVals);
    if (cached != null) return cached;
    byte[] key = HBaseUtils.buildPartitionKey(dbName, tableName, partVals);
    byte[] serialized = read(PART_TABLE, key, CATALOG_CF, CATALOG_COL);
    if (serialized == null) return null;
    HBaseUtils.StorageDescriptorParts sdParts =
        HBaseUtils.deserializePartition(dbName, tableName, partVals, serialized);
    StorageDescriptor sd = getStorageDescriptor(sdParts.sdHash);
    HBaseUtils.assembleStorageDescriptor(sd, sdParts);
    if (populateCache) partCache.put(dbName, tableName, sdParts.containingPartition);
    return sdParts.containingPartition;
  }

  private List<Partition> scanPartitionsWithFilter(byte[] startRow, byte [] endRow,
      int maxResults, Filter filter)
      throws IOException {
    Iterator<Result> iter =
        scan(PART_TABLE, startRow, endRow, CATALOG_CF, CATALOG_COL, filter);
    List<Partition> parts = new ArrayList<Partition>();
    int numToFetch = maxResults < 0 ? Integer.MAX_VALUE : maxResults;
    for (int i = 0; i < numToFetch && iter.hasNext(); i++) {
      Result result = iter.next();
      HBaseUtils.StorageDescriptorParts sdParts = HBaseUtils.deserializePartition(result.getRow(),
          result.getValue(CATALOG_CF, CATALOG_COL));
      StorageDescriptor sd = getStorageDescriptor(sdParts.sdHash);
      HBaseUtils.assembleStorageDescriptor(sd, sdParts);
      parts.add(sdParts.containingPartition);
    }
    return parts;
  }

  /**********************************************************************************************
   * Role related methods
   *********************************************************************************************/

  /**
   * Fetch the list of all roles for a user
   * @param userName name of the user
   * @return the list of all roles this user participates in
   * @throws IOException
   */
  List<String> getUserRoles(String userName) throws IOException {
    byte[] key = HBaseUtils.buildKey(userName);
    byte[] serialized = read(USER_TO_ROLE_TABLE, key, CATALOG_CF, CATALOG_COL);
    if (serialized == null) return null;
    return HBaseUtils.deserializeRoleList(serialized);
  }

  /**
   * Find all roles directly participated in by a given principal.  This builds the role cache
   * because it assumes that subsequent calls may be made to find roles participated in indirectly.
   * @param name username or role name
   * @param type user or role
   * @return map of role name to grant info for all roles directly participated in.
   */
  List<Role> getPrincipalDirectRoles(String name, PrincipalType type)
      throws IOException {
    buildRoleCache();

    Set<String> rolesFound = new HashSet<String>();
    for (Map.Entry<String, HbaseMetastoreProto.RoleGrantInfoList> e : roleCache.entrySet()) {
      for (HbaseMetastoreProto.RoleGrantInfo giw : e.getValue().getGrantInfoList()) {
        if (HBaseUtils.convertPrincipalTypes(giw.getPrincipalType()) == type &&
            giw.getPrincipalName().equals(name)) {
          rolesFound.add(e.getKey());
          break;
        }
      }
    }
    List<Role> directRoles = new ArrayList<Role>(rolesFound.size());
    List<Get> gets = new ArrayList<Get>();
    HTableInterface htab = conn.getHBaseTable(ROLE_TABLE);
    for (String roleFound : rolesFound) {
      byte[] key = HBaseUtils.buildKey(roleFound);
      Get g = new Get(key);
      g.addColumn(CATALOG_CF, CATALOG_COL);
      gets.add(g);
    }

    Result[] results = htab.get(gets);
    for (int i = 0; i < results.length; i++) {
      byte[] serialized = results[i].getValue(CATALOG_CF, CATALOG_COL);
      if (serialized != null) {
        directRoles.add(HBaseUtils.deserializeRole(results[i].getRow(), serialized));
      }
    }

    return directRoles;
  }

  /**
   * Fetch all roles and users included directly in a given role.
   * @param roleName name of the principal
   * @return a list of all roles included in this role
   * @throws IOException
   */
  HbaseMetastoreProto.RoleGrantInfoList getRolePrincipals(String roleName)
      throws IOException, NoSuchObjectException {
    HbaseMetastoreProto.RoleGrantInfoList rolePrincipals = roleCache.get(roleName);
    if (rolePrincipals != null) return rolePrincipals;
    byte[] key = HBaseUtils.buildKey(roleName);
    byte[] serialized = read(ROLE_TABLE, key, CATALOG_CF, ROLES_COL);
    if (serialized == null) return null;
    rolePrincipals = HbaseMetastoreProto.RoleGrantInfoList.parseFrom(serialized);
    roleCache.put(roleName, rolePrincipals);
    return rolePrincipals;
  }

  /**
   * Given a role, find all users who are either directly or indirectly participate in this role.
   * This is expensive, it should be used sparingly.  It scan the entire userToRole table and
   * does a linear search on each entry.
   * @param roleName name of the role
   * @return set of all users in the role
   * @throws IOException
   */
  Set<String> findAllUsersInRole(String roleName) throws IOException {
    // Walk the userToRole table and collect every user that matches this role.
    Set<String> users = new HashSet<String>();
    Iterator<Result> iter = scan(USER_TO_ROLE_TABLE, CATALOG_CF, CATALOG_COL);
    while (iter.hasNext()) {
      Result result = iter.next();
      List<String> roleList =
          HBaseUtils.deserializeRoleList(result.getValue(CATALOG_CF, CATALOG_COL));
      for (String rn : roleList) {
        if (rn.equals(roleName)) {
          users.add(new String(result.getRow(), HBaseUtils.ENCODING));
          break;
        }
      }
    }
    return users;
  }

  /**
   * Add a principal to a role.
   * @param roleName name of the role to add principal to
   * @param grantInfo grant information for this principal.
   * @throws java.io.IOException
   * @throws NoSuchObjectException
   *
   */
  void addPrincipalToRole(String roleName, HbaseMetastoreProto.RoleGrantInfo grantInfo)
      throws IOException, NoSuchObjectException {
    HbaseMetastoreProto.RoleGrantInfoList proto = getRolePrincipals(roleName);
    List<HbaseMetastoreProto.RoleGrantInfo> rolePrincipals =
        new ArrayList<HbaseMetastoreProto.RoleGrantInfo>();
    if (proto != null) {
      rolePrincipals.addAll(proto.getGrantInfoList());
    }

    rolePrincipals.add(grantInfo);
    proto = HbaseMetastoreProto.RoleGrantInfoList.newBuilder()
        .addAllGrantInfo(rolePrincipals)
        .build();
    byte[] key = HBaseUtils.buildKey(roleName);
    store(ROLE_TABLE, key, CATALOG_CF, ROLES_COL, proto.toByteArray());
    roleCache.put(roleName, proto);
  }

  /**
   * Drop a principal from a role.
   * @param roleName Name of the role to drop the principal from
   * @param principalName name of the principal to drop from the role
   * @param type user or role
   * @param grantOnly if this is true, just remove the grant option, don't actually remove the
   *                  user from the role.
   * @throws NoSuchObjectException
   * @throws IOException
   */
  void dropPrincipalFromRole(String roleName, String principalName, PrincipalType type,
                             boolean grantOnly)
      throws NoSuchObjectException, IOException {
    HbaseMetastoreProto.RoleGrantInfoList proto = getRolePrincipals(roleName);
    if (proto == null) return;
    List<HbaseMetastoreProto.RoleGrantInfo> rolePrincipals =
        new ArrayList<HbaseMetastoreProto.RoleGrantInfo>();
    rolePrincipals.addAll(proto.getGrantInfoList());

    for (int i = 0; i < rolePrincipals.size(); i++) {
      if (HBaseUtils.convertPrincipalTypes(rolePrincipals.get(i).getPrincipalType()) == type &&
          rolePrincipals.get(i).getPrincipalName().equals(principalName)) {
        if (grantOnly) {
          rolePrincipals.set(i,
              HbaseMetastoreProto.RoleGrantInfo.newBuilder(rolePrincipals.get(i))
                  .setGrantOption(false)
                  .build());
        } else {
          rolePrincipals.remove(i);
        }
        break;
      }
    }
    byte[] key = HBaseUtils.buildKey(roleName);
    proto = HbaseMetastoreProto.RoleGrantInfoList.newBuilder()
        .addAllGrantInfo(rolePrincipals)
        .build();
    store(ROLE_TABLE, key, CATALOG_CF, ROLES_COL, proto.toByteArray());
    roleCache.put(roleName, proto);
  }

  /**
   * Rebuild the row for a given user in the USER_TO_ROLE table.  This is expensive.  It
   * should be called as infrequently as possible.
   * @param userName name of the user
   * @throws IOException
   */
  void buildRoleMapForUser(String userName) throws IOException, NoSuchObjectException {
    // This is mega ugly.  Hopefully we don't have to do this too often.
    // First, scan the role table and put it all in memory
    buildRoleCache();
    LOG.debug("Building role map for " + userName);

    // Second, find every role the user participates in directly.
    Set<String> rolesToAdd = new HashSet<String>();
    Set<String> rolesToCheckNext = new HashSet<String>();
    for (Map.Entry<String, HbaseMetastoreProto.RoleGrantInfoList> e : roleCache.entrySet()) {
      for (HbaseMetastoreProto.RoleGrantInfo grantInfo : e.getValue().getGrantInfoList()) {
        if (HBaseUtils.convertPrincipalTypes(grantInfo.getPrincipalType()) == PrincipalType.USER &&
            userName .equals(grantInfo.getPrincipalName())) {
          rolesToAdd.add(e.getKey());
          rolesToCheckNext.add(e.getKey());
          LOG.debug("Adding " + e.getKey() + " to list of roles user is in directly");
          break;
        }
      }
    }

    // Third, find every role the user participates in indirectly (that is, they have been
    // granted into role X and role Y has been granted into role X).
    while (rolesToCheckNext.size() > 0) {
      Set<String> tmpRolesToCheckNext = new HashSet<String>();
      for (String roleName : rolesToCheckNext) {
        HbaseMetastoreProto.RoleGrantInfoList grantInfos = roleCache.get(roleName);
        if (grantInfos == null) continue;  // happens when a role contains no grants
        for (HbaseMetastoreProto.RoleGrantInfo grantInfo : grantInfos.getGrantInfoList()) {
          if (HBaseUtils.convertPrincipalTypes(grantInfo.getPrincipalType()) == PrincipalType.ROLE &&
              rolesToAdd.add(grantInfo.getPrincipalName())) {
            tmpRolesToCheckNext.add(grantInfo.getPrincipalName());
            LOG.debug("Adding " + grantInfo.getPrincipalName() +
                " to list of roles user is in indirectly");
          }
        }
      }
      rolesToCheckNext = tmpRolesToCheckNext;
    }

    byte[] key = HBaseUtils.buildKey(userName);
    byte[] serialized = HBaseUtils.serializeRoleList(new ArrayList<String>(rolesToAdd));
    store(USER_TO_ROLE_TABLE, key, CATALOG_CF, CATALOG_COL, serialized);
  }

  /**
   * Remove all of the grants for a role.  This is not cheap.
   * @param roleName Role to remove from all other roles and grants
   * @throws IOException
   */
  void removeRoleGrants(String roleName) throws IOException {
    buildRoleCache();

    List<Put> puts = new ArrayList<Put>();
    // First, walk the role table and remove any references to this role
    for (Map.Entry<String, HbaseMetastoreProto.RoleGrantInfoList> e : roleCache.entrySet()) {
      boolean madeAChange = false;
      List<HbaseMetastoreProto.RoleGrantInfo> rgil =
          new ArrayList<HbaseMetastoreProto.RoleGrantInfo>();
      rgil.addAll(e.getValue().getGrantInfoList());
      for (int i = 0; i < rgil.size(); i++) {
        if (HBaseUtils.convertPrincipalTypes(rgil.get(i).getPrincipalType()) == PrincipalType.ROLE &&
            rgil.get(i).getPrincipalName().equals(roleName)) {
          rgil.remove(i);
          madeAChange = true;
          break;
        }
      }
      if (madeAChange) {
        Put put = new Put(HBaseUtils.buildKey(e.getKey()));
        HbaseMetastoreProto.RoleGrantInfoList proto =
            HbaseMetastoreProto.RoleGrantInfoList.newBuilder()
            .addAllGrantInfo(rgil)
            .build();
        put.add(CATALOG_CF, ROLES_COL, proto.toByteArray());
        puts.add(put);
        roleCache.put(e.getKey(), proto);
      }
    }

    if (puts.size() > 0) {
      HTableInterface htab = conn.getHBaseTable(ROLE_TABLE);
      htab.put(puts);
      conn.flush(htab);
    }

    // Remove any global privileges held by this role
    PrincipalPrivilegeSet global = getGlobalPrivs();
    if (global != null &&
        global.getRolePrivileges() != null &&
        global.getRolePrivileges().remove(roleName) != null) {
      putGlobalPrivs(global);
    }

    // Now, walk the db table
    puts.clear();
    List<Database> dbs = scanDatabases(null);
    if (dbs == null) dbs = new ArrayList<Database>(); // rare, but can happen
    for (Database db : dbs) {
      if (db.getPrivileges() != null &&
          db.getPrivileges().getRolePrivileges() != null &&
          db.getPrivileges().getRolePrivileges().remove(roleName) != null) {
        byte[][] serialized = HBaseUtils.serializeDatabase(db);
        Put put = new Put(serialized[0]);
        put.add(CATALOG_CF, CATALOG_COL, serialized[1]);
        puts.add(put);
      }
    }

    if (puts.size() > 0) {
      HTableInterface htab = conn.getHBaseTable(DB_TABLE);
      htab.put(puts);
      conn.flush(htab);
    }

    // Finally, walk the table table
    puts.clear();
    for (Database db : dbs) {
      List<Table> tables = scanTables(db.getName(), null);
      if (tables != null) {
        for (Table table : tables) {
          if (table.getPrivileges() != null &&
              table.getPrivileges().getRolePrivileges() != null &&
              table.getPrivileges().getRolePrivileges().remove(roleName) != null) {
            byte[][] serialized = HBaseUtils.serializeTable(table,
                HBaseUtils.hashStorageDescriptor(table.getSd(), md));
            Put put = new Put(serialized[0]);
            put.add(CATALOG_CF, CATALOG_COL, serialized[1]);
            puts.add(put);
          }
        }
      }
    }

    if (puts.size() > 0) {
      HTableInterface htab = conn.getHBaseTable(TABLE_TABLE);
      htab.put(puts);
      conn.flush(htab);
    }
  }

  /**
   * Fetch a role
   * @param roleName name of the role
   * @return role object, or null if no such role
   * @throws IOException
   */
  Role getRole(String roleName) throws IOException {
    byte[] key = HBaseUtils.buildKey(roleName);
    byte[] serialized = read(ROLE_TABLE, key, CATALOG_CF, CATALOG_COL);
    if (serialized == null) return null;
    return HBaseUtils.deserializeRole(roleName, serialized);
  }

  /**
   * Get a list of roles.
   * @return list of all known roles.
   * @throws IOException
   */
  List<Role> scanRoles() throws IOException {
    Iterator<Result> iter = scan(ROLE_TABLE, CATALOG_CF, CATALOG_COL);
    List<Role> roles = new ArrayList<Role>();
    while (iter.hasNext()) {
      Result result = iter.next();
      roles.add(HBaseUtils.deserializeRole(result.getRow(),
          result.getValue(CATALOG_CF, CATALOG_COL)));
    }
    return roles;
  }

  /**
   * Add a new role
   * @param role role object
   * @throws IOException
   */
  void putRole(Role role) throws IOException {
    byte[][] serialized = HBaseUtils.serializeRole(role);
    store(ROLE_TABLE, serialized[0], CATALOG_CF, CATALOG_COL, serialized[1]);
  }

  /**
   * Drop a role
   * @param roleName name of role to drop
   * @throws IOException
   */
  void deleteRole(String roleName) throws IOException {
    byte[] key = HBaseUtils.buildKey(roleName);
    delete(ROLE_TABLE, key, null, null);
    roleCache.remove(roleName);
  }

  private void buildRoleCache() throws IOException {
    if (!entireRoleTableInCache) {
      Iterator<Result> roles = scan(ROLE_TABLE, CATALOG_CF, ROLES_COL);
      while (roles.hasNext()) {
        Result res = roles.next();
        String roleName = new String(res.getRow(), HBaseUtils.ENCODING);
        HbaseMetastoreProto.RoleGrantInfoList grantInfos =
            HbaseMetastoreProto.RoleGrantInfoList.parseFrom(res.getValue(CATALOG_CF, ROLES_COL));
        roleCache.put(roleName, grantInfos);
      }
      entireRoleTableInCache = true;
    }
  }

  /**********************************************************************************************
   * Table related methods
   *********************************************************************************************/

  /**
   * Fetch a table object
   * @param dbName database the table is in
   * @param tableName table name
   * @return Table object, or null if no such table
   * @throws IOException
   */
  Table getTable(String dbName, String tableName) throws IOException {
    return getTable(dbName, tableName, true);
  }

  /**
   * Fetch a list of table objects.
   * @param dbName Database that all fetched tables are in
   * @param tableNames list of table names
   * @return list of tables, in the same order as the provided names.
   * @throws IOException
   */
  List<Table> getTables(String dbName, List<String> tableNames) throws IOException {
    // I could implement getTable in terms of this method.  But it is such a core function
    // that I don't want to slow it down for the much less common fetching of multiple tables.
    List<Table> results = new ArrayList<Table>(tableNames.size());
    ObjectPair<String, String>[] hashKeys = new ObjectPair[tableNames.size()];
    boolean atLeastOneMissing = false;
    for (int i = 0; i < tableNames.size(); i++) {
      hashKeys[i] = new ObjectPair<String, String>(dbName, tableNames.get(i));
      // The result may be null, but we still want to add it so that we have a slot in the list
      // for it.
      results.add(tableCache.get(hashKeys[i]));
      if (results.get(i) == null) atLeastOneMissing = true;
    }
    if (!atLeastOneMissing) return results;

    // Now build a single get that will fetch the remaining tables
    List<Get> gets = new ArrayList<Get>();
    HTableInterface htab = conn.getHBaseTable(TABLE_TABLE);
    for (int i = 0; i < tableNames.size(); i++) {
      if (results.get(i) != null) continue;
      byte[] key = HBaseUtils.buildKey(dbName, tableNames.get(i));
      Get g = new Get(key);
      g.addColumn(CATALOG_CF, CATALOG_COL);
      gets.add(g);
    }
    Result[] res = htab.get(gets);
    for (int i = 0, nextGet = 0; i < tableNames.size(); i++) {
      if (results.get(i) != null) continue;
      byte[] serialized = res[nextGet++].getValue(CATALOG_CF, CATALOG_COL);
      if (serialized != null) {
        HBaseUtils.StorageDescriptorParts sdParts =
            HBaseUtils.deserializeTable(dbName, tableNames.get(i), serialized);
        StorageDescriptor sd = getStorageDescriptor(sdParts.sdHash);
        HBaseUtils.assembleStorageDescriptor(sd, sdParts);
        tableCache.put(hashKeys[i], sdParts.containingTable);
        results.set(i, sdParts.containingTable);
      }
    }
    return results;
  }

  /**
   * Get a list of tables.
   * @param dbName Database these tables are in
   * @param regex Regular expression to use in searching for table names.  It is expected to
   *              be a Java regular expression.  If it is null then all tables in the indicated
   *              database will be returned.
   * @return list of tables matching the regular expression.
   * @throws IOException
   */
  List<Table> scanTables(String dbName, String regex) throws IOException {
    // There's no way to know whether all the tables we are looking for are
    // in the cache, so we would need to scan one way or another.  Thus there's no value in hitting
    // the cache for this function.
    byte[] keyPrefix = null;
    if (dbName != null) {
      keyPrefix = HBaseUtils.buildKeyWithTrailingSeparator(dbName);
    }
    Filter filter = null;
    if (regex != null) {
      filter = new RowFilter(CompareFilter.CompareOp.EQUAL, new RegexStringComparator(regex));
    }
    Iterator<Result> iter =
        scan(TABLE_TABLE, keyPrefix, HBaseUtils.getEndPrefix(keyPrefix),
            CATALOG_CF, CATALOG_COL, filter);
    List<Table> tables = new ArrayList<Table>();
    while (iter.hasNext()) {
      Result result = iter.next();
      HBaseUtils.StorageDescriptorParts sdParts =
          HBaseUtils.deserializeTable(result.getRow(), result.getValue(CATALOG_CF, CATALOG_COL));
      StorageDescriptor sd = getStorageDescriptor(sdParts.sdHash);
      HBaseUtils.assembleStorageDescriptor(sd, sdParts);
      tables.add(sdParts.containingTable);
    }
    return tables;
  }

  /**
   * Put a table object.  This should only be called when the table is new (create table) as it
   * will blindly add/increment the storage descriptor.  If you are altering an existing table
   * call {@link #replaceTable} instead.
   * @param table table object
   * @throws IOException
   */
  void putTable(Table table) throws IOException {
    byte[] hash = putStorageDescriptor(table.getSd());
    byte[][] serialized = HBaseUtils.serializeTable(table, hash);
    store(TABLE_TABLE, serialized[0], CATALOG_CF, CATALOG_COL, serialized[1]);
    tableCache.put(new ObjectPair<String, String>(table.getDbName(), table.getTableName()), table);
  }

  /**
   * Replace an existing table.  This will also compare the storage descriptors and see if the
   * reference count needs to be adjusted
   * @param oldTable old version of the table
   * @param newTable new version of the table
   */
  void replaceTable(Table oldTable, Table newTable) throws IOException {
    byte[] hash;
    byte[] oldHash = HBaseUtils.hashStorageDescriptor(oldTable.getSd(), md);
    byte[] newHash = HBaseUtils.hashStorageDescriptor(newTable.getSd(), md);
    if (Arrays.equals(oldHash, newHash)) {
      hash = oldHash;
    } else {
      decrementStorageDescriptorRefCount(oldTable.getSd());
      hash = putStorageDescriptor(newTable.getSd());
    }
    byte[][] serialized = HBaseUtils.serializeTable(newTable, hash);
    store(TABLE_TABLE, serialized[0], CATALOG_CF, CATALOG_COL, serialized[1]);
    tableCache.put(new ObjectPair<>(newTable.getDbName(), newTable.getTableName()), newTable);
    if (!oldTable.getTableName().equals(newTable.getTableName())) {
      deleteTable(oldTable.getDbName(), oldTable.getTableName());
    }
  }

  /**
   * Delete a table
   * @param dbName name of database table is in
   * @param tableName table to drop
   * @throws IOException
   */
  void deleteTable(String dbName, String tableName) throws IOException {
    deleteTable(dbName, tableName, true);
  }

  private void deleteTable(String dbName, String tableName, boolean decrementRefCnt)
      throws IOException {
    tableCache.remove(new ObjectPair<String, String>(dbName, tableName));
    if (decrementRefCnt) {
      // Find the table so I can get the storage descriptor and drop it
      Table t = getTable(dbName, tableName, false);
      decrementStorageDescriptorRefCount(t.getSd());
    }
    byte[] key = HBaseUtils.buildKey(dbName, tableName);
    delete(TABLE_TABLE, key, null, null);
  }

  private Table getTable(String dbName, String tableName, boolean populateCache)
      throws IOException {
    ObjectPair<String, String> hashKey = new ObjectPair<String, String>(dbName, tableName);
    Table cached = tableCache.get(hashKey);
    if (cached != null) return cached;
    byte[] key = HBaseUtils.buildKey(dbName, tableName);
    byte[] serialized = read(TABLE_TABLE, key, CATALOG_CF, CATALOG_COL);
    if (serialized == null) return null;
    HBaseUtils.StorageDescriptorParts sdParts =
        HBaseUtils.deserializeTable(dbName, tableName, serialized);
    StorageDescriptor sd = getStorageDescriptor(sdParts.sdHash);
    HBaseUtils.assembleStorageDescriptor(sd, sdParts);
    if (populateCache) tableCache.put(hashKey, sdParts.containingTable);
    return sdParts.containingTable;
  }

  /**********************************************************************************************
   * StorageDescriptor related methods
   *********************************************************************************************/

  /**
   * If this serde has already been read, then return it from the cache.  If not, read it, then
   * return it.
   * @param hash hash of the storage descriptor to read
   * @return the storage descriptor
   * @throws IOException
   */
  StorageDescriptor getStorageDescriptor(byte[] hash) throws IOException {
    ByteArrayWrapper hashKey = new ByteArrayWrapper(hash);
    StorageDescriptor cached = sdCache.get(hashKey);
    if (cached != null) return cached;
    LOG.debug("Not found in cache, looking in hbase");
    byte[] serialized = read(SD_TABLE, hash, CATALOG_CF, CATALOG_COL);
    if (serialized == null) {
      throw new RuntimeException("Woh, bad!  Trying to fetch a non-existent storage descriptor " +
          "from hash " + Base64.encodeBase64String(hash));
    }
    StorageDescriptor sd = HBaseUtils.deserializeStorageDescriptor(serialized);
    sdCache.put(hashKey, sd);
    return sd;
  }

  /**
   * Lower the reference count on the storage descriptor by one.  If it goes to zero, then it
   * will be deleted.
   * @param sd Storage descriptor
   * @throws IOException
   */
  void decrementStorageDescriptorRefCount(StorageDescriptor sd) throws IOException {
    byte[] key = HBaseUtils.hashStorageDescriptor(sd, md);
    byte[] serializedRefCnt = read(SD_TABLE, key, CATALOG_CF, REF_COUNT_COL);
    if (serializedRefCnt == null) {
      // Someone deleted it before we got to it, no worries
      return;
    }
    int refCnt = Integer.valueOf(new String(serializedRefCnt, HBaseUtils.ENCODING));
    HTableInterface htab = conn.getHBaseTable(SD_TABLE);
    if (--refCnt < 1) {
      Delete d = new Delete(key);
      // We don't use checkAndDelete here because it isn't compatible with the transaction
      // managers.  If the transaction managers are doing their jobs then we should not need it
      // anyway.
      htab.delete(d);
      sdCache.remove(new ByteArrayWrapper(key));
    } else {
      Put p = new Put(key);
      p.add(CATALOG_CF, REF_COUNT_COL, Integer.toString(refCnt).getBytes(HBaseUtils.ENCODING));
      htab.put(p);
      conn.flush(htab);
    }
  }

  /**
   * Place the common parts of a storage descriptor into the cache and write the storage
   * descriptor out to HBase.  This should only be called if you are sure that the storage
   * descriptor needs to be added.  If you have changed a table or partition but not it's storage
   * descriptor do not call this method, as it will increment the reference count of the storage
   * descriptor.
   * @param storageDescriptor storage descriptor to store.
   * @return id of the entry in the cache, to be written in for the storage descriptor
   */
  byte[] putStorageDescriptor(StorageDescriptor storageDescriptor) throws IOException {
    byte[] sd = HBaseUtils.serializeStorageDescriptor(storageDescriptor);
    byte[] key = HBaseUtils.hashStorageDescriptor(storageDescriptor, md);
    byte[] serializedRefCnt = read(SD_TABLE, key, CATALOG_CF, REF_COUNT_COL);
    HTableInterface htab = conn.getHBaseTable(SD_TABLE);
    if (serializedRefCnt == null) {
      // We are the first to put it in the DB
      Put p = new Put(key);
      p.add(CATALOG_CF, CATALOG_COL, sd);
      p.add(CATALOG_CF, REF_COUNT_COL, "1".getBytes(HBaseUtils.ENCODING));
      htab.put(p);
      sdCache.put(new ByteArrayWrapper(key), storageDescriptor);
    } else {
      // Just increment the reference count
      int refCnt = Integer.valueOf(new String(serializedRefCnt, HBaseUtils.ENCODING)) + 1;
      Put p = new Put(key);
      p.add(CATALOG_CF, REF_COUNT_COL, Integer.toString(refCnt).getBytes(HBaseUtils.ENCODING));
      htab.put(p);
    }
    conn.flush(htab);
    return key;
  }

  private static class ByteArrayWrapper {
    byte[] wrapped;

    ByteArrayWrapper(byte[] b) {
      wrapped = b;
    }

    @Override
    public boolean equals(Object other) {
      if (other instanceof ByteArrayWrapper) {
        return Arrays.equals(((ByteArrayWrapper)other).wrapped, wrapped);
      } else {
        return false;
      }
    }

    @Override
    public int hashCode() {
      return Arrays.hashCode(wrapped);
    }
  }

  /**********************************************************************************************
   * Statistics related methods
   *********************************************************************************************/

  /**
   * Update statistics for one or more columns for a table or a partition.
   *
   * @param dbName database the table is in
   * @param tableName table to update statistics for
   * @param partName name of the partition, can be null if these are table level statistics.
   * @param partVals partition values that define partition to update statistics for. If this is
   *          null, then these will be assumed to be table level statistics
   * @param stats Stats object with stats for one or more columns
   * @throws IOException
   */
  void updateStatistics(String dbName, String tableName, String partName, List<String> partVals,
      ColumnStatistics stats) throws IOException {
    byte[] key = getStatisticsKey(dbName, tableName, partVals);
    String hbaseTable = getStatisticsTable(partVals);
    byte[][] colnames = new byte[stats.getStatsObjSize()][];
    byte[][] serialized = new byte[stats.getStatsObjSize()][];
    for (int i = 0; i < stats.getStatsObjSize(); i++) {
      ColumnStatisticsObj obj = stats.getStatsObj().get(i);
      serialized[i] = HBaseUtils.serializeStatsForOneColumn(stats, obj);
      String colname = obj.getColName();
      colnames[i] = HBaseUtils.buildKey(colname);
    }
    store(hbaseTable, key, STATS_CF, colnames, serialized);
  }

  /**
   * Get statistics for a table
   *
   * @param dbName name of database table is in
   * @param tblName name of table
   * @param colNames list of column names to get statistics for
   * @return column statistics for indicated table
   * @throws IOException
   */
  ColumnStatistics getTableStatistics(String dbName, String tblName, List<String> colNames)
      throws IOException {
    byte[] tabKey = HBaseUtils.buildKey(dbName, tblName);
    ColumnStatistics tableStats = new ColumnStatistics();
    ColumnStatisticsDesc statsDesc = new ColumnStatisticsDesc();
    statsDesc.setIsTblLevel(true);
    statsDesc.setDbName(dbName);
    statsDesc.setTableName(tblName);
    tableStats.setStatsDesc(statsDesc);
    byte[][] colKeys = new byte[colNames.size()][];
    for (int i = 0; i < colKeys.length; i++) {
      colKeys[i] = HBaseUtils.buildKey(colNames.get(i));
    }
    Result result = read(TABLE_TABLE, tabKey, STATS_CF, colKeys);
    for (int i = 0; i < colKeys.length; i++) {
      byte[] serializedColStats = result.getValue(STATS_CF, colKeys[i]);
      if (serializedColStats == null) {
        // There were no stats for this column, so skip it
        continue;
      }
      ColumnStatisticsObj obj =
          HBaseUtils.deserializeStatsForOneColumn(tableStats, serializedColStats);
      obj.setColName(colNames.get(i));
      tableStats.addToStatsObj(obj);
    }
    return tableStats;
  }

  /**
   * Get statistics for a set of partitions
   *
   * @param dbName name of database table is in
   * @param tblName table partitions are in
   * @param partNames names of the partitions, used only to set values inside the return stats
   *          objects
   * @param partVals partition values for each partition, needed because this class doesn't know how
   *          to translate from partName to partVals
   * @param colNames column names to fetch stats for. These columns will be fetched for all
   *          requested partitions
   * @return list of ColumnStats, one for each partition. The values will be in the same order as
   *         the partNames list that was passed in
   * @throws IOException
   */
  List<ColumnStatistics> getPartitionStatistics(String dbName, String tblName,
      List<String> partNames, List<List<String>> partVals, List<String> colNames)
      throws IOException {
    List<ColumnStatistics> statsList = new ArrayList<ColumnStatistics>(partNames.size());
    ColumnStatistics partitionStats;
    ColumnStatisticsDesc statsDesc;
    byte[][] colKeys = new byte[colNames.size()][];
    List<Get> gets = new ArrayList<Get>();
    // Initialize the list and build the Gets
    for (int pOff = 0; pOff < partNames.size(); pOff++) {
      // Add an entry for this partition in the stats list
      partitionStats = new ColumnStatistics();
      statsDesc = new ColumnStatisticsDesc();
      statsDesc.setIsTblLevel(false);
      statsDesc.setDbName(dbName);
      statsDesc.setTableName(tblName);
      statsDesc.setPartName(partNames.get(pOff));
      partitionStats.setStatsDesc(statsDesc);
      statsList.add(partitionStats);
      // Build the list of Gets
      for (int i = 0; i < colKeys.length; i++) {
        colKeys[i] = HBaseUtils.buildKey(colNames.get(i));
      }
      byte[] partKey = HBaseUtils.buildPartitionKey(dbName, tblName, partVals.get(pOff));
      Get get = new Get(partKey);
      for (byte[] colName : colKeys) {
        get.addColumn(STATS_CF, colName);
      }
      gets.add(get);
    }

    HTableInterface htab = conn.getHBaseTable(PART_TABLE);
    // Get results from HBase
    Result[] results = htab.get(gets);
    // Deserialize the stats objects and add to stats list
    for (int pOff = 0; pOff < results.length; pOff++) {
      for (int cOff = 0; cOff < colNames.size(); cOff++) {
        byte[] serializedColStats = results[pOff].getValue(STATS_CF, colKeys[cOff]);
        if (serializedColStats == null) {
          // There were no stats for this column, so skip it
          continue;
        }
        partitionStats = statsList.get(pOff);
        ColumnStatisticsObj colStats =
            HBaseUtils.deserializeStatsForOneColumn(partitionStats, serializedColStats);
        colStats.setColName(colNames.get(cOff));
        partitionStats.addToStatsObj(colStats);
      }
    }
    return statsList;
  }

  /**
   * Get aggregate stats for a column from the DB and populate the bloom filter if it's not null
   * @param dbName
   * @param tblName
   * @param partNames
   * @param partVals
   * @param colNames
   * @return
   * @throws IOException
   */
  AggrStats getAggrStats(String dbName, String tblName, List<String> partNames,
      List<List<String>> partVals, List<String> colNames) throws IOException {
    // One ColumnStatisticsObj per column
    List<ColumnStatisticsObj> colStatsList = new ArrayList<ColumnStatisticsObj>();
    AggregateStatsCache.AggrColStats colStatsAggrCached;
    ColumnStatisticsObj colStatsAggr;
    int maxPartitionsPerCacheNode = aggrStatsCache.getMaxPartsPerCacheNode();
    float falsePositiveProbability = aggrStatsCache.getFalsePositiveProbability();
    int partitionsRequested = partNames.size();
    // TODO: Steal extrapolation logic from current MetaStoreDirectSql code
    // Right now doing nothing and keeping partitionsFound == partitionsRequested
    int partitionsFound = partitionsRequested;
    for (String colName : colNames) {
      if (partitionsRequested > maxPartitionsPerCacheNode) {
        // Read from HBase but don't add to cache since it doesn't qualify the criteria
        colStatsAggr = getAggrStatsFromDB(dbName, tblName, colName, partNames, partVals, null);
        colStatsList.add(colStatsAggr);
      } else {
        // Check the cache first
        colStatsAggrCached = aggrStatsCache.get(dbName, tblName, colName, partNames);
        if (colStatsAggrCached != null) {
          colStatsList.add(colStatsAggrCached.getColStats());
        } else {
          // Bloom filter for the new node that we will eventually add to the cache
          BloomFilter bloomFilter =
              new BloomFilter(maxPartitionsPerCacheNode, falsePositiveProbability);
          colStatsAggr =
              getAggrStatsFromDB(dbName, tblName, colName, partNames, partVals, bloomFilter);
          colStatsList.add(colStatsAggr);
          // Update the cache to add this new aggregate node
          aggrStatsCache.add(dbName, tblName, colName, partitionsFound, colStatsAggr, bloomFilter);
        }
      }
    }
    return new AggrStats(colStatsList, partitionsFound);
  }

  /**
   *
   * @param dbName
   * @param tblName
   * @param partNames
   * @param partVals
   * @param colName
   * @param bloomFilter
   * @return
   */
  private ColumnStatisticsObj getAggrStatsFromDB(String dbName, String tblName, String colName,
      List<String> partNames, List<List<String>> partVals, BloomFilter bloomFilter)
      throws IOException {
    ColumnStatisticsObj colStatsAggr = new ColumnStatisticsObj();
    boolean colStatsAggrInited = false;
    ColumnStatsAggregator colStatsAggregator = null;
    List<Get> gets = new ArrayList<Get>();
    byte[] colKey = HBaseUtils.buildKey(colName);
    // Build a list of Gets, one per partition
    for (int pOff = 0; pOff < partNames.size(); pOff++) {
      byte[] partKey = HBaseUtils.buildPartitionKey(dbName, tblName, partVals.get(pOff));
      Get get = new Get(partKey);
      get.addColumn(STATS_CF, colKey);
      gets.add(get);
    }
    HTableInterface htab = conn.getHBaseTable(PART_TABLE);
    // Get results from HBase
    Result[] results = htab.get(gets);
    // Iterate through the results
    // The results size and order is the same as the number and order of the Gets
    // If the column is not present in a partition, the Result object will be empty
    for (int pOff = 0; pOff < partNames.size(); pOff++) {
      if (results[pOff].isEmpty()) {
        // There were no stats for this column, so skip it
        continue;
      }
      byte[] serializedColStats = results[pOff].getValue(STATS_CF, colKey);
      if (serializedColStats == null) {
        // There were no stats for this column, so skip it
        continue;
      }
      ColumnStatisticsObj colStats =
          HBaseUtils.deserializeStatsForOneColumn(null, serializedColStats);
      if (!colStatsAggrInited) {
        // This is the 1st column stats object we got
        colStatsAggr.setColName(colName);
        colStatsAggr.setColType(colStats.getColType());
        colStatsAggr.setStatsData(colStats.getStatsData());
        colStatsAggregator =
            ColumnStatsAggregatorFactory.getColumnStatsAggregator(colStats.getStatsData()
                .getSetField());
        colStatsAggrInited = true;
      } else {
        // Perform aggregation with whatever we've already aggregated
        colStatsAggregator.aggregate(colStatsAggr, colStats);
      }
      // Add partition to the bloom filter if it's requested
      if (bloomFilter != null) {
        bloomFilter.add(partNames.get(pOff).getBytes());
      }
    }
    return colStatsAggr;
  }

  private byte[] getStatisticsKey(String dbName, String tableName, List<String> partVals) {
    return partVals == null ? HBaseUtils.buildKey(dbName, tableName) : HBaseUtils
        .buildPartitionKey(dbName, tableName, partVals);
  }

  private String getStatisticsTable(List<String> partVals) {
    return partVals == null ? TABLE_TABLE : PART_TABLE;
  }

  /**********************************************************************************************
   * Cache methods
   *********************************************************************************************/

  /**
   * This should be called whenever a new query is started.
   */
  void flushCatalogCache() {
    for (Counter counter : counters) {
      LOG.debug(counter.dump());
      counter.clear();
    }
    tableCache.flush();
    sdCache.flush();
    partCache.flush();
    flushRoleCache();
  }

  private void flushRoleCache() {
    roleCache.clear();
    entireRoleTableInCache = false;
  }

  /**********************************************************************************************
   * General access methods
   *********************************************************************************************/

  private void store(String table, byte[] key, byte[] colFam, byte[] colName, byte[] obj)
      throws IOException {
    HTableInterface htab = conn.getHBaseTable(table);
    Put p = new Put(key);
    p.add(colFam, colName, obj);
    htab.put(p);
    conn.flush(htab);
  }

  private void store(String table, byte[] key, byte[] colFam, byte[][] colName, byte[][] obj)
      throws IOException {
    HTableInterface htab = conn.getHBaseTable(table);
    Put p = new Put(key);
    for (int i = 0; i < colName.length; i++) {
      p.add(colFam, colName[i], obj[i]);
    }
    htab.put(p);
    conn.flush(htab);
  }

  private byte[] read(String table, byte[] key, byte[] colFam, byte[] colName) throws IOException {
    HTableInterface htab = conn.getHBaseTable(table);
    Get g = new Get(key);
    g.addColumn(colFam, colName);
    Result res = htab.get(g);
    return res.getValue(colFam, colName);
  }

  private Result read(String table, byte[] key, byte[] colFam, byte[][] colNames)
      throws IOException {
    HTableInterface htab = conn.getHBaseTable(table);
    Get g = new Get(key);
    for (byte[] colName : colNames) g.addColumn(colFam, colName);
    return htab.get(g);
  }

  // Delete a row.  If colFam and colName are not null, then only the named column will be
  // deleted.  If colName is null and colFam is not, only the named family will be deleted.  If
  // both are null the entire row will be deleted.
  private void delete(String table, byte[] key, byte[] colFam, byte[] colName) throws IOException {
    HTableInterface htab = conn.getHBaseTable(table);
    Delete d = new Delete(key);
    if (colName != null) d.deleteColumn(colFam, colName);
    else if (colFam != null) d.deleteFamily(colFam);
    htab.delete(d);
  }

  private Iterator<Result> scan(String table, byte[] colFam,
      byte[] colName) throws IOException {
    return scan(table, null, null, colFam, colName, null);
  }

  private Iterator<Result> scan(String table, byte[] colFam, byte[] colName,
      Filter filter) throws IOException {
    return scan(table, null, null, colFam, colName, filter);
  }

  private Iterator<Result> scan(String table, byte[] keyStart, byte[] keyEnd, byte[] colFam,
                                          byte[] colName, Filter filter) throws IOException {
    HTableInterface htab = conn.getHBaseTable(table);
    Scan s = new Scan();
    if (keyStart != null) {
      s.setStartRow(keyStart);
    }
    if (keyEnd != null) {
      s.setStopRow(keyEnd);
    }
    s.addColumn(colFam, colName);
    if (filter != null) {
      s.setFilter(filter);
    }
    ResultScanner scanner = htab.getScanner(s);
    return scanner.iterator();
  }



  /**********************************************************************************************
   * Testing methods and classes
   *********************************************************************************************/

  @VisibleForTesting
  int countStorageDescriptor() throws IOException {
    ResultScanner scanner = conn.getHBaseTable(SD_TABLE).getScanner(new Scan());
    int cnt = 0;
    Result r;
    do {
      r = scanner.next();
      if (r != null) {
        LOG.debug("Saw record with hash " + Base64.encodeBase64String(r.getRow()));
        cnt++;
      }
    } while (r != null);

    return cnt;
  }

  /**
   * Use this for unit testing only, so that a mock connection object can be passed in.
   * @param connection Mock connection objecct
   */
  @VisibleForTesting
  static void setTestConnection(HBaseConnection connection) {
    testConn = connection;
  }


  // For testing without the cache
  private static class BogusObjectCache<K, V> extends ObjectCache<K, V> {
    static Counter bogus = new Counter("bogus");

   BogusObjectCache() {
      super(1, bogus, bogus, bogus);
    }

    @Override
    V get(K key) {
      return null;
    }
  }

  private static class BogusPartitionCache extends PartitionCache {
    static Counter bogus = new Counter("bogus");

    BogusPartitionCache() {
      super(1, bogus, bogus, bogus);
    }

    @Override
    Collection<Partition> getAllForTable(String dbName, String tableName) {
      return null;
    }

    @Override
    Partition get(String dbName, String tableName, List<String> partVals) {
      return null;
    }
  }
}


File: metastore/src/java/org/apache/hadoop/hive/metastore/hbase/HBaseStore.java
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
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.hadoop.hive.metastore.hbase;

import org.apache.commons.lang.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hive.common.FileUtils;
import org.apache.hadoop.hive.metastore.HiveMetaStore;
import org.apache.hadoop.hive.metastore.PartFilterExprUtil;
import org.apache.hadoop.hive.metastore.PartitionExpressionProxy;
import org.apache.hadoop.hive.metastore.RawStore;
import org.apache.hadoop.hive.metastore.api.AggrStats;
import org.apache.hadoop.hive.metastore.api.ColumnStatistics;
import org.apache.hadoop.hive.metastore.api.CurrentNotificationEventId;
import org.apache.hadoop.hive.metastore.api.Database;
import org.apache.hadoop.hive.metastore.api.FieldSchema;
import org.apache.hadoop.hive.metastore.api.Function;
import org.apache.hadoop.hive.metastore.api.HiveObjectPrivilege;
import org.apache.hadoop.hive.metastore.api.HiveObjectRef;
import org.apache.hadoop.hive.metastore.api.HiveObjectType;
import org.apache.hadoop.hive.metastore.api.Index;
import org.apache.hadoop.hive.metastore.api.InvalidInputException;
import org.apache.hadoop.hive.metastore.api.InvalidObjectException;
import org.apache.hadoop.hive.metastore.api.InvalidPartitionException;
import org.apache.hadoop.hive.metastore.api.MetaException;
import org.apache.hadoop.hive.metastore.api.NoSuchObjectException;
import org.apache.hadoop.hive.metastore.api.NotificationEvent;
import org.apache.hadoop.hive.metastore.api.NotificationEventRequest;
import org.apache.hadoop.hive.metastore.api.NotificationEventResponse;
import org.apache.hadoop.hive.metastore.api.Partition;
import org.apache.hadoop.hive.metastore.api.PartitionEventType;
import org.apache.hadoop.hive.metastore.api.PrincipalPrivilegeSet;
import org.apache.hadoop.hive.metastore.api.PrincipalType;
import org.apache.hadoop.hive.metastore.api.PrivilegeBag;
import org.apache.hadoop.hive.metastore.api.PrivilegeGrantInfo;
import org.apache.hadoop.hive.metastore.api.Role;
import org.apache.hadoop.hive.metastore.api.RolePrincipalGrant;
import org.apache.hadoop.hive.metastore.api.Table;
import org.apache.hadoop.hive.metastore.api.Type;
import org.apache.hadoop.hive.metastore.api.UnknownDBException;
import org.apache.hadoop.hive.metastore.api.UnknownPartitionException;
import org.apache.hadoop.hive.metastore.api.UnknownTableException;
import org.apache.hadoop.hive.metastore.hbase.HBaseFilterPlanUtil.PlanResult;
import org.apache.hadoop.hive.metastore.hbase.HBaseFilterPlanUtil.ScanPlan;
import org.apache.hadoop.hive.metastore.parser.ExpressionTree;
import org.apache.hadoop.hive.metastore.partition.spec.PartitionSpecProxy;
import org.apache.thrift.TException;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

/**
 * Implementation of RawStore that stores data in HBase
 */
public class HBaseStore implements RawStore {
  static final private Log LOG = LogFactory.getLog(HBaseStore.class.getName());

  // Do not access this directly, call getHBase to make sure it is initialized.
  private HBaseReadWrite hbase = null;
  private Configuration conf;
  private int txnNestLevel = 0;
  private PartitionExpressionProxy expressionProxy = null;

  public HBaseStore() {
  }

  @Override
  public void shutdown() {
    try {
      if (txnNestLevel != 0) rollbackTransaction();
      getHBase().close();
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  @Override
  public boolean openTransaction() {
    if (txnNestLevel++ <= 0) {
      LOG.debug("Opening HBase transaction");
      getHBase().begin();
      txnNestLevel = 1;
    }
    return true;
  }

  @Override
  public boolean commitTransaction() {
    if (--txnNestLevel == 0) {
      LOG.debug("Committing HBase transaction");
      getHBase().commit();
    }
    return true;
  }

  @Override
  public void rollbackTransaction() {
    txnNestLevel = 0;
    LOG.debug("Rolling back HBase transaction");
    getHBase().rollback();
  }

  @Override
  public void createDatabase(Database db) throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {

      // HiveMetaStore already checks for existence of the database, don't recheck
      getHBase().putDb(db);
      commit = true;
    } catch (IOException e) {
      LOG.error("Unable to create database ", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }

  }

  @Override
  public Database getDatabase(String name) throws NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      Database db = getHBase().getDb(name);
      if (db == null) {
        throw new NoSuchObjectException("Unable to find db " + name);
      }
      commit = true;
      return db;
    } catch (IOException e) {
      LOG.error("Unable to get db", e);
      throw new NoSuchObjectException("Error reading db " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean dropDatabase(String dbname) throws NoSuchObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().deleteDb(dbname);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to delete db" + e);
      throw new MetaException("Unable to drop database " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean alterDatabase(String dbname, Database db) throws NoSuchObjectException,
      MetaException {
    // ObjectStore fetches the old db before updating it, but I can't see the possible value of
    // that since the caller will have needed to call getDatabase to have the db object.
    boolean commit = false;
    openTransaction();
    try {
      getHBase().putDb(db);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to alter database ", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<String> getDatabases(String pattern) throws MetaException {
    boolean commit = false;
    openTransaction();
    try {
      List<Database> dbs = getHBase().scanDatabases(likeToRegex(pattern));
      List<String> dbNames = new ArrayList<String>(dbs.size());
      for (Database db : dbs) dbNames.add(db.getName());
      commit = true;
      return dbNames;
    } catch (IOException e) {
      LOG.error("Unable to get databases ", e);
      throw new MetaException("Unable to get databases, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<String> getAllDatabases() throws MetaException {
    return getDatabases(null);
  }

  @Override
  public boolean createType(Type type) {
    throw new UnsupportedOperationException();
  }

  @Override
  public Type getType(String typeName) {
    throw new UnsupportedOperationException();
  }

  @Override
  public boolean dropType(String typeName) {
    throw new UnsupportedOperationException();
  }

  @Override
  public void createTable(Table tbl) throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    // HiveMetaStore above us checks if the table already exists, so we can blindly store it here.
    try {
      getHBase().putTable(tbl);
      commit = true;
    } catch (IOException e) {
      LOG.error("Unable to create table ", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean dropTable(String dbName, String tableName) throws MetaException,
      NoSuchObjectException, InvalidObjectException, InvalidInputException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().deleteTable(dbName, tableName);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to delete db" + e);
      throw new MetaException("Unable to drop table " + tableNameForErrorMsg(dbName, tableName));
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public Table getTable(String dbName, String tableName) throws MetaException {
    boolean commit = false;
    openTransaction();
    try {
      Table table = getHBase().getTable(dbName, tableName);
      if (table == null) {
        LOG.debug("Unable to find table " + tableNameForErrorMsg(dbName, tableName));
      }
      commit = true;
      return table;
    } catch (IOException e) {
      LOG.error("Unable to get table", e);
      throw new MetaException("Error reading table " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean addPartition(Partition part) throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().putPartition(part);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to add partition", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean addPartitions(String dbName, String tblName, List<Partition> parts)
      throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().putPartitions(parts);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to add partitions", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean addPartitions(String dbName, String tblName, PartitionSpecProxy partitionSpec,
                               boolean ifNotExists) throws InvalidObjectException, MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public Partition getPartition(String dbName, String tableName, List<String> part_vals) throws
      MetaException, NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      Partition part = getHBase().getPartition(dbName, tableName, part_vals);
      if (part == null) {
        throw new NoSuchObjectException("Unable to find partition " +
            partNameForErrorMsg(dbName, tableName, part_vals));
      }
      commit = true;
      return part;
    } catch (IOException e) {
      LOG.error("Unable to get partition", e);
      throw new MetaException("Error reading partition " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean doesPartitionExist(String dbName, String tableName, List<String> part_vals) throws
      MetaException, NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      boolean exists = getHBase().getPartition(dbName, tableName, part_vals) != null;
      commit = true;
      return exists;
    } catch (IOException e) {
      LOG.error("Unable to get partition", e);
      throw new MetaException("Error reading partition " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean dropPartition(String dbName, String tableName, List<String> part_vals) throws
      MetaException, NoSuchObjectException, InvalidObjectException, InvalidInputException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().deletePartition(dbName, tableName, part_vals);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to delete db" + e);
      throw new MetaException("Unable to drop partition " + partNameForErrorMsg(dbName, tableName,
          part_vals));
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<Partition> getPartitions(String dbName, String tableName, int max) throws
      MetaException, NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      List<Partition> parts = getHBase().scanPartitionsInTable(dbName, tableName, max);
      commit = true;
      return parts;
    } catch (IOException e) {
      LOG.error("Unable to get partitions", e);
      throw new MetaException("Error scanning partitions");
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public void alterTable(String dbname, String name, Table newTable) throws InvalidObjectException,
      MetaException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().replaceTable(getHBase().getTable(dbname, name), newTable);
      if (newTable.getPartitionKeys() != null && newTable.getPartitionKeys().size() > 0
          && !name.equals(newTable.getTableName())) {
        // They renamed the table, so we need to change each partition as well, since it changes
        // the key.
        try {
          List<Partition> oldParts = getPartitions(dbname, name, -1);
          List<Partition> newParts = new ArrayList<>(oldParts.size());
          for (Partition oldPart : oldParts) {
            Partition newPart = oldPart.deepCopy();
            newPart.setTableName(newTable.getTableName());
            newParts.add(newPart);
          }
          getHBase().replacePartitions(oldParts, newParts);
        } catch (NoSuchObjectException e) {
          LOG.debug("No partitions found for old table so not worrying about it");
        }

      }
      commit = true;
    } catch (IOException e) {
      LOG.error("Unable to alter table " + tableNameForErrorMsg(dbname, name), e);
      throw new MetaException("Unable to alter table " + tableNameForErrorMsg(dbname, name));
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<String> getTables(String dbName, String pattern) throws MetaException {
    boolean commit = false;
    openTransaction();
    try {
      List<Table> tables = getHBase().scanTables(dbName, likeToRegex(pattern));
      List<String> tableNames = new ArrayList<String>(tables.size());
      for (Table table : tables) tableNames.add(table.getTableName());
      commit = true;
      return tableNames;
    } catch (IOException e) {
      LOG.error("Unable to get tables ", e);
      throw new MetaException("Unable to get tables, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<Table> getTableObjectsByName(String dbname, List<String> tableNames) throws
      MetaException, UnknownDBException {
    boolean commit = false;
    openTransaction();
    try {
      List<Table> tables = getHBase().getTables(dbname, tableNames);
      commit = true;
      return tables;
    } catch (IOException e) {
      LOG.error("Unable to get tables ", e);
      throw new MetaException("Unable to get tables, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<String> getAllTables(String dbName) throws MetaException {
    return getTables(dbName, null);
  }

  @Override
  public List<String> listTableNamesByFilter(String dbName, String filter, short max_tables) throws
      MetaException, UnknownDBException {
    // TODO needs to wait until we support pushing filters into HBase.
    throw new UnsupportedOperationException();
  }

  @Override
  public List<String> listPartitionNames(String db_name, String tbl_name, short max_parts) throws
      MetaException {
    boolean commit = false;
    openTransaction();
    try {
      List<Partition> parts = getHBase().scanPartitionsInTable(db_name, tbl_name, max_parts);
      if (parts == null) return null;
      List<String> names = new ArrayList<String>(parts.size());
      Table table = getHBase().getTable(db_name, tbl_name);
      for (Partition p : parts) {
        names.add(buildExternalPartName(table, p));
      }
      commit = true;
      return names;
    } catch (IOException e) {
      LOG.error("Unable to get partitions", e);
      throw new MetaException("Error scanning partitions");
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<String> listPartitionNamesByFilter(String db_name, String tbl_name, String filter,
                                                 short max_parts) throws MetaException {
    // TODO needs to wait until we support pushing filters into HBase.
    throw new UnsupportedOperationException();
  }

  @Override
  public void alterPartition(String db_name, String tbl_name, List<String> part_vals,
                             Partition new_part) throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      Partition oldPart = getHBase().getPartition(db_name, tbl_name, part_vals);
      getHBase().replacePartition(oldPart, new_part);
      commit = true;
    } catch (IOException e) {
      LOG.error("Unable to add partition", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public void alterPartitions(String db_name, String tbl_name, List<List<String>> part_vals_list,
                              List<Partition> new_parts) throws InvalidObjectException,
      MetaException {
    boolean commit = false;
    openTransaction();
    try {
      List<Partition> oldParts = getHBase().getPartitions(db_name, tbl_name, part_vals_list);
      getHBase().replacePartitions(oldParts, new_parts);
      commit = true;
    } catch (IOException e) {
      LOG.error("Unable to add partition", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean addIndex(Index index) throws InvalidObjectException, MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public Index getIndex(String dbName, String origTableName, String indexName) throws
      MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public boolean dropIndex(String dbName, String origTableName, String indexName) throws
      MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public List<Index> getIndexes(String dbName, String origTableName, int max) throws MetaException {
    // TODO - Index not currently supported.  But I need to return an empty list or else drop
    // table cores.
    return new ArrayList<Index>();
  }

  @Override
  public List<String> listIndexNames(String dbName, String origTableName, short max) throws
      MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public void alterIndex(String dbname, String baseTblName, String name, Index newIndex) throws
      InvalidObjectException, MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public List<Partition> getPartitionsByFilter(String dbName, String tblName, String filter,
                                               short maxParts) throws MetaException,
      NoSuchObjectException {
    final ExpressionTree exprTree = (filter != null && !filter.isEmpty()) ? PartFilterExprUtil
        .getFilterParser(filter).tree : ExpressionTree.EMPTY_TREE;
    List<Partition> result = new ArrayList<Partition>();
    boolean commit = false;
    openTransaction();
    try {
      getPartitionsByExprInternal(dbName, tblName, exprTree, maxParts, result);
      return result;
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean getPartitionsByExpr(String dbName, String tblName, byte[] expr,
                                     String defaultPartitionName, short maxParts,
                                     List<Partition> result) throws TException {
    final ExpressionTree exprTree = PartFilterExprUtil.makeExpressionTree(expressionProxy, expr);
    // TODO: investigate if there should be any role for defaultPartitionName in this
    // implementation. direct sql code path in ObjectStore does not use it.

    boolean commit = false;
    openTransaction();
    try {
      return getPartitionsByExprInternal(dbName, tblName, exprTree, maxParts, result);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  private boolean getPartitionsByExprInternal(String dbName, String tblName,
      ExpressionTree exprTree, short maxParts, List<Partition> result) throws MetaException,
      NoSuchObjectException {

    Table table = getTable(dbName, tblName);
    if (table == null) {
      throw new NoSuchObjectException("Unable to find table " + dbName + "." + tblName);
    }
    String firstPartitionColumn = table.getPartitionKeys().get(0).getName();
    // general hbase filter plan from expression tree
    PlanResult planRes = HBaseFilterPlanUtil.getFilterPlan(exprTree, firstPartitionColumn);

    if (LOG.isDebugEnabled()) {
      LOG.debug("Hbase Filter Plan generated : " + planRes.plan);
    }

    // results from scans need to be merged as there can be overlapping results between
    // the scans. Use a map of list of partition values to partition for this.
    Map<List<String>, Partition> mergedParts = new HashMap<List<String>, Partition>();
    for (ScanPlan splan : planRes.plan.getPlans()) {
      try {
        List<Partition> parts = getHBase().scanPartitions(dbName, tblName,
            splan.getStartRowSuffix(), splan.getEndRowSuffix(), null, -1);
        boolean reachedMax = false;
        for (Partition part : parts) {
          mergedParts.put(part.getValues(), part);
          if (mergedParts.size() == maxParts) {
            reachedMax = true;
            break;
          }
        }
        if (reachedMax) {
          break;
        }
      } catch (IOException e) {
        LOG.error("Unable to get partitions", e);
        throw new MetaException("Error scanning partitions" + tableNameForErrorMsg(dbName, tblName)
            + ": " + e);
      }
    }
    for (Entry<List<String>, Partition> mp : mergedParts.entrySet()) {
      result.add(mp.getValue());
    }
    if (LOG.isDebugEnabled()) {
      LOG.debug("Matched partitions " + result);
    }

    // return true if there might be some additional partitions that don't match filter conditions
    // being returned
    return !planRes.hasUnsupportedCondition;
  }

  @Override
  public List<Partition> getPartitionsByNames(String dbName, String tblName,
                                              List<String> partNames) throws MetaException,
      NoSuchObjectException {
    List<Partition> parts = new ArrayList<Partition>();
    for (String partName : partNames) {
      parts.add(getPartition(dbName, tblName, partNameToVals(partName)));
    }
    return parts;
  }

  @Override
  public Table markPartitionForEvent(String dbName, String tblName, Map<String, String> partVals,
                                     PartitionEventType evtType) throws MetaException,
      UnknownTableException, InvalidPartitionException, UnknownPartitionException {
    throw new UnsupportedOperationException();
  }

  @Override
  public boolean isPartitionMarkedForEvent(String dbName, String tblName,
                                           Map<String, String> partName,
                                           PartitionEventType evtType) throws MetaException,
      UnknownTableException, InvalidPartitionException, UnknownPartitionException {
    throw new UnsupportedOperationException();
  }

  /*
   * The design for roles.  Roles are a pain because of their hierarchical nature.  When a user
   * comes in and we need to be able to determine all roles he is a part of, we do not want to
   * have to walk the hierarchy in the database.  This means we need to flatten the role map for
   * each user.  But we also have to track how the roles are connected for each user, in case one
   * role is revoked from another (e.g. if role1 is included in role2 but then revoked
   * from it and user1 was granted both role2 and role1 we cannot remove user1 from role1
   * because he was granted that separately).
   *
   * We want to optimize for the read case and put the cost on grant and revoke of roles, since
   * we assume that is the less common case.  So we lay out the roles data as follows:
   *
   * There is a ROLES table that records each role, plus what other principals have been granted
   * into it, along with the info on grantor, etc.
   *
   * There is a USER_TO_ROLES table that contains the mapping of each user to every role he is a
   * part of.
   *
   * This makes determining what roles a user participates in very quick, as USER_TO_ROLE is a
   * simple list for each user.  It makes granting users into roles expensive, and granting roles
   * into roles very expensive.  Each time a user is granted into a role, we need to walk the
   * hierarchy in the role table (which means moving through that table multiple times) to
   * determine every role the user participates in.  Each a role is granted into another role
   * this hierarchical walk must be done for every principal in the role being granted into.  To
   * mitigate this pain somewhat whenever doing these mappings we cache the entire ROLES table in
   * memory since we assume it is not large.
   *
   * On a related note, whenever a role is dropped we must walk not only all these role tables
   * above (equivalent to a role being revoked from another role, since we have to rebuilding
   * mappings for any users in roles that contained that role and any users directly in that
   * role), but we also have to remove all the privileges associated with that role directly.
   * That means a walk of the DBS table and of the TBLS table.
   */

  @Override
  public boolean addRole(String roleName, String ownerName) throws InvalidObjectException,
      MetaException, NoSuchObjectException {
    int now = (int)(System.currentTimeMillis()/1000);
    Role role = new Role(roleName, now, ownerName);
    boolean commit = false;
    openTransaction();
    try {
      if (getHBase().getRole(roleName) != null) {
        throw new InvalidObjectException("Role " + roleName + " already exists");
      }
      getHBase().putRole(role);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to create role ", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean removeRole(String roleName) throws MetaException, NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      Set<String> usersInRole = getHBase().findAllUsersInRole(roleName);
      getHBase().deleteRole(roleName);
      getHBase().removeRoleGrants(roleName);
      for (String user : usersInRole) {
        getHBase().buildRoleMapForUser(user);
      }
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to delete role" + e);
      throw new MetaException("Unable to drop role " + roleName);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean grantRole(Role role, String userName, PrincipalType principalType, String grantor,
                           PrincipalType grantorType, boolean grantOption)
      throws MetaException, NoSuchObjectException, InvalidObjectException {
    boolean commit = false;
    openTransaction();
    try {
      Set<String> usersToRemap = findUsersToRemapRolesFor(role, userName, principalType);
      HbaseMetastoreProto.RoleGrantInfo.Builder builder =
          HbaseMetastoreProto.RoleGrantInfo.newBuilder();
      if (userName != null) builder.setPrincipalName(userName);
      if (principalType != null) {
        builder.setPrincipalType(HBaseUtils.convertPrincipalTypes(principalType));
      }
      builder.setAddTime((int)(System.currentTimeMillis() / 1000));
      if (grantor != null) builder.setGrantor(grantor);
      if (grantorType != null) {
        builder.setGrantorType(HBaseUtils.convertPrincipalTypes(grantorType));
      }
      builder.setGrantOption(grantOption);

      getHBase().addPrincipalToRole(role.getRoleName(), builder.build());
      for (String user : usersToRemap) {
        getHBase().buildRoleMapForUser(user);
      }
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to grant role", e);
      throw new MetaException("Unable to grant role " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean revokeRole(Role role, String userName, PrincipalType principalType,
                            boolean grantOption) throws MetaException, NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    // This can have a couple of different meanings.  If grantOption is true, then this is only
    // revoking the grant option, the role itself doesn't need to be removed.  If it is false
    // then we need to remove the userName from the role altogether.
    try {
      if (grantOption) {
        // If this is a grant only change, we don't need to rebuild the user mappings.
        getHBase().dropPrincipalFromRole(role.getRoleName(), userName, principalType, grantOption);
      } else {
        Set<String> usersToRemap = findUsersToRemapRolesFor(role, userName, principalType);
        getHBase().dropPrincipalFromRole(role.getRoleName(), userName, principalType, grantOption);
        for (String user : usersToRemap) {
          getHBase().buildRoleMapForUser(user);
        }
      }
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to revoke role " + role.getRoleName() + " from " + userName, e);
      throw new MetaException("Unable to revoke role " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public PrincipalPrivilegeSet getUserPrivilegeSet(String userName, List<String> groupNames)
      throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      PrincipalPrivilegeSet pps = new PrincipalPrivilegeSet();
      PrincipalPrivilegeSet global = getHBase().getGlobalPrivs();
      if (global == null) return null;
      List<PrivilegeGrantInfo> pgi;
      if (global.getUserPrivileges() != null) {
        pgi = global.getUserPrivileges().get(userName);
        if (pgi != null) {
          pps.putToUserPrivileges(userName, pgi);
        }
      }

      if (global.getRolePrivileges() != null) {
        List<String> roles = getHBase().getUserRoles(userName);
        if (roles != null) {
          for (String role : roles) {
            pgi = global.getRolePrivileges().get(role);
            if (pgi != null) {
              pps.putToRolePrivileges(role, pgi);
            }
          }
        }
      }
      commit = true;
      return pps;
    } catch (IOException e) {
      LOG.error("Unable to get db privileges for user", e);
      throw new MetaException("Unable to get db privileges for user, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public PrincipalPrivilegeSet getDBPrivilegeSet(String dbName, String userName,
                                                 List<String> groupNames)
      throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      PrincipalPrivilegeSet pps = new PrincipalPrivilegeSet();
      Database db = getHBase().getDb(dbName);
      if (db.getPrivileges() != null) {
        List<PrivilegeGrantInfo> pgi;
        // Find the user privileges for this db
        if (db.getPrivileges().getUserPrivileges() != null) {
          pgi = db.getPrivileges().getUserPrivileges().get(userName);
          if (pgi != null) {
            pps.putToUserPrivileges(userName, pgi);
          }
        }

        if (db.getPrivileges().getRolePrivileges() != null) {
          List<String> roles = getHBase().getUserRoles(userName);
          if (roles != null) {
            for (String role : roles) {
              pgi = db.getPrivileges().getRolePrivileges().get(role);
              if (pgi != null) {
                pps.putToRolePrivileges(role, pgi);
              }
            }
          }
        }
      }
      commit = true;
      return pps;
    } catch (IOException e) {
      LOG.error("Unable to get db privileges for user", e);
      throw new MetaException("Unable to get db privileges for user, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public PrincipalPrivilegeSet getTablePrivilegeSet(String dbName, String tableName,
                                                    String userName, List<String> groupNames)
      throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      PrincipalPrivilegeSet pps = new PrincipalPrivilegeSet();
      Table table = getHBase().getTable(dbName, tableName);
      List<PrivilegeGrantInfo> pgi;
      if (table.getPrivileges() != null) {
        if (table.getPrivileges().getUserPrivileges() != null) {
          pgi = table.getPrivileges().getUserPrivileges().get(userName);
          if (pgi != null) {
            pps.putToUserPrivileges(userName, pgi);
          }
        }

        if (table.getPrivileges().getRolePrivileges() != null) {
          List<String> roles = getHBase().getUserRoles(userName);
          if (roles != null) {
            for (String role : roles) {
              pgi = table.getPrivileges().getRolePrivileges().get(role);
              if (pgi != null) {
                pps.putToRolePrivileges(role, pgi);
              }
            }
          }
        }
      }
      commit = true;
      return pps;
    } catch (IOException e) {
      LOG.error("Unable to get db privileges for user", e);
      throw new MetaException("Unable to get db privileges for user, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public PrincipalPrivilegeSet getPartitionPrivilegeSet(String dbName, String tableName,
                                                        String partition, String userName,
                                                        List<String> groupNames) throws
      InvalidObjectException, MetaException {
    // We don't support partition privileges
    return null;
  }

  @Override
  public PrincipalPrivilegeSet getColumnPrivilegeSet(String dbName, String tableName,
                                                     String partitionName, String columnName,
                                                     String userName,
                                                     List<String> groupNames) throws
      InvalidObjectException, MetaException {
    // We don't support column level privileges
    return null;
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalGlobalGrants(String principalName,
                                                             PrincipalType principalType) {
    List<PrivilegeGrantInfo> grants;
    List<HiveObjectPrivilege> privileges = new ArrayList<HiveObjectPrivilege>();
    boolean commit = false;
    openTransaction();
    try {
      PrincipalPrivilegeSet pps = getHBase().getGlobalPrivs();
      if (pps == null) return privileges;
      Map<String, List<PrivilegeGrantInfo>> map;
      switch (principalType) {
        case USER:
          map = pps.getUserPrivileges();
          break;

        case ROLE:
          map = pps.getRolePrivileges();
          break;

        default:
          throw new RuntimeException("Unknown or unsupported principal type " +
              principalType.toString());
      }
      if (map == null) return privileges;
      grants = map.get(principalName);

      if (grants == null || grants.size() == 0) return privileges;
      for (PrivilegeGrantInfo pgi : grants) {
        privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.GLOBAL, null,
            null, null, null), principalName, principalType, pgi));
      }
      commit = true;
      return privileges;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalDBGrants(String principalName,
                                                         PrincipalType principalType,
                                                         String dbName) {
    List<PrivilegeGrantInfo> grants;
    List<HiveObjectPrivilege> privileges = new ArrayList<HiveObjectPrivilege>();
    boolean commit = false;
    openTransaction();
    try {
      Database db = getHBase().getDb(dbName);
      if (db == null) return privileges;
      PrincipalPrivilegeSet pps = db.getPrivileges();
      if (pps == null) return privileges;
      Map<String, List<PrivilegeGrantInfo>> map;
      switch (principalType) {
        case USER:
          map = pps.getUserPrivileges();
          break;

        case ROLE:
          map = pps.getRolePrivileges();
          break;

        default:
          throw new RuntimeException("Unknown or unsupported principal type " +
              principalType.toString());
      }
      if (map == null) return privileges;
      grants = map.get(principalName);

      if (grants == null || grants.size() == 0) return privileges;
      for (PrivilegeGrantInfo pgi : grants) {
        privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.DATABASE, dbName,
         null, null, null), principalName, principalType, pgi));
      }
      commit = true;
      return privileges;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listAllTableGrants(String principalName,
                                                      PrincipalType principalType,
                                                      String dbName,
                                                      String tableName) {
    List<PrivilegeGrantInfo> grants;
    List<HiveObjectPrivilege> privileges = new ArrayList<HiveObjectPrivilege>();
    boolean commit = false;
    openTransaction();
    try {
      Table table = getHBase().getTable(dbName, tableName);
      if (table == null) return privileges;
      PrincipalPrivilegeSet pps = table.getPrivileges();
      if (pps == null) return privileges;
      Map<String, List<PrivilegeGrantInfo>> map;
      switch (principalType) {
        case USER:
          map = pps.getUserPrivileges();
          break;

        case ROLE:
          map = pps.getRolePrivileges();
          break;

        default:
          throw new RuntimeException("Unknown or unsupported principal type " +
              principalType.toString());
      }
      if (map == null) return privileges;
      grants = map.get(principalName);

      if (grants == null || grants.size() == 0) return privileges;
      for (PrivilegeGrantInfo pgi : grants) {
        privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.TABLE, dbName,
            tableName, null, null), principalName, principalType, pgi));
      }
      commit = true;
      return privileges;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalPartitionGrants(String principalName,
                                                                PrincipalType principalType,
                                                                String dbName,
                                                                String tableName,
                                                                List<String> partValues,
                                                                String partName) {
    // We don't support partition grants
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalTableColumnGrants(String principalName,
                                                                  PrincipalType principalType,
                                                                  String dbName, String tableName,
                                                                  String columnName) {
    // We don't support column grants
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalPartitionColumnGrants(String principalName,
                                                                      PrincipalType principalType,
                                                                      String dbName,
                                                                      String tableName,
                                                                      List<String> partVals,
                                                                      String partName,
                                                                      String columnName) {
    // We don't support column grants
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public boolean grantPrivileges(PrivilegeBag privileges)
      throws InvalidObjectException, MetaException, NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      for (HiveObjectPrivilege priv : privileges.getPrivileges()) {
        // Locate the right object to deal with
        PrivilegeInfo privilegeInfo = findPrivilegeToGrantOrRevoke(priv);

        // Now, let's see if we've already got this privilege
        for (PrivilegeGrantInfo info : privilegeInfo.grants) {
          if (info.getPrivilege().equals(priv.getGrantInfo().getPrivilege())) {
            throw new InvalidObjectException(priv.getPrincipalName() + " already has " +
                priv.getGrantInfo().getPrivilege() + " on " + privilegeInfo.typeErrMsg);
          }
        }
        privilegeInfo.grants.add(priv.getGrantInfo());

        writeBackGrantOrRevoke(priv, privilegeInfo);
      }
      commit = true;
      return true;
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean revokePrivileges(PrivilegeBag privileges, boolean grantOption) throws
      InvalidObjectException, MetaException, NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      for (HiveObjectPrivilege priv : privileges.getPrivileges()) {
        PrivilegeInfo privilegeInfo = findPrivilegeToGrantOrRevoke(priv);

        for (int i = 0; i < privilegeInfo.grants.size(); i++) {
          if (privilegeInfo.grants.get(i).getPrivilege().equals(
              priv.getGrantInfo().getPrivilege())) {
            if (grantOption) privilegeInfo.grants.get(i).setGrantOption(false);
            else privilegeInfo.grants.remove(i);
            break;
          }
        }
        writeBackGrantOrRevoke(priv, privilegeInfo);
      }
      commit = true;
      return true;
    } finally {
      commitOrRoleBack(commit);
    }
  }

  private static class PrivilegeInfo {
    Database db;
    Table table;
    List<PrivilegeGrantInfo> grants;
    String typeErrMsg;
    PrincipalPrivilegeSet privSet;
  }

  private PrivilegeInfo findPrivilegeToGrantOrRevoke(HiveObjectPrivilege privilege)
      throws MetaException, NoSuchObjectException, InvalidObjectException {
    PrivilegeInfo result = new PrivilegeInfo();
    switch (privilege.getHiveObject().getObjectType()) {
      case GLOBAL:
        try {
          result.privSet = createOnNull(getHBase().getGlobalPrivs());
        } catch (IOException e) {
          LOG.error("Unable to fetch global privileges", e);
          throw new MetaException("Unable to fetch global privileges, " + e.getMessage());
        }
        result.typeErrMsg = "global";
        break;

      case DATABASE:
        result.db = getDatabase(privilege.getHiveObject().getDbName());
        result.typeErrMsg = "database " + result.db.getName();
        result.privSet = createOnNull(result.db.getPrivileges());
        break;

      case TABLE:
        result.table = getTable(privilege.getHiveObject().getDbName(),
            privilege.getHiveObject().getObjectName());
        result.typeErrMsg = "table " + result.table.getTableName();
        result.privSet = createOnNull(result.table.getPrivileges());
        break;

      case PARTITION:
      case COLUMN:
        throw new RuntimeException("HBase metastore does not support partition or column " +
            "permissions");

      default:
        throw new RuntimeException("Woah bad, unknown object type " +
            privilege.getHiveObject().getObjectType());
    }

    // Locate the right PrivilegeGrantInfo
    Map<String, List<PrivilegeGrantInfo>> grantInfos;
    switch (privilege.getPrincipalType()) {
      case USER:
        grantInfos = result.privSet.getUserPrivileges();
        result.typeErrMsg = "user";
        break;

      case GROUP:
        throw new RuntimeException("HBase metastore does not support group permissions");

      case ROLE:
        grantInfos = result.privSet.getRolePrivileges();
        result.typeErrMsg = "role";
        break;

      default:
        throw new RuntimeException("Woah bad, unknown principal type " +
            privilege.getPrincipalType());
    }

    // Find the requested name in the grantInfo
    result.grants = grantInfos.get(privilege.getPrincipalName());
    if (result.grants == null) {
      // Means we don't have any grants for this user yet.
      result.grants = new ArrayList<PrivilegeGrantInfo>();
      grantInfos.put(privilege.getPrincipalName(), result.grants);
    }
    return result;
  }

  private PrincipalPrivilegeSet createOnNull(PrincipalPrivilegeSet pps) {
    // If this is the first time a user has been granted a privilege set will be null.
    if (pps == null) {
      pps = new PrincipalPrivilegeSet();
    }
    if (pps.getUserPrivileges() == null) {
      pps.setUserPrivileges(new HashMap<String, List<PrivilegeGrantInfo>>());
    }
    if (pps.getRolePrivileges() == null) {
      pps.setRolePrivileges(new HashMap<String, List<PrivilegeGrantInfo>>());
    }
    return pps;
  }

  private void writeBackGrantOrRevoke(HiveObjectPrivilege priv, PrivilegeInfo pi)
      throws MetaException, NoSuchObjectException, InvalidObjectException {
    // Now write it back
    switch (priv.getHiveObject().getObjectType()) {
      case GLOBAL:
        try {
          getHBase().putGlobalPrivs(pi.privSet);
        } catch (IOException e) {
          LOG.error("Unable to write global privileges", e);
          throw new MetaException("Unable to write global privileges, " + e.getMessage());
        }
        break;

      case DATABASE:
        pi.db.setPrivileges(pi.privSet);
        alterDatabase(pi.db.getName(), pi.db);
        break;

      case TABLE:
        pi.table.setPrivileges(pi.privSet);
        alterTable(pi.table.getDbName(), pi.table.getTableName(), pi.table);
        break;

      default:
        throw new RuntimeException("Dude, you missed the second switch!");
    }
  }

  @Override
  public Role getRole(String roleName) throws NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      Role role = getHBase().getRole(roleName);
      if (role == null) {
        throw new NoSuchObjectException("Unable to find role " + roleName);
      }
      commit = true;
      return role;
    } catch (IOException e) {
      LOG.error("Unable to get role", e);
      throw new NoSuchObjectException("Error reading table " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<String> listRoleNames() {
    boolean commit = false;
    openTransaction();
    try {
      List<Role> roles = getHBase().scanRoles();
      List<String> roleNames = new ArrayList<String>(roles.size());
      for (Role role : roles) roleNames.add(role.getRoleName());
      commit = true;
      return roleNames;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<Role> listRoles(String principalName, PrincipalType principalType) {
    List<Role> roles = new ArrayList<Role>();
    boolean commit = false;
    openTransaction();
    try {
      try {
        roles.addAll(getHBase().getPrincipalDirectRoles(principalName, principalType));
      } catch (IOException e) {
        throw new RuntimeException(e);
      }
      // Add the public role if this is a user
      if (principalType == PrincipalType.USER) {
        roles.add(new Role(HiveMetaStore.PUBLIC, 0, null));
      }
      commit = true;
      return roles;
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<RolePrincipalGrant> listRolesWithGrants(String principalName,
                                                      PrincipalType principalType) {
    boolean commit = false;
    openTransaction();
    try {
      List<Role> roles = listRoles(principalName, principalType);
      List<RolePrincipalGrant> rpgs = new ArrayList<RolePrincipalGrant>(roles.size());
      for (Role role : roles) {
        HbaseMetastoreProto.RoleGrantInfoList grants = getHBase().getRolePrincipals(role.getRoleName());
        if (grants != null) {
          for (HbaseMetastoreProto.RoleGrantInfo grant : grants.getGrantInfoList()) {
            if (grant.getPrincipalType() == HBaseUtils.convertPrincipalTypes(principalType) &&
                grant.getPrincipalName().equals(principalName)) {
              rpgs.add(new RolePrincipalGrant(role.getRoleName(), principalName, principalType,
                  grant.getGrantOption(), (int) grant.getAddTime(), grant.getGrantor(),
                  HBaseUtils.convertPrincipalTypes(grant.getGrantorType())));
            }
          }
        }
      }
      commit = true;
      return rpgs;
    } catch (Exception e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<RolePrincipalGrant> listRoleMembers(String roleName) {
    boolean commit = false;
    openTransaction();
    try {
      HbaseMetastoreProto.RoleGrantInfoList gil = getHBase().getRolePrincipals(roleName);
      List<RolePrincipalGrant> roleMaps = new ArrayList<RolePrincipalGrant>(gil.getGrantInfoList().size());
      for (HbaseMetastoreProto.RoleGrantInfo giw : gil.getGrantInfoList()) {
        roleMaps.add(new RolePrincipalGrant(roleName, giw.getPrincipalName(),
            HBaseUtils.convertPrincipalTypes(giw.getPrincipalType()),
            giw.getGrantOption(), (int)giw.getAddTime(), giw.getGrantor(),
            HBaseUtils.convertPrincipalTypes(giw.getGrantorType())));
      }
      commit = true;
      return roleMaps;
    } catch (Exception e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public Partition getPartitionWithAuth(String dbName, String tblName, List<String> partVals,
                                        String user_name, List<String> group_names)
      throws MetaException, NoSuchObjectException, InvalidObjectException {
    // We don't do authorization checks for partitions.
    return getPartition(dbName, tblName, partVals);
  }

  @Override
  public List<Partition> getPartitionsWithAuth(String dbName, String tblName, short maxParts,
                                               String userName, List<String> groupNames)
      throws MetaException, NoSuchObjectException, InvalidObjectException {
    // We don't do authorization checks for partitions.
    return getPartitions(dbName, tblName, maxParts);
  }

  @Override
  public List<String> listPartitionNamesPs(String db_name, String tbl_name, List<String> part_vals,
                                           short max_parts)
      throws MetaException, NoSuchObjectException {
    List<Partition> parts =
        listPartitionsPsWithAuth(db_name, tbl_name, part_vals, max_parts, null, null);
    List<String> partNames = new ArrayList<String>(parts.size());
    for (Partition part : parts) {
      partNames.add(buildExternalPartName(db_name, tbl_name, part.getValues()));
    }
    return partNames;
  }


  @Override
  public List<Partition> listPartitionsPsWithAuth(String db_name, String tbl_name,
                                                  List<String> part_vals, short max_parts,
                                                  String userName, List<String> groupNames)
      throws MetaException, NoSuchObjectException {
    // We don't handle auth info with partitions
    boolean commit = false;
    openTransaction();
    try {
      List<Partition> parts = getHBase().scanPartitions(db_name, tbl_name, part_vals, max_parts);
      commit = true;
      return parts;
    } catch (IOException e) {
      LOG.error("Unable to list partition names", e);
      throw new MetaException("Failed to list part names, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean updateTableColumnStatistics(ColumnStatistics colStats) throws
      NoSuchObjectException, MetaException, InvalidObjectException, InvalidInputException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().updateStatistics(colStats.getStatsDesc().getDbName(),
          colStats.getStatsDesc().getTableName(), null, null, colStats);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to update column statistics", e);
      throw new MetaException("Failed to update column statistics, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean updatePartitionColumnStatistics(ColumnStatistics statsObj,
                                                 List<String> partVals) throws
      NoSuchObjectException, MetaException, InvalidObjectException, InvalidInputException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().updateStatistics(statsObj.getStatsDesc().getDbName(),
          statsObj.getStatsDesc().getTableName(), statsObj.getStatsDesc().getPartName(),
          partVals, statsObj);
      commit = true;
      return true;
    } catch (IOException e) {
      LOG.error("Unable to update column statistics", e);
      throw new MetaException("Failed to update column statistics, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public ColumnStatistics getTableColumnStatistics(String dbName, String tableName,
                                                   List<String> colName) throws MetaException,
      NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      ColumnStatistics cs = getHBase().getTableStatistics(dbName, tableName, colName);
      commit = true;
      return cs;
    } catch (IOException e) {
      LOG.error("Unable to fetch column statistics", e);
      throw new MetaException("Failed to fetch column statistics, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<ColumnStatistics> getPartitionColumnStatistics(String dbName, String tblName,
      List<String> partNames, List<String> colNames) throws MetaException, NoSuchObjectException {
    List<List<String>> partVals = new ArrayList<List<String>>(partNames.size());
    for (String partName : partNames) {
      partVals.add(partNameToVals(partName));
    }
    for (String partName : partNames) partVals.add(partNameToVals(partName));
    boolean commit = false;
    openTransaction();
    try {
      List<ColumnStatistics> cs =
          getHBase().getPartitionStatistics(dbName, tblName, partNames,  partVals, colNames);
      commit = true;
      return cs;
    } catch (IOException e) {
      LOG.error("Unable to fetch column statistics", e);
      throw new MetaException("Failed fetching column statistics, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public boolean deletePartitionColumnStatistics(String dbName, String tableName, String partName,
      List<String> partVals, String colName) throws NoSuchObjectException, MetaException,
      InvalidObjectException, InvalidInputException {
    // NOP, stats will be deleted along with the partition when it is dropped.
    return true;
  }

  @Override
  public boolean deleteTableColumnStatistics(String dbName, String tableName, String colName) throws
      NoSuchObjectException, MetaException, InvalidObjectException, InvalidInputException {
    // NOP, stats will be deleted along with the table when it is dropped.
    return true;
  }

  /**
   * Return aggregated statistics for each column in the colNames list aggregated over partitions in
   * the partNames list
   *
   */
  @Override
  public AggrStats get_aggr_stats_for(String dbName, String tblName, List<String> partNames,
      List<String> colNames) throws MetaException, NoSuchObjectException {
    List<List<String>> partVals = new ArrayList<List<String>>(partNames.size());
    for (String partName : partNames) {
      partVals.add(partNameToVals(partName));
    }
    boolean commit = false;
    openTransaction();
    try {
      AggrStats stats = getHBase().getAggrStats(dbName, tblName, partNames, partVals, colNames);
      commit = true;
      return stats;
    } catch (IOException e) {
      LOG.error("Unable to fetch aggregate column statistics", e);
      throw new MetaException("Failed fetching aggregate column statistics, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public long cleanupEvents() {
    throw new UnsupportedOperationException();
  }

  @Override
  public boolean addToken(String tokenIdentifier, String delegationToken) {
    throw new UnsupportedOperationException();
  }

  @Override
  public boolean removeToken(String tokenIdentifier) {
    throw new UnsupportedOperationException();
  }

  @Override
  public String getToken(String tokenIdentifier) {
    throw new UnsupportedOperationException();
  }

  @Override
  public List<String> getAllTokenIdentifiers() {
    throw new UnsupportedOperationException();
  }

  @Override
  public int addMasterKey(String key) throws MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public void updateMasterKey(Integer seqNo, String key) throws NoSuchObjectException,
      MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public boolean removeMasterKey(Integer keySeq) {
    throw new UnsupportedOperationException();
  }

  @Override
  public String[] getMasterKeys() {
    throw new UnsupportedOperationException();
  }

  @Override
  public void verifySchema() throws MetaException {

  }

  @Override
  public String getMetaStoreSchemaVersion() throws MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public void setMetaStoreSchemaVersion(String version, String comment) throws MetaException {
    throw new UnsupportedOperationException();
  }

  @Override
  public void dropPartitions(String dbName, String tblName, List<String> partNames) throws
      MetaException, NoSuchObjectException {
    boolean commit = false;
    openTransaction();
    try {
      for (String partName : partNames) {
        dropPartition(dbName, tblName, partNameToVals(partName));
      }
      commit = true;
    } catch (Exception e) {
      LOG.error("Unable to drop partitions", e);
      throw new NoSuchObjectException("Failure dropping partitions, " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalDBGrantsAll(String principalName,
                                                            PrincipalType principalType) {
    List<HiveObjectPrivilege> privileges = new ArrayList<HiveObjectPrivilege>();
    boolean commit = false;
    openTransaction();
    try {
      List<Database> dbs = getHBase().scanDatabases(null);
      for (Database db : dbs) {
        List<PrivilegeGrantInfo> grants;

        PrincipalPrivilegeSet pps = db.getPrivileges();
        if (pps == null) continue;
        Map<String, List<PrivilegeGrantInfo>> map;
        switch (principalType) {
          case USER:
            map = pps.getUserPrivileges();
            break;

          case ROLE:
            map = pps.getRolePrivileges();
            break;

          default:
            throw new RuntimeException("Unknown or unsupported principal type " +
                principalType.toString());
        }

        if (map == null) continue;
        grants = map.get(principalName);
        if (grants == null || grants.size() == 0) continue;
        for (PrivilegeGrantInfo pgi : grants) {
          privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.DATABASE,
              db.getName(), null, null, null), principalName, principalType, pgi));
        }
      }
      commit = true;
      return privileges;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalTableGrantsAll(String principalName,
                                                               PrincipalType principalType) {
    List<HiveObjectPrivilege> privileges = new ArrayList<HiveObjectPrivilege>();
    boolean commit = false;
    openTransaction();
    try {
      List<Table> tables = getHBase().scanTables(null, null);
      for (Table table : tables) {
        List<PrivilegeGrantInfo> grants;

        PrincipalPrivilegeSet pps = table.getPrivileges();
        if (pps == null) continue;
        Map<String, List<PrivilegeGrantInfo>> map;
        switch (principalType) {
          case USER:
            map = pps.getUserPrivileges();
            break;

          case ROLE:
            map = pps.getRolePrivileges();
            break;

          default:
            throw new RuntimeException("Unknown or unsupported principal type " +
                principalType.toString());
        }

        if (map == null) continue;
        grants = map.get(principalName);
        if (grants == null || grants.size() == 0) continue;
        for (PrivilegeGrantInfo pgi : grants) {
          privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.TABLE,
              table.getDbName(), table.getTableName(), null, null), principalName, principalType,
              pgi));
        }
      }
      commit = true;
      return privileges;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalPartitionGrantsAll(String principalName,
                                                                   PrincipalType principalType) {
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalTableColumnGrantsAll(String principalName,
                                                                     PrincipalType principalType) {
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public List<HiveObjectPrivilege> listPrincipalPartitionColumnGrantsAll(String principalName,
                                                                         PrincipalType principalType) {
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public List<HiveObjectPrivilege> listGlobalGrantsAll() {
    List<HiveObjectPrivilege> privileges = new ArrayList<HiveObjectPrivilege>();
    boolean commit = false;
    openTransaction();
    try {
      PrincipalPrivilegeSet pps = getHBase().getGlobalPrivs();
      if (pps != null) {
        for (Map.Entry<String, List<PrivilegeGrantInfo>> e : pps.getUserPrivileges().entrySet()) {
          for (PrivilegeGrantInfo pgi : e.getValue()) {
            privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.GLOBAL, null,
                null, null, null), e.getKey(), PrincipalType.USER, pgi));
          }
        }
        for (Map.Entry<String, List<PrivilegeGrantInfo>> e : pps.getRolePrivileges().entrySet()) {
          for (PrivilegeGrantInfo pgi : e.getValue()) {
            privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.GLOBAL, null,
                null, null, null), e.getKey(), PrincipalType.ROLE, pgi));
          }
        }
      }
      commit = true;
      return privileges;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listDBGrantsAll(String dbName) {
    List<HiveObjectPrivilege> privileges = new ArrayList<HiveObjectPrivilege>();
    boolean commit = false;
    openTransaction();
    try {
      Database db = getHBase().getDb(dbName);
      PrincipalPrivilegeSet pps = db.getPrivileges();
      if (pps != null) {
        for (Map.Entry<String, List<PrivilegeGrantInfo>> e : pps.getUserPrivileges().entrySet()) {
          for (PrivilegeGrantInfo pgi : e.getValue()) {
            privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.DATABASE, dbName,
                null, null, null), e.getKey(), PrincipalType.USER, pgi));
          }
        }
        for (Map.Entry<String, List<PrivilegeGrantInfo>> e : pps.getRolePrivileges().entrySet()) {
          for (PrivilegeGrantInfo pgi : e.getValue()) {
            privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.DATABASE, dbName,
                null, null, null), e.getKey(), PrincipalType.ROLE, pgi));
          }
        }
      }
      commit = true;
      return privileges;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listPartitionColumnGrantsAll(String dbName, String tableName,
                                                                String partitionName,
                                                                String columnName) {
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public List<HiveObjectPrivilege> listTableGrantsAll(String dbName, String tableName) {
    List<HiveObjectPrivilege> privileges = new ArrayList<HiveObjectPrivilege>();
    boolean commit = false;
    openTransaction();
    try {
      Table table = getHBase().getTable(dbName, tableName);
      PrincipalPrivilegeSet pps = table.getPrivileges();
      if (pps != null) {
        for (Map.Entry<String, List<PrivilegeGrantInfo>> e : pps.getUserPrivileges().entrySet()) {
          for (PrivilegeGrantInfo pgi : e.getValue()) {
            privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.TABLE, dbName,
                tableName, null, null), e.getKey(), PrincipalType.USER, pgi));
          }
        }
        for (Map.Entry<String, List<PrivilegeGrantInfo>> e : pps.getRolePrivileges().entrySet()) {
          for (PrivilegeGrantInfo pgi : e.getValue()) {
            privileges.add(new HiveObjectPrivilege(new HiveObjectRef(HiveObjectType.TABLE, dbName,
                tableName, null, null), e.getKey(), PrincipalType.ROLE, pgi));
          }
        }
      }
      commit = true;
      return privileges;
    } catch (IOException e) {
      throw new RuntimeException(e);
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<HiveObjectPrivilege> listPartitionGrantsAll(String dbName, String tableName,
                                                          String partitionName) {
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public List<HiveObjectPrivilege> listTableColumnGrantsAll(String dbName, String tableName,
                                                            String columnName) {
    return new ArrayList<HiveObjectPrivilege>();
  }

  @Override
  public void createFunction(Function func) throws InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().putFunction(func);
      commit = true;
    } catch (IOException e) {
      LOG.error("Unable to create function", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public void alterFunction(String dbName, String funcName, Function newFunction) throws
      InvalidObjectException, MetaException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().putFunction(newFunction);
      commit = true;
    } catch (IOException e) {
      LOG.error("Unable to alter function ", e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public void dropFunction(String dbName, String funcName) throws MetaException,
      NoSuchObjectException, InvalidObjectException, InvalidInputException {
    boolean commit = false;
    openTransaction();
    try {
      getHBase().deleteFunction(dbName, funcName);
      commit = true;
    } catch (IOException e) {
      LOG.error("Unable to delete function" + e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public Function getFunction(String dbName, String funcName) throws MetaException {
    boolean commit = false;
    openTransaction();
    try {
      Function func = getHBase().getFunction(dbName, funcName);
      commit = true;
      return func;
    } catch (IOException e) {
      LOG.error("Unable to get function" + e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public List<String> getFunctions(String dbName, String pattern) throws MetaException {
    boolean commit = false;
    openTransaction();
    try {
      List<Function> funcs = getHBase().scanFunctions(dbName, likeToRegex(pattern));
      List<String> funcNames = new ArrayList<String>(funcs.size());
      for (Function func : funcs) funcNames.add(func.getFunctionName());
      commit = true;
      return funcNames;
    } catch (IOException e) {
      LOG.error("Unable to get functions" + e);
      throw new MetaException("Unable to read from or write to hbase " + e.getMessage());
    } finally {
      commitOrRoleBack(commit);
    }
  }

  @Override
  public NotificationEventResponse getNextNotification(NotificationEventRequest rqst) {
    throw new UnsupportedOperationException();
  }

  @Override
  public void addNotificationEvent(NotificationEvent event) {
    throw new UnsupportedOperationException();
  }

  @Override
  public void cleanNotificationEvents(int olderThan) {
    throw new UnsupportedOperationException();
  }

  @Override
  public CurrentNotificationEventId getCurrentNotificationEventId() {
    throw new UnsupportedOperationException();
  }

  @Override
  public void flushCache() {
    getHBase().flushCatalogCache();
  }

  @Override
  public void setConf(Configuration configuration) {
    // initialize expressionProxy. Also re-initialize it if
    // setConf is being called with new configuration object (though that
    // is not expected to happen, doing it just for safety)
    if(expressionProxy == null || conf != configuration) {
      expressionProxy = PartFilterExprUtil.createExpressionProxy(configuration);
    }
    conf = configuration;
  }

  @Override
  public Configuration getConf() {
    return conf;

  }

  private HBaseReadWrite getHBase() {
    if (hbase == null) hbase = HBaseReadWrite.getInstance(conf);
    return hbase;
  }

  // This is for building error messages only.  It does not look up anything in the metastore.
  private String tableNameForErrorMsg(String dbName, String tableName) {
    return dbName + "." + tableName;
  }

  // This is for building error messages only.  It does not look up anything in the metastore as
  // they may just throw another error.
  private String partNameForErrorMsg(String dbName, String tableName, List<String> partVals) {
    return tableNameForErrorMsg(dbName, tableName) + "." + StringUtils.join(partVals, ':');
  }

  private String buildExternalPartName(Table table, Partition part) {
    return buildExternalPartName(table, part.getValues());
  }

  private String buildExternalPartName(String dbName, String tableName, List<String> partVals)
      throws MetaException {
    return buildExternalPartName(getTable(dbName, tableName), partVals);
  }

  private Set<String> findUsersToRemapRolesFor(Role role, String principalName, PrincipalType type)
      throws IOException, NoSuchObjectException {
    Set<String> usersToRemap;
    switch (type) {
      case USER:
        // In this case it's just the user being added to the role that we need to remap for.
        usersToRemap = new HashSet<String>();
        usersToRemap.add(principalName);
        break;

      case ROLE:
        // In this case we need to remap for all users in the containing role (not the role being
        // granted into the containing role).
        usersToRemap = getHBase().findAllUsersInRole(role.getRoleName());
        break;

      default:
        throw new RuntimeException("Unknown principal type " + type);

    }
    return usersToRemap;
  }

  /**
   * Build a partition name for external use.  Necessary since HBase itself doesn't store
   * partition names.
   * @param table  table object
   * @param partVals partition values.
   * @return
   */
  static String buildExternalPartName(Table table, List<String> partVals) {
    List<String> partCols = new ArrayList<String>();
    for (FieldSchema pc : table.getPartitionKeys()) partCols.add(pc.getName());
    return FileUtils.makePartName(partCols, partVals);
  }

  private List<String> partNameToVals(String name) {
    if (name == null) return null;
    List<String> vals = new ArrayList<String>();
    String[] kvp = name.split("/");
    for (String kv : kvp) {
      vals.add(kv.substring(kv.indexOf('=') + 1));
    }
    return vals;
  }

  private String likeToRegex(String like) {
    if (like == null) return null;
    // Convert Hive's strange like syntax to Java regex.  Per
    // https://cwiki.apache.org/confluence/display/Hive/LanguageManual+DDL#LanguageManualDDL-Show
    // the supported syntax is that * means Java .* and | means 'or'
    // This implementation leaves other regular expression syntax alone, which means people can
    // use it, even though it wouldn't work on RDBMS backed metastores.
    return like.replace("*", ".*");
  }

  private void commitOrRoleBack(boolean commit) {
    if (commit) {
      LOG.debug("Committing transaction");
      commitTransaction();
    } else {
      LOG.debug("Rolling back transaction");
      rollbackTransaction();
    }
  }
}


File: metastore/src/java/org/apache/hadoop/hive/metastore/hbase/HBaseUtils.java
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
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.hadoop.hive.metastore.hbase;

import com.google.protobuf.ByteString;
import com.google.protobuf.InvalidProtocolBufferException;
import org.apache.commons.lang.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hive.metastore.api.BinaryColumnStatsData;
import org.apache.hadoop.hive.metastore.api.BooleanColumnStatsData;
import org.apache.hadoop.hive.metastore.api.ColumnStatistics;
import org.apache.hadoop.hive.metastore.api.ColumnStatisticsData;
import org.apache.hadoop.hive.metastore.api.ColumnStatisticsData._Fields;
import org.apache.hadoop.hive.metastore.api.ColumnStatisticsObj;
import org.apache.hadoop.hive.metastore.api.Database;
import org.apache.hadoop.hive.metastore.api.Decimal;
import org.apache.hadoop.hive.metastore.api.DecimalColumnStatsData;
import org.apache.hadoop.hive.metastore.api.DoubleColumnStatsData;
import org.apache.hadoop.hive.metastore.api.FieldSchema;
import org.apache.hadoop.hive.metastore.api.Function;
import org.apache.hadoop.hive.metastore.api.FunctionType;
import org.apache.hadoop.hive.metastore.api.LongColumnStatsData;
import org.apache.hadoop.hive.metastore.api.Order;
import org.apache.hadoop.hive.metastore.api.Partition;
import org.apache.hadoop.hive.metastore.api.PrincipalPrivilegeSet;
import org.apache.hadoop.hive.metastore.api.PrincipalType;
import org.apache.hadoop.hive.metastore.api.PrivilegeGrantInfo;
import org.apache.hadoop.hive.metastore.api.ResourceType;
import org.apache.hadoop.hive.metastore.api.ResourceUri;
import org.apache.hadoop.hive.metastore.api.Role;
import org.apache.hadoop.hive.metastore.api.SerDeInfo;
import org.apache.hadoop.hive.metastore.api.SkewedInfo;
import org.apache.hadoop.hive.metastore.api.StorageDescriptor;
import org.apache.hadoop.hive.metastore.api.StringColumnStatsData;
import org.apache.hadoop.hive.metastore.api.Table;
import org.apache.thrift.TFieldIdEnum;

import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SortedMap;
import java.util.SortedSet;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Utility functions
 */
class HBaseUtils {

  final static Charset ENCODING = StandardCharsets.UTF_8;
  final static char KEY_SEPARATOR = '\u0001';
  final static String KEY_SEPARATOR_STR = new String(new char[] {KEY_SEPARATOR});

  static final private Log LOG = LogFactory.getLog(HBaseUtils.class.getName());

  /**
   * Build a key for an object in hbase
   * @param components
   * @return
   */
  static byte[] buildKey(String... components) {
    return buildKey(false, components);
  }

  static byte[] buildKeyWithTrailingSeparator(String... components) {
    return buildKey(true, components);
  }

  private static byte[] buildKey(boolean trailingSeparator, String... components) {
    String protoKey = StringUtils.join(components, KEY_SEPARATOR);
    if (trailingSeparator) protoKey += KEY_SEPARATOR;
    return protoKey.getBytes(ENCODING);
  }

  private static HbaseMetastoreProto.Parameters buildParameters(Map<String, String> params) {
    List<HbaseMetastoreProto.ParameterEntry> entries =
        new ArrayList<HbaseMetastoreProto.ParameterEntry>();
    for (Map.Entry<String, String> e : params.entrySet()) {
      entries.add(
          HbaseMetastoreProto.ParameterEntry.newBuilder()
              .setKey(e.getKey())
              .setValue(e.getValue())
              .build());
    }
    return HbaseMetastoreProto.Parameters.newBuilder()
        .addAllParameter(entries)
        .build();
  }

  private static Map<String, String> buildParameters(HbaseMetastoreProto.Parameters protoParams) {
    Map<String, String> params = new HashMap<String, String>();
    for (HbaseMetastoreProto.ParameterEntry pe : protoParams.getParameterList()) {
      params.put(pe.getKey(), pe.getValue());
    }
    return params;
  }


  private static List<HbaseMetastoreProto.PrincipalPrivilegeSetEntry>
  buildPrincipalPrivilegeSetEntry(Map<String, List<PrivilegeGrantInfo>> entries) {
    List<HbaseMetastoreProto.PrincipalPrivilegeSetEntry> results =
        new ArrayList<HbaseMetastoreProto.PrincipalPrivilegeSetEntry>();
    for (Map.Entry<String, List<PrivilegeGrantInfo>> entry : entries.entrySet()) {
      results.add(HbaseMetastoreProto.PrincipalPrivilegeSetEntry.newBuilder()
          .setPrincipalName(entry.getKey())
          .addAllPrivileges(buildPrivilegeGrantInfo(entry.getValue()))
          .build());
    }
    return results;
  }

  private static List<HbaseMetastoreProto.PrivilegeGrantInfo> buildPrivilegeGrantInfo(
      List<PrivilegeGrantInfo> privileges) {
    List<HbaseMetastoreProto.PrivilegeGrantInfo> results =
        new ArrayList<HbaseMetastoreProto.PrivilegeGrantInfo>();
    for (PrivilegeGrantInfo privilege : privileges) {
      HbaseMetastoreProto.PrivilegeGrantInfo.Builder builder =
          HbaseMetastoreProto.PrivilegeGrantInfo.newBuilder();
      if (privilege.getPrivilege() != null) builder.setPrivilege(privilege.getPrivilege());
      builder.setCreateTime(privilege.getCreateTime());
      if (privilege.getGrantor() != null) builder.setGrantor(privilege.getGrantor());
      if (privilege.getGrantorType() != null) {
        builder.setGrantorType(convertPrincipalTypes(privilege.getGrantorType()));
      }
      builder.setGrantOption(privilege.isGrantOption());
      results.add(builder.build());
    }
    return results;
  }

  /**
   * Convert Thrift.PrincipalType to HbaseMetastoreProto.principalType
   * @param type
   * @return
   */
  static HbaseMetastoreProto.PrincipalType convertPrincipalTypes(PrincipalType type) {
    switch (type) {
      case USER: return HbaseMetastoreProto.PrincipalType.USER;
      case ROLE: return HbaseMetastoreProto.PrincipalType.ROLE;
      default: throw new RuntimeException("Unknown principal type " + type.toString());
    }
  }

  /**
   * Convert principalType from HbaseMetastoreProto to Thrift.PrincipalType
   * @param type
   * @return
   */
  static PrincipalType convertPrincipalTypes(HbaseMetastoreProto.PrincipalType type) {
    switch (type) {
      case USER: return PrincipalType.USER;
      case ROLE: return PrincipalType.ROLE;
      default: throw new RuntimeException("Unknown principal type " + type.toString());
    }
  }

  private static Map<String, List<PrivilegeGrantInfo>> convertPrincipalPrivilegeSetEntries(
      List<HbaseMetastoreProto.PrincipalPrivilegeSetEntry> entries) {
    Map<String, List<PrivilegeGrantInfo>> map =
        new HashMap<String, List<PrivilegeGrantInfo>>();
    for (HbaseMetastoreProto.PrincipalPrivilegeSetEntry entry : entries) {
      map.put(entry.getPrincipalName(), convertPrivilegeGrantInfos(entry.getPrivilegesList()));
    }
    return map;
  }

  private static List<PrivilegeGrantInfo> convertPrivilegeGrantInfos(
      List<HbaseMetastoreProto.PrivilegeGrantInfo> privileges) {
    List<PrivilegeGrantInfo> results = new ArrayList<PrivilegeGrantInfo>();
    for (HbaseMetastoreProto.PrivilegeGrantInfo proto : privileges) {
      PrivilegeGrantInfo pgi = new PrivilegeGrantInfo();
      if (proto.hasPrivilege()) pgi.setPrivilege(proto.getPrivilege());
      pgi.setCreateTime((int)proto.getCreateTime());
      if (proto.hasGrantor()) pgi.setGrantor(proto.getGrantor());
      if (proto.hasGrantorType()) {
        pgi.setGrantorType(convertPrincipalTypes(proto.getGrantorType()));
      }
      if (proto.hasGrantOption()) pgi.setGrantOption(proto.getGrantOption());
      results.add(pgi);
    }
    return results;
  }

  private static HbaseMetastoreProto.PrincipalPrivilegeSet
  buildPrincipalPrivilegeSet(PrincipalPrivilegeSet pps) {
    HbaseMetastoreProto.PrincipalPrivilegeSet.Builder builder =
        HbaseMetastoreProto.PrincipalPrivilegeSet.newBuilder();
    if (pps.getUserPrivileges() != null) {
      builder.addAllUsers(buildPrincipalPrivilegeSetEntry(pps.getUserPrivileges()));
    }
    if (pps.getRolePrivileges() != null) {
      builder.addAllRoles(buildPrincipalPrivilegeSetEntry(pps.getRolePrivileges()));
    }
    return builder.build();
  }

  private static PrincipalPrivilegeSet buildPrincipalPrivilegeSet(
      HbaseMetastoreProto.PrincipalPrivilegeSet proto) throws InvalidProtocolBufferException {
    PrincipalPrivilegeSet pps = new PrincipalPrivilegeSet();
    pps.setUserPrivileges(convertPrincipalPrivilegeSetEntries(proto.getUsersList()));
    pps.setRolePrivileges(convertPrincipalPrivilegeSetEntries(proto.getRolesList()));
    return pps;
  }
  /**
   * Serialize a PrincipalPrivilegeSet
   * @param pps
   * @return
   */
  static byte[] serializePrincipalPrivilegeSet(PrincipalPrivilegeSet pps) {
    return buildPrincipalPrivilegeSet(pps).toByteArray();
  }

  /**
   * Deserialize a PrincipalPrivilegeSet
   * @param serialized
   * @return
   * @throws InvalidProtocolBufferException
   */
  static PrincipalPrivilegeSet deserializePrincipalPrivilegeSet(byte[] serialized)
      throws InvalidProtocolBufferException {
    HbaseMetastoreProto.PrincipalPrivilegeSet proto =
        HbaseMetastoreProto.PrincipalPrivilegeSet.parseFrom(serialized);
    return buildPrincipalPrivilegeSet(proto);
  }

  /**
   * Serialize a role
   * @param role
   * @return two byte arrays, first contains the key, the second the serialized value.
   */
  static byte[][] serializeRole(Role role) {
    byte[][] result = new byte[2][];
    result[0] = buildKey(role.getRoleName());
    HbaseMetastoreProto.Role.Builder builder = HbaseMetastoreProto.Role.newBuilder();
    builder.setCreateTime(role.getCreateTime());
    if (role.getOwnerName() != null) builder.setOwnerName(role.getOwnerName());
    result[1] = builder.build().toByteArray();
    return result;
  }

  /**
   * Deserialize a role.  This method should be used when the rolename is already known as it
   * doesn't have to re-deserialize it.
   * @param roleName name of the role
   * @param value value fetched from hbase
   * @return A role
   * @throws InvalidProtocolBufferException
   */
  static Role deserializeRole(String roleName, byte[] value)
      throws InvalidProtocolBufferException {
    Role role = new Role();
    role.setRoleName(roleName);
    HbaseMetastoreProto.Role protoRole =
        HbaseMetastoreProto.Role.parseFrom(value);
    role.setCreateTime((int)protoRole.getCreateTime());
    if (protoRole.hasOwnerName()) role.setOwnerName(protoRole.getOwnerName());
    return role;
  }

  /**
   * Deserialize a role.  This method should be used when the rolename is not already known (eg
   * when doing a scan).
   * @param key key from hbase
   * @param value value from hbase
   * @return a role
   * @throws InvalidProtocolBufferException
   */
  static Role deserializeRole(byte[] key, byte[] value)
      throws InvalidProtocolBufferException {
    String roleName = new String(key, ENCODING);
    return deserializeRole(roleName, value);
  }

  /**
   * Serialize a list of role names
   * @param roles
   * @return
   */
  static byte[] serializeRoleList(List<String> roles) {
    return HbaseMetastoreProto.RoleList.newBuilder()
        .addAllRole(roles)
        .build()
        .toByteArray();
  }

  static List<String> deserializeRoleList(byte[] value) throws InvalidProtocolBufferException {
    HbaseMetastoreProto.RoleList proto = HbaseMetastoreProto.RoleList.parseFrom(value);
    return new ArrayList<String>(proto.getRoleList());
  }

  /**
   * Serialize a database
   * @param db
   * @return two byte arrays, first contains the key, the second the serialized value.
   */
  static byte[][] serializeDatabase(Database db) {
    byte[][] result = new byte[2][];
    result[0] = buildKey(db.getName());
    HbaseMetastoreProto.Database.Builder builder = HbaseMetastoreProto.Database.newBuilder();

    if (db.getDescription() != null) builder.setDescription(db.getDescription());
    if (db.getLocationUri() != null) builder.setUri(db.getLocationUri());
    if (db.getParameters() != null) builder.setParameters(buildParameters(db.getParameters()));
    if (db.getPrivileges() != null) {
      builder.setPrivileges(buildPrincipalPrivilegeSet(db.getPrivileges()));
    }
    if (db.getOwnerName() != null) builder.setOwnerName(db.getOwnerName());
    if (db.getOwnerType() != null) builder.setOwnerType(convertPrincipalTypes(db.getOwnerType()));

    result[1] = builder.build().toByteArray();
    return result;
  }

  /**
   * Deserialize a database.  This method should be used when the db anme is already known as it
   * doesn't have to re-deserialize it.
   * @param dbName name of the role
   * @param value value fetched from hbase
   * @return A database
   * @throws InvalidProtocolBufferException
   */
  static Database deserializeDatabase(String dbName, byte[] value)
      throws InvalidProtocolBufferException {
    Database db = new Database();
    db.setName(dbName);
    HbaseMetastoreProto.Database protoDb = HbaseMetastoreProto.Database.parseFrom(value);
    if (protoDb.hasDescription()) db.setDescription(protoDb.getDescription());
    if (protoDb.hasUri()) db.setLocationUri(protoDb.getUri());
    if (protoDb.hasParameters()) db.setParameters(buildParameters(protoDb.getParameters()));
    if (protoDb.hasPrivileges()) {
      db.setPrivileges(buildPrincipalPrivilegeSet(protoDb.getPrivileges()));
    }
    if (protoDb.hasOwnerName()) db.setOwnerName(protoDb.getOwnerName());
    if (protoDb.hasOwnerType()) db.setOwnerType(convertPrincipalTypes(protoDb.getOwnerType()));

    return db;
  }

  /**
   * Deserialize a database.  This method should be used when the db name is not already known (eg
   * when doing a scan).
   * @param key key from hbase
   * @param value value from hbase
   * @return a role
   * @throws InvalidProtocolBufferException
   */
  static Database deserializeDatabase(byte[] key, byte[] value)
      throws InvalidProtocolBufferException {
    String dbName = new String(key, ENCODING);
    return deserializeDatabase(dbName, value);
  }

  /**
   * Serialize a function
   * @param func function to serialize
   * @return two byte arrays, first contains the key, the second the value.
   */
  static byte[][] serializeFunction(Function func) {
    byte[][] result = new byte[2][];
    result[0] = buildKey(func.getDbName(), func.getFunctionName());
    HbaseMetastoreProto.Function.Builder builder = HbaseMetastoreProto.Function.newBuilder();
    if (func.getClassName() != null) builder.setClassName(func.getClassName());
    if (func.getOwnerName() != null) builder.setOwnerName(func.getOwnerName());
    if (func.getOwnerType() != null) {
      builder.setOwnerType(convertPrincipalTypes(func.getOwnerType()));
    }
    builder.setCreateTime(func.getCreateTime());
    if (func.getFunctionType() != null) {
      builder.setFunctionType(convertFunctionTypes(func.getFunctionType()));
    }
    if (func.getResourceUris() != null) {
      for (ResourceUri uri : func.getResourceUris()) {
        builder.addResourceUris(HbaseMetastoreProto.Function.ResourceUri.newBuilder()
            .setResourceType(convertResourceTypes(uri.getResourceType()))
            .setUri(uri.getUri()));
      }
    }
    result[1] = builder.build().toByteArray();
    return result;
  }

  /**
   * Deserialize a function.  This method should be used when the function and db name are
   * already known.
   * @param dbName name of the database the function is in
   * @param functionName name of the function
   * @param value serialized value of the function
   * @return function as an object
   * @throws InvalidProtocolBufferException
   */
  static Function deserializeFunction(String dbName, String functionName, byte[] value)
      throws InvalidProtocolBufferException {
    Function func = new Function();
    func.setDbName(dbName);
    func.setFunctionName(functionName);
    HbaseMetastoreProto.Function protoFunc = HbaseMetastoreProto.Function.parseFrom(value);
    if (protoFunc.hasClassName()) func.setClassName(protoFunc.getClassName());
    if (protoFunc.hasOwnerName()) func.setOwnerName(protoFunc.getOwnerName());
    if (protoFunc.hasOwnerType()) {
      func.setOwnerType(convertPrincipalTypes(protoFunc.getOwnerType()));
    }
    func.setCreateTime((int)protoFunc.getCreateTime());
    if (protoFunc.hasFunctionType()) {
      func.setFunctionType(convertFunctionTypes(protoFunc.getFunctionType()));
    }
    for (HbaseMetastoreProto.Function.ResourceUri protoUri : protoFunc.getResourceUrisList()) {
      func.addToResourceUris(new ResourceUri(convertResourceTypes(protoUri.getResourceType()),
                                             protoUri.getUri()));
    }
    return func;
  }

  /**
   * Deserialize a function.  This method should be used when the dbname and function name are
   * not already known, such as in a scan.
   * @param key key from hbase
   * @param value value from hbase
   * @return function object
   * @throws InvalidProtocolBufferException
   */
  static Function deserializeFunction(byte[] key, byte[] value)
      throws  InvalidProtocolBufferException {
    String[] keys = deserializeKey(key);
    return deserializeFunction(keys[0], keys[1], value);
  }

  private static HbaseMetastoreProto.Function.FunctionType convertFunctionTypes(FunctionType type) {
    switch (type) {
    case JAVA: return HbaseMetastoreProto.Function.FunctionType.JAVA;
    default: throw new RuntimeException("Unknown function type " + type.toString());
    }
  }

  private static FunctionType convertFunctionTypes(HbaseMetastoreProto.Function.FunctionType type) {
    switch (type) {
    case JAVA: return FunctionType.JAVA;
    default: throw new RuntimeException("Unknown function type " + type.toString());
    }
  }

  private static HbaseMetastoreProto.Function.ResourceUri.ResourceType
  convertResourceTypes(ResourceType type) {
    switch (type) {
    case JAR: return HbaseMetastoreProto.Function.ResourceUri.ResourceType.JAR;
    case FILE: return HbaseMetastoreProto.Function.ResourceUri.ResourceType.FILE;
    case ARCHIVE: return HbaseMetastoreProto.Function.ResourceUri.ResourceType.ARCHIVE;
    default: throw new RuntimeException("Unknown resource type " + type.toString());
    }
  }

  private static ResourceType convertResourceTypes(
      HbaseMetastoreProto.Function.ResourceUri.ResourceType type) {
    switch (type) {
    case JAR: return ResourceType.JAR;
    case FILE: return ResourceType.FILE;
    case ARCHIVE: return ResourceType.ARCHIVE;
    default: throw new RuntimeException("Unknown resource type " + type.toString());
    }
  }

  private static List<FieldSchema>
  convertFieldSchemaListFromProto(List<HbaseMetastoreProto.FieldSchema> protoList) {
    List<FieldSchema> schemas = new ArrayList<FieldSchema>(protoList.size());
    for (HbaseMetastoreProto.FieldSchema proto : protoList) {
      schemas.add(new FieldSchema(proto.getName(), proto.getType(),
          proto.hasComment() ? proto.getComment() : null));
    }
    return schemas;
  }

  private static List<HbaseMetastoreProto.FieldSchema>
  convertFieldSchemaListToProto(List<FieldSchema> schemas) {
    List<HbaseMetastoreProto.FieldSchema> protoList =
        new ArrayList<HbaseMetastoreProto.FieldSchema>(schemas.size());
    for (FieldSchema fs : schemas) {
      HbaseMetastoreProto.FieldSchema.Builder builder =
          HbaseMetastoreProto.FieldSchema.newBuilder();
      builder
          .setName(fs.getName())
          .setType(fs.getType());
      if (fs.getComment() != null) builder.setComment(fs.getComment());
      protoList.add(builder.build());
    }
    return protoList;
  }

  /**
   * Serialize a storage descriptor.
   * @param sd storage descriptor to serialize
   * @return serialized storage descriptor.
   */
  static byte[] serializeStorageDescriptor(StorageDescriptor sd)  {
    HbaseMetastoreProto.StorageDescriptor.Builder builder =
        HbaseMetastoreProto.StorageDescriptor.newBuilder();
    builder.addAllCols(convertFieldSchemaListToProto(sd.getCols()));
    if (sd.getInputFormat() != null) {
      builder.setInputFormat(sd.getInputFormat());
    }
    if (sd.getOutputFormat() != null) {
      builder.setOutputFormat(sd.getOutputFormat());
    }
    builder.setIsCompressed(sd.isCompressed());
    builder.setNumBuckets(sd.getNumBuckets());
    if (sd.getSerdeInfo() != null) {
      HbaseMetastoreProto.StorageDescriptor.SerDeInfo.Builder serdeBuilder =
          HbaseMetastoreProto.StorageDescriptor.SerDeInfo.newBuilder();
      SerDeInfo serde = sd.getSerdeInfo();
      if (serde.getName() != null) {
        serdeBuilder.setName(serde.getName());
      }
      if (serde.getSerializationLib() != null) {
        serdeBuilder.setSerializationLib(serde.getSerializationLib());
      }
      if (serde.getParameters() != null) {
        serdeBuilder.setParameters(buildParameters(serde.getParameters()));
      }
      builder.setSerdeInfo(serdeBuilder);
    }
    if (sd.getBucketCols() != null) {
      builder.addAllBucketCols(sd.getBucketCols());
    }
    if (sd.getSortCols() != null) {
      List<Order> orders = sd.getSortCols();
      List<HbaseMetastoreProto.StorageDescriptor.Order> protoList =
          new ArrayList<HbaseMetastoreProto.StorageDescriptor.Order>(orders.size());
      for (Order order : orders) {
        protoList.add(HbaseMetastoreProto.StorageDescriptor.Order.newBuilder()
            .setColumnName(order.getCol())
            .setOrder(order.getOrder())
            .build());
      }
      builder.addAllSortCols(protoList);
    }
    if (sd.getSkewedInfo() != null) {
      HbaseMetastoreProto.StorageDescriptor.SkewedInfo.Builder skewBuilder =
          HbaseMetastoreProto.StorageDescriptor.SkewedInfo.newBuilder();
      SkewedInfo skewed = sd.getSkewedInfo();
      if (skewed.getSkewedColNames() != null) {
        skewBuilder.addAllSkewedColNames(skewed.getSkewedColNames());
      }
      if (skewed.getSkewedColValues() != null) {
        for (List<String> innerList : skewed.getSkewedColValues()) {
          HbaseMetastoreProto.StorageDescriptor.SkewedInfo.SkewedColValueList.Builder listBuilder =
              HbaseMetastoreProto.StorageDescriptor.SkewedInfo.SkewedColValueList.newBuilder();
          listBuilder.addAllSkewedColValue(innerList);
          skewBuilder.addSkewedColValues(listBuilder);
        }
      }
      if (skewed.getSkewedColValueLocationMaps() != null) {
        for (Map.Entry<List<String>, String> e : skewed.getSkewedColValueLocationMaps().entrySet()) {
          HbaseMetastoreProto.StorageDescriptor.SkewedInfo.SkewedColValueLocationMap.Builder mapBuilder =
              HbaseMetastoreProto.StorageDescriptor.SkewedInfo.SkewedColValueLocationMap.newBuilder();
          mapBuilder.addAllKey(e.getKey());
          mapBuilder.setValue(e.getValue());
          skewBuilder.addSkewedColValueLocationMaps(mapBuilder);
        }
      }
      builder.setSkewedInfo(skewBuilder);
    }
    builder.setStoredAsSubDirectories(sd.isStoredAsSubDirectories());

    return builder.build().toByteArray();
  }

  /**
   * Produce a hash for the storage descriptor
   * @param sd storage descriptor to hash
   * @param md message descriptor to use to generate the hash
   * @return the hash as a byte array
   */
  static byte[] hashStorageDescriptor(StorageDescriptor sd, MessageDigest md)  {
    // Note all maps and lists have to be absolutely sorted.  Otherwise we'll produce different
    // results for hashes based on the OS or JVM being used.
    md.reset();
    for (FieldSchema fs : sd.getCols()) {
      md.update(fs.getName().getBytes(ENCODING));
      md.update(fs.getType().getBytes(ENCODING));
      if (fs.getComment() != null) md.update(fs.getComment().getBytes(ENCODING));
    }
    if (sd.getInputFormat() != null) {
      md.update(sd.getInputFormat().getBytes(ENCODING));
    }
    if (sd.getOutputFormat() != null) {
      md.update(sd.getOutputFormat().getBytes(ENCODING));
    }
    md.update(sd.isCompressed() ? "true".getBytes(ENCODING) : "false".getBytes(ENCODING));
    md.update(Integer.toString(sd.getNumBuckets()).getBytes(ENCODING));
    if (sd.getSerdeInfo() != null) {
      SerDeInfo serde = sd.getSerdeInfo();
      if (serde.getName() != null) {
        md.update(serde.getName().getBytes(ENCODING));
      }
      if (serde.getSerializationLib() != null) {
        md.update(serde.getSerializationLib().getBytes(ENCODING));
      }
      if (serde.getParameters() != null) {
        SortedMap<String, String> params = new TreeMap<String, String>(serde.getParameters());
        for (Map.Entry<String, String> param : params.entrySet()) {
          md.update(param.getKey().getBytes(ENCODING));
          md.update(param.getValue().getBytes(ENCODING));
        }
      }
    }
    if (sd.getBucketCols() != null) {
      SortedSet<String> bucketCols = new TreeSet<String>(sd.getBucketCols());
      for (String bucket : bucketCols) md.update(bucket.getBytes(ENCODING));
    }
    if (sd.getSortCols() != null) {
      SortedSet<Order> orders = new TreeSet<Order>(sd.getSortCols());
      for (Order order : orders) {
        md.update(order.getCol().getBytes(ENCODING));
        md.update(Integer.toString(order.getOrder()).getBytes(ENCODING));
      }
    }
    if (sd.getSkewedInfo() != null) {
      SkewedInfo skewed = sd.getSkewedInfo();
      if (skewed.getSkewedColNames() != null) {
        SortedSet<String> colnames = new TreeSet<String>(skewed.getSkewedColNames());
        for (String colname : colnames) md.update(colname.getBytes(ENCODING));
      }
      if (skewed.getSkewedColValues() != null) {
        SortedSet<String> sortedOuterList = new TreeSet<String>();
        for (List<String> innerList : skewed.getSkewedColValues()) {
          SortedSet<String> sortedInnerList = new TreeSet<String>(innerList);
          sortedOuterList.add(StringUtils.join(sortedInnerList, "."));
        }
        for (String colval : sortedOuterList) md.update(colval.getBytes(ENCODING));
      }
      if (skewed.getSkewedColValueLocationMaps() != null) {
        SortedMap<String, String> sortedMap = new TreeMap<String, String>();
        for (Map.Entry<List<String>, String> smap : skewed.getSkewedColValueLocationMaps().entrySet()) {
          SortedSet<String> sortedKey = new TreeSet<String>(smap.getKey());
          sortedMap.put(StringUtils.join(sortedKey, "."), smap.getValue());
        }
        for (Map.Entry<String, String> e : sortedMap.entrySet()) {
          md.update(e.getKey().getBytes(ENCODING));
          md.update(e.getValue().getBytes(ENCODING));
        }
      }
    }

    return md.digest();
  }

  static StorageDescriptor deserializeStorageDescriptor(byte[] serialized)
      throws InvalidProtocolBufferException {
    HbaseMetastoreProto.StorageDescriptor proto =
        HbaseMetastoreProto.StorageDescriptor.parseFrom(serialized);
    StorageDescriptor sd = new StorageDescriptor();
    sd.setCols(convertFieldSchemaListFromProto(proto.getColsList()));
    if (proto.hasInputFormat()) sd.setInputFormat(proto.getInputFormat());
    if (proto.hasOutputFormat()) sd.setOutputFormat(proto.getOutputFormat());
    sd.setCompressed(proto.getIsCompressed());
    sd.setNumBuckets(proto.getNumBuckets());
    if (proto.hasSerdeInfo()) {
      SerDeInfo serde = new SerDeInfo();
      serde.setName(proto.getSerdeInfo().getName());
      serde.setSerializationLib(proto.getSerdeInfo().getSerializationLib());
      serde.setParameters(buildParameters(proto.getSerdeInfo().getParameters()));
      sd.setSerdeInfo(serde);
    }
    sd.setBucketCols(new ArrayList<String>(proto.getBucketColsList()));
    List<Order> sortCols = new ArrayList<Order>();
    for (HbaseMetastoreProto.StorageDescriptor.Order protoOrder : proto.getSortColsList()) {
      sortCols.add(new Order(protoOrder.getColumnName(), protoOrder.getOrder()));
    }
    sd.setSortCols(sortCols);
    if (proto.hasSkewedInfo()) {
      SkewedInfo skewed = new SkewedInfo();
      skewed
          .setSkewedColNames(new ArrayList<String>(proto.getSkewedInfo().getSkewedColNamesList()));
      for (HbaseMetastoreProto.StorageDescriptor.SkewedInfo.SkewedColValueList innerList :
          proto.getSkewedInfo().getSkewedColValuesList()) {
        skewed.addToSkewedColValues(new ArrayList<String>(innerList.getSkewedColValueList()));
      }
      Map<List<String>, String> colMaps = new HashMap<List<String>, String>();
      for (HbaseMetastoreProto.StorageDescriptor.SkewedInfo.SkewedColValueLocationMap map :
          proto.getSkewedInfo().getSkewedColValueLocationMapsList()) {
        colMaps.put(new ArrayList<String>(map.getKeyList()), map.getValue());
      }
      skewed.setSkewedColValueLocationMaps(colMaps);
      sd.setSkewedInfo(skewed);
    }
    if (proto.hasStoredAsSubDirectories()) {
      sd.setStoredAsSubDirectories(proto.getStoredAsSubDirectories());
    }
    return sd;
  }

  /**
   * Serialize a partition
   * @param part partition object
   * @param sdHash hash that is being used as a key for the enclosed storage descriptor
   * @return First element is the key, second is the serialized partition
   */
  static byte[][] serializePartition(Partition part, byte[] sdHash) {
    byte[][] result = new byte[2][];
    result[0] = buildPartitionKey(part.getDbName(), part.getTableName(), part.getValues());
    HbaseMetastoreProto.Partition.Builder builder = HbaseMetastoreProto.Partition.newBuilder();
    builder
        .setCreateTime(part.getCreateTime())
        .setLastAccessTime(part.getLastAccessTime());
    if (part.getSd().getLocation() != null) builder.setLocation(part.getSd().getLocation());
    if (part.getSd().getParameters() != null) {
      builder.setSdParameters(buildParameters(part.getSd().getParameters()));
    }
    builder.setSdHash(ByteString.copyFrom(sdHash));
    if (part.getParameters() != null) builder.setParameters(buildParameters(part.getParameters()));
    result[1] = builder.build().toByteArray();
    return result;
  }

  static byte[] buildPartitionKey(String dbName, String tableName, List<String> partVals) {
    Deque<String> keyParts = new ArrayDeque<String>(partVals);
    keyParts.addFirst(tableName);
    keyParts.addFirst(dbName);
    return buildKey(keyParts.toArray(new String[keyParts.size()]));
  }

  static class StorageDescriptorParts {
    byte[] sdHash;
    String location;
    Map<String, String> parameters;
    Partition containingPartition;
    Table containingTable;
  }

  static void assembleStorageDescriptor(StorageDescriptor sd, StorageDescriptorParts parts) {
    SharedStorageDescriptor ssd = new SharedStorageDescriptor();
    ssd.setLocation(parts.location);
    ssd.setParameters(parts.parameters);
    ssd.setShared(sd);
    if (parts.containingPartition != null) {
      parts.containingPartition.setSd(ssd);
    } else if (parts.containingTable != null) {
      parts.containingTable.setSd(ssd);
    } else {
      throw new RuntimeException("Need either a partition or a table");
    }
  }

  /**
   * Deserialize a partition.  This version should be used when the partition key is not already
   * known (eg a scan).
   * @param key the key fetched from HBase
   * @param serialized the value fetched from HBase
   * @return A struct that contains the partition plus parts of the storage descriptor
   */
  static StorageDescriptorParts deserializePartition(byte[] key, byte[] serialized)
      throws InvalidProtocolBufferException {
    String[] keys = deserializeKey(key);
    return deserializePartition(keys[0], keys[1],
        Arrays.asList(Arrays.copyOfRange(keys, 2, keys.length)), serialized);
  }

  /**
   * Deserialize a partition.  This version should be used when the partition key is
   * known (eg a get).
   * @param dbName database name
   * @param tableName table name
   * @param partVals partition values
   * @param serialized the value fetched from HBase
   * @return A struct that contains the partition plus parts of the storage descriptor
   */
  static StorageDescriptorParts deserializePartition(String dbName, String tableName,
                                                     List<String> partVals, byte[] serialized)
      throws InvalidProtocolBufferException {
    HbaseMetastoreProto.Partition proto = HbaseMetastoreProto.Partition.parseFrom(serialized);
    Partition part = new Partition();
    StorageDescriptorParts sdParts = new StorageDescriptorParts();
    sdParts.containingPartition = part;
    part.setDbName(dbName);
    part.setTableName(tableName);
    part.setValues(partVals);
    part.setCreateTime((int)proto.getCreateTime());
    part.setLastAccessTime((int)proto.getLastAccessTime());
    if (proto.hasLocation()) sdParts.location = proto.getLocation();
    if (proto.hasSdParameters()) sdParts.parameters = buildParameters(proto.getSdParameters());
    sdParts.sdHash = proto.getSdHash().toByteArray();
    if (proto.hasParameters()) part.setParameters(buildParameters(proto.getParameters()));
    return sdParts;
  }

  private static String[] deserializeKey(byte[] key) {
    String k = new String(key, ENCODING);
    return k.split(KEY_SEPARATOR_STR);
  }

  /**
   * Serialize a table
   * @param table table object
   * @param sdHash hash that is being used as a key for the enclosed storage descriptor
   * @return First element is the key, second is the serialized table
   */
  static byte[][] serializeTable(Table table, byte[] sdHash) {
    byte[][] result = new byte[2][];
    result[0] = buildKey(table.getDbName(), table.getTableName());
    HbaseMetastoreProto.Table.Builder builder = HbaseMetastoreProto.Table.newBuilder();
    if (table.getOwner() != null) builder.setOwner(table.getOwner());
    builder
        .setCreateTime(table.getCreateTime())
        .setLastAccessTime(table.getLastAccessTime())
        .setRetention(table.getRetention());
    if (table.getSd().getLocation() != null) builder.setLocation(table.getSd().getLocation());
    if (table.getSd().getParameters() != null) {
      builder.setSdParameters(buildParameters(table.getSd().getParameters()));
    }
    builder.setSdHash(ByteString.copyFrom(sdHash));
    if (table.getPartitionKeys() != null) {
      builder.addAllPartitionKeys(convertFieldSchemaListToProto(table.getPartitionKeys()));
    }
    if (table.getParameters() != null) {
      builder.setParameters(buildParameters(table.getParameters()));
    }
    if (table.getViewOriginalText() != null) {
      builder.setViewOriginalText(table.getViewOriginalText());
    }
    if (table.getViewExpandedText() != null) {
      builder.setViewExpandedText(table.getViewExpandedText());
    }
    if (table.getTableType() != null) builder.setTableType(table.getTableType());
    if (table.getPrivileges() != null) {
      builder.setPrivileges(buildPrincipalPrivilegeSet(table.getPrivileges()));
    }
    builder.setIsTemporary(table.isTemporary());
    result[1] = builder.build().toByteArray();
    return result;
  }

  /**
   * Deserialize a table.  This version should be used when the table key is not already
   * known (eg a scan).
   * @param key the key fetched from HBase
   * @param serialized the value fetched from HBase
   * @return A struct that contains the table plus parts of the storage descriptor
   */
  static StorageDescriptorParts deserializeTable(byte[] key, byte[] serialized)
      throws InvalidProtocolBufferException {
    String[] keys = deserializeKey(key);
    return deserializeTable(keys[0], keys[1], serialized);
  }

  /**
   * Deserialize a table.  This version should be used when the table key is
   * known (eg a get).
   * @param dbName database name
   * @param tableName table name
   * @param serialized the value fetched from HBase
   * @return A struct that contains the partition plus parts of the storage descriptor
   */
  static StorageDescriptorParts deserializeTable(String dbName, String tableName,
                                                 byte[] serialized)
      throws InvalidProtocolBufferException {
    HbaseMetastoreProto.Table proto = HbaseMetastoreProto.Table.parseFrom(serialized);
    Table table = new Table();
    StorageDescriptorParts sdParts = new StorageDescriptorParts();
    sdParts.containingTable = table;
    table.setDbName(dbName);
    table.setTableName(tableName);
    table.setOwner(proto.getOwner());
    table.setCreateTime((int)proto.getCreateTime());
    table.setLastAccessTime((int)proto.getLastAccessTime());
    table.setRetention((int)proto.getRetention());
    if (proto.hasLocation()) sdParts.location = proto.getLocation();
    if (proto.hasSdParameters()) sdParts.parameters = buildParameters(proto.getSdParameters());
    sdParts.sdHash = proto.getSdHash().toByteArray();
    table.setPartitionKeys(convertFieldSchemaListFromProto(proto.getPartitionKeysList()));
    table.setParameters(buildParameters(proto.getParameters()));
    if (proto.hasViewOriginalText()) table.setViewOriginalText(proto.getViewOriginalText());
    if (proto.hasViewExpandedText()) table.setViewExpandedText(proto.getViewExpandedText());
    table.setTableType(proto.getTableType());
    if (proto.hasPrivileges()) {
      table.setPrivileges(buildPrincipalPrivilegeSet(proto.getPrivileges()));
    }
    if (proto.hasIsTemporary()) table.setTemporary(proto.getIsTemporary());
    return sdParts;
  }

  static byte[] serializeStatsForOneColumn(ColumnStatistics partitionColumnStats, ColumnStatisticsObj colStats)
      throws IOException {
    HbaseMetastoreProto.ColumnStats.Builder builder = HbaseMetastoreProto.ColumnStats.newBuilder();
    builder.setLastAnalyzed(partitionColumnStats.getStatsDesc().getLastAnalyzed());
    if (colStats.getColType() == null) {
      throw new RuntimeException("Column type must be set");
    }
    builder.setColumnType(colStats.getColType());
    ColumnStatisticsData colData = colStats.getStatsData();
    switch (colData.getSetField()) {
      case BOOLEAN_STATS:
        BooleanColumnStatsData boolData = colData.getBooleanStats();
        builder.setNumNulls(boolData.getNumNulls());
        builder.setBoolStats(
            HbaseMetastoreProto.ColumnStats.BooleanStats.newBuilder()
                .setNumTrues(boolData.getNumTrues())
                .setNumFalses(boolData.getNumFalses())
                .build());
        break;

      case LONG_STATS:
        LongColumnStatsData longData = colData.getLongStats();
        builder.setNumNulls(longData.getNumNulls());
        builder.setNumDistinctValues(longData.getNumDVs());
        builder.setLongStats(
            HbaseMetastoreProto.ColumnStats.LongStats.newBuilder()
                .setLowValue(longData.getLowValue())
                .setHighValue(longData.getHighValue())
                .build());
        break;

      case DOUBLE_STATS:
        DoubleColumnStatsData doubleData = colData.getDoubleStats();
        builder.setNumNulls(doubleData.getNumNulls());
        builder.setNumDistinctValues(doubleData.getNumDVs());
        builder.setDoubleStats(
            HbaseMetastoreProto.ColumnStats.DoubleStats.newBuilder()
                .setLowValue(doubleData.getLowValue())
                .setHighValue(doubleData.getHighValue())
                .build());
        break;

      case STRING_STATS:
        StringColumnStatsData stringData = colData.getStringStats();
        builder.setNumNulls(stringData.getNumNulls());
        builder.setNumDistinctValues(stringData.getNumDVs());
        builder.setStringStats(
            HbaseMetastoreProto.ColumnStats.StringStats.newBuilder()
                .setMaxColLength(stringData.getMaxColLen())
                .setAvgColLength(stringData.getAvgColLen())
                .build());
        break;

      case BINARY_STATS:
        BinaryColumnStatsData binaryData = colData.getBinaryStats();
        builder.setNumNulls(binaryData.getNumNulls());
        builder.setBinaryStats(
            HbaseMetastoreProto.ColumnStats.StringStats.newBuilder()
                .setMaxColLength(binaryData.getMaxColLen())
                .setAvgColLength(binaryData.getAvgColLen())
                .build());
        break;

      case DECIMAL_STATS:
        DecimalColumnStatsData decimalData = colData.getDecimalStats();
        builder.setNumNulls(decimalData.getNumNulls());
        builder.setNumDistinctValues(decimalData.getNumDVs());
        builder.setDecimalStats(
            HbaseMetastoreProto.ColumnStats.DecimalStats.newBuilder()
                .setLowValue(
                    HbaseMetastoreProto.ColumnStats.DecimalStats.Decimal.newBuilder()
                      .setUnscaled(ByteString.copyFrom(decimalData.getLowValue().getUnscaled()))
                      .setScale(decimalData.getLowValue().getScale())
                      .build())
                .setHighValue(
                    HbaseMetastoreProto.ColumnStats.DecimalStats.Decimal.newBuilder()
                    .setUnscaled(ByteString.copyFrom(decimalData.getHighValue().getUnscaled()))
                    .setScale(decimalData.getHighValue().getScale())
                    .build()))
                .build();
        break;

      default:
        throw new RuntimeException("Woh, bad.  Unknown stats type!");
    }
    return builder.build().toByteArray();
  }

  static ColumnStatisticsObj deserializeStatsForOneColumn(ColumnStatistics partitionColumnStats,
      byte[] bytes) throws IOException {
    HbaseMetastoreProto.ColumnStats proto = HbaseMetastoreProto.ColumnStats.parseFrom(bytes);
    ColumnStatisticsObj colStats = new ColumnStatisticsObj();
    long lastAnalyzed = proto.getLastAnalyzed();
    if (partitionColumnStats != null) {
      partitionColumnStats.getStatsDesc().setLastAnalyzed(
          Math.max(lastAnalyzed, partitionColumnStats.getStatsDesc().getLastAnalyzed()));
    }
    colStats.setColType(proto.getColumnType());

    ColumnStatisticsData colData = new ColumnStatisticsData();
    if (proto.hasBoolStats()) {
      BooleanColumnStatsData boolData = new BooleanColumnStatsData();
      boolData.setNumTrues(proto.getBoolStats().getNumTrues());
      boolData.setNumFalses(proto.getBoolStats().getNumFalses());
      boolData.setNumNulls(proto.getNumNulls());
      colData.setBooleanStats(boolData);
    } else if (proto.hasLongStats()) {
      LongColumnStatsData longData = new LongColumnStatsData();
      if (proto.getLongStats().hasLowValue()) {
        longData.setLowValue(proto.getLongStats().getLowValue());
      }
      if (proto.getLongStats().hasHighValue()) {
        longData.setHighValue(proto.getLongStats().getHighValue());
      }
      longData.setNumNulls(proto.getNumNulls());
      longData.setNumDVs(proto.getNumDistinctValues());
      colData.setLongStats(longData);
    } else if (proto.hasDoubleStats()) {
      DoubleColumnStatsData doubleData = new DoubleColumnStatsData();
      if (proto.getDoubleStats().hasLowValue()) {
        doubleData.setLowValue(proto.getDoubleStats().getLowValue());
      }
      if (proto.getDoubleStats().hasHighValue()) {
        doubleData.setHighValue(proto.getDoubleStats().getHighValue());
      }
      doubleData.setNumNulls(proto.getNumNulls());
      doubleData.setNumDVs(proto.getNumDistinctValues());
      colData.setDoubleStats(doubleData);
    } else if (proto.hasStringStats()) {
      StringColumnStatsData stringData = new StringColumnStatsData();
      stringData.setMaxColLen(proto.getStringStats().getMaxColLength());
      stringData.setAvgColLen(proto.getStringStats().getAvgColLength());
      stringData.setNumNulls(proto.getNumNulls());
      stringData.setNumDVs(proto.getNumDistinctValues());
      colData.setStringStats(stringData);
    } else if (proto.hasBinaryStats()) {
      BinaryColumnStatsData binaryData = new BinaryColumnStatsData();
      binaryData.setMaxColLen(proto.getBinaryStats().getMaxColLength());
      binaryData.setAvgColLen(proto.getBinaryStats().getAvgColLength());
      binaryData.setNumNulls(proto.getNumNulls());
      colData.setBinaryStats(binaryData);
    } else if (proto.hasDecimalStats()) {
      DecimalColumnStatsData decimalData = new DecimalColumnStatsData();
      if (proto.getDecimalStats().hasHighValue()) {
        Decimal hiVal = new Decimal();
        hiVal.setUnscaled(proto.getDecimalStats().getHighValue().getUnscaled().toByteArray());
        hiVal.setScale((short) proto.getDecimalStats().getHighValue().getScale());
        decimalData.setHighValue(hiVal);
      }
      if (proto.getDecimalStats().hasLowValue()) {
        Decimal loVal = new Decimal();
        loVal.setUnscaled(proto.getDecimalStats().getLowValue().getUnscaled().toByteArray());
        loVal.setScale((short) proto.getDecimalStats().getLowValue().getScale());
        decimalData.setLowValue(loVal);
      }
      decimalData.setNumNulls(proto.getNumNulls());
      decimalData.setNumDVs(proto.getNumDistinctValues());
      colData.setDecimalStats(decimalData);
    } else {
      throw new RuntimeException("Woh, bad.  Unknown stats type!");
    }
    colStats.setStatsData(colData);
    return colStats;
  }

  /**
   * @param keyStart byte array representing the start prefix
   * @return byte array corresponding to the next possible prefix
   */
  static byte[] getEndPrefix(byte[] keyStart) {
    if (keyStart == null) {
      return null;
    }
    // Since this is a prefix and not full key, the usual hbase technique of
    // appending 0 byte does not work. Instead of that, increment the last byte.
    byte[] keyEnd = Arrays.copyOf(keyStart, keyStart.length);
    keyEnd[keyEnd.length - 1]++;
    return keyEnd;
  }
}


File: metastore/src/java/org/apache/hadoop/hive/metastore/hbase/stats/ColumnStatsAggregatorFactory.java
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
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.apache.hadoop.hive.metastore.hbase.stats;

import org.apache.hadoop.hive.metastore.api.ColumnStatisticsData._Fields;

public class ColumnStatsAggregatorFactory {

  private ColumnStatsAggregatorFactory() {
  }

  public static ColumnStatsAggregator getColumnStatsAggregator(_Fields type) {
    switch (type) {
    case BOOLEAN_STATS:
      return new BooleanColumnStatsAggregator();
    case LONG_STATS:
      return new LongColumnStatsAggregator();
    case DOUBLE_STATS:
      return new DoubleColumnStatsAggregator();
    case STRING_STATS:
      return new StringColumnStatsAggregator();
    case BINARY_STATS:
      return new BinaryColumnStatsAggregator();
    case DECIMAL_STATS:
      return new DecimalColumnStatsAggregator();
    default:
      throw new RuntimeException("Woh, bad.  Unknown stats type!");
    }
  }

}


File: metastore/src/test/org/apache/hadoop/hive/metastore/hbase/TestHBaseStore.java
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
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.hadoop.hive.metastore.hbase;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hbase.Cell;
import org.apache.hadoop.hbase.client.HTableInterface;
import org.apache.hadoop.hive.conf.HiveConf;
import org.apache.hadoop.hive.metastore.api.AggrStats;
import org.apache.hadoop.hive.metastore.api.BinaryColumnStatsData;
import org.apache.hadoop.hive.metastore.api.BooleanColumnStatsData;
import org.apache.hadoop.hive.metastore.api.ColumnStatistics;
import org.apache.hadoop.hive.metastore.api.ColumnStatisticsData;
import org.apache.hadoop.hive.metastore.api.ColumnStatisticsDesc;
import org.apache.hadoop.hive.metastore.api.ColumnStatisticsObj;
import org.apache.hadoop.hive.metastore.api.Database;
import org.apache.hadoop.hive.metastore.api.Decimal;
import org.apache.hadoop.hive.metastore.api.DecimalColumnStatsData;
import org.apache.hadoop.hive.metastore.api.DoubleColumnStatsData;
import org.apache.hadoop.hive.metastore.api.FieldSchema;
import org.apache.hadoop.hive.metastore.api.Function;
import org.apache.hadoop.hive.metastore.api.FunctionType;
import org.apache.hadoop.hive.metastore.api.LongColumnStatsData;
import org.apache.hadoop.hive.metastore.api.NoSuchObjectException;
import org.apache.hadoop.hive.metastore.api.Order;
import org.apache.hadoop.hive.metastore.api.Partition;
import org.apache.hadoop.hive.metastore.api.PrincipalType;
import org.apache.hadoop.hive.metastore.api.ResourceType;
import org.apache.hadoop.hive.metastore.api.ResourceUri;
import org.apache.hadoop.hive.metastore.api.Role;
import org.apache.hadoop.hive.metastore.api.SerDeInfo;
import org.apache.hadoop.hive.metastore.api.SkewedInfo;
import org.apache.hadoop.hive.metastore.api.StorageDescriptor;
import org.apache.hadoop.hive.metastore.api.StringColumnStatsData;
import org.apache.hadoop.hive.metastore.api.Table;
import org.junit.AfterClass;
import org.junit.Assert;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.io.IOException;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

/**
 *
 */
public class TestHBaseStore {
  private static final Log LOG = LogFactory.getLog(TestHBaseStore.class.getName());
  static Map<String, String> emptyParameters = new HashMap<String, String>();
  // Table with NUM_PART_KEYS partitioning keys and NUM_PARTITIONS values per key
  static final int NUM_PART_KEYS = 1;
  static final int NUM_PARTITIONS = 5;
  static final String DB = "db";
  static final String TBL = "tbl";
  static final String COL = "col";
  static final String PART_KEY_PREFIX = "part";
  static final String PART_VAL_PREFIX = "val";
  static final String PART_KV_SEPARATOR = "=";
  static final List<String> PART_KEYS = new ArrayList<String>();
  static final List<String> PART_VALS = new ArrayList<String>();
  // Initialize mock partitions
  static {
    for (int i = 1; i <= NUM_PART_KEYS; i++) {
      PART_KEYS.add(PART_KEY_PREFIX + i);
    }
    for (int i = 1; i <= NUM_PARTITIONS; i++) {
      PART_VALS.add(PART_VAL_PREFIX + i);
    }
  }
  static final long DEFAULT_TIME = System.currentTimeMillis();
  static final String BOOLEAN_COL = "boolCol";
  static final String BOOLEAN_TYPE = "boolean";
  static final String LONG_COL = "longCol";
  static final String LONG_TYPE = "long";
  static final String DOUBLE_COL = "doubleCol";
  static final String DOUBLE_TYPE = "double";
  static final String STRING_COL = "stringCol";
  static final String STRING_TYPE = "string";
  static final String BINARY_COL = "binaryCol";
  static final String BINARY_TYPE = "binary";
  static final String DECIMAL_COL = "decimalCol";
  static final String DECIMAL_TYPE = "decimal(5,3)";
  static List<ColumnStatisticsObj> booleanColStatsObjs = new ArrayList<ColumnStatisticsObj>(
      NUM_PARTITIONS);
  static List<ColumnStatisticsObj> longColStatsObjs = new ArrayList<ColumnStatisticsObj>(
      NUM_PARTITIONS);
  static List<ColumnStatisticsObj> doubleColStatsObjs = new ArrayList<ColumnStatisticsObj>(
      NUM_PARTITIONS);
  static List<ColumnStatisticsObj> stringColStatsObjs = new ArrayList<ColumnStatisticsObj>(
      NUM_PARTITIONS);
  static List<ColumnStatisticsObj> binaryColStatsObjs = new ArrayList<ColumnStatisticsObj>(
      NUM_PARTITIONS);
  static List<ColumnStatisticsObj> decimalColStatsObjs = new ArrayList<ColumnStatisticsObj>(
      NUM_PARTITIONS);

  @Rule public ExpectedException thrown = ExpectedException.none();
  @Mock HTableInterface htable;
  SortedMap<String, Cell> rows = new TreeMap<String, Cell>();
  HBaseStore store;


  @BeforeClass
  public static void beforeTest() {
    // All data intitializations
    populateMockStats();
  }

  private static void populateMockStats() {
    ColumnStatisticsObj statsObj;
    // Add NUM_PARTITIONS ColumnStatisticsObj of each type
    // For aggregate stats test, we'll treat each ColumnStatisticsObj as stats for 1 partition
    // For the rest, we'll just pick the 1st ColumnStatisticsObj from this list and use it
    for (int i = 0; i < NUM_PARTITIONS; i++) {
      statsObj = mockBooleanStats(i);
      booleanColStatsObjs.add(statsObj);
      statsObj = mockLongStats(i);
      longColStatsObjs.add(statsObj);
      statsObj = mockDoubleStats(i);
      doubleColStatsObjs.add(statsObj);
      statsObj = mockStringStats(i);
      stringColStatsObjs.add(statsObj);
      statsObj = mockBinaryStats(i);
      binaryColStatsObjs.add(statsObj);
      statsObj = mockDecimalStats(i);
      decimalColStatsObjs.add(statsObj);
    }
  }

  private static ColumnStatisticsObj mockBooleanStats(int i) {
    long trues = 37 + 100*i;
    long falses = 12 + 50*i;
    long nulls = 2 + i;
    ColumnStatisticsObj colStatsObj = new ColumnStatisticsObj();
    colStatsObj.setColName(BOOLEAN_COL);
    colStatsObj.setColType(BOOLEAN_TYPE);
    ColumnStatisticsData data = new ColumnStatisticsData();
    BooleanColumnStatsData boolData = new BooleanColumnStatsData();
    boolData.setNumTrues(trues);
    boolData.setNumFalses(falses);
    boolData.setNumNulls(nulls);
    data.setBooleanStats(boolData);
    colStatsObj.setStatsData(data);
    return colStatsObj;
  }

  private static ColumnStatisticsObj mockLongStats(int i) {
    long high = 120938479124L + 100*i;
    long low = -12341243213412124L - 50*i;
    long nulls = 23 + i;
    long dVs = 213L + 10*i;
    ColumnStatisticsObj colStatsObj = new ColumnStatisticsObj();
    colStatsObj.setColName(LONG_COL);
    colStatsObj.setColType(LONG_TYPE);
    ColumnStatisticsData data = new ColumnStatisticsData();
    LongColumnStatsData longData = new LongColumnStatsData();
    longData.setHighValue(high);
    longData.setLowValue(low);
    longData.setNumNulls(nulls);
    longData.setNumDVs(dVs);
    data.setLongStats(longData);
    colStatsObj.setStatsData(data);
    return colStatsObj;
  }

  private static ColumnStatisticsObj mockDoubleStats(int i) {
    double high = 123423.23423 + 100*i;
    double low = 0.00001234233 - 50*i;
    long nulls = 92 + i;
    long dVs = 1234123421L + 10*i;
    ColumnStatisticsObj colStatsObj = new ColumnStatisticsObj();
    colStatsObj.setColName(DOUBLE_COL);
    colStatsObj.setColType(DOUBLE_TYPE);
    ColumnStatisticsData data = new ColumnStatisticsData();
    DoubleColumnStatsData doubleData = new DoubleColumnStatsData();
    doubleData.setHighValue(high);
    doubleData.setLowValue(low);
    doubleData.setNumNulls(nulls);
    doubleData.setNumDVs(dVs);
    data.setDoubleStats(doubleData);
    colStatsObj.setStatsData(data);
    return colStatsObj;
  }

  private static ColumnStatisticsObj mockStringStats(int i) {
    long maxLen = 1234 + 10*i;
    double avgLen = 32.3 + i;
    long nulls = 987 + 10*i;
    long dVs = 906 + i;
    ColumnStatisticsObj colStatsObj = new ColumnStatisticsObj();
    colStatsObj.setColName(STRING_COL);
    colStatsObj.setColType(STRING_TYPE);
    ColumnStatisticsData data = new ColumnStatisticsData();
    StringColumnStatsData stringData = new StringColumnStatsData();
    stringData.setMaxColLen(maxLen);
    stringData.setAvgColLen(avgLen);
    stringData.setNumNulls(nulls);
    stringData.setNumDVs(dVs);
    data.setStringStats(stringData);
    colStatsObj.setStatsData(data);
    return colStatsObj;
  }

  private static ColumnStatisticsObj mockBinaryStats(int i) {;
    long maxLen = 123412987L + 10*i;
    double avgLen = 76.98 + i;
    long nulls = 976998797L + 10*i;
    ColumnStatisticsObj colStatsObj = new ColumnStatisticsObj();
    colStatsObj.setColName(BINARY_COL);
    colStatsObj.setColType(BINARY_TYPE);
    ColumnStatisticsData data = new ColumnStatisticsData();
    BinaryColumnStatsData binaryData = new BinaryColumnStatsData();
    binaryData.setMaxColLen(maxLen);
    binaryData.setAvgColLen(avgLen);
    binaryData.setNumNulls(nulls);
    data.setBinaryStats(binaryData);
    colStatsObj.setStatsData(data);
    return colStatsObj;
  }

  private static ColumnStatisticsObj mockDecimalStats(int i) {
    Decimal high = new Decimal();
    high.setScale((short)3);
    String strHigh = String.valueOf(3876 + 100*i);
    high.setUnscaled(strHigh.getBytes());
    Decimal low = new Decimal();
    low.setScale((short)3);
    String strLow = String.valueOf(38 + i);
    low.setUnscaled(strLow.getBytes());
    long nulls = 13 + i;
    long dVs = 923947293L + 100*i;
    ColumnStatisticsObj colStatsObj = new ColumnStatisticsObj();
    colStatsObj.setColName(DECIMAL_COL);
    colStatsObj.setColType(DECIMAL_TYPE);
    ColumnStatisticsData data = new ColumnStatisticsData();
    DecimalColumnStatsData decimalData = new DecimalColumnStatsData();
    decimalData.setHighValue(high);
    decimalData.setLowValue(low);
    decimalData.setNumNulls(nulls);
    decimalData.setNumDVs(dVs);
    data.setDecimalStats(decimalData);
    colStatsObj.setStatsData(data);
    return colStatsObj;
  }

  @AfterClass
  public static void afterTest() {
  }


  @Before
  public void init() throws IOException {
    MockitoAnnotations.initMocks(this);
    HiveConf conf = new HiveConf();
    conf.setBoolean(HBaseReadWrite.NO_CACHE_CONF, true);
    store = MockUtils.init(conf, htable, rows);
  }

  @Test
  public void createDb() throws Exception {
    String dbname = "mydb";
    Database db = new Database(dbname, "no description", "file:///tmp", emptyParameters);
    store.createDatabase(db);

    Database d = store.getDatabase(dbname);
    Assert.assertEquals(dbname, d.getName());
    Assert.assertEquals("no description", d.getDescription());
    Assert.assertEquals("file:///tmp", d.getLocationUri());
  }

  @Test
  public void alterDb() throws Exception {
    String dbname = "mydb";
    Database db = new Database(dbname, "no description", "file:///tmp", emptyParameters);
    store.createDatabase(db);
    db.setDescription("a description");
    store.alterDatabase(dbname, db);

    Database d = store.getDatabase(dbname);
    Assert.assertEquals(dbname, d.getName());
    Assert.assertEquals("a description", d.getDescription());
    Assert.assertEquals("file:///tmp", d.getLocationUri());
  }

  @Test
  public void dropDb() throws Exception {
    String dbname = "anotherdb";
    Database db = new Database(dbname, "no description", "file:///tmp", emptyParameters);
    store.createDatabase(db);

    Database d = store.getDatabase(dbname);
    Assert.assertNotNull(d);

    store.dropDatabase(dbname);
    thrown.expect(NoSuchObjectException.class);
    store.getDatabase(dbname);
  }

  @Test
  public void createFunction() throws Exception {
    String funcName = "createfunc";
    int now = (int)(System.currentTimeMillis()/ 1000);
    Function func = new Function(funcName, DB, "o.a.h.h.myfunc", "me", PrincipalType.USER,
        now, FunctionType.JAVA, Arrays.asList(new ResourceUri(ResourceType.JAR,
        "file:/tmp/somewhere")));
    store.createFunction(func);

    Function f = store.getFunction(DB, funcName);
    Assert.assertEquals(DB, f.getDbName());
    Assert.assertEquals(funcName, f.getFunctionName());
    Assert.assertEquals("o.a.h.h.myfunc", f.getClassName());
    Assert.assertEquals("me", f.getOwnerName());
    Assert.assertEquals(PrincipalType.USER, f.getOwnerType());
    Assert.assertTrue(now <= f.getCreateTime());
    Assert.assertEquals(FunctionType.JAVA, f.getFunctionType());
    Assert.assertEquals(1, f.getResourceUrisSize());
    Assert.assertEquals(ResourceType.JAR, f.getResourceUris().get(0).getResourceType());
    Assert.assertEquals("file:/tmp/somewhere", f.getResourceUris().get(0).getUri());
  }

  @Test
  public void alterFunction() throws Exception {
    String funcName = "alterfunc";
    int now = (int)(System.currentTimeMillis()/ 1000);
    List<ResourceUri> uris = new ArrayList<ResourceUri>();
    uris.add(new ResourceUri(ResourceType.FILE, "whatever"));
    Function func = new Function(funcName, DB, "o.a.h.h.myfunc", "me", PrincipalType.USER,
        now, FunctionType.JAVA, uris);
    store.createFunction(func);

    Function f = store.getFunction(DB, funcName);
    Assert.assertEquals(ResourceType.FILE, f.getResourceUris().get(0).getResourceType());

    func.addToResourceUris(new ResourceUri(ResourceType.ARCHIVE, "file"));
    store.alterFunction(DB, funcName, func);

    f = store.getFunction(DB, funcName);
    Assert.assertEquals(2, f.getResourceUrisSize());
    Assert.assertEquals(ResourceType.FILE, f.getResourceUris().get(0).getResourceType());
    Assert.assertEquals(ResourceType.ARCHIVE, f.getResourceUris().get(1).getResourceType());

  }

  @Test
  public void dropFunction() throws Exception {
    String funcName = "delfunc";
    int now = (int)(System.currentTimeMillis()/ 1000);
    Function func = new Function(funcName, DB, "o.a.h.h.myfunc", "me", PrincipalType.USER,
        now, FunctionType.JAVA, Arrays.asList(new ResourceUri(ResourceType.JAR, "file:/tmp/somewhere")));
    store.createFunction(func);

    Function f = store.getFunction(DB, funcName);
    Assert.assertNotNull(f);

    store.dropFunction(DB, funcName);
    //thrown.expect(NoSuchObjectException.class);
    Assert.assertNull(store.getFunction(DB, funcName));
  }

  @Test
  public void createTable() throws Exception {
    String tableName = "mytable";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", ""));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    Map<String, String> params = new HashMap<String, String>();
    params.put("key", "value");
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", false, 17,
        serde, Arrays.asList("bucketcol"), Arrays.asList(new Order("sortcol", 1)), params);
    Table table = new Table(tableName, "default", "me", startTime, startTime, 0, sd, null,
        emptyParameters, null, null, null);
    store.createTable(table);

    Table t = store.getTable("default", tableName);
    Assert.assertEquals(1, t.getSd().getColsSize());
    Assert.assertEquals("col1", t.getSd().getCols().get(0).getName());
    Assert.assertEquals("int", t.getSd().getCols().get(0).getType());
    Assert.assertEquals("", t.getSd().getCols().get(0).getComment());
    Assert.assertEquals("serde", t.getSd().getSerdeInfo().getName());
    Assert.assertEquals("seriallib", t.getSd().getSerdeInfo().getSerializationLib());
    Assert.assertEquals("file:/tmp", t.getSd().getLocation());
    Assert.assertEquals("input", t.getSd().getInputFormat());
    Assert.assertEquals("output", t.getSd().getOutputFormat());
    Assert.assertFalse(t.getSd().isCompressed());
    Assert.assertEquals(17, t.getSd().getNumBuckets());
    Assert.assertEquals(1, t.getSd().getBucketColsSize());
    Assert.assertEquals("bucketcol", t.getSd().getBucketCols().get(0));
    Assert.assertEquals(1, t.getSd().getSortColsSize());
    Assert.assertEquals("sortcol", t.getSd().getSortCols().get(0).getCol());
    Assert.assertEquals(1, t.getSd().getSortCols().get(0).getOrder());
    Assert.assertEquals(1, t.getSd().getParametersSize());
    Assert.assertEquals("value", t.getSd().getParameters().get("key"));
    Assert.assertEquals("me", t.getOwner());
    Assert.assertEquals("default", t.getDbName());
    Assert.assertEquals(tableName, t.getTableName());
    Assert.assertEquals(0, t.getParametersSize());
  }

  @Test
  public void skewInfo() throws Exception {
    String tableName = "mytable";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", ""));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", true, 0,
        serde, null, null, emptyParameters);

    Map<List<String>, String> map = new HashMap<List<String>, String>();
    map.put(Arrays.asList("col3"), "col4");
    SkewedInfo skew = new SkewedInfo(Arrays.asList("col1"), Arrays.asList(Arrays.asList("col2")),
        map);
    sd.setSkewedInfo(skew);
    Table table = new Table(tableName, "default", "me", startTime, startTime, 0, sd, null,
        emptyParameters, null, null, null);
    store.createTable(table);

    Table t = store.getTable("default", tableName);
    Assert.assertEquals(1, t.getSd().getColsSize());
    Assert.assertEquals("col1", t.getSd().getCols().get(0).getName());
    Assert.assertEquals("int", t.getSd().getCols().get(0).getType());
    Assert.assertEquals("", t.getSd().getCols().get(0).getComment());
    Assert.assertEquals("serde", t.getSd().getSerdeInfo().getName());
    Assert.assertEquals("seriallib", t.getSd().getSerdeInfo().getSerializationLib());
    Assert.assertEquals("file:/tmp", t.getSd().getLocation());
    Assert.assertEquals("input", t.getSd().getInputFormat());
    Assert.assertEquals("output", t.getSd().getOutputFormat());
    Assert.assertTrue(t.getSd().isCompressed());
    Assert.assertEquals(0, t.getSd().getNumBuckets());
    Assert.assertEquals(0, t.getSd().getSortColsSize());
    Assert.assertEquals("me", t.getOwner());
    Assert.assertEquals("default", t.getDbName());
    Assert.assertEquals(tableName, t.getTableName());
    Assert.assertEquals(0, t.getParametersSize());

    skew = t.getSd().getSkewedInfo();
    Assert.assertNotNull(skew);
    Assert.assertEquals(1, skew.getSkewedColNamesSize());
    Assert.assertEquals("col1", skew.getSkewedColNames().get(0));
    Assert.assertEquals(1, skew.getSkewedColValuesSize());
    Assert.assertEquals("col2", skew.getSkewedColValues().get(0).get(0));
    Assert.assertEquals(1, skew.getSkewedColValueLocationMapsSize());
    Assert.assertEquals("col4", skew.getSkewedColValueLocationMaps().get(Arrays.asList("col3")));

  }

  @Test
  public void hashSd() throws Exception {
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", ""));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", true, 0,
        serde, null, null, emptyParameters);

    Map<List<String>, String> map = new HashMap<List<String>, String>();
    map.put(Arrays.asList("col3"), "col4");
    SkewedInfo skew = new SkewedInfo(Arrays.asList("col1"), Arrays.asList(Arrays.asList("col2")),
        map);
    sd.setSkewedInfo(skew);

    MessageDigest md = MessageDigest.getInstance("MD5");
    byte[] baseHash = HBaseUtils.hashStorageDescriptor(sd, md);

    StorageDescriptor changeSchema = new StorageDescriptor(sd);
    changeSchema.getCols().add(new FieldSchema("col2", "varchar(32)", "a comment"));
    byte[] schemaHash = HBaseUtils.hashStorageDescriptor(changeSchema, md);
    Assert.assertFalse(Arrays.equals(baseHash, schemaHash));

    StorageDescriptor changeLocation = new StorageDescriptor(sd);
    changeLocation.setLocation("file:/somewhere/else");
    byte[] locationHash = HBaseUtils.hashStorageDescriptor(changeLocation, md);
    Assert.assertArrayEquals(baseHash, locationHash);
  }

  @Test
  public void alterTable() throws Exception {
    String tableName = "alttable";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", "nocomment"));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", false, 0,
        serde, null, null, emptyParameters);
    Table table = new Table(tableName, "default", "me", startTime, startTime, 0, sd, null,
        emptyParameters, null, null, null);
    store.createTable(table);

    startTime += 10;
    table.setLastAccessTime(startTime);
    store.alterTable("default", tableName, table);

    Table t = store.getTable("default", tableName);
    Assert.assertEquals(1, t.getSd().getColsSize());
    Assert.assertEquals("col1", t.getSd().getCols().get(0).getName());
    Assert.assertEquals("int", t.getSd().getCols().get(0).getType());
    Assert.assertEquals("nocomment", t.getSd().getCols().get(0).getComment());
    Assert.assertEquals("serde", t.getSd().getSerdeInfo().getName());
    Assert.assertEquals("seriallib", t.getSd().getSerdeInfo().getSerializationLib());
    Assert.assertEquals("file:/tmp", t.getSd().getLocation());
    Assert.assertEquals("input", t.getSd().getInputFormat());
    Assert.assertEquals("output", t.getSd().getOutputFormat());
    Assert.assertEquals("me", t.getOwner());
    Assert.assertEquals("default", t.getDbName());
    Assert.assertEquals(tableName, t.getTableName());
    Assert.assertEquals(startTime, t.getLastAccessTime());
  }

  @Test
  public void dropTable() throws Exception {
    String tableName = "dtable";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", "nocomment"));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", false, 0,
        serde, null, null, emptyParameters);
    Table table = new Table(tableName, "default", "me", startTime, startTime, 0, sd, null,
        emptyParameters, null, null, null);
    store.createTable(table);

    Table t = store.getTable("default", tableName);
    Assert.assertNotNull(t);

    store.dropTable("default", tableName);
    Assert.assertNull(store.getTable("default", tableName));
  }

  @Test
  public void createPartition() throws Exception {
    String tableName = "myparttable";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", "nocomment"));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", false, 0,
        serde, null, null, emptyParameters);
    List<FieldSchema> partCols = new ArrayList<FieldSchema>();
    partCols.add(new FieldSchema("pc", "string", ""));
    Table table = new Table(tableName, DB, "me", startTime, startTime, 0, sd, partCols,
        emptyParameters, null, null, null);
    store.createTable(table);

    List<String> vals = Arrays.asList("fred");
    StorageDescriptor psd = new StorageDescriptor(sd);
    psd.setLocation("file:/tmp/pc=fred");
    Partition part = new Partition(vals, DB, tableName, startTime, startTime, psd,
        emptyParameters);
    store.addPartition(part);

    Partition p = store.getPartition(DB, tableName, vals);
    Assert.assertEquals(1, p.getSd().getColsSize());
    Assert.assertEquals("col1", p.getSd().getCols().get(0).getName());
    Assert.assertEquals("int", p.getSd().getCols().get(0).getType());
    Assert.assertEquals("nocomment", p.getSd().getCols().get(0).getComment());
    Assert.assertEquals("serde", p.getSd().getSerdeInfo().getName());
    Assert.assertEquals("seriallib", p.getSd().getSerdeInfo().getSerializationLib());
    Assert.assertEquals("file:/tmp/pc=fred", p.getSd().getLocation());
    Assert.assertEquals("input", p.getSd().getInputFormat());
    Assert.assertEquals("output", p.getSd().getOutputFormat());
    Assert.assertEquals(DB, p.getDbName());
    Assert.assertEquals(tableName, p.getTableName());
    Assert.assertEquals(1, p.getValuesSize());
    Assert.assertEquals("fred", p.getValues().get(0));

    Assert.assertTrue(store.doesPartitionExist(DB, tableName, vals));
    Assert.assertFalse(store.doesPartitionExist(DB, tableName, Arrays.asList("bob")));
  }

  @Test
  public void alterPartition() throws Exception {
    String tableName = "alterparttable";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", "nocomment"));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", false, 0,
        serde, null, null, emptyParameters);
    List<FieldSchema> partCols = new ArrayList<FieldSchema>();
    partCols.add(new FieldSchema("pc", "string", ""));
    Table table = new Table(tableName, DB, "me", startTime, startTime, 0, sd, partCols,
        emptyParameters, null, null, null);
    store.createTable(table);

    List<String> vals = Arrays.asList("fred");
    StorageDescriptor psd = new StorageDescriptor(sd);
    psd.setLocation("file:/tmp/pc=fred");
    Partition part = new Partition(vals, DB, tableName, startTime, startTime, psd,
        emptyParameters);
    store.addPartition(part);

    part.setLastAccessTime(startTime + 10);
    store.alterPartition(DB, tableName, vals, part);

    Partition p = store.getPartition(DB, tableName, vals);
    Assert.assertEquals(1, p.getSd().getColsSize());
    Assert.assertEquals("col1", p.getSd().getCols().get(0).getName());
    Assert.assertEquals("int", p.getSd().getCols().get(0).getType());
    Assert.assertEquals("nocomment", p.getSd().getCols().get(0).getComment());
    Assert.assertEquals("serde", p.getSd().getSerdeInfo().getName());
    Assert.assertEquals("seriallib", p.getSd().getSerdeInfo().getSerializationLib());
    Assert.assertEquals("file:/tmp/pc=fred", p.getSd().getLocation());
    Assert.assertEquals("input", p.getSd().getInputFormat());
    Assert.assertEquals("output", p.getSd().getOutputFormat());
    Assert.assertEquals(DB, p.getDbName());
    Assert.assertEquals(tableName, p.getTableName());
    Assert.assertEquals(1, p.getValuesSize());
    Assert.assertEquals("fred", p.getValues().get(0));
    Assert.assertEquals(startTime + 10, p.getLastAccessTime());

    Assert.assertTrue(store.doesPartitionExist(DB, tableName, vals));
    Assert.assertFalse(store.doesPartitionExist(DB, tableName, Arrays.asList("bob")));
  }

  @Test
  public void getPartitions() throws Exception {
    String tableName = "manyParts";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", "nocomment"));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", false, 0,
        serde, null, null, emptyParameters);
    List<FieldSchema> partCols = new ArrayList<FieldSchema>();
    partCols.add(new FieldSchema("pc", "string", ""));
    Table table = new Table(tableName, DB, "me", startTime, startTime, 0, sd, partCols,
        emptyParameters, null, null, null);
    store.createTable(table);

    List<String> partVals = Arrays.asList("alan", "bob", "carl", "doug", "ethan");
    for (String val : partVals) {
      List<String> vals = new ArrayList<String>();
      vals.add(val);
      StorageDescriptor psd = new StorageDescriptor(sd);
      psd.setLocation("file:/tmp/pc=" + val);
      Partition part = new Partition(vals, DB, tableName, startTime, startTime, psd,
          emptyParameters);
      store.addPartition(part);

      Partition p = store.getPartition(DB, tableName, vals);
      Assert.assertEquals("file:/tmp/pc=" + val, p.getSd().getLocation());
    }

    List<Partition> parts = store.getPartitions(DB, tableName, -1);
    Assert.assertEquals(5, parts.size());
    String[] pv = new String[5];
    for (int i = 0; i < 5; i++) pv[i] = parts.get(i).getValues().get(0);
    Arrays.sort(pv);
    Assert.assertArrayEquals(pv, partVals.toArray(new String[5]));
  }

  @Test
  public void listGetDropPartitionNames() throws Exception {
    String tableName = "listParts";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", "nocomment"));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", false, 0,
        serde, null, null, emptyParameters);
    List<FieldSchema> partCols = new ArrayList<FieldSchema>();
    partCols.add(new FieldSchema("pc", "string", ""));
    partCols.add(new FieldSchema("region", "string", ""));
    Table table = new Table(tableName, DB, "me", startTime, startTime, 0, sd, partCols,
        emptyParameters, null, null, null);
    store.createTable(table);

    String[][] partVals = new String[][]{{"today", "north america"}, {"tomorrow", "europe"}};
    for (String[] pv : partVals) {
      List<String> vals = new ArrayList<String>();
      for (String v : pv) vals.add(v);
      StorageDescriptor psd = new StorageDescriptor(sd);
      psd.setLocation("file:/tmp/pc=" + pv[0] + "/region=" + pv[1]);
      Partition part = new Partition(vals, DB, tableName, startTime, startTime, psd,
          emptyParameters);
      store.addPartition(part);
    }

    List<String> names = store.listPartitionNames(DB, tableName, (short) -1);
    Assert.assertEquals(2, names.size());
    String[] resultNames = names.toArray(new String[names.size()]);
    Arrays.sort(resultNames);
    Assert.assertArrayEquals(resultNames, new String[]{"pc=today/region=north america",
      "pc=tomorrow/region=europe"});

    List<Partition> parts = store.getPartitionsByNames(DB, tableName, names);
    Assert.assertArrayEquals(partVals[0], parts.get(0).getValues().toArray(new String[2]));
    Assert.assertArrayEquals(partVals[1], parts.get(1).getValues().toArray(new String[2]));

    store.dropPartitions(DB, tableName, names);
    List<Partition> afterDropParts = store.getPartitions(DB, tableName, -1);
    Assert.assertEquals(0, afterDropParts.size());
  }


  @Test
  public void dropPartition() throws Exception {
    String tableName = "myparttable2";
    int startTime = (int)(System.currentTimeMillis() / 1000);
    List<FieldSchema> cols = new ArrayList<FieldSchema>();
    cols.add(new FieldSchema("col1", "int", "nocomment"));
    SerDeInfo serde = new SerDeInfo("serde", "seriallib", null);
    StorageDescriptor sd = new StorageDescriptor(cols, "file:/tmp", "input", "output", false, 0,
        serde, null, null, emptyParameters);
    List<FieldSchema> partCols = new ArrayList<FieldSchema>();
    partCols.add(new FieldSchema("pc", "string", ""));
    Table table = new Table(tableName, DB, "me", startTime, startTime, 0, sd, partCols,
        emptyParameters, null, null, null);
    store.createTable(table);

    List<String> vals = Arrays.asList("fred");
    StorageDescriptor psd = new StorageDescriptor(sd);
    psd.setLocation("file:/tmp/pc=fred");
    Partition part = new Partition(vals, DB, tableName, startTime, startTime, psd,
        emptyParameters);
    store.addPartition(part);

    Assert.assertNotNull(store.getPartition(DB, tableName, vals));
    store.dropPartition(DB, tableName, vals);
    thrown.expect(NoSuchObjectException.class);
    store.getPartition(DB, tableName, vals);
  }

  @Test
  public void createRole() throws Exception {
    int now = (int)System.currentTimeMillis()/1000;
    String roleName = "myrole";
    store.addRole(roleName, "me");

    Role r = store.getRole(roleName);
    Assert.assertEquals(roleName, r.getRoleName());
    Assert.assertEquals("me", r.getOwnerName());
    Assert.assertTrue(now <= r.getCreateTime());
  }

  @Test
  public void dropRole() throws Exception {
    String roleName = "anotherrole";
    store.addRole(roleName, "me");

    Role role = store.getRole(roleName);
    Assert.assertNotNull(role);

    store.removeRole(roleName);
    thrown.expect(NoSuchObjectException.class);
    store.getRole(roleName);
  }

  // Due to the way our mock stuff works, we can only insert one column at a time, so we'll test
  // each stat type separately.  We'll test them together in the integration tests.
  @Test
  public void booleanTableStatistics() throws Exception {
    // Add a boolean table stats for BOOLEAN_COL to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for table level stats
    ColumnStatisticsDesc desc = getMockTblColStatsDesc();
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = booleanColStatsObjs.get(0);
    BooleanColumnStatsData boolData = obj.getStatsData().getBooleanStats();
    // Add to DB
    stats.addToStatsObj(obj);
    store.updateTableColumnStatistics(stats);
    // Get from DB
    ColumnStatistics statsFromDB = store.getTableColumnStatistics(DB, TBL, Arrays.asList(BOOLEAN_COL));
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.getStatsDesc().getTableName());
    Assert.assertTrue(statsFromDB.getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.BOOLEAN_STATS, dataFromDB.getSetField());
    // Compare BooleanColumnStatsData
    BooleanColumnStatsData boolDataFromDB = dataFromDB.getBooleanStats();
    Assert.assertEquals(boolData.getNumTrues(), boolDataFromDB.getNumTrues());
    Assert.assertEquals(boolData.getNumFalses(), boolDataFromDB.getNumFalses());
    Assert.assertEquals(boolData.getNumNulls(), boolDataFromDB.getNumNulls());
  }

  @Test
  public void longTableStatistics() throws Exception {
    // Add a long table stats for LONG_COL to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for table level stats
    ColumnStatisticsDesc desc = getMockTblColStatsDesc();
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = longColStatsObjs.get(0);
    LongColumnStatsData longData = obj.getStatsData().getLongStats();
    // Add to DB
    stats.addToStatsObj(obj);
    store.updateTableColumnStatistics(stats);
    // Get from DB
    ColumnStatistics statsFromDB = store.getTableColumnStatistics(DB, TBL, Arrays.asList(LONG_COL));
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.getStatsDesc().getTableName());
    Assert.assertTrue(statsFromDB.getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.LONG_STATS, dataFromDB.getSetField());
    // Compare LongColumnStatsData
    LongColumnStatsData longDataFromDB = dataFromDB.getLongStats();
    Assert.assertEquals(longData.getHighValue(), longDataFromDB.getHighValue());
    Assert.assertEquals(longData.getLowValue(), longDataFromDB.getLowValue());
    Assert.assertEquals(longData.getNumNulls(), longDataFromDB.getNumNulls());
    Assert.assertEquals(longData.getNumDVs(), longDataFromDB.getNumDVs());
  }

  @Test
  public void doubleTableStatistics() throws Exception {
    // Add a double table stats for DOUBLE_COL to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for table level stats
    ColumnStatisticsDesc desc = getMockTblColStatsDesc();
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = doubleColStatsObjs.get(0);
    DoubleColumnStatsData doubleData = obj.getStatsData().getDoubleStats();
    // Add to DB
    stats.addToStatsObj(obj);
    store.updateTableColumnStatistics(stats);
    // Get from DB
    ColumnStatistics statsFromDB = store.getTableColumnStatistics(DB, TBL, Arrays.asList(DOUBLE_COL));
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.getStatsDesc().getTableName());
    Assert.assertTrue(statsFromDB.getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.DOUBLE_STATS, dataFromDB.getSetField());
    // Compare DoubleColumnStatsData
    DoubleColumnStatsData doubleDataFromDB = dataFromDB.getDoubleStats();
    Assert.assertEquals(doubleData.getHighValue(), doubleDataFromDB.getHighValue(), 0.01);
    Assert.assertEquals(doubleData.getLowValue(), doubleDataFromDB.getLowValue(), 0.01);
    Assert.assertEquals(doubleData.getNumNulls(), doubleDataFromDB.getNumNulls());
    Assert.assertEquals(doubleData.getNumDVs(), doubleDataFromDB.getNumDVs());
  }

  @Test
  public void stringTableStatistics() throws Exception {
    // Add a string table stats for STRING_COL to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for table level stats
    ColumnStatisticsDesc desc = getMockTblColStatsDesc();
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = stringColStatsObjs.get(0);
    StringColumnStatsData stringData = obj.getStatsData().getStringStats();
    // Add to DB
    stats.addToStatsObj(obj);
    store.updateTableColumnStatistics(stats);
    // Get from DB
    ColumnStatistics statsFromDB = store.getTableColumnStatistics(DB, TBL, Arrays.asList(STRING_COL));
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.getStatsDesc().getTableName());
    Assert.assertTrue(statsFromDB.getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.STRING_STATS, dataFromDB.getSetField());
    // Compare StringColumnStatsData
    StringColumnStatsData stringDataFromDB = dataFromDB.getStringStats();
    Assert.assertEquals(stringData.getMaxColLen(), stringDataFromDB.getMaxColLen());
    Assert.assertEquals(stringData.getAvgColLen(), stringDataFromDB.getAvgColLen(), 0.01);
    Assert.assertEquals(stringData.getNumNulls(), stringDataFromDB.getNumNulls());
    Assert.assertEquals(stringData.getNumDVs(), stringDataFromDB.getNumDVs());
  }

  @Test
  public void binaryTableStatistics() throws Exception {
    // Add a binary table stats for BINARY_COL to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for table level stats
    ColumnStatisticsDesc desc = getMockTblColStatsDesc();
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = binaryColStatsObjs.get(0);
    BinaryColumnStatsData binaryData = obj.getStatsData().getBinaryStats();
    // Add to DB
    stats.addToStatsObj(obj);
    store.updateTableColumnStatistics(stats);
    // Get from DB
    ColumnStatistics statsFromDB = store.getTableColumnStatistics(DB, TBL, Arrays.asList(BINARY_COL));
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.getStatsDesc().getTableName());
    Assert.assertTrue(statsFromDB.getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.BINARY_STATS, dataFromDB.getSetField());
    // Compare BinaryColumnStatsData
    BinaryColumnStatsData binaryDataFromDB = dataFromDB.getBinaryStats();
    Assert.assertEquals(binaryData.getMaxColLen(), binaryDataFromDB.getMaxColLen());
    Assert.assertEquals(binaryData.getAvgColLen(), binaryDataFromDB.getAvgColLen(), 0.01);
    Assert.assertEquals(binaryData.getNumNulls(), binaryDataFromDB.getNumNulls());
  }

  @Test
  public void decimalTableStatistics() throws Exception {
    // Add a decimal table stats for DECIMAL_COL to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for table level stats
    ColumnStatisticsDesc desc = getMockTblColStatsDesc();
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = decimalColStatsObjs.get(0);
    DecimalColumnStatsData decimalData = obj.getStatsData().getDecimalStats();
    // Add to DB
    stats.addToStatsObj(obj);
    store.updateTableColumnStatistics(stats);
    // Get from DB
    ColumnStatistics statsFromDB = store.getTableColumnStatistics(DB, TBL, Arrays.asList(DECIMAL_COL));
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.getStatsDesc().getTableName());
    Assert.assertTrue(statsFromDB.getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.DECIMAL_STATS, dataFromDB.getSetField());
    // Compare DecimalColumnStatsData
    DecimalColumnStatsData decimalDataFromDB = dataFromDB.getDecimalStats();
    Assert.assertEquals(decimalData.getHighValue(), decimalDataFromDB.getHighValue());
    Assert.assertEquals(decimalData.getLowValue(), decimalDataFromDB.getLowValue());
    Assert.assertEquals(decimalData.getNumNulls(), decimalDataFromDB.getNumNulls());
    Assert.assertEquals(decimalData.getNumDVs(), decimalDataFromDB.getNumDVs());
  }

  @Test
  public void booleanPartitionStatistics() throws Exception {
    // Add partition stats for: BOOLEAN_COL and partition: {PART_KEYS(0), PART_VALS(0)} to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for partition level stats
    ColumnStatisticsDesc desc = getMockPartColStatsDesc(0, 0);
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = booleanColStatsObjs.get(0);
    BooleanColumnStatsData boolData = obj.getStatsData().getBooleanStats();
    // Add to DB
    stats.addToStatsObj(obj);
    List<String> parVals = new ArrayList<String>();
    parVals.add(PART_VALS.get(0));
    store.updatePartitionColumnStatistics(stats, parVals);
    // Get from DB
    List<String> partNames = new ArrayList<String>();
    partNames.add(desc.getPartName());
    List<String> colNames = new ArrayList<String>();
    colNames.add(obj.getColName());
    List<ColumnStatistics> statsFromDB = store.getPartitionColumnStatistics(DB, TBL, partNames, colNames);
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(1, statsFromDB.size());
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.get(0).getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.get(0).getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.get(0).getStatsDesc().getTableName());
    Assert.assertFalse(statsFromDB.get(0).getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.get(0).getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.get(0).getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.BOOLEAN_STATS, dataFromDB.getSetField());
    // Compare BooleanColumnStatsData
    BooleanColumnStatsData boolDataFromDB = dataFromDB.getBooleanStats();
    Assert.assertEquals(boolData.getNumTrues(), boolDataFromDB.getNumTrues());
    Assert.assertEquals(boolData.getNumFalses(), boolDataFromDB.getNumFalses());
    Assert.assertEquals(boolData.getNumNulls(), boolDataFromDB.getNumNulls());
  }

  @Test
  public void longPartitionStatistics() throws Exception {
    // Add partition stats for: LONG_COL and partition: {PART_KEYS(0), PART_VALS(0)} to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for partition level stats
    ColumnStatisticsDesc desc = getMockPartColStatsDesc(0, 0);
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = longColStatsObjs.get(0);
    LongColumnStatsData longData = obj.getStatsData().getLongStats();
    // Add to DB
    stats.addToStatsObj(obj);
    List<String> parVals = new ArrayList<String>();
    parVals.add(PART_VALS.get(0));
    store.updatePartitionColumnStatistics(stats, parVals);
    // Get from DB
    List<String> partNames = new ArrayList<String>();
    partNames.add(desc.getPartName());
    List<String> colNames = new ArrayList<String>();
    colNames.add(obj.getColName());
    List<ColumnStatistics> statsFromDB = store.getPartitionColumnStatistics(DB, TBL, partNames, colNames);
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(1, statsFromDB.size());
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.get(0).getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.get(0).getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.get(0).getStatsDesc().getTableName());
    Assert.assertFalse(statsFromDB.get(0).getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.get(0).getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.get(0).getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.LONG_STATS, dataFromDB.getSetField());
    // Compare LongColumnStatsData
    LongColumnStatsData longDataFromDB = dataFromDB.getLongStats();
    Assert.assertEquals(longData.getHighValue(), longDataFromDB.getHighValue());
    Assert.assertEquals(longData.getLowValue(), longDataFromDB.getLowValue());
    Assert.assertEquals(longData.getNumNulls(), longDataFromDB.getNumNulls());
    Assert.assertEquals(longData.getNumDVs(), longDataFromDB.getNumDVs());
  }

  @Test
  public void doublePartitionStatistics() throws Exception {
    // Add partition stats for: DOUBLE_COL and partition: {PART_KEYS(0), PART_VALS(0)} to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for partition level stats
    ColumnStatisticsDesc desc = getMockPartColStatsDesc(0, 0);
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = doubleColStatsObjs.get(0);
    DoubleColumnStatsData doubleData = obj.getStatsData().getDoubleStats();
    // Add to DB
    stats.addToStatsObj(obj);
    List<String> parVals = new ArrayList<String>();
    parVals.add(PART_VALS.get(0));
    store.updatePartitionColumnStatistics(stats, parVals);
    // Get from DB
    List<String> partNames = new ArrayList<String>();
    partNames.add(desc.getPartName());
    List<String> colNames = new ArrayList<String>();
    colNames.add(obj.getColName());
    List<ColumnStatistics> statsFromDB = store.getPartitionColumnStatistics(DB, TBL, partNames, colNames);
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(1, statsFromDB.size());
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.get(0).getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.get(0).getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.get(0).getStatsDesc().getTableName());
    Assert.assertFalse(statsFromDB.get(0).getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.get(0).getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.get(0).getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.DOUBLE_STATS, dataFromDB.getSetField());
    // Compare DoubleColumnStatsData
    DoubleColumnStatsData doubleDataFromDB = dataFromDB.getDoubleStats();
    Assert.assertEquals(doubleData.getHighValue(), doubleDataFromDB.getHighValue(), 0.01);
    Assert.assertEquals(doubleData.getLowValue(), doubleDataFromDB.getLowValue(), 0.01);
    Assert.assertEquals(doubleData.getNumNulls(), doubleDataFromDB.getNumNulls());
    Assert.assertEquals(doubleData.getNumDVs(), doubleDataFromDB.getNumDVs());
  }

  @Test
  public void stringPartitionStatistics() throws Exception {
    // Add partition stats for: STRING_COL and partition: {PART_KEYS(0), PART_VALS(0)} to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for partition level stats
    ColumnStatisticsDesc desc = getMockPartColStatsDesc(0, 0);
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = stringColStatsObjs.get(0);
    StringColumnStatsData stringData = obj.getStatsData().getStringStats();
    // Add to DB
    stats.addToStatsObj(obj);
    List<String> parVals = new ArrayList<String>();
    parVals.add(PART_VALS.get(0));
    store.updatePartitionColumnStatistics(stats, parVals);
    // Get from DB
    List<String> partNames = new ArrayList<String>();
    partNames.add(desc.getPartName());
    List<String> colNames = new ArrayList<String>();
    colNames.add(obj.getColName());
    List<ColumnStatistics> statsFromDB = store.getPartitionColumnStatistics(DB, TBL, partNames, colNames);
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(1, statsFromDB.size());
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.get(0).getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.get(0).getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.get(0).getStatsDesc().getTableName());
    Assert.assertFalse(statsFromDB.get(0).getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.get(0).getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.get(0).getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.STRING_STATS, dataFromDB.getSetField());
    // Compare StringColumnStatsData
    StringColumnStatsData stringDataFromDB = dataFromDB.getStringStats();
    Assert.assertEquals(stringData.getMaxColLen(), stringDataFromDB.getMaxColLen());
    Assert.assertEquals(stringData.getAvgColLen(), stringDataFromDB.getAvgColLen(), 0.01);
    Assert.assertEquals(stringData.getNumNulls(), stringDataFromDB.getNumNulls());
    Assert.assertEquals(stringData.getNumDVs(), stringDataFromDB.getNumDVs());
  }

  @Test
  public void binaryPartitionStatistics() throws Exception {
    // Add partition stats for: BINARY_COL and partition: {PART_KEYS(0), PART_VALS(0)} to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for partition level stats
    ColumnStatisticsDesc desc = getMockPartColStatsDesc(0, 0);
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = binaryColStatsObjs.get(0);
    BinaryColumnStatsData binaryData = obj.getStatsData().getBinaryStats();
    // Add to DB
    stats.addToStatsObj(obj);
    List<String> parVals = new ArrayList<String>();
    parVals.add(PART_VALS.get(0));
    store.updatePartitionColumnStatistics(stats, parVals);
    // Get from DB
    List<String> partNames = new ArrayList<String>();
    partNames.add(desc.getPartName());
    List<String> colNames = new ArrayList<String>();
    colNames.add(obj.getColName());
    List<ColumnStatistics> statsFromDB = store.getPartitionColumnStatistics(DB, TBL, partNames, colNames);
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(1, statsFromDB.size());
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.get(0).getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.get(0).getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.get(0).getStatsDesc().getTableName());
    Assert.assertFalse(statsFromDB.get(0).getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.get(0).getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.get(0).getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.BINARY_STATS, dataFromDB.getSetField());
    // Compare BinaryColumnStatsData
    BinaryColumnStatsData binaryDataFromDB = dataFromDB.getBinaryStats();
    Assert.assertEquals(binaryData.getMaxColLen(), binaryDataFromDB.getMaxColLen());
    Assert.assertEquals(binaryData.getAvgColLen(), binaryDataFromDB.getAvgColLen(), 0.01);
    Assert.assertEquals(binaryData.getNumNulls(), binaryDataFromDB.getNumNulls());
  }

  @Test
  public void decimalPartitionStatistics() throws Exception {
    // Add partition stats for: DECIMAL_COL and partition: {PART_KEYS(0), PART_VALS(0)} to DB
    // Because of the way our mock implementation works we actually need to not create the table
    // before we set statistics on it.
    ColumnStatistics stats = new ColumnStatistics();
    // Get a default ColumnStatisticsDesc for partition level stats
    ColumnStatisticsDesc desc = getMockPartColStatsDesc(0, 0);
    stats.setStatsDesc(desc);
    // Get one of the pre-created ColumnStatisticsObj
    ColumnStatisticsObj obj = decimalColStatsObjs.get(0);
    DecimalColumnStatsData decimalData = obj.getStatsData().getDecimalStats();
    // Add to DB
    stats.addToStatsObj(obj);
    List<String> parVals = new ArrayList<String>();
    parVals.add(PART_VALS.get(0));
    store.updatePartitionColumnStatistics(stats, parVals);
    // Get from DB
    List<String> partNames = new ArrayList<String>();
    partNames.add(desc.getPartName());
    List<String> colNames = new ArrayList<String>();
    colNames.add(obj.getColName());
    List<ColumnStatistics> statsFromDB = store.getPartitionColumnStatistics(DB, TBL, partNames, colNames);
    // Compare ColumnStatisticsDesc
    Assert.assertEquals(1, statsFromDB.size());
    Assert.assertEquals(desc.getLastAnalyzed(), statsFromDB.get(0).getStatsDesc().getLastAnalyzed());
    Assert.assertEquals(DB, statsFromDB.get(0).getStatsDesc().getDbName());
    Assert.assertEquals(TBL, statsFromDB.get(0).getStatsDesc().getTableName());
    Assert.assertFalse(statsFromDB.get(0).getStatsDesc().isIsTblLevel());
    // Compare ColumnStatisticsObj
    Assert.assertEquals(1, statsFromDB.get(0).getStatsObjSize());
    ColumnStatisticsObj objFromDB = statsFromDB.get(0).getStatsObj().get(0);
    ColumnStatisticsData dataFromDB = objFromDB.getStatsData();
    // Compare ColumnStatisticsData
    Assert.assertEquals(ColumnStatisticsData._Fields.DECIMAL_STATS, dataFromDB.getSetField());
    // Compare DecimalColumnStatsData
    DecimalColumnStatsData decimalDataFromDB = dataFromDB.getDecimalStats();
    Assert.assertEquals(decimalData.getHighValue(), decimalDataFromDB.getHighValue());
    Assert.assertEquals(decimalData.getLowValue(), decimalDataFromDB.getLowValue());
    Assert.assertEquals(decimalData.getNumNulls(), decimalDataFromDB.getNumNulls());
    Assert.assertEquals(decimalData.getNumDVs(), decimalDataFromDB.getNumDVs());
  }

  // TODO: Activate this test, when we are able to mock the HBaseReadWrite.NO_CACHE_CONF set to false
  // Right now, I have tested this by using aggrStatsCache despite NO_CACHE_CONF set to true
  // Also need to add tests for other data types + refactor a lot of duplicate code in stats testing
  //@Test
  public void AggrStats() throws Exception {
    int numParts = 3;
    ColumnStatistics stats;
    ColumnStatisticsDesc desc;
    ColumnStatisticsObj obj;
    List<String> partNames = new ArrayList<String>();
    List<String> colNames = new ArrayList<String>();
    colNames.add(BOOLEAN_COL);
    // Add boolean col stats to DB for numParts partitions:
    // PART_VALS(0), PART_VALS(1) & PART_VALS(2) for PART_KEYS(0)
    for (int i = 0; i < numParts; i++) {
      stats = new ColumnStatistics();
      // Get a default ColumnStatisticsDesc for partition level stats
      desc = getMockPartColStatsDesc(0, i);
      stats.setStatsDesc(desc);
      partNames.add(desc.getPartName());
      // Get one of the pre-created ColumnStatisticsObj
      obj = booleanColStatsObjs.get(i);
      stats.addToStatsObj(obj);
      // Add to DB
      List<String> parVals = new ArrayList<String>();
      parVals.add(PART_VALS.get(i));
      store.updatePartitionColumnStatistics(stats, parVals);
    }
    // Read aggregate stats
    AggrStats aggrStatsFromDB = store.get_aggr_stats_for(DB, TBL, partNames, colNames);
    // Verify
    Assert.assertEquals(1, aggrStatsFromDB.getColStatsSize());
    ColumnStatisticsObj objFromDB = aggrStatsFromDB.getColStats().get(0);
    Assert.assertNotNull(objFromDB);
    // Aggregate our mock values
    long numTrues = 0, numFalses = 0, numNulls = 0;
    BooleanColumnStatsData boolData;;
    for (int i = 0; i < numParts; i++) {
      boolData = booleanColStatsObjs.get(i).getStatsData().getBooleanStats();
      numTrues = numTrues + boolData.getNumTrues();
      numFalses = numFalses + boolData.getNumFalses();
      numNulls = numNulls + boolData.getNumNulls();
    }
    // Compare with what we got from the method call
    BooleanColumnStatsData boolDataFromDB = objFromDB.getStatsData().getBooleanStats();
    Assert.assertEquals(numTrues, boolDataFromDB.getNumTrues());
    Assert.assertEquals(numFalses, boolDataFromDB.getNumFalses());
    Assert.assertEquals(numNulls, boolDataFromDB.getNumNulls());
  }

  /**
   * Returns a dummy table level ColumnStatisticsDesc with default values
   */
  private ColumnStatisticsDesc getMockTblColStatsDesc() {
    ColumnStatisticsDesc desc = new ColumnStatisticsDesc();
    desc.setLastAnalyzed(DEFAULT_TIME);
    desc.setDbName(DB);
    desc.setTableName(TBL);
    desc.setIsTblLevel(true);
    return desc;
  }

  /**
   * Returns a dummy partition level ColumnStatisticsDesc
   */
  private ColumnStatisticsDesc getMockPartColStatsDesc(int partKeyIndex, int partValIndex) {
    ColumnStatisticsDesc desc = new ColumnStatisticsDesc();
    desc.setLastAnalyzed(DEFAULT_TIME);
    desc.setDbName(DB);
    desc.setTableName(TBL);
    // part1=val1
    desc.setPartName(PART_KEYS.get(partKeyIndex) + PART_KV_SEPARATOR + PART_VALS.get(partValIndex));
    desc.setIsTblLevel(false);
    return desc;
  }

}
