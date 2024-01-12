Refactoring Types: ['Move Class']
ExopackageInstaller.java
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

package com.facebook.buck.cli;

import com.android.ddmlib.AdbCommandRejectedException;
import com.android.ddmlib.CollectingOutputReceiver;
import com.android.ddmlib.IDevice;
import com.android.ddmlib.InstallException;
import com.facebook.buck.android.agent.util.AgentUtil;
import com.facebook.buck.event.BuckEventBus;
import com.facebook.buck.event.ConsoleEvent;
import com.facebook.buck.event.TraceEventLogger;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.log.Logger;
import com.facebook.buck.rules.ExopackageInfo;
import com.facebook.buck.rules.InstallableApk;
import com.facebook.buck.step.ExecutionContext;
import com.facebook.buck.util.NamedTemporaryFile;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Charsets;
import com.google.common.base.Function;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.base.Predicates;
import com.google.common.base.Splitter;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;

import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.annotation.Nullable;

/**
 * ExopackageInstaller manages the installation of apps with the "exopackage" flag set to true.
 */
public class ExopackageInstaller {

  private static final Logger LOG = Logger.get(ExopackageInstaller.class);

  /**
   * Prefix of the path to the agent apk on the device.
   */
  private static final String AGENT_DEVICE_PATH = "/data/app/" + AgentUtil.AGENT_PACKAGE_NAME;

  /**
   * Command line to invoke the agent on the device.
   */
  private static final String JAVA_AGENT_COMMAND =
      "dalvikvm -classpath " +
      AGENT_DEVICE_PATH + "-1.apk:" + AGENT_DEVICE_PATH + "-2.apk:" +
      AGENT_DEVICE_PATH + "-1/base.apk:" + AGENT_DEVICE_PATH + "-2/base.apk " +
      "com.facebook.buck.android.agent.AgentMain ";

  /**
   * Maximum length of commands that can be passed to "adb shell".
   */
  private static final int MAX_ADB_COMMAND_SIZE = 1019;

  private static final Path SECONDARY_DEX_DIR = Paths.get("secondary-dex");

  private static final Path NATIVE_LIBS_DIR = Paths.get("native-libs");

  @VisibleForTesting
  static final Pattern DEX_FILE_PATTERN = Pattern.compile("secondary-([0-9a-f]+)\\.[\\w.-]*");

  @VisibleForTesting
  static final Pattern NATIVE_LIB_PATTERN = Pattern.compile("native-([0-9a-f]+)\\.so");

  private final ProjectFilesystem projectFilesystem;
  private final BuckEventBus eventBus;
  private final AdbHelper adbHelper;
  private final InstallableApk apkRule;
  private final String packageName;
  private final Path dataRoot;

  private final ExopackageInfo exopackageInfo;

  /**
   * The next port number to use for communicating with the agent on a device.
   * This resets for every instance of ExopackageInstaller,
   * but is incremented for every device we are installing on when using "-x".
   */
  private final AtomicInteger nextAgentPort = new AtomicInteger(2828);

  @VisibleForTesting
  static class PackageInfo {
    final String apkPath;
    final String nativeLibPath;
    final String versionCode;
    private PackageInfo(String apkPath, String nativeLibPath, String versionCode) {
      this.nativeLibPath = nativeLibPath;
      this.apkPath = apkPath;
      this.versionCode = versionCode;
    }
  }

  public ExopackageInstaller(
      ExecutionContext context,
      AdbHelper adbHelper,
      InstallableApk apkRule) {
    this.adbHelper = adbHelper;
    this.projectFilesystem = context.getProjectFilesystem();
    this.eventBus = context.getBuckEventBus();
    this.apkRule = apkRule;
    this.packageName = AdbHelper.tryToExtractPackageNameFromManifest(apkRule, context);
    this.dataRoot = Paths.get("/data/local/tmp/exopackage/").resolve(packageName);

    Preconditions.checkArgument(AdbHelper.PACKAGE_NAME_PATTERN.matcher(packageName).matches());

    Optional<ExopackageInfo> exopackageInfo = apkRule.getExopackageInfo();
    Preconditions.checkArgument(exopackageInfo.isPresent());
    this.exopackageInfo = exopackageInfo.get();
  }

  /**
   * Installs the app specified in the constructor.  This object should be discarded afterward.
   */
  public synchronized boolean install() throws InterruptedException {
    eventBus.post(InstallEvent.started(apkRule.getBuildTarget()));

    boolean success = adbHelper.adbCall(
        new AdbHelper.AdbCallable() {
          @Override
          public boolean call(IDevice device) throws Exception {
            try {
              return new SingleDeviceInstaller(device, nextAgentPort.getAndIncrement()).doInstall();
            } catch (Exception e) {
              throw new RuntimeException("Failed to install exopackage on " + device, e);
            }
          }

          @Override
          public String toString() {
            return "install exopackage";
          }
        });

    eventBus.post(InstallEvent.finished(apkRule.getBuildTarget(), success));
    return success;
  }

  /**
   * Helper class to manage the state required to install on a single device.
   */
  private class SingleDeviceInstaller {

    /**
     * Device that we are installing onto.
     */
    private final IDevice device;

    /**
     * Port to use for sending files to the agent.
     */
    private final int agentPort;

    /**
     * True iff we should use the native agent.
     */
    private boolean useNativeAgent = true;

    /**
     * Set after the agent is installed.
     */
    @Nullable
    private String nativeAgentPath;

    private SingleDeviceInstaller(IDevice device, int agentPort) {
      this.device = device;
      this.agentPort = agentPort;
    }

    boolean doInstall() throws Exception {
      Optional<PackageInfo> agentInfo = installAgentIfNecessary();
      if (!agentInfo.isPresent()) {
        return false;
      }

      nativeAgentPath = agentInfo.get().nativeLibPath;
      determineBestAgent();

      final File apk = apkRule.getApkPath().toFile();
      // TODO(user): Support SD installation.
      final boolean installViaSd = false;

      if (shouldAppBeInstalled()) {
        try (TraceEventLogger ignored = TraceEventLogger.start(eventBus, "install_exo_apk")) {
          boolean success = adbHelper.installApkOnDevice(device, apk, installViaSd);
          if (!success) {
            return false;
          }
        }
      }

      if (exopackageInfo.getDexInfo().isPresent()) {
        installSecondaryDexFiles();
      }

      if (exopackageInfo.getNativeLibsInfo().isPresent()) {
        installNativeLibraryFiles();
      }

      // TODO(user): Make this work on Gingerbread.
      try (TraceEventLogger ignored = TraceEventLogger.start(eventBus, "kill_app")) {
        AdbHelper.executeCommandWithErrorChecking(device, "am force-stop " + packageName);
      }

      return true;
    }

    private void installSecondaryDexFiles() throws Exception {
      final ImmutableMap<String, Path> hashToSources = getRequiredDexFiles();
      final ImmutableSet<String> requiredHashes = hashToSources.keySet();
      final ImmutableSet<String> presentHashes = prepareSecondaryDexDir(requiredHashes);
      final Set<String> hashesToInstall = Sets.difference(requiredHashes, presentHashes);

      Map<String, Path> filesToInstallByHash =
          Maps.filterKeys(hashToSources, Predicates.in(hashesToInstall));

      // This is a bit gross.  It was a late addition.  Ideally, we could eliminate this, but
      // it wouldn't be terrible if we don't.  We store the dexed jars on the device
      // with the full SHA-1 hashes in their names.  This is the format that the loader uses
      // internally, so ideally we would just load them in place.  However, the code currently
      // expects to be able to copy the jars from a directory that matches the name in the
      // metadata file, like "secondary-1.dex.jar".  We don't want to give up putting the
      // hashes in the file names (because we use that to skip re-uploads), so just hack
      // the metadata file to have hash-like names.
      String metadataContents = com.google.common.io.Files.toString(
          exopackageInfo.getDexInfo().get().getMetadata().toFile(),
          Charsets.UTF_8)
          .replaceAll(
              "secondary-(\\d+)\\.dex\\.jar (\\p{XDigit}{40}) ",
              "secondary-$2.dex.jar $2 ");

      installFiles(
          "secondary_dex",
          ImmutableMap.copyOf(filesToInstallByHash),
          metadataContents,
          "secondary-%s.dex.jar",
          SECONDARY_DEX_DIR);
    }

    private ImmutableList<String> getDeviceAbis() throws Exception {
      ImmutableList.Builder<String> abis = ImmutableList.builder();
      // Rare special indigenous to Lollipop devices
      String abiListProperty = getProperty("ro.product.cpu.abilist");
      if (!abiListProperty.isEmpty()) {
        abis.addAll(Splitter.on(',').splitToList(abiListProperty));
      } else {
        String abi1 = getProperty("ro.product.cpu.abi");
        if (abi1.isEmpty()) {
          throw new RuntimeException("adb returned empty result for ro.product.cpu.abi property.");
        }

        abis.add(abi1);
        String abi2 = getProperty("ro.product.cpu.abi2");
        if (!abi2.isEmpty()) {
          abis.add(abi2);
        }
      }

      return abis.build();
    }

    private void installNativeLibraryFiles() throws Exception {
      ImmutableMultimap<String, Path> allLibraries = getAllLibraries();
      ImmutableSet.Builder<String> providedLibraries = ImmutableSet.builder();
      for (String abi : getDeviceAbis()) {
        ImmutableMap<String, Path> libraries =
            getRequiredLibrariesForAbi(allLibraries, abi, providedLibraries.build());

        installNativeLibrariesForAbi(abi, libraries);
        providedLibraries.addAll(libraries.keySet());
      }
    }

    private void installNativeLibrariesForAbi(String abi, ImmutableMap<String, Path> libraries)
        throws Exception {
      if (libraries.isEmpty()) {
        return;
      }

      ImmutableSet<String> requiredHashes = libraries.keySet();
      ImmutableSet<String> presentHashes = prepareNativeLibsDir(abi, requiredHashes);

      Map<String, Path> filesToInstallByHash =
          Maps.filterKeys(libraries, Predicates.not(Predicates.in(presentHashes)));

      String metadataContents = Joiner.on('\n').join(
          FluentIterable.from(libraries.entrySet()).transform(
              new Function<Map.Entry<String, Path>, String>() {
                @Override
                public String apply(Map.Entry<String, Path> input) {
                  String hash = input.getKey();
                  String filename = input.getValue().getFileName().toString();
                  int index = filename.indexOf('.');
                  String libname = index == -1 ? filename : filename.substring(0, index);
                  return String.format("%s native-%s.so", libname, hash);
                }
              }));

      installFiles(
          "native_library",
          ImmutableMap.copyOf(filesToInstallByHash),
          metadataContents,
          "native-%s.so",
          NATIVE_LIBS_DIR.resolve(abi));
    }

    /**
     * Sets {@link #useNativeAgent} to true on pre-L devices, because our native agent is built
     * without -fPIC.  The java agent works fine on L as long as we don't use it for mkdir.
     */
    private void determineBestAgent() throws Exception {
      String value = getProperty("ro.build.version.sdk");
      try {
        if (Integer.valueOf(value.trim()) > 19) {
          useNativeAgent = false;
        }
      } catch (NumberFormatException exn) {
        useNativeAgent = false;
      }
    }

    private String getAgentCommand() {
      if (useNativeAgent) {
        return nativeAgentPath + "/libagent.so ";
      } else {
        return JAVA_AGENT_COMMAND;
      }
    }

    private Optional<PackageInfo> getPackageInfo(final String packageName) throws Exception {
      try (TraceEventLogger ignored = TraceEventLogger.start(
          eventBus,
          "get_package_info",
          ImmutableMap.of("package", packageName))) {

        /* This produces output that looks like

          Package [com.facebook.katana] (4229ce68):
            userId=10145 gids=[1028, 1015, 3003]
            pkg=Package{42690b80 com.facebook.katana}
            codePath=/data/app/com.facebook.katana-1.apk
            resourcePath=/data/app/com.facebook.katana-1.apk
            nativeLibraryPath=/data/app-lib/com.facebook.katana-1
            versionCode=1640376 targetSdk=14
            versionName=8.0.0.0.23

            ...

         */
        String lines = AdbHelper.executeCommandWithErrorChecking(
            device, "dumpsys package " + packageName);

        return parsePackageInfo(packageName, lines);
      }
    }

    /**
     * @return PackageInfo for the agent, or absent if installation failed.
     */
    private Optional<PackageInfo> installAgentIfNecessary() throws Exception {
      Optional<PackageInfo> agentInfo = getPackageInfo(AgentUtil.AGENT_PACKAGE_NAME);
      if (!agentInfo.isPresent()) {
        LOG.debug("Agent not installed.  Installing.");
        return installAgentApk();
      }
      LOG.debug("Agent version: %s", agentInfo.get().versionCode);
      if (!agentInfo.get().versionCode.equals(AgentUtil.AGENT_VERSION_CODE)) {
        // Always uninstall before installing.  We might be downgrading, which requires
        // an uninstall, or we might just want a clean installation.
        uninstallAgent();
        return installAgentApk();
      }
      return agentInfo;
    }

    private void uninstallAgent() throws InstallException {
      try (TraceEventLogger ignored = TraceEventLogger.start(eventBus, "uninstall_old_agent")) {
        device.uninstallPackage(AgentUtil.AGENT_PACKAGE_NAME);
      }
    }

    private Optional<PackageInfo> installAgentApk() throws Exception {
      try (TraceEventLogger ignored = TraceEventLogger.start(eventBus, "install_agent_apk")) {
        String apkFileName = System.getProperty("buck.android_agent_path");
        if (apkFileName == null) {
          throw new RuntimeException("Android agent apk path not specified in properties");
        }
        File apkPath = new File(apkFileName);
        boolean success = adbHelper.installApkOnDevice(device, apkPath, /* installViaSd */ false);
        if (!success) {
          return Optional.absent();
        }
        return getPackageInfo(AgentUtil.AGENT_PACKAGE_NAME);
      }
    }

    private boolean shouldAppBeInstalled() throws Exception {
      Optional<PackageInfo> appPackageInfo = getPackageInfo(packageName);
      if (!appPackageInfo.isPresent()) {
        eventBus.post(ConsoleEvent.info("App not installed.  Installing now."));
        return true;
      }

      LOG.debug("App path: %s", appPackageInfo.get().apkPath);
      String installedAppSignature = getInstalledAppSignature(appPackageInfo.get().apkPath);
      String localAppSignature = AgentUtil.getJarSignature(apkRule.getApkPath().toString());
      LOG.debug("Local app signature: %s", localAppSignature);
      LOG.debug("Remote app signature: %s", installedAppSignature);

      if (!installedAppSignature.equals(localAppSignature)) {
        LOG.debug("App signatures do not match.  Must re-install.");
        return true;
      }

      LOG.debug("App signatures match.  No need to install.");
      return false;
    }

    private String getInstalledAppSignature(final String packagePath) throws Exception {
      try (TraceEventLogger ignored = TraceEventLogger.start(eventBus, "get_app_signature")) {
        String command = getAgentCommand() + "get-signature " + packagePath;
        LOG.debug("Executing %s", command);
        String output = AdbHelper.executeCommandWithErrorChecking(device, command);

        String result = output.trim();
        if (result.contains("\n") || result.contains("\r")) {
          throw new IllegalStateException("Unexpected return from get-signature:\n" + output);
        }

        return result;
      }
    }

    private ImmutableMap<String, Path> getRequiredDexFiles() throws IOException {
      ExopackageInfo.DexInfo dexInfo = exopackageInfo.getDexInfo().get();
      ImmutableMultimap<String, Path> multimap = parseExopackageInfoMetadata(
          dexInfo.getMetadata(),
          dexInfo.getDirectory(),
          projectFilesystem);
      // Convert multimap to a map, because every key should have only one value.
      ImmutableMap.Builder<String, Path> builder = ImmutableMap.builder();
      for (Map.Entry<String, Path> entry : multimap.entries()) {
        builder.put(entry);
      }
      return builder.build();
    }

    private ImmutableSet<String> prepareSecondaryDexDir(ImmutableSet<String> requiredHashes)
        throws Exception {
      return prepareDirectory("secondary-dex", DEX_FILE_PATTERN, requiredHashes);
    }

    private ImmutableSet<String> prepareNativeLibsDir(
        String abi,
        ImmutableSet<String> requiredHashes) throws Exception {
      return prepareDirectory("native-libs/" + abi, NATIVE_LIB_PATTERN, requiredHashes);
    }

