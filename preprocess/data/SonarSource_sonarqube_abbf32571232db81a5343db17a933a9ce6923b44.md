Refactoring Types: ['Rename Package']
ava/org/sonar/server/computation/step/SendIssueNotificationsStep.java
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
package org.sonar.server.computation.step;

import com.google.common.collect.ImmutableSet;
import java.util.Date;
import java.util.Map;
import java.util.Set;
import org.sonar.api.issue.internal.DefaultIssue;
import org.sonar.server.computation.batch.BatchReportReader;
import org.sonar.server.computation.component.Component;
import org.sonar.server.computation.component.TreeRootHolder;
import org.sonar.server.computation.issue.IssueCache;
import org.sonar.server.computation.issue.RuleCache;
import org.sonar.server.issue.notification.IssueChangeNotification;
import org.sonar.server.issue.notification.MyNewIssuesNotification;
import org.sonar.server.issue.notification.NewIssuesNotification;
import org.sonar.server.issue.notification.NewIssuesNotificationFactory;
import org.sonar.server.issue.notification.NewIssuesStatistics;
import org.sonar.server.notifications.NotificationService;
import org.sonar.server.util.CloseableIterator;

/**
 * Reads issues from disk cache and send related notifications. For performance reasons,
 * the standard notification DB queue is not used as a temporary storage. Notifications
 * are directly processed by {@link org.sonar.server.notifications.NotificationService}.
 */
public class SendIssueNotificationsStep implements ComputationStep {
  /**
   * Types of the notifications sent by this step
   */
  static final Set<String> NOTIF_TYPES = ImmutableSet.of(IssueChangeNotification.TYPE, NewIssuesNotification.TYPE, MyNewIssuesNotification.MY_NEW_ISSUES_NOTIF_TYPE);

  private final IssueCache issueCache;
  private final RuleCache rules;
  private final TreeRootHolder treeRootHolder;
  private final NotificationService service;
  private final BatchReportReader reportReader;
  private NewIssuesNotificationFactory newIssuesNotificationFactory;

  public SendIssueNotificationsStep(IssueCache issueCache, RuleCache rules, TreeRootHolder treeRootHolder, NotificationService service,
    BatchReportReader reportReader, NewIssuesNotificationFactory newIssuesNotificationFactory) {
    this.issueCache = issueCache;
    this.rules = rules;
    this.treeRootHolder = treeRootHolder;
    this.service = service;
    this.reportReader = reportReader;
    this.newIssuesNotificationFactory = newIssuesNotificationFactory;
  }

  @Override
  public void execute() {
    Component project = treeRootHolder.getRoot();
    if (service.hasProjectSubscribersForTypes(project.getUuid(), NOTIF_TYPES)) {
      doExecute(project);
    }
  }

  private void doExecute(Component project) {
    NewIssuesStatistics newIssuesStats = new NewIssuesStatistics();
    CloseableIterator<DefaultIssue> issues = issueCache.traverse();
    String projectName = reportReader.readComponent(reportReader.readMetadata().getRootComponentRef()).getName();
    try {
      while (issues.hasNext()) {
        DefaultIssue issue = issues.next();
        if (issue.isNew() && issue.resolution() == null) {
          newIssuesStats.add(issue);
        } else if (issue.isChanged() && issue.mustSendNotifications()) {
          IssueChangeNotification changeNotification = new IssueChangeNotification();
          changeNotification.setRuleName(rules.ruleName(issue.ruleKey()));
          changeNotification.setIssue(issue);
          changeNotification.setProject(project.getKey(), projectName);
          service.deliver(changeNotification);
        }
      }

    } finally {
      issues.close();
    }
    sendNewIssuesStatistics(newIssuesStats, project, projectName);
  }

  private void sendNewIssuesStatistics(NewIssuesStatistics statistics, Component project, String projectName) {
    if (statistics.hasIssues()) {
      NewIssuesStatistics.Stats globalStatistics = statistics.globalStatistics();
      long analysisDate = reportReader.readMetadata().getAnalysisDate();
      NewIssuesNotification notification = newIssuesNotificationFactory
        .newNewIssuesNotication()
        .setProject(project.getKey(), project.getUuid(), projectName)
        .setAnalysisDate(new Date(analysisDate))
        .setStatistics(projectName, globalStatistics)
        .setDebt(globalStatistics.debt());
      service.deliver(notification);

      // send email to each user having issues
      for (Map.Entry<String, NewIssuesStatistics.Stats> assigneeAndStatisticsTuple : statistics.assigneesStatistics().entrySet()) {
        String assignee = assigneeAndStatisticsTuple.getKey();
        NewIssuesStatistics.Stats assigneeStatistics = assigneeAndStatisticsTuple.getValue();
        MyNewIssuesNotification myNewIssuesNotification = newIssuesNotificationFactory
          .newMyNewIssuesNotification()
          .setAssignee(assignee);
        myNewIssuesNotification
          .setProject(project.getKey(), project.getUuid(), projectName)
          .setAnalysisDate(new Date(analysisDate))
          .setStatistics(projectName, assigneeStatistics)
          .setDebt(assigneeStatistics.debt());

        service.deliver(myNewIssuesNotification);
      }
    }
  }

  @Override
  public String getDescription() {
    return "Send issue notifications";
  }

}


File: server/sonar-server/src/main/java/org/sonar/server/event/NewAlerts.java
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
package org.sonar.server.event;

import com.google.common.collect.Multimap;
import org.sonar.api.notifications.*;

import java.util.Collection;
import java.util.Map;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationDispatcherMetadata;
import org.sonar.core.notification.NotificationManager;

/**
 * This dispatcher means: "notify me each new alert event".
 *
 * @since 3.5
 */
public class NewAlerts extends NotificationDispatcher {

  public static final String KEY = "NewAlerts";
  private final NotificationManager notifications;

  public NewAlerts(NotificationManager notifications) {
    super("alerts");
    this.notifications = notifications;
  }

  @Override
  public String getKey() {
    return KEY;
  }

  public static NotificationDispatcherMetadata newMetadata() {
    return NotificationDispatcherMetadata.create(KEY)
      .setProperty(NotificationDispatcherMetadata.GLOBAL_NOTIFICATION, String.valueOf(true))
      .setProperty(NotificationDispatcherMetadata.PER_PROJECT_NOTIFICATION, String.valueOf(true));
  }

