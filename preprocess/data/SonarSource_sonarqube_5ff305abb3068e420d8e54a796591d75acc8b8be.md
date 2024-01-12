Refactoring Types: ['Extract Interface']
/org/sonar/server/platform/TempFolderProvider.java
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
package org.sonar.server.platform;

import org.apache.commons.io.FileUtils;
import org.picocontainer.injectors.ProviderAdapter;
import org.sonar.api.platform.ServerFileSystem;
import org.sonar.api.utils.TempFolder;
import org.sonar.api.utils.internal.DefaultTempFolder;

import java.io.File;
import java.io.IOException;

public class TempFolderProvider extends ProviderAdapter {

  private TempFolder tempFolder;

  public TempFolder provide(ServerFileSystem fs) {
    if (tempFolder == null) {
      File tempDir = new File(fs.getTempDir(), "tmp");
      try {
        FileUtils.forceMkdir(tempDir);
      } catch (IOException e) {
        throw new IllegalStateException("Unable to create temp directory " + tempDir, e);
      }
      tempFolder = new DefaultTempFolder(tempDir);
    }
    return tempFolder;
  }

}


File: sonar-plugin-api/src/main/java/org/sonar/api/CoreProperties.java
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
package org.sonar.api;

import org.sonar.api.batch.AnalysisMode;
import org.sonar.api.batch.fs.FileSystem;

/**
 * Non-exhaustive list of constants of core properties.
 *
 * @since 1.11
 */
public interface CoreProperties {

  /**
   * @since 3.0
   */
  String ENCRYPTION_SECRET_KEY_PATH = "sonar.secretKeyPath";

  /**
   * @since 2.11
   */
  String CATEGORY_GENERAL = "general";

  /**
   * @since 4.0
   */
  String SUBCATEGORY_DATABASE_CLEANER = "databaseCleaner";

  /**
   * @since 4.0
   */
  String SUBCATEGORY_DUPLICATIONS = "duplications";

  /**
   * @since 4.0
   */
  String SUBCATEGORY_DIFFERENTIAL_VIEWS = "differentialViews";

  /**
   * @since 5.1
   */
  String SUBCATEGORY_LOOKNFEEL = "looknfeel";

  /**
   * @since 5.1
   */
  String SUBCATEGORY_ISSUES = "issues";

  /**
   * @since 4.0
   */
  String SUBCATEGORY_L10N = "localization";

  /**
   * @since 2.11
   */
  String CATEGORY_CODE_COVERAGE = "codeCoverage";

  /**
   * @see #SUBCATEGORY_DUPLICATIONS
   * @since 2.11
   * @deprecated since 4.0. See http://jira.sonarsource.com/browse/SONAR-4660. Do not forget to remove the properties from core bundles
   */
  @Deprecated
  String CATEGORY_DUPLICATIONS = "duplications";

  /**
   * @since 2.11
   */
  String CATEGORY_SECURITY = "security";

  /**
   * @see #SUBCATEGORY_L10N
   * @since 2.11
   * @deprecated since 4.0. See http://jira.sonarsource.com/browse/SONAR-4660. Do not forget to remove the properties from core bundles
   */
  @Deprecated
  String CATEGORY_L10N = "localization";

  /**
   * @since 2.11
   */
  String CATEGORY_JAVA = "java";

  /**
   * @see #SUBCATEGORY_DIFFERENTIAL_VIEWS
   * @since 2.11
   * @deprecated since 4.0. See http://jira.sonarsource.com/browse/SONAR-4660. Do not forget to remove the properties from core bundles
   */
  @Deprecated
  String CATEGORY_DIFFERENTIAL_VIEWS = "differentialViews";

  /**
   * @since 3.3
   */
  String CATEGORY_EXCLUSIONS = "exclusions";

  /**
   * @since 4.0
   */
  String SUBCATEGORY_FILES_EXCLUSIONS = "files";

  /**
   * @since 4.0
   */
  String SUBCATEGORY_DUPLICATIONS_EXCLUSIONS = "duplications";

  /**
   * @since 4.0
   */
  String SUBCATEGORY_COVERAGE_EXCLUSIONS = "coverage";

  /**
   * @since 3.7
   */
  String CATEGORY_LICENSES = "licenses";

