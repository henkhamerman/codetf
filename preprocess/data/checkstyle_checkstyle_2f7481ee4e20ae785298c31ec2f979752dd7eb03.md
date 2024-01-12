Refactoring Types: ['Extract Method']
ools/checkstyle/api/JavadocTagInfo.java
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

package com.puppycrawl.tools.checkstyle.api;

import java.util.Map;

import com.google.common.collect.ImmutableMap;
import com.puppycrawl.tools.checkstyle.ScopeUtils;

/**
 * This enum defines the various Javadoc tags and there properties.
 *
 * <p>
 * This class was modeled after documentation located at
 * <a href="http://docs.oracle.com/javase/8/docs/technotes/tools/windows/javadoc.html">
 * javadoc</a>
 *
 * and
 *
 * <a href="http://www.oracle.com/technetwork/java/javase/documentation/index-137868.html">
 * how to write</a>.
 * </p>
 *
 * <p>
 * Some of this documentation was a little incomplete (ex: valid placement of
 * code, value, and literal tags).
 * </p>
 *
 * <p>
 * Whenever an inconsistency was found the author's judgment was used.
 * </p>
 *
 * <p>
 * For now, the number of required/optional tag arguments are not included
 * because some Javadoc tags have very complex rules for determining this
 * (ex: {@code {@value}} tag).
 * </p>
 *
 * <p>
 * Also, the {@link #isValidOn(DetailAST) isValidOn} method does not consider
 * classes defined in a local code block (method, init block, etc.).
 * </p>
 *
 * @author Travis Schneeberger
 */
