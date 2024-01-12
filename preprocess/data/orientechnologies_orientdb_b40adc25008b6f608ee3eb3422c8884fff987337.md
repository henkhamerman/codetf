Refactoring Types: ['Extract Method']
technologies/orient/client/remote/OStorageRemote.java
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
package com.orientechnologies.orient.client.remote;

import com.orientechnologies.common.concur.lock.OModificationOperationProhibitedException;
import com.orientechnologies.common.exception.OException;
import com.orientechnologies.common.io.OIOException;
import com.orientechnologies.common.log.OLogManager;
import com.orientechnologies.common.util.OCommonConst;
import com.orientechnologies.orient.client.remote.OStorageRemoteThreadLocal.OStorageRemoteSession;
import com.orientechnologies.orient.core.OConstants;
import com.orientechnologies.orient.core.Orient;
import com.orientechnologies.orient.core.command.OCommandOutputListener;
import com.orientechnologies.orient.core.command.OCommandRequestAsynch;
import com.orientechnologies.orient.core.command.OCommandRequestText;
import com.orientechnologies.orient.core.config.OContextConfiguration;
import com.orientechnologies.orient.core.config.OGlobalConfiguration;
import com.orientechnologies.orient.core.config.OStorageConfiguration;
import com.orientechnologies.orient.core.conflict.ORecordConflictStrategy;
import com.orientechnologies.orient.core.db.ODatabaseRecordThreadLocal;
import com.orientechnologies.orient.core.db.document.ODatabaseDocument;
import com.orientechnologies.orient.core.db.document.ODatabaseDocumentTx;
import com.orientechnologies.orient.core.db.record.OCurrentStorageComponentsFactory;
import com.orientechnologies.orient.core.db.record.OIdentifiable;
import com.orientechnologies.orient.core.db.record.ORecordOperation;
import com.orientechnologies.orient.core.db.record.ridbag.sbtree.OBonsaiCollectionPointer;
import com.orientechnologies.orient.core.db.record.ridbag.sbtree.OSBTreeCollectionManager;
import com.orientechnologies.orient.core.exception.OCommandExecutionException;
import com.orientechnologies.orient.core.exception.ODatabaseException;
import com.orientechnologies.orient.core.exception.ORecordNotFoundException;
import com.orientechnologies.orient.core.exception.OStorageException;
import com.orientechnologies.orient.core.exception.OTransactionException;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.id.ORecordId;
import com.orientechnologies.orient.core.record.ORecord;
import com.orientechnologies.orient.core.record.ORecordInternal;
import com.orientechnologies.orient.core.record.impl.ODocument;
import com.orientechnologies.orient.core.serialization.OSerializableStream;
import com.orientechnologies.orient.core.serialization.serializer.record.string.ORecordSerializerSchemaAware2CSV;
import com.orientechnologies.orient.core.serialization.serializer.record.string.ORecordSerializerStringAbstract;
import com.orientechnologies.orient.core.serialization.serializer.stream.OStreamSerializerAnyStreamable;
import com.orientechnologies.orient.core.sql.query.OLiveQuery;
import com.orientechnologies.orient.core.sql.query.OLiveResultListener;
import com.orientechnologies.orient.core.storage.OCluster;
import com.orientechnologies.orient.core.storage.OPhysicalPosition;
import com.orientechnologies.orient.core.storage.ORawBuffer;
import com.orientechnologies.orient.core.storage.ORecordCallback;
import com.orientechnologies.orient.core.storage.ORecordMetadata;
import com.orientechnologies.orient.core.storage.OStorageAbstract;
import com.orientechnologies.orient.core.storage.OStorageOperationResult;
import com.orientechnologies.orient.core.storage.OStorageProxy;
import com.orientechnologies.orient.core.storage.impl.local.paginated.ORecordSerializationContext;
import com.orientechnologies.orient.core.tx.OTransaction;
import com.orientechnologies.orient.core.tx.OTransactionAbstract;
import com.orientechnologies.orient.core.version.ORecordVersion;
import com.orientechnologies.orient.core.version.OVersionFactory;
import com.orientechnologies.orient.enterprise.channel.binary.OChannelBinaryAsynchClient;
import com.orientechnologies.orient.enterprise.channel.binary.OChannelBinaryProtocol;
import com.orientechnologies.orient.enterprise.channel.binary.ORemoteServerEventListener;

import javax.naming.NamingException;
import javax.naming.directory.Attribute;
import javax.naming.directory.Attributes;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.*;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.FutureTask;

/**
 * This object is bound to each remote ODatabase instances.
 */
public class OStorageRemote extends OStorageAbstract implements OStorageProxy {
  public static final String            PARAM_MIN_POOL       = "minpool";
  public static final String            PARAM_MAX_POOL       = "maxpool";
  public static final String            PARAM_DB_TYPE        = "dbtype";
  private static final String           DEFAULT_HOST         = "localhost";
  private static final int              DEFAULT_PORT         = 2424;
  private static final int              DEFAULT_SSL_PORT     = 2434;
  private static final String           ADDRESS_SEPARATOR    = ";";
  private static final String           DRIVER_NAME          = "OrientDB Java";
  protected final List<String>          serverURLs           = new ArrayList<String>();
  protected final Map<String, OCluster> clusterMap           = new ConcurrentHashMap<String, OCluster>();
  private final ExecutorService         asynchExecutor;
  private final ODocument               clusterConfiguration = new ODocument();
  private final String                  clientId;
  private OContextConfiguration         clientConfiguration;
  private int                           connectionRetry;
  private int                           connectionRetryDelay;
  @Deprecated
  private int                           networkPoolCursor    = 0;
  private OCluster[]                    clusters             = OCommonConst.EMPTY_CLUSTER_ARRAY;
  private int                           defaultClusterId;
  @Deprecated
  private int                           minPool;
  @Deprecated
  private int                           maxPool;
  private ORemoteServerEventListener    asynchEventListener;
  private String                        connectionDbType;

  private volatile String               connectionUserName;

  private String                        connectionUserPassword;
  private Map<String, Object>           connectionOptions;
  private OEngineRemote                 engine;
  private String                        recordFormat;

  public OStorageRemote(final String iClientId, final String iURL, final String iMode) throws IOException {
    this(iClientId, iURL, iMode, null);
  }

  public OStorageRemote(final String iClientId, final String iURL, final String iMode, STATUS status) throws IOException {
    super(iURL, iURL, iMode, 0); // NO TIMEOUT @SINCE 1.5
    if (status != null)
      this.status = status;

    clientId = iClientId;
    configuration = null;

    clientConfiguration = new OContextConfiguration();
    connectionRetry = clientConfiguration.getValueAsInteger(OGlobalConfiguration.NETWORK_SOCKET_RETRY);
    connectionRetryDelay = clientConfiguration.getValueAsInteger(OGlobalConfiguration.NETWORK_SOCKET_RETRY_DELAY);
    asynchEventListener = new OStorageRemoteAsynchEventListener(this);
    parseServerURLs();

    asynchExecutor = Executors.newSingleThreadScheduledExecutor();

    engine = (OEngineRemote) Orient.instance().getEngine(OEngineRemote.NAME);
  }

  @Override
  public boolean isAssigningClusterIds() {
    return false;
  }

  public int getSessionId() {
    final OStorageRemoteThreadLocal instance = OStorageRemoteThreadLocal.INSTANCE;
    return instance != null ? instance.get().sessionId : -1;
  }

  public String getServerURL() {
    final OStorageRemoteThreadLocal instance = OStorageRemoteThreadLocal.INSTANCE;
    return instance != null ? instance.get().serverURL : null;
  }

  public byte[] getSessionToken() {
    final OStorageRemoteThreadLocal instance = OStorageRemoteThreadLocal.INSTANCE;
    return instance != null ? instance.get().token : null;
  }

  public void setSessionId(final String iServerURL, final int iSessionId, byte[] token) {
    final OStorageRemoteThreadLocal instance = OStorageRemoteThreadLocal.INSTANCE;
    if (instance != null) {
      final OStorageRemoteSession tl = instance.get();
      tl.serverURL = iServerURL;
      tl.sessionId = iSessionId;
      tl.token = token;
    }
  }

  public void clearToken() {
    final OStorageRemoteThreadLocal instance = OStorageRemoteThreadLocal.INSTANCE;
    if (instance != null) {
      final OStorageRemoteSession tl = instance.get();
      tl.token = null;
    }
  }

  public void clearSession() {
    final OStorageRemoteThreadLocal instance = OStorageRemoteThreadLocal.INSTANCE;
    if (instance != null)
      instance.remove();
  }

  public ORemoteServerEventListener getAsynchEventListener() {
    return asynchEventListener;
  }

  public void setAsynchEventListener(final ORemoteServerEventListener iListener) {
    asynchEventListener = iListener;
  }

  public void removeRemoteServerEventListener() {
    asynchEventListener = null;
  }

  public void open(final String iUserName, final String iUserPassword, final Map<String, Object> iOptions) {
    addUser();

    lock.acquireExclusiveLock();
    try {

      connectionUserName = iUserName;
      connectionUserPassword = iUserPassword;
      connectionOptions = iOptions != null ? new HashMap<String, Object>(iOptions) : null; // CREATE A COPY TO AVOID USER
      // MANIPULATION
      // POST OPEN
      openRemoteDatabase();

      final OStorageConfiguration storageConfiguration = new OStorageRemoteConfiguration(this, recordFormat);
      storageConfiguration.load();

      configuration = storageConfiguration;

      componentsFactory = new OCurrentStorageComponentsFactory(configuration);
    } catch (Exception e) {
      if (e instanceof RuntimeException)
        // PASS THROUGH
        throw (RuntimeException) e;
      else
        throw new OStorageException("Cannot open the remote storage: " + name, e);

    } finally {
      lock.releaseExclusiveLock();
    }
  }

  public void reload() {

    lock.acquireExclusiveLock();
    try {

      OChannelBinaryAsynchClient network = null;
      do {
        try {

          try {
            network = beginRequest(OChannelBinaryProtocol.REQUEST_DB_RELOAD);
          } finally {
            endRequest(network);
          }

          try {
            beginResponse(network);

            readDatabaseInformation(network);
            break;

          } finally {
            endResponse(network);
          }

        } catch (Exception e) {
          handleException(network, "Error on reloading database information", e);

        }
      } while (true);

    } finally {
      lock.releaseExclusiveLock();
    }
  }

  public void create(final Map<String, Object> iOptions) {
    throw new UnsupportedOperationException(
        "Cannot create a database in a remote server. Please use the console or the OServerAdmin class.");
  }

  public boolean exists() {
    throw new UnsupportedOperationException(
        "Cannot check the existance of a database in a remote server. Please use the console or the OServerAdmin class.");
  }

  public void close(final boolean iForce, boolean onDelete) {
    if (status == STATUS.CLOSED)
      return;

    OChannelBinaryAsynchClient network = null;

    lock.acquireExclusiveLock();
    try {
      if (status == STATUS.CLOSED)
        return;

      network = beginRequest(OChannelBinaryProtocol.REQUEST_DB_CLOSE);
      try {
        setSessionId(null, -1, null);
      } finally {
        endRequest(network);
        engine.getConnectionManager().release(network);
      }

      if (!checkForClose(iForce))
        return;

      status = STATUS.CLOSING;
      // CLOSE ALL THE CONNECTIONS
      engine.getConnectionManager().closePool(getCurrentServerURL());

      super.close(iForce, onDelete);
      status = STATUS.CLOSED;

      Orient.instance().unregisterStorage(this);
    } catch (Exception e) {
      if (network != null) {
        OLogManager.instance().debug(this, "Error on closing remote connection: %s", network);
        network.close();
      }
    } finally {
      lock.releaseExclusiveLock();
    }
  }

  public void delete() {
    throw new UnsupportedOperationException(
        "Cannot delete a database in a remote server. Please use the console or the OServerAdmin class.");
  }

  public Set<String> getClusterNames() {
    lock.acquireSharedLock();
    try {

      return new HashSet<String>(clusterMap.keySet());

    } finally {
      lock.releaseSharedLock();
    }
  }

  public OStorageOperationResult<OPhysicalPosition> createRecord(final ORecordId iRid, final byte[] iContent,
      ORecordVersion iRecordVersion, final byte iRecordType, int iMode, final ORecordCallback<Long> iCallback) {

    if (iMode == 1 && iCallback == null)
      // ASYNCHRONOUS MODE NO ANSWER
      iMode = 2;

    final OPhysicalPosition ppos = new OPhysicalPosition(iRecordType);

    OChannelBinaryAsynchClient lastNetworkUsed = null;
    do {
      try {
        final OChannelBinaryAsynchClient network = beginRequest(OChannelBinaryProtocol.REQUEST_RECORD_CREATE);
        lastNetworkUsed = network;

        try {
          network.writeShort((short) iRid.clusterId);
          network.writeBytes(iContent);
          network.writeByte(iRecordType);
          network.writeByte((byte) iMode);

        } finally {
          endRequest(network);
        }

        switch (iMode) {
        case 0:
          // SYNCHRONOUS
          try {
            beginResponse(network);
            if (network.getSrvProtocolVersion() > OChannelBinaryProtocol.PROTOCOL_VERSION_25)
              iRid.clusterId = network.readShort();

            iRid.clusterPosition = network.readLong();
            ppos.clusterPosition = iRid.clusterPosition;
            if (network.getSrvProtocolVersion() >= 11) {
              ppos.recordVersion = network.readVersion();
            } else
              ppos.recordVersion = OVersionFactory.instance().createVersion();

            if (network.getSrvProtocolVersion() >= 20)
              readCollectionChanges(network, ODatabaseRecordThreadLocal.INSTANCE.get().getSbTreeCollectionManager());

            return new OStorageOperationResult<OPhysicalPosition>(ppos);
          } finally {
            endResponse(network);
          }

        case 1:
          // ASYNCHRONOUS
          if (iCallback != null) {
            final int sessionId = getSessionId();
            final byte[] token = getSessionToken();
            final OSBTreeCollectionManager collectionManager = ODatabaseRecordThreadLocal.INSTANCE.get()
                .getSbTreeCollectionManager();
            Callable<Object> response = new Callable<Object>() {
              public Object call() throws Exception {
                final long result;

                try {
                  OStorageRemoteThreadLocal.INSTANCE.get().sessionId = sessionId;
                  OStorageRemoteThreadLocal.INSTANCE.get().token = token;
                  beginResponse(network);
                  if (network.getSrvProtocolVersion() > OChannelBinaryProtocol.PROTOCOL_VERSION_25)
                    iRid.clusterId = network.readShort();
                  result = network.readLong();
                  if (network.getSrvProtocolVersion() >= 11)
                    network.readVersion();

                  if (network.getSrvProtocolVersion() >= 20)
                    readCollectionChanges(network, collectionManager);
                } catch (Exception e) {
                  OLogManager.instance().error(this, "Exception on async query", e);
                  throw e;
                } finally {
                  endResponse(network);
                  OStorageRemoteThreadLocal.INSTANCE.get().sessionId = -1;
                  OStorageRemoteThreadLocal.INSTANCE.get().token = null;
                }
                iCallback.call(iRid, result);
                return null;
              }

            };
            asynchExecutor.submit(new FutureTask<Object>(response));
          }
          break;

        case 2:
          // FREE THE CHANNEL WITHOUT WAITING ANY RESPONSE
          engine.getConnectionManager().release(network);
          break;
        }

        return new OStorageOperationResult<OPhysicalPosition>(ppos);

      } catch (OModificationOperationProhibitedException mope) {
        handleDBFreeze();
      } catch (Exception e) {
        handleException(lastNetworkUsed, "Error on create record in cluster: " + iRid.clusterId, e);

      }
    } while (true);
  }

