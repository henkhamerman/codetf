Refactoring Types: ['Inline Method']
rains/mps/openapi/editor/cells/CellActionType.java
/*
 * Copyright 2003-2013 JetBrains s.r.o.
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
package jetbrains.mps.openapi.editor.cells;

/**
 * User: shatalin
 * Date: 2/11/13
 */
public enum CellActionType {
  INSERT,
  INSERT_BEFORE,
  DELETE,
  BACKSPACE,
  DELETE_TO_WORD_END,
// TODO: DELETE_TO_WORD_START,

  COPY,
  CUT,
  PASTE,
  PASTE_BEFORE,
  PASTE_AFTER,

  LEFT,
  RIGHT,
  UP,
  DOWN,
  NEXT,
  PREV,
  HOME,
  END,
  PAGE_UP,
  PAGE_DOWN,
  ROOT_HOME,
  ROOT_END,
  LOCAL_HOME,
  LOCAL_END,

  SELECT_LEFT,
  SELECT_RIGHT,
  SELECT_UP,
  SELECT_DOWN,
  SELECT_HOME,
  SELECT_END,
  SELECT_LOCAL_END,
  SELECT_LOCAL_HOME,
  SELECT_NEXT,
  SELECT_PREVIOUS,

  RIGHT_TRANSFORM,
  LEFT_TRANSFORM,

  COMPLETE,
  COMPLETE_SMART,

  FOLD,
  UNFOLD,
  FOLD_ALL,
  UNFOLD_ALL,
  TOGGLE_FOLDING,

  SHOW_MESSAGE,
  CLEAR_SELECTION,

  COMMENT,
  UNCOMMENT
}


File: editor/editor-runtime/source/jetbrains/mps/lang/editor/cellProviders/SingleRoleCellProvider.java
/*
 * Copyright 2003-2015 JetBrains s.r.o.
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
package jetbrains.mps.lang.editor.cellProviders;

import jetbrains.mps.editor.runtime.impl.cellActions.CellAction_DeleteSmart;
import jetbrains.mps.lang.smodel.generator.smodelAdapter.AttributeOperations;
import jetbrains.mps.nodeEditor.cells.EditorCell_Constant;
import jetbrains.mps.nodeEditor.cells.EditorCell_Error;
import jetbrains.mps.nodeEditor.cells.EditorCell_Label;
import jetbrains.mps.openapi.editor.EditorContext;
import jetbrains.mps.openapi.editor.cells.CellActionType;
import jetbrains.mps.openapi.editor.cells.EditorCell;
import jetbrains.mps.openapi.editor.cells.EditorCell_Collection;
import org.jetbrains.mps.openapi.language.SContainmentLink;
import org.jetbrains.mps.openapi.model.SNode;

import java.util.Iterator;


/**
 * @author simon
 */
public abstract class SingleRoleCellProvider {

  protected final SContainmentLink myContainmentLink;
  protected final SNode myOwnerNode;
  protected final EditorContext myEditorContext;

  public SingleRoleCellProvider(final SNode ownerNode, final SContainmentLink containmentLink, EditorContext editorContext) {
    myOwnerNode = ownerNode;
    myContainmentLink = containmentLink;
    myEditorContext = editorContext;
  }

  protected EditorCell createChildCell(EditorContext editorContext, SNode child) {
    EditorCell editorCell = editorContext.getEditorComponent().getUpdater().getCurrentUpdateSession().updateChildNodeCell(child);
    //todo get rid of getDeclarationNode
    editorCell.setAction(CellActionType.DELETE, new CellAction_DeleteSmart(myOwnerNode, myContainmentLink.getDeclarationNode(), child));
    editorCell.setAction(CellActionType.BACKSPACE, new CellAction_DeleteSmart(myOwnerNode, myContainmentLink.getDeclarationNode(), child));
    return editorCell;
  }

  public EditorCell createCell() {
    if (areAttributesEmpty()) {
      return createSingleCell();
    } else {
      return createManyCells();
    }
  }

  private EditorCell_Collection createManyCells() {
    EditorCell_Collection resultCell = jetbrains.mps.nodeEditor.cells.EditorCell_Collection.createIndent2(myEditorContext, myOwnerNode);
    for (SNode child : getNodesToPresent()) {
      resultCell.addEditorCell(createChildCell(myEditorContext, child));
    }
    if (isChildEmpty()) {
      resultCell.addEditorCell(createEmptyCell());
    }
    return resultCell;
  }