  /**
   * @since 4.0
   */
  String CATEGORY_TECHNICAL_DEBT = "technicalDebt";

  /* Global settings */
  String SONAR_HOME = "SONAR_HOME";
  String PROJECT_BRANCH_PROPERTY = "sonar.branch";
  String PROJECT_VERSION_PROPERTY = "sonar.projectVersion";

  /**
   * @since 2.6
   */
  String PROJECT_KEY_PROPERTY = "sonar.projectKey";

  /**
   * @since 2.6
   */
  String PROJECT_NAME_PROPERTY = "sonar.projectName";

  /**
   * @since 2.6
   */
  String PROJECT_DESCRIPTION_PROPERTY = "sonar.projectDescription";

  /**
   * To determine value of this property use {@link FileSystem#encoding()}.
   *
   * @since 2.6
   */
  String ENCODING_PROPERTY = "sonar.sourceEncoding";

  /**
   * Value format is yyyy-MM-dd
   */
  String PROJECT_DATE_PROPERTY = "sonar.projectDate";

  /**
   * @deprecated since 4.2 projects are now multi-language
   */
  @Deprecated
  String PROJECT_LANGUAGE_PROPERTY = "sonar.language";

  /**
   * @deprecated since 4.3. See http://jira.sonarsource.com/browse/SONAR-5185
   */
  @Deprecated
  String DYNAMIC_ANALYSIS_PROPERTY = "sonar.dynamicAnalysis";

  /* Exclusions */
  String PROJECT_INCLUSIONS_PROPERTY = "sonar.inclusions";
  String PROJECT_EXCLUSIONS_PROPERTY = "sonar.exclusions";

  /* Coverage exclusions */
  String PROJECT_COVERAGE_EXCLUSIONS_PROPERTY = "sonar.coverage.exclusions";

  /**
   * @since 3.3
   */
  String PROJECT_TEST_INCLUSIONS_PROPERTY = "sonar.test.inclusions";
  String PROJECT_TEST_EXCLUSIONS_PROPERTY = "sonar.test.exclusions";
  String GLOBAL_EXCLUSIONS_PROPERTY = "sonar.global.exclusions";
  String GLOBAL_TEST_EXCLUSIONS_PROPERTY = "sonar.global.test.exclusions";

  /* Sonar Core */

  /**
   * @deprecated since 4.1. See http://jira.sonarsource.com/browse/SONAR-4875
   */
  @Deprecated
  String CORE_VIOLATION_LOCALE_PROPERTY = "sonar.violationLocale";

  String CORE_VIOLATION_LOCALE_DEFAULT_VALUE = "en";

  /**
   * @deprecated since 4.3. See http://jira.sonarsource.com/browse/SONAR-5109
   */
  @Deprecated
  String CORE_SKIPPED_MODULES_PROPERTY = "sonar.skippedModules";

  /**
   * @since 4.0
   * @deprecated since 4.3. See http://jira.sonarsource.com/browse/SONAR-5109
   */
  @Deprecated
  String CORE_INCLUDED_MODULES_PROPERTY = "sonar.includedModules";

  String CORE_FORCE_AUTHENTICATION_PROPERTY = "sonar.forceAuthentication";
  boolean CORE_FORCE_AUTHENTICATION_DEFAULT_VALUE = false;
  String CORE_ALLOW_USERS_TO_SIGNUP_PROPERTY = "sonar.allowUsersToSignUp";
  String CORE_DEFAULT_GROUP = "sonar.defaultGroup";
  String CORE_DEFAULT_GROUP_DEFAULT_VALUE = "sonar-users";
  boolean CORE_ALLOW_USERS_TO_SIGNUP_DEAULT_VALUE = false;

  /**
   * @deprecated since 2.14. See http://jira.sonarsource.com/browse/SONAR-3153. Replaced by {@link #CORE_AUTHENTICATOR_REALM}.
   */
  @Deprecated
  String CORE_AUTHENTICATOR_CLASS = "sonar.authenticator.class";

  /**
   * @since 2.14
   */
  String CORE_AUTHENTICATOR_REALM = "sonar.security.realm";

  String CORE_AUTHENTICATOR_IGNORE_STARTUP_FAILURE = "sonar.authenticator.ignoreStartupFailure";
  String CORE_AUTHENTICATOR_CREATE_USERS = "sonar.authenticator.createUsers";

