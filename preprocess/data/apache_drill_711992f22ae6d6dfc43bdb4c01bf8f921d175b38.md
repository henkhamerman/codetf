Refactoring Types: ['Extract Method']
ache/drill/jdbc/impl/DrillCursor.java
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
package org.apache.drill.jdbc.impl;

import java.sql.SQLException;
import java.util.Calendar;
import java.util.List;

import net.hydromatic.avatica.ArrayImpl.Factory;
import net.hydromatic.avatica.ColumnMetaData;
import net.hydromatic.avatica.Cursor;

import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.record.BatchSchema;
import org.apache.drill.exec.record.RecordBatchLoader;
import org.apache.drill.exec.rpc.user.QueryDataBatch;
import org.slf4j.Logger;
import static org.slf4j.LoggerFactory.getLogger;


class DrillCursor implements Cursor {
  private static final Logger logger = getLogger( DrillCursor.class );

  private static final String UNKNOWN = "--UNKNOWN--";

  /** The associated {@link java.sql.ResultSet} implementation. */
  private final DrillResultSetImpl resultSet;

  /** Holds current batch of records (none before first load). */
  private final RecordBatchLoader currentBatchHolder;

  private final DrillResultSetImpl.ResultsListener resultsListener;

  private final DrillAccessorList accessors = new DrillAccessorList();

  /** Schema of current batch (null before first load). */
  private BatchSchema schema;

  /** ... corresponds to current schema. */
  private DrillColumnMetaDataList columnMetaDataList;

  /** Whether we're past the special first call to this.next() from
   * DrillResultSetImpl.execute(). */
  private boolean initialSchemaLoaded = false;

  /** Whether after first batch.  (Re skipping spurious empty batches.) */
  private boolean afterFirstBatch = false;

  /**
   * Whether the next call to this.next() should just return {@code true} rather
   * than trying to actually advance to the next record.
   * <p>
   *   Currently, can be true only for first call to next().
   * </p>
   * <p>
   *   (Relates to loadInitialSchema()'s calling nextRowInternally()
   *   one "extra" time
   *   (extra relative to number of ResultSet.next() calls) at the beginning to
   *   get first batch and schema before Statement.execute...(...) even returns.
   * </p>
   */
  private boolean returnTrueForNextCallToNext = false;

  /** Whether cursor is after the end of the sequence of records/rows. */
  private boolean afterLastRow = false;

  /** Zero-based offset of current record in record batch.
   * (Not <i>row</i> number.) */
  private int currentRecordNumber = -1;


  /**
   *
   * @param  resultSet  the associated ResultSet implementation
   */
  DrillCursor(final DrillResultSetImpl resultSet) {
    this.resultSet = resultSet;
    currentBatchHolder = resultSet.batchLoader;
    resultsListener = resultSet.resultsListener;
  }

  DrillResultSetImpl getResultSet() {
    return resultSet;
  }

  protected int getCurrentRecordNumber() {
    return currentRecordNumber;
  }

  @Override
  public List<Accessor> createAccessors(List<ColumnMetaData> types,
                                        Calendar localCalendar, Factory factory) {
    columnMetaDataList = (DrillColumnMetaDataList) types;
    return accessors;
  }

  private void updateColumns() {
    accessors.generateAccessors(this, currentBatchHolder);
    columnMetaDataList.updateColumnMetaData(UNKNOWN, UNKNOWN, UNKNOWN, schema);
    if (getResultSet().changeListener != null) {
      getResultSet().changeListener.schemaChanged(schema);
    }
  }