  private EditorCell createSingleCell() {
    Iterator<? extends SNode> iterator = myOwnerNode.getChildren(myContainmentLink).iterator();
    if (iterator.hasNext()) {
      return createChildCell(myEditorContext, iterator.next());
    } else {
      return createEmptyCell();
    }
  }

  private boolean areAttributesEmpty() {
    return !AttributeOperations.getChildAttributes(myOwnerNode, myContainmentLink).iterator().hasNext();
  }

  private boolean isChildEmpty() {
    return !myOwnerNode.getChildren(myContainmentLink).iterator().hasNext();
  }

  protected EditorCell createEmptyCell() {
    EditorCell_Label result = myContainmentLink.isOptional() ?
        new EditorCell_Constant(myEditorContext, myOwnerNode, "") :
        new EditorCell_Error(myEditorContext, myOwnerNode, getNoTargetText());
    result.setDefaultText(getNoTargetText());
    return result;
  }

  protected String getNoTargetText() {
    //todo get rid of getRolName
    return "<no " + myContainmentLink.getRoleName() + ">";
  }
  protected Iterable<SNode> getNodesToPresent() {
    return AttributeOperations.getChildNodesAndAttributes(myOwnerNode, myContainmentLink);
  }
}



File: editor/editor-runtime/source_gen/jetbrains/mps/editor/runtime/impl/cellActions/CellAction_Comment.java
package jetbrains.mps.editor.runtime.impl.cellActions;

/*Generated by MPS */

import jetbrains.mps.editor.runtime.cells.AbstractCellAction;
import org.jetbrains.mps.openapi.model.SNode;
import org.jetbrains.annotations.NotNull;
import jetbrains.mps.openapi.editor.EditorContext;
import jetbrains.mps.lang.smodel.generator.smodelAdapter.SNodeOperations;
import jetbrains.mps.smodel.behaviour.BehaviorReflection;
import org.jetbrains.mps.openapi.language.SContainmentLink;
import jetbrains.mps.editor.runtime.selection.SelectionUtil;
import jetbrains.mps.openapi.editor.selection.SelectionManager;
import jetbrains.mps.openapi.editor.cells.EditorCell;
import jetbrains.mps.nodeEditor.cells.CellFinderUtil;
import org.jetbrains.mps.util.Condition;
import jetbrains.mps.smodel.adapter.structure.MetaAdapterFactory;

public class CellAction_Comment extends AbstractCellAction {
  private final SNode myNode;

  /**
   * 
   * @param node node to comment. This node must have parent when executing action
   */
  public CellAction_Comment(@NotNull SNode node) {
    this.myNode = node;
  }

  /**
   * 
   * @param editorContext editor context
   * @throws IllegalStateException if commenting node does not have parent
   */
  public void execute(EditorContext editorContext) {
    SNode parent = SNodeOperations.getParent(myNode);
    if (parent == null) {
      throw new IllegalStateException("Node to comment has no parent. Node: " + BehaviorReflection.invokeVirtual(String.class, myNode, "virtual_getPresentation_1213877396640", new Object[]{}) + " Node id: " + myNode.getNodeId());

    }
    SNode newComment = CommentUtil.commentOut(myNode);
    editorContext.flushEvents();
    final SContainmentLink containmentLink = myNode.getContainmentLink();
    assert containmentLink != null;
    if (containmentLink.isMultiple()) {
      SelectionUtil.selectCell(editorContext, newComment, SelectionManager.LAST_CELL);
    } else {
      EditorCell parentCell = editorContext.getEditorComponent().findNodeCell(parent);
      EditorCell cellToSelect = CellFinderUtil.findChildByCondition(parentCell, new Condition<EditorCell>() {
        public boolean met(EditorCell cell) {
          return eq_9lx3n0_a0a0a0a0b0a1a0g0e(cell.getRole(), containmentLink.getRole()) && !(SNodeOperations.isInstanceOf(((SNode) cell.getSNode()), MetaAdapterFactory.getConcept(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x3dcc194340c24debL, "jetbrains.mps.lang.core.structure.BaseCommentAttribute")));
        }
      }, true);
      editorContext.getSelectionManager().setSelection(cellToSelect);
    }
  }
  private static boolean eq_9lx3n0_a0a0a0a0b0a1a0g0e(Object a, Object b) {
    return (a != null ? a.equals(b) : a == b);
  }
}


