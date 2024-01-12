Refactoring Types: ['Move Class']
com/intellij/ui/components/JBSlidingPanel.java
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
package com.intellij.ui.components;

import com.intellij.openapi.util.ActionCallback;
import com.intellij.openapi.util.Pair;
import com.intellij.ui.JBCardLayout;
import com.intellij.util.ui.components.JBPanel;

import java.awt.*;
import java.util.ArrayList;

/**
 * @author Konstantin Bulenkov
 */
public class JBSlidingPanel extends JBPanel {
  private final ArrayList<Pair<String,Component>> mySlides = new ArrayList<Pair<String, Component>>();
  private int mySelectedIndex = -1;

  public JBSlidingPanel() {
    setLayout(new JBCardLayout());
  }

  @Override
  public JBCardLayout getLayout() {
    return (JBCardLayout)super.getLayout();
  }

  @Override
  public Component add(String name, Component comp) {
    mySlides.add(Pair.create(name, comp));
    if (mySelectedIndex == -1) {
      mySelectedIndex = 0;
    }
    return super.add(name, comp);
  }

  public ActionCallback goLeft() {
    if (mySelectedIndex == 0) {
      return ActionCallback.REJECTED;
    }
    mySelectedIndex--;
    return applySlide(JBCardLayout.SwipeDirection.BACKWARD);
  }

  public ActionCallback swipe(String id, JBCardLayout.SwipeDirection direction) {
    final ActionCallback done = new ActionCallback();
    getLayout().swipe(this, id, direction, new Runnable() {
      @Override
      public void run() {
        done.setDone();
      }
    });
    return done;
  }

  public ActionCallback goRight() {
    if (mySelectedIndex == mySlides.size() - 1) {
      return ActionCallback.REJECTED;
    }
    mySelectedIndex++;
    return applySlide(JBCardLayout.SwipeDirection.FORWARD);
  }

  private ActionCallback applySlide(JBCardLayout.SwipeDirection direction) {
    final ActionCallback callback = new ActionCallback();
    getLayout().swipe(this, mySlides.get(mySelectedIndex).first, direction, new Runnable() {
      @Override
      public void run() {
        callback.setDone();
      }
    });
    return callback;
  }

  @Override
  @Deprecated
  public Component add(Component comp) {
    throw new AddMethodIsNotSupportedException();
  }

  @Override
  @Deprecated
  public Component add(Component comp, int index) {
    throw new AddMethodIsNotSupportedException();
  }

  @Override
  @Deprecated
  public void add(Component comp, Object constraints) {
    throw new AddMethodIsNotSupportedException();
  }

  @Override
  @Deprecated
  public void add(Component comp, Object constraints, int index) {
    throw new AddMethodIsNotSupportedException();
  }

  private static class AddMethodIsNotSupportedException extends RuntimeException {
    public AddMethodIsNotSupportedException() {
      super("Use add(String, Component) method");
    }
  }
}


File: platform/platform-impl/src/com/intellij/openapi/wm/impl/IdePanePanel.java
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
package com.intellij.openapi.wm.impl;

import com.intellij.util.ui.components.JBPanel;

import java.awt.*;

public class IdePanePanel extends JBPanel {

  public IdePanePanel(LayoutManager layout) {
    super(layout);
  }

  @Override
  public Color getBackground() {
    return IdeBackgroundUtil.getIdeBackgroundColor();
  }
}


File: platform/platform-impl/src/com/intellij/openapi/wm/impl/IdeRootPane.java
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
package com.intellij.openapi.wm.impl;

import com.intellij.diagnostic.IdeMessagePanel;
import com.intellij.diagnostic.MessagePool;
import com.intellij.ide.DataManager;
import com.intellij.ide.actions.CustomizeUIAction;
import com.intellij.ide.actions.ViewToolbarAction;
import com.intellij.ide.ui.UISettings;
import com.intellij.ide.ui.UISettingsListener;
import com.intellij.ide.ui.customization.CustomActionsSchema;
import com.intellij.openapi.actionSystem.*;
import com.intellij.openapi.actionSystem.ex.ActionManagerEx;
import com.intellij.openapi.application.Application;
import com.intellij.openapi.extensions.Extensions;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.SystemInfo;
import com.intellij.openapi.wm.*;
import com.intellij.openapi.wm.ex.IdeFrameEx;
import com.intellij.openapi.wm.impl.status.IdeStatusBarImpl;
import com.intellij.openapi.wm.impl.status.MemoryUsagePanel;
import com.intellij.ui.BalloonLayout;
import com.intellij.ui.BalloonLayoutImpl;
import com.intellij.ui.PopupHandler;
import com.intellij.ui.components.JBLayeredPane;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.ui.JBUI;
import com.intellij.util.ui.UIUtil;
import com.intellij.util.ui.components.JBPanel;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import java.util.ArrayList;
import java.util.List;

/**
 * @author Anton Katilin
 * @author Vladimir Kondratyev
 */
public class IdeRootPane extends JRootPane implements UISettingsListener {
  /**
   * Toolbar and status bar.
   */
  private JComponent myToolbar;
  private IdeStatusBarImpl myStatusBar;

  private final Box myNorthPanel = Box.createVerticalBox();
  private final List<IdeRootPaneNorthExtension> myNorthComponents = new ArrayList<IdeRootPaneNorthExtension>();

  /**
   * Current <code>ToolWindowsPane</code>. If there is no such pane then this field is null.
   */
  private ToolWindowsPane myToolWindowsPane;
  private JBPanel myContentPane;
  private final ActionManager myActionManager;
  private final UISettings myUISettings;

  private final boolean myGlassPaneInitialized;
  private final IdeGlassPaneImpl myGlassPane;

  private final Application myApplication;
  private MemoryUsagePanel myMemoryWidget;
  private final StatusBarCustomComponentFactory[] myStatusBarCustomComponentFactories;

  private boolean myFullScreen;

  public IdeRootPane(ActionManagerEx actionManager, UISettings uiSettings, DataManager dataManager, Application application, final IdeFrame frame) {
    myActionManager = actionManager;
    myUISettings = uiSettings;

    myContentPane.add(myNorthPanel, BorderLayout.NORTH);

    myStatusBarCustomComponentFactories = application.getExtensions(StatusBarCustomComponentFactory.EP_NAME);
    myApplication = application;

    createStatusBar(frame);

    updateStatusBarVisibility();
    updateToolbar();

    myContentPane.add(myStatusBar, BorderLayout.SOUTH);

    if (WindowManagerImpl.isFloatingMenuBarSupported()) {
      menuBar = new IdeMenuBar(actionManager, dataManager);
      getLayeredPane().add(menuBar, new Integer(JLayeredPane.DEFAULT_LAYER - 1));
      if (frame instanceof IdeFrameEx) {
        addPropertyChangeListener(WindowManagerImpl.FULL_SCREEN, new PropertyChangeListener() {
          @Override public void propertyChange(PropertyChangeEvent evt) {
            myFullScreen = ((IdeFrameEx)frame).isInFullScreen();
          }
        });
      }
    }
    else {
      setJMenuBar(new IdeMenuBar(actionManager, dataManager));
    }

    myGlassPane = new IdeGlassPaneImpl(this);
    setGlassPane(myGlassPane);
    myGlassPaneInitialized = true;

    myGlassPane.setVisible(false);
  }

  @Override
  protected LayoutManager createRootLayout() {
    return WindowManagerImpl.isFloatingMenuBarSupported() ? new MyRootLayout() : super.createRootLayout();
  }

  @Override
  public void setGlassPane(final Component glass) {
    if (myGlassPaneInitialized) throw new IllegalStateException("Setting of glass pane for IdeFrame is prohibited");
    super.setGlassPane(glass);
  }


  /**
   * Invoked when enclosed frame is being shown.
   */
  public final void addNotify(){
    super.addNotify();
    myUISettings.addUISettingsListener(this);
  }

  /**
   * Invoked when enclosed frame is being disposed.
   */
  public final void removeNotify(){
    myUISettings.removeUISettingsListener(this);
    super.removeNotify();
  }

  /**
   * Sets current tool windows pane (panel where all tool windows are located).
   * If <code>toolWindowsPane</code> is <code>null</code> then the method just removes
   * the current tool windows pane.
   */
  final void setToolWindowsPane(@Nullable final ToolWindowsPane toolWindowsPane) {
    final JComponent contentPane = (JComponent)getContentPane();
    if(myToolWindowsPane != null){
      contentPane.remove(myToolWindowsPane);
    }

    myToolWindowsPane = toolWindowsPane;
    if(myToolWindowsPane != null) {
      contentPane.add(myToolWindowsPane,BorderLayout.CENTER);
    }

    contentPane.revalidate();
  }

  protected JLayeredPane createLayeredPane() {
    JLayeredPane p = new JBLayeredPane();
    p.setName(this.getName()+".layeredPane");
    return p;
  }

  @Override
  public void setLayout(LayoutManager mgr) {
    //First time mgr comes from createRootLayout(), it's OK. But then Alloy spoils it and breaks FullScreen mode under Windows
    if (getLayout() != null && UIUtil.isUnderAlloyLookAndFeel()) return;
    super.setLayout(mgr);
  }

  protected final Container createContentPane(){
    return myContentPane = new IdePanePanel(new BorderLayout());
  }

  void updateToolbar() {
    if (myToolbar != null) {
      myNorthPanel.remove(myToolbar);
    }
    myToolbar = createToolbar();
    myNorthPanel.add(myToolbar, 0);
    updateToolbarVisibility();
    myContentPane.revalidate();
  }

  void updateNorthComponents() {
    for (IdeRootPaneNorthExtension northComponent : myNorthComponents) {
      northComponent.revalidate();
    }
    myContentPane.revalidate();
  }

  void updateMainMenuActions(){
    ((IdeMenuBar)menuBar).updateMenuActions();
    menuBar.repaint();
  }

