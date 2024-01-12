Refactoring Types: ['Extract Method']
/groovy/grails/test/mixin/support/TestMixinRuntimeSupport.java
/*
 * Copyright 2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package grails.test.mixin.support;

import grails.test.mixin.TestRuntimeAwareMixin;
import grails.test.runtime.TestRuntime;
import grails.test.runtime.TestRuntimeFactory;
import groovy.lang.ExpandoMetaClass;
import groovy.lang.GroovyObjectSupport;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;

/**
 * Abstract base class for test mixin classes that use the new TestRuntime
 * 
 * @author Lari Hotari
 * @since 2.4.0
 *
 */
public abstract class TestMixinRuntimeSupport extends GroovyObjectSupport implements TestRuntimeAwareMixin {
    static {
        ExpandoMetaClass.enableGlobally();
    }

    private TestRuntime currentRuntime;
    private Set<String> features;
    private Class<?> testClass;

    public TestMixinRuntimeSupport(Set<String> features) {
        this.features = Collections.unmodifiableSet(new LinkedHashSet<String>(features));
    }
    
    @SkipMethod
    public Set<String> getFeatures() {
        return features;
    }

    public TestRuntime getRuntime() {
        if(currentRuntime == null && testClass != null) {
            TestRuntimeFactory.getRuntimeForTestClass(testClass);
        }
        if(currentRuntime == null) {
            throw new IllegalStateException("Current TestRuntime instance is null.");
        } else if (currentRuntime.isClosed()) {
            throw new IllegalStateException("Current TestRuntime instance is closed.");
        }
        return currentRuntime;
    }
    
    @SkipMethod
    public void setRuntime(TestRuntime runtime) {
        this.currentRuntime = runtime;
    }
    
    @SkipMethod
    @Override
    public void setTestClass(Class<?> testClass) {
        this.testClass = testClass;
    }
}

File: grails-plugin-testing/src/main/groovy/org/grails/compiler/injection/test/MockTransformation.java
/*
 * Copyright 2011 SpringSource
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.grails.compiler.injection.test;

import grails.test.mixin.Mock;

import grails.test.mixin.domain.DomainClassUnitTestMixin;
import org.codehaus.groovy.ast.ASTNode;
import org.codehaus.groovy.ast.AnnotatedNode;
import org.codehaus.groovy.ast.AnnotationNode;
import org.codehaus.groovy.ast.ClassNode;
import org.codehaus.groovy.ast.expr.ClassExpression;
import org.codehaus.groovy.ast.expr.Expression;
import org.codehaus.groovy.ast.expr.ListExpression;
import org.codehaus.groovy.control.CompilePhase;
import org.codehaus.groovy.control.SourceUnit;
import org.codehaus.groovy.transform.GroovyASTTransformation;

import java.util.ArrayList;
import java.util.List;

/**
 * Used by the {@link grails.test.mixin.Mock} local transformation to add
 * mocking capabilities for the given classes.
 *
 * @author Graeme Rocher
 * @since 2.0
 */
@GroovyASTTransformation(phase = CompilePhase.CANONICALIZATION)
public class MockTransformation extends TestForTransformation {

    private static final ClassNode MY_TYPE = new ClassNode(Mock.class);
    private static final String MY_TYPE_NAME = "@" + MY_TYPE.getNameWithoutPackage();

    @Override
    public void visit(ASTNode[] astNodes, SourceUnit source) {
        if (!(astNodes[0] instanceof AnnotationNode) || !(astNodes[1] instanceof AnnotatedNode)) {
            throw new RuntimeException("Internal error: wrong types: " + astNodes[0].getClass() +
                  " / " + astNodes[1].getClass());
        }

        AnnotatedNode parent = (AnnotatedNode) astNodes[1];
        AnnotationNode node = (AnnotationNode) astNodes[0];
        if (!MY_TYPE.equals(node.getClassNode()) || !(parent instanceof ClassNode)) {
            return;
        }

        ClassNode classNode = (ClassNode) parent;
        String cName = classNode.getName();
        if (classNode.isInterface()) {
            error(source, "Error processing interface '" + cName + "'. " + MY_TYPE_NAME +
                    " not allowed for interfaces.");
        }

        ListExpression values = getListOfClasses(node);
        if (values == null) {
            error(source, "Error processing class '" + cName + "'. " + MY_TYPE_NAME +
                    " annotation expects a class or a list of classes to mock");
            return;
        }

        List<ClassExpression> domainClassNodes = new ArrayList<ClassExpression>();
        for (Expression expression : values.getExpressions()) {
            if (expression instanceof ClassExpression) {
                ClassExpression classEx = (ClassExpression) expression;
                ClassNode cn = classEx.getType();
                Class<?> mixinClassForArtefactType = getMixinClassForArtefactType(cn);
                if (mixinClassForArtefactType != null) {
                    weaveMock(classNode, classEx, false);
                }
                else {
                    domainClassNodes.add(classEx);
                }
            }
        }
        if (!domainClassNodes.isEmpty()) {
            weaveMixinClass(classNode, DomainClassUnitTestMixin.class);
            addMockCollaborators(classNode, "Domain", domainClassNodes);
            addEnableEMCStatement(classNode);
        }
    }
}


File: grails-plugin-testing/src/main/groovy/org/grails/compiler/injection/test/TestForTransformation.java
/*
 * Copyright 2011 SpringSource
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.grails.compiler.injection.test;

import grails.compiler.ast.GrailsArtefactClassInjector;
import grails.test.mixin.TestFor;
import grails.test.mixin.domain.DomainClassUnitTestMixin;
import grails.test.mixin.support.MixinMethod;
import grails.test.mixin.support.TestMixinRegistrar;
import grails.test.mixin.support.TestMixinRegistry;
import grails.util.BuildSettings;
import grails.util.GrailsNameUtils;
import org.codehaus.groovy.ast.*;
import org.codehaus.groovy.ast.expr.*;
import org.codehaus.groovy.ast.stmt.*;
import org.codehaus.groovy.control.CompilePhase;
import org.codehaus.groovy.control.SourceUnit;
import org.codehaus.groovy.syntax.Token;
import org.codehaus.groovy.transform.GroovyASTTransformation;
import org.grails.compiler.injection.GrailsASTUtils;
import org.grails.compiler.logging.LoggingTransformer;
import org.grails.core.io.DefaultResourceLocator;
import org.grails.core.io.ResourceLocator;
import org.grails.core.io.support.GrailsFactoriesLoader;
import org.grails.io.support.FileSystemResource;
import org.grails.io.support.GrailsResourceUtils;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.context.ApplicationContext;
import org.springframework.core.io.Resource;

import java.io.IOException;
import java.lang.reflect.Modifier;
import java.util.*;

/**
 * Transformation used by the {@link grails.test.mixin.TestFor} annotation to signify the
 * class under test.
 *
 * @author Graeme Rocher
 * @since 2.0
 */
