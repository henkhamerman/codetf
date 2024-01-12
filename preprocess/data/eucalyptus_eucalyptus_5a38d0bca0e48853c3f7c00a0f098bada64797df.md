Refactoring Types: ['Rename Package', 'Move Class']
/com/eucalyptus/cloudwatch/backend/CloudWatchBackendService.java
/*************************************************************************
 * Copyright 2009-2014 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/

package com.eucalyptus.cloudwatch.backend;

import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import net.sf.json.JSONException;
import net.sf.json.JSONSerializer;

import org.apache.log4j.Logger;

import com.eucalyptus.auth.Permissions;
import com.eucalyptus.auth.policy.PolicySpec;
import com.eucalyptus.cloudwatch.common.CloudWatchBackend;
import com.eucalyptus.cloudwatch.common.CloudWatchMetadata;
import com.eucalyptus.cloudwatch.common.backend.msgs.AlarmHistoryItem;
import com.eucalyptus.cloudwatch.common.backend.msgs.AlarmHistoryItems;
import com.eucalyptus.cloudwatch.common.backend.msgs.AlarmNames;
import com.eucalyptus.cloudwatch.common.backend.msgs.Datapoint;
import com.eucalyptus.cloudwatch.common.backend.msgs.Datapoints;
import com.eucalyptus.cloudwatch.common.backend.msgs.DeleteAlarmsResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.DeleteAlarmsType;
import com.eucalyptus.cloudwatch.common.backend.msgs.DescribeAlarmHistoryResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.DescribeAlarmHistoryType;
import com.eucalyptus.cloudwatch.common.backend.msgs.DescribeAlarmsForMetricResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.DescribeAlarmsForMetricType;
import com.eucalyptus.cloudwatch.common.backend.msgs.DescribeAlarmsResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.DescribeAlarmsType;
import com.eucalyptus.cloudwatch.common.backend.msgs.Dimension;
import com.eucalyptus.cloudwatch.common.backend.msgs.DimensionFilter;
import com.eucalyptus.cloudwatch.common.backend.msgs.DimensionFilters;
import com.eucalyptus.cloudwatch.common.backend.msgs.Dimensions;
import com.eucalyptus.cloudwatch.common.backend.msgs.DisableAlarmActionsResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.DisableAlarmActionsType;
import com.eucalyptus.cloudwatch.common.backend.msgs.EnableAlarmActionsResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.EnableAlarmActionsType;
import com.eucalyptus.cloudwatch.common.backend.msgs.GetMetricStatisticsResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.GetMetricStatisticsType;
import com.eucalyptus.cloudwatch.common.backend.msgs.ListMetricsResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.ListMetricsResult;
import com.eucalyptus.cloudwatch.common.backend.msgs.ListMetricsType;
import com.eucalyptus.cloudwatch.common.backend.msgs.Metric;
import com.eucalyptus.cloudwatch.common.backend.msgs.MetricAlarm;
import com.eucalyptus.cloudwatch.common.backend.msgs.MetricAlarms;
import com.eucalyptus.cloudwatch.common.backend.msgs.MetricData;
import com.eucalyptus.cloudwatch.common.backend.msgs.MetricDatum;
import com.eucalyptus.cloudwatch.common.backend.msgs.Metrics;
import com.eucalyptus.cloudwatch.common.backend.msgs.PutMetricAlarmResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.PutMetricAlarmType;
import com.eucalyptus.cloudwatch.common.backend.msgs.PutMetricDataResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.PutMetricDataType;
import com.eucalyptus.cloudwatch.common.backend.msgs.ResourceList;
import com.eucalyptus.cloudwatch.common.backend.msgs.SetAlarmStateResponseType;
import com.eucalyptus.cloudwatch.common.backend.msgs.SetAlarmStateType;
import com.eucalyptus.cloudwatch.common.backend.msgs.StatisticSet;
import com.eucalyptus.cloudwatch.common.backend.msgs.Statistics;
import com.eucalyptus.cloudwatch.domain.DBCleanupService;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmEntity;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmEntity.ComparisonOperator;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmEntity.StateValue;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmEntity.Statistic;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmHistory;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmHistory.HistoryItemType;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmManager.ActionManager;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmManager;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmStateEvaluationDispatcher;
import com.eucalyptus.cloudwatch.domain.listmetrics.ListMetric;
import com.eucalyptus.cloudwatch.domain.listmetrics.ListMetricManager;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricDataQueue;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricManager;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricStatistics;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricUtils;
import com.eucalyptus.component.Faults;
import com.eucalyptus.configurable.ConfigurableClass;
import com.eucalyptus.configurable.ConfigurableField;
import com.eucalyptus.context.Context;
import com.eucalyptus.context.Contexts;
import com.eucalyptus.util.EucalyptusCloudException;
import com.eucalyptus.util.Exceptions;
import com.eucalyptus.auth.principal.OwnerFullName;
import com.eucalyptus.util.RestrictedTypes;
import com.google.common.base.Predicates;
import com.google.common.collect.Collections2;
import com.google.common.collect.Lists;

@ConfigurableClass( root = "cloudwatch", description = "Parameters controlling cloud watch and reporting")
public class CloudWatchBackendService {

  @ConfigurableField(initial = "false", description = "Set this to true to stop cloud watch alarm evaluation and new alarm/metric data entry")
  public static volatile Boolean DISABLE_CLOUDWATCH_SERVICE = false;

  static {
    // TODO: make this configurable
    ExecutorService fixedThreadPool = Executors.newFixedThreadPool(5);
    ScheduledExecutorService alarmWorkerService = Executors
        .newSingleThreadScheduledExecutor();
    alarmWorkerService.scheduleAtFixedRate(new AlarmStateEvaluationDispatcher(
        fixedThreadPool), 0, 1, TimeUnit.MINUTES);
    ScheduledExecutorService dbCleanupService = Executors
        .newSingleThreadScheduledExecutor();
    dbCleanupService.scheduleAtFixedRate(new DBCleanupService(), 1, 24,
        TimeUnit.HOURS);
  }

  private static final Logger LOG = Logger.getLogger(CloudWatchBackendService.class);

  private static final String SystemMetricPrefix = "AWS/";

  public PutMetricAlarmResponseType putMetricAlarm(PutMetricAlarmType request)
      throws CloudWatchException {
    PutMetricAlarmResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();

    try {
      // IAM Action Check
      checkActionPermission(PolicySpec.CLOUDWATCH_PUTMETRICALARM, ctx);
      if (DISABLE_CLOUDWATCH_SERVICE) {
        faultDisableCloudWatchServiceIfNecessary();
        throw new ServiceDisabledException("Service Disabled");
      }
      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String accountId = ownerFullName.getAccountNumber();
      final Boolean actionsEnabled = validateActionsEnabled(request.getActionsEnabled(), true);
      final Map<String, String> dimensionMap = TransformationFunctions.DimensionsToMap.INSTANCE
          .apply(validateDimensions(request.getDimensions()));
      final Collection<String> alarmActions = validateActions(
          request.getAlarmActions(), dimensionMap, "AlarmActions");
      final String alarmDescription = validateAlarmDescription(
          request.getAlarmDescription());
      final String alarmName = validateAlarmName(request.getAlarmName(), true);
      final ComparisonOperator comparisonOperator = validateComparisonOperator(
          request.getComparisonOperator(), true);
      Integer evaluationPeriods = validateEvaluationPeriods(
          request.getEvaluationPeriods(), true);
      final Integer period = validatePeriod(request.getPeriod(), true);
      validatePeriodAndEvaluationPeriodsNotAcrossDays(period, evaluationPeriods);
      final Collection<String> insufficientDataActions = validateActions(
          request.getInsufficientDataActions(), dimensionMap,
          "InsufficientDataActions");
      final String metricName = validateMetricName(request.getMetricName(),
          true);
      final String namespace = validateNamespace(request.getNamespace(), true);
      final Collection<String> okActions = validateActions(
          request.getOkActions(), dimensionMap, "OKActions");
      final Statistic statistic = validateStatistic(request.getStatistic(),
          true);
      final Double threshold = validateThreshold(request.getThreshold(), true);
      final Units unit = validateUnits(request.getUnit(), true);
      if (AlarmManager.countMetricAlarms(accountId) >= 5000) {
        throw new LimitExceededException("The maximum limit of 5000 alarms would be exceeded.");
      }
      AlarmManager.putMetricAlarm(accountId, actionsEnabled, alarmActions,
          alarmDescription, alarmName, comparisonOperator, dimensionMap,
          evaluationPeriods, insufficientDataActions, metricName,
          getMetricTypeFromNamespace(namespace), namespace, okActions, period,
          statistic, threshold, unit);
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public PutMetricDataResponseType putMetricData(PutMetricDataType request)
      throws CloudWatchException {
    PutMetricDataResponseType reply = request.getReply();
    long before = System.currentTimeMillis();
    final Context ctx = Contexts.lookup();

    try {
      // IAM Action Check
      checkActionPermission(PolicySpec.CLOUDWATCH_PUTMETRICDATA, ctx);
      if (DISABLE_CLOUDWATCH_SERVICE) {
        faultDisableCloudWatchServiceIfNecessary();
        throw new ServiceDisabledException("Service Disabled");
      }
      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final List<MetricDatum> metricData = validateMetricData(request.getMetricData());
      final String namespace = validateNamespace(request.getNamespace(), true);
      final Boolean privileged = Contexts.lookup().isPrivileged();
      LOG.trace("Namespace=" + namespace);
      LOG.trace("metricData="+metricData);
      MetricType metricType = getMetricTypeFromNamespace(namespace);
      if (metricType == MetricType.System && !privileged) {
        throw new InvalidParameterValueException("The value AWS/ for parameter Namespace is invalid.");
      }
      MetricDataQueue.getInstance().insertMetricData(ownerFullName.getAccountNumber(), namespace, metricData, metricType);
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public ListMetricsResponseType listMetrics(ListMetricsType request)
      throws CloudWatchException {
    ListMetricsResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();

    try {
      // IAM Action Check
      checkActionPermission(PolicySpec.CLOUDWATCH_LISTMETRICS, ctx);

      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String namespace = validateNamespace(request.getNamespace(), false);
      final String metricName = validateMetricName(request.getMetricName(),
          false);
      final Map<String, String> dimensionMap = TransformationFunctions.DimensionFiltersToMap.INSTANCE
          .apply(validateDimensionFilters(request.getDimensions()));

      // take all stats updated after two weeks ago
      final Date after = new Date(System.currentTimeMillis() - 2 * 7 * 24 * 60
          * 60 * 1000L);
      final Date before = null; // no bound on time before stats are updated
      // (though maybe 'now')
      final Integer maxRecords = 500; // per the API docs
      final String nextToken = request.getNextToken();
      final List<ListMetric> results = ListMetricManager.listMetrics(
          ownerFullName.getAccountNumber(), metricName, namespace,
          dimensionMap, after, before, maxRecords, nextToken);

      final Metrics metrics = new Metrics();
      metrics.setMember(Lists.newArrayList(Collections2
          .<ListMetric, Metric> transform(results,
              TransformationFunctions.ListMetricToMetric.INSTANCE)));
      final ListMetricsResult listMetricsResult = new ListMetricsResult();
      listMetricsResult.setMetrics(metrics);
      if (maxRecords != null && results.size() == maxRecords) {
        listMetricsResult.setNextToken(results.get(results.size() - 1)
            .getNaturalId());
      }
      reply.setListMetricsResult(listMetricsResult);
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }
  public GetMetricStatisticsResponseType getMetricStatistics(
      GetMetricStatisticsType request) throws CloudWatchException {
    GetMetricStatisticsResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();
    try {
      // IAM Action Check
      checkActionPermission(PolicySpec.CLOUDWATCH_GETMETRICSTATISTICS, ctx);

      // TODO: parse statistics separately()?
      final OwnerFullName ownerFullName = ctx.getUserFullName();
      Statistics statistics = validateStatistics(request.getStatistics());
      final String namespace = validateNamespace(request.getNamespace(), true);
      final String metricName = validateMetricName(request.getMetricName(),
          true);
      final Date startTime = MetricManager.stripSeconds(validateStartTime(request.getStartTime(), true));
      final Date endTime = MetricManager.stripSeconds(validateEndTime(request.getEndTime(), true));
      final Integer period = validatePeriod(request.getPeriod(), true);
      validateDateOrder(startTime, endTime, "StartTime", "EndTime", true,
          true);
      validateNotTooManyDataPoints(startTime, endTime, period, 1440L);
      
      // TODO: null units here does not mean Units.NONE but basically a
      // wildcard.
      // Consider this case.
      final Units units = validateUnits(request.getUnit(), false);
      final Map<String, String> dimensionMap = TransformationFunctions.DimensionsToMap.INSTANCE
          .apply(validateDimensions(request.getDimensions()));
      Collection<MetricStatistics> metrics;
      metrics = MetricManager.getMetricStatistics(
          ownerFullName.getAccountNumber(), metricName, namespace,
          dimensionMap, getMetricTypeFromNamespace(namespace), units,
          startTime, endTime, period);
      reply.getGetMetricStatisticsResult().setLabel(metricName);
      ArrayList<Datapoint> datapoints = convertMetricStatisticsToDataoints(
          statistics, metrics);
      if (datapoints.size() > 0) {
        Datapoints datapointsReply = new Datapoints();
        datapointsReply.setMember(datapoints);
        reply.getGetMetricStatisticsResult().setDatapoints(datapointsReply);
      }
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public DisableAlarmActionsResponseType disableAlarmActions(
      final DisableAlarmActionsType request
  ) throws EucalyptusCloudException {
    final DisableAlarmActionsResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();

    try {
      if (DISABLE_CLOUDWATCH_SERVICE) {
        faultDisableCloudWatchServiceIfNecessary();
        throw new ServiceDisabledException("Service Disabled");
      }
      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String accountId = ownerFullName.getAccountNumber();
      final Collection<String> alarmNames =
          validateAlarmNames( request.getAlarmNames(), true );
      if ( !AlarmManager.disableAlarmActions(
          accountId,
          alarmNames,
          RestrictedTypes.<CloudWatchMetadata.AlarmMetadata>filterPrivileged( ) ) ) {
        throw new EucalyptusCloudException("User does not have permission");
      }
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public DescribeAlarmsResponseType describeAlarms(
      final DescribeAlarmsType request
  ) throws CloudWatchException {
    final DescribeAlarmsResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();

    try {
      final boolean showAll = request.getAlarms().remove( "verbose" );
      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String accountId = ctx.isAdministrator() && showAll ? null : ownerFullName.getAccountNumber();
      final String actionPrefix = validateActionPrefix(
          request.getActionPrefix(), false);
      final String alarmNamePrefix = validateAlarmNamePrefix(
          request.getAlarmNamePrefix(), false);
      final Collection<String> alarmNames = validateAlarmNames(
          request.getAlarmNames(), false);
      validateNotBothAlarmNamesAndAlarmNamePrefix(alarmNames, alarmNamePrefix);
      final Integer maxRecords = validateMaxRecords(request.getMaxRecords());
      final String nextToken = request.getNextToken();
      final StateValue stateValue = validateStateValue(request.getStateValue(),
          false);
      final List<AlarmEntity> results = AlarmManager.describeAlarms(accountId,
          actionPrefix, alarmNamePrefix, alarmNames, maxRecords, stateValue,
          nextToken, RestrictedTypes.filteringFor( CloudWatchMetadata.AlarmMetadata.class ).byPrivileges( ).buildPredicate( ) );
      if (maxRecords != null && results.size() == maxRecords) {
        reply.getDescribeAlarmsResult().setNextToken(
            results.get(results.size() - 1).getNaturalId());
      }
      final MetricAlarms metricAlarms = new MetricAlarms();
      metricAlarms.setMember(Lists.newArrayList(Collections2
          .<AlarmEntity, MetricAlarm> transform(results,
              TransformationFunctions.AlarmEntityToMetricAlarm.INSTANCE)));
      reply.getDescribeAlarmsResult().setMetricAlarms(metricAlarms);
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public DescribeAlarmsForMetricResponseType describeAlarmsForMetric(
    final DescribeAlarmsForMetricType request
  ) throws CloudWatchException {
    final DescribeAlarmsForMetricResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();

    try {
      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String accountId = ownerFullName.getAccountNumber();
      final Map<String, String> dimensionMap = TransformationFunctions.DimensionsToMap.INSTANCE
          .apply(validateDimensions(request.getDimensions()));
      final String metricName = validateMetricName(request.getMetricName(),
          true);
      final String namespace = validateNamespace(request.getNamespace(), true);
      final Integer period = validatePeriod(request.getPeriod(), false);
      final Statistic statistic = validateStatistic(request.getStatistic(),
          false);
      final Units unit = validateUnits(request.getUnit(), true);
      final Collection<AlarmEntity> results = AlarmManager.describeAlarmsForMetric(
          accountId, dimensionMap, metricName, namespace, period, statistic,
          unit, RestrictedTypes.filteringFor( CloudWatchMetadata.AlarmMetadata.class ).byPrivileges( ).buildPredicate( ) );
      final MetricAlarms metricAlarms = new MetricAlarms();
      metricAlarms.setMember(Lists.newArrayList(Collections2
          .<AlarmEntity, MetricAlarm> transform(results,
              TransformationFunctions.AlarmEntityToMetricAlarm.INSTANCE)));
      reply.getDescribeAlarmsForMetricResult().setMetricAlarms(metricAlarms);
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public DescribeAlarmHistoryResponseType describeAlarmHistory(
      final DescribeAlarmHistoryType request
  ) throws CloudWatchException {
    final DescribeAlarmHistoryResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();

    try {
      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String accountId = ownerFullName.getAccountNumber();
      final String alarmName = validateAlarmName(request.getAlarmName(), false);
      final Date endDate = validateEndDate(request.getEndDate(), false);
      final Date startDate = validateStartDate(request.getStartDate(), false);
      validateDateOrder(startDate, endDate, "StartDate", "EndDate", false,
          false);
      final HistoryItemType historyItemType = validateHistoryItemType(
          request.getHistoryItemType(), false);
      final Integer maxRecords = validateMaxRecords(request.getMaxRecords());
      final String nextToken = request.getNextToken();
      final List<AlarmHistory> results = AlarmManager.describeAlarmHistory(
          accountId, alarmName, endDate, historyItemType,
          maxRecords, startDate, nextToken, Predicates.compose(
            RestrictedTypes.filteringFor( CloudWatchMetadata.AlarmMetadata.class ).byPrivileges( ).buildPredicate( ),
            TransformationFunctions.AlarmHistoryToAlarmMetadata.INSTANCE ) );
      if (maxRecords != null && results.size() == maxRecords) {
        reply.getDescribeAlarmHistoryResult().setNextToken(
            results.get(results.size() - 1).getNaturalId());
      }
      final AlarmHistoryItems alarmHistoryItems = new AlarmHistoryItems();
      alarmHistoryItems
          .setMember(Lists.newArrayList(Collections2
              .<AlarmHistory, AlarmHistoryItem> transform(
                  results,
                  TransformationFunctions.AlarmHistoryToAlarmHistoryItem.INSTANCE)));
      reply.getDescribeAlarmHistoryResult().setAlarmHistoryItems(
          alarmHistoryItems);
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public EnableAlarmActionsResponseType enableAlarmActions(
      EnableAlarmActionsType request) throws CloudWatchException {
    final EnableAlarmActionsResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();

    try {
      if (DISABLE_CLOUDWATCH_SERVICE) {
        faultDisableCloudWatchServiceIfNecessary();
        throw new ServiceDisabledException("Service Disabled");
      }

      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String accountId = ownerFullName.getAccountNumber();
      final Collection<String> alarmNames =
          validateAlarmNames( request.getAlarmNames(), true );
      if ( !AlarmManager.enableAlarmActions(
          accountId,
          alarmNames,
          RestrictedTypes.<CloudWatchMetadata.AlarmMetadata>filterPrivileged( )) ) {
        throw new EucalyptusCloudException("User does not have permission");
      }
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public DeleteAlarmsResponseType deleteAlarms(DeleteAlarmsType request)
      throws CloudWatchException {
    DeleteAlarmsResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();
    try {
      if (DISABLE_CLOUDWATCH_SERVICE) {
        faultDisableCloudWatchServiceIfNecessary();
        throw new ServiceDisabledException("Service Disabled");
      }

      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String accountId = ownerFullName.getAccountNumber();
      final Collection<String> alarmNames =
          validateAlarmNames( request.getAlarmNames(), true );
      if ( !AlarmManager.deleteAlarms(
          accountId,
          alarmNames,
          RestrictedTypes.<CloudWatchMetadata.AlarmMetadata>filterPrivileged( ) ) ) {
        throw new EucalyptusCloudException("User does not have permission");
      }
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }

  public SetAlarmStateResponseType setAlarmState(SetAlarmStateType request)
      throws CloudWatchException {
    final SetAlarmStateResponseType reply = request.getReply();
    final Context ctx = Contexts.lookup();
    try {
      if (DISABLE_CLOUDWATCH_SERVICE) {
        faultDisableCloudWatchServiceIfNecessary();
        throw new ServiceDisabledException("Service Disabled");
      }
      final OwnerFullName ownerFullName = ctx.getUserFullName();
      final String accountId = ownerFullName.getAccountNumber();
      final String alarmName = validateAlarmName(request.getAlarmName(), true);
      final String stateReason = validateStateReason(request.getStateReason(), true);
      final String stateReasonData = validateStateReasonData(request.getStateReasonData(), false);
      final StateValue stateValue = validateStateValue(request.getStateValue(), true);
      AlarmManager.setAlarmState(
          accountId, alarmName, stateReason, stateReasonData, stateValue,
          RestrictedTypes.<CloudWatchMetadata.AlarmMetadata>filterPrivileged( ) );
    } catch (Exception ex) {
      handleException(ex);
    }
    return reply;
  }
  private static final int DISABLED_SERVICE_FAULT_ID = 1500;
  private boolean alreadyFaulted = false;
  private void faultDisableCloudWatchServiceIfNecessary() {
    // TODO Auto-generated method stub
    if (!alreadyFaulted) {
      Faults.forComponent(CloudWatchBackend.class).havingId(DISABLED_SERVICE_FAULT_ID).withVar("component", "cloudwatch").log();
      alreadyFaulted = true;
    }
    
  }

  private void validatePeriodAndEvaluationPeriodsNotAcrossDays(Integer period,
      Integer evaluationPeriods) throws CloudWatchException{
    if (period * evaluationPeriods > 86400) {
      throw new InvalidParameterCombinationException("Metrics cannot be checked across more than a day (EvaluationPeriods * Period must be <= 86400).");
    }
  }


  private void validateNotTooManyDataPoints(Date startTime, Date endTime,
      Integer period, long maxDataPoints) throws CloudWatchException {
    NumberFormat nf = NumberFormat.getInstance();
    long possibleRequestedDataPoints = (endTime.getTime() - startTime.getTime()) / (1000L * period);
    if (possibleRequestedDataPoints > maxDataPoints) {
      throw new InvalidParameterCombinationException("You have requested up to " + nf.format(possibleRequestedDataPoints)+ " datapoints, which exceeds the limit of " + nf.format(maxDataPoints) + ". You may reduce the datapoints requested by increasing Period, or decreasing the time range.");
    }
  }

  private List<MetricDatum> validateMetricData(MetricData metricData) throws CloudWatchException {
    List<MetricDatum> metricDataCollection = null;
    if (metricData != null) {
      metricDataCollection = metricData.getMember();
      ;
    }
    if (metricDataCollection == null) {
      throw new MissingParameterException(
         "The parameter MetricData is required.");
   }
    if (metricDataCollection.size() < 1) {
      throw new MissingParameterException(
          "The parameter MetricData is required.");
    }
    if (metricDataCollection.size() > 20) {
      throw new InvalidParameterValueException(
          "The collection MetricData must not have a size greater than 20.");
    }
    int ctr = 1;
    for (MetricDatum metricDatum : metricDataCollection) {
      validateMetricDatum(metricDatum, "MetricData.member." + ctr);
      ctr++;
    }
    return metricDataCollection;
  }

  private Date validateStartDate(Date startDate, boolean required)
      throws CloudWatchException {
    return validateTimestamp(startDate, "StartDate", required);
  }

  private Date validateEndDate(Date endDate, boolean required)
      throws CloudWatchException {
    return validateTimestamp(endDate, "EndDate", required);
  }

  private Date validateStartTime(Date startTime, boolean required)
      throws CloudWatchException {
    return validateTimestamp(startTime, "StartTime", required);
  }

  private Date validateEndTime(Date endTime, boolean required)
      throws CloudWatchException {
    return validateTimestamp(endTime, "EndTime", required);
  }

  private MetricDatum validateMetricDatum(MetricDatum metricDatum, String name) throws CloudWatchException {
    if (metricDatum == null) {
      throw new MissingParameterException("The parameter " + name + " is required.");
    }
    validateDimensions(metricDatum.getDimensions(), name + ".Dimensions");
    validateMetricName(metricDatum.getMetricName(), name + ".MetricName",
        true);
    validateWithinTwoWeeks(metricDatum.getTimestamp(), name + "Timestamp");
    validateUnits(metricDatum.getUnit(), name + ".Unit", true);
    validateValueAndStatisticSet(metricDatum.getValue(), name + ".Value",
          metricDatum.getStatisticValues(), name + ".StatisticValues");
    return metricDatum;
  }


  private void validateWithinTwoWeeks(Date timestamp, String name) throws CloudWatchException {
    if (timestamp == null) return;
    Date now = new Date();
    Date twoWeeksAgo = new Date(now.getTime() - 2 * 7 * 24 * 3600 * 1000L);
    long BUFFER = 2 * 3600 * 1000L; // two hours
    if (timestamp.getTime() > now.getTime() + BUFFER || timestamp.getTime() < twoWeeksAgo.getTime() - BUFFER) {
      throw new InvalidParameterValueException("The parameter " + name + ".Timestamp must specify a time within the past two weeks.");
    }
  }

  private void validateValueAndStatisticSet(Double value, String valueName, StatisticSet statisticValues, String statisticValuesName) throws CloudWatchException {
    if (value == null && statisticSetHasNoFields(statisticValues)) {
      throw new MissingParameterException("At least one of the parameters " + valueName + " or "
          + statisticValuesName + " must be specified.");
    }
    if (value != null && !statisticSetHasNoFields(statisticValues)) {
      throw new InvalidParameterCombinationException("The parameters " + valueName + " and "
          + statisticValuesName + " are mutually exclusive and you have specified both.");
    }
    if (value != null) return; // value is set
    validateAllStatisticSetFields(statisticValues, statisticValuesName);
    if (statisticValues.getMaximum() < statisticValues.getMinimum()) {
      throw new MissingParameterException("The parameter " + statisticValuesName+ ".Maximum must be greater than " + statisticValuesName + ".Minimum.");
      
    }
    if (statisticValues.getSampleCount() < 0) {
      throw new MissingParameterException("The parameter " + statisticValuesName+ ".SampleCount must be greater than 0.");
    }
    if (statisticValues.getSampleCount() == 0.0) {
      throw new MissingParameterException("The parameter " + statisticValuesName+ ".SampleCount must not equal 0.");
    }
  }

  private void validateAllStatisticSetFields(StatisticSet statisticValues, String statisticValuesName) throws CloudWatchException {
    StringBuilder errors = new StringBuilder();
    boolean haveErrors = false;
    if (statisticValues == null || statisticValues.getMaximum() == null) {
      if (haveErrors) {
        errors.append("\n");
      }
      errors.append("The parameter " + statisticValuesName + ".Maximum is required.");
      haveErrors = true;
    }
    if (statisticValues == null || statisticValues.getMinimum() == null) {
      if (haveErrors) {
        errors.append("\n");
      }
      errors.append("The parameter " + statisticValuesName + ".Minimum is required.");
      haveErrors = true;
    }
    if (statisticValues == null || statisticValues.getSampleCount() == null) {
      if (haveErrors) {
        errors.append("\n");
      }
      errors.append("The parameter " + statisticValuesName + ".SampleCount is required.");
      haveErrors = true;
    }
    if (statisticValues == null || statisticValues.getSum() == null) {
      if (haveErrors) {
        errors.append("\n");
      }
      errors.append("The parameter " + statisticValuesName + ".Sum is required.");
      haveErrors = true;
    }
    if (haveErrors) {
      throw new MissingParameterException(errors.toString());
    }
  }

  private boolean statisticSetHasNoFields(StatisticSet statisticValues) {
    return (statisticValues == null) || (
        (statisticValues.getMaximum()) == null && (statisticValues.getMinimum() == null) &&
        (statisticValues.getSampleCount()) == null && (statisticValues.getSum() == null));
  }

  private Units validateUnits(String unit, boolean useNoneIfNull) throws CloudWatchException {
    return validateUnits(unit, "Unit", useNoneIfNull);

  }

  private Date validateTimestamp(Date timestamp, String name, boolean required)
      throws CloudWatchException {
    if (timestamp == null) {
      if (required) {
        throw new MissingParameterException("The parameter " + name + " is required.");
      }
    }
    return timestamp;
  }

  private Integer validateEvaluationPeriods(Integer evaluationPeriods,
      boolean required) throws CloudWatchException {
    if (evaluationPeriods == null) {
      if (required) {
        throw new MissingParameterException(
            "The parameter EvaluationPeriods is required.");
      }
    }
    if (evaluationPeriods < 1) {
      throw new InvalidParameterValueException(
          "The parameter EvaluationPeriods must be greater than or equal to 1.");
    }
    return evaluationPeriods;
  }

  private String validateMetricName(String metricName, boolean required)
      throws CloudWatchException {
    return validateMetricName(metricName, "MetricName", required);
  }

  private Dimensions validateDimensions(Dimensions dimensions)
      throws CloudWatchException {
    return validateDimensions(dimensions, "Dimensions");
  }

  private DimensionFilters validateDimensionFilters(
      DimensionFilters dimensionFilters)
      throws CloudWatchException {
    return validateDimensionFilters(dimensionFilters, "Dimensions");
  }

  private Double validateDouble(Double value, String name, boolean required)
      throws CloudWatchException {
    if (value == null) {
      if (required) {
        throw new MissingParameterException("The parameter " + name + " is required.");
      }
    }
    return value;
  }

  private Double validateThreshold(Double threshold, boolean required)
      throws CloudWatchException {
    return validateDouble(threshold, "Threshold", required);
  }

  private ComparisonOperator validateComparisonOperator(
      String comparisonOperator, boolean required) throws CloudWatchException {
    return validateEnum(comparisonOperator, "ComparisonOperator",
        ComparisonOperator.class, required);
  }

  private String validateAlarmDescription(String alarmDescription) throws CloudWatchException {
    return validateStringLength(alarmDescription, "AlarmDescription", 0, 255, false);
  }

  private Boolean validateActionsEnabled(Boolean actionsEnabled, boolean useTrueIfNull) throws CloudWatchException {
    if (actionsEnabled == null) {
      if (useTrueIfNull) {
        return Boolean.TRUE;
      }
    }
    return actionsEnabled;
  }

  private Collection<String> validateActions(ResourceList actions,
      Map<String, String> dimensionMap, String name)
      throws CloudWatchException {
    Collection<String> actionsCollection = null;
    if (actions != null) {
      actionsCollection = actions.getMember();
      ;
    }
    if (actionsCollection == null) {
      return actionsCollection;
    }
    if (actionsCollection.size() > 5) {
      throw new InvalidParameterValueException("The collection " + name
          + " must not have a size greater than 5.");
    }
    int ctr = 1;
    for (String action : actionsCollection) {
      validateAction(action, dimensionMap, name + ".member." + ctr);
      ctr++;
    }
    return actionsCollection;
  }

  private void validateAction(String action, Map<String, String> dimensionMap,
      String name) throws CloudWatchException {
    if (ActionManager.getAction(action, dimensionMap) == null) {
      throw new InvalidParameterValueException("The parameter " + name + "'" + action
          + "' is an unsupported action for this metric and dimension list.");
    }
  }

  private void validateNotBothAlarmNamesAndAlarmNamePrefix(
      Collection<String> alarmNames, String alarmNamePrefix)
      throws CloudWatchException {
    if (alarmNames != null && alarmNamePrefix != null) {
      throw new InvalidParameterCombinationException(
          "AlarmNamePrefix and AlarmNames.member are mutually exclusive");
    }
  }

  private String validateAlarmNamePrefix(String alarmNamePrefix,
      boolean required) throws CloudWatchException {
    return validateStringLength(alarmNamePrefix, "AlarmNamePrefix", 1, 255,
        required);
  }

  private String validateActionPrefix(String actionPrefix, boolean required)
      throws CloudWatchException {
    return validateStringLength(actionPrefix, "ActionPrefix", 1, 1024, required);
  }

  private Statistics validateStatistics(Statistics statistics)
      throws CloudWatchException {
    Collection<String> statisticCollection = null;
    if (statistics != null) {
      statisticCollection = statistics.getMember();
    }
    if (statisticCollection == null) {
      throw new MissingParameterException("The parameter Statistics is required.");
    }
    if (statisticCollection.size() < 1) {
      throw new MissingParameterException("The parameter Statistics is required.");
    }
      
    if (statisticCollection.size() > 5) {
      throw new InvalidParameterValueException(
          "The collection MetricData must not have a size greater than 5.");
    }
    int ctr = 1;
    String[] statisticValues = new String[] { "Average", "Sum", "SampleCount",
        "Maximum", "Minimum" };
    for (String statistic : statisticCollection) {
      if (statistic == null) {
        throw new InvalidParameterValueException("The parameter Statistics.member." + ctr
            + " is required.");
      }
      if (!Arrays.asList(statisticValues).contains(statistic)) {
        throw new InvalidParameterValueException("The parameter Statistics.member." + ctr
            + " must be a value in the set " + Arrays.asList(statisticValues) + ".");
      }
      ctr++;
    }
    return statistics;
  }

  private DimensionFilters validateDimensionFilters(
      DimensionFilters dimensionFilters, String name)
      throws CloudWatchException {
    Collection<DimensionFilter> dimensionFiltersCollection = null;
    if (dimensionFilters != null) {
      dimensionFiltersCollection = dimensionFilters.getMember();
    }
    if (dimensionFiltersCollection == null) {
      return dimensionFilters;
    }
    if (dimensionFiltersCollection.size() > 10) {
      throw new InvalidParameterValueException("The collection " + name
          + " must not have a size greater than 10.");
    }
    int ctr = 1;
    for (DimensionFilter dimensionFilter : dimensionFiltersCollection) {
      validateStringLength(dimensionFilter.getName(), name + ".member." + (ctr)
          + ".Name", 1, 255, true);
      validateStringLength(dimensionFilter.getValue(), name + ".member."
          + (ctr) + ".Value", 1, 255, true);
      ctr++;
    }
    return dimensionFilters;
  }

  private Dimensions validateDimensions(Dimensions dimensions, String name) throws CloudWatchException {
    Collection<Dimension> dimensionsCollection = null;
    if (dimensions != null) {
      dimensionsCollection = dimensions.getMember();
    }
    if (dimensions == null) {
      return dimensions;
    }
    if (dimensionsCollection.size() > 10) {
      throw new InvalidParameterValueException("The collection " + name
          + " must not have a size greater than 10.");
    }
    int ctr = 1;
    for (Dimension dimension : dimensionsCollection) {
      validateStringLength(dimension.getName(), name + ".member." + (ctr)
          + ".Name", 1, 255, true);
      validateStringLength(dimension.getValue(), name + ".member." + (ctr)
          + ".Value", 1, 255, true);
      ctr++;
    }
    return dimensions;
  }

  private Units validateUnits(String unit, String name, boolean useNoneIfNull) throws CloudWatchException {
    if (unit == null) {
      if (useNoneIfNull) {
        return Units.None;
      } else {
        return null;
      }
    }
    try {
      return Units.fromValue(unit);
    } catch (IllegalArgumentException ex) {
      throw new InvalidParameterValueException("The parameter " + name + " must be a value in the set "
          + Arrays.asList(Units.values()) +".");
    }
  }

  private Statistic validateStatistic(String statistic, boolean required)
      throws CloudWatchException {
    return validateEnum(statistic, "Statistic", Statistic.class, required);
  }

  private Integer validatePeriod(Integer period, boolean required)
      throws CloudWatchException {
    if (period == null) {
      if (required) {
        throw new MissingParameterException("The parameter Period is required.");
      } else {
        return period;
      }
    }
    if (period < 0) {
      throw new InvalidParameterValueException("The parameter Period must be greater than 0.");
    }
    if (period == 0) {
      throw new InvalidParameterValueException("The parameter Period must not equal 0.");
    }
    if (period % 60 != 0) {
      throw new InvalidParameterValueException(
          "The parameter Period must be a multiple of 60.");
    }
    return period;
  }

  private String validateNamespace(String namespace, boolean required)
      throws CloudWatchException {
    namespace = validateStringLength(namespace, "Namespace", 1, 255, required);
    return namespace;
  }

  private String validateMetricName(String metricName, String name,
      boolean required) throws CloudWatchException {
    return validateStringLength(metricName, name, 1, 255, required);
  }

  private Integer validateMaxRecords(Integer maxRecords)
      throws CloudWatchException {
    if (maxRecords == null) {
      return 50; // this is from experimentation
    }
    if (maxRecords < 1) {
      throw new InvalidParameterValueException("The parameter MaxRecords must be greater than or equal to 1.");
    }
    if (maxRecords > 100) {
      throw new InvalidParameterValueException("The parameter MaxRecords must be less than or equal to 100.");
    }
    return maxRecords;
  }

  private void validateDateOrder(Date startDate, Date endDate,
      String startDateName, String endDateName, boolean startDateRequired,
      boolean endDateRequired) throws CloudWatchException {
    if (startDate != null && endDate != null) {
      if (startDate.after(endDate)) {
        throw new InvalidParameterValueException("The parameter " + endDateName 
            + " must be greater than " + startDateName + ".");
      }
      if (startDate.equals(endDate)) {
        throw new InvalidParameterValueException("The parameter " + startDateName 
            + " must not equal parameter " + endDateName + ".");
      }
    }
    if (startDate == null && startDateRequired) {
      throw new MissingParameterException("The parameter " + startDateName
          + " is required.");
    }
    if (endDate == null && endDateRequired) {
      throw new MissingParameterException("The parameter " + endDateName
          + " is required.");
    }
  }

  private HistoryItemType validateHistoryItemType(String historyItemType,
      boolean required) throws CloudWatchException {
    return validateEnum(historyItemType, "HistoryItemType",
        HistoryItemType.class, required);
  }

  private Collection<String> validateAlarmNames(AlarmNames alarmNames,
      boolean required) throws CloudWatchException {
    Collection<String> alarmNamesCollection = null;
    if (alarmNames != null) {
      alarmNamesCollection = alarmNames.getMember();
    }
    if (alarmNamesCollection == null) {
      if (required) {
        throw new MissingParameterException(
            "The parameter AlarmNames is required.");
      }
      return alarmNamesCollection;
    }
    if (alarmNamesCollection.size() < 1 && required) {
      throw new MissingParameterException(
          "The parameter AlarmNames is required.");
    }
        
    if (alarmNamesCollection.size() > 100) {
      throw new InvalidParameterValueException(
          "The collection AlarmNames must not have a size greater than 100.");
    }
    int ctr = 1;
    for (String alarmName : alarmNamesCollection) {
      validateAlarmName(alarmName, "AlarmName.member." + (ctr++), true);
    }
    return alarmNamesCollection;
  }

  private <T extends Enum<T>> T validateEnum(String value, String name,
      Class<T> enumType, boolean required) throws CloudWatchException {
    try {
      return Enum.valueOf(enumType, value);
    } catch (IllegalArgumentException ex) {
      throw new InvalidParameterValueException("The parameter " + name + " must be a value in the set "
          + Arrays.asList(enumType.getEnumConstants()) + ".");
    } catch (NullPointerException ex) {
      if (required) {
        throw new MissingParameterException("The parameter " + name + " is required.");
      }
      return null;
    }
  }

  private StateValue validateStateValue(String stateValue, boolean required)
      throws CloudWatchException {
    return validateEnum(stateValue, "StateValue", StateValue.class, required);
  }

  private String validateStateReasonData(String stateReasonData,
      boolean required) throws CloudWatchException {
    stateReasonData = validateStringLength(stateReasonData, "StateReasonData",
        0, 4000, required);
    stateReasonData = validateJSON(stateReasonData, "StateReasonData", required);
    return stateReasonData;
  }

  private String validateJSON(String value, String name, boolean required)
      throws CloudWatchException {
    if (value == null) {
      if (required) {
        throw new MissingParameterException("The parameter " + name + " is required.");
      } else {
        return value;
      }
    }
    try {
      JSONSerializer.toJSON(value);
    } catch (JSONException ex) {
      throw new InvalidFormatException(name
          + " was not syntactically valid JSON");
    }
    return value;
  }

  private String validateStringLength(String value, String name, int minLength,
      int maxLength, boolean required) throws CloudWatchException {
    if (value == null || value.isEmpty() ) {
      if (required) {
        throw new MissingParameterException("The parameter " + name + " is required.");
      } else {
        return value;
      }
    }
    if (value.length() < minLength) {
      throw new InvalidParameterValueException("The parameter " + name + " must be longer than " + (minLength - 1) + " character" + ((minLength == 2) ? "" : "s" ) + ".");
    }
    if (value.length() > maxLength) {
      throw new InvalidParameterValueException("The parameter " + name + " must be shorter than " + (maxLength + 1) + " character" + ((maxLength == 0) ? "" : "s" ) + ".");
    }
    return value;
  }

  private String validateAlarmName(String alarmName, boolean required)
      throws CloudWatchException {
    return validateAlarmName(alarmName, "AlarmName", required);
  }

  private String validateAlarmName(String alarmNameValue, String alarmNameKey,
      boolean required) throws CloudWatchException {
    return validateStringLength(alarmNameValue, alarmNameKey, 1, 255, required);
  }

  private String validateStateReason(String stateReason, boolean required)
      throws CloudWatchException {
    return validateStringLength(stateReason, "StateReason", 0, 1024, required);
  }

  private void checkActionPermission(final String actionType, final Context ctx)
      throws EucalyptusCloudException {
    if (!Permissions.isAuthorized(PolicySpec.VENDOR_CLOUDWATCH, actionType, "",
        ctx.getAccount(), actionType, ctx.getAuthContext())) {
      throw new EucalyptusCloudException("User does not have permission");
    }
  }

  private static void handleException(final Exception e)
      throws CloudWatchException {
    final CloudWatchException cause = Exceptions.findCause(e,
        CloudWatchException.class);
    if (cause != null) {
      throw cause;
    }

    final InternalFailureException exception = new InternalFailureException(
        String.valueOf(e.getMessage()));
    if (Contexts.lookup().hasAdministrativePrivileges()) {
      exception.initCause(e);
    }
    throw exception;
  }

  private MetricType getMetricTypeFromNamespace(String namespace) {
    return namespace.startsWith(SystemMetricPrefix) ? MetricType.System
        : MetricType.Custom;
  }

  private ArrayList<Datapoint> convertMetricStatisticsToDataoints(
      Statistics statistics, Collection<MetricStatistics> metrics) {
    ArrayList<Datapoint> datapoints = Lists.newArrayList();
    boolean wantsAverage = statistics.getMember().contains("Average");
    boolean wantsSum = statistics.getMember().contains("Sum");
    boolean wantsSampleCount = statistics.getMember().contains("SampleCount");
    boolean wantsMaximum = statistics.getMember().contains("Maximum");
    boolean wantsMinimum = statistics.getMember().contains("Minimum");
    for (MetricStatistics metricStatistics : metrics) {
      Datapoint datapoint = new Datapoint();
      datapoint.setTimestamp(metricStatistics.getTimestamp());
      datapoint.setUnit(metricStatistics.getUnits().toString());
      if (wantsSum) {
        datapoint.setSum(metricStatistics.getSampleSum());
      }
      if (wantsSampleCount) {
        datapoint.setSampleCount(metricStatistics.getSampleSize());
      }
      if (wantsMaximum) {
        datapoint.setMaximum(metricStatistics.getSampleMax());
      }
      if (wantsMinimum) {
        datapoint.setMinimum(metricStatistics.getSampleMin());
      }
      if (wantsAverage) {
        datapoint.setAverage(MetricUtils.average(
            metricStatistics.getSampleSum(), metricStatistics.getSampleSize()));
      }
      datapoints.add(datapoint);
    }
    return datapoints;
  }

}


File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/DBCleanupService.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain;

import java.util.Date;

import org.apache.log4j.Logger;

import com.eucalyptus.bootstrap.Bootstrap;
import com.eucalyptus.cloudwatch.common.CloudWatchBackend;
import com.eucalyptus.cloudwatch.domain.absolute.AbsoluteMetricHelper;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmManager;
import com.eucalyptus.cloudwatch.domain.listmetrics.ListMetricManager;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricManager;
import com.eucalyptus.component.Topology;

public class DBCleanupService implements Runnable {
  Logger LOG = Logger.getLogger(DBCleanupService.class);
  public DBCleanupService() {
  }

  @Override
  public void run() {
    LOG.info("Calling cloudwatch db cleanup service");
    if (!( Bootstrap.isFinished() &&
        Topology.isEnabled( CloudWatchBackend.class ) )) {
      LOG.info("Cloudwatch service is not ENABLED");
      return;
    }
    
    Date twoWeeksAgo = new Date(System.currentTimeMillis() - 2 * 7 * 24 * 60 * 60 * 1000L);
    try {
      MetricManager.deleteMetrics(twoWeeksAgo);
    } catch (Exception ex) {
      LOG.error(ex);
      LOG.error(ex, ex);
    }
    try {
      ListMetricManager.deleteMetrics(twoWeeksAgo);
    } catch (Exception ex) {
      LOG.error(ex);
      LOG.error(ex, ex);
    }
    try {
      AlarmManager.deleteAlarmHistory(twoWeeksAgo);
    } catch (Exception ex) {
      LOG.error(ex);
      LOG.error(ex, ex);
    }
    try {
      AbsoluteMetricHelper.deleteAbsoluteMetricHistory(twoWeeksAgo);
    } catch (Exception ex) {
      LOG.error(ex);
      LOG.error(ex, ex);
    }
    LOG.info("Done cleaning up cloudwatch db");
  }

}


File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/alarms/AlarmEntity.java
/*************************************************************************
 * Copyright 2009-2014 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 *
 * This file may incorporate work covered under the following copyright
 * and permission notice:
 *
 *   Copyright 2010-2014 Amazon.com, Inc. or its affiliates. All Rights
 *   Reserved.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License").
 *   You may not use this file except in compliance with the License.
 *   A copy of the License is located at
 *
 *   http://aws.amazon.com/apache2.0
 *
 *   or in the "license" file accompanying this file. This file is
 *   distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
 *   ANY KIND, either express or implied. See the License for the specific
 *   language governing permissions and limitations under the License.
 ************************************************************************/

