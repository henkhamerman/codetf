Refactoring Types: ['Move Class']
mber/runtime/android/AndroidObjectFactory.java
package cucumber.runtime.android;

import android.app.Instrumentation;
import android.content.Intent;
import android.test.ActivityInstrumentationTestCase2;
import android.test.AndroidTestCase;
import android.test.InstrumentationTestCase;
import cucumber.runtime.java.ObjectFactory;

/**
 * Android specific implementation of {@link cucumber.runtime.java.ObjectFactory} which will
 * make sure that created test classes have all necessary references to the executing {@link android.app.Instrumentation}
 * and the associated {@link android.content.Context}.
 */
public class AndroidObjectFactory implements ObjectFactory {

    /**
     * The actual {@link cucumber.runtime.java.ObjectFactory} responsible for creating instances.
     */
    private final ObjectFactory delegate;

    /**
     * The instrumentation to set to the objects.
     */
    private final Instrumentation instrumentation;

    /**
     * Creates a new instance using the given delegate {@link cucumber.runtime.java.ObjectFactory} to
     * forward all calls to and using the given {@link android.app.Instrumentation} to set to the instantiated
     * android test classes.
     *
     * @param delegate the {@link cucumber.runtime.java.ObjectFactory} to delegate to
     * @param instrumentation the {@link android.app.Instrumentation} to set to the tests
     */
    public AndroidObjectFactory(final ObjectFactory delegate, final Instrumentation instrumentation) {
        this.delegate = delegate;
        this.instrumentation = instrumentation;
    }

    @Override
    public void start() {
        delegate.start();
    }

    @Override
    public void stop() {
        delegate.stop();
    }

    @Override
    public void addClass(final Class<?> clazz) {
        delegate.addClass(clazz);
    }

    @Override
    public <T> T getInstance(final Class<T> type) {
        T instance = delegate.getInstance(type);
        decorate(instance);
        return instance;
    }

    private void decorate(final Object instance) {
        if (instance instanceof ActivityInstrumentationTestCase2) {
            final ActivityInstrumentationTestCase2 activityInstrumentationTestCase2 = (ActivityInstrumentationTestCase2) instance;
            activityInstrumentationTestCase2.injectInstrumentation(instrumentation);
            final Intent intent = new Intent();
            intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
            activityInstrumentationTestCase2.setActivityIntent(intent);
        } else if (instance instanceof InstrumentationTestCase) {
            ((InstrumentationTestCase) instance).injectInstrumentation(instrumentation);
        } else if (instance instanceof AndroidTestCase) {
            ((AndroidTestCase) instance).setContext(instrumentation.getTargetContext());
        }
    }
}


File: android/src/main/java/cucumber/runtime/android/CucumberExecutor.java
package cucumber.runtime.android;

import android.app.Instrumentation;
import android.content.Context;
import android.util.Log;
import cucumber.api.CucumberOptions;
import cucumber.api.StepDefinitionReporter;
import cucumber.runtime.Backend;
import cucumber.runtime.ClassFinder;
import cucumber.runtime.CucumberException;
import cucumber.runtime.Runtime;
import cucumber.runtime.RuntimeOptions;
import cucumber.runtime.RuntimeOptionsFactory;
import cucumber.runtime.io.ResourceLoader;
import cucumber.runtime.java.JavaBackend;
import cucumber.runtime.java.ObjectFactory;
import cucumber.runtime.model.CucumberFeature;
import dalvik.system.DexFile;
import gherkin.formatter.Formatter;
import gherkin.formatter.Reporter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * Executes the cucumber scnearios.
 */
public class CucumberExecutor {

    /**
     * The logcat tag to log all cucumber related information to.
     */
    public static final String TAG = "cucumber-android";

    /**
     * The system property name of the cucumber options.
     */
    public static final String CUCUMBER_OPTIONS_SYSTEM_PROPERTY = "cucumber.options";

    /**
     * The instrumentation to report to.
     */
    private final Instrumentation instrumentation;

    /**
     * The {@link java.lang.ClassLoader} for all test relevant classes.
     */
    private final ClassLoader classLoader;

    /**
     * The {@link cucumber.runtime.ClassFinder} to find all to be loaded classes.
     */
    private final ClassFinder classFinder;

    /**
     * The {@link cucumber.runtime.RuntimeOptions} to get the {@link CucumberFeature}s from.
     */
    private final RuntimeOptions runtimeOptions;

    /**
     * The {@link cucumber.runtime.Runtime} to run with.
     */
    private final Runtime runtime;

    /**
     * The actual {@link CucumberFeature}s to run.
     */
    private final List<CucumberFeature> cucumberFeatures;

    /**
     * Creates a new instance for the given parameters.
     *
     * @param arguments       the {@link cucumber.runtime.android.Arguments} which configure this execution
     * @param instrumentation the {@link android.app.Instrumentation} to report to
     */
    public CucumberExecutor(final Arguments arguments, final Instrumentation instrumentation) {

        trySetCucumberOptionsToSystemProperties(arguments);

        final Context context = instrumentation.getContext();
        this.instrumentation = instrumentation;
        this.classLoader = context.getClassLoader();
        this.classFinder = createDexClassFinder(context);
        this.runtimeOptions = createRuntimeOptions(context);

        ResourceLoader resourceLoader = new AndroidResourceLoader(context);
        this.runtime = new Runtime(resourceLoader, classLoader, createBackends(), runtimeOptions);
        this.cucumberFeatures = runtimeOptions.cucumberFeatures(resourceLoader);
    }

    /**
     * Runs the cucumber scenarios with the specified arguments.
     */
    public void execute() {

        runtimeOptions.addPlugin(new AndroidInstrumentationReporter(runtime, instrumentation, getNumberOfConcreteScenarios()));
        runtimeOptions.addPlugin(new AndroidLogcatReporter(runtime, TAG));

        // TODO: This is duplicated in info.cucumber.Runtime.

        final Reporter reporter = runtimeOptions.reporter(classLoader);
        final Formatter formatter = runtimeOptions.formatter(classLoader);

        final StepDefinitionReporter stepDefinitionReporter = runtimeOptions.stepDefinitionReporter(classLoader);
        runtime.getGlue().reportStepDefinitions(stepDefinitionReporter);

        for (final CucumberFeature cucumberFeature : cucumberFeatures) {
            cucumberFeature.run(formatter, reporter, runtime);
        }

        formatter.done();
        formatter.close();
    }

    /**
     * @return the number of actual scenarios, including outlined
     */
    public int getNumberOfConcreteScenarios() {
        return ScenarioCounter.countScenarios(cucumberFeatures);
    }

    private void trySetCucumberOptionsToSystemProperties(final Arguments arguments) {
        final String cucumberOptions = arguments.getCucumberOptions();
        if (!cucumberOptions.isEmpty()) {
            Log.d(TAG, "Setting cucumber.options from arguments: '" + cucumberOptions + "'");
            System.setProperty(CUCUMBER_OPTIONS_SYSTEM_PROPERTY, cucumberOptions);
        }
    }

    private ClassFinder createDexClassFinder(final Context context) {
        final String apkPath = context.getPackageCodePath();
        return new DexClassFinder(newDexFile(apkPath));
    }

    private DexFile newDexFile(final String apkPath) {
        try {
            return new DexFile(apkPath);
        } catch (final IOException e) {
            throw new CucumberException("Failed to open " + apkPath);
        }
    }

    private RuntimeOptions createRuntimeOptions(final Context context) {
        for (final Class<?> clazz : classFinder.getDescendants(Object.class, context.getPackageName())) {
            if (clazz.isAnnotationPresent(CucumberOptions.class)) {
                Log.d(TAG, "Found CucumberOptions in class " + clazz.getName());
                final RuntimeOptionsFactory factory = new RuntimeOptionsFactory(clazz);
                return factory.create();
            }
        }

        throw new CucumberException("No CucumberOptions annotation");
    }

    private Collection<? extends Backend> createBackends() {
        final ObjectFactory delegateObjectFactory = JavaBackend.loadObjectFactory(classFinder);
        final AndroidObjectFactory objectFactory = new AndroidObjectFactory(delegateObjectFactory, instrumentation);
        final List<Backend> backends = new ArrayList<Backend>();
        backends.add(new JavaBackend(objectFactory, classFinder));
        return backends;
    }
}


File: android/src/main/java/cucumber/runtime/android/DexClassFinder.java
package cucumber.runtime.android;

import cucumber.runtime.ClassFinder;
import cucumber.runtime.CucumberException;
import dalvik.system.DexFile;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Enumeration;
import java.util.List;

/**
 * Android specific implementation of {@link cucumber.runtime.ClassFinder} which loads classes contained in the provided {@link dalvik.system.DexFile}.
 */
public class DexClassFinder implements ClassFinder {

    /**
     * Symbol name of the manifest class.
     */
    private static final String MANIFEST_CLASS_NAME = "Manifest";

    /**
     * Symbol name of the resource class.
     */
    private static final String RESOURCE_CLASS_NAME = "R";

    /**
     * Symbol name prefix of any inner class of the resource class.
     */
    private static final String RESOURCE_INNER_CLASS_NAME_PREFIX = "R$";

    /**
     * The file name separator.
     */
    private static final String FILE_NAME_SEPARATOR = ".";

    /**
     * The class loader to actually load the classes specified by the {@link dalvik.system.DexFile}.
     */
    private static final ClassLoader CLASS_LOADER = DexClassFinder.class.getClassLoader();

    /**
     * The "symbol" representing the default package.
     */
    private static final String DEFAULT_PACKAGE = "";

    /**
     * The {@link dalvik.system.DexFile} to load classes from
     */
    private final DexFile dexFile;

    /**
     * Creates a new instance for the given parameter.
     *
     * @param dexFile the {@link dalvik.system.DexFile} to load classes from
     */
    public DexClassFinder(final DexFile dexFile) {
        this.dexFile = dexFile;
    }

