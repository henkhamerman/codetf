Refactoring Types: ['Extract Method']
pm/workflow/core/node/StateNode.java
/**
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

package org.jbpm.workflow.core.node;

import java.util.HashMap;
import java.util.Map;

import org.kie.api.definition.process.Connection;
import org.jbpm.workflow.core.Constraint;
import org.jbpm.workflow.core.impl.ConnectionRef;

public class StateNode extends CompositeContextNode implements Constrainable {

	private static final long serialVersionUID = 510l;
	
    private Map<ConnectionRef, Constraint> constraints = new HashMap<ConnectionRef, Constraint>();
   
    public void setConstraints(Map<ConnectionRef, Constraint> constraints) {
        this.constraints = constraints;
    }

    public void setConstraint(final Connection connection, final Constraint constraint) {
		if (connection == null) {
			throw new IllegalArgumentException("connection is null");
		}
		if (!getDefaultOutgoingConnections().contains(connection)) {
			throw new IllegalArgumentException("connection is unknown:"	+ connection);
		}
		addConstraint(new ConnectionRef(
			connection.getTo().getId(), connection.getToType()), constraint);
	}

    public void addConstraint(ConnectionRef connectionRef, Constraint constraint) {
    	if (connectionRef == null) {
    		throw new IllegalArgumentException(
				"A state node only accepts constraints linked to a connection");
    	}
        constraints.put(connectionRef, constraint);
    }
    
    public Constraint getConstraint(String name){
        return constraints.get(name);
    }
    
    public Map<ConnectionRef, Constraint> getConstraints(){
        return constraints;
    }

    public Constraint getConstraint(final Connection connection) {
        if (connection == null) {
            throw new IllegalArgumentException("connection is null");
        }
        ConnectionRef ref = new ConnectionRef(connection.getTo().getId(), connection.getToType());
        return this.constraints.get(ref);
    }

}


File: jbpm-flow/src/main/java/org/jbpm/workflow/instance/WorkflowProcessInstanceUpgrader.java
/**
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

package org.jbpm.workflow.instance;

import java.util.HashMap;
import java.util.Map;

import org.drools.core.common.InternalKnowledgeRuntime;
import org.jbpm.ruleflow.core.RuleFlowProcess;
import org.jbpm.ruleflow.instance.RuleFlowProcessInstance;
import org.jbpm.workflow.core.impl.NodeImpl;
import org.jbpm.workflow.instance.impl.NodeInstanceImpl;
import org.jbpm.workflow.instance.impl.WorkflowProcessInstanceImpl;
import org.kie.api.definition.process.Node;
import org.kie.api.definition.process.NodeContainer;
import org.kie.api.definition.process.Process;
import org.kie.api.definition.process.WorkflowProcess;
import org.kie.api.runtime.KieRuntime;
import org.kie.api.runtime.process.NodeInstance;
import java.util.Stack;

public class WorkflowProcessInstanceUpgrader {

    public static void upgradeProcessInstance( KieRuntime kruntime, long processInstanceId, String processId,
            Map<String, Long> nodeMapping) {
        if (nodeMapping == null) {
            nodeMapping = new HashMap<String, Long>();
        }
        WorkflowProcessInstanceImpl processInstance = (WorkflowProcessInstanceImpl)
                kruntime.getProcessInstance(processInstanceId);
        if (processInstance == null) {
            throw new IllegalArgumentException("Could not find process instance " + processInstanceId);
        }
        if (processId == null) {
            throw new IllegalArgumentException("Null process id");
        }
        WorkflowProcess process = (WorkflowProcess)
                kruntime.getKieBase().getProcess(processId);
        if (process == null) {
            throw new IllegalArgumentException("Could not find process " + processId);
        }
        if (processInstance.getProcessId().equals(processId)) {
            return;
        }
        synchronized (processInstance) {
            org.kie.api.definition.process.Process oldProcess = processInstance.getProcess();
            processInstance.disconnect();
            processInstance.setProcess(oldProcess);
            updateNodeInstances(processInstance, nodeMapping);
            processInstance.setKnowledgeRuntime((InternalKnowledgeRuntime) kruntime);
            processInstance.setProcess(process);
            processInstance.reconnect();
        }
    }

    /**
     * Do the same as upgradeProcessInstance() but user provides mapping by node names, not by node id's
     * @param kruntime
     * @param activeProcessId
     * @param newProcessId
     * @param nodeNamesMapping
     */
    public static void upgradeProcessInstanceByNodeNames(
            KieRuntime kruntime,
            Long fromProcessId,
            String toProcessId,
            Map<String, String> nodeNamesMapping) {

        Map<String, Long> nodeIdMapping = new HashMap<String, Long>();

        String fromProcessIdString = kruntime.getProcessInstance(fromProcessId).getProcessId();
        Process processFrom = kruntime.getKieBase().getProcess(fromProcessIdString);
        Process processTo = kruntime.getKieBase().getProcess(toProcessId);

        for (Map.Entry<String, String> entry : nodeNamesMapping.entrySet()) {
            String from = null;
            Long to = null;

            if (processFrom instanceof WorkflowProcess) {
                from = getNodeId(((WorkflowProcess) processFrom).getNodes(), entry.getKey(), true);
            } else if (processFrom instanceof RuleFlowProcess) {
                from = getNodeId(((RuleFlowProcessInstance) processFrom).getWorkflowProcess().getNodes(), entry.getKey(), true);
            } else if (processFrom != null) {
                throw new IllegalArgumentException("Suported processes are WorkflowProcess and RuleFlowProcess, it was:" + processFrom.getClass());
            } else {
                throw new IllegalArgumentException("Can not find process with id: " + fromProcessIdString);
            }

            if (processTo instanceof WorkflowProcess) {
                to = Long.valueOf(getNodeId(((WorkflowProcess) processTo).getNodes(), entry.getValue(), false));
            } else if (processTo instanceof RuleFlowProcess) {
                to = Long.valueOf(getNodeId(((RuleFlowProcessInstance) processTo).getWorkflowProcess().getNodes(), entry.getValue(), false));
            } else if (processTo != null) {
                throw new IllegalArgumentException("Suported processes are WorkflowProcess and RuleFlowProcess, it was:" + processTo.getClass());
            } else {
                throw new IllegalArgumentException("Can not find process with id: " + toProcessId);
            }
            nodeIdMapping.put(from, to);
        }

        upgradeProcessInstance(kruntime, fromProcessId, toProcessId, nodeIdMapping);
    }

    private static String getNodeId(Node[] nodes, String nodeName, boolean unique) {

        Stack<Node> nodeStack = new Stack<Node>();
        for (Node node : nodes) {
            nodeStack.push(node);
        }

        Node match = null;
        while (!nodeStack.isEmpty()) {
            Node topNode = nodeStack.pop();

            if (topNode.getName().compareTo(nodeName) == 0) {
                match = topNode;
                break;
            }

            if (topNode instanceof NodeContainer) {
                for (Node node : ((NodeContainer) topNode).getNodes()) {
                    nodeStack.push(node);
                }
            }
        }

        if (match == null) {
            throw new IllegalArgumentException("No node with name " + nodeName);
        }

        String id = "";

        if (unique) {
            while (!(match.getNodeContainer() instanceof Process)) {
                id = ":" + match.getId() + id;
                match = (Node) match.getNodeContainer();
            }
        }

        id = match.getId() + id;

        return id;
    }

    private static void updateNodeInstances(NodeInstanceContainer nodeInstanceContainer, Map<String, Long> nodeMapping) {
        for (NodeInstance nodeInstance : nodeInstanceContainer.getNodeInstances()) {
            String oldNodeId = ((NodeImpl)
                    ((org.jbpm.workflow.instance.NodeInstance) nodeInstance).getNode()).getUniqueId();
            Long newNodeId = nodeMapping.get(oldNodeId);
            if (newNodeId == null) {
                newNodeId = nodeInstance.getNodeId();
            }

            // clean up iteration levels for removed (old) nodes 
            Map<String, Integer> iterLevels = ((WorkflowProcessInstanceImpl) nodeInstance.getProcessInstance()).getIterationLevels();
            String uniqueId = (String) ((NodeImpl) nodeInstance.getNode()).getMetaData("UniqueId");
            iterLevels.remove(uniqueId);
            // and now set to new node id
            ((NodeInstanceImpl) nodeInstance).setNodeId(newNodeId);

            if (nodeInstance instanceof NodeInstanceContainer) {
                updateNodeInstances((NodeInstanceContainer) nodeInstance, nodeMapping);
            }
        }

    }

}


