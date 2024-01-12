Refactoring Types: ['Extract Method']
stractApplePlatform.java
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

import com.facebook.buck.util.immutables.BuckStyleImmutable;

import org.immutables.value.Value;

@Value.Immutable
@BuckStyleImmutable
abstract class AbstractApplePlatform implements Comparable<AbstractApplePlatform> {
  class Name {
    public static final String IPHONEOS = "iphoneos";
    public static final String IPHONESIMULATOR = "iphonesimulator";
    public static final String MACOSX = "macosx";

    private Name() { }
  }

  /**
   * The full name of the platform. For example: {@code macosx}.
   */
  public abstract String getName();

  @Override
  public int compareTo(AbstractApplePlatform other) {
    return getName().compareTo(other.getName());
  }
}


File: src/com/facebook/buck/apple/AppleCxxPlatforms.java
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

import com.facebook.buck.cli.BuckConfig;
import com.facebook.buck.cxx.BsdArchiver;
import com.facebook.buck.cxx.ClangCompiler;
import com.facebook.buck.cxx.CxxBuckConfig;
import com.facebook.buck.cxx.CxxPlatform;
import com.facebook.buck.cxx.CxxPlatforms;
import com.facebook.buck.cxx.DarwinLinker;
import com.facebook.buck.cxx.DebugPathSanitizer;
import com.facebook.buck.cxx.VersionedTool;
import com.facebook.buck.io.ExecutableFinder;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.rules.Tool;
import com.facebook.buck.util.HumanReadableException;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Functions;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableBiMap;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Utility class to create Objective-C/C/C++/Objective-C++ platforms to
 * support building iOS and Mac OS X products with Xcode.
 */
public class AppleCxxPlatforms {

  // Utility class, do not instantiate.
  private AppleCxxPlatforms() { }

  private static final Path USR_BIN = Paths.get("usr/bin");

  public static AppleCxxPlatform build(
      AppleSdk targetSdk,
      String minVersion,
      String targetArchitecture,
      AppleSdkPaths sdkPaths,
      BuckConfig buckConfig) {
    return buildWithExecutableChecker(
        targetSdk,
        minVersion,
        targetArchitecture,
        sdkPaths,
        buckConfig,
        new ExecutableFinder());
  }

  @VisibleForTesting
  static AppleCxxPlatform buildWithExecutableChecker(
      AppleSdk targetSdk,
      String minVersion,
      String targetArchitecture,
      AppleSdkPaths sdkPaths,
      BuckConfig buckConfig,
      ExecutableFinder executableFinder) {

    ImmutableList.Builder<Path> toolSearchPathsBuilder = ImmutableList.builder();
    // Search for tools from most specific to least specific.
    toolSearchPathsBuilder
        .add(sdkPaths.getSdkPath().resolve(USR_BIN))
        .add(sdkPaths.getSdkPath().resolve("Developer").resolve(USR_BIN))
        .add(sdkPaths.getPlatformPath().resolve("Developer").resolve(USR_BIN));
    for (Path toolchainPath : sdkPaths.getToolchainPaths()) {
      toolSearchPathsBuilder.add(toolchainPath.resolve(USR_BIN));
    }
    if (sdkPaths.getDeveloperPath().isPresent()) {
      toolSearchPathsBuilder.add(sdkPaths.getDeveloperPath().get().resolve(USR_BIN));
      toolSearchPathsBuilder.add(sdkPaths.getDeveloperPath().get().resolve("Tools"));
    }
    ImmutableList<Path> toolSearchPaths = toolSearchPathsBuilder.build();

    // TODO(user): Add more and better cflags.
    ImmutableList.Builder<String> cflagsBuilder = ImmutableList.builder();
    cflagsBuilder.add("-isysroot", sdkPaths.getSdkPath().toString());
    cflagsBuilder.add("-arch", targetArchitecture);
    switch (targetSdk.getApplePlatform().getName()) {
      case ApplePlatform.Name.IPHONEOS:
        cflagsBuilder.add("-mios-version-min=" + minVersion);
        break;
      case ApplePlatform.Name.IPHONESIMULATOR:
        cflagsBuilder.add("-mios-simulator-version-min=" + minVersion);
        break;
      default:
        // For Mac builds, -mmacosx-version-min=<version>.
        cflagsBuilder.add(
            "-m" + targetSdk.getApplePlatform().getName() + "-version-min=" + minVersion);
        break;
    }

    ImmutableList<String> ldflags = ImmutableList.of("-sdk_version", targetSdk.getVersion());
    ImmutableList<String> asflags = ImmutableList.of("-arch", targetArchitecture);

    ImmutableList.Builder<String> versionsBuilder = ImmutableList.builder();
    versionsBuilder.add(targetSdk.getVersion());
    for (AppleToolchain toolchain : targetSdk.getToolchains()) {
      versionsBuilder.add(toolchain.getVersion());
    }
    String version = Joiner.on(':').join(versionsBuilder.build());

    Tool clangPath = new VersionedTool(
        getToolPath("clang", toolSearchPaths, executableFinder),
        ImmutableList.<String>of(),
        "apple-clang",
        version);

    Tool clangXxPath = new VersionedTool(
        getToolPath("clang++", toolSearchPaths, executableFinder),
        ImmutableList.<String>of(),
        "apple-clang++",
        version);

    Tool ar = new VersionedTool(
        getToolPath("ar", toolSearchPaths, executableFinder),
        ImmutableList.<String>of(),
        "apple-ar",
        version);

    Tool strip = new VersionedTool(
        getToolPath("strip", toolSearchPaths, executableFinder),
        ImmutableList.<String>of(),
        "apple-strip",
        version);

    Tool actool = new VersionedTool(
        getToolPath("actool", toolSearchPaths, executableFinder),
        ImmutableList.<String>of(),
        "apple-actool",
        version);

    Tool ibtool = new VersionedTool(
        getToolPath("ibtool", toolSearchPaths, executableFinder),
        ImmutableList.<String>of(),
        "apple-ibtool",
        version);

    Tool xctest = new VersionedTool(
        getToolPath("xctest", toolSearchPaths, executableFinder),
        ImmutableList.<String>of(),
        "apple-xctest",
        version);

    Optional<Tool> otest = getOptionalTool(
        "otest",
        toolSearchPaths,
        executableFinder,
        version);

    Tool dsymutil = new VersionedTool(
        getToolPath("dsymutil", toolSearchPaths, executableFinder),
        ImmutableList.<String>of(),
        "apple-dsymutil",
        version);

    CxxBuckConfig config = new CxxBuckConfig(buckConfig);

    ImmutableFlavor targetFlavor = ImmutableFlavor.of(
        ImmutableFlavor.replaceInvalidCharacters(
            targetSdk.getName() + "-" + targetArchitecture));

    ImmutableBiMap.Builder<Path, Path> sanitizerPaths = ImmutableBiMap.builder();
    sanitizerPaths.put(sdkPaths.getSdkPath(), Paths.get("APPLE_SDKROOT"));
    sanitizerPaths.put(sdkPaths.getPlatformPath(), Paths.get("APPLE_PLATFORM_DIR"));
    if (sdkPaths.getDeveloperPath().isPresent()) {
      sanitizerPaths.put(sdkPaths.getDeveloperPath().get(), Paths.get("APPLE_DEVELOPER_DIR"));
    }

    DebugPathSanitizer debugPathSanitizer = new DebugPathSanitizer(
        250,
        File.separatorChar,
        Paths.get("."),
        sanitizerPaths.build());

    ImmutableList<String> cflags = cflagsBuilder.build();

    ImmutableMap.Builder<String, String> macrosBuilder = ImmutableMap.builder();
    macrosBuilder.put("SDKROOT", sdkPaths.getSdkPath().toString());
    macrosBuilder.put("PLATFORM_DIR", sdkPaths.getPlatformPath().toString());
    if (sdkPaths.getDeveloperPath().isPresent()) {
      macrosBuilder.put("DEVELOPER_DIR", sdkPaths.getDeveloperPath().get().toString());
    }
    ImmutableMap<String, String> macros = macrosBuilder.build();

    CxxPlatform cxxPlatform = CxxPlatforms.build(
        targetFlavor,
        config,
        clangPath,
        clangPath,
        new ClangCompiler(clangPath),
        new ClangCompiler(clangXxPath),
        clangPath,
        clangXxPath,
        new DarwinLinker(clangPath),
        new DarwinLinker(clangXxPath),
        ldflags,
        strip,
        new BsdArchiver(ar),
        asflags,
        ImmutableList.<String>of(),
        cflags,
        ImmutableList.<String>of(),
        getOptionalTool("lex", toolSearchPaths, executableFinder, version),
        getOptionalTool("yacc", toolSearchPaths, executableFinder, version),
        "dylib",
        Optional.of(debugPathSanitizer),
        macros);

    return AppleCxxPlatform.builder()
        .setCxxPlatform(cxxPlatform)
        .setAppleSdk(targetSdk)
        .setAppleSdkPaths(sdkPaths)
        .setActool(actool)
        .setIbtool(ibtool)
        .setXctest(xctest)
        .setOtest(otest)
        .setDsymutil(dsymutil)
        .build();
  }

