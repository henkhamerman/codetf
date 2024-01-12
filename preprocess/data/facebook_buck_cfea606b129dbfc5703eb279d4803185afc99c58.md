Refactoring Types: ['Extract Method']
pleBundle.java
/*
 * Copyright 2014-present Facebook, Inc.
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

import com.facebook.buck.cxx.CxxPlatform;
import com.facebook.buck.cxx.CxxPreprocessorInput;
import com.facebook.buck.cxx.HeaderVisibility;
import com.facebook.buck.cxx.NativeTestable;
import com.facebook.buck.cxx.Tool;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargets;
import com.facebook.buck.rules.AbstractBuildRule;
import com.facebook.buck.rules.AddToRuleKey;
import com.facebook.buck.rules.BuildContext;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildableContext;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.coercer.Either;
import com.facebook.buck.step.Step;
import com.facebook.buck.step.fs.CopyStep;
import com.facebook.buck.step.fs.FindAndReplaceStep;
import com.facebook.buck.step.fs.MakeCleanDirectoryStep;
import com.facebook.buck.step.fs.MkdirStep;
import com.facebook.buck.step.fs.WriteFileStep;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.io.Files;

import com.dd.plist.NSObject;
import com.dd.plist.NSNumber;
import com.dd.plist.NSString;

import java.nio.file.Path;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import javax.annotation.Nullable;

/**
 * Creates a bundle: a directory containing files and subdirectories, described by an Info.plist.
 */
public class AppleBundle extends AbstractBuildRule implements NativeTestable {
  private static final Logger LOG = Logger.get(AppleBundle.class);

  @AddToRuleKey
  private final String extension;

  @AddToRuleKey
  private final Optional<SourcePath> infoPlist;

  @AddToRuleKey
  private final ImmutableMap<String, String> infoPlistSubstitutions;

  @AddToRuleKey
  private final Optional<BuildRule> binary;

  @AddToRuleKey
  private final AppleBundleDestinations destinations;

  @AddToRuleKey
  private final Set<SourcePath> resourceDirs;

  @AddToRuleKey
  private final Set<SourcePath> resourceFiles;

  @AddToRuleKey
  private final Tool ibtool;

  @AddToRuleKey
  private final Tool dsymutil;

  @AddToRuleKey
  private final ImmutableSortedSet<BuildTarget> tests;

  @AddToRuleKey
  private final String platformName;

  @AddToRuleKey
  private final String sdkName;

  private final ImmutableSet<AppleAssetCatalog> bundledAssetCatalogs;

  private final Optional<AppleAssetCatalog> mergedAssetCatalog;

  private final String binaryName;
  private final Path bundleRoot;
  private final Path binaryPath;

  AppleBundle(
      BuildRuleParams params,
      SourcePathResolver resolver,
      Either<AppleBundleExtension, String> extension,
      Optional<SourcePath> infoPlist,
      Map<String, String> infoPlistSubstitutions,
      Optional<BuildRule> binary,
      AppleBundleDestinations destinations,
      Set<SourcePath> resourceDirs,
      Set<SourcePath> resourceFiles,
      Tool ibtool,
      Tool dsymutil,
      Set<AppleAssetCatalog> bundledAssetCatalogs,
      Optional<AppleAssetCatalog> mergedAssetCatalog,
      Set<BuildTarget> tests,
      String platformName,
      String sdkName) {
    super(params, resolver);
    this.extension = extension.isLeft() ?
        extension.getLeft().toFileExtension() :
        extension.getRight();
    this.infoPlist = infoPlist;
    this.infoPlistSubstitutions = ImmutableMap.copyOf(infoPlistSubstitutions);
    this.binary = binary;
    this.destinations = destinations;
    this.resourceDirs = resourceDirs;
    this.resourceFiles = resourceFiles;
    this.ibtool = ibtool;
    this.dsymutil = dsymutil;
    this.bundledAssetCatalogs = ImmutableSet.copyOf(bundledAssetCatalogs);
    this.mergedAssetCatalog = mergedAssetCatalog;
    this.binaryName = getBinaryName(getBuildTarget());
    this.bundleRoot = getBundleRoot(getBuildTarget(), this.extension);
    this.binaryPath = this.destinations.getExecutablesPath()
        .resolve(this.binaryName);
    this.tests = ImmutableSortedSet.copyOf(tests);
    this.platformName = platformName;
    this.sdkName = sdkName;
  }

  private static String getBinaryName(BuildTarget buildTarget) {
    return buildTarget.getShortName();
  }

  public static Path getBundleRoot(BuildTarget buildTarget, String extension) {
    return BuildTargets
        .getGenPath(buildTarget, "%s")
        .resolve(getBinaryName(buildTarget) + "." + extension);
  }

  @Override
  @Nullable
  public Path getPathToOutput() {
    return bundleRoot;
  }

  public Path getInfoPlistPath() {
    return getMetadataPath().resolve("Info.plist");
  }

  public Path getUnzippedOutputFilePathToBinary() {
    return this.binaryPath;
  }

  private Path getMetadataPath() {
    return bundleRoot.resolve(destinations.getMetadataPath());
  }