  @Override
  public ORecordMetadata getRecordMetadata(final ORID rid) {

    OChannelBinaryAsynchClient network = null;
    do {
      try {
        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_RECORD_METADATA);
          network.writeRID(rid);
        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          final ORID responseRid = network.readRID();
          final ORecordVersion responseVersion = network.readVersion();

          return new ORecordMetadata(responseRid, responseVersion);
        } finally {
          endResponse(network);
        }
      } catch (Exception e) {
        handleException(network, "Error on read record " + rid, e);
      }
    } while (true);
  }

  @Override
  public OStorageOperationResult<ORawBuffer> readRecordIfVersionIsNotLatest(ORecordId rid, String fetchPlan, boolean ignoreCache,
      ORecordVersion recordVersion) throws ORecordNotFoundException {
    if (OStorageRemoteThreadLocal.INSTANCE.get().commandExecuting)
      // PENDING NETWORK OPERATION, CAN'T EXECUTE IT NOW
      return new OStorageOperationResult<ORawBuffer>(null);

    OChannelBinaryAsynchClient network = null;
    do {
      try {

        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_RECORD_LOAD_IF_VERSION_NOT_LATEST);
          network.writeRID(rid);
          network.writeVersion(recordVersion);
          network.writeString(fetchPlan != null ? fetchPlan : "");
          network.writeByte((byte) (ignoreCache ? 1 : 0));
        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);

          if (network.readByte() == 0)
            return new OStorageOperationResult<ORawBuffer>(null);

          byte type = network.readByte();
          ORecordVersion recVersion = network.readVersion();
          byte[] bytes = network.readBytes();
          ORawBuffer buffer = new ORawBuffer(bytes, recVersion, type);

          final ODatabaseDocument database = ODatabaseRecordThreadLocal.INSTANCE.getIfDefined();
          ORecord record;

          while (network.readByte() == 2) {
            record = (ORecord) OChannelBinaryProtocol.readIdentifiable(network);

            if (database != null)
              // PUT IN THE CLIENT LOCAL CACHE
              database.getLocalCache().updateRecord(record);
          }
          return new OStorageOperationResult<ORawBuffer>(buffer);

        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on read record " + rid, e);
      }
    } while (true);
  }

  public OStorageOperationResult<ORawBuffer> readRecord(final ORecordId iRid, final String iFetchPlan, final boolean iIgnoreCache,
      final ORecordCallback<ORawBuffer> iCallback) {

    if (OStorageRemoteThreadLocal.INSTANCE.get().commandExecuting)
      // PENDING NETWORK OPERATION, CAN'T EXECUTE IT NOW
      return new OStorageOperationResult<ORawBuffer>(null);

    OChannelBinaryAsynchClient network = null;
    do {
      try {

        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_RECORD_LOAD);
          network.writeRID(iRid);
          network.writeString(iFetchPlan != null ? iFetchPlan : "");
          if (network.getSrvProtocolVersion() >= 9)
            network.writeByte((byte) (iIgnoreCache ? 1 : 0));

          if (network.getSrvProtocolVersion() >= 13)
            network.writeByte((byte) 0);
        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);

          if (network.readByte() == 0)
            return new OStorageOperationResult<ORawBuffer>(null);

          final ORawBuffer buffer;
          if (network.getSrvProtocolVersion() <= 27)
            buffer = new ORawBuffer(network.readBytes(), network.readVersion(), network.readByte());
          else {
            byte type = network.readByte();
            ORecordVersion recVersion = network.readVersion();
            byte[] bytes = network.readBytes();
            buffer = new ORawBuffer(bytes, recVersion, type);
          }

          final ODatabaseDocument database = ODatabaseRecordThreadLocal.INSTANCE.getIfDefined();
          ORecord record;
          while (network.readByte() == 2) {
            record = (ORecord) OChannelBinaryProtocol.readIdentifiable(network);

            if (database != null)
              // PUT IN THE CLIENT LOCAL CACHE
              database.getLocalCache().updateRecord(record);
          }
          return new OStorageOperationResult<ORawBuffer>(buffer);

        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on read record " + iRid, e);

      }
    } while (true);
  }

  public OStorageOperationResult<ORecordVersion> updateRecord(final ORecordId iRid, boolean updateContent, final byte[] iContent,
      final ORecordVersion iVersion, final byte iRecordType, int iMode, final ORecordCallback<ORecordVersion> iCallback) {

    if (iMode == 1 && iCallback == null)
      // ASYNCHRONOUS MODE NO ANSWER
      iMode = 2;

    OChannelBinaryAsynchClient lastNetworkUsed = null;
    do {
      try {
        final OChannelBinaryAsynchClient network = beginRequest(OChannelBinaryProtocol.REQUEST_RECORD_UPDATE);
        lastNetworkUsed = network;

        try {
          network.writeRID(iRid);
          if (network.getSrvProtocolVersion() >= 23) {
            network.writeBoolean(updateContent);
          }
          network.writeBytes(iContent);
          network.writeVersion(iVersion);
          network.writeByte(iRecordType);
          network.writeByte((byte) iMode);

        } finally {
          endRequest(network);
        }

        switch (iMode) {
        case 0:
          // SYNCHRONOUS
          try {
            beginResponse(network);
            OStorageOperationResult<ORecordVersion> r = new OStorageOperationResult<ORecordVersion>(network.readVersion());
            readCollectionChanges(network, ODatabaseRecordThreadLocal.INSTANCE.get().getSbTreeCollectionManager());
            return r;
          } finally {
            endResponse(network);
          }

        case 1:
          // ASYNCHRONOUS
          final int sessionId = getSessionId();
          final OSBTreeCollectionManager collectionManager = ODatabaseRecordThreadLocal.INSTANCE.get().getSbTreeCollectionManager();
          Callable<Object> response = new Callable<Object>() {
            public Object call() throws Exception {
              ORecordVersion result;

              try {
                OStorageRemoteThreadLocal.INSTANCE.get().sessionId = sessionId;
                beginResponse(network);
                result = network.readVersion();

                if (network.getSrvProtocolVersion() >= 20)
                  readCollectionChanges(network, collectionManager);
              } finally {
                endResponse(network);
                OStorageRemoteThreadLocal.INSTANCE.get().sessionId = -1;
              }

              iCallback.call(iRid, result);
              return null;
            }

          };
          asynchExecutor.submit(new FutureTask<Object>(response));
        }
        return new OStorageOperationResult<ORecordVersion>(iVersion);

      } catch (OModificationOperationProhibitedException mope) {
        handleDBFreeze();
      } catch (Exception e) {
        handleException(lastNetworkUsed, "Error on update record " + iRid, e);

      }
    } while (true);
  }

  public OStorageOperationResult<Boolean> deleteRecord(final ORecordId iRid, final ORecordVersion iVersion, int iMode,
      final ORecordCallback<Boolean> iCallback) {

    if (iMode == 1 && iCallback == null)
      // ASYNCHRONOUS MODE NO ANSWER
      iMode = 2;

    OChannelBinaryAsynchClient network = null;
    do {
      try {
        network = beginRequest(OChannelBinaryProtocol.REQUEST_RECORD_DELETE);
        return new OStorageOperationResult<Boolean>(deleteRecord(iRid, iVersion, iMode, iCallback, network));
      } catch (OModificationOperationProhibitedException mope) {
        handleDBFreeze();
      } catch (Exception e) {
        handleException(network, "Error on delete record " + iRid, e);

      }
    } while (true);
  }

  @Override
  public OStorageOperationResult<Boolean> hideRecord(ORecordId recordId, int mode, ORecordCallback<Boolean> callback) {

    if (mode == 1 && callback == null)
      // ASYNCHRONOUS MODE NO ANSWER
      mode = 2;

    OChannelBinaryAsynchClient network = null;
    do {
      try {
        network = beginRequest(OChannelBinaryProtocol.REQUEST_RECORD_HIDE);
        return new OStorageOperationResult<Boolean>(hideRecord(recordId, mode, callback, network));
      } catch (OModificationOperationProhibitedException mope) {
        handleDBFreeze();
      } catch (Exception e) {
        handleException(network, "Error on delete record " + recordId, e);

      }
    } while (true);
  }

  @Override
  public boolean cleanOutRecord(ORecordId recordId, ORecordVersion recordVersion, int iMode, ORecordCallback<Boolean> callback) {

    if (iMode == 1 && callback == null)
      // ASYNCHRONOUS MODE NO ANSWER
      iMode = 2;

    OChannelBinaryAsynchClient network = null;
    do {
      try {
        network = beginRequest(OChannelBinaryProtocol.REQUEST_RECORD_CLEAN_OUT);
        return deleteRecord(recordId, recordVersion, iMode, callback, network);
      } catch (OModificationOperationProhibitedException mope) {
        handleDBFreeze();
      } catch (Exception e) {
        handleException(network, "Error on clean out record " + recordId, e);

      }
    } while (true);
  }

  @Override
  public void backup(OutputStream out, Map<String, Object> options, Callable<Object> callable,
      final OCommandOutputListener iListener, int compressionLevel, int bufferSize) throws IOException {
    throw new UnsupportedOperationException(
        "backup is not supported against remote storage. Open the database with plocal or use Enterprise Edition");
  }

  @Override
  public void restore(InputStream in, Map<String, Object> options, Callable<Object> callable, final OCommandOutputListener iListener)
      throws IOException {
    throw new UnsupportedOperationException(
        "restore is not supported against remote storage. Open the database with plocal or use Enterprise Edition");
  }

  public long count(final int iClusterId) {
    return count(new int[] { iClusterId });
  }

  @Override
  public long count(int iClusterId, boolean countTombstones) {
    return count(new int[] { iClusterId }, countTombstones);
  }

  public long[] getClusterDataRange(final int iClusterId) {

    OChannelBinaryAsynchClient network = null;
    do {
      try {
        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_DATACLUSTER_DATARANGE);

          network.writeShort((short) iClusterId);

        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          return new long[] { network.readLong(), network.readLong() };
        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on getting last entry position count in cluster: " + iClusterId, e);

      }
    } while (true);
  }

  @Override
  public OPhysicalPosition[] higherPhysicalPositions(int iClusterId, OPhysicalPosition iClusterPosition) {

    OChannelBinaryAsynchClient network = null;
    do {
      try {

        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_POSITIONS_HIGHER);
          network.writeInt(iClusterId);
          network.writeLong(iClusterPosition.clusterPosition);

        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          final int positionsCount = network.readInt();

          if (positionsCount == 0) {
            return OCommonConst.EMPTY_PHYSICAL_POSITIONS_ARRAY;
          } else {
            return readPhysicalPositions(network, positionsCount);
          }

        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on retrieving higher positions after " + iClusterPosition.clusterPosition, e);
      }
    } while (true);
  }

  @Override
  public OPhysicalPosition[] ceilingPhysicalPositions(int clusterId, OPhysicalPosition physicalPosition) {

    OChannelBinaryAsynchClient network = null;
    do {
      try {

        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_POSITIONS_CEILING);
          network.writeInt(clusterId);
          network.writeLong(physicalPosition.clusterPosition);

        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          final int positionsCount = network.readInt();

          if (positionsCount == 0) {
            return OCommonConst.EMPTY_PHYSICAL_POSITIONS_ARRAY;
          } else {
            return readPhysicalPositions(network, positionsCount);
          }

        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on retrieving ceiling positions after " + physicalPosition.clusterPosition, e);
      }
    } while (true);
  }

  @Override
  public OPhysicalPosition[] lowerPhysicalPositions(int iClusterId, OPhysicalPosition physicalPosition) {

    OChannelBinaryAsynchClient network = null;
    do {
      try {

        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_POSITIONS_LOWER);
          network.writeInt(iClusterId);
          network.writeLong(physicalPosition.clusterPosition);

        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);

          final int positionsCount = network.readInt();

          if (positionsCount == 0) {
            return OCommonConst.EMPTY_PHYSICAL_POSITIONS_ARRAY;
          } else {
            return readPhysicalPositions(network, positionsCount);
          }

        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on retrieving lower positions after " + physicalPosition.clusterPosition, e);

      }
    } while (true);
  }

  @Override
  public OPhysicalPosition[] floorPhysicalPositions(int clusterId, OPhysicalPosition physicalPosition) {

    OChannelBinaryAsynchClient network = null;
    do {
      try {

        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_POSITIONS_FLOOR);
          network.writeInt(clusterId);
          network.writeLong(physicalPosition.clusterPosition);

        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);

          final int positionsCount = network.readInt();

          if (positionsCount == 0) {
            return OCommonConst.EMPTY_PHYSICAL_POSITIONS_ARRAY;
          } else {
            return readPhysicalPositions(network, positionsCount);
          }

        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on retrieving floor positions after " + physicalPosition.clusterPosition, e);
      }
    } while (true);
  }

  public long getSize() {

    OChannelBinaryAsynchClient network = null;
    do {
      try {
        try {

          network = beginRequest(OChannelBinaryProtocol.REQUEST_DB_SIZE);

        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          return network.readLong();
        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on read database size", e);

      }
    } while (true);
  }

  @Override
  public long countRecords() {

    OChannelBinaryAsynchClient network = null;
    do {
      try {
        try {

          network = beginRequest(OChannelBinaryProtocol.REQUEST_DB_COUNTRECORDS);

        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          return network.readLong();
        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on read database record count", e);

      }
    } while (true);
  }

  public long count(final int[] iClusterIds) {
    return count(iClusterIds, false);
  }

  public long count(final int[] iClusterIds, boolean countTombstones) {

    OChannelBinaryAsynchClient network = null;
    do {
      try {
        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_DATACLUSTER_COUNT);

          network.writeShort((short) iClusterIds.length);
          for (int iClusterId : iClusterIds)
            network.writeShort((short) iClusterId);

          if (network.getSrvProtocolVersion() >= 13)
            network.writeByte(countTombstones ? (byte) 1 : (byte) 0);
        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          return network.readLong();
        } finally {
          endResponse(network);
        }

      } catch (Exception e) {
        handleException(network, "Error on read record count in clusters: " + Arrays.toString(iClusterIds), e);

      }
    } while (true);
  }

  /**
   * Execute the command remotely and get the results back.
   */
  public Object command(final OCommandRequestText iCommand) {

    if (!(iCommand instanceof OSerializableStream))
      throw new OCommandExecutionException("Cannot serialize the command to be executed to the server side.");

    Object result = null;
    final boolean live = iCommand instanceof OLiveQuery;

    final ODatabaseDocument database = ODatabaseRecordThreadLocal.INSTANCE.get();
    try {
      OChannelBinaryAsynchClient network = null;
      do {

        OStorageRemoteThreadLocal.INSTANCE.get().commandExecuting = true;
        try {

          final boolean asynch = iCommand instanceof OCommandRequestAsynch && ((OCommandRequestAsynch) iCommand).isAsynchronous();

          try {
            network = beginRequest(OChannelBinaryProtocol.REQUEST_COMMAND);

            if (live) {
              network.writeByte((byte) 'l');
            } else {
              network.writeByte((byte) (asynch ? 'a' : 's')); // ASYNC / SYNC
            }
            network.writeBytes(OStreamSerializerAnyStreamable.INSTANCE.toStream(iCommand));

          } finally {
            endRequest(network);
          }

          try {
            beginResponse(network);

            boolean addNextRecord = true;

            if (asynch) {
              byte status;

              // ASYNCH: READ ONE RECORD AT TIME
              while ((status = network.readByte()) > 0) {
                final ORecord record = (ORecord) OChannelBinaryProtocol.readIdentifiable(network);
                if (record == null)
                  continue;

                switch (status) {
                case 1:
                  // PUT AS PART OF THE RESULT SET. INVOKE THE LISTENER
                  if (addNextRecord) {
                    addNextRecord = iCommand.getResultListener().result(record);
                    database.getLocalCache().updateRecord(record);
                  }
                  break;

                case 2:
                  // PUT IN THE CLIENT LOCAL CACHE
                  database.getLocalCache().updateRecord(record);
                }
              }
            } else {
              final byte type = network.readByte();
              switch (type) {
              case 'n':
                result = null;
                break;

              case 'r':
                result = OChannelBinaryProtocol.readIdentifiable(network);
                if (result instanceof ORecord)
                  database.getLocalCache().updateRecord((ORecord) result);
                break;

              case 'l':
                final int tot = network.readInt();
                final Collection<OIdentifiable> list = new ArrayList<OIdentifiable>(tot);
                for (int i = 0; i < tot; ++i) {
                  final OIdentifiable resultItem = OChannelBinaryProtocol.readIdentifiable(network);
                  if (resultItem instanceof ORecord)
                    database.getLocalCache().updateRecord((ORecord) resultItem);
                  list.add(resultItem);
                }
                result = list;
                break;

              case 'a':
                final String value = new String(network.readBytes());
                result = ORecordSerializerStringAbstract.fieldTypeFromStream(null, ORecordSerializerStringAbstract.getType(value),
                    value);
                break;

              default:
                OLogManager.instance().warn(this, "Received unexpected result from query: %d", type);
              }

              if (network.getSrvProtocolVersion() >= 17) {
                // LOAD THE FETCHED RECORDS IN CACHE
                byte status;
                while ((status = network.readByte()) > 0) {
                  final ORecord record = (ORecord) OChannelBinaryProtocol.readIdentifiable(network);
                  if (record != null && status == 2)
                    // PUT IN THE CLIENT LOCAL CACHE
                    database.getLocalCache().updateRecord(record);
                }
              }
              if (live) {
                ODocument doc = ((List<ODocument>) result).get(0);
                Integer token = doc.field("token");
                Boolean unsubscribe = doc.field("unsubscribe");
                if (token != null) {
                  if (Boolean.TRUE.equals(unsubscribe)) {
                    this.asynchEventListener.unregisterLiveListener(token);
                  } else {
                    OLiveResultListener listener = (OLiveResultListener) iCommand.getResultListener();
                    // TODO pass db copy!!!
                    this.asynchEventListener.registerLiveListener(token, listener);
                  }
                } else {
                  throw new OStorageException("Cannot execute live query, returned null token");
                }
              }
            }
            break;
          } finally {
            endResponse(network);
          }
        } catch (OModificationOperationProhibitedException mope) {
          handleDBFreeze();
        } catch (Exception e) {
          handleException(network, "Error on executing command: " + iCommand, e);

        } finally {
          OStorageRemoteThreadLocal.INSTANCE.get().commandExecuting = false;
        }
      } while (true);
    } finally {
      if (iCommand.getResultListener() != null && !live)
        iCommand.getResultListener().end();
    }

    return result;
  }

  public void commit(final OTransaction iTx, Runnable callback) {

    final List<ORecordOperation> committedEntries = new ArrayList<ORecordOperation>();
    OChannelBinaryAsynchClient network = null;
    do {
      try {
        OStorageRemoteThreadLocal.INSTANCE.get().commandExecuting = true;

        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_TX_COMMIT);

          network.writeInt(iTx.getId());
          network.writeByte((byte) (iTx.isUsingLog() ? 1 : 0));

          final List<ORecordOperation> tmpEntries = new ArrayList<ORecordOperation>();

          if (iTx.getCurrentRecordEntries().iterator().hasNext()) {
            for (ORecordOperation txEntry : iTx.getCurrentRecordEntries())
              committedEntries.add(txEntry);
            while (iTx.getCurrentRecordEntries().iterator().hasNext()) {
              for (ORecordOperation txEntry : iTx.getCurrentRecordEntries())
                tmpEntries.add(txEntry);

              iTx.clearRecordEntries();

              if (tmpEntries.size() > 0) {
                for (ORecordOperation txEntry : tmpEntries) {
                  commitEntry(network, txEntry);
                }
                tmpEntries.clear();
              }
            }
          } else if (committedEntries.size() > 0) {
            tmpEntries.addAll(committedEntries);
            while (!tmpEntries.isEmpty()) {
              iTx.clearRecordEntries();
              for (ORecordOperation txEntry : tmpEntries) {
                ORecordInternal.clearSource(txEntry.getRecord());
                commitEntry(network, txEntry);
              }
              tmpEntries.clear();
              for (ORecordOperation txEntry : iTx.getCurrentRecordEntries())
                tmpEntries.add(txEntry);
            }
          }

          // END OF RECORD ENTRIES
          network.writeByte((byte) 0);

          // SEND INDEX ENTRIES
          network.writeBytes(iTx.getIndexChanges().toStream());
        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          final int createdRecords = network.readInt();
          ORecordId currentRid;
          ORecordId createdRid;
          for (int i = 0; i < createdRecords; i++) {
            currentRid = network.readRID();
            createdRid = network.readRID();

            iTx.updateIdentityAfterCommit(currentRid, createdRid);
          }

          final int updatedRecords = network.readInt();
          ORecordId rid;
          for (int i = 0; i < updatedRecords; ++i) {
            rid = network.readRID();

            ORecordOperation rop = iTx.getRecordEntry(rid);
            if (rop != null)
              rop.getRecord().getRecordVersion().copyFrom(network.readVersion());
          }

          if (network.getSrvProtocolVersion() >= 20)
            readCollectionChanges(network, ODatabaseRecordThreadLocal.INSTANCE.get().getSbTreeCollectionManager());

        } finally {
          endResponse(network);
        }

        committedEntries.clear();
        // SET ALL THE RECORDS AS UNDIRTY
        for (ORecordOperation txEntry : iTx.getAllRecordEntries())
          ORecordInternal.unsetDirty(txEntry.getRecord());

        // UPDATE THE CACHE ONLY IF THE ITERATOR ALLOWS IT. USE THE STRATEGY TO ALWAYS REMOVE ALL THE RECORDS SINCE THEY COULD BE
        // CHANGED AS CONTENT IN CASE OF TREE AND GRAPH DUE TO CROSS REFERENCES
        OTransactionAbstract.updateCacheFromEntries(iTx, iTx.getAllRecordEntries(), false);

        break;

      } catch (OModificationOperationProhibitedException mope) {
        handleDBFreeze();
      } catch (Exception e) {
        handleException(network, "Error on commit", e);

      } finally {
        OStorageRemoteThreadLocal.INSTANCE.get().commandExecuting = false;

      }
    } while (true);
  }

  public void rollback(OTransaction iTx) {
  }

  public int getClusterIdByName(final String iClusterName) {
    lock.acquireSharedLock();
    try {

      if (iClusterName == null)
        return -1;

      if (Character.isDigit(iClusterName.charAt(0)))
        return Integer.parseInt(iClusterName);

      final OCluster cluster = clusterMap.get(iClusterName.toLowerCase());
      if (cluster == null)
        return -1;

      return cluster.getId();
    } finally {
      lock.releaseSharedLock();
    }
  }

  public int getDefaultClusterId() {
    return defaultClusterId;
  }

  public void setDefaultClusterId(int defaultClusterId) {
    this.defaultClusterId = defaultClusterId;
  }

  public int addCluster(final String iClusterName, boolean forceListBased, final Object... iArguments) {
    return addCluster(iClusterName, -1, forceListBased, iArguments);
  }

  public int addCluster(String iClusterName, int iRequestedId, boolean forceListBased, Object... iParameters) {

    OChannelBinaryAsynchClient network = null;
    do {
      lock.acquireExclusiveLock();
      try {
        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_DATACLUSTER_ADD);

          network.writeString(iClusterName);
          if (network.getSrvProtocolVersion() >= 18)
            network.writeShort((short) iRequestedId);
        } finally {
          endRequest(network);
        }

        try {
          beginResponse(network);
          final int clusterId = network.readShort();

          final OClusterRemote cluster = new OClusterRemote();
          cluster.configure(this, clusterId, iClusterName.toLowerCase());

          if (clusters.length <= clusterId)
            clusters = Arrays.copyOf(clusters, clusterId + 1);
          clusters[cluster.getId()] = cluster;
          clusterMap.put(cluster.getName().toLowerCase(), cluster);

          return clusterId;
        } finally {
          endResponse(network);
        }
      } catch (OModificationOperationProhibitedException mphe) {
        handleDBFreeze();
      } catch (Exception e) {
        handleException(network, "Error on add new cluster", e);
      } finally {
        lock.releaseExclusiveLock();
      }
    } while (true);
  }

  public boolean dropCluster(final int iClusterId, final boolean iTruncate) {

    OChannelBinaryAsynchClient network = null;
    do {
      lock.acquireExclusiveLock();
      try {
        try {
          network = beginRequest(OChannelBinaryProtocol.REQUEST_DATACLUSTER_DROP);

          network.writeShort((short) iClusterId);

        } finally {
          endRequest(network);
        }

        byte result = 0;
        try {
          beginResponse(network);
          result = network.readByte();
        } finally {
          endResponse(network);
        }

        if (result == 1) {
          // REMOVE THE CLUSTER LOCALLY
          final OCluster cluster = clusters[iClusterId];
          clusters[iClusterId] = null;
          clusterMap.remove(cluster.getName());
          if (configuration.clusters.size() > iClusterId)
            configuration.dropCluster(iClusterId); // endResponse must be called before this line, which call updateRecord

          return true;
        }
        return false;

      } catch (OModificationOperationProhibitedException mope) {
        handleDBFreeze();
      } catch (Exception e) {
        handleException(network, "Error on removing of cluster", e);

      } finally {
        lock.releaseExclusiveLock();
      }
    } while (true);
  }

  public void synch() {
  }

  public String getPhysicalClusterNameById(final int iClusterId) {
    lock.acquireSharedLock();
    try {

      if (iClusterId >= clusters.length)
        return null;

      final OCluster cluster = clusters[iClusterId];
      return cluster != null ? cluster.getName() : null;

    } finally {
      lock.releaseSharedLock();
    }
  }

  public int getClusterMap() {
    lock.acquireSharedLock();
    try {
      return clusterMap.size();
    } finally {
      lock.releaseSharedLock();
    }
  }

  public Collection<OCluster> getClusterInstances() {
    lock.acquireSharedLock();
    try {

      return Arrays.asList(clusters);

    } finally {
      lock.releaseSharedLock();
    }
  }

  public OCluster getClusterById(int iClusterId) {
    lock.acquireSharedLock();
    try {

      if (iClusterId == ORID.CLUSTER_ID_INVALID)
        // GET THE DEFAULT CLUSTER
        iClusterId = defaultClusterId;

      return clusters[iClusterId];

    } finally {
      lock.releaseSharedLock();
    }
  }

  @Override
  public long getVersion() {
    throw new UnsupportedOperationException("getVersion");
  }

  public ODocument getClusterConfiguration() {
    return clusterConfiguration;
  }

  /**
   * Ends the request and unlock the write lock
   */
  public void endRequest(final OChannelBinaryAsynchClient iNetwork) throws IOException {
    if (iNetwork == null)
      return;

    try {
      iNetwork.flush();
      iNetwork.releaseWriteLock();
    } catch (IOException e) {
      engine.getConnectionManager().remove(iNetwork);
      throw e;
    }
  }

  /**
   * End response reached: release the channel in the pool to being reused
   */
  public void endResponse(final OChannelBinaryAsynchClient iNetwork) {
    iNetwork.endResponse();
    engine.getConnectionManager().release(iNetwork);
  }

  public boolean isPermanentRequester() {
    return false;
  }

  @SuppressWarnings("unchecked")
  public void updateClusterConfiguration(final String iConnectedURL, final byte[] obj) {
    if (obj == null)
      return;

    // UPDATE IT
    synchronized (serverURLs) {
      clusterConfiguration.fromStream(obj);

      clusterConfiguration.toString();

      final List<ODocument> members = clusterConfiguration.field("members");
      if (members != null) {
        serverURLs.clear();

        // ADD CURRENT SERVER AS FIRST
        addHost(iConnectedURL);

        // parseServerURLs();

        for (ODocument m : members)
          if (m != null && !serverURLs.contains((String) m.field("name"))) {
            final Collection<Map<String, Object>> listeners = ((Collection<Map<String, Object>>) m.field("listeners"));
            if (listeners == null)
              throw new ODatabaseException("Received bad distributed configuration: missing 'listeners' array field");

            for (Map<String, Object> listener : listeners) {
              if (((String) listener.get("protocol")).equals("ONetworkProtocolBinary")) {
                String url = (String) listener.get("listen");
                if (!serverURLs.contains(url))
                  addHost(url);
              }
            }
          }
      }
    }
  }

  @Override
  public OCluster getClusterByName(final String iClusterName) {
    throw new UnsupportedOperationException("getClusterByName()");
  }

  @Override
  public ORecordConflictStrategy getConflictStrategy() {
    throw new UnsupportedOperationException("getConflictStrategy");
  }

  @Override
  public void setConflictStrategy(final ORecordConflictStrategy iResolver) {
    throw new UnsupportedOperationException("setConflictStrategy");
  }

  @Override
  public String getURL() {
    return OEngineRemote.NAME + ":" + url;
  }

  public String getClientId() {
    return clientId;
  }

  public int getClusters() {
    lock.acquireSharedLock();
    try {
      return clusterMap.size();
    } finally {
      lock.releaseSharedLock();
    }
  }

  @Override
  public String getType() {
    return OEngineRemote.NAME;
  }

  @Override
  public Class<OSBTreeCollectionManagerRemote> getCollectionManagerClass() {
    return OSBTreeCollectionManagerRemote.class;
  }

  public OEngineRemote getEngine() {
    return engine;
  }

  @Override
  public String getUserName() {
    return connectionUserName;
  }

  /**
   * Handles exceptions. In case of IO errors retries to reconnect until the configured retry times has reached.
   * 
   * @param message
   *          the detail message
   * @param exception
   *          cause of the error
   */
  protected void handleException(final OChannelBinaryAsynchClient iNetwork, final String message, Exception exception) {

    Exception originalException = exception;
    if (exception instanceof OIOException) {
      // BYPASS IT TO HANDLE RE-CONNECT
      exception = (Exception) exception.getCause();
    } else if (exception instanceof OException) {
      // Release on concurrent modification exception created some issue. to double check
      if (iNetwork != null)
        engine.getConnectionManager().release(iNetwork);

      // RE-THROW IT
      throw (OException) exception;
    } else if (!(exception instanceof IOException)) {
      if (iNetwork != null)
        engine.getConnectionManager().release(iNetwork);
      throw new OStorageException(message, exception);
    }

    if (status != STATUS.OPEN)
      // STORAGE CLOSED: DON'T HANDLE RECONNECTION
      return;

    if (iNetwork != null) {
      OLogManager.instance().warn(this, "Caught I/O errors from %s (local socket=%s), trying to reconnect (error: %s)", iNetwork,
          iNetwork.getLocalSocketAddress(), exception == null ? originalException : exception);
      OLogManager.instance().debug(this, "I/O error stack: ", exception == null ? originalException : exception);

      try {
        engine.getConnectionManager().remove(iNetwork);
      } catch (Exception e) {
        // IGNORE ANY EXCEPTION
      }
    } else {
      OLogManager.instance().warn(this, "Caught I/O errors, trying to reconnect (error: %s)",
          exception == null ? originalException.toString() : exception.toString());
      OLogManager.instance().debug(this, "I/O error stack: ", exception == null ? originalException : exception);
    }

    final long lostConnectionTime = System.currentTimeMillis();

    final int currentMaxRetry;
    final int currentRetryDelay;

    final int urlSize;
    synchronized (serverURLs) {
      urlSize = serverURLs.size();
    }

    if (urlSize > 1) {
      // IN CLUSTER: NO RETRY AND 0 SLEEP TIME BETWEEN NODES
      currentMaxRetry = 1;
      currentRetryDelay = 0;
    } else {
      currentMaxRetry = connectionRetry;
      currentRetryDelay = connectionRetryDelay;
    }

    for (int retry = 0; retry < currentMaxRetry; ++retry) {
      // WAIT THE DELAY BEFORE TO RETRY (BUT FIRST TRY)
      if (retry > 0 && currentRetryDelay > 0)
        try {
          Thread.sleep(currentRetryDelay);
        } catch (InterruptedException e) {
          // THREAD INTERRUPTED: RETURN EXCEPTION
          Thread.currentThread().interrupt();
          break;
        }

      try {
        if (OLogManager.instance().isDebugEnabled())
          OLogManager.instance()
              .debug(this, "Retrying to connect to remote server #" + (retry + 1) + "/" + currentMaxRetry + "...");

        // FORCE RESET OF THREAD DATA (SERVER URL + SESSION ID)
        setSessionId(null, -1, null);

        // REACQUIRE DB SESSION ID
        final String currentURL = openRemoteDatabase();

        OLogManager
            .instance()
            .warn(
                this,
                "Connection re-acquired transparently after %dms and %d retries to server '%s': no errors will be thrown at application level",
                System.currentTimeMillis() - lostConnectionTime, retry + 1, currentURL);

        // RECONNECTED!
        return;

      } catch (Throwable t) {
        // DO NOTHING BUT CONTINUE IN THE LOOP
      }
    }

    // RECONNECTION FAILED: THROW+LOG THE ORIGINAL EXCEPTION
    throw new OStorageException(message, exception);
  }

  protected String openRemoteDatabase() throws IOException {
    connectionDbType = ODatabaseDocument.TYPE;

    if (connectionOptions != null && connectionOptions.size() > 0) {
      if (connectionOptions.containsKey(PARAM_DB_TYPE))
        connectionDbType = connectionOptions.get(PARAM_DB_TYPE).toString();
    }

    OChannelBinaryAsynchClient network = null;
    String currentURL = getCurrentServerURL();
    do {
      do {
        try {
          clearToken();
          network = getAvailableNetwork(currentURL);
          try {
            network.writeByte(OChannelBinaryProtocol.REQUEST_DB_OPEN);
            network.writeInt(getSessionId());

            // @SINCE 1.0rc8
            sendClientInfo(network);

            network.writeString(name);

            if (network.getSrvProtocolVersion() >= 8)
              network.writeString(connectionDbType);

            network.writeString(connectionUserName);
            network.writeString(connectionUserPassword);

          } finally {
            endRequest(network);
          }

          final int sessionId;

          try {
            beginResponse(network);
            sessionId = network.readInt();
            byte[] token = network.readBytes();
            if (token.length == 0) {
              token = null;
            } else {
              network.getServiceThread().setTokenBased(true);
            }
            setSessionId(network.getServerURL(), sessionId, token);

            OLogManager.instance().debug(this, "Client connected to %s with session id=%d", network.getServerURL(), sessionId);

            readDatabaseInformation(network);

            // READ CLUSTER CONFIGURATION
            updateClusterConfiguration(network.getServerURL(), network.readBytes());

            // read OrientDB release info
            if (network.getSrvProtocolVersion() >= 14)
              network.readString();

            status = STATUS.OPEN;

            return currentURL;

          } finally {
            endResponse(network);
          }
        } catch (OIOException e) {
          if (network != null) {
            // REMOVE THE NETWORK CONNECTION IF ANY
            engine.getConnectionManager().remove(network);
            network = null;
          }
        } catch (OException e) {
          // PROPAGATE ANY OTHER ORIENTDB EXCEPTION
          throw e;

        } catch (Exception e) {
          if (network != null) {
            // REMOVE THE NETWORK CONNECTION IF ANY
            engine.getConnectionManager().remove(network);
            network = null;
          }
        }
      } while (engine.getConnectionManager().getAvailableConnections(currentURL) > 0);

      currentURL = useNewServerURL(currentURL);

    } while (currentURL != null);

    // REFILL ORIGINAL SERVER LIST
    parseServerURLs();

    synchronized (serverURLs) {
      throw new OStorageException("Cannot create a connection to remote server address(es): " + serverURLs);
    }
  }

  protected String useNewServerURL(final String iUrl) {
    int pos = iUrl.indexOf('/');
    if (pos >= iUrl.length() - 1)
      // IGNORE ENDING /
      pos = -1;

    final String postFix = pos > -1 ? iUrl.substring(pos) : "";
    final String url = pos > -1 ? iUrl.substring(0, pos) : iUrl;

    synchronized (serverURLs) {
      // REMOVE INVALID URL
      serverURLs.remove(url);

      OLogManager.instance().debug(this, "Updated server list: %s...", serverURLs);

      if (!serverURLs.isEmpty())
        return serverURLs.get(0) + postFix;
    }

    return null;
  }

  protected void sendClientInfo(OChannelBinaryAsynchClient network) throws IOException {
    if (network.getSrvProtocolVersion() >= 7) {
      // @COMPATIBILITY 1.0rc8
      network.writeString(DRIVER_NAME).writeString(OConstants.ORIENT_VERSION)
          .writeShort((short) OChannelBinaryProtocol.CURRENT_PROTOCOL_VERSION).writeString(clientId);
    }
    if (network.getSrvProtocolVersion() > OChannelBinaryProtocol.PROTOCOL_VERSION_21) {
      network.writeString(ODatabaseDocumentTx.getDefaultSerializer().toString());
      recordFormat = ODatabaseDocumentTx.getDefaultSerializer().toString();
    } else
      recordFormat = ORecordSerializerSchemaAware2CSV.NAME;
    if (network.getSrvProtocolVersion() > OChannelBinaryProtocol.PROTOCOL_VERSION_26)
      network.writeBoolean(OGlobalConfiguration.CLIENT_SESSION_TOKEN_BASED.getValueAsBoolean());
  }

  /**
   * Parse the URLs. Multiple URLs must be separated by semicolon (;)
   */
  protected void parseServerURLs() {
    String lastHost = null;
    int dbPos = url.indexOf('/');
    if (dbPos == -1) {
      // SHORT FORM
      addHost(url);
      lastHost = url;
      name = url;
    } else {
      name = url.substring(url.lastIndexOf("/") + 1);
      for (String host : url.substring(0, dbPos).split(ADDRESS_SEPARATOR)) {
        lastHost = host;
        addHost(host);
      }
    }

    synchronized (serverURLs) {
      if (serverURLs.size() == 1 && OGlobalConfiguration.NETWORK_BINARY_DNS_LOADBALANCING_ENABLED.getValueAsBoolean()) {
        // LOOK FOR LOAD BALANCING DNS TXT RECORD
        final String primaryServer = lastHost;

        OLogManager.instance().debug(this, "Retrieving URLs from DNS '%s' (timeout=%d)...", primaryServer,
            OGlobalConfiguration.NETWORK_BINARY_DNS_LOADBALANCING_TIMEOUT.getValueAsInteger());

        try {
          final Hashtable<String, String> env = new Hashtable<String, String>();
          env.put("java.naming.factory.initial", "com.sun.jndi.dns.DnsContextFactory");
          env.put("com.sun.jndi.ldap.connect.timeout",
              OGlobalConfiguration.NETWORK_BINARY_DNS_LOADBALANCING_TIMEOUT.getValueAsString());
          final DirContext ictx = new InitialDirContext(env);
          final String hostName = !primaryServer.contains(":") ? primaryServer : primaryServer.substring(0,
              primaryServer.indexOf(":"));
          final Attributes attrs = ictx.getAttributes(hostName, new String[] { "TXT" });
          final Attribute attr = attrs.get("TXT");
          if (attr != null) {
            for (int i = 0; i < attr.size(); ++i) {
              String configuration = (String) attr.get(i);
              if (configuration.startsWith("\""))
                configuration = configuration.substring(1, configuration.length() - 1);
              if (configuration != null) {
                serverURLs.clear();
                final String[] parts = configuration.split(" ");
                for (String part : parts) {
                  if (part.startsWith("s=")) {
                    addHost(part.substring("s=".length()));
                  }
                }
              }
            }
          }
        } catch (NamingException ignore) {
        }
      }
    }
  }

  /**
   * Registers the remote server with port.
   */
  protected String addHost(String host) {
    if (host.startsWith("localhost"))
      host = "127.0.0.1" + host.substring("localhost".length());

    // REGISTER THE REMOTE SERVER+PORT
    if (!host.contains(":"))
      host += ":"
          + (clientConfiguration.getValueAsBoolean(OGlobalConfiguration.CLIENT_USE_SSL) ? getDefaultSSLPort() : getDefaultPort());

    if (host.contains("/"))
      host = host.substring(0, host.indexOf("/"));

    synchronized (serverURLs) {
      if (!serverURLs.contains(host))
        serverURLs.add(host);
    }

    return host;
  }

  protected String getDefaultHost() {
    return DEFAULT_HOST;
  }

  protected int getDefaultPort() {
    return DEFAULT_PORT;
  }

  protected int getDefaultSSLPort() {
    return DEFAULT_SSL_PORT;
  }

  /**
   * Acquire a network channel from the pool. Don't lock the write stream since the connection usage is exclusive.
   * 
   * @param iCommand
   *          id. Ids described at {@link OChannelBinaryProtocol}
   * @return connection to server
   * @throws IOException
   */
  protected OChannelBinaryAsynchClient beginRequest(final byte iCommand) throws IOException {
    final OChannelBinaryAsynchClient network = getAvailableNetwork(getCurrentServerURL());
    network.writeByte(iCommand);
    network.writeInt(getSessionId());
    byte[] token = getSessionToken();
    if (token != null) {
      network.writeBytes(token);
    }

    return network;
  }

  protected String getCurrentServerURL() {
    synchronized (serverURLs) {
      if (serverURLs.isEmpty()) {
        parseServerURLs();
        if (serverURLs.isEmpty())
          throw new OStorageException("Cannot create a connection to remote server because url list is empty");
      }

      return serverURLs.get(0) + "/" + getName();
    }
  }

  protected OChannelBinaryAsynchClient getAvailableNetwork(final String iCurrentURL) throws IOException {
    OChannelBinaryAsynchClient network;

    String lastURL = iCurrentURL;
    do {
      try {
        network = engine.getConnectionManager().acquire(lastURL, clientConfiguration, connectionOptions, asynchEventListener);
      } catch (Exception e) {
        // CATCH ANY EXCEPTION AND TRY WITH A NEXT ONE IF ANY
        network = null;
      }

      if (network == null) {
        lastURL = useNewServerURL(lastURL);
        if (lastURL == null) {
          parseServerURLs();
          throw new OIOException("Cannot open a connection to remote server: " + iCurrentURL);
        }
      } else if (!network.isConnected()) {
        // DISCONNECTED NETWORK, GET ANOTHER ONE
        OLogManager.instance().error(this, "Removing disconnected network channel '%s'...", lastURL);
        engine.getConnectionManager().remove(network);
        network = null;
      } else if (!network.tryLock()) {
        // CANNOT LOCK IT, MAYBE HASN'T BE CORRECTLY UNLOCKED BY PREVIOUS USER
        OLogManager.instance().error(this, "Removing locked network channel '%s'...", lastURL);
        engine.getConnectionManager().remove(network);
        network = null;
      }

    } while (network == null);
    return network;
  }

  /**
   * Starts listening the response.
   */
  protected void beginResponse(final OChannelBinaryAsynchClient iNetwork) throws IOException {
    byte[] newToken = iNetwork.beginResponse(getSessionId(), getSessionToken() != null);
    if (newToken != null && newToken.length > 0) {
      setSessionId(getServerURL(), getSessionId(), newToken);
    }
  }

  protected void getResponse(final OChannelBinaryAsynchClient iNetwork) throws IOException {
    try {
      beginResponse(iNetwork);
    } finally {
      endResponse(iNetwork);
    }
  }

  private boolean hideRecord(final ORecordId rid, int mode, final ORecordCallback<Boolean> callback,
      final OChannelBinaryAsynchClient network) throws IOException {
    try {

      network.writeRID(rid);
      network.writeByte((byte) mode);

    } finally {
      endRequest(network);
    }

    switch (mode) {
    case 0:
      // SYNCHRONOUS
      try {
        beginResponse(network);
        return network.readByte() == 1;
      } finally {
        endResponse(network);
      }

    case 1:
      // ASYNCHRONOUS
      if (callback != null) {
        final int sessionId = getSessionId();
        Callable<Object> response = new Callable<Object>() {
          public Object call() throws Exception {
            Boolean result;

            try {
              OStorageRemoteThreadLocal.INSTANCE.get().sessionId = sessionId;
              beginResponse(network);
              result = network.readByte() == 1;
            } finally {
              endResponse(network);
              OStorageRemoteThreadLocal.INSTANCE.get().sessionId = -1;
            }

            callback.call(rid, result);
            return null;
          }
        };
        asynchExecutor.submit(new FutureTask<Object>(response));
      }
    }
    return false;
  }

  private OPhysicalPosition[] readPhysicalPositions(OChannelBinaryAsynchClient network, int positionsCount) throws IOException {
    final OPhysicalPosition[] physicalPositions = new OPhysicalPosition[positionsCount];

    for (int i = 0; i < physicalPositions.length; i++) {
      final OPhysicalPosition position = new OPhysicalPosition();

      position.clusterPosition = network.readLong();
      position.recordSize = network.readInt();
      position.recordVersion = network.readVersion();

      physicalPositions[i] = position;
    }
    return physicalPositions;
  }

  private void readCollectionChanges(OChannelBinaryAsynchClient network, OSBTreeCollectionManager collectionManager)
      throws IOException {
    int count = network.readInt();

    for (int i = 0; i < count; i++) {
      final long mBitsOfId = network.readLong();
      final long lBitsOfId = network.readLong();

      final OBonsaiCollectionPointer pointer = OCollectionNetworkSerializer.INSTANCE.readCollectionPointer(network);

      if (collectionManager != null)
        collectionManager.updateCollectionPointer(new UUID(mBitsOfId, lBitsOfId), pointer);
    }

    if (ORecordSerializationContext.getDepth() <= 1 && collectionManager != null)
      collectionManager.clearPendingCollections();
  }

  private void commitEntry(final OChannelBinaryAsynchClient iNetwork, final ORecordOperation txEntry) throws IOException {
    if (txEntry.type == ORecordOperation.LOADED)
      // JUMP LOADED OBJECTS
      return;

    // SERIALIZE THE RECORD IF NEEDED. THIS IS DONE HERE TO CATCH EXCEPTION AND SEND A -1 AS ERROR TO THE SERVER TO SIGNAL THE ABORT
    // OF TX COMMIT
    byte[] stream = null;
    try {
      switch (txEntry.type) {
      case ORecordOperation.CREATED:
      case ORecordOperation.UPDATED:
        stream = txEntry.getRecord().toStream();
        break;
      }
    } catch (Exception e) {
      // ABORT TX COMMIT
      iNetwork.writeByte((byte) -1);
      throw new OTransactionException("Error on transaction commit", e);
    }

    iNetwork.writeByte((byte) 1);
    iNetwork.writeByte(txEntry.type);
    iNetwork.writeRID(txEntry.getRecord().getIdentity());
    iNetwork.writeByte(ORecordInternal.getRecordType(txEntry.getRecord()));

    switch (txEntry.type) {
    case ORecordOperation.CREATED:
      iNetwork.writeBytes(stream);
      break;

    case ORecordOperation.UPDATED:
      iNetwork.writeVersion(txEntry.getRecord().getRecordVersion());
      iNetwork.writeBytes(stream);
      if (iNetwork.getSrvProtocolVersion() >= 23)
        iNetwork.writeBoolean(ORecordInternal.isContentChanged(txEntry.getRecord()));
      break;

    case ORecordOperation.DELETED:
      iNetwork.writeVersion(txEntry.getRecord().getRecordVersion());
      break;
    }
  }

  private boolean handleDBFreeze() {
    boolean retry;
    OLogManager.instance().warn(this,
        "DB is frozen will wait for " + OGlobalConfiguration.CLIENT_DB_RELEASE_WAIT_TIMEOUT.getValue() + " ms. and then retry.");
    retry = true;
    try {
      Thread.sleep(OGlobalConfiguration.CLIENT_DB_RELEASE_WAIT_TIMEOUT.getValueAsInteger());
    } catch (InterruptedException ie) {
      retry = false;

      Thread.currentThread().interrupt();
    }
    return retry;
  }

  private void readDatabaseInformation(final OChannelBinaryAsynchClient network) throws IOException {
    // @COMPATIBILITY 1.0rc8
    final int tot = network.getSrvProtocolVersion() >= 7 ? network.readShort() : network.readInt();

    clusters = new OCluster[tot];
    clusterMap.clear();

    for (int i = 0; i < tot; ++i) {
      final OClusterRemote cluster = new OClusterRemote();
      String clusterName = network.readString();
      if (clusterName != null)
        clusterName = clusterName.toLowerCase();
      final int clusterId = network.readShort();

      if (network.getSrvProtocolVersion() < 24)
        network.readString();

      final int dataSegmentId = network.getSrvProtocolVersion() >= 12 && network.getSrvProtocolVersion() < 24 ? (int) network
          .readShort() : 0;

      cluster.configure(this, clusterId, clusterName);

      if (clusterId >= clusters.length)
        clusters = Arrays.copyOf(clusters, clusterId + 1);
      clusters[clusterId] = cluster;
      clusterMap.put(clusterName, cluster);
    }

    defaultClusterId = clusterMap.get(CLUSTER_DEFAULT_NAME).getId();
  }

  private boolean deleteRecord(final ORecordId iRid, ORecordVersion iVersion, int iMode, final ORecordCallback<Boolean> iCallback,
      final OChannelBinaryAsynchClient network) throws IOException {
    try {

      network.writeRID(iRid);
      network.writeVersion(iVersion);
      network.writeByte((byte) iMode);

    } finally {
      endRequest(network);
    }

    switch (iMode) {
    case 0:
      // SYNCHRONOUS
      try {
        beginResponse(network);
        return network.readByte() == 1;
      } finally {
        endResponse(network);
      }

    case 1:
      // ASYNCHRONOUS
      if (iCallback != null) {
        final int sessionId = getSessionId();
        Callable<Object> response = new Callable<Object>() {
          public Object call() throws Exception {
            Boolean result;

            try {
              OStorageRemoteThreadLocal.INSTANCE.get().sessionId = sessionId;
              beginResponse(network);
              result = network.readByte() == 1;
            } finally {
              endResponse(network);
              OStorageRemoteThreadLocal.INSTANCE.get().sessionId = -1;
            }

            iCallback.call(iRid, result);
            return null;
          }
        };
        asynchExecutor.submit(new FutureTask<Object>(response));
      }
    }
    return false;
  }
}


