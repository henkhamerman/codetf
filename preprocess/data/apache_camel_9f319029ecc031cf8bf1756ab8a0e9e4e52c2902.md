Refactoring Types: ['Extract Interface']
he/camel/model/DataFormatDefinition.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.camel.model;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlTransient;
import javax.xml.bind.annotation.XmlType;

import org.apache.camel.CamelContext;
import org.apache.camel.spi.DataFormat;
import org.apache.camel.spi.Metadata;
import org.apache.camel.spi.RouteContext;
import org.apache.camel.util.IntrospectionSupport;
import org.apache.camel.util.ObjectHelper;

import static org.apache.camel.util.EndpointHelper.isReferenceParameter;

/**
 * Represents a Camel data format
 */
@Metadata(label = "dataformat,transformation")
@XmlType(name = "dataFormat")
@XmlAccessorType(XmlAccessType.FIELD)
public class DataFormatDefinition extends IdentifiedType {
    @XmlTransient
    private DataFormat dataFormat;
    @XmlTransient
    private String dataFormatName;

    public DataFormatDefinition() {
    }

    public DataFormatDefinition(DataFormat dataFormat) {
        this.dataFormat = dataFormat;
    }

    protected DataFormatDefinition(String dataFormatName) {
        this.dataFormatName = dataFormatName;
    }

    /**
     * Factory method to create the data format
     *
     * @param routeContext route context
     * @param type         the data format type
     * @param ref          reference to lookup for a data format
     * @return the data format or null if not possible to create
     */
    public static DataFormat getDataFormat(RouteContext routeContext, DataFormatDefinition type, String ref) {
        if (type == null) {
            ObjectHelper.notNull(ref, "ref or type");

            // try to let resolver see if it can resolve it, its not always possible
            type = ((ModelCamelContext) routeContext.getCamelContext()).resolveDataFormatDefinition(ref);

            if (type != null) {
                return type.getDataFormat(routeContext);
            }

            DataFormat dataFormat = routeContext.getCamelContext().resolveDataFormat(ref);
            if (dataFormat == null) {
                throw new IllegalArgumentException("Cannot find data format in registry with ref: " + ref);
            }

            return dataFormat;
        } else {
            return type.getDataFormat(routeContext);
        }
    }

    public DataFormat getDataFormat(RouteContext routeContext) {
        if (dataFormat == null) {
            Runnable propertyPlaceholdersChangeReverter = ProcessorDefinitionHelper.createPropertyPlaceholdersChangeReverter();

            // resolve properties before we create the data format
            try {
                ProcessorDefinitionHelper.resolvePropertyPlaceholders(routeContext.getCamelContext(), this);
            } catch (Exception e) {
                throw new IllegalArgumentException("Error resolving property placeholders on data format: " + this, e);
            }
            try {
                dataFormat = createDataFormat(routeContext);
                if (dataFormat != null) {
                    configureDataFormat(dataFormat, routeContext.getCamelContext());
                } else {
                    throw new IllegalArgumentException(
                            "Data format '" + (dataFormatName != null ? dataFormatName : "<null>") + "' could not be created. "
                                    + "Ensure that the data format is valid and the associated Camel component is present on the classpath");
                }
            } finally {
                propertyPlaceholdersChangeReverter.run();
            }
        }
        return dataFormat;
    }

    /**
     * Factory method to create the data format instance
     */
    protected DataFormat createDataFormat(RouteContext routeContext) {
        // must use getDataFormatName() as we need special logic in json dataformat
        if (getDataFormatName() != null) {
            return routeContext.getCamelContext().resolveDataFormat(getDataFormatName());
        }
        return null;
    }

    /**
     * Allows derived classes to customize the data format
     *
     * @deprecated use {@link #configureDataFormat(org.apache.camel.spi.DataFormat, org.apache.camel.CamelContext)}
     */
    @Deprecated
    protected void configureDataFormat(DataFormat dataFormat) {
    }

    /**
     * Allows derived classes to customize the data format
     */
    protected void configureDataFormat(DataFormat dataFormat, CamelContext camelContext) {
    }

    /**
     * Sets a named property on the data format instance using introspection
     *
     * @deprecated use {@link #setProperty(org.apache.camel.CamelContext, Object, String, Object)}
     */
    @Deprecated
    protected void setProperty(Object bean, String name, Object value) {
        setProperty(null, bean, name, value);
    }

    /**
     * Sets a named property on the data format instance using introspection
     */
    protected void setProperty(CamelContext camelContext, Object bean, String name, Object value) {
        try {
            String ref = value instanceof String ? value.toString() : null;
            if (isReferenceParameter(ref) && camelContext != null) {
                IntrospectionSupport.setProperty(camelContext, camelContext.getTypeConverter(), bean, name, null, ref, true);
            } else {
                IntrospectionSupport.setProperty(bean, name, value);
            }
        } catch (Exception e) {
            throw new IllegalArgumentException("Failed to set property: " + name + " on: " + bean + ". Reason: " + e, e);
        }
    }

    public String getDataFormatName() {
        return dataFormatName;
    }

    public void setDataFormatName(String dataFormatName) {
        this.dataFormatName = dataFormatName;
    }

    public DataFormat getDataFormat() {
        return dataFormat;
    }

    public void setDataFormat(DataFormat dataFormat) {
        this.dataFormat = dataFormat;
    }

    public String getShortName() {
        String name = getClass().getSimpleName();
        if (name.endsWith("DataFormat")) {
            name = name.substring(0, name.indexOf("DataFormat"));
        }
        return name;
    }

}



File: camel-core/src/main/java/org/apache/camel/model/ProcessorDefinition.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.camel.model;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlAnyAttribute;
import javax.xml.bind.annotation.XmlAttribute;
import javax.xml.bind.annotation.XmlTransient;
import javax.xml.namespace.QName;

import org.apache.camel.Channel;
import org.apache.camel.Endpoint;
import org.apache.camel.ErrorHandlerFactory;
import org.apache.camel.Exchange;
import org.apache.camel.ExchangePattern;
import org.apache.camel.Expression;
import org.apache.camel.LoggingLevel;
import org.apache.camel.Predicate;
import org.apache.camel.Processor;
import org.apache.camel.Route;
import org.apache.camel.builder.DataFormatClause;
import org.apache.camel.builder.ExpressionBuilder;
import org.apache.camel.builder.ExpressionClause;
import org.apache.camel.builder.ProcessorBuilder;
import org.apache.camel.model.language.ConstantExpression;
import org.apache.camel.model.language.ExpressionDefinition;
import org.apache.camel.model.language.LanguageExpression;
import org.apache.camel.model.rest.RestDefinition;
import org.apache.camel.processor.InterceptEndpointProcessor;
import org.apache.camel.processor.Pipeline;
import org.apache.camel.processor.aggregate.AggregationStrategy;
import org.apache.camel.processor.interceptor.DefaultChannel;
import org.apache.camel.processor.interceptor.Delayer;
import org.apache.camel.processor.interceptor.HandleFault;
import org.apache.camel.processor.interceptor.StreamCaching;
import org.apache.camel.processor.loadbalancer.LoadBalancer;
import org.apache.camel.spi.DataFormat;
import org.apache.camel.spi.IdAware;
import org.apache.camel.spi.IdempotentRepository;
import org.apache.camel.spi.InterceptStrategy;
import org.apache.camel.spi.LifecycleStrategy;
import org.apache.camel.spi.Policy;
import org.apache.camel.spi.RouteContext;
import org.apache.camel.util.IntrospectionSupport;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Base class for processor types that most XML types extend.
 *
 * @version 
 */
@XmlAccessorType(XmlAccessType.FIELD)
public abstract class ProcessorDefinition<Type extends ProcessorDefinition<Type>> extends OptionalIdentifiedDefinition<Type> implements Block {
    @XmlTransient
    private static final AtomicInteger COUNTER = new AtomicInteger();
    @XmlTransient
    protected final Logger log = LoggerFactory.getLogger(getClass());
    @XmlAttribute
    protected Boolean inheritErrorHandler;
    @XmlTransient
    private final LinkedList<Block> blocks = new LinkedList<Block>();
    @XmlTransient
    private ProcessorDefinition<?> parent;
    @XmlTransient
    private final List<InterceptStrategy> interceptStrategies = new ArrayList<InterceptStrategy>();
    // use xs:any to support optional property placeholders
    @XmlAnyAttribute
    private Map<QName, Object> otherAttributes;
    @XmlTransient
    private final int index;

    protected ProcessorDefinition() {
        // every time we create a definition we should inc the COUNTER counter
        index = COUNTER.getAndIncrement();
    }

    /**
     * Gets the unique index number for when this {@link ProcessorDefinition} was created by its constructor.
     * <p/>
     * This can be used to know the order in which the definition was created when assembled as a route.
     *
     * @return the index number
     */
    public int getIndex() {
        return index;
    }

    // else to use an optional attribute in JAXB2
    public abstract List<ProcessorDefinition<?>> getOutputs();

    public abstract boolean isOutputSupported();

    /**
     * Whether this definition can only be added as top-level directly on the route itself (such as onException,onCompletion,intercept, etc.)
     * <p/>
     * If trying to add a top-level only definition to a nested output would fail in the {@link #addOutput(ProcessorDefinition)}
     * method.
     */
    public boolean isTopLevelOnly() {
        return false;
    }

    /**
     * Whether this model is abstract or not.
     * <p/>
     * An abstract model is something that is used for configuring cross cutting concerns such as
     * error handling, transaction policies, interceptors etc.
     * <p/>
     * Regular definitions is what is part of the route, such as ToDefinition, WireTapDefinition and the likes.
     * <p/>
     * Will by default return <tt>false</tt> to indicate regular definition, so all the abstract definitions
     * must override this method and return <tt>true</tt> instead.
     * <p/>
     * This information is used in camel-spring to let Camel work a bit on the model provided by JAXB from the
     * Spring XML file. This is needed to handle those cross cutting concerns properly. The Java DSL does not
     * have this issue as it can work this out directly using the fluent builder methods.
     *
     * @return <tt>true</tt> for abstract, otherwise <tt>false</tt> for regular.
     */
    public boolean isAbstract() {
        return false;
    }

    /**
     * Override this in definition class and implement logic to create the processor
     * based on the definition model.
     */
    public Processor createProcessor(RouteContext routeContext) throws Exception {
        throw new UnsupportedOperationException("Not implemented yet for class: " + getClass().getName());
    }

    /**
     * Prefer to use {#link #createChildProcessor}.
     */
    public Processor createOutputsProcessor(RouteContext routeContext) throws Exception {
        Collection<ProcessorDefinition<?>> outputs = getOutputs();
        return createOutputsProcessor(routeContext, outputs);
    }

    /**
     * Creates the child processor (outputs) from the current definition
     *
     * @param routeContext   the route context
     * @param mandatory      whether or not children is mandatory (ie the definition should have outputs)
     * @return the created children, or <tt>null</tt> if definition had no output
     * @throws Exception is thrown if error creating the child or if it was mandatory and there was no output defined on definition
     */
    public Processor createChildProcessor(RouteContext routeContext, boolean mandatory) throws Exception {
        Processor children = null;
        // at first use custom factory
        if (routeContext.getCamelContext().getProcessorFactory() != null) {
            children = routeContext.getCamelContext().getProcessorFactory().createChildProcessor(routeContext, this, mandatory);
        }
        // fallback to default implementation if factory did not create the child
        if (children == null) {
            children = createOutputsProcessor(routeContext);
        }

        if (children == null && mandatory) {
            throw new IllegalArgumentException("Definition has no children on " + this);
        }
        return children;
    }

    @Override
    public void addOutput(ProcessorDefinition<?> output) {
        if (!blocks.isEmpty()) {
            // let the Block deal with the output
            Block block = blocks.getLast();
            block.addOutput(output);
            return;
        }

        // validate that top-level is only added on the route (eg top level)
        boolean parentIsRoute = this.getClass().isAssignableFrom(RouteDefinition.class);
        if (output.isTopLevelOnly() && !parentIsRoute) {
            throw new IllegalArgumentException("The output must be added as top-level on the route. Try moving " + output + " to the top of route.");
        }

        output.setParent(this);
        configureChild(output);
        getOutputs().add(output);
    }

    public void clearOutput() {
        getOutputs().clear();
        blocks.clear();
    }

    public void addRoutes(RouteContext routeContext, Collection<Route> routes) throws Exception {
        Processor processor = makeProcessor(routeContext);
        if (processor == null) {
            // no processor to add
            return;
        }

        if (!routeContext.isRouteAdded()) {
            boolean endpointInterceptor = false;

            // are we routing to an endpoint interceptor, if so we should not add it as an event driven
            // processor as we use the producer to trigger the interceptor
            if (processor instanceof Channel) {
                Channel channel = (Channel) processor;
                Processor next = channel.getNextProcessor();
                if (next instanceof InterceptEndpointProcessor) {
                    endpointInterceptor = true;
                }
            }

            // only add regular processors as event driven
            if (endpointInterceptor) {
                log.debug("Endpoint interceptor should not be added as an event driven consumer route: {}", processor);
            } else {
                log.trace("Adding event driven processor: {}", processor);
                routeContext.addEventDrivenProcessor(processor);
            }

        }
    }

    /**
     * Wraps the child processor in whatever necessary interceptors and error handlers
     */
    public Processor wrapProcessor(RouteContext routeContext, Processor processor) throws Exception {
        // dont double wrap
        if (processor instanceof Channel) {
            return processor;
        }
        return wrapChannel(routeContext, processor, null);
    }

    protected Processor wrapChannel(RouteContext routeContext, Processor processor, ProcessorDefinition<?> child) throws Exception {
        // put a channel in between this and each output to control the route flow logic
        ModelChannel channel = createChannel(routeContext);
        channel.setNextProcessor(processor);

        // add interceptor strategies to the channel must be in this order: camel context, route context, local
        addInterceptStrategies(routeContext, channel, routeContext.getCamelContext().getInterceptStrategies());
        addInterceptStrategies(routeContext, channel, routeContext.getInterceptStrategies());
        addInterceptStrategies(routeContext, channel, this.getInterceptStrategies());

        // must do this ugly cast to avoid compiler error on AIX/HP-UX
        ProcessorDefinition<?> defn = (ProcessorDefinition<?>) this;

        // set the child before init the channel
        channel.setChildDefinition(child);
        channel.initChannel(defn, routeContext);

        // set the error handler, must be done after init as we can set the error handler as first in the chain
        if (defn instanceof TryDefinition || defn instanceof CatchDefinition || defn instanceof FinallyDefinition) {
            // do not use error handler for try .. catch .. finally blocks as it will handle errors itself
            log.trace("{} is part of doTry .. doCatch .. doFinally so no error handler is applied", defn);
        } else if (ProcessorDefinitionHelper.isParentOfType(TryDefinition.class, defn, true)
                || ProcessorDefinitionHelper.isParentOfType(CatchDefinition.class, defn, true)
                || ProcessorDefinitionHelper.isParentOfType(FinallyDefinition.class, defn, true)) {
            // do not use error handler for try .. catch .. finally blocks as it will handle errors itself
            // by checking that any of our parent(s) is not a try .. catch or finally type
            log.trace("{} is part of doTry .. doCatch .. doFinally so no error handler is applied", defn);
        } else if (defn instanceof OnExceptionDefinition || ProcessorDefinitionHelper.isParentOfType(OnExceptionDefinition.class, defn, true)) {
            log.trace("{} is part of OnException so no error handler is applied", defn);
            // do not use error handler for onExceptions blocks as it will handle errors itself
        } else if (defn instanceof MulticastDefinition) {
            // do not use error handler for multicast as it offers fine grained error handlers for its outputs
            // however if share unit of work is enabled, we need to wrap an error handler on the multicast parent
            MulticastDefinition def = (MulticastDefinition) defn;
            boolean isShareUnitOfWork = def.getShareUnitOfWork() != null && def.getShareUnitOfWork();
            if (isShareUnitOfWork && child == null) {
                // only wrap the parent (not the children of the multicast)
                wrapChannelInErrorHandler(channel, routeContext);
            } else {
                log.trace("{} is part of multicast which have special error handling so no error handler is applied", defn);
            }
        } else {
            // use error handler by default or if configured to do so
            wrapChannelInErrorHandler(channel, routeContext);
        }

        // do post init at the end
        channel.postInitChannel(defn, routeContext);
        log.trace("{} wrapped in Channel: {}", defn, channel);

        return channel;
    }

    /**
     * Wraps the given channel in error handler (if error handler is inherited)
     *
     * @param channel       the channel
     * @param routeContext  the route context
     * @throws Exception can be thrown if failed to create error handler builder
     */
    private void wrapChannelInErrorHandler(Channel channel, RouteContext routeContext) throws Exception {
        if (isInheritErrorHandler() == null || isInheritErrorHandler()) {
            log.trace("{} is configured to inheritErrorHandler", this);
            Processor output = channel.getOutput();
            Processor errorHandler = wrapInErrorHandler(routeContext, output);
            // set error handler on channel
            channel.setErrorHandler(errorHandler);
        } else {
            log.debug("{} is configured to not inheritErrorHandler.", this);
        }
    }

    /**
     * Wraps the given output in an error handler
     *
     * @param routeContext the route context
     * @param output the output
     * @return the output wrapped with the error handler
     * @throws Exception can be thrown if failed to create error handler builder
     */
    protected Processor wrapInErrorHandler(RouteContext routeContext, Processor output) throws Exception {
        ErrorHandlerFactory builder = routeContext.getRoute().getErrorHandlerBuilder();
        // create error handler
        Processor errorHandler = builder.createErrorHandler(routeContext, output);

        // invoke lifecycles so we can manage this error handler builder
        for (LifecycleStrategy strategy : routeContext.getCamelContext().getLifecycleStrategies()) {
            strategy.onErrorHandlerAdd(routeContext, errorHandler, builder);
        }

        return errorHandler;
    }

    /**
     * Adds the given list of interceptors to the channel.
     *
     * @param routeContext  the route context
     * @param channel       the channel to add strategies
     * @param strategies    list of strategies to add.
     */
    protected void addInterceptStrategies(RouteContext routeContext, Channel channel, List<InterceptStrategy> strategies) {
        for (InterceptStrategy strategy : strategies) {
            if (!routeContext.isStreamCaching() && strategy instanceof StreamCaching) {
                // stream cache is disabled so we should not add it
                continue;
            }
            if (!routeContext.isHandleFault() && strategy instanceof HandleFault) {
                // handle fault is disabled so we should not add it
                continue;
            }
            if (strategy instanceof Delayer) {
                if (routeContext.getDelayer() == null || routeContext.getDelayer() <= 0) {
                    // delayer is disabled so we should not add it
                    continue;
                } else {
                    // replace existing delayer as delayer have individual configuration
                    Iterator<InterceptStrategy> it = channel.getInterceptStrategies().iterator();
                    while (it.hasNext()) {
                        InterceptStrategy existing = it.next();
                        if (existing instanceof Delayer) {
                            it.remove();
                        }
                    }
                    // add the new correct delayer
                    channel.addInterceptStrategy(strategy);
                    continue;
                }
            }

            // add strategy
            channel.addInterceptStrategy(strategy);
        }
    }

