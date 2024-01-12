Refactoring Types: ['Move Method']
n/java/org/sonar/server/computation/step/PersistComponentsStep.java
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
import java.util.List;
import java.util.Map;
import javax.annotation.Nullable;
import org.apache.commons.io.FilenameUtils;
import org.apache.commons.lang.ObjectUtils;
import org.apache.commons.lang.StringUtils;
import org.sonar.api.resources.Qualifiers;
import org.sonar.api.resources.Scopes;
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

  public PersistComponentsStep(DbClient dbClient, TreeRootHolder treeRootHolder, BatchReportReader reportReader, DbIdsRepository dbIdsRepository) {
    this.dbClient = dbClient;
    this.treeRootHolder = treeRootHolder;
    this.reportReader = reportReader;
    this.dbIdsRepository = dbIdsRepository;
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
      componentDto.setQualifier(getFileQualifier(reportComponent));
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

  private static ComponentDto createComponentDto(BatchReport.Component reportComponent, Component component) {
    String componentKey = component.getKey();
    String componentUuid = component.getUuid();

    ComponentDto componentDto = new ComponentDto();
    componentDto.setUuid(componentUuid);
    componentDto.setKey(componentKey);
    componentDto.setDeprecatedKey(componentKey);
    componentDto.setEnabled(true);
    return componentDto;
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

  private static String getFileQualifier(BatchReport.Component reportComponent) {
    return reportComponent.getIsTest() ? Qualifiers.UNIT_TEST_FILE : Qualifiers.FILE;
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
import org.junit.After;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.experimental.categories.Category;
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

  DbSession session;

  DbClient dbClient;

  long now;

  PersistComponentsStep sut;

  @Before
  public void setup() throws Exception {
    dbTester.truncateTables();
    session = dbTester.myBatis().openSession(false);
    dbClient = new DbClient(dbTester.database(), dbTester.myBatis(), new ComponentDao(), new SnapshotDao());

    dbIdsRepository = new DbIdsRepository();

    now = DATE_FORMAT.parse("2015-06-02").getTime();

    sut = new PersistComponentsStep( dbClient, treeRootHolder, reportReader, dbIdsRepository);
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

    Component file = new DumbComponent(Component.Type.FILE, 4, "DEFG", "MODULE_KEY:src/main/java/dir/Foo.java");
    Component directory = new DumbComponent(Component.Type.DIRECTORY, 3, "CDEF", "MODULE_KEY:src/main/java/dir", file);
    Component module = new DumbComponent(Component.Type.MODULE, 2, "BCDE", "MODULE_KEY", directory);
    Component project = new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY, module);
    treeRootHolder.setRoot(project);

    sut.execute();

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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.DIRECTORY, 2, "CDEF", PROJECT_KEY + ":/",
        new DumbComponent(Component.Type.FILE, 3, "DEFG", PROJECT_KEY + ":pom.xml"))));

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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.DIRECTORY, 2, "CDEF", PROJECT_KEY + ":src/test/java/dir",
        new DumbComponent(Component.Type.FILE, 3, "DEFG", PROJECT_KEY + ":src/test/java/dir/FooTest.java"))));

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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.MODULE, 2, "BCDE", "MODULE_KEY",
        new DumbComponent(Component.Type.DIRECTORY, 3, "CDEF", "MODULE_KEY:src/main/java/dir",
          new DumbComponent(Component.Type.FILE, 4, "DEFG", "MODULE_KEY:src/main/java/dir/Foo.java")))));

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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.MODULE, 2, "BCDE", "MODULE_KEY",
        new DumbComponent(Component.Type.MODULE, 3, "CDEF", "SUB_MODULE_1_KEY",
          new DumbComponent(Component.Type.MODULE, 4, "DEFG", "SUB_MODULE_2_KEY",
            new DumbComponent(Component.Type.DIRECTORY, 5, "EFGH", "SUB_MODULE_2_KEY:src/main/java/dir"))))));

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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.MODULE, 2, "BCDE", "MODULE_A",
        new DumbComponent(Component.Type.MODULE, 3, "DEFG", "SUB_MODULE_A")),
      new DumbComponent(Component.Type.MODULE, 4, "CDEF", "MODULE_B")));

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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.MODULE, 2, "BCDE", "MODULE_KEY",
        new DumbComponent(Component.Type.DIRECTORY, 3, "CDEF", "MODULE_KEY:src/main/java/dir",
          new DumbComponent(Component.Type.FILE, 4, "DEFG", "MODULE_KEY:src/main/java/dir/Foo.java")))));

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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.MODULE, 2, "BCDE", "MODULE_KEY")));
    
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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.MODULE, 2, "BCDE", "MODULE_KEY")));
    
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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.MODULE, 2, "BCDE", "MODULE_KEY")));

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

    treeRootHolder.setRoot(new DumbComponent(Component.Type.PROJECT, 1, "ABCD", PROJECT_KEY,
      new DumbComponent(Component.Type.MODULE, 2, "EDCB", "MODULE_A",
        new DumbComponent(Component.Type.MODULE, 3, "BCDE", "MODULE_B",
          new DumbComponent(Component.Type.DIRECTORY, 4, "CDEF", "MODULE_B:src/main/java/dir",
            new DumbComponent(Component.Type.FILE, 5, "DEFG", "MODULE_B:src/main/java/dir/Foo.java"))))));

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

}
