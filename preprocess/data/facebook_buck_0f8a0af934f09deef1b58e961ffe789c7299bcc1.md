Refactoring Types: ['Move Method', 'Move Class']
escription.java
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
package com.facebook.buck.android;

import com.facebook.buck.cxx.CxxPlatform;
import com.facebook.buck.cxx.CxxPreprocessables;
import com.facebook.buck.cxx.CxxPreprocessorInput;
import com.facebook.buck.cxx.CxxSource;
import com.facebook.buck.cxx.Linker;
import com.facebook.buck.cxx.NativeLinkable;
import com.facebook.buck.cxx.NativeLinkableInput;
import com.facebook.buck.cxx.NativeLinkables;
import com.facebook.buck.file.WriteFile;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargets;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.model.Pair;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRuleType;
import com.facebook.buck.rules.Description;
import com.facebook.buck.rules.PathSourcePath;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.macros.EnvironmentVariableMacroExpander;
import com.facebook.buck.rules.macros.MacroExpander;
import com.facebook.buck.rules.macros.MacroHandler;
import com.facebook.buck.util.BuckConstant;
import com.facebook.buck.util.Escaper;
import com.facebook.buck.util.MoreIterables;
import com.facebook.buck.util.MoreStrings;
import com.facebook.buck.util.environment.Platform;
import com.facebook.infer.annotation.SuppressFieldNotInitialized;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Functions;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.base.Predicates;
import com.google.common.base.Suppliers;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;

import java.io.IOException;
import java.nio.file.FileVisitOption;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.EnumSet;
import java.util.Map;
import java.util.regex.Pattern;

public class NdkLibraryDescription implements Description<NdkLibraryDescription.Arg> {

  public static final BuildRuleType TYPE = BuildRuleType.of("ndk_library");

  private static final Flavor MAKEFILE_FLAVOR = ImmutableFlavor.of("makefile");

  private static final Pattern EXTENSIONS_REGEX =
      Pattern.compile(
              ".*\\." +
              MoreStrings.regexPatternForAny("mk", "h", "hpp", "c", "cpp", "cc", "cxx") + "$");

  public static final MacroHandler MACRO_HANDLER = new MacroHandler(
      ImmutableMap.<String, MacroExpander>of(
          "env", new EnvironmentVariableMacroExpander(Platform.detect())
      )
  );

  private final Optional<String> ndkVersion;
  private final ImmutableMap<NdkCxxPlatforms.TargetCpuType, NdkCxxPlatform> cxxPlatforms;

  public NdkLibraryDescription(
      Optional<String> ndkVersion,
      ImmutableMap<NdkCxxPlatforms.TargetCpuType, NdkCxxPlatform> cxxPlatforms) {
    this.ndkVersion = ndkVersion;
    this.cxxPlatforms = Preconditions.checkNotNull(cxxPlatforms);
  }

  @Override
  public BuildRuleType getBuildRuleType() {
    return TYPE;
  }

  @Override
  public Arg createUnpopulatedConstructorArg() {
    return new Arg();
  }

  private Iterable<String> escapeForMakefile(Iterable<String> args) {
    ImmutableList.Builder<String> escapedArgs = ImmutableList.builder();

    for (String arg : args) {
      String escapedArg = arg;

      // The ndk-build makefiles make heavy use of the "eval" function to propagate variables,
      // which means we need to perform additional makefile escaping for *every* "eval" that
      // gets used.  Turns out there are three "evals", so we escape a total of four times
      // including the initial escaping.  Since the makefiles eventually hand-off these values
      // to the shell, we first perform bash escaping.
      //
      escapedArg = Escaper.escapeAsShellString(escapedArg);
      for (int i = 0; i < 4; i++) {
        escapedArg = Escaper.escapeAsMakefileValueString(escapedArg);
      }

      // We run ndk-build from the root of the NDK, so fixup paths that use the relative path to
      // the buck out directory.
      if (arg.startsWith(BuckConstant.BUCK_OUTPUT_DIRECTORY)) {
        escapedArg = "$(BUCK_PROJECT_DIR)/" + escapedArg;
      }

      escapedArgs.add(escapedArg);
    }

    return escapedArgs.build();
  }

  private String getTargetArchAbi(NdkCxxPlatforms.TargetCpuType cpuType) {
    switch (cpuType) {
      case ARM:
        return "armeabi";
      case ARMV7:
        return "armeabi-v7a";
      case X86:
        return "x86";
      case MIPS:
        return "mips";
      default:
        throw new IllegalStateException();
    }
  }

  @VisibleForTesting
  protected static Path getGeneratedMakefilePath(BuildTarget target) {
    return BuildTargets.getGenPath(target, "Android.%s.mk");
  }

  /**
   * @return a {@link BuildRule} which generates a Android.mk which pulls in the local Android.mk
   *     file and also appends relevant preprocessor and linker flags to use C/C++ library deps.
   */
  private Pair<BuildRule, Iterable<BuildRule>> generateMakefile(
      final BuildRuleParams params,
      BuildRuleResolver resolver) {

    SourcePathResolver pathResolver = new SourcePathResolver(resolver);

    ImmutableList.Builder<String> outputLinesBuilder = ImmutableList.builder();
    ImmutableSortedSet.Builder<BuildRule> deps = ImmutableSortedSet.naturalOrder();

    for (Map.Entry<NdkCxxPlatforms.TargetCpuType, NdkCxxPlatform> entry : cxxPlatforms.entrySet()) {
      CxxPlatform cxxPlatform = entry.getValue().getCxxPlatform();

      CxxPreprocessorInput cxxPreprocessorInput;
      try {
        // Collect the preprocessor input for all C/C++ library deps.  We search *through* other
        // NDK library rules.
        cxxPreprocessorInput = CxxPreprocessorInput.concat(
            CxxPreprocessables.getTransitiveCxxPreprocessorInput(
                cxxPlatform,
                params.getDeps(),
                Predicates.instanceOf(NdkLibrary.class)));
      } catch (CxxPreprocessorInput.ConflictingHeadersException e) {
        throw e.getHumanReadableExceptionForBuildTarget(params.getBuildTarget());
      }

      // We add any dependencies from the C/C++ preprocessor input to this rule, even though
      // it technically should be added to the top-level rule.
      deps.addAll(
          pathResolver.filterBuildRuleInputs(
              cxxPreprocessorInput.getIncludes().getPrefixHeaders()));
      deps.addAll(
          pathResolver.filterBuildRuleInputs(
              cxxPreprocessorInput.getIncludes().getNameToPathMap().values()));
      deps.addAll(resolver.getAllRules(cxxPreprocessorInput.getRules()));

      // Add in the transitive preprocessor flags contributed by C/C++ library rules into the
      // NDK build.
      Iterable<String> ppflags = Iterables.concat(
          cxxPreprocessorInput.getPreprocessorFlags().get(CxxSource.Type.C),
          MoreIterables.zipAndConcat(
              Iterables.cycle("-I"),
              FluentIterable.from(cxxPreprocessorInput.getIncludeRoots())
                  .transform(Functions.toStringFunction())),
          MoreIterables.zipAndConcat(
              Iterables.cycle("-isystem"),
              FluentIterable.from(cxxPreprocessorInput.getIncludeRoots())
                  .transform(Functions.toStringFunction())));
      String localCflags = Joiner.on(' ').join(escapeForMakefile(ppflags));

      // Collect the native linkable input for all C/C++ library deps.  We search *through* other
      // NDK library rules.
      NativeLinkableInput nativeLinkableInput =
          NativeLinkables.getTransitiveNativeLinkableInput(
              cxxPlatform,
              params.getDeps(),
              Linker.LinkableDepType.SHARED,
              Predicates.or(
                  Predicates.instanceOf(NativeLinkable.class),
                  Predicates.instanceOf(NdkLibrary.class)),
              /* reverse */ true);

      // We add any dependencies from the native linkable input to this rule, even though
      // it technically should be added to the top-level rule.
      deps.addAll(pathResolver.filterBuildRuleInputs(nativeLinkableInput.getInputs()));

      // Add in the transitive native linkable flags contributed by C/C++ library rules into the
      // NDK build.
      String localLdflags = Joiner.on(' ').join(escapeForMakefile(nativeLinkableInput.getArgs()));

      // Write the relevant lines to the generated makefile.
      if (!localCflags.isEmpty() || !localLdflags.isEmpty()) {
        NdkCxxPlatforms.TargetCpuType targetCpuType = entry.getKey();
        String targetArchAbi = getTargetArchAbi(targetCpuType);

        outputLinesBuilder.add(String.format("ifeq ($(TARGET_ARCH_ABI),%s)", targetArchAbi));
        if (!localCflags.isEmpty()) {
          outputLinesBuilder.add("BUCK_DEP_CFLAGS=" + localCflags);
        }
        if (!localLdflags.isEmpty()) {
          outputLinesBuilder.add("BUCK_DEP_LDFLAGS=" + localLdflags);
        }
        outputLinesBuilder.add("endif");
        outputLinesBuilder.add("");
      }
    }

    // GCC-only magic that rewrites non-deterministic parts of builds
    String ndksubst = NdkCxxPlatforms.ANDROID_NDK_ROOT;

    outputLinesBuilder.addAll(
        ImmutableList.copyOf(new String[] {
              // We're evaluated once per architecture, but want to add the cflags only once.
              "ifeq ($(BUCK_ALREADY_HOOKED_CFLAGS),)",
              "BUCK_ALREADY_HOOKED_CFLAGS := 1",
              // Only GCC supports -fdebug-prefix-map
              "ifeq ($(filter clang%,$(NDK_TOOLCHAIN_VERSION)),)",
              // Replace absolute paths with machine-relative ones.
              "NDK_APP_CFLAGS += -fdebug-prefix-map=$(NDK_ROOT)/=" + ndksubst + "/",
              "NDK_APP_CFLAGS += -fdebug-prefix-map=$(abspath $(BUCK_PROJECT_DIR))/=./",
              // Replace paths relative to the build rule with paths relative to the
              // repository root.
              "NDK_APP_CFLAGS += -fdebug-prefix-map=$(BUCK_PROJECT_DIR)/=./",
              "NDK_APP_CFLAGS += -fdebug-prefix-map=./=" +
              ".$(subst $(abspath $(BUCK_PROJECT_DIR)),,$(abspath $(CURDIR)))/",
              "NDK_APP_CFLAGS += -fno-record-gcc-switches",
              "ifeq ($(filter 4.6,$(TOOLCHAIN_VERSION)),)",
              // Do not let header canonicalization undo the work we just did above.  Note that GCC
              // 4.6 doesn't support this option, but that's okay, because it doesn't canonicalize
              // headers either.
              "NDK_APP_CPPFLAGS += -fno-canonical-system-headers",
              // If we include the -fdebug-prefix-map in the switches, the "from"-parts of which
              // contain machine-specific paths, we lose determinism.  GCC 4.6 didn't include
              // detailed command line argument information anyway.
              "NDK_APP_CFLAGS += -gno-record-gcc-switches",
              "endif", // !GCC 4.6
              "endif", // !clang

              // Rewrite NDK module paths to import managed modules by relative path instead of by
              // absolute path, but only for modules under the project root.
              "BUCK_SAVED_IMPORTS := $(__ndk_import_dirs)",
              "__ndk_import_dirs :=",
              "$(foreach __dir,$(BUCK_SAVED_IMPORTS),\\",
              "$(call import-add-path-optional,\\",
              "$(if $(filter $(abspath $(BUCK_PROJECT_DIR))%,$(__dir)),\\",
              "$(BUCK_PROJECT_DIR)$(patsubst $(abspath $(BUCK_PROJECT_DIR))%,%,$(__dir)),\\",
              "$(__dir))))",
              "endif", // !already hooked
            }));

    outputLinesBuilder.add("include Android.mk");

    BuildTarget makefileTarget = BuildTarget
        .builder(params.getBuildTarget())
        .addFlavors(MAKEFILE_FLAVOR)
        .build();
    BuildRuleParams makefileParams = params.copyWithChanges(
        makefileTarget,
        Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of()),
        Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of()));
    final Path makefilePath = getGeneratedMakefilePath(params.getBuildTarget());
    final String contents = Joiner.on(System.lineSeparator()).join(outputLinesBuilder.build());

    return new Pair<BuildRule, Iterable<BuildRule>>(
        new WriteFile(makefileParams, pathResolver, contents, makefilePath),
        deps.build());
  }

  @VisibleForTesting
  protected ImmutableSortedSet<SourcePath> findSources(
      final ProjectFilesystem filesystem,
      final Path buildRulePath) {
    final ImmutableSortedSet.Builder<SourcePath> srcs = ImmutableSortedSet.naturalOrder();

    try {
      final Path rootDirectory = filesystem.resolve(buildRulePath);
      Files.walkFileTree(
          rootDirectory,
          EnumSet.of(FileVisitOption.FOLLOW_LINKS),
          /* maxDepth */ Integer.MAX_VALUE,
          new SimpleFileVisitor<Path>() {
            @Override
            public FileVisitResult visitFile(Path file, BasicFileAttributes attrs)
                throws IOException {
              if (EXTENSIONS_REGEX.matcher(file.toString()).matches()) {
                srcs.add(
                    new PathSourcePath(
                        filesystem,
                        buildRulePath.resolve(rootDirectory.relativize(file))));
              }

              return super.visitFile(file, attrs);
            }
          });
    } catch (IOException e) {
      throw new RuntimeException(e);
    }

    return srcs.build();
  }

  @Override
  public <A extends Arg> NdkLibrary createBuildRule(
      final BuildRuleParams params,
      BuildRuleResolver resolver,
      A args) {

    Pair<BuildRule, Iterable<BuildRule>> makefilePair = generateMakefile(params, resolver);
    resolver.addToIndex(makefilePair.getFirst());
    return new NdkLibrary(
        params.appendExtraDeps(
            ImmutableSortedSet.<BuildRule>naturalOrder()
                .add(makefilePair.getFirst())
                .addAll(makefilePair.getSecond())
                .build()),
        new SourcePathResolver(resolver),
        getGeneratedMakefilePath(params.getBuildTarget()),
        findSources(params.getProjectFilesystem(), params.getBuildTarget().getBasePath()),
        args.flags.get(),
        args.isAsset.or(false),
        ndkVersion,
        MACRO_HANDLER.getExpander(
            params.getBuildTarget(),
            resolver,
            params.getProjectFilesystem()));
  }

  @SuppressFieldNotInitialized
  public static class Arg {
    public Optional<ImmutableList<String>> flags;
    public Optional<Boolean> isAsset;
    public Optional<ImmutableSortedSet<BuildTarget>> deps;
  }

}


File: src/com/facebook/buck/cxx/AbstractCxxHeaders.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.rules.RuleKey;
import com.facebook.buck.rules.RuleKeyAppendable;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.util.immutables.BuckStyleImmutable;
import com.google.common.collect.ImmutableSortedSet;

import org.immutables.value.Value;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;

@Value.Immutable
@BuckStyleImmutable
abstract class AbstractCxxHeaders implements RuleKeyAppendable {

  /**
   * List of headers that are implicitly included at the beginning of each preprocessed source file.
   */
  abstract List<SourcePath> getPrefixHeaders();

  /**
   * Maps the name of the header (e.g. the path used to include it in a C/C++ source) to the
   * real location of the header.
   */
  abstract Map<Path, SourcePath> getNameToPathMap();

  /**
   * Maps the full of the header (e.g. the path to the header that appears in error messages) to
   * the real location of the header.
   */
  abstract Map<Path, SourcePath> getFullNameToPathMap();

  @Override
  public RuleKey.Builder appendToRuleKey(RuleKey.Builder builder) {
    builder.setReflectively("prefixHeaders", getPrefixHeaders());

    for (Path path : ImmutableSortedSet.copyOf(getNameToPathMap().keySet())) {
      SourcePath source = getNameToPathMap().get(path);
      builder.setReflectively("include(" + path + ")", source);
    }

    return builder;
  }
}


File: src/com/facebook/buck/cxx/AbstractCxxPreprocessorInput.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.buck.util.immutables.BuckStyleImmutable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Multimap;

import org.immutables.value.Value;

import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The components that get contributed to a top-level run of the C++ preprocessor.
 */
@Value.Immutable
@BuckStyleImmutable
abstract class AbstractCxxPreprocessorInput {

  // The build rules which produce headers found in the includes below.
  @Value.Parameter
  public abstract Set<BuildTarget> getRules();

  @Value.Parameter
  public abstract Multimap<CxxSource.Type, String> getPreprocessorFlags();

  @Value.Parameter
  @Value.Default
  public CxxHeaders getIncludes() {
    return CxxHeaders.builder().build();
  }

  // Normal include directories where headers are found.
  @Value.Parameter
  public abstract List<Path> getIncludeRoots();

  // Include directories where system headers.
  @Value.Parameter
  public abstract List<Path> getSystemIncludeRoots();

  // Directories where frameworks are stored.
  @Value.Parameter
  public abstract List<Path> getFrameworkRoots();

  public static final CxxPreprocessorInput EMPTY = CxxPreprocessorInput.builder().build();

  public static CxxPreprocessorInput.Builder builder() {
    return CxxPreprocessorInput.builder();
  }

  private static void addAllEntriesToIncludeMap(
      Map<Path, SourcePath> destination,
      Map<Path, SourcePath> source) throws ConflictingHeadersException {
    for (Map.Entry<Path, SourcePath> entry : source.entrySet()) {
      SourcePath original = destination.put(entry.getKey(), entry.getValue());
      if (original != null && !original.equals(entry.getValue())) {
        throw new ConflictingHeadersException(entry.getKey(), original, entry.getValue());
      }
    }
  }

  public static CxxPreprocessorInput concat(Iterable<CxxPreprocessorInput> inputs)
      throws ConflictingHeadersException {
    ImmutableSet.Builder<BuildTarget> rules = ImmutableSet.builder();
    ImmutableMultimap.Builder<CxxSource.Type, String> preprocessorFlags =
      ImmutableMultimap.builder();
    ImmutableList.Builder<SourcePath> prefixHeaders = ImmutableList.builder();
    Map<Path, SourcePath> includeNameToPathMap = new HashMap<>();
    Map<Path, SourcePath> includeFullNameToPathMap = new HashMap<>();
    ImmutableList.Builder<Path> includeRoots = ImmutableList.builder();
    ImmutableList.Builder<Path> systemIncludeRoots = ImmutableList.builder();
    ImmutableList.Builder<Path> frameworkRoots = ImmutableList.builder();

    for (CxxPreprocessorInput input : inputs) {
      rules.addAll(input.getRules());
      preprocessorFlags.putAll(input.getPreprocessorFlags());
      prefixHeaders.addAll(input.getIncludes().getPrefixHeaders());
      addAllEntriesToIncludeMap(
          includeNameToPathMap,
          input.getIncludes().getNameToPathMap());
      addAllEntriesToIncludeMap(
          includeFullNameToPathMap,
          input.getIncludes().getFullNameToPathMap());
      includeRoots.addAll(input.getIncludeRoots());
      systemIncludeRoots.addAll(input.getSystemIncludeRoots());
      frameworkRoots.addAll(input.getFrameworkRoots());
    }

    return CxxPreprocessorInput.of(
        rules.build(),
        preprocessorFlags.build(),
        CxxHeaders.builder()
            .addAllPrefixHeaders(prefixHeaders.build())
            .putAllNameToPathMap(includeNameToPathMap)
            .putAllFullNameToPathMap(includeFullNameToPathMap)
            .build(),
        includeRoots.build(),
        systemIncludeRoots.build(),
        frameworkRoots.build());
  }

  @SuppressWarnings("serial")
  public static class ConflictingHeadersException extends Exception {
    public ConflictingHeadersException(Path key, SourcePath value1, SourcePath value2) {
      super(
          String.format(
              "'%s' maps to both %s.",
              key,
              ImmutableSortedSet.of(value1, value2)));
    }

    public HumanReadableException getHumanReadableExceptionForBuildTarget(BuildTarget buildTarget) {
      return new HumanReadableException(
          this,
          "Target '%s' uses conflicting header file mappings. %s",
          buildTarget,
          getMessage());
    }
  }

}


File: src/com/facebook/buck/cxx/CxxDescriptionEnhancer.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.io.MorePaths;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargets;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.HasBuildTarget;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.model.Pair;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.Description;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SymlinkTree;
import com.facebook.buck.rules.TargetNode;
import com.facebook.buck.rules.coercer.Either;
import com.facebook.buck.rules.coercer.SourceWithFlags;
import com.facebook.buck.util.HumanReadableException;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.base.Functions;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.base.Predicates;
import com.google.common.base.Suppliers;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;
import com.google.common.io.Files;