  @Override
  public ImmutableList<Step> getBuildSteps(
      BuildContext context,
      BuildableContext buildableContext) {
    ImmutableList.Builder<Step> stepsBuilder = ImmutableList.builder();

    Path metadataPath = getMetadataPath();

    Path infoPlistInputPath = getResolver().getPath(infoPlist.get());
    Path infoPlistSubstitutionTempPath =
        BuildTargets.getScratchPath(getBuildTarget(), "%s.plist");
    Path infoPlistOutputPath = metadataPath.resolve("Info.plist");

    stepsBuilder.add(
        new MakeCleanDirectoryStep(bundleRoot),
        new MkdirStep(metadataPath),
        // TODO(user): This is only appropriate for .app bundles.
        new WriteFileStep("APPLWRUN", metadataPath.resolve("PkgInfo")),
        new FindAndReplaceStep(
            infoPlistInputPath,
            infoPlistSubstitutionTempPath,
            InfoPlistSubstitution.createVariableExpansionFunction(
                withDefaults(
                    infoPlistSubstitutions,
                    ImmutableMap.of(
                        "EXECUTABLE_NAME", binaryName,
                        "PRODUCT_NAME", binaryName
                    ))
            )),
        new PlistProcessStep(
            infoPlistSubstitutionTempPath,
            infoPlistOutputPath,
            getInfoPlistAdditionalKeys(platformName, sdkName),
            getInfoPlistOverrideKeys(platformName)));

    if (binary.isPresent()) {
      stepsBuilder.add(
          new MkdirStep(bundleRoot.resolve(this.destinations.getExecutablesPath())));
      Path bundleBinaryPath = bundleRoot.resolve(binaryPath);
      stepsBuilder.add(
          CopyStep.forFile(
              binary.get().getPathToOutput(),
              bundleBinaryPath));
      stepsBuilder.add(
          new DsymStep(
              dsymutil.getCommandPrefix(getResolver()),
              bundleBinaryPath,
              bundleBinaryPath.resolveSibling(
                  bundleBinaryPath.getFileName().toString() + ".dSYM")));
    }

    for (SourcePath dir : resourceDirs) {
      Path bundleDestinationPath = bundleRoot.resolve(this.destinations.getResourcesPath());
      stepsBuilder.add(new MkdirStep(bundleDestinationPath));
      stepsBuilder.add(
          CopyStep.forDirectory(
              getResolver().getPath(dir),
              bundleDestinationPath,
              CopyStep.DirectoryMode.DIRECTORY_AND_CONTENTS));
    }
    for (SourcePath file : resourceFiles) {
      Path bundleDestinationPath = bundleRoot.resolve(this.destinations.getResourcesPath());
      stepsBuilder.add(new MkdirStep(bundleDestinationPath));
      Path resolvedFilePath = getResolver().getPath(file);
      Path destinationPath = bundleDestinationPath.resolve(resolvedFilePath.getFileName());
      addResourceProcessingSteps(resolvedFilePath, destinationPath, stepsBuilder);
    }

    for (AppleAssetCatalog bundledAssetCatalog : bundledAssetCatalogs) {
      Path bundleDir = bundledAssetCatalog.getOutputDir();
      stepsBuilder.add(
          CopyStep.forDirectory(
              bundleDir,
              bundleRoot,
              CopyStep.DirectoryMode.DIRECTORY_AND_CONTENTS));
    }

    if (mergedAssetCatalog.isPresent()) {
      Path bundleDir = mergedAssetCatalog.get().getOutputDir();
      stepsBuilder.add(
          CopyStep.forDirectory(
              bundleDir,
              bundleRoot,
              CopyStep.DirectoryMode.CONTENTS_ONLY));
    }

    // Ensure the bundle directory is archived so we can fetch it later.
    buildableContext.recordArtifact(bundleRoot);

    return stepsBuilder.build();
  }

  static ImmutableMap<String, String> withDefaults(
      ImmutableMap<String, String> map,
      ImmutableMap<String, String> defaults) {
    ImmutableMap.Builder<String, String> builder = ImmutableMap.<String, String>builder()
        .putAll(map);
    for (ImmutableMap.Entry<String, String> entry : defaults.entrySet()) {
      if (!map.containsKey(entry.getKey())) {
        builder = builder.put(entry.getKey(), entry.getValue());
      }
    }
    return builder.build();
  }

  static ImmutableMap<String, NSObject> getInfoPlistOverrideKeys(
      String platformName) {
    ImmutableMap.Builder<String, NSObject> keys = ImmutableMap.builder();

    if (platformName.contains("osx")) {
      keys.put("LSRequiresIPhoneOS", new NSNumber(false));
    } else {
      keys.put("LSRequiresIPhoneOS", new NSNumber(true));
    }

    return keys.build();
  }

  static ImmutableMap<String, NSObject> getInfoPlistAdditionalKeys(
      String platformName,
      String sdkName) {
    ImmutableMap.Builder<String, NSObject> keys = ImmutableMap.builder();

    if (platformName.contains("osx")) {
      keys.put("NSHighResolutionCapable", new NSNumber(true));
      keys.put("NSSupportsAutomaticGraphicsSwitching", new NSNumber(true));
    }

    keys.put("DTPlatformName", new NSString(platformName));
    keys.put("DTSDKName", new NSString(sdkName));

    return keys.build();
  }

  private void addResourceProcessingSteps(
      Path sourcePath,
      Path destinationPath,
      ImmutableList.Builder<Step> stepsBuilder) {
    String sourcePathExtension = Files.getFileExtension(sourcePath.toString())
        .toLowerCase(Locale.US);
    switch (sourcePathExtension) {
      case "xib":
        String compiledNibFilename = Files.getNameWithoutExtension(destinationPath.toString()) +
            ".nib";
        Path compiledNibPath = destinationPath.getParent().resolve(compiledNibFilename);
        LOG.debug("Compiling XIB %s to NIB %s", sourcePath, destinationPath);
        stepsBuilder.add(
            new IbtoolStep(
                ibtool.getCommandPrefix(getResolver()),
                sourcePath,
                compiledNibPath));
        break;
      default:
        stepsBuilder.add(CopyStep.forFile(sourcePath, destinationPath));
        break;
    }
  }

  @Override
  public boolean isTestedBy(BuildTarget testRule) {
    if (tests.contains(testRule)) {
      return true;
    }

    if (binary.isPresent()) {
      BuildRule binaryRule = binary.get();
      if (binaryRule instanceof NativeTestable) {
        return ((NativeTestable) binaryRule).isTestedBy(testRule);
      }
    }

    return false;
  }

  @Override
  public CxxPreprocessorInput getCxxPreprocessorInput(
      CxxPlatform cxxPlatform,
      HeaderVisibility headerVisibility) {
    if (binary.isPresent()) {
      BuildRule binaryRule = binary.get();
      if (binaryRule instanceof NativeTestable) {
        return ((NativeTestable) binaryRule).getCxxPreprocessorInput(cxxPlatform, headerVisibility);
      }
    }
    return CxxPreprocessorInput.EMPTY;
  }
}


