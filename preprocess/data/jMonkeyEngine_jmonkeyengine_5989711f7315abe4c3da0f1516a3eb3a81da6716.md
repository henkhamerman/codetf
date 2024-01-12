Refactoring Types: ['Extract Method']
m/jme3/gde/materialdefinition/editor/ConnectionCurve.java
/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package com.jme3.gde.materialdefinition.editor;

import com.jme3.gde.materialdefinition.fileStructure.leaves.MappingBlock;
import com.jme3.gde.materialdefinition.utils.MaterialUtils;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Point;
import java.awt.RenderingHints;
import java.awt.event.ComponentEvent;
import java.awt.event.ComponentListener;
import java.awt.event.KeyEvent;
import java.awt.event.KeyListener;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.awt.geom.CubicCurve2D;
import java.awt.geom.Path2D;
import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;
import javax.swing.event.MenuDragMouseEvent;
import javax.swing.event.MouseInputListener;

/**
 *
 * @author Nehon
 */
public class ConnectionCurve extends JPanel implements ComponentListener, MouseInputListener, KeyListener, Selectable, PropertyChangeListener {

    protected Dot start;
    protected Dot end;
    private final Point[] points = new Point[7];
    private int pointsSize = 7;
    private int nbCurve = 2;
    private final CubicCurve2D[] curves = new CubicCurve2D[2];    
    private String key = "";
    protected MappingBlock mapping;

    private MouseEvent convertEvent(MouseEvent e) {
        MouseEvent me = null;
        //workaround for swing utilities removing mouse button when converting events.
        if (e instanceof MouseWheelEvent || e instanceof MenuDragMouseEvent) {
            SwingUtilities.convertMouseEvent(this, e, getDiagram());
        } else {
            Point p = SwingUtilities.convertPoint(this, new Point(e.getX(),
                    e.getY()),
                    getDiagram());

            me = new MouseEvent(getDiagram(),
                    e.getID(),
                    e.getWhen(),
                    e.getModifiers()
                    | e.getModifiersEx(),
                    p.x, p.y,
                    e.getXOnScreen(),
                    e.getYOnScreen(),
                    e.getClickCount(),
                    e.isPopupTrigger(),
                    e.getButton());
        }
        return me;
    }
    
    @SuppressWarnings("LeakingThisInConstructor")
    public ConnectionCurve(Dot start, Dot end) {

        if (start.getParamType() == Dot.ParamType.Output
                || (start.getParamType() == Dot.ParamType.Both && end.getParamType() != Dot.ParamType.Output)
                || (end.getParamType() == Dot.ParamType.Both && start.getParamType() != Dot.ParamType.Input)) {
            this.start = start;
            this.end = end;
        } else {
            this.start = end;
            this.end = start;
        }

        for (int i = 0; i < 7; i++) {
            points[i] = new Point();
        }
        for (int i = 0; i < nbCurve; i++) {
            curves[i] = new CubicCurve2D.Double();
        }
        resize(this.start, this.end);
        addMouseMotionListener(this);
        addMouseListener(this);
        addKeyListener(this);
        setFocusable(true);
        setOpaque(false);

    }

    private void translate(Point p, Point store) {
        store.x = p.x - getLocation().x - 1;
        store.y = p.y - getLocation().y - 1;
    }
    private final Point p1 = new Point();
    private final Point p2 = new Point();
    private final Point p3 = new Point();
    private final Point p4 = new Point();

    public String getKey() {
        return key;
    }

    protected void makeKey(MappingBlock mapping, String techName) {
        this.mapping = mapping;
        key = MaterialUtils.makeKey(mapping, techName);
    }

    @Override
    protected void paintComponent(Graphics g) {

        Graphics2D g2 = ((Graphics2D) g);
        g2.setRenderingHint(
                RenderingHints.KEY_ANTIALIASING,
                RenderingHints.VALUE_ANTIALIAS_ON);

        g2.setStroke(new BasicStroke(4));
        Path2D.Double path1 = new Path2D.Double();
         if (getDiagram().selectedItem == this) {
            g.setColor(SELECTED_COLOR);
        } else {
            g.setColor(VERY_DARK_GREY);
        }
       

        if (pointsSize < 4) {
            translate(points[0], p1);
            translate(points[1], p2);
            translate(points[1], p3);
            translate(points[2], p4);
            path1.moveTo(p1.x, p1.y);
            path1.curveTo(p2.x, p2.y, p3.x, p3.y, p4.x, p4.y);
            curves[0].setCurve(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, p4.x, p4.y);
            nbCurve = 1;
        }

        for (int i = 0; i < pointsSize - 3; i += 3) {

            translate(points[i], p1);
            translate(points[i + 1], p2);
            translate(points[i + 2], p3);
            translate(points[i + 3], p4);
            path1.moveTo(p1.x, p1.y);
            path1.curveTo(p2.x, p2.y, p3.x, p3.y, p4.x, p4.y);
            if (i > 1) {
                curves[1].setCurve(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, p4.x, p4.y);
                nbCurve = 2;
            } else {
                curves[0].setCurve(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, p4.x, p4.y);
                nbCurve = 1;
            }

        }

        ((Graphics2D) g).draw(path1);
        g2.setStroke(new BasicStroke(2));
       
        if (getDiagram().selectedItem == this) {
            g.setColor(Color.WHITE);
        } else {
            g.setColor(LIGHT_GREY);
        }
        
        ((Graphics2D) g).draw(path1);
    }
    private final static Color LIGHT_GREY = new Color(190, 190, 190);
    private final static Color VERY_DARK_GREY = new Color(5, 5, 5);
    private final static Color SELECTED_COLOR = new Color(0.8f, 0.8f, 1.0f, 1.0f);
    
    public final static int MARGIN = 15;

    private int getOffset() {
        return 5 * start.getIndex();
    }

    private int getHMiddle() {
        int st = start.getNode().getLocation().y + start.getNode().getHeight();
        int diff = end.getNode().getLocation().y - st;
        return st + diff / 2 + getOffset();

    }