import java.nio.file.Path;
import java.util.Collections;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class CxxDescriptionEnhancer {

  private static final Logger LOG = Logger.get(CxxDescriptionEnhancer.class);

  public static final Flavor HEADER_SYMLINK_TREE_FLAVOR = ImmutableFlavor.of("header-symlink-tree");
  public static final Flavor EXPORTED_HEADER_SYMLINK_TREE_FLAVOR =
      ImmutableFlavor.of("exported-header-symlink-tree");
  public static final Flavor STATIC_FLAVOR = ImmutableFlavor.of("static");
  public static final Flavor STATIC_PIC_FLAVOR = ImmutableFlavor.of("static-pic");
  public static final Flavor SHARED_FLAVOR = ImmutableFlavor.of("shared");
  public static final Flavor MACH_O_BUNDLE_FLAVOR = ImmutableFlavor.of("mach-o-bundle");

  public static final Flavor CXX_LINK_BINARY_FLAVOR = ImmutableFlavor.of("binary");
  public static final Flavor LEX_YACC_SOURCE_FLAVOR = ImmutableFlavor.of("lex_yacc_sources");

  private CxxDescriptionEnhancer() {}

  private static BuildTarget createLexYaccSourcesBuildTarget(BuildTarget target) {
    return BuildTarget.builder(target).addFlavors(LEX_YACC_SOURCE_FLAVOR).build();
  }

  public static CxxHeaderSourceSpec requireLexYaccSources(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      ImmutableMap<String, SourcePath> lexSources,
      ImmutableMap<String, SourcePath> yaccSources) {
    BuildTarget lexYaccTarget = createLexYaccSourcesBuildTarget(params.getBuildTarget());

    // Check the cache...
    Optional<BuildRule> rule = ruleResolver.getRuleOptional(lexYaccTarget);
    if (rule.isPresent()) {
      @SuppressWarnings("unchecked")
      ContainerBuildRule<CxxHeaderSourceSpec> containerRule =
          (ContainerBuildRule<CxxHeaderSourceSpec>) rule.get();
      return containerRule.get();
    }

    // Setup the rules to run lex/yacc.
    CxxHeaderSourceSpec lexYaccSources =
        CxxDescriptionEnhancer.createLexYaccBuildRules(
            params,
            ruleResolver,
            cxxPlatform,
            ImmutableList.<String>of(),
            lexSources,
            ImmutableList.<String>of(),
            yaccSources);

    ruleResolver.addToIndex(
        ContainerBuildRule.of(
            params,
            pathResolver,
            lexYaccTarget,
            lexYaccSources));

    return lexYaccSources;
  }

  public static SymlinkTree createHeaderSymlinkTree(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      boolean includeLexYaccHeaders,
      ImmutableMap<String, SourcePath> lexSources,
      ImmutableMap<String, SourcePath> yaccSources,
      ImmutableMap<Path, SourcePath> headers,
      HeaderVisibility headerVisibility) {

    BuildTarget headerSymlinkTreeTarget =
        CxxDescriptionEnhancer.createHeaderSymlinkTreeTarget(
            params.getBuildTarget(),
            cxxPlatform.getFlavor(),
            headerVisibility);
    Path headerSymlinkTreeRoot =
        CxxDescriptionEnhancer.getHeaderSymlinkTreePath(
            params.getBuildTarget(),
            cxxPlatform.getFlavor(),
            headerVisibility);

    CxxHeaderSourceSpec lexYaccSources;
    if (includeLexYaccHeaders) {
      lexYaccSources = requireLexYaccSources(
          params,
          ruleResolver,
          pathResolver,
          cxxPlatform,
          lexSources,
          yaccSources);
    } else {
      lexYaccSources = CxxHeaderSourceSpec.builder().build();
    }

    return CxxPreprocessables.createHeaderSymlinkTreeBuildRule(
        pathResolver,
        headerSymlinkTreeTarget,
        params,
        headerSymlinkTreeRoot,
        ImmutableMap.<Path, SourcePath>builder()
            .putAll(headers)
            .putAll(lexYaccSources.getCxxHeaders())
            .build());
  }

  public static SymlinkTree requireHeaderSymlinkTree(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      boolean includeLexYaccHeaders,
      ImmutableMap<String, SourcePath> lexSources,
      ImmutableMap<String, SourcePath> yaccSources,
      ImmutableMap<Path, SourcePath> headers,
      HeaderVisibility headerVisibility) {
    BuildTarget headerSymlinkTreeTarget =
        CxxDescriptionEnhancer.createHeaderSymlinkTreeTarget(
            params.getBuildTarget(),
            cxxPlatform.getFlavor(),
            headerVisibility);

    // Check the cache...
    Optional<BuildRule> rule = ruleResolver.getRuleOptional(headerSymlinkTreeTarget);
    if (rule.isPresent()) {
      Preconditions.checkState(rule.get() instanceof SymlinkTree);
      return (SymlinkTree) rule.get();
    }

    SymlinkTree symlinkTree = createHeaderSymlinkTree(
        params,
        ruleResolver,
        pathResolver,
        cxxPlatform,
        includeLexYaccHeaders,
        lexSources,
        yaccSources,
        headers,
        headerVisibility);

    ruleResolver.addToIndex(symlinkTree);

    return symlinkTree;
  }

  /**
   * @return the {@link BuildTarget} to use for the {@link BuildRule} generating the
   *    symlink tree of headers.
   */
  public static BuildTarget createHeaderSymlinkTreeTarget(
      BuildTarget target,
      Flavor platform,
      HeaderVisibility headerVisibility) {
    return BuildTarget
        .builder(target)
        .addFlavors(platform)
        .addFlavors(getHeaderSymlinkTreeFlavor(headerVisibility))
        .build();
  }

  /**
   * @return the {@link Path} to use for the symlink tree of headers.
   */
  public static Path getHeaderSymlinkTreePath(
      BuildTarget target,
      Flavor platform,
      HeaderVisibility headerVisibility) {
    return BuildTargets.getGenPath(
        createHeaderSymlinkTreeTarget(target, platform, headerVisibility),
        "%s");
  }

  public static Flavor getHeaderSymlinkTreeFlavor(HeaderVisibility headerVisibility) {
    switch (headerVisibility) {
      case PUBLIC:
        return EXPORTED_HEADER_SYMLINK_TREE_FLAVOR;
      case PRIVATE:
        return HEADER_SYMLINK_TREE_FLAVOR;
      default:
        throw new RuntimeException("Unexpected value of enum ExportMode");
    }
  }

  private static ImmutableMap<Path, SourcePath> getHeaderMapFromArgParameter(
      SourcePathResolver pathResolver,
      BuildTarget buildTarget,
      Optional<String> headerNamespace,
      String parameterName,
      Optional<Either<ImmutableList<SourcePath>, ImmutableMap<String, SourcePath>>> parameter) {
    ImmutableMap<String, SourcePath> headers;
    if (!parameter.isPresent()) {
      headers = ImmutableMap.of();
    } else if (parameter.get().isRight()) {
      headers = parameter.get().getRight();
    } else {
      headers = pathResolver.getSourcePathNames(
          buildTarget,
          parameterName,
          parameter.get().getLeft());
    }
    return CxxPreprocessables.resolveHeaderMap(
        headerNamespace.transform(MorePaths.TO_PATH)
            .or(buildTarget.getBasePath()),
        headers);
  }

  /**
   * @return a map of header locations to input {@link SourcePath} objects formed by parsing the
   *    input {@link SourcePath} objects for the "headers" parameter.
   */
  public static ImmutableMap<Path, SourcePath> parseHeaders(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxConstructorArg args) {
    return getHeaderMapFromArgParameter(
        new SourcePathResolver(resolver),
        params.getBuildTarget(),
        args.headerNamespace,
        "headers",
        args.headers);
  }

  /**
   * @return a map of header locations to input {@link SourcePath} objects formed by parsing the
   *    input {@link SourcePath} objects for the "exportedHeaders" parameter.
   */
  public static ImmutableMap<Path, SourcePath> parseExportedHeaders(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxLibraryDescription.Arg args) {
    return getHeaderMapFromArgParameter(
        new SourcePathResolver(resolver),
        params.getBuildTarget(),
        args.headerNamespace,
        "exportedHeaders",
        args.exportedHeaders);
  }

  /**
   * @return a list {@link CxxSource} objects formed by parsing the input {@link SourcePath}
   *    objects for the "srcs" parameter.
   */
  public static ImmutableMap<String, CxxSource> parseCxxSources(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxConstructorArg args) {
    ImmutableMap<String, SourceWithFlags> sources;
    if (!args.srcs.isPresent()) {
      sources = ImmutableMap.of();
    } else if (args.srcs.get().isRight()) {
      sources = args.srcs.get().getRight();
    } else {
      SourcePathResolver pathResolver = new SourcePathResolver(resolver);
      sources = pathResolver.getSourcePathNames(
          params.getBuildTarget(),
          "srcs",
          args.srcs.get().getLeft(),
          SourceWithFlags.TO_SOURCE_PATH);
    }
    return CxxCompilableEnhancer.resolveCxxSources(sources);
  }

  public static ImmutableMap<String, SourcePath> parseLexSources(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxConstructorArg args) {
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);
    return pathResolver.getSourcePathNames(
        params.getBuildTarget(),
        "lexSrcs",
        args.lexSrcs.or(ImmutableList.<SourcePath>of()));
  }

  public static ImmutableMap<String, SourcePath> parseYaccSources(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxConstructorArg args) {
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);
    return pathResolver.getSourcePathNames(
        params.getBuildTarget(),
        "yaccSrcs",
        args.yaccSrcs.or(ImmutableList.<SourcePath>of()));
  }

  @VisibleForTesting
  protected static BuildTarget createLexBuildTarget(BuildTarget target, String name) {
    return BuildTarget
        .builder(target.getUnflavoredBuildTarget())
        .addFlavors(
            ImmutableFlavor.of(
                String.format(
                    "lex-%s",
                    name.replace('/', '-').replace('.', '-').replace('+', '-').replace(' ', '-'))))
        .build();
  }

  @VisibleForTesting
  protected static BuildTarget createYaccBuildTarget(BuildTarget target, String name) {
    return BuildTarget
        .builder(target.getUnflavoredBuildTarget())
        .addFlavors(
            ImmutableFlavor.of(
                String.format(
                    "yacc-%s",
                    name.replace('/', '-').replace('.', '-').replace('+', '-').replace(' ', '-'))))
        .build();
  }

  /**
   * @return the output path prefix to use for yacc generated files.
   */
  @VisibleForTesting
  protected static Path getYaccOutputPrefix(BuildTarget target, String name) {
    BuildTarget flavoredTarget = createYaccBuildTarget(target, name);
    return BuildTargets.getGenPath(flavoredTarget, "%s/" + name);
  }

  /**
   * @return the output path to use for the lex generated C/C++ source.
   */
  @VisibleForTesting
  protected static Path getLexSourceOutputPath(BuildTarget target, String name) {
    BuildTarget flavoredTarget = createLexBuildTarget(target, name);
    return BuildTargets.getGenPath(flavoredTarget, "%s/" + name + ".cc");
  }

  /**
   * @return the output path to use for the lex generated C/C++ header.
   */
  @VisibleForTesting
  protected static Path getLexHeaderOutputPath(BuildTarget target, String name) {
    BuildTarget flavoredTarget = createLexBuildTarget(target, name);
    return BuildTargets.getGenPath(flavoredTarget, "%s/" + name + ".h");
  }

  /**
   * Generate {@link Lex} and {@link Yacc} rules generating C/C++ sources from the
   * given lex/yacc sources.
   *
   * @return {@link CxxHeaderSourceSpec} containing the generated headers/sources
   */
  public static CxxHeaderSourceSpec createLexYaccBuildRules(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxPlatform cxxPlatform,
      ImmutableList<String> lexFlags,
      ImmutableMap<String, SourcePath> lexSrcs,
      ImmutableList<String> yaccFlags,
      ImmutableMap<String, SourcePath> yaccSrcs) {
    if (!lexSrcs.isEmpty() && !cxxPlatform.getLex().isPresent()) {
      throw new HumanReadableException(
          "Platform %s must support lex to compile srcs %s",
          cxxPlatform,
          lexSrcs);
    }

    if (!yaccSrcs.isEmpty() && !cxxPlatform.getYacc().isPresent()) {
      throw new HumanReadableException(
          "Platform %s must support yacc to compile srcs %s",
          cxxPlatform,
          yaccSrcs);
    }

    SourcePathResolver pathResolver = new SourcePathResolver(resolver);

    ImmutableMap.Builder<String, CxxSource> lexYaccCxxSourcesBuilder = ImmutableMap.builder();
    ImmutableMap.Builder<Path, SourcePath> lexYaccHeadersBuilder = ImmutableMap.builder();

    // Loop over all lex sources, generating build rule for each one and adding the sources
    // and headers it generates to our bookkeeping maps.
    for (ImmutableMap.Entry<String, SourcePath> ent : lexSrcs.entrySet()) {
      final String name = ent.getKey();
      final SourcePath source = ent.getValue();

      BuildTarget target = createLexBuildTarget(params.getBuildTarget(), name);
      Path outputSource = getLexSourceOutputPath(target, name);
      Path outputHeader = getLexHeaderOutputPath(target, name);

      // Create the build rule to run lex on this source and add it to the resolver.
      Lex lex = new Lex(
          params.copyWithChanges(
              target,
              Suppliers.ofInstance(
                  ImmutableSortedSet.copyOf(
                      pathResolver.filterBuildRuleInputs(ImmutableList.of(source)))),
              Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of())),
          pathResolver,
          cxxPlatform.getLex().get(),
          ImmutableList.<String>builder()
              .addAll(cxxPlatform.getLexFlags())
              .addAll(lexFlags)
              .build(),
          outputSource,
          outputHeader,
          source);
      resolver.addToIndex(lex);

      // Record the output source and header as {@link BuildRuleSourcePath} objects.
      lexYaccCxxSourcesBuilder.put(
          name + ".cc",
          CxxSource.of(
              CxxSource.Type.CXX,
              new BuildTargetSourcePath(
                  lex.getProjectFilesystem(),
                  lex.getBuildTarget(),
                  outputSource),
              ImmutableList.<String>of()));
      lexYaccHeadersBuilder.put(
          params.getBuildTarget().getBasePath().resolve(name + ".h"),
          new BuildTargetSourcePath(
              lex.getProjectFilesystem(),
              lex.getBuildTarget(),
              outputHeader));
    }

    // Loop over all yaccc sources, generating build rule for each one and adding the sources
    // and headers it generates to our bookkeeping maps.
    for (ImmutableMap.Entry<String, SourcePath> ent : yaccSrcs.entrySet()) {
      final String name = ent.getKey();
      final SourcePath source = ent.getValue();

      BuildTarget target = createYaccBuildTarget(params.getBuildTarget(), name);
      Path outputPrefix = getYaccOutputPrefix(target, Files.getNameWithoutExtension(name));

      // Create the build rule to run yacc on this source and add it to the resolver.
      Yacc yacc = new Yacc(
          params.copyWithChanges(
              target,
              Suppliers.ofInstance(
                  ImmutableSortedSet.copyOf(
                      pathResolver.filterBuildRuleInputs(ImmutableList.of(source)))),
              Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of())),
          pathResolver,
          cxxPlatform.getYacc().get(),
          ImmutableList.<String>builder()
              .addAll(cxxPlatform.getYaccFlags())
              .addAll(yaccFlags)
              .build(),
          outputPrefix,
          source);
      resolver.addToIndex(yacc);

      // Record the output source and header as {@link BuildRuleSourcePath} objects.
      lexYaccCxxSourcesBuilder.put(
          name + ".cc",
          CxxSource.of(
              CxxSource.Type.CXX,
              new BuildTargetSourcePath(
                  yacc.getProjectFilesystem(),
                  yacc.getBuildTarget(),
                  Yacc.getSourceOutputPath(outputPrefix)),
              ImmutableList.<String>of()));

      lexYaccHeadersBuilder.put(
          params.getBuildTarget().getBasePath().resolve(name + ".h"),
          new BuildTargetSourcePath(
              yacc.getProjectFilesystem(),
              yacc.getBuildTarget(),
              Yacc.getHeaderOutputPath(outputPrefix)));
    }

    return CxxHeaderSourceSpec.of(
        lexYaccHeadersBuilder.build(),
        lexYaccCxxSourcesBuilder.build());
  }

  public static CxxPreprocessorInput combineCxxPreprocessorInput(
      BuildRuleParams params,
      CxxPlatform cxxPlatform,
      ImmutableMultimap<CxxSource.Type, String> preprocessorFlags,
      ImmutableList<SourcePath> prefixHeaders,
      ImmutableList<SymlinkTree> headerSymlinkTrees,
      ImmutableList<Path> frameworkSearchPaths,
      Iterable<CxxPreprocessorInput> cxxPreprocessorInputFromDeps) {

    // Add the private includes of any rules which list this rule as a test.
    BuildTarget targetWithoutFlavor = BuildTarget.of(
        params.getBuildTarget().getUnflavoredBuildTarget());
    ImmutableList.Builder<CxxPreprocessorInput> cxxPreprocessorInputFromTestedRulesBuilder =
        ImmutableList.builder();
    for (BuildRule rule : params.getDeps()) {
      if (rule instanceof NativeTestable) {
        NativeTestable testable = (NativeTestable) rule;
        if (testable.isTestedBy(targetWithoutFlavor)) {
          LOG.debug(
              "Adding private includes of tested rule %s to testing rule %s",
              rule.getBuildTarget(),
              params.getBuildTarget());
          cxxPreprocessorInputFromTestedRulesBuilder.add(
              testable.getCxxPreprocessorInput(
                  cxxPlatform,
                  HeaderVisibility.PRIVATE));
        }
      }
    }

    ImmutableList<CxxPreprocessorInput> cxxPreprocessorInputFromTestedRules =
        cxxPreprocessorInputFromTestedRulesBuilder.build();
    LOG.verbose(
        "Rules tested by target %s added private includes %s",
        params.getBuildTarget(),
        cxxPreprocessorInputFromTestedRules);

    ImmutableMap.Builder<Path, SourcePath> allLinks = ImmutableMap.builder();
    ImmutableMap.Builder<Path, SourcePath> allFullLinks = ImmutableMap.builder();
    ImmutableList.Builder<Path> allIncludeRoots = ImmutableList.builder();
    for (SymlinkTree headerSymlinkTree : headerSymlinkTrees) {
      allLinks.putAll(headerSymlinkTree.getLinks());
      allFullLinks.putAll(headerSymlinkTree.getFullLinks());
      allIncludeRoots.add(headerSymlinkTree.getRoot());
    }

    CxxPreprocessorInput localPreprocessorInput =
        CxxPreprocessorInput.builder()
            .addAllRules(Iterables.transform(headerSymlinkTrees, HasBuildTarget.TO_TARGET))
            .putAllPreprocessorFlags(preprocessorFlags)
            .setIncludes(
                CxxHeaders.builder()
                    .addAllPrefixHeaders(prefixHeaders)
                    .putAllNameToPathMap(allLinks.build())
                    .putAllFullNameToPathMap(allFullLinks.build())
                    .build())
            .addAllIncludeRoots(allIncludeRoots.build())
            .addAllFrameworkRoots(frameworkSearchPaths)
            .build();

    try {
      return CxxPreprocessorInput.concat(
          Iterables.concat(
              Collections.singleton(localPreprocessorInput),
              cxxPreprocessorInputFromDeps,
              cxxPreprocessorInputFromTestedRules));
    } catch (CxxPreprocessorInput.ConflictingHeadersException e) {
      throw e.getHumanReadableExceptionForBuildTarget(params.getBuildTarget());
    }
  }

  public static BuildTarget createStaticLibraryBuildTarget(
      BuildTarget target,
      Flavor platform,
      CxxSourceRuleFactory.PicType pic) {
    return BuildTarget.builder(target)
        .addFlavors(platform)
        .addFlavors(pic == CxxSourceRuleFactory.PicType.PDC ? STATIC_FLAVOR : STATIC_PIC_FLAVOR)
        .build();
  }

  public static BuildTarget createSharedLibraryBuildTarget(
      BuildTarget target,
      Flavor platform) {
    return BuildTarget.builder(target).addFlavors(platform).addFlavors(SHARED_FLAVOR).build();
  }

  public static Path getStaticLibraryPath(
      BuildTarget target,
      Flavor platform,
      CxxSourceRuleFactory.PicType pic) {
    String name = String.format("lib%s.a", target.getShortName());
    return BuildTargets.getGenPath(createStaticLibraryBuildTarget(target, platform, pic), "%s")
        .resolve(name);
  }

  public static String getDefaultSharedLibrarySoname(BuildTarget target, CxxPlatform platform) {
    String libName =
        Joiner.on('_').join(
            ImmutableList.builder()
                .addAll(
                    FluentIterable.from(target.getBasePath())
                        .transform(Functions.toStringFunction())
                        .filter(Predicates.not(Predicates.equalTo(""))))
                .add(
                    target
                        .withoutFlavors(ImmutableSet.of(platform.getFlavor()))
                        .getShortNameAndFlavorPostfix())
                .build());
    String extension = platform.getSharedLibraryExtension();
    return String.format("lib%s.%s", libName, extension);
  }

  public static Path getSharedLibraryPath(
      BuildTarget target,
      String soname,
      CxxPlatform platform) {
    return BuildTargets.getGenPath(
        createSharedLibraryBuildTarget(target, platform.getFlavor()),
        "%s/" + soname);
  }

  @VisibleForTesting
  protected static Path getOutputPath(BuildTarget target) {
    return BuildTargets.getGenPath(target, "%s/" + target.getShortNameAndFlavorPostfix());
  }

  @VisibleForTesting
  protected static BuildTarget createCxxLinkTarget(BuildTarget target) {
    return BuildTarget.builder(target).addFlavors(CXX_LINK_BINARY_FLAVOR).build();
  }

  static class CxxLinkAndCompileRules {
    final CxxLink cxxLink;
    final ImmutableSortedSet<CxxPreprocessAndCompile> compileRules;
    CxxLinkAndCompileRules(
        CxxLink cxxLink,
        ImmutableSortedSet<CxxPreprocessAndCompile> compileRules) {
      this.cxxLink = cxxLink;
      this.compileRules = compileRules;
    }
  }

  public static CxxLinkAndCompileRules createBuildRulesForCxxBinaryDescriptionArg(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxPlatform cxxPlatform,
      CxxBinaryDescription.Arg args,
      CxxPreprocessMode preprocessMode) {

    ImmutableMap<String, CxxSource> srcs = parseCxxSources(params, resolver, args);
    ImmutableMap<Path, SourcePath> headers = parseHeaders(params, resolver, args);
    ImmutableMap<String, SourcePath> lexSrcs = parseLexSources(params, resolver, args);
    ImmutableMap<String, SourcePath> yaccSrcs = parseYaccSources(params, resolver, args);

    SourcePathResolver sourcePathResolver = new SourcePathResolver(resolver);

    // Setup the rules to run lex/yacc.
    CxxHeaderSourceSpec lexYaccSources =
        requireLexYaccSources(
            params,
            resolver,
            sourcePathResolver,
            cxxPlatform,
            lexSrcs,
            yaccSrcs);

    // Setup the header symlink tree and combine all the preprocessor input from this rule
    // and all dependencies.
    SymlinkTree headerSymlinkTree = requireHeaderSymlinkTree(
        params,
        resolver,
        sourcePathResolver,
        cxxPlatform,
        /* includeLexYaccHeaders */ true,
        lexSrcs,
        yaccSrcs,
        headers,
        HeaderVisibility.PRIVATE);
    CxxPreprocessorInput cxxPreprocessorInput =
        combineCxxPreprocessorInput(
            params,
            cxxPlatform,
            CxxFlags.getLanguageFlags(
                args.preprocessorFlags,
                args.platformPreprocessorFlags,
                args.langPreprocessorFlags,
                cxxPlatform.getFlavor()),
            args.prefixHeaders.get(),
            ImmutableList.of(headerSymlinkTree),
            args.frameworkSearchPaths.get(),
            CxxPreprocessables.getTransitiveCxxPreprocessorInput(
                cxxPlatform,
                FluentIterable.from(params.getDeps())
                    .filter(Predicates.instanceOf(CxxPreprocessorDep.class))));

    // The complete list of input sources.
    ImmutableMap<String, CxxSource> sources =
        ImmutableMap.<String, CxxSource>builder()
            .putAll(srcs)
            .putAll(lexYaccSources.getCxxSources())
            .build();

    // Generate and add all the build rules to preprocess and compile the source to the
    // resolver and get the `SourcePath`s representing the generated object files.
    ImmutableMap<CxxPreprocessAndCompile, SourcePath> objects =
        CxxSourceRuleFactory.requirePreprocessAndCompileRules(
            params,
            resolver,
            sourcePathResolver,
            cxxPlatform,
            cxxPreprocessorInput,
            CxxFlags.getFlags(
                args.compilerFlags,
                args.platformCompilerFlags,
                cxxPlatform.getFlavor()),
            preprocessMode,
            sources,
            CxxSourceRuleFactory.PicType.PDC);

    // Generate the final link rule.  We use the top-level target as the link rule's
    // target, so that it corresponds to the actual binary we build.
    Path output = getOutputPath(params.getBuildTarget());
    CxxLink cxxLink = CxxLinkableEnhancer.createCxxLinkableBuildRule(
        cxxPlatform,
        params,
        sourcePathResolver,
        /* extraCxxLdFlags */ ImmutableList.<String>of(),
        /* extraLdFlags */ CxxFlags.getFlags(
            args.linkerFlags,
            args.platformLinkerFlags,
            cxxPlatform.getFlavor()),
        createCxxLinkTarget(params.getBuildTarget()),
        Linker.LinkType.EXECUTABLE,
        Optional.<String>absent(),
        output,
        objects.values(),
        (args.linkStyle.or(CxxBinaryDescription.LinkStyle.STATIC) ==
            CxxBinaryDescription.LinkStyle.STATIC)
        ? Linker.LinkableDepType.STATIC
        : Linker.LinkableDepType.SHARED,
        params.getDeps(),
        args.cxxRuntimeType,
        Optional.<SourcePath>absent());
    resolver.addToIndex(cxxLink);

    return new CxxLinkAndCompileRules(cxxLink, ImmutableSortedSet.copyOf(objects.keySet()));
  }

  private static <T> BuildRule createBuildRule(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      TargetNode<T> node,
      Flavor... flavors) {
    BuildTarget target = BuildTarget.builder(params.getBuildTarget()).addFlavors(flavors).build();
    Description<T> description = node.getDescription();
    T args = node.getConstructorArg();
    return description.createBuildRule(
        params.copyWithChanges(
            target,
            Suppliers.ofInstance(params.getDeclaredDeps()),
            Suppliers.ofInstance(params.getExtraDeps())),
        ruleResolver,
        args);
  }

  /**
   * Ensure that the build rule generated by the given {@link BuildRuleParams} had been generated
   * by it's corresponding {@link Description} and added to the {@link BuildRuleResolver}.  If not,
   * call into it's associated {@link Description} to generate it's {@link BuildRule}.
   *
   * @return the {@link BuildRule} generated by the description corresponding to the supplied
   *     {@link BuildRuleParams}.
   */
  public static BuildRule requireBuildRule(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      Flavor... flavors) {
    BuildTarget target = BuildTarget.builder(params.getBuildTarget()).addFlavors(flavors).build();
    Optional<BuildRule> rule = ruleResolver.getRuleOptional(target);
    if (!rule.isPresent()) {
      TargetNode<?> node = params.getTargetGraph().get(params.getBuildTarget());
      Preconditions.checkNotNull(
          node,
          String.format("%s not in target graph", params.getBuildTarget()));
      rule = Optional.of(createBuildRule(params, ruleResolver, node, flavors));
      ruleResolver.addToIndex(rule.get());
    }
    return rule.get();
  }

  /**
   * @return a {@link Function} object which transforms path names from the output of a compiler
   *     or preprocessor using {@code pathProcessor}.
   */
  public static Function<String, String> createErrorMessagePathProcessor(
      final Function<String, String> pathProcessor) {
    return new Function<String, String>() {

      private final ImmutableList<Pattern> patterns =
          ImmutableList.of(
              Pattern.compile(
                  "(?<=^(?:In file included |\\s+)from )" +
                  "(?<path>[^:]+)" +
                  "(?=[:,](?:\\d+[:,](?:\\d+[:,])?)?$)"),
              Pattern.compile(
                  "^(?<path>[^:]+)(?=:(?:\\d+:(?:\\d+:)?)? )"));

      @Override
      public String apply(String line) {
        for (Pattern pattern : patterns) {
          Matcher m = pattern.matcher(line);
          if (m.find()) {
            return m.replaceAll(pathProcessor.apply(m.group("path")));
          }
        }
        return line;
      }

    };
  }

  public static ImmutableList<String> getPlatformFlags(
      ImmutableList<Pair<String, ImmutableList<String>>> platformFlags,
      String platform) {

    ImmutableList.Builder<String> platformFlagsBuilder = ImmutableList.builder();

    for (Pair<String, ImmutableList<String>> pair : platformFlags) {
      Pattern pattern = Pattern.compile(pair.getFirst());
      Matcher matcher = pattern.matcher(platform);
      if (matcher.find()) {
        platformFlagsBuilder.addAll(pair.getSecond());
        break;
      }
    }

    return platformFlagsBuilder.build();
  }
}


File: src/com/facebook/buck/cxx/CxxLibraryDescription.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.FlavorDomain;
import com.facebook.buck.model.FlavorDomainException;
import com.facebook.buck.model.Flavored;
import com.facebook.buck.model.Pair;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRuleType;
import com.facebook.buck.rules.Description;
import com.facebook.buck.rules.ImplicitDepsInferringDescription;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SymlinkTree;
import com.facebook.buck.rules.coercer.Either;
import com.facebook.buck.rules.coercer.SourceWithFlags;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.buck.util.MoreIterables;
import com.facebook.infer.annotation.SuppressFieldNotInitialized;
import com.google.common.base.Function;
import com.google.common.base.Functions;
import com.google.common.base.Optional;
import com.google.common.base.Suppliers;
import com.google.common.collect.ImmutableCollection;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;

import java.nio.file.Path;
import java.util.Map;
import java.util.Set;