  @Override
  public void dispatch(Notification notification, Context context) {
    String projectIdString = notification.getFieldValue("projectId");
    if (projectIdString != null) {
      int projectId = Integer.parseInt(projectIdString);
      Multimap<String, NotificationChannel> subscribedRecipients = notifications.findSubscribedRecipientsForDispatcher(this, projectId);

      for (Map.Entry<String, Collection<NotificationChannel>> channelsByRecipients : subscribedRecipients.asMap().entrySet()) {
        String userLogin = channelsByRecipients.getKey();
        for (NotificationChannel channel : channelsByRecipients.getValue()) {
          context.addUser(userLogin, channel);
        }
      }
    }
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/issue/IssueBulkChangeService.java
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

package org.sonar.server.issue;

import com.google.common.base.Function;
import com.google.common.base.Predicate;
import com.google.common.collect.Collections2;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.CheckForNull;
import javax.annotation.Nullable;
import org.sonar.api.issue.Issue;
import org.sonar.api.issue.internal.DefaultIssue;
import org.sonar.api.issue.internal.IssueChangeContext;
import org.sonar.api.rule.RuleKey;
import org.sonar.api.rules.Rule;
import org.sonar.api.utils.log.Logger;
import org.sonar.api.utils.log.Loggers;
import org.sonar.core.component.ComponentDto;
import org.sonar.core.issue.db.IssueDto;
import org.sonar.core.issue.db.IssueStorage;
import org.sonar.core.notification.NotificationManager;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.persistence.MyBatis;
import org.sonar.server.db.DbClient;
import org.sonar.server.es.SearchOptions;
import org.sonar.server.exceptions.BadRequestException;
import org.sonar.server.issue.index.IssueDoc;
import org.sonar.server.issue.notification.IssueChangeNotification;
import org.sonar.server.rule.DefaultRuleFinder;
import org.sonar.server.user.UserSession;

import static com.google.common.collect.Lists.newArrayList;
import static com.google.common.collect.Maps.newHashMap;
import static com.google.common.collect.Sets.newHashSet;

public class IssueBulkChangeService {

  private static final Logger LOG = Loggers.get(IssueBulkChangeService.class);

  private final DbClient dbClient;
  private final IssueService issueService;
  private final IssueStorage issueStorage;
  private final DefaultRuleFinder ruleFinder;
  private final NotificationManager notificationService;
  private final List<Action> actions;
  private final UserSession userSession;

  public IssueBulkChangeService(DbClient dbClient, IssueService issueService, IssueStorage issueStorage, DefaultRuleFinder ruleFinder,
    NotificationManager notificationService, List<Action> actions, UserSession userSession) {
    this.dbClient = dbClient;
    this.issueService = issueService;
    this.issueStorage = issueStorage;
    this.ruleFinder = ruleFinder;
    this.notificationService = notificationService;
    this.actions = actions;
    this.userSession = userSession;
  }

  public IssueBulkChangeResult execute(IssueBulkChangeQuery issueBulkChangeQuery, UserSession userSession) {
    LOG.debug("BulkChangeQuery : {}", issueBulkChangeQuery);
    long start = System.currentTimeMillis();
    userSession.checkLoggedIn();

    IssueBulkChangeResult result = new IssueBulkChangeResult();

    Collection<Issue> issues = getByKeysForUpdate(issueBulkChangeQuery.issues());
    Repository repository = new Repository(issues);

    List<Action> bulkActions = getActionsToApply(issueBulkChangeQuery, issues, userSession);
    IssueChangeContext issueChangeContext = IssueChangeContext.createUser(new Date(), userSession.getLogin());
    Set<String> concernedProjects = new HashSet<>();
    for (Issue issue : issues) {
      ActionContext actionContext = new ActionContext(issue, issueChangeContext);
      for (Action action : bulkActions) {
        applyAction(action, actionContext, issueBulkChangeQuery, result);
      }
      if (result.issuesChanged().contains(issue)) {
        // Apply comment action only on changed issues
        if (issueBulkChangeQuery.hasComment()) {
          applyAction(getAction(CommentAction.KEY), actionContext, issueBulkChangeQuery, result);
        }
        issueStorage.save((DefaultIssue) issue);
        if (issueBulkChangeQuery.sendNotifications()) {
          String projectKey = issue.projectKey();
          if (projectKey != null) {
            Rule rule = repository.rule(issue.ruleKey());
            notificationService.scheduleForSending(new IssueChangeNotification()
              .setIssue((DefaultIssue) issue)
              .setChangeAuthorLogin(issueChangeContext.login())
              .setRuleName(rule != null ? rule.getName() : null)
              .setProject(projectKey, repository.project(projectKey).name())
              .setComponent(repository.component(issue.componentKey())));
          }
        }
        concernedProjects.add(issue.projectKey());
      }
    }
    LOG.debug("BulkChange execution time : {} ms", System.currentTimeMillis() - start);
    return result;
  }

  private Collection<Issue> getByKeysForUpdate(List<String> issueKeys) {
    // Load from index to check permission
    SearchOptions options = new SearchOptions().setLimit(SearchOptions.MAX_LIMIT);
    // TODO restrict fields to issue key, in order to not load all other fields;
    List<IssueDoc> authorizedIssues = issueService.search(IssueQuery.builder(userSession).issueKeys(issueKeys).build(), options).getDocs();
    Collection<String> authorizedKeys = Collections2.transform(authorizedIssues, new Function<IssueDoc, String>() {
      @Override
      public String apply(IssueDoc input) {
        return input.key();
      }
    });

    if (!authorizedKeys.isEmpty()) {
      DbSession session = dbClient.openSession(false);
      try {
        List<IssueDto> dtos = dbClient.issueDao().selectByKeys(session, Lists.newArrayList(authorizedKeys));
        return Collections2.transform(dtos, new Function<IssueDto, Issue>() {
          @Override
          public Issue apply(@Nullable IssueDto input) {
            return input != null ? input.toDefaultIssue() : null;
          }
        });
      } finally {
        MyBatis.closeQuietly(session);
      }
    }
    return Collections.emptyList();
  }

  private List<Action> getActionsToApply(IssueBulkChangeQuery issueBulkChangeQuery, Collection<Issue> issues, UserSession userSession) {
    List<Action> bulkActions = newArrayList();
    for (String actionKey : issueBulkChangeQuery.actions()) {
      Action action = getAction(actionKey);
      if (action.verify(issueBulkChangeQuery.properties(actionKey), issues, userSession)) {
        bulkActions.add(action);
      }
    }
    return bulkActions;
  }

  private static void applyAction(Action action, ActionContext actionContext, IssueBulkChangeQuery issueBulkChangeQuery, IssueBulkChangeResult result) {
    Issue issue = actionContext.issue();
    try {
      if (action.supports(issue) && action.execute(issueBulkChangeQuery.properties(action.key()), actionContext)) {
        result.addIssueChanged(issue);
      } else {
        result.addIssueNotChanged(issue);
      }
    } catch (Exception e) {
      result.addIssueNotChanged(issue);
      LOG.info("An error occur when trying to apply the action : " + action.key() + " on issue : " + issue.key() + ". This issue has been ignored.", e);
    }
  }

  private Action getAction(final String actionKey) {
    Action action = Iterables.find(actions, new Predicate<Action>() {
      @Override
      public boolean apply(Action action) {
        return action.key().equals(actionKey);
      }
    }, null);
    if (action == null) {
      throw new BadRequestException("The action : '" + actionKey + "' is unknown");
    }
    return action;
  }

  static class ActionContext implements Action.Context {
    private final Issue issue;
    private final IssueChangeContext changeContext;

    ActionContext(Issue issue, IssueChangeContext changeContext) {
      this.issue = issue;
      this.changeContext = changeContext;
    }

    @Override
    public Issue issue() {
      return issue;
    }

    @Override
    public IssueChangeContext issueChangeContext() {
      return changeContext;
    }
  }

  private class Repository {

    private final Map<RuleKey, Rule> rules = newHashMap();
    private final Map<String, ComponentDto> components = newHashMap();
    private final Map<String, ComponentDto> projects = newHashMap();

    public Repository(Collection<Issue> issues) {
      Set<RuleKey> ruleKeys = newHashSet();
      Set<String> componentKeys = newHashSet();
      Set<String> projectKeys = newHashSet();

      for (Issue issue : issues) {
        ruleKeys.add(issue.ruleKey());
        componentKeys.add(issue.componentKey());
        String projectKey = issue.projectKey();
        if (projectKey != null) {
          projectKeys.add(projectKey);
        }
      }

      DbSession session = dbClient.openSession(false);
      try {
        for (Rule rule : ruleFinder.findByKeys(ruleKeys)) {
          rules.put(rule.ruleKey(), rule);
        }

        for (ComponentDto file : dbClient.componentDao().selectByKeys(session, componentKeys)) {
          components.put(file.getKey(), file);
        }

        for (ComponentDto project : dbClient.componentDao().selectByKeys(session, projectKeys)) {
          projects.put(project.getKey(), project);
        }
      } finally {
        session.close();
      }
    }

    public Rule rule(RuleKey ruleKey) {
      return rules.get(ruleKey);
    }

    @CheckForNull
    public ComponentDto component(String key) {
      return components.get(key);
    }

    public ComponentDto project(String key) {
      return projects.get(key);
    }
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/issue/IssueService.java
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
package org.sonar.server.issue;

import com.google.common.base.Objects;
import com.google.common.base.Strings;
import org.apache.commons.lang.StringUtils;
import org.sonar.api.issue.ActionPlan;
import org.sonar.api.issue.Issue;
import org.sonar.api.issue.internal.DefaultIssue;
import org.sonar.api.issue.internal.IssueChangeContext;
import org.sonar.core.notification.NotificationManager;
import org.sonar.api.rule.RuleKey;
import org.sonar.api.rule.Severity;
import org.sonar.api.rules.Rule;
import org.sonar.api.rules.RuleFinder;
import org.sonar.api.server.ServerSide;
import org.sonar.api.user.User;
import org.sonar.api.user.UserFinder;
import org.sonar.api.web.UserRole;
import org.sonar.core.component.ComponentDto;
import org.sonar.core.issue.DefaultIssueBuilder;
import org.sonar.core.issue.IssueUpdater;
import org.sonar.core.issue.db.IssueDto;
import org.sonar.core.issue.db.IssueStorage;
import org.sonar.core.issue.workflow.IssueWorkflow;
import org.sonar.core.issue.workflow.Transition;
import org.sonar.core.persistence.DbSession;
import org.sonar.server.db.DbClient;
import org.sonar.server.es.SearchOptions;
import org.sonar.server.es.SearchResult;
import org.sonar.server.exceptions.NotFoundException;
import org.sonar.server.issue.actionplan.ActionPlanService;
import org.sonar.server.issue.index.IssueDoc;
import org.sonar.server.issue.index.IssueIndex;
import org.sonar.server.issue.notification.IssueChangeNotification;
import org.sonar.server.source.index.SourceLineDoc;
import org.sonar.server.source.index.SourceLineIndex;
import org.sonar.server.user.UserSession;
import org.sonar.server.user.index.UserDoc;
import org.sonar.server.user.index.UserIndex;

import javax.annotation.CheckForNull;
import javax.annotation.Nullable;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Map;

@ServerSide
public class IssueService {

  private final DbClient dbClient;
  private final IssueIndex issueIndex;

  private final IssueWorkflow workflow;
  private final IssueUpdater issueUpdater;
  private final IssueStorage issueStorage;
  private final NotificationManager notificationService;
  private final ActionPlanService actionPlanService;
  private final RuleFinder ruleFinder;
  private final UserFinder userFinder;
  private final UserIndex userIndex;
  private final SourceLineIndex sourceLineIndex;
  private final UserSession userSession;

  public IssueService(DbClient dbClient, IssueIndex issueIndex,
    IssueWorkflow workflow,
    IssueStorage issueStorage,
    IssueUpdater issueUpdater,
    NotificationManager notificationService,
    ActionPlanService actionPlanService,
    RuleFinder ruleFinder,
    UserFinder userFinder,
    UserIndex userIndex, SourceLineIndex sourceLineIndex, UserSession userSession) {
    this.dbClient = dbClient;
    this.issueIndex = issueIndex;
    this.workflow = workflow;
    this.issueStorage = issueStorage;
    this.issueUpdater = issueUpdater;
    this.actionPlanService = actionPlanService;
    this.ruleFinder = ruleFinder;
    this.notificationService = notificationService;
    this.userFinder = userFinder;
    this.userIndex = userIndex;
    this.sourceLineIndex = sourceLineIndex;
    this.userSession = userSession;
  }

  public List<String> listStatus() {
    return workflow.statusKeys();
  }

  /**
   * List of available transitions.
   * <p/>
   * Never return null, but return an empty list if the issue does not exist.
   */
  public List<Transition> listTransitions(String issueKey) {
    DbSession session = dbClient.openSession(false);
    try {
      return listTransitions(getByKeyForUpdate(session, issueKey).toDefaultIssue());
    } finally {
      session.close();
    }
  }

  /**
   * Never return null, but an empty list if the issue does not exist.
   * No security check is done since it should already have been done to get the issue
   */
  public List<Transition> listTransitions(@Nullable Issue issue) {
    if (issue == null) {
      return Collections.emptyList();
    }
    List<Transition> outTransitions = workflow.outTransitions(issue);
    List<Transition> allowedTransitions = new ArrayList<>();
    for (Transition transition : outTransitions) {
      String projectUuid = issue.projectUuid();
      if (StringUtils.isBlank(transition.requiredProjectPermission()) ||
        (projectUuid != null && userSession.hasProjectPermissionByUuid(transition.requiredProjectPermission(), projectUuid))) {
        allowedTransitions.add(transition);
      }
    }
    return allowedTransitions;
  }

  public Issue doTransition(String issueKey, String transitionKey) {
    verifyLoggedIn();

    DbSession session = dbClient.openSession(false);
    try {
      DefaultIssue defaultIssue = getByKeyForUpdate(session, issueKey).toDefaultIssue();
      IssueChangeContext context = IssueChangeContext.createUser(new Date(), userSession.getLogin());
      checkTransitionPermission(transitionKey, userSession, defaultIssue);
      if (workflow.doTransition(defaultIssue, transitionKey, context)) {
        saveIssue(session, defaultIssue, context, null);
      }
      return defaultIssue;

    } finally {
      session.close();
    }
  }

  private void checkTransitionPermission(String transitionKey, UserSession userSession, DefaultIssue defaultIssue) {
    List<Transition> outTransitions = workflow.outTransitions(defaultIssue);
    for (Transition transition : outTransitions) {
      String projectKey = defaultIssue.projectKey();
      if (transition.key().equals(transitionKey) && StringUtils.isNotBlank(transition.requiredProjectPermission()) && projectKey != null) {
        userSession.checkProjectPermission(transition.requiredProjectPermission(), projectKey);
      }
    }
  }

  public Issue assign(String issueKey, @Nullable String assignee) {
    verifyLoggedIn();

    DbSession session = dbClient.openSession(false);
    try {
      DefaultIssue issue = getByKeyForUpdate(session, issueKey).toDefaultIssue();
      User user = null;
      if (!Strings.isNullOrEmpty(assignee)) {
        user = userFinder.findByLogin(assignee);
        if (user == null) {
          throw new NotFoundException("Unknown user: " + assignee);
        }
      }
      IssueChangeContext context = IssueChangeContext.createUser(new Date(), userSession.getLogin());
      if (issueUpdater.assign(issue, user, context)) {
        saveIssue(session, issue, context, null);
      }
      return issue;

    } finally {
      session.close();
    }
  }

  public Issue plan(String issueKey, @Nullable String actionPlanKey) {
    verifyLoggedIn();

    DbSession session = dbClient.openSession(false);
    try {
      ActionPlan actionPlan = null;
      if (!Strings.isNullOrEmpty(actionPlanKey)) {
        actionPlan = actionPlanService.findByKey(actionPlanKey, userSession);
        if (actionPlan == null) {
          throw new NotFoundException("Unknown action plan: " + actionPlanKey);
        }
      }
      DefaultIssue issue = getByKeyForUpdate(session, issueKey).toDefaultIssue();

      IssueChangeContext context = IssueChangeContext.createUser(new Date(), userSession.getLogin());
      if (issueUpdater.plan(issue, actionPlan, context)) {
        saveIssue(session, issue, context, null);
      }
      return issue;

    } finally {
      session.close();
    }
  }

  public Issue setSeverity(String issueKey, String severity) {
    verifyLoggedIn();

    DbSession session = dbClient.openSession(false);
    try {
      DefaultIssue issue = getByKeyForUpdate(session, issueKey).toDefaultIssue();
      userSession.checkProjectPermission(UserRole.ISSUE_ADMIN, issue.projectKey());

      IssueChangeContext context = IssueChangeContext.createUser(new Date(), userSession.getLogin());
      if (issueUpdater.setManualSeverity(issue, severity, context)) {
        saveIssue(session, issue, context, null);
      }
      return issue;
    } finally {
      session.close();
    }
  }

  public DefaultIssue createManualIssue(String componentKey, RuleKey ruleKey, @Nullable Integer line, @Nullable String message, @Nullable String severity,
    @Nullable Double effortToFix) {
    verifyLoggedIn();

    DbSession session = dbClient.openSession(false);
    try {
      ComponentDto component = dbClient.componentDao().selectByKey(session, componentKey);
      ComponentDto project = dbClient.componentDao().selectByUuid(session, component.projectUuid());

      userSession.checkProjectPermission(UserRole.USER, project.getKey());
      if (!ruleKey.isManual()) {
        throw new IllegalArgumentException("Issues can be created only on rules marked as 'manual': " + ruleKey);
      }
      Rule rule = getNullableRuleByKey(ruleKey);
      if (rule == null) {
        throw new IllegalArgumentException("Unknown rule: " + ruleKey);
      }

      DefaultIssue issue = new DefaultIssueBuilder()
        .componentKey(component.getKey())
        .projectKey(project.getKey())
        .line(line)
        .message(!Strings.isNullOrEmpty(message) ? message : rule.getName())
        .severity(Objects.firstNonNull(severity, Severity.MAJOR))
        .effortToFix(effortToFix)
        .ruleKey(ruleKey)
        .reporter(userSession.getLogin())
        .assignee(findSourceLineUser(component.uuid(), line))
        .build();

      Date now = new Date();
      issue.setCreationDate(now);
      issue.setUpdateDate(now);
      issueStorage.save(issue);
      return issue;
    } finally {
      session.close();
    }
  }

  public Issue getByKey(String key) {
    return issueIndex.getByKey(key);
  }

  IssueDto getByKeyForUpdate(DbSession session, String key) {
    // Load from index to check permission : if the user has no permission to see the issue an exception will be generated
    Issue authorizedIssueIndex = getByKey(key);
    return dbClient.issueDao().selectByKey(session, authorizedIssueIndex.key());
  }

  void saveIssue(DbSession session, DefaultIssue issue, IssueChangeContext context, @Nullable String comment) {
    String projectKey = issue.projectKey();
    if (projectKey == null) {
      throw new IllegalStateException(String.format("Issue '%s' has no project key", issue.key()));
    }
    issueStorage.save(session, issue);
    Rule rule = getNullableRuleByKey(issue.ruleKey());
    ComponentDto project = dbClient.componentDao().selectByKey(session, projectKey);
    notificationService.scheduleForSending(new IssueChangeNotification()
      .setIssue(issue)
      .setChangeAuthorLogin(context.login())
      .setRuleName(rule != null ? rule.getName() : null)
      .setProject(project.getKey(), project.name())
      .setComponent(dbClient.componentDao().selectNullableByKey(session, issue.componentKey()))
      .setComment(comment));
  }

  /**
   * Should use {@link org.sonar.server.rule.RuleService#getByKey(org.sonar.api.rule.RuleKey)}, but it's not possible as IssueNotifications is still used by the batch.
   * Can be null for removed rules
   */
  private Rule getNullableRuleByKey(RuleKey ruleKey) {
    return ruleFinder.findByKey(ruleKey);
  }

  public SearchResult<IssueDoc> search(IssueQuery query, SearchOptions options) {
    return issueIndex.search(query, options);
  }

  private void verifyLoggedIn() {
    userSession.checkLoggedIn();
  }

  /**
   * Search for all tags, whatever issue resolution or user access rights
   */
  public List<String> listTags(@Nullable String textQuery, int pageSize) {
    IssueQuery query = IssueQuery.builder(userSession)
      .checkAuthorization(false)
      .build();
    return issueIndex.listTags(query, textQuery, pageSize);
  }

  public List<String> listAuthors(@Nullable String textQuery, int pageSize) {
    IssueQuery query = IssueQuery.builder(userSession)
      .checkAuthorization(false)
      .build();
    return issueIndex.listAuthors(query, textQuery, pageSize);
  }

  public Collection<String> setTags(String issueKey, Collection<String> tags) {
    verifyLoggedIn();

    DbSession session = dbClient.openSession(false);
    try {
      DefaultIssue issue = getByKeyForUpdate(session, issueKey).toDefaultIssue();
      IssueChangeContext context = IssueChangeContext.createUser(new Date(), userSession.getLogin());
      if (issueUpdater.setTags(issue, tags, context)) {
        saveIssue(session, issue, context, null);
      }
      return issue.tags();

    } finally {
      session.close();
    }
  }

  public Map<String, Long> listTagsForComponent(IssueQuery query, int pageSize) {
    return issueIndex.countTags(query, pageSize);
  }

  @CheckForNull
  private String findSourceLineUser(String fileUuid, @Nullable Integer line) {
    if (line != null) {
      SourceLineDoc sourceLine = sourceLineIndex.getLine(fileUuid, line);
      String scmAuthor = sourceLine.scmAuthor();
      if (!Strings.isNullOrEmpty(scmAuthor)) {
        UserDoc userDoc = userIndex.getNullableByScmAccount(scmAuthor);
        if (userDoc != null) {
          return userDoc.login();
        }
      }
    }
    return null;
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/issue/notification/ChangesOnMyIssueNotificationDispatcher.java
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
package org.sonar.server.issue.notification;

import com.google.common.base.Objects;
import com.google.common.collect.Multimap;
import org.sonar.api.notifications.*;

import javax.annotation.Nullable;
import java.util.Collection;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationDispatcherMetadata;
import org.sonar.core.notification.NotificationManager;

/**
 * This dispatcher means: "notify me when a change is done on an issue that is assigned to me or reported by me".
 *
 * @since 3.6, but the feature exists since 2.10 ("review-changed" notification)
 */
public class ChangesOnMyIssueNotificationDispatcher extends NotificationDispatcher {

  public static final String KEY = "ChangesOnMyIssue";
  private NotificationManager notificationManager;

  public ChangesOnMyIssueNotificationDispatcher(NotificationManager notificationManager) {
    super(IssueChangeNotification.TYPE);
    this.notificationManager = notificationManager;
  }

  @Override
  public String getKey() {
    return KEY;
  }

  public static NotificationDispatcherMetadata newMetadata() {
    return NotificationDispatcherMetadata.create(KEY)
      .setProperty(NotificationDispatcherMetadata.GLOBAL_NOTIFICATION, String.valueOf(true))
      .setProperty(NotificationDispatcherMetadata.PER_PROJECT_NOTIFICATION, String.valueOf(true));
  }

  @Override
  public void dispatch(Notification notification, Context context) {
    String projectKey = notification.getFieldValue("projectKey");
    Multimap<String, NotificationChannel> subscribedRecipients = notificationManager.findNotificationSubscribers(this, projectKey);

    // See available fields in the class IssueNotifications.

    // All the following users can be null
    String changeAuthor = notification.getFieldValue("changeAuthor");
    String reporter = notification.getFieldValue("reporter");
    String assignee = notification.getFieldValue("assignee");

    if (!Objects.equal(changeAuthor, reporter)) {
      addUserToContextIfSubscribed(context, reporter, subscribedRecipients);
    }
    if (!Objects.equal(changeAuthor, assignee)) {
      addUserToContextIfSubscribed(context, assignee, subscribedRecipients);
    }
  }

  private void addUserToContextIfSubscribed(Context context, @Nullable String user, Multimap<String, NotificationChannel> subscribedRecipients) {
    if (user != null) {
      Collection<NotificationChannel> channels = subscribedRecipients.get(user);
      for (NotificationChannel channel : channels) {
        context.addUser(user, channel);
      }
    }
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/issue/notification/DoNotFixNotificationDispatcher.java
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

package org.sonar.server.issue.notification;

import com.google.common.base.Objects;
import com.google.common.collect.Multimap;
import org.sonar.api.issue.Issue;
import org.sonar.api.notifications.*;

import java.util.Collection;
import java.util.Map;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationDispatcherMetadata;
import org.sonar.core.notification.NotificationManager;

/**
 * This dispatcher means: "notify me when an issue is resolved as false positive or won't fix".
 */
public class DoNotFixNotificationDispatcher extends NotificationDispatcher {

  public static final String KEY = "NewFalsePositiveIssue";

  private final NotificationManager notifications;

  public DoNotFixNotificationDispatcher(NotificationManager notifications) {
    super(IssueChangeNotification.TYPE);
    this.notifications = notifications;
  }

  @Override
  public String getKey() {
    return KEY;
  }

  public static NotificationDispatcherMetadata newMetadata() {
    return NotificationDispatcherMetadata.create(KEY)
      .setProperty(NotificationDispatcherMetadata.GLOBAL_NOTIFICATION, String.valueOf(true))
      .setProperty(NotificationDispatcherMetadata.PER_PROJECT_NOTIFICATION, String.valueOf(true));
  }

  @Override
  public void dispatch(Notification notification, Context context) {
    String newResolution = notification.getFieldValue("new.resolution");
    if (Objects.equal(newResolution, Issue.RESOLUTION_FALSE_POSITIVE) || Objects.equal(newResolution, Issue.RESOLUTION_WONT_FIX)) {
      String author = notification.getFieldValue("changeAuthor");
      String projectKey = notification.getFieldValue("projectKey");
      Multimap<String, NotificationChannel> subscribedRecipients = notifications.findNotificationSubscribers(this, projectKey);
      notify(author, context, subscribedRecipients);
    }
  }

  private void notify(String author, Context context, Multimap<String, NotificationChannel> subscribedRecipients) {
    for (Map.Entry<String, Collection<NotificationChannel>> channelsByRecipients : subscribedRecipients.asMap().entrySet()) {
      String login = channelsByRecipients.getKey();
      // Do not notify the person that resolved the issue
      if (!Objects.equal(author, login)) {
        for (NotificationChannel channel : channelsByRecipients.getValue()) {
          context.addUser(login, channel);
        }
      }
    }
  }

}


File: server/sonar-server/src/main/java/org/sonar/server/issue/notification/MyNewIssuesNotificationDispatcher.java
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

package org.sonar.server.issue.notification;

import com.google.common.collect.Multimap;
import org.sonar.api.notifications.*;

import java.util.Collection;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationDispatcherMetadata;
import org.sonar.core.notification.NotificationManager;

/**
 * This dispatcher means: "notify me when new issues are introduced during project analysis"
 */
public class MyNewIssuesNotificationDispatcher extends NotificationDispatcher {

  public static final String KEY = "SQ-MyNewIssues";
  private final NotificationManager manager;

  public MyNewIssuesNotificationDispatcher(NotificationManager manager) {
    super(MyNewIssuesNotification.MY_NEW_ISSUES_NOTIF_TYPE);
    this.manager = manager;
  }

  public static NotificationDispatcherMetadata newMetadata() {
    return NotificationDispatcherMetadata.create(KEY)
      .setProperty(NotificationDispatcherMetadata.GLOBAL_NOTIFICATION, String.valueOf(true))
      .setProperty(NotificationDispatcherMetadata.PER_PROJECT_NOTIFICATION, String.valueOf(true));
  }

  @Override
  public String getKey() {
    return KEY;
  }

  @Override
  public void dispatch(Notification notification, Context context) {
    String projectKey = notification.getFieldValue("projectKey");
    String assignee = notification.getFieldValue("assignee");
    Multimap<String, NotificationChannel> subscribedRecipients = manager.findNotificationSubscribers(this, projectKey);

    Collection<NotificationChannel> channels = subscribedRecipients.get(assignee);
    for (NotificationChannel channel : channels) {
      context.addUser(assignee, channel);
    }
  }

}


File: server/sonar-server/src/main/java/org/sonar/server/issue/notification/NewIssuesNotificationDispatcher.java
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
package org.sonar.server.issue.notification;

import com.google.common.collect.Multimap;
import org.sonar.api.notifications.*;

import java.util.Collection;
import java.util.Map;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationDispatcherMetadata;
import org.sonar.core.notification.NotificationManager;

/**
 * This dispatcher means: "notify me when new issues are introduced during project analysis"
 */
public class NewIssuesNotificationDispatcher extends NotificationDispatcher {

  public static final String KEY = "NewIssues";
  private final NotificationManager manager;

  public NewIssuesNotificationDispatcher(NotificationManager manager) {
    super(NewIssuesNotification.TYPE);
    this.manager = manager;
  }

  @Override
  public String getKey() {
    return KEY;
  }

  public static NotificationDispatcherMetadata newMetadata() {
    return NotificationDispatcherMetadata.create(KEY)
      .setProperty(NotificationDispatcherMetadata.GLOBAL_NOTIFICATION, String.valueOf(true))
      .setProperty(NotificationDispatcherMetadata.PER_PROJECT_NOTIFICATION, String.valueOf(true));
  }

  @Override
  public void dispatch(Notification notification, Context context) {
    String projectKey = notification.getFieldValue("projectKey");
    Multimap<String, NotificationChannel> subscribedRecipients = manager.findNotificationSubscribers(this, projectKey);

    for (Map.Entry<String, Collection<NotificationChannel>> channelsByRecipients : subscribedRecipients.asMap().entrySet()) {
      String userLogin = channelsByRecipients.getKey();
      for (NotificationChannel channel : channelsByRecipients.getValue()) {
        context.addUser(userLogin, channel);
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
import org.sonar.core.notification.DefaultNotificationManager;
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
import org.sonar.server.notifications.NotificationCenter;
import org.sonar.server.notifications.NotificationService;
import org.sonar.server.notifications.email.AlertsEmailTemplate;
import org.sonar.server.notifications.email.EmailNotificationChannel;
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


File: server/sonar-server/src/test/java/org/sonar/server/computation/step/SendIssueNotificationsStepTest.java
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
package org.sonar.server.computation.step;

import java.io.IOException;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import org.mockito.Mockito;
import org.sonar.api.issue.internal.DefaultIssue;
import org.sonar.api.notifications.Notification;
import org.sonar.api.rule.Severity;
import org.sonar.api.utils.System2;
import org.sonar.batch.protocol.Constants;
import org.sonar.batch.protocol.output.BatchReport;
import org.sonar.server.computation.batch.BatchReportReaderRule;
import org.sonar.server.computation.batch.TreeRootHolderRule;
import org.sonar.server.computation.component.Component;
import org.sonar.server.computation.component.DumbComponent;
import org.sonar.server.computation.issue.IssueCache;
import org.sonar.server.computation.issue.RuleCache;
import org.sonar.server.issue.notification.IssueChangeNotification;
import org.sonar.server.issue.notification.NewIssuesNotification;
import org.sonar.server.issue.notification.NewIssuesNotificationFactory;
import org.sonar.server.notifications.NotificationService;

import static org.mockito.Mockito.any;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class SendIssueNotificationsStepTest extends BaseStepTest {

  private static final String PROJECT_UUID = "PROJECT_UUID";
  private static final String PROJECT_KEY = "PROJECT_KEY";

  @Rule
  public BatchReportReaderRule reportReader = new BatchReportReaderRule();

  @Rule
  public TreeRootHolderRule treeRootHolder = new TreeRootHolderRule();

  @Rule
  public TemporaryFolder temp = new TemporaryFolder();

  NotificationService notifService = mock(NotificationService.class);
  IssueCache issueCache;
  SendIssueNotificationsStep sut;

  @Before
  public void setUp() throws Exception {
    issueCache = new IssueCache(temp.newFile(), System2.INSTANCE);
    NewIssuesNotificationFactory newIssuesNotificationFactory = mock(NewIssuesNotificationFactory.class, Mockito.RETURNS_DEEP_STUBS);
    sut = new SendIssueNotificationsStep(issueCache, mock(RuleCache.class), treeRootHolder, notifService, reportReader, newIssuesNotificationFactory);

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, PROJECT_UUID, PROJECT_KEY));

    reportReader.setMetadata(BatchReport.Metadata.newBuilder()
      .setRootComponentRef(1)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project name")
      .build());
  }

  @Test
  public void do_not_send_notifications_if_no_subscribers() throws IOException {
    when(notifService.hasProjectSubscribersForTypes(PROJECT_UUID, SendIssueNotificationsStep.NOTIF_TYPES)).thenReturn(false);

    sut.execute();

    verify(notifService, never()).deliver(any(Notification.class));
  }

  @Test
  public void send_notifications_if_subscribers() {
    issueCache.newAppender().append(new DefaultIssue()
      .setSeverity(Severity.BLOCKER)).close();

    when(notifService.hasProjectSubscribersForTypes(PROJECT_UUID, SendIssueNotificationsStep.NOTIF_TYPES)).thenReturn(true);

    sut.execute();

    verify(notifService).deliver(any(NewIssuesNotification.class));
    verify(notifService, atLeastOnce()).deliver(any(IssueChangeNotification.class));
  }

  @Override
  protected ComputationStep step() {
    return sut;
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/event/NewAlertsTest.java
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
package org.sonar.server.event;

import com.google.common.collect.HashMultimap;
import com.google.common.collect.Multimap;
import org.junit.Test;
import org.sonar.api.notifications.Notification;
import org.sonar.api.notifications.NotificationChannel;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationManager;

import static org.mockito.Mockito.*;

public class NewAlertsTest {

  NotificationManager notificationManager = mock(NotificationManager.class);
  NotificationDispatcher.Context context = mock(NotificationDispatcher.Context.class);
  NotificationChannel emailChannel = mock(NotificationChannel.class);
  NotificationChannel twitterChannel = mock(NotificationChannel.class);
  NewAlerts dispatcher = new NewAlerts(notificationManager);

  @Test
  public void should_not_dispatch_if_not_alerts_notification() {
    Notification notification = new Notification("other-notif");
    dispatcher.performDispatch(notification, context);

    verify(context, never()).addUser(any(String.class), any(NotificationChannel.class));
  }

  @Test
  public void should_dispatch_to_users_who_have_subscribed() {
    Multimap<String, NotificationChannel> recipients = HashMultimap.create();
    recipients.put("user1", emailChannel);
    recipients.put("user2", twitterChannel);
    when(notificationManager.findSubscribedRecipientsForDispatcher(dispatcher, 34)).thenReturn(recipients);

    Notification notification = new Notification("alerts").setFieldValue("projectId", "34");
    dispatcher.performDispatch(notification, context);

    verify(context).addUser("user1", emailChannel);
    verify(context).addUser("user2", twitterChannel);
    verifyNoMoreInteractions(context);
  }

  @Test
  public void should_not_dispatch_if_missing_project_id() {
    Multimap<String, NotificationChannel> recipients = HashMultimap.create();
    recipients.put("user1", emailChannel);
    recipients.put("user2", twitterChannel);
    when(notificationManager.findSubscribedRecipientsForDispatcher(dispatcher, 34)).thenReturn(recipients);

    Notification notification = new Notification("alerts");
    dispatcher.performDispatch(notification, context);

    verifyNoMoreInteractions(context);
  }

}


File: server/sonar-server/src/test/java/org/sonar/server/issue/notification/ChangesOnMyIssueNotificationDispatcherTest.java
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
package org.sonar.server.issue.notification;

import com.google.common.collect.HashMultimap;
import com.google.common.collect.Multimap;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.runners.MockitoJUnitRunner;
import org.sonar.api.notifications.*;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationDispatcherMetadata;
import org.sonar.core.notification.NotificationManager;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

@RunWith(MockitoJUnitRunner.class)
public class ChangesOnMyIssueNotificationDispatcherTest {

  @Mock
  NotificationManager notifications;

  @Mock
  NotificationDispatcher.Context context;

  @Mock
  NotificationChannel emailChannel;

  @Mock
  NotificationChannel twitterChannel;

  ChangesOnMyIssueNotificationDispatcher dispatcher;

  @Before
  public void setUp() {
    dispatcher = new ChangesOnMyIssueNotificationDispatcher(notifications);
  }

  @Test
  public void test_metadata() throws Exception {
    NotificationDispatcherMetadata metadata = ChangesOnMyIssueNotificationDispatcher.newMetadata();
    assertThat(metadata.getDispatcherKey()).isEqualTo(dispatcher.getKey());
    assertThat(metadata.getProperty(NotificationDispatcherMetadata.GLOBAL_NOTIFICATION)).isEqualTo("true");
    assertThat(metadata.getProperty(NotificationDispatcherMetadata.PER_PROJECT_NOTIFICATION)).isEqualTo("true");
  }

  @Test
  public void should_not_dispatch_if_other_notification_type() {
    Notification notification = new Notification("other-notif");
    dispatcher.performDispatch(notification, context);

    verify(context, never()).addUser(any(String.class), any(NotificationChannel.class));
  }

  @Test
  public void should_dispatch_to_reporter_and_assignee() {
    Multimap<String, NotificationChannel> recipients = HashMultimap.create();
    recipients.put("simon", emailChannel);
    recipients.put("freddy", twitterChannel);
    recipients.put("godin", twitterChannel);
    when(notifications.findNotificationSubscribers(dispatcher, "struts")).thenReturn(recipients);

    Notification notification = new IssueChangeNotification().setFieldValue("projectKey", "struts")
      .setFieldValue("changeAuthor", "olivier")
      .setFieldValue("reporter", "simon")
      .setFieldValue("assignee", "freddy");
    dispatcher.performDispatch(notification, context);

    verify(context).addUser("simon", emailChannel);
    verify(context).addUser("freddy", twitterChannel);
    verify(context, never()).addUser("godin", twitterChannel);
    verifyNoMoreInteractions(context);
  }

  @Test
  public void should_not_dispatch_to_author_of_changes() {
    Multimap<String, NotificationChannel> recipients = HashMultimap.create();
    recipients.put("simon", emailChannel);
    recipients.put("freddy", twitterChannel);
    recipients.put("godin", twitterChannel);
    when(notifications.findNotificationSubscribers(dispatcher, "struts")).thenReturn(recipients);

    // change author is the reporter
    dispatcher.performDispatch(new IssueChangeNotification().setFieldValue("projectKey", "struts")
      .setFieldValue("changeAuthor", "simon").setFieldValue("reporter", "simon"), context);

    // change author is the assignee
    dispatcher.performDispatch(new IssueChangeNotification().setFieldValue("projectKey", "struts")
      .setFieldValue("changeAuthor", "simon").setFieldValue("assignee", "simon"), context);

    // no change author
    dispatcher.performDispatch(new IssueChangeNotification().setFieldValue("projectKey", "struts")
      .setFieldValue("new.resolution", "FIXED"), context);

    verifyNoMoreInteractions(context);
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/issue/notification/DoNotFixNotificationDispatcherTest.java
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
package org.sonar.server.issue.notification;

import com.google.common.collect.HashMultimap;
import com.google.common.collect.Multimap;
import org.junit.Test;
import org.sonar.api.issue.Issue;
import org.sonar.api.notifications.Notification;
import org.sonar.api.notifications.NotificationChannel;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationDispatcherMetadata;
import org.sonar.core.notification.NotificationManager;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

public class DoNotFixNotificationDispatcherTest {
  NotificationManager notifications = mock(NotificationManager.class);
  NotificationDispatcher.Context context = mock(NotificationDispatcher.Context.class);
  NotificationChannel emailChannel = mock(NotificationChannel.class);
  NotificationChannel twitterChannel = mock(NotificationChannel.class);
  DoNotFixNotificationDispatcher sut = new DoNotFixNotificationDispatcher(notifications);;

  @Test
  public void test_metadata() throws Exception {
    NotificationDispatcherMetadata metadata = DoNotFixNotificationDispatcher.newMetadata();
    assertThat(metadata.getDispatcherKey()).isEqualTo(sut.getKey());
    assertThat(metadata.getProperty(NotificationDispatcherMetadata.GLOBAL_NOTIFICATION)).isEqualTo("true");
    assertThat(metadata.getProperty(NotificationDispatcherMetadata.PER_PROJECT_NOTIFICATION)).isEqualTo("true");
  }

  @Test
  public void should_not_dispatch_if_other_notification_type() {
    Notification notification = new Notification("other");
    sut.performDispatch(notification, context);

    verify(context, never()).addUser(any(String.class), any(NotificationChannel.class));
  }

  @Test
  public void should_dispatch_to_subscribers() {
    Multimap<String, NotificationChannel> recipients = HashMultimap.create();
    recipients.put("simon", emailChannel);
    recipients.put("freddy", twitterChannel);
    recipients.put("godin", twitterChannel);
    when(notifications.findNotificationSubscribers(sut, "struts")).thenReturn(recipients);

    Notification fpNotif = new IssueChangeNotification().setFieldValue("projectKey", "struts")
      .setFieldValue("changeAuthor", "godin")
      .setFieldValue("new.resolution", Issue.RESOLUTION_FALSE_POSITIVE)
      .setFieldValue("assignee", "freddy");
    sut.performDispatch(fpNotif, context);

    verify(context).addUser("simon", emailChannel);
    verify(context).addUser("freddy", twitterChannel);
    // do not notify the person who flagged the issue as false-positive
    verify(context, never()).addUser("godin", twitterChannel);
    verifyNoMoreInteractions(context);
  }

  /**
   * Only false positive and won't fix resolutions
   */
  @Test
  public void ignore_other_resolutions() {
    Multimap<String, NotificationChannel> recipients = HashMultimap.create();
    recipients.put("simon", emailChannel);
    recipients.put("freddy", twitterChannel);
    when(notifications.findNotificationSubscribers(sut, "struts")).thenReturn(recipients);

    Notification fixedNotif = new IssueChangeNotification().setFieldValue("projectKey", "struts")
      .setFieldValue("changeAuthor", "godin")
      .setFieldValue("new.resolution", Issue.RESOLUTION_FIXED)
      .setFieldValue("assignee", "freddy");
    sut.performDispatch(fixedNotif, context);

    verifyZeroInteractions(context);
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/issue/notification/MyNewIssuesNotificationDispatcherTest.java
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

package org.sonar.server.issue.notification;

import com.google.common.collect.HashMultimap;
import com.google.common.collect.Multimap;
import org.junit.Before;
import org.junit.Test;
import org.sonar.api.notifications.Notification;
import org.sonar.api.notifications.NotificationChannel;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationManager;

import static org.mockito.Mockito.*;

public class MyNewIssuesNotificationDispatcherTest {

  private MyNewIssuesNotificationDispatcher sut;

  private NotificationManager notificationManager = mock(NotificationManager.class);
  private NotificationDispatcher.Context context = mock(NotificationDispatcher.Context.class);
  private NotificationChannel emailChannel = mock(NotificationChannel.class);
  private NotificationChannel twitterChannel = mock(NotificationChannel.class);


  @Before
  public void setUp() {
    sut = new MyNewIssuesNotificationDispatcher(notificationManager);
  }

  @Test
  public void do_not_dispatch_if_no_new_notification() {
    Notification notification = new Notification("other-notif");
    sut.performDispatch(notification, context);

    verify(context, never()).addUser(any(String.class), any(NotificationChannel.class));
  }

  @Test
  public void dispatch_to_users_who_have_subscribed_to_notification_and_project() {
    Multimap<String, NotificationChannel> recipients = HashMultimap.create();
    recipients.put("user1", emailChannel);
    recipients.put("user2", twitterChannel);
    when(notificationManager.findNotificationSubscribers(sut, "struts")).thenReturn(recipients);

    Notification notification = new Notification(MyNewIssuesNotification.MY_NEW_ISSUES_NOTIF_TYPE)
      .setFieldValue("projectKey", "struts")
      .setFieldValue("assignee", "user1");
    sut.performDispatch(notification, context);

    verify(context).addUser("user1", emailChannel);
    verifyNoMoreInteractions(context);
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/issue/notification/NewIssuesNotificationDispatcherTest.java
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
package org.sonar.server.issue.notification;

import com.google.common.collect.HashMultimap;
import com.google.common.collect.Multimap;
import org.junit.Before;
import org.junit.Test;
import org.sonar.api.notifications.Notification;
import org.sonar.api.notifications.NotificationChannel;
import org.sonar.core.notification.NotificationDispatcher;
import org.sonar.core.notification.NotificationManager;

import static org.mockito.Mockito.*;

public class NewIssuesNotificationDispatcherTest {

  private NotificationManager notifications = mock(NotificationManager.class);
  private NotificationDispatcher.Context context = mock(NotificationDispatcher.Context.class);
  private NotificationChannel emailChannel = mock(NotificationChannel.class);
  private NotificationChannel twitterChannel = mock(NotificationChannel.class);
  private NewIssuesNotificationDispatcher dispatcher = mock(NewIssuesNotificationDispatcher.class);

  @Before
  public void setUp() {
    dispatcher = new NewIssuesNotificationDispatcher(notifications);
  }

  @Test
  public void shouldNotDispatchIfNotNewViolationsNotification() {
    Notification notification = new Notification("other-notif");
    dispatcher.performDispatch(notification, context);

    verify(context, never()).addUser(any(String.class), any(NotificationChannel.class));
  }

  @Test
  public void shouldDispatchToUsersWhoHaveSubscribedAndFlaggedProjectAsFavourite() {
    Multimap<String, NotificationChannel> recipients = HashMultimap.create();
    recipients.put("user1", emailChannel);
    recipients.put("user2", twitterChannel);
    when(notifications.findNotificationSubscribers(dispatcher, "struts")).thenReturn(recipients);

    Notification notification = new Notification(NewIssuesNotification.TYPE).setFieldValue("projectKey", "struts");
    dispatcher.performDispatch(notification, context);

    verify(context).addUser("user1", emailChannel);
    verify(context).addUser("user2", twitterChannel);
    verifyNoMoreInteractions(context);
  }
}


File: sonar-batch/src/main/java/org/sonar/batch/bootstrap/BatchComponents.java
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
package org.sonar.batch.bootstrap;

import com.google.common.collect.Lists;
import java.util.Collection;
import java.util.List;
import org.sonar.batch.components.TimeMachineConfiguration;
import org.sonar.batch.compute.ApplyProjectRolesDecorator;
import org.sonar.batch.compute.BranchCoverageDecorator;
import org.sonar.batch.compute.CommentDensityDecorator;
import org.sonar.batch.compute.CountFalsePositivesDecorator;
import org.sonar.batch.compute.CountUnresolvedIssuesDecorator;
import org.sonar.batch.compute.CoverageDecorator;
import org.sonar.batch.compute.DirectoriesDecorator;
import org.sonar.batch.compute.FilesDecorator;
import org.sonar.batch.compute.ItBranchCoverageDecorator;
import org.sonar.batch.compute.ItCoverageDecorator;
import org.sonar.batch.compute.ItLineCoverageDecorator;
import org.sonar.batch.compute.LineCoverageDecorator;
import org.sonar.batch.compute.ManualMeasureDecorator;
import org.sonar.batch.compute.NewCoverageAggregator;
import org.sonar.batch.compute.NewCoverageFileAnalyzer;
import org.sonar.batch.compute.NewItCoverageFileAnalyzer;
import org.sonar.batch.compute.NewOverallCoverageFileAnalyzer;
import org.sonar.batch.compute.OverallBranchCoverageDecorator;
import org.sonar.batch.compute.OverallCoverageDecorator;
import org.sonar.batch.compute.OverallLineCoverageDecorator;
import org.sonar.batch.compute.TimeMachineConfigurationPersister;
import org.sonar.batch.compute.UnitTestDecorator;
import org.sonar.batch.compute.VariationDecorator;
import org.sonar.batch.cpd.CpdComponents;
import org.sonar.batch.debt.DebtDecorator;
import org.sonar.batch.debt.IssueChangelogDebtCalculator;
import org.sonar.batch.debt.NewDebtDecorator;
import org.sonar.batch.debt.SqaleRatingDecorator;
import org.sonar.batch.debt.SqaleRatingSettings;
import org.sonar.batch.issue.tracking.InitialOpenIssuesSensor;
import org.sonar.batch.issue.tracking.IssueHandlers;
import org.sonar.batch.issue.tracking.IssueTracking;
import org.sonar.batch.issue.tracking.IssueTrackingDecorator;
import org.sonar.batch.language.LanguageDistributionDecorator;
import org.sonar.batch.qualitygate.QualityGateVerifier;
import org.sonar.batch.scan.report.ConsoleReport;
import org.sonar.batch.scan.report.HtmlReport;
import org.sonar.batch.scan.report.IssuesReportBuilder;
import org.sonar.batch.scan.report.JSONReport;
import org.sonar.batch.scan.report.RuleNameProvider;
import org.sonar.batch.scan.report.SourceProvider;
import org.sonar.batch.scm.ScmConfiguration;
import org.sonar.batch.scm.ScmSensor;
import org.sonar.batch.source.CodeColorizerSensor;
import org.sonar.batch.source.LinesSensor;
import org.sonar.core.config.CorePropertyDefinitions;
import org.sonar.core.notification.DefaultNotificationManager;
import org.sonar.core.resource.DefaultResourceTypes;

public class BatchComponents {
  private BatchComponents() {
    // only static stuff
  }

  public static Collection all(DefaultAnalysisMode analysisMode) {
    List components = Lists.newArrayList(
      DefaultResourceTypes.get(),
      // SCM
      ScmConfiguration.class,
      ScmSensor.class,

      LinesSensor.class,
      CodeColorizerSensor.class,

      // Issues tracking
      IssueTracking.class,

      // Reports
      ConsoleReport.class,
      JSONReport.class,
      HtmlReport.class,
      IssuesReportBuilder.class,
      SourceProvider.class,
      RuleNameProvider.class,

      // language
      LanguageDistributionDecorator.class,

      // Debt
      IssueChangelogDebtCalculator.class,
      DebtDecorator.class,
      NewDebtDecorator.class,
      SqaleRatingDecorator.class,
      SqaleRatingSettings.class,

      DefaultNotificationManager.class,

      // Quality Gate
      QualityGateVerifier.class,

      // Issue tracking
      IssueTrackingDecorator.class,
      IssueHandlers.class,
      InitialOpenIssuesSensor.class,

      // to be moved to compute engine
      CountUnresolvedIssuesDecorator.class,
      CountFalsePositivesDecorator.class,
      UnitTestDecorator.class,
      LineCoverageDecorator.class,
      CoverageDecorator.class,
      BranchCoverageDecorator.class,
      ItLineCoverageDecorator.class,
      ItCoverageDecorator.class,
      ItBranchCoverageDecorator.class,
      OverallLineCoverageDecorator.class,
      OverallCoverageDecorator.class,
      OverallBranchCoverageDecorator.class,
      ApplyProjectRolesDecorator.class,
      CommentDensityDecorator.class,
      DirectoriesDecorator.class,
      FilesDecorator.class,
      ManualMeasureDecorator.class,
      VariationDecorator.class,
      TimeMachineConfigurationPersister.class,
      NewCoverageFileAnalyzer.class,
      NewItCoverageFileAnalyzer.class,
      NewOverallCoverageFileAnalyzer.class,
      NewCoverageAggregator.class,
      TimeMachineConfiguration.class
      );
    components.addAll(CorePropertyDefinitions.all());
    // CPD
    components.addAll(CpdComponents.all());
    return components;
  }
}