package com.eucalyptus.cloudwatch.domain.alarms;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.Iterator;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.EnumType;
import javax.persistence.Enumerated;
import javax.persistence.Lob;
import javax.persistence.PersistenceContext;
import javax.persistence.Table;
import org.apache.log4j.Logger;
import org.hibernate.annotations.Cache;
import org.hibernate.annotations.CacheConcurrencyStrategy;
import org.hibernate.annotations.Type;
import com.eucalyptus.auth.principal.AccountFullName;
import com.eucalyptus.cloudwatch.common.CloudWatchMetadata;
import com.eucalyptus.cloudwatch.domain.AbstractPersistentWithDimensions;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;
import com.eucalyptus.auth.principal.OwnerFullName;

@Entity
@PersistenceContext(name="eucalyptus_cloudwatch")
@Table(name="alarms")
@Cache( usage = CacheConcurrencyStrategy.TRANSACTIONAL )
public class AlarmEntity extends AbstractPersistentWithDimensions implements CloudWatchMetadata.AlarmMetadata {

  private static final Logger LOG = Logger.getLogger(AlarmEntity.class);
  @Column(name = "account_id", nullable = false)
  private String accountId;

  @Column(name="actions_enabled", nullable = false)
  private Boolean actionsEnabled;

  @Column(name = "alarm_configuration_updated_timestamp", nullable = false)
  private Date alarmConfigurationUpdatedTimestamp;

  @Column(name="alarm_description")
  private String alarmDescription;

