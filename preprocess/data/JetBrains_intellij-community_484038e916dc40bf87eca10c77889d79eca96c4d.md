Refactoring Types: ['Extract Method']
ellij/compiler/options/AnnotationProcessorsPanel.java
/*
 * Copyright 2000-2012 JetBrains s.r.o.
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
package com.intellij.compiler.options;

import com.intellij.icons.AllIcons;
import com.intellij.openapi.actionSystem.ActionManager;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.ShortcutSet;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.module.ModuleManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.InputValidatorEx;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.ui.Splitter;
import com.intellij.openapi.ui.popup.JBPopup;
import com.intellij.openapi.ui.popup.JBPopupFactory;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.ui.AnActionButton;
import com.intellij.ui.ColoredTreeCellRenderer;
import com.intellij.ui.IdeBorderFactory;
import com.intellij.ui.ToolbarDecorator;
import com.intellij.ui.awt.RelativePoint;
import com.intellij.ui.components.JBList;
import com.intellij.ui.treeStructure.Tree;
import com.intellij.util.ui.EditableTreeModel;
import com.intellij.util.ui.tree.TreeUtil;
import org.jetbrains.jps.model.java.compiler.ProcessorConfigProfile;
import org.jetbrains.jps.model.java.impl.compiler.ProcessorConfigProfileImpl;

import javax.swing.*;
import javax.swing.event.TreeSelectionEvent;
import javax.swing.event.TreeSelectionListener;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.DefaultTreeModel;
import javax.swing.tree.TreePath;
import java.awt.*;
import java.awt.event.MouseEvent;
import java.util.*;
import java.util.List;

/**
 * @author Konstantin Bulenkov
 */
@SuppressWarnings({"unchecked", "UseOfObsoleteCollectionType"})
public class AnnotationProcessorsPanel extends JPanel {
  private final ProcessorConfigProfile myDefaultProfile = new ProcessorConfigProfileImpl("");
  private final List<ProcessorConfigProfile> myModuleProfiles = new ArrayList<ProcessorConfigProfile>();
  private final Map<String, Module> myAllModulesMap = new HashMap<String, Module>();
  private final Project myProject;
  private final Tree myTree;
  private final ProcessorProfilePanel myProfilePanel;
  private ProcessorConfigProfile mySelectedProfile = null;

  public AnnotationProcessorsPanel(Project project) {
    super(new BorderLayout());
    Splitter splitter = new Splitter(false, 0.3f);
    add(splitter, BorderLayout.CENTER);
    myProject = project;
    for (Module module : ModuleManager.getInstance(project).getModules()) {
      myAllModulesMap.put(module.getName(), module);
    }
    myTree = new Tree(new MyTreeModel());
    myTree.setRootVisible(false);
        final JPanel treePanel =
          ToolbarDecorator.createDecorator(myTree).addExtraAction(new AnActionButton("Move to", AllIcons.Actions.Nextfile) {
            @Override
            public void actionPerformed(AnActionEvent e) {
              final MyModuleNode node = (MyModuleNode)myTree.getSelectionPath().getLastPathComponent();
              final TreePath[] selectedNodes = myTree.getSelectionPaths();
              final ProcessorConfigProfile nodeProfile = ((ProfileNode)node.getParent()).myProfile;
              final List<ProcessorConfigProfile> profiles = new ArrayList<ProcessorConfigProfile>();
              profiles.add(myDefaultProfile);
              for (ProcessorConfigProfile profile : myModuleProfiles) {
                profiles.add(profile);
              }
              profiles.remove(nodeProfile);
              final JBList list = new JBList(profiles);
              final JBPopup popup = JBPopupFactory.getInstance().createListPopupBuilder(list)
                .setTitle("Move to")
                .setItemChoosenCallback(new Runnable() {
                  @Override
                  public void run() {
                    final Object value = list.getSelectedValue();
                    if (value instanceof ProcessorConfigProfile) {
                      final ProcessorConfigProfile chosenProfile = (ProcessorConfigProfile)value;
                      final Module toSelect = (Module)node.getUserObject();
                      if (selectedNodes != null) {
                        for (TreePath selectedNode : selectedNodes) {
                          final Object node = selectedNode.getLastPathComponent();
                          if (node instanceof MyModuleNode) {
                            final Module module = (Module)((MyModuleNode)node).getUserObject();
                            if (nodeProfile != myDefaultProfile) {
                              nodeProfile.removeModuleName(module.getName());
                            }
                            if (chosenProfile != myDefaultProfile) {
                              chosenProfile.addModuleName(module.getName());
                            }
                          }
                        }
                      }

                      final RootNode root = (RootNode)myTree.getModel().getRoot();
                      root.sync();
                      final DefaultMutableTreeNode node = TreeUtil.findNodeWithObject(root, toSelect);
                      if (node != null) {
                        TreeUtil.selectNode(myTree, node);
                      }
                    }
                  }
                })
                .createPopup();
              RelativePoint point =
                e.getInputEvent() instanceof MouseEvent ? getPreferredPopupPoint() : TreeUtil.getPointForSelection(myTree);
              popup.show(point);
            }

            @Override
            public ShortcutSet getShortcut() {
              return ActionManager.getInstance().getAction("Move").getShortcutSet();
            }

            @Override
            public boolean isEnabled() {
              return myTree.getSelectionPath() != null
                     && myTree.getSelectionPath().getLastPathComponent() instanceof MyModuleNode
                     && !myModuleProfiles.isEmpty();
            }
          }).createPanel();
    splitter.setFirstComponent(treePanel);
    myTree.setCellRenderer(new MyCellRenderer());

    myTree.addTreeSelectionListener(new TreeSelectionListener() {
      @Override
      public void valueChanged(TreeSelectionEvent e) {
        final TreePath path = myTree.getSelectionPath();
        if (path != null) {
          Object node = path.getLastPathComponent();
          if (node instanceof MyModuleNode) {
            node = ((MyModuleNode)node).getParent();
          }
          if (node instanceof ProfileNode) {
            final ProcessorConfigProfile nodeProfile = ((ProfileNode)node).myProfile;
            final ProcessorConfigProfile selectedProfile = mySelectedProfile;
            if (nodeProfile != selectedProfile) {
              if (selectedProfile != null) {
                myProfilePanel.saveTo(selectedProfile);
              }
              mySelectedProfile = nodeProfile;
              myProfilePanel.setProfile(nodeProfile);
            }
          }
        }
      }
    });
    myProfilePanel = new ProcessorProfilePanel(project);
    myProfilePanel.setBorder(IdeBorderFactory.createEmptyBorder(0, 6, 0, 0));
    splitter.setSecondComponent(myProfilePanel);
  }

