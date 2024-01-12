Refactoring Types: ['Extract Method']
lient/dom/DomUtils.java
/*
 * DomUtils.java
 *
 * Copyright (C) 2009-12 by RStudio, Inc.
 *
 * Unless you have received this program directly from RStudio pursuant
 * to the terms of a commercial license agreement with RStudio, then
 * this program is licensed to you under the terms of version 3 of the
 * GNU Affero General Public License. This program is distributed WITHOUT
 * ANY EXPRESS OR IMPLIED WARRANTY, INCLUDING THOSE OF NON-INFRINGEMENT,
 * MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. Please refer to the
 * AGPL (http://www.gnu.org/licenses/agpl-3.0.txt) for more details.
 *
 */
package org.rstudio.core.client.dom;

import com.google.gwt.core.client.GWT;
import com.google.gwt.core.client.JavaScriptObject;
import com.google.gwt.core.client.JsArrayMixed;
import com.google.gwt.core.client.JsArrayString;
import com.google.gwt.dom.client.*;
import com.google.gwt.dom.client.Element;
import com.google.gwt.user.client.*;
import com.google.gwt.user.client.ui.UIObject;

import org.rstudio.core.client.BrowseCap;
import org.rstudio.core.client.Debug;
import org.rstudio.core.client.Point;
import org.rstudio.core.client.Rectangle;
import org.rstudio.core.client.command.KeyboardShortcut;
import org.rstudio.core.client.dom.impl.DomUtilsImpl;
import org.rstudio.core.client.dom.impl.NodeRelativePosition;
import org.rstudio.core.client.regex.Match;
import org.rstudio.core.client.regex.Pattern;

/**
 * Helper methods that are mostly useful for interacting with 
 * contentEditable regions.
 */
public class DomUtils
{
   public interface NodePredicate
   {
      boolean test(Node n) ;
   }

   public static native Element getActiveElement() /*-{
      return $doc.activeElement;
   }-*/;

   /**
    * In IE8, focusing the history table (which is larger than the scroll
    * panel it's contained in) causes the scroll panel to jump to the top.
    * Using setActive() solves this problem. Other browsers don't support
    * setActive but also don't have the scrolling problem.
    * @param element
    */
   public static native void setActive(Element element) /*-{
      if (element.setActive)
         element.setActive();
      else
         element.focus();
   }-*/;

   public static int trimLines(Element element, int linesToTrim)
   {
      return trimLines(element.getChildNodes(), linesToTrim);
   }

   public static native void scrollToBottom(Element element) /*-{
      element.scrollTop = element.scrollHeight;
   }-*/;

   public static JavaScriptObject splice(JavaScriptObject array,
                                         int index,
                                         int howMany,
                                         String... elements)
   {
      JsArrayMixed args = JavaScriptObject.createArray().cast();
      args.push(index);
      args.push(howMany);
      for (String el : elements)
         args.push(el);
      return spliceInternal(array, args);
   }

   private static native JsArrayString spliceInternal(JavaScriptObject array,
                                                      JsArrayMixed args) /*-{
      return Array.prototype.splice.apply(array, args);
   }-*/;

   public static Node findNodeUpwards(Node node,
                                      Element scope,
                                      NodePredicate predicate)
   {
      if (scope != null && !scope.isOrHasChild(node))
         throw new IllegalArgumentException("Incorrect scope passed to findParentNode");

      for (; node != null; node = node.getParentNode())
      {
         if (predicate.test(node))
            return node;
         if (scope == node)
            return null;
      }
      return null;
   }

   public static boolean isEffectivelyVisible(Element element)
   {
      while (element != null)
      {
         if (!UIObject.isVisible(element))
            return false;

         // If element never equals body, then the element is not attached
         if (element == Document.get().getBody())
            return true;

         element = element.getParentElement();
      }

      // Element is not attached
      return false;
   }

   public static void selectElement(Element el)
   {
      impl.selectElement(el);
   }

   private static final Pattern NEWLINE = Pattern.create("\\n");
   private static int trimLines(NodeList<Node> nodes, final int linesToTrim)
   {
      if (nodes == null || nodes.getLength() == 0 || linesToTrim == 0)
         return 0;

      int linesLeft = linesToTrim;

      Node node = nodes.getItem(0);

      while (node != null && linesLeft > 0)
      {
         switch (node.getNodeType())
         {
            case Node.ELEMENT_NODE:
               if (((Element)node).getTagName().equalsIgnoreCase("br"))
               {
                  linesLeft--;
                  node = removeAndGetNext(node);
                  continue;
               }
               else
               {
                  int trimmed = trimLines(node.getChildNodes(), linesLeft);
                  linesLeft -= trimmed;
                  if (!node.hasChildNodes())
                     node = removeAndGetNext(node);
                  continue;
               }
            case Node.TEXT_NODE:
               String text = ((Text)node).getData();

               Match lastMatch = null;
               Match match = NEWLINE.match(text, 0);
               while (match != null && linesLeft > 0)
               {
                  lastMatch = match;
                  linesLeft--;
                  match = match.nextMatch();
               }

               if (linesLeft > 0 || lastMatch == null)
               {
                  node = removeAndGetNext(node);
                  continue;
               }
               else
               {
                  int index = lastMatch.getIndex() + 1;
                  if (text.length() == index)
                     node.removeFromParent();
                  else
                     ((Text) node).deleteData(0, index);
                  break;
               }
         }
      }

      return linesToTrim - linesLeft;
   }

   private static Node removeAndGetNext(Node node)
   {
      Node next = node.getNextSibling();
      node.removeFromParent();
      return next;
   }

   /**
    *
    * @param node
    * @param pre Count hard returns in text nodes as newlines (only true if
    *    white-space mode is pre*)
    * @return
    */
   public static int countLines(Node node, boolean pre)
   {
      switch (node.getNodeType())
      {
         case Node.TEXT_NODE:
            return countLinesInternal((Text)node, pre);
         case Node.ELEMENT_NODE:
            return countLinesInternal((Element)node, pre);
         default:
            return 0;
      }
   }

