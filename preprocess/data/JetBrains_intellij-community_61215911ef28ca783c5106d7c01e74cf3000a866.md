Refactoring Types: ['Extract Method']
ains/idea/svn/commandLine/Command.java
package org.jetbrains.idea.svn.commandLine;

import com.intellij.openapi.util.text.StringUtil;
import com.intellij.util.Function;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.idea.svn.api.Depth;
import org.jetbrains.idea.svn.api.ProgressTracker;
import org.jetbrains.idea.svn.properties.PropertyValue;
import org.tmatesoft.svn.core.SVNURL;
import org.tmatesoft.svn.core.wc.SVNRevision;
import org.tmatesoft.svn.core.wc2.SvnTarget;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;

/**
 * @author Konstantin Kolosovsky.
 */
// TODO: Probably make command immutable and use CommandBuilder for updates.
public class Command {

  @NotNull private final List<String> myParameters = ContainerUtil.newArrayList();
  @NotNull private final List<String> myOriginalParameters = ContainerUtil.newArrayList();
  @NotNull private final SvnCommandName myName;

  private File workingDirectory;
  @Nullable private File myConfigDir;
  @Nullable private LineCommandListener myResultBuilder;
  @Nullable private volatile SVNURL myRepositoryUrl;
  @NotNull private SvnTarget myTarget;
  @Nullable private Collection<File> myTargets;
  @Nullable private PropertyValue myPropertyValue;

  @Nullable private ProgressTracker myCanceller;

  public Command(@NotNull SvnCommandName name) {
    myName = name;
  }

  public void put(@Nullable Depth depth) {
    CommandUtil.put(myParameters, depth, false);
  }

  public void put(@NotNull SvnTarget target) {
    CommandUtil.put(myParameters, target);
  }

  public void put(@Nullable SVNRevision revision) {
    CommandUtil.put(myParameters, revision);
  }

  public void put(@NotNull String parameter, boolean condition) {
    CommandUtil.put(myParameters, condition, parameter);
  }

  public void put(@NonNls @NotNull String... parameters) {
    put(Arrays.asList(parameters));
  }

  public void put(@NotNull List<String> parameters) {
    myParameters.addAll(parameters);
  }

  public void putIfNotPresent(@NotNull String parameter) {
    if (!myParameters.contains(parameter)) {
      myParameters.add(parameter);
    }
  }

  @Nullable
  public ProgressTracker getCanceller() {
    return myCanceller;
  }

  public void setCanceller(@Nullable ProgressTracker canceller) {
    myCanceller = canceller;
  }

  @Nullable
  public File getConfigDir() {
    return myConfigDir;
  }

  public File getWorkingDirectory() {
    return workingDirectory;
  }

  @Nullable
  public LineCommandListener getResultBuilder() {
    return myResultBuilder;
  }

  @Nullable
  public SVNURL getRepositoryUrl() {
    return myRepositoryUrl;
  }

  @NotNull
  public SVNURL requireRepositoryUrl() {
    SVNURL result = getRepositoryUrl();
    assert result != null;

    return result;
  }

  @NotNull
  public SvnTarget getTarget() {
    return myTarget;
  }

  @Nullable
  public List<String> getTargetsPaths() {
    return ContainerUtil.isEmpty(myTargets) ? null : ContainerUtil.map(myTargets, new Function<File, String>() {
      @Override
      public String fun(File file) {
        return file.getAbsolutePath();
      }
    });
  }

  @Nullable
  public PropertyValue getPropertyValue() {
    return myPropertyValue;
  }

  @NotNull
  public SvnCommandName getName() {
    return myName;
  }

  public void setWorkingDirectory(File workingDirectory) {
    this.workingDirectory = workingDirectory;
  }

  public void setConfigDir(@Nullable File configDir) {
    this.myConfigDir = configDir;
  }

  public void setResultBuilder(@Nullable LineCommandListener resultBuilder) {
    myResultBuilder = resultBuilder;
  }

  public void setRepositoryUrl(@Nullable SVNURL repositoryUrl) {
    myRepositoryUrl = repositoryUrl;
  }

  public void setTarget(@NotNull SvnTarget target) {
    myTarget = target;
  }

  public void setTargets(@Nullable Collection<File> targets) {
    myTargets = targets;
  }

  public void setPropertyValue(@Nullable PropertyValue propertyValue) {
    myPropertyValue = propertyValue;
  }

  // TODO: used only to ensure authentication info is not logged to file. Remove when command execution model is refactored
  // TODO: - so we could determine if parameter should be logged by the parameter itself.
  public void saveOriginalParameters() {
    myOriginalParameters.clear();
    myOriginalParameters.addAll(myParameters);
  }