@GroovyASTTransformation(phase = CompilePhase.CANONICALIZATION)
@SuppressWarnings("rawtypes")
public class TestForTransformation extends TestMixinTransformation implements TestMixinRegistry {

    private static final ClassNode MY_TYPE = new ClassNode(TestFor.class);
    private static final Token ASSIGN = Token.newSymbol("=", -1, -1);

    protected static final Map<String, Class> artefactTypeToTestMap = new HashMap<String, Class>();
    static {
        List<TestMixinRegistrar> registrars = GrailsFactoriesLoader.loadFactories(TestMixinRegistrar.class);
        TestMixinRegistry thisRegistry = new TestMixinRegistry() {
            @Override
            public void registerMixin(String artefactType, Class mixin) {
                artefactTypeToTestMap.put(artefactType, mixin);
            }
        };
        for(TestMixinRegistrar registrar : registrars) {
            registrar.registerTestMixins(thisRegistry);
        }
    }

    public static final String DOMAIN_TYPE = "Domain";
    public static final ClassNode BEFORE_CLASS_NODE = new ClassNode(Before.class);
    public static final AnnotationNode BEFORE_ANNOTATION = new AnnotationNode(BEFORE_CLASS_NODE);

    public static final ClassNode AFTER_CLASS_NODE = new ClassNode(After.class);
    public static final AnnotationNode AFTER_ANNOTATION = new AnnotationNode(AFTER_CLASS_NODE);

    public static final AnnotationNode TEST_ANNOTATION = new AnnotationNode(new ClassNode(Test.class));
    private static final String GROOVY_TEST_CASE_CLASS_NAME = "groovy.util.GroovyTestCase";
    public static final String VOID_TYPE = "void";

    private ResourceLocator resourceLocator;

    public ResourceLocator getResourceLocator() {
        if (resourceLocator == null) {
            resourceLocator = new DefaultResourceLocator();
            String basedir = BuildSettings.BASE_DIR.getAbsolutePath();
            resourceLocator.setSearchLocation(basedir);
        }
        return resourceLocator;
    }

    @Override
    public void visit(ASTNode[] astNodes, SourceUnit source) {
        if (!(astNodes[0] instanceof AnnotationNode) || !(astNodes[1] instanceof AnnotatedNode)) {
            throw new RuntimeException("Internal error: wrong types: $node.class / $parent.class");
        }

        AnnotatedNode parent = (AnnotatedNode) astNodes[1];
        AnnotationNode node = (AnnotationNode) astNodes[0];
        if (!MY_TYPE.equals(node.getClassNode()) || !(parent instanceof ClassNode)) {
            return;
        }

        ClassNode classNode = (ClassNode) parent;
        if (classNode.isInterface() || Modifier.isAbstract(classNode.getModifiers())) {
            return;
        }

        boolean junit3Test = isJunit3Test(classNode);
        boolean spockTest = isSpockTest(classNode);
        boolean isJunit = !junit3Test && !spockTest;

        if (!junit3Test && !spockTest && !isJunit) return;

        handleTestForAnnotation(classNode, source, node, junit3Test);
        addEnableEMCStatement(classNode);
    }

    protected void handleTestForAnnotation(ClassNode classNode, SourceUnit source, AnnotationNode testForAnnotationNode, boolean junit3Test) {
        Expression value = testForAnnotationNode.getMember("value");
        ClassExpression ce;
        if (value instanceof ClassExpression) {
            ce = (ClassExpression) value;
            testFor(classNode, ce);
            return;
        }

        if (junit3Test) {
            return;
        }

        List<AnnotationNode> annotations = classNode.getAnnotations(MY_TYPE);
        if (annotations.size()>0) return; // bail out, in this case it was already applied as a local transform

        annotations = classNode.getAnnotations(TestMixinTransformation.MY_TYPE);
        if (annotations.size()>0) return; // bail out, another TestMixin transform already defines behavior

        // no explicit class specified try by convention
        String fileName = source.getName();
        String className = GrailsResourceUtils.getClassName(new FileSystemResource(fileName));
        if (className == null) {
            return;
        }

        String targetClassName = null;

        if (className.endsWith("Tests")) {
            targetClassName = className.substring(0, className.indexOf("Tests"));
        }
        else if (className.endsWith("Test")) {
            targetClassName = className.substring(0, className.indexOf("Test"));
        }
        else if (className.endsWith("Spec")) {
            targetClassName = className.substring(0, className.indexOf("Spec"));
        }

        if (targetClassName == null) {
            return;
        }

        Resource targetResource = getResourceLocator().findResourceForClassName(targetClassName);
        if (targetResource == null) {
            return;
        }

        try {
            if (GrailsResourceUtils.isDomainClass(targetResource.getURL())) {
                testFor(classNode, new ClassExpression(new ClassNode(targetClassName, 0, ClassHelper.OBJECT_TYPE)));
            }
            else {
                for (String artefactType : artefactTypeToTestMap.keySet()) {
                    if (targetClassName.endsWith(artefactType)) {
                        testFor(classNode, new ClassExpression(new ClassNode(targetClassName, 0, ClassHelper.OBJECT_TYPE)));
                        break;
                    }
                }
            }
        } catch (IOException e) {
            // ignore
        }
    }

