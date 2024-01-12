Refactoring Types: ['Extract Method']
vy/org/gradle/api/internal/file/collections/ListBackedFileSet.java
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
package org.gradle.api.internal.file.collections;

import org.gradle.util.GUtil;

import java.io.File;
import java.io.Serializable;
import java.util.*;

/**
 * Adapts a java util collection into a file set.
 */
public class ListBackedFileSet implements MinimalFileSet, Serializable {
    private final Set<File> files;

    public ListBackedFileSet(File... files) {
        this(Arrays.asList(files));
    }

    public ListBackedFileSet(Collection<File> files) {
        this.files = new LinkedHashSet<File>(files);
    }

    public String getDisplayName() {
        switch (files.size()) {
            case 0:
                return "empty file collection";
            case 1:
                return String.format("file '%s'", files.iterator().next());
            default:
                return String.format("files %s", GUtil.toString(files));
        }
    }

    public Set<File> getFiles() {
        return files;
    }
}


File: subprojects/core/src/main/groovy/org/gradle/api/internal/file/collections/SimpleFileCollection.java
/*
 * Copyright 2010 the original author or authors.
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
package org.gradle.api.internal.file.collections;

import java.io.File;
import java.io.Serializable;
import java.util.Collection;

public class SimpleFileCollection extends FileCollectionAdapter implements Serializable {
    public SimpleFileCollection(File... files) {
        super(new ListBackedFileSet(files));
    }

    public SimpleFileCollection(Collection<File> files) {
        super(new ListBackedFileSet(files));
    }
}


File: subprojects/platform-play/src/main/java/org/gradle/play/internal/DefaultPlayApplicationBinarySpec.java
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

package org.gradle.play.internal;

import com.google.common.collect.Maps;
import com.google.common.collect.Sets;
import org.gradle.api.file.FileCollection;
import org.gradle.api.internal.AbstractBuildableModelElement;
import org.gradle.language.base.LanguageSourceSet;
import org.gradle.language.javascript.JavaScriptSourceSet;
import org.gradle.language.scala.ScalaLanguageSourceSet;
import org.gradle.platform.base.binary.BaseBinarySpec;
import org.gradle.platform.base.internal.BinaryBuildAbility;
import org.gradle.platform.base.internal.ToolSearchBuildAbility;
import org.gradle.platform.base.internal.toolchain.ToolResolver;
import org.gradle.play.JvmClasses;
import org.gradle.play.PlayApplicationSpec;
import org.gradle.play.PublicAssets;
import org.gradle.play.platform.PlayPlatform;

import java.io.File;
import java.util.Map;
import java.util.Set;

public class DefaultPlayApplicationBinarySpec extends BaseBinarySpec implements PlayApplicationBinarySpecInternal {
    private final JvmClasses classesDir = new DefaultJvmClasses();
    private final PublicAssets assets = new DefaultPublicAssets();
    private Map<LanguageSourceSet, ScalaLanguageSourceSet> generatedScala = Maps.newHashMap();
    private Map<LanguageSourceSet, JavaScriptSourceSet> generatedJavaScript = Maps.newHashMap();
    private PlayPlatform platform;
    private File jarFile;
    private File assetsJarFile;
    private FileCollection classpath;
    private ToolResolver toolResolver;
    private PlayApplicationSpec application;

    @Override
    protected String getTypeName() {
        return "Play Application Jar";
    }

    @Override
    public PlayApplicationSpec getApplication() {
        return application;
    }

    @Override
    public void setApplication(PlayApplicationSpec application) {
        this.application = application;
    }

    public PlayPlatform getTargetPlatform() {
        return platform;
    }

    public File getJarFile() {
        return jarFile;
    }

    public void setTargetPlatform(PlayPlatform platform) {
        this.platform = platform;
    }

    public void setJarFile(File file) {
        this.jarFile = file;
    }

    public File getAssetsJarFile() {
        return assetsJarFile;
    }

    public void setAssetsJarFile(File assetsJarFile) {
        this.assetsJarFile = assetsJarFile;
    }

    public JvmClasses getClasses() {
        return classesDir;
    }

    public PublicAssets getAssets() {
        return assets;
    }

    @Override
    public Map<LanguageSourceSet, ScalaLanguageSourceSet> getGeneratedScala() {
        return generatedScala;
    }

    @Override
    public Map<LanguageSourceSet, JavaScriptSourceSet> getGeneratedJavaScript() {
        return generatedJavaScript;
    }

    @Override
    public FileCollection getClasspath() {
        return classpath;
    }

    @Override
    public void setClasspath(FileCollection classpath) {
        this.classpath = classpath;
    }

    @Override
    public BinaryBuildAbility getBinaryBuildAbility() {
        return new ToolSearchBuildAbility(toolResolver.checkToolAvailability(getTargetPlatform()));
    }

    @Override
    public void setToolResolver(ToolResolver toolResolver) {
        this.toolResolver = toolResolver;
    }

    @Override
    public ToolResolver getToolResolver() {
        return toolResolver;
    }

    private static class DefaultJvmClasses extends AbstractBuildableModelElement implements JvmClasses {
        private Set<File> resourceDirs = Sets.newLinkedHashSet();
        private File classesDir;

        public File getClassesDir() {
            return classesDir;
        }

        public void setClassesDir(File classesDir) {
            this.classesDir = classesDir;
        }

        public Set<File> getResourceDirs() {
            return resourceDirs;
        }

        public void addResourceDir(File resourceDir) {
            resourceDirs.add(resourceDir);
        }
    }

    private static class DefaultPublicAssets extends AbstractBuildableModelElement implements PublicAssets {
        private Set<File> resourceDirs = Sets.newLinkedHashSet();

        public Set<File> getAssetDirs() {
            return resourceDirs;
        }

        public void addAssetDir(File assetDir) {
            resourceDirs.add(assetDir);
        }
    }
}


File: subprojects/platform-play/src/main/java/org/gradle/play/internal/PlayApplicationBinarySpecInternal.java
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

package org.gradle.play.internal;

import org.gradle.api.file.FileCollection;
import org.gradle.platform.base.internal.BinarySpecInternal;
import org.gradle.platform.base.internal.toolchain.ToolResolver;
import org.gradle.play.PlayApplicationBinarySpec;
import org.gradle.play.PlayApplicationSpec;
import org.gradle.play.platform.PlayPlatform;

import java.io.File;

public interface PlayApplicationBinarySpecInternal extends PlayApplicationBinarySpec, BinarySpecInternal {
    void setApplication(PlayApplicationSpec application);

    void setTargetPlatform(PlayPlatform platform);

    void setToolResolver(ToolResolver toolResolver);

    ToolResolver getToolResolver();

    void setJarFile(File file);

    void setAssetsJarFile(File file);

    // TODO:DAZ Should be taken from the LanguageSourceSet instances?
    // TODO:DAZ Should be a Classpath instance
    FileCollection getClasspath();

    void setClasspath(FileCollection applicationClasspath);
}


File: subprojects/platform-play/src/main/java/org/gradle/play/internal/run/DefaultPlayRunSpec.java
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

package org.gradle.play.internal.run;

import com.google.common.collect.Sets;
import org.gradle.api.file.FileCollection;
import org.gradle.api.tasks.compile.BaseForkOptions;

import java.io.File;
import java.io.Serializable;

public class DefaultPlayRunSpec implements PlayRunSpec, Serializable {
    private final Iterable<File> classpath;
    private final File applicationJar;
    private final File assetsJar;
    private final Iterable<File> assetsDirs;
    private final File projectPath;
    private BaseForkOptions forkOptions;
    private int httpPort;

    public DefaultPlayRunSpec(FileCollection classpath, File applicationJar, File assetsJar, Iterable<File> assetsDirs, File projectPath, BaseForkOptions forkOptions, int httpPort) {
        this.classpath = Sets.newHashSet(classpath);
        this.applicationJar = applicationJar;
        this.assetsJar = assetsJar;
        this.assetsDirs = assetsDirs;
        this.projectPath = projectPath;
        this.forkOptions = forkOptions;
        this.httpPort = httpPort;
    }

    public BaseForkOptions getForkOptions() {
        return forkOptions;
    }

    public Iterable<File> getClasspath() {
        return classpath;
    }

    public File getProjectPath() {
        return projectPath;
    }

    public int getHttpPort() {
        return httpPort;
    }

    public File getApplicationJar() {
        return applicationJar;
    }

    public File getAssetsJar() {
        return assetsJar;
    }

    public Iterable<File> getAssetsDirs() {
        return assetsDirs;
    }
}


File: subprojects/platform-play/src/main/java/org/gradle/play/internal/run/DefaultVersionedPlayRunAdapter.java
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

package org.gradle.play.internal.run;

import org.gradle.internal.UncheckedException;
import org.gradle.internal.classpath.DefaultClassPath;
import org.gradle.scala.internal.reflect.ScalaMethod;
import org.gradle.scala.internal.reflect.ScalaReflectionUtil;

import java.io.Closeable;
import java.io.File;
import java.io.IOException;
import java.io.Serializable;
import java.lang.ref.SoftReference;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.HashMap;
import java.util.concurrent.atomic.AtomicReference;
import java.util.jar.JarFile;

public abstract class DefaultVersionedPlayRunAdapter implements VersionedPlayRunAdapter, Serializable {
    private final AtomicReference<Object> reloadObject = new AtomicReference<Object>();
    private volatile SoftReference<URLClassLoader> previousClassLoaderReference;
    private volatile SoftReference<URLClassLoader> currentClassLoaderReference;

    protected abstract Class<?> getBuildLinkClass(ClassLoader classLoader) throws ClassNotFoundException;

    protected abstract Class<?> getDocHandlerFactoryClass(ClassLoader classLoader) throws ClassNotFoundException;

    protected abstract Class<?> getBuildDocHandlerClass(ClassLoader docsClassLoader) throws ClassNotFoundException;

    public Object getBuildLink(final ClassLoader classLoader, final File projectPath, final File applicationJar, final File assetsJar, final Iterable<File> assetsDirs) throws ClassNotFoundException {
        final ClassLoader assetsClassLoader = createAssetsClassLoader(assetsJar, assetsDirs, classLoader);
        forceReloadNextTime();
        return Proxy.newProxyInstance(classLoader, new Class<?>[]{getBuildLinkClass(classLoader)}, new InvocationHandler() {
            public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
                if (method.getName().equals("projectPath")) {
                    return projectPath;
                } else if (method.getName().equals("reload")) {
                    closePreviousClassLoader();
                    Object result = reloadObject.getAndSet(null);
                    if (result == null) {
                        return null;
                    } else if (result == Boolean.TRUE) {
                        URLClassLoader currentClassLoader = new URLClassLoader(new URL[]{applicationJar.toURI().toURL()}, assetsClassLoader);
                        storeClassLoader(currentClassLoader);
                        return currentClassLoader;
                    } else {
                        throw new IllegalStateException();
                    }
                } else if (method.getName().equals("settings")) {
                    return new HashMap<String, String>();
                }
                //TODO: all methods
                return null;
            }
        });
    }

    protected ClassLoader createAssetsClassLoader(File assetsJar, Iterable<File> assetsDirs, ClassLoader classLoader) {
        return new URLClassLoader(new DefaultClassPath(assetsJar).getAsURLArray(), classLoader);
    }

    private void storeClassLoader(URLClassLoader currentClassLoader) {
        URLClassLoader previousClassLoader = currentClassLoaderReference != null ? currentClassLoaderReference.get() : null;
        if (previousClassLoader != null) {
            previousClassLoaderReference = new SoftReference<URLClassLoader>(previousClassLoader);
        }
        currentClassLoaderReference = new SoftReference<URLClassLoader>(currentClassLoader);
    }

    private void closePreviousClassLoader() throws IOException {
        URLClassLoader previousClassLoader = previousClassLoaderReference != null ? previousClassLoaderReference.get() : null;
        if (previousClassLoader instanceof Closeable) {
            // use Closeable interface to find close method to prevent Java 1.7 specific method access
            ((Closeable) previousClassLoader).close();
        }
        previousClassLoaderReference = null;
    }

    @Override
    public void forceReloadNextTime() {
        reloadObject.set(Boolean.TRUE);
    }

    public Object getBuildDocHandler(ClassLoader docsClassLoader, Iterable<File> classpath) throws NoSuchMethodException, ClassNotFoundException, IOException, IllegalAccessException {
        Class<?> docHandlerFactoryClass = getDocHandlerFactoryClass(docsClassLoader);
        Method docHandlerFactoryMethod = docHandlerFactoryClass.getMethod("fromJar", JarFile.class, String.class);
        JarFile documentationJar = findDocumentationJar(classpath);
        try {
            return docHandlerFactoryMethod.invoke(null, documentationJar, "play/docs/content");
        } catch (InvocationTargetException e) {
            throw UncheckedException.unwrapAndRethrow(e);
        }
    }

    private JarFile findDocumentationJar(Iterable<File> classpath) throws IOException {
        // TODO:DAZ Use the location of the DocHandlerFactoryClass instead.
        File docJarFile = null;
        for (File file : classpath) {
            if (file.getName().startsWith("play-docs")) {
                docJarFile = file;
                break;
            }
        }
        return new JarFile(docJarFile);
    }

    public void runDevHttpServer(ClassLoader classLoader, ClassLoader docsClassLoader, Object buildLink, Object buildDocHandler, int httpPort) throws ClassNotFoundException {
        ScalaMethod runMethod = ScalaReflectionUtil.scalaMethod(classLoader, "play.core.server.NettyServer", "mainDevHttpMode", getBuildLinkClass(classLoader), getBuildDocHandlerClass(docsClassLoader), int.class);
        runMethod.invoke(buildLink, buildDocHandler, httpPort);
    }

}


File: subprojects/platform-play/src/main/java/org/gradle/play/internal/run/PlayRunSpec.java
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

package org.gradle.play.internal.run;

import org.gradle.api.tasks.compile.BaseForkOptions;

import java.io.File;

public interface PlayRunSpec {

    BaseForkOptions getForkOptions();

    Iterable<File> getClasspath();

    File getApplicationJar();

    File getAssetsJar();

    Iterable<File> getAssetsDirs();

    File getProjectPath();

    int getHttpPort();

}


File: subprojects/platform-play/src/main/java/org/gradle/play/internal/run/PlayWorkerServer.java
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

package org.gradle.play.internal.run;

import org.gradle.api.Action;
import org.gradle.api.logging.Logging;
import org.gradle.internal.UncheckedException;
import org.gradle.internal.classpath.DefaultClassPath;
import org.gradle.process.internal.WorkerProcessContext;

import java.io.IOException;
import java.io.Serializable;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLClassLoader;
import java.net.URLConnection;
import java.util.concurrent.CountDownLatch;

public class PlayWorkerServer implements Action<WorkerProcessContext>, PlayRunWorkerServerProtocol, Serializable {

    private PlayRunSpec runSpec;
    private VersionedPlayRunAdapter spec;

    private volatile CountDownLatch stop;

    public PlayWorkerServer(PlayRunSpec runSpec, VersionedPlayRunAdapter spec) {
        this.runSpec = runSpec;
        this.spec = spec;
    }

    public void execute(WorkerProcessContext context) {
        stop = new CountDownLatch(1);
        final PlayRunWorkerClientProtocol clientProtocol = context.getServerConnection().addOutgoing(PlayRunWorkerClientProtocol.class);
        context.getServerConnection().addIncoming(PlayRunWorkerServerProtocol.class, this);
        context.getServerConnection().connect();
        final PlayAppLifecycleUpdate result = startServer();
        try {
            clientProtocol.update(result);
            stop.await();
        } catch (InterruptedException e) {
            throw UncheckedException.throwAsUncheckedException(e);
        } finally {
            clientProtocol.update(PlayAppLifecycleUpdate.stopped());
        }
    }

    private PlayAppLifecycleUpdate startServer() {
        try {
            run();
            return PlayAppLifecycleUpdate.running();
        } catch (Exception e) {
            Logging.getLogger(this.getClass()).error("Failed to run Play", e);
            return PlayAppLifecycleUpdate.failed(e);
        }
    }

    private void run() {
        disableUrlConnectionCaching();
        final Thread thread = Thread.currentThread();
        final ClassLoader previousContextClassLoader = thread.getContextClassLoader();
        final ClassLoader classLoader = new URLClassLoader(new DefaultClassPath(runSpec.getClasspath()).getAsURLArray());
        thread.setContextClassLoader(classLoader);
        try {
            ClassLoader docsClassLoader = classLoader;

            Object buildDocHandler = spec.getBuildDocHandler(docsClassLoader, runSpec.getClasspath());

            Object buildLink = spec.getBuildLink(classLoader, runSpec.getProjectPath(), runSpec.getApplicationJar(), runSpec.getAssetsJar(), runSpec.getAssetsDirs());
            spec.runDevHttpServer(classLoader, docsClassLoader, buildLink, buildDocHandler, runSpec.getHttpPort());
        } catch (Exception e) {
            throw UncheckedException.throwAsUncheckedException(e);
        } finally {
            thread.setContextClassLoader(previousContextClassLoader);
        }
    }

    private void disableUrlConnectionCaching() {
        // fix problems in updating jar files by disabling default caching of URL connections.
        // URLConnection default caching should be disabled since it causes jar file locking issues and JVM crashes in updating jar files.
        // Changes to jar files won't be noticed in all cases when caching is enabled.
        // sun.net.www.protocol.jar.JarURLConnection leaves the JarFile instance open if URLConnection caching is enabled.
        try {
            URL url = new URL("jar:file://valid_jar_url_syntax.jar!/");
            URLConnection urlConnection = url.openConnection();
            urlConnection.setDefaultUseCaches(false);
        } catch (MalformedURLException e) {
            UncheckedException.throwAsUncheckedException(e);
        } catch (IOException e) {
            UncheckedException.throwAsUncheckedException(e);
        }
    }

    public void stop() {
        stop.countDown();
    }

    @Override
    public void rebuildSuccess() {
        spec.forceReloadNextTime();
    }
}


File: subprojects/platform-play/src/main/java/org/gradle/play/internal/run/VersionedPlayRunAdapter.java
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

package org.gradle.play.internal.run;

import java.io.File;
import java.io.IOException;

public interface VersionedPlayRunAdapter {
    void forceReloadNextTime();

    Object getBuildLink(ClassLoader classLoader, File projectPath, File applicationJar, File assetsJar, Iterable<File> assetsDirs) throws ClassNotFoundException;

    Object getBuildDocHandler(ClassLoader docsClassLoader, Iterable<File> classpath) throws NoSuchMethodException, ClassNotFoundException, IOException, IllegalAccessException;

    void runDevHttpServer(ClassLoader classLoader, ClassLoader docsClassLoader, Object buildLink, Object buildDocHandler, int httpPort) throws ClassNotFoundException;
}


File: subprojects/platform-play/src/main/java/org/gradle/play/plugins/PlayApplicationPlugin.java
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
package org.gradle.play.plugins;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import org.apache.commons.lang.StringUtils;
import org.gradle.api.*;
import org.gradle.api.internal.artifacts.dependencies.DefaultExternalModuleDependency;
import org.gradle.api.internal.artifacts.publish.DefaultPublishArtifact;
import org.gradle.api.internal.file.FileResolver;
import org.gradle.api.internal.file.copy.CopySpecInternal;
import org.gradle.api.internal.project.ProjectIdentifier;
import org.gradle.api.plugins.ExtensionContainer;
import org.gradle.api.tasks.scala.IncrementalCompileOptions;
import org.gradle.deployment.internal.DeploymentRegistry;
import org.gradle.internal.reflect.Instantiator;
import org.gradle.internal.service.ServiceRegistry;
import org.gradle.jvm.tasks.Jar;
import org.gradle.language.base.LanguageSourceSet;
import org.gradle.language.base.internal.compile.Compiler;
import org.gradle.language.base.sources.BaseLanguageSourceSet;
import org.gradle.language.java.JavaSourceSet;
import org.gradle.language.java.plugins.JavaLanguagePlugin;
import org.gradle.language.jvm.JvmResourceSet;
import org.gradle.language.routes.RoutesSourceSet;
import org.gradle.language.routes.internal.DefaultRoutesSourceSet;
import org.gradle.language.scala.ScalaLanguageSourceSet;
import org.gradle.language.scala.internal.DefaultScalaLanguageSourceSet;
import org.gradle.language.scala.plugins.ScalaLanguagePlugin;
import org.gradle.language.scala.tasks.PlatformScalaCompile;
import org.gradle.language.twirl.TwirlSourceSet;
import org.gradle.language.twirl.internal.DefaultTwirlSourceSet;
import org.gradle.model.*;
import org.gradle.platform.base.*;
import org.gradle.platform.base.internal.DefaultPlatformRequirement;
import org.gradle.platform.base.internal.PlatformRequirement;
import org.gradle.platform.base.internal.PlatformResolvers;
import org.gradle.platform.base.internal.toolchain.ResolvedTool;
import org.gradle.platform.base.internal.toolchain.ToolResolver;
import org.gradle.play.JvmClasses;
import org.gradle.play.PlayApplicationBinarySpec;
import org.gradle.play.PlayApplicationSpec;
import org.gradle.play.PublicAssets;
import org.gradle.play.internal.*;
import org.gradle.play.internal.platform.PlayMajorVersion;
import org.gradle.play.internal.platform.PlayPlatformInternal;
import org.gradle.play.internal.routes.RoutesCompileSpec;
import org.gradle.play.internal.run.PlayApplicationDeploymentHandle;
import org.gradle.play.internal.run.PlayApplicationRunner;
import org.gradle.play.internal.twirl.TwirlCompileSpec;
import org.gradle.play.internal.twirl.TwirlCompilerFactory;
import org.gradle.play.platform.PlayPlatform;
import org.gradle.play.tasks.PlayRun;
import org.gradle.play.tasks.RoutesCompile;
import org.gradle.play.tasks.TwirlCompile;
import org.gradle.util.VersionNumber;

import java.io.File;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;

/**
 * Plugin for Play Framework component support. Registers the {@link org.gradle.play.PlayApplicationSpec} component type for the components container.
 */