File: jbpm-human-task/jbpm-human-task-core/src/test/java/org/jbpm/services/task/LifeCycleBaseTest.java
/**
 * Copyright 2010 JBoss Inc
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package org.jbpm.services.task;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.StringReader;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.jbpm.services.task.exception.PermissionDeniedException;
import org.jbpm.services.task.impl.factories.TaskFactory;
import org.jbpm.services.task.impl.model.xml.JaxbContent;
import org.jbpm.services.task.utils.ContentMarshallerHelper;
import org.junit.Test;
import org.kie.api.task.model.Comment;
import org.kie.api.task.model.Content;
import org.kie.api.task.model.Group;
import org.kie.api.task.model.I18NText;
import org.kie.api.task.model.OrganizationalEntity;
import org.kie.api.task.model.Status;
import org.kie.api.task.model.Task;
import org.kie.api.task.model.TaskSummary;
import org.kie.api.task.model.User;
import org.kie.internal.task.api.TaskModelProvider;
import org.kie.internal.task.api.model.AccessType;
import org.kie.internal.task.api.model.ContentData;
import org.kie.internal.task.api.model.FaultData;
import org.kie.internal.task.api.model.InternalComment;
import org.kie.internal.task.api.model.InternalI18NText;
import org.kie.internal.task.api.model.InternalOrganizationalEntity;
import org.kie.internal.task.api.model.InternalPeopleAssignments;
import org.kie.internal.task.api.model.InternalTask;
import org.kie.internal.task.api.model.InternalTaskData;

public abstract class LifeCycleBaseTest extends HumanTaskServicesBaseTest {

    
    @Test
    /*
    * Related to BZ-1105868 
    */
    public void testWithNoTaskAndEmptyLists(){
      
      List<TaskSummary> tasksAssignedAsPotentialOwner = taskService.getTasksAssignedAsPotentialOwner("nouser", new ArrayList<String>());
      assertTrue(tasksAssignedAsPotentialOwner.isEmpty());
      
      List<TaskSummary> tasksAssignedAsPotentialOwner2 = taskService.getTasksAssignedAsPotentialOwner("nouser", (List<String>)null);
      assertTrue(tasksAssignedAsPotentialOwner2.isEmpty());
      
      List<TaskSummary> tasksAssignedAsPotentialOwner3 = taskService.getTasksAssignedAsPotentialOwner("", (List<String>)null);
      assertTrue(tasksAssignedAsPotentialOwner3.isEmpty());
      
      List<TaskSummary> tasksAssignedAsPotentialOwner4 = taskService.getTasksAssignedAsPotentialOwner(null,(List<String>) null);
      assertTrue(tasksAssignedAsPotentialOwner4.isEmpty());
      
      List<TaskSummary> tasksAssignedAsPotentialOwner5 = taskService.getTasksAssignedAsPotentialOwner("salaboy", (List<String>)null);
      assertTrue(tasksAssignedAsPotentialOwner5.isEmpty());
      
      List<TaskSummary> tasks = taskService.getTasksAssignedAsPotentialOwnerByStatusByGroup("Bobba Fet", null, null);
      assertTrue(tasks.isEmpty());
      
      List<TaskSummary> tasks2 = taskService.getTasksAssignedAsPotentialOwnerByStatusByGroup("Bobba Fet", new ArrayList<String>(), null);
      assertTrue(tasks2.isEmpty());
      
      List<TaskSummary> tasks3 = taskService.getTasksAssignedAsPotentialOwnerByStatusByGroup("Bobba Fet", new ArrayList<String>(), new ArrayList<Status>());
      assertTrue(tasks3.isEmpty());
      
      List<TaskSummary> tasks4 = taskService.getTasksAssignedAsPotentialOwnerByStatusByGroup("admin", new ArrayList<String>(), new ArrayList<Status>());
      assertTrue(tasks4.isEmpty());
              
      
    }
  
    @Test
    public void testNewTaskWithNoPotentialOwners() {

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { businessAdministrators = [ new User('Administrator') ],}),";
        str += "name =  'This is my task name' })";


        Task task = TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Task should remain in Created state with no actual owner

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(task1.getTaskData().getStatus(), Status.Created);
        assertNull(task1.getTaskData().getActualOwner());
    }

    @Test
    public void testNewTaskWithSinglePotentialOwner() {
        
        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet')  ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";


        Task task = TaskFactory.evalTask(new StringReader(str));

        taskService.addTask(task, new HashMap<String, Object>());
        long taskId = task.getId();

        // Task should be assigned to the single potential owner and state set to Reserved
        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        String potOwner = "Bobba Fet"; 
        assertEquals(potOwner, task1.getTaskData().getActualOwner().getId());
        
        taskService.getTasksAssignedAsPotentialOwner(potOwner, "en-UK");
    }
    
    

    @Test
    public void testNewTaskWithContent() {
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";

        ContentData data = ContentMarshallerHelper.marshal("content", null);

        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, data);

        long taskId = task.getId();

        // Task should be assigned to the single potential owner and state set to Reserved


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(AccessType.Inline, ((InternalTaskData) task1.getTaskData()).getDocumentAccessType());
        assertEquals("java.lang.String", task1.getTaskData().getDocumentType());
        long contentId = task1.getTaskData().getDocumentContentId();
        assertTrue(contentId != -1);

        Content content = taskService.getContentById(contentId);
        Object unmarshalledObject = ContentMarshallerHelper.unmarshall(content.getContent(), null);
        assertEquals("content", unmarshalledObject.toString());
        xmlRoundTripContent(content);
    }
    
    @Test
    public void testNewTaskWithMapContent() {
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ],businessAdministrators = [ new User('Administrator') ], }),";                        
        str += "name =  'This is my task name' })";
            
        Map<String, Object> variablesMap = new HashMap<String, Object>();
        variablesMap.put("key1", "value1");
        variablesMap.put("key2", null);
        variablesMap.put("key3", "value3");
        ContentData data = ContentMarshallerHelper.marshal(variablesMap, null);
        
        Task task = ( Task )  TaskFactory.evalTask( new StringReader( str ));
        taskService.addTask( task, data );
        
        long taskId = task.getId();
        
        // Task should be assigned to the single potential owner and state set to Reserved
        Task task1 = taskService.getTaskById( taskId );
        assertEquals( AccessType.Inline, ((InternalTaskData) task1.getTaskData()).getDocumentAccessType() );
        assertEquals( "java.util.HashMap", task1.getTaskData().getDocumentType() );
        long contentId = task1.getTaskData().getDocumentContentId();
        assertTrue( contentId != -1 ); 
       
        // content
        Content content = taskService.getContentById(contentId);
        Object unmarshalledObject = ContentMarshallerHelper.unmarshall(content.getContent(), null);
        if(!(unmarshalledObject instanceof Map)){
            fail("The variables should be a Map");
        }
        Map<String, Object> unmarshalledvars = (Map<String, Object>)unmarshalledObject;
        JaxbContent jaxbContent = xmlRoundTripContent(content);
        assertNotNull( "Jaxb Content map not filled", jaxbContent.getContentMap());
        
        assertEquals("value1",unmarshalledvars.get("key1") );
        assertNull(unmarshalledvars.get("key2") );
        assertEquals("value3",unmarshalledvars.get("key3") );
    }
    
    /*
     * This test shows how to work with a task and save severeal intermediate steps of the content that the 
     * task is handling. 
     * The input parameters for this task are: (key1,value1) (key3,value3). 
     * 
     * (key2, null) is a variable that is input/output, this means that is a variable that comes defined, but it value can be changed
     * by the user
     * 
     * The expected outputs for the task are: (key2, value2), (key4, value4) (key5, value5) (key6, value6)
     */
    @Test
    public void testNewTaskWithMapContentAndOutput() {
        
        
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ],businessAdministrators = [ new User('Administrator') ], }),";                        
        str += "name =  'This is my task name' })";
            
        Map<String, Object> variablesMap = new HashMap<String, Object>();
        variablesMap.put("key1", "value1");
        variablesMap.put("key2", null);
        variablesMap.put("key3", "value3");
        ContentData data = ContentMarshallerHelper.marshal(variablesMap, null);
        
        Task task = ( Task )  TaskFactory.evalTask( new StringReader( str ));
        taskService.addTask( task, data );
        
        long taskId = task.getId();
        
        // Task should be assigned to the single potential owner and state set to Reserved
        
        
        Task task1 = taskService.getTaskById( taskId );
        assertEquals( AccessType.Inline, ((InternalTaskData) task1.getTaskData()).getDocumentAccessType() );
        assertEquals( "java.util.HashMap", task1.getTaskData().getDocumentType() );
        long contentId = task1.getTaskData().getDocumentContentId();
        assertTrue( contentId != -1 ); 

        
        
        Content content = taskService.getContentById(contentId);
        Object unmarshalledObject = ContentMarshallerHelper.unmarshall(content.getContent(), null);
        if(!(unmarshalledObject instanceof Map)){
            fail("The variables should be a Map");
        }
        xmlRoundTripContent(content);
        
        Map<String, Object> unmarshalledvars = (Map<String, Object>) unmarshalledObject;
        
        assertEquals("value1",unmarshalledvars.get("key1") );
        assertNull(unmarshalledvars.get("key2") );
        assertEquals("value3",unmarshalledvars.get("key3") );
        
        taskService.start(taskId,"Bobba Fet" );
        
        task1 = taskService.getTaskById( taskId );
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        // Once the task has being started the user decide to start working on it. 
        
        
        Map<String, Object> intermediateOutputContentMap = new HashMap<String, Object>();
        
        intermediateOutputContentMap.put("key2", "value2");
        intermediateOutputContentMap.put("key4", "value4");
        
        
        taskService.addContent(taskId, intermediateOutputContentMap);
        
        Map<String, Object> finalOutputContentMap = new HashMap<String, Object>();
         finalOutputContentMap.put("key5", "value5");
        finalOutputContentMap.put("key6", "value6");
        
        
        taskService.complete(taskId,"Bobba Fet", finalOutputContentMap);
        
        task1 = taskService.getTaskById( taskId );
        assertEquals(Status.Completed, task1.getTaskData().getStatus());
        long outputContentId = task1.getTaskData().getOutputContentId();
        Content contentById = taskService.getContentById(outputContentId);
        
        unmarshalledObject = ContentMarshallerHelper.unmarshall(contentById.getContent(), null);
        assertNotNull(unmarshalledObject);
        if(!(unmarshalledObject instanceof Map)){
            fail("The variables should be a Map");
        
        }
        assertTrue(((Map<String, Object>)unmarshalledObject).containsKey("key2"));
        assertTrue(((Map<String, Object>)unmarshalledObject).containsKey("key4"));
        assertTrue(((Map<String, Object>)unmarshalledObject).containsKey("key5"));
        assertTrue(((Map<String, Object>)unmarshalledObject).containsKey("key6"));
        xmlRoundTripContent(contentById);
    }
    
    @Test
    public void testNewTaskWithLargeContent() {
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";

        String largeContent = "";
        for (int i = 0; i < 1000; i++) {
            largeContent += i + "xxxxxxxxx";
        }

        ContentData data = ContentMarshallerHelper.marshal(largeContent, null);

        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, data);

        long taskId = task.getId();

        // Task should be assigned to the single potential owner and state set to Reserved


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(AccessType.Inline, ((InternalTaskData) task1.getTaskData()).getDocumentAccessType());
        assertEquals("java.lang.String", task1.getTaskData().getDocumentType());
        long contentId = task1.getTaskData().getDocumentContentId();
        assertTrue(contentId != -1);

        Content content = taskService.getContentById(contentId);
        Object unmarshalledObject = ContentMarshallerHelper.unmarshall(content.getContent(), null);
        assertEquals(largeContent, unmarshalledObject.toString());
        xmlRoundTripContent(content);
    }

    @Test
    public void testClaimWithMultiplePotentialOwners() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'),new User('Darth Vader') ], businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // A Task with multiple potential owners moves to "Ready" state until someone claims it.


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task1.getTaskData().getStatus());


        taskService.claim(taskId, "Darth Vader");

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testClaimWithGroupAssignee() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new Group('Knights Templer' )], businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // A Task with multiple potential owners moves to "Ready" state until someone claims it.


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task1.getTaskData().getStatus());

        taskService.claim(taskId, "Darth Vader");

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }
    
    
     @Test
    public void testForwardGroupClaimQueryAssignee() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('salaboy' )], businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";
        
        // One potential owner, should go straight to state Reserved
        String str2 = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str2 += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('salaboy')], businessAdministrators = [ new User('Administrator') ], }),";
        str2 += "name = 'This is my second task name' })";

         // One potential owner, should go straight to state Reserved
        String str3 = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str3 += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new Group('Crusaders'), new Group('Knights Templer')], businessAdministrators = [ new User('Administrator') ], }),";
        str3 += "name = 'This is my third task name' })";
        
        
        List<String> groupIds = new ArrayList<String>();
        
        groupIds.add("Knights Templer");
        groupIds.add("non existing group");
        groupIds.add("non existing group 2");
        groupIds.add("Crusaders");
        
        List<Status> statuses = new ArrayList<Status>();
        statuses.add(Status.Ready);
        statuses.add(Status.Created);
        statuses.add(Status.InProgress);
        statuses.add(Status.Reserved);
        

        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        
        
        Task task3 = (Task) TaskFactory.evalTask(new StringReader(str2));
        taskService.addTask(task3, new HashMap<String, Object>());
        
        Task task4 = (Task) TaskFactory.evalTask(new StringReader(str3));
        taskService.addTask(task4, new HashMap<String, Object>());
        
        List<TaskSummary> tasksAssignedByGroups = taskService.getTasksAssignedByGroups(groupIds);
        assertEquals(1, tasksAssignedByGroups.size());

        // A Task with multiple potential owners moves to "Ready" state until someone claims it.

          List<TaskSummary> allTasks = taskService.getTasksAssignedByGroups(groupIds);
        assertEquals(1, allTasks.size());
        List<TaskSummary> personalTasks = taskService.getTasksOwnedByStatus("salaboy", statuses, "en-UK");
        assertEquals(2, personalTasks.size());
        allTasks.addAll(personalTasks);
        assertEquals(3, allTasks.size());

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        List<TaskSummary> tasksAssignedAsPotentialOwner = taskService.getTasksAssignedAsPotentialOwner("salaboy", "en-UK");
        assertEquals(3, tasksAssignedAsPotentialOwner.size());
        
        taskService.forward(taskId, "salaboy", "Crusaders");

        
        allTasks = taskService.getTasksAssignedByGroups(groupIds);
        assertEquals(2, allTasks.size());
        personalTasks = taskService.getTasksOwnedByStatus("salaboy", statuses, "en-UK");
        assertEquals(1, personalTasks.size());
        allTasks.addAll(personalTasks);
        assertEquals(3, allTasks.size());
        
        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task2.getTaskData().getStatus());
        assertNull(task2.getTaskData().getActualOwner());
        assertEquals(1, task2.getPeopleAssignments().getPotentialOwners().size());
        List<TaskSummary> tasksAssignedByGroup = taskService.getTasksAssignedByGroup("Crusaders");
        
        assertEquals(2, tasksAssignedByGroup.size());
       
        
        tasksAssignedByGroups = taskService.getTasksAssignedByGroups(groupIds);
        assertEquals(2, tasksAssignedByGroups.size());
        
        taskService.claim(taskId, "salaboy");
        
        task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
        assertEquals("salaboy", task2.getTaskData().getActualOwner().getId());
        assertEquals(1, task2.getPeopleAssignments().getPotentialOwners().size());
        
        List<TaskSummary> tasksOwned = taskService.getTasksOwned("salaboy", "en-UK");
        assertEquals(2, tasksOwned.size());
  
        allTasks = taskService.getTasksAssignedByGroups(groupIds);
        assertEquals(1, allTasks.size());
        personalTasks = taskService.getTasksOwnedByStatus("salaboy", statuses, "en-UK");
        assertEquals(2, personalTasks.size());
        allTasks.addAll(personalTasks);
        assertEquals(3, allTasks.size());
        
        
    }

    @Test
    public void testStartFromReadyStateWithPotentialOwner() throws Exception {

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ], businessAdministrators = [ new User('Administrator') ],}),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // A Task with multiple potential owners moves to "Ready" state until someone claims it.


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task1.getTaskData().getStatus());

        // Go straight from Ready to Inprogress
        taskService.start(taskId, "Darth Vader");

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testStartFromReadyStateWithIncorrectPotentialOwner() {

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ], businessAdministrators = [ new User('Administrator') ],}),";
        str += "name = 'This is my task name'})";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        // A Task with multiple potential owners moves to "Ready" state until someone claims it.
        List<TaskSummary> tasksAssignedAsPotentialOwner = taskService.getTasksAssignedAsPotentialOwner("Bobba Fet", "en-UK");
        assertEquals(1, tasksAssignedAsPotentialOwner.size());
        
        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task1.getTaskData().getStatus());

        // State should not change as user isn't potential owner


        PermissionDeniedException denied = null;
        try {
            taskService.start(taskId, "Tony Stark");
        } catch (PermissionDeniedException e) {
            denied = e;
        }

        assertNotNull("Should get permissed denied exception", denied);

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task2.getTaskData().getStatus());
        assertNull(task2.getTaskData().getActualOwner());
    }

    @Test
    public void testStartFromReserved() throws Exception {

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ], businessAdministrators = [ new User('Administrator') ],}),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Task should be assigned to the single potential owner and state set to Reserved


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Bobba Fet", task1.getTaskData().getActualOwner().getId());

        // Should change to InProgress

        taskService.start(taskId, "Bobba Fet");




        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task2.getTaskData().getStatus());
        assertEquals("Bobba Fet", task1.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testStartFromReservedWithIncorrectUser() {

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ], businessAdministrators = [ new User('Administrator') ],}),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Task should be assigned to the single potential owner and state set to Reserved

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Bobba Fet", task1.getTaskData().getActualOwner().getId());

        // Should change not change



        PermissionDeniedException denied = null;
        try {
            taskService.start(taskId, "Tony Stark");
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
        assertEquals("Bobba Fet", task1.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testStop() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress
        taskService.start(taskId, "Darth Vader");

        taskService.getTaskById(taskId);
        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Now Stop

        taskService.stop(taskId, "Darth Vader");


        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testStopWithIncorrectUser() {

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");




        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Should not stop


        PermissionDeniedException denied = null;
        try {
            taskService.stop(taskId, "Bobba Fet");
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);



        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testReleaseFromInprogress() throws Exception {


        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");



        taskService.getTaskById(taskId);
        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Released

        taskService.release(taskId, "Darth Vader");




        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task2.getTaskData().getStatus());
        assertNull(task2.getTaskData().getActualOwner());
    }

    public void testReleaseFromReserved() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name'})";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.claim(taskId, "Darth Vader");




        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Released

        taskService.release(taskId, "Darth Vader");

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task2.getTaskData().getStatus());
        assertNull(task2.getTaskData().getActualOwner());
    }

    @Test
    public void testReleaseWithIncorrectUser() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.claim(taskId, "Darth Vader");




        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is not changed


        PermissionDeniedException denied = null;
        try {
            taskService.release(taskId, "Bobba Fet");
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);



        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testSuspendFromReady() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name'})";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Check is Ready

        taskService.getTaskById(taskId);
        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task1.getTaskData().getStatus());
        assertNull(task1.getTaskData().getActualOwner());

        // Check is Suspended

        taskService.suspend(taskId, "Darth Vader");




        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Suspended, task2.getTaskData().getStatus());
        assertEquals(Status.Ready, task2.getTaskData().getPreviousStatus());
        assertNull(task1.getTaskData().getActualOwner());
    }

    @Test
    public void testSuspendFromReserved() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Check is Reserved

        taskService.claim(taskId, "Darth Vader");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Suspended

        taskService.suspend(taskId, "Darth Vader");

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getPreviousStatus());
        assertEquals(Status.Suspended, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testSuspendFromReservedWithIncorrectUser() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Check is Reserved
        taskService.claim(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is not changed


        PermissionDeniedException denied = null;
        try {
            taskService.suspend(taskId, "Bobba Fet");
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);



        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test // FIX
    public void testResumeFromReady() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Check is Ready


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task1.getTaskData().getStatus());
        assertNull(task1.getTaskData().getActualOwner());

        // Check is Suspended

        taskService.suspend(taskId, "Darth Vader");

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Suspended, task2.getTaskData().getStatus());
        assertEquals(Status.Ready, task2.getTaskData().getPreviousStatus());
        assertNull(task1.getTaskData().getActualOwner());

        // Check is Resumed

        taskService.resume(taskId, "Darth Vader");

        Task task3 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task3.getTaskData().getStatus());
        assertEquals(Status.Suspended, task3.getTaskData().getPreviousStatus());
        assertNull(task3.getTaskData().getActualOwner());
    }

    @Test
    public void testResumeFromReserved() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Check is Reserved

        taskService.claim(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is suspended

        taskService.suspend(taskId, "Darth Vader");




        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getPreviousStatus());
        assertEquals(Status.Suspended, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());

        // Check is Resumed

        taskService.resume(taskId, "Darth Vader");

        Task task3 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task3.getTaskData().getStatus());
        assertEquals(Status.Suspended, task3.getTaskData().getPreviousStatus());
        assertEquals("Darth Vader", task3.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testResumeFromReservedWithIncorrectUser() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Check is Reserved

        taskService.claim(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check not changed

        PermissionDeniedException denied = null;
        try {
            taskService.suspend(taskId, "Bobba Fet");
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testSkipFromReady() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { skipable = true} ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Check is Complete

        taskService.skip(taskId, "Darth Vader");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Obsolete, task1.getTaskData().getStatus());
        assertNull(task1.getTaskData().getActualOwner());
    }

    @Test
    public void testSkipFromReserved() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { skipable = true} ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready 

        taskService.claim(taskId, "Darth Vader");


        // Check is Complete

        taskService.skip(taskId, "Darth Vader");

        taskService.getTaskById(taskId);
        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Obsolete, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testDelegateFromReady() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());
        long taskId = task.getId();

        // Check is Delegated
        taskService.delegate(taskId, "Darth Vader", "Tony Stark");




        Task task2 = taskService.getTaskById(taskId);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Darth Vader");
        assertTrue(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Tony Stark");
        assertTrue(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        assertEquals("Tony Stark", task2.getTaskData().getActualOwner().getId());
        // this was checking for ready, but it should be reserved.. it was an old bug
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
    }

    @Test
    public void testDelegateFromReserved() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Claim and Reserved

        taskService.claim(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Delegated

        taskService.delegate(taskId, "Darth Vader", "Tony Stark");




        Task task2 = taskService.getTaskById(taskId);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Darth Vader");
        assertTrue(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Tony Stark");
        assertTrue(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        assertEquals("Tony Stark", task2.getTaskData().getActualOwner().getId());
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
    }

    @Test
    public void testDelegateFromReservedWithIncorrectUser() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());
        long taskId = task.getId();

        // Claim and Reserved

        taskService.claim(taskId, "Darth Vader");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check was not delegated


        PermissionDeniedException denied = null;
        try {
            taskService.delegate(taskId, "Bobba Fet", "Tony Stark");
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);

        Task task2 = taskService.getTaskById(taskId);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Darth Vader");
        assertTrue(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Tony Stark");
        assertFalse(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
    }

    public void testForwardFromReady() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Check is Forwarded

        taskService.forward(taskId, "Darth Vader", "Tony Stark");


        Task task2 = taskService.getTaskById(taskId);
        assertFalse(task2.getPeopleAssignments().getPotentialOwners().contains("Darth Vader"));
        assertTrue(task2.getPeopleAssignments().getPotentialOwners().contains("Tony Stark"));
        assertNull(task2.getTaskData().getActualOwner());
        assertEquals(Status.Ready, task2.getTaskData().getStatus());
    }

    @Test
    public void testForwardFromReserved() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Claim and Reserved

        taskService.claim(taskId, "Darth Vader");




        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Delegated

        taskService.forward(taskId, "Darth Vader", "Tony Stark");


        Task task2 = taskService.getTaskById(taskId);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Darth Vader");
        assertFalse(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Tony Stark");
        assertTrue(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        assertNull(task2.getTaskData().getActualOwner());
        assertEquals(Status.Ready, task2.getTaskData().getStatus());
    }

    @Test
    public void testForwardFromReservedWithIncorrectUser() throws Exception {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Claim and Reserved

        taskService.claim(taskId, "Darth Vader");




        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check was not delegated


        PermissionDeniedException denied = null;
        try {
            taskService.forward(taskId, "Bobba Fet", "Tony Stark");
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);



        Task task2 = taskService.getTaskById(taskId);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Darth Vader");
        assertTrue(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Tony Stark");
        assertFalse(task2.getPeopleAssignments().getPotentialOwners().contains(user));
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
        assertEquals(Status.Reserved, task2.getTaskData().getStatus());
    }

    @Test
    public void testComplete() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Complete

        taskService.complete(taskId, "Darth Vader", null);




        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Completed, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testCompleteWithIncorrectUser() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Should not complete as wrong user


        PermissionDeniedException denied = null;
        try {
            taskService.complete(taskId, "Bobba Fet", null);
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);



        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testCompleteWithContent() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        //ContentData data = ContentMarshallerHelper.marshal("content", null);
        Map<String, Object> params = new HashMap<String, Object>();
        params.put("content", "content");
        taskService.complete(taskId, "Darth Vader", params);

        List<Content> allContent = taskService.getAllContentByTaskId(taskId);
        assertNotNull(allContent);
        assertEquals(3, allContent.size());
        // only input(0) and output(1) is present
        assertNotNull(allContent.get(0));
        assertNotNull(allContent.get(1));
        assertNull(allContent.get(2));

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(AccessType.Inline, ((InternalTaskData) task2.getTaskData()).getOutputAccessType());
        assertEquals("java.util.HashMap", task2.getTaskData().getOutputType());
        long contentId = task2.getTaskData().getOutputContentId();
        assertTrue(contentId != -1);



        Content content = taskService.getContentById(contentId);
        Map<String, Object> unmarshalledObject = (Map<String, Object>) ContentMarshallerHelper.unmarshall(content.getContent(), null);
        assertEquals("content", unmarshalledObject.get("content"));
        
        // update content
        params.put("content", "updated content");
	    taskService.setOutput(taskId, "Darth Vader", params);
	    
	    task = taskService.getTaskById(taskId);
	    contentId = task.getTaskData().getOutputContentId();
	    
	    content = taskService.getContentById(contentId);
	    String updated = new String(content.getContent());
	    unmarshalledObject = (Map<String, Object>) ContentMarshallerHelper.unmarshall(content.getContent(), null);
        assertEquals("updated content", unmarshalledObject.get("content"));
        
        taskService.deleteOutput(taskId, "Darth Vader");
        content = taskService.getContentById(contentId);
        assertNull(content);
    }

    @Test
    public void testCompleteWithResults() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ], businessAdministrators = [ new User('Administrator') ],}),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());


        Map<String, Object> params = new HashMap<String, Object>();
        params.put("content", "content");
        taskService.complete(taskId, "Darth Vader", params);


        Task task2 = taskService.getTaskById(taskId);
        assertEquals(AccessType.Inline, ((InternalTaskData) task2.getTaskData()).getOutputAccessType());
        assertEquals("java.util.HashMap", task2.getTaskData().getOutputType());
        long contentId = task2.getTaskData().getOutputContentId();
        assertTrue(contentId != -1);



        Content content = taskService.getContentById(contentId);
        Map<String, Object> unmarshalledObject = (Map<String, Object>) ContentMarshallerHelper.unmarshall(content.getContent(), null);
        assertEquals("content", unmarshalledObject.get("content"));
    }

    @Test
    public void testFail() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");




        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Failed

        taskService.fail(taskId, "Darth Vader", null);

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Failed, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testFailWithIncorrectUser() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ], businessAdministrators = [ new User('Administrator') ],}),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");




        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Should not fail as wrong user


        PermissionDeniedException denied = null;
        try {
            taskService.fail(taskId, "Bobba Fet", null);
        } catch (PermissionDeniedException e) {
            denied = e;
        }
        assertNotNull("Should get permissed denied exception", denied);



        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }

    @Test
    public void testFailWithContent() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ], businessAdministrators = [ new User('Administrator') ],}),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Go straight from Ready to Inprogress
        taskService.start(taskId, "Darth Vader");

        taskService.getTaskById(taskId);
        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        Map<String, Object> faultData = new HashMap<String, Object>();
        faultData.put("faultType", "type");
        faultData.put("faultName", "faultName");
        faultData.put("content", "content");

        taskService.fail(taskId, "Darth Vader", faultData);
        
        List<Content> allContent = taskService.getAllContentByTaskId(taskId);
        assertNotNull(allContent);
        assertEquals(3, allContent.size());
        // only input(0) and fault(2) is present
        assertNotNull(allContent.get(0));
        assertNull(allContent.get(1));
        assertNotNull(allContent.get(2));

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Failed, task2.getTaskData().getStatus());
        assertEquals(AccessType.Inline, ((InternalTaskData) task2.getTaskData()).getFaultAccessType());
        assertEquals("type", task2.getTaskData().getFaultType());
        assertEquals("faultName", task2.getTaskData().getFaultName());
        long contentId = task2.getTaskData().getFaultContentId();
        assertTrue(contentId != -1);



        Content content = taskService.getContentById(contentId);
        Map<String, Object> unmarshalledContent = (Map<String, Object>) ContentMarshallerHelper.unmarshall(content.getContent(), null);
        assertEquals("content", unmarshalledContent.get("content"));
        xmlRoundTripContent(content);
        
        // update fault
	    FaultData data = TaskModelProvider.getFactory().newFaultData();
	    data.setAccessType(AccessType.Inline);
	    data.setType("type");
	    data.setFaultName("faultName");
	    data.setContent("updated content".getBytes());
	    
	    taskService.setFault(taskId, "Darth Vader", data);
	    
	    task = taskService.getTaskById(taskId);
	    contentId = task.getTaskData().getFaultContentId();
	    
	    content = taskService.getContentById(contentId);
	    String updated = new String(content.getContent());
	    assertEquals("updated content", updated);
        
	    // delete fault
        taskService.deleteFault(taskId, "Darth Vader");
        content = taskService.getContentById(contentId);
        assertNull(content);
    }