  private JComponent createToolbar() {
    ActionGroup group = (ActionGroup)CustomActionsSchema.getInstance().getCorrectedAction(IdeActions.GROUP_MAIN_TOOLBAR);
    final ActionToolbar toolBar= myActionManager.createActionToolbar(
      ActionPlaces.MAIN_TOOLBAR,
      group,
      true
    );
    toolBar.setLayoutPolicy(ActionToolbar.WRAP_LAYOUT_POLICY);

    DefaultActionGroup menuGroup = new DefaultActionGroup();
    menuGroup.add(new ViewToolbarAction());
    menuGroup.add(new CustomizeUIAction());
    PopupHandler.installUnknownPopupHandler(toolBar.getComponent(), menuGroup, myActionManager);

    return toolBar.getComponent();
  }

  private void createStatusBar(IdeFrame frame) {
    myStatusBar = new IdeStatusBarImpl();
    myStatusBar.install(frame);

    myMemoryWidget = new MemoryUsagePanel();

    if (myStatusBarCustomComponentFactories != null) {
      for (final StatusBarCustomComponentFactory<JComponent> componentFactory : myStatusBarCustomComponentFactories) {
        final JComponent c = componentFactory.createComponent(myStatusBar);
        myStatusBar.addWidget(new CustomStatusBarWidget() {
          public JComponent getComponent() {
            return c;
          }

          @NotNull
          public String ID() {
            return c.getClass().getSimpleName();
          }

          public WidgetPresentation getPresentation(@NotNull PlatformType type) {
            return null;
          }

          public void install(@NotNull StatusBar statusBar) {
          }

          public void dispose() {
            componentFactory.disposeComponent(myStatusBar, c);
          }
        }, "before " + MemoryUsagePanel.WIDGET_ID);
      }
    }

    myStatusBar.addWidget(myMemoryWidget);
    myStatusBar.addWidget(new IdeMessagePanel(MessagePool.getInstance()), "before " + MemoryUsagePanel.WIDGET_ID);

    setMemoryIndicatorVisible(myUISettings.SHOW_MEMORY_INDICATOR);
  }

  void setMemoryIndicatorVisible(final boolean visible) {
    if (myMemoryWidget != null) {
      myMemoryWidget.setShowing(visible);
      if (!SystemInfo.isMac) {
        myStatusBar.setBorder(BorderFactory.createEmptyBorder(1, 4, 0, visible ? 0 : 2));
      }
    }
  }

  @Nullable
  final StatusBar getStatusBar() {
    return myStatusBar;
  }

  private void updateToolbarVisibility(){
    myToolbar.setVisible(myUISettings.SHOW_MAIN_TOOLBAR && !UISettings.getInstance().PRESENTATION_MODE);
  }

  private void updateStatusBarVisibility(){
    myStatusBar.setVisible(myUISettings.SHOW_STATUS_BAR && !myUISettings.PRESENTATION_MODE);
  }

  public void installNorthComponents(final Project project) {
    ContainerUtil.addAll(myNorthComponents, Extensions.getExtensions(IdeRootPaneNorthExtension.EP_NAME, project));
    for (IdeRootPaneNorthExtension northComponent : myNorthComponents) {
      myNorthPanel.add(northComponent.getComponent());
      northComponent.uiSettingsChanged(myUISettings);
    }
  }

  public void deinstallNorthComponents(){
    for (IdeRootPaneNorthExtension northComponent : myNorthComponents) {
      myNorthPanel.remove(northComponent.getComponent());
      Disposer.dispose(northComponent);
    }
    myNorthComponents.clear();
  }

  public IdeRootPaneNorthExtension findByName(String name) {
    for (IdeRootPaneNorthExtension northComponent : myNorthComponents) {
      if (Comparing.strEqual(name, northComponent.getKey())) {
        return northComponent;
      }
    }
    return null;
  }

  public void uiSettingsChanged(UISettings source) {
    setMemoryIndicatorVisible(source.SHOW_MEMORY_INDICATOR);
    updateToolbarVisibility();
    updateStatusBarVisibility();
    for (IdeRootPaneNorthExtension component : myNorthComponents) {
      component.uiSettingsChanged(source);
    }
    IdeFrame frame = UIUtil.getParentOfType(IdeFrame.class, this);
    BalloonLayout layout = frame != null ? frame.getBalloonLayout() : null;
    if (layout instanceof BalloonLayoutImpl) ((BalloonLayoutImpl)layout).queueRelayout();
  }

  public ToolWindowsPane getToolWindowsPane() {
    return myToolWindowsPane;
  }

  private class MyRootLayout extends RootLayout {
    public Dimension preferredLayoutSize(Container parent) {
      Dimension rd, mbd;
      Insets i = getInsets();

      if (contentPane != null) {
        rd = contentPane.getPreferredSize();
      }
      else {
        rd = parent.getSize();
      }
      if (menuBar != null && menuBar.isVisible() && !myFullScreen) {
        mbd = menuBar.getPreferredSize();
      }
      else {
        mbd = JBUI.emptySize();
      }
      return new Dimension(Math.max(rd.width, mbd.width) + i.left + i.right,
                           rd.height + mbd.height + i.top + i.bottom);
    }

    public Dimension minimumLayoutSize(Container parent) {
      Dimension rd, mbd;
      Insets i = getInsets();
      if (contentPane != null) {
        rd = contentPane.getMinimumSize();
      }
      else {
        rd = parent.getSize();
      }
      if (menuBar != null && menuBar.isVisible() && !myFullScreen) {
        mbd = menuBar.getMinimumSize();
      }
      else {
        mbd = JBUI.emptySize();
      }
      return new Dimension(Math.max(rd.width, mbd.width) + i.left + i.right,
                           rd.height + mbd.height + i.top + i.bottom);
    }

    public Dimension maximumLayoutSize(Container target) {
      Dimension rd, mbd;
      Insets i = getInsets();
      if (menuBar != null && menuBar.isVisible() && !myFullScreen) {
        mbd = menuBar.getMaximumSize();
      }
      else {
        mbd = JBUI.emptySize();
      }
      if (contentPane != null) {
        rd = contentPane.getMaximumSize();
      }
      else {
        rd = new Dimension(Integer.MAX_VALUE,
                           Integer.MAX_VALUE - i.top - i.bottom - mbd.height - 1);
      }
      return new Dimension(Math.min(rd.width, mbd.width) + i.left + i.right,
                           rd.height + mbd.height + i.top + i.bottom);
    }

    public void layoutContainer(Container parent) {
      Rectangle b = parent.getBounds();
      Insets i = getInsets();
      int contentY = 0;
      int w = b.width - i.right - i.left;
      int h = b.height - i.top - i.bottom;

      if (layeredPane != null) {
        layeredPane.setBounds(i.left, i.top, w, h);
      }
      if (glassPane != null) {
        glassPane.setBounds(i.left, i.top, w, h);
      }
      if (menuBar != null && menuBar.isVisible()) {
        Dimension mbd = menuBar.getPreferredSize();
        menuBar.setBounds(0, 0, w, mbd.height);
        if (!myFullScreen) {
          contentY += mbd.height;
        }
      }
      if (contentPane != null) {
        contentPane.setBounds(0, contentY, w, h - contentY);
      }
    }
  }
}


File: platform/platform-impl/src/com/intellij/ui/components/JBMovePanel.java
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
package com.intellij.ui.components;

import com.intellij.icons.AllIcons;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.impl.ActionButton;
import com.intellij.openapi.actionSystem.impl.PresentationFactory;
import com.intellij.openapi.ui.VerticalFlowLayout;
import com.intellij.ui.IdeBorderFactory;
import com.intellij.ui.ListUtil;
import com.intellij.ui.ScrollPaneFactory;
import com.intellij.util.ui.GridBag;
import com.intellij.util.ui.components.JBPanel;
import org.jetbrains.annotations.NotNull;

import javax.swing.*;
import java.awt.*;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.util.EnumMap;
import java.util.Enumeration;
import java.util.Map;

/**
 * A UI control which consists of two lists with ability to move elements between them.
 * <p/>
 * It looks as <a href="http://openfaces.org/documentation/developersGuide/twolistselection.html">here</a>.
 * 
 * @author Konstantin Bulenkov
 */
public class JBMovePanel extends JBPanel {

  public static final String MOVE_PANEL_PLACE = "MOVE_PANEL";

  public static final InsertPositionStrategy ANCHORING_SELECTION = new InsertPositionStrategy() {
    @Override
    public int getInsertionIndex(@NotNull Object data, @NotNull JList list) {
      int index = list.getSelectedIndex();
      DefaultListModel model = (DefaultListModel)list.getModel();
      return index < 0 ? model.getSize() : index + 1;
    }
  };

  public static final InsertPositionStrategy NATURAL_ORDER = new InsertPositionStrategy() {
    @SuppressWarnings("unchecked")
    @Override
    public int getInsertionIndex(@NotNull Object data, @NotNull JList list) {
      Enumeration elements = ((DefaultListModel)list.getModel()).elements();
      int index = 0;
      while (elements.hasMoreElements()) {
        Object e = elements.nextElement();
        // DefaultListModel is type-aware only since java7, so, use raw types until we're on java6.
        if (((Comparable)e).compareTo(data) >= 0) {
          break;
        }
        index++;
      }
      return index;
    }
  };

  @NotNull private final Map<ButtonType, ActionButton> myButtons = new EnumMap<ButtonType, ActionButton>(ButtonType.class);

  @NotNull private final ListPanel myLeftPanel  = new ListPanel();
  @NotNull private final ListPanel myRightPanel = new ListPanel();

  @NotNull protected final JList        myLeftList;
  @NotNull protected final JList        myRightList;
  @NotNull protected final ActionButton myLeftButton;
  @NotNull protected final ActionButton myAllLeftButton;
  @NotNull protected final ActionButton myRightButton;
  @NotNull protected final ActionButton myAllRightButton;
  @NotNull protected final ActionButton myUpButton;
  @NotNull protected final ActionButton myDownButton;

  @NotNull private InsertPositionStrategy myLeftInsertionStrategy = ANCHORING_SELECTION;
  @NotNull private InsertPositionStrategy myRightInsertionStrategy = ANCHORING_SELECTION;