  /**
   * Advances this cursor to the next row, if any, or to after the sequence of
   * rows if no next row.  However, the first call does not advance to the first
   * row, only reading schema information.
   * <p>
   *   Is to be called (once) from {@link DrillResultSetImpl#execute()}, and
   *   then from {@link AvaticaResultSet#next()}.
   * </p>
   *
   * @return  whether cursor is positioned at a row (false when after end of
   *   results)
   */
  @Override
  public boolean next() throws SQLException {
    if (!initialSchemaLoaded) {
      initialSchemaLoaded = true;
      returnTrueForNextCallToNext = true;
    } else if (returnTrueForNextCallToNext && !afterLastRow) {
      // We have a deferred "not after end" to report--reset and report that.
      returnTrueForNextCallToNext = false;
      return true;
    }

    if (afterLastRow) {
      // We're already after end of rows/records--just report that after end.
      return false;
    }

    if (currentRecordNumber + 1 < currentBatchHolder.getRecordCount()) {
      // Have next row in current batch--just advance index and report "at a row."
      currentRecordNumber++;
      return true;
    } else {
      // No (more) records in any current batch--try to get first or next batch.
      // (First call always takes this branch.)

      try {
        QueryDataBatch qrb = resultsListener.getNext();

        // (Apparently:)  Skip any spurious empty batches (batches that have
        // zero rows and/or null data, other than the first batch (which carries
        // the (initial) schema but no rows)).
        while ( qrb != null
                && ( qrb.getHeader().getRowCount() == 0
                     || qrb.getData() == null )
                && afterFirstBatch ) {
          // Empty message--dispose of and try to get another.
          logger.warn( "Spurious batch read: {}", qrb );

          qrb.release();

          qrb = resultsListener.getNext();

          // NOTE:  It is unclear why this check does not check getRowCount()
          // as the loop condition above does.
          if ( qrb != null && qrb.getData() == null ) {
            // Got another batch with null data--dispose of and report "no more
            // rows".

            qrb.release();

            // NOTE:  It is unclear why this returns false but doesn't set
            // afterLastRow (as we do when we normally return false).
            return false;
          }
        }

        afterFirstBatch = true;

        if (qrb == null) {
          // End of batches--clean up, set state to done, report after last row.

          currentBatchHolder.clear();  // (We load it so we clear it.)
          afterLastRow = true;
          return false;
        } else {
          // Got next (or first) batch--reset record offset to beginning,
          // assimilate schema if changed, ... ???

          currentRecordNumber = 0;

          final boolean schemaChanged;
          try {
            schemaChanged = currentBatchHolder.load(qrb.getHeader().getDef(),
                                                    qrb.getData());
          }
          finally {
            qrb.release();
          }
          schema = currentBatchHolder.getSchema();
          if (schemaChanged) {
            updateColumns();
          }

          if (returnTrueForNextCallToNext
              && currentBatchHolder.getRecordCount() == 0) {
            returnTrueForNextCallToNext = false;
          }
          return true;
        }
      }
      catch ( UserException e ) {
        // A normally expected case--for any server-side error (e.g., syntax
        // error in SQL statement).
        // Construct SQLException with message text from the UserException.
        // TODO:  Map UserException error type to SQLException subclass (once
        // error type is accessible, of course. :-( )
        throw new SQLException( e.getMessage(), e );
      }
      catch ( InterruptedException e ) {
        // Not normally expected--Drill doesn't interrupt in this area (right?)--
        // but JDBC client certainly could.
        throw new SQLException( "Interrupted.", e );
      }
      catch ( SchemaChangeException e ) {
        // TODO:  Clean:  DRILL-2933:  RecordBatchLoader.load(...) no longer
        // throws SchemaChangeException, so check/clean catch clause.
        throw new SQLException(
            "Unexpected SchemaChangeException from RecordBatchLoader.load(...)" );
      }
      catch ( RuntimeException e ) {
        throw new SQLException( "Unexpected RuntimeException: " + e.toString(), e );
      }

    }
  }

  @Override
  public void close() {
    // currentBatchHolder is owned by resultSet and cleaned up by
    // DrillResultSet.cleanup()

    // listener is owned by resultSet and cleaned up by
    // DrillResultSet.cleanup()

    // Clean up result set (to deallocate any buffers).
    getResultSet().cleanup();
    // TODO:  CHECK:  Something might need to set statement.openResultSet to
    // null.  Also, AvaticaResultSet.close() doesn't check whether already
    // closed and skip calls to cursor.close(), statement.onResultSetClose()
  }

  @Override
  public boolean wasNull() throws SQLException {
    return accessors.wasNull();
  }

}


File: exec/jdbc/src/main/java/org/apache/drill/jdbc/impl/DrillResultSetImpl.java
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
package org.apache.drill.jdbc.impl;

