Refactoring Types: ['Extract Method']
ojectGenerator.java
/*
 * Copyright 2013-present Facebook, Inc.
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

package com.facebook.buck.apple;

import com.dd.plist.NSDictionary;
import com.dd.plist.NSObject;
import com.dd.plist.NSString;
import com.dd.plist.PropertyListParser;
import com.facebook.buck.apple.clang.HeaderMap;
import com.facebook.buck.apple.xcode.GidGenerator;
import com.facebook.buck.apple.xcode.XcodeprojSerializer;
import com.facebook.buck.apple.xcode.xcodeproj.PBXAggregateTarget;
import com.facebook.buck.apple.xcode.xcodeproj.PBXBuildFile;
import com.facebook.buck.apple.xcode.xcodeproj.PBXCopyFilesBuildPhase;
import com.facebook.buck.apple.xcode.xcodeproj.PBXFileReference;
import com.facebook.buck.apple.xcode.xcodeproj.PBXGroup;
import com.facebook.buck.apple.xcode.xcodeproj.PBXNativeTarget;
import com.facebook.buck.apple.xcode.xcodeproj.PBXProject;
import com.facebook.buck.apple.xcode.xcodeproj.PBXReference;
import com.facebook.buck.apple.xcode.xcodeproj.PBXShellScriptBuildPhase;
import com.facebook.buck.apple.xcode.xcodeproj.PBXTarget;
import com.facebook.buck.apple.xcode.xcodeproj.ProductType;
import com.facebook.buck.apple.xcode.xcodeproj.SourceTreePath;
import com.facebook.buck.apple.xcode.xcodeproj.XCBuildConfiguration;
import com.facebook.buck.apple.xcode.xcodeproj.XCConfigurationList;
import com.facebook.buck.apple.xcode.xcodeproj.XCVersionGroup;
import com.facebook.buck.cxx.CxxDescriptionEnhancer;
import com.facebook.buck.cxx.CxxSource;
import com.facebook.buck.cxx.HeaderVisibility;
import com.facebook.buck.io.MorePaths;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.js.IosReactNativeLibraryDescription;
import com.facebook.buck.js.ReactNativeFlavors;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuckVersion;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargets;
import com.facebook.buck.model.HasTests;
import com.facebook.buck.parser.NoSuchBuildTargetException;
import com.facebook.buck.rules.BuildRuleType;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.PathSourcePath;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TargetNode;
import com.facebook.buck.rules.coercer.Either;
import com.facebook.buck.rules.coercer.FrameworkPath;
import com.facebook.buck.rules.coercer.SourceList;
import com.facebook.buck.rules.coercer.SourceWithFlags;
import com.facebook.buck.shell.ExportFileDescription;
import com.facebook.buck.shell.GenruleDescription;
import com.facebook.buck.util.BuckConstant;
import com.facebook.buck.util.Escaper;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.buck.util.MoreIterables;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Charsets;
import com.google.common.base.Function;
import com.google.common.base.Functions;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.base.Predicate;
import com.google.common.base.Predicates;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableCollection;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSetMultimap;
import com.google.common.collect.ImmutableSortedMap;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Maps;
import com.google.common.collect.Multimap;
import com.google.common.collect.Sets;
import com.google.common.hash.HashCode;
import com.google.common.hash.Hasher;
import com.google.common.hash.Hashing;
import com.google.common.io.BaseEncoding;
import com.google.common.util.concurrent.UncheckedExecutionException;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.FileVisitResult;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.FileAttribute;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Generator for xcode project and associated files from a set of xcode/ios rules.
 */
public class ProjectGenerator {
  private static final Logger LOG = Logger.get(ProjectGenerator.class);

  public enum Option {
    /** Use short BuildTarget name instead of full name for targets */
    USE_SHORT_NAMES_FOR_TARGETS,

    /** Put targets into groups reflecting directory structure of their BUCK files */
    CREATE_DIRECTORY_STRUCTURE,

    /** Generate read-only project files */
    GENERATE_READ_ONLY_FILES,

    /** Include tests in the scheme */
    INCLUDE_TESTS,
    ;
  }

  /**
   * Standard options for generating a separated project
   */
  public static final ImmutableSet<Option> SEPARATED_PROJECT_OPTIONS = ImmutableSet.of(
      Option.USE_SHORT_NAMES_FOR_TARGETS);

  /**
   * Standard options for generating a combined project
   */
  public static final ImmutableSet<Option> COMBINED_PROJECT_OPTIONS = ImmutableSet.of(
      Option.CREATE_DIRECTORY_STRUCTURE,
      Option.USE_SHORT_NAMES_FOR_TARGETS);

  public static final String PATH_TO_ASSET_CATALOG_COMPILER = System.getProperty(
      "buck.path_to_compile_asset_catalogs_py",
      "src/com/facebook/buck/apple/compile_asset_catalogs.py");
  public static final String PATH_TO_ASSET_CATALOG_BUILD_PHASE_SCRIPT = System.getProperty(
      "buck.path_to_compile_asset_catalogs_build_phase_sh",
      "src/com/facebook/buck/apple/compile_asset_catalogs_build_phase.sh");
  public static final String PATH_OVERRIDE_FOR_ASSET_CATALOG_BUILD_PHASE_SCRIPT =
      System.getProperty(
          "buck.path_override_for_asset_catalog_build_phase",
          null);

  private static final FileAttribute<?> READ_ONLY_FILE_ATTRIBUTE =
    PosixFilePermissions.asFileAttribute(
        ImmutableSet.of(
            PosixFilePermission.OWNER_READ,
            PosixFilePermission.GROUP_READ,
            PosixFilePermission.OTHERS_READ));

  public static final Function<
      TargetNode<AppleNativeTargetDescriptionArg>,
      Iterable<String>> GET_EXPORTED_LINKER_FLAGS =
      new Function<TargetNode<AppleNativeTargetDescriptionArg>, Iterable<String>>() {
        @Override
        public Iterable<String> apply(TargetNode<AppleNativeTargetDescriptionArg> input) {
          return input.getConstructorArg().exportedLinkerFlags.get();
        }
      };

  public static final Function<
      TargetNode<AppleNativeTargetDescriptionArg>,
      Iterable<String>> GET_EXPORTED_PREPROCESSOR_FLAGS =
      new Function<TargetNode<AppleNativeTargetDescriptionArg>, Iterable<String>>() {
        @Override
        public Iterable<String> apply(TargetNode<AppleNativeTargetDescriptionArg> input) {
          return input.getConstructorArg().exportedPreprocessorFlags.get();
        }
      };

  private static final ImmutableSet<CxxSource.Type> SUPPORTED_LANG_PREPROCESSOR_FLAG_TYPES =
      ImmutableSet.of(CxxSource.Type.CXX, CxxSource.Type.OBJCXX);

  private final Function<SourcePath, Path> sourcePathResolver;
  private final TargetGraph targetGraph;
  private final ProjectFilesystem projectFilesystem;
  private final Optional<Path> reactNativeServer;
  private final Path outputDirectory;
  private final String projectName;
  private final ImmutableSet<BuildTarget> initialTargets;
  private final Path projectPath;
  private final Path placedAssetCatalogBuildPhaseScript;
  private final PathRelativizer pathRelativizer;

  private final String buildFileName;
  private final ImmutableSet<Option> options;
  private final Optional<BuildTarget> targetToBuildWithBuck;
  private final ImmutableList<String> buildWithBuckFlags;

  private ImmutableSet<TargetNode<AppleTestDescription.Arg>> testsToGenerateAsStaticLibraries =
      ImmutableSet.of();
  private ImmutableMultimap<AppleTestBundleParamsKey, TargetNode<AppleTestDescription.Arg>>
      additionalCombinedTestTargets = ImmutableMultimap.of();

  // These fields are created/filled when creating the projects.
  private final PBXProject project;
  private final LoadingCache<TargetNode<?>, Optional<PBXTarget>> targetNodeToProjectTarget;
  private boolean shouldPlaceAssetCatalogCompiler = false;
  private final ImmutableMultimap.Builder<TargetNode<?>, PBXTarget>
      targetNodeToGeneratedProjectTargetBuilder;
  private boolean projectGenerated;
  private final List<Path> headerSymlinkTrees;
  private final ImmutableSet.Builder<PBXTarget> buildableCombinedTestTargets =
      ImmutableSet.builder();
  private final ImmutableSet.Builder<BuildTarget> requiredBuildTargetsBuilder =
      ImmutableSet.builder();
  private final Function<? super TargetNode<?>, Path> outputPathOfNode;

  /**
   * Populated while generating project configurations, in order to collect the possible
   * project-level configurations to set.
   */
  private final ImmutableSet.Builder<String> targetConfigNamesBuilder;

  private final Map<String, String> gidsToTargetNames;

  public ProjectGenerator(
      TargetGraph targetGraph,
      Set<BuildTarget> initialTargets,
      ProjectFilesystem projectFilesystem,
      Optional<Path> reactNativeServer,
      Path outputDirectory,
      String projectName,
      String buildFileName,
      Set<Option> options,
      Optional<BuildTarget> targetToBuildWithBuck,
      ImmutableList<String> buildWithBuckFlags,
      Function<? super TargetNode<?>, Path> outputPathOfNode) {
    this.sourcePathResolver = new Function<SourcePath, Path>() {
      @Override
      public Path apply(SourcePath input) {
        return resolveSourcePath(input);
      }
    };

    this.targetGraph = targetGraph;
    this.initialTargets = ImmutableSet.copyOf(initialTargets);
    this.projectFilesystem = projectFilesystem;
    this.reactNativeServer = reactNativeServer;
    this.outputDirectory = outputDirectory;
    this.projectName = projectName;
    this.buildFileName = buildFileName;
    this.options = ImmutableSet.copyOf(options);
    this.targetToBuildWithBuck = targetToBuildWithBuck;
    this.buildWithBuckFlags = buildWithBuckFlags;
    this.outputPathOfNode = outputPathOfNode;

    this.projectPath = outputDirectory.resolve(projectName + ".xcodeproj");
    this.pathRelativizer = new PathRelativizer(
        outputDirectory,
        sourcePathResolver);

    LOG.debug(
        "Output directory %s, profile fs root path %s, repo root relative to output dir %s",
        this.outputDirectory,
        projectFilesystem.getRootPath(),
        this.pathRelativizer.outputDirToRootRelative(Paths.get(".")));

    this.placedAssetCatalogBuildPhaseScript =
        BuckConstant.SCRATCH_PATH.resolve("xcode-scripts/compile_asset_catalogs_build_phase.sh");

    this.project = new PBXProject(projectName);
    this.headerSymlinkTrees = new ArrayList<>();

    this.targetNodeToGeneratedProjectTargetBuilder = ImmutableMultimap.builder();
    this.targetNodeToProjectTarget = CacheBuilder.newBuilder().build(
        new CacheLoader<TargetNode<?>, Optional<PBXTarget>>() {
          @Override
          public Optional<PBXTarget> load(TargetNode<?> key) throws Exception {
            return generateProjectTarget(key);
          }
        });

    targetConfigNamesBuilder = ImmutableSet.builder();
    gidsToTargetNames = new HashMap<>();
  }

  /**
   * Sets the set of tests which should be generated as static libraries instead of test bundles.
   */
  public ProjectGenerator setTestsToGenerateAsStaticLibraries(
      Set<TargetNode<AppleTestDescription.Arg>> set) {
    Preconditions.checkState(!projectGenerated);
    this.testsToGenerateAsStaticLibraries = ImmutableSet.copyOf(set);
    return this;
  }

  /**
   * Sets combined test targets which should be generated in this project.
   */
  public ProjectGenerator setAdditionalCombinedTestTargets(
      Multimap<AppleTestBundleParamsKey, TargetNode<AppleTestDescription.Arg>> targets) {
    Preconditions.checkState(!projectGenerated);
    this.additionalCombinedTestTargets = ImmutableMultimap.copyOf(targets);
    return this;
  }

  @VisibleForTesting
  PBXProject getGeneratedProject() {
    return project;
  }

  @VisibleForTesting
  List<Path> getGeneratedHeaderSymlinkTrees() {
    return headerSymlinkTrees;
  }

  public Path getProjectPath() {
    return projectPath;
  }

  public ImmutableMultimap<BuildTarget, PBXTarget> getBuildTargetToGeneratedTargetMap() {
    Preconditions.checkState(projectGenerated, "Must have called createXcodeProjects");
    ImmutableMultimap.Builder<BuildTarget, PBXTarget> buildTargetToPbxTargetMap =
        ImmutableMultimap.builder();
    for (Map.Entry<TargetNode<?>, PBXTarget> entry :
        targetNodeToGeneratedProjectTargetBuilder.build().entries()) {
      buildTargetToPbxTargetMap.put(entry.getKey().getBuildTarget(), entry.getValue());
    }
    return buildTargetToPbxTargetMap.build();
  }

  public ImmutableSet<PBXTarget> getBuildableCombinedTestTargets() {
    Preconditions.checkState(projectGenerated, "Must have called createXcodeProjects");
    return buildableCombinedTestTargets.build();
  }

  public ImmutableSet<BuildTarget> getRequiredBuildTargets() {
    Preconditions.checkState(projectGenerated, "Must have called createXcodeProjects");
    return requiredBuildTargetsBuilder.build();
  }

  public void createXcodeProjects() throws IOException {
    LOG.debug("Creating projects for targets %s", initialTargets);

    try {
      for (TargetNode<?> targetNode : targetGraph.getNodes()) {
        if (isBuiltByCurrentProject(targetNode.getBuildTarget())) {
          LOG.debug("Including rule %s in project", targetNode);
          // Trigger the loading cache to call the generateProjectTarget function.
          Optional<PBXTarget> target = targetNodeToProjectTarget.getUnchecked(targetNode);
          if (target.isPresent()) {
            targetNodeToGeneratedProjectTargetBuilder.put(targetNode, target.get());
          }
        } else {
          LOG.verbose("Excluding rule %s (not built by current project)", targetNode);
        }
      }

      if (targetToBuildWithBuck.isPresent()) {
        generateAggregateTarget(
            Preconditions.checkNotNull(targetGraph.get(targetToBuildWithBuck.get())));
      }

      int combinedTestIndex = 0;
      for (AppleTestBundleParamsKey key : additionalCombinedTestTargets.keySet()) {
        generateCombinedTestTarget(
            deriveCombinedTestTargetNameFromKey(key, combinedTestIndex++),
            key,
            additionalCombinedTestTargets.get(key));
      }

      for (String configName : targetConfigNamesBuilder.build()) {
        XCBuildConfiguration outputConfig = project
            .getBuildConfigurationList()
            .getBuildConfigurationsByName()
            .getUnchecked(configName);
        outputConfig.setBuildSettings(new NSDictionary());
      }

      writeProjectFile(project);

      if (shouldPlaceAssetCatalogCompiler) {
        Path placedAssetCatalogCompilerPath = projectFilesystem.getPathForRelativePath(
            BuckConstant.SCRATCH_PATH.resolve(
                "xcode-scripts/compile_asset_catalogs.py"));
        LOG.debug("Ensuring asset catalog is copied to path [%s]", placedAssetCatalogCompilerPath);
        projectFilesystem.createParentDirs(placedAssetCatalogCompilerPath);
        projectFilesystem.createParentDirs(placedAssetCatalogBuildPhaseScript);
        projectFilesystem.copyFile(
            Paths.get(PATH_TO_ASSET_CATALOG_COMPILER),
            placedAssetCatalogCompilerPath);
        projectFilesystem.copyFile(
            Paths.get(PATH_TO_ASSET_CATALOG_BUILD_PHASE_SCRIPT),
            placedAssetCatalogBuildPhaseScript);
      }
      projectGenerated = true;
    } catch (UncheckedExecutionException e) {
      // if any code throws an exception, they tend to get wrapped in LoadingCache's
      // UncheckedExecutionException. Unwrap it if its cause is HumanReadable.
      UncheckedExecutionException originalException = e;
      while (e.getCause() instanceof UncheckedExecutionException) {
        e = (UncheckedExecutionException) e.getCause();
      }
      if (e.getCause() instanceof HumanReadableException) {
        throw (HumanReadableException) e.getCause();
      } else {
        throw originalException;
      }
    }
  }

  private void generateAggregateTarget(TargetNode<?> targetNode) {
    final BuildTarget buildTarget = targetNode.getBuildTarget();
    ImmutableMap<String, ImmutableMap<String, String>> configs =
        getAppleNativeNode(targetGraph, targetNode).get().getConstructorArg().configs.get();
    String productName = getXcodeTargetName(buildTarget) + "-Buck";

    PBXShellScriptBuildPhase shellScriptBuildPhase = new PBXShellScriptBuildPhase();
    ImmutableList<String> command = ImmutableList
        .<String>builder()
        .add("buck")
        .add("build")
        .addAll(Iterables.transform(buildWithBuckFlags, Escaper.BASH_ESCAPER))
        .add(Escaper.escapeAsBashString(buildTarget.getFullyQualifiedName()))
        .build();

    shellScriptBuildPhase.setShellScript(Joiner.on(' ').join(command));

    XCConfigurationList configurationList = new XCConfigurationList();
    PBXGroup group = project
        .getMainGroup()
        .getOrCreateDescendantGroupByPath(
            FluentIterable
                .from(buildTarget.getBasePath())
                .transform(Functions.toStringFunction())
                .toList())
        .getOrCreateChildGroupByName(getXcodeTargetName(buildTarget));
    for (String configurationName : configs.keySet()) {
      XCBuildConfiguration configuration = configurationList
          .getBuildConfigurationsByName()
          .getUnchecked(configurationName);
      configuration.setBaseConfigurationReference(
          getConfigurationFileReference(
              group,
              getConfigurationNameToXcconfigPath(buildTarget).apply(configurationName)));

      NSDictionary inlineSettings = new NSDictionary();
      inlineSettings.put("HEADER_SEARCH_PATHS", "");
      inlineSettings.put("LIBRARY_SEARCH_PATHS", "");
      inlineSettings.put("FRAMEWORK_SEARCH_PATHS", "");
      configuration.setBuildSettings(inlineSettings);
    }

    PBXAggregateTarget aggregateTarget = new PBXAggregateTarget(productName);
    aggregateTarget.setProductName(productName);
    aggregateTarget.getBuildPhases().add(shellScriptBuildPhase);
    aggregateTarget.setBuildConfigurationList(configurationList);
    project.getTargets().add(aggregateTarget);

    targetNodeToGeneratedProjectTargetBuilder.put(targetNode, aggregateTarget);
  }

  @SuppressWarnings("unchecked")
  private Optional<PBXTarget> generateProjectTarget(TargetNode<?> targetNode)
      throws IOException {
    Preconditions.checkState(
        isBuiltByCurrentProject(targetNode.getBuildTarget()),
        "should not generate rule if it shouldn't be built by current project");
    Optional<PBXTarget> result = Optional.absent();
    if (targetNode.getType().equals(AppleLibraryDescription.TYPE)) {
      result = Optional.<PBXTarget>of(
          generateAppleLibraryTarget(
              project,
              (TargetNode<AppleNativeTargetDescriptionArg>) targetNode,
              Optional.<TargetNode<AppleBundleDescription.Arg>>absent()));
    } else if (targetNode.getType().equals(AppleBinaryDescription.TYPE)) {
      result = Optional.<PBXTarget>of(
          generateAppleBinaryTarget(
              project,
              (TargetNode<AppleNativeTargetDescriptionArg>) targetNode));
    } else if (targetNode.getType().equals(AppleBundleDescription.TYPE)) {
      TargetNode<AppleBundleDescription.Arg> bundleTargetNode =
          (TargetNode<AppleBundleDescription.Arg>) targetNode;
      result = Optional.<PBXTarget>of(
          generateAppleBundleTarget(
              project,
              bundleTargetNode,
              (TargetNode<AppleNativeTargetDescriptionArg>) Preconditions.checkNotNull(
                  targetGraph.get(bundleTargetNode.getConstructorArg().binary)),
              Optional.<TargetNode<AppleBundleDescription.Arg>>absent()));
    } else if (targetNode.getType().equals(AppleTestDescription.TYPE)) {
      TargetNode<AppleTestDescription.Arg> testTargetNode =
          (TargetNode<AppleTestDescription.Arg>) targetNode;
      Optional<TargetNode<AppleBundleDescription.Arg>> testHostBundle;
      if (testTargetNode.getConstructorArg().testHostApp.isPresent()) {
        BuildTarget testHostBundleTarget =
            testTargetNode.getConstructorArg().testHostApp.get();
        TargetNode<?> testHostBundleNode = targetGraph.get(testHostBundleTarget);
        Preconditions.checkNotNull(testHostBundleNode);
        if (testHostBundleNode.getType() != AppleBundleDescription.TYPE) {
          throw new HumanReadableException(
              "The test host target '%s' has the wrong type (%s), must be apple_bundle",
              testHostBundleTarget,
              testHostBundleNode.getType());
        }
        testHostBundle = Optional.of((TargetNode<AppleBundleDescription.Arg>) testHostBundleNode);
      } else {
        testHostBundle = Optional.absent();
      }
      if (testsToGenerateAsStaticLibraries.contains(testTargetNode)) {
        result = Optional.<PBXTarget>of(
            generateAppleLibraryTarget(
                project,
                testTargetNode,
                testHostBundle));
      } else {
        result = Optional.<PBXTarget>of(
            generateAppleBundleTarget(
                project,
                testTargetNode,
                testTargetNode,
                testHostBundle));
      }
    } else if (targetNode.getType().equals(AppleResourceDescription.TYPE)) {
      // Check that the resource target node is referencing valid files or directories.
      // If a SourcePath is a BuildTargetSourcePath (or some hypothetical future implementation of
      // AbstractSourcePath), just assume it's the right type; we have no way of checking now as it
      // may not exist yet.
      TargetNode<AppleResourceDescription.Arg> resource =
          (TargetNode<AppleResourceDescription.Arg>) targetNode;
      AppleResourceDescription.Arg arg = resource.getConstructorArg();
      for (SourcePath dir : arg.dirs) {
        if (dir instanceof PathSourcePath &&
            !projectFilesystem.isDirectory(sourcePathResolver.apply(dir))) {
          throw new HumanReadableException(
              "%s specified in the dirs parameter of %s is not a directory",
              dir.toString(), resource.toString());
        }
      }
      for (SourcePath file : arg.files) {
        if (file instanceof PathSourcePath &&
            !projectFilesystem.isFile(sourcePathResolver.apply(file))) {
          throw new HumanReadableException(
              "%s specified in the files parameter of %s is not a regular file",
              file.toString(), resource.toString());
        }
      }
    }

    return result;
  }

  PBXNativeTarget generateAppleBundleTarget(
      PBXProject project,
      TargetNode<? extends HasAppleBundleFields> targetNode,
      TargetNode<? extends AppleNativeTargetDescriptionArg> binaryNode,
      Optional<TargetNode<AppleBundleDescription.Arg>> bundleLoaderNode)
      throws IOException {
    Optional<Path> infoPlistPath;
    if (targetNode.getConstructorArg().getInfoPlist().isPresent()) {
      infoPlistPath = Optional.of(
          Preconditions.checkNotNull(
              sourcePathResolver.apply(targetNode.getConstructorArg().getInfoPlist().get())));
    } else {
      infoPlistPath = Optional.absent();
    }

    PBXNativeTarget target = generateBinaryTarget(
        project,
        Optional.of(targetNode),
        binaryNode,
        bundleToTargetProductType(targetNode, binaryNode),
        "%s." + getExtensionString(targetNode.getConstructorArg().getExtension()),
        infoPlistPath,
        /* includeFrameworks */ true,
        AppleResources.collectRecursiveResources(targetGraph, ImmutableList.of(targetNode)),
        AppleBuildRules.collectRecursiveAssetCatalogs(targetGraph, ImmutableList.of(targetNode)),
        bundleLoaderNode);

    // -- copy any binary and bundle targets into this bundle
    Iterable<TargetNode<?>> copiedRules = AppleBuildRules.getRecursiveTargetNodeDependenciesOfTypes(
        targetGraph,
        AppleBuildRules.RecursiveDependenciesMode.COPYING,
        targetNode,
        Optional.of(AppleBuildRules.XCODE_TARGET_BUILD_RULE_TYPES));
    generateCopyFilesBuildPhases(target, copiedRules);

    LOG.debug("Generated iOS bundle target %s", target);
    return target;
  }