File: client/src/main/java/com/orientechnologies/orient/client/remote/OStorageRemoteThread.java
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
package com.orientechnologies.orient.client.remote;

import com.orientechnologies.common.concur.resource.OSharedResourceAdaptiveExternal;
import com.orientechnologies.orient.core.Orient;
import com.orientechnologies.orient.core.command.OCommandOutputListener;
import com.orientechnologies.orient.core.command.OCommandRequestText;
import com.orientechnologies.orient.core.config.OStorageConfiguration;
import com.orientechnologies.orient.core.conflict.ORecordConflictStrategy;
import com.orientechnologies.orient.core.db.record.OCurrentStorageComponentsFactory;
import com.orientechnologies.orient.core.db.record.ridbag.sbtree.OSBTreeCollectionManager;
import com.orientechnologies.orient.core.exception.ORecordNotFoundException;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.id.ORecordId;
import com.orientechnologies.orient.core.record.impl.ODocument;
import com.orientechnologies.orient.core.storage.OCluster;
import com.orientechnologies.orient.core.storage.OPhysicalPosition;
import com.orientechnologies.orient.core.storage.ORawBuffer;
import com.orientechnologies.orient.core.storage.ORecordCallback;
import com.orientechnologies.orient.core.storage.ORecordMetadata;
import com.orientechnologies.orient.core.storage.OStorage;
import com.orientechnologies.orient.core.storage.OStorageOperationResult;
import com.orientechnologies.orient.core.storage.OStorageProxy;
import com.orientechnologies.orient.core.tx.OTransaction;
import com.orientechnologies.orient.core.version.ORecordVersion;
import com.orientechnologies.orient.core.version.OVersionFactory;
import com.orientechnologies.orient.enterprise.channel.binary.OChannelBinaryAsynchClient;
import com.orientechnologies.orient.enterprise.channel.binary.ORemoteServerEventListener;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Collection;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Wrapper of OStorageRemote that maintains the sessionId. It's bound to the ODatabase and allow to use the shared OStorageRemote.
 */
@SuppressWarnings("unchecked")
public class OStorageRemoteThread implements OStorageProxy {
  private static AtomicInteger sessionSerialId = new AtomicInteger(-1);

  private final OStorageRemote delegate;
  private String               serverURL;
  private int                  sessionId;
  private byte[]               token;

  public OStorageRemoteThread(final OStorageRemote iSharedStorage) {
    delegate = iSharedStorage;
    serverURL = null;
    sessionId = sessionSerialId.decrementAndGet();
  }

  public OStorageRemoteThread(final OStorageRemote iSharedStorage, final int iSessionId) {
    delegate = iSharedStorage;
    serverURL = null;
    sessionId = iSessionId;
  }

  public static int getNextConnectionId() {
    return sessionSerialId.decrementAndGet();
  }

  public void open(final String iUserName, final String iUserPassword, final Map<String, Object> iOptions) {
    pushSession();
    try {
      delegate.open(iUserName, iUserPassword, iOptions);
    } finally {
      popSession();
    }
  }

  @Override
  public boolean isDistributed() {
    return delegate.isDistributed();
  }

  @Override
  public Class<? extends OSBTreeCollectionManager> getCollectionManagerClass() {
    return delegate.getCollectionManagerClass();
  }

  public void create(final Map<String, Object> iOptions) {
    pushSession();
    try {
      delegate.create(iOptions);
    } finally {
      popSession();
    }
  }

  public void close(boolean iForce, boolean onDelete) {
    pushSession();
    try {
      delegate.close(iForce, false);
      Orient.instance().unregisterStorage(this);
    } finally {
      popSession();
    }
  }

  public boolean dropCluster(final String iClusterName, final boolean iTruncate) {
    pushSession();
    try {
      return delegate.dropCluster(iClusterName, iTruncate);
    } finally {
      popSession();
    }
  }

  public int getUsers() {
    pushSession();
    try {
      return delegate.getUsers();
    } finally {
      popSession();
    }
  }

  public int addUser() {
    pushSession();
    try {
      return delegate.addUser();
    } finally {
      popSession();
    }
  }

  public OSharedResourceAdaptiveExternal getLock() {
    pushSession();
    try {
      return delegate.getLock();
    } finally {
      popSession();
    }
  }

  public void setSessionId(final String iServerURL, final int iSessionId, byte[] iToken) {
    serverURL = iServerURL;
    sessionId = iSessionId;
    token = iToken;
    delegate.setSessionId(serverURL, iSessionId, iToken);
  }

  public void reload() {
    pushSession();
    try {
      delegate.reload();
    } finally {
      popSession();
    }
  }

