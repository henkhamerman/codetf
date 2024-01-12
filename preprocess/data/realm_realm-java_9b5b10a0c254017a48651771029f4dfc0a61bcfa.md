Refactoring Types: ['Move Attribute']
c/main/java/io/realm/processor/ClassMetaData.java
/*
 * Copyright 2014 Realm Inc.
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

package io.realm.processor;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.annotation.processing.Messager;
import javax.annotation.processing.ProcessingEnvironment;
import javax.lang.model.element.Element;
import javax.lang.model.element.ElementKind;
import javax.lang.model.element.ExecutableElement;
import javax.lang.model.element.Modifier;
import javax.lang.model.element.PackageElement;
import javax.lang.model.element.TypeElement;
import javax.lang.model.element.VariableElement;
import javax.lang.model.type.DeclaredType;
import javax.lang.model.type.TypeKind;
import javax.lang.model.type.TypeMirror;
import javax.lang.model.util.Types;

import io.realm.annotations.Ignore;
import io.realm.annotations.Index;
import io.realm.annotations.PrimaryKey;

/**
 * Utility class for holding metadata for RealmProxy classes.
 */
public class ClassMetaData {

    private final TypeElement classType; // Reference to model class.
    private String className; // Model class simple name.
    private String packageName; // package name for model class.
    private boolean hasDefaultConstructor; // True if model has a public no-arg constructor.
    private VariableElement primaryKey; // Reference to field used as primary key, if any.
    private List<VariableElement> fields = new ArrayList<VariableElement>(); // List of all fields in the class except those @Ignored.
    private List<String> fieldNames = new ArrayList<String>();
    private List<String> ignoreFieldNames = new ArrayList<String>();
    private List<VariableElement> indexedFields = new ArrayList<VariableElement>(); // list of all fields marked @Index.
    private Set<String> expectedGetters = new HashSet<String>(); // Set of fieldnames that are expected to have a getter
    private Set<String> expectedSetters = new HashSet<String>(); // Set of fieldnames that are expected to have a setter
    private Set<ExecutableElement> methods = new HashSet<ExecutableElement>(); // List of all methods in the model class
    private Map<String, String> getters = new HashMap<String, String>(); // Map between fieldnames and their getters
    private Map<String, String> setters = new HashMap<String, String>(); // Map between fieldname and their setters

    private final List<TypeMirror> validPrimaryKeyTypes;
    private final Types typeUtils;
    private DeclaredType realmList;

    public ClassMetaData(ProcessingEnvironment env, TypeElement clazz) {
        this.classType = clazz;
        this.className = clazz.getSimpleName().toString();
        typeUtils = env.getTypeUtils();
        TypeMirror stringType = env.getElementUtils().getTypeElement("java.lang.String").asType();
        realmList = typeUtils.getDeclaredType(env.getElementUtils().getTypeElement("io.realm.RealmList"), typeUtils.getWildcardType(null, null));
        validPrimaryKeyTypes = Arrays.asList(
                stringType,
                typeUtils.getPrimitiveType(TypeKind.SHORT),
                typeUtils.getPrimitiveType(TypeKind.INT),
                typeUtils.getPrimitiveType(TypeKind.LONG)
        );
    }

    /**
     * Build the meta data structures for this class. Any errors or messages will be
     * posted on the provided Messager.
     *
     * @return True if meta data was correctly created and processing can continue, false otherwise.
     */
    public boolean generate() {

        // Get the package of the class
        Element enclosingElement = classType.getEnclosingElement();
        if (!enclosingElement.getKind().equals(ElementKind.PACKAGE)) {
            Utils.error("The RealmClass annotation does not support nested classes", classType);
            return false;
        }

        TypeElement parentElement = (TypeElement) Utils.getSuperClass(classType);
        if (!parentElement.toString().endsWith(".RealmObject")) {
            Utils.error("A RealmClass annotated object must be derived from RealmObject", classType);
            return false;
        }

        PackageElement packageElement = (PackageElement) enclosingElement;
        packageName = packageElement.getQualifiedName().toString();

        if (!categorizeClassElements()) return false;
        if (!checkListTypes()) return  false;
        if (!checkMethods()) return false;
        if (!checkDefaultConstructor()) return false;
        if (!checkRequiredGetters()) return false;
        if (!checkRequireSetters()) return false;

        return true; // Meta data was successfully generated
    }

    // Check that only allowed methods are present in the model class
    private boolean checkMethods() {
        for (ExecutableElement executableElement : methods) {
            String methodName = executableElement.getSimpleName().toString();

            // Check the modifiers of the method
            Set<Modifier> modifiers = executableElement.getModifiers();
            if (modifiers.contains(Modifier.STATIC)) {
                continue; // We're cool with static methods. Move along!
            } else if (!modifiers.contains(Modifier.PUBLIC)) {
                Utils.error("The methods of the model must be public", executableElement);
                return false;
            }

            // Check that getters and setters are valid
            if (methodName.startsWith("get") || methodName.startsWith("is")) {
                if (!checkGetterMethod(methodName)) {
                    Utils.error(String.format("Getter %s is not associated to any field", methodName), executableElement);
                    return false;
                }
            } else if (methodName.startsWith("set")) {
                if (!checkSetterMethod(methodName)) {
                    Utils.error(String.format("Setter %s is not associated to any field", methodName), executableElement);
                    return false;
                }
            } else {
                Utils.error("Only getters and setters should be defined in model classes", executableElement);
                return false;
            }
        }

        return true;
    }

    private boolean checkListTypes() {
        for (VariableElement field : fields) {
            if (typeUtils.isAssignable(field.asType(), realmList)) {
                if (Utils.getGenericType(field) == null) {
                    Utils.error("No generic type supplied for field", field);
                    return false;
                }
            }
        }
        return true;
    }

    // Verify that a setter is used to set a field in the model class.
    // Note: This is done heuristically by comparing the name of setter with the name of the field.
    // Annotation processors does not allow us to inspect individual statements.
    private boolean checkSetterMethod(String methodName) {
        boolean found = false;

        String methodMinusSet = methodName.substring(3);
        String methodMinusSetCapitalised = Utils.lowerFirstChar(methodMinusSet);
        String methodMenusSetPlusIs = "is" + methodMinusSet;

        if (fieldNames.contains(methodMinusSet)) { // mPerson -> setmPerson
            expectedSetters.remove(methodMinusSet);
            if (!ignoreFieldNames.contains(methodMinusSet)) {
                setters.put(methodMinusSet, methodName);
            }
            found = true;
        } else if (fieldNames.contains(methodMinusSetCapitalised)) { // person -> setPerson
            expectedSetters.remove(methodMinusSetCapitalised);
            if (!ignoreFieldNames.contains(methodMinusSetCapitalised)) {
                setters.put(methodMinusSetCapitalised, methodName);
            }
            found = true;
        } else if (fieldNames.contains(methodMenusSetPlusIs)) { // isReady -> setReady
            expectedSetters.remove(methodMenusSetPlusIs);
            if (!ignoreFieldNames.contains(methodMenusSetPlusIs)) {
                setters.put(methodMenusSetPlusIs, methodName);
            }
            found = true;
        }

        return found;
    }

    // Verify that a getter is used to get a field in the model class.
    // Note: This is done heuristically by comparing the name of getter with the name of the field.
    // Annotation processors does not allow us to inspect individual statements.
    private boolean checkGetterMethod(String methodName) {
        boolean found = false;

        if (methodName.startsWith("is")) {
            String methodMinusIs = methodName.substring(2);
            String methodMinusIsCapitalised = Utils.lowerFirstChar(methodMinusIs);
            if (fieldNames.contains(methodName)) { // isDone -> isDone
                expectedGetters.remove(methodName);
                if (!ignoreFieldNames.contains(methodName)) {
                    getters.put(methodName, methodName);
                }
                found = true;
            } else if (fieldNames.contains(methodMinusIs)) {  // mDone -> ismDone
                expectedGetters.remove(methodMinusIs);
                if (!ignoreFieldNames.contains(methodMinusIs)) {
                    getters.put(methodMinusIs, methodName);
                }
                found = true;
            } else if (fieldNames.contains(methodMinusIsCapitalised)) { // done -> isDone
                expectedGetters.remove(methodMinusIsCapitalised);
                if (!ignoreFieldNames.contains(methodMinusIsCapitalised)) {
                    getters.put(methodMinusIsCapitalised, methodName);
                }
                found = true;
            }
        }

        if (!found && methodName.startsWith("get")) {
            String methodMinusGet = methodName.substring(3);
            String methodMinusGetCapitalised = Utils.lowerFirstChar(methodMinusGet);
            if (fieldNames.contains(methodMinusGet)) { // mPerson -> getmPerson
                expectedGetters.remove(methodMinusGet);
                if (!ignoreFieldNames.contains(methodMinusGet)) {
                    getters.put(methodMinusGet, methodName);
                }
                found = true;
            } else if (fieldNames.contains(methodMinusGetCapitalised)) { // person -> getPerson
                expectedGetters.remove(methodMinusGetCapitalised);
                if (!ignoreFieldNames.contains(methodMinusGetCapitalised)) {
                    getters.put(methodMinusGetCapitalised, methodName);
                }
                found = true;
            }
        }

        return found;
    }

    // Report any setters that are missing
    private boolean checkRequireSetters() {
        for (String expectedSetter : expectedSetters) {
            Utils.error("No setter found for field " + expectedSetter);
        }
        return expectedSetters.size() == 0;
    }

    // Report any getters that are missing
    private boolean checkRequiredGetters() {
        for (String expectedGetter : expectedGetters) {
            Utils.error("No getter found for field " + expectedGetter);
        }
        return expectedGetters.size() == 0;
    }

    // Report if the default constructor is missing
    private boolean checkDefaultConstructor() {
        if (!hasDefaultConstructor) {
            Utils.error("A default public constructor with no argument must be declared if a custom constructor is declared.");
            return false;
        } else {
            return true;
        }
    }

    // Iterate through all class elements and add them to the appropriate internal data structures.
    // Returns true if all elements could be false if elements could not be categorized,
    private boolean categorizeClassElements() {
        for (Element element : classType.getEnclosedElements()) {
            ElementKind elementKind = element.getKind();

            if (elementKind.equals(ElementKind.FIELD)) {
                VariableElement variableElement = (VariableElement) element;
                String fieldName = variableElement.getSimpleName().toString();

                Set<Modifier> modifiers = variableElement.getModifiers();
                if (modifiers.contains(Modifier.STATIC)) {
                    continue; // completely ignore any static fields
                }

                if (variableElement.getAnnotation(Ignore.class) != null) {
                    // The field has the @Ignore annotation. No need to go any further.
                    String ignoredFieldName = variableElement.getSimpleName().toString();
                    fieldNames.add(ignoredFieldName);
                    ignoreFieldNames.add(ignoredFieldName);
                    continue;
                }

                if (variableElement.getAnnotation(Index.class) != null) {
                    // The field has the @Index annotation. It's only valid for:
                    // * String
                    String elementTypeCanonicalName = variableElement.asType().toString();
                    if (elementTypeCanonicalName.equals("java.lang.String")) {
                        indexedFields.add(variableElement);
                    } else {
                        Utils.error("@Index is only applicable to String fields - got " + element);
                        return false;
                    }
                }

                if (variableElement.getAnnotation(PrimaryKey.class) != null) {
                    // The field has the @PrimaryKey annotation. It is only valid for
                    // String, short, int, long and must only be present one time
                    if (primaryKey != null) {
                        Utils.error(String.format("@PrimaryKey cannot be defined more than once. It was found here \"%s\" and here \"%s\"",
                                primaryKey.getSimpleName().toString(),
                                variableElement.getSimpleName().toString()));
                        return false;
                    }

                    TypeMirror fieldType = variableElement.asType();
                    if (!isValidPrimaryKeyType(fieldType)) {
                        Utils.error("\"" + variableElement.getSimpleName().toString() + "\" is not allowed as primary key. See @PrimaryKey for allowed types.");
                        return false;
                    }

                    primaryKey = variableElement;

                    // Also add as index if the primary key is a string
                    if (Utils.isString(variableElement) && !indexedFields.contains(variableElement)) {
                        indexedFields.add(variableElement);
                    }
                }

                if (!variableElement.getModifiers().contains(Modifier.PRIVATE)) {
                    Utils.error("The fields of the model must be private", variableElement);
                    return false;
                }

                fields.add(variableElement);
                expectedGetters.add(fieldName);
                expectedSetters.add(fieldName);
            } else if (elementKind.equals(ElementKind.CONSTRUCTOR)) {
                hasDefaultConstructor =  hasDefaultConstructor || Utils.isDefaultConstructor(element);

            } else if (elementKind.equals(ElementKind.METHOD)) {
                ExecutableElement executableElement = (ExecutableElement) element;
                methods.add(executableElement);
            }
        }

        for (VariableElement field : fields) {
            fieldNames.add(field.getSimpleName().toString());
        }

        if (fields.size() == 0) {
            Utils.error(className + " must contain at least 1 persistable field");
        }

        return true;
    }