@Incubating
public class PlayApplicationPlugin implements Plugin<Project> {
    public static final int DEFAULT_HTTP_PORT = 9000;
    private static final VersionNumber MINIMUM_PLAY_VERSION_WITH_RUN_SUPPORT = VersionNumber.parse("2.3.7");
    public static final String RUN_SUPPORT_PLAY_MODULE = "run-support";

    private static final Map<PlayMajorVersion, String> PLAY_TO_SBT_IO_VERSION_MAPPING = ImmutableMap.<PlayMajorVersion, String>builder()
                                                                                                    .put(PlayMajorVersion.PLAY_2_3_X, "0.13.6")
                                                                                                    .put(PlayMajorVersion.PLAY_2_4_X, "0.13.8")
                                                                                                    .build();


    @Override
    public void apply(Project project) {
        project.getPluginManager().apply(JavaLanguagePlugin.class);
        project.getPluginManager().apply(ScalaLanguagePlugin.class);
        project.getExtensions().create("playConfigurations", PlayPluginConfigurations.class, project.getConfigurations(), project.getDependencies());
    }

    @SuppressWarnings("UnusedDeclaration")
    static class Rules extends RuleSource {
        @Model
        PlayPluginConfigurations configurations(ExtensionContainer extensions) {
            return extensions.getByType(PlayPluginConfigurations.class);
        }

