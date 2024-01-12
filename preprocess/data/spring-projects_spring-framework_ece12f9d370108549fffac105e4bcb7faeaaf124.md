Refactoring Types: ['Extract Method']
springframework/core/annotation/AnnotationUtils.java
/*
 * Copyright 2002-2015 the original author or authors.
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

package org.springframework.core.annotation;

import java.lang.annotation.Annotation;
import java.lang.reflect.AnnotatedElement;
import java.lang.reflect.Array;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.springframework.core.BridgeMethodResolver;
import org.springframework.util.Assert;
import org.springframework.util.ClassUtils;
import org.springframework.util.ConcurrentReferenceHashMap;
import org.springframework.util.ObjectUtils;
import org.springframework.util.ReflectionUtils;
import org.springframework.util.StringUtils;

/**
 * General utility methods for working with annotations, handling meta-annotations,
 * bridge methods (which the compiler generates for generic declarations) as well
 * as super methods (for optional <em>annotation inheritance</em>).
 *
 * <p>Note that most of the features of this class are not provided by the
 * JDK's introspection facilities themselves.
 *
 * <p>As a general rule for runtime-retained annotations (e.g. for transaction
 * control, authorization, or service exposure), always use the lookup methods
 * on this class (e.g., {@link #findAnnotation(Method, Class)},
 * {@link #getAnnotation(Method, Class)}, and {@link #getAnnotations(Method)})
 * instead of the plain annotation lookup methods in the JDK. You can still
 * explicitly choose between a <em>get</em> lookup on the given class level only
 * ({@link #getAnnotation(Method, Class)}) and a <em>find</em> lookup in the entire
 * inheritance hierarchy of the given method ({@link #findAnnotation(Method, Class)}).
 *
 * <h3>Terminology</h3>
 * The terms <em>directly present</em> and <em>present</em> have the same
 * meanings as defined in the class-level Javadoc for {@link AnnotatedElement}.
 *
 * <p>An annotation is <em>meta-present</em> on an element if the annotation
 * is declared as a meta-annotation on some other annotation which is
 * <em>present</em> on the element.
 *
 * <h3>Meta-annotation Support</h3>
 * <p>Most {@code find*()} methods and some {@code get*()} methods in this
 * class provide support for finding annotations used as meta-annotations.
 * Consult the Javadoc for each method in this class for details. For support
 * for meta-annotations with <em>attribute overrides</em> in
 * <em>composed annotations</em>, use {@link AnnotatedElementUtils} instead.
 *
 * <h3>Search Scope</h3>
 * <p>The search algorithms used by methods in this class stop searching for
 * an annotation once the first annotation of the specified type has been
 * found. As a consequence, additional annotations of the specified type will
 * be silently ignored.
 *
 * @author Rob Harrop
 * @author Juergen Hoeller
 * @author Sam Brannen
 * @author Mark Fisher
 * @author Chris Beams
 * @author Phillip Webb
 * @since 2.0
 * @see AliasFor
 * @see AnnotationAttributes
 * @see AnnotatedElementUtils
 * @see BridgeMethodResolver
 * @see java.lang.reflect.AnnotatedElement#getAnnotations()
 * @see java.lang.reflect.AnnotatedElement#getAnnotation(Class)
 * @see java.lang.reflect.AnnotatedElement#getDeclaredAnnotations()
 */
public abstract class AnnotationUtils {

	/**
	 * The attribute name for annotations with a single element.
	 */
	public static final String VALUE = "value";


	/**
	 * An object that can be stored in {@link AnnotationAttributes} as a
	 * placeholder for an attribute's declared default value.
	 */
	private static final Object DEFAULT_VALUE_PLACEHOLDER = new String("<SPRING DEFAULT VALUE PLACEHOLDER>");

	private static final Map<AnnotationCacheKey, Annotation> findAnnotationCache =
			new ConcurrentReferenceHashMap<AnnotationCacheKey, Annotation>(256);

	private static final Map<Class<?>, Boolean> annotatedInterfaceCache =
			new ConcurrentReferenceHashMap<Class<?>, Boolean>(256);

	private static final Map<Class<? extends Annotation>, Boolean> synthesizableCache =
			new ConcurrentReferenceHashMap<Class<? extends Annotation>, Boolean>(256);

	private static final Map<Class<? extends Annotation>, Map<String, String>> attributeAliasesCache =
			new ConcurrentReferenceHashMap<Class<? extends Annotation>, Map<String, String>>(256);

	private static final Map<Class<? extends Annotation>, List<Method>> attributeMethodsCache =
			new ConcurrentReferenceHashMap<Class<? extends Annotation>, List<Method>>(256);

	private static transient Log logger;


	/**
	 * Get a single {@link Annotation} of {@code annotationType} from the supplied
	 * annotation: either the given annotation itself or a direct meta-annotation
	 * thereof.
	 * <p>Note that this method supports only a single level of meta-annotations.
	 * For support for arbitrary levels of meta-annotations, use one of the
	 * {@code find*()} methods instead.
	 * @param ann the Annotation to check
	 * @param annotationType the annotation type to look for, both locally and as a meta-annotation
	 * @return the first matching annotation, or {@code null} if not found
	 * @since 4.0
	 */
	@SuppressWarnings("unchecked")
	public static <A extends Annotation> A getAnnotation(Annotation ann, Class<A> annotationType) {
		if (annotationType.isInstance(ann)) {
			return synthesizeAnnotation((A) ann);
		}
		Class<? extends Annotation> annotatedElement = ann.annotationType();
		try {
			return synthesizeAnnotation(annotatedElement.getAnnotation(annotationType), annotatedElement);
		}
		catch (Exception ex) {
			// Assuming nested Class values not resolvable within annotation attributes...
			handleIntrospectionFailure(annotatedElement, ex);
			return null;
		}
	}

	/**
	 * Get a single {@link Annotation} of {@code annotationType} from the supplied
	 * {@link AnnotatedElement}, where the annotation is either <em>present</em> or
	 * <em>meta-present</em> on the {@code AnnotatedElement}.
	 * <p>Note that this method supports only a single level of meta-annotations.
	 * For support for arbitrary levels of meta-annotations, use
	 * {@link #findAnnotation(AnnotatedElement, Class)} instead.
	 * @param annotatedElement the {@code AnnotatedElement} from which to get the annotation
	 * @param annotationType the annotation type to look for, both locally and as a meta-annotation
	 * @return the first matching annotation, or {@code null} if not found
	 * @since 3.1
	 */
	public static <A extends Annotation> A getAnnotation(AnnotatedElement annotatedElement, Class<A> annotationType) {
		try {
			A annotation = annotatedElement.getAnnotation(annotationType);
			if (annotation == null) {
				for (Annotation metaAnn : annotatedElement.getAnnotations()) {
					annotation = metaAnn.annotationType().getAnnotation(annotationType);
					if (annotation != null) {
						break;
					}
				}
			}
			return synthesizeAnnotation(annotation, annotatedElement);
		}
		catch (Exception ex) {
			// Assuming nested Class values not resolvable within annotation attributes...
			handleIntrospectionFailure(annotatedElement, ex);
			return null;
		}
	}

	/**
	 * Get a single {@link Annotation} of {@code annotationType} from the
	 * supplied {@link Method}, where the annotation is either <em>present</em>
	 * or <em>meta-present</em> on the method.
	 * <p>Correctly handles bridge {@link Method Methods} generated by the compiler.
	 * <p>Note that this method supports only a single level of meta-annotations.
	 * For support for arbitrary levels of meta-annotations, use
	 * {@link #findAnnotation(Method, Class)} instead.
	 * @param method the method to look for annotations on
	 * @param annotationType the annotation type to look for
	 * @return the first matching annotation, or {@code null} if not found
	 * @see org.springframework.core.BridgeMethodResolver#findBridgedMethod(Method)
	 * @see #getAnnotation(AnnotatedElement, Class)
	 */
	public static <A extends Annotation> A getAnnotation(Method method, Class<A> annotationType) {
		Method resolvedMethod = BridgeMethodResolver.findBridgedMethod(method);
		return getAnnotation((AnnotatedElement) resolvedMethod, annotationType);
	}

	/**
	 * Get all {@link Annotation Annotations} that are <em>present</em> on the
	 * supplied {@link AnnotatedElement}.
	 * <p>Meta-annotations will <em>not</em> be searched.
	 * @param annotatedElement the Method, Constructor or Field to retrieve annotations from
	 * @return the annotations found, an empty array, or {@code null} if not
	 * resolvable (e.g. because nested Class values in annotation attributes
	 * failed to resolve at runtime)
	 * @since 4.0.8
	 */
	public static Annotation[] getAnnotations(AnnotatedElement annotatedElement) {
		try {
			return annotatedElement.getAnnotations();
		}
		catch (Exception ex) {
			// Assuming nested Class values not resolvable within annotation attributes...
			handleIntrospectionFailure(annotatedElement, ex);
		}
		return null;
	}

	/**
	 * Get all {@link Annotation Annotations} that are <em>present</em on the
	 * supplied {@link Method}.
	 * <p>Correctly handles bridge {@link Method Methods} generated by the compiler.
	 * <p>Meta-annotations will <em>not</em> be searched.
	 * @param method the Method to retrieve annotations from
	 * @return the annotations found, an empty array, or {@code null} if not
	 * resolvable (e.g. because nested Class values in annotation attributes
	 * failed to resolve at runtime)
	 * @see org.springframework.core.BridgeMethodResolver#findBridgedMethod(Method)
	 * @see AnnotatedElement#getAnnotations()
	 */
	public static Annotation[] getAnnotations(Method method) {
		try {
			return BridgeMethodResolver.findBridgedMethod(method).getAnnotations();
		}
		catch (Exception ex) {
			// Assuming nested Class values not resolvable within annotation attributes...
			handleIntrospectionFailure(method, ex);
		}
		return null;
	}

	/**
	 * Get the <em>repeatable</em> {@link Annotation}s of {@code annotationType}
	 * from the supplied {@link Method}, where such annotations are either
	 * <em>present</em> or <em>meta-present</em> on the method.
	 * <p>Handles both single annotations and annotations nested within a
	 * <em>containing annotation</em>.
	 * <p>Correctly handles bridge {@link Method Methods} generated by the compiler.
	 * <p>Meta-annotations will be searched if the annotation is not
	 * <em>present</em> on the supplied method.
	 * @param method the method to look for annotations on; never {@code null}
	 * @param containerAnnotationType the type of the container that holds the
	 * annotations; may be {@code null} if a container is not supported
	 * @param annotationType the annotation type to look for
	 * @return the annotations found or an empty set; never {@code null}
	 * @since 4.0
	 * @see org.springframework.core.BridgeMethodResolver#findBridgedMethod(Method)
	 * @see java.lang.annotation.Repeatable
	 */
	public static <A extends Annotation> Set<A> getRepeatableAnnotation(Method method,
			Class<? extends Annotation> containerAnnotationType, Class<A> annotationType) {

		Method resolvedMethod = BridgeMethodResolver.findBridgedMethod(method);
		return getRepeatableAnnotation((AnnotatedElement) resolvedMethod, containerAnnotationType, annotationType);
	}

	/**
	 * Get the <em>repeatable</em> {@link Annotation}s of {@code annotationType}
	 * from the supplied {@link AnnotatedElement}, where such annotations are
	 * either <em>present</em> or <em>meta-present</em> on the element.
	 * <p>Handles both single annotations and annotations nested within a
	 * <em>containing annotation</em>.
	 * <p>Meta-annotations will be searched if the annotation is not
	 * <em>present</em> on the supplied element.
	 * @param annotatedElement the element to look for annotations on; never {@code null}
	 * @param containerAnnotationType the type of the container that holds the
	 * annotations; may be {@code null} if a container is not supported
	 * @param annotationType the annotation type to look for
	 * @return the annotations found or an empty set; never {@code null}
	 * @since 4.0
	 * @see java.lang.annotation.Repeatable
	 */
	public static <A extends Annotation> Set<A> getRepeatableAnnotation(AnnotatedElement annotatedElement,
			Class<? extends Annotation> containerAnnotationType, Class<A> annotationType) {

		try {
			if (annotatedElement.getAnnotations().length > 0) {
				return new AnnotationCollector<A>(containerAnnotationType, annotationType).getResult(annotatedElement);
			}
		}
		catch (Exception ex) {
			// Assuming nested Class values not resolvable within annotation attributes...
			handleIntrospectionFailure(annotatedElement, ex);
		}
		return Collections.emptySet();
	}

	/**
	 * Find a single {@link Annotation} of {@code annotationType} on the
	 * supplied {@link AnnotatedElement}.
	 * <p>Meta-annotations will be searched if the annotation is not
	 * <em>directly present</em> on the supplied element.
	 * <p><strong>Warning</strong>: this method operates generically on
	 * annotated elements. In other words, this method does not execute
	 * specialized search algorithms for classes or methods. If you require
	 * the more specific semantics of {@link #findAnnotation(Class, Class)}
	 * or {@link #findAnnotation(Method, Class)}, invoke one of those methods
	 * instead.
	 * @param annotatedElement the {@code AnnotatedElement} on which to find the annotation
	 * @param annotationType the annotation type to look for, both locally and as a meta-annotation
	 * @return the first matching annotation, or {@code null} if not found
	 * @since 4.2
	 */
	public static <A extends Annotation> A findAnnotation(AnnotatedElement annotatedElement, Class<A> annotationType) {
		// Do NOT store result in the findAnnotationCache since doing so could break
		// findAnnotation(Class, Class) and findAnnotation(Method, Class).
		return synthesizeAnnotation(findAnnotation(annotatedElement, annotationType, new HashSet<Annotation>()),
			annotatedElement);
	}

	/**
	 * Perform the search algorithm for {@link #findAnnotation(AnnotatedElement, Class)}
	 * avoiding endless recursion by tracking which annotations have already
	 * been <em>visited</em>.
	 * @param annotatedElement the {@code AnnotatedElement} on which to find the annotation
	 * @param annotationType the annotation type to look for, both locally and as a meta-annotation
	 * @param visited the set of annotations that have already been visited
	 * @return the first matching annotation, or {@code null} if not found
	 * @since 4.2
	 */
	@SuppressWarnings("unchecked")
	private static <A extends Annotation> A findAnnotation(AnnotatedElement annotatedElement, Class<A> annotationType, Set<Annotation> visited) {
		Assert.notNull(annotatedElement, "AnnotatedElement must not be null");
		try {
			Annotation[] anns = annotatedElement.getDeclaredAnnotations();
			for (Annotation ann : anns) {
				if (ann.annotationType().equals(annotationType)) {
					return (A) ann;
				}
			}
			for (Annotation ann : anns) {
				if (!isInJavaLangAnnotationPackage(ann) && visited.add(ann)) {
					A annotation = findAnnotation((AnnotatedElement) ann.annotationType(), annotationType, visited);
					if (annotation != null) {
						return annotation;
					}
				}
			}
		}
		catch (Exception ex) {
			// Assuming nested Class values not resolvable within annotation attributes...
			handleIntrospectionFailure(annotatedElement, ex);
		}
		return null;
	}

	/**
	 * Find a single {@link Annotation} of {@code annotationType} on the supplied
	 * {@link Method}, traversing its super methods (i.e., from superclasses and
	 * interfaces) if the annotation is not <em>directly present</em> on the given
	 * method itself.
	 * <p>Correctly handles bridge {@link Method Methods} generated by the compiler.
	 * <p>Meta-annotations will be searched if the annotation is not
	 * <em>directly present</em> on the method.
	 * <p>Annotations on methods are not inherited by default, so we need to handle
	 * this explicitly.
	 * @param method the method to look for annotations on
	 * @param annotationType the annotation type to look for
	 * @return the first matching annotation, or {@code null} if not found
	 * @see #getAnnotation(Method, Class)
	 */
	@SuppressWarnings("unchecked")
	public static <A extends Annotation> A findAnnotation(Method method, Class<A> annotationType) {
		AnnotationCacheKey cacheKey = new AnnotationCacheKey(method, annotationType);
		A result = (A) findAnnotationCache.get(cacheKey);

		if (result == null) {
			Method resolvedMethod = BridgeMethodResolver.findBridgedMethod(method);
			result = findAnnotation((AnnotatedElement) resolvedMethod, annotationType);

			if (result == null) {
				result = searchOnInterfaces(method, annotationType, method.getDeclaringClass().getInterfaces());
			}

			Class<?> clazz = method.getDeclaringClass();
			while (result == null) {
				clazz = clazz.getSuperclass();
				if (clazz == null || Object.class == clazz) {
					break;
				}
				try {
					Method equivalentMethod = clazz.getDeclaredMethod(method.getName(), method.getParameterTypes());
					Method resolvedEquivalentMethod = BridgeMethodResolver.findBridgedMethod(equivalentMethod);
					result = findAnnotation((AnnotatedElement) resolvedEquivalentMethod, annotationType);
				}
				catch (NoSuchMethodException ex) {
					// No equivalent method found
				}
				if (result == null) {
					result = searchOnInterfaces(method, annotationType, clazz.getInterfaces());
				}
			}

			if (result != null) {
				findAnnotationCache.put(cacheKey, result);
			}
		}

		return synthesizeAnnotation(result, method);
	}

	private static <A extends Annotation> A searchOnInterfaces(Method method, Class<A> annotationType, Class<?>... ifcs) {
		A annotation = null;
		for (Class<?> iface : ifcs) {
			if (isInterfaceWithAnnotatedMethods(iface)) {
				try {
					Method equivalentMethod = iface.getMethod(method.getName(), method.getParameterTypes());
					annotation = getAnnotation(equivalentMethod, annotationType);
				}
				catch (NoSuchMethodException ex) {
					// Skip this interface - it doesn't have the method...
				}
				if (annotation != null) {
					break;
				}
			}
		}
		return annotation;
	}

	static boolean isInterfaceWithAnnotatedMethods(Class<?> iface) {
		Boolean found = annotatedInterfaceCache.get(iface);
		if (found != null) {
			return found.booleanValue();
		}
		found = Boolean.FALSE;
		for (Method ifcMethod : iface.getMethods()) {
			try {
				if (ifcMethod.getAnnotations().length > 0) {
					found = Boolean.TRUE;
					break;
				}
			}
			catch (Exception ex) {
				// Assuming nested Class values not resolvable within annotation attributes...
				handleIntrospectionFailure(ifcMethod, ex);
			}
		}
		annotatedInterfaceCache.put(iface, found);
		return found.booleanValue();
	}