  /**
   * @since 3.6
   */
  String CORE_AUTHENTICATOR_UPDATE_USER_ATTRIBUTES = "sonar.security.updateUserAttributes";

  String SERVER_VERSION = "sonar.core.version";
  String SERVER_ID = "sonar.core.id";

  // format is yyyy-MM-dd'T'HH:mm:ssZ
  String SERVER_STARTTIME = "sonar.core.startTime";

  /**
   * @since 2.10
   */
  String SERVER_BASE_URL = "sonar.core.serverBaseURL";

  /**
   * @see #SERVER_BASE_URL
   * @since 2.10
   */
  String SERVER_BASE_URL_DEFAULT_VALUE = "http://localhost:9000";

  /* CPD */
  String CPD_PLUGIN = "cpd";

  /**
   * @deprecated in 3.1
   */
  @Deprecated
  String CPD_MINIMUM_TOKENS_PROPERTY = "sonar.cpd.minimumTokens";

  /**
   * @deprecated in 5.0
   * @see <a href="https://jira.sonarsource.com/browse/SONAR-5339">SONAR-5339</a>
   */
  @Deprecated
  String CPD_SKIP_PROPERTY = "sonar.cpd.skip";

  /**
   * @since 2.11
   */
  String CPD_CROSS_PROJECT = "sonar.cpd.cross_project";

  /**
   * @see #CPD_CROSS_PROJECT
   * @since 2.11
   */
  boolean CPD_CROSS_RPOJECT_DEFAULT_VALUE = false;

  /**
   * @since 3.5
   */
  String CPD_EXCLUSIONS = "sonar.cpd.exclusions";

  /* Design */

  /**
   * Indicates whether Java bytecode analysis should be skipped.
   *
   * @since 2.0
   */
  String DESIGN_SKIP_DESIGN_PROPERTY = "sonar.skipDesign";
  boolean DESIGN_SKIP_DESIGN_DEFAULT_VALUE = false;

  /**
   * Indicates whether Package Design Analysis should be skipped.
   *
   * @since 2.9
   */
  String DESIGN_SKIP_PACKAGE_DESIGN_PROPERTY = "sonar.skipPackageDesign";
  boolean DESIGN_SKIP_PACKAGE_DESIGN_DEFAULT_VALUE = false;

  /* Google Analytics */
  String GOOGLE_ANALYTICS_PLUGIN = "google-analytics";
  String GOOGLE_ANALYTICS_ACCOUNT_PROPERTY = "sonar.google-analytics.account";

  /* Time machine periods */
  String TIMEMACHINE_PERIOD_PREFIX = "sonar.timemachine.period";
  String TIMEMACHINE_MODE_PREVIOUS_ANALYSIS = "previous_analysis";
  String TIMEMACHINE_MODE_DATE = "date";
  String TIMEMACHINE_MODE_VERSION = "version";
  String TIMEMACHINE_MODE_DAYS = "days";
  String TIMEMACHINE_MODE_PREVIOUS_VERSION = "previous_version";
  String TIMEMACHINE_DEFAULT_PERIOD_1 = TIMEMACHINE_MODE_PREVIOUS_ANALYSIS;
  String TIMEMACHINE_DEFAULT_PERIOD_2 = "30";
  String TIMEMACHINE_DEFAULT_PERIOD_3 = TIMEMACHINE_MODE_PREVIOUS_VERSION;
  String TIMEMACHINE_DEFAULT_PERIOD_4 = "";
  String TIMEMACHINE_DEFAULT_PERIOD_5 = "";

  /**
   * @since 2.11
   */
  String ORGANISATION = "sonar.organisation";

  /**
   * @since 2.11
   */
  String PERMANENT_SERVER_ID = "sonar.server_id";

  /**
   * @since 2.11
   */
  String SERVER_ID_IP_ADDRESS = "sonar.server_id.ip_address";

  /**
   * @since 3.3
   */
  String LINKS_HOME_PAGE = "sonar.links.homepage";

  /**
   * @since 3.3
   */
  String LINKS_CI = "sonar.links.ci";