        @Model
        FileResolver fileResolver(ServiceRegistry serviceRegistry) {
            return serviceRegistry.get(FileResolver.class);
        }

        @ComponentType
        void register(ComponentTypeBuilder<PlayApplicationSpec> builder) {
            builder.defaultImplementation(DefaultPlayApplicationSpec.class);
        }

        @Mutate
        public void registerPlatformResolver(PlatformResolvers platformResolvers) {
            platformResolvers.register(new PlayPlatformResolver());
        }

        @Mutate
        void createDefaultPlayApp(ModelMap<PlayApplicationSpec> builder) {
            builder.create("play");
        }

        @BinaryType
        void registerApplication(BinaryTypeBuilder<PlayApplicationBinarySpec> builder) {
            builder.defaultImplementation(DefaultPlayApplicationBinarySpec.class);
        }

        @LanguageType
        void registerTwirlLanguageType(LanguageTypeBuilder<TwirlSourceSet> builder) {
            builder.setLanguageName("twirl");
            builder.defaultImplementation(DefaultTwirlSourceSet.class);
        }

        @LanguageType
        void registerRoutesLanguageType(LanguageTypeBuilder<RoutesSourceSet> builder) {
            builder.setLanguageName("routes");
            builder.defaultImplementation(DefaultRoutesSourceSet.class);
        }

