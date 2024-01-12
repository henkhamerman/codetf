Refactoring Types: ['Extract Method']
main/java/org/gradle/language/base/plugins/ComponentModelBasePlugin.java
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
package org.gradle.language.base.plugins;

import org.gradle.api.*;
import org.gradle.api.internal.project.ProjectInternal;
import org.gradle.api.internal.rules.ModelMapCreators;
import org.gradle.api.internal.rules.NamedDomainObjectFactoryRegistry;
import org.gradle.api.plugins.ExtensionContainer;
import org.gradle.api.tasks.TaskContainer;
import org.gradle.internal.reflect.Instantiator;
import org.gradle.internal.service.ServiceRegistry;
import org.gradle.internal.util.BiFunction;
import org.gradle.language.base.LanguageSourceSet;
import org.gradle.language.base.ProjectSourceSet;
import org.gradle.language.base.internal.LanguageSourceSetInternal;
import org.gradle.language.base.internal.SourceTransformTaskConfig;
import org.gradle.language.base.internal.model.BinarySpecFactoryRegistry;
import org.gradle.language.base.internal.model.ComponentRules;
import org.gradle.language.base.internal.registry.*;
import org.gradle.model.*;
import org.gradle.model.internal.core.ModelCreator;
import org.gradle.model.internal.core.ModelPath;
import org.gradle.model.internal.core.ModelReference;
import org.gradle.model.internal.core.MutableModelNode;
import org.gradle.model.internal.core.rule.describe.SimpleModelRuleDescriptor;
import org.gradle.model.internal.manage.schema.ModelMapSchema;
import org.gradle.model.internal.manage.schema.ModelSchemaStore;
import org.gradle.model.internal.registry.ModelRegistry;
import org.gradle.model.internal.type.ModelType;
import org.gradle.platform.base.*;
import org.gradle.platform.base.internal.*;

import javax.inject.Inject;

import static org.apache.commons.lang.StringUtils.capitalize;

/**
 * Base plugin for language support.
 *
 * Adds a {@link org.gradle.platform.base.ComponentSpecContainer} named {@code componentSpecs} to the project.
 *
 * For each binary instance added to the binaries container, registers a lifecycle task to create that binary.
 */
@Incubating
public class ComponentModelBasePlugin implements Plugin<ProjectInternal> {
    private final ModelRegistry modelRegistry;
    private final ModelSchemaStore schemaStore;

    @Inject
    public ComponentModelBasePlugin(ModelRegistry modelRegistry, ModelSchemaStore schemaStore) {
        this.modelRegistry = modelRegistry;
        this.schemaStore = schemaStore;
    }

    public void apply(final ProjectInternal project) {
        project.getPluginManager().apply(LanguageBasePlugin.class);

        SimpleModelRuleDescriptor descriptor = new SimpleModelRuleDescriptor(ComponentModelBasePlugin.class.getSimpleName() + ".apply()");

        ModelMapSchema<ComponentSpecContainer> schema = (ModelMapSchema<ComponentSpecContainer>) schemaStore.getSchema(ModelType.of(ComponentSpecContainer.class));
        ModelPath components = ModelPath.path("components");
        ModelCreator componentsCreator = ModelMapCreators.specialized(
            components,
            ComponentSpec.class,
            ComponentSpecContainer.class,
            schema.getManagedImpl().asSubclass(ComponentSpecContainer.class),
            ModelReference.of(ComponentSpecFactory.class),
            descriptor
        );
        modelRegistry.create(componentsCreator);
        modelRegistry.getRoot().applyToAllLinksTransitive(ModelType.of(ComponentSpec.class), ComponentRules.class);
    }

    @SuppressWarnings("UnusedDeclaration")
    static class Rules extends RuleSource {
        @Model
        ComponentSpecFactory componentSpecFactory() {
            return new ComponentSpecFactory("this collection");
        }

        @Model
        LanguageRegistry languages(ServiceRegistry serviceRegistry) {
            return serviceRegistry.get(Instantiator.class).newInstance(DefaultLanguageRegistry.class);
        }

        @Model
        LanguageTransformContainer languageTransforms(ServiceRegistry serviceRegistry) {
            return serviceRegistry.get(Instantiator.class).newInstance(DefaultLanguageTransformContainer.class);
        }

        // Required because creation of Binaries from Components is not yet wired into the infrastructure
        @Mutate
        void closeComponentsForBinaries(ModelMap<Task> tasks, ComponentSpecContainer components) {
        }

