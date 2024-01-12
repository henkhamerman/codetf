Refactoring Types: ['Rename Package']
ava/org/sonar/server/db/DbClient.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.db;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.IdentityHashMap;
import java.util.Map;
import org.sonar.api.server.ServerSide;
import org.sonar.core.issue.db.ActionPlanDao;
import org.sonar.core.issue.db.IssueChangeDao;
import org.sonar.core.issue.db.IssueFilterDao;
import org.sonar.core.permission.PermissionTemplateDao;
import org.sonar.core.persistence.DaoComponent;
import org.sonar.core.persistence.Database;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.persistence.MyBatis;
import org.sonar.core.properties.PropertiesDao;
import org.sonar.core.purge.PurgeDao;
import org.sonar.core.qualityprofile.db.QualityProfileDao;
import org.sonar.core.resource.ResourceDao;
import org.sonar.core.technicaldebt.db.CharacteristicDao;
import org.sonar.core.template.LoadedTemplateDao;
import org.sonar.core.user.AuthorDao;
import org.sonar.core.user.AuthorizationDao;
import org.sonar.core.user.GroupMembershipDao;
import org.sonar.core.user.RoleDao;
import org.sonar.server.activity.db.ActivityDao;
import org.sonar.server.component.db.ComponentDao;
import org.sonar.server.component.db.ComponentIndexDao;
import org.sonar.server.component.db.ComponentLinkDao;
import org.sonar.server.component.db.SnapshotDao;
import org.sonar.server.computation.db.AnalysisReportDao;
import org.sonar.server.custommeasure.persistence.CustomMeasureDao;
import org.sonar.server.dashboard.db.DashboardDao;
import org.sonar.server.dashboard.db.WidgetDao;
import org.sonar.server.dashboard.db.WidgetPropertyDao;
import org.sonar.server.event.db.EventDao;
import org.sonar.server.issue.db.IssueDao;
import org.sonar.server.measure.persistence.MeasureDao;
import org.sonar.server.metric.persistence.MetricDao;
import org.sonar.server.qualityprofile.db.ActiveRuleDao;
import org.sonar.server.rule.db.RuleDao;
import org.sonar.server.source.db.FileSourceDao;
import org.sonar.server.user.db.GroupDao;
import org.sonar.server.user.db.UserDao;
import org.sonar.server.user.db.UserGroupDao;

/**
 * Facade for all db components, mainly DAOs
 */
@ServerSide
public class DbClient {

  private final Database db;
  private final MyBatis myBatis;
  private final RuleDao ruleDao;
  private final ActiveRuleDao activeRuleDao;
  private final QualityProfileDao qualityProfileDao;
  private final CharacteristicDao debtCharacteristicDao;
  private final LoadedTemplateDao loadedTemplateDao;
  private final PropertiesDao propertiesDao;
  private final ComponentDao componentDao;
  private final SnapshotDao snapshotDao;
  private final ResourceDao resourceDao;
  private final MeasureDao measureDao;
  private final MetricDao metricDao;
  private final ActivityDao activityDao;
  private final AuthorizationDao authorizationDao;
  private final UserDao userDao;
  private final GroupDao groupDao;
  private final UserGroupDao userGroupDao;
  private final GroupMembershipDao groupMembershipDao;
  private final RoleDao roleDao;
  private final PermissionTemplateDao permissionTemplateDao;
  private final IssueDao issueDao;
  private final IssueFilterDao issueFilterDao;
  private final IssueChangeDao issueChangeDao;
  private final ActionPlanDao actionPlanDao;
  private final AnalysisReportDao analysisReportDao;
  private final DashboardDao dashboardDao;
  private final WidgetDao widgetDao;
  private final WidgetPropertyDao widgetPropertyDao;
  private final FileSourceDao fileSourceDao;
  private final AuthorDao authorDao;
  private final ComponentIndexDao componentIndexDao;
  private final ComponentLinkDao componentLinkDao;
  private final EventDao eventDao;
  private final PurgeDao purgeDao;
  private final CustomMeasureDao customMeasureDao;

  public DbClient(Database db, MyBatis myBatis, DaoComponent... daoComponents) {
    this.db = db;
    this.myBatis = myBatis;

    Map<Class, DaoComponent> map = new IdentityHashMap<>();
    for (DaoComponent daoComponent : daoComponents) {
      map.put(daoComponent.getClass(), daoComponent);
    }
    ruleDao = getDao(map, RuleDao.class);
    activeRuleDao = getDao(map, ActiveRuleDao.class);
    debtCharacteristicDao = getDao(map, CharacteristicDao.class);
    qualityProfileDao = getDao(map, QualityProfileDao.class);
    loadedTemplateDao = getDao(map, LoadedTemplateDao.class);
    propertiesDao = getDao(map, PropertiesDao.class);
    componentDao = getDao(map, ComponentDao.class);
    snapshotDao = getDao(map, SnapshotDao.class);
    resourceDao = getDao(map, ResourceDao.class);
    measureDao = getDao(map, MeasureDao.class);
    metricDao = getDao(map, MetricDao.class);
    customMeasureDao = getDao(map, CustomMeasureDao.class);
    activityDao = getDao(map, ActivityDao.class);
    authorizationDao = getDao(map, AuthorizationDao.class);
    userDao = getDao(map, UserDao.class);
    groupDao = getDao(map, GroupDao.class);
    userGroupDao = getDao(map, UserGroupDao.class);
    groupMembershipDao = getDao(map, GroupMembershipDao.class);
    roleDao = getDao(map, RoleDao.class);
    permissionTemplateDao = getDao(map, PermissionTemplateDao.class);
    issueDao = getDao(map, IssueDao.class);
    issueFilterDao = getDao(map, IssueFilterDao.class);
    issueChangeDao = getDao(map, IssueChangeDao.class);
    actionPlanDao = getDao(map, ActionPlanDao.class);
    analysisReportDao = getDao(map, AnalysisReportDao.class);
    dashboardDao = getDao(map, DashboardDao.class);
    widgetDao = getDao(map, WidgetDao.class);
    widgetPropertyDao = getDao(map, WidgetPropertyDao.class);
    fileSourceDao = getDao(map, FileSourceDao.class);
    authorDao = getDao(map, AuthorDao.class);
    componentIndexDao = getDao(map, ComponentIndexDao.class);
    componentLinkDao = getDao(map, ComponentLinkDao.class);
    eventDao = getDao(map, EventDao.class);
    purgeDao = getDao(map, PurgeDao.class);
  }

  public Database database() {
    return db;
  }

  public DbSession openSession(boolean batch) {
    return myBatis.openSession(batch);
  }

  public RuleDao ruleDao() {
    return ruleDao;
  }

  public ActiveRuleDao activeRuleDao() {
    return activeRuleDao;
  }

  public IssueDao issueDao() {
    return issueDao;
  }

  public IssueFilterDao issueFilterDao() {
    return issueFilterDao;
  }

  public IssueChangeDao issueChangeDao() {
    return issueChangeDao;
  }

  public QualityProfileDao qualityProfileDao() {
    return qualityProfileDao;
  }

  public CharacteristicDao debtCharacteristicDao() {
    return debtCharacteristicDao;
  }

  public LoadedTemplateDao loadedTemplateDao() {
    return loadedTemplateDao;
  }

  public PropertiesDao propertiesDao() {
    return propertiesDao;
  }

  public ComponentDao componentDao() {
    return componentDao;
  }

  public SnapshotDao snapshotDao() {
    return snapshotDao;
  }

  public ResourceDao resourceDao() {
    return resourceDao;
  }

  public MeasureDao measureDao() {
    return measureDao;
  }

  public MetricDao metricDao() {
    return metricDao;
  }

  public CustomMeasureDao customMeasureDao() {
    return customMeasureDao;
  }

  public ActivityDao activityDao() {
    return activityDao;
  }

  public AuthorizationDao authorizationDao() {
    return authorizationDao;
  }

  public UserDao userDao() {
    return userDao;
  }

  public GroupDao groupDao() {
    return groupDao;
  }

  public UserGroupDao userGroupDao() {
    return userGroupDao;
  }

  public GroupMembershipDao groupMembershipDao() {
    return groupMembershipDao;
  }

  public RoleDao roleDao() {
    return roleDao;
  }

  public PermissionTemplateDao permissionTemplateDao() {
    return permissionTemplateDao;
  }

  public ActionPlanDao actionPlanDao() {
    return actionPlanDao;
  }

  public AnalysisReportDao analysisReportDao() {
    return analysisReportDao;
  }

  public DashboardDao dashboardDao() {
    return dashboardDao;
  }

  public WidgetDao widgetDao() {
    return widgetDao;
  }

  public WidgetPropertyDao widgetPropertyDao() {
    return widgetPropertyDao;
  }

  public FileSourceDao fileSourceDao() {
    return fileSourceDao;
  }

  public AuthorDao authorDao() {
    return authorDao;
  }