    /**
     * Main entry point for the calling the TestForTransformation programmatically.
     *
     * @param classNode The class node that represents th test
     * @param ce The class expression that represents the class to test
     */
    public void testFor(ClassNode classNode, ClassExpression ce) {

        autoAnnotateSetupTeardown(classNode);
        boolean isJunit3Test = isJunit3Test(classNode);

        // make sure the 'log' property is not the one from GroovyTestCase
        FieldNode log = classNode.getField("log");
        if (log == null || log.getDeclaringClass().getName().equals(GROOVY_TEST_CASE_CLASS_NAME)) {
            LoggingTransformer.addLogField(classNode, classNode.getName());
        }
        boolean isSpockTest = isSpockTest(classNode);

        boolean isJunit4 = !isSpockTest && !isJunit3Test;
        if (isJunit4) {
            // assume JUnit 4
            Map<String, MethodNode> declaredMethodsMap = classNode.getDeclaredMethodsMap();
            boolean hasTestMethods = false;
            for (String methodName : declaredMethodsMap.keySet()) {
                MethodNode methodNode = declaredMethodsMap.get(methodName);
                ClassNode testAnnotationClassNode = TEST_ANNOTATION.getClassNode();
                List<AnnotationNode> existingTestAnnotations = methodNode.getAnnotations(testAnnotationClassNode);
                if (isCandidateMethod(methodNode) && (methodNode.getName().startsWith("test") || existingTestAnnotations.size()>0)) {
                    if (existingTestAnnotations.size()==0) {
                        ClassNode returnType = methodNode.getReturnType();
                        if (returnType.getName().equals(VOID_TYPE)) {
                            methodNode.addAnnotation(TEST_ANNOTATION);
                        }
                    }
                    hasTestMethods = true;
                }
            }
            if (!hasTestMethods) {
                isJunit4 = false;
            }
        }

        if (isJunit4 || isJunit3Test || isSpockTest) {
            final MethodNode methodToAdd = weaveMock(classNode, ce, true);
            if (methodToAdd != null && isJunit3Test) {
                addMethodCallsToMethod(classNode,SET_UP_METHOD, Arrays.asList(methodToAdd));
            }
        }
    }

    private Map<ClassNode, List<Class>> wovenMixins = new HashMap<ClassNode, List<Class>>();
    protected MethodNode weaveMock(ClassNode classNode, ClassExpression value, boolean isClassUnderTest) {

        ClassNode testTarget = value.getType();
        String className = testTarget.getName();
        MethodNode testForMethod = null;
        for (String artefactType : artefactTypeToTestMap.keySet()) {
            if (className.endsWith(artefactType)) {
                Class mixinClass = artefactTypeToTestMap.get(artefactType);
                if (!isAlreadyWoven(classNode, mixinClass)) {
                    weaveMixinClass(classNode, mixinClass);
                    if (isClassUnderTest) {
                        testForMethod = addClassUnderTestMethod(classNode, value, artefactType);
                    }
                    else {
                        addMockCollaboratorToSetup(classNode, value, artefactType);
                    }
                    return testForMethod;
                }

                addMockCollaboratorToSetup(classNode, value, artefactType);
                return null;
            }
        }

        // must be a domain class
        weaveMixinClass(classNode, DomainClassUnitTestMixin.class);
        if (isClassUnderTest) {
            testForMethod = addClassUnderTestMethod(classNode, value, DOMAIN_TYPE);
        }
        else {
            addMockCollaboratorToSetup(classNode, value, DOMAIN_TYPE);
        }

        return testForMethod;
    }

    protected Class getMixinClassForArtefactType(ClassNode classNode) {
        String className = classNode.getName();
        for (String artefactType : artefactTypeToTestMap.keySet()) {
            if (className.endsWith(artefactType)) {
                Class mixinClass = artefactTypeToTestMap.get(artefactType);
                if (mixinClass != null) {
                    return mixinClass;
                }
            }
        }
        return null;
    }


    private void addMockCollaboratorToSetup(ClassNode classNode, ClassExpression targetClassExpression, String artefactType) {
        BlockStatement methodBody = getOrCreateTestSetupMethod(classNode);
        addMockCollaborator(artefactType, targetClassExpression,methodBody);
    }

    protected BlockStatement getOrCreateTestSetupMethod(ClassNode classNode) {
        BlockStatement methodBody;
        if (isJunit3Test(classNode)) {
            methodBody = getJunit3Setup(classNode);
        }
        else {
            methodBody = getExistingOrCreateJUnit4Setup(classNode);
        }
        return methodBody;
    }

    protected BlockStatement getExistingOrCreateJUnit4Setup(ClassNode classNode) {
        Statement code = getExistingJUnit4BeforeMethod(classNode);
        if (code instanceof BlockStatement) {
            return (BlockStatement) code;
        }
        return getJunit4Setup(classNode);
    }

    protected Statement getExistingJUnit4BeforeMethod(ClassNode classNode) {
        Statement code = null;
        Map<String, MethodNode> declaredMethodsMap = classNode.getDeclaredMethodsMap();
        for (MethodNode methodNode : declaredMethodsMap.values()) {
            if (isDeclaredBeforeMethod(methodNode)) {
                code = getMethodBody(methodNode);
            }
        }
        return code;
    }

    private Statement getMethodBody(MethodNode methodNode) {
        Statement code = methodNode.getCode();
        if (!(code instanceof BlockStatement)) {
            BlockStatement body = new BlockStatement();
            body.addStatement(code);
            code = body;
        }
        return code;
    }

    private boolean isDeclaredBeforeMethod(MethodNode methodNode) {
        return isPublicInstanceMethod(methodNode) && hasAnnotation(methodNode, Before.class) && !hasAnnotation(methodNode, MixinMethod.class);
    }

    private boolean isPublicInstanceMethod(MethodNode methodNode) {
        return !methodNode.isSynthetic() && !methodNode.isStatic() && methodNode.isPublic();
    }

    private BlockStatement getJunit4Setup(ClassNode classNode) {
        MethodNode setupMethod = classNode.getDeclaredMethod(SET_UP_METHOD, GrailsArtefactClassInjector.ZERO_PARAMETERS);
        if (setupMethod == null) {
            setupMethod = new MethodNode(SET_UP_METHOD,Modifier.PUBLIC,ClassHelper.VOID_TYPE,GrailsArtefactClassInjector.ZERO_PARAMETERS,null,new BlockStatement());
            setupMethod.addAnnotation(MIXIN_METHOD_ANNOTATION);
            classNode.addMethod(setupMethod);
        }
        if (setupMethod.getAnnotations(BEFORE_CLASS_NODE).size() == 0) {
            setupMethod.addAnnotation(BEFORE_ANNOTATION);
        }
        return getOrCreateMethodBody(classNode, setupMethod, SET_UP_METHOD);

    }