File: editor/editor-runtime/source_gen/jetbrains/mps/editor/runtime/impl/cellActions/Cell_Action_Uncomment.java
package jetbrains.mps.editor.runtime.impl.cellActions;

/*Generated by MPS */

import jetbrains.mps.editor.runtime.cells.AbstractCellAction;
import org.jetbrains.mps.openapi.model.SNode;
import org.jetbrains.annotations.NotNull;
import jetbrains.mps.openapi.editor.EditorContext;
import jetbrains.mps.lang.smodel.generator.smodelAdapter.SNodeOperations;
import jetbrains.mps.smodel.behaviour.BehaviorReflection;
import jetbrains.mps.editor.runtime.selection.SelectionUtil;

public class Cell_Action_Uncomment extends AbstractCellAction {
  private final SNode myNode;

  /**
   * 
   * @param node node to comment. This node must have parent when executing action
   */
  public Cell_Action_Uncomment(@NotNull SNode node) {
    this.myNode = node;
  }

  /**
   * 
   * 
   * @param editorContext editor context
   * @throws IllegalStateException if commenting node does not have parent
   */
  public void execute(EditorContext editorContext) {
    SNode parent = SNodeOperations.getParent(myNode);
    if (parent == null) {
      throw new IllegalStateException("Node to comment has no parent. Node: " + BehaviorReflection.invokeVirtual(String.class, myNode, "virtual_getPresentation_1213877396640", new Object[]{}) + " Node id: " + myNode.getNodeId());

    }
    SNode commentedNode = CommentUtil.uncomment(myNode);
    editorContext.flushEvents();
    if (commentedNode != null) {
      SelectionUtil.selectNode(editorContext, commentedNode);
    }

  }

}


File: editor/editor-runtime/source_gen/jetbrains/mps/editor/runtime/impl/cellActions/CommentUtil.java
package jetbrains.mps.editor.runtime.impl.cellActions;

/*Generated by MPS */

import org.jetbrains.annotations.NotNull;
import org.jetbrains.mps.openapi.model.SNode;
import jetbrains.mps.lang.smodel.generator.smodelAdapter.SNodeOperations;
import jetbrains.mps.smodel.behaviour.BehaviorReflection;
import org.jetbrains.mps.openapi.language.SContainmentLink;
import org.jetbrains.mps.openapi.language.SAbstractConcept;
import jetbrains.mps.smodel.action.NodeFactoryManager;
import jetbrains.mps.lang.smodel.generator.smodelAdapter.SConceptOperations;
import jetbrains.mps.smodel.adapter.structure.MetaAdapterFactory;
import jetbrains.mps.lang.smodel.generator.smodelAdapter.SLinkOperations;
import jetbrains.mps.internal.collections.runtime.ListSequence;
import java.util.Iterator;
import jetbrains.mps.internal.collections.runtime.Sequence;
import jetbrains.mps.lang.smodel.generator.smodelAdapter.AttributeOperations;

public class CommentUtil {
  private CommentUtil() {
  }
  /**
   * 
   * 
   * @param node node to comment. This node must have parent
   * @throws IllegalArgumentException if node does not have parent
   */
  @NotNull
  public static SNode commentOut(@NotNull SNode node) {
    SNode parent = SNodeOperations.getParent(node);
    if (parent == null) {
      throw new IllegalArgumentException("Node to comment has no parent. Node: " + BehaviorReflection.invokeVirtual(String.class, node, "virtual_getPresentation_1213877396640", new Object[]{}) + " Node id: " + node.getNodeId());
    }
    SContainmentLink containmentLink = node.getContainmentLink();
    assert containmentLink != null;
    SNode newComment = CommentUtil.createAndInsertNewComment(parent, containmentLink, node);
    SAbstractConcept targetConcept = containmentLink.getTargetConcept();
    if (!(containmentLink.isMultiple()) && !(containmentLink.isOptional())) {
      parent.addChild(containmentLink, NodeFactoryManager.createNode(targetConcept, null, parent, SNodeOperations.getModel(parent)));
    }
    return newComment;
  }
  @NotNull
  private static SNode createAndInsertNewComment(SNode parent, SContainmentLink containmentLink, SNode anchor) {
    SNode newComment = SConceptOperations.createNewNode(SNodeOperations.asInstanceConcept(MetaAdapterFactory.getConcept(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x3dcc194340c24debL, "jetbrains.mps.lang.core.structure.BaseCommentAttribute")));
    insertInProperPlace(parent, anchor, containmentLink, MetaAdapterFactory.getContainmentLink(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x10802efe25aL, 0x47bf8397520e5942L, "smodelAttribute"), newComment);
    BehaviorReflection.invokeNonVirtual(Void.class, newComment, "jetbrains.mps.lang.core.structure.ChildAttribute", "call_setLink_709746936026609906", new Object[]{containmentLink});
    SLinkOperations.setTarget(newComment, MetaAdapterFactory.getContainmentLink(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x3dcc194340c24debL, 0x2ab99f0d2248e89dL, "commentedNode"), anchor);
    return newComment;
  }


