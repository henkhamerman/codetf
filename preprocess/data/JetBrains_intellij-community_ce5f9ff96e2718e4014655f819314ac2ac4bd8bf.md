Refactoring Types: ['Move Method']
ntellij/ui/LayeredIcon.java
/*
 * Copyright 2000-2014 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.ui;

import com.intellij.openapi.diagnostic.Logger;
import org.jetbrains.annotations.NotNull;

import javax.swing.*;
import java.awt.*;
import java.util.Arrays;

public class LayeredIcon implements Icon {
  private static final Logger LOG = Logger.getInstance("#com.intellij.ui.LayeredIcon");
  private final Icon[] myIcons;
  private final boolean[] myDisabledLayers;
  private final int[] myHShifts;
  private final int[] myVShifts;

  private int myWidth;
  private int myHeight;
  private int myXShift;
  private int myYShift;

  public LayeredIcon(int layerCount) {
    myIcons = new Icon[layerCount];
    myDisabledLayers = new boolean[layerCount];
    myHShifts = new int[layerCount];
    myVShifts = new int[layerCount];
  }

  public LayeredIcon(@NotNull Icon... icons) {
    this(icons.length);
    for (int i = 0; i < icons.length; i++) {
      setIcon(icons[i], i);
    }
  }

  public static LayeredIcon createHorizontalIcon(@NotNull Icon... icons) {
    LayeredIcon result = new LayeredIcon(icons.length);
    int maxHeight = 0;
    for (Icon icon : icons) {
      maxHeight = Math.max(maxHeight, icon.getIconHeight());
    }
    int hShift = 0;
    for (int i = 0; i < icons.length; i++) {
      result.setIcon(icons[i], i, hShift, (maxHeight - icons[i].getIconHeight()) / 2);
      hShift +=icons[i].getIconWidth() + 1;
    }
    return result;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof LayeredIcon)) return false;

    final LayeredIcon icon = (LayeredIcon)o;

    if (myHeight != icon.myHeight) return false;
    if (myWidth != icon.myWidth) return false;
    if (myXShift != icon.myXShift) return false;
    if (myYShift != icon.myYShift) return false;
    if (!Arrays.equals(myHShifts, icon.myHShifts)) return false;
    if (!Arrays.equals(myIcons, icon.myIcons)) return false;
    if (!Arrays.equals(myVShifts, icon.myVShifts)) return false;

    return true;
  }

  @Override
  public int hashCode() {
    return 0;
  }

  public void setIcon(Icon icon, int layer) {
    setIcon(icon, layer, 0, 0);
  }

  public Icon getIcon(int layer) {
    return myIcons[layer];
  }

  public Icon[] getAllLayers() {
    return myIcons;
  }

  public void setIcon(Icon icon, int layer, int hShift, int vShift) {
    if (icon instanceof LayeredIcon) {
      ((LayeredIcon)icon).checkIHaventIconInsideMe(this);
    }
    myIcons[layer] = icon;
    myHShifts[layer] = hShift;
    myVShifts[layer] = vShift;
    recalculateSize();
  }

  private void checkIHaventIconInsideMe(Icon icon) {
    LOG.assertTrue(icon != this);
    for (Icon child : myIcons) {
      if (child instanceof LayeredIcon) ((LayeredIcon)child).checkIHaventIconInsideMe(icon);
    }
  }

  @Override
  public void paintIcon(Component c, Graphics g, int x, int y) {
    for(int i = 0; i < myIcons.length; i++){
      Icon icon = myIcons[i];
      if (icon == null || myDisabledLayers[i]) continue;
      icon.paintIcon(c, g, myXShift + x + myHShifts[i], myYShift + y + myVShifts[i]);
    }
  }

  public boolean isLayerEnabled(int layer) {
    return !myDisabledLayers[layer];
  }

  public void setLayerEnabled(int layer, boolean enabled) {
    myDisabledLayers[layer] = !enabled;
  }

  @Override
  public int getIconWidth() {
    if (myWidth <= 1) { //icon is not loaded yet
      recalculateSize();
    }
    return myWidth;
  }

  @Override
  public int getIconHeight() {
    if (myHeight <= 1) { //icon is not loaded yet
      recalculateSize();
    }
    return myHeight;
  }

  private void recalculateSize() {
    int minX = Integer.MAX_VALUE;
    int maxX = Integer.MIN_VALUE;
    int minY = Integer.MAX_VALUE;
    int maxY = Integer.MIN_VALUE;
    for(int i = 0; i < myIcons.length; i++){
      Icon icon = myIcons[i];
      if (icon == null) continue;
      int hShift = myHShifts[i];
      int vShift = myVShifts[i];
      minX = Math.min(minX, hShift);
      maxX = Math.max(maxX, hShift + icon.getIconWidth());
      minY = Math.min(minY, vShift);
      maxY = Math.max(maxY, vShift + icon.getIconHeight());
    }
    myWidth = maxX - minX;
    myHeight = maxY - minY;

    if (myIcons.length > 1) {
      myXShift = -minX;
      myYShift = -minY;
    }
  }

  public static Icon create(final Icon backgroundIcon, final Icon foregroundIcon) {
    final LayeredIcon layeredIcon = new LayeredIcon(2);
    layeredIcon.setIcon(backgroundIcon, 0);
    layeredIcon.setIcon(foregroundIcon, 1);
    return layeredIcon;
  }
}


File: platform/core-api/src/com/intellij/util/IconUtil.java
/*
 * Copyright 2000-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.util;

import com.intellij.ide.FileIconPatcher;
import com.intellij.ide.FileIconProvider;
import com.intellij.ide.presentation.VirtualFilePresentation;
import com.intellij.openapi.extensions.Extensions;
import com.intellij.openapi.project.DumbService;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.IconLoader;
import com.intellij.openapi.util.Iconable;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.SystemInfo;
import com.intellij.openapi.vfs.VFileProperty;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.openapi.vfs.WritingAccessProvider;
import com.intellij.ui.IconDeferrer;
import com.intellij.ui.JBColor;
import com.intellij.ui.LayeredIcon;
import com.intellij.ui.RowIcon;
import com.intellij.util.ui.*;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.awt.geom.AffineTransform;
import java.awt.image.BufferedImage;


/**
 * @author max
 * @author Konstantin Bulenkov
 */
public class IconUtil {
  private static final Key<Boolean> PROJECT_WAS_EVER_INITIALIZED = Key.create("iconDeferrer:projectWasEverInitialized");

  private static boolean wasEverInitialized(@NotNull Project project) {
    Boolean was = project.getUserData(PROJECT_WAS_EVER_INITIALIZED);
    if (was == null) {
      if (project.isInitialized()) {
        was = Boolean.valueOf(true);
        project.putUserData(PROJECT_WAS_EVER_INITIALIZED, was);
      }
      else {
        was = Boolean.valueOf(false);
      }
    }

    return was.booleanValue();
  }

  @NotNull
  public static Icon cropIcon(@NotNull Icon icon, int maxWidth, int maxHeight) {
    if (icon.getIconHeight() <= maxHeight && icon.getIconWidth() <= maxWidth) {
      return icon;
    }

    final int w = Math.min(icon.getIconWidth(), maxWidth);
    final int h = Math.min(icon.getIconHeight(), maxHeight);

    final BufferedImage image = GraphicsEnvironment
      .getLocalGraphicsEnvironment()
      .getDefaultScreenDevice()
      .getDefaultConfiguration()
      .createCompatibleImage(icon.getIconWidth(), icon.getIconHeight(), Transparency.TRANSLUCENT);
    final Graphics2D g = image.createGraphics();
    icon.paintIcon(new JPanel(), g, 0, 0);
    g.dispose();

    final BufferedImage img = UIUtil.createImage(w, h, Transparency.TRANSLUCENT);
    final int offX = icon.getIconWidth() > maxWidth ? (icon.getIconWidth() - maxWidth) / 2 : 0;
    final int offY = icon.getIconHeight() > maxHeight ? (icon.getIconHeight() - maxHeight) / 2 : 0;
    for (int col = 0; col < w; col++) {
      for (int row = 0; row < h; row++) {
        img.setRGB(col, row, image.getRGB(col + offX, row + offY));
      }
    }

    return new ImageIcon(img);
  }

  public static Icon cropIcon(@NotNull Icon icon, Rectangle area) {
    if (!new Rectangle(icon.getIconWidth(), icon.getIconHeight()).contains(area)) {
      return icon;
    }
    return new CropIcon(icon, area);
  }

  @NotNull
  public static Icon flip(@NotNull final Icon icon, final boolean horizontal) {
    return new Icon() {
      @Override
      public void paintIcon(Component c, Graphics g, int x, int y) {
        Graphics2D g2d = (Graphics2D)g.create();
        try {
          AffineTransform transform =
            AffineTransform.getTranslateInstance(horizontal ? x + getIconWidth() : x, horizontal ? y : y + getIconHeight());
          transform.concatenate(AffineTransform.getScaleInstance(horizontal ? -1 : 1, horizontal ? 1 : -1));
          transform.preConcatenate(g2d.getTransform());
          g2d.setTransform(transform);
          icon.paintIcon(c, g2d, 0, 0);
        }
        finally {
          g2d.dispose();
        }
      }

      @Override
      public int getIconWidth() {
        return icon.getIconWidth();
      }

      @Override
      public int getIconHeight() {
        return icon.getIconHeight();
      }
    };
  }

  private static final NullableFunction<FileIconKey, Icon> ICON_NULLABLE_FUNCTION = new NullableFunction<FileIconKey, Icon>() {
    @Override
    public Icon fun(final FileIconKey key) {
      final VirtualFile file = key.getFile();
      final int flags = key.getFlags();
      final Project project = key.getProject();

      if (!file.isValid() || project != null && (project.isDisposed() || !wasEverInitialized(project))) return null;

      final Icon providersIcon = getProvidersIcon(file, flags, project);
      Icon icon = providersIcon == null ? VirtualFilePresentation.getIconImpl(file) : providersIcon;

      final boolean dumb = project != null && DumbService.getInstance(project).isDumb();
      for (FileIconPatcher patcher : getPatchers()) {
        if (dumb && !DumbService.isDumbAware(patcher)) {
          continue;
        }

        icon = patcher.patchIcon(icon, file, flags, project);
      }

      if ((flags & Iconable.ICON_FLAG_READ_STATUS) != 0 &&
          (!file.isWritable() || !WritingAccessProvider.isPotentiallyWritable(file, project))) {
        icon = new LayeredIcon(icon, PlatformIcons.LOCKED_ICON);
      }
      if (file.is(VFileProperty.SYMLINK)) {
        icon = new LayeredIcon(icon, PlatformIcons.SYMLINK_ICON);
      }

      Iconable.LastComputedIcon.put(file, icon, flags);

      return icon;
    }
  };

  public static Icon getIcon(@NotNull final VirtualFile file, @Iconable.IconFlags final int flags, @Nullable final Project project) {
    Icon lastIcon = Iconable.LastComputedIcon.get(file, flags);

    final Icon base = lastIcon != null ? lastIcon : VirtualFilePresentation.getIconImpl(file);
    return IconDeferrer.getInstance().defer(base, new FileIconKey(file, project, flags), ICON_NULLABLE_FUNCTION);
  }

  @Nullable
  private static Icon getProvidersIcon(@NotNull VirtualFile file, @Iconable.IconFlags int flags, Project project) {
    for (FileIconProvider provider : getProviders()) {
      final Icon icon = provider.getIcon(file, flags, project);
      if (icon != null) return icon;
    }
    return null;
  }

  @NotNull
  public static Icon getEmptyIcon(boolean showVisibility) {
    RowIcon baseIcon = new RowIcon(2);
    baseIcon.setIcon(createEmptyIconLike(PlatformIcons.CLASS_ICON_PATH), 0);
    if (showVisibility) {
      baseIcon.setIcon(createEmptyIconLike(PlatformIcons.PUBLIC_ICON_PATH), 1);
    }
    return baseIcon;
  }

  @NotNull
  private static Icon createEmptyIconLike(@NotNull String baseIconPath) {
    Icon baseIcon = IconLoader.findIcon(baseIconPath);
    if (baseIcon == null) {
      return EmptyIcon.ICON_16;
    }
    return new EmptyIcon(baseIcon.getIconWidth(), baseIcon.getIconHeight());
  }

  private static class FileIconProviderHolder {
    private static final FileIconProvider[] myProviders = Extensions.getExtensions(FileIconProvider.EP_NAME);
  }

  private static FileIconProvider[] getProviders() {
    return FileIconProviderHolder.myProviders;
  }

  private static class FileIconPatcherHolder {
    private static final FileIconPatcher[] ourPatchers = Extensions.getExtensions(FileIconPatcher.EP_NAME);
  }

  private static FileIconPatcher[] getPatchers() {
    return FileIconPatcherHolder.ourPatchers;
  }