  private boolean myActivePreferredSizeProcessing;

  public enum ButtonType {LEFT, RIGHT, ALL_LEFT, ALL_RIGHT}

  public JBMovePanel(@NotNull JList left, @NotNull JList right) {
    super(new GridBagLayout());
    assertModelIsEditable(left);
    assertModelIsEditable(right);
    myLeftList = left;
    myRightList = right;

    final JPanel leftRightButtonsPanel = new JPanel(new VerticalFlowLayout(VerticalFlowLayout.MIDDLE));
    leftRightButtonsPanel.add(myRightButton = createButton(ButtonType.RIGHT));
    leftRightButtonsPanel.add(myAllRightButton = createButton(ButtonType.ALL_RIGHT));
    leftRightButtonsPanel.add(myLeftButton = createButton(ButtonType.LEFT));
    leftRightButtonsPanel.add(myAllLeftButton = createButton(ButtonType.ALL_LEFT));

    myUpButton = createButton(new UpAction());
    myDownButton = createButton(new DownAction());
    final JPanel upDownButtonsPanel = new JPanel(new VerticalFlowLayout(VerticalFlowLayout.MIDDLE));
    upDownButtonsPanel.add(myUpButton);
    upDownButtonsPanel.add(myDownButton);

    MouseListener mouseListener = new MouseAdapter() {
      @Override
      public void mouseClicked(MouseEvent e) {
        if (e.getClickCount() != 2 || e.getButton() != MouseEvent.BUTTON1) {
          return;
        }
        if (e.getSource() == myLeftList) {
          doRight();
        }
        else if (e.getSource() == myRightList) {
          doLeft();
        }
      }
    };
    myLeftList.addMouseListener(mouseListener);
    myRightList.addMouseListener(mouseListener);

    GridBag listConstraints = new GridBag().weightx(1).weighty(1).fillCell();
    GridBag buttonConstraints = new GridBag().anchor(GridBagConstraints.CENTER);
    myLeftPanel.add(ScrollPaneFactory.createScrollPane(left), listConstraints);
    add(myLeftPanel, listConstraints);
    add(leftRightButtonsPanel, buttonConstraints);
    myRightPanel.add(ScrollPaneFactory.createScrollPane(right), listConstraints);
    add(myRightPanel, listConstraints);
    add(upDownButtonsPanel, buttonConstraints);
  }

  private static void assertModelIsEditable(@NotNull JList list) {
    assert list.getModel() instanceof DefaultListModel : String
      .format("List model should extends %s interface", DefaultListModel.class.getName());
  }

  public void setShowButtons(@NotNull ButtonType... types) {
    for (ActionButton button : myButtons.values()) {
      button.setVisible(false);
    }
    for (ButtonType type : types) {
      myButtons.get(type).setVisible(true);
    }
  }

  public void setListLabels(@NotNull String left, @NotNull String right) {
    // Border insets are used as a component insets (see JComponent.getInsets()). That's why an ugly bottom inset is used when
    // we create a border with default insets. That is the reason why we explicitly specify bottom inset as zero.
    Insets insets = new Insets(IdeBorderFactory.TITLED_BORDER_TOP_INSET,
                               IdeBorderFactory.TITLED_BORDER_LEFT_INSET,
                               0,
                               IdeBorderFactory.TITLED_BORDER_RIGHT_INSET);
    myLeftPanel.setBorder(IdeBorderFactory.createTitledBorder(left, false, insets));
    myRightPanel.setBorder(IdeBorderFactory.createTitledBorder(right, false, insets));
  }

  public void setLeftInsertionStrategy(@NotNull InsertPositionStrategy leftInsertionStrategy) {
    myLeftInsertionStrategy = leftInsertionStrategy;
  }
  
  // Commented to preserve green code policy until this method is not used. Uncomment when necessary.
  //public void setRightInsertionStrategy(@NotNull InsertPositionStrategy rightInsertionStrategy) {
  //  myRightInsertionStrategy = rightInsertionStrategy;
  //}
  
  @Override
  public void setEnabled(boolean enabled) {
    super.setEnabled(enabled);
    myLeftList.setEnabled(enabled);
    myRightList.setEnabled(enabled);
    for (ActionButton button : myButtons.values()) {
      button.setEnabled(enabled);
    }
  }

  @NotNull
  private ActionButton createButton(@NotNull final ButtonType type) {
    final AnAction action;
    switch (type) {
      case LEFT:
        action = new LeftAction();
        break;
      case RIGHT:
        action = new RightAction();
        break;
      case ALL_LEFT:
        action = new AllLeftAction();
        break;
      case ALL_RIGHT:
        action = new AllRightAction();
        break;
      default: throw new IllegalArgumentException("Unsupported button type: " + type);
    }


    ActionButton button = createButton(action);
    myButtons.put(type, button);
    return button;
  }

  @NotNull
  private static ActionButton createButton(@NotNull final AnAction action) {
    PresentationFactory presentationFactory = new PresentationFactory();
    Icon icon = AllIcons.Actions.AllLeft;
    Dimension size = new Dimension(icon.getIconWidth(), icon.getIconHeight());
    return new ActionButton(action, presentationFactory.getPresentation(action), MOVE_PANEL_PLACE, size);
  }

  protected void doRight() {
    moveBetween(myRightList, myRightInsertionStrategy, myLeftList);
  }

  protected void doLeft() {
    moveBetween(myLeftList, myLeftInsertionStrategy, myRightList);
  }

  protected void doAllLeft() {
    moveAllBetween(myLeftList, myRightList);
  }

  protected void doAllRight() {
    moveAllBetween(myRightList, myLeftList);
  }

  private static void moveBetween(@NotNull JList to, @NotNull InsertPositionStrategy strategy, @NotNull JList from) {
    final int[] indices = from.getSelectedIndices();
    if (indices.length <= 0) {
      return;
    }
    
    final Object[] values = from.getSelectedValues();
    for (int i = indices.length - 1; i >= 0; i--) {
      ((DefaultListModel)from.getModel()).remove(indices[i]);
    }
    if (from.getModel().getSize() > 0) {
      int newSelectionIndex = indices[0];
      newSelectionIndex = Math.min(from.getModel().getSize() - 1, newSelectionIndex);
      from.setSelectedIndex(newSelectionIndex);
    }

    to.clearSelection();
    DefaultListModel toModel = (DefaultListModel)to.getModel();
    int newSelectionIndex = -1;
    for (Object value : values) {
      if (!toModel.contains(value)) {
        int i = strategy.getInsertionIndex(value, to);
        if (newSelectionIndex < 0) {
          newSelectionIndex = i;
        }
        toModel.add(i, value);
        to.addSelectionInterval(i, i);
      }
    }
  }

  private static void moveAllBetween(@NotNull JList to, @NotNull JList from) {
    final DefaultListModel fromModel = (DefaultListModel)from.getModel();
    final DefaultListModel toModel = (DefaultListModel)to.getModel();
    while (fromModel.getSize() > 0) {
      Object element = fromModel.remove(0);
      if (!toModel.contains(element)) {
        toModel.addElement(element);
      }
    }
  }

  public static void main(String[] args) {
    final JBMovePanel panel = new JBMovePanel(new JBList("asdas", "weqrwe", "ads12312", "aZSD23"),
                                              new JBList("123412", "as2341", "aaaaaaaaaaa", "ZZZZZZZZZZ", "12"));
    final JFrame test = new JFrame("Test");
    test.setContentPane(panel);
    test.setSize(500, 500);
    test.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
    test.setVisible(true);
  }
  
  public interface InsertPositionStrategy {
    int getInsertionIndex(@NotNull Object data, @NotNull JList list);
  }

  /**
   * The general idea is to layout target lists to use the same width. This wrapper panel controls that.
   */
  private class ListPanel extends JPanel {

    ListPanel() {
      super(new GridBagLayout());
    }

    @Override
    public Dimension getPreferredSize() {
      Dimension d1 = super.getPreferredSize();
      if (myActivePreferredSizeProcessing) {
        return d1;
      }
      myActivePreferredSizeProcessing = true;
      try {
        final Dimension d2;
        if (myLeftPanel == this) {
          d2 = myRightPanel.getPreferredSize();
        }
        else {
          d2 = myLeftPanel.getPreferredSize();
        }
        return new Dimension(Math.max(d1.width, d2.width), Math.max(d1.height, d2.height));
      }
      finally {
        myActivePreferredSizeProcessing = false;
      }
    }
  }
  
  private class LeftAction extends AnAction {

    LeftAction() {
      getTemplatePresentation().setIcon(AllIcons.Actions.Left);
    }

    @Override
    public void actionPerformed(AnActionEvent e) {
      doLeft(); 
    }
  }

  private class RightAction extends AnAction {

    RightAction() {
      getTemplatePresentation().setIcon(AllIcons.Actions.Right);
    }

    @Override
    public void actionPerformed(AnActionEvent e) {
      doRight();
    }
  }

  private class AllLeftAction extends AnAction {

    AllLeftAction() {
      getTemplatePresentation().setIcon(AllIcons.Actions.AllLeft);
    }

    @Override
    public void actionPerformed(AnActionEvent e) {
      doAllLeft();
    }
  }

  private class AllRightAction extends AnAction {

    AllRightAction() {
      getTemplatePresentation().setIcon(AllIcons.Actions.AllRight);
    }

    @Override
    public void actionPerformed(AnActionEvent e) {
      doAllRight();
    }
  }
  
  private class UpAction extends AnAction {
    
    UpAction() {
      getTemplatePresentation().setIcon(AllIcons.Actions.UP);
    }

    @Override
    public void actionPerformed(AnActionEvent e) {
      ListUtil.moveSelectedItemsUp(myRightList); 
    }
  }

  private class DownAction extends AnAction {

    DownAction() {
      getTemplatePresentation().setIcon(AllIcons.Actions.Down);
    }

    @Override
    public void actionPerformed(AnActionEvent e) {
      ListUtil.moveSelectedItemsDown(myRightList);
    }
  }
}


