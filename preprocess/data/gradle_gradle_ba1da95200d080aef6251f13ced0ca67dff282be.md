Refactoring Types: ['Rename Package']
in/java/org/gradle/tooling/TestLauncher.java
/*
 * Copyright 2015 the original author or authors.
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

package org.gradle.tooling;

import org.gradle.tooling.events.test.TestOperationDescriptor;
import org.gradle.tooling.tests.TestExecutionException;

/**
 *
 * A {@code TestLauncher} allows you to configure and execute a tests in a Gradle build.
 *
 * @since 2.5
 *
 * */
public interface TestLauncher extends ConfigurableLauncher<TestLauncher> {
    TestLauncher withTests(TestOperationDescriptor... testDescriptors);

    void run() throws TestExecutionException; // Run synchronously
    void run(ResultHandler<? super Void> handler); // Start asynchronously
}


File: subprojects/tooling-api/src/main/java/org/gradle/tooling/internal/consumer/ResultHandlerAdapter.java
/*
 * Copyright 2011 the original author or authors.
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
package org.gradle.tooling.internal.consumer;

import org.gradle.internal.event.ListenerNotificationException;
import org.gradle.tooling.*;
import org.gradle.tooling.exceptions.UnsupportedBuildArgumentException;
import org.gradle.tooling.exceptions.UnsupportedOperationConfigurationException;
import org.gradle.tooling.internal.protocol.BuildExceptionVersion1;
import org.gradle.tooling.internal.protocol.InternalBuildCancelledException;
import org.gradle.tooling.internal.protocol.ResultHandlerVersion1;
import org.gradle.tooling.internal.protocol.exceptions.InternalUnsupportedBuildArgumentException;
import org.gradle.tooling.internal.protocol.test.InternalTestExecutionException;
import org.gradle.tooling.tests.TestExecutionException;

/**
 * Adapts a {@link ResultHandler} to a {@link ResultHandlerVersion1}.
 *
 * @param <T> The result type.
 */
abstract class ResultHandlerAdapter<T> implements ResultHandlerVersion1<T> {
    private final ResultHandler<? super T> handler;

    ResultHandlerAdapter(ResultHandler<? super T> handler) {
        this.handler = handler;
    }

    public void onComplete(T result) {
        handler.onComplete(result);
    }

    public void onFailure(Throwable failure) {
        if (failure instanceof InternalUnsupportedBuildArgumentException) {
            handler.onFailure(new UnsupportedBuildArgumentException(connectionFailureMessage(failure)
                    + "\n" + failure.getMessage(), failure));
        } else if (failure instanceof UnsupportedOperationConfigurationException) {
            handler.onFailure(new UnsupportedOperationConfigurationException(connectionFailureMessage(failure)
                    + "\n" + failure.getMessage(), failure.getCause()));
        } else if (failure instanceof GradleConnectionException) {
            handler.onFailure((GradleConnectionException) failure);
        } else if (failure instanceof InternalBuildCancelledException) {
            handler.onFailure(new BuildCancelledException(connectionFailureMessage(failure), failure.getCause()));
        } else if (failure instanceof InternalTestExecutionException) {
            handler.onFailure(new TestExecutionException(connectionFailureMessage(failure), failure.getCause()));
        } else if (failure instanceof BuildExceptionVersion1) {
            handler.onFailure(new BuildException(connectionFailureMessage(failure), failure.getCause()));
        } else if (failure instanceof ListenerNotificationException) {
            handler.onFailure(new ListenerFailedException(connectionFailureMessage(failure), ((ListenerNotificationException) failure).getCauses()));
        } else {
            handler.onFailure(new GradleConnectionException(connectionFailureMessage(failure), failure));
        }
    }

    protected abstract String connectionFailureMessage(Throwable failure);
}