    private int getVMiddleStart() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        return startLocation.x + Math.max(MARGIN, (endLocation.x - startLocation.x) / 2) + getOffset();
    }

    private int getVMiddleStartNoMargin() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        return startLocation.x + ((endLocation.x - startLocation.x) / 2) + getOffset();
    }

    private int getVMiddleStartClampedRight() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        int right = end.getNode().getLocation().x + end.getNode().getWidth() + MARGIN;
        int loc = startLocation.x + Math.max(MARGIN, (endLocation.x - startLocation.x) / 2);
        return Math.max(loc, right) + getOffset();
    }

    private int getVMiddleEnd() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        return endLocation.x - Math.max(0, Math.max(MARGIN, (endLocation.x - startLocation.x) / 2) + getOffset());

    }

    private int getVMiddleEndClampedLeft() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        int left = start.getNode().getLocation().x - MARGIN;//+ end.getNode().getWidth() + MARGIN;
        int loc = endLocation.x - Math.max(0, Math.max(MARGIN, (endLocation.x - startLocation.x) / 2));
        return Math.min(loc, left) + getOffset();

    }

    private int getHBottom() {
        int endBottom = end.getNode().getLocation().y + end.getNode().getHeight() + MARGIN;
        int startBottom = start.getNode().getLocation().y + start.getNode().getHeight() + MARGIN;
        return Math.max(endBottom, startBottom) + getOffset();

    }

    public final void resize(Dot start, Dot end) {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();

        if (start.getParamType() == Dot.ParamType.Both) {
            startLocation.x = endLocation.x - MARGIN * 2;
            pointsSize = 3;
            points[0].setLocation(startLocation);
            points[1].x = startLocation.x;
            points[1].y = endLocation.y;
            points[2].setLocation(endLocation);
        } else if (end.getParamType() == Dot.ParamType.Both) {
            endLocation.x = startLocation.x + MARGIN * 2;
            pointsSize = 3;
            points[0].setLocation(startLocation);
            points[1].x = endLocation.x;
            points[1].y = startLocation.y;
            points[2].setLocation(endLocation);
        } else if (startLocation.x + MARGIN <= endLocation.x - MARGIN) {
            pointsSize = 4;
            points[0].setLocation(startLocation);
            points[1].x = getVMiddleStart();
            points[1].y = startLocation.y;
            points[2].x = getVMiddleStart();
            points[2].y = endLocation.y;
            points[3].setLocation(endLocation);
        } else if (startLocation.x <= endLocation.x) {
            pointsSize = 4;
            points[0].setLocation(startLocation);
            points[1].x = getVMiddleStartNoMargin();
            points[1].y = startLocation.y;
            points[2].x = getVMiddleStartNoMargin();
            points[2].y = endLocation.y;
            points[3].setLocation(endLocation);
        } else {
            pointsSize = 7;
            points[0].setLocation(startLocation);
            points[6].setLocation(endLocation);
            points[1].x = getVMiddleStart();
            points[1].y = startLocation.y;

            points[5].x = getVMiddleEnd();
            points[5].y = endLocation.y;
            if ((start.getNode().getLocation().y + start.getNode().getHeight() + MARGIN
                    > end.getNode().getLocation().y - MARGIN)
                    && (end.getNode().getLocation().y + end.getNode().getHeight() + MARGIN
                    > start.getNode().getLocation().y - MARGIN)) {

                if (startLocation.y + MARGIN <= endLocation.y - MARGIN) {
                    points[1].x = getVMiddleStartClampedRight();
                    points[2].x = getVMiddleStartClampedRight();
                } else {
                    points[1].x = getVMiddleStart();
                    points[2].x = getVMiddleStart();
                }
                points[2].y = getHBottom();
                points[4].y = getHBottom();

                if (startLocation.y + MARGIN > endLocation.y - MARGIN) {
                    points[4].x = getVMiddleEndClampedLeft();
                    points[5].x = getVMiddleEndClampedLeft();
                    points[3].x = points[4].x + (points[2].x - points[4].x) / 2;

                } else {
                    points[4].x = getVMiddleEnd();
                    points[5].x = getVMiddleEnd();
                    points[3].x = points[4].x + (points[2].x - points[4].x) / 2;
                }

                points[3].y = getHBottom();

            } else {

                points[2].x = getVMiddleStart();
                points[2].y = getHMiddle();
                points[3].x = points[4].x + (points[2].x - points[4].x) / 2;
                points[3].y = getHMiddle();
                points[4].x = getVMiddleEnd();
                points[4].y = points[3].y;
            }
        }
        updateBounds();
    }

    private void updateBounds() {
        int minX = Integer.MAX_VALUE, minY = Integer.MAX_VALUE, maxX = Integer.MIN_VALUE, maxY = Integer.MIN_VALUE;
        for (int i = 0; i < pointsSize; i++) {
            if (points[i].x < minX) {
                minX = points[i].x;
            }
            if (points[i].y < minY) {
                minY = points[i].y;
            }

            if (points[i].x > maxX) {
                maxX = points[i].x;
            }
            if (points[i].y > maxY) {
                maxY = points[i].y;
            }
        }
        maxX += MARGIN;
        maxY += MARGIN;
        minX -= MARGIN;
        minY -= MARGIN;

        setLocation(minX, minY);
        setSize(maxX - minX, maxY - minY);
    }

    private Diagram getDiagram() {
        return (Diagram) start.getDiagram();
    }

    @Override
    public void mouseDragged(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    private void dispatchEventToDiagram(MouseEvent e) {
        MouseEvent me = convertEvent(e);
        getDiagram().dispatchEvent(me);
    }

    @Override
    public void mouseMoved(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    @Override
    public void mouseClicked(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    @Override
    public void mousePressed(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    @Override
    public void mouseReleased(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    public void select(MouseEvent e) {

        requestFocusInWindow(true);
        int margin = MARGIN / 2;
        boolean selected = false;

        for (int i = 0; i < nbCurve && !selected; i++) {
            selected = curves[i].intersects(e.getX() - margin, e.getY() - margin, e.getX() + margin, e.getY() + margin);
        }

        if (selected) {
            getDiagram().select(this);
            e.consume();
        }
    }

    @Override
    public void mouseEntered(MouseEvent e) {
    }

    @Override
    public void mouseExited(MouseEvent e) {
    }

    @Override
    public void keyTyped(KeyEvent e) {
    }

    @Override
    public void keyPressed(KeyEvent e) {

        if (e.getKeyCode() == KeyEvent.VK_DELETE) {
            Diagram diag = getDiagram();
            if (diag.selectedItem == this) {
                diag.removeSelectedConnection();
            }
        }
    }

    @Override
    public void keyReleased(KeyEvent e) {
    }

    public void componentResized(ComponentEvent e) {
    }

    public void componentMoved(ComponentEvent e) {
        resize(start, end);
    }

    public void componentShown(ComponentEvent e) {
    }

    public void componentHidden(ComponentEvent e) {
    }

    public void propertyChange(PropertyChangeEvent evt) {
        MappingBlock map = (MappingBlock) evt.getSource();
        key = MaterialUtils.makeKey(map, getDiagram().getCurrentTechniqueName());
    }

    public Dot getStart() {
        return start;
    }

    public Dot getEnd() {
        return end;
    }
    
    
}


File: sdk/jme3-materialeditor/src/com/jme3/gde/materialdefinition/editor/ConnectionStraight.java
/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package com.jme3.gde.materialdefinition.editor;

import com.jme3.gde.materialdefinition.fileStructure.leaves.MappingBlock;
import com.jme3.gde.materialdefinition.utils.MaterialUtils;
import java.awt.Color;
import java.awt.Graphics;
import java.awt.Point;
import java.awt.event.ComponentEvent;
import java.awt.event.ComponentListener;
import java.awt.event.KeyEvent;
import java.awt.event.KeyListener;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;
import javax.swing.event.MenuDragMouseEvent;
import javax.swing.event.MouseInputListener;

/**
 *
 * Kept this class in case of.
 * This is the old staright connection class, now ConnectionCurve is used
 * @author Nehon
 */
@Deprecated
public class ConnectionStraight extends JPanel implements ComponentListener, MouseInputListener, KeyListener, Selectable, PropertyChangeListener {

    protected Dot start;
    protected Dot end;
    private Point[] points = new Point[6];
    private int pointsSize = 6;
    private Corner[] corners = new Corner[6];
    private String key = "";
    protected MappingBlock mapping;

    private MouseEvent convertEvent(MouseEvent e) {
        MouseEvent me = null;
        //workaround for swing utilities removing mouse button when converting events.
        if (e instanceof MouseWheelEvent || e instanceof MenuDragMouseEvent) {
            SwingUtilities.convertMouseEvent(this, e, getDiagram());
        } else {
            Point p = SwingUtilities.convertPoint(this, new Point(e.getX(),
                    e.getY()),
                    getDiagram());

            me = new MouseEvent(getDiagram(),
                    e.getID(),
                    e.getWhen(),
                    e.getModifiers()
                    | e.getModifiersEx(),
                    p.x, p.y,
                    e.getXOnScreen(),
                    e.getYOnScreen(),
                    e.getClickCount(),
                    e.isPopupTrigger(),
                    e.getButton());
        }
        return me;
    }

    private enum Corner {

        RightBottom,
        BottomRight,
        BottomLeft,
        LeftBottom,
        RightTop,
        TopRight,
        LeftTop,
        TopLeft,
        Top,
        Bottom,
        None,}

    public ConnectionStraight(Dot start, Dot end) {


        if (start.getParamType() == Dot.ParamType.Output
                || (start.getParamType() == Dot.ParamType.Both && end.getParamType() != Dot.ParamType.Output)
                || (end.getParamType() == Dot.ParamType.Both && start.getParamType() != Dot.ParamType.Input)) {
            this.start = start;
            this.end = end;
        } else {
            this.start = end;
            this.end = start;
        }

        for (int i = 0; i < 6; i++) {
            points[i] = new Point();
        }
        resize(this.start, this.end);
        addMouseMotionListener(this);
        addMouseListener(this);
        addKeyListener(this);
        setFocusable(true);
        setOpaque(false);

    }

    private void translate(Point p, Point store) {
        store.x = p.x - getLocation().x - 1;
        store.y = p.y - getLocation().y - 1;
    }
    private Point p1 = new Point();
    private Point p2 = new Point();
    private Point tp1 = new Point();
    private Point bp1 = new Point();
    private Point tp2 = new Point();
    private Point bp2 = new Point();

    @Override
    protected void paintBorder(Graphics g) {
//        super.paintBorder(g);
//
//        g.setColor(Color.GRAY);
//        g.drawLine(0, 0, getWidth(), 0);
//        g.drawLine(getWidth(), 0, getWidth(), getHeight() - 1);
//        g.drawLine(getWidth(), getHeight() - 1, 0, getHeight() - 1);
//        g.drawLine(0, getHeight() - 1, 0, 0);
    }

    public String getKey() {
        return key;
    }

    protected void makeKey(MappingBlock mapping, String techName) {
        this.mapping = mapping;
        key = MaterialUtils.makeKey(mapping, techName);
    }

    private void adjustCorners(Corner corner, Point tp, Point bp) {
        switch (corner) {
            case LeftTop:
            case TopLeft:
                tp.x -= 1;
                bp.x += 1;
                tp.y += 1;
                bp.y -= 1;
                break;
            case RightBottom:
            case BottomRight:
                tp.x += 1;
                bp.x -= 1;
                tp.y -= 1;
                bp.y += 1;
                break;
            case RightTop:
            case TopRight:
                tp.x -= 1;
                bp.x += 1;
                tp.y -= 1;
                bp.y += 1;
                break;
            case LeftBottom:
            case BottomLeft:
                tp.x += 1;
                bp.x -= 1;
                tp.y += 1;
                bp.y -= 1;
                break;
            case None:
                tp.y -= 1;
                bp.y += 1;
                break;
            case Top:
                tp.x -= 1;
                bp.x += 1;
                break;
            case Bottom:
                tp.x += 1;
                bp.x -= 1;
                break;
        }
    }

    @Override
    protected void paintComponent(Graphics g) {
        if (paintDebug) {
            for (int i = 0; i < pointsSize - 1; i++) {
                translate(points[i], p1);
                p1.x -= MARGIN;
                p1.y -= MARGIN;
                translate(points[i + 1], p2);
                p2.x += MARGIN;
                p2.y += MARGIN;
                g.setColor(Color.GRAY);
                g.drawLine(p1.x, p1.y, p2.x, p1.y);
                g.drawLine(p2.x, p1.y, p2.x, p2.y);
                g.drawLine(p2.x, p2.y, p1.x, p2.y);
                g.drawLine(p1.x, p2.y, p1.x, p1.y);


            }

            paintDebug = false;
        }

        for (int i = 0; i < pointsSize - 1; i++) {

            g.setColor(Color.YELLOW);
            translate(points[i], p1);
            translate(points[i + 1], p2);
            g.drawLine(p1.x, p1.y, p2.x, p2.y);


            if (getDiagram().selectedItem == this) {
                g.setColor(Color.CYAN);
            } else {
                g.setColor(Color.GRAY);
            }
            tp1.setLocation(p1);
            bp1.setLocation(p1);
            tp2.setLocation(p2);
            bp2.setLocation(p2);
            adjustCorners(corners[i], tp1, bp1);
            adjustCorners(corners[i + 1], tp2, bp2);
            g.drawLine(tp1.x, tp1.y, tp2.x, tp2.y);
            g.drawLine(bp1.x, bp1.y, bp2.x, bp2.y);

        }

    }
    public final static int MARGIN = 10;

    private int getOffset() {
        return 5 * start.getIndex();
    }

    private int getHMiddle() {
        int st = start.getNode().getLocation().y + start.getNode().getHeight();
        int diff = end.getNode().getLocation().y - st;
        return st + diff / 2 + getOffset();

    }

    private int getVMiddleStart() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        return startLocation.x + Math.max(MARGIN, (endLocation.x - startLocation.x) / 2) + getOffset();
    }

    private int getVMiddleStartClampedRight() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        int right = end.getNode().getLocation().x + end.getNode().getWidth() + MARGIN;
        int loc = startLocation.x + Math.max(MARGIN, (endLocation.x - startLocation.x) / 2);
        return Math.max(loc, right) + getOffset();
    }

    private int getVMiddleEnd() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        return endLocation.x - Math.max(0, Math.max(MARGIN, (endLocation.x - startLocation.x) / 2) + getOffset());

    }

    private int getVMiddleEndClampedLeft() {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();
        int left = start.getNode().getLocation().x - MARGIN;//+ end.getNode().getWidth() + MARGIN;
        int loc = endLocation.x - Math.max(0, Math.max(MARGIN, (endLocation.x - startLocation.x) / 2));
        return Math.min(loc, left) + getOffset();

    }

    private int getHBottom() {
        int endBottom = end.getNode().getLocation().y + end.getNode().getHeight() + MARGIN;
        int startBottom = start.getNode().getLocation().y + start.getNode().getHeight() + MARGIN;
        return Math.max(endBottom, startBottom) + getOffset();

    }

    public final void resize(Dot start, Dot end) {
        Point startLocation = start.getStartLocation();
        Point endLocation = end.getEndLocation();

        if (start.getParamType() == Dot.ParamType.Both) {
            startLocation.x = endLocation.x - MARGIN * 2;
            pointsSize = 3;
            points[0].setLocation(startLocation);
            points[1].x = startLocation.x;
            points[1].y = endLocation.y;
            points[2].setLocation(endLocation);
            if (startLocation.y <= endLocation.y) {
                corners[0] = Corner.Bottom;
                corners[1] = Corner.BottomRight;
                corners[2] = Corner.None;
            } else {
                corners[0] = Corner.Top;
                corners[1] = Corner.TopRight;
                corners[2] = Corner.None;
            }
        } else if (end.getParamType() == Dot.ParamType.Both) {
            endLocation.x = startLocation.x + MARGIN * 2;
            pointsSize = 3;
            points[0].setLocation(startLocation);
            points[1].x = endLocation.x;
            points[1].y = startLocation.y;
            points[2].setLocation(endLocation);
            if (startLocation.y <= endLocation.y) {
                corners[0] = Corner.None;
                corners[1] = Corner.RightBottom;
                corners[2] = Corner.Bottom;
            } else {
                corners[0] = Corner.None;
                corners[1] = Corner.RightTop;
                corners[2] = Corner.Top;
            }
        } else if (startLocation.x + MARGIN <= endLocation.x - MARGIN) {
            pointsSize = 4;
            points[0].setLocation(startLocation);
            points[1].x = getVMiddleStart();
            points[1].y = startLocation.y;
            points[2].x = getVMiddleStart();
            points[2].y = endLocation.y;
            corners[0] = Corner.None;
            corners[3] = Corner.None;
            points[3].setLocation(endLocation);
            if (startLocation.y <= endLocation.y) {
                corners[1] = Corner.RightBottom;
                corners[2] = Corner.BottomRight;
            } else {
                corners[1] = Corner.RightTop;
                corners[2] = Corner.TopRight;
            }

        } else {
            pointsSize = 6;
            points[0].setLocation(startLocation);
            points[5].setLocation(endLocation);
            points[1].x = getVMiddleStart();
            points[1].y = startLocation.y;

            points[4].x = getVMiddleEnd();
            points[4].y = endLocation.y;
            corners[0] = Corner.None;
            corners[5] = Corner.None;
            if ((start.getNode().getLocation().y + start.getNode().getHeight() + MARGIN
                    > end.getNode().getLocation().y - MARGIN)
                    && (end.getNode().getLocation().y + end.getNode().getHeight() + MARGIN
                    > start.getNode().getLocation().y - MARGIN)) {

                if (startLocation.y + MARGIN <= endLocation.y - MARGIN) {
                    points[1].x = getVMiddleStartClampedRight();
                    points[2].x = getVMiddleStartClampedRight();
                } else {
                    points[1].x = getVMiddleStart();
                    points[2].x = getVMiddleStart();
                }
                points[2].y = getHBottom();

                if (startLocation.y + MARGIN > endLocation.y - MARGIN) {
                    points[3].x = getVMiddleEndClampedLeft();
                    points[4].x = getVMiddleEndClampedLeft();

                } else {
                    points[3].x = getVMiddleEnd();
                    points[4].x = getVMiddleEnd();
                }

                points[3].y = getHBottom();

                corners[1] = Corner.RightBottom;
                corners[2] = Corner.BottomLeft;
                corners[3] = Corner.LeftTop;
                corners[4] = Corner.TopRight;

            } else {

                points[2].x = getVMiddleStart();
                points[2].y = getHMiddle();

                points[3].x = getVMiddleEnd();
                points[3].y = getHMiddle();


                if (startLocation.y <= endLocation.y) {
                    corners[1] = Corner.RightBottom;
                    corners[2] = Corner.BottomLeft;
                    corners[3] = Corner.LeftBottom;
                    corners[4] = Corner.BottomRight;
                } else {
                    corners[1] = Corner.RightTop;
                    corners[2] = Corner.TopLeft;
                    corners[3] = Corner.LeftTop;
                    corners[4] = Corner.TopRight;
                }
            }
        }
        updateBounds();
    }

    private void updateBounds() {
        int minX = Integer.MAX_VALUE, minY = Integer.MAX_VALUE, maxX = Integer.MIN_VALUE, maxY = Integer.MIN_VALUE;
        for (int i = 0; i < pointsSize; i++) {
            if (points[i].x < minX) {
                minX = points[i].x;
            }
            if (points[i].y < minY) {
                minY = points[i].y;
            }

            if (points[i].x > maxX) {
                maxX = points[i].x;
            }
            if (points[i].y > maxY) {
                maxY = points[i].y;
            }
        }
        maxX += MARGIN;
        maxY += MARGIN;
        minX -= MARGIN;
        minY -= MARGIN;

        setLocation(minX, minY);
        setSize(maxX - minX, maxY - minY);
    }

    private Diagram getDiagram() {
        return (Diagram) start.getDiagram();
    }

    @Override
    public void mouseDragged(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    private void dispatchEventToDiagram(MouseEvent e) {
        MouseEvent me = null;
        me = convertEvent(e);
        getDiagram().dispatchEvent(me);
    }

    @Override
    public void mouseMoved(MouseEvent e) {
        dispatchEventToDiagram(e);
    }
    private boolean paintDebug = false;

    private void debug() {
        paintDebug = true;
        repaint();
    }

    @Override
    public void mouseClicked(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    @Override
    public void mousePressed(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    @Override
    public void mouseReleased(MouseEvent e) {
        dispatchEventToDiagram(e);
    }

    public void select(MouseEvent e) {
        boolean selected = false;
        requestFocusInWindow(true);
        for (int i = 0; i < pointsSize - 1; i++) {
            translate(points[i], p1);
            translate(points[i + 1], p2);
            if (p1.x > p2.x || p1.y > p2.y) {
                tp1.setLocation(p1);
                p1.setLocation(p2);
                p2.setLocation(tp1);
            }

            p1.x -= MARGIN / 2;
            p1.y -= MARGIN / 2;

            p2.x += MARGIN / 2;
            p2.y += MARGIN / 2;


            if (e.getX() >= p1.x && e.getX() <= p2.x
                    && e.getY() >= p1.y && e.getY() <= p2.y) {
                selected = true;
            }
        }

        if (selected) {
            getDiagram().select(this);
            e.consume();
        }
    }

    @Override
    public void mouseEntered(MouseEvent e) {
    }

    @Override
    public void mouseExited(MouseEvent e) {
    }

    @Override
    public void keyTyped(KeyEvent e) {
    }

    @Override
    public void keyPressed(KeyEvent e) {

        if (e.getKeyCode() == KeyEvent.VK_DELETE) {
            Diagram diag = getDiagram();
            if (diag.selectedItem == this) {
                diag.removeSelectedConnection();
            }
        }
    }

    @Override
    public void keyReleased(KeyEvent e) {
    }

    public void componentResized(ComponentEvent e) {
    }

    public void componentMoved(ComponentEvent e) {
        resize(start, end);
    }

    public void componentShown(ComponentEvent e) {
    }

    public void componentHidden(ComponentEvent e) {
    }

    public void propertyChange(PropertyChangeEvent evt) {
        MappingBlock mapping = (MappingBlock) evt.getSource();
        key = MaterialUtils.makeKey(mapping, getDiagram().getCurrentTechniqueName());
    }
}


File: sdk/jme3-materialeditor/src/com/jme3/gde/materialdefinition/editor/Diagram.java
/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package com.jme3.gde.materialdefinition.editor;

import com.jme3.gde.core.assets.ProjectAssetManager;
import com.jme3.gde.materialdefinition.dialog.AddAttributeDialog;
import com.jme3.gde.materialdefinition.dialog.AddMaterialParameterDialog;
import com.jme3.gde.materialdefinition.dialog.AddNodeDialog;
import com.jme3.gde.materialdefinition.dialog.AddWorldParameterDialog;
import com.jme3.gde.materialdefinition.fileStructure.ShaderNodeBlock;
import com.jme3.gde.materialdefinition.icons.Icons;
import com.jme3.material.Material;
import com.jme3.shader.Shader;
import com.jme3.shader.ShaderNodeDefinition;
import com.jme3.shader.ShaderNodeVariable;
import com.jme3.shader.UniformBinding;
import com.jme3.shader.VarType;
import java.awt.Color;
import java.awt.Component;
import java.awt.Cursor;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Point;
import java.awt.Rectangle;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.ComponentEvent;
import java.awt.event.ComponentListener;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.awt.event.MouseMotionListener;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import javax.swing.BorderFactory;
import javax.swing.Icon;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JPopupMenu;
import javax.swing.JScrollPane;
import javax.swing.JSeparator;
import javax.swing.JViewport;
import javax.swing.SwingUtilities;
import javax.swing.border.Border;
import javax.swing.border.TitledBorder;

/**
 *
 * @author Nehon
 */
public class Diagram extends JPanel implements MouseListener, MouseMotionListener, ComponentListener {

    protected Dot draggedFrom;
    protected Dot draggedTo;
    protected Selectable selectedItem;
    protected List<Connection> connections = new ArrayList<Connection>();
    protected List<NodePanel> nodes = new ArrayList<NodePanel>();
    protected List<OutBusPanel> outBuses = new ArrayList<OutBusPanel>();
    private final MyMenu contextMenu = new MyMenu("Add");
    private MatDefEditorlElement parent;
    private String currentTechniqueName;
    private final BackdropPanel backDrop = new BackdropPanel();

    @SuppressWarnings("LeakingThisInConstructor")
    public Diagram() {

        addMouseListener(this);
        addMouseMotionListener(this);
        createPopupMenu();
    }

    @Override
    public void mouseClicked(MouseEvent e) {
    }

    @Override
    public void mousePressed(MouseEvent e) {

        if (e.getButton() == MouseEvent.BUTTON1) {
            for (OutBusPanel outBusPanel : outBuses) {
                Point p = SwingUtilities.convertPoint(this, e.getX(), e.getY(), outBusPanel);
                if (outBusPanel.contains(p)) {
                    MouseEvent me = SwingUtilities.convertMouseEvent(this, e, outBusPanel);
                    outBusPanel.dispatchEvent(me);
                    if (me.isConsumed()) {
                        return;
                    }
                }
            }

            for (Connection connection : connections) {
                MouseEvent me = SwingUtilities.convertMouseEvent(this, e, connection);
                connection.select(me);
                if (me.isConsumed()) {
                    return;
                }
            }

            selectedItem = null;
            repaint();
        } else if (e.getButton() == MouseEvent.BUTTON2) {
            setCursor(hndCursor);
            pp.setLocation(e.getPoint());
            ((JScrollPane) getParent().getParent()).setWheelScrollingEnabled(false);
        }
    }

    public void refreshPreviews(Material mat, String technique) {
        for (OutBusPanel outBusPanel : outBuses) {
            outBusPanel.updatePreview(mat, technique);
        }
        if (backDrop.isVisible()) {
            backDrop.showMaterial(mat, technique);
        }
    }

    public void displayBackdrop() {
        if (backDrop.getParent() == null) {
            add(backDrop);
            ((JViewport) getParent()).addChangeListener(backDrop);
        }

        backDrop.setVisible(true);
        backDrop.update(((JViewport) getParent()));
    }

    Point clickLoc = new Point(0, 0);

    @Override
    public void mouseReleased(MouseEvent e) {

        switch (e.getButton()) {
            case MouseEvent.BUTTON1:
                if (draggedFrom != null && draggedFrom.getNode() instanceof OutBusPanel) {
                    MouseEvent me = SwingUtilities.convertMouseEvent(this, e, draggedFrom.getNode());
                    draggedFrom.getNode().dispatchEvent(me);
                    if (me.isConsumed()) {
                        return;
                    }
                }

                dispatchToOutBuses(e);
                break;
            case MouseEvent.BUTTON2:
                setCursor(defCursor);
                ((JScrollPane) getParent().getParent()).setWheelScrollingEnabled(true);
                break;
            case MouseEvent.BUTTON3:
                contextMenu.show(this, e.getX(), e.getY());
                clickLoc.setLocation(e.getX(), e.getY());
                break;
        }

    }

    public MatDefEditorlElement getEditorParent() {
        return parent;
    }

    public void addConnection(Connection conn) {
        connections.add(conn);
        add(conn);
        for (OutBusPanel bus : outBuses) {
            setComponentZOrder(bus, getComponentCount() - 1);
        }
        repaint();
    }

    protected void showEdit(NodePanel node) {
        parent.showShaderEditor(node.getName(), node.getType(), node.filePaths);
    }

    public void notifyMappingCreation(Connection conn) {
        parent.makeMapping(conn);
    }

    public void addNode(NodePanel node) {
        add(node);
        node.setTechName(currentTechniqueName);
        node.setDiagram(this);
        nodes.add(node);
        setComponentZOrder(node, 0);
        node.addComponentListener(this);
    }

    public void addOutBus(OutBusPanel bus) {
        outBuses.add(bus);
        bus.setDiagram(this);
        add(bus);
        setComponentZOrder(bus, getComponentCount() - 1);
        addComponentListener(bus);
        bus.componentResized(new ComponentEvent(this, ActionEvent.ACTION_PERFORMED));
        bus.revalidate();
    }

    @Override
    public void mouseEntered(MouseEvent e) {
    }

    @Override
    public void mouseExited(MouseEvent e) {
    }

    protected void removeSelectedConnection() {
        if (selectedItem instanceof Connection) {
            Connection selectedConnection = (Connection) selectedItem;
            removeConnection(selectedConnection);
            selectedItem = null;
            parent.notifyRemoveConnection(selectedConnection);
        }
    }

    private String fixNodeName(String name) {
        return fixNodeName(name, 0);
    }

    private String fixNodeName(String name, int count) {
        for (NodePanel nodePanel : nodes) {
            if ((name + (count == 0 ? "" : count)).equals(nodePanel.getName())) {
                return fixNodeName(name, count + 1);
            }
        }
        return name + (count == 0 ? "" : count);
    }

    public void addNodesFromDefs(List<ShaderNodeDefinition> defList, String path, Point clickPosition) {
        int i = 0;
        for (ShaderNodeDefinition def : defList) {
            ShaderNodeBlock sn = new ShaderNodeBlock(def, path);
            sn.setName(fixNodeName(sn.getName()));

            NodePanel np = new NodePanel(sn, def);
            addNode(np);
            np.setLocation(clickPosition.x + i * 150, clickPosition.y);
            sn.setSpatialOrder(np.getLocation().x);
            i++;
            np.revalidate();
            getEditorParent().notifyAddNode(sn, def);
        }
        repaint();
    }

    public void addMatParam(String type, String name, Point point) {
        String fixedType = type;
        if (type.equals("Color")) {
            fixedType = "Vector4";
        }
        ShaderNodeVariable param = new ShaderNodeVariable(VarType.valueOf(fixedType).getGlslType(), name);
        NodePanel np = new NodePanel(param, NodePanel.NodeType.MatParam);
        addNode(np);
        np.setLocation(point.x, point.y);
        np.revalidate();
        repaint();
        getEditorParent().notifyAddMapParam(type, name);
    }

    public void addWorldParam(UniformBinding binding, Point point) {

        ShaderNodeVariable param = new ShaderNodeVariable(binding.getGlslType(), binding.name());
        NodePanel np = new NodePanel(param, NodePanel.NodeType.WorldParam);
        addNode(np);
        np.setLocation(point.x, point.y);
        np.revalidate();
        repaint();
        getEditorParent().notifyAddWorldParam(binding.name());
    }

    public void addAttribute(String name, String type, Point point) {
        ShaderNodeVariable param = new ShaderNodeVariable(type, "Attr", name);
        NodePanel np = new NodePanel(param, NodePanel.NodeType.Attribute);
        addNode(np);
        np.setLocation(point.x, point.y);
        np.revalidate();
        repaint();
    }

    protected void removeSelectedNode() {
        if (selectedItem instanceof NodePanel) {
            int result = JOptionPane.showConfirmDialog(null, "Delete this node and all its mappings?", "Delete Shader Node", JOptionPane.OK_CANCEL_OPTION);
            if (result == JOptionPane.OK_OPTION) {
                NodePanel selectedNode = (NodePanel) selectedItem;
                nodes.remove(selectedNode);
                for (Iterator<Connection> it = connections.iterator(); it.hasNext();) {
                    Connection conn = it.next();
                    if (conn.start.getNode() == selectedNode || conn.end.getNode() == selectedNode) {
                        it.remove();
                        conn.end.disconnect();
                        conn.start.disconnect();
                        remove(conn);
                    }
                }

                selectedNode.cleanup();
                remove(selectedNode);
                selectedItem = null;
                repaint();
                parent.notifyRemoveNode(selectedNode);
            }
        }
    }

    private final Cursor defCursor = Cursor.getPredefinedCursor(Cursor.DEFAULT_CURSOR);
    private final Cursor hndCursor = Cursor.getPredefinedCursor(Cursor.MOVE_CURSOR);
    private final Point pp = new Point();

    @Override
    public void mouseDragged(MouseEvent e) {
        if (SwingUtilities.isLeftMouseButton(e)) {
            if (draggedFrom == null) {
                if (selectedItem instanceof OutBusPanel) {
                    OutBusPanel bus = (OutBusPanel) selectedItem;
                    MouseEvent me = SwingUtilities.convertMouseEvent(this, e, bus);
                    bus.dispatchEvent(me);
                }
            }
        } else if (SwingUtilities.isMiddleMouseButton(e)) {
            JViewport vport = (JViewport) getParent();
            Point cp = e.getPoint();
            Point vp = vport.getViewPosition();
            vp.translate(pp.x - cp.x, pp.y - cp.y);
            scrollRectToVisible(new Rectangle(vp, vport.getSize()));
            //pp.setLocation(cp);

        }
    }

    protected void draggingDot(MouseEvent e) {
        for (OutBusPanel outBusPanel : outBuses) {
            Point p = SwingUtilities.convertPoint(this, e.getX(), e.getY(), outBusPanel);
            if (outBusPanel.contains(p)) {
                MouseEvent me = SwingUtilities.convertMouseEvent(this, e, outBusPanel);
                outBusPanel.draggingDot(me);
                if (me.isConsumed()) {
                    return;
                }
            }
        }
    }

    public Connection connect(Dot start, Dot end) {
        Connection conn = new Connection(start, end);
        start.connect(conn);
        end.connect(conn);

        addConnection(conn);

        return conn;
    }

    public NodePanel getNodePanel(String key) {
        for (NodePanel nodePanel : nodes) {
            if (nodePanel.getKey().equals(key)) {
                return nodePanel;
            }
        }
        return null;
    }

    public OutBusPanel getOutBusPanel(String key) {
        for (OutBusPanel out : outBuses) {
            if (out.getKey().equals(key)) {
                return out;
            }
        }
        return null;
    }

    /**
     * selection from the editor. Select the item and notify the topComponent
     *
     * @param selectable
     */
    public void select(Selectable selectable) {
        parent.selectionChanged(doSelect(selectable));
    }

    /**
     * do select the item and repaint the diagram
     *
     * @param selectable
     * @return
     */
    private Selectable doSelect(Selectable selectable) {
        this.selectedItem = selectable;
        if (selectable instanceof Component) {
            ((Component) selectable).requestFocusInWindow();
        }
        repaint();
        return selectable;
    }

    /**
     * find the item with the given key and select it without notifying the
     * topComponent
     *
     * @param key
     * @return
     */
    public Selectable select(String key) {

        for (NodePanel nodePanel : nodes) {
            if (nodePanel.getKey().equals(key)) {
                return doSelect(nodePanel);
            }
        }

        for (Connection connection : connections) {
            if (connection.getKey().equals(key)) {
                return doSelect(connection);
            }
        }

        for (OutBusPanel outBusPanel : outBuses) {
            if (outBusPanel.getKey().equals(key)) {
                return doSelect(outBusPanel);
            }
        }

        return doSelect(null);
    }

    @Override
    public void mouseMoved(MouseEvent e) {
        dispatchToOutBuses(e);
    }

    private JMenuItem createMenuItem(String text, Icon icon) {
        JMenuItem item = new JMenuItem(text, icon);
        item.setFont(new Font("Tahoma", 1, 10)); // NOI18N
        return item;
    }

    public void clear() {
        removeAll();
        outBuses.clear();
        connections.clear();
        nodes.clear();
    }

    private void createPopupMenu() {
        contextMenu.setFont(new Font("Tahoma", 1, 10)); // NOI18N
        contextMenu.setOpaque(true);
        Border titleUnderline = BorderFactory.createMatteBorder(1, 0, 0, 0, Color.BLACK);
        TitledBorder labelBorder = BorderFactory.createTitledBorder(
                titleUnderline, contextMenu.getLabel(),
                TitledBorder.LEADING, TitledBorder.ABOVE_TOP, contextMenu.getFont(), Color.BLACK);

        contextMenu.setBorder(BorderFactory.createLineBorder(Color.BLACK));
        contextMenu.setBorder(BorderFactory.createCompoundBorder(contextMenu.getBorder(),
                labelBorder));

        JMenuItem nodeItem = createMenuItem("Node", Icons.node);
        nodeItem.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                AddNodeDialog d = new AddNodeDialog(null, true, parent.obj.getLookup().lookup(ProjectAssetManager.class), Diagram.this, clickLoc);
                d.setLocationRelativeTo(null);
                d.setVisible(true);
            }
        });

        contextMenu.add(nodeItem);
        contextMenu.add(createSeparator());
        JMenuItem matParamItem = createMenuItem("Material Parameter", Icons.mat);
        matParamItem.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                AddMaterialParameterDialog d = new AddMaterialParameterDialog(null, true, Diagram.this, clickLoc);
                d.setLocationRelativeTo(null);
                d.setVisible(true);
            }
        });
        contextMenu.add(matParamItem);
        JMenuItem worldParamItem = createMenuItem("World Parameter", Icons.world);
        worldParamItem.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                AddWorldParameterDialog d = new AddWorldParameterDialog(null, true, Diagram.this, clickLoc);
                d.setLocationRelativeTo(null);
                d.setVisible(true);
            }
        });
        contextMenu.add(worldParamItem);
        JMenuItem attributeItem = createMenuItem("Attribute", Icons.attrib);
        attributeItem.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                AddAttributeDialog d = new AddAttributeDialog(null, true, Diagram.this, clickLoc);
                d.setLocationRelativeTo(null);
                d.setVisible(true);
            }
        });
        contextMenu.add(attributeItem);
        contextMenu.add(createSeparator());
        JMenuItem outputItem = createMenuItem("Output color", Icons.output);
        contextMenu.add(outputItem);
        outputItem.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                OutBusPanel p2 = new OutBusPanel("color" + (outBuses.size() - 1), Shader.ShaderType.Fragment);
                p2.setBounds(0, 350 + 50 * (outBuses.size() - 1), p2.getWidth(), p2.getHeight());

                addOutBus(p2);

            }
        });
    }

    private JSeparator createSeparator() {
        JSeparator jsep = new JSeparator(JSeparator.HORIZONTAL);
        jsep.setBackground(Color.BLACK);
        return jsep;
    }

    private void dispatchToOutBuses(MouseEvent e) {
        for (OutBusPanel outBusPanel : outBuses) {
            Point p = SwingUtilities.convertPoint(this, e.getX(), e.getY(), outBusPanel);
            if (outBusPanel.contains(p)) {
                MouseEvent me = SwingUtilities.convertMouseEvent(this, e, outBusPanel);
                outBusPanel.dispatchEvent(me);
                if (me.isConsumed()) {
                    return;
                }
            }
        }
    }

    private void removeConnection(Connection selectedConnection) {
        connections.remove(selectedConnection);
        selectedConnection.end.disconnect();
        selectedConnection.start.disconnect();
        remove(selectedConnection);
    }

    private class MyMenu extends JPopupMenu {

        public MyMenu(String label) {
            super(label);
        }

    }

    public void fixSize() {
        int maxWidth = minWidth;
        int maxHeight = minHeight;

        for (NodePanel nodePanel : nodes) {
            int w = nodePanel.getLocation().x + nodePanel.getWidth() + 150;
            if (w > maxWidth) {
                maxWidth = w;
            }
            int h = nodePanel.getLocation().y + nodePanel.getHeight();
            if (h > maxHeight) {
                maxHeight = h;
            }
        }
        for (OutBusPanel outBusPanel : outBuses) {
            int h = outBusPanel.getLocation().y + outBusPanel.getHeight();
            if (h > maxHeight) {
                maxHeight = h;
            }
        }
        setPreferredSize(new Dimension(maxWidth, maxHeight));
        revalidate();
    }
    int minWidth = 0;
    int minHeight = 0;

    public void componentResized(ComponentEvent e) {
        minWidth = e.getComponent().getWidth() - 2;
        minHeight = e.getComponent().getHeight() - 2;
        fixSize();
    }

    public void autoLayout() {

        int offset = 550;
        for (OutBusPanel outBus : outBuses) {
            if (outBus.getKey().equalsIgnoreCase("position")) {
                outBus.setLocation(0, 100);
                
            } else {
                outBus.setLocation(0, offset);
                offset += 260;
            }
            getEditorParent().savePositionToMetaData(outBus.getKey(), outBus.getLocation().x, outBus.getLocation().y);
        }
        offset = 0;
        String keys = "";
        for (NodePanel node : nodes) {

            if (node.getType() == NodePanel.NodeType.Vertex || node.getType() == NodePanel.NodeType.Fragment) {
                node.setLocation(offset + 200, getNodeTop(node));
                getEditorParent().savePositionToMetaData(node.getKey(), node.getLocation().x, node.getLocation().y);
                int pad = getNodeTop(node);
                for (Connection connection : connections) {
                    if (connection.getEnd().getNode() == node) {
                        if (connection.getStart().getNode() instanceof NodePanel) {
                            NodePanel startP = (NodePanel) connection.getStart().getNode();
                            if (startP.getType() != NodePanel.NodeType.Vertex && startP.getType() != NodePanel.NodeType.Fragment) {
                                startP.setLocation(offset + 30, pad);
                                getEditorParent().savePositionToMetaData(startP.getKey(), startP.getLocation().x, startP.getLocation().y);
                                keys += startP.getKey() + "|";
                                pad += 50;
                            }
                        }
                    }
                }
            }
            offset += 320;
        }
        offset = 0;
        for (NodePanel node : nodes) {
            if (node.getType() != NodePanel.NodeType.Vertex && node.getType() != NodePanel.NodeType.Fragment && !(keys.contains(node.getKey()))) {
                node.setLocation(offset + 10, 0);
                getEditorParent().savePositionToMetaData(node.getKey(), node.getLocation().x, node.getLocation().y);
                offset += 130;
            }
        }

    }

    private int getNodeTop(NodePanel node) {
        if (node.getType() == NodePanel.NodeType.Vertex) {
            return 150;
        }
        if (node.getType() == NodePanel.NodeType.Fragment) {
            return 400;
        }
        return 0;

    }

    public void componentMoved(ComponentEvent e) {
    }

    public void componentShown(ComponentEvent e) {
    }

    public void componentHidden(ComponentEvent e) {
    }

    public void setParent(MatDefEditorlElement parent) {
        this.parent = parent;
    }

    public void setCurrentTechniqueName(String currentTechniqueName) {
        this.currentTechniqueName = currentTechniqueName;
    }

    public String getCurrentTechniqueName() {
        return currentTechniqueName;
    }
}