        @Mutate
        void createJvmSourceSets(ModelMap<PlayApplicationSpec> components, ServiceRegistry serviceRegistry) {
            components.beforeEach(new Action<PlayApplicationSpec>() {
                @Override
                public void execute(PlayApplicationSpec playComponent) {
                    playComponent.getSource().create("scala", ScalaLanguageSourceSet.class, new Action<ScalaLanguageSourceSet>() {
                        @Override
                        public void execute(ScalaLanguageSourceSet scalaSources) {
                            scalaSources.getSource().srcDir("app");
                            scalaSources.getSource().include("**/*.scala");
                        }
                    });

                    playComponent.getSource().create("java", JavaSourceSet.class, new Action<JavaSourceSet>() {
                        @Override
                        public void execute(JavaSourceSet javaSources) {
                            javaSources.getSource().srcDir("app");
                            javaSources.getSource().include("**/*.java");
                        }
                    });

                    playComponent.getSource().create("resources", JvmResourceSet.class, new Action<JvmResourceSet>() {
                        @Override
                        public void execute(JvmResourceSet appResources) {
                            appResources.getSource().srcDirs("conf");
                        }
                    });
                }
            });
        }

        @Validate
        void failOnMultiplePlayComponents(ModelMap<PlayApplicationSpec> container) {
            if (container.size() >= 2) {
                throw new GradleException("Multiple components of type 'PlayApplicationSpec' are not supported.");
            }
        }

        @Validate
        void failOnMultipleTargetPlatforms(ModelMap<PlayApplicationSpec> playApplications) {
            playApplications.afterEach(new Action<PlayApplicationSpec>() {
                public void execute(PlayApplicationSpec playApplication) {
                    PlayApplicationSpecInternal playApplicationInternal = (PlayApplicationSpecInternal) playApplication;
                    if (playApplicationInternal.getTargetPlatforms().size() > 1) {
                        throw new GradleException("Multiple target platforms for 'PlayApplicationSpec' is not (yet) supported.");
                    }
                }
            });
        }

        @ComponentBinaries
        void createBinaries(ModelMap<PlayApplicationBinarySpec> binaries, final PlayApplicationSpec componentSpec,
                            final PlatformResolvers platforms, final PlayPluginConfigurations configurations, final ServiceRegistry serviceRegistry,
                            @Path("buildDir") final File buildDir, final ProjectIdentifier projectIdentifier) {

            final FileResolver fileResolver = serviceRegistry.get(FileResolver.class);
            final Instantiator instantiator = serviceRegistry.get(Instantiator.class);
            final ToolResolver toolResolver = serviceRegistry.get(ToolResolver.class);
            final String binaryName = String.format("%sBinary", componentSpec.getName());

            binaries.create(binaryName, new Action<PlayApplicationBinarySpec>() {
                public void execute(PlayApplicationBinarySpec playBinary) {
                    PlayApplicationBinarySpecInternal playBinaryInternal = (PlayApplicationBinarySpecInternal) playBinary;
                    playBinaryInternal.setApplication(componentSpec);
                    final File binaryBuildDir = new File(buildDir, binaryName);

                    final PlayPlatform chosenPlatform = resolveTargetPlatform(componentSpec, platforms, configurations);
                    initialiseConfigurations(configurations, chosenPlatform);

                    playBinaryInternal.setTargetPlatform(chosenPlatform);
                    playBinaryInternal.setToolResolver(toolResolver);

                    File mainJar = new File(binaryBuildDir, String.format("lib/%s.jar", projectIdentifier.getName()));
                    File assetsJar = new File(binaryBuildDir, String.format("lib/%s-assets.jar", projectIdentifier.getName()));
                    playBinaryInternal.setJarFile(mainJar);
                    playBinaryInternal.setAssetsJarFile(assetsJar);

                    configurations.getPlay().addArtifact(new DefaultPublishArtifact(projectIdentifier.getName(), "jar", "jar", null, new Date(), mainJar, playBinaryInternal));
                    configurations.getPlay().addArtifact(new DefaultPublishArtifact(projectIdentifier.getName(), "jar", "jar", "assets", new Date(), assetsJar, playBinaryInternal));

                    JvmClasses classes = playBinary.getClasses();
                    classes.setClassesDir(new File(binaryBuildDir, "classes"));

                    ModelMap<JvmResourceSet> jvmResourceSets = componentSpec.getSource().withType(JvmResourceSet.class);
                    for (JvmResourceSet jvmResourceSet : jvmResourceSets.values()) {
                        for (File resourceDir : jvmResourceSet.getSource()) {
                            classes.addResourceDir(resourceDir);
                        }
                    }

                    // TODO:DAZ These should be configured on the component
                    PublicAssets assets = playBinary.getAssets();
                    assets.addAssetDir(new File(projectIdentifier.getProjectDir(), "public"));

                    playBinaryInternal.setClasspath(configurations.getPlay().getFileCollection());

                    DeploymentRegistry deploymentRegistry = serviceRegistry.get(DeploymentRegistry.class);
                    // this doesn't handle a scenario where a binary name changes between builds in the same
                    // session.  We only allow one play component/binary right now, so this isn't an issue, but
                    // it will need to be dealt with if we ever support multiple play binaries in a project.
                    String deploymentId = getDeploymentId(projectIdentifier, playBinary.getName(), chosenPlatform.getName());
                    if (deploymentRegistry.get(PlayApplicationDeploymentHandle.class, deploymentId) == null) {
                        ToolResolver toolResolver = serviceRegistry.get(ToolResolver.class);
                        final ResolvedTool<PlayApplicationRunner> playApplicationRunnerTool = toolResolver.resolve(PlayApplicationRunner.class, chosenPlatform);

                        if (playApplicationRunnerTool.isAvailable()) {
                            // we resolve the runner now so that we we don't carry all of the baggage from PlayToolProvider across builds via the registry
                            deploymentRegistry.register(deploymentId, new PlayApplicationDeploymentHandle(deploymentId, playApplicationRunnerTool.get()));
                        }
                    }
                }
            });
        }

