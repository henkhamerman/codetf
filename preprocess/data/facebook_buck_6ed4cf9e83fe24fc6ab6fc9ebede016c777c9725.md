Refactoring Types: ['Inline Method']
Link.java
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
import com.facebook.buck.rules.Tool;
import com.facebook.buck.rules.keys.SupportsInputBasedRuleKey;
import com.facebook.buck.step.Step;
import com.facebook.buck.step.fs.FileScrubberStep;
import com.facebook.buck.step.fs.MkdirStep;
import com.google.common.base.Functions;
import com.google.common.base.Optional;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableSet;

import java.nio.file.Path;

public class CxxLink
    extends AbstractBuildRule
    implements RuleKeyAppendable, SupportsInputBasedRuleKey {

  @AddToRuleKey
  private final Linker linker;
  @AddToRuleKey(stringify = true)
  private final Path output;
  @SuppressWarnings("PMD.UnusedPrivateField")
  @AddToRuleKey
  private final ImmutableList<SourcePath> inputs;
  // We need to make sure we sanitize paths in the arguments, so add them to the rule key
  // in `appendToRuleKey` where we can first filter the args through the sanitizer.
  private final ImmutableList<String> args;
  private final ImmutableSet<Path> frameworkRoots;
  private final DebugPathSanitizer sanitizer;

  public CxxLink(
      BuildRuleParams params,
      SourcePathResolver resolver,
      Linker linker,
      Path output,
      ImmutableList<SourcePath> inputs,
      ImmutableList<String> args,
      ImmutableSet<Path> frameworkRoots,
      DebugPathSanitizer sanitizer) {
    super(params, resolver);
    this.linker = linker;
    this.output = output;
    this.inputs = inputs;
    this.args = args;
    this.frameworkRoots = frameworkRoots;
    this.sanitizer = sanitizer;
  }

  @Override
  public RuleKey.Builder appendToRuleKey(RuleKey.Builder builder) {
    return builder
        .setReflectively(
            "args",
            FluentIterable.from(args)
                .transform(sanitizer.sanitize(Optional.<Path>absent(), /* expandPaths */ false))
                .toList())
        .setReflectively(
            "frameworkRoots",
            FluentIterable.from(frameworkRoots)
                .transform(Functions.toStringFunction())
                .transform(sanitizer.sanitize(Optional.<Path>absent(), /* expandPaths */ false))
                .toList());
  }

  @Override
  public ImmutableList<Step> getBuildSteps(
      BuildContext context,
      BuildableContext buildableContext) {
    buildableContext.recordArtifact(output);
    return ImmutableList.of(
        new MkdirStep(output.getParent()),
        new CxxLinkStep(
            linker.getCommandPrefix(getResolver()),
            output,
            args,
            frameworkRoots),
        new FileScrubberStep(output, linker.getScrubbers()));
  }

  @Override
  public Path getPathToOutput() {
    return output;
  }

  public Tool getLinker() {
    return linker;
  }

  public Path getOutput() {
    return output;
  }

  public ImmutableList<String> getArgs() {
    return args;
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
import com.facebook.buck.rules.keys.SupportsInputBasedRuleKey;
import com.facebook.buck.step.Step;
import com.facebook.buck.step.fs.MkdirStep;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.buck.util.MoreIterables;
import com.facebook.buck.util.Optionals;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.base.Functions;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Iterables;

import java.nio.file.Path;
import java.util.Map;

/**
 * A build rule which preprocesses and/or compiles a C/C++ source in a single step.
 */
public class CxxPreprocessAndCompile
    extends AbstractBuildRule
    implements RuleKeyAppendable, SupportsInputBasedRuleKey {

  @AddToRuleKey
  private final CxxPreprocessAndCompileStep.Operation operation;
  @AddToRuleKey
  private final Optional<Preprocessor> preprocessor;
  private final Optional<ImmutableList<String>> platformPreprocessorFlags;
  private final Optional<ImmutableList<String>> rulePreprocessorFlags;
  @AddToRuleKey
  private final Optional<Compiler> compiler;
  private final Optional<ImmutableList<String>> platformCompilerFlags;
  private final Optional<ImmutableList<String>> ruleCompilerFlags;
  @AddToRuleKey(stringify = true)
  private final Path output;
  @AddToRuleKey
  private final SourcePath input;
  private final CxxSource.Type inputType;
  private final ImmutableSet<Path> includeRoots;
  private final ImmutableSet<Path> systemIncludeRoots;
  private final ImmutableSet<Path> frameworkRoots;
  @AddToRuleKey
  private final ImmutableList<CxxHeaders> includes;
  private final DebugPathSanitizer sanitizer;

  @VisibleForTesting
  CxxPreprocessAndCompile(
      BuildRuleParams params,
      SourcePathResolver resolver,
      CxxPreprocessAndCompileStep.Operation operation,
      Optional<Preprocessor> preprocessor,
      Optional<ImmutableList<String>> platformPreprocessorFlags,
      Optional<ImmutableList<String>> rulePreprocessorFlags,
      Optional<Compiler> compiler,
      Optional<ImmutableList<String>> platformCompilerFlags,
      Optional<ImmutableList<String>> ruleCompilerFlags,
      Path output,
      SourcePath input,
      CxxSource.Type inputType,
      ImmutableSet<Path> includeRoots,
      ImmutableSet<Path> systemIncludeRoots,
      ImmutableSet<Path> frameworkRoots,
      ImmutableList<CxxHeaders> includes,
      DebugPathSanitizer sanitizer) {
    super(params, resolver);
    Preconditions.checkState(operation.isPreprocess() == preprocessor.isPresent());
    Preconditions.checkState(operation.isPreprocess() == platformPreprocessorFlags.isPresent());
    Preconditions.checkState(operation.isPreprocess() == rulePreprocessorFlags.isPresent());
    Preconditions.checkState(operation.isCompile() == compiler.isPresent());
    Preconditions.checkState(operation.isCompile() == platformCompilerFlags.isPresent());
    Preconditions.checkState(operation.isCompile() == ruleCompilerFlags.isPresent());
    this.operation = operation;
    this.preprocessor = preprocessor;
    this.platformPreprocessorFlags = platformPreprocessorFlags;
    this.rulePreprocessorFlags = rulePreprocessorFlags;
    this.compiler = compiler;
    this.platformCompilerFlags = platformCompilerFlags;
    this.ruleCompilerFlags = ruleCompilerFlags;
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
      Compiler compiler,
      ImmutableList<String> platformFlags,
      ImmutableList<String> ruleFlags,
      Path output,
      SourcePath input,
      CxxSource.Type inputType,
      DebugPathSanitizer sanitizer) {
    return new CxxPreprocessAndCompile(
        params,
        resolver,
        CxxPreprocessAndCompileStep.Operation.COMPILE,
        Optional.<Preprocessor>absent(),
        Optional.<ImmutableList<String>>absent(),
        Optional.<ImmutableList<String>>absent(),
        Optional.of(compiler),
        Optional.of(platformFlags),
        Optional.of(ruleFlags),
        output,
        input,
        inputType,
        ImmutableSet.<Path>of(),
        ImmutableSet.<Path>of(),
        ImmutableSet.<Path>of(),
        ImmutableList.<CxxHeaders>of(),
        sanitizer);
  }

  /**
   * @return a {@link CxxPreprocessAndCompile} step that preprocesses the given source.
   */
  public static CxxPreprocessAndCompile preprocess(
      BuildRuleParams params,
      SourcePathResolver resolver,
      Preprocessor preprocessor,
      ImmutableList<String> platformFlags,
      ImmutableList<String> ruleFlags,
      Path output,
      SourcePath input,
      CxxSource.Type inputType,
      ImmutableSet<Path> includeRoots,
      ImmutableSet<Path> systemIncludeRoots,
      ImmutableSet<Path> frameworkRoots,
      ImmutableList<CxxHeaders> includes,
      DebugPathSanitizer sanitizer) {
    return new CxxPreprocessAndCompile(
        params,
        resolver,
        CxxPreprocessAndCompileStep.Operation.PREPROCESS,
        Optional.of(preprocessor),
        Optional.of(platformFlags),
        Optional.of(ruleFlags),
        Optional.<Compiler>absent(),
        Optional.<ImmutableList<String>>absent(),
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
      Preprocessor preprocessor,
      ImmutableList<String> platformPreprocessorFlags,
      ImmutableList<String> rulePreprocessorFlags,
      Compiler compiler,
      ImmutableList<String> platformCompilerFlags,
      ImmutableList<String> ruleCompilerFlags,
      Path output,
      SourcePath input,
      CxxSource.Type inputType,
      ImmutableSet<Path> includeRoots,
      ImmutableSet<Path> systemIncludeRoots,
      ImmutableSet<Path> frameworkRoots,
      ImmutableList<CxxHeaders> includes,
      DebugPathSanitizer sanitizer,
      CxxPreprocessMode strategy) {
    return new CxxPreprocessAndCompile(
        params,
        resolver,
        (strategy == CxxPreprocessMode.PIPED
            ? CxxPreprocessAndCompileStep.Operation.PIPED_PREPROCESS_AND_COMPILE
            : CxxPreprocessAndCompileStep.Operation.COMPILE_MUNGE_DEBUGINFO),
        Optional.of(preprocessor),
        Optional.of(platformPreprocessorFlags),
        Optional.of(rulePreprocessorFlags),
        Optional.of(compiler),
        Optional.of(platformCompilerFlags),
        Optional.of(ruleCompilerFlags),
        output,
        input,
        inputType,
        includeRoots,
        systemIncludeRoots,
        frameworkRoots,
        includes,
        sanitizer);
  }

  @Override
  public RuleKey.Builder appendToRuleKey(RuleKey.Builder builder) {
    // Sanitize any relevant paths in the flags we pass to the preprocessor, to prevent them
    // from contributing to the rule key.
    builder.setReflectively("platformPreprocessorFlags", sanitizeFlags(platformPreprocessorFlags));
    builder.setReflectively("rulePreprocessorFlags", sanitizeFlags(rulePreprocessorFlags));
    builder.setReflectively("platformCompilerFlags", sanitizeFlags(platformCompilerFlags));
    builder.setReflectively("ruleCompilerFlags", sanitizeFlags(ruleCompilerFlags));
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

  private ImmutableList<String> sanitizeFlags(Optional<ImmutableList<String>> flags) {
    return FluentIterable.from(flags.or(ImmutableList.<String>of()))
        .transform(sanitizer.sanitize(Optional.<Path>absent(), /* expandPaths */ false))
        .toList();
  }

  @VisibleForTesting
  CxxPreprocessAndCompileStep makeMainStep() {

    // Resolve the map of symlinks to real paths to hand off the preprocess step.  If we're
    // compiling, this will just be empty.
    ImmutableMap.Builder<Path, Path> replacementPathsBuilder = ImmutableMap.builder();
    try {
      for (Map.Entry<Path, SourcePath> entry :
           CxxHeaders.concat(includes).getFullNameToPathMap().entrySet()) {
        replacementPathsBuilder.put(entry.getKey(), getResolver().getPath(entry.getValue()));
      }
    } catch (CxxHeaders.ConflictingHeadersException e) {
      throw e.getHumanReadableExceptionForBuildTarget(getBuildTarget());
    }
    ImmutableMap<Path, Path> replacementPaths = replacementPathsBuilder.build();

    Optional<ImmutableList<String>> preprocessorCommand;
    if (preprocessor.isPresent()) {
      preprocessorCommand = Optional.of(
          ImmutableList.<String>builder()
              .addAll(preprocessor.get().getCommandPrefix(getResolver()))
              .addAll(getPreprocessorPlatformPrefix())
              .addAll(getPreprocessorSuffix())
              .addAll(preprocessor.get().getExtraFlags().or(ImmutableList.<String>of()))
              .build());
    } else {
      preprocessorCommand = Optional.absent();
    }

    Optional<ImmutableList<String>> compilerCommand;
    if (compiler.isPresent()) {
      compilerCommand = Optional.of(
          ImmutableList.<String>builder()
              .addAll(compiler.get().getCommandPrefix(getResolver()))
              .addAll(getCompilerPlatformPrefix())
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
        sanitizer,
        Optionals.bind(
            preprocessor,
            new Function<Preprocessor, Optional<Function<String, Iterable<String>>>>() {
              @Override
              public Optional<Function<String, Iterable<String>>> apply(Preprocessor input) {
                return input.getExtraLineProcessor();
              }
            }));
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

  private ImmutableList<String> getPreprocessorPlatformPrefix() {
    Preconditions.checkState(operation.isPreprocess());
    return platformPreprocessorFlags.get();
  }

  private ImmutableList<String> getCompilerPlatformPrefix() {
    Preconditions.checkState(operation.isCompile());
    ImmutableList.Builder<String> flags = ImmutableList.builder();
    if (operation == CxxPreprocessAndCompileStep.Operation.COMPILE_MUNGE_DEBUGINFO) {
      flags.addAll(getPreprocessorPlatformPrefix());
    }
    flags.addAll(platformCompilerFlags.get());
    return flags.build();
  }

  private ImmutableList<String> getPreprocessorSuffix() {
    Preconditions.checkState(operation.isPreprocess());
    ImmutableSet.Builder<SourcePath> prefixHeaders = ImmutableSet.builder();
    for (CxxHeaders cxxHeaders : includes) {
      prefixHeaders.addAll(cxxHeaders.getPrefixHeaders());
    }
    return ImmutableList.<String>builder()
        .addAll(rulePreprocessorFlags.get())
        .addAll(
            MoreIterables.zipAndConcat(
                Iterables.cycle("-include"),
                FluentIterable.from(prefixHeaders.build())
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
    suffix.addAll(ruleCompilerFlags.get());
    suffix.addAll(
        compiler.get()
            .debugCompilationDirFlags(sanitizer.getCompilationDirectory())
            .or(ImmutableList.<String>of()));
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
    cmd.addAll(preprocessBuildRule.getPreprocessorPlatformPrefix());
    cmd.addAll(getCompilerPlatformPrefix());
    cmd.addAll(preprocessBuildRule.getPreprocessorSuffix());
    cmd.addAll(getCompilerSuffix());
    cmd.add("-x", preprocessBuildRule.inputType.getLanguage());
    cmd.add("-c");
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
  Optional<ImmutableList<String>> getRulePreprocessorFlags() {
    return rulePreprocessorFlags;
  }

  @VisibleForTesting
  Optional<ImmutableList<String>> getPlatformPreprocessorFlags() {
    return platformPreprocessorFlags;
  }

  @VisibleForTesting
  Optional<ImmutableList<String>> getRuleCompilerFlags() {
    return ruleCompilerFlags;
  }

  @VisibleForTesting
  Optional<ImmutableList<String>> getPlatformCompilerFlags() {
    return platformCompilerFlags;
  }

  public Path getOutput() {
    return output;
  }

  public SourcePath getInput() {
    return input;
  }

  public ImmutableList<CxxHeaders> getIncludes() {
    return includes;
  }

}


File: src/com/facebook/buck/cxx/CxxPreprocessAndCompileStep.java
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

import com.facebook.buck.log.Logger;
import com.facebook.buck.step.ExecutionContext;
import com.facebook.buck.step.Step;
import com.facebook.buck.util.Escaper;
import com.facebook.buck.util.FunctionLineProcessorThread;
import com.facebook.buck.util.MoreThrowables;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Function;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.io.Files;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.annotation.Nullable;

/**
 * A step that preprocesses and/or compiles C/C++ sources in a single step.
 */
public class CxxPreprocessAndCompileStep implements Step {

  private static final Logger LOG = Logger.get(CxxPreprocessAndCompileStep.class);

  private final Operation operation;
  private final Path output;
  private final Path input;
  private final CxxSource.Type inputType;
  private final Optional<ImmutableList<String>> preprocessorCommand;
  private final Optional<ImmutableList<String>> compilerCommand;
  private final ImmutableMap<Path, Path> replacementPaths;
  private final DebugPathSanitizer sanitizer;
  private final Optional<Function<String, Iterable<String>>> extraLineProcessor;

  // N.B. These include paths are special to GCC. They aren't real files and there is no remapping
  // needed, so we can just ignore them everywhere.
  private static final ImmutableSet<String> SPECIAL_INCLUDE_PATHS = ImmutableSet.of(
      "<built-in>",
      "<command-line>"
  );

  public CxxPreprocessAndCompileStep(
      Operation operation,
      Path output,
      Path input,
      CxxSource.Type inputType,
      Optional<ImmutableList<String>> preprocessorCommand,
      Optional<ImmutableList<String>> compilerCommand,
      ImmutableMap<Path, Path> replacementPaths,
      DebugPathSanitizer sanitizer,
      Optional<Function<String, Iterable<String>>> extraLineProcessor) {
    Preconditions.checkState(operation.isPreprocess() == preprocessorCommand.isPresent());
    Preconditions.checkState(operation.isCompile() == compilerCommand.isPresent());
    this.operation = operation;
    this.output = output;
    this.input = input;
    this.inputType = inputType;
    this.preprocessorCommand = preprocessorCommand;
    this.compilerCommand = compilerCommand;
    this.replacementPaths = replacementPaths;
    this.sanitizer = sanitizer;
    this.extraLineProcessor = extraLineProcessor;
  }

  @Override
  public String getShortName() {
    Optional<CxxSource.Type> type = CxxSource.Type.fromExtension(
        Files.getFileExtension(input.getFileName().toString()));
    String fileType;
    if (type.isPresent()) {
      fileType = type.get().getLanguage();
    } else {
      fileType = "unknown";
    }
    return fileType + " " + operation.toString().toLowerCase();
  }

  @VisibleForTesting
  Function<String, Iterable<String>> createPreprocessOutputLineProcessor(final Path workingDir) {
    return new Function<String, Iterable<String>>() {

      private final Pattern lineMarkers =
          Pattern.compile("^# (?<num>\\d+) \"(?<path>[^\"]+)\"(?<rest>.*)?$");

      @Override
      public Iterable<String> apply(String line) {
        if (line.startsWith("# ")) {
          Matcher m = lineMarkers.matcher(line);

          if (m.find() && !SPECIAL_INCLUDE_PATHS.contains(m.group("path"))) {
            String originalPath = m.group("path");
            String replacementPath = originalPath;

            replacementPath = Optional
                .fromNullable(replacementPaths.get(Paths.get(replacementPath)))
                .transform(Escaper.PATH_FOR_C_INCLUDE_STRING_ESCAPER)
                .or(replacementPath);

            replacementPath =
                sanitizer.sanitize(
                    Optional.of(workingDir),
                    replacementPath,
                    /* expandPaths */ false);

            if (!originalPath.equals(replacementPath)) {
              String num = m.group("num");
              String rest = m.group("rest");
              return ImmutableList.of("# " + num + " \"" + replacementPath + "\"" + rest);
            }
          }

          return ImmutableList.of(line);
        }

        if (extraLineProcessor.isPresent()) {
          return extraLineProcessor.get().apply(line);
        }

        return ImmutableList.of(line);
      }
    };
  }

  @VisibleForTesting
  Function<String, Iterable<String>> createErrorLineProcessor(final Path workingDir) {
    return CxxDescriptionEnhancer.createErrorMessagePathProcessor(
        new Function<String, String>() {
          @Override
          public String apply(String original) {
            Path path = Paths.get(original);

            // If we're compiling, we also need to restore the original working directory in the
            // error output.
            if (operation == Operation.COMPILE) {
              path = Paths.get(sanitizer.restore(Optional.of(workingDir), original));
            }

            // And, of course, we need to fixup any replacement paths.
            return Optional
                .fromNullable(replacementPaths.get(path))
                .transform(Escaper.PATH_FOR_C_INCLUDE_STRING_ESCAPER)
                .or(Escaper.escapePathForCIncludeString(path));
          }
        });
  }

  /**
   * Apply common settings for our subprocesses.
   *
   * @return Half-configured ProcessBuilder
   */
  private ProcessBuilder makeSubprocessBuilder(ExecutionContext context) {
    ProcessBuilder builder = new ProcessBuilder();
    builder.directory(context.getProjectDirectoryRoot().toAbsolutePath().toFile());
    builder.redirectError(ProcessBuilder.Redirect.PIPE);

    // A forced compilation directory is set in the constructor.  Now, we can't actually force
    // the compiler to embed this into the binary -- all we can do set the PWD environment to
    // variations of the actual current working directory (e.g. /actual/dir or
    // /actual/dir////).  This adjustment serves two purposes:
    //
    //   1) it makes the compiler's current-directory line directive output agree with its cwd,
    //      given by getProjectDirectoryRoot.  (If PWD and cwd are different names for the same
    //      directory, the compiler prefers PWD, but we expect cwd for DebugPathSanitizer.)
    //
    //   2) in the case where we're using post-linkd debug path replacement, we reserve room
    //      to expand the path later.
    //
    builder.environment().put(
        "PWD",
        // We only need to expand the working directory if compiling, as some compilers
        // (e.g. clang) ignore overrides set in the preprocessed source when embedding the
        // working directory in the debug info.
        operation == Operation.COMPILE_MUNGE_DEBUGINFO ?
            sanitizer.getExpandedPath(context.getProjectDirectoryRoot().toAbsolutePath()) :
            context.getProjectDirectoryRoot().toAbsolutePath().toString());

    return builder;
  }

  private ImmutableList<String> makePreprocessCommand() {
    return ImmutableList.<String>builder()
        .addAll(preprocessorCommand.get())
        .add("-x", inputType.getLanguage())
        .add("-E")
        .add(input.toString())
        .build();
  }

  private ImmutableList<String> makeCompileCommand(
      String inputFileName,
      String inputLanguage) {
    return ImmutableList.<String>builder()
        .addAll(compilerCommand.get())
        .add("-x", inputLanguage)
        .add("-c")
        .add(inputFileName)
        .add("-o")
        .add(output.toString())
        .build();
  }

  private void safeCloseProcessor(@Nullable FunctionLineProcessorThread processor) {
    if (processor != null) {
      try {
        processor.waitFor();
        processor.close();
      } catch (Exception ex) {
        LOG.warn(ex, "error closing processor");
      }
    }
  }

  private int executePiped(ExecutionContext context)
      throws IOException, InterruptedException {
    ByteArrayOutputStream preprocessError = new ByteArrayOutputStream();
    ProcessBuilder preprocessBuilder = makeSubprocessBuilder(context);
    preprocessBuilder.command(makePreprocessCommand());
    preprocessBuilder.redirectOutput(ProcessBuilder.Redirect.PIPE);

    ByteArrayOutputStream compileError = new ByteArrayOutputStream();
    ProcessBuilder compileBuilder = makeSubprocessBuilder(context);
    compileBuilder.command(
        makeCompileCommand(
            "-",
            inputType.getPreprocessedLanguage()));
    compileBuilder.redirectInput(ProcessBuilder.Redirect.PIPE);

    Process preprocess = null;
    Process compile = null;
    FunctionLineProcessorThread errorProcessorPreprocess = null;
    FunctionLineProcessorThread errorProcessorCompile = null;
    FunctionLineProcessorThread lineDirectiveMunger = null;

    try {
      LOG.debug(
          "Running command (pwd=%s): %s",
          preprocessBuilder.directory(),
          getDescription(context));

      preprocess = preprocessBuilder.start();
      compile = compileBuilder.start();

      errorProcessorPreprocess =
          new FunctionLineProcessorThread(
              preprocess.getErrorStream(),
              preprocessError,
              createErrorLineProcessor(context.getProjectDirectoryRoot()));
      errorProcessorPreprocess.start();

      errorProcessorCompile =
          new FunctionLineProcessorThread(
              compile.getErrorStream(),
              compileError,
              createErrorLineProcessor(context.getProjectDirectoryRoot()));
      errorProcessorCompile.start();

      lineDirectiveMunger =
          new FunctionLineProcessorThread(
              preprocess.getInputStream(),
              compile.getOutputStream(),
              createPreprocessOutputLineProcessor(context.getProjectDirectoryRoot()));
      lineDirectiveMunger.start();

      int compileStatus = compile.waitFor();
      int preprocessStatus = preprocess.waitFor();

      safeCloseProcessor(errorProcessorPreprocess);
      safeCloseProcessor(errorProcessorCompile);

      String preprocessErr = new String(preprocessError.toByteArray());
      if (!preprocessErr.isEmpty()) {
        context.getConsole().printErrorText(preprocessErr);
      }

      String compileErr = new String(compileError.toByteArray());
      if (!compileErr.isEmpty()) {
        context.getConsole().printErrorText(compileErr);
      }

      if (preprocessStatus != 0) {
        LOG.warn("error %d %s(preprocess) %s: %s", preprocessStatus,
            operation.toString().toLowerCase(), input, preprocessErr);
      }

      if (compileStatus != 0) {
        LOG.warn("error %d %s(compile) %s: %s", compileStatus,
            operation.toString().toLowerCase(), input, compileErr);
      }

      if (preprocessStatus != 0) {
        return preprocessStatus;
      }

      if (compileStatus != 0) {
        return compileStatus;
      }

      return 0;
    } finally {
      if (preprocess != null) {
        preprocess.destroy();
        preprocess.waitFor();
      }

      if (compile != null) {
        compile.destroy();
        compile.waitFor();
      }

      safeCloseProcessor(errorProcessorPreprocess);
      safeCloseProcessor(errorProcessorCompile);
      safeCloseProcessor(lineDirectiveMunger);
    }
  }

  private int executeOther(ExecutionContext context) throws Exception {
    ProcessBuilder builder = makeSubprocessBuilder(context);

    // If we're preprocessing, file output goes through stdout, so we can postprocess it.
    if (operation == Operation.PREPROCESS) {
      builder.command(makePreprocessCommand());
      builder.redirectOutput(ProcessBuilder.Redirect.PIPE);
    } else {
      builder.command(
          makeCompileCommand(
              input.toString(),
              inputType.getLanguage()));
    }

    LOG.debug(
        "Running command (pwd=%s): %s",
        builder.directory(),
        getDescription(context));

    // Start the process.
    Process process = builder.start();

    // We buffer error messages in memory, as these are typically small.
    ByteArrayOutputStream error = new ByteArrayOutputStream();

    // Open the temp file to write the intermediate output to and also fire up managed threads
    // to process the stdout and stderr lines from the preprocess command.
    int exitCode;
    try {
      try (FunctionLineProcessorThread errorProcessor =
               new FunctionLineProcessorThread(
                   process.getErrorStream(),
                   error,
                   createErrorLineProcessor(context.getProjectDirectoryRoot()))) {
        errorProcessor.start();

        // If we're preprocessing, we pipe the output through a processor to sanitize the line
        // markers.  So fire that up...
        if (operation == Operation.PREPROCESS) {
          try (OutputStream output =
                   context.getProjectFilesystem().newFileOutputStream(this.output);
               FunctionLineProcessorThread outputProcessor =
                   new FunctionLineProcessorThread(
                       process.getInputStream(),
                       output,
                       createPreprocessOutputLineProcessor(context.getProjectDirectoryRoot()))) {
            outputProcessor.start();
            outputProcessor.waitFor();
          } catch (Throwable thrown) {
            process.destroy();
            throw thrown;
          }
        }
        errorProcessor.waitFor();
      } catch (Throwable thrown) {
        process.destroy();
        throw thrown;
      }
      exitCode = process.waitFor();
    } finally {
      process.destroy();
      process.waitFor();
    }

    // If we generated any error output, print that to the console.
    String err = new String(error.toByteArray());
    if (!err.isEmpty()) {
      context.getConsole().printErrorText(err);
    }

    return exitCode;
  }

  @Override
  public int execute(ExecutionContext context) throws InterruptedException {
    try {
      LOG.debug("%s %s -> %s", operation.toString().toLowerCase(), input, output);

      // We need completely different logic if we're piping from the preprocessor to the compiler.
      int exitCode;
      if (operation == Operation.PIPED_PREPROCESS_AND_COMPILE) {
        exitCode = executePiped(context);
      } else {
        exitCode = executeOther(context);
      }

      // If the compilation completed successfully and we didn't effect debug-info normalization
      // through #line directive modification, perform the in-place update of the compilation per
      // above.  This locates the relevant debug section and swaps out the expanded actual
      // compilation directory with the one we really want.
      if (exitCode == 0 && operation == Operation.COMPILE_MUNGE_DEBUGINFO) {
        try {
          sanitizer.restoreCompilationDirectory(
              context.getProjectDirectoryRoot().toAbsolutePath().resolve(output),
              context.getProjectDirectoryRoot().toAbsolutePath());
        } catch (IOException e) {
          context.logError(e, "error updating compilation directory");
          return 1;
        }
      }

      if (exitCode != 0) {
        LOG.warn("error %d %s %s", exitCode, operation.toString().toLowerCase(), input);
      }

      return exitCode;

    } catch (Exception e) {
      MoreThrowables.propagateIfInterrupt(e);
      context.getConsole().printBuildFailureWithStacktrace(e);
      return 1;
    }
  }

  public ImmutableList<String> getCommand() {
    switch (operation) {
      case COMPILE:
      case COMPILE_MUNGE_DEBUGINFO:
        return makeCompileCommand(
            input.toString(),
            inputType.getLanguage());
      case PREPROCESS:
        return makePreprocessCommand();
      // $CASES-OMITTED$
      default:
        throw new RuntimeException("invalid operation type");
    }
  }

  public String getDescriptionNoContext() {
    switch (operation) {
      case PIPED_PREPROCESS_AND_COMPILE: {
        return Joiner.on(' ').join(
            FluentIterable.from(makePreprocessCommand())
            .transform(Escaper.SHELL_ESCAPER)) +
            " | " +
            Joiner.on(' ').join(
                FluentIterable.from(
                    makeCompileCommand(
                        "-",
                        inputType.getPreprocessedLanguage()))
                .transform(Escaper.SHELL_ESCAPER));

      }
      // $CASES-OMITTED$
      default: {
        return Joiner.on(' ').join(
            FluentIterable.from(getCommand())
            .transform(Escaper.SHELL_ESCAPER));
      }
    }
  }

  @Override
  public String getDescription(ExecutionContext context) {
    return getDescriptionNoContext();
  }

  public enum Operation {
    COMPILE,
    COMPILE_MUNGE_DEBUGINFO,
    PREPROCESS,
    PIPED_PREPROCESS_AND_COMPILE,
    ;

    public boolean isPreprocess() {
      return this == COMPILE_MUNGE_DEBUGINFO ||
          this == PREPROCESS ||
          this == PIPED_PREPROCESS_AND_COMPILE;
    }

    public boolean isCompile() {
      return this == COMPILE ||
          this == COMPILE_MUNGE_DEBUGINFO ||
          this == PIPED_PREPROCESS_AND_COMPILE;
    }

  }

}


File: src/com/facebook/buck/cxx/DebugPathSanitizer.java
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

import static com.facebook.buck.cxx.DebugSectionProperty.COMPRESSED;
import static com.facebook.buck.cxx.DebugSectionProperty.STRINGS;
import static java.nio.channels.FileChannel.MapMode.READ_WRITE;
import static java.nio.file.StandardOpenOption.READ;
import static java.nio.file.StandardOpenOption.WRITE;

import com.facebook.buck.log.Logger;
import com.google.common.base.Charsets;
import com.google.common.base.Function;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.base.Strings;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.collect.ImmutableBiMap;
import com.google.common.collect.ImmutableMap;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.ExecutionException;

/**
 * Encapsulates all the logic to sanitize debug paths in native code.  Currently, this just
 * supports sanitizing the compilation directory that compilers typically embed in binaries
 * when including debug sections (e.g. using "-g" with gcc/clang inserts the compilation
 * directory in the DW_AT_comp_dir DWARF field).
 */
public class DebugPathSanitizer {

  private static final DebugSectionFinder DEBUG_SECTION_FINDER = new DebugSectionFinder();

  private final int pathSize;
  private final char separator;
  private final Path compilationDirectory;
  private final ImmutableBiMap<Path, Path> other;

  private final LoadingCache<Path, ImmutableBiMap<Path, Path>> pathCache =
      CacheBuilder
          .newBuilder()
          .softValues()
          .build(new CacheLoader<Path, ImmutableBiMap<Path, Path>>() {
            @Override
            public ImmutableBiMap<Path, Path> load(Path key) {
              return getAllPathsWork(key);
            }
          });

  /**
   * @param pathSize fix paths to this size for in-place replacements.
   * @param separator the path separator used to fill paths aren't of {@code pathSize} length.
   * @param compilationDirectory the desired path to replace the actual compilation directory with.
   */
  public DebugPathSanitizer(
      int pathSize,
      char separator,
      Path compilationDirectory,
      ImmutableBiMap<Path, Path> other) {
    this.pathSize = pathSize;
    this.separator = separator;
    this.compilationDirectory = compilationDirectory;
    this.other = other;
  }

  /**
   * @return the given path as a string, expanded using {@code separator} to fulfill the required
   *     {@code pathSize}.
   */
  public String getExpandedPath(Path path) {
    Preconditions.checkArgument(path.toString().length() <= pathSize);
    return Strings.padEnd(path.toString(), pathSize, separator);
  }

  private ImmutableBiMap<Path, Path> getAllPaths(Optional<Path> workingDir) {
    if (!workingDir.isPresent()) {
      return other;
    }

    try {
      return pathCache.get(workingDir.get());
    } catch (ExecutionException e) {
      Logger.get(DebugPathSanitizer.class).error(
          "Problem loading paths into cache",
          e);
      return getAllPathsWork(workingDir.get());
    }
  }

  private ImmutableBiMap<Path, Path> getAllPathsWork(Path workingDir) {
    ImmutableBiMap.Builder<Path, Path> builder = ImmutableBiMap.builder();
    builder.put(workingDir, compilationDirectory);
    builder.putAll(other);
    return builder.build();
  }

  public String getCompilationDirectory() {
    return getExpandedPath(compilationDirectory);
  }

  public Function<String, String> sanitize(
      final Optional<Path> workingDir,
      final boolean expandPaths) {
    return new Function<String, String>() {
      @Override
      public String apply(String input) {
        return DebugPathSanitizer.this.sanitize(workingDir, input, expandPaths);
      }
    };
  }

  /**
   * @param workingDir the current working directory, if applicable.
   * @param contents the string to sanitize.
   * @param expandPaths whether to pad sanitized paths to {@code pathSize}.
   * @return a string with all matching paths replaced with their sanitized versions.
   */
  public String sanitize(Optional<Path> workingDir, String contents, boolean expandPaths) {
    for (Map.Entry<Path, Path> entry : getAllPaths(workingDir).entrySet()) {
      String replacement;
      if (expandPaths) {
        replacement = getExpandedPath(entry.getValue());
      } else {
        replacement = entry.getValue().toString();
      }
      String pathToReplace = entry.getKey().toString();
      if (contents.contains(pathToReplace)) {
        // String.replace creates a number of objects, and creates a fair
        // amount of object churn at this level, so we avoid doing it if
        // it's essentially going to be a no-op.
        contents = contents.replace(pathToReplace, replacement);
      }
    }
    return contents;
  }

  public String sanitize(Optional<Path> workingDir, String contents) {
    return sanitize(workingDir, contents, /* expandPaths */ true);
  }

  public String restore(Optional<Path> workingDir, String contents) {
    for (Map.Entry<Path, Path> entry : getAllPaths(workingDir).entrySet()) {
      contents = contents.replace(getExpandedPath(entry.getValue()), entry.getKey().toString());
    }
    return contents;
  }

  /**
   * Run {@code replacer} on all relevant debug sections in {@code buffer}, falling back to
   * processing the entire {@code buffer} if the format is unrecognized.
   */
  private void restore(ByteBuffer buffer, ByteBufferReplacer replacer) {

    // Find the debug sections in the file represented by the buffer.
    Optional<ImmutableMap<String, DebugSection>> results = DEBUG_SECTION_FINDER.find(buffer);

    // If we were able to recognize the file format and find debug symbols, perform the
    // replacement on them.  Otherwise, just do a find-and-replace on the whole blob.
    if (results.isPresent()) {
      for (DebugSection section : results.get().values()) {
        // We can't do in-place updates on compressed debug sections.
        Preconditions.checkState(!section.properties.contains(COMPRESSED));
        if (section.properties.contains(STRINGS)) {
          replacer.replace(section.body);
        }
      }
    } else {
      replacer.replace(buffer);
    }
  }

  private void restore(Path path, ByteBufferReplacer replacer) throws IOException {
    try (FileChannel channel = FileChannel.open(path, READ, WRITE)) {
      MappedByteBuffer buffer = channel.map(READ_WRITE, 0, channel.size());
      restore(buffer, replacer);
    }
  }

  /**
   * @return a {@link ByteBufferReplacer} suitable for replacing {@code workingDir} with
   *     {@code compilationDirectory}.
   */
  private ByteBufferReplacer getCompilationDirectoryReplacer(Path workingDir) {
    return new ByteBufferReplacer(
        ImmutableMap.of(
            getExpandedPath(workingDir).getBytes(Charsets.US_ASCII),
            getExpandedPath(compilationDirectory).getBytes(Charsets.US_ASCII)));
  }

  // Construct the replacer, giving the expanded current directory and the desired directory.
  // We use ASCII, since all the relevant debug standards we care about (e.g. DWARF) use it.
  public void restoreCompilationDirectory(Path path, Path workingDir) throws IOException {
    restore(path, getCompilationDirectoryReplacer(workingDir));
  }

}


File: test/com/facebook/buck/cxx/DebugPathSanitizerTest.java
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

import static org.hamcrest.Matchers.equalTo;
import static org.junit.Assert.assertThat;

import com.google.common.base.Optional;
import com.google.common.collect.ImmutableBiMap;

import org.junit.Before;
import org.junit.Test;

import java.nio.file.Paths;

public class DebugPathSanitizerTest {

  DebugPathSanitizer debugPathSanitizer;

  @Before
  public void setUp() {
    debugPathSanitizer = new DebugPathSanitizer(
        40,
        '/',
        Paths.get("."),
        ImmutableBiMap.of(
            Paths.get("/some/absolute/path"),
            Paths.get("SYMBOLIC_NAME"),
            Paths.get("/another/path/with/subdirectories"),
            Paths.get("OTHER_NAME_WITH_SUFFIX"),
            Paths.get("/another/path"),
            Paths.get("OTHER_NAME")));
  }

  @Test
  public void sanitizeWithoutAnyMatchesWithExpandPaths() {
    assertThat(
        debugPathSanitizer.sanitize(
            Optional.of(Paths.get("/project/root")),
            "an arbitrary string with no match",
            /* expandPaths */ true),
        equalTo("an arbitrary string with no match"));
  }

  @Test
  public void sanitizeWithoutAnyMatchesWithoutExpandPaths() {
    assertThat(
        debugPathSanitizer.sanitize(
            Optional.of(Paths.get("/project/root")),
            "an arbitrary string with no match",
            /* expandPaths */ false),
        equalTo("an arbitrary string with no match"));
  }

  @Test
  public void sanitizeProjectRootWithExpandPaths() {
    assertThat(
        debugPathSanitizer.sanitize(
            Optional.of(Paths.get("/project/root")),
            "a string that mentions the /project/root somewhere",
            /* expandPaths */ true),
        equalTo("a string that mentions the ./////////////////////////////////////// somewhere"));
  }

  @Test
  public void sanitizeProjectRootWithoutExpandPaths() {
    assertThat(
        debugPathSanitizer.sanitize(
            Optional.of(Paths.get("/project/root")),
            "a string that mentions the /project/root somewhere",
            /* expandPaths */ false),
        equalTo("a string that mentions the . somewhere"));
  }

  @Test
  public void sanitizeOtherDirectoriesWithExpandPaths() {
    assertThat(
        debugPathSanitizer.sanitize(
            Optional.of(Paths.get("/project/root")),
            "-I/some/absolute/path/dir -I/another/path",
            /* expandPaths */ true),
        equalTo(
            "-ISYMBOLIC_NAME////////////////////////////dir " +
                "-IOTHER_NAME//////////////////////////////"));
  }

  @Test
  public void sanitizeOtherDirectoriesWithoutExpandPaths() {
    assertThat(
        debugPathSanitizer.sanitize(
            Optional.of(Paths.get("/project/root")),
            "-I/some/absolute/path/dir -I/another/path",
            /* expandPaths */ false),
        equalTo("-ISYMBOLIC_NAME/dir -IOTHER_NAME"));
  }

  @Test
  public void sanitizeDirectoriesThatArePrefixOfOtherDirectoriesWithExpandPaths() {
    assertThat(
        debugPathSanitizer.sanitize(
            Optional.of(Paths.get("/project/root")),
            "-I/another/path/with/subdirectories/something",
            /* expandPaths */ true),
        equalTo("-IOTHER_NAME_WITH_SUFFIX///////////////////something"));
  }

  @Test
  public void sanitizeDirectoriesThatArePrefixOfOtherDirectoriesWithoutExpandPaths() {
    assertThat(
        debugPathSanitizer.sanitize(
            Optional.of(Paths.get("/project/root")),
            "-I/another/path/with/subdirectories/something",
            /* expandPaths */ false),
        equalTo("-IOTHER_NAME_WITH_SUFFIX/something"));
  }

  @Test
  public void restoreWithoutAnyMatches() {
    assertThat(
        debugPathSanitizer.restore(
            Optional.of(Paths.get("/project/root")),
            "an arbitrary string with no match"),
        equalTo("an arbitrary string with no match"));
  }

  @Test
  public void restoreProjectRoot() {
    assertThat(
        debugPathSanitizer.restore(
            Optional.of(Paths.get("/project/root")),
            "a string that mentions the ./////////////////////////////////////// somewhere"),
        equalTo("a string that mentions the /project/root somewhere"));
  }

  @Test
  public void restoreOtherDirectories() {
    assertThat(
        debugPathSanitizer.restore(
            Optional.of(Paths.get("/project/root")),
            "-ISYMBOLIC_NAME////////////////////////////dir " +
                "-IOTHER_NAME//////////////////////////////"),
        equalTo("-I/some/absolute/path/dir -I/another/path"));
  }

  @Test
  public void restoreDirectoriesThatArePrefixOfOtherDirectories() {
    assertThat(
        debugPathSanitizer.restore(
            Optional.of(Paths.get("/project/root")),
            "-IOTHER_NAME_WITH_SUFFIX///////////////////something"),
        equalTo("-I/another/path/with/subdirectories/something"));
  }

  @Test
  public void restoreDoesNotTouchUnexpandedPaths() {
    assertThat(
        debugPathSanitizer.restore(
            Optional.of(Paths.get("/project/root")),
            ". -ISYMBOLIC_NAME/ OTHER_NAME"),
        equalTo(". -ISYMBOLIC_NAME/ OTHER_NAME"));
  }

}