  @NotNull
  public List<String> getParameters() {
    return ContainerUtil.newArrayList(myParameters);
  }

  public String getText() {
    List<String> data = new ArrayList<String>();

    if (myConfigDir != null) {
      data.add("--config-dir");
      data.add(myConfigDir.getPath());
    }
    data.add(myName.getName());
    data.addAll(myOriginalParameters);

    List<String> targetsPaths = getTargetsPaths();
    if (!ContainerUtil.isEmpty(targetsPaths)) {
      data.addAll(targetsPaths);
    }

    return StringUtil.join(data, " ");
  }

  public boolean isLocalInfo() {
    return is(SvnCommandName.info) && hasLocalTarget() && !myParameters.contains("--revision");
  }

  public boolean isLocalStatus() {
    return is(SvnCommandName.st) && hasLocalTarget() && !myParameters.contains("-u");
  }

  public boolean isLocalProperty() {
    boolean isPropertyCommand =
      is(SvnCommandName.proplist) || is(SvnCommandName.propget) || is(SvnCommandName.propset) || is(SvnCommandName.propdel);

    return isPropertyCommand && hasLocalTarget() && isLocal(getRevision());
  }

  public boolean isLocalCat() {
    return is(SvnCommandName.cat) && hasLocalTarget() && isLocal(getRevision());
  }

  @Nullable
  private SVNRevision getRevision() {
    int index = myParameters.indexOf("--revision");

    return index >= 0 && index + 1 < myParameters.size() ? SVNRevision.parse(myParameters.get(index + 1)) : null;
  }

  public boolean is(@NotNull SvnCommandName name) {
    return name.equals(myName);
  }

  private boolean hasLocalTarget() {
    return myTarget.isFile() && isLocal(myTarget.getPegRevision());
  }

  private static boolean isLocal(@Nullable SVNRevision revision) {
    return revision == null ||
           SVNRevision.UNDEFINED.equals(revision) ||
           SVNRevision.BASE.equals(revision) ||
           SVNRevision.WORKING.equals(revision);
  }
}

File: plugins/svn4idea/src/org/jetbrains/idea/svn/commandLine/CommandUtil.java
package org.jetbrains.idea.svn.commandLine;

import com.intellij.openapi.application.PathManager;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.util.text.DateFormatUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.idea.svn.api.Depth;
import org.jetbrains.idea.svn.diff.DiffOptions;
import org.jetbrains.idea.svn.status.StatusType;
import org.tmatesoft.svn.core.wc.SVNRevision;
import org.tmatesoft.svn.core.wc2.SvnTarget;

import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBException;
import javax.xml.bind.Unmarshaller;
import java.io.File;
import java.io.StringReader;
import java.util.List;

/**
 * @author Konstantin Kolosovsky.
 */
public class CommandUtil {

  /**
   * Puts given value to parameters if condition is satisfied
   *
   * @param parameters
   * @param condition
   * @param value
   */
  public static void put(@NotNull List<String> parameters, boolean condition, @NotNull String value) {
    if (condition) {
      parameters.add(value);
    }
  }

  public static void put(@NotNull List<String> parameters, @NotNull File path) {
    put(parameters, path.getAbsolutePath(), SVNRevision.UNDEFINED);
  }

  public static void put(@NotNull List<String> parameters, @NotNull File path, boolean usePegRevision) {
    if (usePegRevision) {
      put(parameters, path);
    } else {
      parameters.add(path.getAbsolutePath());
    }
  }

  public static void put(@NotNull List<String> parameters, @NotNull File path, @Nullable SVNRevision pegRevision) {
    put(parameters, path.getAbsolutePath(), pegRevision);
  }

  public static void put(@NotNull List<String> parameters, @NotNull String path, @Nullable SVNRevision pegRevision) {
    StringBuilder builder = new StringBuilder(path);

    boolean hasAtSymbol = path.contains("@");
    boolean hasPegRevision = pegRevision != null &&
                             !SVNRevision.UNDEFINED.equals(pegRevision) &&
                             !SVNRevision.WORKING.equals(pegRevision) &&
                             pegRevision.isValid();

    if (hasPegRevision || hasAtSymbol) {
      // add '@' to correctly handle paths that contain '@' symbol
      builder.append("@");
    }
    if (hasPegRevision) {
      builder.append(format(pegRevision));
    }

    parameters.add(builder.toString());
  }

