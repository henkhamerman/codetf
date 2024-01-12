Refactoring Types: ['Move Class']
in/java/org/sonar/server/component/db/SnapshotDao.java
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

package org.sonar.server.component.db;

import java.util.List;
import javax.annotation.CheckForNull;
import javax.annotation.Nullable;
import org.sonar.api.resources.Scopes;
import org.sonar.core.component.SnapshotDto;
import org.sonar.core.component.SnapshotQuery;
import org.sonar.core.component.db.SnapshotMapper;
import org.sonar.core.persistence.DaoComponent;
import org.sonar.core.persistence.DbSession;
import org.sonar.server.exceptions.NotFoundException;

public class SnapshotDao implements DaoComponent {

  @CheckForNull
  public SnapshotDto selectNullableById(DbSession session, Long id) {
    return mapper(session).selectByKey(id);
  }

  public SnapshotDto selectById(DbSession session, Long key) {
    SnapshotDto value = selectNullableById(session, key);
    if (value == null) {
      throw new NotFoundException(String.format("Key '%s' not found", key));
    }
    return value;
  }

  @CheckForNull
  public SnapshotDto selectLastSnapshotByComponentId(DbSession session, long componentId) {
    return mapper(session).selectLastSnapshot(componentId);
  }

  public List<SnapshotDto> selectSnapshotsByComponentId(DbSession session, long componentId) {
    return mapper(session).selectSnapshotsByQuery(new SnapshotQuery().setComponentId(componentId));
  }

  public List<SnapshotDto> selectSnapshotsByQuery(DbSession session, SnapshotQuery query) {
    return mapper(session).selectSnapshotsByQuery(query);
  }

  public List<SnapshotDto> selectPreviousVersionSnapshots(DbSession session, long componentId, String lastVersion) {
    return mapper(session).selectPreviousVersionSnapshots(componentId, lastVersion);
  }

  public List<SnapshotDto> selectSnapshotAndChildrenOfProjectScope(DbSession session, long snapshotId) {
    return mapper(session).selectSnapshotAndChildrenOfScope(snapshotId, Scopes.PROJECT);
  }

  public int updateSnapshotAndChildrenLastFlagAndStatus(DbSession session, SnapshotDto snapshot, boolean isLast, String status) {
    Long rootId = snapshot.getId();
    String path = snapshot.getPath() + snapshot.getId() + ".%";
    Long pathRootId = snapshot.getRootIdOrSelf();

    return mapper(session).updateSnapshotAndChildrenLastFlagAndStatus(rootId, pathRootId, path, isLast, status);
  }

  public int updateSnapshotAndChildrenLastFlag(DbSession session, SnapshotDto snapshot, boolean isLast) {
    Long rootId = snapshot.getId();
    String path = snapshot.getPath() + snapshot.getId() + ".%";
    Long pathRootId = snapshot.getRootIdOrSelf();

    return mapper(session).updateSnapshotAndChildrenLastFlag(rootId, pathRootId, path, isLast);
  }

  public static boolean isLast(SnapshotDto snapshotTested, @Nullable SnapshotDto previousLastSnapshot) {
    return previousLastSnapshot == null || previousLastSnapshot.getCreatedAt() < snapshotTested.getCreatedAt();
  }

  public SnapshotDto insert(DbSession session, SnapshotDto item) {
    mapper(session).insert(item);
    return item;
  }