public class CxxLibraryDescription implements
    Description<CxxLibraryDescription.Arg>,
    ImplicitDepsInferringDescription<CxxLibraryDescription.Arg>,
    Flavored {

  public enum Type {
    HEADERS,
    EXPORTED_HEADERS,
    SHARED,
    STATIC_PIC,
    STATIC,
    MACH_O_BUNDLE,
  }

  public static final BuildRuleType TYPE = BuildRuleType.of("cxx_library");

  private static final FlavorDomain<Type> LIBRARY_TYPE =
      new FlavorDomain<>(
          "C/C++ Library Type",
          ImmutableMap.<Flavor, Type>builder()
              .put(CxxDescriptionEnhancer.HEADER_SYMLINK_TREE_FLAVOR, Type.HEADERS)
              .put(
                  CxxDescriptionEnhancer.EXPORTED_HEADER_SYMLINK_TREE_FLAVOR,
                  Type.EXPORTED_HEADERS)
              .put(CxxDescriptionEnhancer.SHARED_FLAVOR, Type.SHARED)
              .put(CxxDescriptionEnhancer.STATIC_PIC_FLAVOR, Type.STATIC_PIC)
              .put(CxxDescriptionEnhancer.STATIC_FLAVOR, Type.STATIC)
              .put(CxxDescriptionEnhancer.MACH_O_BUNDLE_FLAVOR, Type.MACH_O_BUNDLE)
              .build());

  private final CxxBuckConfig cxxBuckConfig;
  private final FlavorDomain<CxxPlatform> cxxPlatforms;
  private final CxxPreprocessMode preprocessMode;

  public CxxLibraryDescription(
      CxxBuckConfig cxxBuckConfig,
      FlavorDomain<CxxPlatform> cxxPlatforms,
      CxxPreprocessMode preprocessMode) {
    this.cxxBuckConfig = cxxBuckConfig;
    this.cxxPlatforms = cxxPlatforms;
    this.preprocessMode = preprocessMode;
  }

  @Override
  public boolean hasFlavors(ImmutableSet<Flavor> flavors) {
    return cxxPlatforms.containsAnyOf(flavors) ||
        flavors.contains(CxxCompilationDatabase.COMPILATION_DATABASE);
  }

  private static ImmutableCollection<CxxPreprocessorInput> getTransitiveCxxPreprocessorInput(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      ImmutableMultimap<CxxSource.Type, String> exportedPreprocessorFlags,
      ImmutableMap<Path, SourcePath> exportedHeaders,
      ImmutableList<Path> frameworkSearchPaths) {

    // Check if there is a target node representative for the library in the action graph and,
    // if so, grab the cached transitive C/C++ preprocessor input from that.  We===
    BuildTarget rawTarget =
        params.getBuildTarget()
            .withoutFlavors(
                ImmutableSet.<Flavor>builder()
                    .addAll(LIBRARY_TYPE.getFlavors())
                    .add(cxxPlatform.getFlavor())
                    .build());
    Optional<BuildRule> rawRule = ruleResolver.getRuleOptional(rawTarget);
    if (rawRule.isPresent()) {
      CxxLibrary rule = (CxxLibrary) rawRule.get();
      return rule.getTransitiveCxxPreprocessorInput(cxxPlatform, HeaderVisibility.PUBLIC).values();
    }

    // Otherwise, construct it ourselves.
    SymlinkTree symlinkTree =
        CxxDescriptionEnhancer.requireHeaderSymlinkTree(
            params,
            ruleResolver,
            pathResolver,
            cxxPlatform,
            /* includeLexYaccHeaders */ false,
            ImmutableMap.<String, SourcePath>of(),
            ImmutableMap.<String, SourcePath>of(),
            exportedHeaders,
            HeaderVisibility.PUBLIC);
    Map<BuildTarget, CxxPreprocessorInput> input = Maps.newLinkedHashMap();
    input.put(
        params.getBuildTarget(),
        CxxPreprocessorInput.builder()
            .addRules(symlinkTree.getBuildTarget())
            .putAllPreprocessorFlags(exportedPreprocessorFlags)
            .setIncludes(
                CxxHeaders.builder()
                    .putAllNameToPathMap(symlinkTree.getLinks())
                    .putAllFullNameToPathMap(symlinkTree.getFullLinks())
                    .build())
            .addIncludeRoots(symlinkTree.getRoot())
            .addAllFrameworkRoots(frameworkSearchPaths)
            .build());
    for (BuildRule rule : params.getDeps()) {
      if (rule instanceof CxxPreprocessorDep) {
        input.putAll(
            ((CxxPreprocessorDep) rule).getTransitiveCxxPreprocessorInput(
                cxxPlatform,
                HeaderVisibility.PUBLIC));
      }
    }
    return ImmutableList.copyOf(input.values());
  }

  private static ImmutableMap<CxxPreprocessAndCompile, SourcePath> requireObjects(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      ImmutableMap<String, SourcePath> lexSources,
      ImmutableMap<String, SourcePath> yaccSources,
      ImmutableMultimap<CxxSource.Type, String> preprocessorFlags,
      ImmutableMultimap<CxxSource.Type, String> exportedPreprocessorFlags,
      ImmutableList<SourcePath> prefixHeaders,
      ImmutableMap<Path, SourcePath> headers,
      ImmutableMap<Path, SourcePath> exportedHeaders,
      ImmutableList<String> compilerFlags,
      ImmutableMap<String, CxxSource> sources,
      ImmutableList<Path> frameworkSearchPaths,
      CxxPreprocessMode preprocessMode,
      CxxSourceRuleFactory.PicType pic) {

    CxxHeaderSourceSpec lexYaccSources =
        CxxDescriptionEnhancer.requireLexYaccSources(
            params,
            ruleResolver,
            pathResolver,
            cxxPlatform,
            lexSources,
            yaccSources);

    SymlinkTree headerSymlinkTree =
        CxxDescriptionEnhancer.requireHeaderSymlinkTree(
            params,
            ruleResolver,
            pathResolver,
            cxxPlatform,
            /* includeLexYaccHeaders */ true,
            lexSources,
            yaccSources,
            headers,
            HeaderVisibility.PRIVATE);

    CxxPreprocessorInput cxxPreprocessorInputFromDependencies =
        CxxDescriptionEnhancer.combineCxxPreprocessorInput(
            params,
            cxxPlatform,
            preprocessorFlags,
            prefixHeaders,
            ImmutableList.of(headerSymlinkTree),
            ImmutableList.<Path>of(),
            getTransitiveCxxPreprocessorInput(
                params,
                ruleResolver,
                pathResolver,
                cxxPlatform,
                exportedPreprocessorFlags,
                exportedHeaders,
                frameworkSearchPaths));

    ImmutableMap<String, CxxSource> allSources =
        ImmutableMap.<String, CxxSource>builder()
            .putAll(sources)
            .putAll(lexYaccSources.getCxxSources())
            .build();

    // Create rule to build the object files.
    return CxxSourceRuleFactory.requirePreprocessAndCompileRules(
        params,
        ruleResolver,
        pathResolver,
        cxxPlatform,
        cxxPreprocessorInputFromDependencies,
        compilerFlags,
        preprocessMode,
        allSources,
        pic);
  }

  /**
   * Create all build rules needed to generate the static library.
   *
   * @return the {@link Archive} rule representing the actual static library.
   */
  private static BuildRule createStaticLibrary(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      ImmutableMap<String, SourcePath> lexSources,
      ImmutableMap<String, SourcePath> yaccSources,
      ImmutableMultimap<CxxSource.Type, String> preprocessorFlags,
      ImmutableMultimap<CxxSource.Type, String> exportedPreprocessorFlags,
      ImmutableList<SourcePath> prefixHeaders,
      ImmutableMap<Path, SourcePath> headers,
      ImmutableMap<Path, SourcePath> exportedHeaders,
      ImmutableList<String> compilerFlags,
      ImmutableMap<String, CxxSource> sources,
      ImmutableList<Path> frameworkSearchPaths,
      CxxPreprocessMode preprocessMode,
      CxxSourceRuleFactory.PicType pic) {

    // Create rules for compiling the non-PIC object files.
    ImmutableMap<CxxPreprocessAndCompile, SourcePath> objects = requireObjects(
        params,
        ruleResolver,
        pathResolver,
        cxxPlatform,
        lexSources,
        yaccSources,
        preprocessorFlags,
        exportedPreprocessorFlags,
        prefixHeaders,
        headers,
        exportedHeaders,
        compilerFlags,
        sources,
        frameworkSearchPaths,
        preprocessMode,
        pic);

    // Write a build rule to create the archive for this C/C++ library.
    BuildTarget staticTarget =
        CxxDescriptionEnhancer.createStaticLibraryBuildTarget(
            params.getBuildTarget(),
            cxxPlatform.getFlavor(),
            pic);
    Path staticLibraryPath =
        CxxDescriptionEnhancer.getStaticLibraryPath(
            params.getBuildTarget(),
            cxxPlatform.getFlavor(),
            pic);
    return Archives.createArchiveRule(
        pathResolver,
        staticTarget,
        params,
        cxxPlatform.getAr(),
        cxxPlatform.getArExpectedGlobalHeader(),
        staticLibraryPath,
        ImmutableList.copyOf(objects.values()));
  }

  /**
   * Create all build rules needed to generate the shared library.
   *
   * @return the {@link CxxLink} rule representing the actual shared library.
   */
  private static BuildRule createSharedLibrary(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      ImmutableMap<String, SourcePath> lexSources,
      ImmutableMap<String, SourcePath> yaccSources,
      ImmutableMultimap<CxxSource.Type, String> preprocessorFlags,
      ImmutableMultimap<CxxSource.Type, String> exportedPreprocessorFlags,
      ImmutableList<SourcePath> prefixHeaders,
      ImmutableMap<Path, SourcePath> headers,
      ImmutableMap<Path, SourcePath> exportedHeaders,
      ImmutableList<String> compilerFlags,
      ImmutableMap<String, CxxSource> sources,
      ImmutableList<String> linkerFlags,
      ImmutableList<Path> frameworkSearchPaths,
      Optional<String> soname,
      CxxPreprocessMode preprocessMode,
      Optional<Linker.CxxRuntimeType> cxxRuntimeType,
      Linker.LinkType linkType,
      Linker.LinkableDepType linkableDepType,
      Optional<SourcePath> bundleLoader) {

    // Create rules for compiling the PIC object files.
    ImmutableMap<CxxPreprocessAndCompile, SourcePath> objects = requireObjects(
        params,
        ruleResolver,
        pathResolver,
        cxxPlatform,
        lexSources,
        yaccSources,
        preprocessorFlags,
        exportedPreprocessorFlags,
        prefixHeaders,
        headers,
        exportedHeaders,
        compilerFlags,
        sources,
        frameworkSearchPaths,
        preprocessMode,
        CxxSourceRuleFactory.PicType.PIC);

    // Setup the rules to link the shared library.
    BuildTarget sharedTarget =
        CxxDescriptionEnhancer.createSharedLibraryBuildTarget(
            params.getBuildTarget(),
            cxxPlatform.getFlavor());
    String sharedLibrarySoname =
        soname.or(
            CxxDescriptionEnhancer.getDefaultSharedLibrarySoname(
                params.getBuildTarget(), cxxPlatform));
    Path sharedLibraryPath = CxxDescriptionEnhancer.getSharedLibraryPath(
        params.getBuildTarget(),
        sharedLibrarySoname,
        cxxPlatform);
    ImmutableList.Builder<String> extraCxxLdFlagsBuilder = ImmutableList.builder();
    extraCxxLdFlagsBuilder.addAll(
        MoreIterables.zipAndConcat(
            Iterables.cycle("-F"),
            Iterables.transform(frameworkSearchPaths, Functions.toStringFunction())));
    ImmutableList<String> extraCxxLdFlags = extraCxxLdFlagsBuilder.build();

    return CxxLinkableEnhancer.createCxxLinkableBuildRule(
            cxxPlatform,
            params,
            pathResolver,
            extraCxxLdFlags,
            linkerFlags,
            sharedTarget,
            linkType,
            Optional.of(sharedLibrarySoname),
            sharedLibraryPath,
            objects.values(),
            linkableDepType,
            params.getDeps(),
            cxxRuntimeType,
            bundleLoader);
  }

  /**
   * Create all build rules needed to generate the compilation database.
   *
   * @return the {@link CxxCompilationDatabase} rule representing the actual compilation database.
   */
  private static CxxCompilationDatabase createCompilationDatabase(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      ImmutableMap<String, SourcePath> lexSources,
      ImmutableMap<String, SourcePath> yaccSources,
      ImmutableMultimap<CxxSource.Type, String> preprocessorFlags,
      ImmutableMultimap<CxxSource.Type, String> exportedPreprocessorFlags,
      ImmutableList<SourcePath> prefixHeaders,
      ImmutableMap<Path, SourcePath> headers,
      ImmutableMap<Path, SourcePath> exportedHeaders,
      ImmutableList<String> compilerFlags,
      ImmutableMap<String, CxxSource> sources,
      ImmutableList<Path> frameworkSearchPaths,
      CxxPreprocessMode preprocessMode) {
    BuildRuleParams paramsWithoutCompilationDatabaseFlavor = CxxCompilationDatabase
        .paramsWithoutCompilationDatabaseFlavor(params);
    // Invoking requireObjects has the side-effect of invoking
    // CxxSourceRuleFactory.requirePreprocessAndCompileRules(), which has the side-effect of
    // creating CxxPreprocessAndCompile rules and adding them to the ruleResolver.
    ImmutableMap<CxxPreprocessAndCompile, SourcePath> objects = requireObjects(
        paramsWithoutCompilationDatabaseFlavor,
        ruleResolver,
        pathResolver,
        cxxPlatform,
        lexSources,
        yaccSources,
        preprocessorFlags,
        exportedPreprocessorFlags,
        prefixHeaders,
        headers,
        exportedHeaders,
        compilerFlags,
        sources,
        frameworkSearchPaths,
        preprocessMode,
        CxxSourceRuleFactory.PicType.PIC);

    return CxxCompilationDatabase.createCompilationDatabase(
        params,
        pathResolver,
        preprocessMode,
        objects.keySet());
  }

  @Override
  public Arg createUnpopulatedConstructorArg() {
    return new Arg();
  }

  public static Arg createEmptyConstructorArg() {
    Arg arg = new Arg();
    arg.deps = Optional.of(ImmutableSortedSet.<BuildTarget>of());
    arg.srcs = Optional.of(
        Either.<ImmutableList<SourceWithFlags>, ImmutableMap<String, SourceWithFlags>>ofLeft(
            ImmutableList.<SourceWithFlags>of()));
    arg.prefixHeaders = Optional.of(ImmutableList.<SourcePath>of());
    arg.headers = Optional.of(
        Either.<ImmutableList<SourcePath>, ImmutableMap<String, SourcePath>>ofLeft(
            ImmutableList.<SourcePath>of()));
    arg.exportedHeaders = Optional.of(
        Either.<ImmutableList<SourcePath>, ImmutableMap<String, SourcePath>>ofLeft(
            ImmutableList.<SourcePath>of()));
    arg.compilerFlags = Optional.of(ImmutableList.<String>of());
    arg.platformCompilerFlags =
        Optional.of(ImmutableList.<Pair<String, ImmutableList<String>>>of());
    arg.exportedPreprocessorFlags = Optional.of(ImmutableList.<String>of());
    arg.exportedPlatformPreprocessorFlags =
        Optional.of(ImmutableList.<Pair<String, ImmutableList<String>>>of());
    arg.exportedLangPreprocessorFlags = Optional.of(
        ImmutableMap.<CxxSource.Type, ImmutableList<String>>of());
    arg.preprocessorFlags = Optional.of(ImmutableList.<String>of());
    arg.platformPreprocessorFlags =
        Optional.of(ImmutableList.<Pair<String, ImmutableList<String>>>of());
    arg.langPreprocessorFlags = Optional.of(
        ImmutableMap.<CxxSource.Type, ImmutableList<String>>of());
    arg.linkerFlags = Optional.of(ImmutableList.<String>of());
    arg.exportedLinkerFlags = Optional.of(ImmutableList.<String>of());
    arg.platformLinkerFlags = Optional.of(ImmutableList.<Pair<String, ImmutableList<String>>>of());
    arg.exportedPlatformLinkerFlags = Optional.of(
        ImmutableList.<Pair<String, ImmutableList<String>>>of());
    arg.cxxRuntimeType = Optional.absent();
    arg.forceStatic = Optional.absent();
    arg.linkWhole = Optional.absent();
    arg.lexSrcs = Optional.of(ImmutableList.<SourcePath>of());
    arg.yaccSrcs = Optional.of(ImmutableList.<SourcePath>of());
    arg.headerNamespace = Optional.absent();
    arg.soname = Optional.absent();
    arg.frameworkSearchPaths = Optional.of(ImmutableList.<Path>of());
    arg.tests = Optional.of(ImmutableSortedSet.<BuildTarget>of());
    arg.supportedPlatformsRegex = Optional.absent();
    return arg;
  }

  /**
   * @return a {@link SymlinkTree} for the headers of this C/C++ library.
   */
  public static <A extends Arg> SymlinkTree createHeaderSymlinkTreeBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxPlatform cxxPlatform,
      A args) {
    return CxxDescriptionEnhancer.createHeaderSymlinkTree(
        params,
        resolver,
        new SourcePathResolver(resolver),
        cxxPlatform,
        /* includeLexYaccHeaders */ true,
        CxxDescriptionEnhancer.parseLexSources(params, resolver, args),
        CxxDescriptionEnhancer.parseYaccSources(params, resolver, args),
        CxxDescriptionEnhancer.parseHeaders(params, resolver, args),
        HeaderVisibility.PRIVATE);
  }

  /**
   * @return a {@link SymlinkTree} for the exported headers of this C/C++ library.
   */
  public static <A extends Arg> SymlinkTree createExportedHeaderSymlinkTreeBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxPlatform cxxPlatform,
      A args) {
    return CxxDescriptionEnhancer.createHeaderSymlinkTree(
        params,
        resolver,
        new SourcePathResolver(resolver),
        cxxPlatform,
        /* includeLexYaccHeaders */ false,
        ImmutableMap.<String, SourcePath>of(),
        ImmutableMap.<String, SourcePath>of(),
        CxxDescriptionEnhancer.parseExportedHeaders(params, resolver, args),
        HeaderVisibility.PUBLIC);
  }

  /**
   * @return a {@link Archive} rule which builds a static library version of this C/C++ library.
   */
  public static <A extends Arg> BuildRule createStaticLibraryBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxPlatform cxxPlatform,
      A args,
      CxxPreprocessMode preprocessMode,
      CxxSourceRuleFactory.PicType pic) {
    return createStaticLibrary(
        params,
        resolver,
        new SourcePathResolver(resolver),
        cxxPlatform,
        CxxDescriptionEnhancer.parseLexSources(params, resolver, args),
        CxxDescriptionEnhancer.parseYaccSources(params, resolver, args),
        CxxFlags.getLanguageFlags(
            args.preprocessorFlags,
            args.platformPreprocessorFlags,
            args.langPreprocessorFlags,
            cxxPlatform.getFlavor()),
        CxxFlags.getLanguageFlags(
            args.exportedPreprocessorFlags,
            args.exportedPlatformPreprocessorFlags,
            args.exportedLangPreprocessorFlags,
            cxxPlatform.getFlavor()),
        args.prefixHeaders.get(),
        CxxDescriptionEnhancer.parseHeaders(params, resolver, args),
        CxxDescriptionEnhancer.parseExportedHeaders(params, resolver, args),
        CxxFlags.getFlags(
            args.compilerFlags,
            args.platformCompilerFlags,
            cxxPlatform.getFlavor()),
        CxxDescriptionEnhancer.parseCxxSources(params, resolver, args),
        args.frameworkSearchPaths.get(),
        preprocessMode,
        pic);
  }

  /**
   * @return a {@link CxxLink} rule which builds a shared library version of this C/C++ library.
   */
  public static <A extends Arg> BuildRule createSharedLibraryBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxPlatform cxxPlatform,
      A args,
      CxxPreprocessMode preprocessMode,
      Linker.LinkType linkType,
      Linker.LinkableDepType linkableDepType,
      Optional<SourcePath> bundleLoader) {
    ImmutableList.Builder<String> linkerFlags = ImmutableList.builder();

    linkerFlags.addAll(
        CxxFlags.getFlags(
            args.linkerFlags,
            args.platformLinkerFlags,
            cxxPlatform.getFlavor()));

    linkerFlags.addAll(
        CxxFlags.getFlags(
            args.exportedLinkerFlags,
            args.exportedPlatformLinkerFlags,
            cxxPlatform.getFlavor()));

    return createSharedLibrary(
        params,
        resolver,
        new SourcePathResolver(resolver),
        cxxPlatform,
        CxxDescriptionEnhancer.parseLexSources(params, resolver, args),
        CxxDescriptionEnhancer.parseYaccSources(params, resolver, args),
        CxxFlags.getLanguageFlags(
            args.preprocessorFlags,
            args.platformPreprocessorFlags,
            args.langPreprocessorFlags,
            cxxPlatform.getFlavor()),
        CxxFlags.getLanguageFlags(
            args.exportedPreprocessorFlags,
            args.exportedPlatformPreprocessorFlags,
            args.exportedLangPreprocessorFlags,
            cxxPlatform.getFlavor()),
        args.prefixHeaders.get(),
        CxxDescriptionEnhancer.parseHeaders(params, resolver, args),
        CxxDescriptionEnhancer.parseExportedHeaders(params, resolver, args),
        CxxFlags.getFlags(
            args.compilerFlags,
            args.platformCompilerFlags,
            cxxPlatform.getFlavor()),
        CxxDescriptionEnhancer.parseCxxSources(params, resolver, args),
        linkerFlags.build(),
        args.frameworkSearchPaths.get(),
        args.soname,
        preprocessMode,
        args.cxxRuntimeType,
        linkType,
        linkableDepType,
        bundleLoader);
  }

  /**
   * @return a {@link CxxCompilationDatabase} rule which builds a compilation database for this
   * C/C++ library.
   */
  public static <A extends Arg> CxxCompilationDatabase createCompilationDatabaseBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      CxxPlatform cxxPlatform,
      A args,
      CxxPreprocessMode preprocessMode) {
    return createCompilationDatabase(
        params,
        resolver,
        new SourcePathResolver(resolver),
        cxxPlatform,
        CxxDescriptionEnhancer.parseLexSources(params, resolver, args),
        CxxDescriptionEnhancer.parseYaccSources(params, resolver, args),
        CxxFlags.getLanguageFlags(
            args.preprocessorFlags,
            args.platformPreprocessorFlags,
            args.langPreprocessorFlags,
            cxxPlatform.getFlavor()),
        CxxFlags.getLanguageFlags(
            args.exportedPreprocessorFlags,
            args.exportedPlatformPreprocessorFlags,
            args.exportedLangPreprocessorFlags,
            cxxPlatform.getFlavor()),
        args.prefixHeaders.get(),
        CxxDescriptionEnhancer.parseHeaders(params, resolver, args),
        CxxDescriptionEnhancer.parseExportedHeaders(params, resolver, args),
        CxxFlags.getFlags(
            args.compilerFlags,
            args.platformCompilerFlags,
            cxxPlatform.getFlavor()),
        CxxDescriptionEnhancer.parseCxxSources(params, resolver, args),
        args.frameworkSearchPaths.get(),
        preprocessMode);
  }

  public static TypeAndPlatform getTypeAndPlatform(
      BuildTarget buildTarget,
      FlavorDomain<CxxPlatform> platforms) {
    // See if we're building a particular "type" and "platform" of this library, and if so, extract
    // them from the flavors attached to the build target.
    Optional<Map.Entry<Flavor, Type>> type;
    Optional<Map.Entry<Flavor, CxxPlatform>> platform;
    try {
      type = LIBRARY_TYPE.getFlavorAndValue(
          ImmutableSet.copyOf(buildTarget.getFlavors()));
      platform = platforms.getFlavorAndValue(
          ImmutableSet.copyOf(buildTarget.getFlavors()));
    } catch (FlavorDomainException e) {
      throw new HumanReadableException("%s: %s", buildTarget, e.getMessage());
    }
    return TypeAndPlatform.of(type, platform);
  }

  @Override
  public <A extends Arg> BuildRule createBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      A args) {
    TypeAndPlatform typeAndPlatform = getTypeAndPlatform(
        params.getBuildTarget(),
        cxxPlatforms);
    return createBuildRule(
        params,
        resolver,
        args,
        typeAndPlatform,
        Optional.<Linker.LinkableDepType>absent(),
        Optional.<SourcePath>absent());
  }

  public <A extends Arg> BuildRule createBuildRule(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      final A args,
      TypeAndPlatform typeAndPlatform,
      Optional<Linker.LinkableDepType> linkableDepType,
      Optional<SourcePath> bundleLoader) {
    Optional<Map.Entry<Flavor, CxxPlatform>> platform = typeAndPlatform.getPlatform();

    if (params.getBuildTarget().getFlavors()
        .contains(CxxCompilationDatabase.COMPILATION_DATABASE)) {
      // XXX: This needs bundleLoader for tests..
      return createCompilationDatabaseBuildRule(
          params,
          resolver,
          platform.isPresent()
              ? platform.get().getValue()
              : DefaultCxxPlatforms.build(cxxBuckConfig),
          args,
          preprocessMode);
    }


    Optional<Map.Entry<Flavor, Type>> type = typeAndPlatform.getType();

    // If we *are* building a specific type of this lib, call into the type specific
    // rule builder methods.
    if (type.isPresent() && platform.isPresent()) {
      Set<Flavor> flavors = Sets.newHashSet(params.getBuildTarget().getFlavors());
      flavors.remove(type.get().getKey());
      BuildTarget target = BuildTarget
          .builder(params.getBuildTarget().getUnflavoredBuildTarget())
          .addAllFlavors(flavors)
          .build();
      BuildRuleParams typeParams =
          params.copyWithChanges(
              target,
              Suppliers.ofInstance(params.getDeclaredDeps()),
              Suppliers.ofInstance(params.getExtraDeps()));
      if (type.get().getValue().equals(Type.HEADERS)) {
        return createHeaderSymlinkTreeBuildRule(
            typeParams,
            resolver,
            platform.get().getValue(),
            args);
      } else if (type.get().getValue().equals(Type.EXPORTED_HEADERS)) {
          return createExportedHeaderSymlinkTreeBuildRule(
              typeParams,
              resolver,
              platform.get().getValue(),
              args);
      } else if (type.get().getValue().equals(Type.SHARED)) {
        return createSharedLibraryBuildRule(
            typeParams,
            resolver,
            platform.get().getValue(),
            args,
            preprocessMode,
            Linker.LinkType.SHARED,
            linkableDepType.or(Linker.LinkableDepType.SHARED),
            Optional.<SourcePath>absent());
      } else if (type.get().getValue().equals(Type.MACH_O_BUNDLE)) {
        return createSharedLibraryBuildRule(
            typeParams,
            resolver,
            platform.get().getValue(),
            args,
            preprocessMode,
            Linker.LinkType.MACH_O_BUNDLE,
            linkableDepType.or(Linker.LinkableDepType.SHARED),
            bundleLoader);
      } else if (type.get().getValue().equals(Type.STATIC)) {
        return createStaticLibraryBuildRule(
            typeParams,
            resolver,
            platform.get().getValue(),
            args,
            preprocessMode,
            CxxSourceRuleFactory.PicType.PDC);
      } else {
        return createStaticLibraryBuildRule(
            typeParams,
            resolver,
            platform.get().getValue(),
            args,
            preprocessMode,
            CxxSourceRuleFactory.PicType.PIC);
      }
    }

    // I'm not proud of this.
    boolean hasObjects = false;
    if (args.srcs.isPresent()) {
      Either<ImmutableList<SourceWithFlags>, ImmutableMap<String, SourceWithFlags>> either =
          args.srcs.get();
      if (either.isLeft()) {
        hasObjects = !either.getLeft().isEmpty();
      } else {
        hasObjects = !either.getRight().isEmpty();
      }
    }
    hasObjects |=
          !args.lexSrcs.get().isEmpty() ||
          !args.yaccSrcs.get().isEmpty();

    // Otherwise, we return the generic placeholder of this library, that dependents can use
    // get the real build rules via querying the action graph.
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);
    return new CxxLibrary(
        params,
        resolver,
        pathResolver,
        !hasObjects,
        new Function<CxxPlatform, ImmutableMultimap<CxxSource.Type, String>>() {
          @Override
          public ImmutableMultimap<CxxSource.Type, String> apply(CxxPlatform input) {
            return CxxFlags.getLanguageFlags(
                args.exportedPreprocessorFlags,
                args.exportedPlatformPreprocessorFlags,
                args.exportedLangPreprocessorFlags,
                input.getFlavor());
          }
        },
        new Function<CxxPlatform, ImmutableList<String>>() {
          @Override
          public ImmutableList<String> apply(CxxPlatform input) {
            return CxxFlags.getFlags(
                args.exportedLinkerFlags,
                args.exportedPlatformLinkerFlags,
                input.getFlavor());
          }
        },
        args.supportedPlatformsRegex,
        args.frameworkSearchPaths.get(),
        args.forceStatic.or(false) ? CxxLibrary.Linkage.STATIC : CxxLibrary.Linkage.ANY,
        args.linkWhole.or(false),
        args.soname,
        args.tests.get());
  }

  @Override
  public BuildRuleType getBuildRuleType() {
    return TYPE;
  }

  @Override
  public Iterable<BuildTarget> findDepsForTargetFromConstructorArgs(
      BuildTarget buildTarget,
      Arg constructorArg) {
    ImmutableSet.Builder<BuildTarget> deps = ImmutableSet.builder();

    if (constructorArg.lexSrcs.isPresent() && !constructorArg.lexSrcs.get().isEmpty()) {
      deps.add(cxxBuckConfig.getLexDep());
    }

    return deps.build();
  }

  @SuppressFieldNotInitialized
  public static class Arg extends CxxConstructorArg {
    public Optional<Either<ImmutableList<SourcePath>, ImmutableMap<String, SourcePath>>>
        exportedHeaders;
    public Optional<ImmutableList<String>> exportedPreprocessorFlags;
    public Optional<ImmutableList<Pair<String, ImmutableList<String>>>>
        exportedPlatformPreprocessorFlags;
    public Optional<ImmutableMap<CxxSource.Type, ImmutableList<String>>>
        exportedLangPreprocessorFlags;
    public Optional<ImmutableList<String>> exportedLinkerFlags;
    public Optional<ImmutableList<Pair<String, ImmutableList<String>>>>
        exportedPlatformLinkerFlags;
    public Optional<String> supportedPlatformsRegex;
    public Optional<String> soname;
    public Optional<Boolean> forceStatic;
    public Optional<Boolean> linkWhole;
  }

}


File: src/com/facebook/buck/cxx/CxxPreprocessAndCompile.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.rules.AbstractBuildRule;
import com.facebook.buck.rules.AddToRuleKey;
import com.facebook.buck.rules.BuildContext;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildableContext;
import com.facebook.buck.rules.RuleKey;
import com.facebook.buck.rules.RuleKeyAppendable;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.step.Step;
import com.facebook.buck.step.fs.MkdirStep;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.buck.util.MoreIterables;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Functions;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Iterables;

import java.nio.file.Path;
import java.util.Map;

/**
 * A build rule which preprocesses and/or compiles a C/C++ source in a single step.
 */
public class CxxPreprocessAndCompile extends AbstractBuildRule implements RuleKeyAppendable {

  @AddToRuleKey
  private final CxxPreprocessAndCompileStep.Operation operation;
  @AddToRuleKey
  private final Optional<Tool> preprocessor;
  private final Optional<ImmutableList<String>> preprocessorFlags;
  @AddToRuleKey
  private final Optional<Tool> compiler;
  private final Optional<ImmutableList<String>> compilerFlags;
  @AddToRuleKey(stringify = true)
  private final Path output;
  @AddToRuleKey
  private final SourcePath input;
  private final CxxSource.Type inputType;
  private final ImmutableList<Path> includeRoots;
  private final ImmutableList<Path> systemIncludeRoots;
  private final ImmutableList<Path> frameworkRoots;
  @AddToRuleKey
  private final CxxHeaders includes;
  private final DebugPathSanitizer sanitizer;

  @VisibleForTesting
  CxxPreprocessAndCompile(
      BuildRuleParams params,
      SourcePathResolver resolver,
      CxxPreprocessAndCompileStep.Operation operation,
      Optional<Tool> preprocessor,
      Optional<ImmutableList<String>> preprocessorFlags,
      Optional<Tool> compiler,
      Optional<ImmutableList<String>> compilerFlags,
      Path output,
      SourcePath input,
      CxxSource.Type inputType,
      ImmutableList<Path> includeRoots,
      ImmutableList<Path> systemIncludeRoots,
      ImmutableList<Path> frameworkRoots,
      CxxHeaders includes,
      DebugPathSanitizer sanitizer) {
    super(params, resolver);
    Preconditions.checkState(operation.isPreprocess() == preprocessor.isPresent());
    Preconditions.checkState(operation.isPreprocess() == preprocessorFlags.isPresent());
    Preconditions.checkState(operation.isCompile() == compiler.isPresent());
    Preconditions.checkState(operation.isCompile() == compilerFlags.isPresent());
    this.operation = operation;
    this.preprocessor = preprocessor;
    this.preprocessorFlags = preprocessorFlags;
    this.compiler = compiler;
    this.compilerFlags = compilerFlags;
    this.output = output;
    this.input = input;
    this.inputType = inputType;
    this.includeRoots = includeRoots;
    this.systemIncludeRoots = systemIncludeRoots;
    this.frameworkRoots = frameworkRoots;
    this.includes = includes;
    this.sanitizer = sanitizer;
  }

  /**
   * @return a {@link CxxPreprocessAndCompile} step that compiles the given preprocessed source.
   */
  public static CxxPreprocessAndCompile compile(
      BuildRuleParams params,
      SourcePathResolver resolver,
      Tool compiler,
      ImmutableList<String> flags,
      Path output,
      SourcePath input,
      CxxSource.Type inputType,
      DebugPathSanitizer sanitizer) {
    return new CxxPreprocessAndCompile(
        params,
        resolver,
        CxxPreprocessAndCompileStep.Operation.COMPILE,
        Optional.<Tool>absent(),
        Optional.<ImmutableList<String>>absent(),
        Optional.of(compiler),
        Optional.of(flags),
        output,
        input,
        inputType,
        ImmutableList.<Path>of(),
        ImmutableList.<Path>of(),
        ImmutableList.<Path>of(),
        CxxHeaders.builder().build(),
        sanitizer);
  }

  /**
   * @return a {@link CxxPreprocessAndCompile} step that preprocesses the given source.
   */
  public static CxxPreprocessAndCompile preprocess(
      BuildRuleParams params,
      SourcePathResolver resolver,
      Tool preprocessor,
      ImmutableList<String> flags,
      Path output,
      SourcePath input,
      CxxSource.Type inputType,
      ImmutableList<Path> includeRoots,
      ImmutableList<Path> systemIncludeRoots,
      ImmutableList<Path> frameworkRoots,
      CxxHeaders includes,
      DebugPathSanitizer sanitizer) {
    return new CxxPreprocessAndCompile(
        params,
        resolver,
        CxxPreprocessAndCompileStep.Operation.PREPROCESS,
        Optional.of(preprocessor),
        Optional.of(flags),
        Optional.<Tool>absent(),
        Optional.<ImmutableList<String>>absent(),
        output,
        input,
        inputType,
        includeRoots,
        systemIncludeRoots,
        frameworkRoots,
        includes,
        sanitizer);
  }

  /**
   * @return a {@link CxxPreprocessAndCompile} step that preprocesses and compiles the given source.
   */
  public static CxxPreprocessAndCompile preprocessAndCompile(
      BuildRuleParams params,
      SourcePathResolver resolver,
      Tool preprocessor,
      ImmutableList<String> preprocessorFlags,
      Tool compiler,
      ImmutableList<String> compilerFlags,
      Path output,
      SourcePath input,
      CxxSource.Type inputType,
      ImmutableList<Path> includeRoots,
      ImmutableList<Path> systemIncludeRoots,
      ImmutableList<Path> frameworkRoots,
      CxxHeaders includes,
      DebugPathSanitizer sanitizer,
      CxxPreprocessMode strategy) {
    return new CxxPreprocessAndCompile(
        params,
        resolver,
        (strategy == CxxPreprocessMode.PIPED
            ? CxxPreprocessAndCompileStep.Operation.PIPED_PREPROCESS_AND_COMPILE
            : CxxPreprocessAndCompileStep.Operation.COMPILE_MUNGE_DEBUGINFO),
        Optional.of(preprocessor),
        Optional.of(preprocessorFlags),
        Optional.of(compiler),
        Optional.of(compilerFlags),
        output,
        input,
        inputType,
        includeRoots,
        systemIncludeRoots,
        frameworkRoots,
        includes,
        (strategy == CxxPreprocessMode.COMBINED
            ? sanitizer
            : sanitizer.changePathSize(0)));
  }

  @Override
  public RuleKey.Builder appendToRuleKey(RuleKey.Builder builder) {
    // Sanitize any relevant paths in the flags we pass to the preprocessor, to prevent them
    // from contributing to the rule key.
    ImmutableList<String> flags = ImmutableList.<String>builder()
        .addAll(this.preprocessorFlags.or(ImmutableList.<String>of()))
        .addAll(this.compilerFlags.or(ImmutableList.<String>of()))
        .build();
    flags = FluentIterable.from(flags)
        .transform(sanitizer.sanitize(Optional.<Path>absent(), /* expandPaths */ false))
        .toList();
    builder.setReflectively("flags", flags);
    ImmutableList<String> frameworkRoots = FluentIterable.from(this.frameworkRoots)
        .transform(Functions.toStringFunction())
        .transform(sanitizer.sanitize(Optional.<Path>absent(), /* expandPaths */ false))
        .toList();
    builder.setReflectively("frameworkRoots", frameworkRoots);

    // If a sanitizer is being used for compilation, we need to record the working directory in
    // the rule key, as changing this changes the generated object file.
    if (operation == CxxPreprocessAndCompileStep.Operation.COMPILE_MUNGE_DEBUGINFO) {
      builder.setReflectively("compilationDirectory", sanitizer.getCompilationDirectory());
    }

    return builder;
  }

  @VisibleForTesting
  CxxPreprocessAndCompileStep makeMainStep() {

    // Resolve the map of symlinks to real paths to hand off the preprocess step.  If we're
    // compiling, this will just be empty.
    ImmutableMap.Builder<Path, Path> replacementPathsBuilder = ImmutableMap.builder();
    for (Map.Entry<Path, SourcePath> entry : includes.getFullNameToPathMap().entrySet()) {
      replacementPathsBuilder.put(entry.getKey(), getResolver().getPath(entry.getValue()));
    }
    ImmutableMap<Path, Path> replacementPaths = replacementPathsBuilder.build();

    Optional<ImmutableList<String>> preprocessorCommand;
    if (preprocessor.isPresent()) {
      preprocessorCommand = Optional.of(
          ImmutableList.<String>builder()
              .addAll(preprocessor.get().getCommandPrefix(getResolver()))
              .addAll(getPreprocessorSuffix())
              .build());
    } else {
      preprocessorCommand = Optional.absent();
    }

    Optional<ImmutableList<String>> compilerCommand;
    if (compiler.isPresent()) {
      compilerCommand = Optional.of(
          ImmutableList.<String>builder()
              .addAll(compiler.get().getCommandPrefix(getResolver()))
              .addAll(getCompilerSuffix())
              .build());
    } else {
      compilerCommand = Optional.absent();
    }

    return new CxxPreprocessAndCompileStep(
        operation,
        output,
        getResolver().getPath(input),
        inputType,
        preprocessorCommand,
        compilerCommand,
        replacementPaths,
        sanitizer);
  }

  @Override
  public ImmutableList<Step> getBuildSteps(
      BuildContext context,
      BuildableContext buildableContext) {
    buildableContext.recordArtifact(output);
    return ImmutableList.of(
        new MkdirStep(output.getParent()),
        makeMainStep());
  }

  private ImmutableList<String> getPreprocessorSuffix() {
    Preconditions.checkState(operation.isPreprocess());
    return ImmutableList.<String>builder()
        .addAll(preprocessorFlags.get())
        .addAll(
            MoreIterables.zipAndConcat(
                Iterables.cycle("-include"),
                FluentIterable.from(includes.getPrefixHeaders())
                    .transform(getResolver().getPathFunction())
                    .transform(Functions.toStringFunction())))
        .addAll(
            MoreIterables.zipAndConcat(
                Iterables.cycle("-I"),
                Iterables.transform(includeRoots, Functions.toStringFunction())))
        .addAll(
            MoreIterables.zipAndConcat(
                Iterables.cycle("-isystem"),
                Iterables.transform(systemIncludeRoots, Functions.toStringFunction())))
        .addAll(
            MoreIterables.zipAndConcat(
                Iterables.cycle("-F"),
                Iterables.transform(frameworkRoots, Functions.toStringFunction())))
        .build();
  }

  private ImmutableList<String> getCompilerSuffix() {
    Preconditions.checkState(operation.isCompile());
    ImmutableList.Builder<String> suffix = ImmutableList.builder();
    if (operation == CxxPreprocessAndCompileStep.Operation.COMPILE_MUNGE_DEBUGINFO) {
      suffix.addAll(getPreprocessorSuffix());
    }
    suffix.addAll(compilerFlags.get());
    return suffix.build();
  }

  public ImmutableList<String> getCompileCommandCombinedWithPreprocessBuildRule(
      CxxPreprocessAndCompile preprocessBuildRule) {
    if (!operation.isCompile() ||
        !preprocessBuildRule.operation.isPreprocess()) {
      throw new HumanReadableException(
          "%s is not preprocess rule or %s is not compile rule.",
          preprocessBuildRule,
          this);
    }
    ImmutableList.Builder<String> cmd = ImmutableList.builder();
    cmd.addAll(compiler.get().getCommandPrefix(getResolver()));
    cmd.add("-x", preprocessBuildRule.inputType.getLanguage());
    cmd.add("-c");
    cmd.addAll(preprocessBuildRule.getPreprocessorSuffix());
    cmd.addAll(getCompilerSuffix());
    cmd.add("-o", output.toString());
    cmd.add(getResolver().getPath(preprocessBuildRule.input).toString());
    return cmd.build();
  }

  public ImmutableList<String> getCommand() {
    if (operation == CxxPreprocessAndCompileStep.Operation.COMPILE_MUNGE_DEBUGINFO) {
      return makeMainStep().getCommand();
    }
    return getCompileCommandCombinedWithPreprocessBuildRule(this);
  }

  @Override
  public Path getPathToOutput() {
    return output;
  }

  @VisibleForTesting
  Optional<ImmutableList<String>> getPreprocessorFlags() {
    return preprocessorFlags;
  }

  @VisibleForTesting
  Optional<ImmutableList<String>> getCompilerFlags() {
    return compilerFlags;
  }

  public Path getOutput() {
    return output;
  }

  public SourcePath getInput() {
    return input;
  }

  public CxxHeaders getIncludes() {
    return includes;
  }

}


File: src/com/facebook/buck/cxx/CxxPreprocessables.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.graph.AbstractBreadthFirstTraversal;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SymlinkTree;
import com.google.common.base.Preconditions;
import com.google.common.base.Predicate;
import com.google.common.base.Predicates;
import com.google.common.base.Suppliers;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Maps;
import com.google.common.collect.Multimap;

import java.nio.file.Path;
import java.util.Collection;
import java.util.Map;

public class CxxPreprocessables {

  private CxxPreprocessables() {}

  /**
   * Resolve the map of name to {@link SourcePath} to a map of full header name to
   * {@link SourcePath}.
   */
  public static ImmutableMap<Path, SourcePath> resolveHeaderMap(
      Path basePath,
      ImmutableMap<String, SourcePath> headers) {

    ImmutableMap.Builder<Path, SourcePath> headerMap = ImmutableMap.builder();

    // Resolve the "names" of the headers to actual paths by prepending the base path
    // specified by the build target.
    for (ImmutableMap.Entry<String, SourcePath> ent : headers.entrySet()) {
      Path path = basePath.resolve(ent.getKey());
      headerMap.put(path, ent.getValue());
    }

    return headerMap.build();
  }