  /**
   * @since 3.3
   */
  String LINKS_ISSUE_TRACKER = "sonar.links.issue";

  /**
   * @since 3.3
   */
  String LINKS_SOURCES = "sonar.links.scm";

  /**
   * @since 3.3
   */
  String LINKS_SOURCES_DEV = "sonar.links.scm_dev";

  /**
   * @since 3.4
   */
  String LOGIN = "sonar.login";

  /**
   * @since 3.4
   */
  String PASSWORD = "sonar.password";

  /**
   * @since 3.4
   * @deprecated since 5.1 use {@link AnalysisMode} to check existing mode
   */
  @Deprecated
  String DRY_RUN = "sonar.dryRun";

  /**
   * @since 3.5
   * @deprecated since 5.2 no more task concept on batch side
   */
  @Deprecated
  String TASK = "sonar.task";

  /**
   * @since 3.6
   * @deprecated since 5.2 no more task concept on batch side
   */
  @Deprecated
  String SCAN_TASK = "scan";

  /**
   * @since 3.6
   */
  String PROFILING_LOG_PROPERTY = "sonar.showProfiling";

  /**
   * @deprecated replaced in v3.4 by properties specific to languages, for example sonar.java.coveragePlugin
   * See http://jira.sonarsource.com/browse/SONARJAVA-39 for more details.
   */
  @Deprecated
  String CORE_COVERAGE_PLUGIN_PROPERTY = "sonar.core.codeCoveragePlugin";

  /**
   * @since 3.7
   * @deprecated in 4.0 no more used
   */
  @Deprecated
  String DRY_RUN_READ_TIMEOUT_SEC = "sonar.dryRun.readTimeout";

  /**
   * @since 4.0
   * @deprecated in 5.1 no more used
   */
  String PREVIEW_READ_TIMEOUT_SEC = "sonar.preview.readTimeout";

  /**
   * @since 4.0
   */
  String CORE_PREVENT_AUTOMATIC_PROJECT_CREATION = "sonar.preventAutoProjectCreation";

  /**
   * @since 4.0
   */
  String ANALYSIS_MODE = "sonar.analysis.mode";

  /**
   * @since 4.0
   */
  String ANALYSIS_MODE_ANALYSIS = "analysis";

  /**
   * @since 4.0
   */
  String ANALYSIS_MODE_PREVIEW = "preview";

  /**
   * @since 4.0
   */
  String ANALYSIS_MODE_INCREMENTAL = "incremental";

  /**
   * @since 4.0
   */
  String PREVIEW_INCLUDE_PLUGINS = "sonar.preview.includePlugins";
  String PREVIEW_INCLUDE_PLUGINS_DEFAULT_VALUE = "";

  /**
   * @since 4.0
   */
  String PREVIEW_EXCLUDE_PLUGINS = "sonar.preview.excludePlugins";
  String PREVIEW_EXCLUDE_PLUGINS_DEFAULT_VALUE = "buildstability,devcockpit,pdfreport,report,views,jira,buildbreaker";

  /**
   * @since 4.0
   */
  String WORKING_DIRECTORY = "sonar.working.directory";
  String WORKING_DIRECTORY_DEFAULT_VALUE = ".sonar";

  /**
   * @since 3.4
   * @deprecated in 4.0 replaced by {@link CoreProperties#PREVIEW_INCLUDE_PLUGINS}
   */
  @Deprecated
  String DRY_RUN_INCLUDE_PLUGINS = "sonar.dryRun.includePlugins";
  /**
   * @since 3.4
   * @deprecated in 4.0 replaced by {@link CoreProperties#PREVIEW_INCLUDE_PLUGINS_DEFAULT_VALUE}
   */
  @Deprecated
  String DRY_RUN_INCLUDE_PLUGINS_DEFAULT_VALUE = PREVIEW_INCLUDE_PLUGINS_DEFAULT_VALUE;

  /**
   * @since 3.4
   * @deprecated in 4.0 replaced by {@link CoreProperties#PREVIEW_EXCLUDE_PLUGINS}
   */
  @Deprecated
  String DRY_RUN_EXCLUDE_PLUGINS = "sonar.dryRun.excludePlugins";
  /**
   * @since 3.4
   * @deprecated in 4.0 replaced by {@link CoreProperties#PREVIEW_EXCLUDE_PLUGINS_DEFAULT_VALUE}
   */
  @Deprecated
  String DRY_RUN_EXCLUDE_PLUGINS_DEFAULT_VALUE = PREVIEW_EXCLUDE_PLUGINS_DEFAULT_VALUE;