import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.util.TimeZone;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.LinkedBlockingDeque;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import net.hydromatic.avatica.AvaticaPrepareResult;
import net.hydromatic.avatica.AvaticaResultSet;
import net.hydromatic.avatica.AvaticaStatement;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.client.DrillClient;
import org.apache.drill.exec.proto.UserBitShared.QueryId;
import org.apache.drill.exec.proto.UserBitShared.QueryResult.QueryState;
import org.apache.drill.exec.proto.UserBitShared.QueryType;
import org.apache.drill.exec.proto.helper.QueryIdHelper;
import org.apache.drill.exec.record.RecordBatchLoader;
import org.apache.drill.exec.rpc.user.ConnectionThrottle;
import org.apache.drill.exec.rpc.user.QueryDataBatch;
import org.apache.drill.exec.rpc.user.UserResultsListener;
import org.apache.drill.jdbc.AlreadyClosedSqlException;
import org.apache.drill.jdbc.DrillConnection;
import org.apache.drill.jdbc.DrillResultSet;
import org.apache.drill.jdbc.ExecutionCanceledSqlException;
import org.apache.drill.jdbc.SchemaChangeListener;

import static org.slf4j.LoggerFactory.getLogger;
import org.slf4j.Logger;

import com.google.common.collect.Queues;


/**
 * Drill's implementation of {@link ResultSet}.
 */
class DrillResultSetImpl extends AvaticaResultSet implements DrillResultSet {
  @SuppressWarnings("unused")
  private static final org.slf4j.Logger logger =
      org.slf4j.LoggerFactory.getLogger(DrillResultSetImpl.class);

  private final DrillStatementImpl statement;

  SchemaChangeListener changeListener;
  final ResultsListener resultsListener;
  private final DrillClient client;
  // TODO:  Resolve:  Since is barely manipulated here in DrillResultSetImpl,
  //  move down into DrillCursor and have this.clean() have cursor clean it.
  final RecordBatchLoader batchLoader;
  final DrillCursor cursor;
  boolean hasPendingCancelationNotification;

  DrillResultSetImpl(DrillStatementImpl statement, AvaticaPrepareResult prepareResult,
                     ResultSetMetaData resultSetMetaData, TimeZone timeZone) {
    super(statement, prepareResult, resultSetMetaData, timeZone);
    this.statement = statement;
    final int batchQueueThrottlingThreshold =
        this.getStatement().getConnection().getClient().getConfig().getInt(
            ExecConstants.JDBC_BATCH_QUEUE_THROTTLING_THRESHOLD );
    resultsListener = new ResultsListener( batchQueueThrottlingThreshold );
    DrillConnection c = (DrillConnection) statement.getConnection();
    DrillClient client = c.getClient();
    batchLoader = new RecordBatchLoader(client.getAllocator());
    this.client = client;
    cursor = new DrillCursor(this);
  }

  public DrillStatementImpl getStatement() {
    return statement;
  }

  /**
   * Throws AlreadyClosedSqlException or QueryCanceledSqlException if this
   * ResultSet is closed.
   *
   * @throws  ExecutionCanceledSqlException  if ResultSet is closed because of
   *          cancelation and no QueryCanceledSqlException had been thrown yet
   *          for this ResultSet
   * @throws  AlreadyClosedSqlException  if ResultSet is closed
   * @throws  SQLException  if error in calling {@link #isClosed()}
   */
  private void checkNotClosed() throws SQLException {
    if ( isClosed() ) {
      if ( hasPendingCancelationNotification ) {
        hasPendingCancelationNotification = false;
        throw new ExecutionCanceledSqlException(
            "SQL statement execution canceled; ResultSet now closed." );
      }
      else {
        throw new AlreadyClosedSqlException( "ResultSet is already closed." );
      }
    }
  }

  @Override
  public ResultSetMetaData getMetaData() throws SQLException {
    checkNotClosed();
    return super.getMetaData();
  }


  @Override
  protected void cancel() {
    hasPendingCancelationNotification = true;
    cleanup();
    close();
  }

  synchronized void cleanup() {
    if (resultsListener.getQueryId() != null && ! resultsListener.completed) {
      client.cancelQuery(resultsListener.getQueryId());
    }
    resultsListener.close();
    batchLoader.clear();
  }