//    
//    /**
//     * The issue here has to do with the fact that hibernate uses lazy initialization. 
//     * Actually, what's happening is that one of the collections retrieved isn't retrieved "for update", 
//     * so that the proxy collection instance retrieved can't be updated. 
//     * (The collection instance can't be updated because hibernate doesn't allowed that unless the collection 
//     * has been retrieved "for update" -- which is actually logical.)
//     * 
//     * This, of course, only happens when using the LocalTaskService. Why? Because the LocalTaskService
//     * "shares" a persistence context with the taskService. If I spent another half-hour, I could explain
//     * why that causes this particular problem. 
//     * Regardless,  I can't stress enough how much that complicates the situation here, and, especially, 
//     * why that makes the LocalTaskService a significantly different variant of the TaskService
//     * than the HornetQ, Mina or other transport medium based instances.  
//     */
//    public void FIXME_testRegisterRemove() throws Exception {
//    	  Map <String, Object> vars = fillVariables();
//        
//        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
//        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ], }),";                        
//        str += "names = [ new I18NText( 'en-UK', 'This is my task name')] })";
//
//        
//        Task task = ( Task )  TaskFactory.eval( new StringReader( str ), vars );
//        taskService.addTask( task, null );
//        
//        long taskId = task.getId();               
//       
//        taskService.register(taskId, "Bobba Fet");
//
//        
//        Task task1 = taskService.getTaskById(taskId);
//        List<OrganizationalEntity> myRecipientTasks = task1.getPeopleAssignments().getRecipients();
//        
//        assertNotNull(myRecipientTasks);
//        assertEquals(1, myRecipientTasks.size());
//        assertTrue(task1.getPeopleAssignments().getRecipients().contains("Bobba Fet"));
//        
//        taskService.remove(taskId, "Bobba Fet");
//        
//        Task task2 = taskService.getTaskById( taskId );
//        assertFalse(task2.getPeopleAssignments().getRecipients().contains("Bobba Fet"));
//    }
//    

    @Test
    public void testRemoveNotInRecipientList() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { status = Status.Ready } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ],businessAdministrators = [ new User('Administrator') ],";
        str += "recipients = [new User('Bobba Fet') ] }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str), null);
        // We need to add the Admin if we don't initialize the task
        if (task.getPeopleAssignments() != null && task.getPeopleAssignments().getBusinessAdministrators() != null) {
            List<OrganizationalEntity> businessAdmins = new ArrayList<OrganizationalEntity>();
            User user = TaskModelProvider.getFactory().newUser();
            ((InternalOrganizationalEntity) user).setId("Administrator");
            businessAdmins.add(user);
            businessAdmins.addAll(task.getPeopleAssignments().getBusinessAdministrators());
            ((InternalPeopleAssignments) task.getPeopleAssignments()).setBusinessAdministrators(businessAdmins);
        }
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        // Do nominate and fail due to Ready status


        List<TaskSummary> myRecipientTasks = taskService.getTasksAssignedAsRecipient("Jabba Hutt");

        assertNotNull(myRecipientTasks);
        assertEquals(0, myRecipientTasks.size());



        List<TaskSummary> myPotentialTasks = taskService.getTasksAssignedAsPotentialOwner("Jabba Hutt", "en-UK");

        assertNotNull(myPotentialTasks);
        assertEquals(0, myPotentialTasks.size());


        try {
            taskService.remove(taskId, "Jabba Hutt");
            fail("Shouldn't be successful");
        } catch (RuntimeException e) { //expected
        }

        //shouldn't affect the assignments


        Task task1 = taskService.getTaskById(taskId);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Bobba Fet");
        assertTrue(((InternalPeopleAssignments) task1.getPeopleAssignments()).getRecipients().contains(user));
    }

    /**
     * Nominate an organization entity to process the task. If it is nominated
     * to one person then the new state of the task is Reserved. If it is
     * nominated to several people then the new state of the task is Ready. This
     * can only be performed when the task is in the state Created.
     */
    @Test
    public void testNominateOnOtherThanCreated() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { status = Status.Ready } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { businessAdministrators = [ new User('Administrator') ] ,";
        str += " potentialOwners = [ new User('Darth Vader'), new User('Bobba Fet') ] } ),";
        str += "name =  'This is my task name' })";

        Task task = (Task) TaskFactory.evalTask(new StringReader(str), null);

        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();

        taskService.start(taskId, "Bobba Fet");

        try {
            List<OrganizationalEntity> potentialOwners = new ArrayList<OrganizationalEntity>();
            User user = TaskModelProvider.getFactory().newUser();
            ((InternalOrganizationalEntity) user).setId("Bobba Fet");
            potentialOwners.add(user);
            taskService.nominate(taskId, "Darth Vader", potentialOwners);

            fail("Shouldn't be successful");
        } catch (RuntimeException e) { //expected
//        	assertNotNull(nominateHandler.getError());
//        	assertNotNull(nominateHandler.getError().getMessage());
//        	assertTrue(nominateHandler.getError().getMessage().contains("Created"));
        }

        //shouldn't affect the assignments

        Task task1 = taskService.getTaskById(taskId);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Darth Vader");
        assertTrue(task1.getPeopleAssignments().getPotentialOwners().contains(user));
        user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Bobba Fet");
        assertTrue(task1.getPeopleAssignments().getPotentialOwners().contains(user));
    }

    @Test
    public void testNominateWithIncorrectUser() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { businessAdministrators = [ new User('Bobba Fet') ] } ),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();


        try {
            List<OrganizationalEntity> potentialOwners = new ArrayList<OrganizationalEntity>(1);
            User user = TaskModelProvider.getFactory().newUser();
            ((InternalOrganizationalEntity) user).setId("Jabba Hutt");
            potentialOwners.add(user);
            taskService.nominate(taskId, "Darth Vader", potentialOwners);

            fail("Shouldn't be successful");
        } catch (RuntimeException e) { //expected
//        	assertNotNull(nominateHandler.getError());
//        	assertNotNull(nominateHandler.getError().getMessage());
//        	assertTrue(nominateHandler.getError().getMessage().contains("Darth Vader"));
        }

        //shouldn't affect the assignments

        Task task1 = taskService.getTaskById(taskId);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Bobba Fet");
        assertTrue(task1.getPeopleAssignments().getBusinessAdministrators().contains(user));
        assertEquals(task1.getTaskData().getStatus(), Status.Created);
    }

    @Test
    public void testNominateToUser() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { businessAdministrators = [ new User('Darth Vader'), new User('Bobba Fet') ] } ),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();


        List<OrganizationalEntity> potentialOwners = new ArrayList<OrganizationalEntity>(1);
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Jabba Hutt");
        potentialOwners.add(user);
        taskService.nominate(taskId, "Darth Vader", potentialOwners);


        //shouldn't affect the assignments


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(task1.getTaskData().getActualOwner().getId(), "Jabba Hutt");
        assertEquals(task1.getTaskData().getStatus(), Status.Reserved);
    }

    @Test
    public void testNominateToGroup() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { businessAdministrators = [ new User('Darth Vader'), new User('Bobba Fet') ] } ),";
        str += "name = 'This is my task name'})";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();


        List<OrganizationalEntity> potentialGroups = new ArrayList<OrganizationalEntity>();
        Group group = TaskModelProvider.getFactory().newGroup();
        ((InternalOrganizationalEntity) group).setId("Knights Templer");
        potentialGroups.add(group);
        taskService.nominate(taskId, "Darth Vader", potentialGroups);


        //shouldn't affect the assignments


        Task task1 = taskService.getTaskById(taskId);
        assertTrue(task1.getPeopleAssignments().getPotentialOwners().contains(group));
        assertEquals(task1.getTaskData().getStatus(), Status.Ready);
    }

    @Test
    public void testActivate() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { ";
        str += "businessAdministrators = [ new User('Darth Vader') ] } ),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();


        taskService.activate(taskId, "Darth Vader");

        Task task1 = taskService.getTaskById(taskId);

        assertEquals(task1.getTaskData().getStatus(), Status.Ready);
        //When we are not using remoting the object is the same
        //assertTrue(task1.equals(task));
        //When we use remoting this will be false
        //assertFalse(task1.equals(task));
    }

    @Test
    public void testActivateWithIncorrectUser() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [ new User('Darth Vader'), new User('Bobba Fet') ], ";
        str += "businessAdministrators = [ new User('Jabba Hutt') ] } ),";
        str += "name =  'This is my task name'})";

        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();


        try {
            taskService.activate(taskId, "Darth Vader");

            fail("Shouldn't have succeded");
        } catch (RuntimeException e) {
//        	assertNotNull(activateResponseHandler.getError());
//        	assertNotNull(activateResponseHandler.getError().getMessage());
//        	assertTrue(activateResponseHandler.getError().getMessage().toLowerCase().contains("status"));
        }

    }

    @Test
    public void testActivateFromIncorrectStatus() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { status = Status.Ready } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [ new User('Darth Vader'), new User('Bobba Fet') ], ";
        str += "businessAdministrators = [ new User('Jabba Hutt') ] } ),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str), null);
        // We need to add the Admin if we don't initialize the task
        if (task.getPeopleAssignments() != null && task.getPeopleAssignments().getBusinessAdministrators() != null) {
            List<OrganizationalEntity> businessAdmins = new ArrayList<OrganizationalEntity>();
            User user = TaskModelProvider.getFactory().newUser();
            ((InternalOrganizationalEntity) user).setId("Administrator");
            businessAdmins.add(user);
            businessAdmins.addAll(task.getPeopleAssignments().getBusinessAdministrators());
            ((InternalPeopleAssignments) task.getPeopleAssignments()).setBusinessAdministrators(businessAdmins);
        }
        
        taskService.addTask(task, new HashMap<String, Object>());

        
        long taskId = task.getId();


        try {
            taskService.activate(taskId, "Darth Vader");

            fail("Shouldn't have succeded");
        } catch (RuntimeException e) {
//        	assertNotNull(activateResponseHandler.getError());
//        	assertNotNull(activateResponseHandler.getError().getMessage());
//        	assertTrue(activateResponseHandler.getError().getMessage().contains("Darth Vader"));
        }
    }

    @Test
    public void testExitFromReady() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { skipable = false} ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ], businessAdministrators = [ new User('Administrator')] }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        task = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task.getTaskData().getStatus());


        taskService.exit(taskId, "Administrator");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Exited, task1.getTaskData().getStatus());
    }

    @Test
    public void testExitFromReserved() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { skipable = false} ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ], businessAdministrators = [ new User('Administrator')] }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        task = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task.getTaskData().getStatus());


        taskService.exit(taskId, "Administrator");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Exited, task1.getTaskData().getStatus());
    }

    @Test
    public void testExitFromInProgress() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { skipable = false} ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ], businessAdministrators = [ new User('Administrator')] }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        task = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task.getTaskData().getStatus());

        taskService.start(taskId, "Bobba Fet");
        task = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task.getTaskData().getStatus());

        taskService.exit(taskId, "Administrator");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Exited, task1.getTaskData().getStatus());
    }

    @Test
    public void testExitFromSuspended() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { skipable = false} ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet') ], businessAdministrators = [ new User('Administrator')] }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        task = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task.getTaskData().getStatus());

        taskService.suspend(taskId, "Bobba Fet");
        task = taskService.getTaskById(taskId);
        assertEquals(Status.Suspended, task.getTaskData().getStatus());

        taskService.exit(taskId, "Administrator");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Exited, task1.getTaskData().getStatus());
    }

    @Test
    public void testExitPermissionDenied() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { skipable = false} ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ], businessAdministrators = [ new User('Administrator')] }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        task = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task.getTaskData().getStatus());

        try {
            taskService.exit(taskId, "Darth Vader");
            fail("Non admin user can't exit a task");
        } catch (PermissionDeniedException e) {
        }
        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Ready, task1.getTaskData().getStatus());
    }

    @Test
    public void testExitNotAvailableToUsers() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { skipable = false} ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet')], businessAdministrators = [ new User('Administrator')] }),";
        str += "name = 'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        task = taskService.getTaskById(taskId);
        assertEquals(Status.Reserved, task.getTaskData().getStatus());


        taskService.exit(taskId, "Administrator");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.Exited, task1.getTaskData().getStatus());

        List<TaskSummary> exitedTasks = taskService.getTasksAssignedAsPotentialOwner("Bobba Fet", "en-UK");
        assertEquals(0, exitedTasks.size());

    }

    @Test
    public void testClaimConflictAndRetry() {
        

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('salaboy'), new User('Bobba Fet') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";

        // Create a local instance of the TaskService

        // Deploy the Task Definition to the Task Component
        taskService.addTask((Task) TaskFactory.evalTask(new StringReader(str)), new HashMap<String, Object>());

        // Because the Task contains a direct assignment we can query it for its Potential Owner
        // Notice that we obtain a list of TaskSummary (a lightweight representation of a task)
        List<TaskSummary> salaboyTasks = taskService.getTasksAssignedAsPotentialOwner("salaboy", "en-UK");

        // We know that there is just one task available so we get the first one
        Long salaboyTaskId = salaboyTasks.get(0).getId();

        // In order to check the task status we need to get the real task
        // The task is in a Reserved status because it already have a well-defined Potential Owner
        Task salaboyTask = taskService.getTaskById(salaboyTaskId);
        assertEquals(Status.Ready, salaboyTask.getTaskData().getStatus());

        // Because the Task contains a direct assignment we can query it for its Potential Owner
        // Notice that we obtain a list of TaskSummary (a lightweight representation of a task)
        List<TaskSummary> bobbaTasks = taskService.getTasksAssignedAsPotentialOwner("Bobba Fet", "en-UK");

        // We know that there is just one task available so we get the first one
        Long bobbaTaskId = bobbaTasks.get(0).getId();
        assertEquals(bobbaTaskId, salaboyTaskId);
        // In order to check the task status we need to get the real task
        // The task is in a Reserved status because it already have a well-defined Potential Owner
        Task bobbaTask = taskService.getTaskById(bobbaTaskId);
        assertEquals(Status.Ready, bobbaTask.getTaskData().getStatus());


        taskService.claim(bobbaTask.getId(), "Bobba Fet");

        try {
            taskService.claim(salaboyTask.getId(), "salaboy");
        } catch (PermissionDeniedException ex) {
            // The Task is gone.. salaboy needs to retry
            assertNotNull(ex);
        }

    }

    @Test
    public void testClaimNextAvailable() {
        
        // Create a local instance of the TaskService

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('salaboy'), new User('Bobba Fet') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";

        // Deploy the Task Definition to the Task Component
        taskService.addTask((Task) TaskFactory.evalTask(new StringReader(str)), new HashMap<String, Object>());

        // we don't need to query for our task to see what we will claim, just claim the next one available for us

        taskService.claimNextAvailable("Bobba Fet", "en-UK");


        List<Status> status = new ArrayList<Status>();
        status.add(Status.Ready);
        List<TaskSummary> salaboyTasks = taskService.getTasksAssignedAsPotentialOwnerByStatus("salaboy", status, "en-UK");
        assertEquals(0, salaboyTasks.size());

    }
    
    @Test
    public void testClaimNextAvailableWithGroups() {
        
        // Create a local instance of the TaskService

        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('salaboy'), new User('Bobba Fet') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";

        // Deploy the Task Definition to the Task Component
        taskService.addTask((Task) TaskFactory.evalTask(new StringReader(str)), new HashMap<String, Object>());

        // we don't need to query for our task to see what we will claim, just claim the next one available for us
        List<String> groups = new ArrayList<String>();
        groups.add("HR");
        taskService.claimNextAvailable("Bobba Fet", groups);


        List<Status> status = new ArrayList<Status>();
        status.add(Status.Ready);
        List<TaskSummary> salaboyTasks = taskService.getTasksAssignedAsPotentialOwnerByStatus("salaboy", status, "en-UK");
        assertEquals(0, salaboyTasks.size());

    }
    
    @Test
    public void testCompleteWithRestrictedGroups() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new Group('analyst'), new Group('Crusaders') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name =  'This is my task name' })";


        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        
        List<OrganizationalEntity> potOwners = task.getPeopleAssignments().getPotentialOwners();
        assertNotNull(potOwners);
        assertEquals(1, potOwners.size());
        assertEquals("Crusaders", potOwners.get(0).getId());

        // Go straight from Ready to Inprogress

        taskService.start(taskId, "Darth Vader");


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Complete

        taskService.complete(taskId, "Darth Vader", null);




        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Completed, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }
    
    @Test
    public void testInvalidTask() {
    	try {
    		taskService.claim(-1, "Darth Vader");
    	} catch (PermissionDeniedException e) {
    		if ("Task '-1' not found".equals(e.getMessage())) {
    			return;
    		} else {
    			throw e;
    		}
    	}
    }
    
    @Test
    public void testCompleteWithComments() {       
        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";

        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());

        long taskId = task.getId();
        
        List<Comment> comments = taskService.getAllCommentsByTaskId(taskId);
        assertNotNull(comments);
        assertEquals(0, comments.size());
        
        User user = TaskModelProvider.getFactory().newUser();
        ((InternalOrganizationalEntity) user).setId("Bobba Fet");
        
        Comment comment = TaskModelProvider.getFactory().newComment();
        ((InternalComment)comment).setAddedAt(new Date());
        ((InternalComment)comment).setAddedBy(user);
        ((InternalComment)comment).setText("Simple test comment");
        taskService.addComment(taskId, comment);
        
        comments = taskService.getAllCommentsByTaskId(taskId);
        assertNotNull(comments);
        assertEquals(1, comments.size());

        // Go straight from Ready to Inprogress
        taskService.start(taskId, "Darth Vader");

        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Complete
        taskService.complete(taskId, "Darth Vader", null);

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Completed, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
    }
    
    @Test
    public void testNewTaskWithSingleInvalidPotentialOwner() {
        
        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new Group('invalid')  ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";


        Task task = TaskFactory.evalTask(new StringReader(str));

        taskService.addTask(task, new HashMap<String, Object>());
        try {
	        String potOwner = "invalid";             
	        taskService.getTasksAssignedAsPotentialOwner(potOwner, "en-UK");
	        fail("Should fail due to same id for group and user");
        } catch (RuntimeException e) {
        	assertTrue(e.getMessage().endsWith("please check that there is no group and user with same id"));
        }
    }

    @Test
    public void testLongDescription() {
        // BZ-1107473
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";

        Task task = (Task) TaskFactory.evalTask(new StringReader(str));

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 1000; i++) {
            sb.append("a");
        }
        String comment = sb.toString();

        // NOTE: AbstractHTWorkItemHandler stores "Comment" parameter as 'Description'
        List<I18NText> descriptions = new ArrayList<I18NText>();
        I18NText descText = TaskModelProvider.getFactory().newI18NText();
        ((InternalI18NText) descText).setLanguage("en-UK");
        ((InternalI18NText) descText).setText(comment);
        descriptions.add(descText);
        ((InternalTask)task).setDescriptions(descriptions);

        taskService.addTask(task, new HashMap<String, Object>()); // Fails if shortText is longer than 255

        long taskId = task.getId();

        Task resultTask = taskService.getTaskById(taskId);
        List<I18NText> resultDescriptions = resultTask.getDescriptions();

        InternalI18NText resultDescription = (InternalI18NText)resultDescriptions.get(0);

        assertEquals(1000, resultDescription.getText().length()); // This is text

        // 6.1.x no longer uses shortText in API and Taskorm.xml so no assert.
    }
    
    @Test
    public void testCompleteByActiveTasks() {
        

        // One potential owner, should go straight to state Reserved
        String str = "(with (new Task()) { priority = 55, taskData = (with( new TaskData()) { activationTime = new Date(), processInstanceId = 123 } ), ";
        str += "peopleAssignments = (with ( new PeopleAssignments() ) { potentialOwners = [new User('Bobba Fet'), new User('Darth Vader') ],businessAdministrators = [ new User('Administrator') ], }),";
        str += "name = 'This is my task name' })";

        Date creationTime = new Date();
        
        Task task = (Task) TaskFactory.evalTask(new StringReader(str));
        taskService.addTask(task, new HashMap<String, Object>());


        long taskId = task.getId();
        assertNotNull(task.getTaskData().getActivationTime());

        // Go straight from Ready to Inprogress
        taskService.start(taskId, "Darth Vader");
        
        List<TaskSummary> activeTasks = taskService.getActiveTasks();
        assertNotNull(activeTasks);
        assertEquals(1,  activeTasks.size());
        
        activeTasks = taskService.getActiveTasks(creationTime);
        assertNotNull(activeTasks);
        assertEquals(1,  activeTasks.size());


        Task task1 = taskService.getTaskById(taskId);
        assertEquals(Status.InProgress, task1.getTaskData().getStatus());
        assertEquals("Darth Vader", task1.getTaskData().getActualOwner().getId());

        // Check is Complete

        taskService.complete(taskId, "Darth Vader", null);

        Task task2 = taskService.getTaskById(taskId);
        assertEquals(Status.Completed, task2.getTaskData().getStatus());
        assertEquals("Darth Vader", task2.getTaskData().getActualOwner().getId());
        
        List<TaskSummary> completedTasks = taskService.getCompletedTasks();
        assertNotNull(completedTasks);
        assertEquals(1,  completedTasks.size());
        
        completedTasks = taskService.getCompletedTasks(creationTime);
        assertNotNull(completedTasks);
        assertEquals(1,  completedTasks.size());
        
        completedTasks = taskService.getCompletedTasksByProcessId(123l);
        assertNotNull(completedTasks);
        assertEquals(1,  completedTasks.size());
        
        taskService.archiveTasks(completedTasks);
        
        List<TaskSummary> archiveddTasks = taskService.getArchivedTasks();
        assertNotNull(archiveddTasks);
        assertEquals(1,  archiveddTasks.size());
    }
}


