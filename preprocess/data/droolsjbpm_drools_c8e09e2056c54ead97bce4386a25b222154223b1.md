Refactoring Types: ['Extract Method', 'Extract Interface']
ie/builder/impl/ClasspathKieProject.java
package org.drools.compiler.kie.builder.impl;

import org.drools.compiler.kie.builder.impl.event.KieModuleDiscovered;
import org.drools.compiler.kie.builder.impl.event.KieServicesEventListerner;
import org.drools.core.util.IoUtils;
import org.drools.core.util.StringUtils;
import org.drools.compiler.kproject.ReleaseIdImpl;
import org.drools.compiler.kproject.models.KieModuleModelImpl;
import org.drools.compiler.kproject.xml.PomModel;
import org.kie.api.KieServices;
import org.kie.api.builder.ReleaseId;
import org.kie.api.builder.model.KieModuleModel;
import org.kie.api.builder.KieRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.io.UnsupportedEncodingException;
import java.lang.ref.WeakReference;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLDecoder;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

import static org.drools.compiler.kie.builder.impl.KieBuilderImpl.setDefaultsforEmptyKieModule;
import static org.drools.core.common.ProjectClassLoader.createProjectClassLoader;

/**
 * Discovers all KieModules on the classpath, via the kmodule.xml file.
 * KieBaseModels and KieSessionModels are then indexed, with helper lookups
 * Each resulting KieModule is added to the KieRepository
 *
 */
public class ClasspathKieProject extends AbstractKieProject {

    private static final Logger             log               = LoggerFactory.getLogger( ClasspathKieProject.class );

    public static final String OSGI_KIE_MODULE_CLASS_NAME     = "org.drools.osgi.compiler.OsgiKieModule";

    private Map<ReleaseId, InternalKieModule>     kieModules  = new HashMap<ReleaseId, InternalKieModule>();

    private Map<String, InternalKieModule>  kJarFromKBaseName = new HashMap<String, InternalKieModule>();

    private final KieRepository kieRepository;
    
    private final ClassLoader parentCL;

    private ClassLoader classLoader;

    private final WeakReference<KieServicesEventListerner> listener;

    ClasspathKieProject(ClassLoader parentCL, WeakReference<KieServicesEventListerner> listener) {
        this.kieRepository = KieServices.Factory.get().getRepository();
        this.listener = listener;
        this.parentCL = parentCL;
    }

    public void init() {
        this.classLoader = createProjectClassLoader(parentCL);
        discoverKieModules();
        indexParts(kieModules.values(), kJarFromKBaseName);
    }

    public ReleaseId getGAV() {
        return null;
    }

    public long getCreationTimestamp() {
        return 0L;
    }

    public void discoverKieModules() {
        String[] configFiles = {KieModuleModelImpl.KMODULE_JAR_PATH, KieModuleModelImpl.KMODULE_SPRING_JAR_PATH};
        for ( String configFile : configFiles) {
            final Enumeration<URL> e;
            try {
                e = classLoader.getResources(configFile );
            } catch ( IOException exc ) {
                log.error( "Unable to find and build index of "+configFile+"." + exc.getMessage() );
                return;
            }

            // Map of kmodule urls
            while ( e.hasMoreElements() ) {
                URL url = e.nextElement();
                notifyKieModuleFound(url);
                try {
                    InternalKieModule kModule = fetchKModule(url);

                    if (kModule != null) {
                        ReleaseId releaseId = kModule.getReleaseId();
                        kieModules.put(releaseId, kModule);

                        log.debug( "Discovered classpath module " + releaseId.toExternalForm() );

                        kieRepository.addKieModule(kModule);
                    }

                } catch ( Exception exc ) {
                    log.error( "Unable to build index of kmodule.xml url=" + url.toExternalForm() + "\n" + exc.getMessage() );
                }
            }
        }
    }

    private void notifyKieModuleFound(URL url) {
        log.info( "Found kmodule: " + url);
        if (listener != null && listener.get() != null) {
            listener.get().onKieModuleDiscovered(new KieModuleDiscovered(url.toString()));
        }
    }

    public static InternalKieModule fetchKModule(URL url) {
        if (url.toString().startsWith("bundle:")) {
            return fetchOsgiKModule(url);
        }
        return fetchKModule(url, fixURLFromKProjectPath(url));
    }

    private static InternalKieModule fetchOsgiKModule(URL url) {
        Method m;
        try {
            Class<?> c = Class.forName(OSGI_KIE_MODULE_CLASS_NAME);
            m = c.getMethod("create", URL.class);
        } catch (Exception e) {
            log.error("It is necessary to have the drools-osgi-integration module on the path in order to create a KieProject from an ogsi bundle", e);
            throw new RuntimeException(e);
        }
        try {
            return (InternalKieModule) m.invoke(null, url);
        } catch (Exception e) {
            log.error("Failure creating a OsgiKieModule caused by: " + e.getMessage(), e);
            throw new RuntimeException(e);
        }
    }

    private static void fetchKModuleFromSpring(URL kModuleUrl, String fixedURL){
        try{
            Class clazz = Class.forName("org.kie.spring.KModuleSpringMarshaller");
            Method method = clazz.getDeclaredMethod("fromXML", java.net.URL.class, String.class);
            method.invoke(null, kModuleUrl, fixedURL);
        } catch (Exception e) {
            log.error("It is necessary to have the kie-spring module on the path in order to create a KieProject from a spring context", e);
            throw new RuntimeException(e);
        }
    }

    private static InternalKieModule fetchKModule(URL url, String fixedURL) {
        if ( url.getPath().endsWith("-spring.xml")) {
            // the entire kmodule creation is happening in the kie-spring module,
            // hence we force a null return
            fetchKModuleFromSpring(url, fixedURL);
            return null;
        }
        KieModuleModel kieProject = KieModuleModelImpl.fromXML( url );

        setDefaultsforEmptyKieModule(kieProject);

        String pomProperties = getPomProperties( fixedURL );
        if (pomProperties == null) {
            log.warn("Cannot find maven pom properties for this project. Using the container's default ReleaseId");
        }

        ReleaseId releaseId = pomProperties != null ?
                              ReleaseIdImpl.fromPropertiesString(pomProperties) :
                              KieServices.Factory.get().getRepository().getDefaultReleaseId();

        String rootPath = fixedURL;
        if ( rootPath.lastIndexOf( ':' ) > 0 ) {
            rootPath = IoUtils.asSystemSpecificPath( rootPath, rootPath.lastIndexOf( ':') );
        }

        return createInternalKieModule(url, fixedURL, kieProject, releaseId, rootPath);
    }

    public static InternalKieModule createInternalKieModule(URL url, String fixedURL, KieModuleModel kieProject, ReleaseId releaseId, String rootPath) {
        File file = new File( rootPath );
        return file.isDirectory() ?
               new FileKieModule( releaseId, kieProject, file ) :
               new ZipKieModule( releaseId, kieProject, file );
    }

    public static String getPomProperties(String urlPathToAdd) {
        String pomProperties = null;
        String rootPath = urlPathToAdd;
        if ( rootPath.lastIndexOf( ':' ) > 0 ) {
            rootPath = IoUtils.asSystemSpecificPath( rootPath, rootPath.lastIndexOf( ':' ) );
        }

        if ( urlPathToAdd.endsWith( ".jar" ) || urlPathToAdd.endsWith( "/content" ) ) {
            pomProperties = getPomPropertiesFromZipFile(rootPath);
        } else {
            pomProperties = getPomPropertiesFromFileSystem(rootPath);
            if (pomProperties == null) {
                int webInf = rootPath.indexOf("/WEB-INF");
                if (webInf > 0) {
                    rootPath = rootPath.substring(0, webInf);
                    pomProperties = getPomPropertiesFromFileSystem(rootPath);
                }
            }
            if (pomProperties == null) {
                pomProperties = generatePomPropertiesFromPom(rootPath);
            }
        }

        if (pomProperties == null) {
            log.warn( "Unable to load pom.properties from" + urlPathToAdd );
        }
        return pomProperties;
    }

    private static String getPomPropertiesFromZipFile(String rootPath) {
        File actualZipFile = new File( rootPath );
        if ( !actualZipFile.exists() ) {
            log.error( "Unable to load pom.properties from" + rootPath + " as jarPath cannot be found\n" + rootPath );
            return null;
        }

        ZipFile zipFile = null;

        try {
            zipFile = new ZipFile( actualZipFile );

            String file = KieBuilderImpl.findPomProperties( zipFile );
            if ( file == null ) {
                log.warn( "Unable to find pom.properties in " + rootPath );
                return null;
            }
            ZipEntry zipEntry = zipFile.getEntry( file );

            String pomProps = StringUtils.readFileAsString(
                    new InputStreamReader( zipFile.getInputStream( zipEntry ), IoUtils.UTF8_CHARSET ) );
            log.debug( "Found and used pom.properties " + file);
            return pomProps;
        } catch ( Exception e ) {
            log.error( "Unable to load pom.properties from " + rootPath + "\n" + e.getMessage() );
        } finally {
            try {
                zipFile.close();
            } catch ( IOException e ) {
                log.error( "Error when closing InputStream to " + rootPath + "\n" + e.getMessage() );
            }
        }
        return null;
    }

    private static String getPomPropertiesFromFileSystem(String rootPath) {
        Reader reader = null;
        try {
            File file = KieBuilderImpl.findPomProperties( new File( rootPath ) );
            if ( file == null ) {
                log.warn( "Unable to find pom.properties in " + rootPath );
                return null;
            }
            reader = new InputStreamReader( new FileInputStream( file ), IoUtils.UTF8_CHARSET );
            log.debug( "Found and used pom.properties " + file);
            return StringUtils.toString( reader );
        } catch ( Exception e ) {
            log.warn( "Unable to load pom.properties tried recursing down from " + rootPath + "\n" + e.getMessage() );
        } finally {
            if ( reader != null ) {
                try {
                    reader.close();
                } catch ( IOException e ) {
                    log.error( "Error when closing InputStream to " + rootPath + "\n" + e.getMessage() );
                }
            }
        }
        return null;
    }

    private static String generatePomPropertiesFromPom(String rootPath) {
        // recurse until we reach root or find a pom.xml
        File file = null;
        for ( File folder = new File( rootPath ); folder.getParent() != null; folder = new File( folder.getParent() ) ) {
            file = new File( folder, "pom.xml" );
            if ( file.exists() ) {
                break;
            }
            file = null;
        }

        if ( file != null ) {
            FileInputStream fis = null;
            try {
                fis = new FileInputStream( file ) ;
                PomModel pomModel = PomModel.Parser.parse( rootPath + "/pom.xml", fis);

                KieBuilderImpl.validatePomModel( pomModel ); // throws an exception if invalid

                ReleaseIdImpl gav = (ReleaseIdImpl) pomModel.getReleaseId();

                String str =  KieBuilderImpl.generatePomProperties( gav );
                log.info( "Recursed up folders, found and used pom.xml " + file );

                return str;
            } catch ( Exception e ) {
                log.error( "As folder project tried to fall back to pom.xml " + file + "\nbut failed with exception:\n" + e.getMessage() );
            } finally {
                if ( fis != null ) {
                    try {
                        fis.close();
                    } catch ( IOException e ) {
                        log.error( "Error when closing InputStream to " + file + "\n" + e.getMessage() );
                    }
                }
            }
        } else {
            log.warn( "As folder project tried to fall back to pom.xml, but could not find one for " + file );
        }
        return null;
    }

    public static String fixURLFromKProjectPath(URL url) {
        String urlPath = url.toExternalForm();

        // determine resource type (eg: jar, file, bundle)
        String urlType = "file";
        int colonIndex = urlPath.indexOf( ":" );
        if ( colonIndex != -1 ) {
            urlType = urlPath.substring( 0,
                                         colonIndex );
        }

        urlPath = url.getPath();

        if ( "jar".equals( urlType ) ) {
            // switch to using getPath() instead of toExternalForm()
            if ( urlPath.indexOf( '!' ) > 0 ) {
                urlPath = urlPath.substring( 0,
                                             urlPath.indexOf( '!' ) );
            }
        } else if ( "vfs".equals( urlType ) ) {
            urlPath = getPathForVFS(url);
        } else {
            if (url.toString().contains("-spring.xml")){
                urlPath = urlPath.substring( 0, urlPath.length() - ("/" + KieModuleModelImpl.KMODULE_SPRING_JAR_PATH).length() );
            } else {
                urlPath = urlPath.substring( 0,
                        urlPath.length() - ("/" + KieModuleModelImpl.KMODULE_JAR_PATH).length() );
            }
        }

        if (urlPath.endsWith(".jar!")) {
            urlPath = urlPath.substring( 0, urlPath.length() - 1 );
        }

        // remove any remaining protocols, normally only if it was a jar
        int firstSlash = urlPath.indexOf( '/' );
        colonIndex = firstSlash > 0 ? urlPath.lastIndexOf( ":", firstSlash ) : urlPath.lastIndexOf( ":" );
        if ( colonIndex >= 0 ) {
            urlPath = IoUtils.asSystemSpecificPath(urlPath, colonIndex);
        }

        try {
            urlPath = URLDecoder.decode( urlPath,
                                         "UTF-8" );
        } catch ( UnsupportedEncodingException e ) {
            throw new IllegalArgumentException( "Error decoding URL (" + url + ") using UTF-8",
                                                e );
        }

        log.debug("KieModule URL type=" + urlType + " url=" + urlPath);

        return urlPath;
    }

    private static String getPathForVFS(URL url) {
        String urlString = url.toString();
        int kModulePos = urlString.length() - ("/" + KieModuleModelImpl.KMODULE_JAR_PATH).length();
        boolean isInJar = urlString.substring(kModulePos - 4, kModulePos).equals(".jar");

        try {
            Method m = Class.forName("org.jboss.vfs.VirtualFile").getMethod("getPhysicalFile");
            Object content = url.openConnection().getContent();
            File f = (File)m.invoke(content);
            String path = f.getPath();

            if (isInJar && path.contains("contents" + File.separator)) {
                String jarName = urlString.substring(0, kModulePos);
                jarName = jarName.substring(jarName.lastIndexOf('/')+1);
                String jarFolderPath = path.substring( 0, path.length() - ("contents/" + KieModuleModelImpl.KMODULE_JAR_PATH).length() );
                String jarPath = jarFolderPath + jarName;
                path = new File(jarPath).exists() ? jarPath : jarFolderPath + "content";
            } else if (path.endsWith(File.separator + KieModuleModelImpl.KMODULE_FILE_NAME)) {
                path = path.substring( 0, path.length() - ("/" + KieModuleModelImpl.KMODULE_JAR_PATH).length() );
            }

            log.info( "Virtual file physical path = " + path );
            return path;
        } catch (Exception e) {
            log.error( "Error when reading virtual file from " + url.toString(), e );
        }
        return url.getPath();
    }

    public InternalKieModule getKieModuleForKBase(String kBaseName) {
        return this.kJarFromKBaseName.get( kBaseName );
    }

    public ClassLoader getClassLoader() {
        return this.classLoader;
    }

    public ClassLoader getClonedClassLoader() {
        return createProjectClassLoader(classLoader.getParent());
    }

    public InputStream getPomAsStream() {
        return classLoader.getResourceAsStream("pom.xml");
    }
}