    private BlockStatement getJunit3Setup(ClassNode classNode) {
        boolean hasExistingSetupMethod = classNode.hasDeclaredMethod(SET_UP_METHOD, Parameter.EMPTY_ARRAY);
        BlockStatement setUpMethodBody = getOrCreateNoArgsMethodBody(classNode, SET_UP_METHOD);
        if(!hasExistingSetupMethod) {
            setUpMethodBody.getStatements().add(new ExpressionStatement(new MethodCallExpression(new VariableExpression("super"), SET_UP_METHOD, GrailsArtefactClassInjector.ZERO_ARGS)));
        }
        return setUpMethodBody;
    }

    private boolean isAlreadyWoven(ClassNode classNode, Class mixinClass) {
        List<Class> mixinClasses = wovenMixins.get(classNode);
        if (mixinClasses == null) {
            mixinClasses = new ArrayList<Class>();
            mixinClasses.add(mixinClass);
            wovenMixins.put(classNode, mixinClasses);
        }
        else {
            if (mixinClasses.contains(mixinClass)) {
                return true;
            }

            mixinClasses.add(mixinClass);
        }
        return false;
    }

    protected void weaveMixinClass(ClassNode classNode, Class mixinClass) {
        ListExpression listExpression = new ListExpression();
        listExpression.addExpression(new ClassExpression(new ClassNode(mixinClass)));
        weaveMixinsIntoClass(classNode,listExpression);
    }

    protected MethodNode addClassUnderTestMethod(ClassNode classNode, ClassExpression targetClass, String type) {

        String methodName = "setup" + type + "UnderTest";
        String fieldName = GrailsNameUtils.getPropertyName(type);
        String getterName = GrailsNameUtils.getGetterName(fieldName);
        fieldName = '$' +fieldName;

        if (classNode.getField(fieldName) == null) {
            classNode.addField(fieldName, Modifier.PRIVATE, targetClass.getType(),null);
        }

        MethodNode methodNode = classNode.getDeclaredMethod(methodName,GrailsArtefactClassInjector.ZERO_PARAMETERS);

        VariableExpression fieldExpression = new VariableExpression(fieldName, targetClass.getType());
        if (methodNode == null) {
            BlockStatement setupMethodBody = new BlockStatement();
            addMockCollaborator(type, targetClass, setupMethodBody);

            methodNode = new MethodNode(methodName, Modifier.PUBLIC, ClassHelper.VOID_TYPE, GrailsArtefactClassInjector.ZERO_PARAMETERS,null, setupMethodBody);
            methodNode.addAnnotation(BEFORE_ANNOTATION);
            methodNode.addAnnotation(MIXIN_METHOD_ANNOTATION);
            
            classNode.addMethod(methodNode);
            GrailsASTUtils.addCompileStaticAnnotation(methodNode);
        }

        MethodNode getter = classNode.getDeclaredMethod(getterName, GrailsArtefactClassInjector.ZERO_PARAMETERS);
        if (getter == null) {
            BlockStatement getterBody = new BlockStatement();
            getter = new MethodNode(getterName, Modifier.PUBLIC, targetClass.getType().getPlainNodeReference(),GrailsArtefactClassInjector.ZERO_PARAMETERS,null, getterBody);

            BinaryExpression testTargetAssignment = new BinaryExpression(fieldExpression, ASSIGN, new ConstructorCallExpression(targetClass.getType(), GrailsArtefactClassInjector.ZERO_ARGS));

            IfStatement autowiringIfStatement = getAutowiringIfStatement(targetClass,fieldExpression, testTargetAssignment);
            getterBody.addStatement(autowiringIfStatement);

            getterBody.addStatement(new ReturnStatement(fieldExpression));
            classNode.addMethod(getter);
            GrailsASTUtils.addCompileStaticAnnotation(getter);
        }

        return methodNode;
    }

    private IfStatement getAutowiringIfStatement(ClassExpression targetClass, VariableExpression fieldExpression, BinaryExpression testTargetAssignment) {
        VariableExpression appCtxVar = new VariableExpression("applicationContext", ClassHelper.make(ApplicationContext.class));

        BooleanExpression applicationContextCheck = new BooleanExpression(
                new BinaryExpression(
                new BinaryExpression(fieldExpression, GrailsASTUtils.EQUALS_OPERATOR, GrailsASTUtils.NULL_EXPRESSION),
                        Token.newSymbol("&&",0,0),
                new BinaryExpression(appCtxVar, GrailsASTUtils.NOT_EQUALS_OPERATOR, GrailsASTUtils.NULL_EXPRESSION)));
        BlockStatement performAutowireBlock = new BlockStatement();
        ArgumentListExpression arguments = new ArgumentListExpression();
        arguments.addExpression(fieldExpression);
        arguments.addExpression(new ConstantExpression(1));
        arguments.addExpression(new ConstantExpression(false));
        BlockStatement assignFromApplicationContext = new BlockStatement();
        ArgumentListExpression argWithClassName = new ArgumentListExpression();
        MethodCallExpression getClassNameMethodCall = new MethodCallExpression(targetClass, "getName", new ArgumentListExpression());
        argWithClassName.addExpression(getClassNameMethodCall);

        assignFromApplicationContext.addStatement(new ExpressionStatement(new BinaryExpression(fieldExpression, ASSIGN, new MethodCallExpression(appCtxVar, "getBean", argWithClassName))));
        BlockStatement elseBlock = new BlockStatement();
        elseBlock.addStatement(new ExpressionStatement(testTargetAssignment));
        performAutowireBlock.addStatement(new IfStatement(new BooleanExpression(new MethodCallExpression(appCtxVar, "containsBean", argWithClassName)), assignFromApplicationContext, elseBlock));
        performAutowireBlock.addStatement(new ExpressionStatement(new MethodCallExpression(new PropertyExpression(appCtxVar,"autowireCapableBeanFactory"), "autowireBeanProperties", arguments)));
        return new IfStatement(applicationContextCheck, performAutowireBlock, new BlockStatement());
    }

    protected void addMockCollaborator(String mockType, ClassExpression targetClass, BlockStatement methodBody) {
        ArgumentListExpression args = new ArgumentListExpression();
        args.addExpression(targetClass);
        methodBody.getStatements().add(0, new ExpressionStatement(new MethodCallExpression(new VariableExpression("this"), "mock" + mockType, args)));
    }

