Refactoring Types: ['Move Class']
/java/org/jboss/as/clustering/controller/AddStepHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.jboss.as.clustering.controller;

import java.util.Arrays;
import java.util.Collection;
import java.util.EnumSet;
import java.util.LinkedList;
import java.util.List;

import org.jboss.as.controller.AbstractAddStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.descriptions.ResourceDescriptionResolver;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.registry.OperationEntry;
import org.jboss.as.controller.registry.Resource;
import org.jboss.dmr.ModelNode;

/**
 * Generic add operation step handler that delegates service installation/rollback to a {@link ResourceServiceHandler}.
 * @author Paul Ferraro
 */
public class AddStepHandler extends AbstractAddStepHandler implements Registration {

    private final ResourceDescriptionResolver resolver;
    private final ResourceServiceHandler handler;
    private final List<Attribute> attributes = new LinkedList<>();

    public AddStepHandler(ResourceDescriptionResolver resolver, ResourceServiceHandler handler) {
        this.resolver = resolver;
        this.handler = handler;
    }

    public <E extends Enum<E> & Attribute> AddStepHandler addAttributes(Class<E> enumClass) {
        return this.addAttributes(EnumSet.allOf(enumClass));
    }

    public AddStepHandler addAttributes(Attribute... attributes) {
        return this.addAttributes(Arrays.asList(attributes));
    }

    public AddStepHandler addAttributes(Collection<? extends Attribute> attributes) {
        this.attributes.addAll(attributes);
        return this;
    }

    @Override
    protected void populateModel(OperationContext context, ModelNode operation, Resource resource) throws  OperationFailedException {
        ModelNode model = resource.getModel();
        for (Attribute attribute : this.attributes) {
            attribute.getDefinition().validateAndSet(operation, model);
        }
    }

    @Override
    protected void performRuntime(OperationContext context, ModelNode operation, ModelNode model) throws OperationFailedException {
        this.handler.installServices(context, model);
    }

    @Override
    protected void rollbackRuntime(OperationContext context, ModelNode operation, Resource resource) {
        try {
            this.handler.removeServices(context, resource.getModel());
        } catch (OperationFailedException e) {
            throw new IllegalStateException(e);
        }
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        SimpleOperationDefinitionBuilder builder = new SimpleOperationDefinitionBuilder(ModelDescriptionConstants.ADD, this.resolver).withFlag(OperationEntry.Flag.RESTART_NONE);
        for (Attribute attribute : this.attributes) {
            builder.addParameter(attribute.getDefinition());
        }
        registration.registerOperationHandler(builder.build(), this);
    }
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/BoottimeAddStepHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.jboss.as.clustering.controller;

import java.util.Arrays;
import java.util.Collection;
import java.util.EnumSet;
import java.util.LinkedList;
import java.util.List;

import org.jboss.as.controller.AbstractBoottimeAddStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.descriptions.ResourceDescriptionResolver;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.registry.OperationEntry;
import org.jboss.as.controller.registry.Resource;
import org.jboss.dmr.ModelNode;

/**
 * Convenience extension of {@link AbstractBoottimeAddStepHandler} that that delegates service installation/rollback to a {@link ResourceServiceHandler}.
 * @author Paul Ferraro
 */
public class BoottimeAddStepHandler extends AbstractBoottimeAddStepHandler implements Registration {

    private final ResourceDescriptionResolver resolver;
    private final ResourceServiceHandler handler;
    private final List<Attribute> attributes = new LinkedList<>();

    public <E extends Enum<E> & Attribute> BoottimeAddStepHandler(ResourceDescriptionResolver resolver, ResourceServiceHandler handler) {
        this.resolver = resolver;
        this.handler = handler;
    }

    public <E extends Enum<E> & Attribute> BoottimeAddStepHandler addAttributes(Class<E> enumClass) {
        return this.addAttributes(EnumSet.allOf(enumClass));
    }

    public BoottimeAddStepHandler addAttributes(Attribute... attributes) {
        return this.addAttributes(Arrays.asList(attributes));
    }

    public BoottimeAddStepHandler addAttributes(Collection<? extends Attribute> attributes) {
        this.attributes.addAll(attributes);
        return this;
    }

    @Override
    protected void populateModel(OperationContext context, ModelNode operation, Resource resource) throws OperationFailedException {
        ModelNode model = resource.getModel();
        for (Attribute attribute : this.attributes) {
            attribute.getDefinition().validateAndSet(operation, model);
        }
    }

    @Override
    protected void performBoottime(OperationContext context, ModelNode operation, Resource resource) throws OperationFailedException {
        this.handler.installServices(context, resource.getModel());
    }

    @Override
    protected void rollbackRuntime(OperationContext context, ModelNode operation, Resource resource) {
        try {
            this.handler.removeServices(context, resource.getModel());
        } catch (OperationFailedException e) {
            throw new IllegalStateException(e);
        }
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        SimpleOperationDefinitionBuilder builder = new SimpleOperationDefinitionBuilder(ModelDescriptionConstants.ADD, this.resolver).withFlag(OperationEntry.Flag.RESTART_NONE);
        for (Attribute attribute : this.attributes) {
            builder.addParameter(attribute.getDefinition());
        }
        registration.registerOperationHandler(builder.build(), this);
    }
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/Metric.java
/*
 * JBoss, Home of Professional Open Source
 * Copyright 2014 Red Hat Inc. and/or its affiliates and other contributors
 * as indicated by the @author tags. All rights reserved.
 * See the copyright.txt in the distribution for a
 * full listing of individual contributors.
 *
 * This copyrighted material is made available to anyone wishing to use,
 * modify, copy, or redistribute it subject to the terms and conditions
 * of the GNU Lesser General Public License, v. 2.1.
 * This program is distributed in the hope that it will be useful, but WITHOUT A
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.
 * You should have received a copy of the GNU Lesser General Public License,
 * v.2.1 along with this distribution; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 * MA  02110-1301, USA.
 */
package org.jboss.as.clustering.controller;

/**
 * Interface to be implemented by metric enumerations.
 * @author Paul Ferraro
 * @param <C> metric context
 */
public interface Metric<C> extends Attribute, Executable<C> {
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/Registration.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.jboss.as.clustering.controller;

import org.jboss.as.controller.registry.ManagementResourceRegistration;

/**
 * Implemented by a resource artifact that can register itself.
 * @author Paul Ferraro
 */
public interface Registration {
    /**
     * Registers this object with a resource.
     * @param registration a registration for a management resource
     */
    void register(ManagementResourceRegistration registration);
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/ReloadRequiredAddStepHandler.java
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

package org.jboss.as.clustering.controller;

import java.util.Collection;

import org.jboss.as.controller.AbstractAddStepHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.registry.Resource;
import org.jboss.dmr.ModelNode;

/**
 * @author Paul Ferraro
 */
public class ReloadRequiredAddStepHandler extends AbstractAddStepHandler {

    public ReloadRequiredAddStepHandler(AttributeDefinition... attributes) {
        super(attributes);
    }

    public ReloadRequiredAddStepHandler(Collection<AttributeDefinition> attributes) {
        super(attributes);
    }

    @Override
    protected boolean requiresRuntime(OperationContext context) {
        return !context.isBooting() && super.requiresRuntime(context);
    }

    @Override
    protected void performRuntime(OperationContext context, ModelNode operation, Resource resource) {
        context.reloadRequired();
    }

    @Override
    protected void rollbackRuntime(OperationContext context, ModelNode operation, Resource resource) {
        context.revertReloadRequired();
    }
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/RemoveStepHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.jboss.as.clustering.controller;

import org.jboss.as.controller.AbstractRemoveStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.descriptions.ResourceDescriptionResolver;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.registry.OperationEntry;
import org.jboss.dmr.ModelNode;

/**
 * Generic remove operation step handler that delegates service removal/recovery to a dedicated {@link ResourceServiceHandler}
 * and recursively removes any child resources and their associated services.
 * @author Paul Ferraro
 */
public class RemoveStepHandler extends AbstractRemoveStepHandler implements Registration {

    private final ResourceDescriptionResolver resolver;
    private final ResourceServiceHandler handler;

    public RemoveStepHandler(ResourceDescriptionResolver resolver, ResourceServiceHandler handler) {
        this.resolver = resolver;
        this.handler = handler;
    }

    @Override
    protected void performRuntime(OperationContext context, ModelNode operation, ModelNode model) throws OperationFailedException {
        this.handler.removeServices(context, model);
    }

    @Override
    protected void recoverServices(OperationContext context, ModelNode operation, ModelNode model) throws OperationFailedException {
        this.handler.installServices(context, model);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerOperationHandler(new SimpleOperationDefinitionBuilder(ModelDescriptionConstants.REMOVE, this.resolver).withFlag(OperationEntry.Flag.RESTART_RESOURCE_SERVICES).build(), this);
    }
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/ResourceServiceBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.jboss.as.clustering.controller;

import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * Service builder that can be configured via a resource model.
 * @author Paul Ferraro
 */
public interface ResourceServiceBuilder<T> extends Builder<T> {

    /**
     * Configures this builder using the specified expression resolver and model.
     * @param resolver an expression resolver
     * @param model the resource model
     * @return the reference to this builder
     * @throws OperationFailedException if there was a failure reading the model
     */
    Builder<T> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException;
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/RestartParentAddHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.jboss.as.clustering.controller;

import java.util.Arrays;
import java.util.Collection;
import java.util.EnumSet;
import java.util.LinkedList;
import java.util.List;

import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.RestartParentResourceAddHandler;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.descriptions.ResourceDescriptionResolver;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.registry.OperationEntry;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceName;

/**
 * {@link RestartParentResourceAddHandler} that leverages a {@link ResourceServiceBuilderFactory} for service recreation.
 * @author Paul Ferraro
 */
public class RestartParentAddHandler<T> extends RestartParentResourceAddHandler implements Registration {

    private final ResourceDescriptionResolver resolver;
    private final ResourceServiceBuilderFactory<T> builderFactory;
    private final List<Attribute> attributes = new LinkedList<>();

    public RestartParentAddHandler(ResourceDescriptionResolver resolver, ResourceServiceBuilderFactory<T> builderFactory) {
        super(null);
        this.resolver = resolver;
        this.builderFactory = builderFactory;
    }

    public <E extends Enum<E> & Attribute> RestartParentAddHandler<T> addAttributes(Class<E> enumClass) {
        return this.addAttributes(EnumSet.allOf(enumClass));
    }

    public RestartParentAddHandler<T> addAttributes(Attribute... attributes) {
        return this.addAttributes(Arrays.asList(attributes));
    }

    public RestartParentAddHandler<T> addAttributes(Collection<? extends Attribute> attributes) {
        this.attributes.addAll(attributes);
        return this;
    }

    @Override
    protected void populateModel(ModelNode operation, ModelNode model) throws OperationFailedException {
        for (Attribute attribute : this.attributes) {
            attribute.getDefinition().validateAndSet(operation, model);
        }
    }

    @Override
    protected void recreateParentService(OperationContext context, PathAddress parentAddress, ModelNode parentModel) throws OperationFailedException {
        this.builderFactory.createBuilder(parentAddress).configure(context, parentModel).build(context.getServiceTarget()).install();
    }

    @Override
    protected ServiceName getParentServiceName(PathAddress parentAddress) {
        return this.builderFactory.createBuilder(parentAddress).getServiceName();
    }

    @Override
    protected PathAddress getParentAddress(PathAddress address) {
        return address.getParent();
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        SimpleOperationDefinitionBuilder builder = new SimpleOperationDefinitionBuilder(ModelDescriptionConstants.ADD, this.resolver).withFlag(OperationEntry.Flag.RESTART_NONE);
        for (Attribute attribute : this.attributes) {
            builder.addParameter(attribute.getDefinition());
        }
        registration.registerOperationHandler(builder.build(), this);
    }
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/RestartParentRemoveHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.jboss.as.clustering.controller;

import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.RestartParentResourceRemoveHandler;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.descriptions.ResourceDescriptionResolver;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.registry.OperationEntry;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceName;

/**
 * {@link RestartParentResourceRemoveHandler} that leverages a {@link ResourceServiceBuilderFactory} for service recreation.
 * @author Paul Ferraro
 */
public class RestartParentRemoveHandler<T> extends RestartParentResourceRemoveHandler implements Registration {

    private final ResourceDescriptionResolver resolver;
    private final ResourceServiceBuilderFactory<T> builderFactory;

    public RestartParentRemoveHandler(ResourceDescriptionResolver resolver, ResourceServiceBuilderFactory<T> builderFactory) {
        super(null);
        this.resolver = resolver;
        this.builderFactory = builderFactory;
    }

    @Override
    protected void recreateParentService(OperationContext context, PathAddress parentAddress, ModelNode parentModel) throws OperationFailedException {
        this.builderFactory.createBuilder(parentAddress).configure(context, parentModel).build(context.getServiceTarget()).install();
    }

    @Override
    protected ServiceName getParentServiceName(PathAddress parentAddress) {
        return this.builderFactory.createBuilder(parentAddress).getServiceName();
    }

    @Override
    protected PathAddress getParentAddress(PathAddress address) {
        return address.getParent();
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerOperationHandler(new SimpleOperationDefinitionBuilder(ModelDescriptionConstants.REMOVE, this.resolver).withFlag(OperationEntry.Flag.RESTART_RESOURCE_SERVICES).build(), this);
    }
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/validation/ModuleIdentifierValidator.java
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

package org.jboss.as.clustering.controller.validation;

import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.operations.validation.ModelTypeValidator;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;
import org.jboss.modules.ModuleIdentifier;

public class ModuleIdentifierValidator extends ModelTypeValidator {

    public ModuleIdentifierValidator(boolean nullable, boolean allowExpressions) {
        super(ModelType.STRING, nullable, allowExpressions);
    }

    @Override
    public void validateParameter(String parameterName, ModelNode value) throws OperationFailedException {
        super.validateParameter(parameterName, value);
        if (value.isDefined()) {
            String module = value.asString();
            try {
                ModuleIdentifier.fromString(module);
            } catch (IllegalArgumentException e) {
                throw new OperationFailedException(e.getMessage() + ": " + module, e);
            }
        }
    }
}


File: clustering/common/src/main/java/org/jboss/as/clustering/controller/validation/ParameterValidatorBuilder.java
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
package org.jboss.as.clustering.controller.validation;

import org.jboss.as.controller.operations.validation.ParameterValidator;

public interface ParameterValidatorBuilder {
    /**
     * Builds the validator.
     * @return a parameter validator
     */
    ParameterValidator build();
}


File: clustering/common/src/main/java/org/jboss/as/clustering/msc/ServiceContainerHelper.java
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

package org.jboss.as.clustering.msc;

import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceController.Mode;
import org.jboss.msc.service.ServiceController.State;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceRegistry;
import org.jboss.msc.service.StabilityMonitor;
import org.jboss.msc.service.StartException;

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;

/**
 * Helper methods for interacting with a modular service container.
 * @author Paul Ferraro
 * @author <a href="mailto:ropalka@redhat.com">Richard Opalka</a>
 */
public class ServiceContainerHelper {
    // Mapping of service controller mode changes that appropriate for toggling to a given controller state
    private static final Map<State, Map<Mode, Mode>> modeToggle = new EnumMap<>(State.class);
    static {
        Map<Mode, Mode> map = new EnumMap<>(Mode.class);
        map.put(Mode.NEVER, Mode.ACTIVE);
        map.put(Mode.ON_DEMAND, Mode.PASSIVE);
        modeToggle.put(State.UP, map);

        map = new EnumMap<>(Mode.class);
        map.put(Mode.ACTIVE, Mode.NEVER);
        map.put(Mode.PASSIVE, Mode.ON_DEMAND);
        modeToggle.put(State.DOWN, map);

        map = new EnumMap<>(Mode.class);
        for (Mode mode: EnumSet.complementOf(EnumSet.of(Mode.REMOVE))) {
            map.put(mode, Mode.REMOVE);
        }
        modeToggle.put(State.REMOVED, map);
    }

    /**
     * Returns the value of the specified service, if the service exists and is started.
     * @param registry the service registry
     * @param name the service name
     * @return the service value, if the service exists and is started, null otherwise
     */
    public static <T> T findValue(ServiceRegistry registry, ServiceName name) {
        ServiceController<T> service = findService(registry, name);
        return ((service != null) && (service.getState() == State.UP)) ? service.getValue() : null;
    }

    /**
     * Generics friendly version of {@link ServiceRegistry#getService(ServiceName)}
     * @param registry service registry
     * @param name service name
     * @return the service controller with the specified name, or null if the service does not exist
     */
    public static <T> ServiceController<T> findService(ServiceRegistry registry, ServiceName name) {
        return (ServiceController<T>) registry.getService(name);
    }

    /**
     * Generics friendly version of {@link ServiceRegistry#getRequiredService(ServiceName)}
     * @param registry service registry
     * @param name service name
     * @return the service controller with the specified name
     * @throws org.jboss.msc.ServiceNotFoundException if the service was not found
     */
    public static <T> ServiceController<T> getService(ServiceRegistry registry, ServiceName name) {
        return (ServiceController<T>) registry.getRequiredService(name);
    }

    /**
     * Returns the service value of the specified service, starting it if necessary.
     * @param controller a service controller
     * @return the service value of the specified service
     * @throws StartException if the specified service could not be started
     */
    public static <T> T getValue(ServiceController<T> controller) throws StartException {
        start(controller);
        return controller.getValue();
    }

    /**
     * Ensures the specified service is started.
     * @param controller a service controller
     * @throws StartException if the specified service could not be started
     */
    public static void start(final ServiceController<?> controller) throws StartException {
        transition(controller, State.UP);
    }

    /**
     * Ensures the specified service is stopped.
     * @param controller a service controller
     */
    public static void stop(ServiceController<?> controller) {
        try {
            transition(controller, State.DOWN);
        } catch (StartException e) {
            // This can't happen
            throw new IllegalStateException(e);
        }
    }

    /**
     * Ensures the specified service is removed.
     * @param controller a service controller
     */
    public static void remove(ServiceController<?> controller) {
        try {
            transition(controller, State.REMOVED);
        } catch (StartException e) {
            // This can't happen
            throw new IllegalStateException(e);
        }
    }