File: drools-core/src/main/java/org/drools/core/base/ClassFieldAccessorCache.java
/*
 * Copyright 2010 JBoss Inc
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

package org.drools.core.base;

import org.drools.core.util.asm.ClassFieldInspector;

import java.security.ProtectionDomain;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

public class ClassFieldAccessorCache {

    private Map<ClassLoader, CacheEntry> cacheByClassLoader;

    private ClassLoader                  classLoader;

    public ClassFieldAccessorCache(ClassLoader classLoader) {
        //        lookup = new HashMap<AccessorKey, LookupEntry>();
        cacheByClassLoader = new WeakHashMap<ClassLoader, CacheEntry>();
        this.classLoader = classLoader;
    }

    public ClassLoader getClassLoader() {
        return this.classLoader;
    }

    public ClassObjectType getClassObjectType(ClassObjectType objectType, boolean lookupClass) {
        // lookup the class when the ClassObjectType might refer to the class from another ClassLoader
        Class cls = lookupClass ? getClass( objectType.getClassName() ) : objectType.getClassType();
        CacheEntry cache = getCacheEntry( cls );
        return cache.getClassObjectType( cls,
                                         objectType );
    }

    public static class ClassObjectTypeKey {
        private Class   cls;
        private boolean event;

        public ClassObjectTypeKey(Class cls,
                                  boolean event) {
            this.cls = cls;
            this.event = event;
        }

        public Class getCls() {
            return cls;
        }

        public boolean isEvent() {
            return event;
        }

        public int hashCode() {
            final int prime = 31;
            int result = 1;
            result = prime * result + ((cls == null) ? 0 : cls.hashCode());
            result = prime * result + (event ? 1231 : 1237);
            return result;
        }

        public boolean equals(Object obj) {
            if ( this == obj ) return true;
            if ( obj == null ) return false;
            if ( !(obj instanceof ClassObjectTypeKey) ) return false;
            ClassObjectTypeKey other = (ClassObjectTypeKey) obj;
            if ( cls == null ) {
                if ( other.cls != null ) return false;
            } else if ( !cls.equals( other.cls ) ) return false;
            if ( event != other.event ) return false;
            return true;
        }

    }
    
    public BaseClassFieldReader getReadAcessor(ClassFieldReader reader) {
        String className = reader.getClassName();
        String fieldName = reader.getFieldName();

        Class cls = getClass( className );
        CacheEntry cache = getCacheEntry( cls );

        // get the ReaderAccessor for this key
        return cache.getReadAccessor( new AccessorKey( className,
                                                       fieldName,
                                                       AccessorKey.AccessorType.FieldAccessor ),
                                      cls );
    }

    public BaseClassFieldWriter getWriteAcessor(ClassFieldWriter writer) {
        String className = writer.getClassName();
        String fieldName = writer.getFieldName();

        Class cls = getClass( className );
        CacheEntry cache = getCacheEntry( cls );

        // get the ReaderAccessor for this key
        return cache.getWriteAccessor( new AccessorKey( className,
                                                        fieldName,
                                                        AccessorKey.AccessorType.FieldAccessor ),
                                       cls );
    }

    public Class getClass(String className) {
        try {
            return this.classLoader.loadClass( className );
        } catch ( ClassNotFoundException e ) {
            throw new RuntimeException( "Unable to resolve class '" + className + "'" );
        }
    }

    public CacheEntry getCacheEntry(Class cls) {
        // System classloader classes return null on some JVMs
        ClassLoader cl = cls.getClassLoader() != null ? cls.getClassLoader() : this.classLoader;

        CacheEntry cache = this.cacheByClassLoader.get( cl );
        if ( cache == null ) {
            // setup a cache for this ClassLoader
            cache = new CacheEntry( this.classLoader );
            this.cacheByClassLoader.put( cl,
                                         cache );
        }

        return cache;
    }

    public static class CacheEntry {
        private ByteArrayClassLoader                                     byteArrayClassLoader;
        private final ConcurrentMap<AccessorKey, BaseClassFieldReader>   readCache   = new ConcurrentHashMap<AccessorKey, BaseClassFieldReader>();
        private final ConcurrentMap<AccessorKey, BaseClassFieldWriter>   writeCache  = new ConcurrentHashMap<AccessorKey, BaseClassFieldWriter>();

        private final ConcurrentMap<Class< ? >, ClassFieldInspector>     inspectors  = new ConcurrentHashMap<Class< ? >, ClassFieldInspector>();

        private final ConcurrentMap<ClassObjectTypeKey, ClassObjectType> objectTypes = new ConcurrentHashMap<ClassObjectTypeKey, ClassObjectType>();

        public CacheEntry(ClassLoader parentClassLoader) {
            if ( parentClassLoader == null ) {
                throw new RuntimeException( "ClassFieldAccessorFactory cannot have a null parent ClassLoader" );
            }
            this.byteArrayClassLoader = new ByteArrayClassLoader( parentClassLoader );
        }

        public ByteArrayClassLoader getByteArrayClassLoader() {
            return byteArrayClassLoader;
        }

        public BaseClassFieldReader getReadAccessor(AccessorKey key,
                                                    Class cls) {
            BaseClassFieldReader reader = this.readCache.get( key );
            if ( reader == null ) {
                reader = ClassFieldAccessorFactory.getInstance().getClassFieldReader( cls,
                                                                                      key.getFieldName(),
                                                                                      this );
                if ( reader != null ) {
                    BaseClassFieldReader existingReader = this.readCache.putIfAbsent( key,
                                                                                      reader );
                    if ( existingReader != null ) {
                        // Raced, use the (now) existing entry
                        reader = existingReader;
                    }
                }
            }

            return reader;
        }

        public BaseClassFieldWriter getWriteAccessor(AccessorKey key,
                                                     Class cls) {
            BaseClassFieldWriter writer = this.writeCache.get( key );
            if ( writer == null ) {
                writer = ClassFieldAccessorFactory.getInstance().getClassFieldWriter( cls,
                                                                                      key.getFieldName(),
                                                                                      this );
                if ( writer != null ) {
                    BaseClassFieldWriter existingWriter = this.writeCache.putIfAbsent( key,
                                                                                       writer );
                    if ( existingWriter != null ) {
                        // Raced, use the (now) existing entry
                        writer = existingWriter;
                    }
                }
            }

            return writer;
        }

        public Map<Class< ? >, ClassFieldInspector> getInspectors() {
            return inspectors;
        }

        public ClassObjectType getClassObjectType(Class<?> cls,
                                                  ClassObjectType objectType) {
            ClassObjectTypeKey key = new ClassObjectTypeKey( cls,
                                                             objectType.isEvent() );
            ClassObjectType existing = objectTypes.get( key );

            if ( existing == null ) {
                objectType.setClassType( cls ); // most likely set, but set anyway.
                existing = objectTypes.putIfAbsent( key, objectType );
                if ( existing == null ) {
                    // Not raced, use the one we created.
                    existing = objectType;
                }
            }

            return existing;
        }

    }

    public static class ByteArrayClassLoader extends ClassLoader {
        public ByteArrayClassLoader(final ClassLoader parent) {
            super( parent );
        }

        public Class< ? > defineClass(final String name,
                                      final byte[] bytes,
                                      final ProtectionDomain domain) {
            return defineClass( name,
                                bytes,
                                0,
                                bytes.length,
                                domain );
        }
    }

}


File: drools-core/src/main/java/org/drools/core/base/ClassFieldAccessorFactory.java
/*
 * Copyright 2005 JBoss Inc
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

package org.drools.core.base;

import org.drools.core.base.ClassFieldAccessorCache.ByteArrayClassLoader;
import org.drools.core.base.ClassFieldAccessorCache.CacheEntry;
import org.drools.core.base.extractors.BaseBooleanClassFieldReader;
import org.drools.core.base.extractors.BaseBooleanClassFieldWriter;
import org.drools.core.base.extractors.BaseByteClassFieldReader;
import org.drools.core.base.extractors.BaseByteClassFieldWriter;
import org.drools.core.base.extractors.BaseCharClassFieldReader;
import org.drools.core.base.extractors.BaseCharClassFieldWriter;
import org.drools.core.base.extractors.BaseDateClassFieldReader;
import org.drools.core.base.extractors.BaseDoubleClassFieldReader;
import org.drools.core.base.extractors.BaseDoubleClassFieldWriter;
import org.drools.core.base.extractors.BaseFloatClassFieldReader;
import org.drools.core.base.extractors.BaseFloatClassFieldWriter;
import org.drools.core.base.extractors.BaseIntClassFieldReader;
import org.drools.core.base.extractors.BaseIntClassFieldWriter;
import org.drools.core.base.extractors.BaseLongClassFieldReader;
import org.drools.core.base.extractors.BaseLongClassFieldWriter;
import org.drools.core.base.extractors.BaseNumberClassFieldReader;
import org.drools.core.base.extractors.BaseObjectClassFieldReader;
import org.drools.core.base.extractors.BaseObjectClassFieldWriter;
import org.drools.core.base.extractors.BaseShortClassFieldReader;
import org.drools.core.base.extractors.BaseShortClassFieldWriter;
import org.drools.core.base.extractors.SelfReferenceClassFieldReader;
import org.drools.core.common.InternalWorkingMemory;
import org.drools.core.util.asm.ClassFieldInspector;
import org.mvel2.asm.ClassWriter;
import org.mvel2.asm.Label;
import org.mvel2.asm.MethodVisitor;
import org.mvel2.asm.Opcodes;
import org.mvel2.asm.Type;

import java.lang.reflect.Method;
import java.security.AccessController;
import java.security.PrivilegedAction;
import java.security.ProtectionDomain;
import java.util.Date;
import java.util.Map;

import static org.drools.core.rule.builder.dialect.asm.ClassGenerator.createClassWriter;

/**
 * This generates subclasses of BaseClassFieldExtractor to provide field extractors.
 * This should not be used directly, but via ClassFieldExtractor (which ensures that it is 
 * all nicely serializable).
 */

public class ClassFieldAccessorFactory {

    private static final String                        BASE_PACKAGE         = "org/drools/base";

    private static final String                        SELF_REFERENCE_FIELD = "this";

    private static final ProtectionDomain              PROTECTION_DOMAIN;
//
//    private final Map<Class< ? >, ClassFieldInspector> inspectors           = new HashMap<Class< ? >, ClassFieldInspector>();
//
//    private ByteArrayClassLoader                       byteArrayClassLoader;

    static {
        PROTECTION_DOMAIN = AccessController.doPrivileged( new PrivilegedAction<ProtectionDomain>() {
            public ProtectionDomain run() {
                return ClassFieldAccessorFactory.class.getProtectionDomain();
            }
        } );
    }
    
    private static ClassFieldAccessorFactory instance = new ClassFieldAccessorFactory();
    
    public static ClassFieldAccessorFactory getInstance() {
        return instance;
    }

    public BaseClassFieldReader getClassFieldReader(final Class< ? > clazz,
                                                    final String fieldName,
                                                    CacheEntry cache) {
        ByteArrayClassLoader byteArrayClassLoader = cache.getByteArrayClassLoader();
        Map<Class< ? >, ClassFieldInspector> inspectors = cache.getInspectors();
        try {
            // if it is a self reference
            if ( SELF_REFERENCE_FIELD.equals( fieldName ) ) {
                // then just create an instance of the special class field extractor
                return new SelfReferenceClassFieldReader( clazz,
                                                          fieldName );
            } else {
                // otherwise, bytecode generate a specific extractor
                ClassFieldInspector inspector = inspectors.get( clazz );
                if ( inspector == null ) {
                    inspector = new ClassFieldInspector( clazz );
                    inspectors.put( clazz,
                                    inspector );
                }
                Class< ? > fieldType = (Class< ? >) inspector.getFieldTypes().get( fieldName );
                Method getterMethod = (Method) inspector.getGetterMethods().get( fieldName );
                Integer index = (Integer) inspector.getFieldNames().get( fieldName );
                if ( fieldType == null && fieldName.length() > 1 && Character.isLowerCase( fieldName.charAt( 0 ) ) && Character.isUpperCase( fieldName.charAt(1) ) ) {
                    // it might be that odd case of javabeans naming conventions that does not use lower case first letters if the second is uppercase
                    String altFieldName = Character.toUpperCase( fieldName.charAt( 0 ) ) + fieldName.substring( 1 );
                    fieldType = (Class< ? >) inspector.getFieldTypes().get( altFieldName );
                    if( fieldType != null ) {
                        // it seems it is the corner case indeed.
                        getterMethod = (Method) inspector.getGetterMethods().get( altFieldName );
                        index = (Integer) inspector.getFieldNames().get( altFieldName );
                    }
                }
                if ( fieldType != null && getterMethod != null ) {
                    final String className = ClassFieldAccessorFactory.BASE_PACKAGE + "/" + Type.getInternalName( clazz ) + Math.abs( System.identityHashCode( clazz ) ) + "$" + getterMethod.getName();

                    // generating byte array to create target class
                    final byte[] bytes = dumpReader( clazz,
                                                     className,
                                                     getterMethod,
                                                     fieldType,
                                                     clazz.isInterface() );
                    // use bytes to get a class 

                    final Class< ? > newClass = byteArrayClassLoader.defineClass( className.replace( '/',
                                                                                                     '.' ),
                                                                                  bytes,
                                                                                  PROTECTION_DOMAIN );
                    // instantiating target class
                    final ValueType valueType = ValueType.determineValueType( fieldType );
                    final Object[] params = {index, fieldType, valueType};
                    return (BaseClassFieldReader) newClass.getConstructors()[0].newInstance( params );
                } else {
                    // must be a public field
                    return null;
                }
            }
        } catch ( final RuntimeException e ) {
            throw e;
        } catch ( final Exception e ) {
            throw new RuntimeException( e );
        }
    }

    public BaseClassFieldWriter getClassFieldWriter(final Class< ? > clazz,
                                                    final String fieldName,
                                                    final CacheEntry cache) {
        ByteArrayClassLoader byteArrayClassLoader = cache.getByteArrayClassLoader();
        Map<Class< ? >, ClassFieldInspector> inspectors = cache.getInspectors();
        
        try {
            // otherwise, bytecode generate a specific extractor
            ClassFieldInspector inspector = inspectors.get( clazz );
            if ( inspector == null ) {
                inspector = new ClassFieldInspector( clazz );
                inspectors.put( clazz,
                                inspector );
            }
            Method setterMethod = (Method) inspector.getSetterMethods().get( fieldName );
            Integer index = (Integer) inspector.getFieldNames().get( fieldName );
            if ( setterMethod == null && fieldName.length() > 1 && Character.isLowerCase( fieldName.charAt( 0 ) ) && Character.isUpperCase( fieldName.charAt(1) ) ) {
                // it might be that odd case of javabeans naming conventions that does not use lower case first letters if the second is uppercase
                String altFieldName = Character.toUpperCase( fieldName.charAt( 0 ) ) + fieldName.substring( 1 );
                setterMethod = (Method) inspector.getSetterMethods().get( altFieldName );
                index = (Integer) inspector.getFieldNames().get( altFieldName );
            }
            if ( setterMethod != null ) {
                final Class< ? > fieldType = setterMethod.getParameterTypes()[0];
                final String className = ClassFieldAccessorFactory.BASE_PACKAGE + "/" + Type.getInternalName( clazz ) + Math.abs( System.identityHashCode( clazz ) ) + "$" + setterMethod.getName();

                // generating byte array to create target class
                final byte[] bytes = dumpWriter( clazz,
                                                 className,
                                                 setterMethod,
                                                 fieldType,
                                                 clazz.isInterface() );
                // use bytes to get a class 

                final Class< ? > newClass = byteArrayClassLoader.defineClass( className.replace( '/',
                                                                                                 '.' ),
                                                                              bytes,
                                                                              PROTECTION_DOMAIN );
                // instantiating target class
                final ValueType valueType = ValueType.determineValueType( fieldType );
                final Object[] params = {index, fieldType, valueType};
                return (BaseClassFieldWriter) newClass.getConstructors()[0].newInstance( params );
            } else {
                if ( inspector.getFieldNames().containsKey( fieldName ) ) {
                    if ( inspector.getGetterMethods().get( fieldName ) != null ) {
                        // field without setter
                        return null;
                    } else {
                        // public field
                        return null;
                    }

                } else {
                    throw new RuntimeException( "Field/method '" + fieldName + "' not found for class '" + clazz.getName() + "'" );
                }
            }
        } catch ( final RuntimeException e ) {
            throw e;
        } catch ( final Exception e ) {
            throw new RuntimeException( e );
        }
    }

    private byte[] dumpReader(final Class< ? > originalClass,
                              final String className,
                              final Method getterMethod,
                              final Class< ? > fieldType,
                              final boolean isInterface) throws Exception {

        final Class< ? > superClass = getReaderSuperClassFor( fieldType );
        final ClassWriter cw = buildClassHeader( superClass, className );

        //        buildConstructor( superClass,
        //                          className,
        //                          cw );

        build3ArgConstructor( superClass,
                              className,
                              cw );

        buildGetMethod( originalClass,
                        className,
                        superClass,
                        getterMethod,
                        cw );

        cw.visitEnd();

        return cw.toByteArray();
    }

    private byte[] dumpWriter(final Class< ? > originalClass,
                              final String className,
                              final Method getterMethod,
                              final Class< ? > fieldType,
                              final boolean isInterface) throws Exception {


        final Class< ? > superClass = getWriterSuperClassFor( fieldType );
        final ClassWriter cw = buildClassHeader( superClass, className );

        build3ArgConstructor( superClass,
                              className,
                              cw );

        buildSetMethod( originalClass,
                        className,
                        superClass,
                        getterMethod,
                        fieldType,
                        cw );

        cw.visitEnd();

        return cw.toByteArray();
    }

    /**
     * Builds the class header
     */
    protected ClassWriter buildClassHeader(Class< ? > superClass, String className) {

        ClassWriter cw = createClassWriter( superClass.getClassLoader(),
                                            Opcodes.ACC_PUBLIC + Opcodes.ACC_SUPER,
                                            className,
                                            null,
                                            Type.getInternalName( superClass ),
                                            null );

        cw.visitSource( null,
                        null );

        return cw;
    }

    /**
     * Creates a constructor for the field extractor receiving
     * the index, field type and value type
     */
    private void build3ArgConstructor(final Class< ? > superClazz,
                                      final String className,
                                      final ClassWriter cw) {
        MethodVisitor mv;
        {
            mv = cw.visitMethod( Opcodes.ACC_PUBLIC,
                                 "<init>",
                                 Type.getMethodDescriptor( Type.VOID_TYPE,
                                                           new Type[]{Type.getType( int.class ), Type.getType( Class.class ), Type.getType( ValueType.class )} ),
                                 null,
                                 null );
            mv.visitCode();
            final Label l0 = new Label();
            mv.visitLabel( l0 );
            mv.visitVarInsn( Opcodes.ALOAD,
                             0 );
            mv.visitVarInsn( Opcodes.ILOAD,
                             1 );
            mv.visitVarInsn( Opcodes.ALOAD,
                             2 );
            mv.visitVarInsn( Opcodes.ALOAD,
                             3 );
            mv.visitMethodInsn( Opcodes.INVOKESPECIAL,
                                Type.getInternalName( superClazz ),
                                "<init>",
                                Type.getMethodDescriptor( Type.VOID_TYPE,
                                                          new Type[]{Type.getType( int.class ), Type.getType( Class.class ), Type.getType( ValueType.class )} ) );
            final Label l1 = new Label();
            mv.visitLabel( l1 );
            mv.visitInsn( Opcodes.RETURN );
            final Label l2 = new Label();
            mv.visitLabel( l2 );
            mv.visitLocalVariable( "this",
                                   "L" + className + ";",
                                   null,
                                   l0,
                                   l2,
                                   0 );
            mv.visitLocalVariable( "index",
                                   Type.getDescriptor( int.class ),
                                   null,
                                   l0,
                                   l2,
                                   1 );
            mv.visitLocalVariable( "fieldType",
                                   Type.getDescriptor( Class.class ),
                                   null,
                                   l0,
                                   l2,
                                   2 );
            mv.visitLocalVariable( "valueType",
                                   Type.getDescriptor( ValueType.class ),
                                   null,
                                   l0,
                                   l2,
                                   3 );
            mv.visitMaxs( 0,
                          0 );
            mv.visitEnd();
        }
    }