  private PBXNativeTarget generateAppleBinaryTarget(
      PBXProject project,
      TargetNode<AppleNativeTargetDescriptionArg> targetNode)
      throws IOException {
    PBXNativeTarget target = generateBinaryTarget(
        project,
        Optional.<TargetNode<AppleBundleDescription.Arg>>absent(),
        targetNode,
        ProductType.TOOL,
        "%s",
        Optional.<Path>absent(),
        /* includeFrameworks */ true,
        ImmutableSet.<AppleResourceDescription.Arg>of(),
        ImmutableSet.<AppleAssetCatalogDescription.Arg>of(),
        Optional.<TargetNode<AppleBundleDescription.Arg>>absent());
    LOG.debug("Generated Apple binary target %s", target);
    return target;
  }

  private PBXNativeTarget generateAppleLibraryTarget(
      PBXProject project,
      TargetNode<? extends AppleNativeTargetDescriptionArg> targetNode,
      Optional<TargetNode<AppleBundleDescription.Arg>> bundleLoaderNode)
      throws IOException {
    boolean isShared = targetNode
        .getBuildTarget()
        .getFlavors()
        .contains(CxxDescriptionEnhancer.SHARED_FLAVOR);
    ProductType productType = isShared ?
        ProductType.DYNAMIC_LIBRARY :
        ProductType.STATIC_LIBRARY;
    PBXNativeTarget target = generateBinaryTarget(
        project,
        Optional.<TargetNode<AppleBundleDescription.Arg>>absent(),
        targetNode,
        productType,
        AppleBuildRules.getOutputFileNameFormatForLibrary(isShared),
        Optional.<Path>absent(),
        /* includeFrameworks */ isShared,
        ImmutableSet.<AppleResourceDescription.Arg>of(),
        ImmutableSet.<AppleAssetCatalogDescription.Arg>of(),
        bundleLoaderNode);
    LOG.debug("Generated iOS library target %s", target);
    return target;
  }

  private PBXNativeTarget generateBinaryTarget(
      PBXProject project,
      Optional<? extends TargetNode<? extends HasAppleBundleFields>> bundle,
      TargetNode<? extends AppleNativeTargetDescriptionArg> targetNode,
      ProductType productType,
      String productOutputFormat,
      Optional<Path> infoPlistOptional,
      boolean includeFrameworks,
      ImmutableSet<AppleResourceDescription.Arg> resources,
      ImmutableSet<AppleAssetCatalogDescription.Arg> assetCatalogs,
      Optional<TargetNode<AppleBundleDescription.Arg>> bundleLoaderNode)
      throws IOException {
    Optional<String> targetGid = targetNode.getConstructorArg().gid;
    LOG.debug("Generating binary target for node %s (GID %s)", targetNode, targetGid);
    if (targetGid.isPresent()) {
      // Check if we have used this hardcoded GID before.
      // If not, remember it so we don't use it again.
      String thisTargetName = targetNode.getBuildTarget().getFullyQualifiedName();
      String conflictingTargetName = gidsToTargetNames.get(targetGid.get());
      if (conflictingTargetName != null) {
        throw new HumanReadableException(
            "Targets %s have the same hardcoded GID (%s)",
            ImmutableSortedSet.of(thisTargetName, conflictingTargetName),
            targetGid.get());
      }
      gidsToTargetNames.put(targetGid.get(), thisTargetName);
    }

    TargetNode<?> buildTargetNode = bundle.isPresent() ? bundle.get() : targetNode;
    final BuildTarget buildTarget = buildTargetNode.getBuildTarget();

    String productName = getProductName(buildTarget);
    AppleNativeTargetDescriptionArg arg = targetNode.getConstructorArg();
    NewNativeTargetProjectMutator mutator = new NewNativeTargetProjectMutator(
        pathRelativizer,
        sourcePathResolver);
    ImmutableSet<SourcePath> exportedHeaders =
        ImmutableSet.copyOf(getHeaderSourcePaths(arg.exportedHeaders));
    ImmutableSet<SourcePath> headers = ImmutableSet.copyOf(getHeaderSourcePaths(arg.headers));
    mutator
        .setTargetName(getXcodeTargetName(buildTarget))
        .setProduct(
            productType,
            productName,
            Paths.get(String.format(productOutputFormat, productName)))
        .setGid(targetGid)
        .setShouldGenerateCopyHeadersPhase(
            !targetNode.getConstructorArg().getUseBuckHeaderMaps())
        .setSourcesWithFlags(ImmutableSet.copyOf(arg.srcs.get()))
        .setExtraXcodeSources(ImmutableSet.copyOf(arg.extraXcodeSources.get()))
        .setPublicHeaders(exportedHeaders)
        .setPrivateHeaders(headers)
        .setPrefixHeader(arg.prefixHeader)
        .setResources(resources);

    if (options.contains(Option.CREATE_DIRECTORY_STRUCTURE)) {
      mutator.setTargetGroupPath(
          FluentIterable
              .from(buildTarget.getBasePath())
              .transform(Functions.toStringFunction())
              .toList());
    }

    if (!assetCatalogs.isEmpty()) {
      mutator.setAssetCatalogs(getAndMarkAssetCatalogBuildScript(), assetCatalogs);
    }

    if (includeFrameworks) {
      ImmutableSet.Builder<FrameworkPath> frameworksBuilder = ImmutableSet.builder();
      frameworksBuilder.addAll(targetNode.getConstructorArg().frameworks.get());
      frameworksBuilder.addAll(collectRecursiveFrameworkDependencies(ImmutableList.of(targetNode)));
      mutator.setFrameworks(frameworksBuilder.build());
      mutator.setArchives(
          collectRecursiveLibraryDependencies(ImmutableList.of(targetNode)));
    }

    // TODO(Task #3772930): Go through all dependencies of the rule
    // and add any shell script rules here
    ImmutableList.Builder<TargetNode<?>> preScriptPhases = ImmutableList.builder();
    ImmutableList.Builder<TargetNode<?>> postScriptPhases = ImmutableList.builder();
    if (bundle.isPresent() && targetNode != bundle.get()) {
      collectBuildScriptDependencies(
          targetGraph.getAll(bundle.get().getDeclaredDeps()),
          preScriptPhases,
          postScriptPhases);
    }
    collectBuildScriptDependencies(
        targetGraph.getAll(targetNode.getDeclaredDeps()),
        preScriptPhases,
        postScriptPhases);
    mutator.setPreBuildRunScriptPhases(preScriptPhases.build());
    mutator.setPostBuildRunScriptPhases(postScriptPhases.build());
    boolean skipRNBundle = ReactNativeFlavors.skipBundling(buildTargetNode.getBuildTarget());
    mutator.skipReactNativeBundle(skipRNBundle);

    if (skipRNBundle && reactNativeServer.isPresent()) {
      mutator.setAdditionalRunScripts(
          ImmutableList.of(projectFilesystem.resolve(reactNativeServer.get())));
    }

    NewNativeTargetProjectMutator.Result targetBuilderResult;
    try {
      targetBuilderResult = mutator.buildTargetAndAddToProject(project);
    } catch (NoSuchBuildTargetException e) {
      throw new HumanReadableException(e);
    }
    PBXGroup targetGroup = targetBuilderResult.targetGroup;

    SourceTreePath buckFilePath = new SourceTreePath(
        PBXReference.SourceTree.SOURCE_ROOT,
        pathRelativizer.outputPathToBuildTargetPath(buildTarget).resolve(buildFileName));
    PBXFileReference buckReference =
        targetGroup.getOrCreateFileReferenceBySourceTreePath(buckFilePath);
    buckReference.setExplicitFileType(Optional.of("text.script.python"));

    // -- configurations
    ImmutableMap.Builder<String, String> extraSettingsBuilder = ImmutableMap.builder();
    extraSettingsBuilder
        .put("TARGET_NAME", getProductName(buildTarget))
        .put("SRCROOT", pathRelativizer.outputPathToBuildTargetPath(buildTarget).toString());
    if (bundleLoaderNode.isPresent()) {
      TargetNode<AppleBundleDescription.Arg> bundleLoader = bundleLoaderNode.get();
      String bundleLoaderProductName = getProductName(bundleLoader.getBuildTarget());
      String bundleName = bundleLoaderProductName + "." +
          getExtensionString(bundleLoader.getConstructorArg().getExtension());
      String bundleLoaderOutputPath = Joiner.on('/').join(
          getTargetOutputPath(bundleLoader),
          bundleName,
          // TODO(user): How do we handle the "Contents" sub-directory for OS X app tests?
          bundleLoaderProductName);
      extraSettingsBuilder
          .put("BUNDLE_LOADER", bundleLoaderOutputPath)
          .put("TEST_HOST", "$(BUNDLE_LOADER)");
    }
    if (infoPlistOptional.isPresent()) {
      Path infoPlistPath = pathRelativizer.outputDirToRootRelative(infoPlistOptional.get());
      extraSettingsBuilder.put("INFOPLIST_FILE", infoPlistPath.toString());
    }
    Optional<SourcePath> prefixHeaderOptional = targetNode.getConstructorArg().prefixHeader;
    if (prefixHeaderOptional.isPresent()) {
        Path prefixHeaderRelative = sourcePathResolver.apply(prefixHeaderOptional.get());
        Path prefixHeaderPath = pathRelativizer.outputDirToRootRelative(prefixHeaderRelative);
        extraSettingsBuilder.put("GCC_PREFIX_HEADER", prefixHeaderPath.toString());
        extraSettingsBuilder.put("GCC_PRECOMPILE_PREFIX_HEADER", "YES");
    }
    if (targetNode.getConstructorArg().getUseBuckHeaderMaps()) {
      extraSettingsBuilder.put("USE_HEADERMAP", "NO");
    }

    ImmutableMap.Builder<String, String> defaultSettingsBuilder = ImmutableMap.builder();
    defaultSettingsBuilder.put(
        "REPO_ROOT",
        projectFilesystem.getRootPath().toAbsolutePath().normalize().toString());
    defaultSettingsBuilder.put("PRODUCT_NAME", getProductName(buildTarget));
    if (bundle.isPresent()) {
      defaultSettingsBuilder.put(
          "WRAPPER_EXTENSION",
          getExtensionString(bundle.get().getConstructorArg().getExtension()));
    }
    String publicHeadersPath =
        getHeaderOutputPath(buildTargetNode, targetNode.getConstructorArg().headerPathPrefix);
    LOG.debug("Public headers path for %s: %s", targetNode, publicHeadersPath);
    defaultSettingsBuilder.put("PUBLIC_HEADERS_FOLDER_PATH", publicHeadersPath);
    // We use BUILT_PRODUCTS_DIR as the root for the everything being built. Target-
    // specific output is placed within CONFIGURATION_BUILD_DIR, inside BUILT_PRODUCTS_DIR.
    // That allows Copy Files build phases to reference files in the CONFIGURATION_BUILD_DIR
    // of other targets by using paths relative to the target-independent BUILT_PRODUCTS_DIR.
    defaultSettingsBuilder.put(
        "BUILT_PRODUCTS_DIR",
        // $EFFECTIVE_PLATFORM_NAME starts with a dash, so this expands to something like:
        // $SYMROOT/Debug-iphonesimulator
        Joiner.on('/').join("$SYMROOT", "$CONFIGURATION$EFFECTIVE_PLATFORM_NAME"));
    defaultSettingsBuilder.put("CONFIGURATION_BUILD_DIR", "$BUILT_PRODUCTS_DIR");
    if (!bundle.isPresent() && targetNode.getType().equals(AppleLibraryDescription.TYPE)) {
      defaultSettingsBuilder.put("EXECUTABLE_PREFIX", "lib");
    }

    ImmutableMap.Builder<String, String> appendConfigsBuilder = ImmutableMap.builder();

    appendConfigsBuilder
        .put(
            "HEADER_SEARCH_PATHS",
            Joiner.on(' ').join(
                Iterables.concat(
                    collectRecursiveHeaderSearchPaths(targetNode),
                    collectRecursiveHeaderMaps(targetNode))))
        .put(
            "LIBRARY_SEARCH_PATHS",
            Joiner.on(' ').join(
                collectRecursiveLibrarySearchPaths(ImmutableSet.of(targetNode))))
        .put(
            "FRAMEWORK_SEARCH_PATHS",
            Joiner.on(' ').join(
                collectRecursiveFrameworkSearchPaths(ImmutableList.of(targetNode))))
        .put(
            "OTHER_CFLAGS",
            Joiner
                .on(' ')
                .join(
                    Iterables.concat(
                        targetNode.getConstructorArg().compilerFlags.get(),
                        targetNode.getConstructorArg().preprocessorFlags.get(),
                        collectRecursiveExportedPreprocessorFlags(ImmutableList.of(targetNode)))))
        .put(
            "OTHER_LDFLAGS",
            Joiner
                .on(' ')
                .join(
                    MoreIterables.zipAndConcat(
                        Iterables.cycle("-Xlinker"),
                        Iterables.concat(
                            targetNode.getConstructorArg().linkerFlags.get(),
                            collectRecursiveExportedLinkerFlags(ImmutableList.of(targetNode))))));

    ImmutableMap<CxxSource.Type, ImmutableList<String>> langPreprocessorFlags =
        targetNode.getConstructorArg().langPreprocessorFlags.get();

    Sets.SetView<CxxSource.Type> unsupportedLangPreprocessorFlags =
        Sets.difference(langPreprocessorFlags.keySet(), SUPPORTED_LANG_PREPROCESSOR_FLAG_TYPES);

    if (!unsupportedLangPreprocessorFlags.isEmpty()) {
      throw new HumanReadableException(
          "%s: Xcode project generation does not support specified lang_preprocessor_flags keys: " +
          "%s",
          buildTarget,
          unsupportedLangPreprocessorFlags);
    }

    ImmutableSet.Builder<String> allCxxFlagsBuilder = ImmutableSet.builder();
    ImmutableList<String> cxxFlags = langPreprocessorFlags.get(CxxSource.Type.CXX);
    if (cxxFlags != null) {
      allCxxFlagsBuilder.addAll(cxxFlags);
    }
    ImmutableList<String> objcxxFlags = langPreprocessorFlags.get(CxxSource.Type.OBJCXX);
    if (objcxxFlags != null) {
      allCxxFlagsBuilder.addAll(objcxxFlags);
    }
    ImmutableSet<String> allCxxFlags = allCxxFlagsBuilder.build();
    if (!allCxxFlags.isEmpty()) {
      appendConfigsBuilder.put(
          "OTHER_CPLUSPLUSFLAGS",
          Joiner.on(' ').join(allCxxFlags));
    }

    PBXNativeTarget target = targetBuilderResult.target;

    setTargetBuildConfigurations(
        getConfigurationNameToXcconfigPath(buildTarget),
        target,
        targetGroup,
        targetNode.getConstructorArg().configs.get(),
        extraSettingsBuilder.build(),
        defaultSettingsBuilder.build(),
        appendConfigsBuilder.build());

    // -- phases
    if (targetNode.getConstructorArg().getUseBuckHeaderMaps()) {
      Path headerPathPrefix =
          AppleDescriptions.getHeaderPathPrefix(arg, targetNode.getBuildTarget());
      createHeaderSymlinkTree(
          sourcePathResolver,
          AppleDescriptions.convertAppleHeadersToPublicCxxHeaders(
              sourcePathResolver,
              headerPathPrefix,
              arg),
          AppleDescriptions.getPathToHeaderSymlinkTree(targetNode, HeaderVisibility.PUBLIC).get());
      createHeaderSymlinkTree(
          sourcePathResolver,
          AppleDescriptions.convertAppleHeadersToPrivateCxxHeaders(
              sourcePathResolver,
              headerPathPrefix,
              arg),
          AppleDescriptions.getPathToHeaderSymlinkTree(targetNode, HeaderVisibility.PRIVATE).get());
    }

    // Use Core Data models from immediate dependencies only.
    addCoreDataModelBuildPhase(
        targetGroup,
        FluentIterable
            .from(targetNode.getDeps())
            .transform(
                new Function<BuildTarget, TargetNode<?>>() {
                  @Override
                  public TargetNode<?> apply(BuildTarget input) {
                    return Preconditions.checkNotNull(targetGraph.get(input));
                  }
                })
            .filter(
                new Predicate<TargetNode<?>>() {
                  @Override
                  public boolean apply(TargetNode<?> input) {
                    return CoreDataModelDescription.TYPE.equals(input.getType());
                  }
                })
            .transform(
                new Function<TargetNode<?>, CoreDataModelDescription.Arg>() {
                  @Override
                  public CoreDataModelDescription.Arg apply(TargetNode<?> input) {
                    return (CoreDataModelDescription.Arg) input.getConstructorArg();
                  }
                })
            .toSet());

    return target;
  }

  private Function<String, Path> getConfigurationNameToXcconfigPath(final BuildTarget buildTarget) {
    return new Function<String, Path>() {
      @Override
      public Path apply(String input) {
        return BuildTargets.getGenPath(buildTarget, "%s-" + input + ".xcconfig");
      }
    };
  }

  private Iterable<SourcePath> getHeaderSourcePaths(
      Optional<SourceList> headers) {
    if (!headers.isPresent()) {
      return ImmutableList.of();
    } else if (headers.get().getUnnamedSources().isPresent()) {
      return headers.get().getUnnamedSources().get();
    } else {
      return headers.get().getNamedSources().get().values();
    }
  }

  private void generateCombinedTestTarget(
      final String productName,
      AppleTestBundleParamsKey key,
      ImmutableCollection<TargetNode<AppleTestDescription.Arg>> tests)
      throws IOException {
    ImmutableSet.Builder<PBXFileReference> testLibs = ImmutableSet.builder();
    for (TargetNode<AppleTestDescription.Arg> test : tests) {
      testLibs.add(getOrCreateTestLibraryFileReference(test));
    }
    NewNativeTargetProjectMutator mutator = new NewNativeTargetProjectMutator(
        pathRelativizer,
        sourcePathResolver)
        .setTargetName(productName)
        .setProduct(
            dylibProductTypeByBundleExtension(key.getExtension().getLeft()).get(),
            productName,
            Paths.get(productName + "." + getExtensionString(key.getExtension())))
        .setShouldGenerateCopyHeadersPhase(false)
        .setSourcesWithFlags(
            ImmutableSet.of(
                SourceWithFlags.of(
                    new PathSourcePath(projectFilesystem, emptyFileWithExtension("c")))))
        .setArchives(Sets.union(collectRecursiveLibraryDependencies(tests), testLibs.build()))
        .setResources(AppleResources.collectRecursiveResources(targetGraph, tests))
        .setAssetCatalogs(
            getAndMarkAssetCatalogBuildScript(),
            AppleBuildRules.collectRecursiveAssetCatalogs(targetGraph, tests));

    ImmutableSet.Builder<FrameworkPath> frameworksBuilder = ImmutableSet.builder();
    frameworksBuilder.addAll(collectRecursiveFrameworkDependencies(tests));
    for (TargetNode<AppleTestDescription.Arg> test : tests) {
      frameworksBuilder.addAll(test.getConstructorArg().frameworks.get());
    }
    mutator.setFrameworks(frameworksBuilder.build());

    NewNativeTargetProjectMutator.Result result;
    try {
      result = mutator.buildTargetAndAddToProject(project);
    } catch (NoSuchBuildTargetException e) {
      throw new HumanReadableException(e);
    }

    ImmutableMap.Builder<String, String> overrideBuildSettingsBuilder =
        ImmutableMap.<String, String>builder()
            .put("GCC_PREFIX_HEADER", "")
            .put("USE_HEADERMAP", "NO");
    if (key.getInfoPlist().isPresent()) {
      overrideBuildSettingsBuilder.put(
          "INFOPLIST_FILE",
          pathRelativizer.outputDirToRootRelative(
                sourcePathResolver.apply(key.getInfoPlist().get())).toString());
    }
    setTargetBuildConfigurations(
        new Function<String, Path>() {
          @Override
          public Path apply(String input) {
            return outputDirectory.resolve(
                String.format("xcconfigs/%s-%s.xcconfig", productName, input));
          }
        },
        result.target,
        result.targetGroup,
        key.getConfigs().get(),
        overrideBuildSettingsBuilder.build(),
        ImmutableMap.of(
            "PRODUCT_NAME", productName,
            "WRAPPER_EXTENSION", getExtensionString(key.getExtension())),
        ImmutableMap.of(
            "FRAMEWORK_SEARCH_PATHS",
            Joiner.on(' ').join(collectRecursiveFrameworkSearchPaths(tests)),
            "LIBRARY_SEARCH_PATHS",
            Joiner.on(' ').join(collectRecursiveLibrarySearchPaths(tests)),
            "OTHER_LDFLAGS",
            Joiner.on(' ').join(
                MoreIterables.zipAndConcat(
                    Iterables.cycle("-Xlinker"),
                    Iterables.concat(
                        key.getLinkerFlags(),
                        collectRecursiveExportedLinkerFlags(tests))))));
    buildableCombinedTestTargets.add(result.target);
  }

  private String deriveCombinedTestTargetNameFromKey(
      AppleTestBundleParamsKey key,
      int combinedTestIndex) {
    return Joiner.on("-").join(
        "_BuckCombinedTest",
        getExtensionString(key.getExtension()),
        combinedTestIndex);

  }

  /**
   * Create target level configuration entries.
   *
   * @param target      Xcode target for which the configurations will be set.
   * @param targetGroup Xcode group in which the configuration file references will be placed.
   * @param configurations  Configurations as extracted from the BUCK file.
   * @param overrideBuildSettings Build settings that will override ones defined elsewhere.
   * @param defaultBuildSettings  Target-inline level build settings that will be set if not already
   *                              defined.
   * @param appendBuildSettings   Target-inline level build settings that will incorporate the
   *                              existing value or values at a higher level.
   */
  private void setTargetBuildConfigurations(
      Function<String, Path> configurationNameToXcconfigPath,
      PBXTarget target,
      PBXGroup targetGroup,
      ImmutableMap<String, ImmutableMap<String, String>> configurations,
      ImmutableMap<String, String> overrideBuildSettings,
      ImmutableMap<String, String> defaultBuildSettings,
      ImmutableMap<String, String> appendBuildSettings)
      throws IOException {

    for (Map.Entry<String, ImmutableMap<String, String>> configurationEntry :
        configurations.entrySet()) {
      targetConfigNamesBuilder.add(configurationEntry.getKey());

      ImmutableMap<String, String> targetLevelInlineSettings =
          configurationEntry.getValue();

      XCBuildConfiguration outputConfiguration = target
          .getBuildConfigurationList()
          .getBuildConfigurationsByName()
          .getUnchecked(configurationEntry.getKey());

      HashMap<String, String> combinedOverrideConfigs = Maps.newHashMap(overrideBuildSettings);
      for (Map.Entry<String, String> entry: defaultBuildSettings.entrySet()) {
        String existingSetting = targetLevelInlineSettings.get(entry.getKey());
        if (existingSetting == null) {
          combinedOverrideConfigs.put(entry.getKey(), entry.getValue());
        }
      }

      for (Map.Entry<String, String> entry : appendBuildSettings.entrySet()) {
        String existingSetting = targetLevelInlineSettings.get(entry.getKey());
        String settingPrefix = existingSetting != null ? existingSetting : "$(inherited)";
        combinedOverrideConfigs.put(entry.getKey(), settingPrefix + " " + entry.getValue());
      }

      Iterable<Map.Entry<String, String>> entries = Iterables.concat(
          targetLevelInlineSettings.entrySet(),
          combinedOverrideConfigs.entrySet());

      Path xcconfigPath = configurationNameToXcconfigPath.apply(configurationEntry.getKey());
      projectFilesystem.mkdirs(Preconditions.checkNotNull(xcconfigPath).getParent());

      StringBuilder stringBuilder = new StringBuilder();
      for (Map.Entry<String, String> entry : entries) {
        stringBuilder.append(entry.getKey());
        stringBuilder.append(" = ");
        stringBuilder.append(entry.getValue());
        stringBuilder.append('\n');
      }
      String xcconfigContents = stringBuilder.toString();

      if (MorePaths.fileContentsDiffer(
          new ByteArrayInputStream(xcconfigContents.getBytes(Charsets.UTF_8)),
          xcconfigPath,
          projectFilesystem)) {
        if (shouldGenerateReadOnlyFiles()) {
          projectFilesystem.writeContentsToPath(
              xcconfigContents,
              xcconfigPath,
              READ_ONLY_FILE_ATTRIBUTE);
        } else {
          projectFilesystem.writeContentsToPath(
              xcconfigContents,
              xcconfigPath);
        }
      }

      PBXFileReference fileReference = getConfigurationFileReference(targetGroup, xcconfigPath);
      outputConfiguration.setBaseConfigurationReference(fileReference);
    }
  }