  public boolean exists() {
    pushSession();
    try {
      return delegate.exists();
    } finally {
      popSession();
    }
  }

  public int removeUser() {
    pushSession();
    try {
      return delegate.removeUser();
    } finally {
      popSession();
    }
  }

  public void close() {
    pushSession();
    try {
      delegate.close();

      Orient.instance().unregisterStorage(this);
    } finally {
      popSession();
    }
  }

  public void delete() {
    pushSession();
    try {
      delegate.delete();
      Orient.instance().unregisterStorage(this);
    } finally {
      popSession();
    }
  }

  @Override
  public OStorage getUnderlying() {
    return delegate;
  }

  public Set<String> getClusterNames() {
    pushSession();
    try {
      return delegate.getClusterNames();
    } finally {
      popSession();
    }
  }

  @Override
  public void backup(OutputStream out, Map<String, Object> options, final Callable<Object> callable,
      final OCommandOutputListener iListener, int compressionLevel, int bufferSize) throws IOException {
    throw new UnsupportedOperationException("backup");
  }

  @Override
  public void restore(InputStream in, Map<String, Object> options, final Callable<Object> callable,
      final OCommandOutputListener iListener) throws IOException {
    throw new UnsupportedOperationException("restore");
  }

  public OStorageOperationResult<OPhysicalPosition> createRecord(final ORecordId iRid, final byte[] iContent,
      ORecordVersion iRecordVersion, final byte iRecordType, final int iMode, ORecordCallback<Long> iCallback) {
    pushSession();
    try {
      return delegate.createRecord(iRid, iContent, OVersionFactory.instance().createVersion(), iRecordType, iMode, iCallback);
    } finally {
      popSession();
    }
  }

  public OStorageOperationResult<ORawBuffer> readRecord(final ORecordId iRid, final String iFetchPlan, boolean iIgnoreCache,
      ORecordCallback<ORawBuffer> iCallback) {
    pushSession();
    try {
      return delegate.readRecord(iRid, iFetchPlan, iIgnoreCache, null);
    } finally {
      popSession();
    }
  }

  @Override
  public OStorageOperationResult<ORawBuffer> readRecordIfVersionIsNotLatest(ORecordId rid, String fetchPlan, boolean ignoreCache,
      ORecordVersion recordVersion) throws ORecordNotFoundException {
    pushSession();
    try {
      return delegate.readRecordIfVersionIsNotLatest(rid, fetchPlan, ignoreCache, recordVersion);
    } finally {
      popSession();
    }
  }

  public OStorageOperationResult<ORecordVersion> updateRecord(final ORecordId iRid, boolean updateContent, final byte[] iContent,
      final ORecordVersion iVersion, final byte iRecordType, final int iMode, ORecordCallback<ORecordVersion> iCallback) {
    pushSession();
    try {
      return delegate.updateRecord(iRid, updateContent, iContent, iVersion, iRecordType, iMode, iCallback);
    } finally {
      popSession();
    }
  }

  public OStorageOperationResult<Boolean> deleteRecord(final ORecordId iRid, final ORecordVersion iVersion, final int iMode,
      ORecordCallback<Boolean> iCallback) {
    pushSession();
    try {
      return delegate.deleteRecord(iRid, iVersion, iMode, iCallback);
    } finally {
      popSession();
    }
  }

  @Override
  public OStorageOperationResult<Boolean> hideRecord(ORecordId recordId, int mode, ORecordCallback<Boolean> callback) {
    pushSession();
    try {
      return delegate.hideRecord(recordId, mode, callback);
    } finally {
      popSession();
    }
  }

  @Override
  public OCluster getClusterByName(String clusterName) {
    return delegate.getClusterByName(clusterName);
  }

  @Override
  public ORecordConflictStrategy getConflictStrategy() {
    throw new UnsupportedOperationException("getConflictStrategy");
  }

  @Override
  public void setConflictStrategy(ORecordConflictStrategy iResolver) {
    throw new UnsupportedOperationException("setConflictStrategy");
  }

  @Override
  public ORecordMetadata getRecordMetadata(ORID rid) {
    pushSession();
    try {
      return delegate.getRecordMetadata(rid);
    } finally {
      popSession();
    }
  }

  @Override
  public boolean cleanOutRecord(ORecordId recordId, ORecordVersion recordVersion, int iMode, ORecordCallback<Boolean> callback) {
    pushSession();
    try {
      return delegate.cleanOutRecord(recordId, recordVersion, iMode, callback);
    } finally {
      popSession();
    }
  }

  public long count(final int iClusterId) {
    pushSession();
    try {
      return delegate.count(iClusterId);
    } finally {
      popSession();
    }
  }

  @Override
  public long count(int iClusterId, boolean countTombstones) {
    pushSession();
    try {
      return delegate.count(iClusterId, countTombstones);
    } finally {
      popSession();
    }
  }

  @Override
  public long count(int[] iClusterIds, boolean countTombstones) {
    pushSession();
    try {
      return delegate.count(iClusterIds, countTombstones);
    } finally {
      popSession();
    }
  }

  public String toString() {
    return delegate.toString();
  }

  public long[] getClusterDataRange(final int iClusterId) {
    pushSession();
    try {
      return delegate.getClusterDataRange(iClusterId);
    } finally {
      popSession();
    }
  }

  @Override
  public OPhysicalPosition[] higherPhysicalPositions(int currentClusterId, OPhysicalPosition physicalPosition) {
    pushSession();
    try {
      return delegate.higherPhysicalPositions(currentClusterId, physicalPosition);
    } finally {
      popSession();
    }
  }

  @Override
  public OPhysicalPosition[] lowerPhysicalPositions(int currentClusterId, OPhysicalPosition physicalPosition) {
    pushSession();
    try {
      return delegate.lowerPhysicalPositions(currentClusterId, physicalPosition);
    } finally {
      popSession();
    }
  }

  @Override
  public OPhysicalPosition[] ceilingPhysicalPositions(int clusterId, OPhysicalPosition physicalPosition) {
    pushSession();
    try {
      return delegate.ceilingPhysicalPositions(clusterId, physicalPosition);
    } finally {
      popSession();
    }
  }

  @Override
  public OPhysicalPosition[] floorPhysicalPositions(int clusterId, OPhysicalPosition physicalPosition) {
    pushSession();
    try {
      return delegate.floorPhysicalPositions(clusterId, physicalPosition);
    } finally {
      popSession();
    }
  }

  public long getSize() {
    pushSession();
    try {
      return delegate.getSize();
    } finally {
      popSession();
    }
  }

  public long countRecords() {
    pushSession();
    try {
      return delegate.countRecords();
    } finally {
      popSession();
    }
  }

  public long count(final int[] iClusterIds) {
    pushSession();
    try {
      return delegate.count(iClusterIds);
    } finally {
      popSession();
    }
  }

  public Object command(final OCommandRequestText iCommand) {
    pushSession();
    try {
      return delegate.command(iCommand);
    } finally {
      popSession();
    }
  }

  public void commit(final OTransaction iTx, Runnable callback) {
    pushSession();
    try {
      delegate.commit(iTx, null);
    } finally {
      popSession();
    }
  }

  public void rollback(OTransaction iTx) {
    pushSession();
    try {
      delegate.rollback(iTx);
    } finally {
      popSession();
    }
  }

  public int getClusterIdByName(final String iClusterName) {
    pushSession();
    try {
      return delegate.getClusterIdByName(iClusterName);
    } finally {
      popSession();
    }
  }

  public int getDefaultClusterId() {
    pushSession();
    try {
      return delegate.getDefaultClusterId();
    } finally {
      popSession();
    }
  }

  public void setDefaultClusterId(final int defaultClusterId) {
    pushSession();
    try {
      delegate.setDefaultClusterId(defaultClusterId);
    } finally {
      popSession();
    }
  }

  public int addCluster(final String iClusterName, boolean forceListBased, final Object... iArguments) {
    pushSession();
    try {
      return delegate.addCluster(iClusterName, false, iArguments);
    } finally {
      popSession();
    }
  }

  public int addCluster(String iClusterName, int iRequestedId, boolean forceListBased, Object... iParameters) {
    pushSession();
    try {
      return delegate.addCluster(iClusterName, iRequestedId, forceListBased, iParameters);
    } finally {
      popSession();
    }
  }

  public boolean dropCluster(final int iClusterId, final boolean iTruncate) {
    pushSession();
    try {
      return delegate.dropCluster(iClusterId, iTruncate);
    } finally {
      popSession();
    }
  }

  public void synch() {
    pushSession();
    try {
      delegate.synch();
    } finally {
      popSession();
    }
  }

  public String getPhysicalClusterNameById(final int iClusterId) {
    pushSession();
    try {
      return delegate.getPhysicalClusterNameById(iClusterId);
    } finally {
      popSession();
    }
  }

  public int getClusters() {
    pushSession();
    try {
      return delegate.getClusterMap();
    } finally {
      popSession();
    }
  }

  public Collection<OCluster> getClusterInstances() {
    pushSession();
    try {
      return delegate.getClusterInstances();
    } finally {
      popSession();
    }
  }

  public OCluster getClusterById(final int iId) {
    pushSession();
    try {
      return delegate.getClusterById(iId);
    } finally {
      popSession();
    }
  }

  public long getVersion() {
    pushSession();
    try {
      return delegate.getVersion();
    } finally {
      popSession();
    }
  }

  public boolean isPermanentRequester() {
    pushSession();
    try {
      return delegate.isPermanentRequester();
    } finally {
      popSession();
    }
  }

  public void updateClusterConfiguration(final String iCurrentURL, final byte[] iContent) {
    pushSession();
    try {
      delegate.updateClusterConfiguration(iCurrentURL, iContent);
    } finally {
      popSession();
    }
  }

  public OStorageConfiguration getConfiguration() {
    pushSession();
    try {
      return delegate.getConfiguration();
    } finally {
      popSession();
    }
  }

  public boolean isClosed() {
    return (sessionId < 0 && token == null) || delegate.isClosed();
  }

  public boolean checkForRecordValidity(final OPhysicalPosition ppos) {
    pushSession();
    try {
      return delegate.checkForRecordValidity(ppos);
    } finally {
      popSession();
    }
  }

  @Override
  public boolean isAssigningClusterIds() {
    return false;
  }

  public String getName() {
    pushSession();
    try {
      return delegate.getName();
    } finally {
      popSession();
    }
  }

  public String getURL() {
    return delegate.getURL();
  }

  public void beginResponse(final OChannelBinaryAsynchClient iNetwork) throws IOException {
    pushSession();
    try {
      delegate.beginResponse(iNetwork);
    } finally {
      popSession();
    }
  }

  @Override
  public OCurrentStorageComponentsFactory getComponentsFactory() {
    return delegate.getComponentsFactory();
  }

  @Override
  public long getLastOperationId() {
    return 0;
  }

  public boolean existsResource(final String iName) {
    return delegate.existsResource(iName);
  }

  public synchronized <T> T getResource(final String iName, final Callable<T> iCallback) {
    return (T) delegate.getResource(iName, iCallback);
  }

  public <T> T removeResource(final String iName) {
    return (T) delegate.removeResource(iName);
  }

  public ODocument getClusterConfiguration() {
    return delegate.getClusterConfiguration();
  }

  public <V> V callInLock(final Callable<V> iCallable, final boolean iExclusiveLock) {
    return delegate.callInLock(iCallable, iExclusiveLock);
  }

  public ORemoteServerEventListener getRemoteServerEventListener() {
    return delegate.getAsynchEventListener();
  }

  public void setRemoteServerEventListener(final ORemoteServerEventListener iListener) {
    delegate.setAsynchEventListener(iListener);
  }

  public void removeRemoteServerEventListener() {
    delegate.removeRemoteServerEventListener();
  }

  @Override
  public void checkForClusterPermissions(final String iClusterName) {
    delegate.checkForClusterPermissions(iClusterName);
  }

  public STATUS getStatus() {
    return delegate.getStatus();
  }

  @Override
  public String getUserName() {
    return delegate.getUserName();
  }

  @Override
  public String getType() {
    return delegate.getType();
  }

  @Override
  public boolean equals(final Object iOther) {
    if (iOther instanceof OStorageRemoteThread)
      return iOther == this;

    if (iOther instanceof OStorageRemote)
      return iOther == delegate;

    return false;
  }

  protected void handleException(final OChannelBinaryAsynchClient iNetwork, final String iMessage, final Exception iException) {
    delegate.handleException(iNetwork, iMessage, iException);
  }

  protected void pushSession() {
    delegate.setSessionId(serverURL, sessionId, token);
  }

  protected void popSession() {
    serverURL = delegate.getServerURL();
    sessionId = delegate.getSessionId();
    token = delegate.getSessionToken();
    // delegate.clearSession();
  }
}


File: core/src/main/java/com/orientechnologies/orient/core/index/OIndexRemote.java
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
package com.orientechnologies.orient.core.index;

import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.orientechnologies.common.listener.OProgressListener;
import com.orientechnologies.orient.core.command.OCommandRequest;
import com.orientechnologies.orient.core.db.ODatabase;
import com.orientechnologies.orient.core.db.ODatabaseRecordThreadLocal;
import com.orientechnologies.orient.core.db.record.OIdentifiable;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.metadata.schema.OType;
import com.orientechnologies.orient.core.record.ORecord;
import com.orientechnologies.orient.core.record.impl.ODocument;
import com.orientechnologies.orient.core.sql.OCommandSQL;

/**
 * Proxied abstract index.
 * 
 * @author Luca Garulli
 * 
 */
@SuppressWarnings("unchecked")
public abstract class OIndexRemote<T> implements OIndex<T> {
  public static final String    QUERY_GET_VALUES_BEETWEN_SELECT                   = "select from index:%s where ";
  public static final String    QUERY_GET_VALUES_BEETWEN_INCLUSIVE_FROM_CONDITION = "key >= ?";
  public static final String    QUERY_GET_VALUES_BEETWEN_EXCLUSIVE_FROM_CONDITION = "key > ?";
  public static final String    QUERY_GET_VALUES_BEETWEN_INCLUSIVE_TO_CONDITION   = "key <= ?";
  public static final String    QUERY_GET_VALUES_BEETWEN_EXCLUSIVE_TO_CONDITION   = "key < ?";
  public static final String    QUERY_GET_VALUES_AND_OPERATOR                     = " and ";
  public static final String    QUERY_GET_VALUES_LIMIT                            = " limit ";
  protected final static String QUERY_ENTRIES                                     = "select key, rid from index:%s";
  protected final static String QUERY_ENTRIES_DESC                                = "select key, rid from index:%s order by key desc";

  private final static String   QUERY_GET_ENTRIES                                 = "select from index:%s where key in [%s]";

  private final static String   QUERY_PUT                                         = "insert into index:%s (key,rid) values (?,?)";
  private final static String   QUERY_REMOVE                                      = "delete from index:%s where key = ?";
  private final static String   QUERY_REMOVE2                                     = "delete from index:%s where key = ? and rid = ?";
  private final static String   QUERY_REMOVE3                                     = "delete from index:%s where rid = ?";
  private final static String   QUERY_CONTAINS                                    = "select count(*) as size from index:%s where key = ?";
  private final static String   QUERY_COUNT                                       = "select count(*) as size from index:%s where key = ?";
  private final static String   QUERY_COUNT_RANGE                                 = "select count(*) as size from index:%s where ";
  private final static String   QUERY_SIZE                                        = "select count(*) as size from index:%s";
  private final static String   QUERY_KEY_SIZE                                    = "select count(distinct( key )) as size from index:%s";
  private final static String   QUERY_KEYS                                        = "select key from index:%s";
  private final static String   QUERY_REBUILD                                     = "rebuild index %s";
  private final static String   QUERY_CLEAR                                       = "delete from index:%s";
  private final static String   QUERY_DROP                                        = "drop index %s";
  protected final String        databaseName;
  private final String          wrappedType;
  private final ORID            rid;
  protected OIndexDefinition    indexDefinition;
  protected String              name;
  protected ODocument           configuration;
  protected Set<String>         clustersToIndex;

  public OIndexRemote(final String iName, final String iWrappedType, final ORID iRid, final OIndexDefinition iIndexDefinition,
      final ODocument iConfiguration, final Set<String> clustersToIndex) {
    this.name = iName;
    this.wrappedType = iWrappedType;
    this.rid = iRid;
    this.indexDefinition = iIndexDefinition;
    this.configuration = iConfiguration;
    this.clustersToIndex = new HashSet<String>(clustersToIndex);
    this.databaseName = ODatabaseRecordThreadLocal.INSTANCE.get().getName();
  }

  public OIndexRemote<T> create(final String name, final OIndexDefinition indexDefinition, final String clusterIndexName,
      final Set<String> clustersToIndex, boolean rebuild, final OProgressListener progressListener) {
    this.name = name;
    return this;
  }

  public OIndexRemote<T> delete() {
    final OCommandRequest cmd = formatCommand(QUERY_DROP, name);
    getDatabase().command(cmd).execute();
    return this;
  }

  @Override
  public void deleteWithoutIndexLoad(String indexName) {
    throw new UnsupportedOperationException("deleteWithoutIndexLoad");
  }

  public String getDatabaseName() {
    return databaseName;
  }

  public boolean contains(final Object iKey) {
    final OCommandRequest cmd = formatCommand(QUERY_CONTAINS, name);
    final List<ODocument> result = getDatabase().command(cmd).execute(iKey);
    return (Long) result.get(0).field("size") > 0;
  }

  public long count(final Object iKey) {
    final OCommandRequest cmd = formatCommand(QUERY_COUNT, name);
    final List<ODocument> result = getDatabase().command(cmd).execute(iKey);
    return (Long) result.get(0).field("size");
  }

  public long count(final Object iRangeFrom, final boolean iFromInclusive, final Object iRangeTo, final boolean iToInclusive,
      final int maxValuesToFetch) {
    final StringBuilder query = new StringBuilder(QUERY_COUNT_RANGE);

    if (iFromInclusive)
      query.append(QUERY_GET_VALUES_BEETWEN_INCLUSIVE_FROM_CONDITION);
    else
      query.append(QUERY_GET_VALUES_BEETWEN_EXCLUSIVE_FROM_CONDITION);

    query.append(QUERY_GET_VALUES_AND_OPERATOR);

    if (iToInclusive)
      query.append(QUERY_GET_VALUES_BEETWEN_INCLUSIVE_TO_CONDITION);
    else
      query.append(QUERY_GET_VALUES_BEETWEN_EXCLUSIVE_TO_CONDITION);

    if (maxValuesToFetch > 0)
      query.append(QUERY_GET_VALUES_LIMIT).append(maxValuesToFetch);

    final OCommandRequest cmd = formatCommand(query.toString());
    return (Long) getDatabase().command(cmd).execute(iRangeFrom, iRangeTo);
  }

  public OIndexRemote<T> put(final Object iKey, final OIdentifiable iValue) {
    if (iValue instanceof ORecord && !iValue.getIdentity().isValid())
      // SAVE IT BEFORE TO PUT
      ((ORecord) iValue).save();

    if (iValue.getIdentity().isNew())
      throw new OIndexException(
          "Cannot insert values in manual indexes against remote protocol during a transaction. Temporary RID cannot be managed at server side");

    final OCommandRequest cmd = formatCommand(QUERY_PUT, name);
    getDatabase().command(cmd).execute(iKey, iValue.getIdentity());
    return this;
  }

  public boolean remove(final Object key) {
    final OCommandRequest cmd = formatCommand(QUERY_REMOVE, name);
    return ((Integer) getDatabase().command(cmd).execute(key)) > 0;
  }

  public boolean remove(final Object iKey, final OIdentifiable iRID) {
    final int deleted;
    if (iRID != null) {

      if (iRID.getIdentity().isNew())
        throw new OIndexException(
            "Cannot remove values in manual indexes against remote protocol during a transaction. Temporary RID cannot be managed at server side");

      final OCommandRequest cmd = formatCommand(QUERY_REMOVE2, name);
      deleted = (Integer) getDatabase().command(cmd).execute(iKey, iRID);
    } else {
      final OCommandRequest cmd = formatCommand(QUERY_REMOVE, name);
      deleted = (Integer) getDatabase().command(cmd).execute(iKey);
    }
    return deleted > 0;
  }

  public int remove(final OIdentifiable iRecord) {
    final OCommandRequest cmd = formatCommand(QUERY_REMOVE3, name, iRecord.getIdentity());
    return (Integer) getDatabase().command(cmd).execute(iRecord);
  }

  public void automaticRebuild() {
    throw new UnsupportedOperationException("autoRebuild()");
  }

  public long rebuild() {
    final OCommandRequest cmd = formatCommand(QUERY_REBUILD, name);
    return (Long) getDatabase().command(cmd).execute();
  }

  public OIndexRemote<T> clear() {
    final OCommandRequest cmd = formatCommand(QUERY_CLEAR, name);
    getDatabase().command(cmd).execute();
    return this;
  }

  public long getSize() {
    final OCommandRequest cmd = formatCommand(QUERY_SIZE, name);
    final List<ODocument> result = getDatabase().command(cmd).execute();
    return (Long) result.get(0).field("size");
  }

  public long getKeySize() {
    final OCommandRequest cmd = formatCommand(QUERY_KEY_SIZE, name);
    final List<ODocument> result = getDatabase().command(cmd).execute();
    return (Long) result.get(0).field("size");
  }

  public boolean isAutomatic() {
    return indexDefinition != null && indexDefinition.getClassName() != null;
  }

  public String getName() {
    return name;
  }

  @Override
  public void flush() {
  }

  public String getType() {
    return wrappedType;
  }

  public ODocument getConfiguration() {
    return configuration;
  }

  @Override
  public ODocument getMetadata() {
    return configuration.field("metadata", OType.EMBEDDED);
  }

  public ORID getIdentity() {
    return rid;
  }

  public void commit(final ODocument iDocument) {
  }

  public OIndexInternal<T> getInternal() {
    return null;
  }

  public long rebuild(final OProgressListener iProgressListener) {
    return rebuild();
  }

  public OType[] getKeyTypes() {
    if (indexDefinition != null)
      return indexDefinition.getTypes();
    return null;
  }

  public Collection<ODocument> getEntries(final Collection<?> iKeys) {
    final StringBuilder params = new StringBuilder(128);
    if (!iKeys.isEmpty()) {
      params.append("?");
      for (int i = 1; i < iKeys.size(); i++) {
        params.append(", ?");
      }
    }

    final OCommandRequest cmd = formatCommand(QUERY_GET_ENTRIES, name, params.toString());
    return (Collection<ODocument>) getDatabase().command(cmd).execute(iKeys.toArray());
  }

  public OIndexDefinition getDefinition() {
    return indexDefinition;
  }

  @Override
  public boolean equals(final Object o) {
    if (this == o)
      return true;
    if (o == null || getClass() != o.getClass())
      return false;

    final OIndexRemote<?> that = (OIndexRemote<?>) o;

    return name.equals(that.name);
  }

  @Override
  public int hashCode() {
    return name.hashCode();
  }

  public Collection<ODocument> getEntries(final Collection<?> iKeys, int maxEntriesToFetch) {
    if (maxEntriesToFetch < 0)
      return getEntries(iKeys);

    final StringBuilder params = new StringBuilder(128);
    if (!iKeys.isEmpty()) {
      params.append("?");
      for (int i = 1; i < iKeys.size(); i++) {
        params.append(", ?");
      }
    }

    final OCommandRequest cmd = formatCommand(QUERY_GET_ENTRIES + QUERY_GET_VALUES_LIMIT + maxEntriesToFetch, name,
        params.toString());
    return getDatabase().command(cmd).execute(iKeys.toArray());
  }