File: sdk/jme3-materialeditor/src/com/jme3/gde/materialdefinition/editor/DraggablePanel.java
/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package com.jme3.gde.materialdefinition.editor;

import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.awt.event.MouseMotionListener;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;

/**
 *
 * @author Nehon
 */
public class DraggablePanel extends JPanel implements MouseListener, MouseMotionListener {

    protected int svdx, svdy, svdex, svdey;
    private boolean vertical = false;
    protected Diagram diagram;

    public DraggablePanel(boolean vertical) {
        this();
        this.vertical = vertical;
    }

    public DraggablePanel() {
        addMouseListener(this);
        addMouseMotionListener(this);
    }

    @Override
    public void mouseClicked(MouseEvent e) {
    }

    @Override
    public void mousePressed(MouseEvent e) {
        if (e.getButton() != MouseEvent.BUTTON2) {
            svdx = getLocation().x;
            if (!vertical) {
                svdex = e.getXOnScreen();
            }
            svdy = getLocation().y;
            svdey = e.getYOnScreen();
            e.consume();
        }
    }

    @Override
    public void mouseReleased(MouseEvent e) {
    }

    @Override
    public void mouseEntered(MouseEvent e) {
    }

    @Override
    public void mouseExited(MouseEvent e) {
    }

    @Override
    public void mouseMoved(MouseEvent e) {
    }