  public ComponentIndexDao componentIndexDao() {
    return componentIndexDao;
  }

  public ComponentLinkDao componentLinkDao() {
    return componentLinkDao;
  }

  public EventDao eventDao() {
    return eventDao;
  }

  public PurgeDao purgeDao() {
    return purgeDao;
  }

  private <K> K getDao(Map<Class, DaoComponent> map, Class<K> clazz) {
    return (K) map.get(clazz);
  }

  /**
   * Create a PreparedStatement for SELECT requests with scrolling of results
   */
  public final PreparedStatement newScrollingSelectStatement(Connection connection, String sql) {
    int fetchSize = database().getDialect().getScrollDefaultFetchSize();
    return newScrollingSelectStatement(connection, sql, fetchSize);
  }

  /**
   * Create a PreparedStatement for SELECT requests with scrolling of results row by row (only one row
   * in memory at a time)
   */
  public final PreparedStatement newScrollingSingleRowSelectStatement(Connection connection, String sql) {
    int fetchSize = database().getDialect().getScrollSingleRowFetchSize();
    return newScrollingSelectStatement(connection, sql, fetchSize);
  }

  private PreparedStatement newScrollingSelectStatement(Connection connection, String sql, int fetchSize) {
    try {
      PreparedStatement stmt = connection.prepareStatement(sql, ResultSet.TYPE_FORWARD_ONLY, ResultSet.CONCUR_READ_ONLY);
      stmt.setFetchSize(fetchSize);
      return stmt;
    } catch (SQLException e) {
      throw new IllegalStateException("Fail to create SQL statement: " + sql, e);
    }
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/platform/platformlevel/PlatformLevel1.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.platform.platformlevel;

import java.util.Properties;
import javax.annotation.Nullable;
import org.sonar.api.utils.System2;
import org.sonar.api.utils.internal.TempFolderCleaner;
import org.sonar.core.config.CorePropertyDefinitions;
import org.sonar.core.config.Logback;
import org.sonar.core.measure.db.MeasureFilterDao;
import org.sonar.core.persistence.DaoUtils;
import org.sonar.core.persistence.DatabaseVersion;
import org.sonar.core.persistence.DefaultDatabase;
import org.sonar.core.persistence.MyBatis;
import org.sonar.core.persistence.SemaphoreUpdater;
import org.sonar.core.persistence.SemaphoresImpl;
import org.sonar.core.purge.PurgeProfiler;
import org.sonar.server.activity.db.ActivityDao;
import org.sonar.server.component.db.ComponentDao;
import org.sonar.server.component.db.ComponentIndexDao;
import org.sonar.server.component.db.ComponentLinkDao;
import org.sonar.server.component.db.SnapshotDao;
import org.sonar.server.computation.db.AnalysisReportDao;
import org.sonar.server.custommeasure.persistence.CustomMeasureDao;
import org.sonar.server.dashboard.db.DashboardDao;
import org.sonar.server.dashboard.db.WidgetDao;
import org.sonar.server.dashboard.db.WidgetPropertyDao;
import org.sonar.server.db.DatabaseChecker;
import org.sonar.server.db.DbClient;
import org.sonar.server.db.EmbeddedDatabaseFactory;
import org.sonar.server.db.migrations.MigrationStepModule;
import org.sonar.server.event.db.EventDao;
import org.sonar.server.issue.db.IssueDao;
import org.sonar.server.issue.index.IssueIndex;
import org.sonar.server.measure.persistence.MeasureDao;
import org.sonar.server.metric.persistence.MetricDao;
import org.sonar.server.platform.DatabaseServerCompatibility;
import org.sonar.server.platform.DefaultServerFileSystem;
import org.sonar.server.platform.Platform;
import org.sonar.server.platform.ServerImpl;
import org.sonar.server.platform.ServerSettings;
import org.sonar.server.platform.TempFolderProvider;
import org.sonar.server.qualityprofile.db.ActiveRuleDao;
import org.sonar.server.qualityprofile.index.ActiveRuleIndex;
import org.sonar.server.qualityprofile.index.ActiveRuleNormalizer;
import org.sonar.server.ruby.PlatformRackBridge;
import org.sonar.server.rule.db.RuleDao;
import org.sonar.server.rule.index.RuleIndex;
import org.sonar.server.rule.index.RuleNormalizer;
import org.sonar.server.search.EsSearchModule;
import org.sonar.server.search.IndexQueue;
import org.sonar.server.source.db.FileSourceDao;
import org.sonar.server.user.ThreadLocalUserSession;
import org.sonar.server.user.db.GroupDao;
import org.sonar.server.user.db.UserDao;
import org.sonar.server.user.db.UserGroupDao;

public class PlatformLevel1 extends PlatformLevel {
  private final Platform platform;
  private final Properties properties;
  @Nullable
  private final Object[] extraRootComponents;

  public PlatformLevel1(Platform platform, Properties properties, Object... extraRootComponents) {
    super("level1");
    this.platform = platform;
    this.properties = properties;
    this.extraRootComponents = extraRootComponents;
  }

  @Override
  public void configureLevel() {
    add(platform, properties);
    addExtraRootComponents();
    add(
      ServerSettings.class,
      ServerImpl.class,
      Logback.class,
      EmbeddedDatabaseFactory.class,
      DefaultDatabase.class,
      DatabaseChecker.class,
      MyBatis.class,
      IndexQueue.class,
      DatabaseServerCompatibility.class,
      DatabaseVersion.class,
      PurgeProfiler.class,
      DefaultServerFileSystem.class,
      SemaphoreUpdater.class,
      SemaphoresImpl.class,
      TempFolderCleaner.class,
      new TempFolderProvider(),
      System2.INSTANCE,

      // rack bridges
      PlatformRackBridge.class,

      // user session
      ThreadLocalUserSession.class,

      // DB
      DbClient.class,

      // Elasticsearch
      EsSearchModule.class,

      // users
      GroupDao.class,
      UserDao.class,
      UserGroupDao.class,

      // dashboards
      DashboardDao.class,
      WidgetDao.class,
      WidgetPropertyDao.class,

      // rules/qprofiles
      RuleNormalizer.class,
      ActiveRuleNormalizer.class,
      RuleIndex.class,
      ActiveRuleIndex.class,
      RuleDao.class,
      ActiveRuleDao.class,

      // issues
      IssueIndex.class,
      IssueDao.class,

      // measures
      MeasureDao.class,
      MetricDao.class,
      MeasureFilterDao.class,
      CustomMeasureDao.class,

      // components
      ComponentDao.class,
      ComponentIndexDao.class,
      ComponentLinkDao.class,
      SnapshotDao.class,

      EventDao.class,
      ActivityDao.class,
      AnalysisReportDao.class,
      FileSourceDao.class);
    addAll(CorePropertyDefinitions.all());
    add(MigrationStepModule.class);
    addAll(DaoUtils.getDaoClasses());
  }

  private void addExtraRootComponents() {
    if (this.extraRootComponents != null) {
      for (Object extraRootComponent : this.extraRootComponents) {
        add(extraRootComponent);
      }
    }
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/platform/platformlevel/PlatformLevel4.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.platform.platformlevel;

import java.util.List;
import org.sonar.api.config.EmailSettings;
import org.sonar.api.issue.action.Actions;
import org.sonar.api.profiles.AnnotationProfileParser;
import org.sonar.api.profiles.XMLProfileParser;
import org.sonar.api.profiles.XMLProfileSerializer;
import org.sonar.api.resources.Languages;
import org.sonar.api.resources.ResourceTypes;
import org.sonar.api.rules.AnnotationRuleParser;
import org.sonar.api.rules.XMLRuleParser;
import org.sonar.api.server.rule.RulesDefinitionXmlLoader;
import org.sonar.core.computation.dbcleaner.IndexPurgeListener;
import org.sonar.core.computation.dbcleaner.ProjectCleaner;
import org.sonar.core.computation.dbcleaner.period.DefaultPeriodCleaner;
import org.sonar.core.issue.IssueFilterSerializer;
import org.sonar.core.issue.IssueUpdater;
import org.sonar.core.issue.workflow.FunctionExecutor;
import org.sonar.core.issue.workflow.IssueWorkflow;
import org.sonar.core.metric.DefaultMetricFinder;
import org.sonar.server.notification.DefaultNotificationManager;
import org.sonar.core.permission.PermissionFacade;
import org.sonar.core.qualitygate.db.ProjectQgateAssociationDao;
import org.sonar.core.qualitygate.db.QualityGateConditionDao;
import org.sonar.core.qualitygate.db.QualityGateDao;
import org.sonar.core.resource.DefaultResourcePermissions;
import org.sonar.core.resource.DefaultResourceTypes;
import org.sonar.core.timemachine.Periods;
import org.sonar.core.user.DefaultUserFinder;
import org.sonar.core.user.HibernateUserFinder;
import org.sonar.jpa.dao.MeasuresDao;
import org.sonar.server.activity.ActivityService;
import org.sonar.server.activity.RubyQProfileActivityService;
import org.sonar.server.activity.index.ActivityIndex;
import org.sonar.server.activity.index.ActivityIndexDefinition;
import org.sonar.server.activity.index.ActivityIndexer;
import org.sonar.server.activity.ws.ActivitiesWs;
import org.sonar.server.activity.ws.ActivityMapping;
import org.sonar.server.authentication.ws.AuthenticationWs;
import org.sonar.server.batch.BatchWsModule;
import org.sonar.server.charts.ChartFactory;
import org.sonar.server.charts.DistributionAreaChart;
import org.sonar.server.charts.DistributionBarChart;
import org.sonar.server.component.ComponentCleanerService;
import org.sonar.server.component.ComponentService;
import org.sonar.server.component.DefaultComponentFinder;
import org.sonar.server.component.DefaultRubyComponentService;
import org.sonar.server.component.ws.ComponentsWs;
import org.sonar.server.component.ws.EventsWs;
import org.sonar.server.component.ws.ResourcesWs;
import org.sonar.server.computation.ComputationThreadLauncher;
import org.sonar.server.computation.ReportQueue;
import org.sonar.server.computation.ws.ComputationWs;
import org.sonar.server.computation.ws.HistoryAction;
import org.sonar.server.computation.ws.IsQueueEmptyWs;
import org.sonar.server.computation.ws.QueueAction;
import org.sonar.server.config.ws.PropertiesWs;
import org.sonar.server.custommeasure.ws.CustomMeasuresWsModule;
import org.sonar.server.dashboard.template.GlobalDefaultDashboard;
import org.sonar.server.dashboard.template.ProjectDefaultDashboard;
import org.sonar.server.dashboard.template.ProjectIssuesDashboard;
import org.sonar.server.dashboard.template.ProjectTimeMachineDashboard;
import org.sonar.server.dashboard.widget.ActionPlansWidget;
import org.sonar.server.dashboard.widget.AlertsWidget;
import org.sonar.server.dashboard.widget.BubbleChartWidget;
import org.sonar.server.dashboard.widget.ComplexityWidget;
import org.sonar.server.dashboard.widget.CoverageWidget;
import org.sonar.server.dashboard.widget.CustomMeasuresWidget;
import org.sonar.server.dashboard.widget.DebtOverviewWidget;
import org.sonar.server.dashboard.widget.DescriptionWidget;
import org.sonar.server.dashboard.widget.DocumentationCommentsWidget;
import org.sonar.server.dashboard.widget.DuplicationsWidget;
import org.sonar.server.dashboard.widget.EventsWidget;
import org.sonar.server.dashboard.widget.HotspotMetricWidget;
import org.sonar.server.dashboard.widget.IssueFilterWidget;
import org.sonar.server.dashboard.widget.IssueTagCloudWidget;
import org.sonar.server.dashboard.widget.IssuesWidget;
import org.sonar.server.dashboard.widget.ItCoverageWidget;
import org.sonar.server.dashboard.widget.MeasureFilterAsBubbleChartWidget;
import org.sonar.server.dashboard.widget.MeasureFilterAsCloudWidget;
import org.sonar.server.dashboard.widget.MeasureFilterAsHistogramWidget;
import org.sonar.server.dashboard.widget.MeasureFilterAsPieChartWidget;
import org.sonar.server.dashboard.widget.MeasureFilterAsTreemapWidget;
import org.sonar.server.dashboard.widget.MeasureFilterListWidget;
import org.sonar.server.dashboard.widget.ProjectFileCloudWidget;
import org.sonar.server.dashboard.widget.ProjectIssueFilterWidget;
import org.sonar.server.dashboard.widget.SizeWidget;
import org.sonar.server.dashboard.widget.TechnicalDebtPyramidWidget;
import org.sonar.server.dashboard.widget.TimeMachineWidget;
import org.sonar.server.dashboard.widget.TimelineWidget;
import org.sonar.server.dashboard.widget.TreemapWidget;
import org.sonar.server.dashboard.widget.WelcomeWidget;
import org.sonar.server.dashboard.ws.DashboardsWs;
import org.sonar.server.debt.DebtCharacteristicsXMLImporter;
import org.sonar.server.debt.DebtModelBackup;
import org.sonar.server.debt.DebtModelLookup;
import org.sonar.server.debt.DebtModelOperations;
import org.sonar.server.debt.DebtModelPluginRepository;
import org.sonar.server.debt.DebtModelService;
import org.sonar.server.debt.DebtModelXMLExporter;
import org.sonar.server.debt.DebtRulesXMLImporter;
import org.sonar.server.duplication.ws.DuplicationsJsonWriter;
import org.sonar.server.duplication.ws.DuplicationsParser;
import org.sonar.server.duplication.ws.DuplicationsWs;
import org.sonar.server.es.IndexCreator;
import org.sonar.server.es.IndexDefinitions;
import org.sonar.server.event.NewAlerts;
import org.sonar.server.issue.ActionService;
import org.sonar.server.issue.AddTagsAction;
import org.sonar.server.issue.AssignAction;
import org.sonar.server.issue.CommentAction;
import org.sonar.server.issue.InternalRubyIssueService;
import org.sonar.server.issue.IssueBulkChangeService;
import org.sonar.server.issue.IssueChangelogFormatter;
import org.sonar.server.issue.IssueChangelogService;
import org.sonar.server.issue.IssueCommentService;
import org.sonar.server.issue.IssueQueryService;
import org.sonar.server.issue.IssueService;
import org.sonar.server.issue.PlanAction;
import org.sonar.server.issue.RemoveTagsAction;
import org.sonar.server.issue.ServerIssueStorage;
import org.sonar.server.issue.SetSeverityAction;
import org.sonar.server.issue.TransitionAction;
import org.sonar.server.issue.actionplan.ActionPlanService;
import org.sonar.server.issue.actionplan.ActionPlanWs;
import org.sonar.server.issue.filter.IssueFilterService;
import org.sonar.server.issue.filter.IssueFilterWriter;
import org.sonar.server.issue.filter.IssueFilterWs;
import org.sonar.server.issue.index.IssueAuthorizationIndexer;
import org.sonar.server.issue.index.IssueIndexDefinition;
import org.sonar.server.issue.index.IssueIndexer;
import org.sonar.server.issue.notification.ChangesOnMyIssueNotificationDispatcher;
import org.sonar.server.issue.notification.DoNotFixNotificationDispatcher;
import org.sonar.server.issue.notification.IssueChangesEmailTemplate;
import org.sonar.server.issue.notification.MyNewIssuesEmailTemplate;
import org.sonar.server.issue.notification.MyNewIssuesNotificationDispatcher;
import org.sonar.server.issue.notification.NewIssuesEmailTemplate;
import org.sonar.server.issue.notification.NewIssuesNotificationDispatcher;
import org.sonar.server.issue.notification.NewIssuesNotificationFactory;
import org.sonar.server.issue.ws.ComponentTagsAction;
import org.sonar.server.issue.ws.IssueActionsWriter;
import org.sonar.server.issue.ws.IssuesWs;
import org.sonar.server.issue.ws.SetTagsAction;
import org.sonar.server.language.ws.LanguageWs;
import org.sonar.server.measure.MeasureFilterEngine;
import org.sonar.server.measure.MeasureFilterExecutor;
import org.sonar.server.measure.MeasureFilterFactory;
import org.sonar.server.measure.template.MyFavouritesFilter;
import org.sonar.server.measure.template.ProjectFilter;
import org.sonar.server.measure.ws.ManualMeasuresWs;
import org.sonar.server.measure.ws.TimeMachineWs;
import org.sonar.server.metric.CoreCustomMetrics;
import org.sonar.server.metric.ws.MetricsWsModule;
import org.sonar.server.notification.NotificationCenter;
import org.sonar.server.notification.NotificationService;
import org.sonar.server.notification.email.AlertsEmailTemplate;
import org.sonar.server.notification.email.EmailNotificationChannel;
import org.sonar.server.permission.InternalPermissionService;
import org.sonar.server.permission.InternalPermissionTemplateService;
import org.sonar.server.permission.PermissionFinder;
import org.sonar.server.permission.ws.PermissionsWs;
import org.sonar.server.platform.BackendCleanup;
import org.sonar.server.platform.SettingsChangeNotifier;
import org.sonar.server.platform.monitoring.DatabaseMonitor;
import org.sonar.server.platform.monitoring.EsMonitor;
import org.sonar.server.platform.monitoring.JvmPropertiesMonitor;
import org.sonar.server.platform.monitoring.PluginsMonitor;
import org.sonar.server.platform.monitoring.SonarQubeMonitor;
import org.sonar.server.platform.monitoring.SystemMonitor;
import org.sonar.server.platform.ws.InfoAction;
import org.sonar.server.platform.ws.L10nWs;
import org.sonar.server.platform.ws.MigrateDbSystemAction;
import org.sonar.server.platform.ws.RestartAction;
import org.sonar.server.platform.ws.ServerWs;
import org.sonar.server.platform.ws.StatusAction;
import org.sonar.server.platform.ws.SystemWs;
import org.sonar.server.platform.ws.UpgradesAction;
import org.sonar.server.plugins.PluginDownloader;
import org.sonar.server.plugins.ServerExtensionInstaller;
import org.sonar.server.plugins.UpdateCenterClient;
import org.sonar.server.plugins.UpdateCenterMatrixFactory;
import org.sonar.server.plugins.ws.AvailableAction;
import org.sonar.server.plugins.ws.CancelAllAction;
import org.sonar.server.plugins.ws.InstallAction;
import org.sonar.server.plugins.ws.InstalledAction;
import org.sonar.server.plugins.ws.PendingAction;
import org.sonar.server.plugins.ws.PluginUpdateAggregator;
import org.sonar.server.plugins.ws.PluginWSCommons;
import org.sonar.server.plugins.ws.PluginsWs;
import org.sonar.server.plugins.ws.UninstallAction;
import org.sonar.server.plugins.ws.UpdatesAction;
import org.sonar.server.project.ws.ProjectsWsModule;
import org.sonar.server.properties.ProjectSettingsFactory;
import org.sonar.server.qualitygate.QgateProjectFinder;
import org.sonar.server.qualitygate.QualityGates;
import org.sonar.server.qualitygate.ws.CreateConditionAction;
import org.sonar.server.qualitygate.ws.DeleteConditionAction;
import org.sonar.server.qualitygate.ws.DeselectAction;
import org.sonar.server.qualitygate.ws.DestroyAction;
import org.sonar.server.qualitygate.ws.QGatesWs;
import org.sonar.server.qualitygate.ws.SelectAction;
import org.sonar.server.qualitygate.ws.SetAsDefaultAction;
import org.sonar.server.qualitygate.ws.UnsetDefaultAction;
import org.sonar.server.qualitygate.ws.UpdateConditionAction;
import org.sonar.server.qualityprofile.BuiltInProfiles;
import org.sonar.server.qualityprofile.QProfileBackuper;
import org.sonar.server.qualityprofile.QProfileComparison;
import org.sonar.server.qualityprofile.QProfileCopier;
import org.sonar.server.qualityprofile.QProfileExporters;
import org.sonar.server.qualityprofile.QProfileFactory;
import org.sonar.server.qualityprofile.QProfileLoader;
import org.sonar.server.qualityprofile.QProfileLookup;
import org.sonar.server.qualityprofile.QProfileProjectLookup;
import org.sonar.server.qualityprofile.QProfileProjectOperations;
import org.sonar.server.qualityprofile.QProfileReset;
import org.sonar.server.qualityprofile.QProfileService;
import org.sonar.server.qualityprofile.QProfiles;
import org.sonar.server.qualityprofile.RuleActivator;
import org.sonar.server.qualityprofile.RuleActivatorContextFactory;
import org.sonar.server.qualityprofile.ws.BackupAction;
import org.sonar.server.qualityprofile.ws.BulkRuleActivationActions;
import org.sonar.server.qualityprofile.ws.ChangeParentAction;
import org.sonar.server.qualityprofile.ws.ChangelogAction;
import org.sonar.server.qualityprofile.ws.CompareAction;
import org.sonar.server.qualityprofile.ws.CopyAction;
import org.sonar.server.qualityprofile.ws.CreateAction;
import org.sonar.server.qualityprofile.ws.ExportAction;
import org.sonar.server.qualityprofile.ws.ExportersAction;
import org.sonar.server.qualityprofile.ws.ImportersAction;
import org.sonar.server.qualityprofile.ws.InheritanceAction;
import org.sonar.server.qualityprofile.ws.ProfilesWs;
import org.sonar.server.qualityprofile.ws.ProjectAssociationActions;
import org.sonar.server.qualityprofile.ws.ProjectsAction;
import org.sonar.server.qualityprofile.ws.QProfilesWs;
import org.sonar.server.qualityprofile.ws.RenameAction;
import org.sonar.server.qualityprofile.ws.RestoreAction;
import org.sonar.server.qualityprofile.ws.RestoreBuiltInAction;
import org.sonar.server.qualityprofile.ws.RuleActivationActions;
import org.sonar.server.qualityprofile.ws.SetDefaultAction;
import org.sonar.server.rule.DefaultRuleFinder;
import org.sonar.server.rule.DeprecatedRulesDefinitionLoader;
import org.sonar.server.rule.RubyRuleService;
import org.sonar.server.rule.RuleCreator;
import org.sonar.server.rule.RuleDefinitionsLoader;
import org.sonar.server.rule.RuleDeleter;
import org.sonar.server.rule.RuleOperations;
import org.sonar.server.rule.RuleRepositories;
import org.sonar.server.rule.RuleService;
import org.sonar.server.rule.RuleUpdater;
import org.sonar.server.rule.ws.ActiveRuleCompleter;
import org.sonar.server.rule.ws.RepositoriesAction;
import org.sonar.server.rule.ws.RuleMapping;
import org.sonar.server.rule.ws.RulesWs;
import org.sonar.server.rule.ws.TagsAction;
import org.sonar.server.source.HtmlSourceDecorator;
import org.sonar.server.source.SourceService;
import org.sonar.server.source.index.SourceLineIndex;
import org.sonar.server.source.index.SourceLineIndexDefinition;
import org.sonar.server.source.index.SourceLineIndexer;
import org.sonar.server.source.ws.HashAction;
import org.sonar.server.source.ws.IndexAction;
import org.sonar.server.source.ws.LinesAction;
import org.sonar.server.source.ws.RawAction;
import org.sonar.server.source.ws.ScmAction;
import org.sonar.server.source.ws.SourcesWs;
import org.sonar.server.test.CoverageService;
import org.sonar.server.test.index.TestIndex;
import org.sonar.server.test.index.TestIndexDefinition;
import org.sonar.server.test.index.TestIndexer;
import org.sonar.server.test.ws.CoveredFilesAction;
import org.sonar.server.test.ws.TestsWs;
import org.sonar.server.text.MacroInterpreter;
import org.sonar.server.text.RubyTextService;
import org.sonar.server.ui.PageDecorations;
import org.sonar.server.ui.Views;
import org.sonar.server.ui.ws.ComponentNavigationAction;
import org.sonar.server.ui.ws.GlobalNavigationAction;
import org.sonar.server.ui.ws.NavigationWs;
import org.sonar.server.ui.ws.SettingsNavigationAction;
import org.sonar.server.updatecenter.ws.UpdateCenterWs;
import org.sonar.server.user.DefaultUserService;
import org.sonar.server.user.GroupMembershipFinder;
import org.sonar.server.user.GroupMembershipService;
import org.sonar.server.user.NewUserNotifier;
import org.sonar.server.user.SecurityRealmFactory;
import org.sonar.server.user.UserUpdater;
import org.sonar.server.user.index.UserIndex;
import org.sonar.server.user.index.UserIndexDefinition;
import org.sonar.server.user.index.UserIndexer;
import org.sonar.server.user.ws.CurrentAction;
import org.sonar.server.user.ws.FavoritesWs;
import org.sonar.server.user.ws.UserPropertiesWs;
import org.sonar.server.user.ws.UsersWs;
import org.sonar.server.usergroups.ws.UserGroupsModule;
import org.sonar.server.util.BooleanTypeValidation;
import org.sonar.server.util.FloatTypeValidation;
import org.sonar.server.util.IntegerTypeValidation;
import org.sonar.server.util.StringListTypeValidation;
import org.sonar.server.util.StringTypeValidation;
import org.sonar.server.util.TextTypeValidation;
import org.sonar.server.util.TypeValidations;
import org.sonar.server.view.index.ViewIndex;
import org.sonar.server.view.index.ViewIndexDefinition;
import org.sonar.server.view.index.ViewIndexer;
import org.sonar.server.ws.ListingWs;
import org.sonar.server.ws.WebServiceEngine;

public class PlatformLevel4 extends PlatformLevel {

  private final List<Object> level4AddedComponents;

  public PlatformLevel4(PlatformLevel parent, List<Object> level4AddedComponents) {
    super("level4", parent);
    this.level4AddedComponents = level4AddedComponents;
  }

  @Override
  protected void configureLevel() {
    add(
      PluginDownloader.class,
      ChartFactory.class,
      DistributionBarChart.class,
      DistributionAreaChart.class,
      Views.class,
      ResourceTypes.class,
      DefaultResourceTypes.get(),
      SettingsChangeNotifier.class,
      PageDecorations.class,
      DefaultResourcePermissions.class,
      Periods.class,
      ServerWs.class,
      BackendCleanup.class,
      IndexDefinitions.class,
      IndexCreator.class,

      // Activity
      ActivityService.class,
      ActivityIndexDefinition.class,
      ActivityIndexer.class,
      ActivityIndex.class,

      // batch
      BatchWsModule.class,

      // Dashboard
      DashboardsWs.class,
      org.sonar.server.dashboard.ws.ShowAction.class,
      ProjectDefaultDashboard.class,
      ProjectIssuesDashboard.class,
      ProjectTimeMachineDashboard.class,
      GlobalDefaultDashboard.class,
      AlertsWidget.class,
      CoverageWidget.class,
      ItCoverageWidget.class,
      DescriptionWidget.class,
      ComplexityWidget.class,
      IssuesWidget.class,
      SizeWidget.class,
      EventsWidget.class,
      CustomMeasuresWidget.class,
      TimelineWidget.class,
      BubbleChartWidget.class,
      TimeMachineWidget.class,
      HotspotMetricWidget.class,
      TreemapWidget.class,
      MeasureFilterListWidget.class,
      MeasureFilterAsTreemapWidget.class,
      WelcomeWidget.class,
      DocumentationCommentsWidget.class,
      DuplicationsWidget.class,
      TechnicalDebtPyramidWidget.class,
      MeasureFilterAsPieChartWidget.class,
      MeasureFilterAsCloudWidget.class,
      MeasureFilterAsHistogramWidget.class,
      MeasureFilterAsBubbleChartWidget.class,
      ProjectFileCloudWidget.class,
      DebtOverviewWidget.class,
      ActionPlansWidget.class,
      IssueFilterWidget.class,
      ProjectIssueFilterWidget.class,
      IssueTagCloudWidget.class,

      // update center
      UpdateCenterClient.class,
      UpdateCenterMatrixFactory.class,
      UpdateCenterWs.class,

      // quality profile
      XMLProfileParser.class,
      XMLProfileSerializer.class,
      AnnotationProfileParser.class,
      QProfiles.class,
      QProfileLookup.class,
      QProfileProjectOperations.class,
      QProfileProjectLookup.class,
      QProfileComparison.class,
      BuiltInProfiles.class,
      RestoreBuiltInAction.class,
      org.sonar.server.qualityprofile.ws.SearchAction.class,
      SetDefaultAction.class,
      ProjectsAction.class,
      org.sonar.server.qualityprofile.ws.DeleteAction.class,
      RenameAction.class,
      CopyAction.class,
      BackupAction.class,
      RestoreAction.class,
      CreateAction.class,
      ImportersAction.class,
      InheritanceAction.class,
      ChangeParentAction.class,
      ChangelogAction.class,
      CompareAction.class,
      ExportAction.class,
      ExportersAction.class,
      QProfilesWs.class,
      ProfilesWs.class,
      RuleActivationActions.class,
      BulkRuleActivationActions.class,
      ProjectAssociationActions.class,
      RuleActivator.class,
      QProfileLoader.class,
      QProfileExporters.class,
      QProfileService.class,
      RuleActivatorContextFactory.class,
      QProfileFactory.class,
      QProfileCopier.class,
      QProfileBackuper.class,
      QProfileReset.class,
      RubyQProfileActivityService.class,

      // rule
      AnnotationRuleParser.class,
      XMLRuleParser.class,
      DefaultRuleFinder.class,
      RuleOperations.class,
      RubyRuleService.class,
      RuleRepositories.class,
      DeprecatedRulesDefinitionLoader.class,
      RuleDefinitionsLoader.class,
      RulesDefinitionXmlLoader.class,
      RuleService.class,
      RuleUpdater.class,
      RuleCreator.class,
      RuleDeleter.class,
      org.sonar.server.rule.ws.UpdateAction.class,
      RulesWs.class,
      org.sonar.server.rule.ws.SearchAction.class,
      org.sonar.server.rule.ws.ShowAction.class,
      org.sonar.server.rule.ws.CreateAction.class,
      org.sonar.server.rule.ws.DeleteAction.class,
      TagsAction.class,
      RuleMapping.class,
      ActiveRuleCompleter.class,
      RepositoriesAction.class,
      org.sonar.server.rule.ws.AppAction.class,

      // languages
      Languages.class,
      LanguageWs.class,
      org.sonar.server.language.ws.ListAction.class,

      // activity
      ActivitiesWs.class,
      org.sonar.server.activity.ws.SearchAction.class,
      ActivityMapping.class,

      // measure
      MeasuresDao.class,

      MeasureFilterFactory.class,
      MeasureFilterExecutor.class,
      MeasureFilterEngine.class,
      ManualMeasuresWs.class,
      MetricsWsModule.class,
      CustomMeasuresWsModule.class,
      ProjectFilter.class,
      MyFavouritesFilter.class,
      CoreCustomMetrics.class,
      DefaultMetricFinder.class,
      TimeMachineWs.class,

      // quality gates
      QualityGateDao.class,
      QualityGateConditionDao.class,
      QualityGates.class,
      ProjectQgateAssociationDao.class,
      QgateProjectFinder.class,

      org.sonar.server.qualitygate.ws.ListAction.class,
      org.sonar.server.qualitygate.ws.SearchAction.class,
      org.sonar.server.qualitygate.ws.ShowAction.class,
      org.sonar.server.qualitygate.ws.CreateAction.class,
      org.sonar.server.qualitygate.ws.RenameAction.class,
      org.sonar.server.qualitygate.ws.CopyAction.class,
      DestroyAction.class,
      SetAsDefaultAction.class,
      UnsetDefaultAction.class,
      SelectAction.class,
      DeselectAction.class,
      CreateConditionAction.class,
      DeleteConditionAction.class,
      UpdateConditionAction.class,
      org.sonar.server.qualitygate.ws.AppAction.class,
      QGatesWs.class,

      // web services
      WebServiceEngine.class,
      ListingWs.class,

      // localization
      L10nWs.class,

      // authentication
      AuthenticationWs.class,

      // users
      SecurityRealmFactory.class,
      HibernateUserFinder.class,
      NewUserNotifier.class,
      DefaultUserFinder.class,
      DefaultUserService.class,
      UsersWs.class,
      org.sonar.server.user.ws.CreateAction.class,
      org.sonar.server.user.ws.UpdateAction.class,
      org.sonar.server.user.ws.DeactivateAction.class,
      org.sonar.server.user.ws.ChangePasswordAction.class,
      CurrentAction.class,
      org.sonar.server.user.ws.SearchAction.class,
      org.sonar.server.user.ws.GroupsAction.class,
      org.sonar.server.issue.ws.AuthorsAction.class,
      FavoritesWs.class,
      UserPropertiesWs.class,
      UserIndexDefinition.class,
      UserIndexer.class,
      UserIndex.class,
      UserUpdater.class,

      // groups
      GroupMembershipService.class,
      GroupMembershipFinder.class,
      UserGroupsModule.class,

      // permissions
      PermissionFacade.class,
      InternalPermissionService.class,
      InternalPermissionTemplateService.class,
      PermissionFinder.class,
      PermissionsWs.class,

      // components
      ProjectsWsModule.class,
      DefaultComponentFinder.class,
      DefaultRubyComponentService.class,
      ComponentService.class,
      ResourcesWs.class,
      ComponentsWs.class,
      org.sonar.server.component.ws.AppAction.class,
      org.sonar.server.component.ws.SearchAction.class,
      EventsWs.class,
      NewAlerts.class,
      NewAlerts.newMetadata(),
      ComponentCleanerService.class,

      // views
      ViewIndexDefinition.class,
      ViewIndexer.class,
      ViewIndex.class,

      // issues
      IssueIndexDefinition.class,
      IssueIndexer.class,
      IssueAuthorizationIndexer.class,
      ServerIssueStorage.class,
      IssueUpdater.class,
      FunctionExecutor.class,
      IssueWorkflow.class,
      IssueCommentService.class,
      InternalRubyIssueService.class,
      IssueChangelogService.class,
      ActionService.class,
      Actions.class,
      IssueBulkChangeService.class,
      IssueChangelogFormatter.class,
      IssuesWs.class,
      org.sonar.server.issue.ws.ShowAction.class,
      org.sonar.server.issue.ws.SearchAction.class,
      org.sonar.server.issue.ws.TagsAction.class,
      SetTagsAction.class,
      ComponentTagsAction.class,
      IssueService.class,
      IssueActionsWriter.class,
      IssueQueryService.class,
      NewIssuesEmailTemplate.class,
      MyNewIssuesEmailTemplate.class,
      IssueChangesEmailTemplate.class,
      ChangesOnMyIssueNotificationDispatcher.class,
      ChangesOnMyIssueNotificationDispatcher.newMetadata(),
      NewIssuesNotificationDispatcher.class,
      NewIssuesNotificationDispatcher.newMetadata(),
      MyNewIssuesNotificationDispatcher.class,
      MyNewIssuesNotificationDispatcher.newMetadata(),
      DoNotFixNotificationDispatcher.class,
      DoNotFixNotificationDispatcher.newMetadata(),
      NewIssuesNotificationFactory.class,
      EmailNotificationChannel.class,
      AlertsEmailTemplate.class,

      // issue filters
      IssueFilterService.class,
      IssueFilterSerializer.class,
      IssueFilterWs.class,
      IssueFilterWriter.class,
      org.sonar.server.issue.filter.AppAction.class,
      org.sonar.server.issue.filter.ShowAction.class,
      org.sonar.server.issue.filter.FavoritesAction.class,

      // action plan
      ActionPlanWs.class,
      ActionPlanService.class,

      // issues actions
      AssignAction.class,
      PlanAction.class,
      SetSeverityAction.class,
      CommentAction.class,
      TransitionAction.class,
      AddTagsAction.class,
      RemoveTagsAction.class,

      // technical debt
      DebtModelService.class,
      DebtModelOperations.class,
      DebtModelLookup.class,
      DebtModelBackup.class,
      DebtModelPluginRepository.class,
      DebtModelXMLExporter.class,
      DebtRulesXMLImporter.class,
      DebtCharacteristicsXMLImporter.class,

      // source
      HtmlSourceDecorator.class,
      SourceService.class,
      SourcesWs.class,
      org.sonar.server.source.ws.ShowAction.class,
      LinesAction.class,
      HashAction.class,
      RawAction.class,
      IndexAction.class,
      ScmAction.class,
      SourceLineIndexDefinition.class,
      SourceLineIndex.class,
      SourceLineIndexer.class,

      // Duplications
      DuplicationsParser.class,
      DuplicationsWs.class,
      DuplicationsJsonWriter.class,
      org.sonar.server.duplication.ws.ShowAction.class,

      // text
      MacroInterpreter.class,
      RubyTextService.class,

      // Notifications
      EmailSettings.class,
      NotificationService.class,
      NotificationCenter.class,
      DefaultNotificationManager.class,

      // Tests
      CoverageService.class,
      TestsWs.class,
      CoveredFilesAction.class,
      org.sonar.server.test.ws.ListAction.class,
      TestIndexDefinition.class,
      TestIndex.class,
      TestIndexer.class,

      // Properties
      PropertiesWs.class,

      // Type validation
      TypeValidations.class,
      IntegerTypeValidation.class,
      FloatTypeValidation.class,
      BooleanTypeValidation.class,
      TextTypeValidation.class,
      StringTypeValidation.class,
      StringListTypeValidation.class,

      // System
      RestartAction.class,
      InfoAction.class,
      UpgradesAction.class,
      MigrateDbSystemAction.class,
      StatusAction.class,
      SystemWs.class,
      SystemMonitor.class,
      SonarQubeMonitor.class,
      EsMonitor.class,
      PluginsMonitor.class,
      JvmPropertiesMonitor.class,
      DatabaseMonitor.class,

      // Plugins WS
      PluginWSCommons.class,
      PluginUpdateAggregator.class,
      InstalledAction.class,
      AvailableAction.class,
      UpdatesAction.class,
      PendingAction.class,
      InstallAction.class,
      org.sonar.server.plugins.ws.UpdateAction.class,
      UninstallAction.class,
      CancelAllAction.class,
      PluginsWs.class,

      // Compute engine
      ReportQueue.class,
      ComputationThreadLauncher.class,
      ComputationWs.class,
      IsQueueEmptyWs.class,
      QueueAction.class,
      HistoryAction.class,
      DefaultPeriodCleaner.class,
      ProjectCleaner.class,
      ProjectSettingsFactory.class,
      IndexPurgeListener.class,

      // UI
      GlobalNavigationAction.class,
      SettingsNavigationAction.class,
      ComponentNavigationAction.class,
      NavigationWs.class);

    addAll(level4AddedComponents);
  }

  @Override
  public PlatformLevel start() {
    ServerExtensionInstaller extensionInstaller = getComponentByType(ServerExtensionInstaller.class);
    extensionInstaller.installExtensions(getContainer());

    super.start();

    return this;
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/metric/ws/CreateActionTest.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

package org.sonar.server.metric.ws;

import org.junit.After;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.experimental.categories.Category;
import org.junit.rules.ExpectedException;
import org.sonar.api.measures.Metric.ValueType;
import org.sonar.core.metric.db.MetricDto;
import org.sonar.core.permission.GlobalPermissions;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.persistence.DbTester;
import org.sonar.server.custommeasure.persistence.CustomMeasureDao;
import org.sonar.server.custommeasure.persistence.CustomMeasureTesting;
import org.sonar.server.db.DbClient;
import org.sonar.server.exceptions.ForbiddenException;
import org.sonar.server.exceptions.ServerException;
import org.sonar.server.metric.persistence.MetricDao;
import org.sonar.server.tester.UserSessionRule;
import org.sonar.server.ws.WsTester;
import org.sonar.test.DbTests;

import static org.assertj.core.api.Assertions.assertThat;
import static org.sonar.server.metric.ws.CreateAction.PARAM_DESCRIPTION;
import static org.sonar.server.metric.ws.CreateAction.PARAM_DOMAIN;
import static org.sonar.server.metric.ws.CreateAction.PARAM_KEY;
import static org.sonar.server.metric.ws.CreateAction.PARAM_NAME;
import static org.sonar.server.metric.ws.CreateAction.PARAM_TYPE;

@Category(DbTests.class)
public class CreateActionTest {

  private static final String DEFAULT_KEY = "custom-metric-key";
  private static final String DEFAULT_NAME = "custom-metric-name";
  private static final String DEFAULT_DOMAIN = "custom-metric-domain";
  private static final String DEFAULT_DESCRIPTION = "custom-metric-description";
  private static final String DEFAULT_TYPE = ValueType.INT.name();

  @ClassRule
  public static DbTester db = new DbTester();
  @Rule
  public ExpectedException expectedException = ExpectedException.none();
  @Rule
  public UserSessionRule userSessionRule = UserSessionRule.standalone();
  WsTester ws;
  DbClient dbClient;
  DbSession dbSession;

  @Before
  public void setUp() {
    dbClient = new DbClient(db.database(), db.myBatis(), new MetricDao(), new CustomMeasureDao());
    dbSession = dbClient.openSession(false);
    db.truncateTables();

    ws = new WsTester(new MetricsWs(new CreateAction(dbClient, userSessionRule)));
    userSessionRule.login("login").setGlobalPermissions(GlobalPermissions.SYSTEM_ADMIN);
  }

  @After
  public void tearDown() {
    dbSession.close();
  }

  @Test
  public void insert_new_minimalist_metric() throws Exception {
    newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, DEFAULT_NAME)
      .setParam(PARAM_TYPE, DEFAULT_TYPE)
      .execute();

    MetricDto metric = dbClient.metricDao().selectNullableByKey(dbSession, DEFAULT_KEY);

    assertThat(metric.getKey()).isEqualTo(DEFAULT_KEY);
    assertThat(metric.getShortName()).isEqualTo(DEFAULT_NAME);
    assertThat(metric.getValueType()).isEqualTo(DEFAULT_TYPE);
    assertThat(metric.getDescription()).isNull();
    assertThat(metric.getDomain()).isNull();
    assertThat(metric.isUserManaged()).isTrue();
    assertThat(metric.isEnabled()).isTrue();
    assertThat(metric.getDirection()).isEqualTo(0);
    assertThat(metric.isQualitative()).isFalse();
  }

  @Test
  public void insert_new_full_metric() throws Exception {
    newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, DEFAULT_NAME)
      .setParam(PARAM_TYPE, DEFAULT_TYPE)
      .setParam(PARAM_DOMAIN, DEFAULT_DOMAIN)
      .setParam(PARAM_DESCRIPTION, DEFAULT_DESCRIPTION)
      .execute();

    MetricDto metric = dbClient.metricDao().selectNullableByKey(dbSession, DEFAULT_KEY);

    assertThat(metric.getKey()).isEqualTo(DEFAULT_KEY);
    assertThat(metric.getDescription()).isEqualTo(DEFAULT_DESCRIPTION);
    assertThat(metric.getDomain()).isEqualTo(DEFAULT_DOMAIN);
  }

  @Test
  public void return_metric_with_id() throws Exception {
    WsTester.Result result = newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, DEFAULT_NAME)
      .setParam(PARAM_TYPE, DEFAULT_TYPE)
      .setParam(PARAM_DOMAIN, DEFAULT_DOMAIN)
      .setParam(PARAM_DESCRIPTION, DEFAULT_DESCRIPTION)
      .execute();

    result.assertJson(getClass(), "metric.json");
    assertThat(result.outputAsString()).matches(".*\"id\"\\s*:\\s*\"\\w+\".*");
  }

  @Test
  public void update_existing_metric_when_custom_and_disabled() throws Exception {
    MetricDto metricInDb = MetricTesting.newMetricDto()
      .setKey(DEFAULT_KEY)
      .setValueType(ValueType.BOOL.name())
      .setUserManaged(true)
      .setEnabled(false);
    dbClient.metricDao().insert(dbSession, metricInDb);
    dbSession.commit();

    WsTester.Result result = newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, DEFAULT_NAME)
      .setParam(PARAM_TYPE, DEFAULT_TYPE)
      .setParam(PARAM_DESCRIPTION, DEFAULT_DESCRIPTION)
      .setParam(PARAM_DOMAIN, DEFAULT_DOMAIN)
      .execute();

    result.assertJson(getClass(), "metric.json");
    result.outputAsString().matches("\"id\"\\s*:\\s*\"" + metricInDb.getId() + "\"");
    MetricDto metricAfterWs = dbClient.metricDao().selectNullableByKey(dbSession, DEFAULT_KEY);
    assertThat(metricAfterWs.getId()).isEqualTo(metricInDb.getId());
    assertThat(metricAfterWs.getDomain()).isEqualTo(DEFAULT_DOMAIN);
    assertThat(metricAfterWs.getDescription()).isEqualTo(DEFAULT_DESCRIPTION);
    assertThat(metricAfterWs.getValueType()).isEqualTo(DEFAULT_TYPE);
    assertThat(metricAfterWs.getShortName()).isEqualTo(DEFAULT_NAME);
  }

  @Test
  public void fail_when_existing_activated_metric_with_same_key() throws Exception {
    expectedException.expect(ServerException.class);
    dbClient.metricDao().insert(dbSession, MetricTesting.newMetricDto()
      .setKey(DEFAULT_KEY)
      .setValueType(DEFAULT_TYPE)
      .setUserManaged(true)
      .setEnabled(true));
    dbSession.commit();

    newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, "any-name")
      .setParam(PARAM_TYPE, DEFAULT_TYPE).execute();
  }

  @Test
  public void fail_when_existing_non_custom_metric_with_same_key() throws Exception {
    expectedException.expect(ServerException.class);
    dbClient.metricDao().insert(dbSession, MetricTesting.newMetricDto()
      .setKey(DEFAULT_KEY)
      .setValueType(DEFAULT_TYPE)
      .setUserManaged(false)
      .setEnabled(false));
    dbSession.commit();

    newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, "any-name")
      .setParam(PARAM_TYPE, DEFAULT_TYPE).execute();
  }