  /**
   * 
   * 
   * @param attribute attribute containing commented node. This node must have parent
   * @throws IllegalArgumentException if attribute has no parent   
   */
  public static SNode uncomment(@NotNull SNode attribute) {
    SNode parent = SNodeOperations.getParent(attribute);
    if (parent == null) {
      throw new IllegalArgumentException("Node to uncomment has no parent. Node: " + BehaviorReflection.invokeVirtual(String.class, attribute, "virtual_getPresentation_1213877396640", new Object[]{}) + " Node id: " + attribute.getNodeId());
    }
    SContainmentLink containmentLink = BehaviorReflection.invokeNonVirtual(SContainmentLink.class, attribute, "jetbrains.mps.lang.core.structure.ChildAttribute", "call_getLink_709746936026609871", new Object[]{});
    SNode commentedNode = SLinkOperations.getTarget(attribute, MetaAdapterFactory.getContainmentLink(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x3dcc194340c24debL, 0x2ab99f0d2248e89dL, "commentedNode"));
    if (containmentLink != null) {
      if (!(containmentLink.isMultiple())) {
        SNode currentChild = ListSequence.fromList(SNodeOperations.getChildren(parent, containmentLink)).first();
        if ((currentChild != null)) {
          createAndInsertNewComment(parent, containmentLink, currentChild);
        }
      }
      if (commentedNode != null) {
        attribute.removeChild(commentedNode);
        insertNodeNearComment(parent, attribute, containmentLink, commentedNode);
      }
    }
    SNodeOperations.deleteNode(attribute);
    return commentedNode;
  }


  private static void insertNodeNearComment(SNode parent, SNode anchorComment, SContainmentLink linkToInsert, SNode nodeToInsert) {
    insertInProperPlace(parent, anchorComment, linkToInsert, linkToInsert, nodeToInsert);
  }

  private static void insertInProperPlace(SNode parent, SNode anchor, SContainmentLink anchorLink, SContainmentLink linkToInsert, SNode newChild) {
    SNode prev = getPrevious(parent, anchor, anchorLink);
    SNode next = getNext(parent, anchor, anchorLink);
    if (prev != null) {
      parent.insertChildAfter(linkToInsert, newChild, prev);
    } else if (next != null) {
      parent.insertChildBefore(linkToInsert, newChild, next);
    } else {
      parent.addChild(linkToInsert, newChild);
    }
  }



  private static SNode getPrevious(SNode parent, SNode anchor, SContainmentLink containmentLink) {
    Iterator<SNode> iterator = Sequence.fromIterable(AttributeOperations.getChildNodesAndAttributes(parent, containmentLink)).iterator();
    SNode prev = null;
    while (iterator.hasNext()) {
      SNode next = iterator.next();
      if (next == anchor) {
        return prev;
      }
    }
    return null;
  }
  private static SNode getNext(SNode parent, SNode anchor, SContainmentLink containmentLink) {
    Iterator<SNode> iterator = Sequence.fromIterable(AttributeOperations.getChildNodesAndAttributes(parent, containmentLink)).iterator();
    while (iterator.hasNext()) {
      SNode next = iterator.next();
      if (next == anchor) {
        if (iterator.hasNext()) {
          return iterator.next();
        }
      }
    }
    return null;
  }

}


File: languages/languageDesign/editor/source_gen/jetbrains/mps/lang/editor/structure/CellActionId.java
package jetbrains.mps.lang.editor.structure;

/*Generated by MPS */

