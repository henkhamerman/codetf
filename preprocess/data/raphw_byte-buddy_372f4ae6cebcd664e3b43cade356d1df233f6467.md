Refactoring Types: ['Move Attribute']
et/bytebuddy/description/type/TypeDescription.java
package net.bytebuddy.description.type;

import com.sun.javaws.jnl.PackageDesc;
import net.bytebuddy.description.annotation.AnnotationDescription;
import net.bytebuddy.description.annotation.AnnotationList;
import net.bytebuddy.description.enumeration.EnumerationDescription;
import net.bytebuddy.description.field.FieldList;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.method.MethodList;
import net.bytebuddy.description.type.generic.GenericTypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeList;
import net.bytebuddy.description.type.generic.TypeVariableSource;
import net.bytebuddy.implementation.bytecode.StackSize;
import net.bytebuddy.utility.JavaType;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;
import org.objectweb.asm.signature.SignatureWriter;

import java.io.Serializable;
import java.lang.annotation.Annotation;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.*;

import static net.bytebuddy.matcher.ElementMatchers.named;
import static net.bytebuddy.utility.ByteBuddyCommons.join;

/**
 * Implementations of this interface represent a Java type, i.e. a class or interface.
 */
public interface TypeDescription extends GenericTypeDescription, TypeVariableSource, Iterable<GenericTypeDescription> {

    /**
     * A representation of the {@link java.lang.Object} type.
     */
    TypeDescription OBJECT = new ForLoadedType(Object.class);

    /**
     * A representation of the {@link java.lang.String} type.
     */
    TypeDescription STRING = new ForLoadedType(String.class);

    /**
     * A representation of the {@link java.lang.Class} type.
     */
    TypeDescription CLASS = new ForLoadedType(Class.class);

    /**
     * A representation of the {@code void} non-type.
     */
    TypeDescription VOID = new ForLoadedType(void.class);

    /**
     * A representation of the {@link java.lang.Enum} type.
     */
    TypeDescription ENUM = new ForLoadedType(Enum.class);

    /**
     * Checks if {@code value} is an instance of the type represented by this instance.
     *
     * @param value The object of interest.
     * @return {@code true} if the object is an instance of the type described by this instance.
     */
    boolean isInstance(Object value);

    /**
     * Checks if {@code value} is an instance of the type represented by this instance or a wrapper instance of the
     * corresponding primitive value.
     *
     * @param value The object of interest.
     * @return {@code true} if the object is an instance or wrapper of the type described by this instance.
     */
    boolean isInstanceOrWrapper(Object value);

    /**
     * Checks if this type is assignable from the type described by this instance, for example for
     * {@code class Foo} and {@code class Bar extends Foo}, this method would return {@code true} for
     * {@code Foo.class.isAssignableFrom(Bar.class)}.
     *
     * @param type The type of interest.
     * @return {@code true} if this type is assignable from {@code type}.
     */
    boolean isAssignableFrom(Class<?> type);

    /**
     * Checks if this type is assignable from the type described by this instance, for example for
     * {@code class Foo} and {@code class Bar extends Foo}, this method would return {@code true} for
     * {@code Foo.class.isAssignableFrom(Bar.class)}.
     * <p>&nbsp;</p>
     * Implementations of this methods are allowed to delegate to
     * {@link TypeDescription#isAssignableFrom(Class)}
     *
     * @param typeDescription The type of interest.
     * @return {@code true} if this type is assignable from {@code type}.
     */
    boolean isAssignableFrom(TypeDescription typeDescription);

    /**
     * Checks if this type is assignable from the type described by this instance, for example for
     * {@code class Foo} and {@code class Bar extends Foo}, this method would return {@code true} for
     * {@code Bar.class.isAssignableTo(Foo.class)}.
     *
     * @param type The type of interest.
     * @return {@code true} if this type is assignable to {@code type}.
     */
    boolean isAssignableTo(Class<?> type);

    /**
     * Checks if this type is assignable from the type described by this instance, for example for
     * {@code class Foo} and {@code class Bar extends Foo}, this method would return {@code true} for
     * {@code Bar.class.isAssignableFrom(Foo.class)}.
     * <p>&nbsp;</p>
     * Implementations of this methods are allowed to delegate to
     * {@link TypeDescription#isAssignableTo(Class)}
     *
     * @param typeDescription The type of interest.
     * @return {@code true} if this type is assignable to {@code type}.
     */
    boolean isAssignableTo(TypeDescription typeDescription);

    /**
     * Checks if the type described by this instance represents {@code type}.
     *
     * @param type The type of interest.
     * @return {@code true} if the type described by this instance represents {@code type}.
     */
    boolean represents(Class<?> type);

    /**
     * Checks if the type described by this entity is an array.
     *
     * @return {@code true} if this type description represents an array.
     */
    boolean isArray();

    /**
     * Returns the component type of this type.
     *
     * @return The component type of this array or {@code null} if this type description does not represent an array.
     */
    @Override
    TypeDescription getComponentType();

    /**
     * Checks if the type described by this entity is a primitive type.
     *
     * @return {@code true} if this type description represents a primitive type.
     */
    boolean isPrimitive();

    /**
     * Returns the component type of this type.
     *
     * @return The component type of this array or {@code null} if type does not have a super type as for the
     * {@link java.lang.Object} type.
     */
    TypeDescription getSuperType();

    GenericTypeDescription getSuperTypeGen();

    /**
     * Returns a list of interfaces that are implemented by this type.
     *
     * @return A list of interfaces that are implemented by this type.
     */
    TypeList getInterfaces();

    GenericTypeList getInterfacesGen();

    /**
     * Returns all interfaces that are implemented by this type, either directly or indirectly.
     *
     * @return A list of all interfaces of this type in random order.
     */
    TypeList getInheritedInterfaces();

    /**
     * Returns a description of the enclosing method of this type.
     *
     * @return A description of the enclosing method of this type or {@code null} if there is no such method.
     */
    MethodDescription getEnclosingMethod();

    /**
     * Returns a description of the enclosing type of this type.
     *
     * @return A  description of the enclosing type of this type or {@code null} if there is no such type.
     */
    TypeDescription getEnclosingType();

    /**
     * <p>
     * Returns the type's actual modifiers as present in the class file. For example, a type cannot be {@code private}.
     * but it modifiers might reflect this property nevertheless if a class was defined as a private inner class.
     * </p>
     * <p>
     * Unfortunately, the modifier for marking a {@code static} class collides with the {@code SUPER} modifier such
     * that these flags are indistinguishable. Therefore, the flag must be specified manually.
     * </p>
     *
     * @param superFlag {@code true} if the super flag should be set.
     * @return The type's actual modifiers.
     */
    int getActualModifiers(boolean superFlag);

    /**
     * Returns the simple internalName of this type.
     *
     * @return The simple internalName of this type.
     */
    String getSimpleName();

    /**
     * Returns the canonical internalName of this type.
     *
     * @return The canonical internalName of this type.
     */
    String getCanonicalName();

    /**
     * Checks if this type description represents an anonymous type.
     *
     * @return {@code true} if this type description represents an anonymous type.
     */
    boolean isAnonymousClass();

    /**
     * Checks if this type description represents a local type.
     *
     * @return {@code true} if this type description represents a local type.
     */
    boolean isLocalClass();

    /**
     * Checks if this type description represents a member type.
     *
     * @return {@code true} if this type description represents a member type.
     */
    boolean isMemberClass();

    /**
     * Returns a list of fields that are declared by this type.
     *
     * @return A list of fields that are declared by this type.
     */
    FieldList getDeclaredFields();

    /**
     * Returns a list of methods that are declared by this type.
     *
     * @return A list of methods that are declared by this type.
     */
    MethodList getDeclaredMethods();

    /**
     * Returns the package internalName of the type described by this instance.
     *
     * @return The package internalName of the type described by this instance.
     */
    PackageDescription getPackage();

    /**
     * Returns the annotations that this type declares or inherits from super types.
     *
     * @return A list of all inherited annotations.
     */
    AnnotationList getInheritedAnnotations();

    /**
     * Checks if two types are defined in the same package.
     *
     * @param typeDescription The type of interest.
     * @return {@code true} if this type and the given type are in the same package.
     */
    boolean isSamePackage(TypeDescription typeDescription);

    /**
     * Checks if instances of this type can be stored in the constant pool of a class. Note that any primitive
     * type that is smaller than an {@code int} cannot be stored in the constant pool as those types are represented
     * as {@code int} values internally.
     *
     * @return {@code true} if instances of this type can be stored in the constant pool of a class.
     */
    boolean isConstantPool();

    /**
     * Checks if this type represents a wrapper type for a primitive type. The {@link java.lang.Void} type is
     * not considered to be a wrapper type.
     *
     * @return {@code true} if this type represents a wrapper type.
     */
    boolean isPrimitiveWrapper();

    /**
     * Checks if instances of this type can be returned from an annotation method.
     *
     * @return {@code true} if instances of this type can be returned from an annotation method.
     */
    boolean isAnnotationReturnType();

    /**
     * Checks if instances of this type can be used for describing an annotation value.
     *
     * @return {@code true} if instances of this type can be used for describing an annotation value.
     */
    boolean isAnnotationValue();

    /**
     * Checks if instances of this type can be used for describing the given annotation value.
     *
     * @param value The value that is supposed to describe the annotation value for this instance.
     * @return {@code true} if instances of this type can be used for describing the given annotation value..
     */
    boolean isAnnotationValue(Object value);

    /**
     * An abstract base implementation of a type description.
     */
    abstract class AbstractTypeDescription extends AbstractModifierReviewable implements TypeDescription {

        /**
         * Collects all interfaces for a given type description.
         *
         * @param typeDescription An interface type to check for other interfaces.
         * @param interfaces      A collection of already discovered interfaces.
         */
        private static void collect(TypeDescription typeDescription, Set<TypeDescription> interfaces) {
            if (interfaces.add(typeDescription)) {
                for (TypeDescription interfaceType : typeDescription.getInterfaces()) {
                    collect(interfaceType, interfaces);
                }
            }
        }

        @Override
        public TypeDescription getSuperType() {
            GenericTypeDescription superType = getSuperTypeGen();
            return superType == null
                    ? null
                    : superType.asRawType();
        }

        @Override
        public TypeList getInterfaces() {
            return getInterfacesGen().asRawTypes();
        }

        @Override
        public Sort getSort() {
            return Sort.RAW;
        }

        @Override
        public TypeDescription asRawType() {
            return this;
        }

        @Override
        public GenericTypeList getUpperBounds() {
            return new GenericTypeList.Empty();
        }

        @Override
        public GenericTypeList getLowerBounds() {
            return new GenericTypeList.Empty();
        }

        @Override
        public boolean isInstance(Object value) {
            return isAssignableFrom(value.getClass());
        }

        @Override
        public boolean isInstanceOrWrapper(Object value) {
            return isInstance(value)
                    || (represents(boolean.class) && value instanceof Boolean)
                    || (represents(byte.class) && value instanceof Byte)
                    || (represents(short.class) && value instanceof Short)
                    || (represents(char.class) && value instanceof Character)
                    || (represents(int.class) && value instanceof Integer)
                    || (represents(long.class) && value instanceof Long)
                    || (represents(float.class) && value instanceof Float)
                    || (represents(double.class) && value instanceof Double);

        }

        @Override
        public boolean isAnnotationValue(Object value) {
            if ((represents(Class.class) && value instanceof TypeDescription)
                    || (value instanceof AnnotationDescription && ((AnnotationDescription) value).getAnnotationType().equals(this))
                    || (value instanceof EnumerationDescription && ((EnumerationDescription) value).getEnumerationType().equals(this))
                    || (represents(String.class) && value instanceof String)
                    || (represents(boolean.class) && value instanceof Boolean)
                    || (represents(byte.class) && value instanceof Byte)
                    || (represents(short.class) && value instanceof Short)
                    || (represents(char.class) && value instanceof Character)
                    || (represents(int.class) && value instanceof Integer)
                    || (represents(long.class) && value instanceof Long)
                    || (represents(float.class) && value instanceof Float)
                    || (represents(double.class) && value instanceof Double)
                    || (represents(String[].class) && value instanceof String[])
                    || (represents(boolean[].class) && value instanceof boolean[])
                    || (represents(byte[].class) && value instanceof byte[])
                    || (represents(short[].class) && value instanceof short[])
                    || (represents(char[].class) && value instanceof char[])
                    || (represents(int[].class) && value instanceof int[])
                    || (represents(long[].class) && value instanceof long[])
                    || (represents(float[].class) && value instanceof float[])
                    || (represents(double[].class) && value instanceof double[])
                    || (represents(Class[].class) && value instanceof TypeDescription[])) {
                return true;
            } else if (isAssignableTo(Annotation[].class) && value instanceof AnnotationDescription[]) {
                for (AnnotationDescription annotationDescription : (AnnotationDescription[]) value) {
                    if (!annotationDescription.getAnnotationType().equals(getComponentType())) {
                        return false;
                    }
                }
                return true;
            } else if (isAssignableTo(Enum[].class) && value instanceof EnumerationDescription[]) {
                for (EnumerationDescription enumerationDescription : (EnumerationDescription[]) value) {
                    if (!enumerationDescription.getEnumerationType().equals(getComponentType())) {
                        return false;
                    }
                }
                return true;
            } else {
                return false;
            }
        }

        @Override
        public String getInternalName() {
            return getName().replace('.', '/');
        }

        @Override
        public int getActualModifiers(boolean superFlag) {
            int actualModifiers;
            if (isPrivate()) {
                actualModifiers = getModifiers() & ~(Opcodes.ACC_PRIVATE | Opcodes.ACC_STATIC);
            } else if (isProtected()) {
                actualModifiers = getModifiers() & ~(Opcodes.ACC_PROTECTED | Opcodes.ACC_STATIC) | Opcodes.ACC_PUBLIC;
            } else {
                actualModifiers = getModifiers() & ~Opcodes.ACC_STATIC;
            }
            return superFlag ? (actualModifiers | Opcodes.ACC_SUPER) : actualModifiers;
        }

        @Override
        public String getGenericSignature() {
            GenericTypeDescription superType = getSuperTypeGen();
            if (superType == null) {
                return null;
            }
            SignatureWriter signatureWriter = new SignatureWriter();
            boolean generic = false;
            for (GenericTypeDescription typeVariable : getTypeVariables()) {
                signatureWriter.visitFormalTypeParameter(typeVariable.getSymbol());
                for (GenericTypeDescription upperBound : typeVariable.getUpperBounds()) {
                    upperBound.accept(new GenericTypeDescription.Visitor.ForSignatureVisitor(upperBound.asRawType().isInterface()
                            ? signatureWriter.visitInterfaceBound()
                            : signatureWriter.visitClassBound()));
                }
                generic = true;
            }
            superType.accept(new GenericTypeDescription.Visitor.ForSignatureVisitor(signatureWriter.visitSuperclass()));
            generic = generic || !superType.getSort().isRawType();
            for (GenericTypeDescription interfaceType : getInterfacesGen()) {
                interfaceType.accept(new GenericTypeDescription.Visitor.ForSignatureVisitor(signatureWriter.visitInterface()));
                generic = generic || !interfaceType.getSort().isRawType();
            }
            return generic
                    ? signatureWriter.toString()
                    : null;
        }

        @Override
        public TypeVariableSource getVariableSource() {
            return null;
        }

        @Override
        public boolean isSamePackage(TypeDescription typeDescription) {
            PackageDescription thisPackage = getPackage(), otherPackage = typeDescription.getPackage();
            return thisPackage == null || otherPackage == null
                    ? thisPackage == otherPackage
                    : thisPackage.equals(otherPackage);
        }

        @Override
        public boolean isVisibleTo(TypeDescription typeDescription) {
            return isPublic() || isProtected() || isSamePackage(typeDescription);
        }

        @Override
        public TypeList getInheritedInterfaces() {
            Set<TypeDescription> interfaces = new HashSet<TypeDescription>();
            TypeDescription current = this;
            do {
                for (TypeDescription interfaceType : current.getInterfaces()) {
                    collect(interfaceType, interfaces);
                }
            } while ((current = current.getSuperType()) != null);
            return new TypeList.Explicit(new ArrayList<TypeDescription>(interfaces));
        }

        @Override
        public AnnotationList getInheritedAnnotations() {
            AnnotationList declaredAnnotations = getDeclaredAnnotations();
            if (getSuperType() == null) {
                return declaredAnnotations;
            } else {
                Set<TypeDescription> annotationTypes = new HashSet<TypeDescription>(declaredAnnotations.size());
                for (AnnotationDescription annotationDescription : declaredAnnotations) {
                    annotationTypes.add(annotationDescription.getAnnotationType());
                }
                return new AnnotationList.Explicit(join(declaredAnnotations, getSuperType().getInheritedAnnotations().inherited(annotationTypes)));
            }
        }

        @Override
        public String getSourceCodeName() {
            if (isArray()) {
                TypeDescription typeDescription = this;
                int dimensions = 0;
                do {
                    dimensions++;
                    typeDescription = typeDescription.getComponentType();
                } while (typeDescription.isArray());
                StringBuilder stringBuilder = new StringBuilder();
                stringBuilder.append(typeDescription.getSourceCodeName());
                for (int i = 0; i < dimensions; i++) {
                    stringBuilder.append("[]");
                }
                return stringBuilder.toString();
            } else {
                return getName();
            }
        }

        /**
         * Returns the name of this type's package.
         *
         * @return The name of this type's package or {@code null} if this type is defined in the default package.
         */
        protected String getPackageName() {
            String name = getName();
            int packageIndex = name.lastIndexOf('.');
            return packageIndex == -1
                    ? null
                    : name.substring(0, packageIndex);
        }

        @Override
        public boolean isConstantPool() {
            return represents(int.class)
                    || represents(long.class)
                    || represents(float.class)
                    || represents(double.class)
                    || represents(String.class)
                    || represents(Class.class)
                    || JavaType.METHOD_HANDLE.getTypeStub().equals(this)
                    || JavaType.METHOD_TYPE.getTypeStub().equals(this);
        }

        @Override
        public boolean isPrimitiveWrapper() {
            return represents(Boolean.class)
                    || represents(Byte.class)
                    || represents(Short.class)
                    || represents(Character.class)
                    || represents(Integer.class)
                    || represents(Long.class)
                    || represents(Float.class)
                    || represents(Double.class);
        }

        @Override
        public boolean isAnnotationReturnType() {
            return isPrimitive()
                    || represents(String.class)
                    || (isAssignableTo(Enum.class) && !represents(Enum.class))
                    || (isAssignableTo(Annotation.class) && !represents(Annotation.class))
                    || represents(Class.class)
                    || (isArray() && !getComponentType().isArray() && getComponentType().isAnnotationReturnType());
        }

        @Override
        public boolean isAnnotationValue() {
            return isPrimitive()
                    || represents(String.class)
                    || isAssignableTo(TypeDescription.class)
                    || isAssignableTo(AnnotationDescription.class)
                    || isAssignableTo(EnumerationDescription.class)
                    || (isArray() && !getComponentType().isArray() && getComponentType().isAnnotationValue());
        }

        @Override
        public GenericTypeList getParameters() {
            return new GenericTypeList.Empty();
        }

        @Override
        public String getSymbol() {
            return null;
        }

        @Override
        public String getTypeName() {
            return getName();
        }

        @Override
        public GenericTypeDescription getOwnerType() {
            return null;
        }

        @Override
        public TypeVariableSource getEnclosingSource() {
            MethodDescription enclosingMethod = getEnclosingMethod();
            return enclosingMethod == null
                    ? getEnclosingType()
                    : enclosingMethod;
        }

        @Override
        public GenericTypeDescription findVariable(String symbol) {
            GenericTypeList typeVariables = getTypeVariables().filter(named(symbol));
            if (typeVariables.isEmpty()) {
                TypeVariableSource enclosingSource = getEnclosingSource();
                return enclosingSource == null
                        ? null
                        : enclosingSource.findVariable(symbol);
            } else {
                return typeVariables.getOnly();
            }
        }

        @Override
        public <T> T accept(TypeVariableSource.Visitor<T> visitor) {
            return visitor.onType(this);
        }

        @Override
        public <T> T accept(GenericTypeDescription.Visitor<T> visitor) {
            return visitor.onRawType(this);
        }

        @Override
        public Iterator<GenericTypeDescription> iterator() {
            return new SuperTypeIterator(this);
        }

        @Override
        public boolean equals(Object other) {
            return other == this || other instanceof GenericTypeDescription
                    && ((GenericTypeDescription) other).getSort().isRawType()
                    && getInternalName().equals(((GenericTypeDescription) other).asRawType().getInternalName());
        }

        @Override
        public int hashCode() {
            return getInternalName().hashCode();
        }

        @Override
        public String toString() {
            return (isPrimitive() ? "" : (isInterface() ? "interface" : "class") + " ") + getName();
        }

        protected static class SuperTypeIterator implements Iterator<GenericTypeDescription> {

            private GenericTypeDescription nextType;

            protected SuperTypeIterator(TypeDescription initialType) {
                nextType = initialType;
            }

            @Override
            public boolean hasNext() {
                return nextType != null;
            }

            @Override
            public GenericTypeDescription next() {
                if (!hasNext()) {
                    throw new NoSuchElementException("End of type hierarchy");
                }
                try {
                    return nextType;
                } finally {
                    nextType = nextType.asRawType().getSuperTypeGen(); // TODO: Retain variables
                }
            }

            @Override
            public void remove() {
                throw new UnsupportedOperationException("remove");
            }
        }

        /**
         * An adapter implementation of a {@link TypeDescription} that
         * describes any type that is not an array or a primitive type.
         */
        public abstract static class OfSimpleType extends AbstractTypeDescription {

            /**
             * Checks if a specific type is assignable to another type where the source type must be a super
             * type of the target type.
             *
             * @param sourceType The source type to which another type is to be assigned to.
             * @param targetType The target type that is to be assigned to the source type.
             * @return {@code true} if the target type is assignable to the source type.
             */
            private static boolean isAssignable(TypeDescription sourceType, TypeDescription targetType) {
                // Means that '[sourceType] var = ([targetType]) val;' is a valid assignment. This is true, if:
                // (1) Both types are equal.
                if (sourceType.equals(targetType)) {
                    return true;
                }
                // Interfaces do not extend the Object type but are assignable to the Object type.
                if (sourceType.represents(Object.class) && !targetType.isPrimitive()) {
                    return true;
                }
                // The sub type has a super type and this super type is assignable to the super type.
                TypeDescription targetTypeSuperType = targetType.getSuperType();
                if (targetTypeSuperType != null && targetTypeSuperType.isAssignableTo(sourceType)) {
                    return true;
                }
                // (2) If the target type is an interface, any of this type's interfaces might be assignable to it.
                if (sourceType.isInterface()) {
                    for (TypeDescription interfaceType : targetType.getInterfaces()) {
                        if (interfaceType.isAssignableTo(sourceType)) {
                            return true;
                        }
                    }
                }
                // (3) None of these criteria are true, i.e. the types are not assignable.
                return false;
            }

            @Override
            public boolean isAssignableFrom(Class<?> type) {
                return isAssignableFrom(new ForLoadedType(type));
            }

            @Override
            public boolean isAssignableFrom(TypeDescription typeDescription) {
                return isAssignable(this, typeDescription);
            }

            @Override
            public boolean isAssignableTo(Class<?> type) {
                return isAssignableTo(new ForLoadedType(type));
            }

            @Override
            public boolean isAssignableTo(TypeDescription typeDescription) {
                return isAssignable(typeDescription, this);
            }

            @Override
            public boolean isInstance(Object value) {
                return isAssignableFrom(value.getClass());
            }

            @Override
            public boolean isPrimitive() {
                return false;
            }

            @Override
            public boolean isArray() {
                return false;
            }

            @Override
            public TypeDescription getComponentType() {
                return null;
            }

            @Override
            public boolean represents(Class<?> type) {
                return type.getName().equals(getName());
            }

            @Override
            public String getDescriptor() {
                return "L" + getInternalName() + ";";
            }

            @Override
            public String getCanonicalName() {
                return getName().replace('$', '.');
            }

            @Override
            public String getSimpleName() {
                int simpleNameIndex = getInternalName().lastIndexOf('$');
                simpleNameIndex = simpleNameIndex == -1 ? getInternalName().lastIndexOf('/') : simpleNameIndex;
                return simpleNameIndex == -1 ? getInternalName() : getInternalName().substring(simpleNameIndex + 1);
            }

            @Override
            public StackSize getStackSize() {
                return StackSize.SINGLE;
            }
        }
    }

    /**
     * A type description implementation that represents a loaded type.
     */
    class ForLoadedType extends AbstractTypeDescription {

        /**
         * The loaded type this instance represents.
         */
        private final Class<?> type;

        /**
         * Creates a new immutable type description for a loaded type.
         *
         * @param type The type to be represented by this type description.
         */
        public ForLoadedType(Class<?> type) {
            this.type = type;
        }

        /**
         * Checks if two types are assignable to each other. This check makes use of the fact that two types are loaded and
         * have a {@link ClassLoader} which allows to check a type's assignability in a more efficient manner. However, two
         * {@link Class} instances are considered assignable by this method, even if their loaded versions are not assignable
         * as of class loader conflicts.
         *
         * @param sourceType The type to which another type should be assigned to.
         * @param targetType The type which is to be assigned to another type.
         * @return {@code true} if the source type is assignable from the target type.
         */
        private static boolean isAssignable(Class<?> sourceType, Class<?> targetType) {
            if (sourceType.isAssignableFrom(targetType)) {
                return true;
            } else if (sourceType.isPrimitive() || targetType.isPrimitive()) {
                return false; // Implied by 'sourceType.isAssignableFrom(targetType)'
            } else if (targetType.isArray()) {
                // Checks for 'Object', 'Serializable' and 'Cloneable' are implied by 'sourceType.isAssignableFrom(targetType)'
                return sourceType.isArray() && isAssignable(sourceType.getComponentType(), targetType.getComponentType());
            } else if (sourceType.getClassLoader() != targetType.getClassLoader()) {
                // (1) Both types are equal by their name which means that they represent the same class on the byte code level.
                if (sourceType.getName().equals(targetType.getName())) {
                    return true;
                }
                Class<?> targetTypeSuperType = targetType.getSuperclass();
                if (targetTypeSuperType != null && isAssignable(sourceType, targetTypeSuperType)) {
                    return true;
                }
                // (2) If the target type is an interface, any of this type's interfaces might be assignable to it.
                if (sourceType.isInterface()) {
                    for (Class<?> interfaceType : targetType.getInterfaces()) {
                        if (isAssignable(sourceType, interfaceType)) {
                            return true;
                        }
                    }
                }
                // (3) None of these criteria are true, i.e. the types are not assignable.
                return false;
            } else /* if (sourceType.getClassLoader() == targetType.getClassLoader() // implied by assignable check */ {
                return false; // For equal class loader, the check is implied by 'sourceType.isAssignableFrom(targetType)'
            }
        }

        @Override
        public boolean isInstance(Object value) {
            return type.isInstance(value) || super.isInstance(value); // Consider class loaded by multiple class loaders.
        }

        @Override
        public boolean isAssignableFrom(Class<?> type) {
            return isAssignable(this.type, type);
        }

        @Override
        public boolean isAssignableFrom(TypeDescription typeDescription) {
            return typeDescription.isAssignableTo(type);
        }

        @Override
        public boolean isAssignableTo(Class<?> type) {
            return isAssignable(type, this.type);
        }

        @Override
        public boolean isAssignableTo(TypeDescription typeDescription) {
            return typeDescription.isAssignableFrom(type);
        }

        @Override
        public boolean represents(Class<?> type) {
            return type == this.type || equals(new ForLoadedType(type));
        }

        @Override
        public boolean isInterface() {
            return type.isInterface();
        }

        @Override
        public boolean isArray() {
            return type.isArray();
        }

        @Override
        public TypeDescription getComponentType() {
            Class<?> componentType = type.getComponentType();
            return componentType == null
                    ? null
                    : new TypeDescription.ForLoadedType(componentType);
        }

        @Override
        public boolean isPrimitive() {
            return type.isPrimitive();
        }

        @Override
        public boolean isAnnotation() {
            return type.isAnnotation();
        }

        @Override
        public GenericTypeDescription getSuperTypeGen() {
            return type.getSuperclass() == null
                    ? null
                    : new LazyProjection.OfLoadedSuperType(type);
        }

        @Override
        public GenericTypeList getInterfacesGen() {
            return isArray()
                    ? new GenericTypeList.ForLoadedType(Cloneable.class, Serializable.class)
                    : new GenericTypeList.LazyProjection.OfInterfaces(type);
        }

        @Override
        public TypeDescription getDeclaringType() {
            Class<?> declaringType = type.getDeclaringClass();
            return declaringType == null
                    ? null
                    : new TypeDescription.ForLoadedType(declaringType);
        }

        @Override
        public MethodDescription getEnclosingMethod() {
            Method enclosingMethod = type.getEnclosingMethod();
            Constructor<?> enclosingConstructor = type.getEnclosingConstructor();
            if (enclosingMethod != null) {
                return new MethodDescription.ForLoadedMethod(enclosingMethod);
            } else if (enclosingConstructor != null) {
                return new MethodDescription.ForLoadedConstructor(enclosingConstructor);
            } else {
                return null;
            }
        }

        @Override
        public TypeDescription getEnclosingType() {
            Class<?> enclosingType = type.getEnclosingClass();
            return enclosingType == null
                    ? null
                    : new TypeDescription.ForLoadedType(enclosingType);
        }

        @Override
        public String getSimpleName() {
            return type.getSimpleName();
        }

        @Override
        public String getCanonicalName() {
            return type.getCanonicalName();
        }

        @Override
        public boolean isAnonymousClass() {
            return type.isAnonymousClass();
        }

        @Override
        public boolean isLocalClass() {
            return type.isLocalClass();
        }

        @Override
        public boolean isMemberClass() {
            return type.isMemberClass();
        }

        @Override
        public FieldList getDeclaredFields() {
            return new FieldList.ForLoadedField(type.getDeclaredFields());
        }

        @Override
        public MethodList getDeclaredMethods() {
            return new MethodList.ForLoadedType(type);
        }

        @Override
        public PackageDescription getPackage() {
            Package aPackage = type.getPackage();
            return aPackage == null
                    ? null
                    : new PackageDescription.ForLoadedPackage(aPackage);
        }

        @Override
        public StackSize getStackSize() {
            return StackSize.of(type);
        }

        @Override
        public String getName() {
            return type.getName();
        }

        @Override
        public String getDescriptor() {
            return Type.getDescriptor(type);
        }

        @Override
        public int getModifiers() {
            return type.getModifiers();
        }

        @Override
        public GenericTypeList getTypeVariables() {
            return new GenericTypeList.ForLoadedType(type.getTypeParameters());
        }

        @Override
        public AnnotationList getDeclaredAnnotations() {
            return new AnnotationList.ForLoadedAnnotation(type.getDeclaredAnnotations());
        }

        @Override
        public AnnotationList getInheritedAnnotations() {
            return new AnnotationList.ForLoadedAnnotation(type.getAnnotations());
        }
    }

    /**
     * A projection for an array type based on an existing {@link TypeDescription}.
     */
    class ArrayProjection extends AbstractTypeDescription {

        /**
         * The modifiers of any array type.
         */
        private static final int ARRAY_MODIFIERS = Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_ABSTRACT;

        /**
         * The base component type which is itself not an array.
         */
        private final TypeDescription componentType;

        /**
         * The arity of this array.
         */
        private final int arity;

        /**
         * Crrates a new array projection.
         *
         * @param componentType The base component type of the array which is itself not an array.
         * @param arity         The arity of this array.
         */
        protected ArrayProjection(TypeDescription componentType, int arity) {
            this.componentType = componentType;
            this.arity = arity;
        }

        /**
         * Creates an array projection.
         *
         * @param componentType The component type of the array.
         * @param arity         The arity of this array.
         * @return A projection of the component type as an arity of the given value.
         */
        public static TypeDescription of(TypeDescription componentType, int arity) {
            if (arity < 0) {
                throw new IllegalArgumentException("Arrays cannot have a negative arity");
            }
            while (componentType.isArray()) {
                componentType = componentType.getComponentType();
                arity++;
            }
            return arity == 0
                    ? componentType
                    : new ArrayProjection(componentType, arity);
        }

        /**
         * Checks if two types are assignable to another by first checking the array dimensions and by later
         * checking the component types if the arity matches.
         *
         * @param sourceType The source type to which another type is to be assigned to.
         * @param targetType The target type that is to be assigned to the source type.
         * @return {@code true} if both types are assignable to one another.
         */
        private static boolean isArrayAssignable(TypeDescription sourceType, TypeDescription targetType) {
            int sourceArity = 0, targetArity = 0;
            while (sourceType.isArray()) {
                sourceArity++;
                sourceType = sourceType.getComponentType();
            }
            while (targetType.isArray()) {
                targetArity++;
                targetType = targetType.getComponentType();
            }
            return sourceArity == targetArity && sourceType.isAssignableFrom(targetType);
        }

        @Override
        public boolean isAssignableFrom(Class<?> type) {
            return isAssignableFrom(new ForLoadedType(type));
        }

        @Override
        public boolean isAssignableFrom(TypeDescription typeDescription) {
            return isArrayAssignable(this, typeDescription);
        }

        @Override
        public boolean isAssignableTo(Class<?> type) {
            return isAssignableTo(new ForLoadedType(type));
        }

        @Override
        public boolean isAssignableTo(TypeDescription typeDescription) {
            return typeDescription.represents(Object.class)
                    || typeDescription.represents(Serializable.class)
                    || typeDescription.represents(Cloneable.class)
                    || isArrayAssignable(typeDescription, this);
        }

        @Override
        public boolean represents(Class<?> type) {
            int arity = 0;
            while (type.isArray()) {
                type = type.getComponentType();
                arity++;
            }
            return arity == this.arity && componentType.represents(type);
        }

        @Override
        public boolean isArray() {
            return true;
        }

        @Override
        public TypeDescription getComponentType() {
            return arity == 1
                    ? componentType
                    : new ArrayProjection(componentType, arity - 1);
        }

        @Override
        public boolean isPrimitive() {
            return false;
        }

        @Override
        public GenericTypeDescription getSuperTypeGen() {
            return new ForLoadedType(Object.class);
        }

        @Override
        public GenericTypeList getInterfacesGen() {
            return new GenericTypeList.ForLoadedType(Cloneable.class, Serializable.class);
        }

        @Override
        public MethodDescription getEnclosingMethod() {
            return null;
        }

        @Override
        public TypeDescription getEnclosingType() {
            return null;
        }

        @Override
        public String getSimpleName() {
            StringBuilder stringBuilder = new StringBuilder(componentType.getSimpleName());
            for (int i = 0; i < arity; i++) {
                stringBuilder.append("[]");
            }
            return stringBuilder.toString();
        }

        @Override
        public String getCanonicalName() {
            StringBuilder stringBuilder = new StringBuilder(componentType.getCanonicalName());
            for (int i = 0; i < arity; i++) {
                stringBuilder.append("[]");
            }
            return stringBuilder.toString();
        }

        @Override
        public boolean isAnonymousClass() {
            return false;
        }

        @Override
        public boolean isLocalClass() {
            return false;
        }

        @Override
        public boolean isMemberClass() {
            return false;
        }

        @Override
        public FieldList getDeclaredFields() {
            return new FieldList.Empty();
        }

        @Override
        public MethodList getDeclaredMethods() {
            return new MethodList.Empty();
        }

        @Override
        public StackSize getStackSize() {
            return StackSize.SINGLE;
        }

        @Override
        public AnnotationList getDeclaredAnnotations() {
            return new AnnotationList.Empty();
        }

        @Override
        public AnnotationList getInheritedAnnotations() {
            return new AnnotationList.Empty();
        }

        @Override
        public PackageDescription getPackage() {
            return null;
        }

        @Override
        public String getName() {
            StringBuilder stringBuilder = new StringBuilder();
            for (int i = 0; i < arity; i++) {
                stringBuilder.append('[');
            }
            return stringBuilder.append(componentType.getDescriptor().replace('/', '.')).toString();
        }

        @Override
        public String getDescriptor() {
            StringBuilder stringBuilder = new StringBuilder();
            for (int i = 0; i < arity; i++) {
                stringBuilder.append('[');
            }
            return stringBuilder.append(componentType.getDescriptor()).toString();
        }

        @Override
        public TypeDescription getDeclaringType() {
            return null;
        }

        @Override
        public int getModifiers() {
            return ARRAY_MODIFIERS;
        }

        @Override
        public GenericTypeList getTypeVariables() {
            return new GenericTypeList.Empty();
        }
    }

    /**
     * A latent type description for a type without methods or fields.
     */
    class Latent extends AbstractTypeDescription.OfSimpleType {

        /**
         * The name of the type.
         */
        private final String name;

        /**
         * The modifiers of the type.
         */
        private final int modifiers;

        /**
         * The super type or {@code null} if no such type exists.
         */
        private final GenericTypeDescription superType;

        /**
         * The interfaces that this type implements.
         */
        private final List<? extends GenericTypeDescription> interfaces;

        /**
         * Creates a new latent type.
         *
         * @param name       The name of the type.
         * @param modifiers  The modifiers of the type.
         * @param superType  The super type or {@code null} if no such type exists.
         * @param interfaces The interfaces that this type implements.
         */
        public Latent(String name, int modifiers, GenericTypeDescription superType, List<? extends GenericTypeDescription> interfaces) {
            this.name = name;
            this.modifiers = modifiers;
            this.superType = superType;
            this.interfaces = interfaces;
        }

        @Override
        public GenericTypeDescription getSuperTypeGen() {
            return superType;
        }

        @Override
        public GenericTypeList getInterfacesGen() {
            return new GenericTypeList.Explicit(interfaces);
        }

        @Override
        public MethodDescription getEnclosingMethod() {
            return null;
        }

        @Override
        public TypeDescription getEnclosingType() {
            return null;
        }

        @Override
        public String getCanonicalName() {
            return getName().replace('$', '.');
        }

        @Override
        public boolean isAnonymousClass() {
            return false;
        }

        @Override
        public boolean isLocalClass() {
            return false;
        }

        @Override
        public boolean isMemberClass() {
            return false;
        }

        @Override
        public FieldList getDeclaredFields() {
            return new FieldList.Empty();
        }

        @Override
        public MethodList getDeclaredMethods() {
            return new MethodList.Empty();
        }

        @Override
        public PackageDescription getPackage() {
            String name = getName();
            int index = name.lastIndexOf('.');
            return index == -1
                    ? null
                    : new PackageDescription.Simple(name.substring(0, index));
        }

        @Override
        public AnnotationList getDeclaredAnnotations() {
            return new AnnotationList.Empty();
        }

        @Override
        public TypeDescription getDeclaringType() {
            return null;
        }

        @Override
        public int getModifiers() {
            return modifiers;
        }

        @Override
        public String getName() {
            return name;
        }

        @Override
        public GenericTypeList getTypeVariables() {
            return new GenericTypeList.Empty();
        }
    }

    class ForPackageDescription extends AbstractTypeDescription.OfSimpleType {

        private final PackageDescription packageDescription;

        public ForPackageDescription(PackageDescription packageDescription) {
            this.packageDescription = packageDescription;
        }

        @Override
        public GenericTypeDescription getSuperTypeGen() {
            return TypeDescription.OBJECT;
        }

        @Override
        public GenericTypeList getInterfacesGen() {
            return new GenericTypeList.Empty();
        }

        @Override
        public MethodDescription getEnclosingMethod() {
            return null;
        }

        @Override
        public TypeDescription getEnclosingType() {
            return null;
        }

        @Override
        public boolean isAnonymousClass() {
            return false;
        }

        @Override
        public boolean isLocalClass() {
            return false;
        }

        @Override
        public boolean isMemberClass() {
            return false;
        }

        @Override
        public FieldList getDeclaredFields() {
            return new FieldList.Empty();
        }

        @Override
        public MethodList getDeclaredMethods() {
            return new MethodList.Empty();
        }

        @Override
        public PackageDescription getPackage() {
            return packageDescription;
        }

        @Override
        public AnnotationList getDeclaredAnnotations() {
            return packageDescription.getDeclaredAnnotations();
        }

        @Override
        public TypeDescription getDeclaringType() {
            return null;
        }

        @Override
        public GenericTypeList getTypeVariables() {
            return new GenericTypeList.Empty();
        }

        @Override
        public int getModifiers() {
            return PackageDescription.PACKAGE_MODIFIERS;
        }

        @Override
        public String getName() {
            return packageDescription.getName();
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/description/type/TypeList.java
package net.bytebuddy.description.type;

import net.bytebuddy.description.type.generic.GenericTypeList;
import net.bytebuddy.implementation.bytecode.StackSize;
import net.bytebuddy.matcher.FilterableList;
import org.objectweb.asm.Type;

import java.util.Arrays;
import java.util.List;

/**
 * Implementations represent a list of type descriptions.
 */
public interface TypeList extends FilterableList<TypeDescription, TypeList> {

    /**
     * Returns a list of internal names of all types represented by this list.
     *
     * @return An array of all internal names or {@code null} if the list is empty.
     */
    String[] toInternalNames();

    /**
     * Returns the sum of the size of all types contained in this list.
     *
     * @return The sum of the size of all types contained in this list.
     */
    int getStackSize();

    GenericTypeList asGenericTypes();

    abstract class AbstractBase extends FilterableList.AbstractBase<TypeDescription, TypeList> implements TypeList {

        @Override
        protected TypeList wrap(List<TypeDescription> values) {
            return new Explicit(values);
        }
    }

    /**
     * Implementation of a type list for an array of loaded types.
     */
    class ForLoadedType extends AbstractBase {

        /**
         * The loaded types this type list represents.
         */
        private final List<? extends Class<?>> types;

        /**
         * Creates a new type list for an array of loaded types.
         *
         * @param type The types to be represented by this list.
         */
        public ForLoadedType(Class<?>... type) {
            this(Arrays.asList(type));
        }

        /**
         * Creates a new type list for an array of loaded types.
         *
         * @param types The types to be represented by this list.
         */
        public ForLoadedType(List<? extends Class<?>> types) {
            this.types = types;
        }

        @Override
        public TypeDescription get(int index) {
            return new TypeDescription.ForLoadedType(types.get(index));
        }

        @Override
        public int size() {
            return types.size();
        }

        @Override
        public String[] toInternalNames() {
            String[] internalNames = new String[types.size()];
            int i = 0;
            for (Class<?> type : types) {
                internalNames[i++] = Type.getInternalName(type);
            }
            return internalNames.length == 0 ? null : internalNames;
        }

        @Override
        public int getStackSize() {
            return StackSize.sizeOf(types);
        }

        @Override
        public GenericTypeList asGenericTypes() {
            return new GenericTypeList.ForLoadedType(types);
        }
    }

    /**
     * A wrapper implementation of an explicit list of types.
     */
    class Explicit extends AbstractBase {

        /**
         * The list of type descriptions this list represents.
         */
        private final List<? extends TypeDescription> typeDescriptions;

        /**
         * Creates an immutable wrapper.
         *
         * @param typeDescriptions The list of types to be represented by this wrapper.
         */
        public Explicit(List<? extends TypeDescription> typeDescriptions) {
            this.typeDescriptions = typeDescriptions;
        }

        @Override
        public TypeDescription get(int index) {
            return typeDescriptions.get(index);
        }

        @Override
        public int size() {
            return typeDescriptions.size();
        }

        @Override
        public String[] toInternalNames() {
            String[] internalNames = new String[typeDescriptions.size()];
            int i = 0;
            for (TypeDescription typeDescription : typeDescriptions) {
                internalNames[i++] = typeDescription.getInternalName();
            }
            return internalNames.length == 0 ? null : internalNames;
        }

        @Override
        public int getStackSize() {
            int stackSize = 0;
            for (TypeDescription typeDescription : typeDescriptions) {
                stackSize += typeDescription.getStackSize().getSize();
            }
            return stackSize;
        }

        @Override
        public GenericTypeList asGenericTypes() {
            return new GenericTypeList.Explicit(typeDescriptions);
        }
    }

    /**
     * An implementation of an empty type list.
     */
    class Empty extends FilterableList.Empty<TypeDescription, TypeList> implements TypeList {

        @Override
        public String[] toInternalNames() {
            return null;
        }

        @Override
        public int getStackSize() {
            return 0;
        }

        @Override
        public GenericTypeList asGenericTypes() {
            return new GenericTypeList.Empty();
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/description/type/generic/GenericTypeDescription.java
package net.bytebuddy.description.type.generic;

import net.bytebuddy.description.NamedElement;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.implementation.bytecode.StackSize;
import net.bytebuddy.utility.JavaMethod;
import org.objectweb.asm.signature.SignatureVisitor;

import java.lang.reflect.*;
import java.util.Collections;
import java.util.List;

import static net.bytebuddy.matcher.ElementMatchers.named;

public interface GenericTypeDescription extends NamedElement {

    Sort getSort();

    TypeDescription asRawType();

    GenericTypeList getUpperBounds();

    GenericTypeList getLowerBounds();

    GenericTypeDescription getComponentType();

    GenericTypeList getParameters();

    TypeVariableSource getVariableSource();

    GenericTypeDescription getOwnerType();

    String getSymbol();

    String getTypeName();

    /**
     * Returns the size of the type described by this instance.
     *
     * @return The size of the type described by this instance.
     */
    StackSize getStackSize();

    <T> T accept(Visitor<T> visitor);

    enum Sort {

        RAW,
        GENERIC_ARRAY,
        PARAMETERIZED,
        WILDCARD,
        VARIABLE;

        public static GenericTypeDescription describe(Type type) {
            if (type instanceof Class<?>) {
                return new TypeDescription.ForLoadedType((Class<?>) type);
            } else if (type instanceof GenericArrayType) {
                return new ForGenericArray.OfLoadedType((GenericArrayType) type);
            } else if (type instanceof ParameterizedType) {
                return new ForParameterizedType.OfLoadedType((ParameterizedType) type);
            } else if (type instanceof TypeVariable) {
                return new ForTypeVariable.OfLoadedType((TypeVariable<?>) type);
            } else if (type instanceof WildcardType) {
                return new ForWildcardType.OfLoadedType((WildcardType) type);
            } else {
                throw new IllegalStateException("Unknown type: " + type);
            }
        }

        public boolean isRawType() {
            return this == RAW;
        }

        public boolean isParameterized() {
            return this == PARAMETERIZED;
        }

        public boolean isGenericArray() {
            return this == GENERIC_ARRAY;
        }

        public boolean isWildcard() {
            return this == WILDCARD;
        }

        public boolean isTypeVariable() {
            return this == VARIABLE;
        }
    }

    interface Visitor<T> {

        T onGenericArray(GenericTypeDescription genericTypeDescription);

        T onWildcardType(GenericTypeDescription genericTypeDescription);

        T onParameterizedType(GenericTypeDescription genericTypeDescription);

        T onTypeVariable(GenericTypeDescription genericTypeDescription);

        T onRawType(TypeDescription typeDescription);

        class ForSignatureVisitor implements Visitor<SignatureVisitor> {

            private static final int ONLY_CHARACTER = 0;

            protected final SignatureVisitor signatureVisitor;

            public ForSignatureVisitor(SignatureVisitor signatureVisitor) {
                this.signatureVisitor = signatureVisitor;
            }

            @Override
            public SignatureVisitor onGenericArray(GenericTypeDescription genericTypeDescription) {
                genericTypeDescription.getComponentType().accept(new ForSignatureVisitor(signatureVisitor.visitArrayType()));
                return signatureVisitor;
            }

            @Override
            public SignatureVisitor onWildcardType(GenericTypeDescription genericTypeDescription) {
                throw new IllegalStateException("Unexpected wildcard: " + genericTypeDescription);
            }

            @Override
            public SignatureVisitor onParameterizedType(GenericTypeDescription genericTypeDescription) {
                onOwnableType(genericTypeDescription);
                signatureVisitor.visitEnd();
                return signatureVisitor;
            }

            private void onOwnableType(GenericTypeDescription genericTypeDescription) {
                GenericTypeDescription ownerType = genericTypeDescription.getOwnerType();
                if (ownerType != null) {
                    onOwnableType(ownerType);
                    signatureVisitor.visitInnerClassType(genericTypeDescription.asRawType().getSimpleName());
                } else {
                    signatureVisitor.visitClassType(genericTypeDescription.asRawType().getInternalName());
                }
                for (GenericTypeDescription upperBound : genericTypeDescription.getParameters()) {
                    upperBound.accept(new OfParameter(signatureVisitor));
                }
            }

            @Override
            public SignatureVisitor onTypeVariable(GenericTypeDescription genericTypeDescription) {
                signatureVisitor.visitTypeVariable(genericTypeDescription.getSymbol());
                return signatureVisitor;
            }

            @Override
            public SignatureVisitor onRawType(TypeDescription typeDescription) {
                if (typeDescription.isPrimitive()) {
                    signatureVisitor.visitBaseType(typeDescription.getDescriptor().charAt(ONLY_CHARACTER));
                } else {
                    signatureVisitor.visitClassType(typeDescription.getInternalName());
                    signatureVisitor.visitEnd();
                }
                return signatureVisitor;
            }

            protected static class OfParameter extends ForSignatureVisitor {

                protected OfParameter(SignatureVisitor signatureVisitor) {
                    super(signatureVisitor);
                }

                @Override
                public SignatureVisitor onWildcardType(GenericTypeDescription genericTypeDescription) {
                    GenericTypeList upperBounds = genericTypeDescription.getUpperBounds();
                    GenericTypeList lowerBounds = genericTypeDescription.getLowerBounds();
                    if (upperBounds.getOnly().asRawType().represents(Object.class) && lowerBounds.isEmpty()) {
                        signatureVisitor.visitTypeArgument();
                    } else if (!lowerBounds.isEmpty() /* && upperBounds.isEmpty() */) {
                        lowerBounds.getOnly().accept(new ForSignatureVisitor(signatureVisitor.visitTypeArgument(SignatureVisitor.EXTENDS)));
                    } else /* if (!upperBounds.isEmpty() && lowerBounds.isEmpty()) */ {
                        upperBounds.getOnly().accept(new ForSignatureVisitor(signatureVisitor.visitTypeArgument(SignatureVisitor.SUPER)));
                    }
                    return signatureVisitor;
                }

                @Override
                public SignatureVisitor onGenericArray(GenericTypeDescription genericTypeDescription) {
                    genericTypeDescription.accept(new ForSignatureVisitor(signatureVisitor.visitTypeArgument(SignatureVisitor.INSTANCEOF)));
                    return signatureVisitor;
                }

                @Override
                public SignatureVisitor onParameterizedType(GenericTypeDescription genericTypeDescription) {
                    genericTypeDescription.accept(new ForSignatureVisitor(signatureVisitor.visitTypeArgument(SignatureVisitor.INSTANCEOF)));
                    return signatureVisitor;
                }

                @Override
                public SignatureVisitor onTypeVariable(GenericTypeDescription genericTypeDescription) {
                    genericTypeDescription.accept(new ForSignatureVisitor(signatureVisitor.visitTypeArgument(SignatureVisitor.INSTANCEOF)));
                    return signatureVisitor;
                }

                @Override
                public SignatureVisitor onRawType(TypeDescription typeDescription) {
                    typeDescription.accept(new ForSignatureVisitor(signatureVisitor.visitTypeArgument(SignatureVisitor.INSTANCEOF)));
                    return signatureVisitor;
                }
            }
        }
    }

    abstract class ForGenericArray implements GenericTypeDescription {

        @Override
        public Sort getSort() {
            return Sort.GENERIC_ARRAY;
        }

        @Override
        public TypeDescription asRawType() {
            return TypeDescription.ArrayProjection.of(getComponentType().asRawType(), 1);
        }

        @Override
        public GenericTypeList getUpperBounds() {
            return new GenericTypeList.Empty();
        }

        @Override
        public GenericTypeList getLowerBounds() {
            return new GenericTypeList.Empty();
        }

        @Override
        public TypeVariableSource getVariableSource() {
            return null;
        }

        @Override
        public GenericTypeList getParameters() {
            return new GenericTypeList.Empty();
        }

        @Override
        public GenericTypeDescription getOwnerType() {
            return null;
        }

        @Override
        public String getSymbol() {
            return null;
        }

        @Override
        public String getTypeName() {
            return toString();
        }

        @Override
        public String getSourceCodeName() {
            return toString();
        }

        @Override
        public <T> T accept(Visitor<T> visitor) {
            return visitor.onGenericArray(this);
        }

        @Override
        public StackSize getStackSize() {
            return StackSize.SINGLE;
        }

        @Override
        public boolean equals(Object other) {
            if (!(other instanceof GenericTypeDescription)) return false;
            GenericTypeDescription genericTypeDescription = (GenericTypeDescription) other;
            return genericTypeDescription.getSort().isGenericArray() && getComponentType().equals(genericTypeDescription.getComponentType());
        }

        @Override
        public int hashCode() {
            return getComponentType().hashCode();
        }

        @Override
        public String toString() {
            return getComponentType().getTypeName() + "[]";
        }

        public static class OfLoadedType extends ForGenericArray {

            private final GenericArrayType genericArrayType;

            public OfLoadedType(GenericArrayType genericArrayType) {
                this.genericArrayType = genericArrayType;
            }

            @Override
            public GenericTypeDescription getComponentType() {
                return Sort.describe(genericArrayType.getGenericComponentType());
            }
        }

        public static class Latent extends ForGenericArray {

            public static GenericTypeDescription of(GenericTypeDescription componentType, int arity) {
                if (arity < 0) {
                    throw new IllegalArgumentException("Arity cannot be negative");
                }
                while (componentType.getSort().isGenericArray()) {
                    arity++;
                    componentType = componentType.getComponentType();
                }
                return arity == 0
                        ? componentType
                        : new Latent(componentType, arity);
            }

            private final GenericTypeDescription componentType;

            private final int arity;

            protected Latent(GenericTypeDescription componentType, int arity) {
                this.componentType = componentType;
                this.arity = arity;
            }

            @Override
            public GenericTypeDescription getComponentType() {
                return arity == 1
                        ? componentType
                        : new Latent(componentType, arity - 1);
            }
        }
    }

    abstract class ForWildcardType implements GenericTypeDescription {

        public static final String SYMBOL = "?";

        @Override
        public Sort getSort() {
            return Sort.WILDCARD;
        }

        @Override
        public TypeDescription asRawType() {
            throw new IllegalStateException("A wildcard cannot present an erasable type: " + this);
        }

        @Override
        public GenericTypeDescription getComponentType() {
            return null;
        }

        @Override
        public TypeVariableSource getVariableSource() {
            return null;
        }

        @Override
        public GenericTypeList getParameters() {
            return new GenericTypeList.Empty();
        }

        @Override
        public GenericTypeDescription getOwnerType() {
            return null;
        }

        @Override
        public String getSymbol() {
            return null;
        }

        @Override
        public String getTypeName() {
            return toString();
        }

        @Override
        public String getSourceCodeName() {
            return toString();
        }

        @Override
        public <T> T accept(Visitor<T> visitor) {
            return visitor.onWildcardType(this);
        }

        @Override
        public StackSize getStackSize() {
            return StackSize.SINGLE;
        }

        @Override
        public int hashCode() {
            int lowerHash = 1, upperHash = 1;
            for (GenericTypeDescription genericTypeDescription : getLowerBounds()) {
                lowerHash = 31 * lowerHash + genericTypeDescription.hashCode();
            }
            for (GenericTypeDescription genericTypeDescription : getUpperBounds()) {
                upperHash = 31 * upperHash + genericTypeDescription.hashCode();
            }
            return lowerHash ^ upperHash;
        }

        @Override
        public boolean equals(Object other) {
            if (!(other instanceof GenericTypeDescription)) return false;
            GenericTypeDescription genericTypeDescription = (GenericTypeDescription) other;
            return genericTypeDescription.getSort().isWildcard()
                    && getUpperBounds().equals(genericTypeDescription.getUpperBounds())
                    && getLowerBounds().equals(genericTypeDescription.getLowerBounds());
        }

        @Override
        public String toString() {
            StringBuilder stringBuilder = new StringBuilder(SYMBOL);
            GenericTypeList bounds = getLowerBounds();
            if (!bounds.isEmpty()) {
                if (bounds.size() == 1 && bounds.get(0).equals(TypeDescription.OBJECT)) {
                    return SYMBOL;
                }
                stringBuilder.append(" super ");
            } else {
                bounds = getUpperBounds();
                if (bounds.isEmpty()) {
                    return SYMBOL;
                }
                stringBuilder.append(" extends ");
            }
            boolean multiple = false;
            for (GenericTypeDescription genericTypeDescription : bounds) {
                if (multiple) {
                    stringBuilder.append(" & ");
                }
                stringBuilder.append(genericTypeDescription.getTypeName());
                multiple = true;
            }
            return stringBuilder.toString();
        }

        public static class OfLoadedType extends ForWildcardType {

            private final WildcardType wildcardType;

            public OfLoadedType(WildcardType wildcardType) {
                this.wildcardType = wildcardType;
            }

            @Override
            public GenericTypeList getLowerBounds() {
                return new GenericTypeList.ForLoadedType(wildcardType.getLowerBounds());
            }

            @Override
            public GenericTypeList getUpperBounds() {
                return new GenericTypeList.ForLoadedType(wildcardType.getUpperBounds());
            }
        }

        public static class Latent extends ForWildcardType {

            public static GenericTypeDescription unbounded() {
                return new Latent(Collections.singletonList(TypeDescription.OBJECT), Collections.<GenericTypeDescription>emptyList());
            }

            public static GenericTypeDescription boundedAbove(GenericTypeDescription upperBound) {
                return new Latent(Collections.singletonList(upperBound), Collections.<GenericTypeDescription>emptyList());
            }

            public static GenericTypeDescription boundedBelow(GenericTypeDescription lowerBound) {
                return new Latent(Collections.singletonList(TypeDescription.OBJECT), Collections.singletonList(lowerBound));
            }

            private final List<? extends GenericTypeDescription> upperBounds;

            private final List<? extends GenericTypeDescription> lowerBounds;

            protected Latent(List<? extends GenericTypeDescription> upperBounds, List<? extends GenericTypeDescription> lowerBounds) {
                this.upperBounds = upperBounds;
                this.lowerBounds = lowerBounds;
            }

            @Override
            public GenericTypeList getUpperBounds() {
                return new GenericTypeList.Explicit(upperBounds);
            }

            @Override
            public GenericTypeList getLowerBounds() {
                return new GenericTypeList.Explicit(lowerBounds);
            }
        }
    }

    abstract class ForParameterizedType implements GenericTypeDescription {

        @Override
        public Sort getSort() {
            return Sort.PARAMETERIZED;
        }

        @Override
        public GenericTypeList getUpperBounds() {
            return new GenericTypeList.Empty();
        }

        @Override
        public GenericTypeList getLowerBounds() {
            return new GenericTypeList.Empty();
        }

        @Override
        public GenericTypeDescription getComponentType() {
            return null;
        }

        @Override
        public TypeVariableSource getVariableSource() {
            return null;
        }

        @Override
        public String getTypeName() {
            return toString();
        }

        @Override
        public String getSymbol() {
            return null;
        }

        @Override
        public String getSourceCodeName() {
            return toString();
        }

        @Override
        public <T> T accept(Visitor<T> visitor) {
            return visitor.onParameterizedType(this);
        }

        @Override
        public StackSize getStackSize() {
            return StackSize.SINGLE;
        }

        @Override
        public int hashCode() {
            int result = 1;
            for (GenericTypeDescription genericTypeDescription : getLowerBounds()) {
                result = 31 * result + genericTypeDescription.hashCode();
            }
            GenericTypeDescription ownerType = getOwnerType();
            return result ^ (ownerType == null
                    ? asRawType().hashCode()
                    : ownerType.hashCode());
        }

        @Override
        public boolean equals(Object other) {
            if (!(other instanceof GenericTypeDescription)) return false;
            GenericTypeDescription genericTypeDescription = (GenericTypeDescription) other;
            if (!genericTypeDescription.getSort().isParameterized()) return false;
            GenericTypeDescription ownerType = getOwnerType(), otherOwnerType = genericTypeDescription.getOwnerType();
            return asRawType().equals(genericTypeDescription.asRawType())
                    && !(ownerType == null && otherOwnerType != null) && !(ownerType != null && !ownerType.equals(otherOwnerType))
                    && getParameters().equals(genericTypeDescription.getParameters());

        }

        @Override
        public String toString() {
            StringBuilder stringBuilder = new StringBuilder();
            GenericTypeDescription ownerType = getOwnerType();
            if (ownerType != null) {
                stringBuilder.append(ownerType.getTypeName());
                stringBuilder.append(".");
                stringBuilder.append(ownerType.getSort().isParameterized()
                        ? asRawType().getName().replace(ownerType.asRawType().getName() + "$", "")
                        : asRawType().getName());
            } else {
                stringBuilder.append(asRawType().getName());
            }
            GenericTypeList actualTypeArguments = getParameters();
            if (!actualTypeArguments.isEmpty()) {
                stringBuilder.append("<");
                boolean multiple = false;
                for (GenericTypeDescription genericTypeDescription : actualTypeArguments) {
                    if (multiple) {
                        stringBuilder.append(", ");
                    }
                    stringBuilder.append(genericTypeDescription.getTypeName());
                    multiple = true;
                }
                stringBuilder.append(">");
            }
            return stringBuilder.toString();
        }

        public static class OfLoadedType extends ForParameterizedType {

            private final ParameterizedType parameterizedType;

            public OfLoadedType(ParameterizedType parameterizedType) {
                this.parameterizedType = parameterizedType;
            }

            @Override
            public GenericTypeList getParameters() {
                return new GenericTypeList.ForLoadedType(parameterizedType.getActualTypeArguments());
            }

            @Override
            public GenericTypeDescription getOwnerType() {
                Type ownerType = parameterizedType.getOwnerType();
                return ownerType == null
                        ? null
                        : Sort.describe(ownerType);
            }

            @Override
            public TypeDescription asRawType() {
                return new TypeDescription.ForLoadedType((Class<?>) parameterizedType.getRawType());
            }
        }

        public static class Latent extends ForParameterizedType {

            private final TypeDescription rawType;

            private final List<? extends GenericTypeDescription> parameters;

            private final GenericTypeDescription ownerType;

            public Latent(TypeDescription rawType, List<? extends GenericTypeDescription> parameters, GenericTypeDescription ownerType) {
                this.rawType = rawType;
                this.parameters = parameters;
                this.ownerType = ownerType;
            }

            @Override
            public TypeDescription asRawType() {
                return rawType;
            }

            @Override
            public GenericTypeList getParameters() {
                return new GenericTypeList.Explicit(parameters);
            }

            @Override
            public GenericTypeDescription getOwnerType() {
                return ownerType;
            }
        }
    }

    abstract class ForTypeVariable implements GenericTypeDescription {

        @Override
        public Sort getSort() {
            return Sort.VARIABLE;
        }

        @Override
        public TypeDescription asRawType() {
            GenericTypeList upperBounds = getUpperBounds();
            return upperBounds.isEmpty()
                    ? TypeDescription.OBJECT
                    : upperBounds.get(0).asRawType();
        }

        @Override
        public GenericTypeDescription getComponentType() {
            return null;
        }

        @Override
        public GenericTypeList getParameters() {
            return new GenericTypeList.Empty();
        }

        @Override
        public GenericTypeList getLowerBounds() {
            return new GenericTypeList.Empty();
        }

        @Override
        public GenericTypeDescription getOwnerType() {
            return null;
        }

        @Override
        public String getTypeName() {
            return toString();
        }

        @Override
        public String getSourceCodeName() {
            return getSymbol();
        }

        @Override
        public <T> T accept(Visitor<T> visitor) {
            return visitor.onTypeVariable(this);
        }

        @Override
        public StackSize getStackSize() {
            return StackSize.SINGLE;
        }

        @Override
        public int hashCode() {
            return getVariableSource().hashCode() ^ getSymbol().hashCode();
        }

        @Override
        public boolean equals(Object other) {
            if (!(other instanceof GenericTypeDescription)) return false;
            GenericTypeDescription genericTypeDescription = (GenericTypeDescription) other;
            return genericTypeDescription.getSort().isTypeVariable()
                    && genericTypeDescription.getSymbol().equals(genericTypeDescription.getSymbol())
                    && genericTypeDescription.getVariableSource().equals(genericTypeDescription.getVariableSource());
        }

        @Override
        public String toString() {
            return getSymbol();
        }

        public static class OfLoadedType extends ForTypeVariable {

            private final TypeVariable<?> typeVariable;

            public OfLoadedType(TypeVariable<?> typeVariable) {
                this.typeVariable = typeVariable;
            }

            @Override
            public TypeVariableSource getVariableSource() {
                GenericDeclaration genericDeclaration = typeVariable.getGenericDeclaration();
                if (genericDeclaration instanceof Class) {
                    return new TypeDescription.ForLoadedType((Class<?>) genericDeclaration);
                } else if (genericDeclaration instanceof Method) {
                    return new MethodDescription.ForLoadedMethod((Method) genericDeclaration);
                } else if (genericDeclaration instanceof Constructor) {
                    return new MethodDescription.ForLoadedConstructor((Constructor<?>) genericDeclaration);
                } else {
                    throw new IllegalStateException("Unknown declaration: " + genericDeclaration);
                }
            }

            @Override
            public GenericTypeList getUpperBounds() {
                return new GenericTypeList.ForLoadedType(typeVariable.getBounds());
            }

            @Override
            public String getSymbol() {
                return typeVariable.getName();
            }
        }

        public static class Latent extends ForTypeVariable {

            private final List<? extends GenericTypeDescription> bounds;

            private final TypeVariableSource typeVariableSource;

            private final String symbol;

            public static GenericTypeDescription of(List<? extends GenericTypeDescription> bounds, TypeVariableSource typeVariableSource, String symbol) {
                if (bounds.isEmpty()) {
                    bounds = Collections.singletonList(TypeDescription.OBJECT);
                } // TODO: Add validation
                return new Latent(bounds, typeVariableSource, symbol);
            }

            public Latent(List<? extends GenericTypeDescription> bounds, TypeVariableSource typeVariableSource, String symbol) {
                this.bounds = bounds;
                this.typeVariableSource = typeVariableSource;
                this.symbol = symbol;
            }

            @Override
            public GenericTypeList getUpperBounds() {
                return new GenericTypeList.Explicit(bounds);
            }

            @Override
            public TypeVariableSource getVariableSource() {
                return typeVariableSource;
            }

            @Override
            public String getSymbol() {
                return symbol;
            }
        }
    }

    abstract class LazyProjection implements GenericTypeDescription {

        protected abstract GenericTypeDescription resolve();

        @Override
        public Sort getSort() {
            return resolve().getSort();
        }

        @Override
        public GenericTypeList getUpperBounds() {
            return resolve().getUpperBounds();
        }

        @Override
        public GenericTypeList getLowerBounds() {
            return resolve().getLowerBounds();
        }

        @Override
        public GenericTypeDescription getComponentType() {
            return resolve().getComponentType();
        }

        @Override
        public GenericTypeList getParameters() {
            return resolve().getParameters();
        }

        @Override
        public TypeVariableSource getVariableSource() {
            return resolve().getVariableSource();
        }

        @Override
        public GenericTypeDescription getOwnerType() {
            return resolve().getOwnerType();
        }

        @Override
        public String getTypeName() {
            return resolve().getTypeName();
        }

        @Override
        public String getSymbol() {
            return resolve().getSymbol();
        }

        @Override
        public String getSourceCodeName() {
            return resolve().getSourceCodeName();
        }

        @Override
        public <T> T accept(Visitor<T> visitor) {
            return resolve().accept(visitor);
        }

        @Override
        public StackSize getStackSize() {
            return asRawType().getStackSize();
        }

        @Override
        public int hashCode() {
            return resolve().hashCode();
        }

        @Override
        public boolean equals(Object other) {
            return resolve().equals(other);
        }

        @Override
        public String toString() {
            return resolve().toString();
        }

        public static class OfLoadedSuperType extends LazyProjection {

            private final Class<?> type;

            public OfLoadedSuperType(Class<?> type) {
                this.type = type;
            }

            @Override
            protected GenericTypeDescription resolve() {
                return Sort.describe(type.getGenericSuperclass());
            }

            @Override
            public TypeDescription asRawType() {
                return new TypeDescription.ForLoadedType(type.getSuperclass());
            }
        }

        public static class OfLoadedReturnType extends LazyProjection {

            private final Method method;

            public OfLoadedReturnType(Method method) {
                this.method = method;
            }

            @Override
            protected GenericTypeDescription resolve() {
                return Sort.describe(method.getGenericReturnType());
            }

            @Override
            public TypeDescription asRawType() {
                return new TypeDescription.ForLoadedType(method.getReturnType());
            }
        }

        public static class OfLoadedFieldType extends LazyProjection {

            private final Field field;

            public OfLoadedFieldType(Field field) {
                this.field = field;
            }

            @Override
            protected GenericTypeDescription resolve() {
                return Sort.describe(field.getGenericType());
            }

            @Override
            public TypeDescription asRawType() {
                return new TypeDescription.ForLoadedType(field.getType());
            }
        }

        public static class OfLoadedParameter extends LazyProjection {

            protected static final JavaMethod GET_TYPE;

            protected static final JavaMethod GET_GENERIC_TYPE;

            static {
                JavaMethod getType, getGenericType;
                try {
                    Class<?> parameterType = Class.forName("java.lang.reflect.Parameter");
                    getType = new JavaMethod.ForLoadedMethod(parameterType.getDeclaredMethod("getType"));
                    getGenericType = new JavaMethod.ForLoadedMethod(parameterType.getDeclaredMethod("getParameterizedType"));
                } catch (Exception ignored) {
                    getType = JavaMethod.ForUnavailableMethod.INSTANCE;
                    getGenericType = JavaMethod.ForUnavailableMethod.INSTANCE;
                }
                GET_TYPE = getType;
                GET_GENERIC_TYPE = getGenericType;
            }

            private final Object parameter;

            public OfLoadedParameter(Object parameter) {
                this.parameter = parameter;
            }

            @Override
            protected GenericTypeDescription resolve() {
                return Sort.describe((Type) GET_GENERIC_TYPE.invoke(parameter));
            }

            @Override
            public TypeDescription asRawType() {
                return new TypeDescription.ForLoadedType((Class<?>) GET_TYPE.invoke(parameter));
            }
        }

        public static class OfLegacyVmConstructorParameter extends LazyProjection {

            private final Constructor<?> constructor;

            private final int index;

            private final Class<?> rawType;

            public OfLegacyVmConstructorParameter(Constructor<?> constructor, int index, Class<?> rawType) {
                this.constructor = constructor;
                this.index = index;
                this.rawType = rawType;
            }

            @Override
            protected GenericTypeDescription resolve() {
                return Sort.describe(constructor.getGenericParameterTypes()[index]);
            }

            @Override
            public TypeDescription asRawType() {
                return new TypeDescription.ForLoadedType(rawType);
            }
        }

        public static class OfLegacyVmMethodParameter extends LazyProjection {

            private final Method method;

            private final int index;

            private final Class<?> rawType;

            public OfLegacyVmMethodParameter(Method method, int index, Class<?> rawType) {
                this.method = method;
                this.index = index;
                this.rawType = rawType;
            }

            @Override
            protected GenericTypeDescription resolve() {
                return Sort.describe(method.getGenericParameterTypes()[index]);
            }

            @Override
            public TypeDescription asRawType() {
                return new TypeDescription.ForLoadedType(rawType);
            }
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/description/type/generic/GenericTypeList.java
package net.bytebuddy.description.type.generic;

import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.TypeList;
import net.bytebuddy.matcher.FilterableList;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public interface GenericTypeList extends FilterableList<GenericTypeDescription, GenericTypeList> {

    TypeList asRawTypes();

    /**
     * Returns the sum of the size of all types contained in this list.
     *
     * @return The sum of the size of all types contained in this list.
     */
    int getStackSize();

    abstract class AbstractBase extends FilterableList.AbstractBase<GenericTypeDescription, GenericTypeList> implements GenericTypeList {

        @Override
        protected GenericTypeList wrap(List<GenericTypeDescription> values) {
            return new Explicit(values);
        }

        @Override
        public int getStackSize() {
            int stackSize = 0;
            for (GenericTypeDescription genericTypeDescription : this) {
                stackSize += genericTypeDescription.getStackSize().getSize();
            }
            return stackSize;
        }
    }

    class Explicit extends AbstractBase {

        private final List<? extends GenericTypeDescription> genericTypes;

        public Explicit(List<? extends GenericTypeDescription> genericTypes) {
            this.genericTypes = genericTypes;
        }

        @Override
        public GenericTypeDescription get(int index) {
            return genericTypes.get(index);
        }

        @Override
        public int size() {
            return genericTypes.size();
        }

        @Override
        public TypeList asRawTypes() {
            List<TypeDescription> typeDescriptions = new ArrayList<TypeDescription>(genericTypes.size());
            for (GenericTypeDescription genericTypeDescription : genericTypes) {
                typeDescriptions.add(genericTypeDescription.asRawType());
            }
            return new TypeList.Explicit(typeDescriptions);
        }
    }

    class ForLoadedType extends AbstractBase {

        private final List<? extends Type> types;

        public ForLoadedType(Type... type) {
            this(Arrays.asList(type));
        }

        public ForLoadedType(List<? extends Type> types) {
            this.types = types;
        }

        @Override
        public GenericTypeDescription get(int index) {
            return GenericTypeDescription.Sort.describe(types.get(index));
        }

        @Override
        public int size() {
            return types.size();
        }

        @Override
        public TypeList asRawTypes() {
            List<TypeDescription> typeDescriptions = new ArrayList<TypeDescription>(types.size());
            for (GenericTypeDescription genericTypeDescription : this) {
                typeDescriptions.add(genericTypeDescription.asRawType());
            }
            return new TypeList.Explicit(typeDescriptions);
        }
    }

    class Empty extends FilterableList.Empty<GenericTypeDescription, GenericTypeList> implements GenericTypeList {

        @Override
        public TypeList asRawTypes() {
            return new TypeList.Empty();
        }

        @Override
        public int getStackSize() {
            return 0;
        }
    }

    abstract class LazyProjection extends AbstractBase {

        public static class OfInterfaces extends LazyProjection {

            private final Class<?> type;

            public OfInterfaces(Class<?> type) {
                this.type = type;
            }

            @Override
            public GenericTypeDescription get(int index) {
                return GenericTypeDescription.Sort.describe(type.getGenericInterfaces()[index]);
            }

            @Override
            public int size() {
                return type.getInterfaces().length;
            }

            @Override
            public TypeList asRawTypes() {
                return new TypeList.ForLoadedType(type.getInterfaces());
            }
        }

        public static class OfConstructorExceptionTypes extends LazyProjection {

            private final Constructor<?> constructor;

            public OfConstructorExceptionTypes(Constructor<?> constructor) {
                this.constructor = constructor;
            }

            @Override
            public GenericTypeDescription get(int index) {
                return GenericTypeDescription.Sort.describe(constructor.getGenericExceptionTypes()[index]);
            }

            @Override
            public int size() {
                return constructor.getExceptionTypes().length;
            }

            @Override
            public TypeList asRawTypes() {
                return new TypeList.ForLoadedType(constructor.getExceptionTypes());
            }
        }

        public static class OfMethodExceptionTypes extends LazyProjection {

            private final Method method;

            public OfMethodExceptionTypes(Method method) {
                this.method = method;
            }

            @Override
            public GenericTypeDescription get(int index) {
                return GenericTypeDescription.Sort.describe(method.getGenericExceptionTypes()[index]);
            }

            @Override
            public int size() {
                return method.getExceptionTypes().length;
            }

            @Override
            public TypeList asRawTypes() {
                return new TypeList.ForLoadedType(method.getExceptionTypes());
            }
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/dynamic/DynamicType.java
package net.bytebuddy.dynamic;

import net.bytebuddy.ClassFileVersion;
import net.bytebuddy.NamingStrategy;
import net.bytebuddy.asm.ClassVisitorWrapper;
import net.bytebuddy.description.annotation.AnnotationDescription;
import net.bytebuddy.description.annotation.AnnotationList;
import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.modifier.ModifierContributor;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.TypeList;
import net.bytebuddy.dynamic.loading.ClassLoadingStrategy;
import net.bytebuddy.dynamic.scaffold.*;
import net.bytebuddy.implementation.Implementation;
import net.bytebuddy.implementation.LoadedTypeInitializer;
import net.bytebuddy.implementation.attribute.FieldAttributeAppender;
import net.bytebuddy.implementation.attribute.MethodAttributeAppender;
import net.bytebuddy.implementation.attribute.TypeAttributeAppender;
import net.bytebuddy.implementation.auxiliary.AuxiliaryType;
import net.bytebuddy.matcher.ElementMatcher;
import net.bytebuddy.matcher.ElementMatchers;
import net.bytebuddy.matcher.LatentMethodMatcher;
import org.objectweb.asm.Opcodes;

import java.io.*;
import java.lang.annotation.Annotation;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.*;
import java.util.jar.JarEntry;
import java.util.jar.JarInputStream;
import java.util.jar.JarOutputStream;
import java.util.jar.Manifest;
import java.util.logging.Logger;

import static net.bytebuddy.matcher.ElementMatchers.*;
import static net.bytebuddy.utility.ByteBuddyCommons.*;

/**
 * A dynamic type that is created at runtime, usually as the result of applying a
 * {@link net.bytebuddy.dynamic.DynamicType.Builder} or as the result of an
 * {@link net.bytebuddy.implementation.auxiliary.AuxiliaryType}.
 * <p>&nbsp;</p>
 * Note that the {@link TypeDescription}s will represent their
 * unloaded forms and therefore differ from the loaded types, especially with regards to annotations.
 */
public interface DynamicType {

    /**
     * <p>
     * Returns a description of this dynamic type.
     * </p>
     * <p>
     * <b>Note</b>: This description will most likely differ from the binary representation of this type. Normally,
     * annotations and intercepted methods are not added to this type description.
     * </p>
     *
     * @return A description of this dynamic type.
     */
    TypeDescription getTypeDescription();

    /**
     * Returns a byte array representing this dynamic type. This byte array might be reused by this dynamic type and
     * must therefore not be altered.
     *
     * @return A byte array of the type's binary representation.
     */
    byte[] getBytes();

    /**
     * <p>
     * Returns a map of all auxiliary types that are required for making use of the main type.
     * </p>
     * <p>
     * <b>Note</b>: The type descriptions will most likely differ from the binary representation of this type.
     * Normally, annotations and intercepted methods are not added to the type descriptions of auxiliary types.
     * </p>
     *
     * @return A map of all auxiliary types by their descriptions to their binary representation.
     */
    Map<TypeDescription, byte[]> getRawAuxiliaryTypes();

    /**
     * Returns all types that are implied by this dynamic type.
     *
     * @return A mapping from all type descriptions, the actual type and its auxiliary types to their binary
     * representation
     */
    Map<TypeDescription, byte[]> getAllTypes();

    /**
     * <p>
     * Returns a map of all loaded type initializers for the main type and all auxiliary types, if any.
     * </p>
     * <p>
     * <b>Note</b>: The type descriptions will most likely differ from the binary representation of this type.
     * Normally, annotations and intercepted methods are not added to the type descriptions of auxiliary types.
     * </p>
     *
     * @return A mapping of all types' descriptions to their loaded type initializers.
     */
    Map<TypeDescription, LoadedTypeInitializer> getLoadedTypeInitializers();

    /**
     * Checks if a dynamic type requires some form of explicit type initialization, either for itself or for one
     * of its auxiliary types, if any. This is the case when this dynamic type was defined to delegate method calls
     * to a specific instance which is stored in a field of the created type. If this class serialized, it could not
     * be used without its loaded type initializers since the field value represents a specific runtime context.
     *
     * @return {@code true} if this type requires explicit type initialization.
     */
    boolean hasAliveLoadedTypeInitializers();

    /**
     * <p>
     * Saves a dynamic type in a given folder using the Java class file format while respecting the naming conventions
     * for saving compiled Java classes. All auxiliary types, if any, are saved in the same directory. The resulting
     * folder structure will resemble the structure that is required for Java run times, i.e. each folder representing
     * a segment of the package name. If the specified {@code folder} does not yet exist, it is created during the
     * call of this method.
     * </p>
     * <p>
     * <b>Note</b>: The type descriptions will most likely differ from the binary representation of this type.
     * Normally, annotations and intercepted methods are not added to the type descriptions of auxiliary types.
     * </p>
     *
     * @param folder The base target folder for storing this dynamic type and its auxiliary types, if any.
     * @return A map of type descriptions pointing to files with their stored binary representations within {@code folder}.
     * @throws IOException Thrown if the underlying file operations cause an {@code IOException}.
     */
    Map<TypeDescription, File> saveIn(File folder) throws IOException;

    /**
     * Injects the types of this dynamic type into a given <i>jar</i> file. Any pre-existent type with the same name
     * is overridden during injection. The {@code target} file's folder must exist prior to calling this method. The
     * file itself is overwritten or created depending on its prior existence.
     *
     * @param sourceJar The original jar file.
     * @param targetJar The {@code source} jar file with the injected contents.
     * @return The {@code target} jar file.
     * @throws IOException If an IO exception occurs while injecting from the source into the target.
     */
    File inject(File sourceJar, File targetJar) throws IOException;

    /**
     * Injects the types of this dynamic type into a given <i>jar</i> file. Any pre-existent type with the same name
     * is overridden during injection.
     *
     * @param jar The jar file to replace with an injected version.
     * @return The {@code jar} file.
     * @throws IOException If an IO exception occurs while injecting into the jar.
     */
    File inject(File jar) throws IOException;

    /**
     * Saves the contents of this dynamic type inside a <i>jar</i> file. The folder of the given {@code file} must
     * exist prior to calling this method.
     *
     * @param file     The target file to which the <i>jar</i> is written to.
     * @param manifest The manifest of the created <i>jar</i>.
     * @return The given {@code file}.
     * @throws IOException If an IO exception occurs while writing the file.
     */
    File toJar(File file, Manifest manifest) throws IOException;

    /**
     * A builder for defining a dynamic type. Implementations of such builders are fully immutable and return
     * modified instances.
     *
     * @param <T> The most specific known loaded type that is implemented by the created dynamic type, usually the
     *            type itself, an interface or the direct super class.
     */
    interface Builder<T> {

        /**
         * Defines a class file format version for this builder for which the dynamic types should be created.
         *
         * @param classFileVersion The class format version for the dynamic type to implement.
         * @return A builder that writes its classes in a given class format version.
         */
        Builder<T> classFileVersion(ClassFileVersion classFileVersion);

        /**
         * Adds the given interfaces to be implemented by the created type.
         *
         * @param interfaceType The interfaces to implement.
         * @return A builder which will create a dynamic type that implements the given interfaces.
         */
        OptionalMatchedMethodInterception<T> implement(Class<?>... interfaceType);

        /**
         * Adds the given interfaces to be implemented by the created type.
         *
         * @param interfaceTypes The interfaces to implement.
         * @return A builder which will create a dynamic type that implements the given interfaces.
         */
        OptionalMatchedMethodInterception<T> implement(Iterable<? extends Class<?>> interfaceTypes);

        /**
         * Adds the given interfaces to be implemented by the created type.
         *
         * @param interfaceType A description of the interfaces to implement.
         * @return A builder which will create a dynamic type that implements the given interfaces.
         */
        OptionalMatchedMethodInterception<T> implement(TypeDescription... interfaceType);

        /**
         * Adds the given interfaces to be implemented by the created type.
         *
         * @param interfaceTypes A description of the interfaces to implement.
         * @return A builder which will create a dynamic type that implements the given interfaces.
         */
        OptionalMatchedMethodInterception<T> implement(Collection<? extends TypeDescription> interfaceTypes);

        /**
         * Names the currently created dynamic type by a fixed name.
         *
         * @param name A fully qualified name to give to the created dynamic type.
         * @return A builder that will name its dynamic type by the given name.
         */
        Builder<T> name(String name);

        /**
         * Names the currently created dynamic type by the given naming strategy.
         *
         * @param namingStrategy The naming strategy to apply.
         * @return A builder that creates a type by applying the given naming strategy.
         */
        Builder<T> name(NamingStrategy namingStrategy);

        /**
         * Defines a naming strategy for naming auxiliary types.
         *
         * @param namingStrategy The naming strategy to use.
         * @return This builder where the auxiliary naming strategy was set to be used.
         */
        Builder<T> name(AuxiliaryType.NamingStrategy namingStrategy);

        /**
         * Defines modifiers for the created dynamic type.
         *
         * @param modifier A collection of modifiers to be reflected by the created dynamic type.
         * @return A builder that will create a dynamic type that reflects the given modifiers.
         */
        Builder<T> modifiers(ModifierContributor.ForType... modifier);

        /**
         * Defines modifiers for the created dynamic type.
         *
         * @param modifiers The modifiers to be reflected by the created dynamic type.
         * @return A builder that will create a dynamic type that reflects the given modifiers.
         */
        Builder<T> modifiers(int modifiers);

        /**
         * Defines a matcher for methods that will be ignored for any interception attempt. Any methods
         * that were directly declared on an instrumented type will never be ignored, i.e. ignored methods
         * only represent a filter for methods that are declared in super types that should never be overriden.
         *
         * @param ignoredMethods A method matcher characterizing the methods to be ignored.
         * @return A builder that will always ignore the methods matched by the given method matcher.
         */
        Builder<T> ignoreMethods(ElementMatcher<? super MethodDescription> ignoredMethods);

        /**
         * Adds an attribute appender to the currently constructed type which will be applied on the creation of
         * the type.
         *
         * @param attributeAppender An attribute appender to be applied onto the currently created type.
         * @return A builder that will apply the given attribute appender onto the currently created type.
         */
        Builder<T> attribute(TypeAttributeAppender attributeAppender);

        /**
         * Adds annotations to the currently constructed type.
         * <p>&nbsp;</p>
         * Note: The annotations will not be visible to {@link Implementation}s.
         *
         * @param annotation The annotations to be added to the currently constructed type.
         * @return A builder that will add the given annotation to the created type.
         */
        Builder<T> annotateType(Annotation... annotation);

        /**
         * Adds annotations to the currently constructed type.
         * <p>&nbsp;</p>
         * Note: The annotations will not be visible to {@link Implementation}s.
         *
         * @param annotations The annotations to be added to the currently constructed type.
         * @return A builder that will add the given annotation to the created type.
         */
        Builder<T> annotateType(Iterable<? extends Annotation> annotations);

        /**
         * Adds annotations to the currently constructed type.
         * <p>&nbsp;</p>
         * Note: The annotations will not be visible to {@link Implementation}s.
         *
         * @param annotation The annotations to be added to the currently constructed type.
         * @return A builder that will add the given annotation to the created type.
         */
        Builder<T> annotateType(AnnotationDescription... annotation);

        /**
         * Adds annotations to the currently constructed type.
         * <p>&nbsp;</p>
         * Note: The annotations will not be visible to {@link Implementation}s.
         *
         * @param annotations The annotations to be added to the currently constructed type.
         * @return A builder that will add the given annotation to the created type.
         */
        Builder<T> annotateType(Collection<? extends AnnotationDescription> annotations);

        /**
         * Adds an additional ASM {@link org.objectweb.asm.ClassVisitor} to this builder which will be applied in
         * the construction process of this dynamic type.
         *
         * @param classVisitorWrapper The wrapper delegate for the ASM class visitor.
         * @return A builder that will apply the given ASM class visitor.
         */
        Builder<T> classVisitor(ClassVisitorWrapper classVisitorWrapper);

        /**
         * Defines a bridge method resolver factory to be applied to this type creation. A bridge method resolver is
         * responsible for determining the target method that is invoked by a bridge method. This way, a super method
         * invocation is resolved by invoking the actual super method instead of the bridge method which would in turn
         * resolve the actual method virtually.
         *
         * @param bridgeMethodResolverFactory The bridge method resolver factory that is to be used.
         * @return A builder that will apply the given bridge method resolver factory.
         */
        Builder<T> bridgeMethodResolverFactory(BridgeMethodResolver.Factory bridgeMethodResolverFactory);

        /**
         * Defines the use of a specific factory for a {@link MethodLookupEngine}.
         *
         * @param methodLookupEngineFactory The factory to be used.
         * @return A builder that applies the given method lookup engine factory.
         */
        Builder<T> methodLookupEngine(MethodLookupEngine.Factory methodLookupEngineFactory);

        /**
         * Defines a new field for this type.
         *
         * @param name      The name of the method.
         * @param fieldType The type of this field where the current type can be represented by
         *                  {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifier  The modifiers for this method.
         * @return An interception delegate that exclusively matches the new method.
         */
        FieldValueTarget<T> defineField(String name, Class<?> fieldType, ModifierContributor.ForField... modifier);

        /**
         * Defines a new field for this type.
         *
         * @param name                 The name of the method.
         * @param fieldTypeDescription The type of this field where the current type can be represented by
         *                             {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifier             The modifiers for this method.
         * @return An interception delegate that exclusively matches the new method.
         */
        FieldValueTarget<T> defineField(String name, TypeDescription fieldTypeDescription, ModifierContributor.ForField... modifier);

        /**
         * Defines a new field for this type.
         *
         * @param name      The name of the method.
         * @param fieldType The type of this field where the current type can be represented by
         *                  {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifiers The modifiers for this method.
         * @return An interception delegate that exclusively matches the new method.
         */
        FieldValueTarget<T> defineField(String name, Class<?> fieldType, int modifiers);

        /**
         * Defines a new field for this type.
         *
         * @param name                 The name of the method.
         * @param fieldTypeDescription The type of this field where the current type can be represented by
         *                             {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifiers            The modifiers for this method.
         * @return An interception delegate that exclusively matches the new method.
         */
        FieldValueTarget<T> defineField(String name, TypeDescription fieldTypeDescription, int modifiers);

        /**
         * Defines a new field for this type. The annotations of the given field are not copied and
         * must be added manually if they are required.
         *
         * @param field The field that the generated type should imitate.
         * @return An interception delegate that exclusively matches the new method.
         */
        FieldValueTarget<T> defineField(Field field);

        /**
         * Defines a new field for this type. The annotations of the given field are not copied and
         * must be added manually if they are required.
         *
         * @param fieldDescription The field that the generated type should imitate.
         * @return An interception delegate that exclusively matches the new method.
         */
        FieldValueTarget<T> defineField(FieldDescription fieldDescription);

        /**
         * Defines a new method for this type.
         * <p>&nbsp;</p>
         * Note that a method definition overrides any method of identical signature that was defined in a super
         * type what is only valid if the method is of at least broader visibility and if the overridden method
         * is not {@code final}.
         *
         * @param name           The name of the method.
         * @param returnType     The return type of the method  where the current type can be represented by
         *                       {@link net.bytebuddy.dynamic.TargetType}.
         * @param parameterTypes The parameter types of this method  where the current type can be represented by
         *                       {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifier       The modifiers for this method.
         * @return An interception delegate that exclusively matches the new method.
         */
        ExceptionDeclarableMethodInterception<T> defineMethod(String name,
                                                              Class<?> returnType,
                                                              List<? extends Class<?>> parameterTypes,
                                                              ModifierContributor.ForMethod... modifier);

        /**
         * Defines a new method for this type.
         * <p>&nbsp;</p>
         * Note that a method definition overrides any method of identical signature that was defined in a super
         * type what is only valid if the method is of at least broader visibility and if the overridden method
         * is not {@code final}.
         *
         * @param name           The name of the method.
         * @param returnType     A description of the return type of the method  where the current type can be
         *                       represented by {@link net.bytebuddy.dynamic.TargetType}.
         * @param parameterTypes Descriptions of the parameter types of this method  where the current type can be
         *                       represented by {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifier       The modifiers for this method.
         * @return An interception delegate that exclusively matches the new method.
         */
        ExceptionDeclarableMethodInterception<T> defineMethod(String name,
                                                              TypeDescription returnType,
                                                              List<? extends TypeDescription> parameterTypes,
                                                              ModifierContributor.ForMethod... modifier);

        /**
         * Defines a new method for this type.
         * <p>&nbsp;</p>
         * Note that a method definition overrides any method of identical signature that was defined in a super
         * type what is only valid if the method is of at least broader visibility and if the overridden method
         * is not {@code final}.
         *
         * @param name           The name of the method.
         * @param returnType     The return type of the method  where the current type can be represented by
         *                       {@link net.bytebuddy.dynamic.TargetType}.
         * @param parameterTypes The parameter types of this method  where the current type can be represented by
         *                       {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifiers      The modifiers for this method.
         * @return An interception delegate that exclusively matches the new method.
         */
        ExceptionDeclarableMethodInterception<T> defineMethod(String name,
                                                              Class<?> returnType,
                                                              List<? extends Class<?>> parameterTypes,
                                                              int modifiers);

        /**
         * Defines a new method for this type.
         * <p>&nbsp;</p>
         * Note that a method definition overrides any method of identical signature that was defined in a super
         * type what is only valid if the method is of at least broader visibility and if the overridden method
         * is not {@code final}.
         *
         * @param name           The name of the method.
         * @param returnType     A description of the return type of the method  where the current type can be
         *                       represented by {@link net.bytebuddy.dynamic.TargetType}.
         * @param parameterTypes Descriptions of the parameter types of this method  where the current type can be
         *                       represented by {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifiers      The modifiers for this method.
         * @return An interception delegate that exclusively matches the new method.
         */
        ExceptionDeclarableMethodInterception<T> defineMethod(String name,
                                                              TypeDescription returnType,
                                                              List<? extends TypeDescription> parameterTypes,
                                                              int modifiers);

        /**
         * Defines a new method for this type. Declared exceptions or annotations of the method are not copied and must
         * be added manually.
         * <p>&nbsp;</p>
         * Note that a method definition overrides any method of identical signature that was defined in a super
         * type what is only valid if the method is of at least broader visibility and if the overridden method
         * is not {@code final}.
         *
         * @param method The method that the generated type should imitate.
         * @return An interception delegate that exclusively matches the new method.
         */
        ExceptionDeclarableMethodInterception<T> defineMethod(Method method);

        /**
         * Defines a new method for this type. Declared exceptions or annotations of the method are not copied and must
         * be added manually.
         * <p>&nbsp;</p>
         * Note that a method definition overrides any method of identical signature that was defined in a super
         * type what is only valid if the method is of at least broader visibility and if the overridden method
         * is not {@code final}.
         *
         * @param methodDescription The method that the generated type should imitate.
         * @return An interception delegate that exclusively matches the new method.
         */
        ExceptionDeclarableMethodInterception<T> defineMethod(MethodDescription methodDescription);

        /**
         * Defines a new constructor for this type. A constructor must not be {@code static}. Instead, a static type
         * initializer is added automatically if such an initializer is required. See
         * {@link net.bytebuddy.matcher.ElementMatchers#isTypeInitializer()} for a matcher for this initializer
         * which can be intercepted using
         * {@link net.bytebuddy.dynamic.DynamicType.Builder#invokable(net.bytebuddy.matcher.ElementMatcher)}.
         * <p>&nbsp;</p>
         * Note that a constructor's implementation must call another constructor of the same class or a constructor of
         * its super class. This constructor call must be hardcoded inside of the constructor's method body. Before
         * this constructor call is made, it is not legal to call any methods or to read any fields of the instance
         * under construction.
         *
         * @param parameterTypes The parameter types of this constructor where the current type can be represented by
         *                       {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifier       The modifiers for this constructor.
         * @return An interception delegate that exclusively matches the new constructor.
         */
        ExceptionDeclarableMethodInterception<T> defineConstructor(Iterable<? extends Class<?>> parameterTypes, ModifierContributor.ForMethod... modifier);

        /**
         * Defines a new constructor for this type. A constructor must not be {@code static}. Instead, a static type
         * initializer is added automatically if such an initializer is required. See
         * {@link net.bytebuddy.matcher.ElementMatchers#isTypeInitializer()} for a matcher for this initializer
         * which can be intercepted using
         * {@link net.bytebuddy.dynamic.DynamicType.Builder#invokable(net.bytebuddy.matcher.ElementMatcher)}.
         * <p>&nbsp;</p>
         * Note that a constructor's implementation must call another constructor of the same class or a constructor of
         * its super class. This constructor call must be hardcoded inside of the constructor's method body. Before
         * this constructor call is made, it is not legal to call any methods or to read any fields of the instance
         * under construction.
         *
         * @param parameterTypes The parameter types of this constructor where the current type can be represented by
         *                       {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifier       The modifiers for this constructor.
         * @return An interception delegate that exclusively matches the new constructor.
         */
        ExceptionDeclarableMethodInterception<T> defineConstructor(List<? extends TypeDescription> parameterTypes, ModifierContributor.ForMethod... modifier);

        /**
         * Defines a new constructor for this type. A constructor must not be {@code static}. Instead, a static type
         * initializer is added automatically if such an initializer is required. See
         * {@link net.bytebuddy.matcher.ElementMatchers#isTypeInitializer()} for a matcher for this initializer
         * which can be intercepted using
         * {@link net.bytebuddy.dynamic.DynamicType.Builder#invokable(net.bytebuddy.matcher.ElementMatcher)}.
         * <p>&nbsp;</p>
         * Note that a constructor's implementation must call another constructor of the same class or a constructor of
         * its super class. This constructor call must be hardcoded inside of the constructor's method body. Before
         * this constructor call is made, it is not legal to call any methods or to read any fields of the instance
         * under construction.
         *
         * @param parameterTypes The parameter types of this constructor where the current type can be represented by
         *                       {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifiers      The modifiers for this constructor.
         * @return An interception delegate that exclusively matches the new constructor.
         */
        ExceptionDeclarableMethodInterception<T> defineConstructor(Iterable<? extends Class<?>> parameterTypes, int modifiers);

        /**
         * Defines a new constructor for this type. A constructor must not be {@code static}. Instead, a static type
         * initializer is added automatically if such an initializer is required. See
         * {@link net.bytebuddy.matcher.ElementMatchers#isTypeInitializer()} for a matcher for this initializer
         * which can be intercepted using
         * {@link net.bytebuddy.dynamic.DynamicType.Builder#invokable(net.bytebuddy.matcher.ElementMatcher)}.
         * <p>&nbsp;</p>
         * Note that a constructor's implementation must call another constructor of the same class or a constructor of
         * its super class. This constructor call must be hardcoded inside of the constructor's method body. Before
         * this constructor call is made, it is not legal to call any methods or to read any fields of the instance
         * under construction.
         *
         * @param parameterTypes The parameter types of this constructor where the current type can be represented by
         *                       {@link net.bytebuddy.dynamic.TargetType}.
         * @param modifiers      The modifiers for this constructor.
         * @return An interception delegate that exclusively matches the new constructor.
         */
        ExceptionDeclarableMethodInterception<T> defineConstructor(List<? extends TypeDescription> parameterTypes, int modifiers);

        /**
         * Defines a new constructor for this type. A constructor must not be {@code static}. Instead, a static type
         * initializer is added automatically if such an initializer is required. See
         * {@link net.bytebuddy.matcher.ElementMatchers#isTypeInitializer()} for a matcher for this initializer
         * which can be intercepted using
         * {@link net.bytebuddy.dynamic.DynamicType.Builder#invokable(net.bytebuddy.matcher.ElementMatcher)}.
         * Declared exceptions or annotations of the method are not copied and must be added manually.
         * <p>&nbsp;</p>
         * Note that a constructor's implementation must call another constructor of the same class or a constructor of
         * its super class. This constructor call must be hardcoded inside of the constructor's method body. Before
         * this constructor call is made, it is not legal to call any methods or to read any fields of the instance
         * under construction.
         *
         * @param constructor The constructor for the generated type to imitate.
         * @return An interception delegate that exclusively matches the new constructor.
         */
        ExceptionDeclarableMethodInterception<T> defineConstructor(Constructor<?> constructor);

        /**
         * Defines a new constructor for this type. A constructor must not be {@code static}. Instead, a static type
         * initializer is added automatically if such an initializer is required. See
         * {@link net.bytebuddy.matcher.ElementMatchers#isTypeInitializer()} for a matcher for this initializer
         * which can be intercepted using
         * {@link net.bytebuddy.dynamic.DynamicType.Builder#invokable(net.bytebuddy.matcher.ElementMatcher)}.
         * Declared exceptions or annotations of the method are not copied and must be added manually.
         * <p>&nbsp;</p>
         * Note that a constructor's implementation must call another constructor of the same class or a constructor of
         * its super class. This constructor call must be hardcoded inside of the constructor's method body. Before
         * this constructor call is made, it is not legal to call any methods or to read any fields of the instance
         * under construction.
         *
         * @param methodDescription The constructor for the generated type to imitate.
         * @return An interception delegate that exclusively matches the new constructor.
         */
        ExceptionDeclarableMethodInterception<T> defineConstructor(MethodDescription methodDescription);

        /**
         * Defines a new method or constructor for this type. Declared exceptions or annotations of the method
         * are not copied and must be added manually.
         * <p>&nbsp;</p>
         * Note that a method definition overrides any method of identical signature that was defined in a super
         * type what is only valid if the method is of at least broader visibility and if the overridden method
         * is not {@code final}.
         *
         * @param methodDescription The method tor constructor hat the generated type should imitate.
         * @return An interception delegate that exclusively matches the new method or constructor.
         */
        ExceptionDeclarableMethodInterception<T> define(MethodDescription methodDescription);

        /**
         * Selects a set of methods of this type for instrumentation.
         *
         * @param methodMatcher A matcher describing the methods to be intercepted by this instrumentation.
         * @return An interception delegate for methods matching the given method matcher.
         */
        MatchedMethodInterception<T> method(ElementMatcher<? super MethodDescription> methodMatcher);

        /**
         * Selects a set of constructors of this type for implementation.
         *
         * @param methodMatcher A matcher describing the constructors to be intercepted by this implementation.
         * @return An interception delegate for constructors matching the given method matcher.
         */
        MatchedMethodInterception<T> constructor(ElementMatcher<? super MethodDescription> methodMatcher);

        /**
         * Selects a set of byte code level methods, i.e. methods, constructors and the type initializer of
         * this type for implementation.
         *
         * @param methodMatcher A matcher describing the byte code methods to be intercepted by this implementation.
         * @return An interception delegate for byte code methods matching the given method matcher.
         */
        MatchedMethodInterception<T> invokable(ElementMatcher<? super MethodDescription> methodMatcher);

        /**
         * Selects a set of byte code level methods, i.e. methods, construcors and the type initializer of
         * this type for implementation.
         *
         * @param methodMatcher A latent matcher describing the byte code methods to be intercepted by this implementation.
         * @return An interception delegate for byte code methods matching the given method matcher.
         */
        MatchedMethodInterception<T> invokable(LatentMethodMatcher methodMatcher);

        /**
         * Creates the dynamic type without loading it.
         *
         * @return An unloaded representation of the dynamic type.
         */
        Unloaded<T> make();

        /**
         * Defines an implementation for a method that was added to this instrumentation or a to method selection
         * of existing methods.
         *
         * @param <S> The most specific known loaded type that is implemented by the created dynamic type, usually the
         *            type itself, an interface or the direct super class.
         */
        interface MatchedMethodInterception<S> {

            /**
             * Intercepts the currently selected methods with the provided implementation. If this intercepted method is
             * not yet declared by the current type, it might be added to the currently built type as a result of this
             * interception. If the method is already declared by the current type, its byte code code might be copied
             * into the body of a synthetic method in order to preserve the original code's invokeability.
             *
             * @param implementation The implementation to apply to the currently selected method.
             * @return A builder which will intercept the currently selected methods by the given implementation.
             */
            MethodAnnotationTarget<S> intercept(Implementation implementation);

            /**
             * Implements the currently selected methods as {@code abstract} methods.
             *
             * @return A builder which will implement the currently selected methods as {@code abstract} methods.
             */
            MethodAnnotationTarget<S> withoutCode();

            /**
             * Defines a default annotation value to set for any matched method.
             *
             * @param value The value that the annotation property should set as a default.
             * @param type  The type of the annotation property.
             * @return A builder which defines the given default value for all matched methods.
             */
            MethodAnnotationTarget<S> withDefaultValue(Object value, Class<?> type);

            /**
             * Defines a default annotation value to set for any matched method. The value is to be represented in a wrapper format,
             * {@code enum} values should be handed as {@link net.bytebuddy.description.enumeration.EnumerationDescription}
             * instances, annotations as {@link AnnotationDescription} instances and
             * {@link Class} values as {@link TypeDescription} instances. Other values are handed in their raw format or as their wrapper types.
             *
             * @param value A non-loaded value that the annotation property should set as a default.
             * @return A builder which defines the given default value for all matched methods.
             */
            MethodAnnotationTarget<S> withDefaultValue(Object value);
        }

        /**
         * Defines an implementation for a method that was added to this instrumentation and allows to include
         * exception declarations for the newly defined method.
         *
         * @param <S> The most specific known loaded type that is implemented by the created dynamic type, usually the
         *            type itself, an interface or the direct super class.
         */
        interface ExceptionDeclarableMethodInterception<S> extends MatchedMethodInterception<S> {

            /**
             * Defines a number of {@link java.lang.Throwable} types to be include in the exception declaration.
             *
             * @param exceptionType The types that should be declared to be thrown by the selected method.
             * @return A target for instrumenting the defined method where the method will declare the given exception
             * types.
             */
            MatchedMethodInterception<S> throwing(Class<?>... exceptionType);

            /**
             * Defines a number of {@link java.lang.Throwable} types to be include in the exception declaration.
             *
             * @param exceptionTypes The types that should be declared to be thrown by the selected method.
             * @return A target for instrumenting the defined method where the method will declare the given exception
             * types.
             */
            MatchedMethodInterception<S> throwing(Iterable<? extends Class<?>> exceptionTypes);

            /**
             * Defines a number of {@link java.lang.Throwable} types to be include in the exception declaration.
             *
             * @param exceptionType Descriptions of the types that should be declared to be thrown by the selected method.
             * @return A target for instrumenting the defined method where the method will declare the given exception
             * types.
             */
            MatchedMethodInterception<S> throwing(TypeDescription... exceptionType);

            /**
             * Defines a number of {@link java.lang.Throwable} types to be include in the exception declaration.
             *
             * @param exceptionTypes Descriptions of the types that should be declared to be thrown by the selected method.
             * @return A target for instrumenting the defined method where the method will declare the given exception
             * types.
             */
            MatchedMethodInterception<S> throwing(Collection<? extends TypeDescription> exceptionTypes);
        }

        /**
         * An optional matched method interception allows to define an interception without requiring the definition
         * of an implementation.
         *
         * @param <S> The most specific known loaded type that is implemented by the created dynamic type, usually the
         *            type itself, an interface or the direct super class.
         */
        interface OptionalMatchedMethodInterception<S> extends MatchedMethodInterception<S>, Builder<S> {
            /* This interface is merely a combinator of the matched method interception and the builder interfaces. */
        }

        /**
         * A builder to which a method was just added or an interception for existing methods was specified such that
         * attribute changes can be applied to these methods.
         *
         * @param <S> The most specific known loaded type that is implemented by the created dynamic type, usually the
         *            type itself, an interface or the direct super class.
         */
        interface MethodAnnotationTarget<S> extends Builder<S> {

            /**
             * Defines an attribute appender factory to be applied onto the currently selected methods.
             *
             * @param attributeAppenderFactory The attribute appender factory to apply onto the currently selected
             *                                 methods.
             * @return A builder where the given attribute appender factory will be applied to the currently selected methods.
             */
            MethodAnnotationTarget<S> attribute(MethodAttributeAppender.Factory attributeAppenderFactory);

            /**
             * Defines annotations to be added to the currently selected method.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to
             * {@link Implementation}s.
             *
             * @param annotation The annotations to add to the currently selected methods.
             * @return A builder where the given annotation will be added to the currently selected methods.
             */
            MethodAnnotationTarget<S> annotateMethod(Annotation... annotation);

            /**
             * Defines annotations to be added to the currently selected method.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to
             * {@link Implementation}s.
             *
             * @param annotations The annotations to add to the currently selected methods.
             * @return A builder where the given annotation will be added to the currently selected methods.
             */
            MethodAnnotationTarget<S> annotateMethod(Iterable<? extends Annotation> annotations);

            /**
             * Defines annotations to be added to the currently selected method.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to
             * {@link Implementation}s.
             *
             * @param annotation The annotations to add to the currently selected methods.
             * @return A builder where the given annotation will be added to the currently selected methods.
             */
            MethodAnnotationTarget<S> annotateMethod(AnnotationDescription... annotation);

            /**
             * Defines annotations to be added to the currently selected method.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to
             * {@link Implementation}s.
             *
             * @param annotations The annotations to add to the currently selected methods.
             * @return A builder where the given annotation will be added to the currently selected methods.
             */
            MethodAnnotationTarget<S> annotateMethod(Collection<? extends AnnotationDescription> annotations);

            /**
             * Defines annotations to be added to a parameter of the currently selected methods.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to
             * {@link Implementation}s.
             *
             * @param parameterIndex The index of the parameter to annotate.
             * @param annotation     The annotations to add to a parameter of the currently selected methods.
             * @return A builder where the given annotation will be added to a parameter of the currently selected
             * methods.
             */
            MethodAnnotationTarget<S> annotateParameter(int parameterIndex, Annotation... annotation);

            /**
             * Defines annotations to be added to a parameter of the currently selected methods.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to
             * {@link Implementation}s.
             *
             * @param parameterIndex The index of the parameter to annotate.
             * @param annotations    The annotations to add to a parameter of the currently selected methods.
             * @return A builder where the given annotation will be added to a parameter of the currently selected
             * methods.
             */
            MethodAnnotationTarget<S> annotateParameter(int parameterIndex, Iterable<? extends Annotation> annotations);

            /**
             * Defines annotations to be added to a parameter of the currently selected methods.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to
             * {@link Implementation}s.
             *
             * @param parameterIndex The index of the parameter to annotate.
             * @param annotation     The annotations to add to a parameter of the currently selected methods.
             * @return A builder where the given annotation will be added to a parameter of the currently selected
             * methods.
             */
            MethodAnnotationTarget<S> annotateParameter(int parameterIndex, AnnotationDescription... annotation);

            /**
             * Defines annotations to be added to a parameter of the currently selected methods.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to
             * {@link Implementation}s.
             *
             * @param parameterIndex The index of the parameter to annotate.
             * @param annotations    The annotations to add to a parameter of the currently selected methods.
             * @return A builder where the given annotation will be added to a parameter of the currently selected
             * methods.
             */
            MethodAnnotationTarget<S> annotateParameter(int parameterIndex, Collection<? extends AnnotationDescription> annotations);
        }

        /**
         * A builder to which a field was just added such that default values can be defined for the field. Default
         * values must only be defined for {@code static} fields of a primitive type or of the {@link java.lang.String}
         * type.
         *
         * @param <S> The most specific known type of the dynamic type, usually the type itself, an interface or the
         *            direct super class.
         */
        interface FieldValueTarget<S> extends FieldAnnotationTarget<S> {

            /**
             * Defines a {@code boolean} value to become the optional default value for the recently defined
             * {@code static} field. Defining such a boolean default value is only legal for fields that are
             * represented as an integer within the Java virtual machine. These types are the {@code boolean} type,
             * the {@code byte} type, the {@code short} type, the {@code char} type and the {@code int} type.
             *
             * @param value The value to be defined as a default value for the recently defined field.
             * @return A field annotation target for the currently defined field.
             */
            FieldAnnotationTarget<S> value(boolean value);

            /**
             * Defines an {@code int} value to be become the optional default value for the recently defined
             * {@code static} field. Defining such an integer default value is only legal for fields that are
             * represented as an integer within the Java virtual machine. These types are the {@code boolean} type,
             * the {@code byte} type, the {@code short} type, the {@code char} type and the {@code int} type. By
             * extension, integer types can also be defined for {@code long} types and are automatically converted.
             *
             * @param value The value to be defined as a default value for the recently defined field.
             * @return A field annotation target for the currently defined field.
             */
            FieldAnnotationTarget<S> value(int value);

            /**
             * Defined a default value for a {@code long}-typed {@code static} field. This is only legal if the
             * defined field is also of type {@code long}.
             *
             * @param value The value to be defined as a default value for the recently defined field.
             * @return A field annotation target for the currently defined field.
             */
            FieldAnnotationTarget<S> value(long value);

            /**
             * Defined a default value for a {@code float}-typed {@code static} field. This is only legal if the
             * defined field is also of type {@code float}.
             *
             * @param value The value to be defined as a default value for the recently defined field.
             * @return A field annotation target for the currently defined field.
             */
            FieldAnnotationTarget<S> value(float value);

            /**
             * Defined a default value for a {@code double}-typed {@code static} field. This is only legal if the
             * defined field is also of type {@code double}.
             *
             * @param value The value to be defined as a default value for the recently defined field.
             * @return A field annotation target for the currently defined field.
             */
            FieldAnnotationTarget<S> value(double value);

            /**
             * Defined a default value for a {@link java.lang.String}-typed {@code static} field. This is only legal if
             * the defined field is also of type {@link java.lang.String}. The string must not be {@code null}.
             *
             * @param value The value to be defined as a default value for the recently defined field.
             * @return A field annotation target for the currently defined field.
             */
            FieldAnnotationTarget<S> value(String value);

            /**
             * A validator for assuring that a given value can be represented by a given primitive type.
             */
            enum NumericRangeValidator {

                /**
                 * A validator for {@code boolean} values.
                 */
                BOOLEAN(0, 1),

                /**
                 * A validator for {@code byte} values.
                 */
                BYTE(Byte.MIN_VALUE, Byte.MAX_VALUE),

                /**
                 * A validator for {@code short} values.
                 */
                SHORT(Short.MIN_VALUE, Short.MAX_VALUE),

                /**
                 * A validator for {@code char} values.
                 */
                CHARACTER(Character.MIN_VALUE, Character.MAX_VALUE),

                /**
                 * A validator for {@code int} values.
                 */
                INTEGER(Integer.MIN_VALUE, Integer.MAX_VALUE),

                /**
                 * A validator for {@code long} values.
                 */
                LONG(Integer.MIN_VALUE, Integer.MAX_VALUE) {
                    @Override
                    public Object validate(int value) {
                        return (long) value;
                    }
                };

                /**
                 * The minimum and maximum values for an {@code int} value for the represented primitive value.
                 */
                private final int minimum, maximum;

                /**
                 * Creates a new numeric range validator.
                 *
                 * @param minimum The minimum {@code int} value that can be represented by this primitive type.
                 * @param maximum The maximum {@code int} value that can be represented by this primitive type.
                 */
                NumericRangeValidator(int minimum, int maximum) {
                    this.minimum = minimum;
                    this.maximum = maximum;
                }

                /**
                 * Identifies the correct validator for a given type description.
                 *
                 * @param typeDescription The type of a field for which a default value should be validated.
                 * @return The corresponding numeric range validator.
                 */
                public static NumericRangeValidator of(TypeDescription typeDescription) {
                    if (typeDescription.represents(boolean.class)) {
                        return BOOLEAN;
                    } else if (typeDescription.represents(byte.class)) {
                        return BYTE;
                    } else if (typeDescription.represents(short.class)) {
                        return SHORT;
                    } else if (typeDescription.represents(char.class)) {
                        return CHARACTER;
                    } else if (typeDescription.represents(int.class)) {
                        return INTEGER;
                    } else if (typeDescription.represents(long.class)) {
                        return LONG;
                    } else {
                        throw new IllegalStateException(String.format("A field of type %s does not permit an " +
                                "integer-typed default value", typeDescription));
                    }
                }

                /**
                 * Validates and wraps a given {@code int} value for the represented numeric range.
                 *
                 * @param value The value to be validated for a given numeric range.
                 * @return The wrapped value after validation.
                 */
                public Object validate(int value) {
                    if (value < minimum || value > maximum) {
                        throw new IllegalArgumentException(String.format("The value %d overflows for %s", value, this));
                    }
                    return value;
                }

                @Override
                public String toString() {
                    return "DynamicType.Builder.FieldValueTarget.NumericRangeValidator." + name();
                }
            }
        }

        /**
         * A builder to which a field was just added such that attribute changes can be applied to this field.
         *
         * @param <S> The most specific known type of the dynamic type, usually the type itself, an interface or the
         *            direct super class.
         */
        interface FieldAnnotationTarget<S> extends Builder<S> {

            /**
             * Defines an attribute appender factory to be applied onto the currently selected field.
             *
             * @param attributeAppenderFactory The attribute appender factory to apply onto the currently selected
             *                                 field.
             * @return A builder where the given attribute appender factory will be applied to the currently selected field.
             */
            FieldAnnotationTarget<S> attribute(FieldAttributeAppender.Factory attributeAppenderFactory);

            /**
             * Defines annotations to be added to the currently selected field.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to {@link Implementation}s.
             *
             * @param annotation The annotations to add to the currently selected field.
             * @return A builder where the given annotation will be added to the currently selected field.
             */
            FieldAnnotationTarget<S> annotateField(Annotation... annotation);

            /**
             * Defines annotations to be added to the currently selected field.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to {@link Implementation}s.
             *
             * @param annotations The annotations to add to the currently selected field.
             * @return A builder where the given annotation will be added to the currently selected field.
             */
            FieldAnnotationTarget<S> annotateField(Iterable<? extends Annotation> annotations);

            /**
             * Defines annotations to be added to the currently selected field.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to {@link Implementation}s.
             *
             * @param annotation The annotations to add to the currently selected field.
             * @return A builder where the given annotation will be added to the currently selected field.
             */
            FieldAnnotationTarget<S> annotateField(AnnotationDescription... annotation);

            /**
             * Defines annotations to be added to the currently selected field.
             * <p>&nbsp;</p>
             * Note: The annotations will not be visible to {@link Implementation}s.
             *
             * @param annotations The annotations to add to the currently selected field.
             * @return A builder where the given annotation will be added to the currently selected field.
             */
            FieldAnnotationTarget<S> annotateField(Collection<? extends AnnotationDescription> annotations);
        }

        /**
         * An abstract base implementation for a dynamic type builder. For representing the built type, the
         * {@link net.bytebuddy.dynamic.TargetType} class can be used as a placeholder.
         *
         * @param <S> The most specific known loaded type that is implemented by the created dynamic type, usually the
         *            type itself, an interface or the direct super class.
         */
        abstract class AbstractBase<S> implements Builder<S> {

            /**
             * The class file version specified for this builder.
             */
            protected final ClassFileVersion classFileVersion;

            /**
             * The naming strategy specified for this builder.
             */
            protected final NamingStrategy namingStrategy;

            /**
             * The naming strategy for auxiliary types specified for this builder.
             */
            protected final AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy;

            /**
             * The target type description that is specified for this builder.
             */
            protected final TypeDescription targetType;

            /**
             * The interface types to implement as specified for this builder.
             */
            protected final List<TypeDescription> interfaceTypes;

            /**
             * The modifiers specified for this builder.
             */
            protected final int modifiers;

            /**
             * The type attribute appender specified for this builder.
             */
            protected final TypeAttributeAppender attributeAppender;

            /**
             * The method matcher for ignored method specified for this builder.
             */
            protected final ElementMatcher<? super MethodDescription> ignoredMethods;

            /**
             * The bridge method resolver factory specified for this builder.
             */
            protected final BridgeMethodResolver.Factory bridgeMethodResolverFactory;

            /**
             * The class visitor wrapper chain that is applied on created types by this builder.
             */
            protected final ClassVisitorWrapper.Chain classVisitorWrapperChain;

            /**
             * The field registry of this builder.
             */
            protected final FieldRegistry fieldRegistry;

            /**
             * The method registry of this builder.
             */
            protected final MethodRegistry methodRegistry;

            /**
             * The method lookup engine factory to be used by this builder.
             */
            protected final MethodLookupEngine.Factory methodLookupEngineFactory;

            /**
             * The default field attribute appender factory that is automatically added to any field that is
             * registered on this builder.
             */
            protected final FieldAttributeAppender.Factory defaultFieldAttributeAppenderFactory;

            /**
             * The default method attribute appender factory that is automatically added to any field method is
             * registered on this builder.
             */
            protected final MethodAttributeAppender.Factory defaultMethodAttributeAppenderFactory;

            /**
             * This builder's currently registered field tokens.
             */
            protected final List<FieldToken> fieldTokens;

            /**
             * This builder's currently registered method tokens.
             */
            protected final List<MethodToken> methodTokens;

            /**
             * Creates a new immutable type builder base implementation.
             *
             * @param classFileVersion                      The class file version for the created dynamic type.
             * @param namingStrategy                        The naming strategy for naming the dynamic type.
             * @param auxiliaryTypeNamingStrategy           The naming strategy for naming auxiliary types of the dynamic type.
             * @param targetType                            A description of the type that the dynamic type should represent.
             * @param interfaceTypes                        A list of interfaces that should be implemented by the created dynamic type.
             * @param modifiers                             The modifiers to be represented by the dynamic type.
             * @param attributeAppender                     The attribute appender to apply onto the dynamic type that is created.
             * @param ignoredMethods                        A matcher for determining methods that are to be ignored for instrumentation.
             * @param bridgeMethodResolverFactory           A factory for creating a bridge method resolver.
             * @param classVisitorWrapperChain              A chain of ASM class visitors to apply to the writing process.
             * @param fieldRegistry                         The field registry to apply to the dynamic type creation.
             * @param methodRegistry                        The method registry to apply to the dynamic type creation.
             * @param methodLookupEngineFactory             The method lookup engine factory to apply to the dynamic type creation.
             * @param defaultFieldAttributeAppenderFactory  The field attribute appender factory that should be applied by default if
             *                                              no specific appender was specified for a given field.
             * @param defaultMethodAttributeAppenderFactory The method attribute appender factory that should be applied by default
             *                                              if no specific appender was specified for a given method.
             * @param fieldTokens                           A list of field representations that were added explicitly to this
             *                                              dynamic type.
             * @param methodTokens                          A list of method representations that were added explicitly to this
             *                                              dynamic type.
             */
            protected AbstractBase(ClassFileVersion classFileVersion,
                                   NamingStrategy namingStrategy,
                                   AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy,
                                   TypeDescription targetType,
                                   List<TypeDescription> interfaceTypes,
                                   int modifiers,
                                   TypeAttributeAppender attributeAppender,
                                   ElementMatcher<? super MethodDescription> ignoredMethods,
                                   BridgeMethodResolver.Factory bridgeMethodResolverFactory,
                                   ClassVisitorWrapper.Chain classVisitorWrapperChain,
                                   FieldRegistry fieldRegistry,
                                   MethodRegistry methodRegistry,
                                   MethodLookupEngine.Factory methodLookupEngineFactory,
                                   FieldAttributeAppender.Factory defaultFieldAttributeAppenderFactory,
                                   MethodAttributeAppender.Factory defaultMethodAttributeAppenderFactory,
                                   List<FieldToken> fieldTokens,
                                   List<MethodToken> methodTokens) {
                this.classFileVersion = classFileVersion;
                this.namingStrategy = namingStrategy;
                this.auxiliaryTypeNamingStrategy = auxiliaryTypeNamingStrategy;
                this.targetType = targetType;
                this.interfaceTypes = interfaceTypes;
                this.modifiers = modifiers;
                this.attributeAppender = attributeAppender;
                this.ignoredMethods = ignoredMethods;
                this.bridgeMethodResolverFactory = bridgeMethodResolverFactory;
                this.classVisitorWrapperChain = classVisitorWrapperChain;
                this.fieldRegistry = fieldRegistry;
                this.methodRegistry = methodRegistry;
                this.methodLookupEngineFactory = methodLookupEngineFactory;
                this.defaultFieldAttributeAppenderFactory = defaultFieldAttributeAppenderFactory;
                this.defaultMethodAttributeAppenderFactory = defaultMethodAttributeAppenderFactory;
                this.fieldTokens = fieldTokens;
                this.methodTokens = methodTokens;
            }

            /**
             * Adds all fields and methods to an instrumented type.
             *
             * @param instrumentedType The instrumented type that is basis of the alteration.
             * @return The created instrumented type with all fields and methods applied.
             */
            protected InstrumentedType applyRecordedMembersTo(InstrumentedType instrumentedType) {
                for (FieldToken fieldToken : fieldTokens) {
                    instrumentedType = instrumentedType.withField(fieldToken.name,
                            fieldToken.resolveFieldType(instrumentedType),
                            fieldToken.modifiers);
                }
                for (MethodToken methodToken : methodTokens) {
                    instrumentedType = instrumentedType.withMethod(methodToken.internalName,
                            methodToken.resolveReturnType(instrumentedType),
                            methodToken.resolveParameterTypes(instrumentedType),
                            methodToken.resolveExceptionTypes(instrumentedType),
                            methodToken.modifiers);
                }
                return instrumentedType;
            }

            @Override
            public OptionalMatchedMethodInterception<S> implement(Class<?>... interfaceType) {
                return implement(new TypeList.ForLoadedType(nonNull(interfaceType)));
            }

            @Override
            public OptionalMatchedMethodInterception<S> implement(Iterable<? extends Class<?>> interfaceTypes) {
                return implement(new TypeList.ForLoadedType(toList(interfaceTypes)));
            }

            @Override
            public OptionalMatchedMethodInterception<S> implement(TypeDescription... interfaceType) {
                return implement(Arrays.asList(interfaceType));
            }

            @Override
            public OptionalMatchedMethodInterception<S> implement(Collection<? extends TypeDescription> interfaceTypes) {
                return new DefaultOptionalMatchedMethodInterception(new ArrayList<TypeDescription>(isImplementable(interfaceTypes)));
            }

            @Override
            public FieldValueTarget<S> defineField(String name,
                                                   Class<?> fieldType,
                                                   ModifierContributor.ForField... modifier) {
                return defineField(name, new TypeDescription.ForLoadedType(fieldType), modifier);
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineMethod(String name,
                                                                         Class<?> returnType,
                                                                         List<? extends Class<?>> parameterTypes,
                                                                         ModifierContributor.ForMethod... modifier) {
                return defineMethod(name,
                        new TypeDescription.ForLoadedType(returnType),
                        new TypeList.ForLoadedType(new ArrayList<Class<?>>(nonNull(parameterTypes))),
                        modifier);
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineConstructor(Iterable<? extends Class<?>> parameterTypes,
                                                                              ModifierContributor.ForMethod... modifier) {
                return defineConstructor(new TypeList.ForLoadedType(toList(parameterTypes)), modifier);
            }

            @Override
            public Builder<S> classFileVersion(ClassFileVersion classFileVersion) {
                return materialize(nonNull(classFileVersion),
                        namingStrategy,
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> name(String name) {
                return materialize(classFileVersion,
                        new NamingStrategy.Fixed(isValidTypeName(name)),
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> name(NamingStrategy namingStrategy) {
                return materialize(classFileVersion,
                        nonNull(namingStrategy),
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> name(AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy) {
                return materialize(classFileVersion,
                        namingStrategy,
                        nonNull(auxiliaryTypeNamingStrategy),
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> modifiers(ModifierContributor.ForType... modifier) {
                return materialize(classFileVersion,
                        namingStrategy,
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        resolveModifierContributors(TYPE_MODIFIER_MASK, nonNull(modifier)),
                        attributeAppender,
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> modifiers(int modifiers) {
                return materialize(classFileVersion,
                        namingStrategy,
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> ignoreMethods(ElementMatcher<? super MethodDescription> ignoredMethods) {
                return materialize(classFileVersion,
                        namingStrategy,
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        new ElementMatcher.Junction.Conjunction<MethodDescription>(this.ignoredMethods,
                                nonNull(ignoredMethods)),
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> attribute(TypeAttributeAppender attributeAppender) {
                return materialize(classFileVersion,
                        namingStrategy,
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        new TypeAttributeAppender.Compound(this.attributeAppender, nonNull(attributeAppender)),
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> annotateType(Annotation... annotation) {
                return annotateType((new AnnotationList.ForLoadedAnnotation(nonNull(annotation))));
            }

            @Override
            public Builder<S> annotateType(Iterable<? extends Annotation> annotations) {
                return annotateType(new AnnotationList.ForLoadedAnnotation(toList(annotations)));
            }

            @Override
            public Builder<S> annotateType(AnnotationDescription... annotation) {
                return annotateType(new AnnotationList.Explicit(Arrays.asList(nonNull(annotation))));
            }

            @Override
            public Builder<S> annotateType(Collection<? extends AnnotationDescription> annotations) {
                return attribute(new TypeAttributeAppender.ForAnnotation(new ArrayList<AnnotationDescription>(nonNull(annotations))));
            }

            @Override
            public Builder<S> classVisitor(ClassVisitorWrapper classVisitorWrapper) {
                return materialize(classFileVersion,
                        namingStrategy,
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain.append(nonNull(classVisitorWrapper)),
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> methodLookupEngine(MethodLookupEngine.Factory methodLookupEngineFactory) {
                return materialize(classFileVersion,
                        namingStrategy,
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        ignoredMethods,
                        bridgeMethodResolverFactory,
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        nonNull(methodLookupEngineFactory),
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public Builder<S> bridgeMethodResolverFactory(BridgeMethodResolver.Factory bridgeMethodResolverFactory) {
                return materialize(classFileVersion,
                        namingStrategy,
                        auxiliaryTypeNamingStrategy,
                        targetType,
                        interfaceTypes,
                        modifiers,
                        attributeAppender,
                        ignoredMethods,
                        nonNull(bridgeMethodResolverFactory),
                        classVisitorWrapperChain,
                        fieldRegistry,
                        methodRegistry,
                        methodLookupEngineFactory,
                        defaultFieldAttributeAppenderFactory,
                        defaultMethodAttributeAppenderFactory,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public FieldValueTarget<S> defineField(String name,
                                                   TypeDescription fieldType,
                                                   ModifierContributor.ForField... modifier) {
                return defineField(name,
                        fieldType,
                        resolveModifierContributors(FIELD_MODIFIER_MASK, nonNull(modifier)));
            }

            @Override
            public FieldValueTarget<S> defineField(String name,
                                                   Class<?> fieldType,
                                                   int modifiers) {
                return defineField(name,
                        new TypeDescription.ForLoadedType(nonNull(fieldType)),
                        modifiers);
            }

            @Override
            public FieldValueTarget<S> defineField(String name,
                                                   TypeDescription fieldTypeDescription,
                                                   int modifiers) {
                return new DefaultFieldValueTarget(new FieldToken(isValidIdentifier(name), isActualType(fieldTypeDescription), modifiers),
                        defaultFieldAttributeAppenderFactory);
            }

            @Override
            public FieldValueTarget<S> defineField(Field field) {
                return defineField(field.getName(), field.getType(), field.getModifiers());
            }

            @Override
            public FieldValueTarget<S> defineField(FieldDescription fieldDescription) {
                return defineField(fieldDescription.getName(), fieldDescription.getFieldType(), fieldDescription.getModifiers());
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineMethod(String name,
                                                                         TypeDescription returnType,
                                                                         List<? extends TypeDescription> parameterTypes,
                                                                         ModifierContributor.ForMethod... modifier) {
                return defineMethod(name, returnType, parameterTypes, resolveModifierContributors(METHOD_MODIFIER_MASK, modifier));
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineMethod(Method method) {
                return defineMethod(method.getName(), method.getReturnType(), Arrays.asList(method.getParameterTypes()), method.getModifiers());
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineMethod(MethodDescription methodDescription) {
                if (!methodDescription.isMethod()) {
                    throw new IllegalArgumentException("Not a method: " + methodDescription);
                }
                return defineMethod(methodDescription.getName(),
                        methodDescription.getReturnType(),
                        methodDescription.getParameters().asTypeList(),
                        methodDescription.getModifiers());
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineMethod(String name,
                                                                         Class<?> returnType,
                                                                         List<? extends Class<?>> parameterTypes,
                                                                         int modifiers) {
                return defineMethod(name,
                        new TypeDescription.ForLoadedType(nonNull(returnType)),
                        new TypeList.ForLoadedType(nonNull(parameterTypes)),
                        modifiers);
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineMethod(String name,
                                                                         TypeDescription returnType,
                                                                         List<? extends TypeDescription> parameterTypes,
                                                                         int modifiers) {
                return new DefaultExceptionDeclarableMethodInterception(new MethodToken(isValidIdentifier(name),
                        isActualTypeOrVoid(returnType),
                        isActualType(parameterTypes),
                        Collections.<TypeDescription>emptyList(),
                        modifiers));
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineConstructor(
                    List<? extends TypeDescription> parameterTypes,
                    ModifierContributor.ForMethod... modifier) {
                return defineConstructor(parameterTypes, resolveModifierContributors(METHOD_MODIFIER_MASK & ~Opcodes.ACC_STATIC, nonNull(modifier)));
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineConstructor(Constructor<?> constructor) {
                return defineConstructor(Arrays.asList(constructor.getParameterTypes()),
                        constructor.getModifiers());
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineConstructor(MethodDescription methodDescription) {
                if (!methodDescription.isConstructor()) {
                    throw new IllegalArgumentException("Not a constructor: " + methodDescription);
                }
                return defineConstructor(methodDescription.getParameters().asTypeList(), methodDescription.getModifiers());
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineConstructor(Iterable<? extends Class<?>> parameterTypes, int modifiers) {
                return defineConstructor(new TypeList.ForLoadedType(toList(parameterTypes)), modifiers);
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> defineConstructor(List<? extends TypeDescription> parameterTypes, int modifiers) {
                return new DefaultExceptionDeclarableMethodInterception(new MethodToken(isActualType(parameterTypes),
                        Collections.<TypeDescription>emptyList(),
                        modifiers));
            }

            @Override
            public ExceptionDeclarableMethodInterception<S> define(MethodDescription methodDescription) {
                return methodDescription.isMethod()
                        ? defineMethod(methodDescription)
                        : defineConstructor(methodDescription);
            }

            @Override
            public MatchedMethodInterception<S> method(ElementMatcher<? super MethodDescription> methodMatcher) {
                return invokable(isMethod().and(nonNull(methodMatcher)));
            }

            @Override
            public MatchedMethodInterception<S> constructor(ElementMatcher<? super MethodDescription> methodMatcher) {
                return invokable(isConstructor().and(nonNull(methodMatcher)));
            }

            @Override
            public MatchedMethodInterception<S> invokable(ElementMatcher<? super MethodDescription> methodMatcher) {
                return invokable(new LatentMethodMatcher.Resolved(nonNull(methodMatcher)));
            }

            @Override
            public MatchedMethodInterception<S> invokable(LatentMethodMatcher methodMatcher) {
                return new DefaultMatchedMethodInterception(nonNull(methodMatcher), methodTokens);
            }

            /**
             * Creates a new immutable type builder which represents the given arguments.
             *
             * @param classFileVersion                      The class file version for the created dynamic type.
             * @param namingStrategy                        The naming strategy for naming the dynamic type.
             * @param auxiliaryTypeNamingStrategy           The naming strategy for naming the auxiliary type of the dynamic type.
             * @param targetType                            A description of the type that the dynamic type should represent.
             * @param interfaceTypes                        A list of interfaces that should be implemented by the created dynamic type.
             * @param modifiers                             The modifiers to be represented by the dynamic type.
             * @param attributeAppender                     The attribute appender to apply onto the dynamic type that is created.
             * @param ignoredMethods                        A matcher for determining methods that are to be ignored for implementation.
             * @param bridgeMethodResolverFactory           A factory for creating a bridge method resolver.
             * @param classVisitorWrapperChain              A chain of ASM class visitors to apply to the writing process.
             * @param fieldRegistry                         The field registry to apply to the dynamic type creation.
             * @param methodRegistry                        The method registry to apply to the dynamic type creation.
             * @param methodLookupEngineFactory             The method lookup engine factory to apply to the dynamic type creation.
             * @param defaultFieldAttributeAppenderFactory  The field attribute appender factory that should be applied by default if
             *                                              no specific appender was specified for a given field.
             * @param defaultMethodAttributeAppenderFactory The method attribute appender factory that should be applied by default
             *                                              if no specific appender was specified for a given method.
             * @param fieldTokens                           A list of field representations that were added explicitly to this
             *                                              dynamic type.
             * @param methodTokens                          A list of method representations that were added explicitly to this
             *                                              dynamic type.
             * @return A dynamic type builder that represents the given arguments.
             */
            protected abstract Builder<S> materialize(ClassFileVersion classFileVersion,
                                                      NamingStrategy namingStrategy,
                                                      AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy,
                                                      TypeDescription targetType,
                                                      List<TypeDescription> interfaceTypes,
                                                      int modifiers,
                                                      TypeAttributeAppender attributeAppender,
                                                      ElementMatcher<? super MethodDescription> ignoredMethods,
                                                      BridgeMethodResolver.Factory bridgeMethodResolverFactory,
                                                      ClassVisitorWrapper.Chain classVisitorWrapperChain,
                                                      FieldRegistry fieldRegistry,
                                                      MethodRegistry methodRegistry,
                                                      MethodLookupEngine.Factory methodLookupEngineFactory,
                                                      FieldAttributeAppender.Factory defaultFieldAttributeAppenderFactory,
                                                      MethodAttributeAppender.Factory defaultMethodAttributeAppenderFactory,
                                                      List<FieldToken> fieldTokens,
                                                      List<MethodToken> methodTokens);

            @Override
            public boolean equals(Object other) {
                if (this == other)
                    return true;
                if (other == null || getClass() != other.getClass())
                    return false;
                AbstractBase that = (AbstractBase) other;
                return modifiers == that.modifiers
                        && attributeAppender.equals(that.attributeAppender)
                        && bridgeMethodResolverFactory.equals(that.bridgeMethodResolverFactory)
                        && classFileVersion.equals(that.classFileVersion)
                        && classVisitorWrapperChain.equals(that.classVisitorWrapperChain)
                        && defaultFieldAttributeAppenderFactory.equals(that.defaultFieldAttributeAppenderFactory)
                        && defaultMethodAttributeAppenderFactory.equals(that.defaultMethodAttributeAppenderFactory)
                        && fieldRegistry.equals(that.fieldRegistry)
                        && fieldTokens.equals(that.fieldTokens)
                        && ignoredMethods.equals(that.ignoredMethods)
                        && interfaceTypes.equals(that.interfaceTypes)
                        && targetType.equals(that.targetType)
                        && methodLookupEngineFactory.equals(that.methodLookupEngineFactory)
                        && methodRegistry.equals(that.methodRegistry)
                        && methodTokens.equals(that.methodTokens)
                        && namingStrategy.equals(that.namingStrategy)
                        && auxiliaryTypeNamingStrategy.equals(that.auxiliaryTypeNamingStrategy);
            }

            @Override
            public int hashCode() {
                int result = classFileVersion.hashCode();
                result = 31 * result + namingStrategy.hashCode();
                result = 31 * result + auxiliaryTypeNamingStrategy.hashCode();
                result = 31 * result + targetType.hashCode();
                result = 31 * result + interfaceTypes.hashCode();
                result = 31 * result + modifiers;
                result = 31 * result + attributeAppender.hashCode();
                result = 31 * result + ignoredMethods.hashCode();
                result = 31 * result + bridgeMethodResolverFactory.hashCode();
                result = 31 * result + classVisitorWrapperChain.hashCode();
                result = 31 * result + fieldRegistry.hashCode();
                result = 31 * result + methodRegistry.hashCode();
                result = 31 * result + methodLookupEngineFactory.hashCode();
                result = 31 * result + defaultFieldAttributeAppenderFactory.hashCode();
                result = 31 * result + defaultMethodAttributeAppenderFactory.hashCode();
                result = 31 * result + fieldTokens.hashCode();
                result = 31 * result + methodTokens.hashCode();
                return result;
            }

            /**
             * A method token representing a latent method that is defined for the built dynamic type.
             */
            protected static class MethodToken implements LatentMethodMatcher {

                /**
                 * The internal name of the method.
                 */
                protected final String internalName;

                /**
                 * A description of the return type of the method or a type describing the
                 * {@link net.bytebuddy.dynamic.TargetType} placeholder.
                 */
                protected final TypeDescription returnType;

                /**
                 * A list of parameter type descriptions for the method which might be represented by the
                 * {@link net.bytebuddy.dynamic.TargetType} placeholder.
                 */
                protected final List<TypeDescription> parameterTypes;

                /**
                 * A list of exception type descriptions for the method.
                 */
                protected final List<TypeDescription> exceptionTypes;

                /**
                 * The modifiers of the method.
                 */
                protected final int modifiers;

                /**
                 * Creates a new method token representing a constructor to implement for the built dynamic type.
                 *
                 * @param parameterTypes A list of parameters for the constructor.
                 * @param exceptionTypes A list of exception types that are declared for the constructor.
                 * @param modifiers      The modifiers of the constructor.
                 */
                public MethodToken(List<? extends TypeDescription> parameterTypes,
                                   List<? extends TypeDescription> exceptionTypes,
                                   int modifiers) {
                    this(MethodDescription.CONSTRUCTOR_INTERNAL_NAME,
                            TypeDescription.VOID,
                            parameterTypes,
                            exceptionTypes,
                            modifiers);
                }

                /**
                 * Creates a new method token representing a method to implement for the built dynamic type.
                 *
                 * @param internalName   The internal name of the method.
                 * @param returnType     The return type of the method.
                 * @param parameterTypes A list of parameters for the method.
                 * @param exceptionTypes A list of exception types that are declared for the method.
                 * @param modifiers      The modifiers of the method.
                 */
                public MethodToken(String internalName,
                                   TypeDescription returnType,
                                   List<? extends TypeDescription> parameterTypes,
                                   List<? extends TypeDescription> exceptionTypes,
                                   int modifiers) {
                    this.internalName = internalName;
                    this.returnType = returnType;
                    this.parameterTypes = Collections.unmodifiableList(new ArrayList<TypeDescription>(parameterTypes));
                    this.exceptionTypes = Collections.unmodifiableList(new ArrayList<TypeDescription>(exceptionTypes));
                    this.modifiers = modifiers;
                }

                @Override
                public ElementMatcher<? super MethodDescription> resolve(TypeDescription instrumentedType) {
                    return (MethodDescription.CONSTRUCTOR_INTERNAL_NAME.equals(internalName)
                            ? isConstructor()
                            : ElementMatchers.<MethodDescription>named(internalName))
                            .and(returns(resolveReturnType(instrumentedType)))
                            .<MethodDescription>and(takesArguments(resolveParameterTypes(instrumentedType)));
                }

                /**
                 * Resolves the return type for the method which could be represented by the
                 * {@link net.bytebuddy.dynamic.TargetType} placeholder type.
                 *
                 * @param instrumentedType The instrumented place which is used for replacement.
                 * @return A type description for the actual return type.
                 */
                protected TypeDescription resolveReturnType(TypeDescription instrumentedType) {
                    return TargetType.resolve(returnType, instrumentedType, TargetType.MATCHER);
                }

                /**
                 * Resolves the parameter types for the method which could be represented by the
                 * {@link net.bytebuddy.dynamic.TargetType} placeholder type.
                 *
                 * @param instrumentedType The instrumented place which is used for replacement.
                 * @return A list of type descriptions for the actual parameter types.
                 */
                protected List<TypeDescription> resolveParameterTypes(TypeDescription instrumentedType) {
                    return TargetType.resolve(parameterTypes, instrumentedType, TargetType.MATCHER).asRawTypes();
                }

                /**
                 * Resolves the declared exception types for the method.
                 *
                 * @param instrumentedType The instrumented place which is used for replacement.
                 * @return A list of type descriptions for the actual exception types.
                 */
                protected List<TypeDescription> resolveExceptionTypes(TypeDescription instrumentedType) {
                    return TargetType.resolve(exceptionTypes, instrumentedType, TargetType.MATCHER).asRawTypes();
                }

                /**
                 * Returns the internal name of this method token.
                 *
                 * @return The internal name of this method token.
                 */
                public String getInternalName() {
                    return internalName;
                }

                /**
                 * Returns a description of the return type of this method token.
                 *
                 * @return A description of the return type of this method token.
                 */
                public TypeDescription getReturnType() {
                    return returnType;
                }

                /**
                 * Returns a list of descriptions of the parameter types of this method token.
                 *
                 * @return A list of descriptions of the parameter types of this method token.
                 */
                public List<TypeDescription> getParameterTypes() {
                    return parameterTypes;
                }

                /**
                 * Returns a list of exception types of this method token.
                 *
                 * @return A list of exception types of this method token.
                 */
                public List<TypeDescription> getExceptionTypes() {
                    return exceptionTypes;
                }

                /**
                 * Returns the modifiers for this method token.
                 *
                 * @return The modifiers for this method token.
                 */
                public int getModifiers() {
                    return modifiers;
                }

                @Override
                public boolean equals(Object other) {
                    return (this == other || other instanceof MethodToken)
                            && internalName.equals(((MethodToken) other).getInternalName())
                            && parameterTypes.equals(((MethodToken) other).getParameterTypes())
                            && returnType.equals(((MethodToken) other).getReturnType());
                }

                @Override
                public int hashCode() {
                    int result = internalName.hashCode();
                    result = 31 * result + returnType.hashCode();
                    result = 31 * result + parameterTypes.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "DynamicType.Builder.AbstractBase.MethodToken{" +
                            "internalName='" + internalName + '\'' +
                            ", returnType=" + returnType +
                            ", parameterTypes=" + parameterTypes +
                            ", exceptionTypes=" + exceptionTypes +
                            ", modifiers=" + modifiers + '}';
                }
            }

            /**
             * A field token representing a latent field that is defined for the built dynamic type.
             */
            protected static class FieldToken implements FieldRegistry.LatentFieldMatcher {

                /**
                 * The name of the field.
                 */
                protected final String name;

                /**
                 * A description of the field type or a description of the
                 * {@link net.bytebuddy.dynamic.TargetType} placeholder.
                 */
                protected final TypeDescription fieldType;

                /**
                 * The field modifiers.
                 */
                protected final int modifiers;

                /**
                 * Creates a new field token.
                 *
                 * @param name      The name of the field.
                 * @param fieldType A description of the field type.
                 * @param modifiers The modifers of the field.
                 */
                public FieldToken(String name, TypeDescription fieldType, int modifiers) {
                    this.name = name;
                    this.fieldType = fieldType;
                    this.modifiers = modifiers;
                }

                /**
                 * Resolves the field type which could be represented by the
                 * {@link net.bytebuddy.dynamic.TargetType} placeholder type.
                 *
                 * @param instrumentedType The instrumented place which is used for replacement.
                 * @return A type description for the actual field type.
                 */
                protected TypeDescription resolveFieldType(TypeDescription instrumentedType) {
                    return TargetType.resolve(fieldType, instrumentedType, TargetType.MATCHER);
                }

                /**
                 * Returns the name of this field token.
                 *
                 * @return The name of this field token.
                 */
                public String getName() {
                    return name;
                }

                /**
                 * Returns the type of this field token.
                 *
                 * @return The type of this field token.
                 */
                public TypeDescription getFieldType() {
                    return fieldType;
                }

                /**
                 * Returns the modifiers of this field token.
                 *
                 * @return The modifiers of this field token.
                 */
                public int getModifiers() {
                    return modifiers;
                }

                @Override
                public String getFieldName() {
                    return name;
                }

                @Override
                public boolean equals(Object other) {
                    return (this == other || other instanceof FieldToken)
                            && name.equals(((FieldToken) other).getFieldName());
                }

                @Override
                public int hashCode() {
                    return name.hashCode();
                }

                @Override
                public String toString() {
                    return "DynamicType.Builder.AbstractBase.FieldToken{" +
                            "name='" + name + '\'' +
                            ", fieldType=" + fieldType +
                            ", modifiers=" + modifiers + '}';
                }
            }

            /**
             * A base implementation of a builder that is capable of manifesting a change that was not yet applied to
             * the builder.
             *
             * @param <U> The most specific known loaded type that is implemented by the created dynamic type, usually the
             *            type itself, an interface or the direct super class.
             */
            protected abstract class AbstractDelegatingBuilder<U> implements Builder<U> {

                @Override
                public Builder<U> classFileVersion(ClassFileVersion classFileVersion) {
                    return materialize().classFileVersion(classFileVersion);
                }

                @Override
                public OptionalMatchedMethodInterception<U> implement(Class<?>... interfaceType) {
                    return materialize().implement(interfaceType);
                }

                @Override
                public OptionalMatchedMethodInterception<U> implement(Iterable<? extends Class<?>> interfaceTypes) {
                    return materialize().implement(interfaceTypes);
                }

                @Override
                public OptionalMatchedMethodInterception<U> implement(TypeDescription... interfaceType) {
                    return materialize().implement(interfaceType);
                }

                @Override
                public OptionalMatchedMethodInterception<U> implement(Collection<? extends TypeDescription> typeDescriptions) {
                    return materialize().implement(typeDescriptions);
                }

                @Override
                public Builder<U> name(String name) {
                    return materialize().name(name);
                }

                @Override
                public Builder<U> name(NamingStrategy namingStrategy) {
                    return materialize().name(namingStrategy);
                }

                @Override
                public Builder<U> name(AuxiliaryType.NamingStrategy namingStrategy) {
                    return materialize().name(namingStrategy);
                }

                @Override
                public Builder<U> modifiers(ModifierContributor.ForType... modifier) {
                    return materialize().modifiers(modifier);
                }

                @Override
                public Builder<U> modifiers(int modifiers) {
                    return materialize().modifiers(modifiers);
                }

                @Override
                public Builder<U> ignoreMethods(ElementMatcher<? super MethodDescription> ignoredMethods) {
                    return materialize().ignoreMethods(ignoredMethods);
                }

                @Override
                public Builder<U> attribute(TypeAttributeAppender attributeAppender) {
                    return materialize().attribute(attributeAppender);
                }

                @Override
                public Builder<U> annotateType(Annotation... annotation) {
                    return materialize().annotateType(annotation);
                }

                @Override
                public Builder<U> annotateType(Iterable<? extends Annotation> annotations) {
                    return materialize().annotateType(annotations);
                }

                @Override
                public Builder<U> annotateType(AnnotationDescription... annotation) {
                    return materialize().annotateType(annotation);
                }

                @Override
                public Builder<U> annotateType(Collection<? extends AnnotationDescription> annotations) {
                    return materialize().annotateType(annotations);
                }

                @Override
                public Builder<U> classVisitor(ClassVisitorWrapper classVisitorWrapper) {
                    return materialize().classVisitor(classVisitorWrapper);
                }

                @Override
                public Builder<U> methodLookupEngine(MethodLookupEngine.Factory methodLookupEngineFactory) {
                    return materialize().methodLookupEngine(methodLookupEngineFactory);
                }

                @Override
                public Builder<U> bridgeMethodResolverFactory(BridgeMethodResolver.Factory bridgeMethodResolverFactory) {
                    return materialize().bridgeMethodResolverFactory(bridgeMethodResolverFactory);
                }

                @Override
                public FieldValueTarget<U> defineField(String name,
                                                       Class<?> fieldType,
                                                       ModifierContributor.ForField... modifier) {
                    return materialize().defineField(name, fieldType, modifier);
                }

                @Override
                public FieldValueTarget<U> defineField(String name,
                                                       TypeDescription fieldTypeDescription,
                                                       ModifierContributor.ForField... modifier) {
                    return materialize().defineField(name, fieldTypeDescription, modifier);
                }

                @Override
                public FieldValueTarget<U> defineField(String name, Class<?> fieldType, int modifiers) {
                    return materialize().defineField(name, fieldType, modifiers);
                }

                @Override
                public FieldValueTarget<U> defineField(String name,
                                                       TypeDescription fieldTypeDescription,
                                                       int modifiers) {
                    return materialize().defineField(name, fieldTypeDescription, modifiers);
                }

                @Override
                public FieldValueTarget<U> defineField(Field field) {
                    return materialize().defineField(field);
                }

                @Override
                public FieldValueTarget<U> defineField(FieldDescription fieldDescription) {
                    return materialize().defineField(fieldDescription);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineMethod(String name,
                                                                             Class<?> returnType,
                                                                             List<? extends Class<?>> parameterTypes,
                                                                             ModifierContributor.ForMethod... modifier) {
                    return materialize().defineMethod(name, returnType, parameterTypes, modifier);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineMethod(String name,
                                                                             TypeDescription returnType,
                                                                             List<? extends TypeDescription> parameterTypes,
                                                                             ModifierContributor.ForMethod... modifier) {
                    return materialize().defineMethod(name, returnType, parameterTypes, modifier);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineMethod(String name,
                                                                             Class<?> returnType,
                                                                             List<? extends Class<?>> parameterTypes,
                                                                             int modifiers) {
                    return materialize().defineMethod(name, returnType, parameterTypes, modifiers);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineMethod(String name,
                                                                             TypeDescription returnType,
                                                                             List<? extends TypeDescription> parameterTypes,
                                                                             int modifiers) {
                    return materialize().defineMethod(name, returnType, parameterTypes, modifiers);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineMethod(Method method) {
                    return materialize().defineMethod(method);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineMethod(MethodDescription methodDescription) {
                    return materialize().defineMethod(methodDescription);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineConstructor(Iterable<? extends Class<?>> parameterTypes,
                                                                                  ModifierContributor.ForMethod... modifier) {
                    return materialize().defineConstructor(parameterTypes, modifier);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineConstructor(List<? extends TypeDescription> parameterTypes,
                                                                                  ModifierContributor.ForMethod... modifier) {
                    return materialize().defineConstructor(parameterTypes, modifier);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineConstructor(Iterable<? extends Class<?>> parameterTypes, int modifiers) {
                    return materialize().defineConstructor(parameterTypes, modifiers);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineConstructor(List<? extends TypeDescription> parameterTypes, int modifiers) {
                    return materialize().defineConstructor(parameterTypes, modifiers);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineConstructor(Constructor<?> constructor) {
                    return materialize().defineConstructor(constructor);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> defineConstructor(MethodDescription methodDescription) {
                    return materialize().defineConstructor(methodDescription);
                }

                @Override
                public ExceptionDeclarableMethodInterception<U> define(MethodDescription methodDescription) {
                    return materialize().define(methodDescription);
                }

                @Override
                public MatchedMethodInterception<U> method(ElementMatcher<? super MethodDescription> methodMatcher) {
                    return materialize().method(methodMatcher);
                }

                @Override
                public MatchedMethodInterception<U> constructor(ElementMatcher<? super MethodDescription> methodMatcher) {
                    return materialize().constructor(methodMatcher);
                }

                @Override
                public MatchedMethodInterception<U> invokable(ElementMatcher<? super MethodDescription> methodMatcher) {
                    return materialize().invokable(methodMatcher);
                }

                @Override
                public MatchedMethodInterception<U> invokable(LatentMethodMatcher methodMatcher) {
                    return materialize().invokable(methodMatcher);
                }

                @Override
                public Unloaded<U> make() {
                    return materialize().make();
                }

                /**
                 * Materializes the current state of the build before applying another modification.
                 *
                 * @return A builder with all pending changes materialized.
                 */
                protected abstract Builder<U> materialize();
            }

            /**
             * A {@link net.bytebuddy.dynamic.DynamicType.Builder} for which a field was recently defined such that attributes
             * can be added to this recently defined field.
             */
            protected class DefaultFieldValueTarget extends AbstractDelegatingBuilder<S> implements FieldValueTarget<S> {

                /**
                 * Representations of {@code boolean} values as JVM integers.
                 */
                private static final int NUMERIC_BOOLEAN_TRUE = 1, NUMERIC_BOOLEAN_FALSE = 0;

                /**
                 * A token representing the field that was recently defined.
                 */
                private final FieldToken fieldToken;

                /**
                 * The attribute appender factory that was defined for this field token.
                 */
                private final FieldAttributeAppender.Factory attributeAppenderFactory;

                /**
                 * The default value that is to be defined for the recently defined field or {@code null} if no such
                 * value is to be defined. Default values must only be defined for {@code static} fields of primitive types
                 * or of the {@link java.lang.String} type.
                 */
                private final Object defaultValue;

                /**
                 * Creates a new subclass field annotation target for a field without a default value.
                 *
                 * @param fieldToken               A token representing the field that was recently defined.
                 * @param attributeAppenderFactory The attribute appender factory that was defined for this field token.
                 */
                private DefaultFieldValueTarget(FieldToken fieldToken,
                                                FieldAttributeAppender.Factory attributeAppenderFactory) {
                    this(fieldToken, attributeAppenderFactory, null);
                }

                /**
                 * Creates a new subclass field annotation target.
                 *
                 * @param fieldToken               A token representing the field that was recently defined.
                 * @param attributeAppenderFactory The attribute appender factory that was defined for this field token.
                 * @param defaultValue             The default value to define for the recently defined field.
                 */
                private DefaultFieldValueTarget(FieldToken fieldToken,
                                                FieldAttributeAppender.Factory attributeAppenderFactory,
                                                Object defaultValue) {
                    this.fieldToken = fieldToken;
                    this.attributeAppenderFactory = attributeAppenderFactory;
                    this.defaultValue = defaultValue;
                }

                @Override
                protected DynamicType.Builder<S> materialize() {
                    return AbstractBase.this.materialize(classFileVersion,
                            namingStrategy,
                            auxiliaryTypeNamingStrategy,
                            targetType,
                            interfaceTypes,
                            modifiers,
                            attributeAppender,
                            ignoredMethods,
                            bridgeMethodResolverFactory,
                            classVisitorWrapperChain,
                            fieldRegistry.include(fieldToken, attributeAppenderFactory, defaultValue),
                            methodRegistry,
                            methodLookupEngineFactory,
                            defaultFieldAttributeAppenderFactory,
                            defaultMethodAttributeAppenderFactory,
                            join(fieldTokens, fieldToken),
                            methodTokens);
                }

                @Override
                public FieldAnnotationTarget<S> value(boolean value) {
                    return value(value ? NUMERIC_BOOLEAN_TRUE : NUMERIC_BOOLEAN_FALSE);
                }

                @Override
                public FieldAnnotationTarget<S> value(int value) {
                    return makeFieldAnnotationTarget(
                            NumericRangeValidator.of(fieldToken.getFieldType()).validate(value));
                }

                @Override
                public FieldAnnotationTarget<S> value(long value) {
                    return makeFieldAnnotationTarget(isValid(value, long.class));
                }

                @Override
                public FieldAnnotationTarget<S> value(float value) {
                    return makeFieldAnnotationTarget(isValid(value, float.class));
                }

                @Override
                public FieldAnnotationTarget<S> value(double value) {
                    return makeFieldAnnotationTarget(isValid(value, double.class));
                }

                @Override
                public FieldAnnotationTarget<S> value(String value) {
                    return makeFieldAnnotationTarget(isValid(value, String.class));
                }

                /**
                 * Asserts the field's type to be of a given legal types.
                 *
                 * @param defaultValue The default value to define for the recently defined field.
                 * @param legalType    The type of which this default value needs to be in order to be legal.
                 * @return The given default value.
                 */
                private Object isValid(Object defaultValue, Class<?> legalType) {
                    if (fieldToken.getFieldType().represents(legalType)) {
                        return defaultValue;
                    } else {
                        throw new IllegalStateException(
                                String.format("The given value %s was not of the required type %s",
                                        defaultValue, legalType));
                    }
                }

                /**
                 * Creates a field annotation target for the given default value.
                 *
                 * @param defaultValue The default value to define for the recently defined field.
                 * @return The resulting field annotation target.
                 */
                private FieldAnnotationTarget<S> makeFieldAnnotationTarget(Object defaultValue) {
                    if ((fieldToken.getModifiers() & Opcodes.ACC_STATIC) == 0) {
                        throw new IllegalStateException("Default field values can only be set for static fields");
                    }
                    return new DefaultFieldValueTarget(fieldToken, attributeAppenderFactory, defaultValue);
                }

                @Override
                public FieldAnnotationTarget<S> attribute(FieldAttributeAppender.Factory attributeAppenderFactory) {
                    return new DefaultFieldValueTarget(fieldToken,
                            new FieldAttributeAppender.Factory.Compound(this.attributeAppenderFactory,
                                    nonNull(attributeAppenderFactory)));
                }

                @Override
                public FieldAnnotationTarget<S> annotateField(Annotation... annotation) {
                    return annotateField((new AnnotationList.ForLoadedAnnotation(nonNull(annotation))));
                }

                @Override
                public FieldAnnotationTarget<S> annotateField(Iterable<? extends Annotation> annotations) {
                    return annotateField(new AnnotationList.ForLoadedAnnotation(toList(annotations)));
                }

                @Override
                public FieldAnnotationTarget<S> annotateField(AnnotationDescription... annotation) {
                    return annotateField(Arrays.asList(nonNull(annotation)));
                }

                @Override
                public FieldAnnotationTarget<S> annotateField(Collection<? extends AnnotationDescription> annotations) {
                    return attribute(new FieldAttributeAppender.ForAnnotation(new ArrayList<AnnotationDescription>(nonNull(annotations))));
                }

                @Override
                @SuppressWarnings("unchecked")
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (other == null || getClass() != other.getClass()) return false;
                    DefaultFieldValueTarget that = (DefaultFieldValueTarget) other;
                    return attributeAppenderFactory.equals(that.attributeAppenderFactory)
                            && !(defaultValue != null ?
                            !defaultValue.equals(that.defaultValue) :
                            that.defaultValue != null)
                            && fieldToken.equals(that.fieldToken)
                            && AbstractBase.this.equals(that.getDynamicTypeBuilder());
                }

                @Override
                public int hashCode() {
                    int result = fieldToken.hashCode();
                    result = 31 * result + attributeAppenderFactory.hashCode();
                    result = 31 * result + (defaultValue != null ? defaultValue.hashCode() : 0);
                    result = 31 * result + AbstractBase.this.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "DynamicType.Builder.AbstractBase.DefaultFieldValueTarget{" +
                            "base=" + AbstractBase.this +
                            ", fieldToken=" + fieldToken +
                            ", attributeAppenderFactory=" + attributeAppenderFactory +
                            ", defaultValue=" + defaultValue +
                            '}';
                }

                /**
                 * Returns the outer instance.
                 *
                 * @return The outer instance.
                 */
                private Builder<?> getDynamicTypeBuilder() {
                    return AbstractBase.this;
                }
            }

            /**
             * A {@link net.bytebuddy.dynamic.DynamicType.Builder.MatchedMethodInterception} for which a method was recently
             * identified or defined such that an {@link Implementation} for these methods can
             * now be defined.
             */
            protected class DefaultMatchedMethodInterception implements MatchedMethodInterception<S> {

                /**
                 * The latent method matcher that identifies this interception.
                 */
                private final LatentMethodMatcher methodMatcher;

                /**
                 * A list of all method tokens that were previously defined.
                 */
                private final List<MethodToken> methodTokens;

                /**
                 * Creates a new instance of a default matched method interception.
                 *
                 * @param methodMatcher The latent method matcher that identifies this interception.
                 * @param methodTokens  A list of all method tokens that were previously defined.
                 */
                protected DefaultMatchedMethodInterception(LatentMethodMatcher methodMatcher,
                                                           List<MethodToken> methodTokens) {
                    this.methodMatcher = methodMatcher;
                    this.methodTokens = methodTokens;
                }

                @Override
                public MethodAnnotationTarget<S> intercept(Implementation implementation) {
                    return new DefaultMethodAnnotationTarget(methodTokens,
                            methodMatcher,
                            new MethodRegistry.Handler.ForImplementation(nonNull(implementation)),
                            defaultMethodAttributeAppenderFactory);
                }

                @Override
                public MethodAnnotationTarget<S> withoutCode() {
                    return new DefaultMethodAnnotationTarget(methodTokens,
                            methodMatcher,
                            MethodRegistry.Handler.ForAbstractMethod.INSTANCE,
                            defaultMethodAttributeAppenderFactory);
                }

                @Override
                public MethodAnnotationTarget<S> withDefaultValue(Object value, Class<?> type) {
                    return withDefaultValue(AnnotationDescription.ForLoadedAnnotation.describe(nonNull(value), new TypeDescription.ForLoadedType(nonNull(type))));
                }

                @Override
                public MethodAnnotationTarget<S> withDefaultValue(Object value) {
                    return new DefaultMethodAnnotationTarget(methodTokens,
                            methodMatcher,
                            MethodRegistry.Handler.ForAnnotationValue.of(value),
                            MethodAttributeAppender.NoOp.INSTANCE);
                }

                @Override
                @SuppressWarnings("unchecked")
                public boolean equals(Object other) {
                    if (this == other)
                        return true;
                    if (other == null || getClass() != other.getClass())
                        return false;
                    DefaultMatchedMethodInterception that = (DefaultMatchedMethodInterception) other;
                    return methodMatcher.equals(that.methodMatcher)
                            && methodTokens.equals(that.methodTokens)
                            && AbstractBase.this.equals(that.getDynamicTypeBuilder());
                }

                @Override
                public int hashCode() {
                    int result = methodMatcher.hashCode();
                    result = 31 * result + methodTokens.hashCode();
                    result = 31 * result + AbstractBase.this.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "DynamicType.Builder.AbstractBase.DefaultMatchedMethodInterception{" +
                            "base=" + AbstractBase.this +
                            ", methodMatcher=" + methodMatcher +
                            ", methodTokens=" + methodTokens +
                            '}';
                }

                /**
                 * Returns the outer instance.
                 *
                 * @return The outer instance.
                 */
                private Builder<?> getDynamicTypeBuilder() {
                    return AbstractBase.this;
                }
            }

            /**
             * A {@link net.bytebuddy.dynamic.DynamicType.Builder.ExceptionDeclarableMethodInterception} which allows the
             * definition of exceptions for a recently defined method.
             */
            protected class DefaultExceptionDeclarableMethodInterception implements ExceptionDeclarableMethodInterception<S> {

                /**
                 * The method token for which exceptions can be defined additionally.
                 */
                private final MethodToken methodToken;

                /**
                 * Creates a new subclass exception declarable method interception.
                 *
                 * @param methodToken The method token to define on the currently constructed method.
                 */
                private DefaultExceptionDeclarableMethodInterception(MethodToken methodToken) {
                    this.methodToken = methodToken;
                }

                @Override
                public MatchedMethodInterception<S> throwing(Class<?>... exceptionType) {
                    return throwing(new TypeList.ForLoadedType(nonNull(exceptionType)));
                }

                @Override
                public MatchedMethodInterception<S> throwing(Iterable<? extends Class<?>> exceptionTypes) {
                    return throwing(new TypeList.ForLoadedType(toList(exceptionTypes)));
                }

                @Override
                public MatchedMethodInterception<S> throwing(TypeDescription... exceptionType) {
                    return throwing(Arrays.asList(nonNull(exceptionType)));
                }

                @Override
                public MatchedMethodInterception<S> throwing(Collection<? extends TypeDescription> exceptionTypes) {
                    return materialize(new MethodToken(methodToken.getInternalName(),
                            methodToken.getReturnType(),
                            methodToken.getParameterTypes(),
                            uniqueRaw(isThrowable(new ArrayList<TypeDescription>(exceptionTypes))),
                            methodToken.getModifiers()));
                }

                @Override
                public MethodAnnotationTarget<S> intercept(Implementation implementation) {
                    return materialize(methodToken).intercept(implementation);
                }

                @Override
                public MethodAnnotationTarget<S> withoutCode() {
                    return materialize(methodToken).withoutCode();
                }

                @Override
                public MethodAnnotationTarget<S> withDefaultValue(Object value, Class<?> type) {
                    return materialize(methodToken).withDefaultValue(value, type);
                }

                @Override
                public MethodAnnotationTarget<S> withDefaultValue(Object value) {
                    return materialize(methodToken).withDefaultValue(value);
                }

                /**
                 * Materializes the given method definition and returns an instance for defining an implementation.
                 *
                 * @param methodToken The method token to define on the currently constructed type.
                 * @return A subclass matched method interception that represents the materialized method.
                 */
                private DefaultMatchedMethodInterception materialize(MethodToken methodToken) {
                    return new DefaultMatchedMethodInterception(methodToken, join(methodTokens, methodToken));
                }

                @Override
                @SuppressWarnings("unchecked")
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && methodToken.equals(((DefaultExceptionDeclarableMethodInterception) other).methodToken)
                            && AbstractBase.this
                            .equals(((DefaultExceptionDeclarableMethodInterception) other).getDynamicTypeBuilder());
                }

                @Override
                public int hashCode() {
                    return 31 * AbstractBase.this.hashCode() + methodToken.hashCode();
                }

                @Override
                public String toString() {
                    return "DynamicType.Builder.AbstractBase.DefaultExceptionDeclarableMethodInterception{" +
                            "base=" + AbstractBase.this +
                            ", methodToken=" + methodToken +
                            '}';
                }

                /**
                 * Returns the outer instance.
                 *
                 * @return The outer instance.
                 */
                private Builder<?> getDynamicTypeBuilder() {
                    return AbstractBase.this;
                }
            }

            /**
             * A {@link net.bytebuddy.dynamic.DynamicType.Builder.MethodAnnotationTarget} which allows the definition of
             * annotations for a recently identified method.
             */
            protected class DefaultMethodAnnotationTarget extends AbstractDelegatingBuilder<S> implements MethodAnnotationTarget<S> {

                /**
                 * A list of all method tokens that were previously defined.
                 */
                private final List<MethodToken> methodTokens;

                /**
                 * A matcher that allows to identify the methods to be intercepted.
                 */
                private final LatentMethodMatcher methodMatcher;

                /**
                 * The handler to apply to any matched method.
                 */
                private final MethodRegistry.Handler handler;

                /**
                 * The method attribute appender factory to be applied to the matched methods.
                 */
                private final MethodAttributeAppender.Factory attributeAppenderFactory;

                /**
                 * Creates a new default method annotation target.
                 *
                 * @param methodTokens             A list of all method tokens that were previously defined.
                 * @param methodMatcher            A matcher that allows to identify the methods to be intercepted.
                 * @param handler                  The handler to apply to any matched method.
                 * @param attributeAppenderFactory The method attribute appender factory to be applied to the matched methods.
                 */
                protected DefaultMethodAnnotationTarget(List<MethodToken> methodTokens,
                                                        LatentMethodMatcher methodMatcher,
                                                        MethodRegistry.Handler handler,
                                                        MethodAttributeAppender.Factory attributeAppenderFactory) {
                    this.methodMatcher = methodMatcher;
                    this.methodTokens = methodTokens;
                    this.handler = handler;
                    this.attributeAppenderFactory = attributeAppenderFactory;
                }

                @Override
                protected DynamicType.Builder<S> materialize() {
                    return AbstractBase.this.materialize(classFileVersion,
                            namingStrategy,
                            auxiliaryTypeNamingStrategy,
                            targetType,
                            interfaceTypes,
                            modifiers,
                            attributeAppender,
                            ignoredMethods,
                            bridgeMethodResolverFactory,
                            classVisitorWrapperChain,
                            fieldRegistry,
                            methodRegistry.prepend(methodMatcher, handler, attributeAppenderFactory),
                            methodLookupEngineFactory,
                            defaultFieldAttributeAppenderFactory,
                            defaultMethodAttributeAppenderFactory,
                            fieldTokens,
                            methodTokens);
                }

                @Override
                public MethodAnnotationTarget<S> attribute(MethodAttributeAppender.Factory attributeAppenderFactory) {
                    return new DefaultMethodAnnotationTarget(methodTokens,
                            methodMatcher,
                            handler,
                            new MethodAttributeAppender.Factory.Compound(this.attributeAppenderFactory,
                                    nonNull(attributeAppenderFactory)));
                }

                @Override
                public MethodAnnotationTarget<S> annotateMethod(Annotation... annotation) {
                    return annotateMethod((new AnnotationList.ForLoadedAnnotation(nonNull(annotation))));
                }

                @Override
                public MethodAnnotationTarget<S> annotateMethod(Iterable<? extends Annotation> annotations) {
                    return annotateMethod(new AnnotationList.ForLoadedAnnotation(toList(annotations)));
                }

                @Override
                public MethodAnnotationTarget<S> annotateMethod(AnnotationDescription... annotation) {
                    return annotateMethod(Arrays.asList(nonNull(annotation)));
                }

                @Override
                public MethodAnnotationTarget<S> annotateMethod(Collection<? extends AnnotationDescription> annotations) {
                    return attribute(new MethodAttributeAppender.ForAnnotation((nonNull(new ArrayList<AnnotationDescription>(annotations)))));
                }

                @Override
                public MethodAnnotationTarget<S> annotateParameter(int parameterIndex, Annotation... annotation) {
                    return annotateParameter(parameterIndex, new AnnotationList.ForLoadedAnnotation(nonNull(annotation)));
                }

                @Override
                public MethodAnnotationTarget<S> annotateParameter(int parameterIndex, Iterable<? extends Annotation> annotations) {
                    return annotateParameter(parameterIndex, new AnnotationList.ForLoadedAnnotation(toList(annotations)));
                }

                @Override
                public MethodAnnotationTarget<S> annotateParameter(int parameterIndex, AnnotationDescription... annotation) {
                    return annotateParameter(parameterIndex, Arrays.asList(nonNull(annotation)));
                }

                @Override
                public MethodAnnotationTarget<S> annotateParameter(int parameterIndex, Collection<? extends AnnotationDescription> annotations) {
                    return attribute(new MethodAttributeAppender.ForAnnotation(parameterIndex, nonNull(new ArrayList<AnnotationDescription>(annotations))));
                }

                @Override
                @SuppressWarnings("unchecked")
                public boolean equals(Object other) {
                    if (this == other)
                        return true;
                    if (other == null || getClass() != other.getClass())
                        return false;
                    DefaultMethodAnnotationTarget that = (DefaultMethodAnnotationTarget) other;
                    return attributeAppenderFactory.equals(that.attributeAppenderFactory)
                            && handler.equals(that.handler)
                            && methodMatcher.equals(that.methodMatcher)
                            && methodTokens.equals(that.methodTokens)
                            && AbstractBase.this.equals(that.getDynamicTypeBuilder());
                }

                @Override
                public int hashCode() {
                    int result = methodTokens.hashCode();
                    result = 31 * result + methodMatcher.hashCode();
                    result = 31 * result + handler.hashCode();
                    result = 31 * result + attributeAppenderFactory.hashCode();
                    result = 31 * result + AbstractBase.this.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "DynamicType.Builder.AbstractBase.DefaultMethodAnnotationTarget{" +
                            "base=" + AbstractBase.this +
                            ", methodTokens=" + methodTokens +
                            ", methodMatcher=" + methodMatcher +
                            ", handler=" + handler +
                            ", attributeAppenderFactory=" + attributeAppenderFactory +
                            '}';
                }

                /**
                 * Returns the outer instance.
                 *
                 * @return The outer instance.
                 */
                private Builder<?> getDynamicTypeBuilder() {
                    return AbstractBase.this;
                }
            }

            /**
             * Allows for the direct implementation of an interface after its implementation was specified.
             */
            protected class DefaultOptionalMatchedMethodInterception extends AbstractDelegatingBuilder<S> implements OptionalMatchedMethodInterception<S> {

                /**
                 * A list of all interfaces to implement.
                 */
                private List<TypeDescription> additionalInterfaceTypes;

                /**
                 * Creates a new subclass optional matched method interception.
                 *
                 * @param interfaceTypes An array of all interfaces to implement.
                 */
                protected DefaultOptionalMatchedMethodInterception(List<TypeDescription> interfaceTypes) {
                    additionalInterfaceTypes = interfaceTypes;
                }

                @Override
                public MethodAnnotationTarget<S> intercept(Implementation implementation) {
                    return materialize().method(isDeclaredBy(anyOf(additionalInterfaceTypes))).intercept(nonNull(implementation));
                }

                @Override
                public MethodAnnotationTarget<S> withoutCode() {
                    return materialize().method(isDeclaredBy(anyOf(additionalInterfaceTypes))).withoutCode();
                }

                @Override
                public MethodAnnotationTarget<S> withDefaultValue(Object value, Class<?> type) {
                    return materialize().method(isDeclaredBy(anyOf(additionalInterfaceTypes))).withDefaultValue(value, type);
                }

                @Override
                public MethodAnnotationTarget<S> withDefaultValue(Object value) {
                    return materialize().method(isDeclaredBy(anyOf(additionalInterfaceTypes))).withDefaultValue(value);
                }

                @Override
                protected DynamicType.Builder<S> materialize() {
                    return AbstractBase.this.materialize(classFileVersion,
                            namingStrategy,
                            auxiliaryTypeNamingStrategy,
                            targetType,
                            joinUniqueRaw(interfaceTypes, additionalInterfaceTypes),
                            modifiers,
                            attributeAppender,
                            ignoredMethods,
                            bridgeMethodResolverFactory,
                            classVisitorWrapperChain,
                            fieldRegistry,
                            methodRegistry,
                            methodLookupEngineFactory,
                            defaultFieldAttributeAppenderFactory,
                            defaultMethodAttributeAppenderFactory,
                            fieldTokens,
                            methodTokens);
                }

                /**
                 * Returns the outer instance.
                 *
                 * @return The outer instance.
                 */
                private DynamicType.Builder<?> getDynamicTypeBuilder() {
                    return AbstractBase.this;
                }

                @Override
                @SuppressWarnings("unchecked")
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (other == null || getClass() != other.getClass()) return false;
                    DefaultOptionalMatchedMethodInterception that = (DefaultOptionalMatchedMethodInterception) other;
                    return additionalInterfaceTypes.equals(that.additionalInterfaceTypes)
                            && AbstractBase.this.equals(that.getDynamicTypeBuilder());
                }

                @Override
                public int hashCode() {
                    return 31 * AbstractBase.this.hashCode() + additionalInterfaceTypes.hashCode();
                }

                @Override
                public String toString() {
                    return "DynamicType.Builder.AbstractBase.DefaultOptionalMatchedMethodInterception{" +
                            "base=" + AbstractBase.this +
                            "additionalInterfaceTypes=" + additionalInterfaceTypes +
                            '}';
                }
            }
        }
    }

    /**
     * A dynamic type that has been loaded into the running instance of the Java virtual machine.
     *
     * @param <T> The most specific known loaded type that is implemented by this dynamic type, usually the
     *            type itself, an interface or the direct super class.
     */
    interface Loaded<T> extends DynamicType {

        /**
         * Returns the loaded main class.
         *
         * @return A loaded class representation of this dynamic type.
         */
        Class<? extends T> getLoaded();

        /**
         * <p>
         * Returns a map of all loaded auxiliary types to this dynamic type.
         * </p>
         * <p>
         * <b>Note</b>: The type descriptions will most likely differ from the binary representation of this type.
         * Normally, annotations and intercepted methods are not added to the type descriptions of auxiliary types.
         * </p>
         *
         * @return A mapping from the fully qualified names of all auxiliary types to their loaded class representations.
         */
        Map<TypeDescription, Class<?>> getLoadedAuxiliaryTypes();
    }

    /**
     * A dynamic type that has not yet been loaded by a given {@link java.lang.ClassLoader}.
     *
     * @param <T> The most specific known loaded type that is implemented by this dynamic type, usually the
     *            type itself, an interface or the direct super class.
     */
    interface Unloaded<T> extends DynamicType {

        /**
         * Attempts to load this dynamic type including all of its auxiliary types, if any.
         *
         * @param classLoader          The class loader to use for this class loading.
         * @param classLoadingStrategy The class loader strategy which should be used for this class loading.
         * @return This dynamic type in its loaded state.
         * @see net.bytebuddy.dynamic.loading.ClassLoadingStrategy.Default
         */
        Loaded<T> load(ClassLoader classLoader, ClassLoadingStrategy classLoadingStrategy);
    }

    /**
     * A default implementation of a dynamic type.
     */
    class Default implements DynamicType {

        /**
         * The file name extension for Java class files.
         */
        private static final String CLASS_FILE_EXTENSION = ".class";

        /**
         * The size of a writing buffer.
         */
        private static final int BUFFER_SIZE = 1024;

        /**
         * A convenience index for the beginning of an array to improve the readability of the code.
         */
        private static final int FROM_BEGINNING = 0;

        /**
         * A convenience representative of an {@link java.io.InputStream}'s end to improve the readability of the code.
         */
        private static final int END_OF_FILE = -1;

        /**
         * A suffix for temporary files.
         */
        private static final String TEMP_SUFFIX = "tmp";

        /**
         * A type description of this dynamic type.
         */
        protected final TypeDescription typeDescription;

        /**
         * The byte array representing this dynamic type.
         */
        protected final byte[] binaryRepresentation;

        /**
         * The loaded type initializer for this dynamic type.
         */
        protected final LoadedTypeInitializer loadedTypeInitializer;

        /**
         * A list of auxiliary types for this dynamic type.
         */
        protected final List<? extends DynamicType> auxiliaryTypes;

        /**
         * Creates a new dynamic type.
         *
         * @param typeDescription       A description of this dynamic type.
         * @param binaryRepresentation  A byte array containing the binary representation of this dynamic type.
         * @param loadedTypeInitializer The loaded type initializer of this dynamic type.
         * @param auxiliaryTypes        The auxiliary type required for this dynamic type.
         */
        public Default(TypeDescription typeDescription,
                       byte[] binaryRepresentation,
                       LoadedTypeInitializer loadedTypeInitializer,
                       List<? extends DynamicType> auxiliaryTypes) {
            this.typeDescription = typeDescription;
            this.binaryRepresentation = binaryRepresentation;
            this.loadedTypeInitializer = loadedTypeInitializer;
            this.auxiliaryTypes = auxiliaryTypes;
        }

        @Override
        public TypeDescription getTypeDescription() {
            return typeDescription;
        }

        @Override
        public Map<TypeDescription, byte[]> getAllTypes() {
            Map<TypeDescription, byte[]> allTypes = new HashMap<TypeDescription, byte[]>(auxiliaryTypes.size() + 1);
            for (DynamicType auxiliaryType : auxiliaryTypes) {
                allTypes.putAll(auxiliaryType.getAllTypes());
            }
            allTypes.put(typeDescription, binaryRepresentation);
            return allTypes;
        }

        @Override
        public Map<TypeDescription, LoadedTypeInitializer> getLoadedTypeInitializers() {
            Map<TypeDescription, LoadedTypeInitializer> classLoadingCallbacks = new HashMap<TypeDescription, LoadedTypeInitializer>(
                    auxiliaryTypes.size() + 1);
            for (DynamicType auxiliaryType : auxiliaryTypes) {
                classLoadingCallbacks.putAll(auxiliaryType.getLoadedTypeInitializers());
            }
            classLoadingCallbacks.put(typeDescription, loadedTypeInitializer);
            return classLoadingCallbacks;
        }

        @Override
        public boolean hasAliveLoadedTypeInitializers() {
            for (LoadedTypeInitializer loadedTypeInitializer : getLoadedTypeInitializers().values()) {
                if (loadedTypeInitializer.isAlive()) {
                    return true;
                }
            }
            return false;
        }

        @Override
        public byte[] getBytes() {
            return binaryRepresentation;
        }

        @Override
        public Map<TypeDescription, byte[]> getRawAuxiliaryTypes() {
            Map<TypeDescription, byte[]> auxiliaryTypes = new HashMap<TypeDescription, byte[]>();
            for (DynamicType auxiliaryType : this.auxiliaryTypes) {
                auxiliaryTypes.put(auxiliaryType.getTypeDescription(), auxiliaryType.getBytes());
                auxiliaryTypes.putAll(auxiliaryType.getRawAuxiliaryTypes());
            }
            return auxiliaryTypes;
        }

        @Override
        public Map<TypeDescription, File> saveIn(File folder) throws IOException {
            Map<TypeDescription, File> savedFiles = new HashMap<TypeDescription, File>();
            File target = new File(folder, typeDescription.getName().replace('.', File.separatorChar) + CLASS_FILE_EXTENSION);
            if (target.getParentFile() != null) {
                target.getParentFile().mkdirs();
            }
            OutputStream outputStream = new FileOutputStream(target);
            try {
                outputStream.write(binaryRepresentation);
            } finally {
                outputStream.close();
            }
            savedFiles.put(typeDescription, target);
            for (DynamicType auxiliaryType : auxiliaryTypes) {
                savedFiles.putAll(auxiliaryType.saveIn(folder));
            }
            return savedFiles;
        }

        @Override
        public File inject(File sourceJar, File targetJar) throws IOException {
            JarInputStream jarInputStream = new JarInputStream(new BufferedInputStream(new FileInputStream(sourceJar)));
            try {
                targetJar.createNewFile();
                JarOutputStream jarOutputStream = new JarOutputStream(new BufferedOutputStream(new FileOutputStream(targetJar)), jarInputStream.getManifest());
                try {
                    Map<TypeDescription, byte[]> rawAuxiliaryTypes = getRawAuxiliaryTypes();
                    Map<String, byte[]> files = new HashMap<String, byte[]>(rawAuxiliaryTypes.size() + 1);
                    for (Map.Entry<TypeDescription, byte[]> entry : rawAuxiliaryTypes.entrySet()) {
                        files.put(entry.getKey().getInternalName() + CLASS_FILE_EXTENSION, entry.getValue());
                    }
                    files.put(typeDescription.getInternalName() + CLASS_FILE_EXTENSION, binaryRepresentation);
                    JarEntry jarEntry;
                    while ((jarEntry = jarInputStream.getNextJarEntry()) != null) {
                        jarOutputStream.putNextEntry(jarEntry);
                        byte[] replacement = files.remove(jarEntry.getName());
                        if (replacement == null) {
                            byte[] buffer = new byte[BUFFER_SIZE];
                            int index;
                            while ((index = jarInputStream.read(buffer)) != END_OF_FILE) {
                                jarOutputStream.write(buffer, FROM_BEGINNING, index);
                            }
                        } else {
                            jarOutputStream.write(replacement);
                        }
                        jarInputStream.closeEntry();
                        jarOutputStream.closeEntry();
                    }
                    for (Map.Entry<String, byte[]> entry : files.entrySet()) {
                        jarOutputStream.putNextEntry(new JarEntry(entry.getKey()));
                        jarOutputStream.write(entry.getValue());
                        jarOutputStream.closeEntry();
                    }
                } finally {
                    jarOutputStream.close();
                }
            } finally {
                jarInputStream.close();
            }
            return targetJar;
        }

        @Override
        public File inject(File jar) throws IOException {
            File temporary = inject(jar, File.createTempFile(jar.getName(), TEMP_SUFFIX));
            try {
                InputStream jarInputStream = new BufferedInputStream(new FileInputStream(temporary));
                try {
                    OutputStream jarOutputStream = new BufferedOutputStream(new FileOutputStream(jar));
                    try {
                        byte[] buffer = new byte[BUFFER_SIZE];
                        int index;
                        while ((index = jarInputStream.read(buffer)) != END_OF_FILE) {
                            jarOutputStream.write(buffer, FROM_BEGINNING, index);
                        }
                    } finally {
                        jarOutputStream.close();
                    }
                } finally {
                    jarInputStream.close();
                }
            } finally {
                if (!temporary.delete()) {
                    Logger.getAnonymousLogger().warning("Cannot delete " + temporary);
                }
            }
            return jar;
        }

        @Override
        public File toJar(File file, Manifest manifest) throws IOException {
            file.createNewFile();
            JarOutputStream outputStream = new JarOutputStream(new BufferedOutputStream(new FileOutputStream(file)), manifest);
            try {
                for (Map.Entry<TypeDescription, byte[]> entry : getRawAuxiliaryTypes().entrySet()) {
                    outputStream.putNextEntry(new JarEntry(entry.getKey().getInternalName() + CLASS_FILE_EXTENSION));
                    outputStream.write(entry.getValue());
                    outputStream.closeEntry();
                }
                outputStream.putNextEntry(new JarEntry(typeDescription.getInternalName() + CLASS_FILE_EXTENSION));
                outputStream.write(binaryRepresentation);
                outputStream.closeEntry();
            } finally {
                outputStream.close();
            }
            return file;
        }

        @Override
        public boolean equals(Object other) {
            if (this == other)
                return true;
            if (other == null || getClass() != other.getClass())
                return false;
            Default aDefault = (Default) other;
            return auxiliaryTypes.equals(aDefault.auxiliaryTypes)
                    && Arrays.equals(binaryRepresentation, aDefault.binaryRepresentation)
                    && typeDescription.equals(aDefault.typeDescription)
                    && loadedTypeInitializer.equals(aDefault.loadedTypeInitializer);

        }

        @Override
        public int hashCode() {
            int result = typeDescription.hashCode();
            result = 31 * result + Arrays.hashCode(binaryRepresentation);
            result = 31 * result + loadedTypeInitializer.hashCode();
            result = 31 * result + auxiliaryTypes.hashCode();
            return result;
        }

        @Override
        public String toString() {
            return "DynamicType.Default{" +
                    "typeDescription='" + typeDescription + '\'' +
                    ", binaryRepresentation=<" + binaryRepresentation.length + " bytes>" +
                    ", loadedTypeInitializer=" + loadedTypeInitializer +
                    ", auxiliaryTypes=" + auxiliaryTypes +
                    '}';
        }

        /**
         * A default implementation of an unloaded dynamic type.
         *
         * @param <T> The most specific known loaded type that is implemented by this dynamic type, usually the
         *            type itself, an interface or the direct super class.
         */
        public static class Unloaded<T> extends Default implements DynamicType.Unloaded<T> {

            /**
             * Creates a new unloaded representation of a dynamic type.
             *
             * @param typeDescription       A description of this dynamic type.
             * @param typeByte              An array of byte of the binary representation of this dynamic type.
             * @param loadedTypeInitializer The type initializer of this dynamic type.
             * @param auxiliaryTypes        The auxiliary types that are required for this dynamic type.
             */
            public Unloaded(TypeDescription typeDescription,
                            byte[] typeByte,
                            LoadedTypeInitializer loadedTypeInitializer,
                            List<? extends DynamicType> auxiliaryTypes) {
                super(typeDescription, typeByte, loadedTypeInitializer, auxiliaryTypes);
            }

            @Override
            public DynamicType.Loaded<T> load(ClassLoader classLoader, ClassLoadingStrategy classLoadingStrategy) {
                LinkedHashMap<TypeDescription, byte[]> types = new LinkedHashMap<TypeDescription, byte[]>(
                        getRawAuxiliaryTypes());
                types.put(typeDescription, binaryRepresentation);
                return new Default.Loaded<T>(typeDescription,
                        binaryRepresentation,
                        loadedTypeInitializer,
                        auxiliaryTypes,
                        initialize(classLoadingStrategy.load(classLoader, types)));
            }

            /**
             * Runs all loaded type initializers for all loaded classes.
             *
             * @param uninitialized The uninitialized loaded classes mapped by their type description.
             * @return A new hash map that contains the same classes as those given.
             */
            private Map<TypeDescription, Class<?>> initialize(Map<TypeDescription, Class<?>> uninitialized) {
                Map<TypeDescription, LoadedTypeInitializer> typeInitializers = getLoadedTypeInitializers();
                for (Map.Entry<TypeDescription, Class<?>> entry : uninitialized.entrySet()) {
                    typeInitializers.get(entry.getKey()).onLoad(entry.getValue());
                }
                return new HashMap<TypeDescription, Class<?>>(uninitialized);
            }

            @Override
            public String toString() {
                return "DynamicType.Default.Unloaded{" +
                        "typeDescription='" + typeDescription + '\'' +
                        ", binaryRepresentation=<" + binaryRepresentation.length + " bytes>" +
                        ", typeInitializer=" + loadedTypeInitializer +
                        ", auxiliaryTypes=" + auxiliaryTypes +
                        '}';
            }
        }

        /**
         * A default implementation of a loaded dynamic type.
         *
         * @param <T> The most specific known loaded type that is implemented by this dynamic type, usually the
         *            type itself, an interface or the direct super class.
         */
        protected static class Loaded<T> extends Default implements DynamicType.Loaded<T> {

            /**
             * The loaded types for the given loaded dynamic type.
             */
            private final Map<TypeDescription, Class<?>> loadedTypes;

            /**
             * Creates a new representation of a loaded dynamic type.
             *
             * @param typeDescription       A description of this dynamic type.
             * @param typeByte              An array of byte of the binary representation of this dynamic type.
             * @param loadedTypeInitializer The type initializer of this dynamic type.
             * @param auxiliaryTypes        The auxiliary types that are required for this dynamic type.
             * @param loadedTypes           A map of loaded types for this dynamic type and all its auxiliary types.
             */
            protected Loaded(TypeDescription typeDescription,
                             byte[] typeByte,
                             LoadedTypeInitializer loadedTypeInitializer,
                             List<? extends DynamicType> auxiliaryTypes,
                             Map<TypeDescription, Class<?>> loadedTypes) {
                super(typeDescription, typeByte, loadedTypeInitializer, auxiliaryTypes);
                this.loadedTypes = loadedTypes;
            }

            @Override
            @SuppressWarnings("unchecked")
            public Class<? extends T> getLoaded() {
                return (Class<? extends T>) loadedTypes.get(typeDescription);
            }

            @Override
            public Map<TypeDescription, Class<?>> getLoadedAuxiliaryTypes() {
                Map<TypeDescription, Class<?>> loadedAuxiliaryTypes = new HashMap<TypeDescription, Class<?>>(
                        loadedTypes);
                loadedAuxiliaryTypes.remove(typeDescription);
                return loadedAuxiliaryTypes;
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && super.equals(other) && loadedTypes.equals(((Default.Loaded) other).loadedTypes);
            }

            @Override
            public int hashCode() {
                return 31 * super.hashCode() + loadedTypes.hashCode();
            }

            @Override
            public String toString() {
                return "DynamicType.Default.Loaded{" +
                        "typeDescription='" + typeDescription + '\'' +
                        ", binaryRepresentation=<" + binaryRepresentation.length + " bytes>" +
                        ", typeInitializer=" + loadedTypeInitializer +
                        ", auxiliaryTypes=" + auxiliaryTypes +
                        ", loadedTypes=" + loadedTypes +
                        '}';
            }
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/dynamic/TargetType.java
package net.bytebuddy.dynamic;

import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeList;
import net.bytebuddy.description.type.generic.TypeVariableSource;
import net.bytebuddy.matcher.ElementMatcher;

import java.util.ArrayList;
import java.util.List;

import static net.bytebuddy.matcher.ElementMatchers.is;

/**
 * This type is used as a place holder for creating methods or fields that refer to the type that currently subject
 * of creation within a {@link net.bytebuddy.dynamic.DynamicType.Builder}.
 */
public final class TargetType {

    /**
     * A description representation of the {@link net.bytebuddy.dynamic.TargetType}.
     */
    public static final TypeDescription DESCRIPTION = new TypeDescription.ForLoadedType(TargetType.class);

    public static final ElementMatcher<TypeDescription> MATCHER = is(DESCRIPTION);

    /**
     * As the {@link net.bytebuddy.dynamic.TargetType} is only to be used as a marker, its constructor is made inaccessible.
     */
    private TargetType() {
        throw new UnsupportedOperationException("This is a place holder type that should not be instantiated");
    }

    public static TypeDescription resolve(TypeDescription observed,
                                          TypeDescription substitute,
                                          ElementMatcher<? super TypeDescription> substitutionMatcher) {
        int arity = 0;
        TypeDescription componentType = observed;
        while (componentType.isArray()) {
            componentType = componentType.getComponentType();
            arity++;
        }
        return substitutionMatcher.matches(componentType)
                ? TypeDescription.ArrayProjection.of(substitute, arity)
                : observed;
    }

    public static GenericTypeDescription resolve(GenericTypeDescription observed,
                                                 TypeDescription substitute,
                                                 ElementMatcher<? super TypeDescription> substitutionMatcher) {
        switch (observed.getSort()) {
            case RAW:
                return resolve(observed.asRawType(), substitute, substitutionMatcher);
            case GENERIC_ARRAY:
                return GenericTypeDescription.ForGenericArray.Latent.of(resolve(observed.getComponentType(), substitute, substitutionMatcher), 1);
            case PARAMETERIZED:
                GenericTypeDescription ownerType = observed.getOwnerType();
                return new GenericTypeDescription.ForParameterizedType.Latent(resolve(observed.asRawType(), substitute, substitutionMatcher),
                        resolve(observed.getParameters(), substitute, substitutionMatcher),
                        ownerType == null
                                ? null
                                : resolve(ownerType, substitute, substitutionMatcher));
            case WILDCARD:
                GenericTypeList lowerBounds = observed.getLowerBounds(), upperBounds = observed.getUpperBounds();
                return lowerBounds.isEmpty()
                        ? GenericTypeDescription.ForWildcardType.Latent.boundedAbove(resolve(upperBounds.getOnly(), substitute, substitutionMatcher))
                        : GenericTypeDescription.ForWildcardType.Latent.boundedBelow(resolve(lowerBounds.getOnly(), substitute, substitutionMatcher));
            case VARIABLE:
                return observed.getVariableSource().accept(new TypeVariableProxy.Extractor(substitute, substitutionMatcher)).resolve(observed);
            default:
                throw new AssertionError("Unexpected generic type: " + observed.getSort());
        }
    }

    public static GenericTypeList resolve(List<? extends GenericTypeDescription> typeList,
                                          TypeDescription substitute,
                                          ElementMatcher<? super TypeDescription> substitutionMatcher) {
        List<GenericTypeDescription> resolved = new ArrayList<GenericTypeDescription>(typeList.size());
        for (GenericTypeDescription typeDescription : typeList) {
            resolved.add(resolve(typeDescription, substitute, substitutionMatcher));
        }
        return new GenericTypeList.Explicit(resolved);
    }

    protected interface TypeVariableProxy {

        GenericTypeDescription resolve(GenericTypeDescription original);

        enum Retaining implements TypeVariableProxy {

            INSTANCE;

            @Override
            public GenericTypeDescription resolve(GenericTypeDescription original) {
                return original;
            }
        }

        class ForType implements TypeVariableProxy {

            private final TypeDescription substitute;

            public ForType(TypeDescription substitute) {
                this.substitute = substitute;
            }

            @Override
            public GenericTypeDescription resolve(GenericTypeDescription original) {
                // TODO: Lazy!
                GenericTypeDescription typeVariable = substitute.findVariable(original.getSymbol());
                if (typeVariable == null) {
                    throw new IllegalStateException("Cannot resolve type variable " + original.getSymbol() + " for " + substitute);
                }
                return typeVariable;
            }
        }

        class ForMethod implements TypeVariableProxy {

            private final TypeDescription substitute;

            private final MethodDescription methodDescription;

            public ForMethod(TypeDescription substitute, MethodDescription methodDescription) {
                this.substitute = substitute;
                this.methodDescription = methodDescription; // TODO: Not method description, rather raw resolved look up.
            }

            @Override
            public GenericTypeDescription resolve(GenericTypeDescription original) {
                // TODO: Lazy!
                GenericTypeDescription typeVariable = substitute.getDeclaredMethods().filter(is(methodDescription))
                        .getOnly()
                        .findVariable(original.getSymbol());
                if (typeVariable == null) {
                    throw new IllegalStateException("Cannot resolve type variable " + original.getSymbol() + " for " + methodDescription);
                }
                return typeVariable;
            }
        }

        class Extractor implements TypeVariableSource.Visitor<TypeVariableProxy> {

            private final TypeDescription substitute;

            private final ElementMatcher<? super TypeDescription> substitutionMatcher;

            public Extractor(TypeDescription substitute, ElementMatcher<? super TypeDescription> substitutionMatcher) {
                this.substitute = substitute;
                this.substitutionMatcher = substitutionMatcher;
            }

            @Override
            public TypeVariableProxy onType(TypeDescription typeDescription) {
                return substitutionMatcher.matches(typeDescription)
                        ? new TypeVariableProxy.ForType(substitute)
                        : Retaining.INSTANCE;
            }

            @Override
            public TypeVariableProxy onMethod(MethodDescription methodDescription) {
                return substitutionMatcher.matches(methodDescription.getDeclaringType())
                        ? new TypeVariableProxy.ForMethod(substitute, methodDescription)
                        : Retaining.INSTANCE;
            }
        }
    }

    // TODO: Make resolution lazy for generic types.
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/dynamic/scaffold/InstrumentedType.java
package net.bytebuddy.dynamic.scaffold;

import net.bytebuddy.description.annotation.AnnotationDescription;
import net.bytebuddy.description.annotation.AnnotationList;
import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.field.FieldList;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.method.MethodList;
import net.bytebuddy.description.method.ParameterDescription;
import net.bytebuddy.description.method.ParameterList;
import net.bytebuddy.description.type.PackageDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeList;
import net.bytebuddy.description.type.generic.TypeVariableSource;
import net.bytebuddy.dynamic.TargetType;
import net.bytebuddy.implementation.Implementation;
import net.bytebuddy.implementation.LoadedTypeInitializer;
import net.bytebuddy.implementation.bytecode.ByteCodeAppender;
import net.bytebuddy.implementation.bytecode.member.MethodReturn;
import net.bytebuddy.matcher.ElementMatcher;
import org.objectweb.asm.MethodVisitor;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Implementations of this interface represent an instrumented type that is subject to change. Implementations
 * should however be immutable and return new instance when their mutator methods are called.
 */
public interface InstrumentedType extends TypeDescription {

    /**
     * Creates a new instrumented type that includes a new field.
     *
     * @param internalName The internal name of the new field.
     * @param fieldType    A description of the type of the new field.
     * @param modifiers    The modifier of the new field.
     * @return A new instrumented type that is equal to this instrumented type but with the additional field.
     */
    InstrumentedType withField(String internalName,
                               GenericTypeDescription fieldType,
                               int modifiers);

    /**
     * Creates a new instrumented type that includes a new method or constructor.
     *
     * @param internalName   The internal name of the new field.
     * @param returnType     A description of the return type of the new field.
     * @param parameterTypes A list of descriptions of the parameter types.
     * @param exceptionTypes A list of descriptions of the exception types that are declared by this method.
     * @param modifiers      The modifier of the new field.
     * @return A new instrumented type that is equal to this instrumented type but with the additional field.
     */
    InstrumentedType withMethod(String internalName,
                                GenericTypeDescription returnType,
                                List<? extends GenericTypeDescription> parameterTypes,
                                List<? extends GenericTypeDescription> exceptionTypes,
                                int modifiers);

    /**
     * Creates a new instrumented type that includes the given {@link net.bytebuddy.implementation.LoadedTypeInitializer}.
     *
     * @param loadedTypeInitializer The type initializer to include.
     * @return A new instrumented type that is equal to this instrumented type but with the additional type initializer.
     */
    InstrumentedType withInitializer(LoadedTypeInitializer loadedTypeInitializer);

    /**
     * Creates a new instrumented type that executes the given initializer in the instrumented type's
     * type initializer.
     *
     * @param byteCodeAppender The byte code to add to the type initializer.
     * @return A new instrumented type that is equal to this instrumented type but with the given stack manipulation
     * attached to its type initializer.
     */
    InstrumentedType withInitializer(ByteCodeAppender byteCodeAppender);

    /**
     * Returns the {@link net.bytebuddy.implementation.LoadedTypeInitializer}s that were registered
     * for this instrumented type.
     *
     * @return The registered loaded type initializers for this instrumented type.
     */
    LoadedTypeInitializer getLoadedTypeInitializer();

    /**
     * Returns this instrumented type's type initializer.
     *
     * @return This instrumented type's type initializer.
     */
    TypeInitializer getTypeInitializer();

    /**
     * A type initializer is responsible for defining a type's static initialization block.
     */
    interface TypeInitializer extends ByteCodeAppender {

        /**
         * Indicates if this type initializer is defined.
         *
         * @return {@code true} if this type initializer is defined.
         */
        boolean isDefined();

        /**
         * Expands this type initializer with another byte code appender. For this to be possible, this type initializer must
         * be defined.
         *
         * @param byteCodeAppender The byte code appender to apply within the type initializer.
         * @return A defined type initializer.
         */
        TypeInitializer expandWith(ByteCodeAppender byteCodeAppender);

        /**
         * Returns this type initializer with an ending return statement. For this to be possible, this type initializer must
         * be defined.
         *
         * @return This type initializer with an ending return statement.
         */
        ByteCodeAppender withReturn();

        /**
         * Canonical implementation of a non-defined type initializer.
         */
        enum None implements TypeInitializer {

            /**
             * The singleton instance.
             */
            INSTANCE;

            @Override
            public boolean isDefined() {
                return false;
            }

            @Override
            public TypeInitializer expandWith(ByteCodeAppender byteCodeAppender) {
                return new TypeInitializer.Simple(byteCodeAppender);
            }

            @Override
            public ByteCodeAppender withReturn() {
                throw new IllegalStateException("Cannot append return to non-defined type initializer");
            }

            @Override
            public Size apply(MethodVisitor methodVisitor, Implementation.Context implementationContext, MethodDescription instrumentedMethod) {
                throw new IllegalStateException("Cannot apply a non-defined type initializer");
            }

            @Override
            public String toString() {
                return "InstrumentedType.TypeInitializer.None." + name();
            }
        }

        /**
         * A simple, defined type initializer that executes a given {@link net.bytebuddy.implementation.bytecode.ByteCodeAppender}.
         */
        class Simple implements TypeInitializer {

            /**
             * The stack manipulation to apply within the type initializer.
             */
            private final ByteCodeAppender byteCodeAppender;

            /**
             * Creates a new simple type initializer.
             *
             * @param byteCodeAppender The byte code appender manipulation to apply within the type initializer.
             */
            public Simple(ByteCodeAppender byteCodeAppender) {
                this.byteCodeAppender = byteCodeAppender;
            }

            @Override
            public boolean isDefined() {
                return true;
            }

            @Override
            public TypeInitializer expandWith(ByteCodeAppender byteCodeAppender) {
                return new TypeInitializer.Simple(new ByteCodeAppender.Compound(this.byteCodeAppender, byteCodeAppender));
            }

            @Override
            public ByteCodeAppender withReturn() {
                return new ByteCodeAppender.Compound(byteCodeAppender, new ByteCodeAppender.Simple(MethodReturn.VOID));
            }

            @Override
            public Size apply(MethodVisitor methodVisitor, Implementation.Context implementationContext, MethodDescription instrumentedMethod) {
                return byteCodeAppender.apply(methodVisitor, implementationContext, instrumentedMethod);
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && byteCodeAppender.equals(((TypeInitializer.Simple) other).byteCodeAppender);
            }

            @Override
            public int hashCode() {
                return byteCodeAppender.hashCode();
            }

            @Override
            public String toString() {
                return "InstrumentedType.TypeInitializer.Simple{" +
                        "byteCodeAppender=" + byteCodeAppender +
                        '}';
            }
        }
    }

    /**
     * An abstract base implementation of an instrumented type.
     */
    abstract class AbstractBase extends AbstractTypeDescription.OfSimpleType implements InstrumentedType {

        /**
         * The loaded type initializer for this instrumented type.
         */
        protected final LoadedTypeInitializer loadedTypeInitializer;

        /**
         * The type initializer for this instrumented type.
         */
        protected final TypeInitializer typeInitializer;

        protected final List<GenericTypeDescription> typeVariables;

        /**
         * A list of field descriptions registered for this instrumented type.
         */
        protected final List<FieldDescription> fieldDescriptions;

        /**
         * A list of method descriptions registered for this instrumented type.
         */
        protected final List<MethodDescription> methodDescriptions;

        /**
         * Creates a new instrumented type with a no-op loaded type initializer and without registered fields or
         * methods.
         */
        protected AbstractBase() {
            loadedTypeInitializer = LoadedTypeInitializer.NoOp.INSTANCE;
            typeInitializer = TypeInitializer.None.INSTANCE;
            typeVariables = Collections.emptyList();
            fieldDescriptions = Collections.emptyList();
            methodDescriptions = Collections.emptyList();
        }

        protected AbstractBase(LoadedTypeInitializer loadedTypeInitializer,
                               TypeInitializer typeInitializer,
                               ElementMatcher<? super TypeDescription> matcher,
                               List<? extends GenericTypeDescription> typeVariables,
                               List<? extends FieldDescription> fieldDescriptions,
                               List<? extends MethodDescription> methodDescriptions) {
            this.loadedTypeInitializer = loadedTypeInitializer;
            this.typeInitializer = typeInitializer;
            this.typeVariables = new ArrayList<GenericTypeDescription>(typeVariables.size());
            for (GenericTypeDescription typeVariable : typeVariables) {
                this.typeVariables.add(new TypeVariableToken(matcher, typeVariable));
            }
            this.fieldDescriptions = new ArrayList<FieldDescription>(fieldDescriptions.size());
            for (FieldDescription fieldDescription : fieldDescriptions) {
                this.fieldDescriptions.add(new FieldToken(matcher, fieldDescription));
            }
            this.methodDescriptions = new ArrayList<MethodDescription>(methodDescriptions.size());
            for (MethodDescription methodDescription : methodDescriptions) {
                this.methodDescriptions.add(new MethodToken(matcher, methodDescription));
            }
        }

        @Override
        public MethodDescription getEnclosingMethod() {
            return null;
        }

        @Override
        public TypeDescription getEnclosingType() {
            return null;
        }

        @Override
        public TypeDescription getDeclaringType() {
            return null;
        }

        @Override
        public boolean isAnonymousClass() {
            return false;
        }

        @Override
        public String getCanonicalName() {
            return getName();
        }

        @Override
        public boolean isLocalClass() {
            return false;
        }

        @Override
        public boolean isMemberClass() {
            return false;
        }

        @Override
        public GenericTypeList getTypeVariables() {
            return new GenericTypeList.Explicit(typeVariables);
        }

        @Override
        public FieldList getDeclaredFields() {
            return new FieldList.Explicit(fieldDescriptions);
        }

        @Override
        public MethodList getDeclaredMethods() {
            return new MethodList.Explicit(methodDescriptions);
        }

        @Override
        public LoadedTypeInitializer getLoadedTypeInitializer() {
            return loadedTypeInitializer;
        }

        @Override
        public TypeInitializer getTypeInitializer() {
            return typeInitializer;
        }

        @Override
        public PackageDescription getPackage() {
            String packageName = getPackageName();
            return packageName == null
                    ? null
                    : new PackageDescription.Simple(packageName);
        }

        protected class TypeVariableToken extends GenericTypeDescription.ForTypeVariable {

            private final String symbol;

            private final List<GenericTypeDescription> bounds;

            private TypeVariableToken(ElementMatcher<? super TypeDescription> matcher, GenericTypeDescription typeVariable) {
                symbol = typeVariable.getSymbol();
                bounds = null; // TODO!
//                bounds = TargetType.resolve(typeVariable.getUpperBounds(), AbstractBase.this, matcher);
            }

            @Override
            public GenericTypeList getUpperBounds() {
                return new GenericTypeList.Explicit(bounds);
            }

            @Override
            public TypeVariableSource getVariableSource() {
                return AbstractBase.this;
            }

            @Override
            public String getSymbol() {
                return symbol;
            }
        }

        /**
         * An implementation of a new field for the enclosing instrumented type.
         */
        protected class FieldToken extends FieldDescription.AbstractFieldDescription {

            /**
             * The name of the field token.
             */
            private final String name;

            /**
             * The type of the field.
             */
            private final GenericTypeDescription fieldType;

            /**
             * The modifiers of the field.
             */
            private final int modifiers;

            /**
             * The declared annotations of this field.
             */
            private final List<AnnotationDescription> declaredAnnotations;

            private FieldToken(ElementMatcher<? super TypeDescription> matcher, FieldDescription fieldDescription) {
                name = fieldDescription.getName();
                fieldType = TargetType.resolve(fieldDescription.getFieldTypeGen(), AbstractBase.this, matcher);
                modifiers = fieldDescription.getModifiers();
                declaredAnnotations = fieldDescription.getDeclaredAnnotations();
            }

            @Override
            public GenericTypeDescription getFieldTypeGen() {
                return fieldType;
            }

            @Override
            public AnnotationList getDeclaredAnnotations() {
                return new AnnotationList.Explicit(declaredAnnotations);
            }

            @Override
            public String getName() {
                return name;
            }

            @Override
            public TypeDescription getDeclaringType() {
                return AbstractBase.this;
            }

            @Override
            public int getModifiers() {
                return modifiers;
            }
        }

        /**
         * An implementation of a new method or constructor for the enclosing instrumented type.
         */
        protected class MethodToken extends MethodDescription.AbstractMethodDescription {

            /**
             * The internal name of the represented method.
             */
            private final String internalName;

            private final List<GenericTypeDescription> typeVariables;

            /**
             * The return type of the represented method.
             */
            private final GenericTypeDescription returnType;

            /**
             * The exception types of the represented method.
             */
            private final List<GenericTypeDescription> exceptionTypes;

            /**
             * The modifiers of the represented method.
             */
            private final int modifiers;

            /**
             * The declared annotations of this method.
             */
            private final List<AnnotationDescription> declaredAnnotations;

            /**
             * A list of descriptions of the method's parameters.
             */
            private final List<ParameterDescription> parameters;

            /**
             * The default value of this method or {@code null} if no such value exists.
             */
            private final Object defaultValue;

            private MethodToken(ElementMatcher<? super TypeDescription> matcher, MethodDescription methodDescription) {
                internalName = methodDescription.getInternalName();
                typeVariables = new ArrayList<GenericTypeDescription>(methodDescription.getTypeVariables().size());
                for (GenericTypeDescription typeVariable : methodDescription.getTypeVariables()) {
                    typeVariables.add(new TypeVariableToken(matcher, typeVariable));
                }
                returnType = TargetType.resolve(methodDescription.getReturnTypeGen(), AbstractBase.this, matcher);
                exceptionTypes = TargetType.resolve(methodDescription.getExceptionTypesGen(), AbstractBase.this, matcher);
                modifiers = methodDescription.getModifiers();
                declaredAnnotations = methodDescription.getDeclaredAnnotations();
                parameters = new ArrayList<ParameterDescription>(methodDescription.getParameters().size());
                for (ParameterDescription parameterDescription : methodDescription.getParameters()) {
                    parameters.add(new ParameterToken(matcher, parameterDescription));
                }
                defaultValue = methodDescription.getDefaultValue();
            }

            @Override
            public GenericTypeDescription getReturnTypeGen() {
                return returnType;
            }

            @Override
            public GenericTypeList getExceptionTypesGen() {
                return new GenericTypeList.Explicit(exceptionTypes);
            }

            @Override
            public ParameterList getParameters() {
                return new ParameterList.Explicit(parameters);
            }

            @Override
            public AnnotationList getDeclaredAnnotations() {
                return new AnnotationList.Explicit(declaredAnnotations);
            }

            @Override
            public String getInternalName() {
                return internalName;
            }

            @Override
            public TypeDescription getDeclaringType() {
                return AbstractBase.this;
            }

            @Override
            public int getModifiers() {
                return modifiers;
            }

            @Override
            public GenericTypeList getTypeVariables() {
                return new GenericTypeList.Explicit(typeVariables);
            }

            @Override
            public Object getDefaultValue() {
                return defaultValue;
            }

            protected class TypeVariableToken extends GenericTypeDescription.ForTypeVariable {

                private final String symbol;

                private final List<GenericTypeDescription> bounds;

                private TypeVariableToken(ElementMatcher<? super TypeDescription> matcher, GenericTypeDescription typeVariable) {
                    symbol = typeVariable.getSymbol();
                    bounds = TargetType.resolve(typeVariable.getUpperBounds(), AbstractBase.this, matcher);
                }

                @Override
                public GenericTypeList getUpperBounds() {
                    return new GenericTypeList.Explicit(bounds);
                }

                @Override
                public TypeVariableSource getVariableSource() {
                    return MethodToken.this;
                }

                @Override
                public String getSymbol() {
                    return symbol;
                }
            }

            /**
             * An implementation of a method parameter for a method of an instrumented type.
             */
            protected class ParameterToken extends ParameterDescription.AbstractParameterDescription {

                /**
                 * The type of the parameter.
                 */
                private final GenericTypeDescription parameterType;

                /**
                 * The index of the parameter.
                 */
                private final int index;

                /**
                 * The name of the parameter or {@code null} if no explicit name is known for this parameter.
                 */
                private final String name;

                /**
                 * The modifiers of this parameter or {@code null} if no such modifiers are known.
                 */
                private final Integer modifiers;

                /**
                 * The annotations of this parameter.
                 */
                private final List<AnnotationDescription> parameterAnnotations;

                protected ParameterToken(ElementMatcher<? super TypeDescription> matcher, ParameterDescription parameterDescription) {
                    parameterType = TargetType.resolve(parameterDescription.getTypeGen(), AbstractBase.this, matcher);
                    index = parameterDescription.getIndex();
                    name = parameterDescription.isNamed()
                            ? parameterDescription.getName()
                            : null;
                    modifiers = parameterDescription.hasModifiers()
                            ? getModifiers()
                            : null;
                    parameterAnnotations = Collections.emptyList();
                }

                @Override
                public GenericTypeDescription getTypeGen() {
                    return parameterType;
                }

                @Override
                public MethodDescription getDeclaringMethod() {
                    return MethodToken.this;
                }

                @Override
                public int getIndex() {
                    return index;
                }

                @Override
                public boolean isNamed() {
                    return name != null;
                }

                @Override
                public boolean hasModifiers() {
                    return modifiers != null;
                }

                @Override
                public AnnotationList getDeclaredAnnotations() {
                    return new AnnotationList.Explicit(parameterAnnotations);
                }

                @Override
                public int getModifiers() {
                    return hasModifiers()
                            ? modifiers
                            : super.getModifiers();
                }

                @Override
                public String getName() {
                    return isNamed()
                            ? name
                            : super.getName();
                }
            }
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/dynamic/scaffold/TypeWriter.java
package net.bytebuddy.dynamic.scaffold;

import net.bytebuddy.ClassFileVersion;
import net.bytebuddy.asm.ClassVisitorWrapper;
import net.bytebuddy.description.ModifierReviewable;
import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.method.MethodList;
import net.bytebuddy.description.method.ParameterDescription;
import net.bytebuddy.description.method.ParameterList;
import net.bytebuddy.description.type.PackageDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.TypeList;
import net.bytebuddy.dynamic.ClassFileLocator;
import net.bytebuddy.dynamic.DynamicType;
import net.bytebuddy.dynamic.scaffold.inline.MethodRebaseResolver;
import net.bytebuddy.implementation.Implementation;
import net.bytebuddy.implementation.LoadedTypeInitializer;
import net.bytebuddy.implementation.attribute.AnnotationAppender;
import net.bytebuddy.implementation.attribute.FieldAttributeAppender;
import net.bytebuddy.implementation.attribute.MethodAttributeAppender;
import net.bytebuddy.implementation.attribute.TypeAttributeAppender;
import net.bytebuddy.implementation.auxiliary.AuxiliaryType;
import net.bytebuddy.implementation.bytecode.ByteCodeAppender;
import net.bytebuddy.implementation.bytecode.member.MethodInvocation;
import net.bytebuddy.utility.RandomString;
import org.objectweb.asm.*;
import org.objectweb.asm.commons.RemappingClassAdapter;
import org.objectweb.asm.commons.SimpleRemapper;

import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static net.bytebuddy.utility.ByteBuddyCommons.join;

/**
 * A type writer is a utility for writing an actual class file using the ASM library.
 *
 * @param <T> The best known loaded type for the dynamically created type.
 */
public interface TypeWriter<T> {

    /**
     * Creates the dynamic type that is described by this type writer.
     *
     * @return An unloaded dynamic type that describes the created type.
     */
    DynamicType.Unloaded<T> make();

    /**
     * An field pool that allows a lookup for how to implement a field.
     */
    interface FieldPool {

        /**
         * Returns the field attribute appender that matches a given field description or a default field
         * attribute appender if no appender was registered for the given field.
         *
         * @param fieldDescription The field description of interest.
         * @return The registered field attribute appender for the given field or the default appender if no such
         * appender was found.
         */
        Entry target(FieldDescription fieldDescription);

        /**
         * An entry of a field pool that describes how a field is implemented.
         *
         * @see net.bytebuddy.dynamic.scaffold.TypeWriter.FieldPool
         */
        interface Entry {

            /**
             * Returns the field attribute appender for a given field.
             *
             * @return The attribute appender to be applied on the given field.
             */
            FieldAttributeAppender getFieldAppender();

            /**
             * Returns the default value for the field that is represented by this entry. This value might be
             * {@code null} if no such value is set.
             *
             * @return The default value for the field that is represented by this entry.
             */
            Object getDefaultValue();

            /**
             * Writes this entry to a given class visitor.
             *
             * @param classVisitor     The class visitor to which this entry is to be written to.
             * @param fieldDescription A description of the field that is to be written.
             */
            void apply(ClassVisitor classVisitor, FieldDescription fieldDescription);

            /**
             * A default implementation of a compiled field registry that simply returns a no-op
             * {@link net.bytebuddy.implementation.attribute.FieldAttributeAppender.Factory}
             * for any field.
             */
            enum NoOp implements Entry {

                /**
                 * The singleton instance.
                 */
                INSTANCE;

                @Override
                public FieldAttributeAppender getFieldAppender() {
                    return FieldAttributeAppender.NoOp.INSTANCE;
                }

                @Override
                public Object getDefaultValue() {
                    return null;
                }

                @Override
                public void apply(ClassVisitor classVisitor, FieldDescription fieldDescription) {
                    classVisitor.visitField(fieldDescription.getModifiers(),
                            fieldDescription.getInternalName(),
                            fieldDescription.getDescriptor(),
                            fieldDescription.getGenericSignature(),
                            null).visitEnd();
                }

                @Override
                public String toString() {
                    return "TypeWriter.FieldPool.Entry.NoOp." + name();
                }
            }

            /**
             * A simple entry that creates a specific
             * {@link net.bytebuddy.implementation.attribute.FieldAttributeAppender.Factory}
             * for any field.
             */
            class Simple implements Entry {

                /**
                 * The field attribute appender factory that is represented by this entry.
                 */
                private final FieldAttributeAppender attributeAppender;

                /**
                 * The field's default value or {@code null} if no default value is set.
                 */
                private final Object defaultValue;

                /**
                 * Creates a new simple entry for a given attribute appender factory.
                 *
                 * @param attributeAppender The attribute appender to be returned.
                 * @param defaultValue      The field's default value or {@code null} if no default value is
                 *                          set.
                 */
                public Simple(FieldAttributeAppender attributeAppender, Object defaultValue) {
                    this.attributeAppender = attributeAppender;
                    this.defaultValue = defaultValue;
                }

                @Override
                public FieldAttributeAppender getFieldAppender() {
                    return attributeAppender;
                }

                @Override
                public Object getDefaultValue() {
                    return defaultValue;
                }

                @Override
                public void apply(ClassVisitor classVisitor, FieldDescription fieldDescription) {
                    FieldVisitor fieldVisitor = classVisitor.visitField(fieldDescription.getModifiers(),
                            fieldDescription.getInternalName(),
                            fieldDescription.getDescriptor(),
                            fieldDescription.getGenericSignature(),
                            defaultValue);
                    attributeAppender.apply(fieldVisitor, fieldDescription);
                    fieldVisitor.visitEnd();
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other)
                        return true;
                    if (other == null || getClass() != other.getClass())
                        return false;
                    Simple simple = (Simple) other;
                    return attributeAppender.equals(simple.attributeAppender)
                            && !(defaultValue != null ?
                            !defaultValue.equals(simple.defaultValue) :
                            simple.defaultValue != null);
                }

                @Override
                public int hashCode() {
                    return 31 * attributeAppender.hashCode() + (defaultValue != null ? defaultValue.hashCode() : 0);
                }

                @Override
                public String toString() {
                    return "TypeWriter.FieldPool.Entry.Simple{" +
                            "attributeAppenderFactory=" + attributeAppender +
                            ", defaultValue=" + defaultValue +
                            '}';
                }
            }
        }
    }

    /**
     * An method pool that allows a lookup for how to implement a method.
     */
    interface MethodPool {

        /**
         * Looks up a handler entry for a given method.
         *
         * @param methodDescription The method being processed.
         * @return A handler entry for the given method.
         */
        Entry target(MethodDescription methodDescription);

        /**
         * An entry of a method pool that describes how a method is implemented.
         *
         * @see net.bytebuddy.dynamic.scaffold.TypeWriter.MethodPool
         */
        interface Entry {

            /**
             * Returns the sort of this method instrumentation.
             *
             * @return The sort of this method instrumentation.
             */
            Sort getSort();

            /**
             * Prepends the given method appender to this entry.
             *
             * @param byteCodeAppender The byte code appender to prepend.
             * @return This entry with the given code prepended.
             */
            Entry prepend(ByteCodeAppender byteCodeAppender);

            /**
             * Applies this method entry. This method can always be called and might be a no-op.
             *
             * @param classVisitor          The class visitor to which this entry should be applied.
             * @param implementationContext The implementation context to which this entry should be applied.
             * @param methodDescription     The method description of the instrumented method.
             */
            void apply(ClassVisitor classVisitor, Implementation.Context implementationContext, MethodDescription methodDescription);

            /**
             * Applies the head of this entry. Applying an entry is only possible if a method is defined, i.e. the sort of this entry is not
             * {@link net.bytebuddy.dynamic.scaffold.TypeWriter.MethodPool.Entry.Sort#SKIP}.
             *
             * @param methodVisitor     The method visitor to which this entry should be applied.
             * @param methodDescription The method description of the instrumented method.
             */
            void applyHead(MethodVisitor methodVisitor, MethodDescription methodDescription);

            /**
             * Applies the body of this entry. Applying the body of an entry is only possible if a method is implemented, i.e. the sort of this
             * entry is {@link net.bytebuddy.dynamic.scaffold.TypeWriter.MethodPool.Entry.Sort#IMPLEMENT}.
             *
             * @param methodVisitor         The method visitor to which this entry should be applied.
             * @param implementationContext The implementation context to which this entry should be applied.
             * @param methodDescription     The method description of the instrumented method.
             */
            void applyBody(MethodVisitor methodVisitor, Implementation.Context implementationContext, MethodDescription methodDescription);

            /**
             * The sort of an entry.
             */
            enum Sort {

                /**
                 * Describes a method that should not be implemented or retained in its original state.
                 */
                SKIP(false, false),

                /**
                 * Describes a method that should be defined but is abstract or native, i.e. does not define any byte code.
                 */
                DEFINE(true, false),

                /**
                 * Describes a method that is implemented in byte code.
                 */
                IMPLEMENT(true, true);

                /**
                 * Indicates if this sort defines a method, with or without byte code.
                 */
                private final boolean define;

                /**
                 * Indicates if this sort defines byte code.
                 */
                private final boolean implement;

                /**
                 * Creates a new sort.
                 *
                 * @param define    Indicates if this sort defines a method, with or without byte code.
                 * @param implement Indicates if this sort defines byte code.
                 */
                Sort(boolean define, boolean implement) {
                    this.define = define;
                    this.implement = implement;
                }

                /**
                 * Indicates if this sort defines a method, with or without byte code.
                 *
                 * @return {@code true} if this sort defines a method, with or without byte code.
                 */
                public boolean isDefined() {
                    return define;
                }

                /**
                 * Indicates if this sort defines byte code.
                 *
                 * @return {@code true} if this sort defines byte code.
                 */
                public boolean isImplemented() {
                    return implement;
                }

                @Override
                public String toString() {
                    return "TypeWriter.MethodPool.Entry.Sort." + name();
                }
            }

            /**
             * A canonical implementation of a skipped method.
             */
            enum ForSkippedMethod implements Entry {

                /**
                 * The singleton instance.
                 */
                INSTANCE;

                @Override
                public void apply(ClassVisitor classVisitor,
                                  Implementation.Context implementationContext,
                                  MethodDescription methodDescription) {
                    /* do nothing */
                }

                @Override
                public void applyBody(MethodVisitor methodVisitor,
                                      Implementation.Context implementationContext,
                                      MethodDescription methodDescription) {
                    throw new IllegalStateException("Cannot apply headless implementation for method that should be skipped");
                }

                @Override
                public void applyHead(MethodVisitor methodVisitor, MethodDescription methodDescription) {
                    throw new IllegalStateException("Cannot apply headless implementation for method that should be skipped");
                }

                @Override
                public Sort getSort() {
                    return Sort.SKIP;
                }

                @Override
                public Entry prepend(ByteCodeAppender byteCodeAppender) {
                    throw new IllegalStateException("Cannot prepend code to non-implemented method");
                }

                @Override
                public String toString() {
                    return "TypeWriter.MethodPool.Entry.Skip." + name();
                }
            }

            /**
             * A base implementation of an abstract entry that defines a method.
             */
            abstract class AbstractDefiningEntry implements Entry {

                @Override
                public void apply(ClassVisitor classVisitor, Implementation.Context implementationContext, MethodDescription methodDescription) {
                    MethodVisitor methodVisitor = classVisitor.visitMethod(methodDescription.getAdjustedModifiers(getSort().isImplemented()),
                            methodDescription.getInternalName(),
                            methodDescription.getDescriptor(),
                            methodDescription.getGenericSignature(),
                            methodDescription.getExceptionTypes().toInternalNames());
                    ParameterList parameterList = methodDescription.getParameters();
                    if (parameterList.hasExplicitMetaData()) {
                        for (ParameterDescription parameterDescription : parameterList) {
                            methodVisitor.visitParameter(parameterDescription.getName(), parameterDescription.getModifiers());
                        }
                    }
                    applyHead(methodVisitor, methodDescription);
                    applyBody(methodVisitor, implementationContext, methodDescription);
                    methodVisitor.visitEnd();
                }
            }

            /**
             * Describes an entry that defines a method as byte code.
             */
            class ForImplementation extends AbstractDefiningEntry {

                /**
                 * The byte code appender to apply.
                 */
                private final ByteCodeAppender byteCodeAppender;

                /**
                 * The method attribute appender to apply.
                 */
                private final MethodAttributeAppender methodAttributeAppender;

                /**
                 * Creates a new entry for a method that defines a method as byte code.
                 *
                 * @param byteCodeAppender        The byte code appender to apply.
                 * @param methodAttributeAppender The method attribute appender to apply.
                 */
                public ForImplementation(ByteCodeAppender byteCodeAppender, MethodAttributeAppender methodAttributeAppender) {
                    this.byteCodeAppender = byteCodeAppender;
                    this.methodAttributeAppender = methodAttributeAppender;
                }

                @Override
                public void applyHead(MethodVisitor methodVisitor, MethodDescription methodDescription) {
                    /* do nothing */
                }

                @Override
                public void applyBody(MethodVisitor methodVisitor, Implementation.Context implementationContext, MethodDescription methodDescription) {
                    methodAttributeAppender.apply(methodVisitor, methodDescription);
                    methodVisitor.visitCode();
                    ByteCodeAppender.Size size = byteCodeAppender.apply(methodVisitor, implementationContext, methodDescription);
                    methodVisitor.visitMaxs(size.getOperandStackSize(), size.getLocalVariableSize());
                }

                @Override
                public Entry prepend(ByteCodeAppender byteCodeAppender) {
                    return new ForImplementation(new ByteCodeAppender.Compound(byteCodeAppender, this.byteCodeAppender), methodAttributeAppender);
                }

                @Override
                public Sort getSort() {
                    return Sort.IMPLEMENT;
                }

                @Override
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && byteCodeAppender.equals(((ForImplementation) other).byteCodeAppender)
                            && methodAttributeAppender.equals(((ForImplementation) other).methodAttributeAppender);
                }

                @Override
                public int hashCode() {
                    return 31 * byteCodeAppender.hashCode() + methodAttributeAppender.hashCode();
                }

                @Override
                public String toString() {
                    return "TypeWriter.MethodPool.Entry.ForImplementation{" +
                            "byteCodeAppender=" + byteCodeAppender +
                            ", methodAttributeAppender=" + methodAttributeAppender +
                            '}';
                }
            }

            /**
             * Describes an entry that defines a method but without byte code and without an annotation value.
             */
            class ForAbstractMethod extends AbstractDefiningEntry {

                /**
                 * The method attribute appender to apply.
                 */
                private final MethodAttributeAppender methodAttributeAppender;

                /**
                 * Creates a new entry for a method that is defines but does not append byte code, i.e. is native or abstract.
                 *
                 * @param methodAttributeAppender The method attribute appender to apply.
                 */
                public ForAbstractMethod(MethodAttributeAppender methodAttributeAppender) {
                    this.methodAttributeAppender = methodAttributeAppender;
                }

                @Override
                public Sort getSort() {
                    return Sort.DEFINE;
                }

                @Override
                public void applyHead(MethodVisitor methodVisitor, MethodDescription methodDescription) {
                    /* do nothing */
                }

                @Override
                public void applyBody(MethodVisitor methodVisitor, Implementation.Context implementationContext, MethodDescription methodDescription) {
                    methodAttributeAppender.apply(methodVisitor, methodDescription);
                }

                @Override
                public Entry prepend(ByteCodeAppender byteCodeAppender) {
                    throw new IllegalStateException("Cannot prepend code to abstract method");
                }

                @Override
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && methodAttributeAppender.equals(((ForAbstractMethod) other).methodAttributeAppender);
                }

                @Override
                public int hashCode() {
                    return methodAttributeAppender.hashCode();
                }

                @Override
                public String toString() {
                    return "TypeWriter.MethodPool.Entry.ForAbstractMethod{" +
                            "methodAttributeAppender=" + methodAttributeAppender +
                            '}';
                }
            }

            /**
             * Describes an entry that defines a method with a default annotation value.
             */
            class ForAnnotationDefaultValue extends AbstractDefiningEntry {

                /**
                 * The annotation value to define.
                 */
                private final Object annotationValue;

                /**
                 * The method attribute appender to apply.
                 */
                private final MethodAttributeAppender methodAttributeAppender;

                /**
                 * Creates a new entry for defining a method with a default annotation value.
                 *
                 * @param annotationValue         The annotation value to define.
                 * @param methodAttributeAppender The method attribute appender to apply.
                 */
                public ForAnnotationDefaultValue(Object annotationValue, MethodAttributeAppender methodAttributeAppender) {
                    this.annotationValue = annotationValue;
                    this.methodAttributeAppender = methodAttributeAppender;
                }

                @Override
                public Sort getSort() {
                    return Sort.DEFINE;
                }

                @Override
                public void applyHead(MethodVisitor methodVisitor, MethodDescription methodDescription) {
                    if (!methodDescription.isDefaultValue(annotationValue)) {
                        throw new IllegalStateException("Cannot set " + annotationValue + " as default for " + methodDescription);
                    }
                    AnnotationVisitor annotationVisitor = methodVisitor.visitAnnotationDefault();
                    AnnotationAppender.Default.apply(annotationVisitor,
                            methodDescription.getReturnType(),
                            AnnotationAppender.NO_NAME,
                            annotationValue);
                    annotationVisitor.visitEnd();
                }

                @Override
                public void applyBody(MethodVisitor methodVisitor,
                                      Implementation.Context implementationContext,
                                      MethodDescription methodDescription) {
                    methodAttributeAppender.apply(methodVisitor, methodDescription);
                }

                @Override
                public Entry prepend(ByteCodeAppender byteCodeAppender) {
                    throw new IllegalStateException("Cannot prepend code to method that defines a default annotation value");
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (other == null || getClass() != other.getClass()) return false;
                    ForAnnotationDefaultValue that = (ForAnnotationDefaultValue) other;
                    return annotationValue.equals(that.annotationValue) && methodAttributeAppender.equals(that.methodAttributeAppender);

                }

                @Override
                public int hashCode() {
                    int result = annotationValue.hashCode();
                    result = 31 * result + methodAttributeAppender.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "TypeWriter.MethodPool.Entry.ForAnnotationDefaultValue{" +
                            "annotationValue=" + annotationValue +
                            ", methodAttributeAppender=" + methodAttributeAppender +
                            '}';
                }
            }
        }
    }

    /**
     * A default implementation of a {@link net.bytebuddy.dynamic.scaffold.TypeWriter}.
     *
     * @param <S> The best known loaded type for the dynamically created type.
     */
    abstract class Default<S> implements TypeWriter<S> {

        /**
         * A flag for ASM not to automatically compute any information such as operand stack sizes and stack map frames.
         */
        protected static final int ASM_MANUAL_FLAG = 0;

        /**
         * The ASM API version to use.
         */
        protected static final int ASM_API_VERSION = Opcodes.ASM5;

        /**
         * The instrumented type that is to be written.
         */
        protected final TypeDescription instrumentedType;

        /**
         * The loaded type initializer of the instrumented type.
         */
        protected final LoadedTypeInitializer loadedTypeInitializer;

        /**
         * The type initializer of the instrumented type.
         */
        protected final InstrumentedType.TypeInitializer typeInitializer;

        /**
         * A list of explicit auxiliary types that are to be added to the created dynamic type.
         */
        protected final List<DynamicType> explicitAuxiliaryTypes;

        /**
         * The class file version of the written type.
         */
        protected final ClassFileVersion classFileVersion;

        /**
         * A naming strategy that is used for naming auxiliary types.
         */
        protected final AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy;

        /**
         * A class visitor wrapper to apply during instrumentation.
         */
        protected final ClassVisitorWrapper classVisitorWrapper;

        /**
         * The type attribute appender to apply.
         */
        protected final TypeAttributeAppender attributeAppender;

        /**
         * The field pool to be used for instrumenting fields.
         */
        protected final FieldPool fieldPool;

        /**
         * The method pool to be used for instrumenting methods.
         */
        protected final MethodPool methodPool;

        /**
         * A list of all instrumented methods.
         */
        protected final MethodList instrumentedMethods;

        /**
         * Creates a new default type writer.
         *
         * @param instrumentedType            The instrumented type that is to be written.
         * @param loadedTypeInitializer       The loaded type initializer of the instrumented type.
         * @param typeInitializer             The type initializer of the instrumented type.
         * @param explicitAuxiliaryTypes      A list of explicit auxiliary types that are to be added to the created dynamic type.
         * @param classFileVersion            The class file version of the written type.
         * @param auxiliaryTypeNamingStrategy A naming strategy that is used for naming auxiliary types.
         * @param classVisitorWrapper         A class visitor wrapper to apply during instrumentation.
         * @param attributeAppender           The type attribute appender to apply.
         * @param fieldPool                   The field pool to be used for instrumenting fields.
         * @param methodPool                  The method pool to be used for instrumenting methods.
         * @param instrumentedMethods         A list of all instrumented methods.
         */
        protected Default(TypeDescription instrumentedType,
                          LoadedTypeInitializer loadedTypeInitializer,
                          InstrumentedType.TypeInitializer typeInitializer,
                          List<DynamicType> explicitAuxiliaryTypes,
                          ClassFileVersion classFileVersion,
                          AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy,
                          ClassVisitorWrapper classVisitorWrapper,
                          TypeAttributeAppender attributeAppender,
                          FieldPool fieldPool,
                          MethodPool methodPool,
                          MethodList instrumentedMethods) {
            this.instrumentedType = instrumentedType;
            this.loadedTypeInitializer = loadedTypeInitializer;
            this.typeInitializer = typeInitializer;
            this.explicitAuxiliaryTypes = explicitAuxiliaryTypes;
            this.classFileVersion = classFileVersion;
            this.auxiliaryTypeNamingStrategy = auxiliaryTypeNamingStrategy;
            this.classVisitorWrapper = classVisitorWrapper;
            this.attributeAppender = attributeAppender;
            this.fieldPool = fieldPool;
            this.methodPool = methodPool;
            this.instrumentedMethods = instrumentedMethods;
        }

        /**
         * Creates a type writer for creating a new type.
         *
         * @param methodRegistry              The method registry to use for creating the type.
         * @param fieldPool                   The field pool to use.
         * @param auxiliaryTypeNamingStrategy A naming strategy for naming auxiliary types.
         * @param classVisitorWrapper         The class visitor wrapper to apply when creating the type.
         * @param attributeAppender           The attribute appender to use.
         * @param classFileVersion            The class file version of the created type.
         * @param <U>                         The best known loaded type for the dynamically created type.
         * @return An appropriate type writer.
         */
        public static <U> TypeWriter<U> forCreation(MethodRegistry.Compiled methodRegistry,
                                                    FieldPool fieldPool,
                                                    AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy,
                                                    ClassVisitorWrapper classVisitorWrapper,
                                                    TypeAttributeAppender attributeAppender,
                                                    ClassFileVersion classFileVersion) {
            return new ForCreation<U>(methodRegistry.getInstrumentedType(),
                    methodRegistry.getLoadedTypeInitializer(),
                    methodRegistry.getTypeInitializer(),
                    Collections.<DynamicType>emptyList(),
                    classFileVersion,
                    auxiliaryTypeNamingStrategy,
                    classVisitorWrapper,
                    attributeAppender,
                    fieldPool,
                    methodRegistry,
                    methodRegistry.getInstrumentedMethods());
        }

        /**
         * Creates a type writer for creating a new type.
         *
         * @param methodRegistry              The method registry to use for creating the type.
         * @param fieldPool                   The field pool to use.
         * @param auxiliaryTypeNamingStrategy A naming strategy for naming auxiliary types.
         * @param classVisitorWrapper         The class visitor wrapper to apply when creating the type.
         * @param attributeAppender           The attribute appender to use.
         * @param classFileVersion            The minimum class file version of the created type.
         * @param classFileLocator            The class file locator to use.
         * @param methodRebaseResolver        The method rebase resolver to use.
         * @param targetType                  The target type that is to be rebased.
         * @param <U>                         The best known loaded type for the dynamically created type.
         * @return An appropriate type writer.
         */
        public static <U> TypeWriter<U> forRebasing(MethodRegistry.Compiled methodRegistry,
                                                    FieldPool fieldPool,
                                                    AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy,
                                                    ClassVisitorWrapper classVisitorWrapper,
                                                    TypeAttributeAppender attributeAppender,
                                                    ClassFileVersion classFileVersion,
                                                    ClassFileLocator classFileLocator,
                                                    TypeDescription targetType,
                                                    MethodRebaseResolver methodRebaseResolver) {
            return new ForInlining<U>(methodRegistry.getInstrumentedType(),
                    methodRegistry.getLoadedTypeInitializer(),
                    methodRegistry.getTypeInitializer(),
                    methodRebaseResolver.getAuxiliaryTypes(),
                    classFileVersion,
                    auxiliaryTypeNamingStrategy,
                    classVisitorWrapper,
                    attributeAppender,
                    fieldPool,
                    methodRegistry,
                    methodRegistry.getInstrumentedMethods(),
                    classFileLocator,
                    targetType,
                    methodRebaseResolver);
        }

        /**
         * Creates a type writer for creating a new type.
         *
         * @param methodRegistry              The method registry to use for creating the type.
         * @param fieldPool                   The field pool to use.
         * @param auxiliaryTypeNamingStrategy A naming strategy for naming auxiliary types.
         * @param classVisitorWrapper         The class visitor wrapper to apply when creating the type.
         * @param attributeAppender           The attribute appender to use.
         * @param classFileVersion            The minimum class file version of the created type.
         * @param classFileLocator            The class file locator to use.
         * @param targetType                  The target type that is to be rebased.
         * @param <U>                         The best known loaded type for the dynamically created type.
         * @return An appropriate type writer.
         */
        public static <U> TypeWriter<U> forRedefinition(MethodRegistry.Compiled methodRegistry,
                                                        FieldPool fieldPool,
                                                        AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy,
                                                        ClassVisitorWrapper classVisitorWrapper,
                                                        TypeAttributeAppender attributeAppender,
                                                        ClassFileVersion classFileVersion,
                                                        ClassFileLocator classFileLocator,
                                                        TypeDescription targetType) {
            return new ForInlining<U>(methodRegistry.getInstrumentedType(),
                    methodRegistry.getLoadedTypeInitializer(),
                    methodRegistry.getTypeInitializer(),
                    Collections.<DynamicType>emptyList(),
                    classFileVersion,
                    auxiliaryTypeNamingStrategy,
                    classVisitorWrapper,
                    attributeAppender,
                    fieldPool,
                    methodRegistry,
                    methodRegistry.getInstrumentedMethods(),
                    classFileLocator,
                    targetType,
                    MethodRebaseResolver.Disabled.INSTANCE);
        }

        @Override
        public DynamicType.Unloaded<S> make() {
            Implementation.Context.ExtractableView implementationContext = new Implementation.Context.Default(instrumentedType,
                    auxiliaryTypeNamingStrategy,
                    typeInitializer,
                    classFileVersion);
            return new DynamicType.Default.Unloaded<S>(instrumentedType,
                    create(implementationContext),
                    loadedTypeInitializer,
                    join(explicitAuxiliaryTypes, implementationContext.getRegisteredAuxiliaryTypes()));
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (other == null || getClass() != other.getClass()) return false;
            Default<?> aDefault = (Default<?>) other;
            return instrumentedType.equals(aDefault.instrumentedType)
                    && loadedTypeInitializer.equals(aDefault.loadedTypeInitializer)
                    && typeInitializer.equals(aDefault.typeInitializer)
                    && explicitAuxiliaryTypes.equals(aDefault.explicitAuxiliaryTypes)
                    && classFileVersion.equals(aDefault.classFileVersion)
                    && auxiliaryTypeNamingStrategy.equals(aDefault.auxiliaryTypeNamingStrategy)
                    && classVisitorWrapper.equals(aDefault.classVisitorWrapper)
                    && attributeAppender.equals(aDefault.attributeAppender)
                    && fieldPool.equals(aDefault.fieldPool)
                    && methodPool.equals(aDefault.methodPool)
                    && instrumentedMethods.equals(aDefault.instrumentedMethods);
        }

        @Override
        public int hashCode() {
            int result = instrumentedType.hashCode();
            result = 31 * result + loadedTypeInitializer.hashCode();
            result = 31 * result + typeInitializer.hashCode();
            result = 31 * result + explicitAuxiliaryTypes.hashCode();
            result = 31 * result + classFileVersion.hashCode();
            result = 31 * result + auxiliaryTypeNamingStrategy.hashCode();
            result = 31 * result + classVisitorWrapper.hashCode();
            result = 31 * result + attributeAppender.hashCode();
            result = 31 * result + fieldPool.hashCode();
            result = 31 * result + methodPool.hashCode();
            result = 31 * result + instrumentedMethods.hashCode();
            return result;
        }

        /**
         * Creates the instrumented type.
         *
         * @param implementationContext The implementation context to use.
         * @return A byte array that represents the instrumented type.
         */
        protected abstract byte[] create(Implementation.Context.ExtractableView implementationContext);

        /**
         * A class validator that validates that a class only defines members that are appropriate for the sort of the generated class.
         */
        protected static class ValidatingClassVisitor extends ClassVisitor {

            /**
             * Indicates that a method has no method parameters.
             */
            private static final String NO_PARAMETERS = "()";

            /**
             * Indicates that a method returns void.
             */
            private static final String RETURNS_VOID = "V";

            /**
             * The constraint to assert the members against. The constraint is first defined when the general class information is visited.
             */
            private Constraint constraint;

            /**
             * Creates a validating class visitor.
             *
             * @param classVisitor The class visitor to which any calls are delegated to.
             */
            protected ValidatingClassVisitor(ClassVisitor classVisitor) {
                super(ASM_API_VERSION, classVisitor);
            }

            @Override
            public void visit(int version, int modifier, String name, String signature, String superName, String[] interfaces) {
                ClassFileVersion classFileVersion = new ClassFileVersion(version);
                if (name.endsWith("." + PackageDescription.PACKAGE_CLASS_NAME)) {
                    constraint = Constraint.PACKAGE_CLASS;
                } else if ((modifier & Opcodes.ACC_ANNOTATION) != ModifierReviewable.EMPTY_MASK) {
                    constraint = classFileVersion.isSupportsDefaultMethods()
                            ? Constraint.JAVA8_ANNOTATION
                            : Constraint.ANNOTATION;
                } else if ((modifier & Opcodes.ACC_INTERFACE) != ModifierReviewable.EMPTY_MASK) {
                    constraint = classFileVersion.isSupportsDefaultMethods()
                            ? Constraint.JAVA8_INTERFACE
                            : Constraint.INTERFACE;
                } else if ((modifier & Opcodes.ACC_ABSTRACT) != ModifierReviewable.EMPTY_MASK) {
                    constraint = Constraint.ABSTRACT_CLASS;
                } else {
                    constraint = Constraint.MANIFEST_CLASS;
                }
                constraint.assertPackage(modifier, interfaces);
                super.visit(version, modifier, name, signature, superName, interfaces);
            }

            @Override
            public FieldVisitor visitField(int modifiers, String name, String desc, String signature, Object defaultValue) {
                constraint.assertField(name, (modifiers & Opcodes.ACC_PUBLIC) != 0, (modifiers & Opcodes.ACC_STATIC) != 0);
                return super.visitField(modifiers, name, desc, signature, defaultValue);
            }

            @Override
            public MethodVisitor visitMethod(int modifiers, String name, String descriptor, String signature, String[] exceptions) {
                constraint.assertMethod(name,
                        (modifiers & Opcodes.ACC_ABSTRACT) != 0,
                        (modifiers & Opcodes.ACC_PUBLIC) != 0,
                        (modifiers & Opcodes.ACC_STATIC) != 0,
                        !descriptor.startsWith(NO_PARAMETERS) || descriptor.endsWith(RETURNS_VOID));
                return new ValidatingMethodVisitor(super.visitMethod(modifiers, name, descriptor, signature, exceptions), name);
            }

            @Override
            public String toString() {
                return "TypeWriter.Default.ValidatingClassVisitor{" +
                        "constraint=" + constraint +
                        "}";
            }

            /**
             * A method validator for checking default values.
             */
            protected class ValidatingMethodVisitor extends MethodVisitor {

                /**
                 * The name of the method being visited.
                 */
                private final String name;

                /**
                 * Creates a validating method visitor.
                 *
                 * @param methodVisitor The method visitor to which any calls are delegated to.
                 * @param name          The name of the method being visited.
                 */
                protected ValidatingMethodVisitor(MethodVisitor methodVisitor, String name) {
                    super(ASM_API_VERSION, methodVisitor);
                    this.name = name;
                }

                @Override
                public AnnotationVisitor visitAnnotationDefault() {
                    constraint.assertDefault(name);
                    return super.visitAnnotationDefault();
                }

                @Override
                public String toString() {
                    return "TypeWriter.Default.ValidatingClassVisitor.ValidatingMethodVisitor{" +
                            "classVisitor=" + ValidatingClassVisitor.this +
                            ", name='" + name + '\'' +
                            '}';
                }
            }

            /**
             * A constraint for members that are legal for a given type.
             */
            protected enum Constraint {

                /**
                 * Constraints for a non-abstract class.
                 */
                MANIFEST_CLASS("non-abstract class", true, true, true, true, false, true, false, true),

                /**
                 * Constraints for an abstract class.
                 */
                ABSTRACT_CLASS("abstract class", true, true, true, true, true, true, false, true),

                /**
                 * Constrains for an interface type before Java 8.
                 */
                INTERFACE("interface (Java 7-)", false, false, false, false, true, false, false, true),

                /**
                 * Constrains for an interface type since Java 8.
                 */
                JAVA8_INTERFACE("interface (Java 8+)", false, false, false, true, true, true, false, true),

                /**
                 * Constrains for an annotation type before Java 8.
                 */
                ANNOTATION("annotation (Java 7-)", false, false, false, false, true, false, true, true),

                /**
                 * Constrains for an annotation type since Java 8.
                 */
                JAVA8_ANNOTATION("annotation (Java 8+)", false, false, false, true, true, true, true, true),

                PACKAGE_CLASS("package definition", false, true, false, false, true, false, false, false);

                /**
                 * A name to represent the type being validated within an error message.
                 */
                private final String sortName;

                /**
                 * Determines if a sort allows constructors.
                 */
                private final boolean allowsConstructor;

                /**
                 * Determines if a sort allows non-public members.
                 */
                private final boolean allowsNonPublic;

                /**
                 * Determines if a sort allows non-static fields.
                 */
                private final boolean allowsNonStaticFields;

                /**
                 * Determines if a sort allows static methods.
                 */
                private final boolean allowsStaticMethods;

                /**
                 * Determines if a sort allows abstract methods.
                 */
                private final boolean allowsAbstract;

                /**
                 * Determines if a sort allows non-abstract methods.
                 */
                private final boolean allowsNonAbstract;

                /**
                 * Determines if a sort allows the definition of annotation default values.
                 */
                private final boolean allowsDefaultValue;

                private final boolean allowsNonPackage;

                /**
                 * Creates a new constraint.
                 *
                 * @param sortName              A name to represent the type being validated within an error message.
                 * @param allowsConstructor     Determines if a sort allows constructors.
                 * @param allowsNonPublic       Determines if a sort allows non-public members.
                 * @param allowsNonStaticFields Determines if a sort allows non-static fields.
                 * @param allowsStaticMethods   Determines if a sort allows static methods.
                 * @param allowsAbstract        Determines if a sort allows abstract methods.
                 * @param allowsNonAbstract     Determines if a sort allows non-abstract methods.
                 * @param allowsDefaultValue    Determines if a sort allows the definition of annotation default values.
                 */
                Constraint(String sortName,
                           boolean allowsConstructor,
                           boolean allowsNonPublic,
                           boolean allowsNonStaticFields,
                           boolean allowsStaticMethods,
                           boolean allowsAbstract,
                           boolean allowsNonAbstract,
                           boolean allowsDefaultValue,
                           boolean allowsNonPackage) {
                    this.sortName = sortName;
                    this.allowsConstructor = allowsConstructor;
                    this.allowsNonPublic = allowsNonPublic;
                    this.allowsNonStaticFields = allowsNonStaticFields;
                    this.allowsStaticMethods = allowsStaticMethods;
                    this.allowsAbstract = allowsAbstract;
                    this.allowsNonAbstract = allowsNonAbstract;
                    this.allowsDefaultValue = allowsDefaultValue;
                    this.allowsNonPackage = allowsNonPackage;
                }

                /**
                 * Asserts a field for being valid.
                 *
                 * @param name     The name of the field.
                 * @param isPublic {@code true} if this field is public.
                 * @param isStatic {@code true} if this field is static.
                 */
                protected void assertField(String name, boolean isPublic, boolean isStatic) {
                    if (!isPublic && !allowsNonPublic) {
                        throw new IllegalStateException("Cannot define non-public field " + name + " for " + sortName);
                    } else if (!isStatic && !allowsNonStaticFields) {
                        throw new IllegalStateException("Cannot define for non-static field " + name + " for " + sortName);
                    }
                }

                /**
                 * Asserts a method for being valid.
                 *
                 * @param name                  The name of the method.
                 * @param isAbstract            {@code true} if the method is abstract.
                 * @param isPublic              {@code true} if this method is public.
                 * @param isStatic              {@code true} if this method is static.
                 * @param isDefaultIncompatible {@code true} if a method's signature cannot describe an annotation property method.
                 */
                protected void assertMethod(String name, boolean isAbstract, boolean isPublic, boolean isStatic, boolean isDefaultIncompatible) {
                    if (!allowsConstructor && name.equals(MethodDescription.CONSTRUCTOR_INTERNAL_NAME)) {
                        throw new IllegalStateException("Cannot define constructor for " + sortName);
                    } else if (isStatic && isAbstract) {
                        throw new IllegalStateException("Cannot define static method " + name + " to be abstract");
                    } else if (isAbstract && name.equals(MethodDescription.CONSTRUCTOR_INTERNAL_NAME)) {
                        throw new IllegalStateException("Cannot define abstract constructor " + name);
                    } else if (!isPublic && !allowsNonPublic) {
                        throw new IllegalStateException("Cannot define non-public method " + name + " for " + sortName);
                    } else if (isStatic && !allowsStaticMethods) {
                        throw new IllegalStateException("Cannot define static method " + name + " for " + sortName);
                    } else if (!isStatic && isAbstract && !allowsAbstract) {
                        throw new IllegalStateException("Cannot define abstract method " + name + " for " + sortName);
                    } else if (!isAbstract && !allowsNonAbstract) {
                        throw new IllegalStateException("Cannot define non-abstract method " + name + " for " + sortName);
                    } else if (!isStatic && isDefaultIncompatible && allowsDefaultValue) {
                        throw new IllegalStateException("The signature of " + name + " is not compatible for a property of " + sortName);
                    }
                }

                /**
                 * Asserts if a default value is legal for a method.
                 *
                 * @param name The name of the method.
                 */
                protected void assertDefault(String name) {
                    if (!allowsDefaultValue) {
                        throw new IllegalStateException("Cannot define define default value on " + name + " for " + sortName);
                    }
                }

                protected void assertPackage(int modifier, String[] interfaces) {
                    if (!allowsNonPackage && modifier != PackageDescription.PACKAGE_MODIFIERS) {
                        throw new IllegalStateException("Cannot alter modifier for " + sortName);
                    } else if (!allowsNonPackage && interfaces != null) {
                        throw new IllegalStateException("Cannot implement interface for " + sortName);
                    }
                }

                @Override
                public String toString() {
                    return "TypeWriter.Default.ValidatingClassVisitor.Constraint." + name();
                }
            }
        }

        /**
         * A type writer that inlines the created type into an existing class file.
         *
         * @param <U> The best known loaded type for the dynamically created type.
         */
        public static class ForInlining<U> extends Default<U> {

            /**
             * Indicates that a class does not define an explicit super class.
             */
            private static final TypeDescription NO_SUPER_CLASS = null;

            /**
             * Indicates that a method should be retained.
             */
            private static final MethodDescription RETAIN_METHOD = null;

            /**
             * Indicates that a method should be ignored.
             */
            private static final MethodVisitor IGNORE_METHOD = null;

            /**
             * Indicates that an annotation should be ignored.
             */
            private static final AnnotationVisitor IGNORE_ANNOTATION = null;

            /**
             * The class file locator to use.
             */
            private final ClassFileLocator classFileLocator;

            /**
             * The target type that is to be redefined via inlining.
             */
            private final TypeDescription targetType;

            /**
             * The method rebase resolver to use.
             */
            private final MethodRebaseResolver methodRebaseResolver;

            /**
             * Creates a new type writer for inling a type into an existing type description.
             *
             * @param instrumentedType            The instrumented type that is to be written.
             * @param loadedTypeInitializer       The loaded type initializer of the instrumented type.
             * @param typeInitializer             The type initializer of the instrumented type.
             * @param explicitAuxiliaryTypes      A list of explicit auxiliary types that are to be added to the created dynamic type.
             * @param classFileVersion            The class file version of the written type.
             * @param auxiliaryTypeNamingStrategy A naming strategy that is used for naming auxiliary types.
             * @param classVisitorWrapper         A class visitor wrapper to apply during instrumentation.
             * @param attributeAppender           The type attribute appender to apply.
             * @param fieldPool                   The field pool to be used for instrumenting fields.
             * @param methodPool                  The method pool to be used for instrumenting methods.
             * @param instrumentedMethods         A list of all instrumented methods.
             * @param classFileLocator            The class file locator to use.
             * @param targetType                  The target type that is to be redefined via inlining.
             * @param methodRebaseResolver        The method rebase resolver to use.
             */
            protected ForInlining(TypeDescription instrumentedType,
                                  LoadedTypeInitializer loadedTypeInitializer,
                                  InstrumentedType.TypeInitializer typeInitializer,
                                  List<DynamicType> explicitAuxiliaryTypes,
                                  ClassFileVersion classFileVersion,
                                  AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy,
                                  ClassVisitorWrapper classVisitorWrapper,
                                  TypeAttributeAppender attributeAppender,
                                  FieldPool fieldPool,
                                  MethodPool methodPool,
                                  MethodList instrumentedMethods,
                                  ClassFileLocator classFileLocator,
                                  TypeDescription targetType,
                                  MethodRebaseResolver methodRebaseResolver) {
                super(instrumentedType,
                        loadedTypeInitializer,
                        typeInitializer,
                        explicitAuxiliaryTypes,
                        classFileVersion,
                        auxiliaryTypeNamingStrategy,
                        classVisitorWrapper,
                        attributeAppender,
                        fieldPool,
                        methodPool,
                        instrumentedMethods);
                this.classFileLocator = classFileLocator;
                this.targetType = targetType;
                this.methodRebaseResolver = methodRebaseResolver;
            }

            @Override
            public byte[] create(Implementation.Context.ExtractableView implementationContext) {
                try {
                    ClassFileLocator.Resolution resolution = classFileLocator.locate(targetType.getName());
                    if (!resolution.isResolved()) {
                        throw new IllegalArgumentException("Cannot locate the class file for " + targetType + " using " + classFileLocator);
                    }
                    return doCreate(implementationContext, resolution.resolve());
                } catch (IOException e) {
                    throw new RuntimeException("The class file could not be written", e);
                }
            }

            /**
             * Performs the actual creation of a class file.
             *
             * @param implementationContext The implementation context to use for implementing the class file.
             * @param binaryRepresentation  The binary representation of the class file.
             * @return The byte array representing the created class.
             */
            private byte[] doCreate(Implementation.Context.ExtractableView implementationContext, byte[] binaryRepresentation) {
                ClassReader classReader = new ClassReader(binaryRepresentation);
                ClassWriter classWriter = new ClassWriter(classReader, ASM_MANUAL_FLAG);
                classReader.accept(writeTo(classVisitorWrapper.wrap(new ValidatingClassVisitor(classWriter)), implementationContext), ASM_MANUAL_FLAG);
                return classWriter.toByteArray();
            }

            /**
             * Creates a class visitor which weaves all changes and additions on the fly.
             *
             * @param classVisitor          The class visitor to which this entry is to be written to.
             * @param implementationContext The implementation context to use for implementing the class file.
             * @return A class visitor which is capable of applying the changes.
             */
            private ClassVisitor writeTo(ClassVisitor classVisitor, Implementation.Context.ExtractableView implementationContext) {
                String originalName = targetType.getInternalName();
                String targetName = instrumentedType.getInternalName();
                ClassVisitor targetClassVisitor = new RedefinitionClassVisitor(classVisitor, implementationContext);
                return originalName.equals(targetName)
                        ? targetClassVisitor
                        : new RemappingClassAdapter(targetClassVisitor, new SimpleRemapper(originalName, targetName));
            }

            @Override
            public boolean equals(Object other) {
                if (this == other) return true;
                if (other == null || getClass() != other.getClass()) return false;
                if (!super.equals(other)) return false;
                ForInlining<?> that = (ForInlining<?>) other;
                return classFileLocator.equals(that.classFileLocator)
                        && targetType.equals(that.targetType)
                        && methodRebaseResolver.equals(that.methodRebaseResolver);
            }

            @Override
            public int hashCode() {
                int result = super.hashCode();
                result = 31 * result + classFileLocator.hashCode();
                result = 31 * result + targetType.hashCode();
                result = 31 * result + methodRebaseResolver.hashCode();
                return result;
            }

            @Override
            public String toString() {
                return "TypeWriter.Default.ForInlining{" +
                        "instrumentedType=" + instrumentedType +
                        ", loadedTypeInitializer=" + loadedTypeInitializer +
                        ", typeInitializer=" + typeInitializer +
                        ", explicitAuxiliaryTypes=" + explicitAuxiliaryTypes +
                        ", classFileVersion=" + classFileVersion +
                        ", auxiliaryTypeNamingStrategy=" + auxiliaryTypeNamingStrategy +
                        ", classVisitorWrapper=" + classVisitorWrapper +
                        ", attributeAppender=" + attributeAppender +
                        ", fieldPool=" + fieldPool +
                        ", methodPool=" + methodPool +
                        ", instrumentedMethods=" + instrumentedMethods +
                        ", classFileLocator=" + classFileLocator +
                        ", targetType=" + targetType +
                        ", methodRebaseResolver=" + methodRebaseResolver +
                        '}';
            }

            /**
             * A class visitor which is capable of applying a redefinition of an existing class file.
             */
            protected class RedefinitionClassVisitor extends ClassVisitor {

                /**
                 * The implementation context for this class creation.
                 */
                private final Implementation.Context.ExtractableView implementationContext;

                /**
                 * A mutable map of all declared fields of the instrumented type by their names.
                 */
                private final Map<String, FieldDescription> declaredFields;

                /**
                 * A mutable map of all declarable methods of the instrumented type by their unique signatures.
                 */
                private final Map<String, MethodDescription> declarableMethods;

                /**
                 * A mutable reference for code that is to be injected into the actual type initializer, if any.
                 * Usually, this represents an invocation of the actual type initializer that is found in the class
                 * file which is relocated into a static method.
                 */
                private Implementation.Context.ExtractableView.InjectedCode injectedCode;

                /**
                 * Creates a class visitor which is capable of redefining an existent class on the fly.
                 *
                 * @param classVisitor          The underlying class visitor to which writes are delegated.
                 * @param implementationContext The implementation context to use for implementing the class file.
                 */
                protected RedefinitionClassVisitor(ClassVisitor classVisitor, Implementation.Context.ExtractableView implementationContext) {
                    super(ASM_API_VERSION, classVisitor);
                    this.implementationContext = implementationContext;
                    List<? extends FieldDescription> fieldDescriptions = instrumentedType.getDeclaredFields();
                    declaredFields = new HashMap<String, FieldDescription>(fieldDescriptions.size());
                    for (FieldDescription fieldDescription : fieldDescriptions) {
                        declaredFields.put(fieldDescription.getInternalName(), fieldDescription);
                    }
                    declarableMethods = new HashMap<String, MethodDescription>(instrumentedMethods.size());
                    for (MethodDescription methodDescription : instrumentedMethods) {
                        declarableMethods.put(methodDescription.getUniqueSignature(), methodDescription);
                    }
                    injectedCode = Implementation.Context.ExtractableView.InjectedCode.None.INSTANCE;
                }

                @Override
                public void visit(int classFileVersionNumber,
                                  int modifiers,
                                  String internalName,
                                  String genericSignature,
                                  String superTypeInternalName,
                                  String[] interfaceTypeInternalName) {
                    ClassFileVersion originalClassFileVersion = new ClassFileVersion(classFileVersionNumber);
                    super.visit((classFileVersion.compareTo(originalClassFileVersion) > 0
                                    ? classFileVersion
                                    : originalClassFileVersion).getVersionNumber(),
                            instrumentedType.getActualModifiers((modifiers & Opcodes.ACC_SUPER) != 0),
                            instrumentedType.getInternalName(),
                            instrumentedType.getGenericSignature(),
                            (instrumentedType.getSuperType() == NO_SUPER_CLASS ?
                                    TypeDescription.OBJECT :
                                    instrumentedType.getSuperType()).getInternalName(),
                            instrumentedType.getInterfaces().toInternalNames());
                    attributeAppender.apply(this, instrumentedType);
                }

                @Override
                public FieldVisitor visitField(int modifiers,
                                               String internalName,
                                               String descriptor,
                                               String genericSignature,
                                               Object defaultValue) {
                    declaredFields.remove(internalName); // Ignore in favor of the class file definition.
                    return super.visitField(modifiers, internalName, descriptor, genericSignature, defaultValue);
                }

                @Override
                public MethodVisitor visitMethod(int modifiers,
                                                 String internalName,
                                                 String descriptor,
                                                 String genericSignature,
                                                 String[] exceptionTypeInternalName) {
                    if (internalName.equals(MethodDescription.TYPE_INITIALIZER_INTERNAL_NAME)) {
                        TypeInitializerInjection injectedCode = new TypeInitializerInjection();
                        this.injectedCode = injectedCode;
                        return super.visitMethod(injectedCode.getInjectorProxyMethod().getModifiers(),
                                injectedCode.getInjectorProxyMethod().getInternalName(),
                                injectedCode.getInjectorProxyMethod().getDescriptor(),
                                injectedCode.getInjectorProxyMethod().getGenericSignature(),
                                injectedCode.getInjectorProxyMethod().getExceptionTypes().toInternalNames());
                    }
                    MethodDescription methodDescription = declarableMethods.remove(internalName + descriptor);
                    return methodDescription == RETAIN_METHOD
                            ? super.visitMethod(modifiers, internalName, descriptor, genericSignature, exceptionTypeInternalName)
                            : redefine(methodDescription, (modifiers & Opcodes.ACC_ABSTRACT) != 0);
                }

                /**
                 * Redefines a given method if this is required by looking up a potential implementation from the
                 * {@link net.bytebuddy.dynamic.scaffold.TypeWriter.MethodPool}.
                 *
                 * @param methodDescription The method being considered for redefinition.
                 * @param abstractOrigin    {@code true} if the original method is abstract, i.e. there is no implementation
                 *                          to preserve.
                 * @return A method visitor which is capable of consuming the original method.
                 */
                protected MethodVisitor redefine(MethodDescription methodDescription, boolean abstractOrigin) {
                    TypeWriter.MethodPool.Entry entry = methodPool.target(methodDescription);
                    if (!entry.getSort().isDefined()) {
                        return super.visitMethod(methodDescription.getModifiers(),
                                methodDescription.getInternalName(),
                                methodDescription.getDescriptor(),
                                methodDescription.getGenericSignature(),
                                methodDescription.getExceptionTypes().toInternalNames());
                    }
                    MethodVisitor methodVisitor = super.visitMethod(
                            methodDescription.getAdjustedModifiers(entry.getSort().isImplemented()),
                            methodDescription.getInternalName(),
                            methodDescription.getDescriptor(),
                            methodDescription.getGenericSignature(),
                            methodDescription.getExceptionTypes().toInternalNames());
                    return abstractOrigin
                            ? new AttributeObtainingMethodVisitor(methodVisitor, entry, methodDescription)
                            : new CodePreservingMethodVisitor(methodVisitor, entry, methodDescription);
                }

                @Override
                public void visitEnd() {
                    for (FieldDescription fieldDescription : declaredFields.values()) {
                        fieldPool.target(fieldDescription).apply(cv, fieldDescription);
                    }
                    for (MethodDescription methodDescription : declarableMethods.values()) {
                        methodPool.target(methodDescription).apply(cv, implementationContext, methodDescription);
                    }
                    implementationContext.drain(cv, methodPool, injectedCode);
                    super.visitEnd();
                }

                @Override
                public String toString() {
                    return "TypeWriter.Default.ForInlining.RedefinitionClassVisitor{" +
                            "typeWriter=" + TypeWriter.Default.ForInlining.this +
                            ", implementationContext=" + implementationContext +
                            ", declaredFields=" + declaredFields +
                            ", declarableMethods=" + declarableMethods +
                            ", injectedCode=" + injectedCode +
                            '}';
                }

                /**
                 * A method visitor that preserves the code of a method in the class file by copying it into a rebased
                 * method while copying all attributes and annotations to the actual method.
                 */
                protected class CodePreservingMethodVisitor extends MethodVisitor {

                    /**
                     * The method visitor of the actual method.
                     */
                    private final MethodVisitor actualMethodVisitor;

                    /**
                     * The method pool entry to apply.
                     */
                    private final MethodPool.Entry entry;

                    /**
                     * A description of the actual method.
                     */
                    private final MethodDescription methodDescription;

                    /**
                     * The resolution of a potential rebased method.
                     */
                    private final MethodRebaseResolver.Resolution resolution;

                    /**
                     * Creates a new code preserving method visitor.
                     *
                     * @param actualMethodVisitor The method visitor of the actual method.
                     * @param entry               The method pool entry to apply.
                     * @param methodDescription   A description of the actual method.
                     */
                    protected CodePreservingMethodVisitor(MethodVisitor actualMethodVisitor,
                                                          MethodPool.Entry entry,
                                                          MethodDescription methodDescription) {
                        super(ASM_API_VERSION, actualMethodVisitor);
                        this.actualMethodVisitor = actualMethodVisitor;
                        this.entry = entry;
                        this.methodDescription = methodDescription;
                        this.resolution = methodRebaseResolver.resolve(methodDescription);
                        entry.applyHead(actualMethodVisitor, methodDescription);
                    }

                    @Override
                    public AnnotationVisitor visitAnnotationDefault() {
                        return IGNORE_ANNOTATION; // Annotation types can never be rebased.
                    }

                    @Override
                    public void visitCode() {
                        entry.applyBody(actualMethodVisitor, implementationContext, methodDescription);
                        actualMethodVisitor.visitEnd();
                        mv = resolution.isRebased()
                                ? cv.visitMethod(resolution.getResolvedMethod().getModifiers(),
                                resolution.getResolvedMethod().getInternalName(),
                                resolution.getResolvedMethod().getDescriptor(),
                                resolution.getResolvedMethod().getGenericSignature(),
                                resolution.getResolvedMethod().getExceptionTypes().toInternalNames())
                                : IGNORE_METHOD;
                        super.visitCode();
                    }

                    @Override
                    public void visitMaxs(int maxStack, int maxLocals) {
                        super.visitMaxs(maxStack, Math.max(maxLocals, resolution.getResolvedMethod().getStackSize()));
                    }

                    @Override
                    public String toString() {
                        return "TypeWriter.Default.ForInlining.RedefinitionClassVisitor.CodePreservingMethodVisitor{" +
                                "classVisitor=" + TypeWriter.Default.ForInlining.RedefinitionClassVisitor.this +
                                ", actualMethodVisitor=" + actualMethodVisitor +
                                ", entry=" + entry +
                                ", methodDescription=" + methodDescription +
                                ", resolution=" + resolution +
                                '}';
                    }
                }

                /**
                 * A method visitor that obtains all attributes and annotations of a method that is found in the
                 * class file but discards all code.
                 */
                protected class AttributeObtainingMethodVisitor extends MethodVisitor {

                    /**
                     * The method visitor to which the actual method is to be written to.
                     */
                    private final MethodVisitor actualMethodVisitor;

                    /**
                     * The method pool entry to apply.
                     */
                    private final MethodPool.Entry entry;

                    /**
                     * A description of the method that is currently written.
                     */
                    private final MethodDescription methodDescription;

                    /**
                     * Creates a new attribute obtaining method visitor.
                     *
                     * @param actualMethodVisitor The method visitor of the actual method.
                     * @param entry               The method pool entry to apply.
                     * @param methodDescription   A description of the actual method.
                     */
                    protected AttributeObtainingMethodVisitor(MethodVisitor actualMethodVisitor,
                                                              MethodPool.Entry entry,
                                                              MethodDescription methodDescription) {
                        super(ASM_API_VERSION, actualMethodVisitor);
                        this.actualMethodVisitor = actualMethodVisitor;
                        this.entry = entry;
                        this.methodDescription = methodDescription;
                        entry.applyHead(actualMethodVisitor, methodDescription);
                    }

                    @Override
                    public AnnotationVisitor visitAnnotationDefault() {
                        return IGNORE_ANNOTATION;
                    }

                    @Override
                    public void visitCode() {
                        mv = IGNORE_METHOD;
                    }

                    @Override
                    public void visitEnd() {
                        entry.applyBody(actualMethodVisitor, implementationContext, methodDescription);
                        actualMethodVisitor.visitEnd();
                    }

                    @Override
                    public String toString() {
                        return "TypeWriter.Default.ForInlining.RedefinitionClassVisitor.AttributeObtainingMethodVisitor{" +
                                "classVisitor=" + TypeWriter.Default.ForInlining.RedefinitionClassVisitor.this +
                                ", actualMethodVisitor=" + actualMethodVisitor +
                                ", entry=" + entry +
                                ", methodDescription=" + methodDescription +
                                '}';
                    }
                }

                /**
                 * A code injection for the type initializer that invokes a method representing the original type initializer
                 * which is copied to a static method.
                 */
                protected class TypeInitializerInjection implements Implementation.Context.ExtractableView.InjectedCode {

                    /**
                     * The modifiers for the method that consumes the original type initializer.
                     */
                    private static final int TYPE_INITIALIZER_PROXY_MODIFIERS = Opcodes.ACC_STATIC | Opcodes.ACC_PRIVATE | Opcodes.ACC_SYNTHETIC;

                    /**
                     * A prefix for the name of the method that represents the original type initializer.
                     */
                    private static final String TYPE_INITIALIZER_PROXY_PREFIX = "originalTypeInitializer";

                    /**
                     * The method to which the original type initializer code is to be written to.
                     */
                    private final MethodDescription injectorProxyMethod;

                    /**
                     * Creates a new type initializer injection.
                     */
                    private TypeInitializerInjection() {
                        injectorProxyMethod = new MethodDescription.Latent(
                                String.format("%s$%s", TYPE_INITIALIZER_PROXY_PREFIX, RandomString.make()),
                                instrumentedType,
                                TypeDescription.VOID,
                                new TypeList.Empty(),
                                TYPE_INITIALIZER_PROXY_MODIFIERS,
                                Collections.<TypeDescription>emptyList());
                    }

                    @Override
                    public ByteCodeAppender getByteCodeAppender() {
                        return new ByteCodeAppender.Simple(MethodInvocation.invoke(injectorProxyMethod));
                    }

                    @Override
                    public boolean isDefined() {
                        return true;
                    }

                    /**
                     * Returns the proxy method to which the original type initializer code is written to.
                     *
                     * @return A method description of this proxy method.
                     */
                    public MethodDescription getInjectorProxyMethod() {
                        return injectorProxyMethod;
                    }

                    @Override
                    public String toString() {
                        return "TypeWriter.Default.ForInlining.RedefinitionClassVisitor.TypeInitializerInjection{" +
                                "classVisitor=" + TypeWriter.Default.ForInlining.RedefinitionClassVisitor.this +
                                ", injectorProxyMethod=" + injectorProxyMethod +
                                '}';
                    }
                }
            }
        }

        /**
         * A type writer that creates a class file that is not based upon another, existing class.
         *
         * @param <U> The best known loaded type for the dynamically created type.
         */
        public static class ForCreation<U> extends Default<U> {

            /**
             * Creates a new type writer for creating a new type.
             *
             * @param instrumentedType            The instrumented type that is to be written.
             * @param loadedTypeInitializer       The loaded type initializer of the instrumented type.
             * @param typeInitializer             The type initializer of the instrumented type.
             * @param explicitAuxiliaryTypes      A list of explicit auxiliary types that are to be added to the created dynamic type.
             * @param classFileVersion            The class file version of the written type.
             * @param auxiliaryTypeNamingStrategy A naming strategy that is used for naming auxiliary types.
             * @param classVisitorWrapper         A class visitor wrapper to apply during instrumentation.
             * @param attributeAppender           The type attribute appender to apply.
             * @param fieldPool                   The field pool to be used for instrumenting fields.
             * @param methodPool                  The method pool to be used for instrumenting methods.
             * @param instrumentedMethods         A list of all instrumented methods.
             */
            protected ForCreation(TypeDescription instrumentedType,
                                  LoadedTypeInitializer loadedTypeInitializer,
                                  InstrumentedType.TypeInitializer typeInitializer,
                                  List<DynamicType> explicitAuxiliaryTypes,
                                  ClassFileVersion classFileVersion,
                                  AuxiliaryType.NamingStrategy auxiliaryTypeNamingStrategy,
                                  ClassVisitorWrapper classVisitorWrapper,
                                  TypeAttributeAppender attributeAppender,
                                  FieldPool fieldPool,
                                  MethodPool methodPool,
                                  MethodList instrumentedMethods) {
                super(instrumentedType,
                        loadedTypeInitializer,
                        typeInitializer,
                        explicitAuxiliaryTypes,
                        classFileVersion,
                        auxiliaryTypeNamingStrategy,
                        classVisitorWrapper,
                        attributeAppender,
                        fieldPool,
                        methodPool,
                        instrumentedMethods);
            }

            @Override
            public byte[] create(Implementation.Context.ExtractableView implementationContext) {
                ClassWriter classWriter = new ClassWriter(ASM_MANUAL_FLAG);
                ClassVisitor classVisitor = classVisitorWrapper.wrap(new ValidatingClassVisitor(classWriter));
                classVisitor.visit(classFileVersion.getVersionNumber(),
                        instrumentedType.getActualModifiers(!instrumentedType.isInterface()),
                        instrumentedType.getInternalName(),
                        instrumentedType.getGenericSignature(),
                        (instrumentedType.getSuperType() == null
                                ? TypeDescription.OBJECT
                                : instrumentedType.getSuperType()).getInternalName(),
                        instrumentedType.getInterfaces().toInternalNames());
                attributeAppender.apply(classVisitor, instrumentedType);
                for (FieldDescription fieldDescription : instrumentedType.getDeclaredFields()) {
                    fieldPool.target(fieldDescription).apply(classVisitor, fieldDescription);
                }
                for (MethodDescription methodDescription : instrumentedMethods) {
                    methodPool.target(methodDescription).apply(classVisitor, implementationContext, methodDescription);
                }
                implementationContext.drain(classVisitor, methodPool, Implementation.Context.ExtractableView.InjectedCode.None.INSTANCE);
                classVisitor.visitEnd();
                return classWriter.toByteArray();
            }

            @Override
            public String toString() {
                return "TypeWriter.Default.ForCreation{" +
                        "instrumentedType=" + instrumentedType +
                        ", loadedTypeInitializer=" + loadedTypeInitializer +
                        ", typeInitializer=" + typeInitializer +
                        ", explicitAuxiliaryTypes=" + explicitAuxiliaryTypes +
                        ", classFileVersion=" + classFileVersion +
                        ", auxiliaryTypeNamingStrategy=" + auxiliaryTypeNamingStrategy +
                        ", classVisitorWrapper=" + classVisitorWrapper +
                        ", attributeAppender=" + attributeAppender +
                        ", fieldPool=" + fieldPool +
                        ", methodPool=" + methodPool +
                        ", instrumentedMethods=" + instrumentedMethods +
                        "}";
            }
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/dynamic/scaffold/inline/InlineInstrumentedType.java
package net.bytebuddy.dynamic.scaffold.inline;

import net.bytebuddy.ClassFileVersion;
import net.bytebuddy.NamingStrategy;
import net.bytebuddy.description.annotation.AnnotationList;
import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeList;
import net.bytebuddy.dynamic.scaffold.InstrumentedType;
import net.bytebuddy.implementation.LoadedTypeInitializer;
import net.bytebuddy.implementation.bytecode.ByteCodeAppender;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static net.bytebuddy.matcher.ElementMatchers.named;
import static net.bytebuddy.utility.ByteBuddyCommons.isValidTypeName;
import static net.bytebuddy.utility.ByteBuddyCommons.join;

/**
 * An instrumented type which enhances a given type description by an extending redefinition.
 */
public class InlineInstrumentedType extends InstrumentedType.AbstractBase {

    /**
     * The type which is the base for this instrumented type.
     */
    private final TypeDescription levelType;

    /**
     * The name of the instrumented type.
     */
    private final String name;

    /**
     * The modifiers of the instrumented type.
     */
    private final int modifiers;

    /**
     * The additional interfaces that this type should implement.
     */
    private final List<GenericTypeDescription> interfaces;

    /**
     * Creates a new inlined instrumented type.
     *
     * @param classFileVersion The class file version for the given type.
     * @param levelType        The name of the instrumented type.
     * @param interfaces       The additional interfaces that this type should implement.
     * @param modifiers        The name of the instrumented type.
     * @param namingStrategy   The naming strategy to apply for the given type.
     */
    public InlineInstrumentedType(ClassFileVersion classFileVersion,
                                  TypeDescription levelType,
                                  List<? extends GenericTypeDescription> interfaces,
                                  int modifiers,
                                  NamingStrategy namingStrategy) {
        super(LoadedTypeInitializer.NoOp.INSTANCE,
                TypeInitializer.None.INSTANCE,
                named(levelType.getName()),
                levelType.getTypeVariables(),
                levelType.getDeclaredFields(),
                levelType.getDeclaredMethods());
        this.levelType = levelType;
        this.modifiers = modifiers;
        Set<GenericTypeDescription> interfaceTypes = new HashSet<GenericTypeDescription>(levelType.getInterfacesGen());
        interfaceTypes.addAll(interfaces);
        this.interfaces = new ArrayList<GenericTypeDescription>(interfaceTypes);
        this.name = isValidTypeName(namingStrategy.name(new NamingStrategy.UnnamedType.Default(levelType.getSuperTypeGen(),
                interfaces,
                modifiers,
                classFileVersion)));
    }

    protected InlineInstrumentedType(TypeDescription levelType,
                                     String name,
                                     List<GenericTypeDescription> interfaces,
                                     int modifiers,
                                     List<? extends GenericTypeDescription> typeVariables,
                                     List<? extends FieldDescription> fieldDescriptions,
                                     List<? extends MethodDescription> methodDescriptions,
                                     LoadedTypeInitializer loadedTypeInitializer,
                                     TypeInitializer typeInitializer) {
        super(loadedTypeInitializer,
                typeInitializer,
                named(name),
                typeVariables,
                fieldDescriptions,
                methodDescriptions);
        this.levelType = levelType;
        this.name = name;
        this.modifiers = modifiers;
        this.interfaces = interfaces;
    }

    @Override
    public InstrumentedType withField(String internalName,
                                      GenericTypeDescription fieldType,
                                      int modifiers) {
        FieldDescription additionalField = new FieldDescription.Latent(internalName, this, fieldType, modifiers);
        if (fieldDescriptions.contains(additionalField)) {
            throw new IllegalArgumentException("Field " + additionalField + " is already defined on " + this);
        }
        return new InlineInstrumentedType(levelType,
                name,
                interfaces,
                this.modifiers,
                typeVariables,
                join(fieldDescriptions, additionalField),
                methodDescriptions,
                loadedTypeInitializer,
                typeInitializer);
    }

    @Override
    public InstrumentedType withMethod(String internalName,
                                       GenericTypeDescription returnType,
                                       List<? extends GenericTypeDescription> parameterTypes,
                                       List<? extends GenericTypeDescription> exceptionTypes,
                                       int modifiers) {
        MethodDescription additionalMethod = new MethodDescription.Latent(internalName,
                this,
                returnType,
                parameterTypes,
                modifiers,
                exceptionTypes);
        if (methodDescriptions.contains(additionalMethod)) {
            throw new IllegalArgumentException("Method " + additionalMethod + " is already defined on " + this);
        }
        return new InlineInstrumentedType(levelType,
                name,
                interfaces,
                this.modifiers,
                typeVariables,
                fieldDescriptions,
                join(methodDescriptions, additionalMethod),
                loadedTypeInitializer,
                typeInitializer);
    }

    @Override
    public InstrumentedType withInitializer(LoadedTypeInitializer loadedTypeInitializer) {
        return new InlineInstrumentedType(levelType,
                name,
                interfaces,
                modifiers,
                typeVariables,
                fieldDescriptions,
                methodDescriptions,
                new LoadedTypeInitializer.Compound(this.loadedTypeInitializer, loadedTypeInitializer),
                typeInitializer);
    }

    @Override
    public InstrumentedType withInitializer(ByteCodeAppender byteCodeAppender) {
        return new InlineInstrumentedType(levelType,
                name,
                interfaces,
                modifiers,
                typeVariables,
                fieldDescriptions,
                methodDescriptions,
                loadedTypeInitializer,
                typeInitializer.expandWith(byteCodeAppender));
    }

    @Override
    public GenericTypeDescription getSuperTypeGen() {
        return levelType.getSuperTypeGen();
    }

    @Override
    public GenericTypeList getInterfacesGen() {
        return new GenericTypeList.Explicit(interfaces);
    }

    @Override
    public String getName() {
        return name;
    }

    @Override
    public int getModifiers() {
        return modifiers;
    }

    @Override
    public AnnotationList getDeclaredAnnotations() {
        return levelType.getDeclaredAnnotations();
    }

    @Override
    public AnnotationList getInheritedAnnotations() {
        return levelType.getInheritedAnnotations();
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/implementation/FieldAccessor.java
package net.bytebuddy.implementation;

import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.field.FieldList;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.modifier.ModifierContributor;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.dynamic.TargetType;
import net.bytebuddy.dynamic.scaffold.InstrumentedType;
import net.bytebuddy.implementation.bytecode.ByteCodeAppender;
import net.bytebuddy.implementation.bytecode.StackManipulation;
import net.bytebuddy.implementation.bytecode.assign.Assigner;
import net.bytebuddy.implementation.bytecode.member.FieldAccess;
import net.bytebuddy.implementation.bytecode.member.MethodReturn;
import net.bytebuddy.implementation.bytecode.member.MethodVariableAccess;
import net.bytebuddy.utility.ByteBuddyCommons;
import org.objectweb.asm.MethodVisitor;

import static net.bytebuddy.matcher.ElementMatchers.*;
import static net.bytebuddy.utility.ByteBuddyCommons.*;

/**
 * Defines a method to access a given field by following the Java bean conventions for getters and setters:
 * <ul>
 * <li>Getter: A method named {@code getFoo()} will be instrumented to read and return the value of a field {@code foo}
 * or another field if one was specified explicitly. If a property is of type {@link java.lang.Boolean} or
 * {@code boolean}, the name {@code isFoo()} is also permitted.</li>
 * <li>Setter: A method named {@code setFoo(value)} will be instrumented to write the given argument {@code value}
 * to a field {@code foo} or to another field if one was specified explicitly.</li>
 * </ul>
 */
public abstract class FieldAccessor implements Implementation {

    /**
     * The assigner to use.
     */
    protected final Assigner assigner;

    /**
     * {@code true} if the runtime type of the field's value should be considered when a field
     * is accessed.
     */
    protected final boolean dynamicallyTyped;

    /**
     * Creates a new field accessor.
     *
     * @param assigner         The assigner to use.
     * @param dynamicallyTyped {@code true} if a field value's runtime type should be considered.
     */
    protected FieldAccessor(Assigner assigner, boolean dynamicallyTyped) {
        this.assigner = assigner;
        this.dynamicallyTyped = dynamicallyTyped;
    }

    /**
     * Defines a field accessor where any access is targeted to a field named {@code name}.
     *
     * @param name The name of the field to be accessed.
     * @return A field accessor for a field of a given name.
     */
    public static FieldDefinable ofField(String name) {
        return new ForNamedField(Assigner.DEFAULT, Assigner.STATICALLY_TYPED, isValidIdentifier(name));
    }

    /**
     * Defines a field accessor where any access is targeted to a field that matches the methods
     * name with the Java specification for bean properties, i.e. a method {@code getFoo} or {@code setFoo(value)}
     * will either read or write a field named {@code foo}.
     *
     * @return A field accessor that follows the Java naming conventions for bean properties.
     */
    public static OwnerTypeLocatable ofBeanProperty() {
        return of(FieldNameExtractor.ForBeanProperty.INSTANCE);
    }

    /**
     * Defines a custom strategy for determining the field that is accessed by this field accessor.
     *
     * @param fieldNameExtractor The field name extractor to use.
     * @return A field accessor using the given field name extractor.
     */
    public static OwnerTypeLocatable of(FieldNameExtractor fieldNameExtractor) {
        return new ForUnnamedField(Assigner.DEFAULT, Assigner.STATICALLY_TYPED, nonNull(fieldNameExtractor));
    }

    /**
     * Applies a field getter implementation.
     *
     * @param methodVisitor         The method visitor to write any instructions to.
     * @param implementationContext The implementation context of the current implementation.
     * @param fieldDescription      The description of the field to read.
     * @param methodDescription     The method that is target of the implementation.
     * @return The required size of the operand stack and local variable array for this implementation.
     */
    protected ByteCodeAppender.Size applyGetter(MethodVisitor methodVisitor,
                                                Implementation.Context implementationContext,
                                                FieldDescription fieldDescription,
                                                MethodDescription methodDescription) {
        StackManipulation stackManipulation = assigner.assign(fieldDescription.getFieldType(),
                methodDescription.getReturnType(),
                dynamicallyTyped);
        if (!stackManipulation.isValid()) {
            throw new IllegalStateException("Getter type of " + methodDescription + " is not compatible with " + fieldDescription);
        }
        return apply(methodVisitor,
                implementationContext,
                fieldDescription,
                methodDescription,
                new StackManipulation.Compound(
                        FieldAccess.forField(fieldDescription).getter(),
                        stackManipulation
                )
        );
    }

    /**
     * Applies a field setter implementation.
     *
     * @param methodVisitor         The method visitor to write any instructions to.
     * @param implementationContext The implementation context of the current implementation.
     * @param fieldDescription      The description of the field to write to.
     * @param methodDescription     The method that is target of the instrumentation.
     * @return The required size of the operand stack and local variable array for this implementation.
     */
    protected ByteCodeAppender.Size applySetter(MethodVisitor methodVisitor,
                                                Implementation.Context implementationContext,
                                                FieldDescription fieldDescription,
                                                MethodDescription methodDescription) {
        StackManipulation stackManipulation = assigner.assign(methodDescription.getParameters().get(0).getType(),
                fieldDescription.getFieldType(),
                dynamicallyTyped);
        if (!stackManipulation.isValid()) {
            throw new IllegalStateException("Setter type of " + methodDescription + " is not compatible with " + fieldDescription);
        } else if (fieldDescription.isFinal()) {
            throw new IllegalArgumentException("Cannot apply setter on final field " + fieldDescription);
        }
        return apply(methodVisitor,
                implementationContext,
                fieldDescription,
                methodDescription,
                new StackManipulation.Compound(
                        MethodVariableAccess.forType(fieldDescription.getFieldType())
                                .loadOffset(methodDescription.getParameters().get(0).getOffset()),
                        stackManipulation,
                        FieldAccess.forField(fieldDescription).putter()
                )
        );
    }

    /**
     * A generic implementation of the application of a {@link net.bytebuddy.implementation.bytecode.ByteCodeAppender}.
     *
     * @param methodVisitor         The method visitor to write any instructions to.
     * @param implementationContext The implementation context of the current implementation.
     * @param fieldDescription      The description of the field to access.
     * @param methodDescription     The method that is target of the implementation.
     * @param fieldAccess           The manipulation that represents the field access.
     * @return A suitable {@link net.bytebuddy.implementation.bytecode.ByteCodeAppender}.
     */
    private ByteCodeAppender.Size apply(MethodVisitor methodVisitor,
                                        Implementation.Context implementationContext,
                                        FieldDescription fieldDescription,
                                        MethodDescription methodDescription,
                                        StackManipulation fieldAccess) {
        if (methodDescription.isStatic() && !fieldDescription.isStatic()) {
            throw new IllegalArgumentException("Cannot call instance field "
                    + fieldDescription + " from static method " + methodDescription);
        }
        StackManipulation.Size stackSize = new StackManipulation.Compound(
                fieldDescription.isStatic()
                        ? StackManipulation.LegalTrivial.INSTANCE
                        : MethodVariableAccess.REFERENCE.loadOffset(0),
                fieldAccess,
                MethodReturn.returning(methodDescription.getReturnType())
        ).apply(methodVisitor, implementationContext);
        return new ByteCodeAppender.Size(stackSize.getMaximalSize(), methodDescription.getStackSize());
    }

    /**
     * Locates a field's name.
     *
     * @param targetMethod The method that is target of the implementation.
     * @return The name of the field to be located for this implementation.
     */
    protected abstract String getFieldName(MethodDescription targetMethod);

    @Override
    public boolean equals(Object other) {
        return this == other || !(other == null || getClass() != other.getClass())
                && dynamicallyTyped == ((FieldAccessor) other).dynamicallyTyped
                && assigner.equals(((FieldAccessor) other).assigner);
    }

    @Override
    public int hashCode() {
        return 31 * assigner.hashCode() + (dynamicallyTyped ? 1 : 0);
    }

    /**
     * A field locator allows to determine a field name for a given method.
     */
    public interface FieldLocator {

        /**
         * Locates a field of a given name or throws an exception if no field with such a name exists.
         *
         * @param name The name of the field to locate.
         * @return A representation of this field.
         */
        FieldDescription locate(String name);

        /**
         * A factory that only looks up fields in the instrumented type.
         */
        enum ForInstrumentedType implements Factory {

            /**
             * The singleton instance.
             */
            INSTANCE;

            @Override
            public FieldLocator make(TypeDescription instrumentedType) {
                return new ForGivenType(instrumentedType, instrumentedType);
            }

            @Override
            public String toString() {
                return "FieldAccessor.FieldLocator.ForInstrumentedType." + name();
            }
        }

        /**
         * A factory for creating a {@link net.bytebuddy.implementation.FieldAccessor.FieldLocator}.
         */
        interface Factory {

            /**
             * Creates a field locator.
             *
             * @param instrumentedType The instrumented type onto which the field locator is to be applied.
             * @return The field locator for locating fields on a given type.
             */
            FieldLocator make(TypeDescription instrumentedType);
        }

        /**
         * A field locator that finds a type by traversing the type hierarchy beginning with fields defined
         * in the most specific subclass traversing the class hierarchy down to the least specific type.
         * This emulates the Java language's field access where fields are shadowed when an extending class defines
         * a field with identical name.
         */
        class ForInstrumentedTypeHierarchy implements FieldLocator {

            /**
             * The instrumented type for which a field is located.
             */
            private final TypeDescription instrumentedType;

            /**
             * Creates a field locator that follows the type hierarchy.
             *
             * @param instrumentedType The instrumented type onto which the field locator is to be applied.
             */
            public ForInstrumentedTypeHierarchy(TypeDescription instrumentedType) {
                this.instrumentedType = instrumentedType;
            }

            @Override
            public FieldDescription locate(String name) {
                TypeDescription currentType = instrumentedType;
                do {
                    FieldList fieldList = currentType.getDeclaredFields().filter(named(name).and(isVisibleTo(instrumentedType)));
                    if (fieldList.size() == 1) {
                        return fieldList.getOnly();
                    }
                } while (!(currentType = currentType.getSuperType()).represents(Object.class));
                throw new IllegalArgumentException("There is no field '" + name + " that is visible to " + instrumentedType);
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && instrumentedType.equals(((ForInstrumentedTypeHierarchy) other).instrumentedType);
            }

            @Override
            public int hashCode() {
                return instrumentedType.hashCode();
            }

            @Override
            public String toString() {
                return "FieldAccessor.FieldLocator.ForInstrumentedTypeHierarchy{instrumentedType=" + instrumentedType + '}';
            }

            /**
             * A field locator factory creating a
             * {@link net.bytebuddy.implementation.FieldAccessor.FieldLocator.ForInstrumentedTypeHierarchy}.
             */
            public enum Factory implements FieldLocator.Factory {

                /**
                 * The singleton instance.
                 */
                INSTANCE;

                @Override
                public FieldLocator make(TypeDescription instrumentedType) {
                    return new ForInstrumentedTypeHierarchy(instrumentedType);
                }

                @Override
                public String toString() {
                    return "FieldAccessor.FieldLocator.ForInstrumentedTypeHierarchy.Factory." + name();
                }
            }
        }

        /**
         * A field locator that only looks up fields that are defined for a given type.
         */
        class ForGivenType implements FieldLocator {

            /**
             * The target type for which a field should be accessed.
             */
            private final TypeDescription targetType;

            /**
             * The instrumented type onto which the field locator is to be applied.
             */
            private final TypeDescription instrumentedType;

            /**
             * Creates a new field locator for a given type.
             *
             * @param targetType       The type for which fields are to be looked up.
             * @param instrumentedType The instrumented type onto which the field locator is to be applied.
             */
            public ForGivenType(TypeDescription targetType, TypeDescription instrumentedType) {
                this.targetType = targetType;
                this.instrumentedType = instrumentedType;
            }

            @Override
            public FieldDescription locate(String name) {
                FieldList fieldList = targetType.getDeclaredFields().filter(named(name).and(isVisibleTo(instrumentedType)));
                if (fieldList.size() != 1) {
                    throw new IllegalArgumentException("No field named " + name + " on " + targetType + " is visible to " + instrumentedType);
                }
                return fieldList.getOnly();
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && instrumentedType.equals(((ForGivenType) other).instrumentedType)
                        && targetType.equals(((ForGivenType) other).targetType);
            }

            @Override
            public int hashCode() {
                return 31 * instrumentedType.hashCode() + targetType.hashCode();
            }

            @Override
            public String toString() {
                return "FieldAccessor.FieldLocator.ForGivenType{" +
                        "targetType=" + targetType +
                        ", instrumentedType=" + instrumentedType +
                        '}';
            }

            /**
             * A factory for a field locator locating given type.
             */
            public static class Factory implements FieldLocator.Factory {

                /**
                 * The type to locate.
                 */
                private final TypeDescription targetType;

                /**
                 * Creates a new field locator factory for a given type.
                 *
                 * @param targetType The type for which fields are to be looked up.
                 */
                public Factory(TypeDescription targetType) {
                    this.targetType = targetType;
                }

                @Override
                public FieldLocator make(TypeDescription instrumentedType) {
                    return new ForGivenType(targetType, instrumentedType);
                }

                @Override
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && targetType.equals(((Factory) other).targetType);
                }

                @Override
                public int hashCode() {
                    return targetType.hashCode();
                }

                @Override
                public String toString() {
                    return "FieldAccessor.FieldLocator.ForGivenType.Factory{targetType=" + targetType + '}';
                }
            }
        }
    }

    /**
     * A field name extractor is responsible for determining a field name to a method that is implemented
     * to access this method.
     */
    public interface FieldNameExtractor {

        /**
         * Extracts a field name to be accessed by a getter or setter method.
         *
         * @param methodDescription The method for which a field name is to be determined.
         * @return The name of the field to be accessed by this method.
         */
        String fieldNameFor(MethodDescription methodDescription);

        /**
         * A {@link net.bytebuddy.implementation.FieldAccessor.FieldNameExtractor} that determines a field name
         * according to the rules of Java bean naming conventions.
         */
        enum ForBeanProperty implements FieldNameExtractor {

            /**
             * The singleton instance.
             */
            INSTANCE;

            @Override
            public String fieldNameFor(MethodDescription methodDescription) {
                String name = methodDescription.getInternalName();
                int crop;
                if (name.startsWith("get") || name.startsWith("set")) {
                    crop = 3;
                } else if (name.startsWith("is")) {
                    crop = 2;
                } else {
                    throw new IllegalArgumentException(methodDescription + " does not follow Java bean naming conventions");
                }
                name = name.substring(crop);
                if (name.length() == 0) {
                    throw new IllegalArgumentException(methodDescription + " does not specify a bean name");
                }
                return Character.toLowerCase(name.charAt(0)) + name.substring(1);
            }

            @Override
            public String toString() {
                return "FieldAccessor.FieldNameExtractor.ForBeanProperty." + name();
            }
        }
    }

    /**
     * A field accessor that can be configured to use a given assigner and runtime type use configuration.
     */
    public interface AssignerConfigurable extends Implementation {

        /**
         * Returns a field accessor that is identical to this field accessor but uses the given assigner
         * and runtime type use configuration.
         *
         * @param assigner         The assigner to use.
         * @param dynamicallyTyped {@code true} if a field value's runtime type should be considered.
         * @return This field accessor with the given assigner and runtime type use configuration.
         */
        Implementation withAssigner(Assigner assigner, boolean dynamicallyTyped);
    }

    /**
     * A field accessor that can be configured to locate a field in a specific manner.
     */
    public interface OwnerTypeLocatable extends AssignerConfigurable {

        /**
         * Determines that a field should only be considered when it was defined in a given type.
         *
         * @param type The type to be considered.
         * @return This field accessor which will only considered fields that are defined in the given type.
         */
        AssignerConfigurable in(Class<?> type);

        /**
         * Determines that a field should only be considered when it was defined in a given type.
         *
         * @param typeDescription A description of the type to be considered.
         * @return This field accessor which will only considered fields that are defined in the given type.
         */
        AssignerConfigurable in(TypeDescription typeDescription);

        /**
         * Determines that a field should only be considered when it was identified by a field locator that is
         * produced by the given factory.
         *
         * @param fieldLocatorFactory A factory that will produce a field locator that will be used to find locate
         *                            a field to be accessed.
         * @return This field accessor which will only considered fields that are defined in the given type.
         */
        AssignerConfigurable in(FieldLocator.Factory fieldLocatorFactory);
    }

    /**
     * Determines a field accessor that accesses a field of a given name which might not yet be
     * defined.
     */
    public interface FieldDefinable extends OwnerTypeLocatable {

        /**
         * Defines a field with the given name in the instrumented type.
         *
         * @param type     The type of the field.
         * @param modifier The modifiers for the field.
         * @return A field accessor that defines a field of the given type.
         */
        AssignerConfigurable defineAs(Class<?> type, ModifierContributor.ForField... modifier);

        /**
         * Defines a field with the given name in the instrumented type.
         *
         * @param typeDescription The type of the field.
         * @param modifier        The modifiers for the field.
         * @return A field accessor that defines a field of the given type.
         */
        AssignerConfigurable defineAs(TypeDescription typeDescription, ModifierContributor.ForField... modifier);
    }

    /**
     * Implementation of a field accessor implementation where a field is identified by a method's name following
     * the Java specification for bean properties.
     */
    protected static class ForUnnamedField extends FieldAccessor implements OwnerTypeLocatable {

        /**
         * A factory for creating a field locator for implementing this field accessor.
         */
        private final FieldLocator.Factory fieldLocatorFactory;

        /**
         * The field name extractor to be used.
         */
        private final FieldNameExtractor fieldNameExtractor;

        /**
         * Creates a new field accessor implementation.
         *
         * @param assigner           The assigner to use.
         * @param dynamicallyTyped   {@code true} if a field value's runtime type should be considered.
         * @param fieldNameExtractor The field name extractor to use.
         */
        protected ForUnnamedField(Assigner assigner,
                                  boolean dynamicallyTyped,
                                  FieldNameExtractor fieldNameExtractor) {
            this(assigner,
                    dynamicallyTyped,
                    fieldNameExtractor,
                    FieldLocator.ForInstrumentedTypeHierarchy.Factory.INSTANCE);
        }

        /**
         * Creates a new field accessor implementation.
         *
         * @param assigner            The assigner to use.
         * @param dynamicallyTyped    {@code true} if a field value's runtime type should be considered.
         * @param fieldNameExtractor  The field name extractor to use.
         * @param fieldLocatorFactory A factory that will produce a field locator that will be used to find locate
         *                            a field to be accessed.
         */
        protected ForUnnamedField(Assigner assigner,
                                  boolean dynamicallyTyped,
                                  FieldNameExtractor fieldNameExtractor,
                                  FieldLocator.Factory fieldLocatorFactory) {
            super(assigner, dynamicallyTyped);
            this.fieldNameExtractor = fieldNameExtractor;
            this.fieldLocatorFactory = fieldLocatorFactory;
        }

        @Override
        public AssignerConfigurable in(FieldLocator.Factory fieldLocatorFactory) {
            return new ForUnnamedField(assigner, dynamicallyTyped, fieldNameExtractor, nonNull(fieldLocatorFactory));
        }

        @Override
        public AssignerConfigurable in(Class<?> type) {
            return in(new TypeDescription.ForLoadedType(nonNull(type)));
        }

        @Override
        public AssignerConfigurable in(TypeDescription typeDescription) {
            return typeDescription.represents(TargetType.class)
                    ? in(FieldLocator.ForInstrumentedType.INSTANCE)
                    : in(new FieldLocator.ForGivenType.Factory(typeDescription));
        }

        @Override
        public Implementation withAssigner(Assigner assigner, boolean dynamicallyTyped) {
            return new ForUnnamedField(nonNull(assigner), dynamicallyTyped, fieldNameExtractor, fieldLocatorFactory);
        }

        @Override
        public InstrumentedType prepare(InstrumentedType instrumentedType) {
            return instrumentedType;
        }

        @Override
        public ByteCodeAppender appender(Target implementationTarget) {
            return new Appender(fieldLocatorFactory.make(implementationTarget.getTypeDescription()));
        }

        @Override
        protected String getFieldName(MethodDescription targetMethod) {
            return fieldNameExtractor.fieldNameFor(targetMethod);
        }

        @Override
        public boolean equals(Object other) {
            return this == other || !(other == null || getClass() != other.getClass())
                    && super.equals(other)
                    && fieldNameExtractor.equals(((ForUnnamedField) other).fieldNameExtractor)
                    && fieldLocatorFactory.equals(((ForUnnamedField) other).fieldLocatorFactory);
        }

        @Override
        public int hashCode() {
            return 31 * (31 * super.hashCode() + fieldLocatorFactory.hashCode()) + fieldNameExtractor.hashCode();
        }

        @Override
        public String toString() {
            return "FieldAccessor.ForUnnamedField{" +
                    "assigner=" + assigner +
                    "dynamicallyTyped=" + dynamicallyTyped +
                    "fieldLocatorFactory=" + fieldLocatorFactory +
                    "fieldNameExtractor=" + fieldNameExtractor +
                    '}';
        }
    }

    /**
     * Implementation of a field accessor implementation where the field name is given explicitly.
     */
    protected static class ForNamedField extends FieldAccessor implements FieldDefinable {

        /**
         * The name of the field that is accessed.
         */
        private final String fieldName;

        /**
         * The preparation handler for implementing this field accessor.
         */
        private final PreparationHandler preparationHandler;

        /**
         * The field locator factory for implementing this field accessor.
         */
        private final FieldLocator.Factory fieldLocatorFactory;

        /**
         * Creates a field accessor implementation for a field of a given name.
         *
         * @param assigner         The assigner to use.
         * @param dynamicallyTyped {@code true} if a field value's runtime type should be considered.
         * @param fieldName        The name of the field.
         */
        protected ForNamedField(Assigner assigner,
                                boolean dynamicallyTyped,
                                String fieldName) {
            super(assigner, dynamicallyTyped);
            this.fieldName = fieldName;
            preparationHandler = PreparationHandler.NoOp.INSTANCE;
            fieldLocatorFactory = FieldLocator.ForInstrumentedTypeHierarchy.Factory.INSTANCE;
        }

        /**
         * reates a field accessor implementation for a field of a given name.
         *
         * @param fieldName           The name of the field.
         * @param preparationHandler  The preparation handler for potentially defining a field.
         * @param fieldLocatorFactory A factory that will produce a field locator that will be used to find locate
         *                            a field to be accessed.
         * @param assigner            The assigner to use.
         * @param dynamicallyTyped    {@code true} if a field value's runtime type should be considered.
         */
        private ForNamedField(Assigner assigner,
                              boolean dynamicallyTyped,
                              String fieldName,
                              PreparationHandler preparationHandler,
                              FieldLocator.Factory fieldLocatorFactory) {
            super(assigner, dynamicallyTyped);
            this.fieldName = fieldName;
            this.preparationHandler = preparationHandler;
            this.fieldLocatorFactory = fieldLocatorFactory;
        }

        @Override
        public AssignerConfigurable defineAs(Class<?> type, ModifierContributor.ForField... modifier) {
            return defineAs(new TypeDescription.ForLoadedType(nonNull(type)), modifier);
        }

        @Override
        public AssignerConfigurable defineAs(TypeDescription typeDescription, ModifierContributor.ForField... modifier) {
            return new ForNamedField(assigner,
                    dynamicallyTyped,
                    fieldName,
                    PreparationHandler.FieldDefiner.of(fieldName, isActualType(typeDescription), nonNull(modifier)),
                    FieldLocator.ForInstrumentedType.INSTANCE);
        }

        @Override
        public AssignerConfigurable in(FieldLocator.Factory fieldLocatorFactory) {
            return new ForNamedField(assigner,
                    dynamicallyTyped,
                    fieldName,
                    preparationHandler,
                    nonNull(fieldLocatorFactory));
        }

        @Override
        public AssignerConfigurable in(Class<?> type) {
            return in(new TypeDescription.ForLoadedType(nonNull(type)));
        }

        @Override
        public AssignerConfigurable in(TypeDescription typeDescription) {
            return typeDescription.represents(TargetType.class)
                    ? in(FieldLocator.ForInstrumentedType.INSTANCE)
                    : in(new FieldLocator.ForGivenType.Factory(typeDescription));
        }

        @Override
        public Implementation withAssigner(Assigner assigner, boolean dynamicallyTyped) {
            return new ForNamedField(nonNull(assigner),
                    dynamicallyTyped,
                    fieldName,
                    preparationHandler,
                    fieldLocatorFactory);
        }

        @Override
        public InstrumentedType prepare(InstrumentedType instrumentedType) {
            return preparationHandler.prepare(instrumentedType);
        }

        @Override
        public ByteCodeAppender appender(Target implementationTarget) {
            return new Appender(fieldLocatorFactory.make(implementationTarget.getTypeDescription()));
        }

        @Override
        protected String getFieldName(MethodDescription targetMethod) {
            return fieldName;
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (other == null || getClass() != other.getClass()) return false;
            if (!super.equals(other)) return false;
            ForNamedField that = (ForNamedField) other;
            return fieldLocatorFactory.equals(that.fieldLocatorFactory)
                    && fieldName.equals(that.fieldName)
                    && preparationHandler.equals(that.preparationHandler);
        }

        @Override
        public int hashCode() {
            int result = super.hashCode();
            result = 31 * result + fieldName.hashCode();
            result = 31 * result + preparationHandler.hashCode();
            result = 31 * result + fieldLocatorFactory.hashCode();
            return result;
        }

        @Override
        public String toString() {
            return "FieldAccessor.ForNamedField{" +
                    "assigner=" + assigner +
                    "dynamicallyTyped=" + dynamicallyTyped +
                    "fieldName='" + fieldName + '\'' +
                    ", preparationHandler=" + preparationHandler +
                    ", fieldLocatorFactory=" + fieldLocatorFactory +
                    '}';
        }

        /**
         * A preparation handler is responsible for defining a field value on an implementation, if necessary.
         */
        protected interface PreparationHandler {

            /**
             * Prepares the instrumented type.
             *
             * @param instrumentedType The instrumented type to be prepared.
             * @return The readily prepared instrumented type.
             */
            InstrumentedType prepare(InstrumentedType instrumentedType);

            /**
             * A non-operational preparation handler that does not alter the field.
             */
            enum NoOp implements PreparationHandler {

                /**
                 * The singleton instance.
                 */
                INSTANCE;

                @Override
                public InstrumentedType prepare(InstrumentedType instrumentedType) {
                    return instrumentedType;
                }

                @Override
                public String toString() {
                    return "FieldAccessor.ForNamedField.PreparationHandler.NoOp." + name();
                }
            }

            /**
             * A preparation handler that actually defines a field on an instrumented type.
             */
            class FieldDefiner implements PreparationHandler {

                /**
                 * The name of the field that is defined by this preparation handler.
                 */
                private final String name;

                /**
                 * The type of the field that is to be defined.
                 */
                private final TypeDescription typeDescription;

                /**
                 * The modifier of the field that is to be defined.
                 */
                private final int modifiers;

                /**
                 * Creates a new field definer.
                 *
                 * @param name            The name of the field that is defined by this preparation handler.
                 * @param typeDescription The type of the field that is to be defined.
                 * @param modifiers       The modifiers of the field that is to be defined.
                 */
                protected FieldDefiner(String name, TypeDescription typeDescription, int modifiers) {
                    this.name = name;
                    this.typeDescription = typeDescription;
                    this.modifiers = modifiers;
                }

                /**
                 * Creates a new preparation handler that defines a given field.
                 *
                 * @param name            The name of the field that is defined by this preparation handler.
                 * @param typeDescription The type of the field that is to be defined.
                 * @param contributor     The modifiers of the field that is to be defined.
                 * @return A corresponding preparation handler.
                 */
                public static PreparationHandler of(String name, TypeDescription typeDescription, ModifierContributor.ForField... contributor) {
                    return new FieldDefiner(name, typeDescription, resolveModifierContributors(ByteBuddyCommons.FIELD_MODIFIER_MASK, contributor));
                }

                @Override
                public InstrumentedType prepare(InstrumentedType instrumentedType) {
                    return instrumentedType.withField(name, TargetType.resolve(typeDescription, instrumentedType, TargetType.MATCHER), modifiers);
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (other == null || getClass() != other.getClass()) return false;
                    FieldDefiner that = (FieldDefiner) other;
                    return modifiers == that.modifiers
                            && name.equals(that.name)
                            && typeDescription.equals(that.typeDescription);
                }

                @Override
                public int hashCode() {
                    int result = name.hashCode();
                    result = 31 * result + typeDescription.hashCode();
                    result = 31 * result + modifiers;
                    return result;
                }

                @Override
                public String toString() {
                    return "FieldAccessor.ForNamedField.PreparationHandler.FieldDefiner{" +
                            "name='" + name + '\'' +
                            ", typeDescription=" + typeDescription +
                            ", modifiers=" + modifiers +
                            '}';
                }
            }
        }
    }

    /**
     * An byte code appender for an field accessor implementation.
     */
    protected class Appender implements ByteCodeAppender {

        /**
         * The field locator for implementing this appender.
         */
        private final FieldLocator fieldLocator;

        /**
         * Creates a new byte code appender for a field accessor implementation.
         *
         * @param fieldLocator The field locator for this byte code appender.
         */
        protected Appender(FieldLocator fieldLocator) {
            this.fieldLocator = fieldLocator;
        }

        @Override
        public Size apply(MethodVisitor methodVisitor,
                          Implementation.Context implementationContext,
                          MethodDescription instrumentedMethod) {
            if (isConstructor().matches(instrumentedMethod)) {
                throw new IllegalArgumentException("Constructors cannot define beans: " + instrumentedMethod);
            }
            if (takesArguments(0).and(not(returns(void.class))).matches(instrumentedMethod)) {
                return applyGetter(methodVisitor,
                        implementationContext,
                        fieldLocator.locate(getFieldName(instrumentedMethod)),
                        instrumentedMethod);
            } else if (takesArguments(1).and(returns(void.class)).matches(instrumentedMethod)) {
                return applySetter(methodVisitor,
                        implementationContext,
                        fieldLocator.locate(getFieldName(instrumentedMethod)),
                        instrumentedMethod);
            } else {
                throw new IllegalArgumentException("Method " + implementationContext + " is no bean property");
            }
        }

        /**
         * Returns the outer instance.
         *
         * @return The outer instance.
         */
        private FieldAccessor getFieldAccessor() {
            return FieldAccessor.this;
        }

        @Override
        public boolean equals(Object other) {
            return this == other || !(other == null || getClass() != other.getClass())
                    && fieldLocator.equals(((Appender) other).fieldLocator)
                    && FieldAccessor.this.equals(((Appender) other).getFieldAccessor());
        }

        @Override
        public int hashCode() {
            return 31 * FieldAccessor.this.hashCode() + fieldLocator.hashCode();
        }

        @Override
        public String toString() {
            return "FieldAccessor.Appender{" +
                    "fieldLocator=" + fieldLocator +
                    "fieldAccessor=" + FieldAccessor.this +
                    '}';
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/implementation/bind/annotation/FieldProxy.java
package net.bytebuddy.implementation.bind.annotation;

import net.bytebuddy.ByteBuddy;
import net.bytebuddy.ClassFileVersion;
import net.bytebuddy.description.annotation.AnnotationDescription;
import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.field.FieldList;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.method.MethodList;
import net.bytebuddy.description.method.ParameterDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.dynamic.DynamicType;
import net.bytebuddy.dynamic.TargetType;
import net.bytebuddy.dynamic.scaffold.InstrumentedType;
import net.bytebuddy.dynamic.scaffold.subclass.ConstructorStrategy;
import net.bytebuddy.implementation.Implementation;
import net.bytebuddy.implementation.auxiliary.AuxiliaryType;
import net.bytebuddy.implementation.bind.MethodDelegationBinder;
import net.bytebuddy.implementation.bytecode.ByteCodeAppender;
import net.bytebuddy.implementation.bytecode.Duplication;
import net.bytebuddy.implementation.bytecode.StackManipulation;
import net.bytebuddy.implementation.bytecode.TypeCreation;
import net.bytebuddy.implementation.bytecode.assign.Assigner;
import net.bytebuddy.implementation.bytecode.member.FieldAccess;
import net.bytebuddy.implementation.bytecode.member.MethodInvocation;
import net.bytebuddy.implementation.bytecode.member.MethodReturn;
import net.bytebuddy.implementation.bytecode.member.MethodVariableAccess;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

import java.io.Serializable;
import java.lang.annotation.*;
import java.util.Collections;

import static net.bytebuddy.matcher.ElementMatchers.*;
import static net.bytebuddy.utility.ByteBuddyCommons.nonNull;

/**
 * Using this annotation it is possible to access fields by getter and setter types. Before this annotation can be
 * used, it needs to be installed with two types. The getter type must be defined in a single-method interface
 * with a single method that returns an {@link java.lang.Object} type and takes no arguments. The getter interface
 * must similarly return {@code void} and take a single {@link java.lang.Object} argument. After installing these
 * interfaces with the {@link FieldProxy.Binder}, this
 * binder needs to be registered with a {@link net.bytebuddy.implementation.MethodDelegation} before it can be used.
 */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.PARAMETER)
public @interface FieldProxy {

    /**
     * A placeholder name to indicate that a field name should be inferred by the name of the intercepted
     * method by the Java bean naming conventions.
     */
    String BEAN_PROPERTY = "";

    /**
     * Determines if the proxy should be serializable.
     *
     * @return {@code true} if the proxy should be serializable.
     */
    boolean serializableProxy() default false;

    /**
     * Determines the name of the field that is to be accessed. If this property is not set, a field name is inferred
     * by the intercepted method after the Java beans naming conventions.
     *
     * @return The name of the field to be accessed.
     */
    String value() default "";

    /**
     * Determines which type defines the field that is to be accessed. If this property is not set, the most field
     * that is defined highest in the type hierarchy is accessed.
     *
     * @return The type that defines the accessed field.
     */
    Class<?> definingType() default void.class;

    /**
     * A binder for the {@link FieldProxy} annotation.
     */
    class Binder implements TargetMethodAnnotationDrivenBinder.ParameterBinder<FieldProxy> {

        /**
         * A reference to the method that declares the field annotation's defining type property.
         */
        private static final MethodDescription DEFINING_TYPE;

        /**
         * A reference to the method that declares the field annotation's field name property.
         */
        private static final MethodDescription FIELD_NAME;

        /**
         * A reference to the method that declares the field annotation's serializable proxy property.
         */
        private static final MethodDescription SERIALIZABLE_PROXY;

        /*
         * Fetches a reference to all annotation properties.
         */
        static {
            MethodList methodList = new TypeDescription.ForLoadedType(FieldProxy.class).getDeclaredMethods();
            DEFINING_TYPE = methodList.filter(named("definingType")).getOnly();
            FIELD_NAME = methodList.filter(named("value")).getOnly();
            SERIALIZABLE_PROXY = methodList.filter(named("serializableProxy")).getOnly();
        }

        /**
         * The getter method to be implemented by a getter proxy.
         */
        private final MethodDescription getterMethod;

        /**
         * The setter method to be implemented by a setter proxy.
         */
        private final MethodDescription setterMethod;

        /**
         * Creates a new binder for the {@link FieldProxy}
         * annotation.
         *
         * @param getterMethod The getter method to be implemented by a getter proxy.
         * @param setterMethod The setter method to be implemented by a setter proxy.
         */
        protected Binder(MethodDescription getterMethod, MethodDescription setterMethod) {
            this.getterMethod = getterMethod;
            this.setterMethod = setterMethod;
        }

        /**
         * Creates a binder by installing two proxy types which are implemented by this binder if a field getter
         * or a field setter is requested by using the
         * {@link FieldProxy} annotation.
         *
         * @param getterType The type which should be used for getter proxies. The type must
         *                   represent an interface which defines a single method which returns an
         *                   {@link java.lang.Object} return type and does not take any arguments. The use of generics
         *                   is permitted.
         * @param setterType The type which should be uses for setter proxies. The type must
         *                   represent an interface which defines a single method which returns {@code void}
         *                   and takes a signle {@link java.lang.Object}-typed argument. The use of generics
         *                   is permitted.
         * @return A binder for the {@link FieldProxy}
         * annotation.
         */
        public static TargetMethodAnnotationDrivenBinder.ParameterBinder<FieldProxy> install(Class<?> getterType,
                                                                                             Class<?> setterType) {
            return install(new TypeDescription.ForLoadedType(nonNull(getterType)), new TypeDescription.ForLoadedType(nonNull(setterType)));
        }

        /**
         * Creates a binder by installing two proxy types which are implemented by this binder if a field getter
         * or a field setter is requested by using the
         * {@link FieldProxy} annotation.
         *
         * @param getterType The type which should be used for getter proxies. The type must
         *                   represent an interface which defines a single method which returns an
         *                   {@link java.lang.Object} return type and does not take any arguments. The use of generics
         *                   is permitted.
         * @param setterType The type which should be uses for setter proxies. The type must
         *                   represent an interface which defines a single method which returns {@code void}
         *                   and takes a signle {@link java.lang.Object}-typed argument. The use of generics
         *                   is permitted.
         * @return A binder for the {@link FieldProxy}
         * annotation.
         */
        public static TargetMethodAnnotationDrivenBinder.ParameterBinder<FieldProxy> install(TypeDescription getterType,
                                                                                             TypeDescription setterType) {
            MethodDescription getterMethod = onlyMethod(nonNull(getterType));
            if (!getterMethod.getReturnType().represents(Object.class)) {
                throw new IllegalArgumentException(getterMethod + " must take a single Object-typed parameter");
            } else if (getterMethod.getParameters().size() != 0) {
                throw new IllegalArgumentException(getterMethod + " must not declare parameters");
            }
            MethodDescription setterMethod = onlyMethod(nonNull(setterType));
            if (!setterMethod.getReturnType().represents(void.class)) {
                throw new IllegalArgumentException(setterMethod + " must return void");
            } else if (setterMethod.getParameters().size() != 1 || !setterMethod.getParameters().get(0).getType().represents(Object.class)) {
                throw new IllegalArgumentException(setterMethod + " must declare a single Object-typed parameters");
            }
            return new Binder(getterMethod, setterMethod);
        }

        /**
         * Extracts the only method from a given type description which is validated for the required properties for
         * using the type as a proxy base type.
         *
         * @param typeDescription The type description to evaluate.
         * @return The only method which was found to be compatible to the proxy requirements.
         */
        private static MethodDescription onlyMethod(TypeDescription typeDescription) {
            if (!typeDescription.isInterface()) {
                throw new IllegalArgumentException(typeDescription + " is not an interface");
            } else if (typeDescription.getInterfaces().size() > 0) {
                throw new IllegalArgumentException(typeDescription + " must not extend other interfaces");
            } else if (!typeDescription.isPublic()) {
                throw new IllegalArgumentException(typeDescription + " is mot public");
            }
            MethodList methodCandidates = typeDescription.getDeclaredMethods().filter(not(isStatic()));
            if (methodCandidates.size() != 1) {
                throw new IllegalArgumentException(typeDescription + " must declare exactly one non-static method");
            }
            return methodCandidates.getOnly();
        }

        @Override
        public Class<FieldProxy> getHandledType() {
            return FieldProxy.class;
        }

        @Override
        public MethodDelegationBinder.ParameterBinding<?> bind(AnnotationDescription.Loadable<FieldProxy> annotation,
                                                               MethodDescription source,
                                                               ParameterDescription target,
                                                               Implementation.Target implementationTarget,
                                                               Assigner assigner) {
            AccessType accessType;
            if (target.getType().equals(getterMethod.getDeclaringType())) {
                accessType = AccessType.GETTER;
            } else if (target.getType().equals(setterMethod.getDeclaringType())) {
                accessType = AccessType.SETTER;
            } else {
                throw new IllegalStateException(target + " uses a @Field annotation on an non-installed type");
            }
            FieldLocator.Resolution resolution = FieldLocator.of(annotation.getValue(FIELD_NAME, String.class), source)
                    .lookup(annotation.getValue(DEFINING_TYPE, TypeDescription.class), implementationTarget.getTypeDescription())
                    .resolve(implementationTarget.getTypeDescription());
            return resolution.isValid()
                    ? new MethodDelegationBinder.ParameterBinding.Anonymous(new AccessorProxy(
                    resolution.getFieldDescription(),
                    assigner,
                    implementationTarget.getTypeDescription(),
                    accessType,
                    annotation.getValue(SERIALIZABLE_PROXY, Boolean.class)))
                    : MethodDelegationBinder.ParameterBinding.Illegal.INSTANCE;
        }

        @Override
        public boolean equals(Object other) {
            return this == other || !(other == null || getClass() != other.getClass())
                    && getterMethod.equals(((Binder) other).getterMethod)
                    && setterMethod.equals(((Binder) other).setterMethod);
        }

        @Override
        public int hashCode() {
            int result = getterMethod.hashCode();
            result = 31 * result + setterMethod.hashCode();
            return result;
        }

        @Override
        public String toString() {
            return "FieldProxy.Binder{" +
                    "getterMethod=" + getterMethod +
                    ", setterMethod=" + setterMethod +
                    '}';
        }

        /**
         * Represents an implementation for implementing a proxy type constructor when a static field is accessed.
         */
        protected enum StaticFieldConstructor implements Implementation {

            /**
             * The singleton instance.
             */
            INSTANCE;

            /**
             * A reference of the {@link Object} type default constructor.
             */
            protected final MethodDescription objectTypeDefaultConstructor;

            /**
             * Creates the constructor call singleton.
             */
            StaticFieldConstructor() {
                objectTypeDefaultConstructor = TypeDescription.OBJECT.getDeclaredMethods()
                        .filter(isConstructor())
                        .getOnly();
            }

            @Override
            public InstrumentedType prepare(InstrumentedType instrumentedType) {
                return instrumentedType;
            }

            @Override
            public ByteCodeAppender appender(Target implementationTarget) {
                return new ByteCodeAppender.Simple(MethodVariableAccess.REFERENCE.loadOffset(0),
                        MethodInvocation.invoke(objectTypeDefaultConstructor),
                        MethodReturn.VOID);
            }

            @Override
            public String toString() {
                return "FieldProxy.Binder.StaticFieldConstructor." + name();
            }
        }

        /**
         * Determines the way a field is to be accessed.
         */
        protected enum AccessType {

            /**
             * Represents getter access for a field.
             */
            GETTER {
                @Override
                protected TypeDescription proxyType(MethodDescription getterMethod, MethodDescription setterMethod) {
                    return getterMethod.getDeclaringType();
                }

                @Override
                protected Implementation access(FieldDescription fieldDescription,
                                                Assigner assigner,
                                                AuxiliaryType.MethodAccessorFactory methodAccessorFactory) {
                    return new Getter(fieldDescription, assigner, methodAccessorFactory);
                }
            },

            /**
             * Represents setter access for a field.
             */
            SETTER {
                @Override
                protected TypeDescription proxyType(MethodDescription getterMethod, MethodDescription setterMethod) {
                    return setterMethod.getDeclaringType();
                }

                @Override
                protected Implementation access(FieldDescription fieldDescription,
                                                Assigner assigner,
                                                AuxiliaryType.MethodAccessorFactory methodAccessorFactory) {
                    return new Setter(fieldDescription, assigner, methodAccessorFactory);
                }
            };


            /**
             * Locates the type to be implemented by a field accessor proxy.
             *
             * @param getterMethod The getter method to be implemented by a getter proxy.
             * @param setterMethod The setter method to be implemented by a setter proxy.
             * @return The correct proxy type for the represented sort of accessor.
             */
            protected abstract TypeDescription proxyType(MethodDescription getterMethod, MethodDescription setterMethod);

            /**
             * Returns an implementation that implements the sort of accessor implementation that is represented by
             * this instance.
             *
             * @param fieldDescription      The field to be accessed.
             * @param assigner              The assigner to use.
             * @param methodAccessorFactory The accessed type's method accessor factory.
             * @return A suitable implementation.
             */
            protected abstract Implementation access(FieldDescription fieldDescription,
                                                     Assigner assigner,
                                                     AuxiliaryType.MethodAccessorFactory methodAccessorFactory);

            @Override
            public String toString() {
                return "FieldProxy.Binder.AccessType." + name();
            }

            /**
             * Implementation for a getter method.
             */
            protected static class Getter implements Implementation {

                /**
                 * The field that is being accessed.
                 */
                private final FieldDescription accessedField;

                /**
                 * The assigner to use.
                 */
                private final Assigner assigner;

                /**
                 * The accessed type's method accessor factory.
                 */
                private final AuxiliaryType.MethodAccessorFactory methodAccessorFactory;

                /**
                 * Creates a new getter implementation.
                 *
                 * @param accessedField         The field that is being accessed.
                 * @param assigner              The assigner to use.
                 * @param methodAccessorFactory The accessed type's method accessor factory.
                 */
                protected Getter(FieldDescription accessedField,
                                 Assigner assigner,
                                 AuxiliaryType.MethodAccessorFactory methodAccessorFactory) {
                    this.accessedField = accessedField;
                    this.assigner = assigner;
                    this.methodAccessorFactory = methodAccessorFactory;
                }

                @Override
                public InstrumentedType prepare(InstrumentedType instrumentedType) {
                    return instrumentedType;
                }

                @Override
                public ByteCodeAppender appender(Target implementationTarget) {
                    return new Appender(implementationTarget);
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (other == null || getClass() != other.getClass()) return false;
                    Getter getter = (Getter) other;
                    return accessedField.equals(getter.accessedField)
                            && assigner.equals(getter.assigner)
                            && methodAccessorFactory.equals(getter.methodAccessorFactory);
                }

                @Override
                public int hashCode() {
                    int result = accessedField.hashCode();
                    result = 31 * result + assigner.hashCode();
                    result = 31 * result + methodAccessorFactory.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "FieldProxy.Binder.AccessType.Getter{" +
                            "accessedField=" + accessedField +
                            ", assigner=" + assigner +
                            ", methodAccessorFactory=" + methodAccessorFactory +
                            '}';
                }

                /**
                 * A byte code appender for a getter method.
                 */
                protected class Appender implements ByteCodeAppender {

                    /**
                     * The generated accessor type.
                     */
                    private final TypeDescription typeDescription;

                    /**
                     * Creates a new appender for a setter method.
                     *
                     * @param implementationTarget The implementation target of the current instrumentation.
                     */
                    protected Appender(Target implementationTarget) {
                        typeDescription = implementationTarget.getTypeDescription();
                    }

                    @Override
                    public Size apply(MethodVisitor methodVisitor,
                                      Context implementationContext,
                                      MethodDescription instrumentedMethod) {
                        MethodDescription getterMethod = methodAccessorFactory.registerGetterFor(accessedField);
                        StackManipulation.Size stackSize = new StackManipulation.Compound(
                                accessedField.isStatic()
                                        ? StackManipulation.LegalTrivial.INSTANCE
                                        : new StackManipulation.Compound(
                                        MethodVariableAccess.REFERENCE.loadOffset(0),
                                        FieldAccess.forField(typeDescription.getDeclaredFields()
                                                .filter((named(AccessorProxy.FIELD_NAME))).getOnly()).getter()),
                                MethodInvocation.invoke(getterMethod),
                                assigner.assign(getterMethod.getReturnType(), instrumentedMethod.getReturnType(), Assigner.DYNAMICALLY_TYPED),
                                MethodReturn.returning(instrumentedMethod.getReturnType())
                        ).apply(methodVisitor, implementationContext);
                        return new Size(stackSize.getMaximalSize(), instrumentedMethod.getStackSize());
                    }

                    /**
                     * Returns the outer instance.
                     *
                     * @return The outer instance.
                     */
                    private Getter getOuter() {
                        return Getter.this;
                    }

                    @Override
                    public boolean equals(Object other) {
                        return this == other || !(other == null || getClass() != other.getClass())
                                && Getter.this.equals(((Appender) other).getOuter())
                                && typeDescription.equals(((Appender) other).typeDescription);
                    }

                    @Override
                    public int hashCode() {
                        return typeDescription.hashCode() + 31 * Getter.this.hashCode();
                    }

                    @Override
                    public String toString() {
                        return "FieldProxy.Binder.AccessType.Getter.Appender{" +
                                "getter=" + Getter.this +
                                "typeDescription=" + typeDescription +
                                '}';
                    }
                }
            }

            /**
             * Implementation for a setter method.
             */
            protected static class Setter implements Implementation {

                /**
                 * The field that is being accessed.
                 */
                private final FieldDescription accessedField;

                /**
                 * The assigner to use.
                 */
                private final Assigner assigner;

                /**
                 * The accessed type's method accessor factory.
                 */
                private final AuxiliaryType.MethodAccessorFactory methodAccessorFactory;

                /**
                 * Creates a new setter implementation.
                 *
                 * @param accessedField         The field that is being accessed.
                 * @param assigner              The assigner to use.
                 * @param methodAccessorFactory The accessed type's method accessor factory.
                 */
                protected Setter(FieldDescription accessedField,
                                 Assigner assigner,
                                 AuxiliaryType.MethodAccessorFactory methodAccessorFactory) {
                    this.accessedField = accessedField;
                    this.assigner = assigner;
                    this.methodAccessorFactory = methodAccessorFactory;
                }

                @Override
                public InstrumentedType prepare(InstrumentedType instrumentedType) {
                    return instrumentedType;
                }

                @Override
                public ByteCodeAppender appender(Target implementationTarget) {
                    return new Appender(implementationTarget);
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (other == null || getClass() != other.getClass()) return false;
                    Setter getter = (Setter) other;
                    return accessedField.equals(getter.accessedField)
                            && assigner.equals(getter.assigner)
                            && methodAccessorFactory.equals(getter.methodAccessorFactory);
                }

                @Override
                public int hashCode() {
                    int result = accessedField.hashCode();
                    result = 31 * result + assigner.hashCode();
                    result = 31 * result + methodAccessorFactory.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "FieldProxy.Binder.AccessType.Setter{" +
                            "accessedField=" + accessedField +
                            ", assigner=" + assigner +
                            ", methodAccessorFactory=" + methodAccessorFactory +
                            '}';
                }

                /**
                 * A byte code appender for a setter method.
                 */
                protected class Appender implements ByteCodeAppender {

                    /**
                     * The generated accessor type.
                     */
                    private final TypeDescription typeDescription;

                    /**
                     * Creates a new appender for a setter method.
                     *
                     * @param implementationTarget The implementation target of the current instrumentation.
                     */
                    protected Appender(Target implementationTarget) {
                        typeDescription = implementationTarget.getTypeDescription();
                    }

                    @Override
                    public Size apply(MethodVisitor methodVisitor,
                                      Context implementationContext,
                                      MethodDescription instrumentedMethod) {
                        TypeDescription parameterType = instrumentedMethod.getParameters().get(0).getType();
                        MethodDescription setterMethod = methodAccessorFactory.registerSetterFor(accessedField);
                        StackManipulation.Size stackSize = new StackManipulation.Compound(
                                accessedField.isStatic()
                                        ? StackManipulation.LegalTrivial.INSTANCE
                                        : new StackManipulation.Compound(
                                        MethodVariableAccess.REFERENCE.loadOffset(0),
                                        FieldAccess.forField(typeDescription.getDeclaredFields()
                                                .filter((named(AccessorProxy.FIELD_NAME))).getOnly()).getter()),
                                MethodVariableAccess.forType(parameterType).loadOffset(1),
                                assigner.assign(parameterType, setterMethod.getParameters().get(0).getType(), Assigner.DYNAMICALLY_TYPED),
                                MethodInvocation.invoke(setterMethod),
                                MethodReturn.VOID
                        ).apply(methodVisitor, implementationContext);
                        return new Size(stackSize.getMaximalSize(), instrumentedMethod.getStackSize());
                    }

                    /**
                     * Returns the outer instance.
                     *
                     * @return The outer instance.
                     */
                    private Setter getOuter() {
                        return Setter.this;
                    }

                    @Override
                    public boolean equals(Object other) {
                        return this == other || !(other == null || getClass() != other.getClass())
                                && Setter.this.equals(((Appender) other).getOuter())
                                && typeDescription.equals(((Appender) other).typeDescription);
                    }

                    @Override
                    public int hashCode() {
                        return typeDescription.hashCode() + 31 * Setter.this.hashCode();
                    }

                    @Override
                    public String toString() {
                        return "FieldProxy.Binder.AccessType.Setter.Appender{" +
                                "setter=" + Setter.this +
                                "typeDescription=" + typeDescription +
                                '}';
                    }
                }
            }
        }

        /**
         * Represents an implementation for implementing a proxy type constructor when a non-static field is accessed.
         */
        protected static class InstanceFieldConstructor implements Implementation {

            /**
             * The instrumented type from which a field is to be accessed.
             */
            private final TypeDescription instrumentedType;

            /**
             * Creates a new implementation for implementing a field accessor proxy's constructor when accessing
             * a non-static field.
             *
             * @param instrumentedType The instrumented type from which a field is to be accessed.
             */
            protected InstanceFieldConstructor(TypeDescription instrumentedType) {
                this.instrumentedType = instrumentedType;
            }

            @Override
            public InstrumentedType prepare(InstrumentedType instrumentedType) {
                return instrumentedType.withField(AccessorProxy.FIELD_NAME,
                        this.instrumentedType,
                        Opcodes.ACC_FINAL | Opcodes.ACC_PRIVATE);
            }

            @Override
            public ByteCodeAppender appender(Target implementationTarget) {
                return new Appender(implementationTarget);
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && instrumentedType.equals(((InstanceFieldConstructor) other).instrumentedType);
            }

            @Override
            public int hashCode() {
                return instrumentedType.hashCode();
            }

            @Override
            public String toString() {
                return "FieldProxy.Binder.InstanceFieldConstructor{" +
                        "instrumentedType=" + instrumentedType +
                        '}';
            }

            /**
             * An appender for implementing an
             * {@link FieldProxy.Binder.InstanceFieldConstructor}.
             */
            protected static class Appender implements ByteCodeAppender {

                /**
                 * The field to be set within the constructor.
                 */
                private final FieldDescription fieldDescription;

                /**
                 * Creates a new appender.
                 *
                 * @param implementationTarget The implementation target of the current implementation.
                 */
                protected Appender(Target implementationTarget) {
                    fieldDescription = implementationTarget.getTypeDescription()
                            .getDeclaredFields()
                            .filter((named(AccessorProxy.FIELD_NAME)))
                            .getOnly();
                }

                @Override
                public Size apply(MethodVisitor methodVisitor,
                                  Context implementationContext,
                                  MethodDescription instrumentedMethod) {
                    StackManipulation.Size stackSize = new StackManipulation.Compound(
                            MethodVariableAccess.REFERENCE.loadOffset(0),
                            MethodInvocation.invoke(StaticFieldConstructor.INSTANCE.objectTypeDefaultConstructor),
                            MethodVariableAccess.loadThisReferenceAndArguments(instrumentedMethod),
                            FieldAccess.forField(fieldDescription).putter(),
                            MethodReturn.VOID
                    ).apply(methodVisitor, implementationContext);
                    return new Size(stackSize.getMaximalSize(), instrumentedMethod.getStackSize());
                }

                @Override
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && fieldDescription.equals(((Appender) other).fieldDescription);
                }

                @Override
                public int hashCode() {
                    return fieldDescription.hashCode();
                }

                @Override
                public String toString() {
                    return "FieldProxy.Binder.InstanceFieldConstructor.Appender{" +
                            "fieldDescription=" + fieldDescription +
                            '}';
                }
            }
        }

        /**
         * A field locator is responsible for locating the type a field is defined in.
         */
        protected abstract static class FieldLocator {

            /**
             * Returns a field locator for a given field.
             *
             * @param fieldName         The field's name which might represent
             *                          {@link FieldProxy#BEAN_PROPERTY}
             *                          if the field's name should be derived from a method's name.
             * @param methodDescription The intercepted method.
             * @return An appropriate field locator.
             */
            protected static FieldLocator of(String fieldName, MethodDescription methodDescription) {
                return BEAN_PROPERTY.equals(fieldName)
                        ? Legal.consider(methodDescription)
                        : new Legal(fieldName);
            }

            /**
             * Locates a field of a given name on a specific type.
             *
             * @param typeDescription  The type which defines the field or a representation of {@code void} for
             *                         looking up a type implicitly within the type hierarchy.
             * @param instrumentedType The instrumented type from which a field is to be accessed.
             * @return A corresponding lookup engine.
             */
            protected abstract LookupEngine lookup(TypeDescription typeDescription, TypeDescription instrumentedType);

            /**
             * A resolution represents the result of a field location.
             */
            protected abstract static class Resolution {

                /**
                 * Determines if a field lookup was successful.
                 *
                 * @return {@code true} if a field lookup was successful.
                 */
                protected abstract boolean isValid();

                /**
                 * Returns a description of the located field. This method must only be called for valid
                 * resolutions.
                 *
                 * @return The located field.
                 */
                protected abstract FieldDescription getFieldDescription();

                /**
                 * A resolution for a non-located field.
                 */
                protected static class Unresolved extends Resolution {

                    @Override
                    protected boolean isValid() {
                        return false;
                    }

                    @Override
                    protected FieldDescription getFieldDescription() {
                        throw new IllegalStateException("Cannot resolve an unresolved field lookup");
                    }

                    @Override
                    public int hashCode() {
                        return 17;
                    }

                    @Override
                    public boolean equals(Object other) {
                        return other == this || (other != null && other.getClass() == getClass());
                    }

                    @Override
                    public String toString() {
                        return "FieldProxy.Binder.FieldLocator.Resolution.Unresolved{}";
                    }
                }

                /**
                 * A resolution for a successfully located field.
                 */
                protected static class Resolved extends Resolution {

                    /**
                     * The located field.
                     */
                    private final FieldDescription fieldDescription;

                    /**
                     * Creates a new successful resolution.
                     *
                     * @param fieldDescription The located field.
                     */
                    protected Resolved(FieldDescription fieldDescription) {
                        this.fieldDescription = fieldDescription;
                    }

                    @Override
                    protected boolean isValid() {
                        return true;
                    }

                    @Override
                    protected FieldDescription getFieldDescription() {
                        return fieldDescription;
                    }

                    @Override
                    public boolean equals(Object other) {
                        return this == other || !(other == null || getClass() != other.getClass())
                                && fieldDescription.equals(((Resolved) other).fieldDescription);
                    }

                    @Override
                    public int hashCode() {
                        return fieldDescription.hashCode();
                    }

                    @Override
                    public String toString() {
                        return "FieldProxy.Binder.FieldLocator.Resolution.Resolved{" +
                                "fieldDescription=" + fieldDescription +
                                '}';
                    }
                }
            }

            /**
             * A lookup engine is responsible for finding a specific field in a type hierarchy.
             */
            protected abstract static class LookupEngine {

                /**
                 * Locates a field if possible and returns a corresponding resolution.
                 *
                 * @param instrumentedType The instrumented type from which a field is to be accessed.
                 * @return A resolution of the field name lookup.
                 */
                protected abstract Resolution resolve(TypeDescription instrumentedType);

                /**
                 * Represents a lookup engine that can only produce illegal look-ups.
                 */
                protected static class Illegal extends LookupEngine {

                    @Override
                    protected Resolution resolve(TypeDescription instrumentedType) {
                        return new Resolution.Unresolved();
                    }

                    @Override
                    public int hashCode() {
                        return 17;
                    }

                    @Override
                    public boolean equals(Object other) {
                        return other == this || (other != null && other.getClass() == getClass());
                    }

                    @Override
                    public String toString() {
                        return "FieldProxy.Binder.FieldLocator.LookupEngine.Illegal{}";
                    }
                }

                /**
                 * Represents a lookup engine that tries to find the most specific field in a class hierarchy.
                 */
                protected static class ForHierarchy extends LookupEngine {

                    /**
                     * The name of the field to be found.
                     */
                    private final String fieldName;

                    /**
                     * Creates a new lookup engine that looks up a field name within the class hierarchy of the
                     * instrumented type.
                     *
                     * @param fieldName The name of the field to be found.
                     */
                    protected ForHierarchy(String fieldName) {
                        this.fieldName = fieldName;
                    }

                    @Override
                    protected Resolution resolve(TypeDescription instrumentedType) {
                        TypeDescription currentType = instrumentedType;
                        do {
                            FieldList fieldList = currentType.getDeclaredFields().filter(named(fieldName).and(isVisibleTo(instrumentedType)));
                            if (fieldList.size() == 1) {
                                return new Resolution.Resolved(fieldList.getOnly());
                            }
                        } while ((currentType = currentType.getSuperType()) != null);
                        return new Resolution.Unresolved();
                    }

                    @Override
                    public boolean equals(Object other) {
                        return this == other || !(other == null || getClass() != other.getClass())
                                && fieldName.equals(((ForHierarchy) other).fieldName);
                    }

                    @Override
                    public int hashCode() {
                        return fieldName.hashCode();
                    }

                    @Override
                    public String toString() {
                        return "FieldProxy.Binder.FieldLocator.LookupEngine.ForHierarchy{" +
                                "fieldName='" + fieldName + '\'' +
                                '}';
                    }
                }

                /**
                 * Represents a lookup engine that tries to find a field for a given type.
                 */
                protected static class ForExplicitType extends LookupEngine {

                    /**
                     * The name of the field.
                     */
                    private final String fieldName;

                    /**
                     * The type which is supposed to define a field with the given field name.
                     */
                    private final TypeDescription typeDescription;

                    /**
                     * Creates a new lookup engine for a given type.
                     *
                     * @param fieldName       The name of the field to be found.
                     * @param typeDescription The type which is supposed to define a field with the given field name.
                     */
                    protected ForExplicitType(String fieldName, TypeDescription typeDescription) {
                        this.fieldName = fieldName;
                        this.typeDescription = typeDescription;
                    }

                    @Override
                    protected Resolution resolve(TypeDescription instrumentedType) {
                        FieldList fieldList = typeDescription.getDeclaredFields().filter(named(fieldName).and(isVisibleTo(instrumentedType)));
                        return fieldList.size() == 1
                                ? new Resolution.Resolved(fieldList.getOnly())
                                : new Resolution.Unresolved();
                    }

                    @Override
                    public boolean equals(Object other) {
                        return this == other || !(other == null || getClass() != other.getClass())
                                && fieldName.equals(((ForExplicitType) other).fieldName)
                                && typeDescription.equals(((ForExplicitType) other).typeDescription);
                    }

                    @Override
                    public int hashCode() {
                        int result = fieldName.hashCode();
                        result = 31 * result + typeDescription.hashCode();
                        return result;
                    }

                    @Override
                    public String toString() {
                        return "FieldProxy.Binder.FieldLocator.LookupEngine.ForExplicitType{" +
                                "fieldName='" + fieldName + '\'' +
                                ", typeDescription=" + typeDescription +
                                '}';
                    }
                }
            }

            /**
             * Represents a field locator for a field whos name could be located.
             */
            protected static class Legal extends FieldLocator {

                /**
                 * The name of the field.
                 */
                private final String fieldName;

                /**
                 * Creates a new field locator for a legal field name.
                 *
                 * @param fieldName The name of the field.
                 */
                protected Legal(String fieldName) {
                    this.fieldName = fieldName;
                }

                /**
                 * Considers a given method to expose a field name by following the Java bean naming conventions
                 * for getter and setter methods.
                 *
                 * @param methodDescription The method to consider for such a field name identification.
                 * @return A correspoding field name locator.
                 */
                protected static FieldLocator consider(MethodDescription methodDescription) {
                    String fieldName;
                    if (isSetter().matches(methodDescription)) {
                        fieldName = methodDescription.getInternalName().substring(3);
                    } else if (isGetter().matches(methodDescription)) {
                        fieldName = methodDescription.getInternalName()
                                .substring(methodDescription.getInternalName().startsWith("is") ? 2 : 3);
                    } else {
                        return new Illegal();
                    }
                    return new Legal(Character.toLowerCase(fieldName.charAt(0)) + fieldName.substring(1));
                }

                @Override
                protected LookupEngine lookup(TypeDescription typeDescription, TypeDescription instrumentedType) {
                    return typeDescription.represents(void.class)
                            ? new LookupEngine.ForHierarchy(fieldName)
                            : new LookupEngine.ForExplicitType(fieldName, TargetType.resolve(typeDescription, instrumentedType, TargetType.MATCHER));
                }

                @Override
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && fieldName.equals(((Legal) other).fieldName);
                }

                @Override
                public int hashCode() {
                    return fieldName.hashCode();
                }

                @Override
                public String toString() {
                    return "FieldProxy.Binder.FieldLocator.Legal{" +
                            "fieldName='" + fieldName + '\'' +
                            '}';
                }
            }

            /**
             * Represents an illegal field locator which can impossible locate a field.
             */
            protected static class Illegal extends FieldLocator {

                @Override
                protected LookupEngine lookup(TypeDescription typeDescription, TypeDescription instrumentedType) {
                    return new LookupEngine.Illegal();
                }

                @Override
                public int hashCode() {
                    return 31;
                }

                @Override
                public boolean equals(Object other) {
                    return other == this || (other != null && other.getClass() == getClass());
                }

                @Override
                public String toString() {
                    return "FieldProxy.Binder.FieldLocator.Illegal{}";
                }
            }
        }

        /**
         * A proxy type for accessing a field either by a getter or a setter.
         */
        protected class AccessorProxy implements AuxiliaryType, StackManipulation {

            /**
             * The name of the field that stores the accessed instance if any.
             */
            protected static final String FIELD_NAME = "instance";

            /**
             * The field that is being accessed.
             */
            private final FieldDescription accessedField;

            /**
             * The type which is accessed.
             */
            private final TypeDescription instrumentedType;

            /**
             * The assigner to use.
             */
            private final Assigner assigner;

            /**
             * The access type to implement.
             */
            private final AccessType accessType;

            /**
             * {@code true} if the generated proxy should be serializable.
             */
            private final boolean serializableProxy;

            /**
             * @param accessedField     The field that is being accessed.
             * @param assigner          The assigner to use.
             * @param instrumentedType  The type which is accessed.
             * @param accessType        The assigner to use.
             * @param serializableProxy {@code true} if the generated proxy should be serializable.
             */
            protected AccessorProxy(FieldDescription accessedField,
                                    Assigner assigner,
                                    TypeDescription instrumentedType,
                                    AccessType accessType,
                                    boolean serializableProxy) {
                this.accessedField = accessedField;
                this.assigner = assigner;
                this.instrumentedType = instrumentedType;
                this.accessType = accessType;
                this.serializableProxy = serializableProxy;
            }

            @Override
            public DynamicType make(String auxiliaryTypeName,
                                    ClassFileVersion classFileVersion,
                                    MethodAccessorFactory methodAccessorFactory) {
                return new ByteBuddy(classFileVersion)
                        .subclass(accessType.proxyType(getterMethod, setterMethod), ConstructorStrategy.Default.NO_CONSTRUCTORS)
                        .name(auxiliaryTypeName)
                        .modifiers(DEFAULT_TYPE_MODIFIER)
                        .implement(serializableProxy ? new Class<?>[]{Serializable.class} : new Class<?>[0])
                        .defineConstructor(accessedField.isStatic()
                                ? Collections.<TypeDescription>emptyList()
                                : Collections.singletonList(instrumentedType))
                        .intercept(accessedField.isStatic()
                                ? StaticFieldConstructor.INSTANCE
                                : new InstanceFieldConstructor(instrumentedType))
                        .method(isDeclaredBy(accessType.proxyType(getterMethod, setterMethod)))
                        .intercept(accessType.access(accessedField, assigner, methodAccessorFactory))
                        .make();
            }

            @Override
            public boolean isValid() {
                return true;
            }

            @Override
            public Size apply(MethodVisitor methodVisitor, Implementation.Context implementationContext) {
                TypeDescription auxiliaryType = implementationContext.register(this);
                return new Compound(
                        TypeCreation.forType(auxiliaryType),
                        Duplication.SINGLE,
                        accessedField.isStatic()
                                ? LegalTrivial.INSTANCE
                                : MethodVariableAccess.REFERENCE.loadOffset(0),
                        MethodInvocation.invoke(auxiliaryType.getDeclaredMethods().filter(isConstructor()).getOnly())
                ).apply(methodVisitor, implementationContext);
            }

            /**
             * Returns the outer instance.
             *
             * @return The outer instance.
             */
            private Binder getOuter() {
                return Binder.this;
            }

            @Override
            public boolean equals(Object other) {
                if (this == other) return true;
                if (other == null || getClass() != other.getClass()) return false;
                AccessorProxy that = (AccessorProxy) other;
                return serializableProxy == that.serializableProxy
                        && accessType == that.accessType
                        && accessedField.equals(that.accessedField)
                        && assigner.equals(that.assigner)
                        && Binder.this.equals(that.getOuter())
                        && instrumentedType.equals(that.instrumentedType);
            }

            @Override
            public int hashCode() {
                int result = accessedField.hashCode();
                result = 31 * result + instrumentedType.hashCode();
                result = 31 * result + assigner.hashCode();
                result = 31 * result + Binder.this.hashCode();
                result = 31 * result + accessType.hashCode();
                result = 31 * result + (serializableProxy ? 1 : 0);
                return result;
            }

            @Override
            public String toString() {
                return "FieldProxy.Binder.AccessorProxy{" +
                        "accessedField=" + accessedField +
                        ", instrumentedType=" + instrumentedType +
                        ", assigner=" + assigner +
                        ", accessType=" + accessType +
                        ", serializableProxy=" + serializableProxy +
                        ", binder=" + Binder.this +
                        '}';
            }
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/implementation/bind/annotation/Super.java
package net.bytebuddy.implementation.bind.annotation;

import net.bytebuddy.description.annotation.AnnotationDescription;
import net.bytebuddy.description.enumeration.EnumerationDescription;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.method.MethodList;
import net.bytebuddy.description.method.ParameterDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.dynamic.TargetType;
import net.bytebuddy.implementation.Implementation;
import net.bytebuddy.implementation.auxiliary.TypeProxy;
import net.bytebuddy.implementation.bind.MethodDelegationBinder;
import net.bytebuddy.implementation.bytecode.StackManipulation;
import net.bytebuddy.implementation.bytecode.assign.Assigner;

import java.lang.annotation.*;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import static net.bytebuddy.matcher.ElementMatchers.is;
import static net.bytebuddy.matcher.ElementMatchers.named;
import static net.bytebuddy.matcher.ElementMatchers.returns;

/**
 * Parameters that are annotated with this annotation are assigned an instance of an auxiliary proxy type that allows calling
 * any {@code super} methods of the instrumented type where the parameter type must be a super type of the instrumented type.
 * The proxy type will be a direct subclass of the parameter's type such as for example a specific interface.
 * <p>&nbsp;</p>
 * Obviously, the proxy type must be instantiated before it is assigned to the intercepting method's parameter. For this
 * purpose, two strategies are available which can be specified by setting the {@link Super#strategy()} parameter which can
 * be assigned:
 * <ol>
 * <li>{@link net.bytebuddy.implementation.bind.annotation.Super.Instantiation#CONSTRUCTOR}:
 * A constructor call is made where {@link Super#constructorParameters()} determines the constructor's signature. Any constructor
 * parameter is assigned the parameter's default value when the constructor is called. Calling the default constructor is the
 * preconfigured strategy.</li>
 * <li>{@link net.bytebuddy.implementation.bind.annotation.Super.Instantiation#UNSAFE}:
 * The proxy is created by making use of Java's {@link sun.reflect.ReflectionFactory} which is however not a public API which
 * is why it should be used with care. No constructor is called when this strategy is used. If this option is set, the
 * {@link Super#constructorParameters()} parameter is ignored.</li>
 * </ol>
 * Note that when for example intercepting a type {@code Foo} that implements some interface {@code Bar}, the proxy type
 * will only implement {@code Bar} and therefore extend {@link java.lang.Object} what allows for calling the default
 * constructor on the proxy. This implies that an interception by some method {@code qux(@Super Baz baz, @Super Bar bar)}
 * would cause the creation of two super call proxies, one extending {@code Baz}, the other extending {@code Bar}, give
 * that both types are super types of {@code Foo}.
 * <p>&nbsp;</p>
 * As an exception, no method calls to {@link Object#finalize()} are delegated by calling this method on the {@code super}-call
 * proxy by default. If this is absolutely necessary, this can however be enabled by setting {@link Super#ignoreFinalizer()}
 * to {@code false}.
 * <p>&nbsp;</p>
 * If a method parameter is not a super type of the instrumented type, the method with the parameter that is annoted by
 * #{@code Super} is not considered a possible delegation target.
 */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.PARAMETER)
public @interface Super {

    /**
     * Determines how the {@code super}call proxy type is instantiated.
     *
     * @return The instantiation strategy for this proxy.
     */
    Instantiation strategy() default Instantiation.CONSTRUCTOR;

    /**
     * If {@code true}, the proxy type will not implement {@code super} calls to {@link Object#finalize()} or any overridden methods.
     *
     * @return {@code false} if finalizer methods should be considered for {@code super}-call proxy type delegation.
     */
    boolean ignoreFinalizer() default true;

    /**
     * Determines if the generated proxy should be {@link java.io.Serializable}. If the annotated type
     * already is serializable, such an explicit specification is not required.
     *
     * @return {@code true} if the generated proxy should be {@link java.io.Serializable}.
     */
    boolean serializableProxy() default false;

    /**
     * Defines the parameter types of the constructor to be called for the created {@code super}-call proxy type.
     *
     * @return The parameter types of the constructor to be called.
     */
    Class<?>[] constructorParameters() default {};

    /**
     * Determines the instantiation of the proxy type.
     *
     * @see net.bytebuddy.implementation.bind.annotation.Super
     */
    enum Instantiation {

        /**
         * A proxy instance is instantiated by its constructor. For the constructor's arguments, the parameters default
         * values are used. The constructor can be identified by setting {@link Super#constructorParameters()}.
         */
        CONSTRUCTOR {
            @Override
            protected StackManipulation proxyFor(TypeDescription parameterType,
                                                 Implementation.Target implementationTarget,
                                                 AnnotationDescription.Loadable<Super> annotation) {
                TypeDescription[] constructorParameters = annotation.getValue(CONSTRUCTOR_PARAMETERS, TypeDescription[].class);
                List<TypeDescription> typeDescriptions = TargetType.resolve(Arrays.asList(constructorParameters),
                        implementationTarget.getTypeDescription(),
                        TargetType.MATCHER).asRawTypes();
                return new TypeProxy.ForSuperMethodByConstructor(parameterType,
                        implementationTarget,
                        typeDescriptions,
                        annotation.getValue(IGNORE_FINALIZER, Boolean.class),
                        annotation.getValue(SERIALIZABLE_PROXY, Boolean.class));
            }
        },

        /**
         * A proxy is instantiated by calling JVM internal methods and without calling a constructor. This strategy
         * might fail on exotic JVM implementations.
         */
        UNSAFE {
            @Override
            protected StackManipulation proxyFor(TypeDescription parameterType,
                                                 Implementation.Target implementationTarget,
                                                 AnnotationDescription.Loadable<Super> annotation) {
                return new TypeProxy.ForSuperMethodByReflectionFactory(parameterType,
                        implementationTarget,
                        annotation.getValue(IGNORE_FINALIZER, Boolean.class),
                        annotation.getValue(SERIALIZABLE_PROXY, Boolean.class));
            }
        };

        /**
         * A reference to the ignore finalizer method.
         */
        private static final MethodDescription IGNORE_FINALIZER;

        /**
         * A reference to the serializable proxy method.
         */
        private static final MethodDescription SERIALIZABLE_PROXY;

        /**
         * A reference to the constructor parameters method.
         */
        private static final MethodDescription CONSTRUCTOR_PARAMETERS;

        /*
         * Extracts method references to the annotation methods.
         */
        static {
            MethodList annotationProperties = new TypeDescription.ForLoadedType(Super.class).getDeclaredMethods();
            IGNORE_FINALIZER = annotationProperties.filter(named("ignoreFinalizer")).getOnly();
            SERIALIZABLE_PROXY = annotationProperties.filter(named("serializableProxy")).getOnly();
            CONSTRUCTOR_PARAMETERS = annotationProperties.filter(named("constructorParameters")).getOnly();
        }

        /**
         * Creates a stack manipulation which loads a {@code super}-call proxy onto the stack.
         *
         * @param parameterType        The type of the parameter that was annotated with
         *                             {@link net.bytebuddy.implementation.bind.annotation.Super}
         * @param implementationTarget The implementation target for the currently created type.
         * @param annotation           The annotation that caused this method call.
         * @return A stack manipulation representing this instance's instantiation strategy.
         */
        protected abstract StackManipulation proxyFor(TypeDescription parameterType,
                                                      Implementation.Target implementationTarget,
                                                      AnnotationDescription.Loadable<Super> annotation);

        @Override
        public String toString() {
            return "Super.Instantiation." + name();
        }
    }

    /**
     * A binder for handling the
     * {@link net.bytebuddy.implementation.bind.annotation.Super}
     * annotation.
     *
     * @see TargetMethodAnnotationDrivenBinder
     */
    enum Binder implements TargetMethodAnnotationDrivenBinder.ParameterBinder<Super> {

        /**
         * The singleton instance.
         */
        INSTANCE;

        /**
         * A method reference to the strategy property.
         */
        private static final MethodDescription STRATEGY;

        /*
         * Extracts method references of the super annotation.
         */
        static {
            MethodList annotationProperties = new TypeDescription.ForLoadedType(Super.class).getDeclaredMethods();
            STRATEGY = annotationProperties.filter(returns(Instantiation.class)).getOnly();
        }

        @Override
        public Class<Super> getHandledType() {
            return Super.class;
        }

        @Override
        public MethodDelegationBinder.ParameterBinding<?> bind(AnnotationDescription.Loadable<Super> annotation,
                                                               MethodDescription source,
                                                               ParameterDescription target,
                                                               Implementation.Target implementationTarget,
                                                               Assigner assigner) {
            if (source.isStatic() || !implementationTarget.getTypeDescription().isAssignableTo(target.getType())) {
                return MethodDelegationBinder.ParameterBinding.Illegal.INSTANCE;
            } else {
                return new MethodDelegationBinder.ParameterBinding.Anonymous(annotation
                        .getValue(STRATEGY, EnumerationDescription.class).load(Instantiation.class)
                        .proxyFor(target.getType(), implementationTarget, annotation));
            }
        }

        @Override
        public String toString() {
            return "Super.Binder." + name();
        }
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/matcher/ElementMatchers.java
package net.bytebuddy.matcher;

import net.bytebuddy.description.ByteCodeElement;
import net.bytebuddy.description.ModifierReviewable;
import net.bytebuddy.description.NamedElement;
import net.bytebuddy.description.annotation.AnnotatedCodeElement;
import net.bytebuddy.description.annotation.AnnotationDescription;
import net.bytebuddy.description.annotation.AnnotationList;
import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.method.MethodList;
import net.bytebuddy.description.method.ParameterDescription;
import net.bytebuddy.description.method.ParameterList;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.TypeList;
import net.bytebuddy.description.type.generic.GenericTypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeList;

import java.lang.annotation.Annotation;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Type;
import java.util.*;

import static net.bytebuddy.utility.ByteBuddyCommons.nonNull;


/**
 * A utility class that contains a human-readable language for creating {@link net.bytebuddy.matcher.ElementMatcher}s.
 */
public final class ElementMatchers {

    /**
     * A readable reference to the bootstrap class loader which is represented by {@code null}.
     */
    private static final ClassLoader BOOTSTRAP_CLASSLOADER = null;

    /**
     * A private constructor that must not be invoked.
     */
    private ElementMatchers() {
        throw new UnsupportedOperationException();
    }

    /**
     * Matches the given value which can also be {@code null} by the {@link java.lang.Object#equals(Object)} method or
     * by a null-check.
     *
     * @param value The value that is to be matched.
     * @param <T>   The type of the matched object.
     * @return A matcher that matches an exact value.
     */
    public static <T> ElementMatcher.Junction<T> is(Object value) {
        return value == null
                ? new NullMatcher<T>()
                : new EqualityMatcher<T>(value);
    }

    /**
     * Exactly matches a given field as a {@link FieldDescription}.
     *
     * @param field The field to match by its description
     * @param <T>   The type of the matched object.
     * @return An element matcher that exactly matches the given field.
     */
    public static <T extends FieldDescription> ElementMatcher.Junction<T> is(Field field) {
        return is(new FieldDescription.ForLoadedField(nonNull(field)));
    }

    /**
     * Exactly matches a given {@link FieldDescription}.
     *
     * @param fieldDescription The field description to match.
     * @param <T>              The type of the matched object.
     * @return An element matcher that matches the given field description.
     */
    public static <T extends FieldDescription> ElementMatcher.Junction<T> is(FieldDescription fieldDescription) {
        return new EqualityMatcher<T>(nonNull(fieldDescription));
    }

    /**
     * Exactly matches a given method as a {@link MethodDescription}.
     *
     * @param method The method to match by its description
     * @param <T>    The type of the matched object.
     * @return An element matcher that exactly matches the given method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> is(Method method) {
        return is(new MethodDescription.ForLoadedMethod(nonNull(method)));
    }

    /**
     * Exactly matches a given constructor as a {@link MethodDescription}.
     *
     * @param constructor The constructor to match by its description
     * @param <T>         The type of the matched object.
     * @return An element matcher that exactly matches the given constructor.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> is(Constructor<?> constructor) {
        return is(new MethodDescription.ForLoadedConstructor(nonNull(constructor)));
    }

    /**
     * Exactly matches a given {@link MethodDescription}.
     *
     * @param methodDescription The method description to match.
     * @param <T>               The type of the matched object.
     * @return An element matcher that matches the given method description.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> is(MethodDescription methodDescription) {
        return new EqualityMatcher<T>(nonNull(methodDescription));
    }

    /**
     * Exactly matches a given type as a {@link TypeDescription}.
     *
     * @param type The type to match by its description
     * @param <T>  The type of the matched object.
     * @return An element matcher that exactly matches the given type.
     */
    public static <T extends GenericTypeDescription> ElementMatcher.Junction<T> is(Type type) {
        return is(GenericTypeDescription.Sort.describe(nonNull(type)));
    }

    /**
     * Exactly matches a given {@link TypeDescription}.
     *
     * @param typeDescription The type to match by its description
     * @param <T>             The type of the matched object.
     * @return An element matcher that exactly matches the given type.
     */
    public static <T extends GenericTypeDescription> ElementMatcher.Junction<T> is(GenericTypeDescription typeDescription) {
        return new EqualityMatcher<T>(nonNull(typeDescription));
    }

    /**
     * Exactly matches a given annotation as an {@link AnnotationDescription}.
     *
     * @param annotation The annotation to match by its description.
     * @param <T>        The type of the matched object.
     * @return An element matcher that exactly matches the given annotation.
     */
    public static <T extends AnnotationDescription> ElementMatcher.Junction<T> is(Annotation annotation) {
        return is(AnnotationDescription.ForLoadedAnnotation.of(nonNull(annotation)));
    }

    /**
     * Exactly matches a given {@link AnnotationDescription}.
     *
     * @param annotationDescription The annotation description to match.
     * @param <T>                   The type of the matched object.
     * @return An element matcher that exactly matches the given annotation.
     */
    public static <T extends AnnotationDescription> ElementMatcher.Junction<T> is(AnnotationDescription annotationDescription) {
        return new EqualityMatcher<T>(nonNull(annotationDescription));
    }

    /**
     * Inverts another matcher.
     *
     * @param matcher The matcher to invert.
     * @param <T>     The type of the matched object.
     * @return An inverted version of the given {@code matcher}.
     */
    public static <T> ElementMatcher.Junction<T> not(ElementMatcher<? super T> matcher) {
        return new NegatingMatcher<T>(nonNull(matcher));
    }

    /**
     * Creates a matcher that always returns {@code true}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that matches anything.
     */
    public static <T> ElementMatcher.Junction<T> any() {
        return new BooleanMatcher<T>(true);
    }

    /**
     * Creates a matcher that always returns {@code false}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that matches nothing.
     */
    public static <T> ElementMatcher.Junction<T> none() {
        return new BooleanMatcher<T>(false);
    }

    /**
     * Creates a matcher that matches any of the given objects by the {@link java.lang.Object#equals(Object)} method.
     * None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with any of the given objects.
     */
    public static <T> ElementMatcher.Junction<T> anyOf(Object... value) {
        return anyOf(Arrays.asList(nonNull(value)));
    }

    /**
     * Creates a matcher that matches any of the given objects by the {@link java.lang.Object#equals(Object)} method.
     * None of the values must be {@code null}.
     *
     * @param values The input values to be compared against.
     * @param <T>    The type of the matched object.
     * @return A matcher that checks for the equality with any of the given objects.
     */
    public static <T> ElementMatcher.Junction<T> anyOf(Iterable<?> values) {
        ElementMatcher.Junction<T> matcher = none();
        for (Object value : values) {
            matcher = matcher.or(is(value));
        }
        return matcher;
    }

    /**
     * Creates a matcher that matches any of the given types as {@link TypeDescription}s
     * by the {@link java.lang.Object#equals(Object)} method. None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with any of the given objects.
     */
    public static <T extends GenericTypeDescription> ElementMatcher.Junction<T> anyOf(Type... value) {
        return anyOf(new GenericTypeList.ForLoadedType(nonNull(value)));
    }

    /**
     * Creates a matcher that matches any of the given constructors as {@link MethodDescription}s
     * by the {@link java.lang.Object#equals(Object)} method. None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with any of the given objects.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> anyOf(Constructor<?>... value) {
        return anyOf(new MethodList.ForLoadedType(nonNull(value), new Method[0]));
    }

    /**
     * Creates a matcher that matches any of the given methods as {@link MethodDescription}s
     * by the {@link java.lang.Object#equals(Object)} method. None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with any of the given objects.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> anyOf(Method... value) {
        return anyOf(new MethodList.ForLoadedType(new Constructor<?>[0], nonNull(value)));
    }

    /**
     * Creates a matcher that matches any of the given annotations as {@link AnnotationDescription}s
     * by the {@link java.lang.Object#equals(Object)} method. None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with any of the given objects.
     */
    public static <T extends AnnotationDescription> ElementMatcher.Junction<T> anyOf(Annotation... value) {
        return anyOf(new AnnotationList.ForLoadedAnnotation(nonNull(value)));
    }

    /**
     * Creates a matcher that matches none of the given objects by the {@link java.lang.Object#equals(Object)} method.
     * None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with none of the given objects.
     */
    public static <T> ElementMatcher.Junction<T> noneOf(Object... value) {
        return noneOf(Arrays.asList(value));
    }

    /**
     * Creates a matcher that matches none of the given objects by the {@link java.lang.Object#equals(Object)} method.
     * None of the values must be {@code null}.
     *
     * @param values The input values to be compared against.
     * @param <T>    The type of the matched object.
     * @return A matcher that checks for the equality with none of the given objects.
     */
    public static <T> ElementMatcher.Junction<T> noneOf(Iterable<?> values) {
        ElementMatcher.Junction<T> matcher = any();
        for (Object value : values) {
            matcher = matcher.and(not(is(value)));
        }
        return matcher;
    }

    /**
     * Creates a matcher that matches none of the given types as {@link TypeDescription}s
     * by the {@link java.lang.Object#equals(Object)} method. None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with none of the given objects.
     */
    public static <T extends GenericTypeDescription> ElementMatcher.Junction<T> noneOf(Type... value) {
        return noneOf(new GenericTypeList.ForLoadedType(nonNull(value)));
    }

    /**
     * Creates a matcher that matches none of the given constructors as {@link MethodDescription}s
     * by the {@link java.lang.Object#equals(Object)} method. None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with none of the given objects.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> noneOf(Constructor<?>... value) {
        return noneOf(new MethodList.ForLoadedType(nonNull(value), new Method[0]));
    }

    /**
     * Creates a matcher that matches none of the given methods as {@link MethodDescription}s
     * by the {@link java.lang.Object#equals(Object)} method. None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with none of the given objects.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> noneOf(Method... value) {
        return noneOf(new MethodList.ForLoadedType(new Constructor<?>[0], nonNull(value)));
    }

    /**
     * Creates a matcher that matches none of the given annotations as {@link AnnotationDescription}s
     * by the {@link java.lang.Object#equals(Object)} method. None of the values must be {@code null}.
     *
     * @param value The input values to be compared against.
     * @param <T>   The type of the matched object.
     * @return A matcher that checks for the equality with any of the given objects.
     */
    public static <T extends AnnotationDescription> ElementMatcher.Junction<T> noneOf(Annotation... value) {
        return noneOf(new AnnotationList.ForLoadedAnnotation(nonNull(value)));
    }

    /**
     * Converts a matcher for a type description into a matcher for a raw type of the matched generic type against the given matcher. A wildcard
     * type which does not define a raw type results in a negative match.
     *
     * @param matcher The matcher to match the matched object's raw type against.
     * @param <T>     The type of the matched object.
     * @return A type matcher for a generic type that matches the matched type's raw type against the given type description matcher.
     */
    public static <T extends GenericTypeDescription> ElementMatcher.Junction<T> rawType(ElementMatcher<? super TypeDescription> matcher) {
        return new RawTypeMatcher<T>(matcher);
    }

    /**
     * Matches a {@link NamedElement} for its exact name.
     *
     * @param name The expected name.
     * @param <T>  The type of the matched object.
     * @return An element matcher for a named element's exact name.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> named(String name) {
        return new NameMatcher<T>(new StringMatcher(nonNull(name), StringMatcher.Mode.EQUALS_FULLY));
    }

    /**
     * Matches a {@link NamedElement} for its name. The name's
     * capitalization is ignored.
     *
     * @param name The expected name.
     * @param <T>  The type of the matched object.
     * @return An element matcher for a named element's name.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> namedIgnoreCase(String name) {
        return new NameMatcher<T>(new StringMatcher(nonNull(name), StringMatcher.Mode.EQUALS_FULLY_IGNORE_CASE));
    }

    /**
     * Matches a {@link NamedElement} for its name's prefix.
     *
     * @param prefix The expected name's prefix.
     * @param <T>    The type of the matched object.
     * @return An element matcher for a named element's name's prefix.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> nameStartsWith(String prefix) {
        return new NameMatcher<T>(new StringMatcher(nonNull(prefix), StringMatcher.Mode.STARTS_WITH));
    }

    /**
     * Matches a {@link NamedElement} for its name's prefix. The name's
     * capitalization is ignored.
     *
     * @param prefix The expected name's prefix.
     * @param <T>    The type of the matched object.
     * @return An element matcher for a named element's name's prefix.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> nameStartsWithIgnoreCase(String prefix) {
        return new NameMatcher<T>(new StringMatcher(nonNull(prefix), StringMatcher.Mode.STARTS_WITH_IGNORE_CASE));
    }

    /**
     * Matches a {@link NamedElement} for its name's suffix.
     *
     * @param suffix The expected name's suffix.
     * @param <T>    The type of the matched object.
     * @return An element matcher for a named element's name's suffix.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> nameEndsWith(String suffix) {
        return new NameMatcher<T>(new StringMatcher(nonNull(suffix), StringMatcher.Mode.ENDS_WITH));
    }

    /**
     * Matches a {@link NamedElement} for its name's suffix. The name's
     * capitalization is ignored.
     *
     * @param suffix The expected name's suffix.
     * @param <T>    The type of the matched object.
     * @return An element matcher for a named element's name's suffix.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> nameEndsWithIgnoreCase(String suffix) {
        return new NameMatcher<T>(new StringMatcher(nonNull(suffix), StringMatcher.Mode.ENDS_WITH_IGNORE_CASE));
    }

    /**
     * Matches a {@link NamedElement} for an infix of its name.
     *
     * @param infix The expected infix of the name.
     * @param <T>   The type of the matched object.
     * @return An element matcher for a named element's name's infix.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> nameContains(String infix) {
        return new NameMatcher<T>(new StringMatcher(nonNull(infix), StringMatcher.Mode.CONTAINS));
    }

    /**
     * Matches a {@link NamedElement} for an infix of its name. The name's
     * capitalization is ignored.
     *
     * @param infix The expected infix of the name.
     * @param <T>   The type of the matched object.
     * @return An element matcher for a named element's name's infix.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> nameContainsIgnoreCase(String infix) {
        return new NameMatcher<T>(new StringMatcher(nonNull(infix), StringMatcher.Mode.CONTAINS_IGNORE_CASE));
    }

    /**
     * Matches a {@link NamedElement} name against a regular expression.
     *
     * @param regex The regular expression to match the name against.
     * @param <T>   The type of the matched object.
     * @return An element matcher for a named element's name's against the given regular expression.
     */
    public static <T extends NamedElement> ElementMatcher.Junction<T> nameMatches(String regex) {
        return new NameMatcher<T>(new StringMatcher(nonNull(regex), StringMatcher.Mode.MATCHES));
    }

    /**
     * Matches a {@link ByteCodeElement}'s descriptor against a given value.
     *
     * @param descriptor The expected descriptor.
     * @param <T>        The type of the matched object.
     * @return A matcher for the given {@code descriptor}.
     */
    public static <T extends ByteCodeElement> ElementMatcher.Junction<T> hasDescriptor(String descriptor) {
        return new DescriptorMatcher<T>(new StringMatcher(nonNull(descriptor), StringMatcher.Mode.EQUALS_FULLY));
    }

    /**
     * Matches a {@link ByteCodeElement} for being declared by a given
     * {@link TypeDescription}.
     *
     * @param type The type that is expected to declare the matched byte code element.
     * @param <T>  The type of the matched object.
     * @return A matcher for byte code elements being declared by the given {@code type}.
     */
    public static <T extends ByteCodeElement> ElementMatcher.Junction<T> isDeclaredBy(TypeDescription type) {
        return isDeclaredBy(is(nonNull(type)));
    }

    /**
     * Matches a {@link ByteCodeElement} for being declared by a given
     * {@link java.lang.Class}.
     *
     * @param type The type that is expected to declare the matched byte code element.
     * @param <T>  The type of the matched object.
     * @return A matcher for byte code elements being declared by the given {@code type}.
     */
    public static <T extends ByteCodeElement> ElementMatcher.Junction<T> isDeclaredBy(Class<?> type) {
        return isDeclaredBy(new TypeDescription.ForLoadedType(nonNull(type)));
    }

    /**
     * Matches a {@link ByteCodeElement} for being declared by a
     * {@link TypeDescription} that is matched by the given matcher.
     *
     * @param matcher A matcher for the declaring type of the matched byte code element as long as it
     *                is not {@code null}.
     * @param <T>     The type of the matched object.
     * @return A matcher for byte code elements being declared by a type matched by the given {@code matcher}.
     */
    public static <T extends ByteCodeElement> ElementMatcher.Junction<T> isDeclaredBy(ElementMatcher<? super TypeDescription> matcher) {
        return new DeclaringTypeMatcher<T>(nonNull(matcher));
    }

    /**
     * Matches a {@link ByteCodeElement} that is visible to a given {@link java.lang.Class}.
     *
     * @param type The type that a matched byte code element is expected to be visible to.
     * @param <T>  The type of the matched object.
     * @return A matcher for a byte code element to be visible to a given {@code type}.
     */
    public static <T extends ByteCodeElement> ElementMatcher.Junction<T> isVisibleTo(Class<?> type) {
        return isVisibleTo(new TypeDescription.ForLoadedType(nonNull(type)));
    }

    /**
     * Matches a {@link ByteCodeElement} that is visible to a given
     * {@link TypeDescription}.
     *
     * @param typeDescription The type that a matched byte code element is expected to be visible to.
     * @param <T>             The type of the matched object.
     * @return A matcher for a byte code element to be visible to a given {@code typeDescription}.
     */
    public static <T extends ByteCodeElement> ElementMatcher.Junction<T> isVisibleTo(TypeDescription typeDescription) {
        return new VisibilityMatcher<T>(nonNull(typeDescription));
    }

    /**
     * Matches an {@link net.bytebuddy.description.annotation.AnnotatedCodeElement} for declared annotations.
     * This matcher does not match inherited annotations which only exist for classes. Use
     * {@link net.bytebuddy.matcher.ElementMatchers#inheritsAnnotation(Class)} for matching inherited annotations.
     *
     * @param type The annotation type to match against.
     * @param <T>  The type of the matched object.
     * @return A matcher that validates that an annotated element is annotated with an annotation of {@code type}.
     */
    public static <T extends AnnotatedCodeElement> ElementMatcher.Junction<T> isAnnotatedWith(Class<? extends Annotation> type) {
        return isAnnotatedWith(new TypeDescription.ForLoadedType(nonNull(type)));
    }

    /**
     * Matches an {@link net.bytebuddy.description.annotation.AnnotatedCodeElement} for declared annotations.
     * This matcher does not match inherited annotations which only exist for classes. Use
     * {@link net.bytebuddy.matcher.ElementMatchers#inheritsAnnotation(TypeDescription)}
     * for matching inherited annotations.
     *
     * @param typeDescription The annotation type to match against.
     * @param <T>             The type of the matched object.
     * @return A matcher that validates that an annotated element is annotated with an annotation of {@code typeDescription}.
     */
    public static <T extends AnnotatedCodeElement> ElementMatcher.Junction<T> isAnnotatedWith(TypeDescription typeDescription) {
        return isAnnotatedWith(is(typeDescription));
    }

    /**
     * Matches an {@link net.bytebuddy.description.annotation.AnnotatedCodeElement} for declared annotations.
     * This matcher does not match inherited annotations which only exist for classes. Use
     * {@link net.bytebuddy.matcher.ElementMatchers#inheritsAnnotation(net.bytebuddy.matcher.ElementMatcher)}
     * for matching inherited annotations.
     *
     * @param matcher The matcher to apply to any annotation's type found on the matched annotated element.
     * @param <T>     The type of the matched object.
     * @return A matcher that validates that an annotated element is annotated with an annotation of a type
     * that matches the given {@code matcher}.
     */
    public static <T extends AnnotatedCodeElement> ElementMatcher.Junction<T> isAnnotatedWith(ElementMatcher<? super TypeDescription> matcher) {
        return declaresAnnotation(new AnnotationTypeMatcher<AnnotationDescription>(nonNull(matcher)));
    }

    /**
     * Matches an {@link net.bytebuddy.description.annotation.AnnotatedCodeElement} to declare any annotation
     * that matches the given matcher. Note that this matcher does not match inherited annotations that only exist
     * for types. Use {@link net.bytebuddy.matcher.ElementMatchers#inheritsAnnotation(net.bytebuddy.matcher.ElementMatcher)}
     * for matching inherited annotations.
     *
     * @param matcher A matcher to apply on any declared annotation of the matched annotated element.
     * @param <T>     The type of the matched object.
     * @return A matcher that validates that an annotated element is annotated with an annotation that matches
     * the given {@code matcher}.
     */
    public static <T extends AnnotatedCodeElement> ElementMatcher.Junction<T> declaresAnnotation(ElementMatcher<? super AnnotationDescription> matcher) {
        return new DeclaringAnnotationMatcher<T>(new CollectionItemMatcher<AnnotationDescription>(nonNull(matcher)));
    }

    /**
     * Matches a {@link ModifierReviewable} that is {@code public}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a {@code public} modifier reviewable.
     */
    public static <T extends ModifierReviewable> ElementMatcher.Junction<T> isPublic() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.PUBLIC);
    }

    /**
     * Matches a {@link ModifierReviewable} that is {@code protected}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a {@code protected} modifier reviewable.
     */
    public static <T extends ModifierReviewable> ElementMatcher.Junction<T> isProtected() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.PROTECTED);
    }

    /**
     * Matches a {@link ModifierReviewable} that is package-private.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a package-private modifier reviewable.
     */
    public static <T extends ModifierReviewable> ElementMatcher.Junction<T> isPackagePrivate() {
        return not(isPublic().or(isProtected()).or(isPrivate()));
    }

    /**
     * Matches a {@link ModifierReviewable} that is {@code private}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a {@code private} modifier reviewable.
     */
    public static <T extends ModifierReviewable> ElementMatcher.Junction<T> isPrivate() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.PRIVATE);
    }

    /**
     * Matches a {@link ModifierReviewable} that is {@code final}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a {@code final} modifier reviewable.
     */
    public static <T extends ModifierReviewable> ElementMatcher.Junction<T> isFinal() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.FINAL);
    }

    /**
     * Matches a {@link ModifierReviewable} that is {@code static}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a {@code static} modifier reviewable.
     */
    public static <T extends ModifierReviewable> ElementMatcher.Junction<T> isStatic() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.STATIC);
    }

    /**
     * Matches a {@link ModifierReviewable} that is synthetic.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a synthetic modifier reviewable.
     */
    public static <T extends ModifierReviewable> ElementMatcher.Junction<T> isSynthetic() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.SYNTHETIC);
    }

    /**
     * Matches a {@link MethodDescription} that is {@code synchronized}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a {@code synchronized} method description.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isSynchronized() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.SYNCHRONIZED);
    }

    /**
     * Matches a {@link MethodDescription} that is {@code native}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a {@code native} method description.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isNative() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.NATIVE);
    }

    /**
     * Matches a {@link MethodDescription} that is {@code strictfp}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a {@code strictfp} method description.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isStrict() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.STRICT);
    }

    /**
     * Matches a {@link MethodDescription} that is a var-args.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a var-args method description.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isVarArgs() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.VAR_ARGS);
    }

    /**
     * Matches a {@link MethodDescription} that is a bridge.
     *
     * @param <T> The type of the matched object.
     * @return A matcher for a bridge method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isBridge() {
        return new ModifierMatcher<T>(ModifierMatcher.Mode.BRIDGE);
    }

    /**
     * Matches {@link MethodDescription}s that returns a given
     * {@link java.lang.Class}.
     *
     * @param type The type the matched method is expected to return.
     * @param <T>  The type of the matched object.
     * @return An element matcher that matches a given return type for a method description.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> returns(Type type) {
        return returns(GenericTypeDescription.Sort.describe(nonNull(type)));
    }

    /**
     * Matches {@link MethodDescription}s that returns a given
     * {@link TypeDescription}.
     *
     * @param typeDescription The type the matched method is expected to return.
     * @param <T>             The type of the matched object.
     * @return An element matcher that matches a given return type for a method description.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> returns(GenericTypeDescription typeDescription) {
        return returns(is(nonNull(typeDescription)));
    }

    /**
     * Matches {@link MethodDescription}s that matches a matched method's
     * return type.
     *
     * @param matcher A matcher to apply onto a matched method's return type.
     * @param <T>     The type of the matched object.
     * @return An element matcher that matches a given return type against another {@code matcher}.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> returns(ElementMatcher<? super TypeDescription> matcher) {
        return new MethodReturnTypeMatcher<T>(nonNull(matcher));
    }

    /**
     * Matches a {@link MethodDescription} by its exact parameter types.
     *
     * @param type The parameter types of a method in their order.
     * @param <T>  The type of the matched object.
     * @return An element matcher that matches a method by its exact argument types.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> takesArguments(Type... type) {
        return takesArguments(new GenericTypeList.ForLoadedType(nonNull(type)));
    }

    /**
     * Matches a {@link MethodDescription} by its exact parameter types.
     *
     * @param typeDescription The parameter types of a method in their order.
     * @param <T>             The type of the matched object.
     * @return An element matcher that matches a method by its exact argument types.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> takesArguments(GenericTypeDescription... typeDescription) {
        return takesArguments((Arrays.asList(nonNull(typeDescription))));
    }

    /**
     * Matches a {@link MethodDescription} by its exact parameter types.
     *
     * @param typeDescriptions The parameter types of a method in their order.
     * @param <T>              The type of the matched object.
     * @return An element matcher that matches a method by its exact argument types.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> takesArguments(Iterable<? extends GenericTypeDescription> typeDescriptions) {
        List<ElementMatcher<? super GenericTypeDescription>> typeMatchers = new LinkedList<ElementMatcher<? super GenericTypeDescription>>();
        for (GenericTypeDescription typeDescription : typeDescriptions) {
            typeMatchers.add(is(nonNull(typeDescription)));
        }
        return takesArguments(new CollectionOneToOneMatcher<GenericTypeDescription>(typeMatchers));
    }

    /**
     * Matches a {@link MethodDescription} by applying an iterable collection
     * of element matcher on any parameter's {@link TypeDescription}.
     *
     * @param matchers The matcher that are applied onto the parameter types of the matched method description.
     * @param <T>      The type of the matched object.
     * @return A matcher that matches a method description by applying another element matcher onto each
     * parameter's type.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> takesArguments(
            ElementMatcher<? super Iterable<? extends GenericTypeDescription>> matchers) {
        return new MethodParameterMatcher<T>(new MethodParameterTypeMatcher<ParameterList>(nonNull(matchers)));
    }

    /**
     * Matches a {@link MethodDescription} by the number of its parameters.
     *
     * @param length The expected length.
     * @param <T>    The type of the matched object.
     * @return A matcher that matches a method description by the number of its parameters.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> takesArguments(int length) {
        return new MethodParameterMatcher<T>(new CollectionSizeMatcher<ParameterList>(length));
    }

    /**
     * Matches a {@link MethodDescription} by validating that at least one
     * parameter fullfils a given constraint.
     *
     * @param matcher The constraint to check the parameters against.
     * @param <T>     The type of the matched object.
     * @return A matcher that matches a method description's parameters against the given constraint.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> hasParameter(ElementMatcher<? super ParameterDescription> matcher) {
        return hasParameters(new CollectionItemMatcher<ParameterDescription>(nonNull(matcher)));
    }

    /**
     * Matches a {@link MethodDescription} by validating that its parameters
     * fulfill a given constraint.
     *
     * @param matcher The matcher to apply for validating the parameters.
     * @param <T>     The type of the matched object.
     * @return A matcher that matches a method description's parameters against the given constraint.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> hasParameters(ElementMatcher<? super Iterable<? extends ParameterDescription>> matcher) {
        return new MethodParameterMatcher<T>(nonNull(matcher));
    }

    /**
     * Matches a {@link MethodDescription} by its capability to throw a given
     * checked exception. For specifying a non-checked exception, any method is matched.
     *
     * @param exceptionType The type of the exception that should be declared by the method to be matched.
     * @param <T>           The type of the matched object.
     * @return A matcher that matches a method description by its declaration of throwing a checked exception.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> canThrow(Class<? extends Throwable> exceptionType) {
        return canThrow(new TypeDescription.ForLoadedType(nonNull(exceptionType)));
    }

    /**
     * Matches a {@link MethodDescription} by its capability to throw a given
     * checked exception. For specifying a non-checked exception, any method is matched.
     *
     * @param exceptionType The type of the exception that should be declared by the method to be matched.
     * @param <T>           The type of the matched object.
     * @return A matcher that matches a method description by its declaration of throwing a checked exception.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> canThrow(TypeDescription exceptionType) {
        return exceptionType.isAssignableTo(RuntimeException.class) || exceptionType.isAssignableTo(Error.class)
                ? new BooleanMatcher<T>(true)
                : ElementMatchers.<T>declaresException(exceptionType);
    }

    /**
     * Matches a {@link MethodDescription} by its capability to throw a given
     * checked exception. For specifying a non-checked exception, any method is matched.
     *
     * @param exceptionType The type of the exception that should be declared by the method to be matched.
     * @param <T>           The type of the matched object.
     * @return A matcher that matches a method description by its declaration of throwing a checked exception.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> declaresException(Class<? extends Throwable> exceptionType) {
        return declaresException(new TypeDescription.ForLoadedType(nonNull(exceptionType)));
    }

    /**
     * Matches a {@link MethodDescription} by its capability to throw a given
     * checked exception. For specifying a non-checked exception, any method is matched.
     *
     * @param exceptionType The type of the exception that should be declared by the method to be matched.
     * @param <T>           The type of the matched object.
     * @return A matcher that matches a method description by its declaration of throwing a checked exception.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> declaresException(TypeDescription exceptionType) {
        return exceptionType.isAssignableTo(Throwable.class)
                ? ElementMatchers.<T>declaresException(new CollectionItemMatcher<TypeDescription>(new SubTypeMatcher<TypeDescription>(exceptionType)))
                : new BooleanMatcher<T>(false);
    }

    /**
     * Matches a {@link MethodDescription} by its declared exceptions.
     *
     * @param exceptionMatcher A matcher that is applied by to the declared exceptions.
     * @param <T>              The type of the matched object.
     * @return A matcher that matches a method description by its declared exceptions.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> declaresException(
            ElementMatcher<? super List<? extends TypeDescription>> exceptionMatcher) {
        return new MethodExceptionTypeMatcher<T>(nonNull(exceptionMatcher));
    }

    /**
     * Only matches method descriptions that represent a {@link java.lang.reflect.Method}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches method descriptions that represent a Java method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isMethod() {
        return new MethodSortMatcher<T>(MethodSortMatcher.Sort.METHOD);
    }

    /**
     * Only matches method descriptions that represent a {@link java.lang.reflect.Constructor}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches method descriptions that represent a Java constructor.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isConstructor() {
        return new MethodSortMatcher<T>(MethodSortMatcher.Sort.CONSTRUCTOR);
    }

    /**
     * Only matches method descriptions that represent a {@link java.lang.Class} type initializer.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches method descriptions that represent the type initializer.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isTypeInitializer() {
        return new MethodSortMatcher<T>(MethodSortMatcher.Sort.TYPE_INITIALIZER);
    }

    /**
     * Only matches method descriptions that represent a visibility bridge. A visibility bridge is a Java bridge
     * method that was inserted by the compiler in order to increase the visibility of a method when inheriting
     * a {@code public} method from a package-private type. In this case, the package-private type's method
     * is declared to be package-private itself such that the bridge method needs to increase the visibility and
     * delegates the call to the original, package-private implementation.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that matches visibility bridge methods.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isVisibilityBridge() {
        return new MethodSortMatcher<T>(MethodSortMatcher.Sort.VISIBILITY_BRIDGE);
    }

    /**
     * Only matches methods that are overridable, i.e. non-final and dispatched virtually.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches overridable methods.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isOverridable() {
        return new MethodSortMatcher<T>(MethodSortMatcher.Sort.OVERRIDABLE);
    }

    /**
     * Only matches Java 8 default methods.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches Java 8 default methods.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isDefaultMethod() {
        return new MethodSortMatcher<T>(MethodSortMatcher.Sort.DEFAULT_METHOD);
    }

    /**
     * Matches a default constructor, i.e. a constructor without arguments.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that matches a default constructor.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isDefaultConstructor() {
        return isConstructor().and(takesArguments(0));
    }

    /**
     * Only matches the {@link Object#finalize()} method if it was not overridden.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches a non-overridden {@link Object#finalize()} method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isDefaultFinalizer() {
        return isFinalizer().and(isDeclaredBy(TypeDescription.OBJECT));
    }

    /**
     * Only matches the {@link Object#finalize()} method, even if it was overridden.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches the {@link Object#finalize()} method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isFinalizer() {
        return named("finalize").and(takesArguments(0)).and(returns(TypeDescription.VOID));
    }

    /**
     * Only matches the {@link Object#toString()} method, also if it was overridden.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches the {@link Object#toString()} method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isHashCode() {
        return named("hashCode").and(takesArguments(0)).and(returns(int.class));
    }

    /**
     * Only matches the {@link Object#equals(Object)} method, also if it was overridden.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches the {@link Object#equals(Object)} method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isEquals() {
        return named("equals").and(takesArguments(TypeDescription.OBJECT)).and(returns(boolean.class));
    }

    /**
     * Only matches the {@link Object#clone()} method, also if it was overridden.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches the {@link Object#clone()} method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isClone() {
        return named("clone").and(takesArguments(0)).and(returns(TypeDescription.OBJECT));
    }

    /**
     * Only matches the {@link Object#toString()} method, also if it was overridden.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches the {@link Object#toString()} method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isToString() {
        return named("toString").and(takesArguments(0)).and(returns(TypeDescription.STRING));
    }

    /**
     * Matches any Java bean setter method.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that matches any setter method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isSetter() {
        return nameStartsWith("set").and(takesArguments(1)).and(returns(TypeDescription.VOID));
    }

    /**
     * Matches any Java bean setter method which takes an argument the given type.
     *
     * @param type The required setter type.
     * @param <T>  The type of the matched object.
     * @return A matcher that matches any setter method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isSetter(Type type) {
        return isSetter(GenericTypeDescription.Sort.describe(nonNull(type)));
    }

    /**
     * Matches any Java bean setter method which takes an argument the given type.
     *
     * @param typeDescription The required setter type.
     * @param <T>             The type of the matched object.
     * @return A matcher that matches a setter method with the specified argument type.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isSetter(GenericTypeDescription typeDescription) {
        return isSetter(is(nonNull(typeDescription)));
    }

    /**
     * Matches any Java bean setter method which takes an argument that matches the supplied matcher.
     *
     * @param matcher A matcher to be allied to a setter method's argument type.
     * @param <T>     The type of the matched object.
     * @return A matcher that matches a setter method with an argument type that matches the supplied matcher.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isSetter(ElementMatcher<? super GenericTypeDescription> matcher) {
        return isSetter().and(takesArguments(new CollectionOneToOneMatcher<GenericTypeDescription>(Collections.singletonList(nonNull(matcher)))));
    }

    /**
     * Matches any Java bean getter method.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that matches any getter method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isGetter() {
        return takesArguments(0).and(not(returns(TypeDescription.VOID))).and(nameStartsWith("get")
                .or(nameStartsWith("is").and(returns(anyOf(boolean.class, Boolean.class)))));
    }

    /**
     * Matches any Java bean getter method which returns the given type.
     *
     * @param type The required getter type.
     * @param <T>  The type of the matched object.
     * @return A matcher that matches a getter method with the given type.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isGetter(Type type) {
        return isGetter(GenericTypeDescription.Sort.describe(nonNull(type)));
    }

    /**
     * Matches any Java bean getter method which returns the given type.
     *
     * @param typeDescription The required getter type.
     * @param <T>             The type of the matched object.
     * @return A matcher that matches a getter method with the given type.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isGetter(GenericTypeDescription typeDescription) {
        return isGetter(is(nonNull(typeDescription)));
    }

    /**
     * Matches any Java bean getter method which returns an value with a type matches the supplied matcher.
     *
     * @param matcher A matcher to be allied to a getter method's argument type.
     * @param <T>     The type of the matched object.
     * @return A matcher that matches a getter method with a return type that matches the supplied matcher.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isGetter(ElementMatcher<? super GenericTypeDescription> matcher) {
        return isGetter().and(returns(nonNull(matcher)));
    }

    /**
     * Matches a <i>specialized</i> version of a given method. This method is characterized by an identical name and
     * by a return type that is a sub type of the given method's return type and by parameter types that are sub types
     * of the the given method's parameter types.
     *
     * @param methodDescription The method description to match.
     * @param <T>               The type of the matched object.
     * @return A matcher that matches a specialized version of the given method.
     */
    public static <T extends MethodDescription> ElementMatcher.Junction<T> isSpecializationOf(MethodDescription methodDescription) {
        TypeList parameterTypes = methodDescription.getParameters().asTypeList();
        List<ElementMatcher<GenericTypeDescription>> matchers = new ArrayList<ElementMatcher<GenericTypeDescription>>(parameterTypes.size());
        for (TypeDescription typeDescription : parameterTypes) {
            matchers.add(rawType(isSubTypeOf(typeDescription)));
        }
        return (methodDescription.isStatic() ? ElementMatchers.<T>isStatic() : ElementMatchers.<T>not(isStatic()))
                .<T>and(named(methodDescription.getSourceCodeName()))
                .<T>and(returns(isSubTypeOf(methodDescription.getReturnType())))
                .and(takesArguments(new CollectionOneToOneMatcher<GenericTypeDescription>(matchers)));
    }

    /**
     * Matches any type description that is a subtype of the given type.
     *
     * @param type The type to be checked being a super type of the matched type.
     * @param <T>  The type of the matched object.
     * @return A matcher that matches any type description that represents a sub type of the given type.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> isSubTypeOf(Class<?> type) {
        return isSubTypeOf(new TypeDescription.ForLoadedType(nonNull(type)));
    }

    /**
     * Matches any type description that is a subtype of the given type.
     *
     * @param typeDescription The type to be checked being a super type of the matched type.
     * @param <T>             The type of the matched object.
     * @return A matcher that matches any type description that represents a sub type of the given type.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> isSubTypeOf(TypeDescription typeDescription) {
        return new SubTypeMatcher<T>(nonNull(typeDescription));
    }

    /**
     * Matches any type description that is a super type of the given type.
     *
     * @param type The type to be checked being a subtype of the matched type.
     * @param <T>  The type of the matched object.
     * @return A matcher that matches any type description that represents a super type of the given type.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> isSuperTypeOf(Class<?> type) {
        return isSuperTypeOf(new TypeDescription.ForLoadedType(nonNull(type)));
    }

    /**
     * Matches any type description that is a super type of the given type.
     *
     * @param typeDescription The type to be checked being a subtype of the matched type.
     * @param <T>             The type of the matched object.
     * @return A matcher that matches any type description that represents a super type of the given type.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> isSuperTypeOf(TypeDescription typeDescription) {
        return new SuperTypeMatcher<T>(nonNull(typeDescription));
    }

    /**
     * Matches any annotations by their type on a type that declared these annotations or inherited them from its
     * super classes.
     *
     * @param type The annotation type to be matched.
     * @param <T>  The type of the matched object.
     * @return A matcher that matches any inherited annotation by their type.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> inheritsAnnotation(Class<?> type) {
        return inheritsAnnotation(new TypeDescription.ForLoadedType(nonNull(type)));
    }

    /**
     * Matches any annotations by their type on a type that declared these annotations or inherited them from its
     * super classes.
     *
     * @param typeDescription The annotation type to be matched.
     * @param <T>             The type of the matched object.
     * @return A matcher that matches any inherited annotation by their type.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> inheritsAnnotation(TypeDescription typeDescription) {
        return inheritsAnnotation(is(nonNull(typeDescription)));
    }

    /**
     * Matches any annotations by a given matcher on a type that declared these annotations or inherited them from its
     * super classes.
     *
     * @param matcher A matcher to apply onto the inherited annotations.
     * @param <T>     The type of the matched object.
     * @return A matcher that matches any inherited annotation by a given matcher.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> inheritsAnnotation(ElementMatcher<? super TypeDescription> matcher) {
        return hasAnnotation(new AnnotationTypeMatcher<AnnotationDescription>(nonNull(matcher)));
    }

    /**
     * Matches a list of annotations by a given matcher on a type that declared these annotations or inherited them
     * from its super classes.
     *
     * @param matcher A matcher to apply onto a list of inherited annotations.
     * @param <T>     The type of the matched object.
     * @return A matcher that matches a list of inherited annotation by a given matcher.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> hasAnnotation(ElementMatcher<? super AnnotationDescription> matcher) {
        return new InheritedAnnotationMatcher<T>(new CollectionItemMatcher<AnnotationDescription>(nonNull(matcher)));
    }

    /**
     * Matches a type by a another matcher that is applied on any of its declared fields.
     *
     * @param fieldMatcher The matcher that is applied onto each declared field.
     * @param <T>          The type of the matched object.
     * @return A matcher that matches any type where another matcher is matched positively on at least on declared field.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> declaresField(ElementMatcher<? super FieldDescription> fieldMatcher) {
        return new DeclaringFieldMatcher<T>(new CollectionItemMatcher<FieldDescription>(nonNull(fieldMatcher)));
    }

    /**
     * Matches a type by a another matcher that is applied on any of its declared methods.
     *
     * @param methodMatcher The matcher that is applied onto each declared method.
     * @param <T>           The type of the matched object.
     * @return A matcher that matches any type where another matcher is matched positively on at least on declared methods.
     */
    public static <T extends TypeDescription> ElementMatcher.Junction<T> declaresMethod(ElementMatcher<? super MethodDescription> methodMatcher) {
        return new DeclaringMethodMatcher<T>(new CollectionItemMatcher<MethodDescription>(nonNull(methodMatcher)));
    }

    /**
     * Matches exactly the bootstrap {@link java.lang.ClassLoader} . The returned matcher is a synonym to
     * a matcher matching {@code null}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches the bootstrap class loader.
     */
    public static <T extends ClassLoader> ElementMatcher<T> isBootstrapClassLoader() {
        return new NullMatcher<T>();
    }

    /**
     * Matches exactly the system {@link java.lang.ClassLoader}. The returned matcher is a synonym to
     * a matcher matching {@code ClassLoader.gerSystemClassLoader()}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches the system class loader.
     */
    public static <T extends ClassLoader> ElementMatcher<T> isSystemClassLoader() {
        return new EqualityMatcher<T>(ClassLoader.getSystemClassLoader());
    }

    /**
     * Matches exactly the extension {@link java.lang.ClassLoader}. The returned matcher is a synonym to
     * a matcher matching {@code ClassLoader.gerSystemClassLoader().getParent()}.
     *
     * @param <T> The type of the matched object.
     * @return A matcher that only matches the extension class loader.
     */
    public static <T extends ClassLoader> ElementMatcher<T> isExtensionClassLoader() {
        return new EqualityMatcher<T>(ClassLoader.getSystemClassLoader().getParent());
    }

    /**
     * Matches any class loader that is either the given class loader or a child of the given class loader.
     *
     * @param classLoader The class loader of which child class loaders are matched.
     * @param <T>         The type of the matched object.
     * @return A matcher that matches the given class loader and any class loader that is a child of the given
     * class loader.
     */
    public static <T extends ClassLoader> ElementMatcher<T> isChildOf(ClassLoader classLoader) {
        return classLoader == BOOTSTRAP_CLASSLOADER
                ? new BooleanMatcher<T>(true)
                : ElementMatchers.<T>hasChild(is(classLoader));
    }

    /**
     * Matches all class loaders in the hierarchy of the matched class loader against a given matcher.
     *
     * @param matcher The matcher to apply to all class loaders in the hierarchy of the matched class loader.
     * @param <T>     The type of the matched object.
     * @return A matcher that matches all class loaders in the hierarchy of the matched class loader.
     */
    public static <T extends ClassLoader> ElementMatcher<T> hasChild(ElementMatcher<? super ClassLoader> matcher) {
        return new ClassLoaderHierarchyMatcher<T>(nonNull(matcher));
    }

    /**
     * Matches any class loader that is either the given class loader or a parent of the given class loader.
     *
     * @param classLoader The class loader of which parent class loaders are matched.
     * @param <T>         The type of the matched object.
     * @return A matcher that matches the given class loader and any class loader that is a parent of the given
     * class loader.
     */
    public static <T extends ClassLoader> ElementMatcher<T> isParentOf(ClassLoader classLoader) {
        return classLoader == BOOTSTRAP_CLASSLOADER
                ? ElementMatchers.<T>isBootstrapClassLoader()
                : new ClassLoaderParentMatcher<T>(classLoader);
    }
}


File: byte-buddy-dep/src/main/java/net/bytebuddy/pool/TypePool.java
package net.bytebuddy.pool;

import net.bytebuddy.description.annotation.AnnotationDescription;
import net.bytebuddy.description.annotation.AnnotationList;
import net.bytebuddy.description.enumeration.EnumerationDescription;
import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.field.FieldList;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.method.MethodList;
import net.bytebuddy.description.method.ParameterDescription;
import net.bytebuddy.description.method.ParameterList;
import net.bytebuddy.description.type.PackageDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.TypeList;
import net.bytebuddy.description.type.generic.GenericTypeDescription;
import net.bytebuddy.description.type.generic.GenericTypeList;
import net.bytebuddy.description.type.generic.TypeVariableSource;
import net.bytebuddy.dynamic.ClassFileLocator;
import net.bytebuddy.implementation.bytecode.StackSize;
import net.bytebuddy.matcher.ElementMatchers;
import net.bytebuddy.matcher.FilterableList;
import net.bytebuddy.utility.PropertyDispatcher;
import org.objectweb.asm.*;
import org.objectweb.asm.signature.SignatureReader;
import org.objectweb.asm.signature.SignatureVisitor;

import java.io.IOException;
import java.lang.annotation.Annotation;
import java.lang.reflect.Array;
import java.lang.reflect.MalformedParameterizedTypeException;
import java.lang.reflect.Proxy;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

import static net.bytebuddy.matcher.ElementMatchers.*;

/**
 * A type pool allows the retrieval of {@link TypeDescription} by its name.
 */
public interface TypePool {

    /**
     * Locates and describes the given type by its name.
     *
     * @param name The name of the type to describe. The name is to be written as when calling {@link Object#toString()}
     *             on a loaded {@link java.lang.Class}.
     * @return A resolution of the type to describe. If the type to be described was found, the returned
     * {@link net.bytebuddy.pool.TypePool.Resolution} represents this type. Otherwise, an illegal resolution is
     * returned.
     */
    Resolution describe(String name);

    /**
     * Clears this type pool's cache.
     */
    void clear();

    /**
     * A resolution of a {@link net.bytebuddy.pool.TypePool} which was queried for a description.
     */
    interface Resolution {

        /**
         * Determines if this resolution represents a {@link TypeDescription}.
         *
         * @return {@code true} if the queried type could be resolved.
         */
        boolean isResolved();

        /**
         * Resolves this resolution to the represented type description. This method must only be invoked if this
         * instance could be resolved. Otherwise, an exception is thrown on calling this method.
         *
         * @return The type description that is represented by this resolution.
         */
        TypeDescription resolve();

        /**
         * A simple resolution that represents a given {@link TypeDescription}.
         */
        class Simple implements Resolution {

            /**
             * The represented type description.
             */
            private final TypeDescription typeDescription;

            /**
             * Creates a new successful resolution of a given type description.
             *
             * @param typeDescription The represented type description.
             */
            public Simple(TypeDescription typeDescription) {
                this.typeDescription = typeDescription;
            }

            @Override
            public boolean isResolved() {
                return true;
            }

            @Override
            public TypeDescription resolve() {
                return typeDescription;
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && typeDescription.equals(((Simple) other).typeDescription);
            }

            @Override
            public int hashCode() {
                return typeDescription.hashCode();
            }

            @Override
            public String toString() {
                return "TypePool.Resolution.Simple{" +
                        "typeDescription=" + typeDescription +
                        '}';
            }
        }

        /**
         * A canonical representation of a non-successful resolution of a {@link net.bytebuddy.pool.TypePool}.
         */
        class Illegal implements Resolution {

            /**
             * The name of the unresolved type.
             */
            private final String name;

            /**
             * Creates a new illegal resolution.
             *
             * @param name The name of the unresolved type.
             */
            public Illegal(String name) {
                this.name = name;
            }

            @Override
            public boolean isResolved() {
                return false;
            }

            @Override
            public TypeDescription resolve() {
                throw new IllegalStateException("Cannot resolve type description for " + name);
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && name.equals(((Illegal) other).name);
            }

            @Override
            public int hashCode() {
                return name.hashCode();
            }

            @Override
            public String toString() {
                return "TypePool.Resolution.Illegal{" +
                        "name='" + name + '\'' +
                        '}';
            }
        }
    }

    /**
     * A cache provider for a {@link net.bytebuddy.pool.TypePool}.
     */
    interface CacheProvider {

        /**
         * The value that is returned on a cache-miss.
         */
        Resolution NOTHING = null;

        /**
         * Attempts to find a resolution in this cache.
         *
         * @param name The name of the type to describe.
         * @return A resolution of the type or {@code null} if no such resolution can be found in the cache..
         */
        Resolution find(String name);

        /**
         * Registers a resolution in this cache. If a resolution to the given name already exists in the
         * cache, it should be discarded.
         *
         * @param name       The name of the type that is to be registered.
         * @param resolution The resolution to register.
         * @return The oldest version of a resolution that is currently registered in the cache which might
         * be the given resolution or another resolution that was previously registered.
         */
        Resolution register(String name, Resolution resolution);

        /**
         * Clears this cache.
         */
        void clear();

        /**
         * A non-operational cache that does not store any type descriptions.
         */
        enum NoOp implements CacheProvider {

            /**
             * The singleton instance.
             */
            INSTANCE;

            @Override
            public Resolution find(String name) {
                return NOTHING;
            }

            @Override
            public Resolution register(String name, Resolution resolution) {
                return resolution;
            }

            @Override
            public void clear() {
                /* do nothing */
            }

            @Override
            public String toString() {
                return "TypePool.CacheProvider.NoOp." + name();
            }
        }

        /**
         * A simple, thread-safe type cache based on a {@link java.util.concurrent.ConcurrentHashMap}.
         */
        class Simple implements CacheProvider {

            /**
             * A map containing all cached resolutions by their names.
             */
            private final ConcurrentMap<String, Resolution> cache;

            /**
             * Creates a new simple cache.
             */
            public Simple() {
                cache = new ConcurrentHashMap<String, Resolution>();
            }

            @Override
            public Resolution find(String name) {
                return cache.get(name);
            }

            @Override
            public Resolution register(String name, Resolution resolution) {
                Resolution cached = cache.putIfAbsent(name, resolution);
                return cached == NOTHING ? resolution : cached;
            }

            @Override
            public void clear() {
                cache.clear();
            }

            @Override
            public String toString() {
                return "TypePool.CacheProvider.Simple{cache=" + cache + '}';
            }
        }
    }

    /**
     * A base implementation of a {@link net.bytebuddy.pool.TypePool} that is managing a cache provider and
     * that handles the description of array and primitive types.
     */
    abstract class AbstractBase implements TypePool {

        /**
         * A map of primitive types by their name.
         */
        protected static final Map<String, TypeDescription> PRIMITIVE_TYPES;

        /**
         * A map of primitive types by their descriptor.
         */
        protected static final Map<String, String> PRIMITIVE_DESCRIPTORS;

        /**
         * The array symbol as used by Java descriptors.
         */
        private static final String ARRAY_SYMBOL = "[";

        /*
         * Initializes the maps of primitive type names and descriptors.
         */
        static {
            Map<String, TypeDescription> primitiveTypes = new HashMap<String, TypeDescription>();
            Map<String, String> primitiveDescriptors = new HashMap<String, String>();
            for (Class<?> primitiveType : new Class<?>[]{boolean.class,
                    byte.class,
                    short.class,
                    char.class,
                    int.class,
                    long.class,
                    float.class,
                    double.class,
                    void.class}) {
                primitiveTypes.put(primitiveType.getName(), new TypeDescription.ForLoadedType(primitiveType));
                primitiveDescriptors.put(Type.getDescriptor(primitiveType), primitiveType.getName());
            }
            PRIMITIVE_TYPES = Collections.unmodifiableMap(primitiveTypes);
            PRIMITIVE_DESCRIPTORS = Collections.unmodifiableMap(primitiveDescriptors);
        }

        /**
         * The cache provider of this instance.
         */
        protected final CacheProvider cacheProvider;

        /**
         * Creates a new instance.
         *
         * @param cacheProvider The cache provider to be used.
         */
        protected AbstractBase(CacheProvider cacheProvider) {
            this.cacheProvider = cacheProvider;
        }

        @Override
        public Resolution describe(String name) {
            if (name.contains("/")) {
                throw new IllegalArgumentException(name + " contains the illegal character '/'");
            }
            int arity = 0;
            while (name.startsWith(ARRAY_SYMBOL)) {
                arity++;
                name = name.substring(1);
            }
            if (arity > 0) {
                String primitiveName = PRIMITIVE_DESCRIPTORS.get(name);
                name = primitiveName == null ? name.substring(1, name.length() - 1) : primitiveName;
            }
            TypeDescription typeDescription = PRIMITIVE_TYPES.get(name);
            Resolution resolution = typeDescription == null
                    ? cacheProvider.find(name)
                    : new Resolution.Simple(typeDescription);
            if (resolution == null) {
                resolution = cacheProvider.register(name, doDescribe(name));
            }
            return ArrayTypeResolution.of(resolution, arity);
        }

        @Override
        public void clear() {
            cacheProvider.clear();
        }

        /**
         * Determines a resolution to a non-primitive, non-array type.
         *
         * @param name The name of the type to describe.
         * @return A resolution to the type to describe.
         */
        protected abstract Resolution doDescribe(String name);

        @Override
        public boolean equals(Object other) {
            return this == other || !(other == null || getClass() != other.getClass())
                    && cacheProvider.equals(((AbstractBase) other).cacheProvider);
        }

        @Override
        public int hashCode() {
            return cacheProvider.hashCode();
        }

        /**
         * A resolution for a type that, if resolved, represents an array type.
         */
        protected static class ArrayTypeResolution implements Resolution {

            /**
             * The underlying resolution that is represented by this instance.
             */
            private final Resolution resolution;

            /**
             * The arity of the represented array.
             */
            private final int arity;

            /**
             * Creates a wrapper for another resolution that, if resolved, represents an array type.
             *
             * @param resolution The underlying resolution that is represented by this instance.
             * @param arity      The arity of the represented array.
             */
            protected ArrayTypeResolution(Resolution resolution, int arity) {
                this.resolution = resolution;
                this.arity = arity;
            }

            /**
             * Creates a wrapper for another resolution that, if resolved, represents an array type. The wrapper
             * is only created if the arity is not zero. If the arity is zero, the given resolution is simply
             * returned instead.
             *
             * @param resolution The underlying resolution that is represented by this instance.
             * @param arity      The arity of the represented array.
             * @return A wrapper for another resolution that, if resolved, represents an array type or the
             * given resolution if the given arity is zero.
             */
            protected static Resolution of(Resolution resolution, int arity) {
                return arity == 0
                        ? resolution
                        : new ArrayTypeResolution(resolution, arity);
            }

            @Override
            public boolean isResolved() {
                return resolution.isResolved();
            }

            @Override
            public TypeDescription resolve() {
                return TypeDescription.ArrayProjection.of(resolution.resolve(), arity);
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && arity == ((ArrayTypeResolution) other).arity
                        && resolution.equals(((ArrayTypeResolution) other).resolution);
            }

            @Override
            public int hashCode() {
                int result = resolution.hashCode();
                result = 31 * result + arity;
                return result;
            }

            @Override
            public String toString() {
                return "TypePool.AbstractBase.ArrayTypeResolution{" +
                        "resolution=" + resolution +
                        ", arity=" + arity +
                        '}';
            }
        }

        /**
         * Represents a nested annotation value.
         */
        protected static class RawAnnotationValue implements AnnotationDescription.AnnotationValue<AnnotationDescription, Annotation> {

            /**
             * The type pool to use for looking up types.
             */
            private final TypePool typePool;

            /**
             * The annotation token that represents the nested invocation.
             */
            private final LazyTypeDescription.AnnotationToken annotationToken;

            /**
             * Creates a new annotation value for a nested annotation.
             *
             * @param typePool        The type pool to use for looking up types.
             * @param annotationToken The token that represents the annotation.
             */
            public RawAnnotationValue(TypePool typePool, LazyTypeDescription.AnnotationToken annotationToken) {
                this.typePool = typePool;
                this.annotationToken = annotationToken;
            }

            @Override
            public AnnotationDescription resolve() {
                return annotationToken.toAnnotationDescription(typePool);
            }

            @Override
            @SuppressWarnings("unchecked")
            public Loaded<Annotation> load(ClassLoader classLoader) throws ClassNotFoundException {
                Class<?> type = classLoader.loadClass(annotationToken.getDescriptor()
                        .substring(1, annotationToken.getDescriptor().length() - 1)
                        .replace('/', '.'));
                if (type.isAnnotation()) {
                    return new ForAnnotation.Loaded<Annotation>((Annotation) Proxy.newProxyInstance(classLoader,
                            new Class<?>[]{type},
                            AnnotationDescription.AnnotationInvocationHandler.of(classLoader,
                                    (Class<? extends Annotation>) type,
                                    annotationToken.getValues())));
                } else {
                    return new ForAnnotation.IncompatibleRuntimeType(type);
                }
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && annotationToken.equals(((RawAnnotationValue) other).annotationToken);
            }

            @Override
            public int hashCode() {
                return annotationToken.hashCode();
            }

            @Override
            public String toString() {
                return "TypePool.AbstractBase.RawAnnotationValue{" +
                        "annotationToken=" + annotationToken +
                        '}';
            }
        }

        /**
         * Represents an enumeration value of an annotation.
         */
        protected static class RawEnumerationValue implements AnnotationDescription.AnnotationValue<EnumerationDescription, Enum<?>> {

            /**
             * The type pool to use for looking up types.
             */
            private final TypePool typePool;

            /**
             * The descriptor of the enumeration type.
             */
            private final String descriptor;

            /**
             * The name of the enumeration.
             */
            private final String value;

            /**
             * Creates a new enumeration value representation.
             *
             * @param typePool   The type pool to use for looking up types.
             * @param descriptor The descriptor of the enumeration type.
             * @param value      The name of the enumeration.
             */
            public RawEnumerationValue(TypePool typePool, String descriptor, String value) {
                this.typePool = typePool;
                this.descriptor = descriptor;
                this.value = value;
            }

            @Override
            public EnumerationDescription resolve() {
                return new LazyEnumerationDescription();
            }

            @Override
            @SuppressWarnings("unchecked")
            public Loaded<Enum<?>> load(ClassLoader classLoader) throws ClassNotFoundException {
                Class<?> type = classLoader.loadClass(descriptor.substring(1, descriptor.length() - 1).replace('/', '.'));
                try {
                    return type.isEnum()
                            ? new ForEnumeration.Loaded(Enum.valueOf((Class) type, value))
                            : new ForEnumeration.IncompatibleRuntimeType(type);
                } catch (IllegalArgumentException ignored) {
                    return new ForEnumeration.UnknownRuntimeEnumeration((Class) type, value);
                }
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && descriptor.equals(((RawEnumerationValue) other).descriptor)
                        && value.equals(((RawEnumerationValue) other).value);
            }

            @Override
            public int hashCode() {
                return 31 * descriptor.hashCode() + value.hashCode();
            }

            @Override
            public String toString() {
                return "TypePool.LazyTypeDescription.AnnotationValue.ForEnumeration{" +
                        "descriptor='" + descriptor + '\'' +
                        ", value='" + value + '\'' +
                        '}';
            }

            /**
             * An enumeration description where any type references are only resolved on demand.
             */
            protected class LazyEnumerationDescription extends EnumerationDescription.AbstractEnumerationDescription {

                @Override
                public String getValue() {
                    return value;
                }

                @Override
                public TypeDescription getEnumerationType() {
                    return typePool.describe(descriptor.substring(1, descriptor.length() - 1).replace('/', '.')).resolve();
                }

                @Override
                public <T extends Enum<T>> T load(Class<T> type) {
                    return Enum.valueOf(type, value);
                }
            }
        }

        /**
         * Represents a type value of an annotation.
         */
        protected static class RawTypeValue implements AnnotationDescription.AnnotationValue<TypeDescription, Class<?>> {

            /**
             * A convenience reference indicating that a loaded type should not be initialized.
             */
            private static final boolean NO_INITIALIZATION = false;

            /**
             * The type pool to use for looking up types.
             */
            private final TypePool typePool;

            /**
             * The binary name of the type.
             */
            private final String name;

            /**
             * Represents a type value of an annotation.
             *
             * @param typePool The type pool to use for looking up types.
             * @param type     A type representation of the type that is referenced by the annotation..
             */
            public RawTypeValue(TypePool typePool, Type type) {
                this.typePool = typePool;
                name = type.getSort() == Type.ARRAY
                        ? type.getInternalName().replace('/', '.')
                        : type.getClassName();
            }

            @Override
            public TypeDescription resolve() {
                return typePool.describe(name).resolve();
            }

            @Override
            public AnnotationDescription.AnnotationValue.Loaded<Class<?>> load(ClassLoader classLoader) throws ClassNotFoundException {
                return new Loaded(Class.forName(name, NO_INITIALIZATION, classLoader));
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && name.equals(((RawTypeValue) other).name);
            }

            @Override
            public int hashCode() {
                return name.hashCode();
            }

            @Override
            public String toString() {
                return "TypePool.LazyTypeDescription.AnnotationValue.ForType{" +
                        "name='" + name + '\'' +
                        '}';
            }

            /**
             * Represents a loaded annotation property that represents a type.
             */
            protected class Loaded implements AnnotationDescription.AnnotationValue.Loaded<Class<?>> {

                /**
                 * The type that is represented by an annotation property.
                 */
                private final Class<?> type;

                /**
                 * Creates a new representation for an annotation property referencing a type.
                 *
                 * @param type The type that is represented by an annotation property.
                 */
                public Loaded(Class<?> type) {
                    this.type = type;
                }

                @Override
                public State getState() {
                    return State.RESOLVED;
                }

                @Override
                public Class<?> resolve() {
                    return type;
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (!(other instanceof AnnotationDescription.AnnotationValue.Loaded<?>)) return false;
                    AnnotationDescription.AnnotationValue.Loaded<?> loadedOther = (AnnotationDescription.AnnotationValue.Loaded<?>) other;
                    return loadedOther.getState().isResolved() && type.equals(loadedOther.resolve());
                }

                @Override
                public int hashCode() {
                    return type.hashCode();
                }

                @Override
                public String toString() {
                    return type.toString();
                }
            }
        }

        /**
         * Represents an array that is referenced by an annotation which does not contain primitive values.
         */
        protected static class RawNonPrimitiveArray implements AnnotationDescription.AnnotationValue<Object[], Object[]> {

            /**
             * The type pool to use for looking up types.
             */
            private final TypePool typePool;

            /**
             * A reference to the component type.
             */
            private final ComponentTypeReference componentTypeReference;

            /**
             * A list of all values of this array value in their order.
             */
            private List<AnnotationDescription.AnnotationValue<?, ?>> value;

            /**
             * Creates a new array value representation of a complex array.
             *
             * @param typePool               The type pool to use for looking up types.
             * @param componentTypeReference A lazy reference to the component type of this array.
             * @param value                  A list of all values of this annotation.
             */
            public RawNonPrimitiveArray(TypePool typePool,
                                        ComponentTypeReference componentTypeReference,
                                        List<AnnotationDescription.AnnotationValue<?, ?>> value) {
                this.typePool = typePool;
                this.value = value;
                this.componentTypeReference = componentTypeReference;
            }

            @Override
            public Object[] resolve() {
                TypeDescription componentTypeDescription = typePool.describe(componentTypeReference.lookup()).resolve();
                Class<?> componentType;
                if (componentTypeDescription.represents(Class.class)) {
                    componentType = TypeDescription.class;
                } else if (componentTypeDescription.isAssignableTo(Enum.class)) { // Enums can implement annotation interfaces, check this first.
                    componentType = EnumerationDescription.class;
                } else if (componentTypeDescription.isAssignableTo(Annotation.class)) {
                    componentType = AnnotationDescription.class;
                } else if (componentTypeDescription.represents(String.class)) {
                    componentType = String.class;
                } else {
                    throw new IllegalStateException("Unexpected complex array component type " + componentTypeDescription);
                }
                Object[] array = (Object[]) Array.newInstance(componentType, value.size());
                int index = 0;
                for (AnnotationDescription.AnnotationValue<?, ?> annotationValue : value) {
                    Array.set(array, index++, annotationValue.resolve());
                }
                return array;
            }

            @Override
            public AnnotationDescription.AnnotationValue.Loaded<Object[]> load(ClassLoader classLoader) throws ClassNotFoundException {
                List<AnnotationDescription.AnnotationValue.Loaded<?>> loadedValues = new ArrayList<AnnotationDescription.AnnotationValue.Loaded<?>>(value.size());
                for (AnnotationDescription.AnnotationValue<?, ?> value : this.value) {
                    loadedValues.add(value.load(classLoader));
                }
                return new Loaded(classLoader.loadClass(componentTypeReference.lookup()), loadedValues);
            }

            @Override
            public boolean equals(Object other) {
                return this == other || !(other == null || getClass() != other.getClass())
                        && componentTypeReference.equals(((RawNonPrimitiveArray) other).componentTypeReference)
                        && value.equals(((RawNonPrimitiveArray) other).value);
            }

            @Override
            public int hashCode() {
                return 31 * value.hashCode() + componentTypeReference.hashCode();
            }

            @Override
            public String toString() {
                return "TypePool.LazyTypeDescription.AnnotationValue.ForComplexArray{" +
                        "value=" + value +
                        ", componentTypeReference=" + componentTypeReference +
                        '}';
            }

            /**
             * A lazy representation of the component type of an array.
             */
            public interface ComponentTypeReference {

                /**
                 * Lazily returns the binary name of the array component type of an annotation value.
                 *
                 * @return The binary name of the component type.
                 */
                String lookup();
            }

            /**
             * Represents a loaded annotation property representing a complex array.
             */
            protected class Loaded implements AnnotationDescription.AnnotationValue.Loaded<Object[]> {

                /**
                 * The array's loaded component type.
                 */
                private final Class<?> componentType;

                /**
                 * A list of loaded values of the represented complex array.
                 */
                private final List<AnnotationDescription.AnnotationValue.Loaded<?>> values;

                /**
                 * Creates a new representation of an annotation property representing an array of
                 * non-trivial values.
                 *
                 * @param componentType The array's loaded component type.
                 * @param values        A list of loaded values of the represented complex array.
                 */
                public Loaded(Class<?> componentType, List<AnnotationDescription.AnnotationValue.Loaded<?>> values) {
                    this.componentType = componentType;
                    this.values = values;
                }

                @Override
                public State getState() {
                    for (AnnotationDescription.AnnotationValue.Loaded<?> value : values) {
                        if (!value.getState().isResolved()) {
                            return State.NON_RESOLVED;
                        }
                    }
                    return State.RESOLVED;
                }

                @Override
                public Object[] resolve() {
                    Object[] array = (Object[]) Array.newInstance(componentType, values.size());
                    int index = 0;
                    for (AnnotationDescription.AnnotationValue.Loaded<?> annotationValue : values) {
                        Array.set(array, index++, annotationValue.resolve());
                    }
                    return array;
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (!(other instanceof AnnotationDescription.AnnotationValue.Loaded<?>)) return false;
                    AnnotationDescription.AnnotationValue.Loaded<?> loadedOther = (AnnotationDescription.AnnotationValue.Loaded<?>) other;
                    if (!loadedOther.getState().isResolved()) return false;
                    Object otherValue = loadedOther.resolve();
                    if (!(otherValue instanceof Object[])) return false;
                    Object[] otherArrayValue = (Object[]) otherValue;
                    if (values.size() != otherArrayValue.length) return false;
                    Iterator<AnnotationDescription.AnnotationValue.Loaded<?>> iterator = values.iterator();
                    for (Object value : otherArrayValue) {
                        AnnotationDescription.AnnotationValue.Loaded<?> self = iterator.next();
                        if (!self.getState().isResolved() || !self.resolve().equals(value)) {
                            return false;
                        }
                    }
                    return true;
                }

                @Override
                public int hashCode() {
                    int result = 1;
                    for (AnnotationDescription.AnnotationValue.Loaded<?> value : values) {
                        result = 31 * result + value.hashCode();
                    }
                    return result;
                }

                @Override
                public String toString() {
                    StringBuilder stringBuilder = new StringBuilder("[");
                    for (AnnotationDescription.AnnotationValue.Loaded<?> value : values) {
                        stringBuilder.append(value.toString());
                    }
                    return stringBuilder.append("]").toString();
                }
            }
        }
    }

    /**
     * A default implementation of a {@link net.bytebuddy.pool.TypePool} that models binary data in the
     * Java byte code format into a {@link TypeDescription}. The data lookup
     * is delegated to a {@link net.bytebuddy.dynamic.ClassFileLocator}.
     */
    class Default extends AbstractBase {

        /**
         * Indicates that a visited method should be ignored.
         */
        private static final MethodVisitor IGNORE_METHOD = null;

        /**
         * The ASM version that is applied when reading class files.
         */
        private static final int ASM_API_VERSION = Opcodes.ASM5;

        /**
         * A flag to indicate ASM that no automatic calculations are requested.
         */
        private static final int ASM_MANUAL_FLAG = 0;

        /**
         * The locator to query for finding binary data of a type.
         */
        private final ClassFileLocator classFileLocator;

        /**
         * Creates a new default type pool.
         *
         * @param cacheProvider    The cache provider to be used.
         * @param classFileLocator The class file locator to be used.
         */
        public Default(CacheProvider cacheProvider, ClassFileLocator classFileLocator) {
            super(cacheProvider);
            this.classFileLocator = classFileLocator;
        }

        /**
         * Creates a default {@link net.bytebuddy.pool.TypePool} that looks up data by querying the system class
         * loader.
         *
         * @return A type pool that reads its data from the system class path.
         */
        public static TypePool ofClassPath() {
            return new Default(new CacheProvider.Simple(), ClassFileLocator.ForClassLoader.ofClassPath());
        }

        @Override
        protected Resolution doDescribe(String name) {
            try {
                ClassFileLocator.Resolution resolution = classFileLocator.locate(name);
                return resolution.isResolved()
                        ? new Resolution.Simple(parse(resolution.resolve()))
                        : new Resolution.Illegal(name);
            } catch (IOException e) {
                throw new IllegalStateException("Error while reading class file", e);
            }
        }

        /**
         * Parses a binary representation and transforms it into a type description.
         *
         * @param binaryRepresentation The binary data to be parsed.
         * @return A type description of the binary data.
         */
        private TypeDescription parse(byte[] binaryRepresentation) {
            ClassReader classReader = new ClassReader(binaryRepresentation);
            TypeExtractor typeExtractor = new TypeExtractor();
            classReader.accept(typeExtractor, ASM_MANUAL_FLAG);
            return typeExtractor.toTypeDescription();
        }

        @Override
        public boolean equals(Object other) {
            return this == other || !(other == null || getClass() != other.getClass())
                    && super.equals(other)
                    && classFileLocator.equals(((Default) other).classFileLocator);
        }

        @Override
        public int hashCode() {
            return 31 * super.hashCode() + classFileLocator.hashCode();
        }

        @Override
        public String toString() {
            return "TypePool.Default{" +
                    "classFileLocator=" + classFileLocator +
                    ", cacheProvider=" + cacheProvider +
                    '}';
        }

        /**
         * An annotation registrant implements a visitor pattern for reading an unknown amount of values of annotations.
         */
        protected interface AnnotationRegistrant {

            /**
             * Registers an annotation value.
             *
             * @param name            The name of the annotation value.
             * @param annotationValue The value of the annotation.
             */
            void register(String name, AnnotationDescription.AnnotationValue<?, ?> annotationValue);

            /**
             * Called once all annotation values are visited.
             */
            void onComplete();
        }

        /**
         * A component type locator allows for the lazy location of an array's component type.
         */
        protected interface ComponentTypeLocator {

            /**
             * Binds this component type to a given property name of an annotation.
             *
             * @param name The name of an annotation property which the returned component type reference should
             *             query for resolving an array's component type.
             * @return A component type reference to an annotation value's component type.
             */
            RawNonPrimitiveArray.ComponentTypeReference bind(String name);

            /**
             * A component type locator which cannot legally resolve an array's component type.
             */
            enum Illegal implements ComponentTypeLocator {

                /**
                 * The singleton instance.
                 */
                INSTANCE;

                @Override
                public RawNonPrimitiveArray.ComponentTypeReference bind(String name) {
                    throw new IllegalStateException("Unexpected lookup of component type for " + name);
                }

                @Override
                public String toString() {
                    return "TypePool.Default.ComponentTypeLocator.Illegal." + name();
                }
            }

            /**
             * A component type locator that lazily analyses an annotation for resolving an annotation property's
             * array value's component type.
             */
            class ForAnnotationProperty implements ComponentTypeLocator {

                /**
                 * The type pool to query for type descriptions.
                 */
                private final TypePool typePool;

                /**
                 * The name of the annotation to analyze.
                 */
                private final String annotationName;

                /**
                 * Creates a new component type locator for an array value.
                 *
                 * @param typePool             The type pool to be used for looking up linked types.
                 * @param annotationDescriptor A descriptor of the annotation to analyze.
                 */
                public ForAnnotationProperty(TypePool typePool, String annotationDescriptor) {
                    this.typePool = typePool;
                    annotationName = annotationDescriptor.substring(1, annotationDescriptor.length() - 1).replace('/', '.');
                }

                @Override
                public RawNonPrimitiveArray.ComponentTypeReference bind(String name) {
                    return new Bound(name);
                }

                @Override
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && annotationName.equals(((ForAnnotationProperty) other).annotationName)
                            && typePool.equals(((ForAnnotationProperty) other).typePool);
                }

                @Override
                public int hashCode() {
                    int result = typePool.hashCode();
                    result = 31 * result + annotationName.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "TypePool.Default.ComponentTypeLocator.ForAnnotationProperty{" +
                            "typePool=" + typePool +
                            ", annotationName='" + annotationName + '\'' +
                            '}';
                }

                /**
                 * A bound representation of a
                 * {@link net.bytebuddy.pool.TypePool.Default.ComponentTypeLocator.ForAnnotationProperty}.
                 */
                protected class Bound implements RawNonPrimitiveArray.ComponentTypeReference {

                    /**
                     * The name of the annotation property.
                     */
                    private final String name;

                    /**
                     * Creates a new bound component type locator for an annotation property.
                     *
                     * @param name The name of the annotation property.
                     */
                    protected Bound(String name) {
                        this.name = name;
                    }

                    @Override
                    public String lookup() {
                        return typePool.describe(annotationName)
                                .resolve()
                                .getDeclaredMethods()
                                .filter(named(name))
                                .getOnly()
                                .getReturnType()
                                .getComponentType()
                                .getName();
                    }

                    @Override
                    public boolean equals(Object other) {
                        return this == other || !(other == null || getClass() != other.getClass())
                                && name.equals(((Bound) other).name)
                                && ForAnnotationProperty.this.equals(((Bound) other).getOuter());
                    }

                    @Override
                    public int hashCode() {
                        return name.hashCode() + 31 * ForAnnotationProperty.this.hashCode();
                    }

                    /**
                     * Returns the outer instance.
                     *
                     * @return The outer instance.
                     */
                    private ForAnnotationProperty getOuter() {
                        return ForAnnotationProperty.this;
                    }

                    @Override
                    public String toString() {
                        return "TypePool.Default.ComponentTypeLocator.ForAnnotationProperty.Bound{" +
                                "name='" + name + '\'' +
                                '}';
                    }
                }
            }

            /**
             * A component type locator that locates an array type by a method's return value from its method descriptor.
             */
            class ForArrayType implements ComponentTypeLocator, RawNonPrimitiveArray.ComponentTypeReference {

                /**
                 * The resolved component type's binary name.
                 */
                private final String componentType;

                /**
                 * Creates a new component type locator for an array type.
                 *
                 * @param methodDescriptor The method descriptor to resolve.
                 */
                public ForArrayType(String methodDescriptor) {
                    String arrayType = Type.getMethodType(methodDescriptor).getReturnType().getClassName();
                    componentType = arrayType.substring(0, arrayType.length() - 2);
                }

                @Override
                public RawNonPrimitiveArray.ComponentTypeReference bind(String name) {
                    return this;
                }

                @Override
                public String lookup() {
                    return componentType;
                }

                @Override
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && componentType.equals(((ForArrayType) other).componentType);
                }

                @Override
                public int hashCode() {
                    return componentType.hashCode();
                }

                @Override
                public String toString() {
                    return "TypePool.Default.ComponentTypeLocator.ForArrayType{" +
                            "componentType='" + componentType + '\'' +
                            '}';
                }
            }
        }

        /**
         * A bag for collecting parameter meta information that is stored as debug information for implemented
         * methods.
         */
        protected static class ParameterBag {

            /**
             * An array of the method's parameter types.
             */
            private final Type[] parameterType;

            /**
             * A map containing the tokens that were collected until now.
             */
            private final Map<Integer, String> parameterRegistry;

            /**
             * Creates a new bag.
             *
             * @param parameterType An array of parameter types for the method on which this parameter bag
             *                      is used.
             */
            protected ParameterBag(Type[] parameterType) {
                this.parameterType = parameterType;
                parameterRegistry = new HashMap<Integer, String>(parameterType.length);
            }

            /**
             * Registers a new parameter.
             *
             * @param offset The offset of the registered entry on the local variable array of the method.
             * @param name   The name of the parameter.
             */
            protected void register(int offset, String name) {
                parameterRegistry.put(offset, name);
            }

            /**
             * Resolves the collected parameters as a list of parameter tokens.
             *
             * @param isStatic {@code true} if the analyzed method is static.
             * @return A list of parameter tokens based on the collected information.
             */
            protected List<LazyTypeDescription.MethodToken.ParameterToken> resolve(boolean isStatic) {
                List<LazyTypeDescription.MethodToken.ParameterToken> parameterTokens = new ArrayList<LazyTypeDescription.MethodToken.ParameterToken>(parameterType.length);
                int offset = isStatic
                        ? StackSize.ZERO.getSize()
                        : StackSize.SINGLE.getSize();
                for (Type aParameterType : parameterType) {
                    String name = this.parameterRegistry.get(offset);
                    parameterTokens.add(name == null
                            ? new LazyTypeDescription.MethodToken.ParameterToken()
                            : new LazyTypeDescription.MethodToken.ParameterToken(name));
                    offset += aParameterType.getSize();
                }
                return parameterTokens;
            }

            @Override
            public String toString() {
                return "TypePool.Default.ParameterBag{" +
                        "parameterType=" + Arrays.toString(parameterType) +
                        ", parameterRegistry=" + parameterRegistry +
                        '}';
            }
        }

        protected interface GenericTypeRegistrant {

            void register(LazyTypeDescription.GenericTypeToken token);

            class RejectingSignatureVisitor extends SignatureVisitor {

                private static final String MESSAGE = "Unexpected token in generic signature";

                public RejectingSignatureVisitor() {
                    super(ASM_API_VERSION);
                }

                @Override
                public void visitFormalTypeParameter(String name) {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitClassBound() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitInterfaceBound() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitSuperclass() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitInterface() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitParameterType() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitReturnType() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitExceptionType() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public void visitBaseType(char descriptor) {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public void visitTypeVariable(String name) {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitArrayType() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public void visitClassType(String name) {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public void visitInnerClassType(String name) {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public void visitTypeArgument() {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public SignatureVisitor visitTypeArgument(char wildcard) {
                    throw new IllegalStateException(MESSAGE);
                }

                @Override
                public void visitEnd() {
                    throw new IllegalStateException(MESSAGE);
                }
            }
        }

        protected static class GenericTypeExtractor extends GenericTypeRegistrant.RejectingSignatureVisitor implements GenericTypeRegistrant {

            private final GenericTypeRegistrant genericTypeRegistrant;

            private IncompleteToken incompleteToken;

            protected GenericTypeExtractor(GenericTypeRegistrant genericTypeRegistrant) {
                this.genericTypeRegistrant = genericTypeRegistrant;
            }

            @Override
            public void visitBaseType(char descriptor) {
                genericTypeRegistrant.register(LazyTypeDescription.GenericTypeToken.ForPrimitiveType.of(descriptor));
            }

            @Override
            public void visitTypeVariable(String name) {
                genericTypeRegistrant.register(new LazyTypeDescription.GenericTypeToken.ForTypeVariable(name));
            }

            @Override
            public SignatureVisitor visitArrayType() {
                return new GenericTypeExtractor(this);
            }

            @Override
            public void register(LazyTypeDescription.GenericTypeToken componentTypeToken) {
                genericTypeRegistrant.register(new LazyTypeDescription.GenericTypeToken.ForArray(componentTypeToken));
            }

            @Override
            public void visitClassType(String name) {
                incompleteToken = new IncompleteToken.ForTopLevelClass(name);
            }

            @Override
            public void visitInnerClassType(String name) {
                incompleteToken = new IncompleteToken.ForInnerClass(name, incompleteToken);
            }

            @Override
            public void visitTypeArgument() {
                incompleteToken.appendPlaceholder();
            }

            @Override
            public SignatureVisitor visitTypeArgument(char wildcard) {
                switch (wildcard) {
                    case SignatureVisitor.SUPER:
                        return incompleteToken.appendLowerBound();
                    case SignatureVisitor.EXTENDS:
                        return incompleteToken.appendUpperBound();
                    case SignatureVisitor.INSTANCEOF:
                        return incompleteToken.appendDirectBound();
                    default:
                        throw new IllegalArgumentException("Unknown wildcard: " + wildcard);
                }
            }

            @Override
            public void visitEnd() {
                genericTypeRegistrant.register(incompleteToken.toToken());
            }

            protected interface IncompleteToken {

                SignatureVisitor appendLowerBound();

                SignatureVisitor appendUpperBound();

                SignatureVisitor appendDirectBound();

                void appendPlaceholder();

                boolean isParameterized();

                String getName();

                LazyTypeDescription.GenericTypeToken toToken();

                abstract class AbstractBase implements IncompleteToken {

                    protected final List<LazyTypeDescription.GenericTypeToken> parameters;

                    public AbstractBase() {
                        parameters = new LinkedList<LazyTypeDescription.GenericTypeToken>();
                    }

                    @Override
                    public SignatureVisitor appendDirectBound() {
                        return new GenericTypeExtractor(new ForDirectBound());
                    }

                    @Override
                    public SignatureVisitor appendUpperBound() {
                        return new GenericTypeExtractor(new ForUpperBound());
                    }

                    @Override
                    public SignatureVisitor appendLowerBound() {
                        return new GenericTypeExtractor(new ForLowerBound());
                    }

                    @Override
                    public void appendPlaceholder() {
                        parameters.add(LazyTypeDescription.GenericTypeToken.ForUnboundWildcard.INSTANCE);
                    }

                    protected class ForDirectBound implements GenericTypeRegistrant {

                        @Override
                        public void register(LazyTypeDescription.GenericTypeToken token) {
                            parameters.add(token);
                        }
                    }

                    protected class ForUpperBound implements GenericTypeRegistrant {

                        @Override
                        public void register(LazyTypeDescription.GenericTypeToken token) {
                            parameters.add(new LazyTypeDescription.GenericTypeToken.ForUpperBoundWildcard(token));
                        }
                    }

                    protected class ForLowerBound implements GenericTypeRegistrant {

                        @Override
                        public void register(LazyTypeDescription.GenericTypeToken token) {
                            parameters.add(new LazyTypeDescription.GenericTypeToken.ForLowerBoundWildcard(token));
                        }
                    }
                }

                class ForTopLevelClass extends AbstractBase {

                    private final String internalName;

                    public ForTopLevelClass(String internalName) {
                        this.internalName = internalName;
                    }

                    @Override
                    public LazyTypeDescription.GenericTypeToken toToken() {
                        return isParameterized()
                                ? new LazyTypeDescription.GenericTypeToken.ForParameterizedType(getName(), parameters)
                                : new LazyTypeDescription.GenericTypeToken.ForRawType(getName());
                    }

                    @Override
                    public boolean isParameterized() {
                        return !parameters.isEmpty();
                    }

                    @Override
                    public String getName() {
                        return internalName.replace('/', '.');
                    }
                }

                class ForInnerClass extends AbstractBase {

                    private static final char INNER_CLASS_SEPERATOR = '$';

                    private final String internalName;

                    private final IncompleteToken outerClassToken;

                    public ForInnerClass(String internalName, IncompleteToken outerClassToken) {
                        this.internalName = internalName;
                        this.outerClassToken = outerClassToken;
                    }

                    @Override
                    public LazyTypeDescription.GenericTypeToken toToken() {
                        return isParameterized() || outerClassToken.isParameterized()
                                ? new LazyTypeDescription.GenericTypeToken.ForParameterizedType.Nested(getName(), parameters, outerClassToken.toToken())
                                : new LazyTypeDescription.GenericTypeToken.ForRawType(getName());
                    }

                    @Override
                    public boolean isParameterized() {
                        return !parameters.isEmpty() || !outerClassToken.isParameterized();
                    }

                    @Override
                    public String getName() {
                        return outerClassToken.getName() + INNER_CLASS_SEPERATOR + internalName.replace('/', '.');
                    }
                }
            }

            protected abstract static class ForSignature<T extends LazyTypeDescription.GenericTypeToken.Resolution>
                    extends RejectingSignatureVisitor
                    implements GenericTypeRegistrant {

                protected static <S extends LazyTypeDescription.GenericTypeToken.Resolution> S extract(String genericSignature, ForSignature<S> visitor) {
                    SignatureReader signatureReader = new SignatureReader(genericSignature);
                    signatureReader.accept(visitor);
                    return visitor.resolve();
                }

                protected final List<LazyTypeDescription.GenericTypeToken> typeVariableTokens;

                private String currentTypeParameter;

                private List<LazyTypeDescription.GenericTypeToken> currentBounds;

                public ForSignature() {
                    typeVariableTokens = new LinkedList<LazyTypeDescription.GenericTypeToken>();
                }

                @Override
                public void visitFormalTypeParameter(String name) {
                    collectTypeParameter();
                    currentTypeParameter = name;
                    currentBounds = new LinkedList<LazyTypeDescription.GenericTypeToken>();
                }

                @Override
                public SignatureVisitor visitClassBound() {
                    return new GenericTypeExtractor(this);
                }

                @Override
                public SignatureVisitor visitInterfaceBound() {
                    return new GenericTypeExtractor(this);
                }

                @Override
                public void register(LazyTypeDescription.GenericTypeToken token) {
                    currentBounds.add(token);
                }

                protected void collectTypeParameter() {
                    if (currentTypeParameter != null) {
                        typeVariableTokens.add(new LazyTypeDescription.GenericTypeToken.ForTypeVariable.Formal(currentTypeParameter, currentBounds));
                    }
                }

                public abstract T resolve();

                protected static class OfType extends ForSignature<LazyTypeDescription.GenericTypeToken.Resolution.ForType> {

                    public static LazyTypeDescription.GenericTypeToken.Resolution.ForType extract(String genericSignature) {
                        try {
                            return genericSignature == null
                                    ? LazyTypeDescription.GenericTypeToken.Resolution.Raw.INSTANCE
                                    : ForSignature.extract(genericSignature, new OfType());
                        } catch (RuntimeException ignored) {
                            return LazyTypeDescription.GenericTypeToken.Resolution.Defective.INSTANCE;
                        }
                    }

                    private LazyTypeDescription.GenericTypeToken superTypeToken;

                    private final List<LazyTypeDescription.GenericTypeToken> interfaceTypeTokens;

                    protected OfType() {
                        interfaceTypeTokens = new LinkedList<LazyTypeDescription.GenericTypeToken>();
                    }

                    @Override
                    public SignatureVisitor visitSuperclass() {
                        collectTypeParameter();
                        return new GenericTypeExtractor(new SuperTypeRegistrant());
                    }

                    @Override
                    public SignatureVisitor visitInterface() {
                        return new GenericTypeExtractor(new InterfaceTypeRegistrant());
                    }

                    @Override
                    public LazyTypeDescription.GenericTypeToken.Resolution.ForType resolve() {
                        return new LazyTypeDescription.GenericTypeToken.Resolution.ForType.Tokenized(superTypeToken, interfaceTypeTokens, typeVariableTokens);
                    }

                    protected class SuperTypeRegistrant implements GenericTypeRegistrant {

                        @Override
                        public void register(LazyTypeDescription.GenericTypeToken token) {
                            superTypeToken = token;
                        }
                    }

                    protected class InterfaceTypeRegistrant implements GenericTypeRegistrant {

                        @Override
                        public void register(LazyTypeDescription.GenericTypeToken token) {
                            interfaceTypeTokens.add(token);
                        }
                    }
                }

                protected static class OfMethod extends ForSignature<LazyTypeDescription.GenericTypeToken.Resolution.ForMethod> {

                    public static LazyTypeDescription.GenericTypeToken.Resolution.ForMethod extract(String genericSignature) {
                        try {
                            return genericSignature == null
                                    ? LazyTypeDescription.GenericTypeToken.Resolution.Raw.INSTANCE
                                    : ForSignature.extract(genericSignature, new OfMethod());
                        } catch (RuntimeException ignored) {
                            return LazyTypeDescription.GenericTypeToken.Resolution.Defective.INSTANCE;
                        }
                    }

                    private LazyTypeDescription.GenericTypeToken returnTypeToken;

                    private final List<LazyTypeDescription.GenericTypeToken> parameterTypeTokens;

                    private final List<LazyTypeDescription.GenericTypeToken> exceptionTypeTokens;

                    public OfMethod() {
                        parameterTypeTokens = new LinkedList<LazyTypeDescription.GenericTypeToken>();
                        exceptionTypeTokens = new LinkedList<LazyTypeDescription.GenericTypeToken>();
                    }

                    @Override
                    public SignatureVisitor visitParameterType() {
                        return new GenericTypeExtractor(new ParameterTypeRegistrant());
                    }

                    @Override
                    public SignatureVisitor visitReturnType() {
                        collectTypeParameter();
                        return new GenericTypeExtractor(new ReturnTypeTypeRegistrant());
                    }

                    @Override
                    public SignatureVisitor visitExceptionType() {
                        return new GenericTypeExtractor(new InterfaceTypeRegistrant());
                    }

                    @Override
                    public LazyTypeDescription.GenericTypeToken.Resolution.ForMethod resolve() {
                        return new LazyTypeDescription.GenericTypeToken.Resolution.ForMethod.Tokenized(returnTypeToken,
                                parameterTypeTokens,
                                exceptionTypeTokens,
                                typeVariableTokens);
                    }

                    protected class ParameterTypeRegistrant implements GenericTypeRegistrant {

                        @Override
                        public void register(LazyTypeDescription.GenericTypeToken token) {
                            parameterTypeTokens.add(token);
                        }
                    }

                    protected class ReturnTypeTypeRegistrant implements GenericTypeRegistrant {

                        @Override
                        public void register(LazyTypeDescription.GenericTypeToken token) {
                            returnTypeToken = token;
                        }
                    }

                    protected class InterfaceTypeRegistrant implements GenericTypeRegistrant {

                        @Override
                        public void register(LazyTypeDescription.GenericTypeToken token) {
                            exceptionTypeTokens.add(token);
                        }
                    }
                }

                protected static class OfField implements GenericTypeRegistrant {

                    public static LazyTypeDescription.GenericTypeToken.Resolution.ForField extract(String genericSignature) {
                        if (genericSignature == null) {
                            return LazyTypeDescription.GenericTypeToken.Resolution.Raw.INSTANCE;
                        } else {
                            SignatureReader signatureReader = new SignatureReader(genericSignature);
                            OfField visitor = new OfField();
                            try {
                                signatureReader.acceptType(new GenericTypeExtractor(visitor));
                                return visitor.resolve();
                            } catch (RuntimeException ignored) {
                                return LazyTypeDescription.GenericTypeToken.Resolution.Defective.INSTANCE;
                            }
                        }
                    }

                    private LazyTypeDescription.GenericTypeToken fieldTypeToken;

                    @Override
                    public void register(LazyTypeDescription.GenericTypeToken token) {
                        fieldTypeToken = token;
                    }

                    protected LazyTypeDescription.GenericTypeToken.Resolution.ForField resolve() {
                        return new LazyTypeDescription.GenericTypeToken.Resolution.ForField.Tokenized(fieldTypeToken);
                    }
                }
            }
        }

        /**
         * A type extractor reads a class file and collects data that is relevant to create a type description.
         */
        protected class TypeExtractor extends ClassVisitor {

            /**
             * A list of annotation tokens describing annotations that are found on the visited type.
             */
            private final List<LazyTypeDescription.AnnotationToken> annotationTokens;

            /**
             * A list of field tokens describing fields that are found on the visited type.
             */
            private final List<LazyTypeDescription.FieldToken> fieldTokens;

            /**
             * A list of method tokens describing annotations that are found on the visited type.
             */
            private final List<LazyTypeDescription.MethodToken> methodTokens;

            /**
             * The modifiers found for this type.
             */
            private int modifiers;

            /**
             * The internal name found for this type.
             */
            private String internalName;

            /**
             * The internal name of the super type found for this type or {@code null} if no such type exists.
             */
            private String superTypeName;

            /**
             * The generic signature of the type or {@code null} if it is not generic.
             */
            private String genericSignature;

            /**
             * A list of internal names of interfaces implemented by this type or {@code null} if no interfaces
             * are implemented.
             */
            private String[] interfaceName;

            /**
             * {@code true} if this type was found to represent an anonymous type.
             */
            private boolean anonymousType;

            /**
             * The declaration context found for this type.
             */
            private LazyTypeDescription.DeclarationContext declarationContext;

            /**
             * Creates a new type extractor.
             */
            protected TypeExtractor() {
                super(ASM_API_VERSION);
                annotationTokens = new LinkedList<LazyTypeDescription.AnnotationToken>();
                fieldTokens = new LinkedList<LazyTypeDescription.FieldToken>();
                methodTokens = new LinkedList<LazyTypeDescription.MethodToken>();
                anonymousType = false;
                declarationContext = LazyTypeDescription.DeclarationContext.SelfDeclared.INSTANCE;
            }

            @Override
            public void visit(int classFileVersion,
                              int modifiers,
                              String internalName,
                              String genericSignature,
                              String superTypeName,
                              String[] interfaceName) {
                this.modifiers = modifiers;
                this.internalName = internalName;
                this.genericSignature = genericSignature;
                this.superTypeName = superTypeName;
                this.interfaceName = interfaceName;
            }

            @Override
            public void visitOuterClass(String typeName, String methodName, String methodDescriptor) {
                if (methodName != null) {
                    declarationContext = new LazyTypeDescription.DeclarationContext.DeclaredInMethod(typeName,
                            methodName,
                            methodDescriptor);
                } else if (typeName != null) {
                    declarationContext = new LazyTypeDescription.DeclarationContext.DeclaredInType(typeName);
                }
            }

            @Override
            public void visitInnerClass(String internalName, String outerName, String innerName, int modifiers) {
                if (internalName.equals(this.internalName)) {
                    this.modifiers = modifiers;
                    if (innerName == null) {
                        anonymousType = true;
                    }
                    if (declarationContext.isSelfDeclared()) {
                        declarationContext = new LazyTypeDescription.DeclarationContext.DeclaredInType(outerName);
                    }
                }
            }

            @Override
            public AnnotationVisitor visitAnnotation(String descriptor, boolean visible) {
                return new AnnotationExtractor(new OnTypeCollector(descriptor),
                        new ComponentTypeLocator.ForAnnotationProperty(Default.this, descriptor));
            }

            @Override
            public FieldVisitor visitField(int modifiers,
                                           String internalName,
                                           String descriptor,
                                           String genericSignature,
                                           Object defaultValue) {
                return new FieldExtractor(modifiers, internalName, descriptor, genericSignature);
            }

            @Override
            public MethodVisitor visitMethod(int modifiers,
                                             String internalName,
                                             String descriptor,
                                             String genericSignature,
                                             String[] exceptionName) {
                return internalName.equals(MethodDescription.TYPE_INITIALIZER_INTERNAL_NAME)
                        ? IGNORE_METHOD
                        : new MethodExtractor(modifiers, internalName, descriptor, genericSignature, exceptionName);
            }

            /**
             * Creates a type description from all data that is currently collected. This method should only be invoked
             * after a class file was parsed fully.
             *
             * @return A type description reflecting the data that was collected by this instance.
             */
            protected TypeDescription toTypeDescription() {
                return new LazyTypeDescription(Default.this,
                        modifiers,
                        internalName,
                        superTypeName,
                        interfaceName,
                        GenericTypeExtractor.ForSignature.OfType.extract(genericSignature),
                        declarationContext,
                        anonymousType,
                        annotationTokens,
                        fieldTokens,
                        methodTokens);
            }

            @Override
            public String toString() {
                return "TypePool.Default.TypeExtractor{" +
                        "typePool=" + Default.this +
                        ", annotationTokens=" + annotationTokens +
                        ", fieldTokens=" + fieldTokens +
                        ", methodTokens=" + methodTokens +
                        ", modifiers=" + modifiers +
                        ", internalName='" + internalName + '\'' +
                        ", superTypeName='" + superTypeName + '\'' +
                        ", genericSignature='" + genericSignature + '\'' +
                        ", interfaceName=" + Arrays.toString(interfaceName) +
                        ", anonymousType=" + anonymousType +
                        ", declarationContext=" + declarationContext +
                        '}';
            }

            /**
             * An annotation registrant that collects annotations found on a type.
             */
            protected class OnTypeCollector implements AnnotationRegistrant {

                /**
                 * The descriptor of the annotation that is being collected.
                 */
                private final String descriptor;

                /**
                 * The values that were collected so far.
                 */
                private final Map<String, AnnotationDescription.AnnotationValue<?, ?>> values;

                /**
                 * Creates a new on type collector.
                 *
                 * @param descriptor The descriptor of the annotation that is being collected.
                 */
                protected OnTypeCollector(String descriptor) {
                    this.descriptor = descriptor;
                    values = new HashMap<String, AnnotationDescription.AnnotationValue<?, ?>>();
                }

                @Override
                public void register(String name, AnnotationDescription.AnnotationValue<?, ?> annotationValue) {
                    values.put(name, annotationValue);
                }

                @Override
                public void onComplete() {
                    annotationTokens.add(new LazyTypeDescription.AnnotationToken(descriptor, values));
                }

                @Override
                public String toString() {
                    return "TypePool.Default.TypeExtractor.OnTypeCollector{" +
                            "typeExtractor=" + TypeExtractor.this +
                            ", descriptor='" + descriptor + '\'' +
                            ", values=" + values +
                            '}';
                }
            }

            /**
             * An annotation extractor reads an annotation found in a class field an collects data that
             * is relevant to creating a related annotation description.
             */
            protected class AnnotationExtractor extends AnnotationVisitor {

                /**
                 * The annotation registrant to register found annotation values on.
                 */
                private final AnnotationRegistrant annotationRegistrant;

                /**
                 * A locator for the component type of any found annotation value.
                 */
                private final ComponentTypeLocator componentTypeLocator;

                /**
                 * Creates a new annotation extractor.
                 *
                 * @param annotationRegistrant The annotation registrant to register found annotation values on.
                 * @param componentTypeLocator A locator for the component type of any found annotation value.
                 */
                protected AnnotationExtractor(AnnotationRegistrant annotationRegistrant,
                                              ComponentTypeLocator componentTypeLocator) {
                    super(ASM_API_VERSION);
                    this.annotationRegistrant = annotationRegistrant;
                    this.componentTypeLocator = componentTypeLocator;
                }

                @Override
                public void visit(String name, Object value) {
                    AnnotationDescription.AnnotationValue<?, ?> annotationValue;
                    if (value instanceof Type) {
                        annotationValue = new RawTypeValue(Default.this, (Type) value);
                    } else if (value.getClass().isArray()) {
                        annotationValue = new AnnotationDescription.AnnotationValue.Trivial<Object>(value);
                    } else {
                        annotationValue = new AnnotationDescription.AnnotationValue.Trivial<Object>(value);
                    }
                    annotationRegistrant.register(name, annotationValue);
                }

                @Override
                public void visitEnum(String name, String descriptor, String value) {
                    annotationRegistrant.register(name, new RawEnumerationValue(Default.this, descriptor, value));
                }

                @Override
                public AnnotationVisitor visitAnnotation(String name, String descriptor) {
                    return new AnnotationExtractor(new AnnotationLookup(name, descriptor),
                            new ComponentTypeLocator.ForAnnotationProperty(TypePool.Default.this, descriptor));
                }

                @Override
                public AnnotationVisitor visitArray(String name) {
                    return new AnnotationExtractor(new ArrayLookup(name, componentTypeLocator.bind(name)), ComponentTypeLocator.Illegal.INSTANCE);
                }

                @Override
                public void visitEnd() {
                    annotationRegistrant.onComplete();
                }

                @Override
                public String toString() {
                    return "TypePool.Default.TypeExtractor.AnnotationExtractor{" +
                            "typeExtractor=" + TypeExtractor.this +
                            "annotationRegistrant=" + annotationRegistrant +
                            ", componentTypeLocator=" + componentTypeLocator +
                            '}';
                }

                /**
                 * An annotation registrant for registering values of an array.
                 */
                protected class ArrayLookup implements AnnotationRegistrant {

                    /**
                     * The name of the annotation property the collected array is representing.
                     */
                    private final String name;

                    /**
                     * A lazy reference to resolve the component type of the collected array.
                     */
                    private final RawNonPrimitiveArray.ComponentTypeReference componentTypeReference;

                    /**
                     * A list of all annotation values that are found on this array.
                     */
                    private final List<AnnotationDescription.AnnotationValue<?, ?>> values;

                    /**
                     * Creates a new annotation registrant for an array lookup.
                     *
                     * @param name                   The name of the annotation property the collected array is representing.
                     * @param componentTypeReference A lazy reference to resolve the component type of the collected array.
                     */
                    protected ArrayLookup(String name,
                                          RawNonPrimitiveArray.ComponentTypeReference componentTypeReference) {
                        this.name = name;
                        this.componentTypeReference = componentTypeReference;
                        values = new LinkedList<AnnotationDescription.AnnotationValue<?, ?>>();
                    }

                    @Override
                    public void register(String ignored, AnnotationDescription.AnnotationValue<?, ?> annotationValue) {
                        values.add(annotationValue);
                    }

                    @Override
                    public void onComplete() {
                        annotationRegistrant.register(name, new RawNonPrimitiveArray(Default.this, componentTypeReference, values));
                    }

                    @Override
                    public String toString() {
                        return "TypePool.Default.TypeExtractor.AnnotationExtractor.ArrayLookup{" +
                                "annotationExtractor=" + AnnotationExtractor.this +
                                ", name='" + name + '\'' +
                                ", componentTypeReference=" + componentTypeReference +
                                ", values=" + values +
                                '}';
                    }
                }

                /**
                 * An annotation registrant for registering the values on an array that is itself an annotation property.
                 */
                protected class AnnotationLookup implements AnnotationRegistrant {

                    /**
                     * The name of the original annotation for which the annotation values are looked up.
                     */
                    private final String name;

                    /**
                     * The descriptor of the original annotation for which the annotation values are looked up.
                     */
                    private final String descriptor;

                    /**
                     * A mapping of annotation property values to their values.
                     */
                    private final Map<String, AnnotationDescription.AnnotationValue<?, ?>> values;

                    /**
                     * Creates a new annotation registrant for a recursive annotation lookup.
                     *
                     * @param name       The name of the original annotation for which the annotation values are
                     *                   looked up.
                     * @param descriptor The descriptor of the original annotation for which the annotation values are
                     *                   looked up.
                     */
                    protected AnnotationLookup(String name, String descriptor) {
                        this.name = name;
                        this.descriptor = descriptor;
                        values = new HashMap<String, AnnotationDescription.AnnotationValue<?, ?>>();
                    }

                    @Override
                    public void register(String name, AnnotationDescription.AnnotationValue<?, ?> annotationValue) {
                        values.put(name, annotationValue);
                    }

                    @Override
                    public void onComplete() {
                        annotationRegistrant.register(name, new RawAnnotationValue(Default.this, new LazyTypeDescription.AnnotationToken(descriptor, values)));
                    }

                    @Override
                    public String toString() {
                        return "TypePool.Default.TypeExtractor.AnnotationExtractor.AnnotationLookup{" +
                                "annotationExtractor=" + AnnotationExtractor.this +
                                ", name='" + name + '\'' +
                                ", descriptor='" + descriptor + '\'' +
                                ", values=" + values +
                                '}';
                    }
                }
            }

            /**
             * A field extractor reads a field within a class file and collects data that is relevant
             * to creating a related field description.
             */
            protected class FieldExtractor extends FieldVisitor {

                /**
                 * The modifiers found on the field.
                 */
                private final int modifiers;

                /**
                 * The name of the field.
                 */
                private final String internalName;

                /**
                 * The descriptor of the field type.
                 */

                /**
                 * The generic signature of the field or {@code null} if it is not generic.
                 */
                private final String descriptor;

                /**
                 * The generic signature of the field or {@code null} if it is not generic.
                 */
                private final String genericSignature;

                /**
                 * A list of annotation tokens found for this field.
                 */
                private final List<LazyTypeDescription.AnnotationToken> annotationTokens;

                /**
                 * Creates a new field extractor.
                 *
                 * @param modifiers        The modifiers found for this field.
                 * @param internalName     The name of the field.
                 * @param descriptor       The descriptor of the field type.
                 * @param genericSignature The generic signature of the field or {@code null} if it is not generic.
                 */
                protected FieldExtractor(int modifiers,
                                         String internalName,
                                         String descriptor,
                                         String genericSignature) {
                    super(ASM_API_VERSION);
                    this.modifiers = modifiers;
                    this.internalName = internalName;
                    this.descriptor = descriptor;
                    this.genericSignature = genericSignature;
                    annotationTokens = new LinkedList<LazyTypeDescription.AnnotationToken>();
                }

                @Override
                public AnnotationVisitor visitAnnotation(String descriptor, boolean visible) {
                    return new AnnotationExtractor(new OnFieldCollector(descriptor),
                            new ComponentTypeLocator.ForAnnotationProperty(Default.this, descriptor));
                }

                @Override
                public void visitEnd() {
                    fieldTokens.add(new LazyTypeDescription.FieldToken(modifiers,
                            internalName,
                            descriptor,
                            GenericTypeExtractor.ForSignature.OfField.extract(genericSignature),
                            annotationTokens));
                }

                @Override
                public String toString() {
                    return "TypePool.Default.TypeExtractor.FieldExtractor{" +
                            "typeExtractor=" + TypeExtractor.this +
                            ", modifiers=" + modifiers +
                            ", internalName='" + internalName + '\'' +
                            ", descriptor='" + descriptor + '\'' +
                            ", genericSignature='" + genericSignature + '\'' +
                            ", annotationTokens=" + annotationTokens +
                            '}';
                }

                /**
                 * An annotation registrant that collects annotations that are declared on a field.
                 */
                protected class OnFieldCollector implements AnnotationRegistrant {

                    /**
                     * The annotation descriptor.
                     */
                    private final String descriptor;

                    /**
                     * A mapping of annotation property names to their values.
                     */
                    private final Map<String, AnnotationDescription.AnnotationValue<?, ?>> values;

                    /**
                     * Creates a new annotation field registrant.
                     *
                     * @param descriptor The descriptor of the annotation.
                     */
                    protected OnFieldCollector(String descriptor) {
                        this.descriptor = descriptor;
                        values = new HashMap<String, AnnotationDescription.AnnotationValue<?, ?>>();
                    }

                    @Override
                    public void register(String name, AnnotationDescription.AnnotationValue<?, ?> annotationValue) {
                        values.put(name, annotationValue);
                    }

                    @Override
                    public void onComplete() {
                        annotationTokens.add(new LazyTypeDescription.AnnotationToken(descriptor, values));
                    }

                    @Override
                    public String toString() {
                        return "TypePool.Default.TypeExtractor.FieldExtractor.OnFieldCollector{" +
                                "fieldExtractor=" + FieldExtractor.this +
                                ", descriptor='" + descriptor + '\'' +
                                ", values=" + values +
                                '}';
                    }
                }
            }

            /**
             * A method extractor reads a method within a class file and collects data that is relevant
             * to creating a related method description.
             */
            protected class MethodExtractor extends MethodVisitor implements AnnotationRegistrant {

                /**
                 * The modifiers found for this method.
                 */
                private final int modifiers;

                /**
                 * The internal name found for this method.
                 */
                private final String internalName;

                /**
                 * The descriptor found for this method.
                 */
                private final String descriptor;

                /**
                 * The generic signature of the method or {@code null} if it is not generic.
                 */
                private final String genericSignature;

                /**
                 * An array of internal names of the exceptions of the found method
                 * or {@code null} if there are no such exceptions.
                 */
                private final String[] exceptionName;

                /**
                 * A list of annotation tokens declared on the found method.
                 */
                private final List<LazyTypeDescription.AnnotationToken> annotationTokens;

                /**
                 * A mapping of parameter indices to annotation tokens found for the parameters at these indices.
                 */
                private final Map<Integer, List<LazyTypeDescription.AnnotationToken>> parameterAnnotationTokens;

                /**
                 * A list of tokens representing meta information of a parameter as it is available for method's
                 * that are compiled in the Java 8 version format.
                 */
                private final List<LazyTypeDescription.MethodToken.ParameterToken> parameterTokens;

                /**
                 * A bag of parameter meta information representing debugging information which allows to extract
                 * a method's parameter names.
                 */
                private final ParameterBag legacyParameterBag;

                /**
                 * The first label that is found in the method's body, if any, denoting the start of the method.
                 * This label can be used to identify names of local variables that describe the method's parameters.
                 */
                private Label firstLabel;

                /**
                 * The default value of the found method or {@code null} if no such value exists.
                 */
                private AnnotationDescription.AnnotationValue<?, ?> defaultValue;

                /**
                 * Creates a method extractor.
                 *
                 * @param modifiers        The modifiers found for this method.
                 * @param internalName     The internal name found for this method.
                 * @param descriptor       The descriptor found for this method.
                 * @param genericSignature The generic signature of the method or {@code null} if it is not generic.
                 * @param exceptionName    An array of internal names of the exceptions of the found method
                 *                         or {@code null} if there are no such exceptions.
                 */
                protected MethodExtractor(int modifiers,
                                          String internalName,
                                          String descriptor,
                                          String genericSignature,
                                          String[] exceptionName) {
                    super(ASM_API_VERSION);
                    this.modifiers = modifiers;
                    this.internalName = internalName;
                    this.descriptor = descriptor;
                    this.genericSignature = genericSignature;
                    this.exceptionName = exceptionName;
                    annotationTokens = new LinkedList<LazyTypeDescription.AnnotationToken>();
                    Type[] parameterTypes = Type.getMethodType(descriptor).getArgumentTypes();
                    parameterAnnotationTokens = new HashMap<Integer, List<LazyTypeDescription.AnnotationToken>>(parameterTypes.length);
                    for (int i = 0; i < parameterTypes.length; i++) {
                        parameterAnnotationTokens.put(i, new LinkedList<LazyTypeDescription.AnnotationToken>());
                    }
                    parameterTokens = new ArrayList<LazyTypeDescription.MethodToken.ParameterToken>(parameterTypes.length);
                    legacyParameterBag = new ParameterBag(parameterTypes);
                }

                @Override
                public AnnotationVisitor visitAnnotation(String descriptor, boolean visible) {
                    return new AnnotationExtractor(new OnMethodCollector(descriptor),
                            new ComponentTypeLocator.ForAnnotationProperty(Default.this, descriptor));
                }

                @Override
                public AnnotationVisitor visitParameterAnnotation(int index, String descriptor, boolean visible) {
                    return new AnnotationExtractor(new OnMethodParameterCollector(descriptor, index),
                            new ComponentTypeLocator.ForAnnotationProperty(Default.this, descriptor));
                }

                @Override
                public void visitLabel(Label label) {
                    if (firstLabel == null) {
                        firstLabel = label;
                    }
                }

                @Override
                public void visitLocalVariable(String name, String descriptor, String signature, Label start, Label end, int index) {
                    if (start == firstLabel) {
                        legacyParameterBag.register(index, name);
                    }
                }

                @Override
                public void visitParameter(String name, int modifiers) {
                    parameterTokens.add(new LazyTypeDescription.MethodToken.ParameterToken(name, modifiers));
                }

                @Override
                public AnnotationVisitor visitAnnotationDefault() {
                    return new AnnotationExtractor(this, new ComponentTypeLocator.ForArrayType(descriptor));
                }

                @Override
                public void register(String ignored, AnnotationDescription.AnnotationValue<?, ?> annotationValue) {
                    defaultValue = annotationValue;
                }

                @Override
                public void onComplete() {
                    /* do nothing, as the register method is called at most once for default values */
                }

                @Override
                public void visitEnd() {
                    methodTokens.add(new LazyTypeDescription.MethodToken(modifiers,
                            internalName,
                            descriptor,
                            GenericTypeExtractor.ForSignature.OfMethod.extract(genericSignature),
                            exceptionName,
                            annotationTokens,
                            parameterAnnotationTokens,
                            parameterTokens.isEmpty()
                                    ? legacyParameterBag.resolve((modifiers & Opcodes.ACC_STATIC) != 0)
                                    : parameterTokens,
                            defaultValue));
                }

                @Override
                public String toString() {
                    return "TypePool.Default.TypeExtractor.MethodExtractor{" +
                            "typeExtractor=" + TypeExtractor.this +
                            ", modifiers=" + modifiers +
                            ", internalName='" + internalName + '\'' +
                            ", descriptor='" + descriptor + '\'' +
                            ", genericSignature='" + genericSignature + '\'' +
                            ", exceptionName=" + Arrays.toString(exceptionName) +
                            ", annotationTokens=" + annotationTokens +
                            ", parameterAnnotationTokens=" + parameterAnnotationTokens +
                            ", parameterTokens=" + parameterTokens +
                            ", legacyParameterBag=" + legacyParameterBag +
                            ", firstLabel=" + firstLabel +
                            ", defaultValue=" + defaultValue +
                            '}';
                }

                /**
                 * An annotation registrant for annotations found on the method itself.
                 */
                protected class OnMethodCollector implements AnnotationRegistrant {

                    /**
                     * The descriptor of the annotation.
                     */
                    private final String descriptor;

                    /**
                     * A mapping of annotation properties to their values.
                     */
                    private final Map<String, AnnotationDescription.AnnotationValue<?, ?>> values;

                    /**
                     * Creates a new method annotation registrant.
                     *
                     * @param descriptor The descriptor of the annotation.
                     */
                    protected OnMethodCollector(String descriptor) {
                        this.descriptor = descriptor;
                        values = new HashMap<String, AnnotationDescription.AnnotationValue<?, ?>>();
                    }

                    @Override
                    public void register(String name, AnnotationDescription.AnnotationValue<?, ?> annotationValue) {
                        values.put(name, annotationValue);
                    }

                    @Override
                    public void onComplete() {
                        annotationTokens.add(new LazyTypeDescription.AnnotationToken(descriptor, values));
                    }

                    @Override
                    public String toString() {
                        return "TypePool.Default.TypeExtractor.MethodExtractor.OnMethodCollector{" +
                                "methodExtractor=" + MethodExtractor.this +
                                ", descriptor='" + descriptor + '\'' +
                                ", values=" + values +
                                '}';
                    }
                }

                /**
                 * An annotation registrant that collects annotations that are found on a specific parameter.
                 */
                protected class OnMethodParameterCollector implements AnnotationRegistrant {

                    /**
                     * The descriptor of the annotation.
                     */
                    private final String descriptor;

                    /**
                     * The index of the parameter of this annotation.
                     */
                    private final int index;

                    /**
                     * A mapping of annotation properties to their values.
                     */
                    private final Map<String, AnnotationDescription.AnnotationValue<?, ?>> values;

                    /**
                     * Creates a new method parameter annotation registrant.
                     *
                     * @param descriptor The descriptor of the annotation.
                     * @param index      The index of the parameter of this annotation.
                     */
                    protected OnMethodParameterCollector(String descriptor, int index) {
                        this.descriptor = descriptor;
                        this.index = index;
                        values = new HashMap<String, AnnotationDescription.AnnotationValue<?, ?>>();
                    }

                    @Override
                    public void register(String name, AnnotationDescription.AnnotationValue<?, ?> annotationValue) {
                        values.put(name, annotationValue);
                    }

                    @Override
                    public void onComplete() {
                        parameterAnnotationTokens.get(index).add(new LazyTypeDescription.AnnotationToken(descriptor, values));
                    }

                    @Override
                    public String toString() {
                        return "TypePool.Default.TypeExtractor.MethodExtractor.OnMethodParameterCollector{" +
                                "methodExtractor=" + MethodExtractor.this +
                                ", descriptor='" + descriptor + '\'' +
                                ", index=" + index +
                                ", values=" + values +
                                '}';
                    }
                }
            }
        }
    }

    /**
     * A type description that looks up any referenced {@link net.bytebuddy.description.ByteCodeElement} or
     * {@link AnnotationDescription} by querying a type pool at lookup time.
     */
    class LazyTypeDescription extends TypeDescription.AbstractTypeDescription.OfSimpleType {

        /**
         * The type pool to be used for looking up linked types.
         */
        private final TypePool typePool;

        /**
         * The modifiers of this type.
         */
        private final int modifiers;

        /**
         * The binary name of this type.
         */
        private final String name;

        private final String superTypeDescriptor;

        private final GenericTypeToken.Resolution.ForType signatureResolution;

        private final List<String> interfaceTypeDescriptors;

        /**
         * The declaration context of this type.
         */
        private final DeclarationContext declarationContext;

        /**
         * {@code true} if this type is an anonymous type.
         */
        private final boolean anonymousType;

        /**
         * A list of annotation descriptions that are declared by this type.
         */
        private final List<AnnotationDescription> declaredAnnotations;

        /**
         * A list of field descriptions that are declared by this type.
         */
        private final List<FieldDescription> declaredFields;

        /**
         * A list of method descriptions that are declared by this type.
         */
        private final List<MethodDescription> declaredMethods;

        protected LazyTypeDescription(TypePool typePool,
                                      int modifiers,
                                      String name,
                                      String superTypeInternalName,
                                      String[] interfaceInternalName,
                                      GenericTypeToken.Resolution.ForType signatureResolution,
                                      DeclarationContext declarationContext,
                                      boolean anonymousType,
                                      List<AnnotationToken> annotationTokens,
                                      List<FieldToken> fieldTokens,
                                      List<MethodToken> methodTokens) {
            this.typePool = typePool;
            this.modifiers = modifiers;
            this.name = Type.getObjectType(name).getClassName();
            this.superTypeDescriptor = superTypeInternalName == null
                    ? null
                    : Type.getObjectType(superTypeInternalName).getDescriptor();
            this.signatureResolution = signatureResolution;
            if (interfaceInternalName == null) {
                interfaceTypeDescriptors = Collections.<String>emptyList();
            } else {
                interfaceTypeDescriptors = new ArrayList<String>(interfaceInternalName.length);
                for (String internalName : interfaceInternalName) {
                    interfaceTypeDescriptors.add(Type.getObjectType(internalName).getDescriptor());
                }
            }
            this.declarationContext = declarationContext;
            this.anonymousType = anonymousType;
            declaredAnnotations = new ArrayList<AnnotationDescription>(annotationTokens.size());
            for (AnnotationToken annotationToken : annotationTokens) {
                declaredAnnotations.add(annotationToken.toAnnotationDescription(typePool));
            }
            declaredFields = new ArrayList<FieldDescription>(fieldTokens.size());
            for (FieldToken fieldToken : fieldTokens) {
                declaredFields.add(fieldToken.toFieldDescription(this));
            }
            declaredMethods = new ArrayList<MethodDescription>(methodTokens.size());
            for (MethodToken methodToken : methodTokens) {
                declaredMethods.add(methodToken.toMethodDescription(this));
            }
        }

        @Override
        public GenericTypeDescription getSuperTypeGen() {
            return superTypeDescriptor == null || isInterface()
                    ? null
                    : signatureResolution.resolveSuperType(superTypeDescriptor, typePool, this);
        }

        @Override
        public GenericTypeList getInterfacesGen() {
            return signatureResolution.resolveInterfaceTypes(interfaceTypeDescriptors, typePool, this);
        }

        @Override
        public MethodDescription getEnclosingMethod() {
            return declarationContext.getEnclosingMethod(typePool);
        }

        @Override
        public TypeDescription getEnclosingType() {
            return declarationContext.getEnclosingType(typePool);
        }

        @Override
        public boolean isAnonymousClass() {
            return anonymousType;
        }

        @Override
        public boolean isLocalClass() {
            return !anonymousType && declarationContext.isDeclaredInMethod();
        }

        @Override
        public boolean isMemberClass() {
            return declarationContext.isDeclaredInType();
        }

        @Override
        public FieldList getDeclaredFields() {
            return new FieldList.Explicit(declaredFields);
        }

        @Override
        public MethodList getDeclaredMethods() {
            return new MethodList.Explicit(declaredMethods);
        }

        @Override
        public PackageDescription getPackage() {
            String packageName = getPackageName();
            return packageName == null
                    ? null
                    : new LazyPackageDescription(typePool, packageName);
        }

        @Override
        public String getName() {
            return name;
        }

        @Override
        public TypeDescription getDeclaringType() {
            return declarationContext.isDeclaredInType()
                    ? declarationContext.getEnclosingType(typePool)
                    : null;
        }

        @Override
        public int getModifiers() {
            return modifiers;
        }

        @Override
        public AnnotationList getDeclaredAnnotations() {
            return new AnnotationList.Explicit(declaredAnnotations);
        }

        @Override
        public GenericTypeList getTypeVariables() {
            return signatureResolution.resolveTypeVariables(typePool, this);
        }

        /**
         * A declaration context encapsulates information about whether a type was declared within another type
         * or within a method of another type.
         */
        protected interface DeclarationContext {

            /**
             * Returns the enclosing method or {@code null} if no such method exists.
             *
             * @param typePool The type pool to be used for looking up linked types.
             * @return A method description describing the linked type or {@code null}.
             */
            MethodDescription getEnclosingMethod(TypePool typePool);

            /**
             * Returns the enclosing type or {@code null} if no such type exists.
             *
             * @param typePool The type pool to be used for looking up linked types.
             * @return A type description describing the linked type or {@code null}.
             */
            TypeDescription getEnclosingType(TypePool typePool);

            /**
             * Returns {@code true} if this instance represents a self declared type.
             *
             * @return {@code true} if this instance represents a self declared type.
             */
            boolean isSelfDeclared();

            /**
             * Returns {@code true} if this instance represents a type that was declared within another type but not
             * within a method.
             *
             * @return {@code true} if this instance represents a type that was declared within another type but not
             * within a method.
             */
            boolean isDeclaredInType();

            /**
             * Returns {@code true} if this instance represents a type that was declared within a method.
             *
             * @return {@code true} if this instance represents a type that was declared within a method.
             */
            boolean isDeclaredInMethod();

            /**
             * Represents a self-declared type that is not defined within another type.
             */
            enum SelfDeclared implements DeclarationContext {

                /**
                 * The singleton instance.
                 */
                INSTANCE;

                @Override
                public MethodDescription getEnclosingMethod(TypePool typePool) {
                    return null;
                }

                @Override
                public TypeDescription getEnclosingType(TypePool typePool) {
                    return null;
                }

                @Override
                public boolean isSelfDeclared() {
                    return true;
                }

                @Override
                public boolean isDeclaredInType() {
                    return false;
                }

                @Override
                public boolean isDeclaredInMethod() {
                    return false;
                }

                @Override
                public String toString() {
                    return "TypePool.LazyTypeDescription.DeclarationContext.SelfDeclared." + name();
                }
            }

            /**
             * A declaration context representing a type that is declared within another type but not within
             * a method.
             */
            class DeclaredInType implements DeclarationContext {

                /**
                 * The binary name of the referenced type.
                 */
                private final String name;

                /**
                 * Creates a new declaration context for a type that is declared within another type.
                 *
                 * @param internalName The internal name of the declaring type.
                 */
                public DeclaredInType(String internalName) {
                    name = internalName.replace('/', '.');
                }

                @Override
                public MethodDescription getEnclosingMethod(TypePool typePool) {
                    return null;
                }

                @Override
                public TypeDescription getEnclosingType(TypePool typePool) {
                    return typePool.describe(name).resolve();
                }

                @Override
                public boolean isSelfDeclared() {
                    return false;
                }

                @Override
                public boolean isDeclaredInType() {
                    return true;
                }

                @Override
                public boolean isDeclaredInMethod() {
                    return false;
                }

                @Override
                public boolean equals(Object other) {
                    return this == other || !(other == null || getClass() != other.getClass())
                            && name.equals(((DeclaredInType) other).name);
                }

                @Override
                public int hashCode() {
                    return name.hashCode();
                }

                @Override
                public String toString() {
                    return "TypePool.LazyTypeDescription.DeclarationContext.DeclaredInType{" +
                            "name='" + name + '\'' +
                            '}';
                }
            }

            /**
             * A declaration context representing a type that is declared within a method of another type.
             */
            class DeclaredInMethod implements DeclarationContext {

                /**
                 * The binary name of the declaring type.
                 */
                private final String name;

                /**
                 * The name of the method that is declaring a type.
                 */
                private final String methodName;

                /**
                 * The descriptor of the method that is declaring a type.
                 */
                private final String methodDescriptor;

                /**
                 * Creates a new declaration context for a method that declares a type.
                 *
                 * @param internalName     The internal name of the declaring type.
                 * @param methodName       The name of the method that is declaring a type.
                 * @param methodDescriptor The descriptor of the method that is declaring a type.
                 */
                public DeclaredInMethod(String internalName, String methodName, String methodDescriptor) {
                    name = internalName.replace('/', '.');
                    this.methodName = methodName;
                    this.methodDescriptor = methodDescriptor;
                }

                @Override
                public MethodDescription getEnclosingMethod(TypePool typePool) {
                    return getEnclosingType(typePool).getDeclaredMethods()
                            .filter((MethodDescription.CONSTRUCTOR_INTERNAL_NAME.equals(methodName)
                                    ? isConstructor()
                                    : ElementMatchers.<MethodDescription>named(methodName))
                                    .<MethodDescription>and(hasDescriptor(methodDescriptor))).getOnly();
                }

                @Override
                public TypeDescription getEnclosingType(TypePool typePool) {
                    return typePool.describe(name).resolve();
                }

                @Override
                public boolean isSelfDeclared() {
                    return false;
                }

                @Override
                public boolean isDeclaredInType() {
                    return false;
                }

                @Override
                public boolean isDeclaredInMethod() {
                    return true;
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (other == null || getClass() != other.getClass()) return false;
                    DeclaredInMethod that = (DeclaredInMethod) other;
                    return methodDescriptor.equals(that.methodDescriptor)
                            && methodName.equals(that.methodName)
                            && name.equals(that.name);
                }

                @Override
                public int hashCode() {
                    int result = name.hashCode();
                    result = 31 * result + methodName.hashCode();
                    result = 31 * result + methodDescriptor.hashCode();
                    return result;
                }

                @Override
                public String toString() {
                    return "TypePool.LazyTypeDescription.DeclarationContext.DeclaredInMethod{" +
                            "name='" + name + '\'' +
                            ", methodName='" + methodName + '\'' +
                            ", methodDescriptor='" + methodDescriptor + '\'' +
                            '}';
                }
            }
        }

        /**
         * A token for representing collected data on an annotation.
         */
        protected static class AnnotationToken {

            /**
             * The descriptor of the represented annotation.
             */
            private final String descriptor;

            /**
             * A map of annotation value names to their value representations.
             */
            private final Map<String, AnnotationDescription.AnnotationValue<?, ?>> values;

            /**
             * Creates a new annotation token.
             *
             * @param descriptor The descriptor of the represented annotation.
             * @param values     A map of annotation value names to their value representations.
             */
            protected AnnotationToken(String descriptor, Map<String, AnnotationDescription.AnnotationValue<?, ?>> values) {
                this.descriptor = descriptor;
                this.values = values;
            }

            /**
             * Returns the descriptor of the represented annotation.
             *
             * @return The descriptor of the represented annotation.
             */
            public String getDescriptor() {
                return descriptor;
            }

            /**
             * Returns a map of annotation value names to their value representations.
             *
             * @return A map of annotation value names to their value representations.
             */
            public Map<String, AnnotationDescription.AnnotationValue<?, ?>> getValues() {
                return values;
            }

            /**
             * Transforms this token into an annotation description.
             *
             * @param typePool The type pool to be used for looking up linked types.
             * @return An annotation description that resembles this token.
             */
            private AnnotationDescription toAnnotationDescription(TypePool typePool) {
                return new LazyAnnotationDescription(typePool, descriptor, values);
            }

            @Override
            public boolean equals(Object other) {
                if (this == other) return true;
                if (other == null || getClass() != other.getClass()) return false;
                AnnotationToken that = (AnnotationToken) other;
                return descriptor.equals(that.descriptor)
                        && values.equals(that.values);
            }

            @Override
            public int hashCode() {
                int result = descriptor.hashCode();
                result = 31 * result + values.hashCode();
                return result;
            }

            @Override
            public String toString() {
                return "TypePool.LazyTypeDescription.AnnotationToken{" +
                        "descriptor='" + descriptor + '\'' +
                        ", values=" + values +
                        '}';
            }
        }

        /**
         * A token for representing collected data on a field.
         */
        protected static class FieldToken {

            /**
             * The modifiers of the represented field.
             */
            private final int modifiers;

            /**
             * The name of the field.
             */
            private final String name;

            /**
             * The descriptor of the field.
             */
            private final String descriptor;

            private final GenericTypeToken.Resolution.ForField signatureResoltion;

            /**
             * A list of annotation tokens representing the annotations of the represented field.
             */
            private final List<AnnotationToken> annotationTokens;

            protected FieldToken(int modifiers,
                                 String name,
                                 String descriptor,
                                 GenericTypeToken.Resolution.ForField signatureResoltion,
                                 List<AnnotationToken> annotationTokens) {
                this.modifiers = modifiers;
                this.name = name;
                this.descriptor = descriptor;
                this.signatureResoltion = signatureResoltion;
                this.annotationTokens = annotationTokens;
            }

            /**
             * Returns the modifiers of the represented field.
             *
             * @return The modifiers of the represented field.
             */
            protected int getModifiers() {
                return modifiers;
            }

            /**
             * Returns the name of the represented field.
             *
             * @return The name of the represented field.
             */
            protected String getName() {
                return name;
            }

            /**
             * Returns the descriptor of the represented field.
             *
             * @return The descriptor of the represented field.
             */
            protected String getDescriptor() {
                return descriptor;
            }

            protected GenericTypeToken.Resolution.ForField getSignatureResolution() {
                return signatureResoltion;
            }

            /**
             * Returns a list of annotation tokens of the represented field.
             *
             * @return A list of annotation tokens of the represented field.
             */
            protected List<AnnotationToken> getAnnotationTokens() {
                return annotationTokens;
            }

            /**
             * Transforms this token into a lazy field description.
             *
             * @param lazyTypeDescription The lazy type description to attach this field description to.
             * @return A field description resembling this field token.
             */
            private FieldDescription toFieldDescription(LazyTypeDescription lazyTypeDescription) {
                return lazyTypeDescription.new LazyFieldDescription(getModifiers(),
                        getName(),
                        getDescriptor(),
                        getSignatureResolution(),
                        getAnnotationTokens());
            }

            @Override
            public boolean equals(Object other) {
                if (this == other) return true;
                if (other == null || getClass() != other.getClass()) return false;
                FieldToken that = (FieldToken) other;
                return modifiers == that.modifiers
                        && annotationTokens.equals(that.annotationTokens)
                        && descriptor.equals(that.descriptor)
                        && signatureResoltion.equals(that.signatureResoltion)
                        && name.equals(that.name);
            }

            @Override
            public int hashCode() {
                int result = modifiers;
                result = 31 * result + name.hashCode();
                result = 31 * result + descriptor.hashCode();
                result = 31 * result + signatureResoltion.hashCode();
                result = 31 * result + annotationTokens.hashCode();
                return result;
            }

            @Override
            public String toString() {
                return "TypePool.LazyTypeDescription.FieldToken{" +
                        "modifiers=" + modifiers +
                        ", name='" + name + '\'' +
                        ", descriptor='" + descriptor + '\'' +
                        ", signatureResoltion=" + signatureResoltion +
                        ", annotationTokens=" + annotationTokens +
                        '}';
            }
        }

        /**
         * A token for representing collected data on a method.
         */
        protected static class MethodToken {

            /**
             * The modifiers of the represented method.
             */
            private final int modifiers;

            /**
             * The internal name of the represented method.
             */
            private final String name;

            /**
             * The descriptor of the represented method.
             */
            private final String descriptor;

            private final GenericTypeToken.Resolution.ForMethod signatureResolution;

            /**
             * An array of internal names of the exceptions of the represented method or {@code null} if there
             * are no such exceptions.
             */
            private final String[] exceptionName;

            /**
             * A list of annotation tokens that are present on the represented method.
             */
            private final List<AnnotationToken> annotationTokens;

            /**
             * A map of parameter indices to tokens that represent their annotations.
             */
            private final Map<Integer, List<AnnotationToken>> parameterAnnotationTokens;

            /**
             * A list of tokens describing meta data of the method's parameters.
             */
            private final List<ParameterToken> parameterTokens;

            /**
             * The default value of this method or {@code null} if there is no such value.
             */
            private final AnnotationDescription.AnnotationValue<?, ?> defaultValue;

            protected MethodToken(int modifiers,
                                  String name,
                                  String descriptor,
                                  GenericTypeToken.Resolution.ForMethod signatureResolution,
                                  String[] exceptionName,
                                  List<AnnotationToken> annotationTokens,
                                  Map<Integer, List<AnnotationToken>> parameterAnnotationTokens,
                                  List<ParameterToken> parameterTokens,
                                  AnnotationDescription.AnnotationValue<?, ?> defaultValue) {
                this.modifiers = modifiers;
                this.name = name;
                this.descriptor = descriptor;
                this.signatureResolution = signatureResolution;
                this.exceptionName = exceptionName;
                this.annotationTokens = annotationTokens;
                this.parameterAnnotationTokens = parameterAnnotationTokens;
                this.parameterTokens = parameterTokens;
                this.defaultValue = defaultValue;
            }

            /**
             * Returns the modifiers of the represented method.
             *
             * @return The modifiers of the represented method.
             */
            protected int getModifiers() {
                return modifiers;
            }

            /**
             * Returns the internal name of the represented method.
             *
             * @return The internal name of the represented method.
             */
            protected String getName() {
                return name;
            }

            /**
             * Returns the descriptor of the represented method.
             *
             * @return The descriptor of the represented method.
             */
            protected String getDescriptor() {
                return descriptor;
            }

            protected GenericTypeToken.Resolution.ForMethod getSignatureResolution() {
                return signatureResolution;
            }

            /**
             * Returns the internal names of the exception type declared of the represented method.
             *
             * @return The internal names of the exception type declared of the represented method.
             */
            protected String[] getExceptionName() {
                return exceptionName;
            }

            /**
             * Returns a list of annotation tokens declared by the represented method.
             *
             * @return A list of annotation tokens declared by the represented method.
             */
            protected List<AnnotationToken> getAnnotationTokens() {
                return annotationTokens;
            }

            /**
             * Returns a map of parameter type indices to a list of annotation tokens representing these annotations.
             *
             * @return A map of parameter type indices to a list of annotation tokens representing these annotations.
             */
            protected Map<Integer, List<AnnotationToken>> getParameterAnnotationTokens() {
                return parameterAnnotationTokens;
            }

            /**
             * Returns the parameter tokens for this type. These tokens might be out of sync with the method's
             * parameters if the meta information attached to a method is not available or corrupt.
             *
             * @return A list of parameter tokens to the described method.
             */
            protected List<ParameterToken> getParameterTokens() {
                return parameterTokens;
            }

            /**
             * Returns the default value of the represented method or {@code null} if no such values exists.
             *
             * @return The default value of the represented method or {@code null} if no such values exists.
             */
            protected AnnotationDescription.AnnotationValue<?, ?> getDefaultValue() {
                return defaultValue;
            }

            /**
             * Transforms this method token to a method description that is attached to a lazy type description.
             *
             * @param lazyTypeDescription The lazy type description to attach this method description to.
             * @return A method description representing this field token.
             */
            private MethodDescription toMethodDescription(LazyTypeDescription lazyTypeDescription) {
                return lazyTypeDescription.new LazyMethodDescription(getModifiers(),
                        getName(),
                        getDescriptor(),
                        getSignatureResolution(),
                        getExceptionName(),
                        getAnnotationTokens(),
                        getParameterAnnotationTokens(),
                        getParameterTokens(),
                        getDefaultValue());
            }

            @Override
            public boolean equals(Object other) {
                if (this == other) return true;
                if (other == null || getClass() != other.getClass()) return false;
                MethodToken that = (MethodToken) other;
                return modifiers == that.modifiers
                        && annotationTokens.equals(that.annotationTokens)
                        && defaultValue.equals(that.defaultValue)
                        && descriptor.equals(that.descriptor)
                        && parameterTokens.equals(that.parameterTokens)
                        && signatureResolution.equals(that.signatureResolution)
                        && Arrays.equals(exceptionName, that.exceptionName)
                        && name.equals(that.name)
                        && parameterAnnotationTokens.equals(that.parameterAnnotationTokens);
            }

            @Override
            public int hashCode() {
                int result = modifiers;
                result = 31 * result + name.hashCode();
                result = 31 * result + descriptor.hashCode();
                result = 31 * result + signatureResolution.hashCode();
                result = 31 * result + Arrays.hashCode(exceptionName);
                result = 31 * result + annotationTokens.hashCode();
                result = 31 * result + parameterAnnotationTokens.hashCode();
                result = 31 * result + parameterTokens.hashCode();
                result = 31 * result + defaultValue.hashCode();
                return result;
            }

            @Override
            public String toString() {
                return "TypePool.LazyTypeDescription.MethodToken{" +
                        "modifiers=" + modifiers +
                        ", name='" + name + '\'' +
                        ", descriptor='" + descriptor + '\'' +
                        ", signatureResolution=" + signatureResolution +
                        ", exceptionName=" + Arrays.toString(exceptionName) +
                        ", annotationTokens=" + annotationTokens +
                        ", parameterAnnotationTokens=" + parameterAnnotationTokens +
                        ", parameterTokens=" + parameterTokens +
                        ", defaultValue=" + defaultValue +
                        '}';
            }

            /**
             * A token representing a method's parameter.
             */
            protected static class ParameterToken {

                /**
                 * Donates an unknown name of a parameter.
                 */
                protected static final String NO_NAME = null;

                /**
                 * Donates an unknown modifier of a parameter.
                 */
                protected static final Integer NO_MODIFIERS = null;

                /**
                 * The name of the parameter or {@code null} if no explicit name for this parameter is known.
                 */
                private final String name;

                /**
                 * The modifiers of the parameter or {@code null} if no modifiers are known for this parameter.
                 */
                private final Integer modifiers;

                /**
                 * Creates a parameter token for a parameter without an explicit name and without specific modifiers.
                 */
                protected ParameterToken() {
                    this(NO_NAME);
                }

                /**
                 * Creates a parameter token for a parameter with an explicit name and without specific modifiers.
                 *
                 * @param name The name of the parameter.
                 */
                protected ParameterToken(String name) {
                    this(name, NO_MODIFIERS);
                }

                /**
                 * Creates a parameter token for a parameter with an explicit name and with specific modifiers.
                 *
                 * @param name      The name of the parameter.
                 * @param modifiers The modifiers of the parameter.
                 */
                protected ParameterToken(String name, Integer modifiers) {
                    this.name = name;
                    this.modifiers = modifiers;
                }

                /**
                 * Returns the name of the parameter or {@code null} if there is no such name.
                 *
                 * @return The name of the parameter or {@code null} if there is no such name.
                 */
                protected String getName() {
                    return name;
                }

                /**
                 * Returns the modifiers of the parameter or {@code null} if no modifiers are known.
                 *
                 * @return The modifiers of the parameter or {@code null} if no modifiers are known.
                 */
                protected Integer getModifiers() {
                    return modifiers;
                }

                @Override
                public boolean equals(Object other) {
                    if (this == other) return true;
                    if (other == null || getClass() != other.getClass()) return false;
                    ParameterToken that = ((ParameterToken) other);
                    return !(modifiers != null ? !modifiers.equals(that.modifiers) : that.modifiers != null)
                            && !(name != null ? !name.equals(that.name) : that.name != null);
                }

                @Override
                public int hashCode() {
                    int result = name != null ? name.hashCode() : 0;
                    result = 31 * result + (modifiers != null ? modifiers.hashCode() : 0);
                    return result;
                }

                @Override
                public String toString() {
                    return "TypePool.LazyTypeDescription.MethodToken.ParameterToken{" +
                            "name='" + name + '\'' +
                            ", modifiers=" + modifiers +
                            '}';
                }
            }
        }

        protected interface GenericTypeToken {

            Sort getSort();

            GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource);

            interface Resolution {

                GenericTypeList resolveTypeVariables(TypePool typePool, TypeVariableSource typeVariableSource);

                interface ForType extends Resolution {

                    GenericTypeDescription resolveSuperType(String superTypeDescriptor, TypePool typePool, TypeDescription definingType);

                    GenericTypeList resolveInterfaceTypes(List<String> interfaceTypeDescriptors, TypePool typePool, TypeDescription definingType);

                    class Tokenized implements ForType {

                        private final GenericTypeToken superTypeToken;

                        private final List<GenericTypeToken> interfaceTypeTokens;

                        private final List<GenericTypeToken> typeVariableTokens;

                        public Tokenized(GenericTypeToken superTypeToken,
                                         List<GenericTypeToken> interfaceTypeTokens,
                                         List<GenericTypeToken> typeVariableTokens) {
                            this.superTypeToken = superTypeToken;
                            this.interfaceTypeTokens = interfaceTypeTokens;
                            this.typeVariableTokens = typeVariableTokens;
                        }

                        @Override
                        public GenericTypeDescription resolveSuperType(String superTypeDescriptor, TypePool typePool, TypeDescription definingType) {
                            return new TokenizedGenericType(typePool, superTypeToken, superTypeDescriptor, definingType);
                        }

                        @Override
                        public GenericTypeList resolveInterfaceTypes(List<String> interfaceTypeDescriptors, TypePool typePool, TypeDescription definingType) {
                            return TokenizedGenericType.TokenList.of(typePool, interfaceTypeTokens, interfaceTypeDescriptors, definingType);
                        }

                        @Override
                        public GenericTypeList resolveTypeVariables(TypePool typePool, TypeVariableSource typeVariableSource) {
                            return TokenizedGenericType.TypeVariableList.of(typePool, typeVariableTokens, typeVariableSource);
                        }
                    }
                }

                interface ForMethod extends Resolution {

                    GenericTypeDescription resolveReturnType(String returnTypeDescriptor, TypePool typePool, MethodDescription definingMethod);

                    GenericTypeList resolveParameterTypes(List<String> parameterTypeDescriptors, TypePool typePool, MethodDescription definingMethod);

                    GenericTypeList resolveExceptionTypes(List<String> exceptionTypeDescriptors, TypePool typePool, MethodDescription definingMethod);

                    class Tokenized implements ForMethod {

                        private final GenericTypeToken returnTypeToken;

                        private final List<GenericTypeToken> parameterTypeTokens;

                        private final List<GenericTypeToken> exceptionTypeTokens;

                        private final List<GenericTypeToken> typeVariableTokens;

                        public Tokenized(GenericTypeToken returnTypeToken,
                                         List<GenericTypeToken> parameterTypeTokens,
                                         List<GenericTypeToken> exceptionTypeTokens,
                                         List<GenericTypeToken> typeVariableTokens) {
                            this.returnTypeToken = returnTypeToken;
                            this.parameterTypeTokens = parameterTypeTokens;
                            this.exceptionTypeTokens = exceptionTypeTokens;
                            this.typeVariableTokens = typeVariableTokens;
                        }

                        @Override
                        public GenericTypeDescription resolveReturnType(String returnTypeDescriptor, TypePool typePool, MethodDescription definingMethod) {
                            return new TokenizedGenericType(typePool, returnTypeToken, returnTypeDescriptor, definingMethod);
                        }

                        @Override
                        public GenericTypeList resolveParameterTypes(List<String> parameterTypeDescriptors, TypePool typePool, MethodDescription definingMethod) {
                            return TokenizedGenericType.TokenList.of(typePool, parameterTypeTokens, parameterTypeDescriptors, definingMethod);
                        }

                        @Override
                        public GenericTypeList resolveExceptionTypes(List<String> exceptionTypeDescriptors, TypePool typePool, MethodDescription definingMethod) {
                            return TokenizedGenericType.TokenList.of(typePool, exceptionTypeTokens, exceptionTypeDescriptors, definingMethod);
                        }

                        @Override
                        public GenericTypeList resolveTypeVariables(TypePool typePool, TypeVariableSource typeVariableSource) {
                            return TokenizedGenericType.TypeVariableList.of(typePool, typeVariableTokens, typeVariableSource);
                        }
                    }
                }

                interface ForField {

                    GenericTypeDescription resolveFieldType(String fieldTypeDescriptor, TypePool typePool, FieldDescription definingField);

                    class Tokenized implements ForField {

                        private final GenericTypeToken fieldTypeToken;

                        public Tokenized(GenericTypeToken fieldTypeToken) {
                            this.fieldTypeToken = fieldTypeToken;
                        }

                        @Override
                        public GenericTypeDescription resolveFieldType(String fieldTypeDescriptor, TypePool typePool, FieldDescription definingField) {
                            return new TokenizedGenericType(typePool, fieldTypeToken, fieldTypeDescriptor, definingField.getDeclaringType());
                        }
                    }
                }

                enum Raw implements ForType, ForMethod, ForField {

                    INSTANCE;

                    @Override
                    public GenericTypeDescription resolveFieldType(String fieldTypeDescriptor, TypePool typePool, FieldDescription definingField) {
                        return TokenizedGenericType.toRawType(typePool, fieldTypeDescriptor);
                    }

                    @Override
                    public GenericTypeDescription resolveReturnType(String returnTypeDescriptor, TypePool typePool, MethodDescription definingMethod) {
                        return TokenizedGenericType.toRawType(typePool, returnTypeDescriptor);
                    }

                    @Override
                    public GenericTypeList resolveParameterTypes(List<String> parameterTypeDescriptors, TypePool typePool, MethodDescription definingMethod) {
                        return LazyTypeList.of(typePool, parameterTypeDescriptors).asGenericTypes();
                    }

                    @Override
                    public GenericTypeList resolveExceptionTypes(List<String> exceptionTypeDescriptors, TypePool typePool, MethodDescription definingMethod) {
                        return LazyTypeList.of(typePool, exceptionTypeDescriptors).asGenericTypes();
                    }

                    @Override
                    public GenericTypeDescription resolveSuperType(String superTypeDescriptor, TypePool typePool, TypeDescription definingType) {
                        return TokenizedGenericType.toRawType(typePool, superTypeDescriptor);
                    }

                    @Override
                    public GenericTypeList resolveInterfaceTypes(List<String> interfaceTypeDescriptors, TypePool typePool, TypeDescription definingType) {
                        return LazyTypeList.of(typePool, interfaceTypeDescriptors).asGenericTypes();
                    }

                    @Override
                    public GenericTypeList resolveTypeVariables(TypePool typePool, TypeVariableSource typeVariableSource) {
                        return new GenericTypeList.Empty();
                    }
                }

                enum Defective implements ForType, ForMethod, ForField {

                    INSTANCE;

                    @Override
                    public GenericTypeDescription resolveFieldType(String fieldTypeDescriptor, TypePool typePool, FieldDescription definingField) {
                        return new TokenizedGenericType.Defective(typePool, fieldTypeDescriptor);
                    }

                    @Override
                    public GenericTypeDescription resolveReturnType(String returnTypeDescriptor, TypePool typePool, MethodDescription definingMethod) {
                        return new TokenizedGenericType.Defective(typePool, returnTypeDescriptor);
                    }

                    @Override
                    public GenericTypeList resolveParameterTypes(List<String> parameterTypeDescriptors, TypePool typePool, MethodDescription definingMethod) {
                        return new TokenizedGenericType.Defective.TokenList(typePool, parameterTypeDescriptors);
                    }

                    @Override
                    public GenericTypeList resolveExceptionTypes(List<String> exceptionTypeDescriptors, TypePool typePool, MethodDescription definingMethod) {
                        return new TokenizedGenericType.Defective.TokenList(typePool, exceptionTypeDescriptors);
                    }

                    @Override
                    public GenericTypeDescription resolveSuperType(String superTypeDescriptor, TypePool typePool, TypeDescription definingType) {
                        return new TokenizedGenericType.Defective(typePool, superTypeDescriptor);
                    }

                    @Override
                    public GenericTypeList resolveInterfaceTypes(List<String> interfaceTypeDescriptors, TypePool typePool, TypeDescription definingType) {
                        return new TokenizedGenericType.Defective.TokenList(typePool, interfaceTypeDescriptors);
                    }

                    @Override
                    public GenericTypeList resolveTypeVariables(TypePool typePool, TypeVariableSource typeVariableSource) {
                        throw new MalformedParameterizedTypeException();
                    }
                }
            }

            enum ForPrimitiveType implements GenericTypeToken {

                BOOLEAN(boolean.class),
                BYTE(byte.class),
                SHORT(short.class),
                CHAR(char.class),
                INTEGER(int.class),
                LONG(long.class),
                FLOAT(float.class),
                DOUBLE(double.class),
                VOID(void.class);

                public static GenericTypeToken of(char descriptor) {
                    switch (descriptor) {
                        case 'V':
                            return VOID;
                        case 'Z':
                            return BOOLEAN;
                        case 'B':
                            return BYTE;
                        case 'S':
                            return SHORT;
                        case 'C':
                            return CHAR;
                        case 'I':
                            return INTEGER;
                        case 'J':
                            return LONG;
                        case 'F':
                            return FLOAT;
                        case 'D':
                            return DOUBLE;
                        default:
                            throw new IllegalArgumentException("Not a valid descriptor: " + descriptor);
                    }
                }

                private final TypeDescription typeDescription;

                ForPrimitiveType(Class<?> type) {
                    typeDescription = new TypeDescription.ForLoadedType(type);
                }

                @Override
                public Sort getSort() {
                    return Sort.RAW;
                }

                @Override
                public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                    return typeDescription;
                }
            }

            class ForRawType implements GenericTypeToken {

                private final String name;

                public ForRawType(String name) {
                    this.name = name;
                }

                @Override
                public Sort getSort() {
                    return Sort.RAW;
                }

                @Override
                public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                    return typePool.describe(name).resolve();
                }
            }

            class ForTypeVariable implements GenericTypeToken {

                private final String symbol;

                public ForTypeVariable(String symbol) {
                    this.symbol = symbol;
                }

                @Override
                public Sort getSort() {
                    return Sort.VARIABLE;
                }

                @Override
                public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                    GenericTypeDescription typeVariable = typeVariableSource.findVariable(symbol);
                    if (typeVariable == null) {
                        throw new IllegalStateException("Cannot resolve type variable " + symbol + " for " + typeVariableSource);
                    } else {
                        return typeVariable;
                    }
                }

                public static class Formal implements GenericTypeToken {

                    private final String symbol;

                    private final List<GenericTypeToken> bounds;

                    public Formal(String symbol, List<GenericTypeToken> bounds) {
                        this.symbol = symbol;
                        this.bounds = bounds;
                    }

                    @Override
                    public Sort getSort() {
                        return Sort.VARIABLE;
                    }

                    @Override
                    public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                        return new LazyTypeVariable(typePool, typeVariableSource);
                    }

                    protected class LazyTypeVariable extends GenericTypeDescription.ForTypeVariable {

                        private final TypePool typePool;

                        private final TypeVariableSource typeVariableSource;

                        protected LazyTypeVariable(TypePool typePool, TypeVariableSource typeVariableSource) {
                            this.typePool = typePool;
                            this.typeVariableSource = typeVariableSource;
                        }

                        @Override
                        public GenericTypeList getUpperBounds() {
                            List<GenericTypeDescription> genericTypeDescriptions = new ArrayList<GenericTypeDescription>(bounds.size());
                            for (GenericTypeToken bound : bounds) {
                                genericTypeDescriptions.add(bound.toGenericType(typePool, typeVariableSource));
                            }
                            return new GenericTypeList.Explicit(genericTypeDescriptions);
                        }

                        @Override
                        public TypeVariableSource getVariableSource() {
                            return typeVariableSource;
                        }

                        @Override
                        public String getSymbol() {
                            return symbol;
                        }
                    }
                }
            }

            class ForArray implements GenericTypeToken {

                private final GenericTypeToken componentTypeToken;

                public ForArray(GenericTypeToken componentTypeToken) {
                    this.componentTypeToken = componentTypeToken;
                }

                @Override
                public Sort getSort() {
                    return Sort.GENERIC_ARRAY;
                }

                @Override
                public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                    return GenericTypeDescription.ForGenericArray.Latent.of(componentTypeToken.toGenericType(typePool, typeVariableSource), 1);
                }
            }

            class ForLowerBoundWildcard implements GenericTypeToken {

                private final GenericTypeToken baseType;

                public ForLowerBoundWildcard(GenericTypeToken baseType) {
                    this.baseType = baseType;
                }

                @Override
                public Sort getSort() {
                    return Sort.WILDCARD;
                }

                @Override
                public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                    return GenericTypeDescription.ForWildcardType.Latent.boundedBelow(baseType.toGenericType(typePool, typeVariableSource));
                }
            }

            class ForUpperBoundWildcard implements GenericTypeToken {

                private final GenericTypeToken baseType;

                public ForUpperBoundWildcard(GenericTypeToken baseType) {
                    this.baseType = baseType;
                }

                @Override
                public Sort getSort() {
                    return Sort.WILDCARD;
                }

                @Override
                public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                    return GenericTypeDescription.ForWildcardType.Latent.boundedAbove(baseType.toGenericType(typePool, typeVariableSource));
                }
            }

            enum ForUnboundWildcard implements GenericTypeToken {

                INSTANCE;

                @Override
                public Sort getSort() {
                    return Sort.WILDCARD;
                }

                @Override
                public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                    return GenericTypeDescription.ForWildcardType.Latent.unbounded();
                }
            }

            class ForParameterizedType implements GenericTypeToken {

                private final String name;

                private final List<GenericTypeToken> parameters;

                public ForParameterizedType(String name, List<GenericTypeToken> parameters) {
                    this.name = name;
                    this.parameters = parameters;
                }

                @Override
                public Sort getSort() {
                    return Sort.PARAMETERIZED;
                }

                @Override
                public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                    return new LazyParameterizedType(typePool, typeVariableSource);
                }

                protected class LazyParameterizedType extends GenericTypeDescription.ForParameterizedType {

                    private final TypePool typePool;

                    private final TypeVariableSource typeVariableSource;

                    public LazyParameterizedType(TypePool typePool, TypeVariableSource typeVariableSource) {
                        this.typePool = typePool;
                        this.typeVariableSource = typeVariableSource;
                    }

                    @Override
                    public TypeDescription asRawType() {
                        return typePool.describe(name).resolve();
                    }

                    @Override
                    public GenericTypeList getParameters() {
                        List<GenericTypeDescription> genericTypeDescriptions = new ArrayList<GenericTypeDescription>(parameters.size());
                        for (GenericTypeToken parameter : parameters) {
                            genericTypeDescriptions.add(parameter.toGenericType(typePool, typeVariableSource));
                        }
                        return new GenericTypeList.Explicit(genericTypeDescriptions);
                    }

                    @Override
                    public GenericTypeDescription getOwnerType() {
                        return typePool.describe(name).resolve().getEnclosingType();
                    }
                }

                public static class Nested implements GenericTypeToken {

                    private final String name;

                    private final List<GenericTypeToken> parameters;

                    private final GenericTypeToken ownerType;

                    public Nested(String name, List<GenericTypeToken> parameters, GenericTypeToken ownerType) {
                        this.name = name;
                        this.parameters = parameters;
                        this.ownerType = ownerType;
                    }

                    @Override
                    public Sort getSort() {
                        return Sort.PARAMETERIZED;
                    }

                    @Override
                    public GenericTypeDescription toGenericType(TypePool typePool, TypeVariableSource typeVariableSource) {
                        return new LazyParameterizedType(typePool, typeVariableSource);
                    }

                    protected class LazyParameterizedType extends GenericTypeDescription.ForParameterizedType {

                        private final TypePool typePool;

                        private final TypeVariableSource typeVariableSource;

                        public LazyParameterizedType(TypePool typePool, TypeVariableSource typeVariableSource) {
                            this.typePool = typePool;
                            this.typeVariableSource = typeVariableSource;
                        }

                        @Override
                        public TypeDescription asRawType() {
                            return typePool.describe(name).resolve();
                        }

                        @Override
                        public GenericTypeList getParameters() {
                            List<GenericTypeDescription> genericTypeDescriptions = new ArrayList<GenericTypeDescription>(parameters.size());
                            for (GenericTypeToken parameter : parameters) {
                                genericTypeDescriptions.add(parameter.toGenericType(typePool, typeVariableSource));
                            }
                            return new GenericTypeList.Explicit(genericTypeDescriptions);
                        }

                        @Override
                        public GenericTypeDescription getOwnerType() {
                            return ownerType.toGenericType(typePool, typeVariableSource);
                        }
                    }
                }
            }
        }

        /**
         * A lazy description of an annotation that looks up types from a type pool when required.
         */
        private static class LazyAnnotationDescription extends AnnotationDescription.AbstractAnnotationDescription {

            /**
             * The type pool for looking up type references.
             */
            protected final TypePool typePool;

            /**
             * A map of annotation values by their property name.
             */
            protected final Map<String, AnnotationValue<?, ?>> values;

            /**
             * The descriptor of this annotation.
             */
            private final String descriptor;

            /**
             * Creates a new lazy annotation description.
             *
             * @param typePool   The type pool to be used for looking up linked types.
             * @param descriptor The descriptor of the annotation type.
             * @param values     A map of annotation value names to their value representations.
             */
            private LazyAnnotationDescription(TypePool typePool,
                                              String descriptor,
                                              Map<String, AnnotationValue<?, ?>> values) {
                this.typePool = typePool;
                this.descriptor = descriptor;
                this.values = values;
            }

            @Override
            public Object getValue(MethodDescription methodDescription) {
                if (!methodDescription.getDeclaringType().getDescriptor().equals(descriptor)) {
                    throw new IllegalArgumentException(methodDescription + " is not declared by " + getAnnotationType());
                }
                AnnotationValue<?, ?> annotationValue = values.get(methodDescription.getName());
                Object value = annotationValue == null
                        ? getAnnotationType().getDeclaredMethods().filter(is(methodDescription)).getOnly().getDefaultValue()
                        : annotationValue.resolve();
                if (value == null) {
                    throw new IllegalStateException(methodDescription + " is not defined on annotation");
                }
                return PropertyDispatcher.of(value.getClass()).conditionalClone(value);
            }

            @Override
            public TypeDescription getAnnotationType() {
                return typePool.describe(descriptor.substring(1, descriptor.length() - 1).replace('/', '.')).resolve();
            }

            @Override
            public <T extends Annotation> Loadable<T> prepare(Class<T> annotationType) {
                return new Loadable<T>(typePool, descriptor, values, annotationType);
            }

            /**
             * A loadable version of a lazy annotation description.
             *
             * @param <S> The annotation type.
             */
            private static class Loadable<S extends Annotation> extends LazyAnnotationDescription implements AnnotationDescription.Loadable<S> {

                /**
                 * The loaded annotation type.
                 */
                private final Class<S> annotationType;

                /**
                 * Creates a new loadable version of a lazy annotation.
                 *
                 * @param typePool       The type pool to be used for looking up linked types.
                 * @param descriptor     The descriptor of the represented annotation.
                 * @param values         A map of annotation value names to their value representations.
                 * @param annotationType The loaded annotation type.
                 */
                private Loadable(TypePool typePool,
                                 String descriptor,
                                 Map<String, AnnotationValue<?, ?>> values,
                                 Class<S> annotationType) {
                    super(typePool, descriptor, values);
                    if (!Type.getDescriptor(annotationType).equals(descriptor)) {
                        throw new IllegalArgumentException(annotationType + " does not correspond to " + descriptor);
                    }
                    this.annotationType = annotationType;
                }

                @Override
                public S load() throws ClassNotFoundException {
                    return load(annotationType.getClassLoader());
                }

                @Override
                @SuppressWarnings("unchecked")
                public S load(ClassLoader classLoader) throws ClassNotFoundException {
                    return (S) Proxy.newProxyInstance(classLoader,
                            new Class<?>[]{annotationType},
                            AnnotationInvocationHandler.of(annotationType.getClassLoader(), annotationType, values));
                }

                @Override
                public S loadSilent() {
                    try {
                        return load();
                    } catch (ClassNotFoundException e) {
                        throw new IllegalStateException(ForLoadedAnnotation.ERROR_MESSAGE, e);
                    }
                }

                @Override
                public S loadSilent(ClassLoader classLoader) {
                    try {
                        return load(classLoader);
                    } catch (ClassNotFoundException e) {
                        throw new IllegalStateException(ForLoadedAnnotation.ERROR_MESSAGE, e);
                    }
                }
            }
        }

        /**
         * An implementation of a {@link PackageDescription} that only
         * loads its annotations on requirement.
         */
        private static class LazyPackageDescription extends PackageDescription.AbstractPackageDescription {

            /**
             * The type pool to use for look-ups.
             */
            private final TypePool typePool;

            /**
             * The name of the package.
             */
            private final String name;

            /**
             * Creates a new lazy package description.
             *
             * @param typePool The type pool to use for look-ups.
             * @param name     The name of the package.
             */
            private LazyPackageDescription(TypePool typePool, String name) {
                this.typePool = typePool;
                this.name = name;
            }

            @Override
            public AnnotationList getDeclaredAnnotations() {
                Resolution resolution = typePool.describe(name + "." + PackageDescription.PACKAGE_CLASS_NAME);
                return resolution.isResolved()
                        ? resolution.resolve().getDeclaredAnnotations()
                        : new AnnotationList.Empty();
            }

            @Override
            public String getName() {
                return name;
            }

            @Override
            public boolean isSealed() {
                return false;
            }
        }

        /**
         * A lazy field description that only resolved type references when required.
         */
        private class LazyFieldDescription extends FieldDescription.AbstractFieldDescription {

            /**
             * The modifiers of the field.
             */
            private final int modifiers;

            /**
             * The name of the field.
             */
            private final String name;

            private final String fieldTypeDescriptor;

            private final GenericTypeToken.Resolution.ForField signatureResolution;

            /**
             * A list of annotation descriptions of this field.
             */
            private final List<AnnotationDescription> declaredAnnotations;

            private LazyFieldDescription(int modifiers,
                                         String name,
                                         String descriptor,
                                         GenericTypeToken.Resolution.ForField signatureResolution,
                                         List<AnnotationToken> annotationTokens) {
                this.modifiers = modifiers;
                this.name = name;
                fieldTypeDescriptor = descriptor;
                this.signatureResolution = signatureResolution;
                declaredAnnotations = new ArrayList<AnnotationDescription>(annotationTokens.size());
                for (AnnotationToken annotationToken : annotationTokens) {
                    declaredAnnotations.add(annotationToken.toAnnotationDescription(typePool));
                }
            }

            @Override
            public GenericTypeDescription getFieldTypeGen() {
                return signatureResolution.resolveFieldType(fieldTypeDescriptor, typePool, this);
            }

            @Override
            public AnnotationList getDeclaredAnnotations() {
                return new AnnotationList.Explicit(declaredAnnotations);
            }

            @Override
            public String getName() {
                return name;
            }

            @Override
            public TypeDescription getDeclaringType() {
                return LazyTypeDescription.this;
            }

            @Override
            public int getModifiers() {
                return modifiers;
            }
        }

        /**
         * A lazy representation of a method that resolves references to types only on demand.
         */
        private class LazyMethodDescription extends MethodDescription.AbstractMethodDescription {

            /**
             * The modifiers of this method.
             */
            private final int modifiers;

            /**
             * The internal name of this method.
             */
            private final String internalName;

            private final String returnTypeDescriptor;

            private final GenericTypeToken.Resolution.ForMethod signatureResolution;

            private final List<String> parameterTypeDescriptors;

            private final List<String> exceptionTypeDescriptors;

            /**
             * A list of annotation descriptions that are declared by this method.
             */
            private final List<AnnotationDescription> declaredAnnotations;

            /**
             * A nested list of annotation descriptions that are declared by the parameters of this
             * method in their oder.
             */
            private final List<List<AnnotationDescription>> declaredParameterAnnotations;

            /**
             * An array of parameter names which may be {@code null} if no explicit name is known for a parameter.
             */
            private final String[] parameterNames;

            /**
             * An array of parameter modifiers which may be {@code null} if no modifiers is known.
             */
            private final Integer[] parameterModifiers;

            /**
             * The default value of this method or {@code null} if no such value exists.
             */
            private final AnnotationDescription.AnnotationValue<?, ?> defaultValue;

            /**
             * Creates a new lazy method description.
             *
             * @param modifiers                 The modifiers of the represented method.
             * @param internalName              The internal name of this method.
             * @param methodDescriptor          The method descriptor of this method.
             * @param exceptionTypeInternalName The internal names of the exceptions that are declared by this
             *                                  method or {@code null} if no exceptions are declared by this
             *                                  method.
             * @param annotationTokens          A list of annotation tokens representing annotations that are declared
             *                                  by this method.
             * @param parameterAnnotationTokens A nested list of annotation tokens representing annotations that are
             *                                  declared by the fields of this method.
             * @param parameterTokens           A list of parameter tokens which might be empty or even out of sync
             *                                  with the actual parameters if the debugging information found in a
             *                                  class was corrupt.
             * @param defaultValue              The default value of this method or {@code null} if there is no
             *                                  such value.
             */
            private LazyMethodDescription(int modifiers,
                                          String internalName,
                                          String methodDescriptor,
                                          GenericTypeToken.Resolution.ForMethod signatureResolution,
                                          String[] exceptionTypeInternalName,
                                          List<AnnotationToken> annotationTokens,
                                          Map<Integer, List<AnnotationToken>> parameterAnnotationTokens,
                                          List<MethodToken.ParameterToken> parameterTokens,
                                          AnnotationDescription.AnnotationValue<?, ?> defaultValue) {
                this.modifiers = modifiers;
                this.internalName = internalName;
                Type methodType = Type.getMethodType(methodDescriptor);
                Type returnType = methodType.getReturnType();
                Type[] parameterType = methodType.getArgumentTypes();
                returnTypeDescriptor = returnType.getDescriptor();
                parameterTypeDescriptors = new ArrayList<String>(parameterType.length);
                for (Type type : parameterType) {
                    parameterTypeDescriptors.add(type.getDescriptor());
                }
                this.signatureResolution = signatureResolution;
                if (exceptionTypeInternalName == null) {
                    exceptionTypeDescriptors = Collections.emptyList();
                } else {
                    exceptionTypeDescriptors = new ArrayList<String>(exceptionTypeInternalName.length);
                    for (String anExceptionTypeInternalName : exceptionTypeInternalName) {
                        exceptionTypeDescriptors.add(Type.getObjectType(anExceptionTypeInternalName).getDescriptor());
                    }
                }
                declaredAnnotations = new ArrayList<AnnotationDescription>(annotationTokens.size());
                for (AnnotationToken annotationToken : annotationTokens) {
                    declaredAnnotations.add(annotationToken.toAnnotationDescription(typePool));
                }
                declaredParameterAnnotations = new ArrayList<List<AnnotationDescription>>(parameterType.length);
                for (int index = 0; index < parameterType.length; index++) {
                    List<AnnotationToken> tokens = parameterAnnotationTokens.get(index);
                    List<AnnotationDescription> annotationDescriptions;
                    annotationDescriptions = new ArrayList<AnnotationDescription>(tokens.size());
                    for (AnnotationToken annotationToken : tokens) {
                        annotationDescriptions.add(annotationToken.toAnnotationDescription(typePool));
                    }
                    declaredParameterAnnotations.add(annotationDescriptions);
                }
                parameterNames = new String[parameterType.length];
                parameterModifiers = new Integer[parameterType.length];
                if (parameterTokens.size() == parameterType.length) {
                    int index = 0;
                    for (MethodToken.ParameterToken parameterToken : parameterTokens) {
                        parameterNames[index] = parameterToken.getName();
                        parameterModifiers[index] = parameterToken.getModifiers();
                        index++;
                    }
                }
                this.defaultValue = defaultValue;
            }

            @Override
            public GenericTypeDescription getReturnTypeGen() {
                return signatureResolution.resolveReturnType(returnTypeDescriptor, typePool, this);
            }

            @Override
            public GenericTypeList getExceptionTypesGen() {
                return signatureResolution.resolveExceptionTypes(exceptionTypeDescriptors, typePool, this);
            }

            @Override
            public ParameterList getParameters() {
                return new LazyParameterList();
            }

            @Override
            public AnnotationList getDeclaredAnnotations() {
                return new AnnotationList.Explicit(declaredAnnotations);
            }

            @Override
            public String getInternalName() {
                return internalName;
            }

            @Override
            public TypeDescription getDeclaringType() {
                return LazyTypeDescription.this;
            }

            @Override
            public int getModifiers() {
                return modifiers;
            }

            @Override
            public GenericTypeList getTypeVariables() {
                return signatureResolution.resolveTypeVariables(typePool, this);
            }

            @Override
            public Object getDefaultValue() {
                return defaultValue == null
                        ? null
                        : defaultValue.resolve();
            }

            /**
             * A lazy list of parameter descriptions for the enclosing method description.
             */
            private class LazyParameterList extends FilterableList.AbstractBase<ParameterDescription, ParameterList> implements ParameterList {

                @Override
                protected ParameterList wrap(List<ParameterDescription> values) {
                    return new Explicit(values);
                }

                @Override
                public ParameterDescription get(int index) {
                    return new LazyParameterDescription(index);
                }

                @Override
                public boolean hasExplicitMetaData() {
                    for (int i = 0; i < size(); i++) {
                        if (parameterNames[i] == null || parameterModifiers[i] == null) {
                            return false;
                        }
                    }
                    return true;
                }

                @Override
                public int size() {
                    return parameterTypeDescriptors.size();
                }

                @Override
                public TypeList asTypeList() {
                    return LazyTypeList.of(typePool, parameterTypeDescriptors);
                }

                @Override
                public GenericTypeList asTypeListGen() {
                    return signatureResolution.resolveParameterTypes(parameterTypeDescriptors, typePool, LazyMethodDescription.this);
                }
            }

            /**
             * A lazy description of a parameters of the enclosing method.
             */
            private class LazyParameterDescription extends ParameterDescription.AbstractParameterDescription {

                /**
                 * The index of the described parameter.
                 */
                private final int index;

                /**
                 * Creates a new description for a given parameter of the enclosing method.
                 *
                 * @param index The index of the described parameter.
                 */
                protected LazyParameterDescription(int index) {
                    this.index = index;
                }

                @Override
                public TypeDescription getType() {
                    return TokenizedGenericType.toRawType(typePool, parameterTypeDescriptors.get(index));
                }

                @Override
                public MethodDescription getDeclaringMethod() {
                    return LazyMethodDescription.this;
                }

                @Override
                public int getIndex() {
                    return index;
                }

                @Override
                public boolean isNamed() {
                    return parameterNames[index] != null;
                }

                @Override
                public boolean hasModifiers() {
                    return parameterModifiers[index] != null;
                }

                @Override
                public String getName() {
                    return isNamed()
                            ? parameterNames[index]
                            : super.getName();
                }

                @Override
                public int getModifiers() {
                    return hasModifiers()
                            ? parameterModifiers[index]
                            : super.getModifiers();
                }

                @Override
                public GenericTypeDescription getTypeGen() {
                    return signatureResolution.resolveParameterTypes(parameterTypeDescriptors, typePool, LazyMethodDescription.this).get(index);
                }

                @Override
                public AnnotationList getDeclaredAnnotations() {
                    return new AnnotationList.Explicit(declaredParameterAnnotations.get(index));
                }
            }
        }

        /**
         * A list that is constructing {@link net.bytebuddy.pool.TypePool.LazyTypeDescription}s.
         */
        private static class LazyTypeList extends TypeList.AbstractBase {

            private final TypePool typePool;

            private final List<String> descriptors;

            protected static TypeList of(TypePool typePool, List<String> descriptors) {
                return descriptors.isEmpty()
                        ? new TypeList.Empty()
                        : new LazyTypeList(typePool, descriptors);
            }

            private LazyTypeList(TypePool typePool, List<String> descriptors) {
                this.typePool = typePool;
                this.descriptors = descriptors;
            }

            @Override
            public TypeDescription get(int index) {
                return TokenizedGenericType.toRawType(typePool, descriptors.get(index));
            }

            @Override
            public int size() {
                return descriptors.size();
            }

            @Override
            public String[] toInternalNames() {
                if (descriptors.isEmpty()) {
                    return null;
                } else {
                    String[] internalName = new String[descriptors.size()];
                    int index = 0;
                    for (String descriptor : descriptors) {
                        internalName[index++] = Type.getType(descriptor).getInternalName();
                    }
                    return internalName;
                }
            }

            @Override
            public int getStackSize() {
                int stackSize = 0;
                for (String descriptor : descriptors) {
                    stackSize += Type.getType(descriptor).getSize();
                }
                return stackSize;
            }

            @Override
            public GenericTypeList asGenericTypes() {
                return new Generified();
            }

            private class Generified extends GenericTypeList.AbstractBase {

                @Override
                public GenericTypeDescription get(int index) {
                    return LazyTypeList.this.get(index);
                }

                @Override
                public int size() {
                    return LazyTypeList.this.size();
                }

                @Override
                public TypeList asRawTypes() {
                    return LazyTypeList.this;
                }
            }
        }

        private static class TokenizedGenericType extends GenericTypeDescription.LazyProjection {

            protected static TypeDescription toRawType(TypePool typePool, String descriptor) {
                Type type = Type.getType(descriptor);
                return typePool.describe(type.getSort() == Type.ARRAY
                        ? type.getInternalName().replace('/', '.')
                        : type.getClassName()).resolve();
            }

            private final TypePool typePool;

            private final GenericTypeToken genericTypeToken;

            private final String rawTypeDescriptor;

            private final TypeVariableSource typeVariableSource;

            protected TokenizedGenericType(TypePool typePool, GenericTypeToken genericTypeToken, String rawTypeDescriptor, TypeVariableSource typeVariableSource) {
                this.typePool = typePool;
                this.genericTypeToken = genericTypeToken;
                this.rawTypeDescriptor = rawTypeDescriptor;
                this.typeVariableSource = typeVariableSource;
            }

            @Override
            public Sort getSort() {
                return genericTypeToken.getSort();
            }

            @Override
            protected GenericTypeDescription resolve() {
                return genericTypeToken.toGenericType(typePool, typeVariableSource);
            }

            @Override
            public TypeDescription asRawType() {
                return toRawType(typePool, rawTypeDescriptor);
            }

            protected static class TokenList extends GenericTypeList.AbstractBase {

                private final TypePool typePool;

                private final List<GenericTypeToken> genericTypeTokens;

                private final List<String> rawTypeDescriptors;

                private final TypeVariableSource typeVariableSource;

                protected static GenericTypeList of(TypePool typePool,
                                                    List<GenericTypeToken> genericTypeTokens,
                                                    List<String> rawTypeDescriptors,
                                                    TypeVariableSource typeVariableSource) {
                    return rawTypeDescriptors.isEmpty()
                            ? new GenericTypeList.Empty()
                            : new TokenList(typePool, genericTypeTokens, rawTypeDescriptors, typeVariableSource);
                }

                private TokenList(TypePool typePool,
                                  List<GenericTypeToken> genericTypeTokens,
                                  List<String> rawTypeDescriptors,
                                  TypeVariableSource typeVariableSource) {
                    this.typePool = typePool;
                    this.genericTypeTokens = genericTypeTokens;
                    this.rawTypeDescriptors = rawTypeDescriptors;
                    this.typeVariableSource = typeVariableSource;
                }

                @Override
                public GenericTypeDescription get(int index) {
                    return new TokenizedGenericType(typePool, genericTypeTokens.get(index), rawTypeDescriptors.get(index), typeVariableSource);
                }

                @Override
                public int size() {
                    return rawTypeDescriptors.size();
                }

                @Override
                public TypeList asRawTypes() {
                    return LazyTypeList.of(typePool, rawTypeDescriptors);
                }
            }

            protected static class TypeVariableList extends GenericTypeList.AbstractBase {

                protected static GenericTypeList of(TypePool typePool,
                                                    List<GenericTypeToken> typeVariables,
                                                    TypeVariableSource typeVariableSource) {
                    return typeVariables.isEmpty()
                            ? new GenericTypeList.Empty()
                            : new TypeVariableList(typePool, typeVariables, typeVariableSource);
                }

                private final TypePool typePool;

                private final List<GenericTypeToken> typeVariables;

                private final TypeVariableSource typeVariableSource;

                private TypeVariableList(TypePool typePool,
                                         List<GenericTypeToken> typeVariables,
                                         TypeVariableSource typeVariableSource) {
                    this.typePool = typePool;
                    this.typeVariables = typeVariables;
                    this.typeVariableSource = typeVariableSource;
                }

                @Override
                public GenericTypeDescription get(int index) {
                    return typeVariables.get(index).toGenericType(typePool, typeVariableSource);
                }

                @Override
                public int size() {
                    return typeVariables.size();
                }

                @Override
                public TypeList asRawTypes() {
                    List<TypeDescription> typeDescriptions = new ArrayList<TypeDescription>();
                    for (GenericTypeDescription typeVariable : this) {
                        typeDescriptions.add(typeVariable.asRawType());
                    }
                    return new TypeList.Explicit(typeDescriptions);
                }
            }

            protected static class Defective extends GenericTypeDescription.LazyProjection {

                private final TypePool typePool;

                private final String rawTypeDescriptor;

                protected Defective(TypePool typePool, String rawTypeDescriptor) {
                    this.typePool = typePool;
                    this.rawTypeDescriptor = rawTypeDescriptor;
                }

                @Override
                protected GenericTypeDescription resolve() {
                    throw new MalformedParameterizedTypeException();
                }

                @Override
                public TypeDescription asRawType() {
                    return toRawType(typePool, rawTypeDescriptor);
                }

                protected static class TokenList extends GenericTypeList.AbstractBase {

                    private final TypePool typePool;

                    private final List<String> rawTypeDescriptors;

                    private TokenList(TypePool typePool, List<String> rawTypeDescriptors) {
                        this.typePool = typePool;
                        this.rawTypeDescriptors = rawTypeDescriptors;
                    }

                    @Override
                    public GenericTypeDescription get(int index) {
                        return new TokenizedGenericType.Defective(typePool, rawTypeDescriptors.get(index));
                    }

                    @Override
                    public int size() {
                        return rawTypeDescriptors.size();
                    }

                    @Override
                    public TypeList asRawTypes() {
                        return LazyTypeList.of(typePool, rawTypeDescriptors);
                    }
                }

            }
        }
    }
}


File: byte-buddy-dep/src/test/java/net/bytebuddy/description/type/generic/AbstractGenericTypeDescriptionTest.java
package net.bytebuddy.description.type.generic;

import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.type.TypeDescription;
import org.junit.Test;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.List;

import static net.bytebuddy.matcher.ElementMatchers.named;
import static org.hamcrest.CoreMatchers.sameInstance;
import static org.junit.Assert.fail;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.CoreMatchers.nullValue;
import static org.hamcrest.MatcherAssert.assertThat;

public abstract class AbstractGenericTypeDescriptionTest {

    private static final String FOO = "foo", BAR = "bar", QUX = "qux", BAZ = "baz";

    private static final String T = "T", S = "S", U = "U", V = "V";

    protected abstract GenericTypeDescription describe(Field field);

    protected abstract GenericTypeDescription describe(Method method);

    @Test
    public void testSimpleParameterizedType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(SimpleParameterizedType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getParameters().size(), is(1));
        assertThat(genericTypeDescription.getParameters().getOnly().getSort(), is(GenericTypeDescription.Sort.RAW));
        assertThat(genericTypeDescription.getParameters().getOnly().asRawType().represents(String.class), is(true));
        assertThat(genericTypeDescription.getTypeName(), is(SimpleParameterizedType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getComponentType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(), nullValue(TypeVariableSource.class));
        assertThat(genericTypeDescription.getSymbol(), nullValue(String.class));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(0));
    }

    @Test
    public void testUpperBoundWildcardParameterizedType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(UpperBoundWildcardParameterizedType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getParameters().size(), is(1));
        assertThat(genericTypeDescription.getParameters().getOnly().getSort(), is(GenericTypeDescription.Sort.WILDCARD));
        try {
            genericTypeDescription.getParameters().getOnly().asRawType();
            fail();
        } catch (IllegalStateException ignored) {
            /* expected */
        }
        assertThat(genericTypeDescription.getParameters().getOnly().getUpperBounds().size(), is(1));
        assertThat(genericTypeDescription.getParameters().getOnly().getUpperBounds().getOnly().getSort(), is(GenericTypeDescription.Sort.RAW));
        assertThat(genericTypeDescription.getParameters().getOnly().getUpperBounds().getOnly().asRawType().represents(String.class), is(true));
        assertThat(genericTypeDescription.getParameters().getOnly().getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getTypeName(), is(UpperBoundWildcardParameterizedType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getComponentType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(), nullValue(TypeVariableSource.class));
        assertThat(genericTypeDescription.getSymbol(), nullValue(String.class));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(0));
    }

    @Test
    public void testLowerBoundWildcardParameterizedType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(LowerBoundWildcardParameterizedType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getParameters().size(), is(1));
        assertThat(genericTypeDescription.getParameters().getOnly().getSort(), is(GenericTypeDescription.Sort.WILDCARD));
        try {
            genericTypeDescription.getParameters().getOnly().asRawType();
            fail();
        } catch (IllegalStateException ignored) {
            /* expected */
        }
        assertThat(genericTypeDescription.getParameters().getOnly().getUpperBounds().size(), is(1));
        assertThat(genericTypeDescription.getParameters().getOnly().getUpperBounds().getOnly().getSort(), is(GenericTypeDescription.Sort.RAW));
        try {
            genericTypeDescription.getParameters().getOnly().asRawType();
            fail();
        } catch (IllegalStateException ignored) {
            /* expected */
        }
        assertThat(genericTypeDescription.getParameters().getOnly().getLowerBounds().size(), is(1));
        assertThat(genericTypeDescription.getParameters().getOnly().getLowerBounds().getOnly().getSort(), is(GenericTypeDescription.Sort.RAW));
        assertThat(genericTypeDescription.getParameters().getOnly().getLowerBounds().getOnly().asRawType().represents(String.class), is(true));
        assertThat(genericTypeDescription.getTypeName(), is(LowerBoundWildcardParameterizedType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getComponentType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(), nullValue(TypeVariableSource.class));
        assertThat(genericTypeDescription.getSymbol(), nullValue(String.class));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(0));
    }

    @Test
    public void testGenericArrayType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(GenericArrayType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.GENERIC_ARRAY));
        assertThat(genericTypeDescription.getComponentType().getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getComponentType().getParameters().size(), is(1));
        assertThat(genericTypeDescription.getComponentType().getParameters().getOnly().getSort(), is(GenericTypeDescription.Sort.RAW));
        assertThat(genericTypeDescription.getComponentType().getParameters().getOnly().asRawType().represents(String.class), is(true));
        assertThat(genericTypeDescription.getTypeName(), is(GenericArrayType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(), nullValue(TypeVariableSource.class));
        assertThat(genericTypeDescription.getSymbol(), nullValue(String.class));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(0));
    }

    @Test
    public void testTypeVariableType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(SimpleTypeVariableType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(genericTypeDescription.getSymbol(), is(T));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(1));
        assertThat(genericTypeDescription.getUpperBounds().getOnly(), is((GenericTypeDescription) TypeDescription.OBJECT));
        assertThat(genericTypeDescription.getTypeName(), is(SimpleTypeVariableType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getComponentType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(), is((TypeVariableSource) new TypeDescription.ForLoadedType(SimpleTypeVariableType.class)));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().size(), is(1));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().getOnly(), is(genericTypeDescription));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
    }

    @Test
    public void testSingleUpperBoundTypeVariableType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(SingleUpperBoundTypeVariableType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(genericTypeDescription.getSymbol(), is(T));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(1));
        assertThat(genericTypeDescription.getUpperBounds().getOnly(), is((GenericTypeDescription) TypeDescription.STRING));
        assertThat(genericTypeDescription.getTypeName(), is(SingleUpperBoundTypeVariableType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getComponentType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(),
                is((TypeVariableSource) new TypeDescription.ForLoadedType(SingleUpperBoundTypeVariableType.class)));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().size(), is(1));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().getOnly(), is(genericTypeDescription));
    }

    @Test
    public void testMultipleUpperBoundTypeVariableType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(MultipleUpperBoundTypeVariableType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(genericTypeDescription.getSymbol(), is(T));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(3));
        assertThat(genericTypeDescription.getUpperBounds().get(0), is((GenericTypeDescription) TypeDescription.STRING));
        assertThat(genericTypeDescription.getUpperBounds().get(1), is((GenericTypeDescription) new TypeDescription.ForLoadedType(Foo.class)));
        assertThat(genericTypeDescription.getUpperBounds().get(2), is((GenericTypeDescription) new TypeDescription.ForLoadedType(Bar.class)));
        assertThat(genericTypeDescription.getTypeName(), is(MultipleUpperBoundTypeVariableType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getComponentType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(),
                is((TypeVariableSource) new TypeDescription.ForLoadedType(MultipleUpperBoundTypeVariableType.class)));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().size(), is(1));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().getOnly(), is(genericTypeDescription));
    }

    @Test
    public void testInterfaceOnlyMultipleUpperBoundTypeVariableType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(InterfaceOnlyMultipleUpperBoundTypeVariableType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(genericTypeDescription.getSymbol(), is(T));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(2));
        assertThat(genericTypeDescription.getUpperBounds().get(0), is((GenericTypeDescription) new TypeDescription.ForLoadedType(Foo.class)));
        assertThat(genericTypeDescription.getUpperBounds().get(1), is((GenericTypeDescription) new TypeDescription.ForLoadedType(Bar.class)));
        assertThat(genericTypeDescription.getTypeName(),
                is(InterfaceOnlyMultipleUpperBoundTypeVariableType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getComponentType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(),
                is((TypeVariableSource) new TypeDescription.ForLoadedType(InterfaceOnlyMultipleUpperBoundTypeVariableType.class)));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().size(), is(1));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().getOnly(), is(genericTypeDescription));
    }

    @Test
    public void testShadowedTypeVariableType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(ShadowingTypeVariableType.class.getDeclaredMethod(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(genericTypeDescription.getSymbol(), is(T));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(1));
        assertThat(genericTypeDescription.getUpperBounds().getOnly(), is((GenericTypeDescription) TypeDescription.OBJECT));
        assertThat(genericTypeDescription.getTypeName(), is(ShadowingTypeVariableType.class.getDeclaredMethod(FOO).getGenericReturnType().toString()));
        assertThat(genericTypeDescription.getComponentType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getOwnerType(), nullValue(GenericTypeDescription.class));
        assertThat(genericTypeDescription.getVariableSource(),
                is((TypeVariableSource) new MethodDescription.ForLoadedMethod(ShadowingTypeVariableType.class.getDeclaredMethod(FOO))));
        assertThat(genericTypeDescription.getLowerBounds().size(), is(0));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().size(), is(1));
        assertThat(genericTypeDescription.getVariableSource().getTypeVariables().getOnly(), is(genericTypeDescription));
    }

    @Test
    public void testNestedTypeVariableType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(NestedTypeVariableType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getTypeName(), is(NestedTypeVariableType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getParameters().size(), is(0));
        Type ownerType = ((ParameterizedType) NestedTypeVariableType.class.getDeclaredField(FOO).getGenericType()).getOwnerType();
        assertThat(genericTypeDescription.getOwnerType(), is(GenericTypeDescription.Sort.describe(ownerType)));
        assertThat(genericTypeDescription.getOwnerType().getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getOwnerType().getParameters().size(), is(1));
        assertThat(genericTypeDescription.getOwnerType().getParameters().getOnly().getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(genericTypeDescription.getOwnerType().getParameters().getOnly().getSymbol(), is(T));
    }

    @Test
    public void testNestedSpecifiedTypeVariableType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(NestedSpecifiedTypeVariableType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getTypeName(), is(NestedSpecifiedTypeVariableType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getParameters().size(), is(0));
        Type ownerType = ((ParameterizedType) NestedSpecifiedTypeVariableType.class.getDeclaredField(FOO).getGenericType()).getOwnerType();
        assertThat(genericTypeDescription.getOwnerType(), is(GenericTypeDescription.Sort.describe(ownerType)));
        assertThat(genericTypeDescription.getOwnerType().getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getOwnerType().getParameters().size(), is(1));
        assertThat(genericTypeDescription.getOwnerType().getParameters().getOnly().getSort(), is(GenericTypeDescription.Sort.RAW));
        assertThat(genericTypeDescription.getOwnerType().getParameters().getOnly(), is((GenericTypeDescription) TypeDescription.STRING));
    }

    @Test
    public void testNestedStaticTypeVariableType() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(NestedStaticTypeVariableType.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getTypeName(), is(NestedStaticTypeVariableType.class.getDeclaredField(FOO).getGenericType().toString()));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(genericTypeDescription.getParameters().size(), is(1));
        assertThat(genericTypeDescription.getParameters().getOnly(), is((GenericTypeDescription) TypeDescription.STRING));
        Type ownerType = ((ParameterizedType) NestedStaticTypeVariableType.class.getDeclaredField(FOO).getGenericType()).getOwnerType();
        assertThat(genericTypeDescription.getOwnerType(), is(GenericTypeDescription.Sort.describe(ownerType)));
        assertThat(genericTypeDescription.getOwnerType().getSort(), is(GenericTypeDescription.Sort.RAW));
    }

    @Test
    public void testNestedInnerType() throws Exception {
        GenericTypeDescription foo = describe(NestedInnerType.InnerType.class.getDeclaredMethod(FOO));
        assertThat(foo.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(foo.getSymbol(), is(T));
        assertThat(foo.getUpperBounds().size(), is(1));
        assertThat(foo.getUpperBounds().getOnly(), is((GenericTypeDescription) TypeDescription.OBJECT));
        assertThat(foo.getVariableSource(), is((TypeVariableSource) new TypeDescription.ForLoadedType(NestedInnerType.class)));
        GenericTypeDescription bar = describe(NestedInnerType.InnerType.class.getDeclaredMethod(BAR));
        assertThat(bar.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(bar.getSymbol(), is(S));
        assertThat(bar.getUpperBounds().size(), is(1));
        assertThat(bar.getUpperBounds().getOnly(), is(foo));
        assertThat(bar.getVariableSource(), is((TypeVariableSource) new TypeDescription.ForLoadedType(NestedInnerType.InnerType.class)));
        GenericTypeDescription qux = describe(NestedInnerType.InnerType.class.getDeclaredMethod(QUX));
        assertThat(qux.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(qux.getSymbol(), is(U));
        assertThat(qux.getUpperBounds().size(), is(1));
        assertThat(qux.getUpperBounds().getOnly(), is(foo));
        MethodDescription quxMethod = new MethodDescription.ForLoadedMethod(NestedInnerType.InnerType.class.getDeclaredMethod(QUX));
        assertThat(qux.getVariableSource(), is((TypeVariableSource) quxMethod));
    }

    @Test
    public void testNestedInnerMethod() throws Exception {
        Class<?> innerType = new NestedInnerMethod().foo();
        GenericTypeDescription foo = describe(innerType.getDeclaredMethod(FOO));
        assertThat(foo.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(foo.getSymbol(), is(T));
        assertThat(foo.getUpperBounds().size(), is(1));
        assertThat(foo.getUpperBounds().getOnly(), is((GenericTypeDescription) TypeDescription.OBJECT));
        assertThat(foo.getVariableSource(), is((TypeVariableSource) new TypeDescription.ForLoadedType(NestedInnerMethod.class)));
        GenericTypeDescription bar = describe(innerType.getDeclaredMethod(BAR));
        assertThat(bar.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(bar.getSymbol(), is(S));
        assertThat(bar.getUpperBounds().size(), is(1));
        assertThat(bar.getUpperBounds().getOnly(), is(foo));
        assertThat(bar.getVariableSource(), is((TypeVariableSource) new MethodDescription.ForLoadedMethod(NestedInnerMethod.class.getDeclaredMethod(FOO))));
        GenericTypeDescription qux = describe(innerType.getDeclaredMethod(QUX));
        assertThat(qux.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(qux.getSymbol(), is(U));
        assertThat(qux.getUpperBounds().size(), is(1));
        assertThat(qux.getUpperBounds().getOnly(), is(bar));
        assertThat(qux.getVariableSource(), is((TypeVariableSource) new TypeDescription.ForLoadedType(innerType)));
        GenericTypeDescription baz = describe(innerType.getDeclaredMethod(BAZ));
        assertThat(baz.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(baz.getSymbol(), is(V));
        assertThat(baz.getUpperBounds().size(), is(1));
        assertThat(baz.getUpperBounds().getOnly(), is(qux));
        assertThat(baz.getVariableSource(), is((TypeVariableSource) new MethodDescription.ForLoadedMethod(innerType.getDeclaredMethod(BAZ))));

    }

    @Test
    public void testRecursiveTypeVariable() throws Exception {
        GenericTypeDescription genericTypeDescription = describe(RecursiveTypeVariable.class.getDeclaredField(FOO));
        assertThat(genericTypeDescription.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(genericTypeDescription.getSymbol(), is(T));
        assertThat(genericTypeDescription.getUpperBounds().size(), is(1));
        GenericTypeDescription upperBound = genericTypeDescription.getUpperBounds().getOnly();
        assertThat(upperBound.getSort(), is(GenericTypeDescription.Sort.PARAMETERIZED));
        assertThat(upperBound.asRawType(), is((GenericTypeDescription) genericTypeDescription.asRawType()));
        assertThat(upperBound.getParameters().size(), is(1));
        assertThat(upperBound.getParameters().getOnly(), is(genericTypeDescription));
    }

    @Test
    public void testBackwardsReferenceTypeVariable() throws Exception {
        GenericTypeDescription foo = describe(BackwardsReferenceTypeVariable.class.getDeclaredField(FOO));
        assertThat(foo.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(foo.getSymbol(), is(S));
        assertThat(foo.getUpperBounds().size(), is(1));
        TypeDescription backwardsReference = new TypeDescription.ForLoadedType(BackwardsReferenceTypeVariable.class);
        assertThat(foo.getUpperBounds().getOnly(), is(backwardsReference.getTypeVariables().filter(named(T)).getOnly()));
        GenericTypeDescription bar = describe(BackwardsReferenceTypeVariable.class.getDeclaredField(BAR));
        assertThat(bar.getSort(), is(GenericTypeDescription.Sort.VARIABLE));
        assertThat(bar.getSymbol(), is(T));
        assertThat(bar.getUpperBounds().size(), is(1));
        assertThat(bar.getUpperBounds().getOnly(), is((GenericTypeDescription) TypeDescription.OBJECT));
    }

    @SuppressWarnings("unused")
    public static class SimpleParameterizedType {

        List<String> foo;
    }

    @SuppressWarnings("unused")
    public static class UpperBoundWildcardParameterizedType {

        List<? extends String> foo;
    }

    @SuppressWarnings("unused")
    public static class LowerBoundWildcardParameterizedType {

        List<? super String> foo;
    }

    @SuppressWarnings("unused")
    public static class GenericArrayType {

        List<String>[] foo;
    }

    @SuppressWarnings("unused")
    public static class SimpleTypeVariableType<T> {

        T foo;
    }

    @SuppressWarnings("unused")
    public static class SingleUpperBoundTypeVariableType<T extends String> {

        T foo;
    }

    @SuppressWarnings("unused")
    public static class MultipleUpperBoundTypeVariableType<T extends String & Foo & Bar> {

        T foo;
    }

    @SuppressWarnings("unused")
    public static class InterfaceOnlyMultipleUpperBoundTypeVariableType<T extends Foo & Bar> {

        T foo;
    }

    @SuppressWarnings("unused")
    public static class ShadowingTypeVariableType<T> {

        @SuppressWarnings("all")
        <T> T foo() {
            return null;
        }
    }

    @SuppressWarnings("unused")
    public static class NestedTypeVariableType<T> {

        class Placeholder {
            /* empty */
        }

        Placeholder foo;
    }

    @SuppressWarnings("unused")
    public static class NestedSpecifiedTypeVariableType<T> {

        class Placeholder {
            /* empty */
        }

        NestedSpecifiedTypeVariableType<String>.Placeholder foo;
    }

    @SuppressWarnings("unused")
    public static class NestedStaticTypeVariableType<T> {

        static class Placeholder<S> {
            /* empty */
        }

        NestedStaticTypeVariableType.Placeholder<String> foo;
    }

    @SuppressWarnings("unused")
    public static class NestedInnerType<T> {

        class InnerType<S extends T> {

            <U extends S> T foo() {
                return null;
            }

            <U extends S> S bar() {
                return null;
            }

            <U extends S> U qux() {
                return null;
            }
        }
    }

    @SuppressWarnings("unused")
    public static class NestedInnerMethod<T> {

        <S extends T> Class<?> foo() {
            class InnerType<U extends S> {

                <V extends U> T foo() {
                    return null;
                }

                <V extends U> S bar() {
                    return null;
                }

                <V extends U> U qux() {
                    return null;
                }

                <V extends U> V baz() {
                    return null;
                }
            }
            return InnerType.class;
        }
    }

    @SuppressWarnings("unused")
    public static class RecursiveTypeVariable<T extends RecursiveTypeVariable<T>> {

        T foo;
    }

    @SuppressWarnings("unused")
    public static class BackwardsReferenceTypeVariable<T, S extends T> {

        S foo;

        T bar;
    }

    @SuppressWarnings("unused")
    public interface Foo {
        /* empty */
    }

    @SuppressWarnings("unused")
    public interface Bar {
        /* empty */
    }
}


File: byte-buddy-dep/src/test/java/net/bytebuddy/dynamic/DynamicTypeBuilderTokenTest.java
package net.bytebuddy.dynamic;

import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.TypeList;
import net.bytebuddy.test.utility.MockitoRule;
import net.bytebuddy.test.utility.ObjectPropertyAssertion;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TestRule;
import org.mockito.Mock;

import java.util.Collections;
import java.util.List;

import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.CoreMatchers.not;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class DynamicTypeBuilderTokenTest {

    private static final String FOO = "foo", BAR = "bar";

    private static final int QUX = 42, BAZ = QUX * 2;

    @Rule
    public TestRule mockitoRule = new MockitoRule(this);

    @Mock
    private TypeDescription singleType, parameterType, exceptionType;

    private TypeList parameterTypes, exceptionTypes;

    @Before
    public void setUp() throws Exception {
        parameterTypes = new TypeList.Explicit(Collections.singletonList(parameterType));
        exceptionTypes = new TypeList.Explicit(Collections.singletonList(exceptionType));
    }

    @Test
    public void testMethodTokenHashCode() throws Exception {
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX).hashCode(),
                is(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX).hashCode()));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX).hashCode(),
                not(is(new DynamicType.Builder.AbstractBase.MethodToken(BAR, singleType, parameterTypes, exceptionTypes, QUX).hashCode())));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX).hashCode(),
                not(is(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, new TypeList.Empty(), exceptionTypes, QUX).hashCode())));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX).hashCode(),
                not(is(new DynamicType.Builder.AbstractBase.MethodToken(FOO, mock(TypeDescription.class), parameterTypes, exceptionTypes, QUX).hashCode())));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX).hashCode(),
                is(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, BAZ).hashCode()));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX).hashCode(),
                is(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, new TypeList.Empty(), QUX).hashCode()));
    }

    @Test
    public void testMethodTokenEquals() throws Exception {
        DynamicType.Builder.AbstractBase.MethodToken equal = mock(DynamicType.Builder.AbstractBase.MethodToken.class);
        when(equal.getInternalName()).thenReturn(FOO);
        when(equal.getReturnType()).thenReturn(singleType);
        when(equal.getParameterTypes()).thenReturn(parameterTypes);
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX),
                is(equal));
        DynamicType.Builder.AbstractBase.MethodToken equalButName = mock(DynamicType.Builder.AbstractBase.MethodToken.class);
        when(equalButName.getInternalName()).thenReturn(BAR);
        when(equalButName.getReturnType()).thenReturn(singleType);
        when(equalButName.getParameterTypes()).thenReturn(parameterTypes);
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX),
                not(is(equalButName)));
        DynamicType.Builder.AbstractBase.MethodToken equalButReturnType = mock(DynamicType.Builder.AbstractBase.MethodToken.class);
        when(equalButReturnType.getInternalName()).thenReturn(BAR);
        when(equalButReturnType.getReturnType()).thenReturn(mock(TypeDescription.class));
        when(equalButReturnType.getParameterTypes()).thenReturn(parameterTypes);
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX),
                not(is(equalButReturnType)));
        DynamicType.Builder.AbstractBase.MethodToken equalButParameterType = mock(DynamicType.Builder.AbstractBase.MethodToken.class);
        when(equalButParameterType.getInternalName()).thenReturn(BAR);
        when(equalButParameterType.getReturnType()).thenReturn(singleType);
        when(equalButParameterType.getParameterTypes()).thenReturn(new TypeList.Empty());
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX),
                not(is(equalButParameterType)));
    }

    @Test
    @SuppressWarnings("unchecked")
    public void testMethodTokenSubstitute() throws Exception {
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, TargetType.DESCRIPTION, parameterTypes, exceptionTypes, QUX)
                .resolveReturnType(singleType), is(singleType));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, new TypeList.ForLoadedType(TargetType.class), QUX)
                .resolveExceptionTypes(singleType), is((List<TypeDescription>) new TypeList.Explicit(Collections.singletonList(singleType))));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, new TypeList.ForLoadedType(TargetType.class), exceptionTypes, QUX)
                .resolveParameterTypes(singleType), is((List<TypeDescription>) new TypeList.Explicit(Collections.singletonList(singleType))));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX)
                .resolveReturnType(mock(TypeDescription.class)), is(singleType));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX)
                .resolveExceptionTypes(mock(TypeDescription.class)), is((List<TypeDescription>) exceptionTypes));
        assertThat(new DynamicType.Builder.AbstractBase.MethodToken(FOO, singleType, parameterTypes, exceptionTypes, QUX)
                .resolveParameterTypes(mock(TypeDescription.class)), is((List<TypeDescription>) parameterTypes));
    }

    @Test
    public void testFieldTokenHashCode() throws Exception {
        assertThat(new DynamicType.Builder.AbstractBase.FieldToken(FOO, singleType, QUX).hashCode(),
                is(new DynamicType.Builder.AbstractBase.FieldToken(FOO, singleType, QUX).hashCode()));
        assertThat(new DynamicType.Builder.AbstractBase.FieldToken(FOO, singleType, QUX).hashCode(),
                not(is(new DynamicType.Builder.AbstractBase.FieldToken(BAR, singleType, QUX).hashCode())));
        assertThat(new DynamicType.Builder.AbstractBase.FieldToken(FOO, singleType, QUX).hashCode(),
                is(new DynamicType.Builder.AbstractBase.FieldToken(FOO, mock(TypeDescription.class), QUX).hashCode()));
        assertThat(new DynamicType.Builder.AbstractBase.FieldToken(FOO, singleType, QUX).hashCode(),
                is(new DynamicType.Builder.AbstractBase.FieldToken(FOO, singleType, BAZ).hashCode()));
    }

    @Test
    public void testFieldTokenEquals() throws Exception {
        DynamicType.Builder.AbstractBase.FieldToken equal = mock(DynamicType.Builder.AbstractBase.FieldToken.class);
        when(equal.getFieldName()).thenReturn(FOO);
        assertThat(new DynamicType.Builder.AbstractBase.FieldToken(FOO, singleType, QUX), is(equal));
        DynamicType.Builder.AbstractBase.FieldToken equalButName = mock(DynamicType.Builder.AbstractBase.FieldToken.class);
        when(equalButName.getFieldName()).thenReturn(BAR);
    }

    @Test
    public void testFieldTokenSubstitute() throws Exception {
        assertThat(new DynamicType.Builder.AbstractBase.FieldToken(FOO, TargetType.DESCRIPTION, QUX)
                .resolveFieldType(singleType), is(singleType));
        assertThat(new DynamicType.Builder.AbstractBase.FieldToken(FOO, singleType, QUX)
                .resolveFieldType(mock(TypeDescription.class)), is(singleType));
    }

    @Test
    public void testObjectProperties() throws Exception {
        ObjectPropertyAssertion.of(DynamicType.Builder.AbstractBase.FieldToken.class).applyMutable();
        ObjectPropertyAssertion.of(DynamicType.Builder.AbstractBase.MethodToken.class).create(new ObjectPropertyAssertion.Creator<TypeList>() {
            @Override
            public TypeList create() {
                return new TypeList.Explicit(Collections.singletonList(mock(TypeDescription.class)));
            }
        }).applyMutable();
    }
}


File: byte-buddy-dep/src/test/java/net/bytebuddy/dynamic/TargetTypeTest.java
package net.bytebuddy.dynamic;

import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.matcher.ElementMatchers;
import org.junit.Before;
import org.junit.Test;

import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.CoreMatchers.sameInstance;
import static org.hamcrest.MatcherAssert.assertThat;

public class TargetTypeTest {

    private TypeDescription originalType, substitute;

    @Before
    public void setUp() throws Exception {
        originalType = new TypeDescription.ForLoadedType(OriginalType.class);
        substitute = new TypeDescription.ForLoadedType(Substitute.class);
    }

    @Test
    public void testSimpleResolution() throws Exception {
        assertThat(TargetType.resolve(originalType, substitute, ElementMatchers.is(originalType)), is(substitute));
    }

    @Test
    public void testSimpleSkippedResolution() throws Exception {
        assertThat(TargetType.resolve(originalType, substitute, ElementMatchers.none()), sameInstance(originalType));
    }

    @Test
    public void testArrayResolution() throws Exception {
        TypeDescription arrayType = TypeDescription.ArrayProjection.of(originalType, 2);
        assertThat(TargetType.resolve(arrayType, substitute, ElementMatchers.is(originalType)), is(TypeDescription.ArrayProjection.of(substitute, 2)));
    }

    @Test
    public void testArraySkippedResolution() throws Exception {
        TypeDescription arrayType = TypeDescription.ArrayProjection.of(originalType, 2);
        assertThat(TargetType.resolve(arrayType, substitute, ElementMatchers.none()), sameInstance(arrayType));
    }

    // TODO: Generic types!

    public static class OriginalType {
        /* empty */
    }

    public static class Substitute {
        /* empty */
    }
}


File: byte-buddy-dep/src/test/java/net/bytebuddy/dynamic/scaffold/AbstractInstrumentedTypeTest.java
package net.bytebuddy.dynamic.scaffold;

import net.bytebuddy.description.field.FieldDescription;
import net.bytebuddy.description.method.MethodDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.TypeList;
import net.bytebuddy.description.type.generic.GenericTypeDescription;
import net.bytebuddy.implementation.Implementation;
import net.bytebuddy.implementation.LoadedTypeInitializer;
import net.bytebuddy.implementation.bytecode.ByteCodeAppender;
import net.bytebuddy.implementation.bytecode.StackSize;
import net.bytebuddy.test.utility.MockitoRule;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TestRule;
import org.mockito.Mock;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

import java.io.Serializable;
import java.util.Collections;

import static org.hamcrest.CoreMatchers.*;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.core.IsNot.not;
import static org.mockito.Mockito.*;

public abstract class AbstractInstrumentedTypeTest {

    private static final String FOO = "foo", BAR = "bar", QUX = "qux", BAZ = "baz";

    @Rule
    public TestRule mockitoRule = new MockitoRule(this);

    @Mock
    private MethodVisitor methodVisitor;

    @Mock
    private Implementation.Context implementationContext;

    protected abstract InstrumentedType makePlainInstrumentedType();

    @Test
    public void testWithField() throws Exception {
        TypeDescription fieldType = mock(TypeDescription.class);
        when(fieldType.asRawType()).thenReturn(fieldType); // REFACTOR
        when(fieldType.getName()).thenReturn(FOO);
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        instrumentedType = instrumentedType.withField(BAR, fieldType, Opcodes.ACC_PUBLIC);
        assertThat(instrumentedType.getDeclaredFields().size(), is(1));
        FieldDescription fieldDescription = instrumentedType.getDeclaredFields().get(0);
        assertThat(fieldDescription.getFieldType(), is(fieldType));
        assertThat(fieldDescription.getModifiers(), is(Opcodes.ACC_PUBLIC));
        assertThat(fieldDescription.getName(), is(BAR));
        assertThat(fieldDescription.getDeclaringType(), sameInstance((TypeDescription) instrumentedType));
    }

    @Test
    public void testWithFieldOfInstrumentedType() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        instrumentedType = instrumentedType.withField(BAR, instrumentedType, Opcodes.ACC_PUBLIC);
        assertThat(instrumentedType.getDeclaredFields().size(), is(1));
        FieldDescription fieldDescription = instrumentedType.getDeclaredFields().get(0);
        assertThat(fieldDescription.getFieldType(), sameInstance((TypeDescription) instrumentedType));
        assertThat(fieldDescription.getModifiers(), is(Opcodes.ACC_PUBLIC));
        assertThat(fieldDescription.getName(), is(BAR));
        assertThat(fieldDescription.getDeclaringType(), sameInstance((TypeDescription) instrumentedType));
    }

    @Test
    public void testWithFieldOfInstrumentedTypeAsArray() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        instrumentedType = instrumentedType.withField(BAR, TypeDescription.ArrayProjection.of(instrumentedType, 1), Opcodes.ACC_PUBLIC);
        assertThat(instrumentedType.getDeclaredFields().size(), is(1));
        FieldDescription fieldDescription = instrumentedType.getDeclaredFields().get(0);
        assertThat(fieldDescription.getFieldType().isArray(), is(true));
        assertThat(fieldDescription.getFieldType().getComponentType(), sameInstance((TypeDescription) instrumentedType));
        assertThat(fieldDescription.getModifiers(), is(Opcodes.ACC_PUBLIC));
        assertThat(fieldDescription.getName(), is(BAR));
        assertThat(fieldDescription.getDeclaringType(), sameInstance((TypeDescription) instrumentedType));
    }

    @Test(expected = IllegalArgumentException.class)
    public void testWithFieldDouble() throws Exception {
        TypeDescription fieldType = mock(TypeDescription.class);
        when(fieldType.asRawType()).thenReturn(fieldType); // REFACTOR
        when(fieldType.getName()).thenReturn(FOO);
        makePlainInstrumentedType()
                .withField(BAR, fieldType, Opcodes.ACC_PUBLIC)
                .withField(BAR, fieldType, Opcodes.ACC_PUBLIC);
    }

    @Test
    public void testWithMethod() throws Exception {
        TypeDescription returnType = mock(TypeDescription.class);
        when(returnType.asRawType()).thenReturn(returnType); // REFACTOR
        TypeDescription parameterType = mock(TypeDescription.class);
        when(parameterType.asRawType()).thenReturn(parameterType); // REFACTOR
        TypeDescription exceptionType = mock(TypeDescription.class);
        when(exceptionType.asRawType()).thenReturn(exceptionType); // REFACTOR
        when(returnType.getName()).thenReturn(FOO);
        when(parameterType.getName()).thenReturn(QUX);
        when(parameterType.getStackSize()).thenReturn(StackSize.ZERO);
        when(exceptionType.getName()).thenReturn(BAZ);
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        instrumentedType = instrumentedType.withMethod(BAR,
                returnType,
                Collections.singletonList(parameterType),
                Collections.singletonList(exceptionType),
                Opcodes.ACC_PUBLIC);
        assertThat(instrumentedType.getDeclaredMethods().size(), is(1));
        MethodDescription methodDescription = instrumentedType.getDeclaredMethods().get(0);
        assertThat(methodDescription.getReturnType(), is(returnType));
        assertThat(methodDescription.getParameters().size(), is(1));
        assertThat(methodDescription.getParameters().asTypeList(), is(Collections.singletonList(parameterType)));
        assertThat(methodDescription.getExceptionTypes().size(), is(1));
        assertThat(methodDescription.getExceptionTypes(), is(Collections.singletonList(exceptionType)));
        assertThat(methodDescription.getModifiers(), is(Opcodes.ACC_PUBLIC));
        assertThat(methodDescription.getName(), is(BAR));
        assertThat(methodDescription.getDeclaringType(), sameInstance((TypeDescription) instrumentedType));
    }

    @Test
    public void testWithMethodOfInstrumentedType() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        instrumentedType = instrumentedType.withMethod(BAR,
                instrumentedType,
                Collections.singletonList(instrumentedType),
                Collections.<TypeDescription>emptyList(),
                Opcodes.ACC_PUBLIC);
        assertThat(instrumentedType.getDeclaredMethods().size(), is(1));
        MethodDescription methodDescription = instrumentedType.getDeclaredMethods().get(0);
        assertThat(methodDescription.getReturnType(), sameInstance((TypeDescription) instrumentedType));
        assertThat(methodDescription.getParameters().size(), is(1));
        assertThat(methodDescription.getParameters().asTypeList().get(0), sameInstance((TypeDescription) instrumentedType));
        assertThat(methodDescription.getExceptionTypes().size(), is(0));
        assertThat(methodDescription.getModifiers(), is(Opcodes.ACC_PUBLIC));
        assertThat(methodDescription.getName(), is(BAR));
        assertThat(methodDescription.getDeclaringType(), sameInstance((TypeDescription) instrumentedType));
    }

    @Test
    public void testWithMethodOfInstrumentedTypeAsArray() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        instrumentedType = instrumentedType.withMethod(BAR,
                TypeDescription.ArrayProjection.of(instrumentedType, 1),
                Collections.singletonList(TypeDescription.ArrayProjection.of(instrumentedType, 1)),
                Collections.<TypeDescription>emptyList(),
                Opcodes.ACC_PUBLIC);
        assertThat(instrumentedType.getDeclaredMethods().size(), is(1));
        MethodDescription methodDescription = instrumentedType.getDeclaredMethods().get(0);
        assertThat(methodDescription.getReturnType().isArray(), is(true));
        assertThat(methodDescription.getReturnType().getComponentType(), sameInstance((TypeDescription) instrumentedType));
        assertThat(methodDescription.getParameters().size(), is(1));
        assertThat(methodDescription.getParameters().asTypeList().get(0).isArray(), is(true));
        assertThat(methodDescription.getParameters().asTypeList().get(0).getComponentType(), sameInstance((TypeDescription) instrumentedType));
        assertThat(methodDescription.getExceptionTypes().size(), is(0));
        assertThat(methodDescription.getModifiers(), is(Opcodes.ACC_PUBLIC));
        assertThat(methodDescription.getName(), is(BAR));
        assertThat(methodDescription.getDeclaringType(), sameInstance((TypeDescription) instrumentedType));
    }

    @Test(expected = IllegalArgumentException.class)
    public void testWithMethodDouble() throws Exception {
        TypeDescription returnType = mock(TypeDescription.class);
        when(returnType.asRawType()).thenReturn(returnType); // REFACTOR
        when(returnType.getName()).thenReturn(FOO);
        makePlainInstrumentedType()
                .withMethod(BAR, returnType, Collections.<TypeDescription>emptyList(), Collections.<TypeDescription>emptyList(), Opcodes.ACC_PUBLIC)
                .withMethod(BAR, returnType, Collections.<TypeDescription>emptyList(), Collections.<TypeDescription>emptyList(), Opcodes.ACC_PUBLIC);
    }

    @Test
    public void testWithLoadedTypeInitializerInitial() throws Exception {
        LoadedTypeInitializer loadedTypeInitializer = makePlainInstrumentedType().getLoadedTypeInitializer();
        assertThat(loadedTypeInitializer.isAlive(), is(false));
    }

    @Test
    public void testWithLoadedTypeInitializerSingle() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        LoadedTypeInitializer loadedTypeInitializer = mock(LoadedTypeInitializer.class);
        instrumentedType = instrumentedType.withInitializer(loadedTypeInitializer);
        assertThat(instrumentedType.getLoadedTypeInitializer(),
                is((LoadedTypeInitializer) new LoadedTypeInitializer.Compound(LoadedTypeInitializer.NoOp.INSTANCE, loadedTypeInitializer)));
    }

    @Test
    public void testWithLoadedTypeInitializerDouble() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        LoadedTypeInitializer first = mock(LoadedTypeInitializer.class), second = mock(LoadedTypeInitializer.class);
        instrumentedType = instrumentedType.withInitializer(first).withInitializer(second);
        assertThat(instrumentedType.getLoadedTypeInitializer(),
                is((LoadedTypeInitializer) new LoadedTypeInitializer.Compound(new LoadedTypeInitializer
                        .Compound(LoadedTypeInitializer.NoOp.INSTANCE, first), second)));
    }

    @Test
    public void testWithTypeInitializerInitial() throws Exception {
        InstrumentedType.TypeInitializer typeInitializer = makePlainInstrumentedType().getTypeInitializer();
        assertThat(typeInitializer.isDefined(), is(false));
    }

    @Test
    public void testWithTypeInitializerSingle() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        ByteCodeAppender byteCodeAppender = mock(ByteCodeAppender.class);
        instrumentedType = instrumentedType.withInitializer(byteCodeAppender);
        InstrumentedType.TypeInitializer typeInitializer = instrumentedType.getTypeInitializer();
        assertThat(typeInitializer.isDefined(), is(true));
        MethodDescription methodDescription = mock(MethodDescription.class);
        typeInitializer.apply(methodVisitor, implementationContext, methodDescription);
        verify(byteCodeAppender).apply(methodVisitor, implementationContext, methodDescription);
    }

    @Test
    public void testWithTypeInitializerDouble() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.getDeclaredFields().size(), is(0));
        ByteCodeAppender first = mock(ByteCodeAppender.class), second = mock(ByteCodeAppender.class);
        MethodDescription methodDescription = mock(MethodDescription.class);
        when(first.apply(methodVisitor, implementationContext, methodDescription)).thenReturn(new ByteCodeAppender.Size(0, 0));
        when(second.apply(methodVisitor, implementationContext, methodDescription)).thenReturn(new ByteCodeAppender.Size(0, 0));
        instrumentedType = instrumentedType.withInitializer(first).withInitializer(second);
        InstrumentedType.TypeInitializer typeInitializer = instrumentedType.getTypeInitializer();
        assertThat(typeInitializer.isDefined(), is(true));
        typeInitializer.apply(methodVisitor, implementationContext, methodDescription);
        verify(first).apply(methodVisitor, implementationContext, methodDescription);
        verify(second).apply(methodVisitor, implementationContext, methodDescription);
    }

    @Test
    public void testGetStackSize() throws Exception {
        assertThat(makePlainInstrumentedType().getStackSize(), is(StackSize.SINGLE));
    }

    @Test
    public void testHashCode() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        assertThat(instrumentedType.hashCode(), is(instrumentedType.getInternalName().hashCode()));
    }

    @Test
    public void testEquals() throws Exception {
        InstrumentedType instrumentedType = makePlainInstrumentedType();
        TypeDescription other = mock(TypeDescription.class);
        when(other.getInternalName()).thenReturn(instrumentedType.getInternalName());
        when(other.getSort()).thenReturn(GenericTypeDescription.Sort.RAW);
        when(other.asRawType()).thenReturn(other);
        assertThat(instrumentedType, equalTo(other));
        verify(other, atLeast(1)).getInternalName();
    }

    @Test
    public void testIsAssignableFrom() {
        assertThat(makePlainInstrumentedType().isAssignableFrom(Object.class), is(false));
        assertThat(makePlainInstrumentedType().isAssignableFrom(Serializable.class), is(false));
        assertThat(makePlainInstrumentedType().isAssignableFrom(Integer.class), is(false));
        TypeDescription objectTypeDescription = new TypeDescription.ForLoadedType(Object.class);
        assertThat(makePlainInstrumentedType().isAssignableFrom(objectTypeDescription), is(false));
        TypeDescription serializableTypeDescription = new TypeDescription.ForLoadedType(Serializable.class);
        assertThat(makePlainInstrumentedType().isAssignableFrom(serializableTypeDescription), is(false));
        TypeDescription integerTypeDescription = new TypeDescription.ForLoadedType(Integer.class);
        assertThat(makePlainInstrumentedType().isAssignableFrom(integerTypeDescription), is(false));
    }

    @Test
    public void testIsAssignableTo() {
        assertThat(makePlainInstrumentedType().isAssignableTo(Object.class), is(true));
        assertThat(makePlainInstrumentedType().isAssignableTo(Serializable.class), is(true));
        assertThat(makePlainInstrumentedType().isAssignableTo(Integer.class), is(false));
        TypeDescription objectTypeDescription = new TypeDescription.ForLoadedType(Object.class);
        assertThat(makePlainInstrumentedType().isAssignableTo(objectTypeDescription), is(true));
        TypeDescription serializableTypeDescription = new TypeDescription.ForLoadedType(Serializable.class);
        assertThat(makePlainInstrumentedType().isAssignableTo(serializableTypeDescription), is(true));
        TypeDescription integerTypeDescription = new TypeDescription.ForLoadedType(Integer.class);
        assertThat(makePlainInstrumentedType().isAssignableTo(integerTypeDescription), is(false));
    }

    @Test
    public void testRepresents() {
        assertThat(makePlainInstrumentedType().represents(Object.class), is(false));
        assertThat(makePlainInstrumentedType().represents(Serializable.class), is(false));
        assertThat(makePlainInstrumentedType().represents(Integer.class), is(false));
    }

    @Test
    public void testSupertype() {
        assertThat(makePlainInstrumentedType().getSuperType(), is((TypeDescription) new TypeDescription.ForLoadedType(Object.class)));
        assertThat(makePlainInstrumentedType().getSuperType(), not(is((TypeDescription) new TypeDescription.ForLoadedType(Integer.class))));
        assertThat(makePlainInstrumentedType().getSuperType(), not(is((TypeDescription) new TypeDescription.ForLoadedType(Serializable.class))));
    }

    @Test
    public void testInterfaces() {
        TypeList interfaces = makePlainInstrumentedType().getInterfaces();
        assertThat(interfaces.size(), is(1));
        assertThat(interfaces.get(0), is(is((TypeDescription) new TypeDescription.ForLoadedType(Serializable.class))));
    }

    @Test
    public void testPackage() {
        assertThat(makePlainInstrumentedType().getPackage().getName(), is(FOO));
    }

    @Test
    public void testSimpleName() {
        assertThat(makePlainInstrumentedType().getSimpleName(), is(BAR));
    }

    @Test
    public void testEnclosingMethod() throws Exception {
        assertThat(makePlainInstrumentedType().getEnclosingMethod(), nullValue());
    }

    @Test
    public void testEnclosingType() throws Exception {
        assertThat(makePlainInstrumentedType().getEnclosingType(), nullValue());
    }

    @Test
    public void testDeclaringType() throws Exception {
        assertThat(makePlainInstrumentedType().getDeclaringType(), nullValue());
    }

    @Test
    public void testIsAnonymous() throws Exception {
        assertThat(makePlainInstrumentedType().isAnonymousClass(), is(false));
    }

    @Test
    public void testCanonicalName() throws Exception {
        TypeDescription typeDescription = makePlainInstrumentedType();
        assertThat(typeDescription.getCanonicalName(), is(typeDescription.getName()));
    }

    @Test
    public void testIsMemberClass() throws Exception {
        assertThat(makePlainInstrumentedType().isMemberClass(), is(false));
    }
}


File: byte-buddy-dep/src/test/java/net/bytebuddy/dynamic/scaffold/inline/InlineInstrumentedTypeTest.java
package net.bytebuddy.dynamic.scaffold.inline;

import net.bytebuddy.ClassFileVersion;
import net.bytebuddy.NamingStrategy;
import net.bytebuddy.description.field.FieldList;
import net.bytebuddy.description.method.MethodList;
import net.bytebuddy.description.type.PackageDescription;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.description.type.TypeList;
import net.bytebuddy.description.type.generic.GenericTypeList;
import net.bytebuddy.dynamic.scaffold.AbstractInstrumentedTypeTest;
import net.bytebuddy.dynamic.scaffold.InstrumentedType;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mock;
import org.objectweb.asm.Opcodes;

import java.io.Serializable;
import java.util.Collections;

import static net.bytebuddy.matcher.ElementMatchers.isConstructor;
import static net.bytebuddy.matcher.ElementMatchers.isMethod;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.mockito.Mockito.when;

public class InlineInstrumentedTypeTest extends AbstractInstrumentedTypeTest {

    private static final String FOO = "foo", BAR = "bar", FOOBAR = FOO + "." + BAR;

    @Mock
    private TypeDescription targetType;

    @Mock
    private PackageDescription packageDescription;

    @Before
    public void setUp() throws Exception {
        when(targetType.getDeclaredMethods()).thenReturn(new MethodList.Empty());
        when(targetType.getDeclaredFields()).thenReturn(new FieldList.Empty());
        when(targetType.getInterfacesGen()).thenReturn(new GenericTypeList.Empty());
        when(targetType.getSuperTypeGen()).thenReturn(new TypeDescription.ForLoadedType(Object.class));
        when(targetType.getPackage()).thenReturn(packageDescription);
        when(packageDescription.getName()).thenReturn(FOO);
    }

    @Override
    protected InstrumentedType makePlainInstrumentedType() {
        return new InlineInstrumentedType(
                ClassFileVersion.forCurrentJavaVersion(),
                targetType,
                new TypeList.ForLoadedType(Collections.<Class<?>>singletonList(Serializable.class)),
                Opcodes.ACC_PUBLIC,
                new NamingStrategy.Fixed(FOOBAR));
    }

    @Test
    public void testTargetTypeMemberInheritance() throws Exception {
        TypeDescription typeDescription = new InlineInstrumentedType(
                ClassFileVersion.forCurrentJavaVersion(),
                new TypeDescription.ForLoadedType(Foo.class),
                new TypeList.ForLoadedType(Collections.<Class<?>>singletonList(Serializable.class)),
                Opcodes.ACC_PUBLIC,
                new NamingStrategy.Fixed(FOOBAR));
        assertThat(typeDescription.getDeclaredMethods().size(), is(2));
        assertThat(typeDescription.getDeclaredMethods().filter(isConstructor()).size(), is(1));
        assertThat(typeDescription.getDeclaredMethods().filter(isMethod()).size(), is(1));
        assertThat(typeDescription.getDeclaredFields().size(), is(1));
    }

    public static class Foo {

        private Void foo;

        public void foo() {
            /* empty */
        }
    }
}