    protected void addMockCollaborators(ClassNode classNode, String mockType, List<ClassExpression> targetClasses) {
         addMockCollaborators(mockType, targetClasses, getOrCreateTestSetupMethod(classNode));
    }


    protected void addMockCollaborators(String mockType, List<ClassExpression> targetClasses, BlockStatement methodBody) {
        ArgumentListExpression args = new ArgumentListExpression();
        for(ClassExpression ce : targetClasses) {
            args.addExpression(ce);
        }
        methodBody.getStatements().add(0, new ExpressionStatement(new MethodCallExpression(new VariableExpression("this"), "mock" + mockType + 's', args)));
    }

    @Override
    public void registerMixin(String artefactType, Class mixin) {
        artefactTypeToTestMap.put(artefactType, mixin);
    }
}


File: grails-plugin-testing/src/main/groovy/org/grails/compiler/injection/test/TestMixinTransformation.java
/*
 * Copyright 2011 SpringSource
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.grails.compiler.injection.test;

import grails.test.mixin.TestMixin;
import grails.test.mixin.TestMixinTargetAware;
import grails.test.mixin.TestRuntimeAwareMixin;
import grails.test.mixin.support.MixinInstance;
import grails.test.mixin.support.MixinMethod;
import grails.test.mixin.support.SkipMethod;
import grails.test.runtime.TestRuntimeJunitAdapter;
import grails.util.GrailsNameUtils;
import groovy.lang.ExpandoMetaClass;
import groovy.lang.GroovyObjectSupport;

import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.codehaus.groovy.ast.ASTNode;
import org.codehaus.groovy.ast.AnnotatedNode;
import org.codehaus.groovy.ast.AnnotationNode;
import org.codehaus.groovy.ast.ClassHelper;
import org.codehaus.groovy.ast.ClassNode;
import org.codehaus.groovy.ast.FieldNode;
import org.codehaus.groovy.ast.MethodNode;
import org.codehaus.groovy.ast.Parameter;
import org.codehaus.groovy.ast.expr.ArgumentListExpression;
import org.codehaus.groovy.ast.expr.ClassExpression;
import org.codehaus.groovy.ast.expr.ConstantExpression;
import org.codehaus.groovy.ast.expr.ConstructorCallExpression;
import org.codehaus.groovy.ast.expr.Expression;
import org.codehaus.groovy.ast.expr.FieldExpression;
import org.codehaus.groovy.ast.expr.ListExpression;
import org.codehaus.groovy.ast.expr.MapEntryExpression;
import org.codehaus.groovy.ast.expr.MapExpression;
import org.codehaus.groovy.ast.expr.MethodCallExpression;
import org.codehaus.groovy.ast.expr.VariableExpression;
import org.codehaus.groovy.ast.stmt.BlockStatement;
import org.codehaus.groovy.ast.stmt.ExpressionStatement;
import org.codehaus.groovy.ast.stmt.ReturnStatement;
import org.codehaus.groovy.ast.stmt.Statement;
import org.codehaus.groovy.control.CompilePhase;
import org.codehaus.groovy.control.SourceUnit;
import org.codehaus.groovy.control.messages.SimpleMessage;
import org.grails.compiler.injection.GrailsASTUtils;
import grails.compiler.ast.GrailsArtefactClassInjector;
import org.codehaus.groovy.transform.ASTTransformation;
import org.codehaus.groovy.transform.GroovyASTTransformation;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TestRule;
import org.spockframework.runtime.model.FieldMetadata;

import spock.lang.Shared;

/**
 * An AST transformation to be applied to tests for adding behavior to a target test class.
 *
 * @author Graeme Rocher
 * @since 2.0
 */
@GroovyASTTransformation(phase = CompilePhase.CANONICALIZATION)
public class TestMixinTransformation implements ASTTransformation{
    private static final String RULE_FIELD_NAME_BASE = "$testRuntime";
    private static final String JUNIT_ADAPTER_FIELD_NAME = RULE_FIELD_NAME_BASE + "JunitAdapter";
    private static final String JUNIT3_RULE_SETUP_TEARDOWN_APPLIED_KEY = "JUNIT3_RULE_SETUP_TEARDOWN_APPLIED_KEY";
    public static final AnnotationNode MIXIN_METHOD_ANNOTATION = new AnnotationNode(new ClassNode(MixinMethod.class));
    static final ClassNode MY_TYPE = new ClassNode(TestMixin.class);
    private static final String MY_TYPE_NAME = "@" + MY_TYPE.getNameWithoutPackage();
    public static final String SPEC_CLASS = "spock.lang.Specification";
    private static final String JUNIT3_CLASS = "junit.framework.TestCase";
    public static final String SET_UP_METHOD = "setUp";
    public static final String TEAR_DOWN_METHOD = "tearDown";
    public static final ClassNode GROOVY_OBJECT_CLASS_NODE = new ClassNode(GroovyObjectSupport.class);
    public static final AnnotationNode TEST_ANNOTATION = new AnnotationNode(new ClassNode(Test.class));
    public static final String VOID_TYPE = "void";
    private static final String EMC_STATEMENT_ADDED_KEY = "EMC_STATEMENT_ADDED_KEY";
    private static final ClassNode SKIP_METHOD_CLASS_NODE = ClassHelper.make(SkipMethod.class);

    public void visit(ASTNode[] astNodes, SourceUnit source) {
        if (!(astNodes[0] instanceof AnnotationNode) || !(astNodes[1] instanceof AnnotatedNode)) {
            throw new RuntimeException("Internal error: wrong types: " + astNodes[0].getClass() + " / " + astNodes[1].getClass());
        }

        AnnotatedNode parent = (AnnotatedNode) astNodes[1];
        AnnotationNode annotationNode = (AnnotationNode) astNodes[0];
        if (!MY_TYPE.equals(annotationNode.getClassNode()) || !(parent instanceof ClassNode)) {
            return;
        }

        ClassNode classNode = (ClassNode) parent;
        ListExpression values = getListOfClasses(annotationNode);
        weaveTestMixins(classNode, values);
        addEnableEMCStatement(classNode);
    }