    @Override
    public <T> Collection<Class<? extends T>> getDescendants(final Class<T> parentType, final String packageName) {
        final List<Class<? extends T>> result = new ArrayList<Class<? extends T>>();

        final Enumeration<String> entries = dexFile.entries();
        while (entries.hasMoreElements()) {
            final String className = entries.nextElement();
            if (isInPackage(className, packageName) && !isGenerated(className)) {
                final Class<? extends T> clazz = loadClass(className);
                if (clazz != null && !parentType.equals(clazz) && parentType.isAssignableFrom(clazz)) {
                    result.add(clazz.asSubclass(parentType));
                }
            }
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private <T> Class<? extends T> loadClass(final String className) {
        try {
            return (Class<? extends T>) Class.forName(className, false, CLASS_LOADER);
        } catch (final ClassNotFoundException e) {
            throw new CucumberException(e);
        }
    }

    private boolean isInPackage(final String className, final String packageName) {
        final int lastDotIndex = className.lastIndexOf(FILE_NAME_SEPARATOR);
        final String classPackage = lastDotIndex == -1 ? DEFAULT_PACKAGE : className.substring(0, lastDotIndex);
        return classPackage.startsWith(packageName);
    }

    private boolean isGenerated(final String className) {
        final int lastDotIndex = className.lastIndexOf(FILE_NAME_SEPARATOR);
        final String shortName = lastDotIndex == -1 ? className : className.substring(lastDotIndex + 1);
        return shortName.equals(MANIFEST_CLASS_NAME) || shortName.equals(RESOURCE_CLASS_NAME) || shortName.startsWith(RESOURCE_INNER_CLASS_NAME_PREFIX);
    }
}


File: android/src/test/java/cucumber/runtime/android/AndroidObjectFactoryTest.java
package cucumber.runtime.android;

import android.app.Instrumentation;
import android.content.Context;
import android.content.Intent;
import android.test.ActivityInstrumentationTestCase2;
import android.test.AndroidTestCase;
import android.test.InstrumentationTestCase;
import cucumber.runtime.java.ObjectFactory;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@RunWith(RobolectricTestRunner.class)
@Config(emulateSdk = 16, manifest = Config.NONE)
public class AndroidObjectFactoryTest {

    private final ObjectFactory delegate = mock(ObjectFactory.class);
    private final Instrumentation instrumentation = mock(Instrumentation.class);
    private final AndroidObjectFactory androidObjectFactory = new AndroidObjectFactory(delegate, instrumentation);

    @Test
    public void delegates_start_call() {

        // when
        androidObjectFactory.start();

        // then
        verify(delegate).start();
    }

    @Test
    public void delegates_stop_call() {

        // when
        androidObjectFactory.stop();

        // then
        verify(delegate).stop();
    }

    @Test
    public void delegates_addClass_call() {

        // given
        final Class<?> someClass = String.class;

        // when
        androidObjectFactory.addClass(someClass);

        // then
        verify(delegate).addClass(String.class);
    }

    @Test
    public void delegates_getInstance_call() {

        // given
        final Class<?> someClass = String.class;

        // when
        androidObjectFactory.getInstance(someClass);

        // then
        verify(delegate).getInstance(someClass);

    }

    @Test
    public void injects_instrumentation_into_ActivityInstrumentationTestCase2() {

        // given
        final Class<?> activityInstrumentationTestCase2Class = ActivityInstrumentationTestCase2.class;
        final ActivityInstrumentationTestCase2 activityInstrumentationTestCase2 = mock(ActivityInstrumentationTestCase2.class);
        when(delegate.getInstance(activityInstrumentationTestCase2Class)).thenReturn(activityInstrumentationTestCase2);

        // when
        androidObjectFactory.getInstance(activityInstrumentationTestCase2Class);

        // then
        verify(activityInstrumentationTestCase2).injectInstrumentation(instrumentation);
    }

    @Test
    public void sets_activity_intent_with_FLAG_ACTIVITY_CLEAR_TOP_to_prevent_stalling_when_calling_getActivity_if_the_activity_is_already_running() {

        // given
        final Class<?> activityInstrumentationTestCase2Class = ActivityInstrumentationTestCase2.class;
        final ActivityInstrumentationTestCase2 activityInstrumentationTestCase2 = mock(ActivityInstrumentationTestCase2.class);
        when(delegate.getInstance(activityInstrumentationTestCase2Class)).thenReturn(activityInstrumentationTestCase2);
        final Intent intent = new Intent().addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);

        // when
        androidObjectFactory.getInstance(activityInstrumentationTestCase2Class);

        // then
        verify(activityInstrumentationTestCase2).setActivityIntent(intent);
    }

    @Test
    public void injects_instrumentation_into_InstrumentationTestCase() {

        // given
        final Class<?> instrumentationTestCaseClass = InstrumentationTestCase.class;
        final InstrumentationTestCase instrumentationTestCase = mock(InstrumentationTestCase.class);
        when(delegate.getInstance(instrumentationTestCaseClass)).thenReturn(instrumentationTestCase);

        // when
        androidObjectFactory.getInstance(instrumentationTestCaseClass);

        // then
        verify(instrumentationTestCase).injectInstrumentation(instrumentation);
    }

    @Test
    public void injects_instrumentation_context_into_AndroidTestCase() {

        // given
        final Class<?> androidTestCaseClass = AndroidTestCase.class;
        final AndroidTestCase androidTestCase = mock(AndroidTestCase.class);
        when(delegate.getInstance(androidTestCaseClass)).thenReturn(androidTestCase);
        final Context context = mock(Context.class);
        when(instrumentation.getTargetContext()).thenReturn(context);

        // when
        androidObjectFactory.getInstance(androidTestCaseClass);

        // then
        verify(androidTestCase).setContext(context);

    }
}

File: core/src/main/java/cucumber/runtime/ClassFinder.java
package cucumber.runtime;

import java.util.Collection;

public interface ClassFinder {
    <T> Collection<Class<? extends T>> getDescendants(Class<T> parentType, String packageName);
}


File: core/src/main/java/cucumber/runtime/Env.java
package cucumber.runtime;

import java.util.MissingResourceException;
import java.util.Properties;
import java.util.ResourceBundle;

/**
 * Looks up values in the following order:
 * <ol>
 * <li>Environment variable</li>
 * <li>System property</li>
 * <li>Resource bundle</li>
 * </ol>
 */
public class Env {
    private final String bundleName;
    private final Properties properties;

    public Env() {
        this(null, System.getProperties());
    }

    public Env(String bundleName) {
        this(bundleName, System.getProperties());
    }

    public Env(Properties properties) {
        this(null, properties);
    }

    public Env(String bundleName, Properties properties) {
        this.bundleName = bundleName;
        this.properties = properties;
    }

    public String get(String key) {
        String result = getFromEnvironment(key);
        if (result == null) {
            result = getFromProperty(key);
            if (result == null && bundleName != null) {
                result = getFromBundle(key);
            }
        }
        return result;
    }

    private String getFromEnvironment(String key) {
        String value = System.getenv(asEnvKey(key));
        if (value == null) {
            value = System.getenv(asPropertyKey(key));
        }
        return value;
    }

    private String getFromProperty(String key) {
        String value = properties.getProperty(asEnvKey(key));
        if (value == null) {
            value = properties.getProperty(asPropertyKey(key));
        }
        return value;
    }

    private String getFromBundle(String key) {
        try {
            ResourceBundle bundle = ResourceBundle.getBundle(bundleName);
            try {
                return bundle.getString(asEnvKey(key));
            } catch (MissingResourceException stringNotFound) {
                try {
                    return bundle.getString(asPropertyKey(key));
                } catch (MissingResourceException ignoreStringNotFound) {
                    return bundle.getString(asPropertyKey(key));
                }
            }
        } catch (MissingResourceException ignoreBundleNotFound) {
            return null;
        }
    }

    public String get(String key, String defaultValue) {
        String result = get(key);
        return result != null ? result : defaultValue;
    }

    private static String asEnvKey(String key) {
        return key.replace('.', '_').toUpperCase();
    }

    private static String asPropertyKey(String key) {
        return key.replace('_', '.').toLowerCase();
    }
}


File: core/src/main/java/cucumber/runtime/RuntimeOptions.java
package cucumber.runtime;

import cucumber.api.SnippetType;
import cucumber.api.StepDefinitionReporter;
import cucumber.api.SummaryPrinter;
import cucumber.runtime.formatter.ColorAware;
import cucumber.runtime.formatter.PluginFactory;
import cucumber.runtime.formatter.StrictAware;
import cucumber.runtime.io.ResourceLoader;
import cucumber.runtime.model.CucumberFeature;
import cucumber.runtime.model.PathWithLines;
import gherkin.I18n;
import gherkin.formatter.Formatter;
import gherkin.formatter.Reporter;
import gherkin.util.FixJava;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.List;
import java.util.ResourceBundle;
import java.util.regex.Pattern;

import static cucumber.runtime.model.CucumberFeature.load;

// IMPORTANT! Make sure USAGE.txt is always uptodate if this class changes.
public class RuntimeOptions {
    public static final String VERSION = ResourceBundle.getBundle("cucumber.version").getString("cucumber-jvm.version");
    public static final String USAGE = FixJava.readResource("/cucumber/api/cli/USAGE.txt");

    private final List<String> glue = new ArrayList<String>();
    private final List<Object> filters = new ArrayList<Object>();
    private final List<String> featurePaths = new ArrayList<String>();
    private final List<String> pluginFormatterNames = new ArrayList<String>();
    private final List<String> pluginStepDefinitionReporterNames = new ArrayList<String>();
    private final List<String> pluginSummaryPrinterNames = new ArrayList<String>();
    private final PluginFactory pluginFactory;
    private final List<Object> plugins = new ArrayList<Object>();
    private boolean dryRun;
    private boolean strict = false;
    private boolean monochrome = false;
    private SnippetType snippetType = SnippetType.UNDERSCORE;
    private boolean pluginNamesInstantiated;

    /**
     * Create a new instance from a string of options, for example:
     * <p/>
     * <pre<{@code "--name 'the fox' --plugin pretty --strict"}</pre>
     *
     * @param argv the arguments
     */
    public RuntimeOptions(String argv) {
        this(new PluginFactory(), Shellwords.parse(argv));
    }

    /**
     * Create a new instance from a list of options, for example:
     * <p/>
     * <pre<{@code Arrays.asList("--name", "the fox", "--plugin", "pretty", "--strict");}</pre>
     *
     * @param argv the arguments
     */
    public RuntimeOptions(List<String> argv) {
        this(new PluginFactory(), argv);
    }

    public RuntimeOptions(Env env, List<String> argv) {
        this(env, new PluginFactory(), argv);
    }

    public RuntimeOptions(PluginFactory pluginFactory, List<String> argv) {
        this(new Env("cucumber"), pluginFactory, argv);
    }

    public RuntimeOptions(Env env, PluginFactory pluginFactory, List<String> argv) {
        this.pluginFactory = pluginFactory;

        argv = new ArrayList<String>(argv); // in case the one passed in is unmodifiable.
        parse(argv);

        String cucumberOptionsFromEnv = env.get("cucumber.options");
        if (cucumberOptionsFromEnv != null) {
            parse(Shellwords.parse(cucumberOptionsFromEnv));
        }

        if (pluginFormatterNames.isEmpty()) {
            pluginFormatterNames.add("progress");
        }
        if (pluginSummaryPrinterNames.isEmpty()) {
            pluginSummaryPrinterNames.add("default_summary");
        }
    }

    private void parse(List<String> args) {
        List<Object> parsedFilters = new ArrayList<Object>();
        List<String> parsedFeaturePaths = new ArrayList<String>();
        List<String> parsedGlue = new ArrayList<String>();

        while (!args.isEmpty()) {
            String arg = args.remove(0).trim();

            if (arg.equals("--help") || arg.equals("-h")) {
                printUsage();
                System.exit(0);
            } else if (arg.equals("--version") || arg.equals("-v")) {
                System.out.println(VERSION);
                System.exit(0);
            } else if (arg.equals("--i18n")) {
                String nextArg = args.remove(0);
                System.exit(printI18n(nextArg));
            } else if (arg.equals("--glue") || arg.equals("-g")) {
                String gluePath = args.remove(0);
                parsedGlue.add(gluePath);
            } else if (arg.equals("--tags") || arg.equals("-t")) {
                parsedFilters.add(args.remove(0));
            } else if (arg.equals("--plugin") || arg.equals("-p")) {
                addPluginName(args.remove(0));
            } else if (arg.equals("--format") || arg.equals("-f")) {
                System.err.println("WARNING: Cucumber-JVM's --format option is deprecated. Please use --plugin instead.");
                addPluginName(args.remove(0));
            } else if (arg.equals("--no-dry-run") || arg.equals("--dry-run") || arg.equals("-d")) {
                dryRun = !arg.startsWith("--no-");
            } else if (arg.equals("--no-strict") || arg.equals("--strict") || arg.equals("-s")) {
                strict = !arg.startsWith("--no-");
            } else if (arg.equals("--no-monochrome") || arg.equals("--monochrome") || arg.equals("-m")) {
                monochrome = !arg.startsWith("--no-");
            } else if (arg.equals("--snippets")) {
                String nextArg = args.remove(0);
                snippetType = SnippetType.fromString(nextArg);
            } else if (arg.equals("--name") || arg.equals("-n")) {
                String nextArg = args.remove(0);
                Pattern patternFilter = Pattern.compile(nextArg);
                parsedFilters.add(patternFilter);
            } else if (arg.startsWith("-")) {
                printUsage();
                throw new CucumberException("Unknown option: " + arg);
            } else {
                parsedFeaturePaths.add(arg);
            }
        }
        if (!parsedFilters.isEmpty() || haveLineFilters(parsedFeaturePaths)) {
            filters.clear();
            filters.addAll(parsedFilters);
            if (parsedFeaturePaths.isEmpty() && !featurePaths.isEmpty()) {
                stripLinesFromFeaturePaths(featurePaths);
            }
        }
        if (!parsedFeaturePaths.isEmpty()) {
            featurePaths.clear();
            featurePaths.addAll(parsedFeaturePaths);
        }
        if (!parsedGlue.isEmpty()) {
            glue.clear();
            glue.addAll(parsedGlue);
        }
    }

    private void addPluginName(String name) {
        if (PluginFactory.isFormatterName(name)) {
            pluginFormatterNames.add(name);
        } else if (PluginFactory.isStepDefinitionResporterName(name)) {
            pluginStepDefinitionReporterNames.add(name);
        } else if (PluginFactory.isSummaryPrinterName(name)) {
            pluginSummaryPrinterNames.add(name);
        } else {
            throw new CucumberException("Unrecognized plugin: " + name);
        }
    }

