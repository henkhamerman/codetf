Refactoring Types: ['Extract Method']
hi-runner/src/com/liferay/gradle/plugins/poshi/runner/PoshiRunnerPlugin.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.gradle.plugins.poshi.runner;

import com.liferay.gradle.plugins.poshi.runner.util.GradleUtil;
import com.liferay.gradle.plugins.poshi.runner.util.OSDetector;

import java.io.File;

import java.util.Iterator;
import java.util.Map;
import java.util.Set;

import org.gradle.api.Action;
import org.gradle.api.GradleException;
import org.gradle.api.Plugin;
import org.gradle.api.Project;
import org.gradle.api.Task;
import org.gradle.api.artifacts.Configuration;
import org.gradle.api.artifacts.Dependency;
import org.gradle.api.artifacts.ResolvableDependencies;
import org.gradle.api.file.FileTree;
import org.gradle.api.reporting.DirectoryReport;
import org.gradle.api.tasks.Copy;
import org.gradle.api.tasks.JavaExec;
import org.gradle.api.tasks.testing.Test;
import org.gradle.api.tasks.testing.TestTaskReports;
import org.gradle.api.tasks.testing.logging.TestLoggingContainer;

/**
 * @author Andrea Di Giorgi
 */
public class PoshiRunnerPlugin implements Plugin<Project> {

	public static final String CONFIGURATION_NAME = "poshiRunner";

	public static final String EXPAND_POSHI_RUNNER_TASK_NAME =
		"expandPoshiRunner";

	public static final String RUN_POSHI_TASK_NAME = "runPoshi";

	public static final String VALIDATE_POSHI_TASK_NAME = "validatePoshi";

	public static final String WRITE_POSHI_PROPERTIES_TASK_NAME =
		"writePoshiProperties";

	@Override
	public void apply(Project project) {
		final PoshiRunnerExtension poshiRunnerExtension =
			GradleUtil.addExtension(
				project, "poshiRunner", PoshiRunnerExtension.class);

		addPoshiRunnerConfiguration(project, poshiRunnerExtension);

		addTasksExpandPoshiRunner(project);
		addTasksRunPoshi(project);
		addTasksValidatePoshi(project);
		addTasksWritePoshiProperties(project);

		project.afterEvaluate(
			new Action<Project>() {

				@Override
				public void execute(Project project) {
					configureTasksExpandPoshiRunner(project);
					configureTasksRunPoshi(project, poshiRunnerExtension);
					configureTasksValidatePoshi(project, poshiRunnerExtension);
					configureTasksWritePoshiProperties(
						project, poshiRunnerExtension);
				}

			});
	}

	protected void addPoshiRunnerConfiguration(
		final Project project,
		final PoshiRunnerExtension poshiRunnerExtension) {

		final Configuration configuration = GradleUtil.addConfiguration(
			project, CONFIGURATION_NAME);

		configuration.setDescription(
			"Configures Poshi Runner for this project.");
		configuration.setVisible(false);

		ResolvableDependencies resolvableDependencies =
			configuration.getIncoming();

		resolvableDependencies.beforeResolve(
			new Action<ResolvableDependencies>() {

				@Override
				public void execute(
					ResolvableDependencies resolvableDependencies) {

					Set<Dependency> dependencies =
						configuration.getDependencies();

					if (dependencies.isEmpty()) {
						addPoshiRunnerDependenciesPoshiRunner(
							project, poshiRunnerExtension);
						addPoshiRunnerDependenciesSikuli(
							project, poshiRunnerExtension);
					}
				}

			});
	}

	protected void addPoshiRunnerDependenciesPoshiRunner(
		Project project, PoshiRunnerExtension poshiRunnerExtension) {

		GradleUtil.addDependency(
			project, CONFIGURATION_NAME, "com.liferay",
			"com.liferay.poshi.runner", poshiRunnerExtension.getVersion(),
			null);
	}

	protected void addPoshiRunnerDependenciesSikuli(
		Project project, PoshiRunnerExtension poshiRunnerExtension) {

		String bitMode = OSDetector.getBitmode();

		if (bitMode.equals("32")) {
			bitMode = "x86";
		}
		else {
			bitMode = "x86_64";
		}

		String os = "linux";

		if (OSDetector.isApple()) {
			os = "macosx";
		}
		else if (OSDetector.isWindows()) {
			os = "windows";
		}

		String classifier = os + "-" + bitMode;

		GradleUtil.addDependency(
			project, CONFIGURATION_NAME, "org.bytedeco.javacpp-presets",
			"opencv", poshiRunnerExtension.getOpenCVVersion(), classifier);
	}