  public Set<String> getClusters() {
    return Collections.unmodifiableSet(clustersToIndex);
  }

  public ODocument checkEntry(final OIdentifiable iRecord, final Object iKey) {
    return null;
  }

  @Override
  public boolean isRebuiding() {
    return false;
  }

  @Override
  public Object getFirstKey() {
    throw new UnsupportedOperationException("getFirstKey");
  }

  @Override
  public Object getLastKey() {
    throw new UnsupportedOperationException("getLastKey");
  }

  @Override
  public OIndexCursor iterateEntriesBetween(Object fromKey, boolean fromInclusive, Object toKey, boolean toInclusive,
      boolean ascOrder) {
    throw new UnsupportedOperationException("iterateEntriesBetween");
  }

  @Override
  public OIndexCursor iterateEntriesMajor(Object fromKey, boolean fromInclusive, boolean ascOrder) {
    throw new UnsupportedOperationException("iterateEntriesMajor");
  }

  @Override
  public OIndexCursor iterateEntriesMinor(Object toKey, boolean toInclusive, boolean ascOrder) {
    throw new UnsupportedOperationException("iterateEntriesMinor");
  }

  @Override
  public OIndexCursor iterateEntries(Collection<?> keys, boolean ascSortOrder) {
    throw new UnsupportedOperationException("iterateEntries");
  }

  @Override
  public OIndexCursor cursor() {
    final OCommandRequest cmd = formatCommand(QUERY_ENTRIES, name);
    final Collection<ODocument> result = getDatabase().command(cmd).execute();

    return new OIndexAbstractCursor() {
      private final Iterator<ODocument> documentIterator = result.iterator();

      @Override
      public Map.Entry<Object, OIdentifiable> nextEntry() {
        if (!documentIterator.hasNext())
          return null;

        final ODocument value = documentIterator.next();

        return new Map.Entry<Object, OIdentifiable>() {
          @Override
          public Object getKey() {
            return value.field("key");
          }

          @Override
          public OIdentifiable getValue() {
            return value.field("rid");
          }

          @Override
          public OIdentifiable setValue(OIdentifiable value) {
            throw new UnsupportedOperationException("setValue");
          }
        };
      }
    };

  }

  @Override
  public OIndexCursor descCursor() {
    final OCommandRequest cmd = formatCommand(QUERY_ENTRIES_DESC, name);
    final Collection<ODocument> result = getDatabase().command(cmd).execute();

    return new OIndexAbstractCursor() {
      private final Iterator<ODocument> documentIterator = result.iterator();

      @Override
      public Map.Entry<Object, OIdentifiable> nextEntry() {
        if (!documentIterator.hasNext())
          return null;

        final ODocument value = documentIterator.next();

        return new Map.Entry<Object, OIdentifiable>() {
          @Override
          public Object getKey() {
            return value.field("key");
          }

          @Override
          public OIdentifiable getValue() {
            return value.field("rid");
          }

          @Override
          public OIdentifiable setValue(OIdentifiable value) {
            throw new UnsupportedOperationException("setValue");
          }
        };
      }
    };
  }

  @Override
  public OIndexKeyCursor keyCursor() {
    final OCommandRequest cmd = formatCommand(QUERY_KEYS, name);
    final Collection<ODocument> result = getDatabase().command(cmd).execute();

    return new OIndexKeyCursor() {
      private final Iterator<ODocument> documentIterator = result.iterator();

      @Override
      public Map.Entry<Object, OIdentifiable> next(int prefetchSize) {
        if (!documentIterator.hasNext())
          return null;

        final ODocument value = documentIterator.next();

        return value.field("key");
      }
    };
  }

	@Override
	public int compareTo(OIndex<T> index) {
		final String name = index.getName();
		return this.name.compareTo(name);
	}


	protected OCommandRequest formatCommand(final String iTemplate, final Object... iArgs) {
    final String text = String.format(iTemplate, iArgs);
    return new OCommandSQL(text);
  }

  protected ODatabase<ORecord> getDatabase() {
    return ODatabaseRecordThreadLocal.INSTANCE.get();
  }
}


File: core/src/main/java/com/orientechnologies/orient/core/index/OIndexRemoteMultiValue.java
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
package com.orientechnologies.orient.core.index;

import java.util.Collection;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.ListIterator;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

import com.orientechnologies.orient.core.command.OCommandRequest;
import com.orientechnologies.orient.core.db.record.OIdentifiable;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.metadata.schema.OType;
import com.orientechnologies.orient.core.record.impl.ODocument;

/**
 * Proxied index.
 * 
 * @author Luca Garulli
 * 
 */
@SuppressWarnings("unchecked")
public class OIndexRemoteMultiValue extends OIndexRemote<Collection<OIdentifiable>> {
  protected final static String QUERY_GET = "select EXPAND( rid ) from index:%s where key = ?";

  public OIndexRemoteMultiValue(final String iName, final String iWrappedType, final ORID iRid,
      final OIndexDefinition iIndexDefinition, final ODocument iConfiguration, final Set<String> clustersToIndex) {
    super(iName, iWrappedType, iRid, iIndexDefinition, iConfiguration, clustersToIndex);
  }

  public Collection<OIdentifiable> get(final Object iKey) {
    final OCommandRequest cmd = formatCommand(QUERY_GET, name);
    return new HashSet<OIdentifiable>((Collection<OIdentifiable>) getDatabase().command(cmd).execute(iKey));
  }

  public Iterator<Entry<Object, Collection<OIdentifiable>>> iterator() {
    final OCommandRequest cmd = formatCommand(QUERY_ENTRIES, name);
    final Collection<ODocument> result = getDatabase().command(cmd).execute();

    final Map<Object, Collection<OIdentifiable>> map = new LinkedHashMap<Object, Collection<OIdentifiable>>();
    for (final ODocument d : result) {
      d.setLazyLoad(false);
      Collection<OIdentifiable> rids = map.get(d.field("key"));
      if (rids == null) {
        rids = new HashSet<OIdentifiable>();
        map.put(d.field("key"), rids);
      }

      rids.add((OIdentifiable) d.field("rid"));
    }

    return map.entrySet().iterator();
  }

  public Iterator<Entry<Object, Collection<OIdentifiable>>> inverseIterator() {
    final OCommandRequest cmd = formatCommand(QUERY_ENTRIES, name);
    final List<ODocument> result = getDatabase().command(cmd).execute();

    final Map<Object, Collection<OIdentifiable>> map = new LinkedHashMap<Object, Collection<OIdentifiable>>();
    for (ListIterator<ODocument> it = result.listIterator(); it.hasPrevious();) {
      ODocument d = it.previous();
      d.setLazyLoad(false);
      Collection<OIdentifiable> rids = map.get(d.field("key"));
      if (rids == null) {
        rids = new HashSet<OIdentifiable>();
        map.put(d.field("key"), rids);
      }

      rids.add((OIdentifiable) d.field("rid"));
    }

    return map.entrySet().iterator();
  }

  public Iterator<OIdentifiable> valuesIterator() {
    throw new UnsupportedOperationException();
  }

  public Iterator<OIdentifiable> valuesInverseIterator() {
    throw new UnsupportedOperationException();
  }

  @Override
  public boolean supportsOrderedIterations() {
    return false;
  }
}


File: core/src/main/java/com/orientechnologies/orient/core/index/OIndexRemoteOneValue.java
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
package com.orientechnologies.orient.core.index;

import java.util.Collection;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.ListIterator;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

import com.orientechnologies.orient.core.command.OCommandRequest;
import com.orientechnologies.orient.core.db.record.OIdentifiable;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.metadata.schema.OType;
import com.orientechnologies.orient.core.record.impl.ODocument;

/**
 * Proxied single value index.
 * 
 * @author Luca Garulli
 * 
 */
public class OIndexRemoteOneValue extends OIndexRemote<OIdentifiable> {
  protected final static String QUERY_GET = "select rid from index:%s where key = ?";

  public OIndexRemoteOneValue(final String iName, final String iWrappedType, final ORID iRid,
      final OIndexDefinition iIndexDefinition, final ODocument iConfiguration, final Set<String> clustersToIndex) {
    super(iName, iWrappedType, iRid, iIndexDefinition, iConfiguration, clustersToIndex);
  }

  public OIdentifiable get(final Object iKey) {
    final OCommandRequest cmd = formatCommand(QUERY_GET, name);
    final List<OIdentifiable> result = getDatabase().command(cmd).execute(iKey);
    if (result != null && !result.isEmpty())
      return ((OIdentifiable) ((ODocument) result.get(0).getRecord()).field("rid")).getIdentity();
    return null;
  }

  public Iterator<Entry<Object, OIdentifiable>> iterator() {
    final OCommandRequest cmd = formatCommand(QUERY_ENTRIES, name);
    final Collection<ODocument> result = getDatabase().command(cmd).execute();

    final Map<Object, OIdentifiable> map = new LinkedHashMap<Object, OIdentifiable>();
    for (final ODocument d : result) {
      d.setLazyLoad(false);
      map.put(d.field("key"), (OIdentifiable) d.field("rid"));
    }

    return map.entrySet().iterator();
  }

  public Iterator<Entry<Object, OIdentifiable>> inverseIterator() {
    final OCommandRequest cmd = formatCommand(QUERY_ENTRIES, name);
    final List<ODocument> result = getDatabase().command(cmd).execute();

    final Map<Object, OIdentifiable> map = new LinkedHashMap<Object, OIdentifiable>();

    for (ListIterator<ODocument> it = result.listIterator(); it.hasPrevious();) {
      ODocument d = it.previous();
      d.setLazyLoad(false);
      map.put(d.field("key"), (OIdentifiable) d.field("rid"));
    }

    return map.entrySet().iterator();
  }

  @Override
  public boolean supportsOrderedIterations() {
    return false;
  }

}


File: core/src/main/java/com/orientechnologies/orient/core/serialization/OSerializableStream.java
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
package com.orientechnologies.orient.core.serialization;

import java.io.Serializable;

import com.orientechnologies.orient.core.exception.OSerializationException;

/**
 * Base interface of serialization.
 * 
 * @author Luca Garulli (l.garulli--at--orientechnologies.com)
 * 
 */
public interface OSerializableStream extends Serializable {
	/**
	 * Marshalls the object. Transforms the current object in byte[] form to being stored or transferred over the network.
	 * 
	 * @return The byte array representation of the object
	 * @see #fromStream(byte[])
	 * @throws OSerializationException
	 *           if the marshalling does not succeed
	 */
	public byte[] toStream() throws OSerializationException;

	/**
	 * Unmarshalls the object. Fills the current object with the values contained in the byte array representation restoring a
	 * previous state. Usually byte[] comes from the storage or network.
	 * 
	 * @param iStream
	 *          byte array representation of the object
	 * @return The Object instance itself giving a "fluent interface". Useful to call multiple methods in chain.
	 * @throws OSerializationException
	 *           if the unmarshalling does not succeed
	 */
	public OSerializableStream fromStream(byte[] iStream) throws OSerializationException;
}


File: core/src/main/java/com/orientechnologies/orient/core/storage/OStorageProxy.java
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
package com.orientechnologies.orient.core.storage;

/**
 * Tagged interface for proxy storage implementation
 * 
 * @author Luca Garulli
 * 
 */
public interface OStorageProxy extends OStorage {
	public String getUserName();
}


File: enterprise/src/main/java/com/orientechnologies/orient/enterprise/channel/binary/OChannelBinaryProtocol.java
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
package com.orientechnologies.orient.enterprise.channel.binary;

import com.orientechnologies.orient.core.Orient;
import com.orientechnologies.orient.core.db.record.OIdentifiable;
import com.orientechnologies.orient.core.id.ORecordId;
import com.orientechnologies.orient.core.record.ORecord;
import com.orientechnologies.orient.core.record.ORecordInternal;
import com.orientechnologies.orient.core.version.ORecordVersion;

import java.io.IOException;

/**
 * The range of the requests is 1-79.
 * 
 * @author Luca Garulli (l.garulli--at--orientechnologies.com)
 * 
 */
public class OChannelBinaryProtocol {
  // OUTGOING
  public static final byte  REQUEST_SHUTDOWN                          = 1;
  public static final byte  REQUEST_CONNECT                           = 2;

  public static final byte  REQUEST_DB_OPEN                           = 3;
  public static final byte  REQUEST_DB_CREATE                         = 4;
  public static final byte  REQUEST_DB_CLOSE                          = 5;
  public static final byte  REQUEST_DB_EXIST                          = 6;
  public static final byte  REQUEST_DB_DROP                           = 7;
  public static final byte  REQUEST_DB_SIZE                           = 8;
  public static final byte  REQUEST_DB_COUNTRECORDS                   = 9;

  public static final byte  REQUEST_DATACLUSTER_ADD                   = 10;
  public static final byte  REQUEST_DATACLUSTER_DROP                  = 11;
  public static final byte  REQUEST_DATACLUSTER_COUNT                 = 12;
  public static final byte  REQUEST_DATACLUSTER_DATARANGE             = 13;
  public static final byte  REQUEST_DATACLUSTER_COPY                  = 14;
  public static final byte  REQUEST_DATACLUSTER_LH_CLUSTER_IS_USED    = 16;                 // since 1.2.0

  public static final byte  REQUEST_DATASEGMENT_ADD                   = 20;
  public static final byte  REQUEST_DATASEGMENT_DROP                  = 21;

  public static final byte  REQUEST_RECORD_METADATA                   = 29;                 // since 1.4.0
  public static final byte  REQUEST_RECORD_LOAD                       = 30;
  public static final byte  REQUEST_RECORD_CREATE                     = 31;
  public static final byte  REQUEST_RECORD_UPDATE                     = 32;
  public static final byte  REQUEST_RECORD_DELETE                     = 33;
  public static final byte  REQUEST_RECORD_COPY                       = 34;
  public static final byte  REQUEST_POSITIONS_HIGHER                  = 36;                 // since 1.3.0
  public static final byte  REQUEST_POSITIONS_LOWER                   = 37;                 // since 1.3.0
  public static final byte  REQUEST_RECORD_CLEAN_OUT                  = 38;                 // since 1.3.0
  public static final byte  REQUEST_POSITIONS_FLOOR                   = 39;                 // since 1.3.0

  public static final byte  REQUEST_COUNT                             = 40;                 // DEPRECATED: USE
                                                                                             // REQUEST_DATACLUSTER_COUNT
  public static final byte  REQUEST_COMMAND                           = 41;
  public static final byte  REQUEST_POSITIONS_CEILING                 = 42;                 // since 1.3.0
  public static final byte  REQUEST_RECORD_HIDE                       = 43;                 // since 1.7
  public static final byte  REQUEST_RECORD_LOAD_IF_VERSION_NOT_LATEST = 44;                 // since 2.1

  public static final byte  REQUEST_TX_COMMIT                         = 60;

  public static final byte  REQUEST_CONFIG_GET                        = 70;
  public static final byte  REQUEST_CONFIG_SET                        = 71;
  public static final byte  REQUEST_CONFIG_LIST                       = 72;
  public static final byte  REQUEST_DB_RELOAD                         = 73;                 // SINCE 1.0rc4
  public static final byte  REQUEST_DB_LIST                           = 74;                 // SINCE 1.0rc6

  public static final byte  REQUEST_PUSH_DISTRIB_CONFIG               = 80;
  public static final byte  REQUEST_PUSH_LIVE_QUERY                   = 81;                 // SINCE 2.1

  // DISTRIBUTED
  public static final byte  REQUEST_DB_COPY                           = 90;                 // SINCE 1.0rc8
  public static final byte  REQUEST_REPLICATION                       = 91;                 // SINCE 1.0
  public static final byte  REQUEST_CLUSTER                           = 92;                 // SINCE 1.0
  public static final byte  REQUEST_DB_TRANSFER                       = 93;                 // SINCE 1.0.2

  // Lock + sync
  public static final byte  REQUEST_DB_FREEZE                         = 94;                 // SINCE 1.1.0
  public static final byte  REQUEST_DB_RELEASE                        = 95;                 // SINCE 1.1.0

  public static final byte  REQUEST_DATACLUSTER_FREEZE                = 96;
  public static final byte  REQUEST_DATACLUSTER_RELEASE               = 97;

  // REMOTE SB-TREE COLLECTIONS
  public static final byte  REQUEST_CREATE_SBTREE_BONSAI              = 110;
  public static final byte  REQUEST_SBTREE_BONSAI_GET                 = 111;
  public static final byte  REQUEST_SBTREE_BONSAI_FIRST_KEY           = 112;
  public static final byte  REQUEST_SBTREE_BONSAI_GET_ENTRIES_MAJOR   = 113;
  public static final byte  REQUEST_RIDBAG_GET_SIZE                   = 114;

  public static final int   REQUEST_INDEX_GET                         = 120;
  public static final int   REQUEST_INDEX_PUT                         = 121;
  public static final int   REQUEST_INDEX_REMOVE                      = 122;

  // INCOMING
  public static final byte  RESPONSE_STATUS_OK                        = 0;
  public static final byte  RESPONSE_STATUS_ERROR                     = 1;
  public static final byte  PUSH_DATA                                 = 3;

  // CONSTANTS
  public static final short RECORD_NULL                               = -2;
  public static final short RECORD_RID                                = -3;

  // FOR MORE INFO: https://github.com/orientechnologies/orientdb/wiki/Network-Binary-Protocol#wiki-Compatibility
  public static final int   PROTOCOL_VERSION_21                       = 21;

  public static final int   PROTOCOL_VERSION_24                       = 24;
  public static final int   PROTOCOL_VERSION_25                       = 25;
  public static final int   PROTOCOL_VERSION_26                       = 26;
  public static final int   PROTOCOL_VERSION_27                       = 27;
  public static final int   PROTOCOL_VERSION_28                       = 28;                 // SENT AS SHORT AS FIRST PACKET AFTER
                                                                                             // SOCKET CONNECTION
  public static final int   PROTOCOL_VERSION_29                       = 29;                 // ADDED PUSH SUPPORT FOR LIVE QUERY
  public static final int   PROTOCOL_VERSION_30                       = 30;                 // NEW COMMAND TO READ RECORD ONLY IF
                                                                                             // VERSION IS NOT LATEST WAS ADD

  public static final int   CURRENT_PROTOCOL_VERSION                  = PROTOCOL_VERSION_30;

  public static OIdentifiable readIdentifiable(final OChannelBinaryAsynchClient network) throws IOException {
    final int classId = network.readShort();
    if (classId == RECORD_NULL)
      return null;

    if (classId == RECORD_RID) {
      return network.readRID();
    } else {
      final ORecord record = Orient.instance().getRecordFactoryManager().newInstance(network.readByte());

      final ORecordId rid = network.readRID();
      final ORecordVersion version = network.readVersion();
      final byte[] content = network.readBytes();
      ORecordInternal.fill(record, rid, version, content, false);

      return record;
    }
  }
}


File: server/src/main/java/com/orientechnologies/orient/server/network/protocol/binary/ONetworkProtocolBinary.java
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
package com.orientechnologies.orient.server.network.protocol.binary;

import java.io.IOException;
import java.io.ObjectOutputStream;
import java.net.Socket;
import java.net.SocketException;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.UUID;

import com.orientechnologies.common.collection.OMultiValue;
import com.orientechnologies.common.concur.lock.OLockException;
import com.orientechnologies.common.exception.OException;
import com.orientechnologies.common.io.OIOException;
import com.orientechnologies.common.log.OLogManager;
import com.orientechnologies.common.serialization.types.OBinarySerializer;
import com.orientechnologies.common.serialization.types.OByteSerializer;
import com.orientechnologies.common.serialization.types.OIntegerSerializer;
import com.orientechnologies.common.serialization.types.ONullSerializer;
import com.orientechnologies.common.util.OCommonConst;
import com.orientechnologies.orient.client.remote.OCollectionNetworkSerializer;
import com.orientechnologies.orient.client.remote.OEngineRemote;
import com.orientechnologies.orient.core.OConstants;
import com.orientechnologies.orient.core.Orient;
import com.orientechnologies.orient.core.command.OCommandRequestText;
import com.orientechnologies.orient.core.config.OContextConfiguration;
import com.orientechnologies.orient.core.config.OGlobalConfiguration;
import com.orientechnologies.orient.core.db.ODatabase;
import com.orientechnologies.orient.core.db.ODatabaseInternal;
import com.orientechnologies.orient.core.db.ODatabaseRecordThreadLocal;
import com.orientechnologies.orient.core.db.document.ODatabaseDocument;
import com.orientechnologies.orient.core.db.document.ODatabaseDocumentTx;
import com.orientechnologies.orient.core.db.record.OIdentifiable;
import com.orientechnologies.orient.core.db.record.ridbag.sbtree.OBonsaiCollectionPointer;
import com.orientechnologies.orient.core.db.record.ridbag.sbtree.OSBTreeCollectionManager;
import com.orientechnologies.orient.core.db.record.ridbag.sbtree.OSBTreeRidBag;
import com.orientechnologies.orient.core.exception.OConfigurationException;
import com.orientechnologies.orient.core.exception.ODatabaseException;
import com.orientechnologies.orient.core.exception.OSecurityAccessException;
import com.orientechnologies.orient.core.exception.OSecurityException;
import com.orientechnologies.orient.core.exception.OStorageException;
import com.orientechnologies.orient.core.exception.OTransactionAbortedException;
import com.orientechnologies.orient.core.fetch.OFetchContext;
import com.orientechnologies.orient.core.fetch.OFetchHelper;
import com.orientechnologies.orient.core.fetch.OFetchListener;
import com.orientechnologies.orient.core.fetch.OFetchPlan;
import com.orientechnologies.orient.core.fetch.remote.ORemoteFetchContext;
import com.orientechnologies.orient.core.fetch.remote.ORemoteFetchListener;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.id.ORecordId;
import com.orientechnologies.orient.core.index.OIndex;
import com.orientechnologies.orient.core.index.sbtree.OTreeInternal;
import com.orientechnologies.orient.core.index.sbtreebonsai.local.OSBTreeBonsai;
import com.orientechnologies.orient.core.metadata.schema.OType;
import com.orientechnologies.orient.core.record.ORecord;
import com.orientechnologies.orient.core.record.ORecordInternal;
import com.orientechnologies.orient.core.record.impl.ODocument;
import com.orientechnologies.orient.core.record.impl.ORecordBytes;
import com.orientechnologies.orient.core.serialization.OMemoryStream;
import com.orientechnologies.orient.core.serialization.serializer.ONetworkThreadLocalSerializer;
import com.orientechnologies.orient.core.serialization.serializer.record.ORecordSerializer;
import com.orientechnologies.orient.core.serialization.serializer.record.ORecordSerializerFactory;
import com.orientechnologies.orient.core.serialization.serializer.record.string.ORecordSerializerSchemaAware2CSV;
import com.orientechnologies.orient.core.serialization.serializer.record.string.ORecordSerializerStringAbstract;
import com.orientechnologies.orient.core.serialization.serializer.stream.OStreamSerializerAnyStreamable;
import com.orientechnologies.orient.core.storage.OCluster;
import com.orientechnologies.orient.core.storage.OPhysicalPosition;
import com.orientechnologies.orient.core.storage.ORecordDuplicatedException;
import com.orientechnologies.orient.core.storage.ORecordMetadata;
import com.orientechnologies.orient.core.storage.OStorage;
import com.orientechnologies.orient.core.storage.OStorageProxy;
import com.orientechnologies.orient.core.storage.impl.memory.ODirectMemoryStorage;
import com.orientechnologies.orient.core.type.ODocumentWrapper;
import com.orientechnologies.orient.core.version.ORecordVersion;
import com.orientechnologies.orient.core.version.OVersionFactory;
import com.orientechnologies.orient.enterprise.channel.binary.OChannelBinaryProtocol;
import com.orientechnologies.orient.enterprise.channel.binary.OChannelBinaryServer;
import com.orientechnologies.orient.server.OClientConnection;
import com.orientechnologies.orient.server.OClientConnectionManager;
import com.orientechnologies.orient.server.OServer;
import com.orientechnologies.orient.server.ShutdownHelper;
import com.orientechnologies.orient.server.distributed.ODistributedServerManager;
import com.orientechnologies.orient.server.network.OServerNetworkListener;
import com.orientechnologies.orient.server.plugin.OServerPlugin;
import com.orientechnologies.orient.server.plugin.OServerPluginHelper;
import com.orientechnologies.orient.server.security.OSecurityServerUser;
import com.orientechnologies.orient.server.tx.OTransactionOptimisticProxy;