  public String getAccountId() {
    return accountId;
  }
  public void setAccountId(String accountId) {
    this.accountId = accountId;
  }
  public Boolean getActionsEnabled() {
    return actionsEnabled;
  }
  public void setActionsEnabled(Boolean actionsEnabled) {
    this.actionsEnabled = actionsEnabled;
  }
  public Date getAlarmConfigurationUpdatedTimestamp() {
    return alarmConfigurationUpdatedTimestamp;
  }
  public void setAlarmConfigurationUpdatedTimestamp(
      Date alarmConfigurationUpdatedTimestamp) {
    this.alarmConfigurationUpdatedTimestamp = alarmConfigurationUpdatedTimestamp;
  }
  public String getAlarmDescription() {
    return alarmDescription;
  }
  public void setAlarmDescription(String alarmDescription) {
    this.alarmDescription = alarmDescription;
  }
  public String getAlarmName() {
    return alarmName;
  }
  public void setAlarmName(String alarmName) {
    this.alarmName = alarmName;
  }
  public ComparisonOperator getComparisonOperator() {
    return comparisonOperator;
  }
  public void setComparisonOperator(ComparisonOperator comparisonOperator) {
    this.comparisonOperator = comparisonOperator;
  }
  public Integer getEvaluationPeriods() {
    return evaluationPeriods;
  }
  public void setEvaluationPeriods(Integer evaluationPeriods) {
    this.evaluationPeriods = evaluationPeriods;
  }
  public String getMetricName() {
    return metricName;
  }
  public void setMetricName(String metricName) {
    this.metricName = metricName;
  }
  public MetricType getMetricType() {
    return metricType;
  }
  public void setMetricType(MetricType metricType) {
    this.metricType = metricType;
  }
  public String getNamespace() {
    return namespace;
  }
  public void setNamespace(String namespace) {
    this.namespace = namespace;
  }
  public Integer getPeriod() {
    return period;
  }
  public void setPeriod(Integer period) {
    this.period = period;
  }
  public String getStateReason() {
    return stateReason;
  }
  public void setStateReason(String stateReason) {
    this.stateReason = stateReason;
  }
  public String getStateReasonData() {
    return stateReasonData;
  }
  public void setStateReasonData(String stateReasonData) {
    this.stateReasonData = stateReasonData;
  }
  public Date getStateUpdatedTimestamp() {
    return stateUpdatedTimestamp;
  }
  public void setStateUpdatedTimestamp(Date stateUpdatedTimestamp) {
    this.stateUpdatedTimestamp = stateUpdatedTimestamp;
  }
  public Date getLastActionsUpdatedTimestamp() {
    return lastActionsUpdatedTimestamp;
  }
  public void setLastActionsUpdatedTimestamp(Date lastActionsUpdatedTimestamp) {
    this.lastActionsUpdatedTimestamp = lastActionsUpdatedTimestamp;
  }
  public StateValue getStateValue() {
    return stateValue;
  }
  public void setStateValue(StateValue stateValue) {
    this.stateValue = stateValue;
  }
  public Statistic getStatistic() {
    return statistic;
  }
  public void setStatistic(Statistic statistic) {
    this.statistic = statistic;
  }
  public Units getUnit() {
    return unit;
  }
  public void setUnit(Units unit) {
    this.unit = unit;
  }
  public Double getThreshold() {
    return threshold;
  }
  public void setThreshold(Double threshold) {
    this.threshold = threshold;
  }
  public String getResourceName() {
    return String.format(
        "arn:aws:cloudwatch::%1s:alarm:%2s",
        getAccountId(),
        getAlarmName() );
  }

  public String getDisplayName() {
    return alarmName;
  }

  public OwnerFullName getOwner() {
    return AccountFullName.getInstance( accountId );
  }

  @Column(name="alarm_name", nullable = false)
  private String alarmName;

  @Column(name = "comparison_operator", nullable = false)
  @Enumerated(EnumType.STRING)
  private ComparisonOperator comparisonOperator;

  @Column(name = "evaluation_periods", nullable = false)
  private Integer evaluationPeriods;

  @Column(name = "metric_name", nullable = false)
  private String metricName;

  @Column(name = "metric_type", nullable = false)
  @Enumerated(EnumType.STRING)
  private MetricType metricType;

  @Column(name = "namespace", nullable = false)
  private String namespace;

  @Column(name = "period", nullable = false)
  private Integer period;

  @Column( name = "state_reason", length = 1023)
  private String stateReason;

  @Column( name = "state_reason_data", length =  4000)
  private String stateReasonData;
  
  @Column(name = "state_updated_timestamp", nullable = false)
  private Date stateUpdatedTimestamp;

  @Column(name = "last_actions_executed_timestamp", nullable = false)
  private Date lastActionsUpdatedTimestamp;

  @Column(name = "state_value", nullable = false)
  @Enumerated(EnumType.STRING)
  private StateValue stateValue;

  @Column(name = "statistic", nullable = false)
  @Enumerated(EnumType.STRING)
  private Statistic statistic;

  @Column(name = "unit", nullable = false)
  @Enumerated(EnumType.STRING)
  private Units unit;

  @Column(name = "threshold", nullable = false)
  private Double threshold;

  public enum ComparisonOperator {
    GreaterThanOrEqualToThreshold,
    GreaterThanThreshold,
    LessThanThreshold,
    LessThanOrEqualToThreshold
  }
  
  public enum Statistic {
    SampleCount,
    Average,
    Sum,
    Minimum,
    Maximum
  }

  public enum StateValue {
    OK,
    ALARM,
    INSUFFICIENT_DATA
  }

  // OK ACTIONS
  
  public static final int MAX_OK_ACTIONS_NUM = 5;

  public Collection<String> getOkActions() {
    ArrayList<String> okActions = new ArrayList<String>();
    for (int actionNum = 1; actionNum <= MAX_OK_ACTIONS_NUM; actionNum++) {
      String okAction = getOkAction(actionNum);
      if (okAction != null) {
        okActions.add(okAction);
      }
    }
    return okActions;
  }
  /**
   * Sets all ok actions.  This method copies the input parameter, do not lazily load it.
   * @param okActions
   */
  public void setOkActions(Collection<String> okActions) {
    if (okActions != null && okActions.size() > MAX_OK_ACTIONS_NUM) {
      throw new IllegalArgumentException("Too many actions, " + okActions.size());
    }
    for (int actionNum = 1; actionNum <= MAX_OK_ACTIONS_NUM; actionNum++) {
      setOkAction(actionNum, null);
    }
    if (okActions == null) {
      return;
    }
    Iterator<String> iter = okActions.iterator();
    String action = null;
    for (int actionNum = 1; actionNum <= MAX_OK_ACTIONS_NUM; actionNum++) {
      if (!iter.hasNext()) {
        return;
      }
      action = iter.next();
      setOkAction(actionNum, action);
    }
  }

  @Column( name = "ok_action_1" )
  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  private String okAction1;

  @Column( name = "ok_action_2" )
  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  private String okAction2;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "ok_action_3" )
  private String okAction3;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "ok_action_4" )
  private String okAction4;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "ok_action_5" )
  private String okAction5;

  public String getOkAction1() {
    return okAction1;
  }
  public void setOkAction1(String okAction1) {
    this.okAction1 = okAction1;
  }
  public String getOkAction2() {
    return okAction2;
  }
  public void setOkAction2(String okAction2) {
    this.okAction2 = okAction2;
  }
  public String getOkAction3() {
    return okAction3;
  }
  public void setOkAction3(String okAction3) {
    this.okAction3 = okAction3;
  }
  public String getOkAction4() {
    return okAction4;
  }
  public void setOkAction4(String okAction4) {
    this.okAction4 = okAction4;
  }
  public String getOkAction5() {
    return okAction5;
  }
  public void setOkAction5(String okAction5) {
    this.okAction5 = okAction5;
  }
  private void setOkAction(int actionNum, String value) {
    try {
      if ((actionNum < 1) || (actionNum > MAX_OK_ACTIONS_NUM)) {
        throw new IllegalArgumentException("No such method");
      }
      Method m = this.getClass().getMethod("setOkAction"+actionNum, String.class);
      m.invoke(this, value);
    } catch (Exception ex) {
      LOG.error("Unable to invoke setOkAction"+actionNum+", method may not exist");
      LOG.error(ex,ex);
    }
  }

  private String getOkAction(int actionNum) {
    try {
      if ((actionNum < 1) || (actionNum > MAX_OK_ACTIONS_NUM)) {
        throw new IllegalArgumentException("No such method");
      }
      Method m = this.getClass().getMethod("getOkAction"+actionNum);
      return (String) m.invoke(this);
    } catch (Exception ex) {
      LOG.error("Unable to invoke getOkAction" + actionNum + ", method may not exist");
      LOG.error(ex,ex);
      return null;
    }
  }
  
  // ALARM ACTIONS
  public static final int MAX_ALARM_ACTIONS_NUM = 5;

  public Collection<String> getAlarmActions() {
    ArrayList<String> alarmActions = new ArrayList<String>();
    for (int actionNum = 1; actionNum <= MAX_ALARM_ACTIONS_NUM; actionNum++) {
      String alarmAction = getAlarmAction(actionNum);
      if (alarmAction != null) {
        alarmActions.add(alarmAction);
      }
    }
    return alarmActions;
  }
  /**
   * Sets all alarm actions.  This method copies the input parameter, do not lazily load it.
   * @param alarmActions
   */
  public void setAlarmActions(Collection<String> alarmActions) {
    if (alarmActions != null && alarmActions.size() > MAX_ALARM_ACTIONS_NUM) {
      throw new IllegalArgumentException("Too many actions, " + alarmActions.size());
    }
    for (int actionNum = 1; actionNum <= MAX_ALARM_ACTIONS_NUM; actionNum++) {
      setAlarmAction(actionNum, null);
    }
    if (alarmActions == null) {
      return;
    }
    Iterator<String> iter = alarmActions.iterator();
    String action = null;
    for (int actionNum = 1; actionNum <= MAX_ALARM_ACTIONS_NUM; actionNum++) {
      if (!iter.hasNext()) {
        return;
      }
      action = iter.next();
      setAlarmAction(actionNum, action);
    }
  }

  @Column( name = "alarm_action_1" )
  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  private String alarmAction1;

  @Column( name = "alarm_action_2" )
  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  private String alarmAction2;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "alarm_action_3" )
  private String alarmAction3;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "alarm_action_4" )
  private String alarmAction4;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "alarm_action_5" )
  private String alarmAction5;

  public String getAlarmAction1() {
    return alarmAction1;
  }
  public void setAlarmAction1(String alarmAction1) {
    this.alarmAction1 = alarmAction1;
  }
  public String getAlarmAction2() {
    return alarmAction2;
  }
  public void setAlarmAction2(String alarmAction2) {
    this.alarmAction2 = alarmAction2;
  }
  public String getAlarmAction3() {
    return alarmAction3;
  }
  public void setAlarmAction3(String alarmAction3) {
    this.alarmAction3 = alarmAction3;
  }
  public String getAlarmAction4() {
    return alarmAction4;
  }
  public void setAlarmAction4(String alarmAction4) {
    this.alarmAction4 = alarmAction4;
  }
  public String getAlarmAction5() {
    return alarmAction5;
  }
  public void setAlarmAction5(String alarmAction5) {
    this.alarmAction5 = alarmAction5;
  }
  private void setAlarmAction(int actionNum, String value) {
    try {
      if ((actionNum < 1) || (actionNum > MAX_ALARM_ACTIONS_NUM)) {
        throw new IllegalArgumentException("No such method");
      }
      Method m = this.getClass().getMethod("setAlarmAction"+actionNum, String.class);
      m.invoke(this, value);
    } catch (Exception ex) {
      LOG.error("Unable to invoke setAlarmAction"+actionNum+", method may not exist");
      LOG.error(ex,ex);
    }
  }

  private String getAlarmAction(int actionNum) {
    try {
      if ((actionNum < 1) || (actionNum > MAX_ALARM_ACTIONS_NUM)) {
        throw new IllegalArgumentException("No such method");
      }
      Method m = this.getClass().getMethod("getAlarmAction"+actionNum);
      return (String) m.invoke(this);
    } catch (Exception ex) {
      LOG.error("Unable to invoke getAlarmAction" + actionNum + ", method may not exist");
      LOG.error(ex,ex);
      return null;
    }
  }

  // INSUFFICIENT_DATA ACTIONS
  public static final int MAX_INSUFFICIENT_DATA_ACTIONS_NUM = 5;

  public Collection<String> getInsufficientDataActions() {
    ArrayList<String> insufficientDataActions = new ArrayList<String>();
    for (int actionNum = 1; actionNum <= MAX_INSUFFICIENT_DATA_ACTIONS_NUM; actionNum++) {
      String insufficientDataAction = getInsufficientDataAction(actionNum);
      if (insufficientDataAction != null) {
        insufficientDataActions.add(insufficientDataAction);
      }
    }
    return insufficientDataActions;
  }
  /**
   * Sets all insufficientData actions.  This method copies the input parameter, do not lazily load it.
   * @param insufficientDataActions
   */
  public void setInsufficientDataActions(Collection<String> insufficientDataActions) {
    if (insufficientDataActions != null && insufficientDataActions.size() > MAX_INSUFFICIENT_DATA_ACTIONS_NUM) {
      throw new IllegalArgumentException("Too many actions, " + insufficientDataActions.size());
    }
    for (int actionNum = 1; actionNum <= MAX_INSUFFICIENT_DATA_ACTIONS_NUM; actionNum++) {
      setInsufficientDataAction(actionNum, null);
    }
    if (insufficientDataActions == null) {
      return;
    }
    Iterator<String> iter = insufficientDataActions.iterator();
    String action = null;
    for (int actionNum = 1; actionNum <= MAX_INSUFFICIENT_DATA_ACTIONS_NUM; actionNum++) {
      if (!iter.hasNext()) {
        return;
      }
      action = iter.next();
      setInsufficientDataAction(actionNum, action);
    }
  }

  @Column( name = "insufficient_data_action_1" )
  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  private String insufficientDataAction1;

  @Column( name = "insufficient_data_action_2" )
  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  private String insufficientDataAction2;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "insufficient_data_action_3" )
  private String insufficientDataAction3;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "insufficient_data_action_4" )
  private String insufficientDataAction4;

  @Lob
  @Type(type="org.hibernate.type.StringClobType")  
  @Column( name = "insufficient_data_action_5" )
  private String insufficientDataAction5;

  public String getInsufficientDataAction1() {
    return insufficientDataAction1;
  }
  public void setInsufficientDataAction1(String insufficientDataAction1) {
    this.insufficientDataAction1 = insufficientDataAction1;
  }
  public String getInsufficientDataAction2() {
    return insufficientDataAction2;
  }
  public void setInsufficientDataAction2(String insufficientDataAction2) {
    this.insufficientDataAction2 = insufficientDataAction2;
  }
  public String getInsufficientDataAction3() {
    return insufficientDataAction3;
  }
  public void setInsufficientDataAction3(String insufficientDataAction3) {
    this.insufficientDataAction3 = insufficientDataAction3;
  }
  public String getInsufficientDataAction4() {
    return insufficientDataAction4;
  }
  public void setInsufficientDataAction4(String insufficientDataAction4) {
    this.insufficientDataAction4 = insufficientDataAction4;
  }
  public String getInsufficientDataAction5() {
    return insufficientDataAction5;
  }
  public void setInsufficientDataAction5(String insufficientDataAction5) {
    this.insufficientDataAction5 = insufficientDataAction5;
  }
  private void setInsufficientDataAction(int actionNum, String value) {
    try {
      if ((actionNum < 1) || (actionNum > MAX_INSUFFICIENT_DATA_ACTIONS_NUM)) {
        throw new IllegalArgumentException("No such method");
      }
      Method m = this.getClass().getMethod("setInsufficientDataAction"+actionNum, String.class);
      m.invoke(this, value);
    } catch (Exception ex) {
      LOG.error("Unable to invoke setInsufficientDataAction"+actionNum+", method may not exist");
      LOG.error(ex,ex);
    }
  }

  private String getInsufficientDataAction(int actionNum) {
    try {
      if ((actionNum < 1) || (actionNum > MAX_INSUFFICIENT_DATA_ACTIONS_NUM)) {
        throw new IllegalArgumentException("No such method");
      }
      Method m = this.getClass().getMethod("getInsufficientDataAction"+actionNum);
      return (String) m.invoke(this);
    } catch (Exception ex) {
      LOG.error("Unable to invoke getInsufficientDataAction" + actionNum + ", method may not exist");
      LOG.error(ex,ex);
      return null;
    }
  }

}


File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/alarms/AlarmManager.java
/*************************************************************************
 * Copyright 2009-2015 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 *
 * This file may incorporate work covered under the following copyright
 * and permission notice:
 *
 *   Copyright 2010-2014 Amazon.com, Inc. or its affiliates. All Rights
 *   Reserved.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License").
 *   You may not use this file except in compliance with the License.
 *   A copy of the License is located at
 *
 *   http://aws.amazon.com/apache2.0
 *
 *   or in the "license" file accompanying this file. This file is
 *   distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
 *   ANY KIND, either express or implied. See the License for the specific
 *   language governing permissions and limitations under the License.
 ************************************************************************/

package com.eucalyptus.cloudwatch.domain.alarms;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;
import javax.persistence.EntityTransaction;

import net.sf.json.JSONObject;

import org.apache.log4j.Logger;
import org.hibernate.Criteria;
import org.hibernate.criterion.Junction;
import org.hibernate.criterion.Order;
import org.hibernate.criterion.Projections;
import org.hibernate.criterion.Restrictions;

import com.eucalyptus.auth.principal.AccountFullName;
import com.eucalyptus.autoscaling.common.AutoScaling;
import com.eucalyptus.autoscaling.common.msgs.AutoScalingMessage;
import com.eucalyptus.autoscaling.common.msgs.ExecutePolicyType;
import com.eucalyptus.cloudwatch.backend.CloudWatchException;
import com.eucalyptus.cloudwatch.common.CloudWatchMetadata;
import com.eucalyptus.cloudwatch.common.CloudWatchResourceName;
import com.eucalyptus.cloudwatch.backend.ResourceNotFoundException;
import com.eucalyptus.cloudwatch.domain.DimensionEntity;
import com.eucalyptus.cloudwatch.domain.NextTokenUtils;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmEntity.ComparisonOperator;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmEntity.StateValue;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmEntity.Statistic;
import com.eucalyptus.cloudwatch.domain.alarms.AlarmHistory.HistoryItemType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;
import com.eucalyptus.component.id.Eucalyptus;
import com.eucalyptus.compute.common.ComputeMessage;
import com.eucalyptus.compute.common.backend.StopInstancesType;
import com.eucalyptus.compute.common.backend.TerminateInstancesType;
import com.eucalyptus.crypto.util.Timestamps;
import com.eucalyptus.entities.Entities;
import com.eucalyptus.records.Logs;
import com.eucalyptus.util.CollectionUtils;
import com.eucalyptus.util.Callback;
import com.eucalyptus.util.DispatchingClient;
import com.google.common.base.Optional;
import com.google.common.base.Predicate;
import com.google.common.collect.HashMultimap;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Multimap;
import com.google.common.collect.Sets;

