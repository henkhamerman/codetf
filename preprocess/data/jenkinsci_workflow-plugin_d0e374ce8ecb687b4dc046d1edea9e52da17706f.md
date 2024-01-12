Refactoring Types: ['Inline Method', 'Move Attribute']
/workflow/multibranch/SCMBinder.java
/*
 * The MIT License
 *
 * Copyright 2015 CloudBees, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

package org.jenkinsci.plugins.workflow.multibranch;

import com.thoughtworks.xstream.converters.Converter;
import groovy.lang.GroovyShell;
import hudson.Extension;
import hudson.model.Queue;
import hudson.scm.SCM;
import hudson.util.DescribableList;
import java.io.IOException;
import java.io.Serializable;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.jenkinsci.plugins.workflow.cps.CpsFlowExecution;
import org.jenkinsci.plugins.workflow.cps.GroovyShellDecorator;
import org.jenkinsci.plugins.workflow.job.WorkflowRun;
import org.jenkinsci.plugins.workflow.pickles.Pickle;
import org.jenkinsci.plugins.workflow.support.pickles.SingleTypedPickleFactory;
import org.jenkinsci.plugins.workflow.support.pickles.XStreamPickle;

/**
 * Adds an {@code scm} global variable to the script.
 * This makes it possible to run {@code checkout scm} to get your project sources in the right branch.
 */
@Extension public class SCMBinder extends GroovyShellDecorator {

    @Override public void configureShell(CpsFlowExecution context, GroovyShell shell) {
        if (context == null) {
            return;
        }
        try {
            Queue.Executable exec = context.getOwner().getExecutable();
            if (exec instanceof WorkflowRun) {
                BranchJobProperty property = ((WorkflowRun) exec).getParent().getProperty(BranchJobProperty.class);
                if (property != null) {
                    shell.setVariable("scm", property.getBranch().getScm());
                }
            }
        } catch (IOException x) {
            Logger.getLogger(SCMBinder.class.getName()).log(Level.WARNING, null, x);
        }
    }

    /**
     * Ensures that {@code scm} is saved in its XML representation.
     * Necessary for {@code GitSCM} which is marked {@link Serializable}
     * yet includes a {@link DescribableList} which relies on a custom {@link Converter}.
     */
    @Extension public static class Pickler extends SingleTypedPickleFactory<SCM> {

        @Override protected Pickle pickle(SCM scm) {
            return new XStreamPickle(scm);
        }

    }

}