        private PlayPlatform resolveTargetPlatform(PlayApplicationSpec componentSpec, final PlatformResolvers platforms, PlayPluginConfigurations configurations) {
            PlatformRequirement targetPlatform = getTargetPlatform((PlayApplicationSpecInternal) componentSpec);
            return platforms.resolve(PlayPlatform.class, targetPlatform);
        }

        private PlatformRequirement getTargetPlatform(PlayApplicationSpecInternal playApplicationSpec) {
            if (playApplicationSpec.getTargetPlatforms().isEmpty()) {
                String defaultPlayPlatform = String.format("play-%s", DefaultPlayPlatform.DEFAULT_PLAY_VERSION);
                return DefaultPlatformRequirement.create(defaultPlayPlatform);
            }
            return playApplicationSpec.getTargetPlatforms().get(0);
        }

        private void initialiseConfigurations(PlayPluginConfigurations configurations, PlayPlatform playPlatform) {
            configurations.getPlayPlatform().addDependency(((PlayPlatformInternal) playPlatform).getDependencyNotation("play"));
            configurations.getPlayTest().addDependency(((PlayPlatformInternal) playPlatform).getDependencyNotation("play-test"));
            configurations.getPlayRun().addDependency(((PlayPlatformInternal) playPlatform).getDependencyNotation("play-docs"));

            addRunSupportDependencies(configurations, playPlatform);
        }

        private void addRunSupportDependencies(PlayPluginConfigurations configurations, PlayPlatform playPlatform) {
            if (PlayMajorVersion.forPlatform(playPlatform) != PlayMajorVersion.PLAY_2_2_X) {
                List<?> runSupportDependencies = createRunSupportDependencies(playPlatform);
                for (Object dependencyNotation : runSupportDependencies) {
                    configurations.getPlayRun().addDependency(dependencyNotation);
                }
            }
        }

        private List<?> createRunSupportDependencies(PlayPlatform playPlatform) {
            ImmutableList.Builder<Object> listBuilder = ImmutableList.builder();

            String scalaCompatibilityVersion = playPlatform.getScalaPlatform().getScalaCompatibilityVersion();

            // run-support is available in Play >= 2.3.7
            VersionNumber playVersion = VersionNumber.parse(playPlatform.getPlayVersion());
            if (playVersion.compareTo(MINIMUM_PLAY_VERSION_WITH_RUN_SUPPORT) >= 0) {
                // run-support contains AssetsClassLoader class, which is required for reloading support
                listBuilder.add(((PlayPlatformInternal) playPlatform).getDependencyNotation(RUN_SUPPORT_PLAY_MODULE));
            } else {
                // use run-support from default version for older Play 2.3.x versions
                DefaultExternalModuleDependency runSupportDependency = new DefaultExternalModuleDependency("com.typesafe.play", String.format("%s_%s", RUN_SUPPORT_PLAY_MODULE, scalaCompatibilityVersion), DefaultPlayPlatform.DEFAULT_PLAY_VERSION);
                runSupportDependency.setTransitive(false);
                listBuilder.add(runSupportDependency);
            }

            // the name is "io" for Scala 2.10 , but "io_2.11" for Scala 2.11
            String name = scalaCompatibilityVersion.equals("2.10") ? "io" : String.format("%s_%s", "io", scalaCompatibilityVersion);
            // this dependency is only available in ivy repo that doesn't have a proper default configuration
            // must specify configuration to resolve dependency
            String sbtIoVersion = PLAY_TO_SBT_IO_VERSION_MAPPING.get(PlayMajorVersion.forPlatform(playPlatform));
            DefaultExternalModuleDependency dependency = new DefaultExternalModuleDependency("org.scala-sbt", name, sbtIoVersion, "runtime");
            dependency.setTransitive(false);
            listBuilder.add(dependency);

            return listBuilder.build();
        }

        @Mutate
        void createTwirlSourceSets(ModelMap<PlayApplicationSpec> components) {
            components.beforeEach(new Action<PlayApplicationSpec>() {
                @Override
                public void execute(PlayApplicationSpec playComponent) {
                    playComponent.getSource().create("twirlTemplates", TwirlSourceSet.class, new Action<TwirlSourceSet>() {
                        @Override
                        public void execute(TwirlSourceSet twirlSourceSet) {
                            twirlSourceSet.getSource().srcDir("app");
                            twirlSourceSet.getSource().include("**/*.html");
                        }
                    });
                }
            });
        }

        @Mutate
        void createRoutesSourceSets(ModelMap<PlayApplicationSpec> components) {
            components.beforeEach(new Action<PlayApplicationSpec>() {
                @Override
                public void execute(PlayApplicationSpec playComponent) {
                    playComponent.getSource().create("routes", RoutesSourceSet.class, new Action<RoutesSourceSet>() {
                        @Override
                        public void execute(RoutesSourceSet routesSourceSet) {
                            routesSourceSet.getSource().srcDir("conf");
                            routesSourceSet.getSource().include("routes");
                            routesSourceSet.getSource().include("*.routes");
                        }
                    });
                }
            });
        }

        @Mutate
        void createGeneratedScalaSourceSets(ModelMap<PlayApplicationBinarySpec> binaries, final ServiceRegistry serviceRegistry) {
            createGeneratedScalaSourceSetsForType(TwirlSourceSet.class, binaries, serviceRegistry);
            createGeneratedScalaSourceSetsForType(RoutesSourceSet.class, binaries, serviceRegistry);
        }

        void createGeneratedScalaSourceSetsForType(final Class<? extends LanguageSourceSet> languageSourceSetType, ModelMap<PlayApplicationBinarySpec> binaries, ServiceRegistry serviceRegistry) {
            final FileResolver fileResolver = serviceRegistry.get(FileResolver.class);
            final Instantiator instantiator = serviceRegistry.get(Instantiator.class);
            binaries.all(new Action<PlayApplicationBinarySpec>() {
                @Override
                public void execute(PlayApplicationBinarySpec playApplicationBinarySpec) {
                    // TODO:DAZ We'll need a different container of source sets for generated sources (can't add new ones while we iterate over the set)
                    for (LanguageSourceSet languageSourceSet : playApplicationBinarySpec.getSource().withType(languageSourceSetType)) {
                        String name = String.format("%sScalaSources", languageSourceSet.getName());
                        ScalaLanguageSourceSet twirlScalaSources = BaseLanguageSourceSet.create(DefaultScalaLanguageSourceSet.class, name, playApplicationBinarySpec.getName(), fileResolver, instantiator);
                        playApplicationBinarySpec.getGeneratedScala().put(languageSourceSet, twirlScalaSources);
                    }
                }
            });
        }

        @BinaryTasks
        void createTwirlCompileTasks(ModelMap<Task> tasks, final PlayApplicationBinarySpec binary, ServiceRegistry serviceRegistry, @Path("buildDir") final File buildDir) {
            final ToolResolver toolResolver = serviceRegistry.get(ToolResolver.class);
            final ResolvedTool<Compiler<TwirlCompileSpec>> compilerTool = toolResolver.resolveCompiler(TwirlCompileSpec.class, binary.getTargetPlatform());
            for (final TwirlSourceSet twirlSourceSet : binary.getSource().withType(TwirlSourceSet.class)) {
                final String twirlCompileTaskName = String.format("compile%s%s", StringUtils.capitalize(binary.getName()), StringUtils.capitalize(twirlSourceSet.getName()));
                final File twirlCompileOutputDirectory = srcOutputDirectory(buildDir, binary, twirlCompileTaskName);

                tasks.create(twirlCompileTaskName, TwirlCompile.class, new Action<TwirlCompile>() {
                    public void execute(TwirlCompile twirlCompile) {
                        twirlCompile.setDependencyNotation(TwirlCompilerFactory.createAdapter(binary.getTargetPlatform()).getDependencyNotation());
                        twirlCompile.setSource(twirlSourceSet.getSource());
                        twirlCompile.setOutputDirectory(twirlCompileOutputDirectory);
                        twirlCompile.setCompilerTool(compilerTool);

                        ScalaLanguageSourceSet twirlScalaSources = binary.getGeneratedScala().get(twirlSourceSet);
                        twirlScalaSources.getSource().srcDir(twirlCompileOutputDirectory);
                        twirlScalaSources.builtBy(twirlCompile);
                    }
                });
            }
        }