File: jbpm-human-task/jbpm-human-task-workitems/src/test/java/org/jbpm/services/task/wih/util/PeopleAssignmentHelperTest.java
/**
 * Copyright 2010 JBoss Inc
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package org.jbpm.services.task.wih.util;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.List;

import org.drools.core.process.instance.WorkItem;
import org.drools.core.process.instance.impl.WorkItemImpl;
import org.jbpm.test.util.AbstractBaseTest;
import org.junit.Before;
import org.junit.Test;
import org.kie.api.task.model.Group;
import org.kie.api.task.model.OrganizationalEntity;
import org.kie.api.task.model.PeopleAssignments;
import org.kie.api.task.model.Task;
import org.kie.api.task.model.User;
import org.kie.internal.task.api.TaskModelProvider;
import org.kie.internal.task.api.model.InternalPeopleAssignments;
import org.kie.internal.task.api.model.InternalTask;
import org.kie.internal.task.api.model.InternalTaskData;


public class PeopleAssignmentHelperTest  extends AbstractBaseTest {
	
	private PeopleAssignmentHelper peopleAssignmentHelper;
	
	@Before
	public void setup() {
		
		peopleAssignmentHelper = new PeopleAssignmentHelper();
		
	}
	
	@Test
	public void testProcessPeopleAssignments() {

		List<OrganizationalEntity> organizationalEntities = new ArrayList<OrganizationalEntity>();
		
		String ids = "espiegelberg,   drbug   ";
		assertTrue(organizationalEntities.size() == 0);		
		peopleAssignmentHelper.processPeopleAssignments(ids, organizationalEntities, true);
		assertTrue(organizationalEntities.size() == 2);
		organizationalEntities.contains("drbug");
		organizationalEntities.contains("espiegelberg");
		assertTrue(organizationalEntities.get(0) instanceof User);
		assertTrue(organizationalEntities.get(1) instanceof User);
		
		ids = null;
		organizationalEntities = new ArrayList<OrganizationalEntity>();
		assertTrue(organizationalEntities.size() == 0);		
		peopleAssignmentHelper.processPeopleAssignments(ids, organizationalEntities, true);
		assertTrue(organizationalEntities.size() == 0);
		
		ids = "     ";
		organizationalEntities = new ArrayList<OrganizationalEntity>();
		assertTrue(organizationalEntities.size() == 0);		
		peopleAssignmentHelper.processPeopleAssignments(ids, organizationalEntities, true);
		assertTrue(organizationalEntities.size() == 0);
		
		ids = "Software Developer";
		organizationalEntities = new ArrayList<OrganizationalEntity>();
		assertTrue(organizationalEntities.size() == 0);		
		peopleAssignmentHelper.processPeopleAssignments(ids, organizationalEntities, false);
		assertTrue(organizationalEntities.size() == 1);
		assertTrue(organizationalEntities.get(0) instanceof Group);
		
		// Test that a duplicate is not added; only 1 of the 2 passed in should be added
		ids = "Software Developer,Project Manager";
		peopleAssignmentHelper.processPeopleAssignments(ids, organizationalEntities, false);
		assertTrue(organizationalEntities.size() == 2);
		assertTrue(organizationalEntities.get(0) instanceof Group);
		assertTrue(organizationalEntities.get(1) instanceof Group);
		
	}
	
	@Test
	public void testAssignActors() {
		
		String actorId = "espiegelberg";
		
		Task task = TaskModelProvider.getFactory().newTask();
		InternalTaskData taskData = (InternalTaskData) TaskModelProvider.getFactory().newTaskData();
		PeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
		
		WorkItem workItem = new WorkItemImpl();		
		workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, actorId);
		
		peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
		OrganizationalEntity organizationalEntity1 = peopleAssignments.getPotentialOwners().get(0);
		assertTrue(organizationalEntity1 instanceof User);
		assertEquals(actorId, organizationalEntity1.getId());		
		assertEquals(actorId, taskData.getCreatedBy().getId());
		
		workItem = new WorkItemImpl();
		peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);				
		workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, actorId + ", drbug  ");
		peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
		assertEquals(2, peopleAssignments.getPotentialOwners().size());
		organizationalEntity1 = peopleAssignments.getPotentialOwners().get(0);
		assertEquals(actorId, organizationalEntity1.getId());		
		assertEquals(actorId, taskData.getCreatedBy().getId());
		OrganizationalEntity organizationalEntity2 = peopleAssignments.getPotentialOwners().get(1);
		assertEquals("drbug", organizationalEntity2.getId());

		workItem = new WorkItemImpl();
		peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);				
		workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, "");
		peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
		assertEquals(0, peopleAssignments.getPotentialOwners().size());

	}
	
	@Test
    public void testAssignActorsWithCustomSeparatorViaSysProp() {
        System.setProperty("org.jbpm.ht.user.separator", ";");
        peopleAssignmentHelper = new PeopleAssignmentHelper();
        String actorId = "user1;user2";
        
        Task task = TaskModelProvider.getFactory().newTask();
		InternalTaskData taskData = (InternalTaskData) TaskModelProvider.getFactory().newTaskData();
        PeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
        
        WorkItem workItem = new WorkItemImpl();     
        workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, actorId);
        
        peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
        OrganizationalEntity organizationalEntity1 = peopleAssignments.getPotentialOwners().get(0);
        assertTrue(organizationalEntity1 instanceof User);
        assertEquals("user1", organizationalEntity1.getId());       
        assertEquals("user1", taskData.getCreatedBy().getId());
        
        OrganizationalEntity organizationalEntity2 = peopleAssignments.getPotentialOwners().get(1);
        assertTrue(organizationalEntity2 instanceof User);
        assertEquals("user2", organizationalEntity2.getId());       
        
        workItem = new WorkItemImpl();
        peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);              
        workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, actorId + "; drbug  ");
        peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
        assertEquals(3, peopleAssignments.getPotentialOwners().size());
        organizationalEntity1 = peopleAssignments.getPotentialOwners().get(0);
        assertEquals("user1", organizationalEntity1.getId());       
        assertEquals("user1", taskData.getCreatedBy().getId());
        organizationalEntity2 = peopleAssignments.getPotentialOwners().get(1);
        assertTrue(organizationalEntity2 instanceof User);
        assertEquals("user2", organizationalEntity2.getId()); 
        OrganizationalEntity organizationalEntity3 = peopleAssignments.getPotentialOwners().get(2);
        assertEquals("drbug", organizationalEntity3.getId());

        workItem = new WorkItemImpl();
        peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);              
        workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, "");
        peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
        assertEquals(0, peopleAssignments.getPotentialOwners().size());
        System.clearProperty("org.jbpm.ht.user.separator");
    }
	
	@Test
    public void testAssignActorsWithCustomSeparator() {
        peopleAssignmentHelper = new PeopleAssignmentHelper(":");
        String actorId = "user1:user2";
        
        Task task = TaskModelProvider.getFactory().newTask();
		InternalTaskData taskData = (InternalTaskData) TaskModelProvider.getFactory().newTaskData();
        PeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
        
        WorkItem workItem = new WorkItemImpl();     
        workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, actorId);
        
        peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
        OrganizationalEntity organizationalEntity1 = peopleAssignments.getPotentialOwners().get(0);
        assertTrue(organizationalEntity1 instanceof User);
        assertEquals("user1", organizationalEntity1.getId());       
        assertEquals("user1", taskData.getCreatedBy().getId());
        
        OrganizationalEntity organizationalEntity2 = peopleAssignments.getPotentialOwners().get(1);
        assertTrue(organizationalEntity2 instanceof User);
        assertEquals("user2", organizationalEntity2.getId());       
        
        workItem = new WorkItemImpl();
        peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);              
        workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, actorId + ": drbug  ");
        peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
        assertEquals(3, peopleAssignments.getPotentialOwners().size());
        organizationalEntity1 = peopleAssignments.getPotentialOwners().get(0);
        assertEquals("user1", organizationalEntity1.getId());       
        assertEquals("user1", taskData.getCreatedBy().getId());
        organizationalEntity2 = peopleAssignments.getPotentialOwners().get(1);
        assertTrue(organizationalEntity2 instanceof User);
        assertEquals("user2", organizationalEntity2.getId()); 
        OrganizationalEntity organizationalEntity3 = peopleAssignments.getPotentialOwners().get(2);
        assertEquals("drbug", organizationalEntity3.getId());

        workItem = new WorkItemImpl();
        peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);              
        workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, "");
        peopleAssignmentHelper.assignActors(workItem, peopleAssignments, taskData);
        assertEquals(0, peopleAssignments.getPotentialOwners().size());
    }
	
	@Test
	public void testAssignBusinessAdministrators() {
	
		String businessAdministratorId = "espiegelberg";
		
		Task task = TaskModelProvider.getFactory().newTask();
		PeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
		
		WorkItem workItem = new WorkItemImpl();		
		workItem.setParameter(PeopleAssignmentHelper.BUSINESSADMINISTRATOR_ID, businessAdministratorId);

		peopleAssignmentHelper.assignBusinessAdministrators(workItem, peopleAssignments);
		assertEquals(3, peopleAssignments.getBusinessAdministrators().size());
		OrganizationalEntity organizationalEntity1 = peopleAssignments.getBusinessAdministrators().get(0);
		assertTrue(organizationalEntity1 instanceof User);
		assertEquals("Administrator", organizationalEntity1.getId());

		OrganizationalEntity organizationalEntity2 = peopleAssignments.getBusinessAdministrators().get(1);        
        assertTrue(organizationalEntity2 instanceof Group);              
        assertEquals("Administrators", organizationalEntity2.getId());

        OrganizationalEntity organizationalEntity3 = peopleAssignments.getBusinessAdministrators().get(2);      
        assertTrue(organizationalEntity3 instanceof User);              
        assertEquals(businessAdministratorId, organizationalEntity3.getId());
	}

    @Test
    public void testAssignBusinessAdministratorGroups() {
    
        String businessAdministratorGroupId = "Super users";
        
        Task task = TaskModelProvider.getFactory().newTask();
        PeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
        
        WorkItem workItem = new WorkItemImpl();     
        workItem.setParameter(PeopleAssignmentHelper.BUSINESSADMINISTRATOR_GROUP_ID, businessAdministratorGroupId);

        peopleAssignmentHelper.assignBusinessAdministrators(workItem, peopleAssignments);
        assertEquals(3, peopleAssignments.getBusinessAdministrators().size());
        OrganizationalEntity organizationalEntity1 = peopleAssignments.getBusinessAdministrators().get(0);
        assertTrue(organizationalEntity1 instanceof User);
        assertEquals("Administrator", organizationalEntity1.getId());

        OrganizationalEntity organizationalEntity2 = peopleAssignments.getBusinessAdministrators().get(1);        
        assertTrue(organizationalEntity2 instanceof Group);              
        assertEquals("Administrators", organizationalEntity2.getId());

        OrganizationalEntity organizationalEntity3 = peopleAssignments.getBusinessAdministrators().get(2);      
        assertTrue(organizationalEntity3 instanceof Group);              
        assertEquals(businessAdministratorGroupId, organizationalEntity3.getId());
    }
	
	@Test
	public void testAssignTaskstakeholders() {
	
		String taskStakeholderId = "espiegelberg";
		
		Task task = TaskModelProvider.getFactory().newTask();
		InternalPeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
		
		WorkItem workItem = new WorkItemImpl();		
		workItem.setParameter(PeopleAssignmentHelper.TASKSTAKEHOLDER_ID, taskStakeholderId);

		peopleAssignmentHelper.assignTaskStakeholders(workItem, peopleAssignments);
		assertEquals(1, peopleAssignments.getTaskStakeholders().size());
		OrganizationalEntity organizationalEntity1 = peopleAssignments.getTaskStakeholders().get(0);		
		assertTrue(organizationalEntity1 instanceof User);				
		assertEquals(taskStakeholderId, organizationalEntity1.getId());
		
	}
	
	@Test
	public void testAssignGroups() {
		
		String groupId = "Software Developers, Project Managers";
		
		Task task = TaskModelProvider.getFactory().newTask();
		PeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
		
		WorkItem workItem = new WorkItemImpl();		
		workItem.setParameter(PeopleAssignmentHelper.GROUP_ID, groupId);
		
		peopleAssignmentHelper.assignGroups(workItem, peopleAssignments);
		OrganizationalEntity organizationalEntity1 = peopleAssignments.getPotentialOwners().get(0);
		assertTrue(organizationalEntity1 instanceof Group);
		assertEquals("Software Developers", organizationalEntity1.getId());
		OrganizationalEntity organizationalEntity2 = peopleAssignments.getPotentialOwners().get(1);
		assertTrue(organizationalEntity2 instanceof Group);
		assertEquals("Project Managers", organizationalEntity2.getId());
		
	}
	
	@Test
	public void testgetNullSafePeopleAssignments() {
		
		Task task = TaskModelProvider.getFactory().newTask();
		
		InternalPeopleAssignments peopleAssignment = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
		assertNotNull(peopleAssignment);
		
		peopleAssignment = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
		assertNotNull(peopleAssignment);
		
		((InternalTask) task).setPeopleAssignments(null);
		peopleAssignment = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
		assertNotNull(peopleAssignment);
		assertEquals(0, peopleAssignment.getPotentialOwners().size());
		assertEquals(0, peopleAssignment.getBusinessAdministrators().size());
		assertEquals(0, peopleAssignment.getExcludedOwners().size());
		assertEquals(0, peopleAssignment.getRecipients().size());
		assertEquals(0, peopleAssignment.getTaskStakeholders().size());
		
	}	
	
	@Test
	public void testHandlePeopleAssignments() {
		
		InternalTask task = (InternalTask) TaskModelProvider.getFactory().newTask();
		InternalTaskData taskData = (InternalTaskData) TaskModelProvider.getFactory().newTaskData();
		InternalPeopleAssignments peopleAssignment = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
		assertNotNull(peopleAssignment);
		assertEquals(0, peopleAssignment.getPotentialOwners().size());
		assertEquals(0, peopleAssignment.getBusinessAdministrators().size());
		assertEquals(0, peopleAssignment.getTaskStakeholders().size());
		
		String actorId = "espiegelberg";
		String taskStakeholderId = "drmary";
		String businessAdministratorId = "drbug";
        String businessAdministratorGroupId = "Super users";
        String excludedOwnerId = "john";
        String recipientId = "mary";
		
		WorkItem workItem = new WorkItemImpl();		
		workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, actorId);
		workItem.setParameter(PeopleAssignmentHelper.TASKSTAKEHOLDER_ID, taskStakeholderId);
		workItem.setParameter(PeopleAssignmentHelper.BUSINESSADMINISTRATOR_ID, businessAdministratorId);
        workItem.setParameter(PeopleAssignmentHelper.BUSINESSADMINISTRATOR_GROUP_ID, businessAdministratorGroupId);
        workItem.setParameter(PeopleAssignmentHelper.EXCLUDED_OWNER_ID, excludedOwnerId);
        workItem.setParameter(PeopleAssignmentHelper.RECIPIENT_ID, recipientId);
		
		peopleAssignmentHelper.handlePeopleAssignments(workItem, task, taskData);
		
		List<OrganizationalEntity> potentialOwners = task.getPeopleAssignments().getPotentialOwners();
		assertEquals(1, potentialOwners.size());
		assertEquals(actorId, potentialOwners.get(0).getId());
		
		List<OrganizationalEntity> businessAdministrators = task.getPeopleAssignments().getBusinessAdministrators();
		assertEquals(4, businessAdministrators.size());
		assertEquals("Administrator", businessAdministrators.get(0).getId());
		// Admin group
		assertEquals("Administrators", businessAdministrators.get(1).getId());
		assertEquals(businessAdministratorId, businessAdministrators.get(2).getId());
        assertEquals(businessAdministratorGroupId, businessAdministrators.get(3).getId());
		
		
		List<OrganizationalEntity> taskStakehoders = ((InternalPeopleAssignments) task.getPeopleAssignments()).getTaskStakeholders();
		assertEquals(1, taskStakehoders.size());
		assertEquals(taskStakeholderId, taskStakehoders.get(0).getId());

        List<OrganizationalEntity> excludedOwners = ((InternalPeopleAssignments) task.getPeopleAssignments()).getExcludedOwners();
        assertEquals(1, excludedOwners.size());
        assertEquals(excludedOwnerId, excludedOwners.get(0).getId());

        List<OrganizationalEntity> recipients = ((InternalPeopleAssignments) task.getPeopleAssignments()).getRecipients();
        assertEquals(1, recipients.size());
        assertEquals(recipientId, recipients.get(0).getId());
		
	}

    @Test
    public void testHandleMultiPeopleAssignments() {

    	InternalTask task = (InternalTask) TaskModelProvider.getFactory().newTask();
		InternalTaskData taskData = (InternalTaskData) TaskModelProvider.getFactory().newTaskData();
        InternalPeopleAssignments peopleAssignment = peopleAssignmentHelper.getNullSafePeopleAssignments(task);
        assertNotNull(peopleAssignment);
        assertEquals(0, peopleAssignment.getPotentialOwners().size());
        assertEquals(0, peopleAssignment.getBusinessAdministrators().size());
        assertEquals(0, peopleAssignment.getTaskStakeholders().size());

        String actorId = "espiegelberg,john";
        String taskStakeholderId = "drmary,krisv";
        String businessAdministratorId = "drbug,peter";
        String businessAdministratorGroupId = "Super users,Flow administrators";
        String excludedOwnerId = "john,poul";
        String recipientId = "mary,steve";

        WorkItem workItem = new WorkItemImpl();
        workItem.setParameter(PeopleAssignmentHelper.ACTOR_ID, actorId);
        workItem.setParameter(PeopleAssignmentHelper.TASKSTAKEHOLDER_ID, taskStakeholderId);
        workItem.setParameter(PeopleAssignmentHelper.BUSINESSADMINISTRATOR_ID, businessAdministratorId);
        workItem.setParameter(PeopleAssignmentHelper.BUSINESSADMINISTRATOR_GROUP_ID, businessAdministratorGroupId);
        workItem.setParameter(PeopleAssignmentHelper.EXCLUDED_OWNER_ID, excludedOwnerId);
        workItem.setParameter(PeopleAssignmentHelper.RECIPIENT_ID, recipientId);

        peopleAssignmentHelper.handlePeopleAssignments(workItem, task, taskData);

        List<OrganizationalEntity> potentialOwners = task.getPeopleAssignments().getPotentialOwners();
        assertEquals(2, potentialOwners.size());
        assertEquals("espiegelberg", potentialOwners.get(0).getId());
        assertEquals("john", potentialOwners.get(1).getId());

        List<OrganizationalEntity> businessAdministrators = task.getPeopleAssignments().getBusinessAdministrators();
        assertEquals(6, businessAdministrators.size());
        assertEquals("Administrator", businessAdministrators.get(0).getId());
        //Admin group
        assertEquals("Administrators", businessAdministrators.get(1).getId());
        assertEquals("drbug", businessAdministrators.get(2).getId());
        assertEquals("peter", businessAdministrators.get(3).getId());
        assertEquals("Super users", businessAdministrators.get(4).getId());
        assertEquals("Flow administrators", businessAdministrators.get(5).getId());
        
        
        List<OrganizationalEntity> taskStakehoders = ((InternalPeopleAssignments) task.getPeopleAssignments()).getTaskStakeholders();
        assertEquals(2, taskStakehoders.size());
        assertEquals("drmary", taskStakehoders.get(0).getId());
        assertEquals("krisv", taskStakehoders.get(1).getId());

        List<OrganizationalEntity> excludedOwners = ((InternalPeopleAssignments) task.getPeopleAssignments()).getExcludedOwners();
        assertEquals(2, excludedOwners.size());
        assertEquals("john", excludedOwners.get(0).getId());
        assertEquals("poul", excludedOwners.get(1).getId());

        List<OrganizationalEntity> recipients = ((InternalPeopleAssignments) task.getPeopleAssignments()).getRecipients();
        assertEquals(2, recipients.size());
        assertEquals("mary", recipients.get(0).getId());
        assertEquals("steve", recipients.get(1).getId());

    }

    @Test
    public void testAssignExcludedOwners() {

        String excludedOwnerId = "espiegelberg";

        Task task = TaskModelProvider.getFactory().newTask();
        InternalPeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);

        WorkItem workItem = new WorkItemImpl();
        workItem.setParameter(PeopleAssignmentHelper.EXCLUDED_OWNER_ID, excludedOwnerId);

        peopleAssignmentHelper.assignExcludedOwners(workItem, peopleAssignments);
        assertEquals(1, peopleAssignments.getExcludedOwners().size());
        OrganizationalEntity organizationalEntity1 = peopleAssignments.getExcludedOwners().get(0);
        assertTrue(organizationalEntity1 instanceof User);
        assertEquals(excludedOwnerId, organizationalEntity1.getId());

    }

    @Test
    public void testAssignRecipients() {

        String recipientId = "espiegelberg";

        Task task = TaskModelProvider.getFactory().newTask();
        InternalPeopleAssignments peopleAssignments = peopleAssignmentHelper.getNullSafePeopleAssignments(task);

        WorkItem workItem = new WorkItemImpl();
        workItem.setParameter(PeopleAssignmentHelper.RECIPIENT_ID, recipientId);

        peopleAssignmentHelper.assignRecipients(workItem, peopleAssignments);
        assertEquals(1, peopleAssignments.getRecipients().size());
        OrganizationalEntity organizationalEntity1 = peopleAssignments.getRecipients().get(0);
        assertTrue(organizationalEntity1 instanceof User);
        assertEquals(recipientId, organizationalEntity1.getId());

    }
	
}


File: jbpm-persistence-jpa/src/main/java/org/jbpm/persistence/timer/GlobalJPATimerJobFactoryManager.java
/*
 * Copyright 2012 JBoss Inc
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
package org.jbpm.persistence.timer;

import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.drools.core.command.CommandService;
import org.drools.core.time.InternalSchedulerService;
import org.drools.core.time.Job;
import org.drools.core.time.JobContext;
import org.drools.core.time.JobHandle;
import org.drools.core.time.SelfRemovalJob;
import org.drools.core.time.SelfRemovalJobContext;
import org.drools.core.time.Trigger;
import org.drools.core.time.impl.TimerJobFactoryManager;
import org.drools.core.time.impl.TimerJobInstance;
import org.jbpm.process.instance.timer.TimerManager.ProcessJobContext;

public class GlobalJPATimerJobFactoryManager implements TimerJobFactoryManager {

    private Map<Long, TimerJobInstance> emptyStore = new HashMap<Long,TimerJobInstance>();
    private CommandService commandService;
    private Map<Long, Map<Long, TimerJobInstance>> timerInstances;
    private Map<Long, TimerJobInstance> singleTimerInstances;
    
    public void setCommandService(CommandService commandService) {
        this.commandService = commandService;
    }
    
    public GlobalJPATimerJobFactoryManager() {
        timerInstances = new ConcurrentHashMap<Long, Map<Long, TimerJobInstance>>();
        singleTimerInstances = new ConcurrentHashMap<Long, TimerJobInstance>();
        
    }
    
    public TimerJobInstance createTimerJobInstance(Job job,
                                                   JobContext ctx,
                                                   Trigger trigger,
                                                   JobHandle handle,
                                                   InternalSchedulerService scheduler) {
    	long sessionId = -1;
    	if (ctx instanceof ProcessJobContext) {
            sessionId = ((ProcessJobContext) ctx).getSessionId();
            Map<Long, TimerJobInstance> instances = timerInstances.get(sessionId);
            if (instances == null) {
                instances = new ConcurrentHashMap<Long, TimerJobInstance>();
                timerInstances.put(sessionId, instances);
            }
        }        
        ctx.setJobHandle( handle );
        GlobalJpaTimerJobInstance jobInstance = new GlobalJpaTimerJobInstance( new SelfRemovalJob( job ),
                                                                   new SelfRemovalJobContext( ctx,
                                                                		   emptyStore ),
                                                                   trigger,
                                                                   handle,
                                                                   scheduler);
    
        return jobInstance;
    }
    
    public void addTimerJobInstance(TimerJobInstance instance) {
    
        JobContext ctx = instance.getJobContext();
        if (ctx instanceof SelfRemovalJobContext) {
            ctx = ((SelfRemovalJobContext) ctx).getJobContext();
        }
        Map<Long, TimerJobInstance> instances = null;
        if (ctx instanceof ProcessJobContext) {
            long sessionId = ((ProcessJobContext)ctx).getSessionId();
            instances = timerInstances.get(sessionId);
            if (instances == null) {
                instances = new ConcurrentHashMap<Long, TimerJobInstance>();
                timerInstances.put(sessionId, instances);
            }
        } else {
            instances = singleTimerInstances;
        }
        instances.put( instance.getJobHandle().getId(),
                                 instance );        
    }
    
    public void removeTimerJobInstance(TimerJobInstance instance) {
        JobContext ctx = instance.getJobContext();
        if (ctx instanceof SelfRemovalJobContext) {
            ctx = ((SelfRemovalJobContext) ctx).getJobContext();
        }
        Map<Long, TimerJobInstance> instances = null;
        if (ctx instanceof ProcessJobContext) {
            long sessionId = ((ProcessJobContext)ctx).getSessionId();
            instances = timerInstances.get(sessionId);
            if (instances == null) {
                instances = new ConcurrentHashMap<Long, TimerJobInstance>();
                timerInstances.put(sessionId, instances);
            }
        } else {
            instances = singleTimerInstances;
        }
        instances.remove( instance.getJobHandle().getId() );        
    }
    
    
    public Collection<TimerJobInstance> getTimerJobInstances() {
        return singleTimerInstances.values();
    }
    
    public Collection<TimerJobInstance> getTimerJobInstances(Integer sessionId) {
        Map<Long, TimerJobInstance> sessionTimerJobs = timerInstances.get(sessionId);
        if (sessionTimerJobs == null) {
            return Collections.EMPTY_LIST;
        }
        return sessionTimerJobs.values();
    }
    
    public CommandService getCommandService() {
        return this.commandService;
    }
    
}