    /**
     * Creates the proxy reader method for the given method
     */
    protected void buildGetMethod(final Class< ? > originalClass,
                                  final String className,
                                  final Class< ? > superClass,
                                  final Method getterMethod,
                                  final ClassWriter cw) {

        final Class< ? > fieldType = getterMethod.getReturnType();
        Method overridingMethod;
        try {
            overridingMethod = superClass.getMethod( getOverridingGetMethodName( fieldType ),
                                                     new Class[]{InternalWorkingMemory.class, Object.class} );
        } catch ( final Exception e ) {
            throw new RuntimeException( "This is a bug. Please report back to JBoss Rules team.",
                                        e );
        }
        final MethodVisitor mv = cw.visitMethod( Opcodes.ACC_PUBLIC,
                                                 overridingMethod.getName(),
                                                 Type.getMethodDescriptor( overridingMethod ),
                                                 null,
                                                 null );

        mv.visitCode();

        final Label l0 = new Label();
        mv.visitLabel( l0 );
        mv.visitVarInsn( Opcodes.ALOAD,
                         2 );
        mv.visitTypeInsn( Opcodes.CHECKCAST,
                          Type.getInternalName( originalClass ) );

        if ( originalClass.isInterface() ) {
            mv.visitMethodInsn( Opcodes.INVOKEINTERFACE,
                                Type.getInternalName( originalClass ),
                                getterMethod.getName(),
                                Type.getMethodDescriptor( getterMethod ) );
        } else {
            mv.visitMethodInsn( Opcodes.INVOKEVIRTUAL,
                                Type.getInternalName( originalClass ),
                                getterMethod.getName(),
                                Type.getMethodDescriptor( getterMethod ) );
        }
        mv.visitInsn( Type.getType( fieldType ).getOpcode( Opcodes.IRETURN ) );
        final Label l1 = new Label();
        mv.visitLabel( l1 );
        mv.visitLocalVariable( "this",
                               "L" + className + ";",
                               null,
                               l0,
                               l1,
                               0 );
        mv.visitLocalVariable( "workingMemory",
                               Type.getDescriptor( InternalWorkingMemory.class ),
                               null,
                               l0,
                               l1,
                               1 );
        mv.visitLocalVariable( "object",
                               Type.getDescriptor( Object.class ),
                               null,
                               l0,
                               l1,
                               2 );
        mv.visitMaxs( 0,
                      0 );
        mv.visitEnd();
    }

    /**
     * Creates the set method for the given field definition
     */
    protected void buildSetMethod(final Class< ? > originalClass,
                                  final String className,
                                  final Class< ? > superClass,
                                  final Method setterMethod,
                                  final Class< ? > fieldType,
                                  final ClassWriter cw) {
        MethodVisitor mv;
        // set method
        {
            Method overridingMethod;
            try {
                overridingMethod = superClass.getMethod( getOverridingSetMethodName( fieldType ),
                                                         new Class[]{Object.class, fieldType.isPrimitive() ? fieldType : Object.class} );
            } catch ( final Exception e ) {
                throw new RuntimeException( "This is a bug. Please report back to JBoss Rules team.",
                                            e );
            }

            mv = cw.visitMethod( Opcodes.ACC_PUBLIC,
                                 overridingMethod.getName(),
                                 Type.getMethodDescriptor( overridingMethod ),
                                 null,
                                 null );

            mv.visitCode();
            final Label l0 = new Label();
            mv.visitLabel( l0 );

            mv.visitVarInsn( Opcodes.ALOAD,
                             1 );
            mv.visitTypeInsn( Opcodes.CHECKCAST,
                              Type.getInternalName( originalClass ) );

            mv.visitVarInsn( Type.getType( fieldType ).getOpcode( Opcodes.ILOAD ),
                             2 );

            if ( !fieldType.isPrimitive() ) {
                mv.visitTypeInsn( Opcodes.CHECKCAST,
                                  Type.getInternalName( fieldType ) );
            }

            if ( originalClass.isInterface() ) {
                mv.visitMethodInsn( Opcodes.INVOKEINTERFACE,
                                    Type.getInternalName( originalClass ),
                                    setterMethod.getName(),
                                    Type.getMethodDescriptor( setterMethod ) );
            } else {
                mv.visitMethodInsn( Opcodes.INVOKEVIRTUAL,
                                    Type.getInternalName( originalClass ),
                                    setterMethod.getName(),
                                    Type.getMethodDescriptor( setterMethod ) );
            }

            mv.visitInsn( Opcodes.RETURN );

            final Label l1 = new Label();
            mv.visitLabel( l1 );
            mv.visitLocalVariable( "this",
                                   "L" + className + ";",
                                   null,
                                   l0,
                                   l1,
                                   0 );
            mv.visitLocalVariable( "bean",
                                   Type.getDescriptor( Object.class ),
                                   null,
                                   l0,
                                   l1,
                                   1 );
            mv.visitLocalVariable( "value",
                                   Type.getDescriptor( fieldType ),
                                   null,
                                   l0,
                                   l1,
                                   2 );
            mv.visitMaxs( 0,
                          0 );
            mv.visitEnd();

        }
    }

    private String getOverridingGetMethodName(final Class< ? > fieldType) {
        String ret = null;
        if ( fieldType.isPrimitive() ) {
            if ( fieldType == char.class ) {
                ret = "getCharValue";
            } else if ( fieldType == byte.class ) {
                ret = "getByteValue";
            } else if ( fieldType == short.class ) {
                ret = "getShortValue";
            } else if ( fieldType == int.class ) {
                ret = "getIntValue";
            } else if ( fieldType == long.class ) {
                ret = "getLongValue";
            } else if ( fieldType == float.class ) {
                ret = "getFloatValue";
            } else if ( fieldType == double.class ) {
                ret = "getDoubleValue";
            } else if ( fieldType == boolean.class ) {
                ret = "getBooleanValue";
            }
        } else {
            ret = "getValue";
        }
        return ret;
    }

    private String getOverridingSetMethodName(final Class< ? > fieldType) {
        String ret = null;
        if ( fieldType.isPrimitive() ) {
            if ( fieldType == char.class ) {
                ret = "setCharValue";
            } else if ( fieldType == byte.class ) {
                ret = "setByteValue";
            } else if ( fieldType == short.class ) {
                ret = "setShortValue";
            } else if ( fieldType == int.class ) {
                ret = "setIntValue";
            } else if ( fieldType == long.class ) {
                ret = "setLongValue";
            } else if ( fieldType == float.class ) {
                ret = "setFloatValue";
            } else if ( fieldType == double.class ) {
                ret = "setDoubleValue";
            } else if ( fieldType == boolean.class ) {
                ret = "setBooleanValue";
            }
        } else {
            ret = "setValue";
        }
        return ret;
    }

    /**
     * Returns the appropriate Base class field extractor class
     * for the given fieldType
     * 
     * @param fieldType
     * @return
     */
    private Class< ? > getReaderSuperClassFor(final Class< ? > fieldType) {
        Class< ? > ret = null;
        if ( fieldType.isPrimitive() ) {
            if ( fieldType == char.class ) {
                ret = BaseCharClassFieldReader.class;
            } else if ( fieldType == byte.class ) {
                ret = BaseByteClassFieldReader.class;
            } else if ( fieldType == short.class ) {
                ret = BaseShortClassFieldReader.class;
            } else if ( fieldType == int.class ) {
                ret = BaseIntClassFieldReader.class;
            } else if ( fieldType == long.class ) {
                ret = BaseLongClassFieldReader.class;
            } else if ( fieldType == float.class ) {
                ret = BaseFloatClassFieldReader.class;
            } else if ( fieldType == double.class ) {
                ret = BaseDoubleClassFieldReader.class;
            } else if ( fieldType == boolean.class ) {
                ret = BaseBooleanClassFieldReader.class;
            }
        } else if ( Number.class.isAssignableFrom( fieldType ) ) {
            ret = BaseNumberClassFieldReader.class;
        } else if ( Date.class.isAssignableFrom( fieldType ) ) {
            ret = BaseDateClassFieldReader.class;
        } else {
            ret = BaseObjectClassFieldReader.class;
        }
        return ret;
    }

    /**
     * Returns the appropriate Base class field extractor class
     * for the given fieldType
     * 
     * @param fieldType
     * @return
     */
    private Class< ? > getWriterSuperClassFor(final Class< ? > fieldType) {
        Class< ? > ret = null;
        if ( fieldType.isPrimitive() ) {
            if ( fieldType == char.class ) {
                ret = BaseCharClassFieldWriter.class;
            } else if ( fieldType == byte.class ) {
                ret = BaseByteClassFieldWriter.class;
            } else if ( fieldType == short.class ) {
                ret = BaseShortClassFieldWriter.class;
            } else if ( fieldType == int.class ) {
                ret = BaseIntClassFieldWriter.class;
            } else if ( fieldType == long.class ) {
                ret = BaseLongClassFieldWriter.class;
            } else if ( fieldType == float.class ) {
                ret = BaseFloatClassFieldWriter.class;
            } else if ( fieldType == double.class ) {
                ret = BaseDoubleClassFieldWriter.class;
            } else if ( fieldType == boolean.class ) {
                ret = BaseBooleanClassFieldWriter.class;
            }
        } else {
            ret = BaseObjectClassFieldWriter.class;
        }
        return ret;
    }

}


File: drools-core/src/main/java/org/drools/core/common/ProjectClassLoader.java
package org.drools.core.common;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Method;
import java.net.URL;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.util.concurrent.ConcurrentHashMap;

import static org.drools.core.util.ClassUtils.convertClassToResourcePath;

public class ProjectClassLoader extends ClassLoader {

    private static final boolean CACHE_NON_EXISTING_CLASSES = true;
    private static final ClassNotFoundException dummyCFNE = CACHE_NON_EXISTING_CLASSES ?
                                                            new ClassNotFoundException("This is just a cached Exception. Disable non existing classes cache to see the actual one.") :
                                                            null;

    private static boolean isIBM_JVM = System.getProperty("java.vendor").toLowerCase().contains("ibm");

    private Map<String, byte[]> store;

    private Map<String, ClassBytecode> definedTypes;

    private final Set<String> nonExistingClasses = new HashSet<String>();

    private ClassLoader droolsClassLoader;

    private InternalTypesClassLoader typesClassLoader;

    private final Map<String, Class<?>> loadedClasses = new ConcurrentHashMap<String, Class<?>>();

    private final ResourceProvider resourceProvider;

    private ProjectClassLoader(ClassLoader parent, ResourceProvider resourceProvider) {
        super(parent);
        this.resourceProvider = resourceProvider;
    }

    public static class IBMClassLoader extends ProjectClassLoader {
        private final boolean parentImplemntsFindReosources;

        private static final Enumeration<URL> EMPTY_RESOURCE_ENUM = new Vector<URL>().elements();

        private IBMClassLoader(ClassLoader parent, ResourceProvider resourceProvider) {
            super(parent, resourceProvider);
            Method m = null;
            try {
                m = parent.getClass().getMethod("findResources", String.class);
            } catch (NoSuchMethodException e) { }
            parentImplemntsFindReosources = m != null && m.getDeclaringClass() == parent.getClass();
        }

        @Override
        protected Enumeration<URL> findResources(String name) throws IOException {
            // if the parent doesn't implemnt this method call getResources directly on it
            // see https://blogs.oracle.com/bhaktimehta/entry/ibm_jdk_and_classloader_getresources
            return parentImplemntsFindReosources ? EMPTY_RESOURCE_ENUM : getParent().getResources(name);
        }
    }

    private static ProjectClassLoader internalCreate(ClassLoader parent, ResourceProvider resourceProvider) {
        return isIBM_JVM ? new IBMClassLoader(parent, resourceProvider) : new ProjectClassLoader(parent, resourceProvider);
    }

    public static ClassLoader getClassLoader(final ClassLoader classLoader,
                                             final Class< ? > cls,
                                             final boolean enableCache) {
        ProjectClassLoader projectClassLoader = createProjectClassLoader(classLoader);
        if (cls != null) {
            projectClassLoader.setDroolsClassLoader(cls.getClassLoader());
        }
        return projectClassLoader;
    }

    public static ClassLoader findParentClassLoader() {
        ClassLoader parent = Thread.currentThread().getContextClassLoader();
        if (parent == null) {
            parent = ClassLoader.getSystemClassLoader();
        }
        if (parent == null) {
            parent = ProjectClassLoader.class.getClassLoader();
        }
        return parent;
    }


    public static ProjectClassLoader createProjectClassLoader() {
        return internalCreate(findParentClassLoader(), null);
    }

    public static ProjectClassLoader createProjectClassLoader(ClassLoader parent) {
        return createProjectClassLoader(parent, (ResourceProvider)null);
    }

    public static ProjectClassLoader createProjectClassLoader(ClassLoader parent, ResourceProvider resourceProvider) {
        if (parent == null) {
            return internalCreate(findParentClassLoader(), resourceProvider);
        }
        return parent instanceof ProjectClassLoader ? (ProjectClassLoader)parent : internalCreate(parent, resourceProvider);
    }

    public static ProjectClassLoader createProjectClassLoader(ClassLoader parent, Map<String, byte[]> store) {
        ProjectClassLoader projectClassLoader = createProjectClassLoader(parent);
        projectClassLoader.store = store;
        return projectClassLoader;
    }

    @Override
    protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
        Class<?> cls = loadedClasses.get(name);
        if (cls != null) {
            return cls;
        }
        synchronized (this) {
            try {
                cls = internalLoadClass(name, resolve);
            } catch (ClassNotFoundException e2) {
                cls = loadType(name, resolve);
            }
        }
        loadedClasses.put(name, cls);
        return cls;
    }

    private Class<?> internalLoadClass(String name, boolean resolve) throws ClassNotFoundException {
        if (CACHE_NON_EXISTING_CLASSES && nonExistingClasses.contains(name)) {
            throw dummyCFNE;
        }

        if (droolsClassLoader != null) {
            try {
                return Class.forName(name, resolve, droolsClassLoader);
            } catch (ClassNotFoundException e) { }
        }
        try {
            return super.loadClass(name, resolve);
        } catch (ClassNotFoundException e) {
            return Class.forName(name, resolve, getParent());
        }
    }

    private Class<?> loadType(String name, boolean resolve) throws ClassNotFoundException {
        ClassNotFoundException cnfe = null;
        if (typesClassLoader != null) {
            try {
                return typesClassLoader.loadType(name, resolve);
            } catch (ClassNotFoundException e) {
                cnfe = e;
            }
        }
        return tryDefineType(name, cnfe);
    }

    private Class<?> tryDefineType(String name, ClassNotFoundException cnfe) throws ClassNotFoundException {
        byte[] bytecode = getBytecode(convertClassToResourcePath(name));
        if (bytecode == null) {
            if (CACHE_NON_EXISTING_CLASSES) {
                nonExistingClasses.add(name);
            }
            throw cnfe != null ? cnfe : new ClassNotFoundException(name);
        }
        return defineType(name, bytecode);
    }

    private Class<?> defineType(String name, byte[] bytecode) {
        if (definedTypes == null) {
            definedTypes = new HashMap<String, ClassBytecode>();
        } else {
            ClassBytecode existingClass = definedTypes.get(name);
            if (existingClass != null && Arrays.equals(bytecode, existingClass.bytes)) {
                return existingClass.clazz;
            }
        }

        if (typesClassLoader == null) {
            typesClassLoader = new InternalTypesClassLoader(this);
        }
        Class<?> clazz = typesClassLoader.defineClass(name, bytecode);
        definedTypes.put(name, new ClassBytecode(clazz, bytecode));
        return clazz;
    }

    public Class<?> defineClass(String name, byte[] bytecode) {
        return defineClass(name, convertClassToResourcePath(name), bytecode);
    }

    public Class<?> defineClass(String name, String resourceName, byte[] bytecode) {
        storeClass(name, resourceName, bytecode);
        return defineType(name, bytecode);
    }

    public void undefineClass(String name) {
        String resourceName = convertClassToResourcePath(name);
        if (store.remove(resourceName) != null) {
            if (CACHE_NON_EXISTING_CLASSES) {
                nonExistingClasses.add(name);
            }
            typesClassLoader = null;
        }
    }

    public void storeClass(String name, byte[] bytecode) {
        storeClass(name, convertClassToResourcePath(name), bytecode);
    }

    public void storeClass(String name, String resourceName, byte[] bytecode) {
        if (store == null) {
            store = new HashMap<String, byte[]>();
        }
        store.put(resourceName, bytecode);
        if (CACHE_NON_EXISTING_CLASSES) {
            nonExistingClasses.remove(name);
        }
    }

    public boolean isClassInUse(String className) {
        return loadedClasses.containsKey(className);
    }

    @Override
    public InputStream getResourceAsStream(String name) {
        byte[] bytecode = getBytecode(name);
        if (bytecode != null) {
            return new ByteArrayInputStream( bytecode );
        }
        if (resourceProvider != null) {
            try {
                InputStream is = resourceProvider.getResourceAsStream(name);
                if (is != null) {
                    return is;
                }
            } catch (IOException e) { }
        }
        return super.getResourceAsStream(name);
    }

    @Override
    public URL getResource(String name) {
        if (droolsClassLoader != null) {
            URL resource = droolsClassLoader.getResource(name);
            if (resource != null) {
                return resource;
            }
        }
        if (resourceProvider != null) {
            URL resource = resourceProvider.getResource(name);
            if (resource != null) {
                return resource;
            }
        }
        return super.getResource(name);
    }

    @Override
    public Enumeration<URL> getResources(String name) throws IOException {
        Enumeration<URL> resources = super.getResources(name);
        if (resourceProvider != null) {
            URL providedResource = resourceProvider.getResource(name);
            if (resources != null) {
                return new ResourcesEnum(providedResource, resources);
            }
        }
        return resources;
    }

    private static class ResourcesEnum implements Enumeration<URL> {

        private URL providedResource;
        private final Enumeration<URL> resources;

        private ResourcesEnum(URL providedResource, Enumeration<URL> resources) {
            this.providedResource = providedResource;
            this.resources = resources;
        }

        @Override
        public boolean hasMoreElements() {
            return providedResource != null || resources.hasMoreElements();
        }

        @Override
        public URL nextElement() {
            if (providedResource != null) {
                URL result = providedResource;
                providedResource = null;
                return result;
            }
            return resources.nextElement();
        }
    }

    public byte[] getBytecode(String resourceName) {
        return store == null ? null : store.get(resourceName);
    }

    public Map<String, byte[]> getStore() {
        return store;
    }

    public void setDroolsClassLoader(ClassLoader droolsClassLoader) {
        if (getParent() != droolsClassLoader) {
            this.droolsClassLoader = droolsClassLoader;
            if (CACHE_NON_EXISTING_CLASSES) {
                nonExistingClasses.clear();
            }
        }
    }

    public void initFrom(ProjectClassLoader other) {
        if (other.store != null) {
            if (store == null) {
                store = new HashMap<String, byte[]>();
            }
            store.putAll(other.store);
        }
        nonExistingClasses.addAll(other.nonExistingClasses);
    }

    private static class InternalTypesClassLoader extends ClassLoader {

        private final ProjectClassLoader projectClassLoader;

        private InternalTypesClassLoader(ProjectClassLoader projectClassLoader) {
            super(projectClassLoader.getParent());
            this.projectClassLoader = projectClassLoader;
        }

        public Class<?> defineClass(String name, byte[] bytecode) {
            int lastDot = name.lastIndexOf( '.' );
            if (lastDot > 0) {
                String pkgName = name.substring( 0, lastDot );
                if (getPackage( pkgName ) == null) {
                    definePackage( pkgName, "", "", "", "", "", "", null );
                }
            }
            return defineClass(name, bytecode, 0, bytecode.length);
        }

        protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
            try {
                return loadType(name, resolve);
            } catch (ClassNotFoundException cnfe) {
                synchronized(projectClassLoader) {
                    try {
                        return projectClassLoader.internalLoadClass(name, resolve);
                    } catch (ClassNotFoundException cnfe2) {
                        return projectClassLoader.tryDefineType(name, cnfe);
                    }
                }
            }
        }

        private Class<?> loadType(String name, boolean resolve) throws ClassNotFoundException {
            return super.loadClass(name, resolve);
        }
    }

    public synchronized void reinitTypes() {
        typesClassLoader = null;
        nonExistingClasses.clear();
        loadedClasses.clear();
    }

    private static class ClassBytecode {
        private final Class<?> clazz;
        private final byte[] bytes;

        private ClassBytecode(Class<?> clazz, byte[] bytes) {
            this.clazz = clazz;
            this.bytes = bytes;
        }
    }
}