    private ImmutableSet<String> prepareDirectory(
        String dirname,
        Pattern filePattern,
        ImmutableSet<String> requiredHashes) throws Exception {
      try (TraceEventLogger ignored = TraceEventLogger.start(eventBus, "prepare_" + dirname)) {
        String dirPath = dataRoot.resolve(dirname).toString();
        mkDirP(dirPath);

        String output = AdbHelper.executeCommandWithErrorChecking(device, "ls " + dirPath);

        ImmutableSet.Builder<String> foundHashes = ImmutableSet.builder();
        ImmutableSet.Builder<String> filesToDelete = ImmutableSet.builder();

        processLsOutput(output, filePattern, requiredHashes, foundHashes, filesToDelete);

        String commandPrefix = "cd " + dirPath + " && rm ";
        // Add a fudge factor for separators and error checking.
        final int overhead = commandPrefix.length() + 100;
        for (List<String> rmArgs :
            chunkArgs(filesToDelete.build(), MAX_ADB_COMMAND_SIZE - overhead)) {
          String command = commandPrefix + Joiner.on(' ').join(rmArgs);
          LOG.debug("Executing %s", command);
          AdbHelper.executeCommandWithErrorChecking(device, command);
        }

        return foundHashes.build();
      }
    }

    private void installFiles(
        String filesType,
        ImmutableMap<String, Path> filesToInstallByHash,
        String metadataFileContents,
        String filenameFormat,
        Path destinationDirRelativeToDataRoot) throws Exception {
      try (TraceEventLogger ignored1 =
               TraceEventLogger.start(eventBus, "multi_install_" + filesType)) {
        device.createForward(agentPort, agentPort);
        try {
          for (Map.Entry<String, Path> entry : filesToInstallByHash.entrySet()) {
            Path destination = destinationDirRelativeToDataRoot.resolve(
                String.format(filenameFormat, entry.getKey()));
            Path source = entry.getValue();

            try (TraceEventLogger ignored2 =
                     TraceEventLogger.start(eventBus, "install_" + filesType)) {
              installFile(device, agentPort, destination, source);
            }
          }
          try (TraceEventLogger ignored3 =
                   TraceEventLogger.start(eventBus, "install_" + filesType + "_metadata")) {
            try (NamedTemporaryFile temp = new NamedTemporaryFile("metadata", "tmp")) {
              com.google.common.io.Files.write(
                  metadataFileContents.getBytes(Charsets.UTF_8),
                  temp.get().toFile());
              installFile(
                  device,
                  agentPort,
                  destinationDirRelativeToDataRoot.resolve("metadata.txt"),
                  temp.get());
            }
          }
        } finally {
          try {
            device.removeForward(agentPort, agentPort);
          } catch (AdbCommandRejectedException e) {
            LOG.warn(e, "Failed to remove adb forward on port %d for device %s", agentPort, device);
            eventBus.post(
                ConsoleEvent.warning(
                    "Failed to remove adb forward %d. This is not necessarily a problem\n" +
                        "because it will be recreated during the next exopackage installation.\n" +
                        "See the log for the full exception.",
                    agentPort));
          }
        }
      }
    }

    private void installFile(
        IDevice device,
        final int port,
        Path pathRelativeToDataRoot,
        final Path source) throws Exception {
      CollectingOutputReceiver receiver = new CollectingOutputReceiver() {

        private boolean sentPayload = false;

        @Override
        public void addOutput(byte[] data, int offset, int length) {
          super.addOutput(data, offset, length);
          if (!sentPayload && getOutput().length() >= AgentUtil.TEXT_SECRET_KEY_SIZE) {
            LOG.verbose("Got key: %s", getOutput().trim());

            sentPayload = true;
            try (Socket clientSocket = new Socket("localhost", port)) {
              LOG.verbose("Connected");
              OutputStream outToDevice = clientSocket.getOutputStream();
              outToDevice.write(
                  getOutput().substring(
                      0,
                      AgentUtil.TEXT_SECRET_KEY_SIZE).getBytes());
              LOG.verbose("Wrote key");
              com.google.common.io.Files.asByteSource(source.toFile()).copyTo(outToDevice);
              LOG.verbose("Wrote file");
            } catch (IOException e) {
              throw new RuntimeException(e);
            }
          }
        }
      };

      String targetFileName = dataRoot.resolve(pathRelativeToDataRoot).toString();
      String command =
          "umask 022 && " +
              getAgentCommand() +
              "receive-file " + port + " " + Files.size(source) + " " +
              targetFileName +
              " ; echo -n :$?";
      LOG.debug("Executing %s", command);

      // If we fail to execute the command, stash the exception.  My experience during development
      // has been that the exception from checkReceiverOutput is more actionable.
      Exception shellException = null;
      try {
        device.executeShellCommand(command, receiver);
      } catch (Exception e) {
        shellException = e;
      }

      try {
        AdbHelper.checkReceiverOutput(command, receiver);
      } catch (Exception e) {
        if (shellException != null) {
          e.addSuppressed(shellException);
        }
        throw e;
      }

      if (shellException != null) {
        throw shellException;
      }

      // The standard Java libraries on Android always create new files un-readable by other users.
      // We use the shell user or root to create these files, so we need to explicitly set the mode
      // to allow the app to read them.  Ideally, the agent would do this automatically, but
      // there's no easy way to do this in Java.  We can drop this if we drop support for the
      // Java agent.
      AdbHelper.executeCommandWithErrorChecking(device, "chmod 644 " + targetFileName);
    }

    private String getProperty(String property) throws Exception {
      return AdbHelper.executeCommandWithErrorChecking(device, "getprop " + property).trim();
    }

    private void mkDirP(String dirpath) throws Exception {
      // Kind of a hack here.  The java agent can't force the proper permissions on the
      // directories it creates, so we use the command-line "mkdir -p" instead of the java agent.
      // Fortunately, "mkdir -p" seems to work on all devices where we use use the java agent.
      String mkdirP = useNativeAgent ? getAgentCommand() + "mkdir-p" : "mkdir -p";

      AdbHelper.executeCommandWithErrorChecking(device, "umask 022 && " + mkdirP + " " + dirpath);
    }
  }

  private ImmutableMultimap<String, Path> getAllLibraries() throws IOException {
    ExopackageInfo.NativeLibsInfo nativeLibsInfo = exopackageInfo.getNativeLibsInfo().get();
    return parseExopackageInfoMetadata(
        nativeLibsInfo.getMetadata(),
        nativeLibsInfo.getDirectory(),
        projectFilesystem);
  }

  private ImmutableMap<String, Path> getRequiredLibrariesForAbi(
      ImmutableMultimap<String, Path> allLibraries,
      String abi,
      ImmutableSet<String> ignoreLibraries) throws IOException {
    return filterLibrariesForAbi(
        exopackageInfo.getNativeLibsInfo().get().getDirectory(),
        allLibraries,
        abi,
        ignoreLibraries);
  }

  @VisibleForTesting
  static ImmutableMap<String, Path> filterLibrariesForAbi(
      Path nativeLibsDir,
      ImmutableMultimap<String, Path> allLibraries,
      String abi,
      ImmutableSet<String> ignoreLibraries) {
    ImmutableMap.Builder<String, Path> filteredLibraries = ImmutableMap.builder();
    for (Map.Entry<String, Path> entry : allLibraries.entries()) {
      Path relativePath = nativeLibsDir.relativize(entry.getValue());
      Preconditions.checkState(relativePath.getNameCount() == 2);
      String libAbi = relativePath.getParent().toString();
      String libName = relativePath.getFileName().toString();
      if (libAbi.equals(abi) && !ignoreLibraries.contains(libName)) {
        filteredLibraries.put(entry);
      }
    }
    return filteredLibraries.build();
  }

  /**
   * Parses a text file which is supposed to be in the following format:
   * "file_path_without_spaces file_hash ...." i.e. it parses the first two columns of each line
   * and ignores the rest of it.
   *
   * @return  A multi map from the file hash to its path, which equals the raw path resolved against
   *     {@code resolvePathAgainst}.
   */
  @VisibleForTesting
  static ImmutableMultimap<String, Path> parseExopackageInfoMetadata(
      Path metadataTxt,
      Path resolvePathAgainst,
      ProjectFilesystem filesystem) throws IOException {
    ImmutableMultimap.Builder<String, Path> builder = ImmutableMultimap.builder();
    for (String line : filesystem.readLines(metadataTxt)) {
      List<String> parts = Splitter.on(' ').splitToList(line);
      if (parts.size() < 2) {
        throw new RuntimeException("Illegal line in metadata file: " + line);
      }
      builder.put(parts.get(1), resolvePathAgainst.resolve(parts.get(0)));
    }
    return builder.build();
  }

  @VisibleForTesting
  static Optional<PackageInfo> parsePackageInfo(String packageName, String lines) {
    final String packagePrefix = "  Package [" + packageName + "] (";
    final String otherPrefix = "  Package [";
    boolean sawPackageLine = false;
    final Splitter splitter = Splitter.on('=').limit(2);

    String codePath = null;
    String resourcePath = null;
    String nativeLibPath = null;
    String versionCode = null;

    for (String line : Splitter.on("\r\n").split(lines)) {
      // Just ignore everything until we see the line that says we are in the right package.
      if (line.startsWith(packagePrefix)) {
        sawPackageLine = true;
        continue;
      }
      // This should never happen, but if we do see a different package, stop parsing.
      if (line.startsWith(otherPrefix)) {
        break;
      }
      // Ignore lines before our package.
      if (!sawPackageLine) {
        continue;
      }
      // Parse key-value pairs.
      List<String> parts = splitter.splitToList(line.trim());
      if (parts.size() != 2) {
        continue;
      }
      switch (parts.get(0)) {
        case "codePath":
          codePath = parts.get(1);
          break;
        case "resourcePath":
          resourcePath = parts.get(1);
          break;
        case "nativeLibraryPath":
          nativeLibPath = parts.get(1);
          break;
        // Lollipop uses this name.  Not sure what's "legacy" about it yet.
        // Maybe something to do with 64-bit?
        // Might need to update if people report failures.
        case "legacyNativeLibraryDir":
          nativeLibPath = parts.get(1);
          break;
        case "versionCode":
          // Extra split to get rid of the SDK thing.
          versionCode = parts.get(1).split(" ", 2)[0];
          break;
        default:
          break;
      }
    }

    if (!sawPackageLine) {
      return Optional.absent();
    }

    Preconditions.checkNotNull(codePath, "Could not find codePath");
    Preconditions.checkNotNull(resourcePath, "Could not find resourcePath");
    Preconditions.checkNotNull(nativeLibPath, "Could not find nativeLibraryPath");
    Preconditions.checkNotNull(versionCode, "Could not find versionCode");
    if (!codePath.equals(resourcePath)) {
      throw new IllegalStateException("Code and resource path do not match");
    }

    // Lollipop doesn't give the full path to the apk anymore.  Not sure why it's "base.apk".
    if (!codePath.endsWith(".apk")) {
      codePath += "/base.apk";
    }

    return Optional.of(new PackageInfo(codePath, nativeLibPath, versionCode));
  }

  /**
   * @param output  Output of "ls" command.
   * @param filePattern  A {@link Pattern} that is used to check if a file is valid, and if it
   *     matches, {@code filePattern.group(1)} should return the hash in the file name.
   * @param requiredHashes  Hashes of dex files required for this apk.
   * @param foundHashes  Builder to receive hashes that we need and were found.
   * @param toDelete  Builder to receive files that we need to delete.
   */
  @VisibleForTesting
  static void processLsOutput(
      String output,
      Pattern filePattern,
      ImmutableSet<String> requiredHashes,
      ImmutableSet.Builder<String> foundHashes,
      ImmutableSet.Builder<String> toDelete) {
    for (String line : Splitter.on("\r\n").omitEmptyStrings().split(output)) {
      if (line.equals("lock")) {
        continue;
      }

      Matcher m = filePattern.matcher(line);
      if (m.matches()) {
        if (requiredHashes.contains(m.group(1))) {
          foundHashes.add(m.group(1));
        } else {
          toDelete.add(line);
        }
      } else {
        toDelete.add(line);
      }
    }
  }

  /**
   * Breaks a list of strings into groups whose total size is within some limit.
   * Kind of like the xargs command that groups arguments to avoid maximum argument length limits.
   * Except that the limit in adb is about 1k instead of 512k or 2M on Linux.
   */
  @VisibleForTesting
  static ImmutableList<ImmutableList<String>> chunkArgs(Iterable<String> args, int sizeLimit) {
    ImmutableList.Builder<ImmutableList<String>> topLevelBuilder = ImmutableList.builder();
    ImmutableList.Builder<String> chunkBuilder = ImmutableList.builder();
    int chunkSize = 0;
    for (String arg : args) {
      if (chunkSize + arg.length() > sizeLimit) {
        topLevelBuilder.add(chunkBuilder.build());
        chunkBuilder = ImmutableList.builder();
        chunkSize = 0;
      }
      // We don't check for an individual arg greater than the limit.
      // We just put it in its own chunk and hope for the best.
      chunkBuilder.add(arg);
      chunkSize += arg.length();
    }
    ImmutableList<String> tail = chunkBuilder.build();
    if (!tail.isEmpty()) {
      topLevelBuilder.add(tail);
    }
    return topLevelBuilder.build();
  }
}


File: src/com/facebook/buck/cli/InstallCommand.java
/*
 * Copyright 2012-present Facebook, Inc.
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

import com.facebook.buck.apple.AppleBundle;
import com.facebook.buck.apple.AppleConfig;
import com.facebook.buck.apple.AppleInfoPlistParsing;
import com.facebook.buck.apple.simulator.AppleCoreSimulatorServiceController;
import com.facebook.buck.apple.simulator.AppleSimulator;
import com.facebook.buck.apple.simulator.AppleSimulatorController;
import com.facebook.buck.apple.simulator.AppleSimulatorDiscovery;
import com.facebook.buck.cli.UninstallCommand.UninstallOptions;
import com.facebook.buck.command.Build;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.log.Logger;
import com.facebook.buck.step.ExecutionContext;
import com.facebook.buck.rules.ActionGraph;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.ExopackageInfo;
import com.facebook.buck.rules.InstallableApk;
import com.facebook.buck.util.ProcessExecutor;
import com.facebook.buck.util.UnixUserIdFetcher;
import com.facebook.infer.annotation.SuppressFieldNotInitialized;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;

import org.kohsuke.args4j.Option;

import java.io.IOException;
import java.io.InputStream;

import java.nio.file.Path;

import javax.annotation.Nullable;

/**
 * Command so a user can build and install an APK.
 */
public class InstallCommand extends BuildCommand {

  private static final Logger LOG = Logger.get(InstallCommand.class);
  private static final long APPLE_SIMULATOR_WAIT_MILLIS = 20000;

  @VisibleForTesting static final String RUN_LONG_ARG = "--run";
  @VisibleForTesting static final String RUN_SHORT_ARG = "-r";
  @VisibleForTesting static final String WAIT_FOR_DEBUGGER_LONG_ARG = "--wait-for-debugger";
  @VisibleForTesting static final String WAIT_FOR_DEBUGGER_SHORT_ARG = "-w";
  @VisibleForTesting static final String INSTALL_VIA_SD_LONG_ARG = "--via-sd";
  @VisibleForTesting static final String INSTALL_VIA_SD_SHORT_ARG = "-S";
  @VisibleForTesting static final String ACTIVITY_LONG_ARG = "--activity";
  @VisibleForTesting static final String ACTIVITY_SHORT_ARG = "-a";
  @VisibleForTesting static final String UNINSTALL_LONG_ARG = "--uninstall";
  @VisibleForTesting static final String UNINSTALL_SHORT_ARG = "-u";

  @Option(
      name = UNINSTALL_LONG_ARG,
      aliases = { UNINSTALL_SHORT_ARG },
      usage = "Uninstall the existing version before installing.")
  private boolean uninstallFirst = false;

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private UninstallOptions uninstallOptions;

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private AdbOptions adbOptions;

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private TargetDeviceOptions deviceOptions;

  @Option(
      name = RUN_LONG_ARG,
      aliases = { RUN_SHORT_ARG },
      usage = "Run an activity (the default activity for package unless -a is specified).")
  private boolean run = false;

  @Option(
      name = WAIT_FOR_DEBUGGER_LONG_ARG,
      aliases = { WAIT_FOR_DEBUGGER_SHORT_ARG },
      usage = "Have the launched process wait for the debugger")
  private boolean waitForDebugger = false;

  @Option(
      name = INSTALL_VIA_SD_LONG_ARG,
      aliases = { INSTALL_VIA_SD_SHORT_ARG },
      usage = "Copy package to external storage (SD) instead of /data/local/tmp before installing.")
  private boolean installViaSd = false;