	/**
	 * Find a single {@link Annotation} of {@code annotationType} on the
	 * supplied {@link Class}, traversing its interfaces, annotations, and
	 * superclasses if the annotation is not <em>directly present</em> on
	 * the given class itself.
	 * <p>This method explicitly handles class-level annotations which are not
	 * declared as {@link java.lang.annotation.Inherited inherited} <em>as well
	 * as meta-annotations and annotations on interfaces</em>.
	 * <p>The algorithm operates as follows:
	 * <ol>
	 * <li>Search for the annotation on the given class and return it if found.
	 * <li>Recursively search through all annotations that the given class declares.
	 * <li>Recursively search through all interfaces that the given class declares.
	 * <li>Recursively search through the superclass hierarchy of the given class.
	 * </ol>
	 * <p>Note: in this context, the term <em>recursively</em> means that the search
	 * process continues by returning to step #1 with the current interface,
	 * annotation, or superclass as the class to look for annotations on.
	 * @param clazz the class to look for annotations on
	 * @param annotationType the type of annotation to look for
	 * @return the first matching annotation, or {@code null} if not found
	 */
	@SuppressWarnings("unchecked")
	public static <A extends Annotation> A findAnnotation(Class<?> clazz, Class<A> annotationType) {
		AnnotationCacheKey cacheKey = new AnnotationCacheKey(clazz, annotationType);
		A result = (A) findAnnotationCache.get(cacheKey);
		if (result == null) {
			result = findAnnotation(clazz, annotationType, new HashSet<Annotation>());
			if (result != null) {
				findAnnotationCache.put(cacheKey, result);
			}
		}
		return synthesizeAnnotation(result, clazz);
	}

	/**
	 * Perform the search algorithm for {@link #findAnnotation(Class, Class)},
	 * avoiding endless recursion by tracking which annotations have already
	 * been <em>visited</em>.
	 * @param clazz the class to look for annotations on
	 * @param annotationType the type of annotation to look for
	 * @param visited the set of annotations that have already been visited
	 * @return the first matching annotation, or {@code null} if not found
	 */
	@SuppressWarnings("unchecked")
	private static <A extends Annotation> A findAnnotation(Class<?> clazz, Class<A> annotationType, Set<Annotation> visited) {
		Assert.notNull(clazz, "Class must not be null");

		try {
			Annotation[] anns = clazz.getDeclaredAnnotations();
			for (Annotation ann : anns) {
				if (ann.annotationType().equals(annotationType)) {
					return (A) ann;
				}
			}
			for (Annotation ann : anns) {
				if (!isInJavaLangAnnotationPackage(ann) && visited.add(ann)) {
					A annotation = findAnnotation(ann.annotationType(), annotationType, visited);
					if (annotation != null) {
						return annotation;
					}
				}
			}
		}
		catch (Exception ex) {
			// Assuming nested Class values not resolvable within annotation attributes...
			handleIntrospectionFailure(clazz, ex);
			return null;
		}

		for (Class<?> ifc : clazz.getInterfaces()) {
			A annotation = findAnnotation(ifc, annotationType, visited);
			if (annotation != null) {
				return annotation;
			}
		}

		Class<?> superclass = clazz.getSuperclass();
		if (superclass == null || Object.class == superclass) {
			return null;
		}
		return findAnnotation(superclass, annotationType, visited);
	}

	/**
	 * Find the first {@link Class} in the inheritance hierarchy of the
	 * specified {@code clazz} (including the specified {@code clazz} itself)
	 * on which an annotation of the specified {@code annotationType} is
	 * <em>directly present</em>.
	 * <p>If the supplied {@code clazz} is an interface, only the interface
	 * itself will be checked; the inheritance hierarchy for interfaces will
	 * not be traversed.
	 * <p>Meta-annotations will <em>not</em> be searched.
	 * <p>The standard {@link Class} API does not provide a mechanism for
	 * determining which class in an inheritance hierarchy actually declares
	 * an {@link Annotation}, so we need to handle this explicitly.
	 * @param annotationType the annotation type to look for
	 * @param clazz the class to check for the annotation on (may be {@code null})
	 * @return the first {@link Class} in the inheritance hierarchy that
	 * declares an annotation of the specified {@code annotationType}, or
	 * {@code null} if not found
	 * @see Class#isAnnotationPresent(Class)
	 * @see Class#getDeclaredAnnotations()
	 * @see #findAnnotationDeclaringClassForTypes(List, Class)
	 * @see #isAnnotationDeclaredLocally(Class, Class)
	 */
	public static Class<?> findAnnotationDeclaringClass(Class<? extends Annotation> annotationType, Class<?> clazz) {
		Assert.notNull(annotationType, "Annotation type must not be null");
		if (clazz == null || Object.class == clazz) {
			return null;
		}
		if (isAnnotationDeclaredLocally(annotationType, clazz)) {
			return clazz;
		}
		return findAnnotationDeclaringClass(annotationType, clazz.getSuperclass());
	}

	/**
	 * Find the first {@link Class} in the inheritance hierarchy of the
	 * specified {@code clazz} (including the specified {@code clazz} itself)
	 * on which at least one of the specified {@code annotationTypes} is
	 * <em>directly present</em>.
	 * <p>If the supplied {@code clazz} is an interface, only the interface
	 * itself will be checked; the inheritance hierarchy for interfaces will
	 * not be traversed.
	 * <p>Meta-annotations will <em>not</em> be searched.
	 * <p>The standard {@link Class} API does not provide a mechanism for
	 * determining which class in an inheritance hierarchy actually declares
	 * one of several candidate {@linkplain Annotation annotations}, so we
	 * need to handle this explicitly.
	 * @param annotationTypes the annotation types to look for
	 * @param clazz the class to check for the annotations on, or {@code null}
	 * @return the first {@link Class} in the inheritance hierarchy that
	 * declares an annotation of at least one of the specified
	 * {@code annotationTypes}, or {@code null} if not found
	 * @since 3.2.2
	 * @see Class#isAnnotationPresent(Class)
	 * @see Class#getDeclaredAnnotations()
	 * @see #findAnnotationDeclaringClass(Class, Class)
	 * @see #isAnnotationDeclaredLocally(Class, Class)
	 */
	public static Class<?> findAnnotationDeclaringClassForTypes(List<Class<? extends Annotation>> annotationTypes, Class<?> clazz) {
		Assert.notEmpty(annotationTypes, "The list of annotation types must not be empty");
		if (clazz == null || Object.class == clazz) {
			return null;
		}
		for (Class<? extends Annotation> annotationType : annotationTypes) {
			if (isAnnotationDeclaredLocally(annotationType, clazz)) {
				return clazz;
			}
		}
		return findAnnotationDeclaringClassForTypes(annotationTypes, clazz.getSuperclass());
	}

	/**
	 * Determine whether an annotation of the specified {@code annotationType}
	 * is declared locally (i.e., <em>directly present</em>) on the supplied
	 * {@code clazz}.
	 * <p>The supplied {@link Class} may represent any type.
	 * <p>Meta-annotations will <em>not</em> be searched.
	 * <p>Note: This method does <strong>not</strong> determine if the annotation
	 * is {@linkplain java.lang.annotation.Inherited inherited}. For greater
	 * clarity regarding inherited annotations, consider using
	 * {@link #isAnnotationInherited(Class, Class)} instead.
	 * @param annotationType the annotation type to look for
	 * @param clazz the class to check for the annotation on
	 * @return {@code true} if an annotation of the specified {@code annotationType}
	 * is <em>directly present</em>
	 * @see java.lang.Class#getDeclaredAnnotations()
	 * @see java.lang.Class#getDeclaredAnnotation(Class)
	 * @see #isAnnotationInherited(Class, Class)
	 */
	public static boolean isAnnotationDeclaredLocally(Class<? extends Annotation> annotationType, Class<?> clazz) {
		Assert.notNull(annotationType, "Annotation type must not be null");
		Assert.notNull(clazz, "Class must not be null");
		try {
			for (Annotation ann : clazz.getDeclaredAnnotations()) {
				if (ann.annotationType().equals(annotationType)) {
					return true;
				}
			}
		}
		catch (Exception ex) {
			// Assuming nested Class values not resolvable within annotation attributes...
			handleIntrospectionFailure(clazz, ex);
		}
		return false;
	}

	/**
	 * Determine whether an annotation of the specified {@code annotationType}
	 * is <em>present</em> on the supplied {@code clazz} and is
	 * {@linkplain java.lang.annotation.Inherited inherited} (i.e., not
	 * <em>directly present</em>).
	 * <p>Meta-annotations will <em>not</em> be searched.
	 * <p>If the supplied {@code clazz} is an interface, only the interface
	 * itself will be checked. In accordance with standard meta-annotation
	 * semantics in Java, the inheritance hierarchy for interfaces will not
	 * be traversed. See the {@linkplain java.lang.annotation.Inherited Javadoc}
	 * for the {@code @Inherited} meta-annotation for further details regarding
	 * annotation inheritance.
	 * @param annotationType the annotation type to look for
	 * @param clazz the class to check for the annotation on
	 * @return {@code true} if an annotation of the specified {@code annotationType}
	 * is <em>present</em> and <em>inherited</em>
	 * @see Class#isAnnotationPresent(Class)
	 * @see #isAnnotationDeclaredLocally(Class, Class)
	 */
	public static boolean isAnnotationInherited(Class<? extends Annotation> annotationType, Class<?> clazz) {
		Assert.notNull(annotationType, "Annotation type must not be null");
		Assert.notNull(clazz, "Class must not be null");
		return (clazz.isAnnotationPresent(annotationType) && !isAnnotationDeclaredLocally(annotationType, clazz));
	}

	/**
	 * Determine if the supplied {@link Annotation} is defined in the core JDK
	 * {@code java.lang.annotation} package.
	 * @param annotation the annotation to check (never {@code null})
	 * @return {@code true} if the annotation is in the {@code java.lang.annotation} package
	 */
	public static boolean isInJavaLangAnnotationPackage(Annotation annotation) {
		Assert.notNull(annotation, "Annotation must not be null");
		return isInJavaLangAnnotationPackage(annotation.annotationType().getName());
	}

	/**
	 * Determine if the {@link Annotation} with the supplied name is defined
	 * in the core JDK {@code java.lang.annotation} package.
	 * @param annotationType the name of the annotation type to check (never {@code null} or empty)
	 * @return {@code true} if the annotation is in the {@code java.lang.annotation} package
	 * @since 4.2
	 */
	public static boolean isInJavaLangAnnotationPackage(String annotationType) {
		Assert.hasText(annotationType, "annotationType must not be null or empty");
		return annotationType.startsWith("java.lang.annotation");
	}

	/**
	 * Retrieve the given annotation's attributes as a {@link Map}, preserving all
	 * attribute types.
	 * <p>Equivalent to calling {@link #getAnnotationAttributes(Annotation, boolean, boolean)}
	 * with the {@code classValuesAsString} and {@code nestedAnnotationsAsMap} parameters
	 * set to {@code false}.
	 * <p>Note: This method actually returns an {@link AnnotationAttributes} instance.
	 * However, the {@code Map} signature has been preserved for binary compatibility.
	 * @param annotation the annotation to retrieve the attributes for
	 * @return the Map of annotation attributes, with attribute names as keys and
	 * corresponding attribute values as values; never {@code null}
	 * @see #getAnnotationAttributes(AnnotatedElement, Annotation)
	 * @see #getAnnotationAttributes(Annotation, boolean, boolean)
	 * @see #getAnnotationAttributes(AnnotatedElement, Annotation, boolean, boolean)
	 */
	public static Map<String, Object> getAnnotationAttributes(Annotation annotation) {
		return getAnnotationAttributes(null, annotation);
	}

	/**
	 * Retrieve the given annotation's attributes as a {@link Map}.
	 * <p>Equivalent to calling {@link #getAnnotationAttributes(Annotation, boolean, boolean)}
	 * with the {@code nestedAnnotationsAsMap} parameter set to {@code false}.
	 * <p>Note: This method actually returns an {@link AnnotationAttributes} instance.
	 * However, the {@code Map} signature has been preserved for binary compatibility.
	 * @param annotation the annotation to retrieve the attributes for
	 * @param classValuesAsString whether to convert Class references into Strings (for
	 * compatibility with {@link org.springframework.core.type.AnnotationMetadata})
	 * or to preserve them as Class references
	 * @return the Map of annotation attributes, with attribute names as keys and
	 * corresponding attribute values as values; never {@code null}
	 * @see #getAnnotationAttributes(Annotation, boolean, boolean)
	 */
	public static Map<String, Object> getAnnotationAttributes(Annotation annotation, boolean classValuesAsString) {
		return getAnnotationAttributes(annotation, classValuesAsString, false);
	}

	/**
	 * Retrieve the given annotation's attributes as an {@link AnnotationAttributes} map.
	 * <p>This method provides fully recursive annotation reading capabilities on par with
	 * the reflection-based {@link org.springframework.core.type.StandardAnnotationMetadata}.
	 * @param annotation the annotation to retrieve the attributes for
	 * @param classValuesAsString whether to convert Class references into Strings (for
	 * compatibility with {@link org.springframework.core.type.AnnotationMetadata})
	 * or to preserve them as Class references
	 * @param nestedAnnotationsAsMap whether to convert nested annotations into
	 * {@link AnnotationAttributes} maps (for compatibility with
	 * {@link org.springframework.core.type.AnnotationMetadata}) or to preserve them as
	 * {@code Annotation} instances
	 * @return the annotation attributes (a specialized Map) with attribute names as keys
	 * and corresponding attribute values as values; never {@code null}
	 * @since 3.1.1
	 */
	public static AnnotationAttributes getAnnotationAttributes(Annotation annotation, boolean classValuesAsString,
			boolean nestedAnnotationsAsMap) {
		return getAnnotationAttributes(null, annotation, classValuesAsString, nestedAnnotationsAsMap);
	}

	/**
	 * Retrieve the given annotation's attributes as an {@link AnnotationAttributes} map.
	 * <p>Equivalent to calling {@link #getAnnotationAttributes(AnnotatedElement, Annotation, boolean, boolean)}
	 * with the {@code classValuesAsString} and {@code nestedAnnotationsAsMap} parameters
	 * set to {@code false}.
	 * @param annotatedElement the element that is annotated with the supplied annotation;
	 * may be {@code null} if unknown
	 * @param annotation the annotation to retrieve the attributes for
	 * @return the annotation attributes (a specialized Map) with attribute names as keys
	 * and corresponding attribute values as values; never {@code null}
	 * @since 4.2
	 * @see #getAnnotationAttributes(AnnotatedElement, Annotation, boolean, boolean)
	 */
	public static AnnotationAttributes getAnnotationAttributes(AnnotatedElement annotatedElement, Annotation annotation) {
		return getAnnotationAttributes(annotatedElement, annotation, false, false);
	}

	/**
	 * Retrieve the given annotation's attributes as an {@link AnnotationAttributes} map.
	 * <p>This method provides fully recursive annotation reading capabilities on par with
	 * the reflection-based {@link org.springframework.core.type.StandardAnnotationMetadata}.
	 * @param annotatedElement the element that is annotated with the supplied annotation;
	 * may be {@code null} if unknown
	 * @param annotation the annotation to retrieve the attributes for
	 * @param classValuesAsString whether to convert Class references into Strings (for
	 * compatibility with {@link org.springframework.core.type.AnnotationMetadata})
	 * or to preserve them as Class references
	 * @param nestedAnnotationsAsMap whether to convert nested annotations into
	 * {@link AnnotationAttributes} maps (for compatibility with
	 * {@link org.springframework.core.type.AnnotationMetadata}) or to preserve them as
	 * {@code Annotation} instances
	 * @return the annotation attributes (a specialized Map) with attribute names as keys
	 * and corresponding attribute values as values; never {@code null}
	 * @since 4.2
	 */
	public static AnnotationAttributes getAnnotationAttributes(AnnotatedElement annotatedElement,
			Annotation annotation, boolean classValuesAsString, boolean nestedAnnotationsAsMap) {

		return getAnnotationAttributes(annotatedElement, annotation, classValuesAsString, nestedAnnotationsAsMap, false);
	}

	/**
	 * Retrieve the given annotation's attributes as an {@link AnnotationAttributes} map.
	 *
	 * <p>This method provides fully recursive annotation reading capabilities on par with
	 * the reflection-based {@link org.springframework.core.type.StandardAnnotationMetadata}.
	 *
	 * <p><strong>NOTE</strong>: This variant of {@code getAnnotationAttributes()} is
	 * only intended for use within the framework. Specifically, the {@code mergeMode} flag
	 * can be set to {@code true} in order to support processing of attribute aliases while
	 * merging attributes within an annotation hierarchy. When running in <em>merge mode</em>,
	 * the following special rules apply:
	 * <ol>
	 * <li>The supplied annotation will <em>not</em> be
	 * {@linkplain #synthesizeAnnotation synthesized} before retrieving its attributes;
	 * however, nested annotations and arrays of nested annotations <em>will</em> be
	 * synthesized.</li>
	 * <li>Default values will be replaced with {@link #DEFAULT_VALUE_PLACEHOLDER}.</li>
	 * <li>The resulting, merged annotation attributes should eventually be
	 * {@linkplain #postProcessAnnotationAttributes post-processed} in order to
	 * ensure that placeholders have been replaced by actual default values and
	 * in order to enforce {@code @AliasFor} semantics.</li>
	 * </ol>
	 *
	 * @param annotatedElement the element that is annotated with the supplied annotation;
	 * may be {@code null} if unknown
	 * @param annotation the annotation to retrieve the attributes for
	 * @param classValuesAsString whether to convert Class references into Strings (for
	 * compatibility with {@link org.springframework.core.type.AnnotationMetadata})
	 * or to preserve them as Class references
	 * @param nestedAnnotationsAsMap whether to convert nested annotations into
	 * {@link AnnotationAttributes} maps (for compatibility with
	 * {@link org.springframework.core.type.AnnotationMetadata}) or to preserve them as
	 * {@code Annotation} instances
	 * @param mergeMode whether the annotation attributes should be created
	 * using <em>merge mode</em>
	 * @return the annotation attributes (a specialized Map) with attribute names as keys
	 * and corresponding attribute values as values; never {@code null}
	 * @since 4.2
	 * @see #postProcessAnnotationAttributes
	 */
	static AnnotationAttributes getAnnotationAttributes(AnnotatedElement annotatedElement, Annotation annotation,
			boolean classValuesAsString, boolean nestedAnnotationsAsMap, boolean mergeMode) {

		if (!mergeMode) {
			annotation = synthesizeAnnotation(annotation, annotatedElement);
		}

		Class<? extends Annotation> annotationType = annotation.annotationType();
		AnnotationAttributes attrs = new AnnotationAttributes(annotationType);
		for (Method method : getAttributeMethods(annotationType)) {
			try {
				Object value = method.invoke(annotation);
				Object defaultValue = method.getDefaultValue();
				if (mergeMode && (defaultValue != null)) {
					if (ObjectUtils.nullSafeEquals(value, defaultValue)) {
						value = DEFAULT_VALUE_PLACEHOLDER;
					}
				}
				attrs.put(method.getName(),
					adaptValue(annotatedElement, value, classValuesAsString, nestedAnnotationsAsMap));
			}
			catch (Exception ex) {
				if (ex instanceof InvocationTargetException) {
					Throwable targetException = ((InvocationTargetException) ex).getTargetException();
					rethrowAnnotationConfigurationException(targetException);
				}
				throw new IllegalStateException("Could not obtain annotation attribute value for " + method, ex);
			}
		}
		return attrs;
	}