    private boolean haveLineFilters(List<String> parsedFeaturePaths) {
        for (String pathName : parsedFeaturePaths) {
            if (pathName.startsWith("@") || PathWithLines.hasLineFilters(pathName)) {
                return true;
            }
        }
        return false;
    }

    private void stripLinesFromFeaturePaths(List<String> featurePaths) {
        List<String> newPaths = new ArrayList<String>();
        for (String pathName : featurePaths) {
            newPaths.add(PathWithLines.stripLineFilters(pathName));
        }
        featurePaths.clear();
        featurePaths.addAll(newPaths);
    }

    private void printUsage() {
        System.out.println(USAGE);
    }

    private int printI18n(String language) {
        List<I18n> all = I18n.getAll();

        if (language.equalsIgnoreCase("help")) {
            for (I18n i18n : all) {
                System.out.println(i18n.getIsoCode());
            }
            return 0;
        } else {
            return printKeywordsFor(language, all);
        }
    }

    private int printKeywordsFor(String language, List<I18n> all) {
        for (I18n i18n : all) {
            if (i18n.getIsoCode().equalsIgnoreCase(language)) {
                System.out.println(i18n.getKeywordTable());
                return 0;
            }
        }

        System.err.println("Unrecognised ISO language code");
        return 1;
    }

    public List<CucumberFeature> cucumberFeatures(ResourceLoader resourceLoader) {
        return load(resourceLoader, featurePaths, filters, System.out);
    }

    List<Object> getPlugins() {
        if (!pluginNamesInstantiated) {
            for (String pluginName : pluginFormatterNames) {
                Object plugin = pluginFactory.create(pluginName);
                plugins.add(plugin);
                setMonochromeOnColorAwarePlugins(plugin);
                setStrictOnStrictAwarePlugins(plugin);
            }
            for (String pluginName : pluginStepDefinitionReporterNames) {
                Object plugin = pluginFactory.create(pluginName);
                plugins.add(plugin);
            }
            for (String pluginName : pluginSummaryPrinterNames) {
                Object plugin = pluginFactory.create(pluginName);
                plugins.add(plugin);
            }
            pluginNamesInstantiated = true;
        }
        return plugins;
    }

    public Formatter formatter(ClassLoader classLoader) {
        return pluginProxy(classLoader, Formatter.class);
    }

    public Reporter reporter(ClassLoader classLoader) {
        return pluginProxy(classLoader, Reporter.class);
    }

    public StepDefinitionReporter stepDefinitionReporter(ClassLoader classLoader) {
        return pluginProxy(classLoader, StepDefinitionReporter.class);
    }

    public SummaryPrinter summaryPrinter(ClassLoader classLoader) {
        return pluginProxy(classLoader, SummaryPrinter.class);
    }

    /**
     * Creates a dynamic proxy that multiplexes method invocations to all plugins of the same type.
     *
     * @param classLoader used to create the proxy
     * @param type        proxy type
     * @param <T>         generic proxy type
     * @return a proxy
     */
    public <T> T pluginProxy(ClassLoader classLoader, final Class<T> type) {
        Object proxy = Proxy.newProxyInstance(classLoader, new Class<?>[]{type}, new InvocationHandler() {
            @Override
            public Object invoke(Object target, Method method, Object[] args) throws Throwable {
                for (Object plugin : getPlugins()) {
                    if (type.isInstance(plugin)) {
                        try {
                            Utils.invoke(plugin, method, 0, args);
                        } catch (Throwable t) {
                            if (!method.getName().equals("startOfScenarioLifeCycle") && !method.getName().equals("endOfScenarioLifeCycle")) {
                                // IntelliJ has its own formatter which doesn't yet implement these methods.
                                throw t;
                            }
                        }
                    }
                }
                return null;
            }
        });
        return type.cast(proxy);
    }

    private void setMonochromeOnColorAwarePlugins(Object plugin) {
        if (plugin instanceof ColorAware) {
            ColorAware colorAware = (ColorAware) plugin;
            colorAware.setMonochrome(monochrome);
        }
    }

    private void setStrictOnStrictAwarePlugins(Object plugin) {
        if (plugin instanceof StrictAware) {
            StrictAware strictAware = (StrictAware) plugin;
            strictAware.setStrict(strict);
        }
    }

    public List<String> getGlue() {
        return glue;
    }

    public boolean isStrict() {
        return strict;
    }

    public boolean isDryRun() {
        return dryRun;
    }

    public List<String> getFeaturePaths() {
        return featurePaths;
    }

    public void addPlugin(Object plugin) {
        plugins.add(plugin);
    }

    public List<Object> getFilters() {
        return filters;
    }

    public boolean isMonochrome() {
        return monochrome;
    }

    public SnippetType getSnippetType() {
        return snippetType;
    }
}


File: core/src/main/java/cucumber/runtime/io/ResourceLoaderClassFinder.java
package cucumber.runtime.io;

import cucumber.runtime.ClassFinder;

import java.io.File;
import java.util.Collection;
import java.util.HashSet;

public class ResourceLoaderClassFinder implements ClassFinder {
    private final ResourceLoader resourceLoader;
    private final ClassLoader classLoader;

    public ResourceLoaderClassFinder(ResourceLoader resourceLoader, ClassLoader classLoader) {
        this.resourceLoader = resourceLoader;
        this.classLoader = classLoader;
    }

    @Override
    public <T> Collection<Class<? extends T>> getDescendants(Class<T> parentType, String packageName) {
        Collection<Class<? extends T>> result = new HashSet<Class<? extends T>>();
        String packagePath = "classpath:" + packageName.replace('.', '/').replace(File.separatorChar, '/');
        for (Resource classResource : resourceLoader.resources(packagePath, ".class")) {
            String className = classResource.getClassName(".class");
            Class<?> clazz = loadClass(className, classLoader);
            if (clazz != null && !parentType.equals(clazz) && parentType.isAssignableFrom(clazz)) {
                result.add(clazz.asSubclass(parentType));
            }
        }
        return result;
    }

    private Class<?> loadClass(String className, ClassLoader classLoader) {
        try {
            return classLoader.loadClass(className);
        } catch (ClassNotFoundException ignore) {
            return null;
        } catch (NoClassDefFoundError ignore) {
            return null;
        }
    }
}


File: core/src/test/java/cucumber/runtime/EnvTest.java
package cucumber.runtime;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;

public class EnvTest {

    private Env env = new Env("env-test");

    @Test
    public void looks_up_value_from_environment() {
        assertNotNull(env.get("PATH"));
    }

    @Test
    public void returns_null_for_absent_key() {
        assertNull(env.get("pxfj54#"));
    }

    @Test
    public void looks_up_value_from_system_properties() {
        try {
            System.setProperty("env.test", "from-props");
            assertEquals("from-props", env.get("env.test"));
            assertEquals("from-props", env.get("ENV_TEST"));
        } finally {
            System.getProperties().remove("env.test");
        }
    }

    @Test
    public void looks_up_dotted_value_from_resource_bundle_with_dots() {
        assertEquals("a.b", env.get("a.b"));
    }

    @Test
    public void looks_up_dotted_value_from_resource_bundle_with_underscores() {
        assertEquals("a.b", env.get("A_B"));
    }

    @Test
    public void looks_up_underscored_value_from_resource_bundle_with_dots() {
        assertEquals("B_C", env.get("b.c"));
    }

    @Test
    public void looks_up_underscored_value_from_resource_bundle_with_underscores() {
        assertEquals("B_C", env.get("B_C"));
    }
}


File: guice/src/main/java/cucumber/runtime/java/guice/impl/GuiceFactory.java
package cucumber.runtime.java.guice.impl;

import com.google.inject.Injector;
import cucumber.runtime.java.ObjectFactory;
import cucumber.runtime.java.guice.ScenarioScope;

import java.io.IOException;

/**
 * Guice implementation of the <code>cucumber.runtime.java.ObjectFactory</code>.
 */
public class GuiceFactory implements ObjectFactory {

    private final Injector injector;

    /**
     * This constructor is called reflectively by cucumber.runtime.Refections.
     * @throws IOException if a <code>cucumber-guice.properties</code> file is in the root of the classpath and it
     * cannot be loaded.
     */
    public GuiceFactory() throws IOException {
        this(new InjectorSourceFactory(PropertiesLoader.loadGuiceProperties()).create().getInjector());
    }

    /**
     * Package private constructor that is called by the public constructor at runtime and is also called directly by
     * tests.
     * @param injector an injector configured with a binding for <code>cucumber.runtime.java.guice.ScenarioScope</code>.
     */
    GuiceFactory(Injector injector) {
        this.injector = injector;
    }

    public void addClass(Class<?> clazz) {}

    public void start() {
        injector.getInstance(ScenarioScope.class).enterScope();
    }

    public void stop() {
        injector.getInstance(ScenarioScope.class).exitScope();
    }

    public <T> T getInstance(Class<T> clazz) {
        return injector.getInstance(clazz);
    }

}


File: guice/src/test/java/cucumber/runtime/java/guice/impl/GuiceFactoryTest.java
package cucumber.runtime.java.guice.impl;

import com.google.inject.*;
import cucumber.api.guice.CucumberModules;
import cucumber.api.guice.CucumberScopes;
import cucumber.runtime.java.ObjectFactory;
import cucumber.runtime.java.guice.ScenarioScoped;
import org.junit.After;
import org.junit.Test;

import javax.inject.Singleton;
import java.util.Arrays;
import java.util.List;

import static cucumber.runtime.java.guice.matcher.ElementsAreAllEqualMatcher.elementsAreAllEqual;
import static cucumber.runtime.java.guice.matcher.ElementsAreAllUniqueMatcher.elementsAreAllUnique;
import static org.hamcrest.CoreMatchers.containsString;
import static org.hamcrest.CoreMatchers.notNullValue;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.fail;

public class GuiceFactoryTest {

    private ObjectFactory factory;
    private List<?> instancesFromSameScenario;
    private List<?> instancesFromDifferentScenarios;

    @After
    public void tearDown() {
        // If factory is left in start state it can cause cascading failures due to scope being left open
        try { factory.stop(); } catch (Exception e) {}
    }

    @Test
    public void factoryCanBeIntantiatedWithDefaultConstructor() throws Exception {
        factory = new GuiceFactory();
        assertThat(factory, notNullValue());
    }

    @Test
    public void factoryCanBeIntantiatedWithArgConstructor() {
        factory = new GuiceFactory(Guice.createInjector());
        assertThat(factory, notNullValue());
    }

    @Test
    public void factoryStartFailsIfScenarioScopeIsNotBound() {
        factory = new GuiceFactory(Guice.createInjector());
        try {
            factory.start();
            fail();
        } catch (ConfigurationException e) {
            assertThat(e.getMessage(),
                    containsString("No implementation for cucumber.runtime.java.guice.ScenarioScope was bound"));
        }
    }

    static class UnscopedClass {}