   private static int countLinesInternal(Text textNode, boolean pre)
   {
      if (!pre)
         return 0;
      String value = textNode.getData();
      Pattern pattern = Pattern.create("\\n");
      int count = 0;
      Match m = pattern.match(value, 0);
      while (m != null)
      {
         count++;
         m = m.nextMatch();
      }
      return count;
   }

   private static int countLinesInternal(Element elementNode, boolean pre)
   {
      if (elementNode.getTagName().equalsIgnoreCase("br"))
         return 1;

      int result = 0;
      NodeList<Node> children = elementNode.getChildNodes();
      for (int i = 0; i < children.getLength(); i++)
         result += countLines(children.getItem(i), pre);
      return result;
   }

   private final static DomUtilsImpl impl = GWT.create(DomUtilsImpl.class);

   /**
    * Drives focus to the element, and if (the element is contentEditable and
    * contains no text) or alwaysDriveSelection is true, also drives window
    * selection to the contents of the element. This is sometimes necessary
    * to get focus to move at all.
    */
   public static void focus(Element element, boolean alwaysDriveSelection)
   {
      impl.focus(element, alwaysDriveSelection);
   }

   public static native boolean hasFocus(Element element) /*-{
      return element === $doc.activeElement;
   }-*/;

   public static void collapseSelection(boolean toStart)
   {
      impl.collapseSelection(toStart);
   }

   public static boolean isSelectionCollapsed()
   {
      return impl.isSelectionCollapsed();
   }

   public static boolean isSelectionInElement(Element element)
   {
      return impl.isSelectionInElement(element);
   }

   /**
    * Returns true if the window contains an active selection.
    */
   public static boolean selectionExists()
   {
      return impl.selectionExists();
   }

   public static boolean contains(Element container, Node descendant)
   {
      while (descendant != null)
      {
         if (descendant == container)
            return true ;

         descendant = descendant.getParentNode() ;
      }
      return false ;
   }

   /**
    * CharacterData.deleteData(node, index, offset)
    */
   public static final native void deleteTextData(Text node,
                                                  int offset,
                                                  int length) /*-{
      node.deleteData(offset, length);
   }-*/;

   public static native void insertTextData(Text node,
                                            int offset,
                                            String data) /*-{
      node.insertData(offset, data);
   }-*/;

   public static Rectangle getCursorBounds()
   {
      return getCursorBounds(Document.get()) ;
   }

   public static Rectangle getCursorBounds(Document doc)
   {
      return impl.getCursorBounds(doc);
   }

   public static String replaceSelection(Document document, String text)
   {
      return impl.replaceSelection(document, text);
   }

   public static String getSelectionText(Document document)
   {
      return impl.getSelectionText(document);
   }

   public static int[] getSelectionOffsets(Element container)
   {
      return impl.getSelectionOffsets(container);
   }

   public static void setSelectionOffsets(Element container,
                                          int start,
                                          int end)
   {
      impl.setSelectionOffsets(container, start, end);
   }

   public static Text splitTextNodeAt(Element container, int offset)
   {
      NodeRelativePosition pos = NodeRelativePosition.toPosition(container, offset) ;

      if (pos != null)
      {
         return ((Text)pos.node).splitText(pos.offset) ;
      }
      else
      {
         Text newNode = container.getOwnerDocument().createTextNode("");
         container.appendChild(newNode);
         return newNode;
      }
   }

   public static native Element getTableCell(Element table, int row, int col) /*-{
      return table.rows[row].cells[col] ;
   }-*/;

   public static void dump(Node node, String label)
   {
      StringBuffer buffer = new StringBuffer() ;
      dump(node, "", buffer, false) ;
      Debug.log("Dumping " + label + ":\n\n" + buffer.toString()) ;
   }

   private static void dump(Node node, 
                            String indent, 
                            StringBuffer out, 
                            boolean doSiblings)
   {
      if (node == null)
         return ;
      
      out.append(indent)
         .append(node.getNodeName()) ;
      if (node.getNodeType() != 1)
      {
         out.append(": \"")
            .append(node.getNodeValue())
            .append("\"");
      }
      out.append("\n") ;
      
      dump(node.getFirstChild(), indent + "\u00A0\u00A0", out, true) ;
      if (doSiblings)
         dump(node.getNextSibling(), indent, out, true) ;
   }

   public static native void ensureVisibleVert(
                                           Element container,
                                           Element child,
                                           int padding) /*-{
      if (!child)
         return;

      var height = child.offsetHeight ;
      var top = 0;
      while (child && child != container)
      {
         top += child.offsetTop ;
         child = child.offsetParent ;
      }

      if (!child)
         return;

      // padding
      top -= padding;
      height += padding*2;

      if (top < container.scrollTop)
      {
         container.scrollTop = top ;
      }
      else if (container.scrollTop + container.offsetHeight < top + height)
      {
         container.scrollTop = top + height - container.offsetHeight ;
      }
   }-*/;

   // Forked from com.google.gwt.dom.client.Element.scrollIntoView()
   public static native void scrollIntoViewVert(Element elem) /*-{
     var top = elem.offsetTop;
     var height = elem.offsetHeight;

     if (elem.parentNode != elem.offsetParent) {
       top -= elem.parentNode.offsetTop;
     }

     var cur = elem.parentNode;
     while (cur && (cur.nodeType == 1)) {
       if (top < cur.scrollTop) {
         cur.scrollTop = top;
       }
       if (top + height > cur.scrollTop + cur.clientHeight) {
         cur.scrollTop = (top + height) - cur.clientHeight;
       }

       var offsetTop = cur.offsetTop;
       if (cur.parentNode != cur.offsetParent) {
         offsetTop -= cur.parentNode.offsetTop;
       }

       top += offsetTop - cur.scrollTop;
       cur = cur.parentNode;
     }
   }-*/;

   public static Point getRelativePosition(Element container,
                                                  Element child)
   {
      int left = 0, top = 0;
      while (child != null && child != container)
      {
         left += child.getOffsetLeft();
         top += child.getOffsetTop();
         child = child.getOffsetParent();
      }

      return new Point(left, top);
   }