  private PBXFileReference getConfigurationFileReference(PBXGroup targetGroup, Path xcconfigPath) {
    return targetGroup
        .getOrCreateChildGroupByName("Configurations")
        .getOrCreateFileReferenceBySourceTreePath(
            new SourceTreePath(
                PBXReference.SourceTree.SOURCE_ROOT,
                pathRelativizer.outputDirToRootRelative(xcconfigPath)));
  }

  private void collectBuildScriptDependencies(
      Iterable<TargetNode<?>> targetNodes,
      ImmutableList.Builder<TargetNode<?>> preRules,
      ImmutableList.Builder<TargetNode<?>> postRules) {
    for (TargetNode<?> targetNode : targetNodes) {
      BuildRuleType type = targetNode.getType();
      if (type.equals(XcodePostbuildScriptDescription.TYPE) ||
          type.equals(IosReactNativeLibraryDescription.TYPE)) {
        postRules.add(targetNode);
      } else if (
          type.equals(XcodePrebuildScriptDescription.TYPE) ||
          type.equals(GenruleDescription.TYPE)) {
        preRules.add(targetNode);
      }
    }
  }

  private void createHeaderSymlinkTree(
      Function<SourcePath, Path> pathResolver,
      Map<String, SourcePath> contents,
      Path headerSymlinkTreeRoot) throws IOException {
    LOG.verbose(
        "Building header symlink tree at %s with contents %s",
        headerSymlinkTreeRoot,
        contents);
    ImmutableSortedMap.Builder<Path, Path> resolvedContentsBuilder =
        ImmutableSortedMap.naturalOrder();
    for (Map.Entry<String, SourcePath> entry : contents.entrySet()) {
      Path link = headerSymlinkTreeRoot.resolve(entry.getKey());
      Path existing = projectFilesystem.resolve(pathResolver.apply(entry.getValue()));
      resolvedContentsBuilder.put(link, existing);
    }
    ImmutableSortedMap<Path, Path> resolvedContents = resolvedContentsBuilder.build();

    Path headerMapLocation = getHeaderMapLocationFromSymlinkTreeRoot(headerSymlinkTreeRoot);

    Path hashCodeFilePath = headerSymlinkTreeRoot.resolve(".contents-hash");
    Optional<String> currentHashCode = projectFilesystem.readFileIfItExists(hashCodeFilePath);
    String newHashCode = getHeaderSymlinkTreeHashCode(resolvedContents).toString();
    if (Optional.of(newHashCode).equals(currentHashCode)) {
      LOG.debug(
          "Symlink tree at %s is up to date, not regenerating (key %s).",
          headerSymlinkTreeRoot,
          newHashCode);
    } else {
      LOG.debug(
          "Updating symlink tree at %s (old key %s, new key %s).",
          headerSymlinkTreeRoot,
          currentHashCode,
          newHashCode);
      projectFilesystem.deleteRecursivelyIfExists(headerSymlinkTreeRoot);
      projectFilesystem.mkdirs(headerSymlinkTreeRoot);
      for (Map.Entry<Path, Path> entry : resolvedContents.entrySet()) {
        Path link = entry.getKey();
        Path existing = entry.getValue();
        projectFilesystem.createParentDirs(link);
        projectFilesystem.createSymLink(link, existing, /* force */ false);
      }
      projectFilesystem.writeContentsToPath(newHashCode, hashCodeFilePath);

      HeaderMap.Builder headerMapBuilder = new HeaderMap.Builder();
      for (Map.Entry<String, SourcePath> entry : contents.entrySet()) {
        headerMapBuilder.add(
            entry.getKey(),
            projectFilesystem.resolve(headerSymlinkTreeRoot).resolve(entry.getKey()));
      }
      projectFilesystem.writeBytesToPath(headerMapBuilder.build().getBytes(), headerMapLocation);
    }
    headerSymlinkTrees.add(headerSymlinkTreeRoot);
  }

  private HashCode getHeaderSymlinkTreeHashCode(ImmutableSortedMap<Path, Path> contents) {
    Hasher hasher = Hashing.sha1().newHasher();
    hasher.putBytes(BuckVersion.getVersion().getBytes(Charsets.UTF_8));
    for (Map.Entry<Path, Path> entry : contents.entrySet()) {
      byte[] key = entry.getKey().toString().getBytes(Charsets.UTF_8);
      byte[] value = entry.getValue().toString().getBytes(Charsets.UTF_8);
      hasher.putInt(key.length);
      hasher.putBytes(key);
      hasher.putInt(value.length);
      hasher.putBytes(value);
    }
    return hasher.hash();
  }

  private void addCoreDataModelBuildPhase(
      PBXGroup targetGroup,
      Iterable<CoreDataModelDescription.Arg> dataModels) throws IOException {
    // TODO(user): actually add a build phase

    for (final CoreDataModelDescription.Arg dataModel : dataModels) {
      // Core data models go in the resources group also.
      PBXGroup resourcesGroup = targetGroup.getOrCreateChildGroupByName("Resources");

      if (CoreDataModelDescription.isVersionedDataModel(dataModel)) {
        // It's safe to do I/O here to figure out the current version because we're returning all
        // the versions and the file pointing to the current version from
        // getInputsToCompareToOutput(), so the rule will be correctly detected as stale if any of
        // them change.
        final String currentVersionFileName = ".xccurrentversion";
        final String currentVersionKey = "_XCCurrentVersionName";

        final XCVersionGroup versionGroup =
            resourcesGroup.getOrCreateChildVersionGroupsBySourceTreePath(
                new SourceTreePath(
                    PBXReference.SourceTree.SOURCE_ROOT,
                    pathRelativizer.outputDirToRootRelative(dataModel.path)));

        projectFilesystem.walkRelativeFileTree(
            dataModel.path,
            new SimpleFileVisitor<Path>() {
              @Override
              public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) {
                if (dir.equals(dataModel.path)) {
                  return FileVisitResult.CONTINUE;
                }
                versionGroup.getOrCreateFileReferenceBySourceTreePath(
                    new SourceTreePath(
                        PBXReference.SourceTree.SOURCE_ROOT,
                        pathRelativizer.outputDirToRootRelative(dir)));
                return FileVisitResult.SKIP_SUBTREE;
              }
            });

        Path currentVersionPath = dataModel.path.resolve(currentVersionFileName);
        try (InputStream in = projectFilesystem.newFileInputStream(currentVersionPath)) {
          NSObject rootObject;
          try {
            rootObject = PropertyListParser.parse(in);
          } catch (IOException e) {
            throw e;
          } catch (Exception e) {
            rootObject = null;
          }
          if (!(rootObject instanceof NSDictionary)) {
            throw new HumanReadableException("Malformed %s file.", currentVersionFileName);
          }
          NSDictionary rootDictionary = (NSDictionary) rootObject;
          NSObject currentVersionName = rootDictionary.objectForKey(currentVersionKey);
          if (!(currentVersionName instanceof NSString)) {
            throw new HumanReadableException("Malformed %s file.", currentVersionFileName);
          }
          PBXFileReference ref = versionGroup.getOrCreateFileReferenceBySourceTreePath(
              new SourceTreePath(
                  PBXReference.SourceTree.SOURCE_ROOT,
                  pathRelativizer.outputDirToRootRelative(
                      dataModel.path.resolve(currentVersionName.toString()))));
          versionGroup.setCurrentVersion(Optional.of(ref));
        } catch (NoSuchFileException e) {
          if (versionGroup.getChildren().size() == 1) {
            versionGroup.setCurrentVersion(Optional.of(Iterables.get(
                        versionGroup.getChildren(),
                        0)));
          }
        }
      } else {
        resourcesGroup.getOrCreateFileReferenceBySourceTreePath(
            new SourceTreePath(
                PBXReference.SourceTree.SOURCE_ROOT,
                pathRelativizer.outputDirToRootRelative(dataModel.path)));
      }
    }
  }

  private Optional<PBXCopyFilesBuildPhase.Destination> getDestination(TargetNode<?> targetNode) {
    if (targetNode.getType().equals(AppleBundleDescription.TYPE)) {
      AppleBundleDescription.Arg arg = (AppleBundleDescription.Arg) targetNode.getConstructorArg();
      AppleBundleExtension extension = arg.extension.isLeft() ?
          arg.extension.getLeft() :
          AppleBundleExtension.BUNDLE;
      switch (extension) {
        case FRAMEWORK:
          return Optional.of(PBXCopyFilesBuildPhase.Destination.FRAMEWORKS);
        case APPEX:
        case PLUGIN:
          return Optional.of(PBXCopyFilesBuildPhase.Destination.PLUGINS);
        case APP:
          return Optional.of(PBXCopyFilesBuildPhase.Destination.EXECUTABLES);
        //$CASES-OMITTED$
      default:
          return Optional.of(PBXCopyFilesBuildPhase.Destination.PRODUCTS);
      }
    } else if (targetNode.getType().equals(AppleLibraryDescription.TYPE)) {
      if (targetNode
          .getBuildTarget()
          .getFlavors()
          .contains(CxxDescriptionEnhancer.SHARED_FLAVOR)) {
        return Optional.of(PBXCopyFilesBuildPhase.Destination.FRAMEWORKS);
      } else {
        return Optional.absent();
      }
    } else if (targetNode.getType().equals(AppleBinaryDescription.TYPE)) {
      return Optional.of(PBXCopyFilesBuildPhase.Destination.EXECUTABLES);
    } else {
      throw new RuntimeException("Unexpected type: " + targetNode.getType());
    }
  }

  private void generateCopyFilesBuildPhases(
      PBXNativeTarget target,
      Iterable<TargetNode<?>> copiedNodes) {

    // Bucket build rules into bins by their destinations
    ImmutableSetMultimap.Builder<PBXCopyFilesBuildPhase.Destination, TargetNode<?>>
        ruleByDestinationBuilder = ImmutableSetMultimap.builder();
    for (TargetNode<?> copiedNode : copiedNodes) {
      Optional<PBXCopyFilesBuildPhase.Destination> optionalDestination =
          getDestination(copiedNode);
      if (optionalDestination.isPresent()) {
        ruleByDestinationBuilder.put(optionalDestination.get(), copiedNode);
      }
    }
    ImmutableSetMultimap<PBXCopyFilesBuildPhase.Destination, TargetNode<?>> ruleByDestination =
        ruleByDestinationBuilder.build();

    // Emit a copy files phase for each destination.
    for (PBXCopyFilesBuildPhase.Destination destination : ruleByDestination.keySet()) {
      PBXCopyFilesBuildPhase copyFilesBuildPhase = new PBXCopyFilesBuildPhase(destination, "");
      target.getBuildPhases().add(copyFilesBuildPhase);
      for (TargetNode<?> targetNode : ruleByDestination.get(destination)) {
        PBXFileReference fileReference = getLibraryFileReference(targetNode);
        copyFilesBuildPhase.getFiles().add(new PBXBuildFile(fileReference));
      }
    }
  }

  /**
   * Create the project bundle structure and write {@code project.pbxproj}.
   */
  private Path writeProjectFile(PBXProject project) throws IOException {
    XcodeprojSerializer serializer = new XcodeprojSerializer(
        new GidGenerator(ImmutableSet.copyOf(gidsToTargetNames.keySet())),
        project);
    NSDictionary rootObject = serializer.toPlist();
    Path xcodeprojDir = outputDirectory.resolve(projectName + ".xcodeproj");
    projectFilesystem.mkdirs(xcodeprojDir);
    Path serializedProject = xcodeprojDir.resolve("project.pbxproj");
    String contentsToWrite = rootObject.toXMLPropertyList();
    // Before we write any files, check if the file contents have changed.
    if (MorePaths.fileContentsDiffer(
            new ByteArrayInputStream(contentsToWrite.getBytes(Charsets.UTF_8)),
            serializedProject,
            projectFilesystem)) {
      LOG.debug("Regenerating project at %s", serializedProject);
      if (shouldGenerateReadOnlyFiles()) {
        projectFilesystem.writeContentsToPath(
            contentsToWrite,
            serializedProject,
            READ_ONLY_FILE_ATTRIBUTE);
      } else {
        projectFilesystem.writeContentsToPath(
            contentsToWrite,
            serializedProject);
      }
    } else {
      LOG.debug("Not regenerating project at %s (contents have not changed)", serializedProject);
    }
    return xcodeprojDir;
  }

  private static String getProductName(BuildTarget buildTarget) {
    return buildTarget.getShortName();
  }

  private String getHeaderOutputPath(
      TargetNode<?> buildTargetNode,
      Optional<String> headerPathPrefix) {
    // This is automatically appended to $CONFIGURATION_BUILD_DIR.
    return Joiner.on('/').join(
        getBuiltProductsRelativeTargetOutputPath(buildTargetNode),
        "Headers",
        headerPathPrefix.or("$TARGET_NAME"));
  }

  /**
   * @param targetNode Must have a header symlink tree or an exception will be thrown.
   */
  private Path getHeaderSymlinkTreeRelativePath(
      TargetNode<? extends AppleNativeTargetDescriptionArg> targetNode,
      HeaderVisibility headerVisibility) {
    Optional<Path> treeRoot = AppleDescriptions.getPathToHeaderSymlinkTree(
        targetNode,
        headerVisibility);
    Preconditions.checkState(
        treeRoot.isPresent(),
        "%s does not have a header symlink tree.",
        targetNode);
    return pathRelativizer.outputDirToRootRelative(treeRoot.get());
  }

  private Path getHeaderMapLocationFromSymlinkTreeRoot(Path headerSymlinkTreeRoot) {
    return headerSymlinkTreeRoot.resolve(".tree.hmap");
  }

  private String getHeaderSearchPath(TargetNode<?> targetNode) {
    return Joiner.on('/').join(
        getTargetOutputPath(targetNode),
        "Headers");
  }

  private String getBuiltProductsRelativeTargetOutputPath(TargetNode<?> targetNode) {
    if (targetNode.getType().equals(AppleBinaryDescription.TYPE) ||
        targetNode.getType().equals(AppleTestDescription.TYPE) ||
        (targetNode.getType().equals(AppleBundleDescription.TYPE) &&
            !isFrameworkBundle((AppleBundleDescription.Arg) targetNode.getConstructorArg()))) {
      // TODO(grp): These should be inside the path below. Right now, that causes issues with
      // bundle loader paths hardcoded in .xcconfig files that don't expect the full target path.
      // It also causes issues where Xcode doesn't know where to look for a final .app to run it.
      return ".";
    } else {
      return BaseEncoding
          .base32()
          .omitPadding()
          .encode(targetNode.getBuildTarget().getFullyQualifiedName().getBytes());
    }
  }

  private String getTargetOutputPath(TargetNode<?> targetNode) {
    return Joiner.on('/').join(
        "$BUILT_PRODUCTS_DIR",
        getBuiltProductsRelativeTargetOutputPath(targetNode));
  }

  @SuppressWarnings("unchecked")
  private static Optional<TargetNode<AppleNativeTargetDescriptionArg>> getAppleNativeNodeOfType(
      TargetGraph targetGraph,
      TargetNode<?> targetNode,
      Set<BuildRuleType> nodeTypes,
      Set<AppleBundleExtension> bundleExtensions) {
    Optional<TargetNode<AppleNativeTargetDescriptionArg>> nativeNode = Optional.absent();
    if (nodeTypes.contains(targetNode.getType())) {
      nativeNode = Optional.of((TargetNode<AppleNativeTargetDescriptionArg>) targetNode);
    } else if (targetNode.getType().equals(AppleBundleDescription.TYPE)) {
      TargetNode<AppleBundleDescription.Arg> bundle =
          (TargetNode<AppleBundleDescription.Arg>) targetNode;
      Either<AppleBundleExtension, String> extension = bundle.getConstructorArg().getExtension();
      if (extension.isLeft() && bundleExtensions.contains(extension.getLeft())) {
        nativeNode = Optional.of(
            Preconditions.checkNotNull(
                (TargetNode<AppleNativeTargetDescriptionArg>) targetGraph.get(
                    bundle.getConstructorArg().binary)));
      }
    }
    return nativeNode;
  }

  private static Optional<TargetNode<AppleNativeTargetDescriptionArg>> getAppleNativeNode(
      TargetGraph targetGraph,
      TargetNode<?> targetNode) {
    return getAppleNativeNodeOfType(
        targetGraph,
        targetNode,
        ImmutableSet.of(
            AppleBinaryDescription.TYPE,
            AppleLibraryDescription.TYPE),
        ImmutableSet.of(
            AppleBundleExtension.APP,
            AppleBundleExtension.FRAMEWORK));
  }

  private static Optional<TargetNode<AppleNativeTargetDescriptionArg>> getLibraryNode(
      TargetGraph targetGraph,
      TargetNode<?> targetNode) {
    return getAppleNativeNodeOfType(
        targetGraph,
        targetNode,
        ImmutableSet.of(
            AppleLibraryDescription.TYPE),
        ImmutableSet.of(
            AppleBundleExtension.FRAMEWORK));
  }

  private ImmutableSet<String> collectRecursiveHeaderSearchPaths(
      TargetNode<? extends AppleNativeTargetDescriptionArg> targetNode) {
    LOG.debug("Collecting recursive header search paths for %s...", targetNode);
    return FluentIterable
        .from(
            AppleBuildRules.getRecursiveTargetNodeDependenciesOfTypes(
                targetGraph,
                AppleBuildRules.RecursiveDependenciesMode.BUILDING,
                targetNode,
                Optional.of(AppleBuildRules.XCODE_TARGET_BUILD_RULE_TYPES)))
        .filter(
            new Predicate<TargetNode<?>>() {
              @Override
              public boolean apply(TargetNode<?> input) {
                Optional<TargetNode<AppleNativeTargetDescriptionArg>> nativeNode =
                    getAppleNativeNode(targetGraph, input);
                return nativeNode.isPresent() &&
                    !nativeNode.get().getConstructorArg().getUseBuckHeaderMaps();
              }
            })
        .transform(
            new Function<TargetNode<?>, String>() {
              @Override
              public String apply(TargetNode<?> input) {
                String result = getHeaderSearchPath(input);
                LOG.debug("Header search path for %s: %s", input, result);
                return result;
              }
            })
        .toSet();
  }

  private ImmutableSet<Path> collectRecursiveHeaderMaps(
      TargetNode<? extends AppleNativeTargetDescriptionArg> targetNode) {
    ImmutableSet.Builder<Path> builder = ImmutableSet.builder();

    for (Path headerSymlinkTreePath : collectRecursiveHeaderSymlinkTrees(targetNode)) {
      builder.add(getHeaderMapLocationFromSymlinkTreeRoot(headerSymlinkTreePath));
    }

    return builder.build();
  }

  private ImmutableSet<Path> collectRecursiveHeaderSymlinkTrees(
      TargetNode<? extends AppleNativeTargetDescriptionArg> targetNode) {
    ImmutableSet.Builder<Path> builder = ImmutableSet.builder();

    if (targetNode.getConstructorArg().getUseBuckHeaderMaps()) {
      builder.add(getHeaderSymlinkTreeRelativePath(targetNode, HeaderVisibility.PRIVATE));
      builder.add(getHeaderSymlinkTreeRelativePath(targetNode, HeaderVisibility.PUBLIC));
    }

    for (TargetNode<?> input :
        AppleBuildRules.getRecursiveTargetNodeDependenciesOfTypes(
            targetGraph,
            AppleBuildRules.RecursiveDependenciesMode.BUILDING,
            targetNode,
            Optional.of(AppleBuildRules.XCODE_TARGET_BUILD_RULE_TYPES))) {
      Optional<TargetNode<AppleNativeTargetDescriptionArg>> nativeNode =
          getAppleNativeNode(targetGraph, input);
      if (nativeNode.isPresent() && nativeNode.get().getConstructorArg().getUseBuckHeaderMaps()) {
        builder.add(
            getHeaderSymlinkTreeRelativePath(
                nativeNode.get(),
                HeaderVisibility.PUBLIC));
      }
    }

    addHeaderSymlinkTreesForSourceUnderTest(targetNode, builder, HeaderVisibility.PRIVATE);

    return builder.build();
  }

  private void addHeaderSymlinkTreesForSourceUnderTest(
      TargetNode<? extends AppleNativeTargetDescriptionArg> targetNode,
      ImmutableSet.Builder<Path> headerSymlinkTreesBuilder,
      HeaderVisibility headerVisibility) {
    ImmutableSet<TargetNode<?>> directDependencies = ImmutableSet.copyOf(
        targetGraph.getAll(targetNode.getDeps()));
    for (TargetNode<?> dependency : directDependencies) {
      Optional<TargetNode<AppleNativeTargetDescriptionArg>> nativeNode =
          getAppleNativeNode(targetGraph, dependency);
      if (nativeNode.isPresent() &&
          isSourceUnderTest(dependency, nativeNode.get(), targetNode) &&
          nativeNode.get().getConstructorArg().getUseBuckHeaderMaps()) {
        headerSymlinkTreesBuilder.add(
            getHeaderSymlinkTreeRelativePath(
                nativeNode.get(),
                headerVisibility));
      }
    }
  }

  private boolean isSourceUnderTest(
      TargetNode<?> dependencyNode,
      TargetNode<AppleNativeTargetDescriptionArg> nativeNode,
      TargetNode<?> testNode) {
    boolean isSourceUnderTest =
        nativeNode.getConstructorArg().getTests().contains(testNode.getBuildTarget());

    if (dependencyNode != nativeNode && dependencyNode.getConstructorArg() instanceof HasTests) {
      ImmutableSortedSet<BuildTarget> tests =
          ((HasTests) dependencyNode.getConstructorArg()).getTests();
      if (tests.contains(testNode.getBuildTarget())) {
        isSourceUnderTest = true;
      }
    }

    return isSourceUnderTest;
  }

  private <T> ImmutableSet<String> collectRecursiveLibrarySearchPaths(
      Iterable<TargetNode<T>> targetNodes) {
    return new ImmutableSet.Builder<String>()
        .add("$BUILT_PRODUCTS_DIR")
        .addAll(
            collectRecursiveSearchPathsForFrameworkPaths(
                targetNodes,
                FrameworkPath.FrameworkType.LIBRARY))
        .build();
  }

  private <T> ImmutableSet<String> collectRecursiveFrameworkSearchPaths(
      Iterable<TargetNode<T>> targetNodes) {
    return new ImmutableSet.Builder<String>()
        .add("$BUILT_PRODUCTS_DIR")
        .addAll(
            collectRecursiveSearchPathsForFrameworkPaths(
                targetNodes,
                FrameworkPath.FrameworkType.FRAMEWORK))
        .build();
  }

  private <T> Iterable<FrameworkPath> collectRecursiveFrameworkDependencies(
      Iterable<TargetNode<T>> targetNodes) {
    return FluentIterable
        .from(targetNodes)
        .transformAndConcat(
            AppleBuildRules.newRecursiveRuleDependencyTransformer(
                targetGraph,
                AppleBuildRules.RecursiveDependenciesMode.LINKING,
                AppleBuildRules.XCODE_TARGET_BUILD_RULE_TYPES))
        .transformAndConcat(
            new Function<TargetNode<?>, Iterable<FrameworkPath>>() {
              @Override
              public Iterable<FrameworkPath> apply(TargetNode<?> input) {
                Optional<TargetNode<AppleNativeTargetDescriptionArg>> library =
                    getLibraryNode(targetGraph, input);
                if (library.isPresent() &&
                    !AppleLibraryDescription.isSharedLibraryTarget(
                        library.get().getBuildTarget())) {
                  return library.get().getConstructorArg().frameworks.get();
                } else {
                  return ImmutableList.of();
                }
              }
            });
  }

  private <T> Iterable<String> collectRecursiveSearchPathsForFrameworkPaths(
      Iterable<TargetNode<T>> targetNodes,
      final FrameworkPath.FrameworkType type) {
    return FluentIterable
        .from(targetNodes)
        .transformAndConcat(
            AppleBuildRules.newRecursiveRuleDependencyTransformer(
                targetGraph,
                AppleBuildRules.RecursiveDependenciesMode.LINKING,
                ImmutableSet.of(AppleLibraryDescription.TYPE)))
        .append(targetNodes)
        .transformAndConcat(
            new Function<TargetNode<?>, Iterable<String>>() {
              @Override
              public Iterable<String> apply(TargetNode<?> input) {
                return input
                    .castArg(AppleNativeTargetDescriptionArg.class)
                    .transform(getTargetFrameworkSearchPaths(type))
                    .or(ImmutableSet.<String>of());
              }
            });
  }

  private <T> Iterable<String> collectRecursiveExportedPreprocessorFlags(
      Iterable<TargetNode<T>> targetNodes) {
    return FluentIterable
        .from(targetNodes)
        .transformAndConcat(
            AppleBuildRules.newRecursiveRuleDependencyTransformer(
                targetGraph,
                AppleBuildRules.RecursiveDependenciesMode.BUILDING,
                ImmutableSet.of(AppleLibraryDescription.TYPE)))
        .append(targetNodes)
        .transformAndConcat(
            new Function<TargetNode<?>, Iterable<? extends String>>() {
              @Override
              public Iterable<? extends String> apply(TargetNode<?> input) {
                return input
                    .castArg(AppleNativeTargetDescriptionArg.class)
                    .transform(GET_EXPORTED_PREPROCESSOR_FLAGS)
                    .or(ImmutableSet.<String>of());
              }
            });
  }

  private <T> Iterable<String> collectRecursiveExportedLinkerFlags(
      Iterable<TargetNode<T>> targetNodes) {
    return FluentIterable
        .from(targetNodes)
        .transformAndConcat(
            AppleBuildRules.newRecursiveRuleDependencyTransformer(
                targetGraph,
                AppleBuildRules.RecursiveDependenciesMode.LINKING,
                ImmutableSet.of(AppleLibraryDescription.TYPE)))
        .append(targetNodes)
        .transformAndConcat(
            new Function<TargetNode<?>, Iterable<? extends String>>() {
              @Override
              public Iterable<String> apply(TargetNode<?> input) {
                return input
                    .castArg(AppleNativeTargetDescriptionArg.class)
                    .transform(GET_EXPORTED_LINKER_FLAGS)
                    .or(ImmutableSet.<String>of());
              }
            });
  }

  private <T> ImmutableSet<PBXFileReference> collectRecursiveLibraryDependencies(
      Iterable<TargetNode<T>> targetNodes) {
    return FluentIterable
        .from(targetNodes)
        .transformAndConcat(
            AppleBuildRules.newRecursiveRuleDependencyTransformer(
                targetGraph,
                AppleBuildRules.RecursiveDependenciesMode.LINKING,
                AppleBuildRules.XCODE_TARGET_BUILD_RULE_TYPES))
        .filter(getLibraryWithSourcesToCompilePredicate())
        .transform(
            new Function<TargetNode<?>, PBXFileReference>() {
              @Override
              public PBXFileReference apply(TargetNode<?> input) {
                return getLibraryFileReference(input);
              }
            }).toSet();
  }

  private Function<
      TargetNode<AppleNativeTargetDescriptionArg>,
      Iterable<String>> getTargetFrameworkSearchPaths(final FrameworkPath.FrameworkType type) {

    final Predicate<FrameworkPath> byType = Predicates.compose(
        Predicates.equalTo(type),
        FrameworkPath.getFrameworkTypeFunction(sourcePathResolver));

    final Function<FrameworkPath, Path> toSearchPath = FrameworkPath
        .getUnexpandedSearchPathFunction(
            sourcePathResolver,
            pathRelativizer.outputDirToRootRelative());

    return new Function<TargetNode<AppleNativeTargetDescriptionArg>, Iterable<String>>() {
      @Override
      public Iterable<String> apply(TargetNode<AppleNativeTargetDescriptionArg> input) {
        return FluentIterable
            .from(input.getConstructorArg().frameworks.get())
            .filter(byType)
            .transform(toSearchPath)
            .transform(Functions.toStringFunction());
      }
    };
  }

  private SourceTreePath getProductsSourceTreePath(TargetNode<?> targetNode) {
    String productName = getProductName(targetNode.getBuildTarget());
    String productOutputName;

    if (targetNode.getType().equals(AppleLibraryDescription.TYPE)) {
      String productOutputFormat = AppleBuildRules.getOutputFileNameFormatForLibrary(
          targetNode
              .getBuildTarget()
              .getFlavors()
              .contains(CxxDescriptionEnhancer.SHARED_FLAVOR));
      productOutputName = String.format(productOutputFormat, productName);
    } else if (targetNode.getType().equals(AppleBundleDescription.TYPE) ||
        targetNode.getType().equals(AppleTestDescription.TYPE)) {
      HasAppleBundleFields arg = (HasAppleBundleFields) targetNode.getConstructorArg();
      productOutputName = productName + "." + getExtensionString(arg.getExtension());
    } else if (targetNode.getType().equals(AppleBinaryDescription.TYPE)) {
      productOutputName = productName;
    } else {
      throw new RuntimeException("Unexpected type: " + targetNode.getType());
    }

    return new SourceTreePath(
        PBXReference.SourceTree.BUILT_PRODUCTS_DIR,
        Paths.get(productOutputName));
  }

  private PBXFileReference getLibraryFileReference(TargetNode<?> targetNode) {
    // Don't re-use the productReference from other targets in this project.
    // File references set as a productReference don't work with custom paths.
    SourceTreePath productsPath = getProductsSourceTreePath(targetNode);

    if (targetNode.getType().equals(AppleLibraryDescription.TYPE) ||
        targetNode.getType().equals(AppleBundleDescription.TYPE)) {
      return project.getMainGroup()
          .getOrCreateChildGroupByName("Frameworks")
          .getOrCreateFileReferenceBySourceTreePath(productsPath);
    } else if (targetNode.getType().equals(AppleBinaryDescription.TYPE)) {
      return project.getMainGroup()
          .getOrCreateChildGroupByName("Dependencies")
          .getOrCreateFileReferenceBySourceTreePath(productsPath);
    } else {
      throw new RuntimeException("Unexpected type: " + targetNode.getType());
    }
  }

  /**
   * Return a file reference to a test assuming it's built as a static library.
   */
  private PBXFileReference getOrCreateTestLibraryFileReference(
      TargetNode<AppleTestDescription.Arg> test) {
    SourceTreePath path = new SourceTreePath(
        PBXReference.SourceTree.BUILT_PRODUCTS_DIR,
        Paths.get(getBuiltProductsRelativeTargetOutputPath(test)).resolve(
            String.format(
                AppleBuildRules.getOutputFileNameFormatForLibrary(false),
                getProductName(test.getBuildTarget()))));
    return project.getMainGroup()
        .getOrCreateChildGroupByName("Test Libraries")
        .getOrCreateFileReferenceBySourceTreePath(path);
  }

  /**
   * Whether a given build target is built by the project being generated, or being build elsewhere.
   */
  private boolean isBuiltByCurrentProject(BuildTarget buildTarget) {
    return initialTargets.contains(buildTarget);
  }

  private String getXcodeTargetName(BuildTarget target) {
    return options.contains(Option.USE_SHORT_NAMES_FOR_TARGETS)
        ? target.getShortName()
        : target.getFullyQualifiedName();
  }

  @SuppressWarnings("incomplete-switch")
  ProductType bundleToTargetProductType(
      TargetNode<? extends HasAppleBundleFields> targetNode,
      TargetNode<? extends AppleNativeTargetDescriptionArg> binaryNode) {
    if (targetNode.getConstructorArg().getXcodeProductType().isPresent()) {
      return ProductType.of(targetNode.getConstructorArg().getXcodeProductType().get());
    } else if (targetNode.getConstructorArg().getExtension().isLeft()) {
      AppleBundleExtension extension = targetNode.getConstructorArg().getExtension().getLeft();

      if (binaryNode.getType().equals(AppleLibraryDescription.TYPE)) {
        if (binaryNode.getBuildTarget().getFlavors().contains(
            CxxDescriptionEnhancer.SHARED_FLAVOR)) {
          Optional<ProductType> productType =
              dylibProductTypeByBundleExtension(extension);
          if (productType.isPresent()) {
            return productType.get();
          }
        } else {
          switch (extension) {
            case FRAMEWORK:
              return ProductType.STATIC_FRAMEWORK;
          }
        }
      } else if (binaryNode.getType().equals(AppleBinaryDescription.TYPE)) {
        switch (extension) {
          case APP:
            return ProductType.APPLICATION;
        }
      } else if (binaryNode.getType().equals(AppleTestDescription.TYPE)) {
        switch (extension) {
          case OCTEST:
            return ProductType.BUNDLE;
          case XCTEST:
            return ProductType.UNIT_TEST;
        }
      }
    }

    return ProductType.BUNDLE;
  }

  private boolean shouldGenerateReadOnlyFiles() {
    return options.contains(Option.GENERATE_READ_ONLY_FILES);
  }

  private static String getExtensionString(Either<AppleBundleExtension, String> extension) {
    return extension.isLeft() ? extension.getLeft().toFileExtension() : extension.getRight();
  }

  private static boolean isFrameworkBundle(HasAppleBundleFields arg) {
    return arg.getExtension().isLeft() &&
        arg.getExtension().getLeft().equals(AppleBundleExtension.FRAMEWORK);
  }

  /**
   * Retrieve the location of the asset catalog build script.
   *
   * If the file is provided by buck and needs to be copied, mark it as such in the project.
   */
  private Path getAndMarkAssetCatalogBuildScript() {
    if (PATH_OVERRIDE_FOR_ASSET_CATALOG_BUILD_PHASE_SCRIPT != null) {
      return Paths.get(PATH_OVERRIDE_FOR_ASSET_CATALOG_BUILD_PHASE_SCRIPT);
    } else {
      // In order for the script to run, it must be accessible by Xcode and
      // deserves to be part of the generated output.
      shouldPlaceAssetCatalogCompiler = true;
      return placedAssetCatalogBuildPhaseScript;
    }
  }

  private Path emptyFileWithExtension(String extension) {
    Path path = BuckConstant.GEN_PATH.resolve("xcode-scripts/emptyFile." + extension);
    if (!projectFilesystem.exists(path)) {
      try {
        projectFilesystem.createParentDirs(path);
        projectFilesystem.newFileOutputStream(path).close();
      } catch (IOException e) {
        throw new RuntimeException(e);
      }
    }
    return path;
  }

  private Path resolveSourcePath(SourcePath sourcePath) {
    if (sourcePath instanceof PathSourcePath) {
      return ((PathSourcePath) sourcePath).getRelativePath();
    }
    Preconditions.checkArgument(sourcePath instanceof BuildTargetSourcePath);
    BuildTargetSourcePath buildTargetSourcePath = (BuildTargetSourcePath) sourcePath;
    BuildTarget buildTarget = buildTargetSourcePath.getTarget();
    TargetNode<?> node = Preconditions.checkNotNull(targetGraph.get(buildTarget));
    Optional<TargetNode<ExportFileDescription.Arg>> exportFileNode = node.castArg(
        ExportFileDescription.Arg.class);
    if (!exportFileNode.isPresent()) {
      Path output = outputPathOfNode.apply(node);
      if (output == null) {
        throw new HumanReadableException(
            "The target '%s' does not have an output.",
            node.getBuildTarget());
      }
      requiredBuildTargetsBuilder.add(buildTarget);
      return output;
    }

    Optional<SourcePath> src = exportFileNode.get().getConstructorArg().src;
    if (!src.isPresent()) {
      return buildTarget.getBasePath().resolve(buildTarget.getShortNameAndFlavorPostfix());
    }

    return resolveSourcePath(src.get());
  }

  private Predicate<TargetNode<?>> getLibraryWithSourcesToCompilePredicate() {
    return new Predicate<TargetNode<?>>() {
      @Override
      public boolean apply(TargetNode<?> input) {
        Optional<TargetNode<AppleNativeTargetDescriptionArg>> library =
            getLibraryNode(targetGraph, input);
        if (!library.isPresent()) {
          return false;
        }
        return (library.get().getConstructorArg().srcs.get().size() != 0);
      }
    };
  }

  /**
   * @return product type of a bundle containing a dylib.
   */
  private static Optional<ProductType> dylibProductTypeByBundleExtension(
      AppleBundleExtension extension) {
    switch (extension) {
      case FRAMEWORK:
        return Optional.of(ProductType.FRAMEWORK);
      case APPEX:
        return Optional.of(ProductType.APP_EXTENSION);
      case BUNDLE:
        return Optional.of(ProductType.BUNDLE);
      case OCTEST:
        return Optional.of(ProductType.BUNDLE);
      case XCTEST:
        return Optional.of(ProductType.UNIT_TEST);
      // $CASES-OMITTED$
      default:
        return Optional.absent();
    }
  }
}