    @Test
    public void shouldGiveNewInstancesOfUnscopedClassWithinAScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO));
        instancesFromSameScenario = getInstancesFromSameScenario(factory, UnscopedClass.class);
        assertThat(instancesFromSameScenario, elementsAreAllUnique());
    }

    @Test
    public void shouldGiveNewInstanceOfUnscopedClassForEachScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO));
        instancesFromDifferentScenarios = getInstancesFromDifferentScenarios(factory, UnscopedClass.class);
        assertThat(instancesFromDifferentScenarios, elementsAreAllUnique());
    }

    @ScenarioScoped static class AnnotatedScenarioScopedClass {}

    @Test
    public void shouldGiveTheSameInstanceOfAnnotatedScenarioScopedClassWithinAScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO));
        instancesFromSameScenario = getInstancesFromSameScenario(factory, AnnotatedScenarioScopedClass.class);
        assertThat(instancesFromSameScenario, elementsAreAllEqual());
    }

    @Test
    public void shouldGiveNewInstanceOfAnnotatedScenarioScopedClassForEachScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO));
        instancesFromDifferentScenarios = getInstancesFromDifferentScenarios(factory, AnnotatedScenarioScopedClass.class);
        assertThat(instancesFromDifferentScenarios, elementsAreAllUnique());
    }

    @Singleton static class AnnotatedSingletonClass {}

    @Test
    public void shouldGiveTheSameInstanceOfAnnotatedSingletonClassWithinAScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO));
        instancesFromSameScenario = getInstancesFromSameScenario(factory, AnnotatedSingletonClass.class);
        assertThat(instancesFromSameScenario, elementsAreAllEqual());
    }

    @Test
    public void shouldGiveTheSameInstanceOfAnnotatedSingletonClassForEachScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO));
        instancesFromDifferentScenarios = getInstancesFromDifferentScenarios(factory, AnnotatedSingletonClass.class);
        assertThat(instancesFromDifferentScenarios, elementsAreAllEqual());
    }

    static class BoundScenarioScopedClass {}

    final AbstractModule boundScenarioScopedClassModule = new AbstractModule() {
        @Override protected void configure() {
            bind(BoundScenarioScopedClass.class).in(CucumberScopes.SCENARIO);
        }
    };

    @Test
    public void shouldGiveTheSameInstanceOfBoundScenarioScopedClassWithinAScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO, boundScenarioScopedClassModule));
        instancesFromSameScenario = getInstancesFromSameScenario(factory, BoundScenarioScopedClass.class);
        assertThat(instancesFromSameScenario, elementsAreAllEqual());
    }

    @Test
    public void shouldGiveNewInstanceOfBoundScenarioScopedClassForEachScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO, boundScenarioScopedClassModule));
        instancesFromDifferentScenarios = getInstancesFromDifferentScenarios(factory, BoundScenarioScopedClass.class);
        assertThat(instancesFromDifferentScenarios, elementsAreAllUnique());
    }

    static class BoundSingletonClass {}

    final AbstractModule boundSingletonClassModule = new AbstractModule() {
        @Override protected void configure() {
            bind(BoundSingletonClass.class).in(Scopes.SINGLETON);
        }
    };

    @Test
    public void shouldGiveTheSameInstanceOfBoundSingletonClassWithinAScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO, boundSingletonClassModule));
        instancesFromSameScenario = getInstancesFromSameScenario(factory, BoundSingletonClass.class);
        assertThat(instancesFromSameScenario, elementsAreAllEqual());
    }

    @Test
    public void shouldGiveTheSameInstanceOfBoundSingletonClassForEachScenario() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO, boundSingletonClassModule));
        instancesFromDifferentScenarios = getInstancesFromDifferentScenarios(factory, BoundSingletonClass.class);
        assertThat(instancesFromDifferentScenarios, elementsAreAllEqual());
    }

    @Test
    public void shouldGiveNewInstanceOfAnnotatedSingletonClassForEachScenarioWhenOverridingModuleBindingIsScenarioScope() {
        factory = new GuiceFactory(injector(CucumberModules.SCENARIO, new AbstractModule() {
            @Override
            protected void configure() {
                bind(AnnotatedSingletonClass.class).in(CucumberScopes.SCENARIO);
            }
        }));
        instancesFromDifferentScenarios = getInstancesFromDifferentScenarios(factory, AnnotatedSingletonClass.class);
        assertThat(instancesFromDifferentScenarios, elementsAreAllUnique());
    }

    private Injector injector(Module... module) {
        return Guice.createInjector(Stage.PRODUCTION, module);
    }


    private <E> List<E> getInstancesFromSameScenario(ObjectFactory factory, Class<E> aClass) {

        // Scenario
        factory.start();
        E o1 = factory.getInstance(aClass);
        E o2 = factory.getInstance(aClass);
        E o3 = factory.getInstance(aClass);
        factory.stop();

        return Arrays.asList(o1, o2, o3);
    }

    private <E> List<E> getInstancesFromDifferentScenarios(ObjectFactory factory, Class<E> aClass) {

        // Scenario 1
        factory.start();
        E o1 = factory.getInstance(aClass);
        factory.stop();

        // Scenario 2
        factory.start();
        E o2 = factory.getInstance(aClass);
        factory.stop();

        // Scenario 3
        factory.start();
        E o3 = factory.getInstance(aClass);
        factory.stop();

        return Arrays.asList(o1, o2, o3);
    }

}

File: java/src/main/java/cucumber/runtime/java/DefaultJavaObjectFactory.java
package cucumber.runtime.java;

import cucumber.runtime.CucumberException;

import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

class DefaultJavaObjectFactory implements ObjectFactory {
    private final Map<Class<?>, Object> instances = new HashMap<Class<?>, Object>();

    public void start() {
        // No-op
    }

    public void stop() {
        instances.clear();
    }

    public void addClass(Class<?> clazz) {
    }

    public <T> T getInstance(Class<T> type) {
        T instance = type.cast(instances.get(type));
        if (instance == null) {
            instance = cacheNewInstance(type);
        }
        return instance;
    }

    private <T> T cacheNewInstance(Class<T> type) {
        try {
            Constructor<T> constructor = type.getConstructor();
            T instance = constructor.newInstance();
            instances.put(type, instance);
            return instance;
        } catch (NoSuchMethodException e) {
            throw new CucumberException(String.format("%s doesn't have an empty constructor. If you need DI, put cucumber-picocontainer on the classpath", type), e);
        } catch (Exception e) {
            throw new CucumberException(String.format("Failed to instantiate %s", type), e);
        }
    }
}


File: java/src/main/java/cucumber/runtime/java/JavaBackend.java
package cucumber.runtime.java;

import cucumber.api.java.After;
import cucumber.api.java.Before;
import cucumber.api.java8.GlueBase;
import cucumber.api.java8.HookBody;
import cucumber.api.java8.HookNoArgsBody;
import cucumber.api.java8.StepdefBody;
import cucumber.runtime.Backend;
import cucumber.runtime.ClassFinder;
import cucumber.runtime.CucumberException;
import cucumber.runtime.DuplicateStepDefinitionException;
import cucumber.runtime.Glue;
import cucumber.runtime.NoInstancesException;
import cucumber.runtime.Reflections;
import cucumber.runtime.TooManyInstancesException;
import cucumber.runtime.UnreportedStepExecutor;
import cucumber.runtime.Utils;
import cucumber.runtime.io.MultiLoader;
import cucumber.runtime.io.ResourceLoader;
import cucumber.runtime.io.ResourceLoaderClassFinder;
import cucumber.runtime.snippets.FunctionNameGenerator;
import cucumber.runtime.snippets.Snippet;
import cucumber.runtime.snippets.SnippetGenerator;
import gherkin.formatter.model.Step;

import java.lang.annotation.Annotation;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.regex.Pattern;

import static cucumber.runtime.io.MultiLoader.packageName;

public class JavaBackend implements Backend {
    public static final ThreadLocal<JavaBackend> INSTANCE = new ThreadLocal<JavaBackend>();
    private final SnippetGenerator snippetGenerator = new SnippetGenerator(createSnippet());

    private Snippet createSnippet() {
        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        try {
            classLoader.loadClass("cucumber.runtime.java8.LambdaGlueBase");
            return new Java8Snippet();
        } catch (ClassNotFoundException thatsOk) {
            return new JavaSnippet();
        }
    }

    private final ObjectFactory objectFactory;
    private final ClassFinder classFinder;

    private final MethodScanner methodScanner;
    private Glue glue;
    private List<Class<? extends GlueBase>> glueBaseClasses = new ArrayList<Class<? extends GlueBase>>();

    /**
     * The constructor called by reflection by default.
     *
     * @param resourceLoader
     */
    public JavaBackend(ResourceLoader resourceLoader) {
        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        classFinder = new ResourceLoaderClassFinder(resourceLoader, classLoader);
        methodScanner = new MethodScanner(classFinder);
        objectFactory = loadObjectFactory(classFinder);
    }

    public JavaBackend(ObjectFactory objectFactory) {
        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        ResourceLoader resourceLoader = new MultiLoader(classLoader);
        classFinder = new ResourceLoaderClassFinder(resourceLoader, classLoader);
        methodScanner = new MethodScanner(classFinder);
        this.objectFactory = objectFactory;
    }

    public JavaBackend(ObjectFactory objectFactory, ClassFinder classFinder) {
        this.objectFactory = objectFactory;
        this.classFinder = classFinder;
        methodScanner = new MethodScanner(classFinder);
    }

    public static ObjectFactory loadObjectFactory(ClassFinder classFinder) {
        ObjectFactory objectFactory;
        try {
            Reflections reflections = new Reflections(classFinder);
            objectFactory = reflections.instantiateExactlyOneSubclass(ObjectFactory.class, "cucumber.runtime", new Class[0], new Object[0]);
        } catch (TooManyInstancesException e) {
            System.out.println(getMultipleObjectFactoryLogMessage());
            objectFactory = new DefaultJavaObjectFactory();
        } catch (NoInstancesException e) {
            objectFactory = new DefaultJavaObjectFactory();
        }
        return objectFactory;
    }

    @Override
    public void loadGlue(Glue glue, List<String> gluePaths) {
        this.glue = glue;
        // Scan for Java7 style glue (annotated methods)
        methodScanner.scan(this, gluePaths);

        // Scan for Java8 style glue (lambdas)
        for (final String gluePath : gluePaths) {
            Collection<Class<? extends GlueBase>> glueDefinerClasses = classFinder.getDescendants(GlueBase.class, packageName(gluePath));
            for (final Class<? extends GlueBase> glueClass : glueDefinerClasses) {
                if (glueClass.isInterface()) {
                    continue;
                }

                objectFactory.addClass(glueClass);
                glueBaseClasses.add(glueClass);
            }
        }
    }

    /**
     * Convenience method for frameworks that wish to load glue from methods explicitly (possibly
     * found with a different mechanism than Cucumber's built-in classpath scanning).
     *
     * @param glue          where stepdefs and hooks will be added.
     * @param method        a candidate method.
     * @param glueCodeClass the class implementing the method. Must not be a subclass of the class implementing the method.
     */
    public void loadGlue(Glue glue, Method method, Class<?> glueCodeClass) {
        this.glue = glue;
        methodScanner.scan(this, method, glueCodeClass);
    }

    @Override
    public void setUnreportedStepExecutor(UnreportedStepExecutor executor) {
        //Not used here yet
    }

    @Override
    public void buildWorld() {
        objectFactory.start();

        // Instantiate all the stepdef classes for java8 - the stepdef will be initialised
        // in the constructor.
        try {
            INSTANCE.set(this);
            glue.removeScenarioScopedGlue();
            for (Class<? extends GlueBase> glueBaseClass : glueBaseClasses) {
                objectFactory.getInstance(glueBaseClass);
            }
        } finally {
            INSTANCE.remove();
        }
    }

    @Override
    public void disposeWorld() {
        objectFactory.stop();
    }

    @Override
    public String getSnippet(Step step, FunctionNameGenerator functionNameGenerator) {
        return snippetGenerator.getSnippet(step, functionNameGenerator);
    }

    void addStepDefinition(Annotation annotation, Method method) {
        try {
            objectFactory.addClass(method.getDeclaringClass());
            glue.addStepDefinition(new JavaStepDefinition(method, pattern(annotation), timeoutMillis(annotation), objectFactory));
        } catch (DuplicateStepDefinitionException e) {
            throw e;
        } catch (Throwable e) {
            throw new CucumberException(e);
        }
    }

    public void addStepDefinition(String regexp, long timeoutMillis, StepdefBody body, TypeIntrospector typeIntrospector) {
        try {
            glue.addStepDefinition(new Java8StepDefinition(Pattern.compile(regexp), timeoutMillis, body, typeIntrospector));
        } catch (Exception e) {
            throw new CucumberException(e);
        }
    }

    void addHook(Annotation annotation, Method method) {
        objectFactory.addClass(method.getDeclaringClass());

        if (annotation.annotationType().equals(Before.class)) {
            String[] tagExpressions = ((Before) annotation).value();
            long timeout = ((Before) annotation).timeout();
            glue.addBeforeHook(new JavaHookDefinition(method, tagExpressions, ((Before) annotation).order(), timeout, objectFactory));
        } else {
            String[] tagExpressions = ((After) annotation).value();
            long timeout = ((After) annotation).timeout();
            glue.addAfterHook(new JavaHookDefinition(method, tagExpressions, ((After) annotation).order(), timeout, objectFactory));
        }
    }