  /**
   * @since 4.2
   */
  String CORE_AUTHENTICATOR_LOCAL_USERS = "sonar.security.localUsers";

  /**
   * @since 4.0
   */
  String HOURS_IN_DAY = "sonar.technicalDebt.hoursInDay";

  /**
   * @since 4.5
   */
  String SIZE_METRIC = "sonar.technicalDebt.sizeMetric";

  /**
   * @since 4.5
   */
  String DEVELOPMENT_COST = "sonar.technicalDebt.developmentCost";

  /**
   * @since 4.5
   */
  String DEVELOPMENT_COST_DEF_VALUE = "30";

  /**
   * @since 4.5
   */
  String RATING_GRID = "sonar.technicalDebt.ratingGrid";

  /**
   * @since 4.5
   */
  String RATING_GRID_DEF_VALUES = "0.1,0.2,0.5,1";

  /**
   * @since 4.5
   */
  String LANGUAGE_SPECIFIC_PARAMETERS = "languageSpecificParameters";

  /**
   * @since 4.5
   */
  String LANGUAGE_SPECIFIC_PARAMETERS_LANGUAGE_KEY = "language";

  /**
   * @since 4.5
   */
  String LANGUAGE_SPECIFIC_PARAMETERS_MAN_DAYS_KEY = "man_days";

  /**
   * @since 4.5
   */
  String LANGUAGE_SPECIFIC_PARAMETERS_SIZE_METRIC_KEY = "size_metric";

  /**
   * @since 5.0
   */
  String CATEGORY_SCM = "scm";

  /**
   * @since 5.0
   */
  String SCM_DISABLED_KEY = "sonar.scm.disabled";

  /**
   * @since 5.0
   */
  String SCM_PROVIDER_KEY = "sonar.scm.provider";

  /**
   * @since 5.1
   */
  String IMPORT_UNKNOWN_FILES_KEY = "sonar.import_unknown_files";

  /**
   * @since 5.1
   */
  String DEFAULT_ISSUE_ASSIGNEE = "sonar.issues.defaultAssigneeLogin";

}


File: sonar-plugin-api/src/main/java/org/sonar/api/utils/TempFolder.java
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
package org.sonar.api.utils;

import org.sonar.api.batch.BatchSide;
import org.sonar.api.server.ServerSide;

import javax.annotation.Nullable;

import java.io.File;

/**
 * Use this component to deal with temp files/folders. Root location of temp files/folders
 * depends on situation:
 * <ul>
 * <li>${SONAR_HOME}/temp on server side</li>
 * <li>Working directory on batch side (see sonar.working.directory)</li>
 * </ul>
 * @since 4.0
 *
 */
@BatchSide
@ServerSide
public interface TempFolder {

  /**
   * Create a directory in temp folder with a random unique name.
   */
  File newDir();

  /**
   * Create a directory in temp folder using provided name.
   */
  File newDir(String name);

  File newFile();

  File newFile(@Nullable String prefix, @Nullable String suffix);

}


File: sonar-plugin-api/src/main/java/org/sonar/api/utils/internal/DefaultTempFolder.java
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
package org.sonar.api.utils.internal;

import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.sonar.api.utils.TempFolder;

import javax.annotation.Nullable;

import java.io.File;
import java.io.IOException;
import java.text.MessageFormat;

public class DefaultTempFolder implements TempFolder {

  /** Maximum loop count when creating temp directories. */
  private static final int TEMP_DIR_ATTEMPTS = 10000;

  private final File tempDir;

  public DefaultTempFolder(File tempDir) {
    this.tempDir = tempDir;
  }

  @Override
  public File newDir() {
    return createTempDir(tempDir, "");
  }