	/**
	 * Adapt the given value according to the given class and nested annotation settings.
	 * <p>Nested annotations will be
	 * {@linkplain #synthesizeAnnotation(Annotation, AnnotatedElement) synthesized}.
	 * @param annotatedElement the element that is annotated, used for contextual
	 * logging; may be {@code null} if unknown
	 * @param value the annotation attribute value
	 * @param classValuesAsString whether to convert Class references into Strings (for
	 * compatibility with {@link org.springframework.core.type.AnnotationMetadata})
	 * or to preserve them as Class references
	 * @param nestedAnnotationsAsMap whether to convert nested annotations into
	 * {@link AnnotationAttributes} maps (for compatibility with
	 * {@link org.springframework.core.type.AnnotationMetadata}) or to preserve them as
	 * {@code Annotation} instances
	 * @return the adapted value, or the original value if no adaptation is needed
	 */
	static Object adaptValue(AnnotatedElement annotatedElement, Object value, boolean classValuesAsString,
			boolean nestedAnnotationsAsMap) {

		if (classValuesAsString) {
			if (value instanceof Class) {
				return ((Class<?>) value).getName();
			}
			else if (value instanceof Class[]) {
				Class<?>[] clazzArray = (Class<?>[]) value;
				String[] classNames = new String[clazzArray.length];
				for (int i = 0; i < clazzArray.length; i++) {
					classNames[i] = clazzArray[i].getName();
				}
				return classNames;
			}
		}

		if (value instanceof Annotation) {
			Annotation annotation = (Annotation) value;

			if (nestedAnnotationsAsMap) {
				return getAnnotationAttributes(annotatedElement, annotation, classValuesAsString,
					nestedAnnotationsAsMap);
			}
			else {
				return synthesizeAnnotation(annotation, annotatedElement);
			}
		}

		if (value instanceof Annotation[]) {
			Annotation[] annotations = (Annotation[]) value;

			if (nestedAnnotationsAsMap) {
				AnnotationAttributes[] mappedAnnotations = new AnnotationAttributes[annotations.length];
				for (int i = 0; i < annotations.length; i++) {
					mappedAnnotations[i] = getAnnotationAttributes(annotatedElement, annotations[i],
						classValuesAsString, nestedAnnotationsAsMap);
				}
				return mappedAnnotations;
			}
			else {
				return synthesizeAnnotationArray(annotations, annotatedElement);
			}
		}

		// Fallback
		return value;
	}

	/**
	 * Retrieve the <em>value</em> of the {@code value} attribute of a
	 * single-element Annotation, given an annotation instance.
	 * @param annotation the annotation instance from which to retrieve the value
	 * @return the attribute value, or {@code null} if not found
	 * @see #getValue(Annotation, String)
	 */
	public static Object getValue(Annotation annotation) {
		return getValue(annotation, VALUE);
	}

	/**
	 * Retrieve the <em>value</em> of a named attribute, given an annotation instance.
	 * @param annotation the annotation instance from which to retrieve the value
	 * @param attributeName the name of the attribute value to retrieve
	 * @return the attribute value, or {@code null} if not found
	 * @see #getValue(Annotation)
	 */
	public static Object getValue(Annotation annotation, String attributeName) {
		if (annotation == null || !StringUtils.hasText(attributeName)) {
			return null;
		}
		try {
			Method method = annotation.annotationType().getDeclaredMethod(attributeName);
			ReflectionUtils.makeAccessible(method);
			return method.invoke(annotation);
		}
		catch (Exception ex) {
			return null;
		}
	}

	/**
	 * Retrieve the <em>default value</em> of the {@code value} attribute
	 * of a single-element Annotation, given an annotation instance.
	 * @param annotation the annotation instance from which to retrieve the default value
	 * @return the default value, or {@code null} if not found
	 * @see #getDefaultValue(Annotation, String)
	 */
	public static Object getDefaultValue(Annotation annotation) {
		return getDefaultValue(annotation, VALUE);
	}

	/**
	 * Retrieve the <em>default value</em> of a named attribute, given an annotation instance.
	 * @param annotation the annotation instance from which to retrieve the default value
	 * @param attributeName the name of the attribute value to retrieve
	 * @return the default value of the named attribute, or {@code null} if not found
	 * @see #getDefaultValue(Class, String)
	 */
	public static Object getDefaultValue(Annotation annotation, String attributeName) {
		if (annotation == null) {
			return null;
		}
		return getDefaultValue(annotation.annotationType(), attributeName);
	}

	/**
	 * Retrieve the <em>default value</em> of the {@code value} attribute
	 * of a single-element Annotation, given the {@link Class annotation type}.
	 * @param annotationType the <em>annotation type</em> for which the default value should be retrieved
	 * @return the default value, or {@code null} if not found
	 * @see #getDefaultValue(Class, String)
	 */
	public static Object getDefaultValue(Class<? extends Annotation> annotationType) {
		return getDefaultValue(annotationType, VALUE);
	}

	/**
	 * Retrieve the <em>default value</em> of a named attribute, given the
	 * {@link Class annotation type}.
	 * @param annotationType the <em>annotation type</em> for which the default value should be retrieved
	 * @param attributeName the name of the attribute value to retrieve.
	 * @return the default value of the named attribute, or {@code null} if not found
	 * @see #getDefaultValue(Annotation, String)
	 */
	public static Object getDefaultValue(Class<? extends Annotation> annotationType, String attributeName) {
		if (annotationType == null || !StringUtils.hasText(attributeName)) {
			return null;
		}
		try {
			return annotationType.getDeclaredMethod(attributeName).getDefaultValue();
		}
		catch (Exception ex) {
			return null;
		}
	}

	/**
	 * <em>Synthesize</em> an annotation from the supplied {@code annotation}
	 * by wrapping it in a dynamic proxy that transparently enforces
	 * <em>attribute alias</em> semantics for annotation attributes that are
	 * annotated with {@link AliasFor @AliasFor}.
	 *
	 * @param annotation the annotation to synthesize
	 * @return the synthesized annotation, if the supplied annotation is
	 * <em>synthesizable</em>; {@code null} if the supplied annotation is
	 * {@code null}; otherwise, the supplied annotation unmodified
	 * @throws AnnotationConfigurationException if invalid configuration of
	 * {@code @AliasFor} is detected
	 * @since 4.2
	 * @see #synthesizeAnnotation(Annotation, AnnotatedElement)
	 */
	static <A extends Annotation> A synthesizeAnnotation(A annotation) {
		return synthesizeAnnotation(annotation, null);
	}

	/**
	 * <em>Synthesize</em> an annotation from the supplied {@code annotation}
	 * by wrapping it in a dynamic proxy that transparently enforces
	 * <em>attribute alias</em> semantics for annotation attributes that are
	 * annotated with {@link AliasFor @AliasFor}.
	 *
	 * @param annotation the annotation to synthesize
	 * @param annotatedElement the element that is annotated with the supplied
	 * annotation; may be {@code null} if unknown
	 * @return the synthesized annotation if the supplied annotation is
	 * <em>synthesizable</em>; {@code null} if the supplied annotation is
	 * {@code null}; otherwise the supplied annotation unmodified
	 * @throws AnnotationConfigurationException if invalid configuration of
	 * {@code @AliasFor} is detected
	 * @since 4.2
	 * @see #synthesizeAnnotation(Map, Class, AnnotatedElement)
	 */
	@SuppressWarnings("unchecked")
	public static <A extends Annotation> A synthesizeAnnotation(A annotation, AnnotatedElement annotatedElement) {
		if (annotation == null) {
			return null;
		}
		if (annotation instanceof SynthesizedAnnotation) {
			return annotation;
		}

		Class<? extends Annotation> annotationType = annotation.annotationType();
		if (!isSynthesizable(annotationType)) {
			return annotation;
		}

		AnnotationAttributeExtractor attributeExtractor = new DefaultAnnotationAttributeExtractor(annotation,
			annotatedElement);
		InvocationHandler handler = new SynthesizedAnnotationInvocationHandler(attributeExtractor);
		A synthesizedAnnotation = (A) Proxy.newProxyInstance(ClassUtils.getDefaultClassLoader(), new Class<?>[] {
			(Class<A>) annotationType, SynthesizedAnnotation.class }, handler);

		return synthesizedAnnotation;
	}

	/**
	 * <em>Synthesize</em> an annotation from the supplied map of annotation
	 * attributes by wrapping the map in a dynamic proxy that implements an
	 * annotation of the specified {@code annotationType} and transparently
	 * enforces <em>attribute alias</em> semantics for annotation attributes
	 * that are annotated with {@link AliasFor @AliasFor}.
	 * <p>The supplied map must contain key-value pairs for every attribute
	 * defined by the supplied {@code annotationType}.
	 * <p>Note that {@link AnnotationAttributes} is a specialized type of
	 * {@link Map} that is an ideal candidate for this method's
	 * {@code attributes} argument.
	 *
	 * @param attributes the map of annotation attributes to synthesize
	 * @param annotationType the type of annotation to synthesize; never {@code null}
	 * @param annotatedElement the element that is annotated with the annotation
	 * corresponding to the supplied attributes; may be {@code null} if unknown
	 * @return the synthesized annotation, or {@code null} if the supplied attributes
	 * map is {@code null}
	 * @throws AnnotationConfigurationException if invalid configuration is detected
	 * @since 4.2
	 * @see #synthesizeAnnotation(Annotation, AnnotatedElement)
	 */
	@SuppressWarnings("unchecked")
	public static <A extends Annotation> A synthesizeAnnotation(Map<String, Object> attributes,
			Class<A> annotationType, AnnotatedElement annotatedElement) {
		Assert.notNull(annotationType, "annotationType must not be null");

		if (attributes == null) {
			return null;
		}

		AnnotationAttributeExtractor attributeExtractor = new MapAnnotationAttributeExtractor(attributes,
			annotationType, annotatedElement);
		InvocationHandler handler = new SynthesizedAnnotationInvocationHandler(attributeExtractor);
		A synthesizedAnnotation = (A) Proxy.newProxyInstance(ClassUtils.getDefaultClassLoader(), new Class<?>[] {
			annotationType, SynthesizedAnnotation.class }, handler);

		return synthesizedAnnotation;
	}

	/**
	 * <em>Synthesize</em> the supplied array of {@code annotations} by
	 * creating a new array of the same size and type and populating it
	 * with {@linkplain #synthesizeAnnotation(Annotation) synthesized}
	 * versions of the annotations from the input array.
	 *
	 * @param annotations the array of annotations to synthesize
	 * @param annotatedElement the element that is annotated with the supplied
	 * array of annotations; may be {@code null} if unknown
	 * @return a new array of synthesized annotations, or {@code null} if
	 * the supplied array is {@code null}
	 * @throws AnnotationConfigurationException if invalid configuration of
	 * {@code @AliasFor} is detected
	 * @since 4.2
	 * @see #synthesizeAnnotation(Annotation, AnnotatedElement)
	 * @see #synthesizeAnnotation(Map, Class, AnnotatedElement)
	 */
	public static Annotation[] synthesizeAnnotationArray(Annotation[] annotations, AnnotatedElement annotatedElement) {
		if (annotations == null) {
			return null;
		}

		Annotation[] synthesized = (Annotation[]) Array.newInstance(annotations.getClass().getComponentType(), annotations.length);
		for (int i = 0; i < annotations.length; i++) {
			synthesized[i] = synthesizeAnnotation(annotations[i], annotatedElement);
		}
		return synthesized;
	}

	/**
	 * Get a map of all attribute alias pairs, declared via {@code @AliasFor}
	 * in the supplied annotation type.
	 *
	 * <p>The map is keyed by attribute name with each value representing
	 * the name of the aliased attribute. For each entry {@code [x, y]} in
	 * the map there will be a corresponding {@code [y, x]} entry in the map.
	 *
	 * <p>An empty return value implies that the annotation does not declare
	 * any attribute aliases.
	 *
	 * @param annotationType the annotation type to find attribute aliases in
	 * @return a map containing attribute alias pairs; never {@code null}
	 * @since 4.2
	 */
	static Map<String, String> getAttributeAliasMap(Class<? extends Annotation> annotationType) {
		if (annotationType == null) {
			return Collections.emptyMap();
		}

		Map<String, String> map = attributeAliasesCache.get(annotationType);
		if (map != null) {
			return map;
		}

		map = new HashMap<String, String>();
		for (Method attribute : getAttributeMethods(annotationType)) {
			String attributeName = attribute.getName();
			String aliasedAttributeName = getAliasedAttributeName(attribute);
			if (aliasedAttributeName != null) {
				map.put(attributeName, aliasedAttributeName);
			}
		}

		attributeAliasesCache.put(annotationType, map);

		return map;
	}

	/**
	 * Determine if annotations of the supplied {@code annotationType} are
	 * <em>synthesizable</em> (i.e., in need of being wrapped in a dynamic
	 * proxy that provides functionality above that of a standard JDK
	 * annotation).
	 *
	 * <p>Specifically, an annotation is <em>synthesizable</em> if it declares
	 * any attributes that are configured as <em>aliased pairs</em> via
	 * {@link AliasFor @AliasFor} or if any nested annotations used by the
	 * annotation declare such <em>aliased pairs</em>.
	 *
	 * @since 4.2
	 * @see SynthesizedAnnotation
	 * @see SynthesizedAnnotationInvocationHandler
	 */
	@SuppressWarnings("unchecked")
	private static boolean isSynthesizable(Class<? extends Annotation> annotationType) {

		Boolean synthesizable = synthesizableCache.get(annotationType);
		if (synthesizable != null) {
			return synthesizable.booleanValue();
		}

		synthesizable = Boolean.FALSE;

		for (Method attribute : getAttributeMethods(annotationType)) {
			if (getAliasedAttributeName(attribute) != null) {
				synthesizable = Boolean.TRUE;
				break;
			}

			Class<?> returnType = attribute.getReturnType();

			if (Annotation[].class.isAssignableFrom(returnType)) {
				Class<? extends Annotation> nestedAnnotationType = (Class<? extends Annotation>) returnType.getComponentType();
				if (isSynthesizable(nestedAnnotationType)) {
					synthesizable = Boolean.TRUE;
					break;
				}
			}
			else if (Annotation.class.isAssignableFrom(returnType)) {
				Class<? extends Annotation> nestedAnnotationType = (Class<? extends Annotation>) returnType;
				if (isSynthesizable(nestedAnnotationType)) {
					synthesizable = Boolean.TRUE;
					break;
				}
			}
		}

		synthesizableCache.put(annotationType, synthesizable);

		return synthesizable.booleanValue();
	}

	/**
	 * Get the name of the aliased attribute configured via
	 * {@link AliasFor @AliasFor} on the supplied annotation {@code attribute}.
	 *
	 * <p>This method does not resolve aliases in other annotations. In
	 * other words, if {@code @AliasFor} is present on the supplied
	 * {@code attribute} but {@linkplain AliasFor#annotation references an
	 * annotation} other than {@link Annotation}, this method will return
	 * {@code null} immediately.
	 *
	 * @param attribute the attribute to find an alias for
	 * @return the name of the aliased attribute, or {@code null} if not found
	 * @throws IllegalArgumentException if the supplied attribute method is
	 * not from an annotation, or if the supplied target type is {@link Annotation}
	 * @throws AnnotationConfigurationException if invalid configuration of
	 * {@code @AliasFor} is detected
	 * @since 4.2
	 * @see #getAliasedAttributeName(Method, Class)
	 */
	static String getAliasedAttributeName(Method attribute) {
		return getAliasedAttributeName(attribute, null);
	}

	/**
	 * Get the name of the aliased attribute configured via
	 * {@link AliasFor @AliasFor} on the supplied annotation {@code attribute}.
	 *
	 * @param attribute the attribute to find an alias for
	 * @param targetAnnotationType the type of annotation in which the
	 * aliased attribute is allowed to be declared; {@code null} implies
	 * <em>within the same annotation</em>
	 * @return the name of the aliased attribute, or {@code null} if not found
	 * @throws IllegalArgumentException if the supplied attribute method is
	 * not from an annotation, or if the supplied target type is {@link Annotation}
	 * @throws AnnotationConfigurationException if invalid configuration of
	 * {@code @AliasFor} is detected
	 * @since 4.2
	 */
	@SuppressWarnings("unchecked")
	static String getAliasedAttributeName(Method attribute, Class<? extends Annotation> targetAnnotationType) {
		Class<?> declaringClass = attribute.getDeclaringClass();
		Assert.isTrue(declaringClass.isAnnotation(), "attribute method must be from an annotation");
		Assert.isTrue(!Annotation.class.equals(targetAnnotationType),
			"targetAnnotationType must not be java.lang.annotation.Annotation");

		AliasFor aliasFor = attribute.getAnnotation(AliasFor.class);

		// Nothing to check
		if (aliasFor == null) {
			return null;
		}

		Class<? extends Annotation> sourceAnnotationType = (Class<? extends Annotation>) declaringClass;
		Class<? extends Annotation> aliasedAnnotationType = aliasFor.annotation();

		boolean searchWithinSameAnnotation = (targetAnnotationType == null);
		boolean sameTargetDeclared = (sourceAnnotationType.equals(aliasedAnnotationType) || Annotation.class.equals(aliasedAnnotationType));

		// Wrong search scope?
		if (searchWithinSameAnnotation && !sameTargetDeclared) {
			return null;
		}

		String attributeName = attribute.getName();
		String aliasedAttributeName = aliasFor.attribute();

		if (!StringUtils.hasText(aliasedAttributeName)) {
			String msg = String.format(
				"@AliasFor declaration on attribute [%s] in annotation [%s] is missing required 'attribute' value.",
				attributeName, sourceAnnotationType.getName());
			throw new AnnotationConfigurationException(msg);
		}

		if (sameTargetDeclared) {
			aliasedAnnotationType = sourceAnnotationType;
		}

		Method aliasedAttribute = null;
		try {
			aliasedAttribute = aliasedAnnotationType.getDeclaredMethod(aliasedAttributeName);
		}
		catch (NoSuchMethodException e) {
			String msg = String.format(
				"Attribute [%s] in annotation [%s] is declared as an @AliasFor nonexistent attribute [%s] in annotation [%s].",
				attributeName, sourceAnnotationType.getName(), aliasedAttributeName, aliasedAnnotationType.getName());
			throw new AnnotationConfigurationException(msg, e);
		}

		if (sameTargetDeclared) {
			AliasFor mirrorAliasFor = aliasedAttribute.getAnnotation(AliasFor.class);
			if (mirrorAliasFor == null) {
				String msg = String.format("Attribute [%s] in annotation [%s] must be declared as an @AliasFor [%s].",
					aliasedAttributeName, sourceAnnotationType.getName(), attributeName);
				throw new AnnotationConfigurationException(msg);
			}

			String mirrorAliasedAttributeName = mirrorAliasFor.attribute();
			if (!attributeName.equals(mirrorAliasedAttributeName)) {
				String msg = String.format(
					"Attribute [%s] in annotation [%s] must be declared as an @AliasFor [%s], not [%s].",
					aliasedAttributeName, sourceAnnotationType.getName(), attributeName, mirrorAliasedAttributeName);
				throw new AnnotationConfigurationException(msg);
			}
		}

		Class<?> returnType = attribute.getReturnType();
		Class<?> aliasedReturnType = aliasedAttribute.getReturnType();
		if (!returnType.equals(aliasedReturnType)) {
			String msg = String.format("Misconfigured aliases: attribute [%s] in annotation [%s] "
					+ "and attribute [%s] in annotation [%s] must declare the same return type.", attributeName,
				sourceAnnotationType.getName(), aliasedAttributeName, aliasedAnnotationType.getName());
			throw new AnnotationConfigurationException(msg);
		}

		if (sameTargetDeclared) {
			Object defaultValue = attribute.getDefaultValue();
			Object aliasedDefaultValue = aliasedAttribute.getDefaultValue();

			if ((defaultValue == null) || (aliasedDefaultValue == null)) {
				String msg = String.format("Misconfigured aliases: attribute [%s] in annotation [%s] "
						+ "and attribute [%s] in annotation [%s] must declare default values.", attributeName,
					sourceAnnotationType.getName(), aliasedAttributeName, aliasedAnnotationType.getName());
				throw new AnnotationConfigurationException(msg);
			}

			if (!ObjectUtils.nullSafeEquals(defaultValue, aliasedDefaultValue)) {
				String msg = String.format("Misconfigured aliases: attribute [%s] in annotation [%s] "
						+ "and attribute [%s] in annotation [%s] must declare the same default value.", attributeName,
					sourceAnnotationType.getName(), aliasedAttributeName, aliasedAnnotationType.getName());
				throw new AnnotationConfigurationException(msg);
			}
		}

		return aliasedAttributeName;
	}