  public static Image toImage(@NotNull Icon icon) {
    if (icon instanceof ImageIcon) {
      return ((ImageIcon)icon).getImage();
    }
    else {
      final int w = icon.getIconWidth();
      final int h = icon.getIconHeight();
      final BufferedImage image = GraphicsEnvironment.getLocalGraphicsEnvironment()
        .getDefaultScreenDevice().getDefaultConfiguration().createCompatibleImage(w, h, Transparency.TRANSLUCENT);
      final Graphics2D g = image.createGraphics();
      icon.paintIcon(null, g, 0, 0);
      g.dispose();
      return image;
    }
  }

  public static Icon getAddIcon() {
    return getToolbarDecoratorIcon("add.png");
  }

  public static Icon getRemoveIcon() {
    return getToolbarDecoratorIcon("remove.png");
  }

  public static Icon getMoveUpIcon() {
    return getToolbarDecoratorIcon("moveUp.png");
  }

  public static Icon getMoveDownIcon() {
    return getToolbarDecoratorIcon("moveDown.png");
  }

  public static Icon getEditIcon() {
    return getToolbarDecoratorIcon("edit.png");
  }

  public static Icon getAddClassIcon() {
    return getToolbarDecoratorIcon("addClass.png");
  }

  public static Icon getAddPatternIcon() {
    return getToolbarDecoratorIcon("addPattern.png");
  }

  public static Icon getAddJiraPatternIcon() {
    return getToolbarDecoratorIcon("addJira.png");
  }

  public static Icon getAddYouTrackPatternIcon() {
    return getToolbarDecoratorIcon("addYouTrack.png");
  }

  public static Icon getAddBlankLineIcon() {
    return getToolbarDecoratorIcon("addBlankLine.png");
  }

  public static Icon getAddPackageIcon() {
    return getToolbarDecoratorIcon("addPackage.png");
  }

  public static Icon getAddLinkIcon() {
    return getToolbarDecoratorIcon("addLink.png");
  }

  public static Icon getAddFolderIcon() {
    return getToolbarDecoratorIcon("addFolder.png");
  }

  public static Icon getAnalyzeIcon() {
    return getToolbarDecoratorIcon("analyze.png");
  }

  public static void paintInCenterOf(@NotNull Component c, Graphics g, Icon icon) {
    final int x = (c.getWidth() - icon.getIconWidth()) / 2;
    final int y = (c.getHeight() - icon.getIconHeight()) / 2;
    icon.paintIcon(c, g, x, y);
  }

  public static Icon getToolbarDecoratorIcon(String name) {
    return IconLoader.getIcon(getToolbarDecoratorIconsFolder() + name);
  }

  private static String getToolbarDecoratorIconsFolder() {
    return "/toolbarDecorator/" + (SystemInfo.isMac ? "mac/" : "");
  }

  /**
   * Result icons look like original but have equal (maximum) size
   */
  @NotNull
  public static Icon[] getEqualSizedIcons(@NotNull Icon... icons) {
    Icon[] result = new Icon[icons.length];
    int width = 0;
    int height = 0;
    for (Icon icon : icons) {
      width = Math.max(width, icon.getIconWidth());
      height = Math.max(height, icon.getIconHeight());
    }
    for (int i = 0; i < icons.length; i++) {
      result[i] = new IconSizeWrapper(icons[i], width, height);
    }
    return result;
  }

  public static Icon toSize(@NotNull Icon icon, int width, int height) {
    return new IconSizeWrapper(icon, width, height);
  }

  private static class IconSizeWrapper implements Icon {
    private final Icon myIcon;
    private final int myWidth;
    private final int myHeight;

    private IconSizeWrapper(@NotNull Icon icon, int width, int height) {
      myIcon = icon;
      myWidth = width;
      myHeight = height;
    }

    @Override
    public void paintIcon(Component c, Graphics g, int x, int y) {
      x += (myWidth - myIcon.getIconWidth()) / 2;
      y += (myHeight - myIcon.getIconHeight()) / 2;
      myIcon.paintIcon(c, g, x, y);
    }

    @Override
    public int getIconWidth() {
      return myWidth;
    }

    @Override
    public int getIconHeight() {
      return myHeight;
    }
  }

  private static class CropIcon implements Icon {
    private final Icon mySrc;
    private final Rectangle myCrop;

    private CropIcon(@NotNull Icon src, Rectangle crop) {
      mySrc = src;
      myCrop = crop;
    }

    @Override
    public void paintIcon(Component c, Graphics g, int x, int y) {
      mySrc.paintIcon(c, g, x - myCrop.x, y - myCrop.y);
    }

    @Override
    public int getIconWidth() {
      return myCrop.width;
    }

    @Override
    public int getIconHeight() {
      return myCrop.height;
    }
  }

  public static Icon scale(@NotNull final Icon source, double _scale) {
    final int hiDPIscale;
    if (source instanceof ImageIcon) {
      Image image = ((ImageIcon)source).getImage();
      hiDPIscale = RetinaImage.isAppleHiDPIScaledImage(image) || image instanceof JBHiDPIScaledImage ? 2 : 1;
    } else {
      hiDPIscale = 1;
    }
    final double scale = Math.min(32, Math.max(.1, _scale));
    return new Icon() {
      @Override
      public void paintIcon(Component c, Graphics g, int x, int y) {
        Graphics2D g2d = (Graphics2D)g.create();
        try {
          g2d.translate(x, y);
          AffineTransform transform = AffineTransform.getScaleInstance(scale, scale);
          transform.preConcatenate(g2d.getTransform());
          g2d.setTransform(transform);
          g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BICUBIC);
          source.paintIcon(c, g2d, 0, 0);
        } finally {
          g2d.dispose();
        }
      }

      @Override
      public int getIconWidth() {
        return (int)(source.getIconWidth() * scale) / hiDPIscale;
      }

      @Override
      public int getIconHeight() {
        return (int)(source.getIconHeight() * scale) / hiDPIscale;
      }
    };

  }

  @NotNull
  public static Icon colorize(@NotNull final Icon source, @NotNull Color color) {
    return colorize(source, color, false);
  }

  @NotNull
  public static Icon colorize(@NotNull final Icon source, @NotNull Color color, boolean keepGray) {
    float[] base = Color.RGBtoHSB(color.getRed(), color.getGreen(), color.getBlue(), null);

    final BufferedImage image = UIUtil.createImage(source.getIconWidth(), source.getIconHeight(), Transparency.TRANSLUCENT);
    final Graphics2D g = image.createGraphics();
    source.paintIcon(null, g, 0, 0);
    g.dispose();

    final BufferedImage img = UIUtil.createImage(source.getIconWidth(), source.getIconHeight(), Transparency.TRANSLUCENT);
    int[] rgba = new int[4];
    float[] hsb = new float[3];
    for (int y = 0; y < image.getRaster().getHeight(); y++) {
      for (int x = 0; x < image.getRaster().getWidth(); x++) {
        image.getRaster().getPixel(x, y, rgba);
        if (rgba[3] != 0) {
          Color.RGBtoHSB(rgba[0], rgba[1], rgba[2], hsb);
          int rgb = Color.HSBtoRGB(base[0], base[1] * (keepGray ? hsb[1] : 1f), base[2] * hsb[2]);
          img.getRaster().setPixel(x, y, new int[]{rgb >> 16 & 0xff, rgb >> 8 & 0xff, rgb & 0xff, rgba[3]});
        }
      }
    }

    return createImageIcon(img);
  }

  @NotNull
  public static JBImageIcon createImageIcon(@NotNull final BufferedImage img) {
    return new JBImageIcon(img) {
      @Override
      public int getIconWidth() {
        return getImage() instanceof JBHiDPIScaledImage ? super.getIconWidth() / 2 : super.getIconWidth();
      }

      @Override
      public int getIconHeight() {
        return getImage() instanceof JBHiDPIScaledImage ? super.getIconHeight() / 2: super.getIconHeight();
      }
    };
  }

  @NotNull
  public static Icon textToIcon(final String text, final Component component, final float fontSize) {
    final Font font = JBFont.create(JBUI.Fonts.label().deriveFont(fontSize));
    FontMetrics metrics = component.getFontMetrics(font);
    final int width = metrics.stringWidth(text) + JBUI.scale(4);
    final int height = metrics.getHeight();

    return new Icon() {
      @Override
      public void paintIcon(Component c, Graphics g, int x, int y) {
        GraphicsUtil.setupAntialiasing(g);
        g.setFont(font);
        UIUtil.drawStringWithHighlighting(g, text, x + JBUI.scale(2), y + height - JBUI.scale(1), JBColor.foreground(), JBColor.background());
      }

      @Override
      public int getIconWidth() {
        return width;
      }

      @Override
      public int getIconHeight() {
        return height;
      }
    };
  }
}