  private SnapshotMapper mapper(DbSession session) {
    return session.getMapper(SnapshotMapper.class);
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/computation/period/PeriodsHolder.java
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

package org.sonar.server.computation.period;

import java.util.List;
import org.sonar.api.CoreProperties;

/**
 * Repository of periods used to compute differential measures.
 * Here are the steps to retrieve these periods :
 * - Read the 5 period properties ${@link CoreProperties#TIMEMACHINE_PERIOD_PREFIX}
 * - Try to find the matching snapshots from the properties
 * - If a snapshot is found, a new period is added to the repository
 */
public interface PeriodsHolder {

  List<Period> getPeriods();

}


File: server/sonar-server/src/main/java/org/sonar/server/computation/period/PeriodsHolderImpl.java
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

package org.sonar.server.computation.period;

import com.google.common.base.Preconditions;
import java.util.ArrayList;
import java.util.List;

public class PeriodsHolderImpl implements PeriodsHolder {

  private boolean isPeriodsInitialized = false;
  private List<Period> periods = new ArrayList<>();

  public void setPeriods(List<Period> periods) {
    this.periods = periods;
    isPeriodsInitialized = true;
  }

  @Override
  public List<Period> getPeriods() {
    Preconditions.checkArgument(isPeriodsInitialized, "Periods have not been initialized yet");
    return periods;
  }

}


File: server/sonar-server/src/main/java/org/sonar/server/computation/step/FeedPeriodsStep.java
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

import com.google.common.base.Strings;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import javax.annotation.CheckForNull;
import javax.annotation.Nullable;
import org.apache.commons.lang.StringUtils;
import org.sonar.api.CoreProperties;
import org.sonar.api.config.Settings;
import org.sonar.api.resources.Qualifiers;
import org.sonar.api.utils.DateUtils;
import org.sonar.api.utils.log.Logger;
import org.sonar.api.utils.log.Loggers;
import org.sonar.core.component.ComponentDto;
import org.sonar.core.component.SnapshotDto;
import org.sonar.core.component.SnapshotQuery;
import org.sonar.core.persistence.DbSession;
import org.sonar.server.computation.batch.BatchReportReader;
import org.sonar.server.computation.component.Component;
import org.sonar.server.computation.component.TreeRootHolder;
import org.sonar.server.computation.period.Period;
import org.sonar.server.computation.period.PeriodsHolderImpl;
import org.sonar.server.db.DbClient;

import static org.sonar.core.component.SnapshotQuery.SORT_FIELD.BY_DATE;
import static org.sonar.core.component.SnapshotQuery.SORT_ORDER.ASC;
import static org.sonar.core.component.SnapshotQuery.SORT_ORDER.DESC;

/**
 * Populates the {@link org.sonar.server.computation.period.PeriodsHolder}
 *
 * Here is how these periods are computed :
 * - Read the 5 period properties ${@link CoreProperties#TIMEMACHINE_PERIOD_PREFIX}
 * - Try to find the matching snapshots from the properties
 * - If a snapshot is found, a new period is added to the repository
 */
public class FeedPeriodsStep implements ComputationStep {

  private static final Logger LOG = Loggers.get(FeedPeriodsStep.class);

  private static final int NUMBER_OF_PERIODS = 5;

  private final DbClient dbClient;
  private final Settings settings;
  private final TreeRootHolder treeRootHolder;
  private final BatchReportReader batchReportReader;
  private final PeriodsHolderImpl periodsHolder;

  public FeedPeriodsStep(DbClient dbClient, Settings settings, TreeRootHolder treeRootHolder, BatchReportReader batchReportReader,
    PeriodsHolderImpl periodsHolder) {
    this.dbClient = dbClient;
    this.settings = settings;
    this.treeRootHolder = treeRootHolder;
    this.batchReportReader = batchReportReader;
    this.periodsHolder = periodsHolder;
  }

  @Override
  public void execute() {
    DbSession session = dbClient.openSession(false);
    try {
      periodsHolder.setPeriods(buildPeriods(session));
    } finally {
      session.close();
    }
  }

  private List<Period> buildPeriods(DbSession session) {
    Component project = treeRootHolder.getRoot();
    ComponentDto projectDto = dbClient.componentDao().selectNullableByKey(session, project.getKey());
    // No project on first analysis, no period
    if (projectDto != null) {
      List<Period> periods = new ArrayList<>(5);
      PeriodResolver periodResolver = new PeriodResolver(session, projectDto.getId(), batchReportReader.readMetadata().getAnalysisDate(), project.getVersion(),
        // TODO qualifier will be different for Views
        Qualifiers.PROJECT);

      for (int index = 1; index <= NUMBER_OF_PERIODS; index++) {
        Period period = periodResolver.resolve(index);
        // SONAR-4700 Add a past snapshot only if it exists
        if (period != null) {
          periods.add(period);
        }
      }
      return periods;
    }
    return Collections.emptyList();
  }

  private class PeriodResolver {

    private final DbSession session;
    private final long projectId;
    private final long analysisDate;
    private final String currentVersion;
    private final String qualifier;

    public PeriodResolver(DbSession session, long projectId, long analysisDate, String currentVersion, String qualifier) {
      this.session = session;
      this.projectId = projectId;
      this.analysisDate = analysisDate;
      this.currentVersion = currentVersion;
      this.qualifier = qualifier;
    }

    @CheckForNull
    public Period resolve(int index) {
      String propertyValue = getPropertyValue(qualifier, settings, index);
      if (StringUtils.isBlank(propertyValue)) {
        return null;
      }
      Period period = resolve(index, propertyValue);
      if (period == null && StringUtils.isNotBlank(propertyValue)) {
        LOG.debug("Property " + CoreProperties.TIMEMACHINE_PERIOD_PREFIX + index + " is not valid: " + propertyValue);
      }
      return period;
    }

    @CheckForNull
    private Period resolve(int index, String property) {
      Integer days = tryToResolveByDays(property);
      if (days != null) {
        return findByDays(index, days);
      }
      Date date = tryToResolveByDate(property);
      if (date != null) {
        return findByDate(index, date);
      }
      if (StringUtils.equals(CoreProperties.TIMEMACHINE_MODE_PREVIOUS_ANALYSIS, property)) {
        return findByPreviousAnalysis(index);
      }
      if (StringUtils.equals(CoreProperties.TIMEMACHINE_MODE_PREVIOUS_VERSION, property)) {
        return findByPreviousVersion(index);
      }
      return findByVersion(index, property);
    }

    private Period findByDate(int index, Date date) {
      SnapshotDto snapshot = findFirstSnapshot(session, createCommonQuery(projectId).setCreatedAfter(date.getTime()).setSort(BY_DATE, ASC));
      if (snapshot == null) {
        return null;
      }
      LOG.debug(String.format("Compare to date %s (analysis of %s)", formatDate(date.getTime()), formatDate(snapshot.getCreatedAt())));
      return new Period(index, CoreProperties.TIMEMACHINE_MODE_DATE, DateUtils.formatDate(date), snapshot.getCreatedAt());
    }

    @CheckForNull
    private Period findByDays(int index, int days) {
      List<SnapshotDto> snapshots = dbClient.snapshotDao().selectSnapshotsByQuery(session, createCommonQuery(projectId).setCreatedBefore(analysisDate).setSort(BY_DATE, ASC));
      long targetDate = DateUtils.addDays(new Date(analysisDate), -days).getTime();
      SnapshotDto snapshot = findNearestSnapshotToTargetDate(snapshots, targetDate);
      if (snapshot == null) {
        return null;
      }
      LOG.debug(String.format("Compare over %s days (%s, analysis of %s)", String.valueOf(days), formatDate(targetDate), formatDate(snapshot.getCreatedAt())));
      return new Period(index, CoreProperties.TIMEMACHINE_MODE_DAYS, String.valueOf(days), snapshot.getCreatedAt());
    }

    @CheckForNull
    private Period findByPreviousAnalysis(int index) {
      SnapshotDto snapshot = findFirstSnapshot(session, createCommonQuery(projectId).setCreatedBefore(analysisDate).setIsLast(true).setSort(BY_DATE, DESC));
      if (snapshot == null) {
        return null;
      }
      LOG.debug(String.format("Compare to previous analysis (%s)", formatDate(snapshot.getCreatedAt())));
      return new Period(index, CoreProperties.TIMEMACHINE_MODE_PREVIOUS_ANALYSIS, formatDate(snapshot.getCreatedAt()), snapshot.getCreatedAt());
    }

    @CheckForNull
    private Period findByPreviousVersion(int index) {
      List<SnapshotDto> snapshotDtos = dbClient.snapshotDao().selectPreviousVersionSnapshots(session, projectId, currentVersion);
      if (snapshotDtos.isEmpty()) {
        return null;
      }
      SnapshotDto snapshotDto = snapshotDtos.get(0);
      LOG.debug(String.format("Compare to previous version (%s)", formatDate(snapshotDto.getCreatedAt())));
      return new Period(index, CoreProperties.TIMEMACHINE_MODE_PREVIOUS_VERSION, snapshotDto.getVersion(), snapshotDto.getCreatedAt());
    }

    @CheckForNull
    private Period findByVersion(int index, String version) {
      SnapshotDto snapshot = findFirstSnapshot(session, createCommonQuery(projectId).setVersion(version).setSort(BY_DATE, DESC));
      if (snapshot == null) {
        return null;
      }
      LOG.debug(String.format("Compare to version (%s) (%s)", version, formatDate(snapshot.getCreatedAt())));
      return new Period(index, CoreProperties.TIMEMACHINE_MODE_VERSION, version, snapshot.getCreatedAt());
    }

    @CheckForNull
    private SnapshotDto findFirstSnapshot(DbSession session, SnapshotQuery query) {
      List<SnapshotDto> snapshots = dbClient.snapshotDao().selectSnapshotsByQuery(session, query);
      if (!snapshots.isEmpty()) {
        return snapshots.get(0);
      }
      return null;
    }
  }

  @CheckForNull
  private static Integer tryToResolveByDays(String property) {
    try {
      return Integer.parseInt(property);
    } catch (NumberFormatException e) {
      // Nothing to, it means that the property is not a number of days
      return null;
    }
  }

  @CheckForNull
  private static Date tryToResolveByDate(String property) {
    try {
      return DateUtils.parseDate(property);
    } catch (Exception e) {
      // Nothing to, it means that the property is not a date
      return null;
    }
  }

  @CheckForNull
  private static SnapshotDto findNearestSnapshotToTargetDate(List<SnapshotDto> snapshots, Long targetDate) {
    long bestDistance = Long.MAX_VALUE;
    SnapshotDto nearest = null;
    for (SnapshotDto snapshot : snapshots) {
      long distance = Math.abs(snapshot.getCreatedAt() - targetDate);
      if (distance <= bestDistance) {
        bestDistance = distance;
        nearest = snapshot;
      }
    }
    return nearest;
  }

  private static SnapshotQuery createCommonQuery(Long projectId) {
    return new SnapshotQuery().setComponentId(projectId).setStatus(SnapshotDto.STATUS_PROCESSED);
  }

  private static String formatDate(long date) {
    return DateUtils.formatDate(org.apache.commons.lang.time.DateUtils.truncate(new Date(date), Calendar.SECOND));
  }

  private static String getPropertyValue(@Nullable String qualifier, Settings settings, int index) {
    String value = settings.getString(CoreProperties.TIMEMACHINE_PERIOD_PREFIX + index);
    // For periods 4 and 5 we're also searching for a property prefixed by the qualifier
    if (index > 3 && Strings.isNullOrEmpty(value)) {
      value = settings.getString(CoreProperties.TIMEMACHINE_PERIOD_PREFIX + index + "." + qualifier);
    }
    return value;
  }

  @Override
  public String getDescription() {
    return "Feed differential periods";
  }
}


File: server/sonar-server/src/main/java/org/sonar/server/computation/step/PersistComponentsStep.java
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

import com.google.common.collect.Maps;
import java.util.Date;
import java.util.List;
import java.util.Map;
import javax.annotation.Nullable;
import org.apache.commons.io.FilenameUtils;
import org.apache.commons.lang.ObjectUtils;
import org.apache.commons.lang.StringUtils;
import org.sonar.api.resources.Qualifiers;
import org.sonar.api.resources.Scopes;
import org.sonar.api.utils.System2;
import org.sonar.batch.protocol.output.BatchReport;
import org.sonar.core.component.ComponentDto;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.util.NonNullInputFunction;
import org.sonar.server.computation.batch.BatchReportReader;
import org.sonar.server.computation.component.Component;
import org.sonar.server.computation.component.DbIdsRepository;
import org.sonar.server.computation.component.TreeRootHolder;
import org.sonar.server.db.DbClient;

/**
 * Persist components
 * Also feed the components cache {@link DbIdsRepository} with component ids
 */
public class PersistComponentsStep implements ComputationStep {

  private final DbClient dbClient;
  private final TreeRootHolder treeRootHolder;
  private final BatchReportReader reportReader;
  private final DbIdsRepository dbIdsRepository;
  private final System2 system2;

  public PersistComponentsStep(DbClient dbClient, TreeRootHolder treeRootHolder, BatchReportReader reportReader, DbIdsRepository dbIdsRepository, System2 system2) {
    this.dbClient = dbClient;
    this.treeRootHolder = treeRootHolder;
    this.reportReader = reportReader;
    this.dbIdsRepository = dbIdsRepository;
    this.system2 = system2;
  }

  @Override
  public void execute() {
    DbSession session = dbClient.openSession(false);
    try {
      org.sonar.server.computation.component.Component root = treeRootHolder.getRoot();
      List<ComponentDto> existingComponents = dbClient.componentDao().selectComponentsFromProjectKey(session, root.getKey());
      Map<String, ComponentDto> existingComponentDtosByKey = componentDtosByKey(existingComponents);
      PersisComponent persisComponent = new PersisComponent(session, existingComponentDtosByKey, reportReader);

      persisComponent.recursivelyProcessComponent(root, null);
      session.commit();
    } finally {
      session.close();
    }
  }

  private class PersisComponent {

    private final BatchReportReader reportReader;
    private final Map<String, ComponentDto> existingComponentDtosByKey;
    private final DbSession dbSession;

    private ComponentDto project;

    public PersisComponent(DbSession dbSession, Map<String, ComponentDto> existingComponentDtosByKey, BatchReportReader reportReader) {
      this.reportReader = reportReader;
      this.existingComponentDtosByKey = existingComponentDtosByKey;
      this.dbSession = dbSession;
    }

    private void recursivelyProcessComponent(Component component, @Nullable ComponentDto lastModule) {
      BatchReport.Component reportComponent = reportReader.readComponent(component.getRef());

      switch (component.getType()) {
        case PROJECT:
          this.project = processProject(component, reportComponent);
          processChildren(component, project);
          break;
        case MODULE:
          ComponentDto persistedModule = processModule(component, reportComponent, nonNullLastModule(lastModule));
          processChildren(component, persistedModule);
          break;
        case DIRECTORY:
          processDirectory(component, reportComponent, nonNullLastModule(lastModule));
          processChildren(component, nonNullLastModule(lastModule));
          break;
        case FILE:
          processFile(component, reportComponent, nonNullLastModule(lastModule));
          break;
        default:
          throw new IllegalStateException(String.format("Unsupported component type '%s'", component.getType()));
      }
    }

    private void processChildren(Component component, ComponentDto lastModule) {
      for (Component child : component.getChildren()) {
        recursivelyProcessComponent(child, lastModule);
      }
    }

    private ComponentDto nonNullLastModule(@Nullable ComponentDto lastModule) {
      return lastModule == null ? project : lastModule;
    }

    public ComponentDto processProject(Component project, BatchReport.Component reportComponent) {
      ComponentDto componentDto = createComponentDto(reportComponent, project);

      componentDto.setScope(Scopes.PROJECT);
      componentDto.setQualifier(Qualifiers.PROJECT);
      componentDto.setName(reportComponent.getName());
      componentDto.setLongName(componentDto.name());
      if (reportComponent.hasDescription()) {
        componentDto.setDescription(reportComponent.getDescription());
      }
      componentDto.setProjectUuid(componentDto.uuid());
      componentDto.setModuleUuidPath(ComponentDto.MODULE_UUID_PATH_SEP + componentDto.uuid() + ComponentDto.MODULE_UUID_PATH_SEP);

      ComponentDto projectDto = persistComponent(project.getRef(), componentDto);
      addToCache(project, projectDto);
      return projectDto;
    }

    public ComponentDto processModule(Component module, BatchReport.Component reportComponent, ComponentDto lastModule) {
      ComponentDto componentDto = createComponentDto(reportComponent, module);

      componentDto.setScope(Scopes.PROJECT);
      componentDto.setQualifier(Qualifiers.MODULE);
      componentDto.setName(reportComponent.getName());
      componentDto.setLongName(componentDto.name());
      if (reportComponent.hasPath()) {
        componentDto.setPath(reportComponent.getPath());
      }
      if (reportComponent.hasDescription()) {
        componentDto.setDescription(reportComponent.getDescription());
      }
      componentDto.setParentProjectId(project.getId());
      componentDto.setProjectUuid(lastModule.projectUuid());
      componentDto.setModuleUuid(lastModule.uuid());
      componentDto.setModuleUuidPath(lastModule.moduleUuidPath() + componentDto.uuid() + ComponentDto.MODULE_UUID_PATH_SEP);

      ComponentDto moduleDto = persistComponent(module.getRef(), componentDto);
      addToCache(module, moduleDto);
      return moduleDto;
    }

    public ComponentDto processDirectory(org.sonar.server.computation.component.Component directory, BatchReport.Component reportComponent, ComponentDto lastModule) {
      ComponentDto componentDto = createComponentDto(reportComponent, directory);

      componentDto.setScope(Scopes.DIRECTORY);
      componentDto.setQualifier(Qualifiers.DIRECTORY);
      componentDto.setName(reportComponent.getPath());
      componentDto.setLongName(reportComponent.getPath());
      if (reportComponent.hasPath()) {
        componentDto.setPath(reportComponent.getPath());
      }

      componentDto.setParentProjectId(lastModule.getId());
      componentDto.setProjectUuid(lastModule.projectUuid());
      componentDto.setModuleUuid(lastModule.uuid());
      componentDto.setModuleUuidPath(lastModule.moduleUuidPath());

      ComponentDto directoryDto = persistComponent(directory.getRef(), componentDto);
      addToCache(directory, directoryDto);
      return directoryDto;
    }

    public void processFile(org.sonar.server.computation.component.Component file, BatchReport.Component reportComponent, ComponentDto lastModule) {
      ComponentDto componentDto = createComponentDto(reportComponent, file);

      componentDto.setScope(Scopes.FILE);
      componentDto.setQualifier(getFileQualifier(file));
      componentDto.setName(FilenameUtils.getName(reportComponent.getPath()));
      componentDto.setLongName(reportComponent.getPath());
      if (reportComponent.hasPath()) {
        componentDto.setPath(reportComponent.getPath());
      }
      if (reportComponent.hasLanguage()) {
        componentDto.setLanguage(reportComponent.getLanguage());
      }

      componentDto.setParentProjectId(lastModule.getId());
      componentDto.setProjectUuid(lastModule.projectUuid());
      componentDto.setModuleUuid(lastModule.uuid());
      componentDto.setModuleUuidPath(lastModule.moduleUuidPath());

      ComponentDto fileDto = persistComponent(file.getRef(), componentDto);
      addToCache(file, fileDto);
    }

    private ComponentDto createComponentDto(BatchReport.Component reportComponent, Component component) {
      String componentKey = component.getKey();
      String componentUuid = component.getUuid();

      ComponentDto componentDto = new ComponentDto();
      componentDto.setUuid(componentUuid);
      componentDto.setKey(componentKey);
      componentDto.setDeprecatedKey(componentKey);
      componentDto.setEnabled(true);
      componentDto.setCreatedAt(new Date(system2.now()));
      return componentDto;
    }

    private ComponentDto persistComponent(int componentRef, ComponentDto componentDto) {
      ComponentDto existingComponent = existingComponentDtosByKey.get(componentDto.getKey());
      if (existingComponent == null) {
        dbClient.componentDao().insert(dbSession, componentDto);
        return componentDto;
      } else {
        if (updateComponent(existingComponent, componentDto)) {
          dbClient.componentDao().update(dbSession, existingComponent);
        }
        return existingComponent;
      }
    }

    private void addToCache(Component component, ComponentDto componentDto) {
      dbIdsRepository.setComponentId(component, componentDto.getId());
    }

  }

  private static boolean updateComponent(ComponentDto existingComponent, ComponentDto newComponent) {
    boolean isUpdated = false;
    if (!StringUtils.equals(existingComponent.name(), newComponent.name())) {
      existingComponent.setName(newComponent.name());
      isUpdated = true;
    }
    if (!StringUtils.equals(existingComponent.description(), newComponent.description())) {
      existingComponent.setDescription(newComponent.description());
      isUpdated = true;
    }
    if (!StringUtils.equals(existingComponent.path(), newComponent.path())) {
      existingComponent.setPath(newComponent.path());
      isUpdated = true;
    }
    if (!StringUtils.equals(existingComponent.moduleUuid(), newComponent.moduleUuid())) {
      existingComponent.setModuleUuid(newComponent.moduleUuid());
      isUpdated = true;
    }
    if (!existingComponent.moduleUuidPath().equals(newComponent.moduleUuidPath())) {
      existingComponent.setModuleUuidPath(newComponent.moduleUuidPath());
      isUpdated = true;
    }
    if (!ObjectUtils.equals(existingComponent.parentProjectId(), newComponent.parentProjectId())) {
      existingComponent.setParentProjectId(newComponent.parentProjectId());
      isUpdated = true;
    }
    return isUpdated;
  }

  private static String getFileQualifier(Component component) {
    return component.isUnitTest() ? Qualifiers.UNIT_TEST_FILE : Qualifiers.FILE;
  }

  private static Map<String, ComponentDto> componentDtosByKey(List<ComponentDto> components) {
    return Maps.uniqueIndex(components, new NonNullInputFunction<ComponentDto, String>() {
      @Override
      public String doApply(ComponentDto input) {
        return input.key();
      }
    });
  }

  @Override
  public String getDescription() {
    return "Persist components";
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/component/db/SnapshotDaoTest.java
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

package org.sonar.server.component.db;

import java.util.Date;
import java.util.List;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.sonar.api.utils.DateUtils;
import org.sonar.core.component.SnapshotDto;
import org.sonar.core.component.SnapshotQuery;
import org.sonar.core.persistence.AbstractDaoTestCase;
import org.sonar.core.persistence.DbSession;

import static org.assertj.core.api.Assertions.assertThat;
import static org.sonar.core.component.SnapshotQuery.SORT_FIELD.BY_DATE;
import static org.sonar.core.component.SnapshotQuery.SORT_ORDER.ASC;
import static org.sonar.core.component.SnapshotQuery.SORT_ORDER.DESC;

public class SnapshotDaoTest extends AbstractDaoTestCase {

  DbSession session;

  SnapshotDao sut;

  @Before
  public void createDao() {
    session = getMyBatis().openSession(false);
    sut = new SnapshotDao();
  }

  @After
  public void tearDown() {
    session.close();
  }

  @Test
  public void get_by_key() {
    setupData("shared");

    SnapshotDto result = sut.selectNullableById(session, 3L);
    assertThat(result).isNotNull();
    assertThat(result.getId()).isEqualTo(3L);
    assertThat(result.getComponentId()).isEqualTo(3L);
    assertThat(result.getRootProjectId()).isEqualTo(1L);
    assertThat(result.getParentId()).isEqualTo(2L);
    assertThat(result.getRootId()).isEqualTo(1L);
    assertThat(result.getStatus()).isEqualTo("P");
    assertThat(result.getLast()).isTrue();
    assertThat(result.getPurgeStatus()).isEqualTo(1);
    assertThat(result.getDepth()).isEqualTo(1);
    assertThat(result.getScope()).isEqualTo("DIR");
    assertThat(result.getQualifier()).isEqualTo("PAC");
    assertThat(result.getVersion()).isEqualTo("2.1-SNAPSHOT");
    assertThat(result.getPath()).isEqualTo("1.2.");

    assertThat(result.getPeriodMode(1)).isEqualTo("days1");
    assertThat(result.getPeriodModeParameter(1)).isEqualTo("30");
    assertThat(result.getPeriodDate(1)).isEqualTo(1316815200000L);
    assertThat(result.getPeriodMode(2)).isEqualTo("days2");
    assertThat(result.getPeriodModeParameter(2)).isEqualTo("31");
    assertThat(result.getPeriodDate(2)).isEqualTo(1316901600000L);
    assertThat(result.getPeriodMode(3)).isEqualTo("days3");
    assertThat(result.getPeriodModeParameter(3)).isEqualTo("32");
    assertThat(result.getPeriodDate(3)).isEqualTo(1316988000000L);
    assertThat(result.getPeriodMode(4)).isEqualTo("days4");
    assertThat(result.getPeriodModeParameter(4)).isEqualTo("33");
    assertThat(result.getPeriodDate(4)).isEqualTo(1317074400000L);
    assertThat(result.getPeriodMode(5)).isEqualTo("days5");
    assertThat(result.getPeriodModeParameter(5)).isEqualTo("34");
    assertThat(result.getPeriodDate(5)).isEqualTo(1317160800000L);

    assertThat(result.getCreatedAt()).isEqualTo(1228172400000L);
    assertThat(result.getBuildDate()).isEqualTo(1317247200000L);

    assertThat(sut.selectNullableById(session, 999L)).isNull();
  }

  @Test
  public void lastSnapshot_returns_null_when_no_last_snapshot() {
    setupData("empty");

    SnapshotDto snapshot = sut.selectLastSnapshotByComponentId(session, 123L);

    assertThat(snapshot).isNull();
  }

  @Test
  public void lastSnapshot_from_one_resource() {
    setupData("snapshots");

    SnapshotDto snapshot = sut.selectLastSnapshotByComponentId(session, 2L);

    assertThat(snapshot).isNotNull();
    assertThat(snapshot.getId()).isEqualTo(4L);
  }

  @Test
  public void lastSnapshot_from_one_resource_without_last_is_null() {
    setupData("snapshots");

    SnapshotDto snapshot = sut.selectLastSnapshotByComponentId(session, 5L);

    assertThat(snapshot).isNull();
  }

  @Test
  public void snapshot_and_child_retrieved() {
    setupData("snapshots");

    List<SnapshotDto> snapshots = sut.selectSnapshotAndChildrenOfProjectScope(session, 1L);

    assertThat(snapshots).isNotEmpty();
    assertThat(snapshots).extracting("id").containsOnly(1L, 6L);
  }

  @Test
  public void select_snapshots_by_component_id() {
    setupData("snapshots");

    List<SnapshotDto> snapshots = sut.selectSnapshotsByComponentId(session, 1L);

    assertThat(snapshots).hasSize(3);
  }

  @Test
  public void select_snapshots_by_query() {
    setupData("select_snapshots_by_query");

    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery())).hasSize(6);

    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(1L))).hasSize(3);

    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(1L).setVersion("2.2-SNAPSHOT"))).extracting("id").containsOnly(3L);

    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(1L).setIsLast(true))).extracting("id").containsOnly(1L);
    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(1L).setIsLast(false))).extracting("id").containsOnly(2L, 3L);

    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(1L).setCreatedAfter(1228172400002L))).extracting("id").containsOnly(2L, 3L);
    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(1L).setCreatedBefore(1228172400002L))).extracting("id").containsOnly(1L);

    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(2L).setStatus("P"))).hasSize(1);
    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(2L).setStatus("U"))).hasSize(1);

    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(1L).setSort(BY_DATE, ASC)).get(0).getId()).isEqualTo(1L);
    assertThat(sut.selectSnapshotsByQuery(session, new SnapshotQuery().setComponentId(1L).setSort(BY_DATE, DESC)).get(0).getId()).isEqualTo(3L);
  }

  @Test
  public void select_previous_version_snapshots() throws Exception {
    setupData("select_previous_version_snapshots");

    List<SnapshotDto> snapshots = sut.selectPreviousVersionSnapshots(session, 1L, "1.2-SNAPSHOT");
    assertThat(snapshots).hasSize(2);

    SnapshotDto firstSnapshot = snapshots.get(0);
    assertThat(firstSnapshot.getVersion()).isEqualTo("1.1");

    // All snapshots are returned on an unknown version
    assertThat(sut.selectPreviousVersionSnapshots(session, 1L, "UNKNOWN")).hasSize(3);
  }

  @Test
  public void insert() {
    setupData("empty");

    SnapshotDto dto = defaultSnapshot().setCreatedAt(1403042400000L);

    sut.insert(session, dto);
    session.commit();

    assertThat(dto.getId()).isNotNull();
    checkTables("insert", "snapshots");
  }

  @Test
  public void set_snapshot_and_children_to_false_and_status_processed() {
    setupData("snapshots");
    SnapshotDto snapshot = defaultSnapshot().setId(1L);

    sut.updateSnapshotAndChildrenLastFlagAndStatus(session, snapshot, false, SnapshotDto.STATUS_PROCESSED);
    session.commit();

    List<SnapshotDto> snapshots = sut.selectSnapshotAndChildrenOfProjectScope(session, 1L);
    assertThat(snapshots).hasSize(2);
    assertThat(snapshots).extracting("id").containsOnly(1L, 6L);
    assertThat(snapshots).extracting("last").containsOnly(false);
    assertThat(snapshots).extracting("status").containsOnly(SnapshotDto.STATUS_PROCESSED);
  }

  @Test
  public void set_snapshot_and_children_isLast_flag_to_false() {
    setupData("snapshots");
    SnapshotDto snapshot = defaultSnapshot().setId(1L);

    sut.updateSnapshotAndChildrenLastFlag(session, snapshot, false);
    session.commit();

    List<SnapshotDto> snapshots = sut.selectSnapshotAndChildrenOfProjectScope(session, 1L);
    assertThat(snapshots).hasSize(2);
    assertThat(snapshots).extracting("id").containsOnly(1L, 6L);
    assertThat(snapshots).extracting("last").containsOnly(false);
  }

  @Test
  public void is_last_snapshot_when_no_previous_snapshot() {
    SnapshotDto snapshot = defaultSnapshot();

    boolean isLast = sut.isLast(snapshot, null);

    assertThat(isLast).isTrue();
  }

  @Test
  public void is_last_snapshot_when_previous_snapshot_is_older() {
    Date today = new Date();
    Date yesterday = DateUtils.addDays(today, -1);

    SnapshotDto snapshot = defaultSnapshot().setCreatedAt(today.getTime());
    SnapshotDto previousLastSnapshot = defaultSnapshot().setCreatedAt(yesterday.getTime());

    boolean isLast = sut.isLast(snapshot, previousLastSnapshot);

    assertThat(isLast).isTrue();
  }

  @Test
  public void is_not_last_snapshot_when_previous_snapshot_is_newer() {
    Date today = new Date();
    Date yesterday = DateUtils.addDays(today, -1);

    SnapshotDto snapshot = defaultSnapshot().setCreatedAt(yesterday.getTime());
    SnapshotDto previousLastSnapshot = defaultSnapshot().setCreatedAt(today.getTime());

    boolean isLast = sut.isLast(snapshot, previousLastSnapshot);

    assertThat(isLast).isFalse();
  }

  private static SnapshotDto defaultSnapshot() {
    return new SnapshotDto()
      .setComponentId(3L)
      .setRootProjectId(1L)
      .setParentId(2L)
      .setRootId(1L)
      .setStatus("P")
      .setLast(true)
      .setPurgeStatus(1)
      .setDepth(1)
      .setScope("DIR")
      .setQualifier("PAC")
      .setVersion("2.1-SNAPSHOT")
      .setPath("1.2.")
      .setPeriodMode(1, "days1")
      .setPeriodMode(2, "days2")
      .setPeriodMode(3, "days3")
      .setPeriodMode(4, "days4")
      .setPeriodMode(5, "days5")
      .setPeriodParam(1, "30")
      .setPeriodParam(2, "31")
      .setPeriodParam(3, "32")
      .setPeriodParam(4, "33")
      .setPeriodParam(5, "34")
      .setPeriodDate(1, 1_500_000_000_001L)
      .setPeriodDate(2, 1_500_000_000_002L)
      .setPeriodDate(3, 1_500_000_000_003L)
      .setPeriodDate(4, 1_500_000_000_004L)
      .setPeriodDate(5, 1_500_000_000_005L)
      .setBuildDate(1_500_000_000_006L);
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/computation/period/PeriodsHolderImplTest.java
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

package org.sonar.server.computation.period;

import java.util.ArrayList;
import java.util.List;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import static org.assertj.core.api.Assertions.assertThat;

public class PeriodsHolderImplTest {

  @Rule
  public ExpectedException thrown = ExpectedException.none();

  @Test
  public void get_periods() throws Exception {
    List<Period> periods = new ArrayList<>();
    periods.add(new Period(1, "mode", null, 1000L));

    PeriodsHolderImpl periodsHolder = new PeriodsHolderImpl();
    periodsHolder.setPeriods(periods);

    assertThat(periodsHolder.getPeriods()).hasSize(1);
  }

  @Test
  public void fail_to_get_periods_if_not_initialized() throws Exception {
    thrown.expect(IllegalArgumentException.class);
    thrown.expectMessage("Periods have not been initialized yet");

    new PeriodsHolderImpl().getPeriods();
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/computation/period/PeriodsHolderRule.java
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

package org.sonar.server.computation.period;

import java.util.ArrayList;
import java.util.List;
import org.junit.rules.TestRule;
import org.junit.runner.Description;
import org.junit.runners.model.Statement;

public class PeriodsHolderRule implements TestRule, PeriodsHolder {
  private List<Period> periods = new ArrayList<>();

  @Override
  public Statement apply(final Statement statement, Description description) {
    return new Statement() {
      @Override
      public void evaluate() throws Throwable {
        try {
          statement.evaluate();
        } finally {
          clear();
        }
      }
    };
  }

  private void clear() {
    this.periods = new ArrayList<>();
  }

  @Override
  public List<Period> getPeriods() {
    return periods;
  }

  public void addPeriod(Period period) {
    this.periods.add(period);
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/computation/step/PersistComponentsStepTest.java
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

import java.text.SimpleDateFormat;
import java.util.Date;
import org.junit.After;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.experimental.categories.Category;
import org.sonar.api.utils.DateUtils;
import org.sonar.api.utils.System2;
import org.sonar.batch.protocol.Constants;
import org.sonar.batch.protocol.output.BatchReport;
import org.sonar.core.component.ComponentDto;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.persistence.DbTester;
import org.sonar.server.component.ComponentTesting;
import org.sonar.server.component.db.ComponentDao;
import org.sonar.server.component.db.SnapshotDao;
import org.sonar.server.computation.batch.BatchReportReaderRule;
import org.sonar.server.computation.batch.TreeRootHolderRule;
import org.sonar.server.computation.component.Component;
import org.sonar.server.computation.component.DbIdsRepository;
import org.sonar.server.computation.component.DumbComponent;
import org.sonar.server.db.DbClient;
import org.sonar.test.DbTests;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

@Category(DbTests.class)
public class PersistComponentsStepTest extends BaseStepTest {

  private static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");

  private static final String PROJECT_KEY = "PROJECT_KEY";

  @ClassRule
  public static DbTester dbTester = new DbTester();

  @Rule
  public TreeRootHolderRule treeRootHolder = new TreeRootHolderRule();

  @Rule
  public BatchReportReaderRule reportReader = new BatchReportReaderRule();

  DbIdsRepository dbIdsRepository;

  System2 system2 = mock(System2.class);

  DbSession session;

  DbClient dbClient;

  Date now;

  PersistComponentsStep sut;

  @Before
  public void setup() throws Exception {
    dbTester.truncateTables();
    session = dbTester.myBatis().openSession(false);
    dbClient = new DbClient(dbTester.database(), dbTester.myBatis(), new ComponentDao(), new SnapshotDao());

    dbIdsRepository = new DbIdsRepository();

    now = DATE_FORMAT.parse("2015-06-02");
    when(system2.now()).thenReturn(now.getTime());

    sut = new PersistComponentsStep( dbClient, treeRootHolder, reportReader, dbIdsRepository, system2);
  }

  @Override
  protected ComputationStep step() {
    return sut;
  }

  @After
  public void tearDown() {
    session.close();
  }

  @Test
  public void persist_components() throws Exception {
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .setDescription("Project description")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_KEY")
      .setPath("module")
      .setName("Module")
      .setDescription("Module description")
      .addChildRef(3)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(3)
      .setType(Constants.ComponentType.DIRECTORY)
      .setPath("src/main/java/dir")
      .addChildRef(4)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(4)
      .setType(Constants.ComponentType.FILE)
      .setPath("src/main/java/dir/Foo.java")
      .setLanguage("java")
      .build());

    Component file = DumbComponent.builder(Component.Type.FILE, 4).setUuid("DEFG").setKey("MODULE_KEY:src/main/java/dir/Foo.java").build();
    Component directory = DumbComponent.builder(Component.Type.DIRECTORY, 3).setUuid("CDEF").setKey("MODULE_KEY:src/main/java/dir").addChildren(file).build();
    Component module = DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").addChildren(directory).build();
    Component project = DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(module).build();
    treeRootHolder.setRoot(project);

    sut.execute();
    session.commit();

    assertThat(dbTester.countRowsOfTable("projects")).isEqualTo(4);

    ComponentDto projectDto = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY);
    assertThat(projectDto).isNotNull();
    assertThat(projectDto.name()).isEqualTo("Project");
    assertThat(projectDto.description()).isEqualTo("Project description");
    assertThat(projectDto.path()).isNull();
    assertThat(projectDto.uuid()).isEqualTo("ABCD");
    assertThat(projectDto.moduleUuid()).isNull();
    assertThat(projectDto.moduleUuidPath()).isEqualTo("." + projectDto.uuid() + ".");
    assertThat(projectDto.projectUuid()).isEqualTo(projectDto.uuid());
    assertThat(projectDto.qualifier()).isEqualTo("TRK");
    assertThat(projectDto.scope()).isEqualTo("PRJ");
    assertThat(projectDto.parentProjectId()).isNull();
    assertThat(projectDto.getCreatedAt()).isEqualTo(now);

    ComponentDto moduleDto = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY");
    assertThat(moduleDto).isNotNull();
    assertThat(moduleDto.name()).isEqualTo("Module");
    assertThat(moduleDto.description()).isEqualTo("Module description");
    assertThat(moduleDto.path()).isEqualTo("module");
    assertThat(moduleDto.uuid()).isEqualTo("BCDE");
    assertThat(moduleDto.moduleUuid()).isEqualTo(projectDto.uuid());
    assertThat(moduleDto.moduleUuidPath()).isEqualTo(projectDto.moduleUuidPath() + moduleDto.uuid() + ".");
    assertThat(moduleDto.projectUuid()).isEqualTo(projectDto.uuid());
    assertThat(moduleDto.qualifier()).isEqualTo("BRC");
    assertThat(moduleDto.scope()).isEqualTo("PRJ");
    assertThat(moduleDto.parentProjectId()).isEqualTo(projectDto.getId());
    assertThat(moduleDto.getCreatedAt()).isEqualTo(now);

    ComponentDto directoryDto = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY:src/main/java/dir");
    assertThat(directoryDto).isNotNull();
    assertThat(directoryDto.name()).isEqualTo("src/main/java/dir");
    assertThat(directoryDto.description()).isNull();
    assertThat(directoryDto.path()).isEqualTo("src/main/java/dir");
    assertThat(directoryDto.uuid()).isEqualTo("CDEF");
    assertThat(directoryDto.moduleUuid()).isEqualTo(moduleDto.uuid());
    assertThat(directoryDto.moduleUuidPath()).isEqualTo(moduleDto.moduleUuidPath());
    assertThat(directoryDto.projectUuid()).isEqualTo(projectDto.uuid());
    assertThat(directoryDto.qualifier()).isEqualTo("DIR");
    assertThat(directoryDto.scope()).isEqualTo("DIR");
    assertThat(directoryDto.parentProjectId()).isEqualTo(moduleDto.getId());
    assertThat(directoryDto.getCreatedAt()).isEqualTo(now);

    ComponentDto fileDto = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY:src/main/java/dir/Foo.java");
    assertThat(fileDto).isNotNull();
    assertThat(fileDto.name()).isEqualTo("Foo.java");
    assertThat(fileDto.description()).isNull();
    assertThat(fileDto.path()).isEqualTo("src/main/java/dir/Foo.java");
    assertThat(fileDto.language()).isEqualTo("java");
    assertThat(fileDto.uuid()).isEqualTo("DEFG");
    assertThat(fileDto.moduleUuid()).isEqualTo(moduleDto.uuid());
    assertThat(fileDto.moduleUuidPath()).isEqualTo(moduleDto.moduleUuidPath());
    assertThat(fileDto.projectUuid()).isEqualTo(projectDto.uuid());
    assertThat(fileDto.qualifier()).isEqualTo("FIL");
    assertThat(fileDto.scope()).isEqualTo("FIL");
    assertThat(fileDto.parentProjectId()).isEqualTo(moduleDto.getId());
    assertThat(fileDto.getCreatedAt()).isEqualTo(now);

    assertThat(dbIdsRepository.getComponentId(project)).isEqualTo(projectDto.getId());
    assertThat(dbIdsRepository.getComponentId(module)).isEqualTo(moduleDto.getId());
    assertThat(dbIdsRepository.getComponentId(directory)).isEqualTo(directoryDto.getId());
    assertThat(dbIdsRepository.getComponentId(file)).isEqualTo(fileDto.getId());
  }

  @Test
  public void persist_file_directly_attached_on_root_directory() throws Exception {
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.DIRECTORY)
      .setPath("/")
      .addChildRef(3)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(3)
      .setType(Constants.ComponentType.FILE)
      .setPath("pom.xml")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.DIRECTORY, 2).setUuid("CDEF").setKey(PROJECT_KEY + ":/").addChildren(
        DumbComponent.builder(Component.Type.FILE, 3).setUuid("DEFG").setKey(PROJECT_KEY + ":pom.xml").build()
        ).build()
      ).build());

    sut.execute();

    ComponentDto directory = dbClient.componentDao().selectNullableByKey(session, "PROJECT_KEY:/");
    assertThat(directory).isNotNull();
    assertThat(directory.name()).isEqualTo("/");
    assertThat(directory.path()).isEqualTo("/");

    ComponentDto file = dbClient.componentDao().selectNullableByKey(session, "PROJECT_KEY:pom.xml");
    assertThat(file).isNotNull();
    assertThat(file.name()).isEqualTo("pom.xml");
    assertThat(file.path()).isEqualTo("pom.xml");
  }

  @Test
  public void persist_unit_test() throws Exception {
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.DIRECTORY)
      .setPath("src/test/java/dir")
      .addChildRef(3)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(3)
      .setType(Constants.ComponentType.FILE)
      .setPath("src/test/java/dir/FooTest.java")
      .setIsTest(true)
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.DIRECTORY, 2).setUuid("CDEF").setKey(PROJECT_KEY + ":src/test/java/dir").addChildren(
        DumbComponent.builder(Component.Type.FILE, 3).setUuid("DEFG").setKey(PROJECT_KEY + ":src/test/java/dir/FooTest.java").setUnitTest(true).build())
        .build())
      .build());

    sut.execute();

    ComponentDto file = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY + ":src/test/java/dir/FooTest.java");
    assertThat(file).isNotNull();
    assertThat(file.name()).isEqualTo("FooTest.java");
    assertThat(file.path()).isEqualTo("src/test/java/dir/FooTest.java");
    assertThat(file.qualifier()).isEqualTo("UTS");
    assertThat(file.scope()).isEqualTo("FIL");
  }

  @Test
  public void persist_only_new_components() throws Exception {
    // Project amd module already exists
    ComponentDto project = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, project);
    ComponentDto module = ComponentTesting.newModuleDto("BCDE", project).setKey("MODULE_KEY").setName("Module");
    dbClient.componentDao().insert(session, module);
    session.commit();

    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_KEY")
      .setName("Module")
      .addChildRef(3)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(3)
      .setType(Constants.ComponentType.DIRECTORY)
      .setPath("src/main/java/dir")
      .addChildRef(4)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(4)
      .setType(Constants.ComponentType.FILE)
      .setPath("src/main/java/dir/Foo.java")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").addChildren(
        DumbComponent.builder(Component.Type.DIRECTORY, 3).setUuid("CDEF").setKey("MODULE_KEY:src/main/java/dir").addChildren(
          DumbComponent.builder(Component.Type.FILE, 4).setUuid("DEFG").setKey("MODULE_KEY:src/main/java/dir/Foo.java").build())
          .build())
        .build())
      .build());

    sut.execute();

    assertThat(dbTester.countRowsOfTable("projects")).isEqualTo(4);

    ComponentDto projectReloaded = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY);
    assertThat(projectReloaded.getId()).isEqualTo(project.getId());
    assertThat(projectReloaded.uuid()).isEqualTo(project.uuid());

    ComponentDto moduleReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY");
    assertThat(moduleReloaded.getId()).isEqualTo(module.getId());
    assertThat(moduleReloaded.uuid()).isEqualTo(module.uuid());
    assertThat(moduleReloaded.moduleUuid()).isEqualTo(module.moduleUuid());
    assertThat(moduleReloaded.moduleUuidPath()).isEqualTo(module.moduleUuidPath());
    assertThat(moduleReloaded.projectUuid()).isEqualTo(module.projectUuid());
    assertThat(moduleReloaded.parentProjectId()).isEqualTo(module.parentProjectId());

    ComponentDto directory = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY:src/main/java/dir");
    assertThat(directory).isNotNull();
    assertThat(directory.moduleUuid()).isEqualTo(module.uuid());
    assertThat(directory.moduleUuidPath()).isEqualTo(module.moduleUuidPath());
    assertThat(directory.projectUuid()).isEqualTo(project.uuid());
    assertThat(directory.parentProjectId()).isEqualTo(module.getId());

    ComponentDto file = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY:src/main/java/dir/Foo.java");
    assertThat(file).isNotNull();
    assertThat(file.moduleUuid()).isEqualTo(module.uuid());
    assertThat(file.moduleUuidPath()).isEqualTo(module.moduleUuidPath());
    assertThat(file.projectUuid()).isEqualTo(project.uuid());
    assertThat(file.parentProjectId()).isEqualTo(module.getId());
  }

  @Test
  public void compute_parent_project_id() throws Exception {
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_KEY")
      .setName("Module")
      .addChildRef(3)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(3)
      .setType(Constants.ComponentType.MODULE)
      .setKey("SUB_MODULE_1_KEY")
      .setName("Sub Module 1")
      .addChildRef(4)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(4)
      .setType(Constants.ComponentType.MODULE)
      .setKey("SUB_MODULE_2_KEY")
      .setName("Sub Module 2")
      .addChildRef(5)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(5)
      .setType(Constants.ComponentType.DIRECTORY)
      .setPath("src/main/java/dir")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").addChildren(
        DumbComponent.builder(Component.Type.MODULE, 3).setUuid("CDEF").setKey("SUB_MODULE_1_KEY").addChildren(
          DumbComponent.builder(Component.Type.MODULE, 4).setUuid("DEFG").setKey("SUB_MODULE_2_KEY").addChildren(
            DumbComponent.builder(Component.Type.DIRECTORY, 5).setUuid("EFGH").setKey("SUB_MODULE_2_KEY:src/main/java/dir").build())
            .build())
          .build())
        .build())
      .build());

    sut.execute();

    assertThat(dbTester.countRowsOfTable("projects")).isEqualTo(5);

    ComponentDto project = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY);
    assertThat(project).isNotNull();
    assertThat(project.parentProjectId()).isNull();

    ComponentDto module = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY");
    assertThat(module).isNotNull();
    assertThat(module.parentProjectId()).isEqualTo(project.getId());

    ComponentDto subModule1 = dbClient.componentDao().selectNullableByKey(session, "SUB_MODULE_1_KEY");
    assertThat(subModule1).isNotNull();
    assertThat(subModule1.parentProjectId()).isEqualTo(project.getId());

    ComponentDto subModule2 = dbClient.componentDao().selectNullableByKey(session, "SUB_MODULE_2_KEY");
    assertThat(subModule2).isNotNull();
    assertThat(subModule2.parentProjectId()).isEqualTo(project.getId());

    ComponentDto directory = dbClient.componentDao().selectNullableByKey(session, "SUB_MODULE_2_KEY:src/main/java/dir");
    assertThat(directory).isNotNull();
    assertThat(directory.parentProjectId()).isEqualTo(subModule2.getId());
  }

  @Test
  public void persist_multi_modules() throws Exception {
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .addChildRef(2)
      .addChildRef(4)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_A")
      .setName("Module A")
      .addChildRef(3)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(3)
      .setType(Constants.ComponentType.MODULE)
      .setKey("SUB_MODULE_A")
      .setName("Sub Module A")
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(4)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_B")
      .setName("Module B")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_A").addChildren(
        DumbComponent.builder(Component.Type.MODULE, 3).setUuid("DEFG").setKey("SUB_MODULE_A").build()).build(),
      DumbComponent.builder(Component.Type.MODULE, 4).setUuid("CDEF").setKey("MODULE_B").build())
      .build());

    sut.execute();

    assertThat(dbTester.countRowsOfTable("projects")).isEqualTo(4);

    ComponentDto project = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY);
    assertThat(project).isNotNull();
    assertThat(project.moduleUuid()).isNull();
    assertThat(project.moduleUuidPath()).isEqualTo("." + project.uuid() + ".");
    assertThat(project.parentProjectId()).isNull();

    ComponentDto moduleA = dbClient.componentDao().selectNullableByKey(session, "MODULE_A");
    assertThat(moduleA).isNotNull();
    assertThat(moduleA.moduleUuid()).isEqualTo(project.uuid());
    assertThat(moduleA.moduleUuidPath()).isEqualTo(project.moduleUuidPath() + moduleA.uuid() + ".");
    assertThat(moduleA.parentProjectId()).isEqualTo(project.getId());

    ComponentDto subModuleA = dbClient.componentDao().selectNullableByKey(session, "SUB_MODULE_A");
    assertThat(subModuleA).isNotNull();
    assertThat(subModuleA.moduleUuid()).isEqualTo(moduleA.uuid());
    assertThat(subModuleA.moduleUuidPath()).isEqualTo(moduleA.moduleUuidPath() + subModuleA.uuid() + ".");
    assertThat(subModuleA.parentProjectId()).isEqualTo(project.getId());

    ComponentDto moduleB = dbClient.componentDao().selectNullableByKey(session, "MODULE_B");
    assertThat(moduleB).isNotNull();
    assertThat(moduleB.moduleUuid()).isEqualTo(project.uuid());
    assertThat(moduleB.moduleUuidPath()).isEqualTo(project.moduleUuidPath() + moduleB.uuid() + ".");
    assertThat(moduleB.parentProjectId()).isEqualTo(project.getId());
  }

  @Test
  public void nothing_to_persist() throws Exception {
    ComponentDto project = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, project);
    ComponentDto module = ComponentTesting.newModuleDto("BCDE", project).setKey("MODULE_KEY").setName("Module");
    dbClient.componentDao().insert(session, module);
    ComponentDto directory = ComponentTesting.newDirectory(module, "src/main/java/dir").setUuid("CDEF").setKey("MODULE_KEY:src/main/java/dir");
    ComponentDto file = ComponentTesting.newFileDto(module, "DEFG").setPath("src/main/java/dir/Foo.java").setName("Foo.java").setKey("MODULE_KEY:src/main/java/dir/Foo.java");
    dbClient.componentDao().insert(session, directory, file);
    session.commit();

    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_KEY")
      .setName("Module")
      .addChildRef(3)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(3)
      .setType(Constants.ComponentType.DIRECTORY)
      .setPath("src/main/java/dir")
      .addChildRef(4)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(4)
      .setType(Constants.ComponentType.FILE)
      .setPath("src/main/java/dir/Foo.java")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").addChildren(
        DumbComponent.builder(Component.Type.DIRECTORY, 3).setUuid("CDEF").setKey("MODULE_KEY:src/main/java/dir").addChildren(
          DumbComponent.builder(Component.Type.FILE, 4).setUuid("DEFG").setKey("MODULE_KEY:src/main/java/dir/Foo.java").build())
          .build())
        .build())
      .build());

    sut.execute();

    assertThat(dbTester.countRowsOfTable("projects")).isEqualTo(4);
    assertThat(dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY).getId()).isEqualTo(project.getId());
    assertThat(dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY").getId()).isEqualTo(module.getId());
    assertThat(dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY:src/main/java/dir").getId()).isEqualTo(directory.getId());
    assertThat(dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY:src/main/java/dir/Foo.java").getId()).isEqualTo(file.getId());

    ComponentDto projectReloaded = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY);
    assertThat(projectReloaded.getId()).isEqualTo(project.getId());
    assertThat(projectReloaded.uuid()).isEqualTo(project.uuid());
    assertThat(projectReloaded.moduleUuid()).isEqualTo(project.moduleUuid());
    assertThat(projectReloaded.moduleUuidPath()).isEqualTo(project.moduleUuidPath());
    assertThat(projectReloaded.projectUuid()).isEqualTo(project.projectUuid());
    assertThat(projectReloaded.parentProjectId()).isEqualTo(project.parentProjectId());

    ComponentDto moduleReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY");
    assertThat(moduleReloaded.getId()).isEqualTo(module.getId());
    assertThat(moduleReloaded.uuid()).isEqualTo(module.uuid());
    assertThat(moduleReloaded.moduleUuid()).isEqualTo(module.moduleUuid());
    assertThat(moduleReloaded.moduleUuidPath()).isEqualTo(module.moduleUuidPath());
    assertThat(moduleReloaded.projectUuid()).isEqualTo(module.projectUuid());
    assertThat(moduleReloaded.parentProjectId()).isEqualTo(module.parentProjectId());

    ComponentDto directoryReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY:src/main/java/dir");
    assertThat(directoryReloaded).isNotNull();
    assertThat(directoryReloaded.uuid()).isEqualTo(directory.uuid());
    assertThat(directoryReloaded.moduleUuid()).isEqualTo(directory.moduleUuid());
    assertThat(directoryReloaded.moduleUuidPath()).isEqualTo(directory.moduleUuidPath());
    assertThat(directoryReloaded.projectUuid()).isEqualTo(directory.projectUuid());
    assertThat(directoryReloaded.parentProjectId()).isEqualTo(directory.parentProjectId());
    assertThat(directoryReloaded.name()).isEqualTo(directory.name());
    assertThat(directoryReloaded.path()).isEqualTo(directory.path());

    ComponentDto fileReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY:src/main/java/dir/Foo.java");
    assertThat(fileReloaded).isNotNull();
    assertThat(fileReloaded.uuid()).isEqualTo(file.uuid());
    assertThat(fileReloaded.moduleUuid()).isEqualTo(file.moduleUuid());
    assertThat(fileReloaded.moduleUuidPath()).isEqualTo(file.moduleUuidPath());
    assertThat(fileReloaded.projectUuid()).isEqualTo(file.projectUuid());
    assertThat(fileReloaded.parentProjectId()).isEqualTo(file.parentProjectId());
    assertThat(fileReloaded.name()).isEqualTo(file.name());
    assertThat(fileReloaded.path()).isEqualTo(file.path());
  }

  @Test
  public void update_module_name() throws Exception {
    ComponentDto project = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, project);
    ComponentDto module = ComponentTesting.newModuleDto("BCDE", project).setKey("MODULE_KEY").setName("Module").setPath("path");
    dbClient.componentDao().insert(session, module);
    session.commit();

    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("New project name")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_KEY")
      .setName("New module name")
      .setPath("New path")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").build())
      .build());

    sut.execute();

    ComponentDto projectReloaded = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY);
    assertThat(projectReloaded.name()).isEqualTo("New project name");

    ComponentDto moduleReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY");
    assertThat(moduleReloaded.name()).isEqualTo("New module name");
  }

  @Test
  public void update_module_description() throws Exception {
    ComponentDto project = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project").setDescription("Project description");
    dbClient.componentDao().insert(session, project);
    ComponentDto module = ComponentTesting.newModuleDto("BCDE", project).setKey("MODULE_KEY").setName("Module");
    dbClient.componentDao().insert(session, module);
    session.commit();

    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .setDescription("New project description")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_KEY")
      .setName("Module")
      .setDescription("New module description")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").build())
      .build());

    sut.execute();

    ComponentDto projectReloaded = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY);
    assertThat(projectReloaded.description()).isEqualTo("New project description");

    ComponentDto moduleReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY");
    assertThat(moduleReloaded.description()).isEqualTo("New module description");
  }

  @Test
  public void update_module_path() throws Exception {
    ComponentDto project = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, project);
    ComponentDto module = ComponentTesting.newModuleDto("BCDE", project).setKey("MODULE_KEY").setName("Module").setPath("path");
    dbClient.componentDao().insert(session, module);
    session.commit();

    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_KEY")
      .setName("Module")
      .setPath("New path")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").build())
      .build());

    sut.execute();

    ComponentDto moduleReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_KEY");
    assertThat(moduleReloaded.path()).isEqualTo("New path");
  }

  @Test
  public void update_module_uuid_when_moving_a_module() throws Exception {
    ComponentDto project = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, project);
    ComponentDto moduleA = ComponentTesting.newModuleDto("EDCB", project).setKey("MODULE_A").setName("Module A");
    ComponentDto moduleB = ComponentTesting.newModuleDto("BCDE", project).setKey("MODULE_B").setName("Module B");
    dbClient.componentDao().insert(session, moduleA, moduleB);
    ComponentDto directory = ComponentTesting.newDirectory(moduleB, "src/main/java/dir").setUuid("CDEF").setKey("MODULE_B:src/main/java/dir");
    ComponentDto file = ComponentTesting.newFileDto(moduleB, "DEFG").setPath("src/main/java/dir/Foo.java").setName("Foo.java").setKey("MODULE_B:src/main/java/dir/Foo.java");
    dbClient.componentDao().insert(session, directory, file);
    session.commit();

    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("Project")
      .addChildRef(2)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(2)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_A")
      .setName("Module A")
      .addChildRef(3)
      .build());
    // Module B is now a sub module of module A
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(3)
      .setType(Constants.ComponentType.MODULE)
      .setKey("MODULE_B")
      .setName("Module B")
      .addChildRef(4)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(4)
      .setType(Constants.ComponentType.DIRECTORY)
      .setPath("src/main/java/dir")
      .addChildRef(5)
      .build());
    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(5)
      .setType(Constants.ComponentType.FILE)
      .setPath("src/main/java/dir/Foo.java")
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(
      DumbComponent.builder(Component.Type.MODULE, 2).setUuid("EDCB").setKey("MODULE_A").addChildren(
        DumbComponent.builder(Component.Type.MODULE, 3).setUuid("BCDE").setKey("MODULE_B").addChildren(
          DumbComponent.builder(Component.Type.DIRECTORY, 4).setUuid("CDEF").setKey("MODULE_B:src/main/java/dir").addChildren(
            DumbComponent.builder(Component.Type.FILE, 5).setUuid("DEFG").setKey("MODULE_B:src/main/java/dir/Foo.java").build())
            .build())
          .build())
        .build())
      .build());

    sut.execute();

    assertThat(dbTester.countRowsOfTable("projects")).isEqualTo(5);

    ComponentDto moduleAreloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_A");
    assertThat(moduleAreloaded).isNotNull();

    ComponentDto moduleBReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_B");
    assertThat(moduleBReloaded).isNotNull();
    assertThat(moduleBReloaded.uuid()).isEqualTo(moduleB.uuid());
    assertThat(moduleBReloaded.moduleUuid()).isEqualTo(moduleAreloaded.uuid());
    assertThat(moduleBReloaded.moduleUuidPath()).isEqualTo(moduleAreloaded.moduleUuidPath() + moduleBReloaded.uuid() + ".");
    assertThat(moduleBReloaded.projectUuid()).isEqualTo(project.uuid());
    assertThat(moduleBReloaded.parentProjectId()).isEqualTo(project.getId());

    ComponentDto directoryReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_B:src/main/java/dir");
    assertThat(directoryReloaded).isNotNull();
    assertThat(directoryReloaded.uuid()).isEqualTo(directory.uuid());
    assertThat(directoryReloaded.moduleUuid()).isEqualTo(moduleBReloaded.uuid());
    assertThat(directoryReloaded.moduleUuidPath()).isEqualTo(moduleBReloaded.moduleUuidPath());
    assertThat(directoryReloaded.projectUuid()).isEqualTo(project.uuid());
    assertThat(directoryReloaded.parentProjectId()).isEqualTo(moduleBReloaded.getId());

    ComponentDto fileReloaded = dbClient.componentDao().selectNullableByKey(session, "MODULE_B:src/main/java/dir/Foo.java");
    assertThat(fileReloaded).isNotNull();
    assertThat(fileReloaded.uuid()).isEqualTo(file.uuid());
    assertThat(fileReloaded.moduleUuid()).isEqualTo(moduleBReloaded.uuid());
    assertThat(fileReloaded.moduleUuidPath()).isEqualTo(moduleBReloaded.moduleUuidPath());
    assertThat(fileReloaded.projectUuid()).isEqualTo(project.uuid());
    assertThat(fileReloaded.parentProjectId()).isEqualTo(moduleBReloaded.getId());
  }

  @Test
  public void not_update_create_at() throws Exception {
    Date oldDate = DateUtils.parseDate("2015-01-01");
    ComponentDto project = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project").setCreatedAt(oldDate);
    dbClient.componentDao().insert(session, project);
    ComponentDto module = ComponentTesting.newModuleDto("BCDE", project).setKey("MODULE_KEY").setName("Module").setPath("path").setCreatedAt(oldDate);
    dbClient.componentDao().insert(session, module);
    session.commit();

    reportReader.putComponent(BatchReport.Component.newBuilder()
      .setRef(1)
      .setType(Constants.ComponentType.PROJECT)
      .setKey(PROJECT_KEY)
      .setName("New project name")
      .addChildRef(2)
      .build());

    treeRootHolder.setRoot(DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).build());

    sut.execute();

    ComponentDto projectReloaded = dbClient.componentDao().selectNullableByKey(session, PROJECT_KEY);
    assertThat(projectReloaded.name()).isEqualTo("New project name");
    assertThat(projectReloaded.getCreatedAt()).isNotEqualTo(now);
  }

}