  /**
   * Copied from guava waiting for JDK 7 Files#createTempDirectory
   */
  private static File createTempDir(File baseDir, String prefix) {
    String baseName = prefix + System.currentTimeMillis() + "-";

    for (int counter = 0; counter < TEMP_DIR_ATTEMPTS; counter++) {
      File tempDir = new File(baseDir, baseName + counter);
      if (tempDir.mkdir()) {
        return tempDir;
      }
    }
    throw new IllegalStateException(MessageFormat.format("Failed to create directory within {0} attempts (tried {1} to {2})", TEMP_DIR_ATTEMPTS, baseName + 0, baseName
      + (TEMP_DIR_ATTEMPTS - 1)));
  }

  @Override
  public File newDir(String name) {
    File dir = new File(tempDir, name);
    try {
      FileUtils.forceMkdir(dir);
    } catch (IOException e) {
      throw new IllegalStateException("Failed to create temp directory in " + dir, e);
    }
    return dir;
  }

  @Override
  public File newFile() {
    return newFile(null, null);
  }

  @Override
  public File newFile(@Nullable String prefix, @Nullable String suffix) {
    return createTempFile(tempDir, prefix, suffix);
  }

  /**
   * Inspired by guava waiting for JDK 7 Files#createTempFile
   */
  private static File createTempFile(File baseDir, String prefix, String suffix) {
    String baseName = StringUtils.defaultIfEmpty(prefix, "") + System.currentTimeMillis() + "-";

    try {
      for (int counter = 0; counter < TEMP_DIR_ATTEMPTS; counter++) {
        File tempFile = new File(baseDir, baseName + counter + suffix);
        if (tempFile.createNewFile()) {
          return tempFile;
        }
      }
    } catch (IOException e) {
      throw new IllegalStateException("Failed to create temp file", e);
    }
    throw new IllegalStateException(MessageFormat.format("Failed to create temp file within {0} attempts (tried {1} to {2})", TEMP_DIR_ATTEMPTS, baseName + 0 + suffix, baseName
      + (TEMP_DIR_ATTEMPTS - 1) + suffix));
  }

  public void clean() {
    FileUtils.deleteQuietly(tempDir);
  }

}


File: sonar-plugin-api/src/main/java/org/sonar/api/utils/internal/JUnitTempFolder.java
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
package org.sonar.api.utils.internal;

import org.apache.commons.lang.StringUtils;
import org.junit.rules.ExternalResource;
import org.junit.rules.TemporaryFolder;
import org.junit.runner.Description;
import org.junit.runners.model.Statement;
import org.sonar.api.utils.TempFolder;

import javax.annotation.Nullable;

import java.io.File;
import java.io.IOException;

/**
 * Implementation of {@link org.sonar.api.utils.TempFolder} to be used
 * only in JUnit tests. It wraps {@link org.junit.rules.TemporaryFolder}.
 * <p/>
 * Example:
 * <pre>
 * public class MyTest {
 *   &#064;@org.junit.Rule
 *   public JUnitTempFolder temp = new JUnitTempFolder();
 *
 *   &#064;@org.junit.Test
 *   public void myTest() throws Exception {
 *     File dir = temp.newDir();
 *     // ...
 *   }
 * }
 * </pre>
 *
 * @since 5.1
 */
public class JUnitTempFolder extends ExternalResource implements TempFolder {

  private final TemporaryFolder junit = new TemporaryFolder();

  @Override
  public Statement apply(Statement base, Description description) {
    return junit.apply(base, description);
  }

  @Override
  protected void before() throws Throwable {
    junit.create();
  }

  @Override
  protected void after() {
    junit.delete();
  }

  @Override
  public File newDir() {
    try {
      return junit.newFolder();
    } catch (IOException e) {
      throw new IllegalStateException("Fail to create temp dir", e);
    }
  }

  @Override
  public File newDir(String name) {
    try {
      return junit.newFolder(name);
    } catch (IOException e) {
      throw new IllegalStateException("Fail to create temp dir", e);
    }
  }

  @Override
  public File newFile() {
    try {
      return junit.newFile();
    } catch (IOException e) {
      throw new IllegalStateException("Fail to create temp file", e);
    }
  }

  @Override
  public File newFile(@Nullable String prefix, @Nullable String suffix) {
    try {
      return junit.newFile(StringUtils.defaultString(prefix) + "-" + StringUtils.defaultString(suffix));
    } catch (IOException e) {
      throw new IllegalStateException("Fail to create temp file", e);
    }
  }
}