File: platform/lang-api/src/com/intellij/execution/runners/ExecutionUtil.java
/*
 * Copyright 2000-2009 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.intellij.execution.runners;

import com.intellij.execution.*;
import com.intellij.execution.configurations.RunProfile;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.process.ProcessNotCreatedException;
import com.intellij.execution.ui.RunContentDescriptor;
import com.intellij.ide.DataManager;
import com.intellij.ide.util.PropertiesComponent;
import com.intellij.notification.Notification;
import com.intellij.notification.NotificationGroup;
import com.intellij.notification.NotificationListener;
import com.intellij.notification.NotificationType;
import com.intellij.openapi.actionSystem.LangDataKeys;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.MessageType;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.wm.ToolWindowManager;
import com.intellij.ui.content.Content;
import com.intellij.util.ui.UIUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import javax.swing.event.HyperlinkEvent;
import javax.swing.event.HyperlinkListener;

public class ExecutionUtil {
  private static final Logger LOG = Logger.getInstance("com.intellij.execution.runners.ExecutionUtil");

  private static final NotificationGroup ourNotificationGroup = NotificationGroup.logOnlyGroup("Execution");

  private ExecutionUtil() {
  }

  public static void handleExecutionError(@NotNull Project project,
                                          @NotNull String toolWindowId,
                                          @NotNull RunProfile runProfile,
                                          @NotNull ExecutionException e) {
    handleExecutionError(project, toolWindowId, runProfile.getName(), e);
  }

  public static void handleExecutionError(@NotNull ExecutionEnvironment environment, @NotNull ExecutionException e) {
    handleExecutionError(environment.getProject(), environment.getExecutor().getToolWindowId(), environment.getRunProfile().getName(), e);
  }

  public static void handleExecutionError(@NotNull final Project project,
                                          @NotNull final String toolWindowId,
                                          @NotNull String taskName,
                                          @NotNull ExecutionException e) {
    if (e instanceof RunCanceledByUserException) {
      return;
    }

    LOG.debug(e);

    String description = e.getMessage();
    if (description == null) {
      LOG.warn("Execution error without description", e);
      description = "Unknown error";
    }

    HyperlinkListener listener = null;
    if ((description.contains("87") || description.contains("111") || description.contains("206")) &&
        e instanceof ProcessNotCreatedException &&
        !PropertiesComponent.getInstance(project).isTrueValue("dynamic.classpath")) {
      final String commandLineString = ((ProcessNotCreatedException)e).getCommandLine().getCommandLineString();
      if (commandLineString.length() > 1024 * 32) {
        description = "Command line is too long. In order to reduce its length classpath file can be used.<br>" +
                      "Would you like to enable classpath file mode for all run configurations of your project?<br>" +
                      "<a href=\"\">Enable</a>";

        listener = new HyperlinkListener() {
          @Override
          public void hyperlinkUpdate(HyperlinkEvent event) {
            PropertiesComponent.getInstance(project).setValue("dynamic.classpath", "true");
          }
        };
      }
    }
    final String title = ExecutionBundle.message("error.running.configuration.message", taskName);
    final String fullMessage = title + ":<br>" + description;

    if (ApplicationManager.getApplication().isUnitTestMode()) {
      LOG.error(fullMessage, e);
    }

    if (listener == null && e instanceof HyperlinkListener) {
      listener = (HyperlinkListener)e;
    }

    final HyperlinkListener finalListener = listener;
    final String finalDescription = description;
    UIUtil.invokeLaterIfNeeded(new Runnable() {
      @Override
      public void run() {
        if (project.isDisposed()) {
          return;
        }

        ToolWindowManager toolWindowManager = ToolWindowManager.getInstance(project);
        if (toolWindowManager.canShowNotification(toolWindowId)) {
          //noinspection SSBasedInspection
          toolWindowManager.notifyByBalloon(toolWindowId, MessageType.ERROR, fullMessage, null, finalListener);
        }
        else {
          Messages.showErrorDialog(project, UIUtil.toHtml(fullMessage), "");
        }
        NotificationListener notificationListener = finalListener == null ? null : new NotificationListener() {
          @Override
          public void hyperlinkUpdate(@NotNull Notification notification, @NotNull HyperlinkEvent event) {
            finalListener.hyperlinkUpdate(event);
          }
        };
        ourNotificationGroup.createNotification(title, finalDescription, NotificationType.ERROR, notificationListener).notify(project);
      }
    });
  }

  public static void restartIfActive(@NotNull RunContentDescriptor descriptor) {
    ProcessHandler processHandler = descriptor.getProcessHandler();
    if (processHandler != null
        && processHandler.isStartNotified()
        && !processHandler.isProcessTerminating()
        && !processHandler.isProcessTerminated()) {
      restart(descriptor);
    }
  }

  public static void restart(@NotNull RunContentDescriptor descriptor) {
    restart(descriptor.getComponent());
  }

  public static void restart(@NotNull Content content) {
    restart(content.getComponent());
  }

  private static void restart(@Nullable JComponent component) {
    if (component != null) {
      ExecutionEnvironment environment = LangDataKeys.EXECUTION_ENVIRONMENT.getData(DataManager.getInstance().getDataContext(component));
      if (environment != null) {
        restart(environment);
      }
    }
  }

  public static void restart(@NotNull ExecutionEnvironment environment) {
    if (!ExecutorRegistry.getInstance().isStarting(environment)) {
      ExecutionManager.getInstance(environment.getProject()).restartRunProfile(environment);
    }
  }

  public static void runConfiguration(@NotNull RunnerAndConfigurationSettings configuration, @NotNull Executor executor) {
    ExecutionEnvironmentBuilder builder = createEnvironment(executor, configuration);
    if (builder != null) {
      ExecutionManager.getInstance(configuration.getConfiguration().getProject()).restartRunProfile(builder
                                                                                                      .activeTarget()
                                                                                                      .build());
    }
  }

  @Nullable
  public static ExecutionEnvironmentBuilder createEnvironment(@NotNull Executor executor, @NotNull RunnerAndConfigurationSettings settings) {
    try {
      return ExecutionEnvironmentBuilder.create(executor, settings);
    }
    catch (ExecutionException e) {
      handleExecutionError(settings.getConfiguration().getProject(), executor.getToolWindowId(), settings.getConfiguration().getName(), e);
      return null;
    }
  }
}


File: platform/lang-impl/src/com/intellij/execution/ExecutorRegistryImpl.java
/*
 * Copyright 2000-2014 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.execution;

import com.intellij.execution.actions.RunContextAction;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.execution.runners.ExecutionEnvironmentBuilder;
import com.intellij.execution.runners.ProgramRunner;
import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.extensions.Extensions;
import com.intellij.openapi.project.*;
import com.intellij.openapi.util.Trinity;
import com.intellij.util.containers.HashMap;
import com.intellij.util.containers.HashSet;
import com.intellij.util.messages.MessageBusConnection;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;

public class ExecutorRegistryImpl extends ExecutorRegistry {
  private static final Logger LOG = Logger.getInstance(ExecutorRegistryImpl.class);

  @NonNls public static final String RUNNERS_GROUP = "RunnerActions";
  @NonNls public static final String RUN_CONTEXT_GROUP = "RunContextGroup";

  private List<Executor> myExecutors = new ArrayList<Executor>();
  private ActionManager myActionManager;
  private final Map<String, Executor> myId2Executor = new HashMap<String, Executor>();
  private final Set<String> myContextActionIdSet = new HashSet<String>();
  private final Map<String, AnAction> myId2Action = new HashMap<String, AnAction>();
  private final Map<String, AnAction> myContextActionId2Action = new HashMap<String, AnAction>();

  // [Project, ExecutorId, RunnerId]
  private final Set<Trinity<Project, String, String>> myInProgress = Collections.synchronizedSet(new java.util.HashSet<Trinity<Project, String, String>>());

  public ExecutorRegistryImpl(ActionManager actionManager) {
    myActionManager = actionManager;
  }

  synchronized void initExecutor(@NotNull final Executor executor) {
    if (myId2Executor.get(executor.getId()) != null) {
      LOG.error("Executor with id: \"" + executor.getId() + "\" was already registered!");
    }

    if (myContextActionIdSet.contains(executor.getContextActionId())) {
      LOG.error("Executor with context action id: \"" + executor.getContextActionId() + "\" was already registered!");
    }

    myExecutors.add(executor);
    myId2Executor.put(executor.getId(), executor);
    myContextActionIdSet.add(executor.getContextActionId());

    registerAction(executor.getId(), new ExecutorAction(executor), RUNNERS_GROUP, myId2Action);
    registerAction(executor.getContextActionId(), new RunContextAction(executor), RUN_CONTEXT_GROUP, myContextActionId2Action);
  }

  private void registerAction(@NotNull final String actionId, @NotNull final AnAction anAction, @NotNull final String groupId, @NotNull final Map<String, AnAction> map) {
    AnAction action = myActionManager.getAction(actionId);
    if (action == null) {
      myActionManager.registerAction(actionId, anAction);
      map.put(actionId, anAction);
      action = anAction;
    }

    ((DefaultActionGroup)myActionManager.getAction(groupId)).add(action);
  }

  synchronized void deinitExecutor(@NotNull final Executor executor) {
    myExecutors.remove(executor);
    myId2Executor.remove(executor.getId());
    myContextActionIdSet.remove(executor.getContextActionId());

    unregisterAction(executor.getId(), RUNNERS_GROUP, myId2Action);
    unregisterAction(executor.getContextActionId(), RUN_CONTEXT_GROUP, myContextActionId2Action);
  }

  private void unregisterAction(@NotNull final String actionId, @NotNull final String groupId, @NotNull final Map<String, AnAction> map) {
    final DefaultActionGroup group = (DefaultActionGroup)myActionManager.getAction(groupId);
    if (group != null) {
      group.remove(myActionManager.getAction(actionId));
      final AnAction action = map.get(actionId);
      if (action != null) {
        myActionManager.unregisterAction(actionId);
        map.remove(actionId);
      }
    }
  }

  @Override
  @NotNull
  public synchronized Executor[] getRegisteredExecutors() {
    return myExecutors.toArray(new Executor[myExecutors.size()]);
  }

  @Override
  public Executor getExecutorById(final String executorId) {
    return myId2Executor.get(executorId);
  }

  @Override
  @NonNls
  @NotNull
  public String getComponentName() {
    return "ExecutorRegistyImpl";
  }

  @Override
  public void initComponent() {
    ProjectManager.getInstance().addProjectManagerListener(new ProjectManagerAdapter() {
      @Override
      public void projectOpened(final Project project) {
        final MessageBusConnection connect = project.getMessageBus().connect(project);
        connect.subscribe(ExecutionManager.EXECUTION_TOPIC, new ExecutionAdapter(){
          @Override
          public void processStartScheduled(String executorId, ExecutionEnvironment environment) {
            myInProgress.add(createExecutionId(executorId, environment));
          }

          @Override
          public void processNotStarted(String executorId, @NotNull ExecutionEnvironment environment) {
            myInProgress.remove(createExecutionId(executorId, environment));
          }

          @Override
          public void processStarted(String executorId, @NotNull ExecutionEnvironment environment, @NotNull ProcessHandler handler) {
            myInProgress.remove(createExecutionId(executorId, environment));
          }
        });
      }

      @Override
      public void projectClosed(final Project project) {
        // perform cleanup
        synchronized (myInProgress) {
          for (Iterator<Trinity<Project, String, String>> it = myInProgress.iterator(); it.hasNext(); ) {
            final Trinity<Project, String, String> trinity = it.next();
            if (project.equals(trinity.first)) {
              it.remove();
            }
          }
        }
      }
    });


    final Executor[] executors = Extensions.getExtensions(Executor.EXECUTOR_EXTENSION_NAME);
    for (Executor executor : executors) {
      initExecutor(executor);
    }
  }

  @NotNull
  private static Trinity<Project, String, String> createExecutionId(String executorId, @NotNull ExecutionEnvironment environment) {
    return Trinity.create(environment.getProject(), executorId, environment.getRunner().getRunnerId());
  }

  @Override
  public boolean isStarting(Project project, final String executorId, final String runnerId) {
    return myInProgress.contains(Trinity.create(project, executorId, runnerId));
  }

  @Override
  public boolean isStarting(@NotNull ExecutionEnvironment environment) {
    return isStarting(environment.getProject(), environment.getExecutor().getId(), environment.getRunner().getRunnerId());
  }

  @Override
  public synchronized void disposeComponent() {
    if (!myExecutors.isEmpty()) {
      for (Executor executor : new ArrayList<Executor>(myExecutors)) {
        deinitExecutor(executor);
      }
    }
    myExecutors = null;
    myActionManager = null;
  }

  private class ExecutorAction extends AnAction implements DumbAware {
    private final Executor myExecutor;

    private ExecutorAction(@NotNull final Executor executor) {
      super(executor.getStartActionText(), executor.getDescription(), executor.getIcon());
      myExecutor = executor;
    }

    @Override
    public void update(final AnActionEvent e) {
      final Presentation presentation = e.getPresentation();
      final Project project = e.getProject();

      if (project == null || !project.isInitialized() || project.isDisposed() || DumbService.getInstance(project).isDumb()) {
        presentation.setEnabled(false);
        return;
      }

      final RunnerAndConfigurationSettings selectedConfiguration = getConfiguration(project);
      boolean enabled = false;
      String text;
      final String textWithMnemonic = getTemplatePresentation().getTextWithMnemonic();
      if (selectedConfiguration != null) {
        final ProgramRunner runner = RunnerRegistry.getInstance().getRunner(myExecutor.getId(), selectedConfiguration.getConfiguration());

        ExecutionTarget target = ExecutionTargetManager.getActiveTarget(project);
        enabled = ExecutionTargetManager.canRun(selectedConfiguration, target)
                  && runner != null && !isStarting(project, myExecutor.getId(), runner.getRunnerId());

        if (enabled) {
          presentation.setDescription(myExecutor.getDescription());
        }
        text = myExecutor.getStartActionText(selectedConfiguration.getName());
      }
      else {
        text = textWithMnemonic;
      }

      presentation.setEnabled(enabled);
      presentation.setText(text);
    }

    @Nullable
    private RunnerAndConfigurationSettings getConfiguration(@NotNull final Project project) {
      return RunManagerEx.getInstanceEx(project).getSelectedConfiguration();
    }

    @Override
    public void actionPerformed(final AnActionEvent e) {
      final Project project = e.getProject();
      if (project == null || project.isDisposed()) {
        return;
      }

      RunnerAndConfigurationSettings configuration = getConfiguration(project);
      ExecutionEnvironmentBuilder builder = configuration == null ? null : ExecutionEnvironmentBuilder.createOrNull(myExecutor, configuration);
      if (builder == null) {
        return;
      }
      ExecutionManager.getInstance(project).restartRunProfile(builder.activeTarget().dataContext(e.getDataContext()).build());
    }
  }
}


File: platform/lang-impl/src/com/intellij/execution/actions/RunConfigurationsComboBoxAction.java
/*
 * Copyright 2000-2014 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.intellij.execution.actions;

import com.intellij.execution.*;
import com.intellij.execution.configurations.ConfigurationType;
import com.intellij.icons.AllIcons;
import com.intellij.ide.DataManager;
import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.actionSystem.ex.ComboBoxAction;
import com.intellij.openapi.project.DumbAware;
import com.intellij.openapi.project.DumbAwareAction;
import com.intellij.openapi.project.IndexNotReadyException;
import com.intellij.openapi.project.Project;
import com.intellij.ui.IdeBorderFactory;
import com.intellij.ui.SizedIcon;
import com.intellij.ui.components.panels.NonOpaquePanel;
import com.intellij.util.ui.EmptyIcon;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

public class RunConfigurationsComboBoxAction extends ComboBoxAction implements DumbAware {

  public static final Icon CHECKED_ICON = new SizedIcon(AllIcons.Actions.Checked, 16, 16);
  public static final Icon CHECKED_SELECTED_ICON = new SizedIcon(AllIcons.Actions.Checked_selected, 16, 16);
  public static final Icon EMPTY_ICON = EmptyIcon.ICON_16;

  @Override
  public void update(AnActionEvent e) {
    Presentation presentation = e.getPresentation();
    Project project = e.getData(CommonDataKeys.PROJECT);
    if (ActionPlaces.isMainMenuOrActionSearch(e.getPlace())) {
      presentation.setDescription(ExecutionBundle.message("choose.run.configuration.action.description"));
    }
    try {
      if (project == null || project.isDisposed() || !project.isInitialized()) {
        updatePresentation(null, null, null, presentation);
        presentation.setEnabled(false);
      }
      else {
        updatePresentation(ExecutionTargetManager.getActiveTarget(project),
                           RunManagerEx.getInstanceEx(project).getSelectedConfiguration(),
                           project,
                           presentation);
        presentation.setEnabled(true);
      }
    }
    catch (IndexNotReadyException e1) {
      presentation.setEnabled(false);
    }
  }

  private static void updatePresentation(@Nullable ExecutionTarget target,
                                         @Nullable RunnerAndConfigurationSettings settings,
                                         @Nullable Project project,
                                         @NotNull Presentation presentation) {
    if (project != null && target != null && settings != null) {
      String name = settings.getName();
      if (target != DefaultExecutionTarget.INSTANCE) {
        name += " | " + target.getDisplayName();
      } else {
        if (!settings.canRunOn(target)) {
          name += " | Nothing to run on";
        }
      }
      presentation.setText(name, false);
      setConfigurationIcon(presentation, settings, project);
    }
    else {
      presentation.setText(""); // IDEA-21657
      presentation.setIcon(null);
    }
  }

  private static void setConfigurationIcon(final Presentation presentation,
                                           final RunnerAndConfigurationSettings settings,
                                           final Project project) {
    try {
      presentation.setIcon(RunManagerEx.getInstanceEx(project).getConfigurationIcon(settings));
    }
    catch (IndexNotReadyException ignored) {
    }
  }

  @Override
  protected boolean shouldShowDisabledActions() {
    return true;
  }

  @Override
  public JComponent createCustomComponent(final Presentation presentation) {
    ComboBoxButton button = createComboBoxButton(presentation);
    button.setBorder(BorderFactory.createEmptyBorder(0, 2, 0, 2));
    NonOpaquePanel panel = new NonOpaquePanel(new BorderLayout());
    panel.setBorder(IdeBorderFactory.createEmptyBorder(0, 0, 0, 2));
    panel.add(button);
    return panel;
  }


  @Override
  @NotNull
  protected DefaultActionGroup createPopupActionGroup(final JComponent button) {
    final DefaultActionGroup allActionsGroup = new DefaultActionGroup();
    final Project project = CommonDataKeys.PROJECT.getData(DataManager.getInstance().getDataContext(button));
    if (project != null) {
      final RunManagerEx runManager = RunManagerEx.getInstanceEx(project);

      allActionsGroup.add(ActionManager.getInstance().getAction(IdeActions.ACTION_EDIT_RUN_CONFIGURATIONS));
      allActionsGroup.add(new SaveTemporaryAction());
      allActionsGroup.addSeparator();

      RunnerAndConfigurationSettings selected = RunManager.getInstance(project).getSelectedConfiguration();
      if (selected != null) {
        ExecutionTarget activeTarget = ExecutionTargetManager.getActiveTarget(project);
        for (ExecutionTarget eachTarget : ExecutionTargetManager.getTargetsToChooseFor(project, selected)) {
          allActionsGroup.add(new SelectTargetAction(project, eachTarget, eachTarget.equals(activeTarget)));
        }
        allActionsGroup.addSeparator();
      }

      final ConfigurationType[] types = runManager.getConfigurationFactories();
      for (ConfigurationType type : types) {
        final DefaultActionGroup actionGroup = new DefaultActionGroup();
        Map<String,List<RunnerAndConfigurationSettings>> structure = runManager.getStructure(type);
        for (Map.Entry<String, List<RunnerAndConfigurationSettings>> entry : structure.entrySet()) {
          DefaultActionGroup group = entry.getKey() != null ? new DefaultActionGroup(entry.getKey(), true) : actionGroup;
          group.getTemplatePresentation().setIcon(AllIcons.Nodes.Folder);
          for (RunnerAndConfigurationSettings settings : entry.getValue()) {
            group.add(new SelectConfigAction(settings, project));
          }
          if (group != actionGroup) {
            actionGroup.add(group);
          }
        }

        allActionsGroup.add(actionGroup);
        allActionsGroup.addSeparator();
      }
    }
    return allActionsGroup;
  }

  private static class SaveTemporaryAction extends DumbAwareAction {

    public SaveTemporaryAction() {
      Presentation presentation = getTemplatePresentation();
      presentation.setIcon(AllIcons.Actions.Menu_saveall);
    }

    @Override
    public void actionPerformed(final AnActionEvent e) {
      final Project project = e.getData(CommonDataKeys.PROJECT);
      if (project != null) {
        RunnerAndConfigurationSettings settings = chooseTempSettings(project);
        if (settings != null) {
          final RunManager runManager = RunManager.getInstance(project);
          runManager.makeStable(settings);
        }
      }
    }

    @Override
    public void update(final AnActionEvent e) {
      final Presentation presentation = e.getPresentation();
      final Project project = e.getData(CommonDataKeys.PROJECT);
      if (project == null) {
        disable(presentation);
        return;
      }
      RunnerAndConfigurationSettings settings = chooseTempSettings(project);
      if (settings == null) {
        disable(presentation);
      }
      else {
        presentation.setText(ExecutionBundle.message("save.temporary.run.configuration.action.name", settings.getName()));
        presentation.setDescription(presentation.getText());
        presentation.setVisible(true);
        presentation.setEnabled(true);
      }
    }

    private static void disable(final Presentation presentation) {
      presentation.setEnabled(false);
      presentation.setVisible(false);
    }

    @Nullable
    private static RunnerAndConfigurationSettings chooseTempSettings(@NotNull Project project) {
      RunnerAndConfigurationSettings selectedConfiguration = RunManager.getInstance(project).getSelectedConfiguration();
      if (selectedConfiguration != null && selectedConfiguration.isTemporary()) {
        return selectedConfiguration;
      }
      Iterator<RunnerAndConfigurationSettings> iterator = RunManager.getInstance(project).getTempConfigurationsList().iterator();
      return iterator.hasNext() ? iterator.next() : null;
    }
  }

  private static class SelectTargetAction extends AnAction {
    private final Project myProject;
    private final ExecutionTarget myTarget;

    public SelectTargetAction(final Project project, final ExecutionTarget target, boolean selected) {
      myProject = project;
      myTarget = target;

      String name = target.getDisplayName();
      Presentation presentation = getTemplatePresentation();
      presentation.setText(name, false);
      presentation.setDescription("Select " + name);

      presentation.setIcon(selected ? CHECKED_ICON : EMPTY_ICON);
      presentation.setSelectedIcon(selected ? CHECKED_SELECTED_ICON : EMPTY_ICON);
    }

    @Override
    public void actionPerformed(AnActionEvent e) {
      ExecutionTargetManager.setActiveTarget(myProject, myTarget);
      updatePresentation(ExecutionTargetManager.getActiveTarget(myProject),
                         RunManagerEx.getInstanceEx(myProject).getSelectedConfiguration(),
                         myProject,
                         e.getPresentation());
    }
  }

  private static class SelectConfigAction extends DumbAwareAction {
    private final RunnerAndConfigurationSettings myConfiguration;
    private final Project myProject;

    public SelectConfigAction(final RunnerAndConfigurationSettings configuration, final Project project) {
      myConfiguration = configuration;
      myProject = project;
      String name = configuration.getName();
      if (name == null || name.length() == 0) {
        name = " ";
      }
      final Presentation presentation = getTemplatePresentation();
      presentation.setText(name, false);
      final ConfigurationType type = configuration.getType();
      if (type != null) {
        presentation.setDescription("Select " + type.getConfigurationTypeDescription() + " '" + name + "'");
      }
      updateIcon(presentation);
    }

    private void updateIcon(final Presentation presentation) {
      setConfigurationIcon(presentation, myConfiguration, myProject);
    }

    @Override
    public void actionPerformed(final AnActionEvent e) {
      RunManager.getInstance(myProject).setSelectedConfiguration(myConfiguration);
      updatePresentation(ExecutionTargetManager.getActiveTarget(myProject), myConfiguration, myProject, e.getPresentation());
    }

    @Override
    public void update(final AnActionEvent e) {
      super.update(e);
      updateIcon(e.getPresentation());
    }
  }
}


File: platform/lang-impl/src/com/intellij/execution/actions/StopAction.java
/*
 * Copyright 2000-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.execution.actions;

import com.intellij.execution.ExecutionBundle;
import com.intellij.execution.ExecutionManager;
import com.intellij.execution.KillableProcess;
import com.intellij.execution.configurations.RunProfile;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.ui.RunContentDescriptor;
import com.intellij.icons.AllIcons;
import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.TaskInfo;
import com.intellij.openapi.project.DumbAwareAction;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.popup.JBPopup;
import com.intellij.openapi.ui.popup.JBPopupFactory;
import com.intellij.openapi.ui.popup.ListItemDescriptorAdapter;
import com.intellij.openapi.util.Condition;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.wm.IdeFrame;
import com.intellij.openapi.wm.WindowManager;
import com.intellij.openapi.wm.ex.StatusBarEx;
import com.intellij.openapi.wm.ex.WindowManagerEx;
import com.intellij.ui.components.JBList;
import com.intellij.ui.popup.list.GroupedItemsListRenderer;
import com.intellij.util.Function;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.awt.event.InputEvent;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

class StopAction extends DumbAwareAction implements AnAction.TransparentUpdate {
  @Override
  public void update(final AnActionEvent e) {
    boolean enable = false;
    Icon icon = getTemplatePresentation().getIcon();
    String description = getTemplatePresentation().getDescription();
    Presentation presentation = e.getPresentation();
    if (ActionPlaces.isMainMenuOrActionSearch(e.getPlace()) || ActionPlaces.MAIN_TOOLBAR.equals(e.getPlace())) {
      List<RunContentDescriptor> stoppableDescriptors = getActiveStoppableDescriptors(e.getDataContext());
      List<Pair<TaskInfo, ProgressIndicator>> cancellableProcesses = getCancellableProcesses(e.getProject());
      int todoSize = stoppableDescriptors.size() + cancellableProcesses.size();
      if (todoSize > 1) {
        presentation.setText(getTemplatePresentation().getText()+"...");
      }
      else if (todoSize == 1) {
        if (stoppableDescriptors.size() ==1) {
          presentation.setText(ExecutionBundle.message("stop.configuration.action.name", stoppableDescriptors.get(0).getDisplayName()));
        } else {
          TaskInfo taskInfo = cancellableProcesses.get(0).first;
          presentation.setText(taskInfo.getCancelText() + " " + taskInfo.getTitle());
        }
      } else {
        presentation.setText(getTemplatePresentation().getText());
      }
      enable = todoSize > 0;
    }
    else {
      RunContentDescriptor contentDescriptor = e.getData(LangDataKeys.RUN_CONTENT_DESCRIPTOR);
      ProcessHandler processHandler = contentDescriptor == null ? null : contentDescriptor.getProcessHandler();
      if (processHandler != null && !processHandler.isProcessTerminated()) {
        if (!processHandler.isProcessTerminating()) {
          enable = true;
        }
        else if (processHandler instanceof KillableProcess && ((KillableProcess)processHandler).canKillProcess()) {
          enable = true;
          icon = AllIcons.Debugger.KillProcess;
          description = "Kill process";
        }
      }

      RunProfile runProfile = e.getData(LangDataKeys.RUN_PROFILE);
      if (runProfile == null && contentDescriptor == null) {
        presentation.setText(getTemplatePresentation().getText());
      }
      else {
        presentation.setText(ExecutionBundle.message("stop.configuration.action.name",
                                                     runProfile == null ? contentDescriptor.getDisplayName() : runProfile.getName()));
      }
    }

    presentation.setEnabled(enable);
    presentation.setIcon(icon);
    presentation.setDescription(description);
  }

  @Override
  public void actionPerformed(final AnActionEvent e) {
    final DataContext dataContext = e.getDataContext();
    Project project = e.getProject();
    List<Pair<TaskInfo, ProgressIndicator>> cancellableProcesses = getCancellableProcesses(project);
    List<RunContentDescriptor> stoppableDescriptors = getActiveStoppableDescriptors(dataContext);
    if (ActionPlaces.isMainMenuOrActionSearch(e.getPlace()) || ActionPlaces.MAIN_TOOLBAR.equals(e.getPlace())) {
      int todoSize = cancellableProcesses.size() + stoppableDescriptors.size();
      if (todoSize == 1) {
        if (!stoppableDescriptors.isEmpty()) {
          stopProcess(stoppableDescriptors.get(0));
        } else {
          cancellableProcesses.get(0).second.cancel();
        }
        return;
      }

      Pair<List<HandlerItem>, HandlerItem>
        handlerItems = getItemsList(cancellableProcesses, stoppableDescriptors, getRecentlyStartedContentDescriptor(dataContext));
      if (handlerItems == null || handlerItems.first.isEmpty()) {
        return;
      }

      final JBList list = new JBList(handlerItems.first);
      if (handlerItems.second != null) list.setSelectedValue(handlerItems.second, true);

      list.setCellRenderer(new GroupedItemsListRenderer(new ListItemDescriptorAdapter() {
        @Nullable
        @Override
        public String getTextFor(Object value) {
          return value instanceof HandlerItem ? ((HandlerItem)value).displayName : null;
        }

        @Nullable
        @Override
        public Icon getIconFor(Object value) {
          return value instanceof HandlerItem ? ((HandlerItem)value).icon : null;
        }

        @Override
        public boolean hasSeparatorAboveOf(Object value) {
          return value instanceof HandlerItem && ((HandlerItem)value).hasSeparator;
        }
      }));

      JBPopup popup = JBPopupFactory.getInstance().createListPopupBuilder(list)
        .setMovable(true)
        .setTitle(handlerItems.first.size() == 1 ? "Confirm process stop" : "Stop process")
        .setFilteringEnabled(new Function<Object, String>() {
          @Override
          public String fun(Object o) {
            return ((HandlerItem)o).displayName;
          }
        })
        .setItemChoosenCallback(new Runnable() {
          @Override
          public void run() {
            HandlerItem item = (HandlerItem)list.getSelectedValue();
            if (item != null) item.stop();
          }
        })
        .setRequestFocus(true)
        .createPopup();
      InputEvent inputEvent = e.getInputEvent();
      Component component = inputEvent != null ? inputEvent.getComponent() : null;
      if (component != null && ActionPlaces.MAIN_TOOLBAR.equals(e.getPlace())) {
        popup.showUnderneathOf(component);
      }
      else if (project == null) {
        popup.showInBestPositionFor(dataContext);
      }
      else {
        popup.showCenteredInCurrentWindow(project);
      }
    }
    else {
      stopProcess(getRecentlyStartedContentDescriptor(dataContext));
    }
  }

  @NotNull
  private static List<Pair<TaskInfo, ProgressIndicator>> getCancellableProcesses(@Nullable Project project) {
    IdeFrame frame = ((WindowManagerEx)WindowManager.getInstance()).findFrameFor(project);
    StatusBarEx statusBar = frame == null ? null : (StatusBarEx)frame.getStatusBar();
    if (statusBar == null) return Collections.emptyList();

    return ContainerUtil.findAll(statusBar.getBackgroundProcesses(),
                                 new Condition<Pair<TaskInfo, ProgressIndicator>>() {
                                   @Override
                                   public boolean value(Pair<TaskInfo, ProgressIndicator> pair) {
                                     return pair.first.isCancellable() && !pair.second.isCanceled();
                                   }
                                 });
  }

  @Nullable
  private static Pair<List<HandlerItem>, HandlerItem> getItemsList(List<Pair<TaskInfo, ProgressIndicator>> tasks,
                                                                   List<RunContentDescriptor> descriptors,
                                                                   RunContentDescriptor toSelect) {
    if (tasks.isEmpty() && descriptors.isEmpty()) {
      return null;
    }

    List<HandlerItem> items = new ArrayList<HandlerItem>(tasks.size() + descriptors.size());
    HandlerItem selected = null;
    for (final RunContentDescriptor descriptor : descriptors) {
      final ProcessHandler handler = descriptor.getProcessHandler();
      if (handler != null) {
        HandlerItem item = new HandlerItem(descriptor.getDisplayName(), descriptor.getIcon(), false) {
          @Override
          void stop() {
            stopProcess(descriptor);
          }
        };
        items.add(item);
        if (descriptor == toSelect) {
          selected = item;
        }
      }
    }

    boolean hasSeparator = true;
    for (final Pair<TaskInfo, ProgressIndicator> eachPair : tasks) {
      items.add(new HandlerItem(eachPair.first.getTitle(), AllIcons.Process.Step_passive, hasSeparator) {
        @Override
        void stop() {
          eachPair.second.cancel();
        }
      });
      hasSeparator = false;
    }
    return Pair.create(items, selected);
  }

  private static void stopProcess(@Nullable RunContentDescriptor descriptor) {
    ProcessHandler processHandler = descriptor != null ? descriptor.getProcessHandler() : null;
    if (processHandler == null) return;
    if (processHandler instanceof KillableProcess && processHandler.isProcessTerminating()) {
      ((KillableProcess)processHandler).killProcess();
      return;
    }

    if (processHandler.detachIsDefault()) {
      processHandler.detachProcess();
    }
    else {
      processHandler.destroyProcess();
    }
  }

  @Nullable
  static RunContentDescriptor getRecentlyStartedContentDescriptor(@NotNull DataContext dataContext) {
    final RunContentDescriptor contentDescriptor = LangDataKeys.RUN_CONTENT_DESCRIPTOR.getData(dataContext);
    if (contentDescriptor != null) {
      // toolwindow case
      return contentDescriptor;
    }
    else {
      // main menu toolbar
      final Project project = CommonDataKeys.PROJECT.getData(dataContext);
      return project == null ? null : ExecutionManager.getInstance(project).getContentManager().getSelectedContent();
    }
  }

  @NotNull
  private static List<RunContentDescriptor> getActiveStoppableDescriptors(final DataContext dataContext) {
    final Project project = CommonDataKeys.PROJECT.getData(dataContext);
    if (project == null) {
      return Collections.emptyList();
    }
    final List<RunContentDescriptor> runningProcesses = ExecutionManager.getInstance(project).getContentManager().getAllDescriptors();
    if (runningProcesses.isEmpty()) {
      return Collections.emptyList();
    }
    final List<RunContentDescriptor> activeDescriptors = new ArrayList<RunContentDescriptor>();
    for (RunContentDescriptor descriptor : runningProcesses) {
      if (canBeStopped(descriptor)) {
        activeDescriptors.add(descriptor);
      }
    }
    return activeDescriptors;
  }

  private static boolean canBeStopped(@Nullable RunContentDescriptor descriptor) {
    @Nullable ProcessHandler processHandler = descriptor != null ? descriptor.getProcessHandler() : null;
    return processHandler != null && !processHandler.isProcessTerminated()
           && (!processHandler.isProcessTerminating()
               || processHandler instanceof KillableProcess && ((KillableProcess)processHandler).canKillProcess());
  }

  private abstract static class HandlerItem {
    final String displayName;
    final Icon icon;
    final boolean hasSeparator;

    private HandlerItem(String displayName, Icon icon, boolean hasSeparator) {
      this.displayName = displayName;
      this.icon = icon;
      this.hasSeparator =  hasSeparator;
    }

    public String toString() {
      return displayName;
    }

    abstract void stop();
  }
}


File: platform/lang-impl/src/com/intellij/execution/impl/ExecutionManagerImpl.java
/*
 * Copyright 2000-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.execution.impl;

import com.intellij.CommonBundle;
import com.intellij.execution.*;
import com.intellij.execution.configuration.CompatibilityAwareRunProfile;
import com.intellij.execution.configurations.RunConfiguration;
import com.intellij.execution.configurations.RunProfile;
import com.intellij.execution.configurations.RunProfileState;
import com.intellij.execution.process.ProcessAdapter;
import com.intellij.execution.process.ProcessEvent;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.execution.runners.ExecutionEnvironmentBuilder;
import com.intellij.execution.runners.ExecutionUtil;
import com.intellij.execution.runners.ProgramRunner;
import com.intellij.execution.ui.RunContentDescriptor;
import com.intellij.execution.ui.RunContentManager;
import com.intellij.execution.ui.RunContentManagerImpl;
import com.intellij.ide.SaveAndSyncHandler;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.actionSystem.DataContext;
import com.intellij.openapi.actionSystem.impl.SimpleDataContext;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.DumbService;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.util.Condition;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.Trinity;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.ui.docking.DockManager;
import com.intellij.util.Alarm;
import com.intellij.util.SmartList;
import com.intellij.util.containers.ContainerUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.annotations.TestOnly;

import javax.swing.*;
import java.util.Collections;
import java.util.List;

public class ExecutionManagerImpl extends ExecutionManager implements Disposable {
  public static final Key<Object> EXECUTION_SESSION_ID_KEY = Key.create("EXECUTION_SESSION_ID_KEY");
  public static final Key<Boolean> EXECUTION_SKIP_RUN = Key.create("EXECUTION_SKIP_RUN");

  private static final Logger LOG = Logger.getInstance(ExecutionManagerImpl.class);
  private static final ProcessHandler[] EMPTY_PROCESS_HANDLERS = new ProcessHandler[0];

  private final Project myProject;
  private final Alarm awaitingTerminationAlarm = new Alarm(Alarm.ThreadToUse.SWING_THREAD);
  private final List<Trinity<RunContentDescriptor, RunnerAndConfigurationSettings, Executor>> myRunningConfigurations =
    ContainerUtil.createLockFreeCopyOnWriteList();
  private RunContentManagerImpl myContentManager;
  private volatile boolean myForceCompilationInTests;

  protected ExecutionManagerImpl(@NotNull Project project) {
    myProject = project;
  }

  @NotNull
  private static ExecutionEnvironmentBuilder createEnvironmentBuilder(@NotNull Project project,
                                                                      @NotNull Executor executor,
                                                                      @Nullable RunnerAndConfigurationSettings configuration) {
    ExecutionEnvironmentBuilder builder = new ExecutionEnvironmentBuilder(project, executor);

    ProgramRunner runner =
      RunnerRegistry.getInstance().getRunner(executor.getId(), configuration != null ? configuration.getConfiguration() : null);
    if (runner == null && configuration != null) {
      LOG.error("Cannot find runner for " + configuration.getName());
    }
    else if (runner != null) {
      assert configuration != null;
      builder.runnerAndSettings(runner, configuration);
    }
    return builder;
  }

  public static boolean isProcessRunning(@Nullable RunContentDescriptor descriptor) {
    ProcessHandler processHandler = descriptor == null ? null : descriptor.getProcessHandler();
    return processHandler != null && !processHandler.isProcessTerminated();
  }

  private static void start(@NotNull ExecutionEnvironment environment) {
    RunnerAndConfigurationSettings settings = environment.getRunnerAndConfigurationSettings();
    ProgramRunnerUtil.executeConfiguration(environment, settings != null && settings.isEditBeforeRun(), true);
  }

  private static boolean userApprovesStopForSameTypeConfigurations(Project project, String configName, int instancesCount) {
    RunManagerImpl runManager = RunManagerImpl.getInstanceImpl(project);
    final RunManagerConfig config = runManager.getConfig();
    if (!config.isRestartRequiresConfirmation()) return true;

    DialogWrapper.DoNotAskOption option = new DialogWrapper.DoNotAskOption() {
      @Override
      public boolean isToBeShown() {
        return config.isRestartRequiresConfirmation();
      }

      @Override
      public void setToBeShown(boolean value, int exitCode) {
        config.setRestartRequiresConfirmation(value);
      }

      @Override
      public boolean canBeHidden() {
        return true;
      }

      @Override
      public boolean shouldSaveOptionsOnCancel() {
        return false;
      }

      @NotNull
      @Override
      public String getDoNotShowMessage() {
        return CommonBundle.message("dialog.options.do.not.show");
      }
    };
    return Messages.showOkCancelDialog(
      project,
      ExecutionBundle.message("rerun.singleton.confirmation.message", configName, instancesCount),
      ExecutionBundle.message("process.is.running.dialog.title", configName),
      ExecutionBundle.message("rerun.confirmation.button.text"),
      CommonBundle.message("button.cancel"),
      Messages.getQuestionIcon(), option) == Messages.OK;
  }

  private static boolean userApprovesStopForIncompatibleConfigurations(Project project,
                                                                       String configName,
                                                                       List<RunContentDescriptor> runningIncompatibleDescriptors) {
    RunManagerImpl runManager = RunManagerImpl.getInstanceImpl(project);
    final RunManagerConfig config = runManager.getConfig();
    if (!config.isStopIncompatibleRequiresConfirmation()) return true;

    DialogWrapper.DoNotAskOption option = new DialogWrapper.DoNotAskOption() {
      @Override
      public boolean isToBeShown() {
        return config.isStopIncompatibleRequiresConfirmation();
      }

      @Override
      public void setToBeShown(boolean value, int exitCode) {
        config.setStopIncompatibleRequiresConfirmation(value);
      }

      @Override
      public boolean canBeHidden() {
        return true;
      }

      @Override
      public boolean shouldSaveOptionsOnCancel() {
        return false;
      }

      @NotNull
      @Override
      public String getDoNotShowMessage() {
        return CommonBundle.message("dialog.options.do.not.show");
      }
    };

    final StringBuilder names = new StringBuilder();
    for (final RunContentDescriptor descriptor : runningIncompatibleDescriptors) {
      String name = descriptor.getDisplayName();
      if (names.length() > 0) {
        names.append(", ");
      }
      names.append(StringUtil.isEmpty(name) ? ExecutionBundle.message("run.configuration.no.name")
                                            : String.format("'%s'", name));
    }

    //noinspection DialogTitleCapitalization
    return Messages.showOkCancelDialog(
      project,
      ExecutionBundle.message("stop.incompatible.confirmation.message",
                              configName, names.toString(), runningIncompatibleDescriptors.size()),
      ExecutionBundle.message("incompatible.configuration.is.running.dialog.title", runningIncompatibleDescriptors.size()),
      ExecutionBundle.message("stop.incompatible.confirmation.button.text"),
      CommonBundle.message("button.cancel"),
      Messages.getQuestionIcon(), option) == Messages.OK;
  }

  private static void stop(@Nullable RunContentDescriptor descriptor) {
    ProcessHandler processHandler = descriptor != null ? descriptor.getProcessHandler() : null;
    if (processHandler == null) {
      return;
    }

    if (processHandler instanceof KillableProcess && processHandler.isProcessTerminating()) {
      ((KillableProcess)processHandler).killProcess();
      return;
    }

    if (!processHandler.isProcessTerminated()) {
      if (processHandler.detachIsDefault()) {
        processHandler.detachProcess();
      }
      else {
        processHandler.destroyProcess();
      }
    }
  }

  @Override
  public void dispose() {
    for (Trinity<RunContentDescriptor, RunnerAndConfigurationSettings, Executor> trinity : myRunningConfigurations) {
      Disposer.dispose(trinity.first);
    }
    myRunningConfigurations.clear();
  }

  @NotNull
  @Override
  public RunContentManager getContentManager() {
    if (myContentManager == null) {
      myContentManager = new RunContentManagerImpl(myProject, DockManager.getInstance(myProject));
      Disposer.register(myProject, myContentManager);
    }
    return myContentManager;
  }

  @NotNull
  @Override
  public ProcessHandler[] getRunningProcesses() {
    if (myContentManager == null) return EMPTY_PROCESS_HANDLERS;
    List<ProcessHandler> handlers = null;
    for (RunContentDescriptor descriptor : getContentManager().getAllDescriptors()) {
      ProcessHandler processHandler = descriptor.getProcessHandler();
      if (processHandler != null) {
        if (handlers == null) {
          handlers = new SmartList<ProcessHandler>();
        }
        handlers.add(processHandler);
      }
    }
    return handlers == null ? EMPTY_PROCESS_HANDLERS : handlers.toArray(new ProcessHandler[handlers.size()]);
  }

  @Override
  public void compileAndRun(@NotNull final Runnable startRunnable,
                            @NotNull final ExecutionEnvironment environment,
                            @Nullable final RunProfileState state,
                            @Nullable final Runnable onCancelRunnable) {
    long id = environment.getExecutionId();
    if (id == 0) {
      id = environment.assignNewExecutionId();
    }

    RunProfile profile = environment.getRunProfile();
    if (!(profile instanceof RunConfiguration)) {
      startRunnable.run();
      return;
    }

    final RunConfiguration runConfiguration = (RunConfiguration)profile;
    final List<BeforeRunTask> beforeRunTasks = RunManagerEx.getInstanceEx(myProject).getBeforeRunTasks(runConfiguration);
    if (beforeRunTasks.isEmpty()) {
      startRunnable.run();
    }
    else {
      DataContext context = environment.getDataContext();
      final DataContext projectContext = context != null ? context : SimpleDataContext.getProjectContext(myProject);
      final long finalId = id;
      final Long executionSessionId = new Long(id);
      ApplicationManager.getApplication().executeOnPooledThread(new Runnable() {
        /**
         * @noinspection SSBasedInspection
         */
        @Override
        public void run() {
          for (BeforeRunTask task : beforeRunTasks) {
            if (myProject.isDisposed()) {
              return;
            }
            @SuppressWarnings("unchecked")
            BeforeRunTaskProvider<BeforeRunTask> provider = BeforeRunTaskProvider.getProvider(myProject, task.getProviderId());
            if (provider == null) {
              LOG.warn("Cannot find BeforeRunTaskProvider for id='" + task.getProviderId() + "'");
              continue;
            }
            ExecutionEnvironment taskEnvironment = new ExecutionEnvironmentBuilder(environment).contentToReuse(null).build();
            taskEnvironment.setExecutionId(finalId);
            EXECUTION_SESSION_ID_KEY.set(taskEnvironment, executionSessionId);
            if (!provider.executeTask(projectContext, runConfiguration, taskEnvironment, task)) {
              if (onCancelRunnable != null) {
                SwingUtilities.invokeLater(onCancelRunnable);
              }
              return;
            }
          }

          doRun(environment, startRunnable);
        }
      });
    }
  }

  protected void doRun(@NotNull final ExecutionEnvironment environment, @NotNull final Runnable startRunnable) {
    Boolean allowSkipRun = environment.getUserData(EXECUTION_SKIP_RUN);
    if (allowSkipRun != null && allowSkipRun) {
      environment.getProject().getMessageBus().syncPublisher(EXECUTION_TOPIC).processNotStarted(environment.getExecutor().getId(),
                                                                                                environment);
    }
    else {
      // important! Do not use DumbService.smartInvokeLater here because it depends on modality state
      // and execution of startRunnable could be skipped if modality state check fails
      //noinspection SSBasedInspection
      SwingUtilities.invokeLater(new Runnable() {
        @Override
        public void run() {
          if (!myProject.isDisposed()) {
            DumbService.getInstance(myProject).runWhenSmart(startRunnable);
          }
        }
      });
    }
  }

  @Override
  public void startRunProfile(@NotNull final RunProfileStarter starter,
                              @NotNull final RunProfileState state,
                              @NotNull final ExecutionEnvironment environment) {
    final Project project = environment.getProject();
    RunContentDescriptor reuseContent = getContentManager().getReuseContent(environment);
    if (reuseContent != null) {
      reuseContent.setExecutionId(environment.getExecutionId());
      environment.setContentToReuse(reuseContent);
    }

    final Executor executor = environment.getExecutor();
    project.getMessageBus().syncPublisher(EXECUTION_TOPIC).processStartScheduled(executor.getId(), environment);

    Runnable startRunnable = new Runnable() {
      @Override
      public void run() {
        if (project.isDisposed()) {
          return;
        }

        RunProfile profile = environment.getRunProfile();
        boolean started = false;
        try {
          project.getMessageBus().syncPublisher(EXECUTION_TOPIC).processStarting(executor.getId(), environment);

          final RunContentDescriptor descriptor = starter.execute(state, environment);
          if (descriptor != null) {
            environment.setContentToReuse(descriptor);
            final Trinity<RunContentDescriptor, RunnerAndConfigurationSettings, Executor> trinity =
              Trinity.create(descriptor, environment.getRunnerAndConfigurationSettings(), executor);
            myRunningConfigurations.add(trinity);
            Disposer.register(descriptor, new Disposable() {
              @Override
              public void dispose() {
                myRunningConfigurations.remove(trinity);
              }
            });
            getContentManager().showRunContent(executor, descriptor, environment.getContentToReuse());
            final ProcessHandler processHandler = descriptor.getProcessHandler();
            if (processHandler != null) {
              if (!processHandler.isStartNotified()) {
                processHandler.startNotify();
              }
              project.getMessageBus().syncPublisher(EXECUTION_TOPIC).processStarted(executor.getId(), environment, processHandler);
              started = true;
              processHandler.addProcessListener(new ProcessExecutionListener(project, profile, processHandler));
            }
          }
        }
        catch (ProcessCanceledException e) {
          LOG.info(e);
        }
        catch (ExecutionException e) {
          ExecutionUtil.handleExecutionError(project, executor.getToolWindowId(), profile, e);
          LOG.info(e);
        }
        finally {
          if (!started) {
            project.getMessageBus().syncPublisher(EXECUTION_TOPIC).processNotStarted(executor.getId(), environment);
          }
        }
      }
    };

    if (ApplicationManager.getApplication().isUnitTestMode() && !myForceCompilationInTests) {
      startRunnable.run();
    }
    else {
      compileAndRun(startRunnable, environment, state, new Runnable() {
        @Override
        public void run() {
          if (!project.isDisposed()) {
            project.getMessageBus().syncPublisher(EXECUTION_TOPIC).processNotStarted(executor.getId(), environment);
          }
        }
      });
    }
  }

  @Override
  public void restartRunProfile(@NotNull Project project,
                                @NotNull Executor executor,
                                @NotNull ExecutionTarget target,
                                @Nullable RunnerAndConfigurationSettings configuration,
                                @Nullable ProcessHandler processHandler) {
    ExecutionEnvironmentBuilder builder = createEnvironmentBuilder(project, executor, configuration);
    if (processHandler != null) {
      for (RunContentDescriptor descriptor : getContentManager().getAllDescriptors()) {
        if (descriptor.getProcessHandler() == processHandler) {
          builder.contentToReuse(descriptor);
          break;
        }
      }
    }
    restartRunProfile(builder.target(target).build());
  }

  @Override
  public void restartRunProfile(@NotNull final ExecutionEnvironment environment) {
    RunnerAndConfigurationSettings configuration = environment.getRunnerAndConfigurationSettings();

    List<RunContentDescriptor> runningIncompatible;
    if (configuration == null) {
      runningIncompatible = Collections.emptyList();
    }
    else {
      runningIncompatible = getIncompatibleRunningDescriptors(configuration);
    }

    RunContentDescriptor contentToReuse = environment.getContentToReuse();
    final List<RunContentDescriptor> runningOfTheSameType = new SmartList<RunContentDescriptor>();
    if (configuration != null && configuration.isSingleton()) {
      runningOfTheSameType.addAll(getRunningDescriptorsOfTheSameConfigType(configuration));
    }
    else if (isProcessRunning(contentToReuse)) {
      runningOfTheSameType.add(contentToReuse);
    }

    List<RunContentDescriptor> runningToStop = ContainerUtil.concat(runningOfTheSameType, runningIncompatible);
    if (!runningToStop.isEmpty()) {
      if (configuration != null) {
        if (!runningOfTheSameType.isEmpty()
            && (runningOfTheSameType.size() > 1 || contentToReuse == null || runningOfTheSameType.get(0) != contentToReuse) &&
            !userApprovesStopForSameTypeConfigurations(environment.getProject(), configuration.getName(), runningOfTheSameType.size())) {
          return;
        }
        if (!runningIncompatible.isEmpty()
            && !userApprovesStopForIncompatibleConfigurations(myProject, configuration.getName(), runningIncompatible)) {
          return;
        }
      }

      for (RunContentDescriptor descriptor : runningToStop) {
        stop(descriptor);
      }
    }

    awaitingTerminationAlarm.addRequest(new Runnable() {
      @Override
      public void run() {
        if (DumbService.getInstance(myProject).isDumb() || ExecutorRegistry.getInstance().isStarting(environment)) {
          awaitingTerminationAlarm.addRequest(this, 100);
          return;
        }

        for (RunContentDescriptor descriptor : runningOfTheSameType) {
          ProcessHandler processHandler = descriptor.getProcessHandler();
          if (processHandler != null && !processHandler.isProcessTerminated()) {
            awaitingTerminationAlarm.addRequest(this, 100);
            return;
          }
        }
        start(environment);
      }
    }, 50);
  }

  @TestOnly
  public void setForceCompilationInTests(boolean forceCompilationInTests) {
    myForceCompilationInTests = forceCompilationInTests;
  }

  @NotNull
  private List<RunContentDescriptor> getRunningDescriptorsOfTheSameConfigType(@NotNull final RunnerAndConfigurationSettings configurationAndSettings) {
    return getRunningDescriptors(new Condition<RunnerAndConfigurationSettings>() {
      @Override
      public boolean value(@Nullable RunnerAndConfigurationSettings runningConfigurationAndSettings) {
        return configurationAndSettings == runningConfigurationAndSettings;
      }
    });
  }

  @NotNull
  private List<RunContentDescriptor> getIncompatibleRunningDescriptors(@NotNull RunnerAndConfigurationSettings configurationAndSettings) {
    final RunConfiguration configurationToCheckCompatibility = configurationAndSettings.getConfiguration();
    return getRunningDescriptors(new Condition<RunnerAndConfigurationSettings>() {
      @Override
      public boolean value(@Nullable RunnerAndConfigurationSettings runningConfigurationAndSettings) {
        RunConfiguration runningConfiguration = runningConfigurationAndSettings == null ? null : runningConfigurationAndSettings.getConfiguration();
        if (runningConfiguration == null || !(runningConfiguration instanceof CompatibilityAwareRunProfile)) {
          return false;
        }
        return ((CompatibilityAwareRunProfile)runningConfiguration).mustBeStoppedToRun(configurationToCheckCompatibility);
      }
    });
  }

  @NotNull
  private List<RunContentDescriptor> getRunningDescriptors(@NotNull Condition<RunnerAndConfigurationSettings> condition) {
    List<RunContentDescriptor> result = new SmartList<RunContentDescriptor>();
    for (Trinity<RunContentDescriptor, RunnerAndConfigurationSettings, Executor> trinity : myRunningConfigurations) {
      if (condition.value(trinity.getSecond())) {
        ProcessHandler processHandler = trinity.getFirst().getProcessHandler();
        if (processHandler != null && !processHandler.isProcessTerminating() && !processHandler.isProcessTerminated()) {
          result.add(trinity.getFirst());
        }
      }
    }
    return result;
  }

  private static class ProcessExecutionListener extends ProcessAdapter {
    private final Project myProject;
    private final RunProfile myProfile;
    private final ProcessHandler myProcessHandler;

    public ProcessExecutionListener(Project project, RunProfile profile, ProcessHandler processHandler) {
      myProject = project;
      myProfile = profile;
      myProcessHandler = processHandler;
    }

    @Override
    public void processTerminated(ProcessEvent event) {
      if (myProject.isDisposed()) return;

      myProject.getMessageBus().syncPublisher(EXECUTION_TOPIC).processTerminated(myProfile, myProcessHandler);

      SaveAndSyncHandler.getInstance().scheduleRefresh();
    }

    @Override
    public void processWillTerminate(ProcessEvent event, boolean willBeDestroyed) {
      if (myProject.isDisposed()) return;

      myProject.getMessageBus().syncPublisher(EXECUTION_TOPIC).processTerminating(myProfile, myProcessHandler);
    }
  }
}


