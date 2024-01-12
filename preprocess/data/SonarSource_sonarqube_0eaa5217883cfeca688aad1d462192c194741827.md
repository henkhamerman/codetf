Refactoring Types: ['Move Attribute']
ava/org/sonar/server/issue/InternalRubyIssueService.java
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

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.base.Predicate;
import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;
import java.io.StringWriter;
import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.CheckForNull;
import javax.annotation.Nullable;
import org.apache.commons.io.IOUtils;
import org.apache.commons.lang.StringUtils;
import org.sonar.api.issue.ActionPlan;
import org.sonar.api.issue.Issue;
import org.sonar.api.issue.IssueComment;
import org.sonar.api.issue.action.Action;
import org.sonar.api.issue.internal.DefaultIssue;
import org.sonar.api.issue.internal.DefaultIssueComment;
import org.sonar.api.issue.internal.FieldDiffs;
import org.sonar.api.rule.RuleKey;
import org.sonar.api.server.ServerSide;
import org.sonar.api.user.User;
import org.sonar.api.utils.SonarException;
import org.sonar.api.utils.text.JsonWriter;
import org.sonar.api.web.UserRole;
import org.sonar.core.component.ComponentDto;
import org.sonar.core.issue.ActionPlanStats;
import org.sonar.core.issue.DefaultActionPlan;
import org.sonar.core.issue.db.IssueFilterDto;
import org.sonar.core.issue.workflow.Transition;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.persistence.MyBatis;
import org.sonar.core.resource.ResourceDao;
import org.sonar.core.resource.ResourceDto;
import org.sonar.core.resource.ResourceQuery;
import org.sonar.server.db.DbClient;
import org.sonar.server.es.SearchOptions;
import org.sonar.server.exceptions.BadRequestException;
import org.sonar.server.issue.actionplan.ActionPlanService;
import org.sonar.server.issue.filter.IssueFilterParameters;
import org.sonar.server.issue.filter.IssueFilterService;
import org.sonar.server.issue.ws.IssueComponentHelper;
import org.sonar.server.issue.ws.IssueJsonWriter;
import org.sonar.server.search.QueryContext;
import org.sonar.server.user.UserSession;
import org.sonar.server.user.index.UserIndex;
import org.sonar.server.util.RubyUtils;
import org.sonar.server.util.Validation;

import static com.google.common.collect.Lists.newArrayList;

/**
 * Used through ruby code <pre>Internal.issues</pre>
 *
 * All the issue features that are not published to public API.
 *
 * @since 3.6
 */
@ServerSide
public class InternalRubyIssueService {

  private static final String ID_PARAM = "id";
  private static final String NAME_PARAM = "name";
  private static final String DESCRIPTION_PARAM = "description";
  private static final String PROJECT_PARAM = "project";
  private static final String USER_PARAM = "user";

  private static final String ACTION_PLANS_ERRORS_ACTION_PLAN_DOES_NOT_EXIST_MESSAGE = "action_plans.errors.action_plan_does_not_exist";

  private final IssueService issueService;
  private final IssueQueryService issueQueryService;
  private final IssueCommentService commentService;
  private final IssueChangelogService changelogService;
  private final ActionPlanService actionPlanService;
  private final ResourceDao resourceDao;
  private final ActionService actionService;
  private final IssueFilterService issueFilterService;
  private final IssueBulkChangeService issueBulkChangeService;
  private final IssueJsonWriter issueWriter;
  private final IssueComponentHelper issueComponentHelper;
  private final UserIndex userIndex;
  private final DbClient dbClient;
  private final UserSession userSession;

  public InternalRubyIssueService(
    IssueService issueService,
    IssueQueryService issueQueryService,
    IssueCommentService commentService,
    IssueChangelogService changelogService, ActionPlanService actionPlanService,
    ResourceDao resourceDao, ActionService actionService,
    IssueFilterService issueFilterService, IssueBulkChangeService issueBulkChangeService,
    IssueJsonWriter issueWriter, IssueComponentHelper issueComponentHelper, UserIndex userIndex, DbClient dbClient,
    UserSession userSession) {
    this.issueService = issueService;
    this.issueQueryService = issueQueryService;
    this.commentService = commentService;
    this.changelogService = changelogService;
    this.actionPlanService = actionPlanService;
    this.resourceDao = resourceDao;
    this.actionService = actionService;
    this.issueFilterService = issueFilterService;
    this.issueBulkChangeService = issueBulkChangeService;
    this.issueWriter = issueWriter;
    this.issueComponentHelper = issueComponentHelper;
    this.userIndex = userIndex;
    this.dbClient = dbClient;
    this.userSession = userSession;
  }

  public Issue getIssueByKey(String issueKey) {
    return issueService.getByKey(issueKey);
  }

  public List<Transition> listTransitions(String issueKey) {
    return issueService.listTransitions(issueKey);
  }

  public List<Transition> listTransitions(Issue issue) {
    return issueService.listTransitions(issue);
  }

  public List<String> listStatus() {
    return issueService.listStatus();
  }

  public List<String> listResolutions() {
    return Issue.RESOLUTIONS;
  }

  public IssueChangelog changelog(String issueKey) {
    return changelogService.changelog(issueKey);
  }

  public IssueChangelog changelog(Issue issue) {
    return changelogService.changelog(issue);
  }

  public List<String> formatChangelog(FieldDiffs diffs) {
    return changelogService.formatDiffs(diffs);
  }

  public List<String> listPluginActions() {
    return newArrayList(Iterables.transform(actionService.listAllActions(), new Function<Action, String>() {
      @Override
      public String apply(Action input) {
        return input.key();
      }
    }));
  }

  public List<DefaultIssueComment> findComments(String issueKey) {
    return commentService.findComments(issueKey);
  }

  public List<DefaultIssueComment> findCommentsByIssueKeys(Collection<String> issueKeys) {
    return commentService.findComments(issueKeys);
  }

  public Result<Issue> doTransition(String issueKey, String transitionKey) {
    Result<Issue> result = Result.of();
    try {
      result.set(issueService.doTransition(issueKey, transitionKey));
    } catch (Exception e) {
      result.addError(e.getMessage());
    }
    return result;
  }

  public Result<Issue> assign(String issueKey, @Nullable String assignee) {
    Result<Issue> result = Result.of();
    try {
      result.set(issueService.assign(issueKey, StringUtils.defaultIfBlank(assignee, null)));
    } catch (Exception e) {
      result.addError(e.getMessage());
    }
    return result;
  }

  public Result<Issue> setSeverity(String issueKey, String severity) {
    Result<Issue> result = Result.of();
    try {
      result.set(issueService.setSeverity(issueKey, severity));
    } catch (Exception e) {
      result.addError(e.getMessage());
    }
    return result;
  }

  public Result<Issue> plan(String issueKey, @Nullable String actionPlanKey) {
    Result<Issue> result = Result.of();
    try {
      result.set(issueService.plan(issueKey, actionPlanKey));
    } catch (Exception e) {
      result.addError(e.getMessage());
    }
    return result;
  }

  public Result<IssueComment> addComment(String issueKey, String text) {
    Result<IssueComment> result = Result.of();
    try {
      result.set(commentService.addComment(issueKey, text, userSession));
    } catch (Exception e) {
      result.addError(e.getMessage());
    }
    return result;
  }

  public IssueComment deleteComment(String commentKey) {
    return commentService.deleteComment(commentKey, userSession);
  }

  public Result<IssueComment> editComment(String commentKey, String newText) {
    Result<IssueComment> result = Result.of();
    try {
      result.set(commentService.editComment(commentKey, newText, userSession));
    } catch (Exception e) {
      result.addError(e.getMessage());
    }
    return result;
  }