File: server/sonar-server/src/test/java/org/sonar/server/computation/step/PersistSnapshotsStepTest.java
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

import java.util.List;
import org.junit.After;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.experimental.categories.Category;
import org.sonar.api.CoreProperties;
import org.sonar.api.utils.DateUtils;
import org.sonar.api.utils.System2;
import org.sonar.batch.protocol.output.BatchReport;
import org.sonar.core.component.ComponentDto;
import org.sonar.core.component.SnapshotDto;
import org.sonar.core.component.SnapshotQuery;
import org.sonar.core.persistence.DbSession;
import org.sonar.core.persistence.DbTester;
import org.sonar.server.component.ComponentTesting;
import org.sonar.server.component.SnapshotTesting;
import org.sonar.server.component.db.ComponentDao;
import org.sonar.server.component.db.SnapshotDao;
import org.sonar.server.computation.batch.BatchReportReaderRule;
import org.sonar.server.computation.batch.TreeRootHolderRule;
import org.sonar.server.computation.component.Component;
import org.sonar.server.computation.component.DbIdsRepository;
import org.sonar.server.computation.component.DumbComponent;
import org.sonar.server.computation.period.Period;
import org.sonar.server.computation.period.PeriodsHolderRule;
import org.sonar.server.db.DbClient;
import org.sonar.test.DbTests;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