    protected void addEnableEMCStatement(ClassNode classNode) {
        if (classNode.redirect().getNodeMetaData(EMC_STATEMENT_ADDED_KEY) != Boolean.TRUE) {
            List<Statement> statements = new ArrayList<Statement>();
            ClassNode emcClassNode = ClassHelper.make(ExpandoMetaClass.class);
            // make direct static call to ExpandoMetaClass.enableGlobally() is static initializer block
            statements.add(new ExpressionStatement(GrailsASTUtils.applyDefaultMethodTarget(new MethodCallExpression(
                    new ClassExpression(emcClassNode), "enableGlobally", MethodCallExpression.NO_ARGUMENTS),
                    emcClassNode)));
            classNode.addStaticInitializerStatements(statements, true);
            classNode.redirect().setNodeMetaData(EMC_STATEMENT_ADDED_KEY, Boolean.TRUE);
        }
    }

    /**
     * @param classNode The class node to weave into
     * @param values A list of ClassExpression instances
     */
    public void weaveTestMixins(ClassNode classNode, ListExpression values) {
        String cName = classNode.getName();
        if (classNode.isInterface()) {
            throw new RuntimeException("Error processing interface '" + cName + "'. " +
                    MY_TYPE_NAME + " not allowed for interfaces.");
        }

        autoAnnotateSetupTeardown(classNode);
        autoAddTestAnnotation(classNode);

        weaveMixinsIntoClass(classNode, values);
    }

    private void autoAddTestAnnotation(ClassNode classNode) {
        if(isSpockTest(classNode)) return;
        Map<String, MethodNode> declaredMethodsMap = classNode.getDeclaredMethodsMap();
        for (String methodName : declaredMethodsMap.keySet()) {
            MethodNode methodNode = declaredMethodsMap.get(methodName);
            ClassNode testAnnotationClassNode = TEST_ANNOTATION.getClassNode();
            List<AnnotationNode> existingTestAnnotations = methodNode.getAnnotations(testAnnotationClassNode);
            if (isCandidateMethod(methodNode) && (methodNode.getName().startsWith("test") || existingTestAnnotations.size()>0)) {
                if (existingTestAnnotations.size()==0) {
                    ClassNode returnType = methodNode.getReturnType();
                    if (returnType.getName().equals(VOID_TYPE)) {
                        methodNode.addAnnotation(TEST_ANNOTATION);
                    }
                }
            }
        }

    }

    protected ListExpression getListOfClasses(AnnotationNode node) {
        Expression value = node.getMember("value");
        ListExpression values = null;
        if (value instanceof ListExpression) {
            values = (ListExpression) value;
        }
        else if (value instanceof ClassExpression) {
            values = new ListExpression();
            values.addExpression(value);
        }

        return values;
    }

    public void weaveMixinsIntoClass(ClassNode classNode, ListExpression values) {
        if (values == null) {
            return;
        }

        Junit3TestFixtureMethodHandler junit3MethodHandler = isJunit3Test(classNode) ? new Junit3TestFixtureMethodHandler(classNode) : null; 

        for (Expression current : values.getExpressions()) {
            if (current instanceof ClassExpression) {
                ClassExpression ce = (ClassExpression) current;
                ClassNode mixinClassNode = ce.getType();
                weaveMixinIntoClass(classNode, mixinClassNode, junit3MethodHandler);
            }
        }

        if (junit3MethodHandler != null) {
            junit3MethodHandler.postProcessClassNode();
        }
    }

    protected void weaveMixinIntoClass(final ClassNode classNode, final ClassNode mixinClassNode,
            final Junit3TestFixtureMethodHandler junit3MethodHandler) {
        final String fieldName = '$' + GrailsNameUtils.getPropertyName(mixinClassNode.getName());
        
        boolean implementsTestRuntimeAwareMixin = GrailsASTUtils.findInterface(mixinClassNode, ClassHelper.make(TestRuntimeAwareMixin.class)) != null;
        
        FieldNode mixinFieldNode = null;
        if(!implementsTestRuntimeAwareMixin) { 
            mixinFieldNode = addLegacyMixinFieldIfNonExistent(classNode, mixinClassNode, fieldName);
        } else {
            mixinFieldNode = addTestRuntimeAwareMixinFieldIfNonExistent(classNode, mixinClassNode, fieldName);
        }

        if (mixinFieldNode == null) return; // already woven
        
        FieldExpression fieldReference = new FieldExpression(mixinFieldNode);

        ClassNode currentMixinClassNode = mixinClassNode; 
        while (!currentMixinClassNode.getName().equals(GrailsASTUtils.OBJECT_CLASS)) {
            final List<MethodNode> mixinMethods = currentMixinClassNode.getMethods();

            for (MethodNode mixinMethod : mixinMethods) {
                if (!isCandidateMethod(mixinMethod) || hasDeclaredMethod(classNode, mixinMethod)) {
                    continue;
                }

                MethodNode methodNode;
                if (mixinMethod.isStatic()) {
                    methodNode = GrailsASTUtils.addDelegateStaticMethod(classNode, mixinMethod);
                }
                else {
                    methodNode = GrailsASTUtils.addDelegateInstanceMethod(classNode, fieldReference, mixinMethod, false);
                }
                if (methodNode != null) {
                    methodNode.addAnnotation(MIXIN_METHOD_ANNOTATION);
                    GrailsASTUtils.addCompileStaticAnnotation(methodNode);
                }

                if (junit3MethodHandler != null) {
                    junit3MethodHandler.handle(mixinMethod, methodNode);
                }
            }

            currentMixinClassNode = currentMixinClassNode.getSuperClass();
            if (junit3MethodHandler != null) {
                junit3MethodHandler.mixinSuperClassChanged();
            }
        }
    }
    
    protected FieldNode addTestRuntimeAwareMixinFieldIfNonExistent(ClassNode classNode, ClassNode fieldType,
            String fieldName) {
        if (classNode == null || classNode.getField(fieldName) != null) {
            return null;
        }
        
        MapExpression constructorArguments = new MapExpression();
        constructorArguments.addMapEntryExpression(new MapEntryExpression(new ConstantExpression("testClass"), new ClassExpression(classNode)));
        FieldNode mixinInstanceFieldNode = classNode.addField(fieldName, Modifier.STATIC, fieldType, new ConstructorCallExpression(fieldType, constructorArguments));
        mixinInstanceFieldNode.addAnnotation(new AnnotationNode(ClassHelper.make(MixinInstance.class)));
        
        addJunitRuleFields(classNode);
        
        return mixinInstanceFieldNode;
    }