  public void initProfiles(ProcessorConfigProfile defaultProfile, Collection<ProcessorConfigProfile> moduleProfiles) {
    myDefaultProfile.initFrom(defaultProfile);
    myModuleProfiles.clear();
    for (ProcessorConfigProfile profile : moduleProfiles) {
      ProcessorConfigProfile copy = new ProcessorConfigProfileImpl("");
      copy.initFrom(profile);
      myModuleProfiles.add(copy);
    }
    final RootNode root = (RootNode)myTree.getModel().getRoot();
    root.sync();
    final DefaultMutableTreeNode node = TreeUtil.findNodeWithObject(root, myDefaultProfile);
    if (node != null) {
      TreeUtil.selectNode(myTree, node);
    }

  }

  public ProcessorConfigProfile getDefaultProfile() {
    final ProcessorConfigProfile selectedProfile = mySelectedProfile;
    if (myDefaultProfile == selectedProfile) {
      myProfilePanel.saveTo(selectedProfile);
    }
    return myDefaultProfile;
  }

  public List<ProcessorConfigProfile> getModuleProfiles() {
    final ProcessorConfigProfile selectedProfile = mySelectedProfile;
    if (myDefaultProfile != selectedProfile) {
      myProfilePanel.saveTo(selectedProfile);
    }
    return myModuleProfiles;
  }

  private static void expand(JTree tree) {
    int oldRowCount = 0;
    do {
      int rowCount = tree.getRowCount();
      if (rowCount == oldRowCount) break;
      oldRowCount = rowCount;
      for (int i = 0; i < rowCount; i++) {
        tree.expandRow(i);
      }
    }
    while (true);
  }

  private class MyTreeModel extends DefaultTreeModel implements EditableTreeModel{
    public MyTreeModel() {
      super(new RootNode());
    }

    @Override
    public TreePath addNode(TreePath parentOrNeighbour) {
      final String newProfileName = Messages.showInputDialog(
        myProject, "Profile name", "Create new profile", null, "",
        new InputValidatorEx() {
          @Override
          public boolean checkInput(String inputString) {
            if (StringUtil.isEmpty(inputString) ||
                Comparing.equal(inputString, myDefaultProfile.getName())) {
              return false;
            }
            for (ProcessorConfigProfile profile : myModuleProfiles) {
              if (Comparing.equal(inputString, profile.getName())) {
                return false;
              }
            }
            return true;
          }

          @Override
          public boolean canClose(String inputString) {
            return checkInput(inputString);
          }

          @Override
          public String getErrorText(String inputString) {
            if (checkInput(inputString)) {
              return null;
            }
            return StringUtil.isEmpty(inputString)
                   ? "Profile name shouldn't be empty"
                   : "Profile " + inputString + " already exists";
          }
        });
      if (newProfileName != null) {
        final ProcessorConfigProfile profile = new ProcessorConfigProfileImpl(newProfileName);
        myModuleProfiles.add(profile);
        ((DataSynchronizable)getRoot()).sync();
        final DefaultMutableTreeNode object = TreeUtil.findNodeWithObject((DefaultMutableTreeNode)getRoot(), profile);
        if (object != null) {
          TreeUtil.selectNode(myTree, object);
        }
      }
      return null;
    }