@Category(DbTests.class)
public class PersistSnapshotsStepTest extends BaseStepTest {

  private static final String PROJECT_KEY = "PROJECT_KEY";

  @ClassRule
  public static DbTester dbTester = new DbTester();

  @Rule
  public TreeRootHolderRule treeRootHolder = new TreeRootHolderRule();

  @Rule
  public BatchReportReaderRule reportReader = new BatchReportReaderRule();

  @Rule
  public PeriodsHolderRule periodsHolderRule = new PeriodsHolderRule();

  System2 system2 = mock(System2.class);

  DbIdsRepository dbIdsRepository;

  DbSession session;

  DbClient dbClient;

  long analysisDate;

  long now;

  PersistSnapshotsStep sut;

  @Before
  public void setup() throws Exception {
    dbTester.truncateTables();
    session = dbTester.myBatis().openSession(false);
    dbClient = new DbClient(dbTester.database(), dbTester.myBatis(), new ComponentDao(), new SnapshotDao());

    analysisDate = DateUtils.parseDateQuietly("2015-06-01").getTime();
    reportReader.setMetadata(BatchReport.Metadata.newBuilder()
      .setAnalysisDate(analysisDate)
      .build());
    dbIdsRepository = new DbIdsRepository();

    now = DateUtils.parseDateQuietly("2015-06-02").getTime();

    when(system2.now()).thenReturn(now);

    sut = new PersistSnapshotsStep(system2, dbClient, treeRootHolder, reportReader, dbIdsRepository, periodsHolderRule);
  }