    @Override
    public void mouseDragged(MouseEvent e) {
        if (!SwingUtilities.isMiddleMouseButton(e)) {
            int xoffset = 0;
            if (!vertical) {
                xoffset = e.getLocationOnScreen().x - svdex;
            }
            int yoffset = e.getLocationOnScreen().y - svdey;
            setLocation(Math.max(0, svdx + xoffset), Math.max(0, svdy + yoffset));
            e.consume();
        }
    }

    public Diagram getDiagram() {
        return diagram;
    }

    public void setDiagram(Diagram diagram) {
        this.diagram = diagram;
    }
}


File: sdk/jme3-materialeditor/src/com/jme3/gde/materialdefinition/editor/NodePanel.java
/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package com.jme3.gde.materialdefinition.editor;

import com.jme3.gde.materialdefinition.fileStructure.ShaderNodeBlock;
import com.jme3.gde.materialdefinition.fileStructure.leaves.DefinitionBlock;
import com.jme3.gde.materialdefinition.fileStructure.leaves.InputMappingBlock;
import com.jme3.gde.materialdefinition.fileStructure.leaves.OutputMappingBlock;
import com.jme3.gde.materialdefinition.icons.Icons;
import com.jme3.shader.Shader;
import com.jme3.shader.ShaderNodeDefinition;
import com.jme3.shader.ShaderNodeVariable;
import java.awt.Color;
import java.awt.Font;
import java.awt.GradientPaint;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RadialGradientPaint;
import java.awt.RenderingHints;
import java.awt.event.KeyEvent;
import java.awt.event.KeyListener;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import java.util.ArrayList;
import java.util.List;
import javax.swing.GroupLayout;
import javax.swing.ImageIcon;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.LayoutStyle;
import javax.swing.SwingConstants;
import javax.swing.SwingUtilities;
import org.openide.util.WeakListeners;