	protected void addTasksExpandPoshiRunner(Project project) {
		Copy copy = GradleUtil.addTask(
			project, EXPAND_POSHI_RUNNER_TASK_NAME, Copy.class);

		copy.into(getExpandedPoshiRunnerDir(project));
	}

	protected void addTasksRunPoshi(Project project) {
		Test test = GradleUtil.addTask(
			project, RUN_POSHI_TASK_NAME, Test.class);

		test.dependsOn(EXPAND_POSHI_RUNNER_TASK_NAME);

		test.include("com/liferay/poshi/runner/PoshiRunner.class");

		Configuration configuration = GradleUtil.getConfiguration(
			test.getProject(), CONFIGURATION_NAME);

		test.setClasspath(configuration);
		test.setDescription("Execute tests using Poshi Runner.");
		test.setGroup("verification");
		test.setScanForTestClasses(false);
		test.setTestClassesDir(getExpandedPoshiRunnerDir(project));

		TestLoggingContainer testLoggingContainer = test.getTestLogging();

		testLoggingContainer.setShowStandardStreams(true);

		test.doFirst(
			new Action<Task>() {

				@Override
				public void execute(Task task) {
					Test test = (Test)task;

					Map<String, Object> systemProperties =
						test.getSystemProperties();

					if (!systemProperties.containsKey("test.name")) {
						throw new GradleException(
							"Please set the property poshiTestName.");
					}
				}

		});
	}

	protected void addTasksValidatePoshi(Project project) {
		JavaExec javaExec = GradleUtil.addTask(
			project, VALIDATE_POSHI_TASK_NAME, JavaExec.class);

		Configuration configuration = GradleUtil.getConfiguration(
			project, CONFIGURATION_NAME);

		javaExec.setClasspath(configuration);
		javaExec.setDescription("Validates the Poshi files syntax.");
		javaExec.setGroup("verification");
		javaExec.setMain("com.liferay.poshi.runner.PoshiRunnerValidation");
	}

	protected void addTasksWritePoshiProperties(Project project) {
		JavaExec javaExec = GradleUtil.addTask(
			project, WRITE_POSHI_PROPERTIES_TASK_NAME, JavaExec.class);

		Configuration configuration = GradleUtil.getConfiguration(
			project, CONFIGURATION_NAME);

		javaExec.setClasspath(configuration);
		javaExec.setDescription("Write the Poshi properties files.");
		javaExec.setGroup("verification");
		javaExec.setMain("com.liferay.poshi.runner.PoshiRunnerContext");
	}

	protected void configureTasksExpandPoshiRunner(Project project) {
		Copy copy = (Copy)GradleUtil.getTask(
			project, EXPAND_POSHI_RUNNER_TASK_NAME);

		configureTasksExpandPoshiRunnerFrom(copy);
	}

	protected void configureTasksExpandPoshiRunnerFrom(Copy copy) {
		Project project = copy.getProject();

		Configuration configuration = GradleUtil.getConfiguration(
			project, CONFIGURATION_NAME);

		Iterator<File> iterator = configuration.iterator();

		while (iterator.hasNext()) {
			File file = iterator.next();

			String fileName = file.getName();

			if (fileName.startsWith("com.liferay.poshi.runner-")) {
				FileTree fileTree = project.zipTree(file);

				copy.from(fileTree);

				return;
			}
		}
	}

	protected void configureTasksRunPoshi(
		Project project, PoshiRunnerExtension poshiRunnerExtension) {

		Test test = (Test)GradleUtil.getTask(project, RUN_POSHI_TASK_NAME);

		configureTasksRunPoshiBinResultsDir(test);
		configureTasksRunPoshiReports(test);
		configureTasksRunPoshiSystemProperties(test, poshiRunnerExtension);
	}

	protected void configureTasksRunPoshiBinResultsDir(Test test) {
		if (test.getBinResultsDir() != null) {
			return;
		}

		Project project = test.getProject();

		test.setBinResultsDir(
			project.file("test-results/binary/" + RUN_POSHI_TASK_NAME));
	}