  @Override
  protected ComputationStep step() {
    return sut;
  }

  @After
  public void tearDown() {
    session.close();
  }

  @Test
  public void persist_snapshots() throws Exception {
    ComponentDto projectDto = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, projectDto);
    ComponentDto moduleDto = ComponentTesting.newModuleDto("BCDE", projectDto).setKey("MODULE_KEY").setName("Module");
    dbClient.componentDao().insert(session, moduleDto);
    ComponentDto directoryDto = ComponentTesting.newDirectory(moduleDto, "CDEF", "MODULE_KEY:src/main/java/dir").setKey("MODULE_KEY:src/main/java/dir");
    dbClient.componentDao().insert(session, directoryDto);
    ComponentDto fileDto = ComponentTesting.newFileDto(moduleDto, "DEFG").setKey("MODULE_KEY:src/main/java/dir/Foo.java");
    dbClient.componentDao().insert(session, fileDto);
    session.commit();

    Component file = DumbComponent.builder(Component.Type.FILE, 4).setUuid("DEFG").setKey("MODULE_KEY:src/main/java/dir/Foo.java").build();
    Component directory = DumbComponent.builder(Component.Type.DIRECTORY, 3).setUuid("CDEF").setKey("MODULE_KEY:src/main/java/dir").addChildren(file).build();
    Component module = DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").setVersion("1.1").addChildren(directory).build();
    Component project = DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).setVersion("1.0").addChildren(module).build();
    treeRootHolder.setRoot(project);

    dbIdsRepository.setComponentId(project, projectDto.getId());
    dbIdsRepository.setComponentId(module, moduleDto.getId());
    dbIdsRepository.setComponentId(directory, directoryDto.getId());
    dbIdsRepository.setComponentId(file, fileDto.getId());

    sut.execute();

    assertThat(dbTester.countRowsOfTable("snapshots")).isEqualTo(4);

    SnapshotDto projectSnapshot = getUnprocessedSnapshot(projectDto.getId());
    assertThat(projectSnapshot.getComponentId()).isEqualTo(projectDto.getId());
    assertThat(projectSnapshot.getRootProjectId()).isEqualTo(projectDto.getId());
    assertThat(projectSnapshot.getRootId()).isNull();
    assertThat(projectSnapshot.getParentId()).isNull();
    assertThat(projectSnapshot.getDepth()).isEqualTo(0);
    assertThat(projectSnapshot.getPath()).isEqualTo("");
    assertThat(projectSnapshot.getQualifier()).isEqualTo("TRK");
    assertThat(projectSnapshot.getScope()).isEqualTo("PRJ");
    assertThat(projectSnapshot.getVersion()).isEqualTo("1.0");
    assertThat(projectSnapshot.getLast()).isFalse();
    assertThat(projectSnapshot.getStatus()).isEqualTo("U");
    assertThat(projectSnapshot.getCreatedAt()).isEqualTo(analysisDate);
    assertThat(projectSnapshot.getBuildDate()).isEqualTo(now);

    SnapshotDto moduleSnapshot = getUnprocessedSnapshot(moduleDto.getId());
    assertThat(moduleSnapshot.getComponentId()).isEqualTo(moduleDto.getId());
    assertThat(moduleSnapshot.getRootProjectId()).isEqualTo(projectDto.getId());
    assertThat(moduleSnapshot.getRootId()).isEqualTo(projectSnapshot.getId());
    assertThat(moduleSnapshot.getParentId()).isEqualTo(projectSnapshot.getId());
    assertThat(moduleSnapshot.getDepth()).isEqualTo(1);
    assertThat(moduleSnapshot.getPath()).isEqualTo(projectSnapshot.getId() + ".");
    assertThat(moduleSnapshot.getQualifier()).isEqualTo("BRC");
    assertThat(moduleSnapshot.getScope()).isEqualTo("PRJ");
    assertThat(moduleSnapshot.getVersion()).isEqualTo("1.1");
    assertThat(moduleSnapshot.getLast()).isFalse();
    assertThat(moduleSnapshot.getStatus()).isEqualTo("U");
    assertThat(moduleSnapshot.getCreatedAt()).isEqualTo(analysisDate);
    assertThat(moduleSnapshot.getBuildDate()).isEqualTo(now);

    SnapshotDto directorySnapshot = getUnprocessedSnapshot(directoryDto.getId());
    assertThat(directorySnapshot.getComponentId()).isEqualTo(directoryDto.getId());
    assertThat(directorySnapshot.getRootProjectId()).isEqualTo(projectDto.getId());
    assertThat(directorySnapshot.getRootId()).isEqualTo(projectSnapshot.getId());
    assertThat(directorySnapshot.getParentId()).isEqualTo(moduleSnapshot.getId());
    assertThat(directorySnapshot.getDepth()).isEqualTo(2);
    assertThat(directorySnapshot.getPath()).isEqualTo(projectSnapshot.getId() + "." + moduleSnapshot.getId() + ".");
    assertThat(directorySnapshot.getQualifier()).isEqualTo("DIR");
    assertThat(directorySnapshot.getScope()).isEqualTo("DIR");
    assertThat(directorySnapshot.getVersion()).isNull();
    assertThat(directorySnapshot.getLast()).isFalse();
    assertThat(directorySnapshot.getStatus()).isEqualTo("U");
    assertThat(directorySnapshot.getCreatedAt()).isEqualTo(analysisDate);
    assertThat(directorySnapshot.getBuildDate()).isEqualTo(now);

    SnapshotDto fileSnapshot = getUnprocessedSnapshot(fileDto.getId());
    assertThat(fileSnapshot.getComponentId()).isEqualTo(fileDto.getId());
    assertThat(fileSnapshot.getRootProjectId()).isEqualTo(projectDto.getId());
    assertThat(fileSnapshot.getRootId()).isEqualTo(projectSnapshot.getId());
    assertThat(fileSnapshot.getParentId()).isEqualTo(directorySnapshot.getId());
    assertThat(fileSnapshot.getDepth()).isEqualTo(3);
    assertThat(fileSnapshot.getPath()).isEqualTo(projectSnapshot.getId() + "." + moduleSnapshot.getId() + "." + directorySnapshot.getId() + ".");
    assertThat(fileSnapshot.getQualifier()).isEqualTo("FIL");
    assertThat(fileSnapshot.getScope()).isEqualTo("FIL");
    assertThat(fileSnapshot.getVersion()).isNull();
    assertThat(fileSnapshot.getLast()).isFalse();
    assertThat(fileSnapshot.getStatus()).isEqualTo("U");
    assertThat(fileSnapshot.getCreatedAt()).isEqualTo(analysisDate);
    assertThat(fileSnapshot.getBuildDate()).isEqualTo(now);

    assertThat(dbIdsRepository.getSnapshotId(project)).isEqualTo(projectSnapshot.getId());
    assertThat(dbIdsRepository.getComponentId(module)).isEqualTo(moduleDto.getId());
    assertThat(dbIdsRepository.getComponentId(directory)).isEqualTo(directoryDto.getId());
    assertThat(dbIdsRepository.getComponentId(file)).isEqualTo(fileDto.getId());
  }

  @Test
  public void persist_unit_test() throws Exception {
    ComponentDto projectDto = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, projectDto);
    ComponentDto moduleDto = ComponentTesting.newModuleDto("BCDE", projectDto).setKey("MODULE_KEY").setName("Module");
    dbClient.componentDao().insert(session, moduleDto);
    ComponentDto directoryDto = ComponentTesting.newDirectory(moduleDto, "CDEF", "MODULE_KEY:src/test/java/dir").setKey("MODULE_KEY:src/test/java/dir");
    dbClient.componentDao().insert(session, directoryDto);
    ComponentDto fileDto = ComponentTesting.newFileDto(moduleDto, "DEFG").setKey("MODULE_KEY:src/test/java/dir/FooTest.java").setQualifier("UTS");
    dbClient.componentDao().insert(session, fileDto);
    session.commit();

    Component file = DumbComponent.builder(Component.Type.FILE, 3).setUuid("DEFG").setKey(PROJECT_KEY + ":src/main/java/dir/Foo.java").setUnitTest(true).build();
    Component directory = DumbComponent.builder(Component.Type.DIRECTORY, 2).setUuid("CDEF").setKey(PROJECT_KEY + ":src/main/java/dir").addChildren(file).build();
    Component project = DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(directory).build();
    treeRootHolder.setRoot(project);

    dbIdsRepository.setComponentId(project, projectDto.getId());
    dbIdsRepository.setComponentId(directory, directoryDto.getId());
    dbIdsRepository.setComponentId(file, fileDto.getId());

    sut.execute();

    SnapshotDto fileSnapshot = getUnprocessedSnapshot(fileDto.getId());
    assertThat(fileSnapshot.getQualifier()).isEqualTo("UTS");
    assertThat(fileSnapshot.getScope()).isEqualTo("FIL");
  }

  @Test
  public void persist_snapshots_on_multi_modules() throws Exception {
    ComponentDto projectDto = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY);
    dbClient.componentDao().insert(session, projectDto);
    ComponentDto moduleADto = ComponentTesting.newModuleDto("BCDE", projectDto).setKey("MODULE_A");
    dbClient.componentDao().insert(session, moduleADto);
    ComponentDto subModuleADto = ComponentTesting.newModuleDto("CDEF", moduleADto).setKey("SUB_MODULE_A");
    dbClient.componentDao().insert(session, subModuleADto);
    ComponentDto moduleBDto = ComponentTesting.newModuleDto("DEFG", projectDto).setKey("MODULE_B");
    dbClient.componentDao().insert(session, moduleBDto);
    session.commit();

    Component moduleB = DumbComponent.builder(Component.Type.MODULE, 4).setUuid("DEFG").setKey("MODULE_B").build();
    Component subModuleA = DumbComponent.builder(Component.Type.MODULE, 3).setUuid("CDEF").setKey("SUB_MODULE_A").build();
    Component moduleA = DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_A").addChildren(subModuleA).build();
    Component project = DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(moduleA, moduleB).build();
    treeRootHolder.setRoot(project);

    dbIdsRepository.setComponentId(project, projectDto.getId());
    dbIdsRepository.setComponentId(moduleA, moduleADto.getId());
    dbIdsRepository.setComponentId(subModuleA, subModuleADto.getId());
    dbIdsRepository.setComponentId(moduleB, moduleBDto.getId());

    sut.execute();

    assertThat(dbTester.countRowsOfTable("snapshots")).isEqualTo(4);

    SnapshotDto projectSnapshot = getUnprocessedSnapshot(projectDto.getId());
    assertThat(projectSnapshot.getRootProjectId()).isEqualTo(projectDto.getId());
    assertThat(projectSnapshot.getRootId()).isNull();
    assertThat(projectSnapshot.getParentId()).isNull();
    assertThat(projectSnapshot.getDepth()).isEqualTo(0);
    assertThat(projectSnapshot.getPath()).isEqualTo("");

    SnapshotDto moduleASnapshot = getUnprocessedSnapshot(moduleADto.getId());
    assertThat(moduleASnapshot.getRootProjectId()).isEqualTo(projectDto.getId());
    assertThat(moduleASnapshot.getRootId()).isEqualTo(projectSnapshot.getId());
    assertThat(moduleASnapshot.getParentId()).isEqualTo(projectSnapshot.getId());
    assertThat(moduleASnapshot.getDepth()).isEqualTo(1);
    assertThat(moduleASnapshot.getPath()).isEqualTo(projectSnapshot.getId() + ".");

    SnapshotDto subModuleASnapshot = getUnprocessedSnapshot(subModuleADto.getId());
    assertThat(subModuleASnapshot.getRootProjectId()).isEqualTo(projectDto.getId());
    assertThat(subModuleASnapshot.getRootId()).isEqualTo(projectSnapshot.getId());
    assertThat(subModuleASnapshot.getParentId()).isEqualTo(moduleASnapshot.getId());
    assertThat(subModuleASnapshot.getDepth()).isEqualTo(2);
    assertThat(subModuleASnapshot.getPath()).isEqualTo(projectSnapshot.getId() + "." + moduleASnapshot.getId() + ".");

    SnapshotDto moduleBSnapshot = getUnprocessedSnapshot(moduleBDto.getId());
    assertThat(moduleBSnapshot.getRootProjectId()).isEqualTo(projectDto.getId());
    assertThat(moduleBSnapshot.getRootId()).isEqualTo(projectSnapshot.getId());
    assertThat(moduleBSnapshot.getParentId()).isEqualTo(projectSnapshot.getId());
    assertThat(moduleBSnapshot.getDepth()).isEqualTo(1);
    assertThat(moduleBSnapshot.getPath()).isEqualTo(projectSnapshot.getId() + ".");
  }

  @Test
  public void persist_snapshots_with_periods() throws Exception {
    ComponentDto projectDto = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, projectDto);
    SnapshotDto snapshotDto = SnapshotTesting.createForProject(projectDto).setCreatedAt(DateUtils.parseDateQuietly("2015-01-01").getTime());
    dbClient.snapshotDao().insert(session, snapshotDto);
    session.commit();
    periodsHolderRule.addPeriod(new Period(1, CoreProperties.TIMEMACHINE_MODE_DATE, "2015-01-01", analysisDate));

    Component project = DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).build();
    treeRootHolder.setRoot(project);
    dbIdsRepository.setComponentId(project, projectDto.getId());

    sut.execute();

    SnapshotDto projectSnapshot = getUnprocessedSnapshot(projectDto.getId());
    assertThat(projectSnapshot.getPeriodMode(1)).isEqualTo(CoreProperties.TIMEMACHINE_MODE_DATE);
    assertThat(projectSnapshot.getPeriodDate(1)).isEqualTo(analysisDate);
    assertThat(projectSnapshot.getPeriodModeParameter(1)).isNotNull();
  }

  @Test
  public void only_persist_snapshots_with_periods_on_project_and_module() throws Exception {
    periodsHolderRule.addPeriod(new Period(1, CoreProperties.TIMEMACHINE_MODE_PREVIOUS_ANALYSIS, null, analysisDate));

    ComponentDto projectDto = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, projectDto);
    SnapshotDto projectSnapshot = SnapshotTesting.createForProject(projectDto);
    dbClient.snapshotDao().insert(session, projectSnapshot);

    ComponentDto moduleDto = ComponentTesting.newModuleDto("BCDE", projectDto).setKey("MODULE_KEY").setName("Module");
    dbClient.componentDao().insert(session, moduleDto);
    SnapshotDto moduleSnapshot = SnapshotTesting.createForComponent(moduleDto, projectSnapshot);
    dbClient.snapshotDao().insert(session, moduleSnapshot);

    ComponentDto directoryDto = ComponentTesting.newDirectory(moduleDto, "CDEF", "MODULE_KEY:src/main/java/dir").setKey("MODULE_KEY:src/main/java/dir");
    dbClient.componentDao().insert(session, directoryDto);
    SnapshotDto directorySnapshot = SnapshotTesting.createForComponent(directoryDto, moduleSnapshot);
    dbClient.snapshotDao().insert(session, directorySnapshot);

    ComponentDto fileDto = ComponentTesting.newFileDto(moduleDto, "DEFG").setKey("MODULE_KEY:src/main/java/dir/Foo.java");
    dbClient.componentDao().insert(session, fileDto);
    SnapshotDto fileSnapshot = SnapshotTesting.createForComponent(fileDto, directorySnapshot);
    dbClient.snapshotDao().insert(session, fileSnapshot);

    session.commit();

    Component file = DumbComponent.builder(Component.Type.FILE, 4).setUuid("DEFG").setKey("MODULE_KEY:src/main/java/dir/Foo.java").build();
    Component directory = DumbComponent.builder(Component.Type.DIRECTORY, 3).setUuid("CDEF").setKey("MODULE_KEY:src/main/java/dir").addChildren(file).build();
    Component module = DumbComponent.builder(Component.Type.MODULE, 2).setUuid("BCDE").setKey("MODULE_KEY").addChildren(directory).build();
    Component project = DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).addChildren(module).build();
    treeRootHolder.setRoot(project);

    dbIdsRepository.setComponentId(project, projectDto.getId());
    dbIdsRepository.setComponentId(module, moduleDto.getId());
    dbIdsRepository.setComponentId(directory, directoryDto.getId());
    dbIdsRepository.setComponentId(file, fileDto.getId());

    sut.execute();

    SnapshotDto newProjectSnapshot = getUnprocessedSnapshot(projectDto.getId());
    assertThat(newProjectSnapshot.getPeriodMode(1)).isEqualTo(CoreProperties.TIMEMACHINE_MODE_PREVIOUS_ANALYSIS);

    SnapshotDto newModuleSnapshot = getUnprocessedSnapshot(moduleDto.getId());
    assertThat(newModuleSnapshot.getPeriodMode(1)).isEqualTo(CoreProperties.TIMEMACHINE_MODE_PREVIOUS_ANALYSIS);

    SnapshotDto newDirectorySnapshot = getUnprocessedSnapshot(directoryDto.getId());
    assertThat(newDirectorySnapshot.getPeriodMode(1)).isNull();

    SnapshotDto newFileSnapshot = getUnprocessedSnapshot(fileDto.getId());
    assertThat(newFileSnapshot.getPeriodMode(1)).isNull();
  }

  @Test
  public void set_no_period_on_snapshots_when_no_period() throws Exception {
    ComponentDto projectDto = ComponentTesting.newProjectDto("ABCD").setKey(PROJECT_KEY).setName("Project");
    dbClient.componentDao().insert(session, projectDto);
    SnapshotDto snapshotDto = SnapshotTesting.createForProject(projectDto);
    dbClient.snapshotDao().insert(session, snapshotDto);
    session.commit();

    Component project = DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("ABCD").setKey(PROJECT_KEY).build();
    treeRootHolder.setRoot(project);
    dbIdsRepository.setComponentId(project, projectDto.getId());

    sut.execute();

    SnapshotDto projectSnapshot = getUnprocessedSnapshot(projectDto.getId());
    assertThat(projectSnapshot.getPeriodMode(1)).isNull();
    assertThat(projectSnapshot.getPeriodDate(1)).isNull();
    assertThat(projectSnapshot.getPeriodModeParameter(1)).isNull();
  }

  private SnapshotDto getUnprocessedSnapshot(long componentId) {
    List<SnapshotDto> projectSnapshots = dbClient.snapshotDao().selectSnapshotsByQuery(session,
      new SnapshotQuery().setComponentId(componentId).setIsLast(false).setStatus(SnapshotDto.STATUS_UNPROCESSED));
    assertThat(projectSnapshots).hasSize(1);
    return projectSnapshots.get(0);
  }

}