/**
 *
 * @author Nehon
 */
public class NodePanel extends DraggablePanel implements Selectable, PropertyChangeListener, InOut, KeyListener {

    List<JLabel> inputLabels = new ArrayList<JLabel>();
    List<JLabel> outputLabels = new ArrayList<JLabel>();
    List<Dot> inputDots = new ArrayList<Dot>();
    List<Dot> outputDots = new ArrayList<Dot>();
    private NodeType type = NodeType.Vertex;
    private JPanel content;
    private JLabel header;
    private Color color;
    private String name;
    private String techName;
    private NodeToolBar toolBar;
    protected List<String> filePaths = new ArrayList<String>();
    protected Shader.ShaderType shaderType;

//    private List listeners = Collections.synchronizedList(new LinkedList());
//
//    public void addPropertyChangeListener(PropertyChangeListener pcl) {
//        listeners.add(pcl);
//    }
//
//    public void removePropertyChangeListener(PropertyChangeListener pcl) {
//        listeners.remove(pcl);
//    }
//
//    protected void fire(String propertyName, Object old, Object nue) {
//        //Passing 0 below on purpose, so you only synchronize for one atomic call:
//        PropertyChangeListener[] pcls = (PropertyChangeListener[]) listeners.toArray(new PropertyChangeListener[0]);
//        for (int i = 0; i < pcls.length; i++) {
//            pcls[i].propertyChange(new PropertyChangeEvent(this, propertyName, old, nue));
//        }
//    }
    public enum NodeType {

