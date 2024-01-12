Refactoring Types: ['Extract Method']
tDependenciesCommand.java
/*
 * Copyright 2015-present Facebook, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package com.facebook.buck.cli;

import com.facebook.buck.graph.AbstractBottomUpTraversal;
import com.facebook.buck.json.BuildFileParseException;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetException;
import com.facebook.buck.parser.BuildTargetParser;
import com.facebook.buck.parser.BuildTargetPatternParser;
import com.facebook.buck.parser.ParserConfig;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TargetGraphAndTargets;
import com.facebook.buck.rules.TargetNode;
import com.facebook.buck.rules.TargetNodes;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.base.Preconditions;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Lists;
import com.google.common.collect.Multimap;
import com.google.common.collect.Multimaps;
import com.google.common.collect.Sets;
import com.google.common.collect.TreeMultimap;

import org.kohsuke.args4j.Argument;
import org.kohsuke.args4j.Option;

import java.io.IOException;
import java.util.Collection;
import java.util.List;

public class AuditDependenciesCommand extends AbstractCommand {

  private static final Logger LOG = Logger.get(AuditDependenciesCommand.class);

  @Option(name = "--json",
      usage = "Output in JSON format")
  private boolean generateJsonOutput;

  public boolean shouldGenerateJsonOutput() {
    return generateJsonOutput;
  }

  @Option(
      name = "--include-tests",
      usage = "Includes a target's tests with its dependencies. With the transitive flag, this " +
          "prints the dependencies of the tests as well")
  private boolean includeTests = false;

  @Option(name = "--transitive",
      aliases = { "-t" },
      usage = "Whether to include transitive dependencies in the output")
  private boolean transitive = false;

  @Argument
  private List<String> arguments = Lists.newArrayList();

  public List<String> getArguments() {
    return arguments;
  }

  @VisibleForTesting
  void setArguments(List<String> arguments) {
    this.arguments = arguments;
  }

  public boolean shouldShowTransitiveDependencies() {
    return transitive;
  }

  public boolean shouldIncludeTests() {
    return includeTests;
  }

  public List<String> getArgumentsFormattedAsBuildTargets(BuckConfig buckConfig) {
    return getCommandLineBuildTargetNormalizer(buckConfig).normalizeAll(getArguments());
  }

  @Override
  public int runWithoutHelp(final CommandRunnerParams params)
      throws IOException, InterruptedException {
    final ImmutableSet<String> fullyQualifiedBuildTargets = ImmutableSet.copyOf(
        getArgumentsFormattedAsBuildTargets(params.getBuckConfig()));

    if (fullyQualifiedBuildTargets.isEmpty()) {
      params.getConsole().printBuildFailure("Must specify at least one build target.");
      return 1;
    }

    ImmutableSet<BuildTarget> targets = FluentIterable
        .from(getArgumentsFormattedAsBuildTargets(params.getBuckConfig()))
        .transform(
            new Function<String, BuildTarget>() {
              @Override
              public BuildTarget apply(String input) {
                return BuildTargetParser.INSTANCE.parse(
                    input,
                    BuildTargetPatternParser.fullyQualified());
              }
            })
        .toSet();

    TargetGraph graph;
    try {
      graph = params.getParser().buildTargetGraphForBuildTargets(
          targets,
          new ParserConfig(params.getBuckConfig()),
          params.getBuckEventBus(),
          params.getConsole(),
          params.getEnvironment(),
          getEnableProfiling());
    } catch (BuildTargetException | BuildFileParseException e) {
      params.getConsole().printBuildFailureWithoutStacktrace(e);
      return 1;
    }

    TreeMultimap<BuildTarget, BuildTarget> targetsAndDependencies = TreeMultimap.create();
    for (BuildTarget target : targets) {
      targetsAndDependencies.putAll(target, getDependenciesWithOptions(params, target, graph));
    }

    if (shouldGenerateJsonOutput()) {
      printJSON(params, targetsAndDependencies);
    } else {
      printToConsole(params, targetsAndDependencies);
    }

    return 0;
  }

  @Override
  public boolean isReadOnly() {
    return true;
  }

  ImmutableSet<BuildTarget> getDependenciesWithOptions(
      CommandRunnerParams params,
      BuildTarget target,
      TargetGraph graph) throws IOException, InterruptedException {
    ImmutableSet<BuildTarget> targetsToPrint = shouldShowTransitiveDependencies() ?
        getTransitiveDependencies(ImmutableSet.of(target), graph) :
        getImmediateDependencies(target, graph);

    if (shouldIncludeTests()) {
      ImmutableSet.Builder<BuildTarget> builder = ImmutableSet.builder();
      targetsToPrint = builder
          .addAll(targetsToPrint)
          .addAll(getTestTargetDependencies(params, target, graph))
          .build();
    }
    return targetsToPrint;
  }

  @VisibleForTesting
  ImmutableSet<BuildTarget> getTransitiveDependencies(
      final ImmutableSet<BuildTarget> targets,
      TargetGraph graph) {
    final ImmutableSet.Builder<BuildTarget> builder = ImmutableSet.builder();

    TargetGraph subgraph = graph.getSubgraph(graph.getAll(targets));
    new AbstractBottomUpTraversal<TargetNode<?>, Void>(subgraph) {

      @Override
      public void visit(TargetNode<?> node) {
        LOG.debug("Visiting dependency " + node.getBuildTarget().getFullyQualifiedName());
        // Don't add the requested target to the list of dependencies
        if (!targets.contains(node.getBuildTarget())) {
          builder.add(node.getBuildTarget());
        }
      }

      @Override
      public Void getResult() {
        return null;
      }

    }.traverse();

    return builder.build();
  }

  @VisibleForTesting
  ImmutableSet<BuildTarget> getImmediateDependencies(BuildTarget target, TargetGraph graph) {
    return Preconditions.checkNotNull(graph.get(target)).getDeps();
  }

  @VisibleForTesting
  Collection<BuildTarget> getTestTargetDependencies(
      CommandRunnerParams params,
      BuildTarget target,
      TargetGraph graph) throws IOException, InterruptedException {
    if (!shouldShowTransitiveDependencies()) {
      return TargetNodes.getTestTargetsForNode(Preconditions.checkNotNull(graph.get(target)));
    }

    ProjectGraphParser projectGraphParser = ProjectGraphParsers.createProjectGraphParser(
        params.getParser(),
        new ParserConfig(params.getBuckConfig()),
        params.getBuckEventBus(),
        params.getConsole(),
        params.getEnvironment(),
        getEnableProfiling());

    TargetGraph graphWithTests = TargetGraphTestParsing.expandedTargetGraphToIncludeTestsForTargets(
        projectGraphParser,
        graph,
        ImmutableSet.of(target));

    ImmutableSet<BuildTarget> tests = TargetGraphAndTargets.getExplicitTestTargets(
        ImmutableSet.of(target),
        graphWithTests);
    // We want to return the set of all tests plus their dependencies. Luckily
    // `getTransitiveDependencies` will give us the last part, but we need to make sure we include
    // the tests themselves in our final output
    Sets.SetView<BuildTarget> testsWithDependencies = Sets.union(
        tests,
        getTransitiveDependencies(tests, graphWithTests));
    // Tests normally depend on the code they are testing, but we don't want to include that in our
    // output, so explicitly filter that here.
    return Sets.difference(testsWithDependencies, ImmutableSet.of(target));
  }

  private void printJSON(
      CommandRunnerParams params,
      Multimap<BuildTarget, BuildTarget> targetsAndDependencies) throws IOException {
    Multimap<BuildTarget, String> targetsAndDependenciesNames =
        Multimaps.transformValues(
            targetsAndDependencies, new Function<BuildTarget, String>() {
              @Override
              public String apply(BuildTarget input) {
                return Preconditions.checkNotNull(input.getFullyQualifiedName());
              }
            });
    params.getObjectMapper().writeValue(
        params.getConsole().getStdOut(),
        targetsAndDependenciesNames.asMap());
  }

  private void printToConsole(
      CommandRunnerParams params,
      Multimap<BuildTarget, BuildTarget> targetsAndDependencies) {
    for (BuildTarget target : ImmutableSortedSet.copyOf(targetsAndDependencies.values())) {
      params.getConsole().getStdOut().println(target.getFullyQualifiedName());
    }
  }

  @Override
  public String getShortDescription() {
    return "provides facilities to audit build targets' dependencies";
  }

}


File: src/com/facebook/buck/cli/AuditTestsCommand.java
/*
 * Copyright 2015-present Facebook, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package com.facebook.buck.cli;

import com.facebook.buck.json.BuildFileParseException;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetException;
import com.facebook.buck.parser.ParserConfig;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TargetNodes;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Lists;
import com.google.common.collect.Multimap;
import com.google.common.collect.Multimaps;
import com.google.common.collect.TreeMultimap;

import org.kohsuke.args4j.Argument;
import org.kohsuke.args4j.Option;

import java.io.IOException;
import java.util.List;

public class AuditTestsCommand extends AbstractCommand {

  private static final Logger LOG = Logger.get(AuditTestsCommand.class);

  @Option(name = "--json",
      usage = "Output in JSON format")
  private boolean generateJsonOutput;

  public boolean shouldGenerateJsonOutput() {
    return generateJsonOutput;
  }

  @Argument
  private List<String> arguments = Lists.newArrayList();

  public List<String> getArguments() {
    return arguments;
  }

  @VisibleForTesting
  void setArguments(List<String> arguments) {
    this.arguments = arguments;
  }

  public List<String> getArgumentsFormattedAsBuildTargets(BuckConfig buckConfig) {
    return getCommandLineBuildTargetNormalizer(buckConfig).normalizeAll(getArguments());
  }

  @Override
  public int runWithoutHelp(CommandRunnerParams params) throws IOException, InterruptedException {
    final ImmutableSet<String> fullyQualifiedBuildTargets = ImmutableSet.copyOf(
        getArgumentsFormattedAsBuildTargets(params.getBuckConfig()));

    if (fullyQualifiedBuildTargets.isEmpty()) {
      params.getConsole().printBuildFailure("Must specify at least one build target.");
      return 1;
    }

    ImmutableSet<BuildTarget> targets = getBuildTargets(
        ImmutableSet.copyOf(getArgumentsFormattedAsBuildTargets(params.getBuckConfig())));

    TargetGraph graph;
    try {
      graph = params.getParser().buildTargetGraphForBuildTargets(
          targets,
          new ParserConfig(params.getBuckConfig()),
          params.getBuckEventBus(),
          params.getConsole(),
          params.getEnvironment(),
          getEnableProfiling());
    } catch (BuildTargetException | BuildFileParseException e) {
      params.getConsole().printBuildFailureWithoutStacktrace(e);
      return 1;
    }

    TreeMultimap<BuildTarget, BuildTarget> targetsToPrint =
        getTestsForTargets(targets, graph);
    LOG.debug("Printing out the following targets: " + targetsToPrint);

    if (shouldGenerateJsonOutput()) {
      printJSON(params, targetsToPrint);
    } else {
      printToConsole(params, targetsToPrint);
    }

    return 0;
  }

  @Override
  public boolean isReadOnly() {
    return true;
  }

  TreeMultimap<BuildTarget, BuildTarget> getTestsForTargets(
      final ImmutableSet<BuildTarget> targets,
      final TargetGraph graph) {
    TreeMultimap<BuildTarget, BuildTarget> multimap = TreeMultimap.create();
    for (BuildTarget target : targets) {
      multimap.putAll(
          target,
          TargetNodes.getTestTargetsForNode(Preconditions.checkNotNull(graph.get(target))));
    }
    return multimap;
  }

  private void printJSON(
      CommandRunnerParams params,
      Multimap<BuildTarget, BuildTarget> targetsAndTests)
      throws IOException {
    Multimap<BuildTarget, String> targetsAndTestNames =
        Multimaps.transformValues(
            targetsAndTests, new Function<BuildTarget, String>() {
              @Override
              public String apply(BuildTarget input) {
                return Preconditions.checkNotNull(input.getFullyQualifiedName());
              }
            });
    params.getObjectMapper().writeValue(
        params.getConsole().getStdOut(),
        targetsAndTestNames.asMap());
  }

  private void printToConsole(
      CommandRunnerParams params,
      Multimap<BuildTarget, BuildTarget> targetsAndTests) {
    for (BuildTarget target : ImmutableSortedSet.copyOf(targetsAndTests.values())) {
      params.getConsole().getStdOut().println(target.getFullyQualifiedName());
    }
  }

  @Override
  public String getShortDescription() {
    return "provides facilities to audit build targets' tests";
  }

}


File: test/com/facebook/buck/cli/AuditDependenciesCommandTest.java
/*
 * Copyright 2015-present Facebook, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package com.facebook.buck.cli;

import static org.junit.Assert.assertEquals;

import com.facebook.buck.java.JavaLibraryBuilder;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TargetNode;
import com.facebook.buck.testutil.FakeProjectFilesystem;
import com.facebook.buck.testutil.TargetGraphFactory;
import com.google.common.collect.ImmutableSet;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import java.io.IOException;
import java.nio.file.Paths;

public class AuditDependenciesCommandTest {

  private AuditDependenciesCommand auditDependenciesCommand;

  @Rule
  public ExpectedException thrown = ExpectedException.none();

  @Before
  public void setUp() throws IOException, InterruptedException{
    FakeProjectFilesystem projectFilesystem = new FakeProjectFilesystem();
    projectFilesystem.touch(Paths.get("src/com/facebook/TestAndroidLibrary.java"));
    projectFilesystem.touch(Paths.get("src/com/facebook/TestAndroidLibraryTwo.java"));
    projectFilesystem.touch(Paths.get("src/com/facebook/TestJavaLibrary.java"));
    projectFilesystem.touch(Paths.get("src/com/facebook/TestJavaLibraryTwo.java"));
    projectFilesystem.touch(Paths.get("src/com/facebook/TestJavaLibraryThree.java"));

    auditDependenciesCommand = new AuditDependenciesCommand();
  }

  @Test
  public void testGetTransitiveDependenciesWalksTheGraph() throws IOException {
    BuildTarget javaTarget = BuildTargetFactory.newInstance("//:test-java-library");
    TargetNode<?> javaNode = JavaLibraryBuilder
        .createBuilder(javaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibrary.java"))
        .build();

    BuildTarget secondLibraryTarget = BuildTargetFactory.newInstance("//:test-android-library-two");
    TargetNode<?> secondLibraryNode = JavaLibraryBuilder
        .createBuilder(secondLibraryTarget)
        .addSrc(Paths.get("src/com/facebook/TestAndroidLibraryTwo.java"))
        .addDep(javaTarget)
        .build();

    BuildTarget libraryTarget = BuildTargetFactory.newInstance("//:test-android-library");
    TargetNode<?> libraryNode = JavaLibraryBuilder
        .createBuilder(libraryTarget)
        .addSrc(Paths.get("src/com/facebook/TestAndroidLibrary.java"))
        .addDep(secondLibraryTarget)
        .build();

    ImmutableSet<TargetNode<?>> nodes = ImmutableSet.of(javaNode, libraryNode, secondLibraryNode);
    TargetGraph targetGraph = TargetGraphFactory.newInstance(nodes);

    ImmutableSet<BuildTarget> testInput = ImmutableSet.of(libraryTarget);
    ImmutableSet<BuildTarget> transitiveDependencies =
        auditDependenciesCommand.getTransitiveDependencies(testInput, targetGraph);
    assertEquals(ImmutableSet.of(secondLibraryTarget, javaTarget), transitiveDependencies);
  }

  @Test
  public void testGetImmediateDependenciesDoesntReturnTransitiveDependencies() throws IOException {
    BuildTarget javaTarget = BuildTargetFactory.newInstance("//:test-java-library");
    TargetNode<?> javaNode = JavaLibraryBuilder
        .createBuilder(javaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibrary.java"))
        .build();

    BuildTarget secondLibraryTarget = BuildTargetFactory.newInstance("//:test-android-library-two");
    TargetNode<?> secondLibraryNode = JavaLibraryBuilder
        .createBuilder(secondLibraryTarget)
        .addSrc(Paths.get("src/com/facebook/TestAndroidLibraryTwo.java"))
        .addDep(javaTarget)
        .build();

    BuildTarget libraryTarget = BuildTargetFactory.newInstance("//:test-android-library");
    TargetNode<?> libraryNode = JavaLibraryBuilder
        .createBuilder(libraryTarget)
        .addSrc(Paths.get("src/com/facebook/TestAndroidLibrary.java"))
        .addDep(secondLibraryTarget)
        .build();

    ImmutableSet<TargetNode<?>> nodes = ImmutableSet.of(javaNode, libraryNode, secondLibraryNode);
    TargetGraph targetGraph = TargetGraphFactory.newInstance(nodes);

    ImmutableSet<BuildTarget> immediateDependencies =
        auditDependenciesCommand.getImmediateDependencies(libraryTarget, targetGraph);
    assertEquals(ImmutableSet.of(secondLibraryTarget), immediateDependencies);
  }

  @Test
  public void testGetTransitiveDependenciesWithMultipleInputsReturnsAllDependencies()
      throws IOException {
    BuildTarget thirdJavaTarget = BuildTargetFactory.newInstance("//:test-java-library-three");
    TargetNode<?> thirdJavaNode = JavaLibraryBuilder
        .createBuilder(thirdJavaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibraryThree.java"))
        .build();

    BuildTarget secondJavaTarget = BuildTargetFactory.newInstance("//:test-java-library-two");
    TargetNode<?> secondJavaNode = JavaLibraryBuilder
        .createBuilder(secondJavaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibraryTwo.java"))
        .addDep(thirdJavaTarget)
        .build();

    BuildTarget javaTarget = BuildTargetFactory.newInstance("//:test-java-library");
    TargetNode<?> javaNode = JavaLibraryBuilder
        .createBuilder(javaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibrary.java"))
        .addDep(secondJavaTarget)
        .build();

    BuildTarget secondLibraryTarget = BuildTargetFactory.newInstance("//:test-android-library-two");
    TargetNode<?> secondLibraryNode = JavaLibraryBuilder
        .createBuilder(secondLibraryTarget)
        .addSrc(Paths.get("src/com/facebook/TestAndroidLibraryTwo.java"))
        .build();

    BuildTarget libraryTarget = BuildTargetFactory.newInstance("//:test-android-library");
    TargetNode<?> libraryNode = JavaLibraryBuilder
        .createBuilder(libraryTarget)
        .addSrc(Paths.get("src/com/facebook/TestAndroidLibrary.java"))
        .addDep(secondLibraryTarget)
        .build();

    ImmutableSet<TargetNode<?>> nodes =
        ImmutableSet.of(javaNode, secondJavaNode, thirdJavaNode, libraryNode, secondLibraryNode);
    TargetGraph targetGraph = TargetGraphFactory.newInstance(nodes);

    ImmutableSet<BuildTarget> testInput = ImmutableSet.of(libraryTarget, javaTarget);
    ImmutableSet<BuildTarget> transitiveDependencies =
        auditDependenciesCommand.getTransitiveDependencies(testInput, targetGraph);
    ImmutableSet<BuildTarget> expectedOutput =
        ImmutableSet.of(secondLibraryTarget, secondJavaTarget, thirdJavaTarget);
    assertEquals(expectedOutput, transitiveDependencies);
  }

  @Test
  public void testGetImmediateDependenciesIncludesExtraDependencies() throws IOException {
    BuildTarget thirdJavaTarget = BuildTargetFactory.newInstance("//:test-java-library-three");
    TargetNode<?> thirdJavaNode = JavaLibraryBuilder
        .createBuilder(thirdJavaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibraryThree.java"))
        .build();

    BuildTarget secondJavaTarget = BuildTargetFactory.newInstance("//:test-java-library-two");
    TargetNode<?> secondJavaNode = JavaLibraryBuilder
        .createBuilder(secondJavaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibraryTwo.java"))
        .build();

    BuildTarget javaTarget = BuildTargetFactory.newInstance("//:test-java-library");
    TargetNode<?> javaNode = JavaLibraryBuilder
        .createBuilder(javaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibrary.java"))
        .addExportedDep(thirdJavaTarget)
        .addDep(secondJavaTarget)
        .build();

    ImmutableSet<TargetNode<?>> nodes =
        ImmutableSet.of(javaNode, secondJavaNode, thirdJavaNode);
    TargetGraph targetGraph = TargetGraphFactory.newInstance(nodes);

    ImmutableSet<BuildTarget> transitiveDependencies =
        auditDependenciesCommand.getImmediateDependencies(javaTarget, targetGraph);
    ImmutableSet<BuildTarget> expectedOutput =
        ImmutableSet.of(secondJavaTarget, thirdJavaTarget);
    assertEquals(expectedOutput, transitiveDependencies);
  }

  @Test
  public void testGetTransitiveDependenciesIncludesExtraDependencies() throws IOException {
    BuildTarget thirdJavaTarget = BuildTargetFactory.newInstance("//:test-java-library-three");
    TargetNode<?> thirdJavaNode = JavaLibraryBuilder
        .createBuilder(thirdJavaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibraryThree.java"))
        .build();

    BuildTarget secondJavaTarget = BuildTargetFactory.newInstance("//:test-java-library-two");
    TargetNode<?> secondJavaNode = JavaLibraryBuilder
        .createBuilder(secondJavaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibraryTwo.java"))
        .build();

    BuildTarget javaTarget = BuildTargetFactory.newInstance("//:test-java-library");
    TargetNode<?> javaNode = JavaLibraryBuilder
        .createBuilder(javaTarget)
        .addSrc(Paths.get("src/com/facebook/TestJavaLibrary.java"))
        .addExportedDep(thirdJavaTarget)
        .addDep(secondJavaTarget)
        .build();

    BuildTarget secondLibraryTarget = BuildTargetFactory.newInstance("//:test-android-library-two");
    TargetNode<?> secondLibraryNode = JavaLibraryBuilder
        .createBuilder(secondLibraryTarget)
        .addSrc(Paths.get("src/com/facebook/TestAndroidLibraryTwo.java"))
        .addExportedDep(javaTarget)
        .build();

    BuildTarget libraryTarget = BuildTargetFactory.newInstance("//:test-android-library");
    TargetNode<?> libraryNode = JavaLibraryBuilder
        .createBuilder(libraryTarget)
        .addSrc(Paths.get("src/com/facebook/TestAndroidLibrary.java"))
        .addDep(secondLibraryTarget)
        .build();

    ImmutableSet<TargetNode<?>> nodes =
        ImmutableSet.of(javaNode, secondJavaNode, thirdJavaNode, libraryNode, secondLibraryNode);
    TargetGraph targetGraph = TargetGraphFactory.newInstance(nodes);

    ImmutableSet<BuildTarget> testInput = ImmutableSet.of(libraryTarget);
    ImmutableSet<BuildTarget> transitiveDependencies =
        auditDependenciesCommand.getTransitiveDependencies(testInput, targetGraph);
    ImmutableSet<BuildTarget> expectedOutput =
        ImmutableSet.of(secondLibraryTarget, javaTarget, secondJavaTarget, thirdJavaTarget);
    assertEquals(expectedOutput, transitiveDependencies);
  }

}