	/**
	 * Get all methods declared in the supplied {@code annotationType} that
	 * match Java's requirements for annotation <em>attributes</em>.
	 *
	 * <p>All methods in the returned list will be
	 * {@linkplain ReflectionUtils#makeAccessible(Method) made accessible}.
	 *
	 * @param annotationType the type in which to search for attribute methods;
	 * never {@code null}
	 * @return all annotation attribute methods in the specified annotation
	 * type; never {@code null}, though potentially <em>empty</em>
	 * @since 4.2
	 */
	static List<Method> getAttributeMethods(Class<? extends Annotation> annotationType) {

		List<Method> methods = attributeMethodsCache.get(annotationType);
		if (methods != null) {
			return methods;
		}

		methods = new ArrayList<Method>();
		for (Method method : annotationType.getDeclaredMethods()) {
			if (isAttributeMethod(method)) {
				ReflectionUtils.makeAccessible(method);
				methods.add(method);
			}
		}

		attributeMethodsCache.put(annotationType, methods);

		return methods;
	}

	/**
	 * Determine if the supplied {@code method} is an annotation attribute method.
	 * @param method the method to check
	 * @return {@code true} if the method is an attribute method
	 */
	static boolean isAttributeMethod(Method method) {
		return ((method != null) && (method.getParameterTypes().length == 0) && (method.getReturnType() != void.class));
	}

	/**
	 * Determine if the supplied method is an "annotationType" method.
	 * @return {@code true} if the method is an "annotationType" method
	 * @see Annotation#annotationType()
	 */
	static boolean isAnnotationTypeMethod(Method method) {
		return ((method != null) && method.getName().equals("annotationType") && (method.getParameterTypes().length == 0));
	}

	/**
	 * Post-process the supplied {@link AnnotationAttributes}.
	 *
	 * <p>Specifically, this method enforces <em>attribute alias</em> semantics
	 * for annotation attributes that are annotated with {@link AliasFor @AliasFor}
	 * and replaces {@linkplain #DEFAULT_VALUE_PLACEHOLDER placeholders} with their
	 * original default values.
	 *
	 * @param element the element that is annotated with an annotation or
	 * annotation hierarchy from which the supplied attributes were created;
	 * may be {@code null} if unknown
	 * @param attributes the annotation attributes to post-process
	 * @param classValuesAsString whether to convert Class references into Strings (for
	 * compatibility with {@link org.springframework.core.type.AnnotationMetadata})
	 * or to preserve them as Class references
	 * @param nestedAnnotationsAsMap whether to convert nested annotations into
	 * {@link AnnotationAttributes} maps (for compatibility with
	 * {@link org.springframework.core.type.AnnotationMetadata}) or to preserve them as
	 * {@code Annotation} instances
	 * @since 4.2
	 * @see #getAnnotationAttributes(AnnotatedElement, Annotation, boolean, boolean, boolean)
	 * @see #DEFAULT_VALUE_PLACEHOLDER
	 * @see #getDefaultValue(Class, String)
	 */
	static void postProcessAnnotationAttributes(AnnotatedElement element, AnnotationAttributes attributes,
			boolean classValuesAsString, boolean nestedAnnotationsAsMap) {

		// Abort?
		if (attributes == null) {
			return;
		}

		Class<? extends Annotation> annotationType = attributes.annotationType();

		// Validate @AliasFor configuration
		Map<String, String> aliasMap = getAttributeAliasMap(annotationType);
		Set<String> validated = new HashSet<String>();
		for (String attributeName : aliasMap.keySet()) {
			String aliasedAttributeName = aliasMap.get(attributeName);

			if (validated.add(attributeName) && validated.add(aliasedAttributeName)) {
				Object value = attributes.get(attributeName);
				Object aliasedValue = attributes.get(aliasedAttributeName);

				if (!ObjectUtils.nullSafeEquals(value, aliasedValue) && (value != DEFAULT_VALUE_PLACEHOLDER)
						&& (aliasedValue != DEFAULT_VALUE_PLACEHOLDER)) {
					String elementAsString = (element == null ? "unknown element" : element.toString());
					String msg = String.format(
						"In AnnotationAttributes for annotation [%s] declared on [%s], attribute [%s] and its alias [%s] are "
								+ "declared with values of [%s] and [%s], but only one declaration is permitted.",
						annotationType.getName(), elementAsString, attributeName, aliasedAttributeName,
						ObjectUtils.nullSafeToString(value), ObjectUtils.nullSafeToString(aliasedValue));
					throw new AnnotationConfigurationException(msg);
				}

				// Replace default values with aliased values...
				if (value == DEFAULT_VALUE_PLACEHOLDER) {
					attributes.put(attributeName,
						adaptValue(element, aliasedValue, classValuesAsString, nestedAnnotationsAsMap));
				}
				if (aliasedValue == DEFAULT_VALUE_PLACEHOLDER) {
					attributes.put(aliasedAttributeName,
						adaptValue(element, value, classValuesAsString, nestedAnnotationsAsMap));
				}
			}
		}

		for (String attributeName : attributes.keySet()) {
			Object value = attributes.get(attributeName);
			if (value == DEFAULT_VALUE_PLACEHOLDER) {
				attributes.put(attributeName,
					adaptValue(element, getDefaultValue(annotationType, attributeName), classValuesAsString,
						nestedAnnotationsAsMap));
			}
		}
	}

	/**
	 * <p>If the supplied throwable is an {@link AnnotationConfigurationException},
	 * it will be cast to an {@code AnnotationConfigurationException} and thrown,
	 * allowing it to propagate to the caller.
	 * <p>Otherwise, this method does nothing.
	 * @param t the throwable to inspect
	 * @since 4.2
	 */
	static void rethrowAnnotationConfigurationException(Throwable t) {
		if (t instanceof AnnotationConfigurationException) {
			throw (AnnotationConfigurationException) t;
		}
	}

	/**
	 * Handle the supplied annotation introspection exception.
	 * <p>If the supplied exception is an {@link AnnotationConfigurationException},
	 * it will simply be thrown, allowing it to propagate to the caller, and
	 * nothing will be logged.
	 * <p>Otherwise, this method logs an introspection failure (in particular
	 * {@code TypeNotPresentExceptions}) &mdash; before moving on, pretending
	 * there were no annotations on this specific element.
	 * @param element the element that we tried to introspect annotations on
	 * @param ex the exception that we encountered
	 * @see #rethrowAnnotationConfigurationException
	 */
	static void handleIntrospectionFailure(AnnotatedElement element, Exception ex) {

		rethrowAnnotationConfigurationException(ex);

		Log loggerToUse = logger;
		if (loggerToUse == null) {
			loggerToUse = LogFactory.getLog(AnnotationUtils.class);
			logger = loggerToUse;
		}
		if (element instanceof Class && Annotation.class.isAssignableFrom((Class<?>) element)) {
			// Meta-annotation lookup on an annotation type
			if (logger.isDebugEnabled()) {
				logger.debug("Failed to introspect meta-annotations on [" + element + "]: " + ex);
			}
		}
		else {
			// Direct annotation lookup on regular Class, Method, Field
			if (loggerToUse.isInfoEnabled()) {
				logger.info("Failed to introspect annotations on [" + element + "]: " + ex);
			}
		}
	}


	/**
	 * Cache key for the AnnotatedElement cache.
	 */
	private static class AnnotationCacheKey {

		private final AnnotatedElement element;

		private final Class<? extends Annotation> annotationType;

		public AnnotationCacheKey(AnnotatedElement element, Class<? extends Annotation> annotationType) {
			this.element = element;
			this.annotationType = annotationType;
		}

		@Override
		public boolean equals(Object other) {
			if (this == other) {
				return true;
			}
			if (!(other instanceof AnnotationCacheKey)) {
				return false;
			}
			AnnotationCacheKey otherKey = (AnnotationCacheKey) other;
			return (this.element.equals(otherKey.element) &&
					ObjectUtils.nullSafeEquals(this.annotationType, otherKey.annotationType));
		}

		@Override
		public int hashCode() {
			return (this.element.hashCode() * 29 + this.annotationType.hashCode());
		}
	}


	private static class AnnotationCollector<A extends Annotation> {

		private final Class<? extends Annotation> containerAnnotationType;

		private final Class<A> annotationType;

		private final Set<AnnotatedElement> visited = new HashSet<AnnotatedElement>();

		private final Set<A> result = new LinkedHashSet<A>();

		public AnnotationCollector(Class<? extends Annotation> containerAnnotationType, Class<A> annotationType) {
			this.containerAnnotationType = containerAnnotationType;
			this.annotationType = annotationType;
		}

		public Set<A> getResult(AnnotatedElement element) {
			process(element);
			return Collections.unmodifiableSet(this.result);
		}

		@SuppressWarnings("unchecked")
		private void process(AnnotatedElement element) {
			if (this.visited.add(element)) {
				try {
					for (Annotation ann : element.getAnnotations()) {
						Class<? extends Annotation> currentAnnotationType = ann.annotationType();
						if (ObjectUtils.nullSafeEquals(this.annotationType, currentAnnotationType)) {
							this.result.add(synthesizeAnnotation((A) ann, element));
						}
						else if (ObjectUtils.nullSafeEquals(this.containerAnnotationType, currentAnnotationType)) {
							this.result.addAll(getValue(element, ann));
						}
						else if (!isInJavaLangAnnotationPackage(ann)) {
							process(currentAnnotationType);
						}
					}
				}
				catch (Exception ex) {
					handleIntrospectionFailure(element, ex);
				}
			}
		}

		@SuppressWarnings("unchecked")
		private List<A> getValue(AnnotatedElement element, Annotation annotation) {
			try {
				Method method = annotation.annotationType().getDeclaredMethod("value");
				ReflectionUtils.makeAccessible(method);
				A[] annotations = (A[]) method.invoke(annotation);

				List<A> synthesizedAnnotations = new ArrayList<A>();
				for (A anno : annotations) {
					synthesizedAnnotations.add(synthesizeAnnotation(anno, element));
				}
				return synthesizedAnnotations;
			}
			catch (Exception ex) {
				rethrowAnnotationConfigurationException(ex);
				// Unable to read value from repeating annotation container -> ignore it.
				return Collections.emptyList();
			}
		}
	}

}


File: spring-core/src/main/java/org/springframework/core/annotation/MapAnnotationAttributeExtractor.java
/*
 * Copyright 2002-2015 the original author or authors.
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

package org.springframework.core.annotation;

import java.lang.annotation.Annotation;
import java.lang.reflect.AnnotatedElement;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.springframework.util.ClassUtils;

import static org.springframework.core.annotation.AnnotationUtils.*;

/**
 * Implementation of the {@link AnnotationAttributeExtractor} strategy that
 * is backed by a {@link Map}.
 *
 * @author Sam Brannen
 * @since 4.2
 * @see Annotation
 * @see AliasFor
 * @see AbstractAliasAwareAnnotationAttributeExtractor
 * @see DefaultAnnotationAttributeExtractor
 * @see AnnotationUtils#synthesizeAnnotation(Map, Class, AnnotatedElement)
 */
class MapAnnotationAttributeExtractor extends AbstractAliasAwareAnnotationAttributeExtractor {

	/**
	 * Construct a new {@code MapAnnotationAttributeExtractor}.
	 * <p>The supplied map must contain key-value pairs for every attribute
	 * defined in the supplied {@code annotationType}.
	 * @param attributes the map of annotation attributes; never {@code null}
	 * @param annotationType the type of annotation to synthesize; never {@code null}
	 * @param annotatedElement the element that is annotated with the annotation
	 * of the supplied type; may be {@code null} if unknown
	 */
	MapAnnotationAttributeExtractor(Map<String, Object> attributes, Class<? extends Annotation> annotationType,
			AnnotatedElement annotatedElement) {
		super(annotationType, annotatedElement, new HashMap<String, Object>(attributes));
		validateAttributes(attributes, annotationType);
	}

	@Override
	protected Object getRawAttributeValue(Method attributeMethod) {
		return getMap().get(attributeMethod.getName());
	}

	@Override
	protected Object getRawAttributeValue(String attributeName) {
		return getMap().get(attributeName);
	}

	@SuppressWarnings("unchecked")
	private Map<String, Object> getMap() {
		return (Map<String, Object>) getSource();
	}

	/**
	 * Validate the supplied {@code attributes} map by verifying that it
	 * contains a non-null entry for each annotation attribute in the specified
	 * {@code annotationType} and that the type of the entry matches the
	 * return type for the corresponding annotation attribute.
	 */
	private static void validateAttributes(Map<String, Object> attributes, Class<? extends Annotation> annotationType) {
		for (Method attributeMethod : getAttributeMethods(annotationType)) {
			String attributeName = attributeMethod.getName();

			Object attributeValue = attributes.get(attributeName);
			if (attributeValue == null) {
				throw new IllegalArgumentException(String.format(
					"Attributes map [%s] returned null for required attribute [%s] defined by annotation type [%s].",
					attributes, attributeName, annotationType.getName()));
			}

			Class<?> returnType = attributeMethod.getReturnType();
			if (!ClassUtils.isAssignable(returnType, attributeValue.getClass())) {
				throw new IllegalArgumentException(String.format(
					"Attributes map [%s] returned a value of type [%s] for attribute [%s], "
							+ "but a value of type [%s] is required as defined by annotation type [%s].", attributes,
					attributeValue.getClass().getName(), attributeName, returnType.getName(), annotationType.getName()));
			}
		}
	}

}


File: spring-core/src/test/java/org/springframework/core/annotation/AnnotationUtilsTests.java
/*
 * Copyright 2002-2015 the original author or authors.
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

package org.springframework.core.annotation;

import java.lang.annotation.Annotation;
import java.lang.annotation.Inherited;
import java.lang.annotation.Repeatable;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import org.springframework.core.Ordered;
import org.springframework.core.annotation.subpackage.NonPublicAnnotatedClass;
import org.springframework.stereotype.Component;
import org.springframework.util.ClassUtils;

import static java.util.Arrays.*;
import static java.util.stream.Collectors.*;
import static org.hamcrest.Matchers.*;
import static org.junit.Assert.*;
import static org.springframework.core.annotation.AnnotationUtils.*;

/**
 * Unit tests for {@link AnnotationUtils}.
 *
 * @author Rod Johnson
 * @author Juergen Hoeller
 * @author Sam Brannen
 * @author Chris Beams
 * @author Phillip Webb
 */
public class AnnotationUtilsTests {

	@Rule
	public final ExpectedException exception = ExpectedException.none();

	@Test
	public void findMethodAnnotationOnLeaf() throws Exception {
		Method m = Leaf.class.getMethod("annotatedOnLeaf");
		assertNotNull(m.getAnnotation(Order.class));
		assertNotNull(getAnnotation(m, Order.class));
		assertNotNull(findAnnotation(m, Order.class));
	}

	/** @since 4.2 */
	@Test
	public void findMethodAnnotationWithAnnotationOnMethodInInterface() throws Exception {
		Method m = Leaf.class.getMethod("fromInterfaceImplementedByRoot");
		// @Order is not @Inherited
		assertNull(m.getAnnotation(Order.class));
		// getAnnotation() does not search on interfaces
		assertNull(getAnnotation(m, Order.class));
		// findAnnotation() does search on interfaces
		assertNotNull(findAnnotation(m, Order.class));
	}

	/** @since 4.2 */
	@Test
	public void findMethodAnnotationWithMetaAnnotationOnLeaf() throws Exception {
		Method m = Leaf.class.getMethod("metaAnnotatedOnLeaf");
		assertNull(m.getAnnotation(Order.class));
		assertNotNull(getAnnotation(m, Order.class));
		assertNotNull(findAnnotation(m, Order.class));
	}

	/** @since 4.2 */
	@Test
	public void findMethodAnnotationWithMetaMetaAnnotationOnLeaf() throws Exception {
		Method m = Leaf.class.getMethod("metaMetaAnnotatedOnLeaf");
		assertNull(m.getAnnotation(Component.class));
		assertNull(getAnnotation(m, Component.class));
		assertNotNull(findAnnotation(m, Component.class));
	}

	@Test
	public void findMethodAnnotationOnRoot() throws Exception {
		Method m = Leaf.class.getMethod("annotatedOnRoot");
		assertNotNull(m.getAnnotation(Order.class));
		assertNotNull(getAnnotation(m, Order.class));
		assertNotNull(findAnnotation(m, Order.class));
	}

	/** @since 4.2 */
	@Test
	public void findMethodAnnotationWithMetaAnnotationOnRoot() throws Exception {
		Method m = Leaf.class.getMethod("metaAnnotatedOnRoot");
		assertNull(m.getAnnotation(Order.class));
		assertNotNull(getAnnotation(m, Order.class));
		assertNotNull(findAnnotation(m, Order.class));
	}

	@Test
	public void findMethodAnnotationOnRootButOverridden() throws Exception {
		Method m = Leaf.class.getMethod("overrideWithoutNewAnnotation");
		assertNull(m.getAnnotation(Order.class));
		assertNull(getAnnotation(m, Order.class));
		assertNotNull(findAnnotation(m, Order.class));
	}