        Vertex(new Color(220, 220, 70)),//yellow
        Fragment(new Color(114, 200, 255)),//bleue
        Attribute(Color.WHITE),
        MatParam(new Color(70, 220, 70)),//green
        WorldParam(new Color(220, 70, 70)); //red
        private Color color;

        private NodeType() {
        }

        private NodeType(Color color) {
            this.color = color;
        }

        public Color getColor() {
            return color;
        }
    }

    /**
     * Creates new form NodePanel
     */
    @SuppressWarnings("LeakingThisInConstructor")
    public NodePanel(ShaderNodeBlock node, ShaderNodeDefinition def) {
        super();
        shaderType = def.getType();
        if (def.getType() == Shader.ShaderType.Vertex) {
            type = NodePanel.NodeType.Vertex;
        } else {
            type = NodePanel.NodeType.Fragment;
        }
        init(def.getInputs(), def.getOutputs());

        node.addPropertyChangeListener(WeakListeners.propertyChange(this, node));
        this.addPropertyChangeListener(WeakListeners.propertyChange(node, this));
        refresh(node);
        addKeyListener(this);
        this.filePaths.addAll(def.getShadersPath());
        String defPath = ((DefinitionBlock) node.getContents().get(0)).getPath();
        this.filePaths.add(defPath);
        toolBar = new NodeToolBar(this);        
    }

    /**
     * Creates new form NodePanel
     */
    @SuppressWarnings("LeakingThisInConstructor")
    public NodePanel(ShaderNodeVariable singleOut, NodePanel.NodeType type) {
        super();
        List<ShaderNodeVariable> outputs = new ArrayList<ShaderNodeVariable>();
        outputs.add(singleOut);
        this.type = type;
        init(new ArrayList<ShaderNodeVariable>(), outputs);
        addKeyListener(this);
        toolBar = new NodeToolBar(this);
    }

    public final void refresh(ShaderNodeBlock node) {
        name = node.getName();
        header.setText(node.getName());
        header.setToolTipText(node.getName());

    }

    public void propertyChange(PropertyChangeEvent evt) {
        if (evt.getPropertyName().equals("name")) {
            refresh((ShaderNodeBlock) evt.getSource());
        }
    }

    private void init(List<ShaderNodeVariable> inputs, List<ShaderNodeVariable> outputs) {

        setBounds(0, 0, 120, 30 + inputs.size() * 20 + outputs.size() * 20);

        for (ShaderNodeVariable input : inputs) {

            JLabel label = createLabel(input.getType(), input.getName(), Dot.ParamType.Input);
            Dot dot = createDot(input.getType(), Dot.ParamType.Input, input.getName());
            inputLabels.add(label);
            inputDots.add(dot);
        }
        int index = 0;
        for (ShaderNodeVariable output : outputs) {
            String outName = output.getName();
            JLabel label = createLabel(output.getType(), outName, Dot.ParamType.Output);
            Dot dot = createDot(output.getType(), Dot.ParamType.Output, outName);
            dot.setIndex(index++);
            outputLabels.add(label);
            outputDots.add(dot);
        }

        initComponents();
        updateType();
        setOpaque(false);

    }

    public void setTitle(String s) {
        header.setText(s);
        header.setToolTipText(s);
    }

    public Dot getInputConnectPoint(String varName) {
        return getConnectPoint(inputLabels, varName, inputDots);
    }

    public Dot getOutputConnectPoint(String varName) {
        return getConnectPoint(outputLabels, varName, outputDots);
    }

    private Dot getConnectPoint(List<JLabel> list, String varName, List<Dot> listDot) {
        if (varName.startsWith("m_") || varName.startsWith("g_")) {
            varName = varName.substring(2);
        }
        for (int i = 0; i < list.size(); i++) {
            if (list.get(i).getText().equals(varName)) {
                return listDot.get(i);
            }
        }
        return null;
    }

    @Override
    protected void paintComponent(Graphics g1) {
        Graphics2D g = (Graphics2D) g1;
        Color boderColor = Color.BLACK;
        if (diagram.selectedItem == this) {
            boderColor = Color.WHITE;
        }
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, // Anti-alias!
                RenderingHints.VALUE_ANTIALIAS_ON);
        // Color[] colors = {new Color(0, 0, 0, 0.7f), new Color(0, 0, 0, 0.15f)};
        if (diagram.selectedItem == this) {
            Color[] colors = new Color[]{new Color(0.6f, 0.6f, 1.0f, 0.8f), new Color(0.6f, 0.6f, 1.0f, 0.5f)};
            float[] factors = {0f, 1f};
            g.setPaint(new RadialGradientPaint(getWidth() / 2, getHeight() / 2, getWidth() / 2, factors, colors));
            g.fillRoundRect(8, 3, getWidth() - 10, getHeight() - 6, 15, 15);
        }else{
            if(toolBar.isVisible()){
                toolBar.setVisible(false);
            }
        }

        g.setColor(new Color(170, 170, 170, 120));
        g.fillRoundRect(5, 1, getWidth() - 9, getHeight() - 6, 15, 15);
        g.setColor(boderColor);