public enum JavadocTagInfo {
    /**
     * {@code @author}.
     */
    AUTHOR("@author", "author", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF;
        }
    },

    /**
     * {@code {@code}}.
     */
    CODE("{@code}", "code", Type.INLINE) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code {@docRoot}}.
     */
    DOC_ROOT("{@docRoot}", "docRoot", Type.INLINE) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code @deprecated}.
     */
    DEPRECATED("@deprecated", "deprecated", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.ENUM_CONSTANT_DEF
                || type == TokenTypes.ANNOTATION_FIELD_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code @exception}.
     */
    EXCEPTION("@exception", "exception", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.METHOD_DEF || type == TokenTypes.CTOR_DEF;
        }
    },

    /**
     * {@code {@inheritDoc}}.
     */
    INHERIT_DOC("{@inheritDoc}", "inheritDoc", Type.INLINE) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();

            return type == TokenTypes.METHOD_DEF
                && !ast.branchContains(TokenTypes.LITERAL_STATIC)
                && ScopeUtils.getScopeFromMods(ast
                    .findFirstToken(TokenTypes.MODIFIERS)) != Scope.PRIVATE;
        }
    },

    /**
     * {@code {@link}}.
     */
    LINK("{@link}", "link", Type.INLINE) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code {@linkplain}}.
     */
    LINKPLAIN("{@linkplain}", "linkplain", Type.INLINE) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code {@literal}}.
     */
    LITERAL("{@literal}", "literal", Type.INLINE) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code @param}.
     */
    PARAM("@param", "param", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF;
        }
    },

    /**
     * {@code @return}.
     */
    RETURN("@return", "return", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            final DetailAST returnType = ast.findFirstToken(TokenTypes.TYPE);

            return type == TokenTypes.METHOD_DEF
                && returnType.getFirstChild().getType() != TokenTypes.LITERAL_VOID;

        }
    },

    /**
     * {@code @see}.
     */
    SEE("@see", "see", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code @serial}.
     */
    SERIAL("@serial", "serial", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();

            return type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code @serialData}.
     */
    SERIAL_DATA("@serialData", "serialData", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            final DetailAST methodNameAst = ast.findFirstToken(TokenTypes.IDENT);
            final String methodName = methodNameAst.getText();

            return type == TokenTypes.METHOD_DEF
                && ("writeObject".equals(methodName)
                    || "readObject".equals(methodName)
                    || "writeExternal".equals(methodName)
                    || "readExternal".equals(methodName)
                    || "writeReplace".equals(methodName)
                    || "readResolve".equals(methodName));
        }
    },

    /**
     * {@code @serialField}.
     */
    SERIAL_FIELD("@serialField", "serialField", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            final DetailAST varType = ast.findFirstToken(TokenTypes.TYPE);

            return type == TokenTypes.VARIABLE_DEF
                && varType.getFirstChild().getType() == TokenTypes.ARRAY_DECLARATOR
                && "ObjectStreafield".equals(varType.getFirstChild().getText());
        }
    },

    /**
     * {@code @since}.
     */
    SINCE("@since", "since", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code @throws}.
     */
    THROWS("@throws", "throws", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF;
        }
    },

    /**
     * {@code {@value}}.
     */
    VALUE("{@value}", "value", Type.INLINE) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF
                || type == TokenTypes.METHOD_DEF
                || type == TokenTypes.CTOR_DEF
                || type == TokenTypes.VARIABLE_DEF
                && !ScopeUtils.isLocalVariableDef(ast);
        }
    },

    /**
     * {@code @version}.
     */
    VERSION("@version", "version", Type.BLOCK) {
        /** {@inheritDoc} */
        @Override
        public boolean isValidOn(final DetailAST ast) {
            final int type = ast.getType();
            return type == TokenTypes.PACKAGE_DEF
                || type == TokenTypes.CLASS_DEF
                || type == TokenTypes.INTERFACE_DEF
                || type == TokenTypes.ENUM_DEF
                || type == TokenTypes.ANNOTATION_DEF;
        }
    };

    /** holds tag text to tag enum mappings **/
    private static final Map<String, JavadocTagInfo> TEXT_TO_TAG;
    /** holds tag name to tag enum mappings **/
    private static final Map<String, JavadocTagInfo> NAME_TO_TAG;

    static {
        final ImmutableMap.Builder<String, JavadocTagInfo> textToTagBuilder =
            new ImmutableMap.Builder<>();

        final ImmutableMap.Builder<String, JavadocTagInfo> nameToTagBuilder =
            new ImmutableMap.Builder<>();

        for (final JavadocTagInfo tag : JavadocTagInfo.values()) {
            textToTagBuilder.put(tag.getText(), tag);
            nameToTagBuilder.put(tag.getName(), tag);
        }

        TEXT_TO_TAG = textToTagBuilder.build();
        NAME_TO_TAG = nameToTagBuilder.build();
    }

    /** the tag text **/
    private final String text;
    /** the tag name **/
    private final String name;
    /** the tag type **/
    private final Type type;

    /**
     * Sets the various properties of a Javadoc tag.
     *
     * @param text the tag text
     * @param name the tag name
     * @param type the type of tag
     */
    private JavadocTagInfo(final String text, final String name,
        final Type type) {
        this.text = text;
        this.name = name;
        this.type = type;
    }

    /**
     * Checks if a particular Javadoc tag is valid within a Javadoc block of a
     * given AST.
     *
     * <p>
     * For example: Given a call to
     * <code>JavadocTag.RETURN{@link #isValidOn(DetailAST)}</code>.
     * </p>
     *
     * <p>
     * If passing in a DetailAST representing a non-void METHOD_DEF
     * <code> true </code> would be returned. If passing in a DetailAST
     * representing a CLASS_DEF <code> false </code> would be returned because
     * CLASS_DEF's cannot return a value.
     * </p>
     *
     * @param ast the AST representing a type that can be Javadoc'd
     * @return true if tag is valid.
     */
    public abstract boolean isValidOn(DetailAST ast);

    /**
     * Gets the tag text.
     * @return the tag text
     */
    public String getText() {
        return this.text;
    }

    /**
     * Gets the tag name.
     * @return the tag name
     */
    public String getName() {
        return this.name;
    }

    /**
     * Gets the Tag type defined by {@link JavadocTagInfo.Type Type}.
     * @return the Tag type
     */
    public Type getType() {
        return this.type;
    }

    /**
     * returns a JavadocTag from the tag text.
     * @param text String representing the tag text
     * @return Returns a JavadocTag type from a String representing the tag
     * @throws NullPointerException if the text is null
     * @throws IllegalArgumentException if the text is not a valid tag
     */
    public static JavadocTagInfo fromText(final String text) {
        if (text == null) {
            throw new IllegalArgumentException("the text is null");
        }

        final JavadocTagInfo tag = TEXT_TO_TAG.get(text);

        if (tag == null) {
            throw new IllegalArgumentException("the text [" + text
                + "] is not a valid Javadoc tag text");
        }

        return tag;
    }

    /**
     * returns a JavadocTag from the tag name.
     * @param name String name of the tag
     * @return Returns a JavadocTag type from a String representing the tag
     * @throws NullPointerException if the text is null
     * @throws IllegalArgumentException if the text is not a valid tag. The name
     *    can be checked using {@link JavadocTagInfo#isValidName(String)}
     */
    public static JavadocTagInfo fromName(final String name) {
        if (name == null) {
            throw new IllegalArgumentException("the name is null");
        }

        final JavadocTagInfo tag = NAME_TO_TAG.get(name);

        if (tag == null) {
            throw new IllegalArgumentException("the name [" + name
                + "] is not a valid Javadoc tag name");
        }

        return tag;
    }

    /**
     * Returns whether the provided name is for a valid tag.
     * @param name the tag name to check.
     * @return whether the provided name is for a valid tag.
     */
    public static boolean isValidName(final String name) {
        return NAME_TO_TAG.containsKey(name);
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public String toString() {
        return "text [" + this.text + "] name [" + this.name
            + "] type [" + this.type + "]";
    }

    /**
     * The Javadoc Type.
     *
     * For example a {@code @param} tag is a block tag while a
     * {@code {@link}} tag is a inline tag.
     *
     * @author Travis Schneeberger
     */
    public enum Type {
        /** block type. **/
        BLOCK,

        /** inline type. **/
        INLINE
    }
}