	protected void configureTasksRunPoshiReports(Test test) {
		Project project = test.getProject();
		TestTaskReports testTaskReports = test.getReports();

		DirectoryReport directoryReport = testTaskReports.getHtml();

		if (directoryReport.getDestination() == null) {
			directoryReport.setDestination(project.file("tests"));
		}

		directoryReport = testTaskReports.getJunitXml();

		if (directoryReport.getDestination() == null) {
			directoryReport.setDestination(project.file("test-results"));
		}
	}

	protected void configureTasksRunPoshiSystemProperties(
		Test test, PoshiRunnerExtension poshiRunnerExtension) {

		Map<String, Object> systemProperties = test.getSystemProperties();

		populateSystemProperties(systemProperties, poshiRunnerExtension);

		Project project = test.getProject();

		if (project.hasProperty("poshiTestName")) {
			systemProperties.put(
				"test.name", project.property("poshiTestName"));
		}
	}

	protected void configureTasksValidatePoshi(
		Project project, PoshiRunnerExtension poshiRunnerExtension) {

		JavaExec javaExec = (JavaExec)GradleUtil.getTask(
			project, VALIDATE_POSHI_TASK_NAME);

		populateSystemProperties(
			javaExec.getSystemProperties(), poshiRunnerExtension);
	}

	protected void configureTasksWritePoshiProperties(
		Project project, PoshiRunnerExtension poshiRunnerExtension) {

		JavaExec javaExec = (JavaExec)GradleUtil.getTask(
			project, WRITE_POSHI_PROPERTIES_TASK_NAME);

		populateSystemProperties(
			javaExec.getSystemProperties(), poshiRunnerExtension);
	}

	protected File getExpandedPoshiRunnerDir(Project project) {
		return new File(project.getBuildDir(), "poshi-runner");
	}

	protected void populateSystemProperties(
		Map<String, Object> systemProperties,
		PoshiRunnerExtension poshiRunnerExtension) {

		systemProperties.putAll(poshiRunnerExtension.getPoshiProperties());

		systemProperties.put("test.basedir", poshiRunnerExtension.getBaseDir());
	}

}

File: modules/sdk/gradle-plugins-poshi-runner/src/com/liferay/gradle/plugins/poshi/runner/util/GradleUtil.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.gradle.plugins.poshi.runner.util;

import java.util.HashMap;
import java.util.Map;

import org.gradle.api.Project;
import org.gradle.api.Task;
import org.gradle.api.artifacts.Configuration;
import org.gradle.api.artifacts.ConfigurationContainer;
import org.gradle.api.artifacts.Dependency;
import org.gradle.api.artifacts.dsl.DependencyHandler;
import org.gradle.api.plugins.ExtensionContainer;
import org.gradle.api.tasks.TaskContainer;

/**
 * @author Andrea Di Giorgi
 */
public class GradleUtil {

	public static Configuration addConfiguration(Project project, String name) {
		ConfigurationContainer configurationContainer =
			project.getConfigurations();

		return configurationContainer.create(name);
	}

	public static Dependency addDependency(
		Project project, String configurationName, String group, String name,
		String version, String classifier) {

		DependencyHandler dependencyHandler = project.getDependencies();

		Map<String, Object> dependencyNotation = new HashMap<>();

		dependencyNotation.put("group", group);
		dependencyNotation.put("name", name);
		dependencyNotation.put("version", version);

		if (Validator.isNotNull(classifier)) {
			dependencyNotation.put("classifier", classifier);
		}

		return dependencyHandler.add(configurationName, dependencyNotation);
	}

	public static <T> T addExtension(
		Project project, String name, Class<T> clazz) {

		ExtensionContainer extensionContainer = project.getExtensions();

		return extensionContainer.create(name, clazz, project);
	}

	public static <T extends Task> T addTask(
		Project project, String name, Class<T> clazz) {

		TaskContainer taskContainer = project.getTasks();

		return taskContainer.create(name, clazz);
	}

	public static Configuration getConfiguration(Project project, String name) {
		ConfigurationContainer configurationContainer =
			project.getConfigurations();

		return configurationContainer.getByName(name);
	}