  @Override
  public boolean next() throws SQLException {
    checkNotClosed();
    // TODO:  Resolve following comments (possibly obsolete because of later
    // addition of preceding call to checkNotClosed.  Also, NOTE that the
    // following check, and maybe some checkNotClosed() calls, probably must
    // synchronize on the statement, per the comment on AvaticaStatement's
    // openResultSet:

    // Next may be called after close has been called (for example after a user
    // cancellation) which in turn sets the cursor to null.  So we must check
    // before we call next.
    // TODO: handle next() after close is called in the Avatica code.
    if (super.cursor != null) {
      return super.next();
    } else {
      return false;
    }
  }

  @Override
  protected DrillResultSetImpl execute() throws SQLException{
    DrillConnectionImpl connection = (DrillConnectionImpl) statement.getConnection();

    connection.getClient().runQuery(QueryType.SQL, this.prepareResult.getSql(),
                                    resultsListener);
    connection.getDriver().handler.onStatementExecute(statement, null);

    super.execute();

    // don't return with metadata until we've achieved at least one return message.
    try {
      // TODO:  Revisit:  Why reaching directly into ResultsListener rather than
      // calling some wait method?
      resultsListener.latch.await();
    } catch ( InterruptedException e ) {
      // Preserve evidence that the interruption occurred so that code higher up
      // on the call stack can learn of the interruption and respond to it if it
      // wants to.
      Thread.currentThread().interrupt();

      // Not normally expected--Drill doesn't interrupt in this area (right?)--
      // but JDBC client certainly could.
      throw new SQLException( "Interrupted", e );
    }

    // Read first (schema-only) batch to initialize result-set metadata from
    // (initial) schema before Statement.execute...(...) returns result set:
    cursor.next();

    return this;
  }

  public String getQueryId() {
    if (resultsListener.getQueryId() != null) {
      return QueryIdHelper.getQueryId(resultsListener.getQueryId());
    } else {
      return null;
    }
  }

  static class ResultsListener implements UserResultsListener {
    private static final Logger logger = getLogger( ResultsListener.class );

    private static volatile int nextInstanceId = 1;

    /** (Just for logging.) */
    private final int instanceId;

    private final int batchQueueThrottlingThreshold;

    /** (Just for logging.) */
    private volatile QueryId queryId;

    /** (Just for logging.) */
    private int lastReceivedBatchNumber;
    /** (Just for logging.) */
    private int lastDequeuedBatchNumber;

    private volatile UserException executionFailureException;

    // TODO:  Revisit "completed".  Determine and document exactly what it
    // means.  Some uses imply that it means that incoming messages indicate
    // that the _query_ has _terminated_ (not necessarily _completing_
    // normally), while some uses imply that it's some other state of the
    // ResultListener.  Some uses seem redundant.)
    volatile boolean completed = false;

    /** Whether throttling of incoming data is active. */
    private final AtomicBoolean throttled = new AtomicBoolean( false );
    private volatile ConnectionThrottle throttle;

    private volatile boolean closed = false;
    // TODO:  Rename.  It's obvious it's a latch--but what condition or action
    // does it represent or control?
    private CountDownLatch latch = new CountDownLatch(1);
    private AtomicBoolean receivedMessage = new AtomicBoolean(false);

    final LinkedBlockingDeque<QueryDataBatch> batchQueue =
        Queues.newLinkedBlockingDeque();


    /**
     * ...
     * @param  batchQueueThrottlingThreshold
     *         queue size threshold for throttling server
     */
    ResultsListener( int batchQueueThrottlingThreshold ) {
      instanceId = nextInstanceId++;
      this.batchQueueThrottlingThreshold = batchQueueThrottlingThreshold;
      logger.debug( "[#{}] Query listener created.", instanceId );
    }

    /**
     * Starts throttling if not currently throttling.
     * @param  throttle  the "throttlable" object to throttle
     * @return  true if actually started (wasn't throttling already)
     */
    private boolean startThrottlingIfNot( ConnectionThrottle throttle ) {
      final boolean started = throttled.compareAndSet( false, true );
      if ( started ) {
        this.throttle = throttle;
        throttle.setAutoRead(false);
      }
      return started;
    }