  @Option(
      name = ACTIVITY_LONG_ARG,
      aliases = { ACTIVITY_SHORT_ARG },
      metaVar = "<pkg/activity>",
      usage = "Activity to launch e.g. com.facebook.katana/.LoginActivity. Implies -r.")
  @Nullable
  private String activity = null;

  public AdbOptions adbOptions() {
    return adbOptions;
  }

  public TargetDeviceOptions targetDeviceOptions() {
    return deviceOptions;
  }

  public UninstallOptions uninstallOptions() {
    return uninstallOptions;
  }

  public boolean shouldUninstallFirst() {
    return uninstallFirst;
  }

  public boolean shouldStartActivity() {
    return (activity != null) || run;
  }

  public boolean shouldInstallViaSd() {
    return installViaSd;
  }

  @Nullable
  public String getActivityToStart() {
    return activity;
  }

  @Override
  public int runWithoutHelp(CommandRunnerParams params) throws IOException, InterruptedException {
    // Make sure that only one build target is specified.
    if (getArguments().size() != 1) {
      params.getConsole().getStdErr().println(
          "Must specify exactly one rule.");
      return 1;
    }

    // Build the specified target.
    int exitCode = super.runWithoutHelp(params);
    if (exitCode != 0) {
      return exitCode;
    }

    Build build = super.getBuild();
    ActionGraph graph = build.getActionGraph();
    BuildRule buildRule = Preconditions.checkNotNull(
        graph.findBuildRuleByTarget(getBuildTargets().get(0)));

    if (buildRule instanceof InstallableApk) {
      return installApk(
          params,
          (InstallableApk) buildRule,
          build.getExecutionContext());
    } else if (buildRule instanceof AppleBundle) {
      AppleBundle appleBundle = (AppleBundle) buildRule;
      params.getBuckEventBus().post(InstallEvent.started(appleBundle.getBuildTarget()));
      exitCode = installAppleBundle(
          params,
          appleBundle,
          build.getExecutionContext().getProjectFilesystem(),
          build.getExecutionContext().getProcessExecutor());
      params.getBuckEventBus().post(
          InstallEvent.finished(appleBundle.getBuildTarget(), exitCode == 0));
      return exitCode;
    } else {
      params.getConsole().printBuildFailure(String.format(
              "Specified rule %s must be of type android_binary() or apk_genrule() or " +
              "apple_bundle() but was %s().\n",
              buildRule.getFullyQualifiedName(),
              buildRule.getType()));
      return 1;
    }
  }

  private int installApk(
      CommandRunnerParams params,
      InstallableApk installableApk,
      ExecutionContext executionContext) throws IOException, InterruptedException {
    final AdbHelper adbHelper = new AdbHelper(
        adbOptions(),
        targetDeviceOptions(),
        executionContext,
        params.getConsole(),
        params.getBuckEventBus(),
        params.getBuckConfig());

    // Uninstall the app first, if requested.
    if (shouldUninstallFirst()) {
      String packageName = AdbHelper.tryToExtractPackageNameFromManifest(
          installableApk,
          executionContext);
      adbHelper.uninstallApp(packageName, uninstallOptions());
      // Perhaps the app wasn't installed to begin with, shouldn't stop us.
    }

    boolean installSuccess;
    Optional<ExopackageInfo> exopackageInfo = installableApk.getExopackageInfo();
    if (exopackageInfo.isPresent()) {
      installSuccess = new ExopackageInstaller(
          executionContext,
          adbHelper,
          installableApk)
          .install();
    } else {
      installSuccess = adbHelper.installApk(installableApk, this);
    }
    if (!installSuccess) {
      return 1;
    }

    // We've installed the application successfully.
    // Is either of --activity or --run present?
    if (shouldStartActivity()) {
      int exitCode = adbHelper.startActivity(installableApk, getActivityToStart());
      if (exitCode != 0) {
        return exitCode;
      }
    }

    return 0;
  }

  private int installAppleBundle(
      CommandRunnerParams params,
      AppleBundle appleBundle,
      ProjectFilesystem projectFilesystem,
      ProcessExecutor processExecutor) throws IOException, InterruptedException {

    // TODO(user): This should be shared with the build and passed down.
    AppleConfig appleConfig = new AppleConfig(params.getBuckConfig());
    Optional<Path> xcodeDeveloperPath = appleConfig.getAppleDeveloperDirectorySupplier(
        processExecutor).get();
    if (!xcodeDeveloperPath.isPresent()) {
      params.getConsole().printBuildFailure(
          String.format(
              "Cannot install %s (Xcode not found)", appleBundle.getFullyQualifiedName()));
      return 1;
    }

    UnixUserIdFetcher userIdFetcher = new UnixUserIdFetcher();
    AppleCoreSimulatorServiceController appleCoreSimulatorServiceController =
        new AppleCoreSimulatorServiceController(processExecutor);

    Optional<Path> coreSimulatorServicePath =
        appleCoreSimulatorServiceController.getCoreSimulatorServicePath(userIdFetcher);

    boolean shouldWaitForSimulatorsToShutdown = false;

    if (!coreSimulatorServicePath.isPresent() ||
        !coreSimulatorServicePath.get().toRealPath().startsWith(
            xcodeDeveloperPath.get().toRealPath())) {
      LOG.warn(
          "Core simulator service path %s does not match developer directory %s, " +
          "killing all simulators.",
          coreSimulatorServicePath,
          xcodeDeveloperPath.get());
      if (!appleCoreSimulatorServiceController.killSimulatorProcesses()) {
        params.getConsole().printBuildFailure("Could not kill running simulator processes.");
        return 1;
      }

      shouldWaitForSimulatorsToShutdown = true;
    }

    Path simctlPath = xcodeDeveloperPath.get().resolve("usr/bin/simctl");
    Optional<AppleSimulator> appleSimulator = getAppleSimulatorForBundle(
        appleBundle,
        processExecutor,
        simctlPath);

    if (!appleSimulator.isPresent()) {
      params.getConsole().printBuildFailure(
          String.format(
              "Cannot install %s (no appropriate simulator found)",
              appleBundle.getFullyQualifiedName()));
      return 1;
    }

    Path iosSimulatorPath = xcodeDeveloperPath.get().resolve("Applications/iOS Simulator.app");
    AppleSimulatorController appleSimulatorController = new AppleSimulatorController(
        processExecutor,
        simctlPath,
        iosSimulatorPath);

    if (!appleSimulatorController.canStartSimulator(appleSimulator.get().getUdid())) {
      LOG.warn("Cannot start simulator %s, killing simulators and trying again.");
      if (!appleCoreSimulatorServiceController.killSimulatorProcesses()) {
        params.getConsole().printBuildFailure("Could not kill running simulator processes.");
        return 1;
      }

      shouldWaitForSimulatorsToShutdown = true;

      // Killing the simulator can cause the UDIDs to change, so we need to fetch them again.
      appleSimulator = getAppleSimulatorForBundle(appleBundle, processExecutor, simctlPath);
      if (!appleSimulator.isPresent()) {
        params.getConsole().printBuildFailure(
            String.format(
                "Cannot install %s (no appropriate simulator found)",
                appleBundle.getFullyQualifiedName()));
        return 1;
      }
    }

    long remainingMillis = APPLE_SIMULATOR_WAIT_MILLIS;
    if (shouldWaitForSimulatorsToShutdown) {
      Optional<Long> shutdownMillis = appleSimulatorController.waitForSimulatorsToShutdown(
          remainingMillis);
      if (!shutdownMillis.isPresent()) {
        params.getConsole().printBuildFailure(
            String.format(
                "Cannot install %s (simulators did not shut down within %d ms).",
                appleBundle.getFullyQualifiedName(),
                APPLE_SIMULATOR_WAIT_MILLIS));
        return 1;
      }

      LOG.debug("Simulators shut down in %d millis.", shutdownMillis.get());
      remainingMillis -= shutdownMillis.get();
    }

    LOG.debug("Starting up simulator %s", appleSimulator.get());

    Optional<Long> startMillis = appleSimulatorController.startSimulator(
        appleSimulator.get().getUdid(),
        remainingMillis);

    if (!startMillis.isPresent()) {
      params.getConsole().printBuildFailure(
          String.format(
              "Cannot install %s (could not start simulator %s within %d ms)",
              appleBundle.getFullyQualifiedName(),
              appleSimulator.get().getName(),
              APPLE_SIMULATOR_WAIT_MILLIS));
      return 1;
    }

    LOG.debug(
        "Simulator started in %d ms. Installing Apple bundle %s in simulator %s",
        startMillis.get(),
        appleBundle,
        appleSimulator.get());

    if (!appleSimulatorController.installBundleInSimulator(
            appleSimulator.get().getUdid(),
            projectFilesystem.resolve(appleBundle.getPathToOutput()))) {
      params.getConsole().printBuildFailure(
          String.format(
              "Cannot install %s (could not install bundle %s in simulator %s)",
              appleBundle.getFullyQualifiedName(),
              appleBundle.getPathToOutput(),
              appleSimulator.get().getName()));
      return 1;
    }

    if (run) {
      return launchAppleBundle(
          params,
          appleBundle,
          appleSimulatorController,
          projectFilesystem,
          appleSimulator.get());
    } else {
      params.getConsole().printSuccess(
          String.format(
              "Successfully installed %s. (Use `buck install -r %s` to run.)",
              getArguments().get(0),
              getArguments().get(0)));
      return 0;
    }
  }

  private int launchAppleBundle(
      CommandRunnerParams params,
      AppleBundle appleBundle,
      AppleSimulatorController appleSimulatorController,
      ProjectFilesystem projectFilesystem,
      AppleSimulator appleSimulator) throws IOException, InterruptedException {

    LOG.debug("Launching Apple bundle %s in simulator %s", appleBundle, appleSimulator);

    Optional<String> appleBundleId;
    try (InputStream bundlePlistStream =
             projectFilesystem.getInputStreamForRelativePath(appleBundle.getInfoPlistPath())){
        appleBundleId = AppleInfoPlistParsing.getBundleIdFromPlistStream(bundlePlistStream);
    }
    if (!appleBundleId.isPresent()) {
      params.getConsole().printBuildFailure(
          String.format(
              "Cannot install %s (could not get bundle ID from %s)",
              appleBundle.getFullyQualifiedName(),
              appleBundle.getInfoPlistPath()));
      return 1;
    }

    Optional<Long> launchedPid = appleSimulatorController.launchInstalledBundleInSimulator(
        appleSimulator.getUdid(),
        appleBundleId.get(),
        waitForDebugger ? AppleSimulatorController.LaunchBehavior.WAIT_FOR_DEBUGGER :
            AppleSimulatorController.LaunchBehavior.DO_NOT_WAIT_FOR_DEBUGGER);
    if (!launchedPid.isPresent()) {
      params.getConsole().printBuildFailure(
          String.format(
              "Cannot launch %s (failed to launch bundle ID %s)",
              appleBundle.getFullyQualifiedName(),
              appleBundleId.get()));
      return 1;
    }

    params.getConsole().printSuccess(
        String.format(
            "Successfully launched %s%s. To debug, run: lldb -p %d",
            getArguments().get(0),
            waitForDebugger ? " (waiting for debugger)" : "",
            launchedPid.get()));

    return 0;
  }

  private Optional<AppleSimulator> getAppleSimulatorForBundle(
      AppleBundle appleBundle,
      ProcessExecutor processExecutor,
      Path simctlPath) throws IOException, InterruptedException {
    LOG.debug("Choosing simulator for %s", appleBundle);

    for (AppleSimulator simulator : AppleSimulatorDiscovery.discoverAppleSimulators(
             processExecutor,
             simctlPath)) {
      // TODO(user): Choose this from the flavor and add more command-line params to
      // switch between iPhone/iPad simulator.
      if (simulator.getName().equals("iPhone 5s")) {
        return Optional.of(simulator);
      }
    }

    return Optional.<AppleSimulator>absent();
  }

  @Override
  public String getShortDescription() {
    return "builds and installs an application";
  }

  @Override
  public boolean isReadOnly() {
    return false;
  }

}