File: sonar-batch/src/main/java/org/sonar/batch/qualitygate/QualityGateVerifier.java
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
package org.sonar.batch.qualitygate;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import java.util.Collection;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.apache.commons.lang.StringUtils;
import org.sonar.api.batch.Decorator;
import org.sonar.api.batch.DecoratorBarriers;
import org.sonar.api.batch.DecoratorContext;
import org.sonar.api.batch.DependedUpon;
import org.sonar.api.batch.DependsUpon;
import org.sonar.api.i18n.I18n;
import org.sonar.api.measures.CoreMetrics;
import org.sonar.api.measures.Measure;
import org.sonar.api.measures.Metric;
import org.sonar.api.resources.Project;
import org.sonar.api.resources.Resource;
import org.sonar.api.resources.ResourceUtils;
import org.sonar.api.utils.Duration;
import org.sonar.api.utils.Durations;
import org.sonar.batch.index.BatchComponentCache;
import org.sonar.core.qualitygate.db.QualityGateConditionDto;
import org.sonar.core.timemachine.Periods;

public class QualityGateVerifier implements Decorator {

  private static final String VARIATION_METRIC_PREFIX = "new_";
  private static final String VARIATION = "variation";
  private static final Map<String, String> OPERATOR_LABELS = ImmutableMap.of(
    QualityGateConditionDto.OPERATOR_EQUALS, "=",
    QualityGateConditionDto.OPERATOR_NOT_EQUALS, "!=",
    QualityGateConditionDto.OPERATOR_GREATER_THAN, ">",
    QualityGateConditionDto.OPERATOR_LESS_THAN, "<");

