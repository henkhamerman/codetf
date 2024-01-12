Refactoring Types: ['Inline Method']
omp/GlobalTypeInfo.java
/*
 * Copyright 2013 The Closure Compiler Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.javascript.jscomp;

import com.google.common.base.Joiner;
import com.google.common.base.Preconditions;
import com.google.common.collect.HashBasedTable;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.LinkedHashMultimap;
import com.google.common.collect.Multimap;
import com.google.javascript.jscomp.CodingConvention.Bind;
import com.google.javascript.jscomp.NewTypeInference.WarningReporter;
import com.google.javascript.jscomp.NodeTraversal.AbstractShallowCallback;
import com.google.javascript.jscomp.newtypes.Declaration;
import com.google.javascript.jscomp.newtypes.DeclaredFunctionType;
import com.google.javascript.jscomp.newtypes.DeclaredTypeRegistry;
import com.google.javascript.jscomp.newtypes.EnumType;
import com.google.javascript.jscomp.newtypes.FunctionType;
import com.google.javascript.jscomp.newtypes.FunctionTypeBuilder;
import com.google.javascript.jscomp.newtypes.JSType;
import com.google.javascript.jscomp.newtypes.JSTypeCreatorFromJSDoc;
import com.google.javascript.jscomp.newtypes.JSTypes;
import com.google.javascript.jscomp.newtypes.Namespace;
import com.google.javascript.jscomp.newtypes.NamespaceLit;
import com.google.javascript.jscomp.newtypes.NominalType;
import com.google.javascript.jscomp.newtypes.NominalType.RawNominalType;
import com.google.javascript.jscomp.newtypes.QualifiedName;
import com.google.javascript.jscomp.newtypes.Typedef;
import com.google.javascript.rhino.JSDocInfo;
import com.google.javascript.rhino.Node;
import com.google.javascript.rhino.Token;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Contains information about all scopes; for every variable reference computes
 * whether it is local, a formal parameter, etc.; and computes information about
 * the class hierarchy.
 *
 * <p>Used by the new type inference. See go/jscompiler-new-type-checker for the
 * latest updates.
 *
 * @author blickly@google.com (Ben Lickly)
 * @author dimvar@google.com (Dimitris Vardoulakis)
 */
class GlobalTypeInfo implements CompilerPass {

  static final DiagnosticType DUPLICATE_JSDOC = DiagnosticType.warning(
      "JSC_DUPLICATE_JSDOC",
      "Found two JsDoc comments for variable: {0}.\n");

  static final DiagnosticType REDECLARED_PROPERTY = DiagnosticType.warning(
      "JSC_REDECLARED_PROPERTY",
      "Found two declarations for property {0} of type {1}.\n");

  static final DiagnosticType INVALID_PROP_OVERRIDE = DiagnosticType.warning(
      "JSC_INVALID_PROP_OVERRIDE",
      "Invalid redeclaration of property {0}.\n" +
      "inherited type  : {1}\n" +
      "overriding type : {2}\n");

  static final DiagnosticType CTOR_IN_DIFFERENT_SCOPE = DiagnosticType.warning(
      "JSC_CTOR_IN_DIFFERENT_SCOPE",
      "Modifying the prototype is only allowed if the constructor is " +
      "in the same scope\n");

  static final DiagnosticType UNRECOGNIZED_TYPE_NAME = DiagnosticType.warning(
      "JSC_UNRECOGNIZED_TYPE_NAME",
      "Type annotation references non-existent type {0}.");

  static final DiagnosticType STRUCTDICT_WITHOUT_CTOR = DiagnosticType.warning(
      "JSC_STRUCTDICT_WITHOUT_CTOR",
      "{0} used without @constructor.");

  static final DiagnosticType EXPECTED_CONSTRUCTOR = DiagnosticType.warning(
      "JSC_EXPECTED_CONSTRUCTOR",
      "Expected constructor name but found {0}.");

  static final DiagnosticType EXPECTED_INTERFACE = DiagnosticType.warning(
      "JSC_EXPECTED_INTERFACE",
      "Expected interface name but found {0}.");

  static final DiagnosticType INEXISTENT_PARAM = DiagnosticType.warning(
      "JSC_INEXISTENT_PARAM",
      "parameter {0} does not appear in {1}''s parameter list");

  static final DiagnosticType CONST_WITHOUT_INITIALIZER =
      DiagnosticType.warning(
          "JSC_CONST_WITHOUT_INITIALIZER",
          "Constants must be initialized when they are defined.");

  static final DiagnosticType COULD_NOT_INFER_CONST_TYPE =
      DiagnosticType.warning(
          "JSC_COULD_NOT_INFER_CONST_TYPE",
          "All constants must be typed. The compiler could not infer the type "
          + "of this constant. Please use an explicit type annotation.");

  static final DiagnosticType MISPLACED_CONST_ANNOTATION =
      DiagnosticType.warning(
          "JSC_MISPLACED_CONST_ANNOTATION",
          "This property cannot be @const. " +
          "The @const annotation is only allowed for " +
          "properties of namespaces, prototype properties, " +
          "static properties of constructors, " +
          "and properties of the form this.prop declared inside constructors.");

  static final DiagnosticType CANNOT_OVERRIDE_FINAL_METHOD =
      DiagnosticType.warning(
      "JSC_CANNOT_OVERRIDE_FINAL_METHOD",
      "Final method {0} cannot be overriden.");

  static final DiagnosticType CANNOT_INIT_TYPEDEF =
      DiagnosticType.warning(
      "JSC_CANNOT_INIT_TYPEDEF",
      "A typedef variable represents a type name; " +
      "it cannot be assigned a value.");

  static final DiagnosticType ANONYMOUS_NOMINAL_TYPE =
      DiagnosticType.warning(
          "JSC_ANONYMOUS_NOMINAL_TYPE",
          "Must specify a name when defining a class or interface.");

  static final DiagnosticType MALFORMED_ENUM =
      DiagnosticType.warning(
          "JSC_MALFORMED_ENUM",
          "An enum must be initialized to a non-empty object literal.");

  static final DiagnosticType DUPLICATE_PROP_IN_ENUM =
      DiagnosticType.warning(
          "JSC_DUPLICATE_PROP_IN_ENUM",
          "Property {0} appears twice in the enum declaration.");

  static final DiagnosticType UNDECLARED_NAMESPACE =
      DiagnosticType.warning(
          "JSC_UNDECLARED_NAMESPACE",
          "Undeclared reference to {0}.");

  static final DiagnosticType LENDS_ON_BAD_TYPE =
      DiagnosticType.warning(
          "JSC_LENDS_ON_BAD_TYPE",
          "May only lend properties to namespaces, constructors and their"
          + " prototypes. Found {0}.");

  static final DiagnosticType FUNCTION_CONSTRUCTOR_NOT_DEFINED =
      DiagnosticType.error(
          "JSC_FUNCTION_CONSTRUCTOR_NOT_DEFINED",
          "You must provide externs that define the built-in Function constructor.");

  static final DiagnosticType INVALID_INTERFACE_PROP_INITIALIZER =
      DiagnosticType.warning(
          "JSC_INVALID_INTERFACE_PROP_INITIALIZER",
          "Invalid initialization of interface property.");

  static final DiagnosticGroup ALL_DIAGNOSTICS = new DiagnosticGroup(
      ANONYMOUS_NOMINAL_TYPE,
      CANNOT_INIT_TYPEDEF,
      CANNOT_OVERRIDE_FINAL_METHOD,
      CONST_WITHOUT_INITIALIZER,
      COULD_NOT_INFER_CONST_TYPE,
      CTOR_IN_DIFFERENT_SCOPE,
      DUPLICATE_JSDOC,
      DUPLICATE_PROP_IN_ENUM,
      EXPECTED_CONSTRUCTOR,
      EXPECTED_INTERFACE,
      FUNCTION_CONSTRUCTOR_NOT_DEFINED,
      INEXISTENT_PARAM,
      INVALID_INTERFACE_PROP_INITIALIZER,
      INVALID_PROP_OVERRIDE,
      LENDS_ON_BAD_TYPE,
      MALFORMED_ENUM,
      MISPLACED_CONST_ANNOTATION,
      REDECLARED_PROPERTY,
      STRUCTDICT_WITHOUT_CTOR,
      UNDECLARED_NAMESPACE,
      UNRECOGNIZED_TYPE_NAME,
      TypeCheck.CONFLICTING_EXTENDED_TYPE,
      TypeCheck.ENUM_NOT_CONSTANT,
      TypeCheck.INCOMPATIBLE_EXTENDED_PROPERTY_TYPE,
      TypeCheck.MULTIPLE_VAR_DEF,
      TypeCheck.UNKNOWN_OVERRIDE,
      TypeValidator.INTERFACE_METHOD_NOT_IMPLEMENTED //,
      // VarCheck.UNDEFINED_VAR_ERROR,
      // VariableReferenceCheck.REDECLARED_VARIABLE,
      // VariableReferenceCheck.EARLY_REFERENCE
      );

  // An out-to-in list of the scopes, built during CollectNamedTypes
  // This will be reversed at the end of GlobalTypeInfo to make sure
  // that the scopes can be processed in-to-out in NewTypeInference.
  private final List<Scope> scopes = new ArrayList<>();
  private Scope globalScope;
  private WarningReporter warnings;
  private JSTypeCreatorFromJSDoc typeParser;
  private final AbstractCompiler compiler;
  private final CodingConvention convention;
  private final Map<Node, String> anonFunNames = new LinkedHashMap<>();
  private static final String ANON_FUN_PREFIX = "%anon_fun";
  private int freshId = 1;
  // Only for original definitions, not for aliased constructors
  private Map<Node, RawNominalType> nominaltypesByNode = new LinkedHashMap<>();
  // Keyed on RawNominalTypes and property names
  private HashBasedTable<RawNominalType, String, PropertyDef> propertyDefs =
      HashBasedTable.create();
  // TODO(dimvar): Eventually attach these to nodes, like the current types.
  private Map<Node, JSType> castTypes = new LinkedHashMap<>();
  private Map<Node, JSType> declaredObjLitProps = new LinkedHashMap<>();

  private JSTypes commonTypes;

  GlobalTypeInfo(AbstractCompiler compiler) {
    this.warnings = new WarningReporter(compiler);
    this.compiler = compiler;
    this.convention = compiler.getCodingConvention();
    this.typeParser = new JSTypeCreatorFromJSDoc(this.convention);
    this.commonTypes = JSTypes.make();
  }

  Collection<Scope> getScopes() {
    return scopes;
  }

  Scope getGlobalScope() {
    return globalScope;
  }

  JSTypes getTypesUtilObject() {
    return commonTypes;
  }

  JSType getCastType(Node n) {
    JSType t = castTypes.get(n);
    Preconditions.checkNotNull(t);
    return t;
  }

  JSType getPropDeclaredType(Node n) {
    return declaredObjLitProps.get(n);
  }

  // Differs from the similar method in Scope class on how it treats qnames.
  String getFunInternalName(Node n) {
    Preconditions.checkArgument(n.isFunction());
    if (anonFunNames.containsKey(n)) {
      return anonFunNames.get(n);
    }
    Node fnNameNode = NodeUtil.getFunctionNameNode(n);
    // We don't want to use qualified names here
    Preconditions.checkState(fnNameNode != null);
    Preconditions.checkState(fnNameNode.isName());
    return fnNameNode.getString();
  }

  @Override
  public void process(Node externs, Node root) {
    Preconditions.checkNotNull(warnings, "Cannot rerun GlobalTypeInfo.process");
    Preconditions.checkArgument(externs == null || externs.isSyntheticBlock());
    Preconditions.checkArgument(root.isSyntheticBlock());
    globalScope =
        new Scope(root, null, ImmutableList.<String>of(), commonTypes);
    scopes.add(globalScope);

    // Processing of a scope is split into many separate phases, and it's not
    // straightforward to remember which phase does what.

    // (1) Find names of classes, interfaces, typedefs, enums, and namespaces
    //   defined in the global scope.
    CollectNamedTypes rootCnt = new CollectNamedTypes(globalScope);
    if (externs != null) {
      NodeTraversal.traverse(compiler, externs, rootCnt);
    }
    NodeTraversal.traverse(compiler, root, rootCnt);
    // (2) Determine the type represented by each typedef and each enum
    globalScope.resolveTypedefs(typeParser);
    globalScope.resolveEnums(typeParser);
    // (3) Repeat steps 1-2 for all the other scopes (outer-to-inner)
    for (int i = 1; i < scopes.size(); i++) {
      Scope s = scopes.get(i);
      CollectNamedTypes cnt = new CollectNamedTypes(s);
      NodeTraversal.traverse(compiler, s.getBody(), cnt);
      s.resolveTypedefs(typeParser);
      s.resolveEnums(typeParser);
      if (NewTypeInference.measureMem) {
        NewTypeInference.updatePeakMem();
      }
    }

    // If the Function constructor isn't defined, we cannot create function
    // types. Exit early.
    if (this.commonTypes.getFunctionType() == null) {
      warnings.add(JSError.make(root, FUNCTION_CONSTRUCTOR_NOT_DEFINED));
      return;
    }

    // (4) The bulk of the global-scope processing happens here:
    //     - Create scopes for functions
    //     - Declare properties on types
    ProcessScope rootPs = new ProcessScope(globalScope);
    if (externs != null) {
      NodeTraversal.traverse(compiler, externs, rootPs);
    }
    NodeTraversal.traverse(compiler, root, rootPs);
    // (5) Things that must happen after the traversal of the scope
    rootPs.finishProcessingScope();

    // (6) Repeat steps 4-5 for all the other scopes (outer-to-inner)
    for (int i = 1; i < scopes.size(); i++) {
      Scope s = scopes.get(i);
      ProcessScope ps = new ProcessScope(s);
      NodeTraversal.traverse(compiler, s.getBody(), ps);
      ps.finishProcessingScope();
      if (NewTypeInference.measureMem) {
        NewTypeInference.updatePeakMem();
      }
    }

    // (7) Adjust types of properties based on inheritance information.
    //     Report errors in the inheritance chain.
    reportInheritanceErrors();

    nominaltypesByNode = null;
    propertyDefs = null;
    for (Scope s : scopes) {
      s.removeTmpData();
    }
    Map<Node, String> unknownTypes = typeParser.getUnknownTypesMap();
    for (Map.Entry<Node, String> unknownTypeEntry : unknownTypes.entrySet()) {
      warnings.add(JSError.make(unknownTypeEntry.getKey(),
              UNRECOGNIZED_TYPE_NAME, unknownTypeEntry.getValue()));
    }
    // The jsdoc parser doesn't have access to the error functions in the jscomp
    // package, so we collect its warnings here.
    for (JSError warning : typeParser.getWarnings()) {
      warnings.add(warning);
    }
    typeParser = null;
    compiler.setSymbolTable(this);
    warnings = null;

    // If a scope s1 contains a scope s2, then s2 must be before s1 in scopes.
    // The type inference relies on this fact to process deeper scopes
    // before shallower scopes.
    Collections.reverse(scopes);
  }

  private Collection<PropertyDef> getPropDefsFromInterface(
      NominalType nominalType, String pname) {
    Preconditions.checkArgument(nominalType.isFinalized());
    Preconditions.checkArgument(nominalType.isInterface());
    if (nominalType.getPropDeclaredType(pname) == null) {
      return ImmutableSet.of();
    } else if (propertyDefs.get(nominalType.getId(), pname) != null) {
      return ImmutableSet.of(propertyDefs.get(nominalType.getId(), pname));
    }
    ImmutableSet.Builder<PropertyDef> result = ImmutableSet.builder();
    for (NominalType interf : nominalType.getInstantiatedInterfaces()) {
      result.addAll(getPropDefsFromInterface(interf, pname));
    }
    return result.build();
  }

  private PropertyDef getPropDefFromClass(
      NominalType nominalType, String pname) {
    while (nominalType.getPropDeclaredType(pname) != null) {
      Preconditions.checkArgument(nominalType.isFinalized());
      Preconditions.checkArgument(nominalType.isClass());

      if (propertyDefs.get(nominalType.getId(), pname) != null) {
        return propertyDefs.get(nominalType.getId(), pname);
      }
      nominalType = nominalType.getInstantiatedSuperclass();
    }
    return null;
  }

  /** Report all errors that must be checked at the end of GlobalTypeInfo */
  private void reportInheritanceErrors() {
    Deque<Node> workset = new LinkedList<>(nominaltypesByNode.keySet());
    int iterations = 0;
    final int MAX_ITERATIONS = 50000;
  workset_loop:
    while (!workset.isEmpty()) {
      // TODO(blickly): Fix this infinite loop and remove these counters
      Preconditions.checkState(iterations < MAX_ITERATIONS);
      Node funNode = workset.removeFirst();
      RawNominalType rawNominalType = nominaltypesByNode.get(funNode);
      NominalType superClass = rawNominalType.getSuperClass();
      Set<String> nonInheritedPropNames = rawNominalType.getAllOwnProps();
      if (superClass != null && !superClass.isFinalized()) {
        workset.addLast(funNode);
        iterations++;
        continue workset_loop;
      }
      for (NominalType superInterf : rawNominalType.getInterfaces()) {
        if (!superInterf.isFinalized()) {
          workset.addLast(funNode);
          iterations++;
          continue workset_loop;
        }
      }

      Multimap<String, DeclaredFunctionType> propMethodTypesToProcess =
          LinkedHashMultimap.create();
      Multimap<String, JSType> propTypesToProcess = LinkedHashMultimap.create();
      // Collect inherited types for extended classes
      if (superClass != null) {
        Preconditions.checkState(superClass.isFinalized());
        // TODO(blickly): Can we optimize this to skip unnecessary iterations?
        for (String pname : superClass.getAllPropsOfClass()) {
          nonInheritedPropNames.remove(pname);
          checkSuperProperty(rawNominalType, superClass, pname,
              propMethodTypesToProcess, propTypesToProcess);
        }
      }
      // Collect inherited types for extended/implemented interfaces
      for (NominalType superInterf : rawNominalType.getInterfaces()) {
        Preconditions.checkState(superInterf.isFinalized());
        for (String pname : superInterf.getAllPropsOfInterface()) {
          nonInheritedPropNames.remove(pname);
          checkSuperProperty(rawNominalType, superInterf, pname,
              propMethodTypesToProcess, propTypesToProcess);
        }
      }
      // Munge inherited types of methods
      for (String pname : propMethodTypesToProcess.keySet()) {
        Collection<DeclaredFunctionType> methodTypes =
            propMethodTypesToProcess.get(pname);
        Preconditions.checkState(!methodTypes.isEmpty());
        PropertyDef localPropDef =
            propertyDefs.get(rawNominalType, pname);
        // To find the declared type of a method, we must meet declared types
        // from all inherited methods.
        DeclaredFunctionType superMethodType =
            DeclaredFunctionType.meet(methodTypes);
        DeclaredFunctionType updatedMethodType =
            localPropDef.methodType.withTypeInfoFromSuper(
                superMethodType, getsTypeInfoFromParentMethod(localPropDef));
        localPropDef.updateMethodType(updatedMethodType);
        propTypesToProcess.put(pname,
            commonTypes.fromFunctionType(updatedMethodType.toFunctionType()));
      }
      // Check inherited types of all props
    add_interface_props:
      for (String pname : propTypesToProcess.keySet()) {
        Collection<JSType> defs = propTypesToProcess.get(pname);
        Preconditions.checkState(!defs.isEmpty());
        JSType resultType = JSType.TOP;
        for (JSType inheritedType : defs) {
          resultType = JSType.meet(resultType, inheritedType);
          if (!resultType.isBottom()) {
            resultType = inheritedType;
          } else {
            // TOOD(blickly): Fix this error message to include supertype names
            warnings.add(JSError.make(
                funNode, TypeCheck.INCOMPATIBLE_EXTENDED_PROPERTY_TYPE,
                NodeUtil.getFunctionName(funNode), pname, "", ""));
            continue add_interface_props;
          }
        }
        // TODO(dimvar): check if we can have @const props here
        rawNominalType.addProtoProperty(pname, null, resultType, false);
      }

      // Warn for a prop declared with @override that isn't overriding anything.
      for (String pname : nonInheritedPropNames) {
        Node defSite = propertyDefs.get(rawNominalType, pname).defSite;
        JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(defSite);
        if (jsdoc != null && jsdoc.isOverride()) {
          warnings.add(JSError.make(defSite, TypeCheck.UNKNOWN_OVERRIDE,
                  pname, rawNominalType.getName()));
        }
      }

      // Finalize nominal type once all properties are added.
      rawNominalType.finalizeNominalType();
    }
  }

  private void checkSuperProperty(
      RawNominalType current, NominalType superType, String pname,
      Multimap<String, DeclaredFunctionType> propMethodTypesToProcess,
      Multimap<String, JSType> propTypesToProcess) {
    JSType inheritedPropType = superType.getPropDeclaredType(pname);
    if (inheritedPropType == null) {
      // No need to go further for undeclared props.
      return;
    }
    Collection<PropertyDef> inheritedPropDefs;
    if (superType.isInterface()) {
      inheritedPropDefs = getPropDefsFromInterface(superType, pname);
    } else {
      inheritedPropDefs =
          ImmutableSet.of(getPropDefFromClass(superType, pname));
    }
    if (superType.isInterface() && current.isClass() &&
        !current.mayHaveProp(pname)) {
      warnings.add(JSError.make(
          inheritedPropDefs.iterator().next().defSite,
          TypeValidator.INTERFACE_METHOD_NOT_IMPLEMENTED,
          pname, superType.toString(), current.toString()));
      return;
    }
    PropertyDef localPropDef = propertyDefs.get(current, pname);
    JSType localPropType = localPropDef == null ? null :
        current.getInstancePropDeclaredType(pname);
    if (localPropDef != null && superType.isClass() &&
        localPropType.getFunType() != null &&
        superType.hasConstantProp(pname)) {
      // TODO(dimvar): This doesn't work for multiple levels in the hierarchy.
      // Clean up how we process inherited properties and then fix this.
      warnings.add(JSError.make(
          localPropDef.defSite, CANNOT_OVERRIDE_FINAL_METHOD, pname));
      return;
    }
    // System.out.println("nominalType: " + current + "'s " + pname +
    //     " localPropType: " + localPropType +
    //     " with super: " + superType +
    //     " inheritedPropType: " + inheritedPropType);
    if (localPropType == null) {
      // Add property from interface to class
      propTypesToProcess.put(pname, inheritedPropType);
    } else if (!getsTypeInfoFromParentMethod(localPropDef)
        && !localPropType.isSubtypeOf(inheritedPropType)) {
      warnings.add(JSError.make(
          localPropDef.defSite, INVALID_PROP_OVERRIDE, pname,
          inheritedPropType.toString(), localPropType.toString()));
    } else if (localPropDef.methodType != null) {
      // If we are looking at a method definition, munging may be needed
      for (PropertyDef inheritedPropDef : inheritedPropDefs) {
        if (inheritedPropDef.methodType != null) {
          propMethodTypesToProcess.put(pname,
              inheritedPropDef.methodType.substituteNominalGenerics(superType));
        }
      }
    }
  }

  private static boolean getsTypeInfoFromParentMethod(PropertyDef pd) {
    if (pd == null || pd.methodType == null) {
      return false;
    }
    JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(pd.defSite);
    return jsdoc == null || jsdoc.isOverride();
  }

  /**
   * Collects names of classes, interfaces, namespaces, typedefs and enums.
   * This way, if a type name appears before its declaration, we know what
   * it refers to.
   */
  private class CollectNamedTypes extends AbstractShallowCallback {
    private final Scope currentScope;

    CollectNamedTypes(Scope s) {
      this.currentScope = s;
    }

    private void processQualifiedDefinition(Node qnameNode) {
      Preconditions.checkArgument(qnameNode.isGetProp());
      Preconditions.checkArgument(qnameNode.isQualifiedName());
      Node recv = qnameNode.getFirstChild();
      if (!currentScope.isNamespace(recv)) {
        return;
      }
      if (NodeUtil.isNamespaceDecl(qnameNode)) {
        visitNamespace(qnameNode);
      } else if (NodeUtil.isTypedefDecl(qnameNode)) {
        visitTypedef(qnameNode);
      } else if (NodeUtil.isEnumDecl(qnameNode)) {
        visitEnum(qnameNode);
      } else if (NodeUtil.isAliasedNominalTypeDecl(qnameNode)) {
        maybeRecordAliasedNominalType(qnameNode);
      } else if (!currentScope.isDefined(qnameNode)) {
        Namespace ns = currentScope.getNamespace(QualifiedName.fromNode(recv));
        String pname = qnameNode.getLastChild().getString();
        // A program can have an error where a namespace property is defined
        // twice: the first time with a non-namespace type and the second time
        // as a namespace.
        // Adding the non-namespace property here as undeclared prevents us
        // from mistakenly using the second definition later. We use ? for now,
        // but may find a better type in ProcessScope.
        ns.addUndeclaredProperty(pname, null, JSType.UNKNOWN, /* isConst */ false);
      }
    }

    @Override
    public void visit(NodeTraversal t, Node n, Node parent) {
      switch (n.getType()) {
        case Token.FUNCTION: {
          visitFunctionEarly(n);
          break;
        }
        case Token.VAR: {
          Node nameNode = n.getFirstChild();
          if (NodeUtil.isNamespaceDecl(nameNode)) {
            visitNamespace(nameNode);
          } else if (NodeUtil.isTypedefDecl(nameNode)) {
            visitTypedef(nameNode);
          } else if (NodeUtil.isEnumDecl(nameNode)) {
            visitEnum(nameNode);
          } else if (NodeUtil.isAliasedNominalTypeDecl(nameNode)) {
            maybeRecordAliasedNominalType(nameNode);
          }
          break;
        }
        case Token.EXPR_RESULT: {
          Node expr = n.getFirstChild();
          switch (expr.getType()) {
            case Token.ASSIGN:
              if (!expr.getFirstChild().isGetProp()) {
                return;
              }
              expr = expr.getFirstChild();
              // fall through
            case Token.GETPROP:
              if (isPrototypeProperty(expr)
                  || NodeUtil.referencesThis(expr)
                  || !expr.isQualifiedName()) {
                // Class & prototype properties are handled in ProcessScope
                return;
              }
              processQualifiedDefinition(expr);
              break;
            case Token.CALL: {
              List<String> decls = convention.identifyTypeDeclarationCall(expr);
              if (decls == null || decls.isEmpty()) {
                return;
              }
              currentScope.addUnknownTypeNames(decls);
              break;
            }
          }
          break;
        }
      }
    }

    private void visitNamespace(Node qnameNode) {
      if (currentScope.isDefined(qnameNode)) {
        return;
      }
      if (qnameNode.isGetProp()) {
        Preconditions.checkState(qnameNode.getParent().isAssign());
        qnameNode.getParent().putBooleanProp(Node.ANALYZED_DURING_GTI, true);
      }
      currentScope.addNamespace(qnameNode, qnameNode.isFromExterns());
    }

    private void visitTypedef(Node qnameNode) {
      Preconditions.checkState(qnameNode.isQualifiedName());
      qnameNode.putBooleanProp(Node.ANALYZED_DURING_GTI, true);
      if (NodeUtil.getInitializer(qnameNode) != null) {
        warnings.add(JSError.make(qnameNode, CANNOT_INIT_TYPEDEF));
      }
      // if (qnameNode.isName()
      //     && currentScope.isDefinedLocally(qnameNode.getString())) {
      //   warnings.add(JSError.make(
      //       qnameNode,
      //       VariableReferenceCheck.REDECLARED_VARIABLE,
      //       qnameNode.getQualifiedName()));
      // }
      if (currentScope.isDefined(qnameNode)) {
        return;
      }
      JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(qnameNode);
      Typedef td = Typedef.make(jsdoc.getTypedefType());
      currentScope.addTypedef(qnameNode, td);
    }

    private void visitEnum(Node qnameNode) {
      Preconditions.checkState(qnameNode.isQualifiedName());
      qnameNode.putBooleanProp(Node.ANALYZED_DURING_GTI, true);
      // if (qnameNode.isName()
      //     && currentScope.isDefinedLocally(qnameNode.getString())) {
      //   String qname = qnameNode.getQualifiedName();
      //   warnings.add(JSError.make(qnameNode,
      //           VariableReferenceCheck.REDECLARED_VARIABLE, qname));
      // }
      if (currentScope.isDefined(qnameNode)) {
        return;
      }
      Node init = NodeUtil.getInitializer(qnameNode);
      // First check if the definition is an alias of a previous enum.
      if (init != null && init.isQualifiedName()) {
        EnumType et = currentScope.getEnum(QualifiedName.fromNode(init));
        if (et != null) {
          currentScope.addEnum(qnameNode, et);
          return;
        }
      }
      // Then check if the enum initializer is an object literal.
      if (init == null || !init.isObjectLit() ||
          init.getFirstChild() == null) {
        warnings.add(JSError.make(qnameNode, MALFORMED_ENUM));
        return;
      }
      // Last, read the object-literal properties and create the EnumType.
      JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(qnameNode);
      Set<String> propNames = new LinkedHashSet<>();
      for (Node prop : init.children()) {
        String pname = NodeUtil.getObjectLitKeyName(prop);
        if (propNames.contains(pname)) {
          warnings.add(JSError.make(qnameNode, DUPLICATE_PROP_IN_ENUM, pname));
        }
        if (!convention.isValidEnumKey(pname)) {
          warnings.add(
              JSError.make(prop, TypeCheck.ENUM_NOT_CONSTANT, pname));
        }
        propNames.add(pname);
      }
      currentScope.addEnum(qnameNode,
          EnumType.make(
              qnameNode.getQualifiedName(),
              jsdoc.getEnumParameterType(),
              ImmutableSet.copyOf(propNames)));
    }

    private void visitFunctionEarly(Node fn) {
      JSDocInfo fnDoc = NodeUtil.getBestJSDocInfo(fn);
      Node nameNode = NodeUtil.getFunctionNameNode(fn);
      String internalName = createFunctionInternalName(fn, nameNode);
      boolean isRedeclaration;
      if (nameNode == null || !nameNode.isQualifiedName()) {
        isRedeclaration = false;
      } else if (nameNode.isName()) {
        isRedeclaration = currentScope.isDefinedLocally(nameNode.getString(), false);
      } else {
        isRedeclaration = currentScope.isDefined(nameNode);
      }
      ArrayList<String> formals = collectFormals(fn, fnDoc);
      createFunctionScope(fn, formals, internalName);
      maybeRecordNominalType(fn, nameNode, fnDoc, isRedeclaration);
    }

    private String createFunctionInternalName(Node fn, Node nameNode) {
      String internalName = null;
      if (nameNode == null || !nameNode.isName()) {
        // Anonymous and qualified names need gensymed names.
        internalName = ANON_FUN_PREFIX + freshId;
        anonFunNames.put(fn, internalName);
        freshId++;
      } else if (currentScope.isDefinedLocally(nameNode.getString(), false)) {
        String fnName = nameNode.getString();
        Preconditions.checkState(!fnName.contains("."));
        // warnings.add(JSError.make(
        //     fn, VariableReferenceCheck.REDECLARED_VARIABLE, fnName));
        // Redeclared variables also need gensymed names
        internalName = ANON_FUN_PREFIX + freshId;
        anonFunNames.put(fn, internalName);
        freshId++;
      } else {
        // fnNameNode is undefined simple name
        internalName = nameNode.getString();
      }
      return internalName;
    }

    private void createFunctionScope(
        Node fn, ArrayList<String> formals, String internalName) {
      Scope fnScope = new Scope(fn, currentScope, formals, null);
      if (!fn.isFromExterns()) {
        scopes.add(fnScope);
      }
      currentScope.addLocalFunDef(internalName, fnScope);
    }

    private ArrayList<String> collectFormals(Node fn, JSDocInfo fnDoc) {
      Preconditions.checkArgument(fn.isFunction());
      // Collect the names of the formals.
      // If a formal is a placeholder for variable arity, eg,
      // /** @param {...?} var_args */ function f(var_args) { ... }
      // then we don't collect it.
      // But to decide that we can't just use the jsdoc b/c the type parser
      // may ignore the jsdoc; the only reliable way is to collect the names of
      // formals after building the declared function type.
      ArrayList<String> formals = new ArrayList<>();
      // tmpRestFormals is used only for error checking
      ArrayList<String> tmpRestFormals = new ArrayList<>();
      Node param = NodeUtil.getFunctionParameters(fn).getFirstChild();
      while (param != null) {
        if (JSTypeCreatorFromJSDoc.isRestArg(fnDoc, param.getString())
            && param.getNext() == null) {
          tmpRestFormals.add(param.getString());
        } else {
          formals.add(param.getString());
        }
        param = param.getNext();
      }
      if (fnDoc != null) {
        for (String formalInJsdoc : fnDoc.getParameterNames()) {
          if (!formals.contains(formalInJsdoc) &&
              !tmpRestFormals.contains(formalInJsdoc)) {
            String functionName = NodeUtil.getFunctionName(fn);
            warnings.add(JSError.make(
                fn, INEXISTENT_PARAM, formalInJsdoc, functionName));
          }
        }
      }
      return formals;
    }

    private void maybeRecordNominalType(
        Node fn, Node nameNode, JSDocInfo fnDoc, boolean isRedeclaration) {
      if (fnDoc != null && (fnDoc.isConstructor() || fnDoc.isInterface())) {
        QualifiedName qname = QualifiedName.fromNode(nameNode);
        if (qname == null) {
          warnings.add(JSError.make(fn, ANONYMOUS_NOMINAL_TYPE));
          return;
        }
        ImmutableList<String> typeParameters = fnDoc.getTemplateTypeNames();
        RawNominalType rawNominalType;
        if (fnDoc.isInterface()) {
          rawNominalType = RawNominalType.makeInterface(fn, qname, typeParameters);
        } else if (fnDoc.makesStructs()) {
          rawNominalType = RawNominalType.makeStructClass(fn, qname, typeParameters);
        } else if (fnDoc.makesDicts()) {
          rawNominalType = RawNominalType.makeDictClass(fn, qname, typeParameters);
        } else {
          rawNominalType = RawNominalType.makeUnrestrictedClass(fn, qname, typeParameters);
        }
        nominaltypesByNode.put(fn, rawNominalType);
        if (isRedeclaration) {
          return;
        }
        if (nameNode.isName()
            || currentScope.isNamespace(nameNode.getFirstChild())) {
          if (nameNode.isGetProp()) {
            fn.getParent().getFirstChild()
                .putBooleanProp(Node.ANALYZED_DURING_GTI, true);
          } else if (currentScope.isTopLevel()) {
            maybeRecordBuiltinType(nameNode.getString(), rawNominalType);
          }
          currentScope.addNominalType(nameNode, rawNominalType);
        }
      } else if (fnDoc != null) {
        if (fnDoc.makesStructs()) {
          warnings.add(JSError.make(fn, STRUCTDICT_WITHOUT_CTOR, "@struct"));
        } else if (fnDoc.makesDicts()) {
          warnings.add(JSError.make(fn, STRUCTDICT_WITHOUT_CTOR, "@dict"));
        }
      }
    }

   private void maybeRecordBuiltinType(
       String name, RawNominalType rawNominalType) {
     switch (name) {
       case "Arguments":
         commonTypes.setArgumentsType(rawNominalType);
         break;
       case "Function":
         commonTypes.setFunctionType(rawNominalType);
         break;
       case "Object":
         commonTypes.setObjectType(rawNominalType);
         break;
       case "Number":
         commonTypes.setNumberInstance(rawNominalType.getInstanceAsJSType());
         break;
       case "String":
         commonTypes.setStringInstance(rawNominalType.getInstanceAsJSType());
         break;
       case "Boolean":
         commonTypes.setBooleanInstance(rawNominalType.getInstanceAsJSType());
         break;
       case "RegExp":
         commonTypes.setRegexpInstance(rawNominalType.getInstanceAsJSType());
         break;
       case "Array":
         commonTypes.setArrayType(rawNominalType);
         break;
     }
   }

    private void maybeRecordAliasedNominalType(Node nameNode) {
      Preconditions.checkArgument(nameNode.isQualifiedName());
      Node aliasedDef = nameNode.getParent();
      Preconditions.checkState(aliasedDef.isVar() || aliasedDef.isAssign());
      JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(aliasedDef);
      Node init = NodeUtil.getInitializer(nameNode);
      RawNominalType rawType =
          currentScope.getNominalType(QualifiedName.fromNode(init));
      String initQname = init.getQualifiedName();
      if (jsdoc.isConstructor()) {
        if (rawType == null || rawType.isInterface()) {
          warnings.add(JSError.make(init, EXPECTED_CONSTRUCTOR, initQname));
          return;
        }
      } else if (jsdoc.isInterface()) {
        if (rawType == null || !rawType.isInterface()) {
          warnings.add(JSError.make(init, EXPECTED_INTERFACE, initQname));
          return;
        }
      }
      // TODO(dimvar): If init is an unknown type name, we shouldn't warn;
      // Also, associate nameNode with an unknown type name when returning early
      currentScope.addNominalType(nameNode, rawType);
    }
  }

  private class ProcessScope extends AbstractShallowCallback {
    private final Scope currentScope;
    // /**
    //  * Keep track of undeclared vars as they are crawled to warn about
    //  * use before declaration and undeclared variables.
    //  * We use a multimap so we can give all warnings rather than just the first.
    //  */
    // private final Multimap<String, Node> undeclaredVars;
    private Set<Node> lendsObjlits = new LinkedHashSet<>();

    ProcessScope(Scope currentScope) {
      this.currentScope = currentScope;
      // this.undeclaredVars = LinkedHashMultimap.create();
    }

    void finishProcessingScope() {
      for (Node objlit : lendsObjlits) {
        processLendsNode(objlit);
      }
      lendsObjlits = null;

      // for (Node nameNode : undeclaredVars.values()) {
      //   warnings.add(JSError.make(nameNode,
      //         VarCheck.UNDEFINED_VAR_ERROR, nameNode.getString()));
      // }
    }

    /**
     * @lends can lend properties to an object X being defined in the same
     * statement as the @lends. To make sure that we've seen the definition of
     * X, we process @lends annotations after we've traversed the scope.
     *
     * @lends can only add properties to namespaces, constructors and prototypes
     */
    void processLendsNode(Node objlit) {
      JSDocInfo jsdoc = objlit.getJSDocInfo();
      String lendsName = jsdoc.getLendsName();
      Preconditions.checkNotNull(lendsName);
      QualifiedName lendsQname = QualifiedName.fromQualifiedString(lendsName);
      if (currentScope.isNamespace(lendsQname)) {
        processLendsToNamespace(lendsQname, lendsName, objlit);
      } else {
        RawNominalType rawType = checkValidLendsToPrototypeAndGetClass(
            lendsQname, lendsName, objlit);
        if (rawType == null) {
          return;
        }
        for (Node prop : objlit.children()) {
          String pname =  NodeUtil.getObjectLitKeyName(prop);
          mayAddPropToPrototype(rawType, pname, prop, prop.getFirstChild());
        }
      }
    }

    void processLendsToNamespace(
        QualifiedName lendsQname, String lendsName, Node objlit) {
      RawNominalType rawType = currentScope.getNominalType(lendsQname);
      if (rawType != null && rawType.isInterface()) {
        warnings.add(JSError.make(objlit, LENDS_ON_BAD_TYPE, lendsName));
        return;
      }
      Namespace borrowerNamespace = currentScope.getNamespace(lendsQname);
      for (Node prop : objlit.children()) {
        String pname = NodeUtil.getObjectLitKeyName(prop);
        JSType propDeclType = declaredObjLitProps.get(prop);
        if (propDeclType != null) {
          borrowerNamespace.addProperty(pname, prop, propDeclType, false);
        } else {
          JSType t = simpleInferExprType(prop.getFirstChild());
          if (t == null) {
            t = JSType.UNKNOWN;
          }
          borrowerNamespace.addProperty(pname, prop, t, false);
        }
      }
    }

    RawNominalType checkValidLendsToPrototypeAndGetClass(
        QualifiedName lendsQname, String lendsName, Node objlit) {
      if (!lendsQname.getRightmostName().equals("prototype")) {
        warnings.add(JSError.make(objlit, LENDS_ON_BAD_TYPE, lendsName));
        return null;
      }
      QualifiedName recv = lendsQname.getAllButRightmost();
      RawNominalType rawType = currentScope.getNominalType(recv);
      if (rawType == null || rawType.isInterface()) {
        warnings.add(JSError.make(objlit, LENDS_ON_BAD_TYPE, lendsName));
      }
      return rawType;
    }

    @Override
    public void visit(NodeTraversal t, Node n, Node parent) {
      switch (n.getType()) {
        case Token.FUNCTION:
          Node grandparent = parent.getParent();
          if (grandparent == null ||
              !isPrototypePropertyDeclaration(grandparent)) {
            Scope s = visitFunctionLate(n, null);
            Node name = NodeUtil.getFunctionNameNode(n);
            if (name != null && name.isGetProp() && name.isQualifiedName()) {
              QualifiedName recv = QualifiedName.fromNode(name.getFirstChild());
              String pname = name.getLastChild().getString();
              if (currentScope.isNamespace(recv)) {
                Namespace ns = currentScope.getNamespace(recv);
                ns.addScope(new QualifiedName(pname), s);
              }
            }
          }
          break;

        case Token.NAME: {
          String name = n.getString();
          if (name == null || "undefined".equals(name) || parent.isFunction()) {
            return;
          }
          // TODO(dimvar): Handle local scopes introduced by catch properly,
          // after we decide what to do with variables in general, eg, will we
          // use unique numeric ids?
          if (parent.isVar() || parent.isCatch()) {
            if (NodeUtil.isNamespaceDecl(n) || NodeUtil.isTypedefDecl(n)
                || NodeUtil.isEnumDecl(n)) {
                if (!currentScope.isDefinedLocally(name, false)) {
                  // Malformed enum or typedef
                  currentScope.addLocal(
                      name, JSType.UNKNOWN, false, n.isFromExterns());
                }
              break;
            }
            Node initializer = n.getFirstChild();
            if (initializer != null && initializer.isFunction()) {
              break;
            } else if (currentScope.isDefinedLocally(name, false)) {
              // warnings.add(JSError.make(
              //     n, VariableReferenceCheck.REDECLARED_VARIABLE, name));
              break;
            } else {
              // for (Node useBeforeDeclNode : undeclaredVars.get(name)) {
              //   warnings.add(JSError.make(useBeforeDeclNode,
              //       VariableReferenceCheck.EARLY_REFERENCE, name));
              // }
              // undeclaredVars.removeAll(name);
              if (parent.isCatch()) {
                currentScope.addLocal(name, JSType.UNKNOWN, false, false);
              } else {
                boolean isConst = isConst(parent);
                JSType declType = getVarTypeFromAnnotation(n);
                if (isConst && !mayWarnAboutNoInit(n) && declType == null) {
                  declType = inferConstTypeFromRhs(n);
                }
                currentScope.addLocal(name, declType, isConst, n.isFromExterns());
              }
            }
          } else if (currentScope.isOuterVarEarly(name)) {
            currentScope.addOuterVar(name);
          } else if (// Typedef variables can't be referenced in the source.
              currentScope.getTypedef(name) != null ||
              !name.equals(currentScope.getName()) &&
              !currentScope.isDefinedLocally(name, false)) {
            // undeclaredVars.put(name, n);
          }
          break;
        }

        case Token.GETPROP:
          if (parent.isExprResult()) {
            visitPropertyDeclaration(n);
          }
          break;

        case Token.ASSIGN: {
          Node lvalue = n.getFirstChild();
          if (lvalue.isGetProp() && parent.isExprResult()) {
            visitPropertyDeclaration(lvalue);
          }
          break;
        }

        case Token.CAST:
          castTypes.put(n,
              getDeclaredTypeOfNode(n.getJSDocInfo(), currentScope));
          break;

        case Token.OBJECTLIT: {
          JSDocInfo jsdoc = n.getJSDocInfo();
          if (jsdoc != null && jsdoc.getLendsName() != null) {
            lendsObjlits.add(n);
          }
          Node maybeLvalue = parent.isAssign() ? parent.getFirstChild() : parent;
          if (NodeUtil.isNamespaceDecl(maybeLvalue)
              && currentScope.isNamespace(maybeLvalue)) {
            for (Node prop : n.children()) {
              visitNamespacePropertyDeclaration(
                  prop, maybeLvalue, prop.getString());
            }
          } else if (!NodeUtil.isPrototypeAssignment(maybeLvalue)) {
            for (Node prop : n.children()) {
              if (prop.getJSDocInfo() != null) {
                declaredObjLitProps.put(prop,
                    getDeclaredTypeOfNode(
                        prop.getJSDocInfo(), currentScope));
              }
              if (isAnnotatedAsConst(prop)) {
                warnings.add(JSError.make(prop, MISPLACED_CONST_ANNOTATION));
              }
            }
          }
          break;
        }
      }
    }

    private void visitPropertyDeclaration(Node getProp) {
      // Class property
      if (isClassPropAccess(getProp, currentScope)) {
        if (isAnnotatedAsConst(getProp) && currentScope.isPrototypeMethod()) {
          warnings.add(JSError.make(getProp, MISPLACED_CONST_ANNOTATION));
        }
        visitClassPropertyDeclaration(getProp);
      }
      // Prototype property
      else if (isPropertyDeclaration(getProp) && isPrototypeProperty(getProp)) {
        visitPrototypePropertyDeclaration(getProp);
      }
      // Direct assignment to the prototype
      else if (isPropertyDeclaration(getProp) && NodeUtil.isPrototypeAssignment(getProp)) {
        visitPrototypeAssignment(getProp);
      }
      // "Static" property on constructor
      else if (isPropertyDeclaration(getProp) &&
          isStaticCtorProp(getProp, currentScope)) {
        visitConstructorPropertyDeclaration(getProp);
      }
      // Namespace property
      else if (isPropertyDeclaration(getProp) &&
          currentScope.isNamespace(getProp.getFirstChild())) {
        visitNamespacePropertyDeclaration(getProp);
      }
      // Other property
      else {
        visitOtherPropertyDeclaration(getProp);
      }
    }

    private boolean isStaticCtorProp(Node getProp, Scope s) {
      Preconditions.checkArgument(getProp.isGetProp());
      if (!getProp.isQualifiedName()) {
        return false;
      }
      Node receiverObj = getProp.getFirstChild();
      if (!s.isLocalFunDef(receiverObj.getQualifiedName())) {
        return false;
      }
      return null != currentScope.getNominalType(
          QualifiedName.fromNode(receiverObj));
    }

    /** Returns the newly created scope for this function */
    private Scope visitFunctionLate(Node fn, RawNominalType ownerType) {
      Preconditions.checkArgument(fn.isFunction());
      // String fnName = NodeUtil.getFunctionName(fn);
      // if (fnName != null && !fnName.contains(".")) {
      //   undeclaredVars.removeAll(fnName);
      // }
      String internalName = getFunInternalName(fn);
      Scope fnScope = currentScope.getScope(internalName);
      updateFnScope(fnScope, ownerType);
      return fnScope;
    }

    private void visitPrototypePropertyDeclaration(Node getProp) {
      Preconditions.checkArgument(getProp.isGetProp());
      Node parent = getProp.getParent();
      Node initializer = parent.isAssign() ? parent.getLastChild() : null;
      Node ctorNameNode = NodeUtil.getPrototypeClassName(getProp);
      QualifiedName ctorQname = QualifiedName.fromNode(ctorNameNode);
      RawNominalType rawType = currentScope.getNominalType(ctorQname);

      if (rawType == null) {
        if (initializer != null && initializer.isFunction()) {
          visitFunctionLate(initializer, null);
        }
        // We don't look at assignments to prototypes of non-constructors.
        return;
      }
      if (initializer != null && initializer.isFunction()) {
        parent.putBooleanProp(Node.ANALYZED_DURING_GTI, true);
      }
      // We only add properties to the prototype of a class if the
      // property creations are in the same scope as the constructor
      // TODO(blickly): Rethink this
      if (!currentScope.isDefined(ctorNameNode)) {
        warnings.add(JSError.make(getProp, CTOR_IN_DIFFERENT_SCOPE));
        if (initializer != null && initializer.isFunction()) {
          visitFunctionLate(initializer, rawType);
        }
        return;
      }
      mayWarnAboutInterfacePropInit(rawType, initializer);
      String pname = NodeUtil.getPrototypePropertyName(getProp);
      mayAddPropToPrototype(rawType, pname, getProp, initializer);
    }

    private void mayWarnAboutInterfacePropInit(RawNominalType rawType, Node initializer) {
      if (rawType.isInterface() && initializer != null) {
        String abstractMethodName = convention.getAbstractMethodName();
        if (initializer.isFunction()
            && !NodeUtil.isEmptyFunctionExpression(initializer)) {
          warnings.add(JSError.make(initializer, TypeCheck.INTERFACE_METHOD_NOT_EMPTY));
        } else if (!initializer.isFunction()
            && !initializer.matchesQualifiedName(abstractMethodName)) {
          warnings.add(JSError.make(initializer, INVALID_INTERFACE_PROP_INITIALIZER));
        }
      }
    }

    private void visitPrototypeAssignment(Node getProp) {
      Preconditions.checkArgument(getProp.isGetProp());
      Node ctorNameNode = NodeUtil.getPrototypeClassName(getProp);
      QualifiedName ctorQname = QualifiedName.fromNode(ctorNameNode);
      RawNominalType rawType = currentScope.getNominalType(ctorQname);
      if (rawType == null) {
        return;
      }
      getProp.putBooleanProp(Node.ANALYZED_DURING_GTI, true);
      for (Node objLitChild : getProp.getParent().getLastChild().children()) {
        mayAddPropToPrototype(rawType, objLitChild.getString(), objLitChild,
            objLitChild.getLastChild());
      }
    }

    private void visitConstructorPropertyDeclaration(Node getProp) {
      Preconditions.checkArgument(getProp.isGetProp());
      // Named types have already been crawled in CollectNamedTypes
      if (isNamedType(getProp)) {
        return;
      }
      String ctorName = getProp.getFirstChild().getQualifiedName();
      QualifiedName ctorQname = QualifiedName.fromNode(getProp.getFirstChild());
      Preconditions.checkState(currentScope.isLocalFunDef(ctorName));
      RawNominalType classType = currentScope.getNominalType(ctorQname);
      String pname = getProp.getLastChild().getString();
      JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(getProp);
      JSType propDeclType = getTypeAtPropDeclNode(getProp, jsdoc);
      boolean isConst = isConst(getProp);
      if (propDeclType != null || isConst) {
        JSType previousPropType = classType.getCtorPropDeclaredType(pname);
        if (classType.hasCtorProp(pname) &&
            previousPropType != null &&
            !suppressDupPropWarning(jsdoc, propDeclType, previousPropType)) {
          warnings.add(JSError.make(getProp, REDECLARED_PROPERTY,
                  pname, classType.toString()));
          return;
        }
        if (isConst && !mayWarnAboutNoInit(getProp) && propDeclType == null) {
          propDeclType = inferConstTypeFromRhs(getProp);
        }
        classType.addCtorProperty(pname, getProp, propDeclType, isConst);
        getProp.putBooleanProp(Node.ANALYZED_DURING_GTI, true);
        if (isConst) {
          getProp.putBooleanProp(Node.CONSTANT_PROPERTY_DEF, true);
        }
      } else {
        classType.addUndeclaredCtorProperty(pname, getProp);
      }
    }

    private void visitNamespacePropertyDeclaration(Node getProp) {
      Preconditions.checkArgument(getProp.isGetProp());
      // Named types have already been crawled in CollectNamedTypes
      if (isNamedType(getProp)) {
        return;
      }
      Node recv = getProp.getFirstChild();
      String pname = getProp.getLastChild().getString();
      visitNamespacePropertyDeclaration(getProp, recv, pname);
    }

    private void visitNamespacePropertyDeclaration(
        Node declNode, Node recv, String pname) {
      Preconditions.checkArgument(
          declNode.isGetProp() || declNode.isStringKey());
      Preconditions.checkArgument(currentScope.isNamespace(recv));
      EnumType et = currentScope.getEnum(QualifiedName.fromNode(recv));
      // If there is a reassignment to one of the enum's members, don't consider
      // that a definition of a new property.
      if (et != null && et.enumLiteralHasKey(pname)) {
        return;
      }
      Namespace ns = currentScope.getNamespace(QualifiedName.fromNode(recv));
      JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(declNode);
      JSType propDeclType = getTypeAtPropDeclNode(declNode, jsdoc);
      boolean isConst = isConst(declNode);
      if (propDeclType != null || isConst) {
        JSType previousPropType = ns.getPropDeclaredType(pname);
        if (ns.hasProp(pname) &&
            previousPropType != null &&
            !suppressDupPropWarning(jsdoc, propDeclType, previousPropType)) {
          warnings.add(JSError.make(declNode, REDECLARED_PROPERTY,
                  pname, ns.toString()));
          return;
        }
        if (isConst && !mayWarnAboutNoInit(declNode) && propDeclType == null) {
          propDeclType = inferConstTypeFromRhs(declNode);
        }
        ns.addProperty(pname, declNode, propDeclType, isConst);
        declNode.putBooleanProp(Node.ANALYZED_DURING_GTI, true);
        if (declNode.isGetProp() && isConst) {
          declNode.putBooleanProp(Node.CONSTANT_PROPERTY_DEF, true);
        }
      } else {
        // Try to infer the prop type, but don't say that the prop is declared.
        Node initializer = NodeUtil.getInitializer(declNode);
        JSType t = initializer == null
            ? null : simpleInferExprType(initializer);
        if (t == null) {
          t = JSType.UNKNOWN;
        }
        ns.addUndeclaredProperty(pname, declNode, t, false);
      }
    }

    private void visitClassPropertyDeclaration(Node getProp) {
      Preconditions.checkArgument(getProp.isGetProp());
      NominalType thisType = currentScope.getDeclaredFunctionType().getThisType();
      if (thisType == null) {
        // This will get caught in NewTypeInference
        return;
      }
      RawNominalType rawNominalType = thisType.getRawNominalType();
      String pname = getProp.getLastChild().getString();
      // TODO(blickly): Support @param, @return style fun declarations here.
      JSType declType = getDeclaredTypeOfNode(
          NodeUtil.getBestJSDocInfo(getProp), currentScope);
      boolean isConst = isConst(getProp);
      if (declType != null || isConst) {
        mayWarnAboutExistingProp(rawNominalType, pname, getProp, declType);
        // Intentionally, we keep going even if we warned for redeclared prop.
        // The reason is that if a prop is defined on a class and on its proto
        // with conflicting types, we prefer the type of the class.
        if (isConst && !mayWarnAboutNoInit(getProp) && declType == null) {
          declType = inferConstTypeFromRhs(getProp);
        }
        if (mayAddPropToType(getProp, rawNominalType)) {
          rawNominalType.addClassProperty(pname, getProp, declType, isConst);
        }
        if (isConst) {
          getProp.putBooleanProp(Node.CONSTANT_PROPERTY_DEF, true);
        }
      } else if (mayAddPropToType(getProp, rawNominalType)) {
        rawNominalType.addUndeclaredClassProperty(pname, getProp);
      }
      propertyDefs.put(rawNominalType, pname,
          new PropertyDef(getProp, null, null));
    }

    private void visitOtherPropertyDeclaration(Node getProp) {
      Preconditions.checkArgument(getProp.isGetProp());
      if (isAnnotatedAsConst(getProp)) {
        warnings.add(JSError.make(getProp, MISPLACED_CONST_ANNOTATION));
      }
      RawNominalType rawType = getRawTypeFromJSType(
          simpleInferExprType(getProp.getFirstChild()));
      if (rawType == null) {
        return;
      }
      String pname = getProp.getLastChild().getString();
      JSType declType = getDeclaredTypeOfNode(
          NodeUtil.getBestJSDocInfo(getProp), currentScope);
      if (declType != null) {
        declType = declType.substituteGenericsWithUnknown();
        if (mayWarnAboutExistingProp(rawType, pname, getProp, declType)) {
          return;
        }
        rawType.addPropertyWhichMayNotBeOnAllInstances(pname, declType);
      } else if (!rawType.mayHaveProp(pname)) {
        rawType.addPropertyWhichMayNotBeOnAllInstances(pname, null);
      }
    }

    private RawNominalType getRawTypeFromJSType(JSType t) {
      if (t == null) {
        return null;
      }
      NominalType nt = t.getNominalTypeIfSingletonObj();
      return nt == null ? null : nt.getRawNominalType();
    }

    private JSType getTypeAtPropDeclNode(Node declNode, JSDocInfo jsdoc) {
      Preconditions.checkArgument(!currentScope.isNamespace(declNode));
      Node initializer = NodeUtil.getInitializer(declNode);
      if (initializer != null && initializer.isFunction()) {
        return commonTypes.fromFunctionType(
            currentScope.getScope(getFunInternalName(initializer))
            .getDeclaredFunctionType().toFunctionType());
      }
      return getDeclaredTypeOfNode(jsdoc, currentScope);
    }

    boolean mayWarnAboutNoInit(Node constExpr) {
      if (constExpr.isFromExterns()) {
        return false;
      }
      Node initializer = NodeUtil.getInitializer(constExpr);
      if (initializer == null) {
        warnings.add(JSError.make(constExpr, CONST_WITHOUT_INITIALIZER));
        return true;
      }
      return false;
    }

    // If a @const doesn't have a declared type, we use the initializer to
    // infer a type.
    // When we cannot infer the type of the initializer, we warn.
    // This way, people do not need to remember the cases where the compiler
    // can infer the type of a constant; we tell them if we cannot infer it.
    // This function is called only when the @const has no declared type.
    private JSType inferConstTypeFromRhs(Node constExpr) {
      if (constExpr.isFromExterns()) {
        warnings.add(JSError.make(constExpr, COULD_NOT_INFER_CONST_TYPE));
        return null;
      }
      Node rhs = NodeUtil.getInitializer(constExpr);
      JSType rhsType = simpleInferExprType(rhs);
      if (rhsType == null || rhsType.isUnknown()) {
        warnings.add(JSError.make(constExpr, COULD_NOT_INFER_CONST_TYPE));
        return null;
      }
      return rhsType;
    }

    private FunctionType simpleInferFunctionType(Node n) {
      if (n.isQualifiedName()) {
        Declaration decl = currentScope.getDeclaration(QualifiedName.fromNode(n), false);
        if (decl != null && decl.getFunctionScope() != null) {
          DeclaredFunctionType funType = decl.getFunctionScope().getDeclaredFunctionType();
          if (funType != null) {
            return funType.toFunctionType();
          }
        }
      }
      return null;
    }

    private JSType simpleInferExprType(Node n) {
      switch (n.getType()) {
        case Token.REGEXP:
          return commonTypes.getRegexpType();
        case Token.ARRAYLIT: {
          if (!n.hasChildren()) {
            return null;
          }
          Node child = n.getFirstChild();
          JSType arrayType = simpleInferExprType(child);
          if (arrayType == null) {
            return null;
          }
          while (null != (child = child.getNext())) {
            if (!arrayType.equals(simpleInferExprType(child))) {
              return null;
            }
          }
          return commonTypes.getArrayInstance(arrayType);
        }
        case Token.TRUE:
          return JSType.TRUE_TYPE;
        case Token.FALSE:
          return JSType.FALSE_TYPE;
        case Token.THIS:
          return this.currentScope.getDeclaredTypeOf("this");
        case Token.NAME: {
          String varName = n.getString();
          if (varName.equals("undefined")) {
            return JSType.UNDEFINED;
          } else if (this.currentScope.isNamespace(varName)) {
            // Namespaces (literals, enums, constructors) get populated during
            // ProcessScope, so it's NOT safe to convert them to jstypes until
            // after ProcessScope is done. So, we don't try to do sth clever
            // here to find the type of a namespace property.
            // However, in the GETPROP case, we special-case for enum
            // properties, because enums get resolved right after
            // CollectNamedTypes, so we know the enumerated type.
            // (But we still don't know the types of enum properties outside
            // the object-literal declaration.)
            return null;
          }
          return this.currentScope.getDeclaredTypeOf(varName);
        }
        case Token.OBJECTLIT: {
          JSType objLitType = JSType.TOP_OBJECT;
          for (Node prop : n.children()) {
            JSType propType = simpleInferExprType(prop.getFirstChild());
            if (propType == null) {
              return null;
            }
            objLitType = objLitType.withProperty(
                new QualifiedName(NodeUtil.getObjectLitKeyName(prop)),
                propType);
          }
          return objLitType;
        }
        case Token.GETPROP:
          Node recv = n.getFirstChild();
          if (recv.isQualifiedName()) {
            EnumType et = this.currentScope.getEnum(QualifiedName.fromNode(recv));
            if (et != null
                && et.enumLiteralHasKey(n.getLastChild().getString())) {
              return et.getEnumeratedType();
            }
            if (this.currentScope.isNamespace(recv)) {
              return null;
            }
            JSType recvType = simpleInferExprType(recv);
            QualifiedName qname =
                new QualifiedName(n.getLastChild().getString());
            if (recvType != null && recvType.mayHaveProp(qname)) {
              return recvType.getProp(qname);
            }
          }
          return null;
        case Token.COMMA:
        case Token.ASSIGN:
          return simpleInferExprType(n.getLastChild());
        case Token.CALL:
        case Token.NEW: {
          Node callee = n.getFirstChild();
          // We special-case the function goog.getMsg, which is used by the
          // compiler for i18n.
          if (callee.matchesQualifiedName("goog.getMsg")) {
            return JSType.STRING;
          }
          FunctionType funType = simpleInferFunctionType(callee);
          if (funType == null) {
            return null;
          }
          if (funType.isGeneric()) {
            ImmutableList.Builder<JSType> argTypes = ImmutableList.builder();
            for (Node argNode = n.getFirstChild().getNext();
                 argNode != null;
                 argNode = argNode.getNext()) {
              JSType t = simpleInferExprType(argNode);
              if (t == null) {
                return null;
              }
              argTypes.add(t);
            }
            funType = funType
                .instantiateGenericsFromArgumentTypes(argTypes.build());
            if (funType == null) {
              return null;
            }
          }
          JSType retType =
              n.isNew() ? funType.getThisType() : funType.getReturnType();
          return retType;
        }
        default:
          switch (NodeUtil.getKnownValueType(n)) {
            case NULL:
              return JSType.NULL;
            case VOID:
              return JSType.UNDEFINED;
            case NUMBER:
              return JSType.NUMBER;
            case STRING:
              return JSType.STRING;
            case BOOLEAN:
              return JSType.BOOLEAN;
            case UNDETERMINED:
            default:
              return null;
          }
      }
    }

    private boolean mayAddPropToType(Node getProp, RawNominalType rawType) {
      if (!rawType.isStruct()) {
        return true;
      }
      Node parent = getProp.getParent();
      return (parent.isAssign() && getProp == parent.getFirstChild()
          || parent.isExprResult())
          && currentScope.isConstructor();
    }

    private boolean mayWarnAboutExistingProp(RawNominalType classType,
        String pname, Node propCreationNode, JSType typeInJsdoc) {
      JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(propCreationNode);
      JSType previousPropType = classType.getInstancePropDeclaredType(pname);
      if (classType.mayHaveOwnProp(pname) &&
          previousPropType != null &&
          !suppressDupPropWarning(jsdoc, typeInJsdoc, previousPropType)) {
        warnings.add(JSError.make(propCreationNode, REDECLARED_PROPERTY,
                pname, classType.toString()));
        return true;
      }
      return false;
    }

    // All suppressions happen in SuppressDocWarningsGuard.java, except one.
    // At a duplicate property definition annotated with @suppress {duplicate},
    // if the type in the jsdoc is the same as the already declared type,
    // then don't warn.
    // Type info is required to enforce this, so the current type inference
    // does it in TypeValidator.java, and we do it here.
    // This is a hacky suppression.
    // 1) Why is it just specific to "duplicate" and to properties?
    // 2) The docs say that it's only allowed in the top level, but the code
    //    allows it in all scopes.
    //    https://github.com/google/closure-compiler/wiki/Warnings#suppress-tags
    // For now, we implement it b/c it exists in the current type inference.
    // But I wouldn't mind if we stopped supporting it.
    private boolean suppressDupPropWarning(
        JSDocInfo propCreationJsdoc, JSType typeInJsdoc, JSType previousType) {
      if (propCreationJsdoc == null ||
          !propCreationJsdoc.getSuppressions().contains("duplicate")) {
        return false;
      }
      return typeInJsdoc != null && previousType != null &&
          typeInJsdoc.equals(previousType);
    }

    private DeclaredFunctionType computeFnDeclaredType(
        JSDocInfo fnDoc, String functionName, Node declNode,
        RawNominalType ownerType, Scope parentScope) {
      Preconditions.checkArgument(declNode.isFunction() || declNode.isGetProp());

      // For an unannotated function, check if we can grab a type signature for
      // it from the surrounding code where it appears.
      if (fnDoc == null && !NodeUtil.functionHasInlineJsdocs(declNode)) {
        DeclaredFunctionType t = getDeclaredFunctionTypeFromContext(
            functionName, declNode, parentScope);
        if (t != null) {
          return t;
        }
      }
      // TODO(dimvar): warn if multiple jsdocs for a fun
      RawNominalType ctorType =
          declNode.isFunction() ? nominaltypesByNode.get(declNode) : null;
      DeclaredFunctionType result = typeParser.getFunctionType(
          fnDoc, functionName, declNode, ctorType, ownerType, parentScope);
      if (ctorType != null) {
        ctorType.setCtorFunction(
            result.toFunctionType(), commonTypes.getFunctionType());
      }
      return result;
    }

    // We only return a non-null result if the arity of declNode matches the
    // arity we get from declaredTypeAsJSType.
    private DeclaredFunctionType computeFnDeclaredTypeFromCallee(
        Node declNode, JSType declaredTypeAsJSType) {
      Preconditions.checkArgument(declNode.isFunction());
      Preconditions.checkArgument(declNode.getParent().isCall());
      Preconditions.checkNotNull(declaredTypeAsJSType);

      FunctionType funType = declaredTypeAsJSType.getFunType();
      if (funType == null) {
        return null;
      }
      DeclaredFunctionType declType = funType.toDeclaredFunctionType();
      if (declType == null) {
        return null;
      }
      int numFormals = declNode.getChildAtIndex(1).getChildCount();
      int reqArity = declType.getRequiredArity();
      int optArity = declType.getOptionalArity();
      boolean hasRestFormals = declType.hasRestFormals();
      if (reqArity == optArity && !hasRestFormals) {
        return numFormals == reqArity ? declType : null;
      }
      if (numFormals == optArity && !hasRestFormals
          || numFormals == (optArity + 1) && hasRestFormals) {
        return declType;
      }
      return null;
    }

    // Returns null if it can't find a suitable type in the context
    private DeclaredFunctionType getDeclaredFunctionTypeFromContext(
        String functionName, Node declNode, Scope parentScope) {
      Node parent = declNode.getParent();
      Node maybeBind = parent.isCall() ? parent.getFirstChild() : parent;

      // The function literal is used with .bind or goog.bind
      if (NodeUtil.isFunctionBind(maybeBind) && !NodeUtil.isGoogPartial(maybeBind)) {
        Node call = maybeBind.getParent();
        Bind bindComponents = convention.describeFunctionBind(call, true, false);
        JSType recvType = simpleInferExprType(bindComponents.thisValue);
        if (recvType == null) {
          return null;
        }
        // Use typeParser for the formals, and only add the receiver type here.
        DeclaredFunctionType allButRecvType = typeParser.getFunctionType(
            null, functionName, declNode, null, null, parentScope);
        DeclaredFunctionType onlyHasRecvType = (new FunctionTypeBuilder())
            .addReceiverType(recvType.getNominalTypeIfSingletonObj())
            .buildDeclaration();
        // Using withTypeInfoFromSuper is a hack to add the receiver type.
        return onlyHasRecvType.withTypeInfoFromSuper(allButRecvType, true);
      }

      // The function literal is an argument at a call
      if (parent.isCall() && declNode != parent.getFirstChild()) {
        DeclaredFunctionType calleeDeclType = getDeclaredFunctionTypeOfCalleeIfAny(
            parent.getFirstChild(), parentScope);
        if (calleeDeclType != null && !calleeDeclType.isGeneric()) {
          int index = parent.getIndexOfChild(declNode) - 1;
          JSType declTypeFromCallee = calleeDeclType.getFormalType(index);
          if (declTypeFromCallee != null) {
            DeclaredFunctionType t =
                computeFnDeclaredTypeFromCallee(declNode, declTypeFromCallee);
            if (t != null) {
              return t;
            }
          }
        }
      }

      return null;
    }

    /**
     * Compute the declared type for a given scope.
     */
    private void updateFnScope(Scope fnScope, RawNominalType ownerType) {
      Node fn = fnScope.getRoot();
      Preconditions.checkState(fn.isFunction());
      JSDocInfo fnDoc = NodeUtil.getBestJSDocInfo(fn);
      String functionName = getFunInternalName(fn);
      DeclaredFunctionType declFunType = computeFnDeclaredType(
        fnDoc, functionName, fn, ownerType, currentScope);
      fnScope.setDeclaredType(declFunType);
    }

    private JSType getVarTypeFromAnnotation(Node nameNode) {
      Preconditions.checkArgument(nameNode.getParent().isVar());
      Node varNode = nameNode.getParent();
      JSType varType =
          getDeclaredTypeOfNode(varNode.getJSDocInfo(), currentScope);
      if (varNode.getChildCount() > 1 && varType != null) {
        warnings.add(JSError.make(varNode, TypeCheck.MULTIPLE_VAR_DEF));
      }
      String varName = nameNode.getString();
      JSType nameNodeType =
          getDeclaredTypeOfNode(nameNode.getJSDocInfo(), currentScope);
      if (nameNodeType != null) {
        if (varType != null) {
          warnings.add(JSError.make(nameNode, DUPLICATE_JSDOC, varName));
        }
        return nameNodeType;
      } else {
        return varType;
      }
    }

    /**
     * Called for the usual style of prototype-property definitions,
     * but also for @lends and for direct assignments of object literals to prototypes.
     */
    private void mayAddPropToPrototype(
        RawNominalType rawType, String pname, Node defSite, Node initializer) {
      Scope methodScope;
      DeclaredFunctionType methodType;
      JSType propDeclType;

      // Find the declared type of the property.
      if (initializer != null && initializer.isFunction()) {
        // TODO(dimvar): we must do this for any function "defined" as the rhs
        // of an assignment to a property, not just when the property is a
        // prototype property.
        methodScope = visitFunctionLate(initializer, rawType);
        methodType = methodScope.getDeclaredFunctionType();
        propDeclType = commonTypes.fromFunctionType(methodType.toFunctionType());
      } else {
        JSDocInfo jsdoc = NodeUtil.getBestJSDocInfo(defSite);
        if (jsdoc != null && jsdoc.containsFunctionDeclaration()) {
          // We're parsing a function declaration without a function initializer
          methodScope = null;
          methodType = computeFnDeclaredType(
              jsdoc, pname, defSite, rawType, currentScope);
          propDeclType = commonTypes.fromFunctionType(methodType.toFunctionType());
        } else if (jsdoc != null && jsdoc.hasType()) {
          // We are parsing a non-function prototype property
          methodScope = null;
          methodType = null;
          propDeclType = typeParser.getDeclaredTypeOfNode(jsdoc, rawType, currentScope);
        } else {
          methodScope = null;
          methodType = null;
          propDeclType = null;
        }
      }
      propertyDefs.put(rawType, pname, new PropertyDef(defSite, methodType, methodScope));

      // Add the property to the class with the appropriate type.
      boolean isConst = isConst(defSite);
      if (propDeclType != null || isConst) {
        if (mayWarnAboutExistingProp(rawType, pname, defSite, propDeclType)) {
          return;
        }
        if (defSite.isGetProp() && propDeclType == null
            && isConst && !mayWarnAboutNoInit(defSite)) {
          propDeclType = inferConstTypeFromRhs(defSite);
        }
        rawType.addProtoProperty(pname, defSite, propDeclType, isConst);
        if (defSite.isGetProp()) { // Don't bother saving for @lends
          defSite.putBooleanProp(Node.ANALYZED_DURING_GTI, true);
          if (isConst) {
            defSite.putBooleanProp(Node.CONSTANT_PROPERTY_DEF, true);
          }
        }
      } else {
        rawType.addUndeclaredProtoProperty(pname, defSite);
      }
    }

    private boolean isNamedType(Node getProp) {
      return currentScope.isNamespace(getProp)
          || NodeUtil.isTypedefDecl(getProp);
    }
  }

  private JSType getDeclaredTypeOfNode(JSDocInfo jsdoc, Scope s) {
    return typeParser.getDeclaredTypeOfNode(jsdoc, null, s);
  }

  private DeclaredFunctionType getDeclaredFunctionTypeOfCalleeIfAny(
      Node fn, Scope currentScope) {
    Preconditions.checkArgument(fn.getParent().isCall());
    if (fn.isThis() || !fn.isFunction() && !fn.isQualifiedName()) {
      return null;
    }
    if (fn.isFunction()) {
      return currentScope.getScope(getFunInternalName(fn)).getDeclaredFunctionType();
    }
    Preconditions.checkState(fn.isQualifiedName());
    Declaration decl = currentScope.getDeclaration(QualifiedName.fromNode(fn), false);
    if (decl == null) {
      return null;
    }
    if (decl.getFunctionScope() != null) {
      return decl.getFunctionScope().getDeclaredFunctionType();
    }
    if (decl.getTypeOfSimpleDecl() != null) {
      FunctionType funType = decl.getTypeOfSimpleDecl().getFunType();
      if (funType != null) {
        return funType.toDeclaredFunctionType();
      }
    }
    return null;
  }

  private static boolean isClassPropAccess(Node n, Scope s) {
    return n.isGetProp() && n.getFirstChild().isThis() &&
        (s.isConstructor() || s.isPrototypeMethod());
  }

  // TODO(blickly): Move to NodeUtil
  private static boolean isPropertyDeclaration(Node getProp) {
    Preconditions.checkArgument(getProp.isGetProp());
    Node parent = getProp.getParent();
    return parent.isExprResult() ||
        (parent.isAssign() && parent.getParent().isExprResult());
  }

  // In contrast to the NodeUtil method, here we only accept properties directly
  // on the prototype, and return false for names such as Foo.prototype.bar.baz
  private static boolean isPrototypeProperty(Node getProp) {
    if (!getProp.isGetProp()) {
      return false;
    }
    Node recv = getProp.getFirstChild();
    return recv.isGetProp()
        && recv.getLastChild().getString().equals("prototype");
  }

  private static boolean isPrototypePropertyDeclaration(Node n) {
    return NodeUtil.isExprAssign(n)
        && isPrototypeProperty(n.getFirstChild().getFirstChild());
  }

  private static boolean isAnnotatedAsConst(Node defSite) {
    return NodeUtil.hasConstAnnotation(defSite)
        && !NodeUtil.getBestJSDocInfo(defSite).isConstructor();
  }

  private static Node fromDefsiteToName(Node defSite) {
    if (defSite.isVar()) {
      return defSite.getFirstChild();
    }
    if (defSite.isGetProp()) {
      return defSite.getLastChild();
    }
    if (defSite.isStringKey() || defSite.isGetterDef() || defSite.isSetterDef()) {
      return defSite;
    }
    throw new RuntimeException("Unknown defsite: "
        + Token.name(defSite.getType()));
  }

  private boolean isConst(Node defSite) {
    return isAnnotatedAsConst(defSite)
        || NodeUtil.isConstantByConvention(
            this.convention, fromDefsiteToName(defSite));
  }

  private static class PropertyDef {
    final Node defSite; // The getProp/objectLitKey of the property definition
    DeclaredFunctionType methodType; // null for non-method property decls
    final Scope methodScope; // null for decls without function on the RHS

    PropertyDef(
        Node defSite, DeclaredFunctionType methodType, Scope methodScope) {
      Preconditions.checkNotNull(defSite);
      Preconditions.checkArgument(
          defSite.isGetProp() || NodeUtil.isObjectLitKey(defSite));
      this.defSite = defSite;
      this.methodType = methodType;
      this.methodScope = methodScope;
    }

    void updateMethodType(DeclaredFunctionType updatedType) {
      this.methodType = updatedType;
      if (this.methodScope != null) {
        this.methodScope.setDeclaredType(updatedType);
      }
    }
  }

  static class Scope implements DeclaredTypeRegistry {
    private final Scope parent;
    private final Node root;
    // Name on the function AST node; null for top scope & anonymous functions
    private final String name;
    private final JSTypes commonTypes;

    // A local w/out declared type is mapped to null, not to JSType.UNKNOWN.
    private final Map<String, JSType> locals = new LinkedHashMap<>();
    private final Map<String, JSType> externs;
    private final Set<String> constVars = new LinkedHashSet<>();
    private final List<String> formals;
    // outerVars are the variables that appear free in this scope
    // and are defined in an enclosing scope.
    private final Set<String> outerVars = new LinkedHashSet<>();
    private final Map<String, Scope> localFunDefs = new LinkedHashMap<>();
    private Set<String> unknownTypeNames = new LinkedHashSet<>();
    private Map<String, RawNominalType> localClassDefs = new LinkedHashMap<>();
    private Map<String, Typedef> localTypedefs = new LinkedHashMap<>();
    private Map<String, EnumType> localEnums = new LinkedHashMap<>();
    private Map<String, NamespaceLit> localNamespaces = new LinkedHashMap<>();
    // The set qualifiedEnums is used for enum resolution, and then discarded.
    private Set<EnumType> qualifiedEnums = new LinkedHashSet<>();

    // declaredType is null for top level, but never null for functions,
    // even those without jsdoc.
    // Any inferred parameters or return will be set to null individually.
    private DeclaredFunctionType declaredType;

    private Scope(
        Node root, Scope parent, List<String> formals, JSTypes commonTypes) {
      if (parent == null) {
        this.name = null;
        this.externs = new LinkedHashMap<>();
      } else {
        String nameOnAst = root.getFirstChild().getString();
        this.name = nameOnAst.isEmpty() ? null : nameOnAst;
        this.externs = ImmutableMap.of();
      }
      this.root = root;
      this.parent = parent;
      this.formals = formals;
      this.commonTypes = commonTypes;
    }

    Node getRoot() {
      return root;
    }

    private Node getBody() {
      Preconditions.checkArgument(root.isFunction());
      return NodeUtil.getFunctionBody(root);
    }

    /** Used only for error messages; null for top scope */
    String getReadableName() {
      // TODO(dimvar): don't return null for anonymous functions
      return isTopLevel() ? null : NodeUtil.getFunctionName(root);
    }

    String getName() {
      return name;
    }

    private void setDeclaredType(DeclaredFunctionType declaredType) {
      this.declaredType = declaredType;
      // In NTI, we set the type of a function node after we create the summary.
      // NTI doesn't analyze externs, so we set the type for extern functions here.
      if (this.root.isFromExterns()) {
        this.root.setTypeI(getCommonTypes().fromFunctionType(declaredType.toFunctionType()));
      }
    }

    public DeclaredFunctionType getDeclaredFunctionType() {
      return declaredType;
    }

    boolean isFunction() {
      return root.isFunction();
    }

    private boolean isTopLevel() {
      return parent == null;
    }

    private boolean isConstructor() {
      if (!root.isFunction()) {
        return false;
      }
      JSDocInfo fnDoc = NodeUtil.getBestJSDocInfo(root);
      return fnDoc != null && fnDoc.isConstructor();
    }

    private boolean isPrototypeMethod() {
      Preconditions.checkArgument(root != null);
      return NodeUtil.isPrototypeMethod(root);
    }

    private void addUnknownTypeNames(List<String> names) {
      Preconditions.checkState(this.isTopLevel());
      unknownTypeNames.addAll(names);
    }

    private void addLocalFunDef(String name, Scope scope) {
      Preconditions.checkArgument(!name.isEmpty());
      Preconditions.checkArgument(!name.contains("."));
      Preconditions.checkArgument(!isDefinedLocally(name, false));
      localFunDefs.put(name, scope);
    }

    boolean isFormalParam(String name) {
      return formals.contains(name);
    }

    boolean isLocalFunDef(String name) {
      return localFunDefs.containsKey(name);
    }

    // In other languages, type names and variable names are in distinct
    // namespaces and don't clash.
    // But because our typedefs and enums are var declarations, they are in the
    // same namespace as other variables.
    boolean isDefinedLocally(String name, boolean includeTypes) {
      Preconditions.checkNotNull(name);
      Preconditions.checkState(!name.contains("."));
      if (locals.containsKey(name) || formals.contains(name)
          || localFunDefs.containsKey(name) || "this".equals(name)
          || externs.containsKey(name)
          || localNamespaces.containsKey(name)
          || localTypedefs.containsKey(name)
          || localEnums.containsKey(name)) {
        return true;
      }
      if (includeTypes) {
        return unknownTypeNames.contains(name)
            || declaredType != null && declaredType.isTypeVariableDefinedLocally(name);
      }
      return false;
    }

    private boolean isDefined(Node qnameNode) {
      Preconditions.checkArgument(qnameNode.isQualifiedName());
      if (qnameNode.isName()) {
        return isDefinedLocally(qnameNode.getString(), false);
      } else if (qnameNode.isThis()) {
        return true;
      }
      QualifiedName qname = QualifiedName.fromNode(qnameNode);
      String leftmost = qname.getLeftmostName();
      if (isNamespace(leftmost)) {
        return getNamespace(leftmost).isDefined(qname.getAllButLeftmost());
      }
      return parent == null ? false : parent.isDefined(qnameNode);
    }

    private boolean isNamespace(Node expr) {
      if (expr.isName()) {
        return isNamespace(expr.getString());
      }
      if (!expr.isGetProp()) {
        return false;
      }
      return isNamespace(QualifiedName.fromNode(expr));
    }

    private boolean isNamespace(QualifiedName qname) {
      if (qname == null) {
        return false;
      }
      String leftmost = qname.getLeftmostName();
      return isNamespace(leftmost)
          && (qname.isIdentifier()
              || getNamespace(leftmost)
              .hasSubnamespace(qname.getAllButLeftmost()));
    }

    private boolean isNamespace(String name) {
      Preconditions.checkArgument(!name.contains("."));
      Declaration decl = getDeclaration(name, false);
      return decl != null && decl.getNamespace() != null;
    }

    private boolean isVisibleInScope(String name) {
      Preconditions.checkArgument(!name.contains("."));
      return isDefinedLocally(name, false) ||
          name.equals(this.name) ||
          (parent != null && parent.isVisibleInScope(name));
    }

    boolean isConstVar(String name) {
      Preconditions.checkArgument(!name.contains("."));
      Declaration decl = getDeclaration(name, false);
      return decl != null && decl.isConstant();
    }

    private boolean isOuterVarEarly(String name) {
      Preconditions.checkArgument(!name.contains("."));
      return !isDefinedLocally(name, false) &&
          parent != null && parent.isVisibleInScope(name);
    }

    boolean isUndeclaredFormal(String name) {
      Preconditions.checkArgument(!name.contains("."));
      return formals.contains(name) && getDeclaredTypeOf(name) == null;
    }

    List<String> getFormals() {
      return new ArrayList<>(formals);
    }

    Set<String> getOuterVars() {
      return new LinkedHashSet<>(outerVars);
    }

    Set<String> getLocalFunDefs() {
      return ImmutableSet.copyOf(localFunDefs.keySet());
    }

    boolean isOuterVar(String name) {
      return outerVars.contains(name);
    }

    boolean hasThis() {
      return isFunction() && getDeclaredFunctionType().getThisType() != null;
    }

    private RawNominalType getNominalType(QualifiedName qname) {
      Declaration decl = getDeclaration(qname, false);
      return decl == null ? null : decl.getNominal();
    }

    JSType getUnresolvedTypeByName(String name) {
      if (unknownTypeNames.contains(name)) {
        return JSType.UNKNOWN;
      }
      return null;
    }

    @Override
    public JSTypes getCommonTypes() {
      if (isTopLevel()) {
        return commonTypes;
      }
      return parent.getCommonTypes();
    }

    @Override
    public JSType getDeclaredTypeOf(String name) {
      Preconditions.checkArgument(!name.contains("."));
      if ("this".equals(name)) {
        if (!hasThis()) {
          return null;
        }
        return getDeclaredFunctionType().getThisType().getInstanceAsJSType();
      }
      Declaration decl = getLocalDeclaration(name, false);
      if (decl != null) {
        if (decl.getTypeOfSimpleDecl() != null) {
          Preconditions.checkState(!decl.getTypeOfSimpleDecl().isBottom(), "%s was bottom", name);
          return decl.getTypeOfSimpleDecl();
        } else if (decl.getFunctionScope() != null) {
            DeclaredFunctionType scopeType = decl.getFunctionScope().getDeclaredFunctionType();
            if (scopeType != null) {
              return getCommonTypes().fromFunctionType(scopeType.toFunctionType());
            }
        } else if (decl.getNamespace() != null) {
          return decl.getNamespace().toJSType();
        }
        return null;
      }
      if (name.equals(this.name)) {
        return getCommonTypes()
            .fromFunctionType(getDeclaredFunctionType().toFunctionType());
      }
      if (parent != null) {
        return parent.getDeclaredTypeOf(name);
      }
      return null;
    }

    boolean hasUndeclaredFormalsOrOuters() {
      for (String formal : formals) {
        if (getDeclaredTypeOf(formal) == null) {
          return true;
        }
      }
      for (String outer : outerVars) {
        JSType declType = getDeclaredTypeOf(outer);
        if (declType == null
            // Undeclared functions have a non-null declared type,
            //  but they always have a return type of unknown
            || (declType.getFunType() != null
                && declType.getFunType().getReturnType().isUnknown())) {
          return true;
        }
      }
      return false;
    }

    private Scope getScopeHelper(String fnName) {
      Declaration decl = getDeclaration(fnName, false);
      return decl == null ? null : (Scope) decl.getFunctionScope();
    }

    boolean isKnownFunction(String fnName) {
      return getScopeHelper(fnName) != null;
    }

    boolean isExternalFunction(String fnName) {
      Scope s = Preconditions.checkNotNull(getScopeHelper(fnName));
      return s.root.isFromExterns();
    }

    Scope getScope(String fnName) {
      Scope s = getScopeHelper(fnName);
      Preconditions.checkState(s != null);
      return s;
    }

    Set<String> getLocals() {
      return ImmutableSet.copyOf(locals.keySet());
    }

    Set<String> getExterns() {
      return ImmutableSet.copyOf(externs.keySet());
    }

    private void addLocal(String name, JSType declType,
        boolean isConstant, boolean isFromExterns) {
      Preconditions.checkArgument(!isDefinedLocally(name, false));
      if (isConstant) {
        constVars.add(name);
      }
      if (isFromExterns) {
        externs.put(name, declType);
      } else {
        locals.put(name, declType);
      }
    }

    private void addNamespace(Node qnameNode, boolean isFromExterns) {
      Preconditions.checkArgument(!isNamespace(qnameNode));
      if (qnameNode.isName()) {
        localNamespaces.put(qnameNode.getString(), new NamespaceLit());
        if (isFromExterns) {
          // We don't know the full type of a namespace until after we see all
          // its properties. But we want to add it to the externs, otherwise it
          // is treated as a local and initialized to the wrong thing in NTI.
          externs.put(qnameNode.getString(), null);
        }
      } else {
        QualifiedName qname = QualifiedName.fromNode(qnameNode);
        Namespace ns = getNamespace(qname.getLeftmostName());
        ns.addSubnamespace(qname.getAllButLeftmost());
      }
    }

    private void updateType(String name, JSType newDeclType) {
      if (isDefinedLocally(name, false)) {
        locals.put(name, newDeclType);
      } else if (parent != null) {
        parent.updateType(name, newDeclType);
      } else {
        throw new RuntimeException(
            "Cannot update type of unknown variable: " + name);
      }
    }

    private void addOuterVar(String name) {
      outerVars.add(name);
    }

    private void addNominalType(Node qnameNode, RawNominalType rawNominalType) {
      if (qnameNode.isName()) {
        Preconditions.checkState(
            !localClassDefs.containsKey(qnameNode.getString()));
        localClassDefs.put(qnameNode.getString(), rawNominalType);
      } else {
        Preconditions.checkArgument(!isDefined(qnameNode));
        QualifiedName qname = QualifiedName.fromNode(qnameNode);
        Namespace ns = getNamespace(qname.getLeftmostName());
        ns.addNominalType(qname.getAllButLeftmost(), rawNominalType);
      }
    }

    private void addTypedef(Node qnameNode, Typedef td) {
      if (qnameNode.isName()) {
        Preconditions.checkState(
            !localTypedefs.containsKey(qnameNode.getString()));
        localTypedefs.put(qnameNode.getString(), td);
      } else {
        Preconditions.checkState(!isDefined(qnameNode));
        QualifiedName qname = QualifiedName.fromNode(qnameNode);
        Namespace ns = getNamespace(qname.getLeftmostName());
        ns.addTypedef(qname.getAllButLeftmost(), td);
      }
    }

    private Typedef getTypedef(String name) {
      Preconditions.checkState(!name.contains("."));
      Declaration decl = getDeclaration(name, false);
      return decl == null ? null : decl.getTypedef();
    }

    private void addEnum(Node qnameNode, EnumType e) {
      if (qnameNode.isName()) {
        Preconditions.checkState(
            !localEnums.containsKey(qnameNode.getString()));
        localEnums.put(qnameNode.getString(), e);
      } else {
        Preconditions.checkState(!isDefined(qnameNode));
        QualifiedName qname = QualifiedName.fromNode(qnameNode);
        Namespace ns = getNamespace(qname.getLeftmostName());
        ns.addEnum(qname.getAllButLeftmost(), e);
        qualifiedEnums.add(e);
      }
    }

    private EnumType getEnum(QualifiedName qname) {
      Declaration decl = getDeclaration(qname, false);
      return decl == null ? null : decl.getEnum();
    }

    private Namespace getNamespace(QualifiedName qname) {
      Namespace ns = getNamespace(qname.getLeftmostName());
      return qname.isIdentifier()
          ? ns : ns.getSubnamespace(qname.getAllButLeftmost());
    }

    private Declaration getLocalDeclaration(String name, boolean includeTypes) {
      Preconditions.checkArgument(!name.contains("."));
      if (!isDefinedLocally(name, includeTypes)) {
        return null;
      }
      JSType type = null;
      boolean isFormal = false;
      boolean isFromExterns = false;
      boolean isForwardDeclaration = false;
      boolean isTypeVar = false;
      if (locals.containsKey(name)) {
        type = locals.get(name);
      } else if (formals.contains(name)) {
        isFormal = true;
        int formalIndex = formals.indexOf(name);
        if (declaredType != null && formalIndex != -1) {
          JSType formalType = declaredType.getFormalType(formalIndex);
          if (formalType != null && !formalType.isBottom()) {
            type = formalType;
          }
        }
      } else if (localTypedefs.containsKey(name) || localNamespaces.containsKey(name)
          || localEnums.containsKey(name) || localFunDefs.containsKey(name)
          || localClassDefs.containsKey(name)) {
        // Any further declarations are shadowed
      } else if (declaredType != null && declaredType.isTypeVariableDefinedLocally(name)) {
        isTypeVar = true;
        type = JSType.fromTypeVar(name);
      } else if (externs.containsKey(name)) {
        isFromExterns = true;
        type = externs.get(name);
      } else if (unknownTypeNames.contains(name)) {
        isForwardDeclaration = true;
      }
      return new Declaration(
          type,
          localTypedefs.get(name),
          localNamespaces.get(name),
          localEnums.get(name),
          localFunDefs.get(name),
          localClassDefs.get(name),
          isFormal,
          isTypeVar,
          constVars.contains(name),
          isFromExterns,
          isForwardDeclaration);
    }

    public Declaration getDeclaration(QualifiedName qname, boolean includeTypes) {
      if (qname.isIdentifier()) {
        return getDeclaration(qname.getLeftmostName(), includeTypes);
      }
      Namespace ns = getNamespace(qname.getLeftmostName());
      if (ns == null) {
        return null;
      }
      Declaration decl = ns.getDeclaration(qname.getAllButLeftmost());
      if (decl == null && unknownTypeNames.contains(qname.toString())) {
        return new Declaration(
            JSType.UNKNOWN, null, null, null, null, null, false, false, false, false, true);
      }
      return decl;
    }

    public Declaration getDeclaration(String name, boolean includeTypes) {
      Preconditions.checkArgument(!name.contains("."));
      Declaration decl = getLocalDeclaration(name, includeTypes);
      if (decl != null) {
        return decl;
      }
      return parent == null ? null : parent.getDeclaration(name, includeTypes);
    }

    private Namespace getNamespace(String name) {
      Preconditions.checkArgument(!name.contains("."));
      Declaration decl = getDeclaration(name, false);
      return decl == null ? null : decl.getNamespace();
    }

    private void resolveTypedefs(JSTypeCreatorFromJSDoc typeParser) {
      for (Typedef td : localTypedefs.values()) {
        if (!td.isResolved()) {
          typeParser.resolveTypedef(td, this);
        }
      }
    }

    private void resolveEnums(JSTypeCreatorFromJSDoc typeParser) {
      for (EnumType e : localEnums.values()) {
        if (!e.isResolved()) {
          typeParser.resolveEnum(e, this);
        }
      }
      for (EnumType e : qualifiedEnums) {
        if (!e.isResolved()) {
          typeParser.resolveEnum(e, this);
        }
      }
      qualifiedEnums = null;
    }

    private void declareUnknownType(QualifiedName qname) {
      if (qname.isIdentifier() || null == getNamespace(qname.getLeftmostName())) {
        String name = qname.getLeftmostName();
        if (!locals.containsKey(name)) {
          externs.put(name, JSType.UNKNOWN);
        }
        return;
      }
      Namespace leftmost = getNamespace(qname.getLeftmostName());
      QualifiedName props = qname.getAllButLeftmost();
      // The forward declared type may be on an undeclared namespace.
      // e.g. 'ns.Foo.Bar.Baz' when we don't even have a definition for ns.Foo.
      // Thus, we need to find the prefix of the qname that is not declared.
      while (!props.isIdentifier() && !leftmost.hasSubnamespace(props.getAllButRightmost())) {
        props = props.getAllButRightmost();
      }
      Namespace ns =
          props.isIdentifier() ? leftmost : leftmost.getSubnamespace(props.getAllButRightmost());
      String pname = props.getRightmostName();
      ns.addUndeclaredProperty(pname, null, JSType.UNKNOWN, /* isConst */ false);
    }

    private void removeTmpData() {
      for (String name : unknownTypeNames) {
        declareUnknownType(QualifiedName.fromQualifiedString(name));
      }
      unknownTypeNames = ImmutableSet.of();
      // For now, we put types of namespaces directly into the locals.
      // Alternatively, we could move this into NewTypeInference.initEdgeEnvs
      for (Map.Entry<String, NamespaceLit> entry : localNamespaces.entrySet()) {
        String name = entry.getKey();
        JSType t = entry.getValue().toJSType();
        if (externs.containsKey(name)) {
          externs.put(name, t);
        } else {
          locals.put(name, t);
        }
      }
      for (Map.Entry<String, EnumType> entry : localEnums.entrySet()) {
        locals.put(entry.getKey(), entry.getValue().toJSType());
      }
      for (String typedefName : localTypedefs.keySet()) {
        locals.put(typedefName, JSType.UNDEFINED);
      }
      localNamespaces = ImmutableMap.of();
      localClassDefs = ImmutableMap.of();
      localTypedefs = ImmutableMap.of();
      localEnums = ImmutableMap.of();
    }

    @Override
    public String toString() {
      StringBuilder sb = new StringBuilder();
      if (isTopLevel()) {
        sb.append("<TOP SCOPE>");
      } else {
        sb.append(getReadableName());
        sb.append('(');
        Joiner.on(',').appendTo(sb, formals);
        sb.append(')');
      }
      sb.append(" with root: ");
      sb.append(root);
      return sb.toString();
    }
  }
}


File: src/com/google/javascript/jscomp/newtypes/ObjectType.java
/*
 * Copyright 2013 The Closure Compiler Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.javascript.jscomp.newtypes;

import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Multimap;
import com.google.common.collect.Sets;
import com.google.javascript.rhino.Node;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;

/**
 *
 * @author blickly@google.com (Ben Lickly)
 * @author dimvar@google.com (Dimitris Vardoulakis)
 */
final class ObjectType implements TypeWithProperties {
  // TODO(dimvar): currently, we can't distinguish between an obj at the top of
  // the proto chain (nominalType = null) and an obj for which we can't figure
  // out its class
  private final NominalType nominalType;
  private final FunctionType fn;
  private final boolean isLoose;
  private final PersistentMap<String, Property> props;
  private final ObjectKind objectKind;

  static final ObjectType TOP_OBJECT = ObjectType.makeObjectType(
      null, null, null, false, ObjectKind.UNRESTRICTED);
  static final ObjectType TOP_STRUCT = ObjectType.makeObjectType(
      null, null, null, false, ObjectKind.STRUCT);
  static final ObjectType TOP_DICT = ObjectType.makeObjectType(
      null, null, null, false, ObjectKind.DICT);
  private static final PersistentMap<String, Property> BOTTOM_MAP =
      PersistentMap.of("_", Property.make(JSType.BOTTOM, JSType.BOTTOM));
  private static final ObjectType BOTTOM_OBJECT = new ObjectType(
      null, BOTTOM_MAP, null, false, ObjectKind.UNRESTRICTED);

  // Represents the built-in Object type. It's not available when the ObjectType
  // class is initialized because we read the definition from the externs.
  // It is kind of a hack that this is a static field (since we do create an
  // instance of JSTypes).
  // Making it non static requires significant changes and I'm not sure it's
  // worth it.
  private static NominalType builtinObject = null;

  private ObjectType(NominalType nominalType,
      PersistentMap<String, Property> props, FunctionType fn, boolean isLoose,
      ObjectKind objectKind) {
    Preconditions.checkArgument(fn == null || fn.isLoose() == isLoose,
        "isLoose: %s, fn: %s", isLoose, fn);
    Preconditions.checkArgument(FunctionType.isInhabitable(fn));
    Preconditions.checkArgument(fn == null || nominalType != null,
          "Cannot create function %s without nominal type", fn);
    if (nominalType != null) {
      Preconditions.checkArgument(!nominalType.isClassy() || !isLoose,
          "Cannot create loose objectType with nominal type %s", nominalType);
      Preconditions.checkArgument(fn == null || nominalType.isFunction(),
          "Cannot create objectType of nominal type %s with function (%s)",
          nominalType, fn);
    }
    this.nominalType = nominalType;
    this.props = props;
    this.fn = fn;
    this.isLoose = isLoose;
    this.objectKind = objectKind;
  }

  static ObjectType makeObjectType(NominalType nominalType,
      PersistentMap<String, Property> props, FunctionType fn,
      boolean isLoose, ObjectKind ok) {
    if (props == null) {
      props = PersistentMap.create();
    } else if (containsBottomProp(props) || !FunctionType.isInhabitable(fn)) {
      return BOTTOM_OBJECT;
    }
    return new ObjectType(nominalType, props, fn, isLoose, ok);
  }

  static ObjectType fromFunction(FunctionType fn, NominalType fnNominal) {
    return ObjectType.makeObjectType(
        fnNominal, null, fn, fn.isLoose(), ObjectKind.UNRESTRICTED);
  }

  static ObjectType fromNominalType(NominalType cl) {
    return ObjectType.makeObjectType(cl, null, null, false, cl.getObjectKind());
  }

  /** Construct an object with the given declared non-optional properties. */
  static ObjectType fromProperties(Map<String, JSType> propTypes) {
    PersistentMap<String, Property> props = PersistentMap.create();
    for (Map.Entry<String, JSType> propTypeEntry : propTypes.entrySet()) {
      String propName = propTypeEntry.getKey();
      JSType propType = propTypeEntry.getValue();
      if (propType.isBottom()) {
        return BOTTOM_OBJECT;
      }
      props = props.with(propName, Property.make(propType, propType));
    }
    return new ObjectType(
        null, props, null, false, ObjectKind.UNRESTRICTED);
  }

  static void setObjectType(NominalType builtinObject) {
    ObjectType.builtinObject = builtinObject;
  }

  boolean isInhabitable() {
    return this != BOTTOM_OBJECT;
  }

  static boolean containsBottomProp(PersistentMap<String, Property> props) {
    for (Property p : props.values()) {
      if (p.getType().isBottom()) {
        return true;
      }
    }
    return false;
  }

  boolean isStruct() {
    return objectKind.isStruct();
  }

  boolean isLoose() {
    return isLoose;
  }

  boolean isLooseStruct() {
    return isLoose && objectKind.isStruct();
  }

  boolean isDict() {
    return objectKind.isDict();
  }

  static ImmutableSet<ObjectType> withLooseObjects(Set<ObjectType> objs) {
    ImmutableSet.Builder<ObjectType> newObjs = ImmutableSet.builder();
    for (ObjectType obj : objs) {
      newObjs.add(obj.withLoose());
    }
    return newObjs.build();
  }

  // Trade-offs about property behavior on loose object types:
  // We never mark properties as optional on loose objects. The reason is that
  // we cannot know for sure when a property is optional or not.
  // Eg, when we see an assignment to a loose obj
  //   obj.p1 = 123;
  // we cannot know if obj already has p1, or if this is a property creation.
  // If the assignment is inside an IF branch, we should not say after the IF
  // that p1 is optional. But as a consequence, this means that any property we
  // see on a loose object might be optional. That's why we don't warn about
  // possibly-inexistent properties on loose objects.
  // Last, say we infer a loose object type with a property p1 for a formal
  // parameter of a function f. If we pass a non-loose object to f that does not
  // have a p1, we warn. This may create spurious warnings, if p1 is optional,
  // but mostly it catches real bugs.

  private ObjectType withLoose() {
    if (isLoose()
        // Don't loosen nominal types
        || this.nominalType != null && this.nominalType.isClassy()) {
      return this;
    }
    FunctionType fn = this.fn == null ? null : this.fn.withLoose();
    PersistentMap<String, Property> newProps = PersistentMap.create();
    for (Map.Entry<String, Property> propsEntry : this.props.entrySet()) {
      String pname = propsEntry.getKey();
      Property prop = propsEntry.getValue();
      // It's wrong to warn about a possibly absent property on loose objects.
      newProps = newProps.with(pname, prop.withRequired());
    }
    // No need to call makeObjectType; we know that the new object is inhabitable.
    return new ObjectType(
        nominalType, newProps, fn, true, this.objectKind);
  }

  static ImmutableSet<ObjectType> withoutProperty(
      Set<ObjectType> objs, QualifiedName qname) {
    ImmutableSet.Builder<ObjectType> newObjs = ImmutableSet.builder();
    for (ObjectType obj : objs) {
      newObjs.add(obj.withProperty(qname, null));
    }
    return newObjs.build();
  }

  // When type is null, this method removes the property.
  // If the property is already declared, but isDeclared is false, be careful
  // to not un-declare it.
  // If the property is already constant, but isConstant is false, be careful
  // to not un-const it.
  private ObjectType withPropertyHelper(QualifiedName qname, JSType type,
      boolean isDeclared, boolean isConstant) {
    // TODO(blickly): If the prop exists with right type, short circuit here.
    PersistentMap<String, Property> newProps = this.props;
    if (qname.isIdentifier()) {
      String pname = qname.getLeftmostName();
      JSType declType = getDeclaredProp(qname);
      if (type == null) {
        type = declType;
      }
      if (declType != null) {
        isDeclared = true;
        if (hasConstantProp(qname)) {
          isConstant = true;
        }
        if (type != null && !type.isSubtypeOf(declType)) {
          // Can happen in inheritance-related type errors.
          // Not sure what the best approach is.
          // For now, just forget the inferred type.
          type = declType;
        }
      } else if (isDeclared) {
        declType = type;
      }

      if (type == null && declType == null) {
        newProps = newProps.without(pname);
      } else {
        newProps = newProps.with(pname,
            isConstant ?
            Property.makeConstant(null, type, declType) :
            Property.make(type, isDeclared ? declType : null));
      }
    } else { // This has a nested object
      String objName = qname.getLeftmostName();
      QualifiedName objQname = new QualifiedName(objName);
      if (!mayHaveProp(objQname)) {
        Preconditions.checkState(type == null);
        return this;
      }
      QualifiedName innerProps = qname.getAllButLeftmost();
      Property objProp = getLeftmostProp(objQname);
      JSType inferred = type == null ?
          objProp.getType().withoutProperty(innerProps) :
          objProp.getType().withProperty(innerProps, type);
      JSType declared = objProp.getDeclaredType();
      newProps = newProps.with(objName, objProp.isOptional() ?
          Property.makeOptional(null, inferred, declared) :
          Property.make(inferred, declared));
    }
    return ObjectType.makeObjectType(
        nominalType, newProps, fn, isLoose, objectKind);
  }

  // When type is null, this method removes the property.
  ObjectType withProperty(QualifiedName qname, JSType type) {
    return withPropertyHelper(qname, type, false, false);
  }

  static ImmutableSet<ObjectType> withProperty(
      Set<ObjectType> objs, QualifiedName qname, JSType type) {
    ImmutableSet.Builder<ObjectType> newObjs = ImmutableSet.builder();
    for (ObjectType obj : objs) {
      newObjs.add(obj.withProperty(qname, type));
    }
    return newObjs.build();
  }

  static ImmutableSet<ObjectType> withDeclaredProperty(Set<ObjectType> objs,
      QualifiedName qname, JSType type, boolean isConstant) {
    ImmutableSet.Builder<ObjectType> newObjs = ImmutableSet.builder();
    for (ObjectType obj : objs) {
      newObjs.add(obj.withPropertyHelper(qname, type, true, isConstant));
    }
    return newObjs.build();
  }

  private ObjectType withPropertyRequired(String pname) {
    Property oldProp = this.props.get(pname);
    Property newProp = oldProp == null ?
        Property.make(JSType.UNKNOWN, null) :
        Property.make(oldProp.getType(), oldProp.getDeclaredType());
    return ObjectType.makeObjectType(
        nominalType, this.props.with(pname, newProp), fn,
        isLoose, this.objectKind);
  }

  static ImmutableSet<ObjectType> withPropertyRequired(
      Set<ObjectType> objs, String pname) {
    ImmutableSet.Builder<ObjectType> newObjs = ImmutableSet.builder();
    for (ObjectType obj : objs) {
      newObjs.add(obj.withPropertyRequired(pname));
    }
    return newObjs.build();
  }

  private static PersistentMap<String, Property> meetPropsHelper(
      boolean specializeProps1, NominalType resultNominalType,
      PersistentMap<String, Property> props1,
      PersistentMap<String, Property> props2) {
    PersistentMap<String, Property> newProps = props1;
    if (resultNominalType != null) {
      for (Map.Entry<String, Property> propsEntry : props1.entrySet()) {
        String pname = propsEntry.getKey();
        Property nomProp = resultNominalType.getProp(pname);
        if (nomProp != null) {
          newProps =
              addOrRemoveProp(newProps, pname, nomProp, propsEntry.getValue());
          if (newProps == BOTTOM_MAP) {
            return BOTTOM_MAP;
          }
        }
      }
    }
    for (Map.Entry<String, Property> propsEntry : props2.entrySet()) {
      String pname = propsEntry.getKey();
      Property prop2 = propsEntry.getValue();
      Property newProp;
      if (!props1.containsKey(pname)) {
        newProp = prop2;
      } else {
        Property prop1 = props1.get(pname);
        if (prop1.equals(prop2)) {
          continue;
        }
        newProp = specializeProps1 ?
            prop1.specialize(prop2) :
            Property.meet(prop1, prop2);
      }
      if (resultNominalType != null &&
          resultNominalType.getProp(pname) != null) {
        Property nomProp = resultNominalType.getProp(pname);
        newProps = addOrRemoveProp(newProps, pname, nomProp, newProp);
        if (newProps == BOTTOM_MAP) {
          return BOTTOM_MAP;
        }
      } else {
        if (newProp.getType().isBottom()) {
          return BOTTOM_MAP;
        }
        newProps = newProps.with(pname, newProp);
      }
    }
    return newProps;
  }

  private static PersistentMap<String, Property> addOrRemoveProp(
      PersistentMap<String, Property> props,
      String pname, Property nomProp, Property objProp) {
    JSType propType = objProp.getType();
    JSType nomPropType = nomProp.getType();
    if (!propType.isUnknown() &&
        propType.isSubtypeOf(nomPropType) && !propType.equals(nomPropType)) {
      // We use specialize so that if nomProp is @const, we don't forget it.
      Property newProp = nomProp.specialize(objProp);
      if (newProp.getType().isBottom()) {
        return BOTTOM_MAP;
      }
      return props.with(pname, newProp);
    }
    return props.without(pname);
  }

  private static Property getProp(Map<String, Property> props, NominalType nom, String pname) {
    if (props.containsKey(pname)) {
      return props.get(pname);
    } else if (nom != null) {
      return nom.getProp(pname);
    }
    return null;
  }

  // This method needs the nominal types because otherwise a property may become
  // optional by mistake after the join.
  // joinPropsLoosely doesn't need that, because we don't create optional props
  // on loose types.
  private static PersistentMap<String, Property> joinProps(
      Map<String, Property> props1, Map<String, Property> props2,
      NominalType nom1, NominalType nom2) {
    PersistentMap<String, Property> newProps = PersistentMap.create();
    for (String pname : Sets.union(props1.keySet(), props2.keySet())) {
      Property prop1 = getProp(props1, nom1, pname);
      Property prop2 = getProp(props2, nom2, pname);
      Property newProp = null;
      if (prop1 == null) {
        newProp = prop2.withOptional();
      } else if (prop2 == null) {
        newProp = prop1.withOptional();
      } else {
        newProp = Property.join(prop1, prop2);
      }
      newProps = newProps.with(pname, newProp);
    }
    return newProps;
  }

  private static PersistentMap<String, Property> joinPropsLoosely(
      Map<String, Property> props1, Map<String, Property> props2) {
    PersistentMap<String, Property> newProps = PersistentMap.create();
    for (Map.Entry<String, Property> propsEntry : props1.entrySet()) {
      String pname = propsEntry.getKey();
      if (!props2.containsKey(pname)) {
        newProps = newProps.with(pname, propsEntry.getValue().withRequired());
      }
      if (newProps == BOTTOM_MAP) {
        return BOTTOM_MAP;
      }
    }
    for (Map.Entry<String, Property> propsEntry : props2.entrySet()) {
      String pname = propsEntry.getKey();
      Property prop2 = propsEntry.getValue();
      if (props1.containsKey(pname)) {
        newProps = newProps.with(pname,
            Property.join(props1.get(pname), prop2).withRequired());
      } else {
        newProps = newProps.with(pname, prop2.withRequired());
      }
      if (newProps == BOTTOM_MAP) {
        return BOTTOM_MAP;
      }
    }
    return newProps;
  }

  static boolean isUnionSubtype(boolean keepLoosenessOfThis,
      Set<ObjectType> objs1, Set<ObjectType> objs2) {
    for (ObjectType obj1 : objs1) {
      boolean foundSupertype = false;
      for (ObjectType obj2 : objs2) {
        if (obj1.isSubtypeOf(keepLoosenessOfThis, obj2)) {
          foundSupertype = true;
          break;
        }
      }
      if (!foundSupertype) {
        return false;
      }
    }
    return true;
  }

  boolean isSubtypeOf(ObjectType obj2) {
    return isSubtypeOf(true, obj2);
  }

  /**
   * Required properties are acceptable where an optional is required,
   * but not vice versa.
   * Optional properties create cycles in the type lattice, eg,
   * { } \le { p: num= }  and also   { p: num= } \le { }.
   */
  boolean isSubtypeOf(boolean keepLoosenessOfThis, ObjectType obj2) {
    if (obj2 == TOP_OBJECT) {
      return true;
    }

    if ((keepLoosenessOfThis && this.isLoose) || obj2.isLoose) {
      return this.isLooseSubtypeOf(obj2);
    }

    if ((this.nominalType == null && obj2.nominalType != null)
        || this.nominalType != null && obj2.nominalType != null &&
        !this.nominalType.isSubtypeOf(obj2.nominalType)) {
      return false;
    }

    if (!objectKind.isSubtypeOf(obj2.objectKind)) {
      return false;
    }

    // If nominalType1 < nominalType2, we only need to check that the
    // properties of obj2 are in (obj1 or nominalType1)
    for (Map.Entry<String, Property> entry : obj2.props.entrySet()) {
      String pname = entry.getKey();
      Property prop2 = entry.getValue();
      Property prop1 = this.getLeftmostProp(new QualifiedName(pname));

      if (prop2.isOptional()) {
        if (prop1 != null && !prop1.getType().isSubtypeOf(prop2.getType())) {
          return false;
        }
      } else {
        if (prop1 == null || prop1.isOptional() ||
            !prop1.getType().isSubtypeOf(prop2.getType())) {
          return false;
        }
      }
    }

    if (obj2.fn == null) {
      return true;
    } else if (this.fn == null) {
      // Can only be executed if we have declared types for callable objects.
      return false;
    }
    return this.fn.isSubtypeOf(obj2.fn);
  }

  // We never infer properties as optional on loose objects,
  // and we don't warn about possibly inexistent properties.
  boolean isLooseSubtypeOf(ObjectType obj2) {
    Preconditions.checkState(isLoose || obj2.isLoose);
    if (obj2 == TOP_OBJECT) {
      return true;
    }

    if (!isLoose) {
      if (!objectKind.isSubtypeOf(obj2.objectKind)) {
        return false;
      }
      for (String pname : obj2.props.keySet()) {
        QualifiedName qname = new QualifiedName(pname);
        if (!mayHaveProp(qname) ||
            !getProp(qname).isSubtypeOf(obj2.getProp(qname))) {
          return false;
        }
      }
    } else { // this is loose, obj2 may be loose
      for (String pname : props.keySet()) {
        QualifiedName qname = new QualifiedName(pname);
        if (obj2.mayHaveProp(qname) &&
            !getProp(qname).isSubtypeOf(obj2.getProp(qname))) {
          return false;
        }
      }
    }

    if (obj2.fn == null) {
      return this.fn == null || obj2.isLoose();
    } else if (this.fn == null) {
      return isLoose;
    }
    return fn.isLooseSubtypeOf(obj2.fn);
  }

  ObjectType specialize(ObjectType other) {
    Preconditions.checkState(
        areRelatedClasses(this.nominalType, other.nominalType));
    NominalType resultNominalType =
        NominalType.pickSubclass(this.nominalType, other.nominalType);
    if (resultNominalType != null && resultNominalType.isClassy()) {
      if (fn != null || other.fn != null) {
        return null;
      }
      PersistentMap<String, Property> newProps =
          meetPropsHelper(true, resultNominalType, this.props, other.props);
      if (newProps == BOTTOM_MAP) {
        return BOTTOM_OBJECT;
      }
      return new ObjectType(
          resultNominalType,
          newProps,
          null,
          false,
          ObjectKind.meet(this.objectKind, other.objectKind));
    }
    PersistentMap<String, Property> newProps =
        meetPropsHelper(true, resultNominalType, this.props, other.props);
    if (newProps == BOTTOM_MAP) {
      return BOTTOM_OBJECT;
    }
    return new ObjectType(
        resultNominalType,
        newProps,
        this.fn == null ? null : this.fn.specialize(other.fn),
        this.isLoose,
        ObjectKind.meet(this.objectKind, other.objectKind));
  }

  static ObjectType meet(ObjectType obj1, ObjectType obj2) {
    Preconditions.checkState(
        areRelatedClasses(obj1.nominalType, obj2.nominalType));
    NominalType resultNominalType =
        NominalType.pickSubclass(obj1.nominalType, obj2.nominalType);
    FunctionType fn = FunctionType.meet(obj1.fn, obj2.fn);
    if (!FunctionType.isInhabitable(fn)) {
      return BOTTOM_OBJECT;
    }
    boolean isLoose = obj1.isLoose && obj2.isLoose ||
        fn != null && fn.isLoose();
    PersistentMap<String, Property> props;
    if (isLoose) {
      props = joinPropsLoosely(obj1.props, obj2.props);
    } else {
      props = meetPropsHelper(false, resultNominalType, obj1.props, obj2.props);
    }
    if (props == BOTTOM_MAP) {
      return BOTTOM_OBJECT;
    }
    return new ObjectType(
        resultNominalType,
        props,
        fn,
        isLoose,
        ObjectKind.meet(obj1.objectKind, obj2.objectKind));
  }

  static ObjectType join(ObjectType obj1, ObjectType obj2) {
    NominalType nom1 = obj1.nominalType;
    NominalType nom2 = obj2.nominalType;
    Preconditions.checkState(areRelatedClasses(nom1, nom2));

    if (obj1.equals(obj2)) {
      return obj1;
    }
    boolean isLoose = obj1.isLoose || obj2.isLoose;
    FunctionType fn = FunctionType.join(obj1.fn, obj2.fn);
    PersistentMap<String, Property> props;
    if (isLoose) {
      fn = fn == null ? null : fn.withLoose();
      props = joinPropsLoosely(obj1.props, obj2.props);
    } else {
      props = joinProps(obj1.props, obj2.props, nom1, nom2);
    }
    NominalType nominal = NominalType.pickSuperclass(nom1, nom2);
    // TODO(blickly): Split TOP_OBJECT from empty object and remove this case
    if (nominal == null || !nominal.isFunction()) {
      fn = null;
    }
    return ObjectType.makeObjectType(
        nominal,
        props,
        fn,
        isLoose,
        ObjectKind.join(obj1.objectKind, obj2.objectKind));
  }

  static ImmutableSet<ObjectType> joinSets(
      ImmutableSet<ObjectType> objs1, ImmutableSet<ObjectType> objs2) {
    if (objs1.isEmpty()) {
      return objs2;
    } else if (objs2.isEmpty()) {
      return objs1;
    }
    ObjectType[] objs1Arr = objs1.toArray(new ObjectType[0]);
    ObjectType[] keptFrom1 = objs1Arr.clone();
    ImmutableSet.Builder<ObjectType> newObjs = ImmutableSet.builder();
    for (ObjectType obj2 : objs2) {
      boolean addedObj2 = false;
      for (int i = 0; i < objs1Arr.length; i++) {
        ObjectType obj1 = objs1Arr[i];
        NominalType nominalType1 = obj1.nominalType;
        NominalType nominalType2 = obj2.nominalType;
        if (areRelatedClasses(nominalType1, nominalType2)) {
          if (nominalType2 == null && nominalType1 != null && !obj1.isSubtypeOf(obj2)
              || nominalType1 == null && nominalType2 != null && !obj2.isSubtypeOf(obj1)) {
            // Don't merge other classes with record types
            break;
          }
          keptFrom1[i] = null;
          addedObj2 = true;
          // obj1 and obj2 may be in a subtype relation.
          // Even then, we want to join them because we don't want to forget
          // any extra properties in the subtype object.
          newObjs.add(join(obj1, obj2));

          break;
        }
      }
      if (!addedObj2) {
        newObjs.add(obj2);
      }
    }
    for (ObjectType o : keptFrom1) {
      if (o != null) {
        newObjs.add(o);
      }
    }
    return newObjs.build();
  }

  private static boolean areRelatedClasses(NominalType c1, NominalType c2) {
    if (c1 == null || c2 == null) {
      return true;
    }
    return c1.isSubtypeOf(c2) || c2.isSubtypeOf(c1);
  }

  // TODO(dimvar): handle greatest lower bound of interface types.
  // If we do that, we need to normalize the output, otherwise it could contain
  // two object types that are in a subtype relation, eg, see
  // NewTypeInferenceES5OrLowerTest#testDifficultObjectSpecialization.
  static ImmutableSet<ObjectType> meetSetsHelper(
      boolean specializeObjs1,
      Set<ObjectType> objs1, Set<ObjectType> objs2) {
    ImmutableSet.Builder<ObjectType> newObjs = ImmutableSet.builder();
    for (ObjectType obj2 : objs2) {
      for (ObjectType obj1 : objs1) {
        if (areRelatedClasses(obj1.nominalType, obj2.nominalType)) {
          ObjectType newObj;
          if (specializeObjs1) {
            newObj = obj1.specialize(obj2);
            if (newObj == null) {
              continue;
            }
          } else {
            newObj = meet(obj1, obj2);
          }
          newObjs.add(newObj);
        }
      }
    }
    return newObjs.build();
  }

  static ImmutableSet<ObjectType> meetSets(
      Set<ObjectType> objs1, Set<ObjectType> objs2) {
    return meetSetsHelper(false, objs1, objs2);
  }

  static ImmutableSet<ObjectType> specializeSet(
      Set<ObjectType> objs1, Set<ObjectType> objs2) {
    return meetSetsHelper(true, objs1, objs2);
  }

  FunctionType getFunType() {
    return fn;
  }

  public NominalType getNominalType() {
    return nominalType;
  }

  public ImmutableSet<String> getAllOwnProps() {
    // Used by the type conversion pass.
    // The implementation works only for object literals.
    Preconditions.checkState(this.nominalType == null);
    return ImmutableSet.copyOf(props.keySet());
  }

  @Override
  public JSType getProp(QualifiedName qname) {
    Property p = getLeftmostProp(qname);
    if (qname.isIdentifier()) {
      return p == null ? JSType.UNDEFINED : p.getType();
    } else {
      Preconditions.checkState(p != null);
      return p.getType().getProp(qname.getAllButLeftmost());
    }
  }

  @Override
  public JSType getDeclaredProp(QualifiedName qname) {
    Property p = getLeftmostProp(qname);
    if (p == null) {
      return null;
    } else if (qname.isIdentifier()) {
      return p.isDeclared() ? p.getDeclaredType() : null;
    }
    return p.getType().getDeclaredProp(qname.getAllButLeftmost());
  }

  public Node getPropDefsite(QualifiedName qname) {
    Preconditions.checkArgument(qname.isIdentifier());
    return getLeftmostProp(qname).getDefsite();
  }

  private Property getLeftmostProp(QualifiedName qname) {
    String objName = qname.getLeftmostName();
    Property p = props.get(objName);
    if (p != null) {
      return p;
    }
    if (nominalType != null) {
      return nominalType.getProp(objName);
    }
    return builtinObject == null ? null : builtinObject.getProp(objName);
  }

  @Override
  public boolean mayHaveProp(QualifiedName qname) {
    Property p = getLeftmostProp(qname);
    return p != null &&
        (qname.isIdentifier() ||
        p.getType().mayHaveProp(qname.getAllButLeftmost()));
  }

  @Override
  public boolean hasProp(QualifiedName qname) {
    Preconditions.checkArgument(qname.isIdentifier());
    Property p = getLeftmostProp(qname);
    return p != null && !p.isOptional();
  }

  @Override
  public boolean hasConstantProp(QualifiedName qname) {
    Preconditions.checkArgument(qname.isIdentifier());
    Property p = getLeftmostProp(qname);
    return p != null && p.isConstant();
  }

  /**
   * Unify the two types symmetrically, given that we have already instantiated
   * the type variables of interest in {@code t1} and {@code t2}, treating
   * JSType.UNKNOWN as a "hole" to be filled.
   * @return The unified type, or null if unification fails
   */
  static ObjectType unifyUnknowns(ObjectType t1, ObjectType t2) {
    if (!Objects.equals(t1.nominalType, t2.nominalType)) {
      return null;
    }
    FunctionType newFn = null;
    if (t1.fn != null || t2.fn != null) {
      newFn = FunctionType.unifyUnknowns(t1.fn, t2.fn);
      if (newFn == null) {
        return null;
      }
    }
    PersistentMap<String, Property> newProps = PersistentMap.create();
    for (String propName : t1.props.keySet()) {
      Property prop1 = t1.props.get(propName);
      Property prop2 = t2.props.get(propName);
      if (prop2 == null) {
        return null;
      }
      Property p = Property.unifyUnknowns(prop1, prop2);
      if (p == null) {
        return null;
      }
      newProps = newProps.with(propName, p);
    }
    return makeObjectType(t1.nominalType, newProps, newFn,
        t1.isLoose || t2.isLoose,
        ObjectKind.join(t1.objectKind, t2.objectKind));
  }

  /**
   * Unify {@code this}, which may contain free type variables,
   * with {@code other}, a concrete type, modifying the supplied
   * {@code typeMultimap} to add any new template varaible type bindings.
   * @return Whether unification succeeded
   */
  boolean unifyWithSubtype(ObjectType other, List<String> typeParameters,
      Multimap<String, JSType> typeMultimap) {
    if (fn != null) {
      if (other.fn == null ||
          !fn.unifyWithSubtype(other.fn, typeParameters, typeMultimap)) {
        return false;
      }
    }
    if (nominalType != null && other.nominalType != null) {
      return nominalType.unifyWithSubtype(
          other.nominalType, typeParameters, typeMultimap);
    }
    if (nominalType != null || other.nominalType != null) {
      return false;
    }
    for (String propName : this.props.keySet()) {
      Property thisProp = props.get(propName);
      Property otherProp = other.props.get(propName);
      if (otherProp == null ||
          !thisProp.unifyWithSubtype(otherProp, typeParameters, typeMultimap)) {
        return false;
      }
    }
    return true;
  }

  ObjectType substituteGenerics(Map<String, JSType> concreteTypes) {
    if (concreteTypes.isEmpty()) {
      return this;
    }
    PersistentMap<String, Property> newProps = PersistentMap.create();
    for (Map.Entry<String, Property> propsEntry : this.props.entrySet()) {
      String pname = propsEntry.getKey();
      Property newProp =
          propsEntry.getValue().substituteGenerics(concreteTypes);
      newProps = newProps.with(pname, newProp);
    }
    return makeObjectType(
        nominalType == null ? null :
        nominalType.instantiateGenerics(concreteTypes),
        newProps,
        fn == null ? null : fn.substituteGenerics(concreteTypes),
        isLoose,
        objectKind);
  }

  @Override
  public String toString() {
    return appendTo(new StringBuilder()).toString();
  }

  StringBuilder appendTo(StringBuilder builder) {
    if (props.isEmpty()
        || (props.size() == 1 && props.containsKey("prototype"))) {
      if (fn != null) {
        return fn.appendTo(builder);
      } else if (nominalType != null) {
        return nominalType.appendTo(builder);
      }
    }
    if (nominalType != null) {
      nominalType.appendTo(builder);
    } else if (isStruct()) {
      builder.append("struct");
    } else if (isDict()) {
      builder.append("dict");
    }
    if (nominalType == null || !props.isEmpty()) {
      builder.append('{');
      boolean firstIteration = true;
      for (String pname : new TreeSet<>(props.keySet())) {
        if (firstIteration) {
          firstIteration = false;
        } else {
          builder.append(", ");
        }
        builder.append(pname);
        builder.append(':');
        props.get(pname).appendTo(builder);
      }
      builder.append('}');
    }
    if (isLoose) {
      builder.append(" (loose)");
    }
    return builder;
  }

  @Override
  public boolean equals(Object o) {
    if (o == null) {
      return false;
    }
    if (this == o) {
      return true;
    }
    Preconditions.checkArgument(o instanceof ObjectType);
    ObjectType obj2 = (ObjectType) o;
    return Objects.equals(fn, obj2.fn) &&
        Objects.equals(nominalType, obj2.nominalType) &&
        Objects.equals(props, obj2.props);
  }

  @Override
  public int hashCode() {
    return Objects.hash(fn, props, nominalType);
  }
}


File: test/com/google/javascript/jscomp/NewTypeInferenceES5OrLowerTest.java
/*
 * Copyright 2013 The Closure Compiler Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.javascript.jscomp;

import com.google.common.base.Joiner;

import com.google.javascript.jscomp.newtypes.JSTypeCreatorFromJSDoc;

/**
 * @author blickly@google.com (Ben Lickly)
 * @author dimvar@google.com (Dimitris Vardoulakis)
 */

public final class NewTypeInferenceES5OrLowerTest extends NewTypeInferenceTestBase {

  public void testExterns() {
    typeCheck(
        "/** @param {Array<string>} x */ function f(x) {}; f([5]);",
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testVarDefinitionsInExterns() {
    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "var undecl = {};", "if (undecl) { undecl.x = 7 };");

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "var undecl = {};",
        "function f() { if (undecl) { undecl.x = 7 }; }");

    typeCheckCustomExterns(DEFAULT_EXTERNS + "var undecl;", "undecl(5);");

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "/** @type {number} */ var num;", "num - 5;");

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "var maybeStr; /** @type {string} */ var maybeStr;",
        "maybeStr - 5;");

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "/** @type {string} */ var str;", "str - 5;",
        NewTypeInference.INVALID_OPERAND_TYPE);

    // TODO(blickly): Warn if function in externs has body
    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "function f() {/** @type {string} */ var invisible;}",
        "invisible - 5;");
    //         VarCheck.UNDEFINED_VAR_ERROR);

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "/** @type {number} */ var num;",
        "/** @type {undefined} */ var x = num;",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "var untypedNum;",
        Joiner.on('\n').join(
            "function f(x) {",
            " x < untypedNum;",
            " untypedNum - 5;",
            "}",
            "f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testThisInAtTypeFunction() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){};",
        "/** @type {number} */ Foo.prototype.n;",
        "/** @type {function(this:Foo)} */ function f() { this.n = 'str' };"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "/** @type {function(this:gibberish)} */ function foo() {}",
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "var /** function(this:Foo) */ x = function() {};"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {function(this:Foo)} x */",
        "function f(x) {}",
        "f(/** @type {function(this:Foo)} */ (function() {}));"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {number} */ this.prop = 1; }",
        "/** @type {function(this:Foo)} */",
        "function f() { this.prop = 'asdf'; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {}",
        "/** @param {function(this:Foo)} x */",
        "function f(x) {}",
        "f(/** @type {function(this:Bar)} */ (function() {}));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function High() {}",
        "/** @constructor @extends {High} */",
        "function Low() {}",
        "function f(/** function(this:Low) */ low,",
        "           /** function(this:High) */ high) {",
        "  var fun = (1 < 2) ? low : high;",
        "  var /** function(this:High) */ f2 = fun;",
        "  var /** function(this:Low) */ f3 = fun;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function High() {}",
        "/** @constructor @extends {High} */",
        "function Low() {}",
        "function f(/** function(function(this:Low)) */ low,",
        "           /** function(function(this:High)) */ high) {",
        "  var fun = (1 < 2) ? low : high;",
        "  var /** function(function(this:High)) */ f2 = fun;",
        "  var /** function(function(this:Low)) */ f3 = fun;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " * @param {T} x",
        " */",
        "function Foo(x) {}",
        "/**",
        " * @template T",
        " * @param {function(this:Foo<T>)} fun",
        " */",
        "function f(fun) { return fun; }",
        "var /** function(this:Foo<string>) */ x =",
        "    f(/** @type {function(this:Foo<number>)} */ (function() {}));"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testThisInFunctionJsdoc() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {};",
        "/** @type {number} */ Foo.prototype.n;",
        "/** @this {Foo} */",
        "function f() { this.n = 'str'; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "/** @this {gibberish} */ function foo() {}",
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {number} */ this.prop = 1; }",
        "/** @this {Foo} */",
        "function f() { this.prop = 'asdf'; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  // TODO(dimvar): we must warn when a THIS fun isn't called as a method
  public void testDontCallMethodAsFunction() {
    typeCheck(Joiner.on('\n').join(
        "/** @type{function(this: Object)} */",
        "function f() {}",
        "f();"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype.method = function() {};",
        "var f = (new Foo).method;",
        "f();"));
  }

  public void testNewInFunctionJsdoc() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function h(/** function(new:Foo, ...number):number */ f) {",
        "  (new f()) - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " * @param {T} x",
        " */",
        "function Foo(x) {}",
        "/**",
        " * @template T",
        " * @param {function(new:Foo<T>)} fun",
        " */",
        "function f(fun) { return fun; }",
        "/** @type {function(new:Foo<number>)} */",
        "function f2() {}",
        "var /** function(new:Foo<string>) */ x = f(f2);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(x) {",
        "  x();",
        "  var /** !Foo */ y = new x();",
        "  var /** function(new:Foo, number) */ z = x;",
        "}"));

    // TODO(dimvar): this is a bogus warning, x can be arbitrary and does not
    // need to have the num property; see NominalType#getConstructorObject
    // for what needs to change.
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @type {number} */",
        "Foo.num = 123;",
        "function f(/** function(new:Foo, string) */ x) {",
        "  var /** string */ s = x.num;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testAlhpaRenamingDoesntChangeType() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {U} x",
        " * @param {U} y",
        " * @template U",
        " */",
        "function f(x, y){}",
        "/**",
        " * @template T",
        " * @param {function(T, T): boolean} comp",
        " * @param {!Array<T>} arr",
        " */",
        "function g(comp, arr) {",
        "  var compare = comp || f;",
        "  compare(arr[0], arr[1]);",
        "}"));
  }

  public void testInvalidThisReference() {
    typeCheck("this.x = 5;", CheckGlobalThis.GLOBAL_THIS);

    typeCheck("function f(x){}; f(this);");

    typeCheck("function f(){ return this; }");

    typeCheck("function f() { this.p = 1; }", CheckGlobalThis.GLOBAL_THIS);

    typeCheck("function f() { return this.p; }", CheckGlobalThis.GLOBAL_THIS);

    typeCheck("function f() { this['p']; }", CheckGlobalThis.GLOBAL_THIS);

    // TODO(dimvar): Will be fixed once we handle any JSType as a receiver type
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @this {T}",
        " */",
        "function f(x) {",
        "  this.p = 123;",
        "}"),
        CheckGlobalThis.GLOBAL_THIS);
  }

  public void testSuperClassWithUndeclaredProps() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Error() {};",
        "Error.prototype.sourceURL;",
        "/** @constructor @extends {Error} */ function SyntaxError() {}"));
  }

  public void testInheritMethodFromParent() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {};",
        "/** @param {string} x */ Foo.prototype.method = function(x) {};",
        "/** @constructor @extends {Foo} */ function Bar() {};",
        "(new Bar).method(4)"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testSubClassWithUndeclaredProps() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Super() {};",
        "/** @type {string} */ Super.prototype.str;",
        "/** @constructor @extends {Super} */ function Sub() {};",
        "Sub.prototype.str;"));
  }

  public void testUseBeforeDeclaration() {
    // typeCheck("x; var x;", VariableReferenceCheck.EARLY_REFERENCE);

    // typeCheck("x = 7; var x;", VariableReferenceCheck.EARLY_REFERENCE);

    typeCheck(Joiner.on('\n').join(
        "function f() { return 9; }",
        "var x = f();",
        "x - 7;"));
  }

  // public void testUseWithoutDeclaration() {
  //   typeCheck("x;", VarCheck.UNDEFINED_VAR_ERROR);
  //   typeCheck("x = 7;", VarCheck.UNDEFINED_VAR_ERROR);
  //   typeCheck("var y = x;", VarCheck.UNDEFINED_VAR_ERROR);
  // }

  // public void testVarRedeclaration() {
  //   typeCheck(
  //       "function f(x) { var x; }",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "function f(x) { function x() {} }",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "function f(x) { /** @typedef {number} */ var x; }",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "var x; var x;",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "var x; function x() {}",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "var x; /** @typedef {number} */ var x;",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "function x() {} function x() {}",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "function x() {} var x;",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "function x() {} /** @typedef {number} */ var x;",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "/** @typedef {number} */ var x; /** @typedef {number} */ var x;",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "/** @typedef {number} */ var x; var x;",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "/** @typedef {number} */ var x; function x() {}",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck("var f = function g() {}; function f() {};",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck("var f = function g() {}; var f = function h() {};",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck("var g = function f() {}; var h = function f() {};");

  //   typeCheck(
  //       "var x; /** @enum */ var x = { ONE: 1 };",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck(
  //       "/** @enum */ var x = { ONE: 1 }; var x;",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);
  // }

  public void testDeclaredVariables() {
    typeCheck("var /** null */ obj = 5;", NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "var /** ?number */ n = true;", NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testEmptyBlockPropagation() {
    typeCheck(
        "var x = 5; { }; var /** string */ s = x",
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testForLoopInference() {
    typeCheck(Joiner.on('\n').join(
        "var x = 5;",
        "for (;true;) {",
        "  x = 'str';",
        "}",
        "var /** (string|number) */ y = x;",
        "(function(/** string */ s){})(x);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var x = 5;",
        "while (true) {",
        "  x = 'str';",
        "}",
        "(function(/** string */ s){})(x);",
        "var /** (string|number) */ y = x;"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "while (true) {",
        "  var x = 'str';",
        "}",
        "var /** (string|undefined) */ y = x;",
        "(function(/** string */ s){})(x);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "for (var x = 5; x < 10; x++) {}",
        "(function(/** string */ s){})(x);",
        "var /** number */ y = x;"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testConditionalSpecialization() {
    typeCheck(Joiner.on('\n').join(
        "var x, y = 5;",
        "if (true) {",
        "  x = 5;",
        "} else {",
        "  x = 'str';",
        "}",
        "if (x === 5) {",
        "  y = x;",
        "}",
        "y - 5"));

    typeCheck(Joiner.on('\n').join(
        "var x, y = 5;",
        "if (true) {",
        "  x = 5;",
        "} else {",
        "  x = null;",
        "}",
        "if (x !== null) {",
        "  y = x;",
        "}",
        "y - 5"));

    typeCheck(Joiner.on('\n').join(
        "var x, y;",
        "if (true) {",
        "  x = 5;",
        "} else {",
        "  x = null;",
        "}",
        "if (x === null) {",
        "  y = 5;",
        "} else {",
        "  y = x;",
        "}",
        "y - 5"));

    typeCheck(Joiner.on('\n').join(
        "var numOrNull = true ? null : 1",
        "if (null === numOrNull) { var /** null */ n = numOrNull; }"));
  }

  public void testUnspecializedStrictComparisons() {
    typeCheck(
        "var /** number */ n = (1 === 2);",
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testAndOrConditionalSpecialization() {
    typeCheck(Joiner.on('\n').join(
        "var x, y = 5;",
        "if (true) {",
        "  x = 5;",
        "} else if (true) {",
        "  x = null;",
        "}",
        "if (x !== null && x !== undefined) {",
        "  y = x;",
        "}",
        "y - 5"));

    typeCheck(Joiner.on('\n').join(
        "var x, y;",
        "if (true) {",
        "  x = 5;",
        "} else if (true) {",
        "  x = null;",
        "}",
        "if (x === null || x === void 0) {",
        "  y = 5;",
        "} else {",
        "  y = x;",
        "}",
        "y - 5"));

    typeCheck(Joiner.on('\n').join(
        "var x, y = 5;",
        "if (true) {",
        "  x = 5;",
        "} else if (true) {",
        "  x = null;",
        "}",
        "if (x === null || x === undefined) {",
        "  y = x;",
        "}",
        "var /** (number|null|undefined) **/ z = y;",
        "(function(/** (number|null) */ x){})(y);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var x, y;",
        "if (true) {",
        "  x = 5;",
        "} else if (true) {",
        "  x = null;",
        "}",
        "if (x !== null && x !== undefined) {",
        "  y = 5;",
        "} else {",
        "  y = x;",
        "}",
        "var /** (number|null|undefined) **/ z = y;",
        "(function(/** (number|null) */ x){})(y);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var x, y = 5;",
        "if (true) {",
        "  x = 5;",
        "} else {",
        "  x = 'str';",
        "}",
        "if (x === 7 || x === 8) {",
        "  y = x;",
        "}",
        "y - 5"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function C(){}",
        "var obj = new C;",
        "if (obj || false) { 123, obj.asdf; }"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  (typeof x === 'number') && (x - 5);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|string|null) */ x) {",
        "  (x && (typeof x === 'number')) && (x - 5);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|string|null) */ x) {",
        "  (x && (typeof x === 'string')) && (x - 5);",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|string|null) */ x) {",
        "  typeof x === 'string' && x;",
        "  x < 'asdf';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testLoopConditionSpecialization() {
    typeCheck(Joiner.on('\n').join(
        "var x = true ? null : 'str';",
        "while (x !== null) {}",
        "var /** null */ y = x;"));

    typeCheck(Joiner.on('\n').join(
        "var x = true ? null : 'str';",
        "for (;x !== null;) {}",
        "var /** null */ y = x;"));

    typeCheck(Joiner.on('\n').join(
        "for (var x = true ? null : 'str'; x === null;) {}",
        "var /** string */ y = x;"));

    typeCheck(Joiner.on('\n').join(
        "var x;",
        "for (x = true ? null : 'str'; x === null;) {}",
        "var /** string */ y = x;"));

    typeCheck(Joiner.on('\n').join(
        "var x = true ? null : 'str';",
        "do {} while (x === null);",
        "var /** string */ y = x;"));
  }

  public void testVarDecls() {
    typeCheck("/** @type {number} */ var x, y;", TypeCheck.MULTIPLE_VAR_DEF);

    typeCheck(
        "var /** number */ x = 5, /** string */ y = 6;",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "var /** number */ x = 'str', /** string */ y = 'str2';",
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testBadInitialization() {
    typeCheck(
        "/** @type {string} */ var s = 123;",
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testBadAssignment() {
    typeCheck(
        "/** @type {string} */ var s; s = 123;",
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testBadArithmetic() {
    typeCheck("123 - 'str';", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("123 * 'str';", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("123 / 'str';", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("123 % 'str';", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "var y = 123; var x = 'str'; var z = x - y;",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "var y = 123; var x; var z = x - y;",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("+true;"); // This is considered an explicit coercion

    typeCheck("true + 5;", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("5 + true;", NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testTypeAfterIF() {
    typeCheck(
        "var x = true ? 1 : 'str'; x - 1;",
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testSimpleBwdPropagation() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) { x - 5; }",
        "f(123);",
        "f('asdf')"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { x++; }",
        "f(123);",
        "f('asdf')"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(y) { var x = y; x - 5; }",
        "f(123);",
        "f('asdf')"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(y) { var x; x = y; x - 5; }",
        "f(123);",
        "f('asdf')"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { x + 5; }",
        "f(123);",
        "f('asdf')"));
  }

  public void testSimpleReturn() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) {}",
        "var /** undefined */ x = f();",
        "var /** number */ y = f();"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { return; }",
        "var /** undefined */ x = f();",
        "var /** number */ y = f();"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { return 123; }",
        "var /** undefined */ x = f();",
        "var /** number */ y = f();"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { if (x) {return 123;} else {return 'asdf';} }",
        "var /** (string|number) */ x = f();"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) { if (x) {return 123;} }",
        "var /** (undefined|number) */ x = f();"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) { var y = x; y - 5; return x; }",
        "var /** undefined */ x = f(1);",
        "var /** number */ y = f(2);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testComparisons() {
    typeCheck(
        "1 < 0; 'a' < 'b'; true < false; null < null; undefined < undefined;");

    typeCheck(
        "/** @param {{ p1: ?, p2: ? }} x */ function f(x) { x.p1 < x.p2; }");

    typeCheck("function f(x, y) { x < y; }");

    typeCheck(
        "var x = 1; var y = true ? 1 : 'str'; x < y;",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "var x = 'str'; var y = 1; x < y;",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var y = 1;",
        "  x < y;",
        "  return x;",
        "}",
        "var /** undefined */ x = f(1);",
        "var /** number */ y = f(2);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var y = x, z = 7;",
        "  y < z;",
        "}"));
  }

  public void testFunctionJsdoc() {
    typeCheck(Joiner.on('\n').join(
        "/** @param {number} n */",
        "function f(n) { n < 5; }"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {string} n */",
        "function f(n) { n < 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {string} */",
        "function f() { return 1; }"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {string} */",
        "function f() { return; }"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {string} */",
        "function f(s) { return s; }",
        "f(123);",
        "f('asdf')"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {number} */",
        "function f() {}"),
        CheckMissingReturn.MISSING_RETURN_STATEMENT);

    typeCheck(Joiner.on('\n').join(
        "/** @return {(undefined|number)} */",
        "function f() { if (true) { return 'str'; } }"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(number)} fun */",
        "function f(fun) {}",
        "f(function (/** string */ s) {});"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(
        "/** @param {number} n */ function f(/** number */ n) {}",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck("/** @constructor */ var Foo = function() {}; new Foo;");

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @param {number} x */ Foo.prototype.method = function(x) {};",
        "(new Foo).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.method = /** @param {number} x */ function(x) {};",
        "(new Foo).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.method = function(/** number */ x) {};",
        "(new Foo).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(
        "/** @type {function(number)} */ function f(x) {}; f('asdf');",
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(
        "/** @type {number} */ function f() {}",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @type {function():number} */",
        "function /** number */ f() { return 1; }"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(number) */ fnum, floose, cond) {",
        "  var y;",
        "  if (cond) {",
        "    y = fnum;",
        "  } else {",
        "    floose();",
        "    y = floose;",
        "  }",
        "  return y;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(): *} x */ function g(x) {}",
        "/** @param {function(number): string} x */ function f(x) {",
        "  g(x);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(
        "var x = {}; x.a = function(/** string */ x) {}; x.a(123);",
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck("/** @param {function(...)} x */ function f(x) {}");

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " */",
        "function A() {};",
        "/** @return {number} */",
        "A.prototype.foo = function() {};"));

    typeCheck(
        "/** @param {number} x */ function f(y) {}",
        GlobalTypeInfo.INEXISTENT_PARAM);
  }

  public void testFunctionSubtyping() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {}",
        "function f(/** function(new:Foo) */ x) {}",
        "f(Bar);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** function(new:Foo) */ x) {}",
        "f(function() {});"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor @extends {Foo} */",
        "function Bar() {}",
        "function f(/** function(new:Foo) */ x) {}",
        "f(Bar);"));
  }

  public void testFunctionJoin() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/**",
        " * @param {function(new:Foo, (number|string))} x ",
        " * @param {function(new:Foo, number)} y ",
        " */",
        "function f(x, y) {",
        "  var z = 1 < 2 ? x : y;",
        "  return new z(123);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {}",
        "/**",
        " * @param {function(new:Foo)} x ",
        " * @param {function(new:Bar)} y ",
        " */",
        "function f(x, y) {",
        "  var z = 1 < 2 ? x : y;",
        "  return new z();",
        "}"),
        NewTypeInference.NOT_A_CONSTRUCTOR);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** function(new:Foo) */ x, /** function() */ y) {",
        "  var z = 1 < 2 ? x : y;",
        "  return new z();",
        "}"),
        NewTypeInference.NOT_A_CONSTRUCTOR);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** function(new:Foo) */ x, /** function() */ y) {",
        "  var z = 1 < 2 ? x : y;",
        "  return z();",
        "}"));
  }

  public void testFunctionMeet() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/**",
        " * @param {function(new:Foo, (number|string))} x ",
        " * @param {function(new:Foo, number)} y ",
        " */",
        "function f(x, y) { if (x === y) { return x; } }"));
  }

  public void testRecordWithoutTypesJsdoc() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** {a, b} */ x) {}",
        "f({c: 123});"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testBackwardForwardPathologicalCase() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) { var y = 5; y < x; }",
        "f(123);",
        "f('asdf')"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testTopInitialization() {
    typeCheck("function f(x) { var y = x; y < 5; }");

    typeCheck("function f(x) { x < 5; }");

    typeCheck(
        "function f(x) { x - 5; x < 'str'; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var y = x; y - 5; y < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  // public void testMultipleFunctions() {
  //   typeCheck("function g() {};\n function f(x) { var x; };",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);

  //   typeCheck("function f(x) { var x; };\n function g() {};",
  //       VariableReferenceCheck.REDECLARED_VARIABLE);
  // }

  public void testSimpleCalls() {
    typeCheck("function f() {}; f(5);", TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck("function f(x) { x-5; }; f();", TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "/** @return {number} */ function f() { return 1; }",
        "var /** string */ s = f();"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "function f(/** number */ x) {}; f(true);",
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** boolean */ x) {}",
        "function g() { f(123); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** void */ x) {}",
        "function g() { f(123); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** boolean */ x) {}",
        "function g(x) {",
        "  var /** string */ s = x;",
        "  f(x < 7);",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) {}",
        "function g(x, y) {",
        "  y < x;",
        "  f(x);",
        "  var /** string */ s = y;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testObjectType() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function takesObj(/** Object */ x) {}",
        "takesObj(new Foo);"));

    typeCheck(Joiner.on('\n').join(
        "function takesObj(/** Object */ x) {}",
        "takesObj(null);"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function /** Object */ returnsObj() { return {}; }",
        "function takesFoo(/** Foo */ x) {}",
        "takesFoo(returnsObj());"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck("Object.prototype.hasOwnProperty.call({}, 'asdf');");
  }

  public void testCallsWithComplexOperator() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "function fun(cond, /** !Foo */ f, /** !Bar */ g) {",
        "  (cond ? f : g)();",
        "}"),
        TypeCheck.NOT_CALLABLE);
  }

  public void testDeferredChecks() {
    typeCheck(Joiner.on('\n').join(
        "function f() { return 'str'; }",
        "function g() { f() - 5; }"),
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { x - 5; }",
        "f(5 < 6);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, y) { x - y; }",
        "f(5);"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "function f() { return 'str'; }",
        "function g() { var x = f(); x - 7; }"),
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, y) { return x-y; }",
        "f(5, 'str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {number} */ function f(x) { return x; }",
        "f('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) { return x; }",
        "function g(x) {",
        "  var /** string */ s = f(x);",
        "};"),
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f() { new Foo('asdf'); }",
        "/** @constructor */ function Foo(x) { x - 5; }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Arr() {}",
        "/**",
        " * @template T",
        " * @param {...T} var_args",
        " */",
        "Arr.prototype.push = function(var_args) {};",
        "function f(x) {}",
        "var renameByParts = function(parts) {",
        "  var mapped = new Arr();",
        "  mapped.push(f(parts));",
        "};"));

    // Here we don't want a deferred check and an INVALID_INFERRED_RETURN_TYPE
    // warning b/c the return type is declared.
    typeCheck(Joiner.on('\n').join(
        "/** @return {string} */ function foo(){ return 'str'; }",
        "function g() { foo() - 123; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f() {",
        " function x() {};",
        " function g() { x(1); }",
        " g();",
        "}"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    // We used to erroneously create a deferred check for the call to f
    // (and crash as a result), because we had a bug where the top-level
    // function was not being shadowed by the formal parameter.
    typeCheck(Joiner.on('\n').join(
        "function f() { return 123; }",
        "var outer = 123;",
        "function g(/** function(number) */ f) {",
        "  f(123) < 'str';",
        "  return outer;",
        "}"));
  }

  public void testShadowing() {
    typeCheck(Joiner.on('\n').join(
        "var /** number */ x = 5;",
        "function f() {",
        "  var /** string */ x = 'str';",
        "  return x - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var /** number */ x = 5;",
        "function f() {",
        "  /** @typedef {string} */ var x;",
        "  return x - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var /** number */ x = 5;",
        "function f() {",
        "  /** @enum {string} */ var x = { FOO : 'str' };",
        "  return x - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    // Types that are only present in types, and not in code do not cause shadowing in code
    typeCheck(Joiner.on('\n').join(
        "var /** number */ X = 5;",
        "/** @template X */",
        "function f() {",
        "  return X - 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "var /** string */ X = 'str';",
        "/** @template X */",
        "function f() {",
        "  return X - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testTypedefIsUndefined() {
    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  /** @typedef {string} */ var x;",
        "  /** @type {undefined} */ var y = x;",
        "}"));
  }

  public void testFunctionsInsideFunctions() {
    typeCheck(Joiner.on('\n').join(
        "(function() {",
        "  function f() {}; f(5);",
        "})();"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "(function() {",
        "  function f() { return 'str'; }",
        "  function g() { f() - 5; }",
        "})();"),
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var /** number */ x;",
        "function f() { x = 'str'; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var x;",
        "function f() { x - 5; x < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testCrossScopeWarnings() {
    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  x < 'str';",
        "}",
        "var x = 5;",
        "f()"),
        NewTypeInference.CROSS_SCOPE_GOTCHA);

    // CROSS_SCOPE_GOTCHA is only for undeclared variables
    typeCheck(Joiner.on('\n').join(
        "/** @type {string} */ var s;",
        "function f() {",
        "  s = 123;",
        "}",
        "f();"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function g(x) {",
        "  function f() { x < 'str'; z < 'str'; x = 5; }",
        "  var z = x;",
        "  f();",
        "  x - 5;",
        "  z < 'str';",
        "}"));

    // TODO(dimvar): we can't do this yet; requires more info in the summary
    // typeCheck(Joiner.on('\n').join(
    //     "/** @constructor */",
    //     "function Foo() {",
    //     "  /** @type{?Object} */ this.prop = null;",
    //     "}",
    //     "Foo.prototype.initProp = function() { this.prop = {}; };",
    //     "var obj = new Foo();",
    //     "if (obj.prop == null) {",
    //     "  obj.initProp();",
    //     "  obj.prop.a = 123;",
    //     "}"));
  }

  public void testTrickyUnknownBehavior() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** function() */ x, cond) {",
        "  var y = cond ? x() : 5;",
        "  y < 'str';",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {function() : ?} x */ function f(x, cond) {",
        "  var y = cond ? x() : 5;",
        "  y < 'str';",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** function() */ x) {",
        "  x() < 'str';",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function g() { return {}; }",
        "function f() {",
        "  var /** ? */ x = g();",
        "  return x.y;",
        "}"),
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function g() { return {}; }",
        "function f() {",
        "  var /** ? */ x = g()",
        "  x.y = 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function g(x) { return x; }",
        "function f(z) {",
        "  var /** ? */ x = g(z);",
        "  x.y2 = 123;",
        // specializing to a loose object here
        "  return x.y1 - 5;",
        "}"));
  }

  public void testDeclaredFunctionTypesInFormals() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** function():number */ x) {",
        "  var /** string */ s = x();",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(number) */ x) {",
        "  x(true);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function g(x, y, /** function(number) */ f) {",
        "  y < x;",
        "  f(x);",
        "  var /** string */ s = y;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var y = x(); y - 5; y < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function():?} x */ function f(x) {",
        "  var y = x(); y - 5; y < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "function f(/** ? */ x) { x < 'asdf'; x - 5; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(number): string} x */ function g(x) {}",
        "/** @param {function(number): string} x */ function f(x) {",
        "  g(x);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(number): *} x */ function g(x) {}",
        "/** @param {function(*): string} x */ function f(x) {",
        "  g(x);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(*): string} x */ function g(x) {}",
        "/** @param {function(number): string} x */ function f(x) {",
        "  g(x);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(number): string} x */ function g(x) {}",
        "/** @param {function(number): *} x */ function f(x) {",
        "  g(x);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testSpecializedFunctions() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** function(string) : number */ x) {",
        "  if (x('str') === 5) {",
        "    x(5);",
        "  }",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(string) : string */ x) {",
        "  if (x('str') === 5) {",
        "    x(5);",
        "  }",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(string) */ x, y) {",
        "  y(1);",
        "  if (x === y) {",
        "    x(5);",
        "  }",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x === null) {",
        "    return 5;",
        "  } else {",
        "    return x - 43;",
        "  }",
        "}",
        "f('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var goog = {};",
        "/** @type {!Function} */ goog.abstractMethod = function(){};",
        "/** @constructor */ function Foo(){};",
        "/** @return {!Foo} */ Foo.prototype.clone = goog.abstractMethod;",
        "/** @constructor @extends {Foo} */",
        "function Bar() {}",
        "/** @return {!Bar} */ Bar.prototype.clone = goog.abstractMethod;"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var goog = {};",
        "/** @type {!Function} */ goog.abstractMethod = function(){};",
        "/** @constructor */ function Foo(){};",
        "/** @return {!Foo} */ Foo.prototype.clone = goog.abstractMethod;",
        "/** @constructor @extends {Foo} */",
        "function Bar() {}",
        "/** @return {!Bar} */ Bar.prototype.clone = goog.abstractMethod;",
        "var /** null */ n = (new Bar).clone();"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testDifficultObjectSpecialization() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function X() { this.p = 1; }",
        "/** @constructor */",
        "function Y() { this.p = 2; }",
        "/** @param {(!X|!Y)} a */",
        "function fn(a) {",
        "  a.p;",
        "  /** @type {!X} */ (a);",
        "}"));

    // Currently, two types that have a common subtype specialize to bottom
    // instead of to the common subtype. If we change that, then this test will
    // have no warnings.
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High1() {}",
        "/** @interface */",
        "function High2() {}",
        "/**",
        " * @constructor",
        " * @implements {High1}",
        " * @implements {High2}",
        " */",
        "function Low() {}",
        "function f(x) {",
        "  var /** !High1 */ v1 = x;",
        "  var /** !High2 */ v2 = x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    // Currently, two types that have a common subtype specialize to bottom
    // instead of to the common subtype. If we change that, then this test will
    // have no warnings, and the type of x will be !Low.
    // (We must normalize the output of specialize to avoid getting (!Med|!Low))
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High1() {}",
        "/** @interface */",
        "function High2() {}",
        "/** @interface */",
        "function High3() {}",
        "/**",
        " * @interface",
        " * @extends {High1}",
        " * @extends {High2}",
        " */",
        "function Mid() {}",
        "/**",
        " * @interface",
        " * @extends {Mid}",
        " * @extends {High3}",
        " */",
        "function Low() {}",
        "function f(x) {",
        "  var /** !High1 */ v1 = x;",
        "  var /** (!High2|!High3) */ v2 = x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testLooseConstructors() {
    typeCheck(Joiner.on('\n').join(
        "function f(ctor) {",
        "  new ctor(1);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(ctor) {",
        "  new ctor(1);",
        "}",
        "/** @constructor */ function Foo(/** string */ y) {}",
        "f(Foo);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testLooseFunctions() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x(1);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x(1);",
        "}",
        "function g(/** string */ y) {}",
        "f(g);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x(1);",
        "}",
        "function g(/** number */ y) {}",
        "f(g);"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x(1);",
        "}",
        "function g(/** (number|string) */ y) {}",
        "f(g);"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  5 - x(1);",
        "}",
        "/** @return {string} */",
        "function g(/** number */ y) { return ''; }",
        "f(g);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  5 - x(1);",
        "}",
        "/** @return {(number|string)} */",
        "function g(/** number */ y) { return 5; }",
        "f(g);"));

    typeCheck(Joiner.on('\n').join(
        "function f(x, y) {",
        "  x(5);",
        "  y(5);",
        "  return x(y);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x();",
        "  return x;",
        "}",
        "function g() {}",
        "function h() { f(g) - 5; }"),
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, cond) {",
        "  x();",
        "  return cond ? 5 : x;",
        "}",
        "function g() {}",
        "function h() { f(g, true) - 5; }"),
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);
    // A loose function is a loose subtype of a non-loose function.
    // Traditional function subtyping would warn here.
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x(5);",
        "  return x;",
        "}",
        "function g(x) {}",
        "function h() {",
        "  var /** function((number|string)) */ fun = f(g);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function g(/** string */ x) {}",
        "function f(x, y) {",
        "  y - 5;",
        "  x(y);",
        "  y + y;",
        "}",
        "f(g, 5)"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {string} */",
        "function g(/** number */ x) { return 'str'; }",
        "/** @return {number} */",
        "function f(x) {",
        "  var y = 5;",
        "  var z = x(y);",
        "  return z;",
        "}",
        "f(g)"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {number} */",
        "function g(/** number */ y) { return 6; }",
        "function f(x, cond) {",
        "  if (cond) {",
        "    5 - x(1);",
        "  } else {",
        "    x('str') < 'str';",
        "  }",
        "}",
        "f(g, true)"));

    typeCheck(Joiner.on('\n').join(
        "function f(g, cond) {",
        "  if (cond) {",
        "    g(5, cond);",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {function (number)|Function} x",
        " */",
        "function f(x) {};",
        "f(function () {});"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x(true, 'asdf');",
        "  x(false);",
        "}"));
  }

  public void testBackwardForwardPathologicalCase2() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, /** string */ y, z) {",
        "  var w = z;",
        "  x < z;",
        "  w < y;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testNotCallable() {
    typeCheck(Joiner.on('\n').join(
        "/** @param {number} x */ function f(x) {",
        "  x(7);",
        "}"),
        TypeCheck.NOT_CALLABLE);
  }

  public void testSimpleLocallyDefinedFunction() {
    typeCheck(Joiner.on('\n').join(
        "function f() { return 'str'; }",
        "var x = f();",
        "x - 7;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f() { return 'str'; }",
        "f() - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "(function() {",
        "  function f() { return 'str'; }",
        "  f() - 5;",
        "})();"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "(function() {",
        "  function f() { return 'str'; }",
        "  f() - 5;",
        "})();"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testIdentityFunction() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) { return x; }",
        "5 - f(1);"));
  }

  public void testReturnTypeInferred() {
    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  var x = g();",
        "  var /** string */ s = x;",
        "  x - 5;",
        "};",
        "function g() { return 'str'};"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testGetpropOnNonObjects() {
    typeCheck("(null).foo;", NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(Joiner.on('\n').join(
        "var /** undefined */ n;",
        "n.foo;"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck("var x = {}; x.foo.bar = 1;", TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "var /** undefined */ n;",
        "n.foo = 5;"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (x.prop) {",
        "    var /** { prop: ? } */ y = x;",
        "  }",
        "}"));

    // TODO(blickly): Currently, this warning is not good, referring to props of
    // BOTTOM. Ideally, we could warn about accessing a prop on undefined.
    typeCheck(Joiner.on('\n').join(
        "/** @param {undefined} x */",
        "function f(x) {",
        "  if (x.prop) {}",
        "}"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck("null[123];", NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(
        "function f(/** !Object */ x) { if (x[123]) { return 1; } }");

    typeCheck(
        "function f(/** undefined */ x) { if (x[123]) { return 1; } }",
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|null) */ n) {",
        "  n.foo;",
        "}"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|null|undefined) */ n) {",
        "  n.foo;",
        "}"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(Joiner.on('\n').join(
        "function f(/** (!Object|number|null|undefined) */ n) {",
        "  n.foo;",
        "}"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "Foo.prototype.prop;",
        "function f(/** (!Foo|undefined) */ n) {",
        "  n.prop;",
        "}"),
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "/** @type {string} */ Foo.prototype.prop1;",
        "function g(/** Foo */ f) {",
        "  f.prop1.prop2 = 'str';",
        "};"),
        NewTypeInference.NULLABLE_DEREFERENCE);
  }

  public void testNonexistentProperty() {
    typeCheck(Joiner.on('\n').join(
        "/** @param {{ a: number }} obj */",
        "function f(obj) {",
        "  123, obj.b;",
        "  obj.b = 'str';",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck("({}).p < 'asdf';", TypeCheck.INEXISTENT_PROPERTY);

    typeCheck("(/** @type {?} */ (null)).prop - 123;");

    typeCheck("(/** @type {?} */ (null)).prop += 123;");

    typeCheck("var x = {}; var y = x.a;", TypeCheck.INEXISTENT_PROPERTY);

    typeCheck("var x = {}; x.y - 3; x.y = 5;", TypeCheck.INEXISTENT_PROPERTY);
  }

  public void testNullableDereference() {
    typeCheck(
        "function f(/** ?{ p : number } */ o) { return o.p; }",
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() { /** @const */ this.p = 5; }",
        "function g(/** ?Foo */ f) { return f.p; }"),
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.p = function(){};",
        "function g(/** ?Foo */ f) { f.p(); }"),
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(
        "var f = 5 ? function() {} : null; f();",
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(
        "var f = 5 ? function(/** number */ n) {} : null; f('str');",
        NewTypeInference.NULLABLE_DEREFERENCE,
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** ?{ p : number } */ o) {",
        "  goog.asserts.assert(o);",
        "  return o.p;",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** ?{ p : number } */ o) {",
        "  goog.asserts.assertObject(o);",
        "  return o.p;",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** ?Array<string> */ a) {",
        "  goog.asserts.assertArray(a);",
        "  return a.length;",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.p = function(){};",
        "function g(/** ?Foo */ f) {",
        "  goog.asserts.assertInstanceof(f, Foo);",
        "  f.p();",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "function g(/** !Bar */ o) {",
        "  goog.asserts.assertInstanceof(o, Foo);",
        "}"),
        NewTypeInference.ASSERT_FALSE);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function g(/** !Foo */ o) {",
        "  goog.asserts.assertInstanceof(o, 42);",
        "}"),
        NewTypeInference.UNKNOWN_ASSERTION_TYPE);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function Bar() {}",
        "function g(/** !Foo */ o) {",
        "  goog.asserts.assertInstanceof(o, Bar);",
        "}"),
        NewTypeInference.UNKNOWN_ASSERTION_TYPE);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @interface */ function Bar() {}",
        "function g(/** !Foo */ o) {",
        "  goog.asserts.assertInstanceof(o, Bar);",
        "}"),
        NewTypeInference.UNKNOWN_ASSERTION_TYPE);
  }

  public void testAsserts() {
    typeCheck(
        CLOSURE_BASE + Joiner.on('\n').join(
            "function f(/** ({ p : string }|null|undefined) */ o) {",
            "  goog.asserts.assert(o);",
            "  o.p - 5;",
            "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function f(/** (Array<string>|Foo) */ o) {",
        "  goog.asserts.assert(o instanceof Array);",
        "  var /** string */ s = o.length;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.p = function(/** number */ x){};",
        "function f(/** (function(new:Foo)) */ ctor,",
        "           /** ?Foo */ o) {",
        "  goog.asserts.assertInstanceof(o, ctor);",
        "  o.p('str');",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {",
        "  var y = x;",
        "  goog.asserts.assertInstanceof(y, Foo);",
        "}"));
  }

  public void testDontInferBottom() {
    typeCheck(
        // Ensure we don't infer bottom for x here
        "function f(x) { var /** string */ s; (s = x) - 5; } f(9);",
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testDontInferBottomReturn() {
    typeCheck(
        // Technically, BOTTOM is correct here, but since using dead code is error prone,
        // we'd rather infer f to return TOP (and get a warning).
        "function f() { throw ''; } f() - 5;",
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testAssignToInvalidObject() {
    typeCheck(
        "n.foo = 5; var n;",
        // VariableReferenceCheck.EARLY_REFERENCE,
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);
  }

  public void testAssignmentDoesntFlowWrongInit() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ n) {",
        "  n = 'typo';",
        "  n - 5;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ n: number }} x */ function f(x) {",
        "  x.n = 'typo';",
        "  x.n - 5;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testPossiblyNonexistentProperties() {
    typeCheck(Joiner.on('\n').join(
        "/** @param {{ n: number }} x */ function f(x) {",
        "  if (x.p) {",
        "    return x.p;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p : string }} x */ function reqHasPropP(x){}",
        "/** @param {{ n: number }} x */ function f(x, cond) {",
        "  if (cond) {",
        "    x.p = 'str';",
        "  }",
        "  reqHasPropP(x);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ n: number }} x */ function f(x, cond) {",
        "  if (cond) { x.p = 'str'; }",
        "  if (x.p) {",
        "    x.p - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** { n : number } */ x) {",
        "  x.s = 'str';",
        "  return x.inexistentProp;",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);
  }

  public void testDeclaredRecordTypes() {
    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} x */ function f(x) {",
        "  return x.p - 3;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: string }} x */ function f(x) {",
        "  return x.p - 3;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ 'p': string }} x */ function f(x) {",
        "  return x.p - 3;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} x */ function f(x) {",
        "  return x.q;",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: string }} obj */ function f(obj, x, y) {",
        "  x < y;",
        "  x - 5;",
        "  obj.p < y;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} x */ function f(x) {",
        "  x.p = 3;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} x */ function f(x) {",
        "  x.p = 'str';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} x */ function f(x) {",
        "  x.q = 'str';",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} x */ function f(x) {",
        "  x.q = 'str';",
        "}",
        "/** @param {{ p: number }} x */ function g(x) {",
        "  f(x);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} x */ function f(x) {",
        "  x.q = 'str';",
        "  return x.q;",
        "}",
        "/** @param {{ p: number }} x */ function g(x) {",
        "  f(x) - 5;",
        "}"),
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} x */ function f(x) {",
        "  x.q = 'str';",
        "  x.q = 7;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** { prop: number} */ obj) {",
        "  obj.prop = 'asdf';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** { prop: number} */ obj, cond) {",
        "  if (cond) { obj.prop = 123; } else { obj.prop = 234; }",
        "  obj.prop = 'asdf';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** {p: number} */ x, /** {p: (number|null)} */ y) {",
        "  var z;",
        "  if (true) { z = x; } else { z = y; }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "var /** { a: number } */ obj1 = { a: 321};",
        "var /** { a: number, b: number } */ obj2 = obj1;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testSimpleObjectLiterals() {
    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} obj */",
        "function f(obj) {",
        "  obj = { p: 123 };",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number, p2: string }} obj */",
        "function f(obj) {",
        "  obj = { p: 123 };",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} obj */",
        "function f(obj) {",
        "  obj = { p: 'str' };",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var obj;",
        "obj = { p: 123 };",
        "obj.p < 'str';"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} obj */",
        "function f(obj, x) {",
        "  obj = { p: x };",
        "  x < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} obj */",
        "function f(obj, x) {",
        "  obj = { p: 123, q: x };",
        "  obj.q - 5;",
        "  x < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
    // An example of how record types can hide away the extra properties and
    // allow type misuse.
    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} obj */",
        "function f(obj) {",
        "  obj.q = 123;",
        "}",
        "/** @param {{ p: number, q: string }} obj */",
        "function g(obj) { f(obj); }"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {{ p: number }} obj */",
        "function f(obj) {}",
        "var obj = {p: 5};",
        "if (true) {",
        "  obj.q = 123;",
        "}",
        "f(obj);"));

    typeCheck(
        "function f(/** number */ n) {}; f({});",
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testInferPreciseTypeWithDeclaredUnknown() {
    typeCheck(
        "var /** ? */ x = 'str'; x - 123;",
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testSimpleLooseObjects() {
    typeCheck("function f(obj) { obj.x = 1; obj.x - 5; }");

    typeCheck(
        "function f(obj) { obj.x = 'str'; obj.x - 5; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  var /** number */ x = obj.p;",
        "  obj.p < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  var /** @type {{ p: number }} */ x = obj;",
        "  obj.p < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  obj.x = 1;",
        "  return obj.x;",
        "}",
        "f({x: 'str'});"));

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  obj.x - 1;",
        "}",
        "f({x: 'str'});"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj, cond) {",
        "  if (cond) {",
        "    obj.x = 'str';",
        "  }",
        "  obj.x - 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  obj.x - 1;",
        "  return obj;",
        "}",
        "var /** string */ s = (f({x: 5})).x;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }


  public void testNestedLooseObjects() {
    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  obj.a.b = 123;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  obj.a.b = 123;",
        "  obj.a.b < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj, cond) {",
        "  (cond ? obj : obj).x - 1;",
        "  return obj.x;",
        "}",
        "f({x: 'str'}, true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  obj.a.b - 123;",
        "}",
        "f({a: {b: 'str'}})"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  obj.a.b = 123;",
        "}",
        "f({a: {b: 'str'}})"));

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  var o;",
        "  (o = obj).x - 1;",
        "  return o.x;",
        "}",
        "f({x: 'str'});"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  ({x: obj.foo}).x - 1;",
        "}",
        "f({foo: 'str'});"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  ({p: x++}).p = 'str';",
        "}",
        "f('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  ({p: 'str'}).p = x++;",
        "}",
        "f('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, y, z) {",
        "  ({p: (y = x++), q: 'str'}).p = z = y;",
        "  z < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testLooseObjectSubtyping() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {}",
        "function f(obj) { obj.prop - 5; }",
        "var /** !Foo */ x = new Foo;",
        "f(x);",
        "var /** !Bar */ y = x;"),
        NewTypeInference.INVALID_ARGUMENT_TYPE,
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function f(obj) { obj.prop - 5; }",
        "f(new Foo);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {string} */ this.prop = 'str'; }",
        "function f(obj) { obj.prop - 5; }",
        "f(new Foo);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() { /** @type {number} */ this.prop = 1; }",
        "function g(obj) { var /** string */ s = obj.prop; return obj; }",
        "var /** !Foo */ x = g({ prop: '' });"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    // Infer obj.a as loose, don't warn at the call to f.
    typeCheck(Joiner.on('\n').join(
        "function f(obj) { obj.a.num - 5; }",
        "function g(obj) {",
        "  obj.a.str < 'str';",
        "  f(obj);",
        "}"));

    // A loose object is a subtype of Array even if it has a dotted property
    typeCheck(Joiner.on('\n').join(
        "function f(/** Array<?> */ x) {}",
        "function g(obj) {",
        "  obj.x = 123;",
        "  f(obj);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(g) {",
        "  if (g.randomName) {",
        "  } else {",
        "    return g();",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x.a) {} else {}",
        "}",
        "f({ b: 123 }); "));

    // TODO(dimvar): We could warn about this since x is callable and we're
    // passing a non-function, but we don't catch it for now.
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x.randomName) {",
        "  } else {",
        "    return x();",
        "  }",
        "}",
        "f({ abc: 123 }); "));
  }

  public void testUnionOfRecords() {
    // The previous type inference doesn't warn because it keeps records
    // separate in unions.
    // We treat {x:number}|{y:number} as {x:number=, y:number=}
    typeCheck(Joiner.on('\n').join(
        "/** @param {({x:number}|{y:number})} obj */",
        "function f(obj) {}",
        "f({x: 5, y: 'asdf'});"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testUnionOfFunctionAndNumber() {
    typeCheck("var x = function(/** number */ y){};");

    // typeCheck("var x = function(/** number */ y){}; var x = 5",
    //     VariableReferenceCheck.REDECLARED_VARIABLE);

    typeCheck(
        "var x = function(/** number */ y){}; x('str');",
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(
        "var x = true ? function(/** number */ y){} : 5; x('str');",
        TypeCheck.NOT_CALLABLE,
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testAnonymousNominalType() {
    typeCheck(Joiner.on('\n').join(
        "function f() { return {}; }",
        "/** @constructor */",
        "f().Foo = function() {};"),
        GlobalTypeInfo.ANONYMOUS_NOMINAL_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var x = {};",
        "function f() { return x; }",
        "/** @constructor */",
        "f().Foo = function() {};",
        "new (f().Foo)();"),
        GlobalTypeInfo.ANONYMOUS_NOMINAL_TYPE);
  }

  public void testFoo() {
    typeCheck(
        "/** @constructor */ function Foo() {}; Foo();",
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);

    typeCheck(
        "function Foo() {}; new Foo();", NewTypeInference.NOT_A_CONSTRUCTOR);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {};",
        "function reqFoo(/** Foo */ f) {};",
        "reqFoo(new Foo());"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {};",
        "/** @constructor */ function Bar() {};",
        "function reqFoo(/** Foo */ f) {};",
        "reqFoo(new Bar());"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {};",
        "function reqFoo(/** Foo */ f) {};",
        "function g() {",
        "  /** @constructor */ function Foo() {};",
        "  reqFoo(new Foo());",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {number} x */",
        "Foo.prototype.method = function(x) {};",
        "/** @param {!Foo} x */",
        "function f(x) { x.method('asdf'); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testComma() {
    typeCheck(
        "var x; var /** string */ s = (x = 1, x);",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var y = x;",
        "  y < (123, 'asdf');",
        "}",
        "f(123);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testTypeof() {
    typeCheck("(typeof 'asdf') < 123;", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var y = x;",
        "  y < (typeof 123);",
        "}",
        "f(123);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x === 'string') {",
        "    x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x != 'function') {",
        "    x - 5;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x == 'string') {",
        "    x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if ('string' === typeof x) {",
        "    x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x === 'number') {",
        "    x < 'asdf';",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x === 'boolean') {",
        "    x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x === 'undefined') {",
        "    x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x === 'function') {",
        "    x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (typeof x === 'function') {",
        "    x();",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x === 'object') {",
        "    x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (!(typeof x == 'number')) {",
        "    x.prop;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (!(typeof x == 'undefined')) {",
        "    x - 5;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (!(typeof x == 'undefined')) {",
        "    var /** undefined */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (typeof x !== 'undefined') {",
        "    var /** undefined */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (typeof x == 'undefined') {} else {",
        "    var /** undefined */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|undefined) */ x) {",
        "  if (typeof x !== 'undefined') {",
        "    x - 5;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  return (typeof 123 == 'number' ||",
        "    typeof 123 == 'string' ||",
        "    typeof 123 == 'boolean' ||",
        "    typeof 123 == 'undefined' ||",
        "    typeof 123 == 'function' ||",
        "    typeof 123 == 'object' ||",
        "    typeof 123 == 'unknown');",
        "}"));

    typeCheck(
        "function f(){ if (typeof 123 == 'numbr') return 321; }",
        TypeValidator.UNKNOWN_TYPEOF_VALUE);

    typeCheck(
        "switch (typeof 123) { case 'foo': }",
        TypeValidator.UNKNOWN_TYPEOF_VALUE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @param {(number|null|Foo)} x */",
        "function f(x) {",
        "  if (!(typeof x === 'object')) {",
        "    var /** number */ n = x;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {(number|function(number):number)} x */",
        "function f(x) {",
        "  if (!(typeof x === 'function')) {",
        "    var /** number */ n = x;",
        "  }",
        "}"));
  }

  public void testAssignWithOp() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var y = x, z = 0;",
        "  y < (z -= 123);",
        "}",
        "f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var y = x, z = { prop: 0 };",
        "  y < (z.prop -= 123);",
        "}",
        "f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  var z = { prop: 0 };",
        "  x < z.prop;",
        "  z.prop -= 123;",
        "}",
        "f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck("var x = 0; x *= 'asdf';", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "var /** string */ x = 'asdf'; x *= 123;",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("var x; x *= 123;", NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testClassConstructor() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {",
        "  /** @type {number} */ this.n = 5;",
        "};",
        "(new Foo()).n - 5;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {",
        "  /** @type {number} */ this.n = 5;",
        "};",
        "(new Foo()).n = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {",
        "  /** @type {number} */ this.n;",
        "};",
        "(new Foo()).n = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f() { (new Foo()).n = 'str'; }",
        "/** @constructor */ function Foo() {",
        "  /** @type {number} */ this.n = 5;",
        "};"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f() { var x = new Foo(); x.n = 'str'; }",
        "/** @constructor */ function Foo() {",
        "  /** @type {number} */ this.n = 5;",
        "};"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f() { var x = new Foo(); return x.n - 5; }",
        "/** @constructor */ function Foo() {",
        "  this.n = 5;",
        "};"));

    typeCheck(Joiner.on('\n').join(
        "function f() { var x = new Foo(); x.s = 'str'; x.s < x.n; }",
        "/** @constructor */ function Foo() {",
        "  /** @type {number} */ this.n = 5;",
        "};"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {",
        "  /** @type {number} */ this.n = 5;",
        "};",
        "function reqFoo(/** Foo */ x) {};",
        "reqFoo({ n : 20 });"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f() { var x = new Foo(); x.n - 5; x.n < 'str'; }",
        "/** @constructor */ function Foo() {",
        "  this.n = 5;",
        "};"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testPropertyDeclarations() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {number} */ this.x = 'abc';",
        "  /** @type {string} */ this.x = 'def';",
        "}"),
        GlobalTypeInfo.REDECLARED_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {number} */ this.x = 5;",
        "  /** @type {number} */ this.x = 7;",
        "}"),
        GlobalTypeInfo.REDECLARED_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  this.x = 5;",
        "  /** @type {number} */ this.x = 7;",
        "}",
        "function g() { (new Foo()).x < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {number} */ this.x = 7;",
        "  this.x = 5;",
        "}",
        "function g() { (new Foo()).x < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {number} */ this.x = 7;",
        "  this.x < 'str';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {?} */ this.x = 1;",
        "  /** @type {?} */ this.x = 1;",
        "}"),
        GlobalTypeInfo.REDECLARED_PROPERTY);
  }

  public void testPrototypePropertyAssignments() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {string} */ Foo.prototype.x = 'str';",
        "function g() { (new Foo()).x - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.x = 'str';",
        "function g() { var f = new Foo(); f.x - 5; f.x < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {function(string)} s */",
        "Foo.prototype.bar = function(s) {};",
        "function g() { (new Foo()).bar(5); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {};",
        "Foo.prototype.bar = function(s) {",
        "  /** @type {string} */ this.x = 'str';",
        "};",
        "(new Foo()).x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "(function() { Foo.prototype.prop = 123; })();"),
        GlobalTypeInfo.CTOR_IN_DIFFERENT_SCOPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function F() {}",
        "F.prototype.bar = function() {};",
        "F.prototype.bar = function() {};"),
        GlobalTypeInfo.REDECLARED_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function F() {}",
        "/** @return {void} */ F.prototype.bar = function() {};",
        "F.prototype.bar = function() {};"),
        GlobalTypeInfo.REDECLARED_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function C(){}",
        "C.prototype.foo = {};",
        "C.prototype.method = function() { this.foo.bar = 123; }"));

    // TODO(dimvar): I think we can fix the next one with better deferred checks
    // for prototype methods. Look into it.
    // typeCheck(Joiner.on('\n').join(
    //     "/** @constructor */ function Foo() {};",
    //     "Foo.prototype.bar = function(s) { s < 'asdf'; };",
    //     "function g() { (new Foo()).bar(5); }"),
    //     NewTypeInference.INVALID_ARGUMENT_TYPE);

    // TODO(blickly): Add fancier JSDoc annotation finding to jstypecreator
    // typeCheck(Joiner.on('\n').join(
    //     "/** @constructor */ function Foo() {};",
    //     "/** @param {string} s */ Foo.prototype.bar = function(s) {};",
    //     "function g() { (new Foo()).bar(5); }"),
    //     NewTypeInference.INVALID_ARGUMENT_TYPE);
    // typeCheck(Joiner.on('\n').join(
    //     "/** @constructor */ function Foo() {};",
    //     "Foo.prototype.bar = function(/** string */ s) {};",
    //     "function g() { (new Foo()).bar(5); }"),
    //     NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f() {}",
        "function g() { f.prototype.prop = 123; }"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {!Function} f */",
        "function foo(f) { f.prototype.bar = function(x) {}; }"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype.method = function() {};",
        "/** @type {number} */",
        "Foo.prototype.method.pnum = 123;",
        "var /** number */ n = Foo.prototype['method.pnum'];"),
        TypeCheck.INEXISTENT_PROPERTY);
  }

  public void testPrototypeAssignment() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype = { a: 1, b: 2 };",
        "var x = (new Foo).a;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype = { a: 1, b: 2 - 'asdf' };",
        "var x = (new Foo).a;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype = { a: 1, /** @const */ b: 2 };",
        "(new Foo).b = 3;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype = { method: function(/** number */ x) {} };",
        "(new Foo).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype = { method: function(/** number */ x) {} };",
        "/** @constructor @extends {Foo} */",
        "function Bar() {}",
        "(new Bar).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testAssignmentsToPrototype() {
    // TODO(dimvar): the 1st should pass, the 2nd we may stop catching
    // if we decide to not check these assignments at all.

    // typeCheck(Joiner.on('\n').join(
    //     "/** @constructor */",
    //     "function Foo() {}",
    //     "/** @constructor @extends {Foo} */",
    //     "function Bar() {}",
    //     "Bar.prototype = new Foo;",
    //     "Bar.prototype.method1 = function() {};"));

    // typeCheck(Joiner.on('\n').join(
    //     "/**",
    //     " * @constructor",
    //     " * @struct",
    //     " */",
    //     "function Bar() {}",
    //     "Bar.prototype = {};"),
    //     TypeCheck.CONFLICTING_SHAPE_TYPE);
  }

  public void testConflictingPropertyDefinitions() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() { this.x = 'str1'; };",
        "/** @type {string} */ Foo.prototype.x = 'str2';",
        "(new Foo).x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {string} */ Foo.prototype.x = 'str1';",
        "Foo.prototype.x = 'str2';",
        "(new Foo).x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.x = 'str2';",
        "/** @type {string} */ Foo.prototype.x = 'str1';",
        "(new Foo).x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {string} */ this.x = 'str1'; };",
        "Foo.prototype.x = 'str2';",
        "(new Foo).x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() { this.x = 5; };",
        "/** @type {string} */ Foo.prototype.x = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {string} */ this.x = 'str1'; };",
        "Foo.prototype.x = 5;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {string} */ this.x = 'str'; };",
        "/** @type {number} */ Foo.prototype.x = 'str';"),
        GlobalTypeInfo.REDECLARED_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {number} */ Foo.prototype.x = 1;",
        "/** @type {number} */ Foo.prototype.x = 2;"),
        GlobalTypeInfo.REDECLARED_PROPERTY);
  }

  public void testPrototypeAliasing() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.x = 'str';",
        "var fp = Foo.prototype;",
        "fp.x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testInstanceof() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function takesFoos(/** Foo */ afoo) {}",
        "function f(/** (number|Foo) */ x) {",
        "  takesFoos(x);",
        "  if (x instanceof Foo) { takesFoos(x); }",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(
        "({} instanceof function(){});", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "(123 instanceof Foo);"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function takesFoos(/** Foo */ afoo) {}",
        "function f(/** boolean */ cond, /** (number|Foo) */ x) {",
        "  if (x instanceof (cond || Foo)) { takesFoos(x); }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function f(/** (number|!Foo) */ x) {",
        "  if (x instanceof Foo) {} else { x - 5; }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function f(/** (number|!Foo) */ x) {",
        "  if (!(x instanceof Foo)) { x - 5; }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "function takesFoos(/** Foo */ afoo) {}",
        "function f(/** Foo */ x) {",
        "  if (x instanceof Bar) {} else { takesFoos(x); }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "function takesFoos(/** Foo */ afoo) {}",
        "/** @param {*} x */ function f(x) {",
        "  takesFoos(x);",
        "  if (x instanceof Foo) { takesFoos(x); }",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "var x = new Foo();",
        "x.bar = 'asdf';",
        "if (x instanceof Foo) { x.bar - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    // typeCheck(
    //     "function f(x) { if (x instanceof UndefinedClass) {} }",
    //     VarCheck.UNDEFINED_VAR_ERROR);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() { this.prop = 123; }",
        "function f(x) { x = 123; if (x instanceof Foo) { x.prop; } }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "/** @param {(number|!Bar)} x */",
        "function f(x) {",
        "  if (!(x instanceof Foo)) {",
        "    var /** number */ n = x;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @enum {!Foo} */",
        "var E = { ONE: new Foo };",
        "/** @param {(number|E)} x */",
        "function f(x) {",
        "  if (!(x instanceof Foo)) {",
        "    var /** number */ n = x;",
        "  }",
        "}"));
  }

  public void testFunctionsExtendFunction() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x instanceof Function) { x(); }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x instanceof Function) { x(1); x('str') }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** (null|function()) */ x) {",
        "  if (x instanceof Function) { x(); }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** (null|function()) */ x) {",
        "  if (x instanceof Function) {} else { x(); }",
        "}"),
        TypeCheck.NOT_CALLABLE);

    typeCheck("(function(){}).call(null);");

    typeCheck(Joiner.on('\n').join(
        "function greet(name) {}",
        "greet.call(null, 'bob');",
        "greet.apply(null, ['bob']);"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "Foo.prototype.greet = function(name){};",
        "Foo.prototype.greet.call(new Foo, 'bob');"));

    typeCheck(Joiner.on('\n').join(
        "Function.prototype.method = function(/** string */ x){};",
        "(function(){}).method(5);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(value) {",
        "  if (value instanceof Function) {} else if (value instanceof Object) {",
        "    return value.displayName || value.name || '';",
        "  }",
        "};"));
  }

  public void testObjectsAreNotClassy() {
    typeCheck(Joiner.on('\n').join(
        "function g(obj) {",
        "  if (!(obj instanceof Object)) { throw -1; }",
        "  return obj.x - 5;",
        "}",
        "g(new Object);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testFunctionWithProps() {
    typeCheck(Joiner.on('\n').join(
        "function f() {}",
        "f.x = 'asdf';",
        "f.x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testConstructorProperties() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {number} */ Foo.n = 1",
        "/** @type {number} */ Foo.n = 1"),
        GlobalTypeInfo.REDECLARED_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "function g() { Foo.bar - 5; }",
        "/** @constructor */ function Foo() {}",
        "Foo.bar = 42;"));

    typeCheck(Joiner.on('\n').join(
        "function g() { Foo.bar - 5; }",
        "/** @constructor */ function Foo() {}",
        "/** @type {string} */ Foo.bar = 'str';"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function g() { return (new Foo).bar; }",
        "/** @constructor */ function Foo() {}",
        "/** @type {string} */ Foo.bar = 'str';"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {string} */ Foo.prop = 'asdf';",
        "var x = Foo;",
        "x.prop - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function g() { Foo.prototype.baz = (new Foo).bar + Foo.bar; }",
        "/** @constructor */ function Foo() {}",
        "/** @type {number} */ Foo.prototype.bar = 5",
        "/** @type {string} */ Foo.bar = 'str';"),
        GlobalTypeInfo.CTOR_IN_DIFFERENT_SCOPE);

    // TODO(dimvar): warn about redeclared property
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {number} */ Foo.n = 1;",
        "Foo.n = 1;"));

    // TODO(dimvar): warn about redeclared property
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {number} */ Foo.n;",
        "Foo.n = '';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testTypeTighteningHeuristic() {
    typeCheck(
        "/** @param {*} x */ function f(x) { var /** ? */ y = x; x - 5; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** ? */ x) {",
        "  if (!(typeof x == 'number')) {",
        "    x < 'asdf';",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** { prop: ? } */ x) {",
        "  var /** (number|string) */ y = x.prop;",
        "  x.prop < 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|string) */ x, /** (number|string) */ y) {",
        "  var z;",
        "  if (1 < 2) {",
        "    z = x;",
        "  } else {",
        "    z = y;",
        "  }",
        "  z - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testDeclaredPropertyIndirectly() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** { n: number } */ obj) {",
        "  var o2 = obj;",
        "  o2.n = 'asdf';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testNonRequiredArguments() {
    typeCheck(Joiner.on('\n').join(
        "function f(f1, /** function(string=) */ f2, cond) {",
        "  var y;",
        "  if (cond) {",
        "    f1();",
        "    y = f1;",
        "  } else {",
        "    y = f2;",
        "  }",
        "  return y;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(number=)} fnum */",
        "function f(fnum) {",
        "  fnum(); fnum('asdf');",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(...number)} fnum */",
        "function f(fnum) {",
        "  fnum(); fnum(1, 2, 3, 'asdf');",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(number=, number)} g */",
        "function f(g) {}"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @param {number=} x */",
        "function f(x) {}",
        "f(); f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {number=} x */",
        "function f(x) {}",
        "f(1, 2);"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(
        "/** @type {function()} */ function f(x) {}",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(
        "/** @type {function(number)} */ function f() {}",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(
        "/** @type {function(number)} */ function f(/** number */ x) {}",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {number=} x",
        " * @param {number} y",
        " */",
        "function f(x, y) {}"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @type {function(number=)} */ function f(x) {}",
        "f(); f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(
        "/** @type {function(number=, number)} */ function f(x, y) {}",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(
        "function /** number */ f() { return 'asdf'; }",
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    typeCheck(
        "/** @return {number} */ function /** number */ f() { return 1; }",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @type {function(): number} */",
        "function /** number */ f() { return 1; }"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @type {function(...number)} */ function f() {}",
        "f(); f(1, 2, 3); f(1, 2, 'asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {...number} var_args */ function f(var_args) {}",
        "f(); f(1, 2, 3); f(1, 2, 'asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(
        "/** @type {function(...number)} */ function f(x) {}",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {...number} var_args",
        " * @param {number=} x",
        " */",
        "function f(var_args, x) {}"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @type {function(number=, ...number)} */",
        "function f(x) {}",
        "f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(number=) */ fnum,",
        "  /** function(string=) */ fstr, cond) {",
        "  var y;",
        "  if (cond) {",
        "    y = fnum;",
        "  } else {",
        "    y = fstr;",
        "  }",
        "  y();",
        "  y(123);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(...number) */ fnum,",
        "  /** function(...string) */ fstr, cond) {",
        "  var y;",
        "  if (cond) {",
        "    y = fnum;",
        "  } else {",
        "    y = fstr;",
        "  }",
        "  y();",
        "  y(123);",
        "}"),
        TypeCheck.NOT_CALLABLE,
        TypeCheck.NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "function f(",
        "  /** function() */ f1, /** function(string=) */ f2, cond) {",
        "  var y;",
        "  if (cond) {",
        "    y = f1;",
        "  } else {",
        "    y = f2;",
        "  }",
        "  y(123);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(string): *} x */ function g(x) {}",
        "/** @param {function(...number): string} x */ function f(x) {",
        "  g(x);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {number=} x",
        " * @param {number=} y",
        " */",
        "function f(x, y) {}",
        "f(undefined, 123);",
        "f('str')"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(...) */ fun) {}",
        "f(function() {});"));

    // The restarg formal doesn't have to be called var_args.
    // It shouldn't be used in the body of the function.
    // typeCheck(
    //     "/** @param {...number} x */ function f(x) { x - 5; }",
    //     VarCheck.UNDEFINED_VAR_ERROR);

    typeCheck(
        "/** @param {number=} x */ function f(x) { x - 5; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "/** @param {number=} x */ function f(x) { if (x) { x - 5; } }");

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(...number) */ x) {}",
        "f(function() {});"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** function() */ x) {}",
        "f(/** @type {function(...number)} */ (function(nums) {}));"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(string=) */ x) {}",
        "f(/** @type {function(...number)} */ (function(nums) {}));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** function(...number) */ x) {}",
        "f(/** @type {function(string=)} */ (function(x) {}));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {number} opt_num */ function f(opt_num) {}",
        "f();"));

    typeCheck(
        "function f(opt_num, x) {}", RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck("function f(var_args) {} f(1, 2, 3);");

    typeCheck(
        "function f(var_args, x) {}", RhinoErrorReporter.BAD_JSDOC_ANNOTATION);
  }

  public void testInferredOptionalFormals() {
    typeCheck("function f(x) {} f();");

    typeCheck("function f(/** number */ x, y) { x-5; } f(123);");

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x !== undefined) {",
        "    return x-5;",
        "  } else {",
        "    return 0;",
        "  }",
        "}",
        "f() - 1;",
        "f('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {function(number=)} */",
        "function f() {",
        "  return function(x) {};",
        "}",
        "f()();",
        "f()('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testSimpleClassInheritance() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {}",
        "/** @constructor @extends{Parent} */",
        "function Child() {}",
        "Child.prototype = new Parent();"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {",
        "  /** @type {string} */ this.prop = 'asdf';",
        "}",
        "/** @constructor @extends{Parent} */",
        "function Child() {}",
        "Child.prototype = new Parent();",
        "(new Child()).prop - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {",
        "  /** @type {string} */ this.prop = 'asdf';",
        "}",
        "/** @constructor @extends{Parent} */",
        "function Child() {}",
        "Child.prototype = new Parent();",
        "(new Child()).prop = 5;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {}",
        "/** @type {string} */ Parent.prototype.prop = 'asdf';",
        "/** @constructor @extends{Parent} */",
        "function Child() {}",
        "Child.prototype = new Parent();",
        "(new Child()).prop - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {}",
        "/** @type {string} */ Parent.prototype.prop = 'asdf';",
        "/** @constructor @extends{Parent} */",
        "function Child() {",
        "  /** @type {number} */ this.prop = 5;",
        "}",
        "Child.prototype = new Parent();"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {}",
        "/** @type {string} */ Parent.prototype.prop = 'asdf';",
        "/** @constructor @extends{Parent} */",
        "function Child() {}",
        "Child.prototype = new Parent();",
        "/** @type {number} */ Child.prototype.prop = 5;"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE,
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {}",
        "/** @extends {Parent} */ function Child() {}"),
        JSTypeCreatorFromJSDoc.EXTENDS_NOT_ON_CTOR_OR_INTERF);

    typeCheck(
        "/** @constructor @extends{number} */ function Foo() {}",
        JSTypeCreatorFromJSDoc.EXTENDS_NON_OBJECT);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @implements {string}",
        " */",
        "function Foo() {}"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @extends {number}",
        " */",
        "function Foo() {}"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Foo() {}",
        "/** @implements {Foo} */ function bar() {}"),
        JSTypeCreatorFromJSDoc.IMPLEMENTS_WITHOUT_CONSTRUCTOR);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype.method = function(x) { x - 1; };",
        "/** @constructor @extends {Foo} */",
        "function Bar() {}",
        "Bar.prototype.method = function(x, y) { x - y; };",
        "Bar.prototype.method2 = function(x, y) {};",
        "Bar.prototype.method = Bar.prototype.method2;"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);
  }

  public void testInheritingTheParentClassInterfaces() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High() {}",
        "/** @type {number} */",
        "High.prototype.p;",
        "/** @constructor @implements {High} */",
        "function Mid() {}",
        "Mid.prototype.p = 123;",
        // Low has p from Mid, no warning here
        "/** @constructor @extends {Mid} */",
        "function Low() {}"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High() {}",
        "/** @constructor @implements {High} */",
        "function Mid() {}",
        "/** @constructor @extends {Mid} */",
        "function Low() {}",
        "var /** !High */ x = new Low();"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function High() {}",
        "/**",
        " * @constructor",
        " * @template T",
        " * @implements {High<T>}",
        " */",
        "function Mid() {}",
        "/** @constructor @extends {Mid<number>} */",
        "function Low() {}",
        "var /** !High<string> */ x = new Low;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testInheritanceSubtyping() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Parent() {}",
        "/** @constructor @extends{Parent} */ function Child() {}",
        "(function(/** Parent */ x) {})(new Child);"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Parent() {}",
        "/** @constructor @extends{Parent} */ function Child() {}",
        "(function(/** Child */ x) {})(new Parent);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Parent() {}",
        "/** @constructor @extends{Parent} */ function Child() {}",
        "/** @constructor */",
        "function Foo() { /** @type {Parent} */ this.x = new Child(); }",
        "/** @type {Child} */ Foo.prototype.y = new Parent();"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High() {}",
        "/** @constructor @implements {High} */",
        "function Low() {}",
        "var /** !High */ x = new Low"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High() {}",
        "/** @interface @extends {High}*/",
        "function Low() {}",
        "function f(/** !High */ h, /** !Low */ l) { h = l; }"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High() {}",
        "/** @interface @extends {High}*/",
        "function Low() {}",
        "/** @constructor @implements {Low} */",
        "function Foo() {}",
        "var /** !High */ x = new Foo;"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Foo() {}",
        "/** @interface */",
        "function High() {}",
        "/** @interface @extends {High} */",
        "function Med() {}",
        "/**",
        " * @interface",
        " * @extends {Med}",
        " * @extends {Foo}",
        " */",
        "function Low() {}",
        "function f(/** !High */ x, /** !Low */ y) { x = y }"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function Foo() {}",
        "function f(/** !Foo<number> */ x, /** !Foo<string> */ y) { x = y; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function Foo() {}",
        "/**",
        " * @constructor",
        " * @implements {Foo<number>}",
        " */",
        "function Bar() {}",
        "function f(/** !Foo<string> */ x, /** Bar */ y) { x = y; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function Foo() {}",
        "/**",
        " * @constructor",
        " * @template T",
        " * @implements {Foo<T>}",
        " */",
        "function Bar() {}",
        "function f(/** !Foo<string> */ x, /** !Bar<number> */ y) { x = y; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function Foo() {}",
        "/**",
        " * @constructor",
        " * @template T",
        " * @implements {Foo<T>}",
        " */",
        "function Bar() {}",
        "function f(/** !Foo<string> */ x, /** !Bar<string> */ y) {",
        "  x = y;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function Foo() {}",
        "/**",
        " * @constructor",
        " * @template T",
        " * @implements {Foo<T>}",
        " */",
        "function Bar() {}",
        "/**",
        " * @template T",
        " * @param {!Foo<T>} x",
        " * @param {!Bar<number>} y",
        " */",
        "function f(x, y) { x = y; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    // When getting a method signature from the parent, the receiver type is
    // still the child's type.
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High() {}",
        "/** @param {number} x */",
        "High.prototype.method = function (x) {};",
        "/** @constructor @implements {High} */",
        "function Low() {}",
        "Low.prototype.method = function (x) {",
        "  var /** !Low */ y = this;",
        "};"));
  }

  public void testInheritanceImplicitObjectSubtyping() {
    String objectExterns = DEFAULT_EXTERNS
        + "/** @return {string} */ Object.prototype.toString = function() {};";

    typeCheckCustomExterns(
        objectExterns,
        Joiner.on('\n').join(
            "/** @constructor */ function Foo() {}",
            "/** @override */ Foo.prototype.toString = function(){ return ''; };"));

    typeCheckCustomExterns(
        objectExterns,
        Joiner.on('\n').join(
            "/** @constructor */ function Foo() {}",
            "/** @override */ Foo.prototype.toString = function(){ return 5; };"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);
  }

  public void testRecordtypeSubtyping() {
    // TODO(dimvar): fix
    // typeCheck(Joiner.on('\n').join(
    //     "/** @interface */ function I() {}",
    //     "/** @type {number} */ I.prototype.prop;",
    //     "function f(/** !I */ x) {",
    //     "  var /** { prop: number} */ y = x;",
    //     "}"));
  }

  public void testWarnAboutOverridesNotVisibleDuringGlobalTypeInfo() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @extends {Parent} */ function Child() {}",
        "/** @type {string} */ Child.prototype.y = 'str';",
        "/** @constructor */ function Grandparent() {}",
        "/** @type {number} */ Grandparent.prototype.y = 9;",
        "/** @constructor @extends {Grandparent} */ function Parent() {}"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);
  }

  public void testInvalidMethodPropertyOverride() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/** @type {number} */ Parent.prototype.y;",
        "/** @constructor @implements {Parent} */ function Child() {}",
        "/** @param {string} x */ Child.prototype.y = function(x) {};"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/** @param {string} x */ Parent.prototype.y = function(x) {};",
        "/** @constructor @implements {Parent} */ function Child() {}",
        "/** @type {number} */ Child.prototype.y = 9;"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Parent() {}",
        "/** @type {number} */ Parent.prototype.y = 9;",
        "/** @constructor @extends {Parent} */ function Child() {}",
        "/** @param {string} x */ Child.prototype.y = function(x) {};"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Parent() {}",
        "/** @param {string} x */ Parent.prototype.y = function(x) {};",
        "/** @constructor @extends {Parent} */ function Child() {}",
        "/** @type {number} */ Child.prototype.y = 9;"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    // TODO(dimvar): fix
    // typeCheck(Joiner.on('\n').join(
    //     "/** @constructor */",
    //     "function Foo() {}",
    //     "Foo.prototype.f = function(/** number */ x, /** number */ y) {};",
    //     "/** @constructor @extends {Foo} */",
    //     "function Bar() {}",
    //     "/** @override */",
    //     "Bar.prototype.f = function(x) {};"),
    //     GlobalTypeInfo.INVALID_PROP_OVERRIDE);
  }

  public void testMultipleObjects() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "/** @param {(Foo|Bar)} x */ function reqFooBar(x) {}",
        "function f(cond) {",
        "  reqFooBar(cond ? new Foo : new Bar);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "/** @param {Foo} x */ function reqFoo(x) {}",
        "function f(cond) {",
        "  reqFoo(cond ? new Foo : new Bar);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "/** @param {(Foo|Bar)} x */ function g(x) {",
        "  if (x instanceof Foo) {",
        "    var /** Foo */ y = x;",
        "  } else {",
        "    var /** Bar */ z = x;",
        "  }",
        "  var /** Foo */ w = x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {string} */ this.s = 'str'; }",
        "/** @param {(!Foo|{n:number, s:string})} x */ function g(x) {",
        "  if (x instanceof Foo) {",
        "  } else {",
        "    x.s - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {number} */ Foo.prototype.n = 5;",
        "/** @param {{n : number}} x */ function reqRecord(x) {}",
        "function f() {",
        "  reqRecord(new Foo);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @type {number} */ Foo.prototype.n = 5;",
        "/** @param {{n : string}} x */ function reqRecord(x) {}",
        "function f() {",
        "  reqRecord(new Foo);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @param {{n : number}|!Foo} x */",
        "function f(x) {",
        "  x.n - 5;",
        "}"),
        NewTypeInference.POSSIBLY_INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @param {{n : number}|!Foo} x */",
        "function f(x) {",
        "  x.abc - 5;",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "/** @param {!Bar|!Foo} x */",
        "function f(x) {",
        "  x.abc = 'str';",
        "  if (x instanceof Foo) {",
        "    x.abc - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testMultipleFunctionsInUnion() {
    typeCheck(Joiner.on('\n').join(
        "/** @param {function():string | function():number} x",
        "  * @return {string|number} */",
        "function f(x) {",
        "  return x();",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(string)|function(number)} x",
        "  * @param {string|number} y */",
        "function f(x, y) {",
        "  x(y);",
        "}"),
        JSTypeCreatorFromJSDoc.UNION_IS_UNINHABITABLE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template S, T",
        " * @param {function(S):void | function(T):void} fun",
        " */",
        "function f(fun) {}"),
        JSTypeCreatorFromJSDoc.UNION_IS_UNINHABITABLE);
  }

  public void testPrototypeOnNonCtorFunction() {
    typeCheck("function Foo() {}; Foo.prototype.y = 5;");
  }

  public void testInvalidTypeReference() {
    typeCheck(
        "/** @type {gibberish} */ var x;",
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(
        "/** @param {gibberish} x */ function f(x){};",
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(
        "function f(/** gibberish */ x){};",
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(Joiner.on('\n').join(
        "/** @returns {gibberish} */",
        "function f(x) { return x; };"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(
        "/** @interface @extends {gibberish} */ function Foo(){};",
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(
        "/** @constructor @implements {gibberish} */ function Foo(){};",
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(
        "/** @constructor @extends {gibberish} */ function Foo() {};",
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);
  }

  public void testCircularDependencies() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @extends {Bar}*/ function Foo() {}",
        "/** @constructor */ function Bar() {}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {Foo} x */ function f(x) {}",
        "/** @constructor */ function Foo() {}"));

    typeCheck(Joiner.on('\n').join(
        "f(new Bar)",
        "/** @param {Foo} x */ function f(x) {}",
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @param {Foo} x */ function Bar(x) {}",
        "/** @constructor @param {Bar} x */ function Foo(x) {}",
        "new Bar(new Foo(null));"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @param {Foo} x */ function Bar(x) {}",
        "/** @constructor @param {Bar} x */ function Foo(x) {}",
        "new Bar(new Foo(undefined));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @extends {Bar} */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}"),
        JSTypeCreatorFromJSDoc.INHERITANCE_CYCLE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface @extends {Bar} */ function Foo() {}",
        "/** @interface @extends {Foo} */ function Bar() {}"),
        JSTypeCreatorFromJSDoc.INHERITANCE_CYCLE);

    typeCheck(
        "/** @constructor @extends {Foo} */ function Foo() {}",
        JSTypeCreatorFromJSDoc.INHERITANCE_CYCLE);
  }

  public void testInvalidInitOfInterfaceProps() throws Exception {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function T() {};",
        "T.prototype.x = function() { return 'foo'; }"),
        TypeCheck.INTERFACE_METHOD_NOT_EMPTY);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I() {};",
        "/** @type {number} */",
        "I.prototype.n = 123;"),
        GlobalTypeInfo.INVALID_INTERFACE_PROP_INITIALIZER);
  }

  public void testInterfaceSingleInheritance() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I() {}",
        "/** @type {string} */ I.prototype.prop;",
        "/** @constructor @implements{I} */ function C() {}"),
        TypeValidator.INTERFACE_METHOD_NOT_IMPLEMENTED);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I() {}",
        "/** @param {number} x */",
        "I.prototype.method = function(x) {};",
        "/** @constructor @implements{I} */ function C() {}"),
        TypeValidator.INTERFACE_METHOD_NOT_IMPLEMENTED);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function IParent() {}",
        "/** @type {number} */ IParent.prototype.prop;",
        "/** @interface @extends{IParent} */ function IChild() {}",
        "/** @constructor @implements{IChild} */",
        "function C() { this.prop = 5; }",
        "(new C).prop < 'adsf';"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function IParent() {}",
        "/** @type {number} */ IParent.prototype.prop;",
        "/** @interface @extends{IParent} */ function IChild() {}",
        "/** @constructor @implements{IChild} */",
        "function C() { this.prop = 'str'; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() { /** @type {number} */ this.prop = 123; }",
        "/** @constructor @extends {Parent} */ function Child() {}",
        "(new Child).prop = 321;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() { /** @type {number} */ this.prop = 123; }",
        "/** @constructor @extends {Parent} */ function Child() {}",
        "(new Child).prop = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I() {}",
        "/** @param {number} x */",
        "I.prototype.method = function(x, y) {};",
        "/** @constructor @implements{I} */ function C() {}",
        "/** @param {string} y */",
        "C.prototype.method = function(x, y) {};",
        "(new C).method(5, 6);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I() {}",
        "/** @param {number} x */",
        "I.prototype.method = function(x, y) {};",
        "/** @constructor @implements{I} */ function C() {}",
        "/** @param {string} y */",
        "C.prototype.method = function(x, y) {};",
        "(new C).method('asdf', 'fgr');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I() {}",
        "/** @param {number} x */",
        "I.prototype.method = function(x) {};",
        "/** @constructor @implements{I} */ function C() {}",
        "C.prototype.method = function(x) {};",
        "(new C).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I1() {}",
        "/** @param {number} x */ I1.prototype.method = function(x, y) {};",
        "/** @interface */ function I2() {}",
        "/** @param {string} y */ I2.prototype.method = function(x, y) {};",
        "/** @constructor @implements{I1} @implements{I2} */ function C(){}",
        "C.prototype.method = function(x, y) {};",
        "(new C).method('asdf', 'fgr');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I1() {}",
        "/** @param {number} x */ I1.prototype.method = function(x, y) {};",
        "/** @interface */ function I2() {}",
        "/** @param {string} y */ I2.prototype.method = function(x, y) {};",
        "/** @constructor @implements{I1} @implements{I2} */ function C(){}",
        "C.prototype.method = function(x, y) {};",
        "(new C).method(1, 2);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I1() {}",
        "/** @param {number} x */ I1.prototype.method = function(x) {};",
        "/** @interface */ function I2() {}",
        "/** @param {string} x */ I2.prototype.method = function(x) {};",
        "/** @constructor @implements{I1} @implements{I2} */ function C(){}",
        // Type of C.method is @param {(string|number)}
        "C.prototype.method = function(x) {};"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I1() {}",
        "/** @param {number} x */ I1.prototype.method = function(x) {};",
        "/** @interface */ function I2() {}",
        "/** @param {string} x */ I2.prototype.method = function(x) {};",
        "/** @constructor @implements{I1} @implements{I2} */ function C(){}",
        // Type of C.method is @param {(string|number)}
        "C.prototype.method = function(x) {};",
        "(new C).method(true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I() {}",
        "/** @param {number} x */ I.prototype.method = function(x) {};",
        "/** @constructor */ function S() {}",
        "/** @param {string} x */ S.prototype.method = function(x) {};",
        "/** @constructor @implements{I} @extends{S} */ function C(){}",
        // Type of C.method is @param {(string|number)}
        "C.prototype.method = function(x) {};",
        "(new C).method(true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testInterfaceMultipleInheritanceNoCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function I1() {}",
        "I1.prototype.method = function(x) {};",
        "/** @interface */",
        "function I2() {}",
        "I2.prototype.method = function(x) {};",
        "/**",
        " * @interface",
        " * @extends {I1}",
        " * @extends {I2}",
        " */",
        "function I3() {}",
        "/** @constructor @implements {I3} */",
        "function Foo() {}",
        "Foo.prototype.method = function(x) {};"));
  }

  public void testInterfaceArgument() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function I() {}",
        "/** @param {number} x */",
        "I.prototype.method = function(x) {};",
        "/** @param {!I} x */",
        "function foo(x) { x.method('asdf'); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function IParent() {}",
        "/** @param {number} x */",
        "IParent.prototype.method = function(x) {};",
        "/** @interface @extends {IParent} */",
        "function IChild() {}",
        "/** @param {!IChild} x */",
        "function foo(x) { x.method('asdf'); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testExtendedInterfacePropertiesCompatibility() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */function Int0() {};",
        "/** @interface */function Int1() {};",
        "/** @type {number} */",
        "Int0.prototype.foo;",
        "/** @type {string} */",
        "Int1.prototype.foo;",
        "/** @interface \n @extends {Int0} \n @extends {Int1} */",
        "function Int2() {};"),
        TypeCheck.INCOMPATIBLE_EXTENDED_PROPERTY_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Parent1() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {number}",
        " */",
        "Parent1.prototype.method = function(x) {};",
        "/** @interface */",
        "function Parent2() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {string}",
        " */",
        "Parent2.prototype.method = function(x) {};",
        "/** @interface @extends {Parent1} @extends {Parent2} */",
        "function Child() {}"),
        TypeCheck.INCOMPATIBLE_EXTENDED_PROPERTY_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "/** @interface */",
        "function Parent1() {}",
        "/** @type {!Foo} */",
        "Parent1.prototype.obj;",
        "/** @interface */",
        "function Parent2() {}",
        "/** @type {!Bar} */",
        "Parent2.prototype.obj;",
        "/** @interface @extends {Parent1} @extends {Parent2} */",
        "function Child() {}"),
        TypeCheck.INCOMPATIBLE_EXTENDED_PROPERTY_TYPE);
  }

  public void testTwoLevelExtendedInterface() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */function Int0() {};",
        "/** @type {function()} */",
        "Int0.prototype.foo;",
        "/** @interface @extends {Int0} */function Int1() {};",
        "/** @constructor \n @implements {Int1} */",
        "function Ctor() {};"),
        TypeValidator.INTERFACE_METHOD_NOT_IMPLEMENTED);
  }

  public void testConstructorExtensions() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function I() {}",
        "/** @param {number} x */",
        "I.prototype.method = function(x) {};",
        "/** @constructor @extends{I} */ function C() {}",
        "C.prototype.method = function(x) {};",
        "(new C).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function I() {}",
        "/** @param {number} x */",
        "I.prototype.method = function(x, y) {};",
        "/** @constructor @extends{I} */ function C() {}",
        "/** @param {string} y */",
        "C.prototype.method = function(x, y) {};",
        "(new C).method('asdf', 'fgr');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testInterfaceAndConstructorInvalidConstructions() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @extends {Bar} */",
        "function Foo() {}",
        "/** @interface */",
        "function Bar() {}"),
        TypeCheck.CONFLICTING_EXTENDED_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @implements {Bar} */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {}"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @interface @implements {Foo} */",
        "function Bar() {}"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @interface @extends {Foo} */",
        "function Bar() {}"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);
  }

  public void testNot() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor */",
        "function Bar() { /** @type {string} */ this.prop = 'asdf'; }",
        "function f(/** (!Foo|!Bar) */ obj) {",
        "  if (!(obj instanceof Foo)) {",
        "    obj.prop - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(cond) {",
        "  var x = cond ? null : 123;",
        "  if (!(x === null)) { x - 5; }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){ this.prop = 123; }",
        "function f(/** Foo */ obj) {",
        "  if (!obj) { obj.prop; }",
        "}"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);
  }

  public void testNullability() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {Foo} x */",
        "function f(x) {}",
        "f(new Foo);"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){ this.prop = 123; }",
        "function f(/** Foo */ obj) { obj.prop; }"),
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function I() {}",
        "I.prototype.method = function() {};",
        "/** @param {I} x */",
        "function foo(x) { x.method(); }"),
        NewTypeInference.NULLABLE_DEREFERENCE);
  }

  public void testGetElem() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function C(){ /** @type {number} */ this.prop = 1; }",
        "(new C)['prop'] < 'asdf';"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, y) {",
        "  x < y;",
        "  ({})[y - 5];",
        "}",
        "f('asdf', 123);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // We don't see the warning here b/c the formal param x is assigned to a
    // string, and we use x's type at the end of the function to create the
    // summary.
    typeCheck(Joiner.on('\n').join(
        "function f(x, y) {",
        "  x < y;",
        "  ({})[y - 5];",
        "  x = 'asdf';",
        "}",
        "f('asdf', 123);"));

    typeCheck(Joiner.on('\n').join(
        "function f(x, y) {",
        "  ({})[y - 5];",
        "  x < y;",
        "}",
        "f('asdf', 123);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x['prop'] = 'str';",
        "  return x['prop'] - 5;",
        "}",
        "f({});"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("function f(/** ? */ o) { return o[0].prop; }");

    // TODO(blickly): The fact that this has no warnings is somewhat unpleasant.
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x['prop'] = 7;",
        "  var p = 'prop';",
        "  x[p] = 'str';",
        "  return x['prop'] - 5;",
        "}",
        "f({});"));
  }

  public void testNamespaces() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @constructor */ ns.C = function() {};",
        "ns.C();"),
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @param {number} x */ ns.f = function(x) {};",
        "ns.f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @constructor */ ns.C = function(){}",
        "ns.C.prototype.method = function(/** string */ x){};",
        "(new ns.C).method(5);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @const */ ns.ns2 = {};",
        "/** @constructor */ ns.ns2.C = function() {};",
        "ns.ns2.C();"),
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @const */ ns.ns2 = {};",
        "/** @constructor */ ns.ns2.C = function() {};",
        "ns.ns2.C.prototype.method = function(/** string */ x){};",
        "(new ns.ns2.C).method(11);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function C1(){}",
        "/** @constructor */ C1.C2 = function(){}",
        "C1.C2.prototype.method = function(/** string */ x){};",
        "(new C1.C2).method(1);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function C1(){};",
        "/** @constructor */ C1.prototype.C2 = function(){};",
        "(new C1).C2();"),
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @type {number} */ ns.N = 5;",
        "ns.N();"),
        TypeCheck.NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @type {number} */ ns.foo = 123;",
        "/** @type {string} */ ns.foo = '';"),
        GlobalTypeInfo.REDECLARED_PROPERTY,
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @type {number} */ ns.foo;",
        "/** @type {string} */ ns.foo;"),
        GlobalTypeInfo.REDECLARED_PROPERTY);

    // We warn for duplicate declarations even if they are the same type.
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @type {number} */ ns.foo;",
        "/** @type {number} */ ns.foo;"),
        GlobalTypeInfo.REDECLARED_PROPERTY);

    // Without the @const, we don't consider it a namespace and don't warn.
    typeCheck(Joiner.on('\n').join(
        "var ns = {};",
        "/** @type {number} */ ns.foo = 123;",
        "/** @type {string} */ ns.foo = '';"));

    // TODO(dimvar): warn about redeclared property
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "ns.x = 5;",
        "/** @type {string} */",
        "ns.x = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "ns.prop = 1;",
        "function f() { var /** string */ s = ns.prop; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testNamespacesInExterns() {
    typeCheckCustomExterns(
        DEFAULT_EXTERNS + Joiner.on('\n').join(
            "/** @const */ var ns = {};",
            "/** @type {number} */ ns.num;"),
        "var /** number */ n = ns.num;");

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + Joiner.on('\n').join(
            "/** @const */ var ns = {};",
            "/** @type {number} */ ns.num;"),
        "var /** string */ s = ns.num;",
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testDontInferNamespaces() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @const */ var x = ns;"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */ var e = { FOO : 5 };",
        "/** @const */ var x = e;"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @type {number} */ ns.n = 5;",
        "/** @const */ var x = ns.n;"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);
  }

  public void testDontInferUndeclaredFunctionReturn() {
    typeCheck(Joiner.on('\n').join(
        "function f() {}",
        "/** @const */ var x = f();"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "ns.f = function() {}",
        "/** @const */ var x = f();"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);
  }

  // public void testUndeclaredNamespaces() {
  //   typeCheck(Joiner.on('\n').join(
  //       "/** @constructor */ ns.Foo = function(){};",
  //       "ns.Foo.prototype.method = function(){};"),
  //       VarCheck.UNDEFINED_VAR_ERROR,
  //       VarCheck.UNDEFINED_VAR_ERROR);
  // }

  public void testNestedNamespaces() {
    // In the previous type inference, ns.subns did not need a
    // @const annotation, but we require it.
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.subns = {};",
        "/** @type {string} */",
        "ns.subns.n = 'str';",
        "function f() { ns.subns.n - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testNonnamespaceLooksLikeANamespace() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @type {Object} */",
        "ns.obj = null;",
        "function setObj() {",
        "  ns.obj = {};",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @type {Object} */",
        "ns.obj = null;",
        "function setObj() {",
        "  ns.obj = {};",
        "  ns.obj.str = 'str';",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @type {Object} */",
        "ns.obj = null;",
        "ns.obj = {};",
        "ns.obj.x = 'str';",
        "ns.obj.x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @type {Object} */",
        "ns.obj = null;",
        "ns.obj = { x : 1, y : 5};",
        "ns.obj.x = 'str';"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @type {Object} */",
        "ns.obj = null;",
        "ns.obj = { x : 1, y : 5};",
        "ns.obj.x = 'str';",
        "ns.obj.x - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testNamespacedObjectsDontCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @constructor */",
        "ns.Foo = function() {",
        "  ns.Foo.obj.value = ns.Foo.VALUE;",
        "};",
        "ns.Foo.obj = {};",
        "ns.Foo.VALUE = 128;"));
  }

  public void testRedeclaredNamespaces() {
    // TODO(blickly): Consider a warning if RHS doesn't contain ||
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = ns || {}",
        "/** @const */ var ns = ns || {}"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = ns || {}",
        "ns.subns = ns.subns || {}",
        "ns.subns = ns.subns || {}"));
  }

  public void testReferenceToNonexistentNamespace() {
    // typeCheck(
    //     "/** @constructor */ ns.Foo = function(){};",
    //     VarCheck.UNDEFINED_VAR_ERROR);

    // typeCheck(
    //     "ns.subns = {};",
    //     VarCheck.UNDEFINED_VAR_ERROR);

    // typeCheck(
    //     "/** @enum {number} */ ns.NUM = { N : 1 };",
    //     VarCheck.UNDEFINED_VAR_ERROR);

    // typeCheck(
    //     "/** @typedef {number} */ ns.NUM;",
    //     VarCheck.UNDEFINED_VAR_ERROR);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @constructor */ ns.subns.Foo = function(){};"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "ns.subns.subsubns = {};"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @enum {number} */ ns.subns.NUM = { N : 1 };"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @typedef {number} */ ns.subns.NUM;"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "Foo.subns.subsubns = {};"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "/** @constructor */ Foo.subns.Bar = function(){};"),
        TypeCheck.INEXISTENT_PROPERTY);
  }

  public void testThrow() {
    typeCheck("throw 123;");

    typeCheck("var msg = 'hello'; throw msg;");

    typeCheck(Joiner.on('\n').join(
        "function f(cond, x, y) {",
        "  if (cond) {",
        "    x < y;",
        "    throw 123;",
        "  } else {",
        "    x < 2;",
        "  }",
        "}"));

    typeCheck("throw (1 - 'asdf');", NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testQnameInJsdoc() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @constructor */ ns.C = function() {};",
        "/** @param {!ns.C} x */ function f(x) {",
        "  123, x.prop;",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);
  }

  public void testIncrementDecrements() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = { x : 5 };",
        "ns.x++; ++ns.x; ns.x--; --ns.x;"));

    typeCheck(
        "function f(ns) { --ns.x; }; f({x : 'str'})",
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testAndOr() {
    typeCheck("function f(x, y, z) { return x || y && z;}");

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, /** string */ y) {",
        "  var /** number */ n = x || y;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, /** string */ y) {",
        "  var /** number */ n = y || x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function /** number */ f(/** ?number */ x) {",
        "  return x || 42;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function /** (number|string) */ f(/** ?number */ x) {",
        "  return x || 'str';",
        "}"));
  }

  public void testNonStringComparisons() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (null == x) {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x == null) {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (null == x) {",
        "    var /** null */ y = x;",
        "    var /** undefined */ z = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (5 == x) {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (x == 5) {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (null == x) {",
        "  } else {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (x == null) {",
        "  } else {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (null != x) {",
        "  } else {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x != null) {",
        "  } else {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (5 != x) {",
        "  } else {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (x != 5) {",
        "  } else {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (null != x) {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {*} x */",
        "function f(x) {",
        "  if (x != null) {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testAnalyzeLoopsBwd() {
    typeCheck("for(;;);");

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  for (; x - 5 > 0; ) {}",
        "  x = undefined;",
        "}",
        "f(true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  while (x - 5 > 0) {}",
        "  x = undefined;",
        "}",
        "f(true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (x - 5 > 0) {}",
        "  x = undefined;",
        "}",
        "f(true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  do {} while (x - 5 > 0);",
        "  x = undefined;",
        "}",
        "f(true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testDontLoosenNominalTypes() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() { this.prop = 123; }",
        "function f(x) { if (x instanceof Foo) { var y = x.prop; } }"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() { this.prop = 123; }",
        "/** @constructor */ function Bar() { this.prop = 123; }",
        "function f(cond, x) {",
        "  x = cond ? new Foo : new Bar;",
        "  var y = x.prop;",
        "}"));
  }

  public void testFunctionsWithAbnormalExit() {
    typeCheck("function f(x) { x = 1; throw x; }");

    // TODO(dimvar): to fix these, we must collect all THROWs w/out an out-edge
    // and use the envs from them in the summary calculation. (Rare case.)

    // typeCheck(Joiner.on('\n').join(
    //     "function f(x) {",
    //     "  var y = 1;",
    //     "  x < y;",
    //     "  throw 123;",
    //     "}",
    //     "f('asdf');"),
    //     NewTypeInference.INVALID_ARGUMENT_TYPE);
    // typeCheck(Joiner.on('\n').join(
    //     "function f(x, cond) {",
    //     "  if (cond) {",
    //     "    var y = 1;",
    //     "    x < y;",
    //     "    throw 123;",
    //     "  }",
    //     "}",
    //     "f('asdf', 'whatever');"),
    //     NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testAssignAdd() {
    // Without a type annotation, we can't find the type error here.
    typeCheck(Joiner.on('\n').join(
        "function f(x, y) {",
        "  x < y;",
        "  var /** number */ z = 5;",
        "  z += y;",
        "}",
        "f('asdf', 5);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, y) {",
        "  x < y;",
        "  var z = 5;",
        "  z += y;",
        "}",
        "f('asdf', 5);"));

    typeCheck(
        "var s = 'asdf'; (s += 'asdf') - 5;",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("var s = 'asdf'; s += 5;");

    typeCheck("var b = true; b += 5;", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "var n = 123; n += 'asdf';", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "var s = 'asdf'; s += true;", NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testTypeCoercions() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** * */ x) {",
        "  var /** string */ s = !x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** * */ x) {",
        "  var /** string */ s = +x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** * */ x) {",
        "  var /** string */ s = '' + x;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** * */ x) {",
        "  var /** number */ s = '' + x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testSwitch() {
    typeCheck(
        "switch (1) { case 1: break; case 2: break; default: break; }");

    typeCheck(Joiner.on('\n').join(
        "switch (1) {",
        "  case 1:",
        "    1 - 'asdf';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "switch (1) {",
        "  default:",
        "    1 - 'asdf';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "switch (1 - 'asdf') {",
        "  case 1:",
        "    break;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "switch (1) {",
        "  case (1 - 'asdf'):",
        "    break;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** Foo */ x) {",
        "  switch (x) {",
        "    case null:",
        "      break;",
        "    default:",
        "      var /** !Foo */ y = x;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  switch (x) {",
        "    case 123:",
        "      x - 5;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** Foo */ x) {",
        "  switch (x) {",
        "    case null:",
        "    default:",
        "      var /** !Foo */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  switch (x) {",
        "    case null:",
        "      x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  switch (x) {",
        "    case null:",
        "      var /** undefined */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    // Tests for fall-through
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  switch (x) {",
        "    case 1: x - 5;",
        "    case 'asdf': x < 123; x < 'asdf'; break;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  switch (x) {",
        "    case 1: x - 5;",
        "    case 'asdf': break;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function g(/** number */ x) { return 5; }",
        "function f() {",
        "  switch (3) { case g('asdf'): return 123; }",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // TODO(dimvar): warn for type mismatch between label and condition
    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, /** string */ y) {",
        "  switch (y) { case x: ; }",
        "}"));
  }

  public void testForIn() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** string */ y) {",
        "  for (var x in { a: 1, b: 2 }) { y = x; }",
        "  x = 234;",
        "  return 123;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(y) {",
        "  var z = x + 234;",
        "  for (var x in { a: 1, b: 2 }) {}",
        "  return 123;",
        "}"),
        // VariableReferenceCheck.EARLY_REFERENCE,
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ y) {",
        "  for (var x in { a: 1, b: 2 }) { y = x; }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "function f(/** Object? */ o) { for (var x in o); }",
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck("for (var x in 123) ;", NewTypeInference.FORIN_EXPECTS_OBJECT);

    typeCheck(
        "var /** number */ x = 5; for (x in {a : 1});",
        NewTypeInference.FORIN_EXPECTS_STRING_KEY);

    typeCheck(Joiner.on('\n').join(
        "function f(/** undefined */ y) {",
        "  var x;",
        "  for (x in { a: 1, b: 2 }) { y = x; }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testTryCatch() {
    // typeCheck(
    //     "try { e; } catch (e) {}",
    //     VariableReferenceCheck.EARLY_REFERENCE);

    // typeCheck(
    //     "e; try {} catch (e) {}",
    //     VariableReferenceCheck.EARLY_REFERENCE);

    typeCheck("try {} catch (e) { e; }");
    // If the CFG can see that the TRY won't throw, it doesn't go to the catch.
    typeCheck("try {} catch (e) { 1 - 'asdf'; }");

    typeCheck(
        "try { throw 123; } catch (e) { 1 - 'asdf'; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "try { throw 123; } catch (e) {} finally { 1 - 'asdf'; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    // Outside of the catch block, e is unknown, like any other global variable.
    typeCheck(Joiner.on('\n').join(
        "try {",
        "  throw new Error();",
        "} catch (e) {}",
        "var /** number */ n = e;"));

    // // For this to pass, we must model local scopes properly.
    // typeCheck(Joiner.on('\n').join(
    //     "var /** string */ e = 'str';",
    //     "try {",
    //     "  throw new Error();",
    //     "} catch (e) {}",
    //     "e - 3;"),
    //     NewTypeInference.INVALID_OPERAND_TYPE);

    // typeCheck(
    //     "var /** string */ e = 'asdf'; try {} catch (e) {} e - 5;",
    //     VariableReferenceCheck.REDECLARED_VARIABLE);

    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  try {",
        "  } catch (e) {",
        "    return e.stack;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  try {",
        "    throw new Error();",
        "  } catch (e) {",
        "    var /** Error */ x = e;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  try {",
        "    throw new Error();",
        "  } catch (e) {",
        "    var /** number */ x = e;",
        "    var /** string */ y = e;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testIn() {
    typeCheck("(true in {});", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("('asdf' in 123);", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "var /** number */ n = ('asdf' in {});",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** { a: number } */ obj) {",
        "  if ('p' in obj) {",
        "    return obj.p;",
        "  }",
        "}",
        "f({ a: 123 });"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** { a: number } */ obj) {",
        "  if (!('p' in obj)) {",
        "    return obj.p;",
        "  }",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);
  }

  public void testDelprop() {
    typeCheck("delete ({ prop: 123 }).prop;");

    typeCheck(
        "var /** number */ x = delete ({ prop: 123 }).prop;",
        NewTypeInference.MISTYPED_ASSIGN_RHS);
    // We don't detect the missing property
    typeCheck("var obj = { a: 1, b: 2 }; delete obj.a; obj.a;");
  }

  public void testArrayLit() {
    typeCheck("[1, 2, 3 - 'asdf']", NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, y) {",
        "  x < y;",
        "  [y - 5];",
        "}",
        "f('asdf', 123);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testArrayAccesses() {
    typeCheck(
        "var a = [1,2,3]; a['str'];", NewTypeInference.NON_NUMERIC_ARRAY_INDEX);

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Array<number> */ arr, i) {",
        "  arr[i];",
        "}",
        "f([1, 2, 3], 'str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testRegExpLit() {
    typeCheck("/abc/");
  }

  public void testDifficultLvalues() {
    typeCheck(Joiner.on('\n').join(
        "function f() { return {}; }",
        "f().x = 123;"));

    typeCheck(Joiner.on('\n').join(
        "function f() { return {}; }",
        "f().ns = {};"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {number} */ this.a = 123; }",
        "/** @return {!Foo} */",
        "function retFoo() { return new Foo(); }",
        "function f(cond) {",
        "  (retFoo()).a = 'asdf';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "(new Foo).x += 123;"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {number} */ this.a = 123; }",
        "function f(cond, /** !Foo */ foo1) {",
        "  var /** { a: number } */ x = { a: 321 };",
        "  (cond ? foo1 : x).a = 'asdf';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "function f(obj) { obj[1 - 'str'] = 3; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "function f(/** undefined */ n, pname) { n[pname] = 3; }",
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);
  }

  public void testQuestionableUnionJsDoc() {
    // 'string|?' is the same as '?'
    typeCheck(
        "/** @type {string|?} */ var x;",
        JSTypeCreatorFromJSDoc.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "",
        "/**",
        " * @return {T|S}",
        " * @template T, S",
        " */",
        "function f(){};"));

    typeCheck("/** @param {(?)} x */ function f(x) {}");
  }

  public void testGenericsJsdocParsing() {
    typeCheck("/** @template T\n@param {T} x */ function f(x) {}");

    typeCheck(Joiner.on('\n').join(
        "/** @template T\n @param {T} x\n @return {T} */",
        "function f(x) { return x; };"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " * @param {T} x",
        " * @extends {Bar<T>} // error, Bar is not templatized ",
        " */",
        "function Foo(x) {}",
        "/** @constructor */",
        "function Bar() {}"),
        JSTypeCreatorFromJSDoc.INVALID_GENERICS_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " * @param {T} x",
        " */",
        "function Foo(x) {}",
        "/** @param {Foo<number, string>} x */",
        "function f(x) {}"),
        JSTypeCreatorFromJSDoc.INVALID_GENERICS_INSTANTIATION);

    typeCheck("/** @type {Array<number>} */ var x;");

    typeCheck("/** @type {Object<number>} */ var x;");

    typeCheck(
        "/** @template T\n@param {!T} x */ function f(x) {}",
        JSTypeCreatorFromJSDoc.BAD_JSDOC_ANNOTATION);
  }

  public void testPolymorphicFunctionInstantiation() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function id(x) { return x; }",
        "id('str') - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "f(123, 'asdf');"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {(T|null)} x",
        " * @return {(T|number)}",
        " */",
        "function f(x) { return x === null ? 123 : x; }",
        "/** @return {(null|undefined)} */ function g() { return null; }",
        "var /** (number|undefined) */ y = f(g());"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {(T|number)} x",
        " */",
        "function f(x) {}",
        "/** @return {*} */ function g() { return 1; }",
        "f(g());"),
        NewTypeInference.FAILED_TO_UNIFY);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function id(x) { return x; }",
        "/** @return {*} */ function g() { return 1; }",
        "id(g()) - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T, U",
        " * @param {T} x",
        " * @param {U} y",
        " * @return {U}",
        " */",
        "function f(x, y) { return y; }",
        "f(10, 'asdf') - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function g(x) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  f(x, 5);",
        "}",
        "g('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function g(/** ? */ x) {",
        "  /**",
        "   * @template T",
        "   * @param {(T|number)} x",
        "   */",
        "  function f(x) {}",
        "  f(x)",
        "}"));

    // TODO(blickly): Catching the INVALID_ARGUMENT_TYPE here requires
    // return-type unification.
    typeCheck(Joiner.on('\n').join(
        "function g(x) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @return {T}",
        "   */",
        "  function f(x) { return x; }",
        "  f(x) - 5;",
        "  x = 'asdf';",
        "}",
        "g('asdf');"));

    // Empty instantiations
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {(T|number)} x",
        " */",
        "function f(x) {}",
        "f(123);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {(T|null)} x",
        " * @param {(T|number)} y",
        " */",
        "function f(x, y) {}",
        "f(null, 'str');"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){};",
        "/**",
        " * @template T",
        " * @param {(T|Foo)} x",
        " * @param {(T|number)} y",
        " */",
        "function f(x, y) {}",
        "f(new Foo(), 'str');"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(T):T} f",
        " * @param {T} x",
        " */",
        "function apply(f, x) { return f(x); }",
        "/** @type {string} */",
        "var out;",
        "var result = apply(function(x){ out = x; return x; }, 0);"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/** @template T */",
        "function f(/** T */ x, /** T */ y) {}",
        "f(1, 'str');"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/** @template T */",
        "function /** T */ f(/** T */ x) { return x; }",
        "f('str') - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {",
        "  /** @constructor */",
        "  function Foo() {",
        "    /** @type {T} */",
        "    this.prop = x;",
        "  }",
        "  return (new Foo()).prop;",
        "}",
        "f('asdf') - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {*} x",
        " */",
        "function f(x) {}",
        "f(123);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo() {}",
        "/**",
        " * @template U",
        " * @param {function(U)} x",
        " */",
        "Foo.prototype.f = function(x) { this.f(x); };"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(T)} x",
        " */",
        "function f(x) {}",
        "function g(x) {}",
        "f(g);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(T=)} x",
        " */",
        "function f(x) {}",
        "function g(/** (number|undefined) */ x) {}",
        "f(g);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(...T)} x",
        " */",
        "function f(x) {}",
        "function g() {}",
        "f(g);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {!Array<T>} arr",
        " * @param {?function(this:S, T, number, ?) : boolean} f",
        " * @param {S=} opt_obj",
        " * @return {T|null}",
        " * @template T,S",
        " */",
        "function gaf(arr, f, opt_obj) {",
        "  return null;",
        "};",
        "/** @type {number|null} */",
        "var x = gaf([1, 2, 3], function(x, y, z) { return true; });"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(T):boolean} x",
        " */",
        "function f(x) {}",
        "f(function(x) { return 'asdf'; });"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {function(T)} y",
        " */",
        "function f(x, y) {}",
        "f(123, function(x) { var /** string */ s = x; });"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {}",
        "var y = null;",
        "if (!y) {",
        "} else {",
        "  f(y)",
        "}"));
  }

  public void testGenericReturnType() {
    typeCheck(Joiner.on('\n').join(
        "/** @return {T|string} @template T */",
        "function f() { return 'str'; }"));
  }

  public void testUnificationWithGenericUnion() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @template T */ function Foo(){}",
        "/**",
        " * @template T",
        " * @param {!Array<T>|!Foo<T>} arr",
        " * @return {T}",
        " */",
        "function get(arr) {",
        "  return arr[0];",
        "}",
        "var /** null */ x = get([5]);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {Array<T>} arr",
        " * @return {T|undefined}",
        " */",
        "function get(arr) {",
        "  if (arr === null || arr.length === 0) {",
        "    return undefined;",
        "  }",
        "  return arr[0];",
        "}",
        "var /** (number|undefined) */ x = get([5]);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {Array<T>} arr",
        " * @return {T|undefined}",
        " */",
        "function get(arr) {",
        "  if (arr === null || arr.length === 0) {",
        "    return undefined;",
        "  }",
        "  return arr[0];",
        "}",
        "var /** null */ x = get([5]);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @template U */ function Foo(/** U */ x){}",
        "/**",
        " * @template T",
        " * @param {U|!Array<T>} arr",
        " * @return {U}",
        " */",
        "Foo.prototype.get = function(arr, /** ? */ opt_arg) {",
        "  return opt_arg;",
        "}",
        "var /** null */ x = (new Foo('str')).get([5], 1);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @template U */ function Foo(/** U */ x){}",
        "/**",
        " * @template T",
        " * @param {U|!Array<T>} arr",
        " * @return {U}",
        " */",
        "Foo.prototype.get = function(arr, /** ? */ opt_arg) {",
        "  return opt_arg;",
        "}",
        "Foo.prototype.f = function() {",
        "  var /** null */ x = this.get([5], 1);",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " */",
        "function Bar() {}",
        "/** @constructor */",
        "function Foo() {}",
        "/**",
        " * @template T",
        " * @param {!Bar<(!Bar<T>|!Foo)>} x",
        " */",
        "function f(x) {}",
        "f(/** @type {!Bar<!Bar<number>>} */ (new Bar));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/**",
        " * @template T",
        " * @param {T|null} x",
        " */",
        "function f(x) {}",
        "f(new Foo);"));
  }

  public void testBoxedUnification() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {V} value",
        " * @constructor",
        " * @template V",
        " */",
        "function Box(value) {};",
        "/**",
        " * @constructor",
        " * @param {K} key",
        " * @param {V} val",
        " * @template K, V",
        " */",
        "function Map(key, val) {};",
        "/**",
        " * @param {!Map<K, (V | !Box<V>)>} inMap",
        " * @constructor",
        " * @template K, V",
        " */",
        "function WrappedMap(inMap){};",
        "/** @return {(boolean |!Box<boolean>)} */",
        "function getUnion(/** ? */ u) { return u; }",
        "var inMap = new Map('asdf', getUnion(123));",
        "/** @param {!WrappedMap<string, boolean>} x */",
        "function getWrappedMap(x) {}",
        "getWrappedMap(new WrappedMap(inMap));"));
  }


  public void testUnification() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){};",
        "/** @constructor */ function Bar(){};",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function id(x) { return x; }",
        "var /** Bar */ x = id(new Foo);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function id(x) { return x; }",
        "id({}) - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function id(x) { return x; }",
        "var /** (number|string) */ x = id('str');"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** * */ a, /** string */ b) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  f(a, b);",
        "}"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "function f(/** string */ b) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  f({p:5, r:'str'}, {p:20, r:b});",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** string */ b) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  f({r:'str'}, {p:20, r:b});",
        "}"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "function g(x) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  var /** boolean */ y = true;",
        "  f(x, y);",
        "}",
        "g('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {number} y",
        " */",
        "function f(x, y) {}",
        "f(123, 'asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo() {}",
        "/**",
        " * @template T",
        " * @param {Foo<T>} x",
        " */",
        "function takesFoo(x) {}",
        "takesFoo(undefined);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T|undefined} x",
        " */",
        "function f(x) {}",
        "/**",
        " * @template T",
        " * @param {T|undefined} x",
        " */",
        "function g(x) { f(x); }"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T|undefined} x",
        " * @return {T}",
        " */",
        "function f(x) {",
        "  if (x === undefined) {",
        "    throw new Error('');",
        "  }",
        "  return x;",
        "}",
        "/**",
        " * @template T",
        " * @param {T|undefined} x",
        " * @return {T}",
        " */",
        "function g(x) { return f(x); }",
        "g(123) - 5;"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T|undefined} x",
        " * @return {T}",
        " */",
        "function f(x) {",
        "  if (x === undefined) {",
        "    throw new Error('');",
        "  }",
        "  return x;",
        "}",
        "/**",
        " * @template T",
        " * @param {T|undefined} x",
        " * @return {T}",
        " */",
        "function g(x) { return f(x); }",
        "g(123) < 'asdf';"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testUnifyObjects() {
    typeCheck(Joiner.on('\n').join(
        "function f(b) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  f({p:5, r:'str'}, {p:20, r:b});",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(b) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  f({p:20, r:b}, {p:5, r:'str'});",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function g(x) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  f({prop: x}, {prop: 5});",
        "}",
        "g('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function g(x, cond) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  var y = cond ? {prop: 'str'} : {prop: 5};",
        "  f({prop: x}, y);",
        "}",
        "g({}, true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function g(x, cond) {",
        "  /**",
        "   * @template T",
        "   * @param {T} x",
        "   * @param {T} y",
        "   */",
        "  function f(x, y) {}",
        "  /** @type {{prop : (string | number)}} */",
        "  var y = cond ? {prop: 'str'} : {prop: 5};",
        "  f({prop: x}, y);",
        "}",
        "g({}, true);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {{a: number, b: T}} x",
        " * @return {T}",
        " */",
        "function f(x) { return x.b; }",
        "f({a: 1, b: 'asdf'}) - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @return {T}",
        " */",
        "function f(x) { return x.b; }",
        "f({b: 'asdf'}) - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testFunctionTypeUnifyUnknowns() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "/** @type {function(number)} */",
        "function g(x) {}",
        "/** @type {function(?)} */",
        "function h(x) {}",
        "f(g, h);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "/** @type {function(number)} */",
        "function g(x) {}",
        "/** @type {function(string)} */",
        "function h(x) {}",
        "f(g, h);"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "/** @type {function(number)} */",
        "function g(x) {}",
        "/** @type {function(?, string)} */",
        "function h(x, y) {}",
        "f(g, h);"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "/** @type {function(number=, ...string)} */",
        "function g(x) {}",
        "/** @type {function(number=, ...?)} */",
        "function h(x) {}",
        "f(g, h);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "/** @type {function(number):number} */",
        "function g(x) { return 1; }",
        "/** @type {function(?):string} */",
        "function h(x) { return ''; }",
        "f(g, h);"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "/** @constructor */ function Foo() {}",
        "/** @type {function(new:Foo)} */",
        "function g() {}",
        "/** @type {function(new:Foo)} */",
        "function h() {}",
        "f(g, h);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "/** @constructor */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "/** @type {function(this:Foo)} */",
        "function g() {}",
        "/** @type {function(this:Bar)} */",
        "function h() {}",
        "f(g, h);"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);
  }

  public void testInstantiationInsideObjectTypes() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template U",
        " * @param {U} y",
        " */",
        "function g(y) {",
        "  /**",
        "   * @template T",
        "   * @param {{a: U, b: T}} x",
        "   * @return {T}",
        "   */",
        "  function f(x) { return x.b; }",
        "  f({a: y, b: 'asdf'}) - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template U",
        " * @param {U} y",
        " */",
        "function g(y) {",
        "  /**",
        "   * @template T",
        "   * @param {{b: T}} x",
        "   * @return {T}",
        "   */",
        "  function f(x) { return x.b; }",
        "  f({b: y}) - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testInstantiateInsideFunctionTypes() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {function(T):T} fun",
        " */",
        "function f(x, fun) {}",
        "function g(x) { return x - 5; }",
        "f('asdf', g);"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(T):number} fun",
        " */",
        "function f(fun) {}",
        "function g(x) { return 'asdf'; }",
        "f(g);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(T=)} fun",
        " */",
        "function f(fun) {}",
        "/** @param{string=} x */ function g(x) {}",
        "f(g);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(...T)} fun",
        " */",
        "function f(fun) {}",
        "/** @param {...number} var_args */ function g(var_args) {}",
        "f(g);"));
  }

  public void testPolymorphicFuncallsFromDifferentScope() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function id(x) { return x; }",
        "function g() {",
        "  id('asdf') - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {number} y",
        " */",
        "function f(x, y) {}",
        "function g() {",
        "  f('asdf', 'asdf');",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "function g() {",
        "  f(123, 'asdf');",
        "}"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);
  }

  public void testOpacityOfTypeParameters() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {",
        "  x - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {{ a: T }} x",
        " */",
        "function f(x) {",
        "  x.a - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {function(T):T} fun",
        " */",
        "function f(x, fun) {",
        "  fun(x) - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function f(x) {",
        "  return 5;",
        "}"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {",
        "  var /** ? */ y = x;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {(T|number)}",
        " */",
        "function f(x) {",
        "  var y;",
        "  if (1 < 2) {",
        "    y = x;",
        "  } else {",
        "    y = 123;",
        "  }",
        "  return y;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {(T|number)}",
        " */",
        "function f(x) {",
        "  var y;",
        "  if (1 < 2) {",
        "    y = x;",
        "  } else {",
        "    y = 123;",
        "  }",
        "  return y;",
        "}",
        "f(123) - 5;"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {(T|number)}",
        " */",
        "function f(x) {",
        "  var y;",
        "  if (1 < 2) {",
        "    y = x;",
        "  } else {",
        "    y = 123;",
        "  }",
        "  return y;",
        "}",
        "var /** (number|boolean) */ z = f('asdf');"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {",
        "  var /** T */ y = x;",
        "  y - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T, U",
        " * @param {T} x",
        " * @param {U} y",
        " */",
        "function f(x, y) {",
        "  x = y;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testGenericClassInstantiation() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) {}",
        "/** @param {T} y */",
        "Foo.prototype.bar = function(y) {}",
        "new Foo('str').bar(5)"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) {}",
        "/** @type {function(T)} y */",
        "Foo.prototype.bar = function(y) {};",
        "new Foo('str').bar(5)"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) { /** @type {T} */ this.x = x; }",
        "/** @return {T} */",
        "Foo.prototype.bar = function() { return this.x; };",
        "new Foo('str').bar() - 5"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) { /** @type {T} */ this.x = x; }",
        "/** @type {function() : T} */",
        "Foo.prototype.bar = function() { return this.x; };",
        "new Foo('str').bar() - 5"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) {}",
        "/** @type {function(this:Foo<T>, T)} */",
        "Foo.prototype.bar = function(x) { this.x = x; };",
        "new Foo('str').bar(5)"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) {}",
        "/** @param {!Foo<number>} x */",
        "function f(x) {}",
        "f(new Foo(7));"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) {}",
        "/** @param {Foo<number>} x */",
        "function f(x) {}",
        "f(new Foo('str'));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) {}",
        "/** @param {T} x */",
        "Foo.prototype.method = function(x) {};",
        "/** @param {!Foo<number>} x */",
        "function f(x) { x.method('asdf'); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo() {}",
        "/** @param {T} x */",
        "Foo.prototype.method = function(x) {};",
        "var /** @type {Foo<string>} */ foo = null;",
        "foo.method('asdf');"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);
  }

  public void testLooserCheckingForInferredProperties() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo(x) { this.prop = x; }",
        "function f(/** !Foo */ obj) {",
        "  obj.prop = true ? 1 : 'asdf';",
        "  obj.prop - 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo(x) { this.prop = x; }",
        "function f(/** !Foo */ obj) {",
        "  if (!(typeof obj.prop == 'number')) {",
        "    obj.prop < 'asdf';",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo(x) { this.prop = x; }",
        "function f(/** !Foo */ obj) {",
        "  obj.prop = true ? 1 : 'asdf';",
        "  obj.prop - 5;",
        "  obj.prop < 'asdf';",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function /** string */ f(/** ?number */ x) {",
        "  var o = { prop: 'str' };",
        "  if (x) {",
        "    o.prop = x;",
        "  }",
        "  return o.prop;",
        "}"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);
  }

  public void testInheritanceWithGenerics() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function I() {}",
        "/** @param {T} x */",
        "I.prototype.bar = function(x) {};",
        "/** @constructor @implements {I<number>} */",
        "function Foo() {}",
        "Foo.prototype.bar = function(x) {};",
        "(new Foo).bar(123);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function I() {}",
        "/** @param {T} x */",
        "I.prototype.bar = function(x) {};",
        "/** @constructor @implements {I<number>} */",
        "function Foo() {}",
        "Foo.prototype.bar = function(x) {};",
        "(new Foo).bar('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function I() {}",
        "/** @param {T} x */",
        "I.prototype.bar = function(x) {};",
        "/** @constructor @implements {I<number>} */",
        "function Foo() {}",
        "/** @override */",
        "Foo.prototype.bar = function(x) {};",
        "new Foo().bar('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function I() {}",
        "/** @param {T} x */",
        "I.prototype.bar = function(x) {};",
        "/**",
        " * @template U",
        " * @constructor",
        " * @implements {I<U>}",
        " * @param {U} x",
        " */",
        "function Foo(x) {}",
        "Foo.prototype.bar = function(x) {};{}",
        "new Foo(5).bar('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function I() {}",
        "/** @param {T} x */",
        "I.prototype.bar = function(x) {};",
        "/** @constructor @implements {I<number>} */",
        "function Foo() {}",
        "Foo.prototype.bar = function(x) {};",
        "/** @param {I<string>} x */ function f(x) {};",
        "f(new Foo());"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function I() {}",
        "/** @param {T} x */",
        "I.prototype.bar = function(x) {};",
        "/** @constructor @implements {I<number>} */",
        "function Foo() {}",
        "/** @param {string} x */",
        "Foo.prototype.bar = function(x) {};"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function I() {}",
        "/** @param {T} x */",
        "I.prototype.bar = function(x) {};",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor @implements {I<number>}",
        " */",
        "function Foo(x) {}",
        "/** @param {T} x */",
        "Foo.prototype.bar = function(x) {};"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " */",
        "function Foo() {}",
        "/** @param {T} x */",
        "Foo.prototype.method = function(x) {};",
        "/**",
        " * @template T",
        " * @constructor",
        " * @extends {Foo<T>}",
        " * @param {T} x",
        " */",
        "function Bar(x) {}",
        "/** @param {number} x */",
        "Bar.prototype.method = function(x) {};"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " */",
        "function High() {}",
        "/** @param {Low<T>} x */",
        "High.prototype.method = function(x) {};",
        "/**",
        " * @template T",
        " * @constructor",
        " * @extends {High<T>}",
        " */",
        "function Low() {}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " */",
        "function High() {}",
        "/** @param {Low<number>} x */",
        "High.prototype.method = function(x) {};",
        "/**",
        " * @template T",
        " * @constructor",
        " * @extends {High<T>}",
        " */",
        "function Low() {}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " */",
        "function High() {}",
        "/** @param {Low<T>} x */ // error, low is not templatized",
        "High.prototype.method = function(x) {};",
        "/**",
        " * @constructor",
        " * @extends {High<number>}",
        " */",
        "function Low() {}"),
        JSTypeCreatorFromJSDoc.INVALID_GENERICS_INSTANTIATION);

    // BAD INHERITANCE, WE DON'T HAVE A WARNING TYPE FOR THIS
    // TODO(dimvar): fix
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function I() {}",
        "/**",
        " * @template T",
        " * @constructor",
        " * @implements {I<T>}",
        " * @extends {Bar}",
        " */",
        "function Foo(x) {}",
        "/**",
        " * @constructor",
        " * @implements {I<number>}",
        " */",
        "function Bar(x) {}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function Foo() {}",
        "/** @constructor @implements {Foo<number>} */",
        "function A() {}",
        "var /** Foo<number> */ x = new A();"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "High.prototype.method = function (x) {};",
        "/** @constructor @implements {High} */",
        "function Low() {}",
        "Low.prototype.method = function (x) {",
        "  return x;",
        "};",
        "(new Low).method(123) - 123;"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "High.prototype.method = function (x) {};",
        "/** @constructor @implements {High} */",
        "function Low() {}",
        "Low.prototype.method = function (x) {",
        "  return x;",
        "};",
        "(new Low).method('str') - 123;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @interface",
        " */",
        "function High() {}",
        "/** @return {T} */",
        "High.prototype.method = function () {};",
        "/** @constructor @implements {High} */",
        "function Low() {}",
        "Low.prototype.method = function () { return /** @type {?} */ (null); };",
        "(new Low).method() - 123;",
        "(new Low).method() < 'asdf';"));
  }

  public void testGenericsSubtyping() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "Parent.prototype.method = function(x, y){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {number} x",
        " * @param {number} y",
        " */",
        "Child.prototype.method = function(x, y){};"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "Parent.prototype.method = function(x, y){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {?} x",
        " * @param {number} y",
        " */",
        "Child.prototype.method = function(x, y){};"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "Parent.prototype.method = function(x, y){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {*} x",
        " * @param {*} y",
        " */",
        "Child.prototype.method = function(x, y){};"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "Parent.prototype.method = function(x, y){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {?} x",
        " * @param {?} y",
        " */",
        "Child.prototype.method = function(x, y){};"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {?} x",
        " * @return {?}",
        " */",
        "Child.prototype.method = function(x){ return x; };"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {*} x",
        " * @return {?}",
        " */",
        "Child.prototype.method = function(x){ return x; };"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {*} x",
        " * @return {*}",
        " */",
        "Child.prototype.method = function(x){ return x; };"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {number} x",
        " * @return {number}",
        " */",
        "Child.prototype.method = function(x){ return x; };"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {?} x",
        " * @return {*}",
        " */",
        "Child.prototype.method = function(x){ return x; };"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template T",
        " * @param {function(T, T) : boolean} x",
        " */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @param {function(number, number) : boolean} x",
        " */",
        "Child.prototype.method = function(x){ return x; };"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {}",
        "/** @param {function(number, number)} x */",
        "function g(x) {}",
        "g(f);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {}",
        "/** @param {function()} x */",
        "function g(x) {}",
        "g(f);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Parent() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "Parent.prototype.method = function(x) {};",
        "/**",
        " * @constructor",
        " * @implements {Parent}",
        " */",
        "function Child() {}",
        "/**",
        " * @template U",
        " * @param {U} x",
        " */",
        "Child.prototype.method = function(x) {};"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/** @param {string} x */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "Child.prototype.method = function(x){};"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/** @param {*} x */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "Child.prototype.method = function(x){};"));

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/** @param {?} x */",
        "Parent.prototype.method = function(x){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "Child.prototype.method = function(x){};"));

    // This shows a bug in subtyping of generic functions.
    // We don't catch the invalid prop override.
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @param {string} x",
        " * @param {number} y",
        " */",
        "Parent.prototype.method = function(x, y){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "Child.prototype.method = function(x, y){};"));

    // This shows a bug in subtyping of generic functions.
    // We don't catch the invalid prop override.
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Parent() {}",
        "/**",
        " * @template A, B",
        " * @param {A} x",
        " * @param {B} y",
        " * @return {A}",
        " */",
        "Parent.prototype.method = function(x, y){};",
        "/** @constructor @implements {Parent} */",
        "function Child() {}",
        "/**",
        " * @template A, B",
        " * @param {A} x",
        " * @param {B} y",
        " * @return {B}",
        " */",
        "Child.prototype.method = function(x, y){ return y; };"));
  }

  public void testGenericsVariance() {
    // Array generic parameter is co-variant
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "var /** Array<Foo> */ a = [new Bar];"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {!Array<number|string>} x",
        " * @return {!Array<number>}",
        " */",
        "function f(x) {",
        "  return /** @type {!Array<number>} */ (x);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "var /** Array<Bar> */ a = [new Foo];"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {!Array<null|T>} y",
        " */",
        "function f(x, y) {}",
        "f(new Foo, [new Foo]);"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @param {T} x @template T */ function Gen(x){}",
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "var /** Gen<Foo> */ a = new Gen(new Bar);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @param {T} x @template T */ function Gen(x){}",
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "var /** Gen<Bar> */ a = new Gen(new Foo);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testInferredArrayGenerics() {
    typeCheck(
        "/** @const */ var x = [];", GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(
        "/** @const */ var x = [1, 'str'];",
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "/** @const */ var x = [new Foo, new Bar];"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(
        "var /** Array<string> */ a = [1, 2];",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var arr = [];",
        "var /** Array<string> */ as = arr;"));

    typeCheck(Joiner.on('\n').join(
        "var arr = [1, 2, 3];",
        "var /** Array<string> */ as = arr;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "var /** Array<string> */ a = [new Foo, new Foo];"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "var /** Array<Foo> */ a = [new Foo, new Bar];"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "var /** Array<Bar> */ a = [new Foo, new Bar];"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var x = [1, 2, 3];",
        "function g() { var /** Array<string> */ a = x; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "/** @const */ var x = [new Foo, new Foo];",
        "function g() { var /** Array<Bar> */ a = x; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testSpecializedInstanceofCantGoToBottom() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "ns.f = function() {};",
        "if (ns.f instanceof Function) {}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "/** @const */ var ns = {};",
        "ns.f = new Foo;",
        "if (ns.f instanceof Foo) {}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "/** @constructor */ function Bar(){}",
        "/** @const */ var ns = {};",
        "ns.f = new Foo;",
        "if (ns.f instanceof Bar) {}"));
  }

  public void testDeclaredGenericArrayTypes() {
    typeCheck(Joiner.on('\n').join(
        "/** @type {Array<string>} */",
        "var arr = ['str'];",
        "arr[0]++;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var arr = ['str'];",
        "arr[0]++;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function foo (/** Array<string> */ a) {}",
        "/** @type {Array<number>} */",
        "var b = [1];",
        "foo(b);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function foo (/** Array<string> */ a) {}",
        "foo([1]);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @type {!Array<number>} */",
        "var arr = [1, 2, 3];",
        "arr[0] = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @type {!Array<number>} */",
        "var arr = [1, 2, 3];",
        "arr['0'] = 'str';"));

    // We warn here even though the declared type of the lvalue includes null.
    typeCheck(Joiner.on('\n').join(
        "/** @type {Array<number>} */",
        "var arr = [1, 2, 3];",
        "arr[0] = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** Array<number> */ arr) {",
        "  arr[0] = 'str';",
        "}"),
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var arr = [1, 2, 3];",
        "arr[0] = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var arr = [1, 2, 3];",
        "arr[0] = 'str';"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Super(){}",
        "/** @constructor @extends {Super} */ function Sub(){}",
        "/** @type {!Array<Super>} */ var arr = [new Sub];",
        "arr[0] = new Super;"));

    typeCheck(Joiner.on('\n').join(
        "/** @type {Array<number>} */ var arr = [];",
        "arr[0] = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @type {Array<number>} */ var arr = [];",
        "(function (/** Array<string> */ x){})(arr);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function /** string */ f(/** !Array<number> */ arr) {",
        "  return arr[0];",
        "}"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    // TODO(blickly): Would be nice if we caught the MISTYPED_ASSIGN_RHS here
    typeCheck(Joiner.on('\n').join(
        "var arr = [];",
        "arr[0] = 5;",
        "var /** Array<string> */ as = arr;"));
  }

  public void testInferConstTypeFromGoogGetMsg() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var s = goog.getMsg('asdf');",
        "s - 1;"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testInferConstTypeFromQualifiedName() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {}",
        "/** @return {string} */ ns.f = function() { return 'str'; };",
        "/** @const */ var s = ns.f();",
        "function f() {",
        "  s - 1;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testInferConstTypeFromGenerics() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function f(x) { return x; }",
        "/** @const */ var x = f(5);",
        "function g() { var /** null */ n = x; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @constructor",
        " */",
        "function Foo(x) {}",
        "/** @const */ var foo_str = new Foo('str');",
        "function g() { var /** !Foo<number> */ foo_num = foo_str; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function f(x) { return x; }",
        "/** @const */ var x = f(f ? 'str' : 5);"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " * @return {T}",
        " */",
        "function f(x, y) { return true ? y : x; }",
        "/** @const */ var x = f(5, 'str');",
        "function g() { var /** null */ n = x; }"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE,
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function f(x) { return x; }",
        "/** @const */",
        "var y = f(1, 2);"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE,
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function f(x) { return x; }",
        "/** @const */",
        "var y = f();"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE,
        TypeCheck.WRONG_ARGUMENT_COUNT);
  }

  public void testDifficultClassGenericsInstantiation() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " * @param {T} x",
        " */",
        "function Foo(x) {}",
        "/** @param {Bar<T>} x */",
        "Foo.prototype.method = function(x) {};",
        "/**",
        " * @template T",
        " * @constructor",
        " * @param {T} x",
        " */",
        "function Bar(x) {}",
        "/** @param {Foo<T>} x */",
        "Bar.prototype.method = function(x) {};",
        "(new Foo(123)).method(new Bar('asdf'));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " * @param {T} x",
        " */",
        "function Foo(x) {}",
        "/** @param {Foo<Foo<T>>} x */",
        "Foo.prototype.method = function(x) {};",
        "(new Foo(123)).method(new Foo(new Foo('asdf')));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface\n @template T */function A() {};",
        "/** @return {T} */A.prototype.foo = function() {};",
        "/** @interface\n @template U\n @extends {A<U>} */function B() {};",
        "/** @constructor\n @implements {B<string>} */function C() {};",
        "/** @return {string}\n @override */",
        "C.prototype.foo = function() { return 123; };"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    // Polymorphic method on a generic class.
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " * @param {T} x",
        " */",
        "function Foo(x) {}",
        "/**",
        " * @template U",
        " * @param {U} x",
        " * @return {U}",
        " */",
        "Foo.prototype.method = function(x) { return x; };",
        "(new Foo(123)).method('asdf') - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    // typeCheck(Joiner.on('\n').join(
    //     "/**",
    //     " * @template T",
    //     " * @constructor",
    //     " */",
    //     "function Foo() {}",
    //     "/** @param {T} x */",
    //     "Foo.prototype.method = function(x) {};",
    //     "",
    //     "/**",
    //     " * @template T",
    //     " * @constructor",
    //     " * @extends {Foo<T>}",
    //     " * @param {T} x",
    //     " */",
    //     "function Bar(x) {}",
    //     // Invalid instantiation here, must be T, o/w bugs like the call to f
    //     "/** @param {number} x */",
    //     "Bar.prototype.method = function(x) {};",
    //     "",
    //     "/** @param {!Foo<string>} x */",
    //     "function f(x) { x.method('sadf'); };",
    //     "f(new Bar('asdf'));"),
    //     NewTypeInference.FAILED_TO_UNIFY);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T,U",
        " */",
        "function Foo() {}",
        "Foo.prototype.m1 = function() {",
        "  this.m2(123);",
        "};",
        "/**",
        " * @template U",
        " * @param {U} x",
        " */",
        "Foo.prototype.m2 = function(x) {};"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T, U",
        " */",
        "function Foo() {}",
        "/**",
        " * @template T", // shadows Foo#T, U still visible
        " * @param {T} x",
        " * @param {U} y",
        " */",
        "Foo.prototype.method = function(x, y) {};",
        "var obj = /** @type {!Foo<number, number>} */ (new Foo);",
        "obj.method('asdf', 123);", // OK
        "obj.method('asdf', 'asdf');"), // warning
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function High() {}",
        "/** @param {T} x */",
        "High.prototype.method = function(x) {};",
        "/**",
        " * @constructor",
        " * @implements {High<number>}",
        " */",
        "function Low() {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "Low.prototype.method = function(x) {};"));
  }

  public void testNominalTypeUnification() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T, U",
        " * @param {T} x",
        " */",
        "function Foo(x) {}",
        "/**",
        " * @template T",
        // {!Foo<T>} is instantiating only the 1st template var of Foo
        " * @param {!Foo<T>} x",
        " */",
        "function fn(x) {}",
        "fn(new Foo('asdf'));"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template S, T",
        " * @param {S} x",
        " */",
        "function Foo(x) {",
        "  /** @type {S} */ this.prop = x;",
        "}",
        "/**",
        " * @template T",
        // {!Foo<T>} is instantiating only the 1st template var of Foo
        " * @param {!Foo<T>} x",
        " * @return {T}",
        " */",
        "function fn(x) { return x.prop; }",
        "fn(new Foo('asdf')) - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testCasts() {
    typeCheck("(/** @type {number} */ ('asdf'));", TypeValidator.INVALID_CAST);

    typeCheck(Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  var y = /** @type {number} */ (x);",
        "}"));

    typeCheck("(/** @type {(number|string)} */ (1));");

    typeCheck("(/** @type {number} */ (/** @type {?} */ ('asdf')))");

    // Ignore null when checking whether we are casting to a subtype
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {}",
        "/** @constructor @extends {Parent} */",
        "function Child() {}",
        "/** @type {Child|null} */ (new Parent);"));
  }

  public void testOverride() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Intf() {}",
        "/** @param {(number|string)} x */",
        "Intf.prototype.method = function(x) {};",
        "/**",
        " * @constructor",
        " * @implements {Intf}",
        " */",
        "function C() {}",
        "/** @override */",
        "C.prototype.method = function (x) { x - 1; };",
        "(new C).method('asdf');"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Intf() {}",
        "/** @param {(number|string)} x */",
        "Intf.prototype.method = function(x) {};",
        "/**",
        " * @constructor",
        " * @implements {Intf}",
        " */",
        "function C() {}",
        "/** @inheritDoc */",
        "C.prototype.method = function (x) { x - 1; };",
        "(new C).method('asdf');"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @override */",
        "Foo.prototype.method = function() {};"),
        TypeCheck.UNKNOWN_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @inheritDoc */",
        "Foo.prototype.method = function() {};"),
        TypeCheck.UNKNOWN_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function High() {}",
        "/** @param {number=} x */",
        "High.prototype.f = function(x) {};",
        "/** @constructor @extends {High} */",
        "function Low() {}",
        "/** @override */",
        "Low.prototype.f = function(x) {};",
        "(new Low).f();",
        "(new Low).f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function F() {}",
        "/**",
        " * @param {string} x",
        " * @param {...*} var_args",
        " * @return {*}",
        " */",
        "F.prototype.method;",
        "/**",
        " * @constructor",
        " * @extends {F}",
        " */",
        "function G() {}",
        "/** @override */",
        "G.prototype.method = function (x, opt_index) {};",
        "(new G).method('asdf');"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function F() {}",
        "/**",
        " * @param {string} x",
        " * @param {...number} var_args",
        " * @return {number}",
        " */",
        "F.prototype.method;",
        "/**",
        " * @constructor",
        " * @extends {F}",
        " */",
        "function G() {}",
        "/** @override */",
        "G.prototype.method = function (x, opt_index) {};",
        "(new G).method('asdf', 'asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE,
        CheckMissingReturn.MISSING_RETURN_STATEMENT);
  }

  public void testOverrideNoInitializer() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Intf() {}",
        "/** @param {number} x */",
        "Intf.prototype.method = function(x) {};",
        "/** @interface @extends {Intf} */",
        "function Subintf() {}",
        "/** @override */",
        "Subintf.prototype.method;",
        "function f(/** !Subintf */ x) { x.method('asdf'); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Intf() {}",
        "/** @param {number} x */",
        "Intf.prototype.method = function(x) {};",
        "/** @interface @extends {Intf} */",
        "function Subintf() {}",
        "Subintf.prototype.method;",
        "function f(/** !Subintf */ x) { x.method('asdf'); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Intf() {}",
        "/** @param {number} x */",
        "Intf.prototype.method = function(x) {};",
        "/** @constructor  @implements {Intf} */",
        "function C() {}",
        "/** @override */",
        "C.prototype.method = (function(){ return function(x){}; })();",
        "(new C).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Intf() {}",
        "/** @param {number} x */",
        "Intf.prototype.method = function(x) {};",
        "/** @constructor  @implements {Intf} */",
        "function C() {}",
        "C.prototype.method = (function(){ return function(x){}; })();",
        "(new C).method('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Intf() {}",
        "/** @type {string} */",
        "Intf.prototype.s;",
        "/** @constructor @implements {Intf} */",
        "function C() {}",
        "/** @override */",
        "C.prototype.s = 'str2';",
        "(new C).s - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Intf() {}",
        "/** @type {string} */",
        "Intf.prototype.s;",
        "/** @constructor @implements {Intf} */",
        "function C() {}",
        "/** @type {number} @override */",
        "C.prototype.s = 72;"),
        GlobalTypeInfo.INVALID_PROP_OVERRIDE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Intf() {}",
        "/** @type {string} */",
        "Intf.prototype.s;",
        "/** @constructor @implements {Intf} */",
        "function C() {}",
        "/** @override */",
        "C.prototype.s = 72;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testFunctionConstructor() {
    typeCheck(Joiner.on('\n').join(
        "/** @type {Function} */ function topFun() {}",
        "topFun(1);"));

    typeCheck(
        "/** @type {Function} */ function topFun(x) { return x - 5; }");

    typeCheck(Joiner.on('\n').join(
        "function f(/** Function */ fun) {}",
        "f(function g(x) { return x - 5; });"));

    typeCheck(
        "function f(/** !Function */ fun) { return new fun(1, 2); }");

    typeCheck("function f(/** !Function */ fun) { [] instanceof fun; }");
  }

  public void testConditionalExBranch() {
    typeCheck(Joiner.on('\n').join(
        "function g() { throw 1; }",
        "function f() {",
        "  try {",
        "    if (g()) {}",
        "  } catch (e) {}",
        "};"));
  }

  public void testGenericInterfaceDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @interface @template T */",
        "ns.Interface = function(){}"));
  }

  public void testGetpropOnTopDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {};",
        "/** @type {*} */ Foo.prototype.stuff;",
        "function f(/** !Foo */ foo, x) {",
        "  (foo.stuff.prop = x) || false;",
        "};"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {};",
        "/** @type {*} */ Foo.prototype.stuff;",
        "function f(/** Foo */ foo) {",
        "  foo.stuff.prop || false;",
        "};"),
        NewTypeInference.NULLABLE_DEREFERENCE);
  }

  public void testImplementsGenericInterfaceDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface @template Z */",
        "function Foo(){}",
        "Foo.prototype.getCount = function /** number */ (){};",
        "/**",
        " * @constructor @implements {Foo<T>}",
        " * @template T",
        " */",
        "function Bar(){}",
        "Bar.prototype.getCount = function /** number */ (){};"));
  }

  public void testDeadCodeDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "   throw 'Error';",
        "   return 5;",
        "}"));
  }

  public void testSpecializeFunctionToNominalDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Foo() {}",
        "function reqFoo(/** Foo */ foo) {};",
        "/** @param {Function} fun */",
        "function f(fun) {",
        "    reqFoo(fun);",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "function f(x) {",
        "  if (typeof x == 'function') {",
        "    var /** !Foo */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testPrototypeMethodOnUndeclaredDoesntCrash() {
    typeCheck(
        "Foo.prototype.method = function(){ this.x = 5; };",
        // VarCheck.UNDEFINED_VAR_ERROR,
        CheckGlobalThis.GLOBAL_THIS);
  }

  public void testFunctionGetpropDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "function g() {}",
        "function f() {",
        "  g();",
        "  return g.prop;",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);
  }

  public void testUnannotatedBracketAccessDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "function f(foo, i, j) {",
        "  foo.array[i][j] = 5;",
        "}"));
  }

  public void testUnknownTypeReferenceDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I(){}",
        "/** @type {function(NonExistentClass)} */",
        "I.prototype.method;"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);
  }

  public void testSpecializingTypeVarDoesntGoToBottom() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        "  * @template T",
        "  * @param {T} x",
        "  */",
        "function f(x) {",
        "   if (typeof x === 'string') {",
        "     return x.length;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        "  * @template T",
        "  * @param {T} x",
        "  */",
        "function f(x) {",
        "   if (typeof x === 'string') {",
        "     return x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        "  * @template T",
        "  * @param {T} x",
        "  */",
        "function f(x) {",
        "   if (typeof x === 'string') {",
        "     return x - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        "  * @template T",
        "  * @param {T} x",
        "  */",
        "function f(x) {",
        "   if (typeof x === 'number') {",
        "     (function(/** string */ y){})(x);",
        "  }",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testBottomPropAccessDoesntCrash() {
    // TODO(blickly): This warning is not very good.
    typeCheck(Joiner.on('\n').join(
        "var obj = null;",
        "if (obj) obj.prop += 7;"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype.m = function(/** number */ x) {};",
        "/** @constructor */",
        "function Bar() {}",
        "Bar.prototype.m = function(/** string */ x) {};",
        "function f(/** null|!Foo|!Bar */ x, y) {",
        "  if (x) {",
        "    return x.m(y);",
        "  }",
        "}"),
        NewTypeInference.BOTTOM_PROP);
  }

  public void testUnannotatedFunctionSummaryDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "var /** !Promise */ p;",
        "function f(unused) {",
        "  function g(){ return 5; }",
        "  p.then(g);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "var /** !Promise */ p;",
        "function f(unused) {",
        "  function g(){ return 5; }",
        "  var /** null */ n = p.then(g);",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testSpecializeLooseNullDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "function reqFoo(/** Foo */ x) {}",
        "function f(x) {",
        "   x = null;",
        "   reqFoo(x);",
        "}"));
  }

  public void testOuterVarDefinitionJoinDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "function f() {",
        "  if (true) {",
        "    function g() { new Foo; }",
        "    g();",
        "  }",
        "}"));

    // typeCheck(Joiner.on('\n').join(
    //     "function f() {",
    //     "  if (true) {",
    //     "    function g() { new Foo; }",
    //     "    g();",
    //     "  }",
    //     "}"),
    //     VarCheck.UNDEFINED_VAR_ERROR);
  }

  public void testUnparameterizedArrayDefinitionDoesntCrash() {
    typeCheckCustomExterns(
        DEFAULT_EXTERNS + Joiner.on('\n').join(
            "/** @constructor */ function Function(){}",
            "/** @constructor */ function Array(){}"),
        Joiner.on('\n').join(
            "function f(/** !Array */ arr) {",
            "  var newarr = [];",
            "  newarr[0] = arr[0];",
            "  newarr[0].prop1 = newarr[0].prop2;",
            "};"));
  }

  public void testInstanceofGenericTypeDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @template T */ function Foo(){}",
        "function f(/** !Foo<?> */ f) {",
        "  if (f instanceof Foo) return true;",
        "};"));
  }

  public void testRedeclarationOfFunctionAsNamespaceDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = ns || {};",
        "ns.fun = function(name) {};",
        "ns.fun = ns.fun || {};",
        "ns.fun.get = function(/** string */ name) {};"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = ns || {};",
        "ns.fun = function(name) {};",
        "ns.fun.get = function(/** string */ name) {};",
        "ns.fun = ns.fun || {};"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testInvalidEnumDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum {Array<number>} */",
        "var FooEnum = {",
        "  BAR: [5]",
        "};",
        "/** @param {FooEnum} x */",
        "function f(x) {",
        "    var y = x[0];",
        "};"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "var ns = {};",
        "function f() {",
        "  /** @enum {number} */ var EnumType = ns;",
        "}"),
        GlobalTypeInfo.MALFORMED_ENUM);
  }

  public void testRemoveNonexistentPropDoesntCrash() {
    // TODO(blickly): Would be nice not to warn here,
    // even if it means missing the warning below
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {",
        " /** @type {!Object} */ this.obj = {arr : []}",
        "}",
        "Foo.prototype.bar = function() {",
        " this.obj.arr.length = 0;",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {",
        " /** @type {!Object} */ this.obj = {}",
        "}",
        "Foo.prototype.bar = function() {",
        " this.obj.prop1.prop2 = 0;",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);
  }

  public void testDoublyAssignedPrototypeMethodDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "Foo.prototype.method = function(){};",
        "var f = function() {",
        "   Foo.prototype.method = function(){};",
        "}"),
        GlobalTypeInfo.CTOR_IN_DIFFERENT_SCOPE);
  }

  public void testTopFunctionAsArgumentDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "function f(x) {}",
        "function g(value) {",
        "  if (typeof value == 'function') {",
        "    f(value);",
        "  }",
        "}"));
  }

  public void testGetpropDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Obj(){}",
        "/** @constructor */ var Foo = function() {",
        "    /** @private {Obj} */ this.obj;",
        "};",
        "Foo.prototype.update = function() {",
        "    if (!this.obj) {}",
        "};"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Obj(){}",
        "/** @constructor */",
        "var Foo = function() {",
        "  /** @private {Obj} */ this.obj;",
        "};",
        "Foo.prototype.update = function() {",
        "    if (!this.obj.size) {}",
        "};"),
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Obj(){}",
        "/** @constructor */",
        "var Foo = function() {",
        "  /** @private {Obj} */ this.obj;",
        "};",
        "/** @param {!Foo} x */",
        "function f(x) {",
        "  if (!x.obj.size) {}",
        "};"),
        NewTypeInference.NULLABLE_DEREFERENCE);
  }

  public void testLooseFunctionSubtypeDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "var Foo = function() {};",
        "/** @param {function(!Foo)} fooFun */",
        "var reqFooFun = function(fooFun) {};",
        "/** @type {function(!Foo)} */",
        "var declaredFooFun;",
        "function f(opt_fooFun) {",
        "  reqFooFun(opt_fooFun);",
        "  var fooFun = opt_fooFun || declaredFooFun;",
        "  reqFooFun(fooFun);",
        "};"));

    typeCheck(Joiner.on('\n').join(
        "var /** @type {function(number)} */ f;",
        "f = (function(x) {",
        "  x(1, 2);",
        "  return x;",
        "})(function(x, y) {});"));
  }

  public void testMeetOfLooseObjAndNamedDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){ this.prop = 5; }",
        "/** @constructor */ function Bar(){}",
        "/** @param {function(!Foo)} func */",
        "Bar.prototype.forEach = function(func) {",
        "  this.forEach(function(looseObj) { looseObj.prop; });",
        "};"));
  }

  // public void testAccessVarargsDoesntCrash() {
  //   // TODO(blickly): Support arguments so we only get one warning
  //   typeCheck(Joiner.on('\n').join(
  //       "/** @param {...} var_args */",
  //       "function f(var_args) { return true ? var_args : arguments; }"),
  //       VarCheck.UNDEFINED_VAR_ERROR,
  //       VarCheck.UNDEFINED_VAR_ERROR);
  // }

  public void testUninhabitableObjectTypeDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ n) {",
        "  if (typeof n == 'string') {",
        "    return { 'First': n, 'Second': 5 };",
        "  }",
        "};"));
  }

  public void testMockedOutConstructorDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "/** @constructor */ Foo = function(){};"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testNamespacePropWithNoTypeDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @public */ ns.prop;"));
  }

  public void testArrayLiteralUsedGenericallyDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {!Array<T>} arr",
        " * @return {T}",
        " */",
        "function f(arr) { return arr[0]; }",
        "f([1,2,3]);"));
  }

  public void testSpecializeLooseFunctionDoesntCrash() {
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** !Function */ func) {};",
        "function g(obj) {",
        "    if (goog.isFunction(obj)) {",
        "      f(obj);",
        "    }",
        "};"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Function */ func) {};",
        "function g(obj) {",
        "    if (typeof obj === 'function') {",
        "      f(obj);",
        "    }",
        "};"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {function(T)} fn",
        " * @param {T} x",
        " * @template T",
        " */",
        "function reqGenFun(fn, x) {};",
        "function g(obj, str) {",
        "  var member = obj[str];",
        "  if (typeof member === 'function') {",
        "    reqGenFun(member, str);",
        "  }",
        "};"));
  }

  public void testUnificationWithTopFunctionDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {*} value",
        " * @param {function(new: T, ...)} type",
        " * @template T",
        " */",
        "function assertInstanceof(value, type) {}",
        "/** @const */ var ctor = unresolvedGlobalVar;",
        "function f(obj) {",
        "  if (obj instanceof ctor) {",
        "    return assertInstanceof(obj, ctor);",
        "  }",
        "}"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE,
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testGetpropOnPossiblyInexistentPropertyDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){};",
        "function f() {",
        "  var obj = 3 ? new Foo : { prop : { subprop : 'str'}};",
        "  obj.prop.subprop = 'str';",
        "};"),
        NewTypeInference.POSSIBLY_INEXISTENT_PROPERTY);
  }

  public void testCtorManipulationDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ var X = function() {};",
        "var f = function(ctor) {",
        "  /** @type {function(new: X)} */",
        "  function InstantiableCtor() {};",
        "  InstantiableCtor.prototype = ctor.prototype;",
        "}"));
  }

  public void testAbstractMethodOverrides() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var goog = {};",
        "/** @type {!Function} */ goog.abstractMethod = function(){};",
        "/** @interface */ function I() {}",
        "/** @param {string=} opt_str */",
        "I.prototype.done = goog.abstractMethod;",
        "/** @implements {I} @constructor */ function Foo() {}",
        "/** @override */ Foo.prototype.done = function(opt_str) {}",
        "/** @param {I} stats */ function f(stats) {}",
        "function g() {",
        "  var x = new Foo();",
        "  f(x);",
        "  x.done();",
        "}"));
  }

  public void testThisReferenceUsedGenerically() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @template T */",
        "var Foo = function(t) {",
        "  /** @type {Foo<T>} */",
        "  this.parent_ = null;",
        "}",
        "Foo.prototype.method = function() {",
        "  var p = this;",
        "  while (p != null) p = p.parent_;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @template T */",
        "var Foo = function(t) {",
        "  /** @type {Foo<T>} */",
        "  var p = this;",
        "}"));
  }

  public void testGrandparentTemplatizedDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @template VALUE */",
        "var Grandparent = function() {};",
        "/** @constructor @extends {Grandparent<number>} */",
        "var Parent = function(){};",
        "/** @constructor @extends {Parent} */ function Child(){}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @template VALUE */",
        "var Grandparent = function() {};",
        "/** @constructor @extends {Grandparent} */",
        "var Parent = function(){};",
        "/** @constructor @extends {Parent} */ function Child(){}"));
  }

  public void testDirectPrototypeAssignmentDoesntCrash() {
    typeCheck(Joiner.on('\n').join(
        "function UndeclaredCtor(parent) {}",
        "UndeclaredCtor.prototype = {__proto__: Object.prototype};"));
  }

  public void testDebuggerStatementDoesntCrash() {
    typeCheck("debugger;");
  }

  public void testDeclaredMethodWithoutScope() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Foo(){}",
        "/** @type {function(number)} */ Foo.prototype.bar;",
        "/** @constructor @implements {Foo} */ function Bar(){}",
        "Bar.prototype.bar = function(x){}"));

    typeCheck(Joiner.on('\n').join(
        "/** @type {!Function} */",
        "var g = function() { throw 0; };",
        "/** @constructor */ function Foo(){}",
        "/** @type {function(number)} */ Foo.prototype.bar = g;",
        "/** @constructor @extends {Foo} */ function Bar(){}",
        "Bar.prototype.bar = function(x){}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {string} s */",
        "var reqString = function(s) {};",
        "/** @constructor */ function Foo(){}",
        "/** @type {function(string)} */ Foo.prototype.bar = reqString;",
        "/** @constructor @extends {Foo} */ function Bar(){}",
        "Bar.prototype.bar = function(x){}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {string} s */",
        "var reqString = function(s) {};",
        "/** @constructor */ function Foo(){}",
        "/** @type {function(number)} */ Foo.prototype.bar = reqString;",
        "/** @constructor @extends {Foo} */ function Bar(){}",
        "Bar.prototype.bar = function(x){}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "/** @type {Function} */ Foo.prototype.bar = null;",
        "/** @constructor @extends {Foo} */ function Bar(){}",
        "Bar.prototype.bar = function(){}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){}",
        "/** @type {!Function} */ Foo.prototype.bar = null;",
        "/** @constructor @extends {Foo} */ function Bar(){}",
        "Bar.prototype.bar = function(){}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function I(){}",
        "/** @return {void} */",
        "I.prototype.method;"));
  }

  public void testDontOverrideNestedPropWithWorseType() {
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "var Bar = function() {};",
        "/** @type {Function} */",
        "Bar.prototype.method;",
        "/** @interface */",
        "var Baz = function() {};",
        "Baz.prototype.method = function() {};",
        "/** @constructor */",
        "var Foo = function() {};",
        "/** @type {!Bar|!Baz} */",
        "Foo.prototype.obj;",
        "Foo.prototype.set = function() {",
        "    this.obj.method = 5;",
        "};"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** { prop: number } */ obj, x) {",
        " x < obj.prop;",
        " obj.prop < 'str';",
        " obj.prop = 123;",
        " x = 123;",
        "}",
        "f({ prop: 123}, 123)"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testPropNamesWithDot() {
    typeCheck("var x = { '.': 1, ';': 2, '/': 3, '{': 4, '}': 5 }");

    typeCheck(Joiner.on('\n').join(
        "function f(/** { foo : { bar : string } } */ x) {",
        "  x['foo.bar'] = 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "var x = { '.' : 'str' };",
        "x['.'] - 5"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testObjLitDeclaredProps() {
    typeCheck(
        "({ /** @type {string} */ prop: 123 });",
        NewTypeInference.INVALID_OBJLIT_PROPERTY_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var lit = { /** @type {string} */ prop: 'str' };",
        "lit.prop = 123;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var lit = { /** @type {(number|string)} */ prop: 'str' };",
        "var /** string */ s = lit.prop;"));
  }

  public void testCallArgumentsChecked() {
    typeCheck(
        "3(1 - 'str');",
        TypeCheck.NOT_CALLABLE,
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testRecursiveFunctions() {
    typeCheck(
        "function foo(){ foo() - 123; return 'str'; }",
        NewTypeInference.INVALID_INFERRED_RETURN_TYPE);

    typeCheck(
        "/** @return {string} */ function foo(){ foo() - 123; return 'str'; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {number} */",
        "var f = function rec() { return rec; };"),
        NewTypeInference.RETURN_NONDECLARED_TYPE);
  }

  public void testStructPropAccess() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */ function Foo() { this.prop = 123; }",
        "(new Foo).prop;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */ function Foo() { this.prop = 123; }",
        "(new Foo)['prop'];"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */ function Foo() {}",
        "/** @type {number} */ Foo.prototype.prop;",
        "function f(/** !Foo */ x) { x['prop']; }"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */ function Foo() {",
        "  this.prop = 123;",
        "  this['prop'] - 123;",
        "}"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */ function Foo() { this.prop = 123; }",
        "(new Foo)['prop'] = 123;"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */ function Foo() { this.prop = 123; }",
        "function f(pname) { (new Foo)[pname] = 123; }"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */ function Foo() { this.prop = {}; }",
        "(new Foo)['prop'].newprop = 123;"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "function f(cond) {",
        "  var x;",
        "  if (cond) {",
        "    x = new Foo;",
        "  }",
        "  else {",
        "    x = new Bar;",
        "  }",
        "  x['prop'] = 123;",
        "}"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck("(/** @struct */ { 'prop' : 1 });", TypeCheck.ILLEGAL_OBJLIT_KEY);

    typeCheck(
        "var lit = /** @struct */ { prop : 1 }; lit['prop'];",
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "function f(cond) {",
        "  var x;",
        "  if (cond) {",
        "    x = /** @struct */ { a: 1 };",
        "  }",
        "  else {",
        "    x = /** @struct */ { a: 2 };",
        "  }",
        "  x['a'] = 123;",
        "}"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "function f(cond) {",
        "  var x;",
        "  if (cond) {",
        "    x = /** @struct */ { a: 1 };",
        "  }",
        "  else {",
        "    x = {};",
        "  }",
        "  x['random' + 'propname'] = 123;",
        "}"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @struct",
        " */",
        "function Foo() {",
        "  /** @type {number} */",
        "  this.prop;",
        "  this.prop = 'asdf';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @struct",
        " */",
        "function Foo() {",
        "  /** @type {number} */",
        "  this.prop;",
        "}",
        "(new Foo).prop = 'asdf';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testDictPropAccess() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @dict */ function Foo() { this['prop'] = 123; }",
        "(new Foo)['prop'];"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @dict */ function Foo() { this['prop'] = 123; }",
        "(new Foo).prop;"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @dict */ function Foo() {",
        "  this['prop'] = 123;",
        "  this.prop - 123;",
        "}"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @dict */ function Foo() { this['prop'] = 123; }",
        "(new Foo).prop = 123;"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @dict */ function Foo() { this['prop'] = {}; }",
        "(new Foo).prop.newprop = 123;"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @dict */ function Foo() {}",
        "/** @constructor */ function Bar() {}",
        "function f(cond) {",
        "  var x;",
        "  if (cond) {",
        "    x = new Foo;",
        "  }",
        "  else {",
        "    x = new Bar;",
        "  }",
        "  x.prop = 123;",
        "}"),
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck("(/** @dict */ { prop : 1 });", TypeCheck.ILLEGAL_OBJLIT_KEY);

    typeCheck(
        "var lit = /** @dict */ { 'prop' : 1 }; lit.prop;",
        TypeValidator.ILLEGAL_PROPERTY_ACCESS);

    typeCheck(
        "(/** @dict */ {}).toString();", TypeValidator.ILLEGAL_PROPERTY_ACCESS);
  }

  public void testStructWithIn() {
    typeCheck("('prop' in /** @struct */ {});", TypeCheck.IN_USED_WITH_STRUCT);

    typeCheck(
        "for (var x in /** @struct */ {});", TypeCheck.IN_USED_WITH_STRUCT);
  }

  public void testStructDictSubtyping() {
    typeCheck("var lit = { a: 1 }; lit.a - 2; lit['a'] + 5;");

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */ function Foo() {}",
        "/** @constructor @dict */ function Bar() {}",
        "function f(/** Foo */ x) {}",
        "f(/** @dict */ {});"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** { a : number } */ x) {}",
        "f(/** @dict */ { 'a' : 5 });"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testInferStructDictFormal() {
    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  return obj.prop;",
        "}",
        "f(/** @dict */ { 'prop': 123 });"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  return obj['prop'];",
        "}",
        "f(/** @struct */ { prop: 123 });"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "function f(obj) { obj['prop']; return obj; }",
        "var /** !Foo */ x = f({ prop: 123 });"));

    // We infer unrestricted loose obj for mixed . and [] access
    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  if (obj['p1']) {",
        "    obj.p2.p3 = 123;",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(obj) {",
        "  return obj['a'] + obj.b;",
        "}",
        "f({ a: 123, 'b': 234 });"));
  }

  public void testStructDictInheritance() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "/** @constructor @struct @extends {Foo} */",
        "function Bar() {}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "/** @constructor @unrestricted @extends {Foo} */",
        "function Bar() {}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @dict */",
        "function Foo() {}",
        "/** @constructor @dict @extends {Foo} */",
        "function Bar() {}"));

    // TODO(dimvar): remove conflicting shape type warning
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @unrestricted */",
        "function Foo() {}",
        "/** @constructor @struct @extends {Foo} */",
        "function Bar() {}"),
        JSTypeCreatorFromJSDoc.CONFLICTING_SHAPE_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @unrestricted */",
        "function Foo() {}",
        "/** @constructor @dict @extends {Foo} */",
        "function Bar() {}"),
        JSTypeCreatorFromJSDoc.CONFLICTING_SHAPE_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Foo() {}",
        "/** @constructor @dict @implements {Foo} */",
        "function Bar() {}"),
        JSTypeCreatorFromJSDoc.DICT_IMPLEMENTS_INTERF);
  }

  public void testStructPropCreation() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() { this.prop = 1; }",
        "(new Foo).prop = 2;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "Foo.prototype.method = function() { this.prop = 1; };"),
        TypeCheck.ILLEGAL_PROPERTY_CREATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "Foo.prototype.method = function() { this.prop = 1; };",
        "(new Foo).prop = 2;"),
        TypeCheck.ILLEGAL_PROPERTY_CREATION,
        TypeCheck.ILLEGAL_PROPERTY_CREATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "(new Foo).prop += 2;"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "Foo.prototype.method = function() { this.prop = 1; };",
        "(new Foo).prop++;"),
        TypeCheck.ILLEGAL_PROPERTY_CREATION,
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(
        "(/** @struct */ { prop: 1 }).prop2 = 123;",
        TypeCheck.ILLEGAL_PROPERTY_CREATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "/** @constructor @struct @extends {Foo} */",
        "function Bar() {}",
        "Bar.prototype.prop = 123;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "/** @constructor @struct @extends {Foo} */",
        "function Bar() {}",
        "Bar.prototype.prop = 123;",
        "(new Foo).prop = 234;"),
        TypeCheck.ILLEGAL_PROPERTY_CREATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @struct",
        " */",
        "function Foo() {",
        "  var t = this;",
        "  t.x = 123;",
        "}"),
        TypeCheck.ILLEGAL_PROPERTY_CREATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @struct",
        " */",
        "function Foo() {}",
        "Foo.someprop = 123;"));

    // TODO(dimvar): the current type inf also doesn't catch this.
    // Consider warning when the prop is not an "own" prop.
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "Foo.prototype.bar = 123;",
        "(new Foo).bar = 123;"));

    typeCheck(Joiner.on('\n').join(
        "function f(obj) { obj.prop = 123; }",
        "f(/** @struct */ {});"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @struct */",
        "function Foo() {}",
        "function f(obj) { obj.prop - 5; return obj; }",
        "var s = (1 < 2) ? new Foo : f({ prop: 123 });",
        "s.newprop = 123;"),
        TypeCheck.ILLEGAL_PROPERTY_CREATION);
  }

  public void testMisplacedStructDictAnnotation() {
    typeCheck(
        "/** @struct */ function Struct1() {}",
        GlobalTypeInfo.STRUCTDICT_WITHOUT_CTOR);
    typeCheck(
        "/** @dict */ function Dict() {}",
        GlobalTypeInfo.STRUCTDICT_WITHOUT_CTOR);
  }

  // public void testGlobalVariableInJoin() {
  //   typeCheck(
  //       "function f() { true ? globalVariable : 123; }",
  //       VarCheck.UNDEFINED_VAR_ERROR);
  // }

  // public void testGlobalVariableInAssign() {
  //   typeCheck(
  //       "u.prop = 123;",
  //       VarCheck.UNDEFINED_VAR_ERROR);
  // }

  public void testGetters() {
    typeCheck(
        "var x = { /** @return {string} */ get a() { return 1; } };",
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    typeCheck(
        "var x = { /** @param {number} n */ get a() {} };",
        GlobalTypeInfo.INEXISTENT_PARAM);

    typeCheck(
        "var x = { /** @type {string} */ get a() {} };",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "var x = {",
        "  /**",
        "   * @return {T|number} b",
        "   * @template T",
        "   */",
        "  get a() {}",
        "};"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(
        "var x = /** @dict */ { get a() {} };", TypeCheck.ILLEGAL_OBJLIT_KEY);

    typeCheck(
        "var x = /** @struct */ { get 'a'() {} };",
        TypeCheck.ILLEGAL_OBJLIT_KEY);

    typeCheck(
        "var x = { get a() { 1 - 'asdf'; } };",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var x = { get a() { return 1; } };",
        "x.a < 'str';"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var x = { get a() { return 1; } };",
        "x.a();"),
        TypeCheck.NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "var x = { get 'a'() { return 1; } };",
        "x['a']();"),
        TypeCheck.NOT_CALLABLE);

    // assigning to a getter doesn't remove it
    typeCheck(Joiner.on('\n').join(
        "var x = { get a() { return 1; } };",
        "x.a = 'str';",
        "x.a - 1;"));

    typeCheck(
        "var x = /** @struct */ { get a() {} }; x.a = 123;",
        TypeCheck.ILLEGAL_PROPERTY_CREATION);
  }

  public void testSetters() {
    typeCheck(
        "var x = { /** @return {string} */ set a(b) {} };",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(
        "var x = { /** @type{function(number):number} */ set a(b) {} };",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(
        "var x = { set /** string */ a(b) {} };",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "var x = {",
        "  /**",
        "   * @param {T|number} b",
        "   * @template T",
        "   */",
        "  set a(b) {}",
        "};"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(
        "var x = { set a(b) { return 1; } };",
        NewTypeInference.RETURN_NONDECLARED_TYPE);

    typeCheck(
        "var x = { /** @type {string} */ set a(b) {} };",
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(
        "var x = /** @dict */ { set a(b) {} };", TypeCheck.ILLEGAL_OBJLIT_KEY);

    typeCheck(
        "var x = /** @struct */ { set 'a'(b) {} };",
        TypeCheck.ILLEGAL_OBJLIT_KEY);

    typeCheck(
        "var x = { set a(b) { 1 - 'asdf'; } };",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(
        "var x = { set a(b) {}, prop: 123 }; var y = x.a;",
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "var x = { /** @param {string} b */ set a(b) {} };",
        "x.a = 123;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var x = { set a(b) { b - 5; } };",
        "x.a = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var x = { set 'a'(b) { b - 5; } };",
        "x['a'] = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testConstMissingInitializer() {
    typeCheck("/** @const */ var x;", GlobalTypeInfo.CONST_WITHOUT_INITIALIZER);

    typeCheck("/** @final */ var x;", GlobalTypeInfo.CONST_WITHOUT_INITIALIZER);

    typeCheckCustomExterns(DEFAULT_EXTERNS + "/** @const {number} */ var x;", "");

    // TODO(dimvar): must fix externs initialization
    // typeCheck("/** @const {number} */ var x;", "x - 5;");

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @const */",
        "Foo.prop;"),
        GlobalTypeInfo.CONST_WITHOUT_INITIALIZER);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const */ this.prop;",
        "}"),
        GlobalTypeInfo.CONST_WITHOUT_INITIALIZER);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @const */",
        "Foo.prototype.prop;"),
        GlobalTypeInfo.CONST_WITHOUT_INITIALIZER);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.prop;"),
        GlobalTypeInfo.CONST_WITHOUT_INITIALIZER);
  }

  public void testMisplacedConstPropertyAnnotation() {
    typeCheck(
        "function f(obj) { /** @const */ obj.prop = 123; }",
        GlobalTypeInfo.MISPLACED_CONST_ANNOTATION);

    typeCheck(
        "function f(obj) { /** @const */ obj.prop; }",
        GlobalTypeInfo.MISPLACED_CONST_ANNOTATION);

    typeCheck(
        "var obj = { /** @const */ prop: 1 };",
        GlobalTypeInfo.MISPLACED_CONST_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "Foo.prototype.method = function() {",
        "  /** @const */ this.prop = 1;",
        "}"),
        GlobalTypeInfo.MISPLACED_CONST_ANNOTATION);

    // A final constructor isn't the same as a @const property
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /**",
        "   * @constructor",
        "   * @final",
        "   */",
        "  this.Bar = function() {};",
        "}"));
  }

  public void testConstVarsDontReassign() {
    typeCheck(
        "/** @const */ var x = 1; x = 2;", NewTypeInference.CONST_REASSIGNED);

    typeCheck(
        "/** @const */ var x = 1; x += 2;", NewTypeInference.CONST_REASSIGNED);

    typeCheck(
        "/** @const */ var x = 1; x -= 2;", NewTypeInference.CONST_REASSIGNED);

    typeCheck(
        "/** @const */ var x = 1; x++;", NewTypeInference.CONST_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var x = 1;",
        "function f() { x = 2; }"),
        NewTypeInference.CONST_REASSIGNED);

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "/** @const {number} */ var x;", "x = 2;",
        NewTypeInference.CONST_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var x = 1;",
        "function g() {",
        "  var x = 2;",
        "  x = x + 3;",
        "}"));
  }

  public void testConstPropertiesDontReassign() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const */ this.prop = 1;",
        "}",
        "var obj = new Foo;",
        "obj.prop = 2;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const {number} */",
        "  this.prop = 1;",
        "}",
        "var obj = new Foo;",
        "obj.prop = 2;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const */ this.prop = 1;",
        "}",
        "var obj = new Foo;",
        "obj.prop += 2;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const */ this.prop = 1;",
        "}",
        "var obj = new Foo;",
        "obj.prop++;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.prop = 1;",
        "ns.prop = 2;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.prop = 1;",
        "function f() { ns.prop = 2; }"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const {number} */",
        "ns.prop = 1;",
        "ns.prop = 2;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.prop = 1;",
        "ns.prop++;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @const */ Foo.prop = 1;",
        "Foo.prop = 2;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @const {number} */ Foo.prop = 1;",
        "Foo.prop++;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @const */ Foo.prototype.prop = 1;",
        "Foo.prototype.prop = 2;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @const */ Foo.prototype.prop = 1;",
        "var protoAlias = Foo.prototype;",
        "protoAlias.prop = 2;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @const */ this.X = 4; }",
        "/** @constructor */",
        "function Bar() { /** @const */ this.X = 5; }",
        "var fb = true ? new Foo : new Bar;",
        "fb.X++;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);
  }

  public void testConstantByConvention() {
    typeCheck(Joiner.on('\n').join(
        "var ABC = 123;",
        "ABC = 321;"),
        NewTypeInference.CONST_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  this.ABC = 123;",
        "}",
        "(new Foo).ABC = 321;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);
  }

  public void testDontOverrideFinalMethods() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @final */",
        "Foo.prototype.method = function(x) {};",
        "/** @constructor @extends {Foo} */",
        "function Bar() {}",
        "Bar.prototype.method = function(x) {};"),
        GlobalTypeInfo.CANNOT_OVERRIDE_FINAL_METHOD);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @final */",
        "Foo.prototype.num = 123;",
        "/** @constructor @extends {Foo} */",
        "function Bar() {}",
        "Bar.prototype.num = 2;"));

    // // TODO(dimvar): fix
    // typeCheck(Joiner.on('\n').join(
    //     "/** @constructor */",
    //     "function High() {}",
    //     "/**",
    //     " * @param {number} x",
    //     " * @final",
    //     " */",
    //     "High.prototype.method = function(x) {};",
    //     "/** @constructor @extends {High} */",
    //     "function Mid() {}",
    //     "/** @constructor @extends {Mid} */",
    //     "function Low() {}",
    //     "Low.prototype.method = function(x) {};"),
    //     GlobalTypeInfo.CANNOT_OVERRIDE_FINAL_METHOD);
  }

  public void testInferenceOfConstType() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var s = 'str';",
        "function f() { s - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** string */ x) {",
        "  /** @const */",
        "  var s = x;",
        "  function g() { s - 5; }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function RegExp(){}",
        "/** @const */",
        "var r = /find/;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function RegExp(){}",
        "/** @const */",
        "var r = /find/;",
        "function g() { r - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var a = [5];"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var a = [5];",
        "function g() { a - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var x;",
        "/** @const */ var o = x = {};",
        "function g() { return o.prop; }"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var o = (0,{});",
        "function g() { return o.prop; }"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var s = true ? null : null;",
        "function g() { s - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var s = true ? void 0 : undefined;",
        "function g() { s - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var b = true ? (1<2) : ('' in {});",
        "function g() { b - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var n = 0 || 6;",
        "function g() { n < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var s = 'str' + 5;",
        "function g() { s - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    // TODO(dimvar): must fix externs initialization
    // typeCheck(Joiner.on('\n').join(
    //     "var /** string */ x;",
    //     "/** @const */",
    //     "var s = x;",
    //     "function g() { s - 5; }"),
    //     NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const */",
        "  this.prop = 'str';",
        "}",
        "(new Foo).prop - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @const */",
        "Foo.prop = 'str';",
        "function g() { Foo.prop - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** string */ s) {",
        "  /** @constructor */",
        "  function Foo() {}",
        "  /** @const */",
        "  Foo.prototype.prop = s;",
        "  function g() {",
        "    (new Foo).prop - 5;",
        "  }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.prop = 'str';",
        "function f() {",
        "  ns.prop - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, y) {",
        "  /** @const */",
        "  var n = x - y;",
        "  function g() { n < 'str'; }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  /** @const */",
        "  var notx = !x;",
        "  function g() { notx - 5; }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var lit = { a: 'a', b: 'b' };",
        "function g() { lit.a - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var n = ('str', 123);",
        "function f() { n < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var s = x;",
        "var /** string */ x;"),
        // VariableReferenceCheck.EARLY_REFERENCE,
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  /** @const */",
        "  var c = x;",
        "}"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  /** @const */",
        "  var c = { a: 1, b: x };",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @param {{ a: string }} x",
        " */",
        "function Foo(x) {",
        "  /** @const */",
        "  this.prop = x.a;",
        "}",
        "(new Foo({ a: ''})).prop - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @return {string} */",
        "function f() { return ''; }",
        "/** @const */",
        "var s = f();",
        "function g() { s - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var s = f();",
        "/** @return {string} */",
        "function f() { return ''; }"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {}",
        "/** @const */",
        "var foo = new Foo;",
        "function g() {",
        "  var /** Bar */ bar = foo;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var n1 = 1;",
        "/** @const */",
        "var n2 = n1;",
        "function g() { n2 < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    // Don't treat aliased constructors as if they were const variables.
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Bar() {}",
        "/**",
        " * @constructor",
        " * @final",
        " */",
        "var Foo = Bar;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Bar() {}",
        "/** @const */",
        "var ns = {};",
        "/**",
        " * @constructor",
        " * @final",
        " */",
        "ns.Foo = Bar;"));

    // (Counterintuitive) On a constructor, @final means don't subclass, not
    // that it's a const. We don't warn about reassignment.
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @final",
        " */",
        "var Foo = function() {};",
        "Foo = /** @type {?} */ (function() {});"));
  }

  public void testSuppressions() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @fileoverview",
        " * @suppress {newCheckTypes}",
        " */",
        "123();"));

    typeCheck(Joiner.on('\n').join(
        "123();",
        "/** @suppress {newCheckTypes} */",
        "function f() { 123(); }"),
        TypeCheck.NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "123();",
        "/** @suppress {newCheckTypes} */",
        "function f() { 1 - 'str'; }"),
        TypeCheck.NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @type {Object} */",
        "ns.obj = { prop: 123 };",
        "/**",
        " * @suppress {duplicate}",
        " * @type {Object}",
        " */",
        "ns.obj = null;"));

    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  /** @const */",
        "  var ns = {};",
        "  /** @type {number} */",
        "  ns.prop = 1;",
        "  /**",
        "   * @type {number}",
        "   * @suppress {duplicate}",
        "   */",
        "  ns.prop = 2;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @suppress {constantProperty}",
        " */",
        "function Foo() {",
        "  /** @const */ this.bar = 3; this.bar += 4;",
        "}"));
  }

  public void testTypedefs() {
    typeCheck(Joiner.on('\n').join(
        "/** @typedef {number} */",
        "var num = 1;"),
        GlobalTypeInfo.CANNOT_INIT_TYPEDEF);

    // typeCheck(Joiner.on('\n').join(
    //     "/** @typedef {number} */",
    //     "var num;",
    //     "num - 5;"),
    //     VarCheck.UNDEFINED_VAR_ERROR);

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {NonExistentType} */",
        "var t;",
        "function f(/** t */ x) { x - 1; }"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    // typeCheck(Joiner.on('\n').join(
    //     "/** @typedef {number} */",
    //     "var dup;",
    //     "/** @typedef {number} */",
    //     "var dup;"),
    //     VariableReferenceCheck.REDECLARED_VARIABLE);

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {number} */",
        "var dup;",
        "/** @typedef {string} */",
        "var dup;",
        "var /** dup */ n = 'str';"),
        // VariableReferenceCheck.REDECLARED_VARIABLE,
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {number} */",
        "var num;",
        "/** @type {num} */",
        "var n = 1;"));

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {number} */",
        "var num;",
        "/** @type {num} */",
        "var n = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @type {num} */",
        "var n = 'str';",
        "/** @typedef {number} */",
        "var num;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {number} */",
        "var num;",
        "function f() {",
        "  /** @type {num} */",
        "  var n = 'str';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @type {num2} */",
        "var n = 'str';",
        "/** @typedef {num} */",
        "var num2;",
        "/** @typedef {number} */",
        "var num;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {rec2} */",
        "var rec1;",
        "/** @typedef {rec1} */",
        "var rec2;"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {{ prop: rec2 }} */",
        "var rec1;",
        "/** @typedef {{ prop: rec1 }} */",
        "var rec2;"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @typedef {Foo} */",
        "var Bar;",
        "var /** Bar */ x = null;"));

    // NOTE(dimvar): I don't know if long term we want to support ! on anything
    // other than a nominal-type name, but for now it's good to have this test.
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @typedef {Foo} */",
        "var Bar;",
        "var /** !Bar */ x = null;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {number} */",
        "var N;",
        "function f() {",
        "  /** @constructor */",
        "  function N() {}",
        "  function g(/** N */ obj) { obj - 5; }",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testLends() {
    typeCheck(
        "(/** @lends {InexistentType} */ { a: 1 });",
        GlobalTypeInfo.LENDS_ON_BAD_TYPE);

    typeCheck(
        "(/** @lends {number} */ { a: 1 });", GlobalTypeInfo.LENDS_ON_BAD_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "(/** @lends {Foo.badname} */ { a: 1 });"),
        GlobalTypeInfo.LENDS_ON_BAD_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Foo() {}",
        "(/** @lends {Foo} */ { a: 1 });"),
        GlobalTypeInfo.LENDS_ON_BAD_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Foo() {}",
        "(/** @lends {Foo.prototype} */ { a: 1 });"),
        GlobalTypeInfo.LENDS_ON_BAD_TYPE);

    typeCheck(
        "(/** @lends {Inexistent.Type} */ { a: 1 });",
        GlobalTypeInfo.LENDS_ON_BAD_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "(/** @lends {ns} */ { /** @type {number} */ prop : 1 });",
        "function f() { ns.prop = 'str'; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "(/** @lends {ns} */ { /** @type {number} */ prop : 1 });",
        "/** @const */ var ns = {};",
        "function f() { ns.prop = 'str'; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "(/** @lends {ns} */ { prop : 1 });",
        "function f() { var /** string */ s = ns.prop; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.subns = {};",
        "(/** @lends {ns.subns} */ { prop: 1 });",
        "var /** string */ s = ns.subns.prop;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "(/** @lends {Foo} */ { prop: 1 });",
        "var /** string */ s = Foo.prop;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "(/** @lends {Foo} */ { prop: 1 });",
        "function f() { var /** string */ s = Foo.prop; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @constructor */",
        "ns.Foo = function() {};",
        "(/** @lends {ns.Foo} */ { prop: 1 });",
        "function f() { var /** string */ s = ns.Foo.prop; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "(/** @lends {Foo.prototype} */ { /** @type {number} */ a: 1 });",
        "var /** string */ s = Foo.prototype.a;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "(/** @lends {Foo.prototype} */ { /** @type {number} */ a: 1 });",
        "var /** string */ s = (new Foo).a;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {number} */ this.prop = 1; }",
        "(/** @lends {Foo.prototype} */",
        " { /** @return {number} */ m: function() { return this.prop; } });",
        "var /** string */ s = (new Foo).m();"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testEnumBasicTyping() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {",
        "  ONE: 1,",
        "  TWO: 2",
        "};",
        "function f(/** E */ x) { x < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @enum */",
        // No type annotation defaults to number
        "var E = {",
        "  ONE: 1,",
        "  TWO: 2",
        "};",
        "function f(/** E */ x) { x < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {",
        "  ONE: 1,",
        "  TWO: 2",
        "};",
        "function f(/** E */ x) {}",
        "function g(/** number */ x) {}",
        "f(E.TWO);",
        "g(E.TWO);"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {",
        "  ONE: 1,",
        "  TWO: 2",
        "};",
        "function f(/** E */ x) {}",
        "f(1);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {",
        "  ONE: 1,",
        "  TWO: 2",
        "};",
        "function f() { E.THREE - 5; }"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {!Foo} */",
        "var E = { ONE: new Foo };",
        "/** @constructor */",
        "function Foo() {}"));

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {number} */",
        "var num;",
        "/** @enum {num} */",
        "var E = { ONE: 1 };",
        "function f(/** E */ x) { x < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testEnumsWithNonScalarDeclaredType() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum {!Object} */ var E = {FOO: { prop: 1 }};",
        "E.FOO.prop - 5;"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {{prop: number}} */ var E = {FOO: { prop: 1 }};",
        "E.FOO.prop - 5;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const */ this.prop = 1;",
        "}",
        "/** @enum {!Foo} */",
        "var E = { ONE: new Foo() };",
        "function f(/** E */ x) { x.prop < 'str'; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const */ this.prop = 1;",
        "}",
        "/** @enum {!Foo} */",
        "var E = { ONE: new Foo() };",
        "function f(/** E */ x) { x.prop = 2; }"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @enum {!Foo} */",
        "var E = { A: new Foo };",
        "function f(/** E */ x) { x instanceof Foo; }"));
  }

  public void testEnumBadInitializer() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E;"),
        GlobalTypeInfo.MALFORMED_ENUM);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {};"),
        GlobalTypeInfo.MALFORMED_ENUM);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = 1;"),
        GlobalTypeInfo.MALFORMED_ENUM);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {",
        "  ONE: 1,",
        "  TWO: true",
        "};"),
        NewTypeInference.INVALID_OBJLIT_PROPERTY_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = { a: 1 };"),
        TypeCheck.ENUM_NOT_CONSTANT);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = { A: 1, A: 2 };"),
        GlobalTypeInfo.DUPLICATE_PROP_IN_ENUM);
  }

  public void testEnumPropertiesConstant() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {",
        "  ONE: 1,",
        "  TWO: 2",
        "};",
        "E.THREE = 3;"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {",
        "  ONE: 1,",
        "  TWO: 2",
        "};",
        "E.ONE = E.TWO;"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = {",
        "  ONE: 1,",
        "  TWO: 2",
        "};",
        "function f(/** E */) { E.ONE = E.TWO; }"),
        NewTypeInference.CONST_PROPERTY_REASSIGNED);
  }

  public void testEnumIllegalRecursion() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum {Type2} */",
        "var Type1 = {",
        "  ONE: null",
        "};",
        "/** @enum {Type1} */",
        "var Type2 = {",
        "  ONE: null",
        "};"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION,
        // This warning is a side-effect of the fact that, when there is a
        // cycle, the resolution of one enum will fail but the others will
        // complete successfully.
        NewTypeInference.INVALID_OBJLIT_PROPERTY_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {Type2} */",
        "var Type1 = {",
        "  ONE: null",
        "};",
        "/** @typedef {Type1} */",
        "var Type2;"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);
  }

  public void testEnumBadDeclaredType() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum {InexistentType} */",
        "var E = { ONE : null };"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {*} */",
        "var E = { ONE: 1, STR: '' };"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    // No free type variables in enums
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {",
        "  /** @enum {function(T):number} */",
        "  var E = { ONE: x };",
        "}"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {",
        "  /** @enum {T} */",
        "  var E1 = { ONE: 1 };",
        "  /** @enum {function(E1):E1} */",
        "  var E2 = { ONE: function(x) { return x; } };",
        "}"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " */",
        "function f(x) {",
        "  /** @typedef {T} */ var AliasT;",
        "  /** @enum {T} */",
        "  var E1 = { ONE: 1 };",
        "  /** @enum {function(E1):T} */",
        "  var E2 = { ONE: function(x) { return x; } };",
        "}"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME,
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME,
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    // No unions in enums
    typeCheck(Joiner.on('\n').join(
        "/** @enum {number|string} */",
        "var E = { ONE: 1, STR: '' };"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @enum {Foo} */",
        "var E = { ONE: new Foo, TWO: null };"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @typedef {number|string} */",
        "var NOS;",
        "/** @enum {NOS} */",
        "var E = { ONE: 1, STR: '' };"),
        RhinoErrorReporter.BAD_JSDOC_ANNOTATION);
  }

  public void testEnumsWithGenerics() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum */ var E1 = { A: 1};",
        "/**",
        " * @template T",
        " * @param {(T|E1)} x",
        " * @return {(T|E1)}",
        " */",
        "function f(x) { return x; }",
        "var /** string */ n = f('str');"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @enum */ var E1 = { A: 1};",
        "/** @enum */ var E2 = { A: 2};",
        "/**",
        " * @template T",
        " * @param {(T|E1)} x",
        " * @return {(T|E1)}",
        " */",
        "function f(x) { return x; }",
        "var /** (E2|string) */ x = f('str');"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @enum */",
        "var E = { A: 1 };",
        "/**",
        " * @template T",
        " * @param {number|!Array<T>} x",
        " */",
        "function f(x) {}",
        "f(E.A);",
        "f(123);"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum {string} */",
        "var e1 = { A: '' };",
        "/** @enum {string} */",
        "var e2 = { B: '' };",
        "/**",
        " * @template T",
        " * @param {T|e1} x",
        " * @return {T}",
        " */",
        "function f(x) { return /** @type {T} */ (x); }",
        "/** @param {number|e2} x */",
        "function g(x) { f(x) - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testEnumJoinSpecializeMeet() {
    // join: enum {number} with number
    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = { ONE: 1 };",
        "function f(cond) {",
        "  var x = cond ? E.ONE : 5;",
        "  x - 2;",
        "  var /** E */ y = x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    // join: enum {Low} with High, to High
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function High() {}",
        "/** @constructor @extends {High} */",
        "function Low() {}",
        "/** @enum {!Low} */",
        "var E = { A: new Low };",
        "function f(cond) {",
        "  var x = cond ? E.A : new High;",
        "  var /** High */ y = x;",
        "  var /** E */ z = x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    // join: enum {High} with Low, to (enum{High}|Low)
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function High() {}",
        "/** @constructor @extends {High} */",
        "function Low() {}",
        "/** @enum {!High} */",
        "var E = { A: new High };",
        "function f(cond) {",
        "  var x = cond ? E.A : new Low;",
        "  if (!(x instanceof Low)) { var /** E */ y = x; }",
        "}"));

    // meet: enum {?} with string, to enum {?}
    typeCheck(Joiner.on('\n').join(
        "/** @enum {?} */",
        "var E = { A: 123 };",
        "function f(x) {",
        "  var /** string */ s = x;",
        "  var /** E */ y = x;",
        "  s = x;",
        "}",
        "f('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // meet: E1|E2 with E1|E3, to E1
    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E1 = { ONE: 1 };",
        "/** @enum {number} */",
        "var E2 = { TWO: 1 };",
        "/** @enum {number} */",
        "var E3 = { THREE: 1 };",
        "function f(x) {",
        "  var /** (E1|E2) */ y = x;",
        "  var /** (E1|E3) */ z = x;",
        "  var /** E1 */ w = x;",
        "}",
        "f(E2.TWO);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // meet: enum {number} with number, to enum {number}
    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = { ONE: 1 };",
        "function f(x) {",
        "  var /** E */ y = x;",
        "  var /** number */ z = x;",
        "}",
        "f(123);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // meet: enum {Low} with High, to enum {Low}
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function High() {}",
        "/** @constructor @extends {High} */",
        "function Low() {}",
        "/** @enum {!Low} */",
        "var E = { A: new Low };",
        "function f(x) {",
        "  var /** !High */ y = x;",
        "  var /** E */ z = x;",
        "}",
        "f(new High);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // meet: enum {Low} with (High1|High2), to enum {Low}
    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function High1() {}",
        "/** @interface */",
        "function High2() {}",
        "/** @constructor @implements {High1} @implements {High2} */",
        "function Low() {}",
        "/** @enum {!Low} */",
        "var E = { A: new Low };",
        "function f(x) {",
        "  var /** (!High1 | !High2) */ y = x;",
        "  var /** E */ z = x;",
        "}",
        "f(/** @type {!High1} */ (new Low));"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // meet: enum {High} with Low
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function High() {}",
        "/** @constructor @extends {High} */",
        "function Low() {}",
        "/** @enum {!High} */",
        "var E = { A: new High };",
        "/** @param {function(E)|function(!Low)} x */",
        "function f(x) { x(123); }"),
        JSTypeCreatorFromJSDoc.UNION_IS_UNINHABITABLE);
  }

  public void testEnumAliasing() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var e1 = { A: 1 };",
        "/** @enum {number} */",
        "var e2 = e1;"));

    typeCheck(Joiner.on('\n').join(
        "var x;",
        "/** @enum {number} */",
        "var e1 = { A: 1 };",
        "/** @enum {number} */",
        "var e2 = x;"),
        GlobalTypeInfo.MALFORMED_ENUM);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns1 = {};",
        "/** @enum {number} */",
        "ns1.e1 = { A: 1 };",
        "/** @const */",
        "var ns2 = {};",
        "/** @enum {number} */",
        "ns2.e2 = ns1.e1;"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var e1 = { A: 1 };",
        "/** @enum {number} */",
        "var e2 = e1;",
        "function f(/** e2 */ x) {}",
        "f(e1.A);"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var e1 = { A: 1 };",
        "/** @enum {number} */",
        "var e2 = e1;",
        "function f(/** e2 */ x) {}",
        "f(e2.A);"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var e1 = { A: 1 };",
        "/** @enum {number} */",
        "var e2 = e1;",
        "function f(/** e2 */ x) {}",
        "f('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns1 = {};",
        "/** @enum {number} */",
        "ns1.e1 = { A: 1 };",
        "/** @const */",
        "var ns2 = {};",
        "/** @enum {number} */",
        "ns2.e2 = ns1.e1;",
        "function f(/** ns2.e2 */ x) {}",
        "f(ns1.e1.A);"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns1 = {};",
        "/** @enum {number} */",
        "ns1.e1 = { A: 1 };",
        "/** @const */",
        "var ns2 = {};",
        "/** @enum {number} */",
        "ns2.e2 = ns1.e1;",
        "function f(/** ns1.e1 */ x) {}",
        "f(ns2.e2.A);"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns1 = {};",
        "/** @enum {number} */",
        "ns1.e1 = { A: 1 };",
        "function g() {",
        "  /** @const */",
        "  var ns2 = {};",
        "  /** @enum {number} */",
        "  ns2.e2 = ns1.e1;",
        "  function f(/** ns1.e1 */ x) {}",
        "  f(ns2.e2.A);",
        "}"));
  }

  public void testNoDoubleWarnings() {
    typeCheck(
        "if ((4 - 'str') && true) { 4 + 5; }",
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("(4 - 'str') ? 5 : 6;", NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testRecordSpecializeNominalPreservesRequired() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {number|string} */ this.x = 5 };",
        "var o = true ? {x:5} : {y:'str'};",
        "if (o instanceof Foo) {",
        "  var /** {x:number} */ o2 = o;",
        "}",
        "(function(/** {x:number} */ o3){})(o);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testGoogIsPredicatesNoSpecializedContext() {
    typeCheck(CLOSURE_BASE + "goog.isNull();", TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(
        CLOSURE_BASE + "goog.isNull(1, 2, 5 - 'str');",
        TypeCheck.WRONG_ARGUMENT_COUNT,
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(CLOSURE_BASE
        + "function f(x) { var /** boolean */ b = goog.isNull(x); }");
  }

  public void testGoogIsPredicatesTrue() {
    typeCheck(CLOSURE_BASE
        + "function f(x) { if (goog.isNull(x)) { var /** undefined */ y = x; } }",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @param {number=} x */",
        "function f(x) {",
        "  if (goog.isDef(x)) {",
        "    x - 5;",
        "  }",
        "  x - 5;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {Foo=} x */",
        "function f(x) {",
        "  var /** !Foo */ y;",
        "  if (goog.isDefAndNotNull(x)) {",
        "    y = x;",
        "  }",
        "  y = x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (Array<number>|number) */ x) {",
        "  var /** Array<number> */ a;",
        "  if (goog.isArray(x)) {",
        "    a = x;",
        "  }",
        "  a = x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @param {null|function(number)} x */ ",
        "function f(x) {",
        "  if (goog.isFunction(x)) {",
        "    x('str');",
        "  }",
        "}"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(x) {",
        "  if (goog.isObject(x)) {",
        "    var /** null */ y = x;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  if (goog.isString(x)) {",
        "    x < 'str';",
        "  }",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  if (goog.isNumber(x)) {",
        "    x - 5;",
        "  }",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|boolean) */ x) {",
        "  if (goog.isBoolean(x)) {",
        "    var /** boolean */ b = x;",
        "  }",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/**",
        " * @param {number|string} x",
        " * @return {string}",
        " */",
        "function f(x) {",
        "  return goog.isString(x) && (1 < 2) ? x : 'a';",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/**",
        " * @param {*} o1",
        " * @param {*} o2",
        " * @return {boolean}",
        " */",
        "function deepEquals(o1, o2) {",
        "  if (goog.isObject(o1) && goog.isObject(o2)) {",
        "    if (o1.length != o2.length) {",
        "      return true;",
        "    }",
        "  }",
        "  return false;",
        "}"));
  }

  public void testGoogIsPredicatesFalse() {
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** Foo */ x) {",
        "  var /** !Foo */ y;",
        "  if (!goog.isNull(x)) {",
        "    y = x;",
        "  }",
        "  y = x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @param {number=} x */",
        "function f(x) {",
        "  if (!goog.isDef(x)) {",
        "    var /** undefined */ u = x;",
        "  }",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {Foo=} x */",
        "function f(x) {",
        "  if (!goog.isDefAndNotNull(x)) {",
        "    var /** (null|undefined) */ y = x;",
        "  }",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  if (!goog.isString(x)) {",
        "    x - 5;",
        "  }",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  if (!goog.isNumber(x)) {",
        "    x < 'str';",
        "  }",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|boolean) */ x) {",
        "  if (!goog.isBoolean(x)) {",
        "    x - 5;",
        "  }",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|!Array<number>) */ x) {",
        "  if (!goog.isArray(x)) {",
        "    x - 5;",
        "  }",
        "}"));
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(x) {",
        "  if (goog.isArray(x)) {",
        "    return x[0] - 5;",
        "  }",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|function(number)) */ x) {",
        "  if (!goog.isFunction(x)) {",
        "    x - 5;",
        "  }",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {?Foo} x */",
        "function f(x) {",
        "  if (!goog.isObject(x)) {",
        "    var /** null */ y = x;",
        "  }",
        "}"));
  }

  public void testGoogTypeof() {
    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  if (goog.typeOf(x) === 'number') {",
        "    var /** number */ n = x;",
        "  } else {",
        "    var /** string */ s = x;",
        "  }",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  if ('number' === goog.typeOf(x)) {",
        "    var /** number */ n = x;",
        "  }",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "function f(/** (number|string) */ x) {",
        "  if (goog.typeOf(x) == 'number') {",
        "    var /** number */ n = x;",
        "  }",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @param {number=} x */",
        "function f(x) {",
        "  if (goog.typeOf(x) === 'undefined') {",
        "    var /** undefined */ u = x;",
        "  } else {",
        "    var /** number */ n = x;",
        "  }",
        "}"));

    typeCheck(CLOSURE_BASE + Joiner.on('\n').join(
        "/** @param {string} x */",
        "function f(x, other) {",
        "  if (goog.typeOf(x) === other) {",
        "    var /** null */ n = x;",
        "  } else {",
        "    x - 5;",
        "  }",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS,
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testSuperClassCtorProperty() throws Exception {
    String CLOSURE_DEFS = Joiner.on('\n').join(
        "/** @const */ var goog = {};",
        "goog.inherits = function(child, parent){};");

    typeCheck(CLOSURE_DEFS + Joiner.on('\n').join(
        "/** @constructor */function base() {}",
        "/** @return {number} */ ",
        "  base.prototype.foo = function() { return 1; };",
        "/** @extends {base}\n * @constructor */function derived() {}",
        "goog.inherits(derived, base);",
        "var /** number */ n = derived.superClass_.foo()"));

    typeCheck(CLOSURE_DEFS + Joiner.on('\n').join(
        "/** @constructor */ function OldType() {}",
        "/** @param {?function(new:OldType)} f */ function g(f) {",
        "  /**",
        "    * @constructor",
        "    * @extends {OldType}",
        "    */",
        "  function NewType() {};",
        "  goog.inherits(NewType, f);",
        "  NewType.prototype.method = function() {",
        "    NewType.superClass_.foo.call(this);",
        "  };",
        "}"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(CLOSURE_DEFS + Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "goog.inherits(Foo, Object);",
        "var /** !Object */ b = Foo.superClass_;"));

    typeCheck(CLOSURE_DEFS + Joiner.on('\n').join(
        "/** @constructor */ function base() {}",
        "/** @constructor @extends {base} */ function derived() {}",
        "goog.inherits(derived, base);",
        "var /** null */ b = derived.superClass_"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        CLOSURE_DEFS + "var /** !Object */ b = Object.superClass_",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        CLOSURE_DEFS + "var o = {x: 'str'}; var q = o.superClass_;",
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(CLOSURE_DEFS
        + "var o = {superClass_: 'str'}; var /** string */ s = o.superClass_;");
  }

  public void testAcrossScopeNamespaces() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "(function() {",
        "  /** @constructor */",
        "  ns.Foo = function() {};",
        "})();",
        "ns.Foo();"),
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "(function() {",
        "  /** @type {string} */",
        "  ns.str = 'str';",
        "})();",
        "ns.str - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "(function() {",
        "  /** @constructor */",
        "  ns.Foo = function() {};",
        "})();",
        "function f(/** ns.Foo */ x) {}",
        "f(1);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "(function() {",
        "  /** @constructor */",
        "  ns.Foo = function() {};",
        "})();",
        "var /** ns.Foo */ x = 123;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testQualifiedNamedTypes() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @constructor */",
        "ns.Foo = function() {};",
        "ns.Foo();"),
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @typedef {number} */",
        "ns.num;",
        "var /** ns.num */ y = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @enum {number} */",
        "ns.Foo = { A: 1 };",
        "var /** ns.Foo */ y = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var E = { A: 1 };",
        "/** @typedef {number} */",
        "E.num;",
        "var /** E.num */ x = 'str';"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testEnumsAsNamespaces() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @enum {number} */",
        "ns.E = {",
        "  ONE: 1,",
        "  TWO: true",
        "};"),
        NewTypeInference.INVALID_OBJLIT_PROPERTY_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @enum */",
        "var E = { A: 1 };",
        "/** @enum */",
        "E.E2 = { B: true };",
        "var /** E */ x = E.A;"),
        NewTypeInference.INVALID_OBJLIT_PROPERTY_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @enum */",
        "var E = { A: 1 };",
        "/** @constructor */",
        "E.Foo = function(x) {};",
        "var /** E */ x = E.A;"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @enum {number} */",
        "ns.E = { A: 1 };",
        "/** @constructor */",
        "ns.E.Foo = function(x) {};"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @enum {number} */",
        "ns.E = { A: 1 };",
        "/** @constructor */",
        "ns.E.Foo = function(x) {};",
        "function f() { ns.E.Foo(); }"),
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);
  }

  public void testStringMethods() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function String(){}",
        "/** @this {String|string} */",
        "String.prototype.substr = function(start) {};",
        "/** @const */ var ns = {};",
        "/** @const */ var s = 'str';",
        "ns.r = s.substr(2);"));
  }

  public void testOutOfOrderDeclarations() {
    // This is technically valid JS, but we don't support it
    typeCheck("Foo.STATIC = 5; /** @constructor */ function Foo(){}");
  }

  public void testAbstractMethodsAreTypedCorrectly() {
    typeCheck(Joiner.on('\n').join(
        "/** @type {!Function} */",
        "var abstractMethod = function(){};",
        "/** @constructor */ function Foo(){};",
        "/** @constructor @extends {Foo} */ function Bar(){};",
        "/** @param {number} index */",
        "Foo.prototype.m = abstractMethod;",
        "/** @override */",
        "Bar.prototype.m = function(index) {};"));

    typeCheck(Joiner.on('\n').join(
        "/** @type {!Function} */",
        "var abstractMethod = function(){};",
        "/** @constructor */ function Foo(){};",
        "/** @constructor @extends {Foo} */ function Bar(){};",
        "/** @param {number} index */",
        "Foo.prototype.m = abstractMethod;",
        "/** @override */",
        "Bar.prototype.m = function(index) {};",
        "(new Bar).m('str');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @type {!Function} */",
        "var abstractMethod = function(){};",
        "/** @constructor */ function Foo(){};",
        "/** @constructor @extends {Foo} */ function Bar(){};",
        "/**",
        " * @param {number} b",
        " * @param {string} a",
        " */",
        "Foo.prototype.m = abstractMethod;",
        "/** @override */",
        "Bar.prototype.m = function(a, b) {};",
        "(new Bar).m('str', 5);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE,
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @type {!Function} */",
        "var abstractMethod = function(){};",
        "/** @constructor */ function Foo(){};",
        "/** @constructor @extends {Foo} */ function Bar(){};",
        "/** @type {function(number, string)} */",
        "Foo.prototype.m = abstractMethod;",
        "/** @override */",
        "Bar.prototype.m = function(a, b) {};",
        "(new Bar).m('str', 5);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE,
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testUseJsdocOfCalleeForUnannotatedFunctionsInArgumentPosition() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {string} */ this.prop = 'asdf'; }",
        "/** @param {function(!Foo)} fun */",
        "function f(fun) {}",
        "f(function(x) { x.prop = 123; });"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { /** @type {string} */ this.prop = 'asdf'; }",
        "function f(/** function(this:Foo) */ x) {}",
        "f(function() { this.prop = 123; });"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(string)} fun */",
        "function f(fun) {}",
        "f(function(str) { str - 5; });"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(number, number=)} fun */",
        "function f(fun) {}",
        "f(function(num, maybeNum) { num - maybeNum; });"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {function(string, ...string)} fun */",
        "function f(fun) {}",
        "f(function(str, maybeStrs) { str - 5; });"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @param {function(string)} fun */",
        "ns.f = function(fun) {}",
        "ns.f(function(str) { str - 5; });"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @type {function(function(string))} */",
        "ns.f = function(fun) {}",
        "ns.f(function(str) { str - 5; });"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @param {function(string)} fun */",
        "Foo.f = function(fun) {}",
        "Foo.f(function(str) { str - 5; });"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "(/** @param {function(string)} fun */ function(fun) {})(",
        "  function(str) { str - 5; });"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @param {function(function(function(string)))} outerFun */",
        "ns.f = function(outerFun) {};",
        "ns.f(function(innerFun) {",
        "  innerFun(function(str) { str - 5; });",
        "});"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testNamespacesWithNonEmptyObjectLiteral() {
    typeCheck("/** @const */ var o = { /** @const */ PROP: 5 };");

    typeCheck(
        "var x = 5; /** @const */ var o = { /** @const {number} */ PROP: x };");

    typeCheck(Joiner.on('\n').join(
        "var x = 'str';",
        "/** @const */ var o = { /** @const {string} */ PROP: x };",
        "function g() { o.PROP - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "/** @const */ ns.o = { /** @const */ PROP: 5 };"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "var x = 5;",
        "/** @const */ ns.o = { /** @const {number} */ PROP: x };"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */ var ns = {};",
        "var x = 'str';",
        "/** @const */ ns.o = { /** @const {string} */ PROP: x };",
        "function g() { ns.o.PROP - 5; }"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    // These declarations are not considered namespaces
    typeCheck(
        "(function(){ return {}; })().ns = { /** @const */ PROP: 5 };",
        GlobalTypeInfo.MISPLACED_CONST_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "function f(/** { x : string } */ obj) {",
        "  obj.ns = { /** @const */ PROP: 5 };",
        "}"),
        GlobalTypeInfo.MISPLACED_CONST_ANNOTATION);
  }

  // TODO(dimvar): fix
  public void testAllTestsShouldHaveDupPropWarnings() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.Foo = {};",
        "ns.Foo = { a: 123 };"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.Foo = {};",
        "/** @const */",
        "ns.Foo = { a: 123 };"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.Foo = {};",
        "/**",
        " * @const",
        // @suppress is ignored here b/c there is no @type in the jsdoc.
        " * @suppress {duplicate}",
        " */",
        "ns.Foo = { a: 123 };"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @const */",
        "ns.Foo = {};",
        "/** @type {number} */",
        "ns.Foo = 123;"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum {number} */",
        "var en = { A: 5 };",
        "/** @const */",
        "en.Foo = {};",
        "/** @type {number} */",
        "en.Foo = 123;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @const */",
        "Foo.ns = {};",
        "/** @const */",
        "Foo.ns = {};"));
  }

  public void testNominalTypeAliasing() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "var Bar = Foo;",
        "var /** !Bar */ x = new Foo();"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @constructor */",
        "ns.Foo = function() {};",
        "/** @constructor */",
        "ns.Bar = ns.Foo;",
        "function g() {",
        "  var /** !ns.Bar */ x = new ns.Foo();",
        "  var /** !ns.Bar */ y = new ns.Bar();",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @type {number} */",
        "var n = 123;",
        "/** @constructor */",
        "var Foo = n;"),
        GlobalTypeInfo.EXPECTED_CONSTRUCTOR);

    typeCheck(Joiner.on('\n').join(
        "/** @type {number} */",
        "var n = 123;",
        "/** @interface */",
        "var Foo = n;"),
        GlobalTypeInfo.EXPECTED_INTERFACE);

    typeCheck(Joiner.on('\n').join(
        "/** @interface */",
        "function Foo() {}",
        "/** @constructor */",
        "var Bar = Foo;"),
        GlobalTypeInfo.EXPECTED_CONSTRUCTOR);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @interface */",
        "var Bar = Foo;"),
        GlobalTypeInfo.EXPECTED_INTERFACE);

    // TODO(dimvar): When we allow unknown type names, eg, for fwd-declared
    // types, then we can also fix this.
    // Currently, the type checker doesn't know what !Foo is.
    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "var Bar;",
        Joiner.on('\n').join(
            "/**",
            " * @constructor",
            " * @final",
            " */",
            "var Foo = Bar;",
            "var /** !Foo */ x;"),
        GlobalTypeInfo.EXPECTED_CONSTRUCTOR);
  }

  public void testTypeVariablesVisibleInPrototypeMethods() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo() {}",
        "Foo.prototype.method = function() {",
        "  /** @type {T} */",
        "  this.prop = 123;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo() {}",
        "/** @param {T} x */",
        "Foo.prototype.method = function(x) {",
        "  x = 123;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo() {}",
        "/** @param {T} x */",
        "Foo.prototype.method = function(x) {",
        "  this.prop = x;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo() {}",
        "/** @param {T} x */",
        "Foo.prototype.method = function(x) {",
        "  /** @const */",
        "  this.prop = x;",
        "}"),
        GlobalTypeInfo.MISPLACED_CONST_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Parent() {}",
        "/**",
        " * @constructor",
        " * @extends {Parent<string>}",
        " */",
        "function Child() {}",
        "Child.prototype.method = function() {",
        "  /** @type {T} */",
        "  this.prop = 123;",
        "}"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);
  }

  public void testInferConstTypeFromEnumProps() {
    typeCheck(Joiner.on('\n').join(
        "/** @enum */",
        "var e = { A: 1 };",
        "/** @const */",
        "var numarr = [ e.A ];"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum */",
        "var e = { A: 1 };",
        "/** @type {number} */",
        "e.prop = 123;",
        "/** @const */",
        "var x = e.prop;"),
        GlobalTypeInfo.COULD_NOT_INFER_CONST_TYPE);
  }

  private static final String FORWARD_DECLARATION_DEFINITIONS = Joiner.on('\n').join(
        "/** @const */ var goog = {};",
        "goog.addDependency = function(file, provides, requires){};",
        "goog.forwardDeclare = function(name){};");

  public void testForwardDeclarations() {

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "goog.addDependency('', ['Foo'], []);",
        "goog.forwardDeclare('Bar');",
        "function f(/** !Foo */ x) {}",
        "function g(/** !Bar */ y) {}"));

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "/** @const */ var ns = {};",
        "goog.addDependency('', ['ns.Foo'], []);",
        "goog.forwardDeclare('ns.Bar');",
        "function f(/** !ns.Foo */ x) {}",
        "function g(/** !ns.Bar */ y) {}"));

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "/** @const */ var ns = {};",
        "goog.forwardDeclare('ns.Bar');",
        "function f(/** !ns.Baz */ x) {}"),
        GlobalTypeInfo.UNRECOGNIZED_TYPE_NAME);

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "goog.addDependency('', ['Foo'], []);",
        "goog.forwardDeclare('Bar');",
        "var f = new Foo;",
        "var b = new Bar;"));

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "/** @const */ var ns = {};",
        "goog.addDependency('', ['ns.Foo'], []);",
        "goog.forwardDeclare('ns.Bar');",
        "var f = new ns.Foo;",
        "var b = new ns.Bar;"));

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "/** @const */ var ns = {};",
        "goog.addDependency('', ['ns.subns.Foo'], []);",
        "goog.forwardDeclare('ns.subns.Bar');",
        "var f = new ns.subns.Foo;",
        "var b = new ns.subns.Bar;"));

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "goog.addDependency('', ['ns.subns.Foo'], []);",
        "goog.forwardDeclare('ns.subns.Bar');",
        "var f = new ns.subns.Foo;",
        "var b = new ns.subns.Bar;"));

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "goog.forwardDeclare('ns.subns');",
        "goog.forwardDeclare('ns.subns.Bar');",
        "var b = new ns.subns.Bar;"));

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "goog.forwardDeclare('num');",
        "/** @type {number} */ var num = 5;",
        "function f() { var /** null */ o = num; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "goog.forwardDeclare('Foo');",
        "/** @constructor */ function Foo(){}",
        "function f(/** !Foo */ x) { var /** null */ n = x; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "goog.forwardDeclare('ns.Foo');",
        "/** @const */ var ns = {};",
        "/** @constructor */ ns.Foo = function(){}",
        "function f(/** !ns.Foo */ x) { var /** null */ n = x; }"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    // In the following cases the old type inference warned about arg type,
    // but we allow rather than create synthetic named type
    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "goog.forwardDeclare('Foo');",
        "function f(/** !Foo */ x) {}",
        "/** @constructor */ function Bar(){}",
        "f(new Bar);"));

    typeCheck(Joiner.on('\n').join(FORWARD_DECLARATION_DEFINITIONS,
        "/** @const */ var ns = {};",
        "goog.forwardDeclare('ns.Foo');",
        "function f(/** !ns.Foo */ x) {}",
        "/** @constructor */ function Bar(){}",
        "f(new Bar);"));
  }

  public void testDontLookupInParentScopeForNamesWithoutDeclaredType() {
    typeCheck(Joiner.on('\n').join(
        "/** @type {number} */",
        "var x;",
        "function f() {",
        "  var x = true;",
        "}"));
  }

  public void testSpecializationInPropertyAccesses() {
    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @type {?number} */ ns.n = 123;",
        "if (ns.n === null) {",
        "} else {",
        "  ns.n - 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @const */",
        "var ns = {};",
        "/** @type {?number} */ ns.n = 123;",
        "if (ns.n !== null) {",
        "  ns.n - 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "var obj = { n: (1 < 2 ? null : 123) };",
        "if (obj.n !== null) {",
        "  obj.n - 123;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "var obj = { n: (1 < 2 ? null : 123) };",
        "if (obj.n !== null) {",
        "  obj.n - 123;",
        "}",
        "obj.n - 123;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  this.a = 123;",
        "}",
        "/** @constructor */",
        "function Bar(x) {",
        "  /** @type {Foo} */",
        "  this.b = x;",
        "  if (this.b != null) {",
        "    return this.b.a;",
        "  }",
        "}"));
  }

  public void testAutoconvertBoxedNumberToNumber() {
    typeCheck(
        "var /** !Number */ n = 123;", NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "var /** number */ n = new Number(123);",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Number */ x, y) {",
        "  return x - y;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(x, /** !Number */ y) {",
        "  return x - y;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Number */ x) {",
        "  return x + 'asdf';",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Number */ x) {",
        "  return -x;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Number */ x) {",
        "  x -= 123;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Number */ x, y) {",
        "  y -= x;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Number */ x, /** !Array<string>*/ arr) {",
        "  return arr[x];",
        "}"));
  }

  public void testAutoconvertBoxedStringToString() {
    typeCheck(
        "var /** !String */ s = '';", NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "var /** string */ s = new String('');",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  var /** !String */ x;",
        "  for (x in { p1: 123, p2: 234 }) ;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** !String */ x) {",
        "  return x + 1;",
        "}"));
  }

  public void testAutoconvertBoxedBooleanToBoolean() {
    typeCheck(
        "var /** !Boolean */ b = true;", NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "var /** boolean */ b = new Boolean(true);",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** !Boolean */ x) {",
        "  if (x) { return 123; };",
        "}"));
  }

  public void testAutoconvertScalarsToBoxedScalars() {
    typeCheck(Joiner.on('\n').join(
        "var /** number */ n = 123;",
        "n.toString();"));

    typeCheck(Joiner.on('\n').join(
        "var /** boolean */ b = true;",
        "b.toString();"));

    typeCheck(Joiner.on('\n').join(
        "var /** string */ s = '';",
        "s.toString();"));

    typeCheck(Joiner.on('\n').join(
        "var /** number */ n = 123;",
        "n.prop = 0;",
        "n.prop - 5;"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "var /** number */ n = 123;",
        "n['to' + 'String'];"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {number} */",
        "  this.prop = 123;",
        "}",
        "(new Foo).prop.newprop = 5;"));

    typeCheck(Joiner.on('\n').join(
        "/** @enum */",
        "var E = { A: 1 };",
        "function f(/** E */ x) {",
        "  return x.toString();",
        "}"),
        NewTypeInference.PROPERTY_ACCESS_ON_NONOBJECT);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype.toString = function() {};",
        "function f(/** (number|!Foo) */ x) {",
        "  return x.toString();",
        "}"));
  }

  public void testConstructorsCalledWithoutNew() {
    typeCheck(Joiner.on('\n').join(
        "var n = new Number();",
        "n.prop = 0;",
        "n.prop - 5;"));

    typeCheck(Joiner.on('\n').join(
        "var n = Number();",
        "n.prop = 0;",
        "n.prop - 5;"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor @return {number} */ function Foo(){ return 5; }",
        "var /** !Foo */ f = new Foo;",
        "var /** number */ n = Foo();"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo(){ return 5; }",
        "var /** !Foo */ f = new Foo;",
        "var n = Foo();"),
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);

    // For constructors, return of ? is interpreted the same as undeclared
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @return {?} */ function Foo(){}",
        "var /** !Foo */ f = new Foo;",
        "var n = Foo();"),
        TypeCheck.CONSTRUCTOR_NOT_CALLABLE);
  }

  public void testFunctionBind() {
    // Don't handle specially
    typeCheck(Joiner.on('\n').join(
        "var obj = { bind: function() { return 'asdf'; } };",
        "obj.bind() - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { return x; }",
        "f.bind(null, 1, 2);"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { return x; }",
        "f.bind();"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { return x - 1; }",
        "var g = f.bind(null);",
        "g();"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "function f() {}",
        "f.bind(1);"),
        NewTypeInference.INVALID_THIS_TYPE_IN_BIND);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {}",
        "/** @this {!Foo} */",
        "function f() {}",
        "f.bind(new Bar);"),
        NewTypeInference.INVALID_THIS_TYPE_IN_BIND);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, /** number */ y) { return x - y; }",
        "var g = f.bind(null, 123);",
        "g('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, y) { return x - y; }",
        "var g = f.bind(null, 123);",
        "g('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) { return x - 1; }",
        "var g = f.bind(null, 'asdf');",
        "g() - 3;"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {number=} x */",
        "function f(x) {}",
        "var g = f.bind(null);",
        "g();",
        "g('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {...number} var_args */",
        "function f(var_args) {}",
        "var g = f.bind(null);",
        "g();",
        "g(123, 'asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {number=} x */",
        "function f(x) {}",
        "f.bind(null, undefined);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "f.bind(null, 1, 2);"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "var g = f.bind(null, 1);",
        "g(2);",
        "g('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // T was instantiated to ? in the f.bind call.
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "var g = f.bind(null);",
        "g(2, 'asdf');"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "f.bind(null, 1, 'asdf');"),
        NewTypeInference.NOT_UNIQUE_INSTANTIATION);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " * @param {T} x",
        " */",
        " function Foo(x) {}",
        "/**",
        " * @template T",
        " * @this {Foo<T>}",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "function f(x, y) {}",
        "f.bind(new Foo('asdf'), 1, 2);"),
        NewTypeInference.INVALID_THIS_TYPE_IN_BIND);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " * @param {T} x",
        " */",
        " function Foo(x) {}",
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {T} y",
        " */",
        "Foo.prototype.f = function(x, y) {};",
        "Foo.prototype.f.bind(new Foo('asdf'), 1, 2);"),
        NewTypeInference.INVALID_THIS_TYPE_IN_BIND);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.bind(new Foo);"),
        NewTypeInference.CANNOT_BIND_CTOR);

    // We can't detect that f takes a string
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " * @param {T} x",
        " */",
        "function Foo(x) {}",
        "/**",
        " * @template T",
        " * @this {Foo<T>}",
        " * @param {T} x",
        " */",
        "function poly(x) {}",
        "function f(x) {",
        "  poly.bind(new Foo('asdf'), x);",
        "}",
        "f(123);"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {string} */",
        "  this.p = 'asdf';",
        "}",
        "(function() { this.p - 5; }).bind(new Foo);"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {number} */",
        "  this.p = 123;",
        "}",
        "(function(x) { this.p - x; }).bind(new Foo, 321);"));
  }

  public void testClosureStyleFunctionBind() {
    typeCheck(
        "goog.bind(123, null);", NewTypeInference.GOOG_BIND_EXPECTS_FUNCTION);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { return x; }",
        "goog.bind(f, null, 1, 2);"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "function f(x) { return x; }",
        "goog.bind(f);"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "function f() {}",
        "goog.bind(f, 1);"),
        NewTypeInference.INVALID_THIS_TYPE_IN_BIND);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, /** number */ y) { return x - y; }",
        "var g = goog.bind(f, null, 123);",
        "g('asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) { return x - 1; }",
        "var g = goog.partial(f, 'asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) { return x - 1; }",
        "var g = goog.partial(f, 'asdf');",
        "g() - 3;"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  if (typeof x == 'function') {",
        "    goog.bind(x, {}, 1, 2);",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {string} */",
        "  this.p = 'asdf';",
        "}",
        "goog.bind(function() { this.p - 5; }, new Foo);"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck("goog.partial(function(x) {}, 123)");

    typeCheck("goog.bind(function() {}, null)();");
  }

  public void testPlusBackwardInference() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, w) {",
        "  var y = x + 2;",
        "  function g() { return (y + 2) - 5; }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x, w) {",
        "  function h() { return (w + 2) - 5; }",
        "}"));
  }

  public void testPlus() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {!Foo} x */",
        "function f(x, i) {",
        "  var /** string */ s = x[i];",
        "  var /** number */ y = x[i] + 123;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** ? */ x) {",
        "  var /** string */ s = '' + x;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** ? */ x) {",
        "  var /** number */ s = '' + x;",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "function f(/** ? */ x, /** ? */ y) {",
        "  var /** number */ s = x + y;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** * */ x) {",
        "  var /** number */ n = x + 1;",
        "  var /** string */ s = 1 + x;",
        "}"),
        NewTypeInference.INVALID_OPERAND_TYPE,
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "var /** number */ n = 1 + null;",
        "var /** string */ s = 1 + null;"),
        NewTypeInference.INVALID_OPERAND_TYPE,
        NewTypeInference.INVALID_OPERAND_TYPE,
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var /** number */ n = undefined + 2;",
        "var /** string */ s = undefined + 2;"),
        NewTypeInference.INVALID_OPERAND_TYPE,
        NewTypeInference.INVALID_OPERAND_TYPE,
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "var /** number */ n = 3 + true;",
        "var /** string */ s = 3 + true;"),
        NewTypeInference.INVALID_OPERAND_TYPE,
        NewTypeInference.INVALID_OPERAND_TYPE,
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheckCustomExterns(
        DEFAULT_EXTERNS + "/** @type {number} */ var NaN;",
        Joiner.on('\n').join(
            "var /** number */ n = NaN + 1;",
            "var /** string */ s = NaN + 1;"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testUndefinedFunctionCtorNoCrash() {
    typeCheckCustomExterns("", "function f(x) {}",
        GlobalTypeInfo.FUNCTION_CONSTRUCTOR_NOT_DEFINED);

    // Test that NTI is not run
    typeCheckCustomExterns("", "function f(x) { 1 - 'asdf'; }",
        GlobalTypeInfo.FUNCTION_CONSTRUCTOR_NOT_DEFINED);
  }

  public void testTrickyPropertyJoins() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @type {number} */",
        "Foo.prototype.length;",
        "/** @param {{length:number}|!Foo} x */",
        "function f(x) {",
        "  return x.length - 123;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @type {number} */",
        "Foo.prototype.length;",
        "/** @param {null|{length:number}|!Foo} x */",
        "function f(x) {",
        "  return x.length - 123;",
        "}"),
        NewTypeInference.NULLABLE_DEREFERENCE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @type {number} */",
        "Foo.prototype.length;",
        "/** @param {null|!Foo|{length:number}} x */",
        "function f(x) {",
        "  return x.length - 123;",
        "}"),
        NewTypeInference.NULLABLE_DEREFERENCE);
  }

  public void testJoinOfClassyAndLooseObject() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo(){}",
        "/** @type {number} */",
        "Foo.prototype.p = 5;",
        "function f(o) {",
        "  if (o.p == 5) {",
        "    (function(/** !Foo */ x){})(o);",
        "  }",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() { this.p = 123; }",
        "function f(x) {",
        "  var y;",
        "  if (x.p) {",
        "    y = x;",
        "  } else {",
        "    y = new Foo;",
        "    y.prop = 'asdf';",
        "  }",
        "  y.p -123;",
        "}"));
  }

  public void testUnificationWithSubtyping() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */ function Foo() {}",
        "/** @constructor @extends {Foo} */ function Bar() {}",
        "/** @constructor @extends {Foo} */ function Baz() {}",
        "/**",
        " * @template T",
        " * @param {T|!Foo} x",
        " * @param {T} y",
        " * @return {T}",
        " */",
        "function f(x, y) { return y; }",
        "/** @param {!Bar|!Baz} x */",
        "function g(x) {",
        "  f(x, 123) - 123;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Parent() {}",
        "/** @constructor @extends {Parent} */",
        "function Child() {}",
        "/**",
        " * @template T",
        " * @param {T|!Parent} x",
        " * @return {T}",
        " */",
        "function f(x) { return /** @type {?} */ (x); }",
        "function g(/** (number|!Child) */ x) {",
        "  f(x) - 5;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Parent() {}",
        "/**",
        " * @constructor",
        " * @extends {Parent<number>}",
        " */",
        "function Child() {}",
        "/**",
        " * @template T",
        " * @param {!Parent<T>} x",
        " */",
        "function f(x) {}",
        "/**",
        " * @param {!Child} x",
        " */",
        "function g(x) { f(x); }"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Parent() {}",
        "/**",
        " * @constructor",
        " * @template U",
        " * @extends {Parent<U>}",
        " */",
        "function Child() {}",
        "/**",
        " * @template T",
        " * @param {!Child<T>} x",
        " */",
        "function f(x) {}",
        "/**",
        " * @param {!Parent<number>} x",
        " */",
        "function g(x) { f(x); }"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @constructor",
        " */",
        "function High() {}",
        "/** @constructor @extends {High<number>} */",
        "function Low() {}",
        "/**",
        " * @template T",
        " * @param {!High<T>} x",
        " * @return {T}",
        " */",
        "function f(x) { return /** @type {?} */ (null); }",
        "var /** string */ s = f(new Low);"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function High() {}",
        "/** @return {T} */",
        "High.prototype.get = function() { return /** @type {?} */ (null); };",
        "/**",
        " * @constructor",
        " * @template U",
        " * @extends {High<U>}",
        " */",
        "function Low() {}",
        "/**",
        " * @template V",
        " * @param {!High<V>} x",
        " * @return {V}",
        " */",
        "function f(x) { return x.get(); }",
        "/** @param {!Low<number>} x */",
        "function g(x) {",
        "  var /** number */ n = f(x);",
        "  var /** string */ s = f(x);",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @interface",
        " * @template T",
        " */",
        "function High() {}",
        "/**",
        " * @constructor",
        " * @template T",
        " * @implements {High<T>}",
        " */",
        "function Mid() {}",
        "/**",
        " * @constructor",
        " * @template T",
        " * @extends {Mid<T>}",
        " * @param {T} x",
        " */",
        "function Low(x) {}",
        "/**",
        " * @template T",
        " * @param {!High<T>} x",
        " * @return {T}",
        " */",
        "function f(x) {",
        "  return /** @type {?} */ (null);",
        "}",
        "f(new Low('asdf')) - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testArgumentsArray() {
    typeCheck("arguments = 123;",
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(
        "function f(x, i) { return arguments[i]; }");

    typeCheck(
        "function f(x) { return arguments['asdf']; }",
        NewTypeInference.NON_NUMERIC_ARRAY_INDEX);

    // Arguments is array-like, but not Array
    typeCheck(
        "function f() { return arguments.splice(); }",
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "function f(x, i) { return arguments[i]; }",
        "f(123, 'asdf')"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f() {",
        "  var arguments = 1;",
        "  return arguments - 1;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @param {string} var_args */",
        "function f(var_args) {",
        "  return arguments[0];",
        "}",
        "f('asdf') - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @param {string} var_args */",
        "function f(var_args) {",
        "  var x = arguments;",
        "  return x[0];",
        "}",
        "f('asdf') - 5;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(x, i) {",
        "  x < i;",
        "  arguments[i];",
        "}",
        "f('asdf', 0);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);
  }

  public void testGenericResolutionWithPromises() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @param {function():(T|!Promise<T>)} x",
        " * @return {!Promise<T>}",
        " * @template T",
        " */",
        "function f(x) { return /** @type {?} */ (null); }",
        "function g(/** function(): !Promise<number> */ x) {",
        "  var /** !Promise<number> */ n = f(x);",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {(T|!Promise<T>)} x",
        " * @return {T}",
        " */",
        "function f(x) { return /** @type {?} */ (null); }",
        "function g(/** !Promise<number> */ x) {",
        "  var /** number */ n = f(x);",
        "  var /** string */ s = f(x);",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);
  }

  public void testFunctionCallProperty() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) {}",
        "f.call(null, 'asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) {}",
        "f.call(null);"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) {}",
        "f.call(null, 1, 2);"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {number} x */",
        "Foo.prototype.f = function(x) {};",
        "Foo.prototype.f.call({ a: 123}, 1);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // We don't infer anything about a loose function from a .call invocation.
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x(123) - 5;",
        "  x.call(null, 'asdf');",
        "}",
        "f(function(/** string */ s) { return s; });"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function f(x) { return x; }",
        "var /** number */ n = f.call(null, 'asdf');"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "new Foo.call(null);"),
        NewTypeInference.NOT_A_CONSTRUCTOR);
  }

  public void testFunctionApplyProperty() {
    // We only check the receiver argument of a .apply invocation
    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) {}",
        "f.apply(null, ['asdf']);"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) {}",
        "f.apply(null, 'asdf');"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // We don't check arity in the array argument
    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) {}",
        "f.apply(null, []);"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** number */ x) {}",
        "f.apply(null, [], 1, 2);"),
        TypeCheck.WRONG_ARGUMENT_COUNT);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @param {number} x */",
        "Foo.prototype.f = function(x) {};",
        "Foo.prototype.f.apply({ a: 123}, [1]);"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    // We don't infer anything about a loose function from a .apply invocation.
    typeCheck(Joiner.on('\n').join(
        "function f(x) {",
        "  x(123) - 5;",
        "  x.apply(null, ['asdf']);",
        "}",
        "f(function(/** string */ s) { return s; });"),
        NewTypeInference.INVALID_ARGUMENT_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @return {T}",
        " */",
        "function f(x) { return x; }",
        "var /** number */ n = f.apply(null, ['asdf']);"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "new Foo.apply(null);"),
        NewTypeInference.NOT_A_CONSTRUCTOR);

    typeCheck(Joiner.on('\n').join(
        "function f(x) {}",
        "function g() { f.apply(null, arguments); }"));
  }

  public void testDontWarnOnPropAccessOfBottom() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Bar() {",
        "  /** @type {?Object} */",
        "  this.obj;",
        "}",
        "Bar.prototype.f = function() {",
        "  this.obj = {};",
        "  if (this.obj != null) {}",
        "};"));

    typeCheck(Joiner.on('\n').join(
        "var x = {};",
        "x.obj = {};",
        "if (x.obj != null) {}"));

    typeCheck(Joiner.on('\n').join(
        "var x = {};",
        "x.obj = {};",
        "if (x['obj'] != null) {}"));
  }

  public void testClasslessObjectsHaveBuiltinProperties() {
    typeCheck(Joiner.on('\n').join(
        "function f(/** !Object */ x) {",
        "  return x.hasOwnProperty('asdf');",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "function f(/** { a: number } */ x) {",
        "  return x.hasOwnProperty('asdf');",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "var x = {};",
        "x.hasOwnProperty('asdf');"));

    typeCheck(Joiner.on('\n').join(
        "var x = /** @struct */ { a: 1 };",
        "x.hasOwnProperty('asdf');"));

    typeCheck(Joiner.on('\n').join(
        "var x = /** @dict */ { 'a': 1 };",
        "x['hasOwnProperty']('asdf');"));
  }

  public void testInferThisInSimpleInferExprType() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @const */ var x = this",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {string} */",
        "  this.p = 'asdf';",
        "}",
        "Foo.prototype.m = function() {",
        "  goog.bind(function() { this.p - 5; }, this);",
        "};"),
        NewTypeInference.INVALID_OPERAND_TYPE);
  }

  public void testNoInexistentPropWarningsForDicts() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor @dict */",
        "function Foo() {}",
        "(new Foo)['prop'] - 1;"));
  }

  public void testAddingPropsToExpandosInWhateverScopes() {
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** !Foo */ x) {",
        "  x.prop = 123;",
        "}",
        "(new Foo).prop - 1;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** !Foo */ x) {",
        "  x.prop = 'asdf';", // we don't declare the type to be string
        "}",
        "(new Foo).prop - 1;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f() {",
        "  var x = new Foo;",
        "  x.prop = 123;", // x not inferred as Foo during GTI
        "}",
        "(new Foo).prop - 1;"),
        TypeCheck.INEXISTENT_PROPERTY);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** !Foo */ x) {",
        "  /** @const */",
        "  x.prop = 123;",
        "}",
        "(new Foo).prop - 1;"),
        GlobalTypeInfo.MISPLACED_CONST_ANNOTATION);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "function f(/** !Foo */ x) {",
        "  /** @type {string} */",
        "  x.prop = 'asdf';",
        "}",
        "(new Foo).prop - 123;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function High() {}",
        "function f(/** !High */ x) {",
        "  /** @type {string} */",
        "  x.prop = 'asdf';",
        "}",
        "/** @constructor @extends {High} */",
        "function Low() {}",
        "(new Low).prop - 123;"),
        NewTypeInference.INVALID_OPERAND_TYPE);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {number} */",
        "  this.prop = 123;",
        "}",
        "function f(/** !Foo */ x) {",
        "  /** @type {string} */",
        "  x.prop = 'asdf';",
        "}"),
        GlobalTypeInfo.REDECLARED_PROPERTY,
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {",
        "  /** @type {number} */",
        "  this.prop = 123;",
        "}",
        "function f(/** !Foo */ x) {",
        "  x.prop = 'asdf';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @type {number} */",
        "Foo.prototype.prop = 123;",
        "function f(/** !Foo */ x) {",
        "  x.prop = 'asdf';",
        "}"),
        NewTypeInference.MISTYPED_ASSIGN_RHS);

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo() {}",
        "function f(/** !Foo<string> */ x) {",
        "  x.prop = 123;",
        "}",
        "(new Foo).prop - 1;"));

    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @constructor",
        " * @template T",
        " */",
        "function Foo(/** T */ x) {}",
        "/** @template U */",
        "function addProp(/** !Foo<U> */ x, /** U */ y) {",
        "  /** @type {U} */ x.prop = y;",
        "  return x;",
        "}",
        "addProp(new Foo(1), 5).prop - 1;"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype.m = function() {",
        "  this.prop = 123;",
        "}",
        "function f(/** !Foo */ x) {",
        "  /** @type {number} */",
        "  x.prop = 123;",
        "}"));

    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "Foo.prototype.prop = 123;",
        "/** @type {!Foo} */",
        "var x = new Foo;",
        "/** @type {number} */",
        "x.prop = 123;"));
  }

  public void testFunctionSubtypingWithReceiverTypes() {
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {function(this:T)} x",
        " */",
        "function f(x) {}",
        "/** @constructor */",
        "function Foo() {}",
        "f(/** @this{Foo} */ function () {});"));

    // We don't catch the NOT_UNIQUE_INSTANTIATION warning
    typeCheck(Joiner.on('\n').join(
        "/**",
        " * @template T",
        " * @param {T} x",
        " * @param {function(this:T)} y",
        " */",
        "function f(x, y) {}",
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {}",
        "f(new Bar, /** @this{Foo} */function () {});"));

    // Sets Bar#p to a number but we don't catch it
    typeCheck(Joiner.on('\n').join(
        "/** @constructor */",
        "function Foo() {}",
        "/** @constructor */",
        "function Bar() {",
        "  /** @type {string} */ this.p = 'asdf';",
        "}",
        "/**",
        " * @this {Foo}",
        " * @param {number} x",
        " */",
        "function f(x) { this.p = x; }",
        "/** @param {function(number)} x */",
        "function g(x) { x.call(new Bar, 123); }",
        "g(f);"));
  }
}