File: src/com/facebook/buck/cli/TestCommand.java
/*
 * Copyright 2012-present Facebook, Inc.
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

import com.facebook.buck.command.Build;
import com.facebook.buck.json.BuildFileParseException;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetException;
import com.facebook.buck.model.Pair;
import com.facebook.buck.parser.BuildFileSpec;
import com.facebook.buck.parser.ParserConfig;
import com.facebook.buck.parser.TargetNodePredicateSpec;
import com.facebook.buck.rules.ActionGraph;
import com.facebook.buck.rules.BuildEvent;
import com.facebook.buck.rules.CachingBuildEngine;
import com.facebook.buck.rules.Label;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TargetGraphToActionGraph;
import com.facebook.buck.rules.TargetNode;
import com.facebook.buck.rules.TargetNodes;
import com.facebook.buck.rules.TestRule;
import com.facebook.buck.step.DefaultStepRunner;
import com.facebook.buck.step.TargetDevice;
import com.facebook.buck.test.CoverageReportFormat;
import com.facebook.buck.util.Console;
import com.facebook.buck.util.concurrent.ConcurrencyLimit;
import com.facebook.infer.annotation.SuppressFieldNotInitialized;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Optional;
import com.google.common.base.Preconditions;
import com.google.common.base.Predicate;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;

import org.kohsuke.args4j.Option;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Paths;
import java.util.Comparator;
import java.util.Set;
import java.util.concurrent.ExecutionException;

import javax.annotation.Nullable;

public class TestCommand extends BuildCommand {

  public static final String USE_RESULTS_CACHE = "use_results_cache";

  private static final Logger LOG = Logger.get(TestCommand.class);

  @Option(name = "--all",
          usage =
              "Whether all of the tests should be run. " +
              "If no targets are given, --all is implied")
  private boolean all = false;

  @Option(name = "--code-coverage", usage = "Whether code coverage information will be generated.")
  private boolean isCodeCoverageEnabled = false;

  @Option(name = "--code-coverage-format", usage = "Format to be used for coverage")
  private CoverageReportFormat coverageReportFormat = CoverageReportFormat.HTML;

  @Option(name = "--debug",
          usage = "Whether the test will start suspended with a JDWP debug port of 5005")
  private boolean isDebugEnabled = false;

  @Option(name = "--xml", usage = "Where to write test output as XML.")
  @Nullable
  private String pathToXmlTestOutput = null;

  @Option(name = "--no-results-cache", usage = "Whether to use cached test results.")
  @Nullable
  private Boolean isResultsCacheDisabled = null;

  @Option(name = "--build-filtered", usage = "Whether to build filtered out tests.")
  @Nullable
  private Boolean isBuildFiltered = null;

  @Option(
      name = "--ignore-when-dependencies-fail",
      aliases = {"-i"},
      usage =
          "Ignore test failures for libraries if they depend on other libraries " +
          "that aren't passing their tests.  " +
          "For example, if java_library A depends on B, " +
          "and they are tested respectively by T1 and T2 and both of those tests fail, " +
          "only print the error for T2.")
  private boolean isIgnoreFailingDependencies = false;

  @Option(
      name = "--dry-run",
      usage = "Print tests that match the given command line options, but don't run them.")
  private boolean isDryRun;

  @Option(
      name = "--one-time-output",
      usage =
          "Put test-results in a unique, one-time output directory.  " +
          "This allows multiple tests to be run in parallel without interfering with each other, " +
          "but at the expense of being unable to use cached results.  " +
          "WARNING: this is experimental, and only works for Java tests!")
  private boolean isUsingOneTimeOutput;

  @Option(
      name = "--shuffle",
      usage =
          "Randomize the order in which test classes are executed." +
          "WARNING: only works for Java tests!")
  private boolean isShufflingTests;

  @Option(
      name = "--exclude-transitive-tests",
      usage =
          "Only run the tests targets that were specified on the command line (without adding " +
          "more tests by following dependencies).")
  private boolean shouldExcludeTransitiveTests;

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private TargetDeviceOptions targetDeviceOptions;

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private TestSelectorOptions testSelectorOptions;

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private TestLabelOptions testLabelOptions;

  public boolean isRunAllTests() {
    return all || getArguments().isEmpty();
  }

  @Override
  public boolean isCodeCoverageEnabled() {
    return isCodeCoverageEnabled;
  }

  public boolean isResultsCacheEnabled(BuckConfig buckConfig) {
    // The option is negative (--no-X) but we prefer to reason about positives, in the code.
    if (isResultsCacheDisabled == null) {
      boolean isUseResultsCache = buckConfig.getBooleanValue("test", USE_RESULTS_CACHE, true);
      isResultsCacheDisabled = !isUseResultsCache;
    }
    return !isResultsCacheDisabled;
  }

  @Override
  public boolean isDebugEnabled() {
    return isDebugEnabled;
  }

  public Optional<TargetDevice> getTargetDeviceOptional() {
    return targetDeviceOptions.getTargetDeviceOptional();
  }

  public boolean isDryRun() {
    return isDryRun;
  }

  public boolean isMatchedByLabelOptions(BuckConfig buckConfig, Set<Label> labels) {
    return testLabelOptions.isMatchedByLabelOptions(buckConfig, labels);
  }

  public boolean shouldExcludeTransitiveTests() {
    return shouldExcludeTransitiveTests;
  }

  public boolean shouldExcludeWin() {
    return testLabelOptions.shouldExcludeWin();
  }

  public boolean isBuildFiltered(BuckConfig buckConfig) {
    return isBuildFiltered != null ?
        isBuildFiltered :
        buckConfig.getBooleanValue("test", "build_filtered_tests", false);
  }

  public int getNumTestThreads(BuckConfig buckConfig) {
    if (isDebugEnabled()) {
      return 1;
    }
    return getNumThreads(buckConfig);
  }

  @Override
  public int runWithoutHelp(CommandRunnerParams params) throws IOException, InterruptedException {
    LOG.debug("Running with arguments %s", getArguments());

    // Post the build started event, setting it to the Parser recorded start time if appropriate.
    if (params.getParser().getParseStartTime().isPresent()) {
      params.getBuckEventBus().post(
          BuildEvent.started(getArguments()),
          params.getParser().getParseStartTime().get());
    } else {
      params.getBuckEventBus().post(BuildEvent.started(getArguments()));
    }

    // The first step is to parse all of the build files. This will populate the parser and find all
    // of the test rules.
    ParserConfig parserConfig = new ParserConfig(params.getBuckConfig());
    TargetGraph targetGraph;
    ImmutableSet<BuildTarget> explicitBuildTargets;

    try {

      // If the user asked to run all of the tests, parse all of the build files looking for any
      // test rules.
      if (isRunAllTests()) {
        targetGraph = params.getParser().buildTargetGraphForTargetNodeSpecs(
            ImmutableList.of(
                TargetNodePredicateSpec.of(
                    new Predicate<TargetNode<?>>() {
                      @Override
                      public boolean apply(TargetNode<?> input) {
                        return input.getType().isTestRule();
                      }
                    },
                    BuildFileSpec.fromRecursivePath(
                        Paths.get(""),
                        params.getRepository().getFilesystem().getIgnorePaths()))),
            parserConfig,
            params.getBuckEventBus(),
            params.getConsole(),
            params.getEnvironment(),
            getEnableProfiling()).getSecond();
        explicitBuildTargets = ImmutableSet.of();

        // Otherwise, the user specified specific test targets to build and run, so build a graph
        // around these.
      } else {
        LOG.debug("Parsing graph for arguments %s", getArguments());
        Pair<ImmutableSet<BuildTarget>, TargetGraph> result = params.getParser()
            .buildTargetGraphForTargetNodeSpecs(
                parseArgumentsAsTargetNodeSpecs(
                    params.getBuckConfig(),
                    params.getRepository().getFilesystem().getIgnorePaths(),
                    getArguments()),
                parserConfig,
                params.getBuckEventBus(),
                params.getConsole(),
                params.getEnvironment(),
                getEnableProfiling());
        targetGraph = result.getSecond();
        explicitBuildTargets = result.getFirst();

        LOG.debug("Got explicit build targets %s", explicitBuildTargets);
        ImmutableSet.Builder<BuildTarget> testTargetsBuilder = ImmutableSet.builder();
        for (TargetNode<?> node : targetGraph.getAll(explicitBuildTargets)) {
          ImmutableSortedSet<BuildTarget> nodeTests = TargetNodes.getTestTargetsForNode(node);
          if (!nodeTests.isEmpty()) {
            LOG.debug("Got tests for target %s: %s", node.getBuildTarget(), nodeTests);
            testTargetsBuilder.addAll(nodeTests);
          }
        }
        ImmutableSet<BuildTarget> testTargets = testTargetsBuilder.build();
        if (!testTargets.isEmpty()) {
          LOG.debug("Got related test targets %s, building new target graph...", testTargets);
          targetGraph = params.getParser().buildTargetGraphForBuildTargets(
              Iterables.concat(
                  explicitBuildTargets,
                  testTargets),
              parserConfig,
              params.getBuckEventBus(),
              params.getConsole(),
              params.getEnvironment(),
              getEnableProfiling());
          LOG.debug("Finished building new target graph with tests.");
        }
      }

    } catch (BuildTargetException | BuildFileParseException e) {
      params.getConsole().printBuildFailureWithoutStacktrace(e);
      return 1;
    }

    ActionGraph graph = new TargetGraphToActionGraph(
        params.getBuckEventBus(),
        new BuildTargetNodeToBuildRuleTransformer(),
        params.getFileHashCache()).apply(targetGraph);

    // Look up all of the test rules in the action graph.
    Iterable<TestRule> testRules = Iterables.filter(graph.getNodes(), TestRule.class);

    // Unless the user requests that we build filtered tests, filter them out here, before
    // the build.
    if (!isBuildFiltered(params.getBuckConfig())) {
      testRules = filterTestRules(params.getBuckConfig(), explicitBuildTargets, testRules);
    }

    if (isDryRun()) {
      printMatchingTestRules(params.getConsole(), testRules);
    }

    try (CommandThreadManager pool =
             new CommandThreadManager("Test", getConcurrencyLimit(params.getBuckConfig()))) {
      CachingBuildEngine cachingBuildEngine =
          new CachingBuildEngine(
              pool.getExecutor(),
              getBuildEngineMode().or(params.getBuckConfig().getBuildEngineMode()));
      try (Build build = createBuild(
          params.getBuckConfig(),
          graph,
          params.getRepository().getFilesystem(),
          params.getAndroidPlatformTargetSupplier(),
          cachingBuildEngine,
          getArtifactCache(params),
          params.getConsole(),
          params.getBuckEventBus(),
          getTargetDeviceOptional(),
          params.getPlatform(),
          params.getEnvironment(),
          params.getObjectMapper(),
          params.getClock())) {

        // Build all of the test rules.
        int exitCode = build.executeAndPrintFailuresToConsole(
            testRules,
            isKeepGoing(),
            params.getConsole(),
            getPathToBuildReport(params.getBuckConfig()));
        params.getBuckEventBus().post(BuildEvent.finished(getArguments(), exitCode));
        if (exitCode != 0) {
          return exitCode;
        }

        // If the user requests that we build tests that we filter out, then we perform
        // the filtering here, after we've done the build but before we run the tests.
        if (isBuildFiltered(params.getBuckConfig())) {
          testRules =
              filterTestRules(params.getBuckConfig(), explicitBuildTargets, testRules);
        }

        // Once all of the rules are built, then run the tests.
        ConcurrencyLimit concurrencyLimit = new ConcurrencyLimit(
            getNumTestThreads(params.getBuckConfig()),
            getLoadLimit(params.getBuckConfig()));
        try (CommandThreadManager testPool =
                 new CommandThreadManager("Test-Run", concurrencyLimit)) {
          TestRunningOptions options = TestRunningOptions.builder()
              .setUsingOneTimeOutputDirectories(isUsingOneTimeOutput)
              .setCodeCoverageEnabled(isCodeCoverageEnabled)
              .setRunAllTests(isRunAllTests())
              .setTestSelectorList(testSelectorOptions.getTestSelectorList())
              .setShouldExplainTestSelectorList(testSelectorOptions.shouldExplain())
              .setIgnoreFailingDependencies(isIgnoreFailingDependencies)
              .setResultsCacheEnabled(isResultsCacheEnabled(params.getBuckConfig()))
              .setDryRun(isDryRun)
              .setShufflingTests(isShufflingTests)
              .setPathToXmlTestOutput(Optional.fromNullable(pathToXmlTestOutput))
              .setCoverageReportFormat(coverageReportFormat)
              .build();
          return TestRunning.runTests(
              params,
              testRules,
              Preconditions.checkNotNull(build.getBuildContext()),
              build.getExecutionContext(),
              options,
              testPool.getExecutor(),
              cachingBuildEngine,
              new DefaultStepRunner(build.getExecutionContext()));
        } catch (ExecutionException e) {
          params.getConsole().printBuildFailureWithoutStacktrace(e);
          return 1;
        }
      }
    }
  }

  @Override
  public boolean isReadOnly() {
    return false;
  }

  private void printMatchingTestRules(Console console, Iterable<TestRule> testRules) {
    PrintStream out = console.getStdOut();
    ImmutableList<TestRule> list = ImmutableList.copyOf(testRules);
    out.println(String.format("MATCHING TEST RULES (%d):", list.size()));
    out.println("");
    if (list.isEmpty()) {
      out.println("  (none)");
    } else {
      for (TestRule testRule : testRules) {
        out.println("  " + testRule.getBuildTarget());
      }
    }
    out.println("");
  }

  @VisibleForTesting
  Iterable<TestRule> filterTestRules(
      BuckConfig buckConfig,
      ImmutableSet<BuildTarget> explicitBuildTargets,
      Iterable<TestRule> testRules) {

    ImmutableSortedSet.Builder<TestRule> builder =
        ImmutableSortedSet.orderedBy(
            new Comparator<TestRule>() {
              @Override
              public int compare(TestRule o1, TestRule o2) {
                return o1.getBuildTarget().getFullyQualifiedName().compareTo(
                    o2.getBuildTarget().getFullyQualifiedName());
              }
            });

    for (TestRule rule : testRules) {
      boolean explicitArgument = explicitBuildTargets.contains(rule.getBuildTarget());
      boolean matchesLabel = isMatchedByLabelOptions(buckConfig, rule.getLabels());

      // We always want to run the rules that are given on the command line. Always. Unless we don't
      // want to.
      if (shouldExcludeWin() && !matchesLabel) {
        continue;
      }

      // The testRules Iterable contains transitive deps of the arguments given on the command line,
      // filter those out if such is the user's will.
      if (shouldExcludeTransitiveTests() && !explicitArgument) {
        continue;
      }

      // Normal behavior is to include all rules that match the given label as well as any that
      // were explicitly specified by the user.
      if (explicitArgument || matchesLabel) {
        builder.add(rule);
      }
    }

    return builder.build();
  }

  @Override
  public String getShortDescription() {
    return "builds and runs the tests for the specified target";
  }

}


File: src/com/facebook/buck/cli/UninstallCommand.java
/*
 * Copyright 2012-present Facebook, Inc.
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
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetException;
import com.facebook.buck.model.Pair;
import com.facebook.buck.parser.ParserConfig;
import com.facebook.buck.rules.ActionGraph;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.InstallableApk;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TargetGraphToActionGraph;
import com.facebook.buck.rules.TargetGraphTransformer;
import com.facebook.buck.step.ExecutionContext;
import com.facebook.infer.annotation.SuppressFieldNotInitialized;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;

import org.kohsuke.args4j.Argument;
import org.kohsuke.args4j.Option;

import java.io.IOException;
import java.util.List;

public class UninstallCommand extends AbstractCommand {

  public static class UninstallOptions {
    @VisibleForTesting static final String KEEP_LONG_ARG = "--keep";
    @VisibleForTesting static final String KEEP_SHORT_ARG = "-k";
    @Option(
        name = KEEP_LONG_ARG,
        aliases = { KEEP_SHORT_ARG },
        usage = "Keep user data when uninstalling.")
    private boolean keepData = false;

    public boolean shouldKeepUserData() {
      return keepData;
    }
  }

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private UninstallOptions uninstallOptions;

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private AdbOptions adbOptions;

  @AdditionalOptions
  @SuppressFieldNotInitialized
  private TargetDeviceOptions deviceOptions;

  @Argument
  private List<String> arguments = Lists.newArrayList();

  public List<String> getArguments() {
    return arguments;
  }

  @VisibleForTesting
  void setArguments(List<String> arguments) {
    this.arguments = arguments;
  }

  public UninstallOptions uninstallOptions() {
    return uninstallOptions;
  }

  public AdbOptions adbOptions() {
    return adbOptions;
  }

  public TargetDeviceOptions targetDeviceOptions() {
    return deviceOptions;
  }

  @Override
  public int runWithoutHelp(CommandRunnerParams params) throws IOException, InterruptedException {

    // Parse all of the build targets specified by the user.
    ActionGraph actionGraph;
    ImmutableSet<BuildTarget> buildTargets;
    try {
      Pair<ImmutableSet<BuildTarget>, TargetGraph> result = params.getParser()
          .buildTargetGraphForTargetNodeSpecs(
              parseArgumentsAsTargetNodeSpecs(
                  params.getBuckConfig(),
                  params.getRepository().getFilesystem().getIgnorePaths(),
                  getArguments()),
              new ParserConfig(params.getBuckConfig()),
              params.getBuckEventBus(),
              params.getConsole(),
              params.getEnvironment(),
              getEnableProfiling());
      buildTargets = result.getFirst();
      TargetGraphTransformer<ActionGraph> targetGraphTransformer = new TargetGraphToActionGraph(
          params.getBuckEventBus(),
          new BuildTargetNodeToBuildRuleTransformer(),
          params.getFileHashCache());
      actionGraph = targetGraphTransformer.apply(result.getSecond());
    } catch (BuildTargetException | BuildFileParseException e) {
      params.getConsole().printBuildFailureWithoutStacktrace(e);
      return 1;
    }

    // Make sure that only one build target is specified.
    if (buildTargets.size() != 1) {
      params.getConsole().getStdErr().println("Must specify exactly one android_binary() rule.");
      return 1;
    }
    BuildTarget buildTarget = Iterables.get(buildTargets, 0);

    // Find the android_binary() rule from the parse.
    BuildRule buildRule = Preconditions.checkNotNull(
        actionGraph.findBuildRuleByTarget(buildTarget));
    if (!(buildRule instanceof InstallableApk)) {
      params.getConsole().printBuildFailure(
          String.format(
              "Specified rule %s must be of type android_binary() or apk_genrule() but was %s().\n",
              buildRule.getFullyQualifiedName(),
              buildRule.getType()));
      return 1;
    }
    InstallableApk installableApk = (InstallableApk) buildRule;

    // We need this in case adb isn't already running.
    try (ExecutionContext context = createExecutionContext(params)) {
      final AdbHelper adbHelper = new AdbHelper(
          adbOptions(),
          targetDeviceOptions(),
          context,
          params.getConsole(),
          params.getBuckEventBus(),
          params.getBuckConfig());

      // Find application package name from manifest and uninstall from matching devices.
      String appId = AdbHelper.tryToExtractPackageNameFromManifest(installableApk, context);
      return adbHelper.uninstallApp(
          appId,
          uninstallOptions()
      ) ? 0 : 1;
    }
  }

  @Override
  public String getShortDescription() {
    return "uninstalls an APK";
  }

  @Override
  public boolean isReadOnly() {
    return false;
  }

}


File: src/com/facebook/buck/event/listener/AbstractConsoleEventBusListener.java
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
package com.facebook.buck.event.listener;

import com.facebook.buck.cli.InstallEvent;
import com.facebook.buck.event.BuckEvent;
import com.facebook.buck.event.BuckEventListener;
import com.facebook.buck.event.ConsoleEvent;
import com.facebook.buck.json.ProjectBuildFileParseEvents;
import com.facebook.buck.model.BuildId;
import com.facebook.buck.parser.ParseEvent;
import com.facebook.buck.rules.ActionGraphEvent;
import com.facebook.buck.rules.BuildEvent;
import com.facebook.buck.rules.BuildRuleEvent;
import com.facebook.buck.timing.Clock;
import com.facebook.buck.util.Ansi;
import com.facebook.buck.util.Console;
import com.google.common.base.Optional;
import com.google.common.base.Splitter;
import com.google.common.collect.ImmutableList;
import com.google.common.eventbus.Subscribe;

import java.io.Closeable;
import java.io.IOException;
import java.text.DecimalFormat;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Level;

import javax.annotation.Nullable;

/**
 * Base class for {@link BuckEventListener}s responsible for outputting information about the
 * running build to {@code stderr}.
 */
public abstract class AbstractConsoleEventBusListener implements BuckEventListener, Closeable {
  protected static final DecimalFormat TIME_FORMATTER = new DecimalFormat("0.0s");
  protected static final long UNFINISHED_EVENT_PAIR = -1;
  protected final Console console;
  protected final Clock clock;
  protected final Ansi ansi;

