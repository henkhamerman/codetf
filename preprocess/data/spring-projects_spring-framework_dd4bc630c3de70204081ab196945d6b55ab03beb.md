Refactoring Types: ['Pull Up Attribute', 'Move Class']
p/interceptor/AsyncExecutionAspectSupport.java
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

package org.springframework.aop.interceptor;

import java.lang.reflect.Method;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;
import java.util.concurrent.Future;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.springframework.beans.factory.BeanFactory;
import org.springframework.beans.factory.BeanFactoryAware;
import org.springframework.beans.factory.annotation.BeanFactoryAnnotationUtils;
import org.springframework.core.task.AsyncListenableTaskExecutor;
import org.springframework.core.task.AsyncTaskExecutor;
import org.springframework.core.task.support.TaskExecutorAdapter;
import org.springframework.util.Assert;
import org.springframework.util.ReflectionUtils;
import org.springframework.util.StringUtils;

/**
 * Base class for asynchronous method execution aspects, such as
 * {@code org.springframework.scheduling.annotation.AnnotationAsyncExecutionInterceptor}
 * or {@code org.springframework.scheduling.aspectj.AnnotationAsyncExecutionAspect}.
 *
 * <p>Provides support for <i>executor qualification</i> on a method-by-method basis.
 * {@code AsyncExecutionAspectSupport} objects must be constructed with a default {@code
 * Executor}, but each individual method may further qualify a specific {@code Executor}
 * bean to be used when executing it, e.g. through an annotation attribute.
 *
 * @author Chris Beams
 * @author Juergen Hoeller
 * @author Stephane Nicoll
 * @since 3.1.2
 */
public abstract class AsyncExecutionAspectSupport implements BeanFactoryAware {

	protected final Log logger = LogFactory.getLog(getClass());

	private final Map<Method, AsyncTaskExecutor> executors = new ConcurrentHashMap<Method, AsyncTaskExecutor>(16);

	private Executor defaultExecutor;

	private AsyncUncaughtExceptionHandler exceptionHandler;

	private BeanFactory beanFactory;


	/**
	 * Create a new {@link AsyncExecutionAspectSupport}, using the provided default
	 * executor unless individual async methods indicate via qualifier that a more
	 * specific executor should be used.
	 * @param defaultExecutor the executor to use when executing asynchronous methods
	 * @param exceptionHandler the {@link AsyncUncaughtExceptionHandler} to use
	 */
	public AsyncExecutionAspectSupport(Executor defaultExecutor, AsyncUncaughtExceptionHandler exceptionHandler) {
		this.defaultExecutor = defaultExecutor;
		this.exceptionHandler = exceptionHandler;
	}

	/**
	 * Create a new instance with a default {@link AsyncUncaughtExceptionHandler}.
	 */
	public AsyncExecutionAspectSupport(Executor defaultExecutor) {
		this(defaultExecutor, new SimpleAsyncUncaughtExceptionHandler());
	}


	/**
	 * Supply the executor to be used when executing async methods.
	 * @param defaultExecutor the {@code Executor} (typically a Spring {@code
	 * AsyncTaskExecutor} or {@link java.util.concurrent.ExecutorService}) to delegate to
	 * unless a more specific executor has been requested via a qualifier on the async
	 * method, in which case the executor will be looked up at invocation time against the
	 * enclosing bean factory.
	 * @see #getExecutorQualifier
	 * @see #setBeanFactory(BeanFactory)
	 */
	public void setExecutor(Executor defaultExecutor) {
		this.defaultExecutor = defaultExecutor;
	}

	/**
	 * Supply the {@link AsyncUncaughtExceptionHandler} to use to handle exceptions
	 * thrown by invoking asynchronous methods with a {@code void} return type.
	 */
	public void setExceptionHandler(AsyncUncaughtExceptionHandler exceptionHandler) {
		this.exceptionHandler = exceptionHandler;
	}

	/**
	 * Set the {@link BeanFactory} to be used when looking up executors by qualifier.
	 */
	@Override
	public void setBeanFactory(BeanFactory beanFactory) {
		this.beanFactory = beanFactory;
	}