    public void addBeforeHookDefinition(String[] tagExpressions, long timeoutMillis, int order, HookBody body) {
        glue.addBeforeHook(new Java8HookDefinition(tagExpressions, order, timeoutMillis, body));
    }

    public void addAfterHookDefinition(String[] tagExpressions, long timeoutMillis, int order, HookBody body) {
        glue.addAfterHook(new Java8HookDefinition(tagExpressions, order, timeoutMillis, body));
    }

    public void addBeforeHookDefinition(String[] tagExpressions, long timeoutMillis, int order, HookNoArgsBody body) {
        glue.addBeforeHook(new Java8HookDefinition(tagExpressions, order, timeoutMillis, body));
    }

    public void addAfterHookDefinition(String[] tagExpressions, long timeoutMillis, int order, HookNoArgsBody body) {
        glue.addAfterHook(new Java8HookDefinition(tagExpressions, order, timeoutMillis, body));
    }

    private Pattern pattern(Annotation annotation) throws Throwable {
        Method regexpMethod = annotation.getClass().getMethod("value");
        String regexpString = (String) Utils.invoke(annotation, regexpMethod, 0);
        return Pattern.compile(regexpString);
    }

    private long timeoutMillis(Annotation annotation) throws Throwable {
        Method regexpMethod = annotation.getClass().getMethod("timeout");
        return (Long) Utils.invoke(annotation, regexpMethod, 0);
    }

    private static String getMultipleObjectFactoryLogMessage() {
        StringBuilder sb = new StringBuilder();
        sb.append("More than one Cucumber ObjectFactory was found in the classpath\n\n");
        sb.append("You probably may have included, for instance, cucumber-spring AND cucumber-guice as part of\n");
        sb.append("your dependencies. When this happens, Cucumber falls back to instantiating the\n");
        sb.append("DefaultJavaObjectFactory implementation which doesn't provide IoC.\n");
        sb.append("In order to enjoy IoC features, please remove the unnecessary dependencies from your classpath.\n");
        return sb.toString();
    }
}


File: java/src/main/java/cucumber/runtime/java/JavaHookDefinition.java
package cucumber.runtime.java;

import cucumber.api.Scenario;
import cucumber.runtime.CucumberException;
import cucumber.runtime.HookDefinition;
import cucumber.runtime.MethodFormat;
import cucumber.runtime.Utils;
import gherkin.TagExpression;
import gherkin.formatter.model.Tag;

import java.lang.reflect.Method;
import java.util.Collection;

import static java.util.Arrays.asList;

class JavaHookDefinition implements HookDefinition {

    private final Method method;
    private final long timeoutMillis;
    private final TagExpression tagExpression;
    private final int order;
    private final ObjectFactory objectFactory;

    public JavaHookDefinition(Method method, String[] tagExpressions, int order, long timeoutMillis, ObjectFactory objectFactory) {
        this.method = method;
        this.timeoutMillis = timeoutMillis;
        this.tagExpression = new TagExpression(asList(tagExpressions));
        this.order = order;
        this.objectFactory = objectFactory;
    }

    Method getMethod() {
        return method;
    }

    @Override
    public String getLocation(boolean detail) {
        MethodFormat format = detail ? MethodFormat.FULL : MethodFormat.SHORT;
        return format.format(method);
    }

    @Override
    public void execute(Scenario scenario) throws Throwable {
        Object[] args;
        switch (method.getParameterTypes().length) {
            case 0:
                args = new Object[0];
                break;
            case 1:
                if (!Scenario.class.equals(method.getParameterTypes()[0])) {
                    throw new CucumberException("When a hook declares an argument it must be of type " + Scenario.class.getName() + ". " + method.toString());
                }
                args = new Object[]{scenario};
                break;
            default:
                throw new CucumberException("Hooks must declare 0 or 1 arguments. " + method.toString());
        }

        Utils.invoke(objectFactory.getInstance(method.getDeclaringClass()), method, timeoutMillis, args);
    }

    @Override
    public boolean matches(Collection<Tag> tags) {
        return tagExpression.evaluate(tags);
    }

    @Override
    public int getOrder() {
        return order;
    }

    @Override
    public boolean isScenarioScoped() {
        return false;
    }
}


File: java/src/main/java/cucumber/runtime/java/JavaStepDefinition.java
package cucumber.runtime.java;

import cucumber.runtime.JdkPatternArgumentMatcher;
import cucumber.runtime.MethodFormat;
import cucumber.runtime.ParameterInfo;
import cucumber.runtime.StepDefinition;
import cucumber.runtime.Utils;
import gherkin.I18n;
import gherkin.formatter.Argument;
import gherkin.formatter.model.Step;

import java.lang.reflect.Method;
import java.lang.reflect.Type;
import java.util.List;
import java.util.regex.Pattern;

class JavaStepDefinition implements StepDefinition {
    private final Method method;
    private final Pattern pattern;
    private final long timeoutMillis;
    private final ObjectFactory objectFactory;

    private final JdkPatternArgumentMatcher argumentMatcher;
    private final List<ParameterInfo> parameterInfos;

    public JavaStepDefinition(Method method, Pattern pattern, long timeoutMillis, ObjectFactory objectFactory) {
        this.method = method;
        this.pattern = pattern;
        this.timeoutMillis = timeoutMillis;
        this.objectFactory = objectFactory;

        this.argumentMatcher = new JdkPatternArgumentMatcher(pattern);
        this.parameterInfos = ParameterInfo.fromMethod(method);
    }

    public void execute(I18n i18n, Object[] args) throws Throwable {
        Utils.invoke(objectFactory.getInstance(method.getDeclaringClass()), method, timeoutMillis, args);
    }

    public List<Argument> matchedArguments(Step step) {
        return argumentMatcher.argumentsFrom(step.getName());
    }

    public String getLocation(boolean detail) {
        MethodFormat format = detail ? MethodFormat.FULL : MethodFormat.SHORT;
        return format.format(method);
    }

    @Override
    public Integer getParameterCount() {
        return parameterInfos.size();
    }

    @Override
    public ParameterInfo getParameterType(int n, Type argumentType) {
        return parameterInfos.get(n);
    }

    public boolean isDefinedAt(StackTraceElement e) {
        return e.getClassName().equals(method.getDeclaringClass().getName()) && e.getMethodName().equals(method.getName());
    }

    @Override
    public String getPattern() {
        return pattern.pattern();
    }

    @Override
    public boolean isScenarioScoped() {
        return false;
    }
}


File: java/src/test/java/cucumber/runtime/java/JavaBackendTest.java
package cucumber.runtime.java;

import cucumber.api.StepDefinitionReporter;
import cucumber.runtime.CucumberException;
import cucumber.runtime.Glue;
import cucumber.runtime.HookDefinition;
import cucumber.runtime.StepDefinition;
import cucumber.runtime.StepDefinitionMatch;
import cucumber.runtime.java.stepdefs.Stepdefs;
import gherkin.I18n;
import gherkin.formatter.model.Step;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static java.util.Arrays.asList;
import static org.junit.Assert.assertEquals;

public class JavaBackendTest {
    @Test
    public void finds_step_definitions_by_classpath_url() {
        ObjectFactory factory = new DefaultJavaObjectFactory();
        JavaBackend backend = new JavaBackend(factory);
        GlueStub glue = new GlueStub();
        backend.loadGlue(glue, asList("classpath:cucumber/runtime/java/stepdefs"));
        backend.buildWorld();
        assertEquals(Stepdefs.class, factory.getInstance(Stepdefs.class).getClass());
    }

    @Test
    public void finds_step_definitions_by_package_name() {
        ObjectFactory factory = new DefaultJavaObjectFactory();
        JavaBackend backend = new JavaBackend(factory);
        GlueStub glue = new GlueStub();
        backend.loadGlue(glue, asList("cucumber.runtime.java.stepdefs"));
        backend.buildWorld();
        assertEquals(Stepdefs.class, factory.getInstance(Stepdefs.class).getClass());
    }

    @Test(expected = CucumberException.class)
    public void detects_subclassed_glue_and_throws_exception() {
        ObjectFactory factory = new DefaultJavaObjectFactory();
        JavaBackend backend = new JavaBackend(factory);
        GlueStub glue = new GlueStub();
        backend.loadGlue(glue, asList("cucumber.runtime.java.stepdefs", "cucumber.runtime.java.incorrectlysubclassedstepdefs"));
    }

    private class GlueStub implements Glue {
        public final List<StepDefinition> stepDefinitions = new ArrayList<StepDefinition>();

        @Override
        public void addStepDefinition(StepDefinition stepDefinition) {
            stepDefinitions.add(stepDefinition);
        }

        @Override
        public void addBeforeHook(HookDefinition hookDefinition) {
            throw new UnsupportedOperationException();
        }

        @Override
        public void addAfterHook(HookDefinition hookDefinition) {
            throw new UnsupportedOperationException();
        }

        @Override
        public List<HookDefinition> getBeforeHooks() {
            throw new UnsupportedOperationException();
        }

        @Override
        public List<HookDefinition> getAfterHooks() {
            throw new UnsupportedOperationException();
        }

        @Override
        public StepDefinitionMatch stepDefinitionMatch(String featurePath, Step step, I18n i18n) {
            throw new UnsupportedOperationException();
        }

        @Override
        public void reportStepDefinitions(StepDefinitionReporter stepDefinitionReporter) {
            throw new UnsupportedOperationException();
        }

        @Override
        public void removeScenarioScopedGlue() {
        }
    }
}


File: java/src/test/java/cucumber/runtime/java/JavaObjectFactoryTest.java
package cucumber.runtime.java;

import org.junit.Test;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNotSame;

public class JavaObjectFactoryTest {
    @Test
    public void shouldGiveUsNewInstancesForEachScenario() {
        ObjectFactory factory = new DefaultJavaObjectFactory();
        factory.addClass(SteDef.class);

        // Scenario 1
        factory.start();
        SteDef o1 = factory.getInstance(SteDef.class);
        factory.stop();

        // Scenario 2
        factory.start();
        SteDef o2 = factory.getInstance(SteDef.class);
        factory.stop();

        assertNotNull(o1);
        assertNotSame(o1, o2);
    }

    public static class SteDef {
        // we just test the instances
    }
}


File: java/src/test/java/cucumber/runtime/java/MethodScannerTest.java
package cucumber.runtime.java;

import cucumber.api.java.Before;
import cucumber.runtime.CucumberException;
import cucumber.runtime.Glue;
import cucumber.runtime.io.MultiLoader;
import cucumber.runtime.io.ResourceLoader;
import cucumber.runtime.io.ResourceLoaderClassFinder;
import org.junit.Test;
import org.mockito.Mockito;
import org.mockito.internal.util.reflection.Whitebox;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;
import static org.mockito.Mockito.*;

public class MethodScannerTest {

    @Test
    public void loadGlue_registers_the_methods_declaring_class_in_the_object_factory() throws NoSuchMethodException {
        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        ResourceLoader resourceLoader = new MultiLoader(classLoader);
        MethodScanner methodScanner = new MethodScanner(new ResourceLoaderClassFinder(resourceLoader, classLoader));

        ObjectFactory factory = Mockito.mock(ObjectFactory.class);
        Glue world = Mockito.mock(Glue.class);
        JavaBackend backend = new JavaBackend(factory);
        Whitebox.setInternalState(backend, "glue", world);

        // this delegates to methodScanner.scan which we test
        methodScanner.scan(backend, BaseStepDefs.class.getMethod("m"), BaseStepDefs.class);

        verify(factory, times(1)).addClass(BaseStepDefs.class);
        verifyNoMoreInteractions(factory);
    }

    @Test
    public void loadGlue_fails_when_class_is_not_method_declaring_class() throws NoSuchMethodException {
        JavaBackend backend = new JavaBackend((ObjectFactory) null);
        try {
            backend.loadGlue(null, BaseStepDefs.class.getMethod("m"), Stepdefs2.class);
            fail();
        } catch (CucumberException e) {
            assertEquals("You're not allowed to extend classes that define Step Definitions or hooks. class cucumber.runtime.java.MethodScannerTest$Stepdefs2 extends class cucumber.runtime.java.MethodScannerTest$BaseStepDefs", e.getMessage());
        }
    }