    @Override
    public void removeNode(TreePath nodePath) {
      Object node = nodePath.getLastPathComponent();
      if (node instanceof ProfileNode) {
        final ProcessorConfigProfile nodeProfile = ((ProfileNode)node).myProfile;
        if (nodeProfile != myDefaultProfile) {
          if (mySelectedProfile == nodeProfile) {
            mySelectedProfile = null;
          }
          myModuleProfiles.remove(nodeProfile);
          ((DataSynchronizable)getRoot()).sync();
          final DefaultMutableTreeNode object = TreeUtil.findNodeWithObject((DefaultMutableTreeNode)getRoot(), myDefaultProfile);
          if (object != null) {
            TreeUtil.selectNode(myTree, object);
          }
        }
      }
    }

    @Override
    public void moveNodeTo(TreePath parentOrNeighbour) {
    }

  }


  private class RootNode extends DefaultMutableTreeNode implements DataSynchronizable {
    @Override
    public DataSynchronizable sync() {
      final Vector newKids =  new Vector();
      newKids.add(new ProfileNode(myDefaultProfile, this, true).sync());
      for (ProcessorConfigProfile profile : myModuleProfiles) {
        newKids.add(new ProfileNode(profile, this, false).sync());
      }
      children = newKids;
      ((DefaultTreeModel)myTree.getModel()).reload();
      expand(myTree);
      return this;
    }
  }

  private interface DataSynchronizable {
    DataSynchronizable sync();
  }

  private class ProfileNode extends DefaultMutableTreeNode implements DataSynchronizable {
    private final ProcessorConfigProfile myProfile;
    private final boolean myIsDefault;

    public ProfileNode(ProcessorConfigProfile profile, RootNode parent, boolean isDefault) {
      super(profile);
      setParent(parent);
      myIsDefault = isDefault;
      myProfile = profile;
    }

    @Override
    public DataSynchronizable sync() {
      final List<Module> nodeModules = new ArrayList<Module>();
      if (myIsDefault) {
        final Set<String> nonDefaultProfileModules = new HashSet<String>();
        for (ProcessorConfigProfile profile : myModuleProfiles) {
          nonDefaultProfileModules.addAll(profile.getModuleNames());
        }
        for (Map.Entry<String, Module> entry : myAllModulesMap.entrySet()) {
          if (!nonDefaultProfileModules.contains(entry.getKey())) {
            nodeModules.add(entry.getValue());
          }
        }
      }
      else {
        for (String moduleName : myProfile.getModuleNames()) {
          final Module module = myAllModulesMap.get(moduleName);
          if (module != null) {
            nodeModules.add(module);
          }
        }
      }
      Collections.sort(nodeModules, ModuleComparator.INSTANCE);
      final Vector vector = new Vector();
      for (Module module : nodeModules) {
        vector.add(new MyModuleNode(module, this));
      }
      children = vector;
      return this;
    }

  }

  private static class MyModuleNode extends DefaultMutableTreeNode {
    public MyModuleNode(Module module, ProfileNode parent) {
      super(module);
      setParent(parent);
      setAllowsChildren(false);
    }
  }

  private static class MyCellRenderer extends ColoredTreeCellRenderer {
    @Override
    public void customizeCellRenderer(JTree tree, Object value, boolean selected, boolean expanded, boolean leaf, int row, boolean hasFocus) {
      if (value instanceof ProfileNode) {
        append(((ProfileNode)value).myProfile.getName());
      }
      else if (value instanceof MyModuleNode) {
        final Module module = (Module)((MyModuleNode)value).getUserObject();
        setIcon(AllIcons.Nodes.Module);
        append(module.getName());
      }
    }
  }

  private static class ModuleComparator implements Comparator<Module> {
    static final ModuleComparator INSTANCE = new ModuleComparator();
    @Override
    public int compare(Module o1, Module o2) {
      return o1.getName().compareTo(o2.getName());
    }
  }

}