  public static void put(@NotNull List<String> parameters, @NotNull SvnTarget target) {
    put(parameters, target.getPathOrUrlString(), target.getPegRevision());
  }

  public static void put(@NotNull List<String> parameters, @NotNull SvnTarget target, boolean usePegRevision) {
    if (usePegRevision) {
      put(parameters, target);
    } else {
      parameters.add(target.getPathOrUrlString());
    }
  }

  public static void put(@NotNull List<String> parameters, @Nullable Depth depth) {
    put(parameters, depth, false);
  }

  public static void put(@NotNull List<String> parameters, @Nullable Depth depth, boolean sticky) {
    if (depth != null && !Depth.UNKNOWN.equals(depth)) {
      parameters.add("--depth");
      parameters.add(depth.getName());

      if (sticky) {
        parameters.add("--set-depth");
        parameters.add(depth.getName());
      }
    }
  }

  public static void put(@NotNull List<String> parameters, @Nullable SVNRevision revision) {
    if (revision != null && !SVNRevision.UNDEFINED.equals(revision) && !SVNRevision.WORKING.equals(revision) && revision.isValid()) {
      parameters.add("--revision");
      parameters.add(format(revision));
    }
  }

  public static void put(@NotNull List<String> parameters, @NotNull SVNRevision startRevision, @NotNull SVNRevision endRevision) {
    parameters.add("--revision");
    parameters.add(format(startRevision) + ":" + format(endRevision));
  }

  @NotNull
  public static String format(@NotNull SVNRevision revision) {
    return revision.getDate() != null ? "{" + DateFormatUtil.ISO8601_DATE_FORMAT.format(revision.getDate()) + "}" : revision.toString();
  }

  public static void put(@NotNull List<String> parameters, @Nullable DiffOptions diffOptions) {
    if (diffOptions != null) {
      StringBuilder builder = new StringBuilder();

      if (diffOptions.isIgnoreAllWhitespace()) {
        builder.append(" --ignore-space-change");
      }
      if (diffOptions.isIgnoreAmountOfWhitespace()) {
        builder.append(" --ignore-all-space");
      }
      if (diffOptions.isIgnoreEOLStyle()) {
        builder.append(" --ignore-eol-style");
      }

      String value = builder.toString().trim();

      if (!StringUtil.isEmpty(value)) {
        parameters.add("--extensions");
        parameters.add(value);
      }
    }
  }

  public static void putChangeLists(@NotNull List<String> parameters, @Nullable Iterable<String> changeLists) {
    if (changeLists != null) {
      for (String changeList : changeLists) {
        parameters.add("--cl");
        parameters.add(changeList);
      }
    }
  }

  public static String escape(@NotNull String path) {
    return path.contains("@") ? path + "@" : path;
  }

  public static <T> T parse(@NotNull String data, @NotNull Class<T> type) throws JAXBException {
    JAXBContext context = JAXBContext.newInstance(type);
    Unmarshaller unmarshaller = context.createUnmarshaller();

    return (T) unmarshaller.unmarshal(new StringReader(data.trim()));
  }

  @NotNull
  public static File getHomeDirectory() {
    return new File(PathManager.getHomePath());
  }

  /**
   * Gets svn status represented by single character.
   *
   * @param type
   * @return
   */
  public static char getStatusChar(@Nullable String type) {
    return !StringUtil.isEmpty(type) ? type.charAt(0) : ' ';
  }

  @NotNull
  public static StatusType getStatusType(@Nullable String type) {
    return getStatusType(getStatusChar(type));
  }

  @NotNull
  public static StatusType getStatusType(char first) {
    final StatusType contentsStatus;
    if ('A' == first) {
      contentsStatus = StatusType.STATUS_ADDED;
    } else if ('D' == first) {
      contentsStatus = StatusType.STATUS_DELETED;
    } else if ('U' == first) {
      contentsStatus = StatusType.CHANGED;
    } else if ('C' == first) {
      contentsStatus = StatusType.CONFLICTED;
    } else if ('G' == first) {
      contentsStatus = StatusType.MERGED;
    } else if ('R' == first) {
      contentsStatus = StatusType.STATUS_REPLACED;
    } else if ('E' == first) {
      contentsStatus = StatusType.STATUS_OBSTRUCTED;
    } else {
      contentsStatus = StatusType.STATUS_NORMAL;
    }
    return contentsStatus;
  }

  public static File correctUpToExistingParent(File base) {
    while (base != null) {
      if (base.exists() && base.isDirectory()) return base;
      base = base.getParentFile();
    }
    return null;
  }
}