File: src/main/java/com/puppycrawl/tools/checkstyle/checks/LineSeparatorOption.java
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

package com.puppycrawl.tools.checkstyle.checks;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * Represents the options for line separator settings.
 *
 * @author lkuehne
 * @see NewlineAtEndOfFileCheck
 */
public enum LineSeparatorOption {
    /** Windows-style line separators. **/
    CRLF("\r\n"),

    /** Mac-style line separators. **/
    CR("\r"),

    /** Unix-style line separators. **/
    LF("\n"),

    /** Matches CR, LF and CRLF line separators. **/
    LF_CR_CRLF("##"), // only the length is used - the actual value is ignored

    /** System default line separators. **/
    SYSTEM(System.getProperty("line.separator"));

    /** the line separator representation */
    private final byte[] lineSeparator;

    /**
     * Creates a new <code>LineSeparatorOption</code> instance.
     * @param sep the line separator, e.g. "\r\n"
     */
    private LineSeparatorOption(String sep) {
        lineSeparator = sep.getBytes(StandardCharsets.US_ASCII);
    }

    /**
     * @param bytes a bytes array to check
     * @return if bytes is equal to the byte representation
     * of this line separator
     */
    public boolean matches(byte... bytes) {
        if (this == LF_CR_CRLF) {
            // this silently assumes CRLF and ANY have the same length
            // and LF and CR are of length 1
            return CRLF.matches(bytes)
                || LF.matches(Arrays.copyOfRange(bytes, 1, 2))
                || CR.matches(Arrays.copyOfRange(bytes, 1, 2));
        }
        else {
            return Arrays.equals(bytes, lineSeparator);
        }
    }

    /**
     * @return the length of the file separator in bytes,
     * e.g. 1 for CR, 2 for CRLF, ...
     */
    public int length() {
        return lineSeparator.length;
    }
}


File: src/main/java/com/puppycrawl/tools/checkstyle/checks/modifier/RedundantModifierCheck.java
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

package com.puppycrawl.tools.checkstyle.checks.modifier;

import java.util.ArrayList;
import java.util.List;

import com.puppycrawl.tools.checkstyle.api.Check;
import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

/**
 * Checks for redundant modifiers in interface and annotation definitions.
 * Also checks for redundant final modifiers on methods of final classes.
 *
 * @author lkuehne
 */