	public static Task getTask(Project project, String name) {
		TaskContainer taskContainer = project.getTasks();

		return taskContainer.getByName(name);
	}

}

File: modules/sdk/gradle-plugins-poshi-runner/src/com/liferay/gradle/plugins/poshi/runner/util/Validator.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.gradle.plugins.poshi.runner.util;

/**
 * @author Brian Wing Shun Chan
 * @author Andrea Di Giorgi
 */
public class Validator {

	public static boolean isNotNull(String s) {
		return !isNull(s);
	}

	public static boolean isNull(String s) {
		if (s == null) {
			return true;
		}

		for (int i = 0; i < s.length(); i++) {
			char c = s.charAt(i);

			if (!Character.isWhitespace(c)) {
				return false;
			}
		}

		return true;
	}

}

File: modules/sdk/gradle-util/src/com/liferay/gradle/util/GradleUtil.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.gradle.util;

import groovy.lang.Closure;

import java.io.File;

import java.net.URL;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

import org.gradle.api.Action;
import org.gradle.api.GradleException;
import org.gradle.api.Plugin;
import org.gradle.api.Project;
import org.gradle.api.Task;
import org.gradle.api.artifacts.Configuration;
import org.gradle.api.artifacts.ConfigurationContainer;
import org.gradle.api.artifacts.Dependency;
import org.gradle.api.artifacts.ResolvableDependencies;
import org.gradle.api.artifacts.dsl.DependencyHandler;
import org.gradle.api.file.FileCollection;
import org.gradle.api.file.FileTree;
import org.gradle.api.plugins.Convention;
import org.gradle.api.plugins.ExtensionContainer;
import org.gradle.api.plugins.JavaPluginConvention;
import org.gradle.api.tasks.SourceSet;
import org.gradle.api.tasks.SourceSetContainer;
import org.gradle.api.tasks.TaskContainer;
import org.gradle.api.tasks.util.PatternFilterable;

/**
 * @author Andrea Di Giorgi
 */
public class GradleUtil {

	public static Configuration addConfiguration(Project project, String name) {
		ConfigurationContainer configurationContainer =
			project.getConfigurations();

		return configurationContainer.create(name);
	}

	public static Dependency addDependency(
		Project project, String configurationName, File file) {

		return _addDependency(project, configurationName, project.files(file));
	}

	public static Dependency addDependency(
		Project project, String configurationName,
		FileCollection fileCollection) {

		return _addDependency(project, configurationName, fileCollection);
	}

	public static Dependency addDependency(
		Project project, String configurationName, String dependencyNotation) {

		return _addDependency(project, configurationName, dependencyNotation);
	}

	public static Dependency addDependency(
		Project project, String configurationName, String group, String name,
		String version) {

		return addDependency(
			project, configurationName, group, name, version, true);
	}

	public static Dependency addDependency(
		Project project, String configurationName, String group, String name,
		String version, boolean transitive) {

		Map<String, Object> dependencyNotation = new HashMap<>();

		dependencyNotation.put("group", group);
		dependencyNotation.put("name", name);
		dependencyNotation.put("transitive", transitive);
		dependencyNotation.put("version", version);

		return _addDependency(project, configurationName, dependencyNotation);
	}

	public static <T> T addExtension(
		Project project, String name, Class<T> clazz) {

		ExtensionContainer extensionContainer = project.getExtensions();

		return extensionContainer.create(name, clazz, project);
	}

	public static SourceSet addSourceSet(Project project, String name) {
		JavaPluginConvention javaPluginConvention = getConvention(
			project, JavaPluginConvention.class);

		SourceSetContainer sourceSetContainer =
			javaPluginConvention.getSourceSets();

		return sourceSetContainer.create(name);
	}

	public static <T extends Task> T addTask(
		Project project, String name, Class<T> clazz) {

		Map<String, Class<T>> args = Collections.singletonMap(
			Task.TASK_TYPE, clazz);

		return (T)project.task(args, name);
	}

	public static <T extends Plugin<? extends Project>> void applyPlugin(
		Project project, Class<T> clazz) {

		Map<String, Class<T>> args = Collections.singletonMap("plugin", clazz);

		project.apply(args);
	}