File: platform/platform-impl/src/com/intellij/ui/components/SliderSelectorAction.java
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
package com.intellij.ui.components;

import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.project.DumbAwareAction;
import com.intellij.openapi.ui.popup.JBPopup;
import com.intellij.openapi.ui.popup.JBPopupFactory;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.Ref;
import com.intellij.ui.awt.RelativePoint;
import com.intellij.util.Consumer;
import com.intellij.util.ui.UIUtil;
import com.intellij.util.ui.components.JBPanel;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.util.Collections;
import java.util.Dictionary;
import java.util.Enumeration;
import java.util.Hashtable;

/**
 * @author Irina.Chernushina on 11/12/2014.
 */
public class SliderSelectorAction extends DumbAwareAction {
  @NotNull private final Configuration myConfiguration;

  public SliderSelectorAction(@Nullable String text, @Nullable String description, @Nullable Icon icon,
                              @NotNull Configuration configuration) {
    super(text, description, icon);
    myConfiguration = configuration;
  }

  @Override
  public void update(@NotNull AnActionEvent e) {
    super.update(e);
    final String tooltip = myConfiguration.getTooltip();
    if (tooltip != null) {
      e.getPresentation().setText(getTemplatePresentation().getText() + " (" + tooltip + ")");
      e.getPresentation().setDescription(getTemplatePresentation().getDescription() + " (" + tooltip + ")");
    }
  }

  @Override
  public void actionPerformed(@NotNull AnActionEvent e) {
    final JPanel result = new JPanel(new BorderLayout());
    final JLabel label = new JLabel(myConfiguration.getSelectText());
    label.setBorder(BorderFactory.createEmptyBorder(4, 4, 0, 0));
    JPanel wrapper = new JPanel(new BorderLayout());
    wrapper.add(label, BorderLayout.NORTH);

    final Dictionary dictionary = myConfiguration.getDictionary();
    final Enumeration elements = dictionary.elements();
    final JSlider slider = new JSlider(SwingConstants.HORIZONTAL, myConfiguration.getMin(), myConfiguration.getMax(), myConfiguration.getSelected()) {
      Integer myWidth = null;
      @Override
      public Dimension getPreferredSize() {
        final Dimension size = super.getPreferredSize();
        if (myWidth == null) {
          myWidth = 10;
          final FontMetrics fm = getFontMetrics(getFont());
          while (elements.hasMoreElements()) {
            String text = ((JLabel)elements.nextElement()).getText();
            myWidth += fm.stringWidth(text + "W");
          }
        }
        return new Dimension(myWidth, size.height);
      }
    };

    slider.setMinorTickSpacing(1);
    slider.setPaintTicks(true);
    slider.setPaintTrack(true);
    slider.setSnapToTicks(true);
    UIUtil.setSliderIsFilled(slider, true);
    slider.setPaintLabels(true);
    slider.setLabelTable(dictionary);

    if (! myConfiguration.isShowOk()) {
      result.add(wrapper, BorderLayout.WEST);
      result.add(slider, BorderLayout.CENTER);
    } else {
      result.add(wrapper, BorderLayout.WEST);
      result.add(slider, BorderLayout.CENTER);
    }

    final Runnable saveSelection = new Runnable() {
      @Override
      public void run() {
        int value = slider.getModel().getValue();
        myConfiguration.getResultConsumer().consume(value);
      }
    };
    final Ref<JBPopup> popupRef = new Ref<JBPopup>(null);
    final JBPopup popup = JBPopupFactory.getInstance().createComponentPopupBuilder(result, slider)
      .setMovable(true)
      .setCancelOnWindowDeactivation(true)
      .setCancelKeyEnabled(myConfiguration.isShowOk())
      .setKeyboardActions(Collections.singletonList(Pair.<ActionListener, KeyStroke>create(new ActionListener() {
        @Override
        public void actionPerformed(ActionEvent e) {
          saveSelection.run();
          popupRef.get().closeOk(null);
        }
      }, KeyStroke.getKeyStroke(KeyEvent.VK_ENTER, 0))))
      .createPopup();

    popupRef.set(popup);
    if (myConfiguration.isShowOk()) {
      final JButton done = new JButton("Done");
      final JBPanel doneWrapper = new JBPanel(new BorderLayout());
      doneWrapper.add(done, BorderLayout.NORTH);
      result.add(doneWrapper, BorderLayout.EAST);
      done.addActionListener(new ActionListener() {
        @Override
        public void actionPerformed(ActionEvent e) {
          saveSelection.run();
          popup.closeOk(null);
        }
      });
    } else {
      popup.setFinalRunnable(saveSelection);
    }
    InputEvent inputEvent = e.getInputEvent();
    show(e, result, popup, inputEvent);
  }

  protected void show(AnActionEvent e, JPanel result, JBPopup popup, InputEvent inputEvent) {
    if (inputEvent instanceof MouseEvent) {
      int width = result.getPreferredSize().width;
      MouseEvent inputEvent1 = (MouseEvent)inputEvent;
      Point point1 = new Point(inputEvent1.getX() - width / 2, inputEvent1.getY());
      RelativePoint point = new RelativePoint(inputEvent1.getComponent(), point1);
      popup.show(point);
    } else {
      popup.showInBestPositionFor(e.getDataContext());
    }
  }

  public static class Configuration {
    @NotNull
    private final String mySelectText;
    @NotNull
    private final Dictionary myDictionary;
    private final int mySelected;
    private final int myMin;
    private final int myMax;
    @NotNull
    private final Consumer<Integer> myResultConsumer;
    private boolean showOk = false;

    public Configuration(int selected, @NotNull Dictionary dictionary, @NotNull String selectText, @NotNull Consumer<Integer> consumer) {
      mySelected = selected;
      myDictionary = new Hashtable<Integer, JComponent>();
      mySelectText = selectText;
      myResultConsumer = consumer;

      int min = 1;
      int max = 0;
      final Enumeration keys = dictionary.keys();
      while (keys.hasMoreElements()) {
        final Integer key = (Integer)keys.nextElement();
        final String value = (String)dictionary.get(key);
        myDictionary.put(key, markLabel(value));
        min = Math.min(min, key);
        max = Math.max(max, key);
      }
      myMin = min;
      myMax = max;
    }

    private static JLabel markLabel(final String text) {
      JLabel label = new JLabel(text);
      label.setFont(UIUtil.getLabelFont());
      return label;
    }

    @NotNull
    public String getSelectText() {
      return mySelectText;
    }

    @NotNull
    public Dictionary getDictionary() {
      return myDictionary;
    }

    @NotNull
    public Consumer<Integer> getResultConsumer() {
      return myResultConsumer;
    }

    public int getSelected() {
      return mySelected;
    }

    public int getMin() {
      return myMin;
    }

    public int getMax() {
      return myMax;
    }

    public boolean isShowOk() {
      return showOk;
    }

    public void setShowOk(boolean showOk) {
      this.showOk = showOk;
    }

    public String getTooltip() {
      return null;
    }
  }
}


File: platform/util/src/com/intellij/util/ui/components/BorderLayoutPanel.java
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
package com.intellij.util.ui.components;

import com.intellij.util.ui.JBUI;

import java.awt.*;

/**
 * @author Konstantin Bulenkov
 */
public class BorderLayoutPanel extends JBPanel<BorderLayoutPanel> {
  public BorderLayoutPanel() {
    this(0, 0);
  }

  public BorderLayoutPanel(int hgap, int vgap) {
    super(new BorderLayout(JBUI.scale(hgap), JBUI.scale(vgap)));
  }

  public BorderLayoutPanel addToCenter(Component comp) {
    add(comp, BorderLayout.CENTER);
    return this;
  }

  public BorderLayoutPanel addToRight(Component comp) {
    add(comp, BorderLayout.EAST);
    return this;
  }

  public BorderLayoutPanel addToLeft(Component comp) {
    add(comp, BorderLayout.WEST);
    return this;
  }

  public BorderLayoutPanel addToTop(Component comp) {
    add(comp, BorderLayout.NORTH);
    return this;
  }

  public BorderLayoutPanel addToBottom(Component comp) {
    add(comp, BorderLayout.SOUTH);
    return this;
  }
}


File: platform/vcs-log/impl/src/com/intellij/vcs/log/impl/VcsLogContentProvider.java
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
package com.intellij.vcs.log.impl;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Condition;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vcs.ProjectLevelVcsManager;
import com.intellij.openapi.vcs.VcsListener;
import com.intellij.openapi.vcs.changes.ui.ChangesViewContentEP;
import com.intellij.openapi.vcs.changes.ui.ChangesViewContentProvider;
import com.intellij.util.Function;
import com.intellij.util.NotNullFunction;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.messages.MessageBusConnection;
import com.intellij.util.ui.components.JBPanel;
import com.intellij.vcs.log.VcsLogSettings;
import com.intellij.vcs.log.data.VcsLogUiProperties;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.*;
import java.util.Arrays;

/**
 * Provides the Content tab to the ChangesView log toolwindow.
 * <p/>
 * Delegates to the VcsLogManager.
 */
public class VcsLogContentProvider implements ChangesViewContentProvider {

  public static final String TAB_NAME = "Log";
  private static final Logger LOG = Logger.getInstance(VcsLogContentProvider.class);

  @NotNull private final Project myProject;
  @NotNull private final VcsLogManager myLogManager;
  @NotNull private final ProjectLevelVcsManager myVcsManager;
  @NotNull private final JPanel myContainer = new JBPanel(new BorderLayout());
  private MessageBusConnection myConnection;

  public VcsLogContentProvider(@NotNull Project project,
                               @NotNull ProjectLevelVcsManager manager,
                               @NotNull VcsLogSettings settings,
                               @NotNull VcsLogUiProperties uiProperties) {
    myProject = project;
    myVcsManager = manager;
    myLogManager = new VcsLogManager(project, settings, uiProperties);
  }