File: src/com/facebook/buck/apple/xcode/xcodeproj/AbstractProductType.java
/*
 * Copyright 2013-present Facebook, Inc.
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

package com.facebook.buck.apple.xcode.xcodeproj;

import com.facebook.buck.util.immutables.BuckStyleImmutable;

import org.immutables.value.Value;

@Value.Immutable
@BuckStyleImmutable
abstract class AbstractProductType {
  public static final ProductType STATIC_LIBRARY = ProductType.of(
      "com.apple.product-type.library.static");
  public static final ProductType DYNAMIC_LIBRARY = ProductType.of(
      "com.apple.product-type.library.dynamic");
  public static final ProductType TOOL = ProductType.of(
      "com.apple.product-type.tool");
  public static final ProductType BUNDLE = ProductType.of(
      "com.apple.product-type.bundle");
  public static final ProductType FRAMEWORK = ProductType.of(
      "com.apple.product-type.framework");
  public static final ProductType STATIC_FRAMEWORK = ProductType.of(
      "com.apple.product-type.framework.static");
  public static final ProductType APPLICATION = ProductType.of(
      "com.apple.product-type.application");
  public static final ProductType UNIT_TEST = ProductType.of(
      "com.apple.product-type.bundle.unit-test");
  public static final ProductType APP_EXTENSION = ProductType.of(
      "com.apple.product-type.app-extension");

  @Value.Parameter
  public abstract String getIdentifier();

  @Override
  public String toString() {
    return getIdentifier();
  }
}


File: src/com/facebook/buck/apple/xcode/xcodeproj/PBXCopyFilesBuildPhase.java
/*
 * Copyright 2013-present Facebook, Inc.
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

package com.facebook.buck.apple.xcode.xcodeproj;

import com.facebook.buck.apple.xcode.XcodeprojSerializer;

public class PBXCopyFilesBuildPhase extends PBXBuildPhase {
  /**
   * The prefix path, this does not use SourceTreePath and build variables but rather some sort of
   * enum.
   */
  public enum Destination {
    ABSOLUTE(0),
    WRAPPER(1),
    EXECUTABLES(6),
    RESOURCES(7),
    FRAMEWORKS(10),
    SHARED_FRAMEWORKS(11),
    SHARED_SUPPORT(12),
    PLUGINS(13),
    JAVA_RESOURCES(15),
    PRODUCTS(16),
    ;

    private int value;

    public int getValue() {
      return value;
    }

    private Destination(int value) {
      this.value = value;
    }
  }

  /**
   * Base path of destination folder.
   */
  private Destination dstSubfolderSpec;

  /**
   * Subdirectory under the destination folder.
   */
  private String path;

  public PBXCopyFilesBuildPhase(Destination dstSubfolderSpec, String path) {
    this.dstSubfolderSpec = dstSubfolderSpec;
    this.path = path;
  }

  public Destination getDstSubfolderSpec() {
    return dstSubfolderSpec;
  }

  public String getPath() {
    return path;
  }

  @Override
  public String isa() {
    return "PBXCopyFilesBuildPhase";
  }

  @Override
  public void serializeInto(XcodeprojSerializer s) {
    super.serializeInto(s);
    s.addField("dstSubfolderSpec", dstSubfolderSpec.getValue());
    s.addField("dstPath", path);
  }
}


