Refactoring Types: ['Inline Method']
tools/checkstyle/checks/coding/AbstractNestedDepthCheck.java
////////////////////////////////////////////////////////////////////////////////
// checkstyle: Checks Java source code for adherence to a set of rules.
// Copyright (C) 2001-2015 the original author or authors.
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 2.1 of the License, or (at your option) any later version.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
////////////////////////////////////////////////////////////////////////////////

package com.puppycrawl.tools.checkstyle.checks.coding;

import com.puppycrawl.tools.checkstyle.api.Check;
import com.puppycrawl.tools.checkstyle.api.DetailAST;

/**
 * Abstract class which provides helpers functionality for nested checks.
 *
 * @author <a href="mailto:simon@redhillconsulting.com.au">Simon Harris</a>
 */
public abstract class AbstractNestedDepthCheck extends Check {
    /** maximum allowed nesting depth */
    private int max;
    /** current nesting depth */
    private int depth;

    /**
     * Creates new instance of checks.
     * @param max default allowed nesting depth.
     */
    public AbstractNestedDepthCheck(int max) {
        setMax(max);
    }

    @Override
    public final int[] getRequiredTokens() {
        return getDefaultTokens();
    }

    @Override
    public void beginTree(DetailAST rootAST) {
        depth = 0;
    }

    /**
     * Getter for maximum allowed nesting depth.
     * @return maximum allowed nesting depth.
     */
    public final int getMax() {
        return max;
    }

    /**
     * Setter for maximum allowed nesting depth.
     * @param max maximum allowed nesting depth.
     */
    public final void setMax(int max) {
        this.max = max;
    }

    /**
     * Increasing current nesting depth.
     * @param ast note which increases nesting.
     * @param messageId message id for logging error.
     */
    protected final void nestIn(DetailAST ast, String messageId) {
        if (depth > max) {
            log(ast, messageId, depth, max);
        }
        ++depth;
    }

    /** Decreasing current nesting depth */
    protected final void nestOut() {
        --depth;
    }
}


File: src/main/java/com/puppycrawl/tools/checkstyle/checks/coding/NestedForDepthCheck.java
////////////////////////////////////////////////////////////////////////////////
// checkstyle: Checks Java source code for adherence to a set of rules.
// Copyright (C) 2001-2015 the original author or authors.
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 2.1 of the License, or (at your option) any later version.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
////////////////////////////////////////////////////////////////////////////////

package com.puppycrawl.tools.checkstyle.checks.coding;

import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

/**
 * Check the number of nested <code>for</code> -statements. The maximum
 * number of nested layers can be configured. The default value is 1. Most of
 * the logic is implemented in the parent class. The code for the class is
 * copied from the NestedIfDepthCheck-class. The only difference is the
 * intercepted token (for instead of if). Example:
 * <pre>
 *  &lt;!-- Restricts nested for blocks to a specified depth (default = 1).
 *                                                                        --&gt;
 *  &lt;module name=&quot;com.puppycrawl.tools.checkstyle.checks.coding
 *                                            .CatchWithLostStackCheck&quot;&gt;
 *    &lt;property name=&quot;severity&quot; value=&quot;info&quot;/&gt;
 *    &lt;property name=&quot;max&quot; value=&quot;1&quot;/&gt;
 *  &lt;/module&gt;
 * </pre>
 * @author Alexander Jesse
 * @see com.puppycrawl.tools.checkstyle.checks.coding.AbstractNestedDepthCheck
 * @see com.puppycrawl.tools.checkstyle.checks.coding.NestedIfDepthCheck
 */
public final class NestedForDepthCheck extends AbstractNestedDepthCheck {

    /**
     * A key is pointing to the warning message text in "messages.properties"
     * file.
     */
    public static final String MSG_KEY = "nested.for.depth";

    /** default allowed nesting depth. */
    private static final int DEFAULT_MAX = 1;

    /** Creates new check instance with default allowed nesting depth. */
    public NestedForDepthCheck() {
        super(DEFAULT_MAX);
    }

    @Override
    public int[] getDefaultTokens() {
        return new int[] {TokenTypes.LITERAL_FOR};
    }

    @Override
    public int[] getAcceptableTokens() {
        return new int[] {TokenTypes.LITERAL_FOR};
    }

    @Override
    public void visitToken(DetailAST ast) {
        if (TokenTypes.LITERAL_FOR == ast.getType()) {
            nestIn(ast, MSG_KEY);
        }
    }

    @Override
    public void leaveToken(DetailAST ast) {
        if (TokenTypes.LITERAL_FOR == ast.getType()) {
            nestOut();
        }
    }
}