  public IssueComment findComment(String commentKey) {
    return commentService.findComment(commentKey);
  }

  /**
   * Create manual issue
   */
  public Result<DefaultIssue> create(Map<String, String> params) {
    Result<DefaultIssue> result = Result.of();
    try {
      // mandatory parameters
      String componentKey = params.get("component");
      if (StringUtils.isBlank(componentKey)) {
        result.addError("Component is not set");
      }
      RuleKey ruleKey = null;
      String rule = params.get("rule");
      if (StringUtils.isBlank(rule)) {
        result.addError(Result.Message.ofL10n("issue.manual.missing_rule"));
      } else {
        ruleKey = RuleKey.parse(rule);
      }

      if (result.ok()) {
        DefaultIssue issue = issueService.createManualIssue(componentKey, ruleKey, RubyUtils.toInteger(params.get("line")), params.get("message"), params.get("severity"),
          RubyUtils.toDouble(params.get("effortToFix")));
        result.set(issue);
      }

    } catch (Exception e) {
      result.addError(e.getMessage());
    }
    return result;
  }

  public Collection<ActionPlan> findOpenActionPlans(String projectKey) {
    return actionPlanService.findOpenByProjectKey(projectKey, userSession);
  }

  public ActionPlan findActionPlan(String actionPlanKey) {
    return actionPlanService.findByKey(actionPlanKey, userSession);
  }

  public List<ActionPlanStats> findActionPlanStats(String projectKey) {
    return actionPlanService.findActionPlanStats(projectKey, userSession);
  }

  public Result<ActionPlan> createActionPlan(Map<String, String> parameters) {
    Result<ActionPlan> result = createActionPlanResult(parameters);
    if (result.ok()) {
      result.set(actionPlanService.create(result.get(), userSession));
    }
    return result;
  }

  public Result<ActionPlan> updateActionPlan(String key, Map<String, String> parameters) {
    DefaultActionPlan existingActionPlan = (DefaultActionPlan) actionPlanService.findByKey(key, userSession);
    if (existingActionPlan == null) {
      Result<ActionPlan> result = Result.of();
      result.addError(Result.Message.ofL10n(ACTION_PLANS_ERRORS_ACTION_PLAN_DOES_NOT_EXIST_MESSAGE, key));
      return result;
    } else {
      Result<ActionPlan> result = createActionPlanResult(parameters, existingActionPlan);
      if (result.ok()) {
        DefaultActionPlan actionPlan = (DefaultActionPlan) result.get();
        actionPlan.setKey(existingActionPlan.key());
        actionPlan.setUserLogin(existingActionPlan.userLogin());
        result.set(actionPlanService.update(actionPlan, userSession));
      }
      return result;
    }
  }

  public Result<ActionPlan> closeActionPlan(String actionPlanKey) {
    Result<ActionPlan> result = createResultForExistingActionPlan(actionPlanKey);
    if (result.ok()) {
      result.set(actionPlanService.setStatus(actionPlanKey, ActionPlan.STATUS_CLOSED, userSession));
    }
    return result;
  }

  public Result<ActionPlan> openActionPlan(String actionPlanKey) {
    Result<ActionPlan> result = createResultForExistingActionPlan(actionPlanKey);
    if (result.ok()) {
      result.set(actionPlanService.setStatus(actionPlanKey, ActionPlan.STATUS_OPEN, userSession));
    }
    return result;
  }

  public Result<ActionPlan> deleteActionPlan(String actionPlanKey) {
    Result<ActionPlan> result = createResultForExistingActionPlan(actionPlanKey);
    if (result.ok()) {
      actionPlanService.delete(actionPlanKey, userSession);
    }
    return result;
  }

  @VisibleForTesting
  Result createActionPlanResult(Map<String, String> parameters) {
    return createActionPlanResult(parameters, null);
  }

  @VisibleForTesting
  Result<ActionPlan> createActionPlanResult(Map<String, String> parameters, @Nullable DefaultActionPlan existingActionPlan) {
    Result<ActionPlan> result = Result.of();

    String name = parameters.get(NAME_PARAM);
    String description = parameters.get(DESCRIPTION_PARAM);
    String deadLineParam = parameters.get("deadLine");
    String projectParam = parameters.get(PROJECT_PARAM);

    checkMandatorySizeParameter(name, NAME_PARAM, 200, result);
    checkOptionalSizeParameter(description, DESCRIPTION_PARAM, 1000, result);

    // Can only set project on creation
    if (existingActionPlan == null) {
      checkProject(projectParam, result);
    }
    Date deadLine = checkAndReturnDeadline(deadLineParam, result);

    // TODO move this check in the service, on creation and update
    if (!Strings.isNullOrEmpty(projectParam) && !Strings.isNullOrEmpty(name) && isActionPlanNameAvailable(existingActionPlan, name, projectParam)) {
      result.addError(Result.Message.ofL10n("action_plans.same_name_in_same_project"));
    }

    if (result.ok()) {
      DefaultActionPlan actionPlan = DefaultActionPlan.create(name)
        .setDescription(description)
        .setUserLogin(userSession.getLogin())
        .setDeadLine(deadLine);

      // Can only set project on creation
      if (existingActionPlan == null) {
        actionPlan.setProjectKey(projectParam);
      } else {
        actionPlan.setProjectKey(existingActionPlan.projectKey());
      }

      result.set(actionPlan);
    }
    return result;
  }

  private boolean isActionPlanNameAvailable(@Nullable DefaultActionPlan existingActionPlan, String name, String projectParam) {
    return (existingActionPlan == null || !name.equals(existingActionPlan.name())) && actionPlanService.isNameAlreadyUsedForProject(name, projectParam);
  }

  private void checkProject(String projectParam, Result<ActionPlan> result) {
    if (Strings.isNullOrEmpty(projectParam)) {
      result.addError(Result.Message.ofL10n(Validation.CANT_BE_EMPTY_MESSAGE, PROJECT_PARAM));
    } else {
      ResourceDto project = resourceDao.getResource(ResourceQuery.create().setKey(projectParam));
      if (project == null) {
        result.addError(Result.Message.ofL10n("action_plans.errors.project_does_not_exist", projectParam));
      }
    }
  }

  private static Date checkAndReturnDeadline(String deadLineParam, Result<ActionPlan> result) {
    Date deadLine = null;
    if (!Strings.isNullOrEmpty(deadLineParam)) {
      try {
        deadLine = RubyUtils.toDate(deadLineParam);
        Date today = new Date();
        if (deadLine != null && deadLine.before(today) && !org.apache.commons.lang.time.DateUtils.isSameDay(deadLine, today)) {
          result.addError(Result.Message.ofL10n("action_plans.date_cant_be_in_past"));
        }
      } catch (SonarException e) {
        result.addError(Result.Message.ofL10n("errors.is_not_valid", "date"));
      }
    }
    return deadLine;
  }

  private Result<ActionPlan> createResultForExistingActionPlan(String actionPlanKey) {
    Result<ActionPlan> result = Result.of();
    if (findActionPlan(actionPlanKey) == null) {
      result.addError(Result.Message.ofL10n(ACTION_PLANS_ERRORS_ACTION_PLAN_DOES_NOT_EXIST_MESSAGE, actionPlanKey));
    }
    return result;
  }

  public Result<Issue> executeAction(String issueKey, String actionKey) {
    Result<Issue> result = Result.of();
    try {
      result.set(actionService.execute(issueKey, actionKey, userSession));
    } catch (Exception e) {
      result.addError(e.getMessage());
    }
    return result;
  }

  public List<Action> listActions(String issueKey) {
    return actionService.listAvailableActions(issueKey);
  }

  public List<Action> listActions(Issue issue) {
    return actionService.listAvailableActions(issue);
  }

