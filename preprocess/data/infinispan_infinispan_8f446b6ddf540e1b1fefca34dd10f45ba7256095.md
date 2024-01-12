Refactoring Types: ['Rename Package']
c/test/java/org/infinispan/server/endpoint/EndpointSubsystemTestCase.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat Middleware LLC, and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.infinispan.server.endpoint;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.DESCRIBE;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SUBSYSTEM;

import java.util.Arrays;
import java.util.Collection;
import java.util.List;

import org.infinispan.server.endpoint.subsystem.EndpointExtension;
import org.jboss.as.clustering.subsystem.ClusteringSubsystemTest;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.subsystem.test.KernelServices;
import org.jboss.as.subsystem.test.ModelDescriptionValidator.ValidationConfiguration;
import org.jboss.dmr.ModelNode;
import org.junit.Assert;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

/**
 *
 * @author <a href="kabir.khan@jboss.com">Kabir Khan</a>
 */
@RunWith(value = Parameterized.class)
public class EndpointSubsystemTestCase extends ClusteringSubsystemTest {

   String xmlFile = null;
   int operations = 0;

   public EndpointSubsystemTestCase(String xmlFile, int operations) {
      super(Constants.SUBSYSTEM_NAME, new EndpointExtension(), xmlFile);
      this.xmlFile = xmlFile;
      this.operations = operations;
   }

   @Parameters
   public static Collection<Object[]> data() {
      Object[][] data = new Object[][] {
            { "endpoint-7.2.xml", 16 },
            { "endpoint-8.0.xml", 16 },
      };
      return Arrays.asList(data);
   }

   @Override
   protected ValidationConfiguration getModelValidationConfiguration() {
      // use this configuration to report any exceptional cases for DescriptionProviders
      return new ValidationConfiguration();
   }

   /**
    * Tests that the xml is parsed into the correct operations
    */
   @Test
   public void testParseSubsystem() throws Exception {
      // Parse the subsystem xml into operations
      List<ModelNode> operations = super.parse(getSubsystemXml());

      /*
       * // print the operations System.out.println("List of operations"); for (ModelNode op :
       * operations) { System.out.println("operation = " + op.toString()); }
       */

      // Check that we have the expected number of operations
      // one for each resource instance
      Assert.assertEquals(this.operations, operations.size());

      // Check that each operation has the correct content
      ModelNode addSubsystem = operations.get(0);
      Assert.assertEquals(ADD, addSubsystem.get(OP).asString());
      PathAddress addr = PathAddress.pathAddress(addSubsystem.get(OP_ADDR));
      Assert.assertEquals(1, addr.size());
      PathElement element = addr.getElement(0);
      Assert.assertEquals(SUBSYSTEM, element.getKey());
      Assert.assertEquals(getMainSubsystemName(), element.getValue());
   }

   /**
    * Test that the model created from the xml looks as expected
    */
   @Test
   public void testInstallIntoController() throws Exception {
      // Parse the subsystem xml and install into the controller
      KernelServices services = createKernelServicesBuilder(null).setSubsystemXml(getSubsystemXml()).build();

      // Read the whole model and make sure it looks as expected
      ModelNode model = services.readWholeModel();

      //System.out.println("model = " + model.asString());

      Assert.assertTrue(model.get(SUBSYSTEM).hasDefined(getMainSubsystemName()));
   }

   /**
    * Starts a controller with a given subsystem xml and then checks that a second controller
    * started with the xml marshalled from the first one results in the same model
    */
   @Test
   public void testParseAndMarshalModel() throws Exception {
      // Parse the subsystem xml and install into the first controller

      KernelServices servicesA = createKernelServicesBuilder(null).setSubsystemXml(getSubsystemXml()).build();

      // Get the model and the persisted xml from the first controller
      ModelNode modelA = servicesA.readWholeModel();
      String marshalled = servicesA.getPersistedSubsystemXml();

      // Install the persisted xml from the first controller into a second controller
      KernelServices servicesB = createKernelServicesBuilder(null).setSubsystemXml(marshalled).build();
      ModelNode modelB = servicesB.readWholeModel();

      // Make sure the models from the two controllers are identical
      super.compare(modelA, modelB);
   }

   /**
    * Starts a controller with the given subsystem xml and then checks that a second controller
    * started with the operations from its describe action results in the same model
    */
   @Test
   public void testDescribeHandler() throws Exception {
      // Parse the subsystem xml and install into the first controller
      KernelServices servicesA = createKernelServicesBuilder(null).setSubsystemXml(getSubsystemXml()).build();
      // Get the model and the describe operations from the first controller
      ModelNode modelA = servicesA.readWholeModel();
      ModelNode describeOp = new ModelNode();
      describeOp.get(OP).set(DESCRIBE);
      describeOp.get(OP_ADDR).set(PathAddress.pathAddress(PathElement.pathElement(SUBSYSTEM, getMainSubsystemName())).toModelNode());
      List<ModelNode> operations = checkResultAndGetContents(servicesA.executeOperation(describeOp)).asList();

      // Install the describe options from the first controller into a second controller
      KernelServices servicesB = createKernelServicesBuilder(null).setBootOperations(operations).build();
      ModelNode modelB = servicesB.readWholeModel();

      // Make sure the models from the two controllers are identical
      super.compare(modelA, modelB);

   }
}


File: server/integration/infinispan/src/main/java/org/jboss/as/clustering/infinispan/ChannelTransport.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.infinispan;

import org.infinispan.remoting.transport.jgroups.JGroupsTransport;
import org.jboss.as.clustering.jgroups.ServiceContainerHelper;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceRegistry;
import org.jboss.msc.service.StartException;
import org.jgroups.Channel;

/**
 * @author Paul Ferraro
 */
public class ChannelTransport extends JGroupsTransport {

    private final ServiceRegistry registry;
    private final ServiceName channelName;

    public ChannelTransport(ServiceRegistry registry, ServiceName channelName) {
        this.registry = registry;
        this.channelName = channelName;
    }

    @Override
    protected synchronized void initChannel() {
        ServiceController<Channel> service = ServiceContainerHelper.getService(this.registry, this.channelName);
        try {
            this.channel = ServiceContainerHelper.getValue(service);
            this.channel.setDiscardOwnMessages(false);
            this.connectChannel = true;
            this.disconnectChannel = true;
            this.closeChannel = false;
        } catch (StartException e) {
            throw new IllegalStateException(e);
        }
    }
}


File: server/integration/infinispan/src/main/java/org/jboss/as/clustering/infinispan/ManagedExecutorFactory.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.infinispan;

import java.util.Properties;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ThreadFactory;

import org.infinispan.commons.executors.ExecutorFactory;
import org.infinispan.commons.executors.ThreadPoolExecutorFactory;
import org.jboss.as.clustering.concurrent.ManagedExecutorService;

/**
 * Executor factory that produces {@link ManagedExecutorService} instances.
 * @author Paul Ferraro
 */
public class ManagedExecutorFactory implements ExecutorFactory, ThreadPoolExecutorFactory<ExecutorService> {

    private final Executor executor;

    public ManagedExecutorFactory(Executor executor) {
        this.executor = executor;
    }

    @Override
    public ExecutorService getExecutor(Properties p) {
        return this.createExecutor();
    }

    @Override
    public ExecutorService createExecutor(ThreadFactory factory) {
        return this.createExecutor();
    }

    private ExecutorService createExecutor() {
        return new ManagedExecutorService(this.executor);
    }

    @Override
    public void validate() {
    }
}


File: server/integration/infinispan/src/main/java/org/jboss/as/clustering/infinispan/ManagedScheduledExecutorFactory.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.infinispan;

import java.util.Properties;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadFactory;

import org.infinispan.commons.executors.ThreadPoolExecutorFactory;
import org.infinispan.executors.ScheduledExecutorFactory;
import org.jboss.as.clustering.concurrent.ManagedScheduledExecutorService;

/**
 * Executor factory that produces {@link ManagedScheduledExecutorService} instances.
 * @author Paul Ferraro
 */
public class ManagedScheduledExecutorFactory implements ScheduledExecutorFactory, ThreadPoolExecutorFactory<ScheduledExecutorService> {

    private final ScheduledExecutorService executor;

    public ManagedScheduledExecutorFactory(ScheduledExecutorService executor) {
        this.executor = executor;
    }

    @Override
    public ScheduledExecutorService getScheduledExecutor(Properties p) {
        return this.createExecutor();
    }

    @Override
    public ScheduledExecutorService createExecutor(ThreadFactory factory) {
        return this.createExecutor();
    }

    private ScheduledExecutorService createExecutor() {
        return new ManagedScheduledExecutorService(this.executor);
    }

    @Override
    public void validate() {
    }
}


File: server/integration/infinispan/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CacheContainerAdd.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.infinispan.subsystem;

import org.infinispan.commons.util.ServiceFinder;
import org.infinispan.manager.CacheContainer;
import org.infinispan.manager.EmbeddedCacheManager;
import org.jboss.as.clustering.infinispan.affinity.KeyAffinityServiceFactoryService;
import org.jboss.as.clustering.infinispan.subsystem.EmbeddedCacheManagerConfigurationService.AuthorizationConfiguration;
import org.jboss.as.clustering.jgroups.ChannelFactory;
import org.jboss.as.clustering.jgroups.subsystem.ChannelFactoryService;
import org.jboss.as.clustering.jgroups.subsystem.ChannelService;
import org.jboss.as.controller.AbstractAddStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.registry.Resource;
import org.jboss.as.jmx.MBeanServerService;
import org.jboss.as.naming.ManagedReferenceInjector;
import org.jboss.as.naming.ServiceBasedNamingStore;
import org.jboss.as.naming.deployment.ContextNames;
import org.jboss.as.naming.service.BinderService;
import org.jboss.as.server.Services;
import org.jboss.as.threads.ThreadsServices;
import org.jboss.dmr.ModelNode;
import org.jboss.logging.Logger;
import org.jboss.modules.ModuleIdentifier;
import org.jboss.modules.ModuleLoader;
import org.jboss.msc.inject.Injector;
import org.jboss.msc.service.Service;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.value.InjectedValue;

import javax.management.MBeanServer;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executor;
import java.util.concurrent.ScheduledExecutorService;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;

/**
 * @author Paul Ferraro
 * @author Tristan Tarrant
 * @author Richard Achmatowicz
 */
public class CacheContainerAdd extends AbstractAddStepHandler {

    private static final Logger log = Logger.getLogger(CacheContainerAdd.class.getPackage().getName());

    public static final CacheContainerAdd INSTANCE = new CacheContainerAdd();

    static ModelNode createOperation(ModelNode address, ModelNode existing) throws OperationFailedException {
        ModelNode operation = Util.getEmptyOperation(ADD, address);
        populate(existing, operation);
        return operation;
    }

    private static void populate(ModelNode source, ModelNode target) throws OperationFailedException {
        // AS7-3488 make default-cache non required attrinbute
        // target.get(ModelKeys.DEFAULT_CACHE).set(source.get(ModelKeys.DEFAULT_CACHE));

        CacheContainerResource.DEFAULT_CACHE.validateAndSet(source, target);
        // TODO: need to handle list types
        if (source.hasDefined(ModelKeys.ALIASES)) {
            target.get(ModelKeys.ALIASES).set(source.get(ModelKeys.ALIASES));
        }
        CacheContainerResource.JNDI_NAME.validateAndSet(source, target);
        CacheContainerResource.START.validateAndSet(source, target);
        CacheContainerResource.LISTENER_EXECUTOR.validateAndSet(source, target);
        CacheContainerResource.EVICTION_EXECUTOR.validateAndSet(source, target);
        CacheContainerResource.EXPIRATION_EXECUTOR.validateAndSet(source, target);
        CacheContainerResource.STATE_TRANSFER_EXECUTOR.validateAndSet(source, target);
        CacheContainerResource.ASYNC_EXECUTOR.validateAndSet(source, target);
        CacheContainerResource.REPLICATION_QUEUE_EXECUTOR.validateAndSet(source, target);
        CacheContainerResource.CACHE_CONTAINER_MODULE.validateAndSet(source, target);
        CacheContainerResource.STATISTICS.validateAndSet(source, target);
    }

    @Override
    protected void populateModel(ModelNode operation, ModelNode model) throws OperationFailedException {
        populate(operation, model);
    }

    @Override
    protected void performRuntime(OperationContext context, ModelNode operation, ModelNode model) throws OperationFailedException {
        // Because we use child resources in a read-only manner to configure the cache container, replace the local model with the full model
        installRuntimeServices(context, operation, Resource.Tools.readModel(context.readResource(PathAddress.EMPTY_ADDRESS)));
    }