File: test/com/facebook/buck/apple/ProjectGeneratorTest.java
/*
 * Copyright 2013-present Facebook, Inc.
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

package com.facebook.buck.apple;

import static com.facebook.buck.apple.ProjectGeneratorTestUtils.assertHasSingletonCopyFilesPhaseWithFileEntries;
import static com.facebook.buck.apple.ProjectGeneratorTestUtils.assertHasSingletonFrameworksPhaseWithFrameworkEntries;
import static com.facebook.buck.apple.ProjectGeneratorTestUtils.assertTargetExistsAndReturnTarget;
import static com.facebook.buck.apple.ProjectGeneratorTestUtils.getSingletonPhaseByType;
import static org.hamcrest.CoreMatchers.containsString;
import static org.hamcrest.CoreMatchers.endsWith;
import static org.hamcrest.CoreMatchers.equalTo;
import static org.hamcrest.CoreMatchers.hasItem;
import static org.hamcrest.CoreMatchers.instanceOf;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.CoreMatchers.notNullValue;
import static org.hamcrest.CoreMatchers.startsWith;
import static org.hamcrest.Matchers.hasKey;
import static org.hamcrest.collection.IsCollectionWithSize.hasSize;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;

import com.dd.plist.NSDictionary;
import com.dd.plist.NSString;
import com.facebook.buck.apple.clang.HeaderMap;
import com.facebook.buck.apple.xcode.xcodeproj.PBXBuildFile;
import com.facebook.buck.apple.xcode.xcodeproj.PBXBuildPhase;
import com.facebook.buck.apple.xcode.xcodeproj.PBXFileReference;
import com.facebook.buck.apple.xcode.xcodeproj.PBXGroup;
import com.facebook.buck.apple.xcode.xcodeproj.PBXHeadersBuildPhase;
import com.facebook.buck.apple.xcode.xcodeproj.PBXProject;
import com.facebook.buck.apple.xcode.xcodeproj.PBXReference;
import com.facebook.buck.apple.xcode.xcodeproj.PBXResourcesBuildPhase;
import com.facebook.buck.apple.xcode.xcodeproj.PBXShellScriptBuildPhase;
import com.facebook.buck.apple.xcode.xcodeproj.PBXSourcesBuildPhase;
import com.facebook.buck.apple.xcode.xcodeproj.PBXTarget;
import com.facebook.buck.apple.xcode.xcodeproj.PBXVariantGroup;
import com.facebook.buck.apple.xcode.xcodeproj.ProductType;
import com.facebook.buck.apple.xcode.xcodeproj.SourceTreePath;
import com.facebook.buck.apple.xcode.xcodeproj.XCBuildConfiguration;
import com.facebook.buck.cli.FakeBuckConfig;
import com.facebook.buck.cxx.CxxDescriptionEnhancer;
import com.facebook.buck.cxx.CxxSource;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.js.IosReactNativeLibraryBuilder;
import com.facebook.buck.js.ReactNativeBuckConfig;
import com.facebook.buck.js.ReactNativeFlavors;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.model.HasBuildTarget;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.PathSourcePath;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.TargetNode;
import com.facebook.buck.rules.TestSourcePath;
import com.facebook.buck.rules.coercer.Either;
import com.facebook.buck.rules.coercer.FrameworkPath;
import com.facebook.buck.rules.coercer.SourceWithFlags;
import com.facebook.buck.shell.ExportFileBuilder;
import com.facebook.buck.shell.ExportFileDescription;
import com.facebook.buck.shell.GenruleBuilder;
import com.facebook.buck.testutil.AllExistingProjectFilesystem;
import com.facebook.buck.testutil.FakeProjectFilesystem;
import com.facebook.buck.testutil.TargetGraphFactory;
import com.facebook.buck.timing.SettableFakeClock;
import com.facebook.buck.util.BuckConstant;
import com.facebook.buck.util.HumanReadableException;
import com.google.common.base.Function;
import com.google.common.base.Functions;
import com.google.common.base.Optional;
import com.google.common.base.Predicate;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedMap;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;
import com.google.common.io.ByteStreams;

import org.hamcrest.FeatureMatcher;
import org.hamcrest.Matcher;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.FileAttribute;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.annotation.Nullable;

public class ProjectGeneratorTest {

  private static final Path OUTPUT_DIRECTORY = Paths.get("_gen");
  private static final String PROJECT_NAME = "GeneratedProject";
  private static final String PROJECT_CONTAINER = PROJECT_NAME + ".xcodeproj";
  private static final Path OUTPUT_PROJECT_BUNDLE_PATH =
      OUTPUT_DIRECTORY.resolve(PROJECT_CONTAINER);
  private static final Path OUTPUT_PROJECT_FILE_PATH =
      OUTPUT_PROJECT_BUNDLE_PATH.resolve("project.pbxproj");

  private SettableFakeClock clock;
  private ProjectFilesystem projectFilesystem;
  private FakeProjectFilesystem fakeProjectFilesystem;

  @Rule
  public ExpectedException thrown = ExpectedException.none();

  @Before
  public void setUp() throws IOException {
    clock = new SettableFakeClock(0, 0);
    fakeProjectFilesystem = new FakeProjectFilesystem(clock);
    projectFilesystem = fakeProjectFilesystem;

    // Add support files needed by project generation to fake filesystem.
    projectFilesystem.writeContentsToPath(
        "",
        Paths.get(ProjectGenerator.PATH_TO_ASSET_CATALOG_BUILD_PHASE_SCRIPT));
    projectFilesystem.writeContentsToPath(
        "",
        Paths.get(ProjectGenerator.PATH_TO_ASSET_CATALOG_COMPILER));

    // Add files and directories used to test resources.
    projectFilesystem.createParentDirs(Paths.get("foodir", "foo.png"));
    projectFilesystem.writeContentsToPath(
        "",
        Paths.get("foodir", "foo.png"));
    projectFilesystem.writeContentsToPath(
        "",
        Paths.get("bar.png"));
    fakeProjectFilesystem.touch(Paths.get("Base.lproj", "Bar.storyboard"));
  }

  @Test
  public void testProjectStructureForEmptyProject() throws IOException {
    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of());

    projectGenerator.createXcodeProjects();

    Optional<String> pbxproj = projectFilesystem.readFileIfItExists(OUTPUT_PROJECT_FILE_PATH);
    assertTrue(pbxproj.isPresent());
  }

  @Test
  public void testCreateDirectoryStructure() throws IOException {
    BuildTarget buildTarget1 = BuildTarget.builder("//foo/bar", "target1").build();
    TargetNode<?> node1 = AppleLibraryBuilder.createBuilder(buildTarget1).build();

    BuildTarget buildTarget2 = BuildTarget.builder("//foo/foo", "target2").build();
    TargetNode<?> node2 = AppleLibraryBuilder.createBuilder(buildTarget2).build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(node1, node2),
        ImmutableSet.of(
            ProjectGenerator.Option.CREATE_DIRECTORY_STRUCTURE,
            ProjectGenerator.Option.USE_SHORT_NAMES_FOR_TARGETS));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXGroup mainGroup = project.getMainGroup();

    PBXGroup groupFoo = null;
    for (PBXReference reference : mainGroup.getChildren()) {
      if (reference instanceof PBXGroup && "foo".equals(reference.getName())) {
        groupFoo = (PBXGroup) reference;
      }
    }
    assertNotNull("Project should have a group called foo", groupFoo);

    assertEquals("foo", groupFoo.getName());
    assertThat(groupFoo.getChildren(), hasSize(2));

    PBXGroup groupFooBar = (PBXGroup) Iterables.get(groupFoo.getChildren(), 0);
    assertEquals("bar", groupFooBar.getName());
    assertThat(groupFooBar.getChildren(), hasSize(1));

    PBXGroup groupFooFoo = (PBXGroup) Iterables.get(groupFoo.getChildren(), 1);
    assertEquals("foo", groupFooFoo.getName());
    assertThat(groupFooFoo.getChildren(), hasSize(1));

    PBXGroup groupFooBarTarget1 = (PBXGroup) Iterables.get(groupFooBar.getChildren(), 0);
    assertEquals("target1", groupFooBarTarget1.getName());

    PBXGroup groupFooFooTarget2 = (PBXGroup) Iterables.get(groupFooFoo.getChildren(), 0);
    assertEquals("target2", groupFooFooTarget2.getName());
  }

  @Test
  public void shouldNotCreateHeaderSymlinkTreesWhenTheyAreDisabled() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setUseBuckHeaderMaps(Optional.of(false))
        .setHeaders(
            ImmutableSortedSet.<SourcePath>of(
                new TestSourcePath("HeaderGroup1/foo.h")))
        .setExportedHeaders(
            ImmutableSortedSet.<SourcePath>of(
                new TestSourcePath("HeaderGroup1/bar.h")))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    // No header map should be generated
    List<Path> headerSymlinkTrees = projectGenerator.getGeneratedHeaderSymlinkTrees();
    assertThat(headerSymlinkTrees, hasSize(0));
  }

  @Test
  public void testLibraryHeaderGroupsWithHeaderSymlinkTrees() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setSrcs(Optional.of(ImmutableList.<SourceWithFlags>of()))
        .setHeaders(
            ImmutableSortedSet.<SourcePath>of(
                new TestSourcePath("HeaderGroup1/foo.h"),
                new TestSourcePath("HeaderGroup2/baz.h")))
        .setExportedHeaders(
            ImmutableSortedSet.<SourcePath>of(
                new TestSourcePath("HeaderGroup1/bar.h")))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXGroup targetGroup =
        project.getMainGroup().getOrCreateChildGroupByName(buildTarget.getFullyQualifiedName());
    PBXGroup sourcesGroup = targetGroup.getOrCreateChildGroupByName("Sources");

    assertThat(sourcesGroup.getChildren(), hasSize(2));

    PBXGroup group1 = (PBXGroup) Iterables.get(sourcesGroup.getChildren(), 0);
    assertEquals("HeaderGroup1", group1.getName());
    assertThat(group1.getChildren(), hasSize(2));
    PBXFileReference fileRefFoo = (PBXFileReference) Iterables.get(group1.getChildren(), 0);
    assertEquals("bar.h", fileRefFoo.getName());
    PBXFileReference fileRefBar = (PBXFileReference) Iterables.get(group1.getChildren(), 1);
    assertEquals("foo.h", fileRefBar.getName());

    PBXGroup group2 = (PBXGroup) Iterables.get(sourcesGroup.getChildren(), 1);
    assertEquals("HeaderGroup2", group2.getName());
    assertThat(group2.getChildren(), hasSize(1));
    PBXFileReference fileRefBaz = (PBXFileReference) Iterables.get(group2.getChildren(), 0);
    assertEquals("baz.h", fileRefBaz.getName());

    // There should be no PBXHeadersBuildPhase in the 'Buck header map mode'.
    PBXTarget target = assertTargetExistsAndReturnTarget(project, "//foo:lib");
    assertEquals(
        Optional.<PBXBuildPhase>absent(),
        Iterables.tryFind(
            target.getBuildPhases(), new Predicate<PBXBuildPhase>() {
              @Override
              public boolean apply(PBXBuildPhase input) {
                return input instanceof PBXHeadersBuildPhase;
              }
            }));

    List<Path> headerSymlinkTrees = projectGenerator.getGeneratedHeaderSymlinkTrees();
    assertThat(headerSymlinkTrees, hasSize(2));

    assertEquals(
        "buck-out/gen/foo/lib-public-header-symlink-tree",
        headerSymlinkTrees.get(0).toString());
    assertThatHeaderSymlinkTreeContains(
        Paths.get("buck-out/gen/foo/lib-public-header-symlink-tree"),
        ImmutableMap.of("lib/bar.h", "HeaderGroup1/bar.h"));

    assertEquals(
        "buck-out/gen/foo/lib-private-header-symlink-tree",
        headerSymlinkTrees.get(1).toString());
    assertThatHeaderSymlinkTreeContains(
        Paths.get("buck-out/gen/foo/lib-private-header-symlink-tree"),
        ImmutableMap.<String, String>builder()
            .put("lib/foo.h", "HeaderGroup1/foo.h")
            .put("lib/baz.h", "HeaderGroup2/baz.h")
            .put("foo.h", "HeaderGroup1/foo.h")
            .put("bar.h", "HeaderGroup1/bar.h")
            .put("baz.h", "HeaderGroup2/baz.h")
            .build());
  }

  @Test
  public void testLibraryHeaderGroupsWithMappedHeaders() throws IOException {
    BuildTarget privateGeneratedTarget = BuildTarget.builder("//foo", "generated1.h").build();
    BuildTarget publicGeneratedTarget = BuildTarget.builder("//foo", "generated2.h").build();

    TargetNode<?> privateGeneratedNode =
        ExportFileBuilder.newExportFileBuilder(privateGeneratedTarget).build();
    TargetNode<?> publicGeneratedNode =
        ExportFileBuilder.newExportFileBuilder(publicGeneratedTarget).build();

    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setSrcs(Optional.of(ImmutableList.<SourceWithFlags>of()))
        .setHeaders(
            ImmutableMap.<String, SourcePath>of(
                "any/name.h", new TestSourcePath("HeaderGroup1/foo.h"),
                "different/name.h", new TestSourcePath("HeaderGroup2/baz.h"),
                "one/more/name.h", new BuildTargetSourcePath(privateGeneratedTarget)))
        .setExportedHeaders(
            ImmutableMap.<String, SourcePath>of(
                "yet/another/name.h", new TestSourcePath("HeaderGroup1/bar.h"),
                "and/one/more.h", new BuildTargetSourcePath(publicGeneratedTarget)))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(node, privateGeneratedNode, publicGeneratedNode));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXGroup targetGroup =
        project.getMainGroup().getOrCreateChildGroupByName(buildTarget.getFullyQualifiedName());
    PBXGroup sourcesGroup = targetGroup.getOrCreateChildGroupByName("Sources");

    assertThat(sourcesGroup.getChildren(), hasSize(3));

    PBXGroup group1 = (PBXGroup) Iterables.get(sourcesGroup.getChildren(), 0);
    assertEquals("HeaderGroup1", group1.getName());
    assertThat(group1.getChildren(), hasSize(2));
    PBXFileReference fileRefFoo = (PBXFileReference) Iterables.get(group1.getChildren(), 0);
    assertEquals("bar.h", fileRefFoo.getName());
    PBXFileReference fileRefBar = (PBXFileReference) Iterables.get(group1.getChildren(), 1);
    assertEquals("foo.h", fileRefBar.getName());

    PBXGroup group2 = (PBXGroup) Iterables.get(sourcesGroup.getChildren(), 1);
    assertEquals("HeaderGroup2", group2.getName());
    assertThat(group2.getChildren(), hasSize(1));
    PBXFileReference fileRefBaz = (PBXFileReference) Iterables.get(group2.getChildren(), 0);
    assertEquals("baz.h", fileRefBaz.getName());

    PBXGroup group3 = (PBXGroup) Iterables.get(sourcesGroup.getChildren(), 2);
    assertEquals("foo", group3.getName());
    assertThat(group3.getChildren(), hasSize(2));
    PBXFileReference fileRefGenerated1 = (PBXFileReference) Iterables.get(group3.getChildren(), 0);
    assertEquals("generated1.h", fileRefGenerated1.getName());
    PBXFileReference fileRefGenerated2 = (PBXFileReference) Iterables.get(group3.getChildren(), 1);
    assertEquals("generated2.h", fileRefGenerated2.getName());

    // There should be no PBXHeadersBuildPhase in the 'Buck header map mode'.
    PBXTarget target = assertTargetExistsAndReturnTarget(project, "//foo:lib");
    assertEquals(
        Optional.<PBXBuildPhase>absent(),
        Iterables.tryFind(
            target.getBuildPhases(), new Predicate<PBXBuildPhase>() {
              @Override
              public boolean apply(PBXBuildPhase input) {
                return input instanceof PBXHeadersBuildPhase;
              }
            }));

    List<Path> headerSymlinkTrees = projectGenerator.getGeneratedHeaderSymlinkTrees();
    assertThat(headerSymlinkTrees, hasSize(2));

    assertEquals(
        "buck-out/gen/foo/lib-public-header-symlink-tree",
        headerSymlinkTrees.get(0).toString());
    assertThatHeaderSymlinkTreeContains(
        Paths.get("buck-out/gen/foo/lib-public-header-symlink-tree"),
        ImmutableMap.of(
            "yet/another/name.h", "HeaderGroup1/bar.h",
            "and/one/more.h", "foo/generated2.h"));

    assertEquals(
        "buck-out/gen/foo/lib-private-header-symlink-tree",
        headerSymlinkTrees.get(1).toString());
    assertThatHeaderSymlinkTreeContains(
        Paths.get("buck-out/gen/foo/lib-private-header-symlink-tree"),
        ImmutableMap.of(
            "any/name.h", "HeaderGroup1/foo.h",
            "different/name.h", "HeaderGroup2/baz.h",
            "one/more/name.h", "foo/generated1.h"));
  }

  @Test
  public void testHeaderSymlinkTreesAreRegeneratedWhenKeyChanges() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setSrcs(Optional.of(ImmutableList.<SourceWithFlags>of()))
        .setHeaders(
            ImmutableMap.<String, SourcePath>of(
                "key.h", new TestSourcePath("value.h")))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    List<Path> headerSymlinkTrees = projectGenerator.getGeneratedHeaderSymlinkTrees();
    assertThat(headerSymlinkTrees, hasSize(2));

    assertEquals(
        "buck-out/gen/foo/lib-private-header-symlink-tree",
        headerSymlinkTrees.get(1).toString());
    assertThatHeaderSymlinkTreeContains(
        Paths.get("buck-out/gen/foo/lib-private-header-symlink-tree"),
        ImmutableMap.of("key.h", "value.h"));

    node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setSrcs(Optional.of(ImmutableList.<SourceWithFlags>of()))
        .setHeaders(
            ImmutableMap.<String, SourcePath>of(
                "new-key.h", new TestSourcePath("value.h")))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    headerSymlinkTrees = projectGenerator.getGeneratedHeaderSymlinkTrees();
    assertThat(headerSymlinkTrees, hasSize(2));

    assertEquals(
        "buck-out/gen/foo/lib-private-header-symlink-tree",
        headerSymlinkTrees.get(1).toString());
    assertFalse(
        projectFilesystem.isSymLink(
            Paths.get(
                "buck-out/gen/foo/lib-private-header-symlink-tree/key.h")));
    assertThatHeaderSymlinkTreeContains(
        Paths.get("buck-out/gen/foo/lib-private-header-symlink-tree"),
        ImmutableMap.of("new-key.h", "value.h"));
  }

  @Test
  public void testHeaderSymlinkTreesAreRegeneratedWhenValueChanges() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setSrcs(Optional.of(ImmutableList.<SourceWithFlags>of()))
        .setHeaders(
            ImmutableMap.<String, SourcePath>of(
                "key.h", new TestSourcePath("value.h")))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    List<Path> headerSymlinkTrees = projectGenerator.getGeneratedHeaderSymlinkTrees();
    assertThat(headerSymlinkTrees, hasSize(2));

    assertEquals(
        "buck-out/gen/foo/lib-private-header-symlink-tree",
        headerSymlinkTrees.get(1).toString());
    assertThatHeaderSymlinkTreeContains(
        Paths.get("buck-out/gen/foo/lib-private-header-symlink-tree"),
        ImmutableMap.of("key.h", "value.h"));

    node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setSrcs(Optional.of(ImmutableList.<SourceWithFlags>of()))
        .setHeaders(
            ImmutableMap.<String, SourcePath>of(
                "key.h", new TestSourcePath("new-value.h")))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    headerSymlinkTrees = projectGenerator.getGeneratedHeaderSymlinkTrees();
    assertThat(headerSymlinkTrees, hasSize(2));

    assertEquals(
        "buck-out/gen/foo/lib-private-header-symlink-tree",
        headerSymlinkTrees.get(1).toString());
    assertThatHeaderSymlinkTreeContains(
        Paths.get("buck-out/gen/foo/lib-private-header-symlink-tree"),
        ImmutableMap.of("key.h", "new-value.h"));
  }

  @Test
  public void testHeaderSymlinkTreesWithHeadersVisibleForTesting() throws IOException {
    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    BuildTarget testTarget = BuildTarget.builder("//foo", "test").build();

    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setSrcs(
            Optional.of(
                ImmutableList.of(
                    SourceWithFlags.of(
                        new TestSourcePath("foo.h"),
                        ImmutableList.of("public")),
                    SourceWithFlags.of(
                        new TestSourcePath("bar.h")))))
        .setTests(Optional.of(ImmutableSortedSet.of(testTarget)))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Default",
                    ImmutableMap.<String, String>of())))
        .setUseBuckHeaderMaps(Optional.of(true))
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(libraryNode, testNode));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget testPBXTarget = assertTargetExistsAndReturnTarget(project, "//foo:test");

    ImmutableMap<String, String> buildSettings =
        getBuildSettings(testTarget, testPBXTarget, "Default");

    assertEquals(
        "test binary should use header symlink trees for both public and non-public headers " +
            "of the tested library in HEADER_SEARCH_PATHS",
        "$(inherited) " +
            "../buck-out/gen/foo/test-private-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/test-public-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/lib-public-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/lib-private-header-symlink-tree/.tree.hmap",
        buildSettings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        "USER_HEADER_SEARCH_PATHS should not be set",
        null,
        buildSettings.get("USER_HEADER_SEARCH_PATHS"));
  }

  @Test
  public void testHeaderSymlinkTreesWithTestsAndLibraryBundles() throws IOException {
    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle").build();
    BuildTarget testTarget = BuildTarget.builder("//foo", "test").build();

    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setSrcs(
            Optional.of(
                ImmutableList.of(
                    SourceWithFlags.of(
                        new TestSourcePath("foo.h"),
                        ImmutableList.of("public")),
                    SourceWithFlags.of(
                        new TestSourcePath("bar.h")))))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setBinary(libraryTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.FRAMEWORK))
        .setTests(Optional.of(ImmutableSortedSet.of(testTarget)))
        .build();

    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Default",
                    ImmutableMap.<String, String>of())))
        .setUseBuckHeaderMaps(Optional.of(true))
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setDeps(Optional.of(ImmutableSortedSet.of(bundleTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(libraryNode, bundleNode, testNode));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget testPBXTarget = assertTargetExistsAndReturnTarget(project, "//foo:test");

    ImmutableMap<String, String> buildSettings =
        getBuildSettings(testTarget, testPBXTarget, "Default");

    assertEquals(
        "test binary should use header symlink trees for both public and non-public headers " +
            "of the tested library in HEADER_SEARCH_PATHS",
        "$(inherited) " +
            "../buck-out/gen/foo/test-private-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/test-public-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/lib-public-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/lib-private-header-symlink-tree/.tree.hmap",
        buildSettings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        "USER_HEADER_SEARCH_PATHS should not be set",
        null,
        buildSettings.get("USER_HEADER_SEARCH_PATHS"));
  }

  @Test
  public void testHeaderSymlinkTreesWithTestsAndBinaryBundles() throws IOException {
    BuildTarget binaryTarget = BuildTarget.builder("//foo", "bin").build();
    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle").build();
    BuildTarget testTarget = BuildTarget.builder("//foo", "test").build();

    TargetNode<?> binaryNode = AppleBinaryBuilder
        .createBuilder(binaryTarget)
        .setSrcs(
            Optional.of(
                ImmutableList.of(
                    SourceWithFlags.of(
                        new TestSourcePath("foo.h"),
                        ImmutableList.of("public")),
                    SourceWithFlags.of(
                        new TestSourcePath("bar.h")))))
        .setUseBuckHeaderMaps(Optional.of(true))
        .build();

    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setBinary(binaryTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.APP))
        .setTests(Optional.of(ImmutableSortedSet.of(testTarget)))
        .build();

    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Default",
                    ImmutableMap.<String, String>of())))
        .setUseBuckHeaderMaps(Optional.of(true))
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setDeps(Optional.of(ImmutableSortedSet.of(bundleTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(binaryNode, bundleNode, testNode));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget testPBXTarget = assertTargetExistsAndReturnTarget(project, "//foo:test");

    ImmutableMap<String, String> buildSettings =
        getBuildSettings(testTarget, testPBXTarget, "Default");

    assertEquals(
        "test binary should use header symlink trees for both public and non-public headers " +
            "of the tested binary in HEADER_SEARCH_PATHS",
        "$(inherited) " +
            "../buck-out/gen/foo/test-private-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/test-public-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/bin-public-header-symlink-tree/.tree.hmap " +
            "../buck-out/gen/foo/bin-private-header-symlink-tree/.tree.hmap",
        buildSettings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        "USER_HEADER_SEARCH_PATHS should not be set",
        null,
        buildSettings.get("USER_HEADER_SEARCH_PATHS"));
  }

  private void assertThatHeaderSymlinkTreeContains(Path root, ImmutableMap<String, String> content)
      throws IOException {
    for (Map.Entry<String, String> entry : content.entrySet()) {
      Path link = root.resolve(Paths.get(entry.getKey()));
      Path target = Paths.get(entry.getValue()).toAbsolutePath();
      assertTrue(projectFilesystem.isSymLink(link));
      assertEquals(
          target,
          projectFilesystem.readSymLink(link));
    }

    // Check the tree's header map.
    byte[] headerMapBytes;
    try (InputStream headerMapInputStream =
             projectFilesystem.newFileInputStream(root.resolve(".tree.hmap"))) {
      headerMapBytes = ByteStreams.toByteArray(headerMapInputStream);
    }
    HeaderMap headerMap = HeaderMap.deserialize(headerMapBytes);
    assertNotNull(headerMap);
    assertThat(headerMap.getNumEntries(), equalTo(content.size()));
    for (String key : content.keySet()) {
      assertThat(
          headerMap.lookup(key),
          equalTo(projectFilesystem.resolve(root).resolve(key).toString()));
    }
  }

  @Test
  public void testAppleLibraryRule() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setSrcs(
            Optional.of(
                ImmutableList.of(
                    SourceWithFlags.of(
                        new TestSourcePath("foo.m"), ImmutableList.of("-foo")),
                    SourceWithFlags.of(new TestSourcePath("bar.m")))))
        .setExtraXcodeSources(
            Optional.of(
                ImmutableList.<SourcePath>of(
                    new TestSourcePath("libsomething.a"))))
        .setHeaders(
            ImmutableSortedSet.<SourcePath>of(new TestSourcePath("foo.h")))
        .setUseBuckHeaderMaps(Optional.of(false))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");
    assertThat(target.isa(), equalTo("PBXNativeTarget"));
    assertThat(target.getProductType(), equalTo(ProductType.STATIC_LIBRARY));

    assertHasConfigurations(target, "Debug");
    assertEquals("Should have exact number of build phases", 2, target.getBuildPhases().size());
    assertHasSingletonSourcesPhaseWithSourcesAndFlags(
        target, ImmutableMap.of(
            "foo.m", Optional.of("-foo"),
            "bar.m", Optional.<String>absent(),
            "libsomething.a", Optional.<String>absent()));

   // check headers
    {
      PBXBuildPhase headersBuildPhase =
          Iterables.find(target.getBuildPhases(), new Predicate<PBXBuildPhase>() {
            @Override
            public boolean apply(PBXBuildPhase input) {
              return input instanceof PBXHeadersBuildPhase;
            }
          });
      PBXBuildFile headerBuildFile = Iterables.getOnlyElement(headersBuildPhase.getFiles());

      String headerBuildFilePath = assertFileRefIsRelativeAndResolvePath(
          headerBuildFile.getFileRef());
      assertEquals(
          projectFilesystem.getRootPath().resolve("foo.h").toAbsolutePath().normalize().toString(),
          headerBuildFilePath);
    }

    // this target should not have an asset catalog build phase
    assertFalse(hasShellScriptPhaseToCompileAssetCatalogs(target));
  }

  @Test
  public void testAppleLibraryConfiguresOutputPaths() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setHeaderPathPrefix(Optional.of("MyHeaderPathPrefix"))
        .setPrefixHeader(Optional.<SourcePath>of(new TestSourcePath("Foo/Foo-Prefix.pch")))
        .setUseBuckHeaderMaps(Optional.of(false))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");
    assertThat(target.isa(), equalTo("PBXNativeTarget"));
    assertThat(target.getProductType(), equalTo(ProductType.STATIC_LIBRARY));

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals(
        "../Foo/Foo-Prefix.pch",
        settings.get("GCC_PREFIX_HEADER"));
    assertEquals(
        "$SYMROOT/$CONFIGURATION$EFFECTIVE_PLATFORM_NAME",
        settings.get("BUILT_PRODUCTS_DIR"));
    assertEquals(
        "$BUILT_PRODUCTS_DIR",
        settings.get("CONFIGURATION_BUILD_DIR"));
    assertEquals(
        "F4XWM33PHJWGSYQ/Headers/MyHeaderPathPrefix",
        settings.get("PUBLIC_HEADERS_FOLDER_PATH"));
  }

  @Test
  public void testAppleFrameworkConfiguresPublicHeaderPaths() throws IOException {
    BuildTarget libTarget = BuildTarget.builder("//foo", "lib")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> libNode = AppleLibraryBuilder
        .createBuilder(libTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setHeaderPathPrefix(Optional.of("MyHeaderPathPrefix"))
        .setUseBuckHeaderMaps(Optional.of(false))
        .build();

    BuildTarget frameworkTarget = BuildTarget.builder("//foo", "bundle").build();
    TargetNode<?> frameworkNode = AppleBundleBuilder
        .createBuilder(frameworkTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.FRAMEWORK))
        .setBinary(libTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(libNode, frameworkNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget frameworkPbxTarget = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:bundle");
    assertEquals(frameworkPbxTarget.getProductType(), ProductType.FRAMEWORK);
    assertThat(frameworkPbxTarget.isa(), equalTo("PBXNativeTarget"));
    PBXFileReference frameworkProductReference = frameworkPbxTarget.getProductReference();
    assertEquals("bundle.framework", frameworkProductReference.getName());
    assertEquals(Optional.of("wrapper.framework"), frameworkProductReference.getExplicitFileType());

    ImmutableMap<String, String> settings = getBuildSettings(
        frameworkTarget, frameworkPbxTarget, "Debug");
    assertEquals("framework", settings.get("WRAPPER_EXTENSION"));
    assertEquals(
        "$SYMROOT/$CONFIGURATION$EFFECTIVE_PLATFORM_NAME",
        settings.get("BUILT_PRODUCTS_DIR"));
    assertEquals(
        "$BUILT_PRODUCTS_DIR",
        settings.get("CONFIGURATION_BUILD_DIR"));
    assertEquals(
        "F4XWM33PHJRHK3TENRSQ/Headers/MyHeaderPathPrefix",
        settings.get("PUBLIC_HEADERS_FOLDER_PATH"));
  }

  @Test
  public void testAppleLibraryConfiguresSharedLibraryOutputPaths() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//hi", "lib")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setHeaderPathPrefix(Optional.of("MyHeaderPathPrefix"))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//hi:lib#shared");
    assertThat(target.isa(), equalTo("PBXNativeTarget"));
    assertThat(target.getProductType(), equalTo(ProductType.DYNAMIC_LIBRARY));

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals(
        "$SYMROOT/$CONFIGURATION$EFFECTIVE_PLATFORM_NAME",
        settings.get("BUILT_PRODUCTS_DIR"));
    assertEquals(
        "$BUILT_PRODUCTS_DIR",
        settings.get("CONFIGURATION_BUILD_DIR"));
    assertEquals(
        "F4XWQ2J2NRUWEI3TNBQXEZLE/Headers/MyHeaderPathPrefix",
        settings.get("PUBLIC_HEADERS_FOLDER_PATH"));
  }

  @Test
  public void testAppleLibraryDoesntOverrideHeaderOutputPath() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.of("PUBLIC_HEADERS_FOLDER_PATH", "FooHeaders"))))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");
    assertThat(target.isa(), equalTo("PBXNativeTarget"));
    assertThat(target.getProductType(), equalTo(ProductType.STATIC_LIBRARY));

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals(
        "$SYMROOT/$CONFIGURATION$EFFECTIVE_PLATFORM_NAME",
        settings.get("BUILT_PRODUCTS_DIR"));
    assertEquals(
        "$BUILT_PRODUCTS_DIR",
        settings.get("CONFIGURATION_BUILD_DIR"));
    assertEquals(
        "FooHeaders",
        settings.get("PUBLIC_HEADERS_FOLDER_PATH"));
  }

  @Test
  public void testAppleLibraryCompilerAndPreprocessorFlags() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setCompilerFlags(Optional.of(ImmutableList.of("-fhello")))
        .setPreprocessorFlags(Optional.of(ImmutableList.of("-fworld")))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) -fhello -fworld", settings.get("OTHER_CFLAGS"));
  }

  @Test
  public void testAppleLibraryCompilerAndPreprocessorFlagsDontPropagate() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setCompilerFlags(Optional.of(ImmutableList.of("-fhello")))
        .setPreprocessorFlags(Optional.of(ImmutableList.of("-fworld")))
        .build();

    BuildTarget dependentBuildTarget = BuildTarget.builder("//foo", "bin").build();
    TargetNode<?> dependentNode = AppleBinaryBuilder
        .createBuilder(dependentBuildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setDeps(Optional.of(ImmutableSortedSet.of(buildTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node, dependentNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:bin");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) ", settings.get("OTHER_CFLAGS"));
  }

  @Test
  public void testAppleLibraryExportedPreprocessorFlags() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setExportedPreprocessorFlags(Optional.of(ImmutableList.of("-DHELLO")))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) -DHELLO", settings.get("OTHER_CFLAGS"));
  }

  @Test
  public void testAppleLibraryExportedPreprocessorFlagsPropagate() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setExportedPreprocessorFlags(Optional.of(ImmutableList.of("-DHELLO")))
        .build();

    BuildTarget dependentBuildTarget = BuildTarget.builder("//foo", "bin").build();
    TargetNode<?> dependentNode = AppleBinaryBuilder
        .createBuilder(dependentBuildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setDeps(Optional.of(ImmutableSortedSet.of(buildTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node, dependentNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:bin");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) -DHELLO", settings.get("OTHER_CFLAGS"));
  }

  @Test
  public void testAppleLibraryLinkerFlags() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setLinkerFlags(Optional.of(ImmutableList.of("-lhello")))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) -Xlinker -lhello", settings.get("OTHER_LDFLAGS"));
  }

  @Test
  public void testAppleLibraryLinkerFlagsDontPropagate() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setLinkerFlags(Optional.of(ImmutableList.of("-lhello")))
        .build();

    BuildTarget dependentBuildTarget = BuildTarget.builder("//foo", "bin").build();
    TargetNode<?> dependentNode = AppleBinaryBuilder
        .createBuilder(dependentBuildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setDeps(Optional.of(ImmutableSortedSet.of(buildTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node, dependentNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:bin");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) ", settings.get("OTHER_LDFLAGS"));
  }

  @Test
  public void testAppleLibraryExportedLinkerFlags() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setExportedLinkerFlags(Optional.of(ImmutableList.of("-lhello")))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) -Xlinker -lhello", settings.get("OTHER_LDFLAGS"));
  }

  @Test
  public void testAppleLibraryExportedLinkerFlagsPropagate() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setExportedLinkerFlags(Optional.of(ImmutableList.of("-lhello")))
        .build();

    BuildTarget dependentBuildTarget = BuildTarget.builder("//foo", "bin").build();
    TargetNode<?> dependentNode = AppleBinaryBuilder
        .createBuilder(dependentBuildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setDeps(Optional.of(ImmutableSortedSet.of(buildTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node, dependentNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:bin");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) -Xlinker -lhello", settings.get("OTHER_LDFLAGS"));
  }

  @Test
  public void testConfigurationSerializationWithoutExistingXcconfig() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.of("CUSTOM_SETTING", "VALUE"))))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");
    assertThat(target.isa(), equalTo("PBXNativeTarget"));
    assertThat(target.getProductType(), equalTo(ProductType.STATIC_LIBRARY));

    assertHasConfigurations(target, "Debug");
    XCBuildConfiguration configuration = target
        .getBuildConfigurationList().getBuildConfigurationsByName().asMap().get("Debug");
    assertEquals(configuration.getBuildSettings().count(), 0);

    PBXFileReference xcconfigReference = configuration.getBaseConfigurationReference();
    assertEquals(xcconfigReference.getPath(), "../buck-out/gen/foo/lib-Debug.xcconfig");

    ImmutableMap<String, String> settings = getBuildSettings(
        buildTarget, target, "Debug");
    assertEquals(
        "$SYMROOT/$CONFIGURATION$EFFECTIVE_PLATFORM_NAME",
        settings.get("BUILT_PRODUCTS_DIR"));
    assertEquals(
        "$BUILT_PRODUCTS_DIR",
        settings.get("CONFIGURATION_BUILD_DIR"));
    assertEquals(
        "VALUE",
        settings.get("CUSTOM_SETTING"));
  }

  @Test
  public void testAppleLibraryDependentsSearchHeadersAndLibraries() throws IOException {
    ImmutableSortedMap<String, ImmutableMap<String, String>> configs =
        ImmutableSortedMap.of(
            "Debug", ImmutableMap.<String, String>of());

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setConfigs(Optional.of(configs))
        .setUseBuckHeaderMaps(Optional.of(false))
        .setSrcs(
            Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("foo.m")))))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Library.framework"))))))
        .build();

    BuildTarget testTarget = BuildTarget.builder("//foo", "xctest").build();
    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setConfigs(Optional.of(configs))
        .setUseBuckHeaderMaps(Optional.of(false))
        .setSrcs(
            Optional.of(
                ImmutableList.of(SourceWithFlags.of(new TestSourcePath("fooTest.m")))))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Test.framework"))))))
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(libraryNode, testNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:xctest");

    ImmutableMap<String, String> settings = getBuildSettings(testTarget, target, "Debug");
    assertEquals(
        "$(inherited) $BUILT_PRODUCTS_DIR/F4XWM33PHJWGSYQ/Headers",
        settings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        null,
        settings.get("USER_HEADER_SEARCH_PATHS"));
    assertEquals(
        "$(inherited) $BUILT_PRODUCTS_DIR",
        settings.get("LIBRARY_SEARCH_PATHS"));
    assertEquals(
        "$(inherited) $BUILT_PRODUCTS_DIR $SDKROOT",
        settings.get("FRAMEWORK_SEARCH_PATHS"));
  }

  @Test
  public void testAppleLibraryDependentsInheritSearchPaths() throws IOException {
    ImmutableSortedMap<String, ImmutableMap<String, String>> configs = ImmutableSortedMap.of(
        "Debug",
        ImmutableMap.of(
            "HEADER_SEARCH_PATHS", "headers",
            "USER_HEADER_SEARCH_PATHS", "user_headers",
            "LIBRARY_SEARCH_PATHS", "libraries",
            "FRAMEWORK_SEARCH_PATHS", "frameworks"));

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setConfigs(Optional.of(configs))
        .setUseBuckHeaderMaps(Optional.of(false))
        .setSrcs(
            Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("foo.m")))))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Library.framework"))))))
        .build();

    BuildTarget testTarget = BuildTarget.builder("//foo", "xctest").build();
    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setConfigs(Optional.of(configs))
        .setUseBuckHeaderMaps(Optional.of(false))
        .setSrcs(
            Optional.of(
                ImmutableList.of(SourceWithFlags.of(new TestSourcePath("fooTest.m")))))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Test.framework"))))))
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(libraryNode, testNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:xctest");

    ImmutableMap<String, String> settings = getBuildSettings(testTarget, target, "Debug");
    assertEquals(
        "headers $BUILT_PRODUCTS_DIR/F4XWM33PHJWGSYQ/Headers",
        settings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        "user_headers",
        settings.get("USER_HEADER_SEARCH_PATHS"));
    assertEquals(
        "libraries $BUILT_PRODUCTS_DIR",
        settings.get("LIBRARY_SEARCH_PATHS"));
    assertEquals(
        "frameworks $BUILT_PRODUCTS_DIR $SDKROOT",
        settings.get("FRAMEWORK_SEARCH_PATHS"));
  }

  @Test
  public void testAppleLibraryTransitiveDependentsSearchHeadersAndLibraries() throws IOException {
    ImmutableSortedMap<String, ImmutableMap<String, String>> configs = ImmutableSortedMap.of(
        "Debug", ImmutableMap.<String, String>of());

    BuildTarget libraryDepTarget = BuildTarget.builder("//bar", "lib").build();
    TargetNode<?> libraryDepNode = AppleLibraryBuilder
        .createBuilder(libraryDepTarget)
        .setUseBuckHeaderMaps(Optional.of(false))
        .setConfigs(Optional.of(configs))
        .setSrcs(
            Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("foo.m")))))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Library.framework"))))))
        .build();

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setConfigs(Optional.of(configs))
        .setSrcs(
            Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("foo.m")))))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Library.framework"))))))
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryDepTarget)))
        .setUseBuckHeaderMaps(Optional.of(false))
        .build();

    BuildTarget testTarget = BuildTarget.builder("//foo", "xctest").build();
    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setConfigs(Optional.of(configs))
        .setSrcs(
            Optional.of(
                ImmutableList.of(SourceWithFlags.of(new TestSourcePath("fooTest.m")))))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Test.framework"))))))
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryTarget)))
        .setUseBuckHeaderMaps(Optional.of(false))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(libraryDepNode, libraryNode, testNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:xctest");

    ImmutableMap<String, String> settings = getBuildSettings(testTarget, target, "Debug");
    assertEquals(
        "$(inherited) " +
            "$BUILT_PRODUCTS_DIR/F4XWEYLSHJWGSYQ/Headers " +
            "$BUILT_PRODUCTS_DIR/F4XWM33PHJWGSYQ/Headers",
        settings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        null,
        settings.get("USER_HEADER_SEARCH_PATHS"));
    assertEquals(
        "$(inherited) " +
            "$BUILT_PRODUCTS_DIR",
        settings.get("LIBRARY_SEARCH_PATHS"));
    assertEquals(
        "$(inherited) " +
            "$BUILT_PRODUCTS_DIR $SDKROOT",
        settings.get("FRAMEWORK_SEARCH_PATHS"));
  }

  @Test
  public void testAppleLibraryWithoutSources() throws IOException {
    ImmutableSortedMap<String, ImmutableMap<String, String>> configs = ImmutableSortedMap.of(
        "Debug",
        ImmutableMap.of(
            "HEADER_SEARCH_PATHS", "headers",
            "LIBRARY_SEARCH_PATHS", "libraries"));

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setConfigs(Optional.of(configs))
        .setUseBuckHeaderMaps(Optional.of(false))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Library.framework"))))))
        .build();

    BuildTarget testTarget = BuildTarget.builder("//foo", "xctest").build();
    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setConfigs(Optional.of(configs))
        .setUseBuckHeaderMaps(Optional.of(false))
        .setSrcs(
            Optional.of(
                ImmutableList.of(SourceWithFlags.of(new TestSourcePath("fooTest.m")))))
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(libraryNode, testNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:xctest");

    ImmutableMap<String, String> settings = getBuildSettings(testTarget, target, "Debug");
    assertEquals(
        "headers $BUILT_PRODUCTS_DIR/F4XWM33PHJWGSYQ/Headers",
        settings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        "libraries $BUILT_PRODUCTS_DIR",
        settings.get("LIBRARY_SEARCH_PATHS"));

    assertEquals("Should have exact number of build phases", 2, target.getBuildPhases().size());

    assertHasSingletonSourcesPhaseWithSourcesAndFlags(
        target,
        ImmutableMap.of("fooTest.m", Optional.<String>absent()));

    assertHasSingletonFrameworksPhaseWithFrameworkEntries(
        target,
        ImmutableList.of("$SDKROOT/Library.framework"));
  }

  @Test
  public void testAppleLibraryWithoutSourcesWithHeaders() throws IOException {
    ImmutableSortedMap<String, ImmutableMap<String, String>> configs = ImmutableSortedMap.of(
        "Debug",
        ImmutableMap.of(
            "HEADER_SEARCH_PATHS", "headers",
            "LIBRARY_SEARCH_PATHS", "libraries"));

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setConfigs(Optional.of(configs))
        .setUseBuckHeaderMaps(Optional.of(false))
        .setExportedHeaders(
            ImmutableSortedSet.<SourcePath>of(
                new TestSourcePath("HeaderGroup1/bar.h")))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Library.framework"))))))
        .build();

    BuildTarget testTarget = BuildTarget.builder("//foo", "xctest").build();
    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setConfigs(Optional.of(configs))
        .setUseBuckHeaderMaps(Optional.of(false))
        .setSrcs(
            Optional.of(
                ImmutableList.of(SourceWithFlags.of(new TestSourcePath("fooTest.m")))))
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(libraryNode, testNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:xctest");

    ImmutableMap<String, String> settings = getBuildSettings(testTarget, target, "Debug");
    assertEquals(
        "headers $BUILT_PRODUCTS_DIR/F4XWM33PHJWGSYQ/Headers",
        settings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        "libraries $BUILT_PRODUCTS_DIR",
        settings.get("LIBRARY_SEARCH_PATHS"));

    assertEquals("Should have exact number of build phases", 2, target.getBuildPhases().size());

    assertHasSingletonSourcesPhaseWithSourcesAndFlags(
        target,
        ImmutableMap.of("fooTest.m", Optional.<String>absent()));

    assertHasSingletonFrameworksPhaseWithFrameworkEntries(
        target,
        ImmutableList.of("$SDKROOT/Library.framework"));
  }

  @Test
  public void testAppleTestRule() throws IOException {
    BuildTarget testTarget = BuildTarget.builder("//foo", "xctest").build();
    TargetNode<?> testNode = AppleTestBuilder
        .createBuilder(testTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setUseBuckHeaderMaps(Optional.of(false))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(testNode));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:xctest");
    assertEquals(target.getProductType(), ProductType.UNIT_TEST);
    assertThat(target.isa(), equalTo("PBXNativeTarget"));
    PBXFileReference productReference = target.getProductReference();
    assertEquals("xctest.xctest", productReference.getName());
  }

  @Test
  public void testAppleBinaryRule() throws IOException {
    BuildTarget depTarget = BuildTarget.builder("//dep", "dep").build();
    TargetNode<?> depNode = AppleLibraryBuilder
        .createBuilder(depTarget)
        .setSrcs(Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("e.m")))))
        .setUseBuckHeaderMaps(Optional.of(false))
        .build();

    BuildTarget binaryTarget = BuildTarget.builder("//foo", "binary").build();
    TargetNode<?> binaryNode = AppleBinaryBuilder
        .createBuilder(binaryTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setSrcs(
            Optional.of(
                ImmutableList.of(
                    SourceWithFlags.of(
                        new TestSourcePath("foo.m"), ImmutableList.of("-foo")))))
        .setExtraXcodeSources(
            Optional.of(
                ImmutableList.<SourcePath>of(
                    new TestSourcePath("libsomething.a"))))
        .setHeaders(
            ImmutableSortedSet.<SourcePath>of(
                new TestSourcePath("foo.h")))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("Foo.framework"))))))
        .setDeps(Optional.of(ImmutableSortedSet.of(depTarget)))
        .setGid(Optional.<String>absent())
        .setHeaderPathPrefix(Optional.<String>absent())
        .setUseBuckHeaderMaps(Optional.of(false))
        .setPrefixHeader(Optional.<SourcePath>absent())
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(depNode, binaryNode));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:binary");
    assertHasConfigurations(target, "Debug");
    assertEquals(target.getProductType(), ProductType.TOOL);
    assertEquals("Should have exact number of build phases", 3, target.getBuildPhases().size());
    assertHasSingletonSourcesPhaseWithSourcesAndFlags(
        target,
        ImmutableMap.of(
            "foo.m", Optional.of("-foo"),
            "libsomething.a", Optional.<String>absent()));
    assertHasSingletonFrameworksPhaseWithFrameworkEntries(
        target,
        ImmutableList.of(
            "$SDKROOT/Foo.framework",
            // Propagated library from deps.
            "$BUILT_PRODUCTS_DIR/libdep.a"));

    // this test does not have a dependency on any asset catalogs, so verify no build phase for them
    // exists.
    assertFalse(hasShellScriptPhaseToCompileAssetCatalogs(target));
  }

  @Test
  public void testAppleBundleRuleWithPreBuildScriptDependency() throws IOException {
    BuildTarget scriptTarget = BuildTarget.builder("//foo", "pre_build_script").build();
    TargetNode<?> scriptNode = XcodePrebuildScriptBuilder
        .createBuilder(scriptTarget)
        .setCmd("script.sh")
        .build();

    BuildTarget resourceTarget = BuildTarget.builder("//foo", "resource").build();
    TargetNode<?> resourceNode = AppleResourceBuilder
        .createBuilder(resourceTarget)
        .setFiles(ImmutableSet.<SourcePath>of(new TestSourcePath("bar.png")))
        .setDirs(ImmutableSet.<SourcePath>of())
        .build();

    BuildTarget sharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> sharedLibraryNode = AppleLibraryBuilder
        .createBuilder(sharedLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(resourceTarget)))
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(sharedLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(scriptTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(scriptNode, resourceNode, sharedLibraryNode, bundleNode));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(
        project, "//foo:bundle");
    assertThat(target.getName(), equalTo("//foo:bundle"));
    assertThat(target.isa(), equalTo("PBXNativeTarget"));

    PBXShellScriptBuildPhase shellScriptBuildPhase =
        getSingletonPhaseByType(
            target,
            PBXShellScriptBuildPhase.class);

    assertThat(
        shellScriptBuildPhase.getShellScript(),
        equalTo("script.sh"));

    // Assert that the pre-build script phase comes before resources are copied.
    assertThat(
        target.getBuildPhases().get(0),
        instanceOf(PBXShellScriptBuildPhase.class));

    assertThat(
        target.getBuildPhases().get(1),
        instanceOf(PBXResourcesBuildPhase.class));
  }

  @Test
  public void testAppleBundleRuleWithPostBuildScriptDependency() throws IOException {
    BuildTarget scriptTarget = BuildTarget.builder("//foo", "post_build_script").build();
    TargetNode<?> scriptNode = XcodePostbuildScriptBuilder
        .createBuilder(scriptTarget)
        .setCmd("script.sh")
        .build();

    BuildTarget resourceTarget = BuildTarget.builder("//foo", "resource").build();
    TargetNode<?> resourceNode = AppleResourceBuilder
        .createBuilder(resourceTarget)
        .setFiles(ImmutableSet.<SourcePath>of(new TestSourcePath("bar.png")))
        .setDirs(ImmutableSet.<SourcePath>of())
        .build();

    BuildTarget sharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> sharedLibraryNode = AppleLibraryBuilder
        .createBuilder(sharedLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(resourceTarget)))
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(sharedLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(scriptTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(scriptNode, resourceNode, sharedLibraryNode, bundleNode));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(
        project, "//foo:bundle");
    assertThat(target.getName(), equalTo("//foo:bundle"));
    assertThat(target.isa(), equalTo("PBXNativeTarget"));

    PBXShellScriptBuildPhase shellScriptBuildPhase =
        getSingletonPhaseByType(
            target,
            PBXShellScriptBuildPhase.class);

    assertThat(
        shellScriptBuildPhase.getShellScript(),
        equalTo("script.sh"));

    // Assert that the post-build script phase comes after resources are copied.
    assertThat(
        target.getBuildPhases().get(0),
        instanceOf(PBXResourcesBuildPhase.class));

    assertThat(
        target.getBuildPhases().get(1),
        instanceOf(PBXShellScriptBuildPhase.class));
  }

  @Test
  public void testAppleBundleRuleWithRNLibraryDependency() throws IOException {
    BuildTarget rnLibraryTarget = BuildTarget.builder("//foo", "rn_library").build();
    ProjectFilesystem filesystem = new AllExistingProjectFilesystem();
    ReactNativeBuckConfig buckConfig = new ReactNativeBuckConfig(new FakeBuckConfig(
        ImmutableMap.of("react-native", ImmutableMap.of("packager", "react-native/packager.sh")),
        filesystem));
    TargetNode<?>  rnLibraryNode = IosReactNativeLibraryBuilder
        .builder(rnLibraryTarget, buckConfig)
        .setBundleName("Apps/Foo/FooBundle.js")
        .setEntryPath(new PathSourcePath(filesystem, Paths.get("js/FooApp.js")))
        .build();

    BuildTarget sharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> sharedLibraryNode = AppleLibraryBuilder
        .createBuilder(sharedLibraryTarget)
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(sharedLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(rnLibraryTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(rnLibraryNode, sharedLibraryNode, bundleNode));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(
        project, "//foo:bundle");
    assertThat(target.getName(), equalTo("//foo:bundle"));
    assertThat(target.isa(), equalTo("PBXNativeTarget"));

    PBXShellScriptBuildPhase shellScriptBuildPhase =
        getSingletonPhaseByType(
            target,
            PBXShellScriptBuildPhase.class);

    assertThat(
        shellScriptBuildPhase.getShellScript(),
        startsWith("BASE_DIR="));
  }

  @Test
  public void testNoBundleFlavoredAppleBundleRuleWithRNLibraryDependency() throws IOException {
    BuildTarget rnLibraryTarget = BuildTarget.builder("//foo", "rn_library").build();
    ProjectFilesystem filesystem = new AllExistingProjectFilesystem();
    ReactNativeBuckConfig buckConfig = new ReactNativeBuckConfig(new FakeBuckConfig(
        ImmutableMap.of("react-native", ImmutableMap.of("packager", "react-native/packager.sh")),
        filesystem));
    TargetNode<?>  rnLibraryNode = IosReactNativeLibraryBuilder
        .builder(rnLibraryTarget, buckConfig)
        .setBundleName("Apps/Foo/FooBundle.js")
        .setEntryPath(new PathSourcePath(filesystem, Paths.get("js/FooApp.js")))
        .build();

    BuildTarget sharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> sharedLibraryNode = AppleLibraryBuilder
        .createBuilder(sharedLibraryTarget)
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle")
        .addFlavors(ReactNativeFlavors.DO_NOT_BUNDLE)
        .build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(sharedLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(rnLibraryTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(rnLibraryNode, sharedLibraryNode, bundleNode),
        ImmutableSet.<ProjectGenerator.Option>of(),
        Optional.of(Paths.get("js/react-native/runServer.sh")));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(
        project, "//foo:bundle#rn_no_bundle");
    assertThat(target.getName(), equalTo("//foo:bundle#rn_no_bundle"));
    assertThat(target.isa(), equalTo("PBXNativeTarget"));

    Iterator<PBXShellScriptBuildPhase> phases = Iterables.filter(
        target.getBuildPhases(),
        PBXShellScriptBuildPhase.class).iterator();

    assertThat(phases.hasNext(), is(true));
    assertThat(
        phases.next().getShellScript(),
        containsString("rm -rf ${JS_OUT}"));

    assertThat(phases.hasNext(), is(true));
    assertThat(
        phases.next().getShellScript(),
        endsWith("js/react-native/runServer.sh"));

    assertThat(phases.hasNext(), is(false));
  }

  @Test
  public void testAppleBundleRuleForSharedLibraryFramework() throws IOException {
    BuildTarget sharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> sharedLibraryNode = AppleLibraryBuilder
        .createBuilder(sharedLibraryTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .build();

    BuildTarget buildTarget = BuildTarget.builder("//foo", "bundle").build();
    TargetNode<?> node = AppleBundleBuilder
        .createBuilder(buildTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.FRAMEWORK))
        .setBinary(sharedLibraryTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(sharedLibraryNode, node),
        ImmutableSet.<ProjectGenerator.Option>of());
    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(project, "//foo:bundle");
    assertEquals(target.getProductType(), ProductType.FRAMEWORK);
    assertThat(target.isa(), equalTo("PBXNativeTarget"));
    PBXFileReference productReference = target.getProductReference();
    assertEquals("bundle.framework", productReference.getName());
    assertEquals(Optional.of("wrapper.framework"), productReference.getExplicitFileType());

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals(
        "framework",
        settings.get("WRAPPER_EXTENSION"));
  }

  @Test
  public void testAppleResourceWithVariantGroupSetsFileTypeBasedOnPath() throws IOException {
    BuildTarget resourceTarget = BuildTarget.builder("//foo", "resource").build();
    TargetNode<?> resourceNode = AppleResourceBuilder
        .createBuilder(resourceTarget)
        .setFiles(ImmutableSet.<SourcePath>of())
        .setDirs(ImmutableSet.<SourcePath>of())
        .setVariants(
            Optional.<Set<SourcePath>>of(
                ImmutableSet.<SourcePath>of(
                    new TestSourcePath("Base.lproj/Bar.storyboard"))))
        .build();
    BuildTarget fooLibraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> fooLibraryNode = AppleLibraryBuilder
        .createBuilder(fooLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(resourceTarget)))
        .build();
    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(fooLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(resourceTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(fooLibraryNode, bundleNode, resourceNode),
        ImmutableSet.<ProjectGenerator.Option>of());
    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXGroup targetGroup =
        project.getMainGroup().getOrCreateChildGroupByName(bundleTarget.getFullyQualifiedName());
    PBXGroup resourcesGroup = targetGroup.getOrCreateChildGroupByName("Resources");
    PBXVariantGroup storyboardGroup = (PBXVariantGroup) Iterables.get(
        resourcesGroup.getChildren(),
        0);
    List<PBXReference> storyboardGroupChildren = storyboardGroup.getChildren();
    assertEquals(1, storyboardGroupChildren.size());
    assertTrue(storyboardGroupChildren.get(0) instanceof PBXFileReference);
    PBXFileReference baseStoryboardReference = (PBXFileReference) storyboardGroupChildren.get(0);

    assertEquals("Base", baseStoryboardReference.getName());

    // Make sure the file type is set from the path.
    assertEquals(Optional.of("file.storyboard"), baseStoryboardReference.getLastKnownFileType());
    assertEquals(Optional.<String>absent(), baseStoryboardReference.getExplicitFileType());
  }

  @Test
  public void testAppleBundleRuleWithCustomXcodeProductType() throws IOException {
    BuildTarget sharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> sharedLibraryNode = AppleLibraryBuilder
        .createBuilder(sharedLibraryTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .build();

    BuildTarget buildTarget = BuildTarget.builder("//foo", "custombundle").build();
    TargetNode<?> node = AppleBundleBuilder
        .createBuilder(buildTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.FRAMEWORK))
        .setBinary(sharedLibraryTarget)
        .setXcodeProductType(Optional.of("com.facebook.buck.niftyProductType"))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(sharedLibraryNode, node),
        ImmutableSet.<ProjectGenerator.Option>of());
    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(project, "//foo:custombundle");
    assertEquals(
        target.getProductType(),
        ProductType.of("com.facebook.buck.niftyProductType"));
    assertThat(target.isa(), equalTo("PBXNativeTarget"));
    PBXFileReference productReference = target.getProductReference();
    assertEquals("custombundle.framework", productReference.getName());
    assertEquals(Optional.of("wrapper.framework"), productReference.getExplicitFileType());

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals(
        "framework",
        settings.get("WRAPPER_EXTENSION"));
  }

  @Test
  public void testCoreDataModelRuleAddsReference() throws IOException {
    BuildTarget modelTarget = BuildTarget.builder("//foo", "model").build();
    TargetNode<?> modelNode = CoreDataModelBuilder
        .createBuilder(modelTarget)
        .setPath(new TestSourcePath("foo.xcdatamodel").getRelativePath())
        .build();

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(modelTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(modelNode, libraryNode));

    projectGenerator.createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXGroup targetGroup =
        project.getMainGroup().getOrCreateChildGroupByName(libraryTarget.getFullyQualifiedName());
    PBXGroup resourcesGroup = targetGroup.getOrCreateChildGroupByName("Resources");

    assertThat(resourcesGroup.getChildren(), hasSize(1));

    PBXFileReference modelReference = (PBXFileReference) Iterables.get(
        resourcesGroup.getChildren(),
        0);
    assertEquals("foo.xcdatamodel", modelReference.getName());
  }

  @Test
  public void ruleToTargetMapContainsPBXTarget() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setSrcs(
            Optional.of(
                ImmutableList.of(
                    SourceWithFlags.of(
                        new TestSourcePath("foo.m"), ImmutableList.of("-foo")),
                    SourceWithFlags.of(new TestSourcePath("bar.m")))))
        .setHeaders(
            ImmutableSortedSet.<SourcePath>of(
                new TestSourcePath("foo.h")))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    assertEquals(
        buildTarget, Iterables.getOnlyElement(
            projectGenerator.getBuildTargetToGeneratedTargetMap().keySet()));

    PBXTarget target = Iterables.getOnlyElement(
        projectGenerator.getBuildTargetToGeneratedTargetMap().values());
    assertHasSingletonSourcesPhaseWithSourcesAndFlags(
        target, ImmutableMap.of(
            "foo.m", Optional.of("-foo"),
            "bar.m", Optional.<String>absent()));
  }

  @Test
  public void generatedGidsForTargetsAreStable() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "foo").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:foo");
    String expectedGID = String.format(
        "%08X%08X%08X", target.isa().hashCode(), target.getName().hashCode(), 0);
    assertEquals(
        "expected GID has correct value (value from which it's derived have not changed)",
        "E66DC04E2245423200000000", expectedGID);
    assertEquals("generated GID is same as expected", expectedGID, target.getGlobalID());
  }

  @Test
  public void stopsLinkingRecursiveDependenciesAtSharedLibraries() throws IOException {
    BuildTarget dependentStaticLibraryTarget = BuildTarget.builder("//dep", "static").build();
    TargetNode<?> dependentStaticLibraryNode = AppleLibraryBuilder
        .createBuilder(dependentStaticLibraryTarget)
        .build();

    BuildTarget dependentSharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> dependentSharedLibraryNode = AppleLibraryBuilder
        .createBuilder(dependentSharedLibraryTarget)
        .setSrcs(Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("empty.m")))))
        .setDeps(Optional.of(ImmutableSortedSet.of(dependentStaticLibraryTarget)))
        .build();

    BuildTarget libraryTarget = BuildTarget
        .builder("//foo", "library")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(dependentSharedLibraryTarget)))
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "final").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(libraryTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(
            dependentStaticLibraryNode,
            dependentSharedLibraryNode,
            libraryNode,
            bundleNode));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:final");
    assertEquals(target.getProductType(), ProductType.BUNDLE);
    assertEquals("Should have exact number of build phases ", 2, target.getBuildPhases().size());
    assertHasSingletonFrameworksPhaseWithFrameworkEntries(
        target,
        ImmutableList.of(
            "$BUILT_PRODUCTS_DIR/libshared.dylib"));
  }

  @Test
  public void stopsLinkingRecursiveDependenciesAtBundles() throws IOException {
    BuildTarget dependentStaticLibraryTarget = BuildTarget.builder("//dep", "static").build();
    TargetNode<?> dependentStaticLibraryNode = AppleLibraryBuilder
        .createBuilder(dependentStaticLibraryTarget)
        .build();

    BuildTarget dependentSharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> dependentSharedLibraryNode = AppleLibraryBuilder
        .createBuilder(dependentSharedLibraryTarget)
        .setSrcs(Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("e.m")))))
        .setDeps(Optional.of(ImmutableSortedSet.of(dependentStaticLibraryTarget)))
        .build();

    BuildTarget dependentFrameworkTarget = BuildTarget.builder("//dep", "framework").build();
    TargetNode<?> dependentFrameworkNode = AppleBundleBuilder
        .createBuilder(dependentFrameworkTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.FRAMEWORK))
        .setBinary(dependentSharedLibraryTarget)
        .build();

    BuildTarget libraryTarget = BuildTarget
        .builder("//foo", "library")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(dependentFrameworkTarget)))
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "final").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(libraryTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(
            dependentStaticLibraryNode,
            dependentSharedLibraryNode,
            dependentFrameworkNode,
            libraryNode,
            bundleNode));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:final");
    assertEquals(target.getProductType(), ProductType.BUNDLE);
    assertEquals("Should have exact number of build phases ", 2, target.getBuildPhases().size());
    assertHasSingletonFrameworksPhaseWithFrameworkEntries(
        target,
        ImmutableList.of("$BUILT_PRODUCTS_DIR/framework.framework"));
  }

  @Test
  public void stopsCopyingRecursiveDependenciesAtBundles() throws IOException {
    BuildTarget dependentStaticLibraryTarget = BuildTarget.builder("//dep", "static").build();
    TargetNode<?> dependentStaticLibraryNode = AppleLibraryBuilder
        .createBuilder(dependentStaticLibraryTarget)
        .build();

    BuildTarget dependentStaticFrameworkTarget = BuildTarget
        .builder("//dep", "static-framework")
        .build();
    TargetNode<?> dependentStaticFrameworkNode = AppleBundleBuilder
        .createBuilder(dependentStaticFrameworkTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.FRAMEWORK))
        .setBinary(dependentStaticLibraryTarget)
        .build();

    BuildTarget dependentSharedLibraryTarget = BuildTarget
        .builder("//dep", "shared")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> dependentSharedLibraryNode = AppleLibraryBuilder
        .createBuilder(dependentSharedLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(dependentStaticFrameworkTarget)))
        .build();

    BuildTarget dependentFrameworkTarget = BuildTarget.builder("//dep", "framework").build();
    TargetNode<?> dependentFrameworkNode = AppleBundleBuilder
        .createBuilder(dependentFrameworkTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.FRAMEWORK))
        .setBinary(dependentSharedLibraryTarget)
        .build();

    BuildTarget libraryTarget = BuildTarget
        .builder("//foo", "library")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setSrcs(Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("e.m")))))
        .setDeps(Optional.of(ImmutableSortedSet.of(dependentFrameworkTarget)))
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "final").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(libraryTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        // ant needs this to be explicit
        ImmutableSet.<TargetNode<?>>of(
            dependentStaticLibraryNode,
            dependentStaticFrameworkNode,
            dependentSharedLibraryNode,
            dependentFrameworkNode,
            libraryNode,
            bundleNode));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:final");
    assertEquals(target.getProductType(), ProductType.BUNDLE);
    assertEquals("Should have exact number of build phases ", 2, target.getBuildPhases().size());
    assertHasSingletonCopyFilesPhaseWithFileEntries(
        target,
        ImmutableList.of("$BUILT_PRODUCTS_DIR/framework.framework"));
  }

  @Test
  public void bundlesDontLinkTheirOwnBinary() throws IOException {
    BuildTarget libraryTarget = BuildTarget
        .builder("//foo", "library")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "final").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(libraryTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(libraryNode, bundleNode));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:final");
    assertEquals(target.getProductType(), ProductType.BUNDLE);
    assertEquals("Should have exact number of build phases ", 0, target.getBuildPhases().size());
  }

  @Test
  public void resourcesInDependenciesPropagatesToBundles() throws IOException {
    BuildTarget resourceTarget = BuildTarget.builder("//foo", "res").build();
    TargetNode<?> resourceNode = AppleResourceBuilder
        .createBuilder(resourceTarget)
        .setFiles(ImmutableSet.<SourcePath>of(new TestSourcePath("bar.png")))
        .setDirs(ImmutableSet.<SourcePath>of(new TestSourcePath("foodir")))
        .build();

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(resourceTarget)))
        .build();

    BuildTarget bundleLibraryTarget = BuildTarget.builder("//foo", "bundlelib").build();
    TargetNode<?> bundleLibraryNode = AppleLibraryBuilder
        .createBuilder(bundleLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryTarget)))
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(bundleLibraryTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(resourceNode, libraryNode, bundleLibraryNode, bundleNode));
    projectGenerator.createXcodeProjects();

    PBXProject generatedProject = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(
        generatedProject,
        "//foo:bundle");
    assertHasSingletonResourcesPhaseWithEntries(target, "bar.png", "foodir");
  }

  @Test
  public void assetCatalogsInDependenciesPropogatesToBundles() throws IOException {
    BuildTarget assetCatalogTarget = BuildTarget.builder("//foo", "asset_catalog").build();
    TargetNode<?> assetCatalogNode = AppleAssetCatalogBuilder
        .createBuilder(assetCatalogTarget)
        .setDirs(ImmutableSortedSet.of(Paths.get("AssetCatalog.xcassets")))
        .build();

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(assetCatalogTarget)))
        .build();

    BuildTarget bundleLibraryTarget = BuildTarget.builder("//foo", "bundlelib").build();
    TargetNode<?> bundleLibraryNode = AppleLibraryBuilder
        .createBuilder(bundleLibraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(libraryTarget)))
        .build();

    BuildTarget bundleTarget = BuildTarget.builder("//foo", "bundle").build();
    TargetNode<?> bundleNode = AppleBundleBuilder
        .createBuilder(bundleTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.BUNDLE))
        .setBinary(bundleLibraryTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(assetCatalogNode, libraryNode, bundleLibraryNode, bundleNode));
    projectGenerator.createXcodeProjects();

    PBXProject generatedProject = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(
        generatedProject,
        "//foo:bundle");
    assertTrue(hasShellScriptPhaseToCompileAssetCatalogs(target));
  }

  @Test
  public void generatedTargetConfigurationHasRepoRootSet() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "rule").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node),
        ImmutableSet.<ProjectGenerator.Option>of());
    projectGenerator.createXcodeProjects();

    PBXProject generatedProject = projectGenerator.getGeneratedProject();
    ImmutableMap<String, String> settings = getBuildSettings(
        buildTarget, generatedProject.getTargets().get(0), "Debug");
    assertThat(settings, hasKey("REPO_ROOT"));
    assertEquals(
        projectFilesystem.getRootPath().toAbsolutePath().normalize().toString(),
        settings.get("REPO_ROOT"));
  }

  /**
   * The project configurations should have named entries corresponding to every existing target
   * configuration for targets in the project.
   */
  @Test
  public void generatedProjectConfigurationListIsUnionOfAllTargetConfigurations()
      throws IOException {
    BuildTarget buildTarget1 = BuildTarget.builder("//foo", "rule1").build();
    TargetNode<?> node1 = AppleLibraryBuilder
        .createBuilder(buildTarget1)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Conf1", ImmutableMap.<String, String>of(),
                    "Conf2", ImmutableMap.<String, String>of())))
        .build();

    BuildTarget buildTarget2 = BuildTarget.builder("//foo", "rule2").build();
    TargetNode<?> node2 = AppleLibraryBuilder
        .createBuilder(buildTarget2)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Conf2", ImmutableMap.<String, String>of(),
                    "Conf3", ImmutableMap.<String, String>of())))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(node1, node2));
    projectGenerator.createXcodeProjects();

    PBXProject generatedProject = projectGenerator.getGeneratedProject();
    Map<String, XCBuildConfiguration> configurations =
        generatedProject.getBuildConfigurationList().getBuildConfigurationsByName().asMap();
    assertThat(configurations, hasKey("Conf1"));
    assertThat(configurations, hasKey("Conf2"));
    assertThat(configurations, hasKey("Conf3"));
  }

  @Test
  public void shouldEmitFilesForBuildSettingPrefixedFrameworks() throws IOException {
    BuildTarget buildTarget = BuildTarget
        .builder("//foo", "rule")
        .addFlavors(CxxDescriptionEnhancer.SHARED_FLAVOR)
        .build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setUseBuckHeaderMaps(Optional.of(false))
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setFrameworks(
            Optional.of(
                ImmutableSortedSet.of(
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.BUILT_PRODUCTS_DIR,
                            Paths.get("libfoo.a"))),
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SDKROOT,
                            Paths.get("libfoo.a"))),
                    FrameworkPath.ofSourceTreePath(
                        new SourceTreePath(
                            PBXReference.SourceTree.SOURCE_ROOT,
                            Paths.get("libfoo.a"))))))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));
    projectGenerator.createXcodeProjects();

    PBXProject generatedProject = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(generatedProject, "//foo:rule#shared");
    assertHasSingletonFrameworksPhaseWithFrameworkEntries(
        target,
        ImmutableList.of(
            "$BUILT_PRODUCTS_DIR/libfoo.a",
            "$SDKROOT/libfoo.a",
            "$SOURCE_ROOT/libfoo.a"));

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals(
        "$(inherited) ",
        settings.get("HEADER_SEARCH_PATHS"));
    assertEquals(
        null,
        settings.get("USER_HEADER_SEARCH_PATHS"));
    assertEquals(
        "$(inherited) $BUILT_PRODUCTS_DIR $SDKROOT $SOURCE_ROOT",
        settings.get("LIBRARY_SEARCH_PATHS"));
    assertEquals(
        "$(inherited) $BUILT_PRODUCTS_DIR",
        settings.get("FRAMEWORK_SEARCH_PATHS"));

  }

  @Test
  public void testGeneratedProjectIsNotReadOnlyIfOptionNotSpecified() throws IOException {
    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of());

    projectGenerator.createXcodeProjects();

    assertTrue(fakeProjectFilesystem.getFileAttributesAtPath(OUTPUT_PROJECT_FILE_PATH).isEmpty());
  }

  @Test
  public void testGeneratedProjectIsReadOnlyIfOptionSpecified() throws IOException {
    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(),
        ImmutableSet.of(ProjectGenerator.Option.GENERATE_READ_ONLY_FILES));

    projectGenerator.createXcodeProjects();

    ImmutableSet<PosixFilePermission> permissions =
      ImmutableSet.of(
          PosixFilePermission.OWNER_READ,
          PosixFilePermission.GROUP_READ,
          PosixFilePermission.OTHERS_READ);
    FileAttribute<?> expectedAttribute = PosixFilePermissions.asFileAttribute(permissions);
    // This is lame; Java's PosixFilePermissions class doesn't
    // implement equals() or hashCode() in its FileAttribute anonymous
    // class (http://tinyurl.com/nznhfhy).  So instead of comparing
    // the sets, we have to pull out the attribute and check its value
    // for equality.
    FileAttribute<?> actualAttribute =
      Iterables.getOnlyElement(
          fakeProjectFilesystem.getFileAttributesAtPath(OUTPUT_PROJECT_FILE_PATH));
    assertEquals(
        expectedAttribute.value(),
        actualAttribute.value());
  }

  @Test
  public void targetGidInDescriptionSetsTargetGidInGeneratedProject() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setGid(Optional.of("D00D64738"))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");
    // Ensure the GID for the target uses the gid value in the description.
    assertThat(target.getGlobalID(), equalTo("D00D64738"));
  }

  @Test
  public void targetGidInDescriptionReservesGidFromUseByAnotherTarget() throws IOException {
    BuildTarget fooTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> fooNode = AppleLibraryBuilder
        .createBuilder(fooTarget)
        .setGid(Optional.of("E66DC04E36F2D8BE00000000"))
        .build();

    BuildTarget barTarget = BuildTarget.builder("//bar", "lib").build();
    TargetNode<?> barNode = AppleLibraryBuilder
        .createBuilder(barTarget)
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(fooNode, barNode));
    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//bar:lib");
    // Note the '1': normally //bar:lib's GID would be
    // E66DC04E36F2D8BE00000000 but we hard-coded that in //foo:lib, so //bar:lib
    // will try and fail to use GID, as it'll already have been reserved.
    String expectedGID = String.format(
        "%08X%08X%08X", target.isa().hashCode(), target.getName().hashCode(), 1);
    assertEquals(
        "expected GID has correct value",
        "E66DC04E36F2D8BE00000001", expectedGID);
    assertEquals("generated GID is same as expected", expectedGID, target.getGlobalID());
  }

  @Test
  public void conflictingHardcodedGidsThrow() throws IOException {
    BuildTarget fooTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> fooNode = AppleLibraryBuilder
        .createBuilder(fooTarget)
        .setGid(Optional.of("E66DC04E36F2D8BE00000000"))
        .build();

    BuildTarget barTarget = BuildTarget.builder("//bar", "lib").build();
    TargetNode<?> barNode = AppleLibraryBuilder
        .createBuilder(barTarget)
        .setGid(Optional.of("E66DC04E36F2D8BE00000000"))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(fooNode, barNode));

    thrown.expect(HumanReadableException.class);
    thrown.expectMessage(
        "Targets [//bar:lib, //foo:lib] have the same hardcoded GID (E66DC04E36F2D8BE00000000)");

    projectGenerator.createXcodeProjects();
  }

  @Test
  public void projectIsRewrittenIfContentsHaveChanged() throws IOException {
    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of());

    clock.setCurrentTimeMillis(49152);
    projectGenerator.createXcodeProjects();
    assertThat(
        projectFilesystem.getLastModifiedTime(OUTPUT_PROJECT_FILE_PATH),
        equalTo(49152L));

    BuildTarget buildTarget = BuildTarget.builder("//foo", "foo").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .build();
    ProjectGenerator projectGenerator2 = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    clock.setCurrentTimeMillis(64738);
    projectGenerator2.createXcodeProjects();
    assertThat(
        projectFilesystem.getLastModifiedTime(OUTPUT_PROJECT_FILE_PATH),
        equalTo(64738L));
  }

  @Test
  public void projectIsNotRewrittenIfContentsHaveNotChanged() throws IOException {
    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of());

    clock.setCurrentTimeMillis(49152);
    projectGenerator.createXcodeProjects();
    assertThat(
        projectFilesystem.getLastModifiedTime(OUTPUT_PROJECT_FILE_PATH),
        equalTo(49152L));

    ProjectGenerator projectGenerator2 = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of());

    clock.setCurrentTimeMillis(64738);
    projectGenerator2.createXcodeProjects();
    assertThat(
        projectFilesystem.getLastModifiedTime(OUTPUT_PROJECT_FILE_PATH),
        equalTo(49152L));
  }

  @Test
  public void nonexistentResourceDirectoryShouldThrow() throws IOException {
    ImmutableSet<TargetNode<?>> nodes = setupSimpleLibraryWithResources(
        ImmutableSet.<SourcePath>of(),
        ImmutableSet.<SourcePath>of(new TestSourcePath("nonexistent-directory")));

    thrown.expect(HumanReadableException.class);
    thrown.expectMessage(
        "nonexistent-directory specified in the dirs parameter of //foo:res is not a directory");

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(nodes);
    projectGenerator.createXcodeProjects();
  }

  @Test
  public void nonexistentResourceFileShouldThrow() throws IOException {
    ImmutableSet<TargetNode<?>> nodes = setupSimpleLibraryWithResources(
        ImmutableSet.<SourcePath>of(new TestSourcePath("nonexistent-file.png")),
        ImmutableSet.<SourcePath>of());

    thrown.expect(HumanReadableException.class);
    thrown.expectMessage(
        "nonexistent-file.png specified in the files parameter of //foo:res is not a regular file");

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(nodes);
    projectGenerator.createXcodeProjects();
  }

  @Test
  public void usingFileAsResourceDirectoryShouldThrow() throws IOException {
    ImmutableSet<TargetNode<?>> nodes = setupSimpleLibraryWithResources(
        ImmutableSet.<SourcePath>of(),
        ImmutableSet.<SourcePath>of(new TestSourcePath("bar.png")));

    thrown.expect(HumanReadableException.class);
    thrown.expectMessage(
        "bar.png specified in the dirs parameter of //foo:res is not a directory");

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(nodes);
    projectGenerator.createXcodeProjects();
  }

  @Test
  public void usingDirectoryAsResourceFileShouldThrow() throws IOException {
    ImmutableSet<TargetNode<?>> nodes = setupSimpleLibraryWithResources(
        ImmutableSet.<SourcePath>of(new TestSourcePath("foodir")),
        ImmutableSet.<SourcePath>of());

    thrown.expect(HumanReadableException.class);
    thrown.expectMessage(
        "foodir specified in the files parameter of //foo:res is not a regular file");

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(nodes);
    projectGenerator.createXcodeProjects();
  }

  @Test
  public void usingBuildTargetSourcePathInResourceDirsOrFilesDoesNotThrow() throws IOException {
    BuildTarget buildTarget = BuildTargetFactory.newInstance("//some:rule");
    SourcePath sourcePath = new BuildTargetSourcePath(buildTarget);
    TargetNode<?> generatingTarget = GenruleBuilder.newGenruleBuilder(buildTarget)
        .setCmd("echo HI")
        .build();

    ImmutableSet<TargetNode<?>> nodes = FluentIterable.from(
        setupSimpleLibraryWithResources(
            ImmutableSet.of(sourcePath),
            ImmutableSet.of(sourcePath)))
        .append(generatingTarget)
        .toSet();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(nodes);
    projectGenerator.createXcodeProjects();
  }

  @Test
  public void testGeneratingTestsAsStaticLibraries() throws IOException {
    TargetNode<AppleTestDescription.Arg> libraryTestStatic =
        AppleTestBuilder.createBuilder(BuildTarget.builder("//foo", "libraryTestStatic").build())
            .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
            .build();
    TargetNode<AppleTestDescription.Arg> libraryTestNotStatic =
        AppleTestBuilder.createBuilder(BuildTarget.builder("//foo", "libraryTestNotStatic").build())
            .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
            .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableList.<TargetNode<?>>of(libraryTestStatic, libraryTestNotStatic));
    projectGenerator
        .setTestsToGenerateAsStaticLibraries(ImmutableSet.of(libraryTestStatic))
        .createXcodeProjects();

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget libraryTestStaticTarget =
        assertTargetExistsAndReturnTarget(project, "//foo:libraryTestStatic");
    PBXTarget libraryTestNotStaticTarget =
        assertTargetExistsAndReturnTarget(project, "//foo:libraryTestNotStatic");
    assertThat(
        libraryTestStaticTarget.getProductType(),
        equalTo(ProductType.STATIC_LIBRARY));
    assertThat(
        libraryTestNotStaticTarget.getProductType(),
        equalTo(ProductType.UNIT_TEST));
  }

  @Test
  public void testGeneratingCombinedTests() throws IOException {
    TargetNode<AppleResourceDescription.Arg> testLibDepResource =
        AppleResourceBuilder.createBuilder(BuildTarget.builder("//lib", "deplibresource").build())
            .setFiles(ImmutableSet.<SourcePath>of(new TestSourcePath("bar.png")))
            .setDirs(ImmutableSet.<SourcePath>of())
            .build();
    TargetNode<AppleNativeTargetDescriptionArg> testLibDepLib =
        AppleLibraryBuilder.createBuilder(BuildTarget.builder("//libs", "deplib").build())
            .setFrameworks(
                Optional.of(
                    ImmutableSortedSet.of(
                        FrameworkPath.ofSourceTreePath(
                            new SourceTreePath(
                                PBXReference.SourceTree.SDKROOT,
                                Paths.get("DeclaredInTestLibDep.framework"))))))
            .setDeps(Optional.of(ImmutableSortedSet.of(testLibDepResource.getBuildTarget())))
            .setSrcs(Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("e.m")))))
            .build();
    TargetNode<AppleNativeTargetDescriptionArg> dep1 =
        AppleLibraryBuilder.createBuilder(BuildTarget.builder("//foo", "dep1").build())
            .setDeps(Optional.of(ImmutableSortedSet.of(testLibDepLib.getBuildTarget())))
            .setSrcs(Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("e.m")))))
            .setFrameworks(
                Optional.of(
                    ImmutableSortedSet.of(
                        FrameworkPath.ofSourceTreePath(
                            new SourceTreePath(
                                PBXReference.SourceTree.SDKROOT,
                                Paths.get("DeclaredInTestLib.framework"))))))
            .build();
    TargetNode<AppleNativeTargetDescriptionArg> dep2 =
        AppleLibraryBuilder.createBuilder(BuildTarget.builder("//foo", "dep2").build())
            .setSrcs(Optional.of(ImmutableList.of(SourceWithFlags.of(new TestSourcePath("e.m")))))
            .build();
    TargetNode<AppleTestDescription.Arg> xctest1 =
        AppleTestBuilder.createBuilder(BuildTarget.builder("//foo", "xctest1").build())
            .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
            .setDeps(Optional.of(ImmutableSortedSet.of(dep1.getBuildTarget())))
            .setFrameworks(
                Optional.of(
                    ImmutableSortedSet.of(
                        FrameworkPath.ofSourceTreePath(
                            new SourceTreePath(
                                PBXReference.SourceTree.SDKROOT,
                                Paths.get("DeclaredInTest.framework"))))))
            .build();
    TargetNode<AppleTestDescription.Arg> xctest2 =
        AppleTestBuilder.createBuilder(BuildTarget.builder("//foo", "xctest2").build())
            .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
            .setDeps(Optional.of(ImmutableSortedSet.of(dep2.getBuildTarget())))
            .build();

    ProjectGenerator projectGenerator = new ProjectGenerator(
        TargetGraphFactory.newInstance(
            testLibDepResource,
            testLibDepLib,
            dep1,
            dep2,
            xctest1,
            xctest2),
        ImmutableSet.<BuildTarget>of(),
        projectFilesystem,
        /* reactNativeServer */ Optional.<Path>absent(),
        OUTPUT_DIRECTORY,
        PROJECT_NAME,
        "BUCK",
        ProjectGenerator.SEPARATED_PROJECT_OPTIONS,
        Optional.<BuildTarget>absent(),
        ImmutableList.<String>of(),
        new Function<TargetNode<?>, Path>() {
          @Nullable
          @Override
          public Path apply(TargetNode<?> input) {
            return null;
          }
        })
        .setTestsToGenerateAsStaticLibraries(ImmutableSet.of(xctest1, xctest2))
        .setAdditionalCombinedTestTargets(
            ImmutableMultimap.of(
                AppleTestBundleParamsKey.fromAppleTestDescriptionArg(xctest1.getConstructorArg()),
                xctest1,
                AppleTestBundleParamsKey.fromAppleTestDescriptionArg(xctest2.getConstructorArg()),
                xctest2));
    projectGenerator.createXcodeProjects();

    ImmutableSet<PBXTarget> combinedTestTargets =
        projectGenerator.getBuildableCombinedTestTargets();
    assertThat(combinedTestTargets, hasSize(1));
    assertThat(combinedTestTargets, hasItem(targetWithName("_BuckCombinedTest-xctest-0")));

    PBXProject project = projectGenerator.getGeneratedProject();
    PBXTarget target = assertTargetExistsAndReturnTarget(project, "_BuckCombinedTest-xctest-0");
    assertHasSingletonSourcesPhaseWithSourcesAndFlags(
        target,
        ImmutableMap.of(
            BuckConstant.GEN_PATH.resolve("xcode-scripts/emptyFile.c").toString(),
            Optional.<String>absent()));
    assertHasSingletonFrameworksPhaseWithFrameworkEntries(
        target,
        ImmutableList.of(
            "$BUILT_PRODUCTS_DIR/libxctest1.a",
            "$BUILT_PRODUCTS_DIR/libxctest2.a",
            "$BUILT_PRODUCTS_DIR/libdeplib.a",
            "$BUILT_PRODUCTS_DIR/libdep1.a",
            "$BUILT_PRODUCTS_DIR/libdep2.a",
            "$SDKROOT/DeclaredInTestLib.framework",
            "$SDKROOT/DeclaredInTestLibDep.framework",
            "$SDKROOT/DeclaredInTest.framework"));
    assertHasSingletonResourcesPhaseWithEntries(
        target,
        "bar.png");
  }

  @Test
  public void testResolvingExportFile() throws IOException {
    BuildTarget source1Target = BuildTarget.builder("//Vendor", "source1").build();
    BuildTarget source2Target = BuildTarget.builder("//Vendor", "source2").build();
    BuildTarget source2RefTarget = BuildTarget.builder("//Vendor", "source2ref").build();
    BuildTarget source3Target = BuildTarget.builder("//Vendor", "source3").build();
    BuildTarget headerTarget = BuildTarget.builder("//Vendor", "header").build();
    BuildTarget libTarget = BuildTarget.builder("//Libraries", "foo").build();

    TargetNode<ExportFileDescription.Arg> source1 = ExportFileBuilder
        .newExportFileBuilder(source1Target)
        .setSrc(new PathSourcePath(projectFilesystem, Paths.get("Vendor/sources/source1")))
        .build();

    TargetNode<ExportFileDescription.Arg> source2 = ExportFileBuilder
        .newExportFileBuilder(source2Target)
        .setSrc(new PathSourcePath(projectFilesystem, Paths.get("Vendor/source2")))
        .build();

    TargetNode<ExportFileDescription.Arg> source2Ref = ExportFileBuilder
        .newExportFileBuilder(source2RefTarget)
        .setSrc(new BuildTargetSourcePath(source2Target))
        .build();

    TargetNode<ExportFileDescription.Arg> source3 = ExportFileBuilder
        .newExportFileBuilder(source3Target)
        .build();

    TargetNode<ExportFileDescription.Arg> header = ExportFileBuilder
        .newExportFileBuilder(headerTarget)
        .build();

    TargetNode<AppleNativeTargetDescriptionArg> library = AppleLibraryBuilder
        .createBuilder(libTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setSrcs(
            Optional.of(
                ImmutableList.of(
                    SourceWithFlags.of(
                        new BuildTargetSourcePath(source1Target)),
                    SourceWithFlags.of(
                        new BuildTargetSourcePath(source2RefTarget)),
                    SourceWithFlags.of(
                        new BuildTargetSourcePath(source3Target)))))
        .setPrefixHeader(
            Optional.<SourcePath>of(new BuildTargetSourcePath(headerTarget)))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(
            source1,
            source2,
            source2Ref,
            source3,
            header,
            library));

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        libTarget.toString());

    assertHasSingletonSourcesPhaseWithSourcesAndFlags(
        target,
        ImmutableMap.of(
            "Vendor/sources/source1", Optional.<String>absent(),
            "Vendor/source2", Optional.<String>absent(),
            "Vendor/source3", Optional.<String>absent()));

    ImmutableMap<String, String> settings = getBuildSettings(libTarget, target, "Debug");
    assertEquals("../Vendor/header", settings.get("GCC_PREFIX_HEADER"));
  }

  @Test
  public void applicationTestUsesHostAppAsTestHostAndBundleLoader() throws IOException {
    BuildTarget hostAppBinaryTarget = BuildTarget.builder("//foo", "HostAppBinary").build();
    TargetNode<?> hostAppBinaryNode = AppleBinaryBuilder
        .createBuilder(hostAppBinaryTarget)
        .build();

    BuildTarget hostAppTarget = BuildTarget.builder("//foo", "HostApp").build();
    TargetNode<?> hostAppNode = AppleBundleBuilder
        .createBuilder(hostAppTarget)
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.APP))
        .setBinary(hostAppBinaryTarget)
        .build();

    BuildTarget testTarget = BuildTarget.builder("//foo", "AppTest").build();
    TargetNode<?> testNode = AppleTestBuilder.createBuilder(testTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setExtension(Either.<AppleBundleExtension, String>ofLeft(AppleBundleExtension.XCTEST))
        .setTestHostApp(Optional.of(hostAppTarget))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.of(hostAppBinaryNode, hostAppNode, testNode),
        ImmutableSet.<ProjectGenerator.Option>of());

    projectGenerator.createXcodeProjects();

    PBXTarget testPBXTarget = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:AppTest");

    ImmutableMap<String, String> settings = getBuildSettings(testTarget, testPBXTarget, "Debug");
    assertEquals("$BUILT_PRODUCTS_DIR/./HostApp.app/HostApp", settings.get("BUNDLE_LOADER"));
    assertEquals("$(BUNDLE_LOADER)", settings.get("TEST_HOST"));
  }

  @Test
  public void aggregateTargetForBuildWithBuck() throws IOException {
    BuildTarget binaryTarget = BuildTarget.builder("//foo", "binary").build();
    TargetNode<?> binaryNode = AppleBinaryBuilder
        .createBuilder(binaryTarget)
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setSrcs(
            Optional.of(
                ImmutableList.of(
                    SourceWithFlags.of(
                        new TestSourcePath("foo.m"), ImmutableList.of("-foo")))))
        .build();

    ImmutableSet<TargetNode<?>> nodes = ImmutableSet.<TargetNode<?>>of(binaryNode);
    ProjectGenerator projectGenerator = new ProjectGenerator(
        TargetGraphFactory.newInstance(nodes),
        FluentIterable.from(nodes).transform(HasBuildTarget.TO_TARGET).toSet(),
        projectFilesystem,
        /* reactNativeServer */ Optional.<Path>absent(),
        OUTPUT_DIRECTORY,
        PROJECT_NAME,
        "BUCK",
        ImmutableSet.<ProjectGenerator.Option>of(),
        Optional.of(binaryTarget),
        ImmutableList.of("--flag", "value with spaces"),
        Functions.<Path>constant(null));
    projectGenerator.createXcodeProjects();

    PBXTarget buildWithBuckTarget = null;
    for (PBXTarget target : projectGenerator.getGeneratedProject().getTargets()) {
      if (target.getProductName() != null &&
          target.getProductName().endsWith("-Buck")) {
        buildWithBuckTarget = target;
      }
    }
    assertThat(buildWithBuckTarget, is(notNullValue()));

    assertHasConfigurations(buildWithBuckTarget, "Debug");
    assertEquals(
        "Should have exact number of build phases",
        1,
        buildWithBuckTarget.getBuildPhases().size());
    PBXBuildPhase buildPhase = Iterables.getOnlyElement(buildWithBuckTarget.getBuildPhases());
    assertThat(buildPhase, instanceOf(PBXShellScriptBuildPhase.class));
    PBXShellScriptBuildPhase shellScriptBuildPhase = (PBXShellScriptBuildPhase) buildPhase;
    assertThat(
        shellScriptBuildPhase.getShellScript(),
        equalTo("buck build --flag 'value with spaces' " + binaryTarget.getFullyQualifiedName()));
  }

  @Test
  public void cxxFlagsPropagatedToConfig() throws IOException {
    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setLangPreprocessorFlags(
            Optional.of(
                ImmutableMap.of(
                    CxxSource.Type.CXX, ImmutableList.of("-std=c++11", "-stdlib=libc++"),
                    CxxSource.Type.OBJCXX, ImmutableList.of("-std=c++11", "-stdlib=libc++"))))
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setSrcs(
            Optional.of(
                ImmutableList.of(SourceWithFlags.of(new TestSourcePath("foo.mm")))))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();

    PBXTarget target = assertTargetExistsAndReturnTarget(
        projectGenerator.getGeneratedProject(),
        "//foo:lib");

    ImmutableMap<String, String> settings = getBuildSettings(buildTarget, target, "Debug");
    assertEquals("$(inherited) -std=c++11 -stdlib=libc++", settings.get("OTHER_CPLUSPLUSFLAGS"));
  }

  @Test
  public void unsupportedLangPreprocessorFlagsThrows() throws IOException {
    thrown.expect(HumanReadableException.class);
    thrown.expectMessage(
        "//foo:lib: Xcode project generation does not support specified lang_preprocessor_flags " +
        "keys: [ASSEMBLER]");

    BuildTarget buildTarget = BuildTarget.builder("//foo", "lib").build();
    TargetNode<?> node = AppleLibraryBuilder
        .createBuilder(buildTarget)
        .setLangPreprocessorFlags(
            Optional.of(
                ImmutableMap.of(
                    CxxSource.Type.ASSEMBLER, ImmutableList.of("-Xawesome"))))
        .setConfigs(
            Optional.of(
                ImmutableSortedMap.of(
                    "Debug",
                    ImmutableMap.<String, String>of())))
        .setSrcs(
            Optional.of(
                ImmutableList.of(SourceWithFlags.of(new TestSourcePath("foo.mm")))))
        .build();

    ProjectGenerator projectGenerator = createProjectGeneratorForCombinedProject(
        ImmutableSet.<TargetNode<?>>of(node));

    projectGenerator.createXcodeProjects();
  }

  private ProjectGenerator createProjectGeneratorForCombinedProject(
      Iterable<TargetNode<?>> nodes) {
    return createProjectGeneratorForCombinedProject(
        nodes,
        ImmutableSet.<ProjectGenerator.Option>of());
  }

  private ProjectGenerator createProjectGeneratorForCombinedProject(
      Iterable<TargetNode<?>> nodes,
      ImmutableSet<ProjectGenerator.Option> projectGeneratorOptions) {
    return createProjectGeneratorForCombinedProject(
        nodes,
        projectGeneratorOptions,
        Optional.<Path>absent());
  }

  private ProjectGenerator createProjectGeneratorForCombinedProject(
      Iterable<TargetNode<?>> nodes,
      ImmutableSet<ProjectGenerator.Option> projectGeneratorOptions,
      Optional<Path> reactNativeServer) {
    ImmutableSet<BuildTarget> initialBuildTargets = FluentIterable
        .from(nodes)
        .transform(HasBuildTarget.TO_TARGET)
        .toSet();

    return new ProjectGenerator(
        TargetGraphFactory.newInstance(ImmutableSet.copyOf(nodes)),
        initialBuildTargets,
        projectFilesystem,
        reactNativeServer,
        OUTPUT_DIRECTORY,
        PROJECT_NAME,
        "BUCK",
        projectGeneratorOptions,
        Optional.<BuildTarget>absent(),
        ImmutableList.<String>of(),
        Functions.<Path>constant(null));
  }

  private ImmutableSet<TargetNode<?>> setupSimpleLibraryWithResources(
      ImmutableSet<SourcePath> resourceFiles,
      ImmutableSet<SourcePath> resourceDirectories) {
    BuildTarget resourceTarget = BuildTarget.builder("//foo", "res").build();
    TargetNode<?> resourceNode = AppleResourceBuilder
        .createBuilder(resourceTarget)
        .setFiles(resourceFiles)
        .setDirs(resourceDirectories)
        .build();

    BuildTarget libraryTarget = BuildTarget.builder("//foo", "foo").build();
    TargetNode<?> libraryNode = AppleLibraryBuilder
        .createBuilder(libraryTarget)
        .setDeps(Optional.of(ImmutableSortedSet.of(resourceTarget)))
        .build();

    return ImmutableSet.of(resourceNode, libraryNode);
  }

  private String assertFileRefIsRelativeAndResolvePath(PBXReference fileRef) {
    assert(!fileRef.getPath().startsWith("/"));
    assertEquals(
        "file path should be relative to project directory",
        PBXReference.SourceTree.SOURCE_ROOT,
        fileRef.getSourceTree());
    return projectFilesystem.resolve(OUTPUT_DIRECTORY).resolve(fileRef.getPath())
        .normalize().toString();
  }

  private void assertHasConfigurations(PBXTarget target, String... names) {
    Map<String, XCBuildConfiguration> buildConfigurationMap =
        target.getBuildConfigurationList().getBuildConfigurationsByName().asMap();
    assertEquals(
        "Configuration list has expected number of entries",
        names.length, buildConfigurationMap.size());

    for (String name : names) {
      XCBuildConfiguration configuration = buildConfigurationMap.get(name);

      assertNotNull("Configuration entry exists", configuration);
      assertEquals("Configuration name is same as key", name, configuration.getName());
      assertTrue(
          "Configuration has xcconfig file",
          configuration.getBaseConfigurationReference().getPath().endsWith(".xcconfig"));
    }
  }

  private void assertHasSingletonSourcesPhaseWithSourcesAndFlags(
      PBXTarget target,
      ImmutableMap<String, Optional<String>> sourcesAndFlags) {

    PBXSourcesBuildPhase sourcesBuildPhase =
        getSingletonPhaseByType(target, PBXSourcesBuildPhase.class);

    assertEquals(
        "Sources build phase should have correct number of sources",
        sourcesAndFlags.size(), sourcesBuildPhase.getFiles().size());

    // map keys to absolute paths
    ImmutableMap.Builder<String, Optional<String>> absolutePathFlagMapBuilder =
        ImmutableMap.builder();
    for (Map.Entry<String, Optional<String>> name : sourcesAndFlags.entrySet()) {
      absolutePathFlagMapBuilder.put(
          projectFilesystem.getRootPath().resolve(name.getKey()).toAbsolutePath()
              .normalize().toString(),
          name.getValue());
    }
    ImmutableMap<String, Optional<String>> absolutePathFlagMap = absolutePathFlagMapBuilder.build();

    for (PBXBuildFile file : sourcesBuildPhase.getFiles()) {
      String filePath = assertFileRefIsRelativeAndResolvePath(file.getFileRef());
      Optional<String> flags = absolutePathFlagMap.get(filePath);
      assertNotNull(String.format("Unexpected file ref '%s' found", filePath), flags);
      if (flags.isPresent()) {
        assertTrue("Build file should have settings dictionary", file.getSettings().isPresent());

        NSDictionary buildFileSettings = file.getSettings().get();
        NSString compilerFlags = (NSString) buildFileSettings.get("COMPILER_FLAGS");

        assertNotNull("Build file settings should have COMPILER_FLAGS entry", compilerFlags);
        assertEquals(
            "Build file settings should be expected value",
            flags.get(), compilerFlags.getContent());
      } else {
        assertFalse(
            "Build file should not have settings dictionary", file.getSettings().isPresent());
      }
    }
  }

  private void assertHasSingletonResourcesPhaseWithEntries(PBXTarget target, String... resources) {
    PBXResourcesBuildPhase buildPhase =
        getSingletonPhaseByType(target, PBXResourcesBuildPhase.class);
    assertEquals("Resources phase should have right number of elements",
        resources.length, buildPhase.getFiles().size());

    ImmutableSet.Builder<String> expectedResourceSetBuilder = ImmutableSet.builder();
    for (String resource : resources) {
      expectedResourceSetBuilder.add(
          projectFilesystem.getRootPath().resolve(resource).toAbsolutePath()
              .normalize().toString());
    }
    ImmutableSet<String> expectedResourceSet = expectedResourceSetBuilder.build();

    for (PBXBuildFile file : buildPhase.getFiles()) {
      String source = assertFileRefIsRelativeAndResolvePath(file.getFileRef());
      assertTrue(
          "Resource should be in list of expected resources: " + source,
          expectedResourceSet.contains(source));
    }
  }

  private ImmutableMap<String, String> getBuildSettings(
      BuildTarget buildTarget, PBXTarget target, String config) {
    assertHasConfigurations(target, config);
    return ProjectGeneratorTestUtils.getBuildSettings(
        projectFilesystem, buildTarget, target, config);
  }

  private boolean hasShellScriptPhaseToCompileAssetCatalogs(PBXTarget target) {
    boolean found = false;
    for (PBXBuildPhase phase : target.getBuildPhases()) {
      if (phase.getClass().equals(PBXShellScriptBuildPhase.class)) {
        PBXShellScriptBuildPhase shellScriptBuildPhase = (PBXShellScriptBuildPhase) phase;
        if (shellScriptBuildPhase.getShellScript().contains("compile_asset_catalogs")) {
          found = true;
        }
      }
    }

    return found;
  }

  private Matcher<PBXTarget> targetWithName(String name) {
    return new FeatureMatcher<PBXTarget, String>(
        org.hamcrest.Matchers.equalTo(name),
        "target with name",
        "name") {
      @Override
      protected String featureValueOf(PBXTarget pbxTarget) {
        return pbxTarget.getName();
      }
    };
  }
}