File: drools-core/src/main/java/org/drools/core/rule/JavaDialectRuntimeData.java
/*
 * Copyright 2005 JBoss Inc
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

package org.drools.core.rule;

import org.drools.core.common.ProjectClassLoader;
import org.drools.core.definitions.impl.KnowledgePackageImpl;
import org.drools.core.definitions.rule.impl.RuleImpl;
import org.drools.core.spi.Constraint;
import org.drools.core.spi.Wireable;
import org.drools.core.util.KeyStoreHelper;
import org.drools.core.util.StringUtils;
import org.kie.internal.concurrent.ExecutorProviderFactory;
import org.kie.internal.utils.FastClassLoader;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.Externalizable;
import java.io.IOException;
import java.io.InputStream;
import java.io.ObjectInput;
import java.io.ObjectInputStream;
import java.io.ObjectOutput;
import java.io.ObjectOutputStream;
import java.net.URL;
import java.security.AccessController;
import java.security.InvalidKeyException;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.PrivilegedAction;
import java.security.ProtectionDomain;
import java.security.SignatureException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.NoSuchElementException;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletionService;
import java.util.concurrent.ConcurrentSkipListSet;

import static org.drools.core.util.ClassUtils.convertClassToResourcePath;
import static org.drools.core.util.ClassUtils.convertResourceToClassName;

public class JavaDialectRuntimeData
                                   implements
                                   DialectRuntimeData,
                                   Externalizable {

    private static final long              serialVersionUID = 510l;

    private static final ProtectionDomain  PROTECTION_DOMAIN;

    private Map<String, Object>            invokerLookups;

    private Map<String, byte[]>            classLookups;

    private Map<String, byte[]>            store;

    private transient PackageClassLoader   classLoader;

    private transient ClassLoader          rootClassLoader;

    private boolean                        dirty;

    private List<String>                   wireList         = Collections.<String> emptyList();

    static {
        PROTECTION_DOMAIN = (ProtectionDomain) AccessController.doPrivileged( new PrivilegedAction() {

            public Object run() {
                return JavaDialectRuntimeData.class.getProtectionDomain();
            }
        } );
    }

    public JavaDialectRuntimeData() {
        this.invokerLookups = new HashMap<String, Object>();
		this.classLookups = new HashMap<String,byte[]>();
		this.store = new HashMap<String, byte[]>();        
        this.dirty = false;
    }

    /**
     * Handles the write serialization of the PackageCompilationData. Patterns in Rules may reference generated data which cannot be serialized by
     * default methods. The PackageCompilationData holds a reference to the generated bytecode. The generated bytecode must be restored before any Rules.
     */
    public void writeExternal( ObjectOutput stream ) throws IOException {
        KeyStoreHelper helper = new KeyStoreHelper();

        stream.writeBoolean( helper.isSigned() );
        if (helper.isSigned()) {
            stream.writeObject( helper.getPvtKeyAlias() );
        }

        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        ObjectOutput out = new ObjectOutputStream( bos );

        out.writeInt( this.store.size() );
        for (Entry<String, byte[]> stringEntry : this.store.entrySet()) {
            Entry entry = (Entry) stringEntry;
            out.writeObject(entry.getKey());
            out.writeObject(entry.getValue());
        }
        out.flush();
        out.close();
        byte[] buff = bos.toByteArray();
        stream.writeObject( buff );
        if (helper.isSigned()) {
            sign( stream,
                  helper,
                  buff );
        }

        stream.writeInt( this.invokerLookups.size() );
        for (Entry<String, Object> stringObjectEntry : this.invokerLookups.entrySet()) {
            Entry entry = (Entry) stringObjectEntry;
            stream.writeObject(entry.getKey());
            stream.writeObject(entry.getValue());
        }

        stream.writeInt( this.classLookups.size() );
        for (Entry<String, byte[]> entry : this.classLookups.entrySet()) {
            stream.writeObject( entry.getKey() );
            stream.writeObject( entry.getValue() );
        }

    }

    private void sign( final ObjectOutput stream,
            KeyStoreHelper helper,
            byte[] buff ) {
        try {
            stream.writeObject( helper.signDataWithPrivateKey( buff ) );
        } catch (Exception e) {
            throw new RuntimeException( "Error signing object store: " + e.getMessage(),
                                        e );
        }
    }

    /**
     * Handles the read serialization of the PackageCompilationData. Patterns in Rules may reference generated data which cannot be serialized by
     * default methods. The PackageCompilationData holds a reference to the generated bytecode; which must be restored before any Rules.
     * A custom ObjectInputStream, able to resolve classes against the bytecode, is used to restore the Rules.
     */
    public void readExternal( ObjectInput stream ) throws IOException,
            ClassNotFoundException {
        KeyStoreHelper helper = new KeyStoreHelper();
        boolean signed = stream.readBoolean();
        if (helper.isSigned() != signed) {
            throw new RuntimeException( "This environment is configured to work with " +
                                        ( helper.isSigned() ? "signed" : "unsigned" ) +
                                        " serialized objects, but the given object is " +
                                        ( signed ? "signed" : "unsigned" ) + ". Deserialization aborted." );
        }
        String pubKeyAlias = null;
        if (signed) {
            pubKeyAlias = (String) stream.readObject();
            if (helper.getPubKeyStore() == null) {
                throw new RuntimeException( "The package was serialized with a signature. Please configure a public keystore with the public key to check the signature. Deserialization aborted." );
            }
        }

        // Return the object stored as a byte[]
        byte[] bytes = (byte[]) stream.readObject();
        if (signed) {
            checkSignature( stream,
                            helper,
                            bytes,
                            pubKeyAlias );
        }

        ObjectInputStream in = new ObjectInputStream( new ByteArrayInputStream( bytes ) );
        for (int i = 0, length = in.readInt(); i < length; i++) {
            this.store.put( (String) in.readObject(),
                            (byte[]) in.readObject() );
        }
        in.close();

        for (int i = 0, length = stream.readInt(); i < length; i++) {
            this.invokerLookups.put( (String) stream.readObject(),
                                     stream.readObject() );
        }

        for (int i = 0, length = stream.readInt(); i < length; i++) {
            this.classLookups.put( (String) stream.readObject(),
                                   (byte[]) stream.readObject() );
        }

        // mark it as dirty, so that it reloads everything.
        this.dirty = true;
    }

    private void checkSignature( final ObjectInput stream,
            final KeyStoreHelper helper,
            final byte[] bytes,
            final String pubKeyAlias ) throws ClassNotFoundException,
            IOException {
        byte[] signature = (byte[]) stream.readObject();
        try {
            if (!helper.checkDataWithPublicKey( pubKeyAlias,
                                                bytes,
                                                signature )) {
                throw new RuntimeException( "Signature does not match serialized package. This is a security violation. Deserialisation aborted." );
            }
        } catch (InvalidKeyException e) {
            throw new RuntimeException( "Invalid key checking signature: " + e.getMessage(),
                                        e );
        } catch (KeyStoreException e) {
            throw new RuntimeException( "Error accessing Key Store: " + e.getMessage(),
                                        e );
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException( "No algorithm available: " + e.getMessage(),
                                        e );
        } catch (SignatureException e) {
            throw new RuntimeException( "Signature Exception: " + e.getMessage(),
                                        e );
        }
    }

    public void onAdd( DialectRuntimeRegistry registry,
                       ClassLoader rootClassLoader ) {
        this.rootClassLoader = rootClassLoader;
        this.classLoader = new PackageClassLoader( this,
                                                   this.rootClassLoader );
    }

    public void onRemove() {

    }

    public void onBeforeExecute() {
        if ( isDirty() ) {
            reload();
        } else if (!this.wireList.isEmpty()) {
            try {
                // wire all remaining resources
                int wireListSize = this.wireList.size();
                if (wireListSize < 100) {
                    wireAll(classLoader, getInvokers(), this.wireList);
                } else {
                    wireInParallel(wireListSize);
                }
            } catch (Exception e) {
                throw new RuntimeException( "Unable to wire up JavaDialect", e );
            }
        }

        this.wireList.clear();
    }

    private void wireInParallel(int wireListSize) throws Exception {
        final int parallelThread = Runtime.getRuntime().availableProcessors();
        CompletionService<Boolean> ecs = ExecutorProviderFactory.getExecutorProvider().getCompletionService();

        int size = wireListSize / parallelThread;
        for (int i = 1; i <= parallelThread; i++) {
            List<String> subList = wireList.subList((i-1) * size, i == parallelThread ? wireListSize : i * size);
            ecs.submit(new WiringExecutor(classLoader, getInvokers(), subList));
        }
        for (int i = 1; i <= parallelThread; i++) {
            ecs.take().get();
        }
    }

    private static void wireAll(PackageClassLoader classLoader, Map<String, Object> invokerLookups, List<String> wireList) throws ClassNotFoundException, InstantiationException, IllegalAccessException {
        for (String resourceName : wireList) {
            wire( classLoader, invokerLookups, convertResourceToClassName( resourceName ) );
        }
    }

    private static class WiringExecutor implements Callable<Boolean> {
        private final PackageClassLoader classLoader;
        private final Map<String, Object> invokerLookups;
        private final List<String> wireList;

        private WiringExecutor(PackageClassLoader classLoader, Map<String, Object> invokerLookups, List<String> wireList) {
            this.classLoader = classLoader;
            this.invokerLookups = invokerLookups;
            this.wireList = wireList;
        }

        public Boolean call() throws Exception {
            wireAll(classLoader, invokerLookups, wireList);
            return true;
        }
    }

    public DialectRuntimeData clone( DialectRuntimeRegistry registry,
                                     ClassLoader rootClassLoader ) {
        return clone( registry, rootClassLoader, false );
    }

    public DialectRuntimeData clone( DialectRuntimeRegistry registry,
                                     ClassLoader rootClassLoader,
                                     boolean excludeClasses ) {
        DialectRuntimeData cloneOne = new JavaDialectRuntimeData();
        cloneOne.merge( registry,
                        this,
                        excludeClasses );
        cloneOne.onAdd( registry,
                        rootClassLoader );
        return cloneOne;
    }

    public void merge( DialectRuntimeRegistry registry,
                DialectRuntimeData newData ) {
        // false for backward compatibility, should probably be true by default
        merge(registry, newData, false);
    }

    public void merge( DialectRuntimeRegistry registry, DialectRuntimeData newData, boolean excludeClasses ) {
        JavaDialectRuntimeData newJavaData = (JavaDialectRuntimeData) newData;

        // First update the binary files
        // @todo: this probably has issues if you add classes in the incorrect order - functions, rules, invokers.
        for (String resourceName : newJavaData.list()) {
            if ( ! excludeClasses || ! newJavaData.getClassDefinitions().containsKey( resourceName ) ) {
                write( resourceName,
                       newJavaData.read( resourceName ) );
            }
            //            // no need to wire, as we already know this is done in a merge
            //            if ( getStore().put( resourceName,
            //                                 newJavaData.read( resourceName ) ) != null ) {
            //                // we are updating an existing class so reload();
            //                this.dirty = true;
            //            }
            //            if ( this.dirty == false ) {
            //                // only build up the wireList if we aren't going to reload
            //                this.wireList.add( resourceName );
            //            }
        }

        //        if ( this.dirty ) {
        //            // no need to keep wireList if we are going to reload;
        //            this.wireList.clear();
        //        }

        // Add invokers
        putAllInvokers( newJavaData.getInvokers() );

        if ( ! excludeClasses ) {
            putAllClassDefinitions( newJavaData.getClassDefinitions() );
        }

    }

    public boolean isDirty() {
        return this.dirty;
    }

    public void setDirty( boolean dirty ) {
        this.dirty = dirty;
    }

    public Map<String, byte[]> getStore() {
        if (store == null) {
            store = new HashMap<String, byte[]>();
        }
        return store;
    }

    public byte[] getBytecode(String resourceName) {
        byte[] bytecode = null;
        if (store != null) {
            bytecode = store.get(resourceName);
        }
        if (bytecode == null && rootClassLoader instanceof ProjectClassLoader) {
            bytecode = ((ProjectClassLoader)rootClassLoader).getBytecode(resourceName);
        }
        return bytecode;
    }

    public ClassLoader getClassLoader() {
        return this.classLoader;
    }

    public ClassLoader getRootClassLoader() {
        return rootClassLoader;
    }

    public void removeRule( KnowledgePackageImpl pkg,
                            RuleImpl rule ) {

        if (!( rule instanceof QueryImpl)) {
            // Query's don't have a consequence, so skip those
            final String consequenceName = rule.getConsequence().getClass().getName();

            // check for compiled code and remove if present.
            if (remove( consequenceName )) {
                removeClasses( rule.getLhs() );

                // Now remove the rule class - the name is a subset of the consequence name
                String sufix = StringUtils.ucFirst( rule.getConsequence().getName() ) + "ConsequenceInvoker";
                remove( consequenceName.substring( 0,
                                                   consequenceName.indexOf( sufix ) ) );
            }
        }
    }

    public void removeFunction( KnowledgePackageImpl pkg, Function function ) {
        remove( pkg.getName() + "." + StringUtils.ucFirst( function.getName() ) );
    }

    private void removeClasses( final ConditionalElement ce ) {
        if (ce instanceof GroupElement) {
            final GroupElement group = (GroupElement) ce;
            for (final Object object : group.getChildren()) {
                if (object instanceof ConditionalElement) {
                    removeClasses((ConditionalElement) object);
                } else if (object instanceof Pattern) {
                    removeClasses((Pattern) object);
                }
            }
        } else if (ce instanceof EvalCondition) {
            remove( ( (EvalCondition) ce ).getEvalExpression().getClass().getName() );
        }
    }

    private void removeClasses( final Pattern pattern ) {
        for (final Constraint object : pattern.getConstraints()) {
            if (object instanceof PredicateConstraint) {
                remove(((PredicateConstraint) object).getPredicateExpression().getClass().getName());
            }
        }
    }

    public byte[] read( final String resourceName ) {
        byte[] bytes = null;

        if (!getStore().isEmpty()) {
            bytes = getStore().get( resourceName );
        }
        return bytes;
    }

    public void write( String resourceName, byte[] clazzData ) {
        if (getStore().put( resourceName,
                            clazzData ) != null) {
            this.dirty = true;

            if (!this.wireList.isEmpty()) {
                this.wireList.clear();
            }
        } else if (!this.dirty) {
            try {
                if (this.wireList == Collections.<String> emptyList()) {
                    this.wireList = new ArrayList<String>();
                }
                this.wireList.add( resourceName );
            } catch (final Exception e) {
                e.printStackTrace();
                throw new RuntimeException( e );
            }
        }
    }

    public void wire( final String className ) throws ClassNotFoundException, InstantiationException, IllegalAccessException {
        wire(className, getInvokers().get(className));
    }

    private static void wire( PackageClassLoader classLoader, Map<String, Object> invokerLookups, String className ) throws ClassNotFoundException, InstantiationException, IllegalAccessException {
        wire( classLoader, className, invokerLookups.get( className ) );
    }

    public void wire( final String className, final Object invoker ) throws ClassNotFoundException, InstantiationException, IllegalAccessException {
        wire( classLoader, className, invoker );
    }

    private static void wire( PackageClassLoader classLoader, String className, Object invoker ) throws ClassNotFoundException, InstantiationException, IllegalAccessException {
        final Class clazz = classLoader.loadClass( className );

        if (clazz != null) {
            if (invoker instanceof Wireable) {
                ( (Wireable) invoker ).wire( clazz.newInstance() );
            }
        } else {
            throw new ClassNotFoundException( className );
        }
    }

    public boolean remove( final String resourceName ) {
        getInvokers().remove( resourceName );
        if (getStore().remove( convertClassToResourcePath( resourceName ) ) != null) {
            this.wireList.remove( resourceName );
            // we need to make sure the class is removed from the classLoader
            // reload();
            this.dirty = true;
            return true;
        }
        return false;
    }

    public String[] list() {
        String[] names = new String[getStore().size()];
        int i = 0;

        for (String string : getStore().keySet()) {
            names[i++] = string;
        }
        return names;
    }

    /**
     * This class drops the classLoader and reloads it. During this process  it must re-wire all the invokeables.
     */
    public void reload() {
        // drops the classLoader and adds a new one
        this.classLoader = new PackageClassLoader( this,
                                                   this.rootClassLoader );

        // Wire up invokers
        try {
            for (final Object object : getInvokers().entrySet()) {
                Entry entry = (Entry) object;
                wire( (String) entry.getKey(),
                      entry.getValue() );
            }
        } catch (final ClassNotFoundException e) {
            throw new RuntimeException( e );
        } catch (final InstantiationError e) {
            throw new RuntimeException( e );
        } catch (final IllegalAccessException e) {
            throw new RuntimeException( e );
        } catch (final InstantiationException e) {
            throw new RuntimeException( e );
        }

        this.dirty = false;
    }

    public void clear() {
        getStore().clear();
        getInvokers().clear();
        reload();
    }

    public String toString() {
        return this.getClass().getName() + getStore().toString();
    }

    public void putInvoker( final String className,
            final Object invoker ) {
        getInvokers().put(className,
                          invoker);
    }

    public void putAllInvokers( final Map<String, Object> invokers ) {
        getInvokers().putAll( invokers );

    }

    public Map<String, Object> getInvokers() {
        if (this.invokerLookups == null) {
            this.invokerLookups = new HashMap<String, Object>();
        }
        return this.invokerLookups;
    }

    public void removeInvoker( final String className ) {
        getInvokers().remove(className);
    }



    public void putClassDefinition( final String className,
                                    final byte[] classDef ) {
        getClassDefinitions().put( className,
                                   classDef );
    }

    public void putAllClassDefinitions( final Map classDefinitions ) {
        getClassDefinitions().putAll(classDefinitions);
    }

    public Map<String, byte[]> getClassDefinitions() {
        if (this.classLookups == null) {
            this.classLookups = new HashMap<String, byte[]>();
        }
        return this.classLookups;
    }

    public byte[] getClassDefinition( String className ) {
        if (this.classLookups == null) {
            this.classLookups = new HashMap<String, byte[]>();
        }
        byte[] classDef = this.classLookups.get( className );
        if (classDef == null && rootClassLoader instanceof ProjectClassLoader) {
            classDef = ((ProjectClassLoader)rootClassLoader).getBytecode(className);
            classLookups.put( className, classDef );
        }
        return classDef;
    }

    public void removeClassDefinition( final String className ) {
        getClassDefinitions().remove( className );
    }

    /**
     * This is an Internal Drools Class
     */
    public static class PackageClassLoader extends ClassLoader implements FastClassLoader {

        protected JavaDialectRuntimeData store;

        private Set<String> existingPackages = new ConcurrentSkipListSet<String>();
        
        public PackageClassLoader( JavaDialectRuntimeData store,
                                   ClassLoader rootClassLoader ) {
            super( rootClassLoader );
            this.store = store;
        }

        public Class<?> loadClass( final String name,
                                   final boolean resolve ) throws ClassNotFoundException {
            Class<?> cls = fastFindClass( name );

            if (cls == null) {
                ClassLoader parent = getParent();
                cls = parent.loadClass( name );
            }

            if (cls == null) {
                throw new ClassNotFoundException( "Unable to load class: " + name );
            }

            return cls;
        }

        public Class<?> fastFindClass( final String name ) {
            Class<?> cls = findLoadedClass( name );

            if (cls == null) {
                final byte[] clazzBytes = this.store.read( convertClassToResourcePath( name ) );
                if (clazzBytes != null) {
                    String pkgName = name.substring( 0,
                                                     name.lastIndexOf( '.' ) );

                    if (!existingPackages.contains( pkgName )) {
                        synchronized (this) {
                            if (getPackage( pkgName ) == null) {
                                definePackage( pkgName,
                                               "", "", "", "", "", "",
                                               null );
                            }
                            existingPackages.add( pkgName );
                        }
                    }

                    cls = defineClass( name,
                                       clazzBytes,
                                       0,
                                       clazzBytes.length,
                                       PROTECTION_DOMAIN );
                }

                if (cls != null) {
                    resolveClass( cls );
                }
            }

            return cls;
        }

        public InputStream getResourceAsStream( final String name ) {
            final byte[] clsBytes = this.store.read( name );
            if (clsBytes != null) {
                return new ByteArrayInputStream( clsBytes );
            }
            return null;
        }

        public URL getResource( String name ) {
            return null;
        }

        public Enumeration<URL> getResources( String name ) throws IOException {
            return new Enumeration<URL>() {

                public boolean hasMoreElements() {
                    return false;
                }

                public URL nextElement() {
                    throw new NoSuchElementException();
                }
            };
        }

    }
}