public class RedundantModifierCheck
    extends Check {

    /**
     * A key is pointing to the warning message text in "messages.properties"
     * file.
     */
    public static final String MSG_KEY = "redundantModifier";

    /**
     * An array of tokens for interface modifiers.
     */
    private static final int[] TOKENS_FOR_INTERFACE_MODIFIERS = new int[] {
        TokenTypes.LITERAL_STATIC,
        TokenTypes.ABSTRACT,
    };

    @Override
    public int[] getDefaultTokens() {
        return new int[] {
            TokenTypes.METHOD_DEF,
            TokenTypes.VARIABLE_DEF,
            TokenTypes.ANNOTATION_FIELD_DEF,
            TokenTypes.INTERFACE_DEF,
        };
    }

    @Override
    public int[] getRequiredTokens() {
        return new int[] {};
    }

    @Override
    public int[] getAcceptableTokens() {
        return new int[] {
            TokenTypes.METHOD_DEF,
            TokenTypes.VARIABLE_DEF,
            TokenTypes.ANNOTATION_FIELD_DEF,
            TokenTypes.INTERFACE_DEF,
        };
    }

    @Override
    public void visitToken(DetailAST ast) {
        if (TokenTypes.INTERFACE_DEF == ast.getType()) {
            final DetailAST modifiers =
                ast.findFirstToken(TokenTypes.MODIFIERS);

            for (final int tokenType : TOKENS_FOR_INTERFACE_MODIFIERS) {
                final DetailAST modifier =
                        modifiers.findFirstToken(tokenType);
                if (modifier != null) {
                    log(modifier.getLineNo(), modifier.getColumnNo(),
                            MSG_KEY, modifier.getText());
                }
            }
        }
        else if (isInterfaceOrAnnotationMember(ast)) {
            processInterfaceOrAnnotation(ast);
        }
        else if (ast.getType() == TokenTypes.METHOD_DEF) {
            processMethods(ast);
        }
    }

    /**
     * do validation of interface of annotation
     * @param ast token AST
     */
    private void processInterfaceOrAnnotation(DetailAST ast) {
        final DetailAST modifiers = ast.findFirstToken(TokenTypes.MODIFIERS);
        DetailAST modifier = modifiers.getFirstChild();
        while (modifier != null) {

            // javac does not allow final or static in interface methods
            // order annotation fields hence no need to check that this
            // is not a method or annotation field

            final int type = modifier.getType();
            if (type == TokenTypes.LITERAL_PUBLIC
                || type == TokenTypes.LITERAL_STATIC
                        && ast.getType() != TokenTypes.METHOD_DEF
                || type == TokenTypes.ABSTRACT
                || type == TokenTypes.FINAL) {
                log(modifier.getLineNo(), modifier.getColumnNo(),
                        MSG_KEY, modifier.getText());
                break;
            }

            modifier = modifier.getNextSibling();
        }
    }

    /**
     * process validation ofMethods
     * @param ast method AST
     */
    private void processMethods(DetailAST ast) {
        final DetailAST modifiers =
                        ast.findFirstToken(TokenTypes.MODIFIERS);
        // private method?
        boolean checkFinal =
            modifiers.branchContains(TokenTypes.LITERAL_PRIVATE);
        // declared in a final class?
        DetailAST parent = ast.getParent();
        while (parent != null) {
            if (parent.getType() == TokenTypes.CLASS_DEF) {
                final DetailAST classModifiers =
                    parent.findFirstToken(TokenTypes.MODIFIERS);
                checkFinal |=
                    classModifiers.branchContains(TokenTypes.FINAL);
                break;
            }
            parent = parent.getParent();
        }
        if (checkFinal && !isAnnotatedWithSafeVarargs(ast)) {
            DetailAST modifier = modifiers.getFirstChild();
            while (modifier != null) {
                final int type = modifier.getType();
                if (type == TokenTypes.FINAL) {
                    log(modifier.getLineNo(), modifier.getColumnNo(),
                            MSG_KEY, modifier.getText());
                    break;
                }
                modifier = modifier.getNextSibling();
            }
        }
    }

    /**
     * Checks if current AST node is member of Interface or Annotation, not of their subnodes.
     * @param ast AST node
     * @return true or false
     */
    private static boolean isInterfaceOrAnnotationMember(DetailAST ast) {
        final DetailAST parentTypeDef = ast.getParent().getParent();
        return parentTypeDef.getType() == TokenTypes.INTERFACE_DEF
               || parentTypeDef.getType() == TokenTypes.ANNOTATION_DEF;
    }

    /**
     * Checks if method definition is annotated with
     * <a href="https://docs.oracle.com/javase/8/docs/api/java/lang/SafeVarargs.html">
     * SafeVarargs</a> annotation
     * @param methodDef method definition node
     * @return true or false
     */
    private static boolean isAnnotatedWithSafeVarargs(DetailAST methodDef) {
        boolean result = false;
        final List<DetailAST> methodAnnotationsList = getMethodAnnotationsList(methodDef);
        for (DetailAST annotationNode : methodAnnotationsList) {
            if ("SafeVarargs".equals(annotationNode.getLastChild().getText())) {
                result = true;
                break;
            }
        }
        return result;
    }

    /**
     * Gets the list of annotations on method definition
     * @param methodDef method definition node
     * @return List of annotations
     */
    private static List<DetailAST> getMethodAnnotationsList(DetailAST methodDef) {
        final List<DetailAST> annotationsList = new ArrayList<>();
        final DetailAST modifiers = methodDef.findFirstToken(TokenTypes.MODIFIERS);
        DetailAST modifier = modifiers.getFirstChild();
        while (modifier != null) {
            if (modifier.getType() == TokenTypes.ANNOTATION) {
                annotationsList.add(modifier);
            }
            modifier = modifier.getNextSibling();
        }
        return annotationsList;
    }
}