  public IssueQuery emptyIssueQuery() {
    return issueQueryService.createFromMap(Maps.<String, Object>newHashMap());
  }

  @CheckForNull
  public IssueFilterDto findIssueFilterById(Long id) {
    return issueFilterService.findById(id);
  }

  /**
   * Return the issue filter if the user has the right to see it
   * Never return null
   */
  public IssueFilterDto findIssueFilter(Long id) {
    return issueFilterService.find(id, userSession);
  }

  public boolean isUserAuthorized(IssueFilterDto issueFilter) {
    try {
      String user = issueFilterService.getLoggedLogin(userSession);
      issueFilterService.verifyCurrentUserCanReadFilter(issueFilter, user);
      return true;
    } catch (Exception e) {
      return false;
    }
  }

  public boolean canUserShareIssueFilter() {
    return issueFilterService.canShareFilter(userSession);
  }

  public String serializeFilterQuery(Map<String, Object> filterQuery) {
    return issueFilterService.serializeFilterQuery(filterQuery);
  }

  public Map<String, Object> deserializeFilterQuery(IssueFilterDto issueFilter) {
    return issueFilterService.deserializeIssueFilterQuery(issueFilter);
  }

  public Map<String, Object> sanitizeFilterQuery(Map<String, Object> filterQuery) {
    return Maps.filterEntries(filterQuery, new Predicate<Map.Entry<String, Object>>() {
      @Override
      public boolean apply(Map.Entry<String, Object> input) {
        return IssueFilterParameters.ALL.contains(input.getKey());
      }
    });
  }

  /**
   * Execute issue filter from parameters
   */
  public IssueFilterService.IssueFilterResult execute(Map<String, Object> props) {
    return issueFilterService.execute(issueQueryService.createFromMap(props), toSearchOptions(props));
  }

  /**
   * Execute issue filter from existing filter with optional overridable parameters
   */
  public IssueFilterService.IssueFilterResult execute(Long issueFilterId, Map<String, Object> overrideProps) {
    IssueFilterDto issueFilter = issueFilterService.find(issueFilterId, userSession);
    Map<String, Object> props = issueFilterService.deserializeIssueFilterQuery(issueFilter);
    overrideProps(props, overrideProps);
    return execute(props);
  }

  private static void overrideProps(Map<String, Object> props, Map<String, Object> overrideProps) {
    for (Map.Entry<String, Object> entry : overrideProps.entrySet()) {
      props.put(entry.getKey(), entry.getValue());
    }
  }

  /**
   * List user issue filter
   */
  public List<IssueFilterDto> findIssueFiltersForCurrentUser() {
    return issueFilterService.findByUser(userSession);
  }

  /**
   * Create issue filter
   */
  public IssueFilterDto createIssueFilter(Map<String, String> parameters) {
    IssueFilterDto result = createIssueFilterResultForNew(parameters);
    return issueFilterService.save(result, userSession);
  }

  /**
   * Update issue filter
   */
  public IssueFilterDto updateIssueFilter(Map<String, String> parameters) {
    IssueFilterDto result = createIssueFilterResultForUpdate(parameters);
    return issueFilterService.update(result, userSession);
  }

  /**
   * Update issue filter data
   */
  public IssueFilterDto updateIssueFilterQuery(Long issueFilterId, Map<String, Object> data) {
    return issueFilterService.updateFilterQuery(issueFilterId, data, userSession);
  }

  /**
   * Delete issue filter
   */
  public void deleteIssueFilter(Long issueFilterId) {
    issueFilterService.delete(issueFilterId, userSession);
  }

  /**
   * Copy issue filter
   */
  public IssueFilterDto copyIssueFilter(Long issueFilterIdToCopy, Map<String, String> parameters) {
    IssueFilterDto result = createIssueFilterResultForCopy(parameters);
    return issueFilterService.copy(issueFilterIdToCopy, result, userSession);
  }

  @VisibleForTesting
  IssueFilterDto createIssueFilterResultForNew(Map<String, String> params) {
    return createIssueFilterResult(params, false, false);
  }

  @VisibleForTesting
  IssueFilterDto createIssueFilterResultForUpdate(Map<String, String> params) {
    return createIssueFilterResult(params, true, true);
  }

  @VisibleForTesting
  IssueFilterDto createIssueFilterResultForCopy(Map<String, String> params) {
    return createIssueFilterResult(params, false, false);
  }

  @VisibleForTesting
  IssueFilterDto createIssueFilterResult(Map<String, String> params, boolean checkId, boolean checkUser) {
    String id = params.get(ID_PARAM);
    String name = params.get(NAME_PARAM);
    String description = params.get(DESCRIPTION_PARAM);
    String data = params.get("data");
    String user = params.get(USER_PARAM);
    Boolean sharedParam = RubyUtils.toBoolean(params.get("shared"));
    boolean shared = sharedParam != null ? sharedParam : false;

    if (checkId) {
      Validation.checkMandatoryParameter(id, ID_PARAM);
    }
    if (checkUser) {
      Validation.checkMandatoryParameter(user, USER_PARAM);
    }
    Validation.checkMandatorySizeParameter(name, NAME_PARAM, 100);
    checkOptionalSizeParameter(description, DESCRIPTION_PARAM, 4000);

    IssueFilterDto issueFilterDto = new IssueFilterDto()
      .setName(name)
      .setDescription(description)
      .setShared(shared)
      .setUserLogin(user)
      .setData(data);
    if (!Strings.isNullOrEmpty(id)) {
      issueFilterDto.setId(Long.valueOf(id));
    }
    return issueFilterDto;
  }

  public List<IssueFilterDto> findSharedFiltersForCurrentUser() {
    return issueFilterService.findSharedFiltersWithoutUserFilters(userSession);
  }

  public List<IssueFilterDto> findFavouriteIssueFiltersForCurrentUser() {
    return issueFilterService.findFavoriteFilters(userSession);
  }

  public boolean toggleFavouriteIssueFilter(Long issueFilterId) {
    return issueFilterService.toggleFavouriteIssueFilter(issueFilterId, userSession);
  }

  /**
   * Execute a bulk change
   */
  public IssueBulkChangeResult bulkChange(Map<String, Object> props, String comment, boolean sendNotifications) {
    IssueBulkChangeQuery issueBulkChangeQuery = new IssueBulkChangeQuery(props, comment, sendNotifications);
    return issueBulkChangeService.execute(issueBulkChangeQuery, userSession);
  }

  private static void checkMandatoryParameter(String value, String paramName, Result result) {
    if (Strings.isNullOrEmpty(value)) {
      result.addError(Result.Message.ofL10n(Validation.CANT_BE_EMPTY_MESSAGE, paramName));
    }
  }

  private static void checkMandatorySizeParameter(String value, String paramName, Integer size, Result result) {
    checkMandatoryParameter(value, paramName, result);
    if (!Strings.isNullOrEmpty(value) && value.length() > size) {
      result.addError(Result.Message.ofL10n(Validation.IS_TOO_LONG_MESSAGE, paramName, size));
    }
  }

  private static void checkOptionalSizeParameter(String value, String paramName, Integer size, Result result) {
    if (!Strings.isNullOrEmpty(value) && value.length() > size) {
      result.addError(Result.Message.ofL10n(Validation.IS_TOO_LONG_MESSAGE, paramName, size));
    }
  }

  private static void checkOptionalSizeParameter(String value, String paramName, Integer size) {
    if (!Strings.isNullOrEmpty(value) && value.length() > size) {
      throw new BadRequestException(Validation.IS_TOO_LONG_MESSAGE, paramName, size);
    }
  }

  /**
   * Do not make this method static as it's called by rails
   */
  public int maxPageSize() {
    return QueryContext.MAX_LIMIT;
  }