	/**
	 * Determine the specific executor to use when executing the given method.
	 * Should preferably return an {@link AsyncListenableTaskExecutor} implementation.
	 * @return the executor to use (or {@code null}, but just if no default executor has been set)
	 */
	protected AsyncTaskExecutor determineAsyncExecutor(Method method) {
		AsyncTaskExecutor executor = this.executors.get(method);
		if (executor == null) {
			Executor executorToUse = this.defaultExecutor;
			String qualifier = getExecutorQualifier(method);
			if (StringUtils.hasLength(qualifier)) {
				Assert.notNull(this.beanFactory, "BeanFactory must be set on " + getClass().getSimpleName() +
						" to access qualified executor '" + qualifier + "'");
				executorToUse = BeanFactoryAnnotationUtils.qualifiedBeanOfType(
						this.beanFactory, Executor.class, qualifier);
			}
			else if (executorToUse == null) {
				return null;
			}
			executor = (executorToUse instanceof AsyncListenableTaskExecutor ?
					(AsyncListenableTaskExecutor) executorToUse : new TaskExecutorAdapter(executorToUse));
			this.executors.put(method, executor);
		}
		return executor;
	}

	/**
	 * Return the qualifier or bean name of the executor to be used when executing the
	 * given async method, typically specified in the form of an annotation attribute.
	 * Returning an empty string or {@code null} indicates that no specific executor has
	 * been specified and that the {@linkplain #setExecutor(Executor) default executor}
	 * should be used.
	 * @param method the method to inspect for executor qualifier metadata
	 * @return the qualifier if specified, otherwise empty string or {@code null}
	 * @see #determineAsyncExecutor(Method)
	 */
	protected abstract String getExecutorQualifier(Method method);

	/**
	 * Handles a fatal error thrown while asynchronously invoking the specified
	 * {@link Method}.
	 * <p>If the return type of the method is a {@link Future} object, the original
	 * exception can be propagated by just throwing it at the higher level. However,
	 * for all other cases, the exception will not be transmitted back to the client.
	 * In that later case, the current {@link AsyncUncaughtExceptionHandler} will be
	 * used to manage such exception.
	 * @param ex the exception to handle
	 * @param method the method that was invoked
	 * @param params the parameters used to invoke the method
	 */
	protected void handleError(Throwable ex, Method method, Object... params) throws Exception {
		if (Future.class.isAssignableFrom(method.getReturnType())) {
			ReflectionUtils.rethrowException(ex);
		}
		else {
			// Could not transmit the exception to the caller with default executor
			try {
				this.exceptionHandler.handleUncaughtException(ex, method, params);
			}
			catch (Throwable ex2) {
				logger.error("Exception handler for async method '" + method.toGenericString() +
						"' threw unexpected exception itself", ex2);
			}
		}
	}

}


File: spring-aop/src/main/java/org/springframework/aop/interceptor/AsyncExecutionInterceptor.java
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

package org.springframework.aop.interceptor;

import java.lang.reflect.Method;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executor;
import java.util.concurrent.Future;
import java.util.function.Supplier;

import org.aopalliance.intercept.MethodInterceptor;
import org.aopalliance.intercept.MethodInvocation;

import org.springframework.aop.support.AopUtils;
import org.springframework.core.BridgeMethodResolver;
import org.springframework.core.Ordered;
import org.springframework.core.task.AsyncListenableTaskExecutor;
import org.springframework.core.task.AsyncTaskExecutor;
import org.springframework.lang.UsesJava8;
import org.springframework.util.ClassUtils;
import org.springframework.util.concurrent.ListenableFuture;

/**
 * AOP Alliance {@code MethodInterceptor} that processes method invocations
 * asynchronously, using a given {@link org.springframework.core.task.AsyncTaskExecutor}.
 * Typically used with the {@link org.springframework.scheduling.annotation.Async} annotation.
 *
 * <p>In terms of target method signatures, any parameter types are supported.
 * However, the return type is constrained to either {@code void} or
 * {@code java.util.concurrent.Future}. In the latter case, the Future handle
 * returned from the proxy will be an actual asynchronous Future that can be used
 * to track the result of the asynchronous method execution. However, since the
 * target method needs to implement the same signature, it will have to return
 * a temporary Future handle that just passes the return value through
 * (like Spring's {@link org.springframework.scheduling.annotation.AsyncResult}
 * or EJB 3.1's {@code javax.ejb.AsyncResult}).
 *
 * <p>When the return type is {@code java.util.concurrent.Future}, any exception thrown
 * during the execution can be accessed and managed by the caller. With {@code void}
 * return type however, such exceptions cannot be transmitted back. In that case an
 * {@link AsyncUncaughtExceptionHandler} can be registered to process such exceptions.
 *
 * <p>As of Spring 3.1.2 the {@code AnnotationAsyncExecutionInterceptor} subclass is
 * preferred for use due to its support for executor qualification in conjunction with
 * Spring's {@code @Async} annotation.
 *
 * @author Juergen Hoeller
 * @author Chris Beams
 * @author Stephane Nicoll
 * @since 3.0
 * @see org.springframework.scheduling.annotation.Async
 * @see org.springframework.scheduling.annotation.AsyncAnnotationAdvisor
 * @see org.springframework.scheduling.annotation.AnnotationAsyncExecutionInterceptor
 */