        g.drawRoundRect(4, 0, getWidth() - 9, getHeight() - 6, 15, 15);
        g.setColor(new Color(170, 170, 170, 120));
        g.fillRect(4, 1, 10, 10);
        g.setColor(boderColor);
        g.drawLine(4, 0, 14, 0);
        g.drawLine(4, 0, 4, 10);
        g.setColor(Color.BLACK);
        g.drawLine(5, 15, getWidth() - 6, 15);
        g.setColor(new Color(190, 190, 190));
        g.drawLine(5, 16, getWidth() - 6, 16);

        Color c1 = new Color(color.getRed(), color.getGreen(), color.getBlue(), 150);
        Color c2 = new Color(color.getRed(), color.getGreen(), color.getBlue(), 0);
        g.setPaint(new GradientPaint(0, 15, c1, getWidth(), 15, c2));
        g.fillRect(5, 1, getWidth() - 10, 14);

    }

    public String getKey() {
        switch (type) {
            case Attribute:
                return "Attr." + outputLabels.get(0).getText();
            case WorldParam:
                return "WorldParam." + outputLabels.get(0).getText();
            case MatParam:
                return "MatParam." + outputLabels.get(0).getText();
            default:
                return techName + "/" + name;
        }
    }

    @Override
    public String getName() {
        return name;
    }

    @Override
    public void mousePressed(MouseEvent e) {
        super.mousePressed(e);
        diagram.select(this);
        showToolBar();
    }
    
    private void showToolBar(){
        toolBar.display();
    }

    public NodeType getType() {
        return type;
    }

    @Override
    public void mouseReleased(MouseEvent e) {
        diagram.fixSize();
        if (svdx != getLocation().x) {
            firePropertyChange(ShaderNodeBlock.POSITION, svdx, getLocation().x);
            getDiagram().getEditorParent().savePositionToMetaData(getKey(), getLocation().x, getLocation().y);
        }
    }

    public final void updateType() {

        switch (type) {
            case Vertex:
                header.setIcon(Icons.vert);
                break;
            case Fragment:
                header.setIcon(Icons.frag);
                break;
            case Attribute:
                header.setIcon(Icons.attrib);
                header.setText("Attribute");
                header.setToolTipText("Attribute");
                name = "Attr";
                break;
            case WorldParam:
                header.setIcon(Icons.world);
                header.setText("WorldParam");
                header.setToolTipText("WorldParam");
                name = "WorldParam";
                break;
            case MatParam:
                header.setIcon(Icons.mat);
                header.setText("MatParam");
                header.setToolTipText("MatParam");
                name = "MatParam";
                break;
        }
        color = type.getColor();
    }

    public void edit() {
        if (type == NodeType.Fragment || type == NodeType.Vertex) {
            diagram.showEdit(NodePanel.this);
        }
    }
    
    public void cleanup(){
        toolBar.getParent().remove(toolBar);
    }

    /**
     * This method is called from within the constructor to initialize the form.
     * WARNING: Do NOT modify this code. The content of this method is always
     * regenerated by the Form Editor.
     */
    @SuppressWarnings("unchecked")
    // <editor-fold defaultstate="collapsed" desc="Generated Code">                          
    private void initComponents() {

        ImageIcon icon = Icons.vert;
        if (type == NodeType.Fragment) {
            icon = Icons.frag;
        }
        header = new JLabel(icon);
        header.setForeground(Color.BLACK);
        header.addMouseListener(labelMouseMotionListener);
        header.addMouseMotionListener(labelMouseMotionListener);
        header.setHorizontalAlignment(SwingConstants.LEFT);
        header.setFont(new Font("Tahoma", Font.BOLD, 11));

        content = new JPanel();
        content.setOpaque(false);
        GroupLayout contentLayout = new GroupLayout(content);
        content.setLayout(contentLayout);

        int txtLength = 100;

        GroupLayout.ParallelGroup grpHoriz = contentLayout.createParallelGroup(GroupLayout.Alignment.LEADING);

        for (int i = 0; i < outputDots.size(); i++) {
            grpHoriz.addGroup(GroupLayout.Alignment.TRAILING, contentLayout.createSequentialGroup()
                    .addGap(0, 0, Short.MAX_VALUE)
                    .addComponent(outputLabels.get(i), GroupLayout.PREFERRED_SIZE, txtLength, GroupLayout.PREFERRED_SIZE)
                    .addGap(2, 2, 2)
                    .addComponent(outputDots.get(i), GroupLayout.PREFERRED_SIZE, 10, GroupLayout.PREFERRED_SIZE));
        }
        for (int i = 0; i < inputDots.size(); i++) {
            grpHoriz.addGroup(GroupLayout.Alignment.LEADING, contentLayout.createSequentialGroup()
                    .addComponent(inputDots.get(i), GroupLayout.PREFERRED_SIZE, 10, GroupLayout.PREFERRED_SIZE)
                    .addGap(2, 2, 2)
                    .addComponent(inputLabels.get(i), GroupLayout.PREFERRED_SIZE, txtLength, GroupLayout.PREFERRED_SIZE));
        }

        contentLayout.setHorizontalGroup(grpHoriz);

        GroupLayout.ParallelGroup grpVert = contentLayout.createParallelGroup(GroupLayout.Alignment.LEADING);

        GroupLayout.SequentialGroup grp = contentLayout.createSequentialGroup();
        for (int i = 0; i < inputDots.size(); i++) {
            grp.addGroup(contentLayout.createParallelGroup(GroupLayout.Alignment.CENTER)
                    .addComponent(inputDots.get(i), GroupLayout.PREFERRED_SIZE, GroupLayout.DEFAULT_SIZE, GroupLayout.PREFERRED_SIZE)
                    .addComponent(inputLabels.get(i))).addPreferredGap(LayoutStyle.ComponentPlacement.RELATED);
        }
        for (int i = 0; i < outputDots.size(); i++) {
            grp.addGroup(contentLayout.createParallelGroup(GroupLayout.Alignment.CENTER)
                    .addComponent(outputDots.get(i), GroupLayout.PREFERRED_SIZE, GroupLayout.DEFAULT_SIZE, GroupLayout.PREFERRED_SIZE)
                    .addComponent(outputLabels.get(i))).addPreferredGap(LayoutStyle.ComponentPlacement.RELATED);
        }

        grpVert.addGroup(GroupLayout.Alignment.TRAILING, grp);

        contentLayout.setVerticalGroup(grpVert);

        GroupLayout layout = new GroupLayout(this);
        this.setLayout(layout);
        layout.setHorizontalGroup(
                layout.createParallelGroup(GroupLayout.Alignment.LEADING)
                .addGroup(GroupLayout.Alignment.LEADING, layout.createSequentialGroup()
                        .addGap(6, 6, 6)
                        .addComponent(header, 100, 100, 100))
                .addGroup(GroupLayout.Alignment.LEADING, layout.createSequentialGroup()
                        .addGap(6, 6, 6))
                .addComponent(content, GroupLayout.Alignment.TRAILING, GroupLayout.DEFAULT_SIZE, GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE));
        layout.setVerticalGroup(
                layout.createParallelGroup(GroupLayout.Alignment.LEADING)
                .addGroup(layout.createSequentialGroup()
                        .addComponent(header, GroupLayout.PREFERRED_SIZE, GroupLayout.DEFAULT_SIZE, GroupLayout.PREFERRED_SIZE)
                        .addGap(10, 10, 10)
                        .addComponent(content, GroupLayout.PREFERRED_SIZE, GroupLayout.DEFAULT_SIZE, GroupLayout.PREFERRED_SIZE))
                .addGap(10, 10, 10));
    }

    public JLabel createLabel(String glslType, String txt, Dot.ParamType type) {
        JLabel label = new JLabel(txt);
        label.setForeground(Color.BLACK);
        label.setToolTipText(glslType + " " + txt);
        label.setOpaque(false);
        //label.setPreferredSize(new Dimension(50, 15));        
        label.setHorizontalAlignment(type == Dot.ParamType.Output ? SwingConstants.RIGHT : SwingConstants.LEFT);
        label.setFont(new Font("Tahoma", 0, 10));
        label.addMouseListener(labelMouseMotionListener);
        label.addMouseMotionListener(labelMouseMotionListener);
        // label.setBorder(BorderFactory.createLineBorder(Color.BLACK));
        return label;
    }

    public Dot createDot(String type, Dot.ParamType paramType, String paramName) {
        Dot dot1 = new Dot();
        dot1.setShaderTypr(shaderType);
        dot1.setNode(this);
        dot1.setText(paramName);
        dot1.setParamType(paramType);
        dot1.setType(type);
        return dot1;
    }

    public void keyTyped(KeyEvent e) {
    }

    @Override
    public void keyPressed(KeyEvent e) {

        if (e.getKeyCode() == KeyEvent.VK_DELETE) {
            delete();
        }
    }

    public void delete() {
        Diagram diag = getDiagram();
        if (diag.selectedItem == this) {
            diag.removeSelectedNode();
        }
    }

    public void keyReleased(KeyEvent e) {
    }
    // used to pass press and drag events to the NodePanel when they occur on the label
    private LabelMouseMotionListener labelMouseMotionListener = new LabelMouseMotionListener();

    private class LabelMouseMotionListener extends MouseAdapter {

        @Override
        public void mousePressed(MouseEvent e) {
            MouseEvent me = SwingUtilities.convertMouseEvent(e.getComponent(), e, NodePanel.this);
            NodePanel.this.dispatchEvent(me);
        }

        @Override
        public void mouseDragged(MouseEvent e) {
            MouseEvent me = SwingUtilities.convertMouseEvent(e.getComponent(), e, NodePanel.this);
            NodePanel.this.dispatchEvent(me);
        }

        @Override
        public void mouseReleased(MouseEvent e) {
            MouseEvent me = SwingUtilities.convertMouseEvent(e.getComponent(), e, NodePanel.this);
            NodePanel.this.dispatchEvent(me);
        }
    }

    public void setTechName(String techName) {
        this.techName = techName;
    }

    public void addInputMapping(InputMappingBlock block) {
        firePropertyChange(ShaderNodeBlock.INPUT, null, block);
    }

    public void removeInputMapping(InputMappingBlock block) {
        firePropertyChange(ShaderNodeBlock.INPUT, block, null);
    }

    public void addOutputMapping(OutputMappingBlock block) {
        firePropertyChange(ShaderNodeBlock.OUTPUT, null, block);
    }

    public void removeOutputMapping(OutputMappingBlock block) {
        firePropertyChange(ShaderNodeBlock.OUTPUT, block, null);
    }
}


