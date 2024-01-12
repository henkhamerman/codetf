Refactoring Types: ['Extract Method']
orfjackal/retrolambda/Retrolambda.java
// Copyright © 2013-2015 Esko Luontola <www.orfjackal.net>
// This software is released under the Apache License 2.0.
// The license text is at http://www.apache.org/licenses/LICENSE-2.0

package net.orfjackal.retrolambda;

import net.orfjackal.retrolambda.files.*;
import net.orfjackal.retrolambda.interfaces.*;
import net.orfjackal.retrolambda.lambdas.*;

import java.io.IOException;
import java.net.*;
import java.nio.file.*;
import java.util.*;

public class Retrolambda {

    public static void run(Config config) throws Throwable {
        int bytecodeVersion = config.getBytecodeVersion();
        boolean defaultMethodsEnabled = config.isDefaultMethodsEnabled();
        Path inputDir = config.getInputDir();
        Path outputDir = config.getOutputDir();
        String classpath = config.getClasspath();
        List<Path> includedFiles = config.getIncludedFiles();
        System.out.println("Bytecode version: " + bytecodeVersion + " (" + config.getJavaVersion() + ")");
        System.out.println("Default methods:  " + defaultMethodsEnabled);
        System.out.println("Input directory:  " + inputDir);
        System.out.println("Output directory: " + outputDir);
        System.out.println("Classpath:        " + classpath);
        if (includedFiles != null) {
            System.out.println("Included files:   " + includedFiles.size());
        }

        if (!Files.isDirectory(inputDir)) {
            System.out.println("Nothing to do; not a directory: " + inputDir);
            return;
        }

        Thread.currentThread().setContextClassLoader(new NonDelegatingClassLoader(asUrls(classpath)));

        ClassHierarchyAnalyzer analyzer = new ClassHierarchyAnalyzer();
        ClassSaver saver = new ClassSaver(outputDir);
        Transformers transformers = new Transformers(bytecodeVersion, defaultMethodsEnabled, analyzer);
        LambdaClassSaver lambdaClassSaver = new LambdaClassSaver(saver, transformers);

        try (LambdaClassDumper dumper = new LambdaClassDumper(lambdaClassSaver)) {
            if (PreMain.isAgentLoaded()) {
                PreMain.setLambdaClassSaver(lambdaClassSaver);
            } else {
                dumper.install();
            }

            visitFiles(inputDir, includedFiles, new BytecodeFileVisitor() {
                @Override
                protected void visit(byte[] bytecode) {
                    analyzer.analyze(bytecode);
                }
            });

            // Because Transformers.backportLambdaClass() analyzes the lambda class,
            // adding it to the analyzer's list of classes, we must take care to
            // use the list of classes before that happened, or else we might accidentally
            // overwrite the lambda class.
            List<ClassInfo> interfaces = analyzer.getInterfaces();
            List<ClassInfo> classes = analyzer.getClasses();

            List<byte[]> transformed = new ArrayList<>();
            for (ClassInfo c : interfaces) {
                transformed.addAll(transformers.backportInterface(c.reader));
            }
            for (ClassInfo c : classes) {
                transformed.add(transformers.backportClass(c.reader));
            }

            // We need to load some of the classes (for calling the lambda metafactory)
            // so we need to take care not to modify any bytecode before loading them.
            for (byte[] bytecode : transformed) {
                saver.save(bytecode);
            }
        }
    }

    static void visitFiles(Path inputDir, List<Path> includedFiles, FileVisitor<Path> visitor) throws IOException {
        if (includedFiles != null) {
            visitor = new FilteringFileVisitor(includedFiles, visitor);
        }
        Files.walkFileTree(inputDir, visitor);
    }

    private static URL[] asUrls(String classpath) {
        String[] paths = classpath.split(System.getProperty("path.separator"));
        return Arrays.asList(paths).stream()
                .map(s -> Paths.get(s).toUri())
                .map(Retrolambda::uriToUrl)
                .toArray(URL[]::new);
    }

    private static URL uriToUrl(URI uri) {
        try {
            return uri.toURL();
        } catch (MalformedURLException e) {
            throw new RuntimeException(e);
        }
    }
}


File: retrolambda/src/main/java/net/orfjackal/retrolambda/files/BytecodeFileVisitor.java
// Copyright © 2013-2014 Esko Luontola <www.orfjackal.net>
// This software is released under the Apache License 2.0.
// The license text is at http://www.apache.org/licenses/LICENSE-2.0

package net.orfjackal.retrolambda.files;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;

public abstract class BytecodeFileVisitor extends SimpleFileVisitor<Path> {

    @Override
    public FileVisitResult visitFile(Path inputFile, BasicFileAttributes attrs) throws IOException {
        if (isJavaClass(inputFile)) {
            visit(Files.readAllBytes(inputFile));
        }
        return FileVisitResult.CONTINUE;
    }