import java.util.List;
import jetbrains.mps.internal.collections.runtime.ListSequence;
import java.util.LinkedList;

public enum CellActionId {
  RIGHT_TRANSFORM("RIGHT_TRANSFORM", "right_transform_action_id"),
  DELETE("DELETE", "delete_action_id"),
  INSERT("INSERT", "insert_action_id"),
  INSERT_BEFORE("INSERT_BEFORE", "insert_before_action_id"),
  BACKSPACE("BACKSPACE", "backspace_action_id"),
  DELETE_TO_WORD_END("DELETE_TO_WORD_END", "delete_to_word_end_action_id"),
  COPY("COPY", "copy_action_id"),
  CUT("CUT", "cut_action_id"),
  PASTE("PASTE", "paste_action_id"),
  PASTE_BEFORE("PASTE_BEFORE", "paste_before_action_id"),
  PASTE_AFTER("PASTE_AFTER", "paste_after_action_id"),
  LEFT("LEFT", "left_action_id"),
  RIGHT("RIGHT", "right_action_id"),
  UP("UP", "up_action_id"),
  DOWN("DOWN", "down_action_id"),
  NEXT("NEXT", "next_action_id"),
  PREV("PREV", "prev_action_id"),
  HOME("HOME", "home_action_id"),
  END("END", "end_action_id"),
  PAGE_UP("PAGE_UP", "page_up_action_id"),
  PAGE_DOWN("PAGE_DOWN", "page_down_action_id"),
  ROOT_HOME("ROOT_HOME", "root_home_action_id"),
  ROOT_END("ROOT_END", "root_end_action_id"),
  LOCAL_HOME("LOCAL_HOME", "local_home_action_id"),
  LOCAL_END("LOCAL_END", "local_end_action_id"),
  SELECT_LEFT("SELECT_LEFT", "select_left_action_id"),
  SELECT_RIGHT("SELECT_RIGHT", "select_right_action_id"),
  SELECT_UP("SELECT_UP", "select_up_action_id"),
  SELECT_DOWN("SELECT_DOWN", "select_down_action_id"),
  SELECT_HOME("SELECT_HOME", "select_home_action_id"),
  SELECT_END("SELECT_END", "select_end_action_id"),
  SELECT_LOCAL_END("SELECT_LOCAL_END", "select_local_end_action_id"),
  SELECT_LOCAL_HOME("SELECT_LOCAL_HOME", "select_local_home_action_id"),
  SELECT_NEXT("SELECT_NEXT", "select_next_action_id"),
  SELECT_PREVIOUS("SELECT_PREVIOUS", "select_previous_action_id"),
  LEFT_TRANSFORM("LEFT_TRANSFORM", "left_transform_action_id"),
  COMPLETE("COMPLETE", "complete_action_id"),
  COMPLETE_SMART("COMPLETE_SMART", "complete_smart_action_id"),
  FOLD("FOLD", "fold_action_id"),
  UNFOLD("UNFOLD", "unfold_action_id"),
  FOLD_ALL("FOLD_ALL", "fold_all_action_id"),
  UNFOLD_ALL("UNFOLD_ALL", "unfold_all_action_id"),
  TOGGLE_FOLDING("TOGGLE_FOLDING", "toggle_folding_action_id"),
  SHOW_MESSAGE("SHOW_MESSAGE", "show_message_action_id"),
  COMMENT("COMMENT", "comment_out_action_id"),
  UNCOMMENT("UNCOMMENT", "uncomment_action_id");