  private static Optional<Tool> getOptionalTool(
      String tool,
      ImmutableList<Path> toolSearchPaths,
      ExecutableFinder executableFinder,
      String version) {
    return getOptionalToolPath(tool, toolSearchPaths, executableFinder)
        .transform(VersionedTool.fromPath(tool, version))
        .transform(Functions.<Tool>identity());
  }

  private static Path getToolPath(
      String tool,
      ImmutableList<Path> toolSearchPaths,
      ExecutableFinder executableFinder) {
    Optional<Path> result = getOptionalToolPath(tool, toolSearchPaths, executableFinder);
    if (!result.isPresent()) {
      throw new HumanReadableException("Cannot find tool %s in paths %s", tool, toolSearchPaths);
    }
    return result.get();
  }

    private static Optional<Path> getOptionalToolPath(
      String tool,
      ImmutableList<Path> toolSearchPaths,
      ExecutableFinder executableFinder) {

      return executableFinder.getOptionalExecutable(
          Paths.get(tool),
          toolSearchPaths,
          ImmutableSet.<String>of());
  }

}


File: src/com/facebook/buck/apple/AppleSdkDiscovery.java
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

import com.dd.plist.NSArray;
import com.dd.plist.NSDictionary;
import com.dd.plist.NSObject;
import com.dd.plist.NSString;
import com.dd.plist.PropertyListParser;
import com.facebook.buck.log.Logger;
import com.facebook.buck.util.VersionStringComparator;
import com.google.common.base.Function;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Ordering;
import com.google.common.collect.TreeMultimap;

import java.io.BufferedInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;

/**
 * Utility class to discover the location of SDKs contained inside an Xcode
 * installation.
 */
public class AppleSdkDiscovery {

  private static final Logger LOG = Logger.get(AppleSdkDiscovery.class);

  private static final Ordering<AppleSdk> APPLE_SDK_VERSION_ORDERING =
    Ordering
        .from(new VersionStringComparator())
        .onResultOf(new Function<AppleSdk, String>() {
            @Override
            public String apply(AppleSdk appleSdk) {
                return appleSdk.getVersion();
            }
        });

  private static final String DEFAULT_TOOLCHAIN_ID = "com.apple.dt.toolchain.XcodeDefault";

  // Utility class; do not instantiate.
  private AppleSdkDiscovery() { }

  /**
   * Given a path to an Xcode developer directory and a map of
   * (xctoolchain ID: path) pairs as returned by
   * {@link AppleToolchainDiscovery}, walks through the platforms
   * and builds a map of ({@link AppleSdk}: {@link AppleSdkPaths})
   * objects describing the paths to the SDKs inside.
   *
   * The {@link AppleSdk#getName()} strings match the ones displayed by {@code xcodebuild -showsdks}
   * and look like {@code macosx10.9}, {@code iphoneos8.0}, {@code iphonesimulator8.0},
   * etc.
   */
  public static ImmutableMap<AppleSdk, AppleSdkPaths> discoverAppleSdkPaths(
      Optional<Path> developerDir,
      ImmutableList<Path> extraDirs,
      ImmutableMap<String, AppleToolchain> xcodeToolchains)
      throws IOException {
    Optional<AppleToolchain> defaultToolchain =
        Optional.fromNullable(xcodeToolchains.get(DEFAULT_TOOLCHAIN_ID));

    ImmutableMap.Builder<AppleSdk, AppleSdkPaths> appleSdkPathsBuilder = ImmutableMap.builder();

    Iterable<Path> platformPaths = extraDirs;
    if (developerDir.isPresent()) {
      Path platformsDir = developerDir.get().resolve("Platforms");
      LOG.debug("Searching for Xcode platforms under %s", platformsDir);
      platformPaths = Iterables.concat(
        ImmutableSet.of(platformsDir), platformPaths);
    }

    // We need to find the most recent SDK for each platform so we can
    // make the fall-back SDKs with no version number in their name
    // ("macosx", "iphonesimulator", "iphoneos").
    //
    // To do this, we store a map of (platform: [sdk1, sdk2, ...])
    // pairs where the SDKs for each platform are ordered by version.
    TreeMultimap<ApplePlatform, AppleSdk> orderedSdksForPlatform =
        TreeMultimap.create(
            Ordering.natural(),
            APPLE_SDK_VERSION_ORDERING);

    for (Path platforms : platformPaths) {
      if (!Files.exists(platforms)) {
        LOG.debug("Skipping platform search path %s that does not exist", platforms);
        continue;
      }
      LOG.debug("Searching for Xcode SDKs in %s", platforms);

      try (DirectoryStream<Path> platformStream = Files.newDirectoryStream(
          platforms,
               "*.platform")) {
        for (Path platformDir : platformStream) {
          Path developerSdksPath = platformDir.resolve("Developer/SDKs");
          try (DirectoryStream<Path> sdkStream = Files.newDirectoryStream(
                   developerSdksPath,
                   "*.sdk")) {
            for (Path sdkDir : sdkStream) {
              LOG.debug("Fetching SDK name for %s", sdkDir);
              if (Files.isSymbolicLink(sdkDir)) {
                continue;
              }

              AppleSdk.Builder sdkBuilder = AppleSdk.builder();
              if (buildSdkFromPath(sdkDir, sdkBuilder, xcodeToolchains, defaultToolchain)) {
                AppleSdk sdk = sdkBuilder.build();
                LOG.debug("Found SDK %s", sdk);

                AppleSdkPaths.Builder xcodePathsBuilder = AppleSdkPaths.builder();
                for (AppleToolchain toolchain : sdk.getToolchains()) {
                  xcodePathsBuilder.addToolchainPaths(toolchain.getPath());
                }
                AppleSdkPaths xcodePaths = xcodePathsBuilder
                    .setDeveloperPath(developerDir)
                    .setPlatformPath(platformDir)
                    .setSdkPath(sdkDir)
                    .build();
                appleSdkPathsBuilder.put(sdk, xcodePaths);
                orderedSdksForPlatform.put(sdk.getApplePlatform(), sdk);
              }
            }
          } catch (NoSuchFileException e) {
            LOG.warn(
                e,
                "Couldn't discover SDKs at path %s, ignoring platform %s",
                developerSdksPath,
                platformDir);
          }
        }
      }
    }

    // Get a snapshot of what's in appleSdkPathsBuilder, then for each
    // ApplePlatform, add to appleSdkPathsBuilder the most recent
    // SDK with an unversioned name.
    ImmutableMap<AppleSdk, AppleSdkPaths> discoveredSdkPaths = appleSdkPathsBuilder.build();

    for (ApplePlatform platform : orderedSdksForPlatform.keySet()) {
      AppleSdk mostRecentSdkForPlatform = orderedSdksForPlatform.get(platform).last();
      if (!mostRecentSdkForPlatform.getName().equals(platform.getName())) {
        appleSdkPathsBuilder.put(
            mostRecentSdkForPlatform.withName(platform.getName()),
            discoveredSdkPaths.get(mostRecentSdkForPlatform));
      }
    }

    // This includes both the discovered SDKs with versions in their names, as well as
    // the unversioned aliases added just above.
    return appleSdkPathsBuilder.build();
  }