  @VisibleForTesting
  static SearchOptions toSearchOptions(Map<String, Object> props) {
    SearchOptions options = new SearchOptions();
    Integer pageIndex = RubyUtils.toInteger(props.get(IssueFilterParameters.PAGE_INDEX));
    Integer pageSize = RubyUtils.toInteger(props.get(IssueFilterParameters.PAGE_SIZE));
    if (pageSize != null && pageSize < 0) {
      options.setLimit(SearchOptions.MAX_LIMIT);
    } else {
      options.setPage(pageIndex != null ? pageIndex : 1, pageSize != null ? pageSize : 100);
    }
    return options;
  }

  public Collection<String> listTags() {
    return issueService.listTags(null, 0);
  }

  public Map<String, Long> listTagsForComponent(String componentUuid, int pageSize) {
    IssueQuery query = issueQueryService.createFromMap(
      ImmutableMap.<String, Object>of(
        "componentUuids", componentUuid,
        "resolved", false));
    return issueService.listTagsForComponent(query, pageSize);
  }

  public boolean isUserIssueAdmin(String projectUuid) {
    return userSession.hasProjectPermissionByUuid(UserRole.ISSUE_ADMIN, projectUuid);
  }

  /**
   * Used by issue modification actions currently implemented in Rails
   * @param issue
   * @return the JSON representation of the modified issue, as a ready to use string
   */
  public String writeIssueJson(Issue issue) {
    StringWriter writer = new StringWriter();
    JsonWriter json = JsonWriter.of(writer);
    DbSession dbSession = dbClient.openSession(false);
    try {
      Map<String, User> usersByLogin = getIssueUsersByLogin(issue);

      Set<String> componentUuids = ImmutableSet.of(issue.componentUuid());
      Set<String> projectUuids = Sets.newHashSet();
      Set<ComponentDto> componentDtos = Sets.newHashSet();
      List<ComponentDto> projectDtos = Lists.newArrayList();

      Map<String, ComponentDto> componentsByUuid = Maps.newHashMap();
      Map<String, ComponentDto> projectsByComponentUuid = Maps.newHashMap();

      List<ComponentDto> fileDtos = dbClient.componentDao().selectByUuids(dbSession, componentUuids);
      List<ComponentDto> subProjectDtos = dbClient.componentDao().selectSubProjectsByComponentUuids(dbSession, componentUuids);
      componentDtos.addAll(fileDtos);
      componentDtos.addAll(subProjectDtos);
      for (ComponentDto component : componentDtos) {
        projectUuids.add(component.projectUuid());
      }
      projectDtos.addAll(dbClient.componentDao().selectByUuids(dbSession, projectUuids));
      componentDtos.addAll(projectDtos);

      for (ComponentDto componentDto : componentDtos) {
        componentsByUuid.put(componentDto.uuid(), componentDto);
      }

      projectsByComponentUuid = issueComponentHelper.prepareComponentsAndProjects(projectUuids, componentUuids, componentsByUuid, componentDtos, subProjectDtos, dbSession);

      json.beginObject().name("issue");
      issueWriter.write(json, issue,
        usersByLogin,
        componentsByUuid,
        projectsByComponentUuid,
        ImmutableMultimap.<String, DefaultIssueComment>of(),
        ImmutableMap.<String, ActionPlan>of(),
        ImmutableList.of(IssueJsonWriter.ACTIONS_EXTRA_FIELD, IssueJsonWriter.TRANSITIONS_EXTRA_FIELD));
      json.endObject().close();
    } finally {
      MyBatis.closeQuietly(dbSession);
      IOUtils.closeQuietly(writer);
    }
    return writer.toString();
  }