    private static void transition(final ServiceController<?> targetController, State targetState) throws StartException {
        // Short-circuit if the service is already at the target state
        if (targetController.getState() == targetState) return;

        final StabilityMonitor monitor = new StabilityMonitor();
        try {
            if (targetController.getSubstate().isRestState()) {
                // Force service to transition to desired state
                Mode targetMode = modeToggle.get(targetState).get(targetController.getMode());
                if (targetMode != null) {
                    targetController.setMode(targetMode);
                }
            }
            monitor.addController(targetController);
            monitor.awaitStability();
            if (targetState == State.UP) {
                StartException exception = targetController.getStartException();
                if (exception != null) {
                    throw exception;
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            monitor.removeController(targetController);
        }
    }

    private ServiceContainerHelper() {
        // Hide
    }
}


File: clustering/ejb/infinispan/src/main/java/org/wildfly/clustering/ejb/infinispan/InfinispanBeanManagerFactoryBuilderFactory.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2013, Red Hat, Inc., and individual contributors
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
package org.wildfly.clustering.ejb.infinispan;

import static java.security.AccessController.doPrivileged;

import java.security.PrivilegedAction;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.ThreadFactory;

import org.infinispan.Cache;
import org.jboss.as.server.deployment.Services;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.threads.JBossThreadFactory;
import org.wildfly.clustering.ee.infinispan.TransactionBatch;
import org.wildfly.clustering.ejb.BeanContext;
import org.wildfly.clustering.ejb.BeanManagerFactory;
import org.wildfly.clustering.ejb.BeanManagerFactoryBuilderConfiguration;
import org.wildfly.clustering.ejb.BeanManagerFactoryBuilderFactory;
import org.wildfly.clustering.infinispan.spi.service.CacheBuilder;
import org.wildfly.clustering.infinispan.spi.service.TemplateConfigurationBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.service.concurrent.CachedThreadPoolExecutorServiceBuilder;
import org.wildfly.clustering.service.concurrent.RemoveOnCancelScheduledExecutorServiceBuilder;
import org.wildfly.clustering.spi.CacheGroupServiceNameFactory;

/**
 * Builds an infinispan-based {@link BeanManagerFactory}.
 *
 * @author Paul Ferraro
 *
 * @param <G> the group identifier type
 * @param <I> the bean identifier type
 */
public class InfinispanBeanManagerFactoryBuilderFactory<G, I> implements BeanManagerFactoryBuilderFactory<G, I, TransactionBatch> {

    private static final ThreadFactory EXPIRATION_THREAD_FACTORY = createThreadFactory();
    private static final ThreadFactory EVICTION_THREAD_FACTORY = createThreadFactory();

    private static ThreadFactory createThreadFactory() {
        return doPrivileged(new PrivilegedAction<ThreadFactory>() {
            public ThreadFactory run() {
                return new JBossThreadFactory(new ThreadGroup(BeanEvictionScheduler.class.getSimpleName()), Boolean.FALSE, null, "%G - %t", null, null);
            }
        });
    }

    static String getCacheName(ServiceName deploymentUnitServiceName) {
        if (Services.JBOSS_DEPLOYMENT_SUB_UNIT.isParentOf(deploymentUnitServiceName)) {
            return deploymentUnitServiceName.getParent().getSimpleName() + "/" + deploymentUnitServiceName.getSimpleName();
        }
        return deploymentUnitServiceName.getSimpleName();
    }

    private final String name;
    private final BeanManagerFactoryBuilderConfiguration config;

    public InfinispanBeanManagerFactoryBuilderFactory(String name, BeanManagerFactoryBuilderConfiguration config) {
        this.name = name;
        this.config = config;
    }

    @Override
    public Collection<Builder<?>> getDeploymentBuilders(final ServiceName name) {
        String cacheName = getCacheName(name);
        String containerName = this.config.getContainerName();
        String templateCacheName = this.config.getCacheName();
        if (templateCacheName == null) {
            templateCacheName = CacheGroupServiceNameFactory.DEFAULT_CACHE;
        }

        List<Builder<?>> builders = new ArrayList<>(4);
        builders.add(new TemplateConfigurationBuilder(containerName, cacheName, templateCacheName));
        builders.add(new CacheBuilder<Object, Object>(containerName, cacheName) {
            @Override
            public ServiceBuilder<Cache<Object, Object>> build(ServiceTarget target) {
                return super.build(target).addDependency(name.append("marshalling"));
            }
        });
        builders.add(new RemoveOnCancelScheduledExecutorServiceBuilder(name.append(this.name, "expiration"), EXPIRATION_THREAD_FACTORY));
        builders.add(new CachedThreadPoolExecutorServiceBuilder(name.append(this.name, "eviction"), EVICTION_THREAD_FACTORY));
        return builders;
    }

    @Override
    public <T> Builder<? extends BeanManagerFactory<G, I, T, TransactionBatch>> getBeanManagerFactoryBuilder(BeanContext context) {
        return new InfinispanBeanManagerFactoryBuilder<>(this.name, context, this.config);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/DefaultCacheContainer.java
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

import java.util.LinkedHashSet;
import java.util.Set;

import org.infinispan.AdvancedCache;
import org.infinispan.Cache;
import org.infinispan.cache.impl.AbstractDelegatingAdvancedCache;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.global.GlobalConfiguration;
import org.infinispan.manager.DefaultCacheManager;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.manager.impl.AbstractDelegatingEmbeddedCacheManager;
import org.infinispan.notifications.Listener;
import org.wildfly.clustering.ee.Batch;
import org.wildfly.clustering.ee.Batcher;
import org.wildfly.clustering.infinispan.spi.CacheContainer;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceNameFactory;

/**
 * EmbeddedCacheManager decorator that overrides the default cache semantics of a cache manager.
 * @author Paul Ferraro
 */
public class DefaultCacheContainer extends AbstractDelegatingEmbeddedCacheManager implements CacheContainer {

    private final BatcherFactory batcherFactory;
    private final String defaultCacheName;

    public DefaultCacheContainer(GlobalConfiguration global, String defaultCacheName) {
        this(new DefaultCacheManager(global, null, false), defaultCacheName);
    }

    public DefaultCacheContainer(GlobalConfiguration global, Configuration config, String defaultCacheName) {
        this(new DefaultCacheManager(global, config, false), defaultCacheName);
    }

    public DefaultCacheContainer(EmbeddedCacheManager container, String defaultCacheName) {
        this(container, defaultCacheName, new InfinispanBatcherFactory());
    }

    public DefaultCacheContainer(EmbeddedCacheManager container, String defaultCacheName, BatcherFactory batcherFactory) {
        super(container);
        this.defaultCacheName = defaultCacheName;
        this.batcherFactory = batcherFactory;
    }

    @Override
    public String getDefaultCacheName() {
        return this.defaultCacheName;
    }

    @Override
    public Configuration defineConfiguration(String cacheName, Configuration configuration) {
        return this.cm.defineConfiguration(this.getCacheName(cacheName), configuration);
    }

    @Override
    public Configuration defineConfiguration(String cacheName, String templateCacheName, Configuration configurationOverride) {
        return this.cm.defineConfiguration(this.getCacheName(cacheName), this.getCacheName(templateCacheName), configurationOverride);
    }

    @Override
    public Configuration getDefaultCacheConfiguration() {
        return this.cm.getCacheConfiguration(this.defaultCacheName);
    }

    @Override
    public Configuration getCacheConfiguration(String name) {
        return this.cm.getCacheConfiguration(this.getCacheName(name));
    }

    /**
     * {@inheritDoc}
     * @see org.infinispan.manager.CacheContainer#getCache()
     */
    @Override
    public <K, V> Cache<K, V> getCache() {
        return this.getCache(this.defaultCacheName);
    }

    /**
     * {@inheritDoc}
     * @see org.infinispan.manager.CacheContainer#getCache(java.lang.String)
     */
    @Override
    public <K, V> Cache<K, V> getCache(String cacheName) {
        return this.getCache(cacheName, true);
    }

    /**
     * {@inheritDoc}
     * @see org.infinispan.manager.EmbeddedCacheManager#getCache(java.lang.String, boolean)
     */
    @Override
    public <K, V> Cache<K, V> getCache(String cacheName, boolean createIfAbsent) {
        Cache<K, V> cache = this.cm.<K, V>getCache(this.getCacheName(cacheName), createIfAbsent);
        return (cache != null) ? new DelegatingCache<>(this, this.batcherFactory, cache) : null;
    }

    /**
     * {@inheritDoc}
     * @see org.infinispan.manager.EmbeddedCacheManager#isDefaultRunning()
     */
    @Override
    public boolean isDefaultRunning() {
        return this.cm.isRunning(this.defaultCacheName);
    }

    /**
     * {@inheritDoc}
     * @see org.infinispan.manager.EmbeddedCacheManager#isRunning(String)
     */
    @Override
    public boolean isRunning(String cacheName) {
        return this.cm.isRunning(this.getCacheName(cacheName));
    }

    /**
     * {@inheritDoc}
     * @see org.infinispan.manager.EmbeddedCacheManager#cacheExists(java.lang.String)
     */
    @Override
    public boolean cacheExists(String cacheName) {
        return this.cm.cacheExists(this.getCacheName(cacheName));
    }

    /**
     * {@inheritDoc}
     * @see org.infinispan.manager.EmbeddedCacheManager#removeCache(java.lang.String)
     */
    @Override
    public void removeCache(String cacheName) {
        this.cm.removeCache(this.getCacheName(cacheName));
    }

    @Override
    public EmbeddedCacheManager startCaches(String... names) {
        Set<String> cacheNames = new LinkedHashSet<>();
        for (String name: names) {
            cacheNames.add(this.getCacheName(name));
        }
        this.cm.startCaches(cacheNames.toArray(new String[cacheNames.size()]));
        return this;
    }

    @Override
    public void addCacheDependency(String from, String to) {
        this.cm.addCacheDependency(this.getCacheName(from), this.getCacheName(to));
    }

    private String getCacheName(String name) {
        return ((name == null) || name.equals(CacheServiceNameFactory.DEFAULT_CACHE)) ? this.defaultCacheName : name;
    }

    /**
     * {@inheritDoc}
     * @see java.lang.Object#hashCode()
     */
    @Override
    public int hashCode() {
        return this.toString().hashCode();
    }

    /**
     * {@inheritDoc}
     * @see java.lang.Object#toString()
     */
    @Override
    public String toString() {
        return this.cm.getCacheManagerConfiguration().globalJmxStatistics().cacheManagerName();
    }

    private static class DelegatingCache<K, V> extends AbstractDelegatingAdvancedCache<K, V> {
        private static final ThreadLocal<Batch> CURRENT_BATCH = new ThreadLocal<>();
        private final EmbeddedCacheManager manager;
        private final Batcher<? extends Batch> batcher;

        DelegatingCache(final EmbeddedCacheManager manager, final BatcherFactory batcherFactory, AdvancedCache<K, V> cache) {
            super(cache, new AdvancedCacheWrapper<K, V>() {
                    @Override
                    public AdvancedCache<K, V> wrap(AdvancedCache<K, V> cache) {
                        return new DelegatingCache<>(manager, batcherFactory, cache);
                    }
                }
            );
            this.manager = manager;
            this.batcher = batcherFactory.createBatcher(cache);
        }

        DelegatingCache(EmbeddedCacheManager manager, BatcherFactory batcherFactory, Cache<K, V> cache) {
            this(manager, batcherFactory, cache.getAdvancedCache());
        }

        @Override
        public EmbeddedCacheManager getCacheManager() {
            return this.manager;
        }

        @Override
        public boolean startBatch() {
            if (this.batcher == null) return false;
            Batch batch = CURRENT_BATCH.get();
            if (batch != null) return false;
            CURRENT_BATCH.set(this.batcher.createBatch());
            return true;
        }

        @Override
        public void endBatch(boolean successful) {
            Batch batch = CURRENT_BATCH.get();
            if (batch != null) {
                try {
                    if (successful) {
                        batch.close();
                    } else {
                        batch.discard();
                    }
                } finally {
                    CURRENT_BATCH.remove();
                }
            }
        }

        // Workaround for https://hibernate.atlassian.net/browse/HHH-9337
        @Override
        public void removeListener(Object listener) {
            if (listener.getClass().isAnnotationPresent(Listener.class)) {
                super.removeListener(listener);
            }
        }

        @Override
        public boolean equals(Object object) {
            return (object == this) || (object == this.cache);
        }

        @Override
        public int hashCode() {
            return this.cache.hashCode();
        }
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/BackupForBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.BackupForResourceDefinition.Attribute.CACHE;
import static org.jboss.as.clustering.infinispan.subsystem.BackupForResourceDefinition.Attribute.SITE;

import org.infinispan.configuration.cache.BackupForConfiguration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * Builds a service that provides the {@link BackupForConfiguration} for a cache.
 * @author Paul Ferraro
 */
public class BackupForBuilder extends CacheComponentBuilder<BackupForConfiguration> implements ResourceServiceBuilder<BackupForConfiguration> {

    private volatile org.infinispan.configuration.cache.BackupForBuilder builder = new ConfigurationBuilder().sites().backupFor();

    BackupForBuilder(String containerName, String cacheName) {
        super(CacheComponent.BACKUP_FOR, containerName, cacheName);
    }

    @Override
    public Builder<BackupForConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        String site = ModelNodes.asString(SITE.getDefinition().resolveModelAttribute(resolver, model));
        if (site != null) {
            this.builder.remoteSite(site).remoteCache(CACHE.getDefinition().resolveModelAttribute(resolver, model).asString());
        }
        return this;
    }

    @Override
    public BackupForConfiguration getValue() {
        return this.builder.create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/BackupForResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.infinispan.commons.api.BasicCacheContainer;
import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Definition of the backup-for resource of a cache.
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Paul Ferraro
 */
public class BackupForResourceDefinition extends ComponentResourceDefinition {

    static final PathElement PATH = pathElement("backup-for");
    static final PathElement LEGACY_PATH = PathElement.pathElement(PATH.getValue(), "BACKUP_FOR");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        CACHE("remote-cache", ModelType.STRING, new ModelNode(BasicCacheContainer.DEFAULT_CACHE_NAME)),
        SITE("remote-site", ModelType.STRING, null),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        if (InfinispanModel.VERSION_4_0_0.requiresTransformation(version)) {
            parent.addChildRedirection(PATH, LEGACY_PATH);
        }
    }

    BackupForResourceDefinition() {
        super(PATH);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new BackupForBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/BackupResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.infinispan.configuration.cache.BackupConfiguration.BackupStrategy;
import org.infinispan.configuration.cache.BackupFailurePolicy;
import org.infinispan.configuration.cache.SitesConfiguration;
import org.jboss.as.clustering.controller.OperationHandler;
import org.jboss.as.clustering.controller.Registration;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.ResourceServiceBuilderFactory;
import org.jboss.as.clustering.controller.RestartParentAddHandler;
import org.jboss.as.clustering.controller.RestartParentRemoveHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.operations.validation.EnumValidator;
import org.jboss.as.controller.operations.validation.ParameterValidator;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Definition of a backup site resource.
 *
 * @author Paul Ferraro
 */
public class BackupResourceDefinition extends SimpleResourceDefinition implements Registration {

    static final PathElement WILDCARD_PATH = pathElement(PathElement.WILDCARD_VALUE);

    static PathElement pathElement(String name) {
        return PathElement.pathElement("backup", name);
    }

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        ENABLED("enabled", ModelType.BOOLEAN, new ModelNode(true), null),
        FAILURE_POLICY("failure-policy", ModelType.STRING, new ModelNode(BackupFailurePolicy.WARN.name()), new EnumValidator<>(BackupFailurePolicy.class, true, true)),
        STRATEGY("strategy", ModelType.STRING, new ModelNode(BackupStrategy.ASYNC.name()), new EnumValidator<>(BackupStrategy.class, true, true)),
        TAKE_OFFLINE_AFTER_FAILURES("after-failures", ModelType.INT, new ModelNode(1), null),
        TAKE_OFFLINE_MIN_WAIT("min-wait", ModelType.LONG, new ModelNode(0L), null),
        TIMEOUT("timeout", ModelType.LONG, new ModelNode(10000L), null),
        ;
        private final AttributeDefinition definition;

        private Attribute(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit((type == ModelType.LONG) ? MeasurementUnit.MILLISECONDS : null)
                    .setValidator(validator)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        // Nothing to transform
    }

    private final boolean runtimeRegistration;
    private final ResourceServiceBuilderFactory<SitesConfiguration> parentBuilderFactory;

    BackupResourceDefinition(ResourceServiceBuilderFactory<SitesConfiguration> parentBuilderFactory, boolean runtimeRegistration) {
        super(WILDCARD_PATH, new InfinispanResourceDescriptionResolver(WILDCARD_PATH));
        this.parentBuilderFactory = parentBuilderFactory;
        this.runtimeRegistration = runtimeRegistration;
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        new RestartParentAddHandler<>(this.getResourceDescriptionResolver(), this.parentBuilderFactory).addAttributes(Attribute.class).register(registration);
        new RestartParentRemoveHandler<>(this.getResourceDescriptionResolver(), this.parentBuilderFactory).register(registration);

        if (this.runtimeRegistration) {
            new OperationHandler<>(new BackupOperationExecutor(), BackupOperation.class).register(registration);
        }
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/BackupsBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.BackupResourceDefinition.Attribute.*;

import java.util.HashMap;
import java.util.Map;

import org.infinispan.configuration.cache.BackupConfiguration;
import org.infinispan.configuration.cache.BackupConfigurationBuilder;
import org.infinispan.configuration.cache.BackupFailurePolicy;
import org.infinispan.configuration.cache.BackupForConfiguration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.SitesConfiguration;
import org.infinispan.configuration.cache.SitesConfigurationBuilder;
import org.infinispan.configuration.cache.BackupConfiguration.BackupStrategy;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.value.InjectedValue;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class BackupsBuilder extends CacheComponentBuilder<SitesConfiguration> implements ResourceServiceBuilder<SitesConfiguration> {

    private final InjectedValue<BackupForConfiguration> backupFor = new InjectedValue<>();
    private final Map<String, BackupConfiguration> backups = new HashMap<>();

    private final String containerName;
    private final String cacheName;

    BackupsBuilder(String containerName, String cacheName) {
        super(CacheComponent.BACKUPS, containerName, cacheName);
        this.containerName = containerName;
        this.cacheName = cacheName;
    }

    @Override
    public ServiceBuilder<SitesConfiguration> build(ServiceTarget target) {
        return super.build(target).addDependency(CacheComponent.BACKUP_FOR.getServiceName(this.containerName, this.cacheName), BackupForConfiguration.class, this.backupFor);
    }

    @Override
    public Builder<SitesConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.backups.clear();
        if (model.hasDefined(BackupResourceDefinition.WILDCARD_PATH.getKey())) {
            SitesConfigurationBuilder builder = new ConfigurationBuilder().sites();
            for (Property property : model.get(BackupResourceDefinition.WILDCARD_PATH.getKey()).asPropertyList()) {
                String siteName = property.getName();
                ModelNode backup = property.getValue();
                BackupConfigurationBuilder backupBuilder = builder.addBackup();
                backupBuilder.site(siteName)
                        .enabled(ENABLED.getDefinition().resolveModelAttribute(resolver, backup).asBoolean())
                        .backupFailurePolicy(ModelNodes.asEnum(FAILURE_POLICY.getDefinition().resolveModelAttribute(resolver, backup), BackupFailurePolicy.class))
                        .replicationTimeout(TIMEOUT.getDefinition().resolveModelAttribute(resolver, backup).asLong())
                        .strategy(ModelNodes.asEnum(STRATEGY.getDefinition().resolveModelAttribute(resolver, backup), BackupStrategy.class))
                        .takeOffline()
                            .afterFailures(TAKE_OFFLINE_AFTER_FAILURES.getDefinition().resolveModelAttribute(resolver, backup).asInt())
                            .minTimeToWait(TAKE_OFFLINE_MIN_WAIT.getDefinition().resolveModelAttribute(resolver, backup).asLong())
                ;
                this.backups.put(siteName, backupBuilder.create());
            }
        }
        return this;
    }

    @Override
    public SitesConfiguration getValue() {
        SitesConfigurationBuilder builder = new ConfigurationBuilder().sites();
        builder.backupFor().read(this.backupFor.getValue());
        builder.disableBackups(this.backups.isEmpty());
        for (Map.Entry<String, BackupConfiguration> backup : this.backups.entrySet()) {
            builder.addBackup().read(backup.getValue());
            builder.addInUseBackupSite(backup.getKey());
        }
        return builder.create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/BackupsResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.infinispan.configuration.cache.SitesConfiguration;
import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ParentResourceServiceHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceBuilderFactory;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.PathAddressTransformer;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;

/**
 * @author Paul Ferraro
 */
public class BackupsResourceDefinition extends ComponentResourceDefinition {

    static final PathElement PATH = pathElement("backups");

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        PathAddressTransformer addressTransformer = new PathAddressTransformer() {
            @Override
            public PathAddress transform(PathElement current, Builder builder) {
                return builder.next();
            }
        };
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, addressTransformer) : parent.addChildResource(PATH);

        BackupResourceDefinition.buildTransformation(version, builder);
    }

    private final ResourceServiceBuilderFactory<SitesConfiguration> builderFactory = new BackupsBuilderFactory();
    private final boolean runtimeRegistration;

    public BackupsResourceDefinition(boolean runtimeRegistration) {
        super(PATH);
        this.runtimeRegistration = runtimeRegistration;
    }

    @Override
    public void registerChildren(ManagementResourceRegistration registration) {
        new BackupResourceDefinition(this.builderFactory, this.runtimeRegistration).register(registration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new ParentResourceServiceHandler<>(this.builderFactory);
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/BinaryKeyedJDBCStoreResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.Operations;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.ObjectTypeAttributeDefinition;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.operations.global.ReadResourceHandler;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;

/**
 * Definition of a binary JDBC cache store resource.
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Paul Ferraro
 */
public class BinaryKeyedJDBCStoreResourceDefinition extends JDBCStoreResourceDefinition {

    static final PathElement LEGACY_PATH = PathElement.pathElement("binary-keyed-jdbc-store", "BINARY_KEYED_JDBC_STORE");
    static final PathElement PATH = pathElement("binary-jdbc");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        @Deprecated TABLE("binary-keyed-table", BinaryTableResourceDefinition.Attribute.values(), TableResourceDefinition.Attribute.values(), TableResourceDefinition.ColumnAttribute.values()),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, org.jboss.as.clustering.controller.Attribute[]... attributeSets) {
            int size = 0;
            for (org.jboss.as.clustering.controller.Attribute[] attributes : attributeSets) {
                size += attributes.length;
            }
            List<AttributeDefinition> definitions = new ArrayList<>(size);
            for (org.jboss.as.clustering.controller.Attribute[] attributes : attributeSets) {
                for (org.jboss.as.clustering.controller.Attribute attribute : attributes) {
                    definitions.add(attribute.getDefinition());
                }
            }
            this.definition = ObjectTypeAttributeDefinition.Builder.of(name, definitions.toArray(new AttributeDefinition[size]))
                    .setAllowNull(true)
                    .setDeprecated(InfinispanModel.VERSION_4_0_0.getVersion())
                    .setSuffix("table")
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildResource(PATH) : parent.addChildRedirection(PATH, LEGACY_PATH);

        JDBCStoreResourceDefinition.buildTransformation(version, builder);

        BinaryTableResourceDefinition.buildTransformation(version, builder);
    }

    BinaryKeyedJDBCStoreResourceDefinition(boolean allowRuntimeOnlyRegistration) {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH, pathElement("jdbc"), WILDCARD_PATH), allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerOperations(final ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new BinaryKeyedJDBCStoreBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler) {
            @Override
            public void execute(OperationContext context, ModelNode operation) throws OperationFailedException {
                super.execute(context, operation);
                if (operation.hasDefined(Attribute.TABLE.getDefinition().getName())) {
                    // Translate deprecated TABLE attribute into separate add table operation
                    ModelNode addTableOperation = Util.createAddOperation(context.getCurrentAddress().append(BinaryTableResourceDefinition.PATH));
                    ModelNode parameters = operation.get(Attribute.TABLE.getDefinition().getName());
                    for (Property parameter : parameters.asPropertyList()) {
                        addTableOperation.get(parameter.getName()).set(parameter.getValue());
                    }
                    context.addStep(addTableOperation, registration.getOperationHandler(PathAddress.pathAddress(BinaryTableResourceDefinition.PATH), ModelDescriptionConstants.ADD), context.getCurrentStage());
                }
            }
        }.addAttributes(JDBCStoreResourceDefinition.Attribute.class).addAttributes(StoreResourceDefinition.Attribute.class).register(registration);
        this.registerRemoveOperation(registration, new RemoveStepHandler(this.getResourceDescriptionResolver(), handler));
    }

    static final OperationStepHandler LEGACY_READ_TABLE_HANDLER = new OperationStepHandler() {
        @Override
        public void execute(OperationContext context, ModelNode operation) throws OperationFailedException {
            PathAddress address = context.getCurrentAddress().append(BinaryTableResourceDefinition.PATH);
            ModelNode readResourceOperation = Util.createOperation(ModelDescriptionConstants.READ_RESOURCE_OPERATION, address);
            operation.get(ModelDescriptionConstants.ATTRIBUTES_ONLY).set(true);
            context.addStep(readResourceOperation, new ReadResourceHandler(), context.getCurrentStage());
        }
    };

    static final OperationStepHandler LEGACY_WRITE_TABLE_HANDLER = new OperationStepHandler() {
        @Override
        public void execute(OperationContext context, ModelNode operation) throws OperationFailedException {
            PathAddress address = context.getCurrentAddress().append(BinaryTableResourceDefinition.PATH);
            ModelNode table = Operations.getAttributeValue(operation);
            for (Class<? extends org.jboss.as.clustering.controller.Attribute> attributeClass : Arrays.asList(BinaryTableResourceDefinition.Attribute.class, TableResourceDefinition.Attribute.class)) {
                for (org.jboss.as.clustering.controller.Attribute attribute : attributeClass.getEnumConstants()) {
                    ModelNode writeAttributeOperation = Operations.createWriteAttributeOperation(address, attribute, table.get(attribute.getDefinition().getName()));
                    context.addStep(writeAttributeOperation, new ReloadRequiredWriteAttributeHandler(attribute), context.getCurrentStage());
                }
            }
        }
    };

    @Override
    public void registerChildren(ManagementResourceRegistration registration) {
        super.registerChildren(registration);
        new BinaryTableResourceDefinition().register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);
        registration.registerReadWriteAttribute(Attribute.TABLE.getDefinition(), LEGACY_READ_TABLE_HANDLER, LEGACY_WRITE_TABLE_HANDLER);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/BinaryTableResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Definition of a binary table resource.
 * @author Paul Ferraro
 */
public class BinaryTableResourceDefinition extends TableResourceDefinition {

    static final PathElement PATH = pathElement("binary");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        PREFIX("prefix", ModelType.STRING, new ModelNode("ispn_bucket")),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        // Nothing to transform yet
    }

    BinaryTableResourceDefinition() {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH, WILDCARD_PATH));
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new BinaryTableBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).addAttributes(TableResourceDefinition.Attribute.class).addAttributes(TableResourceDefinition.ColumnAttribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CacheComponent.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.jboss.as.controller.PathElement;
import org.jboss.msc.service.ServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceNameFactory;

/**
 * Enumerates the configurable cache components
 * @author Paul Ferraro
 */
public enum CacheComponent implements CacheServiceNameFactory {

    EVICTION(EvictionResourceDefinition.PATH),
    EXPIRATION(ExpirationResourceDefinition.PATH),
    INDEXING(IndexingResourceDefinition.PATH),
    LOCKING(LockingResourceDefinition.PATH),
    PERSISTENCE(StoreResourceDefinition.WILDCARD_PATH),
    STATE_TRANSFER(StateTransferResourceDefinition.PATH),
    STORE_WRITE(StoreWriteResourceDefinition.WILDCARD_PATH),
    TRANSACTION(TransactionResourceDefinition.PATH),
    BINARY_TABLE(StoreResourceDefinition.WILDCARD_PATH, BinaryTableResourceDefinition.PATH),
    STRING_TABLE(StoreResourceDefinition.WILDCARD_PATH, StringTableResourceDefinition.PATH),
    BACKUPS(BackupResourceDefinition.WILDCARD_PATH),
    BACKUP_FOR(BackupForResourceDefinition.PATH),
    ;

    private final String[] components;

    CacheComponent(PathElement... paths) {
        this.components = new String[paths.length];
        for (int i = 0; i < paths.length; ++i) {
            PathElement path = paths[i];
            this.components[i] = path.isWildcard() ? path.getKey() : path.getValue();
        }
    }

    @Override
    public ServiceName getServiceName(String container) {
        return this.getServiceName(container, DEFAULT_CACHE);
    }

    @Override
    public ServiceName getServiceName(String container, String cache) {
        return CacheServiceName.CONFIGURATION.getServiceName(container, cache).append(this.components);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CacheConfigurationBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.CacheResourceDefinition.Attribute.*;

import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.EvictionConfiguration;
import org.infinispan.configuration.cache.ExpirationConfiguration;
import org.infinispan.configuration.cache.IndexingConfiguration;
import org.infinispan.configuration.cache.JMXStatisticsConfiguration;
import org.infinispan.configuration.cache.LockingConfiguration;
import org.infinispan.configuration.cache.PersistenceConfiguration;
import org.infinispan.configuration.cache.TransactionConfiguration;
import org.infinispan.configuration.global.GlobalConfiguration;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.server.Services;
import org.jboss.dmr.ModelNode;
import org.jboss.modules.ModuleIdentifier;
import org.jboss.modules.ModuleLoadException;
import org.jboss.modules.ModuleLoader;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.value.InjectedValue;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceName;
import org.wildfly.clustering.infinispan.spi.service.ConfigurationBuilderFactory;
import org.wildfly.clustering.service.Builder;

/**
 * Builds a cache configuration from its components.
 * @author Paul Ferraro
 */
public class CacheConfigurationBuilder implements ResourceServiceBuilder<Configuration>, ConfigurationBuilderFactory {

    private final InjectedValue<EvictionConfiguration> eviction = new InjectedValue<>();
    private final InjectedValue<ExpirationConfiguration> expiration = new InjectedValue<>();
    private final InjectedValue<IndexingConfiguration> indexing = new InjectedValue<>();
    private final InjectedValue<LockingConfiguration> locking = new InjectedValue<>();
    private final InjectedValue<PersistenceConfiguration> persistence = new InjectedValue<>();
    private final InjectedValue<TransactionConfiguration> transaction = new InjectedValue<>();
    private final InjectedValue<GlobalConfiguration> global = new InjectedValue<>();
    private final InjectedValue<ModuleLoader> loader = new InjectedValue<>();

    private final String containerName;
    private final String cacheName;

    private volatile JMXStatisticsConfiguration statistics;
    private volatile ModuleIdentifier module;

    CacheConfigurationBuilder(String containerName, String cacheName) {
        this.containerName = containerName;
        this.cacheName = cacheName;
    }

    @Override
    public ServiceName getServiceName() {
        return CacheServiceName.CONFIGURATION.getServiceName(this.containerName, this.cacheName);
    }

    @Override
    public ServiceBuilder<Configuration> build(ServiceTarget target) {
        return new org.wildfly.clustering.infinispan.spi.service.ConfigurationBuilder(this.containerName, this.cacheName, this).build(target)
                .addDependency(CacheComponent.EVICTION.getServiceName(this.containerName, this.cacheName), EvictionConfiguration.class, this.eviction)
                .addDependency(CacheComponent.EXPIRATION.getServiceName(this.containerName, this.cacheName), ExpirationConfiguration.class, this.expiration)
                .addDependency(CacheComponent.INDEXING.getServiceName(this.containerName, this.cacheName), IndexingConfiguration.class, this.indexing)
                .addDependency(CacheComponent.LOCKING.getServiceName(this.containerName, this.cacheName), LockingConfiguration.class, this.locking)
                .addDependency(CacheComponent.PERSISTENCE.getServiceName(this.containerName, this.cacheName), PersistenceConfiguration.class, this.persistence)
                .addDependency(CacheComponent.TRANSACTION.getServiceName(this.containerName, this.cacheName), TransactionConfiguration.class, this.transaction)
                .addDependency(CacheContainerServiceName.CONFIGURATION.getServiceName(this.containerName), GlobalConfiguration.class, this.global)
                .addDependency(Services.JBOSS_SERVICE_MODULE_LOADER, ModuleLoader.class, this.loader)
        ;
    }

    @Override
    public Builder<Configuration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.module = ModelNodes.asModuleIdentifier(MODULE.getDefinition().resolveModelAttribute(resolver, model));
        this.statistics = new ConfigurationBuilder().jmxStatistics().enabled(STATISTICS_ENABLED.getDefinition().resolveModelAttribute(resolver, model).asBoolean()).create();
        return this;
    }

    @Override
    public ConfigurationBuilder createConfigurationBuilder() {
        ConfigurationBuilder builder = new ConfigurationBuilder();

        EvictionConfiguration eviction = this.eviction.getValue();
        ExpirationConfiguration expiration = this.expiration.getValue();
        IndexingConfiguration indexing = this.indexing.getValue();
        LockingConfiguration locking = this.locking.getValue();
        PersistenceConfiguration persistence = this.persistence.getValue();
        TransactionConfiguration transaction = this.transaction.getValue();

        builder.eviction().read(eviction);
        builder.expiration().read(expiration);
        builder.indexing().read(indexing);
        builder.locking().read(locking);
        builder.persistence().read(persistence);
        builder.transaction().read(transaction);
        builder.jmxStatistics().read(this.statistics);

        return builder;
    }

    ClassLoader getClassLoader() {
        if (this.module != null) {
            try {
                return this.loader.getValue().loadModule(this.module).getClassLoader();
            } catch (ModuleLoadException e) {
                throw new IllegalArgumentException(e);
            }
        }
        return this.global.getValue().classLoader();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CacheContainerBuilder.java
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

import static org.jboss.as.clustering.infinispan.subsystem.CacheContainerResourceDefinition.Attribute.*;

import java.util.LinkedList;
import java.util.List;

import org.infinispan.configuration.global.GlobalConfiguration;
import org.infinispan.notifications.Listener;
import org.infinispan.notifications.cachemanagerlistener.annotation.CacheStarted;
import org.infinispan.notifications.cachemanagerlistener.annotation.CacheStopped;
import org.infinispan.notifications.cachemanagerlistener.event.CacheStartedEvent;
import org.infinispan.notifications.cachemanagerlistener.event.CacheStoppedEvent;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.clustering.infinispan.DefaultCacheContainer;
import org.jboss.as.clustering.infinispan.InfinispanLogger;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.Service;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.service.StartContext;
import org.jboss.msc.service.StopContext;
import org.jboss.msc.value.InjectedValue;
import org.wildfly.clustering.infinispan.spi.CacheContainer;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
@Listener
public class CacheContainerBuilder implements ResourceServiceBuilder<CacheContainer>, Service<CacheContainer> {

    private final InjectedValue<GlobalConfiguration> configuration = new InjectedValue<>();
    private final List<String> aliases = new LinkedList<>();
    private final String name;

    private volatile String defaultCache;
    private volatile CacheContainer container;

    public CacheContainerBuilder(String name) {
        this.name = name;
    }

    @Override
    public ServiceName getServiceName() {
        return CacheContainerServiceName.CACHE_CONTAINER.getServiceName(this.name);
    }

    @Override
    public Builder<CacheContainer> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.aliases.clear();
        this.aliases.addAll(ModelNodes.asStringList(ALIASES.getDefinition().resolveModelAttribute(resolver, model)));
        return this;
    }

    @Override
    public ServiceBuilder<CacheContainer> build(ServiceTarget target) {
        ServiceBuilder<CacheContainer> builder = target.addService(this.getServiceName(), this)
                .addDependency(CacheContainerServiceName.CONFIGURATION.getServiceName(this.name), GlobalConfiguration.class, this.configuration)
        ;
        for (String alias : this.aliases) {
            builder.addAliases(CacheContainerServiceName.CACHE_CONTAINER.getServiceName(alias));
        }
        return builder.setInitialMode(ServiceController.Mode.ON_DEMAND);
    }

    CacheContainerBuilder setDefaultCache(String defaultCache) {
        this.defaultCache = defaultCache;
        return this;
    }

    @Override
    public CacheContainer getValue() {
        return this.container;
    }

    @Override
    public void start(StartContext context) {
        GlobalConfiguration config = this.configuration.getValue();
        this.container = new DefaultCacheContainer(config, this.defaultCache);
        this.container.addListener(this);
        this.container.start();
        InfinispanLogger.ROOT_LOGGER.debugf("%s cache container started", this.name);
    }

    @Override
    public void stop(StopContext context) {
        if ((this.container != null) && this.container.getStatus().allowInvocations()) {
            this.container.stop();
            this.container.removeListener(this);
            InfinispanLogger.ROOT_LOGGER.debugf("%s cache container stopped", this.name);
        }
    }

    @CacheStarted
    public void cacheStarted(CacheStartedEvent event) {
        InfinispanLogger.ROOT_LOGGER.cacheStarted(event.getCacheName(), this.name);
    }

    @CacheStopped
    public void cacheStopped(CacheStoppedEvent event) {
        InfinispanLogger.ROOT_LOGGER.cacheStopped(event.getCacheName(), this.name);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CacheContainerComponent.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.jboss.as.controller.PathElement;
import org.jboss.msc.service.ServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceNameFactory;

/**
 * @author Paul Ferraro
 */
public enum CacheContainerComponent implements CacheContainerServiceNameFactory {

    SITE("site"),
    TRANSPORT(JGroupsTransportResourceDefinition.PATH),
    ;
    private final String component;

    CacheContainerComponent(PathElement path) {
        this(path.getKey());
    }

    private CacheContainerComponent(String component) {
        this.component = component;
    }

    @Override
    public ServiceName getServiceName(String container) {
        return CacheContainerServiceName.CONFIGURATION.getServiceName(container).append(this.component);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CacheContainerResourceDefinition.java
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
package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.AttributeParsers;
import org.jboss.as.clustering.controller.MetricHandler;
import org.jboss.as.clustering.controller.Operations;
import org.jboss.as.clustering.controller.Registration;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.transform.OperationTransformer;
import org.jboss.as.clustering.controller.transform.SimpleOperationTransformer;
import org.jboss.as.clustering.controller.validation.ModuleIdentifierValidator;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationDefinition;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleOperationDefinitionBuilder;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.StringListAttributeDefinition;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.operations.global.ListOperations;
import org.jboss.as.controller.operations.validation.EnumValidator;
import org.jboss.as.controller.operations.validation.ParameterValidator;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.services.path.PathManager;
import org.jboss.as.controller.transform.description.DiscardAttributeChecker;
import org.jboss.as.controller.transform.description.RejectAttributeChecker;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Paul Ferraro
 */
public class CacheContainerResourceDefinition extends SimpleResourceDefinition implements Registration {

    static final PathElement WILDCARD_PATH = pathElement(PathElement.WILDCARD_VALUE);

    static PathElement pathElement(String containerName) {
        return PathElement.pathElement("cache-container", containerName);
    }

    static final AttributeDefinition ALIAS = new SimpleAttributeDefinitionBuilder(ModelDescriptionConstants.NAME, ModelType.STRING)
            .setAllowExpression(false)
            .build();

    static final OperationDefinition ALIAS_ADD = new SimpleOperationDefinitionBuilder("add-alias", new InfinispanResourceDescriptionResolver(WILDCARD_PATH))
            .setParameters(ALIAS)
            .setDeprecated(InfinispanModel.VERSION_3_0_0.getVersion())
            .build();

    static final OperationDefinition ALIAS_REMOVE = new SimpleOperationDefinitionBuilder("remove-alias", new InfinispanResourceDescriptionResolver(WILDCARD_PATH))
            .setParameters(ALIAS)
            .setDeprecated(InfinispanModel.VERSION_3_0_0.getVersion())
            .build();

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        ALIASES("aliases"),
        MODULE("module", ModelType.STRING, new ModelNode("org.jboss.as.clustering.infinispan"), new ModuleIdentifierValidator(true, true)),
        DEFAULT_CACHE("default-cache", ModelType.STRING, null, null),
        @Deprecated EVICTION_EXECUTOR("eviction-executor", ModelType.STRING, null, null, InfinispanModel.VERSION_3_0_0),
        JNDI_NAME("jndi-name", ModelType.STRING, null, null),
        @Deprecated LISTENER_EXECUTOR("listener-executor", ModelType.STRING, null, null, InfinispanModel.VERSION_3_0_0),
        @Deprecated REPLICATION_QUEUE_EXECUTOR("replication-queue-executor", ModelType.STRING, null, null, InfinispanModel.VERSION_3_0_0),
        @Deprecated START("start", ModelType.STRING, new ModelNode(StartMode.LAZY.name()), new EnumValidator<>(StartMode.class, true, true), InfinispanModel.VERSION_3_0_0),
        STATISTICS_ENABLED("statistics-enabled", ModelType.BOOLEAN, new ModelNode(false), null),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator) {
            this.definition = createBuilder(name, type, defaultValue, validator).build();
        }

        Attribute(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator, InfinispanModel deprecation) {
            this.definition = createBuilder(name, type, defaultValue, validator).setDeprecated(deprecation.getVersion()).build();
        }

        private static SimpleAttributeDefinitionBuilder createBuilder(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator) {
            return new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setValidator(validator)
            ;
        }

        Attribute(String name) {
            this.definition = new StringListAttributeDefinition.Builder(name)
                    .setAllowNull(true)
                    .setAttributeParser(AttributeParsers.COLLECTION)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = parent.addChildResource(WILDCARD_PATH);

        if (InfinispanModel.VERSION_4_0_0.requiresTransformation(version)) {
            builder.discardChildResource(NoTransportResourceDefinition.PATH);
        } else {
            NoTransportResourceDefinition.buildTransformation(version, builder);
        }

        if (InfinispanModel.VERSION_3_0_0.requiresTransformation(version)) {
            OperationTransformer addAliasTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    String attributeName = Operations.getAttributeName(operation);
                    if (Attribute.ALIASES.getDefinition().getName().equals(attributeName)) {
                        ModelNode value = Operations.getAttributeValue(operation);
                        PathAddress address = Operations.getPathAddress(operation);
                        ModelNode transformedOperation = Util.createOperation(ALIAS_ADD, address);
                        transformedOperation.get(ALIAS.getName()).set(value);
                        return transformedOperation;
                    }
                    return operation;
                }
            };
            builder.addRawOperationTransformationOverride(ListOperations.LIST_ADD_DEFINITION.getName(), new SimpleOperationTransformer(addAliasTransformer));

            OperationTransformer removeAliasTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    String attributeName = Operations.getAttributeName(operation);
                    if (Attribute.ALIASES.getDefinition().getName().equals(attributeName)) {
                        ModelNode value = Operations.getAttributeValue(operation);
                        PathAddress address = Operations.getPathAddress(operation);
                        ModelNode transformedOperation = Util.createOperation(ALIAS_REMOVE, address);
                        transformedOperation.get(ALIAS.getName()).set(value);
                        return transformedOperation;
                    }
                    return operation;
                }
            };
            builder.addRawOperationTransformationOverride(ListOperations.LIST_REMOVE_DEFINITION.getName(), new SimpleOperationTransformer(removeAliasTransformer));
        }

        if (InfinispanModel.VERSION_1_5_0.requiresTransformation(version)) {
            builder.getAttributeBuilder()
                    // discard statistics if set to true, reject otherwise
                    .setDiscard(new DiscardAttributeChecker.DiscardAttributeValueChecker(false, false, new ModelNode(true)), Attribute.STATISTICS_ENABLED.getDefinition())
                    .addRejectCheck(RejectAttributeChecker.UNDEFINED, Attribute.STATISTICS_ENABLED.getDefinition())
                    .addRejectCheck(RejectAttributeChecker.SIMPLE_EXPRESSIONS, Attribute.STATISTICS_ENABLED.getDefinition())
                    .addRejectCheck(new RejectAttributeChecker.SimpleRejectAttributeChecker(new ModelNode(false)), Attribute.STATISTICS_ENABLED.getDefinition());
        }

        JGroupsTransportResourceDefinition.buildTransformation(version, builder);

        DistributedCacheResourceDefinition.buildTransformation(version, builder);
        ReplicatedCacheResourceDefinition.buildTransformation(version, builder);
        InvalidationCacheResourceDefinition.buildTransformation(version, builder);
        LocalCacheResourceDefinition.buildTransformation(version, builder);
    }

    private final PathManager pathManager;
    private final boolean allowRuntimeOnlyRegistration;

    CacheContainerResourceDefinition(PathManager pathManager, boolean allowRuntimeOnlyRegistration) {
        super(WILDCARD_PATH, new InfinispanResourceDescriptionResolver(WILDCARD_PATH));
        this.pathManager = pathManager;
        this.allowRuntimeOnlyRegistration = allowRuntimeOnlyRegistration;
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);

        if (this.allowRuntimeOnlyRegistration) {
            new MetricHandler<>(new CacheContainerMetricExecutor(), CacheContainerMetric.class).register(registration);
        }
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new CacheContainerServiceHandler();
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);

        // Translate legacy add-alias operation to list-add operation
        OperationStepHandler addAliasHandler = new OperationStepHandler() {
            @Override
            public void execute(OperationContext context, ModelNode legacyOperation) {
                String value = legacyOperation.get(ALIAS.getName()).asString();
                ModelNode operation = Operations.createListAddOperation(context.getCurrentAddress(), Attribute.ALIASES, value);
                context.addStep(operation, ListOperations.LIST_ADD_HANDLER, context.getCurrentStage());
            }
        };
        registration.registerOperationHandler(ALIAS_ADD, addAliasHandler);

        // Translate legacy remove-alias operation to list-remove operation
        OperationStepHandler removeAliasHandler = new OperationStepHandler() {
            @Override
            public void execute(OperationContext context, ModelNode legacyOperation) throws OperationFailedException {
                String value = legacyOperation.get(ALIAS.getName()).asString();
                ModelNode operation = Operations.createListRemoveOperation(context.getCurrentAddress(), Attribute.ALIASES, value);
                context.addStep(operation, ListOperations.LIST_REMOVE_HANDLER, context.getCurrentStage());
            }
        };
        registration.registerOperationHandler(ALIAS_REMOVE, removeAliasHandler);
    }

    @Override
    public void registerChildren(ManagementResourceRegistration registration) {
        new JGroupsTransportResourceDefinition().register(registration);
        new NoTransportResourceDefinition().register(registration);

        new LocalCacheResourceDefinition(this.pathManager, this.allowRuntimeOnlyRegistration).register(registration);
        new InvalidationCacheResourceDefinition(this.pathManager, this.allowRuntimeOnlyRegistration).register(registration);
        new ReplicatedCacheResourceDefinition(this.pathManager, this.allowRuntimeOnlyRegistration).register(registration);
        new DistributedCacheResourceDefinition(this.pathManager, this.allowRuntimeOnlyRegistration).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CacheContainerServiceHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.CacheContainerResourceDefinition.Attribute.*;

import java.util.ServiceLoader;

import org.infinispan.Cache;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.registry.Resource;
import org.jboss.as.naming.deployment.ContextNames;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceTarget;
import org.wildfly.clustering.infinispan.spi.CacheContainer;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceNameFactory;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceNameFactory;
import org.wildfly.clustering.service.AliasServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.CacheGroupAliasBuilderProvider;

/**
 * @author Paul Ferraro
 */
public class CacheContainerServiceHandler implements ResourceServiceHandler {

    @Override
    public void installServices(OperationContext context, ModelNode model) throws OperationFailedException {
        String name = context.getCurrentAddressValue();

        // Handle case where ejb subsystem has already installed services for this cache-container
        // This can happen if the ejb cache-container is added to a running server
        if (context.getProcessType().isServer() && !context.isBooting() && name.equals("ejb")) {
            Resource rootResource = context.readResourceFromRoot(PathAddress.EMPTY_ADDRESS);
            PathElement ejbPath = PathElement.pathElement(ModelDescriptionConstants.SUBSYSTEM, "ejb3");
            if (rootResource.hasChild(ejbPath) && rootResource.getChild(ejbPath).hasChild(PathElement.pathElement("service", "remote"))) {
                // Following restart, these services will be installed by this handler, rather than the ejb remote handler
                context.addStep(new OperationStepHandler() {
                    @Override
                    public void execute(final OperationContext context, final ModelNode operation) throws OperationFailedException {
                        context.reloadRequired();
                        context.completeStep(OperationContext.RollbackHandler.REVERT_RELOAD_REQUIRED_ROLLBACK_HANDLER);
                    }
                }, OperationContext.Stage.RUNTIME);
                return;
            }
        }

        ServiceTarget target = context.getServiceTarget();

        new GlobalConfigurationBuilder(name).configure(context, model).build(target).install();

        String defaultCache = ModelNodes.asString(DEFAULT_CACHE.getDefinition().resolveModelAttribute(context, model));
        new CacheContainerBuilder(name).setDefaultCache(defaultCache).configure(context, model).build(target).install();

        new KeyAffinityServiceFactoryBuilder(name).build(target).install();

        String jndiName = ModelNodes.asString(CacheContainerResourceDefinition.Attribute.JNDI_NAME.getDefinition().resolveModelAttribute(context, model));
        BinderServiceBuilder<?> bindingBuilder = new BinderServiceBuilder<>(InfinispanBindingFactory.createCacheContainerBinding(name), CacheContainerServiceName.CACHE_CONTAINER.getServiceName(name), CacheContainer.class);
        if (jndiName != null) {
            bindingBuilder.alias(ContextNames.bindInfoFor(JndiNameFactory.parse(jndiName).getAbsoluteName()));
        }
        bindingBuilder.build(target).install();

        if ((defaultCache != null) && !defaultCache.equals(CacheServiceNameFactory.DEFAULT_CACHE)) {
            for (CacheServiceNameFactory nameFactory : CacheServiceName.values()) {
                new AliasServiceBuilder<>(nameFactory.getServiceName(name), nameFactory.getServiceName(name, defaultCache), Object.class).build(target).install();
            }

            new BinderServiceBuilder<>(InfinispanBindingFactory.createCacheBinding(name, CacheServiceNameFactory.DEFAULT_CACHE), CacheServiceName.CACHE.getServiceName(name), Cache.class).build(target).install();

            for (CacheGroupAliasBuilderProvider provider : ServiceLoader.load(CacheGroupAliasBuilderProvider.class, CacheGroupAliasBuilderProvider.class.getClassLoader())) {
                for (Builder<?> builder : provider.getBuilders(name, CacheServiceNameFactory.DEFAULT_CACHE, defaultCache)) {
                    builder.build(target).install();
                }
            }
        }
    }

    @Override
    public void removeServices(OperationContext context, ModelNode model) throws OperationFailedException {
        String name = context.getCurrentAddressValue();

        String defaultCache = ModelNodes.asString(CacheContainerResourceDefinition.Attribute.DEFAULT_CACHE.getDefinition().resolveModelAttribute(context, model));
        if ((defaultCache != null) && !defaultCache.equals(CacheServiceNameFactory.DEFAULT_CACHE)) {
            for (CacheGroupAliasBuilderProvider provider : ServiceLoader.load(CacheGroupAliasBuilderProvider.class, CacheGroupAliasBuilderProvider.class.getClassLoader())) {
                for (Builder<?> builder : provider.getBuilders(name, CacheServiceNameFactory.DEFAULT_CACHE, defaultCache)) {
                    context.removeService(builder.getServiceName());
                }
            }

            context.removeService(new BinderServiceBuilder<>(InfinispanBindingFactory.createCacheBinding(name, CacheServiceNameFactory.DEFAULT_CACHE), CacheServiceName.CACHE.getServiceName(name), Cache.class).getServiceName());

            for (CacheServiceNameFactory nameFactory : CacheServiceName.values()) {
                context.removeService(nameFactory.getServiceName(name));
            }
        }

        context.removeService(InfinispanBindingFactory.createCacheContainerBinding(name).getBinderServiceName());

        for (CacheContainerServiceNameFactory factory : CacheContainerServiceName.values()) {
            context.removeService(factory.getServiceName(name));
        }
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CacheServiceHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import java.util.ServiceLoader;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.Configuration;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.ResourceServiceBuilderFactory;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.naming.deployment.ContextNames;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceTarget;
import org.wildfly.clustering.infinispan.spi.service.CacheBuilder;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceNameFactory;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.CacheGroupBuilderProvider;

/**
 * @author Paul Ferraro
 */
public class CacheServiceHandler implements ResourceServiceHandler {

    private final ResourceServiceBuilderFactory<Configuration> builderFactory;
    private final Class<? extends CacheGroupBuilderProvider> providerClass;

    CacheServiceHandler(ResourceServiceBuilderFactory<Configuration> builderFactory, Class<? extends CacheGroupBuilderProvider> providerClass) {
        this.builderFactory = builderFactory;
        this.providerClass = providerClass;
    }

    @Override
    public void installServices(OperationContext context, ModelNode model) throws OperationFailedException {
        PathAddress cacheAddress = context.getCurrentAddress();
        PathAddress containerAddress = cacheAddress.getParent();

        String containerName = containerAddress.getLastElement().getValue();
        String cacheName = cacheAddress.getLastElement().getValue();

        ServiceTarget target = context.getServiceTarget();

        this.builderFactory.createBuilder(cacheAddress).configure(context, model).build(target).install();

        new CacheBuilder<>(containerName, cacheName).build(target).install();
        new XAResourceRecoveryBuilder(containerName, cacheName).build(target).install();

        BinderServiceBuilder<?> bindingBuilder = new BinderServiceBuilder<>(InfinispanBindingFactory.createCacheBinding(containerName, cacheName), CacheServiceName.CACHE.getServiceName(containerName, cacheName), Cache.class);
        String jndiName = ModelNodes.asString(CacheResourceDefinition.Attribute.JNDI_NAME.getDefinition().resolveModelAttribute(context, model));
        if (jndiName != null) {
            bindingBuilder.alias(ContextNames.bindInfoFor(JndiNameFactory.parse(jndiName).getAbsoluteName()));
        }
        bindingBuilder.build(target).install();

        for (CacheGroupBuilderProvider provider : ServiceLoader.load(this.providerClass, this.providerClass.getClassLoader())) {
            for (Builder<?> builder : provider.getBuilders(containerName, cacheName)) {
                builder.build(target).install();
            }
        }
    }

    @Override
    public void removeServices(OperationContext context, ModelNode model) {
        PathAddress cacheAddress = context.getCurrentAddress();
        PathAddress containerAddress = cacheAddress.getParent();

        String containerName = containerAddress.getLastElement().getValue();
        String cacheName = cacheAddress.getLastElement().getValue();

        for (CacheGroupBuilderProvider provider : ServiceLoader.load(this.providerClass, this.providerClass.getClassLoader())) {
            for (Builder<?> builder : provider.getBuilders(containerName, cacheName)) {
                context.removeService(builder.getServiceName());
            }
        }

        context.removeService(InfinispanBindingFactory.createCacheBinding(containerName, cacheName).getBinderServiceName());

        for (CacheServiceNameFactory factory : CacheServiceName.values()) {
            context.removeService(factory.getServiceName(containerName, cacheName));
        }

        context.removeService(this.builderFactory.createBuilder(cacheAddress).getServiceName());
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/ClusteredCacheBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.ClusteredCacheResourceDefinition.Attribute.ASYNC_MARSHALLING;
import static org.jboss.as.clustering.infinispan.subsystem.ClusteredCacheResourceDefinition.Attribute.QUEUE_FLUSH_INTERVAL;
import static org.jboss.as.clustering.infinispan.subsystem.ClusteredCacheResourceDefinition.Attribute.QUEUE_SIZE;
import static org.jboss.as.clustering.infinispan.subsystem.ClusteredCacheResourceDefinition.Attribute.REMOTE_TIMEOUT;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ClusteringConfiguration;
import org.infinispan.configuration.cache.ClusteringConfigurationBuilder;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * Builds the configuration of a clustered cache.
 * @author Paul Ferraro
 */
public class ClusteredCacheBuilder extends CacheConfigurationBuilder {

    private final CacheMode mode;

    private volatile ClusteringConfiguration clustering;

    ClusteredCacheBuilder(String containerName, String cacheName, CacheMode mode) {
        super(containerName, cacheName);
        this.mode = mode;
    }

    @Override
    public Builder<Configuration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        Mode mode = ModelNodes.asEnum(ClusteredCacheResourceDefinition.Attribute.MODE.getDefinition().resolveModelAttribute(resolver, model), Mode.class);
        ClusteringConfigurationBuilder builder = new ConfigurationBuilder().clustering().cacheMode(mode.apply(this.mode));

        if (mode.isSynchronous()) {
            builder.sync().replTimeout(REMOTE_TIMEOUT.getDefinition().resolveModelAttribute(resolver, model).asLong());
        } else {
            int queueSize = QUEUE_SIZE.getDefinition().resolveModelAttribute(resolver, model).asInt();

            builder.async()
                    .asyncMarshalling(ASYNC_MARSHALLING.getDefinition().resolveModelAttribute(resolver, model).asBoolean())
                    .useReplQueue(queueSize > 0)
                    .replQueueInterval(QUEUE_FLUSH_INTERVAL.getDefinition().resolveModelAttribute(resolver, model).asLong())
                    .replQueueMaxElements(queueSize)
            ;
        }
        this.clustering = builder.create();

        return super.configure(resolver, model);
    }

    @Override
    public ConfigurationBuilder createConfigurationBuilder() {
        ConfigurationBuilder builder = super.createConfigurationBuilder();
        builder.clustering().read(this.clustering);
        return builder;
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/CustomStoreResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/cache=Y/store=STORE
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class CustomStoreResourceDefinition extends StoreResourceDefinition {

    static final PathElement LEGACY_PATH = PathElement.pathElement("store", "STORE");
    static final PathElement PATH = pathElement("custom");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        CLASS("class", ModelType.STRING)
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, LEGACY_PATH) : parent.addChildResource(PATH);

        StoreResourceDefinition.buildTransformation(version, builder);
    }

    CustomStoreResourceDefinition(boolean allowRuntimeOnlyRegistration) {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH, WILDCARD_PATH), allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new CustomStoreBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).addAttributes(StoreResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/DistributedCacheBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.DistributedCacheResourceDefinition.Attribute.*;

import java.util.ServiceLoader;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.GroupsConfigurationBuilder;
import org.infinispan.configuration.cache.HashConfiguration;
import org.infinispan.configuration.global.GlobalConfiguration;
import org.infinispan.distribution.group.Grouper;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.value.InjectedValue;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.service.Builder;

/**
 * Builds the configuration for a distributed cache.
 * @author Paul Ferraro
 */
public class DistributedCacheBuilder extends SharedStateCacheBuilder {

    private final InjectedValue<GlobalConfiguration> container = new InjectedValue<>();
    private final String containerName;

    private volatile HashConfiguration hash;
    private volatile ConsistentHashStrategy consistentHashStrategy;

    DistributedCacheBuilder(String containerName, String cacheName) {
        super(containerName, cacheName, CacheMode.DIST_SYNC);
        this.containerName = containerName;
    }

    @Override
    public ServiceBuilder<Configuration> build(ServiceTarget target) {
        return super.build(target).addDependency(CacheContainerServiceName.CONFIGURATION.getServiceName(this.containerName), GlobalConfiguration.class, this.container);
    }

    @Override
    public Builder<Configuration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.consistentHashStrategy = ModelNodes.asEnum(CONSISTENT_HASH_STRATEGY.getDefinition().resolveModelAttribute(resolver, model), ConsistentHashStrategy.class);
        long l1Lifespan = L1_LIFESPAN.getDefinition().resolveModelAttribute(resolver, model).asLong();
        this.hash = new ConfigurationBuilder().clustering().hash()
                .capacityFactor(CAPACITY_FACTOR.getDefinition().resolveModelAttribute(resolver, model).asInt())
                .numOwners(OWNERS.getDefinition().resolveModelAttribute(resolver, model).asInt())
                .numSegments(SEGMENTS.getDefinition().resolveModelAttribute(resolver, model).asInt())
                .l1().enabled(l1Lifespan > 0).lifespan(l1Lifespan)
                .hash().create();
        return super.configure(resolver, model);
    }

    @Override
    public ConfigurationBuilder createConfigurationBuilder() {
        ConfigurationBuilder builder = super.createConfigurationBuilder();
        GroupsConfigurationBuilder groupsBuilder = builder.clustering().hash().read(this.hash)
                .consistentHashFactory(this.consistentHashStrategy.createConsistentHashFactory(this.container.getValue().transport().hasTopologyInfo()))
                .groups().enabled();
        for (Grouper<?> grouper: ServiceLoader.load(Grouper.class, this.getClassLoader())) {
            groupsBuilder.addGrouper(grouper);
        }
        return builder;
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/DistributedCacheResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.validation.DoubleRangeValidatorBuilder;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.operations.validation.EnumValidator;
import org.jboss.as.controller.operations.validation.IntRangeValidator;
import org.jboss.as.controller.operations.validation.ParameterValidator;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.services.path.PathManager;
import org.jboss.as.controller.transform.description.DiscardAttributeChecker;
import org.jboss.as.controller.transform.description.RejectAttributeChecker;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/distributed-cache=*
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Radoslav Husar
 */
public class DistributedCacheResourceDefinition extends SharedStateCacheResourceDefinition {

    static final PathElement WILDCARD_PATH = pathElement(PathElement.WILDCARD_VALUE);
    static PathElement pathElement(String name) {
        return PathElement.pathElement("distributed-cache", name);
    }

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        CAPACITY_FACTOR("capacity-factor", ModelType.DOUBLE, new ModelNode(1.0f), new DoubleRangeValidatorBuilder().lowerBound(0).upperBound(Float.MAX_VALUE).build()),
        CONSISTENT_HASH_STRATEGY("consistent-hash-strategy", ModelType.STRING, new ModelNode(ConsistentHashStrategy.INTRA_CACHE.name()), new EnumValidator<>(ConsistentHashStrategy.class, true, true)),
        L1_LIFESPAN("l1-lifespan", ModelType.LONG, new ModelNode(600000L), new DoubleRangeValidatorBuilder().lowerBound(0).build()),
        OWNERS("owners", ModelType.INT, new ModelNode(2), new IntRangeValidator(1, true, true)),
        SEGMENTS("segments", ModelType.INT, new ModelNode(80), new IntRangeValidator(1, true, true)),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit((type == ModelType.LONG) ? MeasurementUnit.MILLISECONDS : null)
                    .setValidator(validator)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = parent.addChildResource(WILDCARD_PATH);

        if (InfinispanModel.VERSION_3_0_0.requiresTransformation(version)) {
            builder.getAttributeBuilder()
                    .setDiscard(new DiscardAttributeChecker.DiscardAttributeValueChecker(Attribute.CAPACITY_FACTOR.getDefinition().getDefaultValue()), Attribute.CAPACITY_FACTOR.getDefinition())
                    .addRejectCheck(RejectAttributeChecker.DEFINED, Attribute.CAPACITY_FACTOR.getDefinition())
                    .setDiscard(new DiscardAttributeChecker.DiscardAttributeValueChecker(Attribute.CONSISTENT_HASH_STRATEGY.getDefinition().getDefaultValue()), Attribute.CONSISTENT_HASH_STRATEGY.getDefinition())
                    .addRejectCheck(RejectAttributeChecker.DEFINED, Attribute.CONSISTENT_HASH_STRATEGY.getDefinition())
                    .end();
        }

        SharedStateCacheResourceDefinition.buildTransformation(version, builder);
    }

    DistributedCacheResourceDefinition(PathManager pathManager, boolean allowRuntimeOnlyRegistration) {
        super(WILDCARD_PATH, pathManager, allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);

        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new DistributedCacheServiceHandler();
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).addAttributes(ClusteredCacheResourceDefinition.Attribute.class).addAttributes(CacheResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/EvictionBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.EvictionResourceDefinition.Attribute.MAX_ENTRIES;
import static org.jboss.as.clustering.infinispan.subsystem.EvictionResourceDefinition.Attribute.STRATEGY;

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.EvictionConfiguration;
import org.infinispan.configuration.cache.EvictionConfigurationBuilder;
import org.infinispan.eviction.EvictionStrategy;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class EvictionBuilder extends CacheComponentBuilder<EvictionConfiguration> implements ResourceServiceBuilder<EvictionConfiguration> {

    private final EvictionConfigurationBuilder builder = new ConfigurationBuilder().eviction();

    EvictionBuilder(String containerName, String cacheName) {
        super(CacheComponent.EVICTION, containerName, cacheName);
    }

    @Override
    public Builder<EvictionConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        EvictionStrategy strategy = ModelNodes.asEnum(STRATEGY.getDefinition().resolveModelAttribute(resolver, model), EvictionStrategy.class);
        this.builder.strategy(strategy);
        this.builder.maxEntries(strategy.isEnabled() ? MAX_ENTRIES.getDefinition().resolveModelAttribute(resolver, model).asLong() : -1L);
        return this;
    }

    @Override
    public EvictionConfiguration getValue() {
        return this.builder.create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/EvictionResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.infinispan.eviction.EvictionStrategy;
import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.MetricHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.operations.validation.EnumValidator;
import org.jboss.as.controller.operations.validation.ParameterValidator;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/cache=Y/eviction=EVICTION
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class EvictionResourceDefinition extends ComponentResourceDefinition {

    static final PathElement PATH = pathElement("eviction");
    static final PathElement LEGACY_PATH = PathElement.pathElement(PATH.getValue(), "EVICTION");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        MAX_ENTRIES("max-entries", ModelType.LONG, new ModelNode(-1L), null),
        STRATEGY("strategy", ModelType.STRING, new ModelNode(EvictionStrategy.NONE.name()), new EnumValidator<>(EvictionStrategy.class, true, false)),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setValidator(validator)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    private final boolean allowRuntimeOnlyRegistration;

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        if (InfinispanModel.VERSION_4_0_0.requiresTransformation(version)) {
            parent.addChildRedirection(PATH, LEGACY_PATH);
        }
    }

    EvictionResourceDefinition(boolean allowRuntimeOnlyRegistration) {
        super(PATH);
        this.allowRuntimeOnlyRegistration = allowRuntimeOnlyRegistration;
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new EvictionBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);

        if (this.allowRuntimeOnlyRegistration) {
            new MetricHandler<>(new EvictionMetricExecutor(), EvictionMetric.class).register(registration);
        }
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/ExpirationBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.ExpirationResourceDefinition.Attribute.INTERVAL;
import static org.jboss.as.clustering.infinispan.subsystem.ExpirationResourceDefinition.Attribute.LIFESPAN;
import static org.jboss.as.clustering.infinispan.subsystem.ExpirationResourceDefinition.Attribute.MAX_IDLE;

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.ExpirationConfiguration;
import org.infinispan.configuration.cache.ExpirationConfigurationBuilder;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class ExpirationBuilder extends CacheComponentBuilder<ExpirationConfiguration> implements ResourceServiceBuilder<ExpirationConfiguration> {

    private final ExpirationConfigurationBuilder builder = new ConfigurationBuilder().expiration();

    ExpirationBuilder(String containerName, String cacheName) {
        super(CacheComponent.EXPIRATION, containerName, cacheName);
    }

    @Override
    public Builder<ExpirationConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.builder.wakeUpInterval(INTERVAL.getDefinition().resolveModelAttribute(resolver, model).asLong());
        this.builder.lifespan(LIFESPAN.getDefinition().resolveModelAttribute(resolver, model).asLong());
        this.builder.maxIdle(MAX_IDLE.getDefinition().resolveModelAttribute(resolver, model).asLong());
        return this;
    }

    @Override
    public ExpirationConfiguration getValue() {
        return this.builder.create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/ExpirationResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/cache=Y/expiration=EXPIRATION
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class ExpirationResourceDefinition extends ComponentResourceDefinition {

    static final PathElement PATH = pathElement("expiration");
    static final PathElement LEGACY_PATH = PathElement.pathElement(PATH.getValue(), "EXPIRATION");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        INTERVAL("interval", ModelType.LONG, new ModelNode(60000L)),
        LIFESPAN("lifespan", ModelType.LONG, new ModelNode(-1L)),
        MAX_IDLE("max-idle", ModelType.LONG, new ModelNode(-1L)),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit((type == ModelType.LONG) ? MeasurementUnit.MILLISECONDS : null)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        if (InfinispanModel.VERSION_4_0_0.requiresTransformation(version)) {
            parent.addChildRedirection(PATH, LEGACY_PATH);
        }
    }

    ExpirationResourceDefinition() {
        super(PATH);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new ExpirationBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/FileStoreResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.services.path.PathManager;
import org.jboss.as.controller.services.path.ResolvePathHandler;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.as.server.ServerEnvironment;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/cache=Y/store=STORE
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class FileStoreResourceDefinition extends StoreResourceDefinition {

    static final PathElement LEGACY_PATH = PathElement.pathElement("file-store", "FILE_STORE");
    static final PathElement PATH = pathElement("file");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        RELATIVE_PATH("path", ModelType.STRING, null),
        RELATIVE_TO("relative-to", ModelType.STRING, new ModelNode(ServerEnvironment.SERVER_DATA_DIR)),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, LEGACY_PATH) : parent.addChildResource(PATH);

        StoreResourceDefinition.buildTransformation(version, builder);
    }

    private final PathManager pathManager;

    FileStoreResourceDefinition(PathManager pathManager, boolean allowRuntimeOnlyRegistration) {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH, WILDCARD_PATH), allowRuntimeOnlyRegistration);
        this.pathManager = pathManager;
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new FileStoreBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).addAttributes(StoreResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);

        if (this.pathManager != null) {
            ResolvePathHandler pathHandler = ResolvePathHandler.Builder.of(this.pathManager)
                    .setPathAttribute(Attribute.RELATIVE_PATH.getDefinition())
                    .setRelativeToAttribute(Attribute.RELATIVE_TO.getDefinition())
                    .build();
            registration.registerOperationHandler(pathHandler.getOperationDefinition(), pathHandler);
        }
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/GlobalConfigurationBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.CacheContainerResourceDefinition.Attribute.*;

import java.util.ServiceLoader;

import javax.management.MBeanServer;

import org.infinispan.configuration.global.GlobalConfiguration;
import org.infinispan.configuration.global.ShutdownHookBehavior;
import org.infinispan.configuration.global.TransportConfiguration;
import org.infinispan.marshall.core.Ids;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.clustering.infinispan.InfinispanLogger;
import org.jboss.as.clustering.infinispan.MBeanServerProvider;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.jmx.MBeanServerService;
import org.jboss.as.server.Services;
import org.jboss.dmr.ModelNode;
import org.jboss.marshalling.ModularClassResolver;
import org.jboss.modules.ModuleIdentifier;
import org.jboss.modules.ModuleLoadException;
import org.jboss.modules.ModuleLoader;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.service.ValueService;
import org.jboss.msc.value.InjectedValue;
import org.jboss.msc.value.Value;
import org.wildfly.clustering.infinispan.spi.io.SimpleExternalizer;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceNameFactory;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class GlobalConfigurationBuilder implements ResourceServiceBuilder<GlobalConfiguration>, Value<GlobalConfiguration> {

    private final InjectedValue<ModuleLoader> loader = new InjectedValue<>();
    private final InjectedValue<MBeanServer> server = new InjectedValue<>();
    private final InjectedValue<TransportConfiguration> transport = new InjectedValue<>();
    private final String name;

    private volatile boolean statisticsEnabled;
    private volatile ModuleIdentifier module;

    GlobalConfigurationBuilder(String name) {
        this.name = name;
    }

    @Override
    public ServiceName getServiceName() {
        return CacheContainerServiceName.CONFIGURATION.getServiceName(this.name);
    }

    @Override
    public Builder<GlobalConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.module = ModelNodes.asModuleIdentifier(MODULE.getDefinition().resolveModelAttribute(resolver, model));
        this.statisticsEnabled = STATISTICS_ENABLED.getDefinition().resolveModelAttribute(resolver, model).asBoolean();
        return this;
    }

    @Override
    public GlobalConfiguration getValue() {
        org.infinispan.configuration.global.GlobalConfigurationBuilder builder = new org.infinispan.configuration.global.GlobalConfigurationBuilder();
        TransportConfiguration transport = this.transport.getValue();
        // This fails due to ISPN-4755 !!
        // this.builder.transport().read(this.transport.getValue());
        // Workaround this by copying relevant fields individually
        builder.transport().transport(transport.transport())
                .distributedSyncTimeout(transport.distributedSyncTimeout())
                .clusterName(transport.clusterName())
                .machineId(transport.machineId())
                .rackId(transport.rackId())
                .siteId(transport.siteId())
        ;

        ModuleLoader moduleLoader = this.loader.getValue();
        builder.serialization().classResolver(ModularClassResolver.getInstance(moduleLoader));
        try {
            ClassLoader loader = moduleLoader.loadModule(this.module).getClassLoader();
            builder.classLoader(loader);
            int id = Ids.MAX_ID;
            for (SimpleExternalizer<?> externalizer: ServiceLoader.load(SimpleExternalizer.class, loader)) {
                InfinispanLogger.ROOT_LOGGER.debugf("Cache container %s will use an externalizer for %s", this.name, externalizer.getTargetClass().getName());
                builder.serialization().addAdvancedExternalizer(id++, externalizer);
            }
        } catch (ModuleLoadException e) {
            throw new IllegalStateException(e);
        }

        builder.shutdown().hookBehavior(ShutdownHookBehavior.DONT_REGISTER);
        builder.globalJmxStatistics()
                .enabled(this.statisticsEnabled)
                .cacheManagerName(this.name)
                .mBeanServerLookup(new MBeanServerProvider(this.server.getValue()))
                .jmxDomain(CacheContainerServiceName.CACHE_CONTAINER.getServiceName(CacheServiceNameFactory.DEFAULT_CACHE).getParent().getCanonicalName())
                .allowDuplicateDomains(true);

        return builder.build();
    }

    @Override
    public ServiceBuilder<GlobalConfiguration> build(ServiceTarget target) {
        return target.addService(this.getServiceName(), new ValueService<>(this))
                .addDependency(Services.JBOSS_SERVICE_MODULE_LOADER, ModuleLoader.class, this.loader)
                .addDependency(MBeanServerService.SERVICE_NAME, MBeanServer.class, this.server)
                .addDependency(CacheContainerComponent.TRANSPORT.getServiceName(this.name), TransportConfiguration.class, this.transport)
                .setInitialMode(ServiceController.Mode.ON_DEMAND)
        ;
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/IndexingBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.IndexingResourceDefinition.Attribute.INDEX;
import static org.jboss.as.clustering.infinispan.subsystem.IndexingResourceDefinition.Attribute.PROPERTIES;

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.Index;
import org.infinispan.configuration.cache.IndexingConfiguration;
import org.infinispan.configuration.cache.IndexingConfigurationBuilder;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class IndexingBuilder extends CacheComponentBuilder<IndexingConfiguration> implements ResourceServiceBuilder<IndexingConfiguration> {

    private final IndexingConfigurationBuilder builder = new ConfigurationBuilder().indexing();

    IndexingBuilder(String containerName, String cacheName) {
        super(CacheComponent.INDEXING, containerName, cacheName);
    }

    @Override
    public Builder<IndexingConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.builder.index(ModelNodes.asEnum(INDEX.getDefinition().resolveModelAttribute(resolver, model), Index.class));
        this.builder.withProperties(ModelNodes.asProperties(PROPERTIES.getDefinition().resolveModelAttribute(resolver, model)));
        return this;
    }

    @Override
    public IndexingConfiguration getValue() {
        return this.builder.create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/IndexingResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.infinispan.configuration.cache.Index;
import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.AttributeMarshallers;
import org.jboss.as.clustering.controller.AttributeParsers;
import org.jboss.as.clustering.controller.Operations;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.clustering.controller.transform.OperationTransformer;
import org.jboss.as.clustering.controller.transform.SimpleOperationTransformer;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleMapAttributeDefinition;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.validation.EnumValidator;
import org.jboss.as.controller.operations.validation.ParameterValidator;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * @author Paul Ferraro
 */
public class IndexingResourceDefinition extends ComponentResourceDefinition {

    static final PathElement PATH = pathElement("indexing");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        INDEX("index", ModelType.STRING, new ModelNode(Index.NONE.name()), new EnumValidator<>(Index.class, true, false)),
        PROPERTIES("properties"),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(false)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setValidator(validator)
                    .build();
        }

        Attribute(String name) {
            this.definition = new SimpleMapAttributeDefinition.Builder(name, true)
                    .setAllowNull(true)
                    .setAttributeMarshaller(AttributeMarshallers.PROPERTY_LIST)
                    .setAttributeParser(AttributeParsers.COLLECTION)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    @SuppressWarnings("deprecation")
    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = parent.addChildResource(PATH);

        if (InfinispanModel.VERSION_4_0_0.requiresTransformation(version)) {
            OperationTransformer addTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress cacheAddress = Operations.getPathAddress(operation).getParent();
                    ModelNode indexOperation = this.translateParameter(cacheAddress, operation, Attribute.INDEX, CacheResourceDefinition.Attribute.INDEXING);
                    ModelNode propertiesOperation = this.translateParameter(cacheAddress, operation, Attribute.PROPERTIES, CacheResourceDefinition.Attribute.INDEXING_PROPERTIES);
                    return Operations.createCompositeOperation(indexOperation, propertiesOperation);
                }

                private ModelNode translateParameter(PathAddress address, ModelNode operation, Attribute attribute, org.jboss.as.clustering.controller.Attribute legacyAttribute) {
                    String name = attribute.getDefinition().getName();
                    return operation.hasDefined(name) ? Operations.createWriteAttributeOperation(address, legacyAttribute, operation.get(name)) : Operations.createUndefineAttributeOperation(address, legacyAttribute);
                }
            };
            builder.addRawOperationTransformationOverride(ModelDescriptionConstants.ADD, new SimpleOperationTransformer(addTransformer));

            OperationTransformer removeTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress cacheAddress = Operations.getPathAddress(operation).getParent();
                    ModelNode indexOperation = Operations.createUndefineAttributeOperation(cacheAddress, CacheResourceDefinition.Attribute.INDEXING);
                    ModelNode propertiesOperation = Operations.createUndefineAttributeOperation(cacheAddress, CacheResourceDefinition.Attribute.INDEXING_PROPERTIES);
                    return Operations.createCompositeOperation(indexOperation, propertiesOperation);
                }
            };
            builder.addRawOperationTransformationOverride(ModelDescriptionConstants.REMOVE, new SimpleOperationTransformer(removeTransformer));

            OperationTransformer readAttributeTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress cacheAddress = Operations.getPathAddress(operation).getParent();
                    String name = Operations.getAttributeName(operation);
                    if (Attribute.INDEX.getDefinition().getName().equals(name)) {
                        return Operations.createReadAttributeOperation(cacheAddress, CacheResourceDefinition.Attribute.INDEXING);
                    } else if (Attribute.PROPERTIES.getDefinition().getName().equals(name)) {
                        return Operations.createReadAttributeOperation(cacheAddress, CacheResourceDefinition.Attribute.INDEXING_PROPERTIES);
                    }
                    return operation;
                }
            };
            builder.addRawOperationTransformationOverride(ModelDescriptionConstants.READ_ATTRIBUTE_OPERATION, new SimpleOperationTransformer(readAttributeTransformer));

            OperationTransformer writeAttributeTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress cacheAddress = Operations.getPathAddress(operation).getParent();
                    String name = Operations.getAttributeName(operation);
                    ModelNode value = Operations.getAttributeValue(operation);
                    if (Attribute.INDEX.getDefinition().getName().equals(name)) {
                        return Operations.createWriteAttributeOperation(cacheAddress, CacheResourceDefinition.Attribute.INDEXING, value);
                    } else if (Attribute.PROPERTIES.getDefinition().getName().equals(name)) {
                        return Operations.createWriteAttributeOperation(cacheAddress, CacheResourceDefinition.Attribute.INDEXING_PROPERTIES, value);
                    }
                    return operation;
                }
            };
            builder.addRawOperationTransformationOverride(ModelDescriptionConstants.WRITE_ATTRIBUTE_OPERATION, new SimpleOperationTransformer(writeAttributeTransformer));

            OperationTransformer undefineAttributeTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress cacheAddress = Operations.getPathAddress(operation).getParent();
                    String name = Operations.getAttributeName(operation);
                    if (Attribute.INDEX.getDefinition().getName().equals(name)) {
                        return Operations.createUndefineAttributeOperation(cacheAddress, CacheResourceDefinition.Attribute.INDEXING);
                    } else if (Attribute.PROPERTIES.getDefinition().getName().equals(name)) {
                        return Operations.createUndefineAttributeOperation(cacheAddress, CacheResourceDefinition.Attribute.INDEXING_PROPERTIES);
                    }
                    return operation;
                }
            };
            builder.addRawOperationTransformationOverride(ModelDescriptionConstants.UNDEFINE_ATTRIBUTE_OPERATION, new SimpleOperationTransformer(undefineAttributeTransformer));
        }
    }

    IndexingResourceDefinition() {
        super(PATH);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new IndexingBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/InfinispanSubsystemResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.BoottimeAddStepHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.GenericSubsystemDescribeHandler;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.services.path.PathManager;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.as.controller.transform.description.TransformationDescription;
import org.jboss.as.controller.transform.description.TransformationDescriptionBuilder;

/**
 * The root resource of the Infinispan subsystem.
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class InfinispanSubsystemResourceDefinition extends SimpleResourceDefinition {

    static final PathElement PATH = PathElement.pathElement(ModelDescriptionConstants.SUBSYSTEM, InfinispanExtension.SUBSYSTEM_NAME);

    static TransformationDescription buildTransformation(ModelVersion version) {
        ResourceTransformationDescriptionBuilder builder = TransformationDescriptionBuilder.Factory.createSubsystemInstance();

        CacheContainerResourceDefinition.buildTransformation(version, builder);

        return builder.build();
    }

    private final PathManager pathManager;
    private final boolean allowRuntimeOnlyRegistration;

    InfinispanSubsystemResourceDefinition(PathManager pathManager, boolean allowRuntimeOnlyRegistration) {
        super(PATH, new InfinispanResourceDescriptionResolver());
        this.pathManager = pathManager;
        this.allowRuntimeOnlyRegistration = allowRuntimeOnlyRegistration;
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new InfinispanSubsystemServiceHandler();
        new BoottimeAddStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
        registration.registerOperationHandler(GenericSubsystemDescribeHandler.DEFINITION, GenericSubsystemDescribeHandler.INSTANCE);
    }

    @Override
    public void registerChildren(ManagementResourceRegistration registration) {
        new CacheContainerResourceDefinition(this.pathManager, this.allowRuntimeOnlyRegistration).register(registration);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/InvalidationCacheResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.services.path.PathManager;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/invalidation-cache=*
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class InvalidationCacheResourceDefinition extends ClusteredCacheResourceDefinition {

    static final PathElement WILDCARD_PATH = pathElement(PathElement.WILDCARD_VALUE);
    static final PathElement pathElement(String name) {
        return PathElement.pathElement("invalidation-cache", name);
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = parent.addChildResource(WILDCARD_PATH);

        ClusteredCacheResourceDefinition.buildTransformation(version, builder);
    }

    InvalidationCacheResourceDefinition(PathManager pathManager, boolean allowRuntimeOnlyRegistration) {
        super(WILDCARD_PATH, pathManager, allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new InvalidationCacheServiceHandler();
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(ClusteredCacheResourceDefinition.Attribute.class).addAttributes(CacheResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/JGroupsTransportBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.JGroupsTransportResourceDefinition.Attribute.LOCK_TIMEOUT;

import org.infinispan.configuration.global.GlobalConfigurationBuilder;
import org.infinispan.configuration.global.TransportConfiguration;
import org.infinispan.configuration.global.TransportConfigurationBuilder;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.infinispan.ChannelTransport;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.value.InjectedValue;
import org.jgroups.Channel;
import org.wildfly.clustering.jgroups.spi.ChannelFactory;
import org.wildfly.clustering.jgroups.spi.ProtocolStackConfiguration;
import org.wildfly.clustering.jgroups.spi.service.ChannelServiceName;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class JGroupsTransportBuilder extends CacheContainerComponentBuilder<TransportConfiguration> implements ResourceServiceBuilder<TransportConfiguration> {

    private final InjectedValue<Channel> channel = new InjectedValue<>();
    private final InjectedValue<ChannelFactory> factory = new InjectedValue<>();
    private final String containerName;

    private volatile long lockTimeout;

    public JGroupsTransportBuilder(String containerName) {
        super(CacheContainerComponent.TRANSPORT, containerName);
        this.containerName = containerName;
    }

    @Override
    public ServiceBuilder<TransportConfiguration> build(ServiceTarget target) {
        return super.build(target)
                .addDependency(ChannelServiceName.CHANNEL.getServiceName(this.containerName), Channel.class, this.channel)
                .addDependency(ChannelServiceName.FACTORY.getServiceName(this.containerName), ChannelFactory.class, this.factory)
        ;
    }

    @Override
    public Builder<TransportConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.lockTimeout = LOCK_TIMEOUT.getDefinition().resolveModelAttribute(resolver, model).asLong();
        return this;
    }

    @Override
    public TransportConfiguration getValue() throws IllegalStateException, IllegalArgumentException {
        Channel channel = this.channel.getValue();
        ChannelFactory factory = this.factory.getValue();
        ProtocolStackConfiguration stack = factory.getProtocolStackConfiguration();
        org.wildfly.clustering.jgroups.spi.TransportConfiguration.Topology topology = stack.getTransport().getTopology();
        TransportConfigurationBuilder builder = new GlobalConfigurationBuilder().transport()
                .clusterName(this.containerName)
                .distributedSyncTimeout(this.lockTimeout)
                .transport(new ChannelTransport(channel, factory))
        ;
        if (topology != null) {
            builder.siteId(topology.getSite()).rackId(topology.getRack()).machineId(topology.getMachine());
        }
        return builder.create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/JGroupsTransportResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import java.util.Set;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.transform.SimpleAttributeConverter;
import org.jboss.as.clustering.controller.transform.SimpleAttributeConverter.Converter;
import org.jboss.as.clustering.controller.transform.SimpleRejectAttributeChecker;
import org.jboss.as.clustering.controller.transform.SimpleRejectAttributeChecker.Rejecter;
import org.jboss.as.clustering.infinispan.InfinispanLogger;
import org.jboss.as.clustering.jgroups.subsystem.ChannelResourceDefinition;
import org.jboss.as.clustering.jgroups.subsystem.JGroupsSubsystemResourceDefinition;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.registry.Resource.NoSuchResourceException;
import org.jboss.as.controller.transform.TransformationContext;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/transport=TRANSPORT
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class JGroupsTransportResourceDefinition extends TransportResourceDefinition {

    static final PathElement LEGACY_PATH = pathElement("TRANSPORT");
    static final PathElement PATH = pathElement("jgroups");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        CHANNEL("channel", ModelType.STRING, null),
        @Deprecated CLUSTER("cluster", ModelType.STRING, null, InfinispanModel.VERSION_3_0_0),
        EXECUTOR("executor", ModelType.STRING, null),
        LOCK_TIMEOUT("lock-timeout", ModelType.LONG, new ModelNode(240000L)),
        @Deprecated STACK("stack", ModelType.STRING, null, InfinispanModel.VERSION_3_0_0),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = createBuilder(name, type, defaultValue).build();
        }

        Attribute(String name, ModelType type, ModelNode defaultValue, InfinispanModel deprecation) {
            this.definition = createBuilder(name, type, defaultValue).setDeprecated(deprecation.getVersion()).build();
        }

        private static SimpleAttributeDefinitionBuilder createBuilder(String name, ModelType type, ModelNode defaultValue) {
            return new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit((type == ModelType.LONG) ? MeasurementUnit.MILLISECONDS : null)
            ;
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, LEGACY_PATH) : parent.addChildResource(PATH);

        if (InfinispanModel.VERSION_3_0_0.requiresTransformation(version)) {
            // We need to reject if we cannot determine the underlying stack via the jgroups subsystem
            Rejecter stackRejecter = new Rejecter() {
                @Override
                public boolean reject(PathAddress address, String name, ModelNode value, ModelNode model, TransformationContext context) {
                    if (value.isDefined()) return false;
                    PathAddress rootAddress = address.subAddress(0, address.size() - 3);
                    PathAddress subsystemAddress = rootAddress.append(JGroupsSubsystemResourceDefinition.PATH);
                    ModelNode subsystemModel = context.readResourceFromRoot(subsystemAddress).getModel();
                    String channelName = null;
                    if (model.hasDefined(Attribute.CHANNEL.getDefinition().getName())) {
                        ModelNode channel = model.get(Attribute.CHANNEL.getDefinition().getName());
                        if (channel.getType() == ModelType.STRING) {
                            channelName = channel.asString();
                        }
                    } else if (subsystemModel.hasDefined(JGroupsSubsystemResourceDefinition.DEFAULT_CHANNEL.getName())) {
                        ModelNode defaultChannel = subsystemModel.get(JGroupsSubsystemResourceDefinition.DEFAULT_CHANNEL.getName());
                        if (defaultChannel.getType() == ModelType.STRING) {
                            channelName = defaultChannel.asString();
                        }
                    }
                    if (channelName == null) return true;
                    String stackName = null;
                    PathAddress channelAddress = subsystemAddress.append(ChannelResourceDefinition.pathElement(channelName));
                    try {
                        ModelNode channel = context.readResourceFromRoot(channelAddress).getModel();
                        if (channel.hasDefined(ChannelResourceDefinition.STACK.getName())) {
                            ModelNode stack = channel.get(ChannelResourceDefinition.STACK.getName());
                            if (stack.getType() == ModelType.STRING) {
                                stackName = stack.asString();
                            }
                        } else if (subsystemModel.hasDefined(JGroupsSubsystemResourceDefinition.DEFAULT_STACK.getName())) {
                            ModelNode defaultStack = subsystemModel.get(JGroupsSubsystemResourceDefinition.DEFAULT_STACK.getName());
                            if (defaultStack.getType() == ModelType.STRING) {
                                stackName = defaultStack.asString();
                            }
                        }
                    } catch (NoSuchResourceException e) {
                        // Ignore
                    }
                    return (stackName == null);
                }

                @Override
                public String getRejectedMessage(Set<String> attributes) {
                    return InfinispanLogger.ROOT_LOGGER.indeterminiteStack();
                }
            };
            // Lookup the stack via the jgroups channel resource, if necessary
            Converter stackConverter = new Converter() {
                @Override
                public void convert(PathAddress address, String name, ModelNode value, ModelNode model, TransformationContext context) {
                    if (!value.isDefined()) {
                        PathAddress rootAddress = address.subAddress(0, address.size() - 3);
                        PathAddress subsystemAddress = rootAddress.append(JGroupsSubsystemResourceDefinition.PATH);
                        ModelNode subsystemModel = context.readResourceFromRoot(subsystemAddress).getModel();
                        String channelName = null;
                        if (model.hasDefined(Attribute.CHANNEL.getDefinition().getName())) {
                            ModelNode channel = model.get(Attribute.CHANNEL.getDefinition().getName());
                            if (channel.getType() == ModelType.STRING) {
                                channelName = channel.asString();
                            }
                        } else if (subsystemModel.hasDefined(JGroupsSubsystemResourceDefinition.DEFAULT_CHANNEL.getName())) {
                            ModelNode defaultChannel = subsystemModel.get(JGroupsSubsystemResourceDefinition.DEFAULT_CHANNEL.getName());
                            if (defaultChannel.getType() == ModelType.STRING) {
                                channelName = defaultChannel.asString();
                            }
                        }
                        if (channelName != null) {
                            PathAddress channelAddress = subsystemAddress.append(ChannelResourceDefinition.pathElement(channelName));
                            try {
                                ModelNode channel = context.readResourceFromRoot(channelAddress).getModel();
                                if (channel.hasDefined(ChannelResourceDefinition.STACK.getName())) {
                                    ModelNode stack = channel.get(ChannelResourceDefinition.STACK.getName());
                                    if (stack.getType() == ModelType.STRING) {
                                        value.set(stack.asString());
                                    }
                                } else if (subsystemModel.hasDefined(JGroupsSubsystemResourceDefinition.DEFAULT_STACK.getName())) {
                                    ModelNode defaultStack = subsystemModel.get(JGroupsSubsystemResourceDefinition.DEFAULT_STACK.getName());
                                    if (defaultStack.getType() == ModelType.STRING) {
                                        value.set(defaultStack.asString());
                                    }
                                }
                            } catch (NoSuchResourceException e) {
                                // Ignore
                            }
                        }
                    }
                }
            };
            builder.getAttributeBuilder()
                    .addRejectCheck(new SimpleRejectAttributeChecker(stackRejecter), Attribute.STACK.getDefinition())
                    .setValueConverter(new SimpleAttributeConverter(stackConverter), Attribute.STACK.getDefinition())
                    .addRename(Attribute.CHANNEL.getDefinition(), Attribute.CLUSTER.getDefinition().getName())
                    .end();
        }
    }

    JGroupsTransportResourceDefinition() {
        super(PATH);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new JGroupsTransportServiceHandler();
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/JGroupsTransportServiceHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.JGroupsTransportResourceDefinition.Attribute.*;

import java.util.ServiceLoader;

import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.clustering.jgroups.subsystem.JGroupsBindingFactory;
import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceTarget;
import org.jgroups.Channel;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceNameFactory;
import org.wildfly.clustering.jgroups.spi.ChannelFactory;
import org.wildfly.clustering.jgroups.spi.service.ChannelBuilder;
import org.wildfly.clustering.jgroups.spi.service.ChannelConnectorBuilder;
import org.wildfly.clustering.jgroups.spi.service.ChannelServiceName;
import org.wildfly.clustering.jgroups.spi.service.ChannelServiceNameFactory;
import org.wildfly.clustering.jgroups.spi.service.ProtocolStackServiceName;
import org.wildfly.clustering.service.AliasServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.GroupAliasBuilderProvider;

/**
 * @author Paul Ferraro
 */
public class JGroupsTransportServiceHandler implements ResourceServiceHandler {

    @Override
    public void installServices(OperationContext context, ModelNode model) throws OperationFailedException {
        String name = context.getCurrentAddress().getParent().getLastElement().getValue();
        ServiceTarget target = context.getServiceTarget();

        String channel = ModelNodes.asString(CHANNEL.getDefinition().resolveModelAttribute(context, model), ChannelServiceNameFactory.DEFAULT_CHANNEL);

        new JGroupsTransportBuilder(name).configure(context, model).build(target).install();

        new SiteBuilder(name).setChannelName(channel).build(target).install();

        new BinderServiceBuilder<>(JGroupsBindingFactory.createChannelBinding(name), ChannelServiceName.CHANNEL.getServiceName(name), Channel.class).build(target).install();
        new ChannelBuilder(name).build(target).install();
        new ChannelConnectorBuilder(name).build(target).install();
        new AliasServiceBuilder<>(ChannelServiceName.FACTORY.getServiceName(name), ProtocolStackServiceName.CHANNEL_FACTORY.getServiceName(channel), ChannelFactory.class).build(target).install();

        for (GroupAliasBuilderProvider provider : ServiceLoader.load(GroupAliasBuilderProvider.class, GroupAliasBuilderProvider.class.getClassLoader())) {
            for (Builder<?> builder : provider.getBuilders(name, channel)) {
                builder.build(target).install();
            }
        }
    }

    @Override
    public void removeServices(OperationContext context, ModelNode model) throws OperationFailedException {
        String name = context.getCurrentAddress().getParent().getLastElement().getValue();

        String channel = ModelNodes.asString(CHANNEL.getDefinition().resolveModelAttribute(context, model), ChannelServiceNameFactory.DEFAULT_CHANNEL);

        for (GroupAliasBuilderProvider provider : ServiceLoader.load(GroupAliasBuilderProvider.class, GroupAliasBuilderProvider.class.getClassLoader())) {
            for (Builder<?> builder : provider.getBuilders(name, channel)) {
                context.removeService(builder.getServiceName());
            }
        }

        for (ChannelServiceNameFactory factory : ChannelServiceName.values()) {
            context.removeService(factory.getServiceName(name));
        }

        for (CacheContainerServiceNameFactory factory : CacheContainerComponent.values()) {
            context.removeService(factory.getServiceName(name));
        }
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/KeyAffinityServiceFactoryBuilder.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import java.security.PrivilegedAction;
import java.util.Collections;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;

import org.infinispan.Cache;
import org.infinispan.affinity.KeyAffinityService;
import org.infinispan.affinity.KeyGenerator;
import org.infinispan.affinity.impl.KeyAffinityServiceImpl;
import org.infinispan.remoting.transport.Address;
import org.wildfly.clustering.infinispan.spi.affinity.KeyAffinityServiceFactory;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.service.AsynchronousServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.jboss.msc.service.Service;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.service.StartContext;
import org.jboss.msc.service.StopContext;
import org.jboss.threads.JBossThreadFactory;

import static java.security.AccessController.doPrivileged;

/**
 * Key affinity service factory that will only generates keys for use by the local node.
 * Returns a trivial implementation if the specified cache is not distributed.
 * @author Paul Ferraro
 */
public class KeyAffinityServiceFactoryBuilder implements Builder<KeyAffinityServiceFactory>, Service<KeyAffinityServiceFactory>, KeyAffinityServiceFactory {

    private final String containerName;
    private volatile int bufferSize = 10;
    private volatile ExecutorService executor;

    public KeyAffinityServiceFactoryBuilder(String containerName) {
        this.containerName = containerName;
    }

    public KeyAffinityServiceFactoryBuilder setBufferSize(int size) {
        this.bufferSize = size;
        return this;
    }

    @Override
    public ServiceName getServiceName() {
        return CacheContainerServiceName.AFFINITY.getServiceName(this.containerName);
    }

    @Override
    public ServiceBuilder<KeyAffinityServiceFactory> build(ServiceTarget target) {
        return new AsynchronousServiceBuilder<>(this.getServiceName(), this).startSynchronously().build(target)
                .setInitialMode(ServiceController.Mode.ON_DEMAND);
    }

    @Override
    public KeyAffinityServiceFactory getValue() {
        return this;
    }

    @Override
    public void start(StartContext context) {
        final ThreadGroup threadGroup = new ThreadGroup("KeyAffinityService ThreadGroup");
        final String namePattern = "KeyAffinityService Thread Pool -- %t";
        final ThreadFactory threadFactory = doPrivileged(new PrivilegedAction<JBossThreadFactory>() {
            public JBossThreadFactory run() {
                return new JBossThreadFactory(threadGroup, Boolean.FALSE, null, namePattern, null, null);
            }
        });

        this.executor = Executors.newCachedThreadPool(threadFactory);
    }

    @Override
    public void stop(StopContext context) {
        this.executor.shutdown();
    }

    @Override
    public <K> KeyAffinityService<K> createService(Cache<K, ?> cache, KeyGenerator<K> generator) {
        boolean clustered = cache.getCacheConfiguration().clustering().cacheMode().isClustered();
        return clustered ? new KeyAffinityServiceImpl<>(this.executor, cache, generator, this.bufferSize, Collections.singleton(cache.getCacheManager().getAddress()), false) : new SimpleKeyAffinityService<>(generator);
    }

    private static class SimpleKeyAffinityService<K> implements KeyAffinityService<K> {
        private final KeyGenerator<K> generator;
        private volatile boolean started = false;

        SimpleKeyAffinityService(KeyGenerator<K> generator) {
            this.generator = generator;
        }

        @Override
        public void start() {
            this.started = true;
        }

        @Override
        public void stop() {
            this.started = false;
        }

        @Override
        public K getKeyForAddress(Address address) {
            return this.generator.getKey();
        }

        @Override
        public K getCollocatedKey(K otherKey) {
            return this.generator.getKey();
        }

        @Override
        public boolean isStarted() {
            return this.started;
        }
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/LocalCacheResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.services.path.PathManager;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/local-cache=*
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class LocalCacheResourceDefinition extends CacheResourceDefinition {

    static final PathElement WILDCARD_PATH = pathElement(PathElement.WILDCARD_VALUE);
    static PathElement pathElement(String name) {
        return PathElement.pathElement("local-cache", name);
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = parent.addChildResource(WILDCARD_PATH);

        CacheResourceDefinition.buildTransformation(version, builder);
    }

    LocalCacheResourceDefinition(PathManager pathManager, boolean allowRuntimeOnlyRegistration) {
        super(WILDCARD_PATH, pathManager, allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new LocalCacheServiceHandler();
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(CacheResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/LockingBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.LockingResourceDefinition.Attribute.ACQUIRE_TIMEOUT;
import static org.jboss.as.clustering.infinispan.subsystem.LockingResourceDefinition.Attribute.CONCURRENCY;
import static org.jboss.as.clustering.infinispan.subsystem.LockingResourceDefinition.Attribute.ISOLATION;
import static org.jboss.as.clustering.infinispan.subsystem.LockingResourceDefinition.Attribute.STRIPING;

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.LockingConfiguration;
import org.infinispan.configuration.cache.LockingConfigurationBuilder;
import org.infinispan.util.concurrent.IsolationLevel;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class LockingBuilder extends CacheComponentBuilder<LockingConfiguration> implements ResourceServiceBuilder<LockingConfiguration> {

    private final LockingConfigurationBuilder builder = new ConfigurationBuilder().locking();

    LockingBuilder(String containerName, String cacheName) {
        super(CacheComponent.LOCKING, containerName, cacheName);
    }

    @Override
    public LockingConfiguration getValue() {
        return this.builder.create();
    }

    @Override
    public Builder<LockingConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.builder.lockAcquisitionTimeout(ACQUIRE_TIMEOUT.getDefinition().resolveModelAttribute(resolver, model).asLong());
        this.builder.concurrencyLevel(CONCURRENCY.getDefinition().resolveModelAttribute(resolver, model).asInt());
        this.builder.isolationLevel(ModelNodes.asEnum(ISOLATION.getDefinition().resolveModelAttribute(resolver, model), IsolationLevel.class));
        this.builder.useLockStriping(STRIPING.getDefinition().resolveModelAttribute(resolver, model).asBoolean());
        return this;
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/LockingResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.infinispan.util.concurrent.IsolationLevel;
import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.MetricHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.operations.validation.EnumValidator;
import org.jboss.as.controller.operations.validation.ParameterValidator;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.AttributeConverter.DefaultValueAttributeConverter;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/cache=Y/locking=LOCKING
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class LockingResourceDefinition extends ComponentResourceDefinition {

    static final PathElement PATH = pathElement("locking");
    static final PathElement LEGACY_PATH = PathElement.pathElement(PATH.getValue(), "LOCKING");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        ACQUIRE_TIMEOUT("acquire-timeout", ModelType.LONG, new ModelNode(15000L), null),
        CONCURRENCY("concurrency-level", ModelType.INT, new ModelNode(1000), null),
        ISOLATION("isolation", ModelType.STRING, new ModelNode(IsolationLevel.READ_COMMITTED.name()), new EnumValidator<>(IsolationLevel.class, true, false)),
        STRIPING("striping", ModelType.BOOLEAN, new ModelNode(false), null),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit((type == ModelType.LONG) ? MeasurementUnit.MILLISECONDS : null)
                    .setValidator(validator)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    private final boolean allowRuntimeOnlyRegistration;

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, LEGACY_PATH) : parent.addChildResource(PATH);

        if (InfinispanModel.VERSION_3_0_0.requiresTransformation(version)) {
            builder.getAttributeBuilder().setValueConverter(new DefaultValueAttributeConverter(Attribute.ISOLATION.getDefinition()), Attribute.ISOLATION.getDefinition());
        }
    }

    LockingResourceDefinition(boolean allowRuntimeOnlyRegistration) {
        super(PATH);
        this.allowRuntimeOnlyRegistration = allowRuntimeOnlyRegistration;
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new LockingBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);

        if (this.allowRuntimeOnlyRegistration) {
            new MetricHandler<>(new LockingMetricExecutor(), LockingMetric.class).register(registration);
        }
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/MixedKeyedJDBCStoreResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.infinispan.persistence.jdbc.configuration.TableManipulationConfiguration;
import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.ResourceServiceBuilderFactory;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;

/**
 * Resource description for the addressable resource
 *
 * /subsystem=infinispan/cache-container=X/cache=Y/store=mixed
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Paul Ferraro
 */
public class MixedKeyedJDBCStoreResourceDefinition extends JDBCStoreResourceDefinition {

    static final PathElement LEGACY_PATH = PathElement.pathElement("mixed-keyed-jdbc-store", "MIXED_KEYED_JDBC_STORE");
    static final PathElement PATH = pathElement("mixed-jdbc");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        @Deprecated BINARY_TABLE(BinaryKeyedJDBCStoreResourceDefinition.Attribute.TABLE),
        @Deprecated STRING_TABLE(StringKeyedJDBCStoreResourceDefinition.Attribute.TABLE),
        ;
        private final AttributeDefinition definition;

        Attribute(org.jboss.as.clustering.controller.Attribute attribute) {
            this.definition = attribute.getDefinition();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, LEGACY_PATH) : parent.addChildResource(PATH);

        JDBCStoreResourceDefinition.buildTransformation(version, builder);

        BinaryTableResourceDefinition.buildTransformation(version, builder);
        StringTableResourceDefinition.buildTransformation(version, builder);
    }

    MixedKeyedJDBCStoreResourceDefinition(boolean allowRuntimeOnlyRegistration) {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH, pathElement("jdbc"), WILDCARD_PATH), allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerOperations(final ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new MixedKeyedJDBCStoreBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler) {
            @Override
            public void execute(OperationContext context, ModelNode operation) throws OperationFailedException {
                super.execute(context, operation);
                // Translate deprecated BINARY_TABLE attribute into separate add table operation
                this.addTableStep(context, operation, Attribute.BINARY_TABLE, BinaryTableResourceDefinition.PATH, new BinaryTableBuilderFactory());
                // Translate deprecated STRING_TABLE attribute into separate add table operation
                this.addTableStep(context, operation, Attribute.STRING_TABLE, StringTableResourceDefinition.PATH, new StringTableBuilderFactory());
            }

            private void addTableStep(OperationContext context, ModelNode operation, Attribute attribute, PathElement path, ResourceServiceBuilderFactory<TableManipulationConfiguration> provider) {
                if (operation.hasDefined(attribute.getDefinition().getName())) {
                    ModelNode addTableOperation = Util.createAddOperation(context.getCurrentAddress().append(path));
                    ModelNode parameters = operation.get(attribute.getDefinition().getName());
                    for (Property parameter : parameters.asPropertyList()) {
                        addTableOperation.get(parameter.getName()).set(parameter.getValue());
                    }
                    context.addStep(addTableOperation, registration.getOperationHandler(PathAddress.pathAddress(path), ModelDescriptionConstants.ADD), context.getCurrentStage());
                }
            }
        }.addAttributes(JDBCStoreResourceDefinition.Attribute.class).addAttributes(StoreResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerChildren(ManagementResourceRegistration registration) {
        super.registerChildren(registration);
        new BinaryTableResourceDefinition().register(registration);
        new StringTableResourceDefinition().register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);
        registration.registerReadWriteAttribute(Attribute.BINARY_TABLE.getDefinition(), BinaryKeyedJDBCStoreResourceDefinition.LEGACY_READ_TABLE_HANDLER, BinaryKeyedJDBCStoreResourceDefinition.LEGACY_WRITE_TABLE_HANDLER);
        registration.registerReadWriteAttribute(Attribute.STRING_TABLE.getDefinition(), StringKeyedJDBCStoreResourceDefinition.LEGACY_READ_TABLE_HANDLER, StringKeyedJDBCStoreResourceDefinition.LEGACY_WRITE_TABLE_HANDLER);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/NoStoreBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.PersistenceConfiguration;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class NoStoreBuilder extends CacheComponentBuilder<PersistenceConfiguration> implements ResourceServiceBuilder<PersistenceConfiguration> {

    NoStoreBuilder(String containerName, String cacheName) {
        super(CacheComponent.PERSISTENCE, containerName, cacheName);
    }

    @Override
    public PersistenceConfiguration getValue() {
        return new ConfigurationBuilder().persistence().passivation(false).create();
    }

    @Override
    public Builder<PersistenceConfiguration> configure(ExpressionResolver resolver, ModelNode model) {
        return this;
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/NoStoreResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.Registration;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;

/**
 * @author Paul Ferraro
 */
public class NoStoreResourceDefinition extends SimpleResourceDefinition implements Registration {

    static PathElement PATH = StoreResourceDefinition.pathElement("none");

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder builder) {
        // Nothing to do yet
    }

    /**
     * @param type
     * @param allowRuntimeOnlyRegistration
     */
    public NoStoreResourceDefinition() {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH));
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new NoStoreBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/NoTransportResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;

/**
 * @author Paul Ferraro
 */
public class NoTransportResourceDefinition extends TransportResourceDefinition {
    static final PathElement PATH = pathElement("none");

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        // Nothing to transform
    }

    NoTransportResourceDefinition() {
        super(PATH);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new NoTransportServiceHandler();
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/NoTransportServiceHandler.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import java.util.ServiceLoader;

import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceTarget;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceNameFactory;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.GroupAliasBuilderProvider;
import org.wildfly.clustering.spi.LocalGroupBuilderProvider;

/**
 * @author Paul Ferraro
 */
public class NoTransportServiceHandler implements ResourceServiceHandler {

    @Override
    public void installServices(OperationContext context, ModelNode model) throws OperationFailedException {
        String name = context.getCurrentAddress().getParent().getLastElement().getValue();

        ServiceTarget target = context.getServiceTarget();

        new NoTransportBuilder(name).build(target).install();
        new SiteBuilder(name).build(target).install();

        for (GroupAliasBuilderProvider provider : ServiceLoader.load(GroupAliasBuilderProvider.class, GroupAliasBuilderProvider.class.getClassLoader())) {
            for (Builder<?> builder : provider.getBuilders(name, LocalGroupBuilderProvider.LOCAL)) {
                builder.build(target).install();
            }
        }
    }

    @Override
    public void removeServices(OperationContext context, ModelNode model) {
        String name = context.getCurrentAddress().getParent().getLastElement().getValue();

        for (GroupAliasBuilderProvider provider : ServiceLoader.load(GroupAliasBuilderProvider.class, GroupAliasBuilderProvider.class.getClassLoader())) {
            for (Builder<?> builder : provider.getBuilders(name, LocalGroupBuilderProvider.LOCAL)) {
                context.removeService(builder.getServiceName());
            }
        }

        for (CacheContainerServiceNameFactory factory : CacheContainerComponent.values()) {
            context.removeService(factory.getServiceName(name));
        }
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/RemoteStoreResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.infinispan.commons.api.BasicCacheContainer;
import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.AttributeParsers;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.StringListAttributeDefinition;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/cache=Y/remote-store=REMOTE_STORE
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class RemoteStoreResourceDefinition extends StoreResourceDefinition {

    static final PathElement LEGACY_PATH = PathElement.pathElement("remote-store", "REMOTE_STORE");
    static final PathElement PATH = pathElement("remote");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        CACHE("cache", ModelType.STRING, new ModelNode(BasicCacheContainer.DEFAULT_CACHE_NAME)),
        SOCKET_TIMEOUT("socket-timeout", ModelType.LONG, new ModelNode(60000L)),
        TCP_NO_DELAY("tcp-no-delay", ModelType.BOOLEAN, new ModelNode(true)),
        SOCKET_BINDINGS("remote-servers")
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit((type == ModelType.LONG) ? MeasurementUnit.MILLISECONDS : null)
                    .build();
        }

        Attribute(String name) {
            this.definition = new StringListAttributeDefinition.Builder(name)
                    .setAttributeParser(AttributeParsers.COLLECTION)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMinSize(1)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, LEGACY_PATH) : parent.addChildResource(PATH);

        StoreResourceDefinition.buildTransformation(version, builder);
    }

    RemoteStoreResourceDefinition(boolean allowRuntimeOnlyRegistration) {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH, WILDCARD_PATH), allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new RemoteStoreBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).addAttributes(StoreResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/ReplicatedCacheResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.services.path.PathManager;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/replicated-cache=*
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class ReplicatedCacheResourceDefinition extends SharedStateCacheResourceDefinition {

    static final PathElement WILDCARD_PATH = pathElement(PathElement.WILDCARD_VALUE);
    static PathElement pathElement(String name) {
        return PathElement.pathElement("replicated-cache", name);
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = parent.addChildResource(WILDCARD_PATH);

        SharedStateCacheResourceDefinition.buildTransformation(version, builder);
    }

    ReplicatedCacheResourceDefinition(PathManager pathManager, boolean allowRuntimeOnlyRegistration) {
        super(WILDCARD_PATH, pathManager, allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new ReplicatedCacheServiceHandler();
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(ClusteredCacheResourceDefinition.Attribute.class).addAttributes(CacheResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StateTransferBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.StateTransferResourceDefinition.Attribute.CHUNK_SIZE;
import static org.jboss.as.clustering.infinispan.subsystem.StateTransferResourceDefinition.Attribute.TIMEOUT;

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.StateTransferConfiguration;
import org.infinispan.configuration.cache.StateTransferConfigurationBuilder;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class StateTransferBuilder extends CacheComponentBuilder<StateTransferConfiguration> implements ResourceServiceBuilder<StateTransferConfiguration> {

    private final StateTransferConfigurationBuilder builder = new ConfigurationBuilder().clustering().stateTransfer();

    StateTransferBuilder(String containerName, String cacheName) {
        super(CacheComponent.STATE_TRANSFER, containerName, cacheName);
    }

    @Override
    public StateTransferConfiguration getValue() {
        return this.builder.create();
    }

    @Override
    public Builder<StateTransferConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.builder.chunkSize(CHUNK_SIZE.getDefinition().resolveModelAttribute(resolver, model).asInt())
                .fetchInMemoryState(true)
                .timeout(TIMEOUT.getDefinition().resolveModelAttribute(resolver, model).asLong())
        ;
        return this;
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StateTransferResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/cache=Y/state-transfer=STATE_TRANSFER
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class StateTransferResourceDefinition extends ComponentResourceDefinition {

    static final PathElement LEGACY_PATH = PathElement.pathElement("state-transfer", "STATE_TRANSFER");
    static final PathElement PATH = pathElement("state-transfer");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        CHUNK_SIZE("chunk-size", ModelType.INT, new ModelNode(10000)),
        @Deprecated ENABLED("enabled", ModelType.BOOLEAN, new ModelNode(true), InfinispanModel.VERSION_4_0_0),
        TIMEOUT("timeout", ModelType.LONG, new ModelNode(60000L)),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = createBuilder(name, type, defaultValue).build();
        }

        Attribute(String name, ModelType type, ModelNode defaultValue, InfinispanModel deprecation) {
            this.definition = createBuilder(name, type, defaultValue).setDeprecated(deprecation.getVersion()).build();
        }

        private static SimpleAttributeDefinitionBuilder createBuilder(String name, ModelType type, ModelNode defaultValue) {
            return new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit((type == ModelType.LONG) ? MeasurementUnit.MILLISECONDS : null)
            ;
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        if (InfinispanModel.VERSION_4_0_0.requiresTransformation(version)) {
            parent.addChildRedirection(PATH, LEGACY_PATH);
        }
    }

    StateTransferResourceDefinition() {
        super(PATH);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new StateTransferBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StoreBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.StoreResourceDefinition.Attribute.FETCH_STATE;
import static org.jboss.as.clustering.infinispan.subsystem.StoreResourceDefinition.Attribute.PASSIVATION;
import static org.jboss.as.clustering.infinispan.subsystem.StoreResourceDefinition.Attribute.PRELOAD;
import static org.jboss.as.clustering.infinispan.subsystem.StoreResourceDefinition.Attribute.PROPERTIES;
import static org.jboss.as.clustering.infinispan.subsystem.StoreResourceDefinition.Attribute.PURGE;
import static org.jboss.as.clustering.infinispan.subsystem.StoreResourceDefinition.Attribute.SHARED;
import static org.jboss.as.clustering.infinispan.subsystem.StoreResourceDefinition.Attribute.SINGLETON;

import org.infinispan.configuration.cache.AsyncStoreConfiguration;
import org.infinispan.configuration.cache.PersistenceConfiguration;
import org.infinispan.configuration.cache.StoreConfigurationBuilder;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.value.InjectedValue;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public abstract class StoreBuilder extends CacheComponentBuilder<PersistenceConfiguration> implements ResourceServiceBuilder<PersistenceConfiguration> {

    private final InjectedValue<AsyncStoreConfiguration> async = new InjectedValue<>();
    private final String containerName;
    private final String cacheName;

    private volatile StoreConfigurationBuilder<?, ?> storeBuilder;

    StoreBuilder(String containerName, String cacheName) {
        super(CacheComponent.PERSISTENCE, containerName, cacheName);
        this.containerName = containerName;
        this.cacheName = cacheName;
    }

    @Override
    public ServiceBuilder<PersistenceConfiguration> build(ServiceTarget target) {
        return super.build(target)
                .addDependency(CacheComponent.STORE_WRITE.getServiceName(this.containerName, this.cacheName), AsyncStoreConfiguration.class, this.async)
        ;
    }

    @Override
    public Builder<PersistenceConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.storeBuilder = this.createStore(resolver, model);
        this.storeBuilder.persistence().passivation(PASSIVATION.getDefinition().resolveModelAttribute(resolver, model).asBoolean());
        this.storeBuilder.fetchPersistentState(FETCH_STATE.getDefinition().resolveModelAttribute(resolver, model).asBoolean())
                .preload(PRELOAD.getDefinition().resolveModelAttribute(resolver, model).asBoolean())
                .purgeOnStartup(PURGE.getDefinition().resolveModelAttribute(resolver, model).asBoolean())
                .shared(SHARED.getDefinition().resolveModelAttribute(resolver, model).asBoolean())
                .singleton().enabled(SINGLETON.getDefinition().resolveModelAttribute(resolver, model).asBoolean())
                .withProperties(ModelNodes.asProperties(PROPERTIES.getDefinition().resolveModelAttribute(resolver, model)))
        ;
        return this;
    }

    abstract StoreConfigurationBuilder<?, ?> createStore(ExpressionResolver resolver, ModelNode model) throws OperationFailedException;

    @Override
    public PersistenceConfiguration getValue() {
        return this.storeBuilder.async().read(this.async.getValue()).persistence().create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StoreResourceDefinition.java
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
package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AttributeMarshallers;
import org.jboss.as.clustering.controller.AttributeParsers;
import org.jboss.as.clustering.controller.MetricHandler;
import org.jboss.as.clustering.controller.Operations;
import org.jboss.as.clustering.controller.Registration;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.transform.OperationTransformer;
import org.jboss.as.clustering.controller.transform.SimpleOperationTransformer;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.SimpleMapAttributeDefinition;
import org.jboss.as.controller.SimpleResourceDefinition;
import org.jboss.as.controller.descriptions.ResourceDescriptionResolver;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.operations.global.MapOperations;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Base class for store resources which require common store attributes only.
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 * @author Paul Ferraro
 */
public abstract class StoreResourceDefinition extends SimpleResourceDefinition implements Registration {

    static final PathElement WILDCARD_PATH = pathElement(PathElement.WILDCARD_VALUE);

    static PathElement pathElement(String value) {
        return PathElement.pathElement("store", value);
    }

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        FETCH_STATE("fetch-state", true),
        PASSIVATION("passivation", true),
        PRELOAD("preload", false),
        PURGE("purge", true),
        SHARED("shared", false),
        SINGLETON("singleton", false),
        PROPERTIES("properties"),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, boolean defaultValue) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, ModelType.BOOLEAN)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(new ModelNode(defaultValue))
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        Attribute(String name) {
            this.definition = new SimpleMapAttributeDefinition.Builder(name, true)
                    .setAllowExpression(true)
                    .setAttributeMarshaller(AttributeMarshallers.PROPERTY_LIST)
                    .setAttributeParser(AttributeParsers.COLLECTION)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    private final boolean allowRuntimeOnlyRegistration;

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder builder) {
        if (InfinispanModel.VERSION_4_0_0.requiresTransformation(version)) {
            builder.discardChildResource(StoreWriteThroughResourceDefinition.PATH);
        } else {
            StoreWriteThroughResourceDefinition.buildTransformation(version, builder);
        }

        if (InfinispanModel.VERSION_3_0_0.requiresTransformation(version)) {
            OperationTransformer putPropertyTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    String attributeName = Operations.getAttributeName(operation);
                    if (Attribute.PROPERTIES.getDefinition().getName().equals(attributeName)) {
                        String key = operation.get("key").asString();
                        ModelNode value = Operations.getAttributeValue(operation);
                        PathAddress address = Operations.getPathAddress(operation);
                        ModelNode transformedOperation = Util.createAddOperation(address.append(StorePropertyResourceDefinition.pathElement(key)));
                        transformedOperation.get(StorePropertyResourceDefinition.VALUE.getName()).set(value);
                        return transformedOperation;
                    }
                    return operation;
                }
            };
            builder.addRawOperationTransformationOverride(MapOperations.MAP_PUT_DEFINITION.getName(), new SimpleOperationTransformer(putPropertyTransformer));

            OperationTransformer removePropertyTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    String attributeName = Operations.getAttributeName(operation);
                    if (Attribute.PROPERTIES.getDefinition().getName().equals(attributeName)) {
                        String key = operation.get("key").asString();
                        PathAddress address = Operations.getPathAddress(operation);
                        return Util.createRemoveOperation(address.append(StorePropertyResourceDefinition.pathElement(key)));
                    }
                    return operation;
                }
            };
            builder.addRawOperationTransformationOverride(MapOperations.MAP_PUT_DEFINITION.getName(), new SimpleOperationTransformer(removePropertyTransformer));
        }

        StoreWriteBehindResourceDefinition.buildTransformation(version, builder);
    }

    StoreResourceDefinition(PathElement path, ResourceDescriptionResolver resolver, boolean allowRuntimeOnlyRegistration) {
        super(path, resolver);
        this.allowRuntimeOnlyRegistration = allowRuntimeOnlyRegistration;
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);

        if (this.allowRuntimeOnlyRegistration) {
            new MetricHandler<>(new StoreMetricExecutor(), StoreMetric.class).register(registration);
        }
    }

    @Override
    public void registerChildren(ManagementResourceRegistration registration) {
        new StoreWriteBehindResourceDefinition().register(registration);
        new StoreWriteThroughResourceDefinition().register(registration);

        new StorePropertyResourceDefinition().register(registration);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StoreWriteBehindBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.StoreWriteBehindResourceDefinition.Attribute.*;

import org.infinispan.configuration.cache.AsyncStoreConfiguration;
import org.infinispan.configuration.cache.AsyncStoreConfigurationBuilder;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class StoreWriteBehindBuilder extends CacheComponentBuilder<AsyncStoreConfiguration> implements ResourceServiceBuilder<AsyncStoreConfiguration> {

    private final AsyncStoreConfigurationBuilder<?> builder = new ConfigurationBuilder().persistence().addSingleFileStore().async();

    StoreWriteBehindBuilder(String containerName, String cacheName) {
        super(CacheComponent.STORE_WRITE, containerName, cacheName);
    }

    @Override
    public AsyncStoreConfiguration getValue() throws IllegalStateException, IllegalArgumentException {
        return this.builder.create();
    }

    @Override
    public Builder<AsyncStoreConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.builder.flushLockTimeout(FLUSH_LOCK_TIMEOUT.getDefinition().resolveModelAttribute(resolver, model).asLong());
        this.builder.modificationQueueSize(MODIFICATION_QUEUE_SIZE.getDefinition().resolveModelAttribute(resolver, model).asInt());
        this.builder.shutdownTimeout(SHUTDOWN_TIMEOUT.getDefinition().resolveModelAttribute(resolver, model).asLong());
        this.builder.threadPoolSize(THREAD_POOL_SIZE.getDefinition().resolveModelAttribute(resolver, model).asInt());
        return this;
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StoreWriteBehindResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.AttributeConverter.DefaultValueAttributeConverter;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource
 *
 *    /subsystem=infinispan/cache-container=X/cache=Y/store=Z/write-behind=WRITE_BEHIND
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class StoreWriteBehindResourceDefinition extends StoreWriteResourceDefinition {

    static final PathElement LEGACY_PATH = PathElement.pathElement("write-behind", "WRITE_BEHIND");
    static final PathElement PATH = pathElement("behind");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        FLUSH_LOCK_TIMEOUT("flush-lock-timeout", ModelType.LONG, new ModelNode(5000L)),
        MODIFICATION_QUEUE_SIZE("modification-queue-size", ModelType.INT, new ModelNode(1024)),
        SHUTDOWN_TIMEOUT("shutdown-timeout", ModelType.LONG, new ModelNode(25000L)),
        THREAD_POOL_SIZE("thread-pool-size", ModelType.INT, new ModelNode(1)),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit((type == ModelType.LONG) ? MeasurementUnit.MILLISECONDS : null)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, LEGACY_PATH) : parent.addChildResource(PATH);

        if (InfinispanModel.VERSION_3_0_0.requiresTransformation(version)) {
            builder.getAttributeBuilder().setValueConverter(new DefaultValueAttributeConverter(Attribute.FLUSH_LOCK_TIMEOUT.getDefinition()), Attribute.FLUSH_LOCK_TIMEOUT.getDefinition());
        }
    }

    StoreWriteBehindResourceDefinition() {
        super(PATH);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new StoreWriteBehindBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StoreWriteThroughBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.infinispan.configuration.cache.AsyncStoreConfiguration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class StoreWriteThroughBuilder extends CacheComponentBuilder<AsyncStoreConfiguration> implements ResourceServiceBuilder<AsyncStoreConfiguration> {

    StoreWriteThroughBuilder(String containerName, String cacheName) {
        super(CacheComponent.STORE_WRITE, containerName, cacheName);
    }

    @Override
    public AsyncStoreConfiguration getValue() throws IllegalStateException, IllegalArgumentException {
        return new ConfigurationBuilder().persistence().addSingleFileStore().async().disable().create();
    }

    @Override
    public Builder<AsyncStoreConfiguration> configure(ExpressionResolver resolver, ModelNode model) {
        return this;
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StoreWriteThroughResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;

/**
 * @author Paul Ferraro
 */
public class StoreWriteThroughResourceDefinition extends StoreWriteResourceDefinition {

    static final PathElement PATH = pathElement("through");

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder builder) {
        // Do nothing
    }

    StoreWriteThroughResourceDefinition() {
        super(PATH);
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new StoreWriteThroughBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StringKeyedJDBCStoreResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.Operations;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.ObjectTypeAttributeDefinition;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.OperationStepHandler;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.controller.operations.global.ReadResourceHandler;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;

/**
 * Resource description for the addressable resource
 *
 * /subsystem=infinispan/cache-container=X/cache=Y/string-keyed-jdbc-store=STRING_KEYED_JDBC_STORE
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class StringKeyedJDBCStoreResourceDefinition extends JDBCStoreResourceDefinition {

    static final PathElement LEGACY_PATH = PathElement.pathElement("string-keyed-jdbc-store", "STRING_KEYED_JDBC_STORE");
    static final PathElement PATH = pathElement("string-jdbc");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        @Deprecated TABLE("string-keyed-table", StringTableResourceDefinition.Attribute.values(), TableResourceDefinition.Attribute.values(), TableResourceDefinition.ColumnAttribute.values()),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, org.jboss.as.clustering.controller.Attribute[]... attributeSets) {
            int size = 0;
            for (org.jboss.as.clustering.controller.Attribute[] attributes : attributeSets) {
                size += attributes.length;
            }
            List<AttributeDefinition> definitions = new ArrayList<>(size);
            for (org.jboss.as.clustering.controller.Attribute[] attributes : attributeSets) {
                for (org.jboss.as.clustering.controller.Attribute attribute : attributes) {
                    definitions.add(attribute.getDefinition());
                }
            }
            this.definition = ObjectTypeAttributeDefinition.Builder.of(name, definitions.toArray(new AttributeDefinition[size]))
                    .setAllowNull(true)
                    .setDeprecated(InfinispanModel.VERSION_4_0_0.getVersion())
                    .setSuffix("table")
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = parent.addChildResource(PATH);

        JDBCStoreResourceDefinition.buildTransformation(version, builder);

        StringTableResourceDefinition.buildTransformation(version, builder);
    }

    StringKeyedJDBCStoreResourceDefinition(boolean allowRuntimeOnlyRegistration) {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH, pathElement("jdbc"), WILDCARD_PATH), allowRuntimeOnlyRegistration);
    }

    @Override
    public void registerChildren(ManagementResourceRegistration registration) {
        super.registerChildren(registration);
        new StringTableResourceDefinition().register(registration);
    }

    @Override
    public void registerOperations(final ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new StringKeyedJDBCStoreBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler) {
            @Override
            public void execute(OperationContext context, ModelNode operation) throws OperationFailedException {
                super.execute(context, operation);
                if (operation.hasDefined(Attribute.TABLE.getDefinition().getName())) {
                    // Translate deprecated TABLE attribute into separate add table operation
                    ModelNode addTableOperation = Util.createAddOperation(context.getCurrentAddress().append(StringTableResourceDefinition.PATH));
                    ModelNode parameters = operation.get(Attribute.TABLE.getDefinition().getName());
                    for (Property parameter : parameters.asPropertyList()) {
                        addTableOperation.get(parameter.getName()).set(parameter.getValue());
                    }
                    context.addStep(addTableOperation, registration.getOperationHandler(PathAddress.pathAddress(StringTableResourceDefinition.PATH), ModelDescriptionConstants.ADD), context.getCurrentStage());
                }
            }
        }.addAttributes(JDBCStoreResourceDefinition.Attribute.class).addAttributes(StoreResourceDefinition.Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    static final OperationStepHandler LEGACY_READ_TABLE_HANDLER = new OperationStepHandler() {
        @Override
        public void execute(OperationContext context, ModelNode operation) throws OperationFailedException {
            PathAddress address = context.getCurrentAddress().append(StringTableResourceDefinition.PATH);
            ModelNode readResourceOperation = Util.createOperation(ModelDescriptionConstants.READ_RESOURCE_OPERATION, address);
            operation.get(ModelDescriptionConstants.ATTRIBUTES_ONLY).set(true);
            context.addStep(readResourceOperation, new ReadResourceHandler(), context.getCurrentStage());
        }
    };

    static final OperationStepHandler LEGACY_WRITE_TABLE_HANDLER = new OperationStepHandler() {
        @Override
        public void execute(OperationContext context, ModelNode operation) throws OperationFailedException {
            PathAddress address = context.getCurrentAddress().append(StringTableResourceDefinition.PATH);
            ModelNode table = Operations.getAttributeValue(operation);
            for (Class<? extends org.jboss.as.clustering.controller.Attribute> attributeClass : Arrays.asList(StringTableResourceDefinition.Attribute.class, TableResourceDefinition.Attribute.class)) {
                for (org.jboss.as.clustering.controller.Attribute attribute : attributeClass.getEnumConstants()) {
                    ModelNode writeAttributeOperation = Operations.createWriteAttributeOperation(address, attribute, table.get(attribute.getDefinition().getName()));
                    context.addStep(writeAttributeOperation, new ReloadRequiredWriteAttributeHandler(attribute), context.getCurrentStage());
                }
            }
        }
    };

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);
        registration.registerReadWriteAttribute(Attribute.TABLE.getDefinition(), LEGACY_READ_TABLE_HANDLER, LEGACY_WRITE_TABLE_HANDLER);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/StringTableResourceDefinition.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import java.util.Arrays;

import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.Operations;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.clustering.controller.transform.OperationTransformer;
import org.jboss.as.clustering.controller.transform.SimpleOperationTransformer;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * @author Paul Ferraro
 */
public class StringTableResourceDefinition extends TableResourceDefinition {

    static final PathElement PATH = pathElement("string");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        PREFIX("prefix", ModelType.STRING, new ModelNode("ispn_entry")),
        ;
        private final AttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    @SuppressWarnings("deprecation")
    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = parent.addChildResource(PATH);

        if (InfinispanModel.VERSION_4_0_0.requiresTransformation(version)) {
            OperationTransformer addTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress storeAddress = Operations.getPathAddress(operation).getParent();
                    ModelNode value = new ModelNode();
                    for (Class<? extends org.jboss.as.clustering.controller.Attribute> attributeClass : Arrays.asList(Attribute.class, TableResourceDefinition.Attribute.class)) {
                        for (org.jboss.as.clustering.controller.Attribute attribute : attributeClass.getEnumConstants()) {
                            String name = attribute.getDefinition().getName();
                            if (operation.hasDefined(name)) {
                                value.get(name).set(operation.get(name));
                            }
                        }
                    }
                    return value.isDefined() ? Operations.createWriteAttributeOperation(storeAddress, StringKeyedJDBCStoreResourceDefinition.Attribute.TABLE, value) : Operations.createUndefineAttributeOperation(storeAddress, StringKeyedJDBCStoreResourceDefinition.Attribute.TABLE);
                }
            };
            builder.addRawOperationTransformationOverride(ModelDescriptionConstants.ADD, new SimpleOperationTransformer(addTransformer));

            OperationTransformer removeTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress storeAddress = Operations.getPathAddress(operation).getParent();
                    return Operations.createUndefineAttributeOperation(storeAddress, StringKeyedJDBCStoreResourceDefinition.Attribute.TABLE);
                }
            };
            builder.addRawOperationTransformationOverride(ModelDescriptionConstants.REMOVE, new SimpleOperationTransformer(removeTransformer));
        }
    }

    StringTableResourceDefinition() {
        super(PATH, new InfinispanResourceDescriptionResolver(PATH, WILDCARD_PATH));
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new StringTableBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).addAttributes(TableResourceDefinition.Attribute.class).addAttributes(TableResourceDefinition.ColumnAttribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        super.registerAttributes(registration);
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerSubModel(this);
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/TableBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.TableResourceDefinition.ColumnAttribute.*;
import static org.jboss.as.clustering.infinispan.subsystem.TableResourceDefinition.Attribute.*;

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.persistence.jdbc.configuration.JdbcStringBasedStoreConfigurationBuilder;
import org.infinispan.persistence.jdbc.configuration.TableManipulationConfiguration;
import org.infinispan.persistence.jdbc.configuration.TableManipulationConfigurationBuilder;
import org.infinispan.persistence.jdbc.configuration.JdbcStringBasedStoreConfigurationBuilder.StringTableManipulationConfigurationBuilder;
import org.jboss.as.clustering.controller.Attribute;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.dmr.ModelNode;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class TableBuilder extends CacheComponentBuilder<TableManipulationConfiguration> implements ResourceServiceBuilder<TableManipulationConfiguration> {

    private final Attribute prefixAttribute;
    private final TableManipulationConfigurationBuilder<JdbcStringBasedStoreConfigurationBuilder, StringTableManipulationConfigurationBuilder> builder = new ConfigurationBuilder().persistence().addStore(JdbcStringBasedStoreConfigurationBuilder.class).table();

    public TableBuilder(Attribute prefixAttribute, CacheComponent component, String containerName, String cacheName) {
        super(component, containerName, cacheName);
        this.prefixAttribute = prefixAttribute;
    }

    @Override
    public Builder<TableManipulationConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.builder.idColumnName(ID.getColumnName().getDefinition().resolveModelAttribute(resolver, model).asString())
                .idColumnType(ID.getColumnType().getDefinition().resolveModelAttribute(resolver, model).asString())
                .dataColumnName(DATA.getColumnName().getDefinition().resolveModelAttribute(resolver, model).asString())
                .dataColumnType(DATA.getColumnType().getDefinition().resolveModelAttribute(resolver, model).asString())
                .timestampColumnName(TIMESTAMP.getColumnName().getDefinition().resolveModelAttribute(resolver, model).asString())
                .timestampColumnType(TIMESTAMP.getColumnType().getDefinition().resolveModelAttribute(resolver, model).asString())
                .batchSize(BATCH_SIZE.getDefinition().resolveModelAttribute(resolver, model).asInt())
                .fetchSize(FETCH_SIZE.getDefinition().resolveModelAttribute(resolver, model).asInt())
                .tableNamePrefix(this.prefixAttribute.getDefinition().resolveModelAttribute(resolver, model).asString())
        ;
        return this;
    }

    @Override
    public TableManipulationConfiguration getValue() {
        return this.builder.create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/TransactionBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

import static org.jboss.as.clustering.infinispan.subsystem.TransactionResourceDefinition.Attribute.LOCKING;
import static org.jboss.as.clustering.infinispan.subsystem.TransactionResourceDefinition.Attribute.MODE;
import static org.jboss.as.clustering.infinispan.subsystem.TransactionResourceDefinition.Attribute.STOP_TIMEOUT;

import javax.transaction.TransactionManager;
import javax.transaction.TransactionSynchronizationRegistry;

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.TransactionConfiguration;
import org.infinispan.configuration.cache.TransactionConfigurationBuilder;
import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.tm.DummyTransactionManager;
import org.jboss.as.clustering.controller.ResourceServiceBuilder;
import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.clustering.infinispan.TransactionManagerProvider;
import org.jboss.as.clustering.infinispan.TransactionSynchronizationRegistryProvider;
import org.jboss.as.controller.ExpressionResolver;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.txn.service.TxnServices;
import org.jboss.dmr.ModelNode;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.value.InjectedValue;
import org.wildfly.clustering.service.Builder;

/**
 * @author Paul Ferraro
 */
public class TransactionBuilder extends CacheComponentBuilder<TransactionConfiguration> implements ResourceServiceBuilder<TransactionConfiguration> {

    private final InjectedValue<TransactionManager> tm = new InjectedValue<>();
    private final InjectedValue<TransactionSynchronizationRegistry> tsr = new InjectedValue<>();

    private final TransactionConfigurationBuilder builder = new ConfigurationBuilder().transaction();

    private volatile TransactionMode mode;

    public TransactionBuilder(String containerName, String cacheName) {
        super(CacheComponent.TRANSACTION, containerName, cacheName);
    }

    @Override
    public ServiceBuilder<TransactionConfiguration> build(ServiceTarget target) {
        ServiceBuilder<TransactionConfiguration> builder = super.build(target);
        switch (this.mode) {
            case NONE: {
                break;
            }
            case BATCH: {
                this.tm.inject(DummyTransactionManager.getInstance());
                break;
            }
            case NON_XA: {
                builder.addDependency(TxnServices.JBOSS_TXN_SYNCHRONIZATION_REGISTRY, TransactionSynchronizationRegistry.class, this.tsr);
            }
            default: {
                builder.addDependency(TxnServices.JBOSS_TXN_TRANSACTION_MANAGER, TransactionManager.class, this.tm);
            }
        }
        return builder;
    }

    @Override
    public Builder<TransactionConfiguration> configure(ExpressionResolver resolver, ModelNode model) throws OperationFailedException {
        this.mode = ModelNodes.asEnum(MODE.getDefinition().resolveModelAttribute(resolver, model), TransactionMode.class);
        this.builder.lockingMode(ModelNodes.asEnum(LOCKING.getDefinition().resolveModelAttribute(resolver, model), LockingMode.class));
        this.builder.cacheStopTimeout(STOP_TIMEOUT.getDefinition().resolveModelAttribute(resolver, model).asLong());
        this.builder.transactionMode((this.mode == TransactionMode.NONE) ? org.infinispan.transaction.TransactionMode.NON_TRANSACTIONAL : org.infinispan.transaction.TransactionMode.TRANSACTIONAL);
        this.builder.useSynchronization(this.mode == TransactionMode.NON_XA);
        this.builder.recovery().enabled(this.mode == TransactionMode.FULL_XA);
        this.builder.invocationBatching().disable();
        return this;
    }

    @Override
    public TransactionConfiguration getValue() {
        TransactionManager tm = this.tm.getOptionalValue();
        this.builder.transactionManagerLookup((tm != null) ? new TransactionManagerProvider(tm) : null);

        TransactionSynchronizationRegistry tsr = this.tsr.getOptionalValue();
        this.builder.transactionSynchronizationRegistryLookup((tsr != null) ? new TransactionSynchronizationRegistryProvider(tsr) : null);

        return this.builder.create();
    }
}


File: clustering/infinispan/extension/src/main/java/org/jboss/as/clustering/infinispan/subsystem/TransactionResourceDefinition.java
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

package org.jboss.as.clustering.infinispan.subsystem;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import org.infinispan.transaction.LockingMode;
import org.jboss.as.clustering.controller.AddStepHandler;
import org.jboss.as.clustering.controller.MetricHandler;
import org.jboss.as.clustering.controller.Operations;
import org.jboss.as.clustering.controller.ReloadRequiredWriteAttributeHandler;
import org.jboss.as.clustering.controller.RemoveStepHandler;
import org.jboss.as.clustering.controller.ResourceServiceHandler;
import org.jboss.as.clustering.controller.SimpleAliasEntry;
import org.jboss.as.clustering.controller.SimpleResourceServiceHandler;
import org.jboss.as.clustering.controller.transform.AttributeOperationTransformer;
import org.jboss.as.clustering.controller.transform.ChainedOperationTransformer;
import org.jboss.as.clustering.controller.transform.SimpleOperationTransformer;
import org.jboss.as.clustering.controller.transform.OperationTransformer;
import org.jboss.as.controller.AttributeDefinition;
import org.jboss.as.controller.ModelVersion;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.SimpleAttributeDefinition;
import org.jboss.as.controller.SimpleAttributeDefinitionBuilder;
import org.jboss.as.controller.client.helpers.MeasurementUnit;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.operations.validation.EnumValidator;
import org.jboss.as.controller.operations.validation.ParameterValidator;
import org.jboss.as.controller.registry.AttributeAccess;
import org.jboss.as.controller.registry.ManagementResourceRegistration;
import org.jboss.as.controller.registry.Resource;
import org.jboss.as.controller.transform.OperationResultTransformer;
import org.jboss.as.controller.transform.ResourceTransformationContext;
import org.jboss.as.controller.transform.ResourceTransformer;
import org.jboss.as.controller.transform.description.AttributeConverter.DefaultValueAttributeConverter;
import org.jboss.as.controller.transform.description.ResourceTransformationDescriptionBuilder;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.ModelType;

/**
 * Resource description for the addressable resource /subsystem=infinispan/cache-container=X/cache=Y/transaction=TRANSACTION
 *
 * @author Richard Achmatowicz (c) 2011 Red Hat Inc.
 */
public class TransactionResourceDefinition extends ComponentResourceDefinition {

    static final PathElement PATH = pathElement("transaction");
    static final PathElement LEGACY_PATH = PathElement.pathElement(PATH.getValue(), "TRANSACTION");

    enum Attribute implements org.jboss.as.clustering.controller.Attribute {
        LOCKING("locking", ModelType.STRING, new ModelNode(LockingMode.PESSIMISTIC.name()), new EnumValidator<>(LockingMode.class, true, false), null),
        MODE("mode", ModelType.STRING, new ModelNode(TransactionMode.NONE.name()), new EnumValidator<>(TransactionMode.class, true, true), null),
        STOP_TIMEOUT("stop-timeout", ModelType.LONG, new ModelNode(10000), null, MeasurementUnit.MILLISECONDS),
        ;
        private final SimpleAttributeDefinition definition;

        Attribute(String name, ModelType type, ModelNode defaultValue, ParameterValidator validator, MeasurementUnit unit) {
            this.definition = new SimpleAttributeDefinitionBuilder(name, type)
                    .setAllowExpression(true)
                    .setAllowNull(true)
                    .setDefaultValue(defaultValue)
                    .setFlags(AttributeAccess.Flag.RESTART_RESOURCE_SERVICES)
                    .setMeasurementUnit(unit)
                    .setValidator(validator)
                    .build();
        }

        @Override
        public AttributeDefinition getDefinition() {
            return this.definition;
        }
    }

    private final boolean allowRuntimeOnlyRegistration;

    @SuppressWarnings("deprecation")
    static void buildTransformation(ModelVersion version, ResourceTransformationDescriptionBuilder parent) {
        ResourceTransformationDescriptionBuilder builder = InfinispanModel.VERSION_4_0_0.requiresTransformation(version) ? parent.addChildRedirection(PATH, LEGACY_PATH) : parent.addChildResource(PATH);

        List<org.jboss.as.controller.transform.OperationTransformer> addOperationTransformers = new LinkedList<>();
        List<org.jboss.as.controller.transform.OperationTransformer> removeOperationTransformers = new LinkedList<>();
        Map<String, org.jboss.as.controller.transform.OperationTransformer> readAttributeTransformers = new HashMap<>();
        Map<String, org.jboss.as.controller.transform.OperationTransformer> writeAttributeTransformers = new HashMap<>();
        Map<String, org.jboss.as.controller.transform.OperationTransformer> undefineAttributeTransformers = new HashMap<>();

        if (InfinispanModel.VERSION_3_0_0.requiresTransformation(version)) {
            // Convert BATCH -> NONE, and include write-attribute:name=batching
            OperationTransformer addTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    if (operation.hasDefined(Attribute.MODE.getDefinition().getName())) {
                        ModelNode mode = operation.get(Attribute.MODE.getDefinition().getName());
                        if ((mode.getType() == ModelType.STRING) && (TransactionMode.valueOf(mode.asString()) == TransactionMode.BATCH)) {
                            mode.set(TransactionMode.NONE.name());
                            PathAddress address = Operations.getPathAddress(operation);
                            return Operations.createCompositeOperation(operation, Operations.createWriteAttributeOperation(cacheAddress(address), CacheResourceDefinition.Attribute.BATCHING, new ModelNode(true)));
                        }
                    }
                    return operation;
                }
            };
            addOperationTransformers.add(new SimpleOperationTransformer(addTransformer));

            // Additionally include undefine-attribute:name=batching
            OperationTransformer removeTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress address = Operations.getPathAddress(operation);
                    return Operations.createCompositeOperation(operation, Operations.createUndefineAttributeOperation(cacheAddress(address), CacheResourceDefinition.Attribute.BATCHING));
                }
            };
            removeOperationTransformers.add(new SimpleOperationTransformer(removeTransformer));

            // If read-attribute:name=batching is true, return BATCH, otherwise use result from read-attribute:name=mode
            OperationTransformer readAttributeOperationTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress address = Operations.getPathAddress(operation);
                    return Operations.createCompositeOperation(Operations.createReadAttributeOperation(cacheAddress(address), CacheResourceDefinition.Attribute.BATCHING), operation);
                }
            };
            OperationResultTransformer readAttributeResultTransformer = new OperationResultTransformer() {
                @Override
                public ModelNode transformResult(ModelNode result) {
                    ModelNode readBatchingResult = result.get(0);
                    return readBatchingResult.asBoolean() ? new ModelNode(TransactionMode.BATCH.name()) : result.get(1);
                }
            };
            readAttributeTransformers.put(Attribute.MODE.getDefinition().getName(), new SimpleOperationTransformer(readAttributeOperationTransformer, readAttributeResultTransformer));

            // Convert BATCH -> NONE, and include write-attribute:name=batching
            OperationTransformer writeAttributeTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    ModelNode mode = Operations.getAttributeValue(operation);
                    boolean batching = (mode.isDefined() && (mode.getType() == ModelType.STRING)) ? (TransactionMode.valueOf(mode.asString()) == TransactionMode.BATCH) : false;
                    if (batching) {
                        mode.set(TransactionMode.NONE.name());
                    }
                    PathAddress address = Operations.getPathAddress(operation);
                    return Operations.createCompositeOperation(operation, Operations.createWriteAttributeOperation(cacheAddress(address), CacheResourceDefinition.Attribute.BATCHING, new ModelNode(batching)));
                }
            };
            writeAttributeTransformers.put(Attribute.MODE.getDefinition().getName(), new SimpleOperationTransformer(writeAttributeTransformer));

            // Include undefine-attribute:name=batching
            OperationTransformer undefineAttributeTransformer = new OperationTransformer() {
                @Override
                public ModelNode transformOperation(ModelNode operation) {
                    PathAddress address = Operations.getPathAddress(operation);
                    return Operations.createCompositeOperation(operation, Operations.createUndefineAttributeOperation(cacheAddress(address), CacheResourceDefinition.Attribute.BATCHING));
                }
            };
            undefineAttributeTransformers.put(Attribute.MODE.getDefinition().getName(), new SimpleOperationTransformer(undefineAttributeTransformer));

            // Convert BATCH -> NONE
            ResourceTransformer modeTransformer = new ResourceTransformer() {
                @Override
                public void transformResource(ResourceTransformationContext context, PathAddress address, Resource resource) throws OperationFailedException {
                    ModelNode model = resource.getModel();
                    if (model.hasDefined(Attribute.MODE.getDefinition().getName())) {
                        ModelNode value = model.get(Attribute.MODE.getDefinition().getName());
                        if ((value.getType() == ModelType.STRING) && (TransactionMode.valueOf(value.asString()) == TransactionMode.BATCH)) {
                            value.set(TransactionMode.NONE.name());
                        }
                    }
                    context.addTransformedResource(PathAddress.EMPTY_ADDRESS, resource).processChildren(resource);
                }
            };
            builder.setCustomResourceTransformer(modeTransformer);

            // change default value of stop-timeout attribute
            builder.getAttributeBuilder().setValueConverter(new DefaultValueAttributeConverter(Attribute.STOP_TIMEOUT.getDefinition()), Attribute.STOP_TIMEOUT.getDefinition());
        }

        buildOperationTransformation(builder, ModelDescriptionConstants.ADD, addOperationTransformers);
        buildOperationTransformation(builder, ModelDescriptionConstants.REMOVE, removeOperationTransformers);
        buildOperationTransformation(builder, ModelDescriptionConstants.READ_ATTRIBUTE_OPERATION, readAttributeTransformers);
        buildOperationTransformation(builder, ModelDescriptionConstants.WRITE_ATTRIBUTE_OPERATION, writeAttributeTransformers);
        buildOperationTransformation(builder, ModelDescriptionConstants.UNDEFINE_ATTRIBUTE_OPERATION, undefineAttributeTransformers);
    }

    static void buildOperationTransformation(ResourceTransformationDescriptionBuilder builder, String operationName, List<org.jboss.as.controller.transform.OperationTransformer> transformers) {
        if (!transformers.isEmpty()) {
            builder.addOperationTransformationOverride(operationName).setCustomOperationTransformer(new ChainedOperationTransformer(transformers)).inheritResourceAttributeDefinitions();
        }
    }

    static void buildOperationTransformation(ResourceTransformationDescriptionBuilder builder, String operationName, Map<String, org.jboss.as.controller.transform.OperationTransformer> transformers) {
        if (!transformers.isEmpty()) {
            builder.addOperationTransformationOverride(operationName).setCustomOperationTransformer(new AttributeOperationTransformer(transformers)).inheritResourceAttributeDefinitions();
        }
    }

    static PathAddress cacheAddress(PathAddress transactionAddress) {
        return transactionAddress.subAddress(0, transactionAddress.size() - 1);
    }

    TransactionResourceDefinition(boolean allowRuntimeOnlyRegistration) {
        super(PATH);
        this.allowRuntimeOnlyRegistration = allowRuntimeOnlyRegistration;
    }

    @Override
    public void registerOperations(ManagementResourceRegistration registration) {
        ResourceServiceHandler handler = new SimpleResourceServiceHandler<>(new TransactionBuilderFactory());
        new AddStepHandler(this.getResourceDescriptionResolver(), handler).addAttributes(Attribute.class).register(registration);
        new RemoveStepHandler(this.getResourceDescriptionResolver(), handler).register(registration);
    }

    @Override
    public void registerAttributes(ManagementResourceRegistration registration) {
        new ReloadRequiredWriteAttributeHandler(Attribute.class).register(registration);

        if (this.allowRuntimeOnlyRegistration) {
            new MetricHandler<>(new TransactionMetricExecutor(), TransactionMetric.class).register(registration);
        }
    }

    @Override
    public void register(ManagementResourceRegistration registration) {
        registration.registerAlias(LEGACY_PATH, new SimpleAliasEntry(registration.registerSubModel(this)));
    }
}


File: clustering/infinispan/extension/src/test/java/org/jboss/as/clustering/infinispan/DefaultCacheContainerTest.java
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

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Collections;
import java.util.List;
import java.util.Set;

import org.infinispan.AdvancedCache;
import org.infinispan.Cache;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.global.GlobalConfiguration;
import org.infinispan.configuration.global.GlobalConfigurationBuilder;
import org.infinispan.lifecycle.ComponentStatus;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.remoting.transport.Address;
import org.junit.After;
import org.junit.Test;
import org.wildfly.clustering.ee.Batcher;
import org.wildfly.clustering.ee.infinispan.TransactionBatch;
import org.wildfly.clustering.infinispan.spi.CacheContainer;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceNameFactory;

/**
 * @author Paul Ferraro
 */
public class DefaultCacheContainerTest {
    private final BatcherFactory batcherFactory = mock(BatcherFactory.class);
    private final EmbeddedCacheManager manager = mock(EmbeddedCacheManager.class);
    private final CacheContainer subject = new DefaultCacheContainer(this.manager, "default", this.batcherFactory);

    @After
    public void cleanup() {
        reset(this.manager);
    }

    @Test
    public void getDefaultCacheName() {
        assertEquals("default", this.subject.getDefaultCacheName());
    }

    @Test
    public void getDefaultCache() {
        AdvancedCache<Object, Object> cache = mock(AdvancedCache.class);

        when(this.manager.<Object, Object>getCache("default", true)).thenReturn(cache);
        when(cache.getAdvancedCache()).thenReturn(cache);
        
        Cache<Object, Object> result = this.subject.getCache();

        assertNotSame(cache, result);
        assertEquals(result, cache);
        assertSame(this.subject, result.getCacheManager());
    }

    @Test
    public void getCache() {
        AdvancedCache<Object, Object> defaultCache = mock(AdvancedCache.class);
        AdvancedCache<Object, Object> otherCache = mock(AdvancedCache.class);
        Batcher<TransactionBatch> batcher = mock(Batcher.class);
        TransactionBatch batch = mock(TransactionBatch.class);

        when(this.manager.<Object, Object>getCache("default", true)).thenReturn(defaultCache);
        when(this.manager.<Object, Object>getCache("other", true)).thenReturn(otherCache);
        when(defaultCache.getAdvancedCache()).thenReturn(defaultCache);
        when(otherCache.getAdvancedCache()).thenReturn(otherCache);
        when(this.batcherFactory.createBatcher(defaultCache)).thenReturn(null);
        when(this.batcherFactory.createBatcher(otherCache)).thenReturn(batcher);

        Cache<Object, Object> result = this.subject.getCache("default");
        
        assertNotSame(defaultCache, result);
        assertEquals(result, defaultCache);
        assertSame(this.subject, result.getCacheManager());

        // Validate no-op batching logic
        boolean started = result.startBatch();

        assertFalse(started);

        verify(defaultCache, never()).startBatch();

        result.endBatch(false);

        verify(defaultCache, never()).endBatch(false);

        when(this.batcherFactory.createBatcher(otherCache)).thenReturn(batcher);

        result = this.subject.getCache("other");

        assertNotSame(otherCache, result);
        assertEquals(result, otherCache);
        assertSame(this.subject, result.getCacheManager());

        // Validate batching logic
        when(batcher.createBatch()).thenReturn(batch);

        started = result.startBatch();

        assertTrue(started);

        started = result.startBatch();

        assertFalse(started);

        // Verify commit
        result.endBatch(true);

        verify(batch).close();
        reset(batch);

        // Verify re-commit is a no-op
        result.endBatch(true);

        verify(batch, never()).close();
        verify(batch, never()).discard();

        // Verify rollback
        started = result.startBatch();

        assertTrue(started);

        result.endBatch(false);

        verify(batch).discard();

        reset(batch);

        // Verify re-rollback is a no-op
        result.endBatch(true);

        verify(batch, never()).close();
        verify(batch, never()).discard();

        result = this.subject.getCache(CacheServiceNameFactory.DEFAULT_CACHE);

        assertNotSame(defaultCache, result);
        assertEquals(result, defaultCache);
        assertSame(this.subject, result.getCacheManager());

        result = this.subject.getCache(null);

        assertNotSame(defaultCache, result);
        assertEquals(result, defaultCache);
        assertSame(this.subject, result.getCacheManager());
    }

    @Test
    public void start() {
        this.subject.start();

        verify(this.manager).start();
    }

    @Test
    public void stop() {
        this.subject.stop();

        verify(this.manager).stop();
    }

    @Test
    public void addListener() {
        Object listener = new Object();
        this.subject.addListener(listener);

        verify(this.manager).addListener(listener);
    }

    @Test
    public void removeListener() {
        Object listener = new Object();
        this.subject.removeListener(listener);

        verify(this.manager).removeListener(listener);
    }

    @Test
    public void getListeners() {
        Set<Object> expected = Collections.singleton(new Object());
        when(this.manager.getListeners()).thenReturn(expected);

        Set<Object> result = this.subject.getListeners();

        assertSame(expected, result);
    }

    @Test
    public void defineConfiguration() {
        ConfigurationBuilder builder = new ConfigurationBuilder();
        Configuration defaultConfig = builder.build();
        Configuration otherConfig = builder.build();
        
        when(this.manager.defineConfiguration("default", defaultConfig)).thenReturn(defaultConfig);
        when(this.manager.defineConfiguration("other", otherConfig)).thenReturn(otherConfig);
        
        Configuration result = this.subject.defineConfiguration("default", defaultConfig);
        
        assertSame(defaultConfig, result);
        
        result = this.subject.defineConfiguration("other", otherConfig);
        
        assertSame(otherConfig, result);
    }

    @Test
    public void getClusterName() {
        String expected = "cluster";
        when(this.manager.getClusterName()).thenReturn(expected);

        String result = this.subject.getClusterName();

        assertSame(expected, result);
    }

    @Test
    public void getMembers() {
        List<Address> expected = Collections.singletonList(mock(Address.class));
        when(this.manager.getMembers()).thenReturn(expected);

        List<Address> result = this.subject.getMembers();

        assertSame(expected, result);
    }

    @Test
    public void getAddress() {
        Address expected = mock(Address.class);
        when(this.manager.getAddress()).thenReturn(expected);

        Address result = this.subject.getAddress();

        assertSame(expected, result);
    }

    @Test
    public void getCoordinator() {
        Address expected = mock(Address.class);
        when(this.manager.getCoordinator()).thenReturn(expected);

        Address result = this.subject.getCoordinator();

        assertSame(expected, result);
    }

    @Test
    public void getStatus() {
        ComponentStatus expected = ComponentStatus.INITIALIZING;
        when(this.manager.getStatus()).thenReturn(expected);

        ComponentStatus result = this.subject.getStatus();

        assertSame(expected, result);
    }

    @Test
    public void getCacheManagerConfiguration() {
        GlobalConfiguration global = new GlobalConfigurationBuilder().build();
        
        when(this.manager.getCacheManagerConfiguration()).thenReturn(global);
        
        GlobalConfiguration result = this.subject.getCacheManagerConfiguration();
        
        assertSame(global, result);
    }

    @Test
    public void getDefaultCacheConfiguration() {
        Configuration config = new ConfigurationBuilder().build();
        
        when(this.manager.getCacheConfiguration("default")).thenReturn(config);
        
        Configuration result = this.subject.getDefaultCacheConfiguration();
        
        assertSame(config, result);
    }

    @Test
    public void getCacheConfiguration() {
        Configuration config = new ConfigurationBuilder().build();
        
        when(this.manager.getCacheConfiguration("cache")).thenReturn(config);
        
        Configuration result = this.subject.getCacheConfiguration("cache");
        
        assertSame(config, result);
    }

    @Test
    public void getCacheNames() {
        Set<String> caches = Collections.singleton("other");
        when(this.manager.getCacheNames()).thenReturn(caches);

        Set<String> result = this.subject.getCacheNames();

        assertEquals(1, result.size());
        assertTrue(result.contains("other"));
    }

    @Test
    public void isRunning() {
        when(this.manager.isRunning("other")).thenReturn(false);
        when(this.manager.isRunning("default")).thenReturn(true);

        boolean result = this.subject.isRunning("other");

        assertFalse(result);

        result = this.subject.isRunning("default");

        assertTrue(result);

        result = this.subject.isRunning(CacheServiceNameFactory.DEFAULT_CACHE);

        assertTrue(result);

        result = this.subject.isRunning(null);

        assertTrue(result);
    }

    @Test
    public void isDefaultRunning() {
        when(this.manager.isRunning("default")).thenReturn(true);

        boolean result = this.subject.isDefaultRunning();

        assertTrue(result);
    }
    
    @Test
    public void startCaches() {
        when(this.manager.startCaches("other", "default")).thenReturn(this.manager);
        
        EmbeddedCacheManager result = this.subject.startCaches("other", CacheServiceNameFactory.DEFAULT_CACHE);
        
        assertSame(this.subject, result);
    }
}


File: clustering/infinispan/spi/src/main/java/org/wildfly/clustering/infinispan/spi/service/CacheContainerServiceName.java
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
package org.wildfly.clustering.infinispan.spi.service;

import org.jboss.msc.service.ServiceName;

/**
 * Enumeration of service name factories for services associated with a cache container.
 * @author Paul Ferraro
 */
public enum CacheContainerServiceName implements CacheContainerServiceNameFactory {

    CACHE_CONTAINER {
        @Override
        public ServiceName getServiceName(String container) {
            return BASE_NAME.append(container);
        }
    },
    CONFIGURATION {
        @Override
        public ServiceName getServiceName(String container) {
            return CACHE_CONTAINER.getServiceName(container).append("config");
        }
    },
    AFFINITY {
        @Override
        public ServiceName getServiceName(String container) {
            return CACHE_CONTAINER.getServiceName(container).append("affinity");
        }
    },
    ;

    static final ServiceName BASE_NAME = ServiceName.JBOSS.append("infinispan");
}


File: clustering/infinispan/spi/src/main/java/org/wildfly/clustering/infinispan/spi/service/CacheServiceName.java
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
package org.wildfly.clustering.infinispan.spi.service;

import org.jboss.msc.service.ServiceName;

/**
 * Enumeration of service name factories for services associated with a cache.
 * @author Paul Ferraro
 */
public enum CacheServiceName implements CacheServiceNameFactory {

    CACHE {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return CacheContainerServiceName.CACHE_CONTAINER.getServiceName(container).append(cache);
        }
    },
    CONFIGURATION {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return CACHE.getServiceName(container, cache).append("config");
        }
    },
    XA_RESOURCE_RECOVERY {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return CACHE.getServiceName(container, cache).append("recovery");
        }
    },
    ;

    @Override
    public ServiceName getServiceName(String container) {
        return this.getServiceName(container, DEFAULT_CACHE);
    }
}


File: clustering/jgroups/extension/src/main/java/org/jboss/as/clustering/jgroups/subsystem/ForkAddHandler.java
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

package org.jboss.as.clustering.jgroups.subsystem;

import java.util.Iterator;
import java.util.ServiceLoader;

import org.jboss.as.clustering.dmr.ModelNodes;
import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.controller.AbstractAddStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.registry.Resource;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;
import org.jboss.msc.service.ServiceTarget;
import org.jgroups.Channel;
import org.wildfly.clustering.jgroups.spi.ChannelFactory;
import org.wildfly.clustering.jgroups.spi.service.ChannelBuilder;
import org.wildfly.clustering.jgroups.spi.service.ChannelConnectorBuilder;
import org.wildfly.clustering.jgroups.spi.service.ChannelServiceName;
import org.wildfly.clustering.jgroups.spi.service.ChannelServiceNameFactory;
import org.wildfly.clustering.jgroups.spi.service.ProtocolStackServiceName;
import org.wildfly.clustering.service.AliasServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.ClusteredGroupBuilderProvider;
import org.wildfly.clustering.spi.GroupBuilderProvider;

/**
 * Add operation handler for fork resources.
 * @author Paul Ferraro
 */
public class ForkAddHandler extends AbstractAddStepHandler {

    @Override
    protected void performRuntime(OperationContext context, ModelNode operation, Resource resource) throws OperationFailedException {
        installRuntimeServices(context, operation, resource.getModel());
    }

    static void installRuntimeServices(OperationContext context, ModelNode operation, ModelNode model) throws OperationFailedException {

        PathAddress address = context.getCurrentAddress();
        String name = address.getElement(address.size() - 1).getValue();
        String channel = address.getElement(address.size() - 2).getValue();

        ServiceTarget target = context.getServiceTarget();

        ForkChannelFactoryBuilder builder = new ForkChannelFactoryBuilder(name);

        if (model.hasDefined(ProtocolResourceDefinition.WILDCARD_PATH.getKey())) {
            for (Property property : model.get(ProtocolResourceDefinition.WILDCARD_PATH.getKey()).asPropertyList()) {
                String protocolName = property.getName();
                ModelNode protocol = property.getValue();
                ProtocolConfigurationBuilder protocolBuilder = builder.addProtocol(protocolName)
                        .setModule(ModelNodes.asModuleIdentifier(ProtocolResourceDefinition.MODULE.resolveModelAttribute(context, protocol)))
                        .setSocketBinding(ModelNodes.asString(ProtocolResourceDefinition.SOCKET_BINDING.resolveModelAttribute(context, protocol)));
                StackAddHandler.addProtocolProperties(context, protocol, protocolBuilder).build(target).install();
            }
        }

        builder.build(target).install();

        // Install channel factory alias
        new AliasServiceBuilder<>(ChannelServiceName.FACTORY.getServiceName(name), ProtocolStackServiceName.CHANNEL_FACTORY.getServiceName(channel), ChannelFactory.class).build(target).install();

        // Install channel
        new ChannelBuilder(name).build(target).install();

        // Install channel connector
        new ChannelConnectorBuilder(name).build(target).install();

        // Install channel jndi binding
        new BinderServiceBuilder<>(JGroupsBindingFactory.createChannelBinding(name), ChannelServiceName.CHANNEL.getServiceName(name), Channel.class).build(target).install();

        for (GroupBuilderProvider provider : ServiceLoader.load(ClusteredGroupBuilderProvider.class, ClusteredGroupBuilderProvider.class.getClassLoader())) {
            Iterator<Builder<?>> groupBuilders = provider.getBuilders(channel, null).iterator();
            for (Builder<?> groupBuilder : provider.getBuilders(name, null)) {
                new AliasServiceBuilder<>(groupBuilder.getServiceName(), groupBuilders.next().getServiceName(), Object.class).build(target).install();
            }
        }
    }

    static void removeRuntimeServices(OperationContext context, ModelNode operation, ModelNode model) {

        String name = context.getCurrentAddressValue();

        for (GroupBuilderProvider provider : ServiceLoader.load(ClusteredGroupBuilderProvider.class, ClusteredGroupBuilderProvider.class.getClassLoader())) {
            for (Builder<?> builder : provider.getBuilders(name, null)) {
                context.removeService(builder.getServiceName());
            }
        }

        context.removeService(JGroupsBindingFactory.createChannelBinding(name).getBinderServiceName());

        for (ChannelServiceNameFactory factory : ChannelServiceName.values()) {
            context.removeService(factory.getServiceName(name));
        }
    }
}


File: clustering/jgroups/spi/src/main/java/org/wildfly/clustering/jgroups/spi/service/ChannelServiceNameFactory.java
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
package org.wildfly.clustering.jgroups.spi.service;

import org.jboss.msc.service.ServiceName;

/**
 * Factory for creating service names for channel-based services
 * @author Paul Ferraro
 */
public interface ChannelServiceNameFactory {

    /**
     * The alias for the default channel.
     */
    String DEFAULT_CHANNEL = "default";

    /**
     * Returns an appropriate service name for the default channel
     * @return
     */
    ServiceName getServiceName();

    /**
     * Returns an appropriate service name for the specified channel
     * @param name the channel name
     * @return
     */
    ServiceName getServiceName(String name);
}


File: clustering/marshalling/src/main/java/org/wildfly/clustering/marshalling/HashableMarshalledValue.java
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

package org.wildfly.clustering.marshalling;

import java.io.IOException;
import java.io.ObjectInput;
import java.io.ObjectOutput;

/**
 * Like {@link SimpleMarshalledValue}, but also serializes the underlying object's hash code,
 * so that this object can still be hashed, even if deserialized, but not yet rehydrated.
 * @author Paul Ferraro
 */
public class HashableMarshalledValue<T> extends SimpleMarshalledValue<T> {
    private static final long serialVersionUID = -7576022002375288323L;

    private transient int hashCode;

    /**
     * @param object
     * @param context
     * @throws IOException
     */
    public HashableMarshalledValue(T object, MarshallingContext context) {
        super(object, context);
        this.hashCode = (object != null ) ? object.hashCode() : 0;
    }

    public HashableMarshalledValue() {
        // Required for externalization
    }

    @Override
    public int hashCode() {
        return this.hashCode;
    }

    @Override
    public boolean equals(Object object) {
        if (object instanceof HashableMarshalledValue) {
            HashableMarshalledValue<?> value = (HashableMarshalledValue<?>) object;
            return (this.hashCode == value.hashCode()) && super.equals(object);
        }
        return super.equals(object);
    }

    @Override
    public void writeExternal(ObjectOutput out) throws IOException {
        super.writeExternal(out);
        out.writeInt(this.hashCode);
    }

    @Override
    public void readExternal(ObjectInput in) throws IOException {
        super.readExternal(in);
        this.hashCode = in.readInt();
    }
}


File: clustering/marshalling/src/test/java/org/wildfly/clustering/marshalling/SimpleMarshalledValueFactoryTestCase.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2008, Red Hat Middleware LLC, and individual contributors
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
package org.wildfly.clustering.marshalling;

import static org.junit.Assert.*;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.UUID;

import org.jboss.marshalling.Marshalling;
import org.jboss.marshalling.MarshallingConfiguration;
import org.junit.Test;
import org.wildfly.clustering.marshalling.MarshallingContext;
import org.wildfly.clustering.marshalling.SimpleMarshalledValue;
import org.wildfly.clustering.marshalling.SimpleMarshalledValueFactory;
import org.wildfly.clustering.marshalling.SimpleMarshallingContext;
import org.wildfly.clustering.marshalling.VersionedMarshallingConfiguration;

/**
 * Unit tests for SimpleMarshalledValue.
 * 
 * @author Brian Stansberry
 */
public class SimpleMarshalledValueFactoryTestCase {
    private final MarshallingContext context;
    private final SimpleMarshalledValueFactory factory;
    
    public SimpleMarshalledValueFactoryTestCase() {
        VersionedMarshallingConfiguration configuration = new VersionedMarshallingConfiguration() {
            @Override
            public int getCurrentMarshallingVersion() {
                return 0;
            }

            @Override
            public MarshallingConfiguration getMarshallingConfiguration(int version) {
                assertEquals(0, version);
                return new MarshallingConfiguration();
            }
        };
        this.context = new SimpleMarshallingContext(Marshalling.getMarshallerFactory("river", Marshalling.class.getClassLoader()), configuration, Thread.currentThread().getContextClassLoader());
        this.factory = this.createFactory(this.context);
    }

    SimpleMarshalledValueFactory createFactory(MarshallingContext context) {
        return new SimpleMarshalledValueFactory(context);
    }
    
    /**
     * Test method for {@link org.jboss.ha.framework.server.SimpleMarshalledValue#get()}.
     */
    @Test
    public void get() throws Exception {
        UUID uuid = UUID.randomUUID();
        SimpleMarshalledValue<UUID> mv = this.factory.createMarshalledValue(uuid);

        assertNotNull(mv.peek());
        assertSame(uuid, mv.peek());
        assertSame(uuid, mv.get(this.context));

        SimpleMarshalledValue<UUID> copy = replicate(mv);

        assertNull(copy.peek());
        
        UUID uuid2 = copy.get(this.context);
        assertNotSame(uuid, uuid2);
        assertEquals(uuid, uuid2);

        copy = replicate(copy);
        uuid2 = copy.get(this.context);
        assertEquals(uuid, uuid2);

        mv = this.factory.createMarshalledValue(null);
        assertNull(mv.peek());
        assertNull(mv.getBytes());
        assertNull(mv.get(this.context));
    }

    /**
     * Test method for {@link org.jboss.ha.framework.server.SimpleMarshalledValue#equals(java.lang.Object)}.
     */
    @Test
    public void equals() throws Exception {
        UUID uuid = UUID.randomUUID();
        SimpleMarshalledValue<UUID> mv = this.factory.createMarshalledValue(uuid);

        assertTrue(mv.equals(mv));
        assertFalse(mv.equals(null));

        SimpleMarshalledValue<UUID> dup = this.factory.createMarshalledValue(uuid);
        assertTrue(mv.equals(dup));
        assertTrue(dup.equals(mv));

        SimpleMarshalledValue<UUID> replica = replicate(mv);
        assertTrue(mv.equals(replica));
        assertTrue(replica.equals(mv));

        SimpleMarshalledValue<UUID> nulled = this.factory.createMarshalledValue(null);
        assertFalse(mv.equals(nulled));
        assertFalse(nulled.equals(mv));
        assertFalse(replica.equals(nulled));
        assertFalse(nulled.equals(replica));
        assertTrue(nulled.equals(nulled));
        assertFalse(nulled.equals(null));
        assertTrue(nulled.equals(this.factory.createMarshalledValue(null)));
    }

    /**
     * Test method for {@link org.jboss.ha.framework.server.SimpleMarshalledValue#hashCode()}.
     */
    @Test
    public void testHashCode() throws Exception {
        UUID uuid = UUID.randomUUID();
        SimpleMarshalledValue<UUID> mv = this.factory.createMarshalledValue(uuid);
        assertEquals(uuid.hashCode(), mv.hashCode());

        SimpleMarshalledValue<UUID> copy = replicate(mv);
        this.validateHashCode(uuid, copy);

        mv = this.factory.createMarshalledValue(null);
        assertEquals(0, mv.hashCode());
    }

    <T> void validateHashCode(T original, SimpleMarshalledValue<T> copy) {
        assertEquals(0, copy.hashCode());
    }
    
    @SuppressWarnings("unchecked")
    <V> SimpleMarshalledValue<V> replicate(SimpleMarshalledValue<V> mv) throws IOException, ClassNotFoundException {
        return (SimpleMarshalledValue<V>) unmarshall(marshall(mv));
    }

    private static byte[] marshall(Object mv) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(mv);
        oos.close();
        return baos.toByteArray();
    }

    private static Object unmarshall(byte[] bytes) throws IOException, ClassNotFoundException {
        ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
        ObjectInputStream ois = new ObjectInputStream(bais);
        try {
            return ois.readObject();
        } finally {
            ois.close();
        }
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/CacheServiceNameProvider.java
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

package org.wildfly.clustering.server;

import org.jboss.msc.service.ServiceName;
import org.wildfly.clustering.service.ServiceNameProvider;
import org.wildfly.clustering.spi.CacheGroupServiceNameFactory;

/**
 * Provides a service name for a cache-based service.
 * @author Paul Ferraro
 */
public class CacheServiceNameProvider implements ServiceNameProvider {

    protected final String containerName;
    protected final String cacheName;
    private final CacheGroupServiceNameFactory factory;

    public CacheServiceNameProvider(CacheGroupServiceNameFactory factory, String containerName, String cacheName) {
        this.factory = factory;
        this.containerName = containerName;
        this.cacheName = cacheName;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ServiceName getServiceName() {
        return this.factory.getServiceName(this.containerName, this.cacheName);
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/GroupServiceNameProvider.java
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

package org.wildfly.clustering.server;

import org.jboss.msc.service.ServiceName;
import org.wildfly.clustering.service.ServiceNameProvider;
import org.wildfly.clustering.spi.GroupServiceNameFactory;

/**
 * Provides a service name for a group-based service.
 * @author Paul Ferraro
 */
public class GroupServiceNameProvider implements ServiceNameProvider {

    protected final String group;
    private final GroupServiceNameFactory factory;

    public GroupServiceNameProvider(GroupServiceNameFactory factory, String group) {
        this.factory = factory;
        this.group = group;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ServiceName getServiceName() {
        return this.factory.getServiceName(this.group);
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/dispatcher/ChannelCommandDispatcher.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2013, Red Hat, Inc., and individual contributors
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
package org.wildfly.clustering.server.dispatcher;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.jgroups.Address;
import org.jgroups.Message;
import org.jgroups.blocks.MessageDispatcher;
import org.jgroups.blocks.RequestOptions;
import org.jgroups.blocks.ResponseMode;
import org.jgroups.blocks.RspFilter;
import org.jgroups.util.Rsp;
import org.wildfly.clustering.dispatcher.Command;
import org.wildfly.clustering.dispatcher.CommandDispatcher;
import org.wildfly.clustering.dispatcher.CommandResponse;
import org.wildfly.clustering.group.Node;
import org.wildfly.clustering.group.NodeFactory;
import org.wildfly.clustering.server.Addressable;

/**
 * MessageDispatcher-based command dispatcher.
 * @author Paul Ferraro
 *
 * @param <C> command execution context
 */
public abstract class ChannelCommandDispatcher<C> implements CommandDispatcher<C> {

    private static final RspFilter FILTER = new RspFilter() {
        @Override
        public boolean isAcceptable(Object response, Address sender) {
            return !(response instanceof NoSuchService);
        }

        @Override
        public boolean needMoreResponses() {
            return true;
        }
    };

    private final MessageDispatcher dispatcher;
    private final CommandMarshaller<C> marshaller;
    private final NodeFactory<Address> factory;
    private final long timeout;
    private final CommandDispatcher<C> localDispatcher;

    public ChannelCommandDispatcher(MessageDispatcher dispatcher, CommandMarshaller<C> marshaller, NodeFactory<Address> factory, long timeout, CommandDispatcher<C> localDispatcher) {
        this.dispatcher = dispatcher;
        this.marshaller = marshaller;
        this.factory = factory;
        this.timeout = timeout;
        this.localDispatcher = localDispatcher;
    }

    @Override
    public <R> Map<Node, CommandResponse<R>> executeOnCluster(Command<R, C> command, Node... excludedNodes) throws Exception {
        RequestOptions options = this.createRequestOptions(excludedNodes);
        Map<Address, Rsp<R>> responses = this.dispatcher.castMessage(null, this.createMessage(command), options);

        Map<Node, CommandResponse<R>> results = new HashMap<>();
        for (Map.Entry<Address, Rsp<R>> entry: responses.entrySet()) {
            Address address = entry.getKey();
            Rsp<R> response = entry.getValue();
            if (response.wasReceived() && !response.wasSuspected()) {
                results.put(this.factory.createNode(address), createCommandResponse(response));
            }
        }

        return results;
    }

    @Override
    public <R> Map<Node, Future<R>> submitOnCluster(Command<R, C> command, Node... excludedNodes) throws Exception {
        final Future<? extends Map<Address, Rsp<R>>> responses = this.dispatcher.castMessageWithFuture(null, this.createMessage(command), this.createRequestOptions(excludedNodes));

        Map<Node, Future<R>> results = new HashMap<>();
        Set<Node> excluded = (excludedNodes != null) ? new HashSet<>(Arrays.asList(excludedNodes)) : Collections.<Node>emptySet();
        for (Address address: this.dispatcher.getChannel().getView().getMembers()) {
            final Node node = this.factory.createNode(address);
            if (!excluded.contains(node)) {
                Future<R> future = new Future<R>() {
                    @Override
                    public boolean cancel(boolean mayInterruptIfRunning) {
                        return responses.cancel(mayInterruptIfRunning);
                    }

                    @Override
                    public R get() throws InterruptedException, ExecutionException {
                        return createCommandResponse(responses.get().get(node)).get();
                    }

                    @Override
                    public R get(long timeout, TimeUnit unit) throws InterruptedException, ExecutionException, TimeoutException {
                        return createCommandResponse(responses.get(timeout, unit).get(node)).get();
                    }

                    @Override
                    public boolean isCancelled() {
                        return responses.isCancelled();
                    }

                    @Override
                    public boolean isDone() {
                        return responses.isDone();
                    }
                };
                results.put(node, future);
            }
        }
        return results;
    }

    @Override
    public <R> CommandResponse<R> executeOnNode(Command<R, C> command, Node node) throws Exception {
        // Bypass MessageDispatcher if target node is local
        if (this.isLocal(node)) {
            return this.localDispatcher.executeOnNode(command, node);
        }
        // Use sendMessageWithFuture(...) instead of sendMessage(...) since we want to differentiate between sender exceptions and receiver exceptions
        Future<R> future = this.dispatcher.sendMessageWithFuture(this.createMessage(command, node), this.createRequestOptions());
        try {
            return new SimpleCommandResponse<>(future.get());
        } catch (InterruptedException e) {
            return new SimpleCommandResponse<>(e);
        } catch (ExecutionException e) {
            return new SimpleCommandResponse<>(e);
        }
    }

    @Override
    public <R> Future<R> submitOnNode(Command<R, C> command, Node node) throws Exception {
        // Bypass MessageDispatcher if target node is local
        if (this.isLocal(node)) {
            return this.localDispatcher.submitOnNode(command, node);
        }
        return this.dispatcher.sendMessageWithFuture(this.createMessage(command, node), this.createRequestOptions());
    }

    private <R> Message createMessage(Command<R, C> command) {
        return this.createMessage(command, null);
    }

    private <R> Message createMessage(Command<R, C> command, Node node) {
        try {
            return new Message(getAddress(node), this.getLocalAddress(), this.marshaller.marshal(command));
        } catch (IOException e) {
            throw new IllegalArgumentException(e);
        }
    }

    private boolean isLocal(Node node) {
        return this.getLocalAddress().equals(getAddress(node));
    }

    private static Address getAddress(Node node) {
        return (node instanceof Addressable) ? ((Addressable) node).getAddress() : null;
    }

    private RequestOptions createRequestOptions(Node... excludedNodes) {
        RequestOptions options = this.createRequestOptions();
        if ((excludedNodes != null) && (excludedNodes.length > 0)) {
            Address[] addresses = new Address[excludedNodes.length];
            for (int i = 0; i < excludedNodes.length; ++i) {
                addresses[i] = getAddress(excludedNodes[i]);
            }
            options.setExclusionList(addresses);
        }
        return options;
    }

    private RequestOptions createRequestOptions() {
        return new RequestOptions(ResponseMode.GET_ALL, this.timeout, false, FILTER, Message.Flag.DONT_BUNDLE, Message.Flag.OOB);
    }

    static <R> CommandResponse<R> createCommandResponse(Rsp<R> response) {
        Throwable exception = response.getException();
        return (exception != null) ? new SimpleCommandResponse<R>(exception) : new SimpleCommandResponse<>(response.getValue());
    }

    private Address getLocalAddress() {
        return this.dispatcher.getChannel().getAddress();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/dispatcher/CommandDispatcherFactoryAliasBuilderProvider.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.wildfly.clustering.server.dispatcher;

import java.util.Arrays;
import java.util.Collection;

import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.naming.ManagedReferenceFactory;
import org.jboss.as.naming.deployment.ContextNames;
import org.wildfly.clustering.dispatcher.CommandDispatcherFactory;
import org.wildfly.clustering.service.AliasServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.GroupAliasBuilderProvider;
import org.wildfly.clustering.spi.GroupServiceName;
import org.wildfly.clustering.spi.GroupServiceNameFactory;

/**
 * @author Paul Ferraro
 */
public class CommandDispatcherFactoryAliasBuilderProvider implements GroupAliasBuilderProvider {

    @Override
    public Collection<Builder<?>> getBuilders(String aliasGroup, String targetGroup) {
        Builder<CommandDispatcherFactory> builder = new AliasServiceBuilder<>(GroupServiceName.COMMAND_DISPATCHER.getServiceName(aliasGroup), GroupServiceName.COMMAND_DISPATCHER.getServiceName(targetGroup), CommandDispatcherFactory.class);
        ContextNames.BindInfo binding = ContextNames.bindInfoFor(JndiNameFactory.createJndiName(JndiNameFactory.DEFAULT_JNDI_NAMESPACE, GroupServiceNameFactory.BASE_NAME, GroupServiceName.COMMAND_DISPATCHER.toString(), aliasGroup).getAbsoluteName());
        Builder<ManagedReferenceFactory> bindingBuilder = new BinderServiceBuilder<>(binding, builder.getServiceName(), CommandDispatcherFactory.class);
        return Arrays.asList(builder, bindingBuilder);
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/dispatcher/CommandDispatcherFactoryBuilderProvider.java
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
package org.wildfly.clustering.server.dispatcher;

import java.util.Arrays;
import java.util.Collection;

import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.naming.ManagedReferenceFactory;
import org.jboss.as.naming.deployment.ContextNames;
import org.jboss.modules.ModuleIdentifier;
import org.wildfly.clustering.dispatcher.CommandDispatcherFactory;
import org.wildfly.clustering.server.GroupBuilderFactory;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.GroupBuilderProvider;
import org.wildfly.clustering.spi.GroupServiceNameFactory;
import org.wildfly.clustering.spi.GroupServiceName;

/**
 * Provides the requisite builders for creating a {@link org.wildfly.clustering.dispatcher.CommandDispatcherFactory} created from a specified factory..
 * @author Paul Ferraro
 */
public class CommandDispatcherFactoryBuilderProvider implements GroupBuilderProvider {

    private final GroupBuilderFactory<CommandDispatcherFactory> factory;

    public CommandDispatcherFactoryBuilderProvider(GroupBuilderFactory<CommandDispatcherFactory> factory) {
        this.factory = factory;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Collection<Builder<?>> getBuilders(String group, ModuleIdentifier module) {
        Builder<CommandDispatcherFactory> builder = this.factory.createBuilder(group, module);
        ContextNames.BindInfo binding = ContextNames.bindInfoFor(JndiNameFactory.createJndiName(JndiNameFactory.DEFAULT_JNDI_NAMESPACE, GroupServiceNameFactory.BASE_NAME, GroupServiceName.COMMAND_DISPATCHER.toString(), group).getAbsoluteName());
        Builder<ManagedReferenceFactory> bindingBuilder = new BinderServiceBuilder<>(binding, builder.getServiceName(), CommandDispatcherFactory.class);
        return Arrays.asList(builder, bindingBuilder);
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/group/GroupAliasBuilderProvider.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.wildfly.clustering.server.group;

import java.util.Arrays;
import java.util.Collection;

import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.naming.ManagedReferenceFactory;
import org.jboss.as.naming.deployment.ContextNames;
import org.wildfly.clustering.group.Group;
import org.wildfly.clustering.service.AliasServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.GroupServiceName;
import org.wildfly.clustering.spi.GroupServiceNameFactory;

/**
 * @author Paul Ferraro
 */
public class GroupAliasBuilderProvider implements org.wildfly.clustering.spi.GroupAliasBuilderProvider {

    @Override
    public Collection<Builder<?>> getBuilders(String aliasGroup, String targetGroup) {
        Builder<Group> builder = new AliasServiceBuilder<>(GroupServiceName.GROUP.getServiceName(aliasGroup), GroupServiceName.GROUP.getServiceName(targetGroup), Group.class);
        ContextNames.BindInfo binding = ContextNames.bindInfoFor(JndiNameFactory.createJndiName(JndiNameFactory.DEFAULT_JNDI_NAMESPACE, GroupServiceNameFactory.BASE_NAME, GroupServiceName.GROUP.toString(), aliasGroup).getAbsoluteName());
        Builder<ManagedReferenceFactory> bindingBuilder = new BinderServiceBuilder<>(binding, builder.getServiceName(), Group.class);
        return Arrays.asList(builder, bindingBuilder);
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/group/GroupBuilderProvider.java
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

package org.wildfly.clustering.server.group;

import java.util.Arrays;
import java.util.Collection;

import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.naming.ManagedReferenceFactory;
import org.jboss.as.naming.deployment.ContextNames;
import org.jboss.modules.ModuleIdentifier;
import org.wildfly.clustering.group.Group;
import org.wildfly.clustering.server.GroupBuilderFactory;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.GroupServiceName;
import org.wildfly.clustering.spi.GroupServiceNameFactory;

/**
 * Provides the requisite builders for a {@link Group} service created from a specified factory.
 * @author Paul Ferraro
 */
public class GroupBuilderProvider implements org.wildfly.clustering.spi.GroupBuilderProvider {

    private final GroupBuilderFactory<Group> factory;

    public GroupBuilderProvider(GroupBuilderFactory<Group> factory) {
        this.factory = factory;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Collection<Builder<?>> getBuilders(String group, ModuleIdentifier module) {
        Builder<Group> builder = this.factory.createBuilder(group, module);
        ContextNames.BindInfo binding = ContextNames.bindInfoFor(JndiNameFactory.createJndiName(JndiNameFactory.DEFAULT_JNDI_NAMESPACE, GroupServiceNameFactory.BASE_NAME, GroupServiceName.GROUP.toString(), group).getAbsoluteName());
        Builder<ManagedReferenceFactory> bindingBuilder = new BinderServiceBuilder<>(binding, builder.getServiceName(), Group.class);
        return Arrays.asList(builder, bindingBuilder);
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/provider/ServiceProviderRegistrationFactoryAliasBuilderProvider.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.wildfly.clustering.server.provider;

import java.util.Arrays;
import java.util.Collection;

import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.naming.ManagedReferenceFactory;
import org.jboss.as.naming.deployment.ContextNames;
import org.wildfly.clustering.provider.ServiceProviderRegistrationFactory;
import org.wildfly.clustering.service.AliasServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.CacheGroupServiceName;
import org.wildfly.clustering.spi.CacheGroupAliasBuilderProvider;
import org.wildfly.clustering.spi.GroupServiceNameFactory;

/**
 * @author Paul Ferraro
 */
public class ServiceProviderRegistrationFactoryAliasBuilderProvider implements CacheGroupAliasBuilderProvider {

    @Override
    public Collection<Builder<?>> getBuilders(String containerName, String aliasCacheName, String targetCacheName) {
        Builder<ServiceProviderRegistrationFactory> builder = new AliasServiceBuilder<>(CacheGroupServiceName.SERVICE_PROVIDER_REGISTRATION.getServiceName(containerName, aliasCacheName), CacheGroupServiceName.SERVICE_PROVIDER_REGISTRATION.getServiceName(containerName, targetCacheName), ServiceProviderRegistrationFactory.class);
        ContextNames.BindInfo binding = ContextNames.bindInfoFor(JndiNameFactory.createJndiName(JndiNameFactory.DEFAULT_JNDI_NAMESPACE, GroupServiceNameFactory.BASE_NAME, CacheGroupServiceName.SERVICE_PROVIDER_REGISTRATION.toString(), containerName, aliasCacheName).getAbsoluteName());
        Builder<ManagedReferenceFactory> bindingBuilder = new BinderServiceBuilder<>(binding, builder.getServiceName(), ServiceProviderRegistrationFactory.class);
        return Arrays.asList(builder, bindingBuilder);
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/provider/ServiceProviderRegistrationFactoryBuilderProvider.java
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
package org.wildfly.clustering.server.provider;

import java.util.Arrays;
import java.util.Collection;

import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.naming.ManagedReferenceFactory;
import org.jboss.as.naming.deployment.ContextNames;
import org.wildfly.clustering.provider.ServiceProviderRegistrationFactory;
import org.wildfly.clustering.server.CacheBuilderFactory;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.CacheGroupBuilderProvider;
import org.wildfly.clustering.spi.CacheGroupServiceName;
import org.wildfly.clustering.spi.GroupServiceNameFactory;

/**
 * Provides the requisite builders for a {@link ServiceProviderRegistrationFactory} created from the specified factory.
 * @author Paul Ferraro
 */
public class ServiceProviderRegistrationFactoryBuilderProvider implements CacheGroupBuilderProvider {

    private final CacheBuilderFactory<ServiceProviderRegistrationFactory> factory;

    public ServiceProviderRegistrationFactoryBuilderProvider(CacheBuilderFactory<ServiceProviderRegistrationFactory> factory) {
        this.factory = factory;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Collection<Builder<?>> getBuilders(String containerName, String cacheName) {
        Builder<ServiceProviderRegistrationFactory> builder = this.factory.createBuilder(containerName, cacheName);
        ContextNames.BindInfo binding = ContextNames.bindInfoFor(JndiNameFactory.createJndiName(JndiNameFactory.DEFAULT_JNDI_NAMESPACE, GroupServiceNameFactory.BASE_NAME, CacheGroupServiceName.SERVICE_PROVIDER_REGISTRATION.toString(), containerName, cacheName).getAbsoluteName());
        Builder<ManagedReferenceFactory> bindingBuilder = new BinderServiceBuilder<>(binding, builder.getServiceName(), ServiceProviderRegistrationFactory.class);
        return Arrays.asList(builder, bindingBuilder);
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/registry/RegistryFactoryAliasBuilderProvider.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.wildfly.clustering.server.registry;

import java.util.Arrays;
import java.util.Collection;

import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.naming.ManagedReferenceFactory;
import org.jboss.as.naming.deployment.ContextNames;
import org.wildfly.clustering.registry.Registry;
import org.wildfly.clustering.registry.RegistryEntryProvider;
import org.wildfly.clustering.registry.RegistryFactory;
import org.wildfly.clustering.service.AliasServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.CacheGroupServiceName;
import org.wildfly.clustering.spi.CacheGroupAliasBuilderProvider;
import org.wildfly.clustering.spi.GroupServiceNameFactory;

/**
 * @author Paul Ferraro
 */
public class RegistryFactoryAliasBuilderProvider implements CacheGroupAliasBuilderProvider {

    @SuppressWarnings("rawtypes")
    @Override
    public Collection<Builder<?>> getBuilders(String containerName, String aliasCacheName, String targetCacheName) {
        Builder<RegistryFactory> factoryBuilder = new AliasServiceBuilder<>(CacheGroupServiceName.REGISTRY_FACTORY.getServiceName(containerName, aliasCacheName), CacheGroupServiceName.REGISTRY_FACTORY.getServiceName(containerName, targetCacheName), RegistryFactory.class);
        Builder<Registry> registryBuilder = new AliasServiceBuilder<>(CacheGroupServiceName.REGISTRY.getServiceName(containerName, aliasCacheName), CacheGroupServiceName.REGISTRY.getServiceName(containerName, targetCacheName), Registry.class);
        Builder<RegistryEntryProvider> entryBuilder = new AliasServiceBuilder<>(CacheGroupServiceName.REGISTRY_ENTRY.getServiceName(containerName, targetCacheName), CacheGroupServiceName.REGISTRY_ENTRY.getServiceName(containerName, aliasCacheName), RegistryEntryProvider.class);
        ContextNames.BindInfo binding = ContextNames.bindInfoFor(JndiNameFactory.createJndiName(JndiNameFactory.DEFAULT_JNDI_NAMESPACE, GroupServiceNameFactory.BASE_NAME, CacheGroupServiceName.REGISTRY.toString(), containerName, aliasCacheName).getAbsoluteName());
        Builder<ManagedReferenceFactory> bindingBuilder = new BinderServiceBuilder<>(binding, factoryBuilder.getServiceName(), RegistryFactory.class);
        return Arrays.asList(factoryBuilder, registryBuilder, entryBuilder, bindingBuilder);
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/registry/RegistryFactoryBuilderProvider.java
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
package org.wildfly.clustering.server.registry;

import java.util.Arrays;
import java.util.Collection;

import org.jboss.as.clustering.naming.BinderServiceBuilder;
import org.jboss.as.clustering.naming.JndiNameFactory;
import org.jboss.as.naming.ManagedReferenceFactory;
import org.jboss.as.naming.deployment.ContextNames;
import org.wildfly.clustering.registry.Registry;
import org.wildfly.clustering.registry.RegistryFactory;
import org.wildfly.clustering.server.CacheBuilderFactory;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.CacheGroupBuilderProvider;
import org.wildfly.clustering.spi.CacheGroupServiceName;
import org.wildfly.clustering.spi.GroupServiceNameFactory;

/**
 * Provides the requisite builders for a clustered {@link RegistryFactory} created from the specified factory.
 * @author Paul Ferraro
 */
public class RegistryFactoryBuilderProvider implements CacheGroupBuilderProvider {

    private final CacheBuilderFactory<RegistryFactory<Object, Object>> factory;

    /**
     * Constructs a new provider for {@link RegistryFactory} service builders.
     */
    public RegistryFactoryBuilderProvider(CacheBuilderFactory<RegistryFactory<Object, Object>> factory) {
        this.factory = factory;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Collection<Builder<?>> getBuilders(String containerName, String cacheName) {
        Builder<RegistryFactory<Object, Object>> builder = this.factory.createBuilder(containerName, cacheName);
        ContextNames.BindInfo binding = ContextNames.bindInfoFor(JndiNameFactory.createJndiName(JndiNameFactory.DEFAULT_JNDI_NAMESPACE, GroupServiceNameFactory.BASE_NAME, CacheGroupServiceName.REGISTRY.toString(), containerName, cacheName).getAbsoluteName());
        Builder<ManagedReferenceFactory> bindingBuilder = new BinderServiceBuilder<>(binding, builder.getServiceName(), RegistryFactory.class);
        Builder<Registry<Object, Object>> registryBuilder = new RegistryBuilder<>(containerName, cacheName);
        return Arrays.asList(builder, bindingBuilder, registryBuilder);
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/singleton/CacheSingletonServiceBuilderFactory.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2013, Red Hat, Inc., and individual contributors
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
package org.wildfly.clustering.server.singleton;

import java.io.Serializable;

import org.jboss.msc.service.Service;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.wildfly.clustering.singleton.SingletonElectionPolicy;
import org.wildfly.clustering.singleton.SingletonServiceBuilder;
import org.wildfly.clustering.singleton.SingletonServiceBuilderFactory;

/**
 * Service for building {@link SingletonService} instances.
 * @author Paul Ferraro
 */
public class CacheSingletonServiceBuilderFactory implements SingletonServiceBuilderFactory {

    final String containerName;
    final String cacheName;

    public CacheSingletonServiceBuilderFactory(String containerName, String cacheName) {
        this.containerName = containerName;
        this.cacheName = cacheName;
    }

    @Override
    public <T extends Serializable> SingletonServiceBuilder<T> createSingletonServiceBuilder(final ServiceName name, Service<T> service) {
        final SingletonService<T> singleton = new SingletonService<>(name, service);
        return new SingletonServiceBuilder<T>() {
            @Override
            public SingletonServiceBuilder<T> requireQuorum(int quorum) {
                singleton.setQuorum(quorum);
                return this;
            }

            @Override
            public SingletonServiceBuilder<T> electionPolicy(SingletonElectionPolicy policy) {
                singleton.setElectionPolicy(policy);
                return this;
            }

            @Override
            public ServiceBuilder<T> build(ServiceTarget target) {
                return singleton.build(target, CacheSingletonServiceBuilderFactory.this.containerName, CacheSingletonServiceBuilderFactory.this.cacheName);
            }

            @Override
            public ServiceName getServiceName() {
                return name;
            }
        };
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/singleton/LocalSingletonServiceBuilderFactory.java
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
package org.wildfly.clustering.server.singleton;

import java.io.Serializable;

import org.jboss.msc.service.Service;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.wildfly.clustering.singleton.SingletonElectionPolicy;
import org.wildfly.clustering.singleton.SingletonServiceBuilder;
import org.wildfly.clustering.singleton.SingletonServiceBuilderFactory;

/**
 * Service that provides a non-clustered {@link SingletonServiceBuilderFactory}
 * @author Paul Ferraro
 */
public class LocalSingletonServiceBuilderFactory implements SingletonServiceBuilderFactory {

    @Override
    public <T extends Serializable> SingletonServiceBuilder<T> createSingletonServiceBuilder(final ServiceName name, final Service<T> service) {
        return new SingletonServiceBuilder<T>() {
            @Override
            public SingletonServiceBuilder<T> requireQuorum(int quorum) {
                // Quorum requirements are inconsequential to a local singleton
                return this;
            }

            @Override
            public SingletonServiceBuilder<T> electionPolicy(SingletonElectionPolicy policy) {
                // Election policies are inconsequential to a local singleton
                return this;
            }

            @Override
            public ServiceBuilder<T> build(ServiceTarget target) {
                return target.addService(name, service);
            }

            @Override
            public ServiceName getServiceName() {
                return name;
            }
        };
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/singleton/SingletonClassTableContributor.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2013, Red Hat, Inc., and individual contributors
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
package org.wildfly.clustering.server.singleton;

import java.util.Arrays;
import java.util.Collection;

import org.wildfly.clustering.marshalling.ClassTableContributor;

/**
 * ClassTable contributor for a {@link SingletonService}.
 * @author Paul Ferraro
 */
public class SingletonClassTableContributor implements ClassTableContributor {

    @Override
    public Collection<Class<?>> getKnownClasses() {
        return Arrays.<Class<?>>asList(SingletonValueCommand.class, StopSingletonCommand.class);
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/singleton/SingletonServiceBuilderFactoryAliasBuilderProvider.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat, Inc., and individual contributors
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

package org.wildfly.clustering.server.singleton;

import java.util.Collection;
import java.util.Collections;

import org.wildfly.clustering.service.AliasServiceBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.singleton.SingletonServiceBuilderFactory;
import org.wildfly.clustering.spi.CacheGroupServiceName;
import org.wildfly.clustering.spi.CacheGroupAliasBuilderProvider;

/**
 * @author Paul Ferraro
 */
public class SingletonServiceBuilderFactoryAliasBuilderProvider implements CacheGroupAliasBuilderProvider {

    @Override
    public Collection<Builder<?>> getBuilders(String containerName, String aliasCacheName, String targetCacheName) {
        return Collections.<Builder<?>>singleton(new AliasServiceBuilder<>(CacheGroupServiceName.SINGLETON_SERVICE_BUILDER.getServiceName(containerName, aliasCacheName), CacheGroupServiceName.SINGLETON_SERVICE_BUILDER.getServiceName(containerName, targetCacheName), SingletonServiceBuilderFactory.class));
    }

    @Override
    public String toString() {
        return this.getClass().getName();
    }
}


File: clustering/server/src/main/java/org/wildfly/clustering/server/singleton/SingletonServiceBuilderFactoryServiceNameProvider.java
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
package org.wildfly.clustering.server.singleton;

import org.wildfly.clustering.server.CacheServiceNameProvider;
import org.wildfly.clustering.spi.CacheGroupServiceName;

/**
 * Provides the service name of a {@link org.wildfly.clustering.singleton.SingletonServiceBuilderFactory}.
 * @author Paul Ferraro
 */
public class SingletonServiceBuilderFactoryServiceNameProvider extends CacheServiceNameProvider {

    /**
     * @param containerName
     * @param cacheName
     */
    public SingletonServiceBuilderFactoryServiceNameProvider(String containerName, String cacheName) {
        super(CacheGroupServiceName.SINGLETON_SERVICE_BUILDER, containerName, cacheName);
    }
}

File: clustering/spi/src/main/java/org/wildfly/clustering/spi/CacheGroupServiceName.java
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
package org.wildfly.clustering.spi;

import org.jboss.msc.service.ServiceName;

/**
 * Set of {@link ServiceName} factories for cache-based services.
 * @author Paul Ferraro
 */
public enum CacheGroupServiceName implements CacheGroupServiceNameFactory {
    NODE_FACTORY() {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return GroupServiceName.NODE_FACTORY.getServiceName(container).append(cache);
        }
    },
    GROUP() {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return GroupServiceName.GROUP.getServiceName(container).append(cache);
        }
    },
    REGISTRY() {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return GroupServiceNameFactory.BASE_SERVICE_NAME.append(this.toString(), container, cache);
        }

        @Override
        public String toString() {
            return "registry";
        }
    },
    REGISTRY_ENTRY() {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return REGISTRY.getServiceName(container, cache).append("entry");
        }
    },
    REGISTRY_FACTORY() {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return REGISTRY.getServiceName(container, cache).append("factory");
        }
    },
    SERVICE_PROVIDER_REGISTRATION() {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return GroupServiceNameFactory.BASE_SERVICE_NAME.append(this.toString(), container, cache);
        }

        @Override
        public String toString() {
            return "providers";
        }
    },
    SINGLETON_SERVICE_BUILDER() {
        @Override
        public ServiceName getServiceName(String container, String cache) {
            return GroupServiceNameFactory.BASE_SERVICE_NAME.append("singleton", "builder", container, cache);
        }
    };

    @Override
    public ServiceName getServiceName(String group) {
        return this.getServiceName(group, DEFAULT_CACHE);
    }
}


File: clustering/spi/src/main/java/org/wildfly/clustering/spi/GroupServiceName.java
package org.wildfly.clustering.spi;

import org.jboss.msc.service.ServiceName;

/**
 * Set of {@link ServiceName} factories for group-based services.
 * @author Paul Ferraro
 */
public enum GroupServiceName implements GroupServiceNameFactory {
    COMMAND_DISPATCHER() {
        @Override
        public ServiceName getServiceName(String group) {
            return BASE_SERVICE_NAME.append(this.toString(), group);
        }

        @Override
        public String toString() {
            return "dispatcher";
        }
    },
    NODE_FACTORY() {
        @Override
        public ServiceName getServiceName(String group) {
            return BASE_SERVICE_NAME.append(this.toString(), group);
        }

        @Override
        public String toString() {
            return "nodes";
        }
    },
    GROUP() {
        @Override
        public ServiceName getServiceName(String group) {
            return BASE_SERVICE_NAME.append(this.toString(), group);
        }

        @Override
        public String toString() {
            return "group";
        }
    },
}


File: clustering/web/infinispan/src/main/java/org/wildfly/clustering/web/infinispan/session/InfinispanSessionManagerFactoryBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2013, Red Hat, Inc., and individual contributors
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
package org.wildfly.clustering.web.infinispan.session;

import org.infinispan.Cache;
import org.infinispan.remoting.transport.Address;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.service.ValueService;
import org.jboss.msc.value.InjectedValue;
import org.jboss.msc.value.Value;
import org.wildfly.clustering.dispatcher.CommandDispatcherFactory;
import org.wildfly.clustering.ee.infinispan.TransactionBatch;
import org.wildfly.clustering.group.NodeFactory;
import org.wildfly.clustering.infinispan.spi.affinity.KeyAffinityServiceFactory;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheBuilder;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceNameFactory;
import org.wildfly.clustering.infinispan.spi.service.TemplateConfigurationBuilder;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.CacheGroupServiceName;
import org.wildfly.clustering.spi.GroupServiceName;
import org.wildfly.clustering.web.session.SessionManagerConfiguration;
import org.wildfly.clustering.web.session.SessionManagerFactory;

public class InfinispanSessionManagerFactoryBuilder implements Builder<SessionManagerFactory<TransactionBatch>>, Value<SessionManagerFactory<TransactionBatch>>, InfinispanSessionManagerFactoryConfiguration {
    public static final String DEFAULT_CACHE_CONTAINER = "web";

    private static ServiceName getCacheServiceName(String cacheName) {
        ServiceName baseServiceName = CacheContainerServiceName.CACHE_CONTAINER.getServiceName(DEFAULT_CACHE_CONTAINER).getParent();
        ServiceName serviceName = ServiceName.parse((cacheName != null) ? cacheName : DEFAULT_CACHE_CONTAINER);
        if (!baseServiceName.isParentOf(serviceName)) {
            serviceName = baseServiceName.append(serviceName);
        }
        return (serviceName.length() < 4) ? serviceName.append(CacheServiceNameFactory.DEFAULT_CACHE) : serviceName;
    }

    private final SessionManagerConfiguration configuration;

    @SuppressWarnings("rawtypes")
    private final InjectedValue<Cache> cache = new InjectedValue<>();
    private final InjectedValue<KeyAffinityServiceFactory> affinityFactory = new InjectedValue<>();
    private final InjectedValue<CommandDispatcherFactory> dispatcherFactory = new InjectedValue<>();
    @SuppressWarnings("rawtypes")
    private final InjectedValue<NodeFactory> nodeFactory = new InjectedValue<>();

    public InfinispanSessionManagerFactoryBuilder(SessionManagerConfiguration configuration) {
        this.configuration = configuration;
    }

    @Override
    public ServiceName getServiceName() {
        return ServiceName.JBOSS.append("clustering", "web", this.configuration.getDeploymentName());
    }

    @Override
    public ServiceBuilder<SessionManagerFactory<TransactionBatch>> build(ServiceTarget target) {
        ServiceName templateCacheServiceName = getCacheServiceName(this.configuration.getCacheName());
        String templateCacheName = templateCacheServiceName.getSimpleName();
        String containerName = templateCacheServiceName.getParent().getSimpleName();
        String cacheName = this.configuration.getDeploymentName();

        new TemplateConfigurationBuilder(containerName, cacheName, templateCacheName).build(target).install();

        new CacheBuilder<>(containerName, cacheName).build(target)
                .addAliases(InfinispanRouteLocatorBuilder.getCacheServiceAlias(cacheName))
                .install();

        return target.addService(this.getServiceName(), new ValueService<>(this))
                .addDependency(CacheServiceName.CACHE.getServiceName(containerName, cacheName), Cache.class, this.cache)
                .addDependency(CacheContainerServiceName.AFFINITY.getServiceName(containerName), KeyAffinityServiceFactory.class, this.affinityFactory)
                .addDependency(GroupServiceName.COMMAND_DISPATCHER.getServiceName(containerName), CommandDispatcherFactory.class, this.dispatcherFactory)
                .addDependency(CacheGroupServiceName.NODE_FACTORY.getServiceName(containerName), NodeFactory.class, this.nodeFactory)
                .setInitialMode(ServiceController.Mode.ON_DEMAND)
        ;
    }

    @Override
    public SessionManagerFactory<TransactionBatch> getValue() {
        return new InfinispanSessionManagerFactory(this);
    }

    @Override
    public SessionManagerConfiguration getSessionManagerConfiguration() {
        return this.configuration;
    }

    @Override
    public <K, V> Cache<K, V> getCache() {
        return this.cache.getValue();
    }

    @Override
    public KeyAffinityServiceFactory getKeyAffinityServiceFactory() {
        return this.affinityFactory.getValue();
    }

    @Override
    public CommandDispatcherFactory getCommandDispatcherFactory() {
        return this.dispatcherFactory.getValue();
    }

    @Override
    public NodeFactory<Address> getNodeFactory() {
        return this.nodeFactory.getValue();
    }
}


File: clustering/web/infinispan/src/main/java/org/wildfly/clustering/web/infinispan/sso/InfinispanSSOManagerFactoryBuilder.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2013, Red Hat, Inc., and individual contributors
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
package org.wildfly.clustering.web.infinispan.sso;

import org.infinispan.Cache;
import org.wildfly.clustering.infinispan.spi.affinity.KeyAffinityServiceFactory;
import org.wildfly.clustering.infinispan.spi.service.CacheContainerServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheBuilder;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceName;
import org.wildfly.clustering.infinispan.spi.service.CacheServiceNameFactory;
import org.wildfly.clustering.infinispan.spi.service.TemplateConfigurationBuilder;
import org.jboss.modules.ModuleLoader;
import org.jboss.msc.service.ServiceBuilder;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.msc.service.ValueService;
import org.jboss.msc.value.InjectedValue;
import org.jboss.msc.value.Value;
import org.wildfly.clustering.ee.infinispan.TransactionBatch;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.web.sso.SSOManagerFactory;

public class InfinispanSSOManagerFactoryBuilder<A, D> implements Builder<SSOManagerFactory<A, D, TransactionBatch>>, Value<SSOManagerFactory<A, D, TransactionBatch>>, InfinispanSSOManagerFactoryConfiguration {

    public static final String DEFAULT_CACHE_CONTAINER = "web";

    private final String host;
    @SuppressWarnings("rawtypes")
    private final InjectedValue<Cache> cache = new InjectedValue<>();
    private final InjectedValue<KeyAffinityServiceFactory> affinityFactory = new InjectedValue<>();
    private final InjectedValue<ModuleLoader> loader = new InjectedValue<>();

    public InfinispanSSOManagerFactoryBuilder(String host) {
        this.host = host;
    }

    @Override
    public ServiceName getServiceName() {
        return ServiceName.JBOSS.append("clustering", "sso", this.host);
    }

    @Override
    public ServiceBuilder<SSOManagerFactory<A, D, TransactionBatch>> build(ServiceTarget target) {
        String containerName = DEFAULT_CACHE_CONTAINER;
        String templateCacheName = CacheServiceNameFactory.DEFAULT_CACHE;
        String cacheName = this.host;

        new TemplateConfigurationBuilder(containerName, cacheName, templateCacheName).build(target).install();

        new CacheBuilder<>(containerName, cacheName).build(target).install();

        return target.addService(this.getServiceName(), new ValueService<>(this))
                .addDependency(CacheServiceName.CACHE.getServiceName(containerName, cacheName), Cache.class, this.cache)
                .addDependency(CacheContainerServiceName.AFFINITY.getServiceName(containerName), KeyAffinityServiceFactory.class, this.affinityFactory)
                .addDependency(ServiceName.JBOSS.append("as", "service-module-loader"), ModuleLoader.class, this.loader)
        ;
    }

    @Override
    public SSOManagerFactory<A, D, TransactionBatch> getValue() {
        return new InfinispanSSOManagerFactory<>(this);
    }

    @Override
    public <K, V> Cache<K, V> getCache() {
        return this.cache.getValue();
    }

    @Override
    public KeyAffinityServiceFactory getKeyAffinityServiceFactory() {
        return this.affinityFactory.getValue();
    }

    @Override
    public ModuleLoader getModuleLoader() {
        return this.loader.getValue();
    }
}


File: ejb3/src/main/java/org/jboss/as/ejb3/subsystem/EJB3RemoteServiceAdd.java
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
package org.jboss.as.ejb3.subsystem;

import java.util.ServiceLoader;
import java.util.concurrent.ExecutorService;

import javax.transaction.TransactionManager;
import javax.transaction.TransactionSynchronizationRegistry;
import javax.transaction.UserTransaction;

import org.jboss.as.controller.AbstractAddStepHandler;
import org.jboss.as.controller.OperationContext;
import org.jboss.as.controller.OperationFailedException;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.PathElement;
import org.jboss.as.controller.descriptions.ModelDescriptionConstants;
import org.jboss.as.controller.registry.Resource;
import org.jboss.as.ejb3.logging.EjbLogger;
import org.jboss.as.ejb3.deployment.DeploymentRepository;
import org.jboss.as.ejb3.remote.EJBRemoteConnectorService;
import org.jboss.as.ejb3.remote.EJBRemoteTransactionsRepository;
import org.jboss.as.ejb3.remote.EJBRemotingConnectorClientMappingsEntryProviderService;
import org.jboss.as.ejb3.remote.RegistryCollector;
import org.jboss.as.ejb3.remote.RegistryCollectorService;
import org.jboss.as.ejb3.remote.RegistryInstallerService;
import org.jboss.as.ejb3.remote.RemoteAsyncInvocationCancelStatusService;
import org.jboss.as.remoting.RemotingConnectorBindingInfoService;
import org.jboss.as.remoting.RemotingServices;
import org.jboss.as.server.suspend.SuspendController;
import org.jboss.as.txn.service.TransactionManagerService;
import org.jboss.as.txn.service.TransactionSynchronizationRegistryService;
import org.jboss.as.txn.service.TxnServices;
import org.jboss.as.txn.service.UserTransactionService;
import org.jboss.dmr.ModelNode;
import org.jboss.dmr.Property;
import org.jboss.modules.Module;
import org.jboss.modules.ModuleIdentifier;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.service.ServiceTarget;
import org.jboss.remoting3.Endpoint;
import org.jboss.remoting3.RemotingOptions;
import org.wildfly.clustering.ejb.BeanManagerFactoryBuilderConfiguration;
import org.wildfly.clustering.service.Builder;
import org.wildfly.clustering.spi.CacheGroupBuilderProvider;
import org.wildfly.clustering.spi.CacheGroupServiceNameFactory;
import org.wildfly.clustering.spi.GroupBuilderProvider;
import org.wildfly.clustering.spi.LocalCacheGroupBuilderProvider;
import org.wildfly.clustering.spi.LocalGroupBuilderProvider;
import org.xnio.Option;
import org.xnio.OptionMap;
import org.xnio.Options;

import com.arjuna.ats.jbossatx.jta.RecoveryManagerService;


/**
 * A {@link AbstractAddStepHandler} to handle the add operation for the EJB
 * remote service, in the EJB subsystem
 *
 * @author <a href="mailto:cdewolf@redhat.com">Carlo de Wolf</a>
 */
public class EJB3RemoteServiceAdd extends AbstractAddStepHandler {
    static final EJB3RemoteServiceAdd INSTANCE = new EJB3RemoteServiceAdd();

    private EJB3RemoteServiceAdd() {
    }

    @Override
    protected void performRuntime(OperationContext context, ModelNode operation, ModelNode model) throws OperationFailedException {
        installRuntimeServices(context, model);

        // add ejb remote transactions repository service
        final EJBRemoteTransactionsRepository transactionsRepository = new EJBRemoteTransactionsRepository();
        final ServiceTarget serviceTarget = context.getServiceTarget();
        serviceTarget.addService(EJBRemoteTransactionsRepository.SERVICE_NAME, transactionsRepository)
                .addDependency(TransactionManagerService.SERVICE_NAME, TransactionManager.class, transactionsRepository.getTransactionManagerInjector())
                .addDependency(UserTransactionService.SERVICE_NAME, UserTransaction.class, transactionsRepository.getUserTransactionInjector())
                .addDependency(TxnServices.JBOSS_TXN_ARJUNA_RECOVERY_MANAGER, RecoveryManagerService.class, transactionsRepository.getRecoveryManagerInjector())
                .setInitialMode(ServiceController.Mode.ACTIVE)
                .install();

        // Service responsible for tracking cancel() invocations on remote async method calls
        final RemoteAsyncInvocationCancelStatusService asyncInvocationCancelStatusService = new RemoteAsyncInvocationCancelStatusService();
        serviceTarget.addService(RemoteAsyncInvocationCancelStatusService.SERVICE_NAME, asyncInvocationCancelStatusService).install();
    }

    void installRuntimeServices(final OperationContext context, final ModelNode model) throws OperationFailedException {
        final String connectorName = EJB3RemoteResourceDefinition.CONNECTOR_REF.resolveModelAttribute(context, model).asString();
        final String threadPoolName = EJB3RemoteResourceDefinition.THREAD_POOL_NAME.resolveModelAttribute(context, model).asString();
        final ServiceName remotingServerInfoServiceName = RemotingConnectorBindingInfoService.serviceName(connectorName);

        final ServiceTarget target = context.getServiceTarget();

        // Install the client-mapping service for the remoting connector
        new EJBRemotingConnectorClientMappingsEntryProviderService().build(target, remotingServerInfoServiceName)
                .setInitialMode(ServiceController.Mode.ON_DEMAND)
                .install();

        new RegistryInstallerService().build(target).setInitialMode(ServiceController.Mode.ON_DEMAND).install();

        // Handle case where no infinispan subsystem exists or does not define an ejb cache-container
        Resource rootResource = context.readResourceFromRoot(PathAddress.EMPTY_ADDRESS);
        PathElement infinispanPath = PathElement.pathElement(ModelDescriptionConstants.SUBSYSTEM, "infinispan");
        if (!rootResource.hasChild(infinispanPath) || !rootResource.getChild(infinispanPath).hasChild(PathElement.pathElement("cache-container", BeanManagerFactoryBuilderConfiguration.DEFAULT_CONTAINER_NAME))) {
            // Install services that would normally be installed by this container/cache
            ModuleIdentifier module = Module.forClass(this.getClass()).getIdentifier();
            for (GroupBuilderProvider provider : ServiceLoader.load(LocalGroupBuilderProvider.class, LocalGroupBuilderProvider.class.getClassLoader())) {
                for (Builder<?> builder : provider.getBuilders(BeanManagerFactoryBuilderConfiguration.DEFAULT_CONTAINER_NAME, module)) {
                    builder.build(target).install();
                }
            }
            for (CacheGroupBuilderProvider provider : ServiceLoader.load(LocalCacheGroupBuilderProvider.class, LocalCacheGroupBuilderProvider.class.getClassLoader())) {
                for (Builder<?> builder : provider.getBuilders(BeanManagerFactoryBuilderConfiguration.DEFAULT_CONTAINER_NAME, CacheGroupServiceNameFactory.DEFAULT_CACHE)) {
                    builder.build(target).install();
                }
            }
        }

        final OptionMap channelCreationOptions = this.getChannelCreationOptions(context);
        // Install the EJB remoting connector service which will listen for client connections on the remoting channel
        // TODO: Externalize (expose via management API if needed) the version and the marshalling strategy
        final EJBRemoteConnectorService ejbRemoteConnectorService = new EJBRemoteConnectorService((byte) 0x02, new String[]{"river"}, channelCreationOptions);
        target.addService(EJBRemoteConnectorService.SERVICE_NAME, ejbRemoteConnectorService)
                // add dependency on the Remoting subsystem endpoint
                .addDependency(RemotingServices.SUBSYSTEM_ENDPOINT, Endpoint.class, ejbRemoteConnectorService.getEndpointInjector())
                // add dependency on the remoting server (which allows remoting connector to connect to it)
                // add rest of the dependencies
                .addDependency(EJB3SubsystemModel.BASE_THREAD_POOL_SERVICE_NAME.append(threadPoolName), ExecutorService.class, ejbRemoteConnectorService.getExecutorService())
                .addDependency(DeploymentRepository.SERVICE_NAME, DeploymentRepository.class, ejbRemoteConnectorService.getDeploymentRepositoryInjector())
                .addDependency(EJBRemoteTransactionsRepository.SERVICE_NAME, EJBRemoteTransactionsRepository.class, ejbRemoteConnectorService.getEJBRemoteTransactionsRepositoryInjector())
                .addDependency(RegistryCollectorService.SERVICE_NAME, RegistryCollector.class, ejbRemoteConnectorService.getClusterRegistryCollectorInjector())
                .addDependency(TransactionManagerService.SERVICE_NAME, TransactionManager.class, ejbRemoteConnectorService.getTransactionManagerInjector())
                .addDependency(TransactionSynchronizationRegistryService.SERVICE_NAME, TransactionSynchronizationRegistry.class, ejbRemoteConnectorService.getTxSyncRegistryInjector())
                .addDependency(RemoteAsyncInvocationCancelStatusService.SERVICE_NAME, RemoteAsyncInvocationCancelStatusService.class, ejbRemoteConnectorService.getAsyncInvocationCancelStatusInjector())
                .addDependency(remotingServerInfoServiceName, RemotingConnectorBindingInfoService.RemotingConnectorInfo.class, ejbRemoteConnectorService.getRemotingConnectorInfoInjectedValue())
                .addDependency(SuspendController.SERVICE_NAME, SuspendController.class, ejbRemoteConnectorService.getSuspendControllerInjectedValue())
                .setInitialMode(ServiceController.Mode.ACTIVE)
                .install();
    }

    @Override
    protected void populateModel(ModelNode operation, ModelNode model) throws OperationFailedException {
        EJB3RemoteResourceDefinition.CONNECTOR_REF.validateAndSet(operation, model);
        EJB3RemoteResourceDefinition.THREAD_POOL_NAME.validateAndSet(operation, model);
    }

    private OptionMap getChannelCreationOptions(final OperationContext context) throws OperationFailedException {
        // read the full model of the current resource
        final ModelNode fullModel = Resource.Tools.readModel(context.readResource(PathAddress.EMPTY_ADDRESS));
        final ModelNode channelCreationOptions = fullModel.get(EJB3SubsystemModel.CHANNEL_CREATION_OPTIONS);
        if (channelCreationOptions.isDefined() && channelCreationOptions.asInt() > 0) {
            final ClassLoader loader = this.getClass().getClassLoader();
            final OptionMap.Builder builder = OptionMap.builder();
            for (final Property optionProperty : channelCreationOptions.asPropertyList()) {
                final String name = optionProperty.getName();
                final ModelNode propValueModel = optionProperty.getValue();
                final String type = RemoteConnectorChannelCreationOptionResource.CHANNEL_CREATION_OPTION_TYPE.resolveModelAttribute(context,propValueModel).asString();
                final String optionClassName = this.getClassNameForChannelOptionType(type);
                final String fullyQualifiedOptionName = optionClassName + "." + name;
                final Option option = Option.fromString(fullyQualifiedOptionName, loader);
                final String value = RemoteConnectorChannelCreationOptionResource.CHANNEL_CREATION_OPTION_VALUE.resolveModelAttribute(context, propValueModel).asString();
                builder.set(option, option.parseValue(value, loader));
            }
            return builder.getMap();
        }
        return OptionMap.EMPTY;
    }

    private String getClassNameForChannelOptionType(final String optionType) {
        if ("remoting".equals(optionType)) {
            return RemotingOptions.class.getName();
        }
        if ("xnio".equals(optionType)) {
            return Options.class.getName();
        }
        throw EjbLogger.ROOT_LOGGER.unknownChannelCreationOptionType(optionType);
    }
}


File: testsuite/integration/clustering/src/test/java/org/jboss/as/test/clustering/cluster/singleton/SingletonServiceTestCase.java
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
package org.jboss.as.test.clustering.cluster.singleton;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;

import javax.servlet.http.HttpServletResponse;

import org.apache.http.HttpResponse;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.utils.HttpClientUtils;
import org.apache.http.impl.client.HttpClients;
import org.jboss.arquillian.container.test.api.Deployment;
import org.jboss.arquillian.container.test.api.OperateOnDeployment;
import org.jboss.arquillian.container.test.api.RunAsClient;
import org.jboss.arquillian.container.test.api.TargetsContainer;
import org.jboss.arquillian.junit.Arquillian;
import org.jboss.arquillian.test.api.ArquillianResource;
import org.jboss.as.test.clustering.cluster.ClusterAbstractTestCase;
import org.jboss.as.test.clustering.cluster.singleton.service.MyService;
import org.jboss.as.test.clustering.cluster.singleton.service.MyServiceActivator;
import org.jboss.as.test.clustering.cluster.singleton.service.MyServiceServlet;
import org.jboss.shrinkwrap.api.Archive;
import org.jboss.shrinkwrap.api.ShrinkWrap;
import org.jboss.shrinkwrap.api.asset.StringAsset;
import org.jboss.shrinkwrap.api.spec.WebArchive;
import org.junit.Assert;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(Arquillian.class)
@RunAsClient
public class SingletonServiceTestCase extends ClusterAbstractTestCase {

    @Deployment(name = DEPLOYMENT_1, managed = false, testable = false)
    @TargetsContainer(CONTAINER_1)
    public static Archive<?> deployment0() {
        return createDeployment();
    }

    @Deployment(name = DEPLOYMENT_2, managed = false, testable = false)
    @TargetsContainer(CONTAINER_2)
    public static Archive<?> deployment1() {
        return createDeployment();
    }

    private static Archive<?> createDeployment() {
        WebArchive war = ShrinkWrap.create(WebArchive.class, "singleton.war");
        war.addPackage(MyService.class.getPackage());
        war.setManifest(new StringAsset("Manifest-Version: 1.0\nDependencies: org.jboss.as.server\n"));
        war.addAsServiceProvider(org.jboss.msc.service.ServiceActivator.class, MyServiceActivator.class);
        return war;
    }

    @Test
    public void testSingletonService(
            @ArquillianResource() @OperateOnDeployment(DEPLOYMENT_1) URL baseURL1,
            @ArquillianResource() @OperateOnDeployment(DEPLOYMENT_2) URL baseURL2)
            throws IOException, URISyntaxException {

        // Needed to be able to inject ArquillianResource
        stop(CONTAINER_2);

        HttpClient client = HttpClients.createDefault();

        // URLs look like "http://IP:PORT/singleton/service"
        URI defaultURI1 = MyServiceServlet.createURI(baseURL1, MyService.DEFAULT_SERVICE_NAME);
        URI defaultURI2 = MyServiceServlet.createURI(baseURL2, MyService.DEFAULT_SERVICE_NAME);

        log.info("URLs are: " + defaultURI1 + ", " + defaultURI2);

        URI quorumURI1 = MyServiceServlet.createURI(baseURL1, MyService.QUORUM_SERVICE_NAME);
        URI quorumURI2 = MyServiceServlet.createURI(baseURL2, MyService.QUORUM_SERVICE_NAME);

        try {
            HttpResponse response = client.execute(new HttpGet(defaultURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(NODE_1, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertNull(response.getFirstHeader("node"));
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            start(CONTAINER_2);

            response = client.execute(new HttpGet(defaultURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(defaultURI2));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI2));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            stop(CONTAINER_2);

            response = client.execute(new HttpGet(defaultURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(NODE_1, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertNull(response.getFirstHeader("node"));
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            start(CONTAINER_2);

            response = client.execute(new HttpGet(defaultURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(defaultURI2));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI2));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            stop(CONTAINER_1);

            response = client.execute(new HttpGet(defaultURI2));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(NODE_2, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI2));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertNull(response.getFirstHeader("node"));
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            start(CONTAINER_1);

            response = client.execute(new HttpGet(defaultURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI1));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(defaultURI2));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }

            response = client.execute(new HttpGet(quorumURI2));
            try {
                Assert.assertEquals(HttpServletResponse.SC_OK, response.getStatusLine().getStatusCode());
                Assert.assertEquals(MyServiceActivator.PREFERRED_NODE, response.getFirstHeader("node").getValue());
            } finally {
                HttpClientUtils.closeQuietly(response);
            }
        } finally {
            HttpClientUtils.closeQuietly(client);
        }
    }
}


File: testsuite/integration/clustering/src/test/java/org/jboss/as/test/clustering/cluster/singleton/service/MyServiceActivator.java
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

package org.jboss.as.test.clustering.cluster.singleton.service;

import static org.jboss.as.test.clustering.ClusteringTestConstants.NODE_2;

import org.wildfly.clustering.singleton.SingletonServiceBuilderFactory;
import org.wildfly.clustering.singleton.election.NamePreference;
import org.wildfly.clustering.singleton.election.PreferredSingletonElectionPolicy;
import org.wildfly.clustering.singleton.election.SimpleSingletonElectionPolicy;
import org.jboss.as.server.ServerEnvironment;
import org.jboss.as.server.ServerEnvironmentService;
import org.jboss.msc.service.ServiceActivator;
import org.jboss.msc.service.ServiceActivatorContext;
import org.jboss.msc.service.ServiceController;
import org.jboss.msc.service.ServiceName;
import org.jboss.msc.value.InjectedValue;

/**
 * @author Paul Ferraro
 */
public class MyServiceActivator implements ServiceActivator {

    private static final String CONTAINER_NAME = "server";
    private static final String CACHE_NAME = "default";
    public static final String PREFERRED_NODE = NODE_2;

    @Override
    public void activate(ServiceActivatorContext context) {
        install(MyService.DEFAULT_SERVICE_NAME, 1, context);
        install(MyService.QUORUM_SERVICE_NAME, 2, context);
    }

    private static void install(ServiceName name, int quorum, ServiceActivatorContext context) {
        InjectedValue<ServerEnvironment> env = new InjectedValue<>();
        MyService service = new MyService(env);
        ServiceController<?> factoryService = context.getServiceRegistry().getRequiredService(SingletonServiceBuilderFactory.SERVICE_NAME.append(CONTAINER_NAME, CACHE_NAME));
        SingletonServiceBuilderFactory factory = (SingletonServiceBuilderFactory) factoryService.getValue();
        factory.createSingletonServiceBuilder(name, service)
            .electionPolicy(new PreferredSingletonElectionPolicy(new SimpleSingletonElectionPolicy(), new NamePreference(PREFERRED_NODE)))
            .requireQuorum(quorum)
            .build(context.getServiceTarget())
                .addDependency(ServerEnvironmentService.SERVICE_NAME, ServerEnvironment.class, env)
                .setInitialMode(ServiceController.Mode.ACTIVE)
                .install()
        ;
    }
}


File: testsuite/mixed-domain/src/test/java/org/jboss/as/test/integration/domain/mixed/eap630/DomainAdjuster630.java
/*
 * JBoss, Home of Professional Open Source.
 * Copyright 2015, Red Hat Middleware LLC, and individual contributors
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

package org.jboss.as.test.integration.domain.mixed.eap630;

import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.EXTENSION;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.PROFILE;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SOCKET_BINDING;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SOCKET_BINDING_GROUP;
import static org.jboss.as.controller.descriptions.ModelDescriptionConstants.SUBSYSTEM;
import static org.jboss.as.controller.operations.common.Util.createAddOperation;
import static org.jboss.as.controller.operations.common.Util.createRemoveOperation;
import static org.jboss.as.controller.operations.common.Util.getUndefineAttributeOperation;
import static org.jboss.as.controller.operations.common.Util.getWriteAttributeOperation;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import org.jboss.as.clustering.infinispan.subsystem.InfinispanExtension;
import org.jboss.as.clustering.jgroups.subsystem.JGroupsExtension;
import org.jboss.as.controller.PathAddress;
import org.jboss.as.controller.client.helpers.domain.DomainClient;
import org.jboss.as.controller.operations.common.Util;
import org.jboss.as.ee.subsystem.EeExtension;
import org.jboss.as.ejb3.subsystem.EJB3Extension;
import org.jboss.as.remoting.RemotingExtension;
import org.jboss.as.test.integration.domain.mixed.DomainAdjuster;
import org.jboss.as.test.integration.domain.mixed.LegacySubsystemConfigurationUtil;
import org.jboss.as.weld.WeldExtension;
import org.jboss.dmr.ModelNode;
import org.wildfly.extension.batch.BatchSubsystemExtension;
import org.wildfly.extension.beanvalidation.BeanValidationExtension;
import org.wildfly.extension.io.IOExtension;
import org.wildfly.extension.messaging.activemq.MessagingExtension;
import org.wildfly.extension.requestcontroller.RequestControllerExtension;
import org.wildfly.extension.security.manager.SecurityManagerExtension;
import org.wildfly.extension.undertow.UndertowExtension;
import org.wildfly.iiop.openjdk.IIOPExtension;

/**
 * Does adjustments to the domain model for 6.3.0 legacy slaves
 *
 * @author <a href="mailto:kabir.khan@jboss.com">Kabir Khan</a>
 */
public class DomainAdjuster630 extends DomainAdjuster {
    @Override
    protected List<ModelNode> adjustForVersion(final DomainClient client, PathAddress profileAddress) throws Exception {
        final List<ModelNode> list = new ArrayList<>();

        list.addAll(removeBatch(profileAddress.append(SUBSYSTEM, BatchSubsystemExtension.SUBSYSTEM_NAME)));
        list.addAll(removeBeanValidation(profileAddress.append(SUBSYSTEM, BeanValidationExtension.SUBSYSTEM_NAME)));
        list.addAll(adjustEe(profileAddress.append(SUBSYSTEM, EeExtension.SUBSYSTEM_NAME)));
        list.addAll(adjustEjb3(profileAddress.append(SUBSYSTEM, EJB3Extension.SUBSYSTEM_NAME)));
        list.addAll(replaceIiopOpenJdk(client, profileAddress.append(SUBSYSTEM, IIOPExtension.SUBSYSTEM_NAME)));
        list.addAll(adjustInfinispan(profileAddress.append(SUBSYSTEM, InfinispanExtension.SUBSYSTEM_NAME)));
        list.addAll(removeIo(profileAddress.append(SUBSYSTEM, IOExtension.SUBSYSTEM_NAME)));
        list.addAll(adjustJGroups(profileAddress.append(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME)));
        list.addAll(adjustRemoting(profileAddress.append(SUBSYSTEM, RemotingExtension.SUBSYSTEM_NAME)));
        list.addAll(adjustWeld(profileAddress.append(SUBSYSTEM, WeldExtension.SUBSYSTEM_NAME)));
        list.addAll(removeRequestController(profileAddress.append(SUBSYSTEM, RequestControllerExtension.SUBSYSTEM_NAME)));
        list.addAll(removeSecurityManager(profileAddress.append(SecurityManagerExtension.SUBSYSTEM_PATH)));
        list.addAll(replaceUndertowWithWeb(profileAddress.append(SUBSYSTEM, UndertowExtension.SUBSYSTEM_NAME)));
        list.addAll(replaceActiveMqWithMessaging(profileAddress.append(SUBSYSTEM, MessagingExtension.SUBSYSTEM_NAME)));


        //Temporary workaround, something weird is going on in infinispan/jgroups so let's get rid of those for now
        //TODO Reenable these subsystems, it is important to see if we boot with them configured although the tests don't use clustering
        list.add(createRemoveOperation(profileAddress.append(SUBSYSTEM, InfinispanExtension.SUBSYSTEM_NAME)));
        list.add(createRemoveOperation(profileAddress.append(SUBSYSTEM, JGroupsExtension.SUBSYSTEM_NAME)));

        return list;
    }



    private Collection<? extends ModelNode> removeBatch(final PathAddress subsystem) {
        final List<ModelNode> list = new ArrayList<>();
        //batch and extension don't exist
        list.add(createRemoveOperation(subsystem));
        list.add(createRemoveOperation(PathAddress.pathAddress(EXTENSION, "org.wildfly.extension.batch")));
        return list;
    }


    private Collection<? extends ModelNode> removeBeanValidation(final PathAddress subsystem) {
        final List<ModelNode> list = new ArrayList<>();
        //bean-validation and extension don't exist
        list.add(createRemoveOperation(subsystem));
        list.add(createRemoveOperation(PathAddress.pathAddress(EXTENSION, "org.wildfly.extension.bean-validation")));
        return list;
    }


    private List<ModelNode> adjustEe(final PathAddress subsystem) throws Exception {
        final List<ModelNode> list = new ArrayList<>();
        //Concurrency resources are not available
        list.add(createRemoveOperation(subsystem.append("context-service", "default")));
        list.add(createRemoveOperation(subsystem.append("managed-thread-factory", "default")));
        list.add(createRemoveOperation(subsystem.append("managed-executor-service", "default")));
        list.add(createRemoveOperation(subsystem.append("managed-scheduled-executor-service", "default")));
        //default-bindings are not available
        list.add(createRemoveOperation(subsystem.append("service", "default-bindings")));
        return list;
    }

    private List<ModelNode> adjustEjb3(final PathAddress subsystem) throws Exception {
        final List<ModelNode> list = new ArrayList<>();
        //passivation-disabled-cache-ref is not understood
        list.add(
                getUndefineAttributeOperation(
                        subsystem, "default-sfsb-passivation-disabled-cache"));
        return list;
    }

    private List<ModelNode> replaceIiopOpenJdk(final DomainClient client, final PathAddress subsystem) throws Exception {
        final List<ModelNode> list = new ArrayList<>();
        //iiop-openjdk does not exist it used to be called jacorb

        //Remove the iiop-openjdk subsystem and extension
        list.add(createRemoveOperation(subsystem));
        list.add(createRemoveOperation(PathAddress.pathAddress(EXTENSION, "org.wildfly.iiop-openjdk")));
        //Add the jacorb extension
        list.add(createAddOperation(PathAddress.pathAddress(EXTENSION, "org.jboss.as.jacorb")));

        //This shoud be the same as in the iiop-openjdk.xml subsystem template
        ModelNode add = createAddOperation(subsystem.getParent().append(SUBSYSTEM, "jacorb"));
        add.get("socket-binding").set("iiop");
        add.get("ssl-socket-binding").set("iiop-ssl");
        add.get("transactions").set("spec");
        add.get("security").set("identity");
        list.add(add);

        return list;
    }

    private List<ModelNode> adjustInfinispan(final PathAddress subsystem) throws Exception {
        final List<ModelNode> list = new ArrayList<>();
        //Statistics need to be enabled for all cache containers and caches
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "server")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "server").append("replicated-cache", "default")));
        list.add(getWriteAttributeOperation(subsystem.append("cache-container", "server").append("transport", "TRANSPORT"), "stack", new ModelNode("udp ")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "web")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "web").append("distributed-cache", "dist")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "ejb")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "ejb").append("distributed-cache", "dist")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "hibernate")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "hibernate").append("invalidation-cache", "entity")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "hibernate").append("local-cache", "local-query")));
        list.add(setStatisticsEnabledTrue(
                subsystem.append("cache-container", "hibernate").append("replicated-cache", "timestamps")));
        return list;
    }

    private Collection<? extends ModelNode> removeIo(final PathAddress subsystem) {
        final List<ModelNode> list = new ArrayList<>();
        //io and extension don't exist so remove them
        //We also must remove the remoting requirement for io worker capability
        list.add(createRemoveOperation(subsystem.getParent().append(SUBSYSTEM, "remoting").append("configuration", "endpoint")));
        list.add(createRemoveOperation(subsystem));
        list.add(createRemoveOperation(PathAddress.pathAddress(EXTENSION, "org.wildfly.extension.io")));
        return list;
    }


    private List<ModelNode> adjustJGroups(final PathAddress subsystem) throws Exception {
        final List<ModelNode> list = new ArrayList<>();
        //default-channel is not understood
        list.add(
                getUndefineAttributeOperation(
                        subsystem, "default-channel"));
        //In fact channels don't work
        list.add(createRemoveOperation(subsystem.append("channel", "ee")));

        // pbcast.NAKACK2 does not exist, use pbcast.NAKACK instead
        // UNICAST3 does not exist, use UNICAST2 instead
        //All this code is to remove and re-add the protocols including the rename to preserve the order
        //TODO once we support indexed adds, use those instead
        //udp
        PathAddress udp = subsystem.append("stack", "udp");
        list.add(createRemoveOperation(udp.append("protocol", "pbcast.NAKACK2")));
        list.add(createRemoveOperation(udp.append("protocol", "UNICAST3")));
        list.add(createRemoveOperation(udp.append("protocol", "pbcast.STABLE")));
        list.add(createRemoveOperation(udp.append("protocol", "pbcast.GMS")));
        list.add(createRemoveOperation(udp.append("protocol", "UFC")));
        list.add(createRemoveOperation(udp.append("protocol", "MFC")));
        list.add(createRemoveOperation(udp.append("protocol", "FRAG2")));
        list.add(createRemoveOperation(udp.append("protocol", "RSVP")));
        list.add(createAddOperation(udp.append("protocol", "pbcast.NAKACK")));
        list.add(createAddOperation(udp.append("protocol", "UNICAST2")));
        list.add(createAddOperation(udp.append("protocol", "pbcast.STABLE")));
        list.add(createAddOperation(udp.append("protocol", "pbcast.GMS")));
        list.add(createAddOperation(udp.append("protocol", "UFC")));
        list.add(createAddOperation(udp.append("protocol", "MFC")));
        list.add(createAddOperation(udp.append("protocol", "FRAG2")));
        list.add(createAddOperation(udp.append("protocol", "RSVP")));

        //udp
        PathAddress tcp = subsystem.append("stack", "tcp");
        list.add(createRemoveOperation(tcp.append("protocol", "pbcast.NAKACK2")));
        list.add(createRemoveOperation(tcp.append("protocol", "UNICAST3")));
        list.add(createRemoveOperation(tcp.append("protocol", "pbcast.STABLE")));
        list.add(createRemoveOperation(tcp.append("protocol", "pbcast.GMS")));
        list.add(createRemoveOperation(tcp.append("protocol", "MFC")));
        list.add(createRemoveOperation(tcp.append("protocol", "FRAG2")));
        list.add(createRemoveOperation(tcp.append("protocol", "RSVP")));
        list.add(createAddOperation(tcp.append("protocol", "pbcast.NAKACK")));
        list.add(createAddOperation(tcp.append("protocol", "UNICAST2")));
        list.add(createAddOperation(tcp.append("protocol", "pbcast.STABLE")));
        list.add(createAddOperation(tcp.append("protocol", "pbcast.GMS")));
        list.add(createAddOperation(tcp.append("protocol", "UFC")));
        list.add(createAddOperation(tcp.append("protocol", "FRAG2")));
        list.add(createAddOperation(tcp.append("protocol", "RSVP")));

        return list;
    }

    private Collection<? extends ModelNode> adjustRemoting(final PathAddress subsystem) {
        final List<ModelNode> list = new ArrayList<>();
        //The endpoint configuration does not exist
        // BES 2015/07/15 -- this is done in removeIO now so the io worker capability and the requirement for it
        // both go in the same op
        //list.add(createRemoveOperation(subsystem.append("configuration", "endpoint")));

        //Replace the http-remoting connector with a normal remoting-connector. This needs the remoting socket binding,
        //so add that too
        list.add(createRemoveOperation(subsystem.append("http-connector", "http-remoting-connector")));
        ModelNode addSocketBinding =
                createAddOperation(
                        PathAddress.pathAddress(SOCKET_BINDING_GROUP, "full-ha-sockets")
                                .append(SOCKET_BINDING, "remoting"));
        addSocketBinding.get("port").set(4447);
        list.add(addSocketBinding);
        ModelNode addRemoting = createAddOperation(subsystem.append("connector", "remoting-connector"));
        addRemoting.get("socket-binding").set("remoting");
        addRemoting.get("security-realm").set("ApplicationRealm");
        list.add(addRemoting);
        return list;

    }

    private Collection<? extends ModelNode> removeRequestController(final PathAddress subsystem) {
        final List<ModelNode> list = new ArrayList<>();
        //request controller and extension don't exist
        list.add(createRemoveOperation(subsystem));
        list.add(createRemoveOperation(PathAddress.pathAddress(EXTENSION, "org.wildfly.extension.request-controller")));
        return list;
    }

    private Collection<? extends ModelNode> removeSecurityManager(final PathAddress subsystem) {
        final List<ModelNode> list = new ArrayList<>();
        //security manager and extension don't exist
        list.add(createRemoveOperation(subsystem));
        list.add(createRemoveOperation(PathAddress.pathAddress(EXTENSION, "org.wildfly.extension.security.manager")));
        return list;
    }


    private Collection<? extends ModelNode> replaceUndertowWithWeb(final PathAddress subsystem) {
        final List<ModelNode> list = new ArrayList<>();
        //Undertow does not exist, remove it and the extension
        list.add(createRemoveOperation(subsystem));
        list.add(createRemoveOperation(PathAddress.pathAddress(EXTENSION, "org.wildfly.extension.undertow")));

        //Add JBoss Web extension and subsystem
        list.add(createAddOperation(PathAddress.pathAddress(EXTENSION, "org.jboss.as.web")));
        final PathAddress web = subsystem.getParent().append(SUBSYSTEM, "web");
        final ModelNode addWeb = Util.createAddOperation(web);
        addWeb.get("default-virtual-server").set("default-host");
        addWeb.get("native").set("false");
        list.add(addWeb);
        list.add(createAddOperation(web.append("configuration", "container")));
        list.add(createAddOperation(web.append("configuration", "static-resources")));
        list.add(createAddOperation(web.append("configuration", "jsp-configuration")));
        ModelNode addHttp = Util.createAddOperation(web.append("connector", "http"));
        addHttp.get("protocol").set("HTTP/1.1");
        addHttp.get("scheme").set("http");
        addHttp.get("socket-binding").set("http");
        list.add(addHttp);
        ModelNode addAjp = Util.createAddOperation(web.append("connector", "ajp"));
        addAjp.get("protocol").set("AJP/1.3");
        addAjp.get("scheme").set("http");
        addAjp.get("socket-binding").set("ajp");
        list.add(addAjp);
        ModelNode addVirtualServer = Util.createAddOperation(web.append("virtual-server", "default-host"));
        addVirtualServer.get("enable-welcome-root").set(true);
        addVirtualServer.get("alias").add("localhost").add("example.com");
        list.add(addVirtualServer);

        return list;
    }

    private Collection<? extends ModelNode> replaceActiveMqWithMessaging(PathAddress subsystem) throws Exception {
        final List<ModelNode> list = new ArrayList<>();
        //messaging-activemq does not exist, remove it and the extension
        list.add(createRemoveOperation(subsystem));
        list.add(createRemoveOperation(PathAddress.pathAddress(EXTENSION, "org.wildfly.extension.messaging-activemq")));

        //Add legacy messaging extension
        list.add(createAddOperation(PathAddress.pathAddress(EXTENSION, "org.jboss.as.messaging")));

        //Get the subsystem add operations (since the subsystem is huge, and there is a template, use the util)
        LegacySubsystemConfigurationUtil util =
                new LegacySubsystemConfigurationUtil(
                        new org.jboss.as.messaging.MessagingExtension(), "messaging", "ha", "subsystem-templates/messaging.xml");

        list.addAll(util.getSubsystemOperations());


        //Now adjust the things from the template which are not available in the legacy server

        //http acceptors and connectors are not available
        PathAddress messaging = PathAddress.pathAddress(PROFILE, "full-ha").append(SUBSYSTEM, "messaging");
        PathAddress server = messaging.append("hornetq-server", "default");
        list.add(createRemoveOperation(server.append("http-acceptor", "http-acceptor")));
        list.add(createRemoveOperation(server.append("http-acceptor", "http-acceptor-throughput")));
        list.add(createRemoveOperation(server.append("http-connector", "http-connector")));
        list.add(createRemoveOperation(server.append("http-connector", "http-connector-throughput")));
        //TODO here we should add a remote connector, for now use the in-vm one
        list.add(getWriteAttributeOperation(server.append("broadcast-group", "bg-group1"), "connectors",
                new ModelNode().add("in-vm")));

        return list;
    }


    private Collection<? extends ModelNode> adjustWeld(final PathAddress subsystem) {
        final List<ModelNode> list = new ArrayList<>();
        list.add(getWriteAttributeOperation(subsystem, "require-bean-descriptor", true));
        list.add(getWriteAttributeOperation(subsystem, "non-portable-mode", true));
        return list;
    }

    private ModelNode setStatisticsEnabledTrue(final PathAddress addr) {
        return getWriteAttributeOperation(addr, "statistics-enabled", true);
    }

    @Override
    protected String getJaspiTestAuthModuleName() {
        return "org.jboss.as.web.security.jaspi.modules.HTTPBasicServerAuthModule";
    }
}