File: src/main/java/com/puppycrawl/tools/checkstyle/checks/coding/NestedIfDepthCheck.java
////////////////////////////////////////////////////////////////////////////////
// checkstyle: Checks Java source code for adherence to a set of rules.
// Copyright (C) 2001-2015 the original author or authors.
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 2.1 of the License, or (at your option) any later version.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
////////////////////////////////////////////////////////////////////////////////

package com.puppycrawl.tools.checkstyle.checks.coding;

import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;
import com.puppycrawl.tools.checkstyle.checks.CheckUtils;

/**
 * Restricts nested if-else blocks to a specified depth (default = 1).
 *
 * @author <a href="mailto:simon@redhillconsulting.com.au">Simon Harris</a>
 */
public final class NestedIfDepthCheck extends AbstractNestedDepthCheck {

    /**
     * A key is pointing to the warning message text in "messages.properties"
     * file.
     */
    public static final String MSG_KEY = "nested.if.depth";

    /** default allowed nesting depth. */
    private static final int DEFAULT_MAX = 1;

    /** Creates new check instance with default allowed nesting depth. */
    public NestedIfDepthCheck() {
        super(DEFAULT_MAX);
    }

    @Override
    public int[] getDefaultTokens() {
        return new int[] {TokenTypes.LITERAL_IF};
    }

    @Override
    public int[] getAcceptableTokens() {
        return new int[] {TokenTypes.LITERAL_IF};
    }

    @Override
    public void visitToken(DetailAST ast) {
        if (ast.getType() == TokenTypes.LITERAL_IF) {
            visitLiteralIf(ast);
        }
        else {
            throw new IllegalStateException(ast.toString());
        }
    }

    @Override
    public void leaveToken(DetailAST ast) {
        if (ast.getType() == TokenTypes.LITERAL_IF) {
            leaveLiteralIf(ast);
        }
        else {
            throw new IllegalStateException(ast.toString());
        }
    }

    /**
     * Increases current nesting depth.
     * @param literalIf node for if.
     */
    private void visitLiteralIf(DetailAST literalIf) {
        if (!CheckUtils.isElseIf(literalIf)) {
            nestIn(literalIf, MSG_KEY);
        }
    }

    /**
     * Decreases current nesting depth.
     * @param literalIf node for if.
     */
    private void leaveLiteralIf(DetailAST literalIf) {
        if (!CheckUtils.isElseIf(literalIf)) {
            nestOut();
        }
    }
}


File: src/main/java/com/puppycrawl/tools/checkstyle/checks/coding/NestedTryDepthCheck.java
////////////////////////////////////////////////////////////////////////////////
// checkstyle: Checks Java source code for adherence to a set of rules.
// Copyright (C) 2001-2015 the original author or authors.
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 2.1 of the License, or (at your option) any later version.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
////////////////////////////////////////////////////////////////////////////////

package com.puppycrawl.tools.checkstyle.checks.coding;

import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

/**
 * Restricts nested try-catch-finally blocks to a specified depth (default = 1).
 * @author <a href="mailto:simon@redhillconsulting.com.au">Simon Harris</a>
 */
public final class NestedTryDepthCheck extends AbstractNestedDepthCheck {

    /**
     * A key is pointing to the warning message text in "messages.properties"
     * file.
     */
    public static final String MSG_KEY = "nested.try.depth";

    /** default allowed nesting depth */
    private static final int DEFAULT_MAX = 1;

    /** Creates new check instance with default allowed nesting depth. */
    public NestedTryDepthCheck() {
        super(DEFAULT_MAX);
    }

    @Override
    public int[] getDefaultTokens() {
        return new int[] {TokenTypes.LITERAL_TRY};
    }

    @Override
    public int[] getAcceptableTokens() {
        return new int[] {TokenTypes.LITERAL_TRY};
    }

    @Override
    public void visitToken(DetailAST ast) {
        if (ast.getType() == TokenTypes.LITERAL_TRY) {
            visitLiteralTry(ast);
        }
        else {
            throw new IllegalStateException(ast.toString());
        }
    }

    @Override
    public void leaveToken(DetailAST ast) {
        if (ast.getType() == TokenTypes.LITERAL_TRY) {
            leaveLiteralTry();
        }
        else {
            throw new IllegalStateException(ast.toString());
        }
    }

    /**
     * Increases current nesting depth.
     * @param literalTry node for try.
     */
    private void visitLiteralTry(DetailAST literalTry) {
        nestIn(literalTry, MSG_KEY);
    }

    /** Decreases current nesting depth */
    private void leaveLiteralTry() {
        nestOut();
    }
}