        @BinaryTasks
        void createRoutesCompileTasks(ModelMap<Task> tasks, final PlayApplicationBinarySpec binary, ServiceRegistry serviceRegistry, @Path("buildDir") final File buildDir) {
            final ToolResolver toolResolver = serviceRegistry.get(ToolResolver.class);
            final ResolvedTool<Compiler<RoutesCompileSpec>> compilerTool = toolResolver.resolveCompiler(RoutesCompileSpec.class, binary.getTargetPlatform());
            for (final RoutesSourceSet routesSourceSet : binary.getSource().withType(RoutesSourceSet.class)) {
                final String routesCompileTaskName = String.format("compile%s%s", StringUtils.capitalize(binary.getName()), StringUtils.capitalize(routesSourceSet.getName()));
                final File routesCompilerOutputDirectory = srcOutputDirectory(buildDir, binary, routesCompileTaskName);

                tasks.create(routesCompileTaskName, RoutesCompile.class, new Action<RoutesCompile>() {
                    public void execute(RoutesCompile routesCompile) {
                        routesCompile.setCompilerTool(compilerTool);
                        routesCompile.setAdditionalImports(new ArrayList<String>());
                        routesCompile.setSource(routesSourceSet.getSource());
                        routesCompile.setOutputDirectory(routesCompilerOutputDirectory);

                        ScalaLanguageSourceSet routesScalaSources = binary.getGeneratedScala().get(routesSourceSet);
                        routesScalaSources.getSource().srcDir(routesCompilerOutputDirectory);
                        routesScalaSources.builtBy(routesCompile);
                    }
                });
            }
        }

        @BinaryTasks
        void createScalaCompileTask(ModelMap<Task> tasks, final PlayApplicationBinarySpec binary, @Path("buildDir") final File buildDir) {
            final String scalaCompileTaskName = String.format("compile%s%s", StringUtils.capitalize(binary.getName()), "Scala");
            tasks.create(scalaCompileTaskName, PlatformScalaCompile.class, new Action<PlatformScalaCompile>() {
                public void execute(PlatformScalaCompile scalaCompile) {

                    scalaCompile.setDestinationDir(binary.getClasses().getClassesDir());
                    scalaCompile.setPlatform(binary.getTargetPlatform().getScalaPlatform());
                    //infer scala classpath
                    String targetCompatibility = binary.getTargetPlatform().getJavaPlatform().getTargetCompatibility().getMajorVersion();
                    scalaCompile.setSourceCompatibility(targetCompatibility);
                    scalaCompile.setTargetCompatibility(targetCompatibility);

                    IncrementalCompileOptions incrementalOptions = scalaCompile.getScalaCompileOptions().getIncrementalOptions();
                    incrementalOptions.setAnalysisFile(new File(buildDir, String.format("tmp/scala/compilerAnalysis/%s.analysis", scalaCompileTaskName)));

                    for (LanguageSourceSet appSources : binary.getSource().withType(ScalaLanguageSourceSet.class)) {
                        scalaCompile.source(appSources.getSource());
                        scalaCompile.dependsOn(appSources);
                    }

                    for (LanguageSourceSet appSources : binary.getSource().withType(JavaSourceSet.class)) {
                        scalaCompile.source(appSources.getSource());
                        scalaCompile.dependsOn(appSources);
                    }

                    for (LanguageSourceSet generatedSourceSet : binary.getGeneratedScala().values()) {
                        scalaCompile.source(generatedSourceSet.getSource());
                        scalaCompile.dependsOn(generatedSourceSet);
                    }

                    scalaCompile.setClasspath(((PlayApplicationBinarySpecInternal) binary).getClasspath());

                    binary.getClasses().builtBy(scalaCompile);
                }
            });
        }

        @BinaryTasks
        void createJarTasks(ModelMap<Task> tasks, final PlayApplicationBinarySpec binary) {
            String jarTaskName = String.format("create%sJar", StringUtils.capitalize(binary.getName()));
            tasks.create(jarTaskName, Jar.class, new Action<Jar>() {
                public void execute(Jar jar) {
                    jar.setDestinationDir(binary.getJarFile().getParentFile());
                    jar.setArchiveName(binary.getJarFile().getName());
                    jar.from(binary.getClasses().getClassesDir());
                    jar.from(binary.getClasses().getResourceDirs());
                    jar.dependsOn(binary.getClasses());
                }
            });

            String assetsJarTaskName = String.format("create%sAssetsJar", StringUtils.capitalize(binary.getName()));
            tasks.create(assetsJarTaskName, Jar.class, new Action<Jar>() {
                public void execute(Jar jar) {
                    jar.setDestinationDir(binary.getAssetsJarFile().getParentFile());
                    jar.setArchiveName(binary.getAssetsJarFile().getName());
                    jar.setClassifier("assets");
                    CopySpecInternal newSpec = jar.getRootSpec().addChild();
                    newSpec.from(binary.getAssets().getAssetDirs());
                    newSpec.into("public");
                    jar.dependsOn(binary.getAssets());
                }
            });
        }

        // TODO:DAZ Need a nice way to create tasks that are associated with a binary but not part of _building_ it.
        @Mutate
        void createPlayRunTask(ModelMap<Task> tasks, BinaryContainer binaryContainer, ServiceRegistry serviceRegistry, final PlayPluginConfigurations configurations, ProjectIdentifier projectIdentifier) {
            final DeploymentRegistry deploymentRegistry = serviceRegistry.get(DeploymentRegistry.class);
            for (final PlayApplicationBinarySpecInternal binary : binaryContainer.withType(PlayApplicationBinarySpecInternal.class)) {
                String runTaskName = String.format("run%s", StringUtils.capitalize(binary.getName()));
                final String deploymentId = getDeploymentId(projectIdentifier, binary.getName(), binary.getTargetPlatform().getName());
                tasks.create(runTaskName, PlayRun.class, new Action<PlayRun>() {
                    public void execute(PlayRun playRun) {
                        playRun.setDescription("Runs the Play application for local development.");
                        playRun.setHttpPort(DEFAULT_HTTP_PORT);
                        playRun.setDeploymentRegistry(deploymentRegistry);
                        playRun.setDeploymentId(deploymentId);
                        playRun.setApplicationJar(binary.getJarFile());
                        playRun.setAssetsJar(binary.getAssetsJarFile());
                        playRun.setAssetsDirs(binary.getAssets().getAssetDirs());
                        playRun.setRuntimeClasspath(configurations.getPlayRun().getFileCollection());
                        playRun.dependsOn(binary.getBuildTask());
                    }
                });
            }
        }

        private File srcOutputDirectory(File buildDir, PlayApplicationBinarySpec binary, String taskName) {
            return new File(buildDir, String.format("%s/src/%s", binary.getName(), taskName));
        }

        private String getDeploymentId(ProjectIdentifier projectIdentifier, String binaryName, String platformName) {
            return projectIdentifier.getPath().concat(":").concat(binaryName).concat(":").concat(platformName);
        }
    }
}


File: subprojects/platform-play/src/main/java/org/gradle/play/plugins/PlayDistributionPlugin.java
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

package org.gradle.play.plugins;