	@Test
	public void findMethodAnnotationNotAnnotated() throws Exception {
		Method m = Leaf.class.getMethod("notAnnotated");
		assertNull(findAnnotation(m, Order.class));
	}

	@Test
	public void findMethodAnnotationOnBridgeMethod() throws Exception {
		Method m = SimpleFoo.class.getMethod("something", Object.class);
		assertTrue(m.isBridge());
		assertNull(m.getAnnotation(Order.class));
		assertNull(getAnnotation(m, Order.class));
		assertNotNull(findAnnotation(m, Order.class));
		// TODO: getAnnotation() on bridge method actually found on OpenJDK 8 b99 and higher!
		// assertNull(m.getAnnotation(Transactional.class));
		assertNotNull(getAnnotation(m, Transactional.class));
		assertNotNull(findAnnotation(m, Transactional.class));
	}

	@Test
	public void findMethodAnnotationFromInterface() throws Exception {
		Method method = ImplementsInterfaceWithAnnotatedMethod.class.getMethod("foo");
		Order order = findAnnotation(method, Order.class);
		assertNotNull(order);
	}

	@Test
	public void findMethodAnnotationFromInterfaceOnSuper() throws Exception {
		Method method = SubOfImplementsInterfaceWithAnnotatedMethod.class.getMethod("foo");
		Order order = findAnnotation(method, Order.class);
		assertNotNull(order);
	}

	@Test
	public void findMethodAnnotationFromInterfaceWhenSuperDoesNotImplementMethod() throws Exception {
		Method method = SubOfAbstractImplementsInterfaceWithAnnotatedMethod.class.getMethod("foo");
		Order order = findAnnotation(method, Order.class);
		assertNotNull(order);
	}

	/** @since 4.1.2 */
	@Test
	public void findClassAnnotationFavorsMoreLocallyDeclaredComposedAnnotationsOverAnnotationsOnInterfaces() {
		Component component = findAnnotation(ClassWithLocalMetaAnnotationAndMetaAnnotatedInterface.class,
			Component.class);
		assertNotNull(component);
		assertEquals("meta2", component.value());
	}

	/** @since 4.0.3 */
	@Test
	public void findClassAnnotationFavorsMoreLocallyDeclaredComposedAnnotationsOverInheritedAnnotations() {
		Transactional transactional = findAnnotation(SubSubClassWithInheritedAnnotation.class, Transactional.class);
		assertNotNull(transactional);
		assertTrue("readOnly flag for SubSubClassWithInheritedAnnotation", transactional.readOnly());
	}

	/** @since 4.0.3 */
	@Test
	public void findClassAnnotationFavorsMoreLocallyDeclaredComposedAnnotationsOverInheritedComposedAnnotations() {
		Component component = findAnnotation(SubSubClassWithInheritedMetaAnnotation.class, Component.class);
		assertNotNull(component);
		assertEquals("meta2", component.value());
	}

	@Test
	public void findClassAnnotationOnMetaMetaAnnotatedClass() {
		Component component = findAnnotation(MetaMetaAnnotatedClass.class, Component.class);
		assertNotNull("Should find meta-annotation on composed annotation on class", component);
		assertEquals("meta2", component.value());
	}

	@Test
	public void findClassAnnotationOnMetaMetaMetaAnnotatedClass() {
		Component component = findAnnotation(MetaMetaMetaAnnotatedClass.class, Component.class);
		assertNotNull("Should find meta-annotation on meta-annotation on composed annotation on class", component);
		assertEquals("meta2", component.value());
	}

	@Test
	public void findClassAnnotationOnAnnotatedClassWithMissingTargetMetaAnnotation() {
		// TransactionalClass is NOT annotated or meta-annotated with @Component
		Component component = findAnnotation(TransactionalClass.class, Component.class);
		assertNull("Should not find @Component on TransactionalClass", component);
	}

	@Test
	public void findClassAnnotationOnMetaCycleAnnotatedClassWithMissingTargetMetaAnnotation() {
		Component component = findAnnotation(MetaCycleAnnotatedClass.class, Component.class);
		assertNull("Should not find @Component on MetaCycleAnnotatedClass", component);
	}

	/** @since 4.2 */
	@Test
	public void findClassAnnotationOnInheritedAnnotationInterface() {
		Transactional tx = findAnnotation(InheritedAnnotationInterface.class, Transactional.class);
		assertNotNull("Should find @Transactional on InheritedAnnotationInterface", tx);
	}

	/** @since 4.2 */
	@Test
	public void findClassAnnotationOnSubInheritedAnnotationInterface() {
		Transactional tx = findAnnotation(SubInheritedAnnotationInterface.class, Transactional.class);
		assertNotNull("Should find @Transactional on SubInheritedAnnotationInterface", tx);
	}

	/** @since 4.2 */
	@Test
	public void findClassAnnotationOnSubSubInheritedAnnotationInterface() {
		Transactional tx = findAnnotation(SubSubInheritedAnnotationInterface.class, Transactional.class);
		assertNotNull("Should find @Transactional on SubSubInheritedAnnotationInterface", tx);
	}

	/** @since 4.2 */
	@Test
	public void findClassAnnotationOnNonInheritedAnnotationInterface() {
		Order order = findAnnotation(NonInheritedAnnotationInterface.class, Order.class);
		assertNotNull("Should find @Order on NonInheritedAnnotationInterface", order);
	}

	/** @since 4.2 */
	@Test
	public void findClassAnnotationOnSubNonInheritedAnnotationInterface() {
		Order order = findAnnotation(SubNonInheritedAnnotationInterface.class, Order.class);
		assertNotNull("Should find @Order on SubNonInheritedAnnotationInterface", order);
	}

	/** @since 4.2 */
	@Test
	public void findClassAnnotationOnSubSubNonInheritedAnnotationInterface() {
		Order order = findAnnotation(SubSubNonInheritedAnnotationInterface.class, Order.class);
		assertNotNull("Should find @Order on SubSubNonInheritedAnnotationInterface", order);
	}

	@Test
	public void findAnnotationDeclaringClassForAllScenarios() throws Exception {
		// no class-level annotation
		assertNull(findAnnotationDeclaringClass(Transactional.class, NonAnnotatedInterface.class));
		assertNull(findAnnotationDeclaringClass(Transactional.class, NonAnnotatedClass.class));

		// inherited class-level annotation; note: @Transactional is inherited
		assertEquals(InheritedAnnotationInterface.class,
			findAnnotationDeclaringClass(Transactional.class, InheritedAnnotationInterface.class));
		assertNull(findAnnotationDeclaringClass(Transactional.class, SubInheritedAnnotationInterface.class));
		assertEquals(InheritedAnnotationClass.class,
			findAnnotationDeclaringClass(Transactional.class, InheritedAnnotationClass.class));
		assertEquals(InheritedAnnotationClass.class,
			findAnnotationDeclaringClass(Transactional.class, SubInheritedAnnotationClass.class));

		// non-inherited class-level annotation; note: @Order is not inherited,
		// but findAnnotationDeclaringClass() should still find it on classes.
		assertEquals(NonInheritedAnnotationInterface.class,
			findAnnotationDeclaringClass(Order.class, NonInheritedAnnotationInterface.class));
		assertNull(findAnnotationDeclaringClass(Order.class, SubNonInheritedAnnotationInterface.class));
		assertEquals(NonInheritedAnnotationClass.class,
			findAnnotationDeclaringClass(Order.class, NonInheritedAnnotationClass.class));
		assertEquals(NonInheritedAnnotationClass.class,
			findAnnotationDeclaringClass(Order.class, SubNonInheritedAnnotationClass.class));
	}

	@Test
	public void findAnnotationDeclaringClassForTypesWithSingleCandidateType() {
		// no class-level annotation
		List<Class<? extends Annotation>> transactionalCandidateList = Arrays.<Class<? extends Annotation>> asList(Transactional.class);
		assertNull(findAnnotationDeclaringClassForTypes(transactionalCandidateList, NonAnnotatedInterface.class));
		assertNull(findAnnotationDeclaringClassForTypes(transactionalCandidateList, NonAnnotatedClass.class));

		// inherited class-level annotation; note: @Transactional is inherited
		assertEquals(InheritedAnnotationInterface.class,
			findAnnotationDeclaringClassForTypes(transactionalCandidateList, InheritedAnnotationInterface.class));
		assertNull(findAnnotationDeclaringClassForTypes(transactionalCandidateList, SubInheritedAnnotationInterface.class));
		assertEquals(InheritedAnnotationClass.class,
			findAnnotationDeclaringClassForTypes(transactionalCandidateList, InheritedAnnotationClass.class));
		assertEquals(InheritedAnnotationClass.class,
			findAnnotationDeclaringClassForTypes(transactionalCandidateList, SubInheritedAnnotationClass.class));

		// non-inherited class-level annotation; note: @Order is not inherited,
		// but findAnnotationDeclaringClassForTypes() should still find it on classes.
		List<Class<? extends Annotation>> orderCandidateList = Arrays.<Class<? extends Annotation>> asList(Order.class);
		assertEquals(NonInheritedAnnotationInterface.class,
			findAnnotationDeclaringClassForTypes(orderCandidateList, NonInheritedAnnotationInterface.class));
		assertNull(findAnnotationDeclaringClassForTypes(orderCandidateList, SubNonInheritedAnnotationInterface.class));
		assertEquals(NonInheritedAnnotationClass.class,
			findAnnotationDeclaringClassForTypes(orderCandidateList, NonInheritedAnnotationClass.class));
		assertEquals(NonInheritedAnnotationClass.class,
			findAnnotationDeclaringClassForTypes(orderCandidateList, SubNonInheritedAnnotationClass.class));
	}

	@Test
	public void findAnnotationDeclaringClassForTypesWithMultipleCandidateTypes() {
		List<Class<? extends Annotation>> candidates = Arrays.<Class<? extends Annotation>> asList(Transactional.class, Order.class);

		// no class-level annotation
		assertNull(findAnnotationDeclaringClassForTypes(candidates, NonAnnotatedInterface.class));
		assertNull(findAnnotationDeclaringClassForTypes(candidates, NonAnnotatedClass.class));

		// inherited class-level annotation; note: @Transactional is inherited
		assertEquals(InheritedAnnotationInterface.class,
			findAnnotationDeclaringClassForTypes(candidates, InheritedAnnotationInterface.class));
		assertNull(findAnnotationDeclaringClassForTypes(candidates, SubInheritedAnnotationInterface.class));
		assertEquals(InheritedAnnotationClass.class,
			findAnnotationDeclaringClassForTypes(candidates, InheritedAnnotationClass.class));
		assertEquals(InheritedAnnotationClass.class,
			findAnnotationDeclaringClassForTypes(candidates, SubInheritedAnnotationClass.class));

		// non-inherited class-level annotation; note: @Order is not inherited,
		// but findAnnotationDeclaringClassForTypes() should still find it on classes.
		assertEquals(NonInheritedAnnotationInterface.class,
			findAnnotationDeclaringClassForTypes(candidates, NonInheritedAnnotationInterface.class));
		assertNull(findAnnotationDeclaringClassForTypes(candidates, SubNonInheritedAnnotationInterface.class));
		assertEquals(NonInheritedAnnotationClass.class,
			findAnnotationDeclaringClassForTypes(candidates, NonInheritedAnnotationClass.class));
		assertEquals(NonInheritedAnnotationClass.class,
			findAnnotationDeclaringClassForTypes(candidates, SubNonInheritedAnnotationClass.class));

		// class hierarchy mixed with @Transactional and @Order declarations
		assertEquals(TransactionalClass.class,
			findAnnotationDeclaringClassForTypes(candidates, TransactionalClass.class));
		assertEquals(TransactionalAndOrderedClass.class,
			findAnnotationDeclaringClassForTypes(candidates, TransactionalAndOrderedClass.class));
		assertEquals(TransactionalAndOrderedClass.class,
			findAnnotationDeclaringClassForTypes(candidates, SubTransactionalAndOrderedClass.class));
	}

	@Test
	public void isAnnotationDeclaredLocallyForAllScenarios() throws Exception {
		// no class-level annotation
		assertFalse(isAnnotationDeclaredLocally(Transactional.class, NonAnnotatedInterface.class));
		assertFalse(isAnnotationDeclaredLocally(Transactional.class, NonAnnotatedClass.class));

		// inherited class-level annotation; note: @Transactional is inherited
		assertTrue(isAnnotationDeclaredLocally(Transactional.class, InheritedAnnotationInterface.class));
		assertFalse(isAnnotationDeclaredLocally(Transactional.class, SubInheritedAnnotationInterface.class));
		assertTrue(isAnnotationDeclaredLocally(Transactional.class, InheritedAnnotationClass.class));
		assertFalse(isAnnotationDeclaredLocally(Transactional.class, SubInheritedAnnotationClass.class));

		// non-inherited class-level annotation; note: @Order is not inherited
		assertTrue(isAnnotationDeclaredLocally(Order.class, NonInheritedAnnotationInterface.class));
		assertFalse(isAnnotationDeclaredLocally(Order.class, SubNonInheritedAnnotationInterface.class));
		assertTrue(isAnnotationDeclaredLocally(Order.class, NonInheritedAnnotationClass.class));
		assertFalse(isAnnotationDeclaredLocally(Order.class, SubNonInheritedAnnotationClass.class));
	}

	@Test
	public void isAnnotationInheritedForAllScenarios() throws Exception {
		// no class-level annotation
		assertFalse(isAnnotationInherited(Transactional.class, NonAnnotatedInterface.class));
		assertFalse(isAnnotationInherited(Transactional.class, NonAnnotatedClass.class));

		// inherited class-level annotation; note: @Transactional is inherited
		assertFalse(isAnnotationInherited(Transactional.class, InheritedAnnotationInterface.class));
		// isAnnotationInherited() does not currently traverse interface
		// hierarchies. Thus the following, though perhaps counter intuitive,
		// must be false:
		assertFalse(isAnnotationInherited(Transactional.class, SubInheritedAnnotationInterface.class));
		assertFalse(isAnnotationInherited(Transactional.class, InheritedAnnotationClass.class));
		assertTrue(isAnnotationInherited(Transactional.class, SubInheritedAnnotationClass.class));

		// non-inherited class-level annotation; note: @Order is not inherited
		assertFalse(isAnnotationInherited(Order.class, NonInheritedAnnotationInterface.class));
		assertFalse(isAnnotationInherited(Order.class, SubNonInheritedAnnotationInterface.class));
		assertFalse(isAnnotationInherited(Order.class, NonInheritedAnnotationClass.class));
		assertFalse(isAnnotationInherited(Order.class, SubNonInheritedAnnotationClass.class));
	}

	@Test
	public void getAnnotationAttributesWithoutAttributeAliases() {
		Component component = WebController.class.getAnnotation(Component.class);
		assertNotNull(component);

		AnnotationAttributes attributes = (AnnotationAttributes) getAnnotationAttributes(component);
		assertNotNull(attributes);
		assertEquals("value attribute: ", "webController", attributes.getString(VALUE));
		assertEquals(Component.class, attributes.annotationType());
	}

	@Test
	public void getAnnotationAttributesWithNestedAnnotations() {
		ComponentScan componentScan = ComponentScanClass.class.getAnnotation(ComponentScan.class);
		assertNotNull(componentScan);

		AnnotationAttributes attributes = getAnnotationAttributes(ComponentScanClass.class, componentScan);
		assertNotNull(attributes);
		assertEquals(ComponentScan.class, attributes.annotationType());

		Filter[] filters = attributes.getAnnotationArray("excludeFilters", Filter.class);
		assertNotNull(filters);

		List<String> patterns = stream(filters).map(Filter::pattern).collect(toList());
		assertEquals(asList("*Foo", "*Bar"), patterns);
	}

	@Test
	public void getAnnotationAttributesWithAttributeAliases() throws Exception {
		Method method = WebController.class.getMethod("handleMappedWithValueAttribute");
		WebMapping webMapping = method.getAnnotation(WebMapping.class);
		AnnotationAttributes attributes = (AnnotationAttributes) getAnnotationAttributes(webMapping);
		assertNotNull(attributes);
		assertEquals(WebMapping.class, attributes.annotationType());
		assertEquals("name attribute: ", "foo", attributes.getString("name"));
		assertEquals("value attribute: ", "/test", attributes.getString(VALUE));
		assertEquals("path attribute: ", "/test", attributes.getString("path"));

		method = WebController.class.getMethod("handleMappedWithPathAttribute");
		webMapping = method.getAnnotation(WebMapping.class);
		attributes = (AnnotationAttributes) getAnnotationAttributes(webMapping);
		assertNotNull(attributes);
		assertEquals(WebMapping.class, attributes.annotationType());
		assertEquals("name attribute: ", "bar", attributes.getString("name"));
		assertEquals("value attribute: ", "/test", attributes.getString(VALUE));
		assertEquals("path attribute: ", "/test", attributes.getString("path"));

		method = WebController.class.getMethod("handleMappedWithDifferentPathAndValueAttributes");
		webMapping = method.getAnnotation(WebMapping.class);
		exception.expect(AnnotationConfigurationException.class);
		exception.expectMessage(containsString("attribute [value] and its alias [path]"));
		exception.expectMessage(containsString("values of [/enigma] and [/test]"));
		exception.expectMessage(containsString("but only one is permitted"));
		getAnnotationAttributes(webMapping);
	}

	@Test
	public void getValueFromAnnotation() throws Exception {
		Method method = SimpleFoo.class.getMethod("something", Object.class);
		Order order = findAnnotation(method, Order.class);

		assertEquals(1, getValue(order, VALUE));
		assertEquals(1, getValue(order));
	}

	@Test
	public void getValueFromNonPublicAnnotation() throws Exception {
		Annotation[] declaredAnnotations = NonPublicAnnotatedClass.class.getDeclaredAnnotations();
		assertEquals(1, declaredAnnotations.length);
		Annotation annotation = declaredAnnotations[0];
		assertNotNull(annotation);
		assertEquals("NonPublicAnnotation", annotation.annotationType().getSimpleName());
		assertEquals(42, getValue(annotation, VALUE));
		assertEquals(42, getValue(annotation));
	}

	@Test
	public void getDefaultValueFromAnnotation() throws Exception {
		Method method = SimpleFoo.class.getMethod("something", Object.class);
		Order order = findAnnotation(method, Order.class);

		assertEquals(Ordered.LOWEST_PRECEDENCE, getDefaultValue(order, VALUE));
		assertEquals(Ordered.LOWEST_PRECEDENCE, getDefaultValue(order));
	}

	@Test
	public void getDefaultValueFromNonPublicAnnotation() throws Exception {
		Annotation[] declaredAnnotations = NonPublicAnnotatedClass.class.getDeclaredAnnotations();
		assertEquals(1, declaredAnnotations.length);
		Annotation annotation = declaredAnnotations[0];
		assertNotNull(annotation);
		assertEquals("NonPublicAnnotation", annotation.annotationType().getSimpleName());
		assertEquals(-1, getDefaultValue(annotation, VALUE));
		assertEquals(-1, getDefaultValue(annotation));
	}