        // Finalizing here, as we need this to run after any 'assembling' task (jar, link, etc) is created.
        @Finalize
        void createSourceTransformTasks(final TaskContainer tasks, final BinaryContainer binaries, LanguageTransformContainer languageTransforms) {
            for (LanguageTransform<?, ?> language : languageTransforms) {
                for (final BinarySpecInternal binary : binaries.withType(BinarySpecInternal.class)) {
                    if (binary.isLegacyBinary() || !language.applyToBinary(binary)) {
                        continue;
                    }

                    final SourceTransformTaskConfig taskConfig = language.getTransformTask();
                    for (LanguageSourceSet languageSourceSet : binary.getAllSources()) {
                        LanguageSourceSetInternal sourceSet = (LanguageSourceSetInternal) languageSourceSet;
                        if (language.getSourceSetType().isInstance(sourceSet) && sourceSet.getMayHaveSources()) {
                            String taskName = taskConfig.getTaskPrefix() + capitalize(binary.getName()) + capitalize(sourceSet.getFullName());
                            Task task = tasks.create(taskName, taskConfig.getTaskType());

                            taskConfig.configureTask(task, binary, sourceSet);

                            task.dependsOn(sourceSet);
                            binary.getTasks().add(task);
                        }
                    }
                }
            }
        }

        // TODO:DAZ Work out why this is required
        @Mutate
        void closeSourcesForBinaries(BinaryContainer binaries, ProjectSourceSet sources) {
            // Only required because sources aren't fully integrated into model
        }

        @Model
        PlatformContainer platforms(ServiceRegistry serviceRegistry) {
            Instantiator instantiator = serviceRegistry.get(Instantiator.class);
            return instantiator.newInstance(DefaultPlatformContainer.class, instantiator);
        }

        @Model
        PlatformResolvers platformResolver(PlatformContainer platforms, ServiceRegistry serviceRegistry) {
            Instantiator instantiator = serviceRegistry.get(Instantiator.class);
            return instantiator.newInstance(DefaultPlatformResolvers.class, platforms);
        }

        @Mutate
        void registerPlatformExtension(ExtensionContainer extensions, PlatformContainer platforms) {
            extensions.add("platforms", platforms);
        }

        @Model
        BinarySpecFactory binarySpecFactory(final BinarySpecFactoryRegistry binaryFactoryRegistry) {
            // BinarySpecFactoryRegistry is used by the BinaryContainer API, which we still need for the time being.
            // We are adapting it to BinarySpecFactory here so it can be used by component.binaries model maps

            final BinarySpecFactory binarySpecFactory = new BinarySpecFactory("this collection");
            binaryFactoryRegistry.copyInto(new NamedDomainObjectFactoryRegistry<BinarySpec>() {
                @Override
                public <U extends BinarySpec> void registerFactory(Class<U> type, final NamedDomainObjectFactory<? extends U> factory) {
                    binarySpecFactory.register(type, null, new BiFunction<U, String, MutableModelNode>() {
                        @Override
                        public U apply(String s, MutableModelNode modelNode) {
                            final U binarySpec = factory.create(s);
                            final Object parentObject = modelNode.getParent().getParent().getPrivateData();
                            if (parentObject instanceof ComponentSpec && binarySpec instanceof ComponentSpecAware) {
                                ((ComponentSpecAware) binarySpec).setComponent((ComponentSpec) parentObject);
                            }

                            return binarySpec;
                        }
                    });
                }
            });
            return binarySpecFactory;
        }

        @Defaults
        void collectBinaries(BinaryContainer binaries, ComponentSpecContainer componentSpecs) {
            for (ComponentSpec componentSpec : componentSpecs.values()) {
                for (BinarySpec binary : componentSpec.getBinaries().values()) {
                    binaries.add(binary);
                }
            }
        }
    }
}


File: subprojects/platform-base/src/main/java/org/gradle/platform/base/BinarySpec.java
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

package org.gradle.platform.base;

import org.gradle.api.*;
import org.gradle.internal.HasInternalProtocol;
import org.gradle.language.base.LanguageSourceSet;
import org.gradle.model.ModelMap;

/**
 * Represents a binary artifact that is the result of building a project component.
 */
@Incubating @HasInternalProtocol
public interface BinarySpec extends BuildableModelElement, Named {
    /**
     * Returns a human-consumable display name for this binary.
     */
    String getDisplayName();