File: multibranch/src/main/java/org/jenkinsci/plugins/workflow/multibranch/WorkflowBranchProjectFactory.java
/*
 * The MIT License
 *
 * Copyright 2015 CloudBees, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

package org.jenkinsci.plugins.workflow.multibranch;

import hudson.Extension;
import hudson.model.Item;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;
import jenkins.branch.Branch;
import jenkins.branch.BranchProjectFactory;
import jenkins.branch.BranchProjectFactoryDescriptor;
import jenkins.branch.MultiBranchProject;
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition;
import org.jenkinsci.plugins.workflow.job.WorkflowJob;
import org.jenkinsci.plugins.workflow.job.WorkflowRun;
import org.kohsuke.stapler.DataBoundConstructor;

public class WorkflowBranchProjectFactory extends BranchProjectFactory<WorkflowJob,WorkflowRun> {
    
    private static final Logger LOGGER = Logger.getLogger(WorkflowBranchProjectFactory.class.getName());

    static final String SCRIPT = "jenkins.groovy";

    @DataBoundConstructor public WorkflowBranchProjectFactory() {}

    @Override public WorkflowJob newInstance(Branch branch) {
        WorkflowJob job = new WorkflowJob((WorkflowMultiBranchProject) getOwner(), branch.getName());
        setBranch(job, branch);
        return job;
    }

    @Override public Branch getBranch(WorkflowJob project) {
        return project.getProperty(BranchJobProperty.class).getBranch();
    }

    @Override public WorkflowJob setBranch(WorkflowJob project, Branch branch) {
        BranchJobProperty property = project.getProperty(BranchJobProperty.class);
        try {
            if (property == null) {
                property = new BranchJobProperty();
                setBranch(property, branch, project);
                project.addProperty(property);
            } else if (!property.getBranch().equals(branch)) {
                setBranch(property, branch, project);
                project.save();
            }
        } catch (IOException x) {
            LOGGER.log(Level.WARNING, null, x);
        }
        return project;
    }

    private void setBranch(BranchJobProperty property, Branch branch, WorkflowJob project) {
        property.setBranch(branch);
        // TODO DRY would perhaps be better for getDefinition to consult the property
        project.setDefinition(new CpsScmFlowDefinition(branch.getScm(), SCRIPT));
    }

    @Override public boolean isProject(Item item) {
        return item instanceof WorkflowJob && ((WorkflowJob) item).getProperty(BranchJobProperty.class) != null;
    }

    @Extension public static class DescriptorImpl extends BranchProjectFactoryDescriptor {

        @Override public String getDisplayName() {
            return "Fixed configuration";
        }

        @SuppressWarnings("rawtypes") // TODO fix super class
        @Override public boolean isApplicable(Class<? extends MultiBranchProject> clazz) {
            return WorkflowMultiBranchProject.class.isAssignableFrom(clazz);
        }

    }

}


File: multibranch/src/main/java/org/jenkinsci/plugins/workflow/multibranch/WorkflowMultiBranchProject.java
/*
 * The MIT License
 *
 * Copyright 2015 CloudBees, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

package org.jenkinsci.plugins.workflow.multibranch;

import hudson.Extension;
import hudson.model.ItemGroup;
import hudson.model.Queue;
import hudson.model.TaskListener;
import hudson.model.TopLevelItem;
import hudson.scm.SCM;
import hudson.scm.SCMDescriptor;
import java.io.IOException;
import java.util.List;
import jenkins.branch.BranchProjectFactory;
import jenkins.branch.MultiBranchProject;
import jenkins.branch.MultiBranchProjectDescriptor;
import jenkins.scm.api.SCMSource;
import jenkins.scm.api.SCMSourceCriteria;
import org.acegisecurity.Authentication;
import org.jenkinsci.plugins.workflow.job.WorkflowJob;
import org.jenkinsci.plugins.workflow.job.WorkflowRun;

/**
 * Representation of a set of workflows keyed off of source branches.
 */
@SuppressWarnings({"unchecked", "rawtypes"}) // core’s fault
public class WorkflowMultiBranchProject extends MultiBranchProject<WorkflowJob,WorkflowRun> {

    public WorkflowMultiBranchProject(ItemGroup parent, String name) {
        super(parent, name);
    }

    @Override protected BranchProjectFactory<WorkflowJob,WorkflowRun> newProjectFactory() {
        return new WorkflowBranchProjectFactory();
    }

    @Override public SCMSourceCriteria getSCMSourceCriteria(SCMSource source) {
        return new SCMSourceCriteria() {
            @Override public boolean isHead(SCMSourceCriteria.Probe probe, TaskListener listener) throws IOException {
                return probe.exists(WorkflowBranchProjectFactory.SCRIPT);
            }
        };
    }

    // TODO unnecessary to override once branch-api on 1.592+
    @Override public Authentication getDefaultAuthentication(Queue.Item item) {
        return getDefaultAuthentication();
    }

    @Extension public static class DescriptorImpl extends MultiBranchProjectDescriptor {

        @Override public String getDisplayName() {
            return "Multibranch Workflow";
        }

        @Override public TopLevelItem newInstance(ItemGroup parent, String name) {
            return new WorkflowMultiBranchProject(parent, name);
        }

        @Override public List<SCMDescriptor<?>> getSCMDescriptors() {
            // TODO this is a problem. We need to select only those compatible with Workflow.
            // Yet SCMDescriptor.isApplicable requires an actual Job, whereas we can only pass WorkflowJob.class!
            // Can we create a dummy WorkflowJob instance?
            return SCM.all();
        }

    }

}