	@Test
	public void getDefaultValueFromAnnotationType() throws Exception {
		assertEquals(Ordered.LOWEST_PRECEDENCE, getDefaultValue(Order.class, VALUE));
		assertEquals(Ordered.LOWEST_PRECEDENCE, getDefaultValue(Order.class));
	}

	@Test
	public void findRepeatableAnnotationOnComposedAnnotation() {
		Repeatable repeatable = findAnnotation(MyRepeatableMeta.class, Repeatable.class);
		assertNotNull(repeatable);
		assertEquals(MyRepeatableContainer.class, repeatable.value());
	}

	@Test
	public void getRepeatableFromMethod() throws Exception {
		Method method = InterfaceWithRepeated.class.getMethod("foo");
		Set<MyRepeatable> annotations = getRepeatableAnnotation(method, MyRepeatableContainer.class, MyRepeatable.class);
		assertNotNull(annotations);
		List<String> values = annotations.stream().map(MyRepeatable::value).collect(toList());
		assertThat(values, equalTo(Arrays.asList("a", "b", "c", "meta")));
	}

	@Test
	public void getRepeatableWithMissingAttributeAliasDeclaration() throws Exception {
		exception.expect(AnnotationConfigurationException.class);
		exception.expectMessage(containsString("Attribute [value] in"));
		exception.expectMessage(containsString(BrokenContextConfig.class.getName()));
		exception.expectMessage(containsString("must be declared as an @AliasFor [locations]"));
		getRepeatableAnnotation(BrokenConfigHierarchyTestCase.class, BrokenHierarchy.class, BrokenContextConfig.class);
	}

	@Test
	public void getRepeatableWithAttributeAliases() throws Exception {
		Set<ContextConfig> annotations = getRepeatableAnnotation(ConfigHierarchyTestCase.class, Hierarchy.class,
			ContextConfig.class);
		assertNotNull(annotations);

		List<String> locations = annotations.stream().map(ContextConfig::locations).collect(toList());
		assertThat(locations, equalTo(Arrays.asList("A", "B")));

		List<String> values = annotations.stream().map(ContextConfig::value).collect(toList());
		assertThat(values, equalTo(Arrays.asList("A", "B")));
	}

	@Test
	public void getAliasedAttributeNameFromAliasedComposedAnnotation() throws Exception {
		Method attribute = AliasedComposedContextConfig.class.getDeclaredMethod("xmlConfigFile");
		assertEquals("locations", getAliasedAttributeName(attribute, ContextConfig.class));
	}

	@Test
	public void synthesizeAnnotationWithoutAttributeAliases() throws Exception {
		Component component = WebController.class.getAnnotation(Component.class);
		assertNotNull(component);
		Component synthesizedComponent = synthesizeAnnotation(component);
		assertNotNull(synthesizedComponent);
		assertSame(component, synthesizedComponent);
		assertEquals("value attribute: ", "webController", synthesizedComponent.value());
	}

	@Test
	public void synthesizeAnnotationsFromNullSources() throws Exception {
		assertNull("null annotation", synthesizeAnnotation(null, null));
		assertNull("null map", synthesizeAnnotation(null, WebMapping.class, null));
	}

	@Test
	public void synthesizeAlreadySynthesizedAnnotation() throws Exception {
		Method method = WebController.class.getMethod("handleMappedWithValueAttribute");
		WebMapping webMapping = method.getAnnotation(WebMapping.class);
		assertNotNull(webMapping);
		WebMapping synthesizedWebMapping = synthesizeAnnotation(webMapping);
		assertNotSame(webMapping, synthesizedWebMapping);
		WebMapping synthesizedAgainWebMapping = synthesizeAnnotation(synthesizedWebMapping);
		assertSame(synthesizedWebMapping, synthesizedAgainWebMapping);
		assertThat(synthesizedAgainWebMapping, instanceOf(SynthesizedAnnotation.class));

		assertNotNull(synthesizedAgainWebMapping);
		assertEquals("name attribute: ", "foo", synthesizedAgainWebMapping.name());
		assertEquals("aliased path attribute: ", "/test", synthesizedAgainWebMapping.path());
		assertEquals("actual value attribute: ", "/test", synthesizedAgainWebMapping.value());
	}

	@Test
	public void synthesizeAnnotationWithAttributeAliasForNonexistentAttribute() throws Exception {
		AliasForNonexistentAttribute annotation = AliasForNonexistentAttributeClass.class.getAnnotation(AliasForNonexistentAttribute.class);
		exception.expect(AnnotationConfigurationException.class);
		exception.expectMessage(containsString("Attribute [foo] in"));
		exception.expectMessage(containsString(AliasForNonexistentAttribute.class.getName()));
		exception.expectMessage(containsString("is declared as an @AliasFor nonexistent attribute [bar]"));
		synthesizeAnnotation(annotation);
	}

	@Test
	public void synthesizeAnnotationWithAttributeAliasWithoutMirroredAliasFor() throws Exception {
		AliasForWithoutMirroredAliasFor annotation = AliasForWithoutMirroredAliasForClass.class.getAnnotation(AliasForWithoutMirroredAliasFor.class);
		exception.expect(AnnotationConfigurationException.class);
		exception.expectMessage(containsString("Attribute [bar] in"));
		exception.expectMessage(containsString(AliasForWithoutMirroredAliasFor.class.getName()));
		exception.expectMessage(containsString("must be declared as an @AliasFor [foo]"));
		synthesizeAnnotation(annotation);
	}

	@Test
	public void synthesizeAnnotationWithAttributeAliasWithMirroredAliasForWrongAttribute() throws Exception {
		AliasForWithMirroredAliasForWrongAttribute annotation = AliasForWithMirroredAliasForWrongAttributeClass.class.getAnnotation(AliasForWithMirroredAliasForWrongAttribute.class);

		// Since JDK 7+ does not guarantee consistent ordering of methods returned using
		// reflection, we cannot make the test dependent on any specific ordering.
		//
		// In other words, we can't be certain which type of exception message we'll get,
		// so we allow for both possibilities.
		exception.expect(AnnotationConfigurationException.class);
		exception.expectMessage(containsString("Attribute [bar] in"));
		exception.expectMessage(containsString(AliasForWithMirroredAliasForWrongAttribute.class.getName()));
		exception.expectMessage(either(containsString("must be declared as an @AliasFor [foo], not [quux]")).
			or(containsString("is declared as an @AliasFor nonexistent attribute [quux]")));
		synthesizeAnnotation(annotation);
	}

	@Test
	public void synthesizeAnnotationWithAttributeAliasForAttributeOfDifferentType() throws Exception {
		AliasForAttributeOfDifferentType annotation = AliasForAttributeOfDifferentTypeClass.class.getAnnotation(AliasForAttributeOfDifferentType.class);
		exception.expect(AnnotationConfigurationException.class);
		exception.expectMessage(startsWith("Misconfigured aliases"));
		exception.expectMessage(containsString(AliasForAttributeOfDifferentType.class.getName()));
		// Since JDK 7+ does not guarantee consistent ordering of methods returned using
		// reflection, we cannot make the test dependent on any specific ordering.
		//
		// In other words, we don't know if "foo" or "bar" will come first.
		exception.expectMessage(containsString("attribute [foo]"));
		exception.expectMessage(containsString("attribute [bar]"));
		exception.expectMessage(containsString("must declare the same return type"));
		synthesizeAnnotation(annotation);
	}

	@Test
	public void synthesizeAnnotationWithAttributeAliasForWithMissingDefaultValues() throws Exception {
		AliasForWithMissingDefaultValues annotation = AliasForWithMissingDefaultValuesClass.class.getAnnotation(AliasForWithMissingDefaultValues.class);
		exception.expectMessage(startsWith("Misconfigured aliases"));
		exception.expectMessage(containsString(AliasForWithMissingDefaultValues.class.getName()));
		// Since JDK 7+ does not guarantee consistent ordering of methods returned using
		// reflection, we cannot make the test dependent on any specific ordering.
		//
		// In other words, we don't know if "foo" or "bar" will come first.
		exception.expectMessage(containsString("attribute [foo]"));
		exception.expectMessage(containsString("attribute [bar]"));
		exception.expectMessage(containsString("must declare default values"));
		synthesizeAnnotation(annotation);
	}

	@Test
	public void synthesizeAnnotationWithAttributeAliasForAttributeWithDifferentDefaultValue() throws Exception {
		AliasForAttributeWithDifferentDefaultValue annotation = AliasForAttributeWithDifferentDefaultValueClass.class.getAnnotation(AliasForAttributeWithDifferentDefaultValue.class);
		exception.expectMessage(startsWith("Misconfigured aliases"));
		exception.expectMessage(containsString(AliasForAttributeWithDifferentDefaultValue.class.getName()));
		// Since JDK 7+ does not guarantee consistent ordering of methods returned using
		// reflection, we cannot make the test dependent on any specific ordering.
		//
		// In other words, we don't know if "foo" or "bar" will come first.
		exception.expectMessage(containsString("attribute [foo]"));
		exception.expectMessage(containsString("attribute [bar]"));
		exception.expectMessage(containsString("must declare the same default value"));
		synthesizeAnnotation(annotation);
	}

	@Test
	public void synthesizeAnnotationWithAttributeAliases() throws Exception {
		Method method = WebController.class.getMethod("handleMappedWithValueAttribute");
		WebMapping webMapping = method.getAnnotation(WebMapping.class);
		assertNotNull(webMapping);

		WebMapping synthesizedWebMapping1 = synthesizeAnnotation(webMapping);
		assertNotNull(synthesizedWebMapping1);
		assertNotSame(webMapping, synthesizedWebMapping1);
		assertThat(synthesizedWebMapping1, instanceOf(SynthesizedAnnotation.class));

		assertEquals("name attribute: ", "foo", synthesizedWebMapping1.name());
		assertEquals("aliased path attribute: ", "/test", synthesizedWebMapping1.path());
		assertEquals("actual value attribute: ", "/test", synthesizedWebMapping1.value());

		WebMapping synthesizedWebMapping2 = synthesizeAnnotation(webMapping);
		assertNotNull(synthesizedWebMapping2);
		assertNotSame(webMapping, synthesizedWebMapping2);
		assertThat(synthesizedWebMapping2, instanceOf(SynthesizedAnnotation.class));

		assertEquals("name attribute: ", "foo", synthesizedWebMapping2.name());
		assertEquals("aliased path attribute: ", "/test", synthesizedWebMapping2.path());
		assertEquals("actual value attribute: ", "/test", synthesizedWebMapping2.value());
	}

	@Test
	public void synthesizeAnnotationFromMapWithoutAttributeAliases() throws Exception {
		Component component = WebController.class.getAnnotation(Component.class);
		assertNotNull(component);

		Map<String, Object> map = new HashMap<String, Object>();
		map.put(VALUE, "webController");
		Component synthesizedComponent = synthesizeAnnotation(map, Component.class, WebController.class);
		assertNotNull(synthesizedComponent);

		assertNotSame(component, synthesizedComponent);
		assertEquals("value from component: ", "webController", component.value());
		assertEquals("value from synthesized component: ", "webController", synthesizedComponent.value());
	}

	@Test
	public void synthesizeAnnotationFromMapWithMissingAttributeValue() throws Exception {
		exception.expect(IllegalArgumentException.class);
		exception.expectMessage(startsWith("Attributes map"));
		exception.expectMessage(containsString("returned null for required attribute [value]"));
		exception.expectMessage(containsString("defined by annotation type [" + Component.class.getName() + "]"));
		synthesizeAnnotation(new HashMap<String, Object>(), Component.class, null);
	}

	@Test
	public void synthesizeAnnotationFromMapWithNullAttributeValue() throws Exception {
		Map<String, Object> map = new HashMap<String, Object>();
		map.put(VALUE, null);

		exception.expect(IllegalArgumentException.class);
		exception.expectMessage(startsWith("Attributes map"));
		exception.expectMessage(containsString("returned null for required attribute [value]"));
		exception.expectMessage(containsString("defined by annotation type [" + Component.class.getName() + "]"));
		synthesizeAnnotation(map, Component.class, null);
	}

	@Test
	public void synthesizeAnnotationFromMapWithAttributeOfIncorrectType() throws Exception {
		Map<String, Object> map = new HashMap<String, Object>();
		map.put(VALUE, 42L);

		exception.expect(IllegalArgumentException.class);
		exception.expectMessage(startsWith("Attributes map"));
		exception.expectMessage(containsString("returned a value of type [java.lang.Long]"));
		exception.expectMessage(containsString("for attribute [value]"));
		exception.expectMessage(containsString("but a value of type [java.lang.String] is required"));
		exception.expectMessage(containsString("as defined by annotation type [" + Component.class.getName() + "]"));
		synthesizeAnnotation(map, Component.class, null);
	}

	@Test
	public void synthesizeAnnotationFromAnnotationAttributesWithoutAttributeAliases() throws Exception {

		// 1) Get an annotation
		Component component = WebController.class.getAnnotation(Component.class);
		assertNotNull(component);

		// 2) Convert the annotation into AnnotationAttributes
		AnnotationAttributes attributes = getAnnotationAttributes(WebController.class, component);
		assertNotNull(attributes);

		// 3) Synthesize the AnnotationAttributes back into an annotation
		Component synthesizedComponent = synthesizeAnnotation(attributes, Component.class, WebController.class);
		assertNotNull(synthesizedComponent);

		// 4) Verify that the original and synthesized annotations are equivalent
		assertNotSame(component, synthesizedComponent);
		assertEquals(component, synthesizedComponent);
		assertEquals("value from component: ", "webController", component.value());
		assertEquals("value from synthesized component: ", "webController", synthesizedComponent.value());
	}

	@Test
	public void toStringForSynthesizedAnnotations() throws Exception {
		Method methodWithPath = WebController.class.getMethod("handleMappedWithPathAttribute");
		WebMapping webMappingWithAliases = methodWithPath.getAnnotation(WebMapping.class);
		assertNotNull(webMappingWithAliases);

		Method methodWithPathAndValue = WebController.class.getMethod("handleMappedWithSamePathAndValueAttributes");
		WebMapping webMappingWithPathAndValue = methodWithPathAndValue.getAnnotation(WebMapping.class);
		assertNotNull(webMappingWithPathAndValue);

		WebMapping synthesizedWebMapping1 = synthesizeAnnotation(webMappingWithAliases);
		assertNotNull(synthesizedWebMapping1);
		WebMapping synthesizedWebMapping2 = synthesizeAnnotation(webMappingWithAliases);
		assertNotNull(synthesizedWebMapping2);

		assertThat(webMappingWithAliases.toString(), is(not(synthesizedWebMapping1.toString())));

		// The unsynthesized annotation for handleMappedWithSamePathAndValueAttributes()
		// should produce the same toString() results as synthesized annotations for
		// handleMappedWithPathAttribute()
		assertToStringForWebMappingWithPathAndValue(webMappingWithPathAndValue);
		assertToStringForWebMappingWithPathAndValue(synthesizedWebMapping1);
		assertToStringForWebMappingWithPathAndValue(synthesizedWebMapping2);
	}

	private void assertToStringForWebMappingWithPathAndValue(WebMapping webMapping) {
		String string = webMapping.toString();
		assertThat(string, startsWith("@" + WebMapping.class.getName() + "("));
		assertThat(string, containsString("value=/test"));
		assertThat(string, containsString("path=/test"));
		assertThat(string, containsString("name=bar"));
		assertThat(string, containsString("method="));
		assertThat(string, containsString("[GET, POST]"));
		assertThat(string, endsWith(")"));
	}

	@Test
	public void equalsForSynthesizedAnnotations() throws Exception {
		Method methodWithPath = WebController.class.getMethod("handleMappedWithPathAttribute");
		WebMapping webMappingWithAliases = methodWithPath.getAnnotation(WebMapping.class);
		assertNotNull(webMappingWithAliases);

		Method methodWithPathAndValue = WebController.class.getMethod("handleMappedWithSamePathAndValueAttributes");
		WebMapping webMappingWithPathAndValue = methodWithPathAndValue.getAnnotation(WebMapping.class);
		assertNotNull(webMappingWithPathAndValue);

		WebMapping synthesizedWebMapping1 = synthesizeAnnotation(webMappingWithAliases);
		assertNotNull(synthesizedWebMapping1);
		WebMapping synthesizedWebMapping2 = synthesizeAnnotation(webMappingWithAliases);
		assertNotNull(synthesizedWebMapping2);

		// Equality amongst standard annotations
		assertThat(webMappingWithAliases, is(webMappingWithAliases));
		assertThat(webMappingWithPathAndValue, is(webMappingWithPathAndValue));

		// Inequality amongst standard annotations
		assertThat(webMappingWithAliases, is(not(webMappingWithPathAndValue)));
		assertThat(webMappingWithPathAndValue, is(not(webMappingWithAliases)));

		// Equality amongst synthesized annotations
		assertThat(synthesizedWebMapping1, is(synthesizedWebMapping1));
		assertThat(synthesizedWebMapping2, is(synthesizedWebMapping2));
		assertThat(synthesizedWebMapping1, is(synthesizedWebMapping2));
		assertThat(synthesizedWebMapping2, is(synthesizedWebMapping1));

		// Equality between standard and synthesized annotations
		assertThat(synthesizedWebMapping1, is(webMappingWithPathAndValue));
		assertThat(webMappingWithPathAndValue, is(synthesizedWebMapping1));

		// Inequality between standard and synthesized annotations
		assertThat(synthesizedWebMapping1, is(not(webMappingWithAliases)));
		assertThat(webMappingWithAliases, is(not(synthesizedWebMapping1)));
	}