    /**
     * Can this binary be built in the current environment?
     */
    boolean isBuildable();

    /**
     * The source sets used to compile this binary.
     */
    DomainObjectSet<LanguageSourceSet> getSource();

    ModelMap<LanguageSourceSet> getSources();

    /**
     * Configures the source sets used to build this binary.
     */
    void sources(Action<? super PolymorphicDomainObjectContainer<LanguageSourceSet>> action);

    /**
     * The set of tasks associated with this binary.
     */
    BinaryTasksCollection getTasks();

    /**
     * Configures the tasks that build this binary.
     */
    void tasks(Action<? super BinaryTasksCollection> action);
}


File: subprojects/platform-base/src/main/java/org/gradle/platform/base/binary/BaseBinarySpec.java
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

package org.gradle.platform.base.binary;

import com.google.common.collect.Sets;
import org.gradle.api.Action;
import org.gradle.api.DomainObjectSet;
import org.gradle.api.Incubating;
import org.gradle.api.PolymorphicDomainObjectContainer;
import org.gradle.api.internal.AbstractBuildableModelElement;
import org.gradle.api.internal.DefaultDomainObjectSet;
import org.gradle.api.internal.project.taskfactory.ITaskFactory;
import org.gradle.internal.Actions;
import org.gradle.internal.reflect.Instantiator;
import org.gradle.internal.reflect.ObjectInstantiationException;
import org.gradle.language.base.FunctionalSourceSet;
import org.gradle.language.base.LanguageSourceSet;
import org.gradle.model.ModelMap;
import org.gradle.model.internal.core.DomainObjectCollectionBackedModelMap;
import org.gradle.platform.base.BinaryTasksCollection;
import org.gradle.platform.base.ModelInstantiationException;
import org.gradle.platform.base.internal.BinaryBuildAbility;
import org.gradle.platform.base.internal.BinarySpecInternal;
import org.gradle.platform.base.internal.DefaultBinaryTasksCollection;
import org.gradle.platform.base.internal.FixedBuildAbility;

import java.util.Set;

/**
 * Base class for custom binary implementations.
 * A custom implementation of {@link org.gradle.platform.base.BinarySpec} must extend this type.
 *
 * TODO at the moment leaking BinarySpecInternal here to generate lifecycleTask in
 * LanguageBasePlugin$createLifecycleTaskForBinary#createLifecycleTaskForBinary rule
 *
 */
@Incubating
public abstract class BaseBinarySpec extends AbstractBuildableModelElement implements BinarySpecInternal {
    private FunctionalSourceSet mainSources;
    private ModelMap<LanguageSourceSet> ownedSources;

    private static ThreadLocal<BinaryInfo> nextBinaryInfo = new ThreadLocal<BinaryInfo>();
    private final BinaryTasksCollection tasks;

    private final String name;
    private final String typeName;

    private boolean disabled;

    public static <T extends BaseBinarySpec> T create(Class<T> type, String name, Instantiator instantiator, ITaskFactory taskFactory) {
        if (type.equals(BaseBinarySpec.class)) {
            throw new ModelInstantiationException("Cannot create instance of abstract class BaseBinarySpec.");
        }
        nextBinaryInfo.set(new BinaryInfo(name, type.getSimpleName(), taskFactory, instantiator));
        try {
            try {
                return instantiator.newInstance(type);
            } catch (ObjectInstantiationException e) {
                throw new ModelInstantiationException(String.format("Could not create binary of type %s", type.getSimpleName()), e.getCause());
            }
        } finally {
            nextBinaryInfo.set(null);
        }
    }

    protected BaseBinarySpec() {
        this(nextBinaryInfo.get());
    }

    private BaseBinarySpec(BinaryInfo info) {
        if (info == null) {
            throw new ModelInstantiationException("Direct instantiation of a BaseBinarySpec is not permitted. Use a BinaryTypeBuilder instead.");
        }
        this.name = info.name;
        this.typeName = info.typeName;
        this.tasks = info.instantiator.newInstance(DefaultBinaryTasksCollection.class, this, info.taskFactory);
    }

    protected String getTypeName() {
        return typeName;
    }

    public String getDisplayName() {
        return String.format("%s '%s'", getTypeName(), getName());
    }

    public String getName() {
        return name;
    }

    @Override
    public void setBuildable(boolean buildable) {
        this.disabled = !buildable;
    }