File: sdk/jme3-materialeditor/src/com/jme3/gde/materialdefinition/editor/OutBusPanel.java
/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package com.jme3.gde.materialdefinition.editor;

import com.jme3.gde.core.scene.SceneApplication;
import com.jme3.gde.materialdefinition.fileStructure.leaves.InputMappingBlock;
import com.jme3.gde.materialdefinition.fileStructure.leaves.OutputMappingBlock;
import com.jme3.material.Material;
import com.jme3.shader.Shader;
import java.awt.Color;
import java.awt.GradientPaint;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.LinearGradientPaint;
import java.awt.Point;
import java.awt.Polygon;
import java.awt.RenderingHints;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.ComponentEvent;
import java.awt.event.ComponentListener;
import java.awt.event.MouseEvent;
import javax.swing.GroupLayout;
import javax.swing.JLabel;
import javax.swing.SwingUtilities;

/**
 *
 * @author Nehon
 */
public class OutBusPanel extends DraggablePanel implements ComponentListener, Selectable, InOut {

    private Color color = new Color(220, 220, 70);
    private String name = "";
    private final InnerPanel panel;
    private final MatPanel preview;
    private final Shader.ShaderType type;

    public OutBusPanel(String name, Shader.ShaderType type) {
        super(true);
        this.type = type;
        if (type == Shader.ShaderType.Fragment) {
            this.color = new Color(114, 200, 255);
        }
        setBounds(0, 0, 300, 50);
        JLabel title = new JLabel();
        this.name = name;
        title.setFont(new java.awt.Font("Impact", 1, 15)); // NOI18N
        title.setForeground(new java.awt.Color(153, 153, 153));
        title.setHorizontalAlignment(javax.swing.SwingConstants.RIGHT);
        title.setText(name);
        setOpaque(false);
        panel = new InnerPanel();

        javax.swing.GroupLayout outBusPanel1Layout = new javax.swing.GroupLayout(this);
        this.setLayout(outBusPanel1Layout);
        outBusPanel1Layout.setHorizontalGroup(
                outBusPanel1Layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                .addGroup(javax.swing.GroupLayout.Alignment.TRAILING, outBusPanel1Layout.createSequentialGroup()
                .addContainerGap(70, 70)
                .addComponent(panel, 20, 200, Short.MAX_VALUE)
                .addComponent(title, GroupLayout.PREFERRED_SIZE, 70, GroupLayout.PREFERRED_SIZE)
                .addGap(30, 30, 30)));
        outBusPanel1Layout.setVerticalGroup(
                outBusPanel1Layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                .addGroup(outBusPanel1Layout.createSequentialGroup()
                .addContainerGap()
                .addComponent(title, javax.swing.GroupLayout.DEFAULT_SIZE, 28, Short.MAX_VALUE)
                .addContainerGap())
                .addGroup(outBusPanel1Layout.createSequentialGroup()
                .addContainerGap(20, 20)
                .addComponent(panel, 10, 10, 10)
                .addContainerGap()));

        preview = new MatPanel();
        addComponentListener(preview);

    }

    @Override
    public void setDiagram(final Diagram diagram) {
        super.setDiagram(diagram);
        // preview.setBounds(350,300,128,100);
        diagram.add(preview);
        preview.update(this);
        preview.setExpandActionListener(new ActionListener() {

            public void actionPerformed(ActionEvent e) {
                diagram.displayBackdrop();
            }
        });
        
    }
    
    public Shader.ShaderType getType(){
        return type;
    }
    
    @Override
    protected void paintComponent(Graphics g1) {
        Graphics2D g = (Graphics2D) g1;
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, // Anti-alias!
                RenderingHints.VALUE_ANTIALIAS_ON);

        int width = getWidth();
        int[] xs = {38, width - 30, width - 30, width, width - 30, width - 30, 38, 38};
        int[] ys = {10, 10, 0, getHeight() / 2, getHeight(), getHeight() - 10, getHeight() - 10, 10};

        Polygon p = new Polygon(xs, ys, 8);

        if (diagram.selectedItem == this) {
            int[] xs2 = {0, width - 30, width - 30, width, width - 32, width - 32, 0, 0};
            int[] ys2 = {10, 10, 0, getHeight() / 2 + 2, getHeight(), getHeight() - 8, getHeight() - 8, 10};

            Polygon p2 = new Polygon(xs2, ys2, 8);
            g.setPaint(new GradientPaint(0, 0, new Color(0.6f, 0.6f, 1.0f, 0.9f), 0, getHeight(), new Color(0.6f, 0.6f, 1.0f, 0.5f)));
            g.fillPolygon(p2);
        }

        Color c1 = new Color(50, 50, 50, 255);
        Color c2 = new Color(50, 50, 50, 80);
        g.setPaint(new GradientPaint(0, 0, c1, width, 0, c2));
        g.fillPolygon(p);
        g.fillRect(0, 10, 3, getHeight() - 20);
        g.fillRect(5, 10, 6, getHeight() - 20);
        g.fillRect(13, 10, 9, getHeight() - 20);
        g.fillRect(24, 10, 12, getHeight() - 20);


    }

    @Override
    public void componentResized(ComponentEvent e) {
        setSize(e.getComponent().getWidth(), 50);
    }

    @Override
    public void componentMoved(ComponentEvent e) {
    }

    @Override
    public void componentShown(ComponentEvent e) {
    }

    @Override
    public void componentHidden(ComponentEvent e) {
    }

    @Override
    public void mousePressed(MouseEvent e) {
        if (dispatchToInnerPanel(e)) {
            return;
        }
        super.mousePressed(e);
        diagram.select(this);
    }

    @Override
    public void mouseDragged(MouseEvent e) {
        if (panel.dragging == false) {
            super.mouseDragged(e);
        }
    }

    protected void draggingDot(MouseEvent e) {
        Point p = SwingUtilities.convertPoint(this, e.getX(), e.getY(), panel);
        if (panel.contains(p)) {
            MouseEvent me = SwingUtilities.convertMouseEvent(this, e, panel);
            panel.mouseEntered(me);
        } else {
            MouseEvent me = SwingUtilities.convertMouseEvent(this, e, panel);
            panel.mouseExited(me);
        }
    }

    public Dot getConnectPoint() {
        return panel;
    }

    public void updatePreview(Material mat, String technique) {
        if (type == Shader.ShaderType.Fragment) {
            preview.showMaterial(mat,technique);
        } else {
            Material vmat = mat.clone();            
            vmat.getAdditionalRenderState().setWireframe(true);
            preview.showMaterial(vmat,technique);
        }
    }

    @Override
    public String getName() {
        return "Global";
    }

    @Override
    public void mouseReleased(MouseEvent e) {
        diagram.fixSize();
        MouseEvent me = SwingUtilities.convertMouseEvent(this, e, panel);
        panel.mouseReleased(me);
        getDiagram().getEditorParent().savePositionToMetaData(getKey(), 0, getLocation().y);

    }

    public String getKey() {
        return name;
    }

    private boolean dispatchToInnerPanel(MouseEvent e) {
        Point p = SwingUtilities.convertPoint(this, e.getX(), e.getY(), panel);
        if (panel.contains(p)) {
            MouseEvent me = SwingUtilities.convertMouseEvent(this, e, panel);
            panel.dispatchEvent(me);
            if (me.isConsumed()) {
                return true;
            }
        }
        return false;
    }

    public void addInputMapping(InputMappingBlock block) {
    }

    public void removeInputMapping(InputMappingBlock block) {
    }

    public void addOutputMapping(OutputMappingBlock block) {
    }

    public void removeOutputMapping(OutputMappingBlock block) {
    }

    class InnerPanel extends Dot {

        boolean over = false;
        boolean dragging = false;

        public InnerPanel() {
            this.shaderType = OutBusPanel.this.type;            
            setOpaque(false);
            setNode(OutBusPanel.this);
            setParamType(Dot.ParamType.Both);
            setType("vec4");
            setText(name);
        }

        @Override
        protected void paintComponent(Graphics g1) {
            Graphics2D g = (Graphics2D) g1;
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, // Anti-alias!
                    RenderingHints.VALUE_ANTIALIAS_ON);

            Color c1 = new Color(color.getRed(), color.getGreen(), color.getBlue(), 255);
            Color c2 = new Color(color.getRed(), color.getGreen(), color.getBlue(), 0);
            g.setPaint(new LinearGradientPaint(0, 0, 0, getHeight(), new float[]{0, 0.5f, 1}, new Color[]{c2, c1, c2}));
            g.fillRoundRect(1, 1, getWidth() - 1, getHeight() - 1, 10, 10);

        }

        @Override
        public void mousePressed(MouseEvent e) {
            super.mousePressed(e);
            dragging = true;
        }

        @Override
        public void mouseDragged(MouseEvent e) {
            e.consume();
        }

        @Override
        public void mouseReleased(MouseEvent e) {
            super.mouseReleased(e);
            dragging = false;
        }

        @Override
        public void mouseEntered(MouseEvent e) {
            if (!over) {
                super.mouseEntered(e);
                over = true;
            }
        }

        @Override
        public void mouseExited(MouseEvent e) {
            if (over) {
                super.mouseExited(e);
                over = false;
            }
        }
    }
}