    protected void addJunitRuleFields(ClassNode classNode) {
        if(classNode.getField(JUNIT_ADAPTER_FIELD_NAME) != null) {
            return;
        }
        ClassNode junitAdapterType = ClassHelper.make(TestRuntimeJunitAdapter.class);
        FieldNode junitAdapterFieldNode = classNode.addField(JUNIT_ADAPTER_FIELD_NAME, Modifier.STATIC, junitAdapterType, new ConstructorCallExpression(junitAdapterType, MethodCallExpression.NO_ARGUMENTS));
        boolean spockTest = isSpockTest(classNode);
        FieldNode staticRuleFieldNode = classNode.addField(RULE_FIELD_NAME_BASE + "StaticClassRule", Modifier.PRIVATE | Modifier.STATIC, ClassHelper.make(TestRule.class), new MethodCallExpression(new FieldExpression(junitAdapterFieldNode), "newClassRule", new ClassExpression(classNode)));
        AnnotationNode classRuleAnnotation = new AnnotationNode(ClassHelper.make(ClassRule.class));
        if(spockTest) {
            // @ClassRule must be added to @Shared field in spock
            FieldNode spockSharedRuleFieldNode = classNode.addField(RULE_FIELD_NAME_BASE + "SharedClassRule", Modifier.PUBLIC, ClassHelper.make(TestRule.class), new FieldExpression(staticRuleFieldNode));
            spockSharedRuleFieldNode.addAnnotation(classRuleAnnotation);
            spockSharedRuleFieldNode.addAnnotation(new AnnotationNode(ClassHelper.make(Shared.class)));
            if(spockTest) {
                addSpockFieldMetadata(spockSharedRuleFieldNode, 0);
            }
        } else {
            staticRuleFieldNode.setModifiers(Modifier.PUBLIC | Modifier.STATIC);
            staticRuleFieldNode.addAnnotation(classRuleAnnotation);
        }

        FieldNode ruleFieldNode = classNode.addField(RULE_FIELD_NAME_BASE + "Rule", Modifier.PUBLIC, ClassHelper.make(TestRule.class), new MethodCallExpression(new FieldExpression(junitAdapterFieldNode), "newRule", new VariableExpression("this")));
        ruleFieldNode.addAnnotation(new AnnotationNode(ClassHelper.make(Rule.class)));
        if(spockTest) {
            addSpockFieldMetadata(ruleFieldNode, 0);
        }
    }
    
    private void addSpockFieldMetadata(FieldNode field, int ordinal) {
        AnnotationNode ann = new AnnotationNode(ClassHelper.make(FieldMetadata.class));
        ann.setMember(FieldMetadata.NAME, new ConstantExpression(field.getName()));
        ann.setMember(FieldMetadata.ORDINAL, new ConstantExpression(ordinal));
        ann.setMember(FieldMetadata.LINE, new ConstantExpression(field.getLineNumber()));
        field.addAnnotation(ann);
      }

    private static class Junit3TestFixtureMethodHandler {
        ClassNode classNode;
        List<MethodNode> beforeMethods = new ArrayList<MethodNode>();
        List<MethodNode> afterMethods = new ArrayList<MethodNode>();
        int beforeClassMethodCount = 0;
        int afterClassMethodCount = 0;
        boolean hasExistingSetUp;
        boolean hasExistingTearDown;
        
        public Junit3TestFixtureMethodHandler(ClassNode classNode) {
            this.classNode=classNode;
            hasExistingSetUp = classNode.hasDeclaredMethod(SET_UP_METHOD, Parameter.EMPTY_ARRAY);
            hasExistingTearDown = classNode.hasDeclaredMethod(TEAR_DOWN_METHOD, Parameter.EMPTY_ARRAY);
        }

        public void mixinSuperClassChanged() {
            beforeClassMethodCount = 0;
            afterClassMethodCount = 0;
        }
        
        public void handle(MethodNode mixinMethod, MethodNode weavedMethod) {
            if (hasAnnotation(mixinMethod, Before.class)) {
                beforeMethods.add(mixinMethod);
            }
            if (hasAnnotation(mixinMethod, BeforeClass.class)) {
                beforeMethods.add(beforeClassMethodCount++, mixinMethod);
            }
            if (hasAnnotation(mixinMethod, After.class)) {
                afterMethods.add(mixinMethod);
            }
            if (hasAnnotation(mixinMethod, AfterClass.class)) {
                afterMethods.add(afterClassMethodCount++, mixinMethod);
            }
        }
        
        public void postProcessClassNode() {
            addMethodCallsToMethod(classNode, SET_UP_METHOD, beforeMethods);
            addMethodCallsToMethod(classNode, TEAR_DOWN_METHOD, afterMethods);
            handleTestRuntimeJunitSetUpAndTearDownCalls();
        }

        private void handleTestRuntimeJunitSetUpAndTearDownCalls() {
            FieldNode junitAdapterFieldNode = classNode.getDeclaredField(JUNIT_ADAPTER_FIELD_NAME);
            if(junitAdapterFieldNode==null) {
                return;
            }

            // add rule calls to junit setup/teardown only once, there might be several test mixins applied for the same class
            if(classNode.redirect().getNodeMetaData(JUNIT3_RULE_SETUP_TEARDOWN_APPLIED_KEY) != Boolean.TRUE) {
                BlockStatement setUpMethodBody = getOrCreateNoArgsMethodBody(classNode, SET_UP_METHOD);
                if(!hasExistingSetUp) {
                    setUpMethodBody.getStatements().add(0, new ExpressionStatement(new MethodCallExpression(new VariableExpression("super"), SET_UP_METHOD, GrailsArtefactClassInjector.ZERO_ARGS)));
                }
                BlockStatement tearDownMethodBody = getOrCreateNoArgsMethodBody(classNode, TEAR_DOWN_METHOD);
                setUpMethodBody.getStatements().add(1, new ExpressionStatement(new MethodCallExpression(new FieldExpression(junitAdapterFieldNode), SET_UP_METHOD, new VariableExpression("this"))));
                tearDownMethodBody.addStatement(new ExpressionStatement(new MethodCallExpression(new FieldExpression(junitAdapterFieldNode), TEAR_DOWN_METHOD, new VariableExpression("this"))));
                if(!hasExistingTearDown) {
                    tearDownMethodBody.addStatement(new ExpressionStatement(new MethodCallExpression(new VariableExpression("super"), TEAR_DOWN_METHOD, GrailsArtefactClassInjector.ZERO_ARGS)));
                }
                classNode.redirect().setNodeMetaData(JUNIT3_RULE_SETUP_TEARDOWN_APPLIED_KEY, Boolean.TRUE);
            }
        }
    }