  @Nullable
  protected volatile ProjectBuildFileParseEvents.Started projectBuildFileParseStarted;
  @Nullable
  protected volatile ProjectBuildFileParseEvents.Finished projectBuildFileParseFinished;

  @Nullable
  protected volatile ParseEvent.Started parseStarted;
  @Nullable
  protected volatile ParseEvent.Finished parseFinished;

  @Nullable
  protected volatile ActionGraphEvent.Started actionGraphStarted;
  @Nullable
  protected volatile ActionGraphEvent.Finished actionGraphFinished;

  @Nullable
  protected volatile BuildEvent.Started buildStarted;
  @Nullable
  protected volatile BuildEvent.Finished buildFinished;

  @Nullable
  protected volatile InstallEvent.Started installStarted;
  @Nullable
  protected volatile InstallEvent.Finished installFinished;

  protected volatile Optional<Integer> ruleCount = Optional.absent();

  protected final AtomicInteger numRulesCompleted = new AtomicInteger();

  public AbstractConsoleEventBusListener(Console console, Clock clock) {
    this.console = console;
    this.clock = clock;
    this.ansi = console.getAnsi();

    this.projectBuildFileParseStarted = null;
    this.projectBuildFileParseFinished = null;

    this.parseStarted = null;
    this.parseFinished = null;

    this.actionGraphStarted = null;
    this.actionGraphFinished = null;

    this.buildStarted = null;
    this.buildFinished = null;

    this.installStarted = null;
    this.installFinished = null;
  }

  protected String formatElapsedTime(long elapsedTimeMs) {
    return TIME_FORMATTER.format(elapsedTimeMs / 1000.0);
  }


  /**
   * Adds a line about a pair of start and finished events to lines.
   *
   * @param prefix Prefix to print for this event pair.
   * @param suffix Suffix to print for this event pair.
   * @param currentMillis The current time in milliseconds.
   * @param offsetMs Offset to remove from calculated time.  Set this to a non-zero value if the
   *     event pair would contain another event.  For example, build time includes parse time, but
   *     to make the events easier to reason about it makes sense to pull parse time out of build
   *     time.
   * @param startEvent The started event.
   * @param finishedEvent The finished event.
   * @param lines The builder to append lines to.
   * @return The amount of time between start and finished if finished is present,
   *    otherwise {@link AbstractConsoleEventBusListener#UNFINISHED_EVENT_PAIR}.
   */
  protected long logEventPair(String prefix,
      Optional<String> suffix,
      long currentMillis,
      long offsetMs,
      @Nullable BuckEvent startEvent,
      @Nullable BuckEvent finishedEvent,
      ImmutableList.Builder<String> lines) {
    long result = UNFINISHED_EVENT_PAIR;
    if (startEvent == null) {
      return result;
    }
    String parseLine = (finishedEvent != null ? "[-] " : "[+] ") + prefix + "...";
    long elapsedTimeMs;
    if (finishedEvent != null) {
      elapsedTimeMs = finishedEvent.getTimestamp() - startEvent.getTimestamp();
      parseLine += "FINISHED ";
      result = elapsedTimeMs;
    } else {
      elapsedTimeMs = currentMillis - startEvent.getTimestamp();
    }
    parseLine += formatElapsedTime(elapsedTimeMs - offsetMs);
    if (suffix.isPresent()) {
      parseLine += " " + suffix.get();
    }
    lines.add(parseLine);

    return result;
  }

  /**
   * Formats a {@link ConsoleEvent} and adds it to {@code lines}.
   */
  protected void formatConsoleEvent(ConsoleEvent logEvent, ImmutableList.Builder<String> lines) {
    String formattedLine = "";
    if (logEvent.getLevel().equals(Level.INFO)) {
      formattedLine = logEvent.getMessage();
    } else if (logEvent.getLevel().equals(Level.WARNING)) {
      formattedLine = ansi.asWarningText(logEvent.getMessage());
    } else if (logEvent.getLevel().equals(Level.SEVERE)) {
      formattedLine = ansi.asErrorText(logEvent.getMessage());
    }
    if (!formattedLine.isEmpty()) {
      // Split log messages at newlines and add each line individually to keep the line count
      // consistent.
      lines.addAll(Splitter.on("\n").split(formattedLine));
    }
  }

  @Subscribe
  public void projectBuildFileParseStarted(ProjectBuildFileParseEvents.Started started) {
    projectBuildFileParseStarted = started;
  }

  @Subscribe
  public void projectBuildFileParseFinished(ProjectBuildFileParseEvents.Finished finished) {
    projectBuildFileParseFinished = finished;
  }

  @Subscribe
  public void parseStarted(ParseEvent.Started started) {
    parseStarted = started;
  }

  @Subscribe
  public void parseFinished(ParseEvent.Finished finished) {
    parseFinished = finished;
  }

  @Subscribe
  public void actionGraphStarted(ActionGraphEvent.Started started) {
    actionGraphStarted = started;
  }

  @Subscribe
  public void actionGraphFinished(ActionGraphEvent.Finished finished) {
    actionGraphFinished = finished;
  }

  @Subscribe
  public void buildStarted(BuildEvent.Started started) {
    buildStarted = started;
  }

  @Subscribe
  public void ruleCountCalculated(BuildEvent.RuleCountCalculated calculated) {
    ruleCount = Optional.of(calculated.getNumRules());
  }

  @Subscribe
  public void incrementNumRulesCompleted(
      @SuppressWarnings("unused") BuildRuleEvent.Finished finished) {
    numRulesCompleted.getAndIncrement();
  }

  @Subscribe
  public void buildFinished(BuildEvent.Finished finished) {
    buildFinished = finished;
  }

  @Subscribe
  public void installStarted(InstallEvent.Started started) {
    installStarted = started;
  }

  @Subscribe
  public void installFinished(InstallEvent.Finished finished) {
    installFinished = finished;
  }

  @Override
  public void outputTrace(BuildId buildId) {}

  @Override
  public void close() throws IOException {
  }
}


File: src/com/facebook/buck/event/listener/ChromeTraceBuildListener.java
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

package com.facebook.buck.event.listener;

import com.facebook.buck.cli.CommandEvent;
import com.facebook.buck.cli.InstallEvent;
import com.facebook.buck.cli.StartActivityEvent;
import com.facebook.buck.cli.UninstallEvent;
import com.facebook.buck.event.BuckEvent;
import com.facebook.buck.event.BuckEventListener;
import com.facebook.buck.event.ChromeTraceEvent;
import com.facebook.buck.event.TraceEvent;
import com.facebook.buck.io.PathListing;
import com.facebook.buck.io.ProjectFilesystem;
import com.facebook.buck.log.Logger;
import com.facebook.buck.model.BuildId;
import com.facebook.buck.parser.ParseEvent;
import com.facebook.buck.rules.ActionGraphEvent;
import com.facebook.buck.rules.ArtifactCacheConnectEvent;
import com.facebook.buck.rules.ArtifactCacheEvent;
import com.facebook.buck.rules.BuildEvent;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleEvent;
import com.facebook.buck.rules.TestSummaryEvent;
import com.facebook.buck.step.StepEvent;
import com.facebook.buck.timing.Clock;
import com.facebook.buck.util.BestCompressionGZIPOutputStream;
import com.facebook.buck.util.BuckConstant;
import com.facebook.buck.util.HumanReadableException;
import com.facebook.buck.util.Optionals;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Functions;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableMap;
import com.google.common.eventbus.Subscribe;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Path;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;

/**
 * Logs events to a json file formatted to be viewed in Chrome Trace View (chrome://tracing).
 */
public class ChromeTraceBuildListener implements BuckEventListener {
  private static final Logger LOG = Logger.get(ChromeTraceBuildListener.class);

  private final ProjectFilesystem projectFilesystem;
  private final Clock clock;
  private final int tracesToKeep;
  private final boolean compressTraces;
  private final ObjectMapper mapper;
  private final ThreadLocal<SimpleDateFormat> dateFormat;
  private ConcurrentLinkedQueue<ChromeTraceEvent> eventList =
      new ConcurrentLinkedQueue<ChromeTraceEvent>();

  public ChromeTraceBuildListener(
      ProjectFilesystem projectFilesystem,
      Clock clock,
      ObjectMapper objectMapper,
      int tracesToKeep,
      boolean compressTraces) {
    this(
        projectFilesystem,
        clock,
        objectMapper,
        Locale.US,
        TimeZone.getDefault(),
        tracesToKeep,
        compressTraces);
  }

  @VisibleForTesting
  ChromeTraceBuildListener(
      ProjectFilesystem projectFilesystem,
      Clock clock,
      ObjectMapper objectMapper,
      final Locale locale,
      final TimeZone timeZone,
      int tracesToKeep,
      boolean compressTraces) {
    this.projectFilesystem = projectFilesystem;
    this.clock = clock;
    this.mapper = objectMapper;
    this.dateFormat = new ThreadLocal<SimpleDateFormat>() {
      @Override
      protected SimpleDateFormat initialValue() {
          SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd.HH-mm-ss", locale);
          dateFormat.setTimeZone(timeZone);
          return dateFormat;
      }
    };
    this.tracesToKeep = tracesToKeep;
    this.compressTraces = compressTraces;
    addProcessMetadataEvent();
  }

  private void addProcessMetadataEvent() {
    eventList.add(
        new ChromeTraceEvent(
            "buck",
            "process_name",
            ChromeTraceEvent.Phase.METADATA,
            /* processId */ 0,
            /* threadId */ 0,
            /* microTime */ 0,
            ImmutableMap.of("name", "buck")));
  }

  @VisibleForTesting
  void deleteOldTraces() {
    if (!projectFilesystem.exists(BuckConstant.BUCK_TRACE_DIR)) {
      return;
    }

    Path traceDirectory = projectFilesystem.getPathForRelativePath(BuckConstant.BUCK_TRACE_DIR);

    try {
      for (Path path : PathListing.listMatchingPathsWithFilters(
               traceDirectory,
               "build.*.trace",
               PathListing.GET_PATH_MODIFIED_TIME,
               PathListing.FilterMode.EXCLUDE,
               Optional.of(tracesToKeep),
               Optional.<Long>absent())) {
        projectFilesystem.deleteFileAtPath(path);
      }
    } catch (IOException e) {
      LOG.error(e, "Couldn't list paths in trace directory %s", traceDirectory);
    }
  }

  @Override
  public void outputTrace(BuildId buildId) {
    try {
      String filenameTime = dateFormat.get().format(new Date(clock.currentTimeMillis()));
      String traceName = String.format("build.%s.%s.trace", filenameTime, buildId);
      if (compressTraces) {
        traceName = traceName + ".gz";
      }
      Path tracePath = BuckConstant.BUCK_TRACE_DIR.resolve(traceName);
      projectFilesystem.createParentDirs(tracePath);
      OutputStream stream = projectFilesystem.newFileOutputStream(tracePath);
      if (compressTraces) {
        stream = new BestCompressionGZIPOutputStream(stream, true);
      }

      LOG.debug("Writing Chrome trace to %s", tracePath);
      mapper.writeValue(stream, eventList);

      String symlinkName = compressTraces ? "build.trace.gz" : "build.trace";
      Path symlinkPath = BuckConstant.BUCK_TRACE_DIR.resolve(symlinkName);
      projectFilesystem.createSymLink(
          projectFilesystem.resolve(symlinkPath),
          projectFilesystem.resolve(tracePath),
          true);

      deleteOldTraces();
    } catch (IOException e) {
      throw new HumanReadableException(e, "Unable to write trace file: " + e);
    }
  }

  @Subscribe
  public void commandStarted(CommandEvent.Started started) {
    writeChromeTraceEvent("buck",
        started.getCommandName(),
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.of(
            "command_args", Joiner.on(' ').join(started.getArgs())
        ),
        started);
  }

  @Subscribe
  public void commandFinished(CommandEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        finished.getCommandName(),
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of(
            "command_args", Joiner.on(' ').join(finished.getArgs()),
            "daemon", Boolean.toString(finished.isDaemon())),
        finished);
  }

  @Subscribe
  public void buildStarted(BuildEvent.Started started) {
    writeChromeTraceEvent("buck",
        "build",
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.<String, String>of(),
        started);
  }

  @Subscribe
  public synchronized void buildFinished(BuildEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        "build",
        ChromeTraceEvent.Phase.END,
        ImmutableMap.<String, String>of(),
        finished);
  }

  @Subscribe
  public void ruleStarted(BuildRuleEvent.Started started) {
    BuildRule buildRule = started.getBuildRule();
    writeChromeTraceEvent("buck",
        buildRule.getFullyQualifiedName(),
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.of("rule_key", started.getRuleKeySafe()),
        started);
  }

  @Subscribe
  public void ruleFinished(BuildRuleEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        finished.getBuildRule().getFullyQualifiedName(),
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of(
            "cache_result", finished.getCacheResult().toString().toLowerCase(),
            "success_type",
            finished.getSuccessType().transform(Functions.toStringFunction()).or("failed")
        ),
        finished);
  }

  @Subscribe
  public void ruleResumed(BuildRuleEvent.Resumed resumed) {
    BuildRule buildRule = resumed.getBuildRule();
    writeChromeTraceEvent(
        "buck",
        buildRule.getFullyQualifiedName(),
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.of("rule_key", resumed.getRuleKeySafe()),
        resumed);
  }

  @Subscribe
  public void ruleSuspended(BuildRuleEvent.Suspended suspended) {
    BuildRule buildRule = suspended.getBuildRule();
    writeChromeTraceEvent("buck",
        buildRule.getFullyQualifiedName(),
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of("rule_key", suspended.getRuleKeySafe()),
        suspended);
  }

  @Subscribe
  public void stepStarted(StepEvent.Started started) {
    writeChromeTraceEvent("buck",
        started.getShortStepName(),
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.<String, String>of(),
        started);
  }

  @Subscribe
  public void stepFinished(StepEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        finished.getShortStepName(),
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of(
            "description", finished.getDescription(),
            "exit_code", Integer.toString(finished.getExitCode())),
        finished);
  }

  @Subscribe
  public void parseStarted(ParseEvent.Started started) {
    writeChromeTraceEvent("buck",
        "parse",
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.<String, String>of(),
        started);
  }

  @Subscribe
  public void parseFinished(ParseEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        "parse",
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of(
            "targets",
            Joiner.on(",").join(finished.getBuildTargets())),
        finished);
  }

  @Subscribe
  public void actionGraphStarted(ActionGraphEvent.Started started) {
    writeChromeTraceEvent(
        "buck",
        "action_graph",
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.<String, String>of(),
        started);
  }

  @Subscribe
  public void actionGraphFinished(ActionGraphEvent.Finished finished) {
    writeChromeTraceEvent(
        "buck",
        "action_graph",
        ChromeTraceEvent.Phase.END,
        ImmutableMap.<String, String>of(),
        finished);
  }

  @Subscribe
  public void installStarted(InstallEvent.Started started) {
    writeChromeTraceEvent("buck",
        "install",
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.<String, String>of(),
        started);
  }

  @Subscribe
  public void installFinished(InstallEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        "install",
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of(
            "target", finished.getBuildTarget().getFullyQualifiedName(),
            "success", Boolean.toString(finished.isSuccess())),
        finished);
  }

  @Subscribe
  public void startActivityStarted(StartActivityEvent.Started started) {
    writeChromeTraceEvent("buck",
        "start_activity",
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.<String, String>of(),
        started);
  }

  @Subscribe
  public void startActivityFinished(StartActivityEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        "start_activity",
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of(
            "target", finished.getBuildTarget().getFullyQualifiedName(),
            "activity_name", finished.getActivityName(),
            "success", Boolean.toString(finished.isSuccess())),
        finished);
  }

  @Subscribe
  public void uninstallStarted(UninstallEvent.Started started) {
    writeChromeTraceEvent("buck",
        "uninstall",
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.<String, String>of(),
        started);
  }

  @Subscribe
  public void uninstallFinished(UninstallEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        "uninstall",
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of(
            "package_name", finished.getPackageName(),
            "success", Boolean.toString(finished.isSuccess())),
        finished);
  }

  @Subscribe
  public void artifactFetchStarted(ArtifactCacheEvent.Started started) {
    writeChromeTraceEvent("buck",
        started.getCategory(),
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.of(
            "rule_key", Joiner.on(", ").join(started.getRuleKeys())),
        started);
  }

  @Subscribe
  public void artifactFetchFinished(ArtifactCacheEvent.Finished finished) {
    ImmutableMap.Builder<String, String> argumentsBuilder = ImmutableMap.<String, String>builder()
        .put("success", Boolean.toString(finished.isSuccess()))
        .put("rule_key", Joiner.on(", ").join(finished.getRuleKeys()));
    Optionals.putIfPresent(finished.getCacheResult().transform(Functions.toStringFunction()),
        "cache_result",
        argumentsBuilder);

    writeChromeTraceEvent("buck",
        finished.getCategory(),
        ChromeTraceEvent.Phase.END,
        argumentsBuilder.build(),
        finished);
  }

  @Subscribe
  public void artifactConnectStarted(ArtifactCacheConnectEvent.Started started) {
    writeChromeTraceEvent("buck",
        "artifact_connect",
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.<String, String>of(),
        started);
  }

  @Subscribe
  public void artifactConnectFinished(ArtifactCacheConnectEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        "artifact_connect",
        ChromeTraceEvent.Phase.END,
        ImmutableMap.<String, String>of(),
        finished);
  }

  @Subscribe
  public void traceEvent(TraceEvent event) {
    writeChromeTraceEvent("buck",
        event.getEventName(),
        event.getPhase(),
        event.getProperties(),
        event);
  }

  @Subscribe
  public void testStartedEvent(TestSummaryEvent.Started started) {
    writeChromeTraceEvent("buck",
        "test",
        ChromeTraceEvent.Phase.BEGIN,
        ImmutableMap.of(
            "test_case_name", started.getTestCaseName(),
            "test_name", started.getTestName()),
        started);
  }

  @Subscribe
  public void testFinishedEvent(TestSummaryEvent.Finished finished) {
    writeChromeTraceEvent("buck",
        "test",
        ChromeTraceEvent.Phase.END,
        ImmutableMap.of(
            "test_case_name", finished.getTestCaseName(),
            "test_name", finished.getTestName()),
        finished);
  }

  private void writeChromeTraceEvent(String category,
      String name,
      ChromeTraceEvent.Phase phase,
      ImmutableMap<String, String> arguments,
      BuckEvent event) {
    eventList.add(new ChromeTraceEvent(category,
        name,
        phase,
        0,
        event.getThreadId(),
        TimeUnit.NANOSECONDS.toMicros(event.getNanoTime()),
        arguments));
  }
}