File: src/com/facebook/buck/apple/AppleBundleDescription.java
/*
 * Copyright 2014-present Facebook, Inc.
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

import com.facebook.buck.cxx.CxxDescriptionEnhancer;
import com.facebook.buck.cxx.CxxPlatform;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.FlavorDomain;
import com.facebook.buck.model.FlavorDomainException;
import com.facebook.buck.model.Flavored;
import com.facebook.buck.model.HasTests;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRuleType;
import com.facebook.buck.rules.BuildRules;
import com.facebook.buck.rules.Description;
import com.facebook.buck.rules.Hint;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SourcePaths;
import com.facebook.buck.rules.TargetNode;
import com.facebook.buck.rules.coercer.Either;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.infer.annotation.SuppressFieldNotInitialized;
import com.google.common.base.Optional;
import com.google.common.base.Predicate;
import com.google.common.base.Predicates;
import com.google.common.base.Suppliers;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Ordering;

import java.util.Map;
import java.util.Set;

public class AppleBundleDescription implements Description<AppleBundleDescription.Arg>, Flavored {
  public static final BuildRuleType TYPE = BuildRuleType.of("apple_bundle");

  private final AppleBinaryDescription appleBinaryDescription;
  private final AppleLibraryDescription appleLibraryDescription;
  private final FlavorDomain<CxxPlatform> cxxPlatformFlavorDomain;
  private final ImmutableMap<Flavor, AppleCxxPlatform> platformFlavorsToAppleCxxPlatforms;
  private final CxxPlatform defaultCxxPlatform;

  public AppleBundleDescription(
      AppleBinaryDescription appleBinaryDescription,
      AppleLibraryDescription appleLibraryDescription,
      FlavorDomain<CxxPlatform> cxxPlatformFlavorDomain,
      Map<Flavor, AppleCxxPlatform> platformFlavorsToAppleCxxPlatforms,
      CxxPlatform defaultCxxPlatform) {
    this.appleBinaryDescription = appleBinaryDescription;
    this.appleLibraryDescription = appleLibraryDescription;
    this.cxxPlatformFlavorDomain = cxxPlatformFlavorDomain;
    this.platformFlavorsToAppleCxxPlatforms =
        ImmutableMap.copyOf(platformFlavorsToAppleCxxPlatforms);
    this.defaultCxxPlatform = defaultCxxPlatform;
  }

  @Override
  public BuildRuleType getBuildRuleType() {
    return TYPE;
  }

  @Override
  public Arg createUnpopulatedConstructorArg() {
    return new Arg();
  }

  @Override
  public boolean hasFlavors(ImmutableSet<Flavor> flavors) {
    return appleLibraryDescription.hasFlavors(flavors) ||
        appleBinaryDescription.hasFlavors(flavors);
  }

  @Override
  public <A extends Arg> AppleBundle createBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      A args) {

    CxxPlatform cxxPlatform;
    try {
      cxxPlatform = cxxPlatformFlavorDomain
          .getValue(params.getBuildTarget().getFlavors())
          .or(defaultCxxPlatform);
    } catch (FlavorDomainException e) {
      throw new HumanReadableException(e, "%s: %s", params.getBuildTarget(), e.getMessage());
    }
    AppleCxxPlatform appleCxxPlatform =
        platformFlavorsToAppleCxxPlatforms.get(cxxPlatform.getFlavor());
    if (appleCxxPlatform == null) {
      throw new HumanReadableException(
          "%s: Apple bundle requires an Apple platform, found '%s'",
          params.getBuildTarget(),
          cxxPlatform.getFlavor().getName());
    }

    AppleBundleDestinations destinations =
        AppleBundleDestinations.platformDestinations(
            appleCxxPlatform.getAppleSdk().getApplePlatform());

    ImmutableSet.Builder<SourcePath> bundleDirsBuilder = ImmutableSet.builder();
    ImmutableSet.Builder<SourcePath> bundleFilesBuilder = ImmutableSet.builder();
    ImmutableSet<AppleResourceDescription.Arg> resourceDescriptions =
        AppleResources.collectRecursiveResources(
            params.getTargetGraph(),
            ImmutableSet.of(params.getTargetGraph().get(params.getBuildTarget())));
    AppleResources.addResourceDirsToBuilder(bundleDirsBuilder, resourceDescriptions);
    AppleResources.addResourceFilesToBuilder(bundleFilesBuilder, resourceDescriptions);
    ImmutableSet<SourcePath> bundleDirs = bundleDirsBuilder.build();
    ImmutableSet<SourcePath> bundleFiles = bundleFilesBuilder.build();

    SourcePathResolver sourcePathResolver = new SourcePathResolver(resolver);

    CollectedAssetCatalogs collectedAssetCatalogs =
        AppleDescriptions.createBuildRulesForTransitiveAssetCatalogDependencies(
            params,
            sourcePathResolver,
            appleCxxPlatform.getAppleSdk().getApplePlatform(),
            appleCxxPlatform.getActool());

    Optional<AppleAssetCatalog> mergedAssetCatalog = collectedAssetCatalogs.getMergedAssetCatalog();
    ImmutableSet<AppleAssetCatalog> bundledAssetCatalogs =
        collectedAssetCatalogs.getBundledAssetCatalogs();

    // TODO(user): Sort through the changes needed to make project generation work with
    // binary being optional.
    BuildRule flavoredBinaryRule = getFlavoredBinaryRule(params, resolver, args);
    BuildRuleParams bundleParamsWithFlavoredBinaryDep = getBundleParamsWithUpdatedDeps(
        params,
        args.binary,
        ImmutableSet.<BuildRule>builder()
            .add(flavoredBinaryRule)
            .addAll(mergedAssetCatalog.asSet())
            .addAll(bundledAssetCatalogs)
            .addAll(
                BuildRules.toBuildRulesFor(
                    params.getBuildTarget(),
                    resolver,
                    SourcePaths.filterBuildTargetSourcePaths(
                        Iterables.concat(bundleFiles, bundleDirs))))
            .build());

    return new AppleBundle(
        bundleParamsWithFlavoredBinaryDep,
        sourcePathResolver,
        args.extension,
        args.infoPlist,
        args.infoPlistSubstitutions.get(),
        Optional.of(flavoredBinaryRule),
        destinations,
        bundleDirs,
        bundleFiles,
        appleCxxPlatform.getIbtool(),
        appleCxxPlatform.getDsymutil(),
        bundledAssetCatalogs,
        mergedAssetCatalog,
        args.getTests(),
        appleCxxPlatform.getAppleSdk().getApplePlatform().getName(),
        appleCxxPlatform.getAppleSdk().getName());
  }

  private static <A extends Arg> BuildRule getFlavoredBinaryRule(
      final BuildRuleParams params,
      final BuildRuleResolver resolver,
      final A args) {
    final TargetNode<?> binaryTargetNode = params.getTargetGraph().get(args.binary);
    BuildRuleParams binaryRuleParams = new BuildRuleParams(
        args.binary,
        Suppliers.ofInstance(
            BuildRules.toBuildRulesFor(
                params.getBuildTarget(),
                resolver,
                binaryTargetNode.getDeclaredDeps())),
        Suppliers.ofInstance(
            BuildRules.toBuildRulesFor(
                params.getBuildTarget(),
                resolver,
                binaryTargetNode.getExtraDeps())),
        params.getProjectFilesystem(),
        params.getRuleKeyBuilderFactory(),
        params.getTargetGraph());
    return CxxDescriptionEnhancer.requireBuildRule(
        binaryRuleParams,
        resolver,
        params.getBuildTarget().getFlavors().toArray(new Flavor[0]));
  }

  private static BuildRuleParams getBundleParamsWithUpdatedDeps(
      final BuildRuleParams params,
      final BuildTarget originalBinaryTarget,
      final Set<BuildRule> newDeps) {
    // Remove the unflavored binary rule and add the flavored one instead.
    final Predicate<BuildRule> notOriginalBinaryRule = Predicates.not(
        BuildRules.isBuildRuleWithTarget(originalBinaryTarget));
    return params.copyWithDeps(
        Suppliers.ofInstance(
            FluentIterable
                .from(params.getDeclaredDeps())
                .filter(notOriginalBinaryRule)
                .append(newDeps)
                .toSortedSet(Ordering.natural())),
        Suppliers.ofInstance(
            FluentIterable
                .from(params.getExtraDeps())
                .filter(notOriginalBinaryRule)
                .toSortedSet(Ordering.natural())));
  }

  @SuppressFieldNotInitialized
  public static class Arg implements HasAppleBundleFields, HasTests {
    public Either<AppleBundleExtension, String> extension;
    public BuildTarget binary;
    public Optional<SourcePath> infoPlist;
    public Optional<ImmutableMap<String, String>> infoPlistSubstitutions;
    public Optional<ImmutableMap<String, SourcePath>> headers;
    public Optional<ImmutableSortedSet<BuildTarget>> deps;
    @Hint(isDep = false) public Optional<ImmutableSortedSet<BuildTarget>> tests;
    public Optional<String> xcodeProductType;

    @Override
    public Either<AppleBundleExtension, String> getExtension() {
      return extension;
    }

    @Override
    public Optional<SourcePath> getInfoPlist() {
      return infoPlist;
    }

    @Override
    public ImmutableSortedSet<BuildTarget> getTests() {
      return tests.get();
    }

    @Override
    public Optional<String> getXcodeProductType() {
      return xcodeProductType;
    }
  }
}


File: src/com/facebook/buck/apple/AppleResources.java
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

package com.facebook.buck.apple;

import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TargetNode;
import com.google.common.base.Function;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableSet;

import java.util.Set;

public class AppleResources {
  // Utility class, do not instantiate.
  private AppleResources() { }

  /**
   * Collect resources from recursive dependencies.
   *
   * @param targetGraph The {@link TargetGraph} containing the node and its dependencies.
   * @param targetNodes {@link TargetNode} at the tip of the traversal.
   * @return The recursive resource buildables.
   */
  public static <T> ImmutableSet<AppleResourceDescription.Arg> collectRecursiveResources(
      final TargetGraph targetGraph,
      Iterable<TargetNode<T>> targetNodes) {
    return FluentIterable
        .from(targetNodes)
        .transformAndConcat(
            AppleBuildRules.newRecursiveRuleDependencyTransformer(
                targetGraph,
                AppleBuildRules.RecursiveDependenciesMode.COPYING,
                ImmutableSet.of(AppleResourceDescription.TYPE)))
        .transform(
            new Function<TargetNode<?>, AppleResourceDescription.Arg>() {
              @Override
              public AppleResourceDescription.Arg apply(TargetNode<?> input) {
                return (AppleResourceDescription.Arg) input.getConstructorArg();
              }
            })
        .toSet();
  }

  public static void addResourceDirsToBuilder(
      ImmutableSet.Builder<SourcePath> resourceDirsBuilder,
      Iterable<AppleResourceDescription.Arg> resourceDescriptions) {
    resourceDirsBuilder.addAll(
        FluentIterable
            .from(resourceDescriptions)
            .transformAndConcat(
                new Function<AppleResourceDescription.Arg, Set<SourcePath>>() {
                  @Override
                  public Set<SourcePath> apply(AppleResourceDescription.Arg arg) {
                    return arg.dirs;
                  }
                })
    );
  }

  public static void addResourceFilesToBuilder(
      ImmutableSet.Builder<SourcePath> resourceFilesBuilder,
      Iterable<AppleResourceDescription.Arg> resourceDescriptions) {
    resourceFilesBuilder.addAll(
        FluentIterable
            .from(resourceDescriptions)
            .transformAndConcat(
                new Function<AppleResourceDescription.Arg, Set<SourcePath>>() {
                  @Override
                  public Set<SourcePath> apply(AppleResourceDescription.Arg arg) {
                    return arg.files;
                  }
                })
    );
  }
}