    public final boolean isBuildable() {
        return getBuildAbility().isBuildable();
    }

    public void setBinarySources(FunctionalSourceSet sources) {
        mainSources = sources;
        ownedSources = DomainObjectCollectionBackedModelMap.wrap(LanguageSourceSet.class, sources, sources.getEntityInstantiator(), sources.getNamer(), Actions.doNothing());
    }

    @Override
    public DomainObjectSet<LanguageSourceSet> getSource() {
        return new DefaultDomainObjectSet<LanguageSourceSet>(LanguageSourceSet.class, mainSources);
    }

    public void sources(Action<? super PolymorphicDomainObjectContainer<LanguageSourceSet>> action) {
        action.execute(mainSources);
    }

    @Override
    public Set<LanguageSourceSet> getAllSources() {
        return Sets.newLinkedHashSet(mainSources);
    }

    @Override
    public ModelMap<LanguageSourceSet> getSources() {
        return ownedSources;
    }

    @Override
    public void addSourceSet(LanguageSourceSet sourceSet) {
        mainSources.add(sourceSet);
    }

    public BinaryTasksCollection getTasks() {
        return tasks;
    }

    @Override
    public void tasks(Action<? super BinaryTasksCollection> action) {
        action.execute(tasks);
    }

    public boolean isLegacyBinary() {
        return false;
    }

    private static class BinaryInfo {
        private final String name;
        private final String typeName;
        private final ITaskFactory taskFactory;
        private final Instantiator instantiator;

        private BinaryInfo(String name, String typeName, ITaskFactory taskFactory, Instantiator instantiator) {
            this.name = name;
            this.typeName = typeName;
            this.taskFactory = taskFactory;
            this.instantiator = instantiator;
        }
    }

    @Override
    public String toString() {
        return getDisplayName();
    }

    @Override
    public final BinaryBuildAbility getBuildAbility() {
        if (disabled) {
            return new FixedBuildAbility(false);
        }
        return getBinaryBuildAbility();
    }

    protected BinaryBuildAbility getBinaryBuildAbility() {
        // Default behavior is to always be buildable.  Binary implementations should define what
        // criteria make them buildable or not.
        return new FixedBuildAbility(true);
    }
}


File: subprojects/platform-base/src/main/java/org/gradle/platform/base/internal/BinarySpecInternal.java
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

package org.gradle.platform.base.internal;

import org.gradle.language.base.FunctionalSourceSet;
import org.gradle.language.base.LanguageSourceSet;
import org.gradle.model.internal.type.ModelType;
import org.gradle.platform.base.BinarySpec;

import java.util.Set;

public interface BinarySpecInternal extends BinarySpec {
    ModelType<BinarySpec> PUBLIC_MODEL_TYPE = ModelType.of(BinarySpec.class);

    /**
     * Return all language source sets.
     * This method is overridden by NativeTestSuiteBinarySpec to include the source sets from the tested binary.
     */
    Set<LanguageSourceSet> getAllSources();

    void addSourceSet(LanguageSourceSet sourceSet);

    void setBinarySources(FunctionalSourceSet sources);

    void setBuildable(boolean buildable);

    BinaryBuildAbility getBuildAbility();

    boolean isLegacyBinary();
}