File: subprojects/tooling-api/src/main/java/org/gradle/tooling/internal/consumer/connection/TestExecutionConsumerConnection.java
/*
 * Copyright 2015 the original author or authors.
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

package org.gradle.tooling.internal.consumer.connection;

import com.google.common.base.Function;
import com.google.common.collect.Collections2;
import com.google.common.collect.Lists;
import org.gradle.api.Action;
import org.gradle.tooling.tests.TestExecutionException;
import org.gradle.tooling.events.OperationDescriptor;
import org.gradle.tooling.events.task.TaskOperationDescriptor;
import org.gradle.tooling.events.test.JvmTestOperationDescriptor;
import org.gradle.tooling.events.test.TestOperationDescriptor;
import org.gradle.tooling.internal.adapter.ProtocolToModelAdapter;
import org.gradle.tooling.internal.adapter.SourceObjectMapping;
import org.gradle.tooling.internal.consumer.DefaultInternalJvmTestExecutionDescriptor;
import org.gradle.tooling.internal.consumer.DefaultInternalTestExecutionRequest;
import org.gradle.tooling.internal.consumer.converters.TaskPropertyHandlerFactory;
import org.gradle.tooling.internal.consumer.parameters.BuildCancellationTokenAdapter;
import org.gradle.tooling.internal.consumer.parameters.ConsumerOperationParameters;
import org.gradle.tooling.internal.consumer.versioning.ModelMapping;
import org.gradle.tooling.internal.protocol.BuildResult;
import org.gradle.tooling.internal.protocol.ConnectionVersion4;
import org.gradle.tooling.internal.protocol.test.InternalJvmTestExecutionDescriptor;
import org.gradle.tooling.internal.protocol.test.InternalTestExecutionConnection;
import org.gradle.tooling.internal.protocol.test.InternalTestExecutionRequest;
import org.gradle.tooling.internal.provider.TestExecutionRequest;

import java.util.Collection;
import java.util.List;

/*
 * <p>Used for providers >= 2.5.</p>
 */
public class TestExecutionConsumerConnection extends ShutdownAwareConsumerConnection {
    private final ProtocolToModelAdapter adapter;

    public TestExecutionConsumerConnection(ConnectionVersion4 delegate, ModelMapping modelMapping, ProtocolToModelAdapter adapter) {
        super(delegate, modelMapping, adapter);
        this.adapter = adapter;
    }

    public Void runTests(final TestExecutionRequest testExecutionRequest, ConsumerOperationParameters operationParameters) {
        final BuildCancellationTokenAdapter cancellationTokenAdapter = new BuildCancellationTokenAdapter(operationParameters.getCancellationToken());
        final BuildResult<Object> result = ((InternalTestExecutionConnection) getDelegate()).runTests(toInternalTestExecutionRequest(testExecutionRequest), cancellationTokenAdapter, operationParameters);
        Action<SourceObjectMapping> mapper = new TaskPropertyHandlerFactory().forVersion(getVersionDetails());
        return adapter.adapt(Void.class, result.getModel(), mapper);
    }

    InternalTestExecutionRequest toInternalTestExecutionRequest(TestExecutionRequest testExecutionRequest) {
        final Collection<TestOperationDescriptor> testOperationDescriptors = testExecutionRequest.getTestOperationDescriptors();
        final Collection<JvmTestOperationDescriptor> jvmTestOperationDescriptors = toJvmTestOperatorDescriptor(testOperationDescriptors);
        final List<InternalJvmTestExecutionDescriptor> internalJvmTestDescriptors = Lists.newArrayList();
        for (final JvmTestOperationDescriptor descriptor : jvmTestOperationDescriptors) {
            internalJvmTestDescriptors.add(new DefaultInternalJvmTestExecutionDescriptor(descriptor.getClassName(), descriptor.getMethodName(), findTaskPath(descriptor)));
        }
        InternalTestExecutionRequest internalTestExecutionRequest = new DefaultInternalTestExecutionRequest(internalJvmTestDescriptors);
        return internalTestExecutionRequest;
    }

    private Collection<JvmTestOperationDescriptor> toJvmTestOperatorDescriptor(Collection<TestOperationDescriptor> testOperationDescriptors) {
        assertOnlyJvmTestOperatorDescriptors(testOperationDescriptors);

        return Collections2.transform(testOperationDescriptors, new Function<TestOperationDescriptor, JvmTestOperationDescriptor>() {
            @Override
            public JvmTestOperationDescriptor apply(TestOperationDescriptor input) {
                return (JvmTestOperationDescriptor) input;
            }
        });
    }

    private void assertOnlyJvmTestOperatorDescriptors(Collection<TestOperationDescriptor> testOperationDescriptors) {
        for (TestOperationDescriptor testOperationDescriptor : testOperationDescriptors) {
            if (!(testOperationDescriptor instanceof JvmTestOperationDescriptor)) {
                throw new TestExecutionException("Invalid TestOperationDescriptor implementation. Only JvmTestOperationDescriptor supported.");
            }
        }
    }

    private String findTaskPath(JvmTestOperationDescriptor descriptor) {
        OperationDescriptor parent = descriptor.getParent();
        while (parent != null && parent.getParent() != null) {
            parent = parent.getParent();
        }
        if (parent instanceof TaskOperationDescriptor) {
            return ((TaskOperationDescriptor) parent).getTaskPath();
        } else {
            return null;
        }
    }
}