    /**
     * Creates a new instance of some kind of composite processor which defaults
     * to using a {@link Pipeline} but derived classes could change the behaviour
     */
    protected Processor createCompositeProcessor(RouteContext routeContext, List<Processor> list) throws Exception {
        return new Pipeline(routeContext.getCamelContext(), list);
    }

    /**
     * Creates a new instance of the {@link Channel}.
     */
    protected ModelChannel createChannel(RouteContext routeContext) throws Exception {
        return new DefaultChannel();
    }

    protected Processor createOutputsProcessor(RouteContext routeContext, Collection<ProcessorDefinition<?>> outputs) throws Exception {
        // We will save list of actions to restore the outputs back to the original state.
        Runnable propertyPlaceholdersChangeReverter = ProcessorDefinitionHelper.createPropertyPlaceholdersChangeReverter();
        try {
            return createOutputsProcessorImpl(routeContext, outputs);
        } finally {
            propertyPlaceholdersChangeReverter.run();
        }
    }

    protected Processor createOutputsProcessorImpl(RouteContext routeContext, Collection<ProcessorDefinition<?>> outputs) throws Exception {
        List<Processor> list = new ArrayList<Processor>();
        for (ProcessorDefinition<?> output : outputs) {

            // allow any custom logic before we create the processor
            output.preCreateProcessor();

            // resolve properties before we create the processor
            ProcessorDefinitionHelper.resolvePropertyPlaceholders(routeContext.getCamelContext(), output);

            // resolve constant fields (eg Exchange.FILE_NAME)
            ProcessorDefinitionHelper.resolveKnownConstantFields(output);

            // also resolve properties and constant fields on embedded expressions
            ProcessorDefinition<?> me = (ProcessorDefinition<?>) output;
            if (me instanceof ExpressionNode) {
                ExpressionNode exp = (ExpressionNode) me;
                ExpressionDefinition expressionDefinition = exp.getExpression();
                if (expressionDefinition != null) {
                    // resolve properties before we create the processor
                    ProcessorDefinitionHelper.resolvePropertyPlaceholders(routeContext.getCamelContext(), expressionDefinition);

                    // resolve constant fields (eg Exchange.FILE_NAME)
                    ProcessorDefinitionHelper.resolveKnownConstantFields(expressionDefinition);
                }
            }

            Processor processor = createProcessor(routeContext, output);

            // inject id
            if (processor instanceof IdAware) {
                String id = output.idOrCreate(routeContext.getCamelContext().getNodeIdFactory());
                ((IdAware) processor).setId(id);
            }

            if (output instanceof Channel && processor == null) {
                continue;
            }

            Processor channel = wrapChannel(routeContext, processor, output);
            list.add(channel);
        }

        // if more than one output wrap than in a composite processor else just keep it as is
        Processor processor = null;
        if (!list.isEmpty()) {
            if (list.size() == 1) {
                processor = list.get(0);
            } else {
                processor = createCompositeProcessor(routeContext, list);
            }
        }

        return processor;
    }

    protected Processor createProcessor(RouteContext routeContext, ProcessorDefinition<?> output) throws Exception {
        Processor processor = null;
        // at first use custom factory
        if (routeContext.getCamelContext().getProcessorFactory() != null) {
            processor = routeContext.getCamelContext().getProcessorFactory().createProcessor(routeContext, output);
        }
        // fallback to default implementation if factory did not create the processor
        if (processor == null) {
            processor = output.createProcessor(routeContext);
        }
        return processor;
    }

    /**
     * Creates the processor and wraps it in any necessary interceptors and error handlers
     */
    protected Processor makeProcessor(RouteContext routeContext) throws Exception {
        // We will save list of actions to restore the definition back to the original state.
        Runnable propertyPlaceholdersChangeReverter = ProcessorDefinitionHelper.createPropertyPlaceholdersChangeReverter();
        try {
            return makeProcessorImpl(routeContext);
        } finally {
            // Lets restore
            propertyPlaceholdersChangeReverter.run();
        }
    }

    private Processor makeProcessorImpl(RouteContext routeContext) throws Exception {
        Processor processor = null;

        // allow any custom logic before we create the processor
        preCreateProcessor();

        // resolve properties before we create the processor
        ProcessorDefinitionHelper.resolvePropertyPlaceholders(routeContext.getCamelContext(), this);

        // resolve constant fields (eg Exchange.FILE_NAME)
        ProcessorDefinitionHelper.resolveKnownConstantFields(this);

        // also resolve properties and constant fields on embedded expressions
        ProcessorDefinition<?> me = (ProcessorDefinition<?>) this;
        if (me instanceof ExpressionNode) {
            ExpressionNode exp = (ExpressionNode) me;
            ExpressionDefinition expressionDefinition = exp.getExpression();
            if (expressionDefinition != null) {
                // resolve properties before we create the processor
                ProcessorDefinitionHelper.resolvePropertyPlaceholders(routeContext.getCamelContext(), expressionDefinition);

                // resolve constant fields (eg Exchange.FILE_NAME)
                ProcessorDefinitionHelper.resolveKnownConstantFields(expressionDefinition);
            }
        }

        // at first use custom factory
        if (routeContext.getCamelContext().getProcessorFactory() != null) {
            processor = routeContext.getCamelContext().getProcessorFactory().createProcessor(routeContext, this);
        }
        // fallback to default implementation if factory did not create the processor
        if (processor == null) {
            processor = createProcessor(routeContext);
        }

        // inject id
        if (processor instanceof IdAware) {
            String id = this.idOrCreate(routeContext.getCamelContext().getNodeIdFactory());
            ((IdAware) processor).setId(id);
        }

        if (processor == null) {
            // no processor to make
            return null;
        }
        return wrapProcessor(routeContext, processor);
    }

    /**
     * Strategy to execute any custom logic before the {@link Processor} is created.
     */
    protected void preCreateProcessor() {
        // noop
    }

    /**
     * Strategy for children to do any custom configuration
     *
     * @param output the child to be added as output to this
     */
    public void configureChild(ProcessorDefinition<?> output) {
        // noop
    }

    // Fluent API
    // -------------------------------------------------------------------------

    /**
     * Adds a placeholder for the given option
     * <p/>
     * Requires using the {@link org.apache.camel.component.properties.PropertiesComponent}
     *
     * @param option  the name of the option
     * @param key     the placeholder key
     * @return the builder
     */
    public Type placeholder(String option, String key) {
        QName name = new QName(Constants.PLACEHOLDER_QNAME, option);
        return attribute(name, key);
    }

    /**
     * Adds an optional attribute
     *
     * @param name    the name of the attribute
     * @param value   the value
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type attribute(QName name, Object value) {
        if (otherAttributes == null) {
            otherAttributes = new HashMap<QName, Object>();
        }
        otherAttributes.put(name, value);
        return (Type) this;
    }

    /**
     * Sends the exchange to the given endpoint
     *
     * @param uri  the endpoint to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(String uri) {
        addOutput(new ToDefinition(uri));
        return (Type) this;
    }   
    
    /**
     * Sends the exchange to the given endpoint
     *
     * @param uri  the String formatted endpoint uri to send to
     * @param args arguments for the string formatting of the uri
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type toF(String uri, Object... args) {
        addOutput(new ToDefinition(String.format(uri, args)));
        return (Type) this;
    }

    /**
     * Sends the exchange to the given endpoint
     *
     * @param endpoint  the endpoint to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(Endpoint endpoint) {
        addOutput(new ToDefinition(endpoint));
        return (Type) this;
    }
    
    /**
     * Sends the exchange with certain exchange pattern to the given endpoint
     * <p/>
     * Notice the existing MEP is preserved
     *
     * @param pattern the pattern to use for the message exchange
     * @param uri  the endpoint to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(ExchangePattern pattern, String uri) {
        addOutput(new ToDefinition(uri, pattern));
        return (Type) this;
    }   

    /**
     * Sends the exchange with certain exchange pattern to the given endpoint
     * <p/>
     * Notice the existing MEP is preserved
     *
     * @param pattern the pattern to use for the message exchange
     * @param endpoint  the endpoint to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(ExchangePattern pattern, Endpoint endpoint) {
        addOutput(new ToDefinition(endpoint, pattern));
        return (Type) this;
    }

    /**
     * Sends the exchange to a list of endpoints
     *
     * @param uris  list of endpoints to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(String... uris) {
        for (String uri : uris) {
            addOutput(new ToDefinition(uri));
        }
        return (Type) this;
    }

    /**
     * Sends the exchange to a list of endpoints
     *
     * @param endpoints  list of endpoints to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(Endpoint... endpoints) {
        for (Endpoint endpoint : endpoints) {
            addOutput(new ToDefinition(endpoint));
        }
        return (Type) this;
    }

    /**
     * Sends the exchange to a list of endpoints
     *
     * @param endpoints  list of endpoints to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(Iterable<Endpoint> endpoints) {
        for (Endpoint endpoint : endpoints) {
            addOutput(new ToDefinition(endpoint));
        }
        return (Type) this;
    }

    /**
     * Sends the exchange to a list of endpoints
     * <p/>
     * Notice the existing MEP is preserved
     *
     * @param pattern the pattern to use for the message exchanges
     * @param uris  list of endpoints to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(ExchangePattern pattern, String... uris) {
        for (String uri : uris) {
            addOutput(new ToDefinition(uri, pattern));
        }
        return (Type) this;
    }

    /**
     * Sends the exchange to a list of endpoints
     * <p/>
     * Notice the existing MEP is preserved
     *
     * @param pattern the pattern to use for the message exchanges
     * @param endpoints  list of endpoints to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(ExchangePattern pattern, Endpoint... endpoints) {
        for (Endpoint endpoint : endpoints) {
            addOutput(new ToDefinition(endpoint, pattern));
        }
        return (Type) this;
    }

    /**
     * Sends the exchange to a list of endpoints
     *
     * @param pattern the pattern to use for the message exchanges
     * @param endpoints  list of endpoints to send to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type to(ExchangePattern pattern, Iterable<Endpoint> endpoints) {
        for (Endpoint endpoint : endpoints) {
            addOutput(new ToDefinition(endpoint, pattern));
        }
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/exchange-pattern.html">ExchangePattern:</a>
     * set the {@link ExchangePattern} into the {@link Exchange}.
     * <p/>
     * The pattern set on the {@link Exchange} will
     *
     * @param exchangePattern  instance of {@link ExchangePattern}
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type setExchangePattern(ExchangePattern exchangePattern) {
        addOutput(new SetExchangePatternDefinition(exchangePattern));
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/exchange-pattern.html">ExchangePattern:</a>
     * set the exchange's ExchangePattern {@link ExchangePattern} to be InOnly
     *
     * @return the builder
     * @deprecated use {@link #setExchangePattern(org.apache.camel.ExchangePattern)} instead
     */
    @Deprecated
    public Type inOnly() {
        return setExchangePattern(ExchangePattern.InOnly);
    }

    /**
     * Sends the message to the given endpoint using an
     * <a href="http://camel.apache.org/event-message.html">Event Message</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOnly exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param uri The endpoint uri which is used for sending the exchange
     * @return the builder
     */
    public Type inOnly(String uri) {
        return to(ExchangePattern.InOnly, uri);
    }

    /**
     * Sends the message to the given endpoint using an
     * <a href="http://camel.apache.org/event-message.html">Event Message</a> or 
     * <a href="http://camel.apache.org/exchange-pattern.html">InOnly exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param endpoint The endpoint which is used for sending the exchange
     * @return the builder
     */
    public Type inOnly(Endpoint endpoint) {
        return to(ExchangePattern.InOnly, endpoint);
    }

    /**
     * Sends the message to the given endpoints using an
     * <a href="http://camel.apache.org/event-message.html">Event Message</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOnly exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param uris  list of endpoints to send to
     * @return the builder
     */
    public Type inOnly(String... uris) {
        return to(ExchangePattern.InOnly, uris);
    }

    /**
     * Sends the message to the given endpoints using an
     * <a href="http://camel.apache.org/event-message.html">Event Message</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOnly exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param endpoints  list of endpoints to send to
     * @return the builder
     */
    public Type inOnly(Endpoint... endpoints) {
        return to(ExchangePattern.InOnly, endpoints);
    }

    /**
     * Sends the message to the given endpoints using an
     * <a href="http://camel.apache.org/event-message.html">Event Message</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOnly exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param endpoints  list of endpoints to send to
     * @return the builder
     */
    public Type inOnly(Iterable<Endpoint> endpoints) {
        return to(ExchangePattern.InOnly, endpoints);
    }

    /**
     * <a href="http://camel.apache.org/exchange-pattern.html">ExchangePattern:</a>
     * set the exchange's ExchangePattern {@link ExchangePattern} to be InOut
     *
     * @return the builder
     * @deprecated use {@link #setExchangePattern(org.apache.camel.ExchangePattern)} instead
     */
    @Deprecated
    public Type inOut() {
        return setExchangePattern(ExchangePattern.InOut);
    }

    /**
     * Sends the message to the given endpoint using an
     * <a href="http://camel.apache.org/request-reply.html">Request Reply</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOut exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param uri The endpoint uri which is used for sending the exchange
     * @return the builder
     */
    public Type inOut(String uri) {
        return to(ExchangePattern.InOut, uri);
    }

    /**
     * Sends the message to the given endpoint using an
     * <a href="http://camel.apache.org/request-reply.html">Request Reply</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOut exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param endpoint The endpoint which is used for sending the exchange
     * @return the builder
     */
    public Type inOut(Endpoint endpoint) {
        return to(ExchangePattern.InOut, endpoint);
    }

    /**
     * Sends the message to the given endpoints using an
     * <a href="http://camel.apache.org/request-reply.html">Request Reply</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOut exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param uris  list of endpoints to send to
     * @return the builder
     */
    public Type inOut(String... uris) {
        return to(ExchangePattern.InOut, uris);
    }

    /**
     * Sends the message to the given endpoints using an
     * <a href="http://camel.apache.org/request-reply.html">Request Reply</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOut exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param endpoints  list of endpoints to send to
     * @return the builder
     */
    public Type inOut(Endpoint... endpoints) {
        return to(ExchangePattern.InOut, endpoints);
    }

    /**
     * Sends the message to the given endpoints using an
     * <a href="http://camel.apache.org/request-reply.html">Request Reply</a> or
     * <a href="http://camel.apache.org/exchange-pattern.html">InOut exchange pattern</a>
     * <p/>
     * Notice the existing MEP is restored after the message has been sent to the given endpoint.
     *
     * @param endpoints  list of endpoints to send to
     * @return the builder
     */
    public Type inOut(Iterable<Endpoint> endpoints) {
        return to(ExchangePattern.InOut, endpoints);
    }