public class ONetworkProtocolBinary extends OBinaryNetworkProtocolAbstract {
  protected OClientConnection connection;
  protected Boolean           tokenBased;

  public ONetworkProtocolBinary() {
    super("OrientDB <- BinaryClient/?");
  }

  public ONetworkProtocolBinary(final String iThreadName) {
    super(iThreadName);
  }

  @Override
  public void config(final OServerNetworkListener iListener, final OServer iServer, final Socket iSocket,
      final OContextConfiguration iConfig) throws IOException {
    // CREATE THE CLIENT CONNECTION
    connection = OClientConnectionManager.instance().connect(this);

    super.config(iListener, iServer, iSocket, iConfig);

    // SEND PROTOCOL VERSION
    channel.writeShort((short) getVersion());

    channel.flush();
    start();
    setName("OrientDB <- BinaryClient (" + iSocket.getRemoteSocketAddress() + ")");
  }

  @Override
  public void startup() {
    super.startup();
    OServerPluginHelper.invokeHandlerCallbackOnClientConnection(server, connection);
  }

  @Override
  public void shutdown() {
    sendShutdown();
    super.shutdown();

    if (connection == null)
      return;

    OServerPluginHelper.invokeHandlerCallbackOnClientDisconnection(server, connection);

    OClientConnectionManager.instance().disconnect(connection);
  }

  @Override
  protected void onBeforeRequest() throws IOException {
    waitNodeIsOnline();

    if (Boolean.FALSE.equals(tokenBased) || requestType == OChannelBinaryProtocol.REQUEST_CONNECT
        || requestType == OChannelBinaryProtocol.REQUEST_DB_OPEN || (tokenHandler == null)) {
      connection = OClientConnectionManager.instance().getConnection(clientTxId, this);
      if (clientTxId < 0) {
        short protocolId = 0;

        if (connection != null)
          protocolId = connection.data.protocolVersion;

        connection = OClientConnectionManager.instance().connect(this);

        if (connection != null)
          connection.data.protocolVersion = protocolId;
      }
    } else {
      if (requestType != OChannelBinaryProtocol.REQUEST_CONNECT && requestType != OChannelBinaryProtocol.REQUEST_DB_OPEN) {
        byte[] tokenBytes = channel.readBytes();
        try {
          this.token = tokenHandler.parseBinaryToken(tokenBytes);
        } catch (Exception e) {
          throw new OException("error on token parse", e);
        }
        if (!this.token.getIsVerified()) {
          throw new OSecurityException("The token provided is not a valid token, signature doesn't match");
        }

        if (tokenBased == null)
          tokenBased = Boolean.TRUE;
        if (token != null) {
          if (!tokenHandler.validateBinaryToken(token)) {
            throw new OSecurityException("The token provided is expired");
          }
          connection = new OClientConnection(clientTxId, this);
          if (tokenHandler != null)
            connection.data = tokenHandler.getProtocolDataFromToken(token);
          String db = token.getDatabase();
          String type = token.getDatabaseType();
          if (db != null && type != null) {
            final ODatabaseDocumentTx database = new ODatabaseDocumentTx(type + ":" + db);
            if (connection.data.serverUser) {
              database.resetInitialization();
              database.setProperty(ODatabase.OPTIONS.SECURITY.toString(), OSecurityServerUser.class);
              database.open(connection.data.serverUsername, null);
            } else
              database.open(token);
            connection.database = database;
          }
          if (connection.data.serverUser) {
            connection.serverUser = server.serverLogin(connection.data.serverUsername, null, null);
          }
        }
      }
    }

    if (connection != null) {
      ODatabaseRecordThreadLocal.INSTANCE.set(connection.database);
      if (connection.database != null) {
        connection.data.lastDatabase = connection.database.getName();
        connection.data.lastUser = connection.database.getUser() != null ? connection.database.getUser().getName() : null;
      } else {
        connection.data.lastDatabase = null;
        connection.data.lastUser = null;
      }

      ++connection.data.totalRequests;
      setDataCommandInfo("Listening");
      connection.data.commandDetail = "-";
      connection.data.lastCommandReceived = System.currentTimeMillis();
    } else {
      ODatabaseRecordThreadLocal.INSTANCE.remove();
      if (requestType != OChannelBinaryProtocol.REQUEST_DB_CLOSE && requestType != OChannelBinaryProtocol.REQUEST_SHUTDOWN) {
        OLogManager.instance().debug(this, "Found unknown session %d, shutdown current connection", clientTxId);
        shutdown();
        throw new OIOException("Found unknown session " + clientTxId);
      }
    }

    OServerPluginHelper.invokeHandlerCallbackOnBeforeClientRequest(server, connection, (byte) requestType);
  }

  @Override
  protected void onAfterRequest() throws IOException {
    OServerPluginHelper.invokeHandlerCallbackOnAfterClientRequest(server, connection, (byte) requestType);

    if (connection != null) {
      if (!Boolean.TRUE.equals(tokenBased)) {
        if (connection.database != null)
          if (!connection.database.isClosed() && connection.database.getLocalCache() != null)
            connection.database.getLocalCache().clear();
      } else {
        if (connection.database != null && !connection.database.isClosed())
          connection.database.close();
        connection.database = null;
      }

      connection.data.lastCommandExecutionTime = System.currentTimeMillis() - connection.data.lastCommandReceived;
      connection.data.totalCommandExecutionTime += connection.data.lastCommandExecutionTime;

      connection.data.lastCommandInfo = connection.data.commandInfo;
      connection.data.lastCommandDetail = connection.data.commandDetail;

      setDataCommandInfo("Listening");
      connection.data.commandDetail = "-";
    }
  }

  protected boolean executeRequest() throws IOException {
    try {
      switch (requestType) {

      case OChannelBinaryProtocol.REQUEST_SHUTDOWN:
        shutdownConnection();
        break;

      case OChannelBinaryProtocol.REQUEST_CONNECT:
        connect();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_LIST:
        listDatabases();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_OPEN:
        openDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_RELOAD:
        reloadDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_CREATE:
        createDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_CLOSE:
        closeDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_EXIST:
        existsDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_DROP:
        dropDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_SIZE:
        sizeDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_COUNTRECORDS:
        countDatabaseRecords();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_COPY:
        copyDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_REPLICATION:
        replicationDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_CLUSTER:
        distributedCluster();
        break;

      case OChannelBinaryProtocol.REQUEST_DATACLUSTER_COUNT:
        countClusters();
        break;

      case OChannelBinaryProtocol.REQUEST_DATACLUSTER_DATARANGE:
        rangeCluster();
        break;

      case OChannelBinaryProtocol.REQUEST_DATACLUSTER_ADD:
        addCluster();
        break;

      case OChannelBinaryProtocol.REQUEST_DATACLUSTER_DROP:
        removeCluster();
        break;

      case OChannelBinaryProtocol.REQUEST_RECORD_METADATA:
        readRecordMetadata();
        break;

      case OChannelBinaryProtocol.REQUEST_RECORD_LOAD:
        readRecord();
        break;

      case OChannelBinaryProtocol.REQUEST_RECORD_LOAD_IF_VERSION_NOT_LATEST:
        readRecordIfVersionIsNotLatest();
        break;

      case OChannelBinaryProtocol.REQUEST_RECORD_CREATE:
        createRecord();
        break;

      case OChannelBinaryProtocol.REQUEST_RECORD_UPDATE:
        updateRecord();
        break;

      case OChannelBinaryProtocol.REQUEST_RECORD_DELETE:
        deleteRecord();
        break;

      case OChannelBinaryProtocol.REQUEST_RECORD_HIDE:
        hideRecord();
        break;

      case OChannelBinaryProtocol.REQUEST_POSITIONS_HIGHER:
        higherPositions();
        break;

      case OChannelBinaryProtocol.REQUEST_POSITIONS_CEILING:
        ceilingPositions();
        break;

      case OChannelBinaryProtocol.REQUEST_POSITIONS_LOWER:
        lowerPositions();
        break;

      case OChannelBinaryProtocol.REQUEST_POSITIONS_FLOOR:
        floorPositions();
        break;

      case OChannelBinaryProtocol.REQUEST_COUNT:
        throw new UnsupportedOperationException("Operation OChannelBinaryProtocol.REQUEST_COUNT has been deprecated");

      case OChannelBinaryProtocol.REQUEST_COMMAND:
        command();
        break;

      case OChannelBinaryProtocol.REQUEST_TX_COMMIT:
        commit();
        break;

      case OChannelBinaryProtocol.REQUEST_CONFIG_GET:
        configGet();
        break;

      case OChannelBinaryProtocol.REQUEST_CONFIG_SET:
        configSet();
        break;

      case OChannelBinaryProtocol.REQUEST_CONFIG_LIST:
        configList();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_FREEZE:
        freezeDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DB_RELEASE:
        releaseDatabase();
        break;

      case OChannelBinaryProtocol.REQUEST_DATACLUSTER_FREEZE:
        freezeCluster();
        break;

      case OChannelBinaryProtocol.REQUEST_DATACLUSTER_RELEASE:
        releaseCluster();
        break;

      case OChannelBinaryProtocol.REQUEST_RECORD_CLEAN_OUT:
        cleanOutRecord();
        break;

      case OChannelBinaryProtocol.REQUEST_CREATE_SBTREE_BONSAI:
        createSBTreeBonsai();
        break;

      case OChannelBinaryProtocol.REQUEST_SBTREE_BONSAI_GET:
        sbTreeBonsaiGet();
        break;

      case OChannelBinaryProtocol.REQUEST_SBTREE_BONSAI_FIRST_KEY:
        sbTreeBonsaiFirstKey();
        break;

      case OChannelBinaryProtocol.REQUEST_SBTREE_BONSAI_GET_ENTRIES_MAJOR:
        sbTreeBonsaiGetEntriesMajor();
        break;

      case OChannelBinaryProtocol.REQUEST_RIDBAG_GET_SIZE:
        ridBagSize();
        break;
      case OChannelBinaryProtocol.REQUEST_INDEX_GET:
        indexGet();
        break;
      case OChannelBinaryProtocol.REQUEST_INDEX_PUT:
        indexPut();
        break;
      case OChannelBinaryProtocol.REQUEST_INDEX_REMOVE:
        indexRemove();
        break;
      default:
        setDataCommandInfo("Command not supported");
        return false;
      }

      return true;
    } catch (RuntimeException e) {
      if (connection != null && connection.database != null) {
        final OSBTreeCollectionManager collectionManager = connection.database.getSbTreeCollectionManager();
        if (collectionManager != null)
          collectionManager.clearChangedIds();
      }

      throw e;
    }
  }

  private void indexPut() throws IOException {
    setDataCommandInfo("Remove Key from index");

    if (!isConnectionAlive())
      return;
    final String indexName = channel.readString();
    List<String> keyList = channel.readStringList();
    ORecordId value = channel.readRID();
    OIndex<?> index = connection.database.getMetadata().getIndexManager().getIndex(indexName);

    if (index == null)
      throw new OException("index with name " + indexName + "not found");

    Object key = index.getDefinition().createValue(keyList);

    if (!isConnectionAlive())
      return;

    beginResponse();
    try {
      try {
        index.put(key, value);
        sendOk(clientTxId);
      } catch (ORecordDuplicatedException ex) {
        sendError(clientTxId, ex);
      }
    } finally {
      connection.data.command = null;
      endResponse();
    }
  }