File: platform/platform-api/src/com/intellij/ui/TreeToolbarDecorator.java
/*
 * Copyright 2000-2012 JetBrains s.r.o.
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

import com.intellij.openapi.actionSystem.ActionToolbarPosition;
import com.intellij.openapi.util.SystemInfo;
import com.intellij.ui.treeStructure.SimpleNode;
import com.intellij.util.ui.EditableModel;
import com.intellij.util.ui.EditableTreeModel;
import com.intellij.util.ui.ElementProducer;
import com.intellij.util.ui.tree.TreeUtil;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import javax.swing.event.TreeSelectionEvent;
import javax.swing.event.TreeSelectionListener;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.DefaultTreeModel;
import javax.swing.tree.TreePath;
import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;

/**
 * @author Konstantin Bulenkov
 */
class TreeToolbarDecorator extends ToolbarDecorator {
  private final JTree myTree;
  @Nullable private final ElementProducer<?> myProducer;

  TreeToolbarDecorator(JTree tree, @Nullable final ElementProducer<?> producer) {
    myTree = tree;
    myProducer = producer;
    myAddActionEnabled = myRemoveActionEnabled = myUpActionEnabled = myDownActionEnabled = myTree.getModel() instanceof EditableTreeModel;
    if (myTree.getModel() instanceof EditableTreeModel) {
      createDefaultTreeActions();
    }
    myTree.getSelectionModel().addTreeSelectionListener(new TreeSelectionListener() {
      @Override
      public void valueChanged(TreeSelectionEvent e) {
        updateButtons();
      }
    });
    myTree.addPropertyChangeListener("enabled", new PropertyChangeListener() {
      @Override
      public void propertyChange(PropertyChangeEvent evt) {
        updateButtons();
      }
    });
  }

  private void createDefaultTreeActions() {
    final EditableTreeModel model = (EditableTreeModel)myTree.getModel();
    myAddAction = new AnActionButtonRunnable() {
      @Override
      public void run(AnActionButton button) {
        final TreePath path = myTree.getSelectionPath();
        final DefaultMutableTreeNode selected =
          path == null ? (DefaultMutableTreeNode)myTree.getModel().getRoot() : (DefaultMutableTreeNode)path.getLastPathComponent();
        final Object selectedNode = selected.getUserObject();

        myTree.stopEditing();
        Object element;
        if (model instanceof DefaultTreeModel && myProducer != null) {
           element = myProducer.createElement();
          if (element == null) return;
        } else {
          element = null;
        }
        DefaultMutableTreeNode parent = selected;
        if ((selectedNode instanceof SimpleNode && ((SimpleNode)selectedNode).isAlwaysLeaf()) || !selected.getAllowsChildren()) {
          parent = (DefaultMutableTreeNode)selected.getParent();
        }
        if (parent != null) {
         parent.insert(new DefaultMutableTreeNode(element), parent.getChildCount());
        }
        final TreePath createdPath = model.addNode(new TreePath(parent.getPath()));
        if (path != null) {
          TreeUtil.selectPath(myTree, createdPath);
          myTree.requestFocus();
        }
      }
    };

    myRemoveAction = new AnActionButtonRunnable() {
      @Override
      public void run(AnActionButton button) {
        myTree.stopEditing();
        final TreePath path = myTree.getSelectionPath();
        model.removeNode(path);
      }
    };
  }

  @Override
  public ToolbarDecorator initPosition() {
    return setToolbarPosition(SystemInfo.isMac ? ActionToolbarPosition.BOTTOM : ActionToolbarPosition.TOP);
  }

  @Override
  protected JComponent getComponent() {
    return myTree;
  }

  @Override
  protected void updateButtons() {
    getActionsPanel().setEnabled(CommonActionsPanel.Buttons.REMOVE, myTree.getSelectionPath() != null);
  }

  @Override
  public ToolbarDecorator setVisibleRowCount(int rowCount) {
    myTree.setVisibleRowCount(rowCount);
    return this;
  }

  @Override
  protected boolean isModelEditable() {
    return myTree.getModel() instanceof EditableModel;
  }

  @Override
  protected void installDnDSupport() {
    RowsDnDSupport.install(myTree, (EditableModel)myTree.getModel());
  }
}


File: platform/util/src/com/intellij/util/ui/EditableTreeModel.java
/*
 * Copyright 2000-2012 JetBrains s.r.o.
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
package com.intellij.util.ui;

import javax.swing.tree.TreePath;

/**
 * @author Konstantin Bulenkov
 * @since 12.0
 */
public interface EditableTreeModel {
  /**
   * Adds a new node into a
   * @param parent selected node, maybe used as parent or as a neighbour
   * @return path to newly created element
   */
  TreePath addNode(TreePath parentOrNeighbour);

  void removeNode(TreePath parent);

  void moveNodeTo(TreePath parentOrNeighbour);
}