   public static int ensureVisibleHoriz(Element container,
                                         Element child,
                                         int paddingLeft,
                                         int paddingRight,
                                         boolean calculateOnly)
   {
      final int scrollLeft = container.getScrollLeft();

      if (child == null)
         return scrollLeft;

      int width = child.getOffsetWidth();
      int left = getRelativePosition(container, child).x;
      left -= paddingLeft;
      width += paddingLeft + paddingRight;

      int result;
      if (left < scrollLeft)
         result = left;
      else if (scrollLeft + container.getOffsetWidth() < left + width)
         result = left + width - container.getOffsetWidth();
      else
         result = scrollLeft;

      if (!calculateOnly && result != scrollLeft)
         container.setScrollLeft(result);

      return result;
   }

   public static native boolean isVisibleVert(Element container,
                                              Element child) /*-{
      if (!container || !child)
         return false;

      var height = child.offsetHeight;
      var top = 0;
      while (child && child != container)
      {
         top += child.offsetTop ;
         child = child.offsetParent ;
      }
      if (!child)
         throw new Error("Child was not in container or " +
                         "container wasn't offset parent");

      var bottom = top + height;
      var scrollTop = container.scrollTop;
      var scrollBottom = container.scrollTop + container.clientHeight;

      return (top > scrollTop && top < scrollBottom)
            || (bottom > scrollTop && bottom < scrollBottom);

   }-*/;

   public static String getHtml(Node node)
   {
      switch (node.getNodeType())
      {
      case Node.DOCUMENT_NODE:
         return ((ElementEx)node).getOuterHtml() ;
      case Node.ELEMENT_NODE:
         return ((ElementEx)node).getOuterHtml() ;
      case Node.TEXT_NODE:
         return node.getNodeValue() ;
      default:
         assert false : 
                  "Add case statement for node type " + node.getNodeType() ;
         return node.getNodeValue() ;
      }
   }

   public static boolean isDescendant(Node el, Node ancestor)
   {
      for (Node parent = el.getParentNode(); 
           parent != null; 
           parent = parent.getParentNode())
      {
         if (parent.equals(ancestor))
            return true ;
      }
      return false ;
   }
   
   public static boolean isDescendantOfElementWithTag(Element el, String[] tags)
   {
      for (Element parent = el.getParentElement(); 
           parent != null; 
           parent = parent.getParentElement())
      {
         for (String tag : tags)
            if (tag.toLowerCase().equals(parent.getTagName().toLowerCase()))
               return true;
      }
      return false ;
   }
   
   /**
    * Finds a node that matches the predicate.
    * 
    * @param start The node from which to start.
    * @param recursive If true, recurses into child nodes.
    * @param siblings If true, looks at the next sibling from "start".
    * @param filter The predicate that determines a match.
    * @return The first matching node encountered in documented order, or null.
    */
   public static Node findNode(Node start, 
                               boolean recursive, 
                               boolean siblings, 
                               NodePredicate filter)
   {
      if (start == null)
         return null ;
      
      if (filter.test(start))
         return start ;
      
      if (recursive)
      {
         Node result = findNode(start.getFirstChild(), true, true, filter) ;
         if (result != null)
            return result ;
      }
      
      if (siblings)
      {
         Node result = findNode(start.getNextSibling(), recursive, true, 
                                filter) ;
         if (result != null)
            return result ;
      }
      
      return null ;
   }

   /**
    * Converts plaintext to HTML, preserving whitespace semantics
    * as much as possible.
    */
   public static String textToHtml(String text)
   {
      // Order of these replacement operations is important.
      return
         text.replaceAll("&", "&amp;")
             .replaceAll("<", "&lt;")
             .replaceAll(">", "&gt;")
             .replaceAll("\\n", "<br />")
             .replaceAll("\\t", "    ")
             .replaceAll(" ", "&nbsp;")
             .replaceAll("&nbsp;(?!&nbsp;)", " ")
             .replaceAll(" $", "&nbsp;")
             .replaceAll("^ ", "&nbsp;");
   }

   public static String textToPreHtml(String text)
   {
      // Order of these replacement operations is important.
      return
         text.replaceAll("&", "&amp;")
             .replaceAll("<", "&lt;")
             .replaceAll(">", "&gt;")
             .replaceAll("\\t", "  ");
   }

   public static String htmlToText(String html)
   {
      Element el = DOM.createSpan();
      el.setInnerHTML(html);
      return el.getInnerText();
   }

   /**
    * Similar to Element.getInnerText() but converts br tags to newlines.
    */
   public static String getInnerText(Element el)
   {
      return getInnerText(el, false);
   }

   public static String getInnerText(Element el, boolean pasteMode)
   {
      StringBuilder out = new StringBuilder();
      getInnerText(el, out, pasteMode);
      return out.toString();
   }

   private static void getInnerText(Node node,
                                    StringBuilder out,
                                    boolean pasteMode)
   {
      if (node == null)
         return;

      for (Node child = node.getFirstChild();
           child != null;
           child = child.getNextSibling())
      {
         switch (child.getNodeType())
         {
            case Node.TEXT_NODE:
               out.append(child.getNodeValue());
               break;
            case Node.ELEMENT_NODE:
               Element childEl = (Element) child;
               String tag = childEl.getTagName().toLowerCase();
               // Sometimes when pasting text (e.g. from IntelliJ) into console
               // the line breaks turn into <br _moz_dirty="true"/> or whatever.
               // We want to keep them in those cases. But in other cases
               // the _moz_dirty breaks are just spurious.
               if (tag.equals("br") && (pasteMode || !childEl.hasAttribute("_moz_dirty")))
                  out.append("\n");
               else if (tag.equals("script") || tag.equals("style"))
                  continue;
               getInnerText(child, out, pasteMode);
               break;
         }
      }
   }