  @Nullable
  public static VcsLogManager findLogManager(@NotNull Project project) {
    final ChangesViewContentEP[] eps = project.getExtensions(ChangesViewContentEP.EP_NAME);
    ChangesViewContentEP ep = ContainerUtil.find(eps, new Condition<ChangesViewContentEP>() {
      @Override
      public boolean value(ChangesViewContentEP ep) {
        return ep.getClassName().equals(VcsLogContentProvider.class.getName());
      }
    });
    if (ep == null) {
      LOG.warn("Proper content provider ep not found among [" + toString(eps) + "]");
      return null;
    }
    ChangesViewContentProvider instance = ep.getInstance(project);
    if (!(instance instanceof VcsLogContentProvider)) {
      LOG.error("Class name matches, but the class doesn't. class name: " + ep.getClassName() + ", class: " + ep.getClass());
      return null;
    }
    VcsLogContentProvider provider = (VcsLogContentProvider)instance;
    return provider.myLogManager;
  }

  @NotNull
  private static String toString(@NotNull ChangesViewContentEP[] eps) {
    return StringUtil.join(eps, new Function<ChangesViewContentEP, String>() {
      @Override
      public String fun(ChangesViewContentEP ep) {
        return String.format("%s-%s-%s", ep.tabName, ep.className, ep.predicateClassName);
      }
    }, ",");
  }

  @Override
  public JComponent initContent() {
    myConnection = myProject.getMessageBus().connect();
    myConnection.subscribe(ProjectLevelVcsManager.VCS_CONFIGURATION_CHANGED, new MyVcsListener());
    initContentInternal();
    return myContainer;
  }

  private void initContentInternal() {
    ApplicationManager.getApplication().assertIsDispatchThread();
    myContainer.add(myLogManager.initContent(Arrays.asList(myVcsManager.getAllVcsRoots()), TAB_NAME), BorderLayout.CENTER);
  }

  @Override
  public void disposeContent() {
    myConnection.disconnect();
    myContainer.removeAll();
    Disposer.dispose(myLogManager);
  }

  private class MyVcsListener implements VcsListener {
    @Override
    public void directoryMappingChanged() {
      ApplicationManager.getApplication().invokeLater(new Runnable() {
        @Override
        public void run() {
          myContainer.removeAll();
          Disposer.dispose(myLogManager);

          initContentInternal();
        }
      });
    }
  }

  public static class VcsLogVisibilityPredicate implements NotNullFunction<Project, Boolean> {
    @NotNull
    @Override
    public Boolean fun(Project project) {
      return !VcsLogManager.findLogProviders(Arrays.asList(ProjectLevelVcsManager.getInstance(project).getAllVcsRoots()), project)
        .isEmpty();
    }
  }
}


File: platform/vcs-log/impl/src/com/intellij/vcs/log/ui/filter/VcsStructureChooser.java
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
package com.intellij.vcs.log.ui.filter;

import com.intellij.ide.util.treeView.AbstractTreeUi;
import com.intellij.ide.util.treeView.NodeDescriptor;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diff.impl.patch.formove.FilePathComparator;
import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory;
import com.intellij.openapi.fileChooser.ex.FileNodeDescriptor;
import com.intellij.openapi.fileChooser.ex.FileSystemTreeImpl;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.module.ModuleManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ModuleRootManager;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.util.Computable;
import com.intellij.openapi.vcs.FilePath;
import com.intellij.openapi.vcs.changes.ui.VirtualFileListCellRenderer;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.ui.*;
import com.intellij.ui.components.JBList;
import com.intellij.ui.components.JBScrollPane;
import com.intellij.ui.treeStructure.Tree;
import com.intellij.util.PlatformIcons;
import com.intellij.util.PlusMinus;
import com.intellij.util.TreeNodeState;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.containers.Convertor;
import com.intellij.util.treeWithCheckedNodes.SelectionManager;
import com.intellij.util.ui.JBUI;
import com.intellij.util.ui.UIUtil;
import com.intellij.util.ui.components.JBPanel;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import javax.swing.border.Border;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.TreeCellRenderer;
import javax.swing.tree.TreePath;
import java.awt.*;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import java.util.*;
import java.util.List;

/**
 * @author irengrig
 *         Date: 2/3/11
 *         Time: 12:04 PM
 */
public class VcsStructureChooser extends DialogWrapper {
  private final static int MAX_FOLDERS = 100;
  public static final Border BORDER = IdeBorderFactory.createBorder(SideBorder.TOP | SideBorder.LEFT);
  public static final String CAN_NOT_ADD_TEXT =
    "<html>Selected: <font color=red>(You have added " + MAX_FOLDERS + " elements. No more is allowed.)</font></html>";
  private static final String VCS_STRUCTURE_CHOOSER_KEY = "git4idea.history.wholeTree.VcsStructureChooser";

  @NotNull private final Project myProject;
  @NotNull private final List<VirtualFile> myInitialRoots;
  @NotNull private final Map<VirtualFile, String> myModulesSet = ContainerUtil.newHashMap();
  @NotNull private final Set<VirtualFile> mySelectedFiles = ContainerUtil.newHashSet();

  @NotNull private final SelectionManager mySelectionManager;

  private Set<VirtualFile> myRoots;
  private JLabel mySelectedLabel;
  private DefaultMutableTreeNode myRoot;
  private Tree myTree;

  public VcsStructureChooser(@NotNull Project project,
                             String title,
                             Collection<VirtualFile> initialSelection,
                             @NotNull List<VirtualFile> initialRoots) {
    super(project, true);
    setTitle(title);
    myProject = project;
    myInitialRoots = initialRoots;
    mySelectionManager = new SelectionManager(MAX_FOLDERS, 500, MyNodeConverter.getInstance());

    init();

    mySelectionManager.setSelection(initialSelection);

    checkEmpty();
  }

  private void calculateRoots() {
    final ModuleManager moduleManager = ModuleManager.getInstance(myProject);
    // assertion for read access inside
    final Module[] modules = ApplicationManager.getApplication().runReadAction(new Computable<Module[]>() {
      public Module[] compute() {
        return moduleManager.getModules();
      }
    });

    final TreeSet<VirtualFile> checkSet = new TreeSet<VirtualFile>(FilePathComparator.getInstance());
    myRoots = new HashSet<VirtualFile>();
    myRoots.addAll(myInitialRoots);
    checkSet.addAll(myInitialRoots);
    for (Module module : modules) {
      final VirtualFile[] files = ModuleRootManager.getInstance(module).getContentRoots();
      for (VirtualFile file : files) {
        final VirtualFile floor = checkSet.floor(file);
        if (floor != null) {
          myModulesSet.put(file, module.getName());
          myRoots.add(file);
        }
      }
    }
  }

  @NotNull
  public Collection<VirtualFile> getSelectedFiles() {
    return mySelectedFiles;
  }

  private void checkEmpty() {
    setOKActionEnabled(!mySelectedFiles.isEmpty());
  }

  @Override
  protected String getDimensionServiceKey() {
    return VCS_STRUCTURE_CHOOSER_KEY;
  }

  @Override
  public JComponent getPreferredFocusedComponent() {
    return myTree;
  }

  @Override
  protected JComponent createCenterPanel() {
    final FileChooserDescriptor descriptor = FileChooserDescriptorFactory.createAllButJarContentsDescriptor();
    calculateRoots();
    final ArrayList<VirtualFile> list = new ArrayList<VirtualFile>(myRoots);
    final Comparator<VirtualFile> comparator = new Comparator<VirtualFile>() {
      @Override
      public int compare(VirtualFile o1, VirtualFile o2) {
        final boolean isDir1 = o1.isDirectory();
        final boolean isDir2 = o2.isDirectory();
        if (isDir1 != isDir2) return isDir1 ? -1 : 1;

        final String module1 = myModulesSet.get(o1);
        final String path1 = module1 != null ? module1 : o1.getPath();
        final String module2 = myModulesSet.get(o2);
        final String path2 = module2 != null ? module2 : o2.getPath();
        return path1.compareToIgnoreCase(path2);
      }
    };
    descriptor.setRoots(list);
    myTree = new Tree();
    myTree.setBorder(BORDER);
    myTree.setShowsRootHandles(true);
    myTree.setRootVisible(true);
    myTree.getExpandableItemsHandler().setEnabled(false);
    final MyCheckboxTreeCellRenderer cellRenderer =
      new MyCheckboxTreeCellRenderer(mySelectionManager, myModulesSet, myProject, myTree, myRoots);
    final FileSystemTreeImpl fileSystemTree =
      new FileSystemTreeImpl(myProject, descriptor, myTree, cellRenderer, null, new Convertor<TreePath, String>() {
        @Override
        public String convert(TreePath o) {
          final DefaultMutableTreeNode lastPathComponent = ((DefaultMutableTreeNode)o.getLastPathComponent());
          final Object uo = lastPathComponent.getUserObject();
          if (uo instanceof FileNodeDescriptor) {
            final VirtualFile file = ((FileNodeDescriptor)uo).getElement().getFile();
            final String module = myModulesSet.get(file);
            if (module != null) return module;
            return file == null ? "" : file.getName();
          }
          return o.toString();
        }
      });
    final AbstractTreeUi ui = fileSystemTree.getTreeBuilder().getUi();
    ui.setNodeDescriptorComparator(new Comparator<NodeDescriptor>() {
      @Override
      public int compare(NodeDescriptor o1, NodeDescriptor o2) {
        if (o1 instanceof FileNodeDescriptor && o2 instanceof FileNodeDescriptor) {
          final VirtualFile f1 = ((FileNodeDescriptor)o1).getElement().getFile();
          final VirtualFile f2 = ((FileNodeDescriptor)o2).getElement().getFile();
          return comparator.compare(f1, f2);
        }
        return o1.getIndex() - o2.getIndex();
      }
    });
    myRoot = (DefaultMutableTreeNode)myTree.getModel().getRoot();

    new ClickListener() {
      @Override
      public boolean onClick(@NotNull MouseEvent e, int clickCount) {
        int row = myTree.getRowForLocation(e.getX(), e.getY());
        if (row < 0) return false;
        final Object o = myTree.getPathForRow(row).getLastPathComponent();
        if (myRoot == o || getFile(o) == null) return false;

        Rectangle rowBounds = myTree.getRowBounds(row);
        cellRenderer.setBounds(rowBounds);
        Rectangle checkBounds = cellRenderer.myCheckbox.getBounds();
        checkBounds.setLocation(rowBounds.getLocation());

        if (checkBounds.height == 0) checkBounds.height = rowBounds.height;

        if (checkBounds.contains(e.getPoint())) {
          mySelectionManager.toggleSelection((DefaultMutableTreeNode)o);
          myTree.revalidate();
          myTree.repaint();
        }
        return true;
      }
    }.installOn(myTree);

    myTree.addKeyListener(new KeyAdapter() {
      public void keyPressed(KeyEvent e) {
        if (e.getKeyCode() == KeyEvent.VK_SPACE) {
          TreePath[] paths = myTree.getSelectionPaths();
          if (paths == null) return;
          for (TreePath path : paths) {
            if (path == null) continue;
            final Object o = path.getLastPathComponent();
            if (myRoot == o || getFile(o) == null) return;
            mySelectionManager.toggleSelection((DefaultMutableTreeNode)o);
          }

          myTree.revalidate();
          myTree.repaint();
          e.consume();
        }
      }
    });

    JBPanel panel = new JBPanel(new BorderLayout());
    panel.add(new JBScrollPane(fileSystemTree.getTree()), BorderLayout.CENTER);
    mySelectedLabel = new JLabel("");
    mySelectedLabel.setBorder(BorderFactory.createEmptyBorder(2, 0, 2, 0));
    panel.add(mySelectedLabel, BorderLayout.SOUTH);

    mySelectionManager.setSelectionChangeListener(new PlusMinus<VirtualFile>() {
      @Override
      public void plus(VirtualFile virtualFile) {
        mySelectedFiles.add(virtualFile);
        recalculateErrorText();
      }

      private void recalculateErrorText() {
        checkEmpty();
        if (mySelectionManager.canAddSelection()) {
          mySelectedLabel.setText("");
        }
        else {
          mySelectedLabel.setText(CAN_NOT_ADD_TEXT);
        }
        mySelectedLabel.revalidate();
      }

      @Override
      public void minus(VirtualFile virtualFile) {
        mySelectedFiles.remove(virtualFile);
        recalculateErrorText();
      }
    });
    panel.setPreferredSize(JBUI.size(400, 300));
    return panel;
  }