	@Test
	public void hashCodeForSynthesizedAnnotations() throws Exception {
		Method methodWithPath = WebController.class.getMethod("handleMappedWithPathAttribute");
		WebMapping webMappingWithAliases = methodWithPath.getAnnotation(WebMapping.class);
		assertNotNull(webMappingWithAliases);

		Method methodWithPathAndValue = WebController.class.getMethod("handleMappedWithSamePathAndValueAttributes");
		WebMapping webMappingWithPathAndValue = methodWithPathAndValue.getAnnotation(WebMapping.class);
		assertNotNull(webMappingWithPathAndValue);

		WebMapping synthesizedWebMapping1 = synthesizeAnnotation(webMappingWithAliases);
		assertNotNull(synthesizedWebMapping1);
		WebMapping synthesizedWebMapping2 = synthesizeAnnotation(webMappingWithAliases);
		assertNotNull(synthesizedWebMapping2);

		// Equality amongst standard annotations
		assertThat(webMappingWithAliases.hashCode(), is(webMappingWithAliases.hashCode()));
		assertThat(webMappingWithPathAndValue.hashCode(), is(webMappingWithPathAndValue.hashCode()));

		// Inequality amongst standard annotations
		assertThat(webMappingWithAliases.hashCode(), is(not(webMappingWithPathAndValue.hashCode())));
		assertThat(webMappingWithPathAndValue.hashCode(), is(not(webMappingWithAliases.hashCode())));

		// Equality amongst synthesized annotations
		assertThat(synthesizedWebMapping1.hashCode(), is(synthesizedWebMapping1.hashCode()));
		assertThat(synthesizedWebMapping2.hashCode(), is(synthesizedWebMapping2.hashCode()));
		assertThat(synthesizedWebMapping1.hashCode(), is(synthesizedWebMapping2.hashCode()));
		assertThat(synthesizedWebMapping2.hashCode(), is(synthesizedWebMapping1.hashCode()));

		// Equality between standard and synthesized annotations
		assertThat(synthesizedWebMapping1.hashCode(), is(webMappingWithPathAndValue.hashCode()));
		assertThat(webMappingWithPathAndValue.hashCode(), is(synthesizedWebMapping1.hashCode()));

		// Inequality between standard and synthesized annotations
		assertThat(synthesizedWebMapping1.hashCode(), is(not(webMappingWithAliases.hashCode())));
		assertThat(webMappingWithAliases.hashCode(), is(not(synthesizedWebMapping1.hashCode())));
	}

	/**
	 * Fully reflection-based test that verifies support for
	 * {@linkplain AnnotationUtils#synthesizeAnnotation synthesizing annotations}
	 * across packages with non-public visibility of user types (e.g., a non-public
	 * annotation that uses {@code @AliasFor}).
	 */
	@Test
	@SuppressWarnings("unchecked")
	public void synthesizeNonPublicAnnotationWithAttributeAliasesFromDifferentPackage() throws Exception {

		Class<?> clazz =
			ClassUtils.forName("org.springframework.core.annotation.subpackage.NonPublicAliasedAnnotatedClass", null);
		Class<? extends Annotation> annotationType = (Class<? extends Annotation>)
			ClassUtils.forName("org.springframework.core.annotation.subpackage.NonPublicAliasedAnnotation", null);

		Annotation annotation = clazz.getAnnotation(annotationType);
		assertNotNull(annotation);
		Annotation synthesizedAnnotation = synthesizeAnnotation(annotation);
		assertNotSame(annotation, synthesizedAnnotation);

		assertNotNull(synthesizedAnnotation);
		assertEquals("name attribute: ", "test", getValue(synthesizedAnnotation, "name"));
		assertEquals("aliased path attribute: ", "/test", getValue(synthesizedAnnotation, "path"));
		assertEquals("aliased path attribute: ", "/test", getValue(synthesizedAnnotation, "value"));
	}

	@Test
	public void synthesizeAnnotationWithAttributeAliasesInNestedAnnotations() throws Exception {
		Hierarchy hierarchy = ConfigHierarchyTestCase.class.getAnnotation(Hierarchy.class);
		assertNotNull(hierarchy);
		Hierarchy synthesizedHierarchy = synthesizeAnnotation(hierarchy);
		assertNotSame(hierarchy, synthesizedHierarchy);
		assertThat(synthesizedHierarchy, instanceOf(SynthesizedAnnotation.class));

		ContextConfig[] configs = synthesizedHierarchy.value();
		assertNotNull(configs);
		assertTrue("nested annotations must be synthesized",
			Arrays.stream(configs).allMatch(c -> c instanceof SynthesizedAnnotation));

		List<String> locations = Arrays.stream(configs).map(ContextConfig::locations).collect(toList());
		assertThat(locations, equalTo(Arrays.asList("A", "B")));

		List<String> values = Arrays.stream(configs).map(ContextConfig::value).collect(toList());
		assertThat(values, equalTo(Arrays.asList("A", "B")));
	}

	@Test
	public void synthesizeAnnotationWithArrayOfAnnotations() throws Exception {
		Hierarchy hierarchy = ConfigHierarchyTestCase.class.getAnnotation(Hierarchy.class);
		assertNotNull(hierarchy);
		Hierarchy synthesizedHierarchy = synthesizeAnnotation(hierarchy);
		assertThat(synthesizedHierarchy, instanceOf(SynthesizedAnnotation.class));

		ContextConfig contextConfig = SimpleConfigTestCase.class.getAnnotation(ContextConfig.class);
		assertNotNull(contextConfig);

		ContextConfig[] configs = synthesizedHierarchy.value();
		List<String> locations = Arrays.stream(configs).map(ContextConfig::locations).collect(toList());
		assertThat(locations, equalTo(Arrays.asList("A", "B")));

		// Alter array returned from synthesized annotation
		configs[0] = contextConfig;

		// Re-retrieve the array from the synthesized annotation
		configs = synthesizedHierarchy.value();
		List<String> values = Arrays.stream(configs).map(ContextConfig::value).collect(toList());
		assertThat(values, equalTo(Arrays.asList("A", "B")));
	}

	@Test
	public void synthesizeAnnotationWithArrayOfChars() throws Exception {
		CharsContainer charsContainer = GroupOfCharsClass.class.getAnnotation(CharsContainer.class);
		assertNotNull(charsContainer);
		CharsContainer synthesizedCharsContainer = synthesizeAnnotation(charsContainer);
		assertThat(synthesizedCharsContainer, instanceOf(SynthesizedAnnotation.class));

		char[] chars = synthesizedCharsContainer.chars();
		assertArrayEquals(new char[] { 'x', 'y', 'z' }, chars);

		// Alter array returned from synthesized annotation
		chars[0] = '?';

		// Re-retrieve the array from the synthesized annotation
		chars = synthesizedCharsContainer.chars();
		assertArrayEquals(new char[] { 'x', 'y', 'z' }, chars);
	}


	@Component(value = "meta1")
	@Order
	@Retention(RetentionPolicy.RUNTIME)
	@Inherited
	@interface Meta1 {
	}

	@Component(value = "meta2")
	@Transactional(readOnly = true)
	@Retention(RetentionPolicy.RUNTIME)
	@interface Meta2 {
	}

	@Meta2
	@Retention(RetentionPolicy.RUNTIME)
	@interface MetaMeta {
	}

	@MetaMeta
	@Retention(RetentionPolicy.RUNTIME)
	@interface MetaMetaMeta {
	}

	@MetaCycle3
	@Retention(RetentionPolicy.RUNTIME)
	@interface MetaCycle1 {
	}

	@MetaCycle1
	@Retention(RetentionPolicy.RUNTIME)
	@interface MetaCycle2 {
	}

	@MetaCycle2
	@Retention(RetentionPolicy.RUNTIME)
	@interface MetaCycle3 {
	}

	@Meta1
	interface InterfaceWithMetaAnnotation {
	}

	@Meta2
	static class ClassWithLocalMetaAnnotationAndMetaAnnotatedInterface implements InterfaceWithMetaAnnotation {
	}

	@Meta1
	static class ClassWithInheritedMetaAnnotation {
	}

	@Meta2
	static class SubClassWithInheritedMetaAnnotation extends ClassWithInheritedMetaAnnotation {
	}

	static class SubSubClassWithInheritedMetaAnnotation extends SubClassWithInheritedMetaAnnotation {
	}

	@Transactional
	static class ClassWithInheritedAnnotation {
	}

	@Meta2
	static class SubClassWithInheritedAnnotation extends ClassWithInheritedAnnotation {
	}

	static class SubSubClassWithInheritedAnnotation extends SubClassWithInheritedAnnotation {
	}

	@MetaMeta
	static class MetaMetaAnnotatedClass {
	}

	@MetaMetaMeta
	static class MetaMetaMetaAnnotatedClass {
	}

	@MetaCycle3
	static class MetaCycleAnnotatedClass {
	}

	public interface AnnotatedInterface {

		@Order(0)
		void fromInterfaceImplementedByRoot();
	}

	public static class Root implements AnnotatedInterface {

		@Order(27)
		public void annotatedOnRoot() {
		}

		@Meta1
		public void metaAnnotatedOnRoot() {
		}

		public void overrideToAnnotate() {
		}

		@Order(27)
		public void overrideWithoutNewAnnotation() {
		}

		public void notAnnotated() {
		}

		@Override
		public void fromInterfaceImplementedByRoot() {
		}
	}

	public static class Leaf extends Root {

		@Order(25)
		public void annotatedOnLeaf() {
		}

		@Meta1
		public void metaAnnotatedOnLeaf() {
		}

		@MetaMeta
		public void metaMetaAnnotatedOnLeaf() {
		}

		@Override
		@Order(1)
		public void overrideToAnnotate() {
		}

		@Override
		public void overrideWithoutNewAnnotation() {
		}
	}

	@Retention(RetentionPolicy.RUNTIME)
	@Inherited
	@interface Transactional {

		boolean readOnly() default false;
	}

	public static abstract class Foo<T> {

		@Order(1)
		public abstract void something(T arg);
	}

	public static class SimpleFoo extends Foo<String> {

		@Override
		@Transactional
		public void something(final String arg) {
		}
	}

	@Transactional
	public interface InheritedAnnotationInterface {
	}

	public interface SubInheritedAnnotationInterface extends InheritedAnnotationInterface {
	}

	public interface SubSubInheritedAnnotationInterface extends SubInheritedAnnotationInterface {
	}

	@Order
	public interface NonInheritedAnnotationInterface {
	}

	public interface SubNonInheritedAnnotationInterface extends NonInheritedAnnotationInterface {
	}

	public interface SubSubNonInheritedAnnotationInterface extends SubNonInheritedAnnotationInterface {
	}

	public static class NonAnnotatedClass {
	}

	public interface NonAnnotatedInterface {
	}

	@Transactional
	public static class InheritedAnnotationClass {
	}

	public static class SubInheritedAnnotationClass extends InheritedAnnotationClass {
	}

	@Order
	public static class NonInheritedAnnotationClass {
	}

	public static class SubNonInheritedAnnotationClass extends NonInheritedAnnotationClass {
	}

	@Transactional
	public static class TransactionalClass {
	}

	@Order
	public static class TransactionalAndOrderedClass extends TransactionalClass {
	}

	public static class SubTransactionalAndOrderedClass extends TransactionalAndOrderedClass {
	}

	public interface InterfaceWithAnnotatedMethod {

		@Order
		void foo();
	}

	public static class ImplementsInterfaceWithAnnotatedMethod implements InterfaceWithAnnotatedMethod {

		@Override
		public void foo() {
		}
	}

	public static class SubOfImplementsInterfaceWithAnnotatedMethod extends ImplementsInterfaceWithAnnotatedMethod {

		@Override
		public void foo() {
		}
	}

	public abstract static class AbstractDoesNotImplementInterfaceWithAnnotatedMethod
			implements InterfaceWithAnnotatedMethod {
	}

	public static class SubOfAbstractImplementsInterfaceWithAnnotatedMethod
			extends AbstractDoesNotImplementInterfaceWithAnnotatedMethod {

		@Override
		public void foo() {
		}
	}

	@Retention(RetentionPolicy.RUNTIME)
	@Inherited
	@interface MyRepeatableContainer {

		MyRepeatable[] value();
	}

	@Retention(RetentionPolicy.RUNTIME)
	@Inherited
	@Repeatable(MyRepeatableContainer.class)
	@interface MyRepeatable {

		String value();
	}

	@Retention(RetentionPolicy.RUNTIME)
	@Inherited
	@MyRepeatable("meta")
	@interface MyRepeatableMeta {
	}

	public interface InterfaceWithRepeated {

		@MyRepeatable("a")
		@MyRepeatableContainer({ @MyRepeatable("b"), @MyRepeatable("c") })
		@MyRepeatableMeta
		void foo();
	}

	enum RequestMethod {
		GET, POST
	}

	/**
	 * Mock of {@code org.springframework.web.bind.annotation.RequestMapping}.
	 */
	@Retention(RetentionPolicy.RUNTIME)
	@interface WebMapping {

		String name();

		@AliasFor(attribute = "path")
		String value() default "";

		@AliasFor(attribute = "value")
		String path() default "";

		RequestMethod[] method() default {};
	}

	@Component("webController")
	static class WebController {

		@WebMapping(value = "/test", name = "foo")
		public void handleMappedWithValueAttribute() {
		}

		@WebMapping(path = "/test", name = "bar", method = { RequestMethod.GET, RequestMethod.POST })
		public void handleMappedWithPathAttribute() {
		}

		/**
		 * mapping is logically "equal" to handleMappedWithPathAttribute().
		 */
		@WebMapping(value = "/test", path = "/test", name = "bar", method = { RequestMethod.GET, RequestMethod.POST })
		public void handleMappedWithSamePathAndValueAttributes() {
		}

		@WebMapping(value = "/enigma", path = "/test", name = "baz")
		public void handleMappedWithDifferentPathAndValueAttributes() {
		}
	}

	/**
	 * Mock of {@code org.springframework.test.context.ContextConfiguration}.
	 */
	@Retention(RetentionPolicy.RUNTIME)
	@interface ContextConfig {

		@AliasFor(attribute = "locations")
		String value() default "";

		@AliasFor(attribute = "value")
		String locations() default "";
	}

	@Retention(RetentionPolicy.RUNTIME)
	@interface BrokenContextConfig {

		// Intentionally missing:
		// @AliasFor(attribute = "locations")
		String value() default "";

		@AliasFor(attribute = "value")
		String locations() default "";
	}

	/**
	 * Mock of {@code org.springframework.test.context.ContextHierarchy}.
	 */
	@Retention(RetentionPolicy.RUNTIME)
	@interface Hierarchy {
		ContextConfig[] value();
	}

	@Retention(RetentionPolicy.RUNTIME)
	@interface BrokenHierarchy {
		BrokenContextConfig[] value();
	}

	@Hierarchy({ @ContextConfig("A"), @ContextConfig(locations = "B") })
	static class ConfigHierarchyTestCase {
	}

	@BrokenHierarchy(@BrokenContextConfig)
	static class BrokenConfigHierarchyTestCase {
	}

	@ContextConfig("simple.xml")
	static class SimpleConfigTestCase {
	}

	@Retention(RetentionPolicy.RUNTIME)
	@interface CharsContainer {

		@AliasFor(attribute = "chars")
		char[] value() default {};

		@AliasFor(attribute = "value")
		char[] chars() default {};
	}

	@CharsContainer(chars = { 'x', 'y', 'z' })
	static class GroupOfCharsClass {
	}


	@Retention(RetentionPolicy.RUNTIME)
	@interface AliasForNonexistentAttribute {

		@AliasFor(attribute = "bar")
		String foo() default "";
	}

	@AliasForNonexistentAttribute
	static class AliasForNonexistentAttributeClass {
	}

	@Retention(RetentionPolicy.RUNTIME)
	@interface AliasForWithoutMirroredAliasFor {

		@AliasFor(attribute = "bar")
		String foo() default "";

		String bar() default "";
	}

	@AliasForWithoutMirroredAliasFor
	static class AliasForWithoutMirroredAliasForClass {
	}

	@Retention(RetentionPolicy.RUNTIME)
	@interface AliasForWithMirroredAliasForWrongAttribute {

		@AliasFor(attribute = "bar")
		String[] foo() default "";

		@AliasFor(attribute = "quux")
		String[] bar() default "";
	}

	@AliasForWithMirroredAliasForWrongAttribute
	static class AliasForWithMirroredAliasForWrongAttributeClass {
	}

	@Retention(RetentionPolicy.RUNTIME)
	@interface AliasForAttributeOfDifferentType {

		@AliasFor(attribute = "bar")
		String[] foo() default "";

		@AliasFor(attribute = "foo")
		boolean bar() default true;
	}

	@AliasForAttributeOfDifferentType
	static class AliasForAttributeOfDifferentTypeClass {
	}

	@Retention(RetentionPolicy.RUNTIME)
	@interface AliasForWithMissingDefaultValues {

		@AliasFor(attribute = "bar")
		String foo();

		@AliasFor(attribute = "foo")
		String bar();
	}

	@AliasForWithMissingDefaultValues(foo = "foo", bar = "bar")
	static class AliasForWithMissingDefaultValuesClass {
	}

	@Retention(RetentionPolicy.RUNTIME)
	@interface AliasForAttributeWithDifferentDefaultValue {

		@AliasFor(attribute = "bar")
		String foo() default "X";

		@AliasFor(attribute = "foo")
		String bar() default "Z";
	}

	@AliasForAttributeWithDifferentDefaultValue
	static class AliasForAttributeWithDifferentDefaultValueClass {
	}

	@ContextConfig
	@Retention(RetentionPolicy.RUNTIME)
	@interface AliasedComposedContextConfig {

		@AliasFor(annotation = ContextConfig.class, attribute = "locations")
		String xmlConfigFile();
	}

	@Retention(RetentionPolicy.RUNTIME)
	@Target({})
	@interface Filter {
		String pattern();
	}

	/**
	 * Mock of {@code org.springframework.context.annotation.ComponentScan}
	 */
	@Retention(RetentionPolicy.RUNTIME)
	@interface ComponentScan {
		Filter[] excludeFilters() default {};
	}

	@ComponentScan(excludeFilters = { @Filter(pattern = "*Foo"), @Filter(pattern = "*Bar") })
	static class ComponentScanClass {
	}

}