   public static void setInnerText(Element el, String plainText)
   {
      el.setInnerText("");
      if (plainText == null || plainText.length() == 0)
         return;

      Document doc = el.getOwnerDocument();

      Pattern pattern = Pattern.create("\\n");
      int tail = 0;
      Match match = pattern.match(plainText, 0);
      while (match != null)
      {
         if (tail != match.getIndex())
         {
            String line = plainText.substring(tail, match.getIndex());
            el.appendChild(doc.createTextNode(line));
         }
         el.appendChild(doc.createBRElement());
         tail = match.getIndex() + 1;
         match = match.nextMatch();
      }

      if (tail < plainText.length())
         el.appendChild(doc.createTextNode(plainText.substring(tail)));
   }

   public static boolean isSelectionAsynchronous()
   {
      return impl.isSelectionAsynchronous();
   }
   
   public static boolean isCommandClick(NativeEvent nativeEvt)
   {
      int modifierKeys = KeyboardShortcut.getModifierValue(nativeEvt);
      
      boolean isCommandPressed = BrowseCap.isMacintosh() ?
            modifierKeys == KeyboardShortcut.META :
               modifierKeys == KeyboardShortcut.CTRL;
      
      return (nativeEvt.getButton() == NativeEvent.BUTTON_LEFT) && isCommandPressed;
   }
   
   // Returns the relative vertical position of a child to its parent. 
   // Presumes that the parent is one of the elements from which the child's
   // position is computed; if this is not the case, the child's position
   // relative to the body is returned.
   public static int topRelativeTo(Element parent, Element child)
   {
      int top = 0;
      Element el = child;
      while (el != null && el != parent)
      {
         top += el.getOffsetTop();
         el = el.getOffsetParent();
      }
      return top;
   }
   
   public static int bottomRelativeTo(Element parent, Element child)
   {
      return topRelativeTo(parent, child) + child.getOffsetHeight();
   }
   
   public static int leftRelativeTo(Element parent, Element child)
   {
      int left = 0;
      Element el = child;
      while (el != null && el != parent)
      {
         left += el.getOffsetLeft();
         el = el.getOffsetParent();
      }
      return left;
   }

   public static final native void setStyle(Element element, 
                                            String name, 
                                            String value) /*-{
      element.style[name] = value;
   }-*/;
   
   public static Element[] getElementsByClassName(String classes)
   {
      Element documentEl = Document.get().cast();
      return getElementsByClassName(documentEl, classes);
   }
   
   public static final native Element[] getElementsByClassName(Element parent, String classes) /*-{
      var result = [];
      var elements = parent.getElementsByClassName(classes);
      for (var i = 0; i < elements.length; i++) {
         result.push(elements[i]);
      }
      return result;
   }-*/;
   
   public static final Element getParent(Element element, int times)
   {
      Element parent = element;
      for (int i = 0; i < times; i++)
      {
         if (parent == null) return null;
         parent = parent.getParentElement();
      }
      return parent;
   }
   
   // NOTE: Not supported in IE8
   public static final native Style getComputedStyles(Element el)
   /*-{
      return $wnd.getComputedStyle(el);
   }-*/;
   
   public static void toggleClass(Element element,
                                  String cssClass,
                                  boolean value)
   {
      if (value && !element.hasClassName(cssClass))
         element.addClassName(cssClass);
      
      if (!value && element.hasClassName(cssClass))
         element.removeClassName(cssClass);
   }
   
}


File: src/gwt/src/org/rstudio/core/client/widget/MiniPopupPanel.java
/*
 * MiniPopupPanel.java
 *
 * Copyright (C) 2009-12 by RStudio, Inc.
 *
 * Unless you have received this program directly from RStudio pursuant
 * to the terms of a commercial license agreement with RStudio, then
 * this program is licensed to you under the terms of version 3 of the
 * GNU Affero General Public License. This program is distributed WITHOUT
 * ANY EXPRESS OR IMPLIED WARRANTY, INCLUDING THOSE OF NON-INFRINGEMENT,
 * MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. Please refer to the
 * AGPL (http://www.gnu.org/licenses/agpl-3.0.txt) for more details.
 *
 */
package org.rstudio.core.client.widget;

import org.rstudio.core.client.dom.DomUtils;

import com.google.gwt.core.client.GWT;
import com.google.gwt.dom.client.Element;
import com.google.gwt.dom.client.NativeEvent;
import com.google.gwt.event.shared.HandlerRegistration;
import com.google.gwt.resources.client.ClientBundle;
import com.google.gwt.resources.client.CssResource;
import com.google.gwt.user.client.DOM;
import com.google.gwt.user.client.Event;
import com.google.gwt.user.client.Event.NativePreviewEvent;
import com.google.gwt.user.client.Event.NativePreviewHandler;
import com.google.gwt.user.client.Window;
import com.google.gwt.user.client.ui.DecoratedPopupPanel;

public class MiniPopupPanel extends DecoratedPopupPanel
{
   public MiniPopupPanel()
   {
      super();
      commonInit();
   }

   public MiniPopupPanel(boolean autoHide)
   {
      super(autoHide);
      commonInit();
   }

   public MiniPopupPanel(boolean autoHide, boolean modal)
   {
      super(autoHide, modal);
      commonInit();
   }
   
   @Override
   public void show()
   {
      addDragHandler();
      super.show();
   }
   
   @Override
   public void hide()
   {
      removeDragHandler();
      super.hide();
   }
   
   private void commonInit()
   {
      addStyleName(RES.styles().popupPanel());
   }
   
   private void addDragHandler()
   {
      if (dragHandler_ != null)
         dragHandler_.removeHandler();
      
      dragHandler_ = Event.addNativePreviewHandler(new NativePreviewHandler()
      {
         
         @Override
         public void onPreviewNativeEvent(NativePreviewEvent npe)
         {
            if (npe.getNativeEvent().getButton() != NativeEvent.BUTTON_LEFT)
               return;
            
            int type = npe.getTypeInt();
            if (type == Event.ONMOUSEDOWN ||
                type == Event.ONMOUSEMOVE ||
                type == Event.ONMOUSEUP)
            {
               if (dragging_)
               {
                  handleDrag(npe);
                  return;
               }
               
               Element target = npe.getNativeEvent().getEventTarget().cast();
               
               String tagName = target.getTagName().toLowerCase();
               for (String tag : TAGS_EXCLUDE_DRAG)
                  if (tagName.equals(tag))
                     return;
               
               if (DomUtils.isDescendantOfElementWithTag(target, TAGS_EXCLUDE_DRAG))
                  return;

               Element self = MiniPopupPanel.this.getElement();
               if (!DomUtils.isDescendant(target, self))
                  return;
               
               handleDrag(npe);
            }
         }
      });
   }
   