  private QualityGate qualityGate;

  private Periods periods;
  private I18n i18n;
  private Durations durations;
  private BatchComponentCache resourceCache;

  public QualityGateVerifier(QualityGate qualityGate, BatchComponentCache resourceCache, Periods periods, I18n i18n, Durations durations) {
    this.qualityGate = qualityGate;
    this.resourceCache = resourceCache;
    this.periods = periods;
    this.i18n = i18n;
    this.durations = durations;
  }

  @DependedUpon
  public Metric generatesQualityGateStatus() {
    return CoreMetrics.ALERT_STATUS;
  }

  @DependsUpon
  public String dependsOnVariations() {
    return DecoratorBarriers.END_OF_TIME_MACHINE;
  }

  @DependsUpon
  public Collection<Metric> dependsUponMetrics() {
    Set<Metric> metrics = Sets.newHashSet();
    for (ResolvedCondition condition : qualityGate.conditions()) {
      metrics.add(condition.metric());
    }
    return metrics;
  }

  @Override
  public boolean shouldExecuteOnProject(Project project) {
    return qualityGate.isEnabled();
  }

  @Override
  public void decorate(Resource resource, DecoratorContext context) {
    if (ResourceUtils.isRootProject(resource)) {
      checkProjectConditions(resource, context);
    }
  }

  private void checkProjectConditions(Resource project, DecoratorContext context) {
    Metric.Level globalLevel = Metric.Level.OK;
    QualityGateDetails details = new QualityGateDetails();
    List<String> labels = Lists.newArrayList();

    for (ResolvedCondition condition : qualityGate.conditions()) {
      Measure measure = context.getMeasure(condition.metric());
      if (measure != null) {
        Metric.Level level = ConditionUtils.getLevel(condition, measure);

        measure.setAlertStatus(level);
        String text = getText(project, condition, level);
        if (!StringUtils.isBlank(text)) {
          measure.setAlertText(text);
          labels.add(text);
        }

        context.saveMeasure(measure);

        if (Metric.Level.WARN == level && globalLevel != Metric.Level.ERROR) {
          globalLevel = Metric.Level.WARN;

        } else if (Metric.Level.ERROR == level) {
          globalLevel = Metric.Level.ERROR;
        }

        details.addCondition(condition, level, ConditionUtils.getValue(condition, measure));
      }
    }

    Measure globalMeasure = new Measure(CoreMetrics.ALERT_STATUS, globalLevel);
    globalMeasure.setAlertStatus(globalLevel);
    globalMeasure.setAlertText(StringUtils.join(labels, ", "));
    context.saveMeasure(globalMeasure);

    details.setLevel(globalLevel);
    Measure detailsMeasure = new Measure(CoreMetrics.QUALITY_GATE_DETAILS, details.toJson());
    context.saveMeasure(detailsMeasure);

  }

  private String getText(Resource project, ResolvedCondition condition, Metric.Level level) {
    if (level == Metric.Level.OK) {
      return null;
    }
    return getAlertLabel(project, condition, level);
  }

  private String getAlertLabel(Resource project, ResolvedCondition condition, Metric.Level level) {
    Integer alertPeriod = condition.period();
    String metric = i18n.message(Locale.ENGLISH, "metric." + condition.metricKey() + ".name", condition.metric().getName());

    StringBuilder stringBuilder = new StringBuilder();
    stringBuilder.append(metric);

    if (alertPeriod != null && !condition.metricKey().startsWith(VARIATION_METRIC_PREFIX)) {
      String variation = i18n.message(Locale.ENGLISH, VARIATION, VARIATION).toLowerCase();
      stringBuilder.append(" ").append(variation);
    }

    stringBuilder
      .append(" ").append(operatorLabel(condition.operator())).append(" ")
      .append(alertValue(condition, level));

    // Disabled because snapshot is no more created by the batch
//    if (alertPeriod != null) {
//      Snapshot snapshot = resourceCache.get(project).snapshot();
//      stringBuilder.append(" ").append(periods.label(snapshot, alertPeriod));
//    }

    return stringBuilder.toString();
  }

  private String alertValue(ResolvedCondition condition, Metric.Level level) {
    String value = level.equals(Metric.Level.ERROR) ? condition.errorThreshold() : condition.warningThreshold();
    if (condition.metric().getType().equals(Metric.ValueType.WORK_DUR)) {
      return formatDuration(value);
    } else {
      return value;
    }
  }

  private String formatDuration(String value) {
    return durations.format(Locale.ENGLISH, Duration.create(Long.parseLong(value)), Durations.DurationFormat.SHORT);
  }

  private String operatorLabel(String operator) {
    return OPERATOR_LABELS.get(operator);
  }

  @Override
  public String toString() {
    return getClass().getSimpleName();
  }
}