File: src/test/java/com/puppycrawl/tools/checkstyle/checks/modifier/RedundantModifierTest.java
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

package com.puppycrawl.tools.checkstyle.checks.modifier;

import static com.puppycrawl.tools.checkstyle.checks.modifier.RedundantModifierCheck.MSG_KEY;

import java.io.File;

import org.junit.Assert;
import org.junit.Test;

import com.puppycrawl.tools.checkstyle.BaseCheckTestSupport;
import com.puppycrawl.tools.checkstyle.DefaultConfiguration;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

public class RedundantModifierTest
    extends BaseCheckTestSupport {
    @Test
    public void testIt() throws Exception {
        final DefaultConfiguration checkConfig =
            createCheckConfig(RedundantModifierCheck.class);
        final String[] expected = {
            "54:12: " + getCheckMessage(MSG_KEY, "static"),
            "57:9: " + getCheckMessage(MSG_KEY, "public"),
            "63:9: " + getCheckMessage(MSG_KEY, "abstract"),
            "66:9: " + getCheckMessage(MSG_KEY, "public"),
            //"69:9: Redundant 'abstract' modifier.",
            "72:9: " + getCheckMessage(MSG_KEY, "final"),
            "79:13: " + getCheckMessage(MSG_KEY, "final"),
            "88:12: " + getCheckMessage(MSG_KEY, "final"),
            "99:1: " + getCheckMessage(MSG_KEY, "abstract"),
            "116:5: " + getCheckMessage(MSG_KEY, "public"),
            "117:5: " + getCheckMessage(MSG_KEY, "final"),
            "118:5: " + getCheckMessage(MSG_KEY, "static"),
            "120:5: " + getCheckMessage(MSG_KEY, "public"),
            "121:5: " + getCheckMessage(MSG_KEY, "abstract"),
        };
        verify(checkConfig, getPath("InputModifier.java"), expected);
    }

    @Test
    public void testStaticMethodInInterface()
        throws Exception {
        final DefaultConfiguration checkConfig =
                createCheckConfig(RedundantModifierCheck.class);
        final String[] expected = {
        };
        verify(checkConfig,
                new File("src/test/resources-noncompilable/com/puppycrawl/tools/"
                        + "checkstyle/InputStaticModifierInInterface.java").getCanonicalPath(),
                expected);
    }

    @Test
    public void testFinalInInterface()
        throws Exception {
        final DefaultConfiguration checkConfig =
                createCheckConfig(RedundantModifierCheck.class);
        final String[] expected = {
            "3:9: " + getCheckMessage(MSG_KEY, "final"),
        };
        verify(checkConfig,
                new File("src/test/resources-noncompilable/com/puppycrawl/tools/"
                        + "checkstyle/InputFinalInDefaultMethods.java").getCanonicalPath(),
                expected);
    }

    @Test
    public void testGetAcceptableTokens() {
        RedundantModifierCheck redundantModifierCheckObj = new RedundantModifierCheck();
        int[] actual = redundantModifierCheckObj.getAcceptableTokens();
        int[] expected = new int[] {
            TokenTypes.METHOD_DEF,
            TokenTypes.VARIABLE_DEF,
            TokenTypes.ANNOTATION_FIELD_DEF,
            TokenTypes.INTERFACE_DEF,
        };
        Assert.assertNotNull(actual);
        Assert.assertArrayEquals(expected, actual);
    }

    @Test
    public void testGetRequiredTokens() {
        RedundantModifierCheck redundantModifierCheckObj = new RedundantModifierCheck();
        int[] actual = redundantModifierCheckObj.getRequiredTokens();
        int[] expected = new int[] {};
        Assert.assertNotNull(actual);
        Assert.assertArrayEquals(expected, actual);
    }
}