   private void handleDrag(NativePreviewEvent npe)
   {
      NativeEvent event = npe.getNativeEvent();
      int type = npe.getTypeInt();
      
      switch (type)
      {
         case Event.ONMOUSEDOWN:
         {
            beginDrag(event);
            event.stopPropagation();
            event.preventDefault();
            break;
         }
         
         case Event.ONMOUSEMOVE:
         {
            if (dragging_)
            {
               drag(event);
               event.stopPropagation();
               event.preventDefault();
            }
            break;
         }
         
         case Event.ONMOUSEUP:
         case Event.ONLOSECAPTURE:
         {
            if (dragging_ && didDrag_)
            {
               event.stopPropagation();
               event.preventDefault();
            }
            
            endDrag(event);
            break;
         }
         
      }
   }
   
   private void drag(NativeEvent event)
   {
      int newMouseX = event.getClientX();
      int newMouseY = event.getClientY();
      
      int diffX = newMouseX - initialMouseX_;
      int diffY = newMouseY - initialMouseY_;
      
      int maxRight = Window.getClientWidth() - this.getOffsetWidth();
      int maxBottom = Window.getClientHeight() - this.getOffsetHeight();
      
      if (diffX != 0 || diffY != 0)
         didDrag_ = true;
      
      setPopupPosition(
            clamp(initialPopupLeft_ + diffX, 0, maxRight),
            clamp(initialPopupTop_ + diffY, 0, maxBottom));
   }
   
   private int clamp(int value, int low, int high)
   {
      if (value < low) return low;
      else if (value > high) return high;
      return value;
   }
   
   private void beginDrag(NativeEvent event)
   {
      DOM.setCapture(getElement());
      dragging_ = true;
      didDrag_ = false;
      
      initialMouseX_ = event.getClientX();
      initialMouseY_ = event.getClientY();
      
      initialPopupLeft_ = getPopupLeft();
      initialPopupTop_ = getPopupTop();
   }
   
   private void endDrag(NativeEvent event)
   {
      DOM.releaseCapture(getElement());
      dragging_ = false;
      
      // Suppress click events fired immediately after a drag end
      if (didDrag_)
      {
         if (clickAfterDragHandler_ != null)
            clickAfterDragHandler_.removeHandler();

         clickAfterDragHandler_ =
               Event.addNativePreviewHandler(new NativePreviewHandler()
               {

                  @Override
                  public void onPreviewNativeEvent(NativePreviewEvent event)
                  {
                     if (event.getTypeInt() == Event.ONCLICK)
                        event.cancel();

                     clickAfterDragHandler_.removeHandler();
                  }
               });
      }
   }
   
   private void removeDragHandler()
   {
      if (dragHandler_ != null)
         dragHandler_.removeHandler();
   }
   
   private int initialPopupLeft_ = 0;
   private int initialPopupTop_ = 0;
   
   private int initialMouseX_ = 0;
   private int initialMouseY_ = 0;
   
   private boolean dragging_ = false;
   private boolean didDrag_ = false;
   
   private HandlerRegistration dragHandler_;
   private HandlerRegistration clickAfterDragHandler_;
   
   private static final String[] TAGS_EXCLUDE_DRAG = new String[] {
      "a", "input", "button"
   };
   
   // Styles ------------------------------------------
   
   public interface Styles extends CssResource
   {
      String popupPanel();
   }
   
   public interface Resources extends ClientBundle
   {
      @Source("MiniPopupPanel.css")
      Styles styles();
   }
   
   private static Resources RES = GWT.create(Resources.class);
   static {
      RES.styles().ensureInjected();
   }

}


File: src/gwt/src/org/rstudio/core/client/widget/TriStateCheckBox.java
/*
 * TriStateCheckBox.java
 *
 * Copyright (C) 2009-12 by RStudio, Inc.
 *
 * Unless you have received this program directly from RStudio pursuant
 * to the terms of a commercial license agreement with RStudio, then
 * this program is licensed to you under the terms of version 3 of the
 * GNU Affero General Public License. This program is distributed WITHOUT
 * ANY EXPRESS OR IMPLIED WARRANTY, INCLUDING THOSE OF NON-INFRINGEMENT,
 * MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. Please refer to the
 * AGPL (http://www.gnu.org/licenses/agpl-3.0.txt) for more details.
 *
 */
package org.rstudio.core.client.widget;

import org.rstudio.core.client.theme.res.ThemeResources;

import com.google.gwt.core.client.GWT;
import com.google.gwt.dom.client.Style.Unit;
import com.google.gwt.event.dom.client.ClickEvent;
import com.google.gwt.event.dom.client.ClickHandler;
import com.google.gwt.event.logical.shared.HasValueChangeHandlers;
import com.google.gwt.event.logical.shared.ValueChangeEvent;
import com.google.gwt.event.logical.shared.ValueChangeHandler;
import com.google.gwt.event.shared.GwtEvent;
import com.google.gwt.event.shared.HandlerManager;
import com.google.gwt.event.shared.HandlerRegistration;
import com.google.gwt.resources.client.ClientBundle;
import com.google.gwt.resources.client.CssResource;
import com.google.gwt.user.client.ui.Composite;
import com.google.gwt.user.client.ui.FlowPanel;
import com.google.gwt.user.client.ui.HorizontalPanel;
import com.google.gwt.user.client.ui.Image;
import com.google.gwt.user.client.ui.InlineHTML;
import com.google.gwt.user.client.ui.Label;