File: subprojects/platform-native/src/main/groovy/org/gradle/nativeplatform/test/internal/DefaultNativeTestSuiteBinarySpec.java
/*
 * Copyright 2013 the original author or authors.
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
package org.gradle.nativeplatform.test.internal;

import com.google.common.collect.Sets;
import org.gradle.language.base.LanguageSourceSet;
import org.gradle.nativeplatform.NativeBinarySpec;
import org.gradle.nativeplatform.internal.AbstractNativeBinarySpec;
import org.gradle.nativeplatform.internal.NativeBinarySpecInternal;
import org.gradle.nativeplatform.tasks.InstallExecutable;
import org.gradle.nativeplatform.tasks.LinkExecutable;
import org.gradle.nativeplatform.tasks.ObjectFilesToBinary;
import org.gradle.nativeplatform.test.NativeTestSuiteBinarySpec;
import org.gradle.nativeplatform.test.NativeTestSuiteSpec;
import org.gradle.nativeplatform.test.tasks.RunTestExecutable;
import org.gradle.platform.base.BinaryTasksCollection;
import org.gradle.platform.base.internal.BinaryTasksCollectionWrapper;

import java.io.File;
import java.util.Set;

public abstract class DefaultNativeTestSuiteBinarySpec extends AbstractNativeBinarySpec implements NativeTestSuiteBinarySpecInternal {
    private final DefaultTasksCollection tasks = new DefaultTasksCollection(super.getTasks());
    private NativeBinarySpecInternal testedBinary;
    private File executableFile;

    @Override
    public NativeTestSuiteSpec getComponent() {
        return (NativeTestSuiteSpec) super.getComponent();
    }

    public NativeBinarySpec getTestedBinary() {
        return testedBinary;
    }

    public void setTestedBinary(NativeBinarySpecInternal testedBinary) {
        this.testedBinary = testedBinary;
        setTargetPlatform(testedBinary.getTargetPlatform());
        setToolChain(testedBinary.getToolChain());
        setPlatformToolProvider(testedBinary.getPlatformToolProvider());
        setBuildType(testedBinary.getBuildType());
        setFlavor(testedBinary.getFlavor());
    }

    @Override
    public Set<LanguageSourceSet> getAllSources() {
        Set<LanguageSourceSet> sources = Sets.newLinkedHashSet(super.getAllSources());
        sources.addAll(testedBinary.getAllSources());
        return sources;
    }

    public File getExecutableFile() {
        return executableFile;
    }

    public void setExecutableFile(File executableFile) {
        this.executableFile = executableFile;
    }

    public File getPrimaryOutput() {
        return getExecutableFile();
    }

    @Override
    protected ObjectFilesToBinary getCreateOrLink() {
        return tasks.getLink();
    }

    public NativeTestSuiteBinarySpec.TasksCollection getTasks() {
        return tasks;
    }

    private static class DefaultTasksCollection extends BinaryTasksCollectionWrapper implements NativeTestSuiteBinarySpec.TasksCollection {
        public DefaultTasksCollection(BinaryTasksCollection delegate) {
            super(delegate);
        }

        public LinkExecutable getLink() {
            return findSingleTaskWithType(LinkExecutable.class);
        }

        public InstallExecutable getInstall() {
            return findSingleTaskWithType(InstallExecutable.class);
        }

        public RunTestExecutable getRun() {
            return findSingleTaskWithType(RunTestExecutable.class);
        }
    }
}


File: subprojects/platform-native/src/main/groovy/org/gradle/nativeplatform/test/plugins/NativeBinariesTestPlugin.java
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

package org.gradle.nativeplatform.test.plugins;

import org.gradle.api.*;
import org.gradle.api.internal.rules.ModelMapCreators;
import org.gradle.api.tasks.TaskContainer;
import org.gradle.language.base.plugins.LifecycleBasePlugin;
import org.gradle.language.nativeplatform.DependentSourceSet;
import org.gradle.model.Finalize;
import org.gradle.model.ModelMap;
import org.gradle.model.Mutate;
import org.gradle.model.RuleSource;
import org.gradle.model.internal.core.ModelCreator;
import org.gradle.model.internal.core.ModelPath;
import org.gradle.model.internal.core.ModelReference;
import org.gradle.model.internal.core.rule.describe.ModelRuleDescriptor;
import org.gradle.model.internal.core.rule.describe.SimpleModelRuleDescriptor;
import org.gradle.model.internal.manage.schema.ModelMapSchema;
import org.gradle.model.internal.manage.schema.ModelSchemaStore;
import org.gradle.model.internal.registry.ModelRegistry;
import org.gradle.model.internal.type.ModelType;
import org.gradle.nativeplatform.internal.NativeBinarySpecInternal;
import org.gradle.nativeplatform.plugins.NativeComponentPlugin;
import org.gradle.nativeplatform.tasks.InstallExecutable;
import org.gradle.nativeplatform.test.NativeTestSuiteBinarySpec;
import org.gradle.nativeplatform.test.internal.NativeTestSuiteBinarySpecInternal;
import org.gradle.nativeplatform.test.tasks.RunTestExecutable;
import org.gradle.platform.base.BinaryContainer;
import org.gradle.platform.base.internal.BinaryNamingScheme;
import org.gradle.platform.base.internal.ComponentSpecFactory;
import org.gradle.platform.base.test.TestSuiteContainer;
import org.gradle.platform.base.test.TestSuiteSpec;

import javax.inject.Inject;
import java.io.File;

/**
 * A plugin that sets up the infrastructure for testing native binaries.
 */