File: src/com/facebook/buck/event/listener/SimpleConsoleEventBusListener.java
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
package com.facebook.buck.event.listener;

import com.facebook.buck.cli.InstallEvent;
import com.facebook.buck.event.ConsoleEvent;
import com.facebook.buck.parser.ParseEvent;
import com.facebook.buck.rules.BuildEvent;
import com.facebook.buck.rules.BuildRuleEvent;
import com.facebook.buck.rules.IndividualTestEvent;
import com.facebook.buck.rules.TestRunEvent;
import com.facebook.buck.timing.Clock;
import com.facebook.buck.util.Console;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableList;
import com.google.common.eventbus.Subscribe;

import java.util.concurrent.atomic.AtomicLong;

/**
 * Implementation of {@code AbstractConsoleEventBusListener} for terminals that don't support ansi.
 */
public class SimpleConsoleEventBusListener extends AbstractConsoleEventBusListener {
  private final AtomicLong parseTime;
  private final TestResultFormatter testFormatter;

  public SimpleConsoleEventBusListener(Console console, Clock clock) {
    super(console, clock);

    this.parseTime = new AtomicLong(0);
    this.testFormatter = new TestResultFormatter(console.getAnsi(), console.getVerbosity());
  }

  @Override
  @Subscribe
  public void parseFinished(ParseEvent.Finished finished) {
    super.parseFinished(finished);
    ImmutableList.Builder<String> lines = ImmutableList.builder();
    this.parseTime.set(logEventPair("PARSING BUCK FILES",
        /* suffix */ Optional.<String>absent(),
        clock.currentTimeMillis(),
        0L,
        parseStarted,
        parseFinished,
        lines));
    printLines(lines);
  }

  @Override
  @Subscribe
  public void buildFinished(BuildEvent.Finished finished) {
    super.buildFinished(finished);
    ImmutableList.Builder<String> lines = ImmutableList.builder();
    logEventPair("BUILDING",
        /* suffix */ Optional.<String>absent(),
        clock.currentTimeMillis(),
        parseTime.get(),
        buildStarted,
        buildFinished,
        lines);
    printLines(lines);
  }

  @Override
  @Subscribe
  public void installFinished(InstallEvent.Finished finished) {
    super.installFinished(finished);
    ImmutableList.Builder<String> lines = ImmutableList.builder();
    logEventPair("INSTALLING",
        /* suffix */ Optional.<String>absent(),
        clock.currentTimeMillis(),
        0L,
        installStarted,
        installFinished,
        lines);
    printLines(lines);
  }

  @Subscribe
  public void logEvent(ConsoleEvent event) {
    ImmutableList.Builder<String> lines = ImmutableList.builder();
    formatConsoleEvent(event, lines);
    printLines(lines);
  }

  @Subscribe
  public void testRunStarted(TestRunEvent.Started event) {
    ImmutableList.Builder<String> lines = ImmutableList.builder();
    testFormatter.runStarted(lines,
        event.isRunAllTests(),
        event.getTestSelectorList(),
        event.shouldExplainTestSelectorList(),
        event.getTargetNames(),
        TestResultFormatter.FormatMode.BEFORE_TEST_RUN);
    printLines(lines);
  }

  @Subscribe
  public void testRunCompleted(TestRunEvent.Finished event) {
    ImmutableList.Builder<String> lines = ImmutableList.builder();
    testFormatter.runComplete(lines, event.getResults());
    printLines(lines);
  }

  @Subscribe
  public void testResultsAvailable(IndividualTestEvent.Finished event) {
    ImmutableList.Builder<String> lines = ImmutableList.builder();
    testFormatter.reportResult(lines, event.getResults());
    printLines(lines);
  }

  @Subscribe
  public void buildRuleFinished(BuildRuleEvent.Finished finished) {
    String line = String.format("BUILT %s", finished.getBuildRule().getFullyQualifiedName());
    if (ruleCount.isPresent()) {
      line += String.format(
          " (%d/%d JOBS)",
          numRulesCompleted.get(),
          ruleCount.get());
    }
    console.getStdErr().println(line);
  }

  private void printLines(ImmutableList.Builder<String> lines) {
    // Print through the {@code DirtyPrintStreamDecorator} so printing from the simple console
    // is considered to dirty stderr and stdout and so it gets synchronized to avoid interlacing
    // output.
    ImmutableList<String> stringList = lines.build();
    if (stringList.size() == 0) {
      return;
    }
    console.getStdErr().println(Joiner.on("\n").join(stringList));
  }
}