    /**
     * Stops throttling if currently throttling.
     * @return  true if actually stopped (was throttling)
     */
    private boolean stopThrottlingIfSo() {
      final boolean stopped = throttled.compareAndSet( true, false );
      if ( stopped ) {
        throttle.setAutoRead(true);
        throttle = null;
      }
      return stopped;
    }

    // TODO:  Doc.:  Release what if what is first relative to what?
    private boolean releaseIfFirst() {
      if (receivedMessage.compareAndSet(false, true)) {
        latch.countDown();
        return true;
      }

      return false;
    }

    @Override
    public void queryIdArrived(QueryId queryId) {
      logger.debug( "[#{}] Received query ID: {}.",
                    instanceId, QueryIdHelper.getQueryId( queryId ) );
      this.queryId = queryId;
    }

    @Override
    public void submissionFailed(UserException ex) {
      logger.debug( "Received query failure:", instanceId, ex );
      this.executionFailureException = ex;
      completed = true;
      close();
      logger.info( "[#{}] Query failed: ", instanceId, ex );
    }

    @Override
    public void dataArrived(QueryDataBatch result, ConnectionThrottle throttle) {
      lastReceivedBatchNumber++;
      logger.debug( "[#{}] Received query data batch #{}: {}.",
                    instanceId, lastReceivedBatchNumber, result );

      // If we're in a closed state, just release the message.
      if (closed) {
        result.release();
        // TODO:  Revisit member completed:  Is ResultListener really completed
        // after only one data batch after being closed?
        completed = true;
        return;
      }

      // We're active; let's add to the queue.
      batchQueue.add(result);

      // Throttle server if queue size has exceed threshold.
      if (batchQueue.size() > batchQueueThrottlingThreshold ) {
        if ( startThrottlingIfNot( throttle ) ) {
          logger.debug( "[#{}] Throttling started at queue size {}.",
                        instanceId, batchQueue.size() );
        }
      }

      releaseIfFirst();
    }

    @Override
    public void queryCompleted(QueryState state) {
      logger.debug( "[#{}] Received query completion: {}.", instanceId, state );
      releaseIfFirst();
      completed = true;
    }

    QueryId getQueryId() {
      return queryId;
    }


    /**
     * Gets the next batch of query results from the queue.
     * @return  the next batch, or {@code null} after last batch has been returned
     * @throws UserException
     *         if the query failed
     * @throws InterruptedException
     *         if waiting on the queue was interrupted
     */
    QueryDataBatch getNext() throws UserException, InterruptedException {
      while (true) {
        if (executionFailureException != null) {
          logger.debug( "[#{}] Dequeued query failure exception: {}.",
                        instanceId, executionFailureException );
          throw executionFailureException;
        }
        if (completed && batchQueue.isEmpty()) {
          return null;
        } else {
          QueryDataBatch qdb = batchQueue.poll(50, TimeUnit.MILLISECONDS);
          if (qdb != null) {
            lastDequeuedBatchNumber++;
            logger.debug( "[#{}] Dequeued query data batch #{}: {}.",
                          instanceId, lastDequeuedBatchNumber, qdb );

            // Unthrottle server if queue size has dropped enough below threshold:
            if ( batchQueue.size() < batchQueueThrottlingThreshold / 2
                 || batchQueue.size() == 0  // (in case threshold < 2)
                 ) {
              if ( stopThrottlingIfSo() ) {
                logger.debug( "[#{}] Throttling stopped at queue size {}.",
                              instanceId, batchQueue.size() );
              }
            }
            return qdb;
          }
        }
      }
    }

    void close() {
      logger.debug( "[#{}] Query listener closing.", instanceId );
      closed = true;
      if ( stopThrottlingIfSo() ) {
        logger.debug( "[#{}] Throttling stopped at close() (at queue size {}).",
                      instanceId, batchQueue.size() );
      }
      while (!batchQueue.isEmpty()) {
        QueryDataBatch qdb = batchQueue.poll();
        if (qdb != null && qdb.getData() != null) {
          qdb.getData().release();
        }
      }
      // Close may be called before the first result is received and therefore
      // when the main thread is blocked waiting for the result.  In that case
      // we want to unblock the main thread.
      latch.countDown(); // TODO:  Why not call releaseIfFirst as used elsewhere?
      completed = true;
    }

  }

}