@Incubating
public class NativeBinariesTestPlugin implements Plugin<Project> {
    private final ModelRegistry modelRegistry;
    private final ModelSchemaStore schemaStore;

    @Inject
    public NativeBinariesTestPlugin(ModelRegistry modelRegistry, ModelSchemaStore schemaStore) {
        this.modelRegistry = modelRegistry;
        this.schemaStore = schemaStore;
    }

    public void apply(final Project project) {
        project.getPluginManager().apply(NativeComponentPlugin.class);

        ModelRuleDescriptor descriptor = new SimpleModelRuleDescriptor(NativeBinariesTestPlugin.class.getName() + ".apply()");
        ModelMapSchema<TestSuiteContainer> schema = (ModelMapSchema<TestSuiteContainer>) schemaStore.getSchema(ModelType.of(TestSuiteContainer.class));
        ModelCreator testSuitesCreator = ModelMapCreators.specialized(ModelPath.path("testSuites"), TestSuiteSpec.class, TestSuiteContainer.class, schema.getManagedImpl().asSubclass(TestSuiteContainer.class), ModelReference.of(ComponentSpecFactory.class), descriptor);

        modelRegistry.create(testSuitesCreator);
    }

    @SuppressWarnings("UnusedDeclaration")
    static class Rules extends RuleSource {
        @Finalize
            // Must run after test binaries have been created (currently in CUnit plugin)
        void attachTestedBinarySourcesToTestBinaries(BinaryContainer binaries) {
            for (NativeTestSuiteBinarySpecInternal testSuiteBinary : binaries.withType(NativeTestSuiteBinarySpecInternal.class)) {
                NativeBinarySpecInternal testedBinary = (NativeBinarySpecInternal) testSuiteBinary.getTestedBinary();
                for (DependentSourceSet testSource : testSuiteBinary.getSource().withType(DependentSourceSet.class)) {
                    testSource.lib(testedBinary.getAllSources());
                }
            }
        }

        @Finalize
        public void createTestTasks(final TaskContainer tasks, BinaryContainer binaries) {
            for (NativeTestSuiteBinarySpec testBinary : binaries.withType(NativeTestSuiteBinarySpec.class)) {
                NativeBinarySpecInternal binary = (NativeBinarySpecInternal) testBinary;
                final BinaryNamingScheme namingScheme = binary.getNamingScheme();

                RunTestExecutable runTask = tasks.create(namingScheme.getTaskName("run"), RunTestExecutable.class);
                final Project project = runTask.getProject();
                runTask.setDescription(String.format("Runs the %s", binary));

                final InstallExecutable installTask = binary.getTasks().withType(InstallExecutable.class).iterator().next();
                runTask.getInputs().files(installTask.getOutputs().getFiles());
                runTask.setExecutable(installTask.getRunScript().getPath());
                runTask.setOutputDir(new File(project.getBuildDir(), "/test-results/" + namingScheme.getOutputDirectoryBase()));

                testBinary.getTasks().add(runTask);
            }
        }

        @Mutate
        public void copyTestBinariesToGlobalContainer(BinaryContainer binaries, TestSuiteContainer testSuites) {
            for (final TestSuiteSpec testSuite : testSuites.withType(TestSuiteSpec.class).values()) {
                binaries.addAll(testSuite.getBinaries().values());
            }
        }

        @Mutate
        void attachBinariesToCheckLifecycle(ModelMap<Task> tasks, final BinaryContainer binaries) {
            // TODO - binaries aren't an input to this rule, they're an input to the action
            tasks.named(LifecycleBasePlugin.CHECK_TASK_NAME, new Action<Task>() {
                @Override
                public void execute(Task checkTask) {
                    for (NativeTestSuiteBinarySpec testBinary : binaries.withType(NativeTestSuiteBinarySpec.class)) {
                        checkTask.dependsOn(testBinary.getTasks().getRun());
                    }
                }
            });
        }
    }

}


File: subprojects/plugins/src/main/groovy/org/gradle/api/internal/jvm/DefaultClassDirectoryBinarySpec.java
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
package org.gradle.api.internal.jvm;