    public String getSimpleClassName() {
        return className;
    }

    /**
     * Returns true if the model class is considered to be a true model class.
     * RealmObject and Proxy classes also has the the @RealmClass annotation but is not considered true
     * model classes.
     */
    public boolean isModelClass() {
        String type = classType.toString();
        if (type.equals("io.realm.dynamic.DynamicRealmObject")) {
            return false;
        }
        return (!type.endsWith(".RealmObject") && !type.endsWith("RealmProxy"));
    }

    public String getFullyQualifiedClassName() {
        return packageName + "." + className;
    }

    public List<VariableElement> getFields() {
        return fields;
    }

    public String getGetter(String fieldName) {
        return getters.get(fieldName);
    }

    public String getSetter(String fieldName) {
        return setters.get(fieldName);
    }

    public List<VariableElement> getIndexedFields() {
        return indexedFields;
    }

    public boolean hasPrimaryKey() {
        return primaryKey != null;
    }

    public VariableElement getPrimaryKey() {
        return primaryKey;
    }

    public String getPrimaryKeyGetter() {
        return getters.get(primaryKey.getSimpleName().toString());
    }

    private boolean isValidPrimaryKeyType(TypeMirror type) {
        for (TypeMirror validType : validPrimaryKeyTypes) {
            if (typeUtils.isAssignable(type, validType)) {
                return true;
            }
        }
        return false;
    }
}