import com.google.common.collect.Maps;
import org.apache.commons.lang.StringUtils;
import org.gradle.api.*;
import org.gradle.api.file.CopySpec;
import org.gradle.api.internal.file.FileOperations;
import org.gradle.api.internal.file.copy.CopySpecInternal;
import org.gradle.api.tasks.Copy;
import org.gradle.api.tasks.application.CreateStartScripts;
import org.gradle.api.tasks.bundling.Zip;
import org.gradle.internal.reflect.Instantiator;
import org.gradle.internal.service.ServiceRegistry;
import org.gradle.jvm.tasks.Jar;
import org.gradle.model.*;
import org.gradle.platform.base.BinaryContainer;
import org.gradle.play.PlayApplicationBinarySpec;
import org.gradle.play.distribution.PlayDistribution;
import org.gradle.play.distribution.PlayDistributionContainer;
import org.gradle.play.internal.distribution.DefaultPlayDistribution;
import org.gradle.play.internal.distribution.DefaultPlayDistributionContainer;
import org.gradle.util.CollectionUtils;

import java.io.File;
import java.util.Map;
import java.util.Set;

/**
 * A plugin that adds a distribution zip to a Play application build.
 */
@SuppressWarnings("UnusedDeclaration")
@Incubating
public class PlayDistributionPlugin extends RuleSource {
    public static final String DISTRIBUTION_GROUP = "distribution";

    @Model
    PlayDistributionContainer distributions(ServiceRegistry serviceRegistry) {
        Instantiator instantiator = serviceRegistry.get(Instantiator.class);
        return new DefaultPlayDistributionContainer(instantiator);
    }

    @Mutate
    void createLifecycleTasks(ModelMap<Task> tasks) {
        tasks.create("dist", new Action<Task>() {
            @Override
            public void execute(Task task) {
                task.setDescription("Assembles all Play distributions.");
                task.setGroup(DISTRIBUTION_GROUP);
            }
        });

        tasks.create("stage", new Action<Task>() {
            @Override
            public void execute(Task task) {
                task.setDescription("Stages all Play distributions.");
                task.setGroup(DISTRIBUTION_GROUP);
            }
        });
    }

    @Defaults
    void createDistributions(@Path("distributions") PlayDistributionContainer distributions, BinaryContainer binaryContainer, PlayPluginConfigurations configurations, ServiceRegistry serviceRegistry) {
        FileOperations fileOperations = serviceRegistry.get(FileOperations.class);
        Instantiator instantiator = serviceRegistry.get(Instantiator.class);
        for (PlayApplicationBinarySpec binary : binaryContainer.withType(PlayApplicationBinarySpec.class)) {
            PlayDistribution distribution = instantiator.newInstance(DefaultPlayDistribution.class, binary.getName(), fileOperations.copySpec(), binary);
            distribution.setBaseName(binary.getName());
            distributions.add(distribution);
        }
    }

    @Mutate
    void createDistributionContentTasks(ModelMap<Task> tasks, final @Path("buildDir") File buildDir,
                                        final @Path("distributions") PlayDistributionContainer distributions,
                                        final PlayPluginConfigurations configurations) {
        for (PlayDistribution distribution : distributions.withType(PlayDistribution.class)) {
            final PlayApplicationBinarySpec binary = distribution.getBinary();
            if (binary == null) {
                throw new InvalidUserCodeException(String.format("Play Distribution '%s' does not have a configured Play binary.", distribution.getName()));
            }

            final File distJarDir = new File(buildDir, String.format("distributionJars/%s", distribution.getName()));
            final String jarTaskName = String.format("create%sDistributionJar", StringUtils.capitalize(distribution.getName()));
            tasks.create(jarTaskName, Jar.class, new Action<Jar>() {
                @Override
                public void execute(Jar jar) {
                    jar.dependsOn(binary.getTasks().withType(Jar.class));
                    jar.from(jar.getProject().zipTree(binary.getJarFile()));
                    jar.setDestinationDir(distJarDir);
                    jar.setArchiveName(binary.getJarFile().getName());

                    Map<String, Object> classpath = Maps.newHashMap();
                    classpath.put("Class-Path", new PlayManifestClasspath(configurations.getPlayRun(), binary.getAssetsJarFile()));
                    jar.getManifest().attributes(classpath);
                }
            });
            final Task distributionJar = tasks.get(jarTaskName);

            final File scriptsDir = new File(buildDir, String.format("scripts/%s", distribution.getName()));
            String createStartScriptsTaskName = String.format("create%sStartScripts", StringUtils.capitalize(distribution.getName()));
            tasks.create(createStartScriptsTaskName, CreateStartScripts.class, new Action<CreateStartScripts>() {
                @Override
                public void execute(CreateStartScripts createStartScripts) {
                    createStartScripts.setDescription("Creates OS specific scripts to run the Play application.");
                    createStartScripts.setClasspath(distributionJar.getOutputs().getFiles());
                    createStartScripts.setMainClassName("play.core.server.NettyServer");
                    createStartScripts.setApplicationName(binary.getName());
                    createStartScripts.setOutputDir(scriptsDir);
                }
            });
            Task createStartScripts = tasks.get(createStartScriptsTaskName);

            CopySpecInternal distSpec = (CopySpecInternal) distribution.getContents();
            CopySpec libSpec = distSpec.addChild().into("lib");
            libSpec.from(distributionJar);
            libSpec.from(binary.getAssetsJarFile());
            libSpec.from(configurations.getPlayRun().getFileCollection());

            CopySpec binSpec = distSpec.addChild().into("bin");
            binSpec.from(createStartScripts);
            binSpec.setFileMode(0755);

            CopySpec confSpec = distSpec.addChild().into("conf");
            confSpec.from("conf").exclude("routes");
            distSpec.from("README");
        }
    }

    @Mutate
    void createDistributionZipTasks(ModelMap<Task> tasks, final @Path("buildDir") File buildDir, PlayDistributionContainer distributions) {
        for (final PlayDistribution distribution : distributions.withType(PlayDistribution.class)) {
            final String stageTaskName = String.format("stage%sDist", StringUtils.capitalize(distribution.getName()));
            final File stageDir = new File(buildDir, "stage");
            final String baseName = StringUtils.isNotEmpty(distribution.getBaseName()) ? distribution.getBaseName() : distribution.getName();
            tasks.create(stageTaskName, Copy.class, new Action<Copy>() {
                @Override
                public void execute(Copy copy) {
                    copy.setDescription("Copies the binary distribution to a staging directory.");
                    copy.setGroup(DISTRIBUTION_GROUP);
                    copy.setDestinationDir(stageDir);

                    CopySpecInternal baseSpec = copy.getRootSpec().addChild();
                    baseSpec.into(baseName);
                    baseSpec.with(distribution.getContents());
                }
            });
            tasks.named("stage", new Action<Task>() {
                @Override
                public void execute(Task task) {
                    task.dependsOn(stageTaskName);
                }
            });

            final Task stageTask = tasks.get(stageTaskName);
            final String distributionTaskName = String.format("create%sDist", StringUtils.capitalize(distribution.getName()));
            tasks.create(distributionTaskName, Zip.class, new Action<Zip>() {
                @Override
                public void execute(final Zip zip) {
                    zip.setDescription("Bundles the Play binary as a distribution.");
                    zip.setGroup(DISTRIBUTION_GROUP);
                    zip.setArchiveName(String.format("%s.zip", baseName));
                    zip.setDestinationDir(new File(buildDir, "distributions"));
                    zip.from(stageTask);
                }
            });

            tasks.named("dist", new Action<Task>() {
                @Override
                public void execute(Task task) {
                    task.dependsOn(distributionTaskName);
                }
            });
        }
    }