import org.gradle.api.Action;
import org.gradle.api.DomainObjectSet;
import org.gradle.api.PolymorphicDomainObjectContainer;
import org.gradle.api.internal.AbstractBuildableModelElement;
import org.gradle.api.internal.DefaultDomainObjectSet;
import org.gradle.api.internal.project.taskfactory.ITaskFactory;
import org.gradle.internal.reflect.Instantiator;
import org.gradle.jvm.JvmBinaryTasks;
import org.gradle.jvm.internal.DefaultJvmBinaryTasks;
import org.gradle.jvm.internal.toolchain.JavaToolChainInternal;
import org.gradle.jvm.platform.JavaPlatform;
import org.gradle.jvm.toolchain.JavaToolChain;
import org.gradle.language.base.FunctionalSourceSet;
import org.gradle.language.base.LanguageSourceSet;
import org.gradle.model.ModelMap;
import org.gradle.platform.base.BinaryTasksCollection;
import org.gradle.platform.base.internal.*;

import java.io.File;
import java.util.Set;

public class DefaultClassDirectoryBinarySpec extends AbstractBuildableModelElement implements ClassDirectoryBinarySpecInternal {
    private final DefaultDomainObjectSet<LanguageSourceSet> sourceSets = new DefaultDomainObjectSet<LanguageSourceSet>(LanguageSourceSet.class);
    private final BinaryNamingScheme namingScheme;
    private final String name;
    private final JavaToolChain toolChain;
    private final JavaPlatform platform;
    private final DefaultJvmBinaryTasks tasks;
    private File classesDir;
    private File resourcesDir;
    private boolean buildable = true;

    public DefaultClassDirectoryBinarySpec(String name, JavaToolChain toolChain, JavaPlatform platform, Instantiator instantiator, ITaskFactory taskFactory) {
        this.name = name;
        this.toolChain = toolChain;
        this.platform = platform;
        this.namingScheme = new ClassDirectoryBinaryNamingScheme(removeClassesSuffix(name));
        this.tasks = instantiator.newInstance(DefaultJvmBinaryTasks.class, new DefaultBinaryTasksCollection(this, taskFactory));
    }

    private String removeClassesSuffix(String name) {
        if (name.endsWith("Classes")) {
            return name.substring(0, name.length() - 7);
        }
        return name;
    }

    public JvmBinaryTasks getTasks() {
        return tasks;
    }

    @Override
    public void tasks(Action<? super BinaryTasksCollection> action) {
        action.execute(tasks);
    }

    public JavaToolChain getToolChain() {
        return toolChain;
    }

    public JavaPlatform getTargetPlatform() {
        return platform;
    }

    public void setTargetPlatform(JavaPlatform platform) {
        throw new UnsupportedOperationException();
    }

    public void setToolChain(JavaToolChain toolChain) {
        throw new UnsupportedOperationException();
    }

    public boolean isBuildable() {
        return getBuildAbility().isBuildable();
    }

    public void setBuildable(boolean buildable) {
        this.buildable = buildable;
    }

    public boolean isLegacyBinary() {
        return true;
    }

    public BinaryNamingScheme getNamingScheme() {
        return namingScheme;
    }

    public String getName() {
        return name;
    }

    public File getClassesDir() {
        return classesDir;
    }

    public void setClassesDir(File classesDir) {
        this.classesDir = classesDir;
    }

    public File getResourcesDir() {
        return resourcesDir;
    }

    public void setResourcesDir(File resourcesDir) {
        this.resourcesDir = resourcesDir;
    }

    public void setBinarySources(FunctionalSourceSet sources) {
        throw new UnsupportedOperationException();
    }

    @Override
    public void sources(Action<? super PolymorphicDomainObjectContainer<LanguageSourceSet>> action) {
        throw new UnsupportedOperationException();
    }

    @Override
    public DomainObjectSet<LanguageSourceSet> getSource() {
        return sourceSets;
    }

    @Override
    public ModelMap<LanguageSourceSet> getSources() {
        // TODO:LPTR This should return something usable
        throw new UnsupportedOperationException();
    }

    @Override
    public Set<LanguageSourceSet> getAllSources() {
        throw new UnsupportedOperationException();
    }

    @Override
    public void addSourceSet(LanguageSourceSet sourceSet) {
        sourceSets.add(sourceSet);
    }

    public String getDisplayName() {
        return namingScheme.getDescription();
    }

    public String toString() {
        return getDisplayName();
    }

    @Override
    public BinaryBuildAbility getBuildAbility() {
        if (!buildable) {
            return new FixedBuildAbility(false);
        }
        return new ToolSearchBuildAbility(((JavaToolChainInternal) getToolChain()).select(getTargetPlatform()));
    }
}