File: multibranch/src/test/java/org/jenkinsci/plugins/workflow/multibranch/SCMBinderTest.java
/*
 * The MIT License
 *
 * Copyright 2015 CloudBees, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

package org.jenkinsci.plugins.workflow.multibranch;

import jenkins.branch.BranchProperty;
import jenkins.branch.BranchSource;
import jenkins.branch.DefaultBranchPropertyStrategy;
import jenkins.plugins.git.GitSCMSource;
import org.jenkinsci.plugins.scriptsecurity.scripts.ScriptApproval;
import org.jenkinsci.plugins.workflow.job.WorkflowJob;
import org.jenkinsci.plugins.workflow.job.WorkflowRun;
import org.jenkinsci.plugins.workflow.steps.scm.GitSampleRepoRule;
import org.jenkinsci.plugins.workflow.test.steps.SemaphoreStep;
import org.junit.Test;
import static org.junit.Assert.*;
import org.junit.ClassRule;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.runners.model.Statement;
import org.jvnet.hudson.test.BuildWatcher;
import org.jvnet.hudson.test.RestartableJenkinsRule;

public class SCMBinderTest {

    @ClassRule public static BuildWatcher buildWatcher = new BuildWatcher();
    @Rule public RestartableJenkinsRule story = new RestartableJenkinsRule();
    @Rule public GitSampleRepoRule sampleRepo = new GitSampleRepoRule();

    @Test public void scmPickle() throws Exception {
        story.addStep(new Statement() {
            @Override public void evaluate() throws Throwable {
                sampleRepo.write("jenkins.groovy", "semaphore 'wait'; node {checkout scm; echo readFile('file')}");
                sampleRepo.write("file", "initial content");
                sampleRepo.git("add", "jenkins.groovy");
                sampleRepo.git("commit", "--all", "--message=flow");
                WorkflowMultiBranchProject mp = story.j.jenkins.createProject(WorkflowMultiBranchProject.class, "p");
                mp.getSourcesList().add(new BranchSource(new GitSCMSource(null, sampleRepo.toString(), "", "*", "", false), new DefaultBranchPropertyStrategy(new BranchProperty[0])));
                mp.scheduleBuild2(0, null).get();
                WorkflowJob p = mp.getItem("master");
                SemaphoreStep.waitForStart("wait/1", null);
                WorkflowRun b1 = p.getLastBuild();
                assertNotNull(b1);
            }
        });
        story.addStep(new Statement() {
            @Override public void evaluate() throws Throwable {
                SemaphoreStep.success("wait/1", null);
                WorkflowJob p = story.j.jenkins.getItemByFullName("p/master", WorkflowJob.class);
                assertNotNull(p);
                WorkflowRun b1 = p.getLastBuild();
                assertNotNull(b1);
                assertEquals(1, b1.getNumber());
                story.j.assertLogContains("initial content", story.j.waitForCompletion(b1));
            }
        });
    }

    @Ignore("TODO currently will print `subsequent content` in b1")
    @Test public void exactRevision() throws Exception {
        story.addStep(new Statement() {
            @Override public void evaluate() throws Throwable {
                sampleRepo.write("jenkins.groovy", "semaphore 'wait'; node {checkout scm; echo readFile('file')}");
                sampleRepo.write("file", "initial content");
                sampleRepo.git("add", "jenkins.groovy");
                sampleRepo.git("commit", "--all", "--message=flow");
                WorkflowMultiBranchProject mp = story.j.jenkins.createProject(WorkflowMultiBranchProject.class, "p");
                mp.getSourcesList().add(new BranchSource(new GitSCMSource(null, sampleRepo.toString(), "", "*", "", false), new DefaultBranchPropertyStrategy(new BranchProperty[0])));
                mp.scheduleBuild2(0, null).get();
                WorkflowJob p = mp.getItem("master");
                SemaphoreStep.waitForStart("wait/1", null);
                WorkflowRun b1 = p.getLastBuild();
                assertNotNull(b1);
                assertEquals(1, b1.getNumber());
                sampleRepo.write("jenkins.groovy", "node {checkout scm; echo readFile('file').toUpperCase()}");
                ScriptApproval.get().approveSignature("method java.lang.String toUpperCase");
                sampleRepo.write("file", "subsequent content");
                sampleRepo.git("commit", "--all", "--message=tweaked");
                SemaphoreStep.success("wait/1", null);
                WorkflowRun b2 = story.j.assertBuildStatusSuccess(p.scheduleBuild2(0));
                assertEquals(2, b2.getNumber());
                story.j.assertLogContains("initial content", story.j.waitForCompletion(b1));
                story.j.assertLogContains("SUBSEQUENT CONTENT", b2);
            }
        });
    }

}