File: src/com/facebook/buck/apple/AppleTestDescription.java
/*
 * Copyright 2014-present Facebook, Inc.
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

import com.facebook.buck.cxx.CxxCompilationDatabase;
import com.facebook.buck.cxx.CxxDescriptionEnhancer;
import com.facebook.buck.cxx.CxxPlatform;
import com.facebook.buck.cxx.Linker;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.FlavorDomain;
import com.facebook.buck.model.FlavorDomainException;
import com.facebook.buck.model.Flavored;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRuleType;
import com.facebook.buck.rules.BuildRules;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.Description;
import com.facebook.buck.rules.ImplicitDepsInferringDescription;
import com.facebook.buck.rules.Label;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SourcePaths;
import com.facebook.buck.rules.TargetNode;
import com.facebook.buck.rules.coercer.Either;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.infer.annotation.SuppressFieldNotInitialized;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.base.Predicate;
import com.google.common.base.Predicates;
import com.google.common.base.Suppliers;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Sets;

import java.util.Map;
import java.util.Set;

public class AppleTestDescription implements
    Description<AppleTestDescription.Arg>,
    Flavored,
    ImplicitDepsInferringDescription<AppleTestDescription.Arg> {

  public static final BuildRuleType TYPE = BuildRuleType.of("apple_test");

  private static final Logger LOG = Logger.get(AppleTestDescription.class);

  /**
   * Flavors for the additional generated build rules.
   */
  private static final Flavor LIBRARY_FLAVOR = ImmutableFlavor.of("apple-test-library");
  private static final Flavor BUNDLE_FLAVOR = ImmutableFlavor.of("apple-test-bundle");

  private static final Set<Flavor> SUPPORTED_FLAVORS = ImmutableSet.of(
      LIBRARY_FLAVOR, BUNDLE_FLAVOR);

  private static final Predicate<Flavor> IS_SUPPORTED_FLAVOR = Predicates.in(SUPPORTED_FLAVORS);

  private static final Set<Flavor> NON_LIBRARY_FLAVORS = ImmutableSet.of(
      CxxCompilationDatabase.COMPILATION_DATABASE,
      CxxDescriptionEnhancer.HEADER_SYMLINK_TREE_FLAVOR,
      CxxDescriptionEnhancer.EXPORTED_HEADER_SYMLINK_TREE_FLAVOR);

  private final AppleConfig appleConfig;
  private final AppleBundleDescription appleBundleDescription;
  private final AppleLibraryDescription appleLibraryDescription;
  private final FlavorDomain<CxxPlatform> cxxPlatformFlavorDomain;
  private final ImmutableMap<Flavor, AppleCxxPlatform> platformFlavorsToAppleCxxPlatforms;
  private final CxxPlatform defaultCxxPlatform;

  public AppleTestDescription(
      AppleConfig appleConfig,
      AppleBundleDescription appleBundleDescription,
      AppleLibraryDescription appleLibraryDescription,
      FlavorDomain<CxxPlatform> cxxPlatformFlavorDomain,
      Map<Flavor, AppleCxxPlatform> platformFlavorsToAppleCxxPlatforms,
      CxxPlatform defaultCxxPlatform) {
    this.appleConfig = appleConfig;
    this.appleBundleDescription = appleBundleDescription;
    this.appleLibraryDescription = appleLibraryDescription;
    this.cxxPlatformFlavorDomain = cxxPlatformFlavorDomain;
    this.platformFlavorsToAppleCxxPlatforms =
        ImmutableMap.copyOf(platformFlavorsToAppleCxxPlatforms);
    this.defaultCxxPlatform = defaultCxxPlatform;
  }

  @Override
  public BuildRuleType getBuildRuleType() {
    return TYPE;
  }

  @Override
  public Arg createUnpopulatedConstructorArg() {
    return new Arg();
  }

  @Override
  public boolean hasFlavors(ImmutableSet<Flavor> flavors) {
    return FluentIterable.from(flavors).allMatch(IS_SUPPORTED_FLAVOR) ||
        appleLibraryDescription.hasFlavors(flavors);
  }

  @Override
  public <A extends Arg> BuildRule createBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      A args) {
    String extension = args.extension.isLeft() ?
        args.extension.getLeft().toFileExtension() :
        args.extension.getRight();
    if (!AppleBundleExtensions.VALID_XCTOOL_BUNDLE_EXTENSIONS.contains(extension)) {
      throw new HumanReadableException(
          "Invalid bundle extension for apple_test rule: %s (must be one of %s)",
          extension,
          AppleBundleExtensions.VALID_XCTOOL_BUNDLE_EXTENSIONS);
    }
    boolean createBundle = Sets.intersection(
        params.getBuildTarget().getFlavors(),
        NON_LIBRARY_FLAVORS).isEmpty();
    Sets.SetView<Flavor> nonLibraryFlavors = Sets.difference(
        params.getBuildTarget().getFlavors(),
        NON_LIBRARY_FLAVORS);
    boolean addDefaultPlatform = nonLibraryFlavors.isEmpty();
    ImmutableSet.Builder<Flavor> extraFlavorsBuilder = ImmutableSet.builder();
    if (createBundle) {
      extraFlavorsBuilder.add(
          LIBRARY_FLAVOR,
          CxxDescriptionEnhancer.MACH_O_BUNDLE_FLAVOR);
    }
    if (addDefaultPlatform) {
      extraFlavorsBuilder.add(defaultCxxPlatform.getFlavor());
    }

    Optional<AppleBundle> testHostApp;
    Optional<SourcePath> testHostAppBinarySourcePath;
    if (args.testHostApp.isPresent()) {
      TargetNode<?> testHostAppNode = params.getTargetGraph().get(args.testHostApp.get());
      Preconditions.checkNotNull(testHostAppNode);

      if (testHostAppNode.getType() != AppleBundleDescription.TYPE) {
        throw new HumanReadableException(
            "Apple test rule %s has unrecognized test_host_app %s type %s (should be %s)",
            params.getBuildTarget(),
            args.testHostApp.get(),
            testHostAppNode.getType(),
            AppleBundleDescription.TYPE);
      }

      AppleBundleDescription.Arg testHostAppDescription = (AppleBundleDescription.Arg)
          testHostAppNode.getConstructorArg();

      testHostApp = Optional.of(
          appleBundleDescription.createBuildRule(
              params.copyWithChanges(
                  BuildTarget.builder(args.testHostApp.get())
                      .addAllFlavors(nonLibraryFlavors)
                      .build(),
                  Suppliers.ofInstance(
                      BuildRules.toBuildRulesFor(
                          args.testHostApp.get(),
                          resolver,
                          testHostAppNode.getDeclaredDeps())),
                  Suppliers.ofInstance(
                      BuildRules.toBuildRulesFor(
                          args.testHostApp.get(),
                          resolver,
                          testHostAppNode.getExtraDeps()))),
              resolver,
              testHostAppDescription));
      testHostAppBinarySourcePath = Optional.<SourcePath>of(
          new BuildTargetSourcePath(
              params.getProjectFilesystem(),
              testHostAppDescription.binary));
    } else {
      testHostApp = Optional.absent();
      testHostAppBinarySourcePath = Optional.absent();
    }

    BuildRule library = appleLibraryDescription.createBuildRule(
        params.copyWithChanges(
            BuildTarget.builder(params.getBuildTarget())
                .addAllFlavors(extraFlavorsBuilder.build())
                .build(),
            Suppliers.ofInstance(params.getDeclaredDeps()),
            Suppliers.ofInstance(params.getExtraDeps())),
        resolver,
        args,
        // For now, instead of building all deps as dylibs and fixing up their install_names,
        // we'll just link them statically.
        Optional.of(Linker.LinkableDepType.STATIC),
        testHostAppBinarySourcePath);
    if (!createBundle) {
      return library;
    }

    CxxPlatform cxxPlatform;
    try {
      cxxPlatform = cxxPlatformFlavorDomain
          .getValue(params.getBuildTarget().getFlavors())
          .or(defaultCxxPlatform);
    } catch (FlavorDomainException e) {
      throw new HumanReadableException(e, "%s: %s", params.getBuildTarget(), e.getMessage());
    }
    AppleCxxPlatform appleCxxPlatform =
        platformFlavorsToAppleCxxPlatforms.get(cxxPlatform.getFlavor());
    if (appleCxxPlatform == null) {
      throw new HumanReadableException(
          "%s: Apple test requires an Apple platform, found '%s'",
          params.getBuildTarget(),
          cxxPlatform.getFlavor().getName());
    }

    AppleBundleDestinations destinations =
        AppleBundleDestinations.platformDestinations(
            appleCxxPlatform.getAppleSdk().getApplePlatform());

    SourcePathResolver sourcePathResolver = new SourcePathResolver(resolver);
    ImmutableSet<AppleResourceDescription.Arg> resourceDescriptions =
        AppleResources.collectRecursiveResources(
            params.getTargetGraph(),
            ImmutableSet.of(params.getTargetGraph().get(params.getBuildTarget())));
    LOG.debug("Got resource nodes %s", resourceDescriptions);
    ImmutableSet.Builder<SourcePath> resourceDirsBuilder = ImmutableSet.builder();
    AppleResources.addResourceDirsToBuilder(resourceDirsBuilder, resourceDescriptions);
    ImmutableSet<SourcePath> resourceDirs = resourceDirsBuilder.build();

    ImmutableSet.Builder<SourcePath> resourceFilesBuilder = ImmutableSet.builder();
    AppleResources.addResourceFilesToBuilder(resourceFilesBuilder, resourceDescriptions);
    ImmutableSet<SourcePath> resourceFiles = resourceFilesBuilder.build();

    CollectedAssetCatalogs collectedAssetCatalogs =
        AppleDescriptions.createBuildRulesForTransitiveAssetCatalogDependencies(
            params,
            sourcePathResolver,
            appleCxxPlatform.getAppleSdk().getApplePlatform(),
            appleCxxPlatform.getActool());

    Optional<AppleAssetCatalog> mergedAssetCatalog = collectedAssetCatalogs.getMergedAssetCatalog();
    ImmutableSet<AppleAssetCatalog> bundledAssetCatalogs =
        collectedAssetCatalogs.getBundledAssetCatalogs();

    String sdkName = appleCxxPlatform.getAppleSdk().getName();
    String platformName = appleCxxPlatform.getAppleSdk().getApplePlatform().getName();

    AppleBundle bundle = new AppleBundle(
        params.copyWithChanges(
            BuildTarget.builder(params.getBuildTarget()).addFlavors(BUNDLE_FLAVOR).build(),
            // We have to add back the original deps here, since they're likely
            // stripped from the library link above (it doesn't actually depend on them).
            Suppliers.ofInstance(
                ImmutableSortedSet.<BuildRule>naturalOrder()
                    .add(library)
                    .addAll(mergedAssetCatalog.asSet())
                    .addAll(bundledAssetCatalogs)
                    .addAll(params.getDeclaredDeps())
                    .addAll(
                        BuildRules.toBuildRulesFor(
                            params.getBuildTarget(),
                            resolver,
                            SourcePaths.filterBuildTargetSourcePaths(
                                Iterables.concat(resourceFiles, resourceDirs))))
                    .build()),
            Suppliers.ofInstance(params.getExtraDeps())),
        sourcePathResolver,
        args.extension,
        args.infoPlist,
        args.infoPlistSubstitutions.get(),
        Optional.of(library),
        destinations,
        resourceDirs,
        resourceFiles,
        appleCxxPlatform.getIbtool(),
        appleCxxPlatform.getDsymutil(),
        bundledAssetCatalogs,
        mergedAssetCatalog,
        ImmutableSortedSet.<BuildTarget>of(),
        platformName,
        sdkName);


    Optional<BuildRule> xctoolZipBuildRule;
    if (appleConfig.getXctoolZipTarget().isPresent()) {
      xctoolZipBuildRule = Optional.of(
          resolver.getRule(appleConfig.getXctoolZipTarget().get()));
    } else {
      xctoolZipBuildRule = Optional.absent();
    }

    return new AppleTest(
        appleConfig.getXctoolPath(),
        xctoolZipBuildRule,
        appleCxxPlatform.getXctest(),
        appleCxxPlatform.getOtest(),
        appleConfig.getXctestPlatformNames().contains(platformName),
        platformName,
        Optional.<String>absent(),
        params.copyWithDeps(
            Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of(bundle)),
            Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of())),
        sourcePathResolver,
        bundle,
        testHostApp,
        extension,
        args.contacts.get(),
        args.labels.get());
  }

  @Override
  public Iterable<BuildTarget> findDepsForTargetFromConstructorArgs(
      BuildTarget buildTarget,
      AppleTestDescription.Arg constructorArg) {
    // TODO(user, coneko): This should technically only be a runtime dependency;
    // doing this adds it to the extra deps in BuildRuleParams passed to
    // the bundle and test rule.
    ImmutableSet.Builder<BuildTarget> deps = ImmutableSet.builder();
    Optional<BuildTarget> xctoolZipTarget = appleConfig.getXctoolZipTarget();
    if (xctoolZipTarget.isPresent()) {
      deps.add(xctoolZipTarget.get());
    }
    return deps.build();
  }

  @SuppressFieldNotInitialized
  public static class Arg extends AppleNativeTargetDescriptionArg implements HasAppleBundleFields {
    public Optional<ImmutableSortedSet<String>> contacts;
    public Optional<ImmutableSortedSet<Label>> labels;
    public Optional<Boolean> canGroup;
    public Optional<BuildTarget> testHostApp;

    // Bundle related fields.
    public Either<AppleBundleExtension, String> extension;
    public Optional<SourcePath> infoPlist;
    public Optional<ImmutableMap<String, String>> infoPlistSubstitutions;
    public Optional<String> xcodeProductType;
    public Optional<String> resourcePrefixDir;

    @Override
    public Either<AppleBundleExtension, String> getExtension() {
      return extension;
    }

    @Override
    public Optional<SourcePath> getInfoPlist() {
      return infoPlist;
    }

    @Override
    public Optional<String> getXcodeProductType() {
      return xcodeProductType;
    }

    public boolean canGroup() {
      return canGroup.or(false);
    }
  }
}