  private Map<String, User> getIssueUsersByLogin(Issue issue) {
    Map<String, User> usersByLogin = Maps.newHashMap();
    if (issue.assignee() != null) {
      usersByLogin.put(issue.assignee(), userIndex.getByLogin(issue.assignee()));
    }
    if (issue.reporter() != null) {
      usersByLogin.put(issue.reporter(), userIndex.getByLogin(issue.reporter()));
    }
    return usersByLogin;
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/issue/ws/IssueJsonWriter.java
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

package org.sonar.server.issue.ws;

import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Multimap;
import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.CheckForNull;
import javax.annotation.Nullable;
import org.sonar.api.i18n.I18n;
import org.sonar.api.issue.ActionPlan;
import org.sonar.api.issue.Issue;
import org.sonar.api.issue.IssueComment;
import org.sonar.api.issue.internal.DefaultIssueComment;
import org.sonar.api.user.User;
import org.sonar.api.utils.DateUtils;
import org.sonar.api.utils.Duration;
import org.sonar.api.utils.Durations;
import org.sonar.api.utils.text.JsonWriter;
import org.sonar.core.component.ComponentDto;
import org.sonar.markdown.Markdown;
import org.sonar.server.user.UserSession;
import org.sonar.server.user.ws.UserJsonWriter;

public class IssueJsonWriter {

  public static final String ACTIONS_EXTRA_FIELD = "actions";
  public static final String TRANSITIONS_EXTRA_FIELD = "transitions";
  public static final String REPORTER_NAME_EXTRA_FIELD = "reporterName";
  public static final String ACTION_PLAN_NAME_EXTRA_FIELD = "actionPlanName";

  public static final Set<String> EXTRA_FIELDS = ImmutableSet.of(
    ACTIONS_EXTRA_FIELD, TRANSITIONS_EXTRA_FIELD, REPORTER_NAME_EXTRA_FIELD, ACTION_PLAN_NAME_EXTRA_FIELD);

  private final I18n i18n;
  private final Durations durations;
  private final UserSession userSession;
  private final UserJsonWriter userWriter;
  private final IssueActionsWriter actionsWriter;

  public IssueJsonWriter(I18n i18n, Durations durations, UserSession userSession, UserJsonWriter userWriter, IssueActionsWriter actionsWriter) {
    this.i18n = i18n;
    this.durations = durations;
    this.userSession = userSession;
    this.userWriter = userWriter;
    this.actionsWriter = actionsWriter;
  }

  public void write(JsonWriter json, Issue issue, Map<String, User> usersByLogin, Map<String, ComponentDto> componentsByUuid,
    Map<String, ComponentDto> projectsByComponentUuid, Multimap<String, DefaultIssueComment> commentsByIssues, Map<String, ActionPlan> actionPlanByKeys, List<String> extraFields) {
    json.beginObject();

    String actionPlanKey = issue.actionPlanKey();
    ComponentDto file = componentsByUuid.get(issue.componentUuid());
    ComponentDto project = null, subProject = null;
    if (file != null) {
      project = projectsByComponentUuid.get(file.uuid());
      if (!file.projectUuid().equals(file.moduleUuid())) {
        subProject = componentsByUuid.get(file.moduleUuid());
      }
    }
    Duration debt = issue.debt();
    Date updateDate = issue.updateDate();

    json
      .prop("key", issue.key())
      .prop("component", file != null ? file.getKey() : null)
      // Only used for the compatibility with the Issues Java WS Client <= 4.4 used by Eclipse
      .prop("componentId", file != null ? file.getId() : null)
      .prop("project", project != null ? project.getKey() : null)
      .prop("subProject", subProject != null ? subProject.getKey() : null)
      .prop("rule", issue.ruleKey().toString())
      .prop("status", issue.status())
      .prop("resolution", issue.resolution())
      .prop("severity", issue.severity())
      .prop("message", issue.message())
      .prop("line", issue.line())
      .prop("debt", debt != null ? durations.encode(debt) : null)
      .prop("reporter", issue.reporter())
      .prop("author", issue.authorLogin())
      .prop("actionPlan", actionPlanKey)
      .prop("creationDate", isoDate(issue.creationDate()))
      .prop("updateDate", isoDate(updateDate))
      // TODO Remove as part of Front-end rework on Issue Domain
      .prop("fUpdateAge", formatAgeDate(updateDate))
      .prop("closeDate", isoDate(issue.closeDate()));

    json.name("assignee");
    userWriter.write(json, usersByLogin.get(issue.assignee()));

    writeTags(issue, json);
    writeIssueComments(commentsByIssues.get(issue.key()), usersByLogin, json);
    writeIssueAttributes(issue, json);
    writeIssueExtraFields(issue, usersByLogin, actionPlanByKeys, extraFields, json);
    json.endObject();
  }

  @CheckForNull
  private static String isoDate(@Nullable Date date) {
    if (date != null) {
      return DateUtils.formatDateTime(date);
    }
    return null;
  }

  private static void writeTags(Issue issue, JsonWriter json) {
    Collection<String> tags = issue.tags();
    if (tags != null && !tags.isEmpty()) {
      json.name("tags").beginArray();
      for (String tag : tags) {
        json.value(tag);
      }
      json.endArray();
    }
  }

  private void writeIssueComments(Collection<DefaultIssueComment> issueComments, Map<String, User> usersByLogin, JsonWriter json) {
    if (!issueComments.isEmpty()) {
      json.name("comments").beginArray();
      String login = userSession.getLogin();
      for (IssueComment comment : issueComments) {
        String userLogin = comment.userLogin();
        User user = userLogin != null ? usersByLogin.get(userLogin) : null;
        json.beginObject()
          .prop("key", comment.key())
          .prop("login", comment.userLogin())
          .prop("email", user != null ? user.email() : null)
          .prop("userName", user != null ? user.name() : null)
          .prop("htmlText", Markdown.convertToHtml(comment.markdownText()))
          .prop("markdown", comment.markdownText())
          .prop("updatable", login != null && login.equals(userLogin))
          .prop("createdAt", DateUtils.formatDateTime(comment.createdAt()))
          .endObject();
      }
      json.endArray();
    }
  }

  private static void writeIssueAttributes(Issue issue, JsonWriter json) {
    if (!issue.attributes().isEmpty()) {
      json.name("attr").beginObject();
      for (Map.Entry<String, String> entry : issue.attributes().entrySet()) {
        json.prop(entry.getKey(), entry.getValue());
      }
      json.endObject();
    }
  }

  private void writeIssueExtraFields(Issue issue, Map<String, User> usersByLogin, Map<String, ActionPlan> actionPlanByKeys,
    @Nullable List<String> extraFields,
    JsonWriter json) {
    if (extraFields != null) {
      if (extraFields.contains(ACTIONS_EXTRA_FIELD)) {
        actionsWriter.writeActions(issue, json);
      }

      if (extraFields.contains(TRANSITIONS_EXTRA_FIELD)) {
        actionsWriter.writeTransitions(issue, json);
      }

      writeReporterIfNeeded(issue, usersByLogin, extraFields, json);

      writeActionPlanIfNeeded(issue, actionPlanByKeys, extraFields, json);
    }
  }

  private void writeReporterIfNeeded(Issue issue, Map<String, User> usersByLogin, List<String> extraFields, JsonWriter json) {
    String reporter = issue.reporter();
    if (extraFields.contains(REPORTER_NAME_EXTRA_FIELD) && reporter != null) {
      User user = usersByLogin.get(reporter);
      json.prop(REPORTER_NAME_EXTRA_FIELD, user != null ? user.name() : null);
    }
  }

  private void writeActionPlanIfNeeded(Issue issue, Map<String, ActionPlan> actionPlanByKeys, List<String> extraFields, JsonWriter json) {
    String actionPlanKey = issue.actionPlanKey();
    if (extraFields.contains(ACTION_PLAN_NAME_EXTRA_FIELD) && actionPlanKey != null) {
      ActionPlan actionPlan = actionPlanByKeys.get(actionPlanKey);
      json.prop(ACTION_PLAN_NAME_EXTRA_FIELD, actionPlan != null ? actionPlan.name() : null);
    }
  }

  @CheckForNull
  private String formatAgeDate(@Nullable Date date) {
    if (date != null) {
      return i18n.ageFromNow(userSession.locale(), date);
    }
    return null;
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/issue/InternalRubyIssueServiceTest.java
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

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.mockito.ArgumentCaptor;
import org.sonar.api.issue.ActionPlan;
import org.sonar.api.issue.Issue;
import org.sonar.api.issue.action.Action;
import org.sonar.api.issue.internal.DefaultIssue;
import org.sonar.api.issue.internal.FieldDiffs;
import org.sonar.api.user.User;
import org.sonar.api.web.UserRole;
import org.sonar.core.issue.DefaultActionPlan;
import org.sonar.core.issue.db.IssueFilterDto;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.resource.ResourceDao;
import org.sonar.core.resource.ResourceDto;
import org.sonar.core.resource.ResourceQuery;
import org.sonar.server.db.DbClient;
import org.sonar.server.es.SearchOptions;
import org.sonar.server.exceptions.BadRequestException;
import org.sonar.server.exceptions.Message;
import org.sonar.server.issue.actionplan.ActionPlanService;
import org.sonar.server.issue.filter.IssueFilterService;
import org.sonar.server.issue.ws.IssueComponentHelper;
import org.sonar.server.issue.ws.IssueJsonWriter;
import org.sonar.server.tester.UserSessionRule;
import org.sonar.server.user.ThreadLocalUserSession;
import org.sonar.server.user.index.UserIndex;

import static com.google.common.collect.Lists.newArrayList;
import static com.google.common.collect.Maps.newHashMap;
import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.fail;
import static org.mockito.Matchers.any;
import static org.mockito.Matchers.anyString;
import static org.mockito.Matchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class InternalRubyIssueServiceTest {
  @Rule
  public UserSessionRule userSessionRule = UserSessionRule.standalone();

  IssueService issueService;

  IssueQueryService issueQueryService;

  IssueCommentService commentService;

  IssueChangelogService changelogService;

  ActionPlanService actionPlanService;

  ResourceDao resourceDao;

  ActionService actionService;

  IssueFilterService issueFilterService;

  IssueBulkChangeService issueBulkChangeService;

  InternalRubyIssueService service;

  IssueJsonWriter issueWriter;

  IssueComponentHelper issueComponentHelper;

  UserIndex userIndex;

  DbClient dbClient;

  DbSession dbSession;

  @Before
  public void setUp() {
    issueService = mock(IssueService.class);
    issueQueryService = mock(IssueQueryService.class);
    commentService = mock(IssueCommentService.class);
    changelogService = mock(IssueChangelogService.class);
    actionPlanService = mock(ActionPlanService.class);
    resourceDao = mock(ResourceDao.class);
    actionService = mock(ActionService.class);
    issueFilterService = mock(IssueFilterService.class);
    issueBulkChangeService = mock(IssueBulkChangeService.class);
    issueWriter = mock(IssueJsonWriter.class);
    issueComponentHelper = mock(IssueComponentHelper.class);
    userIndex = mock(UserIndex.class);
    dbClient = mock(DbClient.class);
    dbSession = mock(DbSession.class);

    ResourceDto project = new ResourceDto().setKey("org.sonar.Sample");
    when(resourceDao.getResource(any(ResourceQuery.class))).thenReturn(project);

    service = new InternalRubyIssueService(issueService, issueQueryService, commentService, changelogService, actionPlanService, resourceDao, actionService,
      issueFilterService, issueBulkChangeService, issueWriter, issueComponentHelper, userIndex, dbClient, userSessionRule);
  }

  @Test
  public void get_issue_by_key() {
    service.getIssueByKey("ABCD");
    verify(issueService).getByKey("ABCD");
  }

  @Test
  public void list_transitions_by_issue_key() {
    service.listTransitions("ABCD");
    verify(issueService).listTransitions(eq("ABCD"));
  }

  @Test
  public void list_transitions_by_issue() {
    Issue issue = new DefaultIssue().setKey("ABCD");
    service.listTransitions(issue);
    verify(issueService).listTransitions(eq(issue));
  }

  @Test
  public void list_status() {
    service.listStatus();
    verify(issueService).listStatus();
  }

  @Test
  public void list_resolutions() {
    assertThat(service.listResolutions()).isEqualTo(Issue.RESOLUTIONS);
  }

  @Test
  public void list_plugin_actions() {
    Action action = mock(Action.class);
    when(action.key()).thenReturn("link-to-jira");

    when(actionService.listAllActions()).thenReturn(newArrayList(action));

    assertThat(service.listPluginActions()).containsOnly("link-to-jira");
  }

  @Test
  public void find_comments_by_issue_key() {
    service.findComments("ABCD");
    verify(commentService).findComments("ABCD");
  }

  @Test
  public void find_comments_by_issue_keys() {
    service.findCommentsByIssueKeys(newArrayList("ABCD"));
    verify(commentService).findComments(newArrayList("ABCD"));
  }

  @Test
  public void do_transition() {
    service.doTransition("ABCD", Issue.STATUS_RESOLVED);
    verify(issueService).doTransition(eq("ABCD"), eq(Issue.STATUS_RESOLVED));
  }

  @Test
  public void create_action_plan() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");
    parameters.put("project", "org.sonar.Sample");
    parameters.put("deadLine", "2113-05-13");

    Result result = service.createActionPlan(parameters);
    assertThat(result.ok()).isTrue();

    ArgumentCaptor<ActionPlan> actionPlanCaptor = ArgumentCaptor.forClass(ActionPlan.class);
    verify(actionPlanService).create(actionPlanCaptor.capture(), any(ThreadLocalUserSession.class));
    ActionPlan actionPlan = actionPlanCaptor.getValue();

    assertThat(actionPlan).isNotNull();
    assertThat(actionPlan.key()).isNotNull();
    assertThat(actionPlan.name()).isEqualTo("Long term");
    assertThat(actionPlan.description()).isEqualTo("Long term issues");
    assertThat(actionPlan.deadLine()).isNotNull();
  }

  @Test
  public void update_action_plan() {
    when(actionPlanService.findByKey(eq("ABCD"), any(ThreadLocalUserSession.class))).thenReturn(DefaultActionPlan.create("Long term"));

    Map<String, String> parameters = newHashMap();
    parameters.put("name", "New Long term");
    parameters.put("description", "New Long term issues");
    parameters.put("deadLine", "2113-05-13");
    parameters.put("project", "org.sonar.MultiSample");

    Result result = service.updateActionPlan("ABCD", parameters);
    assertThat(result.ok()).isTrue();

    ArgumentCaptor<ActionPlan> actionPlanCaptor = ArgumentCaptor.forClass(ActionPlan.class);
    verify(actionPlanService).update(actionPlanCaptor.capture(), any(ThreadLocalUserSession.class));
    ActionPlan actionPlan = actionPlanCaptor.getValue();

    assertThat(actionPlan).isNotNull();
    assertThat(actionPlan.key()).isNotNull();
    assertThat(actionPlan.name()).isEqualTo("New Long term");
    assertThat(actionPlan.description()).isEqualTo("New Long term issues");
    assertThat(actionPlan.deadLine()).isNotNull();
  }

  @Test
  public void update_action_plan_with_new_project() {
    when(actionPlanService.findByKey(eq("ABCD"), any(ThreadLocalUserSession.class))).thenReturn(DefaultActionPlan.create("Long term").setProjectKey("org.sonar.MultiSample"));

    Map<String, String> parameters = newHashMap();
    parameters.put("name", "New Long term");
    parameters.put("description", "New Long term issues");
    parameters.put("deadLine", "2113-05-13");

    ArgumentCaptor<ActionPlan> actionPlanCaptor = ArgumentCaptor.forClass(ActionPlan.class);
    Result result = service.updateActionPlan("ABCD", parameters);
    assertThat(result.ok()).isTrue();

    verify(actionPlanService).update(actionPlanCaptor.capture(), any(ThreadLocalUserSession.class));
    ActionPlan actionPlan = actionPlanCaptor.getValue();

    assertThat(actionPlan).isNotNull();
    assertThat(actionPlan.key()).isNotNull();
    assertThat(actionPlan.name()).isEqualTo("New Long term");
    assertThat(actionPlan.description()).isEqualTo("New Long term issues");
    assertThat(actionPlan.deadLine()).isNotNull();
    assertThat(actionPlan.projectKey()).isEqualTo("org.sonar.MultiSample");
  }

  @Test
  public void not_update_action_plan_when_action_plan_is_not_found() {
    when(actionPlanService.findByKey(eq("ABCD"), any(ThreadLocalUserSession.class))).thenReturn(null);

    Result result = service.updateActionPlan("ABCD", null);
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("action_plans.errors.action_plan_does_not_exist", "ABCD"));
  }

  @Test
  public void delete_action_plan() {
    when(actionPlanService.findByKey(eq("ABCD"), any(ThreadLocalUserSession.class))).thenReturn(DefaultActionPlan.create("Long term"));

    Result result = service.deleteActionPlan("ABCD");
    verify(actionPlanService).delete(eq("ABCD"), any(ThreadLocalUserSession.class));
    assertThat(result.ok()).isTrue();
  }

  @Test
  public void not_delete_action_plan_if_action_plan_not_found() {
    when(actionPlanService.findByKey(eq("ABCD"), any(ThreadLocalUserSession.class))).thenReturn(null);

    Result result = service.deleteActionPlan("ABCD");
    verify(actionPlanService, never()).delete(eq("ABCD"), any(ThreadLocalUserSession.class));
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("action_plans.errors.action_plan_does_not_exist", "ABCD"));
  }

  @Test
  public void close_action_plan() {
    when(actionPlanService.findByKey(eq("ABCD"), any(ThreadLocalUserSession.class))).thenReturn(DefaultActionPlan.create("Long term"));

    Result result = service.closeActionPlan("ABCD");
    verify(actionPlanService).setStatus(eq("ABCD"), eq("CLOSED"), any(ThreadLocalUserSession.class));
    assertThat(result.ok()).isTrue();
  }

  @Test
  public void open_action_plan() {
    when(actionPlanService.findByKey(eq("ABCD"), any(ThreadLocalUserSession.class))).thenReturn(DefaultActionPlan.create("Long term"));

    Result result = service.openActionPlan("ABCD");
    verify(actionPlanService).setStatus(eq("ABCD"), eq("OPEN"), any(ThreadLocalUserSession.class));
    assertThat(result.ok()).isTrue();
  }

  @Test
  public void get_error_on_action_plan_result_when_no_project() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");

    Result result = service.createActionPlanResult(parameters);
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("errors.cant_be_empty", "project"));
  }

  @Test
  public void get_error_on_action_plan_result_when_no_name() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", null);
    parameters.put("description", "Long term issues");
    parameters.put("project", "org.sonar.Sample");

    Result result = service.createActionPlanResult(parameters);
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("errors.cant_be_empty", "name"));
  }

  @Test
  public void get_error_on_action_plan_result_when_name_is_too_long() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", createLongString(201));
    parameters.put("description", "Long term issues");
    parameters.put("project", "org.sonar.Sample");

    Result result = service.createActionPlanResult(parameters);
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("errors.is_too_long", "name", 200));
  }

  @Test
  public void get_error_on_action_plan_result_when_description_is_too_long() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", createLongString(1001));
    parameters.put("project", "org.sonar.Sample");

    Result result = service.createActionPlanResult(parameters);
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("errors.is_too_long", "description", 1000));
  }

  @Test
  public void get_error_on_action_plan_result_when_dead_line_use_wrong_format() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");
    parameters.put("project", "org.sonar.Sample");
    parameters.put("deadLine", "18/05/2013");

    Result result = service.createActionPlanResult(parameters);
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("errors.is_not_valid", "date"));
  }

  @Test
  public void get_error_on_action_plan_result_when_dead_line_is_in_the_past() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");
    parameters.put("project", "org.sonar.Sample");
    parameters.put("deadLine", "2000-01-01");

    Result result = service.createActionPlanResult(parameters);
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("action_plans.date_cant_be_in_past"));
  }

  @Test
  public void get_error_on_action_plan_result_when_name_is_already_used_for_project() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");
    parameters.put("project", "org.sonar.Sample");

    when(actionPlanService.isNameAlreadyUsedForProject(anyString(), anyString())).thenReturn(true);

    Result result = service.createActionPlanResult(parameters, DefaultActionPlan.create("Short term"));
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("action_plans.same_name_in_same_project"));
  }

  @Test
  public void get_error_on_action_plan_result_when_project_not_found() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");
    parameters.put("project", "org.sonar.Sample");

    when(resourceDao.getResource(any(ResourceQuery.class))).thenReturn(null);

    Result result = service.createActionPlanResult(parameters);
    assertThat(result.ok()).isFalse();
    assertThat(result.errors()).contains(Result.Message.ofL10n("action_plans.errors.project_does_not_exist", "org.sonar.Sample"));
  }

  @Test
  public void test_changelog_from_issue_key() throws Exception {
    IssueChangelog changelog = new IssueChangelog(Collections.<FieldDiffs>emptyList(), Collections.<User>emptyList());
    when(changelogService.changelog(eq("ABCDE"))).thenReturn(changelog);

    IssueChangelog result = service.changelog("ABCDE");

    assertThat(result).isSameAs(changelog);
  }

  @Test
  public void test_changelog_from_issue() throws Exception {
    Issue issue = new DefaultIssue().setKey("ABCDE");

    IssueChangelog changelog = new IssueChangelog(Collections.<FieldDiffs>emptyList(), Collections.<User>emptyList());
    when(changelogService.changelog(eq(issue))).thenReturn(changelog);

    IssueChangelog result = service.changelog(issue);

    assertThat(result).isSameAs(changelog);
  }

  @Test
  public void create_issue_filter() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");

    service.createIssueFilter(parameters);

    ArgumentCaptor<IssueFilterDto> issueFilterCaptor = ArgumentCaptor.forClass(IssueFilterDto.class);
    verify(issueFilterService).save(issueFilterCaptor.capture(), any(ThreadLocalUserSession.class));
    IssueFilterDto issueFilter = issueFilterCaptor.getValue();
    assertThat(issueFilter.getName()).isEqualTo("Long term");
    assertThat(issueFilter.getDescription()).isEqualTo("Long term issues");
  }

  @Test
  public void update_issue_filter() {
    Map<String, String> parameters = newHashMap();
    parameters.put("id", "10");
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");
    parameters.put("user", "John");

    service.updateIssueFilter(parameters);

    ArgumentCaptor<IssueFilterDto> issueFilterCaptor = ArgumentCaptor.forClass(IssueFilterDto.class);
    verify(issueFilterService).update(issueFilterCaptor.capture(), any(ThreadLocalUserSession.class));
    IssueFilterDto issueFilter = issueFilterCaptor.getValue();
    assertThat(issueFilter.getId()).isEqualTo(10L);
    assertThat(issueFilter.getName()).isEqualTo("Long term");
    assertThat(issueFilter.getDescription()).isEqualTo("Long term issues");
  }

  @Test
  public void update_data() {
    Map<String, Object> data = newHashMap();
    service.updateIssueFilterQuery(10L, data);
    verify(issueFilterService).updateFilterQuery(eq(10L), eq(data), any(ThreadLocalUserSession.class));
  }

  @Test
  public void delete_issue_filter() {
    service.deleteIssueFilter(1L);
    verify(issueFilterService).delete(eq(1L), any(ThreadLocalUserSession.class));
  }

  @Test
  public void copy_issue_filter() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Copy of Long term");
    parameters.put("description", "Copy of Long term issues");

    service.copyIssueFilter(1L, parameters);

    ArgumentCaptor<IssueFilterDto> issueFilterCaptor = ArgumentCaptor.forClass(IssueFilterDto.class);
    verify(issueFilterService).copy(eq(1L), issueFilterCaptor.capture(), any(ThreadLocalUserSession.class));
    IssueFilterDto issueFilter = issueFilterCaptor.getValue();
    assertThat(issueFilter.getName()).isEqualTo("Copy of Long term");
    assertThat(issueFilter.getDescription()).isEqualTo("Copy of Long term issues");
  }

  @Test
  public void get_error_on_create_issue_filter_result_when_no_name() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "");
    parameters.put("description", "Long term issues");
    parameters.put("user", "John");

    try {
      service.createIssueFilterResultForNew(parameters);
      fail();
    } catch (Exception e) {
      assertThat(e).isInstanceOf(BadRequestException.class);
      checkBadRequestException(e, "errors.cant_be_empty", "name");
    }
  }

  @Test
  public void get_error_on_create_issue_filter_result_when_name_is_too_long() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", createLongString(101));
    parameters.put("description", "Long term issues");
    parameters.put("user", "John");

    try {
      service.createIssueFilterResultForNew(parameters);
      fail();
    } catch (Exception e) {
      assertThat(e).isInstanceOf(BadRequestException.class);
      checkBadRequestException(e, "errors.is_too_long", "name", 100);
    }
  }

  @Test
  public void get_error_on_create_issue_filter_result_when_description_is_too_long() {
    Map<String, String> parameters = newHashMap();
    parameters.put("name", "Long term");
    parameters.put("description", createLongString(4001));
    parameters.put("user", "John");

    try {
      service.createIssueFilterResultForNew(parameters);
      fail();
    } catch (Exception e) {
      assertThat(e).isInstanceOf(BadRequestException.class);
      checkBadRequestException(e, "errors.is_too_long", "description", 4000);
    }
  }

  @Test
  public void get_error_on_create_issue_filter_result_when_id_is_null_on_update() {
    Map<String, String> parameters = newHashMap();
    parameters.put("id", null);
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");
    parameters.put("user", "John");

    try {
      service.createIssueFilterResultForUpdate(parameters);
      fail();
    } catch (Exception e) {
      assertThat(e).isInstanceOf(BadRequestException.class);
      checkBadRequestException(e, "errors.cant_be_empty", "id");
    }
  }

  @Test
  public void get_error_on_create_issue_filter_result_when_user_is_null_on_update() {
    Map<String, String> parameters = newHashMap();
    parameters.put("id", "10");
    parameters.put("name", "All Open Issues");
    parameters.put("description", "Long term issues");
    parameters.put("user", null);

    try {
      service.createIssueFilterResultForUpdate(parameters);
      fail();
    } catch (Exception e) {
      assertThat(e).isInstanceOf(BadRequestException.class);
      checkBadRequestException(e, "errors.cant_be_empty", "user");
    }
  }

  @Test
  public void get_no_error_on_issue_filter_result_when_id_and_user_are_null_on_copy() {
    Map<String, String> parameters = newHashMap();
    parameters.put("id", null);
    parameters.put("name", "Long term");
    parameters.put("description", "Long term issues");
    parameters.put("user", null);

    IssueFilterDto result = service.createIssueFilterResultForCopy(parameters);
    assertThat(result).isNotNull();
  }

  @Test
  public void execute_issue_filter_from_issue_query() {
    service.execute(Maps.<String, Object>newHashMap());
    verify(issueFilterService).execute(any(IssueQuery.class), any(SearchOptions.class));
  }

  @Test
  public void execute_issue_filter_from_existing_filter() {
    Map<String, Object> props = newHashMap();
    props.put("componentRoots", "struts");
    props.put("statuses", "OPEN");
    when(issueFilterService.deserializeIssueFilterQuery(any(IssueFilterDto.class))).thenReturn(props);

    Map<String, Object> overrideProps = newHashMap();
    overrideProps.put("statuses", "CLOSED");
    overrideProps.put("resolved", true);
    overrideProps.put("pageSize", 20);
    overrideProps.put("pageIndex", 2);

    IssueQuery query = IssueQuery.builder(userSessionRule).build();
    when(issueQueryService.createFromMap(eq(overrideProps))).thenReturn(query);

    service.execute(10L, overrideProps);

    ArgumentCaptor<IssueQuery> issueQueryArgumentCaptor = ArgumentCaptor.forClass(IssueQuery.class);
    ArgumentCaptor<SearchOptions> contextArgumentCaptor = ArgumentCaptor.forClass(SearchOptions.class);

    verify(issueFilterService).execute(issueQueryArgumentCaptor.capture(), contextArgumentCaptor.capture());
    verify(issueFilterService).find(eq(10L), any(ThreadLocalUserSession.class));

    SearchOptions searchOptions = contextArgumentCaptor.getValue();
    assertThat(searchOptions.getLimit()).isEqualTo(20);
    assertThat(searchOptions.getPage()).isEqualTo(2);
  }

  @Test
  public void serialize_filter_query() {
    Map<String, Object> props = newHashMap();
    props.put("componentRoots", "struts");
    service.serializeFilterQuery(props);
    verify(issueFilterService).serializeFilterQuery(props);
  }

  @Test
  public void deserialize_filter_query() {
    IssueFilterDto issueFilter = new IssueFilterDto();
    service.deserializeFilterQuery(issueFilter);
    verify(issueFilterService).deserializeIssueFilterQuery(issueFilter);
  }

  @Test
  public void sanitize_filter_query() {
    Map<String, Object> query = newHashMap();
    query.put("statuses", "CLOSED");
    query.put("resolved", true);
    query.put("unknown", "john");
    Map<String, Object> result = service.sanitizeFilterQuery(query);
    assertThat(result.keySet()).containsOnly("statuses", "resolved");
  }

  @Test
  public void find_user_issue_filters() {
    service.findIssueFiltersForCurrentUser();
    verify(issueFilterService).findByUser(any(ThreadLocalUserSession.class));
  }

  @Test
  public void find_shared_issue_filters() {
    service.findSharedFiltersForCurrentUser();
    verify(issueFilterService).findSharedFiltersWithoutUserFilters(any(ThreadLocalUserSession.class));
  }

  @Test
  public void find_favourite_issue_filters() {
    service.findFavouriteIssueFiltersForCurrentUser();
    verify(issueFilterService).findFavoriteFilters(any(ThreadLocalUserSession.class));
  }

  @Test
  public void toggle_favourite_issue_filter() {
    service.toggleFavouriteIssueFilter(10L);
    verify(issueFilterService).toggleFavouriteIssueFilter(eq(10L), any(ThreadLocalUserSession.class));
  }

  @Test
  public void check_if_user_is_authorized_to_see_issue_filter() {
    IssueFilterDto issueFilter = new IssueFilterDto();
    service.isUserAuthorized(issueFilter);
    verify(issueFilterService).getLoggedLogin(any(ThreadLocalUserSession.class));
    verify(issueFilterService).verifyCurrentUserCanReadFilter(eq(issueFilter), anyString());
  }

  @Test
  public void check_if_user_can_share_issue_filter() {
    service.canUserShareIssueFilter();
    verify(issueFilterService).canShareFilter(any(ThreadLocalUserSession.class));
  }

  @Test
  public void execute_bulk_change() {
    Map<String, Object> params = newHashMap();
    params.put("issues", newArrayList("ABCD", "EFGH"));
    params.put("actions", newArrayList("do_transition", "assign", "set_severity", "plan"));
    params.put("do_transition.transition", "confirm");
    params.put("assign.assignee", "arthur");
    params.put("set_severity.severity", "MINOR");
    params.put("plan.plan", "3.7");
    service.bulkChange(params, "My comment", true);
    verify(issueBulkChangeService).execute(any(IssueBulkChangeQuery.class), any(ThreadLocalUserSession.class));
  }

  @Test
  public void format_changelog() {
    FieldDiffs fieldDiffs = new FieldDiffs();
    service.formatChangelog(fieldDiffs);
    verify(changelogService).formatDiffs(eq(fieldDiffs));
  }

  @Test
  public void max_query_size() {
    assertThat(service.maxPageSize()).isEqualTo(500);
  }

  @Test
  public void create_context_from_parameters() {
    Map<String, Object> map = newHashMap();
    map.put("pageSize", 10l);
    map.put("pageIndex", 50);
    SearchOptions searchOptions = InternalRubyIssueService.toSearchOptions(map);
    assertThat(searchOptions.getLimit()).isEqualTo(10);
    assertThat(searchOptions.getPage()).isEqualTo(50);

    map = newHashMap();
    map.put("pageSize", -1);
    map.put("pageIndex", 50);
    searchOptions = InternalRubyIssueService.toSearchOptions(map);
    assertThat(searchOptions.getLimit()).isEqualTo(500);
    assertThat(searchOptions.getPage()).isEqualTo(1);

    searchOptions = InternalRubyIssueService.toSearchOptions(Maps.<String, Object>newHashMap());
    assertThat(searchOptions.getLimit()).isEqualTo(100);
    assertThat(searchOptions.getPage()).isEqualTo(1);
  }

  @Test
  public void list_tags() {
    List<String> tags = Arrays.asList("tag1", "tag2", "tag3");
    when(issueService.listTags(null, 0)).thenReturn(tags);
    assertThat(service.listTags()).isEqualTo(tags);
  }

  @Test
  public void list_tags_for_component() {
    Map<String, Long> tags = ImmutableMap.of("tag1", 1L, "tag2", 2L, "tag3", 3L);
    int pageSize = 42;
    IssueQuery query = IssueQuery.builder(userSessionRule).build();
    String componentUuid = "polop";
    Map<String, Object> params = ImmutableMap.<String, Object>of("componentUuids", componentUuid, "resolved", false);
    when(issueQueryService.createFromMap(params)).thenReturn(query);
    when(issueService.listTagsForComponent(query, pageSize)).thenReturn(tags);
    assertThat(service.listTagsForComponent(componentUuid, pageSize)).isEqualTo(tags);
  }

  @Test
  public void is_user_issue_admin() {
    userSessionRule.addProjectUuidPermissions(UserRole.ISSUE_ADMIN, "bcde");
    assertThat(service.isUserIssueAdmin("abcd")).isFalse();
    assertThat(service.isUserIssueAdmin("bcde")).isTrue();
  }

  private void checkBadRequestException(Exception e, String key, Object... params) {
    BadRequestException exception = (BadRequestException) e;
    Message msg = exception.errors().messages().get(0);
    assertThat(msg.getKey()).isEqualTo(key);
    assertThat(msg.getParams()).containsOnly(params);
  }

  private String createLongString(int size) {
    String result = "";
    for (int i = 0; i < size; i++) {
      result += "c";
    }
    return result;
  }

}