File: sonar-batch/src/test/java/org/sonar/batch/qualitygate/QualityGateVerifierTest.java
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
package org.sonar.batch.qualitygate;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import java.util.ArrayList;
import java.util.Locale;
import org.apache.commons.lang.NotImplementedException;
import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.mockito.ArgumentMatcher;
import org.sonar.api.batch.DecoratorBarriers;
import org.sonar.api.batch.DecoratorContext;
import org.sonar.api.database.model.Snapshot;
import org.sonar.api.i18n.I18n;
import org.sonar.api.measures.CoreMetrics;
import org.sonar.api.measures.Measure;
import org.sonar.api.measures.Metric;
import org.sonar.api.measures.Metric.Level;
import org.sonar.api.resources.File;
import org.sonar.api.resources.Project;
import org.sonar.api.resources.Resource;
import org.sonar.api.test.IsMeasure;
import org.sonar.api.utils.Duration;
import org.sonar.api.utils.Durations;
import org.sonar.batch.index.BatchComponentCache;
import org.sonar.core.qualitygate.db.QualityGateConditionDto;
import org.sonar.core.timemachine.Periods;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Matchers.any;
import static org.mockito.Matchers.anyString;
import static org.mockito.Matchers.argThat;
import static org.mockito.Matchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class QualityGateVerifierTest {

  QualityGateVerifier verifier;
  DecoratorContext context;
  QualityGate qualityGate;

  Measure measureClasses;
  Measure measureCoverage;
  Measure measureComplexity;
  Resource project;
  Snapshot snapshot;
  Periods periods;
  I18n i18n;
  Durations durations;

  @Before
  public void before() {
    context = mock(DecoratorContext.class);
    periods = mock(Periods.class);
    i18n = mock(I18n.class);
    when(i18n.message(any(Locale.class), eq("variation"), eq("variation"))).thenReturn("variation");
    durations = mock(Durations.class);

    measureClasses = new Measure(CoreMetrics.CLASSES, 20d);
    measureCoverage = new Measure(CoreMetrics.COVERAGE, 35d);
    measureComplexity = new Measure(CoreMetrics.COMPLEXITY, 50d);

    when(context.getMeasure(CoreMetrics.CLASSES)).thenReturn(measureClasses);
    when(context.getMeasure(CoreMetrics.COVERAGE)).thenReturn(measureCoverage);
    when(context.getMeasure(CoreMetrics.COMPLEXITY)).thenReturn(measureComplexity);

    snapshot = mock(Snapshot.class);
    qualityGate = mock(QualityGate.class);
    when(qualityGate.isEnabled()).thenReturn(true);

    project = new Project("foo");

    BatchComponentCache resourceCache = new BatchComponentCache();
    resourceCache.add(project, null).setSnapshot(snapshot);

    verifier = new QualityGateVerifier(qualityGate, resourceCache, periods, i18n, durations);
  }

  @Test
  public void should_be_executed_if_quality_gate_is_enabled() {
    assertThat(verifier.shouldExecuteOnProject((Project) project)).isTrue();
    when(qualityGate.isEnabled()).thenReturn(false);
    assertThat(verifier.shouldExecuteOnProject((Project) project)).isFalse();
  }

  @Test
  public void test_toString() {
    assertThat(verifier.toString()).isEqualTo("QualityGateVerifier");
  }

  @Test
  public void generates_quality_gates_status() {
    assertThat(verifier.generatesQualityGateStatus()).isEqualTo(CoreMetrics.ALERT_STATUS);
  }

  @Test
  public void depends_on_variations() {
    assertThat(verifier.dependsOnVariations()).isEqualTo(DecoratorBarriers.END_OF_TIME_MACHINE);
  }

  @Test
  public void depends_upon_metrics() {
    when(qualityGate.conditions()).thenReturn(ImmutableList.of(new ResolvedCondition(null, CoreMetrics.CLASSES)));
    assertThat(verifier.dependsUponMetrics()).containsOnly(CoreMetrics.CLASSES);
  }

  @Test
  public void ok_when_no_alerts() {
    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "20"),
      mockCondition(CoreMetrics.COVERAGE, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "35.0"));
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(hasLevel(measureClasses, Metric.Level.OK)));
    verify(context).saveMeasure(argThat(hasLevel(measureCoverage, Metric.Level.OK)));
    verify(context).saveMeasure(argThat(new IsMeasure(CoreMetrics.ALERT_STATUS, Metric.Level.OK.toString())));
    verify(context).saveMeasure(argThat(new IsMeasure(CoreMetrics.QUALITY_GATE_DETAILS, "{\"level\":\"OK\","
      + "\"conditions\":"
      + "["
      + "{\"metric\":\"classes\",\"op\":\"GT\",\"warning\":\"20\",\"actual\":\"20.0\",\"level\":\"OK\"},"
      + "{\"metric\":\"coverage\",\"op\":\"GT\",\"warning\":\"35.0\",\"actual\":\"35.0\",\"level\":\"OK\"}"
      + "]"
      + "}")));
  }

  @Test
  public void check_root_modules_only() {
    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "20"),
      mockCondition(CoreMetrics.COVERAGE, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "35.0"));
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(File.create("src/Foo.php"), context);

    verify(context, never()).saveMeasure(any(Measure.class));
  }

  @Test
  public void generate_warnings() {
    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "100"),
      mockCondition(CoreMetrics.COVERAGE, QualityGateConditionDto.OPERATOR_LESS_THAN, null, "95.0")); // generates warning because coverage
                                                                                                      // 35% < 95%
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.WARN, null)));

    verify(context).saveMeasure(argThat(hasLevel(measureClasses, Metric.Level.OK)));
    verify(context).saveMeasure(argThat(hasLevel(measureCoverage, Metric.Level.WARN)));

  }

  @Test
  public void globalStatusShouldBeErrorIfWarningsAndErrors() {
    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_LESS_THAN, null, "100"), // generates warning because classes 20 <
                                                                                                   // 100
      mockCondition(CoreMetrics.COVERAGE, QualityGateConditionDto.OPERATOR_LESS_THAN, "50.0", "80.0")); // generates error because coverage
                                                                                                        // 35% < 50%
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.ERROR, null)));

    verify(context).saveMeasure(argThat(hasLevel(measureClasses, Metric.Level.WARN)));
    verify(context).saveMeasure(argThat(hasLevel(measureCoverage, Metric.Level.ERROR)));
  }

  @Test
  public void globalLabelShouldAggregateAllLabels() {
    when(i18n.message(any(Locale.class), eq("metric.classes.name"), anyString())).thenReturn("Classes");
    when(i18n.message(any(Locale.class), eq("metric.coverage.name"), anyString())).thenReturn("Coverages");
    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_LESS_THAN, null, "10000"), // there are 20 classes, error
                                                                                                     // threshold is higher => alert
      mockCondition(CoreMetrics.COVERAGE, QualityGateConditionDto.OPERATOR_LESS_THAN, "50.0", "80.0"));// coverage is 35%, warning threshold
                                                                                                       // is higher => alert
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.ERROR, "Classes < 10000, Coverages < 50.0")));
  }

  @Test
  public void alertLabelUsesL10nMetricName() {
    Metric metric = new Metric.Builder("rating", "Rating", Metric.ValueType.INT).create();

    // metric name is declared in l10n bundle
    when(i18n.message(any(Locale.class), eq("metric.rating.name"), anyString())).thenReturn("THE RATING");

    when(context.getMeasure(metric)).thenReturn(new Measure(metric, 4d));
    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(mockCondition(metric, QualityGateConditionDto.OPERATOR_LESS_THAN, "10", null));
    when(qualityGate.conditions()).thenReturn(conditions);
    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.ERROR, "THE RATING < 10")));
  }

  @Test
  public void alertLabelUsesMetricNameIfMissingL10nBundle() {
    // the third argument is Metric#getName()
    when(i18n.message(any(Locale.class), eq("metric.classes.name"), eq("Classes"))).thenReturn("Classes");
    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      // there are 20 classes, error threshold is higher => alert
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_LESS_THAN, "10000", null)
      );
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.ERROR, "Classes < 10000")));
  }

  @Test
  public void shouldBeOkIfPeriodVariationIsEnough() {
    measureClasses.setVariation1(0d);
    measureCoverage.setVariation2(50d);
    measureComplexity.setVariation3(2d);

    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "10", 1), // ok because no variation
      mockCondition(CoreMetrics.COVERAGE, QualityGateConditionDto.OPERATOR_LESS_THAN, null, "40.0", 2), // ok because coverage increases of
                                                                                                        // 50%, which is more
      // than 40%
      mockCondition(CoreMetrics.COMPLEXITY, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "5", 3) // ok because complexity increases
                                                                                                         // of 2, which is less
      // than 5
      );
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.OK, null)));

    verify(context).saveMeasure(argThat(hasLevel(measureClasses, Metric.Level.OK)));
    verify(context).saveMeasure(argThat(hasLevel(measureCoverage, Metric.Level.OK)));
    verify(context).saveMeasure(argThat(hasLevel(measureComplexity, Metric.Level.OK)));
  }

  @Test
  public void shouldGenerateWarningIfPeriodVariationIsNotEnough() {
    measureClasses.setVariation1(40d);
    measureCoverage.setVariation2(5d);
    measureComplexity.setVariation3(70d);

    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "30", 1), // generates warning because classes
                                                                                                        // increases of 40,
      // which is greater than 30
      mockCondition(CoreMetrics.COVERAGE, QualityGateConditionDto.OPERATOR_LESS_THAN, null, "10.0", 2), // generates warning because
                                                                                                        // coverage increases of 5%,
      // which is smaller than 10%
      mockCondition(CoreMetrics.COMPLEXITY, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "60", 3) // generates warning because
                                                                                                          // complexity increases of
      // 70, which is smaller than 60
      );
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.WARN, null)));

    verify(context).saveMeasure(argThat(hasLevel(measureClasses, Metric.Level.WARN)));
    verify(context).saveMeasure(argThat(hasLevel(measureCoverage, Metric.Level.WARN)));
    verify(context).saveMeasure(argThat(hasLevel(measureComplexity, Metric.Level.WARN)));
  }

  @Test
  public void shouldBeOkIfVariationIsNull() {
    measureClasses.setVariation1(null);

    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "10", 1));
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.OK, null)));
    verify(context).saveMeasure(argThat(hasLevel(measureClasses, Metric.Level.OK)));
  }

  @Test
  public void shouldVariationPeriodValueCouldBeUsedForRatingMetric() {
    Metric ratingMetric = new Metric.Builder("key_rating_metric", "Rating metric", Metric.ValueType.RATING).create();
    Measure measureRatingMetric = new Measure(ratingMetric, 150d);
    measureRatingMetric.setVariation1(50d);
    when(context.getMeasure(ratingMetric)).thenReturn(measureRatingMetric);

    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(ratingMetric, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "100", 1)
      );
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.OK, null)));
    verify(context).saveMeasure(argThat(hasLevel(measureRatingMetric, Metric.Level.OK)));
  }

  @Test
  public void shouldAllowVariationPeriodOnAllPeriods() {
    measureClasses.setVariation4(40d);

    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "30", 4)
      );
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.WARN, null)));
    verify(context).saveMeasure(argThat(hasLevel(measureClasses, Metric.Level.WARN)));
  }

  @Test(expected = NotImplementedException.class)
  public void shouldNotAllowPeriodVariationAlertOnStringMetric() {
    Measure measure = new Measure(CoreMetrics.NCLOC_LANGUAGE_DISTRIBUTION, 100d);
    measure.setVariation1(50d);
    when(context.getMeasure(CoreMetrics.NCLOC_LANGUAGE_DISTRIBUTION)).thenReturn(measure);

    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.NCLOC_LANGUAGE_DISTRIBUTION, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "30", 1)
      );
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);
  }

  @Test
  @Ignore("Disabled because snapshot is no more created by the batch")
  public void shouldLabelAlertContainsPeriod() {
    measureClasses.setVariation1(40d);

    when(i18n.message(any(Locale.class), eq("metric.classes.name"), anyString())).thenReturn("Classes");
    when(periods.label(snapshot, 1)).thenReturn("since someday");

    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(CoreMetrics.CLASSES, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "30", 1) // generates warning because classes
                                                                                                       // increases of 40,
      // which is greater than 30
      );
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.WARN, "Classes variation > 30 since someday")));
  }

  @Test
  @Ignore("Disabled because snapshot is no more created by the batch")
  public void shouldLabelAlertForNewMetricDoNotContainsVariationWord() {
    Metric newMetric = new Metric.Builder("new_metric_key", "New Metric", Metric.ValueType.INT).create();
    Measure measure = new Measure(newMetric, 15d);
    measure.setVariation1(50d);
    when(context.getMeasure(newMetric)).thenReturn(measure);
    measureClasses.setVariation1(40d);

    when(i18n.message(any(Locale.class), eq("metric.new_metric_key.name"), anyString())).thenReturn("New Measure");
    when(periods.label(snapshot, 1)).thenReturn("since someday");

    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(
      mockCondition(newMetric, QualityGateConditionDto.OPERATOR_GREATER_THAN, null, "30", 1) // generates warning because classes increases
                                                                                             // of 40, which is
      // greater than 30
      );
    when(qualityGate.conditions()).thenReturn(conditions);

    verifier.decorate(project, context);

    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.WARN, "New Measure > 30 since someday")));
  }

  @Test
  public void alert_on_work_duration() {
    Metric metric = new Metric.Builder("tech_debt", "Debt", Metric.ValueType.WORK_DUR).create();

    // metric name is declared in l10n bundle
    when(i18n.message(any(Locale.class), eq("metric.tech_debt.name"), anyString())).thenReturn("The Debt");
    when(durations.format(any(Locale.class), eq(Duration.create(3600L)), eq(Durations.DurationFormat.SHORT))).thenReturn("1h");

    when(context.getMeasure(metric)).thenReturn(new Measure(metric, 7200d));
    ArrayList<ResolvedCondition> conditions = Lists.newArrayList(mockCondition(metric, QualityGateConditionDto.OPERATOR_GREATER_THAN, "3600", null));
    when(qualityGate.conditions()).thenReturn(conditions);
    verifier.decorate(project, context);

    // First call to saveMeasure is for the update of debt
    verify(context).saveMeasure(argThat(matchesMetric(metric, Level.ERROR, "The Debt > 1h")));
    verify(context).saveMeasure(argThat(matchesMetric(CoreMetrics.ALERT_STATUS, Metric.Level.ERROR, "The Debt > 1h")));
    verify(context).saveMeasure(argThat(new IsMeasure(CoreMetrics.QUALITY_GATE_DETAILS, "{\"level\":\"ERROR\","
      + "\"conditions\":"
      + "["
      + "{\"metric\":\"tech_debt\",\"op\":\"GT\",\"error\":\"3600\",\"actual\":\"7200.0\",\"level\":\"ERROR\"}"
      + "]"
      + "}")));
  }

  private ArgumentMatcher<Measure> matchesMetric(final Metric metric, final Metric.Level alertStatus, final String alertText) {
    return new ArgumentMatcher<Measure>() {
      @Override
      public boolean matches(Object arg) {
        boolean result = ((Measure) arg).getMetric().equals(metric) && ((Measure) arg).getAlertStatus() == alertStatus;
        if (result && alertText != null) {
          result = alertText.equals(((Measure) arg).getAlertText());
        }
        return result;
      }
    };
  }

  private ArgumentMatcher<Measure> hasLevel(final Measure measure, final Metric.Level alertStatus) {
    return new ArgumentMatcher<Measure>() {
      @Override
      public boolean matches(Object arg) {
        return arg == measure && ((Measure) arg).getAlertStatus().equals(alertStatus);
      }
    };
  }

  private ResolvedCondition mockCondition(Metric metric, String operator, String error, String warning) {
    return mockCondition(metric, operator, error, warning, null);
  }

  private ResolvedCondition mockCondition(Metric metric, String operator, String error, String warning, Integer period) {
    ResolvedCondition cond = mock(ResolvedCondition.class);
    when(cond.metric()).thenReturn(metric);
    when(cond.metricKey()).thenReturn(metric.getKey());
    when(cond.operator()).thenReturn(operator);
    when(cond.warningThreshold()).thenReturn(warning);
    when(cond.errorThreshold()).thenReturn(error);
    when(cond.period()).thenReturn(period);
    return cond;
  }

}


File: sonar-core/src/main/java/org/sonar/core/component/db/SnapshotMapper.java
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

package org.sonar.core.component.db;

import java.util.List;
import javax.annotation.CheckForNull;
import org.apache.ibatis.annotations.Param;
import org.sonar.core.component.SnapshotDto;
import org.sonar.core.component.SnapshotQuery;

public interface SnapshotMapper {

  @CheckForNull
  SnapshotDto selectByKey(long id);

  void insert(SnapshotDto snapshot);

  @CheckForNull
  SnapshotDto selectLastSnapshot(Long resourceId);

  List<SnapshotDto> selectSnapshotsByQuery(@Param("query") SnapshotQuery query);

  List<SnapshotDto> selectPreviousVersionSnapshots(@Param(value = "componentId") Long componentId, @Param(value = "lastVersion") String lastVersion);

  List<SnapshotDto> selectSnapshotAndChildrenOfScope(@Param(value = "snapshot") Long resourceId, @Param(value = "scope") String scope);

  int updateSnapshotAndChildrenLastFlagAndStatus(@Param(value = "root") Long rootId, @Param(value = "pathRootId") Long pathRootId,
    @Param(value = "path") String path, @Param(value = "isLast") boolean isLast, @Param(value = "status") String status);

  int updateSnapshotAndChildrenLastFlag(@Param(value = "root") Long rootId, @Param(value = "pathRootId") Long pathRootId,
    @Param(value = "path") String path, @Param(value = "isLast") boolean isLast);
}