  @Nullable
  private static VirtualFile getFile(final Object node) {
    if (!(((DefaultMutableTreeNode)node).getUserObject() instanceof FileNodeDescriptor)) return null;
    final FileNodeDescriptor descriptor = (FileNodeDescriptor)((DefaultMutableTreeNode)node).getUserObject();
    if (descriptor.getElement().getFile() == null) return null;
    return descriptor.getElement().getFile();
  }

  private static class MyCheckboxTreeCellRenderer extends JPanel implements TreeCellRenderer {
    private final WithModulesListCellRenderer myTextRenderer;
    public final JCheckBox myCheckbox;
    private final SelectionManager mySelectionManager;
    private final Map<VirtualFile, String> myModulesSet;
    private final Collection<VirtualFile> myRoots;
    private final ColoredTreeCellRenderer myColoredRenderer;
    private final JLabel myEmpty;
    private final JList myFictive;

    private MyCheckboxTreeCellRenderer(final SelectionManager selectionManager,
                                       Map<VirtualFile, String> modulesSet,
                                       final Project project,
                                       final JTree tree,
                                       final Collection<VirtualFile> roots) {
      super(new BorderLayout());
      mySelectionManager = selectionManager;
      myModulesSet = modulesSet;
      myRoots = roots;
      setBackground(tree.getBackground());
      myColoredRenderer = new ColoredTreeCellRenderer() {
        @Override
        public void customizeCellRenderer(JTree tree,
                                          Object value,
                                          boolean selected,
                                          boolean expanded,
                                          boolean leaf,
                                          int row,
                                          boolean hasFocus) {
          append(value.toString());
        }
      };
      myFictive = new JBList();
      myFictive.setBackground(tree.getBackground());
      myFictive.setSelectionBackground(UIUtil.getListSelectionBackground());
      myFictive.setSelectionForeground(UIUtil.getListSelectionForeground());

      myTextRenderer = new WithModulesListCellRenderer(project, myModulesSet) {
        @Override
        protected void putParentPath(Object value, FilePath path, FilePath self) {
          if (myRoots.contains(self.getVirtualFile())) {
            super.putParentPath(value, path, self);
          }
        }
      };
      myTextRenderer.setBackground(tree.getBackground());

      myCheckbox = new JCheckBox();
      myCheckbox.setBackground(tree.getBackground());
      myEmpty = new JLabel("");

      add(myCheckbox, BorderLayout.WEST);
      add(myTextRenderer, BorderLayout.CENTER);
      myCheckbox.setVisible(true);
    }

    @Override
    public Component getTreeCellRendererComponent(JTree tree,
                                                  Object value,
                                                  boolean selected,
                                                  boolean expanded,
                                                  boolean leaf,
                                                  int row,
                                                  boolean hasFocus) {
      invalidate();
      final VirtualFile file = getFile(value);
      final DefaultMutableTreeNode node = (DefaultMutableTreeNode)value;
      if (file == null) {
        if (value instanceof DefaultMutableTreeNode) {
          final Object uo = node.getUserObject();
          if (uo instanceof String) {
            myColoredRenderer.getTreeCellRendererComponent(tree, value, selected, expanded, leaf, row, hasFocus);
            return myColoredRenderer;
          }
        }
        return myEmpty;
      }
      myCheckbox.setVisible(true);
      final TreeNodeState state = mySelectionManager.getState(node);
      myCheckbox.setEnabled(TreeNodeState.CLEAR.equals(state) || TreeNodeState.SELECTED.equals(state));
      myCheckbox.setSelected(!TreeNodeState.CLEAR.equals(state));
      myCheckbox.setOpaque(false);
      myCheckbox.setBackground(null);
      setBackground(null);
      myTextRenderer.getListCellRendererComponent(myFictive, file, 0, selected, hasFocus);
      revalidate();
      return this;
    }
  }

  private static class MyNodeConverter implements Convertor<DefaultMutableTreeNode, VirtualFile> {
    private final static MyNodeConverter ourInstance = new MyNodeConverter();

    public static MyNodeConverter getInstance() {
      return ourInstance;
    }

    @Override
    public VirtualFile convert(DefaultMutableTreeNode o) {
      return ((FileNodeDescriptor)o.getUserObject()).getElement().getFile();
    }
  }

  private static class WithModulesListCellRenderer extends VirtualFileListCellRenderer {
    private final Map<VirtualFile, String> myModules;

    private WithModulesListCellRenderer(Project project, final Map<VirtualFile, String> modules) {
      super(project, true);
      myModules = modules;
    }

    @Override
    protected String getName(FilePath path) {
      final String module = myModules.get(path.getVirtualFile());
      if (module != null) {
        return module;
      }
      return super.getName(path);
    }

    @Override
    protected void renderIcon(FilePath path) {
      final String module = myModules.get(path.getVirtualFile());
      if (module != null) {
        setIcon(PlatformIcons.CONTENT_ROOT_ICON_CLOSED);
      }
      else {
        if (path.isDirectory()) {
          setIcon(PlatformIcons.DIRECTORY_CLOSED_ICON);
        }
        else {
          setIcon(path.getFileType().getIcon());
        }
      }
    }

    @Override
    protected void putParentPathImpl(Object value, String parentPath, FilePath self) {
      append(self.getPath(), SimpleTextAttributes.GRAYED_ATTRIBUTES);
    }
  }
}


File: plugins/java-decompiler/plugin/src/org/jetbrains/java/decompiler/IdeaDecompiler.java
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
package org.jetbrains.java.decompiler;

import com.intellij.execution.filters.LineNumbersMapping;
import com.intellij.icons.AllIcons;
import com.intellij.ide.highlighter.JavaFileType;
import com.intellij.ide.plugins.PluginManagerCore;
import com.intellij.ide.util.PropertiesComponent;
import com.intellij.openapi.application.Application;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.application.ModalityState;
import com.intellij.openapi.application.ex.ApplicationManagerEx;
import com.intellij.openapi.fileEditor.*;
import com.intellij.openapi.fileTypes.StdFileTypes;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.project.DefaultProjectFactory;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.util.io.FileUtil;
import com.intellij.openapi.util.registry.Registry;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.codeStyle.CodeStyleSettings;
import com.intellij.psi.codeStyle.CodeStyleSettingsManager;
import com.intellij.psi.codeStyle.CommonCodeStyleSettings;
import com.intellij.psi.compiled.ClassFileDecompilers;
import com.intellij.psi.impl.compiled.ClsFileImpl;
import com.intellij.ui.Gray;
import com.intellij.ui.components.JBLabel;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.messages.MessageBusConnection;
import com.intellij.util.ui.JBUI;
import com.intellij.util.ui.UIUtil;
import com.intellij.util.ui.components.JBPanel;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.annotations.TestOnly;
import org.jetbrains.java.decompiler.main.decompiler.BaseDecompiler;
import org.jetbrains.java.decompiler.main.extern.IBytecodeProvider;
import org.jetbrains.java.decompiler.main.extern.IFernflowerLogger;
import org.jetbrains.java.decompiler.main.extern.IFernflowerPreferences;
import org.jetbrains.java.decompiler.main.extern.IResultSaver;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.io.File;
import java.io.IOException;
import java.util.Collections;
import java.util.Map;
import java.util.jar.Manifest;

public class IdeaDecompiler extends ClassFileDecompilers.Light {
  public static final String BANNER =
    "//\n" +
    "// Source code recreated from a .class file by IntelliJ IDEA\n" +
    "// (powered by Fernflower decompiler)\n" +
    "//\n\n";

  private static final String LEGAL_NOTICE_KEY = "decompiler.legal.notice.accepted";