    static protected FieldNode addLegacyMixinFieldIfNonExistent(ClassNode classNode, ClassNode fieldType, String fieldName) {
        ClassNode targetAwareInterface = GrailsASTUtils.findInterface(fieldType, new ClassNode(TestMixinTargetAware.class).getPlainNodeReference());
        if (classNode != null && classNode.getField(fieldName) == null) {
            Expression constructorArgument = new ArgumentListExpression();
            if(targetAwareInterface != null) {
                MapExpression namedArguments = new MapExpression();
                namedArguments.addMapEntryExpression(new MapEntryExpression(new ConstantExpression("target"), new VariableExpression("this")));
                constructorArgument = namedArguments;
            }
            return classNode.addField(fieldName, Modifier.PRIVATE, fieldType,
                new ConstructorCallExpression(fieldType, constructorArgument));
        }
        return null;
    }

    static protected boolean hasDeclaredMethod(ClassNode classNode, MethodNode mixinMethod) {
        return classNode.hasDeclaredMethod(mixinMethod.getName(), mixinMethod.getParameters());
    }

    static protected boolean hasAnnotation(MethodNode mixinMethod, Class<?> beforeClass) {
        return !mixinMethod.getAnnotations(new ClassNode(beforeClass)).isEmpty();
    }

    static protected void addMethodCallsToMethod(ClassNode classNode, String name, List<MethodNode> methods) {
        if (methods != null && !methods.isEmpty()) {
            BlockStatement setupMethodBody = getOrCreateNoArgsMethodBody(classNode, name);
            for (MethodNode beforeMethod : methods) {
                setupMethodBody.addStatement(new ExpressionStatement(new MethodCallExpression(new VariableExpression("this"), beforeMethod.getName(), GrailsArtefactClassInjector.ZERO_ARGS)));
            }
        }
    }

    static protected BlockStatement getOrCreateNoArgsMethodBody(ClassNode classNode, String name) {
        MethodNode setupMethod = classNode.getMethod(name, GrailsArtefactClassInjector.ZERO_PARAMETERS);
        return getOrCreateMethodBody(classNode, setupMethod, name);
    }

    static protected BlockStatement getOrCreateMethodBody(ClassNode classNode, MethodNode methodNode, String name) {
        BlockStatement methodBody;
        if (!methodNode.getDeclaringClass().equals(classNode)) {
            methodBody = new BlockStatement();
            methodNode = new MethodNode(name, Modifier.PUBLIC, methodNode.getReturnType(), GrailsArtefactClassInjector.ZERO_PARAMETERS, null, methodBody);
            classNode.addMethod(methodNode);
        }
        else {
            final Statement setupMethodBody = methodNode.getCode();
            if (!(setupMethodBody instanceof BlockStatement)) {
                methodBody = new BlockStatement();
                if (setupMethodBody != null) {
                    if (!(setupMethodBody instanceof ReturnStatement)) {
                        methodBody.addStatement(setupMethodBody);
                    }
                }
                methodNode.setCode(methodBody);
            }
            else {
                methodBody = (BlockStatement) setupMethodBody;
            }
        }
        return methodBody;
    }

    public static boolean isJunit3Test(ClassNode classNode) {
        return GrailsASTUtils.isSubclassOf(classNode, JUNIT3_CLASS);
    }

    public static boolean isSpockTest(ClassNode classNode) {
        return GrailsASTUtils.isSubclassOf(classNode, SPEC_CLASS);
    }

    protected boolean isCandidateMethod(MethodNode declaredMethod) {
        return !shouldSkipMethod(declaredMethod) && isAddableMethod(declaredMethod) && 
                !hasSimilarMethod(declaredMethod, ClassHelper.make(TestRuntimeAwareMixin.class));
    }

    protected boolean shouldSkipMethod(MethodNode declaredMethod){
        return declaredMethod.getAnnotations(SKIP_METHOD_CLASS_NODE).size() > 0;
    }

    public static boolean isAddableMethod(MethodNode declaredMethod) {
        ClassNode groovyMethods = GROOVY_OBJECT_CLASS_NODE;
        String methodName = declaredMethod.getName();
        return !declaredMethod.isSynthetic() &&
                !methodName.contains("$") &&
                Modifier.isPublic(declaredMethod.getModifiers()) &&
                !Modifier.isAbstract(declaredMethod.getModifiers()) &&
                !hasSimilarMethod(declaredMethod, groovyMethods);
    }

    protected static boolean hasSimilarMethod(MethodNode declaredMethod, ClassNode groovyMethods) {
        return groovyMethods.hasMethod(declaredMethod.getName(), declaredMethod.getParameters());
    }

    protected void error(SourceUnit source, String me) {
        source.getErrorCollector().addError(new SimpleMessage(me,source), true);
    }

    protected void autoAnnotateSetupTeardown(ClassNode classNode) {
        MethodNode setupMethod = classNode.getDeclaredMethod(SET_UP_METHOD, GrailsArtefactClassInjector.ZERO_PARAMETERS);
        if ( setupMethod != null && setupMethod.getAnnotations(TestForTransformation.BEFORE_CLASS_NODE).size() == 0) {
            setupMethod.addAnnotation(TestForTransformation.BEFORE_ANNOTATION);
        }

        MethodNode tearDown = classNode.getDeclaredMethod(TEAR_DOWN_METHOD, GrailsArtefactClassInjector.ZERO_PARAMETERS);
        if ( tearDown != null && tearDown.getAnnotations(TestForTransformation.AFTER_CLASS_NODE).size() == 0) {
            tearDown.addAnnotation(TestForTransformation.AFTER_ANNOTATION);
        }
    }
}