  @Test
  public void fail_when_metric_type_is_changed_and_associated_measures_exist() throws Exception {
    expectedException.expect(ServerException.class);
    MetricDto metric = MetricTesting.newMetricDto()
      .setKey(DEFAULT_KEY)
      .setValueType(ValueType.BOOL.name())
      .setUserManaged(true)
      .setEnabled(false);
    dbClient.metricDao().insert(dbSession, metric);
    dbClient.customMeasureDao().insert(dbSession, CustomMeasureTesting.newCustomMeasureDto().setMetricId(metric.getId()));
    dbSession.commit();

    newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, "any-name")
      .setParam(PARAM_TYPE, ValueType.INT.name())
      .execute();
  }

  @Test
  public void fail_when_missing_key() throws Exception {
    expectedException.expect(IllegalArgumentException.class);

    newRequest()
      .setParam(PARAM_NAME, DEFAULT_NAME)
      .setParam(PARAM_TYPE, DEFAULT_TYPE).execute();
  }

  @Test
  public void fail_when_missing_name() throws Exception {
    expectedException.expect(IllegalArgumentException.class);

    newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_TYPE, DEFAULT_TYPE).execute();
  }

  @Test
  public void fail_when_missing_type() throws Exception {
    expectedException.expect(IllegalArgumentException.class);

    newRequest()
      .setParam(PARAM_NAME, DEFAULT_NAME)
      .setParam(PARAM_KEY, DEFAULT_KEY).execute();
  }

  @Test
  public void fail_when_insufficient_privileges() throws Exception {
    expectedException.expect(ForbiddenException.class);
    userSessionRule.login("login");

    newRequest()
      .setParam(PARAM_KEY, "any-key")
      .setParam(PARAM_NAME, "any-name")
      .setParam(PARAM_TYPE, DEFAULT_TYPE)
      .execute();
  }

  @Test
  public void fail_when_empty_key() throws Exception {
    expectedException.expect(IllegalArgumentException.class);

    newRequest()
      .setParam(PARAM_KEY, "")
      .setParam(PARAM_NAME, DEFAULT_NAME)
      .setParam(PARAM_TYPE, DEFAULT_TYPE)
      .execute();
  }

  @Test
  public void fail_when_empty_name() throws Exception {
    expectedException.expect(IllegalArgumentException.class);

    newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, "")
      .setParam(PARAM_TYPE, DEFAULT_TYPE)
      .execute();
  }

  @Test
  public void fail_when_empty_type() throws Exception {
    expectedException.expect(IllegalArgumentException.class);

    newRequest()
      .setParam(PARAM_KEY, DEFAULT_KEY)
      .setParam(PARAM_NAME, DEFAULT_NAME)
      .setParam(PARAM_TYPE, "")
      .execute();
  }

  private WsTester.TestRequest newRequest() {
    return ws.newPostRequest("api/metrics", "create");
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/metric/ws/DeleteActionTest.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

package org.sonar.server.metric.ws;

import java.util.Arrays;
import java.util.List;
import org.junit.After;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.experimental.categories.Category;
import org.junit.rules.ExpectedException;
import org.sonar.core.custommeasure.db.CustomMeasureDto;
import org.sonar.core.metric.db.MetricDto;
import org.sonar.core.permission.GlobalPermissions;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.persistence.DbTester;
import org.sonar.server.custommeasure.persistence.CustomMeasureDao;
import org.sonar.server.custommeasure.persistence.CustomMeasureTesting;
import org.sonar.server.db.DbClient;
import org.sonar.server.exceptions.ForbiddenException;
import org.sonar.server.metric.persistence.MetricDao;
import org.sonar.server.tester.UserSessionRule;
import org.sonar.server.ws.WsTester;
import org.sonar.test.DbTests;

import static org.assertj.core.api.Assertions.assertThat;
import static org.sonar.server.metric.ws.MetricTesting.newMetricDto;

@Category(DbTests.class)
public class DeleteActionTest {

  @ClassRule
  public static DbTester db = new DbTester();
  @Rule
  public UserSessionRule userSessionRule = UserSessionRule.standalone();
  @Rule
  public ExpectedException expectedException = ExpectedException.none();
  DbClient dbClient;
  DbSession dbSession;
  WsTester ws;
  MetricDao metricDao;

  @Before
  public void setUp() throws Exception {
    dbClient = new DbClient(db.database(), db.myBatis(), new MetricDao(), new CustomMeasureDao());
    dbSession = dbClient.openSession(false);
    db.truncateTables();
    userSessionRule.login("login").setGlobalPermissions(GlobalPermissions.SYSTEM_ADMIN);
    ws = new WsTester(new MetricsWs(new DeleteAction(dbClient, userSessionRule)));
    metricDao = dbClient.metricDao();
  }

  @After
  public void tearDown() throws Exception {
    dbSession.close();
  }

  @Test
  public void delete_by_keys() throws Exception {
    insertCustomEnabledMetrics(1, 2, 3);
    dbSession.commit();

    newRequest().setParam("keys", "key-1, key-3").execute();
    dbSession.commit();

    List<MetricDto> disabledMetrics = metricDao.selectNullableByKeys(dbSession, Arrays.asList("key-1", "key-3"));
    assertThat(disabledMetrics).extracting("enabled").containsOnly(false);
    assertThat(metricDao.selectNullableByKey(dbSession, "key-2").isEnabled()).isTrue();
  }

  @Test
  public void delete_by_id() throws Exception {
    MetricDto metric = newCustomEnabledMetric(1);
    metricDao.insert(dbSession, metric);
    dbSession.commit();

    WsTester.Result result = newRequest().setParam("ids", String.valueOf(metric.getId())).execute();
    dbSession.commit();

    assertThat(metricDao.selectEnabled(dbSession)).isEmpty();
    result.assertNoContent();
  }

  @Test
  public void do_not_delete_non_custom_metric() throws Exception {
    metricDao.insert(dbSession, newCustomEnabledMetric(1).setUserManaged(false));
    dbSession.commit();

    newRequest().setParam("keys", "key-1").execute();
    dbSession.commit();

    MetricDto metric = metricDao.selectNullableByKey(dbSession, "key-1");
    assertThat(metric.isEnabled()).isTrue();
  }

  @Test
  public void delete_associated_measures() throws Exception {
    MetricDto metric = newCustomEnabledMetric(1);
    metricDao.insert(dbSession, metric);
    CustomMeasureDto customMeasure = CustomMeasureTesting.newCustomMeasureDto().setMetricId(metric.getId());
    CustomMeasureDto undeletedCustomMeasure = CustomMeasureTesting.newCustomMeasureDto().setMetricId(metric.getId() + 1);
    dbClient.customMeasureDao().insert(dbSession, customMeasure);
    dbClient.customMeasureDao().insert(dbSession, undeletedCustomMeasure);
    dbSession.commit();

    newRequest().setParam("keys", "key-1").execute();

    assertThat(dbClient.customMeasureDao().selectNullableById(dbSession, customMeasure.getId())).isNull();
    assertThat(dbClient.customMeasureDao().selectNullableById(dbSession, undeletedCustomMeasure.getId())).isNotNull();
  }

  @Test
  public void fail_when_no_argument() throws Exception {
    expectedException.expect(IllegalArgumentException.class);

    newRequest().execute();
  }

  @Test
  public void fail_when_insufficient_privileges() throws Exception {
    expectedException.expect(ForbiddenException.class);

    userSessionRule.setGlobalPermissions(GlobalPermissions.SCAN_EXECUTION);
    insertCustomEnabledMetrics(1);

    newRequest().setParam("keys", "key-1").execute();
  }

  private MetricDto newCustomEnabledMetric(int id) {
    return newMetricDto().setEnabled(true).setUserManaged(true).setKey("key-" + id);
  }

  private void insertCustomEnabledMetrics(int... ids) {
    for (int id : ids) {
      metricDao.insert(dbSession, newCustomEnabledMetric(id));
    }

    dbSession.commit();
  }

  private WsTester.TestRequest newRequest() {
    return ws.newPostRequest(MetricsWs.ENDPOINT, "delete");
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/metric/ws/UpdateActionTest.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

package org.sonar.server.metric.ws;

import org.junit.After;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.experimental.categories.Category;
import org.junit.rules.ExpectedException;
import org.sonar.api.measures.Metric.ValueType;
import org.sonar.core.metric.db.MetricDto;
import org.sonar.core.permission.GlobalPermissions;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.persistence.DbTester;
import org.sonar.server.custommeasure.persistence.CustomMeasureDao;
import org.sonar.server.db.DbClient;
import org.sonar.server.exceptions.ForbiddenException;
import org.sonar.server.exceptions.ServerException;
import org.sonar.server.metric.persistence.MetricDao;
import org.sonar.server.tester.UserSessionRule;
import org.sonar.server.ws.WsTester;
import org.sonar.test.DbTests;

import static org.assertj.core.api.Assertions.assertThat;
import static org.sonar.server.custommeasure.persistence.CustomMeasureTesting.newCustomMeasureDto;
import static org.sonar.server.metric.ws.UpdateAction.PARAM_DESCRIPTION;
import static org.sonar.server.metric.ws.UpdateAction.PARAM_DOMAIN;
import static org.sonar.server.metric.ws.UpdateAction.PARAM_ID;
import static org.sonar.server.metric.ws.UpdateAction.PARAM_KEY;
import static org.sonar.server.metric.ws.UpdateAction.PARAM_NAME;
import static org.sonar.server.metric.ws.UpdateAction.PARAM_TYPE;

@Category(DbTests.class)
public class UpdateActionTest {

  private static final String DEFAULT_KEY = "custom-metric-key";
  private static final String DEFAULT_NAME = "custom-metric-name";
  private static final String DEFAULT_DOMAIN = "custom-metric-domain";
  private static final String DEFAULT_DESCRIPTION = "custom-metric-description";
  private static final String DEFAULT_TYPE = ValueType.INT.name();

  @ClassRule
  public static DbTester db = new DbTester();
  @Rule
  public ExpectedException expectedException = ExpectedException.none();
  @Rule
  public UserSessionRule userSessionRule = UserSessionRule.standalone();
  WsTester ws;
  DbClient dbClient;
  DbSession dbSession;

  @Before
  public void setUp() {
    dbClient = new DbClient(db.database(), db.myBatis(), new MetricDao(), new CustomMeasureDao());
    dbSession = dbClient.openSession(false);
    db.truncateTables();

    ws = new WsTester(new MetricsWs(new UpdateAction(dbClient, userSessionRule)));
    userSessionRule.login("login").setGlobalPermissions(GlobalPermissions.SYSTEM_ADMIN);
  }

  @After
  public void tearDown() {
    dbSession.close();
  }

  @Test
  public void update_all_fields() throws Exception {
    int id = insertMetric(newDefaultMetric());

    newRequest()
      .setParam(PARAM_ID, String.valueOf(id))
      .setParam(PARAM_KEY, "another-key")
      .setParam(PARAM_NAME, "another-name")
      .setParam(PARAM_TYPE, ValueType.BOOL.name())
      .setParam(PARAM_DOMAIN, "another-domain")
      .setParam(PARAM_DESCRIPTION, "another-description")
      .execute();
    dbSession.commit();

    MetricDto result = dbClient.metricDao().selectNullableById(dbSession, id);
    assertThat(result.getKey()).isEqualTo("another-key");
    assertThat(result.getShortName()).isEqualTo("another-name");
    assertThat(result.getValueType()).isEqualTo(ValueType.BOOL.name());
    assertThat(result.getDomain()).isEqualTo("another-domain");
    assertThat(result.getDescription()).isEqualTo("another-description");
  }

  @Test
  public void update_one_field() throws Exception {
    int id = insertMetric(newDefaultMetric());
    dbClient.customMeasureDao().insert(dbSession, newCustomMeasureDto().setMetricId(id));
    dbSession.commit();

    newRequest()
      .setParam(PARAM_ID, String.valueOf(id))
      .setParam(PARAM_DESCRIPTION, "another-description")
      .execute();
    dbSession.commit();

    MetricDto result = dbClient.metricDao().selectNullableById(dbSession, id);
    assertThat(result.getKey()).isEqualTo(DEFAULT_KEY);
    assertThat(result.getShortName()).isEqualTo(DEFAULT_NAME);
    assertThat(result.getValueType()).isEqualTo(DEFAULT_TYPE);
    assertThat(result.getDomain()).isEqualTo(DEFAULT_DOMAIN);
    assertThat(result.getDescription()).isEqualTo("another-description");
  }

  @Test
  public void update_return_the_full_object_with_id() throws Exception {
    int id = insertMetric(newDefaultMetric().setDescription("another-description"));

    WsTester.Result requestResult = newRequest()
      .setParam(PARAM_ID, String.valueOf(id))
      .setParam(PARAM_DESCRIPTION, DEFAULT_DESCRIPTION)
      .execute();
    dbSession.commit();

    requestResult.assertJson(getClass(), "metric.json");
    assertThat(requestResult.outputAsString()).matches(".*\"id\"\\s*:\\s*\"" + id + "\".*");
  }

  @Test
  public void fail_when_changing_key_for_an_existing_one() throws Exception {
    expectedException.expect(ServerException.class);
    expectedException.expectMessage("The key 'metric-key' is already used by an existing metric.");
    insertMetric(newDefaultMetric().setKey("metric-key"));
    int id = insertMetric(newDefaultMetric().setKey("another-key"));

    newRequest()
      .setParam(PARAM_ID, String.valueOf(id))
      .setParam(PARAM_KEY, "metric-key")
      .execute();
  }

  @Test
  public void fail_when_metric_not_in_db() throws Exception {
    expectedException.expect(ServerException.class);

    newRequest().setParam(PARAM_ID, "42").execute();
  }

  @Test
  public void fail_when_metric_is_deactivated() throws Exception {
    expectedException.expect(ServerException.class);
    int id = insertMetric(newDefaultMetric().setEnabled(false));

    newRequest().setParam(PARAM_ID, String.valueOf(id)).execute();
  }

  @Test
  public void fail_when_metric_is_not_custom() throws Exception {
    expectedException.expect(ServerException.class);
    int id = insertMetric(newDefaultMetric().setUserManaged(false));

    newRequest().setParam(PARAM_ID, String.valueOf(id)).execute();
  }

  @Test
  public void fail_when_custom_measures_and_type_changed() throws Exception {
    expectedException.expect(ServerException.class);
    int id = insertMetric(newDefaultMetric());
    dbClient.customMeasureDao().insert(dbSession, newCustomMeasureDto().setMetricId(id));
    dbSession.commit();

    newRequest()
      .setParam(PARAM_ID, String.valueOf(id))
      .setParam(PARAM_TYPE, ValueType.BOOL.name())
      .execute();
  }

  @Test
  public void fail_when_no_id() throws Exception {
    expectedException.expect(IllegalArgumentException.class);

    newRequest().execute();
  }

  @Test
  public void fail_when_insufficient_privileges() throws Exception {
    expectedException.expect(ForbiddenException.class);
    userSessionRule.login("login");

    newRequest().execute();
  }

  private MetricDto newDefaultMetric() {
    return new MetricDto()
      .setKey(DEFAULT_KEY)
      .setShortName(DEFAULT_NAME)
      .setValueType(DEFAULT_TYPE)
      .setDomain(DEFAULT_DOMAIN)
      .setDescription(DEFAULT_DESCRIPTION)
      .setUserManaged(true)
      .setEnabled(true);
  }

  private int insertMetric(MetricDto metricDto) {
    dbClient.metricDao().insert(dbSession, metricDto);
    dbSession.commit();
    return metricDto.getId();
  }

  private WsTester.TestRequest newRequest() {
    return ws.newPostRequest("api/metrics", "update");
  }
}