  private final IFernflowerLogger myLogger = new IdeaLogger();
  private final Map<String, Object> myOptions;
  private final Map<VirtualFile, ProgressIndicator> myProgress = ContainerUtil.newConcurrentMap();
  private boolean myLegalNoticeAccepted;

  public IdeaDecompiler() {
    Map<String, Object> options = ContainerUtil.newHashMap();
    options.put(IFernflowerPreferences.HIDE_DEFAULT_CONSTRUCTOR, "0");
    options.put(IFernflowerPreferences.DECOMPILE_GENERIC_SIGNATURES, "1");
    options.put(IFernflowerPreferences.REMOVE_SYNTHETIC, "1");
    options.put(IFernflowerPreferences.REMOVE_BRIDGE, "1");
    options.put(IFernflowerPreferences.LITERALS_AS_IS, "1");
    options.put(IFernflowerPreferences.NEW_LINE_SEPARATOR, "1");
    options.put(IFernflowerPreferences.BANNER, BANNER);
    options.put(IFernflowerPreferences.MAX_PROCESSING_METHOD, 60);

    Project project = DefaultProjectFactory.getInstance().getDefaultProject();
    CodeStyleSettings settings = CodeStyleSettingsManager.getInstance(project).getCurrentSettings();
    CommonCodeStyleSettings.IndentOptions indentOptions = settings.getIndentOptions(JavaFileType.INSTANCE);
    options.put(IFernflowerPreferences.INDENT_STRING, StringUtil.repeat(" ", indentOptions.INDENT_SIZE));

    Application app = ApplicationManager.getApplication();
    myLegalNoticeAccepted = app.isUnitTestMode() || PropertiesComponent.getInstance().isValueSet(LEGAL_NOTICE_KEY);
    if (!myLegalNoticeAccepted) {
      MessageBusConnection connection = app.getMessageBus().connect(app);
      connection.subscribe(FileEditorManagerListener.FILE_EDITOR_MANAGER, new FileEditorManagerAdapter() {
        @Override
        public void fileOpened(@NotNull FileEditorManager source, @NotNull VirtualFile file) {
          if (file.getFileType() == StdFileTypes.CLASS) {
            FileEditor editor = source.getSelectedEditor(file);
            if (editor instanceof TextEditor) {
              CharSequence text = ((TextEditor)editor).getEditor().getDocument().getImmutableCharSequence();
              if (StringUtil.startsWith(text, BANNER)) {
                showLegalNotice(source.getProject(), file);
              }
            }
          }
        }
      });
    }

    if (app.isUnitTestMode()) {
      options.put(IFernflowerPreferences.UNIT_TEST_MODE, "1");
    }

    myOptions = Collections.unmodifiableMap(options);
  }

  private void showLegalNotice(final Project project, final VirtualFile file) {
    if (!myLegalNoticeAccepted) {
      ApplicationManager.getApplication().invokeLater(new Runnable() {
        @Override
        public void run() {
          if (!myLegalNoticeAccepted) {
            new LegalNoticeDialog(project, file).show();
          }
        }
      }, ModalityState.NON_MODAL);
    }
  }

  @Override
  public boolean accepts(@NotNull VirtualFile file) {
    return true;
  }

  @NotNull
  @Override
  public CharSequence getText(@NotNull VirtualFile file) throws CannotDecompileException {
    if ("package-info.class".equals(file.getName())) {
      return ClsFileImpl.decompile(file);
    }

    ProgressIndicator indicator = ProgressManager.getInstance().getProgressIndicator();
    if (indicator != null) myProgress.put(file, indicator);

    try {
      Map<String, VirtualFile> files = ContainerUtil.newLinkedHashMap();
      files.put(file.getPath(), file);
      String mask = file.getNameWithoutExtension() + "$";
      for (VirtualFile child : file.getParent().getChildren()) {
        String name = child.getNameWithoutExtension();
        if (name.startsWith(mask) && name.length() > mask.length() && file.getFileType() == StdFileTypes.CLASS) {
          files.put(FileUtil.toSystemIndependentName(child.getPath()), child);
        }
      }
      MyBytecodeProvider provider = new MyBytecodeProvider(files);
      MyResultSaver saver = new MyResultSaver();

      Map<String, Object> options = ContainerUtil.newHashMap(myOptions);
      if (Registry.is("decompiler.use.line.mapping")) {
        options.put(IFernflowerPreferences.BYTECODE_SOURCE_MAPPING, "1");
        options.put(IFernflowerPreferences.USE_DEBUG_LINE_NUMBERS, "0");
      }
      else if (Registry.is("decompiler.use.line.table")) {
        options.put(IFernflowerPreferences.BYTECODE_SOURCE_MAPPING, "0");
        options.put(IFernflowerPreferences.USE_DEBUG_LINE_NUMBERS, "1");
      }
      else {
        options.put(IFernflowerPreferences.BYTECODE_SOURCE_MAPPING, "0");
        options.put(IFernflowerPreferences.USE_DEBUG_LINE_NUMBERS, "0");
      }
      if (Registry.is("decompiler.dump.original.lines")) {
        options.put(IFernflowerPreferences.DUMP_ORIGINAL_LINES, "1");
      }

      BaseDecompiler decompiler = new BaseDecompiler(provider, saver, options, myLogger);
      for (String path : files.keySet()) {
        decompiler.addSpace(new File(path), true);
      }
      decompiler.decompileContext();

      if (saver.myMapping != null) {
        file.putUserData(LineNumbersMapping.LINE_NUMBERS_MAPPING_KEY, new ExactMatchLineNumbersMapping(saver.myMapping));
      }

      return saver.myResult;
    }
    catch (ProcessCanceledException e) {
      throw e;
    }
    catch (Exception e) {
      if (ApplicationManager.getApplication().isUnitTestMode()) {
        AssertionError error = new AssertionError(file.getUrl());
        error.initCause(e);
        throw error;
      }
      else {
        throw new CannotDecompileException(e);
      }
    }
    finally {
      myProgress.remove(file);
    }
  }

  @TestOnly
  @Nullable
  public ProgressIndicator getProgress(@NotNull VirtualFile file) {
    return myProgress.get(file);
  }

  private static class MyBytecodeProvider implements IBytecodeProvider {
    private final Map<String, VirtualFile> myFiles;

    private MyBytecodeProvider(@NotNull Map<String, VirtualFile> files) {
      myFiles = files;
    }

    @Override
    public byte[] getBytecode(String externalPath, String internalPath) {
      try {
        String path = FileUtil.toSystemIndependentName(externalPath);
        VirtualFile file = myFiles.get(path);
        assert file != null : path + " not in " + myFiles.keySet();
        return file.contentsToByteArray();
      }
      catch (IOException e) {
        throw new RuntimeException(e);
      }
    }
  }

  private static class MyResultSaver implements IResultSaver {
    private String myResult = "";
    private int[] myMapping = null;

    @Override
    public void saveClassFile(String path, String qualifiedName, String entryName, String content, int[] mapping) {
      if (myResult.isEmpty()) {
        myResult = content;
        myMapping = mapping;
      }
    }

    @Override
    public void saveFolder(String path) { }

    @Override
    public void copyFile(String source, String path, String entryName) { }

    @Override
    public void createArchive(String path, String archiveName, Manifest manifest) { }

    @Override
    public void saveDirEntry(String path, String archiveName, String entryName) { }

    @Override
    public void copyEntry(String source, String path, String archiveName, String entry) { }

    @Override
    public void saveClassEntry(String path, String archiveName, String qualifiedName, String entryName, String content) { }

    @Override
    public void closeArchive(String path, String archiveName) { }
  }

  private class LegalNoticeDialog extends DialogWrapper {
    private final Project myProject;
    private final VirtualFile myFile;
    private JEditorPane myMessage;

    public LegalNoticeDialog(Project project, VirtualFile file) {
      super(project);
      myProject = project;
      myFile = file;
      setTitle(IdeaDecompilerBundle.message("legal.notice.title"));
      setOKButtonText(IdeaDecompilerBundle.message("legal.notice.action.accept"));
      setCancelButtonText(IdeaDecompilerBundle.message("legal.notice.action.postpone"));
      init();
      pack();
    }

    @Nullable
    @Override
    protected JComponent createCenterPanel() {
      JPanel iconPanel = new JBPanel(new BorderLayout());
      iconPanel.add(new JBLabel(AllIcons.General.WarningDialog), BorderLayout.NORTH);

      myMessage = new JEditorPane();
      myMessage.setEditorKit(UIUtil.getHTMLEditorKit());
      myMessage.setEditable(false);
      myMessage.setPreferredSize(JBUI.size(500, 100));
      myMessage.setBorder(BorderFactory.createLineBorder(Gray._200));
      String text = "<div style='margin:5px;'>" + IdeaDecompilerBundle.message("legal.notice.text") + "</div>";
      myMessage.setText(text);

      JPanel panel = new JBPanel(new BorderLayout(10, 0));
      panel.add(iconPanel, BorderLayout.WEST);
      panel.add(myMessage, BorderLayout.CENTER);
      return panel;
    }

    @NotNull
    @Override
    protected Action[] createActions() {
      DialogWrapperAction decline = new DialogWrapperAction(IdeaDecompilerBundle.message("legal.notice.action.reject")) {
        @Override
        protected void doAction(ActionEvent e) {
          doDeclineAction();
        }
      };
      return new Action[]{getOKAction(), decline, getCancelAction()};
    }

    @Nullable
    @Override
    public JComponent getPreferredFocusedComponent() {
      return myMessage;
    }

    @Override
    protected void doOKAction() {
      super.doOKAction();
      PropertiesComponent.getInstance().setValue(LEGAL_NOTICE_KEY, Boolean.TRUE.toString());
      myLegalNoticeAccepted = true;
    }

    private void doDeclineAction() {
      doCancelAction();
      PluginManagerCore.disablePlugin("org.jetbrains.java.decompiler");
      ApplicationManagerEx.getApplicationEx().restart(true);
    }