  /**
   * Find and return the {@link CxxPreprocessorInput} objects from {@link CxxPreprocessorDep}
   * found while traversing the dependencies starting from the {@link BuildRule} objects given.
   */
  public static Collection<CxxPreprocessorInput> getTransitiveCxxPreprocessorInput(
      final CxxPlatform cxxPlatform,
      Iterable<? extends BuildRule> inputs,
      final Predicate<Object> traverse) {

    // We don't really care about the order we get back here, since headers shouldn't
    // conflict.  However, we want something that's deterministic, so sort by build
    // target.
    final Map<BuildTarget, CxxPreprocessorInput> deps = Maps.newLinkedHashMap();

    // Build up the map of all C/C++ preprocessable dependencies.
    AbstractBreadthFirstTraversal<BuildRule> visitor =
        new AbstractBreadthFirstTraversal<BuildRule>(inputs) {
          @Override
          public ImmutableSet<BuildRule> visit(BuildRule rule) {
            if (rule instanceof CxxPreprocessorDep) {
              CxxPreprocessorDep dep = (CxxPreprocessorDep) rule;
              deps.putAll(
                  dep.getTransitiveCxxPreprocessorInput(cxxPlatform, HeaderVisibility.PUBLIC));
              return ImmutableSet.of();
            }
            return traverse.apply(rule) ? rule.getDeps() : ImmutableSet.<BuildRule>of();
          }
        };
    visitor.start();

    // Grab the cxx preprocessor inputs and return them.
    return deps.values();
  }

  public static Collection<CxxPreprocessorInput> getTransitiveCxxPreprocessorInput(
      final CxxPlatform cxxPlatform,
      Iterable<? extends BuildRule> inputs) {
    return getTransitiveCxxPreprocessorInput(
        cxxPlatform,
        inputs,
        Predicates.alwaysTrue());
  }

  /**
   * Build the {@link SymlinkTree} rule using the original build params from a target node.
   * In particular, make sure to drop all dependencies from the original build rule params,
   * as these are modeled via {@link CxxPreprocessAndCompile}.
   */
  public static SymlinkTree createHeaderSymlinkTreeBuildRule(
      SourcePathResolver resolver,
      BuildTarget target,
      BuildRuleParams params,
      Path root,
      ImmutableMap<Path, SourcePath> links) {

    return new SymlinkTree(
        params.copyWithChanges(
            target,
            // Symlink trees never need to depend on anything.
            Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of()),
            Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of())),
        resolver,
        root,
        links);
  }

  /**
   * Builds a {@link CxxPreprocessorInput} for a rule.
   */
  public static CxxPreprocessorInput getCxxPreprocessorInput(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      Flavor flavor,
      HeaderVisibility headerVisibility,
      Multimap<CxxSource.Type, String> exportedPreprocessorFlags,
      Iterable<Path> frameworkSearchPaths) {
    BuildRule rule = CxxDescriptionEnhancer.requireBuildRule(
        params,
        ruleResolver,
        flavor,
        CxxDescriptionEnhancer.getHeaderSymlinkTreeFlavor(headerVisibility));
    Preconditions.checkState(rule instanceof SymlinkTree);
    SymlinkTree symlinkTree = (SymlinkTree) rule;
    return CxxPreprocessorInput.builder()
        .addRules(symlinkTree.getBuildTarget())
        .putAllPreprocessorFlags(exportedPreprocessorFlags)
        .setIncludes(
            CxxHeaders.builder()
                .putAllNameToPathMap(symlinkTree.getLinks())
                .putAllFullNameToPathMap(symlinkTree.getFullLinks())
                .build())
        .addIncludeRoots(symlinkTree.getRoot())
        .addAllFrameworkRoots(frameworkSearchPaths)
        .build();
  }
}


File: src/com/facebook/buck/cxx/CxxPythonExtensionDescription.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargets;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.FlavorDomain;
import com.facebook.buck.model.FlavorDomainException;
import com.facebook.buck.python.PythonUtil;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRuleType;
import com.facebook.buck.rules.Description;
import com.facebook.buck.rules.ImplicitDepsInferringDescription;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SymlinkTree;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.infer.annotation.SuppressFieldNotInitialized;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;

import java.nio.file.Path;
import java.util.Map;

public class CxxPythonExtensionDescription implements
    Description<CxxPythonExtensionDescription.Arg>,
    ImplicitDepsInferringDescription<CxxPythonExtensionDescription.Arg> {

  private enum Type {
    EXTENSION,
  }

  private static final FlavorDomain<Type> LIBRARY_TYPE =
      new FlavorDomain<>(
          "C/C++ Library Type",
          ImmutableMap.of(
              CxxDescriptionEnhancer.SHARED_FLAVOR, Type.EXTENSION));

  public static final BuildRuleType TYPE = BuildRuleType.of("cxx_python_extension");

  private final CxxBuckConfig cxxBuckConfig;
  private final FlavorDomain<CxxPlatform> cxxPlatforms;

  public CxxPythonExtensionDescription(
      CxxBuckConfig cxxBuckConfig,
      FlavorDomain<CxxPlatform> cxxPlatforms) {
    this.cxxBuckConfig = cxxBuckConfig;
    this.cxxPlatforms = cxxPlatforms;
  }

  @Override
  public Arg createUnpopulatedConstructorArg() {
    return new Arg();
  }

  @VisibleForTesting
  protected BuildTarget getExtensionTarget(BuildTarget target, Flavor platform) {
    return CxxDescriptionEnhancer.createSharedLibraryBuildTarget(target, platform);
  }

  @VisibleForTesting
  protected String getExtensionName(BuildTarget target) {
    // .so is used on OS X too (as opposed to dylib).
    return String.format("%s.so", target.getShortName());
  }

  @VisibleForTesting
  protected Path getExtensionPath(BuildTarget target, Flavor platform) {
    return BuildTargets.getGenPath(getExtensionTarget(target, platform), "%s")
        .resolve(getExtensionName(target));
  }

  private <A extends Arg> BuildRule createExtensionBuildRule(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      CxxPlatform cxxPlatform,
      A args) {
    SourcePathResolver pathResolver = new SourcePathResolver(ruleResolver);

    // Extract all C/C++ sources from the constructor arg.
    ImmutableMap<String, CxxSource> srcs =
        CxxDescriptionEnhancer.parseCxxSources(params, ruleResolver, args);
    ImmutableMap<Path, SourcePath> headers =
        CxxDescriptionEnhancer.parseHeaders(
            params,
            ruleResolver,
            args);
    ImmutableMap<String, SourcePath> lexSrcs =
        CxxDescriptionEnhancer.parseLexSources(params, ruleResolver, args);
    ImmutableMap<String, SourcePath> yaccSrcs =
        CxxDescriptionEnhancer.parseYaccSources(params, ruleResolver, args);

    CxxHeaderSourceSpec lexYaccSources =
        CxxDescriptionEnhancer.createLexYaccBuildRules(
            params,
            ruleResolver,
            cxxPlatform,
            ImmutableList.<String>of(),
            lexSrcs,
            ImmutableList.<String>of(),
            yaccSrcs);

    // Setup the header symlink tree and combine all the preprocessor input from this rule
    // and all dependencies.
    SymlinkTree headerSymlinkTree = CxxDescriptionEnhancer.requireHeaderSymlinkTree(
        params,
        ruleResolver,
        new SourcePathResolver(ruleResolver),
        cxxPlatform,
        /* includeLexYaccHeaders */ true,
        lexSrcs,
        yaccSrcs,
        headers,
        HeaderVisibility.PRIVATE);
    CxxPreprocessorInput cxxPreprocessorInput =
        CxxDescriptionEnhancer.combineCxxPreprocessorInput(
            params,
            cxxPlatform,
            CxxFlags.getLanguageFlags(
                args.preprocessorFlags,
                args.platformPreprocessorFlags,
                args.langPreprocessorFlags,
                cxxPlatform.getFlavor()),
            args.prefixHeaders.get(),
            ImmutableList.of(headerSymlinkTree),
            ImmutableList.<Path>of(),
            CxxPreprocessables.getTransitiveCxxPreprocessorInput(
                cxxPlatform,
                params.getDeps()));

    ImmutableMap<String, CxxSource> allSources =
        ImmutableMap.<String, CxxSource>builder()
            .putAll(srcs)
            .putAll(lexYaccSources.getCxxSources())
            .build();

    // Generate rule to build the object files.
    ImmutableMap<CxxPreprocessAndCompile, SourcePath> picObjects =
        CxxSourceRuleFactory.requirePreprocessAndCompileRules(
            params,
            ruleResolver,
            pathResolver,
            cxxPlatform,
            cxxPreprocessorInput,
            CxxFlags.getFlags(
                args.compilerFlags,
                args.platformCompilerFlags,
                cxxPlatform.getFlavor()),
            cxxBuckConfig.getPreprocessMode(),
            allSources,
            CxxSourceRuleFactory.PicType.PIC);

    // Setup the rules to link the shared library.
    String extensionName = getExtensionName(params.getBuildTarget());
    Path extensionPath = getExtensionPath(params.getBuildTarget(), cxxPlatform.getFlavor());
    return CxxLinkableEnhancer.createCxxLinkableBuildRule(
        cxxPlatform,
        params,
        pathResolver,
        /* extraCxxLdFlags */ ImmutableList.<String>of(),
        /* extraLdFlags */ CxxFlags.getFlags(
            args.linkerFlags,
            args.platformLinkerFlags,
            cxxPlatform.getFlavor()),
        getExtensionTarget(params.getBuildTarget(), cxxPlatform.getFlavor()),
        Linker.LinkType.SHARED,
        Optional.of(extensionName),
        extensionPath,
        picObjects.values(),
        Linker.LinkableDepType.SHARED,
        params.getDeps(),
        args.cxxRuntimeType,
        Optional.<SourcePath>absent());
  }

  @Override
  public <A extends Arg> BuildRule createBuildRule(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      A args) {

    // See if we're building a particular "type" of this library, and if so, extract
    // it as an enum.
    Optional<Map.Entry<Flavor, Type>> type;
    Optional<Map.Entry<Flavor, CxxPlatform>> platform;
    try {
      type = LIBRARY_TYPE.getFlavorAndValue(
          ImmutableSet.copyOf(params.getBuildTarget().getFlavors()));
      platform = cxxPlatforms.getFlavorAndValue(
          ImmutableSet.copyOf(params.getBuildTarget().getFlavors()));
    } catch (FlavorDomainException e) {
      throw new HumanReadableException("%s: %s", params.getBuildTarget(), e.getMessage());
    }

    // If we *are* building a specific type of this lib, call into the type specific
    // rule builder methods.  Currently, we only support building a shared lib from the
    // pre-existing static lib, which we do here.
    if (type.isPresent()) {
      Preconditions.checkState(type.get().getValue() == Type.EXTENSION);
      Preconditions.checkState(platform.isPresent());
      return createExtensionBuildRule(params, ruleResolver, platform.get().getValue(), args);
    }

    // Otherwise, we return the generic placeholder of this library, that dependents can use
    // get the real build rules via querying the action graph.
    SourcePathResolver pathResolver = new SourcePathResolver(ruleResolver);
    Path baseModule = PythonUtil.getBasePath(params.getBuildTarget(), args.baseModule);
    return new CxxPythonExtension(
        params,
        ruleResolver,
        pathResolver,
        baseModule.resolve(getExtensionName(params.getBuildTarget())));
  }

  @Override
  public BuildRuleType getBuildRuleType() {
    return TYPE;
  }

  @Override
  public Iterable<BuildTarget> findDepsForTargetFromConstructorArgs(
      BuildTarget buildTarget,
      Arg constructorArg) {
    ImmutableSet.Builder<BuildTarget> deps = ImmutableSet.builder();

    deps.add(cxxBuckConfig.getPythonDep());

    if (constructorArg.lexSrcs.isPresent() && !constructorArg.lexSrcs.get().isEmpty()) {
      deps.add(cxxBuckConfig.getLexDep());
    }

    return deps.build();
  }

  @SuppressFieldNotInitialized
  public static class Arg extends CxxConstructorArg {
    public Optional<String> baseModule;
  }

}


File: src/com/facebook/buck/cxx/CxxSourceRuleFactory.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargets;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRules;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.util.MoreIterables;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.base.Supplier;
import com.google.common.base.Suppliers;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;

import java.nio.file.Path;
import java.util.Map;
import java.util.Set;

public class CxxSourceRuleFactory {

  private static final Logger LOG = Logger.get(CxxSourceRuleFactory.class);
  private static final String COMPILE_FLAVOR_PREFIX = "compile-";
  private static final String PREPROCESS_FLAVOR_PREFIX = "preprocess-";

  private final BuildRuleParams params;
  private final BuildRuleResolver resolver;
  private final SourcePathResolver pathResolver;
  private final CxxPlatform cxxPlatform;
  private final CxxPreprocessorInput cxxPreprocessorInput;
  private final ImmutableList<String> compilerFlags;

  private final Supplier<ImmutableList<BuildRule>> preprocessDeps = Suppliers.memoize(
      new Supplier<ImmutableList<BuildRule>>() {
        @Override
        public ImmutableList<BuildRule> get() {
          return ImmutableList.<BuildRule>builder()
              // Depend on the rule that generates the sources and headers we're compiling.
              .addAll(
                  pathResolver.filterBuildRuleInputs(
                      ImmutableList.<SourcePath>builder()
                          .addAll(cxxPreprocessorInput.getIncludes().getPrefixHeaders())
                          .addAll(cxxPreprocessorInput.getIncludes().getNameToPathMap().values())
                          .build()))
              // Also add in extra deps from the preprocessor input, such as the symlink tree
              // rules.
              .addAll(
                  BuildRules.toBuildRulesFor(
                      params.getBuildTarget(),
                      resolver,
                      cxxPreprocessorInput.getRules()))
              .build();
        }
      });

  @VisibleForTesting
  public CxxSourceRuleFactory(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      CxxPreprocessorInput cxxPreprocessorInput,
      ImmutableList<String> compilerFlags) {
    this.params = params;
    this.resolver = resolver;
    this.pathResolver = pathResolver;
    this.cxxPlatform = cxxPlatform;
    this.cxxPreprocessorInput = cxxPreprocessorInput;
    this.compilerFlags = compilerFlags;
  }

  /**
   * Prefixes each of the given assembler arguments with "-Xassembler" so that the compiler
   * assembler driver will pass these arguments directly down to the linker rather than
   * interpreting them itself.
   *
   * e.g. ["--fatal-warnings"] -> ["-Xassembler", "--fatal-warnings"]
   *
   * @param args arguments for the assembler.
   * @return arguments to be passed to the compiler assembler driver.
   */
  private Iterable<String> iXassembler(Iterable<String> args) {
    return MoreIterables.zipAndConcat(
        Iterables.cycle("-Xassembler"),
        args);
  }

  private ImmutableList<String> getPreprocessFlags(CxxSource.Type type) {
    return ImmutableList.<String>builder()
        .addAll(CxxSourceTypes.getPlatformPreprocessFlags(cxxPlatform, type))
        .addAll(cxxPreprocessorInput.getPreprocessorFlags().get(type))
        .build();
  }

  /**
   * @return the preprocessed file name for the given source name.
   */
  private String getPreprocessOutputName(CxxSource.Type type, String name) {
    CxxSource.Type outputType = CxxSourceTypes.getPreprocessorOutputType(type);
    return name + "." + Iterables.get(outputType.getExtensions(), 0);
  }

  /**
   * @return a {@link BuildTarget} used for the rule that preprocesses the source by the given
   *     name and type.
   */
  @VisibleForTesting
  public BuildTarget createPreprocessBuildTarget(
      String name,
      CxxSource.Type type,
      PicType pic) {
    String outputName = Flavor.replaceInvalidCharacters(getPreprocessOutputName(type, name));
    return BuildTarget
        .builder(params.getBuildTarget())
        .addFlavors(cxxPlatform.getFlavor())
        .addFlavors(
            ImmutableFlavor.of(
                String.format(
                    PREPROCESS_FLAVOR_PREFIX + "%s%s",
                    pic == PicType.PIC ? "pic-" : "",
                    outputName)))
        .build();
  }

  public static boolean isPreprocessFlavoredBuildTarget(BuildTarget target) {
    Set<Flavor> flavors = target.getFlavors();
    for (Flavor flavor : flavors) {
      if (flavor.getName().startsWith(PREPROCESS_FLAVOR_PREFIX)) {
        return true;
      }
    }
    return false;
  }

  /**
   * @return the output path for an object file compiled from the source with the given name.
   */
  @VisibleForTesting
  Path getPreprocessOutputPath(BuildTarget target, CxxSource.Type type, String name) {
    return BuildTargets.getGenPath(target, "%s").resolve(getPreprocessOutputName(type, name));
  }

  @VisibleForTesting
  public CxxPreprocessAndCompile createPreprocessBuildRule(
      BuildRuleResolver resolver,
      String name,
      CxxSource source,
      PicType pic) {

    Preconditions.checkArgument(CxxSourceTypes.isPreprocessableType(source.getType()));

    BuildTarget target = createPreprocessBuildTarget(name, source.getType(), pic);
    Tool tool = CxxSourceTypes.getPreprocessor(cxxPlatform, source.getType());

    // Build up the list of dependencies for this rule.
    ImmutableSortedSet<BuildRule> dependencies =
        ImmutableSortedSet.<BuildRule>naturalOrder()
            // Add dependencies on any build rules used to create the preprocessor.
            .addAll(tool.getBuildRules(pathResolver))
            // If a build rule generates our input source, add that as a dependency.
            .addAll(pathResolver.filterBuildRuleInputs(source.getPath()))
            // Depend on the rule that generates the sources and headers we're compiling.
            .addAll(preprocessDeps.get())
            .build();

    // Build up the list of extra preprocessor flags for this rule.
    ImmutableList<String> args =
        ImmutableList.<String>builder()
            // If we're using pic, add in the appropriate flag.
            .addAll(pic.getFlags())
            // Add in the source and platform specific preprocessor flags.
            .addAll(getPreprocessFlags(source.getType()))
            // Add custom per-file flags.
            .addAll(source.getFlags())
            .build();

    // Build the CxxCompile rule and add it to our sorted set of build rules.
    CxxPreprocessAndCompile result = CxxPreprocessAndCompile.preprocess(
        params.copyWithChanges(
            target,
            Suppliers.ofInstance(dependencies),
            Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of())),
        pathResolver,
        tool,
        args,
        getPreprocessOutputPath(target, source.getType(), name),
        source.getPath(),
        source.getType(),
        ImmutableList.copyOf(cxxPreprocessorInput.getIncludeRoots()),
        ImmutableList.copyOf(cxxPreprocessorInput.getSystemIncludeRoots()),
        ImmutableList.copyOf(cxxPreprocessorInput.getFrameworkRoots()),
        cxxPreprocessorInput.getIncludes(),
        cxxPlatform.getDebugPathSanitizer());
    resolver.addToIndex(result);
    return result;
  }

  @VisibleForTesting
  CxxPreprocessAndCompile requirePreprocessBuildRule(
      BuildRuleResolver resolver,
      String name,
      CxxSource source,
      PicType pic) {

    BuildTarget target = createPreprocessBuildTarget(name, source.getType(), pic);
    Optional<CxxPreprocessAndCompile> existingRule = resolver.getRuleOptionalWithType(
        target, CxxPreprocessAndCompile.class);
    if (existingRule.isPresent()) {
      return existingRule.get();
    }

    return createPreprocessBuildRule(resolver, name, source, pic);
  }

  /**
   * @return the object file name for the given source name.
   */
  private String getCompileOutputName(String name) {
    return name + ".o";
  }

  /**
   * @return the output path for an object file compiled from the source with the given name.
   */
  @VisibleForTesting
  Path getCompileOutputPath(BuildTarget target, String name) {
    return BuildTargets.getGenPath(target, "%s").resolve(getCompileOutputName(name));
  }

  /**
   * @return a build target for a {@link CxxPreprocessAndCompile} rule for the source with the
   *    given name.
   */
  @VisibleForTesting
  public BuildTarget createCompileBuildTarget(
      String name,
      PicType pic) {
    String outputName = Flavor.replaceInvalidCharacters(getCompileOutputName(name));
    return BuildTarget
        .builder(params.getBuildTarget())
        .addFlavors(cxxPlatform.getFlavor())
        .addFlavors(
            ImmutableFlavor.of(
                String.format(
                    COMPILE_FLAVOR_PREFIX + "%s%s",
                    pic == PicType.PIC ? "pic-" : "",
                    outputName)))
        .build();
  }

  public static boolean isCompileFlavoredBuildTarget(BuildTarget target) {
    Set<Flavor> flavors = target.getFlavors();
    for (Flavor flavor : flavors) {
      if (flavor.getName().startsWith(COMPILE_FLAVOR_PREFIX)) {
        return true;
      }
    }
    return false;
  }

  // Pick the compiler to use.  Basically, if we're dealing with C++ sources, use the C++
  // compiler, and the C compiler for everything.
  private Tool getCompiler(CxxSource.Type type) {
    return CxxSourceTypes.needsCxxCompiler(type) ?
      cxxPlatform.getCxx() :
      cxxPlatform.getCc();
  }

  private ImmutableList<String> getCompileFlags(CxxSource.Type type) {
    ImmutableList.Builder<String> args = ImmutableList.builder();

    // If we're dealing with a C source that can be compiled, add the platform C compiler flags.
    if (type == CxxSource.Type.C_CPP_OUTPUT ||
        type == CxxSource.Type.OBJC_CPP_OUTPUT) {
      args.addAll(cxxPlatform.getCflags());
    }

    // If we're dealing with a C++ source that can be compiled, add the platform C++ compiler
    // flags.
    if (type == CxxSource.Type.CXX_CPP_OUTPUT ||
        type == CxxSource.Type.OBJCXX_CPP_OUTPUT) {
      args.addAll(cxxPlatform.getCxxflags());
    }

    // Add in explicit additional compiler flags, if we're compiling.
    if (type == CxxSource.Type.C_CPP_OUTPUT ||
        type == CxxSource.Type.OBJC_CPP_OUTPUT ||
        type == CxxSource.Type.CXX_CPP_OUTPUT ||
        type == CxxSource.Type.OBJCXX_CPP_OUTPUT) {
      args.addAll(compilerFlags);
    }

    // All source types require assembling, so add in platform-specific assembler flags.
    args.addAll(iXassembler(cxxPlatform.getAsflags()));

    return args.build();
  }

  /**
   * @return a {@link CxxPreprocessAndCompile} rule that preprocesses, compiles, and assembles the
   *    given {@link CxxSource}.
   */
  @VisibleForTesting
  public CxxPreprocessAndCompile createCompileBuildRule(
      BuildRuleResolver resolver,
      String name,
      CxxSource source,
      PicType pic) {

    Preconditions.checkArgument(CxxSourceTypes.isCompilableType(source.getType()));

    BuildTarget target = createCompileBuildTarget(name, pic);
    Tool tool = getCompiler(source.getType());

    ImmutableSortedSet<BuildRule> dependencies =
        ImmutableSortedSet.<BuildRule>naturalOrder()
            // Add dependencies on any build rules used to create the compiler.
            .addAll(tool.getBuildRules(pathResolver))
            // If a build rule generates our input source, add that as a dependency.
            .addAll(pathResolver.filterBuildRuleInputs(source.getPath()))
            .build();

    // Build up the list of compiler flags.
    ImmutableList<String> args =
        ImmutableList.<String>builder()
            // If we're using pic, add in the appropriate flag.
            .addAll(pic.getFlags())
            // Add in the platform and source specific compiler flags.
            .addAll(getCompileFlags(source.getType()))
            // Add in per-source flags.
            .addAll(source.getFlags())
            .build();

    // Build the CxxCompile rule and add it to our sorted set of build rules.
    CxxPreprocessAndCompile result = CxxPreprocessAndCompile.compile(
        params.copyWithChanges(
            target,
            Suppliers.ofInstance(dependencies),
            Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of())),
        pathResolver,
        tool,
        args,
        getCompileOutputPath(target, name),
        source.getPath(),
        source.getType(),
        cxxPlatform.getDebugPathSanitizer());
    resolver.addToIndex(result);
    return result;
  }

  @VisibleForTesting
  CxxPreprocessAndCompile requireCompileBuildRule(
      BuildRuleResolver resolver,
      String name,
      CxxSource source,
      PicType pic) {

    BuildTarget target = createCompileBuildTarget(name, pic);
    Optional<CxxPreprocessAndCompile> existingRule = resolver.getRuleOptionalWithType(
        target, CxxPreprocessAndCompile.class);
    if (existingRule.isPresent()) {
      return existingRule.get();
    }

    return createCompileBuildRule(resolver, name, source, pic);
  }

  /**
   * @return a {@link CxxPreprocessAndCompile} rule that preprocesses, compiles, and assembles the
   *    given {@link CxxSource}.
   */
  @VisibleForTesting
  public CxxPreprocessAndCompile createPreprocessAndCompileBuildRule(
      BuildRuleResolver resolver,
      String name,
      CxxSource source,
      PicType pic,
      CxxPreprocessMode strategy) {

    Preconditions.checkArgument(CxxSourceTypes.isPreprocessableType(source.getType()));

    BuildTarget target = createCompileBuildTarget(name, pic);
    Tool tool = getCompiler(source.getType());

    ImmutableSortedSet<BuildRule> dependencies =
        ImmutableSortedSet.<BuildRule>naturalOrder()
            // Add dependencies on any build rules used to create the preprocessor.
            .addAll(tool.getBuildRules(pathResolver))
            // If a build rule generates our input source, add that as a dependency.
            .addAll(pathResolver.filterBuildRuleInputs(source.getPath()))
            // Add in all preprocessor deps.
            .addAll(preprocessDeps.get())
            .build();

    // Build up the list of compiler flags.
    ImmutableList<String> compilerFlags = ImmutableList.<String>builder()
        // If we're using pic, add in the appropriate flag.
        .addAll(pic.getFlags())
            // Add in the platform and source specific compiler flags.
        .addAll(getCompileFlags(CxxSourceTypes.getPreprocessorOutputType(source.getType())))
            // Add in per-source flags.
        .addAll(source.getFlags())
        .build();

    LOG.verbose("Creating preprocess and compile %s for %s", target, source);

    // Build the CxxCompile rule and add it to our sorted set of build rules.
    CxxPreprocessAndCompile result = CxxPreprocessAndCompile.preprocessAndCompile(
        params.copyWithChanges(
            target,
            Suppliers.ofInstance(dependencies),
            Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of())),
        pathResolver,
        tool,
        getPreprocessFlags(source.getType()),
        tool,
        compilerFlags,
        getCompileOutputPath(target, name),
        source.getPath(),
        source.getType(),
        ImmutableList.copyOf(cxxPreprocessorInput.getIncludeRoots()),
        ImmutableList.copyOf(cxxPreprocessorInput.getSystemIncludeRoots()),
        ImmutableList.copyOf(cxxPreprocessorInput.getFrameworkRoots()),
        cxxPreprocessorInput.getIncludes(), cxxPlatform.getDebugPathSanitizer(), strategy);
    resolver.addToIndex(result);
    return result;
  }

  @VisibleForTesting
  CxxPreprocessAndCompile requirePreprocessAndCompileBuildRule(
      BuildRuleResolver resolver,
      String name,
      CxxSource source,
      PicType pic,
      CxxPreprocessMode strategy) {

    BuildTarget target = createCompileBuildTarget(name, pic);
    Optional<CxxPreprocessAndCompile> existingRule = resolver.getRuleOptionalWithType(
        target, CxxPreprocessAndCompile.class);
    if (existingRule.isPresent()) {
      return existingRule.get();
    }

    return createPreprocessAndCompileBuildRule(resolver, name, source, pic, strategy);
  }

  private ImmutableMap<CxxPreprocessAndCompile, SourcePath> requirePreprocessAndCompileRules(
      BuildRuleResolver resolver,
      CxxPreprocessMode strategy,
      ImmutableMap<String, CxxSource> sources,
      PicType pic) {

    ImmutableList.Builder<CxxPreprocessAndCompile> objects = ImmutableList.builder();

    for (Map.Entry<String, CxxSource> entry : sources.entrySet()) {
      String name = entry.getKey();
      CxxSource source = entry.getValue();

      Preconditions.checkState(
          CxxSourceTypes.isPreprocessableType(source.getType()) ||
              CxxSourceTypes.isCompilableType(source.getType()));

      switch (strategy) {

        case PIPED:
        case COMBINED: {
          CxxPreprocessAndCompile rule;

          // If it's a preprocessable source, use a combine preprocess-and-compile build rule.
          // Otherwise, use a regular compile rule.
          if (CxxSourceTypes.isPreprocessableType(source.getType())) {
            rule = requirePreprocessAndCompileBuildRule(resolver, name, source, pic, strategy);
          } else {
            rule = requireCompileBuildRule(resolver, name, source, pic);
          }

          objects.add(rule);
          break;
        }

        case SEPARATE: {

          // If this is a preprocessable source, first create the preprocess build rule and
          // update the source and name to represent its compilable output.
          if (CxxSourceTypes.isPreprocessableType(source.getType())) {
            CxxPreprocessAndCompile rule = requirePreprocessBuildRule(resolver, name, source, pic);
            source = CxxSource.copyOf(source)
                .withType(CxxSourceTypes.getPreprocessorOutputType(source.getType()))
                .withPath(
                    new BuildTargetSourcePath(
                        params.getProjectFilesystem(),
                        rule.getBuildTarget()));
          }

          // Now build the compile build rule.
          CxxPreprocessAndCompile rule = requireCompileBuildRule(resolver, name, source, pic);
          objects.add(rule);

          break;
        }

        // $CASES-OMITTED$
        default:
          throw new IllegalStateException();
      }
    }

    final ProjectFilesystem projectFilesystem = params.getProjectFilesystem();
    return FluentIterable
        .from(objects.build())
        .toMap(new Function<CxxPreprocessAndCompile, SourcePath>() {
          @Override
          public SourcePath apply(CxxPreprocessAndCompile input) {
            return new BuildTargetSourcePath(projectFilesystem, input.getBuildTarget());
          }
        });
  }

  public static ImmutableMap<CxxPreprocessAndCompile, SourcePath> requirePreprocessAndCompileRules(
      BuildRuleParams params,
      BuildRuleResolver resolver,
      SourcePathResolver pathResolver,
      CxxPlatform cxxPlatform,
      CxxPreprocessorInput cxxPreprocessorInput,
      ImmutableList<String> compilerFlags,
      CxxPreprocessMode strategy,
      ImmutableMap<String, CxxSource> sources,
      PicType pic) {
    CxxSourceRuleFactory factory =
        new CxxSourceRuleFactory(
            params,
            resolver,
            pathResolver,
            cxxPlatform,
            cxxPreprocessorInput,
            compilerFlags);
    return factory.requirePreprocessAndCompileRules(resolver, strategy, sources, pic);
  }

  public enum PicType {

    // Generate position-independent code (e.g. for use in shared libraries).
    PIC("-fPIC"),

    // Generate position-dependent code.
    PDC;

    private final ImmutableList<String> flags;

    PicType(String... flags) {
      this.flags = ImmutableList.copyOf(flags);
    }

    public ImmutableList<String> getFlags() {
      return flags;
    }

  }

}


File: src/com/facebook/buck/cxx/PrebuiltCxxLibrary.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.android.AndroidPackageable;
import com.facebook.buck.android.AndroidPackageableCollector;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.Pair;
import com.facebook.buck.python.PythonPackageComponents;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.PathSourcePath;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Maps;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