    protected abstract void visit(byte[] bytecode);

    private static boolean isJavaClass(Path file) {
        return file.getFileName().toString().endsWith(".class");
    }
}


File: retrolambda/src/main/java/net/orfjackal/retrolambda/files/ClassSaver.java
// Copyright © 2013-2014 Esko Luontola <www.orfjackal.net>
// This software is released under the Apache License 2.0.
// The license text is at http://www.apache.org/licenses/LICENSE-2.0

package net.orfjackal.retrolambda.files;

import org.objectweb.asm.ClassReader;

import java.io.IOException;
import java.nio.file.*;

public class ClassSaver {

    private final Path outputDir;

    public ClassSaver(Path outputDir) {
        this.outputDir = outputDir;
    }

    public void save(byte[] bytecode) throws IOException {
        if (bytecode == null) {
            return;
        }
        ClassReader cr = new ClassReader(bytecode);
        Path outputFile = outputDir.resolve(cr.getClassName() + ".class");
        Files.createDirectories(outputFile.getParent());
        Files.write(outputFile, bytecode);
    }
}


File: retrolambda/src/main/java/net/orfjackal/retrolambda/lambdas/LambdaClassSaver.java
// Copyright © 2013-2014 Esko Luontola <www.orfjackal.net>
// This software is released under the Apache License 2.0.
// The license text is at http://www.apache.org/licenses/LICENSE-2.0

package net.orfjackal.retrolambda.lambdas;

import net.orfjackal.retrolambda.Transformers;
import net.orfjackal.retrolambda.files.ClassSaver;
import org.objectweb.asm.ClassReader;

public class LambdaClassSaver {

    private final ClassSaver saver;
    private final Transformers transformers;

    public LambdaClassSaver(ClassSaver saver, Transformers transformers) {
        this.saver = saver;
        this.transformers = transformers;
    }

    public void saveIfLambda(String className, byte[] bytecode) {
        if (LambdaReifier.isLambdaClassToReify(className)) {
            reifyLambdaClass(className, bytecode);
        }
    }

    private void reifyLambdaClass(String className, byte[] bytecode) {
        try {
            System.out.println("Saving lambda class: " + className);
            saver.save(transformers.backportLambdaClass(new ClassReader(bytecode)));

        } catch (Throwable t) {
            // print to stdout to keep in sync with other log output
            System.out.println("ERROR: Failed to backport lambda class: " + className);
            t.printStackTrace(System.out);
        }
    }
}


File: retrolambda/src/test/java/net/orfjackal/retrolambda/RetrolambdaTest.java
// Copyright © 2013-2014 Esko Luontola <www.orfjackal.net>
// This software is released under the Apache License 2.0.
// The license text is at http://www.apache.org/licenses/LICENSE-2.0

package net.orfjackal.retrolambda;

import org.junit.*;
import org.junit.rules.TemporaryFolder;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.containsInAnyOrder;

public class RetrolambdaTest {

    @Rule
    public final TemporaryFolder tempDir = new TemporaryFolder();

    private Path inputDir;

    private final List<Path> visitedFiles = new ArrayList<>();
    private final FileVisitor<Path> visitor = new SimpleFileVisitor<Path>() {
        @Override
        public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
            visitedFiles.add(file);
            return FileVisitResult.CONTINUE;
        }
    };
    private Path file1;
    private Path file2;
    private Path fileInSubdir;
    private Path outsider;

    @Before
    public void setup() throws IOException {
        inputDir = tempDir.newFolder("inputDir").toPath();
        file1 = Files.createFile(inputDir.resolve("file1.txt"));
        file2 = Files.createFile(inputDir.resolve("file2.txt"));
        Path subdir = inputDir.resolve("subdir");
        Files.createDirectory(subdir);
        fileInSubdir = Files.createFile(subdir.resolve("file.txt"));
        outsider = tempDir.newFile("outsider.txt").toPath();
    }

    @Test
    public void by_default_visits_all_files_recursively() throws IOException {
        Retrolambda.visitFiles(inputDir, null, visitor);

        assertThat(visitedFiles, containsInAnyOrder(file1, file2, fileInSubdir));
    }

    @Test
    public void when_included_files_is_set_then_visits_only_those_files() throws IOException {
        List<Path> includedFiles = Arrays.asList(file1, fileInSubdir);

        Retrolambda.visitFiles(inputDir, includedFiles, visitor);

        assertThat(visitedFiles, containsInAnyOrder(file1, fileInSubdir));
    }

    @Test
    public void ignores_included_files_that_are_outside_the_input_directory() throws IOException {
        List<Path> includedFiles = Arrays.asList(file1, outsider);

        Retrolambda.visitFiles(inputDir, includedFiles, visitor);

        assertThat(visitedFiles, containsInAnyOrder(file1));
    }
}