    @Test
    public void loadGlue_fails_when_class_is_not_subclass_of_declaring_class() throws NoSuchMethodException {
        JavaBackend backend = new JavaBackend((ObjectFactory) null);
        try {
            backend.loadGlue(null, BaseStepDefs.class.getMethod("m"), String.class);
            fail();
        } catch (CucumberException e) {
            assertEquals("class cucumber.runtime.java.MethodScannerTest$BaseStepDefs isn't assignable from class java.lang.String", e.getMessage());
        }
    }

    public static class Stepdefs2 extends BaseStepDefs {
        public interface Interface1 {
        }
    }

    public static class BaseStepDefs {
        @Before
        public void m() {
        }
    }
}


File: java/src/test/java/cucumber/runtime/java/SingletonFactory.java
package cucumber.runtime.java;

class SingletonFactory implements ObjectFactory {
    private Object singleton;

    public SingletonFactory() {
        this(null);
    }

    public SingletonFactory(Object singleton) {
        this.singleton = singleton;
    }

    @Override
    public void start() {
    }

    @Override
    public void stop() {
    }

    @Override
    public void addClass(Class<?> clazz) {
    }

    @Override
    public <T> T getInstance(Class<T> type) {
        if (singleton == null) {
            throw new IllegalStateException("No object is set");
        }
        return type.cast(singleton);
    }

    public void setInstance(Object o) {
        singleton = o;
    }
}


File: jruby/src/main/java/cucumber/runtime/jruby/JRubyBackend.java
package cucumber.runtime.jruby;

import cucumber.api.DataTable;
import cucumber.api.PendingException;
import cucumber.api.Scenario;
import cucumber.runtime.Backend;
import cucumber.runtime.CucumberException;
import cucumber.runtime.Env;
import cucumber.runtime.Glue;
import cucumber.runtime.UnreportedStepExecutor;
import cucumber.runtime.io.Resource;
import cucumber.runtime.io.ResourceLoader;
import cucumber.runtime.snippets.FunctionNameGenerator;
import cucumber.runtime.snippets.SnippetGenerator;
import gherkin.I18n;
import gherkin.formatter.model.DataTableRow;
import gherkin.formatter.model.DocString;
import gherkin.formatter.model.Step;
import org.jruby.CompatVersion;
import org.jruby.Ruby;
import org.jruby.RubyModule;
import org.jruby.RubyObject;
import org.jruby.embed.ScriptingContainer;
import org.jruby.javasupport.JavaEmbedUtils;
import org.jruby.runtime.builtin.IRubyObject;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class JRubyBackend implements Backend {
    private static final Env env = new Env("cucumber");
    private final SnippetGenerator snippetGenerator = new SnippetGenerator(new JRubySnippet());
    private final ScriptingContainer jruby = new ScriptingContainer();
    private final ResourceLoader resourceLoader;
    private final Set<JRubyWorldDefinition> worldDefinitions = new HashSet<JRubyWorldDefinition>();
    private final RubyModule CucumberRuntimeJRubyWorld;

    private Glue glue;
    private UnreportedStepExecutor unreportedStepExecutor;
    private RubyObject currentWorld;

    public JRubyBackend(ResourceLoader resourceLoader) throws UnsupportedEncodingException {
        this.resourceLoader = resourceLoader;
        jruby.put("$backend", this);
        jruby.setClassLoader(getClass().getClassLoader());
        String gemPath = env.get("GEM_PATH");
        if (gemPath != null) {
            jruby.runScriptlet("ENV['GEM_PATH']='" + gemPath + "'");
        }

        String rubyVersion = env.get("RUBY_VERSION");
        if (rubyVersion != null) {
            // RVM typically defines env vars like
            // RUBY_VERSION=ruby-1.9.3-p362
            if (rubyVersion.matches(".*1\\.8\\.\\d.*") || rubyVersion.matches(".*1\\.8")) {
                jruby.setCompatVersion(CompatVersion.RUBY1_8);
            } else if (rubyVersion.matches(".*1\\.9\\.\\d.*") || rubyVersion.matches(".*1\\.9.*")) {
                jruby.setCompatVersion(CompatVersion.RUBY1_9);
            } else if (rubyVersion.matches(".*2\\.0\\.\\d.*") || rubyVersion.matches(".*2\\.0.*")) {
                jruby.setCompatVersion(CompatVersion.RUBY2_0);
            } else {
                throw new CucumberException("Invalid RUBY_VERSION: " + rubyVersion);
            }
        }
        for (Resource resource : resourceLoader.resources("classpath:cucumber/runtime/jruby", ".rb")) {
            runScript(resource);
        }

        // Let's go through some hoops to look up the Cucumber::Runtime::JRuby::World module. Sheesh!
        Ruby runtime = jruby.getProvider().getRuntime();
        RubyModule Cucumber = runtime.getModule("Cucumber");
        RubyModule CucumberRuntime = (RubyModule) Cucumber.const_get(runtime.newString("Runtime"));
        RubyModule CucumberRuntimeJRuby = (RubyModule) CucumberRuntime.const_get(runtime.newString("JRuby"));
        CucumberRuntimeJRubyWorld = (RubyModule) CucumberRuntimeJRuby.const_get(runtime.newString("World"));
    }

    @Override
    public void loadGlue(Glue glue, List<String> gluePaths) {
        this.glue = glue;
        for (String gluePath : gluePaths) {
            Iterable<Resource> resources = resourceLoader.resources(gluePath, ".rb");
            List<Resource> resourcesWithEnvFirst = new ArrayList<Resource>();
            for (Resource resource : resources) {
                if (resource.getAbsolutePath().endsWith("env.rb")) {
                    resourcesWithEnvFirst.add(0, resource);
                } else {
                    resourcesWithEnvFirst.add(resource);
                }
            }
            for (Resource resource : resourcesWithEnvFirst) {
                runScript(resource);
            }
        }
    }

    @Override
    public void setUnreportedStepExecutor(UnreportedStepExecutor executor) {
        this.unreportedStepExecutor = executor;
    }

    @Override
    public void buildWorld() {
        currentWorld = (RubyObject) JavaEmbedUtils.javaToRuby(jruby.getProvider().getRuntime(), new World());
        currentWorld.extend(new IRubyObject[]{CucumberRuntimeJRubyWorld});

        for (JRubyWorldDefinition definition : worldDefinitions) {
            currentWorld = definition.execute(currentWorld);
        }
    }

    private void runScript(Resource resource) {
        try {
            jruby.runScriptlet(new InputStreamReader(resource.getInputStream(), "UTF-8"), resource.getAbsolutePath());
        } catch (IOException e) {
            throw new CucumberException(e);
        }
    }

    @Override
    public void disposeWorld() {
    }

    @Override
    public String getSnippet(Step step, FunctionNameGenerator functionNameGenerator) {
        return snippetGenerator.getSnippet(step, functionNameGenerator);
    }

    public void registerStepdef(RubyObject stepdefRunner) {
        glue.addStepDefinition(new JRubyStepDefinition(this, stepdefRunner));
    }

    public void registerBeforeHook(RubyObject procRunner, String[] tagExpressions) {
        glue.addBeforeHook(new JRubyHookDefinition(this, tagExpressions, procRunner));
    }

    public void registerAfterHook(RubyObject procRunner, String[] tagExpressions) {
        glue.addAfterHook(new JRubyHookDefinition(this, tagExpressions, procRunner));
    }

    public void registerWorldBlock(RubyObject procRunner) {
        worldDefinitions.add(new JRubyWorldDefinition(procRunner));
    }

    public void pending(String reason) throws PendingException {
        throw new PendingException(reason);
    }

    public void runStep(String featurePath, I18n i18n, String stepKeyword, String stepName, int line, DataTable dataTable, DocString docString) throws Throwable {
        List<DataTableRow> dataTableRows = null;
        if (dataTable != null) {
            dataTableRows = dataTable.getGherkinRows();
        }

        unreportedStepExecutor.runUnreportedStep(featurePath, i18n, stepKeyword, stepName, line, dataTableRows, docString);
    }

    public void executeHook(RubyObject hookRunner, Scenario scenario) {
        IRubyObject[] jrubyArgs = new IRubyObject[2];
        jrubyArgs[0] = currentWorld;
        jrubyArgs[1] = JavaEmbedUtils.javaToRuby(hookRunner.getRuntime(), scenario);
        hookRunner.callMethod("execute", jrubyArgs);
    }

    void executeStepdef(RubyObject stepdef, I18n i18n, Object[] args) {
        ArrayList<IRubyObject> jrubyArgs = new ArrayList<IRubyObject>();

        // jrubyWorld.@__gherkin_i18n = i18n
        RubyObject jrubyI18n = (RubyObject) JavaEmbedUtils.javaToRuby(stepdef.getRuntime(), i18n);
        currentWorld.callMethod("instance_variable_set", new IRubyObject[]{stepdef.getRuntime().newSymbol("@__gherkin_i18n"), jrubyI18n});

        jrubyArgs.add(currentWorld);

        for (Object o : args) {
            if (o == null) {
                jrubyArgs.add(null);
            } else if (o instanceof DataTable) {
                //Add a datatable as it stands...
                jrubyArgs.add(JavaEmbedUtils.javaToRuby(stepdef.getRuntime(), o));
            } else {
                jrubyArgs.add(stepdef.getRuntime().newString((String) o));
            }
        }

        stepdef.callMethod("execute", jrubyArgs.toArray(new IRubyObject[jrubyArgs.size()]));
    }
}


File: needle/src/main/java/cucumber/runtime/java/needle/NeedleFactory.java
package cucumber.runtime.java.needle;

import cucumber.runtime.java.ObjectFactory;
import cucumber.runtime.java.needle.config.CollectInjectionProvidersFromStepsInstance;
import cucumber.runtime.java.needle.config.CreateInstanceByDefaultConstructor;
import cucumber.runtime.java.needle.config.CucumberNeedleConfiguration;
import de.akquinet.jbosscc.needle.NeedleTestcase;
import de.akquinet.jbosscc.needle.injection.InjectionProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.LinkedHashMap;
import java.util.Map;

import static cucumber.runtime.java.needle.config.CucumberNeedleConfiguration.RESOURCE_CUCUMBER_NEEDLE;
import static java.lang.String.format;

/**
 * Needle factory for object resolution inside of cucumber tests.
 */
public class NeedleFactory extends NeedleTestcase implements ObjectFactory {

    private final Map<Class<?>, Object> cachedStepsInstances = new LinkedHashMap<Class<?>, Object>();
    private final Logger logger = LoggerFactory.getLogger(this.getClass());
    private final CreateInstanceByDefaultConstructor createInstanceByDefaultConstructor = CreateInstanceByDefaultConstructor.INSTANCE;
    private final CollectInjectionProvidersFromStepsInstance collectInjectionProvidersFromStepsInstance = CollectInjectionProvidersFromStepsInstance.INSTANCE;

    public NeedleFactory() {
        super(setUpInjectionProviders(RESOURCE_CUCUMBER_NEEDLE));
    }

    @Override
    public <T> T getInstance(final Class<T> type) {
        logger.trace("getInstance: " + type.getCanonicalName());
        assertTypeHasBeenAdded(type);
        return nullSafeGetInstance(type);
    }

    @Override
    public void start() {
        logger.trace("start()");
        for (final Class<?> stepDefinitionType : cachedStepsInstances.keySet()) {
            cachedStepsInstances.put(stepDefinitionType, createStepsInstance(stepDefinitionType));
        }
    }

    @Override
    public void stop() {
        logger.trace("stop()");
        for (final Class<?> stepDefinitionType : cachedStepsInstances.keySet()) {
            cachedStepsInstances.put(stepDefinitionType, null);
        }
    }

    @Override
    public void addClass(final Class<?> type) {
        logger.trace("addClass(): " + type.getCanonicalName());

        // build up cache keys ...
        if (!cachedStepsInstances.containsKey(type)) {
            cachedStepsInstances.put(type, null);
        }
    }