public class PrebuiltCxxLibrary extends AbstractCxxLibrary {

  private final BuildRuleParams params;
  private final BuildRuleResolver ruleResolver;
  private final SourcePathResolver pathResolver;
  private final ImmutableList<Path> includeDirs;
  private final Optional<String> libDir;
  private final Optional<String> libName;
  private final ImmutableList<String> exportedLinkerFlags;
  private final ImmutableList<Pair<String, ImmutableList<String>>> exportedPlatformLinkerFlags;
  private final Optional<String> soname;
  private final boolean headerOnly;
  private final boolean linkWhole;
  private final boolean provided;


  private final Map<Pair<Flavor, HeaderVisibility>, ImmutableMap<BuildTarget, CxxPreprocessorInput>>
      cxxPreprocessorInputCache = Maps.newHashMap();

  public PrebuiltCxxLibrary(
      BuildRuleParams params,
      BuildRuleResolver ruleResolver,
      SourcePathResolver pathResolver,
      ImmutableList<Path> includeDirs,
      Optional<String> libDir,
      Optional<String> libName,
      ImmutableList<String> exportedLinkerFlags,
      ImmutableList<Pair<String, ImmutableList<String>>> exportedPlatformLinkerFlags,
      Optional<String> soname,
      boolean headerOnly,
      boolean linkWhole,
      boolean provided) {
    super(params, pathResolver);
    this.params = params;
    this.ruleResolver = ruleResolver;
    this.pathResolver = pathResolver;
    this.includeDirs = includeDirs;
    this.libDir = libDir;
    this.libName = libName;
    this.exportedLinkerFlags = exportedLinkerFlags;
    this.exportedPlatformLinkerFlags = exportedPlatformLinkerFlags;
    this.soname = soname;
    this.headerOnly = headerOnly;
    this.linkWhole = linkWhole;
    this.provided = provided;
  }

  /**
   * Makes sure all build rules needed to produce the shared library are added to the action
   * graph.
   *
   * @return the {@link SourcePath} representing the actual shared library.
   */
  private SourcePath requireSharedLibrary(CxxPlatform cxxPlatform) {
    Path sharedLibraryPath =
        PrebuiltCxxLibraryDescription.getSharedLibraryPath(
            getBuildTarget(),
            cxxPlatform,
            libDir,
            libName);

    // If the shared library is prebuilt, just return a reference to it.
    if (params.getProjectFilesystem().exists(sharedLibraryPath)) {
      return new PathSourcePath(params.getProjectFilesystem(), sharedLibraryPath);
    }

    // Otherwise, generate it's build rule.
    BuildRule sharedLibrary =
        CxxDescriptionEnhancer.requireBuildRule(
            params,
            ruleResolver,
            cxxPlatform.getFlavor(),
            CxxDescriptionEnhancer.SHARED_FLAVOR);

    return new BuildTargetSourcePath(
        sharedLibrary.getProjectFilesystem(),
        sharedLibrary.getBuildTarget());
  }

  @Override
  public CxxPreprocessorInput getCxxPreprocessorInput(
      CxxPlatform cxxPlatform,
      HeaderVisibility headerVisibility) {
    switch (headerVisibility) {
      case PUBLIC:
        return CxxPreprocessorInput.builder()
            // Just pass the include dirs as system includes.
            .addAllSystemIncludeRoots(includeDirs)
            .build();
      case PRIVATE:
        return CxxPreprocessorInput.EMPTY;
    }

    // We explicitly don't put this in a default statement because we
    // want the compiler to warn if someone modifies the HeaderVisibility enum.
    throw new RuntimeException("Invalid header visibility: " + headerVisibility);
  }


  @Override
  public ImmutableMap<BuildTarget, CxxPreprocessorInput>
      getTransitiveCxxPreprocessorInput(
          CxxPlatform cxxPlatform,
          HeaderVisibility headerVisibility) {
    Pair<Flavor, HeaderVisibility> key = new Pair<>(cxxPlatform.getFlavor(), headerVisibility);
    ImmutableMap<BuildTarget, CxxPreprocessorInput> result = cxxPreprocessorInputCache.get(key);
    if (result == null) {
      Map<BuildTarget, CxxPreprocessorInput> builder = Maps.newLinkedHashMap();
      builder.put(getBuildTarget(), getCxxPreprocessorInput(cxxPlatform, headerVisibility));
      for (BuildRule dep : getDeps()) {
        if (dep instanceof CxxPreprocessorDep) {
          builder.putAll(
              ((CxxPreprocessorDep) dep).getTransitiveCxxPreprocessorInput(
                  cxxPlatform,
                  headerVisibility));
        }
      }
      result = ImmutableMap.copyOf(builder);
      cxxPreprocessorInputCache.put(key, result);
    }
    return result;
  }

  @Override
  public NativeLinkableInput getNativeLinkableInput(
      CxxPlatform cxxPlatform,
      Linker.LinkableDepType type) {

    // Build the library path and linker arguments that we pass through the
    // {@link NativeLinkable} interface for linking.
    ImmutableList.Builder<SourcePath> librariesBuilder = ImmutableList.builder();
    ImmutableList.Builder<String> linkerArgsBuilder = ImmutableList.builder();
    linkerArgsBuilder.addAll(exportedLinkerFlags);
    linkerArgsBuilder.addAll(
        CxxDescriptionEnhancer.getPlatformFlags(
            exportedPlatformLinkerFlags,
            cxxPlatform.getFlavor().toString()));
    if (!headerOnly) {
      if (provided || type == Linker.LinkableDepType.SHARED) {
        SourcePath sharedLibrary = requireSharedLibrary(cxxPlatform);
        librariesBuilder.add(sharedLibrary);
        linkerArgsBuilder.add(pathResolver.getPath(sharedLibrary).toString());
      } else {
        Path staticLibraryPath =
            PrebuiltCxxLibraryDescription.getStaticLibraryPath(
                getBuildTarget(),
                cxxPlatform,
                libDir,
                libName);
        librariesBuilder.add(new PathSourcePath(getProjectFilesystem(), staticLibraryPath));
        if (linkWhole) {
          Linker linker = cxxPlatform.getLd();
          linkerArgsBuilder.addAll(linker.linkWhole(staticLibraryPath.toString()));
        } else {
          linkerArgsBuilder.add(staticLibraryPath.toString());
        }
      }
    }
    final ImmutableList<SourcePath> libraries = librariesBuilder.build();
    final ImmutableList<String> linkerArgs = linkerArgsBuilder.build();

    return NativeLinkableInput.of(/* inputs */ libraries, /* args */ linkerArgs);
  }

  @Override
  public Optional<Linker.LinkableDepType> getPreferredLinkage(CxxPlatform cxxPlatform) {
    return Optional.absent();
  }

  @Override
  public PythonPackageComponents getPythonPackageComponents(CxxPlatform cxxPlatform) {
    String resolvedSoname =
        PrebuiltCxxLibraryDescription.getSoname(getBuildTarget(), cxxPlatform, soname, libName);

    // Build up the shared library list to contribute to a python executable package.
    ImmutableMap.Builder<Path, SourcePath> nativeLibrariesBuilder = ImmutableMap.builder();
    if (!headerOnly && !provided) {
      SourcePath sharedLibrary = requireSharedLibrary(cxxPlatform);
      nativeLibrariesBuilder.put(
          Paths.get(resolvedSoname),
          sharedLibrary);
    }
    ImmutableMap<Path, SourcePath> nativeLibraries = nativeLibrariesBuilder.build();

    return PythonPackageComponents.of(
        /* modules */ ImmutableMap.<Path, SourcePath>of(),
        /* resources */ ImmutableMap.<Path, SourcePath>of(),
        nativeLibraries,
        /* prebuiltLibraries */ ImmutableSet.<SourcePath>of(),
        /* zipSafe */ Optional.<Boolean>absent());
  }

  @Override
  public Iterable<AndroidPackageable> getRequiredPackageables() {
    return AndroidPackageableCollector.getPackageableRules(params.getDeps());
  }

  @Override
  public void addToCollector(AndroidPackageableCollector collector) {
    collector.addNativeLinkable(this);
  }

  @Override
  public ImmutableMap<String, SourcePath> getSharedLibraries(CxxPlatform cxxPlatform) {
    String resolvedSoname =
        PrebuiltCxxLibraryDescription.getSoname(getBuildTarget(), cxxPlatform, soname, libName);
    ImmutableMap.Builder<String, SourcePath> solibs = ImmutableMap.builder();
    if (!headerOnly && !provided) {
      SourcePath sharedLibrary = requireSharedLibrary(cxxPlatform);
      solibs.put(resolvedSoname, sharedLibrary);
    }
    return solibs.build();
  }

  @Override
  public boolean isTestedBy(BuildTarget buildTarget) {
    return false;
  }
}


File: src/com/facebook/buck/ocaml/OCamlRuleBuilder.java
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

package com.facebook.buck.ocaml;

import com.facebook.buck.cxx.CxxPreprocessables;
import com.facebook.buck.cxx.CxxPreprocessorDep;
import com.facebook.buck.cxx.CxxPreprocessorInput;
import com.facebook.buck.cxx.Linker;
import com.facebook.buck.cxx.NativeLinkableInput;
import com.facebook.buck.cxx.NativeLinkables;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.rules.AbstractBuildRule;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SourcePaths;
import com.facebook.buck.rules.coercer.OCamlSource;
import com.facebook.buck.util.Ansi;
import com.facebook.buck.util.CapturingPrintStream;
import com.facebook.buck.util.Console;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.buck.util.ProcessExecutor;
import com.facebook.buck.util.Verbosity;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.base.Predicate;
import com.google.common.base.Predicates;
import com.google.common.base.Suppliers;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;

/**
 * Compute transitive dependencies and generate ocaml build rules
 */
public class OCamlRuleBuilder {

  private static final Flavor OCAML_STATIC_FLAVOR = ImmutableFlavor.of("static");
  private static final Flavor OCAML_LINK_BINARY_FLAVOR = ImmutableFlavor.of("binary");

  private OCamlRuleBuilder() {
  }

  public static Function<BuildRule, ImmutableList<String>> getLibInclude(
      final boolean isBytecode) {
    return
      new Function<BuildRule, ImmutableList<String>>() {
        @Override
        public ImmutableList<String> apply(BuildRule input) {
          if (input instanceof OCamlLibrary) {
            OCamlLibrary library = (OCamlLibrary) input;
            if (isBytecode) {
                return ImmutableList.copyOf(library.getBytecodeIncludeDirs());
            } else {
              return ImmutableList.of(library.getIncludeLibDir().toString());
            }
          } else {
            return ImmutableList.of();
          }
        }
      };
  }

  public static ImmutableList<SourcePath> getInput(Iterable<OCamlSource> source) {
    return ImmutableList.copyOf(
        FluentIterable.from(source)
            .transform(
                new Function<OCamlSource, SourcePath>() {
                  @Override
                  public SourcePath apply(OCamlSource input) {
                    return input.getSource();
                  }
                })
    );
  }

  @VisibleForTesting
  protected static BuildTarget createStaticLibraryBuildTarget(BuildTarget target) {
    return BuildTarget.builder(target).addFlavors(OCAML_STATIC_FLAVOR).build();
  }

  @VisibleForTesting
  protected static BuildTarget createOCamlLinkTarget(BuildTarget target) {
    return BuildTarget.builder(target).addFlavors(OCAML_LINK_BINARY_FLAVOR).build();
  }

  public static AbstractBuildRule createBuildRule(
      OCamlBuckConfig ocamlBuckConfig,
      final BuildRuleParams params,
      BuildRuleResolver resolver,
      ImmutableList<OCamlSource> srcs,
      boolean isLibrary,
      ImmutableList<String> argFlags,
      final ImmutableList<String> linkerFlags) {
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);
    boolean noYaccOrLexSources = FluentIterable.from(srcs).transform(OCamlSource.TO_SOURCE_PATH)
        .filter(OCamlUtil.sourcePathExt(
                  pathResolver,
                  OCamlCompilables.OCAML_MLL,
                  OCamlCompilables.OCAML_MLY))
        .isEmpty();
    if (noYaccOrLexSources) {
      return createFineGrainedBuildRule(
          ocamlBuckConfig,
          params,
          resolver,
          srcs,
          isLibrary,
          argFlags,
          linkerFlags);
    } else {
      return createBulkBuildRule(
          ocamlBuckConfig,
          params,
          resolver,
          srcs,
          isLibrary,
          argFlags,
          linkerFlags);
    }
  }

  public static AbstractBuildRule createBulkBuildRule(
      OCamlBuckConfig ocamlBuckConfig,
      final BuildRuleParams params,
      BuildRuleResolver resolver,
      ImmutableList<OCamlSource> srcs,
      boolean isLibrary,
      ImmutableList<String> argFlags,
      final ImmutableList<String> linkerFlags) {
    CxxPreprocessorInput cxxPreprocessorInputFromDeps;
    try {
      cxxPreprocessorInputFromDeps = CxxPreprocessorInput.concat(
          CxxPreprocessables.getTransitiveCxxPreprocessorInput(
              ocamlBuckConfig.getCxxPlatform(),
              FluentIterable.from(params.getDeps())
                  .filter(Predicates.instanceOf(CxxPreprocessorDep.class))));
    } catch (CxxPreprocessorInput.ConflictingHeadersException e) {
      throw e.getHumanReadableExceptionForBuildTarget(params.getBuildTarget());
    }

    SourcePathResolver pathResolver = new SourcePathResolver(resolver);

    ImmutableList<String> includes = FluentIterable.from(params.getDeps())
        .transformAndConcat(getLibInclude(false))
        .toList();

    ImmutableList<String> bytecodeIncludes = FluentIterable.from(params.getDeps())
        .transformAndConcat(getLibInclude(true))
        .toList();

    NativeLinkableInput linkableInput = NativeLinkables.getTransitiveNativeLinkableInput(
        ocamlBuckConfig.getCxxPlatform(),
        params.getDeps(),
        Linker.LinkableDepType.STATIC,
        /* reverse */ false);

    ImmutableList<OCamlLibrary> ocamlInput = OCamlUtil.getTransitiveOCamlInput(params.getDeps());

    ImmutableSortedSet.Builder<BuildRule> allDepsBuilder = ImmutableSortedSet.naturalOrder();
    allDepsBuilder.addAll(pathResolver.filterBuildRuleInputs(getInput(srcs)));
    allDepsBuilder.addAll(pathResolver.filterBuildRuleInputs(linkableInput.getInputs()));
    for (OCamlLibrary library : ocamlInput) {
      allDepsBuilder.addAll(library.getCompileDeps());
      allDepsBuilder.addAll(library.getBytecodeCompileDeps());
    }
    ImmutableSortedSet<BuildRule> allDeps = allDepsBuilder.build();

    BuildTarget buildTarget =
        isLibrary ? createStaticLibraryBuildTarget(params.getBuildTarget())
            : createOCamlLinkTarget(params.getBuildTarget());
    final BuildRuleParams compileParams = params.copyWithChanges(
        buildTarget,
        /* declaredDeps */ Suppliers.ofInstance(allDeps),
        /* extraDeps */ Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of()));

    ImmutableList.Builder<String> flagsBuilder = ImmutableList.builder();
    flagsBuilder.addAll(argFlags);

    ImmutableSortedSet.Builder<BuildRule> compileDepsBuilder = ImmutableSortedSet.naturalOrder();
    ImmutableSortedSet.Builder<BuildRule> bytecodeCompileDepsBuilder =
        ImmutableSortedSet.naturalOrder();
    ImmutableSortedSet.Builder<BuildRule> bytecodeLinkDepsBuilder =
        ImmutableSortedSet.naturalOrder();
    for (OCamlLibrary library : ocamlInput) {
      compileDepsBuilder.addAll(library.getCompileDeps());
      bytecodeCompileDepsBuilder.addAll(library.getBytecodeCompileDeps());
      bytecodeLinkDepsBuilder.addAll(library.getBytecodeLinkDeps());
    }
    OCamlBuildContext ocamlContext =
        OCamlBuildContext.builder(ocamlBuckConfig)
            .setFlags(flagsBuilder.build())
            .setIncludes(includes)
            .setBytecodeIncludes(bytecodeIncludes)
            .setOCamlInput(ocamlInput)
            .setLinkableInput(linkableInput)
            .setBuildTarget(buildTarget)
            .setLibrary(isLibrary)
            .setCxxPreprocessorInput(cxxPreprocessorInputFromDeps)
            .setInput(pathResolver.getAllPaths(getInput(srcs)))
            .setCompileDeps(compileDepsBuilder.build())
            .setBytecodeCompileDeps(bytecodeCompileDepsBuilder.build())
            .setBytecodeLinkDeps(bytecodeLinkDepsBuilder.build())
            .build();

    final OCamlBuild ocamlLibraryBuild = new OCamlBuild(
        compileParams,
        pathResolver,
        ocamlContext,
        ocamlBuckConfig.getCCompiler(),
        ocamlBuckConfig.getCxxCompiler());
    resolver.addToIndex(ocamlLibraryBuild);

    if (isLibrary) {
      return new OCamlStaticLibrary(
          params.copyWithDeps(
              Suppliers.ofInstance(
                  ImmutableSortedSet.<BuildRule>naturalOrder()
                      .addAll(params.getDeclaredDeps())
                      .add(ocamlLibraryBuild)
                      .build()),
              Suppliers.ofInstance(params.getExtraDeps())),
          pathResolver,
          compileParams,
          linkerFlags,
          FluentIterable.from(srcs)
              .transform(OCamlSource.TO_SOURCE_PATH)
              .transform(pathResolver.getPathFunction())
              .filter(OCamlUtil.ext(OCamlCompilables.OCAML_C))
              .transform(ocamlContext.toCOutput())
              .transform(
                  SourcePaths.getToBuildTargetSourcePath(
                      params.getProjectFilesystem(),
                      compileParams.getBuildTarget()))
              .toList(),
          ocamlContext,
          ocamlLibraryBuild,
          ImmutableSortedSet.<BuildRule>of(ocamlLibraryBuild),
          ImmutableSortedSet.<BuildRule>of(ocamlLibraryBuild),
          ImmutableSortedSet.<BuildRule>of(ocamlLibraryBuild));
    } else {
      return new OCamlBinary(
          params.copyWithDeps(
              Suppliers.ofInstance(
                  ImmutableSortedSet.<BuildRule>naturalOrder()
                      .addAll(params.getDeclaredDeps())
                      .add(ocamlLibraryBuild)
                      .build()),
              Suppliers.ofInstance(params.getExtraDeps())),
          pathResolver,
          ocamlLibraryBuild);
    }
  }

  public static AbstractBuildRule createFineGrainedBuildRule(
      OCamlBuckConfig ocamlBuckConfig,
      final BuildRuleParams params,
      BuildRuleResolver resolver,
      ImmutableList<OCamlSource> srcs,
      boolean isLibrary,
      ImmutableList<String> argFlags,
      final ImmutableList<String> linkerFlags) {
    CxxPreprocessorInput cxxPreprocessorInputFromDeps;
    try {
      cxxPreprocessorInputFromDeps = CxxPreprocessorInput.concat(
          CxxPreprocessables.getTransitiveCxxPreprocessorInput(
              ocamlBuckConfig.getCxxPlatform(),
              FluentIterable.from(params.getDeps())
                  .filter(Predicates.instanceOf(CxxPreprocessorDep.class))));
    } catch (CxxPreprocessorInput.ConflictingHeadersException e) {
      throw e.getHumanReadableExceptionForBuildTarget(params.getBuildTarget());
    }

    SourcePathResolver pathResolver = new SourcePathResolver(resolver);

    ImmutableList<String> includes = FluentIterable.from(params.getDeps())
        .transformAndConcat(getLibInclude(false))
        .toList();

    ImmutableList<String> bytecodeIncludes = FluentIterable.from(params.getDeps())
        .transformAndConcat(getLibInclude(true))
        .toList();

    NativeLinkableInput linkableInput = NativeLinkables.getTransitiveNativeLinkableInput(
        ocamlBuckConfig.getCxxPlatform(),
        params.getDeps(),
        Linker.LinkableDepType.STATIC,
        /* reverse */ false);

    ImmutableList<OCamlLibrary> ocamlInput = OCamlUtil.getTransitiveOCamlInput(params.getDeps());

    ImmutableList<SourcePath> allInputs =
        ImmutableList.<SourcePath>builder()
            .addAll(getInput(srcs))
            .addAll(linkableInput.getInputs())
            .build();

    BuildTarget buildTarget =
        isLibrary ? createStaticLibraryBuildTarget(params.getBuildTarget())
            : createOCamlLinkTarget(params.getBuildTarget());

    final BuildRuleParams compileParams = params.copyWithChanges(
        buildTarget,
        /* declaredDeps */ Suppliers.ofInstance(
            ImmutableSortedSet.copyOf(pathResolver.filterBuildRuleInputs(allInputs))),
        /* extraDeps */ Suppliers.ofInstance(ImmutableSortedSet.<BuildRule>of()));

    ImmutableList.Builder<String> flagsBuilder = ImmutableList.builder();
    flagsBuilder.addAll(argFlags);

    ImmutableSortedSet.Builder<BuildRule> compileDepsBuilder = ImmutableSortedSet.naturalOrder();
    ImmutableSortedSet.Builder<BuildRule> bytecodeCompileDepsBuilder =
        ImmutableSortedSet.naturalOrder();
    ImmutableSortedSet.Builder<BuildRule> bytecodeLinkDepsBuilder =
        ImmutableSortedSet.naturalOrder();
    for (OCamlLibrary library : ocamlInput) {
      compileDepsBuilder.addAll(library.getCompileDeps());
      bytecodeCompileDepsBuilder.addAll(library.getBytecodeCompileDeps());
      bytecodeLinkDepsBuilder.addAll(library.getBytecodeLinkDeps());
    }
    OCamlBuildContext ocamlContext =
        OCamlBuildContext.builder(ocamlBuckConfig)
            .setFlags(flagsBuilder.build())
            .setIncludes(includes)
            .setBytecodeIncludes(bytecodeIncludes)
            .setOCamlInput(ocamlInput)
            .setLinkableInput(linkableInput)
            .setBuildTarget(buildTarget)
            .setLibrary(isLibrary)
            .setCxxPreprocessorInput(cxxPreprocessorInputFromDeps)
            .setInput(pathResolver.getAllPaths(getInput(srcs)))
            .setCompileDeps(compileDepsBuilder.build())
            .setBytecodeCompileDeps(bytecodeCompileDepsBuilder.build())
            .setBytecodeLinkDeps(bytecodeLinkDepsBuilder.build())
            .build();

    File baseDir = params.getProjectFilesystem().getRootPath().toAbsolutePath().toFile();
    ImmutableMap<Path, ImmutableList<Path>> mlInput = getMLInputWithDeps(
        baseDir,
        ocamlContext);

    ImmutableList<SourcePath> cInput = getCInput(pathResolver, getInput(srcs));

    OCamlBuildRulesGenerator generator = new OCamlBuildRulesGenerator(
        compileParams,
        pathResolver,
        resolver,
        ocamlContext,
        mlInput,
        cInput,
        ocamlBuckConfig.getCCompiler(),
        ocamlBuckConfig.getCxxCompiler());

    OCamlGeneratedBuildRules result = generator.generate();

    if (isLibrary) {
      return new OCamlStaticLibrary(
          params.copyWithDeps(
              Suppliers.ofInstance(
                  ImmutableSortedSet.<BuildRule>naturalOrder()
                      .addAll(params.getDeclaredDeps())
                      .addAll(result.getRules())
                      .build()),
              Suppliers.ofInstance(params.getExtraDeps())),
          pathResolver,
          compileParams,
          linkerFlags,
          result.getObjectFiles(),
          ocamlContext,
          result.getRules().get(0),
          result.getCompileDeps(),
          result.getBytecodeCompileDeps(),
          ImmutableSortedSet.<BuildRule>naturalOrder()
              .add(result.getBytecodeLink())
              .addAll(pathResolver.filterBuildRuleInputs(result.getObjectFiles()))
              .build());
    } else {
      return new OCamlBinary(
          params.copyWithDeps(
              Suppliers.ofInstance(
                  ImmutableSortedSet.<BuildRule>naturalOrder()
                      .addAll(params.getDeclaredDeps())
                      .addAll(result.getRules())
                      .build()),
              Suppliers.ofInstance(params.getExtraDeps())),
          pathResolver,
          result.getRules().get(0));
    }
  }

  private static ImmutableList<SourcePath> getCInput(
      SourcePathResolver resolver,
      ImmutableList<SourcePath> input) {
    return FluentIterable
        .from(input)
        .filter(OCamlUtil.sourcePathExt(resolver, OCamlCompilables.OCAML_C))
        .toList();
  }

  private static ImmutableMap<Path, ImmutableList<Path>> getMLInputWithDeps(
      File baseDir,
      OCamlBuildContext ocamlContext) {
    OCamlDepToolStep depToolStep = new OCamlDepToolStep(
        ocamlContext.getOcamlDepTool().get(),
        ocamlContext.getMLInput(),
        ocamlContext.getIncludeFlags(/* isBytecode */ false, /* excludeDeps */ true));
    ImmutableList<String> cmd = depToolStep.getShellCommand(null);
    Optional<String> depsString;
    try {
      depsString = executeProcessAndGetStdout(baseDir, cmd);
    } catch (IOException e) {
      throw new HumanReadableException(
          e,
          "Unable to execute ocamldep due to io error: %s",
          Joiner.on(" ").join(cmd));
    } catch (InterruptedException e) {
      throw new HumanReadableException(e,
          "Unable to calculate dependencies. ocamldep is interrupted: %s",
          Joiner.on(" ").join(cmd));
    }
    if (depsString.isPresent()) {
      OCamlDependencyGraphGenerator graphGenerator = new OCamlDependencyGraphGenerator();
      return filterCurrentRuleInput(
          ocamlContext.getMLInput(),
          graphGenerator.generateDependencyMap(depsString.get()));
    } else {
      throw new HumanReadableException("ocamldep execution failed");
    }
  }

  private static ImmutableMap<Path, ImmutableList<Path>> filterCurrentRuleInput(
      final List<Path> mlInput,
      ImmutableMap<Path, ImmutableList<Path>> deps) {
    ImmutableMap.Builder<Path, ImmutableList<Path>> builder = ImmutableMap.builder();
    for (ImmutableMap.Entry<Path, ImmutableList<Path>> entry : deps.entrySet()) {
      if (mlInput.contains(entry.getKey())) {
        builder.put(entry.getKey(),
            FluentIterable.from(entry.getValue())
              .filter(new Predicate<Path>() {
                        @Override
                        public boolean apply(Path input) {
                          return mlInput.contains(input);
                        }
                      }).toList()
            );
      }
    }
    return builder.build();
  }

  private static Optional<String> executeProcessAndGetStdout(
      File baseDir,
      ImmutableList<String> cmd) throws IOException, InterruptedException {
    CapturingPrintStream stdout = new CapturingPrintStream();
    CapturingPrintStream stderr = new CapturingPrintStream();

    ImmutableSet.Builder<ProcessExecutor.Option> options = ImmutableSet.builder();
    options.add(ProcessExecutor.Option.EXPECTING_STD_OUT);
    Console console = new Console(Verbosity.SILENT, stdout, stderr, Ansi.withoutTty());
    ProcessExecutor exe = new ProcessExecutor(console);
    ProcessBuilder processBuilder = new ProcessBuilder(cmd);
    processBuilder.directory(baseDir);
    ProcessExecutor.Result result = exe.execute(
        processBuilder.start(),
        options.build(),
        /* stdin */ Optional.<String>absent(),
        /* timeOutMs */ Optional.<Long>absent(),
        /* timeOutHandler */ Optional.<Function<Process, Void>>absent());
    if (result.getExitCode() != 0) {
      throw new HumanReadableException(stderr.getContentsAsString(StandardCharsets.UTF_8));
    }

    return result.getStdout();
  }
}


File: test/com/facebook/buck/android/NdkCxxPlatformTest.java
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

package com.facebook.buck.android;

import static org.junit.Assert.assertThat;

import com.facebook.buck.cxx.CxxLinkableEnhancer;
import com.facebook.buck.cxx.CxxPreprocessAndCompile;
import com.facebook.buck.cxx.CxxPreprocessMode;
import com.facebook.buck.cxx.CxxPreprocessorInput;
import com.facebook.buck.cxx.CxxSource;
import com.facebook.buck.cxx.CxxSourceRuleFactory;
import com.facebook.buck.cxx.Linker;
import com.facebook.buck.io.AlwaysFoundExecutableFinder;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.model.Pair;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParamsFactory;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.RuleKey;
import com.facebook.buck.rules.RuleKeyBuilderFactory;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.TestSourcePath;
import com.facebook.buck.rules.keys.DefaultRuleKeyBuilderFactory;
import com.facebook.buck.testutil.FakeFileHashCache;
import com.facebook.buck.testutil.FakeProjectFilesystem;
import com.facebook.buck.testutil.integration.DebuggableTemporaryFolder;
import com.facebook.buck.util.environment.Platform;
import com.google.common.base.Optional;
import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;

import org.hamcrest.Matchers;
import org.junit.Rule;
import org.junit.Test;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Map;

public class NdkCxxPlatformTest {

  @Rule
  public DebuggableTemporaryFolder tmp = new DebuggableTemporaryFolder();

  enum Operation {
    PREPROCESS,
    COMPILE,
    PREPROCESS_AND_COMPILE,
  }