    Collection<ServiceController<?>> installRuntimeServices(OperationContext context, ModelNode operation, ModelNode containerModel) throws OperationFailedException {

        final PathAddress address = getCacheContainerAddressFromOperation(operation);
        final String name = address.getLastElement().getValue();
        final ServiceTarget target = context.getServiceTarget();

        // pick up the attribute values from the model
        ModelNode resolvedValue = null ;
        // make default cache non required (AS7-3488)
        final String defaultCache = (resolvedValue = CacheContainerResource.DEFAULT_CACHE.resolveModelAttribute(context, containerModel)).isDefined() ? resolvedValue.asString() : null ;
        final String jndiName = (resolvedValue = CacheContainerResource.JNDI_NAME.resolveModelAttribute(context, containerModel)).isDefined() ? resolvedValue.asString() : null ;
        final String listenerExecutor = (resolvedValue = CacheContainerResource.LISTENER_EXECUTOR.resolveModelAttribute(context, containerModel)).isDefined() ? resolvedValue.asString() : null ;
        final String asyncExecutor = (resolvedValue = CacheContainerResource.ASYNC_EXECUTOR.resolveModelAttribute(context,
              containerModel)).isDefined() ? resolvedValue.asString() : null;
        String expirationExecutor = (resolvedValue = CacheContainerResource.EXPIRATION_EXECUTOR.resolveModelAttribute(context, containerModel)).isDefined() ? resolvedValue.asString() : null ;
        if (expirationExecutor == null) {
           expirationExecutor = (resolvedValue = CacheContainerResource.EVICTION_EXECUTOR.resolveModelAttribute(context, containerModel)).isDefined() ? resolvedValue.asString() : null ;
        }
        final String replicationQueueExecutor = (resolvedValue = CacheContainerResource.REPLICATION_QUEUE_EXECUTOR.resolveModelAttribute(context, containerModel)).isDefined() ? resolvedValue.asString() : null ;
        final String stateTransferExecutor = (resolvedValue = CacheContainerResource.STATE_TRANSFER_EXECUTOR.resolveModelAttribute(context, containerModel)).isDefined() ? resolvedValue.asString() : null ;
        final ServiceController.Mode initialMode = StartMode.valueOf(CacheContainerResource.START.resolveModelAttribute(context, containerModel).asString()).getMode();
        final boolean statistics = CacheContainerResource.STATISTICS.resolveModelAttribute(context, containerModel).asBoolean();

        ServiceName[] aliases = null;
        if (containerModel.hasDefined(ModelKeys.ALIASES)) {
            List<ModelNode> list = operation.get(ModelKeys.ALIASES).asList();
            aliases = new ServiceName[list.size()];
            for (int i = 0; i < list.size(); i++) {
                aliases[i] = EmbeddedCacheManagerService.getServiceName(list.get(i).asString());
            }
        }

        final ModuleIdentifier moduleId = (resolvedValue = CacheContainerResource.CACHE_CONTAINER_MODULE.resolveModelAttribute(context, containerModel)).isDefined() ? ModuleIdentifier.fromString(resolvedValue.asString()) : null;

        // if we have a transport defined, pick up the transport-related attributes and install a channel
        final Transport transportConfig = containerModel.hasDefined(ModelKeys.TRANSPORT) && containerModel.get(ModelKeys.TRANSPORT).hasDefined(ModelKeys.TRANSPORT_NAME) ? new Transport() : null;

        String stack = null;
        String transportExecutor = null;
        String totalOrderExecutor = null;
        String remoteCommandExecutor = null;

        Collection<ServiceController<?>> controllers = new LinkedList<ServiceController<?>>();

        if (transportConfig != null) {
            ModelNode transport = containerModel.get(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);

            stack = (resolvedValue = TransportResource.STACK.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null ;
            // if cluster is not defined, use the cache container name as the default
            final String cluster = (resolvedValue = TransportResource.CLUSTER.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : name ;
            long lockTimeout = TransportResource.LOCK_TIMEOUT.resolveModelAttribute(context, transport).asLong();
            transportExecutor = (resolvedValue = TransportResource.EXECUTOR.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
            totalOrderExecutor = (resolvedValue = TransportResource.TOTAL_ORDER_EXECUTOR.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
            remoteCommandExecutor = (resolvedValue = TransportResource.REMOTE_COMMAND_EXECUTOR.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
            final boolean strictPeerToPeer = TransportResource.STRICT_PEER_TO_PEER.resolveModelAttribute(context, transport).asBoolean();
            transportConfig.setStrictPeerToPeer(strictPeerToPeer);

            // initialise the Transport
            transportConfig.setLockTimeout(lockTimeout);

            controllers.add(this.installChannelService(target, name, cluster, stack));

            for (ChannelDependentServiceProvider provider: ServiceFinder.load(ChannelDependentServiceProvider.class, ChannelDependentServiceProvider.class.getClassLoader())) {
                controllers.add(provider.install(target, name));
            }
        }

        Authorization authorizationConfig = null;
        if (containerModel.hasDefined(ModelKeys.SECURITY) && containerModel.get(ModelKeys.SECURITY).hasDefined(ModelKeys.SECURITY_NAME)) {
            ModelNode securityModel = containerModel.get(ModelKeys.SECURITY, ModelKeys.SECURITY_NAME);

            if (securityModel.hasDefined(ModelKeys.AUTHORIZATION) && securityModel.get(ModelKeys.AUTHORIZATION).hasDefined(ModelKeys.AUTHORIZATION_NAME)) {
                ModelNode authzModel = securityModel.get(ModelKeys.AUTHORIZATION, ModelKeys.AUTHORIZATION_NAME);

                authorizationConfig = new Authorization();
                authorizationConfig.setPrincipalMapper((resolvedValue = CacheContainerAuthorizationResource.MAPPER.resolveModelAttribute(context, authzModel)).isDefined() ? resolvedValue.asString() : null);

                for(ModelNode roleNode : authzModel.get(ModelKeys.ROLE).asList()) {
                    ModelNode role = roleNode.get(0);
                    String roleName = AuthorizationRoleResource.NAME.resolveModelAttribute(context, role).asString();
                    List<String> permissions = new ArrayList<String>();
                    for(ModelNode permission : AuthorizationRoleResource.PERMISSIONS.resolveModelAttribute(context, role).asList()) {
                        permissions.add(permission.asString());
                    }
                    authorizationConfig.getRoles().put(roleName, permissions);
                }

            }
        }

        // install the cache container configuration service
        controllers.add(this.installContainerConfigurationService(target, name, defaultCache, statistics, moduleId,
                stack, transportConfig, authorizationConfig, transportExecutor, totalOrderExecutor,
                remoteCommandExecutor, listenerExecutor, asyncExecutor, expirationExecutor, replicationQueueExecutor, stateTransferExecutor));

        // install a cache container service
        controllers.add(this.installContainerService(target, name, aliases, transportConfig, initialMode));

        // install a name service entry for the cache container
        controllers.add(this.installJndiService(target, name, InfinispanJndiName.createCacheContainerJndiName(jndiName, name)));

        controllers.add(this.installKeyAffinityServiceFactoryService(target, name));

        log.debugf("%s cache container installed", name);
        return controllers;
     }

     void removeRuntimeServices(OperationContext context, ModelNode operation, ModelNode model) throws OperationFailedException {

        final PathAddress address = getCacheContainerAddressFromOperation(operation);
        final String containerName = address.getLastElement().getValue();

        // need to remove all container-related services started, in reverse order
        context.removeService(KeyAffinityServiceFactoryService.getServiceName(containerName));

        // remove the BinderService entry
        ModelNode resolvedValue = null;
        final String jndiName = (resolvedValue = CacheContainerResource.JNDI_NAME.resolveModelAttribute(context, model)).isDefined() ? resolvedValue.asString() : null;
        final ContextNames.BindInfo bindInfo = ContextNames.bindInfoFor(InfinispanJndiName.createCacheContainerJndiName(jndiName, containerName));
        context.removeService(bindInfo.getBinderServiceName());

        // remove the cache container
        context.removeService(EmbeddedCacheManagerService.getServiceName(containerName));
        context.removeService(EmbeddedCacheManagerConfigurationService.getServiceName(containerName));

        // check if a channel was installed
        final ServiceName channelServiceName = ChannelService.getServiceName(containerName) ;
        final ServiceController<?> channelServiceController = context.getServiceRegistry(false).getService(channelServiceName);
        if (channelServiceController != null) {
            for (ChannelDependentServiceProvider provider: ServiceFinder.load(ChannelDependentServiceProvider.class, ChannelDependentServiceProvider.class.getClassLoader())) {
                context.removeService(provider.getServiceName(containerName));
            }
            context.removeService(channelServiceName);
        }
    }

    ServiceController<?> installKeyAffinityServiceFactoryService(ServiceTarget target, String containerName) {
        return target.addService(KeyAffinityServiceFactoryService.getServiceName(containerName), new KeyAffinityServiceFactoryService(10))
                .setInitialMode(ServiceController.Mode.ON_DEMAND)
                .install()
        ;
    }

    ServiceController<?> installChannelService(ServiceTarget target, String containerName, String cluster, String stack) {

        final InjectedValue<ChannelFactory> channelFactory = new InjectedValue<ChannelFactory>();
        return target.addService(ChannelService.getServiceName(containerName), new ChannelService(cluster, channelFactory))
                .addDependency(ChannelFactoryService.getServiceName(stack), ChannelFactory.class, channelFactory)
                .setInitialMode(ServiceController.Mode.ON_DEMAND)
                .install()
        ;
    }

    PathAddress getCacheContainerAddressFromOperation(ModelNode operation) {
        return PathAddress.pathAddress(operation.get(OP_ADDR)) ;
    }

    ServiceController<?> installContainerConfigurationService(ServiceTarget target,
            String containerName, String defaultCache, boolean statistics, ModuleIdentifier moduleId, String stack, Transport transportConfig, Authorization authorizationConfig,
            String transportExecutor, String totalOrderExecutor, String remoteCommandExecutor, String listenerExecutor, String asyncExecutor,
            String expirationExecutor, String replicationQueueExecutor, String stateTransferExecutor) {

        final ServiceName configServiceName = EmbeddedCacheManagerConfigurationService.getServiceName(containerName);
        final EmbeddedCacheManagerDependencies dependencies = new EmbeddedCacheManagerDependencies(transportConfig, authorizationConfig);
        final Service<EmbeddedCacheManagerConfiguration> service = new EmbeddedCacheManagerConfigurationService(containerName, defaultCache, statistics, moduleId, dependencies);
        final ServiceBuilder<EmbeddedCacheManagerConfiguration> configBuilder = target.addService(configServiceName, service)
                .addDependency(Services.JBOSS_SERVICE_MODULE_LOADER, ModuleLoader.class, dependencies.getModuleLoaderInjector())
                .addDependency(MBeanServerService.SERVICE_NAME, MBeanServer.class, dependencies.getMBeanServerInjector())
                .setInitialMode(ServiceController.Mode.ON_DEMAND)
        ;

        // add these dependencies only if we have a transport defined
        if (transportConfig != null) {
            if (transportExecutor != null) {
                addExecutorDependency(configBuilder, transportExecutor, transportConfig.getExecutorInjector());
                addExecutorDependency(configBuilder, totalOrderExecutor, transportConfig.getTotalorderExecutorInjector());
                addExecutorDependency(configBuilder, remoteCommandExecutor, transportConfig.getRemoteCommandExecutorInjector());
            }
            configBuilder.addDependency(ChannelFactoryService.getServiceName(stack), ChannelFactory.class, transportConfig.getChannelFactoryInjector());
        }

        addExecutorDependency(configBuilder, listenerExecutor, dependencies.getListenerExecutorInjector());
        addExecutorDependency(configBuilder, asyncExecutor, dependencies.getAsyncExecutorInjector());
        addExecutorDependency(configBuilder, stateTransferExecutor, dependencies.getStateTransferExecutorInjector());
        addScheduledExecutorDependency(configBuilder, expirationExecutor, dependencies.getExpirationExecutorInjector());
        addScheduledExecutorDependency(configBuilder, replicationQueueExecutor, dependencies.getReplicationQueueExecutorInjector());

        return configBuilder.install();
    }

    ServiceController<?> installContainerService(ServiceTarget target, String containerName, ServiceName[] aliases, Transport transport, ServiceController.Mode initialMode) {

        final ServiceName containerServiceName = EmbeddedCacheManagerService.getServiceName(containerName);
        final ServiceName configServiceName = EmbeddedCacheManagerConfigurationService.getServiceName(containerName);
        final InjectedValue<EmbeddedCacheManagerConfiguration> config = new InjectedValue<EmbeddedCacheManagerConfiguration>();
        final Service<EmbeddedCacheManager> service = new EmbeddedCacheManagerService(config);
        ServiceBuilder<EmbeddedCacheManager> builder = target.addService(containerServiceName, service)
                .addDependency(configServiceName, EmbeddedCacheManagerConfiguration.class, config)
                .addAliases(aliases)
                .setInitialMode(initialMode)
        ;
        if (transport != null) {
            builder.addDependency(ChannelService.getServiceName(containerName));
        }
        return builder.install();
    }

    ServiceController<?> installJndiService(ServiceTarget target, String containerName, String jndiName) {

        final ServiceName containerServiceName = EmbeddedCacheManagerService.getServiceName(containerName);
        final ContextNames.BindInfo bindInfo = ContextNames.bindInfoFor(jndiName);

        final BinderService binder = new BinderService(bindInfo.getBindName());
        return target.addService(bindInfo.getBinderServiceName(), binder)
                .addAliases(ContextNames.JAVA_CONTEXT_SERVICE_NAME.append(jndiName))
                .addDependency(containerServiceName, CacheContainer.class, new ManagedReferenceInjector<CacheContainer>(binder.getManagedObjectInjector()))
                .addDependency(bindInfo.getParentContextServiceName(), ServiceBasedNamingStore.class, binder.getNamingStoreInjector())
                .setInitialMode(ServiceController.Mode.PASSIVE)
                .install()
        ;
    }

    private void addExecutorDependency(ServiceBuilder<EmbeddedCacheManagerConfiguration> builder, String executor, Injector<Executor> injector) {
        if (executor != null) {
            builder.addDependency(ThreadsServices.executorName(executor), Executor.class, injector);
        }
    }

    private void addScheduledExecutorDependency(ServiceBuilder<EmbeddedCacheManagerConfiguration> builder, String executor, Injector<ScheduledExecutorService> injector) {
        if (executor != null) {
            builder.addDependency(ThreadsServices.executorName(executor), ScheduledExecutorService.class, injector);
        }
    }

    static class EmbeddedCacheManagerDependencies implements EmbeddedCacheManagerConfigurationService.Dependencies {
        private final InjectedValue<MBeanServer> mbeanServer = new InjectedValue<MBeanServer>();
        private final InjectedValue<Executor> listenerExecutor = new InjectedValue<Executor>();
        private final InjectedValue<Executor> asyncExecutor = new InjectedValue<Executor>();
        private final InjectedValue<ScheduledExecutorService> expirationExecutor = new InjectedValue<ScheduledExecutorService>();
        private final InjectedValue<ScheduledExecutorService> replicationQueueExecutor = new InjectedValue<ScheduledExecutorService>();
        private final InjectedValue<Executor> stateTransferExecutor = new InjectedValue<>();
        private final EmbeddedCacheManagerConfigurationService.TransportConfiguration transport;
        private final EmbeddedCacheManagerConfigurationService.AuthorizationConfiguration authorization;
        private final InjectedValue<ModuleLoader> moduleLoader = new InjectedValue<ModuleLoader>();

        EmbeddedCacheManagerDependencies(EmbeddedCacheManagerConfigurationService.TransportConfiguration transport, EmbeddedCacheManagerConfigurationService.AuthorizationConfiguration authorization) {
            this.transport = transport;
            this.authorization = authorization;
        }

        Injector<MBeanServer> getMBeanServerInjector() {
            return this.mbeanServer;
        }

        Injector<Executor> getListenerExecutorInjector() {
            return this.listenerExecutor;
        }

        Injector<Executor> getAsyncExecutorInjector() {
            return this.asyncExecutor;
        }

        Injector<Executor> getStateTransferExecutorInjector() {
            return this.stateTransferExecutor;
        }

        Injector<ScheduledExecutorService> getExpirationExecutorInjector() {
            return this.expirationExecutor;
        }

        Injector<ScheduledExecutorService> getReplicationQueueExecutorInjector() {
            return this.replicationQueueExecutor;
        }

        Injector<ModuleLoader> getModuleLoaderInjector() {
            return this.moduleLoader;
        }

        @Override
        public EmbeddedCacheManagerConfigurationService.TransportConfiguration getTransportConfiguration() {
            return this.transport;
        }

        @Override
        public AuthorizationConfiguration getAuthorizationConfiguration() {
            return this.authorization;
        }

        @Override
        public MBeanServer getMBeanServer() {
            return this.mbeanServer.getOptionalValue();
        }

        @Override
        public Executor getListenerExecutor() {
            return this.listenerExecutor.getOptionalValue();
        }

        @Override
        public Executor getAsyncExecutor() {
            return this.asyncExecutor.getOptionalValue();
        }
       
        @Override
        public Executor getStateTransferExecutor() {
           return this.stateTransferExecutor.getOptionalValue();
        }

        @Override
        public ScheduledExecutorService getExpirationExecutor() {
            return this.expirationExecutor.getOptionalValue();
        }

        @Override
        public ScheduledExecutorService getReplicationQueueExecutor() {
            return this.replicationQueueExecutor.getOptionalValue();
        }

        @Override
        public ModuleLoader getModuleLoader() {
            return this.moduleLoader.getValue();
        }
    }

    static class Transport implements EmbeddedCacheManagerConfigurationService.TransportConfiguration {
        private final InjectedValue<ChannelFactory> channelFactory = new InjectedValue<ChannelFactory>();
        private final InjectedValue<Executor> executor = new InjectedValue<Executor>();
        private final InjectedValue<Executor> totalOrderExecutor = new InjectedValue<Executor>();
        private final InjectedValue<Executor> remoteCommandExecutor = new InjectedValue<Executor>();

        private Long lockTimeout;
        private boolean strictPeerToPeer;

        void setLockTimeout(long lockTimeout) {
            this.lockTimeout = lockTimeout;
        }

        void setStrictPeerToPeer(boolean strictPeerToPeer) {
            this.strictPeerToPeer = strictPeerToPeer;
        }

        Injector<ChannelFactory> getChannelFactoryInjector() {
            return this.channelFactory;
        }

        Injector<Executor> getExecutorInjector() {
            return this.executor;
        }

        Injector<Executor> getTotalorderExecutorInjector() {
            return this.totalOrderExecutor;
        }

        Injector<Executor> getRemoteCommandExecutorInjector() {
          return this.remoteCommandExecutor;
       }

       @Override
        public ChannelFactory getChannelFactory() {
            return this.channelFactory.getValue();
        }

        @Override
        public Executor getExecutor() {
            return this.executor.getOptionalValue();
        }

        @Override
        public Executor getTotalOrderExecutor() {
            return this.totalOrderExecutor.getOptionalValue();
        }

        @Override
        public Executor getRemoteCommandExecutor() {
            return this.remoteCommandExecutor.getOptionalValue();
        }

       @Override
        public boolean isStrictPeerToPeer() {
            return this.strictPeerToPeer;
        }

        @Override
        public Long getLockTimeout() {
            return this.lockTimeout;
        }
    }

    static class Authorization implements EmbeddedCacheManagerConfigurationService.AuthorizationConfiguration {
        private String principalMapper;
        private Map<String, List<String>> roles = new HashMap<String, List<String>>();

        public void setPrincipalMapper(String principalMapper) {
            this.principalMapper = principalMapper;
        }

        public void setRoles(Map<String, List<String>> roles) {
            this.roles = roles;
        }

        @Override
        public String getPrincipalMapper() {
            return principalMapper;
        }

        @Override
        public Map<String, List<String>> getRoles() {
            return roles;
        }
    }
}


File: server/integration/infinispan/src/main/java/org/jboss/as/clustering/infinispan/subsystem/EmbeddedCacheManagerConfigurationService.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.infinispan.subsystem;

import org.infinispan.commons.util.ServiceFinder;
import org.infinispan.configuration.global.GlobalAuthorizationConfigurationBuilder;
import org.infinispan.configuration.global.GlobalConfiguration;
import org.infinispan.configuration.global.GlobalConfigurationBuilder;
import org.infinispan.configuration.global.GlobalJmxStatisticsConfigurationBuilder;
import org.infinispan.configuration.global.GlobalRoleConfigurationBuilder;
import org.infinispan.configuration.global.ShutdownHookBehavior;
import org.infinispan.configuration.global.TransportConfigurationBuilder;
import org.infinispan.marshall.core.Ids;
import org.infinispan.security.PrincipalRoleMapper;
import org.infinispan.security.impl.ClusterRoleMapper;
import org.jboss.as.clustering.infinispan.ChannelTransport;
import org.jboss.as.clustering.infinispan.MBeanServerProvider;
import org.jboss.as.clustering.infinispan.ManagedExecutorFactory;
import org.jboss.as.clustering.infinispan.ManagedScheduledExecutorFactory;
import org.jboss.as.clustering.infinispan.ThreadPoolExecutorFactories;
import org.jboss.as.clustering.infinispan.io.SimpleExternalizer;
import org.jboss.as.clustering.jgroups.ChannelFactory;
import org.jboss.as.clustering.jgroups.subsystem.ChannelService;
import org.jboss.marshalling.ModularClassResolver;
import org.jboss.modules.ModuleIdentifier;
import org.jboss.modules.ModuleLoadException;
import org.jboss.modules.ModuleLoader;
import org.jboss.msc.service.Service;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.StartContext;
import org.jboss.msc.service.StartException;
import org.jboss.msc.service.StopContext;

import javax.management.MBeanServer;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.concurrent.Executor;
import java.util.concurrent.ScheduledExecutorService;

/**
 * @author Paul Ferraro
 */
public class EmbeddedCacheManagerConfigurationService implements Service<EmbeddedCacheManagerConfiguration>, EmbeddedCacheManagerConfiguration {
    public static ServiceName getServiceName(String name) {
        return EmbeddedCacheManagerService.getServiceName(name).append("config");
    }

    interface TransportConfiguration {
        Long getLockTimeout();
        ChannelFactory getChannelFactory();
        Executor getExecutor();
        Executor getTotalOrderExecutor();
        Executor getRemoteCommandExecutor();
        boolean isStrictPeerToPeer();
    }

    interface AuthorizationConfiguration {
        String getPrincipalMapper();
        Map<String, List<String>> getRoles();
    }

    interface Dependencies {
        ModuleLoader getModuleLoader();
        TransportConfiguration getTransportConfiguration();
        AuthorizationConfiguration getAuthorizationConfiguration();
        MBeanServer getMBeanServer();
        Executor getListenerExecutor();
        Executor getAsyncExecutor();
        Executor getStateTransferExecutor();
        ScheduledExecutorService getExpirationExecutor();
        ScheduledExecutorService getReplicationQueueExecutor();
    }

    private final String name;
    private final String defaultCache;
    private final boolean statistics;
    private final Dependencies dependencies;
    private final ModuleIdentifier moduleId;
    private volatile GlobalConfiguration config;

    public EmbeddedCacheManagerConfigurationService(String name, String defaultCache, boolean statistics, ModuleIdentifier moduleIdentifier, Dependencies dependencies) {
        this.name = name;
        this.defaultCache = defaultCache;
        this.statistics = statistics;
        this.moduleId = moduleIdentifier;
        this.dependencies = dependencies;
    }

    @Override
    public String getName() {
        return this.name;
    }

    @Override
    public String getDefaultCache() {
        return this.defaultCache;
    }

    @Override
    public GlobalConfiguration getGlobalConfiguration() {
        return this.config;
    }

    @Override
    public ModuleIdentifier getModuleIdentifier() {
        return this.moduleId;
    }

    @Override
    public EmbeddedCacheManagerConfiguration getValue() {
        return this;
    }

    @Override
    public void start(StartContext context) throws StartException {

        GlobalConfigurationBuilder builder = new GlobalConfigurationBuilder();
        ModuleLoader moduleLoader = this.dependencies.getModuleLoader();
        builder.serialization().classResolver(ModularClassResolver.getInstance(moduleLoader));
        ClassLoader loader = null;
        try {
            loader = (this.moduleId != null) ? moduleLoader.loadModule(this.moduleId).getClassLoader() : EmbeddedCacheManagerConfiguration.class.getClassLoader();
            builder.classLoader(loader);
            int id = Ids.MAX_ID;
            for (SimpleExternalizer<?> externalizer: ServiceFinder.load(SimpleExternalizer.class, loader)) {
                builder.serialization().addAdvancedExternalizer(id++, externalizer);
            }
        } catch (ModuleLoadException e) {
            throw new StartException(e);
        }
        builder.shutdown().hookBehavior(ShutdownHookBehavior.DONT_REGISTER);

        TransportConfiguration transport = this.dependencies.getTransportConfiguration();
        TransportConfigurationBuilder transportBuilder = builder.transport();

        if (transport != null) {
            transportBuilder.transport(new ChannelTransport(context.getController().getServiceContainer(), ChannelService.getServiceName(this.name)));
            Long timeout = transport.getLockTimeout();
            if (timeout != null) {
                transportBuilder.distributedSyncTimeout(timeout.longValue());
            }
            // Topology is retrieved from the channel
            org.jboss.as.clustering.jgroups.TransportConfiguration.Topology topology = transport.getChannelFactory().getProtocolStackConfiguration().getTransport().getTopology();
            if (topology != null) {
                String site = topology.getSite();
                if (site != null) {
                    transportBuilder.siteId(site);
                }
                String rack = topology.getRack();
                if (rack != null) {
                    transportBuilder.rackId(rack);
                }
                String machine = topology.getMachine();
                if (machine != null) {
                    transportBuilder.machineId(machine);
                }
            }
            transportBuilder.clusterName(this.name);

            Executor executor = transport.getExecutor();
            if (executor != null) {
                builder.transport().transportThreadPool().threadPoolFactory(new ManagedExecutorFactory(executor));
            }
            Executor totalOrderExecutor = transport.getTotalOrderExecutor();
            if (totalOrderExecutor != null) {
                builder.transport().totalOrderThreadPool().threadPoolFactory(new ManagedExecutorFactory(totalOrderExecutor));
           }
           Executor remoteCommandExecutor = transport.getRemoteCommandExecutor();
           if (remoteCommandExecutor != null) {
                builder.transport().remoteCommandThreadPool().threadPoolFactory(new ManagedExecutorFactory(remoteCommandExecutor));
           }
        }

        AuthorizationConfiguration authorization = this.dependencies.getAuthorizationConfiguration();
        GlobalAuthorizationConfigurationBuilder authorizationBuilder = builder.security().authorization();

        if (authorization != null) {
            authorizationBuilder.enable();
            if (authorization.getPrincipalMapper() != null) {
                try {
                    authorizationBuilder.principalRoleMapper(Class.forName(authorization.getPrincipalMapper(), true, loader).asSubclass(PrincipalRoleMapper.class).newInstance());
                } catch (Exception e) {
                    throw new StartException(e);
                }
            } else {
                authorizationBuilder.principalRoleMapper(new ClusterRoleMapper());
            }
            for(Entry<String, List<String>> role : authorization.getRoles().entrySet()) {
                GlobalRoleConfigurationBuilder roleBuilder = authorizationBuilder.role(role.getKey());
                for(String perm : role.getValue()) {
                    roleBuilder.permission(perm);
                }
            }
        }

        Executor listenerExecutor = this.dependencies.getListenerExecutor();
        if (listenerExecutor != null) {
            builder.listenerThreadPool().threadPoolFactory(new ManagedExecutorFactory(listenerExecutor));
        }
        Executor asyncExecutor = this.dependencies.getAsyncExecutor();
        if (asyncExecutor != null) {
            builder.asyncThreadPool().threadPoolFactory(
                  ThreadPoolExecutorFactories.mkManagedExecutorFactory(asyncExecutor));
        }
        ScheduledExecutorService expirationExecutor = this.dependencies.getExpirationExecutor();
        if (expirationExecutor != null) {
            builder.expirationThreadPool().threadPoolFactory(new ManagedScheduledExecutorFactory(expirationExecutor));
        }
        ScheduledExecutorService replicationQueueExecutor = this.dependencies.getReplicationQueueExecutor();
        if (replicationQueueExecutor != null) {
            builder.replicationQueueThreadPool().threadPoolFactory(new ManagedScheduledExecutorFactory(replicationQueueExecutor));
        }
        Executor stateTransferExecutor = this.dependencies.getStateTransferExecutor();
        if (stateTransferExecutor != null) {
            builder.stateTransferThreadPool().threadPoolFactory(new ManagedExecutorFactory(stateTransferExecutor));
        }

        GlobalJmxStatisticsConfigurationBuilder jmxBuilder = builder.globalJmxStatistics().cacheManagerName(this.name);
        jmxBuilder.jmxDomain(EmbeddedCacheManagerService.getServiceName(null).getCanonicalName());

        MBeanServer server = this.dependencies.getMBeanServer();
        if (server != null && this.statistics) {
            jmxBuilder.enable()
                .mBeanServerLookup(new MBeanServerProvider(server))
                .allowDuplicateDomains(true)
            ;
        } else {
            jmxBuilder.disable();
        }
        this.config = builder.build();
    }

    @Override
    public void stop(StopContext context) {
        // Nothing to stop
    }
}


File: server/integration/infinispan/src/test/java/org/jboss/as/clustering/infinispan/subsystem/InfinispanSubsystemDependenciesInitialization.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2014, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.infinispan.subsystem;

import java.io.Serializable;

import org.jboss.as.clustering.jgroups.subsystem.JGroupsExtension;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.RunningMode;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.extension.ExtensionRegistry;
import org.jboss.as.controller.extension.ExtensionRegistryType;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.registry.Resource;
import org.jboss.as.domain.management.CoreManagementResourceDefinition;
import org.jboss.as.domain.management.audit.AccessAuditResourceDefinition;
import org.jboss.as.jmx.JMXExtension;
import org.jboss.as.subsystem.test.AdditionalInitialization;
import org.jboss.as.txn.subsystem.TransactionExtension;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.FILE_HANDLER;


/**
 * Initializer for subsystem dependencies
 *
 * @author Paul Ferraro
 * @author William Burns
 * @author Tristan Tarrant
 */
public class InfinispanSubsystemDependenciesInitialization extends AdditionalInitialization implements Serializable {
    private static final long serialVersionUID = -4433079373360352449L;
    private final RunningMode mode;

    public InfinispanSubsystemDependenciesInitialization() {
        this(RunningMode.ADMIN_ONLY);
    }

    public InfinispanSubsystemDependenciesInitialization(RunningMode mode) {
        this.mode = mode;
    }

    @Override
    protected RunningMode getRunningMode() {
        return this.mode;
    }

    @Override
    protected void initializeExtraSubystemsAndModel(ExtensionRegistry registry, Resource root,
            ManagementResourceRegistration registration) {
        initializeJGroupsSubsystem(registry, root, registration);
        initializeTxnSubsystem(registry, root, registration);
    }

    private void initializeJGroupsSubsystem(ExtensionRegistry registry, Resource root,
            ManagementResourceRegistration registration) {
        new JGroupsExtension()
                .initialize(registry.getExtensionContext("jgroups", registration, ExtensionRegistryType.MASTER));

        Resource subsystem = Resource.Factory.create();
        subsystem.getModel().get("default-stack").set("tcp");
        root.registerChild(
                PathElement.pathElement(ModelDescriptionConstants.SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME),
                subsystem);

        Resource stack = Resource.Factory.create();
        subsystem.registerChild(PathElement.pathElement("stack", "tcp"), stack);

        Resource transport = Resource.Factory.create();
        transport.getModel().get("type").set("TCP");
        stack.registerChild(PathElement.pathElement(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME), transport);
    }

    private void initializeTxnSubsystem(ExtensionRegistry registry, Resource root,
            ManagementResourceRegistration registration) {
        new TransactionExtension()
                .initialize(registry.getExtensionContext("transactions", registration, ExtensionRegistryType.MASTER));
    }
}

File: server/integration/infinispan/src/test/java/org/jboss/as/clustering/infinispan/subsystem/InfinispanSubsystemTestCase.java
/*
* JBoss, Home of Professional Open Source.
* Copyright 2011, Red Hat Middleware LLC, and individual contributors
* as indicated by the @author tags. See the copyright.txt file in the
* distribution for a full listing of individual contributors.
*
* This is free software; you can redistribute it and/or modify it
* under the terms of the GNU Lesser General Public License as
* published by the Free Software Foundation; either version 2.1 of
* the License, or (at your option) any later version.
*
* This software is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
* Lesser General Public License for more details.
*
* You should have received a copy of the GNU Lesser General Public
* License along with this software; if not, write to the Free
* Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
* 02110-1301 USA, or see the FSF site: http://www.fsf.org.
*/
package org.jboss.as.clustering.infinispan.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.DESCRIBE;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SUBSYSTEM;

import java.util.Arrays;
import java.util.Collection;
import java.util.List;

import org.jboss.as.clustering.subsystem.ClusteringSubsystemTest;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.subsystem.test.AdditionalInitialization;
import org.jboss.as.subsystem.test.KernelServices;
import org.jboss.as.subsystem.test.ModelDescriptionValidator.ValidationConfiguration;
import org.jboss.dmr.ModelNode;
import org.junit.Assert;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

/**
 *
 * @author <a href="kabir.khan@jboss.com">Kabir Khan</a>
 */
@RunWith(value = Parameterized.class)
public class InfinispanSubsystemTestCase extends ClusteringSubsystemTest {

    String xmlFile = null ;
    int operations = 0 ;

    public InfinispanSubsystemTestCase(String xmlFile, int operations) {
        super(InfinispanExtension.SUBSYSTEM_NAME, new InfinispanExtension(), xmlFile);
        this.xmlFile = xmlFile ;
        this.operations = operations ;
    }

    @Parameters
    public static Collection<Object[]> data() {
      Object[][] data = new Object[][] {
                                         { "subsystem-infinispan_5_3.xml", 50 },
                                         { "subsystem-infinispan_6_0.xml", 75 },
                                         { "subsystem-infinispan_7_0.xml", 88 },
                                         { "subsystem-infinispan_7_1.xml", 88 },
                                         { "subsystem-infinispan_7_2.xml", 88 },
                                         { "subsystem-infinispan_8_0.xml", 90 },
                                       };
      return Arrays.asList(data);
    }

    @Override
    protected ValidationConfiguration getModelValidationConfiguration() {
        // use this configuration to report any exceptional cases for DescriptionProviders
        return new ValidationConfiguration();
    }

    /**
     * Tests that the xml is parsed into the correct operations
     */
    @Test
    public void testParseSubsystem() throws Exception {
       // Parse the subsystem xml into operations
       List<ModelNode> operations = super.parse(getSubsystemXml());

       /*
       // print the operations
       System.out.println("List of operations");
       for (ModelNode op : operations) {
           System.out.println("operation = " + op.toString());
       }
       */

       // Check that we have the expected number of operations
       // one for each resource instance
       Assert.assertEquals(this.operations, operations.size());

       // Check that each operation has the correct content
       ModelNode addSubsystem = operations.get(0);
       Assert.assertEquals(ADD, addSubsystem.get(OP).asString());
       PathAddress addr = PathAddress.pathAddress(addSubsystem.get(OP_ADDR));
       Assert.assertEquals(1, addr.size());
       PathElement element = addr.getElement(0);
       Assert.assertEquals(SUBSYSTEM, element.getKey());
       Assert.assertEquals(getMainSubsystemName(), element.getValue());
    }

    /**
     * Test that the model created from the xml looks as expected
     */
    @Test
    public void testInstallIntoController() throws Exception {
       // Parse the subsystem xml and install into the controller
       KernelServices services = createKernelServicesBuilder(AdditionalInitialization.MANAGEMENT).setSubsystemXml(getSubsystemXml()).build();

       // Read the whole model and make sure it looks as expected
       ModelNode model = services.readWholeModel();

       //System.out.println("model = " + model.asString());

       Assert.assertTrue(model.get(SUBSYSTEM).hasDefined(getMainSubsystemName()));
    }

    /**
     * Starts a controller with a given subsystem xml and then checks that a second controller
     * started with the xml marshalled from the first one results in the same model
     */
    @Test
    public void testParseAndMarshalModel() throws Exception {
       // Parse the subsystem xml and install into the first controller

       KernelServices servicesA = createKernelServicesBuilder(AdditionalInitialization.MANAGEMENT).setSubsystemXml(getSubsystemXml()).build();

       // Get the model and the persisted xml from the first controller
       ModelNode modelA = servicesA.readWholeModel();
       String marshalled = servicesA.getPersistedSubsystemXml();

       // Install the persisted xml from the first controller into a second controller
       KernelServices servicesB = createKernelServicesBuilder(AdditionalInitialization.MANAGEMENT).setSubsystemXml(marshalled).build();
       ModelNode modelB = servicesB.readWholeModel();

       // Make sure the models from the two controllers are identical
       super.compare(modelA, modelB);
    }

    /**
     * Starts a controller with the given subsystem xml and then checks that a second controller
     * started with the operations from its describe action results in the same model
     */
    @Test
    public void testDescribeHandler() throws Exception {
       // Parse the subsystem xml and install into the first controller
       KernelServices servicesA = createKernelServicesBuilder(AdditionalInitialization.MANAGEMENT).setSubsystemXml(getSubsystemXml()).build();
       // Get the model and the describe operations from the first controller
       ModelNode modelA = servicesA.readWholeModel();
       ModelNode describeOp = new ModelNode();
       describeOp.get(OP).set(DESCRIBE);
       describeOp.get(OP_ADDR).set(PathAddress.pathAddress(PathElement.pathElement(SUBSYSTEM, getMainSubsystemName())).toModelNode());
       List<ModelNode> operations = checkResultAndGetContents(servicesA.executeOperation(describeOp)).asList();

       // Install the describe options from the first controller into a second controller
       KernelServices servicesB = createKernelServicesBuilder(null).setBootOperations(operations).build();
       ModelNode modelB = servicesB.readWholeModel();

       // Make sure the models from the two controllers are identical
       super.compare(modelA, modelB);

    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/JChannelFactory.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups;

import static org.jboss.as.clustering.jgroups.JGroupsLogger.ROOT_LOGGER;

import java.net.InetSocketAddress;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

import javax.management.MBeanServer;

import org.jboss.as.domain.management.SecurityRealm;
import org.jboss.as.network.SocketBinding;
import org.jboss.as.server.ServerEnvironment;
import org.jgroups.Channel;
import org.jgroups.ChannelListener;
import org.jgroups.Global;
import org.jgroups.JChannel;
import org.jgroups.conf.PropertyConverters;
import org.jgroups.conf.ProtocolStackConfigurator;
import org.jgroups.jmx.JmxConfigurator;
import org.jgroups.protocols.SASL;
import org.jgroups.protocols.TP;
import org.jgroups.protocols.pbcast.GMS;
import org.jgroups.protocols.relay.RELAY2;
import org.jgroups.protocols.relay.config.RelayConfig;
import org.jgroups.stack.Configurator;
import org.jgroups.stack.Protocol;
import org.jgroups.stack.ProtocolStack;
import org.jgroups.util.SocketFactory;
import org.jgroups.util.Util;

/**
 * @author Paul Ferraro
 *
 */
public class JChannelFactory implements ChannelFactory, ChannelListener, ProtocolStackConfigurator {

    private final ProtocolStackConfiguration configuration;
    private final Map<Channel, String> channels = Collections.synchronizedMap(new WeakHashMap<Channel, String>());

    public JChannelFactory(ProtocolStackConfiguration configuration) {
        this.configuration = configuration;
    }

    @Override
    public ServerEnvironment getServerEnvironment() {
        return this.configuration.getEnvironment();
    }

    @Override
    public ProtocolStackConfiguration getProtocolStackConfiguration() {
        return this.configuration;
    }

    @Override
    public Channel createChannel(final String id) throws Exception {
        JChannel channel = new JChannel(this);

        // We need to synchronize on shared transport,
        // so we don't attempt to init a shared transport multiple times
        TP transport = channel.getProtocolStack().getTransport();
        if (transport.isSingleton()) {
            synchronized (transport) {
                this.init(transport);
            }
        } else {
            this.init(transport);
        }

        // Relay protocol is added to stack programmatically, not via ProtocolStackConfigurator
        final RelayConfiguration relayConfig = this.configuration.getRelay();
        if (relayConfig != null) {
            final String localSite = relayConfig.getSiteName();
            final List<RemoteSiteConfiguration> remoteSites = this.configuration.getRelay().getRemoteSites();
            final List<String> sites = new ArrayList<String>(remoteSites.size() + 1);
            sites.add(localSite);
            // Collect bridges, eliminating duplicates
            final Map<String, RelayConfig.BridgeConfig> bridges = new HashMap<String, RelayConfig.BridgeConfig>();
            for (final RemoteSiteConfiguration remoteSite: remoteSites) {
                final String siteName = remoteSite.getName();
                sites.add(siteName);
                final String cluster = remoteSite.getCluster();
                final String clusterName = (cluster != null) ? cluster : siteName;
                final RelayConfig.BridgeConfig bridge = new RelayConfig.BridgeConfig(clusterName) {
                    @Override
                    public JChannel createChannel() throws Exception {
                        return (JChannel) remoteSite.getChannelFactory().createChannel(id + "/" + clusterName);
                    }
                };
                bridges.put(clusterName, bridge);
            }
            // Acquire consistent order of sites
            Collections.sort(sites);
            final RELAY2 relay = new RELAY2().site(localSite);
            for (short i = 0; i < sites.size(); ++i) {
                final String site = sites.get(i);
                RelayConfig.SiteConfig siteConfig = new RelayConfig.SiteConfig(site);
                relay.addSite(site, siteConfig);
                if (site.equals(localSite)) {
                    for (RelayConfig.BridgeConfig bridge: bridges.values()) {
                        siteConfig.addBridge(bridge);
                    }
                }
            }
            Configurator.resolveAndAssignFields(relay, relayConfig.getProperties());
            Configurator.resolveAndInvokePropertyMethods(relay, relayConfig.getProperties());
            channel.getProtocolStack().addProtocol(relay);
            relay.init();
        }

        // Handle the Sasl protocol
        final SaslConfiguration saslConfig = this.configuration.getSasl();
        if (saslConfig != null) {
           final String clusterRole = saslConfig.getClusterRole();
           final SecurityRealm securityRealm = saslConfig.getSecurityRealm();
           final String mech = saslConfig.getMech();
           final SASL sasl = new SASL();
           sasl.setMech(mech);
           Map<String, String> props = saslConfig.getProperties();
           if (props.containsKey("client_password")) {
               String credential = props.get("client_password");
               String name = props.get("client_name");
               if (name == null) {
                   sasl.setClientCallbackHandler(new SaslClientCallbackHandler(securityRealm.getName(), this.configuration.getEnvironment().getNodeName(), credential));
               } else if (name.contains("@")) {
                   sasl.setClientCallbackHandler(new SaslClientCallbackHandler(name, credential));
               } else {
                   sasl.setClientCallbackHandler(new SaslClientCallbackHandler(securityRealm.getName(), name, credential));
               }
           } else {
               props.put("client_password", ""); // HACKY
           }
           Map<String, String> saslProps = props.containsKey("sasl_props") ? Util.parseCommaDelimitedProps(props.get("sasl_props")) : new HashMap<String, String>();
           sasl.setServerCallbackHandler(new RealmAuthorizationCallbackHandler(securityRealm, mech, clusterRole !=null  ? clusterRole : id, saslProps));
           props.put("sasl_props",  new PropertyConverters.StringProperties().toString(saslProps));
           Configurator.resolveAndAssignFields(sasl, props);
           Configurator.resolveAndInvokePropertyMethods(sasl, props);
           channel.getProtocolStack().insertProtocol(sasl, ProtocolStack.BELOW, GMS.class);
           sasl.init();
        }

        channel.setName(this.configuration.getEnvironment().getNodeName() + "/" + id);

        TransportConfiguration.Topology topology = this.configuration.getTransport().getTopology();
        if (topology != null) {
            channel.setAddressGenerator(new TopologyAddressGenerator(channel, topology.getSite(), topology.getRack(), topology.getMachine()));
        }

        MBeanServer server = this.configuration.getMBeanServer();
        if (server != null) {
            try {
                this.channels.put(channel, id);
                JmxConfigurator.registerChannel(channel, server, id);
            } catch (Exception e) {
                ROOT_LOGGER.warn(e.getMessage(), e);
            }
            channel.addChannelListener(this);
        }

        return channel;
    }

    private void init(TP transport) {
        TransportConfiguration transportConfig = this.configuration.getTransport();
        SocketBinding binding = transportConfig.getSocketBinding();
        if (binding != null) {
            SocketFactory factory = transport.getSocketFactory();
            if (!(factory instanceof ManagedSocketFactory)) {
                transport.setSocketFactory(new ManagedSocketFactory(factory, binding.getSocketBindings()));
            }
        }
    }

    /**
     * {@inheritDoc}
     * @see org.jgroups.conf.ProtocolStackConfigurator#getProtocolStackString()
     */
    @Override
    public String getProtocolStackString() {
        return null;
    }

    /**
     * {@inheritDoc}
     * @see org.jgroups.conf.ProtocolStackConfigurator#getProtocolStack()
     */
    @Override
    public List<org.jgroups.conf.ProtocolConfiguration> getProtocolStack() {
        List<org.jgroups.conf.ProtocolConfiguration> configs = new ArrayList<org.jgroups.conf.ProtocolConfiguration>(this.configuration.getProtocols().size() + 1);
        TransportConfiguration transport = this.configuration.getTransport();
        org.jgroups.conf.ProtocolConfiguration config = this.createProtocol(transport);
        Map<String, String> properties = config.getProperties();

        if (transport.isShared()) {
            properties.put(Global.SINGLETON_NAME, this.configuration.getName());
        }

        SocketBinding binding = transport.getSocketBinding();
        if (binding != null) {
            this.configureBindAddress(transport, config, binding);
            this.configureServerSocket(transport, config, "bind_port", binding);
            this.configureMulticastSocket(transport, config, "mcast_addr", "mcast_port", binding);
        }

        SocketBinding diagnosticsSocketBinding = transport.getDiagnosticsSocketBinding();
        boolean diagnostics = (diagnosticsSocketBinding != null);
        properties.put("enable_diagnostics", String.valueOf(diagnostics));
        if (diagnostics) {
            this.configureMulticastSocket(transport, config, "diagnostics_addr", "diagnostics_port", diagnosticsSocketBinding);
        }

        configs.add(config);

        boolean supportsMulticast = transport.hasProperty("mcast_addr");

        for (ProtocolConfiguration protocol: this.configuration.getProtocols()) {
            config = this.createProtocol(protocol);
            binding = protocol.getSocketBinding();
            if (binding != null) {
                this.configureBindAddress(protocol, config, binding);
                this.configureServerSocket(protocol, config, "bind_port", binding);
                this.configureServerSocket(protocol, config, "start_port", binding);
                this.configureMulticastSocket(protocol, config, "mcast_addr", "mcast_port", binding);
            } else if (transport.getSocketBinding() != null) {
                // If no socket-binding was specified, use bind address of transport
                this.configureBindAddress(protocol, config, transport.getSocketBinding());
            }
            if (!supportsMulticast) {
                this.setProperty(protocol, config, "use_mcast_xmit", String.valueOf(false));
            }
            configs.add(config);
        }
        return configs;
    }

    private void configureBindAddress(ProtocolConfiguration protocol, org.jgroups.conf.ProtocolConfiguration config, SocketBinding binding) {
        this.setPropertyNoOverride(protocol, config, "bind_addr", binding.getSocketAddress().getAddress().getHostAddress());
    }

    private void configureServerSocket(ProtocolConfiguration protocol, org.jgroups.conf.ProtocolConfiguration config, String property, SocketBinding binding) {
        this.setPropertyNoOverride(protocol, config, property, String.valueOf(binding.getSocketAddress().getPort()));
    }

    private void configureMulticastSocket(ProtocolConfiguration protocol, org.jgroups.conf.ProtocolConfiguration config, String addressProperty, String portProperty, SocketBinding binding) {
        try {
            InetSocketAddress mcastSocketAddress = binding.getMulticastSocketAddress();
            this.setPropertyNoOverride(protocol, config, addressProperty, mcastSocketAddress.getAddress().getHostAddress());
            this.setPropertyNoOverride(protocol, config, portProperty, String.valueOf(mcastSocketAddress.getPort()));
        } catch (IllegalStateException e) {
            ROOT_LOGGER.couldNotSetAddressAndPortNoMulticastSocket(e, config.getProtocolName(), addressProperty, config.getProtocolName(), portProperty, binding.getName());
        }
    }

    private void setPropertyNoOverride(ProtocolConfiguration protocol, org.jgroups.conf.ProtocolConfiguration config, String name, String value) {
        boolean overridden = false ;
        String propertyValue = null ;
        // check if the property has been overridden by the user and log a message
        try {
            if (overridden = config.getOriginalProperties().containsKey(name))
               propertyValue = config.getOriginalProperties().get(name);
        }
        catch(Exception e) {
            ROOT_LOGGER.unableToAccessProtocolPropertyValue(e, name, protocol.getName());
        }

        // log a warning if property tries to override
        if (overridden) {
            ROOT_LOGGER.unableToOverrideSocketBindingValue(name, protocol.getName(), value, propertyValue);
        }
        setProperty(protocol, config, name, value);
    }

    private void setProperty(ProtocolConfiguration protocol, org.jgroups.conf.ProtocolConfiguration config, String name, String value) {
        if (protocol.hasProperty(name)) {
            config.getProperties().put(name, value);
        }
    }

    private org.jgroups.conf.ProtocolConfiguration createProtocol(final ProtocolConfiguration protocolConfig) {
        String protocol = protocolConfig.getName();
        final Map<String, String> properties = new HashMap<String, String>(this.configuration.getDefaults().getProperties(protocol));
        properties.putAll(protocolConfig.getProperties());
        return new org.jgroups.conf.ProtocolConfiguration(protocol, properties) {
            @Override
            public Map<String, String> getOriginalProperties() {
                return properties;
            }
        };
    }

    private void setValue(Protocol protocol, String property, Object value) {
        ROOT_LOGGER.setProtocolPropertyValue(protocol.getName(), property, value);
        try {
            protocol.setValue(property, value);
        } catch (IllegalArgumentException e) {
            ROOT_LOGGER.nonExistentProtocolPropertyValue(e, protocol.getName(), property, value);
        }
    }

    @Override
    public void channelConnected(Channel channel) {
        // no-op
    }

    @Override
    public void channelDisconnected(Channel channel) {
        // no-op
    }

    @Override
    public void channelClosed(Channel channel) {
        MBeanServer server = this.configuration.getMBeanServer();
        if (server != null) {
            try {
                JmxConfigurator.unregisterChannel((JChannel) channel, server, this.channels.remove(channel));
            } catch (Exception e) {
                ROOT_LOGGER.warn(e.getMessage(), e);
            }
        }
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/JGroupsLogger.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.jgroups;

import static org.jboss.logging.Logger.Level.ERROR;
import static org.jboss.logging.Logger.Level.INFO;
import static org.jboss.logging.Logger.Level.TRACE;
import static org.jboss.logging.Logger.Level.WARN;

import org.jboss.logging.BasicLogger;
import org.jboss.logging.annotations.Cause;
import org.jboss.logging.annotations.LogMessage;
import org.jboss.logging.Logger;
import org.jboss.logging.annotations.Message;
import org.jboss.logging.annotations.MessageLogger;

/**
 * Date: 29.08.2011
 *
 * @author <a href="mailto:jperkins@redhat.com">James R. Perkins</a>
 */
@MessageLogger(projectCode = "JBAS")
public interface JGroupsLogger extends BasicLogger {
    String ROOT_LOGGER_CATEGORY = JGroupsLogger.class.getPackage().getName();

    /**
     * The root logger.
     */
    JGroupsLogger ROOT_LOGGER = Logger.getMessageLogger(JGroupsLogger.class, ROOT_LOGGER_CATEGORY);

    /**
     * Logs an informational message indicating the JGroups subsystem is being activated.
     */
    @LogMessage(level = INFO)
    @Message(id = 10260, value = "Activating JGroups subsystem.")
    void activatingSubsystem();

    @LogMessage(level = TRACE)
    @Message(id = 10261, value = "Setting %s.%s=%d")
    void setProtocolPropertyValue(String protocol, String property, Object value);

    @LogMessage(level = TRACE)
    @Message(id = 10262, value = "Failed to set non-existent %s.%s=%d")
    void nonExistentProtocolPropertyValue(@Cause Throwable cause, String protocolName, String propertyName, Object propertyValue);

    @LogMessage(level = TRACE)
    @Message(id = 10263, value = "Could not set %s.%s and %s.%s, %s socket binding does not specify a multicast socket")
    void couldNotSetAddressAndPortNoMulticastSocket(@Cause Throwable cause, String protocolName, String addressProperty, String protocolNameAgain, String portProperty, String bindingName);

    @LogMessage(level = ERROR)
    @Message(id = 10264, value = "Error accessing original value for property %s of protocol %s")
    void unableToAccessProtocolPropertyValue(@Cause Throwable cause, String propertyName, String protocolName);

    @LogMessage(level = WARN)
    @Message(id = 10265, value = "property %s for protocol %s attempting to override socket binding value %s : property value %s will be ignored")
    void unableToOverrideSocketBindingValue(String propertyName, String protocolName, String bindingName, Object propertyValue);

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/JGroupsMessages.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.jgroups;

import java.net.URL;

import org.jboss.as.controller.OperationFailedException;
import org.jboss.logging.annotations.Message;
import org.jboss.logging.annotations.MessageBundle;
import org.jboss.logging.Messages;

/**
 * Date: 29.08.2011
 *
 * @author <a href="mailto:jperkins@redhat.com">James R. Perkins</a>
 */
@MessageBundle(projectCode = "JBAS")
public interface JGroupsMessages {
    /**
     * The messages.
     */
    JGroupsMessages MESSAGES = Messages.getBundle(JGroupsMessages.class);

    /**
     * A message indicating a file could not be parsed.
     *
     * @param url the path to the file.
     *
     * @return the message.
     */
    @Message(id = 10270, value = "Failed to parse %s")
    String parserFailure(URL url);

    /**
     * A message indicating a resource could not be located.
     *
     * @param resource the resource that could not be located.
     *
     * @return the message.
     */
    @Message(id = 10271, value = "Failed to locate %s")
    String notFound(String resource);

    @Message(id = 10272, value = "A node named %s already exists in this cluster.  Perhaps there is already a server running on this host?  If so, restart this server with a unique node name, via -Djboss.node.name=<node-name>")
    IllegalStateException duplicateNodeName(String name);

    @Message(id = 10273, value = "Transport for stack %s is not defined. Please specify both a transport and protocol list, either as optional parameters to add() or via batching.")
    OperationFailedException transportNotDefined(String stackName);

    @Message(id = 10274, value = "Protocol list for stack %s is not defined. Please specify both a transport and protocol list, either as optional parameters to add() or via batching.")
    OperationFailedException protocolListNotDefined(String stackName);

    @Message(id = 10275, value = "Protocol with relative path %s is already defined.")
    OperationFailedException protocolAlreadyDefined(String relativePath);

    @Message(id = 10276, value = "Protocol with relative path %s is not defined.")
    OperationFailedException protocolNotDefined(String relativePath);

    @Message(id = 10277, value = "Property %s for protocol with relative path %s is not defined. ")
    OperationFailedException propertyNotDefined(String propertyName, String protocolRelativePath);

    @Message(id = 10299, value = "Unauthorized node %s attempting to join cluster.")
    SecurityException unauthorizedNodeJoin(String nodeName);
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/ThreadFactoryAdapter.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups;

import java.util.concurrent.ThreadFactory;


/**
 * Adapts a {@link ThreadFactory} to a {@link org.jgroups.util.ThreadFactory}.
 * @author Paul Ferraro
 */
public class ThreadFactoryAdapter implements org.jgroups.util.ThreadFactory {
    private final ThreadFactory factory;
    public ThreadFactoryAdapter(ThreadFactory factory) {
        this.factory = factory;
    }

    /**
     * @see java.util.concurrent.ThreadFactory#newThread(java.lang.Runnable)
     */
    @Override
    public Thread newThread(Runnable r) {
        return this.factory.newThread(r);
    }

    /**
     * @see org.jgroups.util.ThreadFactory#newThread(java.lang.Runnable, java.lang.String)
     */
    @Override
    public Thread newThread(Runnable r, String name) {
        return this.factory.newThread(r);
    }

    /**
     * @see org.jgroups.util.ThreadFactory#newThread(java.lang.ThreadGroup, java.lang.Runnable, java.lang.String)
     */
    @Override
    public Thread newThread(ThreadGroup group, Runnable r, String name) {
        return this.factory.newThread(r);
    }

    /**
     * @see org.jgroups.util.ThreadFactory#setPattern(java.lang.String)
     */
    @Override
    public void setPattern(String pattern) {
        // no-op
    }

    /**
     * @see org.jgroups.util.ThreadFactory#setIncludeClusterName(boolean)
     */
    @Override
    public void setIncludeClusterName(boolean includeClusterName) {
        // no-op
    }

    /**
     * @see org.jgroups.util.ThreadFactory#setClusterName(java.lang.String)
     */
    @Override
    public void setClusterName(String channelName) {
        // no-op
    }

    /**
     * @see org.jgroups.util.ThreadFactory#setAddress(java.lang.String)
     */
    @Override
    public void setAddress(String address) {
        // no-op
    }

    /**
     * @see org.jgroups.util.ThreadFactory#renameThread(java.lang.String, java.lang.Thread)
     */
    @Override
    public void renameThread(String base_name, Thread thread) {
        // no-op
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/TimerSchedulerAdapter.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups;

import java.lang.reflect.Field;
import java.security.AccessController;
import java.security.PrivilegedAction;
import java.util.concurrent.Delayed;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executor;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.jgroups.util.ThreadFactory;
import org.jgroups.util.TimeScheduler;

/**
 * Adapts a {@link ScheduledExecutorService} to a {@link TimeScheduler}.
 * Disallow modification of the pool itself - this should be done via
 * the threading subsystem directly.
 * @author Paul Ferraro
 */
public class TimerSchedulerAdapter implements TimeScheduler {

    private final ScheduledExecutorService executor;

    public TimerSchedulerAdapter(ScheduledExecutorService executor) {
        this.executor = executor;
    }

    @Override
    public void execute(Runnable command) {
        this.executor.execute(command);
    }

    @Override
    public ScheduledFuture<?> schedule(Runnable command, long delay, TimeUnit unit) {
        return this.executor.schedule(command, delay, unit);
    }

    @Override
    public ScheduledFuture<?> scheduleWithFixedDelay(Runnable command, long initialDelay, long delay, TimeUnit unit) {
        return this.executor.scheduleWithFixedDelay(command, initialDelay, delay, unit);
    }

    @Override
    public ScheduledFuture<?> scheduleAtFixedRate(Runnable command, long initialDelay, long period, TimeUnit unit) {
        return this.executor.scheduleAtFixedRate(command, initialDelay, period, unit);
    }

    @SuppressWarnings("unchecked")
    @Override
    public ScheduledFuture<?> scheduleWithDynamicInterval(final Task task) {

        final MutableScheduledFuture<Object> future = new MutableScheduledFuture<Object>((ScheduledFuture<Object>) this.schedule(task, task.nextInterval(), TimeUnit.MILLISECONDS));
        final long nextInterval = task.nextInterval();
        if (nextInterval > 0) {
            Runnable scheduleTask = new Runnable() {
                @Override
                public void run() {
                    try {
                        future.get();
                        long interval = nextInterval;
                        while ((interval > 0) && !Thread.currentThread().isInterrupted()) {
                            future.setFuture((ScheduledFuture<Object>) TimerSchedulerAdapter.this.schedule(task, interval, TimeUnit.MILLISECONDS));
                            future.get();
                            interval = task.nextInterval();
                        }
                    } catch (InterruptedException e) {
                    } catch (ExecutionException e) {
                    }
                }
            };
            this.execute(scheduleTask);
        }
        return future;
    }

    @Override
    public void setThreadFactory(ThreadFactory factory) {
        // Do nothing
    }

    @Override
    public String dumpTimerTasks() {
        return this.getThreadPool().getQueue().toString();
    }

    @Override
    public int getMinThreads() {
        return this.getThreadPool().getCorePoolSize();
    }

    @Override
    public void setMinThreads(int size) {
        // Do nothing
    }

    @Override
    public int getMaxThreads() {
        return this.getThreadPool().getMaximumPoolSize();
    }

    @Override
    public void setMaxThreads(int size) {
        // Do nothing
    }

    @Override
    public long getKeepAliveTime() {
        return this.getThreadPool().getKeepAliveTime(TimeUnit.MILLISECONDS);
    }

    @Override
    public void setKeepAliveTime(long time) {
        // Do nothing
    }

    @Override
    public int getCurrentThreads() {
        return this.getThreadPool().getActiveCount();
    }

    @Override
    public int size() {
        return this.getThreadPool().getPoolSize();
    }

    @Override
    public void stop() {
        this.executor.shutdown();
    }

    @Override
    public boolean isShutdown() {
        return this.executor.isShutdown();
    }

    private ThreadPoolExecutor getThreadPool() {
        return getThreadPool(this.executor);
    }

    private static ThreadPoolExecutor getThreadPool(Executor executor) {
        if (executor instanceof ThreadPoolExecutor) {
            return (ThreadPoolExecutor) executor;
        } else {
            // This must be a decorator - try to hack out the delegate
            final Field field = getField(executor.getClass(), Executor.class);
            if (field != null) {
                PrivilegedAction<Void> action = new PrivilegedAction<Void>() {
                    @Override
                    public Void run() {
                        field.setAccessible(true);
                        return null;
                    }
                };
                AccessController.doPrivileged(action);
                try {
                    return getThreadPool((Executor) field.get(executor));
                } catch (IllegalAccessException e) {
                    throw new IllegalStateException(e);
                }
            }
        }
        throw new UnsupportedOperationException();
    }

    private static <T> Field getField(Class<? extends T> targetClass, Class<T> fieldClass) {
        for (Field field: targetClass.getDeclaredFields()) {
            if (fieldClass.isAssignableFrom(field.getType())) {
                return field;
            }
        }
        Class<?> superClass = targetClass.getSuperclass();
        return (superClass != null) && fieldClass.isAssignableFrom(superClass) ? getField(superClass.asSubclass(fieldClass), fieldClass) : null;
    }

    private static class MutableScheduledFuture<T> implements ScheduledFuture<T> {
        private volatile ScheduledFuture<T> future;

        MutableScheduledFuture(ScheduledFuture<T> future) {
            this.setFuture(future);
        }

        void setFuture(ScheduledFuture<T> future) {
            this.future = future;
        }

        @Override
        public long getDelay(TimeUnit unit) {
            return this.future.getDelay(unit);
        }

        @Override
        public int compareTo(Delayed delayed) {
            return this.future.compareTo(delayed);
        }

        @Override
        public boolean cancel(boolean mayInterruptIfRunning) {
            return this.future.cancel(mayInterruptIfRunning);
        }

        @Override
        public boolean isCancelled() {
            return this.future.isCancelled();
        }

        @Override
        public boolean isDone() {
            return this.future.isDone();
        }

        @Override
        public T get() throws InterruptedException, ExecutionException {
            return this.future.get();
        }

        @Override
        public T get(long timeout, TimeUnit unit) throws InterruptedException, ExecutionException, TimeoutException {
            return this.future.get(timeout, unit);
        }
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/ChannelFactoryService.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import org.jboss.as.clustering.jgroups.ChannelFactory;
import org.jboss.as.clustering.jgroups.JChannelFactory;
import org.jboss.as.clustering.jgroups.ProtocolStackConfiguration;
import org.jboss.msc.service.Service;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.StartContext;
import org.jboss.msc.service.StartException;
import org.jboss.msc.service.StopContext;

/**
 * @author Paul Ferraro
 */
public class ChannelFactoryService implements Service<ChannelFactory> {
    private static final ServiceName SERVICE_NAME = ServiceName.JBOSS.append(JGroupsExtension.SUBSYSTEM_NAME).append("stack");

    private final ProtocolStackConfiguration configuration;

    private volatile ChannelFactory factory;

    public static ServiceName getServiceName(String name) {
        return (name != null) ? SERVICE_NAME.append(name) : SERVICE_NAME;
    }

    public ChannelFactoryService(ProtocolStackConfiguration configuration) {
        this.configuration = configuration;
    }

    @Override
    public void start(StartContext context) throws StartException {
        this.factory = new JChannelFactory(this.configuration);
    }

    @Override
    public void stop(StopContext context) {
        this.factory = null;
    }

    @Override
    public ChannelFactory getValue() {
        return this.factory;
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/ChannelService.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.clustering.jgroups.JGroupsLogger.ROOT_LOGGER;

import org.jboss.as.clustering.jgroups.ChannelFactory;
import org.jboss.as.clustering.jgroups.JGroupsMessages;
import org.jboss.msc.service.Service;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.StartContext;
import org.jboss.msc.service.StartException;
import org.jboss.msc.service.StopContext;
import org.jboss.msc.value.Value;
import org.jgroups.Address;
import org.jgroups.Channel;
import org.jgroups.ChannelListener;

/**
 * Provides a channel for use by dependent services.
 * Channels produced by this service are unconnected.
 * @author Paul Ferraro
 */
public class ChannelService implements Service<Channel>, ChannelListener {

    private static final ServiceName SERVICE_NAME = ServiceName.JBOSS.append(JGroupsExtension.SUBSYSTEM_NAME).append("channel");

    public static ServiceName getServiceName(String id) {
        return SERVICE_NAME.append(id);
    }

    private final Value<ChannelFactory> factory;
    private final String id;
    private volatile Channel channel;

    public ChannelService(String id, Value<ChannelFactory> factory) {
        this.id = id;
        this.factory = factory;
    }

    @Override
    public Channel getValue() {
        return this.channel;
    }

    @Override
    public void start(StartContext context) throws StartException {
        ChannelFactory factory = this.factory.getValue();
        try {
            this.channel = factory.createChannel(this.id);
            this.channel.addChannelListener(this);
            // Don't connect the channel here
            // This will be done by Infinispan (see AS7-5904)
        } catch (Exception e) {
            throw new StartException(e);
        }

        if  (ROOT_LOGGER.isTraceEnabled())  {
            String output = this.channel.getProtocolStack().printProtocolSpec(true);
            ROOT_LOGGER.tracef("JGroups channel named %s created with configuration:\n %s", this.id, output);
        }
    }

    @Override
    public void stop(StopContext context) {
        if (this.channel != null) {
            this.channel.removeChannelListener(this);
        }
        this.channel = null;
    }

    @Override
    public void channelClosed(Channel channel) {
        // Do nothing
    }

    @Override
    public void channelConnected(Channel channel) {
        // Validate view
        String localName = channel.getName();
        Address localAddress = channel.getAddress();
        for (Address address: channel.getView()) {
            String name = channel.getName(address);
            if ((name != null) && name.equals(localName) && !address.equals(localAddress)) {
                channel.close();
                throw JGroupsMessages.MESSAGES.duplicateNodeName(this.factory.getValue().getProtocolStackConfiguration().getEnvironment().getNodeName());
            }
        }
    }

    @Override
    public void channelDisconnected(Channel channel) {
        // Do nothing
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemAdd.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.clustering.jgroups.JGroupsLogger.ROOT_LOGGER;

import java.util.List;

import org.jboss.as.clustering.jgroups.ChannelFactory;
import org.jboss.as.clustering.jgroups.ProtocolDefaults;
import org.jboss.as.controller.AbstractAddStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.ServiceVerificationHandler;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.service.ValueService;
import org.jboss.msc.value.InjectedValue;

/**
 * Handler for JGroups subsystem add operations.
 *
 * @author Paul Ferraro
 * @author Richard Achmatowicz (c) 2011 Red Hat, Inc
 */
public class JGroupsSubsystemAdd extends AbstractAddStepHandler {

    public static final JGroupsSubsystemAdd INSTANCE = new JGroupsSubsystemAdd();

    static ModelNode createOperation(ModelNode address, ModelNode existing) throws OperationFailedException {
        ModelNode operation = Util.getEmptyOperation(ModelDescriptionConstants.ADD, address);
        populate(existing, operation);
        return operation;
    }

    private static void populate(ModelNode source, ModelNode target) throws OperationFailedException {

        JGroupsSubsystemRootResource.DEFAULT_STACK.validateAndSet(source, target);
        target.get(ModelKeys.STACK).setEmptyObject();
    }

    @Override
    protected void populateModel(ModelNode operation, ModelNode model) throws OperationFailedException {
        populate(operation, model);
    }

    @Override
    protected void performRuntime(OperationContext context, ModelNode operation, ModelNode model, ServiceVerificationHandler verificationHandler, List<ServiceController<?>> newControllers)
            throws OperationFailedException {
        installRuntimeServices(context, operation, model, verificationHandler, newControllers);
    }

    protected void installRuntimeServices(OperationContext context, ModelNode operation, ModelNode model, ServiceVerificationHandler verificationHandler, List<ServiceController<?>> newControllers) throws OperationFailedException {

        ROOT_LOGGER.activatingSubsystem();
        ServiceTarget target = context.getServiceTarget();

        // install the protocol defaults service
        ServiceController<ProtocolDefaults> pdsController = installProtocolDefaultsService(target, verificationHandler);
        if (newControllers != null) {
            newControllers.add(pdsController);
        }

        final String stack = JGroupsSubsystemRootResource.DEFAULT_STACK.resolveModelAttribute(context, model).asString() ;

        // install the default channel factory service
        ServiceController<ChannelFactory> dcfsController = installDefaultChannelFactoryService(target, stack, verificationHandler);
        if (newControllers != null) {
            newControllers.add(dcfsController);
        }
    }

    protected void removeRuntimeServices(OperationContext context, ModelNode operation, ModelNode model)
            throws OperationFailedException {

        // remove the ProtocolDefaultsService
        ServiceName protocolDefaultsService = ProtocolDefaultsService.SERVICE_NAME;
        context.removeService(protocolDefaultsService);

        // remove the DefaultChannelFactoryServiceAlias
        ServiceName defaultChannelFactoryService = ChannelFactoryService.getServiceName(null);
        context.removeService(defaultChannelFactoryService);
    }

    protected ServiceController<ProtocolDefaults> installProtocolDefaultsService(ServiceTarget target, ServiceVerificationHandler verificationHandler) {
        ServiceBuilder<ProtocolDefaults> protocolDefaultsBuilder =
                target.addService(ProtocolDefaultsService.SERVICE_NAME, new ProtocolDefaultsService())
                .setInitialMode(ServiceController.Mode.ON_DEMAND) ;
        return protocolDefaultsBuilder.install() ;
    }

    protected ServiceController<ChannelFactory> installDefaultChannelFactoryService(ServiceTarget target, String stack, ServiceVerificationHandler verificationHandler) {
        final InjectedValue<ChannelFactory> factory = new InjectedValue<ChannelFactory>();
        return target.addService(ChannelFactoryService.getServiceName(null), new ValueService<ChannelFactory>(factory))
                .addDependency(ChannelFactoryService.getServiceName(stack), ChannelFactory.class, factory)
                .setInitialMode(ServiceController.Mode.ON_DEMAND)
                .install()
        ;
    }

    @Override
    protected boolean requiresRuntimeVerification() {
        return false;
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemDescribe.java
 /*
  * JBoss, Home of Professional Open Source.
  * Copyright 2011, Red Hat, Inc., and individual contributors
  * as indicated by the @author tags. See the copyright.txt file in the
  * distribution for a full listing of individual contributors.
  *
  * This is free software; you can redistribute it and/or modify it
  * under the terms of the GNU Lesser General Public License as
  * published by the Free Software Foundation; either version 2.1 of
  * the License, or (at your option) any later version.
  *
  * This software is distributed in the hope that it will be useful,
  * but WITHOUT ANY WARRANTY; without even the implied warranty of
  * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
  * Lesser General Public License for more details.
  *
  * You should have received a copy of the GNU Lesser General Public
  * License along with this software; if not, write to the Free
  * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
  * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
  */
 package org.jboss.as.clustering.jgroups.subsystem;

 import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;

import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationDefinition;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.registry.Resource;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;
import org.jboss.dmr.Property;

 /**
  * This handler is used to generate, given a JGroups model, a list of JGroups resource commands
  * which can be used to recreate the model on another host.
  *
  * We use a custom handler as the JGroups subsystem makes non-standard use of stack operations
  * add-protocol,remove-protocol for adding and removing protocol child resources.
  *
  * NB THis was required in order to maintain ordering of protocol layers.
  *
  * @author Paul Ferraro
  * @author  Richard Achmatowicz (c) 2011 Red Hat Inc.
  */
 public class JGroupsSubsystemDescribe implements OperationStepHandler {

     public static final JGroupsSubsystemDescribe INSTANCE = new JGroupsSubsystemDescribe();

     @Override
     public void execute(OperationContext context, ModelNode operation) throws OperationFailedException {
         final ModelNode result = new ModelNode();
         final PathAddress rootAddress = PathAddress.pathAddress(PathAddress.pathAddress(operation.require(ModelDescriptionConstants.OP_ADDR)).getLastElement());
         final ModelNode subModel = Resource.Tools.readModel(context.readResource(PathAddress.EMPTY_ADDRESS));

         result.add(JGroupsSubsystemAdd.createOperation(rootAddress.toModelNode(), subModel));

         if (subModel.hasDefined(ModelKeys.STACK)) {
             for (final Property stack : subModel.get(ModelKeys.STACK).asPropertyList()) {
                 // process one stack
                 final ModelNode stackAddress = rootAddress.toModelNode();
                 stackAddress.add(ModelKeys.STACK, stack.getName());
                 result.add(ProtocolStackAdd.createOperation(stackAddress, stack.getValue()));

                 // process the child resources

                 // transport=TRANSPORT
                 if (stack.getValue().get(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME).isDefined()) {
                     ModelNode transport = stack.getValue().get(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);
                     ModelNode transportAddress = stackAddress.clone();
                     transportAddress.add(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);
                     // no optional transport:add parameters will be present, so use attributes list
                     result.add(createOperation(TransportResourceDefinition.TRANSPORT_ATTRIBUTES, transportAddress, transport));
                     addProtocolPropertyCommands(transport, transportAddress, result);
                 }
                 // protocol=*
                 if (stack.getValue().get(ModelKeys.PROTOCOL).isDefined()) {
                     for (Property protocol : ProtocolStackAdd.getOrderedProtocolPropertyList(stack.getValue())) {
                         // no optional transport:add parameters will be present, so use attributes list
                         result.add(createProtocolOperation(ProtocolResourceDefinition.PROTOCOL_ATTRIBUTES, stackAddress, protocol.getValue()));
                         ModelNode protocolAddress = stackAddress.clone();
                         protocolAddress.add(ModelKeys.PROTOCOL, protocol.getName()) ;
                         addProtocolPropertyCommands(protocol.getValue(), protocolAddress, result);
                     }
                 }
                 // relay=RELAY
                 if (stack.getValue().get(ModelKeys.RELAY, ModelKeys.RELAY_NAME).isDefined()) {
                     ModelNode relay = stack.getValue().get(ModelKeys.RELAY, ModelKeys.RELAY_NAME);
                     ModelNode relayAddress = stackAddress.clone();
                     relayAddress.add(ModelKeys.RELAY, ModelKeys.RELAY_NAME);
                     result.add(createOperation(RelayResourceDefinition.ATTRIBUTES, relayAddress, relay));
                     addProtocolPropertyCommands(relay, relayAddress, result);
                     // remote-site=*
                     if (relay.get(ModelKeys.REMOTE_SITE).isDefined()) {
                         for (final Property remoteSite : relay.get(ModelKeys.REMOTE_SITE).asPropertyList()) {
                             ModelNode remoteSiteAddress = relayAddress.clone().add(ModelKeys.REMOTE_SITE, remoteSite.getName());
                             // no optional transport:add parameters will be present, so use attributes list
                             result.add(createOperation(RemoteSiteResourceDefinition.ATTRIBUTES, remoteSiteAddress, remoteSite.getValue()));
                         }
                     }
                 }
                 // sasl=SASL
                 if (stack.getValue().get(ModelKeys.SASL, ModelKeys.SASL_NAME).isDefined()) {
                     ModelNode sasl = stack.getValue().get(ModelKeys.SASL, ModelKeys.SASL_NAME);
                     ModelNode saslAddress = stackAddress.clone();
                     saslAddress.add(ModelKeys.SASL, ModelKeys.SASL_NAME);
                     result.add(createOperation(SaslResourceDefinition.ATTRIBUTES, saslAddress, sasl));
                     addProtocolPropertyCommands(sasl, saslAddress, result);
                 }
             }
         }
         context.getResult().set(result);
         context.stepCompleted();
     }

     private void addProtocolPropertyCommands(ModelNode protocol, ModelNode address, ModelNode result) throws OperationFailedException {

         if (protocol.hasDefined(ModelKeys.PROPERTY)) {
              for (Property property : protocol.get(ModelKeys.PROPERTY).asPropertyList()) {
                  ModelNode propertyAddress = address.clone().add(ModelKeys.PROPERTY, property.getName());
                  AttributeDefinition[] ATTRIBUTE = {PropertyResourceDefinition.VALUE} ;
                  result.add(createOperation(ATTRIBUTE, propertyAddress, property.getValue()));
              }
         }
     }

     static ModelNode createOperation(AttributeDefinition[] attributes, ModelNode address, ModelNode existing) throws OperationFailedException {
         ModelNode operation = Util.getEmptyOperation(ADD, address);
         for(final AttributeDefinition attribute : attributes) {
             attribute.validateAndSet(existing, operation);
         }
         return operation;
     }

     static ModelNode createProtocolOperation(AttributeDefinition[] attributes, ModelNode address, ModelNode existing) throws OperationFailedException {
         ModelNode operation = Util.getEmptyOperation(ModelKeys.ADD_PROTOCOL, address);
         for(final AttributeDefinition attribute : attributes) {
             attribute.validateAndSet(existing, operation);
         }
         return operation;
     }


     /*
      * Description provider for the subsystem describe handler
      */
     static OperationDefinition DEFINITION = new SimpleOperationDefinitionBuilder(ModelDescriptionConstants.DESCRIBE,null)
             .setPrivateEntry()
             .setReplyType(ModelType.LIST)
             .setReplyValueType(ModelType.OBJECT)
             .build();

 }


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemRemove.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.REMOVE;

import java.util.List;

import org.jboss.as.controller.AbstractRemoveStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;
import org.jboss.msc.service.ServiceName;

/**
 * Handler for JGroups subsystem add operations.
 *
 * @author Kabir Khan
 */
public class JGroupsSubsystemRemove extends AbstractRemoveStepHandler {

    public static final JGroupsSubsystemRemove INSTANCE = new JGroupsSubsystemRemove();

    @Override
    protected void performRemove(OperationContext context, ModelNode operation, ModelNode model) throws OperationFailedException {
        final PathAddress opAddress = PathAddress.pathAddress(operation.require(OP_ADDR));
        // Add a step *on the top of the stack* to actually remove the subsystem resource
        ModelNode removeSubsystem = Util.createOperation(REMOVE, opAddress);
        context.addStep(removeSubsystem, new OriginalSubsystemRemoveHandler(), OperationContext.Stage.MODEL, true);

        // Now add steps on top of the one added above to remove any existing child stacks
        if (model.hasDefined(ModelKeys.STACK)) {
            List<Property> stacks = model.get(ModelKeys.STACK).asPropertyList() ;
            for (Property stack: stacks) {
                PathAddress address = opAddress.append(ModelKeys.STACK, stack.getName());
                ModelNode removeStack = Util.createOperation(REMOVE, address);
                // remove the stack
                context.addStep(removeStack, ProtocolStackRemove.INSTANCE, OperationContext.Stage.MODEL, true);
            }
        }

        context.stepCompleted();
    }

    static class OriginalSubsystemRemoveHandler extends AbstractRemoveStepHandler {

        @Override
        protected void performRuntime(OperationContext context, ModelNode operation, ModelNode model)
            throws OperationFailedException {
            removeRuntimeServices(context, operation, model);
        }

        protected void removeRuntimeServices(OperationContext context, ModelNode operation, ModelNode model)
                throws OperationFailedException {

            // remove the ProtocolDefaultsService
            ServiceName protocolDefaultsService = ProtocolDefaultsService.SERVICE_NAME;
            context.removeService(protocolDefaultsService);

            // remove the DefaultChannelFactoryServiceAlias
            ServiceName defaultChannelFactoryService = ChannelFactoryService.getServiceName(null);
            context.removeService(defaultChannelFactoryService);
        }
    }

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemRootResource.java
package org.jboss.as.clustering.jgroups.subsystem;

import org.jboss.as.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.controller.SimpleAttributeDefinition;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.dmr.ModelType;

/**
 * The root resource of the JGroups subsystem.
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class JGroupsSubsystemRootResource extends SimpleResourceDefinition {

    // attributes
    static SimpleAttributeDefinition DEFAULT_STACK =
            new SimpleAttributeDefinitionBuilder(ModelKeys.DEFAULT_STACK, ModelType.STRING, false)
                    .setXmlName(Attribute.DEFAULT_STACK.getLocalName())
                    .setAllowExpression(true)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    // registration
    JGroupsSubsystemRootResource() {
        super(JGroupsExtension.SUBSYSTEM_PATH,
                JGroupsExtension.getResourceDescriptionResolver(),
                JGroupsSubsystemAdd.INSTANCE,
                JGroupsSubsystemRemove.INSTANCE);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration resourceRegistration) {
        super.registerOperations(resourceRegistration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration resourceRegistration) {
        super.registerAttributes(resourceRegistration);
        resourceRegistration.registerReadWriteAttribute(DEFAULT_STACK, null, new ReloadRequiredWriteAttributeHandler(DEFAULT_STACK));
    }

    @Override
    public void registerChildren(ManagementResourceRegistration resourceRegistration) {
        super.registerChildren(resourceRegistration);
    }

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemXMLReader_1_0.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SUBSYSTEM;

import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.List;

import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamException;

import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.parsing.ParseUtils;
import org.jboss.dmr.ModelNode;
import org.jboss.staxmapper.XMLElementReader;
import org.jboss.staxmapper.XMLExtendedStreamReader;
import org.jgroups.protocols.TP;
import org.jgroups.stack.Protocol;

/**
 * @author Paul Ferraro
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Tristan Tarrant
 */
public class JGroupsSubsystemXMLReader_1_0 implements XMLElementReader<List<ModelNode>> {
    /**
     * {@inheritDoc}
     * @see org.jboss.staxmapper.XMLElementReader#readElement(org.jboss.staxmapper.XMLExtendedStreamReader, java.lang.Object)
     */
    @Override
    public void readElement(XMLExtendedStreamReader reader, List<ModelNode> operations) throws XMLStreamException {

        ModelNode subsystemAddress = new ModelNode();
        subsystemAddress.add(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME);
        subsystemAddress.protect();
        ModelNode subsystem = Util.getEmptyOperation(ADD, subsystemAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            ParseUtils.requireNoNamespaceAttribute(reader, i);
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case DEFAULT_STACK: {
                    JGroupsSubsystemRootResource.DEFAULT_STACK.parseAndSetParameter(value, subsystem, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!subsystem.hasDefined(ModelKeys.DEFAULT_STACK)) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.DEFAULT_STACK));
        }

        operations.add(subsystem);

        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            switch (Namespace.forUri(reader.getNamespaceURI())) {
                case JGROUPS_1_0: {
                    Element element = Element.forName(reader.getLocalName());
                    switch (element) {
                        case STACK: {
                            this.parseStack(reader, subsystemAddress, operations);
                            break;
                        }
                        default: {
                            throw ParseUtils.unexpectedElement(reader);
                        }
                    }
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseStack(XMLExtendedStreamReader reader, ModelNode subsystemAddress, List<ModelNode> operations) throws XMLStreamException {

        final ModelNode stack = Util.getEmptyOperation(ModelDescriptionConstants.ADD, null);
        List<ModelNode> additionalConfigurationOperations = new ArrayList<ModelNode>();

        String name = null;
        for (int i = 0; i < reader.getAttributeCount(); i++) {
            ParseUtils.requireNoNamespaceAttribute(reader, i);
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    name = value;
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (name == null) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.NAME));
        }

        ModelNode stackAddress = subsystemAddress.clone();
        stackAddress.add(ModelKeys.STACK, name);
        stackAddress.protect();
        stack.get(OP_ADDR).set(stackAddress);

        if (!reader.hasNext() || (reader.nextTag() == XMLStreamConstants.END_ELEMENT) || Element.forName(reader.getLocalName()) != Element.TRANSPORT) {
            throw ParseUtils.missingRequiredElement(reader, Collections.singleton(Element.TRANSPORT));
        }

        this.parseTransport(reader, stackAddress, additionalConfigurationOperations);

        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROTOCOL: {
                    this.parseProtocol(reader, stackAddress, additionalConfigurationOperations);
                     break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }

        operations.add(stack);
        // add operations to create configuration resources
        for (ModelNode additionalOperation : additionalConfigurationOperations) {
            operations.add(additionalOperation);
        }
    }

    private void parseTransport(XMLExtendedStreamReader reader, ModelNode stackAddress, List<ModelNode> operations) throws XMLStreamException {

        // ModelNode for the cache add operation
        ModelNode transportAddress = stackAddress.clone();
        transportAddress.add(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);
        transportAddress.protect();
        ModelNode transport = Util.getEmptyOperation(ModelDescriptionConstants.ADD, transportAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case TYPE: {
                    try {
                        TP.class.getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + value).asSubclass(TP.class).newInstance();
                        TransportResourceDefinition.TYPE.parseAndSetParameter(value, transport, reader);
                    } catch (Exception e) {
                        throw ParseUtils.invalidAttributeValue(reader, i);
                    }
                    break;
                }
                case SHARED: {
                    TransportResourceDefinition.SHARED.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case SOCKET_BINDING: {
                    TransportResourceDefinition.SOCKET_BINDING.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case DIAGNOSTICS_SOCKET_BINDING: {
                    TransportResourceDefinition.DIAGNOSTICS_SOCKET_BINDING.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case DEFAULT_EXECUTOR: {
                    TransportResourceDefinition.DEFAULT_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case OOB_EXECUTOR: {
                    TransportResourceDefinition.OOB_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case TIMER_EXECUTOR: {
                    TransportResourceDefinition.TIMER_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case THREAD_FACTORY: {
                    TransportResourceDefinition.THREAD_FACTORY.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case SITE: {
                    TransportResourceDefinition.SITE.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case RACK: {
                    TransportResourceDefinition.RACK.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case MACHINE: {
                    TransportResourceDefinition.MACHINE.parseAndSetParameter(value, transport, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!transport.hasDefined(ModelKeys.TYPE)) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.TYPE));
        }

        List<ModelNode> propertyOperations = new ArrayList<ModelNode>();
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROPERTY: {
                    this.parseProperty(reader, transportAddress, propertyOperations);
                     break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
        operations.add(transport);
        // add operations to create associated properties
        for (ModelNode propertyOperation : propertyOperations) {
            operations.add(propertyOperation);
        }
    }


    private void parseProtocol(XMLExtendedStreamReader reader, ModelNode stackAddress, List<ModelNode> operations) throws XMLStreamException {

        ModelNode protocol = Util.getEmptyOperation(ModelKeys.ADD_PROTOCOL, null);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case TYPE: {
                    try {
                        Protocol.class.getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + value).asSubclass(Protocol.class).newInstance();
                        ProtocolResourceDefinition.TYPE.parseAndSetParameter(value, protocol, reader);
                    } catch (Exception e) {
                        throw ParseUtils.invalidAttributeValue(reader, i);
                    }
                    break;
                }
                case SOCKET_BINDING: {
                    ProtocolResourceDefinition.SOCKET_BINDING.parseAndSetParameter(value, protocol, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!protocol.hasDefined(ModelKeys.TYPE)) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.TYPE));
        }

        protocol.get(OP_ADDR).set(stackAddress);

        // in order to add any property, we need the protocol address which will be generated
        ModelNode protocolAddress = stackAddress.clone() ;
        protocolAddress.add(ModelKeys.PROTOCOL, protocol.get(ModelKeys.TYPE).asString());

        List<ModelNode> propertyOperations = new ArrayList<ModelNode>();
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROPERTY: {
                    this.parseProperty(reader, protocolAddress, propertyOperations);
                     break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
        operations.add(protocol);
        // add operations to create associated properties
        for (ModelNode propertyOperation : propertyOperations) {
            operations.add(propertyOperation);
        }
    }

    private void parseProperty(XMLExtendedStreamReader reader, ModelNode transportOrProtocolAddress, List<ModelNode> operations) throws XMLStreamException {

        ModelNode property = Util.getEmptyOperation(ModelDescriptionConstants.ADD, null);

        String propertyName = null;
        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    propertyName = value;
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }
        if (property == null) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.NAME));
        }
        String propertyValue = reader.getElementText();

        // ModelNode for the property add operation
        ModelNode propertyAddress = transportOrProtocolAddress.clone();
        propertyAddress.add(ModelKeys.PROPERTY, propertyName);
        propertyAddress.protect();
        property.get(OP_ADDR).set(propertyAddress);

        // assign the value
        PropertyResourceDefinition.VALUE.parseAndSetParameter(propertyValue, property, reader);

        operations.add(property);
    }

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemXMLReader_1_1.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;

import java.util.Collections;
import java.util.EnumSet;
import java.util.List;

import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamException;

import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.parsing.ParseUtils;
import org.jboss.dmr.ModelNode;
import org.jboss.staxmapper.XMLElementReader;
import org.jboss.staxmapper.XMLExtendedStreamReader;
import org.jgroups.protocols.TP;
import org.jgroups.stack.Protocol;

/**
 * @author Paul Ferraro
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Tristan Tarrant
 */
public class JGroupsSubsystemXMLReader_1_1 implements XMLElementReader<List<ModelNode>> {
    /**
     * {@inheritDoc}
     * @see org.jboss.staxmapper.XMLElementReader#readElement(org.jboss.staxmapper.XMLExtendedStreamReader, java.lang.Object)
     */
    @Override
    public void readElement(XMLExtendedStreamReader reader, List<ModelNode> operations) throws XMLStreamException {

        PathAddress subsystemAddress = PathAddress.pathAddress(JGroupsExtension.SUBSYSTEM_PATH);
        ModelNode subsystem = Util.createAddOperation(subsystemAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            ParseUtils.requireNoNamespaceAttribute(reader, i);
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case DEFAULT_STACK: {
                    JGroupsSubsystemRootResource.DEFAULT_STACK.parseAndSetParameter(value, subsystem, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!subsystem.hasDefined(ModelKeys.DEFAULT_STACK)) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.DEFAULT_STACK));
        }

        operations.add(subsystem);

        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            switch (Namespace.forUri(reader.getNamespaceURI())) {
                case JGROUPS_1_1: {
                    Element element = Element.forName(reader.getLocalName());
                    switch (element) {
                        case STACK: {
                            this.parseStack(reader, subsystemAddress, operations);
                            break;
                        }
                        default: {
                            throw ParseUtils.unexpectedElement(reader);
                        }
                    }
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseStack(XMLExtendedStreamReader reader, PathAddress subsystemAddress, List<ModelNode> operations) throws XMLStreamException {
        String name = null;
        for (int i = 0; i < reader.getAttributeCount(); i++) {
            ParseUtils.requireNoNamespaceAttribute(reader, i);
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    name = value;
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (name == null) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.NAME));
        }
        PathAddress stackAddress = subsystemAddress.append(PathElement.pathElement(ModelKeys.STACK, name));
        final ModelNode stack = Util.createAddOperation(stackAddress);
        stack.get(OP_ADDR).set(stackAddress.toModelNode());

        if (!reader.hasNext() || (reader.nextTag() == XMLStreamConstants.END_ELEMENT) || Element.forName(reader.getLocalName()) != Element.TRANSPORT) {
            throw ParseUtils.missingRequiredElement(reader, Collections.singleton(Element.TRANSPORT));
        }
        operations.add(stack);
        this.parseTransport(reader, stackAddress, operations);

        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROTOCOL: {
                    this.parseProtocol(reader, stackAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseTransport(XMLExtendedStreamReader reader, final PathAddress stackAddress, List<ModelNode> operations) throws XMLStreamException {

        // ModelNode for the cache add operation
        PathAddress transportAddress = stackAddress.append(PathElement.pathElement(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME));
        ModelNode transport = Util.createAddOperation(transportAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case TYPE: {
                    try {
                        TP.class.getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + value).asSubclass(TP.class).newInstance();
                        TransportResourceDefinition.TYPE.parseAndSetParameter(value, transport, reader);
                    } catch (Exception e) {
                        throw ParseUtils.invalidAttributeValue(reader, i);
                    }
                    break;
                }
                case SHARED: {
                    TransportResourceDefinition.SHARED.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case SOCKET_BINDING: {
                    TransportResourceDefinition.SOCKET_BINDING.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case DIAGNOSTICS_SOCKET_BINDING: {
                    TransportResourceDefinition.DIAGNOSTICS_SOCKET_BINDING.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case DEFAULT_EXECUTOR: {
                    TransportResourceDefinition.DEFAULT_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case OOB_EXECUTOR: {
                    TransportResourceDefinition.OOB_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case TIMER_EXECUTOR: {
                    TransportResourceDefinition.TIMER_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case THREAD_FACTORY: {
                    TransportResourceDefinition.THREAD_FACTORY.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case SITE: {
                    TransportResourceDefinition.SITE.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case RACK: {
                    TransportResourceDefinition.RACK.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case MACHINE: {
                    TransportResourceDefinition.MACHINE.parseAndSetParameter(value, transport, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!transport.hasDefined(ModelKeys.TYPE)) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.TYPE));
        }
        operations.add(transport);
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROPERTY: {
                    this.parseProperty(reader, transportAddress, operations);
                     break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }

    }

    private void parseProtocol(XMLExtendedStreamReader reader, PathAddress stackAddress, final List<ModelNode> operations) throws XMLStreamException {

        ModelNode protocol = Util.createOperation(ModelKeys.ADD_PROTOCOL, stackAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case TYPE: {
                    try {
                        Protocol.class.getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + value).asSubclass(Protocol.class).newInstance();
                        ProtocolResourceDefinition.TYPE.parseAndSetParameter(value, protocol, reader);
                    } catch (Exception e) {
                        throw ParseUtils.invalidAttributeValue(reader, i);
                    }
                    break;
                }
                case SOCKET_BINDING: {
                    ProtocolResourceDefinition.SOCKET_BINDING.parseAndSetParameter(value, protocol, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!protocol.hasDefined(ModelKeys.TYPE)) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.TYPE));
        }

        // in order to add any property, we need the protocol address which will be generated
        PathAddress protocolAddress = stackAddress.append(PathElement.pathElement(ModelKeys.PROTOCOL, protocol.get(ModelKeys.TYPE).asString()));

        operations.add(protocol);
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROPERTY: {
                    this.parseProperty(reader, protocolAddress, operations);
                     break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseProperty(final XMLExtendedStreamReader reader, final PathAddress transportOrProtocolAddress, final List<ModelNode> operations) throws XMLStreamException {
        String propertyName = null;
        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    propertyName = value;
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }
        if (propertyName == null) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.NAME));
        }
        String propertyValue = reader.getElementText();

        // ModelNode for the property add operation
        PathAddress propertyAddress = transportOrProtocolAddress.append(PathElement.pathElement(ModelKeys.PROPERTY, propertyName));
        ModelNode property = Util.createAddOperation(propertyAddress);

        // assign the value
        PropertyResourceDefinition.VALUE.parseAndSetParameter(propertyValue, property, reader);

        operations.add(property);
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemXMLReader_1_2.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;

import java.util.Collections;
import java.util.EnumSet;
import java.util.List;

import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamException;

import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.parsing.ParseUtils;
import org.jboss.dmr.ModelNode;
import org.jboss.staxmapper.XMLElementReader;
import org.jboss.staxmapper.XMLExtendedStreamReader;
import org.jgroups.protocols.TP;
import org.jgroups.stack.Protocol;

/**
 * @author Paul Ferraro
 */
public class JGroupsSubsystemXMLReader_1_2 implements XMLElementReader<List<ModelNode>> {
    /**
     * {@inheritDoc}
     * @see org.jboss.staxmapper.XMLElementReader#readElement(org.jboss.staxmapper.XMLExtendedStreamReader, java.lang.Object)
     */
    @Override
    public void readElement(XMLExtendedStreamReader reader, List<ModelNode> operations) throws XMLStreamException {

        PathAddress subsystemAddress = PathAddress.pathAddress(JGroupsExtension.SUBSYSTEM_PATH);
        ModelNode subsystem = Util.createAddOperation(subsystemAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            ParseUtils.requireNoNamespaceAttribute(reader, i);
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case DEFAULT_STACK: {
                    JGroupsSubsystemRootResource.DEFAULT_STACK.parseAndSetParameter(value, subsystem, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!subsystem.hasDefined(ModelKeys.DEFAULT_STACK)) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.DEFAULT_STACK));
        }

        operations.add(subsystem);

        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case STACK: {
                    this.parseStack(reader, subsystemAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseStack(XMLExtendedStreamReader reader, PathAddress subsystemAddress, List<ModelNode> operations) throws XMLStreamException {
        String name = null;
        for (int i = 0; i < reader.getAttributeCount(); i++) {
            ParseUtils.requireNoNamespaceAttribute(reader, i);
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    name = value;
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (name == null) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.NAME));
        }
        PathAddress stackAddress = subsystemAddress.append(PathElement.pathElement(ModelKeys.STACK, name));
        final ModelNode stack = Util.createAddOperation(stackAddress);

        if (!reader.hasNext() || (reader.nextTag() == XMLStreamConstants.END_ELEMENT) || Element.forName(reader.getLocalName()) != Element.TRANSPORT) {
            throw ParseUtils.missingRequiredElement(reader, Collections.singleton(Element.TRANSPORT));
        }
        operations.add(stack);
        this.parseTransport(reader, stackAddress, operations);

        boolean hasRelay = false;
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROTOCOL: {
                    if (!hasRelay) {
                        this.parseProtocol(reader, stackAddress, operations);
                    } else {
                        throw ParseUtils.unexpectedElement(reader);
                    }
                    break;
                }
                case RELAY: {
                    if (!hasRelay) {
                        this.parseRelay(reader, stackAddress, operations);
                        hasRelay = true;
                    } else {
                        throw ParseUtils.unexpectedElement(reader);
                    }
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseTransport(XMLExtendedStreamReader reader, final PathAddress stackAddress, List<ModelNode> operations) throws XMLStreamException {

        PathAddress transportAddress = stackAddress.append(PathElement.pathElement(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME));
        ModelNode transport = Util.createAddOperation(transportAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case TYPE: {
                    try {
                        TP.class.getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + value).asSubclass(TP.class).newInstance();
                        TransportResourceDefinition.TYPE.parseAndSetParameter(value, transport, reader);
                    } catch (Exception e) {
                        throw ParseUtils.invalidAttributeValue(reader, i);
                    }
                    break;
                }
                case SHARED: {
                    TransportResourceDefinition.SHARED.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case SOCKET_BINDING: {
                    TransportResourceDefinition.SOCKET_BINDING.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case DIAGNOSTICS_SOCKET_BINDING: {
                    TransportResourceDefinition.DIAGNOSTICS_SOCKET_BINDING.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case DEFAULT_EXECUTOR: {
                    TransportResourceDefinition.DEFAULT_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case OOB_EXECUTOR: {
                    TransportResourceDefinition.OOB_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case TIMER_EXECUTOR: {
                    TransportResourceDefinition.TIMER_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case THREAD_FACTORY: {
                    TransportResourceDefinition.THREAD_FACTORY.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case SITE: {
                    TransportResourceDefinition.SITE.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case RACK: {
                    TransportResourceDefinition.RACK.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case MACHINE: {
                    TransportResourceDefinition.MACHINE.parseAndSetParameter(value, transport, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!transport.hasDefined(ModelKeys.TYPE)) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.TYPE));
        }
        operations.add(transport);
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROPERTY: {
                    this.parseProperty(reader, transportAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseProtocol(XMLExtendedStreamReader reader, PathAddress stackAddress, final List<ModelNode> operations) throws XMLStreamException {

        ModelNode protocol = Util.createOperation(ModelKeys.ADD_PROTOCOL, stackAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case TYPE: {
                    try {
                        Protocol.class.getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + value).asSubclass(Protocol.class).newInstance();
                        ProtocolResourceDefinition.TYPE.parseAndSetParameter(value, protocol, reader);
                    } catch (Exception e) {
                        throw ParseUtils.invalidAttributeValue(reader, i);
                    }
                    break;
                }
                case SOCKET_BINDING: {
                    ProtocolResourceDefinition.SOCKET_BINDING.parseAndSetParameter(value, protocol, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!protocol.hasDefined(ModelKeys.TYPE)) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.TYPE));
        }

        // in order to add any property, we need the protocol address which will be generated
        PathAddress protocolAddress = stackAddress.append(PathElement.pathElement(ModelKeys.PROTOCOL, protocol.get(ModelKeys.TYPE).asString()));

        operations.add(protocol);
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROPERTY: {
                    this.parseProperty(reader, protocolAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseProperty(final XMLExtendedStreamReader reader, final PathAddress address, final List<ModelNode> operations) throws XMLStreamException {
        String propertyName = null;
        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    propertyName = value;
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }
        if (propertyName == null) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.NAME));
        }
        String propertyValue = reader.getElementText();

        // ModelNode for the property add operation
        PathAddress propertyAddress = address.append(PathElement.pathElement(ModelKeys.PROPERTY, propertyName));
        ModelNode property = Util.createAddOperation(propertyAddress);

        // assign the value
        PropertyResourceDefinition.VALUE.parseAndSetParameter(propertyValue, property, reader);

        operations.add(property);
    }

    private void parseRelay(XMLExtendedStreamReader reader, final PathAddress stackAddress, List<ModelNode> operations) throws XMLStreamException {
        PathAddress relayAddress = stackAddress.append(PathElement.pathElement(ModelKeys.RELAY, ModelKeys.RELAY_NAME));
        ModelNode operation = Util.createAddOperation(relayAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case SITE: {
                    RelayResourceDefinition.SITE.parseAndSetParameter(value, operation, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!operation.hasDefined(ModelKeys.SITE)) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.SITE));
        }
        operations.add(operation);

        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case REMOTE_SITE: {
                    this.parseRemoteSite(reader, relayAddress, operations);
                    break;
                }
                case PROPERTY: {
                    this.parseProperty(reader, relayAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseRemoteSite(XMLExtendedStreamReader reader, final PathAddress relayAddress, List<ModelNode> operations) throws XMLStreamException {
        String site = null;
        ModelNode operation = Util.createAddOperation();

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    site = value;
                    break;
                }
                case STACK: {
                    RemoteSiteResourceDefinition.STACK.parseAndSetParameter(value, operation, reader);
                    break;
                }
                case CLUSTER: {
                    RemoteSiteResourceDefinition.CLUSTER.parseAndSetParameter(value, operation, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (site == null) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.NAME));
        }

        ParseUtils.requireNoContent(reader);

        PathAddress siteAddress = relayAddress.append(PathElement.pathElement(ModelKeys.REMOTE_SITE, site));
        operation.get(OP_ADDR).set(siteAddress.toModelNode());

        operations.add(operation);
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemXMLReader_7_0.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;

import java.util.Collections;
import java.util.EnumSet;
import java.util.List;

import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamException;

import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.parsing.ParseUtils;
import org.jboss.dmr.ModelNode;
import org.jboss.staxmapper.XMLElementReader;
import org.jboss.staxmapper.XMLExtendedStreamReader;
import org.jgroups.protocols.TP;
import org.jgroups.stack.Protocol;

/**
 * @author Paul Ferraro
 */
public class JGroupsSubsystemXMLReader_7_0 implements XMLElementReader<List<ModelNode>> {
    /**
     * {@inheritDoc}
     * @see org.jboss.staxmapper.XMLElementReader#readElement(org.jboss.staxmapper.XMLExtendedStreamReader, java.lang.Object)
     */
    @Override
    public void readElement(XMLExtendedStreamReader reader, List<ModelNode> operations) throws XMLStreamException {

        PathAddress subsystemAddress = PathAddress.pathAddress(JGroupsExtension.SUBSYSTEM_PATH);
        ModelNode subsystem = Util.createAddOperation(subsystemAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            ParseUtils.requireNoNamespaceAttribute(reader, i);
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case DEFAULT_STACK: {
                    JGroupsSubsystemRootResource.DEFAULT_STACK.parseAndSetParameter(value, subsystem, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!subsystem.hasDefined(ModelKeys.DEFAULT_STACK)) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.DEFAULT_STACK));
        }

        operations.add(subsystem);

        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case STACK: {
                    this.parseStack(reader, subsystemAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseStack(XMLExtendedStreamReader reader, PathAddress subsystemAddress, List<ModelNode> operations) throws XMLStreamException {
        String name = null;
        for (int i = 0; i < reader.getAttributeCount(); i++) {
            ParseUtils.requireNoNamespaceAttribute(reader, i);
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    name = value;
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (name == null) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.NAME));
        }
        PathAddress stackAddress = subsystemAddress.append(PathElement.pathElement(ModelKeys.STACK, name));
        final ModelNode stack = Util.createAddOperation(stackAddress);

        if (!reader.hasNext() || (reader.nextTag() == XMLStreamConstants.END_ELEMENT) || Element.forName(reader.getLocalName()) != Element.TRANSPORT) {
            throw ParseUtils.missingRequiredElement(reader, Collections.singleton(Element.TRANSPORT));
        }
        operations.add(stack);
        this.parseTransport(reader, stackAddress, operations);

        boolean hasRelay = false;
        boolean hasSasl = false;
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROTOCOL: {
                    if (!hasRelay) {
                        this.parseProtocol(reader, stackAddress, operations);
                    } else {
                        throw ParseUtils.unexpectedElement(reader);
                    }
                    break;
                }
                case RELAY: {
                    if (!hasRelay) {
                        this.parseRelay(reader, stackAddress, operations);
                        hasRelay = true;
                    } else {
                        throw ParseUtils.unexpectedElement(reader);
                    }
                    break;
                }
                case SASL: {
                    if (!hasSasl) {
                        this.parseSasl(reader, stackAddress, operations);
                        hasSasl = true;
                    } else {
                       throw ParseUtils.unexpectedElement(reader);
                    }
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseTransport(XMLExtendedStreamReader reader, final PathAddress stackAddress, List<ModelNode> operations) throws XMLStreamException {

        PathAddress transportAddress = stackAddress.append(PathElement.pathElement(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME));
        ModelNode transport = Util.createAddOperation(transportAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case TYPE: {
                    try {
                        TP.class.getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + value).asSubclass(TP.class).newInstance();
                        TransportResourceDefinition.TYPE.parseAndSetParameter(value, transport, reader);
                    } catch (Exception e) {
                        throw ParseUtils.invalidAttributeValue(reader, i);
                    }
                    break;
                }
                case SHARED: {
                    TransportResourceDefinition.SHARED.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case SOCKET_BINDING: {
                    TransportResourceDefinition.SOCKET_BINDING.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case DIAGNOSTICS_SOCKET_BINDING: {
                    TransportResourceDefinition.DIAGNOSTICS_SOCKET_BINDING.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case DEFAULT_EXECUTOR: {
                    TransportResourceDefinition.DEFAULT_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case OOB_EXECUTOR: {
                    TransportResourceDefinition.OOB_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case TIMER_EXECUTOR: {
                    TransportResourceDefinition.TIMER_EXECUTOR.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case THREAD_FACTORY: {
                    TransportResourceDefinition.THREAD_FACTORY.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case SITE: {
                    TransportResourceDefinition.SITE.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case RACK: {
                    TransportResourceDefinition.RACK.parseAndSetParameter(value, transport, reader);
                    break;
                }
                case MACHINE: {
                    TransportResourceDefinition.MACHINE.parseAndSetParameter(value, transport, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!transport.hasDefined(ModelKeys.TYPE)) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.TYPE));
        }
        operations.add(transport);
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROPERTY: {
                    this.parseProperty(reader, transportAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseProtocol(XMLExtendedStreamReader reader, PathAddress stackAddress, final List<ModelNode> operations) throws XMLStreamException {

        ModelNode protocol = Util.createOperation(ModelKeys.ADD_PROTOCOL, stackAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case TYPE: {
                    try {
                        Protocol.class.getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + value).asSubclass(Protocol.class).newInstance();
                        ProtocolResourceDefinition.TYPE.parseAndSetParameter(value, protocol, reader);
                    } catch (Exception e) {
                        throw ParseUtils.invalidAttributeValue(reader, i);
                    }
                    break;
                }
                case SOCKET_BINDING: {
                    ProtocolResourceDefinition.SOCKET_BINDING.parseAndSetParameter(value, protocol, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!protocol.hasDefined(ModelKeys.TYPE)) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.TYPE));
        }

        // in order to add any property, we need the protocol address which will be generated
        PathAddress protocolAddress = stackAddress.append(PathElement.pathElement(ModelKeys.PROTOCOL, protocol.get(ModelKeys.TYPE).asString()));

        operations.add(protocol);
        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case PROPERTY: {
                    this.parseProperty(reader, protocolAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseProperty(final XMLExtendedStreamReader reader, final PathAddress address, final List<ModelNode> operations) throws XMLStreamException {
        String propertyName = null;
        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    propertyName = value;
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }
        if (propertyName == null) {
            throw ParseUtils.missingRequired(reader, Collections.singleton(Attribute.NAME));
        }
        String propertyValue = reader.getElementText();

        // ModelNode for the property add operation
        PathAddress propertyAddress = address.append(PathElement.pathElement(ModelKeys.PROPERTY, propertyName));
        ModelNode property = Util.createAddOperation(propertyAddress);

        // assign the value
        PropertyResourceDefinition.VALUE.parseAndSetParameter(propertyValue, property, reader);

        operations.add(property);
    }

    private void parseRelay(XMLExtendedStreamReader reader, final PathAddress stackAddress, List<ModelNode> operations) throws XMLStreamException {
        PathAddress relayAddress = stackAddress.append(PathElement.pathElement(ModelKeys.RELAY, ModelKeys.RELAY_NAME));
        ModelNode operation = Util.createAddOperation(relayAddress);

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case SITE: {
                    RelayResourceDefinition.SITE.parseAndSetParameter(value, operation, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (!operation.hasDefined(ModelKeys.SITE)) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.SITE));
        }
        operations.add(operation);

        while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
            Element element = Element.forName(reader.getLocalName());
            switch (element) {
                case REMOTE_SITE: {
                    this.parseRemoteSite(reader, relayAddress, operations);
                    break;
                }
                case PROPERTY: {
                    this.parseProperty(reader, relayAddress, operations);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedElement(reader);
                }
            }
        }
    }

    private void parseRemoteSite(XMLExtendedStreamReader reader, final PathAddress relayAddress, List<ModelNode> operations) throws XMLStreamException {
        String site = null;
        ModelNode operation = Util.createAddOperation();

        for (int i = 0; i < reader.getAttributeCount(); i++) {
            String value = reader.getAttributeValue(i);
            Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
            switch (attribute) {
                case NAME: {
                    site = value;
                    break;
                }
                case STACK: {
                    RemoteSiteResourceDefinition.STACK.parseAndSetParameter(value, operation, reader);
                    break;
                }
                case CLUSTER: {
                    RemoteSiteResourceDefinition.CLUSTER.parseAndSetParameter(value, operation, reader);
                    break;
                }
                default: {
                    throw ParseUtils.unexpectedAttribute(reader, i);
                }
            }
        }

        if (site == null) {
            throw ParseUtils.missingRequired(reader, EnumSet.of(Attribute.NAME));
        }

        ParseUtils.requireNoContent(reader);

        PathAddress siteAddress = relayAddress.append(PathElement.pathElement(ModelKeys.REMOTE_SITE, site));
        operation.get(OP_ADDR).set(siteAddress.toModelNode());

        operations.add(operation);
    }

    private void parseSasl(XMLExtendedStreamReader reader, final PathAddress stackAddress, List<ModelNode> operations) throws XMLStreamException {
       PathAddress saslAddress = stackAddress.append(PathElement.pathElement(ModelKeys.SASL, ModelKeys.SASL_NAME));
       ModelNode operation = Util.createAddOperation(saslAddress);

       EnumSet<Attribute> required = EnumSet.of(Attribute.MECH, Attribute.SECURITY_REALM);
       for (int i = 0; i < reader.getAttributeCount(); i++) {
           String value = reader.getAttributeValue(i);
           Attribute attribute = Attribute.forName(reader.getAttributeLocalName(i));
           required.remove(attribute);
           switch (attribute) {
               case CLUSTER_ROLE: {
                   SaslResourceDefinition.CLUSTER_ROLE.parseAndSetParameter(value, operation, reader);
                   break;
               }
               case MECH: {
                   SaslResourceDefinition.MECH.parseAndSetParameter(value, operation, reader);
                   break;
               }
               case SECURITY_REALM: {
                   SaslResourceDefinition.SECURITY_REALM.parseAndSetParameter(value, operation, reader);
                   break;
               }
               default: {
                   throw ParseUtils.unexpectedAttribute(reader, i);
               }
           }
       }

       if (!required.isEmpty()) {
           throw ParseUtils.missingRequired(reader, required);
       }
       operations.add(operation);

       while (reader.hasNext() && (reader.nextTag() != XMLStreamConstants.END_ELEMENT)) {
           Element element = Element.forName(reader.getLocalName());
           switch (element) {
               case PROPERTY: {
                   this.parseProperty(reader, saslAddress, operations);
                   break;
               }
               default: {
                   throw ParseUtils.unexpectedElement(reader);
               }
           }
       }
   }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemXMLWriter.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.jgroups.subsystem;

import javax.xml.stream.XMLStreamException;

import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.SimpleAttributeDefinition;
import org.jboss.as.controller.persistence.SubsystemMarshallingContext;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;
import org.jboss.staxmapper.XMLElementWriter;
import org.jboss.staxmapper.XMLExtendedStreamWriter;

/**
 * @author Paul Ferraro
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Tristan Tarrant
 */
public class JGroupsSubsystemXMLWriter implements XMLElementWriter<SubsystemMarshallingContext> {
    /**
     * {@inheritDoc}
     * @see org.jboss.staxmapper.XMLElementWriter#writeContent(org.jboss.staxmapper.XMLExtendedStreamWriter, java.lang.Object)
     */
    @Override
    public void writeContent(XMLExtendedStreamWriter writer, SubsystemMarshallingContext context) throws XMLStreamException {
        context.startSubsystemElement(Namespace.CURRENT.getUri(), false);
        ModelNode model = context.getModelNode();

        if (model.isDefined()) {
            this.writeOptional(writer, Attribute.DEFAULT_STACK, model, ModelKeys.DEFAULT_STACK);
            // each property represents a stack
            for (Property property: model.get(ModelKeys.STACK).asPropertyList()) {
                writer.writeStartElement(Element.STACK.getLocalName());
                writer.writeAttribute(Attribute.NAME.getLocalName(), property.getName());
                ModelNode stack = property.getValue();
                // write the transport
                if (stack.hasDefined(ModelKeys.TRANSPORT)) {
                    ModelNode transport = stack.get(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);
                    this.writeProtocol(writer, transport, Element.TRANSPORT);
                }
                // write the protocols in their correct order
                if (stack.hasDefined(ModelKeys.PROTOCOL)) {
//                  for (Property protocol: stack.get(ModelKeys.PROTOCOL).asPropertyList()) {
                    for (Property protocol: ProtocolStackAdd.getOrderedProtocolPropertyList(stack)) {
                        this.writeProtocol(writer, protocol.getValue(), Element.PROTOCOL);
                    }
                }
                if (stack.hasDefined(ModelKeys.RELAY)) {
                    ModelNode relay = stack.get(ModelKeys.RELAY, ModelKeys.RELAY_NAME);
                    this.writeRelay(writer, relay, Element.RELAY);
                }
                if (stack.hasDefined(ModelKeys.SASL)) {
                   ModelNode sasl = stack.get(ModelKeys.SASL, ModelKeys.SASL_NAME);
                   this.writeSasl(writer, sasl, Element.SASL);
               }
                writer.writeEndElement();
            }
        }
        writer.writeEndElement();
    }

    private void writeProtocol(XMLExtendedStreamWriter writer, ModelNode protocol, Element element) throws XMLStreamException {

        writer.writeStartElement(element.getLocalName());
        this.writeRequired(writer, Attribute.TYPE, protocol, ModelKeys.TYPE);
        this.writeOptional(writer, Attribute.SHARED, protocol, ModelKeys.SHARED);
        this.writeOptional(writer, Attribute.SOCKET_BINDING, protocol, ModelKeys.SOCKET_BINDING);
        this.writeOptional(writer, Attribute.DIAGNOSTICS_SOCKET_BINDING, protocol, ModelKeys.DIAGNOSTICS_SOCKET_BINDING);
        this.writeOptional(writer, Attribute.DEFAULT_EXECUTOR, protocol, ModelKeys.DEFAULT_EXECUTOR);
        this.writeOptional(writer, Attribute.OOB_EXECUTOR, protocol, ModelKeys.OOB_EXECUTOR);
        this.writeOptional(writer, Attribute.TIMER_EXECUTOR, protocol, ModelKeys.TIMER_EXECUTOR);
        this.writeOptional(writer, Attribute.THREAD_FACTORY, protocol, ModelKeys.THREAD_FACTORY);
        this.writeOptional(writer, Attribute.MACHINE, protocol, ModelKeys.MACHINE);
        this.writeOptional(writer, Attribute.RACK, protocol, ModelKeys.RACK);
        this.writeOptional(writer, Attribute.SITE, protocol, ModelKeys.SITE);
        this.writeProtocolProperties(writer, protocol);
        writer.writeEndElement();
    }

    private void writeProtocolProperties(XMLExtendedStreamWriter writer, ModelNode protocol) throws XMLStreamException {
        // the format of the property elements
        //  "property" => {
        //       "relative-to" => {"value" => "fred"},
        //   }
        if (protocol.hasDefined(ModelKeys.PROPERTY)) {
            for (Property property: protocol.get(ModelKeys.PROPERTY).asPropertyList()) {
                writer.writeStartElement(Element.PROPERTY.getLocalName());
                writer.writeAttribute(Attribute.NAME.getLocalName(), property.getName());
                Property complexValue = property.getValue().asProperty();
                writer.writeCharacters(complexValue.getValue().asString());
                writer.writeEndElement();
            }
        }
    }

    private void writeRelay(XMLExtendedStreamWriter writer, ModelNode relay, Element element) throws XMLStreamException {
        writer.writeStartElement(element.getLocalName());
        RelayResourceDefinition.SITE.marshallAsAttribute(relay, writer);
        for (Property property : relay.get(ModelKeys.REMOTE_SITE).asPropertyList()) {
            writer.writeStartElement(Element.REMOTE_SITE.getLocalName());
            writer.writeAttribute(Attribute.NAME.getLocalName(), property.getName());
            ModelNode remoteSite = property.getValue();
            RemoteSiteResourceDefinition.STACK.marshallAsAttribute(remoteSite, writer);
            RemoteSiteResourceDefinition.CLUSTER.marshallAsAttribute(remoteSite, writer);
            writer.writeEndElement();
        }
        this.writeProtocolProperties(writer, relay);
        writer.writeEndElement();
    }

    private void writeSasl(XMLExtendedStreamWriter writer, ModelNode sasl, Element element) throws XMLStreamException {
       writer.writeStartElement(element.getLocalName());
       for(SimpleAttributeDefinition attr : SaslResourceDefinition.ATTRIBUTES) {
           attr.marshallAsAttribute(sasl, writer);
       }
       this.writeProtocolProperties(writer, sasl);
       writer.writeEndElement();
    }

    private void writeRequired(XMLExtendedStreamWriter writer, Attribute attribute, ModelNode model, String key) throws XMLStreamException {
        writer.writeAttribute(attribute.getLocalName(), model.require(key).asString());
    }

    private void writeOptional(XMLExtendedStreamWriter writer, Attribute attribute, ModelNode model, String key) throws XMLStreamException {
        if (model.hasDefined(key)) {
            writer.writeAttribute(attribute.getLocalName(), model.get(key).asString());
        }
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/Namespace.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.jboss.dmr.ModelNode;
import org.jboss.staxmapper.XMLElementReader;

/**
 * The namespaces supported by the jgroups extension.
 *
 * @author Paul Ferraro
 * @author Tristan Tarrant
 */
public enum Namespace {
    // must be first
    UNKNOWN("jboss:domain:jgroups", 0, 0, null),

    JGROUPS_1_0("jboss:domain:jgroups", 1, 0, new JGroupsSubsystemXMLReader_1_0()),
    JGROUPS_1_1("jboss:domain:jgroups", 1, 1, new JGroupsSubsystemXMLReader_1_1()),
    JGROUPS_1_2("jboss:domain:jgroups", 1, 2, new JGroupsSubsystemXMLReader_1_2()),

    INFINISPAN_SERVER_JGROUPS_7_0("infinispan:server:jgroups", 7, 0, new JGroupsSubsystemXMLReader_7_0()),
    ;

    private static final String URN_PATTERN = "urn:%s:%d.%d";

    /**
     * The current namespace version.
     */
    public static final Namespace CURRENT = INFINISPAN_SERVER_JGROUPS_7_0;

    private final String domain;
    private final int major;
    private final int minor;
    private final XMLElementReader<List<ModelNode>> reader;

    Namespace(String domain, int major, int minor, XMLElementReader<List<ModelNode>> reader) {
        this.domain = domain;
        this.major = major;
        this.minor = minor;
        this.reader = reader;
    }

    public int getMajorVersion() {
        return this.major;
    }

    public int getMinorVersion() {
        return this.minor;
    }

    /**
     * Get the URI of this namespace.
     *
     * @return the URI
     */
    public String getUri() {
        return String.format(URN_PATTERN, domain, this.major, this.minor);
    }

    public XMLElementReader<List<ModelNode>> getXMLReader() {
        return this.reader;
    }

    private static final Map<String, Namespace> namespaces;

    static {
        final Map<String, Namespace> map = new HashMap<String, Namespace>();
        for (Namespace namespace : values()) {
            final String name = namespace.getUri();
            if (name != null) map.put(name, namespace);
        }
        namespaces = map;
    }

    /**
     * Converts the specified uri to a {@link Namespace}.
     * @param uri a namespace uri
     * @return the matching namespace enum.
     */
    public static Namespace forUri(String uri) {
        final Namespace element = namespaces.get(uri);
        return element == null ? UNKNOWN : element;
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/PropertyResourceDefinition.java
package org.jboss.as.clustering.jgroups.subsystem;

import java.util.List;

import org.jboss.as.controller.AbstractAddStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.controller.ServiceVerificationHandler;
import org.jboss.as.controller.SimpleAttributeDefinition;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.operations.validation.StringLengthValidator;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;
import org.jboss.msc.service.ServiceController;

/**
 * Resource description for the addressable resources:
 *
 *   /subsystem=jgroups/stack=X/transport=TRANSPORT/property=Z
 *   /subsystem=jgroups/stack=X/protocol=Y/property=Z
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */

public class PropertyResourceDefinition extends SimpleResourceDefinition {

    static final PathElement PROPERTY_PATH = PathElement.pathElement(ModelKeys.PROPERTY);

    static SimpleAttributeDefinition VALUE =
            new SimpleAttributeDefinitionBuilder("value", ModelType.STRING, false)
                    .setXmlName("value")
                    .setAllowExpression(true)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .setValidator(new StringLengthValidator(0))
                    .build();


    static final OperationStepHandler REMOVE = new OperationStepHandler() {
        @Override
        public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
            context.removeResource(PathAddress.EMPTY_ADDRESS);
            reloadRequiredStep(context);
            context.stepCompleted();
        }
    };

    static final AbstractAddStepHandler PROTOCOL_PROPERTY_ADD = new AbstractAddStepHandler() {
        @Override
        protected void populateModel(ModelNode operation, ModelNode model) throws OperationFailedException {
            PropertyResourceDefinition.VALUE.validateAndSet(operation, model);
        }

        @Override
        protected void performRuntime(OperationContext context, ModelNode operation, ModelNode model, ServiceVerificationHandler verificationHandler, List<ServiceController<?>> newControllers) throws OperationFailedException {
            reloadRequiredStep(context);
        }
    };

    static final PropertyResourceDefinition INSTANCE = new PropertyResourceDefinition() ;

    // registration
    PropertyResourceDefinition() {
        super(PROPERTY_PATH,
                JGroupsExtension.getResourceDescriptionResolver(ModelKeys.PROPERTY),
                PropertyResourceDefinition.PROTOCOL_PROPERTY_ADD,
                PropertyResourceDefinition.REMOVE);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration resourceRegistration) {
        super.registerOperations(resourceRegistration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration resourceRegistration) {
        super.registerAttributes(resourceRegistration);

        resourceRegistration.registerReadWriteAttribute(VALUE, null, new ReloadRequiredWriteAttributeHandler(VALUE));
    }

    /**
     * Add a step triggering the {@linkplain org.jboss.as.controller.OperationContext#reloadRequired()} in case the
     * the cache service is installed, since the transport-config operations need a reload/restart and can't be
     * applied to the runtime directly.
     *
     * @param context the operation context
     */
    static void reloadRequiredStep(final OperationContext context) {
        if (context.getProcessType().isServer() &&  !context.isBooting()) {
            context.addStep(new OperationStepHandler() {
                @Override
                public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
                    // add some condition here if reload needs to be conditional on context
                    // e.g. if a service is not installed, don't do a reload
                    context.reloadRequired();
                    context.stepCompleted();
                }
            }, OperationContext.Stage.RUNTIME);
        }
    }

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/ProtocolLayerAdd.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.jgroups.subsystem;

import org.jboss.as.clustering.jgroups.JGroupsMessages;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.Resource;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;

/**
 * Implements the operation /subsystem=jgroups/stack=X/protocol=Y:add()
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class ProtocolLayerAdd implements OperationStepHandler {
    AttributeDefinition[] attributes;

    public ProtocolLayerAdd(AttributeDefinition... attributes) {
        this.attributes = attributes;
    }

    @Override
    public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {

        // read /subsystem=jgroups/stack=* for update
        final Resource resource = context.readResourceForUpdate(PathAddress.EMPTY_ADDRESS);
        final ModelNode subModel = resource.getModel();

        // validate the protocol type to be added
        ModelNode type = ProtocolResourceDefinition.TYPE.validateOperation(operation);
        PathElement protocolRelativePath = PathElement.pathElement(ModelKeys.PROTOCOL, type.asString());

        // if child resource already exists, throw OFE
        if (resource.hasChild(protocolRelativePath)) {
            throw JGroupsMessages.MESSAGES.protocolAlreadyDefined(protocolRelativePath.toString());
        }

        // now get the created model
        Resource childResource = context.createResource(PathAddress.pathAddress(protocolRelativePath));
        final ModelNode protocol = childResource.getModel();

        // Process attributes
        for (final AttributeDefinition attribute : attributes) {
            // we use PROPERTIES only to allow the user to pass in a list of properties on store add commands
            // don't copy these into the model
            if (attribute.getName().equals(ModelKeys.PROPERTIES)) { continue; }

            attribute.validateAndSet(operation, protocol);
        }

        // get the current list of protocol names and add the new protocol
        // this list is used to maintain order
        ModelNode protocols = subModel.get(ModelKeys.PROTOCOLS);
        if (!protocols.isDefined()) {
            protocols.setEmptyList();
        }
        protocols.add(type);

        // Process type specific properties if required

        // The protocol parameters  <property name=>value</property>
        if (operation.hasDefined(ModelKeys.PROPERTIES)) {
            for (Property property : operation.get(ModelKeys.PROPERTIES).asPropertyList()) {
                // create a new property=name resource
                final Resource param = context.createResource(PathAddress.pathAddress(protocolRelativePath, PathElement.pathElement(ModelKeys.PROPERTY, property.getName())));
                final ModelNode value = property.getValue();
                if (!value.isDefined()) {
                    throw JGroupsMessages.MESSAGES.propertyNotDefined(property.getName(), protocolRelativePath.toString());
                }
                // set the value of the property
                PropertyResourceDefinition.VALUE.validateAndSet(value, param.getModel());
            }
        }
        // This needs a reload
        reloadRequiredStep(context);
        context.stepCompleted();
    }

    void process(ModelNode subModel, ModelNode operation) {
        //
    }

    /**
     * Add a step triggering the {@linkplain org.jboss.as.controller.OperationContext#reloadRequired()} in case the
     * the cache service is installed, since the transport-config operations need a reload/restart and can't be
     * applied to the runtime directly.
     *
     * @param context the operation context
     */
    void reloadRequiredStep(final OperationContext context) {
        if (context.getProcessType().isServer() && !context.isBooting()) {
            context.addStep(new OperationStepHandler() {
                @Override
                public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
                    // add some condition here if reload needs to be conditional on context
                    // e.g. if a service is not installed, don't do a reload
                    context.reloadRequired();
                    context.stepCompleted();
                }
            }, OperationContext.Stage.RUNTIME);
        }
    }

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/ProtocolLayerRemove.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.jgroups.subsystem;

import java.util.List;

import org.jboss.as.clustering.jgroups.JGroupsMessages;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.Resource;
import org.jboss.dmr.ModelNode;

/**
 * Implements the operation /subsystem=jgroups/stack=X/protocol=Y:remove()
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class ProtocolLayerRemove implements OperationStepHandler {
    static final ProtocolLayerRemove INSTANCE = new ProtocolLayerRemove();

    public ProtocolLayerRemove() {
    }

    @Override
    public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
        // read /subsystem=jgroups/stack=* for update
        final Resource resource = context.readResourceForUpdate(PathAddress.EMPTY_ADDRESS);
        final ModelNode subModel = resource.getModel();

         // validate the protocol type to be removed
        ModelNode type = ProtocolResourceDefinition.TYPE.validateOperation(operation);
        PathElement protocolRelativePath = PathElement.pathElement(ModelKeys.PROTOCOL, type.asString());

        // if child resource already exists, throw OFE
        // TODO not sure if this works ex expected - it may only confirm a registered resource
        if (!resource.hasChild(protocolRelativePath))  {
            throw JGroupsMessages.MESSAGES.protocolNotDefined(protocolRelativePath.toString()) ;
        }

        // remove the resource and its children
        context.removeResource(PathAddress.pathAddress(protocolRelativePath));

        // get the current list of protocol names and remove the protocol
        // copy all elements of the list except the one to remove
        // this list is used to maintain order
        List<ModelNode> protocols = subModel.get(ModelKeys.PROTOCOLS).asList() ;
        ModelNode newList = new ModelNode() ;
        if (protocols == null) {
            // something wrong
        }
        for (ModelNode protocol : protocols) {
            if (!protocol.asString().equals(type.asString())) {
               newList.add(protocol);
            }
        }
        subModel.get(ModelKeys.PROTOCOLS).set(newList);

        // This needs a reload
        reloadRequiredStep(context);
        context.stepCompleted();
    }

    /**
     * Add a step triggering the {@linkplain org.jboss.as.controller.OperationContext#reloadRequired()} in case the
     * the cache service is installed, since the transport-config operations need a reload/restart and can't be
     * applied to the runtime directly.
     *
     * @param context the operation context
     */
    void reloadRequiredStep(final OperationContext context) {
        if (context.getProcessType().isServer() &&  !context.isBooting()) {
            context.addStep(new OperationStepHandler() {
                @Override
                public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
                    // add some condition here if reload needs to be conditional on context
                    // e.g. if a service is not installed, don't do a reload
                    context.reloadRequired();
                    context.stepCompleted();
                }
            }, OperationContext.Stage.RUNTIME);
        }
    }

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/ProtocolResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.jgroups.subsystem;

import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ObjectListAttributeDefinition;
import org.jboss.as.controller.ObjectTypeAttributeDefinition;
import org.jboss.as.controller.OperationDefinition;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.controller.SimpleAttributeDefinition;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleListAttributeDefinition;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.dmr.ModelType;

/**
 * Resource description for /subsystem=jgroups/stack=X/protocol=Y
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */

public class ProtocolResourceDefinition extends SimpleResourceDefinition {
    static final PathElement PROTOCOL_PATH = PathElement.pathElement(ModelKeys.PROTOCOL);

    // attributes
    static SimpleAttributeDefinition TYPE =
            new SimpleAttributeDefinitionBuilder(ModelKeys.TYPE, ModelType.STRING, false)
                    .setXmlName(Attribute.TYPE.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition SOCKET_BINDING =
            new SimpleAttributeDefinitionBuilder(ModelKeys.SOCKET_BINDING, ModelType.STRING, true)
                    .setXmlName(Attribute.SOCKET_BINDING.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition PROPERTY = new SimpleAttributeDefinition(ModelKeys.PROPERTY, ModelType.PROPERTY, true);
    static SimpleListAttributeDefinition PROPERTIES = new SimpleListAttributeDefinition.Builder(ModelKeys.PROPERTIES, PROPERTY).
            setAllowNull(true).
            build();

    static AttributeDefinition[] PROTOCOL_ATTRIBUTES = new AttributeDefinition[] {TYPE, SOCKET_BINDING};
    static AttributeDefinition[] PROTOCOL_PARAMETERS = new AttributeDefinition[] {TYPE, SOCKET_BINDING, PROPERTIES};

    static final ObjectTypeAttributeDefinition PROTOCOL = ObjectTypeAttributeDefinition.
                Builder.of(ModelKeys.PROTOCOL, PROTOCOL_ATTRIBUTES).
                setAllowNull(true).
                setSuffix(null).
                setSuffix("protocol").
                build();

    static final ObjectListAttributeDefinition PROTOCOLS = ObjectListAttributeDefinition.
            Builder.of(ModelKeys.PROTOCOLS, PROTOCOL).
            setAllowNull(true).
            build();

    // operations
    static final OperationDefinition PROTOCOL_ADD = new SimpleOperationDefinitionBuilder(ModelKeys.ADD_PROTOCOL, JGroupsExtension.getResourceDescriptionResolver("stack"))
            .setParameters(PROTOCOL_PARAMETERS)
            .build();

    static final OperationDefinition PROTOCOL_REMOVE = new SimpleOperationDefinitionBuilder(ModelKeys.REMOVE_PROTOCOL, JGroupsExtension.getResourceDescriptionResolver("stack"))
            .setParameters(TYPE)
            .build();

    static final OperationStepHandler PROTOCOL_ADD_HANDLER = new ProtocolLayerAdd(PROTOCOL_PARAMETERS);
    static final OperationStepHandler PROTOCOL_REMOVE_HANDLER = new ProtocolLayerRemove();
    static final ProtocolResourceDefinition INSTANCE = new ProtocolResourceDefinition();

    // registration
    private ProtocolResourceDefinition() {
        super(PROTOCOL_PATH, JGroupsExtension.getResourceDescriptionResolver(ModelKeys.PROTOCOL));
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration resourceRegistration) {
        super.registerAttributes(resourceRegistration);
        final OperationStepHandler writeHandler = new ReloadRequiredWriteAttributeHandler(PROTOCOL_ATTRIBUTES);
        for (AttributeDefinition attr : PROTOCOL_ATTRIBUTES) {
            resourceRegistration.registerReadWriteAttribute(attr, null, writeHandler);
        }
    }

    @Override
    public void registerChildren(ManagementResourceRegistration resourceRegistration) {
        super.registerChildren(resourceRegistration);
        resourceRegistration.registerSubModel(PropertyResourceDefinition.INSTANCE);
    }
}

File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/ProtocolStackAdd.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OPERATION_NAME;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;

import java.lang.reflect.Field;
import java.security.AccessController;
import java.security.PrivilegedAction;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.ResourceBundle;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadFactory;

import javax.management.MBeanServer;

import org.jboss.as.clustering.jgroups.ChannelFactory;
import org.jboss.as.clustering.jgroups.JGroupsMessages;
import org.jboss.as.clustering.jgroups.ProtocolConfiguration;
import org.jboss.as.clustering.jgroups.ProtocolDefaults;
import org.jboss.as.clustering.jgroups.ProtocolStackConfiguration;
import org.jboss.as.clustering.jgroups.RelayConfiguration;
import org.jboss.as.clustering.jgroups.RemoteSiteConfiguration;
import org.jboss.as.clustering.jgroups.SaslConfiguration;
import org.jboss.as.clustering.jgroups.TransportConfiguration;
import org.jboss.as.controller.AbstractAddStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.ServiceVerificationHandler;
import org.jboss.as.controller.descriptions.DescriptionProvider;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.registry.Resource;
import org.jboss.as.domain.management.SecurityRealm;
import org.jboss.as.jmx.MBeanServerService;
import org.jboss.as.network.SocketBinding;
import org.jboss.as.server.ServerEnvironment;
import org.jboss.as.server.ServerEnvironmentService;
import org.jboss.as.threads.ThreadsServices;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;
import org.jboss.msc.inject.Injector;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.value.InjectedValue;
import org.jboss.msc.value.Value;
import org.jboss.threads.JBossExecutors;

/**
 * @author Paul Ferraro
 */
public class ProtocolStackAdd extends AbstractAddStepHandler implements DescriptionProvider {

    public static final ProtocolStackAdd INSTANCE = new ProtocolStackAdd();

    static ModelNode createOperation(ModelNode address, ModelNode existing) {
        ModelNode operation = Util.getEmptyOperation(ModelDescriptionConstants.ADD, address);
        populate(existing, operation);
        return operation;
    }

    // need to override the description provider in order to not include the attribute protocols
    @Override
    public ModelNode getModelDescription(Locale locale) {
        ResourceBundle resources = ResourceBundle.getBundle(JGroupsExtension.RESOURCE_NAME, (locale == null) ? Locale.getDefault() : locale);

        ModelNode stack = new ModelNode();
        stack.get(ModelDescriptionConstants.OPERATION_NAME).set(ADD);
        stack.get(ModelDescriptionConstants.DESCRIPTION).set(resources.getString("jgroups.stack.add"));

        // optional TRANSPORT and PROTOCOLS parameters (to permit configuring a stack from add())
        TransportResourceDefinition.TRANSPORT.addOperationParameterDescription(resources,"jgroups.stack.add", stack);
        ProtocolResourceDefinition.PROTOCOLS.addOperationParameterDescription(resources, "jgroups.stack.add" , stack);

        return stack ;
    }

    private static void populate(ModelNode source, ModelNode target) {
        // nothing to do for a basic add
    }

    @Override
    protected void populateModel(final ModelNode operation, final ModelNode model) {
        // this method is abstract in AbstractAddStepHandler
        // we want to use its more explicit version below, but have to override it anyway
    }

    @Override
    protected void populateModel(final OperationContext context, final ModelNode operation, final Resource resource) {

        final ModelNode model = resource.getModel();

        // handle the basic add() operation parameters
        populate(operation, model);

        // add a step to initialize an *optional* TRANSPORT parameter
        if (operation.hasDefined(ModelKeys.TRANSPORT)) {
            // create an ADD operation to add the transport=TRANSPORT child
            ModelNode addTransport = operation.get(ModelKeys.TRANSPORT).clone();

            addTransport.get(OPERATION_NAME).set(ModelDescriptionConstants.ADD);
            ModelNode transportAddress = operation.get(OP_ADDR).clone();
            transportAddress.add(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);
            transportAddress.protect();
            addTransport.get(OP_ADDR).set(transportAddress);

            // execute the operation using the transport handler
            context.addStep(addTransport, TransportResourceDefinition.TRANSPORT_ADD, OperationContext.Stage.MODEL, true);
        }

        // add steps to initialize *optional* PROTOCOL parameters
        if (operation.hasDefined(ModelKeys.PROTOCOLS)) {

            List<ModelNode> protocols = operation.get(ModelKeys.PROTOCOLS).asList();
            // because we use stage IMMEDIATE when creating protocols, unless we reverse the order
            // of the elements in the LIST, they will get applied in reverse order - the last step
            // added gets executed first

            for (int i = protocols.size()-1; i >= 0; i--) {
                ModelNode protocol = protocols.get(i);

                // create an ADD operation to add the protocol=* child
                ModelNode addProtocol = protocol.clone();
                addProtocol.get(OPERATION_NAME).set(ModelKeys.ADD_PROTOCOL);
                // add-protocol is a stack operation
                ModelNode protocolAddress = operation.get(OP_ADDR).clone();
                protocolAddress.protect();
                addProtocol.get(OP_ADDR).set(protocolAddress);

                // execute the operation using the transport handler
                context.addStep(addProtocol, ProtocolResourceDefinition.PROTOCOL_ADD_HANDLER, OperationContext.Stage.MODEL, true);
            }
        }
    }

    @Override
    protected void performRuntime(OperationContext context, ModelNode operation, ModelNode model, ServiceVerificationHandler verificationHandler, List<ServiceController<?>> newControllers)
            throws OperationFailedException {

        // Because we use child resources in a read-only manner to configure the protocol stack, replace the local model with the full model
        model = Resource.Tools.readModel(context.readResource(PathAddress.EMPTY_ADDRESS));

        installRuntimeServices(context, operation, model, verificationHandler, newControllers);
    }

    protected void installRuntimeServices(OperationContext context, ModelNode operation, ModelNode model, ServiceVerificationHandler verificationHandler, List<ServiceController<?>> newControllers) throws OperationFailedException {

        final PathAddress address = PathAddress.pathAddress(operation.get(OP_ADDR));
        final String name = address.getLastElement().getValue();

        // check that we have enough information to create a stack
        protocolStackSanityCheck(name, model);

        // we need to preserve the order of the protocols as maintained by PROTOCOLS
        // pick up the ordered protocols here as a List<Property> where property is <name, ModelNode>
        List<Property> orderedProtocols = getOrderedProtocolPropertyList(model);

        // pick up the transport here and its values
        ModelNode resolvedValue = null;
        ModelNode transport = model.get(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);
        final String type = (resolvedValue = TransportResourceDefinition.TYPE.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final boolean  shared = TransportResourceDefinition.SHARED.resolveModelAttribute(context, transport).asBoolean();
        final String machine = (resolvedValue = TransportResourceDefinition.MACHINE.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final String rack = (resolvedValue = TransportResourceDefinition.RACK.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final String site = (resolvedValue = TransportResourceDefinition.SITE.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final String timerExecutor = (resolvedValue = TransportResourceDefinition.TIMER_EXECUTOR.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final String threadFactory = (resolvedValue = TransportResourceDefinition.THREAD_FACTORY.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final String diagnosticsSocketBinding = (resolvedValue = TransportResourceDefinition.DIAGNOSTICS_SOCKET_BINDING.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final String defaultExecutor = (resolvedValue = TransportResourceDefinition.DEFAULT_EXECUTOR.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final String oobExecutor = (resolvedValue = TransportResourceDefinition.OOB_EXECUTOR.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;
        final String transportSocketBinding = (resolvedValue = TransportResourceDefinition.SOCKET_BINDING.resolveModelAttribute(context, transport)).isDefined() ? resolvedValue.asString() : null;

        // set up the transport
        Transport transportConfig = new Transport(type);
        transportConfig.setShared(shared);
        transportConfig.setTopology(site, rack, machine);
        initProtocolProperties(context, transport, transportConfig);

        Relay relayConfig = null;
        List<Map.Entry<String, Injector<ChannelFactory>>> stacks = new LinkedList<Map.Entry<String, Injector<ChannelFactory>>>();
        if (model.hasDefined(ModelKeys.RELAY)) {
            final ModelNode relay = model.get(ModelKeys.RELAY, ModelKeys.RELAY_NAME);
            final String siteName = RelayResourceDefinition.SITE.resolveModelAttribute(context, relay).asString();
            relayConfig = new Relay(siteName);
            initProtocolProperties(context, relay, relayConfig);
            if (relay.hasDefined(ModelKeys.REMOTE_SITE)) {
                List<RemoteSiteConfiguration> remoteSites = relayConfig.getRemoteSites();
                for (Property remoteSiteProperty : relay.get(ModelKeys.REMOTE_SITE).asPropertyList()) {
                    final String remoteSiteName = remoteSiteProperty.getName();
                    final ModelNode remoteSite = remoteSiteProperty.getValue();
                    final String clusterName = RemoteSiteResourceDefinition.CLUSTER.resolveModelAttribute(context, remoteSite)
                            .asString();
                    final String stack = RemoteSiteResourceDefinition.STACK.resolveModelAttribute(context, remoteSite).asString();
                    final InjectedValue<ChannelFactory> channelFactory = new InjectedValue<ChannelFactory>();
                    remoteSites.add(new RemoteSite(remoteSiteName, clusterName, channelFactory));
                    stacks.add(new AbstractMap.SimpleImmutableEntry<String, Injector<ChannelFactory>>(stack, channelFactory));
                }
            }
        }

        Sasl saslConfig = null;
        if (model.hasDefined(ModelKeys.SASL)) {
            final ModelNode sasl = model.get(ModelKeys.SASL, ModelKeys.SASL_NAME);
            final String clusterRole = (resolvedValue = SaslResourceDefinition.CLUSTER_ROLE.resolveModelAttribute(context, sasl)).isDefined() ? resolvedValue.asString() : null;
            final String securityRealm = SaslResourceDefinition.SECURITY_REALM.resolveModelAttribute(context, sasl).asString();
            final String mech = SaslResourceDefinition.MECH.resolveModelAttribute(context, sasl).asString();
            saslConfig = new Sasl(securityRealm, mech, clusterRole);
            initProtocolProperties(context, sasl, saslConfig);
        }

        // set up the protocol stack Protocol objects
        ProtocolStack stackConfig = new ProtocolStack(name, transportConfig, relayConfig, saslConfig);
        List<Map.Entry<Protocol, String>> protocolSocketBindings = new ArrayList<Map.Entry<Protocol, String>>(orderedProtocols.size());
        for (Property protocolProperty : orderedProtocols) {
            ModelNode protocol = protocolProperty.getValue();
            final String protocolType = (resolvedValue = ProtocolResourceDefinition.TYPE.resolveModelAttribute(context, protocol)).isDefined() ? resolvedValue.asString() : null;
            Protocol protocolConfig = new Protocol(protocolType);
            initProtocolProperties(context, protocol, protocolConfig);
            stackConfig.getProtocols().add(protocolConfig);
            final String protocolSocketBinding = (resolvedValue = ProtocolResourceDefinition.SOCKET_BINDING.resolveModelAttribute(context, protocol)).isDefined() ? resolvedValue.asString() : null;
            protocolSocketBindings.add(new AbstractMap.SimpleImmutableEntry<Protocol, String>(protocolConfig, protocolSocketBinding));
        }

        // install the default channel factory service
        ServiceController<ChannelFactory> cfsController = installChannelFactoryService(context.getServiceTarget(),
                        name, diagnosticsSocketBinding, defaultExecutor, oobExecutor, timerExecutor, threadFactory,
                        transportSocketBinding, protocolSocketBindings, transportConfig, stackConfig, stacks, saslConfig, verificationHandler);
        if (newControllers != null) {
            newControllers.add(cfsController);
        }
    }

    protected void removeRuntimeServices(OperationContext context, ModelNode operation, ModelNode model)
            throws OperationFailedException {

        final PathAddress address = PathAddress.pathAddress(operation.get(ModelDescriptionConstants.OP_ADDR));
        final String name = address.getLastElement().getValue();

        // remove the ChannelFactoryServiceService
        context.removeService(ChannelFactoryService.getServiceName(name));
    }


    protected ServiceController<ChannelFactory> installChannelFactoryService(ServiceTarget target,
                                                                             String name,
                                                                             String diagnosticsSocketBinding,
                                                                             String defaultExecutor,
                                                                             String oobExecutor,
                                                                             String timerExecutor,
                                                                             String threadFactory,
                                                                             String transportSocketBinding,
                                                                             List<Map.Entry<Protocol, String>> protocolSocketBindings,
                                                                             Transport transportConfig,
                                                                             ProtocolStack stackConfig,
                                                                             List<Map.Entry<String, Injector<ChannelFactory>>> stacks,
                                                                             Sasl sasl,
                                                                             ServiceVerificationHandler verificationHandler) {

        // create the channel factory service builder
        ServiceBuilder<ChannelFactory> builder = target
                .addService(ChannelFactoryService.getServiceName(name), new ChannelFactoryService(stackConfig))
                .addDependency(ProtocolDefaultsService.SERVICE_NAME, ProtocolDefaults.class, stackConfig.getDefaultsInjector())
                .addDependency(MBeanServerService.SERVICE_NAME, MBeanServer.class, stackConfig.getMBeanServerInjector())
                .addDependency(ServerEnvironmentService.SERVICE_NAME, ServerEnvironment.class, stackConfig.getEnvironmentInjector())
                .setInitialMode(ServiceController.Mode.ON_DEMAND)
        ;
        // add transport dependencies
        addSocketBindingDependency(builder, transportSocketBinding, transportConfig.getSocketBindingInjector());

        for (Map.Entry<Protocol, String> entry: protocolSocketBindings) {
            addSocketBindingDependency(builder, entry.getValue(), entry.getKey().getSocketBindingInjector());
        }

        // add remaining dependencies
        addSocketBindingDependency(builder, diagnosticsSocketBinding, transportConfig.getDiagnosticsSocketBindingInjector());
        addExecutorDependency(builder, defaultExecutor, transportConfig.getDefaultExecutorInjector());
        addExecutorDependency(builder, oobExecutor, transportConfig.getOOBExecutorInjector());
        if (timerExecutor != null) {
            builder.addDependency(ThreadsServices.executorName(timerExecutor), ScheduledExecutorService.class, transportConfig.getTimerExecutorInjector());
        }
        if (threadFactory != null) {
            builder.addDependency(ThreadsServices.threadFactoryName(threadFactory), ThreadFactory.class, transportConfig.getThreadFactoryInjector());
        }
        if (sasl != null) {
            builder.addDependency(SecurityRealm.ServiceUtil.createServiceName(sasl.getRealm()), SecurityRealm.class, sasl.getSecurityRealmInjector());
        }
        for (Map.Entry<String, Injector<ChannelFactory>> entry: stacks) {
            builder.addDependency(ChannelFactoryService.getServiceName(entry.getKey()), ChannelFactory.class, entry.getValue());
        }
        return builder.install();
    }

    private void initProtocolProperties(OperationContext context, ModelNode protocol, Protocol protocolConfig) throws OperationFailedException {

        Map<String, String> properties = protocolConfig.getProperties();
        // properties are a child resource of protocol
        if (protocol.hasDefined(ModelKeys.PROPERTY)) {
            for (Property property : protocol.get(ModelKeys.PROPERTY).asPropertyList()) {
                // the format of the property elements
                //  "property" => {
                //       "relative-to" => {"value" => "fred"},
                //   }
                String propertyName = property.getName();
                String propertyValue = PropertyResourceDefinition.VALUE.resolveModelAttribute(context, property.getValue()).asString();
                if (propertyValue != null && !propertyValue.isEmpty()) {
                   properties.put(propertyName, propertyValue);
                }
            }
        }
    }

    public static List<Property> getOrderedProtocolPropertyList(ModelNode stack) {
        ModelNode orderedProtocols = new ModelNode();

        // check for the empty ordering list
        if  (!stack.hasDefined(ModelKeys.PROTOCOLS)) {
            return null;
        }
        // PROTOCOLS is a list of protocol names only, reflecting the order in which protocols were added to the stack
        List<ModelNode> protocolOrdering = stack.get(ModelKeys.PROTOCOLS).asList();

        // now construct an ordered list of the full protocol model nodes
        ModelNode unorderedProtocols = stack.get(ModelKeys.PROTOCOL);
        for (ModelNode protocolName : protocolOrdering) {
            ModelNode protocolModel = unorderedProtocols.get(protocolName.asString());
            orderedProtocols.add(protocolName.asString(), protocolModel);
        }
        return orderedProtocols.asPropertyList();
    }

    private void addSocketBindingDependency(ServiceBuilder<ChannelFactory> builder, String socketBinding, Injector<SocketBinding> injector) {
        if (socketBinding != null) {
            builder.addDependency(SocketBinding.JBOSS_BINDING_NAME.append(socketBinding), SocketBinding.class, injector);
        }
    }

    private void addExecutorDependency(ServiceBuilder<ChannelFactory> builder, String executor, Injector<Executor> injector) {
        if (executor != null) {
            builder.addDependency(ThreadsServices.executorName(executor), Executor.class, injector);
        }
    }

    /*
     * A check that we have the minimal configuration required to create a protocol stack.
     */
    private void protocolStackSanityCheck(String stackName, ModelNode model) throws OperationFailedException {

         ModelNode transport = model.get(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);
         if (!transport.isDefined()) {
            throw JGroupsMessages.MESSAGES.transportNotDefined(stackName);
         }

         List<Property> protocols = getOrderedProtocolPropertyList(model);
         if ( protocols == null || !(protocols.size() > 0)) {
             throw JGroupsMessages.MESSAGES.protocolListNotDefined(stackName);
         }
    }

    @Override
    protected boolean requiresRuntimeVerification() {
        return false;
    }

    static class ProtocolStack implements ProtocolStackConfiguration {
        private final InjectedValue<ProtocolDefaults> defaults = new InjectedValue<ProtocolDefaults>();
        private final InjectedValue<MBeanServer> mbeanServer = new InjectedValue<MBeanServer>();
        private final InjectedValue<ServerEnvironment> environment = new InjectedValue<ServerEnvironment>();
        private final InjectedValue<SecurityRealm> securityRealm = new InjectedValue<SecurityRealm>();

        private final String name;
        private final TransportConfiguration transport;
        private final RelayConfiguration relay;
        private final SaslConfiguration sasl;
        private final List<ProtocolConfiguration> protocols = new LinkedList<ProtocolConfiguration>();


        ProtocolStack(String name, TransportConfiguration transport, RelayConfiguration relay, SaslConfiguration sasl) {
            this.name = name;
            this.transport = transport;
            this.relay = relay;
            this.sasl = sasl;
        }

        public Injector<SecurityRealm> getSecurityRealmInjector() {
            return this.securityRealm;
        }

        Injector<ProtocolDefaults> getDefaultsInjector() {
            return this.defaults;
        }

        Injector<MBeanServer> getMBeanServerInjector() {
            return this.mbeanServer;
        }

        Injector<ServerEnvironment> getEnvironmentInjector() {
            return this.environment;
        }

        @Override
        public TransportConfiguration getTransport() {
            return this.transport;
        }

        @Override
        public List<ProtocolConfiguration> getProtocols() {
            return this.protocols;
        }

        @Override
        public String getName() {
            return this.name;
        }

        @Override
        public ProtocolDefaults getDefaults() {
            return this.defaults.getValue();
        }

        @Override
        public MBeanServer getMBeanServer() {
            return this.mbeanServer.getOptionalValue();
        }

        @Override
        public ServerEnvironment getEnvironment() {
            return this.environment.getValue();
        }

        @Override
        public RelayConfiguration getRelay() {
            return this.relay;
        }

        @Override
        public SaslConfiguration getSasl() {
            return this.sasl;
        }
    }

    static class Transport extends Protocol implements TransportConfiguration {
        private final InjectedValue<SocketBinding> diagnosticsSocketBinding = new InjectedValue<SocketBinding>();
        private final InjectedValue<Executor> defaultExecutor = new InjectedValue<Executor>();
        private final InjectedValue<Executor> oobExecutor = new InjectedValue<Executor>();
        private final InjectedValue<ScheduledExecutorService> timerExecutor = new InjectedValue<ScheduledExecutorService>();
        private final InjectedValue<ThreadFactory> threadFactory = new InjectedValue<ThreadFactory>();
        private boolean shared = true;
        private Topology topology;

        Transport(String name) {
            super(name);
        }

        Injector<SocketBinding> getDiagnosticsSocketBindingInjector() {
            return this.diagnosticsSocketBinding;
        }

        Injector<Executor> getDefaultExecutorInjector() {
            return this.defaultExecutor;
        }

        Injector<Executor> getOOBExecutorInjector() {
            return this.oobExecutor;
        }

        Injector<ScheduledExecutorService> getTimerExecutorInjector() {
            return this.timerExecutor;
        }

        Injector<ThreadFactory> getThreadFactoryInjector() {
            return this.threadFactory;
        }

        void setShared(boolean shared) {
            this.shared = shared;
        }

        @Override
        public boolean isShared() {
            return this.shared;
        }

        @Override
        public Topology getTopology() {
            return this.topology;
        }

        public void setTopology(String site, String rack, String machine) {
            if ((site != null) || (rack != null) || (machine != null)) {
                this.topology = new TopologyImpl(site, rack, machine);
            }
        }

        @Override
        public SocketBinding getDiagnosticsSocketBinding() {
            return this.diagnosticsSocketBinding.getOptionalValue();
        }

        @Override
        public ExecutorService getDefaultExecutor() {
            Executor executor = this.defaultExecutor.getOptionalValue();
            return (executor != null) ? JBossExecutors.protectedExecutorService(executor) : null;
        }

        @Override
        public ExecutorService getOOBExecutor() {
            Executor executor = this.oobExecutor.getOptionalValue();
            return (executor != null) ? JBossExecutors.protectedExecutorService(executor) : null;
        }

        @Override
        public ScheduledExecutorService getTimerExecutor() {
            return this.timerExecutor.getOptionalValue();
        }

        @Override
        public ThreadFactory getThreadFactory() {
            return this.threadFactory.getOptionalValue();
        }

        private class TopologyImpl implements Topology {
            private final String site;
            private final String rack;
            private final String machine;

            TopologyImpl(String site, String rack, String machine) {
                this.site = site;
                this.rack = rack;
                this.machine = machine;
            }

            @Override
            public String getMachine() {
                return this.machine;
            }

            @Override
            public String getRack() {
                return this.rack;
            }

            @Override
            public String getSite() {
                return this.site;
            }
        }
    }

    static class Relay extends Protocol implements RelayConfiguration {
        private final List<RemoteSiteConfiguration> remoteSites = new LinkedList<RemoteSiteConfiguration>();
        private final String siteName;

        Relay(String siteName) {
            super("relay.RELAY2");
            this.siteName = siteName;
        }

        @Override
        public String getSiteName() {
            return this.siteName;
        }

        @Override
        public List<RemoteSiteConfiguration> getRemoteSites() {
            return this.remoteSites;
        }
    }

    static class RemoteSite implements RemoteSiteConfiguration {
        private final Value<ChannelFactory> channelFactory;
        private final String name;
        private final String clusterName;

        RemoteSite(String name, String clusterName, Value<ChannelFactory> channelFactory) {
            this.name = name;
            this.clusterName = clusterName;
            this.channelFactory = channelFactory;
        }

        @Override
        public String getName() {
            return this.name;
        }

        @Override
        public ChannelFactory getChannelFactory() {
            return this.channelFactory.getValue();
        }

        @Override
        public String getCluster() {
            return this.clusterName;
        }
    }

    static class Sasl extends Protocol implements SaslConfiguration {
       private final InjectedValue<SecurityRealm> securityRealmInjector = new InjectedValue<SecurityRealm>();
       private final String clusterRole;
       private final String realm;
       private final String mech;

       Sasl(String realm, String mech, String clusterRole) {
          super("SASL");
          this.realm = realm;
          this.mech = mech;
          this.clusterRole = clusterRole;
       }

       @Override
       public String getClusterRole() {
           return clusterRole;
       }

       @Override
       public String getMech() {
           return mech;
       }

       public String getRealm() {
           return realm;
       }

       @Override
       public SecurityRealm getSecurityRealm() {
         return securityRealmInjector.getValue();
       }

       public Injector<SecurityRealm> getSecurityRealmInjector() {
           return securityRealmInjector;
       }
    }

    static class Protocol implements ProtocolConfiguration {
        private final String name;
        private final InjectedValue<SocketBinding> socketBinding = new InjectedValue<SocketBinding>();
        private final Map<String, String> properties = new HashMap<String, String>();
        final Class<?> protocolClass;

        Protocol(final String name) {
            this.name = name;
            PrivilegedAction<Class<?>> action = new PrivilegedAction<Class<?>>() {
                @Override
                public Class<?> run() {
                    try {
                        return Protocol.this.getClass().getClassLoader().loadClass(org.jgroups.conf.ProtocolConfiguration.protocol_prefix + '.' + name);
                    } catch (ClassNotFoundException e) {
                        throw new IllegalStateException(e);
                    }
                }
            };
            this.protocolClass = AccessController.doPrivileged(action);
        }

        @Override
        public String getName() {
            return this.name;
        }

        @Override
        public boolean hasProperty(final String property) {
            PrivilegedAction<Field> action = new PrivilegedAction<Field>() {
                @Override
                public Field run() {
                    return getField(Protocol.this.protocolClass, property);
                }
            };
            return AccessController.doPrivileged(action) != null;
        }

        static Field getField(Class<?> targetClass, String property) {
            try {
                return targetClass.getDeclaredField(property);
            } catch (NoSuchFieldException e) {
                Class<?> superClass = targetClass.getSuperclass();
                return (superClass != null) && org.jgroups.stack.Protocol.class.isAssignableFrom(superClass) ? getField(superClass, property) : null;
            }
        }

        @Override
        public Map<String, String> getProperties() {
            return this.properties;
        }

        Injector<SocketBinding> getSocketBindingInjector() {
            return this.socketBinding;
        }

        @Override
        public SocketBinding getSocketBinding() {
            return this.socketBinding.getOptionalValue();
        }
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/RemoteSiteResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.ReloadRequiredRemoveStepHandler;
import org.jboss.as.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.controller.SimpleAttributeDefinition;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.descriptions.ResourceDescriptionResolver;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.dmr.ModelType;

/**
 * Resource definition for subsystem=jgroups/stack=X/relay=RELAY/remote-site=Y
 *
 * @author Paul Ferraro
 */
public class RemoteSiteResourceDefinition extends SimpleResourceDefinition {

    private static final ResourceDescriptionResolver RESOLVER = JGroupsExtension.getResourceDescriptionResolver(ModelKeys.REMOTE_SITE);

    static final SimpleAttributeDefinition STACK = new SimpleAttributeDefinitionBuilder(ModelKeys.STACK, ModelType.STRING, true)
            .setXmlName(Attribute.STACK.getLocalName())
            .setAllowExpression(true)
            .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
            .build()
    ;

    static final SimpleAttributeDefinition CLUSTER = new SimpleAttributeDefinitionBuilder(ModelKeys.CLUSTER, ModelType.STRING, true)
            .setXmlName(Attribute.CLUSTER.getLocalName())
            .setAllowExpression(true)
            .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
            .build()
    ;

    static final AttributeDefinition[] ATTRIBUTES = new AttributeDefinition[] { STACK, CLUSTER };

    RemoteSiteResourceDefinition() {
        super(PathElement.pathElement(ModelKeys.REMOTE_SITE), RESOLVER, new AddStepHandler(ATTRIBUTES), ReloadRequiredRemoveStepHandler.INSTANCE);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        final OperationStepHandler writeHandler = new ReloadRequiredWriteAttributeHandler(ATTRIBUTES);
        for (AttributeDefinition attribute: ATTRIBUTES) {
            registration.registerReadWriteAttribute(attribute, null, writeHandler);
        }
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/StackResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;

import org.jboss.as.controller.OperationDefinition;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.StringListAttributeDefinition;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=jgroups/stack=X
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */

public class StackResourceDefinition extends SimpleResourceDefinition {

    static final PathElement STACK_PATH = PathElement.pathElement(ModelKeys.STACK);
    static final OperationStepHandler EXPORT_NATIVE_CONFIGURATION_HANDLER = new ExportNativeConfiguration();

    private final boolean runtimeRegistration;

    static final StringListAttributeDefinition PROTOCOLS = new StringListAttributeDefinition.Builder(ModelKeys.PROTOCOLS)
            .setAllowNull(true)
            .build();

    // attributes
    // operations
    private static final OperationDefinition PROTOCOL_STACK_ADD = new SimpleOperationDefinitionBuilder(ADD, JGroupsExtension.getResourceDescriptionResolver(ModelKeys.STACK))
          .addParameter(TransportResourceDefinition.TRANSPORT)
          .addParameter(ProtocolResourceDefinition.PROTOCOLS)
          .setAttributeResolver(JGroupsExtension.getResourceDescriptionResolver("stack.add"))
          .build();

    static final OperationDefinition EXPORT_NATIVE_CONFIGURATION = new SimpleOperationDefinitionBuilder(ModelKeys.EXPORT_NATIVE_CONFIGURATION, JGroupsExtension.getResourceDescriptionResolver("stack"))
            .setReplyType(ModelType.STRING)
            .build();

    // registration
    public StackResourceDefinition(boolean runtimeRegistration) {
        super(STACK_PATH,
                JGroupsExtension.getResourceDescriptionResolver(ModelKeys.STACK),
                // register below with custom signature
                null,
                ProtocolStackRemove.INSTANCE);
        this.runtimeRegistration = runtimeRegistration;
    }

    @Override
    public void registerOperations(ManagementResourceRegistration resourceRegistration) {
        super.registerOperations(resourceRegistration);
        // override to set up TRANSPORT and PROTOCOLS parameters
        resourceRegistration.registerOperationHandler(PROTOCOL_STACK_ADD, ProtocolStackAdd.INSTANCE);
        // register protocol add and remove
        resourceRegistration.registerOperationHandler(ProtocolResourceDefinition.PROTOCOL_ADD, ProtocolResourceDefinition.PROTOCOL_ADD_HANDLER);
        resourceRegistration.registerOperationHandler(ProtocolResourceDefinition.PROTOCOL_REMOVE, ProtocolResourceDefinition.PROTOCOL_REMOVE_HANDLER);
        // register export-native-configuration
        if (runtimeRegistration) {
            resourceRegistration.registerOperationHandler(StackResourceDefinition.EXPORT_NATIVE_CONFIGURATION, StackResourceDefinition.EXPORT_NATIVE_CONFIGURATION_HANDLER);
        }
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration resourceRegistration) {
        super.registerAttributes(resourceRegistration);
        resourceRegistration.registerReadOnlyAttribute(PROTOCOLS, null);
    }

    @Override
    public void registerChildren(ManagementResourceRegistration resourceRegistration) {
        super.registerChildren(resourceRegistration);
        // child resources
        resourceRegistration.registerSubModel(TransportResourceDefinition.INSTANCE);
        resourceRegistration.registerSubModel(ProtocolResourceDefinition.INSTANCE);
        resourceRegistration.registerSubModel(new RelayResourceDefinition());
        resourceRegistration.registerSubModel(new SaslResourceDefinition());
    }
}

File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/SubsystemWriteAttributeHandler.java
package org.jboss.as.clustering.jgroups.subsystem;

import org.jboss.as.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.controller.registry.ManagementResourceRegistration;

/**
 * Handler for read and write access to the subsystem attribute default-stack.
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class SubsystemWriteAttributeHandler extends ReloadRequiredWriteAttributeHandler {

    public static final SubsystemWriteAttributeHandler INSTANCE = new SubsystemWriteAttributeHandler();

    private SubsystemWriteAttributeHandler() {
        super(JGroupsSubsystemRootResource.DEFAULT_STACK);
    }

    public void registerAttributes(final ManagementResourceRegistration registry) {
        registry.registerReadWriteAttribute(JGroupsSubsystemRootResource.DEFAULT_STACK, null, this);
    }
}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/TransportLayerAdd.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import org.jboss.as.clustering.jgroups.JGroupsMessages;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.Resource;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;

/**
 * Operation handler for /subsystem=jgroups/stack=X/transport=TRANSPORT:add()
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class TransportLayerAdd implements OperationStepHandler {

    AttributeDefinition[] attributes ;

    public TransportLayerAdd(AttributeDefinition... attributes) {
        this.attributes = attributes ;
    }

    @Override
    public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {

        final PathElement transportRelativePath = PathElement.pathElement(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);
        final Resource resource = context.createResource(PathAddress.EMPTY_ADDRESS);
        final ModelNode subModel = resource.getModel();

        // Process attributes
        for(final AttributeDefinition attribute : attributes) {
            // don't process properties twice - we do them below
            if (attribute.getName().equals(ModelKeys.PROPERTIES))
                continue ;
            attribute.validateAndSet(operation, subModel);
        }

        // The transport config parameters  <property name=>value</property>
        if(operation.hasDefined(ModelKeys.PROPERTIES)) {
            for(Property property : operation.get(ModelKeys.PROPERTIES).asPropertyList()) {
                // create a new property=name resource
                final Resource param = context.createResource(PathAddress.pathAddress(PathElement.pathElement(ModelKeys.PROPERTY, property.getName())));
                final ModelNode value = property.getValue();
                if(!value.isDefined()) {
                    throw JGroupsMessages.MESSAGES.propertyNotDefined(property.getName(), transportRelativePath.toString());
                }
                // set the value of the property
                PropertyResourceDefinition.VALUE.validateAndSet(value, param.getModel());
            }
        }
        // This needs a reload
        reloadRequiredStep(context);
        context.stepCompleted();
    }


    /**
     * Add a step triggering the {@linkplain org.jboss.as.controller.OperationContext#reloadRequired()} in case the
     * the cache service is installed, since the transport-config operations need a reload/restart and can't be
     * applied to the runtime directly.
     *
     * @param context the operation context
     */
    void reloadRequiredStep(final OperationContext context) {
        if (context.getProcessType().isServer() &&  !context.isBooting()) {
            context.addStep(new OperationStepHandler() {
                @Override
                public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
                    // add some condition here if reload needs to be conditional on context
                    // e.g. if a service is not installed, don't do a reload
                    context.reloadRequired();
                    context.stepCompleted();
                }
            }, OperationContext.Stage.RUNTIME);
        }
    }

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/TransportLayerRemove.java
package org.jboss.as.clustering.jgroups.subsystem;

import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.dmr.ModelNode;

/**
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class TransportLayerRemove implements OperationStepHandler {

    @Override
    public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
        context.removeResource(PathAddress.EMPTY_ADDRESS);
        reloadRequiredStep(context);
        context.stepCompleted();
    }

    void reloadRequiredStep(final OperationContext context) {
        if (context.getProcessType().isServer() &&  !context.isBooting()) {
            context.addStep(new OperationStepHandler() {
                @Override
                public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
                    // add some condition here if reload needs to be conditional on context
                    // e.g. if a service is not installed, don't do a reload
                    context.reloadRequired();
                    context.stepCompleted();
                }
            }, OperationContext.Stage.RUNTIME);
        }
    }

}


File: server/integration/jgroups/src/main/java/org/jboss/as/clustering/jgroups/subsystem/TransportResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2012, Red Hat, Inc., and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */

package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;

import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ObjectTypeAttributeDefinition;
import org.jboss.as.controller.OperationDefinition;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.controller.SimpleAttributeDefinition;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleListAttributeDefinition;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for /subsystem=jgroups/stack=X/transport=TRANSPORT
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */

public class TransportResourceDefinition extends SimpleResourceDefinition {

    static final PathElement TRANSPORT_PATH = PathElement.pathElement(ModelKeys.TRANSPORT, ModelKeys.TRANSPORT_NAME);

    // attributes
    static SimpleAttributeDefinition TYPE =
            new SimpleAttributeDefinitionBuilder(ModelKeys.TYPE, ModelType.STRING, false)
                    .setXmlName(Attribute.TYPE.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition SHARED =
            new SimpleAttributeDefinitionBuilder(ModelKeys.SHARED, ModelType.BOOLEAN, true)
                    .setXmlName(Attribute.SHARED.getLocalName())
                    .setAllowExpression(true)
                    .setDefaultValue(new ModelNode().set(true))
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition SOCKET_BINDING =
            new SimpleAttributeDefinitionBuilder(ModelKeys.SOCKET_BINDING, ModelType.STRING, true)
                    .setXmlName(Attribute.SOCKET_BINDING.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition DIAGNOSTICS_SOCKET_BINDING =
            new SimpleAttributeDefinitionBuilder(ModelKeys.DIAGNOSTICS_SOCKET_BINDING, ModelType.STRING, true)
                    .setXmlName(Attribute.DIAGNOSTICS_SOCKET_BINDING.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition DEFAULT_EXECUTOR =
            new SimpleAttributeDefinitionBuilder(ModelKeys.DEFAULT_EXECUTOR, ModelType.STRING, true)
                    .setXmlName(Attribute.DEFAULT_EXECUTOR.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition OOB_EXECUTOR =
            new SimpleAttributeDefinitionBuilder(ModelKeys.OOB_EXECUTOR, ModelType.STRING, true)
                    .setXmlName(Attribute.OOB_EXECUTOR.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition TIMER_EXECUTOR =
            new SimpleAttributeDefinitionBuilder(ModelKeys.TIMER_EXECUTOR, ModelType.STRING, true)
                    .setXmlName(Attribute.TIMER_EXECUTOR.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition THREAD_FACTORY =
            new SimpleAttributeDefinitionBuilder(ModelKeys.THREAD_FACTORY, ModelType.STRING, true)
                    .setXmlName(Attribute.THREAD_FACTORY.getLocalName())
                    .setAllowExpression(false)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition SITE =
            new SimpleAttributeDefinitionBuilder(ModelKeys.SITE, ModelType.STRING, true)
                    .setXmlName(Attribute.SITE.getLocalName())
                    .setAllowExpression(true)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition RACK =
            new SimpleAttributeDefinitionBuilder(ModelKeys.RACK, ModelType.STRING, true)
                    .setXmlName(Attribute.RACK.getLocalName())
                    .setAllowExpression(true)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition MACHINE =
            new SimpleAttributeDefinitionBuilder(ModelKeys.MACHINE, ModelType.STRING, true)
                    .setXmlName(Attribute.MACHINE.getLocalName())
                    .setAllowExpression(true)
                    .setFlags(AttributeAccess.Flag.RESTART_ALL_SERVICES)
                    .build();

    static SimpleAttributeDefinition PROPERTY = new SimpleAttributeDefinition(ModelKeys.PROPERTY, ModelType.PROPERTY, true);

    static SimpleListAttributeDefinition PROPERTIES = new SimpleListAttributeDefinition.Builder(ModelKeys.PROPERTIES, PROPERTY).
            setAllowNull(true).
            build();

    // the list of attributes used by the transport resource
    static AttributeDefinition[] TRANSPORT_ATTRIBUTES = new AttributeDefinition[] {TYPE, SHARED, SOCKET_BINDING, DIAGNOSTICS_SOCKET_BINDING, DEFAULT_EXECUTOR,
            OOB_EXECUTOR, TIMER_EXECUTOR, THREAD_FACTORY, SITE, RACK, MACHINE};

    // the list of parameters accepted by a /subsystem=jgroups/stack=X/transport=TRANSPORT:add() operation
    static AttributeDefinition[] TRANSPORT_PARAMETERS = new AttributeDefinition[] {TYPE, SHARED, SOCKET_BINDING, DIAGNOSTICS_SOCKET_BINDING, DEFAULT_EXECUTOR,
            OOB_EXECUTOR, TIMER_EXECUTOR, THREAD_FACTORY, SITE, RACK, MACHINE, PROPERTIES};

    // representation of the type of a single operation parameter TRANSPORT of type OBJECT holding transport attributes
    // If this type is defined in a resource bundle with prefix X, the type descriptions
    // should be of the form X.transport.type, X.transport.shared, etc.
    static final ObjectTypeAttributeDefinition TRANSPORT = ObjectTypeAttributeDefinition.
                Builder.of(ModelKeys.TRANSPORT, TRANSPORT_ATTRIBUTES).
                setAllowNull(true).
                setSuffix(null).
                //setSuffix("transport").
                build();

    // operations
    private static final OperationDefinition TRANSPORT_ADD_DEFINITION = new SimpleOperationDefinitionBuilder(ADD, JGroupsExtension.getResourceDescriptionResolver(ModelKeys.TRANSPORT))
        .setParameters(TRANSPORT_PARAMETERS)
        .build();

    static final OperationStepHandler TRANSPORT_ADD = new TransportLayerAdd(TRANSPORT_PARAMETERS);
    static final OperationStepHandler TRANSPORT_REMOVE = new TransportLayerRemove();
    static final TransportResourceDefinition INSTANCE = new TransportResourceDefinition();

    // registration
    TransportResourceDefinition() {
        super(TRANSPORT_PATH,
                JGroupsExtension.getResourceDescriptionResolver(ModelKeys.TRANSPORT),
                null,  //we register it manualy in #  registerOperations
                TRANSPORT_REMOVE);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        super.registerOperations(registration);
        registration.registerOperationHandler(TRANSPORT_ADD_DEFINITION, TRANSPORT_ADD);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration resourceRegistration) {
        super.registerAttributes(resourceRegistration);

        final OperationStepHandler writeHandler = new ReloadRequiredWriteAttributeHandler(TRANSPORT_ATTRIBUTES);
        for (AttributeDefinition attr : TRANSPORT_ATTRIBUTES) {
            resourceRegistration.registerReadWriteAttribute(attr, null, writeHandler);
        }
    }

    @Override
    public void registerChildren(ManagementResourceRegistration resourceRegistration) {
        super.registerChildren(resourceRegistration);
        resourceRegistration.registerSubModel(PropertyResourceDefinition.INSTANCE);
    }
}

File: server/integration/jgroups/src/test/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemTest.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat Middleware LLC, and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SUBSYSTEM;
import static org.junit.Assert.assertEquals;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.subsystem.test.KernelServices;
import org.jboss.as.subsystem.test.ModelDescriptionValidator.ValidationConfiguration;
import org.jboss.dmr.ModelNode;
import org.junit.Test;

/**
 *
 * @author <a href="kabir.khan@jboss.com">Kabir Khan</a>
 */
public class JGroupsSubsystemTest extends ClusteringSubsystemTest {

    public JGroupsSubsystemTest() {
        super(JGroupsExtension.SUBSYSTEM_NAME, new JGroupsExtension(), "subsystem-jgroups-test.xml");
        System.setProperty("infinispan.jgroups.subsystem.property", "/tmp");
    }

    @Override
    protected ValidationConfiguration getModelValidationConfiguration() {
        // use this configuration to report any exceptional cases for
        // DescriptionProviders
        return new ValidationConfiguration();
    }

    @Override
    protected Set<PathAddress> getIgnoredChildResourcesForRemovalTest() {
        // create a collection of resources in the test which are not removed by
        // a "remove" command
        // i.e. all resources of form
        // /subsystem=jgroups/stack=maximal/protocol=*

        String[] protocolList = { "MPING", "MERGE3", "FD_SOCK", "FD", "VERIFY_SUSPECT", "pbcast.NAKACK2", "UNICAST3",
                "ENCRYPT", "pbcast.STABLE", "pbcast.GMS", "UFC", "MFC", "FRAG2", "RSVP" };
        PathAddress subsystem = PathAddress.pathAddress(PathElement.pathElement(SUBSYSTEM,
                JGroupsExtension.SUBSYSTEM_NAME));
        PathAddress stack = subsystem.append(PathElement.pathElement(ModelKeys.STACK, "maximal"));
        List<PathAddress> addresses = new ArrayList<PathAddress>();
        for (String protocol : protocolList) {
            PathAddress ignoredChild = stack.append(PathElement.pathElement(ModelKeys.PROTOCOL, protocol));
            ;
            addresses.add(ignoredChild);
        }
        return new HashSet<PathAddress>(addresses);
    }

    @Override
    public void testSubsystem() throws Exception {
        // Don't test this
    }

    @Test
    public void testProtocolOrdering() throws Exception {
        String xml = getSubsystemXml();
        KernelServices kernel = super.installInController(xml);

        ModelNode model = kernel.readWholeModel().require("subsystem").require("jgroups").require("stack")
                .require("maximal");
        List<ModelNode> protocols = model.require("protocols").asList();
        Set<String> keys = model.get("protocol").keys();

        assertEquals(protocols.size(), keys.size());
        int i = 0;
        for (String key : keys) {
            String name = protocols.get(i).asString();
            assertEquals(key, name);
            i++;
        }
    }
}


File: server/integration/jgroups/src/test/java/org/jboss/as/clustering/jgroups/subsystem/JGroupsSubsystemTestCase.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2011, Red Hat Middleware LLC, and individual contributors
 * as indicated by the @author tags. See the copyright.txt file in the
 * distribution for a full listing of individual contributors.
 *
 * This is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation; either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this software; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA, or see the FSF site: http://www.fsf.org.
 */
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.*;

import java.util.Arrays;
import java.util.Collection;
import java.util.List;

import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.subsystem.test.KernelServices;
import org.jboss.as.subsystem.test.ModelDescriptionValidator.ValidationConfiguration;
import org.jboss.dmr.ModelNode;
import org.junit.Assert;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

/**
 *
 * @author <a href="kabir.khan@jboss.com">Kabir Khan</a>
 */
@RunWith(value = Parameterized.class)
public class JGroupsSubsystemTestCase extends ClusteringSubsystemTest {

   String xmlFile = null;
   int operations = 0;

   public JGroupsSubsystemTestCase(String xmlFile, int operations) {
      super(JGroupsExtension.SUBSYSTEM_NAME, new JGroupsExtension(), xmlFile);
      this.xmlFile = xmlFile;
      this.operations = operations;
   }

   @Parameters
   public static Collection<Object[]> data() {
      Object[][] data = new Object[][] {
            { "jgroups-1.2.xml", 22 },
            { "jgroups-7.0.xml", 24 },
      };
      return Arrays.asList(data);
   }

   @Override
   protected ValidationConfiguration getModelValidationConfiguration() {
      // use this configuration to report any exceptional cases for DescriptionProviders
      return new ValidationConfiguration();
   }

   /**
    * Tests that the xml is parsed into the correct operations
    */
   @Test
   public void testParseSubsystem() throws Exception {
      // Parse the subsystem xml into operations
      List<ModelNode> operations = super.parse(getSubsystemXml());

      /*
       * // print the operations System.out.println("List of operations"); for (ModelNode op :
       * operations) { System.out.println("operation = " + op.toString()); }
       */

      // Check that we have the expected number of operations
      // one for each resource instance
      Assert.assertEquals(this.operations, operations.size());

      // Check that each operation has the correct content
      ModelNode addSubsystem = operations.get(0);
      Assert.assertEquals(ADD, addSubsystem.get(OP).asString());
      PathAddress addr = PathAddress.pathAddress(addSubsystem.get(OP_ADDR));
      Assert.assertEquals(1, addr.size());
      PathElement element = addr.getElement(0);
      Assert.assertEquals(SUBSYSTEM, element.getKey());
      Assert.assertEquals(getMainSubsystemName(), element.getValue());
   }

   /**
    * Test that the model created from the xml looks as expected
    */
   @Test
   public void testInstallIntoController() throws Exception {
      // Parse the subsystem xml and install into the controller
      KernelServices services = createKernelServicesBuilder(null).setSubsystemXml(getSubsystemXml()).build();

      // Read the whole model and make sure it looks as expected
      ModelNode model = services.readWholeModel();

      //System.out.println("model = " + model.asString());

      Assert.assertTrue(model.get(SUBSYSTEM).hasDefined(getMainSubsystemName()));
   }

   /**
    * Starts a controller with a given subsystem xml and then checks that a second controller
    * started with the xml marshalled from the first one results in the same model
    */
   @Test
   public void testParseAndMarshalModel() throws Exception {
      // Parse the subsystem xml and install into the first controller

      KernelServices servicesA = createKernelServicesBuilder(null).setSubsystemXml(getSubsystemXml()).build();

      // Get the model and the persisted xml from the first controller
      ModelNode modelA = servicesA.readWholeModel();
      String marshalled = servicesA.getPersistedSubsystemXml();

      // Install the persisted xml from the first controller into a second controller
      KernelServices servicesB = createKernelServicesBuilder(null).setSubsystemXml(marshalled).build();
      ModelNode modelB = servicesB.readWholeModel();

      // Make sure the models from the two controllers are identical
      super.compare(modelA, modelB);
   }

   /**
    * Starts a controller with the given subsystem xml and then checks that a second controller
    * started with the operations from its describe action results in the same model
    */
   @Test
   public void testDescribeHandler() throws Exception {
      // Parse the subsystem xml and install into the first controller
      KernelServices servicesA = createKernelServicesBuilder(null).setSubsystemXml(getSubsystemXml()).build();
      // Get the model and the describe operations from the first controller
      ModelNode modelA = servicesA.readWholeModel();
      ModelNode describeOp = new ModelNode();
      describeOp.get(OP).set(DESCRIBE);
      describeOp.get(OP_ADDR).set(PathAddress.pathAddress(PathElement.pathElement(SUBSYSTEM, getMainSubsystemName())).toModelNode());
      List<ModelNode> operations = checkResultAndGetContents(servicesA.executeOperation(describeOp)).asList();

      // Install the describe options from the first controller into a second controller
      KernelServices servicesB = createKernelServicesBuilder(null).setBootOperations(operations).build();
      ModelNode modelB = servicesB.readWholeModel();

      // Make sure the models from the two controllers are identical
      super.compare(modelA, modelB);

   }

    @Override
    public void testSubsystem() throws Exception {
        //Skip
    }


}


File: server/integration/jgroups/src/test/java/org/jboss/as/clustering/jgroups/subsystem/OperationTestCaseBase.java
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.ADD;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.COMPOSITE;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.NAME;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OP_ADDR;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.READ_ATTRIBUTE_OPERATION;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.REMOVE;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.STEPS;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SUBSYSTEM;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.VALUE;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.WRITE_ATTRIBUTE_OPERATION;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.StringWriter;
import java.net.URISyntaxException;
import java.net.URL;

import org.jboss.as.clustering.jgroups.JGroupsMessages;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.subsystem.test.AbstractSubsystemTest;
import org.jboss.dmr.ModelNode;

/**
* Base test case for testing management operations.
*
* @author Richard Achmatowicz (c) 2011 Red Hat Inc.
*/
public class OperationTestCaseBase extends AbstractSubsystemTest {

    static final String SUBSYSTEM_XML_FILE = "subsystem-jgroups-test.xml" ;

    public OperationTestCaseBase() {
        super(JGroupsExtension.SUBSYSTEM_NAME, new JGroupsExtension());
    }

    protected static ModelNode getCompositeOperation(ModelNode[] operations) {
        // create the address of the cache
        ModelNode compositeOp = new ModelNode() ;
        compositeOp.get(OP).set(COMPOSITE);
        compositeOp.get(OP_ADDR).setEmptyList();
        // the operations to be performed
        for (ModelNode operation : operations) {
            compositeOp.get(STEPS).add(operation);
        }
        return compositeOp ;
    }

    protected static ModelNode getSubsystemAddOperation() {
        // create the address of the subsystem
        PathAddress subsystemAddress =  PathAddress.pathAddress(
                PathElement.pathElement(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME));
        ModelNode addOp = new ModelNode() ;
        addOp.get(OP).set(ADD);
        addOp.get(OP_ADDR).set(subsystemAddress.toModelNode());
        // required attributes
        addOp.get(ModelKeys.DEFAULT_STACK).set("maximal2");
        return addOp ;
    }

    protected static ModelNode getSubsystemReadOperation(String name) {
        // create the address of the subsystem
        PathAddress subsystemAddress =  PathAddress.pathAddress(
                PathElement.pathElement(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME));
        ModelNode readOp = new ModelNode() ;
        readOp.get(OP).set(READ_ATTRIBUTE_OPERATION);
        readOp.get(OP_ADDR).set(subsystemAddress.toModelNode());
        // required attributes
        readOp.get(NAME).set(name);
        return readOp ;
    }

    protected static ModelNode getSubsystemWriteOperation(String name, String value) {
        // create the address of the subsystem
        PathAddress subsystemAddress =  PathAddress.pathAddress(
                PathElement.pathElement(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME));
        ModelNode writeOp = new ModelNode() ;
        writeOp.get(OP).set(WRITE_ATTRIBUTE_OPERATION);
        writeOp.get(OP_ADDR).set(subsystemAddress.toModelNode());
        // required attributes
        writeOp.get(NAME).set(name);
        writeOp.get(VALUE).set(value);
        return writeOp ;
    }

    protected static ModelNode getProtocolStackAddOperation(String stackName) {
        // create the address of the cache
        PathAddress stackAddr = getProtocolStackAddress(stackName);
        ModelNode addOp = new ModelNode() ;
        addOp.get(OP).set(ADD);
        addOp.get(OP_ADDR).set(stackAddr.toModelNode());
        // required attributes
        // addOp.get(DEFAULT_CACHE).set("default");
        return addOp ;
    }

    protected static ModelNode getProtocolStackAddOperationWithParameters(String stackName) {
        ModelNode addOp = getProtocolStackAddOperation(stackName);
        // add optional TRANSPORT attribute
        ModelNode transport = new ModelNode();
        transport.get(ModelKeys.TYPE).set("UDP");
        addOp.get(ModelKeys.TRANSPORT).set(transport);
        // add optional PROTOCOLS attribute
        ModelNode protocolsList = new ModelNode();
        ModelNode mping = new ModelNode() ;
        mping.get(ModelKeys.TYPE).set("MPING");
        protocolsList.add(mping);
        ModelNode flush = new ModelNode() ;
        flush.get(ModelKeys.TYPE).set("pbcast.FLUSH");
        protocolsList.add(flush);
        addOp.get(ModelKeys.PROTOCOLS).set(protocolsList);
        return addOp ;
    }

    protected static ModelNode getProtocolStackRemoveOperation(String stackName) {
        // create the address of the cache
        PathAddress stackAddr = getProtocolStackAddress(stackName);
        ModelNode removeOp = new ModelNode() ;
        removeOp.get(OP).set(REMOVE);
        removeOp.get(OP_ADDR).set(stackAddr.toModelNode());
        return removeOp ;
    }

    protected static ModelNode getTransportAddOperation(String stackName, String protocolType) {
        // create the address of the cache
        PathAddress transportAddr = getTransportAddress(stackName);
        ModelNode addOp = new ModelNode() ;
        addOp.get(OP).set(ADD);
        addOp.get(OP_ADDR).set(transportAddr.toModelNode());
        // required attributes
        addOp.get(ModelKeys.TYPE).set(protocolType);
        return addOp ;
    }

    protected static ModelNode getTransportAddOperationWithProperties(String stackName, String protocolType) {
        ModelNode addOp = getTransportAddOperation(stackName, protocolType);
        // add optional PROPERTIES attribute
        ModelNode propertyList = new ModelNode();
        ModelNode propA = new ModelNode();
        propA.add("A","a");
        propertyList.add(propA);
        ModelNode propB = new ModelNode();
        propB.add("B","b");
        propertyList.add(propB);
        addOp.get(ModelKeys.PROPERTIES).set(propertyList);
        return addOp ;
    }

    protected static ModelNode getTransportRemoveOperation(String stackName, String protocolType) {
        // create the address of the cache
        PathAddress transportAddr = getTransportAddress(stackName);
        ModelNode removeOp = new ModelNode() ;
        removeOp.get(OP).set(REMOVE);
        removeOp.get(OP_ADDR).set(transportAddr.toModelNode());
        return removeOp ;
    }

    protected static ModelNode getTransportReadOperation(String stackName, String name) {
        // create the address of the subsystem
        PathAddress transportAddress = getTransportAddress(stackName);
        ModelNode readOp = new ModelNode() ;
        readOp.get(OP).set(READ_ATTRIBUTE_OPERATION);
        readOp.get(OP_ADDR).set(transportAddress.toModelNode());
        // required attributes
        readOp.get(NAME).set(name);
        return readOp ;
    }

    protected static ModelNode getTransportWriteOperation(String stackName, String name, String value) {
        // create the address of the subsystem
        PathAddress transportAddress = getTransportAddress(stackName);
        ModelNode writeOp = new ModelNode() ;
        writeOp.get(OP).set(WRITE_ATTRIBUTE_OPERATION);
        writeOp.get(OP_ADDR).set(transportAddress.toModelNode());
        // required attributes
        writeOp.get(NAME).set(name);
        writeOp.get(VALUE).set(value);
        return writeOp ;
    }

    protected static ModelNode getTransportPropertyReadOperation(String stackName, String propertyName) {
        // create the address of the subsystem
        PathAddress transportPropertyAddress = getTransportPropertyAddress(stackName, propertyName);
        ModelNode readOp = new ModelNode() ;
        readOp.get(OP).set(READ_ATTRIBUTE_OPERATION);
        readOp.get(OP_ADDR).set(transportPropertyAddress.toModelNode());
        // required attributes
        readOp.get(NAME).set(ModelKeys.VALUE);
        return readOp ;
    }

    protected static ModelNode getTransportPropertyWriteOperation(String stackName, String propertyName, String propertyValue) {
        // create the address of the subsystem
        PathAddress transportPropertyAddress = getTransportPropertyAddress(stackName, propertyName);
        ModelNode writeOp = new ModelNode() ;
        writeOp.get(OP).set(WRITE_ATTRIBUTE_OPERATION);
        writeOp.get(OP_ADDR).set(transportPropertyAddress.toModelNode());
        // required attributes
        writeOp.get(NAME).set(ModelKeys.VALUE);
        writeOp.get(VALUE).set(propertyValue);
        return writeOp ;
    }

    protected static ModelNode getProtocolAddOperation(String stackName, String protocolType) {
        // create the address of the cache
        PathAddress stackAddr = getProtocolStackAddress(stackName);
        ModelNode addOp = new ModelNode() ;
        addOp.get(OP).set("add-protocol");
        addOp.get(OP_ADDR).set(stackAddr.toModelNode());
        // required attributes
        addOp.get(ModelKeys.TYPE).set(protocolType);
        return addOp ;
    }

    protected static ModelNode getProtocolAddOperationWithProperties(String stackName, String protocolType) {
        ModelNode addOp = getProtocolAddOperation(stackName, protocolType);
        // add optional PROPERTIES attribute
        ModelNode propertyList = new ModelNode();
        ModelNode propA = new ModelNode();
        propA.add("A","a");
        propertyList.add(propA);
        ModelNode propB = new ModelNode();
        propB.add("B","b");
        propertyList.add(propB);
        addOp.get(ModelKeys.PROPERTIES).set(propertyList);
        return addOp ;
    }

    protected static ModelNode getProtocolReadOperation(String stackName, String protocolName, String name) {
        // create the address of the subsystem
        PathAddress protocolAddress = getProtocolAddress(stackName, protocolName);
        ModelNode readOp = new ModelNode() ;
        readOp.get(OP).set(READ_ATTRIBUTE_OPERATION);
        readOp.get(OP_ADDR).set(protocolAddress.toModelNode());
        // required attributes
        readOp.get(NAME).set(name);
        return readOp ;
    }

    protected static ModelNode getProtocolWriteOperation(String stackName, String protocolName, String name, String value) {
        // create the address of the subsystem
        PathAddress protocolAddress = getProtocolAddress(stackName, protocolName);
        ModelNode writeOp = new ModelNode() ;
        writeOp.get(OP).set(WRITE_ATTRIBUTE_OPERATION);
        writeOp.get(OP_ADDR).set(protocolAddress.toModelNode());
        // required attributes
        writeOp.get(NAME).set(name);
        writeOp.get(VALUE).set(value);
        return writeOp ;
    }

    protected static ModelNode getProtocolPropertyReadOperation(String stackName, String protocolName, String propertyName) {
        // create the address of the subsystem
        PathAddress transportPropertyAddress = getProtocolPropertyAddress(stackName, protocolName, propertyName);
        ModelNode readOp = new ModelNode() ;
        readOp.get(OP).set(READ_ATTRIBUTE_OPERATION);
        readOp.get(OP_ADDR).set(transportPropertyAddress.toModelNode());
        // required attributes
        readOp.get(NAME).set(ModelKeys.VALUE);
        return readOp ;
    }

    protected static ModelNode getProtocolPropertyWriteOperation(String stackName, String protocolName, String propertyName, String propertyValue) {
        // create the address of the subsystem
        PathAddress transportPropertyAddress = getProtocolPropertyAddress(stackName, protocolName, propertyName);
        ModelNode writeOp = new ModelNode() ;
        writeOp.get(OP).set(WRITE_ATTRIBUTE_OPERATION);
        writeOp.get(OP_ADDR).set(transportPropertyAddress.toModelNode());
        // required attributes
        writeOp.get(NAME).set(ModelKeys.VALUE);
        writeOp.get(VALUE).set(propertyValue);
        return writeOp ;
    }

    protected static ModelNode getProtocolRemoveOperation(String stackName, String protocolType) {
        // create the address of the cache
        PathAddress stackAddr = getProtocolStackAddress(stackName);
        ModelNode removeOp = new ModelNode() ;
        removeOp.get(OP).set("remove-protocol");
        removeOp.get(OP_ADDR).set(stackAddr.toModelNode());
        // required attributes
        removeOp.get(ModelKeys.TYPE).set(protocolType);
        return removeOp ;
    }

    protected static PathAddress getProtocolStackAddress(String stackName) {
        // create the address of the stack
        PathAddress stackAddr = PathAddress.pathAddress(
                PathElement.pathElement(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME),
                PathElement.pathElement("stack",stackName));
        return stackAddr ;
    }

    protected static PathAddress getTransportAddress(String stackName) {
        // create the address of the cache
        PathAddress protocolAddr = PathAddress.pathAddress(
                PathElement.pathElement(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME),
                PathElement.pathElement("stack",stackName),
                PathElement.pathElement("transport", "TRANSPORT"));
        return protocolAddr ;
    }

    protected static PathAddress getTransportPropertyAddress(String stackName, String propertyName) {
        // create the address of the cache
        PathAddress protocolAddr = PathAddress.pathAddress(
                PathElement.pathElement(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME),
                PathElement.pathElement("stack",stackName),
                PathElement.pathElement("transport", "TRANSPORT"),
                PathElement.pathElement("property", propertyName));
        return protocolAddr ;
    }

    protected static PathAddress getProtocolAddress(String stackName, String protocolType) {
        // create the address of the cache
        PathAddress protocolAddr = PathAddress.pathAddress(
                PathElement.pathElement(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME),
                PathElement.pathElement("stack",stackName),
                PathElement.pathElement("protocol", protocolType));
        return protocolAddr ;
    }

    protected static PathAddress getProtocolPropertyAddress(String stackName, String protocolType, String propertyName) {
        // create the address of the cache
        PathAddress protocolAddr = PathAddress.pathAddress(
                PathElement.pathElement(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME),
                PathElement.pathElement("stack",stackName),
                PathElement.pathElement("protocol", protocolType),
                PathElement.pathElement("property", propertyName));
        return protocolAddr ;
    }

    protected String getSubsystemXml() throws IOException {
        return getSubsystemXml(SUBSYSTEM_XML_FILE) ;
    }

    protected String getSubsystemXml(String xml_file) throws IOException {
        URL url = Thread.currentThread().getContextClassLoader().getResource(xml_file);
        if (url == null) {
            throw new IllegalStateException(JGroupsMessages.MESSAGES.notFound(xml_file));
        }
        try {
            BufferedReader reader = new BufferedReader(new FileReader(new File(url.toURI())));
            StringWriter writer = new StringWriter();
            try {
                String line = reader.readLine();
                while (line != null) {
                    writer.write(line);
                    line = reader.readLine();
                }
            } finally {
                reader.close();
            }
            return writer.toString();
        } catch (URISyntaxException e) {
            throw new IllegalStateException(e);
        }
    }
}

File: server/integration/jgroups/src/test/java/org/jboss/as/clustering/jgroups/subsystem/OperationsTestCase.java
package org.jboss.as.clustering.jgroups.subsystem;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.FAILURE_DESCRIPTION;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.OUTCOME;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.RESULT;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SUCCESS;

import org.jboss.as.subsystem.test.KernelServices;
import org.jboss.dmr.ModelNode;
import org.junit.Assert;
import org.junit.Ignore;
import org.junit.Test;

/**
* Test case for testing individual management operations.
*
* @author Richard Achmatowicz (c) 2011 Red Hat Inc.
*/
@Ignore
public class OperationsTestCase extends OperationTestCaseBase {

    // subsystem test operations
    static final ModelNode readSubsystemDefaultStackOp = getSubsystemReadOperation(ModelKeys.DEFAULT_STACK);
    static final ModelNode writeSubsystemDefaultStackOp = getSubsystemWriteOperation(ModelKeys.DEFAULT_STACK, "new-default");

    // stack test operations
    static final ModelNode addStackOp = getProtocolStackAddOperation("maximal2");
    // addStackOpWithParams calls the operation  below to check passing optional parameters
    //  /subsystem=jgroups/stack=maximal2:add(transport={type=UDP},protocols=[{type=MPING},{type=FLUSH}])
    static final ModelNode addStackOpWithParams = getProtocolStackAddOperationWithParameters("maximal2");
    static final ModelNode removeStackOp = getProtocolStackRemoveOperation("maximal2");

    // transport test operations
    static final ModelNode readTransportTypeOp = getTransportReadOperation("maximal", ModelKeys.TYPE);
    static final ModelNode readTransportRackOp = getTransportReadOperation("maximal", ModelKeys.RACK);
    static final ModelNode writeTransportRackOp = getTransportWriteOperation("maximal", ModelKeys.RACK, "new-rack");
    static final ModelNode readTransportPropertyOp = getTransportPropertyReadOperation("maximal", "enable_bundling");
    static final ModelNode writeTransportPropertyOp = getTransportPropertyWriteOperation("maximal", "enable_bundling", "false");

    static final ModelNode addTransportOp = getTransportAddOperation("maximal2", "UDP");
    // addTransportOpWithProps calls the operation below to check passing optional parameters
    //   /subsystem=jgroups/stack=maximal2/transport=UDP:add(properties=[{A=>a},{B=>b}])
    static final ModelNode addTransportOpWithProps = getTransportAddOperationWithProperties("maximal2", "UDP");
    static final ModelNode removeTransportOp = getTransportRemoveOperation("maximal2", "UDP");

    // protocol test operations
    static final ModelNode readProtocolTypeOp = getProtocolReadOperation("maximal", "MPING", ModelKeys.TYPE);
    static final ModelNode readProtocolSocketBindingOp = getProtocolReadOperation("maximal", "MPING", ModelKeys.SOCKET_BINDING);
    static final ModelNode writeProtocolSocketBindingOp = getProtocolWriteOperation("maximal", "MPING", ModelKeys.SOCKET_BINDING, "new-socket-binding");
    static final ModelNode readProtocolPropertyOp = getProtocolPropertyReadOperation("maximal", "MPING", "name");
    static final ModelNode writeProtocolPropertyOp = getProtocolPropertyWriteOperation("maximal", "MPING", "name", "new-value");

    static final ModelNode addProtocolOp = getProtocolAddOperation("maximal2", "MPING");
    // addProtocolOpWithProps calls the operation below to check passing optional parameters
    //   /subsystem=jgroups/stack=maximal2:add-protocol(type=MPING, properties=[{A=>a},{B=>b}])
    static final ModelNode addProtocolOpWithProps = getProtocolAddOperationWithProperties("maximal2", "MPING");
    static final ModelNode removeProtocolOp = getProtocolRemoveOperation("maximal2", "MPING");

    /*
     * Tests access to subsystem attributes
     */
    @Test
    public void testSubsystemReadWriteOperations() throws Exception {

        // Parse and install the XML into the controller
        String subsystemXml = getSubsystemXml() ;
        KernelServices servicesA = super.installInController(subsystemXml);

        // read the default stack
        ModelNode result = servicesA.executeOperation(readSubsystemDefaultStackOp);
        Assert.assertEquals(result.get(FAILURE_DESCRIPTION).asString(),SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("maximal", result.get(RESULT).asString());

        // write the default stack
        result = servicesA.executeOperation(writeSubsystemDefaultStackOp);
        Assert.assertEquals(result.get(FAILURE_DESCRIPTION).asString(),SUCCESS, result.get(OUTCOME).asString());

        // re-read the default stack
        result = servicesA.executeOperation(readSubsystemDefaultStackOp);
        Assert.assertEquals(result.get(FAILURE_DESCRIPTION).asString(),SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("new-default", result.get(RESULT).asString());
    }

    /*
     * Tests access to transport attributes
     */
    @Test
    public void testTransportReadWriteOperation() throws Exception {

        // Parse and install the XML into the controller
        String subsystemXml = getSubsystemXml() ;
        KernelServices servicesA = super.installInController(subsystemXml) ;

        // read the transport type attribute
        ModelNode result = servicesA.executeOperation(readTransportTypeOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("TCP", result.get(RESULT).asString());

        // read the transport rack attribute
        result = servicesA.executeOperation(readTransportRackOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("rack1", result.get(RESULT).asString());

        // write the rack attribute
        result = servicesA.executeOperation(writeTransportRackOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());

        // re-read the rack attribute
        result = servicesA.executeOperation(readTransportRackOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("new-rack", result.get(RESULT).asString());
    }

    @Test
    public void testTransportReadWriteWithParameters() throws Exception {
        // Parse and install the XML into the controller
        String subsystemXml = getSubsystemXml() ;
        KernelServices servicesA = super.installInController(subsystemXml) ;

        //Assert.assertTrue("Could not create services",servicesA.);
        // add a protocol stack specifying TRANSPORT and PROTOCOLS parameters
        ModelNode result = servicesA.executeOperation(addStackOpWithParams);
        Assert.assertEquals(result.get(FAILURE_DESCRIPTION).asString(),SUCCESS, result.get(OUTCOME).asString());

         // read the transport type attribute
        result = servicesA.executeOperation(readTransportTypeOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("TCP", result.get(RESULT).asString());

        // write the rack attribute
        result = servicesA.executeOperation(writeTransportRackOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());

        // re-read the rack attribute
        result = servicesA.executeOperation(readTransportRackOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("new-rack", result.get(RESULT).asString());
    }

    @Test
    public void testTransportPropertyReadWriteOperation() throws Exception {
        // Parse and install the XML into the controller
        String subsystemXml = getSubsystemXml() ;
        KernelServices servicesA = super.installInController(subsystemXml) ;

         // read the enable_bundling transport property
        ModelNode result = servicesA.executeOperation(readTransportPropertyOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("true", result.get(RESULT).asString());

        // write the enable_bundling transport property
        result = servicesA.executeOperation(writeTransportPropertyOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());

        // re-read the enable_bundling transport property
        result = servicesA.executeOperation(readTransportPropertyOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("false", result.get(RESULT).asString());
    }

    @Test
    public void testProtocolReadWriteOperation() throws Exception {
        // Parse and install the XML into the controller
        String subsystemXml = getSubsystemXml() ;
        KernelServices servicesA = super.installInController(subsystemXml) ;

        // add a protocol stack specifying TRANSPORT and PROTOCOLS parameters
        ModelNode result = servicesA.executeOperation(addStackOpWithParams);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());

         // read the transport type attribute
        result = servicesA.executeOperation(readProtocolTypeOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("MPING", result.get(RESULT).asString());

        // read the socket binding attribute
        result = servicesA.executeOperation(readProtocolSocketBindingOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("jgroups-mping", result.get(RESULT).asString());

        // write the attribute
        result = servicesA.executeOperation(writeProtocolSocketBindingOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());

        // re-read the attribute
        result = servicesA.executeOperation(readProtocolSocketBindingOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("new-socket-binding", result.get(RESULT).asString());
    }

    @Test
    public void testProtocolPropertyReadWriteOperation() throws Exception {
        // Parse and install the XML into the controller
        String subsystemXml = getSubsystemXml() ;
        KernelServices servicesA = super.installInController(subsystemXml) ;

         // read the name protocol property
        ModelNode result = servicesA.executeOperation(readProtocolPropertyOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("value", result.get(RESULT).asString());

        // write the property
        result = servicesA.executeOperation(writeProtocolPropertyOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());

        // re-read the property
        result = servicesA.executeOperation(readProtocolPropertyOp);
        Assert.assertEquals(SUCCESS, result.get(OUTCOME).asString());
        Assert.assertEquals("new-value", result.get(RESULT).asString());
    }

}