File: platform/lang-impl/src/com/intellij/execution/ui/RunContentManagerImpl.java
/*
 * Copyright 2000-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.execution.ui;

import com.intellij.execution.*;
import com.intellij.execution.process.ProcessAdapter;
import com.intellij.execution.process.ProcessEvent;
import com.intellij.execution.process.ProcessHandler;
import com.intellij.execution.runners.ExecutionEnvironment;
import com.intellij.execution.ui.layout.impl.DockableGridContainerFactory;
import com.intellij.ide.DataManager;
import com.intellij.ide.impl.ContentManagerWatcher;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.actionSystem.DataProvider;
import com.intellij.openapi.actionSystem.PlatformDataKeys;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.progress.Task;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.project.ProjectManager;
import com.intellij.openapi.project.ProjectManagerListener;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.IconLoader;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.wm.ToolWindow;
import com.intellij.openapi.wm.ToolWindowAnchor;
import com.intellij.openapi.wm.ToolWindowManager;
import com.intellij.openapi.wm.ex.ToolWindowManagerAdapter;
import com.intellij.openapi.wm.ex.ToolWindowManagerEx;
import com.intellij.ui.AppUIUtil;
import com.intellij.ui.ColorUtil;
import com.intellij.ui.LayeredIcon;
import com.intellij.ui.content.*;
import com.intellij.ui.docking.DockManager;
import com.intellij.util.SmartList;
import com.intellij.util.concurrency.Semaphore;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.ui.GraphicsUtil;
import com.intellij.util.ui.UIUtil;
import gnu.trove.THashMap;
import gnu.trove.THashSet;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.awt.geom.Ellipse2D;
import java.util.*;
import java.util.List;

public class RunContentManagerImpl implements RunContentManager, Disposable {
  public static final Key<Boolean> ALWAYS_USE_DEFAULT_STOPPING_BEHAVIOUR_KEY = Key.create("ALWAYS_USE_DEFAULT_STOPPING_BEHAVIOUR_KEY");
  private static final Logger LOG = Logger.getInstance(RunContentManagerImpl.class);
  private static final Key<RunContentDescriptor> DESCRIPTOR_KEY = Key.create("Descriptor");

  private final Project myProject;
  private final Map<String, ContentManager> myToolwindowIdToContentManagerMap = new THashMap<String, ContentManager>();
  private final Map<String, Icon> myToolwindowIdToBaseIconMap = new THashMap<String, Icon>();
  private final LinkedList<String> myToolwindowIdZBuffer = new LinkedList<String>();

  public RunContentManagerImpl(@NotNull Project project, @NotNull DockManager dockManager) {
    myProject = project;
    DockableGridContainerFactory containerFactory = new DockableGridContainerFactory();
    dockManager.register(DockableGridContainerFactory.TYPE, containerFactory);
    Disposer.register(myProject, containerFactory);

    AppUIUtil.invokeOnEdt(new Runnable() {
      @Override
      public void run() {
        init();
      }
    }, myProject.getDisposed());
  }

  // must be called on EDT
  private void init() {
    ToolWindowManagerEx toolWindowManager = ToolWindowManagerEx.getInstanceEx(myProject);
    if (toolWindowManager == null) {
      return;
    }

    for (Executor executor : ExecutorRegistry.getInstance().getRegisteredExecutors()) {
      registerToolwindow(executor, toolWindowManager);
    }

    toolWindowManager.addToolWindowManagerListener(new ToolWindowManagerAdapter() {
      @Override
      public void stateChanged() {
        if (myProject.isDisposed()) {
          return;
        }

        ToolWindowManager toolWindowManager = ToolWindowManager.getInstance(myProject);
        Set<String> currentWindows = new THashSet<String>();
        ContainerUtil.addAll(currentWindows, toolWindowManager.getToolWindowIds());
        myToolwindowIdZBuffer.retainAll(currentWindows);

        final String activeToolWindowId = toolWindowManager.getActiveToolWindowId();
        if (activeToolWindowId != null) {
          if (myToolwindowIdZBuffer.remove(activeToolWindowId)) {
            myToolwindowIdZBuffer.addFirst(activeToolWindowId);
          }
        }
      }
    });
  }

  @Override
  public void dispose() {
  }

  private void registerToolwindow(@NotNull final Executor executor, @NotNull ToolWindowManagerEx toolWindowManager) {
    final String toolWindowId = executor.getToolWindowId();
    if (toolWindowManager.getToolWindow(toolWindowId) != null) {
      return;
    }

    final ToolWindow toolWindow = toolWindowManager.registerToolWindow(toolWindowId, true, ToolWindowAnchor.BOTTOM, this, true);
    final ContentManager contentManager = toolWindow.getContentManager();
    contentManager.addDataProvider(new DataProvider() {
      private int myInsideGetData = 0;

      @Override
      public Object getData(String dataId) {
        myInsideGetData++;
        try {
          if (PlatformDataKeys.HELP_ID.is(dataId)) {
            return executor.getHelpId();
          }
          else {
            return myInsideGetData == 1 ? DataManager.getInstance().getDataContext(contentManager.getComponent()).getData(dataId) : null;
          }
        }
        finally {
          myInsideGetData--;
        }
      }
    });

    toolWindow.setIcon(executor.getToolWindowIcon());
    myToolwindowIdToBaseIconMap.put(toolWindowId, executor.getToolWindowIcon());
    new ContentManagerWatcher(toolWindow, contentManager);
    contentManager.addContentManagerListener(new ContentManagerAdapter() {
      @Override
      public void selectionChanged(final ContentManagerEvent event) {
        Content content = event.getContent();
        getSyncPublisher().contentSelected(content == null ? null : getRunContentDescriptorByContent(content), executor);
      }
    });
    myToolwindowIdToContentManagerMap.put(toolWindowId, contentManager);
    Disposer.register(contentManager, new Disposable() {
      @Override
      public void dispose() {
        myToolwindowIdToContentManagerMap.remove(toolWindowId).removeAllContents(true);
        myToolwindowIdZBuffer.remove(toolWindowId);
        myToolwindowIdToBaseIconMap.remove(toolWindowId);
      }
    });
    myToolwindowIdZBuffer.addLast(toolWindowId);
  }

  private RunContentWithExecutorListener getSyncPublisher() {
    return myProject.getMessageBus().syncPublisher(TOPIC);
  }

  @Override
  public void toFrontRunContent(final Executor requestor, final ProcessHandler handler) {
    final RunContentDescriptor descriptor = getDescriptorBy(handler, requestor);
    if (descriptor == null) {
      return;
    }
    toFrontRunContent(requestor, descriptor);
  }

  @Override
  public void toFrontRunContent(final Executor requestor, final RunContentDescriptor descriptor) {
    ApplicationManager.getApplication().invokeLater(new Runnable() {
      @Override
      public void run() {
        ContentManager contentManager = getContentManagerForRunner(requestor);
        Content content = getRunContentByDescriptor(contentManager, descriptor);
        if (content != null) {
          contentManager.setSelectedContent(content);
          ToolWindowManager.getInstance(myProject).getToolWindow(requestor.getToolWindowId()).show(null);
        }
      }
    }, myProject.getDisposed());
  }

  @Override
  public void hideRunContent(@NotNull final Executor executor, final RunContentDescriptor descriptor) {
    ApplicationManager.getApplication().invokeLater(new Runnable() {
      @Override
      public void run() {
        ToolWindow toolWindow = ToolWindowManager.getInstance(myProject).getToolWindow(executor.getToolWindowId());
        if (toolWindow != null) {
          toolWindow.hide(null);
        }
      }
    }, myProject.getDisposed());
  }

  @Override
  @Nullable
  public RunContentDescriptor getSelectedContent(final Executor executor) {
    final Content selectedContent = getContentManagerForRunner(executor).getSelectedContent();
    return selectedContent != null ? getRunContentDescriptorByContent(selectedContent) : null;
  }

  @Override
  @Nullable
  public RunContentDescriptor getSelectedContent() {
    for (String activeWindow : myToolwindowIdZBuffer) {
      final ContentManager contentManager = myToolwindowIdToContentManagerMap.get(activeWindow);
      if (contentManager == null) {
        continue;
      }

      final Content selectedContent = contentManager.getSelectedContent();
      if (selectedContent == null) {
        if (contentManager.getContentCount() == 0) {
          // continue to the next window if the content manager is empty
          continue;
        }
        else {
          // stop iteration over windows because there is some content in the window and the window is the last used one
          break;
        }
      }
      // here we have selected content
      return getRunContentDescriptorByContent(selectedContent);
    }

    return null;
  }

  @Override
  public boolean removeRunContent(@NotNull final Executor executor, final RunContentDescriptor descriptor) {
    final ContentManager contentManager = getContentManagerForRunner(executor);
    final Content content = getRunContentByDescriptor(contentManager, descriptor);
    return content != null && contentManager.removeContent(content, true);
  }

  @Override
  public void showRunContent(@NotNull Executor executor, @NotNull RunContentDescriptor descriptor) {
    showRunContent(executor, descriptor, descriptor.getExecutionId());
  }

  public void showRunContent(@NotNull final Executor executor, @NotNull final RunContentDescriptor descriptor, final long executionId) {
    if (ApplicationManager.getApplication().isUnitTestMode()) {
      return;
    }

    final ContentManager contentManager = getContentManagerForRunner(executor);
    RunContentDescriptor oldDescriptor = chooseReuseContentForDescriptor(contentManager, descriptor, executionId, descriptor.getDisplayName());
    final Content content;
    if (oldDescriptor == null) {
      content = createNewContent(contentManager, descriptor, executor);
      Icon icon = descriptor.getIcon();
      content.setIcon(icon == null ? executor.getToolWindowIcon() : icon);
    }
    else {
      content = oldDescriptor.getAttachedContent();
      LOG.assertTrue(content != null);
      getSyncPublisher().contentRemoved(oldDescriptor, executor);
      Disposer.dispose(oldDescriptor); // is of the same category, can be reused
    }

    content.setExecutionId(executionId);
    content.setComponent(descriptor.getComponent());
    content.setPreferredFocusedComponent(descriptor.getPreferredFocusComputable());
    content.putUserData(DESCRIPTOR_KEY, descriptor);
    final ToolWindow toolWindow = ToolWindowManager.getInstance(myProject).getToolWindow(executor.getToolWindowId());
    final ProcessHandler processHandler = descriptor.getProcessHandler();
    if (processHandler != null) {
      final ProcessAdapter processAdapter = new ProcessAdapter() {
        @Override
        public void startNotified(final ProcessEvent event) {
          UIUtil.invokeLaterIfNeeded(new Runnable() {
            @Override
            public void run() {
              toolWindow.setIcon(getLiveIndicator(myToolwindowIdToBaseIconMap.get(executor.getToolWindowId())));
            }
          });
        }

        @Override
        public void processTerminated(final ProcessEvent event) {
          ApplicationManager.getApplication().invokeLater(new Runnable() {
            @Override
            public void run() {
              boolean alive = false;
              String toolWindowId = executor.getToolWindowId();
              ContentManager manager = myToolwindowIdToContentManagerMap.get(toolWindowId);
              if (manager == null) return;
              for (Content content : manager.getContents()) {
                RunContentDescriptor descriptor = getRunContentDescriptorByContent(content);
                if (descriptor != null) {
                  ProcessHandler handler = descriptor.getProcessHandler();
                  if (handler != null && !handler.isProcessTerminated()) {
                    alive = true;
                    break;
                  }
                }
              }
              Icon base = myToolwindowIdToBaseIconMap.get(toolWindowId);
              toolWindow.setIcon(alive ? getLiveIndicator(base) : base);

              Icon icon = descriptor.getIcon();
              content.setIcon(icon == null ? executor.getDisabledIcon() : IconLoader.getTransparentIcon(icon));
            }
          });
        }
      };
      processHandler.addProcessListener(processAdapter);
      final Disposable disposer = content.getDisposer();
      if (disposer != null) {
        Disposer.register(disposer, new Disposable() {
          @Override
          public void dispose() {
            processHandler.removeProcessListener(processAdapter);
          }
        });
      }
    }
    content.setDisplayName(descriptor.getDisplayName());
    descriptor.setAttachedContent(content);
    content.getManager().setSelectedContent(content);

    if (!descriptor.isActivateToolWindowWhenAdded()) {
      return;
    }

    ApplicationManager.getApplication().invokeLater(new Runnable() {
      @Override
      public void run() {
        ToolWindow window = ToolWindowManager.getInstance(myProject).getToolWindow(executor.getToolWindowId());
        // let's activate tool window, but don't move focus
        //
        // window.show() isn't valid here, because it will not
        // mark the window as "last activated" windows and thus
        // some action like navigation up/down in stacktrace wont
        // work correctly
        descriptor.getPreferredFocusComputable();
        window.activate(descriptor.getActivationCallback(), descriptor.isAutoFocusContent(), descriptor.isAutoFocusContent());
      }
    }, myProject.getDisposed());
  }

  private final static int INDICATOR_SIZE = 4;
  private static Icon getLiveIndicator(final Icon base) {
    return new LayeredIcon(base, new Icon() {
      @Override
      public void paintIcon(Component c, Graphics g, int x, int y) {
        Graphics2D g2d = (Graphics2D)g.create();
        try {
          GraphicsUtil.setupAAPainting(g2d);
          g2d.setColor(Color.GREEN);
          Ellipse2D.Double shape =
            new Ellipse2D.Double(x + getIconWidth() - INDICATOR_SIZE, y + getIconHeight() - INDICATOR_SIZE, INDICATOR_SIZE, INDICATOR_SIZE);
          g2d.fill(shape);
          g2d.setColor(ColorUtil.withAlpha(Color.BLACK, .40));
          g2d.draw(shape);
        }
        finally {
          g2d.dispose();
        }
      }

      @Override
      public int getIconWidth() {
        return base != null ? base.getIconWidth() : 13;
      }

      @Override
      public int getIconHeight() {
        return base != null ? base.getIconHeight() : 13;
      }
    });
  }

  @Nullable
  @Override
  public RunContentDescriptor getReuseContent(@NotNull ExecutionEnvironment executionEnvironment) {
    if (ApplicationManager.getApplication().isUnitTestMode()) return null;
    RunContentDescriptor contentToReuse = executionEnvironment.getContentToReuse();
    if (contentToReuse != null) {
      return contentToReuse;
    }

    final ContentManager contentManager = getContentManagerForRunner(executionEnvironment.getExecutor());
    return chooseReuseContentForDescriptor(contentManager, null, executionEnvironment.getExecutionId(),
                                           executionEnvironment.toString());
  }

  @Override
  public RunContentDescriptor findContentDescriptor(final Executor requestor, final ProcessHandler handler) {
    return getDescriptorBy(handler, requestor);
  }

  @Override
  public void showRunContent(@NotNull Executor info, @NotNull RunContentDescriptor descriptor, @Nullable RunContentDescriptor contentToReuse) {
    copyContentAndBehavior(descriptor, contentToReuse);
    showRunContent(info, descriptor, descriptor.getExecutionId());
  }

  public static void copyContentAndBehavior(@NotNull RunContentDescriptor descriptor, @Nullable RunContentDescriptor contentToReuse) {
    if (contentToReuse != null) {
      Content attachedContent = contentToReuse.getAttachedContent();
      if (attachedContent != null && attachedContent.isValid()) {
        descriptor.setAttachedContent(attachedContent);
      }
      if (contentToReuse.isReuseToolWindowActivation()) {
        descriptor.setActivateToolWindowWhenAdded(contentToReuse.isActivateToolWindowWhenAdded());
      }
    }
  }

  @Nullable
  private static RunContentDescriptor chooseReuseContentForDescriptor(@NotNull ContentManager contentManager,
                                                                      @Nullable RunContentDescriptor descriptor,
                                                                      long executionId,
                                                                      @Nullable String preferredName) {
    Content content = null;
    if (descriptor != null) {
      //Stage one: some specific descriptors (like AnalyzeStacktrace) cannot be reused at all
      if (descriptor.isContentReuseProhibited()) {
        return null;
      }
      //Stage two: try to get content from descriptor itself
      final Content attachedContent = descriptor.getAttachedContent();

      if (attachedContent != null
          && attachedContent.isValid()
          && contentManager.getIndexOfContent(attachedContent) != -1
          && (Comparing.equal(descriptor.getDisplayName(), attachedContent.getDisplayName()) || !attachedContent.isPinned())) {
        content = attachedContent;
      }
    }
    //Stage three: choose the content with name we prefer
    if (content == null) {
      content = getContentFromManager(contentManager, preferredName, executionId);
    }
    if (content == null || !isTerminated(content) || (content.getExecutionId() == executionId && executionId != 0)) {
      return null;
    }
    final RunContentDescriptor oldDescriptor = getRunContentDescriptorByContent(content);
    if (oldDescriptor != null && !oldDescriptor.isContentReuseProhibited() ) {
      //content.setExecutionId(executionId);
      return oldDescriptor;
    }

    return null;
  }

  @Nullable
  private static Content getContentFromManager(ContentManager contentManager, @Nullable String preferredName, long executionId) {
    ArrayList<Content> contents = new ArrayList<Content>(Arrays.asList(contentManager.getContents()));
    Content first = contentManager.getSelectedContent();
    if (first != null && contents.remove(first)) {//selected content should be checked first
      contents.add(0, first);
    }
    if (preferredName != null) {//try to match content with specified preferred name
      for (Content c : contents) {
        if (canReuseContent(c, executionId) && preferredName.equals(c.getDisplayName())) {
          return c;
        }
      }
    }
    for (Content c : contents) {//return first "good" content
      if (canReuseContent(c, executionId)) {
        return c;
      }
    }
    return null;
  }

  private static boolean canReuseContent(Content c, long executionId) {
    return c != null && !c.isPinned() && isTerminated(c) && !(c.getExecutionId() == executionId && executionId != 0);
  }

  @NotNull
  private ContentManager getContentManagerForRunner(final Executor executor) {
    final ContentManager contentManager = myToolwindowIdToContentManagerMap.get(executor.getToolWindowId());
    if (contentManager == null) {
      LOG.error("Runner " + executor.getId() + " is not registered");
    }
    //noinspection ConstantConditions
    return contentManager;
  }

  private Content createNewContent(final ContentManager contentManager, final RunContentDescriptor descriptor, Executor executor) {
    final String processDisplayName = descriptor.getDisplayName();
    final Content content = ContentFactory.SERVICE.getInstance().createContent(descriptor.getComponent(), processDisplayName, true);
    content.putUserData(DESCRIPTOR_KEY, descriptor);
    content.putUserData(ToolWindow.SHOW_CONTENT_ICON, Boolean.TRUE);
    contentManager.addContent(content);
    new CloseListener(content, executor);
    return content;
  }

  private static boolean isTerminated(@NotNull Content content) {
    RunContentDescriptor descriptor = getRunContentDescriptorByContent(content);
    ProcessHandler processHandler = descriptor == null ? null : descriptor.getProcessHandler();
    return processHandler == null || processHandler.isProcessTerminated();
  }

  @Nullable
  private static RunContentDescriptor getRunContentDescriptorByContent(@NotNull Content content) {
    return content.getUserData(DESCRIPTOR_KEY);
  }

  @Override
  @Nullable
  public ToolWindow getToolWindowByDescriptor(@NotNull RunContentDescriptor descriptor) {
    for (Map.Entry<String, ContentManager> entry : myToolwindowIdToContentManagerMap.entrySet()) {
      if (getRunContentByDescriptor(entry.getValue(), descriptor) != null) {
        return ToolWindowManager.getInstance(myProject).getToolWindow(entry.getKey());
      }
    }
    return null;
  }

  @Nullable
  private static Content getRunContentByDescriptor(@NotNull ContentManager contentManager, @NotNull RunContentDescriptor descriptor) {
    for (Content content : contentManager.getContents()) {
      if (descriptor.equals(content.getUserData(DESCRIPTOR_KEY))) {
        return content;
      }
    }
    return null;
  }

  @Override
  @NotNull
  public List<RunContentDescriptor> getAllDescriptors() {
    if (myToolwindowIdToContentManagerMap.isEmpty()) {
      return Collections.emptyList();
    }

    List<RunContentDescriptor> descriptors = new SmartList<RunContentDescriptor>();
    for (String id : myToolwindowIdToContentManagerMap.keySet()) {
      for (Content content : myToolwindowIdToContentManagerMap.get(id).getContents()) {
        RunContentDescriptor descriptor = getRunContentDescriptorByContent(content);
        if (descriptor != null) {
          descriptors.add(descriptor);
        }
      }
    }
    return descriptors;
  }

  @Nullable
  private RunContentDescriptor getDescriptorBy(ProcessHandler handler, Executor runnerInfo) {
    for (Content content : getContentManagerForRunner(runnerInfo).getContents()) {
      RunContentDescriptor runContentDescriptor = getRunContentDescriptorByContent(content);
      assert runContentDescriptor != null;
      if (runContentDescriptor.getProcessHandler() == handler) {
        return runContentDescriptor;
      }
    }
    return null;
  }

  private class CloseListener extends ContentManagerAdapter implements ProjectManagerListener {
    private Content myContent;
    private final Executor myExecutor;

    private CloseListener(@NotNull final Content content, @NotNull Executor executor) {
      myContent = content;
      content.getManager().addContentManagerListener(this);
      ProjectManager.getInstance().addProjectManagerListener(this);
      myExecutor = executor;
    }

    @Override
    public void contentRemoved(final ContentManagerEvent event) {
      final Content content = event.getContent();
      if (content == myContent) {
        dispose();
      }
    }

    private void dispose() {
      if (myContent == null) return;

      final Content content = myContent;
      try {
        RunContentDescriptor descriptor = getRunContentDescriptorByContent(content);
        getSyncPublisher().contentRemoved(descriptor, myExecutor);
        if (descriptor != null) {
          Disposer.dispose(descriptor);
        }
      }
      finally {
        content.getManager().removeContentManagerListener(this);
        ProjectManager.getInstance().removeProjectManagerListener(this);
        content.release(); // don't invoke myContent.release() because myContent becomes null after destroyProcess()
        myContent = null;
      }
    }

    @Override
    public void contentRemoveQuery(final ContentManagerEvent event) {
      if (event.getContent() == myContent) {
        final boolean canClose = closeQuery(false);
        if (!canClose) {
          event.consume();
        }
      }
    }

    @Override
    public void projectOpened(final Project project) {
    }

    @Override
    public void projectClosed(final Project project) {
      if (myContent != null && project == myProject) {
        myContent.getManager().removeContent(myContent, true);
        dispose(); // Dispose content even if content manager refused to.
      }
    }

    @Override
    public boolean canCloseProject(final Project project) {
      if (project != myProject) return true;

      if (myContent == null) return true;

      final boolean canClose = closeQuery(true);
      if (canClose) {
        myContent.getManager().removeContent(myContent, true);
        myContent = null;
      }
      return canClose;
    }

    @Override
    public void projectClosing(final Project project) {
    }

    private boolean closeQuery(boolean modal) {
      final RunContentDescriptor descriptor = getRunContentDescriptorByContent(myContent);
      if (descriptor == null) {
        return true;
      }

      final ProcessHandler processHandler = descriptor.getProcessHandler();
      if (processHandler == null || processHandler.isProcessTerminated() || processHandler.isProcessTerminating()) {
        return true;
      }
      final boolean destroyProcess;
      //noinspection deprecation
      if (processHandler.isSilentlyDestroyOnClose() || Boolean.TRUE.equals(processHandler.getUserData(ProcessHandler.SILENTLY_DESTROY_ON_CLOSE))) {
        destroyProcess = true;
      }
      else {
        //todo[nik] this is a temporary solution for the following problem: some configurations should not allow user to choose between 'terminating' and 'detaching'
        final boolean useDefault = Boolean.TRUE.equals(processHandler.getUserData(ALWAYS_USE_DEFAULT_STOPPING_BEHAVIOUR_KEY));
        final TerminateRemoteProcessDialog.TerminateOption option = new TerminateRemoteProcessDialog.TerminateOption(processHandler.detachIsDefault(), useDefault);
        final int rc = TerminateRemoteProcessDialog.show(myProject, descriptor.getDisplayName(), option);
        if (rc != DialogWrapper.OK_EXIT_CODE) return false;
        destroyProcess = !option.isToBeShown();
      }
      if (destroyProcess) {
        processHandler.destroyProcess();
      }
      else {
        processHandler.detachProcess();
      }
      waitForProcess(descriptor, modal);
      return true;
    }
  }

  private void waitForProcess(final RunContentDescriptor descriptor, final boolean modal) {
    final ProcessHandler processHandler = descriptor.getProcessHandler();
    final boolean killable = !modal && (processHandler instanceof KillableProcess) && ((KillableProcess)processHandler).canKillProcess();

    String title = ExecutionBundle.message("terminating.process.progress.title", descriptor.getDisplayName());
    ProgressManager.getInstance().run(new Task.Backgroundable(myProject, title, true) {

      {
        if (killable) {
          String cancelText= ExecutionBundle.message("terminating.process.progress.kill");
          setCancelText(cancelText);
          setCancelTooltipText(cancelText);
        }
      }

      @Override
      public boolean isConditionalModal() {
        return modal;
      }

      @Override
      public boolean shouldStartInBackground() {
        return !modal;
      }

      @Override
      public void run(@NotNull final ProgressIndicator progressIndicator) {
        final Semaphore semaphore = new Semaphore();
        semaphore.down();

        ApplicationManager.getApplication().executeOnPooledThread(new Runnable() {
          @Override
          public void run() {
            final ProcessHandler processHandler = descriptor.getProcessHandler();
            try {
              if (processHandler != null) {
                processHandler.waitFor();
              }
            }
            finally {
              semaphore.up();
            }
          }
        });

        progressIndicator.setText(ExecutionBundle.message("waiting.for.vm.detach.progress.text"));
        ApplicationManager.getApplication().executeOnPooledThread(new Runnable() {
          @Override
          public void run() {
            while (true) {
              if (progressIndicator.isCanceled() || !progressIndicator.isRunning()) {
                semaphore.up();
                break;
              }
              try {
                //noinspection SynchronizeOnThis
                synchronized (this) {
                  //noinspection SynchronizeOnThis
                  wait(2000L);
                }
              }
              catch (InterruptedException ignore) {
              }
            }
          }
        });

        semaphore.waitFor();
      }

      @Override
      public void onCancel() {
        if (killable && !processHandler.isProcessTerminated()) {
          ((KillableProcess)processHandler).killProcess();
        }
      }
    });
  }
}