File: realm-annotations-processor/src/main/java/io/realm/processor/Constants.java
/*
 * Copyright 2014 Realm Inc.
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

package io.realm.processor;

public class Constants {
    public static final String REALM_PACKAGE_NAME = "io.realm";
    public static final String PROXY_SUFFIX = "RealmProxy";
    public static final String TABLE_PREFIX = "class_";
    public static final String DEFAULT_MODULE_CLASS_NAME = "DefaultRealmModule";
}


File: realm-annotations-processor/src/main/java/io/realm/processor/RealmProxyClassGenerator.java
/*
 * Copyright 2014 Realm Inc.
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

package io.realm.processor;

import com.squareup.javawriter.JavaWriter;

import javax.annotation.processing.ProcessingEnvironment;
import javax.lang.model.element.Modifier;
import javax.lang.model.element.VariableElement;
import javax.lang.model.type.DeclaredType;
import javax.lang.model.type.TypeMirror;
import javax.lang.model.util.Elements;
import javax.lang.model.util.Types;
import javax.tools.JavaFileObject;
import java.io.BufferedWriter;
import java.io.IOException;
import java.util.*;

public class RealmProxyClassGenerator {
    private ProcessingEnvironment processingEnvironment;
    private ClassMetaData metadata;
    private final String className;

    // Class metadata for generating proxy classes
    private Elements elementUtils;
    private Types typeUtils;
    private TypeMirror realmObject;
    private DeclaredType realmList;

    public RealmProxyClassGenerator(ProcessingEnvironment processingEnvironment, ClassMetaData metadata) {
        this.processingEnvironment = processingEnvironment;
        this.metadata = metadata;
        this.className = metadata.getSimpleClassName();
    }

    private static final Map<String, String> JAVA_TO_REALM_TYPES;
    static {
        JAVA_TO_REALM_TYPES = new HashMap<String, String>();
        JAVA_TO_REALM_TYPES.put("byte", "Long");
        JAVA_TO_REALM_TYPES.put("short", "Long");
        JAVA_TO_REALM_TYPES.put("int", "Long");
        JAVA_TO_REALM_TYPES.put("long", "Long");
        JAVA_TO_REALM_TYPES.put("float", "Float");
        JAVA_TO_REALM_TYPES.put("double", "Double");
        JAVA_TO_REALM_TYPES.put("boolean", "Boolean");
        JAVA_TO_REALM_TYPES.put("Byte", "Long");
        JAVA_TO_REALM_TYPES.put("Short", "Long");
        JAVA_TO_REALM_TYPES.put("Integer", "Long");
        JAVA_TO_REALM_TYPES.put("Long", "Long");
        JAVA_TO_REALM_TYPES.put("Float", "Float");
        JAVA_TO_REALM_TYPES.put("Double", "Double");
        JAVA_TO_REALM_TYPES.put("Boolean", "Boolean");
        JAVA_TO_REALM_TYPES.put("java.lang.String", "String");
        JAVA_TO_REALM_TYPES.put("java.util.Date", "Date");
        JAVA_TO_REALM_TYPES.put("byte[]", "BinaryByteArray");
        // TODO: add support for char and Char
    }

    // Types in this array are guarded by if != null and use default value if trying to insert null
    private static final Map<String, String> NULLABLE_JAVA_TYPES;
    static {
        NULLABLE_JAVA_TYPES = new HashMap<String, String>();
        NULLABLE_JAVA_TYPES.put("java.util.Date", "new Date(0)");
        NULLABLE_JAVA_TYPES.put("java.lang.String", "\"\"");
        NULLABLE_JAVA_TYPES.put("byte[]", "new byte[0]");
    }

    private static final Map<String, String> JAVA_TO_COLUMN_TYPES;
    static {
        JAVA_TO_COLUMN_TYPES = new HashMap<String, String>();
        JAVA_TO_COLUMN_TYPES.put("byte", "ColumnType.INTEGER");
        JAVA_TO_COLUMN_TYPES.put("short", "ColumnType.INTEGER");
        JAVA_TO_COLUMN_TYPES.put("int", "ColumnType.INTEGER");
        JAVA_TO_COLUMN_TYPES.put("long", "ColumnType.INTEGER");
        JAVA_TO_COLUMN_TYPES.put("float", "ColumnType.FLOAT");
        JAVA_TO_COLUMN_TYPES.put("double", "ColumnType.DOUBLE");
        JAVA_TO_COLUMN_TYPES.put("boolean", "ColumnType.BOOLEAN");
        JAVA_TO_COLUMN_TYPES.put("Byte", "ColumnType.INTEGER");
        JAVA_TO_COLUMN_TYPES.put("Short", "ColumnType.INTEGER");
        JAVA_TO_COLUMN_TYPES.put("Integer", "ColumnType.INTEGER");
        JAVA_TO_COLUMN_TYPES.put("Long", "ColumnType.INTEGER");
        JAVA_TO_COLUMN_TYPES.put("Float", "ColumnType.FLOAT");
        JAVA_TO_COLUMN_TYPES.put("Double", "ColumnType.DOUBLE");
        JAVA_TO_COLUMN_TYPES.put("Boolean", "ColumnType.BOOLEAN");
        JAVA_TO_COLUMN_TYPES.put("java.lang.String", "ColumnType.STRING");
        JAVA_TO_COLUMN_TYPES.put("java.util.Date", "ColumnType.DATE");
        JAVA_TO_COLUMN_TYPES.put("byte[]", "ColumnType.BINARY");
    }

    private static final Map<String, String> CASTING_TYPES;
    static {
        CASTING_TYPES = new HashMap<String, String>();
        CASTING_TYPES.put("byte", "long");
        CASTING_TYPES.put("short", "long");
        CASTING_TYPES.put("int", "long");
        CASTING_TYPES.put("long", "long");
        CASTING_TYPES.put("float", "float");
        CASTING_TYPES.put("double", "double");
        CASTING_TYPES.put("boolean", "boolean");
        CASTING_TYPES.put("Byte", "long");
        CASTING_TYPES.put("Short", "long");
        CASTING_TYPES.put("Integer", "long");
        CASTING_TYPES.put("Long", "long");
        CASTING_TYPES.put("Float", "float");
        CASTING_TYPES.put("Double", "double");
        CASTING_TYPES.put("Boolean", "boolean");
        CASTING_TYPES.put("java.lang.String", "String");
        CASTING_TYPES.put("java.util.Date", "Date");
        CASTING_TYPES.put("byte[]", "byte[]");
    }

    public void generate() throws IOException, UnsupportedOperationException {
        elementUtils = processingEnvironment.getElementUtils();
        typeUtils = processingEnvironment.getTypeUtils();
        realmObject = elementUtils.getTypeElement("io.realm.RealmObject").asType();
        realmList = typeUtils.getDeclaredType(elementUtils.getTypeElement("io.realm.RealmList"), typeUtils.getWildcardType(null, null));

        String qualifiedGeneratedClassName = String.format("%s.%s", Constants.REALM_PACKAGE_NAME, Utils.getProxyClassName(className));
        JavaFileObject sourceFile = processingEnvironment.getFiler().createSourceFile(qualifiedGeneratedClassName);
        JavaWriter writer = new JavaWriter(new BufferedWriter(sourceFile.openWriter()));

        // Set source code indent to 4 spaces
        writer.setIndent("    ");

        writer.emitPackage(Constants.REALM_PACKAGE_NAME)
                .emitEmptyLine();

        ArrayList<String> imports = new ArrayList<String>();
        imports.add("android.util.JsonReader");
        imports.add("android.util.JsonToken");
        imports.add("io.realm.RealmObject");
        imports.add("io.realm.exceptions.RealmException");
        imports.add("io.realm.exceptions.RealmMigrationNeededException");
        imports.add("io.realm.internal.ColumnType");
        imports.add("io.realm.internal.RealmObjectProxy");
        imports.add("io.realm.internal.Table");
        imports.add("io.realm.internal.TableOrView");
        imports.add("io.realm.internal.ImplicitTransaction");
        imports.add("io.realm.internal.LinkView");
        imports.add("io.realm.internal.android.JsonUtils");
        imports.add("java.io.IOException");
        imports.add("java.util.ArrayList");
        imports.add("java.util.Collections");
        imports.add("java.util.List");
        imports.add("java.util.Arrays");
        imports.add("java.util.Date");
        imports.add("java.util.Map");
        imports.add("java.util.HashMap");
        imports.add("org.json.JSONObject");
        imports.add("org.json.JSONException");
        imports.add("org.json.JSONArray");
        imports.add(metadata.getFullyQualifiedClassName());

        for (VariableElement field : metadata.getFields()) {
            String fieldTypeName = "";
            if (typeUtils.isAssignable(field.asType(), realmObject)) { // Links
                fieldTypeName = field.asType().toString();
            } else if (typeUtils.isAssignable(field.asType(), realmList)) { // LinkLists
                fieldTypeName = ((DeclaredType) field.asType()).getTypeArguments().get(0).toString();
            }
            if (!fieldTypeName.isEmpty() && !imports.contains(fieldTypeName)) {
                imports.add(fieldTypeName);
            }
        }
        Collections.sort(imports);
        writer.emitImports(imports);
        writer.emitEmptyLine();

        // Begin the class definition
        writer.beginType(
                qualifiedGeneratedClassName, // full qualified name of the item to generate
                "class",                     // the type of the item
                EnumSet.of(Modifier.PUBLIC), // modifiers to apply
                className,                   // class to extend
                "RealmObjectProxy")          // interfaces to implement
                .emitEmptyLine();

        emitClassFields(writer);
        emitAccessors(writer);
        emitInitTableMethod(writer);
        emitValidateTableMethod(writer);
        emitGetTableNameMethod(writer);
        emitGetFieldNamesMethod(writer);
        emitGetColumnIndicesMethod(writer);
        emitCreateOrUpdateUsingJsonObject(writer);
        emitCreateUsingJsonStream(writer);
        emitCopyOrUpdateMethod(writer);
        emitCopyMethod(writer);
        emitUpdateMethod(writer);
        emitToStringMethod(writer);
        emitHashcodeMethod(writer);
        emitEqualsMethod(writer);

        // End the class definition
        writer.endType();
        writer.close();
    }

    private void emitClassFields(JavaWriter writer) throws IOException {
        for (VariableElement variableElement : metadata.getFields()) {
            writer.emitField("long", staticFieldIndexVarName(variableElement), EnumSet.of(Modifier.PRIVATE, Modifier.STATIC));
        }
        writer.emitField("Map<String, Long>", "columnIndices", EnumSet.of(Modifier.PRIVATE, Modifier.STATIC));
        writer.emitField("List<String>", "FIELD_NAMES", EnumSet.of(Modifier.PRIVATE, Modifier.STATIC, Modifier.FINAL));
        writer.beginInitializer(true);
        writer.emitStatement("List<String> fieldNames = new ArrayList<String>()");
        for (VariableElement field : metadata.getFields()) {
            writer.emitStatement("fieldNames.add(\"%s\")", field.getSimpleName().toString());
        }
        writer.emitStatement("FIELD_NAMES = Collections.unmodifiableList(fieldNames)");
        writer.endInitializer();
        writer.emitEmptyLine();
    }

    private void emitAccessors(JavaWriter writer) throws IOException {
        for (VariableElement field : metadata.getFields()) {
            String fieldName = field.getSimpleName().toString();
            String fieldTypeCanonicalName = field.asType().toString();

            if (JAVA_TO_REALM_TYPES.containsKey(fieldTypeCanonicalName)) {
                /**
                 * Primitives and boxed types
                 */
                String realmType = JAVA_TO_REALM_TYPES.get(fieldTypeCanonicalName);
                String castingType = CASTING_TYPES.get(fieldTypeCanonicalName);

                // Getter
                writer.emitAnnotation("Override");
                writer.beginMethod(fieldTypeCanonicalName, metadata.getGetter(fieldName), EnumSet.of(Modifier.PUBLIC));
                writer.emitStatement(
                        "realm.checkIfValid()"
                );
                writer.emitStatement(
                        "return (%s) row.get%s(%s)",
                        fieldTypeCanonicalName, realmType, staticFieldIndexVarName(field));
                writer.endMethod();
                writer.emitEmptyLine();

                // Setter
                writer.emitAnnotation("Override");
                writer.beginMethod("void", metadata.getSetter(fieldName), EnumSet.of(Modifier.PUBLIC), fieldTypeCanonicalName, "value");
                writer.emitStatement(
                        "realm.checkIfValid()"
                );
                writer.emitStatement(
                        "row.set%s(%s, (%s) value)",
                        realmType, staticFieldIndexVarName(field), castingType);
                writer.endMethod();
            } else if (typeUtils.isAssignable(field.asType(), realmObject)) {
                /**
                 * Links
                 */

                // Getter
                writer.emitAnnotation("Override");
                writer.beginMethod(fieldTypeCanonicalName, metadata.getGetter(fieldName), EnumSet.of(Modifier.PUBLIC));
                writer.beginControlFlow("if (row.isNullLink(%s))", staticFieldIndexVarName(field));
                writer.emitStatement("return null");
                writer.endControlFlow();
                writer.emitStatement(
                        "return realm.get(%s.class, row.getLink(%s))",
                        fieldTypeCanonicalName, staticFieldIndexVarName(field));
                writer.endMethod();
                writer.emitEmptyLine();

                // Setter
                writer.emitAnnotation("Override");
                writer.beginMethod("void", metadata.getSetter(fieldName), EnumSet.of(Modifier.PUBLIC), fieldTypeCanonicalName, "value");
                writer.beginControlFlow("if (value == null)");
                writer.emitStatement("row.nullifyLink(%s)", staticFieldIndexVarName(field));
                writer.emitStatement("return");
                writer.endControlFlow();
                writer.emitStatement("row.setLink(%s, value.row.getIndex())", staticFieldIndexVarName(field));
                writer.endMethod();
            } else if (typeUtils.isAssignable(field.asType(), realmList)) {
                /**
                 * LinkLists
                 */
                String genericType = Utils.getGenericType(field);

                // Getter
                writer.emitAnnotation("Override");
                writer.beginMethod(fieldTypeCanonicalName, metadata.getGetter(fieldName), EnumSet.of(Modifier.PUBLIC));
                writer.emitStatement(
                        "return new RealmList<%s>(%s.class, row.getLinkList(%s), realm)",
                        genericType, genericType, staticFieldIndexVarName(field));
                writer.endMethod();
                writer.emitEmptyLine();

                // Setter
                writer.emitAnnotation("Override");
                writer.beginMethod("void", metadata.getSetter(fieldName), EnumSet.of(Modifier.PUBLIC), fieldTypeCanonicalName, "value");
                writer.emitStatement("LinkView links = row.getLinkList(%s)", staticFieldIndexVarName(field));
                writer.beginControlFlow("if (value == null)");
                writer.emitStatement("return"); // TODO: delete all the links instead
                writer.endControlFlow();
                writer.emitStatement("links.clear()");
                writer.beginControlFlow("for (RealmObject linkedObject : (RealmList<? extends RealmObject>) value)");
                writer.emitStatement("links.add(linkedObject.row.getIndex())");
                writer.endControlFlow();
                writer.endMethod();
            } else {
                throw new UnsupportedOperationException(
                        String.format("Type %s of field %s is not supported", fieldTypeCanonicalName, fieldName));
            }
            writer.emitEmptyLine();
        }
    }

    private void emitInitTableMethod(JavaWriter writer) throws IOException {
        writer.beginMethod(
                "Table", // Return type
                "initTable", // Method name
                EnumSet.of(Modifier.PUBLIC, Modifier.STATIC), // Modifiers
                "ImplicitTransaction", "transaction"); // Argument type & argument name

        writer.beginControlFlow("if (!transaction.hasTable(\"" + Constants.TABLE_PREFIX + this.className + "\"))");
        writer.emitStatement("Table table = transaction.getTable(\"%s%s\")", Constants.TABLE_PREFIX, this.className);

        // For each field generate corresponding table index constant
        for (VariableElement field : metadata.getFields()) {
            String fieldName = field.getSimpleName().toString();
            String fieldTypeCanonicalName = field.asType().toString();
            String fieldTypeSimpleName = Utils.getFieldTypeSimpleName(field);

            if (JAVA_TO_REALM_TYPES.containsKey(fieldTypeCanonicalName)) {
                writer.emitStatement("table.addColumn(%s, \"%s\")",
                        JAVA_TO_COLUMN_TYPES.get(fieldTypeCanonicalName),
                        fieldName);
            } else if (typeUtils.isAssignable(field.asType(), realmObject)) {
                writer.beginControlFlow("if (!transaction.hasTable(\"%s%s\"))", Constants.TABLE_PREFIX, fieldTypeSimpleName);
                writer.emitStatement("%s%s.initTable(transaction)", fieldTypeSimpleName, Constants.PROXY_SUFFIX);
                writer.endControlFlow();
                writer.emitStatement("table.addColumnLink(ColumnType.LINK, \"%s\", transaction.getTable(\"%s%s\"))",
                        fieldName, Constants.TABLE_PREFIX, fieldTypeSimpleName);
            } else if (typeUtils.isAssignable(field.asType(), realmList)) {
                String genericType = Utils.getGenericType(field);
                writer.beginControlFlow("if (!transaction.hasTable(\"%s%s\"))", Constants.TABLE_PREFIX, genericType);
                writer.emitStatement("%s%s.initTable(transaction)", genericType, Constants.PROXY_SUFFIX);
                writer.endControlFlow();
                writer.emitStatement("table.addColumnLink(ColumnType.LINK_LIST, \"%s\", transaction.getTable(\"%s%s\"))",
                        fieldName, Constants.TABLE_PREFIX, genericType);
            }
        }

        for (VariableElement field : metadata.getIndexedFields()) {
            String fieldName = field.getSimpleName().toString();
            writer.emitStatement("table.addSearchIndex(table.getColumnIndex(\"%s\"))", fieldName);
        }

        if (metadata.hasPrimaryKey()) {
            String fieldName = metadata.getPrimaryKey().getSimpleName().toString();
            writer.emitStatement("table.setPrimaryKey(\"%s\")", fieldName);
        } else {
            writer.emitStatement("table.setPrimaryKey(\"\")");
        }

        writer.emitStatement("return table");
        writer.endControlFlow();
        writer.emitStatement("return transaction.getTable(\"%s%s\")", Constants.TABLE_PREFIX, this.className);
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitValidateTableMethod(JavaWriter writer) throws IOException {
        writer.beginMethod(
                "void", // Return type
                "validateTable", // Method name
                EnumSet.of(Modifier.PUBLIC, Modifier.STATIC), // Modifiers
                "ImplicitTransaction", "transaction"); // Argument type & argument name

        writer.beginControlFlow("if (transaction.hasTable(\"" + Constants.TABLE_PREFIX + this.className + "\"))");
        writer.emitStatement("Table table = transaction.getTable(\"%s%s\")", Constants.TABLE_PREFIX, this.className);

        // verify number of columns
        writer.beginControlFlow("if (table.getColumnCount() != " + metadata.getFields().size() + ")");
        writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Field count does not match - expected %d but was \" + table.getColumnCount())",
                metadata.getFields().size());
        writer.endControlFlow();

        // create type dictionary for lookup
        writer.emitStatement("Map<String, ColumnType> columnTypes = new HashMap<String, ColumnType>()");
        writer.beginControlFlow("for (long i = 0; i < " + metadata.getFields().size() + "; i++)");
        writer.emitStatement("columnTypes.put(table.getColumnName(i), table.getColumnType(i))");
        writer.endControlFlow();

        // Populate column indices
        writer.emitEmptyLine();
        writer.emitStatement("columnIndices = new HashMap<String, Long>()");
        writer
                .beginControlFlow("for (String fieldName : getFieldNames())")
                    .emitStatement("long index = table.getColumnIndex(fieldName)")
                    .beginControlFlow("if (index == -1)")
                        .emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Field '\" + fieldName + \"' not found for type %s\")", metadata.getSimpleClassName())
                    .endControlFlow()
                    .emitStatement("columnIndices.put(fieldName, index)")
                .endControlFlow();
        for (VariableElement field : metadata.getFields()) {
            writer.emitStatement("%s = table.getColumnIndex(\"%s\")", staticFieldIndexVarName(field), field.getSimpleName().toString());
        }
        writer.emitEmptyLine();

        // For each field verify there is a corresponding
        long fieldIndex = 0;
        for (VariableElement field : metadata.getFields()) {
            String fieldName = field.getSimpleName().toString();
            String fieldTypeCanonicalName = field.asType().toString();
            String fieldTypeSimpleName = Utils.getFieldTypeSimpleName(field);

            if (JAVA_TO_REALM_TYPES.containsKey(fieldTypeCanonicalName)) {
                // make sure types align
                writer.beginControlFlow("if (!columnTypes.containsKey(\"%s\"))", fieldName);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Missing field '%s'\")", fieldName);
                writer.endControlFlow();
                writer.beginControlFlow("if (columnTypes.get(\"%s\") != %s)", fieldName, JAVA_TO_COLUMN_TYPES.get(fieldTypeCanonicalName));
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Invalid type '%s' for field '%s'\")",
                        fieldTypeSimpleName, fieldName);
                writer.endControlFlow();

                // Validate @PrimaryKey
                if (field.equals(metadata.getPrimaryKey())) {
                    writer.beginControlFlow("if (table.getPrimaryKey() != table.getColumnIndex(\"%s\"))", fieldName);
                    writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Primary key not defined for field '%s'\")", fieldName);
                    writer.endControlFlow();
                }

                // Validate @Index
                if (metadata.getIndexedFields().contains(field)) {
                    writer.beginControlFlow("if (!table.hasSearchIndex(table.getColumnIndex(\"%s\")))", fieldName);
                    writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Index not defined for field '%s'\")", fieldName);
                    writer.endControlFlow();
                }

            } else if (typeUtils.isAssignable(field.asType(), realmObject)) { // Links
                writer.beginControlFlow("if (!columnTypes.containsKey(\"%s\"))", fieldName);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Missing field '%s'\")", fieldName);
                writer.endControlFlow();
                writer.beginControlFlow("if (columnTypes.get(\"%s\") != ColumnType.LINK)", fieldName);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Invalid type '%s' for field '%s'\")",
                        fieldTypeSimpleName, fieldName);
                writer.endControlFlow();
                writer.beginControlFlow("if (!transaction.hasTable(\"%s%s\"))", Constants.TABLE_PREFIX, fieldTypeSimpleName);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Missing class '%s%s' for field '%s'\")",
                        Constants.TABLE_PREFIX, fieldTypeSimpleName, fieldName);
                writer.endControlFlow();

                writer.emitStatement("Table table_%d = transaction.getTable(\"%s%s\")", fieldIndex, Constants.TABLE_PREFIX, fieldTypeSimpleName);
                writer.beginControlFlow("if (!table.getLinkTarget(%s).hasSameSchema(table_%d))",
                        staticFieldIndexVarName(field), fieldIndex);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Invalid RealmObject for field '%s': '\" + table.getLinkTarget(%s).getName() + \"' expected - was '\" + table_%d.getName() + \"'\")",
                        fieldName, staticFieldIndexVarName(field), fieldIndex);
                writer.endControlFlow();
            } else if (typeUtils.isAssignable(field.asType(), realmList)) { // Link Lists
                String genericType = Utils.getGenericType(field);
                writer.beginControlFlow("if (!columnTypes.containsKey(\"%s\"))", fieldName);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Missing field '%s'\")", fieldName);
                writer.endControlFlow();
                writer.beginControlFlow("if (columnTypes.get(\"%s\") != ColumnType.LINK_LIST)", fieldName);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Invalid type '%s' for field '%s'\")",
                        genericType, fieldName);
                writer.endControlFlow();
                writer.beginControlFlow("if (!transaction.hasTable(\"%s%s\"))", Constants.TABLE_PREFIX, genericType);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Missing class '%s%s' for field '%s'\")",
                        Constants.TABLE_PREFIX, genericType, fieldName);
                writer.endControlFlow();

                writer.emitStatement("Table table_%d = transaction.getTable(\"%s%s\")", fieldIndex, Constants.TABLE_PREFIX, genericType);
                writer.beginControlFlow("if (!table.getLinkTarget(%s).hasSameSchema(table_%d))",
                        staticFieldIndexVarName(field), fieldIndex);
                writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"Invalid RealmList type for field '%s': '\" + table.getLinkTarget(%s).getName() + \"' expected - was '\" + table_%d.getName() + \"'\")",
                        fieldName, staticFieldIndexVarName(field), fieldIndex);
                writer.endControlFlow();
            }
            fieldIndex++;
        }

        writer.nextControlFlow("else");
        writer.emitStatement("throw new RealmMigrationNeededException(transaction.getPath(), \"The %s class is missing from the schema for this Realm.\")", metadata.getSimpleClassName());
        writer.endControlFlow();
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitGetTableNameMethod(JavaWriter writer) throws IOException {
        writer.beginMethod("String", "getTableName", EnumSet.of(Modifier.PUBLIC, Modifier.STATIC));
        writer.emitStatement("return \"%s%s\"", Constants.TABLE_PREFIX, className);
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitGetFieldNamesMethod(JavaWriter writer) throws IOException {
        writer.beginMethod("List<String>", "getFieldNames", EnumSet.of(Modifier.PUBLIC, Modifier.STATIC));
        writer.emitStatement("return FIELD_NAMES");
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitGetColumnIndicesMethod(JavaWriter writer) throws IOException {
        writer.beginMethod("Map<String,Long>", "getColumnIndices", EnumSet.of(Modifier.PUBLIC, Modifier.STATIC));
        writer.emitStatement("return columnIndices");
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitCopyOrUpdateMethod(JavaWriter writer) throws IOException {
        writer.beginMethod(
                className, // Return type
                "copyOrUpdate", // Method name
                EnumSet.of(Modifier.PUBLIC, Modifier.STATIC), // Modifiers
                "Realm", "realm", className, "object", "boolean", "update", "Map<RealmObject,RealmObjectProxy>", "cache" // Argument type & argument name
        );

        // If object is already in the Realm there is nothing to update
        writer
            .beginControlFlow("if (object.realm != null && object.realm.getPath().equals(realm.getPath()))")
                .emitStatement("return object")
            .endControlFlow();

        if (!metadata.hasPrimaryKey()) {
            writer.emitStatement("return copy(realm, object, update, cache)");
        } else {
            writer
                .emitStatement("%s realmObject = null", className)
                .emitStatement("boolean canUpdate = update")
                .beginControlFlow("if (canUpdate)")
                    .emitStatement("Table table = realm.getTable(%s.class)", className)
                    .emitStatement("long pkColumnIndex = table.getPrimaryKey()");

            if (Utils.isString(metadata.getPrimaryKey())) {
                writer
                    .beginControlFlow("if (object.%s() == null)", metadata.getPrimaryKeyGetter())
                        .emitStatement("throw new IllegalArgumentException(\"Primary key value must not be null.\")")
                    .endControlFlow()
                    .emitStatement("long rowIndex = table.findFirstString(pkColumnIndex, object.%s())", metadata.getPrimaryKeyGetter());
            } else {
                writer.emitStatement("long rowIndex = table.findFirstLong(pkColumnIndex, object.%s())", metadata.getPrimaryKeyGetter());
            }

            writer
                .beginControlFlow("if (rowIndex != TableOrView.NO_MATCH)")
                    .emitStatement("realmObject = new %s()", Utils.getProxyClassName(className))
                    .emitStatement("realmObject.realm = realm")
                    .emitStatement("realmObject.row = table.getUncheckedRow(rowIndex)")
                    .emitStatement("cache.put(object, (RealmObjectProxy) realmObject)")
                .nextControlFlow("else")
                    .emitStatement("canUpdate = false")
                .endControlFlow();

            writer.endControlFlow();

            writer
                .emitEmptyLine()
                .beginControlFlow("if (canUpdate)")
                    .emitStatement("return update(realm, realmObject, object, cache)")
                .nextControlFlow("else")
                    .emitStatement("return copy(realm, object, update, cache)")
                .endControlFlow();
        }

        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitCopyMethod(JavaWriter writer) throws IOException {
        writer.beginMethod(
                className, // Return type
                "copy", // Method name
                EnumSet.of(Modifier.PUBLIC, Modifier.STATIC), // Modifiers
                "Realm", "realm", className, "newObject", "boolean", "update", "Map<RealmObject,RealmObjectProxy>", "cache"); // Argument type & argument name

        if (metadata.hasPrimaryKey()) {
            writer.emitStatement("%s realmObject = realm.createObject(%s.class, newObject.%s())", className, className, metadata.getPrimaryKeyGetter());
        } else {
            writer.emitStatement("%s realmObject = realm.createObject(%s.class)", className, className);
        }
        writer.emitStatement("cache.put(newObject, (RealmObjectProxy) realmObject)");
        for (VariableElement field : metadata.getFields()) {
            String fieldName = field.getSimpleName().toString();
            String fieldType = field.asType().toString();
            if (typeUtils.isAssignable(field.asType(), realmObject)) {
                writer
                    .emitEmptyLine()
                    .emitStatement("%s %sObj = newObject.%s()", fieldType, fieldName, metadata.getGetter(fieldName))
                    .beginControlFlow("if (%sObj != null)", fieldName)
                        .emitStatement("%s cache%s = (%s) cache.get(%sObj)", fieldType, fieldName, fieldType, fieldName)
                        .beginControlFlow("if (cache%s != null)", fieldName)
                            .emitStatement("realmObject.%s(cache%s)", metadata.getSetter(fieldName), fieldName)
                        .nextControlFlow("else")
                            .emitStatement("realmObject.%s(%s.copyOrUpdate(realm, %sObj, update, cache))",
                                    metadata.getSetter(fieldName),
                                    Utils.getProxyClassSimpleName(field),
                                    fieldName)
                        .endControlFlow()
                    .endControlFlow();
            } else if (typeUtils.isAssignable(field.asType(), realmList)) {
                writer
                    .emitEmptyLine()
                    .emitStatement("RealmList<%s> %sList = newObject.%s()", Utils.getGenericType(field), fieldName, metadata.getGetter(fieldName))
                    .beginControlFlow("if (%sList != null)", fieldName)
                        .emitStatement("RealmList<%s> %sRealmList = realmObject.%s()", Utils.getGenericType(field), fieldName, metadata.getGetter(fieldName))
                        .beginControlFlow("for (int i = 0; i < %sList.size(); i++)", fieldName)
                                .emitStatement("%s %sItem = %sList.get(i)", Utils.getGenericType(field), fieldName, fieldName)
                                .emitStatement("%s cache%s = (%s) cache.get(%sItem)", Utils.getGenericType(field), fieldName, Utils.getGenericType(field), fieldName)
                                .beginControlFlow("if (cache%s != null)", fieldName)
                                        .emitStatement("%sRealmList.add(cache%s)", fieldName, fieldName)
                                .nextControlFlow("else")
                                        .emitStatement("%sRealmList.add(%s.copyOrUpdate(realm, %sList.get(i), update, cache))", fieldName, Utils.getProxyClassSimpleName(field), fieldName)
                                .endControlFlow()
                        .endControlFlow()
                    .endControlFlow()
                    .emitEmptyLine();

            } else {
                if (NULLABLE_JAVA_TYPES.containsKey(fieldType)) {
                    writer.emitStatement("realmObject.%s(newObject.%s() != null ? newObject.%s() : %s)",
                            metadata.getSetter(fieldName),
                            metadata.getGetter(fieldName),
                            metadata.getGetter(fieldName),
                            NULLABLE_JAVA_TYPES.get(fieldType));
                } else {
                    writer.emitStatement("realmObject.%s(newObject.%s())", metadata.getSetter(fieldName), metadata.getGetter(fieldName));
                }
            }
        }

        writer.emitStatement("return realmObject");
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitUpdateMethod(JavaWriter writer) throws IOException {

        writer.beginMethod(
                className, // Return type
                "update", // Method name
                EnumSet.of(Modifier.STATIC), // Modifiers
                "Realm", "realm", className, "realmObject", className, "newObject", "Map<RealmObject, RealmObjectProxy>", "cache"); // Argument type & argument name

        for (VariableElement field : metadata.getFields()) {
            String fieldName = field.getSimpleName().toString();
            if (typeUtils.isAssignable(field.asType(), realmObject)) {
                writer
                    .emitStatement("%s %sObj = newObject.%s()", Utils.getFieldTypeSimpleName(field), fieldName, metadata.getGetter(fieldName))
                    .beginControlFlow("if (%sObj != null)", fieldName)
                        .emitStatement("%s cache%s = (%s) cache.get(%sObj)", Utils.getFieldTypeSimpleName(field), fieldName, Utils.getFieldTypeSimpleName(field), fieldName)
                        .beginControlFlow("if (cache%s != null)", fieldName)
                            .emitStatement("realmObject.%s(cache%s)", metadata.getSetter(fieldName), fieldName)
                        .nextControlFlow("else")
                            .emitStatement("realmObject.%s(%s.copyOrUpdate(realm, %sObj, true, cache))",
                                    metadata.getSetter(fieldName),
                                    Utils.getProxyClassSimpleName(field),
                                    fieldName,
                                    Utils.getFieldTypeSimpleName(field)
                            )
                        .endControlFlow()
                    .nextControlFlow("else")
                        .emitStatement("realmObject.%s(null)", metadata.getSetter(fieldName))
                    .endControlFlow();
            } else if (typeUtils.isAssignable(field.asType(), realmList)) {
                writer
                    .emitStatement("RealmList<%s> %sList = newObject.%s()", Utils.getGenericType(field), fieldName, metadata.getGetter(fieldName))
                    .emitStatement("RealmList<%s> %sRealmList = realmObject.%s()", Utils.getGenericType(field), fieldName, metadata.getGetter(fieldName))
                    .emitStatement("%sRealmList.clear()", fieldName)
                    .beginControlFlow("if (%sList != null)", fieldName)
                        .beginControlFlow("for (int i = 0; i < %sList.size(); i++)", fieldName)
                            .emitStatement("%s %sItem = %sList.get(i)", Utils.getGenericType(field), fieldName, fieldName)
                            .emitStatement("%s cache%s = (%s) cache.get(%sItem)", Utils.getGenericType(field), fieldName, Utils.getGenericType(field), fieldName)
                            .beginControlFlow("if (cache%s != null)", fieldName)
                                .emitStatement("%sRealmList.add(cache%s)", fieldName, fieldName)
                            .nextControlFlow("else")
                                .emitStatement("%sRealmList.add(%s.copyOrUpdate(realm, %sList.get(i), true, cache))", fieldName, Utils.getProxyClassSimpleName(field), fieldName)
                            .endControlFlow()
                        .endControlFlow()
                    .endControlFlow();

            } else {
                if (field == metadata.getPrimaryKey()) {
                    continue;
                }

                String fieldType = field.asType().toString();
                if (NULLABLE_JAVA_TYPES.containsKey(fieldType)) {
                    writer.emitStatement("realmObject.%s(newObject.%s() != null ? newObject.%s() : %s)",
                            metadata.getSetter(fieldName),
                            metadata.getGetter(fieldName),
                            metadata.getGetter(fieldName),
                            NULLABLE_JAVA_TYPES.get(fieldType));
                } else {
                    writer.emitStatement("realmObject.%s(newObject.%s())", metadata.getSetter(fieldName), metadata.getGetter(fieldName));
                }
            }
        }

        writer.emitStatement("return realmObject");
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitToStringMethod(JavaWriter writer) throws IOException {
        writer.emitAnnotation("Override");
        writer.beginMethod("String", "toString", EnumSet.of(Modifier.PUBLIC));
        writer.beginControlFlow("if (!isValid())");
        writer.emitStatement("return \"Invalid object\"");
        writer.endControlFlow();
        writer.emitStatement("StringBuilder stringBuilder = new StringBuilder(\"%s = [\")", className);
        List<VariableElement> fields = metadata.getFields();
        for (int i = 0; i < fields.size(); i++) {
            VariableElement field = fields.get(i);
            String fieldName = field.getSimpleName().toString();

            writer.emitStatement("stringBuilder.append(\"{%s:\")", fieldName);
            if (typeUtils.isAssignable(field.asType(), realmObject)) {
                String fieldTypeSimpleName = Utils.getFieldTypeSimpleName(field);
                writer.emitStatement(
                        "stringBuilder.append(%s() != null ? \"%s\" : \"null\")",
                        metadata.getGetter(fieldName),
                        fieldTypeSimpleName
                );
            } else if (typeUtils.isAssignable(field.asType(), realmList)) {
                String genericType = Utils.getGenericType(field);
                writer.emitStatement("stringBuilder.append(\"RealmList<%s>[\").append(%s().size()).append(\"]\")",
                        genericType,
                        metadata.getGetter(fieldName));
            } else {
                writer.emitStatement("stringBuilder.append(%s())", metadata.getGetter(fieldName));
            }
            writer.emitStatement("stringBuilder.append(\"}\")");

            if (i < fields.size() - 1) {
                writer.emitStatement("stringBuilder.append(\",\")");
            }
        }

        writer.emitStatement("stringBuilder.append(\"]\")");
        writer.emitStatement("return stringBuilder.toString()");
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitHashcodeMethod(JavaWriter writer) throws IOException {
        writer.emitAnnotation("Override");
        writer.beginMethod("int", "hashCode", EnumSet.of(Modifier.PUBLIC));
        writer.emitStatement("String realmName = realm.getPath()");
        writer.emitStatement("String tableName = row.getTable().getName()");
        writer.emitStatement("long rowIndex = row.getIndex()");
        writer.emitEmptyLine();
        writer.emitStatement("int result = 17");
        writer.emitStatement("result = 31 * result + ((realmName != null) ? realmName.hashCode() : 0)");
        writer.emitStatement("result = 31 * result + ((tableName != null) ? tableName.hashCode() : 0)");
        writer.emitStatement("result = 31 * result + (int) (rowIndex ^ (rowIndex >>> 32))");
        writer.emitStatement("return result");
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitEqualsMethod(JavaWriter writer) throws IOException {
        String proxyClassName = className + Constants.PROXY_SUFFIX;
        writer.emitAnnotation("Override");
        writer.beginMethod("boolean", "equals", EnumSet.of(Modifier.PUBLIC), "Object", "o");
        writer.emitStatement("if (this == o) return true");
        writer.emitStatement("if (o == null || getClass() != o.getClass()) return false");
        writer.emitStatement("%s a%s = (%s)o", proxyClassName, className, proxyClassName);  // FooRealmProxy aFoo = (FooRealmProxy)o
        writer.emitEmptyLine();
        writer.emitStatement("String path = realm.getPath()");
        writer.emitStatement("String otherPath = a%s.realm.getPath()", className);
        writer.emitStatement("if (path != null ? !path.equals(otherPath) : otherPath != null) return false;");
        writer.emitEmptyLine();
        writer.emitStatement("String tableName = row.getTable().getName()");
        writer.emitStatement("String otherTableName = a%s.row.getTable().getName()", className);
        writer.emitStatement("if (tableName != null ? !tableName.equals(otherTableName) : otherTableName != null) return false");
        writer.emitEmptyLine();
        writer.emitStatement("if (row.getIndex() != a%s.row.getIndex()) return false", className);
        writer.emitEmptyLine();
        writer.emitStatement("return true");
        writer.endMethod();
        writer.emitEmptyLine();
    }


    private void emitCreateOrUpdateUsingJsonObject(JavaWriter writer) throws IOException {
        writer.beginMethod(
                className,
                "createOrUpdateUsingJsonObject",
                EnumSet.of(Modifier.PUBLIC, Modifier.STATIC),
                Arrays.asList("Realm", "realm", "JSONObject", "json", "boolean", "update"),
                Arrays.asList("JSONException"));

        if (!metadata.hasPrimaryKey()) {
            writer.emitStatement("%s obj = realm.createObject(%s.class)", className, className);
        } else {
            String pkType = Utils.isString(metadata.getPrimaryKey()) ? "String" : "Long";
            writer
                .emitStatement("%s obj = null", className)
                .beginControlFlow("if (update)")
                    .emitStatement("Table table = realm.getTable(%s.class)", className)
                    .emitStatement("long pkColumnIndex = table.getPrimaryKey()")
                    .beginControlFlow("if (!json.isNull(\"%s\"))", metadata.getPrimaryKey().getSimpleName())
                        .emitStatement("long rowIndex = table.findFirst%s(pkColumnIndex, json.get%s(\"%s\"))",
                                pkType, pkType, metadata.getPrimaryKey().getSimpleName())
                        .beginControlFlow("if (rowIndex != TableOrView.NO_MATCH)")
                            .emitStatement("obj = new %s()", Utils.getProxyClassName(className))
                            .emitStatement("obj.realm = realm")
                            .emitStatement("obj.row = table.getUncheckedRow(rowIndex)")
                        .endControlFlow()
                    .endControlFlow()
                .endControlFlow()
                .beginControlFlow("if (obj == null)")
                    .emitStatement("obj = realm.createObject(%s.class)", className)
                .endControlFlow();
        }

        for (VariableElement field : metadata.getFields()) {
            String fieldName = field.getSimpleName().toString();
            String qualifiedFieldType = field.asType().toString();
            if (typeUtils.isAssignable(field.asType(), realmObject)) {
                RealmJsonTypeHelper.emitFillRealmObjectWithJsonValue(
                        metadata.getSetter(fieldName),
                        fieldName,
                        qualifiedFieldType,
                        Utils.getProxyClassSimpleName(field),
                        writer);

            } else if (typeUtils.isAssignable(field.asType(), realmList)) {
                RealmJsonTypeHelper.emitFillRealmListWithJsonValue(
                        metadata.getGetter(fieldName),
                        metadata.getSetter(fieldName),
                        fieldName,
                        ((DeclaredType) field.asType()).getTypeArguments().get(0).toString(),
                        Utils.getProxyClassSimpleName(field),
                        writer);

            } else {
                RealmJsonTypeHelper.emitFillJavaTypeWithJsonValue(
                        metadata.getSetter(fieldName),
                        fieldName,
                        qualifiedFieldType,
                        writer);
            }
        }

        writer.emitStatement("return obj");
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private void emitCreateUsingJsonStream(JavaWriter writer) throws IOException {
        writer.beginMethod(
                className,
                "createUsingJsonStream",
                EnumSet.of(Modifier.PUBLIC, Modifier.STATIC),
                Arrays.asList("Realm", "realm", "JsonReader", "reader"),
                Arrays.asList("IOException"));

        writer.emitStatement("%s obj = realm.createObject(%s.class)",className, className);
        writer.emitStatement("reader.beginObject()");
        writer.beginControlFlow("while (reader.hasNext())");
        writer.emitStatement("String name = reader.nextName()");

        List<VariableElement> fields = metadata.getFields();
        for (int i = 0; i < fields.size(); i++) {
            VariableElement field = fields.get(i);
            String fieldName = field.getSimpleName().toString();
            String qualifiedFieldType = field.asType().toString();

            if (i == 0) {
                writer.beginControlFlow("if (name.equals(\"%s\") && reader.peek() != JsonToken.NULL)", fieldName);
            } else {
                writer.nextControlFlow("else if (name.equals(\"%s\")  && reader.peek() != JsonToken.NULL)", fieldName);
            }
            if (typeUtils.isAssignable(field.asType(), realmObject)) {
                RealmJsonTypeHelper.emitFillRealmObjectFromStream(
                        metadata.getSetter(fieldName),
                        fieldName,
                        qualifiedFieldType,
                        Utils.getProxyClassSimpleName(field),
                        writer);

            } else if (typeUtils.isAssignable(field.asType(), realmList)) {
                RealmJsonTypeHelper.emitFillRealmListFromStream(
                        metadata.getGetter(fieldName),
                        metadata.getSetter(fieldName),
                        ((DeclaredType) field.asType()).getTypeArguments().get(0).toString(),
                        Utils.getProxyClassSimpleName(field),
                        writer);

            } else {
                RealmJsonTypeHelper.emitFillJavaTypeFromStream(
                        metadata.getSetter(fieldName),
                        fieldName,
                        qualifiedFieldType,
                        writer);
            }
        }

        if (fields.size() > 0) {
            writer.nextControlFlow("else");
            writer.emitStatement("reader.skipValue()");
            writer.endControlFlow();
        }
        writer.endControlFlow();
        writer.emitStatement("reader.endObject()");
        writer.emitStatement("return obj");
        writer.endMethod();
        writer.emitEmptyLine();
    }

    private String staticFieldIndexVarName(VariableElement variableElement) {
        return "INDEX_" + variableElement.getSimpleName().toString().toUpperCase();
    }
}


File: realm-annotations-processor/src/test/java/io/realm/processor/RealmProcessorTest.java
/*
 * Copyright 2014 Realm Inc.
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

package io.realm.processor;

import com.google.testing.compile.JavaFileObjects;
import org.junit.Test;

import javax.tools.JavaFileObject;

import java.util.Arrays;

import static com.google.testing.compile.JavaSourceSubjectFactory.javaSource;
import static com.google.testing.compile.JavaSourcesSubjectFactory.javaSources;
import static org.truth0.Truth.ASSERT;

public class RealmProcessorTest {

    private JavaFileObject simpleModel = JavaFileObjects.forResource("some/test/Simple.java");
    private JavaFileObject simpleProxy = JavaFileObjects.forResource("io/realm/SimpleRealmProxy.java");
    private JavaFileObject allTypesModel = JavaFileObjects.forResource("some/test/AllTypes.java");
    private JavaFileObject allTypesProxy = JavaFileObjects.forResource("io/realm/AllTypesRealmProxy.java");
    private JavaFileObject allTypesDefaultModule = JavaFileObjects.forResource("io/realm/RealmDefaultModule.java");
    private JavaFileObject allTypesDefaultMediator = JavaFileObjects.forResource("io/realm/RealmDefaultModuleMediator.java");
    private JavaFileObject booleansModel = JavaFileObjects.forResource("some/test/Booleans.java");
    private JavaFileObject booleansProxy = JavaFileObjects.forResource("io/realm/BooleansRealmProxy.java");
    private JavaFileObject emptyModel = JavaFileObjects.forResource("some/test/Empty.java");
    private JavaFileObject noAccessorsModel = JavaFileObjects.forResource("some/test/NoAccessors.java");
    private JavaFileObject fieldNamesModel = JavaFileObjects.forResource("some/test/FieldNames.java");
    private JavaFileObject customAccessorModel = JavaFileObjects.forResource("some/test/CustomAccessor.java");
    private JavaFileObject missingGenericTypeModel = JavaFileObjects.forResource("some/test/MissingGenericType.java");

    @Test
    public void compileSimpleFile() {
        ASSERT.about(javaSource())
                .that(simpleModel)
                .compilesWithoutError();
    }

    @Test
    public void compileProcessedSimpleFile() throws Exception {
        ASSERT.about(javaSource())
                .that(simpleModel)
                .processedWith(new RealmProcessor())
                .compilesWithoutError();
    }

    @Test
    public void compileProcessedEmptyFile() throws Exception {
        ASSERT.about(javaSource())
                .that(emptyModel)
                .processedWith(new RealmProcessor())
                .failsToCompile();
    }

    @Test
    public void compileSimpleProxyFile() throws Exception {
        ASSERT.about(javaSource())
                .that(simpleProxy)
                .compilesWithoutError();
    }

    @Test
    public void compareProcessedSimpleFile() throws Exception {
        ASSERT.about(javaSource())
                .that(simpleModel)
                .processedWith(new RealmProcessor())
                .compilesWithoutError()
                .and()
                .generatesSources(simpleProxy);
    }

    @Test
    public void compileAllTypesFile() {
        ASSERT.about(javaSource())
                .that(allTypesModel)
                .compilesWithoutError();
    }

    @Test
    public void compileProcessedAllTypesFile() throws Exception {
        ASSERT.about(javaSource())
                .that(allTypesModel)
                .processedWith(new RealmProcessor())
                .compilesWithoutError();
    }

    @Test
    public void compileAllTypesProxyFile() throws Exception {
        ASSERT.about(javaSource())
                .that(allTypesModel)
                .compilesWithoutError();
    }

    @Test
    public void compareProcessedAllTypesFile() throws Exception {
        ASSERT.about(javaSource())
                .that(allTypesModel)
                .processedWith(new RealmProcessor())
                .compilesWithoutError()
                .and()
                .generatesSources(allTypesProxy, allTypesDefaultMediator, allTypesDefaultModule, allTypesDefaultMediator);
    }

    @Test
    public void compileAppModuleCustomClasses() throws Exception {
        ASSERT.about(javaSources())
                .that(Arrays.asList(allTypesModel, JavaFileObjects.forResource("some/test/AppModuleCustomClasses.java")))
                .processedWith(new RealmProcessor())
                .compilesWithoutError();
    }

    @Test
    public void compileAppModuleAllClasses() throws Exception {
        ASSERT.about(javaSources())
                .that(Arrays.asList(allTypesModel, JavaFileObjects.forResource("some/test/AppModuleAllClasses.java")))
                .processedWith(new RealmProcessor())
                .compilesWithoutError();
    }

    @Test
    public void compileLibraryModulesAllClasses() throws Exception {
        ASSERT.about(javaSources())
                .that(Arrays.asList(allTypesModel, JavaFileObjects.forResource("some/test/LibraryModuleAllClasses.java")))
                .processedWith(new RealmProcessor())
                .compilesWithoutError();
    }

    @Test
    public void compileLibraryModulesCustomClasses() throws Exception {
        ASSERT.about(javaSources())
                .that(Arrays.asList(allTypesModel, JavaFileObjects.forResource("some/test/LibraryModuleCustomClasses.java")))
                .processedWith(new RealmProcessor())
                .compilesWithoutError();
    }

    @Test
    public void compileAppModuleMixedParametersFail() throws Exception {
        ASSERT.about(javaSources())
                .that(Arrays.asList(allTypesModel, JavaFileObjects.forResource("some/test/InvalidAppModuleMixedParameters.java")))
                .processedWith(new RealmProcessor())
                .failsToCompile();
    }

    @Test
    public void compileAppModuleWrongTypeFail() throws Exception {
        ASSERT.about(javaSources())
                .that(Arrays.asList(allTypesModel, JavaFileObjects.forResource("some/test/InvalidAppModuleWrongType.java")))
                .processedWith(new RealmProcessor())
                .failsToCompile();
    }

    @Test
    public void compileLibraryModuleMixedParametersFail() throws Exception {
        ASSERT.about(javaSources())
                .that(Arrays.asList(allTypesModel, JavaFileObjects.forResource("some/test/InvalidLibraryModuleMixedParameters.java")))
                .processedWith(new RealmProcessor())
                .failsToCompile();
    }

    @Test
    public void compileLibraryModuleWrongTypeFail() throws Exception {
        ASSERT.about(javaSources())
                .that(Arrays.asList(allTypesModel, JavaFileObjects.forResource("some/test/InvalidLibraryModuleWrongType.java")))
                .processedWith(new RealmProcessor())
                .failsToCompile();
    }

    @Test
    public void compileBooleanFile() {
        ASSERT.about(javaSource())
                .that(booleansModel)
                .compilesWithoutError();
    }

    @Test
    public void compileProcessedBooleansFile() throws Exception {
        ASSERT.about(javaSource())
                .that(booleansModel)
                .processedWith(new RealmProcessor())
                .compilesWithoutError();
    }

    @Test
    public void compileBooleansProxyFile() throws Exception {
        ASSERT.about(javaSource())
                .that(booleansModel)
                .compilesWithoutError();
    }

    @Test
    public void compareProcessedBooleansFile() throws Exception {
        ASSERT.about(javaSource())
                .that(booleansModel)
                .processedWith(new RealmProcessor())
                .compilesWithoutError()
                .and()
                .generatesSources(booleansProxy);
    }

    @Test
    public void compileNoAccessorsFile() {
        ASSERT.about(javaSource())
                .that(noAccessorsModel)
                .processedWith(new RealmProcessor())
                .failsToCompile();
    }

    @Test
    public void compileMissingGenericType() {
        ASSERT.about(javaSource())
                .that(missingGenericTypeModel)
                .processedWith(new RealmProcessor())
                .failsToCompile();
    }

    @Test
    public void compileFieldNamesFiles() {
        ASSERT.about(javaSource())
                .that(fieldNamesModel)
                .processedWith(new RealmProcessor())
                .compilesWithoutError();
    }

    @Test
    public void compileCustomAccessor() {
        ASSERT.about(javaSource())
                .that(customAccessorModel)
                .processedWith(new RealmProcessor())
                .failsToCompile();
    }
}


File: realm-annotations/src/main/java/io/realm/annotations/Index.java
/*
 * Copyright 2014 Realm Inc.
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

package io.realm.annotations;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * This annotation will add a search index to the field. A search index will make the
 * Realm file larger and inserts slower but queries will be faster. 
 *
 * NOTICE: only String fields can be indexed.
 */
@Retention(RetentionPolicy.CLASS)
@Target(ElementType.FIELD)
public @interface Index {

}


File: realm/src/androidTest/java/io/realm/RealmAnnotationTest.java
/*
 * Copyright 2014 Realm Inc.
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

package io.realm;

import android.test.AndroidTestCase;

import io.realm.entities.AnnotationNameConventions;
import io.realm.entities.AnnotationTypes;
import io.realm.entities.PrimaryKeyAsLong;
import io.realm.entities.PrimaryKeyAsString;
import io.realm.exceptions.RealmException;
import io.realm.internal.Table;

public class RealmAnnotationTest extends AndroidTestCase {
    protected Realm testRealm;

    @Override
    protected void setUp() throws Exception {
        Realm.deleteRealmFile(getContext());
        testRealm = Realm.getInstance(getContext());
        testRealm.beginTransaction();
        AnnotationTypes object = testRealm.createObject(AnnotationTypes.class);
        object.setNotIndexString("String 1");
        object.setIndexString("String 2");
        object.setIgnoreString("String 3");
        testRealm.commitTransaction();
    }

    @Override
    protected void tearDown() throws Exception {
        testRealm.close();
    }

    public void testIgnore() {
        Table table = testRealm.getTable(AnnotationTypes.class);
        assertEquals(-1, table.getColumnIndex("ignoreString"));
    }

    public void testIndex() {
        Table table = testRealm.getTable(AnnotationTypes.class);
        assertTrue(table.hasSearchIndex(table.getColumnIndex("indexString")));
        assertFalse(table.hasSearchIndex(table.getColumnIndex("notIndexString")));
    }

    public void testHasPrimaryKeyNoIntIndex() {
        Table table = testRealm.getTable(AnnotationTypes.class);
        assertTrue(table.hasPrimaryKey());
        assertFalse(table.hasSearchIndex(table.getColumnIndex("id")));
    }

    public void testHasPrimaryKeyStringIndex() {
        Table table = testRealm.getTable(PrimaryKeyAsString.class);
        assertTrue(table.hasPrimaryKey());
        assertTrue(table.hasSearchIndex(table.getColumnIndex("name")));
    }

    // Test migrating primary key from string to long with existing data
    public void testPrimaryKeyMigration_long() {
        testRealm.beginTransaction();
        for (int i = 1; i <= 2; i++) {
            PrimaryKeyAsString obj = testRealm.createObject(PrimaryKeyAsString.class);
            obj.setId(i);
            obj.setName("String" + i);
        }

        Table table = testRealm.getTable(PrimaryKeyAsString.class);
        table.setPrimaryKey("id");
        assertEquals(1, table.getPrimaryKey());
        testRealm.cancelTransaction();
    }

    // Test migrating primary key from string to long with existing data
    public void testPrimaryKeyMigration_longDuplicateValues() {
        testRealm.beginTransaction();
        for (int i = 1; i <= 2; i++) {
            PrimaryKeyAsString obj = testRealm.createObject(PrimaryKeyAsString.class);
            obj.setId(1); // Create duplicate values
            obj.setName("String" + i);
        }

        Table table = testRealm.getTable(PrimaryKeyAsString.class);
        try {
            table.setPrimaryKey("id");
            fail("It should not be possible to set a primary key column which already contains duplicate values.");
        } catch (IllegalArgumentException expected) {
            assertEquals(0, table.getPrimaryKey());
        } finally {
            testRealm.cancelTransaction();
        }
    }

    // Test migrating primary key from long to str with existing data
    public void testPrimaryKeyMigration_string() {
        testRealm.beginTransaction();
        for (int i = 1; i <= 2; i++) {
            PrimaryKeyAsLong obj = testRealm.createObject(PrimaryKeyAsLong.class);
            obj.setId(i);
            obj.setName("String" + i);
        }

        Table table = testRealm.getTable(PrimaryKeyAsLong.class);
        table.setPrimaryKey("name");
        assertEquals(1, table.getPrimaryKey());
        testRealm.cancelTransaction();
    }

    // Test migrating primary key from long to str with existing data
    public void testPrimaryKeyMigration_stringDuplicateValues() {
        testRealm.beginTransaction();
        for (int i = 1; i <= 2; i++) {
            PrimaryKeyAsLong obj = testRealm.createObject(PrimaryKeyAsLong.class);
            obj.setId(i);
            obj.setName("String"); // Create duplicate values
        }

        Table table = testRealm.getTable(PrimaryKeyAsLong.class);
        try {
            table.setPrimaryKey("name");
            fail("It should not be possible to set a primary key column which already contains duplicate values.");
        } catch (IllegalArgumentException expected) {
            assertEquals(0, table.getPrimaryKey());
        } finally {
            testRealm.cancelTransaction();
        }
    }

    public void testPrimaryKey_checkPrimaryKeyOnCreate() {
        testRealm.beginTransaction();
        try {
            testRealm.createObject(AnnotationTypes.class);
            fail("Two empty objects cannot be created on the same table if a primary key is defined");
        } catch (RealmException expected) {
        } finally {
            testRealm.cancelTransaction();
        }
    }

    // It should be allowed to override the primary key value with the same value
    public void testPrimaryKey_defaultStringValue() {
        testRealm.beginTransaction();
        PrimaryKeyAsString str = testRealm.createObject(PrimaryKeyAsString.class);
        str.setName("");
        testRealm.commitTransaction();
    }

    // It should be allowed to override the primary key value with the same value
    public void testPrimaryKey_defaultLongValue() {
        testRealm.beginTransaction();
        PrimaryKeyAsLong str = testRealm.createObject(PrimaryKeyAsLong.class);
        str.setId(0);
        testRealm.commitTransaction();
    }

    public void testPrimaryKey_errorOnInsertingSameObject() {
        try {
            testRealm.beginTransaction();
            AnnotationTypes obj1 = testRealm.createObject(AnnotationTypes.class);
            obj1.setId(1);
            AnnotationTypes obj2 = testRealm.createObject(AnnotationTypes.class);
            obj2.setId(1);
            fail("Inserting two objects with same primary key should fail");
        } catch (RealmException expected) {
        } finally {
            testRealm.cancelTransaction();
        }
    }

    public void testPrimaryKeyIsIndexed() {
        Table table = testRealm.getTable(PrimaryKeyAsString.class);
        assertTrue(table.hasPrimaryKey());
        assertTrue(table.hasSearchIndex(0));
    }

    // Annotation processor honors common naming conventions
    // We check if setters and getters are generated and working
    public void testNamingConvention() {
        Realm realm = Realm.getInstance(getContext());
        realm.beginTransaction();
        realm.clear(AnnotationNameConventions.class);
        AnnotationNameConventions anc1 = realm.createObject(AnnotationNameConventions.class);
        anc1.setHasObject(true);
        anc1.setId_object(1);
        anc1.setmObject(2);
        anc1.setObject_id(3);
        anc1.setObject(true);
        realm.commitTransaction();

        AnnotationNameConventions anc2 = realm.allObjects(AnnotationNameConventions.class).first();
        assertTrue(anc2.isHasObject());
        assertEquals(1, anc2.getId_object());
        assertEquals(2, anc2.getmObject());
        assertEquals(3, anc2.getObject_id());
        assertTrue(anc2.isObject());
        realm.close();
    }
}


File: realm/src/androidTest/java/io/realm/internal/JNITableTest.java
package io.realm.internal;

import android.test.AndroidTestCase;
import android.test.MoreAsserts;

import java.io.File;
import java.util.Date;

import io.realm.internal.test.TestHelper;

public class JNITableTest extends AndroidTestCase {

    Table t = new Table();

    Table createTestTable() {
        Table t = new Table();
        t.addColumn(ColumnType.BINARY, "binary"); // 0
        t.addColumn(ColumnType.BOOLEAN, "boolean");  // 1
        t.addColumn(ColumnType.DATE, "date");     // 2
        t.addColumn(ColumnType.DOUBLE, "double"); // 3
        t.addColumn(ColumnType.FLOAT, "float");   // 4
        t.addColumn(ColumnType.INTEGER, "long");      // 5
        t.addColumn(ColumnType.MIXED, "mixed");   // 6
        t.addColumn(ColumnType.STRING, "string"); // 7
        t.addColumn(ColumnType.TABLE, "table");   // 8
        return t;
    }

    @Override
    public void setUp() {
        t = createTestTable();
    }

    public void testTableToString() {
        Table t = new Table();

        t.addColumn(ColumnType.STRING, "stringCol");
        t.addColumn(ColumnType.INTEGER, "intCol");
        t.addColumn(ColumnType.BOOLEAN, "boolCol");

        t.add("s1", 1, true);
        t.add("s2", 2, false);

        String expected =
"    stringCol  intCol  boolCol\n" +
"0:  s1              1     true\n" +
"1:  s2              2    false\n" ;

        assertEquals(expected, t.toString());
    }

    public void testRowOperationsOnZeroRow(){

        Table t = new Table();
        // Remove rows without columns
        try { t.remove(0);  fail("No rows in table"); } catch (ArrayIndexOutOfBoundsException e) {}
        try { t.remove(10); fail("No rows in table"); } catch (ArrayIndexOutOfBoundsException e) {}

        // Column added, remove rows again
        t.addColumn(ColumnType.STRING, "");
        try { t.remove(0);  fail("No rows in table"); } catch (ArrayIndexOutOfBoundsException e) {}
        try { t.remove(10); fail("No rows in table"); } catch (ArrayIndexOutOfBoundsException e) {}

    }

    public void testZeroColOperations() {
        Table tableZeroCols = new Table();

        // Add rows
        try { tableZeroCols.add("val");         fail("No columns in table"); } catch (IllegalArgumentException e) {}
        try { tableZeroCols.addEmptyRow();      fail("No columns in table"); } catch (IndexOutOfBoundsException e) {}
        try { tableZeroCols.addEmptyRows(10);   fail("No columns in table"); } catch (IndexOutOfBoundsException e) {}


        // Col operations
        try { tableZeroCols.removeColumn(0);                fail("No columns in table"); } catch (ArrayIndexOutOfBoundsException e) {}
        try { tableZeroCols.renameColumn(0, "newName");     fail("No columns in table"); } catch (ArrayIndexOutOfBoundsException e) {}
        try { tableZeroCols.removeColumn(10);               fail("No columns in table"); } catch (ArrayIndexOutOfBoundsException e) {}
        try { tableZeroCols.renameColumn(10, "newName");    fail("No columns in table"); } catch (ArrayIndexOutOfBoundsException e) {}
    }

    public void testTableBinaryTest() {
        Table t = new Table();
        t.addColumn(ColumnType.BINARY, "binary");

        byte[] row0 = new byte[] { 1, 2, 3 };
        byte[] row1 = new byte[] { 10, 20, 30 };

        t.getInternalMethods().insertBinary(0, 0, row0);
        t.getInternalMethods().insertDone();
        t.getInternalMethods().insertBinary(0, 1, row1);
        t.getInternalMethods().insertDone();

        byte[] nullByte = null;

        try { t.getInternalMethods().insertBinary(0, 2, nullByte); fail("Inserting null array"); } catch(IllegalArgumentException e) { }


        MoreAsserts.assertEquals(new byte[]{1, 2, 3}, t.getBinaryByteArray(0, 0));
        assertEquals(false, t.getBinaryByteArray(0, 0) == new byte[]{1, 2, 3});

        byte[] newRow0 = new byte[] { 7, 77, 77 };
        t.setBinaryByteArray(0, 0, newRow0);

        MoreAsserts.assertEquals(new byte[]{7, 77, 77}, t.getBinaryByteArray(0, 0));
        assertEquals(false, t.getBinaryByteArray(0, 0) == new byte[] { 1, 2, 3 });

        try { t.setBinaryByteArray(0, 2, nullByte); fail("Inserting null array"); } catch(IllegalArgumentException e) { }
    }


    public void testFindFirstNonExisting() {
        Table t = TestHelper.getTableWithAllColumnTypes();
        t.add(new byte[]{1,2,3}, true, new Date(1384423149761l), 4.5d, 5.7f, 100, new Mixed("mixed"), "string", null);

        assertEquals(-1, t.findFirstBoolean(1, false));
        assertEquals(-1, t.findFirstDate(2, new Date(138442314986l)));
        assertEquals(-1, t.findFirstDouble(3, 1.0d));
        assertEquals(-1, t.findFirstFloat(4, 1.0f));
        assertEquals(-1, t.findFirstLong(5, 50));
        assertEquals(-1, t.findFirstString(7, "other string"));
    }

    public void testFindFirst() {
        final int TEST_SIZE = 10;
        Table t = TestHelper.getTableWithAllColumnTypes();
        for (int i = 0; i < TEST_SIZE; i++) {
            t.add(new byte[]{1,2,3}, true, new Date(1000*i), (double)i, (float)i, i, new Mixed("mixed " + i), "string " + i, null);
        }
        t.add(new byte[]{1,2,3}, true, new Date(1000*TEST_SIZE), (double)TEST_SIZE, (float)TEST_SIZE, TEST_SIZE, new Mixed("mixed " + TEST_SIZE), "", null);

        assertEquals(0, t.findFirstBoolean(1, true));
        for (int i = 0; i < TEST_SIZE; i++) {
            assertEquals(i, t.findFirstDate(2, new Date(1000*i)));
            assertEquals(i, t.findFirstDouble(3, (double) i));
            assertEquals(i, t.findFirstFloat(4, (float) i));
            assertEquals(i, t.findFirstLong(5, i));
            assertEquals(i, t.findFirstString(7, "string " + i));
        }

        assertEquals(TEST_SIZE, t.findFirstString(7, ""));

        try {
            t.findFirstString(7, null);
            fail();
        } catch (IllegalArgumentException expected) {}

        try {
            t.findFirstDate(2, null);
            fail();
        } catch (IllegalArgumentException expected) {}
    }


    public void testGetValuesFromNonExistingColumn() {
        Table t = TestHelper.getTableWithAllColumnTypes();
        t.addEmptyRows(10);

        try { t.getBinaryByteArray(-1, 0);          fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getBinaryByteArray(-10, 0);         fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getBinaryByteArray(9, 0);           fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

        try { t.getBoolean(-1, 0);                  fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getBoolean(-10, 0);                 fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getBoolean(9, 0);                   fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

        try { t.getDate(-1, 0);                     fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getDate(-10, 0);                    fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getDate(9, 0);                      fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

        try { t.getDouble(-1, 0);                   fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getDouble(-10, 0);                  fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getDouble(9, 0);                    fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

        try { t.getFloat(-1, 0);                    fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getFloat(-10, 0);                   fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getFloat(9, 0);                     fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

        try { t.getLong(-1, 0);                     fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getLong(-10, 0);                    fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getLong(9, 0);                      fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

        try { t.getMixed(-1, 0);                    fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getMixed(-10, 0);                   fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getMixed(9, 0);                     fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

        try { t.getString(-1, 0);                   fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getString(-10, 0);                  fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getString(9, 0);                    fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

        try { t.getSubtable(-1, 0);                 fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getSubtable(-10, 0);                fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getSubtable(9, 0);                  fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

    }

    public void testGetNonExistingColumn() {
        Table t = new Table();
        t.addColumn(ColumnType.INTEGER, "int");

        assertEquals(-1, t.getColumnIndex("non-existing column"));
        try { t.getColumnIndex(null); fail("column name null"); } catch (IllegalArgumentException e) { }
    }


    public void testGetSortedView() {
        Table t = new Table();
        t.addColumn(ColumnType.INTEGER, "");
        t.addColumn(ColumnType.STRING, "");
        t.addColumn(ColumnType.DOUBLE, "");

        t.add(1, "s", 1000d);
        t.add(3,"sss", 10d);
        t.add(2, "ss", 100d);


        // Check the order is as it is added
        assertEquals(1, t.getLong(0, 0));
        assertEquals(3, t.getLong(0, 1));
        assertEquals(2, t.getLong(0, 2));
        assertEquals("s", t.getString(1, 0));
        assertEquals("sss", t.getString(1, 1));
        assertEquals("ss", t.getString(1, 2));
        assertEquals(1000d, t.getDouble(2, 0));
        assertEquals(10d, t.getDouble(2, 1));
        assertEquals(100d, t.getDouble(2, 2));

        // Get the sorted view on first column
        TableView v = t.getSortedView(0);

        // Check the new order
        assertEquals(1, v.getLong(0, 0));
        assertEquals(2, v.getLong(0, 1));
        assertEquals(3, v.getLong(0, 2));
        assertEquals("s", v.getString(1, 0));
        assertEquals("ss", v.getString(1, 1));
        assertEquals("sss", v.getString(1, 2));
        assertEquals(1000d, v.getDouble(2, 0));
        assertEquals(100d, v.getDouble(2, 1));
        assertEquals(10d, v.getDouble(2, 2));

        // Get the sorted view on first column descending
        v = t.getSortedView(0, TableView.Order.descending);

        // Check the new order
        assertEquals(3, v.getLong(0, 0));
        assertEquals(2, v.getLong(0, 1));
        assertEquals(1, v.getLong(0, 2));
        assertEquals("sss", v.getString(1, 0));
        assertEquals("ss", v.getString(1, 1));
        assertEquals("s", v.getString(1, 2));
        assertEquals(10d, v.getDouble(2, 0));
        assertEquals(100d, v.getDouble(2, 1));
        assertEquals(1000d, v.getDouble(2, 2));

        // Some out of bounds test cases
        try { t.getSortedView(-1, TableView.Order.descending);    fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getSortedView(-100, TableView.Order.descending);  fail("Column is less than 0"); } catch (ArrayIndexOutOfBoundsException e) { }
        try { t.getSortedView(100, TableView.Order.descending);   fail("Column does not exist"); } catch (ArrayIndexOutOfBoundsException e) { }

    }

    public void testSetDataInNonExistingRow() {
        Table t = new Table();
        t.addColumn(ColumnType.STRING, "colName");
        t.add("String val");

        try { t.set(1, "new string val"); fail("Row 1 does not exist"); } catch (IllegalArgumentException e) { }
    }


    public void testSetNulls() {
        Table t = new Table();
        t.addColumn(ColumnType.STRING, "");
        t.addColumn(ColumnType.DATE, "");
        t.addColumn(ColumnType.MIXED, "");
        t.addColumn(ColumnType.BINARY, "");
        t.add("String val", new Date(), new Mixed(""), new byte[] { 1,2,3} );

        try { t.setString(0, 0, null);  fail("null string not allowed"); } catch (IllegalArgumentException e) { }
        try { t.setDate(1, 0, null);    fail("null Date not allowed"); } catch (IllegalArgumentException e) { }
    }

    public void testSetDataWithWrongColumnAmountParameters() {
        Table t = new Table();
        t.addColumn(ColumnType.STRING, "colName");
        t.add("String val");

        try { t.set(0, "new string val", "This column does not exist"); fail("Table only has 1 column"); } catch (IllegalArgumentException e) { }
    }

    public void testAddNegativeEmptyRows() {
        Table t = new Table();
        t.addColumn(ColumnType.STRING, "colName");

        try { t.addEmptyRows(-1); fail("Argument is negative"); } catch (IllegalArgumentException e ) { }
    }

    public void testAddNullInMixedColumn() {
        Table t = new Table();
        t.addColumn(ColumnType.MIXED, "mixed");
        t.add(new Mixed(true));

        try { t.setMixed(0, 0, null); fail("Argument is null"); } catch (IllegalArgumentException e) { }
    }

    public void testSetDataWithWrongColumnTypes() {
        Table t = new Table();
        t.addColumn(ColumnType.STRING, "colName");
        t.add("String val");

        try { t.set(0, 100); fail("Table has string column, and here an integer is inserted"); } catch (IllegalArgumentException e) { }
    }

    public void testImmutableInsertNotAllowed() {

        String FILENAME = new File(this.getContext().getFilesDir(), "only-test-file.realm").toString();
        String TABLENAME = "tableName";

        new File(FILENAME).delete();
        new File(FILENAME+".lock").delete();
        SharedGroup group = new SharedGroup(FILENAME);

        // Write transaction must be run so we are sure a db exists with the correct table
        WriteTransaction wt = group.beginWrite();
        try {
            Table table = wt.getTable(TABLENAME);
            table.addColumn(ColumnType.STRING, "col0");
            table.add("value0");
            table.add("value1");
            table.add("value2");

            wt.commit();
        } catch (Throwable t) {
            wt.rollback();
        }

        ReadTransaction rt = group.beginRead();
        try {
            Table table = rt.getTable(TABLENAME);

            try {  table.addAt(1, "NewValue"); fail("Exception expected when inserting in read transaction"); } catch (IllegalStateException e) { }

        } finally {
            rt.endRead();
        }
    }

    public void testGetName() {
        String FILENAME = new File(this.getContext().getFilesDir(), "only-test-file.realm").toString();
        String TABLENAME = "tableName";

        new File(FILENAME).delete();
        new File(FILENAME+".lock").delete();
        SharedGroup group = new SharedGroup(FILENAME);

        // Write transaction must be run so we are sure a db exists with the correct table
        WriteTransaction wt = group.beginWrite();
        try {
            Table table = wt.getTable(TABLENAME);
            wt.commit();
        } catch (Throwable t) {
            wt.rollback();
        }

        ReadTransaction rt = group.beginRead();
        Table table = rt.getTable(TABLENAME);
        assertEquals(TABLENAME, table.getName());
    }

    public void testShouldThrowWhenSetIndexOnWrongColumnType() {
        for (long colIndex = 0; colIndex < t.getColumnCount(); colIndex++) {

            // Check all other column types than String throws exception when using addSearchIndex()/hasSearchIndex()
            boolean exceptionExpected = (t.getColumnType(colIndex) != ColumnType.STRING);

            // Try to addSearchIndex()
            try {
                t.addSearchIndex(colIndex);
                if (exceptionExpected)
                    fail("expected exception for colIndex " + colIndex);
            } catch (IllegalArgumentException e) {
            }

            // Try to hasSearchIndex() for all columnTypes
            t.hasSearchIndex(colIndex);
        }
    }


    /**
     * Returns a table with a few columns and values
     * @return
     */
    private Table getTableWithSimpleData(){
        Table table =  new Table();
        table.addColumn(ColumnType.STRING, "col");
        table.addColumn(ColumnType.INTEGER, "int");
        table.add("val1", 100);
        table.add("val2", 200);
        table.add("val3", 300);

        return table;
    }

    public void testColumnName() {
        Table t = new Table();
        try { t.addColumn(ColumnType.STRING, "I am 64 chracters..............................................."); fail("Only 63 chracters supported"); } catch (IllegalArgumentException e) { }
        t.addColumn(ColumnType.STRING, "I am 63 chracters..............................................");
    }

    public void testTableNumbers() {
        Table t = new Table();
        t.addColumn(ColumnType.INTEGER, "intCol");
        t.addColumn(ColumnType.DOUBLE, "doubleCol");
        t.addColumn(ColumnType.FLOAT, "floatCol");
        t.addColumn(ColumnType.STRING, "StringCol");

        // Add 3 rows of data with same values in each column
        t.add(1, 2.0d, 3.0f, "s1");
        t.add(1, 2.0d, 3.0f, "s1");
        t.add(1, 2.0d, 3.0f, "s1");

        // Add other values
        t.add(10, 20.0d, 30.0f, "s10");
        t.add(100, 200.0d, 300.0f, "s100");
        t.add(1000, 2000.0d, 3000.0f, "s1000");

        // Count instances of values added in the first 3 rows
        assertEquals(3, t.count(0, 1));
        assertEquals(3, t.count(1, 2.0d));
        assertEquals(3, t.count(2, 3.0f));
        assertEquals(3, t.count(3, "s1"));

        assertEquals(3, t.findAllDouble(1, 2.0d).size());
        assertEquals(3, t.findAllFloat(2, 3.0f).size());

        assertEquals(3, t.findFirstDouble(1, 20.0d)); // Find rows index for first double value of 20.0 in column 1
        assertEquals(4, t.findFirstFloat(2, 300.0f)); // Find rows index for first float value of 300.0 in column 2

        // Set double and float
        t.setDouble(1, 2, -2.0d);
        t.setFloat(2, 2, -3.0f);

        // Get double tests
        assertEquals(-2.0d, t.getDouble(1, 2));
        assertEquals(20.0d, t.getDouble(1, 3));
        assertEquals(200.0d, t.getDouble(1, 4));
        assertEquals(2000.0d, t.getDouble(1, 5));

        // Get float test
        assertEquals(-3.0f, t.getFloat(2, 2));
        assertEquals(30.0f, t.getFloat(2, 3));
        assertEquals(300.0f, t.getFloat(2, 4));
        assertEquals(3000.0f, t.getFloat(2, 5));
    }

    public void testMaximumDate() {

        Table table = new Table();
        table.addColumn(ColumnType.DATE, "date");

        table.add(new Date(0));
        table.add(new Date(10000));
        table.add(new Date(1000));

        assertEquals(new Date(10000), table.maximumDate(0));

    }

    public void testMinimumDate() {

        Table table = new Table();
        table.addColumn(ColumnType.DATE, "date");

        table.add(new Date(10000));
        table.add(new Date(0));
        table.add(new Date(1000));

        assertEquals(new Date(0), table.minimumDate(0));

    }

}