// A three state checkbox that toggles between
// off -> indeterminate -> on
public class TriStateCheckBox extends Composite
   implements HasValueChangeHandlers<TriStateCheckBox.State>
{
   public static class State
   {
      private State () {}
   }
   
   public TriStateCheckBox(String label)
   {
      panel_ = new HorizontalPanel();
      panel_.setVerticalAlignment(HorizontalPanel.ALIGN_MIDDLE);
      panel_.addDomHandler(new ClickHandler()
      {
         @Override
         public void onClick(ClickEvent event)
         {
            toggleState();
         }
      }, ClickEvent.getType());
      
      alignHelper_ = new InlineHTML();
      alignHelper_.addStyleName(RES.styles().alignHelper());
      
      checkboxInner_ = new Image();
      checkboxOuter_ = new FlowPanel();
      checkboxOuter_.add(alignHelper_);
      checkboxOuter_.add(checkboxInner_);
      panel_.add(checkboxOuter_);
      
      label_ = new Label(label);
      label_.addStyleName(RES.styles().checkboxLabel());
      panel_.add(label_);
      
      setState(STATE_OFF);
      
      initWidget(panel_);
   }
   
   public void setState(State state)
   {
      if (state == STATE_INDETERMINATE)
         checkboxInner_.setResource(ThemeResources.INSTANCE.checkboxTri());
      else if (state == STATE_OFF)
         checkboxInner_.setResource(ThemeResources.INSTANCE.checkboxOff());
      else if (state == STATE_ON)
         checkboxInner_.setResource(ThemeResources.INSTANCE.checkboxOn());
      
      checkboxOuter_.getElement().getStyle().setHeight(
            checkboxInner_.getHeight(), Unit.PX);
      state_ = state;
   }
   
   private void toggleState()
   {
      if (state_ == STATE_OFF)
         setState(STATE_ON);
      else if (state_ == STATE_INDETERMINATE)
         setState(STATE_OFF);
      else if (state_ == STATE_ON)
         setState(STATE_INDETERMINATE);
      
      ValueChangeEvent.fire(this, state_);
   }
   
   private final HorizontalPanel panel_;
   private final Label label_;
   
   private final InlineHTML alignHelper_;
   private final Image checkboxInner_;
   private final FlowPanel checkboxOuter_;
   private State state_;
   
   public static final State STATE_INDETERMINATE = new State();
   public static final State STATE_OFF = new State();
   public static final State STATE_ON = new State();
   
   public interface Styles extends CssResource
   {
      String alignHelper();
      String checkboxLabel();
   }
   
   public interface Resources extends ClientBundle
   {
      @Source("TriStateCheckBox.css")
      Styles styles();
   }
   
   private static Resources RES = GWT.create(Resources.class);
   static {
      RES.styles().ensureInjected();
   }
   
   private final HandlerManager handlerManager_ = new HandlerManager(this);
   
   @Override
   public HandlerRegistration addValueChangeHandler(ValueChangeHandler<State> handler)
   {
      return handlerManager_.addHandler(
            ValueChangeEvent.getType(),
            handler);
   }

   @Override
   public void fireEvent(GwtEvent<?> event)
   {
      handlerManager_.fireEvent(event);
   }
   
}


File: src/gwt/src/org/rstudio/studio/client/workbench/views/source/editors/text/ChunkOptionsPopupPanel.java
/*
 * ChunkOptionsPopupPanel.java
 *
 * Copyright (C) 2009-12 by RStudio, Inc.
 *
 * Unless you have received this program directly from RStudio pursuant
 * to the terms of a commercial license agreement with RStudio, then
 * this program is licensed to you under the terms of version 3 of the
 * GNU Affero General Public License. This program is distributed WITHOUT
 * ANY EXPRESS OR IMPLIED WARRANTY, INCLUDING THOSE OF NON-INFRINGEMENT,
 * MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. Please refer to the
 * AGPL (http://www.gnu.org/licenses/agpl-3.0.txt) for more details.
 *
 */
package org.rstudio.studio.client.workbench.views.source.editors.text;

import java.util.HashMap;
import java.util.Map;

import org.rstudio.core.client.Pair;
import org.rstudio.core.client.RegexUtil;
import org.rstudio.core.client.StringUtil;
import org.rstudio.core.client.TextCursor;
import org.rstudio.core.client.regex.Match;
import org.rstudio.core.client.regex.Pattern;
import org.rstudio.core.client.widget.MiniPopupPanel;
import org.rstudio.core.client.widget.SmallButton;
import org.rstudio.core.client.widget.TextBoxWithCue;
import org.rstudio.core.client.widget.TriStateCheckBox;
import org.rstudio.studio.client.common.HelpLink;
import org.rstudio.studio.client.workbench.views.source.editors.text.ace.Position;
import org.rstudio.studio.client.workbench.views.source.editors.text.ace.Range;

import com.google.gwt.core.client.GWT;
import com.google.gwt.dom.client.Style.Unit;
import com.google.gwt.event.dom.client.ChangeEvent;
import com.google.gwt.event.dom.client.ChangeHandler;
import com.google.gwt.event.dom.client.ClickEvent;
import com.google.gwt.event.dom.client.ClickHandler;
import com.google.gwt.event.dom.client.KeyCodes;
import com.google.gwt.event.dom.client.KeyUpEvent;
import com.google.gwt.event.dom.client.KeyUpHandler;
import com.google.gwt.event.logical.shared.ValueChangeEvent;
import com.google.gwt.event.logical.shared.ValueChangeHandler;
import com.google.gwt.resources.client.ClientBundle;
import com.google.gwt.resources.client.CssResource;
import com.google.gwt.user.client.ui.FlowPanel;
import com.google.gwt.user.client.ui.HorizontalPanel;
import com.google.gwt.user.client.ui.Label;
import com.google.gwt.user.client.ui.VerticalPanel;