    private void assertTypeHasBeenAdded(final Class<?> type) {
        if (!cachedStepsInstances.containsKey(type)) {
            throw new IllegalStateException(format("%s was not added during addClass()", type.getSimpleName()));
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T nullSafeGetInstance(final Class<T> type) {
        final Object instance = cachedStepsInstances.get(type);
        if (instance == null) {
            throw new IllegalStateException(format("instance of type %s has not been initialized in start()!",
                    type.getSimpleName()));
        }
        return (T) instance;
    }

    private <T> T createStepsInstance(final Class<T> type) {
        logger.trace("createInstance(): " + type.getCanonicalName());
        try {
            final T stepsInstance = createInstanceByDefaultConstructor.apply(type);
            addInjectionProvider(collectInjectionProvidersFromStepsInstance.apply(stepsInstance));
            initTestcase(stepsInstance);
            return stepsInstance;
        } catch (final Exception e) {
            throw new IllegalStateException(e);
        }
    }

    static InjectionProvider<?>[] setUpInjectionProviders(final String resourceName) {
        return new CucumberNeedleConfiguration(resourceName).getInjectionProviders();
    }
}


File: openejb/src/main/java/cucumber/runtime/java/openejb/OpenEJBObjectFactory.java
package cucumber.runtime.java.openejb;

import cucumber.runtime.CucumberException;
import cucumber.runtime.java.ObjectFactory;
import org.apache.openejb.OpenEjbContainer;

import javax.ejb.embeddable.EJBContainer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Properties;

public class OpenEJBObjectFactory implements ObjectFactory {
    private final List<String> classes = new ArrayList<String>();
    private final Map<Class<?>, Object> instances = new HashMap<Class<?>, Object>();
    private EJBContainer container;

    @Override
    public void start() {
        final StringBuilder callers = new StringBuilder();
        for (Iterator<String> it = classes.iterator(); it.hasNext(); ) {
            callers.append(it.next());
            if (it.hasNext()) {
                callers.append(",");
            }
        }

        Properties properties = new Properties();
        properties.setProperty(OpenEjbContainer.Provider.OPENEJB_ADDITIONNAL_CALLERS_KEY, callers.toString());
        container = EJBContainer.createEJBContainer(properties);
    }

    @Override
    public void stop() {
        container.close();
        instances.clear();
    }

    @Override
    public void addClass(Class<?> clazz) {
        classes.add(clazz.getName());
    }

    @Override
    public <T> T getInstance(Class<T> type) {
        if (instances.containsKey(type)) {
            return type.cast(instances.get(type));
        }

        T object;
        try {
            object = type.newInstance();
            container.getContext().bind("inject", object);
        } catch (Exception e) {
            throw new CucumberException("can't create " + type.getName(), e);
        }
        instances.put(type, object);
        return object;
    }
}



File: openejb/src/test/java/cucumber/runtime/java/openejb/OpenEJBObjectFactoryTest.java
package cucumber.runtime.java.openejb;

import cucumber.runtime.java.ObjectFactory;
import org.junit.Test;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNotSame;

public class OpenEJBObjectFactoryTest {
    @Test
    public void shouldGiveUsNewInstancesForEachScenario() {
        ObjectFactory factory = new OpenEJBObjectFactory();
        factory.addClass(BellyStepdefs.class);

        // Scenario 1
        factory.start();
        BellyStepdefs o1 = factory.getInstance(BellyStepdefs.class);
        factory.stop();

        // Scenario 2
        factory.start();
        BellyStepdefs o2 = factory.getInstance(BellyStepdefs.class);
        factory.stop();

        assertNotNull(o1);
        assertNotSame(o1, o2);
    }

}


File: picocontainer/src/main/java/cucumber/runtime/java/picocontainer/PicoFactory.java
package cucumber.runtime.java.picocontainer;

import cucumber.runtime.java.ObjectFactory;
import org.picocontainer.MutablePicoContainer;
import org.picocontainer.PicoBuilder;

import java.lang.reflect.Constructor;
import java.util.HashSet;
import java.util.Set;

public class PicoFactory implements ObjectFactory {
    private MutablePicoContainer pico;
    private final Set<Class<?>> classes = new HashSet<Class<?>>();

    public void start() {
        pico = new PicoBuilder().withCaching().build();
        for (Class<?> clazz : classes) {
            pico.addComponent(clazz);
        }
        pico.start();
    }

    public void stop() {
        pico.stop();
        pico.dispose();
    }

    public void addClass(Class<?> clazz) {
        if (classes.add(clazz)) {
            addConstructorDependencies(clazz);
        }
    }

    public <T> T getInstance(Class<T> type) {
        return pico.getComponent(type);
    }

    private void addConstructorDependencies(Class<?> clazz) {
        for (Constructor constructor : clazz.getConstructors()) {
            for (Class paramClazz : constructor.getParameterTypes()) {
                addClass(paramClazz);
            }
        }
    }
}


File: picocontainer/src/test/java/cucumber/runtime/java/picocontainer/PicoFactoryTest.java
package cucumber.runtime.java.picocontainer;

import cucumber.runtime.java.ObjectFactory;
import org.junit.Test;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNotSame;

public class PicoFactoryTest {
    @Test
    public void shouldGiveUsNewInstancesForEachScenario() {
        ObjectFactory factory = new PicoFactory();
        factory.addClass(StepDefs.class);

        // Scenario 1
        factory.start();
        StepDefs o1 = factory.getInstance(StepDefs.class);
        factory.stop();

        // Scenario 2
        factory.start();
        StepDefs o2 = factory.getInstance(StepDefs.class);
        factory.stop();

        assertNotNull(o1);
        assertNotSame(o1, o2);
    }

}


File: spring/src/main/java/cucumber/runtime/java/spring/SpringFactory.java
package cucumber.runtime.java.spring;

import cucumber.runtime.CucumberException;
import cucumber.runtime.java.ObjectFactory;
import org.springframework.beans.BeansException;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.beans.factory.config.ConfigurableListableBeanFactory;
import org.springframework.beans.factory.support.BeanDefinitionBuilder;
import org.springframework.beans.factory.support.BeanDefinitionRegistry;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.support.ClassPathXmlApplicationContext;
import org.springframework.context.support.GenericApplicationContext;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.ContextHierarchy;
import org.springframework.test.context.TestContextManager;

import java.lang.annotation.Annotation;
import java.util.Collection;
import java.util.HashSet;

/**
 * Spring based implementation of ObjectFactory.
 * <p/>
 * <p>
 * <ul>
 * <li>It uses TestContextManager to manage the spring context.
 * Configuration via: @ContextConfiguration or @ContextHierarcy
 * At least on step definition class needs to have a @ContextConfiguration or
 * @ContextHierarchy annotation. If more that one step definition class has such
 * an annotation, the annotations must be equal on the different step definition
 * classes. If no step definition class with @ContextConfiguration or
 * @ContextHierarcy is found, it will try to load cucumber.xml from the classpath.
 * </li>
 * <li>The step definitions class with @ContextConfiguration or @ContextHierarchy
 * annotation, may also have a @WebAppConfiguration or @DirtiesContext annotation.
 * </li>
 * <li>The step definitions added to the TestContextManagers context and
 * is reloaded for each scenario.</li>
 * </ul>
 * </p>
 * <p/>
 * <p>
 * Application beans are accessible from the step definitions using autowiring
 * (with annotations).
 * </p>
 */
public class SpringFactory implements ObjectFactory {

    private ConfigurableListableBeanFactory beanFactory;
    private CucumberTestContextManager testContextManager;

    private final Collection<Class<?>> stepClasses = new HashSet<Class<?>>();
    private Class<?> stepClassWithSpringContext = null;

    public SpringFactory() {
    }

    @Override
    public void addClass(final Class<?> stepClass) {
        if (!stepClasses.contains(stepClass)) {
            if (dependsOnSpringContext(stepClass)) {
                if (stepClassWithSpringContext == null) {
                    stepClassWithSpringContext = stepClass;
                } else {
                    checkAnnotationsEqual(stepClassWithSpringContext, stepClass);
                }
            }
            stepClasses.add(stepClass);

        }
    }

    private void checkAnnotationsEqual(Class<?> stepClassWithSpringContext, Class<?> stepClass) {
        Annotation[] annotations1 = stepClassWithSpringContext.getAnnotations();
        Annotation[] annotations2 = stepClass.getAnnotations();
        if (annotations1.length != annotations2.length) {
            throw new CucumberException("Annotations differs on glue classes found: " +
                    stepClassWithSpringContext.getName() + ", " +
                    stepClass.getName());
        }
        for (Annotation annotation : annotations1) {
            if (!isAnnotationInArray(annotation, annotations2)) {
                throw new CucumberException("Annotations differs on glue classes found: " +
                        stepClassWithSpringContext.getName() + ", " +
                        stepClass.getName());
            }
        }
    }

    private boolean isAnnotationInArray(Annotation annotation, Annotation[] annotations) {
        for (Annotation annotationFromArray: annotations) {
            if (annotation.equals(annotationFromArray)) {
                return true;
            }
        }
        return false;
    }

    @Override
    public void start() {
        if (stepClassWithSpringContext != null) {
            testContextManager = new CucumberTestContextManager(stepClassWithSpringContext);
        } else {
            if (beanFactory == null) {
                beanFactory = createFallbackContext();
            }
        }
        notifyContextManagerAboutTestClassStarted();
        if (beanFactory == null || isNewContextCreated()) {
            beanFactory = testContextManager.getBeanFactory();
            for (Class<?> stepClass : stepClasses) {
                registerStepClassBeanDefinition(beanFactory, stepClass);
            }
        }
        GlueCodeContext.INSTANCE.start();
    }

    @SuppressWarnings("resource")
    private ConfigurableListableBeanFactory createFallbackContext() {
        ConfigurableApplicationContext applicationContext;
        if (getClass().getClassLoader().getResource("cucumber.xml") != null) {
            applicationContext = new ClassPathXmlApplicationContext("cucumber.xml");
        } else {
            applicationContext = new GenericApplicationContext();
        }
        applicationContext.registerShutdownHook();
        ConfigurableListableBeanFactory beanFactory = applicationContext.getBeanFactory();
        beanFactory.registerScope(GlueCodeScope.NAME, new GlueCodeScope());
        for (Class<?> stepClass : stepClasses) {
            registerStepClassBeanDefinition(beanFactory, stepClass);
        }
        return beanFactory;
    }

    private void notifyContextManagerAboutTestClassStarted() {
        if (testContextManager != null) {
            try {
                testContextManager.beforeTestClass();
            } catch (Exception e) {
                throw new CucumberException(e.getMessage(), e);
            }
        }
    }

    private boolean isNewContextCreated() {
        if (testContextManager == null) {
            return false;
        }
        return !beanFactory.equals(testContextManager.getBeanFactory());
    }

    private void registerStepClassBeanDefinition(ConfigurableListableBeanFactory beanFactory, Class<?> stepClass) {
        BeanDefinitionRegistry registry = (BeanDefinitionRegistry) beanFactory;
        BeanDefinition beanDefinition = BeanDefinitionBuilder
                .genericBeanDefinition(stepClass)
                .setScope(GlueCodeScope.NAME)
                .getBeanDefinition();
        registry.registerBeanDefinition(stepClass.getName(), beanDefinition);
    }

    @Override
    public void stop() {
        notifyContextManagerAboutTestClassFinished();
        GlueCodeContext.INSTANCE.stop();
    }

    private void notifyContextManagerAboutTestClassFinished() {
        if (testContextManager != null) {
            try {
                testContextManager.afterTestClass();
            } catch (Exception e) {
                throw new CucumberException(e.getMessage(), e);
            }
        }
    }

    @Override
    public <T> T getInstance(final Class<T> type) {
        try {
            return beanFactory.getBean(type);
        } catch (BeansException e) {
            throw new CucumberException(e.getMessage(), e);
        }
    }

    private boolean dependsOnSpringContext(Class<?> type) {
        boolean hasStandardAnnotations = annotatedWithSupportedSpringRootTestAnnotations(type);

        if(hasStandardAnnotations) {
            return true;
        }

        final Annotation[] annotations = type.getDeclaredAnnotations();
        return (annotations.length == 1) && annotatedWithSupportedSpringRootTestAnnotations(annotations[0].annotationType());
    }

    private boolean annotatedWithSupportedSpringRootTestAnnotations(Class<?> type) {
        return type.isAnnotationPresent(ContextConfiguration.class)
            || type.isAnnotationPresent(ContextHierarchy.class);
    }
}

class CucumberTestContextManager extends TestContextManager {

    public CucumberTestContextManager(Class<?> testClass) {
        super(testClass);
        registerGlueCodeScope(getContext());
    }

    public ConfigurableListableBeanFactory getBeanFactory() {
        return getContext().getBeanFactory();
    }

    private ConfigurableApplicationContext getContext() {
        return (ConfigurableApplicationContext)getTestContext().getApplicationContext();
    }

    private void registerGlueCodeScope(ConfigurableApplicationContext context) {
        do {
            context.getBeanFactory().registerScope(GlueCodeScope.NAME, new GlueCodeScope());
            context = (ConfigurableApplicationContext)context.getParent();
        } while (context != null);
    }
}


File: spring/src/test/java/cucumber/runtime/java/spring/SpringFactoryTest.java
package cucumber.runtime.java.spring;

import cucumber.runtime.CucumberException;
import cucumber.runtime.java.ObjectFactory;
import cucumber.runtime.java.spring.beans.BellyBean;
import cucumber.runtime.java.spring.commonglue.AutowiresPlatformTransactionManager;
import cucumber.runtime.java.spring.commonglue.AutowiresThirdStepDef;
import cucumber.runtime.java.spring.commonglue.OneStepDef;
import cucumber.runtime.java.spring.commonglue.ThirdStepDef;
import cucumber.runtime.java.spring.metaconfig.BellyMetaStepdefs;
import cucumber.runtime.java.spring.contextconfig.BellyStepdefs;
import cucumber.runtime.java.spring.contextconfig.WithSpringAnnotations;
import cucumber.runtime.java.spring.contexthierarchyconfig.WithContextHierarchyAnnotation;
import cucumber.runtime.java.spring.contexthierarchyconfig.WithDifferentContextHierarchyAnnotation;
import cucumber.runtime.java.spring.dirtiescontextconfig.DirtiesContextBellyStepDefs;
import cucumber.runtime.java.spring.metaconfig.dirties.DirtiesContextBellyMetaStepDefs;
import org.junit.Test;
import org.springframework.transaction.PlatformTransactionManager;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

public class SpringFactoryTest {

    @Test
    public void shouldGiveUsNewStepInstancesForEachScenario() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(BellyStepdefs.class);

        // Scenario 1
        factory.start();
        final BellyStepdefs o1 = factory.getInstance(BellyStepdefs.class);
        factory.stop();

        // Scenario 2
        factory.start();
        final BellyStepdefs o2 = factory.getInstance(BellyStepdefs.class);
        factory.stop();

        assertNotNull(o1);
        assertNotNull(o2);
        assertNotSame(o1, o2);
    }

    @Test
    public void shouldGiveUsNewInstancesOfGlueScopeClassesForEachScenario() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(BellyStepdefs.class);
        factory.addClass(AutowiresPlatformTransactionManager.class);

        // Scenario 1
        factory.start();
        final PlatformTransactionManager o1 =
                factory.getInstance(AutowiresPlatformTransactionManager.class).getTransactionManager();
        factory.stop();

        // Scenario 2
        factory.start();
        final PlatformTransactionManager o2 =
                factory.getInstance(AutowiresPlatformTransactionManager.class).getTransactionManager();
        factory.stop();

        assertNotNull(o1);
        assertNotNull(o2);
        assertNotSame(o1, o2);
    }