  // Create and return some rule keys from a dummy source for the given platforms.
  private ImmutableMap<NdkCxxPlatforms.TargetCpuType, RuleKey> constructCompileRuleKeys(
      Operation operation,
      ImmutableMap<NdkCxxPlatforms.TargetCpuType, NdkCxxPlatform> cxxPlatforms) {
    BuildRuleResolver resolver = new BuildRuleResolver();
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);
    String source = "source.cpp";
    RuleKeyBuilderFactory ruleKeyBuilderFactory =
        new DefaultRuleKeyBuilderFactory(
            FakeFileHashCache.createFromStrings(
                ImmutableMap.<String, String>builder()
                    .put("source.cpp", Strings.repeat("a", 40))
                    .build()),
            pathResolver);
    BuildTarget target = BuildTargetFactory.newInstance("//:target");
    ImmutableMap.Builder<NdkCxxPlatforms.TargetCpuType, RuleKey> ruleKeys =
        ImmutableMap.builder();
    for (Map.Entry<NdkCxxPlatforms.TargetCpuType, NdkCxxPlatform> entry : cxxPlatforms.entrySet()) {
      CxxSourceRuleFactory cxxSourceRuleFactory =
          new CxxSourceRuleFactory(
              BuildRuleParamsFactory.createTrivialBuildRuleParams(target),
              resolver,
              pathResolver,
              entry.getValue().getCxxPlatform(),
              CxxPreprocessorInput.EMPTY,
              ImmutableList.<String>of());
      CxxPreprocessAndCompile rule;
      switch (operation) {
        case PREPROCESS_AND_COMPILE:
          rule =
              cxxSourceRuleFactory.createPreprocessAndCompileBuildRule(
                  resolver,
                  source,
                  CxxSource.of(
                      CxxSource.Type.CXX,
                      new TestSourcePath(source),
                      ImmutableList.<String>of()),
                  CxxSourceRuleFactory.PicType.PIC,
                  CxxPreprocessMode.COMBINED);
          break;
        case PREPROCESS:
          rule =
              cxxSourceRuleFactory.createPreprocessBuildRule(
                  resolver,
                  source,
                  CxxSource.of(
                      CxxSource.Type.CXX,
                      new TestSourcePath(source),
                      ImmutableList.<String>of()),
                  CxxSourceRuleFactory.PicType.PIC);
          break;
        case COMPILE:
          rule =
              cxxSourceRuleFactory.createCompileBuildRule(
                  resolver,
                  source,
                  CxxSource.of(
                      CxxSource.Type.CXX_CPP_OUTPUT,
                      new TestSourcePath(source),
                      ImmutableList.<String>of()),
                  CxxSourceRuleFactory.PicType.PIC);
          break;
        default:
          throw new IllegalStateException();
      }
      RuleKey.Builder builder = ruleKeyBuilderFactory.newInstance(rule);
      ruleKeys.put(entry.getKey(), builder.build());
    }
    return ruleKeys.build();
  }

  // Create and return some rule keys from a dummy source for the given platforms.
  private ImmutableMap<NdkCxxPlatforms.TargetCpuType, RuleKey> constructLinkRuleKeys(
      ImmutableMap<NdkCxxPlatforms.TargetCpuType, NdkCxxPlatform> cxxPlatforms) {
    BuildRuleResolver resolver = new BuildRuleResolver();
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);
    RuleKeyBuilderFactory ruleKeyBuilderFactory =
        new DefaultRuleKeyBuilderFactory(
            FakeFileHashCache.createFromStrings(
                ImmutableMap.<String, String>builder()
                    .put("input.o", Strings.repeat("a", 40))
                    .build()),
            pathResolver);
    BuildTarget target = BuildTargetFactory.newInstance("//:target");
    ImmutableMap.Builder<NdkCxxPlatforms.TargetCpuType, RuleKey> ruleKeys =
        ImmutableMap.builder();
    for (Map.Entry<NdkCxxPlatforms.TargetCpuType, NdkCxxPlatform> entry : cxxPlatforms.entrySet()) {
      BuildRule rule =
          CxxLinkableEnhancer.createCxxLinkableBuildRule(
              entry.getValue().getCxxPlatform(),
              BuildRuleParamsFactory.createTrivialBuildRuleParams(target),
              pathResolver,
              ImmutableList.<String>of(),
              ImmutableList.<String>of(),
              target,
              Linker.LinkType.EXECUTABLE,
              Optional.<String>absent(),
              Paths.get("output"),
              ImmutableList.<SourcePath>of(new TestSourcePath("input.o")),
              Linker.LinkableDepType.SHARED,
              ImmutableList.<BuildRule>of(),
              Optional.<Linker.CxxRuntimeType>absent(),
              Optional.<SourcePath>absent());
      RuleKey.Builder builder = ruleKeyBuilderFactory.newInstance(rule);
      ruleKeys.put(entry.getKey(), builder.build());
    }
    return ruleKeys.build();
  }

  // The important aspects we check for in rule keys is that the host platform and the path
  // to the NDK don't cause changes.
  @Test
  public void checkRootAndPlatformDoNotAffectRuleKeys() throws IOException {

    // Test all major compiler and runtime combinations.
    ImmutableList<Pair<NdkCxxPlatforms.Compiler.Type, NdkCxxPlatforms.CxxRuntime>> configs =
        ImmutableList.of(
            new Pair<>(NdkCxxPlatforms.Compiler.Type.GCC, NdkCxxPlatforms.CxxRuntime.GNUSTL),
            new Pair<>(NdkCxxPlatforms.Compiler.Type.CLANG, NdkCxxPlatforms.CxxRuntime.GNUSTL),
            new Pair<>(NdkCxxPlatforms.Compiler.Type.CLANG, NdkCxxPlatforms.CxxRuntime.LIBCXX));
    for (Pair<NdkCxxPlatforms.Compiler.Type, NdkCxxPlatforms.CxxRuntime> config : configs) {
      Map<String, ImmutableMap<NdkCxxPlatforms.TargetCpuType, RuleKey>>
          preprocessAndCompileRukeKeys = Maps.newHashMap();
      Map<String, ImmutableMap<NdkCxxPlatforms.TargetCpuType, RuleKey>>
          preprocessRukeKeys = Maps.newHashMap();
      Map<String, ImmutableMap<NdkCxxPlatforms.TargetCpuType, RuleKey>>
          compileRukeKeys = Maps.newHashMap();
      Map<String, ImmutableMap<NdkCxxPlatforms.TargetCpuType, RuleKey>>
          linkRukeKeys = Maps.newHashMap();

      // Iterate building up rule keys for combinations of different platforms and NDK root
      // directories.
      for (String dir : ImmutableList.of("something", "something else")) {
        for (Platform platform :
            ImmutableList.of(Platform.LINUX, Platform.MACOS, Platform.WINDOWS)) {
          tmp.create();
          Path root = tmp.newFolder(dir).toPath();
          FakeProjectFilesystem filesystem = new FakeProjectFilesystem(root.toFile());
          filesystem.writeContentsToPath("something", Paths.get("RELEASE.TXT"));
          ImmutableMap<NdkCxxPlatforms.TargetCpuType, NdkCxxPlatform> platforms =
              NdkCxxPlatforms.getPlatforms(
                  filesystem,
                  ImmutableNdkCxxPlatforms.Compiler.builder()
                      .setType(config.getFirst())
                      .setVersion("gcc-version")
                      .setGccVersion("clang-version")
                      .build(),
                  NdkCxxPlatforms.CxxRuntime.GNUSTL,
                  "target-app-platform",
                  platform,
                  new AlwaysFoundExecutableFinder());
          preprocessAndCompileRukeKeys.put(
              String.format("NdkCxxPlatform(%s, %s)", dir, platform),
              constructCompileRuleKeys(Operation.PREPROCESS_AND_COMPILE, platforms));
          preprocessRukeKeys.put(
              String.format("NdkCxxPlatform(%s, %s)", dir, platform),
              constructCompileRuleKeys(Operation.PREPROCESS, platforms));
          compileRukeKeys.put(
              String.format("NdkCxxPlatform(%s, %s)", dir, platform),
              constructCompileRuleKeys(Operation.COMPILE, platforms));
          linkRukeKeys.put(
              String.format("NdkCxxPlatform(%s, %s)", dir, platform),
              constructLinkRuleKeys(platforms));
          tmp.delete();
        }
      }

      // If everything worked, we should be able to collapse all the generated rule keys down
      // to a singleton set.
      assertThat(
          Arrays.toString(preprocessAndCompileRukeKeys.entrySet().toArray()),
          Sets.newHashSet(preprocessAndCompileRukeKeys.values()),
          Matchers.hasSize(1));
      assertThat(
          Arrays.toString(preprocessRukeKeys.entrySet().toArray()),
          Sets.newHashSet(preprocessRukeKeys.values()),
          Matchers.hasSize(1));
      assertThat(
          Arrays.toString(compileRukeKeys.entrySet().toArray()),
          Sets.newHashSet(compileRukeKeys.values()),
          Matchers.hasSize(1));
      assertThat(
          Arrays.toString(linkRukeKeys.entrySet().toArray()),
          Sets.newHashSet(linkRukeKeys.values()),
          Matchers.hasSize(1));
    }

  }

}


File: test/com/facebook/buck/cxx/CxxBinaryDescriptionTest.java
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

package com.facebook.buck.cxx;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

import com.facebook.buck.android.AndroidPackageable;
import com.facebook.buck.android.AndroidPackageableCollector;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.model.HasBuildTarget;
import com.facebook.buck.python.PythonPackageComponents;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleParamsFactory;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.FakeBuildRule;
import com.facebook.buck.rules.FakeBuildRuleParamsBuilder;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TestSourcePath;
import com.facebook.buck.rules.coercer.SourceWithFlags;
import com.facebook.buck.shell.Genrule;
import com.facebook.buck.shell.GenruleBuilder;
import com.facebook.buck.testutil.FakeProjectFilesystem;
import com.google.common.base.Optional;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;

import org.junit.Test;

import java.nio.file.Path;
import java.nio.file.Paths;

public class CxxBinaryDescriptionTest {

  private static FakeBuildRule createFakeBuildRule(
      String target,
      SourcePathResolver resolver,
      BuildRule... deps) {
    return new FakeBuildRule(
        new FakeBuildRuleParamsBuilder(BuildTargetFactory.newInstance(target))
            .setDeps(ImmutableSortedSet.copyOf(deps))
            .build(),
        resolver);
  }

  @Test
  @SuppressWarnings("PMD.UseAssertTrueInsteadOfAssertEquals")
  public void createBuildRule() {
    ProjectFilesystem projectFilesystem = new FakeProjectFilesystem();
    BuildRuleResolver resolver = new BuildRuleResolver();
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);
    CxxPlatform cxxPlatform = CxxBinaryBuilder.createDefaultPlatform();

    // Setup a genrule the generates a header we'll list.
    String genHeaderName = "test/foo.h";
    BuildTarget genHeaderTarget = BuildTargetFactory.newInstance("//:genHeader");
    Genrule genHeader = (Genrule) GenruleBuilder
        .newGenruleBuilder(genHeaderTarget)
        .setOut(genHeaderName)
        .build(resolver);

    // Setup a genrule the generates a source we'll list.
    String genSourceName = "test/foo.cpp";
    BuildTarget genSourceTarget = BuildTargetFactory.newInstance("//:genSource");
    Genrule genSource = (Genrule) GenruleBuilder
        .newGenruleBuilder(genSourceTarget)
        .setOut(genSourceName)
        .build(resolver);

    // Setup a C/C++ library that we'll depend on form the C/C++ binary description.
    final BuildRule header = createFakeBuildRule("//:header", pathResolver);
    final BuildRule headerSymlinkTree = createFakeBuildRule("//:symlink", pathResolver);
    final Path headerSymlinkTreeRoot = Paths.get("symlink/tree/root");
    final BuildRule archive = createFakeBuildRule("//:archive", pathResolver);
    final Path archiveOutput = Paths.get("output/path/lib.a");
    BuildTarget depTarget = BuildTargetFactory.newInstance("//:dep");
    BuildRuleParams depParams = BuildRuleParamsFactory.createTrivialBuildRuleParams(depTarget);
    AbstractCxxLibrary dep = new AbstractCxxLibrary(depParams, pathResolver) {

      @Override
      public CxxPreprocessorInput getCxxPreprocessorInput(
          CxxPlatform cxxPlatform,
          HeaderVisibility headerVisibility) {
        return CxxPreprocessorInput.builder()
            .addRules(
                header.getBuildTarget(),
                headerSymlinkTree.getBuildTarget())
            .addIncludeRoots(headerSymlinkTreeRoot)
            .build();
      }

      @Override
      public ImmutableMap<BuildTarget, CxxPreprocessorInput> getTransitiveCxxPreprocessorInput(
          CxxPlatform cxxPlatform,
          HeaderVisibility headerVisibility) {
        return ImmutableMap.of(
            getBuildTarget(),
            getCxxPreprocessorInput(cxxPlatform, headerVisibility));
      }

      @Override
      public NativeLinkableInput getNativeLinkableInput(
          CxxPlatform cxxPlatform,
          Linker.LinkableDepType type) {
        return NativeLinkableInput.of(
            ImmutableList.<SourcePath>of(
                new BuildTargetSourcePath(getProjectFilesystem(), archive.getBuildTarget())),
            ImmutableList.of(archiveOutput.toString()));
      }

      @Override
      public Optional<Linker.LinkableDepType> getPreferredLinkage(CxxPlatform cxxPlatform) {
        return Optional.absent();
      }

      @Override
      public PythonPackageComponents getPythonPackageComponents(CxxPlatform cxxPlatform) {
        return PythonPackageComponents.of(
            ImmutableMap.<Path, SourcePath>of(),
            ImmutableMap.<Path, SourcePath>of(),
            ImmutableMap.<Path, SourcePath>of(),
            ImmutableSet.<SourcePath>of(),
            Optional.<Boolean>absent());
      }

      @Override
      public Iterable<AndroidPackageable> getRequiredPackageables() {
        return ImmutableList.of();
      }

      @Override
      public void addToCollector(AndroidPackageableCollector collector) {}

      @Override
      public ImmutableMap<String, SourcePath> getSharedLibraries(CxxPlatform cxxPlatform) {
        return ImmutableMap.of();
      }

      @Override
      public boolean isTestedBy(BuildTarget buildTarget) {
        return false;
      }
    };
    resolver.addAllToIndex(ImmutableList.of(header, headerSymlinkTree, archive, dep));

    // Setup the build params we'll pass to description when generating the build rules.
    BuildTarget target = BuildTargetFactory.newInstance("//:rule");
    CxxBinaryBuilder cxxBinaryBuilder =
        (CxxBinaryBuilder) new CxxBinaryBuilder(target)
              .setSrcs(
                  ImmutableList.of(
                      SourceWithFlags.of(new TestSourcePath("test/bar.cpp")),
                      SourceWithFlags.of(
                          new BuildTargetSourcePath(
                              projectFilesystem,
                              genSource.getBuildTarget()))))
              .setHeaders(
                  ImmutableList.<SourcePath>of(
                      new TestSourcePath("test/bar.h"),
                      new BuildTargetSourcePath(projectFilesystem, genHeader.getBuildTarget())))
              .setDeps(ImmutableSortedSet.of(dep.getBuildTarget()));
    CxxBinary binRule = (CxxBinary) cxxBinaryBuilder.build(resolver);
    CxxLink rule = binRule.getRule();
    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            cxxBinaryBuilder.createBuildRuleParams(resolver, projectFilesystem, TargetGraph.EMPTY),
            resolver,
            pathResolver,
            cxxPlatform,
            CxxPreprocessorInput.EMPTY,
            ImmutableList.<String>of());

    // Check that link rule has the expected deps: the object files for our sources and the
    // archive from the dependency.
    assertEquals(
        ImmutableSet.of(
            cxxSourceRuleFactory.createCompileBuildTarget(
                "test/bar.cpp",
                CxxSourceRuleFactory.PicType.PDC),
            cxxSourceRuleFactory.createCompileBuildTarget(
                genSourceName,
                CxxSourceRuleFactory.PicType.PDC),
            archive.getBuildTarget()),
        FluentIterable.from(rule.getDeps())
            .transform(HasBuildTarget.TO_TARGET)
            .toSet());

    // Verify that the preproces rule for our user-provided source has correct deps setup
    // for the various header rules.
    BuildRule preprocessRule1 = resolver.getRule(
        cxxSourceRuleFactory.createPreprocessBuildTarget(
            "test/bar.cpp",
            CxxSource.Type.CXX,
            CxxSourceRuleFactory.PicType.PDC));
    assertEquals(
        ImmutableSet.of(
            genHeaderTarget,
            headerSymlinkTree.getBuildTarget(),
            header.getBuildTarget(),
            CxxDescriptionEnhancer.createHeaderSymlinkTreeTarget(
                target,
                cxxPlatform.getFlavor(),
                HeaderVisibility.PRIVATE)),
        FluentIterable.from(preprocessRule1.getDeps())
            .transform(HasBuildTarget.TO_TARGET)
            .toSet());

    // Verify that the compile rule for our user-provided source has correct deps setup
    // for the various header rules.
    BuildRule compileRule1 = resolver.getRule(
        cxxSourceRuleFactory.createCompileBuildTarget(
            "test/bar.cpp",
            CxxSourceRuleFactory.PicType.PDC));
    assertNotNull(compileRule1);
    assertEquals(
        ImmutableSet.of(
            preprocessRule1.getBuildTarget()),
        FluentIterable.from(compileRule1.getDeps())
            .transform(HasBuildTarget.TO_TARGET)
            .toSet());

    // Verify that the preproces rule for our user-provided source has correct deps setup
    // for the various header rules.
    BuildRule preprocessRule2 = resolver.getRule(
        cxxSourceRuleFactory.createPreprocessBuildTarget(
            genSourceName,
            CxxSource.Type.CXX,
            CxxSourceRuleFactory.PicType.PDC));
    assertEquals(
        ImmutableSet.of(
            genHeaderTarget,
            genSourceTarget,
            headerSymlinkTree.getBuildTarget(),
            header.getBuildTarget(),
            CxxDescriptionEnhancer.createHeaderSymlinkTreeTarget(
                target,
                cxxPlatform.getFlavor(),
                HeaderVisibility.PRIVATE)),
        FluentIterable.from(preprocessRule2.getDeps())
            .transform(HasBuildTarget.TO_TARGET)
            .toSet());

    // Verify that the compile rule for our genrule-generated source has correct deps setup
    // for the various header rules and the generating genrule.
    BuildRule compileRule2 = resolver.getRule(
        cxxSourceRuleFactory.createCompileBuildTarget(
            genSourceName,
            CxxSourceRuleFactory.PicType.PDC));
    assertNotNull(compileRule2);
    assertEquals(
        ImmutableSet.of(
            preprocessRule2.getBuildTarget()),
        FluentIterable.from(compileRule2.getDeps())
            .transform(HasBuildTarget.TO_TARGET)
            .toSet());
  }

}


File: test/com/facebook/buck/cxx/CxxCompilationDatabaseTest.java
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
package com.facebook.buck.cxx;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.rules.BuildContext;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildableContext;
import com.facebook.buck.rules.FakeBuildContext;
import com.facebook.buck.rules.FakeBuildRuleParamsBuilder;
import com.facebook.buck.rules.FakeBuildableContext;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.TestSourcePath;
import com.facebook.buck.step.ExecutionContext;
import com.facebook.buck.step.Step;
import com.facebook.buck.step.TestExecutionContext;
import com.facebook.buck.step.fs.MkdirStep;
import com.facebook.buck.testutil.FakeProjectFilesystem;
import com.facebook.buck.testutil.MoreAsserts;
import com.facebook.buck.testutil.TargetGraphFactory;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;

import org.junit.Test;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

public class CxxCompilationDatabaseTest {

  private void runCombinedTest(
      CxxPreprocessMode strategy,
      ImmutableList<String> expectedArguments) {
    BuildTarget testBuildTarget = BuildTarget
        .builder(BuildTargetFactory.newInstance("//foo:baz"))
        .addAllFlavors(
            ImmutableSet.of(CxxCompilationDatabase.COMPILATION_DATABASE))
        .build();
    BuildRuleParams testBuildRuleParams = new FakeBuildRuleParamsBuilder(testBuildTarget)
        .setTargetGraph(
            TargetGraphFactory.newInstance(
                new CxxLibraryBuilder(testBuildTarget).build()))
        .build();

    BuildRuleResolver testBuildRuleResolver = new BuildRuleResolver();
    SourcePathResolver testSourcePathResolver = new SourcePathResolver(testBuildRuleResolver);

    BuildTarget preprocessTarget = BuildTarget
        .builder(testBuildRuleParams.getBuildTarget().getUnflavoredBuildTarget())
        .addFlavors(
            ImmutableFlavor.of("preprocess-test.cpp"))
        .build();
    BuildTarget compileTarget = BuildTarget
        .builder(testBuildRuleParams.getBuildTarget().getUnflavoredBuildTarget())
        .addFlavors(
            ImmutableFlavor.of("compile-test.cpp"))
        .build();

    ImmutableSortedSet.Builder<CxxPreprocessAndCompile> rules = ImmutableSortedSet.naturalOrder();
    CxxPreprocessAndCompileStep.Operation operation;
    BuildRuleParams compileBuildRuleParams;
    switch (strategy) {
      case SEPARATE:
        operation = CxxPreprocessAndCompileStep.Operation.COMPILE;
        CxxPreprocessAndCompile preprocessRule = new CxxPreprocessAndCompile(
            new FakeBuildRuleParamsBuilder(preprocessTarget).build(),
            testSourcePathResolver,
            operation,
            Optional.<Tool>of(new HashedFileTool(Paths.get("preprocessor"))),
            Optional.of(ImmutableList.<String>of()),
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            Paths.get("test.o"),
            new TestSourcePath("test.cpp"),
            CxxSource.Type.CXX,
            ImmutableList.of(
                Paths.get("foo/bar"),
                Paths.get("test")),
            ImmutableList.<Path>of(),
            ImmutableList.<Path>of(),
            CxxHeaders.builder().build(),
            CxxPlatforms.DEFAULT_DEBUG_PATH_SANITIZER);
        rules.add(preprocessRule);
        compileBuildRuleParams = new FakeBuildRuleParamsBuilder(compileTarget)
            .setDeps(ImmutableSortedSet.<BuildRule>of(preprocessRule))
            .build();
        break;
      case COMBINED:
        operation = CxxPreprocessAndCompileStep.Operation.COMPILE_MUNGE_DEBUGINFO;
        compileBuildRuleParams = new FakeBuildRuleParamsBuilder(compileTarget).build();
        break;
      case PIPED:
        operation = CxxPreprocessAndCompileStep.Operation.PIPED_PREPROCESS_AND_COMPILE;
        compileBuildRuleParams = new FakeBuildRuleParamsBuilder(compileTarget).build();
        break;
      default:
        throw new RuntimeException("Invalid strategy");
    }
    rules.add(
        new CxxPreprocessAndCompile(
            compileBuildRuleParams,
            testSourcePathResolver,
            operation,
            Optional.<Tool>of(new HashedFileTool(Paths.get("preprocessor"))),
            Optional.of(ImmutableList.<String>of()),
            Optional.<Tool>of(new HashedFileTool(Paths.get("compiler"))),
            Optional.of(ImmutableList.<String>of()),
            Paths.get("test.o"),
            new TestSourcePath("test.cpp"),
            CxxSource.Type.CXX,
            ImmutableList.of(
                Paths.get("foo/bar"),
                Paths.get("test")),
            ImmutableList.<Path>of(),
            ImmutableList.<Path>of(),
            CxxHeaders.builder().build(),
            CxxPlatforms.DEFAULT_DEBUG_PATH_SANITIZER));

    CxxCompilationDatabase compilationDatabase = CxxCompilationDatabase.createCompilationDatabase(
        testBuildRuleParams,
        testSourcePathResolver,
        strategy,
        rules.build());

    assertEquals(
        "getPathToOutput() should be a function of the build target.",
        Paths.get("buck-out/gen/foo/__baz#compilation-database.json"),
        compilationDatabase.getPathToOutput());

    BuildContext buildContext = FakeBuildContext.NOOP_CONTEXT;
    BuildableContext buildableContext = new FakeBuildableContext();
    List<Step> buildSteps = compilationDatabase.getBuildSteps(buildContext, buildableContext);
    assertEquals(2, buildSteps.size());
    assertTrue(buildSteps.get(0) instanceof MkdirStep);
    assertTrue(buildSteps.get(1) instanceof
            CxxCompilationDatabase.GenerateCompilationCommandsJson);

    final String root = "/Users/user/src";
    final Path fakeRoot = Paths.get(root);
    ProjectFilesystem projectFilesystem = new FakeProjectFilesystem() {
      @Override
      public Path resolve(Path relativePath) {
        return fakeRoot.resolve(relativePath);
      }
    };
    ExecutionContext context = TestExecutionContext
        .newBuilder()
        .setProjectFilesystem(projectFilesystem)
        .build();
    CxxCompilationDatabase.GenerateCompilationCommandsJson step =
        (CxxCompilationDatabase.GenerateCompilationCommandsJson) buildSteps.get(1);
    Iterable<CxxCompilationDatabaseEntry> observedEntries =
        step.createEntries(context);
    Iterable<CxxCompilationDatabaseEntry> expectedEntries =
        ImmutableList.of(
          new CxxCompilationDatabaseEntry(
              root + "/foo",
              root + "/test.cpp",
              expectedArguments));
    MoreAsserts.assertIterablesEquals(expectedEntries, observedEntries);
  }

  @Test
  public void testCompilationDatabseWithCombinedPreprocessAndCompileStrategy() {
    runCombinedTest(CxxPreprocessMode.COMBINED,
        ImmutableList.of(
            "compiler",
            "-I",
            "foo/bar",
            "-I",
            "test",
            "-x",
            "c++",
            "-c",
            "test.cpp",
            "-o",
            "test.o"));
  }

  @Test
  public void testCompilationDatabseWithPipedPreprocessAndCompileStrategy() {
    runCombinedTest(CxxPreprocessMode.PIPED,
        ImmutableList.of(
            "compiler",
            "-x",
            "c++",
            "-c",
            "-I",
            "foo/bar",
            "-I",
            "test",
            "-o",
            "test.o",
            "test.cpp"));
  }

  @Test
  public void testCompilationDatabseWithSeperatedPreprocessAndCompileStrategy() {
    BuildTarget testBuildTarget = BuildTarget
        .builder(BuildTargetFactory.newInstance("//foo:baz"))
        .addAllFlavors(
            ImmutableSet.of(CxxCompilationDatabase.COMPILATION_DATABASE))
        .build();
    BuildRuleParams testBuildRuleParams = new FakeBuildRuleParamsBuilder(testBuildTarget)
        .setTargetGraph(
            TargetGraphFactory.newInstance(
                new CxxLibraryBuilder(testBuildTarget).build()))
        .build();

    BuildRuleResolver testBuildRuleResolver = new BuildRuleResolver();
    SourcePathResolver testSourcePathResolver = new SourcePathResolver(testBuildRuleResolver);

    BuildTarget preprocessTarget = BuildTarget
        .builder(testBuildRuleParams.getBuildTarget().getUnflavoredBuildTarget())
        .addFlavors(
            ImmutableFlavor.of("preprocess-test.cpp"))
        .build();
    BuildRuleParams preprocessBuildRuleParams = new FakeBuildRuleParamsBuilder(preprocessTarget)
        .build();
    CxxPreprocessAndCompile testPreprocessRule = new CxxPreprocessAndCompile(
        preprocessBuildRuleParams,
        testSourcePathResolver,
        CxxPreprocessAndCompileStep.Operation.PREPROCESS,
        Optional.<Tool>of(new HashedFileTool(Paths.get("compiler"))),
        Optional.of(ImmutableList.<String>of()),
        Optional.<Tool>absent(),
        Optional.<ImmutableList<String>>absent(),
        Paths.get("test.ii"),
        new TestSourcePath("test.cpp"),
        CxxSource.Type.CXX_CPP_OUTPUT,
        ImmutableList.of(
            Paths.get("foo/bar"),
            Paths.get("test")),
        ImmutableList.<Path>of(),
        ImmutableList.<Path>of(),
        CxxHeaders.builder().build(),
        CxxPlatforms.DEFAULT_DEBUG_PATH_SANITIZER);

    BuildTarget compileTarget = BuildTarget
        .builder(testBuildRuleParams.getBuildTarget().getUnflavoredBuildTarget())
        .addFlavors(
            ImmutableFlavor.of("compile-test.cpp"))
        .build();
    BuildRuleParams compileBuildRuleParams = new FakeBuildRuleParamsBuilder(compileTarget)
        .setDeps(ImmutableSortedSet.<BuildRule>of(testPreprocessRule))
        .build();
    CxxPreprocessAndCompile testCompileRule = new CxxPreprocessAndCompile(
        compileBuildRuleParams,
        testSourcePathResolver,
        CxxPreprocessAndCompileStep.Operation.COMPILE,
        Optional.<Tool>absent(),
        Optional.<ImmutableList<String>>absent(),
        Optional.<Tool>of(new HashedFileTool(Paths.get("compiler"))),
        Optional.of(ImmutableList.<String>of()),
        Paths.get("test.o"),
        new TestSourcePath("test.ii"),
        CxxSource.Type.CXX_CPP_OUTPUT,
        ImmutableList.<Path>of(),
        ImmutableList.<Path>of(),
        ImmutableList.<Path>of(),
        CxxHeaders.builder().build(),
        CxxPlatforms.DEFAULT_DEBUG_PATH_SANITIZER);

    CxxCompilationDatabase compilationDatabase = CxxCompilationDatabase.createCompilationDatabase(
        testBuildRuleParams,
        testSourcePathResolver,
        CxxPreprocessMode.SEPARATE,
        ImmutableSortedSet.of(testPreprocessRule, testCompileRule));

    assertEquals(
        "getPathToOutput() should be a function of the build target.",
        Paths.get("buck-out/gen/foo/__baz#compilation-database.json"),
        compilationDatabase.getPathToOutput());

    BuildContext buildContext = FakeBuildContext.NOOP_CONTEXT;
    BuildableContext buildableContext = new FakeBuildableContext();
    List<Step> buildSteps = compilationDatabase.getBuildSteps(buildContext, buildableContext);
    assertEquals(2, buildSteps.size());
    assertTrue(buildSteps.get(0) instanceof MkdirStep);
    assertTrue(buildSteps.get(1) instanceof
            CxxCompilationDatabase.GenerateCompilationCommandsJson);

    final String root = "/Users/user/src";
    final Path fakeRoot = Paths.get(root);
    ProjectFilesystem projectFilesystem = new FakeProjectFilesystem() {
      @Override
      public Path resolve(Path relativePath) {
        return fakeRoot.resolve(relativePath);
      }
    };
    ExecutionContext context = TestExecutionContext
        .newBuilder()
        .setProjectFilesystem(projectFilesystem)
        .build();
    CxxCompilationDatabase.GenerateCompilationCommandsJson step =
        (CxxCompilationDatabase.GenerateCompilationCommandsJson) buildSteps.get(1);
    Iterable<CxxCompilationDatabaseEntry> observedEntries =
        step.createEntries(context);
    Iterable<CxxCompilationDatabaseEntry> expectedEntries =
        ImmutableList.of(
            new CxxCompilationDatabaseEntry(
                root + "/foo",
                root + "/test.cpp",
                ImmutableList.of(
                    "compiler",
                    "-x",
                    "c++-cpp-output",
                    "-c",
                    "-I",
                    "foo/bar",
                    "-I",
                    "test",
                    "-o",
                    "test.o",
                    "test.cpp")));
    MoreAsserts.assertIterablesEquals(expectedEntries, observedEntries);
  }
}


File: test/com/facebook/buck/cxx/CxxDescriptionEnhancerTest.java
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

package com.facebook.buck.cxx;

import static org.hamcrest.Matchers.allOf;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.hasItems;
import static org.hamcrest.Matchers.not;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertThat;

import com.facebook.buck.cli.FakeBuckConfig;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleParamsFactory;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.FakeBuildRule;
import com.facebook.buck.rules.FakeBuildRuleParamsBuilder;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SymlinkTree;
import com.facebook.buck.rules.TestSourcePath;
import com.facebook.buck.shell.Genrule;
import com.facebook.buck.shell.GenruleBuilder;
import com.facebook.buck.testutil.FakeProjectFilesystem;
import com.google.common.base.Predicates;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.io.Files;

import org.junit.Test;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;

public class CxxDescriptionEnhancerTest {

  @Test
  public void createLexYaccBuildRules() throws IOException {
    BuildRuleResolver resolver = new BuildRuleResolver();

    // Setup our C++ buck config with the paths to the lex/yacc binaries.
    FakeProjectFilesystem filesystem = new FakeProjectFilesystem();
    Path lexPath = Paths.get("lex");
    filesystem.touch(lexPath);
    Path yaccPath = Paths.get("yacc");
    filesystem.touch(yaccPath);
    FakeBuckConfig buckConfig = new FakeBuckConfig(
        ImmutableMap.of(
            "cxx", ImmutableMap.of(
                "lex", lexPath.toString(),
                "yacc", yaccPath.toString())),
        filesystem);
    CxxPlatform cxxBuckConfig = DefaultCxxPlatforms.build(new CxxBuckConfig(buckConfig));

    // Setup the target name and build params.
    BuildTarget target = BuildTargetFactory.newInstance("//:test");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);

    // Setup a genrule that generates our lex source.
    String lexSourceName = "test.ll";
    BuildTarget genruleTarget = BuildTargetFactory.newInstance("//:genrule_lex");
    Genrule genrule = (Genrule) GenruleBuilder
        .newGenruleBuilder(genruleTarget)
        .setOut(lexSourceName)
        .build(resolver);
    SourcePath lexSource = new BuildTargetSourcePath(filesystem, genrule.getBuildTarget());