    /**
     * Represents a classpath to be defined in a jar manifest
     */
    static class PlayManifestClasspath {
        final PlayPluginConfigurations.PlayConfiguration playConfiguration;
        final File assetsJarFile;

        public PlayManifestClasspath(PlayPluginConfigurations.PlayConfiguration playConfiguration, File assetsJarFile) {
            this.playConfiguration = playConfiguration;
            this.assetsJarFile = assetsJarFile;
        }

        @Override
        public String toString() {
            Set<File> classpathFiles = playConfiguration.getFileCollection().getFiles();
            classpathFiles.add(assetsJarFile);
            Set<String> classpathFileNames = CollectionUtils.collect(classpathFiles, new Transformer<String, File>() {
                @Override
                public String transform(File file) {
                    return file.getName();
                }
            });

            return StringUtils.join(classpathFileNames, " ");
        }
    }
}


File: subprojects/platform-play/src/main/java/org/gradle/play/plugins/PlayPluginConfigurations.java
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

package org.gradle.play.plugins;

import org.gradle.api.artifacts.Configuration;
import org.gradle.api.artifacts.ConfigurationContainer;
import org.gradle.api.artifacts.Dependency;
import org.gradle.api.artifacts.PublishArtifact;
import org.gradle.api.artifacts.dsl.DependencyHandler;
import org.gradle.api.file.FileCollection;

/**
 * Conventional locations and names for play plugins.
 */
public class PlayPluginConfigurations {
    public static final String PLATFORM_CONFIGURATION = "playPlatform";
    public static final String COMPILE_CONFIGURATION = "play";
    public static final String RUN_CONFIGURATION = "playRun";
    public static final String TEST_COMPILE_CONFIGURATION = "playTest";

    private final ConfigurationContainer configurations;
    private final DependencyHandler dependencyHandler;

    public PlayPluginConfigurations(ConfigurationContainer configurations, DependencyHandler dependencyHandler) {
        this.configurations = configurations;
        this.dependencyHandler = dependencyHandler;
        Configuration playPlatform = configurations.create(PLATFORM_CONFIGURATION);

        Configuration playCompile = configurations.create(COMPILE_CONFIGURATION);
        playCompile.extendsFrom(playPlatform);

        Configuration playRun = configurations.create(RUN_CONFIGURATION);
        playRun.extendsFrom(playCompile);

        Configuration playTestCompile = configurations.create(TEST_COMPILE_CONFIGURATION);
        playTestCompile.extendsFrom(playCompile);

        configurations.maybeCreate(Dependency.DEFAULT_CONFIGURATION).extendsFrom(playCompile);
    }

    public PlayConfiguration getPlayPlatform() {
        return new PlayConfiguration(PLATFORM_CONFIGURATION);
    }

    public PlayConfiguration getPlay() {
        return new PlayConfiguration(COMPILE_CONFIGURATION);
    }

    public PlayConfiguration getPlayRun() {
        return new PlayConfiguration(RUN_CONFIGURATION);
    }

    public PlayConfiguration getPlayTest() {
        return new PlayConfiguration(TEST_COMPILE_CONFIGURATION);
    }

    /**
     * Wrapper around a Configuration instance used by the PlayApplicationPlugin.
     */
    class PlayConfiguration {
        private final String name;

        PlayConfiguration(String name) {
            this.name = name;
        }

        FileCollection getFileCollection() {
            return configurations.getByName(name);
        }

        void addDependency(Object notation) {
            dependencyHandler.add(name, notation);
        }

        void addArtifact(PublishArtifact artifact) {
            configurations.getByName(name).getArtifacts().add(artifact);
        }
    }
}


File: subprojects/platform-play/src/main/java/org/gradle/play/tasks/PlayRun.java
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

package org.gradle.play.tasks;

import org.gradle.api.GradleException;
import org.gradle.api.Incubating;
import org.gradle.api.UncheckedIOException;
import org.gradle.api.file.FileCollection;
import org.gradle.api.internal.ConventionTask;
import org.gradle.api.tasks.InputFile;
import org.gradle.api.tasks.InputFiles;
import org.gradle.api.tasks.TaskAction;
import org.gradle.api.tasks.compile.BaseForkOptions;
import org.gradle.deployment.internal.DeploymentRegistry;
import org.gradle.logging.ProgressLogger;
import org.gradle.logging.ProgressLoggerFactory;
import org.gradle.play.internal.run.DefaultPlayRunSpec;
import org.gradle.play.internal.run.PlayApplicationDeploymentHandle;
import org.gradle.play.internal.run.PlayRunSpec;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.Set;

/**
 * Task to run a Play application.
 */
@Incubating
public class PlayRun extends ConventionTask {
    private static Logger logger = LoggerFactory.getLogger(PlayRun.class);

    private int httpPort;

    @InputFile
    private File applicationJar;

    @InputFile
    private File assetsJar;

    @InputFiles
    private Set<File> assetsDirs;

    @InputFiles
    private FileCollection runtimeClasspath;

    private BaseForkOptions forkOptions;

    private DeploymentRegistry deploymentRegistry;

    private String deploymentId;

    /**
     * fork options for the running a Play application.
     */
    public BaseForkOptions getForkOptions() {
        if (forkOptions == null) {
            forkOptions = new BaseForkOptions();
        }
        return forkOptions;
    }

    @TaskAction
    public void run() {
        PlayApplicationDeploymentHandle deploymentHandle = deploymentRegistry.get(PlayApplicationDeploymentHandle.class, deploymentId);
        if (deploymentHandle == null) {
            throw new GradleException("There are no deployment handles registered with id '".concat(deploymentId).concat("'"));
        }

        ProgressLoggerFactory progressLoggerFactory = getServices().get(ProgressLoggerFactory.class);
        ProgressLogger progressLogger = progressLoggerFactory.newOperation(PlayRun.class)
                .start("Start Play server", "Starting Play");

        int httpPort = getHttpPort();
        PlayRunSpec spec = new DefaultPlayRunSpec(runtimeClasspath, applicationJar, assetsJar, assetsDirs, getProject().getProjectDir(), getForkOptions(), httpPort);

        try {
            deploymentHandle.start(spec);
            progressLogger.completed();
            progressLogger = progressLoggerFactory.newOperation(PlayRun.class)
                    .start(String.format("Run Play App at http://localhost:%d/", httpPort),
                            String.format("Running at http://localhost:%d/", httpPort));
            if (!getProject().getGradle().getStartParameter().isContinuous()) {
                waitForCtrlD();
            }
        } finally {
            progressLogger.completed();
        }
    }

    private void waitForCtrlD() {
        while (true) {
            try {
                int c = System.in.read();
                if (c == -1 || c == 4) {
                    // STOP on Ctrl-D or EOF.
                    logger.info("received end of stream (ctrl+d)");
                    return;
                }
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        }
    }

    /**
     * The HTTP port listened to by the Play application.
     *
     * This port should be available.  The Play application will fail to start if the port is already in use.
     *
     * @return HTTP port
     */
    public int getHttpPort() {
        return httpPort;
    }

    public void setHttpPort(int httpPort) {
        this.httpPort = httpPort;
    }

    public void setApplicationJar(File applicationJar) {
        this.applicationJar = applicationJar;
    }

    public void setAssetsJar(File assetsJar) {
        this.assetsJar = assetsJar;
    }

    public void setAssetsDirs(Set<File> assetsDirs) {
        this.assetsDirs = assetsDirs;
    }

    public void setRuntimeClasspath(FileCollection runtimeClasspath) {
        this.runtimeClasspath = runtimeClasspath;
    }

    public void setDeploymentRegistry(DeploymentRegistry deploymentRegistry) {
        this.deploymentRegistry = deploymentRegistry;
    }

    public void setDeploymentId(String deploymentId) {
        this.deploymentId = deploymentId;
    }
}