File: drools-core/src/main/java/org/drools/core/rule/builder/dialect/asm/ClassGenerator.java
package org.drools.core.rule.builder.dialect.asm;

import org.drools.core.base.TypeResolver;
import org.mvel2.asm.ClassWriter;
import org.mvel2.asm.MethodVisitor;
import org.mvel2.asm.Type;

import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static java.lang.reflect.Modifier.isAbstract;
import static org.drools.core.util.ClassUtils.convertFromPrimitiveType;
import static org.drools.core.util.ClassUtils.convertPrimitiveNameToType;
import static org.drools.core.util.ClassUtils.convertToPrimitiveType;
import static org.mvel2.asm.Opcodes.AASTORE;
import static org.mvel2.asm.Opcodes.ACC_PUBLIC;
import static org.mvel2.asm.Opcodes.ACC_STATIC;
import static org.mvel2.asm.Opcodes.ACC_SUPER;
import static org.mvel2.asm.Opcodes.ACONST_NULL;
import static org.mvel2.asm.Opcodes.ALOAD;
import static org.mvel2.asm.Opcodes.ANEWARRAY;
import static org.mvel2.asm.Opcodes.ARETURN;
import static org.mvel2.asm.Opcodes.BIPUSH;
import static org.mvel2.asm.Opcodes.CHECKCAST;
import static org.mvel2.asm.Opcodes.D2F;
import static org.mvel2.asm.Opcodes.D2I;
import static org.mvel2.asm.Opcodes.D2L;
import static org.mvel2.asm.Opcodes.DUP;
import static org.mvel2.asm.Opcodes.F2D;
import static org.mvel2.asm.Opcodes.F2I;
import static org.mvel2.asm.Opcodes.F2L;
import static org.mvel2.asm.Opcodes.GETFIELD;
import static org.mvel2.asm.Opcodes.GETSTATIC;
import static org.mvel2.asm.Opcodes.I2B;
import static org.mvel2.asm.Opcodes.I2C;
import static org.mvel2.asm.Opcodes.I2D;
import static org.mvel2.asm.Opcodes.I2F;
import static org.mvel2.asm.Opcodes.I2L;
import static org.mvel2.asm.Opcodes.I2S;
import static org.mvel2.asm.Opcodes.ILOAD;
import static org.mvel2.asm.Opcodes.INSTANCEOF;
import static org.mvel2.asm.Opcodes.INVOKEINTERFACE;
import static org.mvel2.asm.Opcodes.INVOKESPECIAL;
import static org.mvel2.asm.Opcodes.INVOKESTATIC;
import static org.mvel2.asm.Opcodes.INVOKEVIRTUAL;
import static org.mvel2.asm.Opcodes.ISTORE;
import static org.mvel2.asm.Opcodes.L2D;
import static org.mvel2.asm.Opcodes.L2F;
import static org.mvel2.asm.Opcodes.L2I;
import static org.mvel2.asm.Opcodes.NEW;
import static org.mvel2.asm.Opcodes.NEWARRAY;
import static org.mvel2.asm.Opcodes.PUTFIELD;
import static org.mvel2.asm.Opcodes.PUTSTATIC;
import static org.mvel2.asm.Opcodes.RETURN;
import static org.mvel2.asm.Opcodes.T_BOOLEAN;
import static org.mvel2.asm.Opcodes.T_BYTE;
import static org.mvel2.asm.Opcodes.T_CHAR;
import static org.mvel2.asm.Opcodes.T_DOUBLE;
import static org.mvel2.asm.Opcodes.T_FLOAT;
import static org.mvel2.asm.Opcodes.T_INT;
import static org.mvel2.asm.Opcodes.T_LONG;
import static org.mvel2.asm.Opcodes.T_SHORT;

public class ClassGenerator {

    private static final boolean DUMP_GENERATED_CLASSES = false;

    private final String className;
    private final TypeResolver typeResolver;
    private final ClassLoader classLoader;

    private int access = ACC_PUBLIC + ACC_SUPER;
    private String signature;
    private Class superClass = Object.class;
    private Class<?>[] interfaces;

    private final String classDescriptor;
    private String superDescriptor;

    private List<ClassPartDescr> classParts = new ArrayList<ClassPartDescr>();
    private StaticInitializerDescr staticInitializer = null;

    private byte[] bytecode;
    private Class<?> clazz;

    private static final Method defineClassMethod;

    static {
        try {
            defineClassMethod = ClassLoader.class.getDeclaredMethod("defineClass", String.class, byte[].class, int.class, int.class);
            defineClassMethod.setAccessible(true);
        } catch (NoSuchMethodException e) {
            throw new RuntimeException(e);
        }
    }

    public ClassGenerator(String className, ClassLoader classLoader) {
        this(className, classLoader, null);
    }

    public ClassGenerator(String className, ClassLoader classLoader, TypeResolver typeResolver) {
        this.className = className;
        this.classDescriptor = className.replace('.', '/');
        this.classLoader = classLoader;
        this.typeResolver = typeResolver == null ? new InternalTypeResolver(this.classLoader) : typeResolver;
    }

    private interface ClassPartDescr {
        void write(ClassGenerator cg, ClassWriter cw);
    }

    public byte[] generateBytecode() {
        if (bytecode == null) {
            ClassWriter cw = createClassWriter(classLoader, access, getClassDescriptor(), signature, getSuperClassDescriptor(), toInteralNames(interfaces));
            for (int i = 0; i < classParts.size(); i++) { // don't use iterator to allow method visits to add more class fields and methods
                classParts.get(i).write(this, cw);
            }
            if (staticInitializer != null) {
                staticInitializer.write(this, cw);
            }
            cw.visitEnd();
            bytecode = cw.toByteArray();
            if (DUMP_GENERATED_CLASSES) {
                dumpGeneratedClass(bytecode);
            }
        }
        return bytecode;
    }

    private Class<?> generateClass() {
        if (clazz == null) {
            byte[] bytecode = generateBytecode();
            try {
                clazz = (Class<?>) defineClassMethod.invoke(classLoader, className, bytecode, 0, bytecode.length);
            } catch (Exception e) {
                clazz = new InternalClassLoader(classLoader).defineClass(className, bytecode);
            }
        }
        return clazz;
    }

    private static class InternalClassLoader extends ClassLoader {
        InternalClassLoader(ClassLoader classLoader) {
            super(classLoader);
        }
        Class<?> defineClass(String name, byte[] b) {
            return defineClass(name, b, 0, b.length);
        }
    }

    public void dumpGeneratedClass() {
        if (!DUMP_GENERATED_CLASSES) {
            dumpGeneratedClass(generateBytecode());
        }
    }

    private void dumpGeneratedClass(byte[] bytecode) {
        FileOutputStream fos = null;
        try {
            fos = new FileOutputStream(className + ".class");
            fos.write(bytecode);
            fos.flush();
        } catch (FileNotFoundException e) {
            throw new RuntimeException(e);
        } catch (IOException e) {
            throw new RuntimeException(e);
        } finally {
            if (fos != null) {
                try {
                    fos.close();
                } catch (IOException e) { }
            }
        }
    }