public class ChunkOptionsPopupPanel extends MiniPopupPanel
{
   public ChunkOptionsPopupPanel()
   {
      super(true);
      
      chunkOptions_ = new HashMap<String, String>();
      checkboxMap_ = new HashMap<String, TriStateCheckBox>();
      
      panel_ = new VerticalPanel();
      add(panel_);
      
      tbChunkLabel_ = new TextBoxWithCue("Unnamed chunk");
      tbChunkLabel_.addStyleName(RES.styles().textBox());
      tbChunkLabel_.addChangeHandler(new ChangeHandler()
      {
         @Override
         public void onChange(ChangeEvent event)
         {
            synchronize();
         }
      });
      
      panel_.addHandler(new KeyUpHandler()
      {
         @Override
         public void onKeyUp(KeyUpEvent event)
         {
            int keyCode = event.getNativeKeyCode();
            if (keyCode == KeyCodes.KEY_ESCAPE ||
                keyCode == KeyCodes.KEY_ENTER)
            {
               ChunkOptionsPopupPanel.this.hide();
               widget_.getEditor().focus();
               return;
            }
         }
      }, KeyUpEvent.getType());
      
      tbChunkLabel_.addKeyUpHandler(new KeyUpHandler()
      {
         @Override
         public void onKeyUp(KeyUpEvent event)
         {
            int keyCode = event.getNativeKeyCode();
            if (keyCode == KeyCodes.KEY_ESCAPE ||
                keyCode == KeyCodes.KEY_ENTER)
            {
               ChunkOptionsPopupPanel.this.hide();
               widget_.getEditor().focus();
               return;
            }
            
            synchronize();
            
         }
      });
      
      HorizontalPanel labelPanel = new HorizontalPanel();
      labelPanel.addStyleName(RES.styles().labelPanel());
      labelPanel.setVerticalAlignment(VerticalPanel.ALIGN_MIDDLE);
      
      Label chunkLabel = new Label("Chunk name:");
      chunkLabel.addStyleName(RES.styles().chunkLabel());
      labelPanel.add(chunkLabel);
      
      tbChunkLabel_.addStyleName(RES.styles().chunkName());
      labelPanel.add(tbChunkLabel_);
      
      panel_.add(labelPanel);
      
      for (Map.Entry<String, String> entry : BOOLEAN_CHUNK_OPTIONS.entrySet())
      {
         addCheckboxController(entry.getKey(), entry.getValue());
      }
      
      HorizontalPanel footerPanel = new HorizontalPanel();
      footerPanel.getElement().getStyle().setWidth(100, Unit.PCT);
      
      FlowPanel linkPanel = new FlowPanel();
      HelpLink helpLink = new HelpLink("Chunk options", "chunk-options", false);
      linkPanel.add(helpLink);
      
      HorizontalPanel buttonPanel = new HorizontalPanel();
      buttonPanel.addStyleName(RES.styles().buttonPanel());
      buttonPanel.setHorizontalAlignment(HorizontalPanel.ALIGN_RIGHT);
      
      SmallButton revertButton = new SmallButton("Revert");
      revertButton.getElement().getStyle().setMarginRight(8, Unit.PX);
      revertButton.addClickHandler(new ClickHandler()
      {
         
         @Override
         public void onClick(ClickEvent event)
         {
            revert();
            hideAndFocusEditor();
         }
      });
      buttonPanel.add(revertButton);
      
      SmallButton applyButton = new SmallButton("Apply");
      applyButton.addClickHandler(new ClickHandler()
      {
         
         @Override
         public void onClick(ClickEvent event)
         {
            synchronize();
            hideAndFocusEditor();
         }
      });
      buttonPanel.add(applyButton);
      
      footerPanel.setVerticalAlignment(VerticalPanel.ALIGN_BOTTOM);
      footerPanel.add(linkPanel);
      
      footerPanel.setHorizontalAlignment(HorizontalPanel.ALIGN_RIGHT);
      footerPanel.add(buttonPanel);
      
      panel_.add(footerPanel);
   }
   
   public void focus()
   {
      tbChunkLabel_.setFocus(true);
   }
   
   public void init(AceEditorWidget widget, Position position)
   {
      widget_ = widget;
      position_ = position;
      chunkOptions_.clear();
      
      originalLine_ = widget_.getEditor().getSession().getLine(position_.getRow());
      parseChunkHeader(originalLine_, chunkOptions_);
      
      for (String option : BOOLEAN_CHUNK_OPTIONS.keySet())
      {
         TriStateCheckBox cb = checkboxMap_.get(option);
         assert cb != null :
            "No checkbox for boolean option '" + option + "'";
         
         if (chunkOptions_.containsKey(option))
         {
            boolean truthy = isTrue(chunkOptions_.get(option));
            if (truthy)
               cb.setState(TriStateCheckBox.STATE_ON);
            else
               cb.setState(TriStateCheckBox.STATE_OFF);
         }
         else
         {
            cb.setState(TriStateCheckBox.STATE_INDETERMINATE);
         }
      }
   }
   
   private boolean isTrue(String string)
   {
      return string.equals("TRUE") || string.equals("T");
   }
   
   private String extractChunkPreamble(String extractedChunkHeader,
                                       String modeId)
   {
      if (modeId.equals("mode/sweave"))
         return "";
      
      int firstSpaceIdx = extractedChunkHeader.indexOf(' ');
      if (firstSpaceIdx == -1)
         return extractedChunkHeader;
      
      int firstCommaIdx = extractedChunkHeader.indexOf(',');
      if (firstCommaIdx == -1)
         firstCommaIdx = extractedChunkHeader.length();
      
      String label = extractedChunkHeader.substring(
            0, Math.min(firstSpaceIdx, firstCommaIdx)).trim();
      
      return label;
   }
   
   private String extractChunkLabel(String extractedChunkHeader)
   {
      int firstSpaceIdx = extractedChunkHeader.indexOf(' ');
      if (firstSpaceIdx == -1)
         return "";
      
      int firstCommaIdx = extractedChunkHeader.indexOf(',');
      if (firstCommaIdx == -1)
         firstCommaIdx = extractedChunkHeader.length();
      
      return firstCommaIdx <= firstSpaceIdx ?
            "" :
            extractedChunkHeader.substring(firstSpaceIdx + 1, firstCommaIdx).trim();
   }
   