	public static void applyScript(Project project, String name, Object obj) {
		Map<String, Object> args = new HashMap<>();

		ClassLoader classLoader = GradleUtil.class.getClassLoader();

		URL url = classLoader.getResource(name);

		if (url == null) {
			throw new GradleException("Unable to apply script " + name);
		}

		args.put("from", url);

		if (obj != null) {
			args.put("to", obj);
		}

		project.apply(args);
	}

	public static void executeIfEmpty(
		final Configuration configuration, final Action<Configuration> action) {

		ResolvableDependencies resolvableDependencies =
			configuration.getIncoming();

		resolvableDependencies.beforeResolve(
			new Action<ResolvableDependencies>() {

				@Override
				public void execute(
					ResolvableDependencies resolvableDependencies) {

					Set<Dependency> dependencies =
						configuration.getDependencies();
					Set<Configuration> parentConfigurations =
						configuration.getExtendsFrom();

					if (dependencies.isEmpty() &&
						parentConfigurations.isEmpty()) {

						action.execute(configuration);
					}
				}

			});
	}

	public static Configuration getConfiguration(Project project, String name) {
		ConfigurationContainer configurationContainer =
			project.getConfigurations();

		return configurationContainer.getByName(name);
	}

	public static <T> T getConvention(Project project, Class<T> clazz) {
		Convention convention = project.getConvention();

		return convention.getPlugin(clazz);
	}

	public static <T> T getExtension(Project project, Class<T> clazz) {
		ExtensionContainer extensionContainer = project.getExtensions();

		return extensionContainer.getByType(clazz);
	}

	public static FileTree getFilteredFileTree(
		FileTree fileTree, final String[] excludes, final String[] includes) {

		Closure<Void> closure = new Closure<Void>(null) {

			@SuppressWarnings("unused")
			public void doCall(PatternFilterable patternFilterable) {
				if (ArrayUtil.isNotEmpty(excludes)) {
					patternFilterable.setExcludes(Arrays.asList(excludes));
				}

				if (ArrayUtil.isNotEmpty(includes)) {
					patternFilterable.setIncludes(Arrays.asList(includes));
				}
			}

		};

		return fileTree.matching(closure);
	}

	public static Project getProject(Project rootProject, File projectDir) {
		for (Project project : rootProject.getAllprojects()) {
			if (projectDir.equals(project.getProjectDir())) {
				return project;
			}
		}

		return null;
	}

	public static SourceSet getSourceSet(Project project, String name) {
		JavaPluginConvention javaPluginConvention = getConvention(
			project, JavaPluginConvention.class);

		SourceSetContainer sourceSetContainer =
			javaPluginConvention.getSourceSets();

		return sourceSetContainer.getByName(name);
	}

	public static Task getTask(Project project, String name) {
		TaskContainer taskContainer = project.getTasks();

		return taskContainer.getByName(name);
	}

	public static String getTaskName(String prefix, File file) {
		String fileName = FileUtil.stripExtension(file.getName());

		fileName = fileName.replaceAll("\\W", "");

		return prefix + StringUtil.capitalize(fileName);
	}

	public static void removeDependencies(
		Project project, String configurationName,
		String[] dependencyNotations) {

		Configuration configuration = getConfiguration(
			project, configurationName);

		Set<Dependency> dependencies = configuration.getDependencies();

		Iterator<Dependency> iterator = dependencies.iterator();

		while (iterator.hasNext()) {
			Dependency dependency = iterator.next();

			String dependencyNotation = _getDependencyNotation(dependency);

			if (ArrayUtil.contains(dependencyNotations, dependencyNotation)) {
				iterator.remove();
			}
		}
	}

	private static Dependency _addDependency(
		Project project, String configurationName, Object dependencyNotation) {

		DependencyHandler dependencyHandler = project.getDependencies();

		return dependencyHandler.add(configurationName, dependencyNotation);
	}

	private static String _getDependencyNotation(Dependency dependency) {
		StringBuilder sb = new StringBuilder();

		if (Validator.isNotNull(dependency.getGroup())) {
			sb.append(dependency.getGroup());
			sb.append(":");
		}

		sb.append(dependency.getName());

		if (Validator.isNotNull(dependency.getVersion())) {
			sb.append(":");
			sb.append(dependency.getVersion());
		}

		return sb.toString();
	}

}