    // Use a regular path for our yacc source.
    String yaccSourceName = "test.yy";
    SourcePath yaccSource = new TestSourcePath(yaccSourceName);

    // Build the rules.
    CxxHeaderSourceSpec actual = CxxDescriptionEnhancer.createLexYaccBuildRules(
        params,
        resolver,
        cxxBuckConfig,
        ImmutableList.<String>of(),
        ImmutableMap.of(lexSourceName, lexSource),
        ImmutableList.<String>of(),
        ImmutableMap.of(yaccSourceName, yaccSource));

    // Grab the generated lex rule and verify it has the genrule as a dep.
    Lex lex = (Lex) resolver.getRule(
        CxxDescriptionEnhancer.createLexBuildTarget(target, lexSourceName));
    assertNotNull(lex);
    assertEquals(
        ImmutableSortedSet.<BuildRule>of(genrule),
        lex.getDeps());

    // Grab the generated yacc rule and verify it has no deps.
    Yacc yacc = (Yacc) resolver.getRule(
        CxxDescriptionEnhancer.createYaccBuildTarget(target, yaccSourceName));
    assertNotNull(yacc);
    assertEquals(
        ImmutableSortedSet.<BuildRule>of(),
        yacc.getDeps());

    // Check the header/source spec is correct.
    Path lexOutputSource = CxxDescriptionEnhancer.getLexSourceOutputPath(target, lexSourceName);
    Path lexOutputHeader = CxxDescriptionEnhancer.getLexHeaderOutputPath(target, lexSourceName);
    Path yaccOutputPrefix =
        CxxDescriptionEnhancer.getYaccOutputPrefix(
            target,
            Files.getNameWithoutExtension(yaccSourceName));
    Path yaccOutputSource = Yacc.getSourceOutputPath(yaccOutputPrefix);
    Path yaccOutputHeader = Yacc.getHeaderOutputPath(yaccOutputPrefix);
    CxxHeaderSourceSpec expected =
        CxxHeaderSourceSpec.of(
            ImmutableMap.<Path, SourcePath>of(
                target.getBasePath().resolve(lexSourceName + ".h"),
                new BuildTargetSourcePath(filesystem, lex.getBuildTarget(), lexOutputHeader),
                target.getBasePath().resolve(yaccSourceName + ".h"),
                new BuildTargetSourcePath(filesystem, yacc.getBuildTarget(), yaccOutputHeader)),
            ImmutableMap.of(
                lexSourceName + ".cc",
                CxxSource.of(
                    CxxSource.Type.CXX,
                    new BuildTargetSourcePath(filesystem, lex.getBuildTarget(), lexOutputSource),
                    ImmutableList.<String>of()),
                yaccSourceName + ".cc",
                CxxSource.of(
                    CxxSource.Type.CXX,
                    new BuildTargetSourcePath(filesystem, yacc.getBuildTarget(), yaccOutputSource),
                    ImmutableList.<String>of())));
    assertEquals(expected, actual);
  }

  @Test
  public void libraryTestIncludesPrivateHeadersOfLibraryUnderTest() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());

    BuildTarget libTarget = BuildTargetFactory.newInstance("//:lib");
    BuildTarget testTarget = BuildTargetFactory.newInstance("//:test");

    BuildRuleParams libParams = BuildRuleParamsFactory.createTrivialBuildRuleParams(libTarget);
    FakeCxxLibrary libRule = new FakeCxxLibrary(
        libParams,
        pathResolver,
        BuildTargetFactory.newInstance("//:header"),
        BuildTargetFactory.newInstance("//:symlink"),
        Paths.get("symlink/tree/lib"),
        BuildTargetFactory.newInstance("//:privateheader"),
        BuildTargetFactory.newInstance("//:privatesymlink"),
        Paths.get("private/symlink/tree/lib"),
        new FakeBuildRule("//:archive", pathResolver),
        Paths.get("output/path/lib.a"),
        new FakeBuildRule("//:shared", pathResolver),
        Paths.get("output/path/lib.so"),
        "lib.so",
        // Ensure the test is listed as a dep of the lib.
        ImmutableSortedSet.of(testTarget)
    );

    BuildRuleParams testParams = new FakeBuildRuleParamsBuilder(testTarget)
        .setDeps(ImmutableSortedSet.<BuildRule>of(libRule))
        .build();

    CxxPreprocessorInput combinedInput = CxxDescriptionEnhancer.combineCxxPreprocessorInput(
        testParams,
        CxxPlatformUtils.DEFAULT_PLATFORM,
        ImmutableMultimap.<CxxSource.Type, String>of(),
        ImmutableList.<SourcePath>of(),
        ImmutableList.<SymlinkTree>of(),
        ImmutableList.<Path>of(),
        CxxPreprocessables.getTransitiveCxxPreprocessorInput(
            CxxPlatformUtils.DEFAULT_PLATFORM,
            FluentIterable.from(testParams.getDeps())
                .filter(Predicates.instanceOf(CxxPreprocessorDep.class))));

    assertThat(
        "Test of library should include both public and private headers",
        combinedInput.getIncludeRoots(),
        hasItems(
            Paths.get("symlink/tree/lib"),
            Paths.get("private/symlink/tree/lib")));
  }

  @Test
  public void nonTestLibraryDepDoesNotIncludePrivateHeadersOfLibrary() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());

    BuildTarget libTarget = BuildTargetFactory.newInstance("//:lib");

    BuildRuleParams libParams = BuildRuleParamsFactory.createTrivialBuildRuleParams(libTarget);
    FakeCxxLibrary libRule = new FakeCxxLibrary(
        libParams,
        pathResolver,
        BuildTargetFactory.newInstance("//:header"),
        BuildTargetFactory.newInstance("//:symlink"),
        Paths.get("symlink/tree/lib"),
        BuildTargetFactory.newInstance("//:privateheader"),
        BuildTargetFactory.newInstance("//:privatesymlink"),
        Paths.get("private/symlink/tree/lib"),
        new FakeBuildRule("//:archive", pathResolver),
        Paths.get("output/path/lib.a"),
        new FakeBuildRule("//:shared", pathResolver),
        Paths.get("output/path/lib.so"),
        "lib.so",
        // This library has no tests.
        ImmutableSortedSet.<BuildTarget>of()
    );

    BuildTarget otherLibDepTarget = BuildTargetFactory.newInstance("//:other");
    BuildRuleParams otherLibDepParams = new FakeBuildRuleParamsBuilder(otherLibDepTarget)
        .setDeps(ImmutableSortedSet.<BuildRule>of(libRule))
        .build();

    CxxPreprocessorInput otherInput = CxxDescriptionEnhancer.combineCxxPreprocessorInput(
        otherLibDepParams,
        CxxPlatformUtils.DEFAULT_PLATFORM,
        ImmutableMultimap.<CxxSource.Type, String>of(),
        ImmutableList.<SourcePath>of(),
        ImmutableList.<SymlinkTree>of(),
        ImmutableList.<Path>of(),
        CxxPreprocessables.getTransitiveCxxPreprocessorInput(
            CxxPlatformUtils.DEFAULT_PLATFORM,
            FluentIterable.from(otherLibDepParams.getDeps())
                .filter(Predicates.instanceOf(CxxPreprocessorDep.class))));

    assertThat(
        "Non-test rule with library dep should include public and not private headers",
        otherInput.getIncludeRoots(),
        allOf(
            hasItem(Paths.get("symlink/tree/lib")),
            not(hasItem(Paths.get("private/symlink/tree/lib")))));
  }

  @Test
  public void buildTargetsWithDifferentFlavorsProduceDifferentDefaultSonames() {
    BuildTarget target1 = BuildTargetFactory.newInstance("//:rule#one");
    BuildTarget target2 = BuildTargetFactory.newInstance("//:rule#two");
    assertNotEquals(
        CxxDescriptionEnhancer.getDefaultSharedLibrarySoname(
            target1,
            CxxPlatformUtils.DEFAULT_PLATFORM),
        CxxDescriptionEnhancer.getDefaultSharedLibrarySoname(
            target2,
            CxxPlatformUtils.DEFAULT_PLATFORM));
  }

}


File: test/com/facebook/buck/cxx/CxxPreprocessAndCompileTest.java
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

package com.facebook.buck.cxx;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;

import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.rules.AbstractBuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleParamsFactory;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.keys.DefaultRuleKeyBuilderFactory;
import com.facebook.buck.rules.RuleKey;
import com.facebook.buck.rules.RuleKeyBuilderFactory;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.TestSourcePath;
import com.facebook.buck.testutil.FakeFileHashCache;
import com.google.common.base.Optional;
import com.google.common.base.Strings;
import com.google.common.collect.ImmutableBiMap;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;

import org.junit.Test;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;

public class CxxPreprocessAndCompileTest {

  private static final Tool DEFAULT_PREPROCESSOR = new HashedFileTool(Paths.get("preprocessor"));
  private static final Tool DEFAULT_COMPILER = new HashedFileTool(Paths.get("compiler"));
  private static final ImmutableList<String> DEFAULT_FLAGS =
      ImmutableList.of("-fsanitize=address");
  private static final Path DEFAULT_OUTPUT = Paths.get("test.o");
  private static final SourcePath DEFAULT_INPUT = new TestSourcePath("test.cpp");
  private static final CxxSource.Type DEFAULT_INPUT_TYPE = CxxSource.Type.CXX;
  private static final CxxHeaders DEFAULT_INCLUDES =
      CxxHeaders.builder()
          .putNameToPathMap(Paths.get("test.h"), new TestSourcePath("foo/test.h"))
          .build();
  private static final ImmutableList<Path> DEFAULT_INCLUDE_ROOTS = ImmutableList.of(
      Paths.get("foo/bar"),
      Paths.get("test"));
  private static final ImmutableList<Path> DEFAULT_SYSTEM_INCLUDE_ROOTS = ImmutableList.of(
      Paths.get("/usr/include"),
      Paths.get("/include"));
  private static final ImmutableList<Path> DEFAULT_FRAMEWORK_ROOTS = ImmutableList.of();
  private static final DebugPathSanitizer DEFAULT_SANITIZER =
      CxxPlatforms.DEFAULT_DEBUG_PATH_SANITIZER;

  private RuleKey generateRuleKey(
      RuleKeyBuilderFactory factory,
      AbstractBuildRule rule) {

    RuleKey.Builder builder = factory.newInstance(rule);
    return builder.build();
  }

  @Test
  public void testThatInputChangesCauseRuleKeyChanges() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    RuleKeyBuilderFactory ruleKeyBuilderFactory =
        new DefaultRuleKeyBuilderFactory(
            FakeFileHashCache.createFromStrings(
                ImmutableMap.<String, String>builder()
                    .put("preprocessor", Strings.repeat("a", 40))
                    .put("compiler", Strings.repeat("a", 40))
                    .put("test.o", Strings.repeat("b", 40))
                    .put("test.cpp", Strings.repeat("c", 40))
                    .put("different", Strings.repeat("d", 40))
                    .put("foo/test.h", Strings.repeat("e", 40))
                    .put("path/to/a/plugin.so", Strings.repeat("f", 40))
                    .put("path/to/a/different/plugin.so", Strings.repeat("a0", 40))
                    .build()),
            pathResolver);

    // Generate a rule key for the defaults.
    RuleKey defaultRuleKey = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.COMPILE,
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            Optional.of(DEFAULT_COMPILER),
            Optional.of(DEFAULT_FLAGS),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, DEFAULT_SANITIZER));

    // Verify that changing the compiler causes a rulekey change.
    RuleKey compilerChange = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.COMPILE,
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            Optional.<Tool>of(new HashedFileTool(Paths.get("different"))),
            Optional.of(DEFAULT_FLAGS),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, DEFAULT_SANITIZER));
    assertNotEquals(defaultRuleKey, compilerChange);

    // Verify that changing the operation causes a rulekey change.
    RuleKey operationChange = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.PREPROCESS,
            Optional.of(DEFAULT_PREPROCESSOR),
            Optional.of(DEFAULT_FLAGS),
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, DEFAULT_SANITIZER));
    assertNotEquals(defaultRuleKey, operationChange);

    // Verify that changing the flags causes a rulekey change.
    RuleKey flagsChange = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.COMPILE,
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            Optional.of(DEFAULT_COMPILER),
            Optional.of(ImmutableList.of("-different")),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, DEFAULT_SANITIZER));
    assertNotEquals(defaultRuleKey, flagsChange);

    // Verify that changing the input causes a rulekey change.
    RuleKey inputChange = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.COMPILE,
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            Optional.of(DEFAULT_COMPILER),
            Optional.of(DEFAULT_FLAGS),
            DEFAULT_OUTPUT,
            new TestSourcePath("different"),
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, DEFAULT_SANITIZER));
    assertNotEquals(defaultRuleKey, inputChange);

    // Verify that changing the includes does *not* cause a rulekey change, since we use a
    // different mechanism to track header changes.
    RuleKey includesChange = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.COMPILE,
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            Optional.of(DEFAULT_COMPILER),
            Optional.of(DEFAULT_FLAGS),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            ImmutableList.of(Paths.get("different")),
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, DEFAULT_SANITIZER));
    assertEquals(defaultRuleKey, includesChange);

    // Verify that changing the system includes does *not* cause a rulekey change, since we use a
    // different mechanism to track header changes.
    RuleKey systemIncludesChange = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.COMPILE,
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            Optional.of(DEFAULT_COMPILER),
            Optional.of(DEFAULT_FLAGS),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            ImmutableList.of(Paths.get("different")),
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, DEFAULT_SANITIZER));
    assertEquals(defaultRuleKey, systemIncludesChange);

    // Verify that changing the framework roots causes a rulekey change.
    RuleKey frameworkRootsChange = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.COMPILE,
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            Optional.of(DEFAULT_COMPILER),
            Optional.of(DEFAULT_FLAGS),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            ImmutableList.of(Paths.get("different")), DEFAULT_INCLUDES, DEFAULT_SANITIZER));
    assertNotEquals(defaultRuleKey, frameworkRootsChange);
  }

  @Test
  public void sanitizedPathsInFlagsDoNotAffectRuleKey() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    RuleKeyBuilderFactory ruleKeyBuilderFactory =
        new DefaultRuleKeyBuilderFactory(
            FakeFileHashCache.createFromStrings(
                ImmutableMap.<String, String>builder()
                    .put("preprocessor", Strings.repeat("a", 40))
                    .put("compiler", Strings.repeat("a", 40))
                    .put("test.o", Strings.repeat("b", 40))
                    .put("test.cpp", Strings.repeat("c", 40))
                    .put("different", Strings.repeat("d", 40))
                    .put("foo/test.h", Strings.repeat("e", 40))
                    .put("path/to/a/plugin.so", Strings.repeat("f", 40))
                    .put("path/to/a/different/plugin.so", Strings.repeat("a0", 40))
                    .build()),
            pathResolver);

    // Set up a map to sanitize the differences in the flags.
    int pathSize = 10;
    DebugPathSanitizer sanitizer1 = new DebugPathSanitizer(
        pathSize,
        File.separatorChar,
        Paths.get("PWD"),
        ImmutableBiMap.of(Paths.get("something"), Paths.get("A")));
    DebugPathSanitizer sanitizer2 = new DebugPathSanitizer(
        pathSize,
        File.separatorChar,
        Paths.get("PWD"),
        ImmutableBiMap.of(Paths.get("different"), Paths.get("A")));

    // Generate a rule key for the defaults.
    ImmutableList<String> flags1 = ImmutableList.of("-Isomething/foo");
    RuleKey ruleKey1 = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.PREPROCESS,
            Optional.of(DEFAULT_PREPROCESSOR),
            Optional.of(flags1),
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, sanitizer1));

    // Generate a rule key for the defaults.
    ImmutableList<String> flags2 = ImmutableList.of("-Idifferent/foo");
    RuleKey ruleKey2 = generateRuleKey(
        ruleKeyBuilderFactory,
        new CxxPreprocessAndCompile(
            params,
            pathResolver,
            CxxPreprocessAndCompileStep.Operation.PREPROCESS,
            Optional.of(DEFAULT_PREPROCESSOR),
            Optional.of(flags2),
            Optional.<Tool>absent(),
            Optional.<ImmutableList<String>>absent(),
            DEFAULT_OUTPUT,
            DEFAULT_INPUT,
            DEFAULT_INPUT_TYPE,
            DEFAULT_INCLUDE_ROOTS,
            DEFAULT_SYSTEM_INCLUDE_ROOTS,
            DEFAULT_FRAMEWORK_ROOTS, DEFAULT_INCLUDES, sanitizer2));

    assertEquals(ruleKey1, ruleKey2);
  }

  @Test
  public void usesCorrectCommandForCompile() {

    // Setup some dummy values for inputs to the CxxPreprocessAndCompile.
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    ImmutableList<String> flags = ImmutableList.of("-ffunction-sections");
    Path output = Paths.get("test.o");
    Path input = Paths.get("test.ii");

    CxxPreprocessAndCompile buildRule = new CxxPreprocessAndCompile(
        params,
        pathResolver,
        CxxPreprocessAndCompileStep.Operation.COMPILE,
        Optional.<Tool>absent(),
        Optional.<ImmutableList<String>>absent(),
        Optional.of(DEFAULT_COMPILER),
        Optional.of(flags),
        output,
        new TestSourcePath(input.toString()),
        DEFAULT_INPUT_TYPE,
        ImmutableList.<Path>of(),
        ImmutableList.<Path>of(),
        DEFAULT_FRAMEWORK_ROOTS, CxxHeaders.builder().build(), DEFAULT_SANITIZER);

    ImmutableList<String> expectedCompileCommand = ImmutableList.<String>builder()
        .add("compiler")
        .add("-ffunction-sections")
        .add("-x", "c++")
        .add("-c")
        .add(input.toString())
        .add("-o", output.toString())
        .build();
    ImmutableList<String> actualCompileCommand = buildRule.makeMainStep().getCommand();
    assertEquals(expectedCompileCommand, actualCompileCommand);
  }

  @Test
  public void usesCorrectCommandForPreprocess() {

    // Setup some dummy values for inputs to the CxxPreprocessAndCompile.
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    ImmutableList<String> flags = ImmutableList.of("-Dtest=blah");
    Path output = Paths.get("test.ii");
    Path input = Paths.get("test.cpp");

    CxxPreprocessAndCompile buildRule = new CxxPreprocessAndCompile(
        params,
        pathResolver,
        CxxPreprocessAndCompileStep.Operation.PREPROCESS,
        Optional.of(DEFAULT_PREPROCESSOR),
        Optional.of(flags),
        Optional.<Tool>absent(),
        Optional.<ImmutableList<String>>absent(),
        output,
        new TestSourcePath(input.toString()),
        DEFAULT_INPUT_TYPE,
        ImmutableList.<Path>of(),
        ImmutableList.<Path>of(),
        DEFAULT_FRAMEWORK_ROOTS, CxxHeaders.builder().build(), DEFAULT_SANITIZER);

    // Verify it uses the expected command.
    ImmutableList<String> expectedPreprocessCommand = ImmutableList.<String>builder()
        .add("preprocessor")
        .add("-Dtest=blah")
        .add("-x", "c++")
        .add("-E")
        .add(input.toString())
        .build();
    ImmutableList<String> actualPreprocessCommand = buildRule.makeMainStep().getCommand();
    assertEquals(expectedPreprocessCommand, actualPreprocessCommand);
  }
}


File: test/com/facebook/buck/cxx/CxxPreprocessablesTest.java
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

package com.facebook.buck.cxx;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.facebook.buck.cli.FakeBuckConfig;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.FakeBuildRule;
import com.facebook.buck.rules.FakeBuildRuleParamsBuilder;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.SymlinkTree;
import com.facebook.buck.rules.TestSourcePath;
import com.facebook.buck.shell.Genrule;
import com.facebook.buck.shell.GenruleBuilder;
import com.facebook.buck.testutil.FakeProjectFilesystem;
import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSortedSet;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import java.nio.file.Path;
import java.nio.file.Paths;

public class CxxPreprocessablesTest {

  private static final ProjectFilesystem PROJECT_FILESYSTEM = new FakeProjectFilesystem();

  private static class FakeCxxPreprocessorDep extends FakeBuildRule
      implements CxxPreprocessorDep {

    private final CxxPreprocessorInput input;

    public FakeCxxPreprocessorDep(
        BuildRuleParams params,
        SourcePathResolver resolver,
        CxxPreprocessorInput input) {
      super(params, resolver);
      this.input = Preconditions.checkNotNull(input);
    }

    @Override
    public CxxPreprocessorInput getCxxPreprocessorInput(
        CxxPlatform cxxPlatform,
        HeaderVisibility headerVisibility) {
      return input;
    }

    @Override
    public ImmutableMap<BuildTarget, CxxPreprocessorInput> getTransitiveCxxPreprocessorInput(
        CxxPlatform cxxPlatform,
        HeaderVisibility headerVisibility) {
      ImmutableMap.Builder<BuildTarget, CxxPreprocessorInput> builder = ImmutableMap.builder();
      builder.put(getBuildTarget(), getCxxPreprocessorInput(cxxPlatform, headerVisibility));
      for (BuildRule dep : getDeps()) {
        if (dep instanceof CxxPreprocessorDep) {
          builder.putAll(
              ((CxxPreprocessorDep) dep).getTransitiveCxxPreprocessorInput(
                  cxxPlatform,
                  headerVisibility));
          }
        }
      return builder.build();
    }

  }

  private static FakeCxxPreprocessorDep createFakeCxxPreprocessorDep(
      BuildTarget target,
      SourcePathResolver resolver,
      CxxPreprocessorInput input,
      BuildRule... deps) {
    return new FakeCxxPreprocessorDep(
        new FakeBuildRuleParamsBuilder(target)
            .setDeps(ImmutableSortedSet.copyOf(deps))
            .build(),
        resolver, input);
  }

  private static FakeCxxPreprocessorDep createFakeCxxPreprocessorDep(
      String target,
      SourcePathResolver resolver,
      CxxPreprocessorInput input,
      BuildRule... deps) {
    return createFakeCxxPreprocessorDep(
        BuildTargetFactory.newInstance(target),
        resolver,
        input,
        deps);
  }

  private static FakeBuildRule createFakeBuildRule(
      BuildTarget target,
      SourcePathResolver resolver,
      BuildRule... deps) {
    return new FakeBuildRule(
        new FakeBuildRuleParamsBuilder(target)
            .setDeps(ImmutableSortedSet.copyOf(deps))
            .build(),
        resolver);
  }

  @Rule
  public ExpectedException exception = ExpectedException.none();

  @Test
  public void resolveHeaderMap() {
    BuildTarget target = BuildTargetFactory.newInstance("//hello/world:test");
    ImmutableMap<String, SourcePath> headerMap = ImmutableMap.<String, SourcePath>of(
        "foo/bar.h", new TestSourcePath("header1.h"),
        "foo/hello.h", new TestSourcePath("header2.h"));

    // Verify that the resolveHeaderMap returns sane results.
    ImmutableMap<Path, SourcePath> expected = ImmutableMap.<Path, SourcePath>of(
        target.getBasePath().resolve("foo/bar.h"), new TestSourcePath("header1.h"),
        target.getBasePath().resolve("foo/hello.h"), new TestSourcePath("header2.h"));
    ImmutableMap<Path, SourcePath> actual = CxxPreprocessables.resolveHeaderMap(
        target.getBasePath(), headerMap);
    assertEquals(expected, actual);
  }

  @Test
  public void getTransitiveCxxPreprocessorInput() throws Exception {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    CxxPlatform cxxPlatform = DefaultCxxPlatforms.build(new CxxBuckConfig(new FakeBuckConfig()));

    // Setup a simple CxxPreprocessorDep which contributes components to preprocessing.
    BuildTarget cppDepTarget1 = BuildTargetFactory.newInstance("//:cpp1");
    CxxPreprocessorInput input1 = CxxPreprocessorInput.builder()
        .addRules(cppDepTarget1)
        .putPreprocessorFlags(CxxSource.Type.C, "-Dtest=yes")
        .putPreprocessorFlags(CxxSource.Type.CXX, "-Dtest=yes")
        .addIncludeRoots(Paths.get("foo/bar"), Paths.get("hello"))
        .addSystemIncludeRoots(Paths.get("/usr/include"))
        .build();
    BuildTarget depTarget1 = BuildTargetFactory.newInstance("//:dep1");
    FakeCxxPreprocessorDep dep1 = createFakeCxxPreprocessorDep(depTarget1, pathResolver, input1);

    // Setup another simple CxxPreprocessorDep which contributes components to preprocessing.
    BuildTarget cppDepTarget2 = BuildTargetFactory.newInstance("//:cpp2");
    CxxPreprocessorInput input2 = CxxPreprocessorInput.builder()
        .addRules(cppDepTarget2)
        .putPreprocessorFlags(CxxSource.Type.C, "-DBLAH")
        .putPreprocessorFlags(CxxSource.Type.CXX, "-DBLAH")
        .addIncludeRoots(Paths.get("goodbye"))
        .addSystemIncludeRoots(Paths.get("test"))
        .build();
    BuildTarget depTarget2 = BuildTargetFactory.newInstance("//:dep2");
    FakeCxxPreprocessorDep dep2 = createFakeCxxPreprocessorDep(depTarget2, pathResolver, input2);

    // Create a normal dep which depends on the two CxxPreprocessorDep rules above.
    BuildTarget depTarget3 = BuildTargetFactory.newInstance("//:dep3");
    CxxPreprocessorInput nothing = CxxPreprocessorInput.EMPTY;
    FakeCxxPreprocessorDep dep3 = createFakeCxxPreprocessorDep(depTarget3,
        pathResolver,
        nothing, dep1, dep2);

    // Verify that getTransitiveCxxPreprocessorInput gets all CxxPreprocessorInput objects
    // from the relevant rules above.
    ImmutableList<CxxPreprocessorInput> expected = ImmutableList.of(nothing, input1, input2);
    ImmutableList<CxxPreprocessorInput> actual = ImmutableList.copyOf(
        CxxPreprocessables.getTransitiveCxxPreprocessorInput(
            cxxPlatform,
            ImmutableList.<BuildRule>of(dep3)));
    assertEquals(expected, actual);
  }

  @Test
  public void createHeaderSymlinkTreeBuildRuleHasNoDeps() {
    BuildRuleResolver resolver = new BuildRuleResolver();
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);
    // Setup up the main build target and build params, which some random dep.  We'll make
    // sure the dep doesn't get propagated to the symlink rule below.
    FakeBuildRule dep = createFakeBuildRule(
        BuildTargetFactory.newInstance("//random:dep"),
        pathResolver);
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = new FakeBuildRuleParamsBuilder(target)
        .setDeps(ImmutableSortedSet.<BuildRule>of(dep))
        .build();
    Path root = Paths.get("root");

    // Setup a simple genrule we can wrap in a BuildTargetSourcePath to model a input source
    // that is built by another rule.
    Genrule genrule = (Genrule) GenruleBuilder
        .newGenruleBuilder(BuildTargetFactory.newInstance("//:genrule"))
        .setOut("foo/bar.o")
        .build(resolver);

    // Setup the link map with both a regular path-based source path and one provided by
    // another build rule.
    ImmutableMap<Path, SourcePath> links = ImmutableMap.<Path, SourcePath>of(
        Paths.get("link1"),
        new TestSourcePath("hello"),
        Paths.get("link2"),
        new BuildTargetSourcePath(PROJECT_FILESYSTEM, genrule.getBuildTarget()));

    // Build our symlink tree rule using the helper method.
    SymlinkTree symlinkTree = CxxPreprocessables.createHeaderSymlinkTreeBuildRule(
        pathResolver,
        target,
        params,
        root,
        links);

    // Verify that the symlink tree has no deps.  This is by design, since setting symlinks can
    // be done completely independently from building the source that the links point to and
    // independently from the original deps attached to the input build rule params.
    assertTrue(symlinkTree.getDeps().isEmpty());
  }

  @Test
  public void getTransitiveNativeLinkableInputDoesNotTraversePastNonNativeLinkables()
      throws Exception {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    CxxPlatform cxxPlatform = DefaultCxxPlatforms.build(new CxxBuckConfig(new FakeBuckConfig()));

    // Create a native linkable that sits at the bottom of the dep chain.
    String sentinal = "bottom";
    CxxPreprocessorInput bottomInput = CxxPreprocessorInput.builder()
        .putPreprocessorFlags(CxxSource.Type.C, sentinal)
        .build();
    BuildRule bottom = createFakeCxxPreprocessorDep("//:bottom", pathResolver, bottomInput);

    // Create a non-native linkable that sits in the middle of the dep chain, preventing
    // traversals to the bottom native linkable.
    BuildRule middle = new FakeBuildRule("//:middle", pathResolver, bottom);

    // Create a native linkable that sits at the top of the dep chain.
    CxxPreprocessorInput topInput = CxxPreprocessorInput.EMPTY;
    BuildRule top = createFakeCxxPreprocessorDep("//:top", pathResolver, topInput, middle);

    // Now grab all input via traversing deps and verify that the middle rule prevents pulling
    // in the bottom input.
    CxxPreprocessorInput totalInput = CxxPreprocessorInput.concat(
        CxxPreprocessables.getTransitiveCxxPreprocessorInput(
            cxxPlatform,
            ImmutableList.of(top)));
    assertTrue(bottomInput.getPreprocessorFlags().get(CxxSource.Type.C).contains(sentinal));
    assertFalse(totalInput.getPreprocessorFlags().get(CxxSource.Type.C).contains(sentinal));
  }

  @Test
  public void combiningTransitiveDependenciesThrowsForConflictingHeaders()
      throws Exception {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    CxxPlatform cxxPlatform = DefaultCxxPlatforms.build(new CxxBuckConfig(new FakeBuckConfig()));

    CxxPreprocessorInput bottomInput = CxxPreprocessorInput.builder()
        .setIncludes(
            CxxHeaders.builder()
                .putNameToPathMap(
                    Paths.get("prefix/file.h"),
                    new TestSourcePath("bottom/file.h"))
                .putFullNameToPathMap(
                    Paths.get("buck-out/something/prefix/file.h"),
                    new TestSourcePath("bottom/file.h"))
                .build())
        .build();
    BuildRule bottom = createFakeCxxPreprocessorDep("//:bottom", pathResolver, bottomInput);

    CxxPreprocessorInput topInput = CxxPreprocessorInput.builder()
        .setIncludes(
            CxxHeaders.builder()
                .putNameToPathMap(
                    Paths.get("prefix/file.h"),
                    new TestSourcePath("top/file.h"))
                .putFullNameToPathMap(
                    Paths.get("buck-out/something-else/prefix/file.h"),
                    new TestSourcePath("top/file.h"))
                .build())
        .build();
    BuildRule top = createFakeCxxPreprocessorDep("//:top", pathResolver, topInput, bottom);

    exception.expect(CxxPreprocessorInput.ConflictingHeadersException.class);
    exception.expectMessage(String.format(
            "'%s' maps to both [%s, %s].",
            Paths.get("prefix/file.h"),
            Paths.get("bottom/file.h"),
            Paths.get("top/file.h")));

    CxxPreprocessorInput.concat(
        CxxPreprocessables.getTransitiveCxxPreprocessorInput(
            cxxPlatform,
            ImmutableList.of(top)));
  }

  @Test
  public void combiningTransitiveDependenciesDoesNotThrowForCompatibleHeaders()
      throws Exception {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    CxxPlatform cxxPlatform = DefaultCxxPlatforms.build(new CxxBuckConfig(new FakeBuckConfig()));

    CxxPreprocessorInput bottomInput = CxxPreprocessorInput.builder()
        .setIncludes(
            CxxHeaders.builder()
                .putNameToPathMap(
                    Paths.get("prefix/file.h"),
                    new TestSourcePath("common/file.h"))
                .putFullNameToPathMap(
                    Paths.get("buck-out/something/prefix/file.h"),
                    new TestSourcePath("common/file.h"))
                .build())
        .build();
    BuildRule bottom = createFakeCxxPreprocessorDep("//:bottom", pathResolver, bottomInput);

    CxxPreprocessorInput topInput = CxxPreprocessorInput.builder()
        .setIncludes(
            CxxHeaders.builder()
                .putNameToPathMap(
                    Paths.get("prefix/file.h"),
                    new TestSourcePath("common/file.h"))
                .putFullNameToPathMap(
                    Paths.get("buck-out/something-else/prefix/file.h"),
                    new TestSourcePath("common/file.h"))
                .build())
        .build();
    BuildRule top = createFakeCxxPreprocessorDep("//:top", pathResolver, topInput, bottom);

    CxxPreprocessorInput expected = CxxPreprocessorInput.builder()
        .setIncludes(
            CxxHeaders.builder()
                .putNameToPathMap(
                    Paths.get("prefix/file.h"),
                    new TestSourcePath("common/file.h"))
                .putFullNameToPathMap(
                    Paths.get("buck-out/something/prefix/file.h"),
                    new TestSourcePath("common/file.h"))
                .putFullNameToPathMap(
                    Paths.get("buck-out/something-else/prefix/file.h"),
                    new TestSourcePath("common/file.h"))
                .build())
        .build();

    assertEquals(
        expected,
        CxxPreprocessorInput.concat(
            CxxPreprocessables.getTransitiveCxxPreprocessorInput(
                cxxPlatform,
                ImmutableList.of(top))));
  }

}