File: src/com/facebook/buck/js/AndroidReactNativeLibrary.java
/*
 * Copyright 2015-present Facebook, Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may
 *  not use this file except in compliance with the License. You may obtain
 *  a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 *  License for the specific language governing permissions and limitations
 *  under the License.
 */

package com.facebook.buck.js;

import com.facebook.buck.android.AndroidPackageable;
import com.facebook.buck.android.AndroidPackageableCollector;
import com.facebook.buck.rules.AbstractBuildRule;
import com.facebook.buck.rules.BuildContext;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildableContext;
import com.facebook.buck.rules.PathSourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.step.Step;
import com.google.common.collect.ImmutableList;

import java.nio.file.Path;

public class AndroidReactNativeLibrary extends AbstractBuildRule implements AndroidPackageable {

  private final ReactNativeBundle bundle;

  protected AndroidReactNativeLibrary(
      BuildRuleParams buildRuleParams,
      SourcePathResolver resolver,
      ReactNativeBundle bundle) {
    super(buildRuleParams, resolver);
    this.bundle = bundle;
  }

  @Override
  public Iterable<AndroidPackageable> getRequiredPackageables() {
    return AndroidPackageableCollector.getPackageableRules(getDeps());
  }

  @Override
  public void addToCollector(AndroidPackageableCollector collector) {
    collector.addAssetsDirectory(
        getBuildTarget(),
        new PathSourcePath(getProjectFilesystem(), bundle.getPathToJSBundleDir()));
  }