  private void indexRemove() throws IOException {
    setDataCommandInfo("Remove Key from index");

    if (!isConnectionAlive())
      return;
    final String indexName = channel.readString();
    List<String> keyList = channel.readStringList();
    OIndex<?> index = connection.database.getMetadata().getIndexManager().getIndex(indexName);
    if (index == null)
      throw new OException("index with name " + indexName + "not found");

    Object key = index.getDefinition().createValue(keyList);

    if (!isConnectionAlive())
      return;

    boolean res = index.remove(key);
    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeBoolean(res);
    } finally {
      connection.data.command = null;
      endResponse();
    }
  }

  private void indexGet() throws IOException {
    setDataCommandInfo("Get from index ");

    if (!isConnectionAlive())
      return;

    final String indexName = channel.readString();
    List<String> keys = channel.readStringList();
    final String fetchPlan = channel.readString();
    OIndex<?> index = connection.database.getMetadata().getIndexManager().getIndex(indexName);
    if (index == null)
      throw new OException("index with name " + indexName + "not found");

    Object key = index.getDefinition().createValue(keys);
    OAbstractCommandResultListener listener = null;

    listener = new OSyncCommandResultListener();

    if (!isConnectionAlive())
      return;

    listener.setFetchPlan(fetchPlan);

    Object result = index.get(key);
    beginResponse();
    try {
      sendOk(clientTxId);
      if (result == null) {
        // NULL VALUE
        channel.writeByte((byte) 'n');
      } else if (result instanceof OIdentifiable) {
        // RECORD
        channel.writeByte((byte) 'r');
        listener.result(result);
        writeIdentifiable((OIdentifiable) result);
      } else if (result instanceof ODocumentWrapper) {
        // RECORD
        channel.writeByte((byte) 'r');
        final ODocument doc = ((ODocumentWrapper) result).getDocument();
        listener.result(doc);
        writeIdentifiable(doc);
      } else if (OMultiValue.isMultiValue(result)) {
        channel.writeByte((byte) 'l');
        channel.writeInt(OMultiValue.getSize(result));
        for (Object o : OMultiValue.getMultiValueIterable(result)) {
          try {
            listener.result(o);
            writeIdentifiable((OIdentifiable) o);
          } catch (Exception e) {
            OLogManager.instance().warn(this, "Cannot serialize record: " + o);
            // WRITE NULL RECORD TO AVOID BREAKING PROTOCOL
            writeIdentifiable(null);
          }
        }
      } else {
        // ANY OTHER (INCLUDING LITERALS)
        channel.writeByte((byte) 'a');
        final StringBuilder value = new StringBuilder(64);
        listener.result(result);
        ORecordSerializerStringAbstract.fieldTypeToString(value, OType.getTypeByClass(result.getClass()), result);
        channel.writeString(value.toString());
      }

      if (connection.data.protocolVersion >= 17 && listener instanceof OSyncCommandResultListener) {
        // SEND FETCHED RECORDS TO LOAD IN CLIENT CACHE
        for (ORecord rec : ((OSyncCommandResultListener) listener).getFetchedRecordsToSend()) {
          channel.writeByte((byte) 2); // CLIENT CACHE RECORD. IT
          // ISN'T PART OF THE
          // RESULT SET
          writeIdentifiable(rec);
        }

        channel.writeByte((byte) 0); // NO MORE RECORDS
      }

    } finally {
      connection.data.command = null;
      endResponse();
    }

  }

  protected void checkServerAccess(final String iResource) {
    if (connection.data.protocolVersion <= OChannelBinaryProtocol.PROTOCOL_VERSION_26) {
      if (connection.serverUser == null)
        throw new OSecurityAccessException("Server user not authenticated.");

      if (!server.isAllowed(connection.serverUser.name, iResource))
        throw new OSecurityAccessException("User '" + connection.serverUser.name + "' cannot access to the resource [" + iResource
            + "]. Use another server user or change permission in the file config/orientdb-server-config.xml");
    } else {
      if (!connection.data.serverUser)
        throw new OSecurityAccessException("Server user not authenticated.");

      if (!server.isAllowed(connection.data.serverUsername, iResource))
        throw new OSecurityAccessException("User '" + connection.data.serverUsername + "' cannot access to the resource ["
            + iResource + "]. Use another server user or change permission in the file config/orientdb-server-config.xml");
    }
  }

  protected ODatabase<?> openDatabase(final ODatabaseInternal<?> database, final String iUser, final String iPassword) {

    if (database.isClosed())
      if (database.getStorage() instanceof ODirectMemoryStorage && !database.exists())
        database.create();
      else {
        try {
          database.open(iUser, iPassword);
        } catch (OSecurityException e) {
          // TRY WITH SERVER'S USER
          try {
            connection.serverUser = server.serverLogin(iUser, iPassword, "database.passthrough");
          } catch (OSecurityException ex) {
            throw e;
          }

          // SERVER AUTHENTICATED, BYPASS SECURITY
          database.activateOnCurrentThread();
          database.resetInitialization();
          database.setProperty(ODatabase.OPTIONS.SECURITY.toString(), OSecurityServerUser.class);
          database.open(iUser, iPassword);
        }
      }

    return database;
  }

  protected void removeCluster() throws IOException {
    setDataCommandInfo("Remove cluster");

    if (!isConnectionAlive())
      return;

    final int id = channel.readShort();

    final String clusterName = connection.database.getClusterNameById(id);
    if (clusterName == null)
      throw new IllegalArgumentException("Cluster " + id
          + " doesn't exist anymore. Refresh the db structure or just reconnect to the database");

    boolean result = connection.database.dropCluster(clusterName, true);

    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeByte((byte) (result ? 1 : 0));
    } finally {
      endResponse();
    }
  }

  protected void addCluster() throws IOException {
    setDataCommandInfo("Add cluster");

    if (!isConnectionAlive())
      return;

    String type = "";
    if (connection.data.protocolVersion < 24)
      type = channel.readString();

    final String name = channel.readString();
    int clusterId = -1;

    final String location;
    if (connection.data.protocolVersion >= 10 && connection.data.protocolVersion < 24 || type.equalsIgnoreCase("PHYSICAL"))
      location = channel.readString();
    else
      location = null;

    if (connection.data.protocolVersion < 24) {
      final String dataSegmentName;
      if (connection.data.protocolVersion >= 10)
        dataSegmentName = channel.readString();
      else {
        channel.readInt(); // OLD INIT SIZE, NOT MORE USED
        dataSegmentName = null;
      }
    }

    if (connection.data.protocolVersion >= 18)
      clusterId = channel.readShort();

    final int num;
    if (clusterId < 0)
      num = connection.database.addCluster(name);
    else
      num = connection.database.addCluster(name, clusterId, null);

    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeShort((short) num);
    } finally {
      endResponse();
    }
  }

  protected void rangeCluster() throws IOException {
    setDataCommandInfo("Get the begin/end range of data in cluster");

    if (!isConnectionAlive())
      return;

    final long[] pos = connection.database.getStorage().getClusterDataRange(channel.readShort());

    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeLong(pos[0]);
      channel.writeLong(pos[1]);
    } finally {
      endResponse();
    }
  }

  protected void countClusters() throws IOException {
    setDataCommandInfo("Count cluster elements");

    if (!isConnectionAlive())
      return;

    int[] clusterIds = new int[channel.readShort()];
    for (int i = 0; i < clusterIds.length; ++i)
      clusterIds[i] = channel.readShort();

    boolean countTombstones = false;
    if (connection.data.protocolVersion >= 13)
      countTombstones = channel.readByte() > 0;

    final long count = connection.database.countClusterElements(clusterIds, countTombstones);

    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeLong(count);
    } finally {
      endResponse();
    }
  }

  protected void reloadDatabase() throws IOException {
    setDataCommandInfo("Reload database information");

    if (!isConnectionAlive())
      return;

    beginResponse();
    try {
      sendOk(clientTxId);

      sendDatabaseInformation();

    } finally {
      endResponse();
    }
  }

  protected void openDatabase() throws IOException {
    setDataCommandInfo("Open database");

    readConnectionData();

    final String dbURL = channel.readString();

    String dbType = ODatabaseDocument.TYPE;
    if (connection.data.protocolVersion >= 8)
      // READ DB-TYPE FROM THE CLIENT
      dbType = channel.readString();

    final String user = channel.readString();
    final String passwd = channel.readString();

    connection.database = (ODatabaseDocumentTx) server.openDatabase(dbType, dbURL, user, passwd, connection.data);

    if (connection.database.getStorage() instanceof OStorageProxy && !loadUserFromSchema(user, passwd)) {
      sendErrorOrDropConnection(clientTxId, new OSecurityAccessException(connection.database.getName(),
          "User or password not valid for database: '" + connection.database.getName() + "'"));
    } else {

      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeInt(connection.id);
        if (connection.data.protocolVersion > OChannelBinaryProtocol.PROTOCOL_VERSION_26) {
          if (Boolean.TRUE.equals(tokenBased)) {
            byte[] token = tokenHandler.getSignedBinaryToken(connection.database, connection.database.getUser(), connection.data);
            channel.writeBytes(token);
          } else
            channel.writeBytes(OCommonConst.EMPTY_BYTE_ARRAY);
        }

        sendDatabaseInformation();

        final OServerPlugin plugin = server.getPlugin("cluster");
        ODocument distributedCfg = null;
        if (plugin != null && plugin instanceof ODistributedServerManager)
          distributedCfg = ((ODistributedServerManager) plugin).getClusterConfiguration();

        channel.writeBytes(distributedCfg != null ? getRecordBytes(distributedCfg) : null);

        if (connection.data.protocolVersion >= 14)
          channel.writeString(OConstants.getVersion());
      } finally {
        endResponse();
      }
    }
  }

  protected void connect() throws IOException {
    setDataCommandInfo("Connect");

    readConnectionData();

    connection.serverUser = server.serverLogin(channel.readString(), channel.readString(), "connect");
    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeInt(connection.id);
      if (connection.data.protocolVersion > OChannelBinaryProtocol.PROTOCOL_VERSION_26) {
        connection.data.serverUsername = connection.serverUser.name;
        connection.data.serverUser = true;
        byte[] token;
        if (Boolean.TRUE.equals(tokenBased)) {
          token = tokenHandler.getSignedBinaryToken(null, null, connection.data);
        } else
          token = OCommonConst.EMPTY_BYTE_ARRAY;
        channel.writeBytes(token);
      }

    } finally {
      endResponse();
    }
  }

  protected void sendError(final int iClientTxId, final Throwable t) throws IOException {
    channel.acquireWriteLock();
    try {

      channel.writeByte(OChannelBinaryProtocol.RESPONSE_STATUS_ERROR);
      channel.writeInt(iClientTxId);
      if (Boolean.TRUE.equals(tokenBased) && token != null) {
        // TODO: Check if the token is expiring and if it is send a new token
        byte[] renewedToken = tokenHandler.renewIfNeeded(token);
        channel.writeBytes(renewedToken);
      }

      final Throwable current;
      if (t instanceof OLockException && t.getCause() instanceof ODatabaseException)
        // BYPASS THE DB POOL EXCEPTION TO PROPAGATE THE RIGHT SECURITY ONE
        current = t.getCause();
      else
        current = t;

      sendErrorDetails(current);

      if (connection != null && connection.data.protocolVersion >= 19) {
        serializeExceptionObject(current);
      }

      channel.flush();

      if (OLogManager.instance().isLevelEnabled(logClientExceptions)) {
        if (logClientFullStackTrace)
          OLogManager.instance().log(this, logClientExceptions, "Sent run-time exception to the client %s: %s", t,
              channel.socket.getRemoteSocketAddress(), t.toString());
        else
          OLogManager.instance().log(this, logClientExceptions, "Sent run-time exception to the client %s: %s", null,
              channel.socket.getRemoteSocketAddress(), t.toString());
      }
    } catch (Exception e) {
      if (e instanceof SocketException)
        shutdown();
      else
        OLogManager.instance().error(this, "Error during sending an error to client", e);
    } finally {
      if (channel.getLockWrite().isHeldByCurrentThread())
        // NO EXCEPTION SO FAR: UNLOCK IT
        channel.releaseWriteLock();
    }
  }

  protected void shutdownConnection() throws IOException {
    setDataCommandInfo("Shutdowning");

    OLogManager.instance().info(this, "Received shutdown command from the remote client %s:%d", channel.socket.getInetAddress(),
        channel.socket.getPort());

    final String user = channel.readString();
    final String passwd = channel.readString();

    if (server.authenticate(user, passwd, "shutdown")) {
      OLogManager.instance().info(this, "Remote client %s:%d authenticated. Starting shutdown of server...",
          channel.socket.getInetAddress(), channel.socket.getPort());

      beginResponse();
      try {
        sendOk(clientTxId);
      } finally {
        endResponse();
      }
      runShutdownInNonDaemonThread();
      return;
    }

    OLogManager.instance().error(this, "Authentication error of remote client %s:%d: shutdown is aborted.",
        channel.socket.getInetAddress(), channel.socket.getPort());

    sendErrorOrDropConnection(clientTxId, new OSecurityAccessException("Invalid user/password to shutdown the server"));
  }

  protected void copyDatabase() throws IOException {
    setDataCommandInfo("Copy the database to a remote server");

    final String dbUrl = channel.readString();
    final String dbUser = channel.readString();
    final String dbPassword = channel.readString();
    final String remoteServerName = channel.readString();
    final String remoteServerEngine = channel.readString();

    checkServerAccess("database.copy");

    final ODatabaseDocumentTx db = (ODatabaseDocumentTx) server.openDatabase(ODatabaseDocument.TYPE, dbUrl, dbUser, dbPassword);

    beginResponse();
    try {
      sendOk(clientTxId);
    } finally {
      endResponse();
    }
  }

  protected void replicationDatabase() throws IOException {
    setDataCommandInfo("Replication command");

    final ODocument request = new ODocument(channel.readBytes());

    final ODistributedServerManager dManager = server.getDistributedManager();
    if (dManager == null)
      throw new OConfigurationException("No distributed manager configured");

    final String operation = request.field("operation");

    ODocument response = null;

    if (operation.equals("start")) {
      checkServerAccess("server.replication.start");

    } else if (operation.equals("stop")) {
      checkServerAccess("server.replication.stop");

    } else if (operation.equals("config")) {
      checkServerAccess("server.replication.config");

      response = new ODocument().fromJSON(dManager.getDatabaseConfiguration((String) request.field("db")).serialize()
          .toJSON("prettyPrint"));

    }

    sendResponse(response);

  }

  protected void distributedCluster() throws IOException {
    setDataCommandInfo("Cluster status");

    final ODocument req = new ODocument(channel.readBytes());

    ODocument response = null;

    final String operation = req.field("operation");
    if (operation == null)
      throw new IllegalArgumentException("Cluster operation is null");

    if (operation.equals("status")) {
      final OServerPlugin plugin = server.getPlugin("cluster");
      if (plugin != null && plugin instanceof ODistributedServerManager)
        response = ((ODistributedServerManager) plugin).getClusterConfiguration();
    } else
      throw new IllegalArgumentException("Cluster operation '" + operation + "' is not supported");

    sendResponse(response);
  }

  protected void countDatabaseRecords() throws IOException {
    setDataCommandInfo("Database count records");

    if (!isConnectionAlive())
      return;

    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeLong(connection.database.getStorage().countRecords());
    } finally {
      endResponse();
    }
  }

  protected void sizeDatabase() throws IOException {
    setDataCommandInfo("Database size");

    if (!isConnectionAlive())
      return;

    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeLong(connection.database.getStorage().getSize());
    } finally {
      endResponse();
    }
  }

  protected void dropDatabase() throws IOException {
    setDataCommandInfo("Drop database");
    String dbName = channel.readString();

    String storageType;
    if (connection.data.protocolVersion >= 16)
      storageType = channel.readString();
    else
      storageType = "local";

    if (storageType == null)
      storageType = "plocal";

    checkServerAccess("database.delete");

    connection.database = getDatabaseInstance(dbName, ODatabaseDocument.TYPE, storageType);

    if (connection.database.exists()) {
      OLogManager.instance().info(this, "Dropped database '%s'", connection.database.getName());

      if (connection.database.isClosed())
        openDatabase(connection.database, connection.serverUser.name, connection.serverUser.password);

      connection.database.drop();
      connection.close();
    } else {
      throw new OStorageException("Database with name '" + dbName + "' doesn't exits.");
    }

    beginResponse();
    try {
      sendOk(clientTxId);
    } finally {
      endResponse();
    }
  }

  protected void existsDatabase() throws IOException {
    setDataCommandInfo("Exists database");
    final String dbName = channel.readString();
    final String storageType;

    if (connection.data.protocolVersion >= 16)
      storageType = channel.readString();
    else
      storageType = "local";

    checkServerAccess("database.exists");

    if (storageType != null)
      connection.database = getDatabaseInstance(dbName, ODatabaseDocument.TYPE, storageType);
    else {
      // CHECK AGAINST ALL THE ENGINE TYPES, BUT REMOTE
      for (String engine : Orient.instance().getEngines()) {
        if (!engine.equalsIgnoreCase(OEngineRemote.NAME)) {
          connection.database = getDatabaseInstance(dbName, ODatabaseDocument.TYPE, engine);
          if (connection.database.exists())
            // FOUND
            break;

          // NOT FOUND: ASSURE TO UNREGISTER IT TO AVOID CACHING
          Orient.instance().unregisterStorage(connection.database.getStorage());
        }
      }
    }

    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeByte((byte) (connection.database.exists() ? 1 : 0));
    } finally {
      endResponse();
    }
  }

  protected void createDatabase() throws IOException {
    setDataCommandInfo("Create database");

    String dbName = channel.readString();
    String dbType = ODatabaseDocument.TYPE;
    if (connection.data.protocolVersion >= 8)
      // READ DB-TYPE FROM THE CLIENT
      dbType = channel.readString();
    String storageType = channel.readString();

    checkServerAccess("database.create");
    checkStorageExistence(dbName);
    connection.database = getDatabaseInstance(dbName, dbType, storageType);
    createDatabase(connection.database, null, null);

    beginResponse();
    try {
      sendOk(clientTxId);
    } finally {
      endResponse();
    }
  }

  protected void closeDatabase() throws IOException {
    setDataCommandInfo("Close Database");

    if (connection != null) {
      if (connection.data.protocolVersion > 0 && connection.data.protocolVersion < 9)
        // OLD CLIENTS WAIT FOR A OK
        sendOk(clientTxId);

      if (Boolean.FALSE.equals(tokenBased) && OClientConnectionManager.instance().disconnect(connection.id))
        sendShutdown();
    }
  }

  protected void configList() throws IOException {
    setDataCommandInfo("List config");

    checkServerAccess("server.config.get");

    beginResponse();
    try {
      sendOk(clientTxId);

      channel.writeShort((short) OGlobalConfiguration.values().length);
      for (OGlobalConfiguration cfg : OGlobalConfiguration.values()) {

        String key;
        try {
          key = cfg.getKey();
        } catch (Exception e) {
          key = "?";
        }

        String value;
        try {
          value = cfg.getValueAsString() != null ? cfg.getValueAsString() : "";
        } catch (Exception e) {
          value = "";
        }

        channel.writeString(key);
        channel.writeString(value);
      }
    } finally {
      endResponse();
    }
  }

  protected void configSet() throws IOException {
    setDataCommandInfo("Get config");

    checkServerAccess("server.config.set");

    final String key = channel.readString();
    final String value = channel.readString();
    final OGlobalConfiguration cfg = OGlobalConfiguration.findByKey(key);
    if (cfg != null)
      cfg.setValue(value);

    beginResponse();
    try {
      sendOk(clientTxId);
    } finally {
      endResponse();
    }
  }

  protected void configGet() throws IOException {
    setDataCommandInfo("Get config");

    checkServerAccess("server.config.get");

    final String key = channel.readString();
    final OGlobalConfiguration cfg = OGlobalConfiguration.findByKey(key);
    String cfgValue = cfg != null ? cfg.getValueAsString() : "";

    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeString(cfgValue);
    } finally {
      endResponse();
    }
  }

  protected void commit() throws IOException {
    setDataCommandInfo("Transaction commit");

    if (!isConnectionAlive())
      return;

    final OTransactionOptimisticProxy tx = new OTransactionOptimisticProxy(connection.database, channel,
        connection.data.protocolVersion, this);

    try {
      connection.database.begin(tx);

      try {
        connection.database.commit();
        beginResponse();
        try {
          sendOk(clientTxId);

          // SEND BACK ALL THE RECORD IDS FOR THE CREATED RECORDS
          channel.writeInt(tx.getCreatedRecords().size());
          for (Entry<ORecordId, ORecord> entry : tx.getCreatedRecords().entrySet()) {
            channel.writeRID(entry.getKey());
            channel.writeRID(entry.getValue().getIdentity());

            // IF THE NEW OBJECT HAS VERSION > 0 MEANS THAT HAS BEEN UPDATED IN THE SAME TX. THIS HAPPENS FOR GRAPHS
            if (entry.getValue().getRecordVersion().getCounter() > 0)
              tx.getUpdatedRecords().put((ORecordId) entry.getValue().getIdentity(), entry.getValue());
          }

          // SEND BACK ALL THE NEW VERSIONS FOR THE UPDATED RECORDS
          channel.writeInt(tx.getUpdatedRecords().size());
          for (Entry<ORecordId, ORecord> entry : tx.getUpdatedRecords().entrySet()) {
            channel.writeRID(entry.getKey());
            channel.writeVersion(entry.getValue().getRecordVersion());
          }

          if (connection.data.protocolVersion >= 20)
            sendCollectionChanges();
        } finally {
          endResponse();
        }
      } catch (Exception e) {
        if (connection != null && connection.database != null) {
          if (connection.database.getTransaction().isActive())
            connection.database.rollback(true);

          final OSBTreeCollectionManager collectionManager = connection.database.getSbTreeCollectionManager();
          if (collectionManager != null)
            collectionManager.clearChangedIds();
        }

        sendErrorOrDropConnection(clientTxId, e);
      }
    } catch (OTransactionAbortedException e) {
      // TX ABORTED BY THE CLIENT
    } catch (Exception e) {
      // Error during TX initialization, possibly index constraints violation.
      if (tx.isActive())
        tx.rollback(true, -1);

      sendErrorOrDropConnection(clientTxId, e);
    }
  }

  protected void command() throws IOException {
    setDataCommandInfo("Execute remote command");

    byte type = channel.readByte();
    final boolean live = type == 'l';
    final boolean asynch = type == 'a';
    String dbSerializerName = connection.database.getSerializer().toString();
    String name = getRecordSerializerName();

    if (!dbSerializerName.equals(name)) {
      ORecordSerializer ser = ORecordSerializerFactory.instance().getFormat(name);
      ONetworkThreadLocalSerializer.setNetworkSerializer(ser);
    }
    final OCommandRequestText command = (OCommandRequestText) OStreamSerializerAnyStreamable.INSTANCE.fromStream(channel
        .readBytes());
    ONetworkThreadLocalSerializer.setNetworkSerializer(null);

    connection.data.commandDetail = command.getText();

    beginResponse();
    try {
      connection.data.command = command;
      OAbstractCommandResultListener listener = null;

      OLiveCommandResultListener liveListener = null;
      if (live) {
        liveListener = new OLiveCommandResultListener(this, clientTxId, command.getResultListener());
        listener = new OSyncCommandResultListener();
        command.setResultListener(liveListener);
      } else if (asynch) {
        listener = new OAsyncCommandResultListener(this, clientTxId, command.getResultListener());
        command.setResultListener(listener);
      } else
        listener = new OSyncCommandResultListener();

      final long serverTimeout = OGlobalConfiguration.COMMAND_TIMEOUT.getValueAsLong();

      if (serverTimeout > 0 && command.getTimeoutTime() > serverTimeout)
        // FORCE THE SERVER'S TIMEOUT
        command.setTimeout(serverTimeout, command.getTimeoutStrategy());

      if (!isConnectionAlive())
        return;

      // ASSIGNED THE PARSED FETCHPLAN
      listener.setFetchPlan(connection.database.command(command).getFetchPlan());

      final Object result = connection.database.command(command).execute();

      // FETCHPLAN HAS TO BE ASSIGNED AGAIN, because it can be changed by SQL statement
      listener.setFetchPlan(command.getFetchPlan());

      if (asynch) {
        // ASYNCHRONOUS
        if (listener.isEmpty())
          try {
            sendOk(clientTxId);
          } catch (IOException ignored) {
          }
        channel.writeByte((byte) 0); // NO MORE RECORDS

      } else {
        // SYNCHRONOUS
        sendOk(clientTxId);

        if (result == null) {
          // NULL VALUE
          channel.writeByte((byte) 'n');
        } else if (result instanceof OIdentifiable) {
          // RECORD
          channel.writeByte((byte) 'r');
          listener.result(result);
          writeIdentifiable((OIdentifiable) result);
        } else if (result instanceof ODocumentWrapper) {
          // RECORD
          channel.writeByte((byte) 'r');
          final ODocument doc = ((ODocumentWrapper) result).getDocument();
          listener.result(doc);
          writeIdentifiable(doc);
        } else if (OMultiValue.isMultiValue(result)) {
          channel.writeByte((byte) 'l');
          channel.writeInt(OMultiValue.getSize(result));
          for (Object o : OMultiValue.getMultiValueIterable(result)) {
            try {
              listener.result(o);
              writeIdentifiable((OIdentifiable) o);
            } catch (Exception e) {
              OLogManager.instance().warn(this, "Cannot serialize record: " + o);
              // WRITE NULL RECORD TO AVOID BREAKING PROTOCOL
              writeIdentifiable(null);
            }
          }
        } else {
          // ANY OTHER (INCLUDING LITERALS)
          channel.writeByte((byte) 'a');
          final StringBuilder value = new StringBuilder(64);
          listener.result(result);
          ORecordSerializerStringAbstract.fieldTypeToString(value, OType.getTypeByClass(result.getClass()), result);
          channel.writeString(value.toString());
        }

        if (connection.data.protocolVersion >= 17 && listener instanceof OSyncCommandResultListener) {
          // SEND FETCHED RECORDS TO LOAD IN CLIENT CACHE
          for (ORecord rec : ((OSyncCommandResultListener) listener).getFetchedRecordsToSend()) {
            channel.writeByte((byte) 2); // CLIENT CACHE RECORD. IT
            // ISN'T PART OF THE
            // RESULT SET
            writeIdentifiable(rec);
          }

          channel.writeByte((byte) 0); // NO MORE RECORDS
        }
      }

    } finally {
      connection.data.command = null;
      endResponse();
    }
  }

  protected void deleteRecord() throws IOException {
    setDataCommandInfo("Delete record");

    if (!isConnectionAlive())
      return;

    final ORID rid = channel.readRID();
    final ORecordVersion version = channel.readVersion();
    final byte mode = channel.readByte();

    final int result = deleteRecord(connection.database, rid, version);

    if (mode < 2) {
      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeByte((byte) result);
      } finally {
        endResponse();
      }
    }
  }

  protected void hideRecord() throws IOException {
    setDataCommandInfo("Hide record");

    if (!isConnectionAlive())
      return;

    final ORID rid = channel.readRID();
    final byte mode = channel.readByte();

    final int result = hideRecord(connection.database, rid);

    if (mode < 2) {
      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeByte((byte) result);
      } finally {
        endResponse();
      }
    }
  }

  protected void cleanOutRecord() throws IOException {
    setDataCommandInfo("Clean out record");

    if (!isConnectionAlive())
      return;

    final ORID rid = channel.readRID();
    final ORecordVersion version = channel.readVersion();
    final byte mode = channel.readByte();

    final int result = cleanOutRecord(connection.database, rid, version);

    if (mode < 2) {
      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeByte((byte) result);
      } finally {
        endResponse();
      }
    }
  }

  /**
   * VERSION MANAGEMENT:<br>
   * -1 : DOCUMENT UPDATE, NO VERSION CONTROL<br>
   * -2 : DOCUMENT UPDATE, NO VERSION CONTROL, NO VERSION INCREMENT<br>
   * -3 : DOCUMENT ROLLBACK, DECREMENT VERSION<br>
   * >-1 : MVCC CONTROL, RECORD UPDATE AND VERSION INCREMENT<br>
   * <-3 : WRONG VERSION VALUE
   *
   * @throws IOException
   */
  protected void updateRecord() throws IOException {
    setDataCommandInfo("Update record");

    if (!isConnectionAlive())
      return;

    final ORecordId rid = channel.readRID();
    boolean updateContent = true;
    if (connection.data.protocolVersion >= 23)
      updateContent = channel.readBoolean();
    final byte[] buffer = channel.readBytes();
    final ORecordVersion version = channel.readVersion();
    final byte recordType = channel.readByte();
    final byte mode = channel.readByte();

    final ORecordVersion newVersion = updateRecord(connection.database, rid, buffer, version, recordType, updateContent);

    if (mode < 2) {
      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeVersion(newVersion);

        if (connection.data.protocolVersion >= 20)
          sendCollectionChanges();
      } finally {
        endResponse();
      }
    }
  }

  protected void createRecord() throws IOException {
    setDataCommandInfo("Create record");

    if (!isConnectionAlive())
      return;

    final int dataSegmentId = connection.data.protocolVersion >= 10 && connection.data.protocolVersion < 24 ? channel.readInt() : 0;

    final ORecordId rid = new ORecordId(channel.readShort(), ORID.CLUSTER_POS_INVALID);
    final byte[] buffer = channel.readBytes();
    final byte recordType = channel.readByte();
    final byte mode = channel.readByte();

    final ORecord record = createRecord(connection.database, rid, buffer, recordType);

    if (mode < 2) {
      beginResponse();
      try {
        sendOk(clientTxId);
        if (connection.data.protocolVersion > OChannelBinaryProtocol.PROTOCOL_VERSION_25)
          channel.writeShort((short) record.getIdentity().getClusterId());
        channel.writeLong(record.getIdentity().getClusterPosition());
        if (connection.data.protocolVersion >= 11)
          channel.writeVersion(record.getRecordVersion());

        if (connection.data.protocolVersion >= 20)
          sendCollectionChanges();
      } finally {
        endResponse();
      }
    }
  }

  protected void readRecordMetadata() throws IOException {
    setDataCommandInfo("Record metadata");

    final ORID rid = channel.readRID();

    beginResponse();
    try {
      final ORecordMetadata metadata = connection.database.getRecordMetadata(rid);
      if (metadata != null) {
        sendOk(clientTxId);
        channel.writeRID(metadata.getRecordId());
        channel.writeVersion(metadata.getRecordVersion());
      } else {
        throw new ODatabaseException(String.format("Record metadata for RID: %s, Not found", rid));
      }
    } finally {
      endResponse();
    }
  }

  protected void readRecord() throws IOException {
    setDataCommandInfo("Load record");

    if (!isConnectionAlive())
      return;

    final ORecordId rid = channel.readRID();
    final String fetchPlanString = channel.readString();
    boolean ignoreCache = false;
    if (connection.data.protocolVersion >= 9)
      ignoreCache = channel.readByte() == 1;

    boolean loadTombstones = false;
    if (connection.data.protocolVersion >= 13)
      loadTombstones = channel.readByte() > 0;

    if (rid.clusterId == 0 && rid.clusterPosition == 0) {
      // @COMPATIBILITY 0.9.25
      // SEND THE DB CONFIGURATION INSTEAD SINCE IT WAS ON RECORD 0:0
      OFetchHelper.checkFetchPlanValid(fetchPlanString);

      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeByte((byte) 1);
        if (connection.data.protocolVersion <= OChannelBinaryProtocol.PROTOCOL_VERSION_27) {
          channel.writeBytes(connection.database.getStorage().getConfiguration().toStream(connection.data.protocolVersion));
          channel.writeVersion(OVersionFactory.instance().createVersion());
          channel.writeByte(ORecordBytes.RECORD_TYPE);
        } else {
          channel.writeByte(ORecordBytes.RECORD_TYPE);
          channel.writeVersion(OVersionFactory.instance().createVersion());
          channel.writeBytes(connection.database.getStorage().getConfiguration().toStream(connection.data.protocolVersion));
        }
        channel.writeByte((byte) 0); // NO MORE RECORDS
      } finally {
        endResponse();
      }

    } else {
      final ORecord record = connection.database.load(rid, fetchPlanString, ignoreCache, loadTombstones,
          OStorage.LOCKING_STRATEGY.NONE);

      beginResponse();
      try {
        sendOk(clientTxId);

        if (record != null) {
          channel.writeByte((byte) 1); // HAS RECORD
          byte[] bytes = getRecordBytes(record);
          int length = trimCsvSerializedContent(bytes);
          if (connection.data.protocolVersion <= OChannelBinaryProtocol.PROTOCOL_VERSION_27) {
            channel.writeBytes(bytes, length);
            channel.writeVersion(record.getRecordVersion());
            channel.writeByte(ORecordInternal.getRecordType(record));
          } else {
            channel.writeByte(ORecordInternal.getRecordType(record));
            channel.writeVersion(record.getRecordVersion());
            channel.writeBytes(bytes, length);
          }

          if (fetchPlanString.length() > 0) {
            // BUILD THE SERVER SIDE RECORD TO ACCES TO THE FETCH
            // PLAN
            if (record instanceof ODocument) {
              final OFetchPlan fetchPlan = OFetchHelper.buildFetchPlan(fetchPlanString);

              final Set<ORecord> recordsToSend = new HashSet<ORecord>();
              final ODocument doc = (ODocument) record;
              final OFetchListener listener = new ORemoteFetchListener() {
                @Override
                protected void sendRecord(ORecord iLinked) {
                  recordsToSend.add(iLinked);
                }
              };
              final OFetchContext context = new ORemoteFetchContext();
              OFetchHelper.fetch(doc, doc, fetchPlan, listener, context, "");

              // SEND RECORDS TO LOAD IN CLIENT CACHE
              for (ORecord d : recordsToSend) {
                if (d.getIdentity().isValid()) {
                  channel.writeByte((byte) 2); // CLIENT CACHE
                  // RECORD. IT ISN'T PART OF THE RESULT SET
                  writeIdentifiable(d);
                }
              }
            }

          }
        }
        channel.writeByte((byte) 0); // NO MORE RECORDS

      } finally {
        endResponse();
      }
    }
  }

  protected void readRecordIfVersionIsNotLatest() throws IOException {
    setDataCommandInfo("Load record if version is not latest");

    if (!isConnectionAlive())
      return;

    final ORecordId rid = channel.readRID();
    final ORecordVersion recordVersion = channel.readVersion();
    final String fetchPlanString = channel.readString();

    boolean ignoreCache = channel.readByte() == 1;

    if (rid.clusterId == 0 && rid.clusterPosition == 0) {
      // @COMPATIBILITY 0.9.25
      // SEND THE DB CONFIGURATION INSTEAD SINCE IT WAS ON RECORD 0:0
      OFetchHelper.checkFetchPlanValid(fetchPlanString);

      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeByte((byte) 1);
        if (connection.data.protocolVersion <= OChannelBinaryProtocol.PROTOCOL_VERSION_27) {
          channel.writeBytes(connection.database.getStorage().getConfiguration().toStream(connection.data.protocolVersion));
          channel.writeVersion(OVersionFactory.instance().createVersion());
          channel.writeByte(ORecordBytes.RECORD_TYPE);
        } else {
          channel.writeByte(ORecordBytes.RECORD_TYPE);
          channel.writeVersion(OVersionFactory.instance().createVersion());
          channel.writeBytes(connection.database.getStorage().getConfiguration().toStream(connection.data.protocolVersion));
        }
        channel.writeByte((byte) 0); // NO MORE RECORDS
      } finally {
        endResponse();
      }

    } else {
      final ORecord record = connection.database.loadIfVersionIsNotLatest(rid, recordVersion, fetchPlanString, ignoreCache);

      beginResponse();
      try {
        sendOk(clientTxId);

        if (record != null) {
          channel.writeByte((byte) 1); // HAS RECORD
          byte[] bytes = getRecordBytes(record);
          int length = trimCsvSerializedContent(bytes);

          channel.writeByte(ORecordInternal.getRecordType(record));
          channel.writeVersion(record.getRecordVersion());
          channel.writeBytes(bytes, length);

          if (fetchPlanString.length() > 0) {
            // BUILD THE SERVER SIDE RECORD TO ACCES TO THE FETCH
            // PLAN
            if (record instanceof ODocument) {
              final OFetchPlan fetchPlan = OFetchHelper.buildFetchPlan(fetchPlanString);

              final Set<ORecord> recordsToSend = new HashSet<ORecord>();
              final ODocument doc = (ODocument) record;
              final OFetchListener listener = new ORemoteFetchListener() {
                @Override
                protected void sendRecord(ORecord iLinked) {
                  recordsToSend.add(iLinked);
                }
              };
              final OFetchContext context = new ORemoteFetchContext();
              OFetchHelper.fetch(doc, doc, fetchPlan, listener, context, "");

              // SEND RECORDS TO LOAD IN CLIENT CACHE
              for (ORecord d : recordsToSend) {
                if (d.getIdentity().isValid()) {
                  channel.writeByte((byte) 2); // CLIENT CACHE
                  // RECORD. IT ISN'T PART OF THE RESULT SET
                  writeIdentifiable(d);
                }
              }
            }

          }
        }
        channel.writeByte((byte) 0); // NO MORE RECORDS

      } finally {
        endResponse();
      }
    }
  }

  protected void beginResponse() {
    channel.acquireWriteLock();
  }

  protected void endResponse() throws IOException {
    // resetting transaction state. Commands are stateless and connection should be cleared
    // otherwise reused connection (connections pool) may lead to unpredicted errors
    if (connection != null && connection.database != null && connection.database.activateOnCurrentThread().getTransaction() != null) {
      connection.database.activateOnCurrentThread();
      connection.database.getTransaction().rollback();
    }
    channel.flush();
    channel.releaseWriteLock();
  }

  protected void setDataCommandInfo(final String iCommandInfo) {
    if (connection != null)
      connection.data.commandInfo = iCommandInfo;
  }

  protected void readConnectionData() throws IOException {
    connection.data.driverName = channel.readString();
    connection.data.driverVersion = channel.readString();
    connection.data.protocolVersion = channel.readShort();
    connection.data.clientId = channel.readString();
    if (connection.data.protocolVersion > OChannelBinaryProtocol.PROTOCOL_VERSION_21)
      connection.data.serializationImpl = channel.readString();
    else
      connection.data.serializationImpl = ORecordSerializerSchemaAware2CSV.NAME;
    if (tokenBased == null) {
      if (connection.data.protocolVersion > OChannelBinaryProtocol.PROTOCOL_VERSION_26)
        tokenBased = channel.readBoolean();
      else
        tokenBased = false;
    } else {
      if (connection.data.protocolVersion > OChannelBinaryProtocol.PROTOCOL_VERSION_26)
        if (channel.readBoolean() != tokenBased) {
          // throw new OException("Not supported mixed connection managment");
        }
    }
    if (tokenBased && tokenHandler == null) {
      // this is not the way
      // throw new OException("The server doesn't support the token based authentication");
      tokenBased = false;
    }
  }

  protected void sendOk(final int iClientTxId) throws IOException {
    channel.writeByte(OChannelBinaryProtocol.RESPONSE_STATUS_OK);
    channel.writeInt(iClientTxId);
    if (Boolean.TRUE.equals(tokenBased) && token != null && requestType != OChannelBinaryProtocol.REQUEST_CONNECT
        && requestType != OChannelBinaryProtocol.REQUEST_DB_OPEN) {
      // TODO: Check if the token is expiring and if it is send a new token
      byte[] renewedToken = tokenHandler.renewIfNeeded(token);
      channel.writeBytes(renewedToken);
    }
  }

  @Override
  protected void handleConnectionError(final OChannelBinaryServer iChannel, final Throwable e) {
    super.handleConnectionError(channel, e);
    OServerPluginHelper.invokeHandlerCallbackOnClientError(server, connection, e);
  }

  protected void sendResponse(final ODocument iResponse) throws IOException {
    beginResponse();
    try {
      sendOk(clientTxId);
      channel.writeBytes(iResponse != null ? iResponse.toStream() : null);
    } finally {
      endResponse();
    }
  }

  protected void freezeDatabase() throws IOException {
    setDataCommandInfo("Freeze database");
    String dbName = channel.readString();

    checkServerAccess("database.freeze");

    final String storageType;

    if (connection.data.protocolVersion >= 16)
      storageType = channel.readString();
    else
      storageType = "local";

    connection.database = getDatabaseInstance(dbName, ODatabaseDocument.TYPE, storageType);

    if (connection.database.exists()) {
      OLogManager.instance().info(this, "Freezing database '%s'", connection.database.getURL());

      if (connection.database.isClosed())
        openDatabase(connection.database, connection.serverUser.name, connection.serverUser.password);

      connection.database.freeze(true);
    } else {
      throw new OStorageException("Database with name '" + dbName + "' doesn't exits.");
    }

    beginResponse();
    try {
      sendOk(clientTxId);
    } finally {
      endResponse();
    }
  }

  protected void releaseDatabase() throws IOException {
    setDataCommandInfo("Release database");
    String dbName = channel.readString();

    checkServerAccess("database.release");

    final String storageType;
    if (connection.data.protocolVersion >= 16)
      storageType = channel.readString();
    else
      storageType = "local";

    connection.database = getDatabaseInstance(dbName, ODatabaseDocument.TYPE, storageType);

    if (connection.database.exists()) {
      OLogManager.instance().info(this, "Realising database '%s'", connection.database.getURL());

      if (connection.database.isClosed())
        openDatabase(connection.database, connection.serverUser.name, connection.serverUser.password);

      connection.database.release();
    } else {
      throw new OStorageException("Database with name '" + dbName + "' doesn't exits.");
    }

    beginResponse();
    try {
      sendOk(clientTxId);
    } finally {
      endResponse();
    }
  }

  protected void freezeCluster() throws IOException {
    setDataCommandInfo("Freeze cluster");
    final String dbName = channel.readString();
    final int clusterId = channel.readShort();

    checkServerAccess("database.freeze");

    final String storageType;

    if (connection.data.protocolVersion >= 16)
      storageType = channel.readString();
    else
      storageType = "local";

    connection.database = getDatabaseInstance(dbName, ODatabaseDocument.TYPE, storageType);

    if (connection.database.exists()) {
      OLogManager.instance().info(this, "Freezing database '%s' cluster %d", connection.database.getURL(), clusterId);

      if (connection.database.isClosed()) {
        openDatabase(connection.database, connection.serverUser.name, connection.serverUser.password);
      }

      connection.database.freezeCluster(clusterId);
    } else {
      throw new OStorageException("Database with name '" + dbName + "' doesn't exits.");
    }

    beginResponse();
    try {
      sendOk(clientTxId);
    } finally {
      endResponse();
    }
  }

  protected void releaseCluster() throws IOException {
    setDataCommandInfo("Release database");
    final String dbName = channel.readString();
    final int clusterId = channel.readShort();

    checkServerAccess("database.release");

    final String storageType;
    if (connection.data.protocolVersion >= 16)
      storageType = channel.readString();
    else
      storageType = "local";

    connection.database = getDatabaseInstance(dbName, ODatabaseDocument.TYPE, storageType);

    if (connection.database.exists()) {
      OLogManager.instance().info(this, "Realising database '%s' cluster %d", connection.database.getURL(), clusterId);

      if (connection.database.isClosed()) {
        openDatabase(connection.database, connection.serverUser.name, connection.serverUser.password);
      }

      connection.database.releaseCluster(clusterId);
    } else {
      throw new OStorageException("Database with name '" + dbName + "' doesn't exits.");
    }

    beginResponse();
    try {
      sendOk(clientTxId);
    } finally {
      endResponse();
    }
  }

  @Override
  protected String getRecordSerializerName() {
    return connection.data.serializationImpl;
  }

  private void sendErrorDetails(Throwable current) throws IOException {
    while (current != null) {
      // MORE DETAILS ARE COMING AS EXCEPTION
      channel.writeByte((byte) 1);

      channel.writeString(current.getClass().getName());
      channel.writeString(current.getMessage());

      current = current.getCause();
    }
    channel.writeByte((byte) 0);
  }

  private void serializeExceptionObject(Throwable original) throws IOException {
    try {
      final OMemoryStream memoryStream = new OMemoryStream();
      final ObjectOutputStream objectOutputStream = new ObjectOutputStream(memoryStream);

      objectOutputStream.writeObject(original);
      objectOutputStream.flush();

      final byte[] result = memoryStream.toByteArray();
      objectOutputStream.close();

      channel.writeBytes(result);
    } catch (Exception e) {
      OLogManager.instance().warn(this, "Can't serialize an exception object", e);

      // Write empty stream for binary compatibility
      channel.writeBytes(OCommonConst.EMPTY_BYTE_ARRAY);
    }
  }

  /**
   * Due to protocol thread is daemon, shutdown should be executed in separate thread to guarantee its complete execution.
   *
   * This method never returns normally.
   */
  private void runShutdownInNonDaemonThread() {
    Thread shutdownThread = new Thread("OrientDB server shutdown thread") {
      public void run() {
        server.shutdown();
        ShutdownHelper.shutdown(1);
      }
    };
    shutdownThread.setDaemon(false);
    shutdownThread.start();
    try {
      shutdownThread.join();
    } catch (InterruptedException ignored) {
    }
  }

  private void ridBagSize() throws IOException {
    setDataCommandInfo("RidBag get size");

    OBonsaiCollectionPointer collectionPointer = OCollectionNetworkSerializer.INSTANCE.readCollectionPointer(channel);
    final byte[] changeStream = channel.readBytes();

    final OSBTreeCollectionManager sbTreeCollectionManager = connection.database.getSbTreeCollectionManager();
    final OSBTreeBonsai<OIdentifiable, Integer> tree = sbTreeCollectionManager.loadSBTree(collectionPointer);
    try {
      final Map<OIdentifiable, OSBTreeRidBag.Change> changes = OSBTreeRidBag.ChangeSerializationHelper.INSTANCE.deserializeChanges(
          changeStream, 0);

      int realSize = tree.getRealBagSize(changes);

      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeInt(realSize);
      } finally {
        endResponse();
      }
    } finally {
      sbTreeCollectionManager.releaseSBTree(collectionPointer);
    }
  }

  private void sbTreeBonsaiGetEntriesMajor() throws IOException {
    setDataCommandInfo("SB-Tree bonsai get values major");

    OBonsaiCollectionPointer collectionPointer = OCollectionNetworkSerializer.INSTANCE.readCollectionPointer(channel);
    byte[] keyStream = channel.readBytes();
    boolean inclusive = channel.readBoolean();
    int pageSize = 128;

    if (connection.data.protocolVersion >= 21)
      pageSize = channel.readInt();

    final OSBTreeCollectionManager sbTreeCollectionManager = connection.database.getSbTreeCollectionManager();
    final OSBTreeBonsai<OIdentifiable, Integer> tree = sbTreeCollectionManager.loadSBTree(collectionPointer);
    try {
      final OBinarySerializer<OIdentifiable> keySerializer = tree.getKeySerializer();
      OIdentifiable key = keySerializer.deserialize(keyStream, 0);

      final OBinarySerializer<Integer> valueSerializer = tree.getValueSerializer();

      OTreeInternal.AccumulativeListener<OIdentifiable, Integer> listener = new OTreeInternal.AccumulativeListener<OIdentifiable, Integer>(
          pageSize);
      tree.loadEntriesMajor(key, inclusive, true, listener);
      List<Entry<OIdentifiable, Integer>> result = listener.getResult();
      byte[] stream = serializeSBTreeEntryCollection(result, keySerializer, valueSerializer);

      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeBytes(stream);
      } finally {
        endResponse();
      }
    } finally {
      sbTreeCollectionManager.releaseSBTree(collectionPointer);
    }
  }

  private byte[] serializeSBTreeEntryCollection(List<Entry<OIdentifiable, Integer>> collection,
      OBinarySerializer<OIdentifiable> keySerializer, OBinarySerializer<Integer> valueSerializer) {
    byte[] stream = new byte[OIntegerSerializer.INT_SIZE + collection.size()
        * (keySerializer.getFixedLength() + valueSerializer.getFixedLength())];
    int offset = 0;

    OIntegerSerializer.INSTANCE.serializeLiteral(collection.size(), stream, offset);
    offset += OIntegerSerializer.INT_SIZE;

    for (Entry<OIdentifiable, Integer> entry : collection) {
      keySerializer.serialize(entry.getKey(), stream, offset);
      offset += keySerializer.getObjectSize(entry.getKey());

      valueSerializer.serialize(entry.getValue(), stream, offset);
      offset += valueSerializer.getObjectSize(entry.getValue());
    }
    return stream;
  }

  private void sbTreeBonsaiFirstKey() throws IOException {
    setDataCommandInfo("SB-Tree bonsai get first key");

    OBonsaiCollectionPointer collectionPointer = OCollectionNetworkSerializer.INSTANCE.readCollectionPointer(channel);

    final OSBTreeCollectionManager sbTreeCollectionManager = connection.database.getSbTreeCollectionManager();
    final OSBTreeBonsai<OIdentifiable, Integer> tree = sbTreeCollectionManager.loadSBTree(collectionPointer);
    try {
      OIdentifiable result = tree.firstKey();
      final OBinarySerializer<? super OIdentifiable> keySerializer;
      if (result == null) {
        keySerializer = ONullSerializer.INSTANCE;
      } else {
        keySerializer = tree.getKeySerializer();
      }

      byte[] stream = new byte[OByteSerializer.BYTE_SIZE + keySerializer.getObjectSize(result)];
      OByteSerializer.INSTANCE.serialize(keySerializer.getId(), stream, 0);
      keySerializer.serialize(result, stream, OByteSerializer.BYTE_SIZE);

      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeBytes(stream);
      } finally {
        endResponse();
      }
    } finally {
      sbTreeCollectionManager.releaseSBTree(collectionPointer);
    }
  }

  private void sbTreeBonsaiGet() throws IOException {
    setDataCommandInfo("SB-Tree bonsai get");

    OBonsaiCollectionPointer collectionPointer = OCollectionNetworkSerializer.INSTANCE.readCollectionPointer(channel);
    final byte[] keyStream = channel.readBytes();

    final OSBTreeCollectionManager sbTreeCollectionManager = connection.database.getSbTreeCollectionManager();
    final OSBTreeBonsai<OIdentifiable, Integer> tree = sbTreeCollectionManager.loadSBTree(collectionPointer);
    try {
      final OIdentifiable key = tree.getKeySerializer().deserialize(keyStream, 0);

      Integer result = tree.get(key);
      final OBinarySerializer<? super Integer> valueSerializer;
      if (result == null) {
        valueSerializer = ONullSerializer.INSTANCE;
      } else {
        valueSerializer = tree.getValueSerializer();
      }

      byte[] stream = new byte[OByteSerializer.BYTE_SIZE + valueSerializer.getObjectSize(result)];
      OByteSerializer.INSTANCE.serialize(valueSerializer.getId(), stream, 0);
      valueSerializer.serialize(result, stream, OByteSerializer.BYTE_SIZE);

      beginResponse();
      try {
        sendOk(clientTxId);
        channel.writeBytes(stream);
      } finally {
        endResponse();
      }
    } finally {
      sbTreeCollectionManager.releaseSBTree(collectionPointer);
    }
  }

  private void createSBTreeBonsai() throws IOException {
    setDataCommandInfo("Create SB-Tree bonsai instance");

    int clusterId = channel.readInt();

    OBonsaiCollectionPointer collectionPointer = connection.database.getSbTreeCollectionManager().createSBTree(clusterId, null);

    beginResponse();
    try {
      sendOk(clientTxId);
      OCollectionNetworkSerializer.INSTANCE.writeCollectionPointer(channel, collectionPointer);
    } finally {
      endResponse();
    }
  }

  private void lowerPositions() throws IOException {
    setDataCommandInfo("Retrieve lower positions");

    final int clusterId = channel.readInt();
    final long clusterPosition = channel.readLong();

    beginResponse();
    try {
      sendOk(clientTxId);

      final OPhysicalPosition[] previousPositions = connection.database.getStorage().lowerPhysicalPositions(clusterId,
          new OPhysicalPosition(clusterPosition));

      if (previousPositions != null) {
        channel.writeInt(previousPositions.length);

        for (final OPhysicalPosition physicalPosition : previousPositions) {
          channel.writeLong(physicalPosition.clusterPosition);
          channel.writeInt(physicalPosition.recordSize);
          channel.writeVersion(physicalPosition.recordVersion);
        }

      } else {
        channel.writeInt(0); // NO MORE RECORDS
      }

    } finally {
      endResponse();
    }
  }

  private void floorPositions() throws IOException {
    setDataCommandInfo("Retrieve floor positions");

    final int clusterId = channel.readInt();
    final long clusterPosition = channel.readLong();

    beginResponse();
    try {
      sendOk(clientTxId);

      final OPhysicalPosition[] previousPositions = connection.database.getStorage().floorPhysicalPositions(clusterId,
          new OPhysicalPosition(clusterPosition));

      if (previousPositions != null) {
        channel.writeInt(previousPositions.length);

        for (final OPhysicalPosition physicalPosition : previousPositions) {
          channel.writeLong(physicalPosition.clusterPosition);
          channel.writeInt(physicalPosition.recordSize);
          channel.writeVersion(physicalPosition.recordVersion);
        }

      } else {
        channel.writeInt(0); // NO MORE RECORDS
      }

    } finally {
      endResponse();
    }
  }

  private void higherPositions() throws IOException {
    setDataCommandInfo("Retrieve higher positions");

    final int clusterId = channel.readInt();
    final long clusterPosition = channel.readLong();

    beginResponse();
    try {
      sendOk(clientTxId);

      OPhysicalPosition[] nextPositions = connection.database.getStorage().higherPhysicalPositions(clusterId,
          new OPhysicalPosition(clusterPosition));

      if (nextPositions != null) {

        channel.writeInt(nextPositions.length);
        for (final OPhysicalPosition physicalPosition : nextPositions) {
          channel.writeLong(physicalPosition.clusterPosition);
          channel.writeInt(physicalPosition.recordSize);
          channel.writeVersion(physicalPosition.recordVersion);
        }
      } else {
        channel.writeInt(0); // NO MORE RECORDS
      }
    } finally {
      endResponse();
    }
  }

  private void ceilingPositions() throws IOException {
    setDataCommandInfo("Retrieve ceiling positions");

    final int clusterId = channel.readInt();
    final long clusterPosition = channel.readLong();

    beginResponse();
    try {
      sendOk(clientTxId);

      final OPhysicalPosition[] previousPositions = connection.database.getStorage().ceilingPhysicalPositions(clusterId,
          new OPhysicalPosition(clusterPosition));

      if (previousPositions != null) {
        channel.writeInt(previousPositions.length);

        for (final OPhysicalPosition physicalPosition : previousPositions) {
          channel.writeLong(physicalPosition.clusterPosition);
          channel.writeInt(physicalPosition.recordSize);
          channel.writeVersion(physicalPosition.recordVersion);
        }

      } else {
        channel.writeInt(0); // NO MORE RECORDS
      }

    } finally {
      endResponse();
    }
  }

  private boolean isConnectionAlive() {
    if (connection == null || connection.database == null) {
      // CONNECTION/DATABASE CLOSED, KILL IT
      OClientConnectionManager.instance().kill(connection);
      return false;
    }
    return true;
  }

  private void sendCollectionChanges() throws IOException {
    OSBTreeCollectionManager collectionManager = connection.database.getSbTreeCollectionManager();
    if (collectionManager != null) {
      Map<UUID, OBonsaiCollectionPointer> changedIds = collectionManager.changedIds();

      channel.writeInt(changedIds.size());

      for (Entry<UUID, OBonsaiCollectionPointer> entry : changedIds.entrySet()) {
        UUID id = entry.getKey();
        channel.writeLong(id.getMostSignificantBits());
        channel.writeLong(id.getLeastSignificantBits());

        OCollectionNetworkSerializer.INSTANCE.writeCollectionPointer(channel, entry.getValue());
      }
      collectionManager.clearChangedIds();
    }
  }

  private void sendDatabaseInformation() throws IOException {
    final Collection<? extends OCluster> clusters = connection.database.getStorage().getClusterInstances();
    int clusterCount = 0;
    for (OCluster c : clusters) {
      if (c != null) {
        ++clusterCount;
      }
    }
    if (connection.data.protocolVersion >= 7)
      channel.writeShort((short) clusterCount);
    else
      channel.writeInt(clusterCount);

    for (OCluster c : clusters) {
      if (c != null) {
        channel.writeString(c.getName());
        channel.writeShort((short) c.getId());

        if (connection.data.protocolVersion >= 12 && connection.data.protocolVersion < 24) {
          channel.writeString("none");
          channel.writeShort((short) -1);
        }
      }
    }
  }

  private void listDatabases() throws IOException {
    checkServerAccess("server.dblist");
    final ODocument result = new ODocument();
    result.field("databases", server.getAvailableStorageNames());

    setDataCommandInfo("List databases");

    beginResponse();
    try {
      sendOk(clientTxId);
      byte[] stream = getRecordBytes(result);
      channel.writeBytes(stream);
    } finally {
      endResponse();
    }
  }

  private boolean loadUserFromSchema(final String iUserName, final String iUserPassword) {
    connection.database.getMetadata().getSecurity().authenticate(iUserName, iUserPassword);
    return true;
  }

}