    /**
     * Sets the id of this node.
     * <p/>
     * <b>Important:</b> If you want to set the id of the route,
     * then you <b>must</b> use {@link #routeId(String)} instead.
     *
     * @param id  the id
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type id(String id) {
        if (isOutputSupported() && getOutputs().isEmpty()) {
            // set id on this
            setId(id);
        } else {
            
            // set it on last output as this is what the user means to do
            // for Block(s) with non empty getOutputs() the id probably refers
            //  to the last definition in the current Block
            List<ProcessorDefinition<?>> outputs = getOutputs();
            if (!blocks.isEmpty()) {
                if (blocks.getLast() instanceof ProcessorDefinition) {
                    ProcessorDefinition<?> block = (ProcessorDefinition<?>)blocks.getLast();
                    if (!block.getOutputs().isEmpty()) {
                        outputs = block.getOutputs();
                    }
                }
            }
            if (!getOutputs().isEmpty()) {
                outputs.get(outputs.size() - 1).setId(id);
            } else {
                // the output could be empty
                setId(id);
            }
        }

        return (Type) this;
    }

    /**
     * Set the route id for this route.
     * <p/>
     * <b>Important: </b> Each route in the same {@link org.apache.camel.CamelContext} must have an <b>unique</b> route id.
     * If you use the API from {@link org.apache.camel.CamelContext} or {@link ModelCamelContext} to add routes, then any
     * new routes which has a route id that matches an old route, then the old route is replaced by the new route.
     *
     * @param id  the route id, should be unique
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type routeId(String id) {
        ProcessorDefinition<?> def = this;

        RouteDefinition route = ProcessorDefinitionHelper.getRoute(def);
        if (route != null) {
            route.setId(id);
        }

        return (Type) this;
    }

    /**
     * Set the route description for this route
     *
     * @param description the route description
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type routeDescription(String description) {
        ProcessorDefinition<?> def = this;

        RouteDefinition route = ProcessorDefinitionHelper.getRoute(def);
        if (route != null) {
            DescriptionDefinition desc = new DescriptionDefinition();
            desc.setText(description);
            route.setDescription(desc);
        }

        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/multicast.html">Multicast EIP:</a>
     * Multicasts messages to all its child outputs; so that each processor and
     * destination gets a copy of the original message to avoid the processors
     * interfering with each other.
     *
     * @return the builder
     */
    public MulticastDefinition multicast() {
        MulticastDefinition answer = new MulticastDefinition();
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/multicast.html">Multicast EIP:</a>
     * Multicasts messages to all its child outputs; so that each processor and
     * destination gets a copy of the original message to avoid the processors
     * interfering with each other.
     *
     * @param aggregationStrategy the strategy used to aggregate responses for
     *          every part
     * @param parallelProcessing if is <tt>true</tt> camel will fork thread to call the endpoint producer
     * @return the builder
     */
    public MulticastDefinition multicast(AggregationStrategy aggregationStrategy, boolean parallelProcessing) {
        MulticastDefinition answer = new MulticastDefinition();
        addOutput(answer);
        answer.setAggregationStrategy(aggregationStrategy);
        answer.setParallelProcessing(parallelProcessing);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/multicast.html">Multicast EIP:</a>
     * Multicasts messages to all its child outputs; so that each processor and
     * destination gets a copy of the original message to avoid the processors
     * interfering with each other.
     *
     * @param aggregationStrategy the strategy used to aggregate responses for every part
     * @return the builder
     */
    public MulticastDefinition multicast(AggregationStrategy aggregationStrategy) {
        MulticastDefinition answer = new MulticastDefinition();
        addOutput(answer);
        answer.setAggregationStrategy(aggregationStrategy);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/pipes-nd-filters.html">Pipes and Filters EIP:</a>
     * Creates a {@link Pipeline} so that the message
     * will get processed by each endpoint in turn and for request/response the
     * output of one endpoint will be the input of the next endpoint
     *
     * @return the builder
     */
    public PipelineDefinition pipeline() {
        PipelineDefinition answer = new PipelineDefinition();
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/pipes-nd-filters.html">Pipes and Filters EIP:</a>
     * Creates a {@link Pipeline} of the list of endpoints so that the message
     * will get processed by each endpoint in turn and for request/response the
     * output of one endpoint will be the input of the next endpoint
     *
     * @param uris  list of endpoints
     * @return the builder
     */
    public Type pipeline(String... uris) {
        return to(uris);
    }

    /**
     * <a href="http://camel.apache.org/pipes-nd-filters.html">Pipes and Filters EIP:</a>
     * Creates a {@link Pipeline} of the list of endpoints so that the message
     * will get processed by each endpoint in turn and for request/response the
     * output of one endpoint will be the input of the next endpoint
     *
     * @param endpoints  list of endpoints
     * @return the builder
     */
    public Type pipeline(Endpoint... endpoints) {
        return to(endpoints);
    }

    /**
     * <a href="http://camel.apache.org/pipes-nd-filters.html">Pipes and Filters EIP:</a>
     * Creates a {@link Pipeline} of the list of endpoints so that the message
     * will get processed by each endpoint in turn and for request/response the
     * output of one endpoint will be the input of the next endpoint
     *
     * @param endpoints  list of endpoints
     * @return the builder
     */
    public Type pipeline(Collection<Endpoint> endpoints) {
        return to(endpoints);
    }

    /**
     * Continues processing the {@link org.apache.camel.Exchange} using asynchronous routing engine.
     *
     * @return the builder
     */
    public ThreadsDefinition threads() {
        ThreadsDefinition answer = new ThreadsDefinition();
        addOutput(answer);
        return answer;
    }

    /**
     * Continues processing the {@link org.apache.camel.Exchange} using asynchronous routing engine.
     *
     * @param poolSize the core pool size
     * @return the builder
     */
    public ThreadsDefinition threads(int poolSize) {
        ThreadsDefinition answer = new ThreadsDefinition();
        answer.setPoolSize(poolSize);
        addOutput(answer);
        return answer;
    }

    /**
     * Continues processing the {@link org.apache.camel.Exchange} using asynchronous routing engine.
     *
     * @param poolSize    the core pool size
     * @param maxPoolSize the maximum pool size
     * @return the builder
     */
    public ThreadsDefinition threads(int poolSize, int maxPoolSize) {
        ThreadsDefinition answer = new ThreadsDefinition();
        answer.setPoolSize(poolSize);
        answer.setMaxPoolSize(maxPoolSize);
        addOutput(answer);
        return answer;
    }
    
    /**
     * Continues processing the {@link org.apache.camel.Exchange} using asynchronous routing engine.
     *
     * @param poolSize    the core pool size
     * @param maxPoolSize the maximum pool size
     * @param threadName the thread pool name
     * @return the builder
     */
    public ThreadsDefinition threads(int poolSize, int maxPoolSize, String threadName) {
        ThreadsDefinition answer = new ThreadsDefinition();
        answer.setPoolSize(poolSize);
        answer.setMaxPoolSize(maxPoolSize);
        answer.setThreadName(threadName);
        addOutput(answer);
        return answer;
    }

    /**
     * Wraps the sub route using AOP allowing you to do before and after work (AOP around).
     *
     * @return the builder
     * @deprecated to be removed in the near future. Instead you can use interceptors or processors to do AOP with Camel.
     */
    @Deprecated
    public AOPDefinition aop() {
        AOPDefinition answer = new AOPDefinition();
        addOutput(answer);
        return answer;
    }

    /**
     * Ends the current block
     *
     * @return the builder
     */
    public ProcessorDefinition<?> end() {
        // must do this ugly cast to avoid compiler error on AIX/HP-UX
        ProcessorDefinition<?> defn = (ProcessorDefinition<?>) this;
        
        // when using choice .. when .. otherwise - doTry .. doCatch .. doFinally we should always
        // end the choice/try definition to avoid having to use 2 x end() in the route
        // this is counter intuitive for end users
        // TODO (camel-3.0): this should be done inside of TryDefinition or even better
        //  in Block(s) in general, but the api needs to be revisited for that.
        if (defn instanceof TryDefinition || defn instanceof ChoiceDefinition) {
            popBlock();
        }

        if (blocks.isEmpty()) {
            if (parent == null) {
                return this.endParent();
            }
            return parent.endParent();
        }
        popBlock();
        return this.endParent();
    }

    /**
     * Strategy to allow {@link ProcessorDefinition}s to have special logic when using end() in the DSL
     * to return back to the intended parent.
     * <p/>
     * For example a content based router we return back to the {@link ChoiceDefinition} when we end()
     * from a {@link WhenDefinition}.
     *
     * @return the end
     */
    public ProcessorDefinition<?> endParent() {
        return this;
    }

    /**
     * Ends the current block and returns back to the {@link ChoiceDefinition choice()} DSL.
     * <p/>
     * <b>Important:</b> If you want to end the entire choice block, then use {@link #end()} instead.
     * The purpose of {@link #endChoice()} is to return <i>control</i> back to the {@link ChoiceDefinition choice()} DSL,
     * so you can add subsequent <tt>when</tt> and <tt>otherwise</tt> to the choice. There can be situations where
     * you would need to use {@link #endChoice()} often when you add additional EIPs inside the <tt>when</tt>'s, and
     * the DSL <t>looses</t> scope when using a regular {@link #end()}, and you would need to use this {@link #endChoice()}
     * to return back the scope to the {@link ChoiceDefinition choice()} DSL.
     * <p/>
     * For more details and examples see also this FAQ:
     * <a href="http://camel.apache.org/why-can-i-not-use-when-or-otherwise-in-a-java-camel-route.html">Why can I not use when or otherwise in a Java Camel route </a>.
     *
     * @return the choice builder
     */
    public ChoiceDefinition endChoice() {
        // are we nested choice?
        ProcessorDefinition<?> def = this;
        if (def.getParent() instanceof WhenDefinition) {
            return (ChoiceDefinition) def.getParent().getParent();
        }

        // are we already a choice?
        if (def instanceof ChoiceDefinition) {
            return (ChoiceDefinition) def;
        }

        // okay end this and get back to the choice
        def = end();
        if (def instanceof WhenDefinition) {
            return (ChoiceDefinition) def.getParent();
        } else if (def instanceof OtherwiseDefinition) {
            return (ChoiceDefinition) def.getParent();
        } else {
            return (ChoiceDefinition) def;
        }
    }

    /**
     * Ends the current block and returns back to the {@link org.apache.camel.model.rest.RestDefinition rest()} DSL.
     *
     * @return the builder
     */
    public RestDefinition endRest() {
        ProcessorDefinition<?> def = this;

        RouteDefinition route = ProcessorDefinitionHelper.getRoute(def);
        if (route != null) {
            return route.getRestDefinition();
        }

        throw new IllegalArgumentException("Cannot find RouteDefinition to allow endRest");
    }

    /**
     * Ends the current block and returns back to the {@link TryDefinition doTry()} DSL.
     *
     * @return the builder
     */
    public TryDefinition endDoTry() {
        ProcessorDefinition<?> def = this;

        // are we already a try?
        if (def instanceof TryDefinition) {
            return (TryDefinition) def;
        }

        // okay end this and get back to the try
        def = end();
        return (TryDefinition) def;
    }

    /**
     * <a href="http://camel.apache.org/idempotent-consumer.html">Idempotent consumer EIP:</a>
     * Creates an {@link org.apache.camel.processor.idempotent.IdempotentConsumer IdempotentConsumer}
     * to avoid duplicate messages
     *
     * @param messageIdExpression  expression to test of duplicate messages
     * @return the builder
     */
    public IdempotentConsumerDefinition idempotentConsumer(Expression messageIdExpression) {
        IdempotentConsumerDefinition answer = new IdempotentConsumerDefinition();
        answer.setExpression(ExpressionNodeHelper.toExpressionDefinition(messageIdExpression));
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/idempotent-consumer.html">Idempotent consumer EIP:</a>
     * Creates an {@link org.apache.camel.processor.idempotent.IdempotentConsumer IdempotentConsumer}
     * to avoid duplicate messages
     *
     * @param messageIdExpression  expression to test of duplicate messages
     * @param idempotentRepository  the repository to use for duplicate check
     * @return the builder
     */
    public IdempotentConsumerDefinition idempotentConsumer(Expression messageIdExpression, IdempotentRepository<?> idempotentRepository) {
        IdempotentConsumerDefinition answer = new IdempotentConsumerDefinition(messageIdExpression, idempotentRepository);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/idempotent-consumer.html">Idempotent consumer EIP:</a>
     * Creates an {@link org.apache.camel.processor.idempotent.IdempotentConsumer IdempotentConsumer}
     * to avoid duplicate messages
     *
     * @param idempotentRepository the repository to use for duplicate check
     * @return the builder used to create the expression
     * @deprecated will be removed in Camel 3.0. Instead use any of the other methods
     */
    @Deprecated
    public ExpressionClause<IdempotentConsumerDefinition> idempotentConsumer(IdempotentRepository<?> idempotentRepository) {
        IdempotentConsumerDefinition answer = new IdempotentConsumerDefinition();
        answer.setMessageIdRepository(idempotentRepository);
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }

    /**
     * <a href="http://camel.apache.org/message-filter.html">Message Filter EIP:</a>
     * Creates a predicate expression which only if it is <tt>true</tt> then the
     * exchange is forwarded to the destination
     *
     * @return the clause used to create the filter expression
     */
    public ExpressionClause<? extends FilterDefinition> filter() {
        FilterDefinition filter = new FilterDefinition();
        addOutput(filter);
        return ExpressionClause.createAndSetExpression(filter);
    }

    /**
     * <a href="http://camel.apache.org/message-filter.html">Message Filter EIP:</a>
     * Creates a predicate which is applied and only if it is <tt>true</tt> then the
     * exchange is forwarded to the destination
     *
     * @param predicate  predicate to use
     * @return the builder 
     */
    public FilterDefinition filter(Predicate predicate) {
        FilterDefinition filter = new FilterDefinition(predicate);
        addOutput(filter);
        return filter;
    }

    /**
     * <a href="http://camel.apache.org/message-filter.html">Message Filter EIP:</a>
     * Creates a predicate expression which only if it is <tt>true</tt> then the
     * exchange is forwarded to the destination
     *
     * @param expression  the predicate expression to use
     * @return the builder
     */
    public FilterDefinition filter(ExpressionDefinition expression) {
        FilterDefinition filter = new FilterDefinition();
        filter.setExpression(expression);
        addOutput(filter);
        return filter;
    }

    /**
     * <a href="http://camel.apache.org/message-filter.html">Message Filter EIP:</a>
     * Creates a predicate language expression which only if it is <tt>true</tt> then the
     * exchange is forwarded to the destination
     *
     * @param language     language for expression
     * @param expression   the expression
     * @return the builder
     */
    public FilterDefinition filter(String language, String expression) {
        return filter(new LanguageExpression(language, expression));
    }
    
    /**
     * Creates a validation expression which only if it is <tt>true</tt> then the
     * exchange is forwarded to the destination.
     * Otherwise a {@link org.apache.camel.processor.validation.PredicateValidationException} is thrown.
     *
     * @param expression  the expression
     * @return the builder
     */
    public ValidateDefinition validate(Expression expression) {
        ValidateDefinition answer = new ValidateDefinition();
        answer.setExpression(ExpressionNodeHelper.toExpressionDefinition(expression));
        addOutput(answer);
        return answer;
    }

    /**
     * Creates a validation expression which only if it is <tt>true</tt> then the
     * exchange is forwarded to the destination.
     * Otherwise a {@link org.apache.camel.processor.validation.PredicateValidationException} is thrown.
     *
     * @param predicate  the predicate
     * @return the builder
     */
    public ValidateDefinition validate(Predicate predicate) {
        ValidateDefinition answer = new ValidateDefinition();
        answer.setExpression(ExpressionNodeHelper.toExpressionDefinition(predicate));
        addOutput(answer);
        return answer;
    }

    /**
     * Creates a validation expression which only if it is <tt>true</tt> then the
     * exchange is forwarded to the destination.
     * Otherwise a {@link org.apache.camel.processor.validation.PredicateValidationException} is thrown.
     *
     * @return the builder
     */
    public ExpressionClause<ValidateDefinition> validate() {
        ValidateDefinition answer = new ValidateDefinition();
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }
    /**
     * <a href="http://camel.apache.org/load-balancer.html">Load Balancer EIP:</a>
     * Creates a loadbalance
     *
     * @return  the builder
     */
    public LoadBalanceDefinition loadBalance() {
        LoadBalanceDefinition answer = new LoadBalanceDefinition();
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/load-balancer.html">Load Balancer EIP:</a>
     * Creates a loadbalance
     *
     * @param loadBalancer a custom load balancer to use
     * @return  the builder
     */
    public LoadBalanceDefinition loadBalance(LoadBalancer loadBalancer) {
        LoadBalanceDefinition answer = new LoadBalanceDefinition();
        addOutput(answer);
        return answer.loadBalance(loadBalancer);
    }

    /**
     * Creates a log message to be logged at INFO level.
     *
     * @param message the log message, (you can use {@link org.apache.camel.language.simple.SimpleLanguage} syntax)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type log(String message) {
        LogDefinition answer = new LogDefinition(message);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Creates a log message to be logged at the given level.
     *
     * @param loggingLevel the logging level to use
     * @param message the log message, (you can use {@link org.apache.camel.language.simple.SimpleLanguage} syntax)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type log(LoggingLevel loggingLevel, String message) {
        LogDefinition answer = new LogDefinition(message);
        answer.setLoggingLevel(loggingLevel);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Creates a log message to be logged at the given level and name.
     *
     * @param loggingLevel the logging level to use
     * @param logName the log name to use
     * @param message the log message, (you can use {@link org.apache.camel.language.simple.SimpleLanguage} syntax)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type log(LoggingLevel loggingLevel, String logName, String message) {
        LogDefinition answer = new LogDefinition(message);
        answer.setLoggingLevel(loggingLevel);
        answer.setLogName(logName);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Creates a log message to be logged at the given level using provided logger.
     *
     * @param loggingLevel the logging level to use
     * @param logger the logger to use
     * @param message the log message, (you can use {@link org.apache.camel.language.simple.SimpleLanguage} syntax)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type log(LoggingLevel loggingLevel, Logger logger, String message) {
        LogDefinition answer = new LogDefinition(message);
        answer.setLoggingLevel(loggingLevel);
        answer.setLogger(logger);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Creates a log message to be logged at the given level and name.
     *
     *
     * @param loggingLevel the logging level to use
     * @param logName the log name to use
     * @param marker  log marker name
     * @param message the log message, (you can use {@link org.apache.camel.language.simple.SimpleLanguage} syntax)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type log(LoggingLevel loggingLevel, String logName, String marker, String message) {
        LogDefinition answer = new LogDefinition(message);
        answer.setLoggingLevel(loggingLevel);
        answer.setLogName(logName);
        answer.setMarker(marker);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Creates a log message to be logged at the given level using provided logger.
     *
     *
     * @param loggingLevel the logging level to use
     * @param logger the logger to use
     * @param marker  log marker name
     * @param message the log message, (you can use {@link org.apache.camel.language.simple.SimpleLanguage} syntax)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type log(LoggingLevel loggingLevel, Logger logger, String marker, String message) {
        LogDefinition answer = new LogDefinition(message);
        answer.setLoggingLevel(loggingLevel);
        answer.setLogger(logger);
        answer.setMarker(marker);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/content-based-router.html">Content Based Router EIP:</a>
     * Creates a choice of one or more predicates with an otherwise clause
     *
     * @return the builder for a choice expression
     */
    public ChoiceDefinition choice() {
        ChoiceDefinition answer = new ChoiceDefinition();
        addOutput(answer);
        return answer;
    }

    /**
     * Creates a try/catch block
     *
     * @return the builder for a tryBlock expression
     */
    public TryDefinition doTry() {
        TryDefinition answer = new TryDefinition();
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/recipient-list.html">Recipient List EIP:</a>
     * Creates a dynamic recipient list allowing you to route messages to a number of dynamically specified recipients.
     * <p/>
     * Will use comma as default delimiter.
     *
     * @param recipients expression to decide the destinations
     * @return the builder
     */
    public RecipientListDefinition<Type> recipientList(Expression recipients) {
        RecipientListDefinition<Type> answer = new RecipientListDefinition<Type>(recipients);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/recipient-list.html">Recipient List EIP:</a>
     * Creates a dynamic recipient list allowing you to route messages to a number of dynamically specified recipients
     *
     * @param recipients expression to decide the destinations
     * @param delimiter  a custom delimiter to use
     * @return the builder
     */
    public RecipientListDefinition<Type> recipientList(Expression recipients, String delimiter) {
        RecipientListDefinition<Type> answer = new RecipientListDefinition<Type>(recipients);
        answer.setDelimiter(delimiter);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/recipient-list.html">Recipient List EIP:</a>
     * Creates a dynamic recipient list allowing you to route messages to a number of dynamically specified recipients
     *
     * @param delimiter  a custom delimiter to use
     * @return the builder
     */
    public ExpressionClause<RecipientListDefinition<Type>> recipientList(String delimiter) {
        RecipientListDefinition<Type> answer = new RecipientListDefinition<Type>();
        answer.setDelimiter(delimiter);
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }

    /**
     * <a href="http://camel.apache.org/recipient-list.html">Recipient List EIP:</a>
     * Creates a dynamic recipient list allowing you to route messages to a number of dynamically specified recipients
     *
     * @return the expression clause to configure the expression to decide the destinations
     */
    public ExpressionClause<RecipientListDefinition<Type>> recipientList() {
        RecipientListDefinition<Type> answer = new RecipientListDefinition<Type>();
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }

    /**
     * <a href="http://camel.apache.org/routing-slip.html">Routing Slip EIP:</a>
     * Creates a routing slip allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * The route slip will be evaluated <i>once</i>, use {@link #dynamicRouter()} if you need even more dynamic routing.
     *
     * @param header  is the header that the {@link org.apache.camel.processor.RoutingSlip RoutingSlip}
     *                class will look in for the list of URIs to route the message to.
     * @param uriDelimiter  is the delimiter that will be used to split up
     *                      the list of URIs in the routing slip.
     * @return the builder
     * @deprecated prefer to use {@link #routingSlip(org.apache.camel.Expression, String)} instead
     */
    @Deprecated
    public Type routingSlip(String header, String uriDelimiter) {
        RoutingSlipDefinition<Type> answer = new RoutingSlipDefinition<Type>(header, uriDelimiter);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/routing-slip.html">Routing Slip EIP:</a>
     * Creates a routing slip allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * The list of URIs will be split based on the default delimiter {@link RoutingSlipDefinition#DEFAULT_DELIMITER}
     * <p/>
     * The route slip will be evaluated <i>once</i>, use {@link #dynamicRouter()} if you need even more dynamic routing.
     *
     * @param header  is the header that the {@link org.apache.camel.processor.RoutingSlip RoutingSlip}
     *                class will look in for the list of URIs to route the message to.
     * @return the builder
     * @deprecated prefer to use {@link #routingSlip(org.apache.camel.Expression)} instead
     */
    @Deprecated
    public Type routingSlip(String header) {
        RoutingSlipDefinition<Type> answer = new RoutingSlipDefinition<Type>(header);
        addOutput(answer);
        return (Type) this;
    }
    
    /**
     * <a href="http://camel.apache.org/routing-slip.html">Routing Slip EIP:</a>
     * Creates a routing slip allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * The route slip will be evaluated <i>once</i>, use {@link #dynamicRouter()} if you need even more dynamic routing.
     *
     * @param header  is the header that the {@link org.apache.camel.processor.RoutingSlip RoutingSlip}
     *                class will look in for the list of URIs to route the message to.
     * @param uriDelimiter  is the delimiter that will be used to split up
     *                      the list of URIs in the routing slip.
     * @param ignoreInvalidEndpoints if this parameter is true, routingSlip will ignore the endpoints which
     *                               cannot be resolved or a producer cannot be created or started 
     * @return the builder
     * @deprecated prefer to use {@link #routingSlip()} instead
     */
    @Deprecated
    public Type routingSlip(String header, String uriDelimiter, boolean ignoreInvalidEndpoints) {
        RoutingSlipDefinition<Type> answer = new RoutingSlipDefinition<Type>(header, uriDelimiter);
        answer.setIgnoreInvalidEndpoints(ignoreInvalidEndpoints);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/routing-slip.html">Routing Slip EIP:</a>
     * Creates a routing slip allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * The list of URIs will be split based on the default delimiter {@link RoutingSlipDefinition#DEFAULT_DELIMITER}
     * <p/>
     * The route slip will be evaluated <i>once</i>, use {@link #dynamicRouter()} if you need even more dynamic routing.
     *
     * @param header  is the header that the {@link org.apache.camel.processor.RoutingSlip RoutingSlip}
     *                class will look in for the list of URIs to route the message to.
     * @param ignoreInvalidEndpoints if this parameter is true, routingSlip will ignore the endpoints which
     *                               cannot be resolved or a producer cannot be created or started 
     * @return the builder
     * @deprecated prefer to use {@link #routingSlip()} instead
     */
    @Deprecated
    public Type routingSlip(String header, boolean ignoreInvalidEndpoints) {
        RoutingSlipDefinition<Type> answer = new RoutingSlipDefinition<Type>(header);
        answer.setIgnoreInvalidEndpoints(ignoreInvalidEndpoints);
        addOutput(answer);
        return (Type) this;
    }
    
    /**
     * <a href="http://camel.apache.org/routing-slip.html">Routing Slip EIP:</a>
     * Creates a routing slip allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * The route slip will be evaluated <i>once</i>, use {@link #dynamicRouter()} if you need even more dynamic routing.
     *
     * @param expression  to decide the destinations
     * @param uriDelimiter  is the delimiter that will be used to split up
     *                      the list of URIs in the routing slip.
     * @return the builder
     */
    public RoutingSlipDefinition<Type> routingSlip(Expression expression, String uriDelimiter) {
        RoutingSlipDefinition<Type> answer = new RoutingSlipDefinition<Type>(expression, uriDelimiter);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/routing-slip.html">Routing Slip EIP:</a>
     * Creates a routing slip allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * The list of URIs will be split based on the default delimiter {@link RoutingSlipDefinition#DEFAULT_DELIMITER}
     * <p/>
     * The route slip will be evaluated <i>once</i>, use {@link #dynamicRouter()} if you need even more dynamic routing.
     *
     * @param expression  to decide the destinations
     * @return the builder
     */
    public RoutingSlipDefinition<Type> routingSlip(Expression expression) {
        RoutingSlipDefinition<Type> answer = new RoutingSlipDefinition<Type>(expression);
        addOutput(answer);
        return answer;
    }
    
    /**
     * <a href="http://camel.apache.org/routing-slip.html">Routing Slip EIP:</a>
     * Creates a routing slip allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * The list of URIs will be split based on the default delimiter {@link RoutingSlipDefinition#DEFAULT_DELIMITER}
     * <p/>
     * The route slip will be evaluated <i>once</i>, use {@link #dynamicRouter()} if you need even more dynamic routing.
     *
     * @return the expression clause to configure the expression to decide the destinations
     */
    public ExpressionClause<RoutingSlipDefinition<Type>> routingSlip() {
        RoutingSlipDefinition<Type> answer = new RoutingSlipDefinition<Type>();
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }

    /**
     * <a href="http://camel.apache.org/dynamic-router.html">Dynamic Router EIP:</a>
     * Creates a dynamic router allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * <br/><b>Important:</b> The expression will be invoked repeatedly until it returns <tt>null</tt>, so be sure it does that,
     * otherwise it will be invoked endlessly.
     *
     * @param expression  to decide the destinations, which will be invoked repeatedly
     *                    until it evaluates <tt>null</tt> to indicate no more destinations.
     * @return the builder
     */
    public DynamicRouterDefinition<Type> dynamicRouter(Expression expression) {
        DynamicRouterDefinition<Type> answer = new DynamicRouterDefinition<Type>(expression);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/dynamic-router.html">Dynamic Router EIP:</a>
     * Creates a dynamic router allowing you to route a message consecutively through a series of processing
     * steps where the sequence of steps is not known at design time and can vary for each message.
     * <p/>
     * <br/><b>Important:</b> The expression will be invoked repeatedly until it returns <tt>null</tt>, so be sure it does that,
     * otherwise it will be invoked endlessly.
     *
     * @return the expression clause to configure the expression to decide the destinations,
     * which will be invoked repeatedly until it evaluates <tt>null</tt> to indicate no more destinations.
     */
    public ExpressionClause<DynamicRouterDefinition<Type>> dynamicRouter() {
        DynamicRouterDefinition<Type> answer = new DynamicRouterDefinition<Type>();
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }

    /**
     * <a href="http://camel.apache.org/sampling.html">Sampling Throttler</a>
     * Creates a sampling throttler allowing you to extract a sample of
     * exchanges from the traffic on a route. It is configured with a sampling
     * period, during which only a single exchange is allowed to pass through.
     * All other exchanges will be stopped.
     * <p/>
     * Default period is one second.
     *
     * @return the builder
     */
    public SamplingDefinition sample() {
        return sample(1, TimeUnit.SECONDS);
    }

    /**
     * <a href="http://camel.apache.org/sampling.html">Sampling Throttler</a>
     * Creates a sampling throttler allowing you to extract a sample of exchanges
     * from the traffic through a route. It is configured with a sampling period
     * during which only a single exchange is allowed to pass through.
     * All other exchanges will be stopped.
     *
     * @param samplePeriod this is the sample interval, only one exchange is
     *            allowed through in this interval
     * @param unit this is the units for the samplePeriod e.g. Seconds
     * @return the builder
     */
    public SamplingDefinition sample(long samplePeriod, TimeUnit unit) {
        SamplingDefinition answer = new SamplingDefinition(samplePeriod, unit);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/sampling.html">Sampling Throttler</a>
     * Creates a sampling throttler allowing you to extract a sample of exchanges
     * from the traffic through a route. It is configured with a sampling message frequency
     * during which only a single exchange is allowed to pass through.
     * All other exchanges will be stopped.
     *
     * @param messageFrequency this is the sample message frequency, only one exchange is 
     *              allowed through for this many messages received
     * @return the builder
     */
    public SamplingDefinition sample(long messageFrequency) {
        SamplingDefinition answer = new SamplingDefinition(messageFrequency);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/splitter.html">Splitter EIP:</a>
     * Creates a splitter allowing you split a message into a number of pieces and process them individually.
     * <p>
     * This splitter responds with the original input message. You can use a custom {@link AggregationStrategy} to
     * control what to respond from the splitter.
     *
     * @return the expression clause builder for the expression on which to split
     */
    public ExpressionClause<SplitDefinition> split() {
        SplitDefinition answer = new SplitDefinition();
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }

    /**
     * <a href="http://camel.apache.org/splitter.html">Splitter EIP:</a>
     * Creates a splitter allowing you split a message into a number of pieces and process them individually.
     * <p>
     * This splitter responds with the original input message. You can use a custom {@link AggregationStrategy} to
     * control what to respond from the splitter.
     *
     * @param expression  the expression on which to split the message
     * @return the builder
     */
    public SplitDefinition split(Expression expression) {
        SplitDefinition answer = new SplitDefinition(expression);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/splitter.html">Splitter EIP:</a>
     * Creates a splitter allowing you split a message into a number of pieces and process them individually.
     * <p>
     * The splitter responds with the answer produced by the given {@link AggregationStrategy}.
     *
     * @param expression  the expression on which to split
     * @param aggregationStrategy  the strategy used to aggregate responses for every part
     * @return the builder
     */
    public SplitDefinition split(Expression expression, AggregationStrategy aggregationStrategy) {
        SplitDefinition answer = new SplitDefinition(expression);
        addOutput(answer);
        answer.setAggregationStrategy(aggregationStrategy);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/resequencer.html">Resequencer EIP:</a>
     * Creates a resequencer allowing you to reorganize messages based on some comparator.
     *
     * @return the expression clause for the expressions on which to compare messages in order
     */
    public ExpressionClause<ResequenceDefinition> resequence() {
        ResequenceDefinition answer = new ResequenceDefinition();
        ExpressionClause<ResequenceDefinition> clause = new ExpressionClause<ResequenceDefinition>(answer);
        answer.setExpression(clause);
        addOutput(answer);
        return clause;
    }

    /**
     * <a href="http://camel.apache.org/resequencer.html">Resequencer EIP:</a>
     * Creates a resequencer allowing you to reorganize messages based on some comparator.
     *
     * @param expression the expression on which to compare messages in order
     * @return the builder
     */
    public ResequenceDefinition resequence(Expression expression) {
        ResequenceDefinition answer = new ResequenceDefinition();
        answer.setExpression(ExpressionNodeHelper.toExpressionDefinition(expression));
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/aggregator.html">Aggregator EIP:</a>
     * Creates an aggregator allowing you to combine a number of messages together into a single message.
     *
     * @return the expression clause to be used as builder to configure the correlation expression
     */
    public ExpressionClause<AggregateDefinition> aggregate() {
        AggregateDefinition answer = new AggregateDefinition();
        ExpressionClause<AggregateDefinition> clause = new ExpressionClause<AggregateDefinition>(answer);
        answer.setExpression(clause);
        addOutput(answer);
        return clause;
    }

    /**
     * <a href="http://camel.apache.org/aggregator.html">Aggregator EIP:</a>
     * Creates an aggregator allowing you to combine a number of messages together into a single message.
     *
     * @param aggregationStrategy the strategy used for the aggregation
     * @return the expression clause to be used as builder to configure the correlation expression
     */
    public ExpressionClause<AggregateDefinition> aggregate(AggregationStrategy aggregationStrategy) {
        AggregateDefinition answer = new AggregateDefinition();
        ExpressionClause<AggregateDefinition> clause = new ExpressionClause<AggregateDefinition>(answer);
        answer.setExpression(clause);
        answer.setAggregationStrategy(aggregationStrategy);
        addOutput(answer);
        return clause;
    }

    /**
     * <a href="http://camel.apache.org/aggregator.html">Aggregator EIP:</a>
     * Creates an aggregator allowing you to combine a number of messages together into a single message.
     *
     * @param correlationExpression the expression used to calculate the
     *                              correlation key. For a JMS message this could be the
     *                              expression <code>header("JMSDestination")</code> or
     *                              <code>header("JMSCorrelationID")</code>
     * @return the builder
     */
    public AggregateDefinition aggregate(Expression correlationExpression) {
        AggregateDefinition answer = new AggregateDefinition(correlationExpression);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/aggregator.html">Aggregator EIP:</a>
     * Creates an aggregator allowing you to combine a number of messages together into a single message.
     *
     * @param correlationExpression the expression used to calculate the
     *                              correlation key. For a JMS message this could be the
     *                              expression <code>header("JMSDestination")</code> or
     *                              <code>header("JMSCorrelationID")</code>
     * @param aggregationStrategy the strategy used for the aggregation
     * @return the builder
     */
    public AggregateDefinition aggregate(Expression correlationExpression, AggregationStrategy aggregationStrategy) {
        AggregateDefinition answer = new AggregateDefinition(correlationExpression, aggregationStrategy);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/delayer.html">Delayer EIP:</a>
     * Creates a delayer allowing you to delay the delivery of messages to some destination.
     *
     * @param delay  an expression to calculate the delay time in millis
     * @return the builder
     */
    public DelayDefinition delay(Expression delay) {
        DelayDefinition answer = new DelayDefinition(delay);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/delayer.html">Delayer EIP:</a>
     * Creates a delayer allowing you to delay the delivery of messages to some destination.
     *
     * @return the expression clause to create the expression
     */
    public ExpressionClause<DelayDefinition> delay() {
        DelayDefinition answer = new DelayDefinition();
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }

    /**
     * <a href="http://camel.apache.org/delayer.html">Delayer EIP:</a>
     * Creates a delayer allowing you to delay the delivery of messages to some destination.
     *
     * @param delay  the delay in millis
     * @return the builder
     */
    public DelayDefinition delay(long delay) {
        return delay(ExpressionBuilder.constantExpression(delay));
    }

    /**
     * <a href="http://camel.apache.org/throttler.html">Throttler EIP:</a>
     * Creates a throttler allowing you to ensure that a specific endpoint does not get overloaded,
     * or that we don't exceed an agreed SLA with some external service.
     * <p/>
     * Will default use a time period of 1 second, so setting the maximumRequestCount to eg 10
     * will default ensure at most 10 messages per second. 
     *
     * @param maximumRequestCount  the maximum messages 
     * @return the builder
     */
    public ThrottleDefinition throttle(long maximumRequestCount) {
        return throttle(ExpressionBuilder.constantExpression(maximumRequestCount));
    }

    /**
     * <a href="http://camel.apache.org/throttler.html">Throttler EIP:</a>
     * Creates a throttler allowing you to ensure that a specific endpoint does not get overloaded,
     * or that we don't exceed an agreed SLA with some external service.
     * <p/>
     * Will default use a time period of 1 second, so setting the maximumRequestCount to eg 10
     * will default ensure at most 10 messages per second. 
     *
     * @param maximumRequestCount  an expression to calculate the maximum request count 
     * @return the builder
     */
    public ThrottleDefinition throttle(Expression maximumRequestCount) {
        ThrottleDefinition answer = new ThrottleDefinition(maximumRequestCount);
        addOutput(answer);
        return answer;
    }
    
    /**
     * <a href="http://camel.apache.org/loop.html">Loop EIP:</a>
     * Creates a loop allowing to process the a message a number of times and possibly process them
     * in a different way. Useful mostly for testing.
     *
     * @return the clause used to create the loop expression
     */
    public ExpressionClause<LoopDefinition> loop() {
        LoopDefinition loop = new LoopDefinition();
        addOutput(loop);
        return ExpressionClause.createAndSetExpression(loop);
    }

    /**
     * <a href="http://camel.apache.org/loop.html">Loop EIP:</a>
     * Creates a loop allowing to process the a message a number of times and possibly process them
     * in a different way. Useful mostly for testing.
     *
     * @param expression the loop expression
     * @return the builder
     */
    public LoopDefinition loop(Expression expression) {
        LoopDefinition loop = new LoopDefinition();
        loop.setExpression(new ExpressionDefinition(expression));
        addOutput(loop);
        return loop;
    }

    /**
     * <a href="http://camel.apache.org/loop.html">Loop EIP:</a>
     * Creates a loop allowing to process the a message a number of times and possibly process them
     * in a different way. Useful mostly for testing.
     *
     * @param count  the number of times
     * @return the builder
     */
    public LoopDefinition loop(int count) {
        LoopDefinition loop = new LoopDefinition();
        loop.setExpression(new ConstantExpression(Integer.toString(count)));
        addOutput(loop);
        return loop;
    }

    /**
     * Sets the exception on the {@link org.apache.camel.Exchange}
     *
     * @param exception the exception to throw
     * @return the builder
     */
    public Type throwException(Exception exception) {
        ThrowExceptionDefinition answer = new ThrowExceptionDefinition();
        answer.setException(exception);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Marks the exchange for rollback only.
     * <p/>
     * Does <b>not</b> set any exception as opposed to {@link #rollback()} methods.
     *
     * @return the builder
     * @see #rollback()
     * @see #rollback(String)
     * @see #markRollbackOnlyLast()
     */
    public Type markRollbackOnly() {
        RollbackDefinition answer = new RollbackDefinition();
        answer.setMarkRollbackOnly(true);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Marks the exchange for rollback only, but only for the last (current) transaction.
     * <p/>
     * A last rollback is used when you have nested transactions and only want the last local transaction to rollback,
     * where as the outer transaction can still be completed
     * <p/>
     * Does <b>not</b> set any exception as opposed to {@link #rollback()} methods.
     *
     * @return the builder
     * @see #rollback()
     * @see #rollback(String)
     * @see #markRollbackOnly()
     */
    public Type markRollbackOnlyLast() {
        RollbackDefinition answer = new RollbackDefinition();
        answer.setMarkRollbackOnlyLast(true);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Marks the exchange for rollback only and sets an exception with a default message.
     * <p/>
     * This is done by setting a {@link org.apache.camel.RollbackExchangeException} on the Exchange
     * and mark it for rollback.
     *
     * @return the builder
     * @see #markRollbackOnly()
     */
    public Type rollback() {
        return rollback(null);
    }

    /**
     * Marks the exchange for rollback and sets an exception with the provided message.
     * <p/>
     * This is done by setting a {@link org.apache.camel.RollbackExchangeException} on the Exchange
     * and mark it for rollback.
     *
     * @param message an optional message used for logging purpose why the rollback was triggered
     * @return the builder
     * @see #markRollbackOnly()
     */
    public Type rollback(String message) {
        RollbackDefinition answer = new RollbackDefinition(message);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/wiretap.html">WireTap EIP:</a>
     * Sends messages to all its child outputs; so that each processor and
     * destination gets a copy of the original message to avoid the processors
     * interfering with each other using {@link ExchangePattern#InOnly}.
     *
     * @param uri  the destination
     * @return the builder
     */
    public WireTapDefinition<Type> wireTap(String uri) {
        WireTapDefinition<Type> answer = new WireTapDefinition<Type>();
        answer.setUri(uri);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/wiretap.html">WireTap EIP:</a>
     * Sends messages to all its child outputs; so that each processor and
     * destination gets a copy of the original message to avoid the processors
     * interfering with each other using {@link ExchangePattern#InOnly}.
     *
     * @param uri  the destination
     * @param      executorService a custom {@link ExecutorService} to use as thread pool
     *             for sending tapped exchanges
     * @return the builder
     * @deprecated use the fluent builder from {@link WireTapDefinition}, will be removed in Camel 3.0
     */
    @Deprecated
    public WireTapDefinition<Type> wireTap(String uri, ExecutorService executorService) {
        WireTapDefinition<Type> answer = new WireTapDefinition<Type>();
        answer.setUri(uri);
        answer.setExecutorService(executorService);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/wiretap.html">WireTap EIP:</a>
     * Sends messages to all its child outputs; so that each processor and
     * destination gets a copy of the original message to avoid the processors
     * interfering with each other using {@link ExchangePattern#InOnly}.
     *
     * @param uri  the destination
     * @param      executorServiceRef reference to lookup a custom {@link ExecutorService}
     *             to use as thread pool for sending tapped exchanges
     * @return the builder
     * @deprecated use the fluent builder from {@link WireTapDefinition}, will be removed in Camel 3.0
     */
    @Deprecated
    public WireTapDefinition<Type> wireTap(String uri, String executorServiceRef) {
        WireTapDefinition<Type> answer = new WireTapDefinition<Type>();
        answer.setUri(uri);
        answer.setExecutorServiceRef(executorServiceRef);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/wiretap.html">WireTap EIP:</a>
     * Sends a new {@link org.apache.camel.Exchange} to the destination
     * using {@link ExchangePattern#InOnly}.
     * <p/>
     * Will use a copy of the original Exchange which is passed in as argument
     * to the given expression
     *
     * @param uri  the destination
     * @param body expression that creates the body to send
     * @return the builder
     * @deprecated use the fluent builder from {@link WireTapDefinition}, will be removed in Camel 3.0
     */
    @Deprecated
    public WireTapDefinition<Type> wireTap(String uri, Expression body) {
        return wireTap(uri, true, body);
    }

    /**
     * <a href="http://camel.apache.org/wiretap.html">WireTap EIP:</a>
     * Sends a new {@link org.apache.camel.Exchange} to the destination
     * using {@link ExchangePattern#InOnly}.
     *
     * @param uri  the destination
     * @param copy whether or not use a copy of the original exchange or a new empty exchange
     * @param body expression that creates the body to send
     * @return the builder
     * @deprecated use the fluent builder from {@link WireTapDefinition}, will be removed in Camel 3.0
     */
    @Deprecated
    public WireTapDefinition<Type> wireTap(String uri, boolean copy, Expression body) {
        WireTapDefinition<Type> answer = new WireTapDefinition<Type>();
        answer.setUri(uri);
        answer.setCopy(copy);
        answer.setNewExchangeExpression(body);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/wiretap.html">WireTap EIP:</a>
     * Sends a new {@link org.apache.camel.Exchange} to the destination
     * using {@link ExchangePattern#InOnly}.
     * <p/>
     * Will use a copy of the original Exchange which is passed in as argument
     * to the given processor
     *
     * @param uri  the destination
     * @param processor  processor preparing the new exchange to send
     * @return the builder
     * @deprecated use the fluent builder from {@link WireTapDefinition}, will be removed in Camel 3.0
     */
    @Deprecated
    public WireTapDefinition<Type> wireTap(String uri, Processor processor) {
        return wireTap(uri, true, processor);
    }

    /**
     * <a href="http://camel.apache.org/wiretap.html">WireTap EIP:</a>
     * Sends a new {@link org.apache.camel.Exchange} to the destination
     * using {@link ExchangePattern#InOnly}.
     *
     * @param uri  the destination
     * @param copy whether or not use a copy of the original exchange or a new empty exchange
     * @param processor  processor preparing the new exchange to send
     * @return the builder
     * @deprecated use the fluent builder from {@link WireTapDefinition}, will be removed in Camel 3.0
     */
    @Deprecated
    public WireTapDefinition<Type> wireTap(String uri, boolean copy, Processor processor) {
        WireTapDefinition<Type> answer = new WireTapDefinition<Type>();
        answer.setUri(uri);
        answer.setCopy(copy);
        answer.setNewExchangeProcessor(processor);
        addOutput(answer);
        return answer;
    }

    /**
     * Pushes the given block on the stack as current block
     *
     * @param block  the block
     */
    void pushBlock(Block block) {
        blocks.add(block);
    }

    /**
     * Pops the block off the stack as current block
     *
     * @return the block
     */
    Block popBlock() {
        return blocks.isEmpty() ? null : blocks.removeLast();
    }

    @SuppressWarnings("unchecked")
    public Type startupOrder(int startupOrder) {
        ProcessorDefinition<?> def = this;

        RouteDefinition route = ProcessorDefinitionHelper.getRoute(def);
        if (route != null) {
            route.startupOrder(startupOrder);
        }

        return (Type) this;
    }

    /**
     * Stops continue routing the current {@link org.apache.camel.Exchange} and marks it as completed.
     *
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type stop() {
        StopDefinition stop = new StopDefinition();
        addOutput(stop);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/exception-clause.html">Exception clause</a>
     * for catching certain exceptions and handling them.
     *
     * @param exceptionType  the exception to catch
     * @return the exception builder to configure
     */
    public OnExceptionDefinition onException(Class<? extends Throwable> exceptionType) {
        OnExceptionDefinition answer = new OnExceptionDefinition(exceptionType);
        answer.setRouteScoped(true);
        addOutput(answer);
        return answer;
    }

    /**
     * <a href="http://camel.apache.org/exception-clause.html">Exception clause</a>
     * for catching certain exceptions and handling them.
     *
     * @param exceptions list of exceptions to catch
     * @return the exception builder to configure
     */
    public OnExceptionDefinition onException(Class<? extends Throwable>... exceptions) {
        OnExceptionDefinition answer = new OnExceptionDefinition(Arrays.asList(exceptions));
        answer.setRouteScoped(true);
        addOutput(answer);
        return answer;
    }

    /**
     * Apply a {@link Policy}.
     * <p/>
     * Policy can be used for transactional policies.
     *
     * @param policy  the policy to apply
     * @return the policy builder to configure
     */
    public PolicyDefinition policy(Policy policy) {
        PolicyDefinition answer = new PolicyDefinition(policy);
        addOutput(answer);
        return answer;
    }

    /**
     * Apply a {@link Policy}.
     * <p/>
     * Policy can be used for transactional policies.
     *
     * @param ref  reference to lookup a policy in the registry
     * @return the policy builder to configure
     */
    public PolicyDefinition policy(String ref) {
        PolicyDefinition answer = new PolicyDefinition();
        answer.setRef(ref);
        addOutput(answer);
        return answer;
    }

    /**
     * Marks this route as transacted and uses the default transacted policy found in the registry.
     *
     * @return the policy builder to configure
     */
    public TransactedDefinition transacted() {
        TransactedDefinition answer = new TransactedDefinition();
        addOutput(answer);
        return answer;
    }

    /**
     * Marks this route as transacted.
     *
     * @param ref  reference to lookup a transacted policy in the registry
     * @return the policy builder to configure
     */
    public TransactedDefinition transacted(String ref) {
        TransactedDefinition answer = new TransactedDefinition();
        answer.setRef(ref);
        addOutput(answer);
        return answer;
    }

    // Transformers
    // -------------------------------------------------------------------------

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds the custom processor to this destination which could be a final
     * destination, or could be a transformation in a pipeline
     *
     * @param processor  the custom {@link Processor}
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type process(Processor processor) {
        ProcessDefinition answer = new ProcessDefinition(processor);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds the custom processor reference to this destination which could be a final
     * destination, or could be a transformation in a pipeline
     *
     * @param ref   reference to a {@link Processor} to lookup in the registry
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type process(String ref) {
        ProcessDefinition answer = new ProcessDefinition();
        answer.setRef(ref);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds the custom processor reference to this destination which could be a final
     * destination, or could be a transformation in a pipeline
     *
     * @param ref   reference to a {@link Processor} to lookup in the registry
     * @return the builder
     * @deprecated use {@link #process(String)}
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type processRef(String ref) {
        ProcessDefinition answer = new ProcessDefinition();
        answer.setRef(ref);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param bean  the bean to invoke, or a reference to a bean if the type is a String
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type bean(Object bean) {
        BeanDefinition answer = new BeanDefinition();
        if (bean instanceof String) {
            answer.setRef((String) bean);
        } else {
            answer.setBean(bean);
        }
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param bean  the bean to invoke, or a reference to a bean if the type is a String
     * @param method  the method name to invoke on the bean (can be used to avoid ambiguity)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type bean(Object bean, String method) {
        BeanDefinition answer = new BeanDefinition();
        if (bean instanceof String) {
            answer.setRef((String) bean);
        } else {
            answer.setBean(bean);
        }
        answer.setMethod(method);
        addOutput(answer);
        return (Type) this;
    }
    
    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param bean  the bean to invoke, or a reference to a bean if the type is a String
     * @param cache  if enabled, Camel will cache the result of the first Registry look-up.
     *               Cache can be enabled if the bean in the Registry is defined as a singleton scope.
     *  the multi parameter
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type bean(Object bean, boolean cache) {
        BeanDefinition answer = new BeanDefinition();
        if (bean instanceof String) {
            answer.setRef((String) bean);
        } else {
            answer.setBean(bean);
        }
        answer.setCache(cache);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param bean  the bean to invoke, or a reference to a bean if the type is a String
     * @param method  the method name to invoke on the bean (can be used to avoid ambiguity)
     * @param cache  if enabled, Camel will cache the result of the first Registry look-up.
     *               Cache can be enabled if the bean in the Registry is defined as a singleton scope.
     *  the multi parameter
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type bean(Object bean, String method, boolean cache) {
        BeanDefinition answer = new BeanDefinition();
        if (bean instanceof String) {
            answer.setRef((String) bean);
        } else {
            answer.setBean(bean);
        }
        answer.setMethod(method);
        answer.setCache(cache);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param  beanType  the bean class, Camel will instantiate an object at runtime
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type bean(Class<?> beanType) {
        BeanDefinition answer = new BeanDefinition();
        answer.setBeanType(beanType);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param  beanType  the bean class, Camel will instantiate an object at runtime
     * @param method  the method name to invoke on the bean (can be used to avoid ambiguity)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type bean(Class<?> beanType, String method) {
        BeanDefinition answer = new BeanDefinition();
        answer.setBeanType(beanType);
        answer.setMethod(method);
        addOutput(answer);
        return (Type) this;
    }
    
    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param beanType  the bean class, Camel will instantiate an object at runtime
     * @param method  the method name to invoke on the bean (can be used to avoid ambiguity)
     * @param multiParameterArray if it is true, camel will treat the message body as an object array which holds
     *  the multi parameter 
     * @return the builder
     * @deprecated the option multiParameterArray is deprecated
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type bean(Class<?> beanType, String method, boolean multiParameterArray) {
        BeanDefinition answer = new BeanDefinition();
        answer.setBeanType(beanType);
        answer.setMethod(method);
        answer.setMultiParameterArray(multiParameterArray);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param beanType  the bean class, Camel will instantiate an object at runtime
     * @param method  the method name to invoke on the bean (can be used to avoid ambiguity)
     * @param multiParameterArray if it is true, camel will treat the message body as an object array which holds
     *  the multi parameter
     * @param cache  if enabled, Camel will cache the result of the first Registry look-up.
     *               Cache can be enabled if the bean in the Registry is defined as a singleton scope.
     * @return the builder
     * @deprecated the option multiParameterArray is deprecated
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type bean(Class<?> beanType, String method, boolean multiParameterArray, boolean cache) {
        BeanDefinition answer = new BeanDefinition();
        answer.setBeanType(beanType);
        answer.setMethod(method);
        answer.setMultiParameterArray(multiParameterArray);
        answer.setCache(cache);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param ref  reference to a bean to lookup in the registry
     * @return the builder
     * @deprecated use {@link #bean(Object)}
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type beanRef(String ref) {
        BeanDefinition answer = new BeanDefinition(ref);
        addOutput(answer);
        return (Type) this;
    }
    
    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param ref  reference to a bean to lookup in the registry
     * @param method  the method name to invoke on the bean (can be used to avoid ambiguity)
     * @return the builder
     * @deprecated use {@link #bean(Object, String)}
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type beanRef(String ref, String method) {
        BeanDefinition answer = new BeanDefinition(ref, method);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param ref  reference to a bean to lookup in the registry
     * @param cache  if enabled, Camel will cache the result of the first Registry look-up.
     *               Cache can be enabled if the bean in the Registry is defined as a singleton scope.
     * @return the builder
     * @deprecated use {@link #bean(Object, String, boolean)}
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type beanRef(String ref, boolean cache) {
        BeanDefinition answer = new BeanDefinition(ref);
        answer.setCache(cache);
        addOutput(answer);
        return (Type) this;
    }
    
    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param ref  reference to a bean to lookup in the registry
     * @param method  the method name to invoke on the bean (can be used to avoid ambiguity)
     * @param cache  if enabled, Camel will cache the result of the first Registry look-up.
     *               Cache can be enabled if the bean in the Registry is defined as a singleton scope.
     * @return the builder
     * @deprecated use {@link #bean(Object, String, boolean)}
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type beanRef(String ref, String method, boolean cache) {
        BeanDefinition answer = new BeanDefinition(ref, method);
        answer.setCache(cache);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a bean which is invoked which could be a final destination, or could be a transformation in a pipeline
     *
     * @param ref  reference to a bean to lookup in the registry
     * @param method  the method name to invoke on the bean (can be used to avoid ambiguity)
     * @param cache  if enabled, Camel will cache the result of the first Registry look-up.
     *               Cache can be enabled if the bean in the Registry is defined as a singleton scope.
     * @param multiParameterArray if it is true, camel will treat the message body as an object array which holds
     *               the multi parameter 
     * @return the builder
     * @deprecated the option multiParameterArray is deprecated
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type beanRef(String ref, String method, boolean cache, boolean multiParameterArray) {
        BeanDefinition answer = new BeanDefinition(ref, method);
        answer.setCache(cache);
        answer.setMultiParameterArray(multiParameterArray);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a processor which sets the body on the IN message
     *
     * @return a expression builder clause to set the body
     */
    public ExpressionClause<ProcessorDefinition<Type>> setBody() {
        ExpressionClause<ProcessorDefinition<Type>> clause = new ExpressionClause<ProcessorDefinition<Type>>(this);
        SetBodyDefinition answer = new SetBodyDefinition(clause);
        addOutput(answer);
        return clause;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a processor which sets the body on the IN message
     *
     * @param expression   the expression used to set the body
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type setBody(Expression expression) {
        SetBodyDefinition answer = new SetBodyDefinition(expression);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a processor which sets the body on the OUT message
     *
     * @param expression   the expression used to set the body
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type transform(Expression expression) {
        TransformDefinition answer = new TransformDefinition(expression);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/message-translator.html">Message Translator EIP:</a>
     * Adds a processor which sets the body on the OUT message
     *
     * @return a expression builder clause to set the body
     */
    public ExpressionClause<ProcessorDefinition<Type>> transform() {
        ExpressionClause<ProcessorDefinition<Type>> clause = 
            new ExpressionClause<ProcessorDefinition<Type>>((ProcessorDefinition<Type>) this);
        TransformDefinition answer = new TransformDefinition(clause);
        addOutput(answer);
        return clause;
    }

    /**
     * Adds a processor which sets the body on the FAULT message
     *
     * @param expression   the expression used to set the body
     * @return the builder
     */
    public Type setFaultBody(Expression expression) {
        return process(ProcessorBuilder.setFaultBody(expression));
    }

    /**
     * Adds a processor which sets the header on the IN message
     *
     * @param name  the header name
     * @return a expression builder clause to set the header
     */
    public ExpressionClause<ProcessorDefinition<Type>> setHeader(String name) {
        ExpressionClause<ProcessorDefinition<Type>> clause = new ExpressionClause<ProcessorDefinition<Type>>(this);
        SetHeaderDefinition answer = new SetHeaderDefinition(name, clause);
        addOutput(answer);
        return clause;
    }

    /**
     * Adds a processor which sets the header on the IN message
     *
     * @param name  the header name
     * @param expression  the expression used to set the header
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type setHeader(String name, Expression expression) {
        SetHeaderDefinition answer = new SetHeaderDefinition(name, expression);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Adds a processor which sets the header on the OUT message
     *
     * @param name  the header name
     * @return a expression builder clause to set the header
     * @deprecated use {@link #setHeader(String)}
     */
    @Deprecated
    public ExpressionClause<ProcessorDefinition<Type>> setOutHeader(String name) {
        ExpressionClause<ProcessorDefinition<Type>> clause = new ExpressionClause<ProcessorDefinition<Type>>(this);
        SetOutHeaderDefinition answer = new SetOutHeaderDefinition(name, clause);
        addOutput(answer);
        return clause;
    }

    /**
     * Adds a processor which sets the header on the OUT message
     *
     * @param name  the header name
     * @param expression  the expression used to set the header
     * @return the builder
     * @deprecated use {@link #setHeader(String, org.apache.camel.Expression)}
     */
    @SuppressWarnings("unchecked")
    @Deprecated
    public Type setOutHeader(String name, Expression expression) {
        SetOutHeaderDefinition answer = new SetOutHeaderDefinition(name, expression);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Adds a processor which sets the header on the FAULT message
     *
     * @param name  the header name
     * @param expression  the expression used to set the header
     * @return the builder
     * @deprecated use {@link #setHeader(String, org.apache.camel.Expression)}
     */
    @Deprecated
    public Type setFaultHeader(String name, Expression expression) {
        return process(ProcessorBuilder.setFaultHeader(name, expression));
    }

    /**
     * Adds a processor which sets the exchange property
     *
     * @param name  the property name
     * @param expression  the expression used to set the property
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type setProperty(String name, Expression expression) {
        SetPropertyDefinition answer = new SetPropertyDefinition(name, expression);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Adds a processor which sets the exchange property
     *
     * @param name  the property name
     * @return a expression builder clause to set the property
     */
    public ExpressionClause<ProcessorDefinition<Type>> setProperty(String name) {
        ExpressionClause<ProcessorDefinition<Type>> clause = new ExpressionClause<ProcessorDefinition<Type>>(this);
        SetPropertyDefinition answer = new SetPropertyDefinition(name, clause);
        addOutput(answer);
        return clause;
    }

    /**
     * Adds a processor which removes the header on the IN message
     *
     * @param name  the header name
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type removeHeader(String name) {
        RemoveHeaderDefinition answer = new RemoveHeaderDefinition(name);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Adds a processor which removes the headers on the IN message
     *
     * @param pattern  a pattern to match header names to be removed
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type removeHeaders(String pattern) {
        RemoveHeadersDefinition answer = new RemoveHeadersDefinition(pattern);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Adds a processor which removes the headers on the IN message
     *
     * @param pattern  a pattern to match header names to be removed
     * @param excludePatterns one or more pattern of header names that should be excluded (= preserved)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type removeHeaders(String pattern, String... excludePatterns) {
        RemoveHeadersDefinition answer = new RemoveHeadersDefinition(pattern, excludePatterns);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Adds a processor which removes the header on the FAULT message
     *
     * @param name  the header name
     * @return the builder
     * @deprecated will be removed in the near future. Instead use {@link #removeHeader(String)}
     */
    @Deprecated
    public Type removeFaultHeader(String name) {
        return process(ProcessorBuilder.removeFaultHeader(name));
    }

    /**
     * Adds a processor which removes the exchange property
     *
     * @param name  the property name
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type removeProperty(String name) {
        RemovePropertyDefinition answer = new RemovePropertyDefinition(name);
        addOutput(answer);
        return (Type) this;
    }
    
    /**
     * Adds a processor which removes the properties in the exchange
     *
     * @param pattern a pattern to match properties names to be removed
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type removeProperties(String pattern) {
        RemovePropertiesDefinition answer = new RemovePropertiesDefinition(pattern);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Adds a processor which removes the properties in the exchange
     *
     * @param pattern a pattern to match properties names to be removed
     * @param excludePatterns one or more pattern of properties names that should be excluded (= preserved)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type removeProperties(String pattern, String... excludePatterns) {
        RemovePropertiesDefinition answer = new RemovePropertiesDefinition(pattern, excludePatterns);
        addOutput(answer);
        return (Type) this;
    }

    /**
     * Converts the IN message body to the specified type
     *
     * @param type the type to convert to
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type convertBodyTo(Class<?> type) {
        addOutput(new ConvertBodyDefinition(type));
        return (Type) this;
    }
    
    /**
     * Converts the IN message body to the specified type
     *
     * @param type the type to convert to
     * @param charset the charset to use by type converters (not all converters support specifc charset)
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type convertBodyTo(Class<?> type, String charset) {
        addOutput(new ConvertBodyDefinition(type, charset));
        return (Type) this;
    }

    /**
     * Sorts the expression using a default sorting based on toString representation.
     *
     * @param expression  the expression, must be convertable to {@link List}
     * @return the builder
     */
    public Type sort(Expression expression) {
        return sort(expression, null);
    }

    /**
     * Sorts the expression using the given comparator
     *
     * @param expression  the expression, must be convertable to {@link List}
     * @param comparator  the comparator to use for sorting
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public <T> Type sort(Expression expression, Comparator<T> comparator) {
        addOutput(new SortDefinition<T>(expression, comparator));
        return (Type) this;
    }

    /**
     * Sorts the expression
     *
     * @return the builder
     */
    public <T> ExpressionClause<SortDefinition<T>> sort() {
        SortDefinition<T> answer = new SortDefinition<T>();
        addOutput(answer);
        return ExpressionClause.createAndSetExpression(answer);
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>.
     * 
     * @param resourceUri           URI of resource endpoint for obtaining additional data.
     * @param aggregationStrategy   aggregation strategy to aggregate input data and additional data.
     * @return the builder
     * @see org.apache.camel.processor.Enricher
     */
    @SuppressWarnings("unchecked")
    public Type enrich(String resourceUri, AggregationStrategy aggregationStrategy) {
        addOutput(new EnrichDefinition(aggregationStrategy, resourceUri));
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>.
     *
     * @param resourceUri           URI of resource endpoint for obtaining additional data.
     * @param aggregationStrategy   aggregation strategy to aggregate input data and additional data.
     * @return the builder
     * @see org.apache.camel.processor.Enricher
     */
    @SuppressWarnings("unchecked")
    public Type enrich(String resourceUri, AggregationStrategy aggregationStrategy, boolean aggregateOnException) {
        EnrichDefinition enrich = new EnrichDefinition(aggregationStrategy, resourceUri);
        enrich.setAggregateOnException(aggregateOnException);
        addOutput(enrich);
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>.
     * <p/>
     * The difference between this and {@link #pollEnrich(String)} is that this uses a producer
     * to obatin the additional data, where as pollEnrich uses a polling consumer.
     *
     * @param resourceUri           URI of resource endpoint for obtaining additional data.
     * @return the builder
     * @see org.apache.camel.processor.Enricher
     */
    @SuppressWarnings("unchecked")
    public Type enrich(String resourceUri) {
        addOutput(new EnrichDefinition(resourceUri));
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>.
     * <p/>
     * The difference between this and {@link #pollEnrich(String)} is that this uses a producer
     * to obtain the additional data, where as pollEnrich uses a polling consumer.
     *
     * @param resourceRef            Reference of resource endpoint for obtaining additional data.
     * @param aggregationStrategyRef Reference of aggregation strategy to aggregate input data and additional data.
     * @return the builder
     * @see org.apache.camel.processor.Enricher
     */
    @SuppressWarnings("unchecked")
    public Type enrichRef(String resourceRef, String aggregationStrategyRef) {
        EnrichDefinition enrich = new EnrichDefinition();
        enrich.setResourceRef(resourceRef);
        enrich.setAggregationStrategyRef(aggregationStrategyRef);
        addOutput(enrich);
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>.
     * <p/>
     * The difference between this and {@link #pollEnrich(String)} is that this uses a producer
     * to obtain the additional data, where as pollEnrich uses a polling consumer.
     *
     * @param resourceRef            Reference of resource endpoint for obtaining additional data.
     * @param aggregationStrategyRef Reference of aggregation strategy to aggregate input data and additional data.
     * @param aggregateOnException   whether to call {@link org.apache.camel.processor.aggregate.AggregationStrategy#aggregate(org.apache.camel.Exchange, org.apache.camel.Exchange)} if
     *                               an exception was thrown.
     * @return the builder
     * @see org.apache.camel.processor.Enricher
     */
    @SuppressWarnings("unchecked")
    public Type enrichRef(String resourceRef, String aggregationStrategyRef, boolean aggregateOnException) {
        EnrichDefinition enrich = new EnrichDefinition();
        enrich.setResourceRef(resourceRef);
        enrich.setAggregationStrategyRef(aggregationStrategyRef);
        enrich.setAggregateOnException(aggregateOnException);
        addOutput(enrich);
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>
     * using a {@link org.apache.camel.PollingConsumer} to poll the endpoint.
     * <p/>
     * The difference between this and {@link #enrich(String)} is that this uses a consumer
     * to obtain the additional data, where as enrich uses a producer.
     * <p/>
     * This method will <tt>block</tt> until data is available, use the method with timeout if you do not
     * want to risk waiting a long time before data is available from the resourceUri.
     *
     * @param resourceUri           URI of resource endpoint for obtaining additional data.
     * @return the builder
     * @see org.apache.camel.processor.PollEnricher
     */
    @SuppressWarnings("unchecked")
    public Type pollEnrich(String resourceUri) {
        addOutput(new PollEnrichDefinition(null, resourceUri, -1));
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>
     * using a {@link org.apache.camel.PollingConsumer} to poll the endpoint.
     * <p/>
     * The difference between this and {@link #enrich(String)} is that this uses a consumer
     * to obtain the additional data, where as enrich uses a producer.
     * <p/>
     * This method will <b>block</b> until data is available, use the method with timeout if you do not
     * want to risk waiting a long time before data is available from the resourceUri.
     *
     * @param resourceUri           URI of resource endpoint for obtaining additional data.
     * @param aggregationStrategy   aggregation strategy to aggregate input data and additional data.
     * @return the builder
     * @see org.apache.camel.processor.PollEnricher
     */
    @SuppressWarnings("unchecked")
    public Type pollEnrich(String resourceUri, AggregationStrategy aggregationStrategy) {
        addOutput(new PollEnrichDefinition(aggregationStrategy, resourceUri, -1));
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>
     * using a {@link org.apache.camel.PollingConsumer} to poll the endpoint.
     * <p/>
     * The difference between this and {@link #enrich(String)} is that this uses a consumer
     * to obtain the additional data, where as enrich uses a producer.
     * <p/>
     * The timeout controls which operation to use on {@link org.apache.camel.PollingConsumer}.
     * If timeout is negative, we use <tt>receive</tt>. If timeout is 0 then we use <tt>receiveNoWait</tt>
     * otherwise we use <tt>receive(timeout)</tt>.
     *
     * @param resourceUri           URI of resource endpoint for obtaining additional data.
     * @param timeout               timeout in millis to wait at most for data to be available.
     * @param aggregationStrategy   aggregation strategy to aggregate input data and additional data.
     * @return the builder
     * @see org.apache.camel.processor.PollEnricher
     */
    @SuppressWarnings("unchecked")
    public Type pollEnrich(String resourceUri, long timeout, AggregationStrategy aggregationStrategy) {
        addOutput(new PollEnrichDefinition(aggregationStrategy, resourceUri, timeout));
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>
     * using a {@link org.apache.camel.PollingConsumer} to poll the endpoint.
     * <p/>
     * The difference between this and {@link #enrich(String)} is that this uses a consumer
     * to obtain the additional data, where as enrich uses a producer.
     * <p/>
     * The timeout controls which operation to use on {@link org.apache.camel.PollingConsumer}.
     * If timeout is negative, we use <tt>receive</tt>. If timeout is 0 then we use <tt>receiveNoWait</tt>
     * otherwise we use <tt>receive(timeout)</tt>.
     *
     * @param resourceUri           URI of resource endpoint for obtaining additional data.
     * @param timeout               timeout in millis to wait at most for data to be available.
     * @param aggregationStrategy   aggregation strategy to aggregate input data and additional data.
     * @param aggregateOnException   whether to call {@link org.apache.camel.processor.aggregate.AggregationStrategy#aggregate(org.apache.camel.Exchange, org.apache.camel.Exchange)} if
     *                               an exception was thrown.
     * @return the builder
     * @see org.apache.camel.processor.PollEnricher
     */
    @SuppressWarnings("unchecked")
    public Type pollEnrich(String resourceUri, long timeout, AggregationStrategy aggregationStrategy, boolean aggregateOnException) {
        PollEnrichDefinition pollEnrich = new PollEnrichDefinition(aggregationStrategy, resourceUri, timeout);
        pollEnrich.setAggregateOnException(aggregateOnException);
        addOutput(pollEnrich);
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>
     * using a {@link org.apache.camel.PollingConsumer} to poll the endpoint.
     * <p/>
     * The difference between this and {@link #enrich(String)} is that this uses a consumer
     * to obtain the additional data, where as enrich uses a producer.
     * <p/>
     * The timeout controls which operation to use on {@link org.apache.camel.PollingConsumer}.
     * If timeout is negative, we use <tt>receive</tt>. If timeout is 0 then we use <tt>receiveNoWait</tt>
     * otherwise we use <tt>receive(timeout)</tt>.
     *
     * @param resourceUri           URI of resource endpoint for obtaining additional data.
     * @param timeout               timeout in millis to wait at most for data to be available.
     * @return the builder
     * @see org.apache.camel.processor.PollEnricher
     */
    @SuppressWarnings("unchecked")
    public Type pollEnrich(String resourceUri, long timeout) {
        addOutput(new PollEnrichDefinition(null, resourceUri, timeout));
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>
     * using a {@link org.apache.camel.PollingConsumer} to poll the endpoint.
     * <p/>
     * The difference between this and {@link #enrich(String)} is that this uses a consumer
     * to obtain the additional data, where as enrich uses a producer.
     * <p/>
     * The timeout controls which operation to use on {@link org.apache.camel.PollingConsumer}.
     * If timeout is negative, we use <tt>receive</tt>. If timeout is 0 then we use <tt>receiveNoWait</tt>
     * otherwise we use <tt>receive(timeout)</tt>.
     *
     * @param resourceRef            Reference of resource endpoint for obtaining additional data.
     * @param timeout                timeout in millis to wait at most for data to be available.
     * @param aggregationStrategyRef Reference of aggregation strategy to aggregate input data and additional data.
     * @return the builder
     * @see org.apache.camel.processor.PollEnricher
     */
    @SuppressWarnings("unchecked")
    public Type pollEnrichRef(String resourceRef, long timeout, String aggregationStrategyRef) {
        PollEnrichDefinition pollEnrich = new PollEnrichDefinition();
        pollEnrich.setResourceRef(resourceRef);
        pollEnrich.setTimeout(timeout);
        pollEnrich.setAggregationStrategyRef(aggregationStrategyRef);
        addOutput(pollEnrich);
        return (Type) this;
    }

    /**
     * The <a href="http://camel.apache.org/content-enricher.html">Content Enricher EIP</a>
     * enriches an exchange with additional data obtained from a <code>resourceUri</code>
     * using a {@link org.apache.camel.PollingConsumer} to poll the endpoint.
     * <p/>
     * The difference between this and {@link #enrich(String)} is that this uses a consumer
     * to obtain the additional data, where as enrich uses a producer.
     * <p/>
     * The timeout controls which operation to use on {@link org.apache.camel.PollingConsumer}.
     * If timeout is negative, we use <tt>receive</tt>. If timeout is 0 then we use <tt>receiveNoWait</tt>
     * otherwise we use <tt>receive(timeout)</tt>.
     *
     * @param resourceRef            Reference of resource endpoint for obtaining additional data.
     * @param timeout                timeout in millis to wait at most for data to be available.
     * @param aggregationStrategyRef Reference of aggregation strategy to aggregate input data and additional data.
     * @param aggregateOnException   whether to call {@link org.apache.camel.processor.aggregate.AggregationStrategy#aggregate(org.apache.camel.Exchange, org.apache.camel.Exchange)} if
     *                               an exception was thrown.
     * @return the builder
     * @see org.apache.camel.processor.PollEnricher
     */
    @SuppressWarnings("unchecked")
    public Type pollEnrichRef(String resourceRef, long timeout, String aggregationStrategyRef, boolean aggregateOnException) {
        PollEnrichDefinition pollEnrich = new PollEnrichDefinition();
        pollEnrich.setResourceRef(resourceRef);
        pollEnrich.setTimeout(timeout);
        pollEnrich.setAggregationStrategyRef(aggregationStrategyRef);
        pollEnrich.setAggregateOnException(aggregateOnException);
        addOutput(pollEnrich);
        return (Type) this;
    }

    /**
     * Adds a onComplection {@link org.apache.camel.spi.Synchronization} hook that invoke this route as
     * a callback when the {@link org.apache.camel.Exchange} has finished being processed.
     * The hook invoke callbacks for either onComplete or onFailure.
     * <p/>
     * Will by default always trigger when the {@link org.apache.camel.Exchange} is complete
     * (either with success or failed).
     * <br/>
     * You can limit the callback to either onComplete or onFailure but invoking the nested
     * builder method.
     * <p/>
     * For onFailure the caused exception is stored as a property on the {@link org.apache.camel.Exchange}
     * with the key {@link org.apache.camel.Exchange#EXCEPTION_CAUGHT}.
     *
     * @return the builder
     */
    public OnCompletionDefinition onCompletion() {
        OnCompletionDefinition answer = new OnCompletionDefinition();
        // we must remove all existing on completion definition (as they are global)
        // and thus we are the only one as route scoped should override any global scoped
        answer.removeAllOnCompletionDefinition(this);
        popBlock();
        addOutput(answer);
        pushBlock(answer);
        return answer;
    }

    // DataFormat support
    // -------------------------------------------------------------------------

    /**
     * <a href="http://camel.apache.org/data-format.html">DataFormat:</a>
     * Unmarshals the in body using a {@link DataFormat} expression to define
     * the format of the input message and the output will be set on the out message body.
     *
     * @return the expression to create the {@link DataFormat}
     */
    public DataFormatClause<ProcessorDefinition<Type>> unmarshal() {
        return new DataFormatClause<ProcessorDefinition<Type>>(this, DataFormatClause.Operation.Unmarshal);
    }

    /**
     * <a href="http://camel.apache.org/data-format.html">DataFormat:</a>
     * Unmarshals the in body using the specified {@link DataFormat}
     * and sets the output on the out message body.
     *
     * @param dataFormatType  the dataformat
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type unmarshal(DataFormatDefinition dataFormatType) {
        addOutput(new UnmarshalDefinition(dataFormatType));
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/data-format.html">DataFormat:</a>
     * Unmarshals the in body using the specified {@link DataFormat}
     * and sets the output on the out message body.
     *
     * @param dataFormat  the dataformat
     * @return the builder
     */
    public Type unmarshal(DataFormat dataFormat) {
        return unmarshal(new DataFormatDefinition(dataFormat));
    }

    /**
     * <a href="http://camel.apache.org/data-format.html">DataFormat:</a>
     * Unmarshals the in body using the specified {@link DataFormat}
     * reference in the {@link org.apache.camel.spi.Registry} and sets
     * the output on the out message body.
     *
     * @param dataTypeRef  reference to a {@link DataFormat} to lookup in the registry
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type unmarshal(String dataTypeRef) {
        addOutput(new UnmarshalDefinition(dataTypeRef));
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/data-format.html">DataFormat:</a>
     * Marshals the in body using a {@link DataFormat} expression to define
     * the format of the output which will be added to the out body.
     *
     * @return the expression to create the {@link DataFormat}
     */
    public DataFormatClause<ProcessorDefinition<Type>> marshal() {
        return new DataFormatClause<ProcessorDefinition<Type>>(this, DataFormatClause.Operation.Marshal);
    }

    /**
     * <a href="http://camel.apache.org/data-format.html">DataFormat:</a>
     * Marshals the in body using the specified {@link DataFormat}
     * and sets the output on the out message body.
     *
     * @param dataFormatType  the dataformat
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type marshal(DataFormatDefinition dataFormatType) {
        addOutput(new MarshalDefinition(dataFormatType));
        return (Type) this;
    }

    /**
     * <a href="http://camel.apache.org/data-format.html">DataFormat:</a>
     * Marshals the in body using the specified {@link DataFormat}
     * and sets the output on the out message body.
     *
     * @param dataFormat  the dataformat
     * @return the builder
     */
    public Type marshal(DataFormat dataFormat) {
        return marshal(new DataFormatDefinition(dataFormat));
    }

    /**
     * <a href="http://camel.apache.org/data-format.html">DataFormat:</a>
     * Marshals the in body the specified {@link DataFormat}
     * reference in the {@link org.apache.camel.spi.Registry} and sets
     * the output on the out message body.
     *
     * @param dataTypeRef  reference to a {@link DataFormat} to lookup in the registry
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type marshal(String dataTypeRef) {
        addOutput(new MarshalDefinition(dataTypeRef));
        return (Type) this;
    }

    /**
     * Sets whether or not to inherit the configured error handler.
     * <br/>
     * The default value is <tt>true</tt>.
     * <p/>
     * You can use this to disable using the inherited error handler for a given
     * DSL such as a load balancer where you want to use a custom error handler strategy.
     *
     * @param inheritErrorHandler whether to not to inherit the error handler for this node
     * @return the builder
     */
    @SuppressWarnings("unchecked")
    public Type inheritErrorHandler(boolean inheritErrorHandler) {
        // set on last output
        int size = getOutputs().size();
        if (size == 0) {
            // if no outputs then configure this DSL
            setInheritErrorHandler(inheritErrorHandler);
        } else {
            // configure on last output as its the intended
            ProcessorDefinition<?> output = getOutputs().get(size - 1);
            if (output != null) {
                output.setInheritErrorHandler(inheritErrorHandler);
            }
        }
        return (Type) this;
    }

    // Properties
    // -------------------------------------------------------------------------
    public ProcessorDefinition<?> getParent() {
        return parent;
    }

    public void setParent(ProcessorDefinition<?> parent) {
        this.parent = parent;
    }

    public List<InterceptStrategy> getInterceptStrategies() {
        return interceptStrategies;
    }

    public void addInterceptStrategy(InterceptStrategy strategy) {
        this.interceptStrategies.add(strategy);
    }

    public Boolean isInheritErrorHandler() {
        return inheritErrorHandler;
    }

    public void setInheritErrorHandler(Boolean inheritErrorHandler) {
        this.inheritErrorHandler = inheritErrorHandler;
    }

    public Map<QName, Object> getOtherAttributes() {
        return otherAttributes;
    }

    public void setOtherAttributes(Map<QName, Object> otherAttributes) {
        this.otherAttributes = otherAttributes;
    }

    /**
     * Returns a label to describe this node such as the expression if some kind of expression node
     */
    public String getLabel() {
        return "";
    }
    
}


File: camel-core/src/main/java/org/apache/camel/model/ProcessorDefinitionHelper.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.camel.model;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ScheduledExecutorService;
import javax.xml.namespace.QName;

import org.apache.camel.CamelContext;
import org.apache.camel.Exchange;
import org.apache.camel.spi.ExecutorServiceManager;
import org.apache.camel.spi.RouteContext;
import org.apache.camel.util.CamelContextHelper;
import org.apache.camel.util.IntrospectionSupport;
import org.apache.camel.util.ObjectHelper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Helper class for ProcessorDefinition and the other model classes.
 */
public final class ProcessorDefinitionHelper {

    private static final Logger LOG = LoggerFactory.getLogger(ProcessorDefinitionHelper.class);
    private static final ThreadLocal<RestoreAction> CURRENT_RESTORE_ACTION = new ThreadLocal<RestoreAction>();

    private ProcessorDefinitionHelper() {
    }

    /**
     * Looks for the given type in the list of outputs and recurring all the children as well.
     *
     * @param outputs list of outputs, can be null or empty.
     * @param type    the type to look for
     * @return the found definitions, or <tt>null</tt> if not found
     */
    public static <T> Iterator<T> filterTypeInOutputs(List<ProcessorDefinition<?>> outputs, Class<T> type) {
        return filterTypeInOutputs(outputs, type, -1);
    }

    /**
     * Looks for the given type in the list of outputs and recurring all the children as well.
     *
     * @param outputs list of outputs, can be null or empty.
     * @param type    the type to look for
     * @param maxDeep maximum levels deep to traverse
     * @return the found definitions, or <tt>null</tt> if not found
     */
    public static <T> Iterator<T> filterTypeInOutputs(List<ProcessorDefinition<?>> outputs, Class<T> type, int maxDeep) {
        List<T> found = new ArrayList<T>();
        doFindType(outputs, type, found, maxDeep);
        return found.iterator();
    }

    /**
     * Looks for the given type in the list of outputs and recurring all the children as well.
     * Will stop at first found and return it.
     *
     * @param outputs list of outputs, can be null or empty.
     * @param type    the type to look for
     * @return the first found type, or <tt>null</tt> if not found
     */
    public static <T> T findFirstTypeInOutputs(List<ProcessorDefinition<?>> outputs, Class<T> type) {
        List<T> found = new ArrayList<T>();
        doFindType(outputs, type, found, -1);
        if (found.isEmpty()) {
            return null;
        }
        return found.iterator().next();
    }

    /**
     * Is the given child the first in the outputs from the parent?
     *
     * @param parentType the type the parent must be
     * @param node       the node
     * @return <tt>true</tt> if first child, <tt>false</tt> otherwise
     */
    public static boolean isFirstChildOfType(Class<?> parentType, ProcessorDefinition<?> node) {
        if (node == null || node.getParent() == null) {
            return false;
        }

        if (node.getParent().getOutputs().isEmpty()) {
            return false;
        }

        if (!(node.getParent().getClass().equals(parentType))) {
            return false;
        }

        return node.getParent().getOutputs().get(0).equals(node);
    }

    /**
     * Is the given node parent(s) of the given type
     *
     * @param parentType the parent type
     * @param node       the current node
     * @param recursive  whether or not to check grand parent(s) as well
     * @return <tt>true</tt> if parent(s) is of given type, <tt>false</tt> otherwise
     */
    public static boolean isParentOfType(Class<?> parentType, ProcessorDefinition<?> node, boolean recursive) {
        if (node == null || node.getParent() == null) {
            return false;
        }

        if (parentType.isAssignableFrom(node.getParent().getClass())) {
            return true;
        } else if (recursive) {
            // recursive up the tree of parents
            return isParentOfType(parentType, node.getParent(), true);
        } else {
            // no match
            return false;
        }
    }

    /**
     * Gets the route definition the given node belongs to.
     *
     * @param node the node
     * @return the route, or <tt>null</tt> if not possible to find
     */
    public static RouteDefinition getRoute(ProcessorDefinition<?> node) {
        if (node == null) {
            return null;
        }

        ProcessorDefinition<?> def = node;
        // drill to the top
        while (def != null && def.getParent() != null) {
            def = def.getParent();
        }

        if (def instanceof RouteDefinition) {
            return (RouteDefinition) def;
        } else {
            // not found
            return null;
        }
    }

    /**
     * Gets the route id the given node belongs to.
     *
     * @param node the node
     * @return the route id, or <tt>null</tt> if not possible to find
     */
    public static String getRouteId(ProcessorDefinition<?> node) {
        RouteDefinition route = getRoute(node);
        return route != null ? route.getId() : null;
    }

    /**
     * Traverses the node, including its children (recursive), and gathers all the node ids.
     *
     * @param node            the target node
     * @param set             set to store ids, if <tt>null</tt> a new set will be created
     * @param onlyCustomId    whether to only store custom assigned ids (ie. {@link org.apache.camel.model.OptionalIdentifiedDefinition#hasCustomIdAssigned()}
     * @param includeAbstract whether to include abstract nodes (ie. {@link org.apache.camel.model.ProcessorDefinition#isAbstract()}
     * @return the set with the found ids.
     */
    public static Set<String> gatherAllNodeIds(ProcessorDefinition<?> node, Set<String> set,
                                               boolean onlyCustomId, boolean includeAbstract) {
        if (node == null) {
            return set;
        }

        // skip abstract
        if (node.isAbstract() && !includeAbstract) {
            return set;
        }

        if (set == null) {
            set = new LinkedHashSet<String>();
        }

        // add ourselves
        if (node.getId() != null) {
            if (!onlyCustomId || node.hasCustomIdAssigned() && onlyCustomId) {
                set.add(node.getId());
            }
        }

        // traverse outputs and recursive children as well
        List<ProcessorDefinition<?>> children = node.getOutputs();
        if (children != null && !children.isEmpty()) {
            for (ProcessorDefinition<?> child : children) {
                // traverse children also
                gatherAllNodeIds(child, set, onlyCustomId, includeAbstract);
            }
        }

        return set;
    }

    private static <T> void doFindType(List<ProcessorDefinition<?>> outputs, Class<T> type, List<T> found, int maxDeep) {

        // do we have any top level abstracts, then we should max deep one more level down
        // as that is really what we want to traverse as well
        if (maxDeep > 0) {
            for (ProcessorDefinition<?> out : outputs) {
                if (out.isAbstract() && out.isTopLevelOnly()) {
                    maxDeep = maxDeep + 1;
                    break;
                }
            }
        }

        // start from level 1
        doFindType(outputs, type, found, 1, maxDeep);
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static <T> void doFindType(List<ProcessorDefinition<?>> outputs, Class<T> type, List<T> found, int current, int maxDeep) {
        if (outputs == null || outputs.isEmpty()) {
            return;
        }

        // break out
        if (maxDeep > 0 && current > maxDeep) {
            return;
        }

        for (ProcessorDefinition out : outputs) {

            // send is much common
            if (out instanceof SendDefinition) {
                SendDefinition send = (SendDefinition) out;
                List<ProcessorDefinition<?>> children = send.getOutputs();
                doFindType(children, type, found, ++current, maxDeep);
            }

            // special for choice
            if (out instanceof ChoiceDefinition) {
                ChoiceDefinition choice = (ChoiceDefinition) out;

                // ensure to add ourself if we match also
                if (type.isInstance(choice)) {
                    found.add((T) choice);
                }

                // only look at when/otherwise if current < maxDeep (or max deep is disabled)
                if (maxDeep < 0 || current < maxDeep) {
                    for (WhenDefinition when : choice.getWhenClauses()) {
                        if (type.isInstance(when)) {
                            found.add((T) when);
                        }
                        List<ProcessorDefinition<?>> children = when.getOutputs();
                        doFindType(children, type, found, ++current, maxDeep);
                    }

                    // otherwise is optional
                    if (choice.getOtherwise() != null) {
                        List<ProcessorDefinition<?>> children = choice.getOtherwise().getOutputs();
                        doFindType(children, type, found, ++current, maxDeep);
                    }
                }

                // do not check children as we already did that
                continue;
            }

            // special for try ... catch ... finally
            if (out instanceof TryDefinition) {
                TryDefinition doTry = (TryDefinition) out;

                // ensure to add ourself if we match also
                if (type.isInstance(doTry)) {
                    found.add((T) doTry);
                }

                // only look at children if current < maxDeep (or max deep is disabled)
                if (maxDeep < 0 || current < maxDeep) {
                    List<ProcessorDefinition<?>> doTryOut = doTry.getOutputsWithoutCatches();
                    doFindType(doTryOut, type, found, ++current, maxDeep);

                    List<CatchDefinition> doTryCatch = doTry.getCatchClauses();
                    for (CatchDefinition doCatch : doTryCatch) {
                        doFindType(doCatch.getOutputs(), type, found, ++current, maxDeep);
                    }

                    if (doTry.getFinallyClause() != null) {
                        doFindType(doTry.getFinallyClause().getOutputs(), type, found, ++current, maxDeep);
                    }
                }

                // do not check children as we already did that
                continue;
            }

            // special for some types which has special outputs
            if (out instanceof OutputDefinition) {
                OutputDefinition outDef = (OutputDefinition) out;

                // ensure to add ourself if we match also
                if (type.isInstance(outDef)) {
                    found.add((T) outDef);
                }

                List<ProcessorDefinition<?>> outDefOut = outDef.getOutputs();
                doFindType(outDefOut, type, found, ++current, maxDeep);

                // do not check children as we already did that
                continue;
            }

            if (type.isInstance(out)) {
                found.add((T) out);
            }

            // try children as well
            List<ProcessorDefinition<?>> children = out.getOutputs();
            doFindType(children, type, found, ++current, maxDeep);
        }
    }

    /**
     * Is there any outputs in the given list.
     * <p/>
     * Is used for check if the route output has any real outputs (non abstracts)
     *
     * @param outputs         the outputs
     * @param excludeAbstract whether or not to exclude abstract outputs (e.g. skip onException etc.)
     * @return <tt>true</tt> if has outputs, otherwise <tt>false</tt> is returned
     */
    @SuppressWarnings({"unchecked", "rawtypes"})
    public static boolean hasOutputs(List<ProcessorDefinition<?>> outputs, boolean excludeAbstract) {
        if (outputs == null || outputs.isEmpty()) {
            return false;
        }
        if (!excludeAbstract) {
            return !outputs.isEmpty();
        }
        for (ProcessorDefinition output : outputs) {
            if (output instanceof TransactedDefinition || output instanceof PolicyDefinition) {
                // special for those as they wrap entire output, so we should just check its output
                return hasOutputs(output.getOutputs(), excludeAbstract);
            }
            if (!output.isAbstract()) {
                return true;
            }
        }
        return false;
    }

    /**
     * Determines whether a new thread pool will be created or not.
     * <p/>
     * This is used to know if a new thread pool will be created, and therefore is not shared by others, and therefore
     * exclusive to the definition.
     *
     * @param routeContext the route context
     * @param definition   the node definition which may leverage executor service.
     * @param useDefault   whether to fallback and use a default thread pool, if no explicit configured
     * @return <tt>true</tt> if a new thread pool will be created, <tt>false</tt> if not
     * @see #getConfiguredExecutorService(org.apache.camel.spi.RouteContext, String, ExecutorServiceAwareDefinition, boolean)
     */
    public static boolean willCreateNewThreadPool(RouteContext routeContext, ExecutorServiceAwareDefinition<?> definition, boolean useDefault) {
        ExecutorServiceManager manager = routeContext.getCamelContext().getExecutorServiceManager();
        ObjectHelper.notNull(manager, "ExecutorServiceManager", routeContext.getCamelContext());

        if (definition.getExecutorService() != null) {
            // no there is a custom thread pool configured
            return false;
        } else if (definition.getExecutorServiceRef() != null) {
            ExecutorService answer = routeContext.getCamelContext().getRegistry().lookupByNameAndType(definition.getExecutorServiceRef(), ExecutorService.class);
            // if no existing thread pool, then we will have to create a new thread pool
            return answer == null;
        } else if (useDefault) {
            return true;
        }

        return false;
    }

    /**
     * Will lookup in {@link org.apache.camel.spi.Registry} for a {@link ExecutorService} registered with the given
     * <tt>executorServiceRef</tt> name.
     * <p/>
     * This method will lookup for configured thread pool in the following order
     * <ul>
     * <li>from the {@link org.apache.camel.spi.Registry} if found</li>
     * <li>from the known list of {@link org.apache.camel.spi.ThreadPoolProfile ThreadPoolProfile(s)}.</li>
     * <li>if none found, then <tt>null</tt> is returned.</li>
     * </ul>
     *
     * @param routeContext       the route context
     * @param name               name which is appended to the thread name, when the {@link java.util.concurrent.ExecutorService}
     *                           is created based on a {@link org.apache.camel.spi.ThreadPoolProfile}.
     * @param source             the source to use the thread pool
     * @param executorServiceRef reference name of the thread pool
     * @return the executor service, or <tt>null</tt> if none was found.
     */
    public static ExecutorService lookupExecutorServiceRef(RouteContext routeContext, String name,
                                                           Object source, String executorServiceRef) {

        ExecutorServiceManager manager = routeContext.getCamelContext().getExecutorServiceManager();
        ObjectHelper.notNull(manager, "ExecutorServiceManager", routeContext.getCamelContext());
        ObjectHelper.notNull(executorServiceRef, "executorServiceRef");

        // lookup in registry first and use existing thread pool if exists
        ExecutorService answer = routeContext.getCamelContext().getRegistry().lookupByNameAndType(executorServiceRef, ExecutorService.class);
        if (answer == null) {
            // then create a thread pool assuming the ref is a thread pool profile id
            answer = manager.newThreadPool(source, name, executorServiceRef);
        }
        return answer;
    }

    /**
     * Will lookup and get the configured {@link java.util.concurrent.ExecutorService} from the given definition.
     * <p/>
     * This method will lookup for configured thread pool in the following order
     * <ul>
     * <li>from the definition if any explicit configured executor service.</li>
     * <li>from the {@link org.apache.camel.spi.Registry} if found</li>
     * <li>from the known list of {@link org.apache.camel.spi.ThreadPoolProfile ThreadPoolProfile(s)}.</li>
     * <li>if none found, then <tt>null</tt> is returned.</li>
     * </ul>
     * The various {@link ExecutorServiceAwareDefinition} should use this helper method to ensure they support
     * configured executor services in the same coherent way.
     *
     * @param routeContext the route context
     * @param name         name which is appended to the thread name, when the {@link java.util.concurrent.ExecutorService}
     *                     is created based on a {@link org.apache.camel.spi.ThreadPoolProfile}.
     * @param definition   the node definition which may leverage executor service.
     * @param useDefault   whether to fallback and use a default thread pool, if no explicit configured
     * @return the configured executor service, or <tt>null</tt> if none was configured.
     * @throws IllegalArgumentException is thrown if lookup of executor service in {@link org.apache.camel.spi.Registry} was not found
     */
    public static ExecutorService getConfiguredExecutorService(RouteContext routeContext, String name,
                                                               ExecutorServiceAwareDefinition<?> definition,
                                                               boolean useDefault) throws IllegalArgumentException {
        ExecutorServiceManager manager = routeContext.getCamelContext().getExecutorServiceManager();
        ObjectHelper.notNull(manager, "ExecutorServiceManager", routeContext.getCamelContext());

        // prefer to use explicit configured executor on the definition
        if (definition.getExecutorService() != null) {
            return definition.getExecutorService();
        } else if (definition.getExecutorServiceRef() != null) {
            // lookup in registry first and use existing thread pool if exists
            ExecutorService answer = lookupExecutorServiceRef(routeContext, name, definition, definition.getExecutorServiceRef());
            if (answer == null) {
                throw new IllegalArgumentException("ExecutorServiceRef " + definition.getExecutorServiceRef() + " not found in registry or as a thread pool profile.");
            }
            return answer;
        } else if (useDefault) {
            return manager.newDefaultThreadPool(definition, name);
        }

        return null;
    }

    /**
     * Will lookup in {@link org.apache.camel.spi.Registry} for a {@link ScheduledExecutorService} registered with the given
     * <tt>executorServiceRef</tt> name.
     * <p/>
     * This method will lookup for configured thread pool in the following order
     * <ul>
     * <li>from the {@link org.apache.camel.spi.Registry} if found</li>
     * <li>from the known list of {@link org.apache.camel.spi.ThreadPoolProfile ThreadPoolProfile(s)}.</li>
     * <li>if none found, then <tt>null</tt> is returned.</li>
     * </ul>
     *
     * @param routeContext       the route context
     * @param name               name which is appended to the thread name, when the {@link java.util.concurrent.ExecutorService}
     *                           is created based on a {@link org.apache.camel.spi.ThreadPoolProfile}.
     * @param source             the source to use the thread pool
     * @param executorServiceRef reference name of the thread pool
     * @return the executor service, or <tt>null</tt> if none was found.
     */
    public static ScheduledExecutorService lookupScheduledExecutorServiceRef(RouteContext routeContext, String name,
                                                                             Object source, String executorServiceRef) {

        ExecutorServiceManager manager = routeContext.getCamelContext().getExecutorServiceManager();
        ObjectHelper.notNull(manager, "ExecutorServiceManager", routeContext.getCamelContext());
        ObjectHelper.notNull(executorServiceRef, "executorServiceRef");

        // lookup in registry first and use existing thread pool if exists
        ScheduledExecutorService answer = routeContext.getCamelContext().getRegistry().lookupByNameAndType(executorServiceRef, ScheduledExecutorService.class);
        if (answer == null) {
            // then create a thread pool assuming the ref is a thread pool profile id
            answer = manager.newScheduledThreadPool(source, name, executorServiceRef);
        }
        return answer;
    }

    /**
     * Will lookup and get the configured {@link java.util.concurrent.ScheduledExecutorService} from the given definition.
     * <p/>
     * This method will lookup for configured thread pool in the following order
     * <ul>
     * <li>from the definition if any explicit configured executor service.</li>
     * <li>from the {@link org.apache.camel.spi.Registry} if found</li>
     * <li>from the known list of {@link org.apache.camel.spi.ThreadPoolProfile ThreadPoolProfile(s)}.</li>
     * <li>if none found, then <tt>null</tt> is returned.</li>
     * </ul>
     * The various {@link ExecutorServiceAwareDefinition} should use this helper method to ensure they support
     * configured executor services in the same coherent way.
     *
     * @param routeContext the rout context
     * @param name         name which is appended to the thread name, when the {@link java.util.concurrent.ExecutorService}
     *                     is created based on a {@link org.apache.camel.spi.ThreadPoolProfile}.
     * @param definition   the node definition which may leverage executor service.
     * @param useDefault   whether to fallback and use a default thread pool, if no explicit configured
     * @return the configured executor service, or <tt>null</tt> if none was configured.
     * @throws IllegalArgumentException is thrown if the found instance is not a ScheduledExecutorService type,
     *                                  or lookup of executor service in {@link org.apache.camel.spi.Registry} was not found
     */
    public static ScheduledExecutorService getConfiguredScheduledExecutorService(RouteContext routeContext, String name,
                                                                                 ExecutorServiceAwareDefinition<?> definition,
                                                                                 boolean useDefault) throws IllegalArgumentException {
        ExecutorServiceManager manager = routeContext.getCamelContext().getExecutorServiceManager();
        ObjectHelper.notNull(manager, "ExecutorServiceManager", routeContext.getCamelContext());

        // prefer to use explicit configured executor on the definition
        if (definition.getExecutorService() != null) {
            ExecutorService executorService = definition.getExecutorService();
            if (executorService instanceof ScheduledExecutorService) {
                return (ScheduledExecutorService) executorService;
            }
            throw new IllegalArgumentException("ExecutorServiceRef " + definition.getExecutorServiceRef() + " is not an ScheduledExecutorService instance");
        } else if (definition.getExecutorServiceRef() != null) {
            ScheduledExecutorService answer = lookupScheduledExecutorServiceRef(routeContext, name, definition, definition.getExecutorServiceRef());
            if (answer == null) {
                throw new IllegalArgumentException("ExecutorServiceRef " + definition.getExecutorServiceRef() + " not found in registry or as a thread pool profile.");
            }
            return answer;
        } else if (useDefault) {
            return manager.newDefaultScheduledThreadPool(definition, name);
        }

        return null;
    }

    /**
     * The RestoreAction is used to track all the undo/restore actions
     * that need to be performed to undo any resolution to property placeholders
     * that have been applied to the camel route defs.  This class is private
     * so it does not get used directly.  It's mainly used by the {@see createPropertyPlaceholdersChangeReverter()}
     * method.
     */
    private static final class RestoreAction implements Runnable {

        private final RestoreAction prevChange;
        private final ArrayList<Runnable> actions = new ArrayList<Runnable>();

        private RestoreAction(RestoreAction prevChange) {
            this.prevChange = prevChange;
        }

        @Override
        public void run() {
            for (Runnable action : actions) {
                action.run();
            }
            actions.clear();
            if (prevChange == null) {
                CURRENT_RESTORE_ACTION.remove();
            } else {
                CURRENT_RESTORE_ACTION.set(prevChange);
            }
        }
    }

    /**
     * Creates a Runnable which when run will revert property placeholder
     * updates to the camel route definitions that were done after this method
     * is called.  The Runnable MUST be executed and MUST be executed in the
     * same thread this method is called from.  Therefore it's recommend you
     * use it in try/finally block like in the following example:
     * <p/>
     * <pre>
     *   Runnable undo = ProcessorDefinitionHelper.createPropertyPlaceholdersChangeReverter();
     *   try {
     *       // All property resolutions in this block will be reverted.
     *   } finally {
     *       undo.run();
     *   }
     * </pre>
     *
     * @return a Runnable that when run, will revert any property place holder
     * changes that occurred on the current thread .
     */
    public static Runnable createPropertyPlaceholdersChangeReverter() {
        RestoreAction prevChanges = CURRENT_RESTORE_ACTION.get();
        RestoreAction rc = new RestoreAction(prevChanges);
        CURRENT_RESTORE_ACTION.set(rc);
        return rc;
    }

    private static void addRestoreAction(final Object target, final Map<String, Object> properties) {
        if (properties.isEmpty()) {
            return;
        }

        RestoreAction restoreAction = CURRENT_RESTORE_ACTION.get();
        if (restoreAction == null) {
            return;
        }

        restoreAction.actions.add(new Runnable() {
            @Override
            public void run() {
                try {
                    IntrospectionSupport.setProperties(null, target, properties);
                } catch (Exception e) {
                    LOG.warn("Could not restore definition properties", e);
                }
            }
        });
    }

    public static void addPropertyPlaceholdersChangeRevertAction(Runnable action) {
        RestoreAction restoreAction = CURRENT_RESTORE_ACTION.get();
        if (restoreAction == null) {
            return;
        }

        restoreAction.actions.add(action);
    }

    /**
     * Inspects the given definition and resolves any property placeholders from its properties.
     * <p/>
     * This implementation will check all the getter/setter pairs on this instance and for all the values
     * (which is a String type) will be property placeholder resolved.
     *
     * @param routeContext the route context
     * @param definition   the definition
     * @throws Exception is thrown if property placeholders was used and there was an error resolving them
     * @see org.apache.camel.CamelContext#resolvePropertyPlaceholders(String)
     * @see org.apache.camel.component.properties.PropertiesComponent
     * @deprecated use {@link #resolvePropertyPlaceholders(org.apache.camel.CamelContext, Object)}
     */
    @Deprecated
    public static void resolvePropertyPlaceholders(RouteContext routeContext, Object definition) throws Exception {
        resolvePropertyPlaceholders(routeContext.getCamelContext(), definition);
    }

    /**
     * Inspects the given definition and resolves any property placeholders from its properties.
     * <p/>
     * This implementation will check all the getter/setter pairs on this instance and for all the values
     * (which is a String type) will be property placeholder resolved.
     *
     * @param camelContext the Camel context
     * @param definition   the definition
     * @throws Exception is thrown if property placeholders was used and there was an error resolving them
     * @see org.apache.camel.CamelContext#resolvePropertyPlaceholders(String)
     * @see org.apache.camel.component.properties.PropertiesComponent
     */
    public static void resolvePropertyPlaceholders(CamelContext camelContext, Object definition) throws Exception {
        LOG.trace("Resolving property placeholders for: {}", definition);

        // find all getter/setter which we can use for property placeholders
        Map<String, Object> properties = new HashMap<String, Object>();
        IntrospectionSupport.getProperties(definition, properties, null);

        ProcessorDefinition<?> processorDefinition = null;
        if (definition instanceof ProcessorDefinition) {
            processorDefinition = (ProcessorDefinition<?>) definition;
        }
        // include additional properties which have the Camel placeholder QName
        // and when the definition parameter is this (otherAttributes belong to this)
        if (processorDefinition != null && processorDefinition.getOtherAttributes() != null) {
            for (QName key : processorDefinition.getOtherAttributes().keySet()) {
                if (Constants.PLACEHOLDER_QNAME.equals(key.getNamespaceURI())) {
                    String local = key.getLocalPart();
                    Object value = processorDefinition.getOtherAttributes().get(key);
                    if (value != null && value instanceof String) {
                        // enforce a properties component to be created if none existed
                        CamelContextHelper.lookupPropertiesComponent(camelContext, true);

                        // value must be enclosed with placeholder tokens
                        String s = (String) value;
                        String prefixToken = camelContext.getPropertyPrefixToken();
                        String suffixToken = camelContext.getPropertySuffixToken();
                        if (prefixToken == null) {
                            throw new IllegalArgumentException("Property with name [" + local + "] uses property placeholders; however, no properties component is configured.");
                        }

                        if (!s.startsWith(prefixToken)) {
                            s = prefixToken + s;
                        }
                        if (!s.endsWith(suffixToken)) {
                            s = s + suffixToken;
                        }
                        value = s;
                    }
                    properties.put(local, value);
                }
            }
        }

        Map<String, Object> changedProperties = new HashMap<String, Object>();
        if (!properties.isEmpty()) {
            LOG.trace("There are {} properties on: {}", properties.size(), definition);
            // lookup and resolve properties for String based properties
            for (Map.Entry<String, Object> entry : properties.entrySet()) {
                // the name is always a String
                String name = entry.getKey();
                Object value = entry.getValue();
                if (value instanceof String) {
                    // value must be a String, as a String is the key for a property placeholder
                    String text = (String) value;
                    text = camelContext.resolvePropertyPlaceholders(text);
                    if (text != value) {
                        // invoke setter as the text has changed
                        boolean changed = IntrospectionSupport.setProperty(camelContext.getTypeConverter(), definition, name, text);
                        if (!changed) {
                            throw new IllegalArgumentException("No setter to set property: " + name + " to: " + text + " on: " + definition);
                        }
                        changedProperties.put(name, value);
                        if (LOG.isDebugEnabled()) {
                            LOG.debug("Changed property [{}] from: {} to: {}", new Object[]{name, value, text});
                        }
                    }
                }
            }
        }
        addRestoreAction(definition, changedProperties);
    }

    /**
     * Inspects the given definition and resolves known fields
     * <p/>
     * This implementation will check all the getter/setter pairs on this instance and for all the values
     * (which is a String type) will check if it refers to a known field (such as on Exchange).
     *
     * @param definition the definition
     */
    public static void resolveKnownConstantFields(Object definition) throws Exception {
        LOG.trace("Resolving known fields for: {}", definition);

        // find all String getter/setter
        Map<String, Object> properties = new HashMap<String, Object>();
        IntrospectionSupport.getProperties(definition, properties, null);

        Map<String, Object> changedProperties = new HashMap<String, Object>();
        if (!properties.isEmpty()) {
            LOG.trace("There are {} properties on: {}", properties.size(), definition);

            // lookup and resolve known constant fields for String based properties
            for (Map.Entry<String, Object> entry : properties.entrySet()) {
                String name = entry.getKey();
                Object value = entry.getValue();
                if (value instanceof String) {
                    // we can only resolve String typed values
                    String text = (String) value;

                    // is the value a known field (currently we only support constants from Exchange.class)
                    if (text.startsWith("Exchange.")) {
                        String field = ObjectHelper.after(text, "Exchange.");
                        String constant = ObjectHelper.lookupConstantFieldValue(Exchange.class, field);
                        if (constant != null) {
                            // invoke setter as the text has changed
                            IntrospectionSupport.setProperty(definition, name, constant);
                            changedProperties.put(name, value);
                            if (LOG.isDebugEnabled()) {
                                LOG.debug("Changed property [{}] from: {} to: {}", new Object[]{name, value, constant});
                            }
                        } else {
                            throw new IllegalArgumentException("Constant field with name: " + field + " not found on Exchange.class");
                        }
                    }
                }
            }
        }
        addRestoreAction(definition, changedProperties);
    }

}


File: camel-core/src/main/java/org/apache/camel/model/language/ExpressionDefinition.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.camel.model.language;

import java.util.List;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlAttribute;
import javax.xml.bind.annotation.XmlID;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlTransient;
import javax.xml.bind.annotation.XmlType;
import javax.xml.bind.annotation.XmlValue;
import javax.xml.bind.annotation.adapters.CollapsedStringAdapter;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;

import org.apache.camel.AfterPropertiesConfigured;
import org.apache.camel.CamelContext;
import org.apache.camel.Exchange;
import org.apache.camel.Expression;
import org.apache.camel.Predicate;
import org.apache.camel.spi.Language;
import org.apache.camel.spi.Metadata;
import org.apache.camel.spi.Required;
import org.apache.camel.spi.RouteContext;
import org.apache.camel.util.CollectionStringBuffer;
import org.apache.camel.util.ExpressionToPredicateAdapter;
import org.apache.camel.util.IntrospectionSupport;
import org.apache.camel.util.ObjectHelper;

/**
 * A useful base class for an expression
 */
@Metadata(label = "language", title = "Expression")
@XmlRootElement
@XmlType(name = "expression") // must be named expression
@XmlAccessorType(XmlAccessType.FIELD)
public class ExpressionDefinition implements Expression, Predicate {
    @XmlAttribute
    @XmlJavaTypeAdapter(CollapsedStringAdapter.class)
    @XmlID
    private String id;
    @XmlValue
    private String expression;
    @XmlAttribute @Metadata(defaultValue = "true")
    private Boolean trim;
    @XmlTransient
    private Predicate predicate;
    @XmlTransient
    private Expression expressionValue;
    @XmlTransient
    private ExpressionDefinition expressionType;

    public ExpressionDefinition() {
    }

    public ExpressionDefinition(String expression) {
        this.expression = expression;
    }

    public ExpressionDefinition(Predicate predicate) {
        this.predicate = predicate;
    }

    public ExpressionDefinition(Expression expression) {
        this.expressionValue = expression;
    }

    public static String getLabel(List<ExpressionDefinition> expressions) {
        CollectionStringBuffer buffer = new CollectionStringBuffer();
        for (ExpressionDefinition expression : expressions) {
            buffer.append(expression.getLabel());
        }
        return buffer.toString();
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        if (getLanguage() != null) {
            sb.append(getLanguage()).append("{");
        }
        if (getPredicate() != null) {
            sb.append(getPredicate().toString());
        }
        if (getExpressionValue() != null) {
            sb.append(getExpressionValue().toString());
        }
        if (getPredicate() == null && getExpressionValue() == null && getExpression() != null) {
            sb.append(getExpression());
        }
        if (getLanguage() != null) {
            sb.append("}");
        }
        return sb.toString();
    }

    public Object evaluate(Exchange exchange) {
        return evaluate(exchange, Object.class);
    }

    public <T> T evaluate(Exchange exchange, Class<T> type) {
        if (expressionValue == null) {
            expressionValue = createExpression(exchange.getContext());
        }
        ObjectHelper.notNull(expressionValue, "expressionValue");
        return expressionValue.evaluate(exchange, type);
    }

    public void assertMatches(String text, Exchange exchange) throws AssertionError {
        if (!matches(exchange)) {
            throw new AssertionError(text + getExpression() + " for exchange: " + exchange);
        }
    }

    public boolean matches(Exchange exchange) {
        if (predicate == null) {
            predicate = createPredicate(exchange.getContext());
        }
        ObjectHelper.notNull(predicate, "predicate");
        return predicate.matches(exchange);
    }

    public String getLanguage() {
        return "";
    }

    public final Predicate createPredicate(RouteContext routeContext) {
        return createPredicate(routeContext.getCamelContext());
    }

    public Predicate createPredicate(CamelContext camelContext) {
        if (predicate == null) {
            if (getExpressionType() != null) {
                predicate = getExpressionType().createPredicate(camelContext);
            } else if (getExpressionValue() != null) {
                predicate = new ExpressionToPredicateAdapter(getExpressionValue());
            } else if (getExpression() != null) {
                ObjectHelper.notNull("language", getLanguage());
                Language language = camelContext.resolveLanguage(getLanguage());
                String exp = getExpression();
                // should be true by default
                boolean isTrim = getTrim() == null || getTrim();
                // trim if configured to trim
                if (exp != null && isTrim) {
                    exp = exp.trim();
                }
                predicate = language.createPredicate(exp);
                configurePredicate(camelContext, predicate);
            }
        }
        return predicate;
    }

    public final Expression createExpression(RouteContext routeContext) {
        return createExpression(routeContext.getCamelContext());
    }

    public Expression createExpression(CamelContext camelContext) {
        if (getExpressionValue() == null) {
            if (getExpressionType() != null) {
                setExpressionValue(getExpressionType().createExpression(camelContext));
            } else if (getExpression() != null) {
                ObjectHelper.notNull("language", getLanguage());
                Language language = camelContext.resolveLanguage(getLanguage());
                String exp = getExpression();
                // should be true by default
                boolean isTrim = getTrim() == null || getTrim();
                // trim if configured to trim
                if (exp != null && isTrim) {
                    exp = exp.trim();
                }
                setExpressionValue(language.createExpression(exp));
                configureExpression(camelContext, getExpressionValue());
            }
        }
        return getExpressionValue();
    }

    public String getExpression() {
        return expression;
    }

    /**
     * The expression value in your chosen language syntax
     */
    @Required
    public void setExpression(String expression) {
        this.expression = expression;
    }

    public String getId() {
        return id;
    }

    /**
     * Sets the id of this node
     */
    public void setId(String value) {
        this.id = value;
    }

    public Predicate getPredicate() {
        return predicate;
    }

    public Expression getExpressionValue() {
        return expressionValue;
    }

    protected void setExpressionValue(Expression expressionValue) {
        this.expressionValue = expressionValue;
    }

    public ExpressionDefinition getExpressionType() {
        return expressionType;
    }

    public Boolean getTrim() {
        return trim;
    }

    /**
     * Whether to trim the value to remove leading and trailing whitespaces and line breaks
     */
    public void setTrim(Boolean trim) {
        this.trim = trim;
    }

    /**
     * Returns some descriptive text to describe this node
     */
    public String getLabel() {
        Predicate predicate = getPredicate();
        if (predicate != null) {
            return predicate.toString();
        }
        Expression expressionValue = getExpressionValue();
        if (expressionValue != null) {
            return expressionValue.toString();
        }

        String exp = getExpression();
        return exp != null ? exp : "";
    }

    /**
     * Allows derived classes to set a lazily created expressionType instance
     * such as if using the {@link org.apache.camel.builder.ExpressionClause}
     */
    protected void setExpressionType(ExpressionDefinition expressionType) {
        this.expressionType = expressionType;
    }

    @SuppressWarnings("unchecked")
    protected void configurePredicate(CamelContext camelContext, Predicate predicate) {
        // allows to perform additional logic after the properties has been configured which may be needed
        // in the various camel components outside camel-core
        if (predicate instanceof AfterPropertiesConfigured) {
            ((AfterPropertiesConfigured) predicate).afterPropertiesConfigured(camelContext);
        }
    }

    @SuppressWarnings("unchecked")
    protected void configureExpression(CamelContext camelContext, Expression expression) {
        // allows to perform additional logic after the properties has been configured which may be needed
        // in the various camel components outside camel-core
        if (expression instanceof AfterPropertiesConfigured) {
            ((AfterPropertiesConfigured) expression).afterPropertiesConfigured(camelContext);
        }
    }

    /**
     * Sets a named property on the object instance using introspection
     */
    protected void setProperty(Object bean, String name, Object value) {
        try {
            IntrospectionSupport.setProperty(bean, name, value);
        } catch (Exception e) {
            throw new IllegalArgumentException("Failed to set property " + name + " on " + bean
                                               + ". Reason: " + e, e);
        }
    }
}