  @Override
  public ImmutableList<Step> getBuildSteps(
      BuildContext context,
      BuildableContext buildableContext) {
    return ImmutableList.of();
  }

  @Override
  public Path getPathToOutput() {
    return bundle.getPathToOutput();
  }
}


File: src/com/facebook/buck/js/IosReactNativeLibraryDescription.java
/*
 * Copyright 2015-present Facebook, Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may
 *  not use this file except in compliance with the License. You may obtain
 *  a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 *  License for the specific language governing permissions and limitations
 *  under the License.
 */

package com.facebook.buck.js;

import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.Flavored;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRuleType;
import com.facebook.buck.rules.Description;
import com.google.common.collect.ImmutableSet;

public class IosReactNativeLibraryDescription
    implements Description<ReactNativeLibraryArgs>, Flavored {

  private static final BuildRuleType TYPE = BuildRuleType.of("ios_react_native_library");

  private final ReactNativeLibraryGraphEnhancer enhancer;

  public IosReactNativeLibraryDescription(ReactNativeBuckConfig buckConfig) {
    this.enhancer = new ReactNativeLibraryGraphEnhancer(buckConfig);
  }

  @Override
  public BuildRuleType getBuildRuleType() {
    return TYPE;
  }

  @Override
  public ReactNativeLibraryArgs createUnpopulatedConstructorArg() {
    return new ReactNativeLibraryArgs();
  }

  @Override
  public <A extends ReactNativeLibraryArgs> ReactNativeBundle createBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      A args) {
    return enhancer.enhanceForIos(params, resolver, args);
  }

  @Override
  public boolean hasFlavors(ImmutableSet<Flavor> flavors) {
    return ReactNativeFlavors.validateFlavors(flavors);
  }
}