  private static void addArchitecturesForPlatform(
      AppleSdk.Builder sdkBuilder,
      ApplePlatform applePlatform) {
    // TODO(user): These need to be read from the SDK, not hard-coded.
    switch (applePlatform.getName()) {
      case ApplePlatform.Name.MACOSX:
        // Fall through.
      case ApplePlatform.Name.IPHONESIMULATOR:
        sdkBuilder.addArchitectures("i386", "x86_64");
        break;
      case ApplePlatform.Name.IPHONEOS:
        sdkBuilder.addArchitectures("armv7", "arm64");
        break;
      default:
        sdkBuilder.addArchitectures("armv7", "arm64", "i386", "x86_64");
        break;
    }
  }

  private static boolean buildSdkFromPath(
        Path sdkDir,
        AppleSdk.Builder sdkBuilder,
        ImmutableMap<String, AppleToolchain> xcodeToolchains,
        Optional<AppleToolchain> defaultToolchain) throws IOException {
    try (InputStream sdkSettingsPlist = Files.newInputStream(sdkDir.resolve("SDKSettings.plist"));
         BufferedInputStream bufferedSdkSettingsPlist = new BufferedInputStream(sdkSettingsPlist)) {
      NSDictionary sdkSettings;
      try {
        sdkSettings = (NSDictionary) PropertyListParser.parse(bufferedSdkSettingsPlist);
      } catch (Exception e) {
        throw new IOException(e);
      }
      String name = sdkSettings.objectForKey("CanonicalName").toString();
      String version = sdkSettings.objectForKey("Version").toString();
      NSDictionary defaultProperties = (NSDictionary) sdkSettings.objectForKey("DefaultProperties");

      boolean foundToolchain = false;
      NSArray toolchains = (NSArray) sdkSettings.objectForKey("Toolchains");
      if (toolchains != null) {
        for (NSObject toolchainIdObject : toolchains.getArray()) {
          String toolchainId = toolchainIdObject.toString();
          AppleToolchain toolchain = xcodeToolchains.get(toolchainId);
          if (toolchain != null) {
            foundToolchain = true;
            sdkBuilder.addToolchains(toolchain);
          } else {
            LOG.debug("Specified toolchain %s not found for SDK path %s", toolchainId, sdkDir);
          }
        }
      }
      if (!foundToolchain && defaultToolchain.isPresent()) {
        foundToolchain = true;
        sdkBuilder.addToolchains(defaultToolchain.get());
      }
      if (!foundToolchain) {
        LOG.warn("No toolchains found and no default toolchain. Skipping SDK path %s.", sdkDir);
        return false;
      } else {
        NSString platformName = (NSString) defaultProperties.objectForKey("PLATFORM_NAME");
        ApplePlatform applePlatform =
            ApplePlatform.builder().setName(platformName.toString()).build();
        sdkBuilder.setName(name).setVersion(version).setApplePlatform(applePlatform);
        addArchitecturesForPlatform(sdkBuilder, applePlatform);
        return true;
      }
    } catch (FileNotFoundException e) {
      LOG.error(e, "No SDKSettings.plist found under SDK path %s", sdkDir);
      return false;
    }
  }
}


File: test/com/facebook/buck/apple/AppleCxxPlatformsTest.java
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

import static com.facebook.buck.testutil.HasConsecutiveItemsMatcher.hasConsecutiveItems;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.hasItems;
import static org.hamcrest.Matchers.is;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThat;

import com.facebook.buck.cli.BuckConfig;
import com.facebook.buck.cxx.CxxBuckConfig;
import com.facebook.buck.cli.FakeBuckConfig;
import com.facebook.buck.cxx.CxxLinkableEnhancer;
import com.facebook.buck.cxx.CxxPlatform;
import com.facebook.buck.cxx.CxxPlatforms;
import com.facebook.buck.cxx.CxxPreprocessAndCompile;
import com.facebook.buck.cxx.CxxPreprocessMode;
import com.facebook.buck.cxx.CxxPreprocessorInput;
import com.facebook.buck.cxx.CxxSource;
import com.facebook.buck.cxx.CxxSourceRuleFactory;
import com.facebook.buck.cxx.Linker;
import com.facebook.buck.io.AlwaysFoundExecutableFinder;
import com.facebook.buck.io.FakeExecutableFinder;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.model.Flavor;
import com.facebook.buck.model.ImmutableFlavor;
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
import com.facebook.buck.util.HumanReadableException;
import com.google.common.base.Optional;
import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;

import org.hamcrest.Matchers;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Map;

/**
 * Unit tests for {@link AppleCxxPlatforms}.
 */
public class AppleCxxPlatformsTest {

  @Rule
  public ExpectedException thrown = ExpectedException.none();