public class AlarmManager {
  private static final Logger LOG = Logger.getLogger(AlarmManager.class);
  public static Long countMetricAlarms(String accountId) {
    EntityTransaction db = Entities.get(AlarmEntity.class);
    try {
      Criteria criteria = Entities.createCriteria(AlarmEntity.class);
      criteria = criteria.setProjection(Projections.rowCount());
      if (accountId != null) {
        criteria = criteria.add( Restrictions.eq( "accountId" , accountId ) );
      }
      return (Long) criteria.uniqueResult();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      db.rollback();
    }
  }
  public static void putMetricAlarm(String accountId, Boolean actionsEnabled,
      Collection<String> alarmActions, String alarmDescription,
      String alarmName, ComparisonOperator comparisonOperator,
      Map<String, String> dimensionMap, Integer evaluationPeriods,
      Collection<String> insufficientDataActions, String metricName,
      MetricType metricType, String namespace, Collection<String> okActions,
      Integer period, Statistic statistic, Double threshold, Units unit) {

    if (dimensionMap == null) {
      dimensionMap = Maps.newHashMap();
    } else if (dimensionMap.size() > AlarmEntity.MAX_DIM_NUM) {
      throw new IllegalArgumentException("Too many dimensions for metric, " + dimensionMap.size());
    }

    AlarmEntity alarmEntity = new AlarmEntity();
    alarmEntity.setAccountId(accountId);
    alarmEntity.setAlarmName(alarmName);
    EntityTransaction db = Entities.get(AlarmEntity.class);
    boolean inDb = false;
    try {
      Criteria criteria = Entities.createCriteria(AlarmEntity.class)
          .add( Restrictions.eq( "accountId" , accountId ) )
          .add( Restrictions.eq( "alarmName" , alarmName ) );
      AlarmEntity inDbAlarm = (AlarmEntity) criteria.uniqueResult();
      if (inDbAlarm != null) {
        inDb = true;
        alarmEntity = inDbAlarm;
      } 
      alarmEntity.setActionsEnabled(actionsEnabled);
      alarmEntity.setAlarmActions(alarmActions);
      alarmEntity.setAlarmDescription(alarmDescription);
      alarmEntity.setComparisonOperator(comparisonOperator);
      TreeSet<DimensionEntity> dimensions = Sets.newTreeSet();
      for (Map.Entry<String,String> entry: dimensionMap.entrySet()) {
        DimensionEntity d = new DimensionEntity();
        d.setName(entry.getKey());
        d.setValue(entry.getValue());
        dimensions.add(d);
      }
      alarmEntity.setDimensions(dimensions);
      alarmEntity.setEvaluationPeriods(evaluationPeriods);
      alarmEntity.setInsufficientDataActions(insufficientDataActions);
      alarmEntity.setMetricName(metricName);
      alarmEntity.setMetricType(metricType);
      alarmEntity.setNamespace(namespace);
      alarmEntity.setOkActions(okActions);
      alarmEntity.setPeriod(period);
      alarmEntity.setStatistic(statistic);
      alarmEntity.setThreshold(threshold);
      alarmEntity.setUnit(unit);
      Date now = new Date();
      alarmEntity.setAlarmConfigurationUpdatedTimestamp(now);
      if (!inDb) {
        alarmEntity.setStateValue(StateValue.INSUFFICIENT_DATA);
        alarmEntity.setStateReason("Unchecked: Initial alarm creation");
        alarmEntity.setStateUpdatedTimestamp(now);
        // TODO: revisit (we are not firing actions on alarm creation, but may after one period)
        alarmEntity.setLastActionsUpdatedTimestamp(now); 
        JSONObject historyDataJSON = new JSONObject();
        historyDataJSON.element("version", "1.0");
        historyDataJSON.element("type", "Create");
        JSONObject historyDataDeletedAlarmJSON = getJSONObjectFromAlarmEntity(alarmEntity);
        historyDataJSON.element("createdAlarm", historyDataDeletedAlarmJSON);
        String historyData = historyDataJSON.toString();
        AlarmManager.addAlarmHistoryItem(accountId, alarmName, historyData, 
            HistoryItemType.ConfigurationUpdate, "Alarm \"" + alarmName + "\" created", now);
        Entities.persist(alarmEntity);
      } else {
        JSONObject historyDataJSON = new JSONObject();
        historyDataJSON.element("version", "1.0");
        historyDataJSON.element("type", "Update");
        JSONObject historyDataDeletedAlarmJSON = getJSONObjectFromAlarmEntity(alarmEntity);
        historyDataJSON.element("updatedAlarm", historyDataDeletedAlarmJSON);
        String historyData = historyDataJSON.toString();
        AlarmManager.addAlarmHistoryItem(accountId, alarmName, historyData, 
            HistoryItemType.ConfigurationUpdate, "Alarm \"" + alarmName + "\" updated", now);
      }
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
  }

  static void addAlarmHistoryItem(String accountId, String alarmName,
      String historyData, HistoryItemType historyItemType, String historySummary,
      Date now) {
    if (now == null) now = new Date();
    EntityTransaction db = Entities.get(AlarmHistory.class);
    try {
      AlarmHistory alarmHistory = new AlarmHistory();
      alarmHistory.setAccountId(accountId);
      alarmHistory.setAlarmName(alarmName);
      alarmHistory.setHistoryData(historyData);
      alarmHistory.setHistoryItemType(historyItemType);
      alarmHistory.setHistorySummary(historySummary);
      alarmHistory.setTimestamp(now);
      Entities.persist(alarmHistory);
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
  }
  
  public static boolean deleteAlarms(
      final String accountId,
      final Collection<String> alarmNames,
      final Predicate<CloudWatchMetadata.AlarmMetadata> filter
  ) {
    return modifySelectedAlarms( accountId, alarmNames, filter, new Predicate<AlarmEntity>() {
      private final Date now = new Date();

      @Override
      public boolean apply( final AlarmEntity alarmEntity ) {
        final String alarmName = alarmEntity.getAlarmName();
        JSONObject historyDataJSON = new JSONObject();
        historyDataJSON.element( "version", "1.0" );
        historyDataJSON.element( "type", "Delete" );
        JSONObject historyDataDeletedAlarmJSON = getJSONObjectFromAlarmEntity( alarmEntity );
        historyDataJSON.element( "deletedAlarm", historyDataDeletedAlarmJSON );
        String historyData = historyDataJSON.toString();
        AlarmManager.addAlarmHistoryItem( alarmEntity.getAccountId(), alarmName, historyData,
            HistoryItemType.ConfigurationUpdate, "Alarm \"" + alarmName + "\" deleted", now );
        Entities.delete( alarmEntity );
        return true;
      }
    } );
  }

  private static JSONObject getJSONObjectFromAlarmEntity(AlarmEntity alarmEntity) {
    JSONObject jsonObject = new JSONObject();
    jsonObject.element("threshold", alarmEntity.getThreshold());
    jsonObject.element("namespace", alarmEntity.getNamespace());
    jsonObject.element("stateValue", alarmEntity.getStateValue().toString());
    ArrayList<JSONObject> dimensions = new ArrayList<JSONObject>();
    if (alarmEntity.getDimensions() != null) {
      for (DimensionEntity dimensionEntity: alarmEntity.getDimensions()) {
        JSONObject dimension = new JSONObject();
        dimension.element("name", dimensionEntity.getName());
        dimension.element("value", dimensionEntity.getValue());
        dimensions.add(dimension);
      }
    }
    jsonObject.element("dimensions", dimensions);
    jsonObject.element("okactions", alarmEntity.getOkActions() != null ? alarmEntity.getOkActions() : new ArrayList<String>());
    jsonObject.element("alarmActions", alarmEntity.getAlarmActions() != null ? alarmEntity.getAlarmActions() : new ArrayList<String>());
    jsonObject.element("evaluationPeriods", alarmEntity.getEvaluationPeriods());
    jsonObject.element("comparisonOperator", alarmEntity.getComparisonOperator().toString());
    jsonObject.element("metricName", alarmEntity.getMetricName());
    jsonObject.element("period", alarmEntity.getPeriod());
    jsonObject.element("alarmName", alarmEntity.getAlarmName());
    jsonObject.element("insufficientDataActions", alarmEntity.getInsufficientDataActions() != null ? alarmEntity.getInsufficientDataActions() : new ArrayList<String>());
    jsonObject.element("actionsEnabled", alarmEntity.getActionsEnabled());
    jsonObject.element("alarmDescription", alarmEntity.getAlarmDescription());
    jsonObject.element("statistic", alarmEntity.getStatistic());
    jsonObject.element("alarmArn", alarmEntity.getResourceName());
    jsonObject.element("alarmConfigurationUpdatedTimestamp", Timestamps.formatIso8601UTCLongDateMillisTimezone(alarmEntity.getAlarmConfigurationUpdatedTimestamp()));
    jsonObject.element("stateUpdatedTimestamp", Timestamps.formatIso8601UTCLongDateMillisTimezone(alarmEntity.getStateUpdatedTimestamp()));
    return jsonObject;
  }

  /**
   * @return False if enable rejected due to filter
   */
  public static boolean enableAlarmActions(
      final String accountId,
      final Collection<String> alarmNames,
      final Predicate<CloudWatchMetadata.AlarmMetadata> filter
  ) {
    return modifySelectedAlarms( accountId, alarmNames, filter, new Predicate<AlarmEntity>() {
      private final Date now = new Date();

      @Override
      public boolean apply( final AlarmEntity alarmEntity ) {
        final String alarmName = alarmEntity.getAlarmName();
        if ( !Boolean.TRUE.equals( alarmEntity.getActionsEnabled() ) ) {
          JSONObject historyDataJSON = new JSONObject();
          historyDataJSON.element( "version", "1.0" );
          historyDataJSON.element( "type", "Update" );
          JSONObject historyDataDeletedAlarmJSON = getJSONObjectFromAlarmEntity( alarmEntity );
          historyDataJSON.element( "updatedAlarm", historyDataDeletedAlarmJSON );
          String historyData = historyDataJSON.toString();
          AlarmManager.addAlarmHistoryItem( alarmEntity.getAccountId(), alarmName, historyData,
              HistoryItemType.ConfigurationUpdate, "Alarm \"" + alarmName + "\" updated", now );
          alarmEntity.setActionsEnabled( Boolean.TRUE );
        }
        return true;
      }
    } );
  }

  /**
   * @return False if disable rejected due to filter
   */
  public static boolean disableAlarmActions(
      final String accountId,
      final Collection<String> alarmNames,
      final Predicate<CloudWatchMetadata.AlarmMetadata> filter
  ) {
    return modifySelectedAlarms( accountId, alarmNames, filter, new Predicate<AlarmEntity>() {
      private final Date now = new Date();

      @Override
      public boolean apply( final AlarmEntity alarmEntity ) {
        final String alarmName = alarmEntity.getAlarmName();
        if ( !Boolean.FALSE.equals( alarmEntity.getActionsEnabled() ) ) {
          JSONObject historyDataJSON = new JSONObject();
          historyDataJSON.element( "version", "1.0" );
          historyDataJSON.element( "type", "Update" );
          JSONObject historyDataDeletedAlarmJSON = getJSONObjectFromAlarmEntity( alarmEntity );
          historyDataJSON.element( "updatedAlarm", historyDataDeletedAlarmJSON );
          String historyData = historyDataJSON.toString();
          AlarmManager.addAlarmHistoryItem( alarmEntity.getAccountId(), alarmName, historyData,
              HistoryItemType.ConfigurationUpdate, "Alarm \"" + alarmName + "\" updated", now );
          alarmEntity.setActionsEnabled( Boolean.FALSE );
        }
        return true;
      }
    } );
  }

  private static boolean modifySelectedAlarms(
      final String accountId,
      final Collection<String> alarmNames,
      final Predicate<CloudWatchMetadata.AlarmMetadata> filter,
      final Predicate<AlarmEntity> update
  ) {
    final Map<String,Collection<String>> accountToNamesMap =
        buildAccountIdToAlarmNamesMap( accountId, alarmNames );
    final EntityTransaction db = Entities.get( AlarmEntity.class );
    try {
      final Criteria criteria = Entities.createCriteria(AlarmEntity.class);
      final Junction disjunction = Restrictions.disjunction();
      for ( final Map.Entry<String,Collection<String>> entry : accountToNamesMap.entrySet( ) ) {
        final Junction conjunction = Restrictions.conjunction();
        conjunction.add( Restrictions.eq( "accountId", entry.getKey() ) );
        conjunction.add( Restrictions.in( "alarmName", entry.getValue() ) );
        disjunction.add( conjunction );
      }
      criteria.add( disjunction );
      criteria.addOrder( Order.asc( "creationTimestamp" ) );
      criteria.addOrder( Order.asc( "naturalId" ) );
      final Collection<AlarmEntity> alarmEntities = (Collection<AlarmEntity>) criteria.list();
      if ( !Iterables.all( alarmEntities, filter ) ) {
        return false;
      }
      CollectionUtils.each( alarmEntities, update );
      db.commit();
      return true;
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
  }

  private static Map<String,Collection<String>> buildAccountIdToAlarmNamesMap(
      @Nullable final String accountId,
      @Nullable final Collection<String> alarmNames
  ) {
    final Multimap<String,String> alarmNamesMultimap = HashMultimap.create( );
    if ( alarmNames != null ) {
      if ( accountId != null ) {
        alarmNamesMultimap.putAll( accountId, alarmNames ); // An ARN is also a valid name
      }
      CollectionUtils.putAll(
          Optional.presentInstances( Iterables.transform(
              alarmNames,
              CloudWatchResourceName.asArnOfType( CloudWatchResourceName.Type.alarm ) ) ),
          alarmNamesMultimap,
          CloudWatchResourceName.toNamespace( ),
          CloudWatchResourceName.toName( )
      );
    }
    return alarmNamesMultimap.asMap();
  }

  public static void setAlarmState(
      final String accountId,
      final String alarmName,
      final String stateReason,
      final String stateReasonData,
      final StateValue stateValue,
      final Predicate<CloudWatchMetadata.AlarmMetadata> filter
  ) throws CloudWatchException {
    final EntityTransaction db = Entities.get(AlarmEntity.class);
    try {
      AlarmEntity alarmEntity = (AlarmEntity) Entities.createCriteria( AlarmEntity.class )
          .add( Restrictions.eq( "accountId" , accountId ) )
          .add( Restrictions.eq( "alarmName" , alarmName ) )
          .uniqueResult();
      if ( alarmEntity == null && CloudWatchResourceName.isResourceName().apply( alarmName ) ) try {
        final CloudWatchResourceName arn =
            CloudWatchResourceName.parse( alarmName, CloudWatchResourceName.Type.alarm );
        alarmEntity = (AlarmEntity) Entities.createCriteria(AlarmEntity.class)
          .add( Restrictions.eq( "accountId", arn.getNamespace() ) )
          .add( Restrictions.eq( "alarmName", arn.getName() ) )
          .uniqueResult();
      } catch ( CloudWatchResourceName.InvalidResourceNameException e ) {
      }
      if ( alarmEntity == null || !filter.apply( alarmEntity ) ) {
        throw new ResourceNotFoundException("Could not find alarm with name '" + alarmName + "'");
      }
      StateValue oldStateValue = alarmEntity.getStateValue();
      if (stateValue != oldStateValue) {
        Date evaluationDate = new Date();
        AlarmState newState = createAlarmState(stateValue, stateReason, stateReasonData);
        AlarmManager.changeAlarmState(alarmEntity, newState, evaluationDate);
        AlarmManager.executeActions(alarmEntity, newState, true, evaluationDate);
      }
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
  }

  public static List<AlarmEntity> describeAlarms(
      @Nullable final String accountId,
      @Nullable final String actionPrefix,
      @Nullable final String alarmNamePrefix,
      @Nullable final Collection<String> alarmNames,
      @Nullable final Integer maxRecords,
      @Nullable final StateValue stateValue,
      @Nullable final String nextToken,
                final Predicate<? super CloudWatchMetadata.AlarmMetadata> filter
  ) throws CloudWatchException {
    final List<AlarmEntity> results = Lists.newArrayList();
    final EntityTransaction db = Entities.get(AlarmEntity.class);
    try {
      boolean first = true;
      String token = nextToken;
      while ( token != null || first ) {
        first = false;
        final Date nextTokenCreatedTime = NextTokenUtils.getNextTokenCreatedTime(token, AlarmEntity.class, true);
        final Criteria criteria = Entities.createCriteria(AlarmEntity.class);
        if (accountId != null) {
          criteria.add( Restrictions.eq( "accountId" , accountId ) );
        }
        if (actionPrefix != null) {
          final Junction actionsOf = Restrictions.disjunction();
          for (int i=1; i<= AlarmEntity.MAX_OK_ACTIONS_NUM; i++) {
            actionsOf.add( Restrictions.like( "okAction" + i, actionPrefix + "%" ) ); // May need Restrictions.ilike for case insensitive
          }
          for (int i=1; i<= AlarmEntity.MAX_ALARM_ACTIONS_NUM; i++) {
            actionsOf.add( Restrictions.like( "alarmAction" + i, actionPrefix + "%" ) ); // May need Restrictions.ilike for case insensitive
          }
          for (int i=1; i<= AlarmEntity.MAX_INSUFFICIENT_DATA_ACTIONS_NUM; i++) {
            actionsOf.add( Restrictions.like( "insufficientDataAction" + i, actionPrefix + "%" ) ); // May need Restrictions.ilike for case insensitive
          }
          criteria.add( actionsOf );
        }
        if (alarmNamePrefix != null) {
          criteria.add( Restrictions.like( "alarmName" , alarmNamePrefix + "%" ) );
        }
        if (alarmNames != null && !alarmNames.isEmpty()) {
          criteria.add( Restrictions.in( "alarmName", alarmNames ) );
        }
        if (stateValue != null) {
          criteria.add( Restrictions.eq( "stateValue" , stateValue ) );
        }
        NextTokenUtils.addNextTokenConstraints(
            maxRecords == null ? null : maxRecords - results.size( ), token, nextTokenCreatedTime, criteria);
        final List<AlarmEntity> alarmEntities = (List<AlarmEntity>) criteria.list();
        Iterables.addAll( results, Iterables.filter( alarmEntities, filter ) );
        token = maxRecords==null || ( maxRecords!=null && ( results.size() >= maxRecords || alarmEntities.size() < maxRecords ) )  ?
            null :
            alarmEntities.get(alarmEntities.size() - 1).getNaturalId();
      }
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
    return results;
  }


  public static Collection<AlarmEntity> describeAlarmsForMetric(
    @Nullable final String accountId,
    @Nonnull  final Map<String, String> dimensionMap,
    @Nullable final String metricName,
    @Nullable final String namespace,
    @Nullable final Integer period,
    @Nullable final Statistic statistic,
    @Nullable final Units unit,
    @Nonnull  final Predicate<? super CloudWatchMetadata.AlarmMetadata> filter
  ) {
    final List<AlarmEntity> results = Lists.newArrayList();
    final EntityTransaction db = Entities.get(AlarmEntity.class);
    try {
      final Criteria criteria = Entities.createCriteria(AlarmEntity.class);
      if (accountId != null) {
        criteria.add( Restrictions.eq( "accountId" , accountId ) );
      }
      final Set<DimensionEntity> dimensions = Sets.newTreeSet( );
      for ( final Map.Entry<String,String> entry: dimensionMap.entrySet( ) ) {
        final DimensionEntity d = new DimensionEntity();
        d.setName(entry.getKey());
        d.setValue(entry.getValue());
        dimensions.add(d);
      }
      int dimIndex = 1;
      for (final DimensionEntity d: dimensions) {
        criteria.add( Restrictions.eq( "dim" + dimIndex + "Name", d.getName() ) );
        criteria.add( Restrictions.eq( "dim" + dimIndex + "Value", d.getValue() ) );
        dimIndex++;
      }
      while (dimIndex <= AlarmEntity.MAX_DIM_NUM) {
        criteria.add( Restrictions.isNull( "dim" + dimIndex + "Name") );
        criteria.add( Restrictions.isNull( "dim" + dimIndex + "Value") );
        dimIndex++;
      }

      if (metricName != null) {
        criteria.add( Restrictions.eq( "metricName" , metricName ) );
      }
      if (namespace != null) {
        criteria.add( Restrictions.eq( "namespace" , namespace ) );
      }
      if (period != null) {
        criteria.add( Restrictions.eq( "period" , period ) );
      }
      if (statistic != null) {
        criteria.add( Restrictions.eq( "statistic" , statistic ) );
      }
      if (unit != null) {
        criteria.add( Restrictions.eq( "unit" , unit ) );
      }
      final List<AlarmEntity> alarmEntities = (List<AlarmEntity>) criteria.list();
      Iterables.addAll( results, Iterables.filter( alarmEntities, filter ) );
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
    return results;
  }

  public static List<AlarmHistory> describeAlarmHistory(
      @Nullable final String accountId,
      @Nullable final String alarmName,
      @Nullable final Date endDate,
      @Nullable final HistoryItemType historyItemType,
      @Nullable final Integer maxRecords,
      @Nullable final Date startDate,
      @Nullable final String nextToken,
      final Predicate<AlarmHistory> filter ) throws CloudWatchException {
    final List<AlarmHistory> results = Lists.newArrayList();
    final EntityTransaction db = Entities.get(AlarmHistory.class);
    try {
      final Map<String,Collection<String>> accountToNamesMap = alarmName == null ?
          Collections.<String,Collection<String>>emptyMap( ) :
          buildAccountIdToAlarmNamesMap( accountId, Collections.singleton( alarmName ) );
      boolean first = true;
      String token = nextToken;
      while ( token != null || first ) {
        first = false;
        final Date nextTokenCreatedTime = NextTokenUtils.getNextTokenCreatedTime(token, AlarmHistory.class, true);
        final Criteria criteria = Entities.createCriteria(AlarmHistory.class);
        final Junction disjunction = Restrictions.disjunction();
        for ( final Map.Entry<String,Collection<String>> entry : accountToNamesMap.entrySet( ) ) {
          final Junction conjunction = Restrictions.conjunction();
          conjunction.add( Restrictions.eq( "accountId", entry.getKey() ) );
          conjunction.add( Restrictions.in( "alarmName", entry.getValue() ) );
          disjunction.add( conjunction );
        }
        criteria.add( disjunction );
        if (historyItemType != null) {
          criteria.add( Restrictions.eq( "historyItemType" , historyItemType ) );
        }
        if (startDate != null) {
          criteria.add( Restrictions.ge( "timestamp" , startDate ) );
        }
        if (endDate != null) {
          criteria.add( Restrictions.le( "timestamp" , endDate ) );
        }
        NextTokenUtils.addNextTokenConstraints(
            maxRecords == null ? null : maxRecords - results.size( ), token, nextTokenCreatedTime, criteria);
        final List<AlarmHistory> alarmHistoryEntities = (List<AlarmHistory>) criteria.list();
        Iterables.addAll( results, Iterables.filter( alarmHistoryEntities, filter ) );
        token = maxRecords==null || ( maxRecords!=null && ( results.size() >= maxRecords || alarmHistoryEntities.size() < maxRecords ) ) ?
            null :
            alarmHistoryEntities.get(alarmHistoryEntities.size() - 1).getNaturalId();
      }
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
    return results;
  }

  /**
   * Delete all alarm history before a certain date
   * @param before the date to delete before (inclusive)
   */
  public static void deleteAlarmHistory(Date before) {
    EntityTransaction db = Entities.get(AlarmHistory.class);
    try {
      Map<String, Date> criteria = Maps.newHashMap();
      criteria.put("before", before);
      Entities.deleteAllMatching(AlarmHistory.class, "WHERE timestamp < :before", criteria);
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
  }

  
  static void changeAlarmState(AlarmEntity alarmEntity, AlarmState newState, Date now) {
    LOG.info("Updating alarm " + alarmEntity.getAlarmName() + " from " + alarmEntity.getStateValue() + " to " + newState.getStateValue());
    alarmEntity.setStateUpdatedTimestamp(now);
    JSONObject historyDataJSON = new JSONObject();
    historyDataJSON.element("version", "1.0");
    historyDataJSON.element("oldState", getJSONObjectFromState(alarmEntity.getStateValue(), alarmEntity.getStateReason(), alarmEntity.getStateReasonData()));
    historyDataJSON.element("newState", getJSONObjectFromState(newState.getStateValue(), newState.getStateReason(), newState.getStateReasonData()));
    String historyData = historyDataJSON.toString();
    AlarmManager.addAlarmHistoryItem(alarmEntity.getAccountId(), alarmEntity.getAlarmName(), historyData, 
        HistoryItemType.StateUpdate, " Alarm updated from " + alarmEntity.getStateValue() + " to " + newState.getStateValue(), now);
    alarmEntity.setStateReason(newState.getStateReason());
    alarmEntity.setStateReasonData(newState.getStateReasonData());
    alarmEntity.setStateValue(newState.getStateValue());
    alarmEntity.setStateUpdatedTimestamp(now);
  }


  private static JSONObject getJSONObjectFromState(StateValue stateValue,
      String stateReason, String stateReasonData) {
    JSONObject jsonObject = new JSONObject();
    jsonObject.element("stateValue", stateValue.toString());
    jsonObject.element("stateReason", stateReason);
    if (stateReasonData != null) {
      jsonObject.element("stateReasonData", stateReasonData);
    }
    return jsonObject;
  }

  static void executeActions(AlarmEntity alarmEntity, AlarmState state,
      boolean stateJustChanged, Date now) {
    if (alarmEntity.getActionsEnabled()) {
      Collection<String> actions = AlarmUtils.getActionsByState(alarmEntity, state);
      for (String action: actions) {
        Action actionToExecute = ActionManager.getAction(action, alarmEntity.getDimensionMap());
        if (actionToExecute == null) {
          LOG.warn("Unsupported action " + action); // TODO: do not let it in to start with...
        } 
        // always execute autoscaling actions, but others only on state change...
        else if (actionToExecute.alwaysExecute() || stateJustChanged) {
          LOG.info("Executing alarm " + alarmEntity.getAlarmName() + " action " + action);
          actionToExecute.executeAction(action, alarmEntity.getDimensionMap(), alarmEntity, now);
        }
      }
    }
    alarmEntity.setLastActionsUpdatedTimestamp(now);
  }

  private static String createStateReasonData(StateValue stateValue,
      List<Double> relevantDataPoints, List<Double> recentDataPoints,
      ComparisonOperator comparisonOperator, Double threshold, String stateReason, Integer period, Date queryDate, Statistic statistic) {
    JSONObject stateReasonDataJSON = new JSONObject();
    stateReasonDataJSON.element("version", "1.0");
    stateReasonDataJSON.element("queryDate", Timestamps.formatIso8601UTCLongDateMillisTimezone(queryDate));
    stateReasonDataJSON.element("statistic", statistic.toString());
    stateReasonDataJSON.element("recentDatapoints", pruneNullsAtBeginning(recentDataPoints));
    stateReasonDataJSON.element("period", period);
    stateReasonDataJSON.element("threshold", threshold);
    String stateReasonData = stateReasonDataJSON.toString();
    return stateReasonData;
  }
  
  private static List<Double> pruneNullsAtBeginning(List<Double> recentDataPoints) {
    ArrayList<Double> returnValue = new ArrayList<Double>();
    boolean foundNotNull = false;
    for (Double recentDataPoint: recentDataPoints) {
      if (recentDataPoint != null) {
        foundNotNull = true;
      }
      if (foundNotNull) {
        returnValue.add(recentDataPoint);
      }
    }
    return returnValue;
  }

  private static String createStateReason(StateValue stateValue, List<Double> relevantDataPoints,
      ComparisonOperator comparisonOperator, Double threshold) {
    String stateReason = null;
    if (stateValue == StateValue.INSUFFICIENT_DATA) {
      stateReason = "Insufficient Data: " + relevantDataPoints.size() +
          AlarmUtils.matchSingularPlural(relevantDataPoints.size(), " datapoint was ", " datapoints were ") +
          "unknown.";
    } else {
      stateReason = "Threshold Crossed: " + relevantDataPoints.size() + 
          AlarmUtils.matchSingularPlural(relevantDataPoints.size(), " datapoint ", " datapoints ") +
          AlarmUtils.makeDoubleList(relevantDataPoints) + 
          AlarmUtils.matchSingularPlural(relevantDataPoints.size(), " was ", " were ") +
          (stateValue == StateValue.OK ? " not " : "") + 
          AlarmUtils.comparisonOperatorString(comparisonOperator) + 
          " the threshold (" + threshold + ").";
    }
    return stateReason;
  }

  static AlarmState createAlarmState(StateValue stateValue,
      List<Double> relevantDataPoints, List<Double> recentDataPoints,
      ComparisonOperator comparisonOperator, Double threshold, Integer period, Date queryDate, Statistic statistic) {
    String stateReason = createStateReason(stateValue, relevantDataPoints, comparisonOperator, threshold);
    return createAlarmState(stateValue, relevantDataPoints, recentDataPoints, comparisonOperator, threshold, stateReason, period, queryDate, statistic);
  }
  
  static AlarmState createAlarmState(StateValue stateValue,
      List<Double> relevantDataPoints, List<Double> recentDataPoints,
      ComparisonOperator comparisonOperator, Double threshold, String stateReason, Integer period, Date queryDate, Statistic statistic) {
    String stateReasonData = createStateReasonData(stateValue, relevantDataPoints, recentDataPoints, comparisonOperator, threshold, stateReason, period, queryDate, statistic);
    return new AlarmState(stateValue, stateReason, stateReasonData);
  }

  private static AlarmState createAlarmState(StateValue stateValue,
      String stateReason, String stateReasonData) {
    return new AlarmState(stateValue, stateReason, stateReasonData);
  }
  
  private static class AutoScalingClient extends DispatchingClient<AutoScalingMessage,AutoScaling> {
    public AutoScalingClient( final String userId ) {
      super( userId, AutoScaling.class );
    }

    public AutoScalingClient( final AccountFullName accountFullName ) {
      super( accountFullName, AutoScaling.class );
    }
  }

  private static class EucalyptusClient extends DispatchingClient<ComputeMessage,Eucalyptus> {
    public EucalyptusClient( final String userId ) {
      super( userId, Eucalyptus.class );
    }

    public EucalyptusClient( final AccountFullName accountFullName ) {
      super( accountFullName, Eucalyptus.class );
    }
  }
  
  private static abstract class Action {
    public abstract boolean filter(final String actionURN, final Map<String, String> dimensionMap);
    public abstract void executeAction(final String actionARN, final Map<String, String> dimensionMap, final AlarmEntity alarmEntity, final Date now);
    public abstract boolean alwaysExecute();
    public void success(final String actionARN, final AlarmEntity alarmEntity, final Date now) {
      JSONObject historyDataJSON = new JSONObject();
      historyDataJSON.element("actionState", "Succeeded");
      historyDataJSON.element("notificationResource", actionARN);
      historyDataJSON.element("stateUpdateTimestamp", Timestamps.formatIso8601UTCLongDateMillisTimezone(alarmEntity.getStateUpdatedTimestamp()));
      String historyData = historyDataJSON.toString();
      AlarmManager.addAlarmHistoryItem(alarmEntity.getAccountId(), alarmEntity.getAlarmName(), historyData, 
        HistoryItemType.Action, " Successfully executed action " + actionARN, now);
    }
    public void failure(final String actionARN, final AlarmEntity alarmEntity, final Date now, Throwable cause) {
      JSONObject historyDataJSON = new JSONObject();
      historyDataJSON.element("actionState", "Failed");
      historyDataJSON.element("notificationResource", actionARN);
      historyDataJSON.element("stateUpdateTimestamp", Timestamps.formatIso8601UTCLongDateMillisTimezone(alarmEntity.getStateUpdatedTimestamp()));
      historyDataJSON.element("error", cause.getMessage() != null ? cause.getMessage() : cause.getClass().getName());
      String historyData = historyDataJSON.toString();
      AlarmManager.addAlarmHistoryItem(alarmEntity.getAccountId(), alarmEntity.getAlarmName(), historyData, 
        HistoryItemType.Action, " Failed to execute action " + actionARN, now);
    }
   }
  private static class ExecuteAutoScalingPolicyAction extends Action {
    @Override
    public boolean filter(String action, Map<String, String> dimensionMap) {
      return (action != null && action.startsWith("arn:aws:autoscaling:"));
    }

    @Override
    public void executeAction(final String action, final Map<String, String> dimensionMap, final AlarmEntity alarmEntity, final Date now) {
      ExecutePolicyType executePolicyType = new ExecutePolicyType();
      executePolicyType.setPolicyName(action);
      executePolicyType.setHonorCooldown(true);
      Callback.Checked<AutoScalingMessage> callback = new Callback.Checked<AutoScalingMessage>() {
        @Override
        public void fire(AutoScalingMessage input) {
          success(action, alarmEntity, now);
        }

        @Override
        public void fireException(Throwable t) {
          failure(action, alarmEntity, now, t);
        }
      };
      try {
        AutoScalingClient client = new AutoScalingClient(AccountFullName.getInstance( alarmEntity.getAccountId() ));
        client.init();
        client.dispatch(executePolicyType, callback);
      } catch (Exception ex) {
        failure(action, alarmEntity, now, ex);
      }
    }

    @Override
    public boolean alwaysExecute() {
      return true;
    }

  }
 
  private static class TerminateInstanceAction extends Action {

    @Override
    public boolean filter(String action, Map<String, String> dimensionMap) {
      if (action == null) return false;
      // Example:
      // arn:aws:automate:us-east-1:ec2:terminate
      if (!action.startsWith("arn:aws:automate:")) return false;
      if (!action.endsWith(":ec2:terminate")) return false;
      if (dimensionMap == null) return false;
      return (dimensionMap.containsKey("InstanceId"));
    }

    @Override
    public void executeAction(final String action, final Map<String, String> dimensionMap, final AlarmEntity alarmEntity, final Date now) {
      TerminateInstancesType terminateInstances = new TerminateInstancesType();
      terminateInstances.getInstancesSet().add( dimensionMap.get("InstanceId"));
      Callback.Checked<ComputeMessage> callback = new Callback.Checked<ComputeMessage>() {
        @Override
        public void fire(ComputeMessage input) {
          success(action, alarmEntity, now);
        }

        @Override
        public void fireException(Throwable t) {
          failure(action, alarmEntity, now, t);
        }
      };
      try {
        EucalyptusClient client = new EucalyptusClient( AccountFullName.getInstance( alarmEntity.getAccountId( ) ) );
        client.init();
        client.dispatch(terminateInstances, callback);
      } catch (Exception ex) {
        failure(action, alarmEntity, now, ex);
      }
    }

    @Override
    public boolean alwaysExecute() {
      return false;
    }
  }
  private static class StopInstanceAction extends Action {

    @Override
    public boolean filter(String action, Map<String, String> dimensionMap) {
      if (action == null) return false;
      // Example:
      // arn:aws:automate:us-east-1:ec2:stop
      if (!action.startsWith("arn:aws:automate:")) return false;
      if (!action.endsWith(":ec2:stop")) return false;
      if (dimensionMap == null) return false;
      return (dimensionMap.containsKey("InstanceId"));
    }

    @Override
    public void executeAction(final String action, final Map<String, String> dimensionMap, final AlarmEntity alarmEntity, final Date now) {
      StopInstancesType stopInstances = new StopInstancesType();
      stopInstances.getInstancesSet().add( dimensionMap.get("InstanceId"));
      Callback.Checked<ComputeMessage> callback = new Callback.Checked<ComputeMessage>() {
        @Override
        public void fire(ComputeMessage input) {
          success(action, alarmEntity, now);
        }

        @Override
        public void fireException(Throwable t) {
          failure(action, alarmEntity, now, t);
        }
      };
      try {
        EucalyptusClient client = new EucalyptusClient(AccountFullName.getInstance( alarmEntity.getAccountId( ) ));
        client.init();
        client.dispatch(stopInstances, callback);
      } catch (Exception ex) {
        failure(action, alarmEntity, now, ex);
      }
    }

    @Override
    public boolean alwaysExecute() {
      return false;
    }
  }

  public static class ActionManager {
    private static List<Action> actions = new ArrayList<Action>();
    static {
      actions.add(new StopInstanceAction());
      actions.add(new TerminateInstanceAction());
      actions.add(new ExecuteAutoScalingPolicyAction());
      
    }
    public static Action getAction(String action, Map<String, String> dimensionMap) {
      for (Action actionFromList :actions) {
        if (actionFromList.filter(action, dimensionMap)) {
          return actionFromList;
        } 
      }
      return null;
    }
  }

}



File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/metricdata/GetMetricStatisticsAggregationKey.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain.metricdata;

import java.util.Comparator;
import java.util.Date;

import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;

public class GetMetricStatisticsAggregationKey {

  public static enum COMPARATOR_WITH_NULLS implements Comparator<GetMetricStatisticsAggregationKey> {
    INSTANCE {

      @Override
      public int compare(GetMetricStatisticsAggregationKey a, GetMetricStatisticsAggregationKey b) {
        if (a == b) return 0;
        if (a == null && b == null) return 0;
        if (a == null && b != null) return -1;
        if (a != null && b == null) return 1;
        // otherwise do it by fields...
        if (compare(a.accountId, b.accountId) != 0) {
          return compare(a.accountId, b.accountId);
        }
        if (compare(a.timestamp, b.timestamp) != 0) {
          return compare(a.timestamp, b.timestamp);
        }
        if (compare(a.namespace, b.namespace) != 0) {
          return compare(a.namespace, b.namespace);
        }
        if (compare(a.metricType, b.metricType) != 0) {
          return compare(a.metricType, b.metricType);
        }
        if (compare(a.metricName, b.metricName) != 0) {
          return compare(a.metricName, b.metricName);
        }
        if (compare(a.dimensionHash, b.dimensionHash) != 0) {
          return compare(a.dimensionHash, b.dimensionHash);
        }
        return compare(a.units, b.units);
      
      }
      
      private int compare(Units a, Units b) {
        // "null" is considered "less"
        if (a == null && b == null) return 0;
        if (a == null && b != null) return -1;
        if (a != null && b == null) return 1;
        return a.compareTo(b);
      }

      private int compare(Date a, Date b) {
        // "null" is considered "less"
        if (a == null && b == null) return 0;
        if (a == null && b != null) return -1;
        if (a != null && b == null) return 1;
        return a.compareTo(b);
      }

      private int compare(MetricType a, MetricType b) {
        // "null" is considered "less"
        if (a == null && b == null) return 0;
        if (a == null && b != null) return -1;
        if (a != null && b == null) return 1;
        return a.compareTo(b);
      }

      private int compare(String a, String b) {
        // "null" is considered "less"
        if (a == null && b == null) return 0;
        if (a == null && b != null) return -1;
        if (a != null && b == null) return 1;
        return a.compareTo(b);
      }
    }
  }

  
  private String accountId;
  private String namespace;
  private String metricName;
  private Units units;
  private MetricType metricType;
  private Date timestamp;
  private String dimensionHash;

  public GetMetricStatisticsAggregationKey(MetricEntity me, Date startTime,
      Integer period, String dimensionHash) {
    this.accountId = me.getAccountId();
    this.namespace = me.getNamespace();
    this.metricName = me.getMetricName();
    this.units = me.getUnits();
    this.metricType = me.getMetricType();
    this.timestamp = MetricManager.getPeriodStart(me.getTimestamp(), startTime, period);
    this.dimensionHash = dimensionHash;
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result + ((accountId == null) ? 0 : accountId.hashCode());
    result = prime * result
        + ((dimensionHash == null) ? 0 : dimensionHash.hashCode());
    result = prime * result
        + ((metricName == null) ? 0 : metricName.hashCode());
    result = prime * result
        + ((metricType == null) ? 0 : metricType.hashCode());
    result = prime * result + ((namespace == null) ? 0 : namespace.hashCode());
    result = prime * result + ((timestamp == null) ? 0 : timestamp.hashCode());
    result = prime * result + ((units == null) ? 0 : units.hashCode());
    return result;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (getClass() != obj.getClass())
      return false;
    GetMetricStatisticsAggregationKey other = (GetMetricStatisticsAggregationKey) obj;
    if (accountId == null) {
      if (other.accountId != null)
        return false;
    } else if (!accountId.equals(other.accountId))
      return false;
    if (dimensionHash == null) {
      if (other.dimensionHash != null)
        return false;
    } else if (!dimensionHash.equals(other.dimensionHash))
      return false;
    if (metricName == null) {
      if (other.metricName != null)
        return false;
    } else if (!metricName.equals(other.metricName))
      return false;
    if (metricType != other.metricType)
      return false;
    if (namespace == null) {
      if (other.namespace != null)
        return false;
    } else if (!namespace.equals(other.namespace))
      return false;
    if (timestamp == null) {
      if (other.timestamp != null)
        return false;
    } else if (!timestamp.equals(other.timestamp))
      return false;
    if (units != other.units)
      return false;
    return true;
  }

}


File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/metricdata/MetricDataQueue.java
/*************************************************************************
 * Copyright 2009-2014 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain.metricdata;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import javax.persistence.EntityTransaction;

import org.apache.log4j.Logger;
import org.hibernate.Criteria;
import org.hibernate.criterion.Restrictions;

import com.eucalyptus.cloudwatch.common.backend.msgs.Dimension;
import com.eucalyptus.cloudwatch.common.backend.msgs.Dimensions;
import com.eucalyptus.cloudwatch.common.backend.msgs.MetricDatum;
import com.eucalyptus.cloudwatch.common.backend.msgs.StatisticSet;
import com.eucalyptus.cloudwatch.domain.absolute.AbsoluteMetricHelper;
import com.eucalyptus.cloudwatch.domain.absolute.AbsoluteMetricHistory;
import com.eucalyptus.cloudwatch.domain.absolute.AbsoluteMetricHelper.MetricDifferenceInfo;
import com.eucalyptus.cloudwatch.domain.listmetrics.ListMetricManager;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;
import com.eucalyptus.entities.Entities;
import com.eucalyptus.records.Logs;
import com.google.common.base.Supplier;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;

public class MetricDataQueue {
  private static final Logger LOG = Logger.getLogger(MetricDataQueue.class);
  final static LinkedBlockingQueue<MetricQueueItem> dataQueue = new LinkedBlockingQueue<MetricQueueItem>();

  private static final ScheduledExecutorService dataFlushTimer = Executors
      .newSingleThreadScheduledExecutor();

  private static MetricDataQueue singleton = getInstance();

  public static MetricDataQueue getInstance() {
    synchronized (MetricDataQueue.class) {
      if (singleton == null)
        singleton = new MetricDataQueue();
    }
    return singleton;
  }

  private void queue(Supplier<MetricQueueItem> metriMetaDataSupplier) {
    final MetricQueueItem metricData = metriMetaDataSupplier.get();
    dataQueue.offer(metricData);
  }

  private static Runnable safeRunner = new Runnable() {
    @Override
    public void run() {
      long before = System.currentTimeMillis();
      try {
        List<MetricQueueItem> dataBatch = Lists.newArrayList();
        dataQueue.drainTo(dataBatch, 15000);
        LOG.debug("Timing:dataBatch.size()="+dataBatch.size());
        long t1 = System.currentTimeMillis();
        dataBatch = dealWithAbsoluteMetrics(dataBatch);
        long t2 = System.currentTimeMillis();
        LOG.debug("Timing:dataBatch.dealWithAbsoluteMetrics():time="+(t2-t1));
        List<SimpleMetricEntity> simpleDataBatch = convertToSimpleDataBatch(dataBatch);
        long t3 = System.currentTimeMillis();
        LOG.debug("Timing:dataBatch.convertToSimpleDataBatch():time="+(t3-t2));
        simpleDataBatch = aggregate(simpleDataBatch);
        long t4 = System.currentTimeMillis();
        LOG.debug("Timing:dataBatch.aggregate():time="+(t4-t3));
        MetricManager.addMetricBatch(simpleDataBatch);
        long t5 = System.currentTimeMillis();
        LOG.debug("Timing:dataBatch.MetricManager.addMetricBatch():time="+(t5-t4));
        ListMetricManager.addMetricBatch(simpleDataBatch);
        long t6 = System.currentTimeMillis();
        LOG.debug("Timing:ListMetricManager.addMetricBatch:time="+(t6-t5));
      } catch (Throwable ex) {
        LOG.debug("error");
        ex.printStackTrace();
        LOG.error(ex,ex);
      } finally {
        long after = System.currentTimeMillis();
        LOG.debug("Timing:time="+(after-before));
      }
    }
  };

  static {
    dataFlushTimer.scheduleAtFixedRate(safeRunner, 0, 1, TimeUnit.MINUTES);
  }

  public static List<SimpleMetricEntity> aggregate(List<SimpleMetricEntity> dataBatch) {
    HashMap<PutMetricDataAggregationKey, SimpleMetricEntity> aggregationMap = Maps.newHashMap();
    for (SimpleMetricEntity item: dataBatch) {
      item.setTimestamp(MetricManager.stripSeconds(item.getTimestamp()));
      PutMetricDataAggregationKey key = new PutMetricDataAggregationKey(item);
      if (!aggregationMap.containsKey(key)) {
        aggregationMap.put(key, new SimpleMetricEntity(item));
      } else {
        SimpleMetricEntity totalSoFar = aggregationMap.get(key);
        totalSoFar.setSampleMax(Math.max(item.getSampleMax(), totalSoFar.getSampleMax()));
        totalSoFar.setSampleMin(Math.min(item.getSampleMin(), totalSoFar.getSampleMin()));
        totalSoFar.setSampleSize(totalSoFar.getSampleSize() + item.getSampleSize());
        totalSoFar.setSampleSum(totalSoFar.getSampleSum() + item.getSampleSum());
      }
    }
    return Lists.newArrayList(aggregationMap.values());
  }

  protected static List<SimpleMetricEntity> convertToSimpleDataBatch(
      List<MetricQueueItem> stupidDataBatch) {
    ArrayList<SimpleMetricEntity> returnValue = new ArrayList<SimpleMetricEntity>();
    for(MetricQueueItem item: stupidDataBatch) {
      SimpleMetricEntity metricMetadata = new SimpleMetricEntity();
      metricMetadata.setAccountId(item.getAccountId());
      MetricDatum datum = item.getMetricDatum();
      
      metricMetadata.setMetricName(datum.getMetricName());
      metricMetadata.setNamespace(item.getNamespace());
      final List<Dimension> dimensions = datum.getDimensions( ) == null ?
          Collections.<Dimension>emptyList( ) :
          datum.getDimensions( ).getMember( );
      metricMetadata.setDimensionMap(makeDimensionMap(dimensions));
      metricMetadata.setMetricType(item.getMetricType());
      metricMetadata.setUnits(Units.fromValue(datum.getUnit())); 
      metricMetadata.setTimestamp(datum.getTimestamp());
      if (datum.getValue() != null) { // Either or case taken care of in service
        metricMetadata.setSampleMax(datum.getValue());
        metricMetadata.setSampleMin(datum.getValue());
        metricMetadata.setSampleSum(datum.getValue());
        metricMetadata.setSampleSize(1.0);
      } else if ((datum.getStatisticValues() != null) &&
            (datum.getStatisticValues().getMaximum() != null) &&
            (datum.getStatisticValues().getMinimum() != null) &&
            (datum.getStatisticValues().getSum() != null) &&
            (datum.getStatisticValues().getSampleCount() != null)) {
          metricMetadata.setSampleMax(datum.getStatisticValues().getMaximum());
          metricMetadata.setSampleMin(datum.getStatisticValues().getMinimum());
          metricMetadata.setSampleSum(datum.getStatisticValues().getSum());
          metricMetadata.setSampleSize(datum.getStatisticValues().getSampleCount());
      } else {
        throw new RuntimeException("Statistics set (all values) or Value must be set"); 
      }
      returnValue.add(metricMetadata);
    }
    return returnValue;
  }

  protected static List<MetricQueueItem> dealWithAbsoluteMetrics(
      List<MetricQueueItem> dataBatch) {
    List<MetricQueueItem> dataToInsert = new ArrayList<MetricQueueItem>(); 
    EntityTransaction db = Entities.get(AbsoluteMetricHistory.class);
    try {
      AbsoluteMetricCache cache = new AbsoluteMetricCache(db);
      // Some points do not actually go in.  If a data point represents an absolute value, the first one does not go in.
      // Also, some data points are added while we go through the list (derived metrics)

      for (final MetricQueueItem item : dataBatch) {
        String accountId = item.getAccountId();
        String nameSpace = item.getNamespace();
        MetricDatum datum = item.getMetricDatum();
        MetricType metricType = item.getMetricType();
        // Deal with the absolute metrics
        // CPUUtilization
        // VolumeReadOps
        // VolumeWriteOps
        // VolumeConsumedReadWriteOps
        // VolumeReadBytes
        // VolumeWriteBytes
        // VolumeTotalReadTime
        // VolumeTotalWriteTime
        // VolumeTotalReadWriteTime (used to calculate VolumeIdleTime)
        // DiskReadOps
        // DiskWriteOps
        // DiskReadBytes
        // DiskWriteBytes
        // NetworkIn 
        // NetworkOut

        if ("AWS/EBS".equals(nameSpace) && metricType == MetricType.System) {
          String volumeId = null;
          if ((datum.getDimensions() != null) && (datum.getDimensions().getMember() != null)) {
            for (Dimension dimension: datum.getDimensions().getMember()) {
              if ("VolumeId".equals(dimension.getName())) {
                volumeId = dimension.getValue();
                cache.load(nameSpace, "VolumeId", volumeId);
              }
            }
          }
          if (EBS_ABSOLUTE_METRICS.containsKey(datum.getMetricName())) {
            // we check if the point below is a 'first' point, or maybe a point in the past.  Either case reject it.
            if (!adjustAbsoluteVolumeStatisticSet(cache, datum, datum.getMetricName(), EBS_ABSOLUTE_METRICS.get(datum.getMetricName()), volumeId)) continue; 
          }
          // special cases
          // 1) VolumeThroughputPercentage -- this is 100% for provisioned volumes, and we need to insert a
          //                                  data point for every timestamp that a volume event occurs.
          //                                  To make sure we don't duplicate the effort, we choose one event at random, VolumeReadOps,
          //                                  and create this new metric arbitrarily
          if ("VolumeReadOps".equals(datum.getMetricName())) { // special case
            dataToInsert.add(createVolumeThroughputMetric(accountId, nameSpace, metricType, datum));
          }
          // 2) VolumeIdleTime -- we piggy back off of the metric we don't need VolumeTotalReadWriteTime, and convert it to VolumeIdleTime
          if ("VolumeTotalReadWriteTime".equals(datum.getMetricName())) {
            convertVolumeTotalReadWriteTimeToVolumeIdleTime(datum);
          }
          // 3) VolumeQueueLength -- this one comes in essentially correct, but we don't have a time duration for it, so we piggy back off
          //                         the absolute metric framework
          if ("VolumeQueueLength".equals(datum.getMetricName())) {
            if (!adjustAbsoluteVolumeQueueLengthStatisticSet(cache, datum, volumeId)) continue;
          }
        }
        
        if ("AWS/EC2".equals(nameSpace) && metricType == MetricType.System) {
          String instanceId = null;
          if ((datum.getDimensions() != null) && (datum.getDimensions().getMember() != null)) {
            for (Dimension dimension: datum.getDimensions().getMember()) {
              if ("InstanceId".equals(dimension.getName())) {
                instanceId = dimension.getValue();
                cache.load(nameSpace, "InstanceId", instanceId);
              }
            }
          }
          if (EC2_ABSOLUTE_METRICS.containsKey(datum.getMetricName())) {
            if (!adjustAbsoluteInstanceStatisticSet(cache, datum, datum.getMetricName(), EC2_ABSOLUTE_METRICS.get(datum.getMetricName()), instanceId)) continue; 
          } else if ("CPUUtilizationMSAbsolute".equals(datum.getMetricName())) { // special case
            // we check if the point below is a 'first' point, or maybe a point in the past.  Either case reject it.
            if (!adjustAbsoluteInstanceCPUStatisticSet(cache, datum, "CPUUtilizationMSAbsolute", "CPUUtilization", instanceId)) continue;
          } 
        }        
        dataToInsert.add(item); // this data point is ok
      }
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
    return dataToInsert;
  }

  private static final Map<String, String> EBS_ABSOLUTE_METRICS = 
      new ImmutableMap.Builder<String, String>()
      .put("VolumeReadOpsAbsolute", "VolumeReadOps")
      .put("VolumeWriteOpsAbsolute", "VolumeWriteOps")
      .put("VolumeReadBytesAbsolute", "VolumeReadBytes")
      .put("VolumeWriteBytesAbsolute", "VolumeWriteBytes")
      .put("VolumeConsumedReadWriteOpsAbsolute", "VolumeConsumedReadWriteOps")
      .put("VolumeTotalReadTimeAbsolute", "VolumeTotalReadTime")
      .put("VolumeTotalWriteTimeAbsolute", "VolumeTotalWriteTime")
      .put("VolumeTotalReadWriteTimeAbsolute", "VolumeTotalReadWriteTime")
      .build();

  private static final Map<String, String> EC2_ABSOLUTE_METRICS = 
      new ImmutableMap.Builder<String, String>()
      .put("DiskReadOpsAbsolute", "DiskReadOps")
      .put("DiskWriteOpsAbsolute", "DiskWriteOps")
      .put("DiskReadBytesAbsolute", "DiskReadBytes")
      .put("DiskWriteBytesAbsolute", "DiskWriteBytes")
      .put("NetworkInAbsolute", "NetworkIn") 
      .put("NetworkOutAbsolute", "NetworkOut") 
      .build();

  public void insertMetricData(final String ownerAccountId, final String nameSpace,
      final List<MetricDatum> metricDatum, final MetricType metricType) {
    // Some points do not actually go in.  If a data point represents an absolute value, the first one does not go in.
    // Also, some data points are added while we go through the list (derived metrics)
    Date now = new Date();

    for (final MetricDatum datum : metricDatum) {
      scrub(datum, now);
      queue(new Supplier<MetricQueueItem>() {
        @Override
        public MetricQueueItem get() {
          MetricQueueItem metricMetadata = new MetricQueueItem();
          metricMetadata.setAccountId(ownerAccountId);
          metricMetadata.setMetricDatum(datum);
          metricMetadata.setNamespace(nameSpace);
          metricMetadata.setMetricType(metricType);
          return metricMetadata;
        }
      });
    }
  }

  private static boolean adjustAbsoluteVolumeQueueLengthStatisticSet(AbsoluteMetricCache cache,
      MetricDatum datum, String volumeId) {
    // the metric value is correct, we just need a statistic set with the sample count.
    // to get this we create a placeholder absolute metric, value always 0, just to get time duration/sample count
    MetricDatum absolutePlaceHolder = new MetricDatum();
    absolutePlaceHolder.setMetricName("VolumeQueueLengthPlaceHolderAbsolute");
    absolutePlaceHolder.setValue(0.0);
    absolutePlaceHolder.setTimestamp(datum.getTimestamp());
    if (!adjustAbsoluteVolumeStatisticSet(cache, absolutePlaceHolder, absolutePlaceHolder.getMetricName(), "VolumeQueueLengthPlaceHolder", volumeId)) return false;
    // otherwise, we have a duration/sample count
    double sampleCount = absolutePlaceHolder.getStatisticValues().getSampleCount();
    double value = datum.getValue();
    datum.setValue(null);
    StatisticSet statisticSet = new StatisticSet();
    statisticSet.setMaximum(value);
    statisticSet.setMinimum(value);
    statisticSet.setSum(value * sampleCount);
    statisticSet.setSampleCount(sampleCount);
    datum.setStatisticValues(statisticSet);
    return true;
  }

  private static void convertVolumeTotalReadWriteTimeToVolumeIdleTime(final MetricDatum datum) {
    // we convert this to VolumeIdleTime = Period Length - VolumeTotalReadWriteTime on the period (though won't be negative)
    datum.setMetricName("VolumeIdleTime");
    double totalReadWriteTime = datum.getStatisticValues().getSum(); // value is in seconds
    double totalPeriodTime = 60.0 * datum.getStatisticValues().getSampleCount();
    double totalIdleTime = totalPeriodTime - totalReadWriteTime;
    if (totalIdleTime < 0) totalIdleTime = 0; // if we have read and written more than in the period, don't go negative
    datum.getStatisticValues().setSum(totalIdleTime);
    double averageIdleTime = totalIdleTime / datum.getStatisticValues().getSampleCount();
    datum.getStatisticValues().setMaximum(averageIdleTime);
    datum.getStatisticValues().setMinimum(averageIdleTime);
  }

  private static MetricQueueItem createVolumeThroughputMetric(String accountId, String nameSpace, MetricType metricType, MetricDatum datum) {
    // add volume throughput percentage.  (The guess is that there will be a set of volume metrics.  
    // Attach it to one so it will be sent as many times as the others.
    // add one
    MetricDatum vtpDatum = new MetricDatum();
    vtpDatum.setMetricName("VolumeThroughputPercentage");
    vtpDatum.setTimestamp(datum.getTimestamp());
    vtpDatum.setUnit(Units.Percent.toString());
    // should be 100% but weigh it the same
    if (datum.getValue() != null) {
      vtpDatum.setValue(100.0); // Any time we have a volume data, this value is 100%
    } else if (datum.getStatisticValues() != null) {
      StatisticSet statisticSet = new StatisticSet();
      statisticSet.setMaximum(100.0);
      statisticSet.setMinimum(100.0);
      statisticSet.setSum(100.0 * datum.getStatisticValues().getSampleCount());
      statisticSet.setSampleCount(datum.getStatisticValues().getSampleCount());
      vtpDatum.setStatisticValues(statisticSet);
    }
    // use the same dimensions as current metric
    Dimensions vtpDimensions = new Dimensions();
    ArrayList<Dimension> vtpDimensionsMember = new ArrayList<Dimension>();
    if ( datum.getDimensions( ) != null ) for ( final Dimension dimension: datum.getDimensions( ).getMember( ) ) {
      Dimension vtpDimension = new Dimension();
      vtpDimension.setName(dimension.getName());
      vtpDimension.setValue(dimension.getValue());
      vtpDimensionsMember.add(vtpDimension);
    }
    vtpDimensions.setMember(vtpDimensionsMember);
    vtpDatum.setDimensions(vtpDimensions);
    MetricQueueItem vtpQueueItem = new MetricQueueItem();
    vtpQueueItem.setAccountId(accountId);
    vtpQueueItem.setMetricType(metricType);
    vtpQueueItem.setNamespace(nameSpace);
    vtpQueueItem.setMetricDatum(vtpDatum);
    return vtpQueueItem;
  }

  private static boolean adjustAbsoluteInstanceCPUStatisticSet(AbsoluteMetricCache cache, MetricDatum datum, String absoluteMetricName,
      String relativeMetricName, String instanceId) {
    MetricDifferenceInfo info = AbsoluteMetricHelper.calculateDifferenceSinceLastEvent(cache, "AWS/EC2", absoluteMetricName, "InstanceId", instanceId, datum.getTimestamp(), datum.getValue());
    if (info != null) {
      // calculate percentage
      double percentage = 0.0;
      if (info.getElapsedTimeInMillis() != 0) {
        // don't want to divide by 0
        percentage = 100.0 * (info.getValueDifference() / info.getElapsedTimeInMillis());
      }
      datum.setMetricName(relativeMetricName);
      datum.setValue(null);
      StatisticSet statisticSet = new StatisticSet();
      statisticSet.setMaximum(percentage);
      statisticSet.setMinimum(percentage);
      double sampleCount = (double) info.getElapsedTimeInMillis() / 60000.0; // number of minutes (this weights the value)
      statisticSet.setSum(sampleCount * percentage);
      statisticSet.setSampleCount(sampleCount);
      datum.setStatisticValues(statisticSet);
      datum.setUnit(Units.Percent.toString());
      return true; //don't continue;
    }
    return false; // continue
  }

  private static boolean adjustAbsoluteInstanceStatisticSet(AbsoluteMetricCache cache, MetricDatum datum, String absoluteMetricName,
      String relativeMetricName, String instanceId) {
    if (instanceId == null) return false;
    MetricDifferenceInfo info = AbsoluteMetricHelper.calculateDifferenceSinceLastEvent(cache, "AWS/EC2", absoluteMetricName, "InstanceId", instanceId, datum.getTimestamp(), datum.getValue());
    if (info != null) {
      datum.setMetricName(relativeMetricName);
      // we need to weigh this data based on the time.  use a statistic set instead of the value
      datum.setValue(null);
      StatisticSet statisticSet = new StatisticSet();
      double sampleCount = (double) info.getElapsedTimeInMillis() / 60000.0; // number of minutes (this weights the value)
      statisticSet.setSum(info.getValueDifference());
      statisticSet.setMaximum(info.getValueDifference() / sampleCount);
      statisticSet.setMinimum(info.getValueDifference() / sampleCount);
      statisticSet.setSampleCount(sampleCount);
      datum.setStatisticValues(statisticSet);
      return true; //don't continue;
    }
    return false; // continue
  }

  
  private static boolean adjustAbsoluteVolumeStatisticSet(AbsoluteMetricCache cache, MetricDatum datum,
      String absoluteMetricName, String relativeMetricName, String volumeId) {
    if (volumeId == null) return false;
    MetricDifferenceInfo info = AbsoluteMetricHelper.calculateDifferenceSinceLastEvent(cache, "AWS/EBS", absoluteMetricName, "VolumeId", volumeId, datum.getTimestamp(), datum.getValue());
    if (info != null) {
      datum.setMetricName(relativeMetricName);
      // we need to weigh this data based on the time.  use a statistic set instead of the value
      datum.setValue(null);
      StatisticSet statisticSet = new StatisticSet();
      double sampleCount = (double) info.getElapsedTimeInMillis() / 60000.0; // number of minutes (this weights the value)
      statisticSet.setSum(info.getValueDifference());
      statisticSet.setMaximum(info.getValueDifference() / sampleCount);
      statisticSet.setMinimum(info.getValueDifference() / sampleCount);
      statisticSet.setSampleCount(sampleCount);
      datum.setStatisticValues(statisticSet);
      return true; //don't continue;
    }
    return false; // continue
  }

  private void scrub(MetricDatum datum, Date now) {
    if (datum.getUnit() == null || datum.getUnit().trim().isEmpty()) datum.setUnit(Units.None.toString());
    if (datum.getTimestamp() == null) datum.setTimestamp(now);
  }

  private static Map<String, String> makeDimensionMap(
      final List<Dimension> dimensions
  ) {
    Map<String,String> returnValue = Maps.newTreeMap();
    for (Dimension dimension: dimensions) {
      returnValue.put(dimension.getName(), dimension.getValue());
    }
    return returnValue;
  }

  public static class AbsoluteMetricCache {
    private EntityTransaction db;
    private Set<AbsoluteMetricLoadCacheKey> loaded = Sets.newHashSet();
    private Map<AbsoluteMetricCacheKey, AbsoluteMetricHistory> cacheMap = Maps.newHashMap();
    public AbsoluteMetricCache(EntityTransaction db) {
      this.db = db;
    }

    public void load(String namespace, String dimensionName, String dimensionValue) {
      AbsoluteMetricLoadCacheKey loadKey = new AbsoluteMetricLoadCacheKey(namespace, dimensionName);
      if (!loaded.contains(loadKey)) {
        Criteria criteria = Entities.createCriteria(AbsoluteMetricHistory.class)
            .add( Restrictions.eq( "namespace", namespace ) )
            .add( Restrictions.eq( "dimensionName", dimensionName ) );
//            .add( Restrictions.eq( "dimensionValue", dimensionValue ) );
        List<AbsoluteMetricHistory> list = (List<AbsoluteMetricHistory>) criteria.list();
        for (AbsoluteMetricHistory item: list) {
          cacheMap.put(new AbsoluteMetricCacheKey(item), item);
        }
        loaded.add(loadKey);
      }
    }

    public AbsoluteMetricHistory lookup(String namespace, String metricName,
        String dimensionName, String dimensionValue) {
      return cacheMap.get(new AbsoluteMetricCacheKey(namespace, metricName, dimensionName, dimensionValue));
    }

    public void put(String namespace, String metricName, String dimensionName,
        String dimensionValue, AbsoluteMetricHistory lastEntity) {
      cacheMap.put(new AbsoluteMetricCacheKey(namespace, metricName, dimensionName, dimensionValue), lastEntity);
    }
    
  }
  public static class AbsoluteMetricLoadCacheKey {
    private String namespace;
    private String dimensionName;

    public String getNamespace() {
      return namespace;
    }
    public void setNamespace(String namespace) {
      this.namespace = namespace;
    }
    public String getDimensionName() {
      return dimensionName;
    }
    public void setDimensionName(String dimensionName) {
      this.dimensionName = dimensionName;
    }
    private AbsoluteMetricLoadCacheKey(String namespace, String dimensionName) {
      super();
      this.namespace = namespace;
      this.dimensionName = dimensionName;
    }
    @Override
    public int hashCode() {
      final int prime = 31;
      int result = 1;
      result = prime * result
          + ((dimensionName == null) ? 0 : dimensionName.hashCode());
      result = prime * result
          + ((namespace == null) ? 0 : namespace.hashCode());
      return result;
    }
    @Override
    public boolean equals(Object obj) {
      if (this == obj)
        return true;
      if (obj == null)
        return false;
      if (getClass() != obj.getClass())
        return false;
      AbsoluteMetricLoadCacheKey other = (AbsoluteMetricLoadCacheKey) obj;
      if (dimensionName == null) {
        if (other.dimensionName != null)
          return false;
      } else if (!dimensionName.equals(other.dimensionName))
        return false;
      if (namespace == null) {
        if (other.namespace != null)
          return false;
      } else if (!namespace.equals(other.namespace))
        return false;
      return true;
    }
    
  }
  public static class AbsoluteMetricCacheKey {
    private String namespace;
    private String metricName;
    private String dimensionName;
    private String dimensionValue;
    public String getNamespace() {
      return namespace;
    }
    public void setNamespace(String namespace) {
      this.namespace = namespace;
    }
    public String getMetricName() {
      return metricName;
    }
    public void setMetricName(String metricName) {
      this.metricName = metricName;
    }
    public String getDimensionName() {
      return dimensionName;
    }
    public void setDimensionName(String dimensionName) {
      this.dimensionName = dimensionName;
    }
    public String getDimensionValue() {
      return dimensionValue;
    }
    public void setDimensionValue(String dimensionValue) {
      this.dimensionValue = dimensionValue;
    }
    public AbsoluteMetricCacheKey(String namespace, String metricName,
        String dimensionName, String dimensionValue) {
      super();
      this.namespace = namespace;
      this.metricName = metricName;
      this.dimensionName = dimensionName;
      this.dimensionValue = dimensionValue;
    }
    public AbsoluteMetricCacheKey(AbsoluteMetricHistory item) {
      super();
      this.namespace = item.getNamespace();
      this.metricName = item.getMetricName();
      this.dimensionName = item.getDimensionName();
      this.dimensionValue = item.getDimensionValue();
    }
    @Override
    public int hashCode() {
      final int prime = 31;
      int result = 1;
      result = prime * result
          + ((dimensionName == null) ? 0 : dimensionName.hashCode());
      result = prime * result
          + ((dimensionValue == null) ? 0 : dimensionValue.hashCode());
      result = prime * result
          + ((metricName == null) ? 0 : metricName.hashCode());
      result = prime * result
          + ((namespace == null) ? 0 : namespace.hashCode());
      return result;
    }
    @Override
    public boolean equals(Object obj) {
      if (this == obj)
        return true;
      if (obj == null)
        return false;
      if (getClass() != obj.getClass())
        return false;
      AbsoluteMetricCacheKey other = (AbsoluteMetricCacheKey) obj;
      if (dimensionName == null) {
        if (other.dimensionName != null)
          return false;
      } else if (!dimensionName.equals(other.dimensionName))
        return false;
      if (dimensionValue == null) {
        if (other.dimensionValue != null)
          return false;
      } else if (!dimensionValue.equals(other.dimensionValue))
        return false;
      if (metricName == null) {
        if (other.metricName != null)
          return false;
      } else if (!metricName.equals(other.metricName))
        return false;
      if (namespace == null) {
        if (other.namespace != null)
          return false;
      } else if (!namespace.equals(other.namespace))
        return false;
      return true;
    }
  }
  
}


File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/metricdata/MetricEntity.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain.metricdata;

import java.util.Date;

import javax.persistence.Column;
import javax.persistence.EnumType;
import javax.persistence.Enumerated;
import javax.persistence.MappedSuperclass;

import com.eucalyptus.cloudwatch.domain.AbstractPersistentWithDimensions;

@MappedSuperclass
public abstract class MetricEntity extends AbstractPersistentWithDimensions {

  @Column(name = "account_id", nullable = false)
  private String accountId;
  @Column(name = "namespace", nullable = false)
  private String namespace;
  @Column(name = "metric_name", nullable = false)
  private String metricName;
  @Column(name = "dimension_hash", nullable = false)
  private String dimensionHash;
  @Column(name = "units", nullable = false)
  @Enumerated(EnumType.STRING)
  private Units units;
  @Column(name = "metric_type", nullable = false)
  @Enumerated(EnumType.STRING)
  private MetricType metricType;
  @Column(name = "timestamp", nullable = false)
  private Date timestamp;
  @Column(name = "sample_size", nullable = false)
  private Double sampleSize;
  @Column(name = "sample_max", nullable = false)
  private Double sampleMax;
  @Column(name = "sample_min", nullable = false)
  private Double sampleMin;
  @Column(name = "sample_sum", nullable = false)
  private Double sampleSum;

  public enum MetricType {
    Custom, System
  }

  public enum Units {
    Seconds, 
    Microseconds, 
    Milliseconds, 
    Bytes, 
    Kilobytes, 
    Megabytes, 
    Gigabytes, 
    Terabytes, 
    Bits,
    Kilobits, 
    Megabits, 
    Gigabits, 
    Terabits, 
    Percent, 
    Count, 
    BytesPerSecond("Bytes/Second"), 
    KilobytesPerSecond("Kilobytes/Second"), 
    MegabytesPerSecond("Megabytes/Second"), 
    GigabytesPerSecond("Gigabytes/Second"), 
    TerabytesPerSecond("Terabytes/Second"), 
    BitsPerSecond("Bits/Second"),
    KilobitsPerSecond("Kilobits/Second"), 
    MegabitsPerSecond("Megabits/Second"), 
    GigabitsPerSecond("Gigabits/Second"), 
    TerabitsPerSecond("Terabits/Second"), 
    CountPerSecond("Count/Second"), 
    None("None");
    private String value;

    Units() {
      this.value = name();
    }

    Units(String value) {
      this.value = value;
    }

    @Override
    public String toString() {
      return value;
    }

    public static Units fromValue(String value) {
      for (Units units: values()) {
        if (units.value.equals(value)) {
          return units;
        }
      }
      throw new IllegalArgumentException("Unknown unit " + value);
    }
  }

  public String getAccountId() {
    return accountId;
  }
  

  public void setAccountId(String accountId) {
    this.accountId = accountId;
  }

  public String getNamespace() {
    return namespace;
  }

  public void setNamespace(String namespace) {
    this.namespace = namespace;
  }

  public String getMetricName() {
    return metricName;
  }

  public void setMetricName(String metricName) {
    this.metricName = metricName;
  }

  public String getDimensionHash() {
    return dimensionHash;
  }

  public void setDimensionHash(String dimensionHash) {
    this.dimensionHash = dimensionHash;
  }

  public Units getUnits() {
    return units;
  }

  public void setUnits(Units units) {
    this.units = units;
  }

  public MetricType getMetricType() {
    return metricType;
  }

  public void setMetricType(MetricType metricType) {
    this.metricType = metricType;
  }

  public Date getTimestamp() {
    return timestamp;
  }

  public void setTimestamp(Date timestamp) {
    this.timestamp = MetricManager.stripSeconds(timestamp);
  }

  public Double getSampleSize() {
    return sampleSize;
  }

  public void setSampleSize(Double sampleSize) {
    this.sampleSize = sampleSize;
  }

  public Double getSampleMax() {
    return sampleMax;
  }

  public void setSampleMax(Double sampleMax) {
    this.sampleMax = sampleMax;
  }

  public Double getSampleMin() {
    return sampleMin;
  }

  public void setSampleMin(Double sampleMin) {
    this.sampleMin = sampleMin;
  }

  public Double getSampleSum() {
    return sampleSum;
  }

  public void setSampleSum(Double sampleSum) {
    this.sampleSum = sampleSum;
  }

  @Override
  public String toString() {
    return "MetricEntity [accountId=" + accountId 
        + ", namespace=" + namespace + ", metricName=" + metricName
        + ", dimensionHash=" + dimensionHash + ", units=" + units
        + ", metricType=" + metricType + ", timestamp=" + timestamp
        + ", sampleSize=" + sampleSize + ", sampleMax=" + sampleMax
        + ", sampleMin=" + sampleMin + ", sampleSum=" + sampleSum
        + ", getDimensions()=" + getDimensions() + "]";
  }
}


File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/metricdata/MetricManager.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain.metricdata;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

import javax.persistence.Column;
import javax.persistence.EntityTransaction;
import javax.persistence.EnumType;
import javax.persistence.Enumerated;

import org.apache.log4j.Logger;
import org.hibernate.Criteria;
import org.hibernate.criterion.Order;
import org.hibernate.criterion.Restrictions;

import com.eucalyptus.cloudwatch.domain.DimensionEntity;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;
import com.eucalyptus.cloudwatch.hashing.HashUtils;
import com.eucalyptus.entities.Entities;
import com.eucalyptus.records.Logs;
import com.google.common.collect.ArrayListMultimap;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Multimap;
import com.google.common.collect.Sets;

public class MetricManager {
	public static final Logger LOG = Logger.getLogger(MetricManager.class);
  public static void addMetric(String accountId, 
      String metricName, String namespace, Map<String, String> dimensionMap,
      MetricType metricType, Units units, Date timestamp, Double sampleSize,
      Double sampleMax, Double sampleMin, Double sampleSum) {
    SimpleMetricEntity simpleMetricEntity = new SimpleMetricEntity();
    simpleMetricEntity.setAccountId(accountId);
    simpleMetricEntity.setDimensionMap(dimensionMap);
    simpleMetricEntity.setMetricName(metricName);
    simpleMetricEntity.setMetricType(metricType);
    simpleMetricEntity.setNamespace(namespace);
    simpleMetricEntity.setSampleMax(sampleMax);
    simpleMetricEntity.setSampleMin(sampleMin);
    simpleMetricEntity.setSampleSize(sampleSize);
    simpleMetricEntity.setSampleSum(sampleSum);
    simpleMetricEntity.setTimestamp(timestamp);
    simpleMetricEntity.setUnits(units);
    validateMetricQueueItem(simpleMetricEntity);
    addManyMetrics(makeMetricMap(foldAndHash(simpleMetricEntity)));
  }
  
  private static Multimap<Class, MetricEntity> makeMetricMap(Collection<MetricEntity> entities) {
    Multimap<Class, MetricEntity> metricMap = ArrayListMultimap
        .<Class, MetricEntity> create();
    for (MetricEntity entity:entities) {
      metricMap
          .put(MetricEntityFactory.getClassForEntitiesGet(entity.getMetricType(),
              entity.getDimensionHash()), entity);
    }
    return metricMap;
  }
  

  private static List<MetricEntity> foldAndHash(SimpleMetricEntity simpleMetricEntity) {
    if (simpleMetricEntity == null) return new ArrayList<MetricEntity>();
    TreeSet<DimensionEntity> dimensions = new TreeSet<DimensionEntity>();
    for (Map.Entry<String, String> entry : simpleMetricEntity.getDimensionMap().entrySet()) {
      DimensionEntity d = new DimensionEntity();
      d.setName(entry.getKey());
      d.setValue(entry.getValue());
      dimensions.add(d);
    }
    Set<Set<DimensionEntity>> permutations = null;
    if (simpleMetricEntity.getMetricType() == MetricType.System) {
      permutations = Sets.powerSet(dimensions);
    } else {
      permutations = Sets.newHashSet();
      permutations.add(dimensions);
    }
    ArrayList<MetricEntity> returnValue = new ArrayList<MetricEntity>();
    for (Set<DimensionEntity> dimensionsPermutation : permutations) {
      String dimensionHash = hash(dimensionsPermutation);
      MetricEntity metric = MetricEntityFactory.getNewMetricEntity(simpleMetricEntity.getMetricType(),
          dimensionHash);
      metric.setAccountId(simpleMetricEntity.getAccountId());
      metric.setMetricName(simpleMetricEntity.getMetricName());
      metric.setNamespace(simpleMetricEntity.getNamespace());
      metric.setDimensions(dimensions);// arguable, but has complete list
      metric.setDimensionHash(dimensionHash);
      metric.setMetricType(simpleMetricEntity.getMetricType());
      metric.setUnits(simpleMetricEntity.getUnits());
      metric.setTimestamp(simpleMetricEntity.getTimestamp());
      metric.setSampleMax(simpleMetricEntity.getSampleMax());
      metric.setSampleMin(simpleMetricEntity.getSampleMin());
      metric.setSampleSum(simpleMetricEntity.getSampleSum());
      metric.setSampleSize(simpleMetricEntity.getSampleSize());
      returnValue.add(metric);
    }
    return returnValue;
  }

  private static void addManyMetrics(Multimap<Class, MetricEntity> metricMap) {
    for (Class c : metricMap.keySet()) {
      EntityTransaction db = Entities.get(c);
      try {
        for (MetricEntity me : metricMap.get(c)) {
          Entities.persist(me);
        }
        db.commit();
      } catch (RuntimeException ex) {
        Logs.extreme().error(ex, ex);
        throw ex;
      } finally {
        if (db.isActive())
          db.rollback();
      }
    }
  }

  public static String hash(Map<String, String> dimensionMap) {
    TreeMap<String, String> sortedDimensionMap = Maps.newTreeMap();
    if (dimensionMap != null) {
      sortedDimensionMap.putAll(dimensionMap);
    }
    StringBuilder sb = new StringBuilder();
    for (Map.Entry<String, String> entry : sortedDimensionMap.entrySet()) {
      sb.append(entry.getKey() + "|" + entry.getValue() + "|");
    }
    return HashUtils.hash(sb);
  }

  public static String hash(Collection<DimensionEntity> dimensions) {
    StringBuilder sb = new StringBuilder();
    for (DimensionEntity dimension : dimensions) {
      sb.append(dimension.getName() + "|" + dimension.getValue() + "|");
    }
    return HashUtils.hash(sb);
  }

  public static Date stripSeconds(Date timestamp) {
    if (timestamp == null)
      return timestamp;
    long time = timestamp.getTime();
    time = time - time % 60000L;
    return new Date(time);
  }

  public static void deleteAllMetrics() {
    for (Class c : MetricEntityFactory.getAllClassesForEntitiesGet()) {
      EntityTransaction db = Entities.get(c);
      try {
        Entities.deleteAll(c);
        db.commit();
      } catch (RuntimeException ex) {
        Logs.extreme().error(ex, ex);
        throw ex;
      } finally {
        if (db.isActive())
          db.rollback();
      }
    }
  }

  /**
   * Delete all metrics before a certain date
   * 
   * @param before
   *          the date to delete before (inclusive)
   */
  public static void deleteMetrics(Date before) {
    for (Class c : MetricEntityFactory.getAllClassesForEntitiesGet()) {
      EntityTransaction db = Entities.get(c);
      try {
        Map<String, Date> criteria = new HashMap<String, Date>();
        criteria.put("before", before);
        Entities.deleteAllMatching(c, "WHERE timestamp < :before", criteria);
        db.commit();
      } catch (RuntimeException ex) {
        Logs.extreme().error(ex, ex);
        throw ex;
      } finally {
        if (db.isActive())
          db.rollback();
      }
    }
  }


  public static Collection<MetricStatistics> getMetricStatistics(String accountId, 
      String metricName, String namespace, Map<String, String> dimensionMap,
      MetricType metricType, Units units, Date startTime, Date endTime, Integer period) {
    if (dimensionMap == null) {
      dimensionMap = new HashMap<String, String>();
    } else if (dimensionMap.size() > MetricEntity.MAX_DIM_NUM) {
      throw new IllegalArgumentException("Too many dimensions for metric, "
          + dimensionMap.size());
    }
    TreeSet<DimensionEntity> dimensions = new TreeSet<DimensionEntity>();
    for (Map.Entry<String, String> entry : dimensionMap.entrySet()) {
      DimensionEntity d = new DimensionEntity();
      d.setName(entry.getKey());
      d.setValue(entry.getValue());
      dimensions.add(d);
    }
    Date now = new Date();
    if (endTime == null) endTime = now;
    if (startTime == null) startTime = new Date(now.getTime() - 60 * 60 * 1000L);
    startTime = stripSeconds(startTime);
    endTime = stripSeconds(endTime);
    if (startTime.after(endTime)) {
      throw new IllegalArgumentException("Start time must be after end time");
    }
    if (period == null) {
      period = 60;
    }
    if (period % 60 != 0) {
      throw new IllegalArgumentException("Period must be a multiple of 60");
    }
    if (period < 0) {
      throw new IllegalArgumentException("Period must be greater than 0");
    }
    if (period == 0) {
      throw new IllegalArgumentException("Period must not equal 0");
    }
    if (metricType == null) {
      throw new IllegalArgumentException("metricType must not be null");
    }
    if (accountId == null) {
      throw new IllegalArgumentException("accountId must not be null");
    }
    if (metricName == null) {
      throw new IllegalArgumentException("metricName must not be null");
    }
    if (namespace == null) {
      throw new IllegalArgumentException("namespace must not be null");
    }
    String hash = hash(dimensions);
    Class metricEntityClass = MetricEntityFactory.getClassForEntitiesGet(metricType, hash);
    Map<GetMetricStatisticsAggregationKey, MetricStatistics> aggregationMap = new TreeMap<GetMetricStatisticsAggregationKey, MetricStatistics>(GetMetricStatisticsAggregationKey.COMPARATOR_WITH_NULLS.INSTANCE);
    EntityTransaction db = Entities.get(metricEntityClass);
    try {
      Criteria criteria = Entities.createCriteria(metricEntityClass);
      criteria = criteria.add(Restrictions.eq("accountId", accountId));
      criteria = criteria.add(Restrictions.eq("metricName", metricName));
      criteria = criteria.add(Restrictions.eq("namespace", namespace));
      criteria = criteria.add(Restrictions.lt("timestamp", endTime));
      criteria = criteria.add(Restrictions.ge("timestamp", startTime));
      criteria = criteria.add(Restrictions.eq("dimensionHash", hash));
      if (units != null) {
        criteria = criteria.add(Restrictions.eq("units", units));
      }
      criteria = criteria.addOrder( Order.asc("creationTimestamp") );
      criteria = criteria.addOrder( Order.asc("naturalId") );
      Collection results = criteria.list();
      for (Object o: results) {
        MetricEntity me = (MetricEntity) o;
        // Note: dimensions from metric entity are the actual dimensions for the point.  dimensions passed in are from the
        // hash (used for aggregation).  The hash dimensions are what we want.
        GetMetricStatisticsAggregationKey key = new GetMetricStatisticsAggregationKey(me, startTime, period, hash);
        MetricStatistics item = new MetricStatistics(me, startTime, period, dimensions);
        if (!aggregationMap.containsKey(key)) {
          aggregationMap.put(key, item);
        } else {
          MetricStatistics totalSoFar = aggregationMap.get(key);
          totalSoFar.setSampleMax(Math.max(item.getSampleMax(), totalSoFar.getSampleMax()));
          totalSoFar.setSampleMin(Math.min(item.getSampleMin(), totalSoFar.getSampleMin()));
          totalSoFar.setSampleSize(totalSoFar.getSampleSize() + item.getSampleSize());
          totalSoFar.setSampleSum(totalSoFar.getSampleSum() + item.getSampleSum());
        }
      }
      db.commit();
    } catch (RuntimeException ex) {
      Logs.extreme().error(ex, ex);
      throw ex;
    } finally {
      if (db.isActive())
        db.rollback();
    }
    return Lists.newArrayList(aggregationMap.values());
  }    

  public static Date getPeriodStart(Date originalTimestamp, Date startTime, Integer period) {
    long difference = originalTimestamp.getTime() - startTime.getTime();
    long remainderInOnePeriod = difference % (1000L * period);
    return new Date(originalTimestamp.getTime() - remainderInOnePeriod);
  }

  public static Collection<MetricEntity> getAllMetrics() {
    ArrayList<MetricEntity> allResults = new ArrayList<MetricEntity>();
    for (Class c : MetricEntityFactory.getAllClassesForEntitiesGet()) {
      EntityTransaction db = Entities.get(c);
      try {
        Criteria criteria = Entities.createCriteria(c);
        criteria = criteria.addOrder( Order.asc("creationTimestamp") );
        criteria = criteria.addOrder( Order.asc("naturalId") );
        Collection dbResults = criteria.list();
        for (Object result : dbResults) {
          allResults.add((MetricEntity) result);
        }
        db.commit();
      } catch (RuntimeException ex) {
        Logs.extreme().error(ex, ex);
        throw ex;
      } finally {
        if (db.isActive())
          db.rollback();
      }
    }
    return allResults;
  }

  public static void addMetricBatch(List<SimpleMetricEntity> dataBatch) {
    ArrayList<MetricEntity> metricEntities = new ArrayList<MetricEntity>();
    for (SimpleMetricEntity simpleMetricEntity: dataBatch) {
      validateMetricQueueItem(simpleMetricEntity);
      metricEntities.addAll(foldAndHash(simpleMetricEntity));
    }
    addManyMetrics(makeMetricMap(metricEntities));
  }

  private static void validateMetricQueueItem(SimpleMetricEntity simpleMetricEntity) {
    LOG.trace("metricName="+simpleMetricEntity.getMetricName());
    LOG.trace("namespace="+simpleMetricEntity.getNamespace());
    LOG.trace("dimensionMap="+simpleMetricEntity.getDimensionMap());
    LOG.trace("metricType="+simpleMetricEntity.getMetricType());
    LOG.trace("units="+simpleMetricEntity.getUnits());
    LOG.trace("timestamp="+simpleMetricEntity.getTimestamp());
    LOG.trace("sampleSize="+simpleMetricEntity.getSampleSize());
    LOG.trace("sampleMax="+simpleMetricEntity.getSampleMax());
    LOG.trace("sampleMin="+simpleMetricEntity.getSampleMin());
    LOG.trace("sampleSum="+simpleMetricEntity.getSampleSum());
  
    if (simpleMetricEntity.getDimensionMap() == null) {
      simpleMetricEntity.setDimensionMap(new HashMap<String, String>());
    } else if (simpleMetricEntity.getDimensionMap().size() > MetricEntity.MAX_DIM_NUM) {
      throw new IllegalArgumentException("Too many dimensions for metric, "
        + simpleMetricEntity.getDimensionMap().size());
    }
    simpleMetricEntity.setTimestamp(stripSeconds(simpleMetricEntity.getTimestamp()));
  }
}


File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/metricdata/MetricStatistics.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain.metricdata;

import java.util.Collection;
import java.util.Date;

import com.eucalyptus.cloudwatch.domain.DimensionEntity;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;

public class MetricStatistics {

  private String accountId;
  private String namespace;
  private String metricName;
  private Units units;
  private MetricType metricType;
  private Date timestamp;
  private Double sampleSize;
  private Double sampleMax;
  private Double sampleMin;
  private Double sampleSum;
  private Collection<DimensionEntity> dimensions;

  
  public String getAccountId() {
    return accountId;
  }


  public void setAccountId(String accountId) {
    this.accountId = accountId;
  }


  public String getNamespace() {
    return namespace;
  }


  public void setNamespace(String namespace) {
    this.namespace = namespace;
  }


  public String getMetricName() {
    return metricName;
  }


  public void setMetricName(String metricName) {
    this.metricName = metricName;
  }


  public Units getUnits() {
    return units;
  }


  public void setUnits(Units units) {
    this.units = units;
  }


  public MetricType getMetricType() {
    return metricType;
  }


  public void setMetricType(MetricType metricType) {
    this.metricType = metricType;
  }


  public Date getTimestamp() {
    return timestamp;
  }


  public void setTimestamp(Date timestamp) {
    this.timestamp = timestamp;
  }


  public Double getSampleSize() {
    return sampleSize;
  }


  public void setSampleSize(Double sampleSize) {
    this.sampleSize = sampleSize;
  }


  public Double getSampleMax() {
    return sampleMax;
  }


  public void setSampleMax(Double sampleMax) {
    this.sampleMax = sampleMax;
  }


  public Double getSampleMin() {
    return sampleMin;
  }


  public void setSampleMin(Double sampleMin) {
    this.sampleMin = sampleMin;
  }


  public Double getSampleSum() {
    return sampleSum;
  }


  public void setSampleSum(Double sampleSum) {
    this.sampleSum = sampleSum;
  }


  public Collection<DimensionEntity> getDimensions() {
    return dimensions;
  }


  public void setDimensions(Collection<DimensionEntity> dimensions) {
    this.dimensions = dimensions;
  }

  public MetricStatistics(MetricEntity me, Date startTime, Integer period, Collection<DimensionEntity> dimensions) {
    this.accountId = me.getAccountId();
    this.namespace = me.getNamespace();
    this.metricName = me.getMetricName();
    this.units = me.getUnits();
    this.metricType = me.getMetricType();
    this.timestamp = MetricManager.getPeriodStart(me.getTimestamp(), startTime, period);
    this.sampleSize = me.getSampleSize();
    this.sampleMax = me.getSampleMax();
    this.sampleMin = me.getSampleMin();
    this.sampleSum = me.getSampleSum();
    this.dimensions = dimensions;
  }

}


File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/metricdata/PutMetricDataAggregationKey.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain.metricdata;

import java.util.Date;

import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;


public class PutMetricDataAggregationKey {

  private String accountId;
  private String dimensionHash;
  private String metricName;
  private MetricType metricType;
  private String namespace;
  private Date timestamp;
  private Units units;

  public PutMetricDataAggregationKey(SimpleMetricEntity item) {
    this.accountId = item.getAccountId();
    this.dimensionHash = MetricManager.hash(item.getDimensionMap());
    this.metricName = item.getMetricName();
    this.metricType = item.getMetricType();
    this.namespace = item.getNamespace();
    this.timestamp = item.getTimestamp();
    this.units = item.getUnits();
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result
        + ((accountId == null) ? 0 : accountId.hashCode());
    result = prime * result
        + ((dimensionHash == null) ? 0 : dimensionHash.hashCode());
    result = prime * result
        + ((metricName == null) ? 0 : metricName.hashCode());
    result = prime * result
        + ((metricType == null) ? 0 : metricType.hashCode());
    result = prime * result
        + ((namespace == null) ? 0 : namespace.hashCode());
    result = prime * result
        + ((timestamp == null) ? 0 : timestamp.hashCode());
    result = prime * result + ((units == null) ? 0 : units.hashCode());
    return result;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (getClass() != obj.getClass())
      return false;
    PutMetricDataAggregationKey other = (PutMetricDataAggregationKey) obj;
    if (accountId == null) {
      if (other.accountId != null)
        return false;
    } else if (!accountId.equals(other.accountId))
      return false;
    if (dimensionHash == null) {
      if (other.dimensionHash != null)
        return false;
    } else if (!dimensionHash.equals(other.dimensionHash))
      return false;
    if (metricName == null) {
      if (other.metricName != null)
        return false;
    } else if (!metricName.equals(other.metricName))
      return false;
    if (metricType != other.metricType)
      return false;
    if (namespace == null) {
      if (other.namespace != null)
        return false;
    } else if (!namespace.equals(other.namespace))
      return false;
    if (timestamp == null) {
      if (other.timestamp != null)
        return false;
    } else if (!timestamp.equals(other.timestamp))
      return false;
    if (units != other.units)
      return false;
    return true;
  }
  
}



File: clc/modules/cloudwatch-backend/src/main/java/com/eucalyptus/cloudwatch/domain/metricdata/SimpleMetricEntity.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain.metricdata;

import java.util.Date;
import java.util.Map;

import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;
import com.google.common.collect.Maps;

public class SimpleMetricEntity {
  private String accountId;
  private String metricName;
  private String namespace;
  private Map<String, String> dimensionMap;
  private MetricType metricType;
  private Units units;
  private Date timestamp;
  private Double sampleSize;
  private Double sampleMax;
  private Double sampleMin;
  private Double sampleSum;

  public SimpleMetricEntity(SimpleMetricEntity other) {
    this.accountId = other.accountId;
    this.metricName = other.metricName;
    this.namespace = other.namespace;
    this.dimensionMap = (other.dimensionMap == null ? null : Maps.newHashMap(other.dimensionMap));
    this.metricType = other.metricType;
    this.units = other.units;
    this.timestamp = other.timestamp;
    this.sampleSize = other.sampleSize;
    this.sampleMax = other.sampleMax;
    this.sampleMin = other.sampleMin;
    this.sampleSum = other.sampleSum;
  }
  public SimpleMetricEntity() {
  }

  public String getAccountId() {
    return accountId;
  }

  public void setAccountId(String accountId) {
    this.accountId = accountId;
  }

  public String getMetricName() {
    return metricName;
  }

  public void setMetricName(String metricName) {
    this.metricName = metricName;
  }

  public String getNamespace() {
    return namespace;
  }

  public void setNamespace(String namespace) {
    this.namespace = namespace;
  }

  public Map<String, String> getDimensionMap() {
    return dimensionMap;
  }

  public void setDimensionMap(Map<String, String> dimensionMap) {
    this.dimensionMap = dimensionMap;
  }

  public MetricType getMetricType() {
    return metricType;
  }

  public void setMetricType(MetricType metricType) {
    this.metricType = metricType;
  }

  public Units getUnits() {
    return units;
  }

  public void setUnits(Units units) {
    this.units = units;
  }

  public Date getTimestamp() {
    return timestamp;
  }

  public void setTimestamp(Date timestamp) {
    this.timestamp = timestamp;
  }

  public Double getSampleSize() {
    return sampleSize;
  }

  public void setSampleSize(Double sampleSize) {
    this.sampleSize = sampleSize;
  }

  public Double getSampleMax() {
    return sampleMax;
  }

  public void setSampleMax(Double sampleMax) {
    this.sampleMax = sampleMax;
  }

  public Double getSampleMin() {
    return sampleMin;
  }

  public void setSampleMin(Double sampleMin) {
    this.sampleMin = sampleMin;
  }

  public Double getSampleSum() {
    return sampleSum;
  }

  public void setSampleSum(Double sampleSum) {
    this.sampleSum = sampleSum;
  }

  @Override
  public String toString() {
    return "SimpleMetricEntity [accountId=" + accountId
        + ", metricName=" + metricName + ", namespace=" + namespace
        + ", dimensionMap=" + dimensionMap + ", metricType=" + metricType
        + ", units=" + units + ", timestamp=" + timestamp + ", sampleSize="
        + sampleSize + ", sampleMax=" + sampleMax + ", sampleMin="
        + sampleMin + ", sampleSum=" + sampleSum + "]";
  }
}


File: clc/modules/cloudwatch-backend/src/test/java/com/eucalyptus/cloudwatch/TestAggregationQueue.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch;

import static org.junit.Assert.*;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import org.junit.Test;

import com.eucalyptus.cloudwatch.domain.metricdata.MetricDataQueue;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricManager;
import com.eucalyptus.cloudwatch.domain.metricdata.SimpleMetricEntity;

public class TestAggregationQueue {

  private static final double TOLERANCE = 0.000000001; 
  @Test
  public void testDistinctAccounts() {
    final Date now = MetricManager.stripSeconds(new Date());
    // throw some different dimension order in there...
    final Map<String,String> hashMap = new HashMap<String, String>();
    hashMap.put("dim1", "val1");
    hashMap.put("dim2", "val2");
    final Map<String,String> treeMap = new TreeMap<String, String>();
    treeMap.put("dim2", "val2");
    treeMap.put("dim1", "val1");
  
    ArrayList<SimpleMetricEntity> list = new ArrayList<SimpleMetricEntity>();
    for (int i=0;i<10;i++) {
      SimpleMetricEntity mqi = new SimpleMetricEntity();
      mqi.setAccountId("account"+(i % 2)); 
      mqi.setDimensionMap((i % 3 == 0) ? hashMap: treeMap); // just a random dimension order
      mqi.setMetricName("metric1");
      mqi.setMetricType(MetricType.Custom);
      mqi.setNamespace("namespace1");
      mqi.setSampleMax((double) i);
      mqi.setSampleMin((double) i);
      mqi.setSampleSize((double) 1);
      mqi.setSampleSum((double) i);
      mqi.setTimestamp(now);
      mqi.setUnits(Units.None);
      list.add(mqi);
    }

    List<SimpleMetricEntity> aggregateList = MetricDataQueue.aggregate(list);
    // should be two items...
    assertEquals(2, aggregateList.size());
    // since we are not sure which order, one should have accountId account1 
    // and one should have accountId0
    SimpleMetricEntity odd, even;
    if (aggregateList.get(0).getAccountId().equals("account0")) {
      even = aggregateList.get(0);
      odd = aggregateList.get(1);
    } else {
      even = aggregateList.get(1);
      odd = aggregateList.get(0);
    }
    // even totals are 0,2,4,6,8 so total = 20, max = 8, min = 0, count = 5
    assertEquals(even.getSampleMax().doubleValue(), 8.0, TOLERANCE);
    assertEquals(even.getSampleMin().doubleValue(), 0.0, TOLERANCE);
    assertEquals(even.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(even.getSampleSum().doubleValue(), 20.0, TOLERANCE);
    assertEquals(even.getAccountId(), "account0");
    assertEquals(even.getDimensionMap(), hashMap); // really either should be ok
    assertEquals(even.getMetricName(), "metric1");
    assertEquals(even.getMetricType(), MetricType.Custom);
    assertEquals(even.getNamespace(), "namespace1");
    assertEquals(even.getTimestamp(), now);
    assertEquals(even.getUnits(), Units.None);

    // odd totals are 1,3,5,7,9 so total = 25, max = 9, min = 1, count = 5
    assertEquals(odd.getSampleMax().doubleValue(), 9.0, TOLERANCE);
    assertEquals(odd.getSampleMin().doubleValue(), 1.0, TOLERANCE);
    assertEquals(odd.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(odd.getSampleSum().doubleValue(), 25.0, TOLERANCE);
    assertEquals(odd.getAccountId(), "account1");
    assertEquals(odd.getDimensionMap(), treeMap); // really either should be ok
    assertEquals(odd.getMetricName(), "metric1");
    assertEquals(odd.getMetricType(), MetricType.Custom);
    assertEquals(odd.getNamespace(), "namespace1");
    assertEquals(odd.getTimestamp(), now);
    assertEquals(odd.getUnits(), Units.None);
  }

  @Test
  public void testDistinctMetricNames() {
    final Date now = MetricManager.stripSeconds(new Date());
    // throw some different dimension order in there...
    final Map<String,String> hashMap = new HashMap<String, String>();
    hashMap.put("dim1", "val1");
    hashMap.put("dim2", "val2");
    final Map<String,String> treeMap = new TreeMap<String, String>();
    treeMap.put("dim2", "val2");
    treeMap.put("dim1", "val1");
  
    ArrayList<SimpleMetricEntity> list = new ArrayList<SimpleMetricEntity>();
    for (int i=0;i<10;i++) {
      SimpleMetricEntity mqi = new SimpleMetricEntity();
      mqi.setAccountId("account1");
      mqi.setDimensionMap((i % 3 == 0) ? hashMap: treeMap); // just a random dimension order
      mqi.setMetricName("metric"+(i % 2));
      mqi.setMetricType(MetricType.Custom);
      mqi.setNamespace("namespace1");
      mqi.setSampleMax((double) i);
      mqi.setSampleMin((double) i);
      mqi.setSampleSize((double) 1);
      mqi.setSampleSum((double) i);
      mqi.setTimestamp(now);
      mqi.setUnits(Units.None);
      list.add(mqi);
    }

    List<SimpleMetricEntity> aggregateList = MetricDataQueue.aggregate(list);
    // should be two items...
    assertEquals(2, aggregateList.size());
    // since we are not sure which order, one should have metricName metric1 
    // and one should have metric0
    SimpleMetricEntity odd, even;
    if (aggregateList.get(0).getMetricName().equals("metric0")) {
      even = aggregateList.get(0);
      odd = aggregateList.get(1);
    } else {
      even = aggregateList.get(1);
      odd = aggregateList.get(0);
    }
    // even totals are 0,2,4,6,8 so total = 20, max = 8, min = 0, count = 5
    assertEquals(even.getSampleMax().doubleValue(), 8.0, TOLERANCE);
    assertEquals(even.getSampleMin().doubleValue(), 0.0, TOLERANCE);
    assertEquals(even.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(even.getSampleSum().doubleValue(), 20.0, TOLERANCE);
    assertEquals(even.getAccountId(), "account1");
    assertEquals(even.getDimensionMap(), hashMap); // really either should be ok
    assertEquals(even.getMetricName(), "metric0");
    assertEquals(even.getMetricType(), MetricType.Custom);
    assertEquals(even.getNamespace(), "namespace1");
    assertEquals(even.getTimestamp(), now);
    assertEquals(even.getUnits(), Units.None);

    // odd totals are 1,3,5,7,9 so total = 25, max = 9, min = 1, count = 5
    assertEquals(odd.getSampleMax().doubleValue(), 9.0, TOLERANCE);
    assertEquals(odd.getSampleMin().doubleValue(), 1.0, TOLERANCE);
    assertEquals(odd.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(odd.getSampleSum().doubleValue(), 25.0, TOLERANCE);
    assertEquals(odd.getAccountId(), "account1");
    assertEquals(odd.getDimensionMap(), treeMap); // really either should be ok
    assertEquals(odd.getMetricName(), "metric1");
    assertEquals(odd.getMetricType(), MetricType.Custom);
    assertEquals(odd.getNamespace(), "namespace1");
    assertEquals(odd.getTimestamp(), now);
    assertEquals(odd.getUnits(), Units.None);
  }


  @Test
  public void testDistinctMetricTypes() {
    final Date now = MetricManager.stripSeconds(new Date());
    // throw some different dimension order in there...
    final Map<String,String> hashMap = new HashMap<String, String>();
    hashMap.put("dim1", "val1");
    hashMap.put("dim2", "val2");
    final Map<String,String> treeMap = new TreeMap<String, String>();
    treeMap.put("dim2", "val2");
    treeMap.put("dim1", "val1");
  
    ArrayList<SimpleMetricEntity> list = new ArrayList<SimpleMetricEntity>();
    for (int i=0;i<10;i++) {
      SimpleMetricEntity mqi = new SimpleMetricEntity();
      mqi.setAccountId("account1");
      mqi.setDimensionMap((i % 3 == 0) ? hashMap: treeMap); // just a random dimension order
      mqi.setMetricName("metric1");
      mqi.setMetricType((i % 2) == 0 ? MetricType.Custom: MetricType.System);
      mqi.setNamespace("namespace1");
      mqi.setSampleMax((double) i);
      mqi.setSampleMin((double) i);
      mqi.setSampleSize((double) 1);
      mqi.setSampleSum((double) i);
      mqi.setTimestamp(now);
      mqi.setUnits(Units.None);
      list.add(mqi);
    }

    List<SimpleMetricEntity> aggregateList = MetricDataQueue.aggregate(list);
    // should be two items...
    assertEquals(2, aggregateList.size());
    // since we are not sure which order, one should have metricType Custom 
    // and one should have System
    SimpleMetricEntity odd, even;
    if (aggregateList.get(0).getMetricType().equals(MetricType.Custom)) {
      even = aggregateList.get(0);
      odd = aggregateList.get(1);
    } else {
      even = aggregateList.get(1);
      odd = aggregateList.get(0);
    }
    // even totals are 0,2,4,6,8 so total = 20, max = 8, min = 0, count = 5
    assertEquals(even.getSampleMax().doubleValue(), 8.0, TOLERANCE);
    assertEquals(even.getSampleMin().doubleValue(), 0.0, TOLERANCE);
    assertEquals(even.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(even.getSampleSum().doubleValue(), 20.0, TOLERANCE);
    assertEquals(even.getAccountId(), "account1");
    assertEquals(even.getDimensionMap(), hashMap); // really either should be ok
    assertEquals(even.getMetricName(), "metric1");
    assertEquals(even.getMetricType(), MetricType.Custom);
    assertEquals(even.getNamespace(), "namespace1");
    assertEquals(even.getTimestamp(), now);
    assertEquals(even.getUnits(), Units.None);

    // odd totals are 1,3,5,7,9 so total = 25, max = 9, min = 1, count = 5
    assertEquals(odd.getSampleMax().doubleValue(), 9.0, TOLERANCE);
    assertEquals(odd.getSampleMin().doubleValue(), 1.0, TOLERANCE);
    assertEquals(odd.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(odd.getSampleSum().doubleValue(), 25.0, TOLERANCE);
    assertEquals(odd.getAccountId(), "account1");
    assertEquals(odd.getDimensionMap(), treeMap); // really either should be ok
    assertEquals(odd.getMetricName(), "metric1");
    assertEquals(odd.getMetricType(), MetricType.System);
    assertEquals(odd.getNamespace(), "namespace1");
    assertEquals(odd.getTimestamp(), now);
    assertEquals(odd.getUnits(), Units.None);
  }
  
  @Test
  public void testDistinctNamespaces() {
    final Date now = MetricManager.stripSeconds(new Date());
    // throw some different dimension order in there...
    final Map<String,String> hashMap = new HashMap<String, String>();
    hashMap.put("dim1", "val1");
    hashMap.put("dim2", "val2");
    final Map<String,String> treeMap = new TreeMap<String, String>();
    treeMap.put("dim2", "val2");
    treeMap.put("dim1", "val1");
  
    ArrayList<SimpleMetricEntity> list = new ArrayList<SimpleMetricEntity>();
    for (int i=0;i<10;i++) {
      SimpleMetricEntity mqi = new SimpleMetricEntity();
      mqi.setAccountId("account1");
      mqi.setDimensionMap((i % 3 == 0) ? hashMap: treeMap); // just a random dimension order
      mqi.setMetricName("metric1");
      mqi.setMetricType(MetricType.Custom);
      mqi.setNamespace("namespace"+(i%2));
      mqi.setSampleMax((double) i);
      mqi.setSampleMin((double) i);
      mqi.setSampleSize((double) 1);
      mqi.setSampleSum((double) i);
      mqi.setTimestamp(now);
      mqi.setUnits(Units.None);
      list.add(mqi);
    }

    List<SimpleMetricEntity> aggregateList = MetricDataQueue.aggregate(list);
    // should be two items...
    assertEquals(2, aggregateList.size());
    // since we are not sure which order, one should have namespace namespace0
    // and one should have namespace0
    SimpleMetricEntity odd, even;
    if (aggregateList.get(0).getNamespace().equals("namespace0")) {
      even = aggregateList.get(0);
      odd = aggregateList.get(1);
    } else {
      even = aggregateList.get(1);
      odd = aggregateList.get(0);
    }
    // even totals are 0,2,4,6,8 so total = 20, max = 8, min = 0, count = 5
    assertEquals(even.getSampleMax().doubleValue(), 8.0, TOLERANCE);
    assertEquals(even.getSampleMin().doubleValue(), 0.0, TOLERANCE);
    assertEquals(even.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(even.getSampleSum().doubleValue(), 20.0, TOLERANCE);
    assertEquals(even.getAccountId(), "account1");
    assertEquals(even.getDimensionMap(), hashMap); // really either should be ok
    assertEquals(even.getMetricName(), "metric1");
    assertEquals(even.getMetricType(), MetricType.Custom);
    assertEquals(even.getNamespace(), "namespace0");
    assertEquals(even.getTimestamp(), now);
    assertEquals(even.getUnits(), Units.None);

    // odd totals are 1,3,5,7,9 so total = 25, max = 9, min = 1, count = 5
    assertEquals(odd.getSampleMax().doubleValue(), 9.0, TOLERANCE);
    assertEquals(odd.getSampleMin().doubleValue(), 1.0, TOLERANCE);
    assertEquals(odd.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(odd.getSampleSum().doubleValue(), 25.0, TOLERANCE);
    assertEquals(odd.getAccountId(), "account1");
    assertEquals(odd.getDimensionMap(), treeMap); // really either should be ok
    assertEquals(odd.getMetricName(), "metric1");
    assertEquals(odd.getMetricType(), MetricType.Custom);
    assertEquals(odd.getNamespace(), "namespace1");
    assertEquals(odd.getTimestamp(), now);
    assertEquals(odd.getUnits(), Units.None);
  }

  @Test
  public void testDistinctTimestamps() {
    final Date now = MetricManager.stripSeconds(new Date());
    final Date later = MetricManager.stripSeconds(new Date(now.getTime() + 120000L)); // two minutes
      // throw some different dimension order in there...
    final Map<String,String> hashMap = new HashMap<String, String>();
    hashMap.put("dim1", "val1");
    hashMap.put("dim2", "val2");
    final Map<String,String> treeMap = new TreeMap<String, String>();
    treeMap.put("dim2", "val2");
    treeMap.put("dim1", "val1");
  
    ArrayList<SimpleMetricEntity> list = new ArrayList<SimpleMetricEntity>();
    for (int i=0;i<10;i++) {
      SimpleMetricEntity mqi = new SimpleMetricEntity();
      mqi.setAccountId("account1");
      mqi.setDimensionMap((i % 3 == 0) ? hashMap: treeMap); // just a random dimension order
      mqi.setMetricName("metric1");
      mqi.setMetricType(MetricType.Custom);
      mqi.setNamespace("namespace1");
      mqi.setSampleMax((double) i);
      mqi.setSampleMin((double) i);
      mqi.setSampleSize((double) 1);
      mqi.setSampleSum((double) i);
      mqi.setTimestamp((i % 2 == 0) ? now : later);
      mqi.setUnits(Units.None);
      list.add(mqi);
    }

    List<SimpleMetricEntity> aggregateList = MetricDataQueue.aggregate(list);
    // should be two items...
    assertEquals(2, aggregateList.size());
    // since we are not sure which order, one should have timestamp now
    // and one should have later
    SimpleMetricEntity odd, even;
    if (aggregateList.get(0).getTimestamp().equals(now)) {
      even = aggregateList.get(0);
      odd = aggregateList.get(1);
    } else {
      even = aggregateList.get(1);
      odd = aggregateList.get(0);
    }
    // even totals are 0,2,4,6,8 so total = 20, max = 8, min = 0, count = 5
    assertEquals(even.getSampleMax().doubleValue(), 8.0, TOLERANCE);
    assertEquals(even.getSampleMin().doubleValue(), 0.0, TOLERANCE);
    assertEquals(even.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(even.getSampleSum().doubleValue(), 20.0, TOLERANCE);
    assertEquals(even.getAccountId(), "account1");
    assertEquals(even.getDimensionMap(), hashMap); // really either should be ok
    assertEquals(even.getMetricName(), "metric1");
    assertEquals(even.getMetricType(), MetricType.Custom);
    assertEquals(even.getNamespace(), "namespace1");
    assertEquals(even.getTimestamp(), now);
    assertEquals(even.getUnits(), Units.None);

    // odd totals are 1,3,5,7,9 so total = 25, max = 9, min = 1, count = 5
    assertEquals(odd.getSampleMax().doubleValue(), 9.0, TOLERANCE);
    assertEquals(odd.getSampleMin().doubleValue(), 1.0, TOLERANCE);
    assertEquals(odd.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(odd.getSampleSum().doubleValue(), 25.0, TOLERANCE);
    assertEquals(odd.getAccountId(), "account1");
    assertEquals(odd.getDimensionMap(), treeMap); // really either should be ok
    assertEquals(odd.getMetricName(), "metric1");
    assertEquals(odd.getMetricType(), MetricType.Custom);
    assertEquals(odd.getNamespace(), "namespace1");
    assertEquals(odd.getTimestamp(), later);
    assertEquals(odd.getUnits(), Units.None);
  }

  @Test
  public void testDistinctUnits() {
    final Date now = MetricManager.stripSeconds(new Date());
      // throw some different dimension order in there...
    final Map<String,String> hashMap = new HashMap<String, String>();
    hashMap.put("dim1", "val1");
    hashMap.put("dim2", "val2");
    final Map<String,String> treeMap = new TreeMap<String, String>();
    treeMap.put("dim2", "val2");
    treeMap.put("dim1", "val1");
  
    ArrayList<SimpleMetricEntity> list = new ArrayList<SimpleMetricEntity>();
    for (int i=0;i<10;i++) {
      SimpleMetricEntity mqi = new SimpleMetricEntity();
      mqi.setAccountId("account1");
      mqi.setDimensionMap((i % 3 == 0) ? hashMap: treeMap); // just a random dimension order
      mqi.setMetricName("metric1");
      mqi.setMetricType(MetricType.Custom);
      mqi.setNamespace("namespace1");
      mqi.setSampleMax((double) i);
      mqi.setSampleMin((double) i);
      mqi.setSampleSize((double) 1);
      mqi.setSampleSum((double) i);
      mqi.setTimestamp(now);
      mqi.setUnits((i % 2 == 0) ? Units.None : Units.Count);
      list.add(mqi);
    }

    List<SimpleMetricEntity> aggregateList = MetricDataQueue.aggregate(list);
    // should be two items...
    assertEquals(2, aggregateList.size());
    // since we are not sure which order, one should have units none
    // and one should have count
    SimpleMetricEntity odd, even;
    if (aggregateList.get(0).getUnits().equals(Units.None)) {
      even = aggregateList.get(0);
      odd = aggregateList.get(1);
    } else {
      even = aggregateList.get(1);
      odd = aggregateList.get(0);
    }
    // even totals are 0,2,4,6,8 so total = 20, max = 8, min = 0, count = 5
    assertEquals(even.getSampleMax().doubleValue(), 8.0, TOLERANCE);
    assertEquals(even.getSampleMin().doubleValue(), 0.0, TOLERANCE);
    assertEquals(even.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(even.getSampleSum().doubleValue(), 20.0, TOLERANCE);
    assertEquals(even.getAccountId(), "account1");
    assertEquals(even.getDimensionMap(), hashMap); // really either should be ok
    assertEquals(even.getMetricName(), "metric1");
    assertEquals(even.getMetricType(), MetricType.Custom);
    assertEquals(even.getNamespace(), "namespace1");
    assertEquals(even.getTimestamp(), now);
    assertEquals(even.getUnits(), Units.None);

    // odd totals are 1,3,5,7,9 so total = 25, max = 9, min = 1, count = 5
    assertEquals(odd.getSampleMax().doubleValue(), 9.0, TOLERANCE);
    assertEquals(odd.getSampleMin().doubleValue(), 1.0, TOLERANCE);
    assertEquals(odd.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(odd.getSampleSum().doubleValue(), 25.0, TOLERANCE);
    assertEquals(odd.getAccountId(), "account1");
    assertEquals(odd.getDimensionMap(), treeMap); // really either should be ok
    assertEquals(odd.getMetricName(), "metric1");
    assertEquals(odd.getMetricType(), MetricType.Custom);
    assertEquals(odd.getNamespace(), "namespace1");
    assertEquals(odd.getTimestamp(), now);
    assertEquals(odd.getUnits(), Units.Count);
  }

  @Test
  public void testDistinctDimensionMaps() {
    final Date now = MetricManager.stripSeconds(new Date());
      // throw some different dimension order in there...
    final Map<String,String> hashMap = new HashMap<String, String>();
    hashMap.put("dim1", "val1");
    hashMap.put("dim2", "val2");
    final Map<String,String> treeMap = new TreeMap<String, String>();
    treeMap.put("dim2", "val2");
    treeMap.put("dim1", "val1");
  
    ArrayList<SimpleMetricEntity> list = new ArrayList<SimpleMetricEntity>();
    for (int i=0;i<10;i++) {
      SimpleMetricEntity mqi = new SimpleMetricEntity();
      mqi.setAccountId("account1");
      mqi.setDimensionMap((i % 2 == 0) ? null: hashMap); 
      mqi.setMetricName("metric1");
      mqi.setMetricType(MetricType.Custom);
      mqi.setNamespace("namespace1");
      mqi.setSampleMax((double) i);
      mqi.setSampleMin((double) i);
      mqi.setSampleSize((double) 1);
      mqi.setSampleSum((double) i);
      mqi.setTimestamp(now);
      mqi.setUnits(Units.None);
      list.add(mqi);
    }

    List<SimpleMetricEntity> aggregateList = MetricDataQueue.aggregate(list);
    // should be two items...
    assertEquals(2, aggregateList.size());
    // since we are not sure which order, one should have dimensionMap null
    // and one should have hashMap
    SimpleMetricEntity odd, even;
    if (aggregateList.get(0).getDimensionMap() == null) {
      even = aggregateList.get(0);
      odd = aggregateList.get(1);
    } else {
      even = aggregateList.get(1);
      odd = aggregateList.get(0);
    }
    // even totals are 0,2,4,6,8 so total = 20, max = 8, min = 0, count = 5
    assertEquals(even.getSampleMax().doubleValue(), 8.0, TOLERANCE);
    assertEquals(even.getSampleMin().doubleValue(), 0.0, TOLERANCE);
    assertEquals(even.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(even.getSampleSum().doubleValue(), 20.0, TOLERANCE);
    assertEquals(even.getAccountId(), "account1");
    assertEquals(even.getDimensionMap(), null); 
    assertEquals(even.getMetricName(), "metric1");
    assertEquals(even.getMetricType(), MetricType.Custom);
    assertEquals(even.getNamespace(), "namespace1");
    assertEquals(even.getTimestamp(), now);
    assertEquals(even.getUnits(), Units.None);

    // odd totals are 1,3,5,7,9 so total = 25, max = 9, min = 1, count = 5
    assertEquals(odd.getSampleMax().doubleValue(), 9.0, TOLERANCE);
    assertEquals(odd.getSampleMin().doubleValue(), 1.0, TOLERANCE);
    assertEquals(odd.getSampleSize().doubleValue(), 5.0, TOLERANCE);
    assertEquals(odd.getSampleSum().doubleValue(), 25.0, TOLERANCE);
    assertEquals(odd.getAccountId(), "account1");
    assertEquals(odd.getDimensionMap(), treeMap); // really either should be ok
    assertEquals(odd.getMetricName(), "metric1");
    assertEquals(odd.getMetricType(), MetricType.Custom);
    assertEquals(odd.getNamespace(), "namespace1");
    assertEquals(odd.getTimestamp(), now);
    assertEquals(odd.getUnits(), Units.None);
  }

  /*
  public static void main(String[] args) {
    
    ArrayList<SimpleMetricEntity> list6 = new ArrayList<SimpleMetricEntity>();
    for (int i=0;i<10;i++) {
      SimpleMetricEntity mqi = new SimpleMetricEntity();
      mqi.setAccountId("account1");
      mqi.setDimensionMap((i % 3 == 0) ? hashMap: treeMap);
      mqi.setMetricName("metric1");
      mqi.setMetricType(MetricType.Custom);
      mqi.setNamespace("namespace1");
      mqi.setSampleMax((double) i);
      mqi.setSampleMin((double) i);
      mqi.setSampleSize((double) 1);
      mqi.setSampleSum((double) i);
      mqi.setTimestamp(now);
      mqi.setUnits((i % 2 == 0) ? Units.None : Units.Count);
      mqi.setUserId("user1");
      list6.add(mqi);
    }
*/  

}


File: clc/modules/cloudwatch-backend/src/test/java/com/eucalyptus/cloudwatch/domain/metricdata/MetricTest.java
/*************************************************************************
 * Copyright 2009-2013 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/
package com.eucalyptus.cloudwatch.domain.metricdata;

import java.util.Date;
import java.util.HashMap;
import java.util.Map;

import org.apache.log4j.Logger;
import org.junit.Ignore;

import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.MetricType;
import com.eucalyptus.cloudwatch.domain.metricdata.MetricEntity.Units;

@Ignore("Manual development test")
public class MetricTest {
  private static final Logger LOG = Logger.getLogger(MetricTest.class);

  public static void addStuff() {
    Map<String, String> dimensionMap1 = new HashMap<String, String>();
    dimensionMap1.put("dim1", "dim1");
    Map<String, String> dimensionMap2 = new HashMap<String, String>();
    dimensionMap2.put("dim1", "dim1");
    dimensionMap2.put("dim2", "dim2");
    Map<String, String> dimensionMap3 = new HashMap<String, String>();
    dimensionMap3.put("dim1", "dim1");
    dimensionMap3.put("dim2", "dim2");
    dimensionMap3.put("dim3", "dim3");
    dimensionMap3.put("dim4", "dim4");
    dimensionMap3.put("dim5", "dim5");
    Map<String, String> dimensionMap4 = new HashMap<String, String>();
    dimensionMap4.put("dim1", "dim1");
    dimensionMap4.put("dim2", "dim2");
    dimensionMap4.put("dim3", "dim3");
    dimensionMap4.put("dim4", "dim4");
    dimensionMap4.put("dim5", "dim5");
    dimensionMap4.put("dim6", "dim6");
    dimensionMap4.put("dim7", "dim7");
    dimensionMap4.put("dim8", "dim8");
    dimensionMap4.put("dim9", "dim9");
    dimensionMap4.put("dim10", "dim10");
    MetricManager.addMetric("account1", "metric1", "name1", null,
        MetricType.Custom, Units.None, new Date(), 1.0, 1.0, 1.0, 1.0);
    MetricManager.addMetric("account1", "metric1", "name1",
        dimensionMap1, MetricType.System, Units.BitsPerSecond,
        new Date(System.currentTimeMillis() - 10000000), 1.0, 2.0, 2.0, 2.0);
    MetricManager.addMetric("account1", "metric1", "name1",
        dimensionMap2, MetricType.System, Units.Count,
        new Date(System.currentTimeMillis() - 20000000), 1.0, 3.0, 3.0, 3.0);
    MetricManager.addMetric("account1", "metric1", "name1",
        dimensionMap3, MetricType.System, Units.Count,
        new Date(System.currentTimeMillis() - 20000000), 1.0, 3.0, 3.0, 3.0);
    MetricManager.addMetric("account1", "metric1", "name1",
        dimensionMap4, MetricType.System, Units.Count,
        new Date(System.currentTimeMillis() - 20000000), 1.0, 3.0, 3.0, 3.0);
    for (MetricEntity me : MetricManager.getAllMetrics()) {
      LOG.fatal("Metric:" + me);
    }
    MetricManager.deleteAllMetrics();
  }
}


File: clc/modules/cluster-manager/src/main/java/com/eucalyptus/cluster/callback/DescribeSensorCallback.java
/*************************************************************************
 * Copyright 2009-2014 Eucalyptus Systems, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 *
 * Please contact Eucalyptus Systems, Inc., 6755 Hollister Ave., Goleta
 * CA 93117, USA or visit http://www.eucalyptus.com/licenses/ if you need
 * additional information or have any questions.
 ************************************************************************/

package com.eucalyptus.cluster.callback;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;

import com.eucalyptus.cloudwatch.common.msgs.PutMetricDataType;

import edu.ucsb.eucalyptus.msgs.DescribeSensorsResponse;
import edu.ucsb.eucalyptus.msgs.DescribeSensorsType;
import edu.ucsb.eucalyptus.msgs.MetricCounterType;
import edu.ucsb.eucalyptus.msgs.MetricDimensionsType;
import edu.ucsb.eucalyptus.msgs.MetricsResourceType;
import edu.ucsb.eucalyptus.msgs.SensorsResourceType;
import edu.ucsb.eucalyptus.msgs.MetricDimensionsValuesType;

import org.apache.log4j.Logger;

import com.eucalyptus.auth.Accounts;
import com.eucalyptus.auth.AuthException;
import com.eucalyptus.component.ServiceConfiguration;
import com.eucalyptus.event.EventFailedException;
import com.eucalyptus.event.ListenerRegistry;
import com.eucalyptus.records.Logs;
import com.eucalyptus.reporting.event.InstanceUsageEvent;
import com.eucalyptus.util.LogUtil;
import com.eucalyptus.util.async.BroadcastCallback;
import com.eucalyptus.compute.common.internal.vm.VmInstance.VmState;
import com.eucalyptus.vm.VmInstances;

import com.google.common.base.Function;
import com.google.common.base.Supplier;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Ordering;

public class DescribeSensorCallback extends
    BroadcastCallback<DescribeSensorsType, DescribeSensorsResponse> {

  private static final Logger LOG = Logger.getLogger(DescribeSensorCallback.class);
  private static final String RESOURCE_TYPE_INSTANCE = "instance";
  private final int historySize;
  private final int collectionIntervalTimeMs;
  private final ArrayList<String> instanceIds;
  private final ListenerRegistry listener = ListenerRegistry.getInstance();

  public DescribeSensorCallback(final int historySize,
                                final int collectionIntervalTimeMS, final ArrayList<String> instanceIds) {
    this.historySize = historySize;
    this.collectionIntervalTimeMs = collectionIntervalTimeMS;
    this.instanceIds = instanceIds;

    final DescribeSensorsType msg =
        new DescribeSensorsType(this.historySize, this.collectionIntervalTimeMs, this.instanceIds);

    this.setRequest(msg);
  }

  @Override
  public void initialize(final DescribeSensorsType msg) {
  }

  @Override
  public BroadcastCallback<DescribeSensorsType, DescribeSensorsResponse> newInstance() {
    return new DescribeSensorCallback(this.historySize, this.collectionIntervalTimeMs, this.instanceIds);
  }

  @Override
  public void fireException(Throwable e) {
    LOG.debug("Request failed: "
        + LogUtil.subheader(this.getRequest().toString(
        "eucalyptus_ucsb_edu")));
    Logs.extreme().error(e, e);
  }



  @Override
  public void fire(final DescribeSensorsResponse msg) {
    LOG.trace("DescribeSensorCallback (fire) called at " + new Date());
    try {
      processCloudWatchStats(msg);
    } catch (Exception ex) {
      LOG.debug("Unable to fire describe sensors call back (cloudwatch)", ex);
    }
    try {
      processReportingStats(msg);
    } catch (Exception ex) {
      LOG.debug("Unable to fire describe sensors call back (reporting)", ex);
    }
  }

  private void processCloudWatchStats(final DescribeSensorsResponse msg) throws Exception {
    CloudWatchHelper cloudWatchHelper = new CloudWatchHelper(new CloudWatchHelper.DefaultInstanceInfoProvider());
    List<PutMetricDataType> putMetricDataList = cloudWatchHelper.collectMetricData(msg);
    ServiceConfiguration serviceConfiguration = CloudWatchHelper.createServiceConfiguration();
    for (PutMetricDataType putMetricData: putMetricDataList) {
      cloudWatchHelper.sendSystemMetric(serviceConfiguration, putMetricData);
    }
  }


  private void processReportingStats(final DescribeSensorsResponse msg) throws Exception {
    final Iterable<String> uuidList =
        Iterables.transform(VmInstances.list(VmState.RUNNING), VmInstances.toInstanceUuid());
    for (final SensorsResourceType sensorData : msg.getSensorsResources()) {
      if (!RESOURCE_TYPE_INSTANCE.equals(sensorData.getResourceType()) ||
          !Iterables.contains(uuidList, sensorData.getResourceUuid()))
        continue;
      
      for (final MetricsResourceType metricType : sensorData.getMetrics()) {
        for (final MetricCounterType counterType : metricType.getCounters()) {
          for (final MetricDimensionsType dimensionType : counterType.getDimensions()) {
            // find and fire most recent value for metric/dimension
            final List<MetricDimensionsValuesType> values =
                Lists.newArrayList(dimensionType.getValues());

            //Reporting use case of metric data from the cc
            Collections.sort(values, Ordering.natural().onResultOf(GetTimestamp.INSTANCE));

            if (!values.isEmpty()) {
              final MetricDimensionsValuesType latestValue = Iterables.getLast(values);
              final Double usageValue = latestValue.getValue();
              if (usageValue == null) {
                LOG.debug("Event received with null 'value', skipping for reporting");
                continue;
              }
              final Long usageTimestamp = latestValue.getTimestamp().getTime();
              final long sequenceNumber = dimensionType.getSequenceNum() + (values.size() - 1);
              fireUsageEvent( new Supplier<InstanceUsageEvent>(){
                @Override
                public InstanceUsageEvent get() {
                  return new InstanceUsageEvent(
                      sensorData.getResourceUuid(),
                      sensorData.getResourceName(),
                      metricType.getMetricName(),
                      sequenceNumber,
                      dimensionType.getDimensionName(),
                      usageValue,
                      usageTimestamp);
                }
              });
            }
          }
        }
      }
    }
  }  

  
  

  private void fireUsageEvent(Supplier<InstanceUsageEvent> instanceUsageEventSupplier) {
    InstanceUsageEvent event = null;
    event = instanceUsageEventSupplier.get();
    try {
      listener.fireEvent(event);
    } catch (EventFailedException e) {
      LOG.debug("Failed to fire instance usage event"
          + (event != null ? event : ""), e);
    }
  }

  enum GetTimestamp implements Function<MetricDimensionsValuesType, Date> {
    INSTANCE;

    @Override
    public Date apply(final MetricDimensionsValuesType metricDimensionsValuesType) {
      return metricDimensionsValuesType.getTimestamp();
    }
  }

}