  private String myName;
  public String getName() {
    return this.myName;
  }
  public String getValueAsString() {
    return this.myValue;
  }
  public static List<CellActionId> getConstants() {
    List<CellActionId> list = ListSequence.fromList(new LinkedList<CellActionId>());
    ListSequence.fromList(list).addElement(CellActionId.RIGHT_TRANSFORM);
    ListSequence.fromList(list).addElement(CellActionId.DELETE);
    ListSequence.fromList(list).addElement(CellActionId.INSERT);
    ListSequence.fromList(list).addElement(CellActionId.INSERT_BEFORE);
    ListSequence.fromList(list).addElement(CellActionId.BACKSPACE);
    ListSequence.fromList(list).addElement(CellActionId.DELETE_TO_WORD_END);
    ListSequence.fromList(list).addElement(CellActionId.COPY);
    ListSequence.fromList(list).addElement(CellActionId.CUT);
    ListSequence.fromList(list).addElement(CellActionId.PASTE);
    ListSequence.fromList(list).addElement(CellActionId.PASTE_BEFORE);
    ListSequence.fromList(list).addElement(CellActionId.PASTE_AFTER);
    ListSequence.fromList(list).addElement(CellActionId.LEFT);
    ListSequence.fromList(list).addElement(CellActionId.RIGHT);
    ListSequence.fromList(list).addElement(CellActionId.UP);
    ListSequence.fromList(list).addElement(CellActionId.DOWN);
    ListSequence.fromList(list).addElement(CellActionId.NEXT);
    ListSequence.fromList(list).addElement(CellActionId.PREV);
    ListSequence.fromList(list).addElement(CellActionId.HOME);
    ListSequence.fromList(list).addElement(CellActionId.END);
    ListSequence.fromList(list).addElement(CellActionId.PAGE_UP);
    ListSequence.fromList(list).addElement(CellActionId.PAGE_DOWN);
    ListSequence.fromList(list).addElement(CellActionId.ROOT_HOME);
    ListSequence.fromList(list).addElement(CellActionId.ROOT_END);
    ListSequence.fromList(list).addElement(CellActionId.LOCAL_HOME);
    ListSequence.fromList(list).addElement(CellActionId.LOCAL_END);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_LEFT);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_RIGHT);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_UP);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_DOWN);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_HOME);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_END);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_LOCAL_END);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_LOCAL_HOME);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_NEXT);
    ListSequence.fromList(list).addElement(CellActionId.SELECT_PREVIOUS);
    ListSequence.fromList(list).addElement(CellActionId.LEFT_TRANSFORM);
    ListSequence.fromList(list).addElement(CellActionId.COMPLETE);
    ListSequence.fromList(list).addElement(CellActionId.COMPLETE_SMART);
    ListSequence.fromList(list).addElement(CellActionId.FOLD);
    ListSequence.fromList(list).addElement(CellActionId.UNFOLD);
    ListSequence.fromList(list).addElement(CellActionId.FOLD_ALL);
    ListSequence.fromList(list).addElement(CellActionId.UNFOLD_ALL);
    ListSequence.fromList(list).addElement(CellActionId.TOGGLE_FOLDING);
    ListSequence.fromList(list).addElement(CellActionId.SHOW_MESSAGE);
    ListSequence.fromList(list).addElement(CellActionId.COMMENT);
    ListSequence.fromList(list).addElement(CellActionId.UNCOMMENT);
    return list;
  }
  public static CellActionId getDefault() {
    return CellActionId.RIGHT_TRANSFORM;
  }
  public static CellActionId parseValue(String value) {
    if (value == null) {
      return CellActionId.getDefault();
    }
    if (value.equals(CellActionId.RIGHT_TRANSFORM.getValueAsString())) {
      return CellActionId.RIGHT_TRANSFORM;
    }
    if (value.equals(CellActionId.DELETE.getValueAsString())) {
      return CellActionId.DELETE;
    }
    if (value.equals(CellActionId.INSERT.getValueAsString())) {
      return CellActionId.INSERT;
    }
    if (value.equals(CellActionId.INSERT_BEFORE.getValueAsString())) {
      return CellActionId.INSERT_BEFORE;
    }
    if (value.equals(CellActionId.BACKSPACE.getValueAsString())) {
      return CellActionId.BACKSPACE;
    }
    if (value.equals(CellActionId.DELETE_TO_WORD_END.getValueAsString())) {
      return CellActionId.DELETE_TO_WORD_END;
    }
    if (value.equals(CellActionId.COPY.getValueAsString())) {
      return CellActionId.COPY;
    }
    if (value.equals(CellActionId.CUT.getValueAsString())) {
      return CellActionId.CUT;
    }
    if (value.equals(CellActionId.PASTE.getValueAsString())) {
      return CellActionId.PASTE;
    }
    if (value.equals(CellActionId.PASTE_BEFORE.getValueAsString())) {
      return CellActionId.PASTE_BEFORE;
    }
    if (value.equals(CellActionId.PASTE_AFTER.getValueAsString())) {
      return CellActionId.PASTE_AFTER;
    }
    if (value.equals(CellActionId.LEFT.getValueAsString())) {
      return CellActionId.LEFT;
    }
    if (value.equals(CellActionId.RIGHT.getValueAsString())) {
      return CellActionId.RIGHT;
    }
    if (value.equals(CellActionId.UP.getValueAsString())) {
      return CellActionId.UP;
    }
    if (value.equals(CellActionId.DOWN.getValueAsString())) {
      return CellActionId.DOWN;
    }
    if (value.equals(CellActionId.NEXT.getValueAsString())) {
      return CellActionId.NEXT;
    }
    if (value.equals(CellActionId.PREV.getValueAsString())) {
      return CellActionId.PREV;
    }
    if (value.equals(CellActionId.HOME.getValueAsString())) {
      return CellActionId.HOME;
    }
    if (value.equals(CellActionId.END.getValueAsString())) {
      return CellActionId.END;
    }
    if (value.equals(CellActionId.PAGE_UP.getValueAsString())) {
      return CellActionId.PAGE_UP;
    }
    if (value.equals(CellActionId.PAGE_DOWN.getValueAsString())) {
      return CellActionId.PAGE_DOWN;
    }
    if (value.equals(CellActionId.ROOT_HOME.getValueAsString())) {
      return CellActionId.ROOT_HOME;
    }
    if (value.equals(CellActionId.ROOT_END.getValueAsString())) {
      return CellActionId.ROOT_END;
    }
    if (value.equals(CellActionId.LOCAL_HOME.getValueAsString())) {
      return CellActionId.LOCAL_HOME;
    }
    if (value.equals(CellActionId.LOCAL_END.getValueAsString())) {
      return CellActionId.LOCAL_END;
    }
    if (value.equals(CellActionId.SELECT_LEFT.getValueAsString())) {
      return CellActionId.SELECT_LEFT;
    }
    if (value.equals(CellActionId.SELECT_RIGHT.getValueAsString())) {
      return CellActionId.SELECT_RIGHT;
    }
    if (value.equals(CellActionId.SELECT_UP.getValueAsString())) {
      return CellActionId.SELECT_UP;
    }
    if (value.equals(CellActionId.SELECT_DOWN.getValueAsString())) {
      return CellActionId.SELECT_DOWN;
    }
    if (value.equals(CellActionId.SELECT_HOME.getValueAsString())) {
      return CellActionId.SELECT_HOME;
    }
    if (value.equals(CellActionId.SELECT_END.getValueAsString())) {
      return CellActionId.SELECT_END;
    }
    if (value.equals(CellActionId.SELECT_LOCAL_END.getValueAsString())) {
      return CellActionId.SELECT_LOCAL_END;
    }
    if (value.equals(CellActionId.SELECT_LOCAL_HOME.getValueAsString())) {
      return CellActionId.SELECT_LOCAL_HOME;
    }
    if (value.equals(CellActionId.SELECT_NEXT.getValueAsString())) {
      return CellActionId.SELECT_NEXT;
    }
    if (value.equals(CellActionId.SELECT_PREVIOUS.getValueAsString())) {
      return CellActionId.SELECT_PREVIOUS;
    }
    if (value.equals(CellActionId.LEFT_TRANSFORM.getValueAsString())) {
      return CellActionId.LEFT_TRANSFORM;
    }
    if (value.equals(CellActionId.COMPLETE.getValueAsString())) {
      return CellActionId.COMPLETE;
    }
    if (value.equals(CellActionId.COMPLETE_SMART.getValueAsString())) {
      return CellActionId.COMPLETE_SMART;
    }
    if (value.equals(CellActionId.FOLD.getValueAsString())) {
      return CellActionId.FOLD;
    }
    if (value.equals(CellActionId.UNFOLD.getValueAsString())) {
      return CellActionId.UNFOLD;
    }
    if (value.equals(CellActionId.FOLD_ALL.getValueAsString())) {
      return CellActionId.FOLD_ALL;
    }
    if (value.equals(CellActionId.UNFOLD_ALL.getValueAsString())) {
      return CellActionId.UNFOLD_ALL;
    }
    if (value.equals(CellActionId.TOGGLE_FOLDING.getValueAsString())) {
      return CellActionId.TOGGLE_FOLDING;
    }
    if (value.equals(CellActionId.SHOW_MESSAGE.getValueAsString())) {
      return CellActionId.SHOW_MESSAGE;
    }
    if (value.equals(CellActionId.COMMENT.getValueAsString())) {
      return CellActionId.COMMENT;
    }
    if (value.equals(CellActionId.UNCOMMENT.getValueAsString())) {
      return CellActionId.UNCOMMENT;
    }
    return CellActionId.getDefault();
  }
  private String myValue;
  CellActionId(String name, String value) {
    this.myName = name;
    this.myValue = value;
  }
  public String getValue() {
    return this.myValue;
  }
}