  @Test
  public void appleSdkPathsBuiltFromDirectory() throws Exception {
    AppleSdkPaths appleSdkPaths =
        AppleSdkPaths.builder()
            .setDeveloperPath(Paths.get("."))
            .addToolchainPaths(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(Paths.get("Platforms/iPhoneOS.platform"))
            .setSdkPath(Paths.get("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS8.0.sdk"))
            .build();

    AppleToolchain toolchain = AppleToolchain.builder()
        .setIdentifier("com.apple.dt.XcodeDefault")
        .setPath(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();

    AppleSdk targetSdk = AppleSdk.builder()
        .setApplePlatform(
            ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
        .setName("iphoneos8.0")
        .setVersion("8.0")
        .setToolchains(ImmutableList.of(toolchain))
        .build();

    ImmutableSet<Path> paths = ImmutableSet.<Path>builder()
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/dsymutil"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/strip"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/libtool"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/ar"))
        .add(Paths.get("usr/bin/actool"))
        .add(Paths.get("usr/bin/ibtool"))
        .add(Paths.get("usr/bin/xctest"))
        .add(Paths.get("Tools/otest"))
        .build();

    AppleCxxPlatform appleCxxPlatform =
        AppleCxxPlatforms.buildWithExecutableChecker(
            targetSdk,
            "7.0",
            "armv7",
            appleSdkPaths,
            new FakeBuckConfig(),
            new FakeExecutableFinder(paths));

    CxxPlatform cxxPlatform = appleCxxPlatform.getCxxPlatform();

    SourcePathResolver resolver = new SourcePathResolver(new BuildRuleResolver());

    assertEquals(
        ImmutableList.of("usr/bin/actool"),
        appleCxxPlatform.getActool().getCommandPrefix(resolver));
    assertEquals(
        ImmutableList.of("usr/bin/ibtool"),
        appleCxxPlatform.getIbtool().getCommandPrefix(resolver));
    assertEquals(
        ImmutableList.of("Toolchains/XcodeDefault.xctoolchain/usr/bin/dsymutil"),
        appleCxxPlatform.getDsymutil().getCommandPrefix(resolver));

    assertEquals(
        ImmutableList.of("usr/bin/xctest"),
        appleCxxPlatform.getXctest().getCommandPrefix(resolver));
    assertThat(appleCxxPlatform.getOtest().isPresent(), is(true));
    assertEquals(
        ImmutableList.of("Tools/otest"),
        appleCxxPlatform.getOtest().get().getCommandPrefix(resolver));

    assertEquals(
        ImmutableFlavor.of("iphoneos8.0-armv7"),
        cxxPlatform.getFlavor());
    assertEquals(
        Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang").toString(),
        cxxPlatform.getCc().getCommandPrefix(resolver).get(0));
    assertThat(
        ImmutableList.<String>builder()
            .addAll(cxxPlatform.getCc().getCommandPrefix(resolver))
            .addAll(cxxPlatform.getCflags())
            .build(),
        hasConsecutiveItems(
            "-isysroot",
            Paths.get("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS8.0.sdk").toString()));
    assertThat(
        cxxPlatform.getCflags(),
        hasConsecutiveItems("-arch", "armv7"));
    assertThat(
        cxxPlatform.getAsflags(),
        hasConsecutiveItems("-arch", "armv7"));
    assertThat(
        cxxPlatform.getCflags(),
        hasConsecutiveItems("-mios-version-min=7.0"));
    assertThat(
        cxxPlatform.getLdflags(),
        hasConsecutiveItems(
            "-sdk_version",
            "8.0"));
    assertEquals(
        Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++").toString(),
        cxxPlatform.getCxx().getCommandPrefix(resolver).get(0));
    assertEquals(
        Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/ar")
            .toString(),
        cxxPlatform.getAr().getCommandPrefix(resolver).get(0));
  }

  @Test
  public void platformWithoutOtestIsValid() throws Exception {
    AppleSdkPaths appleSdkPaths =
        AppleSdkPaths.builder()
            .setDeveloperPath(Paths.get("."))
            .addToolchainPaths(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(Paths.get("Platforms/iPhoneOS.platform"))
            .setSdkPath(Paths.get("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS9.0.sdk"))
            .build();

    AppleToolchain toolchain = AppleToolchain.builder()
        .setIdentifier("com.apple.dt.XcodeDefault")
        .setPath(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();

    AppleSdk targetSdk = AppleSdk.builder()
        .setApplePlatform(
            ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
        .setName("iphoneos9.0")
        .setVersion("9.0")
        .setToolchains(ImmutableList.of(toolchain))
        .build();

    ImmutableSet<Path> paths = ImmutableSet.<Path>builder()
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/dsymutil"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/strip"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/libtool"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/ar"))
        .add(Paths.get("usr/bin/actool"))
        .add(Paths.get("usr/bin/ibtool"))
        .add(Paths.get("usr/bin/xctest"))
        .build();

    AppleCxxPlatform appleCxxPlatform =
        AppleCxxPlatforms.buildWithExecutableChecker(
            targetSdk,
            "7.0",
            "armv7",
            appleSdkPaths,
            new FakeBuckConfig(),
            new FakeExecutableFinder(paths));

    assertThat(appleCxxPlatform.getOtest().isPresent(), is(false));
  }

  @Test
  public void invalidFlavorCharactersInSdkAreEscaped() throws Exception {
    AppleSdkPaths appleSdkPaths =
        AppleSdkPaths.builder()
            .setDeveloperPath(Paths.get("."))
            .addToolchainPaths(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(Paths.get("Platforms/iPhoneOS.platform"))
            .setSdkPath(Paths.get("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS8.0.sdk"))
            .build();

    ImmutableSet<Path> paths = ImmutableSet.<Path>builder()
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/dsymutil"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/strip"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/libtool"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/ar"))
        .add(Paths.get("usr/bin/actool"))
        .add(Paths.get("usr/bin/ibtool"))
        .add(Paths.get("usr/bin/xctest"))
        .add(Paths.get("Tools/otest"))
        .build();

    AppleToolchain toolchain = AppleToolchain.builder()
        .setIdentifier("com.apple.dt.XcodeDefault")
        .setPath(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();

    AppleSdk targetSdk = AppleSdk.builder()
        .setApplePlatform(
            ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
        .setName("_(in)+va|id_")
        .setVersion("8.0")
        .setToolchains(ImmutableList.of(toolchain))
        .build();

    AppleCxxPlatform appleCxxPlatform =
        AppleCxxPlatforms.buildWithExecutableChecker(
            targetSdk,
            "7.0",
            "cha+rs",
            appleSdkPaths,
            new FakeBuckConfig(),
            new FakeExecutableFinder(paths));

    assertEquals(
        ImmutableFlavor.of("__in__va_id_-cha_rs"),
        appleCxxPlatform.getCxxPlatform().getFlavor());
  }

  @Test
  public void cxxToolParamsReadFromBuckConfig() throws Exception {
    AppleSdkPaths appleSdkPaths =
        AppleSdkPaths.builder()
            .setDeveloperPath(Paths.get("."))
            .addToolchainPaths(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(Paths.get("Platforms/iPhoneOS.platform"))
            .setSdkPath(Paths.get("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS8.0.sdk"))
            .build();

    ImmutableSet<Path> paths = ImmutableSet.<Path>builder()
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/dsymutil"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/strip"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/libtool"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/ar"))
        .add(Paths.get("usr/bin/actool"))
        .add(Paths.get("usr/bin/ibtool"))
        .add(Paths.get("usr/bin/xctest"))
        .add(Paths.get("Tools/otest"))
        .build();

    AppleToolchain toolchain = AppleToolchain.builder()
        .setIdentifier("com.apple.dt.XcodeDefault")
        .setPath(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();

    AppleSdk targetSdk = AppleSdk.builder()
        .setApplePlatform(
            ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
        .setName("iphoneos8.0")
        .setVersion("8.0")
        .setToolchains(ImmutableList.of(toolchain))
        .build();

    AppleCxxPlatform appleCxxPlatform =
        AppleCxxPlatforms.buildWithExecutableChecker(
            targetSdk,
            "7.0",
            "armv7",
            appleSdkPaths,
            new FakeBuckConfig(
                ImmutableMap.of(
                    "cxx", ImmutableMap.of(
                        "cflags", "-std=gnu11",
                        "cppflags", "-DCTHING",
                        "cxxflags", "-std=c++11",
                        "cxxppflags", "-DCXXTHING"))),
            new FakeExecutableFinder(paths));

    CxxPlatform cxxPlatform = appleCxxPlatform.getCxxPlatform();

    assertThat(
        cxxPlatform.getCflags(),
        hasItem("-std=gnu11"));
    assertThat(
        cxxPlatform.getCppflags(),
        hasItems("-std=gnu11", "-DCTHING"));
    assertThat(
        cxxPlatform.getCxxflags(),
        hasItem("-std=c++11"));
    assertThat(
        cxxPlatform.getCxxppflags(),
        hasItems("-std=c++11", "-DCXXTHING"));
  }

  @Test
  public void cxxToolParamsReadFromBuckConfigWithGenFlavor() throws Exception {
AppleSdkPaths appleSdkPaths =
        AppleSdkPaths.builder()
            .setDeveloperPath(Paths.get("."))
            .addToolchainPaths(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(Paths.get("Platforms/iPhoneOS.platform"))
            .setSdkPath(Paths.get("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS8.0.sdk"))
            .build();

    ImmutableSet<Path> paths = ImmutableSet.<Path>builder()
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/dsymutil"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/strip"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/libtool"))
        .add(Paths.get("Platforms/iPhoneOS.platform/Developer/usr/bin/ar"))
        .add(Paths.get("usr/bin/actool"))
        .add(Paths.get("usr/bin/ibtool"))
        .add(Paths.get("usr/bin/xctest"))
        .add(Paths.get("Tools/otest"))
        .build();

    AppleToolchain toolchain = AppleToolchain.builder()
        .setIdentifier("com.apple.dt.XcodeDefault")
        .setPath(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();

    AppleSdk targetSdk = AppleSdk.builder()
        .setApplePlatform(
            ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
        .setName("iphoneos8.0")
        .setVersion("8.0")
        .setToolchains(ImmutableList.of(toolchain))
        .build();


    Flavor testFlavor = ImmutableFlavor.of("test-flavor");

    BuckConfig config = new FakeBuckConfig(
                ImmutableMap.of(
                    "cxx", ImmutableMap.of(
                        "cflags", "-std=gnu11",
                        "cppflags", "-DCTHING",
                        "cxxflags", "-std=c++11",
                        "cxxppflags", "-DCXXTHING"),
                    "cxx#" + testFlavor.toString(), ImmutableMap.of(
                        "cflags", "-Wnoerror",
                        "cppflags", "-DCTHING2",
                        "cxxflags", "-Woption",
                        "cxxppflags", "-DCXXTHING2",
                        "default_platform", "iphoneos8.0-armv7")));

    AppleCxxPlatform appleCxxPlatform =
        AppleCxxPlatforms.buildWithExecutableChecker(
            targetSdk,
            "7.0",
            "armv7",
            appleSdkPaths,
            config,
            new FakeExecutableFinder(paths));

    CxxPlatform defaultCxxPlatform = appleCxxPlatform.getCxxPlatform();

    CxxPlatform cxxPlatform = CxxPlatforms.copyPlatformWithFlavorAndConfig(
      defaultCxxPlatform,
        new CxxBuckConfig(config, testFlavor),
        testFlavor);

    assertThat(
        cxxPlatform.getCflags(),
        hasItems("-std=gnu11", "-Wnoerror"));
    assertThat(
        cxxPlatform.getCppflags(),
        hasItems("-std=gnu11",  "-Wnoerror", "-DCTHING", "-DCTHING2"));
    assertThat(
        cxxPlatform.getCxxflags(),
        hasItems("-std=c++11", "-Woption"));
    assertThat(
        cxxPlatform.getCxxppflags(),
        hasItems("-std=c++11", "-Woption", "-DCXXTHING", "-DCXXTHING2"));
  }

  @Test
  public void pathNotFoundThrows() throws Exception {
    thrown.expect(HumanReadableException.class);
    thrown.expectMessage(containsString("Cannot find tool"));
    AppleSdkPaths appleSdkPaths =
        AppleSdkPaths.builder()
            .setDeveloperPath(Paths.get("."))
            .addToolchainPaths(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(Paths.get("Platforms/iPhoneOS.platform"))
            .setSdkPath(Paths.get("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS8.0.sdk"))
            .build();

    AppleToolchain toolchain = AppleToolchain.builder()
        .setIdentifier("com.apple.dt.XcodeDefault")
        .setPath(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();

    AppleSdk targetSdk = AppleSdk.builder()
        .setApplePlatform(
            ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
        .setName("iphoneos8.0")
        .setVersion("8.0")
        .setToolchains(ImmutableList.of(toolchain))
        .build();

    AppleCxxPlatforms.buildWithExecutableChecker(
        targetSdk,
        "7.0",
        "armv7",
        appleSdkPaths,
        new FakeBuckConfig(),
        new FakeExecutableFinder(ImmutableSet.<Path>of()));
  }

  @Test
  public void simulatorPlatformSetsLinkerFlags() throws Exception {
    AppleSdkPaths appleSdkPaths = AppleSdkPaths.builder()
        .setDeveloperPath(Paths.get("."))
        .addToolchainPaths(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
        .setPlatformPath(Paths.get("Platforms/iPhoneOS.platform"))
        .setSdkPath(Paths.get("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneSimulator8.0.sdk"))
        .build();

    ImmutableSet<Path> paths = ImmutableSet.<Path>builder()
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/dsymutil"))
        .add(Paths.get("Toolchains/XcodeDefault.xctoolchain/usr/bin/strip"))
        .add(Paths.get("Platforms/iPhoneSimulator.platform/Developer/usr/bin/libtool"))
        .add(Paths.get("Platforms/iPhoneSimulator.platform/Developer/usr/bin/ar"))
        .add(Paths.get("usr/bin/actool"))
        .add(Paths.get("usr/bin/ibtool"))
        .add(Paths.get("usr/bin/xctest"))
        .add(Paths.get("Tools/otest"))
        .build();

    AppleToolchain toolchain = AppleToolchain.builder()
        .setIdentifier("com.apple.dt.XcodeDefault")
        .setPath(Paths.get("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();

    AppleSdk targetSdk = AppleSdk.builder()
        .setApplePlatform(
            ApplePlatform.builder().setName(ApplePlatform.Name.IPHONESIMULATOR).build())
        .setName("iphonesimulator8.0")
        .setVersion("8.0")
        .setToolchains(ImmutableList.of(toolchain))
        .build();

    AppleCxxPlatform appleCxxPlatform =
        AppleCxxPlatforms.buildWithExecutableChecker(
            targetSdk,
            "7.0",
            "armv7",
            appleSdkPaths,
            new FakeBuckConfig(),
            new FakeExecutableFinder(paths));

    CxxPlatform cxxPlatform = appleCxxPlatform.getCxxPlatform();

    assertThat(
        cxxPlatform.getCflags(),
        hasItem("-mios-simulator-version-min=7.0"));
    assertThat(
        cxxPlatform.getCxxldflags(),
        hasItem("-mios-simulator-version-min=7.0"));
  }

  enum Operation {
    PREPROCESS,
    COMPILE,
    PREPROCESS_AND_COMPILE,
  }

  // Create and return some rule keys from a dummy source for the given platforms.
  private ImmutableMap<Flavor, RuleKey> constructCompileRuleKeys(
      Operation operation,
      ImmutableMap<Flavor, AppleCxxPlatform> cxxPlatforms) {
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
    ImmutableMap.Builder<Flavor, RuleKey> ruleKeys =
        ImmutableMap.builder();
    for (Map.Entry<Flavor, AppleCxxPlatform> entry : cxxPlatforms.entrySet()) {
      CxxSourceRuleFactory cxxSourceRuleFactory =
          new CxxSourceRuleFactory(
              BuildRuleParamsFactory.createTrivialBuildRuleParams(target),
              resolver,
              pathResolver,
              entry.getValue().getCxxPlatform(),
              ImmutableList.<CxxPreprocessorInput>of(),
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
  private ImmutableMap<Flavor, RuleKey> constructLinkRuleKeys(
      ImmutableMap<Flavor, AppleCxxPlatform> cxxPlatforms) {
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
    ImmutableMap.Builder<Flavor, RuleKey> ruleKeys =
        ImmutableMap.builder();
    for (Map.Entry<Flavor, AppleCxxPlatform> entry : cxxPlatforms.entrySet()) {
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

  private AppleCxxPlatform buildAppleCxxPlatform(Path root) {
    AppleSdkPaths appleSdkPaths = AppleSdkPaths.builder()
        .setDeveloperPath(root)
        .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
        .setPlatformPath(root.resolve("Platforms/iPhoneOS.platform"))
        .setSdkPath(
            root.resolve("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneSimulator8.0.sdk"))
        .build();
    AppleToolchain toolchain = AppleToolchain.builder()
        .setIdentifier("com.apple.dt.XcodeDefault")
        .setPath(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();
    AppleSdk targetSdk = AppleSdk.builder()
        .setApplePlatform(
            ApplePlatform.builder().setName(ApplePlatform.Name.IPHONESIMULATOR).build())
        .setName("iphonesimulator8.0")
        .setVersion("8.0")
        .setToolchains(ImmutableList.of(toolchain))
        .build();
    return AppleCxxPlatforms.buildWithExecutableChecker(
        targetSdk,
        "7.0",
        "armv7",
        appleSdkPaths,
        new FakeBuckConfig(),
        new AlwaysFoundExecutableFinder());
  }

  // The important aspects we check for in rule keys is that the host platform and the path
  // to the NDK don't cause changes.
  @Test
  public void checkRootAndPlatformDoNotAffectRuleKeys() throws IOException {
    Map<String, ImmutableMap<Flavor, RuleKey>> preprocessAndCompileRukeKeys = Maps.newHashMap();
    Map<String, ImmutableMap<Flavor, RuleKey>> preprocessRukeKeys = Maps.newHashMap();
    Map<String, ImmutableMap<Flavor, RuleKey>> compileRukeKeys = Maps.newHashMap();
    Map<String, ImmutableMap<Flavor, RuleKey>> linkRukeKeys = Maps.newHashMap();

    // Iterate building up rule keys for combinations of different platforms and NDK root
    // directories.
    for (String dir : ImmutableList.of("something", "something else")) {
      AppleCxxPlatform platform = buildAppleCxxPlatform(Paths.get(dir));
      preprocessAndCompileRukeKeys.put(
          String.format("AppleCxxPlatform(%s)", dir),
          constructCompileRuleKeys(
              Operation.PREPROCESS_AND_COMPILE,
              ImmutableMap.of(platform.getCxxPlatform().getFlavor(), platform)));
      preprocessRukeKeys.put(
          String.format("AppleCxxPlatform(%s)", dir),
          constructCompileRuleKeys(
              Operation.PREPROCESS,
              ImmutableMap.of(platform.getCxxPlatform().getFlavor(), platform)));
      compileRukeKeys.put(
          String.format("AppleCxxPlatform(%s)", dir),
          constructCompileRuleKeys(
              Operation.COMPILE,
              ImmutableMap.of(platform.getCxxPlatform().getFlavor(), platform)));
      linkRukeKeys.put(
          String.format("AppleCxxPlatform(%s)", dir),
          constructLinkRuleKeys(
              ImmutableMap.of(platform.getCxxPlatform().getFlavor(), platform)));
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


File: test/com/facebook/buck/apple/AppleLibraryIntegrationTest.java
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

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assume.assumeTrue;

import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargets;
import com.facebook.buck.model.ImmutableFlavor;
import com.facebook.buck.testutil.integration.DebuggableTemporaryFolder;
import com.facebook.buck.testutil.integration.ProjectWorkspace;
import com.facebook.buck.testutil.integration.TestDataHelper;
import com.facebook.buck.util.BuckConstant;
import com.facebook.buck.util.environment.Platform;

import org.junit.Rule;
import org.junit.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public class AppleLibraryIntegrationTest {

  @Rule
  public DebuggableTemporaryFolder tmp = new DebuggableTemporaryFolder();

  @Test
  public void testAppleLibraryBuildsSomething() throws IOException {
    assumeTrue(Platform.detect() == Platform.MACOS);
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this, "apple_library_builds_something", tmp);
    workspace.setUp();

    ProjectWorkspace.ProcessResult result = workspace.runBuckCommand(
        "build",
        "//Libraries/TestLibrary:TestLibrary#static,default");
    result.assertSuccess();

    assertTrue(Files.exists(tmp.getRootPath().resolve(BuckConstant.GEN_DIR)));
  }

  @Test
  public void testAppleLibraryBuildsSomethingUsingAppleCxxPlatform() throws IOException {
    assumeTrue(Platform.detect() == Platform.MACOS);
    assumeTrue(AppleNativeIntegrationTestUtils.isApplePlatformAvailable(
        ApplePlatform.builder().setName(ApplePlatform.Name.MACOSX).build()));

    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this, "apple_library_builds_something", tmp);
    workspace.setUp();

    ProjectWorkspace.ProcessResult result = workspace.runBuckCommand(
        "build",
        "//Libraries/TestLibrary:TestLibrary#static,macosx-x86_64");
    result.assertSuccess();

    assertTrue(Files.exists(tmp.getRootPath().resolve(BuckConstant.GEN_DIR)));
  }

  @Test
  public void testAppleLibraryHeaderSymlinkTree() throws IOException {
    assumeTrue(Platform.detect() == Platform.MACOS);

    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this, "apple_library_header_symlink_tree", tmp);
    workspace.setUp();

    BuildTarget buildTarget = BuildTarget.builder("//Libraries/TestLibrary", "TestLibrary")
        .addFlavors(ImmutableFlavor.of("default"))
        .addFlavors(ImmutableFlavor.of("header-symlink-tree"))
        .build();
    ProjectWorkspace.ProcessResult result = workspace.runBuckCommand(
        "build",
        buildTarget.getFullyQualifiedName());
    result.assertSuccess();

    Path projectRoot = tmp.getRootPath().toRealPath();

    Path inputPath = projectRoot.resolve(
        buildTarget.getBasePath());
    Path outputPath = projectRoot.resolve(
        BuildTargets.getGenPath(buildTarget, "%s"));

    assertIsSymbolicLink(
        outputPath.resolve("PrivateHeader.h"),
        inputPath.resolve("PrivateHeader.h"));
    assertIsSymbolicLink(
        outputPath.resolve("TestLibrary/PrivateHeader.h"),
        inputPath.resolve("PrivateHeader.h"));
    assertIsSymbolicLink(
        outputPath.resolve("PublicHeader.h"),
        inputPath.resolve("PublicHeader.h"));
  }

  @Test
  public void testAppleLibraryExportedHeaderSymlinkTree() throws IOException {
    assumeTrue(Platform.detect() == Platform.MACOS);

    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this, "apple_library_header_symlink_tree", tmp);
    workspace.setUp();

    BuildTarget buildTarget = BuildTarget.builder("//Libraries/TestLibrary", "TestLibrary")
        .addFlavors(ImmutableFlavor.of("default"))
        .addFlavors(ImmutableFlavor.of("exported-header-symlink-tree"))
        .build();
    ProjectWorkspace.ProcessResult result = workspace.runBuckCommand(
        "build",
        buildTarget.getFullyQualifiedName());
    result.assertSuccess();

    Path projectRoot = tmp.getRootPath().toRealPath();

    Path inputPath = projectRoot.resolve(
        buildTarget.getBasePath());
    Path outputPath = projectRoot.resolve(
        BuildTargets.getGenPath(buildTarget, "%s"));

    assertIsSymbolicLink(
        outputPath.resolve("TestLibrary/PublicHeader.h"),
        inputPath.resolve("PublicHeader.h"));
  }

  @Test
  public void testAppleLibraryIsHermetic() throws IOException {
    assumeTrue(Platform.detect() == Platform.MACOS);
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this, "apple_library_is_hermetic", tmp);
    workspace.setUp();

    ProjectWorkspace.ProcessResult first = workspace.runBuckCommand(
        workspace.getPath("first"),
        "build",
        "//Libraries/TestLibrary:TestLibrary#static,iphonesimulator-x86_64");
    first.assertSuccess();

    ProjectWorkspace.ProcessResult second = workspace.runBuckCommand(
        workspace.getPath("second"),
        "build",
        "//Libraries/TestLibrary:TestLibrary#static,iphonesimulator-x86_64");
    second.assertSuccess();

    assertTrue(
        com.google.common.io.Files.equal(
            workspace.getFile(
                "first/buck-out/gen/Libraries/TestLibrary/" +
                    "TestLibrary#compile-TestClass.m.o,iphonesimulator-x86_64/TestClass.m.o"),
            workspace.getFile(
                "second/buck-out/gen/Libraries/TestLibrary/" +
                    "TestLibrary#compile-TestClass.m.o,iphonesimulator-x86_64/TestClass.m.o")));
    assertTrue(
        com.google.common.io.Files.equal(
            workspace.getFile(
                "first/buck-out/gen/Libraries/TestLibrary/" +
                    "TestLibrary#iphonesimulator-x86_64,static/libTestLibrary.a"),
            workspace.getFile(
                "second/buck-out/gen/Libraries/TestLibrary/" +
                    "TestLibrary#iphonesimulator-x86_64,static/libTestLibrary.a")));
  }

  private static void assertIsSymbolicLink(
      Path link,
      Path target) throws IOException {
    assertTrue(Files.isSymbolicLink(link));
    assertEquals(
        target,
        Files.readSymbolicLink(link));
  }
}


File: test/com/facebook/buck/apple/AppleSdkDiscoveryTest.java
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

import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.equalTo;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;

import com.facebook.buck.testutil.integration.DebuggableTemporaryFolder;
import com.facebook.buck.testutil.integration.ProjectWorkspace;
import com.facebook.buck.testutil.integration.TestDataHelper;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Set;

public class AppleSdkDiscoveryTest {

  @Rule
  public DebuggableTemporaryFolder temp = new DebuggableTemporaryFolder();

  @Rule
  public ExpectedException thrown = ExpectedException.none();

  private AppleToolchain getDefaultToolchain(Path path) {
    return AppleToolchain.builder()
        .setIdentifier("com.apple.dt.toolchain.XcodeDefault")
        .setPath(path.resolve("Toolchains/XcodeDefault.xctoolchain"))
        .setVersion("1")
        .build();
  }

  @Test
  public void shouldReturnAnEmptyMapIfNoPlatformsFound() throws IOException {
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this,
        "sdk-discovery-empty",
        temp);
    workspace.setUp();
    Path path = workspace.getPath("");

    ImmutableMap<String, AppleToolchain> toolchains = ImmutableMap.of(
        "com.apple.dt.toolchain.XcodeDefault",
        getDefaultToolchain(path)
    );
    ImmutableMap<AppleSdk, AppleSdkPaths> sdks = AppleSdkDiscovery.discoverAppleSdkPaths(
        Optional.of(path),
        ImmutableList.<Path>of(),
        toolchains);

    assertEquals(0, sdks.size());
  }

  @Test
  public void shouldFindPlatformsInExtraPlatformDirectories() throws IOException {
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this,
        "sdk-discovery-minimal",
        temp);
    workspace.setUp();
    Path root = workspace.getPath("");

    ProjectWorkspace emptyWorkspace = TestDataHelper.createProjectWorkspaceForScenario(
        this,
        "sdk-discovery-empty",
        temp);
    emptyWorkspace.setUp();
    Path path = emptyWorkspace.getPath("");

    ImmutableMap<String, AppleToolchain> toolchains = ImmutableMap.of(
        "com.apple.dt.toolchain.XcodeDefault",
        getDefaultToolchain(path));

    AppleSdk macosx109Sdk =
        AppleSdk.builder()
            .setName("macosx10.9")
            .setVersion("10.9")
            .setApplePlatform(ApplePlatform.builder().setName(ApplePlatform.Name.MACOSX).build())
            .addArchitectures("i386", "x86_64")
            .addAllToolchains(toolchains.values())
            .build();
    AppleSdkPaths macosx109Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(path)
            .addToolchainPaths(path.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/MacOSX.platform"))
            .setSdkPath(root.resolve("Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.9.sdk"))
            .build();

    ImmutableMap<AppleSdk, AppleSdkPaths> expected =
        ImmutableMap.<AppleSdk, AppleSdkPaths>builder()
            .put(macosx109Sdk, macosx109Paths)
            .put(macosx109Sdk.withName("macosx"), macosx109Paths)
            .build();

    assertThat(
        AppleSdkDiscovery.discoverAppleSdkPaths(
            Optional.of(path),
            ImmutableList.of(root),
            toolchains),
        equalTo(expected));
  }

  @Test
  public void ignoresInvalidExtraPlatformDirectories() throws IOException {
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this,
        "sdk-discovery-minimal",
        temp);
    workspace.setUp();
    Path root = workspace.getPath("");

    Path path = Paths.get("invalid");

    ImmutableMap<String, AppleToolchain> toolchains = ImmutableMap.of(
        "com.apple.dt.toolchain.XcodeDefault",
        getDefaultToolchain(root));

    AppleSdk macosx109Sdk =
        AppleSdk.builder()
            .setName("macosx10.9")
            .setVersion("10.9")
            .setApplePlatform(ApplePlatform.builder().setName(ApplePlatform.Name.MACOSX).build())
            .addArchitectures("i386", "x86_64")
            .addAllToolchains(toolchains.values())
            .build();
    AppleSdkPaths macosx109Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/MacOSX.platform"))
            .setSdkPath(root.resolve("Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.9.sdk"))
            .build();

    ImmutableMap<AppleSdk, AppleSdkPaths> expected =
        ImmutableMap.<AppleSdk, AppleSdkPaths>builder()
            .put(macosx109Sdk, macosx109Paths)
            .put(macosx109Sdk.withName("macosx"), macosx109Paths)
            .build();

    assertThat(
        AppleSdkDiscovery.discoverAppleSdkPaths(
            Optional.of(root),
            ImmutableList.of(path),
            toolchains),
        equalTo(expected));
  }

  @Test
  public void shouldNotIgnoreSdkWithUnrecognizedPlatform() throws Exception {
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this,
        "sdk-unknown-platform-discovery",
        temp);
    workspace.setUp();
    Path root = workspace.getPath("");

    ImmutableMap<String, AppleToolchain> toolchains = ImmutableMap.of(
        "com.apple.dt.toolchain.XcodeDefault",
        getDefaultToolchain(root)
    );
    ImmutableMap<AppleSdk, AppleSdkPaths> sdks = AppleSdkDiscovery.discoverAppleSdkPaths(
        Optional.of(root),
        ImmutableList.<Path>of(),
        toolchains);

    assertEquals(2, sdks.size());
  }

  @Test
  public void shouldIgnoreSdkWithBadSymlink() throws Exception {
    Path root = temp.newFolder().toPath();

    // Create a dangling symlink
    File toDelete = File.createTempFile("foo", "bar");
    Path symlink = root.resolve("Platforms/Foo.platform/Developer/NonExistent1.0.sdk");
    Files.createDirectories(symlink.getParent());
    Files.createSymbolicLink(symlink, toDelete.toPath());
    assertTrue(toDelete.delete());

    ImmutableMap<String, AppleToolchain> toolchains = ImmutableMap.of(
        "com.apple.dt.toolchain.XcodeDefault",
        getDefaultToolchain(root)
    );
    ImmutableMap<AppleSdk, AppleSdkPaths> sdks = AppleSdkDiscovery.discoverAppleSdkPaths(
        Optional.of(root),
        ImmutableList.<Path>of(),
        toolchains);

    assertEquals(0, sdks.size());
  }

  @Test
  public void appleSdkPathsBuiltFromDirectory() throws Exception {
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this,
        "sdk-discovery",
        temp);
    workspace.setUp();
    Path root = workspace.getPath("");
    createSymLinkIosSdks(root, "8.0");

    AppleSdk macosx109Sdk =
        AppleSdk.builder()
            .setName("macosx10.9")
            .setVersion("10.9")
            .setApplePlatform(ApplePlatform.builder().setName(ApplePlatform.Name.MACOSX).build())
            .addArchitectures("i386", "x86_64")
            .addToolchains(getDefaultToolchain(root))
            .build();
    AppleSdkPaths macosx109Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/MacOSX.platform"))
            .setSdkPath(root.resolve("Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.9.sdk"))
            .build();

    AppleSdk iphoneos80Sdk =
        AppleSdk.builder()
            .setName("iphoneos8.0")
            .setVersion("8.0")
            .setApplePlatform(ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
            .addArchitectures("armv7", "arm64")
            .addToolchains(getDefaultToolchain(root))
            .build();
    AppleSdkPaths iphoneos80Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/iPhoneOS.platform"))
            .setSdkPath(root.resolve("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk"))
            .build();

    AppleSdk iphonesimulator80Sdk =
        AppleSdk.builder()
            .setName("iphonesimulator8.0")
            .setVersion("8.0")
            .setApplePlatform(
                ApplePlatform.builder().setName(ApplePlatform.Name.IPHONESIMULATOR).build())
            .addArchitectures("i386", "x86_64")
            .addToolchains(getDefaultToolchain(root))
            .build();
    AppleSdkPaths iphonesimulator80Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/iPhoneSimulator.platform"))
            .setSdkPath(
                root.resolve(
                    "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk"))
            .build();

    ImmutableMap<String, AppleToolchain> toolchains = ImmutableMap.of(
        "com.apple.dt.toolchain.XcodeDefault",
        getDefaultToolchain(root));

    ImmutableMap<AppleSdk, AppleSdkPaths> expected =
        ImmutableMap.<AppleSdk, AppleSdkPaths>builder()
            .put(macosx109Sdk, macosx109Paths)
            .put(macosx109Sdk.withName("macosx"), macosx109Paths)
            .put(iphoneos80Sdk, iphoneos80Paths)
            .put(iphoneos80Sdk.withName("iphoneos"), iphoneos80Paths)
            .put(iphonesimulator80Sdk, iphonesimulator80Paths)
            .put(iphonesimulator80Sdk.withName("iphonesimulator"), iphonesimulator80Paths)
            .build();

    assertThat(
        AppleSdkDiscovery.discoverAppleSdkPaths(
            Optional.of(root),
            ImmutableList.<Path>of(),
            toolchains),
        equalTo(expected));
  }

  @Test
  public void noAppleSdksFoundIfDefaultPlatformMissing() throws Exception {
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this,
        "sdk-discovery",
        temp);
    workspace.setUp();
    Path root = workspace.getPath("");

    ImmutableMap<String, AppleToolchain> toolchains = ImmutableMap.of();

    assertThat(
        AppleSdkDiscovery.discoverAppleSdkPaths(
            Optional.of(root),
            ImmutableList.<Path>of(),
            toolchains).entrySet(),
        empty());
  }

  @Test
  public void multipleAppleSdkPathsPerPlatformBuiltFromDirectory() throws Exception {
    ProjectWorkspace workspace = TestDataHelper.createProjectWorkspaceForScenario(
        this,
        "sdk-multi-version-discovery",
        temp);
    workspace.setUp();
    Path root = workspace.getPath("");

    createSymLinkIosSdks(root, "8.1");

    AppleSdk macosx109Sdk =
        AppleSdk.builder()
            .setName("macosx10.9")
            .setVersion("10.9")
            .setApplePlatform(ApplePlatform.builder().setName(ApplePlatform.Name.MACOSX).build())
            .addArchitectures("i386", "x86_64")
            .addToolchains(getDefaultToolchain(root))
            .build();
    AppleSdkPaths macosx109Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/MacOSX.platform"))
            .setSdkPath(root.resolve("Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.9.sdk"))
            .build();

    AppleSdk iphoneos80Sdk =
        AppleSdk.builder()
            .setName("iphoneos8.0")
            .setVersion("8.0")
            .setApplePlatform(ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
            .addArchitectures("armv7", "arm64")
            .addToolchains(getDefaultToolchain(root))
            .build();
    AppleSdkPaths iphoneos80Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/iPhoneOS.platform"))
            .setSdkPath(root.resolve("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS8.0.sdk"))
            .build();

    AppleSdk iphonesimulator80Sdk =
        AppleSdk.builder()
            .setName("iphonesimulator8.0")
            .setVersion("8.0")
            .setApplePlatform(
                ApplePlatform.builder().setName(ApplePlatform.Name.IPHONESIMULATOR).build())
            .addArchitectures("i386", "x86_64")
            .addToolchains(getDefaultToolchain(root))
            .build();
    AppleSdkPaths iphonesimulator80Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/iPhoneSimulator.platform"))
            .setSdkPath(
                root.resolve(
                    "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator8.0.sdk"))
            .build();

    AppleSdk iphoneos81Sdk =
        AppleSdk.builder()
            .setName("iphoneos8.1")
            .setVersion("8.1")
            .setApplePlatform(ApplePlatform.builder().setName(ApplePlatform.Name.IPHONEOS).build())
            .addArchitectures("armv7", "arm64")
            .addToolchains(getDefaultToolchain(root))
            .build();
    AppleSdkPaths iphoneos81Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/iPhoneOS.platform"))
            .setSdkPath(root.resolve("Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk"))
            .build();

    AppleSdk iphonesimulator81Sdk =
        AppleSdk.builder()
            .setName("iphonesimulator8.1")
            .setVersion("8.1")
            .setApplePlatform(
                ApplePlatform.builder().setName(ApplePlatform.Name.IPHONESIMULATOR).build())
            .addArchitectures("i386", "x86_64")
            .addToolchains(getDefaultToolchain(root))
            .build();
    AppleSdkPaths iphonesimulator81Paths =
        AppleSdkPaths.builder()
            .setDeveloperPath(root)
            .addToolchainPaths(root.resolve("Toolchains/XcodeDefault.xctoolchain"))
            .setPlatformPath(root.resolve("Platforms/iPhoneSimulator.platform"))
            .setSdkPath(
                root.resolve(
                    "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk"))
            .build();

    ImmutableMap<AppleSdk, AppleSdkPaths> expected =
        ImmutableMap.<AppleSdk, AppleSdkPaths>builder()
            .put(macosx109Sdk, macosx109Paths)
            .put(macosx109Sdk.withName("macosx"), macosx109Paths)
            .put(iphoneos80Sdk, iphoneos80Paths)
            .put(iphonesimulator80Sdk, iphonesimulator80Paths)
            .put(iphoneos81Sdk, iphoneos81Paths)
            .put(iphoneos81Sdk.withName("iphoneos"), iphoneos81Paths)
            .put(iphonesimulator81Sdk, iphonesimulator81Paths)
            .put(iphonesimulator81Sdk.withName("iphonesimulator"), iphonesimulator81Paths)
            .build();

    ImmutableMap<String, AppleToolchain> toolchains = ImmutableMap.of(
        "com.apple.dt.toolchain.XcodeDefault",
        getDefaultToolchain(root));

    assertThat(
        AppleSdkDiscovery.discoverAppleSdkPaths(
            Optional.of(root),
            ImmutableList.<Path>of(),
            toolchains),
        equalTo(expected));
  }

  private void createSymLinkIosSdks(Path root, String version) throws IOException {
    Set<String> sdks = ImmutableSet.of("iPhoneOS", "iPhoneSimulator");
    for (String sdk : sdks) {
      Path sdkDir = root.resolve(String.format("Platforms/%s.platform/Developer/SDKs", sdk));

      if (!Files.exists(sdkDir)) {
        continue;
      }

      Path actual = sdkDir.resolve(String.format("%s.sdk", sdk));
      Path link = sdkDir.resolve(String.format("%s%s.sdk", sdk, version));
      Files.createSymbolicLink(link, actual);
    }
  }
}