File: test/com/facebook/buck/cli/InstallCommandOptionsTest.java
/*
 * Copyright 2012-present Facebook, Inc.
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
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import org.kohsuke.args4j.CmdLineException;

public class InstallCommandOptionsTest {

  private InstallCommand getCommand(String... args) throws CmdLineException {
    InstallCommand command = new InstallCommand();
    new AdditionalOptionsCmdLineParser(command).parseArgument(args);
    return command;
  }

  private AdbOptions getAdbOptions(String...args) throws CmdLineException {
    return getCommand(args).adbOptions();
  }

  private TargetDeviceOptions getTargetDeviceOptions(String... args) throws CmdLineException {
    return getCommand(args).targetDeviceOptions();
  }

  @Test
  public void testInstallCommandOptionsRun() throws CmdLineException {
    InstallCommand command = getCommand(
        InstallCommand.RUN_SHORT_ARG, "katana",
        VerbosityParser.VERBOSE_SHORT_ARG, "10");
    assertTrue(command.shouldStartActivity());
    assertNull(command.getActivityToStart());
  }

  @Test
  public void testInstallCommandOptionsRunAndActivity() throws CmdLineException {
    InstallCommand command = getCommand(
        InstallCommand.RUN_SHORT_ARG,
        VerbosityParser.VERBOSE_SHORT_ARG, "10",
        "wakizashi",
        InstallCommand.ACTIVITY_SHORT_ARG, "com.facebook.katana.LoginActivity");
    assertTrue(command.shouldStartActivity());
    assertEquals("com.facebook.katana.LoginActivity", command.getActivityToStart());
  }

  @Test
  public void testInstallCommandOptionsActivity() throws CmdLineException {
    InstallCommand command = getCommand(
        "katana",
        InstallCommand.ACTIVITY_SHORT_ARG, ".LoginActivity");
    assertTrue(command.shouldStartActivity());
    assertEquals(".LoginActivity", command.getActivityToStart());
  }

  @Test
  public void testInstallCommandOptionsNone() throws CmdLineException {
    InstallCommand command = getCommand(
        VerbosityParser.VERBOSE_SHORT_ARG, "10",
        "katana");
    assertFalse(command.shouldStartActivity());
    assertNull(command.getActivityToStart());
  }

  @Test
  public void testInstallCommandOptionsEmulatorMode() throws CmdLineException {
    // Short form.
    TargetDeviceOptions options =
        getTargetDeviceOptions(TargetDeviceOptions.EMULATOR_MODE_SHORT_ARG);
    assertTrue(options.isEmulatorsOnlyModeEnabled());

    // Long form.
    options = getTargetDeviceOptions(TargetDeviceOptions.EMULATOR_MODE_LONG_ARG);
    assertTrue(options.isEmulatorsOnlyModeEnabled());

    // Is off by default.
    options = getTargetDeviceOptions();
    assertFalse(options.isEmulatorsOnlyModeEnabled());
  }

  @Test
  public void testInstallCommandOptionsDeviceMode() throws CmdLineException {
    // Short form.
    TargetDeviceOptions options = getTargetDeviceOptions(TargetDeviceOptions.DEVICE_MODE_SHORT_ARG);
    assertTrue(options.isRealDevicesOnlyModeEnabled());

    // Long form.
    options = getTargetDeviceOptions(TargetDeviceOptions.DEVICE_MODE_LONG_ARG);
    assertTrue(options.isRealDevicesOnlyModeEnabled());

    // Is off by default.
    options = getTargetDeviceOptions();
    assertFalse(options.isRealDevicesOnlyModeEnabled());
  }

  @Test
  public void testInstallCommandOptionsSerial() throws CmdLineException {
    String serial = "some-random-serial-number";
    // Short form.
    TargetDeviceOptions options = getTargetDeviceOptions(
        TargetDeviceOptions.SERIAL_NUMBER_SHORT_ARG, serial);
    assertTrue(options.hasSerialNumber());
    assertEquals(serial, options.getSerialNumber());

    // Long form.
    options = getTargetDeviceOptions(TargetDeviceOptions.SERIAL_NUMBER_LONG_ARG, serial);
    assertTrue(options.hasSerialNumber());
    assertEquals(serial, options.getSerialNumber());

    // Is off by default.
    options = getTargetDeviceOptions();
    assertFalse(options.hasSerialNumber());
    assertEquals(null, options.getSerialNumber());
  }

  @Test
  public void testInstallCommandOptionsMultiInstallMode() throws CmdLineException {
    // Short form.
    AdbOptions options = getAdbOptions(AdbOptions.MULTI_INSTALL_MODE_SHORT_ARG);
    assertTrue(options.isMultiInstallModeEnabled());

    // Long form.
    options = getAdbOptions(AdbOptions.MULTI_INSTALL_MODE_LONG_ARG);
    assertTrue(options.isMultiInstallModeEnabled());

    // Is off by default.
    options = getAdbOptions();
    assertFalse(options.isMultiInstallModeEnabled());
  }

  @Test
  public void testInstallCommandOptionsAdbThreads() throws CmdLineException {
    // Short form.
    AdbOptions options = getAdbOptions(AdbOptions.ADB_THREADS_SHORT_ARG, "4");
    assertEquals(4, options.getAdbThreadCount());

    // Long form.
    options = getAdbOptions(AdbOptions.ADB_THREADS_LONG_ARG, "4");
    assertEquals(4, options.getAdbThreadCount());

    // Is zero by default and overridden when creating the thread pool.
    options = getAdbOptions();
    assertEquals(0, options.getAdbThreadCount());
  }
}


File: test/com/facebook/buck/event/listener/SimpleConsoleEventBusListenerTest.java
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
package com.facebook.buck.event.listener;

import static com.facebook.buck.event.TestEventConfigerator.configureTestEventAtTime;
import static org.junit.Assert.assertEquals;

import com.facebook.buck.cli.InstallEvent;
import com.facebook.buck.event.BuckEventBus;
import com.facebook.buck.event.BuckEventBusFactory;
import com.facebook.buck.event.ConsoleEvent;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.parser.ParseEvent;
import com.facebook.buck.rules.BuildEvent;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleEvent;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRuleStatus;
import com.facebook.buck.rules.BuildRuleSuccessType;
import com.facebook.buck.rules.CacheResult;
import com.facebook.buck.rules.FakeBuildRule;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.testutil.TestConsole;
import com.facebook.buck.timing.Clock;
import com.facebook.buck.timing.IncrementingFakeClock;
import com.google.common.base.Functions;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;
import com.google.common.eventbus.EventBus;
import com.google.common.hash.HashCode;

import org.junit.Test;

import java.util.concurrent.TimeUnit;

public class SimpleConsoleEventBusListenerTest {
  @Test
  public void testSimpleBuild() {
    Clock fakeClock = new IncrementingFakeClock(TimeUnit.SECONDS.toNanos(1));
    BuckEventBus eventBus = BuckEventBusFactory.newInstance(fakeClock);
    EventBus rawEventBus = BuckEventBusFactory.getEventBusFor(eventBus);
    TestConsole console = new TestConsole();

    BuildTarget fakeTarget = BuildTargetFactory.newInstance("//banana:stand");
    ImmutableSet<BuildTarget> buildTargets = ImmutableSet.of(fakeTarget);
    Iterable<String> buildArgs = Iterables.transform(buildTargets, Functions.toStringFunction());
    FakeBuildRule fakeRule = new FakeBuildRule(
        fakeTarget,
        new SourcePathResolver(new BuildRuleResolver()),
        ImmutableSortedSet.<BuildRule>of());

    SimpleConsoleEventBusListener listener = new SimpleConsoleEventBusListener(console, fakeClock);
    eventBus.register(listener);

    final long threadId = 0;

    rawEventBus.post(
        configureTestEventAtTime(
            BuildEvent.started(buildArgs),
            0L,
            TimeUnit.MILLISECONDS,
            threadId));
    rawEventBus.post(configureTestEventAtTime(
        ParseEvent.started(buildTargets), 0L, TimeUnit.MILLISECONDS, threadId));

    assertEquals("", console.getTextWrittenToStdOut());
    assertEquals("", console.getTextWrittenToStdErr());

    rawEventBus.post(configureTestEventAtTime(
        ParseEvent.finished(buildTargets,
            Optional.<TargetGraph>absent()),
            400L,
            TimeUnit.MILLISECONDS,
            threadId));

    final String parsingLine = "[-] PARSING BUCK FILES...FINISHED 0.4s\n";

    assertEquals("", console.getTextWrittenToStdOut());
    assertEquals(parsingLine,
        console.getTextWrittenToStdErr());

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.started(fakeRule), 600L, TimeUnit.MILLISECONDS, threadId));

    rawEventBus.post(
        configureTestEventAtTime(
            BuildRuleEvent.finished(
                fakeRule,
                BuildRuleStatus.SUCCESS,
                CacheResult.miss(),
                Optional.of(BuildRuleSuccessType.BUILT_LOCALLY),
                Optional.<HashCode>absent(),
                Optional.<Long>absent()),
            1000L,
            TimeUnit.MILLISECONDS,
            threadId));
    rawEventBus.post(configureTestEventAtTime(
        BuildEvent.finished(buildArgs, 0), 1234L, TimeUnit.MILLISECONDS, threadId));

    final String buildingLine = "BUILT //banana:stand\n[-] BUILDING...FINISHED 0.8s\n";

    assertEquals("", console.getTextWrittenToStdOut());
    assertEquals(parsingLine + buildingLine,
        console.getTextWrittenToStdErr());

    rawEventBus.post(configureTestEventAtTime(
        ConsoleEvent.severe("I've made a huge mistake."), 1500L, TimeUnit.MILLISECONDS, threadId));

    final String logLine = "I've made a huge mistake.\n";

    assertEquals("", console.getTextWrittenToStdOut());
    assertEquals(parsingLine + buildingLine + logLine,
        console.getTextWrittenToStdErr());

    rawEventBus.post(configureTestEventAtTime(
        InstallEvent.started(fakeTarget), 2500L, TimeUnit.MILLISECONDS, threadId));

    assertEquals("", console.getTextWrittenToStdOut());
    assertEquals(parsingLine + buildingLine + logLine,
        console.getTextWrittenToStdErr());

    rawEventBus.post(configureTestEventAtTime(
        InstallEvent.finished(fakeTarget, true), 4000L, TimeUnit.MILLISECONDS, threadId));

    final String installLine = "[-] INSTALLING...FINISHED 1.5s\n";

    assertEquals("", console.getTextWrittenToStdOut());
    assertEquals(parsingLine + buildingLine + logLine + installLine,
        console.getTextWrittenToStdErr());
  }

}


File: test/com/facebook/buck/event/listener/SuperConsoleEventBusListenerTest.java
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
package com.facebook.buck.event.listener;

import static com.facebook.buck.event.TestEventConfigerator.configureTestEventAtTime;
import static org.junit.Assert.assertEquals;

import com.facebook.buck.cli.InstallEvent;
import com.facebook.buck.event.BuckEventBus;
import com.facebook.buck.event.BuckEventBusFactory;
import com.facebook.buck.event.ConsoleEvent;
import com.facebook.buck.httpserver.WebServer;
import com.facebook.buck.json.ProjectBuildFileParseEvents;
import com.facebook.buck.model.BuildTarget;
import com.facebook.buck.model.BuildTargetFactory;
import com.facebook.buck.parser.ParseEvent;
import com.facebook.buck.rules.ActionGraphEvent;
import com.facebook.buck.rules.BuildEvent;
import com.facebook.buck.rules.BuildRule;
import com.facebook.buck.rules.BuildRuleEvent;
import com.facebook.buck.rules.BuildRuleResolver;
import com.facebook.buck.rules.BuildRuleStatus;
import com.facebook.buck.rules.BuildRuleSuccessType;
import com.facebook.buck.rules.CacheResult;
import com.facebook.buck.rules.FakeBuildRule;
import com.facebook.buck.rules.SourcePathResolver;
import com.facebook.buck.rules.TargetGraph;
import com.facebook.buck.rules.TestRunEvent;
import com.facebook.buck.rules.TestSummaryEvent;
import com.facebook.buck.step.StepEvent;
import com.facebook.buck.test.TestCaseSummary;
import com.facebook.buck.test.TestResultSummary;
import com.facebook.buck.test.TestResults;
import com.facebook.buck.test.TestRuleEvent;
import com.facebook.buck.test.result.type.ResultType;
import com.facebook.buck.test.selectors.TestSelectorList;
import com.facebook.buck.testutil.TestConsole;
import com.facebook.buck.timing.Clock;
import com.facebook.buck.timing.IncrementingFakeClock;
import com.facebook.buck.util.FakeProcessExecutor;
import com.facebook.buck.util.environment.DefaultExecutionEnvironment;
import com.google.common.base.Function;
import com.google.common.base.Functions;
import com.google.common.base.Optional;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableSortedSet;
import com.google.common.collect.Iterables;
import com.google.common.eventbus.EventBus;
import com.google.common.hash.HashCode;

import org.junit.Test;

import java.text.DecimalFormat;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

public class SuperConsoleEventBusListenerTest {
  private static final DecimalFormat timeFormatter = new DecimalFormat("0.0s");

  /**
   * Formats a string with times passed in in seconds.
   *
   * Used to avoid these tests failing if the user's locale doesn't use '.' as the decimal
   * separator, as was the case in https://github.com/facebook/buck/issues/58.
   */
  private static String formatConsoleTimes(String template, Double... time) {
    return String.format(template, (Object[]) FluentIterable.from(ImmutableList.copyOf(time))
        .transform(new Function<Double, String>() {
            @Override
            public String apply(Double input) {
              return timeFormatter.format(input);
            }
          }).toArray(String.class));
  }

  @Test
  public void testSimpleBuild() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    Clock fakeClock = new IncrementingFakeClock(TimeUnit.SECONDS.toNanos(1));
    BuckEventBus eventBus = BuckEventBusFactory.newInstance(fakeClock);
    EventBus rawEventBus = BuckEventBusFactory.getEventBusFor(eventBus);
    TestConsole console = new TestConsole();

    BuildTarget fakeTarget = BuildTargetFactory.newInstance("//banana:stand");
    BuildTarget cachedTarget = BuildTargetFactory.newInstance("//chicken:dance");
    ImmutableSet<BuildTarget> buildTargets = ImmutableSet.of(fakeTarget, cachedTarget);
    Iterable<String> buildArgs = Iterables.transform(buildTargets, Functions.toStringFunction());
    FakeBuildRule fakeRule = new FakeBuildRule(
        fakeTarget,
        pathResolver,
        ImmutableSortedSet.<BuildRule>of());
    FakeBuildRule cachedRule = new FakeBuildRule(
        cachedTarget,
        pathResolver,
        ImmutableSortedSet.<BuildRule>of());

    SuperConsoleEventBusListener listener =
        new SuperConsoleEventBusListener(
            console,
            fakeClock,
            new DefaultExecutionEnvironment(
                new FakeProcessExecutor(),
                ImmutableMap.copyOf(System.getenv()),
                System.getProperties()),
        Optional.<WebServer>absent());
    eventBus.register(listener);

    rawEventBus.post(
        configureTestEventAtTime(
            new ProjectBuildFileParseEvents.Started(),
            0L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    validateConsole(console, listener, 0L, ImmutableList.of(
        formatConsoleTimes("[+] PARSING BUCK FILES...%s", 0.0)));

    validateConsole(
        console, listener, 100L, ImmutableList.of(
            formatConsoleTimes("[+] PARSING BUCK FILES...%s", 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(
            new ProjectBuildFileParseEvents.Finished(),
            200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    validateConsole(
        console, listener, 200L, ImmutableList.of(
            formatConsoleTimes("[-] PARSING BUCK FILES...FINISHED %s", 0.2)));

    rawEventBus.post(
        configureTestEventAtTime(
            BuildEvent.started(buildArgs),
            200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(configureTestEventAtTime(
        ParseEvent.started(buildTargets),
        200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 300L, ImmutableList.of(
        formatConsoleTimes("[+] PROCESSING BUCK FILES...%s", 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(ParseEvent.finished(buildTargets,
                                                     Optional.<TargetGraph>absent()),
        300L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(
        configureTestEventAtTime(
            ActionGraphEvent.finished(),
            400L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    final String parsingLine = formatConsoleTimes("[-] PROCESSING BUCK FILES...FINISHED %s", 0.2);

    validateConsole(console, listener, 540L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.1)));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.started(fakeRule),
        600L, TimeUnit.MILLISECONDS, /* threadId */ 0L));


    validateConsole(console, listener, 800L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.4),
        formatConsoleTimes(" |=> //banana:stand...  %s (checking local cache)", 0.2)));

    String stepShortName = "doing_something";
    String stepDescription = "working hard";
    UUID stepUuid = UUID.randomUUID();
    rawEventBus.post(configureTestEventAtTime(
        StepEvent.started(stepShortName, stepDescription, stepUuid),
          800L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 900L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.5),
        formatConsoleTimes(" |=> //banana:stand...  %s (running doing_something[%s])", 0.3, 0.1)));

    rawEventBus.post(configureTestEventAtTime(
        StepEvent.finished(stepShortName, stepDescription, stepUuid, 0),
        900L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.finished(
            fakeRule,
            BuildRuleStatus.SUCCESS,
            CacheResult.miss(),
            Optional.of(BuildRuleSuccessType.BUILT_LOCALLY),
            Optional.<HashCode>absent(),
            Optional.<Long>absent()),
        1000L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 1000L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.6),
        " |=> IDLE"));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.started(cachedRule),
        1010L, TimeUnit.MILLISECONDS, /* threadId */ 2L));

    validateConsole(console, listener, 1100L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.7),
        " |=> IDLE",
        formatConsoleTimes(" |=> //chicken:dance...  %s (checking local cache)", 0.1)));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.finished(
            cachedRule,
            BuildRuleStatus.SUCCESS,
            CacheResult.miss(),
            Optional.of(BuildRuleSuccessType.BUILT_LOCALLY),
            Optional.<HashCode>absent(),
            Optional.<Long>absent()),
        1120L, TimeUnit.MILLISECONDS, /* threadId */ 2L));

    rawEventBus.post(configureTestEventAtTime(
        BuildEvent.finished(buildArgs, 0),
        1234L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    final String buildingLine = formatConsoleTimes("[-] BUILDING...FINISHED %s", 0.8);

    validateConsole(console, listener, 1300L, ImmutableList.of(parsingLine, buildingLine));

    rawEventBus.post(configureTestEventAtTime(
        ConsoleEvent.severe("I've made a huge mistake."),
        1500L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 1600L, ImmutableList.of(parsingLine,
        buildingLine,
        "Log:",
        "I've made a huge mistake."));

    rawEventBus.post(configureTestEventAtTime(
        InstallEvent.started(fakeTarget),
        2500L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 3000L, ImmutableList.of(parsingLine,
        buildingLine,
        formatConsoleTimes("[+] INSTALLING...%s", 0.5),
        "Log:",
        "I've made a huge mistake."));

    rawEventBus.post(configureTestEventAtTime(
        InstallEvent.finished(fakeTarget, true),
        4000L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 5000L, ImmutableList.of(parsingLine,
        buildingLine,
        formatConsoleTimes("[-] INSTALLING...FINISHED %s", 1.5),
        "Log:",
        "I've made a huge mistake."));

    listener.render();
    String beforeStderrWrite = console.getTextWrittenToStdErr();
    console.getStdErr().print("ROFLCOPTER");
    listener.render();
    assertEquals("After stderr is written to by someone other than SuperConsole, rendering " +
        "should be a noop.",
        beforeStderrWrite + "ROFLCOPTER", console.getTextWrittenToStdErr());
  }

  @Test
  public void testSimpleTest() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    Clock fakeClock = new IncrementingFakeClock(TimeUnit.SECONDS.toNanos(1));
    BuckEventBus eventBus = BuckEventBusFactory.newInstance(fakeClock);
    EventBus rawEventBus = BuckEventBusFactory.getEventBusFor(eventBus);
    TestConsole console = new TestConsole();

    BuildTarget testTarget = BuildTargetFactory.newInstance("//:test");
    ImmutableSet<BuildTarget> testTargets = ImmutableSet.of(testTarget);
    Iterable<String> testArgs = Iterables.transform(testTargets, Functions.toStringFunction());
    FakeBuildRule testBuildRule = new FakeBuildRule(
        testTarget,
        pathResolver,
        ImmutableSortedSet.<BuildRule>of());

    SuperConsoleEventBusListener listener =
        new SuperConsoleEventBusListener(
            console,
            fakeClock,
            new DefaultExecutionEnvironment(
                new FakeProcessExecutor(),
                ImmutableMap.copyOf(System.getenv()),
                System.getProperties()),
        Optional.<WebServer>absent());
    eventBus.register(listener);

    rawEventBus.post(
        configureTestEventAtTime(
            new ProjectBuildFileParseEvents.Started(),
            0L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    validateConsole(console, listener, 0L, ImmutableList.of(
        formatConsoleTimes("[+] PARSING BUCK FILES...%s", 0.0)));

    validateConsole(
        console, listener, 100L, ImmutableList.of(
            formatConsoleTimes("[+] PARSING BUCK FILES...%s", 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(
            new ProjectBuildFileParseEvents.Finished(),
            200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    validateConsole(
        console, listener, 200L, ImmutableList.of(
            formatConsoleTimes("[-] PARSING BUCK FILES...FINISHED %s", 0.2)));

    rawEventBus.post(
        configureTestEventAtTime(
            BuildEvent.started(testArgs),
            200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(configureTestEventAtTime(
        ParseEvent.started(testTargets),
        200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 300L, ImmutableList.of(
        formatConsoleTimes("[+] PROCESSING BUCK FILES...%s", 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(ParseEvent.finished(testTargets,
                                                     Optional.<TargetGraph>absent()),
        300L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(
        configureTestEventAtTime(
            ActionGraphEvent.finished(),
            400L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    final String parsingLine = formatConsoleTimes("[-] PROCESSING BUCK FILES...FINISHED %s", 0.2);

    validateConsole(console, listener, 540L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.1)));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.started(testBuildRule),
        600L, TimeUnit.MILLISECONDS, /* threadId */ 0L));


    validateConsole(console, listener, 800L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.4),
        formatConsoleTimes(" |=> //:test...  %s (checking local cache)", 0.2)));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.finished(
            testBuildRule,
            BuildRuleStatus.SUCCESS,
            CacheResult.miss(),
            Optional.of(BuildRuleSuccessType.BUILT_LOCALLY),
            Optional.<HashCode>absent(),
            Optional.<Long>absent()),
        1000L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    rawEventBus.post(configureTestEventAtTime(
                         BuildEvent.finished(testArgs, 0),
                         1234L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    final String buildingLine = formatConsoleTimes("[-] BUILDING...FINISHED %s", 0.8);

    validateConsole(console, listener, 1300L, ImmutableList.of(parsingLine, buildingLine));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRunEvent.started(
                true, // isRunAllTests
                TestSelectorList.empty(),
                false, // shouldExplainTestSelectorList
                ImmutableSet.copyOf(testArgs)),
            2500L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3000L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.5)));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRuleEvent.started(testTarget),
            3100L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3200L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.7),
            formatConsoleTimes(" |=> //:test...  %s", 0.1)));

    UUID stepUuid = new UUID(0, 1);
    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.started(
                "step_name",
                "step_desc",
                stepUuid),
            3300L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3400L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.9),
            formatConsoleTimes(" |=> //:test...  %s (running step_name[%s])", 0.3, 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.finished(
                "step_name",
                "step_desc",
                stepUuid,
                0),
            3500L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3600L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 1.1),
            formatConsoleTimes(" |=> //:test...  %s", 0.5)));

    UUID testUUID = new UUID(2, 3);

    rawEventBus.post(
        configureTestEventAtTime(
            TestSummaryEvent.started(testUUID, "TestClass", "TestClass.Foo"),
            3700L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3800L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 1.3),
            formatConsoleTimes(" |=> //:test...  %s (running TestClass.Foo[%s])", 0.7, 0.1)));

    TestResultSummary testResultSummary =
        new TestResultSummary(
            "TestClass",
            "TestClass.Foo",
            ResultType.SUCCESS,
            0L, // time
            null, // message
            null, // stacktrace
            null, // stdOut
            null); // stdErr
    rawEventBus.post(
        configureTestEventAtTime(
            TestSummaryEvent.finished(
                testUUID,
                testResultSummary),
            3900L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        4000L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (1 PASS/0 FAIL)", 1.5),
            formatConsoleTimes(" |=> //:test...  %s", 0.9)));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRunEvent.finished(
                ImmutableSet.copyOf(testArgs),
                ImmutableList.of(
                    new TestResults(
                        testTarget,
                        ImmutableList.of(
                            new TestCaseSummary(
                                "TestClass",
                                ImmutableList.of(
                                    testResultSummary))),
                        ImmutableSet.<String>of(), // contacts
                        ImmutableSet.<String>of()))), // labels
            4100L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    final String testingLine = formatConsoleTimes("[-] TESTING...FINISHED %s (1 PASS/0 FAIL)", 1.6);

    validateConsole(
        console,
        listener,
        4200L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            testingLine,
            "Log:",
            "RESULTS FOR ALL TESTS",
            "PASS    <100ms  1 Passed   0 Skipped   0 Failed   TestClass",
            "TESTS PASSED"));
  }

  @Test
  public void testSkippedTest() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    Clock fakeClock = new IncrementingFakeClock(TimeUnit.SECONDS.toNanos(1));
    BuckEventBus eventBus = BuckEventBusFactory.newInstance(fakeClock);
    EventBus rawEventBus = BuckEventBusFactory.getEventBusFor(eventBus);
    TestConsole console = new TestConsole();

    BuildTarget testTarget = BuildTargetFactory.newInstance("//:test");
    ImmutableSet<BuildTarget> testTargets = ImmutableSet.of(testTarget);
    Iterable<String> testArgs = Iterables.transform(testTargets, Functions.toStringFunction());
    FakeBuildRule testBuildRule = new FakeBuildRule(
        testTarget,
        pathResolver,
        ImmutableSortedSet.<BuildRule>of());

    SuperConsoleEventBusListener listener =
        new SuperConsoleEventBusListener(
            console,
            fakeClock,
            new DefaultExecutionEnvironment(
                new FakeProcessExecutor(),
                ImmutableMap.copyOf(System.getenv()),
                System.getProperties()),
        Optional.<WebServer>absent());
    eventBus.register(listener);

    rawEventBus.post(
        configureTestEventAtTime(
            new ProjectBuildFileParseEvents.Started(),
            0L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    validateConsole(console, listener, 0L, ImmutableList.of(
        formatConsoleTimes("[+] PARSING BUCK FILES...%s", 0.0)));

    validateConsole(
        console, listener, 100L, ImmutableList.of(
            formatConsoleTimes("[+] PARSING BUCK FILES...%s", 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(
            new ProjectBuildFileParseEvents.Finished(),
            200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    validateConsole(
        console, listener, 200L, ImmutableList.of(
            formatConsoleTimes("[-] PARSING BUCK FILES...FINISHED %s", 0.2)));

    rawEventBus.post(
        configureTestEventAtTime(
            BuildEvent.started(testArgs),
            200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(configureTestEventAtTime(
        ParseEvent.started(testTargets),
        200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 300L, ImmutableList.of(
        formatConsoleTimes("[+] PROCESSING BUCK FILES...%s", 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(ParseEvent.finished(testTargets,
                                                     Optional.<TargetGraph>absent()),
        300L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(
        configureTestEventAtTime(
            ActionGraphEvent.finished(),
            400L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    final String parsingLine = formatConsoleTimes("[-] PROCESSING BUCK FILES...FINISHED %s", 0.2);

    validateConsole(console, listener, 540L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.1)));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.started(testBuildRule),
        600L, TimeUnit.MILLISECONDS, /* threadId */ 0L));


    validateConsole(console, listener, 800L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.4),
        formatConsoleTimes(" |=> //:test...  %s (checking local cache)", 0.2)));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.finished(
            testBuildRule,
            BuildRuleStatus.SUCCESS,
            CacheResult.miss(),
            Optional.of(BuildRuleSuccessType.BUILT_LOCALLY),
            Optional.<HashCode>absent(),
            Optional.<Long>absent()),
        1000L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    rawEventBus.post(configureTestEventAtTime(
                         BuildEvent.finished(testArgs, 0),
                         1234L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    final String buildingLine = formatConsoleTimes("[-] BUILDING...FINISHED %s", 0.8);

    validateConsole(console, listener, 1300L, ImmutableList.of(parsingLine, buildingLine));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRunEvent.started(
                true, // isRunAllTests
                TestSelectorList.empty(),
                false, // shouldExplainTestSelectorList
                ImmutableSet.copyOf(testArgs)),
            2500L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3000L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.5)));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRuleEvent.started(testTarget),
            3100L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3200L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.7),
            formatConsoleTimes(" |=> //:test...  %s", 0.1)));

    UUID stepUuid = new UUID(0, 1);
    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.started(
                "step_name",
                "step_desc",
                stepUuid),
            3300L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3400L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.9),
            formatConsoleTimes(" |=> //:test...  %s (running step_name[%s])", 0.3, 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.finished(
                "step_name",
                "step_desc",
                stepUuid,
                0),
            3500L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3600L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 1.1),
            formatConsoleTimes(" |=> //:test...  %s", 0.5)));

    UUID testUUID = new UUID(2, 3);

    rawEventBus.post(
        configureTestEventAtTime(
            TestSummaryEvent.started(testUUID, "TestClass", "TestClass.Foo"),
            3700L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3800L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 1.3),
            formatConsoleTimes(" |=> //:test...  %s (running TestClass.Foo[%s])", 0.7, 0.1)));

    TestResultSummary testResultSummary =
        new TestResultSummary(
            "TestClass",
            "TestClass.Foo",
            ResultType.ASSUMPTION_VIOLATION,
            0L, // time
            null, // message
            null, // stacktrace
            null, // stdOut
            null); // stdErr
    rawEventBus.post(
        configureTestEventAtTime(
            TestSummaryEvent.finished(
                testUUID,
                testResultSummary),
            3900L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        4000L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/1 SKIP/0 FAIL)", 1.5),
            formatConsoleTimes(" |=> //:test...  %s", 0.9)));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRunEvent.finished(
                ImmutableSet.copyOf(testArgs),
                ImmutableList.of(
                    new TestResults(
                        testTarget,
                        ImmutableList.of(
                            new TestCaseSummary(
                                "TestClass",
                                ImmutableList.of(
                                    testResultSummary))),
                        ImmutableSet.<String>of(), // contacts
                        ImmutableSet.<String>of()))), // labels
            4100L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    final String testingLine = formatConsoleTimes(
        "[-] TESTING...FINISHED %s (0 PASS/1 SKIP/0 FAIL)",
        1.6);

    validateConsole(
        console,
        listener,
        4200L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            testingLine,
            "Log:",
            "RESULTS FOR ALL TESTS",
            "ASSUME  <100ms  0 Passed   1 Skipped   0 Failed   TestClass",
            "TESTS PASSED (with some assumption violations)"));
  }

  @Test
  public void testFailingTest() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    Clock fakeClock = new IncrementingFakeClock(TimeUnit.SECONDS.toNanos(1));
    BuckEventBus eventBus = BuckEventBusFactory.newInstance(fakeClock);
    EventBus rawEventBus = BuckEventBusFactory.getEventBusFor(eventBus);
    TestConsole console = new TestConsole();

    BuildTarget testTarget = BuildTargetFactory.newInstance("//:test");
    ImmutableSet<BuildTarget> testTargets = ImmutableSet.of(testTarget);
    Iterable<String> testArgs = Iterables.transform(testTargets, Functions.toStringFunction());
    FakeBuildRule testBuildRule = new FakeBuildRule(
        testTarget,
        pathResolver,
        ImmutableSortedSet.<BuildRule>of());

    SuperConsoleEventBusListener listener =
        new SuperConsoleEventBusListener(
            console,
            fakeClock,
            new DefaultExecutionEnvironment(
                new FakeProcessExecutor(),
                ImmutableMap.copyOf(System.getenv()),
                System.getProperties()),
        Optional.<WebServer>absent());
    eventBus.register(listener);

    rawEventBus.post(
        configureTestEventAtTime(
            new ProjectBuildFileParseEvents.Started(),
            0L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    validateConsole(console, listener, 0L, ImmutableList.of(
        formatConsoleTimes("[+] PARSING BUCK FILES...%s", 0.0)));

    validateConsole(
        console, listener, 100L, ImmutableList.of(
            formatConsoleTimes("[+] PARSING BUCK FILES...%s", 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(
            new ProjectBuildFileParseEvents.Finished(),
            200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    validateConsole(
        console, listener, 200L, ImmutableList.of(
            formatConsoleTimes("[-] PARSING BUCK FILES...FINISHED %s", 0.2)));

    rawEventBus.post(
        configureTestEventAtTime(
            BuildEvent.started(testArgs),
            200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(configureTestEventAtTime(
        ParseEvent.started(testTargets),
        200L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    validateConsole(console, listener, 300L, ImmutableList.of(
        formatConsoleTimes("[+] PROCESSING BUCK FILES...%s", 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(ParseEvent.finished(testTargets,
                                                     Optional.<TargetGraph>absent()),
        300L, TimeUnit.MILLISECONDS, /* threadId */ 0L));
    rawEventBus.post(
        configureTestEventAtTime(
            ActionGraphEvent.finished(),
            400L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    final String parsingLine = formatConsoleTimes("[-] PROCESSING BUCK FILES...FINISHED %s", 0.2);

    validateConsole(console, listener, 540L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.1)));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.started(testBuildRule),
        600L, TimeUnit.MILLISECONDS, /* threadId */ 0L));


    validateConsole(console, listener, 800L, ImmutableList.of(parsingLine,
        formatConsoleTimes("[+] BUILDING...%s", 0.4),
        formatConsoleTimes(" |=> //:test...  %s (checking local cache)", 0.2)));

    rawEventBus.post(configureTestEventAtTime(
        BuildRuleEvent.finished(
            testBuildRule,
            BuildRuleStatus.SUCCESS,
            CacheResult.miss(),
            Optional.of(BuildRuleSuccessType.BUILT_LOCALLY),
            Optional.<HashCode>absent(),
            Optional.<Long>absent()),
        1000L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    rawEventBus.post(configureTestEventAtTime(
                         BuildEvent.finished(testArgs, 0),
                         1234L, TimeUnit.MILLISECONDS, /* threadId */ 0L));

    final String buildingLine = formatConsoleTimes("[-] BUILDING...FINISHED %s", 0.8);

    validateConsole(console, listener, 1300L, ImmutableList.of(parsingLine, buildingLine));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRunEvent.started(
                true, // isRunAllTests
                TestSelectorList.empty(),
                false, // shouldExplainTestSelectorList
                ImmutableSet.copyOf(testArgs)),
            2500L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3000L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.5)));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRuleEvent.started(testTarget),
            3100L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3200L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.7),
            formatConsoleTimes(" |=> //:test...  %s", 0.1)));

    UUID stepUuid = new UUID(0, 1);
    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.started(
                "step_name",
                "step_desc",
                stepUuid),
            3300L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3400L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 0.9),
            formatConsoleTimes(" |=> //:test...  %s (running step_name[%s])", 0.3, 0.1)));

    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.finished(
                "step_name",
                "step_desc",
                stepUuid,
                0),
            3500L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3600L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 1.1),
            formatConsoleTimes(" |=> //:test...  %s", 0.5)));

    UUID testUUID = new UUID(2, 3);

    rawEventBus.post(
        configureTestEventAtTime(
            TestSummaryEvent.started(testUUID, "TestClass", "TestClass.Foo"),
            3700L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        3800L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/0 FAIL)", 1.3),
            formatConsoleTimes(" |=> //:test...  %s (running TestClass.Foo[%s])", 0.7, 0.1)));

    TestResultSummary testResultSummary =
        new TestResultSummary(
            "TestClass",
            "TestClass.Foo",
            ResultType.FAILURE,
            0L, // time
            "Foo.java:47: Assertion failure: 'foo' != 'bar'", // message
            null, // stacktrace
            "Message on stdout", // stdOut
            "Message on stderr"); // stdErr
    rawEventBus.post(
        configureTestEventAtTime(
            TestSummaryEvent.finished(
                testUUID,
                testResultSummary),
            3900L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    validateConsole(
        console,
        listener,
        4000L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            formatConsoleTimes("[+] TESTING...%s (0 PASS/1 FAIL)", 1.5),
            formatConsoleTimes(" |=> //:test...  %s", 0.9),
            "Log:",
            "FAILURE TestClass.Foo: Foo.java:47: Assertion failure: 'foo' != 'bar'"));

    rawEventBus.post(
        configureTestEventAtTime(
            TestRunEvent.finished(
                ImmutableSet.copyOf(testArgs),
                ImmutableList.of(
                    new TestResults(
                        testTarget,
                        ImmutableList.of(
                            new TestCaseSummary(
                                "TestClass",
                                ImmutableList.of(
                                    testResultSummary))),
                        ImmutableSet.<String>of(), // contacts
                        ImmutableSet.<String>of()))), // labels
            4100L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    final String testingLine = formatConsoleTimes("[-] TESTING...FINISHED %s (0 PASS/1 FAIL)", 1.6);

    validateConsole(
        console,
        listener,
        4200L,
        ImmutableList.of(
            parsingLine,
            buildingLine,
            testingLine,
            "Log:",
            "FAILURE TestClass.Foo: Foo.java:47: Assertion failure: 'foo' != 'bar'",
            "RESULTS FOR ALL TESTS",
            "FAIL    <100ms  0 Passed   0 Skipped   1 Failed   TestClass",
            "FAILURE TestClass.Foo: Foo.java:47: Assertion failure: 'foo' != 'bar'",
            "====STANDARD OUT====",
            "Message on stdout",
            "====STANDARD ERR====",
            "Message on stderr",
            "TESTS FAILED: 1 FAILURE",
            "Failed target: //:test",
            "FAIL TestClass"));
  }

  @Test
  public void testBuildRuleSuspendResumeEvents() {
    SourcePathResolver pathResolver = new SourcePathResolver(new BuildRuleResolver());
    Clock fakeClock = new IncrementingFakeClock(TimeUnit.SECONDS.toNanos(1));
    BuckEventBus eventBus = BuckEventBusFactory.newInstance(fakeClock);
    EventBus rawEventBus = BuckEventBusFactory.getEventBusFor(eventBus);
    TestConsole console = new TestConsole();

    BuildTarget fakeTarget = BuildTargetFactory.newInstance("//banana:stand");
    ImmutableSet<BuildTarget> buildTargets = ImmutableSet.of(fakeTarget);
    Iterable<String> buildArgs = Iterables.transform(buildTargets, Functions.toStringFunction());
    FakeBuildRule fakeRule = new FakeBuildRule(
        fakeTarget,
        pathResolver,
        ImmutableSortedSet.<BuildRule>of());
    String stepShortName = "doing_something";
    String stepDescription = "working hard";
    UUID stepUuid = UUID.randomUUID();

    SuperConsoleEventBusListener listener =
        new SuperConsoleEventBusListener(
            console,
            fakeClock,
            new DefaultExecutionEnvironment(
                new FakeProcessExecutor(),
                ImmutableMap.copyOf(System.getenv()),
                System.getProperties()),
            Optional.<WebServer>absent());
    eventBus.register(listener);

    // Start the build.
    rawEventBus.post(
        configureTestEventAtTime(
            BuildEvent.started(buildArgs),
            0L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    // Start and stop parsing.
    String parsingLine = formatConsoleTimes("[-] PROCESSING BUCK FILES...FINISHED 0.0s");
    rawEventBus.post(
        configureTestEventAtTime(
            ParseEvent.started(buildTargets),
            0L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));
    rawEventBus.post(
        configureTestEventAtTime(
            ParseEvent.finished(buildTargets, Optional.<TargetGraph>absent()),
            0L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));
    rawEventBus.post(
        configureTestEventAtTime(
            ActionGraphEvent.finished(),
            0L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    // Start the rule.
    rawEventBus.post(
        configureTestEventAtTime(
            BuildRuleEvent.started(fakeRule),
            0L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    // Post events that run a step for 100ms.
    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.started(stepShortName, stepDescription, stepUuid),
            0L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));
    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.finished(stepShortName, stepDescription, stepUuid, /* exitCode */ 0),
            100L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    // Suspend the rule.
    rawEventBus.post(
        configureTestEventAtTime(
            BuildRuleEvent.suspended(fakeRule),
            100L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    // Verify that the rule isn't printed now that it's suspended.
    validateConsole(
        console,
        listener,
        200L,
        ImmutableList.of(
            parsingLine,
            formatConsoleTimes("[+] BUILDING...%s", 0.2),
            " |=> IDLE"));

    // Resume the rule.
    rawEventBus.post(
        configureTestEventAtTime(
            BuildRuleEvent.resumed(fakeRule),
            300L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    // Verify that we print "checking local..." now that we've resumed, and that we're accounting
    // for previous running time.
    validateConsole(
        console,
        listener,
        300L,
        ImmutableList.of(
            parsingLine,
            formatConsoleTimes("[+] BUILDING...%s", 0.3),
            formatConsoleTimes(" |=> //banana:stand...  %s (checking local cache)", 0.1)));

    // Post events that run another step.
    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.started(stepShortName, stepDescription, stepUuid),
            400L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    // Verify the current console now accounts for the step.
    validateConsole(
        console,
        listener,
        500L,
        ImmutableList.of(
            parsingLine,
            formatConsoleTimes("[+] BUILDING...%s", 0.5),
            formatConsoleTimes(
                " |=> //banana:stand...  %s (running doing_something[%s])",
                0.3,
                0.1)));

    // Finish the step and rule.
    rawEventBus.post(
        configureTestEventAtTime(
            StepEvent.finished(stepShortName, stepDescription, stepUuid, /* exitCode */ 0),
            600L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));
    rawEventBus.post(
        configureTestEventAtTime(
            BuildRuleEvent.finished(
                fakeRule,
                BuildRuleStatus.SUCCESS,
                CacheResult.miss(),
                Optional.of(BuildRuleSuccessType.BUILT_LOCALLY),
                Optional.<HashCode>absent(),
                Optional.<Long>absent()),
            600L,
            TimeUnit.MILLISECONDS,
            /* threadId */ 0L));

    // Verify that the rule isn't printed now that it's finally finished..
    validateConsole(
        console,
        listener,
        700L,
        ImmutableList.of(
            parsingLine,
            formatConsoleTimes("[+] BUILDING...%s", 0.7),
            " |=> IDLE"));
  }

  private void validateConsole(TestConsole console,
      SuperConsoleEventBusListener listener,
      long timeMs,
      ImmutableList<String> lines) {
    assertEquals("", console.getTextWrittenToStdOut());
    assertEquals("", console.getTextWrittenToStdErr());
    assertEquals(lines, listener.createRenderLinesAtTime(timeMs));
  }
}