File: workbench/mps-editor/source_gen/jetbrains/mps/ide/editor/actions/Comment_Action.java
package jetbrains.mps.ide.editor.actions;

/*Generated by MPS */

import jetbrains.mps.workbench.action.BaseAction;
import javax.swing.Icon;
import com.intellij.openapi.actionSystem.AnActionEvent;
import java.util.Map;
import jetbrains.mps.openapi.editor.selection.Selection;
import jetbrains.mps.ide.editor.MPSEditorDataKeys;
import org.jetbrains.annotations.NotNull;
import jetbrains.mps.nodeEditor.EditorComponent;
import org.jetbrains.mps.openapi.model.SNode;
import jetbrains.mps.ide.actions.MPSCommonDataKeys;
import jetbrains.mps.openapi.editor.selection.MultipleSelection;
import jetbrains.mps.nodeEditor.selection.EditorCellSelection;
import jetbrains.mps.nodeEditor.selection.EditorCellLabelSelection;
import jetbrains.mps.lang.smodel.generator.smodelAdapter.SNodeOperations;
import jetbrains.mps.smodel.adapter.structure.MetaAdapterFactory;
import jetbrains.mps.openapi.editor.cells.CellActionType;

public class Comment_Action extends BaseAction {
  private static final Icon ICON = null;
  public Comment_Action() {
    super("Comment Out", "", ICON);
    this.setIsAlwaysVisible(false);
    this.setExecuteOutsideCommand(false);
  }
  @Override
  public boolean isDumbAware() {
    return true;
  }
  @Override
  public boolean isApplicable(AnActionEvent event, final Map<String, Object> _params) {
    Selection selection = event.getData(MPSEditorDataKeys.EDITOR_COMPONENT).getSelectionManager().getSelection();
    return selection != null && EditorActionUtils.isWriteActionEnabled(event.getData(MPSEditorDataKeys.EDITOR_COMPONENT), selection.getSelectedCells());
  }
  @Override
  public void doUpdate(@NotNull AnActionEvent event, final Map<String, Object> _params) {
    this.setEnabledState(event.getPresentation(), this.isApplicable(event, _params));
  }
  @Override
  protected boolean collectActionData(AnActionEvent event, final Map<String, Object> _params) {
    if (!(super.collectActionData(event, _params))) {
      return false;
    }
    {
      EditorComponent editorComponent = event.getData(MPSEditorDataKeys.EDITOR_COMPONENT);
      if (editorComponent != null && editorComponent.isInvalid()) {
        editorComponent = null;
      }
      if (editorComponent == null) {
        return false;
      }
    }
    {
      SNode node = event.getData(MPSCommonDataKeys.NODE);
      if (node == null) {
        return false;
      }
    }
    return true;
  }
  @Override
  public void doExecute(@NotNull final AnActionEvent event, final Map<String, Object> _params) {
    Selection selection = event.getData(MPSEditorDataKeys.EDITOR_COMPONENT).getSelectionManager().getSelection();
    boolean uncomment = true;
    if (selection instanceof MultipleSelection || selection instanceof EditorCellSelection || (selection instanceof EditorCellLabelSelection && ((EditorCellLabelSelection) selection).hasNonTrivialSelection())) {
      uncomment = false;
    }
    uncomment = uncomment && SNodeOperations.getNodeAncestor(event.getData(MPSCommonDataKeys.NODE), MetaAdapterFactory.getConcept(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x3dcc194340c24debL, "jetbrains.mps.lang.core.structure.BaseCommentAttribute"), false, false) != null && !(SNodeOperations.isInstanceOf(SNodeOperations.getParent(event.getData(MPSCommonDataKeys.NODE)), MetaAdapterFactory.getConcept(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x3dcc194340c24debL, "jetbrains.mps.lang.core.structure.BaseCommentAttribute")));
    if (uncomment) {
      selection.executeAction(CellActionType.UNCOMMENT);
    } else {
      selection.executeAction(CellActionType.COMMENT);
    }
  }
}