public class AsyncExecutionInterceptor extends AsyncExecutionAspectSupport
		implements MethodInterceptor, Ordered {

	// Java 8's CompletableFuture type present?
	private static final boolean completableFuturePresent = ClassUtils.isPresent(
			"java.util.concurrent.CompletableFuture", AsyncExecutionInterceptor.class.getClassLoader());


	/**
	 * Create a new {@code AsyncExecutionInterceptor}.
	 * @param defaultExecutor the {@link Executor} (typically a Spring {@link AsyncTaskExecutor}
	 * or {@link java.util.concurrent.ExecutorService}) to delegate to
	 * @param exceptionHandler the {@link AsyncUncaughtExceptionHandler} to use
	 */
	public AsyncExecutionInterceptor(Executor defaultExecutor, AsyncUncaughtExceptionHandler exceptionHandler) {
		super(defaultExecutor, exceptionHandler);
	}

	/**
	 * Create a new instance with a default {@link AsyncUncaughtExceptionHandler}.
	 */
	public AsyncExecutionInterceptor(Executor defaultExecutor) {
		super(defaultExecutor);
	}

	/**
	 * Intercept the given method invocation, submit the actual calling of the method to
	 * the correct task executor and return immediately to the caller.
	 * @param invocation the method to intercept and make asynchronous
	 * @return {@link Future} if the original method returns {@code Future}; {@code null}
	 * otherwise.
	 */
	@Override
	public Object invoke(final MethodInvocation invocation) throws Throwable {
		Class<?> targetClass = (invocation.getThis() != null ? AopUtils.getTargetClass(invocation.getThis()) : null);
		Method specificMethod = ClassUtils.getMostSpecificMethod(invocation.getMethod(), targetClass);
		final Method userDeclaredMethod = BridgeMethodResolver.findBridgedMethod(specificMethod);

		AsyncTaskExecutor executor = determineAsyncExecutor(userDeclaredMethod);
		if (executor == null) {
			throw new IllegalStateException(
					"No executor specified and no default executor set on AsyncExecutionInterceptor either");
		}

		Callable<Object> task = new Callable<Object>() {
			@Override
			public Object call() throws Exception {
				try {
					Object result = invocation.proceed();
					if (result instanceof Future) {
						return ((Future<?>) result).get();
					}
				}
				catch (ExecutionException ex) {
					handleError(ex.getCause(), userDeclaredMethod, invocation.getArguments());
				}
				catch (Throwable ex) {
					handleError(ex, userDeclaredMethod, invocation.getArguments());
				}
				return null;
			}
		};

		Class<?> returnType = invocation.getMethod().getReturnType();
		if (completableFuturePresent) {
			Future<Object> result = CompletableFutureDelegate.processCompletableFuture(returnType, task, executor);
			if (result != null) {
				return result;
			}
		}
		if (ListenableFuture.class.isAssignableFrom(returnType)) {
			return ((AsyncListenableTaskExecutor) executor).submitListenable(task);
		}
		else if (Future.class.isAssignableFrom(returnType)) {
			return executor.submit(task);
		}
		else {
			executor.submit(task);
			return null;
		}
	}

	/**
	 * This implementation is a no-op for compatibility in Spring 3.1.2.
	 * Subclasses may override to provide support for extracting qualifier information,
	 * e.g. via an annotation on the given method.
	 * @return always {@code null}
	 * @since 3.1.2
	 * @see #determineAsyncExecutor(Method)
	 */
	@Override
	protected String getExecutorQualifier(Method method) {
		return null;
	}

	@Override
	public int getOrder() {
		return Ordered.HIGHEST_PRECEDENCE;
	}


	/**
	 * Inner class to avoid a hard dependency on Java 8.
	 */
	@UsesJava8
	private static class CompletableFutureDelegate {

		public static <T> Future<T> processCompletableFuture(Class<?> returnType, final Callable<T> task, Executor executor) {
			if (!CompletableFuture.class.isAssignableFrom(returnType)) {
				return null;
			}
			return CompletableFuture.supplyAsync(new Supplier<T>() {
				@Override
				public T get() {
					try {
						return task.call();
					}
					catch (Throwable ex) {
						throw new CompletionException(ex);
					}
				}
			}, executor);
		}
	}

}