    @Test
    public void shouldNeverCreateNewApplicationBeanInstances() {
        // Feature 1
        final ObjectFactory factory1 = new SpringFactory();
        factory1.addClass(BellyStepdefs.class);
        factory1.start();
        final BellyBean o1 = factory1.getInstance(BellyStepdefs.class).getBellyBean();
        factory1.stop();

        // Feature 2
        final ObjectFactory factory2 = new SpringFactory();
        factory2.addClass(BellyStepdefs.class);
        factory2.start();
        final BellyBean o2 = factory2.getInstance(BellyStepdefs.class).getBellyBean();
        factory2.stop();

        assertNotNull(o1);
        assertNotNull(o2);
        assertSame(o1, o2);
    }

    @Test
    public void shouldNeverCreateNewApplicationBeanInstancesUsingMetaConfiguration() {
        // Feature 1
        final ObjectFactory factory1 = new SpringFactory();
        factory1.addClass(BellyMetaStepdefs.class);
        factory1.start();
        final BellyBean o1 = factory1.getInstance(BellyMetaStepdefs.class).getBellyBean();
        factory1.stop();

        // Feature 2
        final ObjectFactory factory2 = new SpringFactory();
        factory2.addClass(BellyMetaStepdefs.class);
        factory2.start();
        final BellyBean o2 = factory2.getInstance(BellyMetaStepdefs.class).getBellyBean();
        factory2.stop();

        assertNotNull(o1);
        assertNotNull(o2);
        assertSame(o1, o2);
    }

    @Test
    public void shouldFindStepDefsCreatedImplicitlyForAutowiring() {
        final ObjectFactory factory1 = new SpringFactory();
        factory1.addClass(WithSpringAnnotations.class);
        factory1.addClass(OneStepDef.class);
        factory1.addClass(ThirdStepDef.class);
        factory1.addClass(AutowiresThirdStepDef.class);
        factory1.start();
        final OneStepDef o1 = factory1.getInstance(OneStepDef.class);
        final ThirdStepDef o2 = factory1.getInstance(ThirdStepDef.class);
        factory1.stop();

        assertNotNull(o1.getThirdStepDef());
        assertNotNull(o2);
        assertSame(o1.getThirdStepDef(), o2);
    }

    @Test
    public void shouldReuseStepDefsCreatedImplicitlyForAutowiring() {
        final ObjectFactory factory1 = new SpringFactory();
        factory1.addClass(WithSpringAnnotations.class);
        factory1.addClass(OneStepDef.class);
        factory1.addClass(ThirdStepDef.class);
        factory1.addClass(AutowiresThirdStepDef.class);
        factory1.start();
        final OneStepDef o1 = factory1.getInstance(OneStepDef.class);
        final AutowiresThirdStepDef o3 = factory1.getInstance(AutowiresThirdStepDef.class);
        factory1.stop();

        assertNotNull(o1.getThirdStepDef());
        assertNotNull(o3.getThirdStepDef());
        assertSame(o1.getThirdStepDef(), o3.getThirdStepDef());
    }

    @Test
    public void shouldRespectCommonAnnotationsInStepDefs() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(WithSpringAnnotations.class);
        factory.start();
        WithSpringAnnotations stepdef = factory.getInstance(WithSpringAnnotations.class);
        factory.stop();

        assertNotNull(stepdef);
        assertTrue(stepdef.isAutowired());
    }

    @Test
    public void shouldRespectContextHierarchyInStepDefs() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(WithContextHierarchyAnnotation.class);
        factory.start();
        WithContextHierarchyAnnotation stepdef = factory.getInstance(WithContextHierarchyAnnotation.class);
        factory.stop();

        assertNotNull(stepdef);
        assertTrue(stepdef.isAutowired());
    }

    @Test
    public void shouldRespectDirtiesContextAnnotationsInStepDefs() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(DirtiesContextBellyStepDefs.class);

        // Scenario 1
        factory.start();
        final BellyBean o1 = factory.getInstance(DirtiesContextBellyStepDefs.class).getBellyBean();

        factory.stop();

        // Scenario 2
        factory.start();
        final BellyBean o2 = factory.getInstance(DirtiesContextBellyStepDefs.class).getBellyBean();
        factory.stop();

        assertNotNull(o1);
        assertNotNull(o2);
        assertNotSame(o1, o2);
    }

    @Test
    public void shouldRespectDirtiesContextAnnotationsInStepDefsUsingMetaConfiguration() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(DirtiesContextBellyMetaStepDefs.class);

        // Scenario 1
        factory.start();
        final BellyBean o1 = factory.getInstance(DirtiesContextBellyMetaStepDefs.class).getBellyBean();

        factory.stop();

        // Scenario 2
        factory.start();
        final BellyBean o2 = factory.getInstance(DirtiesContextBellyMetaStepDefs.class).getBellyBean();
        factory.stop();

        assertNotNull(o1);
        assertNotNull(o2);
        assertNotSame(o1, o2);
    }

    @Test
    public void shouldRespectCustomPropertyPlaceholderConfigurer() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(WithSpringAnnotations.class);
        factory.start();
        WithSpringAnnotations stepdef = factory.getInstance(WithSpringAnnotations.class);
        factory.stop();

        assertEquals("property value", stepdef.getProperty());
    }

    @Test
    public void shouldUseCucumberXmlIfNoClassWithSpringAnnotationIsFound() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(AutowiresPlatformTransactionManager.class);
        factory.start();
        final AutowiresPlatformTransactionManager o1 =
                factory.getInstance(AutowiresPlatformTransactionManager.class);
        factory.stop();

        assertNotNull(o1);
        assertNotNull(o1.getTransactionManager());
    }

    @Test
    public void shouldAllowClassesWithSameSpringAnnotations() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(WithSpringAnnotations.class);
        factory.addClass(BellyStepdefs.class);
    }

    @Test(expected=CucumberException.class)
    public void shouldFailIfClassesWithDifferentSpringAnnotationsAreFound() {
        final ObjectFactory factory = new SpringFactory();
        factory.addClass(WithContextHierarchyAnnotation.class);
        factory.addClass(WithDifferentContextHierarchyAnnotation.class);
    }
}


File: weld/src/main/java/cucumber/runtime/java/weld/WeldFactory.java
package cucumber.runtime.java.weld;

import cucumber.runtime.CucumberException;
import cucumber.runtime.java.ObjectFactory;
import org.jboss.weld.environment.se.Weld;
import org.jboss.weld.environment.se.WeldContainer;

public class WeldFactory extends Weld implements ObjectFactory {

    private WeldContainer weld;

    @Override
    public void start() {
        try {
            weld = super.initialize();
        } catch (IllegalArgumentException e) {
            throw new CucumberException("" +
                    "\n" +
                    "It looks like you're running on a single-core machine, and Weld doesn't like that. See:\n" +
                    "* http://in.relation.to/Bloggers/Weld200Alpha2Released\n" +
                    "* https://issues.jboss.org/browse/WELD-1119\n" +
                    "\n" +
                    "The workaround is to add enabled=false to a org.jboss.weld.executor.properties file on\n" +
                    "your CLASSPATH. Beware that this will trigger another Weld bug - startup will now work,\n" +
                    "but shutdown will fail with a NullPointerException. This exception will be printed and\n" +
                    "not rethrown. It's the best Cucumber-JVM can do until this bug is fixed in Weld.\n" +
                    "\n", e);
        }
    }

    @Override
    public void stop() {
        try {
            this.shutdown();
        } catch (NullPointerException npe) {
            System.err.println("" +
                    "\nIf you have set enabled=false in org.jboss.weld.executor.properties and you are seeing\n" +
                    "this message, it means your weld container didn't shut down properly. It's a Weld bug\n" +
                    "and we can't do much to fix it in Cucumber-JVM.\n" +
                    "");
            npe.printStackTrace();
        }
    }

    @Override
    public void addClass(Class<?> clazz) {
    }

    @Override
    public <T> T getInstance(Class<T> type) {
        return weld.instance().select(type).get();
    }
}


File: weld/src/test/java/cucumber/runtime/java/weld/WeldFactoryTest.java
package cucumber.runtime.java.weld;

import cucumber.runtime.java.ObjectFactory;
import org.junit.Test;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNotSame;

public class WeldFactoryTest {
    @Test
    public void shouldGiveUsNewInstancesForEachScenario() {
        ObjectFactory factory = new WeldFactory();
        factory.addClass(BellyStepdefs.class);

        // Scenario 1
        factory.start();
        BellyStepdefs o1 = factory.getInstance(BellyStepdefs.class);
        factory.stop();

        // Scenario 2
        factory.start();
        BellyStepdefs o2 = factory.getInstance(BellyStepdefs.class);
        factory.stop();

        assertNotNull(o1);
        assertNotSame(o1, o2);
    }

}