   private void parseChunkHeader(String line,
                                 HashMap<String, String> chunkOptions)
   {
      String modeId = widget_.getEditor().getSession().getMode().getId();
      
      Pattern pattern = null;
      if (modeId.equals("mode/rmarkdown"))
         pattern = RegexUtil.RE_RMARKDOWN_CHUNK_BEGIN;
      else if (modeId.equals("mode/sweave"))
         pattern = RegexUtil.RE_SWEAVE_CHUNK_BEGIN;
      else if (modeId.equals("mode/rhtml"))
         pattern = RegexUtil.RE_RHTML_CHUNK_BEGIN;
      
      if (pattern == null) return;
      
      Match match = pattern.match(line,  0);
      if (match == null) return;
      
      String extracted = match.getGroup(1);
      chunkPreamble_ = extractChunkPreamble(extracted, modeId);
      
      String chunkLabel = extractChunkLabel(extracted);
      if (StringUtil.isNullOrEmpty(chunkLabel))
      {
         tbChunkLabel_.setCueMode(true);
      }
      else
      {
         tbChunkLabel_.setCueMode(false);
         tbChunkLabel_.setText(extractChunkLabel(extracted));
      }
      
      int firstCommaIndex = extracted.indexOf(',');
      String arguments = extracted.substring(firstCommaIndex + 1);
      TextCursor cursor = new TextCursor(arguments);
      
      int startIndex = 0;
      while (true)
      {
         if (!cursor.fwdToCharacter('=', false))
            break;
         
         int equalsIndex = cursor.getIndex();
         int endIndex = arguments.length();
         if (cursor.fwdToCharacter(',', true))
            endIndex = cursor.getIndex();
         
         chunkOptions.put(
               arguments.substring(startIndex, equalsIndex).trim(),
               arguments.substring(equalsIndex + 1, endIndex).trim());
         
         startIndex = cursor.getIndex() + 1;
      }
   }
   
   @Override
   public void hide()
   {
      position_ = null;
      chunkOptions_.clear();
      super.hide();
   }
   
   private Pair<String, String> getChunkHeaderBounds(String modeId)
   {
      if (modeId.equals("mode/rmarkdown"))
         return new Pair<String, String>("```{", "}");
      else if (modeId.equals("mode/sweave"))
         return new Pair<String, String>("<<", ">>=");
      else if (modeId.equals("mode/rhtml"))
         return new Pair<String, String>("<!--", "");
      else if (modeId.equals("mode/c_cpp"))
         return new Pair<String, String>("/***", "");
      
      return null;
   }
   
   private void synchronize()
   {
      String modeId = widget_.getEditor().getSession().getMode().getId();
      Pair<String, String> chunkHeaderBounds =
            getChunkHeaderBounds(modeId);
      if (chunkHeaderBounds == null)
         return;
      
      String label = tbChunkLabel_.getText();
      String newLine =
            chunkHeaderBounds.first +
            chunkPreamble_;
      
      if (!label.isEmpty())
      {
         if (StringUtil.isNullOrEmpty(chunkPreamble_))
            newLine += label;
         else
            newLine += " " + label;
      }
      
      if (!chunkOptions_.isEmpty())
      {
         if (!(StringUtil.isNullOrEmpty(chunkPreamble_) &&
             label.isEmpty()))
         {
            newLine += ", ";
         }
         
         newLine += StringUtil.collapse(chunkOptions_, "=", ", ");
      }
      
      newLine +=
            chunkHeaderBounds.second +
            "\n";
      
      widget_.getEditor().getSession().replace(
            Range.fromPoints(
                  Position.create(position_.getRow(), 0),
                  Position.create(position_.getRow() + 1, 0)), newLine);
   }
   
   private void addCheckboxController(final String optionName,
                                      final String label)
   {
      final TriStateCheckBox cb = new TriStateCheckBox(label);
      cb.addStyleName(RES.styles().checkBox());
      cb.addValueChangeHandler(new ValueChangeHandler<TriStateCheckBox.State>()
      {
         @Override
         public void onValueChange(ValueChangeEvent<TriStateCheckBox.State> event)
         {
            TriStateCheckBox.State state = event.getValue();
            if (state == TriStateCheckBox.STATE_INDETERMINATE)
               chunkOptions_.remove(optionName);
            else if (state == TriStateCheckBox.STATE_OFF)
               chunkOptions_.put(optionName, "FALSE");
            else
               chunkOptions_.put(optionName,  "TRUE");
            synchronize();
         }
      });
      checkboxMap_.put(optionName, cb);
      panel_.add(cb);
   }
   
   private void revert()
   {
      if (position_ == null)
         return;
      
      Range replaceRange = Range.fromPoints(
            Position.create(position_.getRow(), 0),
            Position.create(position_.getRow() + 1, 0));
      
      widget_.getEditor().getSession().replace(
            replaceRange,
            originalLine_ + "\n");
   }
   
   private void hideAndFocusEditor()
   {
      hide();
      widget_.getEditor().focus();
   }
   
   private final VerticalPanel panel_;
   private final TextBoxWithCue tbChunkLabel_;
   private final HashMap<String, TriStateCheckBox> checkboxMap_;
   
   private String originalLine_;
   private String chunkPreamble_;
   private HashMap<String, String> chunkOptions_;
   
   private AceEditorWidget widget_;
   private Position position_;
   
   private static final HashMap<String, String> BOOLEAN_CHUNK_OPTIONS;
   
   static {
      BOOLEAN_CHUNK_OPTIONS = new HashMap<String, String>();
      BOOLEAN_CHUNK_OPTIONS.put("eval", "Evaluate R code");
      BOOLEAN_CHUNK_OPTIONS.put("include", "Include chunk output");
      BOOLEAN_CHUNK_OPTIONS.put("echo", "Echo R code");
   }
   
   public interface Styles extends CssResource
   {
      String textBox();
      
      String chunkLabel();
      String chunkName();
      String labelPanel();
      
      String buttonPanel();
      
      String checkBox();
   }
   
   public interface Resources extends ClientBundle
   {
      @Source("ChunkOptionsPopupPanel.css")
      Styles styles();
   }
   
   private static Resources RES = GWT.create(Resources.class);
   static {
      RES.styles().ensureInjected();
   }
}