    public <T> T newInstance() {
        try {
            return (T)generateClass().newInstance();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public <T> T newInstance(Class paramType, Object param) {
        try {
            return (T)generateClass().getConstructor(paramType).newInstance(param);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    // Accessors

    public String getClassDescriptor() {
        return classDescriptor;
    }

    public String getSuperClassDescriptor() {
        if (superDescriptor == null) superDescriptor = toInteralName(superClass);
        return superDescriptor;
    }

    public ClassGenerator setAccess(int access) {
        this.access = access;
        return this;
    }

    public ClassGenerator setSignature(String signature) {
        this.signature = signature;
        return this;
    }

    public ClassGenerator setSuperClass(Class superClass) {
        this.superClass = superClass;
        return this;
    }

    public ClassGenerator setInterfaces(Class<?>... interfaces) {
        this.interfaces = interfaces;
        return this;
    }

    // Utility

    private Map<Class<?>, String> descriptorsCache = new HashMap<Class<?>, String>();

    private String descriptorOf(Class<?> type) {
        String descriptor = descriptorsCache.get(type);
        if (descriptor == null) {
            descriptor = Type.getDescriptor(type);
            descriptorsCache.put(type, descriptor);
        }
        return descriptor;
    }

    public String methodDescr(Class<?> type, Class<?>... args) {
        StringBuilder desc = new StringBuilder("(");
        if (args != null) for (Class<?> arg : args) desc.append(descriptorOf(arg));
        desc.append(")").append(type == null ? "V" : descriptorOf(type));
        return desc.toString();
    }

    private Type toType(Class<?> clazz) {
        return toType(clazz.getName());
    }

    private Type toType(String typeName) {
        return Type.getType(toTypeDescriptor(typeName));
    }

    public String toTypeDescriptor(Class<?> clazz) {
        return descriptorOf(clazz);
    }

    public String toTypeDescriptor(String className) {
        String arrayPrefix = "";
        while (className.endsWith("[]")) {
            arrayPrefix += "[";
            className = className.substring(0, className.length()-2);
        }
        String typeDescriptor;
        try {
            typeDescriptor = toTypeDescriptor(typeResolver.resolveType(className));
        } catch (ClassNotFoundException e) {
            typeDescriptor = "L" + className.replace('.', '/') + ";";
        }
        return arrayPrefix + typeDescriptor;
    }

    public String toInteralName(Class<?> clazz) {
        return clazz.isPrimitive() ? descriptorOf(clazz) : Type.getType(clazz).getInternalName();
    }

    public String toInteralName(String className) {
        String arrayPrefix = "";
        while (className.endsWith("[]")) {
            arrayPrefix += "[";
            className = className.substring(0, className.length()-2);
        }
        String typeDescriptor;
        boolean isPrimitive = false;
        try {
            Class<?> clazz = typeResolver.resolveType(className);
            isPrimitive = clazz.isPrimitive();
            typeDescriptor = toInteralName(clazz);
        } catch (ClassNotFoundException e) {
            typeDescriptor = className.replace('.', '/');
        }
        if (!isPrimitive && arrayPrefix.length() > 0) typeDescriptor = "L" + typeDescriptor + ";";
        return arrayPrefix + typeDescriptor;
    }

    private String[] toInteralNames(Class<?>[] classes) {
        if (classes == null) return null;
        String[] internals = new String[classes.length];
        for (int i = 0; i < classes.length; i++) internals[i] = toInteralName(classes[i]);
        return internals;
    }

    // FieldDescr

    public ClassGenerator addField(int access, String name, Class<?> type) {
        return addField(access, name, type, null, null);
    }

    public ClassGenerator addField(int access, String name, Class<?> type, String signature) {
        return addField(access, name, type, signature, null);
    }

    public ClassGenerator addStaticField(int access, String name, Class<?> type, Object value) {
        return addField(access + ACC_STATIC, name, type, null, value);
    }

    public ClassGenerator addStaticField(int access, String name, Class<?> type, String signature, Object value) {
        return addField(access + ACC_STATIC, name, type, signature, value);
    }

    private ClassGenerator addField(int access, String name, Class<?> type, String signature, Object value) {
        classParts.add(new FieldDescr(access, name, descriptorOf(type), signature, value));
        return this;
    }

    private static class FieldDescr implements ClassPartDescr {
        private final int access;
        private final String name;
        private final String desc;
        private final String signature;
        private final Object value;

        FieldDescr(int access, String name, String desc, String signature, Object value) {
            this.access = access;
            this.name = name;
            this.desc = desc;
            this.signature = signature;
            this.value = value;
        }

        public void write(ClassGenerator cg, ClassWriter cw) {
            cw.visitField(access, name, desc, signature, value).visitEnd();
        }
    }

    public ClassGenerator addDefaultConstructor() {
        return addDefaultConstructor(EMPTY_METHOD_BODY);
    }

    public ClassGenerator addDefaultConstructor(final MethodBody body, Class<?>... args) {
        MethodBody constructorBody = new MethodBody() {
            public void body(MethodVisitor mv) {
                mv.visitVarInsn(ALOAD, 0);
                mv.visitMethodInsn(INVOKESPECIAL, getClassGenerator().getSuperClassDescriptor(), "<init>", "()V"); // super()
                body.writeBody(getClassGenerator(), mv);
            }
        };

        return addMethod(ACC_PUBLIC, "<init>", methodDescr(null, args), constructorBody);
    }

    public ClassGenerator addMethod(int access, String name, String desc) {
        return addMethod(access, name, desc, null, null, EMPTY_METHOD_BODY);
    }

    public ClassGenerator addMethod(int access, String name, String desc, MethodBody body) {
        return addMethod(access, name, desc, null, null, body);
    }

    public ClassGenerator addMethod(int access, String name, String desc, String signature, MethodBody body) {
        return addMethod(access, name, desc, signature, null, body);
    }

    public ClassGenerator addMethod(int access, String name, String desc, String[] exceptions, MethodBody body) {
        return addMethod(access, name, desc, null, exceptions, body);
    }

    public ClassGenerator addMethod(int access, String name, String desc, String signature, String[] exceptions, MethodBody body) {
        classParts.add(new MethodDescr(access, name, desc, signature, exceptions, body));
        return this;
    }

    public ClassGenerator addStaticInitBlock(MethodBody body) {
        if (staticInitializer == null) {
            staticInitializer = new StaticInitializerDescr();
        }
        staticInitializer.addInitializer(body);
        return this;
    }

    private static final MethodBody EMPTY_METHOD_BODY = new MethodBody() {
        protected final void body(MethodVisitor mv) {
            mv.visitInsn(RETURN); // return
        }
    };

    // MethodBody

    public abstract static class MethodBody {
        private ClassGenerator classGenerator;
        protected MethodVisitor mv;
        private Map<Integer, Type> storedTypes;

        protected abstract void body(MethodVisitor mv);

        public final void writeBody(ClassGenerator classGenerator, MethodVisitor mv) {
            this.classGenerator = classGenerator;
            this.mv = mv;
            try {
                body(mv);
            } finally {
                this.classGenerator = null;
                this.mv = null;
            }
        }

        protected ClassGenerator getClassGenerator() {
            return classGenerator;
        }

        protected final int getCodeForType(Class<?> typeClass, int opcode) {
            return Type.getType(typeClass).getOpcode(opcode);
        }

        protected final int store(int registry, Class<?> typeClass) {
            return store(registry, Type.getType(typeClass));
        }

        protected final int store(int registry, String typeName) {
            return store(registry, classGenerator.toType(typeName));
        }

        protected final int store(int registry, Type t) {
            if (storedTypes == null) storedTypes = new HashMap<Integer, Type>();
            mv.visitVarInsn(t.getOpcode(ISTORE), registry);
            storedTypes.put(registry, t);
            return t.getSize();
        }

        protected final void load(int registry) {
            mv.visitVarInsn(storedTypes.get(registry).getOpcode(ILOAD), registry);
        }

        protected final void loadAsObject(int registry) {
            Type type = storedTypes.get(registry);
            mv.visitVarInsn(type.getOpcode(ILOAD), registry);
            String typeName = type.getClassName();
            convertPrimitiveToObject(typeName);
        }

        protected void convertPrimitiveToObject(Class<?> primitiveClass) {
            convertPrimitiveToObject(primitiveClass.getName());
        }

        private void convertPrimitiveToObject(String typeName) {
            if (typeName.equals("int"))
                mv.visitMethodInsn(INVOKESTATIC, "java/lang/Integer", "valueOf", "(I)Ljava/lang/Integer;");
            else if (typeName.equals("boolean"))
                mv.visitMethodInsn(INVOKESTATIC, "java/lang/Boolean", "valueOf", "(Z)Ljava/lang/Boolean;");
            else if (typeName.equals("char"))
                mv.visitMethodInsn(INVOKESTATIC, "java/lang/Character", "valueOf", "(C)Ljava/lang/Character;");
            else if (typeName.equals("byte"))
                mv.visitMethodInsn(INVOKESTATIC, "java/lang/Byte", "valueOf", "(B)Ljava/lang/Byte;");
            else if (typeName.equals("short"))
                mv.visitMethodInsn(INVOKESTATIC, "java/lang/Short", "valueOf", "(S)Ljava/lang/Short;");
            else if (typeName.equals("float"))
                mv.visitMethodInsn(INVOKESTATIC, "java/lang/Float", "valueOf", "(F)Ljava/lang/Float;");
            else if (typeName.equals("long"))
                mv.visitMethodInsn(INVOKESTATIC, "java/lang/Long", "valueOf", "(J)Ljava/lang/Long;");
            else if (typeName.equals("double"))
                mv.visitMethodInsn(INVOKESTATIC, "java/lang/Double", "valueOf", "(D)Ljava/lang/Double;");
        }

        protected final void print(String msg) {
            mv.visitFieldInsn(GETSTATIC, "java/lang/System", "out", "Ljava/io/PrintStream;");
            mv.visitLdcInsn(msg);
            mv.visitMethodInsn(INVOKEVIRTUAL, "java/io/PrintStream", "print", "(Ljava/lang/String;)V");
        }

        protected final void println(String msg) {
            mv.visitFieldInsn(GETSTATIC, "java/lang/System", "out", "Ljava/io/PrintStream;");
            mv.visitLdcInsn(msg);
            mv.visitMethodInsn(INVOKEVIRTUAL, "java/io/PrintStream", "println", "(Ljava/lang/String;)V");
        }

        protected final void printRegistryValue(int reg) {
            Type type = storedTypes.get(reg);
            if (type == null) {
                printRegistryValue(reg, Object.class);
                return;
            }

            printRegistryValue(reg, convertPrimitiveNameToType(type.getClassName()));
        }

        protected final void printRegistryValue(int reg, Class<?> clazz) {
            mv.visitFieldInsn(GETSTATIC, "java/lang/System", "out", "Ljava/io/PrintStream;");
            mv.visitVarInsn(Type.getType(clazz).getOpcode(ILOAD), reg);
            invokeVirtual(PrintStream.class, "print", null, clazz);
        }

        protected final void printLastRegistry(Class<?> clazz) {
            Type t = Type.getType(clazz);
            mv.visitVarInsn(t.getOpcode(ISTORE), 100);
            mv.visitFieldInsn(GETSTATIC, "java/lang/System", "out", "Ljava/io/PrintStream;");
            mv.visitVarInsn(t.getOpcode(ILOAD), 100);
            invokeVirtual(PrintStream.class, "print", null, clazz);
        }

        protected final void printStack() {
            mv.visitTypeInsn(NEW, "java/lang/RuntimeException");
            mv.visitInsn(DUP);
            mv.visitMethodInsn(INVOKESPECIAL, "java/lang/RuntimeException", "<init>", "()V");
            mv.visitMethodInsn(INVOKEVIRTUAL, "java/lang/RuntimeException", "printStackTrace", "()V");
            mv.visitInsn(RETURN);
        }

        protected final <T> void returnAsArray(T[] array) {
            createArray(array.getClass().getComponentType(), array.length);
            for (int i = 0; i < array.length; i++) {
                mv.visitInsn(DUP);
                push(i);
                push(array[i]);
                mv.visitInsn(AASTORE);
            }
            mv.visitInsn(ARETURN);
        }

        protected final <T> void returnAsArray(Collection<T> collection, Class<T> clazz) {
            createArray(clazz, collection.size());
            int i = 0;
            for (T item : collection) {
                mv.visitInsn(DUP);
                push(i++);
                push(item);
                mv.visitInsn(AASTORE);
            }
            mv.visitInsn(ARETURN);
        }

        protected final void createArray(Class<?> componentType, int size) {
            mv.visitLdcInsn(size);
            if (componentType.isPrimitive()) {
                int newPrimitiveArrayType = T_BOOLEAN;
                if (componentType == int.class) {
                    newPrimitiveArrayType = T_INT;
                } else if (componentType == long.class) {
                    newPrimitiveArrayType = T_LONG;
                } else if (componentType == double.class) {
                    newPrimitiveArrayType = T_DOUBLE;
                } else if (componentType == float.class) {
                    newPrimitiveArrayType = T_FLOAT;
                } else if (componentType == char.class) {
                    newPrimitiveArrayType = T_CHAR;
                } else if (componentType == short.class) {
                    newPrimitiveArrayType = T_SHORT;
                } else if (componentType == byte.class) {
                    newPrimitiveArrayType = T_BYTE;
                }
                mv.visitIntInsn(NEWARRAY, newPrimitiveArrayType);
            } else {
                mv.visitTypeInsn(ANEWARRAY, internalName(componentType));
            }
        }

       protected final void push(Object obj) {
            if (obj instanceof Boolean) {
                mv.visitFieldInsn(GETSTATIC, "java/lang/Boolean", (Boolean)obj ? "TRUE" : "FALSE", "Ljava/lang/Boolean;");
            } else {
                mv.visitLdcInsn(obj);
            }
        }

        protected final void push(Object obj, Class<?> type) {
            if (obj == null) {
                mv.visitInsn(ACONST_NULL);
                return;
            }

            if (type == String.class || type == Object.class) {
                mv.visitLdcInsn(obj);
            } else if (type == char.class) {
                mv.visitIntInsn(BIPUSH, (int)((Character)obj).charValue());
            } else if (type.isPrimitive()) {
                if (obj instanceof String) {
                    obj = coerceStringToPrimitive(type, (String)obj);
                } else {
                    obj = coercePrimitiveToPrimitive(type, obj);
                }
                mv.visitLdcInsn(obj);
            } else if (type == Class.class) {
                mv.visitLdcInsn(classGenerator.toType((Class<?>) obj));
            } else if (type == Character.class) {
                invokeConstructor(Character.class, new Object[]{ obj.toString().charAt(0) }, char.class);
            } else if (type.isInterface() || isAbstract(type.getModifiers())) {
                push(obj, obj.getClass());
            } else {
                invokeConstructor(type, new Object[]{ obj.toString() }, String.class);
            }
        }

        private Object coercePrimitiveToPrimitive(Class<?> primitiveType, Object value) {
            if (primitiveType == long.class) {
                return ((Number)value).longValue();
            }
            if (primitiveType == double.class) {
                return ((Number)value).doubleValue();
            }
            if (primitiveType == float.class) {
                return ((Number)value).floatValue();
            }
            return value;
        }

        private Object coerceStringToPrimitive(Class<?> primitiveType, String value) {
            if (primitiveType == boolean.class) {
                return Boolean.valueOf(value);
            }
            if (primitiveType == int.class) {
                return Integer.valueOf(value);
            }
            if (primitiveType == long.class) {
                return Long.valueOf(value);
            }
            if (primitiveType == float.class) {
                return Float.valueOf(value);
            }
            if (primitiveType == double.class) {
                return Double.valueOf(value);
            }
            if (primitiveType == char.class) {
                return Character.valueOf(value.charAt(0));
            }
            if (primitiveType == short.class) {
                return Short.valueOf(value);
            }
            if (primitiveType == byte.class) {
                return Byte.valueOf(value);
            }
            throw new RuntimeException("Unexpected type: " + primitiveType);
        }

        protected final void cast(Class<?> from, Class<?> to) {
            if (to.isAssignableFrom(from)) {
                return;
            }
            if (from.isPrimitive()) {
                if (to.isPrimitive()) {
                    castPrimitiveToPrimitive(from, to);
                } else {
                    Class toPrimitive = convertToPrimitiveType(to);
                    castPrimitiveToPrimitive(convertToPrimitiveType(from), toPrimitive);
                    castFromPrimitive(toPrimitive);
                }
            } else {
                if (to.isPrimitive()) {
                    Class<?> primitiveFrom = convertToPrimitiveType(from);
                    castToPrimitive(primitiveFrom);
                    castPrimitiveToPrimitive(primitiveFrom, to);
                } else {
                    cast(to);
                }
            }
        }

        protected final void cast(Class<?> clazz) {
            mv.visitTypeInsn(CHECKCAST, internalName(clazz));
        }

        protected final void instanceOf(Class<?> clazz) {
            mv.visitTypeInsn(INSTANCEOF, internalName(clazz));
        }

        protected final void castPrimitiveToPrimitive(Class<?> from, Class<?> to) {
            if (from == to) return;
            if (from == int.class) {
                if (to == long.class) mv.visitInsn(I2L);
                else if (to == float.class) mv.visitInsn(I2F);
                else if (to == double.class) mv.visitInsn(I2D);
                else if (to == byte.class) mv.visitInsn(I2B);
                else if (to == char.class) mv.visitInsn(I2C);
                else if (to == short.class) mv.visitInsn(I2S);
            } else if (from == long.class) {
                if (to == int.class) mv.visitInsn(L2I);
                else if (to == float.class) mv.visitInsn(L2F);
                else if (to == double.class) mv.visitInsn(L2D);
            } else if (from == float.class) {
                if (to == int.class) mv.visitInsn(F2I);
                else if (to == long.class) mv.visitInsn(F2L);
                else if (to == double.class) mv.visitInsn(F2D);
            } else if (from == double.class) {
                if (to == int.class) mv.visitInsn(D2I);
                else if (to == long.class) mv.visitInsn(D2L);
                else if (to == float.class) mv.visitInsn(D2F);
            }
        }

        protected final void castFromPrimitive(Class<?> clazz) {
            Class<?> boxedType = convertFromPrimitiveType(clazz);
            invokeStatic(boxedType, "valueOf", boxedType, clazz);
        }

        protected final void castToPrimitive(Class<?> clazz) {
            if (clazz == boolean.class) {
                cast(Boolean.class);
                invokeVirtual(Boolean.class, "booleanValue", boolean.class);
            } else if (clazz == char.class) {
                cast(Character.class);
                invokeVirtual(Character.class, "charValue", char.class);
            } else {
                cast(Number.class);
                invokeVirtual(Number.class, clazz.getName() + "Value", clazz);
            }
        }

        protected final void invoke(Method method) {
            if ((method.getModifiers() & Modifier.STATIC) > 0) {
                invokeStatic(method.getDeclaringClass(), method.getName(), method.getReturnType(), method.getParameterTypes());
            } else if (method.getDeclaringClass().isInterface()) {
                invokeInterface(method.getDeclaringClass(), method.getName(), method.getReturnType(), method.getParameterTypes());
            } else {
                invokeVirtual(method.getDeclaringClass(), method.getName(), method.getReturnType(), method.getParameterTypes());
            }
        }

        protected final void invokeThis(String methodName, Class<?> returnedType, Class<?>... paramsType) {
            mv.visitMethodInsn(INVOKEVIRTUAL, classDescriptor(), methodName, methodDescr(returnedType, paramsType));
        }

        protected final void invokeStatic(Class<?> clazz, String methodName, Class<?> returnedType, Class<?>... paramsType) {
            invoke(INVOKESTATIC, clazz, methodName, returnedType, paramsType);
        }

        protected final void invokeVirtual(Class<?> clazz, String methodName, Class<?> returnedType, Class<?>... paramsType) {
            invoke(INVOKEVIRTUAL, clazz, methodName, returnedType, paramsType);
        }

        protected final void invokeInterface(Class<?> clazz, String methodName, Class<?> returnedType, Class<?>... paramsType) {
            invoke(INVOKEINTERFACE, clazz, methodName, returnedType, paramsType);
        }

        protected final void invokeConstructor(Class<?> clazz) {
            invokeConstructor(clazz, null);
        }

        protected final void invokeConstructor(Class<?> clazz, Object[] params, Class<?>... paramsType) {
            mv.visitTypeInsn(NEW, internalName(clazz));
            mv.visitInsn(DUP);
            if (params != null) {
                for (Object param : params) mv.visitLdcInsn(param);
            }
            invokeSpecial(clazz, "<init>", null, paramsType);
        }

        protected final void invokeSpecial(Class<?> clazz, String methodName, Class<?> returnedType, Class<?>... paramsType) {
            invoke(INVOKESPECIAL, clazz, methodName, returnedType, paramsType);
        }

        protected final void invoke(int opCode, Class<?> clazz, String methodName, Class<?> returnedType, Class<?>... paramsType) {
            mv.visitMethodInsn(opCode, internalName(clazz), methodName, methodDescr(returnedType, paramsType));
        }

        protected final void putStaticField(String name, Class<?> type) {
            mv.visitFieldInsn(PUTSTATIC, classDescriptor(), name, classGenerator.descriptorOf(type));
        }

        protected final void getStaticField(String name, Class<?> type) {
            mv.visitFieldInsn(GETSTATIC, classDescriptor(), name, classGenerator.descriptorOf(type));
        }

        protected final void putFieldInThisFromRegistry(String name, Class<?> type, int regNr) {
            mv.visitVarInsn(ALOAD, 0);
            mv.visitVarInsn(ALOAD, regNr);
            putFieldInThis(name, type);
        }

        protected final void putFieldInThis(String name, Class<?> type) {
            mv.visitFieldInsn(PUTFIELD, classDescriptor(), name, classGenerator.descriptorOf(type));
        }

        protected final void getFieldFromThis(String name, Class<?> type) {
            mv.visitVarInsn(ALOAD, 0);
            mv.visitFieldInsn(GETFIELD, classDescriptor(), name, classGenerator.descriptorOf(type));
        }

        protected final void readField(Field field) {
            boolean isStatic = (field.getModifiers() & Modifier.STATIC) != 0;
            mv.visitFieldInsn(isStatic ? GETSTATIC : GETFIELD, field.getDeclaringClass().getName().replace('.', '/'), field.getName(), classGenerator.descriptorOf(field.getType()));
        }

        // ClassGenerator delegates

        public String classDescriptor() {
            return classGenerator.getClassDescriptor();
        }

        public String superClassDescriptor() {
            return classGenerator.getSuperClassDescriptor();
        }
        public String methodDescr(Class<?> type, Class<?>... args) {
            return classGenerator.methodDescr(type, args);
        }

        private Type type(String typeName) {
            return classGenerator.toType(typeName);
        }

        public String typeDescr(Class<?> clazz) {
            return classGenerator.toTypeDescriptor(clazz);
        }

        public String typeDescr(String className) {
            return classGenerator.toTypeDescriptor(className);
        }

        public String internalName(Class<?> clazz) {
            return classGenerator.toInteralName(clazz);
        }

        public String internalName(String className) {
            return classGenerator.toInteralName(className);
        }
    }

    // MethodDescr

    private static class MethodDescr implements ClassPartDescr {
        private final int access;
        private final String name;
        private final String desc;
        private final String signature;
        private final String[] exceptions;
        private final MethodBody body;

        private MethodDescr(int access, String name, String desc, String signature, String[] exceptions, MethodBody body) {
            this.access = access;
            this.name = name;
            this.desc = desc;
            this.signature = signature;
            this.exceptions = exceptions;
            this.body = body;
        }

        public void write(ClassGenerator cg, ClassWriter cw) {
            MethodVisitor mv = cw.visitMethod(access, name, desc, signature, exceptions);
            mv.visitCode();

            try {
                body.writeBody(cg, mv);
                mv.visitMaxs(0, 0);
            } catch (Exception e) {
                throw new RuntimeException("Error writing method " + name, e);
            }

            mv.visitEnd();
        }
    }

    private static class StaticInitializerDescr implements ClassPartDescr {

        private final List<MethodBody> initializerBodies = new ArrayList<MethodBody>();

        public void write(ClassGenerator cg, ClassWriter cw) {
            MethodVisitor mv = cw.visitMethod(ACC_STATIC, "<clinit>", "()V", null, null);
            mv.visitCode();

            try {
                for (MethodBody initializerBody : initializerBodies) {
                    initializerBody.writeBody(cg, mv);
                }
            } catch (Exception e) {
                throw new RuntimeException("Error writing method static class initializer", e);
            }

            mv.visitInsn(RETURN);
            mv.visitMaxs(0, 0);
            mv.visitEnd();
        }

        private void addInitializer(MethodBody initBlock) {
            initializerBodies.add(initBlock);
        }
    }

    // InternalTypeResolver

    private static class InternalTypeResolver implements TypeResolver {

        public static final Map<String, Class<?>> primitiveClassMap = new HashMap<String, Class<?>>() {{
            put("int", int.class);
            put("boolean", boolean.class);
            put("float", float.class);
            put("long", long.class);
            put("short", short.class);
            put("byte", byte.class);
            put("double", double.class);
            put("char", char.class);
        }};

        private final ClassLoader classLoader;

        private InternalTypeResolver(ClassLoader classLoader) {
            this.classLoader = classLoader;
        }

        public Set<String> getImports() {
            throw new RuntimeException("Not Implemented");
        }

        public void addImport(String importEntry) {
            throw new RuntimeException("Not Implemented");
        }

        public void addImplicitImport(String importEntry) {
            throw new RuntimeException("Not Implemented");
        }

        public Class<?> resolveType(String className) throws ClassNotFoundException {
            Class<?> primitiveClassName = primitiveClassMap.get(className);
            return primitiveClassName != null ? primitiveClassName : Class.forName(className, true, classLoader);
        }

        public Class<?> resolveType(String className, ClassFilter classFilter) throws ClassNotFoundException {
            throw new RuntimeException("Not Implemented");
        }

        public String getFullTypeName(String shortName) throws ClassNotFoundException {
            throw new RuntimeException("Not Implemented");
        }

        public ClassLoader getClassLoader() {
            return classLoader;
        }
    }

    public static class InternalClassWriter extends ClassWriter {

        private ClassLoader classLoader;

        public InternalClassWriter(ClassLoader classLoader, int flags) {
            super(flags);
            this.classLoader = classLoader;
        }

        protected String getCommonSuperClass(final String type1, final String type2) {
            Class c, d;
            try {
                c = Class.forName(type1.replace('/', '.'), false, classLoader);
                d = Class.forName(type2.replace('/', '.'), false, classLoader);
            } catch (Exception e) {
                throw new RuntimeException(e.toString());
            }
            if (c.isAssignableFrom(d)) {
                return type1;
            }
            if (d.isAssignableFrom(c)) {
                return type2;
            }
            if (c.isInterface() || d.isInterface()) {
                return "java/lang/Object";
            } else {
                do {
                    c = c.getSuperclass();
                } while (!c.isAssignableFrom(d));
                return c.getName().replace('.', '/');
            }
        }
    }

    public static ClassWriter createClassWriter(ClassLoader classLoader, int access, String name, String signature, String superName, String[] interfaces) {
        ClassWriter cw = new InternalClassWriter(classLoader, ClassWriter.COMPUTE_MAXS | ClassWriter.COMPUTE_FRAMES );
        cw.visit(ClassLevel.getJavaVersion(classLoader), access, name, signature, superName, interfaces);
        return cw;
    }
}


File: drools-core/src/main/java/org/drools/core/util/ClassUtils.java
/*
 * Copyright 2010 JBoss Inc
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

package org.drools.core.util;

import org.drools.core.common.DroolsObjectInputStream;
import org.drools.core.common.DroolsObjectOutputStream;
import org.kie.api.definition.type.Modifies;
import org.kie.internal.utils.ClassLoaderUtil;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.Externalizable;
import java.io.File;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.security.AccessController;
import java.security.PrivilegedAction;
import java.security.ProtectionDomain;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import static org.drools.core.util.StringUtils.ucFirst;

public final class ClassUtils {
    private static final ProtectionDomain  PROTECTION_DOMAIN;

    static {
        PROTECTION_DOMAIN = (ProtectionDomain) AccessController.doPrivileged( new PrivilegedAction() {

            public Object run() {
                return ClassLoaderUtil.class.getProtectionDomain();
            }
        } );
    }
    
    private static Map<String, Class<?>> classes = Collections.synchronizedMap( new HashMap() );

    private static final String STAR    = "*";

    public static boolean areNullSafeEquals(Object obj1, Object obj2) {
        return obj1 == null ? obj2 == null : obj1.equals(obj2);
    }

    /**
     * Please do not use - internal
     * org/my/Class.xxx -> org.my.Class
     */
    public static String convertResourceToClassName(final String pResourceName) {
        return stripExtension(pResourceName).replace('/', '.');
    }

    /**
     * Please do not use - internal
     * org.my.Class -> org/my/Class.class
     */
    public static String convertClassToResourcePath(final Class cls) {
        return convertClassToResourcePath(cls.getName());
    }

    public static String convertClassToResourcePath(final String pName) {
        return pName.replace( '.',
                              '/' ) + ".class";
    }

    /**
     * Please do not use - internal
     * org/my/Class.xxx -> org/my/Class
     */
    public static String stripExtension(final String pResourceName) {
        final int i = pResourceName.lastIndexOf('.');
        return pResourceName.substring( 0, i );
    }

    public static String toJavaCasing(final String pName) {
        final char[] name = pName.toLowerCase().toCharArray();
        name[0] = Character.toUpperCase( name[0] );
        return new String( name );
    }

    public static String clazzName(final File base,
                                   final File file) {
        final int rootLength = base.getAbsolutePath().length();
        final String absFileName = file.getAbsolutePath();
        final int p = absFileName.lastIndexOf( '.' );
        final String relFileName = absFileName.substring( rootLength + 1, p );
        return relFileName.replace(File.separatorChar, '.');
    }

    public static String relative(final File base,
                                  final File file) {
        final int rootLength = base.getAbsolutePath().length();
        final String absFileName = file.getAbsolutePath();
        return absFileName.substring( rootLength + 1 );
    }

    public static String canonicalName(Class clazz) {
        StringBuilder name = new StringBuilder();

        if ( clazz.isArray() ) {
            name.append( canonicalName( clazz.getComponentType() ) );
            name.append( "[]" );
        } else if ( clazz.getDeclaringClass() == null ) {
            name.append( clazz.getName() );
        } else {
            name.append( canonicalName( clazz.getDeclaringClass() ) );
            name.append( "." );
            name.append( clazz.getName().substring( clazz.getDeclaringClass().getName().length() + 1 ) );
        }

        return name.toString();
    }

    public static Object instantiateObject(String className) {
        return instantiateObject( className,
                                  null );
    }

    /**
     * This method will attempt to create an instance of the specified Class. It uses
     * a syncrhonized HashMap to cache the reflection Class lookup.
     * @param className
     * @return
     */
    public static Object instantiateObject(String className,
                                           ClassLoader classLoader) {
        Class cls = (Class) classes.get( className );
        if ( cls == null ) {
            try {
                cls = Class.forName( className );
            } catch ( Exception e ) {
                //swallow
            }

            //ConfFileFinder
            if ( cls == null && classLoader != null ) {
                try {
                    cls = classLoader.loadClass( className );
                } catch ( Exception e ) {
                    //swallow
                }
            }

            if ( cls == null ) {
                try {
                    cls = ClassUtils.class.getClassLoader().loadClass( className );
                } catch ( Exception e ) {
                    //swallow
                }
            }

            if ( cls == null ) {
                try {
                    cls = Thread.currentThread().getContextClassLoader().loadClass( className );
                } catch ( Exception e ) {
                    //swallow
                }
            }

            if ( cls == null ) {
                try {
                    cls = ClassLoader.getSystemClassLoader().loadClass( className );
                } catch ( Exception e ) {
                    //swallow
                }
            }

            if ( cls != null ) {
                classes.put( className, cls );
            } else {
                throw new RuntimeException( "Unable to load class '" + className + "'" );
            }
        }

        Object object;
        try {
            object = cls.newInstance();
        } catch ( Throwable e ) {
            throw new RuntimeException( "Unable to instantiate object for class '" + className + "'",
                                        e );
        }
        return object;
    }

    /**
     * Populates the import style pattern map from give comma delimited string
     * @param patterns
     * @param str
     */
    public static void addImportStylePatterns(Map<String, Object> patterns,
                                              String str) {
        if ( str == null || "".equals( str.trim() ) ) {
            return;
        }

        String[] items = str.split( " " );
        for (String item : items) {
            String qualifiedNamespace = item.substring(0,
                    item.lastIndexOf('.')).trim();
            String name = item.substring(item.lastIndexOf('.') + 1).trim();
            Object object = patterns.get(qualifiedNamespace);
            if (object == null) {
                if (STAR.equals(name)) {
                    patterns.put(qualifiedNamespace,
                            STAR);
                } else {
                    // create a new list and add it
                    List<String> list = new ArrayList<String>();
                    list.add(name);
                    patterns.put(qualifiedNamespace, list);
                }
            } else if (name.equals(STAR)) {
                // if its a STAR now add it anyway, we don't care if it was a STAR or a List before
                patterns.put(qualifiedNamespace, STAR);
            } else {
                // its a list so add it if it doesn't already exist
                List<String> list = (List<String>) object;
                if (!list.contains(name)) {
                    list.add(name);
                }
            }
        }
    }

    /**
     * Determines if a given full qualified class name matches any import style patterns.
     * @param patterns
     * @param className
     * @return
     */
    public static boolean isMatched(Map<String, Object> patterns,
                                    String className) {
        // Array [] object class names are "[x", where x is the first letter of the array type
        // -> NO '.' in class name, thus!
        // see http://download.oracle.com/javase/6/docs/api/java/lang/Class.html#getName%28%29
        String qualifiedNamespace = className;
        String name = className;
        if( className.indexOf('.') > 0 ) { 
            qualifiedNamespace = className.substring( 0, className.lastIndexOf( '.' ) ).trim();
            name = className.substring( className.lastIndexOf( '.' ) + 1 ).trim();
        }
        else if( className.indexOf('[') == 0 ) { 
           qualifiedNamespace = className.substring(0, className.lastIndexOf('[') );
        }
        Object object = patterns.get( qualifiedNamespace );
        if ( object == null ) {
            return true;
        } else if ( STAR.equals( object ) ) {
            return false;
        } else if ( patterns.containsKey( "*" ) ) {
            // for now we assume if the name space is * then we have a catchall *.* pattern
            return true;
        } else {
            List list = (List) object;
            return !list.contains( name );
        }
    }

    /**
     * Extracts the package name from the given class object
     * @param cls
     * @return
     */
    public static String getPackage(Class<?> cls) {
        // cls.getPackage() sometimes returns null, in which case fall back to string massaging.
        java.lang.Package pkg = cls.isArray() ? cls.getComponentType().getPackage() : cls.getPackage();
        if ( pkg == null ) {
            int dotPos;
            int dolPos = cls.getName().indexOf( '$' );
            if ( dolPos > 0 ) {
                // we have nested classes, so adjust dotpos to before first $
                dotPos = cls.getName().substring( 0, dolPos ).lastIndexOf( '.' );
            } else {
                dotPos = cls.getName().lastIndexOf( '.' );
            }
                
            if ( dotPos > 0 ) {
                return cls.getName().substring( 0,
                                                dotPos );
            } else {
                // must be default package.
                return "";
            }
        } else {
            return pkg.getName();
        }
    }

    public static Class<?> findClass(String name, Collection<String> availableImports, ClassLoader cl) {
        Class<?> clazz = null;
        for (String imp : availableImports) {
            if (imp.endsWith(".*")) {
                imp = imp.substring(0, imp.length()-2);
            }
            String className = imp.endsWith(name) ? imp : imp + "." + name;
            clazz = findClass(className, cl);
            if (clazz != null) {
                break;
            }
        }
        return clazz;
    }

    public static Class<?> findClass(String className, ClassLoader cl) {
        try {
            return Class.forName(className, false, cl);
        } catch (ClassNotFoundException e) {
            int lastDot = className.lastIndexOf('.');
            className = className.substring(0, lastDot) + "$" + className.substring(lastDot+1);
            try {
                return Class.forName(className, false, cl);
            } catch (ClassNotFoundException e1) { }
        }
        return null;
    }

    public static List<String> getSettableProperties(Class<?> clazz) {
        Set<SetterInClass> props = new TreeSet<SetterInClass>();
        for (Method m : clazz.getMethods()) {
            if (m.getParameterTypes().length == 1) {
                String propName = setter2property(m.getName());
                if (propName != null) {
                    props.add( new SetterInClass( propName, m.getDeclaringClass() ) );
                }
            }

            processModifiesAnnotation(clazz, props, m);
        }

        for (Field f : clazz.getFields()) {
            if ( !Modifier.isFinal(f.getModifiers()) && !Modifier.isStatic(f.getModifiers()) ) {
                props.add( new SetterInClass( f.getName(), f.getDeclaringClass() ) );
            }
        }

        List<String> settableProperties = new ArrayList<String>();
        for ( SetterInClass setter : props ) {
            settableProperties.add(setter.setter);
        }
        return settableProperties;
    }

    public static Method getAccessor(Class<?> clazz, String field) {
        try {
            return clazz.getMethod("get" + ucFirst(field));
        } catch (NoSuchMethodException e) {
            try {
                return clazz.getMethod(field);
            } catch (NoSuchMethodException e1) {
                try {
                    return clazz.getMethod("is" + ucFirst(field));
                } catch (NoSuchMethodException e2) {
                    return null;
                }
            }
        }
    }

    private static void processModifiesAnnotation(Class<?> clazz, Set<SetterInClass> props, Method m) {
        Modifies modifies = m.getAnnotation( Modifies.class );
        if (modifies != null) {
            for (String prop : modifies.value()) {
                prop = prop.trim();
                try {
                    Field field = clazz.getField(prop);
                    props.add( new SetterInClass( field.getName(), field.getDeclaringClass() ) );
                } catch (NoSuchFieldException e) {
                    String getter = "get" + prop.substring(0, 1).toUpperCase() + prop.substring(1);
                    try {
                        Method method = clazz.getMethod(getter);
                        props.add( new SetterInClass( prop, method.getDeclaringClass() ) );
                    } catch (NoSuchMethodException e1) {
                        getter = "is" + prop.substring(0, 1).toUpperCase() + prop.substring(1);
                        try {
                            Method method = clazz.getMethod(getter);
                            props.add( new SetterInClass( prop, method.getDeclaringClass() ) );
                        } catch (NoSuchMethodException e2) {
                            throw new RuntimeException(e2);
                        }
                    }
                }
            }
        }
    }

    public static boolean isTypeCompatibleWithArgumentType( Class actual, Class formal ) {
        if ( actual.isPrimitive() && formal.isPrimitive() ) {
            return isConvertible( actual, formal );
        } else if ( actual.isPrimitive() ) {
            return isConvertible( actual, convertToPrimitiveType( formal ) );
        } else if ( formal.isPrimitive() ) {
            return isConvertible( convertToPrimitiveType( actual ), formal );
        } else {
            return formal.isAssignableFrom( actual );
        }
    }

    public static boolean isConvertible( Class srcPrimitive, Class tgtPrimitive ) {
        if ( Boolean.TYPE.equals( srcPrimitive ) ) {
            return Boolean.TYPE.equals( tgtPrimitive );
        } else if ( Byte.TYPE.equals( tgtPrimitive ) ) {
            return Byte.TYPE.equals( tgtPrimitive )
                   || Short.TYPE.equals( tgtPrimitive )
                   || Integer.TYPE.equals( tgtPrimitive )
                   || Long.TYPE.equals( tgtPrimitive )
                   || Float.TYPE.equals( tgtPrimitive )
                   || Double.TYPE.equals( tgtPrimitive );
        } else if ( Character.TYPE.equals( srcPrimitive ) ) {
            return Character.TYPE.equals( tgtPrimitive )
                   || Integer.TYPE.equals( tgtPrimitive )
                   || Long.TYPE.equals( tgtPrimitive )
                   || Float.TYPE.equals( tgtPrimitive )
                   || Double.TYPE.equals( tgtPrimitive );
        } else if ( Double.TYPE.equals( srcPrimitive ) ) {
            return Double.TYPE.equals( tgtPrimitive );
        } else if ( Float.TYPE.equals( srcPrimitive ) ) {
            return Float.TYPE.equals( tgtPrimitive )
                   || Double.TYPE.equals( tgtPrimitive );
        } else if ( Integer.TYPE.equals( srcPrimitive ) ) {
            return Integer.TYPE.equals( tgtPrimitive )
                   || Long.TYPE.equals( tgtPrimitive )
                   || Float.TYPE.equals( tgtPrimitive )
                   || Double.TYPE.equals( tgtPrimitive );
        } else if ( Long.TYPE.equals( srcPrimitive ) ) {
            return Long.TYPE.equals( tgtPrimitive )
                   || Float.TYPE.equals( tgtPrimitive )
                   || Double.TYPE.equals( tgtPrimitive );
        } else if ( Short.TYPE.equals( srcPrimitive ) ) {
            return Short.TYPE.equals( tgtPrimitive )
                   || Integer.TYPE.equals( tgtPrimitive )
                   || Long.TYPE.equals( tgtPrimitive )
                   || Float.TYPE.equals( tgtPrimitive )
                   || Double.TYPE.equals( tgtPrimitive );
        }
        return false;
    }

    private static class SetterInClass implements Comparable {
        private final String setter;
        private final Class<?> clazz;

        private SetterInClass(String setter, Class<?> clazz) {
            this.setter = setter;
            this.clazz = clazz;
        }

        public int compareTo(Object o) {
            SetterInClass other = (SetterInClass) o;
            if (clazz == other.clazz) {
                return setter.compareTo(other.setter);
            }
            return clazz.isAssignableFrom(other.clazz) ? -1 : 1;
        }

        @Override
        public boolean equals(Object obj) {
            SetterInClass other = (SetterInClass) obj;
            return clazz == other.clazz && setter.equals(other.setter);
        }

        @Override
        public int hashCode() {
            return 29 * clazz.hashCode() + 31 * setter.hashCode();
        }
    }

    public static String getter2property(String methodName) {
        if (methodName.startsWith("get") && methodName.length() > 3) {
            return Character.toLowerCase(methodName.charAt(3)) + methodName.substring(4);
        }
        if (methodName.startsWith("is") && methodName.length() > 2) {
            return Character.toLowerCase(methodName.charAt(2)) + methodName.substring(3);
        }
        return null;
    }

    public static String setter2property(String methodName) {
        if (!methodName.startsWith("set") || methodName.length() < 4) {
            return null;
        }
        return Character.toLowerCase(methodName.charAt(3)) + methodName.substring(4);
    }

    public static <T extends Externalizable> T deepClone(T origin) {
        return origin == null ? null : deepClone(origin, origin.getClass().getClassLoader());
    }

    public static <T extends Externalizable> T deepClone(T origin, ClassLoader classLoader) {
        if (origin == null) {
            return null;
        }
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ObjectOutputStream oos = new DroolsObjectOutputStream(baos);
            oos.writeObject(origin);
            ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
            ObjectInputStream ois = new DroolsObjectInputStream(bais, classLoader);
            Object deepCopy = ois.readObject();
            return (T)deepCopy;
        } catch(IOException ioe) {
            throw new RuntimeException(ioe);
        } catch (ClassNotFoundException cnfe) {
            throw new RuntimeException(cnfe);
        }
    }

    public static Class<?> convertFromPrimitiveType(Class<?> type) {
        if (!type.isPrimitive()) return type;
        if (type == int.class) return Integer.class;
        if (type == long.class) return Long.class;
        if (type == float.class) return Float.class;
        if (type == double.class) return Double.class;
        if (type == short.class) return Short.class;
        if (type == byte.class) return Byte.class;
        if (type == char.class) return Character.class;
        if (type == boolean.class) return Boolean.class;
        throw new RuntimeException("Class not convertible from primitive: " + type.getName());
    }

    public static Class<?> convertToPrimitiveType(Class<?> type) {
        if (type.isPrimitive()) return type;
        if (type == Integer.class) return int.class;
        if (type == Long.class) return long.class;
        if (type == Float.class) return float.class;
        if (type == Double.class) return double.class;
        if (type == Short.class) return short.class;
        if (type == Byte.class) return byte.class;
        if (type == Character.class) return char.class;
        if (type == Boolean.class) return boolean.class;
        if (type == BigInteger.class) return long.class;
        if (type == BigDecimal.class) return double.class;
        if (type == Number.class) return double.class;
        throw new RuntimeException("Class not convertible to primitive: " + type.getName());
    }

    public static Class<?> convertPrimitiveNameToType( String typeName ) {
        if (typeName.equals( "int" )) {
            return int.class;
        }
        if (typeName.equals("boolean")) {
            return boolean.class;
        }
        if (typeName.equals("char")) {
            return char.class;
        }
        if (typeName.equals("byte")) {
            return byte.class;
        }
        if (typeName.equals("short")) {
            return short.class;
        }
        if (typeName.equals("float")) {
            return float.class;
        }
        if (typeName.equals("long")) {
            return long.class;
        }
        if (typeName.equals("double")) {
            return double.class;
        }
        return Object.class;
    }

    public static Set<Class<?>> getAllImplementedInterfaceNames( Class<?> klass ) {
        Set<Class<?>> interfaces = new HashSet<Class<?>>();
        while( klass != null ) {
            Class<?>[] localInterfaces = klass.getInterfaces();
            for ( Class<?> intf : localInterfaces ) {
                interfaces.add( intf );
                exploreSuperInterfaces( intf, interfaces );
            }
            klass = klass.getSuperclass();
        }
        return interfaces;
    }

    private static void exploreSuperInterfaces( Class<?> intf, Set<Class<?>> traitInterfaces ) {
        for ( Class<?> sup : intf.getInterfaces() ) {
            traitInterfaces.add( sup );
            exploreSuperInterfaces( sup, traitInterfaces );
        }
    }

    public static Set<Class<?>> getMinimalImplementedInterfaceNames( Class<?> klass ) {
        Set<Class<?>> interfaces = new HashSet<Class<?>>();
        while( klass != null ) {
            Class<?>[] localInterfaces = klass.getInterfaces();
            for ( Class<?> intf : localInterfaces ) {
                boolean subsumed = false;
                for ( Class<?> i : new ArrayList<Class<?>>( interfaces ) ) {
                    if ( intf.isAssignableFrom( i ) ) {
                        subsumed = true;
                        break;
                    } else if ( i.isAssignableFrom( intf ) ) {
                        interfaces.remove( i );
                    }
                }
                if ( subsumed ) {
                    continue;
                }
                interfaces.add( intf );
            }
            klass = klass.getSuperclass();
        }
        return interfaces;
    }

    public static boolean isWindows() {
        String os =  System.getProperty("os.name");
        return os.toUpperCase().contains( "WINDOWS" );
       
    }

    public static boolean isOSX() {
        String os =  System.getProperty("os.name");
        return os.toUpperCase().contains( "MAC OS X" );
    }
}


File: drools-core/src/main/java/org/drools/core/util/Drools.java
package org.drools.core.util;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Drools {

    private static Pattern VERSION_PAT = Pattern.compile("(\\d+)\\.(\\d+)\\.(\\d+)([\\.-](.*))?");

    private static String droolsFullVersion;
    private static int droolsMajorVersion;
    private static int droolsMinorVersion;
    private static int droolsRevisionVersion;
    private static String droolsRevisionClassifier;

    static {
        droolsFullVersion = Drools.class.getPackage().getImplementationVersion();
        if (droolsFullVersion == null) {
            InputStream is = null;
            try {
                is = Drools.class.getClassLoader().getResourceAsStream("drools.versions.properties");
                Properties properties = new Properties();
                properties.load(is);
                droolsFullVersion = properties.get("drools.version").toString();
                is.close();
            } catch ( IOException e ) {
                throw new RuntimeException(e);
            } finally {
                if (is != null) {
                    try {
                        is.close();
                    } catch (IOException e) {
                        throw new RuntimeException(e);
                    }
                }
            }
        }

        Matcher m = VERSION_PAT.matcher(droolsFullVersion);
        if( m.matches() ) {
            droolsMajorVersion = Integer.parseInt(m.group(1));
            droolsMinorVersion = Integer.parseInt(m.group(2));
            droolsRevisionVersion = Integer.parseInt(m.group(3));
            droolsRevisionClassifier = m.group(5);
        }
    }

    public static String getFullVersion() {
        return droolsFullVersion;
    }

    public static int getMajorVersion() {
        return droolsMajorVersion;
    }

    public static int getMinorVersion() {
        return droolsMinorVersion;
    }

    public static int getRevisionVersion() {
        return droolsRevisionVersion;
    }

    public static String getRevisionClassifier() {
        return droolsRevisionClassifier;
    }

    public static boolean isCompatible(int major, int minor, int revision) {
        if (major != droolsMajorVersion) {
            return false;
        }
        // 6.0.x and 6.1+.x aren't compatible
        return minor == 0 ? droolsMinorVersion == 0 : droolsMinorVersion > 0;
    }
}


File: drools-core/src/main/java/org/drools/core/util/IoUtils.java
package org.drools.core.util;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.DatagramSocket;
import java.net.ServerSocket;
import java.nio.channels.FileChannel;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public class IoUtils {

    public static final Charset UTF8_CHARSET = Charset.forName("UTF-8");

    public static int findPort() {
        for( int i = 1024; i < 65535; i++) {
            if ( validPort( i ) ) {
                return i;
            }
        }
        throw new RuntimeException( "No valid port could be found" );
    }
    
    public static boolean validPort(int port) {

        ServerSocket ss = null;
        DatagramSocket ds = null;
        try {
            ss = new ServerSocket(port);
            ss.setReuseAddress(true);
            ds = new DatagramSocket(port);
            ds.setReuseAddress(true);
            return true;
        } catch (IOException e) {
        } finally {
            if (ds != null) {
                ds.close();
            }

            if (ss != null) {
                try {
                    ss.close();
                } catch (IOException e) {
                    /* should not be thrown */
                }
            }
        }

        return false;
    }

    public static String readFileAsString(File file) {
        StringBuffer sb = new StringBuffer();
        BufferedReader reader = null;
        try {
            reader = new BufferedReader(new InputStreamReader(new FileInputStream(file), IoUtils.UTF8_CHARSET));
            for (String line = reader.readLine(); line != null; line = reader.readLine()) {
                sb.append(line).append("\n");
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) { }
            }
        }
        return sb.toString();
    }

    public static void copyFile(File sourceFile, File destFile) {
        destFile.getParentFile().mkdirs();
        if(!destFile.exists()) {
            try {
                destFile.createNewFile();
            } catch (IOException ioe) {
                throw new RuntimeException("Unable to create file " + destFile.getAbsolutePath(), ioe);
            }
        }

        FileChannel source = null;
        FileChannel destination = null;

        try {
            source = new FileInputStream(sourceFile).getChannel();
            destination = new FileOutputStream(destFile).getChannel();
            destination.transferFrom(source, 0, source.size());
        } catch (IOException ioe) {
            throw new RuntimeException("Unable to copy " + sourceFile.getAbsolutePath() + " to " + destFile.getAbsolutePath(), ioe);
        } finally {
            if(source != null) {
                try {
                    source.close();
                } catch (IOException e) { }
            }
            if(destination != null) {
                try {
                    destination.close();
                } catch (IOException e) { }
            }
        }
    }
    
    public static Map<String, byte[]> indexZipFile(java.io.File jarFile) {
        Map<String, byte[]> files = new HashMap<String, byte[]>();
        ZipFile zipFile = null;
        try {
            zipFile = new ZipFile( jarFile );
            Enumeration< ? extends ZipEntry> entries = zipFile.entries();
            while ( entries.hasMoreElements() ) {
                ZipEntry entry = entries.nextElement();
                byte[] bytes = readBytesFromInputStream( zipFile.getInputStream( entry ) );
                files.put( entry.getName(),
                           bytes );
            }
        } catch ( IOException e ) {
            throw new RuntimeException( "Unable to get all ZipFile entries: " + jarFile, e );
        } finally {
            if ( zipFile != null ) {
                try {
                    zipFile.close();
                } catch ( IOException e ) {
                    throw new RuntimeException( "Unable to get all ZipFile entries: " + jarFile, e );
                }
            }
        }
        return files;
    }

    public static List<String> recursiveListFile(File folder) {
        return recursiveListFile(folder, "", Predicate.PassAll.INSTANCE);
    }

    public static List<String> recursiveListFile(File folder, String prefix, Predicate<? super File> filter) {
        List<String> files = new ArrayList<String>();
        for (File child : safeListFiles(folder)) {
            filesInFolder(files, child, prefix, filter);
        }
        return files;
    }

    private static void filesInFolder(List<String> files, File file, String relativePath, Predicate<? super File> filter) {
        if (file.isDirectory()) {
            relativePath += file.getName() + "/";
            for (File child : safeListFiles(file)) {
                filesInFolder(files, child, relativePath, filter);
            }
        } else {
            if (filter.apply(file)) {
                files.add(relativePath + file.getName());
            }
        }
    }

    /**
     * Returns {@link File#listFiles()} on a given file, avoids returning null when an IO error occurs.
     *
     * @param file directory whose files will be returned
     * @return {@link File#listFiles()}
     * @throws IllegalArgumentException when the file is a directory or cannot be accessed
     */
    private static File[] safeListFiles(final File file) {
        final File[] children = file.listFiles();
        if (children != null) {
            return children;
        } else {
            throw new IllegalArgumentException(String.format("Unable to retrieve contents of directory '%s'.",
                                                             file.getAbsolutePath()));
        }
    }

    public static byte[] readBytesFromInputStream(InputStream input) throws IOException {
        int length = input.available();
        byte[] buffer = new byte[Math.max(length, 8192)];
        ByteArrayOutputStream output = new ByteArrayOutputStream(buffer.length);

        if (length > 0) {
            int n = input.read(buffer);
            output.write(buffer, 0, n);
        }

        int n = 0;
        while (-1 != (n = input.read(buffer))) {
            output.write(buffer, 0, n);
        }
        return output.toByteArray();
    }
    
    public static byte[] readBytesFromZipEntry(File file, ZipEntry entry) throws IOException {
        if ( entry == null ) {
            return null;
        }

        ZipFile zipFile = null;
        byte[] bytes = null;
        try {
            zipFile = new ZipFile( file );
            bytes = IoUtils.readBytesFromInputStream(  zipFile.getInputStream( entry ) );
        } finally {
            if ( zipFile != null ) {
                zipFile.close();
            }
        }
        return bytes;

    }

    public static byte[] readBytes(File f) throws IOException {
        byte[] buf = new byte[1024];

        BufferedInputStream bais = null;
        ByteArrayOutputStream baos = null;
        try {
            bais = new BufferedInputStream( new FileInputStream( f ) );
            baos = new ByteArrayOutputStream();
            int len;
            while ( (len = bais.read( buf )) > 0 ) {
                baos.write( buf, 0, len );
            }
        } finally {
            if (  baos != null ) {
                baos.close();
            }
            if ( bais != null ) {
                bais.close();
            }
        }

        return baos.toByteArray();
    }

    public static void write(File f,
                             byte[] data) throws IOException {
        if ( f.exists() ) {
            // we want to make sure there is a time difference for lastModified and lastRead checks as Linux and http often round to seconds
            // http://saloon.javaranch.com/cgi-bin/ubb/ultimatebb.cgi?ubb=get_topic&f=1&t=019789
            try {
                Thread.sleep( 1000 );
            } catch ( Exception e ) {
                throw new RuntimeException( "Unable to sleep" );
            }
        }

        // Attempt to write the file
        writeBytes(f, data );

        // Now check the file was written and re-attempt if it was not
        // Need to do this for testing, to ensure the texts are read the same way, otherwise sometimes you get tail \n sometimes you don't
        int count = 0;
        while ( !areByteArraysEqual(data, readBytes( f ) ) && count < 5 ) {
            // The file failed to write, try 5 times, calling GC and sleep between each iteration
            // Sometimes windows takes a while to release a lock on a file
            System.gc();
            try {
                Thread.sleep( 250 );
            } catch ( InterruptedException e ) {
                throw new RuntimeException( "This should never happen" );
            }
            writeBytes(f, data );
            count++;
        }

        //areByteArraysEqual

        if ( count == 5 ) {
            throw new IOException( "Unable to write to file:" + f.getCanonicalPath() );
        }
    }

    public static void writeBytes(File f, byte[] data) throws IOException {
        byte[] buf = new byte[1024];

        BufferedOutputStream bos = null;
        ByteArrayInputStream bais = null;

        try {
            bos = new BufferedOutputStream( new FileOutputStream(f) );
            bais = new ByteArrayInputStream( data );
            int len;
            while ( (len = bais.read( buf )) > 0 ) {
                bos.write( buf, 0, len );
            }
        } finally {
            if (  bos != null ) {
                bos.close();
            }
            if ( bais != null ) {
                bais.close();
            }
        }
    }

    public static boolean areByteArraysEqual(byte[] b1,
                                             byte[] b2) {

        if ( b1.length != b2.length ) {
            return false;
        }

        for ( int i = 0, length = b1.length; i < length; i++ ) {
            if ( b1[i] != b2[i] ) {
                return false;
            }
        }

        return true;
    }

    public static String asSystemSpecificPath(String urlPath, int colonIndex) {
        String ic = urlPath.substring( Math.max( 0, colonIndex - 2 ), colonIndex + 1 );
        if  ( ic.matches( "\\/[A-Z]:" ) ) {
            return urlPath.substring( colonIndex - 2 );
        } else if  ( ic.matches( "[A-Z]:" ) ) {
            return urlPath.substring( colonIndex - 1 );
        } else {
            return urlPath.substring( colonIndex + 1 );
        }
    }
}


File: drools-core/src/main/java/org/drools/core/util/MemoryUtil.java
package org.drools.core.util;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryPoolMXBean;
import java.lang.management.MemoryUsage;

public class MemoryUtil {

    public static final MemoryStats permGenStats;

    private MemoryUtil() { }

    static {
        MemoryPoolMXBean permGenBean = null;
        for (MemoryPoolMXBean mx : ManagementFactory.getMemoryPoolMXBeans()) {
            if (mx.getName() != null && mx.getName().contains("Perm")) {
                permGenBean = mx;
                break;
            }
        }
        permGenStats = new MemoryStats(permGenBean);
    }

    public static class MemoryStats {
        private final MemoryPoolMXBean memoryBean;

        public MemoryStats(MemoryPoolMXBean memoryBean) {
            this.memoryBean = memoryBean;
        }

        public boolean isUsageThresholdExceeded(int threshold) {
            MemoryUsage memoryUsage = getMemoryUsage();
            return memoryUsage != null && memoryUsage.getUsed() * 100 / memoryUsage.getMax() >= threshold;
        }

        public MemoryUsage getMemoryUsage() {
            return memoryBean != null ? memoryBean.getUsage() : ManagementFactory.getMemoryMXBean().getNonHeapMemoryUsage();
        }
    }
}