File: test/com/facebook/buck/cxx/CxxSourceRuleFactoryHelper.java
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

package com.facebook.buck.cxx;

import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.rules.BuildRuleParamsFactory;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.SourcePathResolver;
import com.google.common.collect.ImmutableList;

public class CxxSourceRuleFactoryHelper {

  private CxxSourceRuleFactoryHelper() {}

  public static CxxSourceRuleFactory of(BuildTarget target, CxxPlatform cxxPlatform) {
    BuildRuleResolver resolver = new BuildRuleResolver();
    return new CxxSourceRuleFactory(
        BuildRuleParamsFactory.createTrivialBuildRuleParams(target),
        resolver,
        new SourcePathResolver(resolver),
        cxxPlatform,
        CxxPreprocessorInput.EMPTY,
        ImmutableList.<String>of());
  }

}


File: test/com/facebook/buck/cxx/CxxSourceRuleFactoryTest.java
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

package com.facebook.buck.cxx;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;

import com.facebook.buck.cli.FakeBuckConfig;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleParams;
import com.facebook.buck.rules.BuildRuleParamsFactory;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildTargetSourcePath;
import com.facebook.buck.rules.FakeBuildRule;
import com.facebook.buck.rules.FakeBuildRuleParamsBuilder;
import com.facebook.buck.rules.PathSourcePath;
import com.facebook.buck.rules.SourcePath;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.TestSourcePath;
import com.facebook.buck.testutil.AllExistingProjectFilesystem;
import com.facebook.buck.testutil.FakeProjectFilesystem;
import com.google.common.base.Joiner;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSortedSet;

import org.hamcrest.Matchers;
import org.junit.Test;

import java.util.Collections;
import java.util.List;

public class CxxSourceRuleFactoryTest {

  private static final ProjectFilesystem PROJECT_FILESYSTEM = new FakeProjectFilesystem();

  private static final CxxPlatform CXX_PLATFORM = DefaultCxxPlatforms.build(
      new CxxBuckConfig(new FakeBuckConfig()));

  private static <T> void assertContains(ImmutableList<T> container, Iterable<T> items) {
    for (T item : items) {
      assertThat(container, Matchers.hasItem(item));
    }
  }

  private static FakeBuildRule createFakeBuildRule(
      String target,
      SourcePathResolver resolver,
      BuildRule... deps) {
    return new FakeBuildRule(
        new FakeBuildRuleParamsBuilder(BuildTargetFactory.newInstance(target))
            .setDeps(ImmutableSortedSet.copyOf(deps))
            .build(),
        resolver);
  }

  @Test
  public void createPreprocessBuildRulePropagatesCxxPreprocessorDeps() {
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    BuildRuleResolver resolver = new BuildRuleResolver();
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);

    FakeBuildRule dep = resolver.addToIndex(
        new FakeBuildRule(
            "//:dep1",
            new SourcePathResolver(new BuildRuleResolver())));

    CxxPreprocessorInput cxxPreprocessorInput =
        CxxPreprocessorInput.builder()
            .addRules(dep.getBuildTarget())
            .build();

    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            resolver,
            pathResolver,
            CXX_PLATFORM,
            cxxPreprocessorInput,
            ImmutableList.<String>of());

    String name = "foo/bar.cpp";
    SourcePath input = new PathSourcePath(PROJECT_FILESYSTEM, target.getBasePath().resolve(name));
    CxxSource cxxSource = CxxSource.of(
        CxxSource.Type.CXX,
        input,
        ImmutableList.<String>of());

    BuildRule cxxPreprocess =
        cxxSourceRuleFactory.requirePreprocessBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertEquals(ImmutableSortedSet.<BuildRule>of(dep), cxxPreprocess.getDeps());
    cxxPreprocess =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertEquals(ImmutableSortedSet.<BuildRule>of(dep), cxxPreprocess.getDeps());
  }

  @Test
  public void preprocessFlagsFromPlatformArePropagated() {
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    BuildRuleResolver resolver = new BuildRuleResolver();
    SourcePathResolver pathResolver = new SourcePathResolver(resolver);

    ImmutableList<String> platformFlags = ImmutableList.of("-some", "-flags");
    CxxPlatform platform = DefaultCxxPlatforms.build(
        new CxxBuckConfig(
            new FakeBuckConfig(
                ImmutableMap.of(
                    "cxx", ImmutableMap.of("cxxppflags", Joiner.on(" ").join(platformFlags))))));

    CxxPreprocessorInput cxxPreprocessorInput = CxxPreprocessorInput.EMPTY;

    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            resolver,
            pathResolver,
            platform,
            cxxPreprocessorInput,
            ImmutableList.<String>of());

    String name = "source.cpp";
    CxxSource cxxSource = CxxSource.of(
        CxxSource.Type.CXX,
        new TestSourcePath(name),
        ImmutableList.<String>of());

    // Verify that platform flags make it to the compile rule.
    CxxPreprocessAndCompile cxxPreprocess =
        cxxSourceRuleFactory.requirePreprocessBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertNotEquals(
        -1,
        Collections.indexOfSubList(cxxPreprocess.getPreprocessorFlags().get(), platformFlags));
    CxxPreprocessAndCompile cxxPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertNotEquals(
        -1,
        Collections.indexOfSubList(
            cxxPreprocessAndCompile.getPreprocessorFlags().get(),
            platformFlags));
  }

  @Test
  public void checkCorrectFlagsAreUsedForPreprocessBuildRules() {
    BuildRuleResolver buildRuleResolver = new BuildRuleResolver();
    SourcePathResolver sourcePathResolver = new SourcePathResolver(buildRuleResolver);
    BuildTarget target = BuildTargetFactory.newInstance("//:target");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    ProjectFilesystem filesystem = new AllExistingProjectFilesystem();
    Joiner space = Joiner.on(" ");

    ImmutableList<String> explicitCppflags = ImmutableList.of("-explicit-cppflag");
    ImmutableList<String> explicitCxxppflags = ImmutableList.of("-explicit-cxxppflag");
    CxxPreprocessorInput cxxPreprocessorInput =
        CxxPreprocessorInput.builder()
            .putAllPreprocessorFlags(CxxSource.Type.C, explicitCppflags)
            .putAllPreprocessorFlags(CxxSource.Type.CXX, explicitCxxppflags)
            .build();

    ImmutableList<String> asppflags = ImmutableList.of("-asppflag", "-asppflag");

    SourcePath cpp = new TestSourcePath("cpp");
    ImmutableList<String> cppflags = ImmutableList.of("-cppflag", "-cppflag");

    SourcePath cxxpp = new TestSourcePath("cxxpp");
    ImmutableList<String> cxxppflags = ImmutableList.of("-cxxppflag", "-cxxppflag");

    FakeBuckConfig buckConfig = new FakeBuckConfig(
        ImmutableMap.of(
            "cxx", ImmutableMap.<String, String>builder()
                .put("asppflags", space.join(asppflags))
                .put("cpp", sourcePathResolver.getPath(cpp).toString())
                .put("cppflags", space.join(cppflags))
                .put("cxxpp", sourcePathResolver.getPath(cxxpp).toString())
                .put("cxxppflags", space.join(cxxppflags))
                .build()),
        filesystem);
    CxxPlatform platform = DefaultCxxPlatforms.build(new CxxBuckConfig(buckConfig));

    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            buildRuleResolver,
            sourcePathResolver,
            platform,
            cxxPreprocessorInput,
            ImmutableList.<String>of());

    String cSourceName = "test.c";
    List<String> perFileFlagsForTestC =
        ImmutableList.of("-per-file-flag-for-c-file", "-and-another-one");
    CxxSource cSource = CxxSource.of(
        CxxSource.Type.C,
        new TestSourcePath(cSourceName),
        perFileFlagsForTestC);
    CxxPreprocessAndCompile cPreprocess =
        cxxSourceRuleFactory.requirePreprocessBuildRule(
            buildRuleResolver,
            cSourceName,
            cSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(cPreprocess.getPreprocessorFlags().get(), explicitCppflags);
    assertContains(cPreprocess.getPreprocessorFlags().get(), cppflags);
    assertContains(cPreprocess.getPreprocessorFlags().get(), perFileFlagsForTestC);
    CxxPreprocessAndCompile cPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            cSourceName,
            cSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(cPreprocessAndCompile.getCompilerFlags().get(), perFileFlagsForTestC);

    String cxxSourceName = "test.cpp";
    List<String> perFileFlagsForTestCpp =
        ImmutableList.of("-per-file-flag-for-cpp-file");
    CxxSource cxxSource = CxxSource.of(
        CxxSource.Type.CXX,
        new TestSourcePath(cxxSourceName),
        perFileFlagsForTestCpp);
    CxxPreprocessAndCompile cxxPreprocess =
        cxxSourceRuleFactory.requirePreprocessBuildRule(
            buildRuleResolver,
            cxxSourceName,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(cxxPreprocess.getPreprocessorFlags().get(), explicitCxxppflags);
    assertContains(cxxPreprocess.getPreprocessorFlags().get(), cxxppflags);
    assertContains(cxxPreprocess.getPreprocessorFlags().get(), perFileFlagsForTestCpp);
    CxxPreprocessAndCompile cxxPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            cxxSourceName,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(cxxPreprocessAndCompile.getCompilerFlags().get(), perFileFlagsForTestCpp);

    String assemblerWithCppSourceName = "test.S";
    List<String> perFileFlagsForTestS =
        ImmutableList.of("-a-flag-for-s-file", "-another-one", "-one-more");
    CxxSource assemblerWithCppSource = CxxSource.of(
        CxxSource.Type.ASSEMBLER_WITH_CPP,
        new TestSourcePath(assemblerWithCppSourceName),
        perFileFlagsForTestS);
    CxxPreprocessAndCompile assemblerWithCppPreprocess =
        cxxSourceRuleFactory.requirePreprocessBuildRule(
            buildRuleResolver,
            assemblerWithCppSourceName,
            assemblerWithCppSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(assemblerWithCppPreprocess.getPreprocessorFlags().get(), asppflags);
    assertContains(assemblerWithCppPreprocess.getPreprocessorFlags().get(), perFileFlagsForTestS);
    CxxPreprocessAndCompile assemblerWithCppPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            assemblerWithCppSourceName,
            assemblerWithCppSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(
        assemblerWithCppPreprocessAndCompile.getCompilerFlags().get(),
        perFileFlagsForTestS);
  }

  @Test
  public void createCompileBuildRulePropagatesBuildRuleSourcePathDeps() {
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    BuildRuleResolver resolver = new BuildRuleResolver();

    FakeBuildRule dep = createFakeBuildRule("//:test", new SourcePathResolver(resolver));
    resolver.addToIndex(dep);
    SourcePath input = new BuildTargetSourcePath(PROJECT_FILESYSTEM, dep.getBuildTarget());
    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            resolver,
            new SourcePathResolver(resolver),
            CXX_PLATFORM,
            CxxPreprocessorInput.EMPTY,
            ImmutableList.<String>of());

    String nameCompile = "foo/bar.ii";
    CxxSource cxxSourceCompile = CxxSource.of(
        CxxSource.Type.CXX_CPP_OUTPUT,
        input,
        ImmutableList.<String>of());
    CxxPreprocessAndCompile cxxCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            resolver,
            nameCompile,
            cxxSourceCompile,
            CxxSourceRuleFactory.PicType.PDC);
    assertEquals(ImmutableSortedSet.<BuildRule>of(dep), cxxCompile.getDeps());

    String namePreprocessAndCompile = "foo/bar.cpp";
    CxxSource cxxSourcePreprocessAndCompile = CxxSource.of(
        CxxSource.Type.CXX,
        input,
        ImmutableList.<String>of());
    CxxPreprocessAndCompile cxxPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            resolver,
            namePreprocessAndCompile,
            cxxSourcePreprocessAndCompile,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertEquals(ImmutableSortedSet.<BuildRule>of(dep), cxxPreprocessAndCompile.getDeps());
  }

  @Test
  @SuppressWarnings("PMD.UseAssertTrueInsteadOfAssertEquals")
  public void createCompileBuildRulePicOption() {
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    BuildRuleResolver resolver = new BuildRuleResolver();

    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            resolver,
            new SourcePathResolver(resolver),
            CXX_PLATFORM,
            CxxPreprocessorInput.EMPTY,
            ImmutableList.<String>of());

    String name = "foo/bar.ii";
    CxxSource cxxSource = CxxSource.of(
        CxxSource.Type.CXX_CPP_OUTPUT,
        new TestSourcePath(name),
        ImmutableList.<String>of());

    // Verify building a non-PIC compile rule does *not* have the "-fPIC" flag and has the
    // expected compile target.
    CxxPreprocessAndCompile noPicCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertFalse(noPicCompile.getCompilerFlags().get().contains("-fPIC"));
    assertEquals(
        cxxSourceRuleFactory.createCompileBuildTarget(
            name,
            CxxSourceRuleFactory.PicType.PDC),
        noPicCompile.getBuildTarget());

    // Verify building a PIC compile rule *does* have the "-fPIC" flag and has the
    // expected compile target.
    CxxPreprocessAndCompile picCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PIC);
    assertTrue(picCompile.getCompilerFlags().get().contains("-fPIC"));
    assertEquals(
        cxxSourceRuleFactory.createCompileBuildTarget(
            name,
            CxxSourceRuleFactory.PicType.PIC),
        picCompile.getBuildTarget());

    name = "foo/bar.cpp";
    cxxSource = CxxSource.of(
        CxxSource.Type.CXX,
        new TestSourcePath(name),
        ImmutableList.<String>of());

    // Verify building a non-PIC compile rule does *not* have the "-fPIC" flag and has the
    // expected compile target.
    CxxPreprocessAndCompile noPicPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertFalse(noPicPreprocessAndCompile.getPreprocessorFlags().get().contains("-fPIC"));
    assertEquals(
        cxxSourceRuleFactory.createCompileBuildTarget(
            name,
            CxxSourceRuleFactory.PicType.PDC),
        noPicPreprocessAndCompile.getBuildTarget());

    // Verify building a PIC compile rule *does* have the "-fPIC" flag and has the
    // expected compile target.
    CxxPreprocessAndCompile picPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PIC,
            CxxPreprocessMode.SEPARATE);
    assertTrue(picPreprocessAndCompile.getCompilerFlags().get().contains("-fPIC"));
    assertEquals(
        cxxSourceRuleFactory.createCompileBuildTarget(
            name,
            CxxSourceRuleFactory.PicType.PIC),
        picPreprocessAndCompile.getBuildTarget());
  }

  @Test
  public void compilerFlagsFromPlatformArePropagated() {
    BuildTarget target = BuildTargetFactory.newInstance("//foo:bar");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    BuildRuleResolver resolver = new BuildRuleResolver();

    ImmutableList<String> platformFlags = ImmutableList.of("-some", "-flags");
    CxxPlatform platform = DefaultCxxPlatforms.build(
        new CxxBuckConfig(
            new FakeBuckConfig(
                ImmutableMap.of(
                    "cxx", ImmutableMap.of("cxxflags", Joiner.on(" ").join(platformFlags))))));

    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            resolver,
            new SourcePathResolver(resolver),
            platform,
            CxxPreprocessorInput.EMPTY,
            ImmutableList.<String>of());

    String name = "source.ii";
    CxxSource cxxSource = CxxSource.of(
        CxxSource.Type.CXX_CPP_OUTPUT,
        new TestSourcePath(name),
        ImmutableList.<String>of());

    // Verify that platform flags make it to the compile rule.
    CxxPreprocessAndCompile cxxCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertNotEquals(
        -1,
        Collections.indexOfSubList(cxxCompile.getCompilerFlags().get(), platformFlags));

    name = "source.cpp";
    cxxSource = CxxSource.of(
        CxxSource.Type.CXX,
        new TestSourcePath(name),
        ImmutableList.<String>of());

    // Verify that platform flags make it to the compile rule.
    CxxPreprocessAndCompile cxxPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            resolver,
            name,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertNotEquals(
        -1,
        Collections.indexOfSubList(
            cxxPreprocessAndCompile.getPreprocessorFlags().get(),
            platformFlags));
  }

  @Test
  public void checkCorrectFlagsAreUsedForCompileBuildRules() {
    BuildRuleResolver buildRuleResolver = new BuildRuleResolver();
    SourcePathResolver sourcePathResolver = new SourcePathResolver(buildRuleResolver);
    BuildTarget target = BuildTargetFactory.newInstance("//:target");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    ProjectFilesystem filesystem = new AllExistingProjectFilesystem();
    Joiner space = Joiner.on(" ");

    ImmutableList<String> explicitCompilerFlags = ImmutableList.of("-explicit-compilerflag");

    SourcePath as = new TestSourcePath("as");
    ImmutableList<String> asflags = ImmutableList.of("-asflag", "-asflag");

    SourcePath cc = new TestSourcePath("cc");
    ImmutableList<String> cflags = ImmutableList.of("-cflag", "-cflag");

    SourcePath cxx = new TestSourcePath("cxx");
    ImmutableList<String> cxxflags = ImmutableList.of("-cxxflag", "-cxxflag");

    FakeBuckConfig buckConfig = new FakeBuckConfig(
        ImmutableMap.of(
            "cxx", ImmutableMap.<String, String>builder()
                .put("as", sourcePathResolver.getPath(as).toString())
                .put("asflags", space.join(asflags))
                .put("cc", sourcePathResolver.getPath(cc).toString())
                .put("cflags", space.join(cflags))
                .put("cxx", sourcePathResolver.getPath(cxx).toString())
                .put("cxxflags", space.join(cxxflags))
                .build()),
        filesystem);
    CxxPlatform platform = DefaultCxxPlatforms.build(new CxxBuckConfig(buckConfig));

    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            buildRuleResolver,
            sourcePathResolver,
            platform,
            CxxPreprocessorInput.EMPTY,
            explicitCompilerFlags);

    String cSourceName = "test.i";
    List<String> cSourcePerFileFlags = ImmutableList.of("-c-source-par-file-flag");
    CxxSource cSource = CxxSource.of(
        CxxSource.Type.C_CPP_OUTPUT,
        new TestSourcePath(cSourceName),
        cSourcePerFileFlags);
    CxxPreprocessAndCompile cCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            buildRuleResolver,
            cSourceName,
            cSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(cCompile.getCompilerFlags().get(), explicitCompilerFlags);
    assertContains(cCompile.getCompilerFlags().get(), cflags);
    assertContains(cCompile.getCompilerFlags().get(), asflags);
    assertContains(cCompile.getCompilerFlags().get(), cSourcePerFileFlags);

    cSourceName = "test.c";
    cSource = CxxSource.of(
        CxxSource.Type.C,
        new TestSourcePath(cSourceName),
        cSourcePerFileFlags);
    CxxPreprocessAndCompile cPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            cSourceName,
            cSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(cPreprocessAndCompile.getCompilerFlags().get(), explicitCompilerFlags);
    assertContains(cPreprocessAndCompile.getCompilerFlags().get(), cflags);
    assertContains(cPreprocessAndCompile.getCompilerFlags().get(), asflags);
    assertContains(cPreprocessAndCompile.getCompilerFlags().get(), cSourcePerFileFlags);

    String cxxSourceName = "test.ii";
    List<String> cxxSourcePerFileFlags = ImmutableList.of("-cxx-source-par-file-flag");
    CxxSource cxxSource =
        CxxSource.of(
            CxxSource.Type.CXX_CPP_OUTPUT,
            new TestSourcePath(cxxSourceName),
            cxxSourcePerFileFlags);
    CxxPreprocessAndCompile cxxCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            buildRuleResolver,
            cxxSourceName,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(cxxCompile.getCompilerFlags().get(), explicitCompilerFlags);
    assertContains(cxxCompile.getCompilerFlags().get(), cxxflags);
    assertContains(cxxCompile.getCompilerFlags().get(), asflags);
    assertContains(cxxCompile.getCompilerFlags().get(), cxxSourcePerFileFlags);

    cxxSourceName = "test.cpp";
    cxxSource =
        CxxSource.of(
            CxxSource.Type.CXX,
            new TestSourcePath(cxxSourceName),
            cxxSourcePerFileFlags);
    CxxPreprocessAndCompile cxxPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            cxxSourceName,
            cxxSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(cxxPreprocessAndCompile.getCompilerFlags().get(), explicitCompilerFlags);
    assertContains(cxxPreprocessAndCompile.getCompilerFlags().get(), cxxflags);
    assertContains(cxxPreprocessAndCompile.getCompilerFlags().get(), asflags);
    assertContains(cxxPreprocessAndCompile.getCompilerFlags().get(), cxxSourcePerFileFlags);

    String cCppOutputSourceName = "test2.i";
    List<String> cCppOutputSourcePerFileFlags =
        ImmutableList.of("-c-cpp-output-source-par-file-flag");
    CxxSource cCppOutputSource = CxxSource.of(
        CxxSource.Type.C_CPP_OUTPUT,
        new TestSourcePath(cCppOutputSourceName),
        cCppOutputSourcePerFileFlags);
    CxxPreprocessAndCompile cCppOutputCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            buildRuleResolver,
            cCppOutputSourceName,
            cCppOutputSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(cCppOutputCompile.getCompilerFlags().get(), explicitCompilerFlags);
    assertContains(cCppOutputCompile.getCompilerFlags().get(), cflags);
    assertContains(cCppOutputCompile.getCompilerFlags().get(), asflags);
    assertContains(cCppOutputCompile.getCompilerFlags().get(), cCppOutputSourcePerFileFlags);

    cCppOutputSourceName = "test2.c";
    cCppOutputSource = CxxSource.of(
        CxxSource.Type.C,
        new TestSourcePath(cCppOutputSourceName),
        cCppOutputSourcePerFileFlags);
    CxxPreprocessAndCompile cCppOutputPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            cCppOutputSourceName,
            cCppOutputSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(
        cCppOutputPreprocessAndCompile.getCompilerFlags().get(),
        explicitCompilerFlags);
    assertContains(cCppOutputPreprocessAndCompile.getCompilerFlags().get(), cflags);
    assertContains(cCppOutputPreprocessAndCompile.getCompilerFlags().get(), asflags);
    assertContains(
        cCppOutputPreprocessAndCompile.getCompilerFlags().get(),
        cCppOutputSourcePerFileFlags);

    String assemblerSourceName = "test.s";
    List<String> assemblerSourcePerFileFlags = ImmutableList.of("-assember-source-par-file-flag");
    CxxSource assemblerSource = CxxSource.of(
        CxxSource.Type.ASSEMBLER,
        new TestSourcePath(assemblerSourceName),
        assemblerSourcePerFileFlags);
    CxxPreprocessAndCompile assemblerCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            buildRuleResolver,
            assemblerSourceName,
            assemblerSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(assemblerCompile.getCompilerFlags().get(), asflags);
    assertContains(assemblerCompile.getCompilerFlags().get(), assemblerSourcePerFileFlags);

    assemblerSourceName = "test.S";
    assemblerSource = CxxSource.of(
        CxxSource.Type.ASSEMBLER_WITH_CPP,
        new TestSourcePath(assemblerSourceName),
        assemblerSourcePerFileFlags);
    CxxPreprocessAndCompile assemblerPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            assemblerSourceName,
            assemblerSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(assemblerPreprocessAndCompile.getCompilerFlags().get(), asflags);
    assertContains(
        assemblerPreprocessAndCompile.getCompilerFlags().get(),
        assemblerSourcePerFileFlags);
  }

  // TODO(#5393669): Re-enable once we can handle the language flag in a portable way.
  /*@Test
  public void languageFlagsArePassed() {
    BuildRuleResolver buildRuleResolver = new BuildRuleResolver();
    BuildTarget target = BuildTargetFactory.newInstance("//:target");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);

    String name = "foo/bar.ii";
    SourcePath input = new PathSourcePath(target.getBasePath().resolve(name));
    CxxSource cxxSource = new CxxSource(CxxSource.Type.CXX_CPP_OUTPUT, input);

    CxxPreprocessAndCompile cxxCompile = CxxCompilableEnhancer.createCompileBuildRule(
        params,
        buildRuleResolver,
        CXX_PLATFORM,
        ImmutableList.<String>of(),
        false,
        name,
        cxxSource);

    assertThat(cxxCompile.getFlags(), Matchers.contains("-x", "c++-cpp-output"));

    name = "foo/bar.mi";
    input = new PathSourcePath(target.getBasePath().resolve(name));
    cxxSource = new CxxSource(CxxSource.Type.OBJC_CPP_OUTPUT, input);

    cxxCompile = CxxCompilableEnhancer.createCompileBuildRule(
        params,
        buildRuleResolver,
        CXX_PLATFORM,
        ImmutableList.<String>of(),
        false,
        name,
        cxxSource);

    assertThat(cxxCompile.getFlags(), Matchers.contains("-x", "objective-c-cpp-output"));

    name = "foo/bar.mii";
    input = new PathSourcePath(target.getBasePath().resolve(name));
    cxxSource = new CxxSource(CxxSource.Type.OBJCXX_CPP_OUTPUT, input);

    cxxCompile = CxxCompilableEnhancer.createCompileBuildRule(
        params,
        buildRuleResolver,
        CXX_PLATFORM,
        ImmutableList.<String>of(),
        false,
        name,
        cxxSource);

    assertThat(cxxCompile.getFlags(), Matchers.contains("-x", "objective-c++-cpp-output"));

    name = "foo/bar.i";
    input = new PathSourcePath(target.getBasePath().resolve(name));
    cxxSource = new CxxSource(CxxSource.Type.C_CPP_OUTPUT, input);

    cxxCompile = CxxCompilableEnhancer.createCompileBuildRule(
        params,
        buildRuleResolver,
        CXX_PLATFORM,
        ImmutableList.<String>of(),
        false,
        name,
        cxxSource);

    assertThat(cxxCompile.getFlags(), Matchers.contains("-x", "c-cpp-output"));
  }*/

  @Test
  public void checkCorrectFlagsAreUsedForObjcAndObjcxx() {
    BuildRuleResolver buildRuleResolver = new BuildRuleResolver();
    BuildTarget target = BuildTargetFactory.newInstance("//:target");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    ProjectFilesystem filesystem = new AllExistingProjectFilesystem();

    ImmutableList<String> explicitCompilerFlags = ImmutableList.of("-fobjc-arc");

    FakeBuckConfig buckConfig = new FakeBuckConfig(filesystem);
    CxxPlatform platform = DefaultCxxPlatforms.build(new CxxBuckConfig(buckConfig));

    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            buildRuleResolver,
            new SourcePathResolver(buildRuleResolver),
            platform,
            CxxPreprocessorInput.EMPTY,
            explicitCompilerFlags);

    String objcSourceName = "test.mi";
    CxxSource objcSource = CxxSource.of(
        CxxSource.Type.OBJC_CPP_OUTPUT,
        new TestSourcePath(objcSourceName),
        ImmutableList.<String>of());
    CxxPreprocessAndCompile objcCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            buildRuleResolver,
            objcSourceName,
            objcSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(objcCompile.getCompilerFlags().get(), explicitCompilerFlags);

    objcSourceName = "test.m";
    objcSource = CxxSource.of(
        CxxSource.Type.OBJC,
        new TestSourcePath(objcSourceName),
        ImmutableList.<String>of());
    CxxPreprocessAndCompile objcPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            objcSourceName,
            objcSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(objcPreprocessAndCompile.getCompilerFlags().get(), explicitCompilerFlags);

    String objcxxSourceName = "test.mii";
    CxxSource objcxxSource = CxxSource.of(
        CxxSource.Type.OBJCXX_CPP_OUTPUT,
        new TestSourcePath(objcxxSourceName),
        ImmutableList.<String>of());
    CxxPreprocessAndCompile objcxxCompile =
        cxxSourceRuleFactory.requireCompileBuildRule(
            buildRuleResolver,
            objcxxSourceName,
            objcxxSource,
            CxxSourceRuleFactory.PicType.PDC);
    assertContains(objcxxCompile.getCompilerFlags().get(), explicitCompilerFlags);

    objcxxSourceName = "test.mm";
    objcxxSource = CxxSource.of(
        CxxSource.Type.OBJCXX,
        new TestSourcePath(objcxxSourceName),
        ImmutableList.<String>of());
    CxxPreprocessAndCompile objcxxPreprocessAndCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            objcxxSourceName,
            objcxxSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);
    assertContains(objcxxPreprocessAndCompile.getCompilerFlags().get(), explicitCompilerFlags);
  }

  @Test
  public void duplicateRuleFetchedFromResolver() {
    BuildRuleResolver buildRuleResolver = new BuildRuleResolver();
    BuildTarget target = BuildTargetFactory.newInstance("//:target");
    BuildRuleParams params = BuildRuleParamsFactory.createTrivialBuildRuleParams(target);
    ProjectFilesystem filesystem = new AllExistingProjectFilesystem();

    FakeBuckConfig buckConfig = new FakeBuckConfig(filesystem);
    CxxPlatform platform = DefaultCxxPlatforms.build(new CxxBuckConfig(buckConfig));

    CxxSourceRuleFactory cxxSourceRuleFactory =
        new CxxSourceRuleFactory(
            params,
            buildRuleResolver,
            new SourcePathResolver(buildRuleResolver),
            platform,
            CxxPreprocessorInput.EMPTY,
            ImmutableList.<String>of());

    String objcSourceName = "test.m";
    CxxSource objcSource = CxxSource.of(
        CxxSource.Type.OBJC,
        new TestSourcePath(objcSourceName),
        ImmutableList.<String>of());
    CxxPreprocessAndCompile objcCompile =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            objcSourceName,
            objcSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);

    // Make sure we can get the same build rule twice.
    CxxPreprocessAndCompile objcCompile2 =
        cxxSourceRuleFactory.requirePreprocessAndCompileBuildRule(
            buildRuleResolver,
            objcSourceName,
            objcSource,
            CxxSourceRuleFactory.PicType.PDC,
            CxxPreprocessMode.SEPARATE);

    assertEquals(objcCompile.getBuildTarget(), objcCompile2.getBuildTarget());
  }
}