File: src/com/facebook/buck/js/ReactNativeBundle.java
/*
 * Copyright 2015-present Facebook, Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may
 *  not use this file except in compliance with the License. You may obtain
 *  a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 *  License for the specific language governing permissions and limitations
 *  under the License.
 */

package com.facebook.buck.js;

import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargets;
import com.facebook.buck.rules.AbiRule;
import com.facebook.buck.rules.AbstractBuildRule;
import com.facebook.buck.rules.AddToRuleKey;
import com.facebook.buck.rules.BuildContext;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildableContext;
import com.facebook.buck.rules.Sha1HashCode;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.shell.ShellStep;
import com.facebook.buck.step.ExecutionContext;
import com.facebook.buck.step.Step;
import com.facebook.buck.step.fs.MakeCleanDirectoryStep;
import com.google.common.collect.ImmutableList;

import java.nio.file.Path;

/**
 * Responsible for running the React Native JS packager in order to generate a single {@code .js}
 * bundle along with resources referenced by the javascript code.
 */
public class ReactNativeBundle extends AbstractBuildRule implements AbiRule {

  @AddToRuleKey
  private final SourcePath entryPath;

  @AddToRuleKey
  private final boolean isDevMode;

  @AddToRuleKey
  private final SourcePath jsPackager;

  @AddToRuleKey
  private final ReactNativePlatform platform;

  private final ReactNativeDeps depsFinder;
  private final Path jsOutput;
  private final Path resource;

  protected ReactNativeBundle(
      BuildRuleParams ruleParams,
      SourcePathResolver resolver,
      SourcePath entryPath,
      boolean isDevMode,
      String bundleName,
      SourcePath jsPackager,
      ReactNativePlatform platform,
      ReactNativeDeps depsFinder) {
    super(ruleParams, resolver);
    this.entryPath = entryPath;
    this.isDevMode = isDevMode;
    this.jsPackager = jsPackager;
    this.platform = platform;
    this.depsFinder = depsFinder;
    BuildTarget buildTarget = ruleParams.getBuildTarget();
    this.jsOutput = BuildTargets.getGenPath(buildTarget, "__%s_js__/").resolve(bundleName);
    this.resource = BuildTargets.getGenPath(buildTarget, "__%s_res__/").resolve("res");
  }

  @Override
  public ImmutableList<Step> getBuildSteps(
      BuildContext context,
      BuildableContext buildableContext) {
    ImmutableList.Builder<Step> steps = ImmutableList.builder();
    steps.add(new MakeCleanDirectoryStep(jsOutput.getParent()));
    steps.add(new MakeCleanDirectoryStep(resource));

    steps.add(
        new ShellStep() {
          @Override
          public String getShortName() {
            return "bundle_react_native";
          }

          @Override
          protected ImmutableList<String> getShellCommandInternal(ExecutionContext context) {
            ProjectFilesystem filesystem = context.getProjectFilesystem();
            return ImmutableList.of(
                getResolver().getPath(jsPackager).toString(),
                "bundle",
                "--entry-file", filesystem.resolve(getResolver().getPath(entryPath)).toString(),
                "--platform", platform.toString(),
                "--dev", isDevMode ? "true" : "false",
                "--bundle-output", filesystem.resolve(jsOutput).toString(),
                "--assets-dest", filesystem.resolve(resource).toString());
          }
        });
    buildableContext.recordArtifact(jsOutput);
    buildableContext.recordArtifact(resource);
    return steps.build();
  }