File: spring-test/src/main/java/org/springframework/test/context/transaction/TransactionalTestExecutionListener.java
/*
 * Copyright 2002-2015 the original author or authors.
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

package org.springframework.test.context.transaction;

import java.lang.annotation.Annotation;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.springframework.beans.BeansException;
import org.springframework.beans.factory.BeanFactory;
import org.springframework.beans.factory.annotation.BeanFactoryAnnotationUtils;
import org.springframework.core.annotation.AnnotatedElementUtils;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.TestContext;
import org.springframework.test.context.support.AbstractTestExecutionListener;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import org.springframework.transaction.interceptor.TransactionAttribute;
import org.springframework.transaction.interceptor.TransactionAttributeSource;
import org.springframework.util.Assert;
import org.springframework.util.ReflectionUtils;
import org.springframework.util.StringUtils;

import static org.springframework.core.annotation.AnnotationUtils.*;

/**
 * {@code TestExecutionListener} that provides support for executing tests
 * within <em>test-managed transactions</em> by honoring Spring's
 * {@link org.springframework.transaction.annotation.Transactional @Transactional}
 * annotation.
 *
 * <h3>Test-managed Transactions</h3>
 * <p><em>Test-managed transactions</em> are transactions that are managed
 * declaratively via this listener or programmatically via
 * {@link TestTransaction}. Such transactions should not be confused with
 * <em>Spring-managed transactions</em> (i.e., those managed directly
 * by Spring within the {@code ApplicationContext} loaded for tests) or
 * <em>application-managed transactions</em> (i.e., those managed
 * programmatically within application code that is invoked via tests).
 * Spring-managed and application-managed transactions will typically
 * participate in test-managed transactions; however, caution should be
 * taken if Spring-managed or application-managed transactions are
 * configured with any propagation type other than
 * {@link org.springframework.transaction.annotation.Propagation#REQUIRED REQUIRED}
 * or {@link org.springframework.transaction.annotation.Propagation#SUPPORTS SUPPORTS}.
 *
 * <h3>Enabling and Disabling Transactions</h3>
 * <p>Annotating a test method with {@code @Transactional} causes the test
 * to be run within a transaction that will, by default, be automatically
 * <em>rolled back</em> after completion of the test. If a test class is
 * annotated with {@code @Transactional}, each test method within that class
 * hierarchy will be run within a transaction. Test methods that are
 * <em>not</em> annotated with {@code @Transactional} (at the class or method
 * level) will not be run within a transaction. Furthermore, tests that
 * <em>are</em> annotated with {@code @Transactional} but have the
 * {@link org.springframework.transaction.annotation.Transactional#propagation propagation}
 * type set to
 * {@link org.springframework.transaction.annotation.Propagation#NOT_SUPPORTED NOT_SUPPORTED}
 * will not be run within a transaction.
 *
 * <h3>Declarative Rollback and Commit Behavior</h3>
 * <p>By default, test transactions will be automatically <em>rolled back</em>
 * after completion of the test; however, transactional commit and rollback
 * behavior can be configured declaratively via the class-level
 * {@link TransactionConfiguration @TransactionConfiguration} and method-level
 * {@link Rollback @Rollback} annotations.
 *
 * <h3>Programmatic Transaction Management</h3>
 * <p>As of Spring Framework 4.1, it is possible to interact with test-managed
 * transactions programmatically via the static methods in {@link TestTransaction}.
 * {@code TestTransaction} may be used within <em>test</em> methods,
 * <em>before</em> methods, and <em>after</em> methods.
 *
 * <h3>Executing Code outside of a Transaction</h3>
 * <p>When executing transactional tests, it is sometimes useful to be able to
 * execute certain <em>set up</em> or <em>tear down</em> code outside of a
 * transaction. {@code TransactionalTestExecutionListener} provides such
 * support for methods annotated with
 * {@link BeforeTransaction @BeforeTransaction} or
 * {@link AfterTransaction @AfterTransaction}.
 *
 * <h3>Configuring a Transaction Manager</h3>
 * <p>{@code TransactionalTestExecutionListener} expects a
 * {@link PlatformTransactionManager} bean to be defined in the Spring
 * {@code ApplicationContext} for the test. In case there are multiple
 * instances of {@code PlatformTransactionManager} within the test's
 * {@code ApplicationContext}, {@code @TransactionConfiguration} supports
 * configuring the bean name of the {@code PlatformTransactionManager} that
 * should be used to drive transactions. Alternatively, a <em>qualifier</em>
 * may be declared via
 * {@link org.springframework.transaction.annotation.Transactional#value @Transactional("myQualifier")}, or
 * {@link org.springframework.transaction.annotation.TransactionManagementConfigurer TransactionManagementConfigurer}
 * can be implemented by an
 * {@link org.springframework.context.annotation.Configuration @Configuration}
 * class. See {@link TestContextTransactionUtils#retrieveTransactionManager}
 * for details on the algorithm used to look up a transaction manager in
 * the test's {@code ApplicationContext}.
 *
 * @author Sam Brannen
 * @author Juergen Hoeller
 * @since 2.5
 * @see TransactionConfiguration
 * @see org.springframework.transaction.annotation.TransactionManagementConfigurer
 * @see org.springframework.transaction.annotation.Transactional
 * @see org.springframework.test.annotation.Rollback
 * @see BeforeTransaction
 * @see AfterTransaction
 * @see TestTransaction
 */
public class TransactionalTestExecutionListener extends AbstractTestExecutionListener {

	private static final Log logger = LogFactory.getLog(TransactionalTestExecutionListener.class);

	private static final String DEFAULT_TRANSACTION_MANAGER_NAME = (String) getDefaultValue(
		TransactionConfiguration.class, "transactionManager");

	private static final Boolean DEFAULT_DEFAULT_ROLLBACK = (Boolean) getDefaultValue(TransactionConfiguration.class,
		"defaultRollback");

	protected final TransactionAttributeSource attributeSource = new AnnotationTransactionAttributeSource();

	private TransactionConfigurationAttributes configurationAttributes;


	/**
	 * Returns {@code 4000}.
	 */
	@Override
	public final int getOrder() {
		return 4000;
	}

	/**
	 * If the test method of the supplied {@linkplain TestContext test context}
	 * is configured to run within a transaction, this method will run
	 * {@link BeforeTransaction @BeforeTransaction} methods and start a new
	 * transaction.
	 * <p>Note that if a {@code @BeforeTransaction} method fails, any remaining
	 * {@code @BeforeTransaction} methods will not be invoked, and a transaction
	 * will not be started.
	 * @see org.springframework.transaction.annotation.Transactional
	 * @see #getTransactionManager(TestContext, String)
	 */
	@Override
	public void beforeTestMethod(final TestContext testContext) throws Exception {
		final Method testMethod = testContext.getTestMethod();
		final Class<?> testClass = testContext.getTestClass();
		Assert.notNull(testMethod, "The test method of the supplied TestContext must not be null");

		TransactionContext txContext = TransactionContextHolder.removeCurrentTransactionContext();
		if (txContext != null) {
			throw new IllegalStateException("Cannot start a new transaction without ending the existing transaction.");
		}

		PlatformTransactionManager tm = null;
		TransactionAttribute transactionAttribute = this.attributeSource.getTransactionAttribute(testMethod, testClass);

		if (transactionAttribute != null) {
			transactionAttribute = TestContextTransactionUtils.createDelegatingTransactionAttribute(testContext,
				transactionAttribute);

			if (logger.isDebugEnabled()) {
				logger.debug("Explicit transaction definition [" + transactionAttribute + "] found for test context "
						+ testContext);
			}

			if (transactionAttribute.getPropagationBehavior() == TransactionDefinition.PROPAGATION_NOT_SUPPORTED) {
				return;
			}

			tm = getTransactionManager(testContext, transactionAttribute.getQualifier());
		}

		if (tm != null) {
			txContext = new TransactionContext(testContext, tm, transactionAttribute, isRollback(testContext));
			runBeforeTransactionMethods(testContext);
			txContext.startTransaction();
			TransactionContextHolder.setCurrentTransactionContext(txContext);
		}
	}

	/**
	 * If a transaction is currently active for the supplied
	 * {@linkplain TestContext test context}, this method will end the transaction
	 * and run {@link AfterTransaction @AfterTransaction} methods.
	 * <p>{@code @AfterTransaction} methods are guaranteed to be invoked even if
	 * an error occurs while ending the transaction.
	 */
	@Override
	public void afterTestMethod(TestContext testContext) throws Exception {
		Method testMethod = testContext.getTestMethod();
		Assert.notNull(testMethod, "The test method of the supplied TestContext must not be null");

		TransactionContext txContext = TransactionContextHolder.removeCurrentTransactionContext();
		// If there was (or perhaps still is) a transaction...
		if (txContext != null) {
			TransactionStatus transactionStatus = txContext.getTransactionStatus();
			try {
				// If the transaction is still active...
				if ((transactionStatus != null) && !transactionStatus.isCompleted()) {
					txContext.endTransaction();
				}
			}
			finally {
				runAfterTransactionMethods(testContext);
			}
		}
	}

	/**
	 * Run all {@link BeforeTransaction @BeforeTransaction} methods for the
	 * specified {@link TestContext test context}. If one of the methods fails,
	 * however, the caught exception will be rethrown in a wrapped
	 * {@link RuntimeException}, and the remaining methods will <strong>not</strong>
	 * be given a chance to execute.
	 * @param testContext the current test context
	 */
	protected void runBeforeTransactionMethods(TestContext testContext) throws Exception {
		try {
			List<Method> methods = getAnnotatedMethods(testContext.getTestClass(), BeforeTransaction.class);
			Collections.reverse(methods);
			for (Method method : methods) {
				if (logger.isDebugEnabled()) {
					logger.debug("Executing @BeforeTransaction method [" + method + "] for test context " + testContext);
				}
				method.invoke(testContext.getTestInstance());
			}
		}
		catch (InvocationTargetException ex) {
			logger.error("Exception encountered while executing @BeforeTransaction methods for test context "
					+ testContext + ".", ex.getTargetException());
			ReflectionUtils.rethrowException(ex.getTargetException());
		}
	}

	/**
	 * Run all {@link AfterTransaction @AfterTransaction} methods for the
	 * specified {@link TestContext test context}. If one of the methods fails,
	 * the caught exception will be logged as an error, and the remaining
	 * methods will be given a chance to execute. After all methods have
	 * executed, the first caught exception, if any, will be rethrown.
	 * @param testContext the current test context
	 */
	protected void runAfterTransactionMethods(TestContext testContext) throws Exception {
		Throwable afterTransactionException = null;

		List<Method> methods = getAnnotatedMethods(testContext.getTestClass(), AfterTransaction.class);
		for (Method method : methods) {
			try {
				if (logger.isDebugEnabled()) {
					logger.debug("Executing @AfterTransaction method [" + method + "] for test context " + testContext);
				}
				method.invoke(testContext.getTestInstance());
			}
			catch (InvocationTargetException ex) {
				Throwable targetException = ex.getTargetException();
				if (afterTransactionException == null) {
					afterTransactionException = targetException;
				}
				logger.error("Exception encountered while executing @AfterTransaction method [" + method
						+ "] for test context " + testContext, targetException);
			}
			catch (Exception ex) {
				if (afterTransactionException == null) {
					afterTransactionException = ex;
				}
				logger.error("Exception encountered while executing @AfterTransaction method [" + method
						+ "] for test context " + testContext, ex);
			}
		}

		if (afterTransactionException != null) {
			ReflectionUtils.rethrowException(afterTransactionException);
		}
	}

	/**
	 * Get the {@link PlatformTransactionManager transaction manager} to use
	 * for the supplied {@linkplain TestContext test context} and {@code qualifier}.
	 * <p>Delegates to {@link #getTransactionManager(TestContext)} if the
	 * supplied {@code qualifier} is {@code null} or empty.
	 * @param testContext the test context for which the transaction manager
	 * should be retrieved
	 * @param qualifier the qualifier for selecting between multiple bean matches;
	 * may be {@code null} or empty
	 * @return the transaction manager to use, or {@code null} if not found
	 * @throws BeansException if an error occurs while retrieving the transaction manager
	 * @see #getTransactionManager(TestContext)
	 */
	protected PlatformTransactionManager getTransactionManager(TestContext testContext, String qualifier) {
		// look up by type and qualifier from @Transactional
		if (StringUtils.hasText(qualifier)) {
			try {
				// Use autowire-capable factory in order to support extended qualifier
				// matching (only exposed on the internal BeanFactory, not on the
				// ApplicationContext).
				BeanFactory bf = testContext.getApplicationContext().getAutowireCapableBeanFactory();

				return BeanFactoryAnnotationUtils.qualifiedBeanOfType(bf, PlatformTransactionManager.class, qualifier);
			}
			catch (RuntimeException ex) {
				if (logger.isWarnEnabled()) {
					logger.warn(
						String.format(
							"Caught exception while retrieving transaction manager with qualifier '%s' for test context %s",
							qualifier, testContext), ex);
				}
				throw ex;
			}
		}

		// else
		return getTransactionManager(testContext);
	}

	/**
	 * Get the {@link PlatformTransactionManager transaction manager} to use
	 * for the supplied {@link TestContext test context}.
	 * <p>The default implementation simply delegates to
	 * {@link TestContextTransactionUtils#retrieveTransactionManager}.
	 * @param testContext the test context for which the transaction manager
	 * should be retrieved
	 * @return the transaction manager to use, or {@code null} if not found
	 * @throws BeansException if an error occurs while retrieving an explicitly
	 * named transaction manager
	 * @see #getTransactionManager(TestContext, String)
	 */
	protected PlatformTransactionManager getTransactionManager(TestContext testContext) {
		String tmName = retrieveConfigurationAttributes(testContext).getTransactionManagerName();
		return TestContextTransactionUtils.retrieveTransactionManager(testContext, tmName);
	}

	/**
	 * Determine whether or not to rollback transactions by default for the
	 * supplied {@link TestContext test context}.
	 * @param testContext the test context for which the default rollback flag
	 * should be retrieved
	 * @return the <em>default rollback</em> flag for the supplied test context
	 * @throws Exception if an error occurs while determining the default rollback flag
	 */
	protected final boolean isDefaultRollback(TestContext testContext) throws Exception {
		return retrieveConfigurationAttributes(testContext).isDefaultRollback();
	}

	/**
	 * Determine whether or not to rollback transactions for the supplied
	 * {@link TestContext test context} by taking into consideration the
	 * {@link #isDefaultRollback(TestContext) default rollback} flag and a
	 * possible method-level override via the {@link Rollback} annotation.
	 * @param testContext the test context for which the rollback flag
	 * should be retrieved
	 * @return the <em>rollback</em> flag for the supplied test context
	 * @throws Exception if an error occurs while determining the rollback flag
	 */
	protected final boolean isRollback(TestContext testContext) throws Exception {
		boolean rollback = isDefaultRollback(testContext);
		Rollback rollbackAnnotation = findAnnotation(testContext.getTestMethod(), Rollback.class);
		if (rollbackAnnotation != null) {
			boolean rollbackOverride = rollbackAnnotation.value();
			if (logger.isDebugEnabled()) {
				logger.debug(String.format(
					"Method-level @Rollback(%s) overrides default rollback [%s] for test context %s.",
					rollbackOverride, rollback, testContext));
			}
			rollback = rollbackOverride;
		}
		else {
			if (logger.isDebugEnabled()) {
				logger.debug(String.format(
					"No method-level @Rollback override: using default rollback [%s] for test context %s.", rollback,
					testContext));
			}
		}
		return rollback;
	}

	/**
	 * Gets all superclasses of the supplied {@link Class class}, including the
	 * class itself. The ordering of the returned list will begin with the
	 * supplied class and continue up the class hierarchy, excluding {@link Object}.
	 * <p>Note: This code has been borrowed from
	 * {@link org.junit.internal.runners.TestClass#getSuperClasses(Class)} and
	 * adapted.
	 * @param clazz the class for which to retrieve the superclasses
	 * @return all superclasses of the supplied class, excluding {@code Object}
	 */
	private List<Class<?>> getSuperClasses(Class<?> clazz) {
		List<Class<?>> results = new ArrayList<Class<?>>();
		Class<?> current = clazz;
		while (current != null && Object.class != current) {
			results.add(current);
			current = current.getSuperclass();
		}
		return results;
	}

	/**
	 * Gets all methods in the supplied {@link Class class} and its superclasses
	 * which are annotated with the supplied {@code annotationType} but
	 * which are not <em>shadowed</em> by methods overridden in subclasses.
	 * <p>Note: This code has been borrowed from
	 * {@link org.junit.internal.runners.TestClass#getAnnotatedMethods(Class)}
	 * and adapted.
	 * @param clazz the class for which to retrieve the annotated methods
	 * @param annotationType the annotation type for which to search
	 * @return all annotated methods in the supplied class and its superclasses
	 */
	private List<Method> getAnnotatedMethods(Class<?> clazz, Class<? extends Annotation> annotationType) {
		List<Method> results = new ArrayList<Method>();
		for (Class<?> current : getSuperClasses(clazz)) {
			for (Method method : current.getDeclaredMethods()) {
				Annotation annotation = getAnnotation(method, annotationType);
				if (annotation != null && !isShadowed(method, results)) {
					results.add(method);
				}
			}
		}
		return results;
	}

	/**
	 * Determine if the supplied {@link Method method} is <em>shadowed</em> by
	 * a method in the supplied {@link List list} of previous methods.
	 * <p>Note: This code has been borrowed from
	 * {@link org.junit.internal.runners.TestClass#isShadowed(Method, List)}.
	 * @param method the method to check for shadowing
	 * @param previousMethods the list of methods which have previously been processed
	 * @return {@code true} if the supplied method is shadowed by a
	 * method in the {@code previousMethods} list
	 */
	private boolean isShadowed(Method method, List<Method> previousMethods) {
		for (Method each : previousMethods) {
			if (isShadowed(method, each)) {
				return true;
			}
		}
		return false;
	}

	/**
	 * Determine if the supplied {@link Method current method} is <em>shadowed</em>
	 * by a {@link Method previous method}.
	 * <p>Note: This code has been borrowed from
	 * {@link org.junit.internal.runners.TestClass#isShadowed(Method, Method)}.
	 * @param current the current method
	 * @param previous the previous method
	 * @return {@code true} if the previous method shadows the current one
	 */
	private boolean isShadowed(Method current, Method previous) {
		if (!previous.getName().equals(current.getName())) {
			return false;
		}
		if (previous.getParameterTypes().length != current.getParameterTypes().length) {
			return false;
		}
		for (int i = 0; i < previous.getParameterTypes().length; i++) {
			if (!previous.getParameterTypes()[i].equals(current.getParameterTypes()[i])) {
				return false;
			}
		}
		return true;
	}

	/**
	 * Retrieves the {@link TransactionConfigurationAttributes} for the
	 * specified {@link Class class} which may optionally declare or inherit
	 * {@link TransactionConfiguration @TransactionConfiguration}. If
	 * {@code @TransactionConfiguration} is not present for the supplied
	 * class, the <em>default values</em> for attributes defined in
	 * {@code @TransactionConfiguration} will be used instead.
	 * @param testContext the test context for which the configuration
	 * attributes should be retrieved
	 * @return the TransactionConfigurationAttributes instance for this listener,
	 * potentially cached
	 */
	TransactionConfigurationAttributes retrieveConfigurationAttributes(TestContext testContext) {
		if (this.configurationAttributes == null) {
			Class<?> clazz = testContext.getTestClass();

			TransactionConfiguration txConfig = AnnotatedElementUtils.findMergedAnnotation(clazz,
				TransactionConfiguration.class);
			if (logger.isDebugEnabled()) {
				logger.debug(String.format("Retrieved @TransactionConfiguration [%s] for test class [%s].",
					txConfig, clazz));
			}

			String transactionManagerName;
			boolean defaultRollback;
			if (txConfig != null) {
				transactionManagerName = txConfig.transactionManager();
				defaultRollback = txConfig.defaultRollback();
			}
			else {
				transactionManagerName = DEFAULT_TRANSACTION_MANAGER_NAME;
				defaultRollback = DEFAULT_DEFAULT_ROLLBACK;
			}

			TransactionConfigurationAttributes configAttributes = new TransactionConfigurationAttributes(
				transactionManagerName, defaultRollback);
			if (logger.isDebugEnabled()) {
				logger.debug(String.format("Retrieved TransactionConfigurationAttributes %s for class [%s].",
					configAttributes, clazz));
			}
			this.configurationAttributes = configAttributes;
		}
		return this.configurationAttributes;
	}

}