    @Override
    public void doCancelAction() {
      super.doCancelAction();
      FileEditorManager.getInstance(myProject).closeFile(myFile);
    }
  }

  private static class ExactMatchLineNumbersMapping implements LineNumbersMapping {
    private final int[] myMapping;

    private ExactMatchLineNumbersMapping(@NotNull int[] mapping) {
      myMapping = mapping;
    }

    @Override
    public int bytecodeToSource(int line) {
      for (int i = 0; i < myMapping.length; i += 2) {
        if (myMapping[i] == line) {
          return myMapping[i + 1];
        }
      }
      return -1;
    }

    @Override
    public int sourceToBytecode(int line) {
      for (int i = 0; i < myMapping.length; i += 2) {
        if (myMapping[i + 1] == line) {
          return myMapping[i];
        }
      }
      return -1;
    }
  }
}


File: xml/impl/src/com/intellij/codeInsight/template/emmet/EmmetPreviewHint.java
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
package com.intellij.codeInsight.template.emmet;

import com.intellij.codeInsight.hint.HintManager;
import com.intellij.codeInsight.hint.HintManagerImpl;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.editor.*;
import com.intellij.openapi.editor.event.DocumentAdapter;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.editor.event.EditorFactoryAdapter;
import com.intellij.openapi.editor.event.EditorFactoryEvent;
import com.intellij.openapi.editor.ex.EditorEx;
import com.intellij.openapi.editor.ex.EditorMarkupModel;
import com.intellij.openapi.editor.ex.MarkupModelEx;
import com.intellij.openapi.fileTypes.FileType;
import com.intellij.openapi.ui.popup.Balloon;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.psi.impl.source.tree.injected.InjectedLanguageUtil;
import com.intellij.ui.HintHint;
import com.intellij.ui.IdeBorderFactory;
import com.intellij.ui.LightweightHint;
import com.intellij.util.Alarm;
import com.intellij.util.DocumentUtil;
import com.intellij.util.Producer;
import com.intellij.util.ui.components.JBPanel;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.annotations.TestOnly;

import javax.swing.*;
import java.awt.*;

public class EmmetPreviewHint extends LightweightHint implements Disposable {
  private static final Key<EmmetPreviewHint> KEY = new Key<EmmetPreviewHint>("emmet.preview");
  @NotNull private final Editor myParentEditor;
  @NotNull private final Editor myEditor;
  @NotNull private final Alarm myAlarm = new Alarm(this);
  private boolean isDisposed = false;

  private EmmetPreviewHint(@NotNull JBPanel panel, @NotNull Editor editor, @NotNull Editor parentEditor) {
    super(panel);
    myParentEditor = parentEditor;
    myEditor = editor;

    final Editor topLevelEditor = InjectedLanguageUtil.getTopLevelEditor(myParentEditor);
    EditorFactory.getInstance().addEditorFactoryListener(new EditorFactoryAdapter() {
      @Override
      public void editorReleased(@NotNull EditorFactoryEvent event) {
        if (event.getEditor() == myParentEditor || event.getEditor() == myEditor || event.getEditor() == topLevelEditor) {
          hide(true);
        }
      }
    }, this);

    myEditor.getDocument().addDocumentListener(new DocumentAdapter() {
      @Override
      public void documentChanged(DocumentEvent event) {
        if (!isDisposed && event.isWholeTextReplaced()) {
          Pair<Point, Short> position = guessPosition();
          HintManagerImpl.adjustEditorHintPosition(EmmetPreviewHint.this, myParentEditor, position.first, position.second);
          myEditor.getScrollingModel().scrollVertically(0);
        }
      }
    }, this);
  }

  public void showHint() {
    myParentEditor.putUserData(KEY, this);

    Pair<Point, Short> position = guessPosition();
    JRootPane pane = myParentEditor.getComponent().getRootPane();
    JComponent layeredPane = pane != null ? pane.getLayeredPane() : myParentEditor.getComponent();
    HintHint hintHint = new HintHint(layeredPane, position.first)
      .setAwtTooltip(true)
      .setContentActive(true)
      .setExplicitClose(true)
      .setShowImmediately(true)
      .setPreferredPosition(position.second == HintManager.ABOVE ? Balloon.Position.above : Balloon.Position.below)
      .setTextBg(myParentEditor.getColorsScheme().getDefaultBackground())
      .setBorderInsets(new Insets(1, 1, 1, 1));

    int hintFlags = HintManager.HIDE_BY_OTHER_HINT | HintManager.HIDE_BY_ESCAPE | HintManager.UPDATE_BY_SCROLLING;
    HintManagerImpl.getInstanceImpl().showEditorHint(this, myParentEditor, position.first, hintFlags, 0, false, hintHint);
  }

  public void updateText(@NotNull final Producer<String> contentProducer) {
    myAlarm.cancelAllRequests();
    myAlarm.addRequest(new Runnable() {
      @Override
      public void run() {
        if (!isDisposed) {
          final String newText = contentProducer.produce();
          if (StringUtil.isEmpty(newText)) {
            hide();
          }
          else if (!myEditor.getDocument().getText().equals(newText)) {
            DocumentUtil.writeInRunUndoTransparentAction(new Runnable() {
              @Override
              public void run() {
                myEditor.getDocument().setText(newText);
              }
            });
          }
        }
      }
    }, 100);
  }

  @TestOnly
  @NotNull
  public String getContent() {
    return myEditor.getDocument().getText();
  }

  @Nullable
  public static EmmetPreviewHint getExistingHint(@NotNull Editor parentEditor) {
    EmmetPreviewHint emmetPreviewHint = KEY.get(parentEditor);
    if (emmetPreviewHint != null) {
      if (!emmetPreviewHint.isDisposed) {
        return emmetPreviewHint;
      }
      emmetPreviewHint.hide();
    }
    return null;
  }

  @NotNull
  public static EmmetPreviewHint createHint(@NotNull final EditorEx parentEditor,
                                            @NotNull String templateText,
                                            @NotNull FileType fileType) {
    EditorFactory editorFactory = EditorFactory.getInstance();
    Document document = editorFactory.createDocument(templateText);
    final EditorEx previewEditor = (EditorEx)editorFactory.createEditor(document, parentEditor.getProject(), fileType, true);
    MarkupModelEx model = previewEditor.getMarkupModel();
    if (model instanceof EditorMarkupModel) {
      ((EditorMarkupModel)model).setErrorStripeVisible(true);
    }
    final EditorSettings settings = previewEditor.getSettings();
    settings.setLineNumbersShown(false);
    settings.setAdditionalLinesCount(1);
    settings.setAdditionalColumnsCount(1);
    settings.setRightMarginShown(false);
    settings.setFoldingOutlineShown(false);
    settings.setLineMarkerAreaShown(false);
    settings.setIndentGuidesShown(false);
    settings.setVirtualSpace(false);
    settings.setWheelFontChangeEnabled(false);
    settings.setAdditionalPageAtBottom(false);
    settings.setCaretRowShown(false);
    previewEditor.setCaretEnabled(false);
    previewEditor.setBorder(IdeBorderFactory.createEmptyBorder());

    JBPanel panel = new JBPanel(new BorderLayout()) {
      @NotNull
      @Override
      public Dimension getPreferredSize() {
        Dimension size = super.getPreferredSize();
        Dimension parentEditorSize = parentEditor.getScrollPane().getSize();
        int maxWidth = (int)parentEditorSize.getWidth() / 3;
        int maxHeight = (int)parentEditorSize.getHeight() / 2;
        final int width = settings.isUseSoftWraps() ? maxWidth : Math.min((int)size.getWidth(), maxWidth);
        final int height = Math.min((int)size.getHeight(), maxHeight);
        return new Dimension(width, height);
      }

      @NotNull
      @Override
      public Insets getInsets() {
        return new Insets(1, 2, 0, 0);
      }
    };
    panel.setBackground(previewEditor.getBackgroundColor());
    panel.add(previewEditor.getComponent(), BorderLayout.CENTER);
    return new EmmetPreviewHint(panel, previewEditor, parentEditor);
  }

  @Override
  public boolean vetoesHiding() {
    return true;
  }

  @Override
  public void hide(boolean ok) {
    super.hide(ok);
    ApplicationManager.getApplication().invokeLater(new Runnable() {
      @Override
      public void run() {
        Disposer.dispose(EmmetPreviewHint.this);
      }
    });
  }

  @Override
  public void dispose() {
    isDisposed = true;
    myAlarm.cancelAllRequests();
    EmmetPreviewHint existingBalloon = myParentEditor.getUserData(KEY);
    if (existingBalloon == this) {
      myParentEditor.putUserData(KEY, null);
    }
    if (!myEditor.isDisposed()) {
      EditorFactory.getInstance().releaseEditor(myEditor);
    }
  }

  @NotNull
  private Pair<Point, Short> guessPosition() {
    JRootPane rootPane = myParentEditor.getContentComponent().getRootPane();
    JComponent layeredPane = rootPane != null ? rootPane.getLayeredPane() : myParentEditor.getComponent();
    LogicalPosition logicalPosition = myParentEditor.getCaretModel().getLogicalPosition();

    LogicalPosition pos = new LogicalPosition(logicalPosition.line, logicalPosition.column);
    Point p1 = HintManagerImpl.getHintPosition(this, myParentEditor, pos, HintManager.UNDER);
    Point p2 = HintManagerImpl.getHintPosition(this, myParentEditor, pos, HintManager.ABOVE);

    boolean p1Ok = p1.y + getComponent().getPreferredSize().height < layeredPane.getHeight();
    boolean p2Ok = p2.y >= 0;

    if (p1Ok) return new Pair<Point, Short>(p1, HintManager.UNDER);
    if (p2Ok) return new Pair<Point, Short>(p2, HintManager.ABOVE);

    int underSpace = layeredPane.getHeight() - p1.y;
    int aboveSpace = p2.y;
    return aboveSpace > underSpace
           ? new Pair<Point, Short>(new Point(p2.x, 0), HintManager.UNDER)
           : new Pair<Point, Short>(p1, HintManager.ABOVE);
  }
}