  public Path getPathToJSBundleDir() {
    return jsOutput.getParent();
  }

  public Path getPathToResources() {
    return resource;
  }

  @Override
  public Path getPathToOutput() {
    return jsOutput;
  }

  @Override
  public Sha1HashCode getAbiKeyForDeps() {
    return depsFinder.getInputsHash();
  }
}


File: src/com/facebook/buck/js/ReactNativeLibraryGraphEnhancer.java
/*
 * Copyright 2015-present Facebook, Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may
 *  not use this file except in compliance with the License. You may obtain
 *  a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 *  License for the specific language governing permissions and limitations
 *  under the License.
 */

package com.facebook.buck.js;

import com.facebook.buck.android.AndroidResource;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.PathSourcePath;
import com.facebook.buck.rules.Sha1HashCode;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.util.HumanReadableException;
import com.google.common.base.Optional;
import com.google.common.base.Supplier;
import com.google.common.base.Suppliers;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableSortedSet;

import java.nio.file.Path;

public class ReactNativeLibraryGraphEnhancer {

  private static final Flavor REACT_NATIVE_DEPS_FLAVOR = ImmutableFlavor.of("rn_deps");
  private static final Flavor REACT_NATIVE_BUNDLE_FLAVOR = ImmutableFlavor.of("bundle");
  private static final Flavor REACT_NATIVE_ANDROID_RES_FLAVOR = ImmutableFlavor.of("android_res");

  private final ReactNativeBuckConfig buckConfig;

  public ReactNativeLibraryGraphEnhancer(ReactNativeBuckConfig buckConfig) {
    this.buckConfig = buckConfig;
  }

  private ReactNativeDeps createReactNativeDeps(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      ReactNativeLibraryArgs args,
      ReactNativePlatform platform) {
    BuildTarget originalBuildTarget = params.getBuildTarget();
    SourcePathResolver sourcePathResolver = new SourcePathResolver(resolver);


    BuildTarget depsFinderTarget = BuildTarget.builder(originalBuildTarget)
        .addFlavors(REACT_NATIVE_DEPS_FLAVOR)
        .build();
    BuildRuleParams paramsForDepsFinder = params.copyWithBuildTarget(depsFinderTarget);
    ReactNativeDeps depsFinder = new ReactNativeDeps(
        paramsForDepsFinder,
        sourcePathResolver,
        getPackager(),
        args.srcs.get(),
        args.entryPath,
        platform);
    return resolver.addToIndex(depsFinder);
  }

  public AndroidReactNativeLibrary enhanceForAndroid(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      AndroidReactNativeLibraryDescription.Args args) {
    final ReactNativeDeps reactNativeDeps =
        createReactNativeDeps(params, resolver, args, ReactNativePlatform.ANDROID);

    SourcePathResolver sourcePathResolver = new SourcePathResolver(resolver);

    BuildTarget originalBuildTarget = params.getBuildTarget();
    BuildRuleParams paramsForBundle =
        params.copyWithBuildTarget(
            BuildTarget.builder(originalBuildTarget)
                .addFlavors(REACT_NATIVE_BUNDLE_FLAVOR)
                .build())
            .copyWithExtraDeps(
                Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of(reactNativeDeps)));
    ReactNativeBundle bundle = new ReactNativeBundle(
        paramsForBundle,
        sourcePathResolver,
        args.entryPath,
        ReactNativeFlavors.isDevMode(originalBuildTarget),
        args.bundleName,
        getPackager(),
        ReactNativePlatform.ANDROID,
        reactNativeDeps);
    resolver.addToIndex(bundle);

    ImmutableList.Builder<BuildRule> extraDeps = ImmutableList.builder();
    extraDeps.add(bundle);
    if (args.rDotJavaPackage.isPresent()) {
      BuildRuleParams paramsForResource =
          params.copyWithBuildTarget(
              BuildTarget.builder(originalBuildTarget)
                  .addFlavors(REACT_NATIVE_ANDROID_RES_FLAVOR)
                  .build())
              .copyWithExtraDeps(Suppliers.ofInstance(
                      ImmutableSortedSet.<BuildRule>of(bundle, reactNativeDeps)));

      BuildRule resource = new AndroidResource(
              paramsForResource,
              sourcePathResolver,
              /* deps */ ImmutableSortedSet.<BuildRule>of(),
              new PathSourcePath(params.getProjectFilesystem(), bundle.getPathToResources()),
              /* resSrcs */ ImmutableSortedSet.<Path>of(),
              args.rDotJavaPackage.get(),
              /* assets */ null,
              /* assetsSrcs */ ImmutableSortedSet.<Path>of(),
              /* manifest */ null,
              /* hasWhitelistedStrings */ false,
              Optional.of(
                  Suppliers.memoize(
                      new Supplier<Sha1HashCode>() {
                        @Override
                        public Sha1HashCode get() {
                          return reactNativeDeps.getInputsHash();
                        }
                      })));
      resolver.addToIndex(resource);
      extraDeps.add(resource);
    }

    return new AndroidReactNativeLibrary(
        params.appendExtraDeps(extraDeps.build()),
        sourcePathResolver,
        bundle);
  }

  public ReactNativeBundle enhanceForIos(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      ReactNativeLibraryArgs args) {
    ReactNativeDeps reactNativeDeps =
        createReactNativeDeps(params, resolver, args, ReactNativePlatform.IOS);

    return new ReactNativeBundle(
        params.appendExtraDeps(ImmutableList.of((BuildRule) reactNativeDeps)),
        new SourcePathResolver(resolver),
        args.entryPath,
        ReactNativeFlavors.isDevMode(params.getBuildTarget()),
        args.bundleName,
        getPackager(),
        ReactNativePlatform.IOS,
        reactNativeDeps);
  }

  private SourcePath getPackager() {
    Optional<SourcePath> packager = buckConfig.getPackager();
    if (!packager.isPresent()) {
      throw new HumanReadableException("In order to use a 'react_native_library' rule, please " +
          "specify 'packager' in .buckconfig under the 'react-native' section.");
    }
    return packager.get();
  }
}
