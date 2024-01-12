Refactoring Types: ['Move Class']
java/springfox/documentation/schema/DefaultModelProvider.java
/*
 *
 *  Copyright 2015 the original author or authors.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *
 */

package springfox.documentation.schema;

import com.fasterxml.classmate.ResolvedType;
import com.fasterxml.classmate.TypeResolver;
import com.google.common.base.Function;
import com.google.common.base.Joiner;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Iterables;
import com.google.common.collect.Multimaps;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;
import springfox.documentation.schema.plugins.SchemaPluginsManager;
import springfox.documentation.schema.property.provider.ModelPropertiesProvider;
import springfox.documentation.spi.schema.contexts.ModelContext;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.google.common.base.Functions.*;
import static com.google.common.base.Strings.*;
import static com.google.common.base.Suppliers.*;
import static com.google.common.collect.Maps.*;
import static springfox.documentation.builders.BuilderDefaults.*;
import static springfox.documentation.schema.Collections.*;
import static springfox.documentation.schema.Maps.*;
import static springfox.documentation.schema.ResolvedTypes.*;
import static springfox.documentation.schema.Types.*;


@Component
public class DefaultModelProvider implements ModelProvider {
  private static final Logger LOG = LoggerFactory.getLogger(DefaultModelProvider.class);
  private final TypeResolver resolver;
  private final ModelPropertiesProvider propertiesProvider;
  private final ModelDependencyProvider dependencyProvider;
  private final SchemaPluginsManager schemaPluginsManager;
  private final TypeNameExtractor typeNameExtractor;

  @Autowired
  public DefaultModelProvider(TypeResolver resolver,
                              @Qualifier("default") ModelPropertiesProvider propertiesProvider,
                              ModelDependencyProvider dependencyProvider,
                              SchemaPluginsManager schemaPluginsManager,
                              TypeNameExtractor typeNameExtractor) {
    this.resolver = resolver;
    this.propertiesProvider = propertiesProvider;
    this.dependencyProvider = dependencyProvider;
    this.schemaPluginsManager = schemaPluginsManager;
    this.typeNameExtractor = typeNameExtractor;
  }

  @Override
  public com.google.common.base.Optional<Model> modelFor(ModelContext modelContext) {
    ResolvedType propertiesHost = modelContext.alternateFor(modelContext.resolvedType(resolver));
    if (isContainerType(propertiesHost)
        || isMapType(propertiesHost)
        || propertiesHost.getErasedType().isEnum()
        || isBaseType(Types.typeNameFor(propertiesHost.getErasedType()))
        || modelContext.hasSeenBefore(propertiesHost)) {
      LOG.debug("Skipping model of type {} as its either a container type, map, enum or base type, or its already "
          + "been handled", resolvedTypeSignature(propertiesHost).or("<null>"));
      return Optional.absent();
    }
    Map<String, ModelProperty> properties = newTreeMap();
    ImmutableMap<String, Collection<ModelProperty>> propertiesIndex
        = Multimaps.index(properties(modelContext, propertiesHost), byPropertyName()).asMap();
    LOG.debug("Inferred {} properties. Properties found {}", propertiesIndex.size(),
        Joiner.on(", ").join(propertiesIndex.keySet()));
    for (Map.Entry<String, Collection<ModelProperty>> each : propertiesIndex.entrySet()) {
      properties.put(each.getKey(), merge(each.getValue()));
    }

    return Optional.of(modelBuilder(propertiesHost, properties, modelContext));
  }

  private ModelProperty merge(Collection<ModelProperty> propertyVariants) {
    ModelProperty merged = Iterables.getFirst(propertyVariants, null);
    for (ModelProperty each : Iterables.skip(propertyVariants, 1)) {
      boolean required = Optional.fromNullable(each.isRequired()).or(false) | merged.isRequired();
      merged = new ModelProperty(defaultIfAbsent(each.getName(), merged.getName()),
          defaultIfAbsent(each.getType(), merged.getType()),
          defaultIfAbsent(emptyToNull(each.getQualifiedType()), merged.getQualifiedType()),
          each.getPosition() > 0 ? each.getPosition() : merged.getPosition(),
          required,
          each.isHidden() | merged.isHidden(),
          defaultIfAbsent(emptyToNull(each.getDescription()), merged.getDescription()),
          defaultIfAbsent(each.getAllowableValues(), merged.getAllowableValues()));
      merged.updateModelRef(forSupplier(ofInstance(defaultIfAbsent(each.getModelRef(), merged.getModelRef()))));
    }
    return merged;
  }

  private Model modelBuilder(ResolvedType propertiesHost,
                             Map<String, ModelProperty> properties,
                             ModelContext modelContext) {
    String typeName = typeNameExtractor.typeName(ModelContext.fromParent(modelContext, propertiesHost));
    modelContext.getBuilder()
        .id(typeName)
        .type(propertiesHost)
        .name(typeName)
        .qualifiedType(ResolvedTypes.simpleQualifiedTypeName(propertiesHost))
        .properties(properties)
        .description("")
        .baseModel("")
        .discriminator("")
        .subTypes(new ArrayList<String>());
    return schemaPluginsManager.model(modelContext);
  }

  @Override
  public Map<String, Model> dependencies(ModelContext modelContext) {
    Map<String, Model> models = newHashMap();
    for (ResolvedType resolvedType : dependencyProvider.dependentModels(modelContext)) {
      ModelContext parentContext = ModelContext.fromParent(modelContext, resolvedType);
      Optional<Model> model = modelFor(parentContext).or(mapModel(parentContext, resolvedType));
      if (model.isPresent()) {
        models.put(model.get().getName(), model.get());
      }
    }
    return models;
  }

  private Optional<Model> mapModel(ModelContext parentContext, ResolvedType resolvedType) {
    if (isMapType(resolvedType) && !parentContext.hasSeenBefore(resolvedType)) {
      String typeName = typeNameExtractor.typeName(parentContext);
      return Optional.of(parentContext.getBuilder()
          .id(typeName)
          .type(resolvedType)
          .name(typeName)
          .qualifiedType(ResolvedTypes.simpleQualifiedTypeName(resolvedType))
          .properties(new HashMap<String, ModelProperty>())
          .description("")
          .baseModel("")
          .discriminator("")
          .subTypes(new ArrayList<String>())
          .build());
    }
    return Optional.absent();
  }

  private Function<ModelProperty, String> byPropertyName() {
    return new Function<ModelProperty, String>() {
      @Override
      public String apply(ModelProperty input) {
        return input.getName();
      }
    };
  }

  private List<ModelProperty> properties(ModelContext context, ResolvedType propertiesHost) {
    return propertiesProvider.propertiesFor(propertiesHost, context);
  }
}


File: springfox-schema/src/main/java/springfox/documentation/schema/ModelDependencyProvider.java
/*
 *
 *  Copyright 2015 the original author or authors.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *
 */

package springfox.documentation.schema;

import com.fasterxml.classmate.ResolvedType;
import com.fasterxml.classmate.TypeResolver;
import com.google.common.base.Predicate;
import com.google.common.collect.FluentIterable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;
import springfox.documentation.schema.property.provider.ModelPropertiesProvider;
import springfox.documentation.spi.schema.contexts.ModelContext;

import java.util.List;
import java.util.Set;

import static com.google.common.base.Predicates.*;
import static com.google.common.collect.FluentIterable.*;
import static com.google.common.collect.Lists.*;
import static springfox.documentation.schema.Collections.*;
import static springfox.documentation.schema.ResolvedTypes.*;

@Component
public class ModelDependencyProvider {

  private static final Logger LOG = LoggerFactory.getLogger(ModelDependencyProvider.class);
  private final TypeResolver typeResolver;
  private final ModelPropertiesProvider propertiesProvider;
  private final TypeNameExtractor nameExtractor;

  @Autowired
  public ModelDependencyProvider(TypeResolver typeResolver,
                                 @Qualifier("default") ModelPropertiesProvider propertiesProvider,
                                 TypeNameExtractor nameExtractor) {
    this.typeResolver = typeResolver;
    this.propertiesProvider = propertiesProvider;
    this.nameExtractor = nameExtractor;
  }

  public Set<ResolvedType> dependentModels(ModelContext modelContext) {
    return
            from(resolvedDependencies(modelContext))
            .filter(ignorableTypes(modelContext))
            .filter(not(baseTypes(modelContext)))
            .toSet();
  }

  private Predicate<ResolvedType> baseTypes(final ModelContext modelContext) {
    return new Predicate<ResolvedType>() {
      @Override
      public boolean apply(ResolvedType resolvedType) {
        return isBaseType(ModelContext.fromParent(modelContext, resolvedType));
      }
    };
  }

  private boolean isBaseType(ModelContext modelContext) {
    String typeName = nameExtractor.typeName(modelContext);
    return Types.isBaseType(typeName);
  }

  private Predicate<ResolvedType> ignorableTypes(final ModelContext modelContext) {
    return new Predicate<ResolvedType>() {
      @Override
      public boolean apply(ResolvedType input) {
        return !modelContext.hasSeenBefore(input);
      }
    };
  }


  private List<ResolvedType> resolvedDependencies(ModelContext modelContext) {
    ResolvedType resolvedType = modelContext.alternateFor(modelContext.resolvedType(typeResolver));
    if (isBaseType(ModelContext.fromParent(modelContext, resolvedType))) {
      LOG.debug("Marking base type {} as seen", resolvedType.getSignature());
      modelContext.seen(resolvedType);
      return newArrayList();
    }
    List<ResolvedType> dependencies = newArrayList(resolvedTypeParameters(modelContext, resolvedType));
    dependencies.addAll(resolvedPropertiesAndFields(modelContext, resolvedType));
    return dependencies;
  }

  private List<? extends ResolvedType> resolvedTypeParameters(ModelContext modelContext, ResolvedType resolvedType) {
    List<ResolvedType> parameters = newArrayList();
    for (ResolvedType parameter : resolvedType.getTypeParameters()) {
      LOG.debug("Adding type for parameter {}", parameter.getSignature());
      parameters.add(modelContext.alternateFor(parameter));
      LOG.debug("Recursively resolving dependencies for parameter {}", parameter.getSignature());
      parameters.addAll(resolvedDependencies(ModelContext.fromParent(modelContext, parameter)));
    }
    return parameters;
  }

  private List<ResolvedType> resolvedPropertiesAndFields(ModelContext modelContext, ResolvedType resolvedType) {
    if (modelContext.hasSeenBefore(resolvedType) || resolvedType.getErasedType().isEnum()) {
      return newArrayList();
    }
    modelContext.seen(resolvedType);
    List<ResolvedType> properties = newArrayList();
    for (ModelProperty property : nonTrivialProperties(modelContext, resolvedType)) {
      LOG.debug("Adding type {} for parameter {}", property.getType().getSignature(), property.getName());
      properties.add(property.getType());
      properties.addAll(maybeFromCollectionElementType(modelContext, property));
      properties.addAll(maybeFromMapValueType(modelContext, property));
      properties.addAll(maybeFromRegularType(modelContext, property));
    }
    return properties;
  }

  private FluentIterable<ModelProperty> nonTrivialProperties(ModelContext modelContext, ResolvedType resolvedType) {
    return from(propertiesFor(modelContext, resolvedType))
            .filter(not(baseProperty(modelContext)));
  }

  private Predicate<? super ModelProperty> baseProperty(final ModelContext modelContext) {
    return new Predicate<ModelProperty>() {
      @Override
      public boolean apply(ModelProperty input) {
        return isBaseType(ModelContext.fromParent(modelContext, input.getType()));
      }
    };
  }

  private List<ResolvedType> maybeFromRegularType(ModelContext modelContext, ModelProperty property) {
    if (isContainerType(property.getType()) || Maps.isMapType(property.getType())) {
      return newArrayList();
    }
    LOG.debug("Recursively resolving dependencies for type {}", resolvedTypeSignature(property.getType()).or("<null>"));
    return newArrayList(resolvedDependencies(ModelContext.fromParent(modelContext, property.getType())));
  }

  private List<ResolvedType> maybeFromCollectionElementType(ModelContext modelContext, ModelProperty property) {
    List<ResolvedType> dependencies = newArrayList();
    if (isContainerType(property.getType())) {
      ResolvedType collectionElementType = collectionElementType(property.getType());
      String resolvedTypeSignature = resolvedTypeSignature(collectionElementType).or("<null>");
      if (!isBaseType(ModelContext.fromParent(modelContext, collectionElementType))) {
        LOG.debug("Adding collectionElement type {}", resolvedTypeSignature);
        dependencies.add(collectionElementType);
      }
      LOG.debug("Recursively resolving dependencies for collectionElement type {}", resolvedTypeSignature);
      dependencies.addAll(resolvedDependencies(ModelContext.fromParent(modelContext, collectionElementType)));
    }
    return dependencies;
  }

  private List<ResolvedType> maybeFromMapValueType(ModelContext modelContext, ModelProperty property) {
    List<ResolvedType> dependencies = newArrayList();
    if (Maps.isMapType(property.getType())) {
      ResolvedType valueType = Maps.mapValueType(property.getType());
      String resolvedTypeSignature = resolvedTypeSignature(valueType).or("<null>");
      if (!isBaseType(ModelContext.fromParent(modelContext, valueType))) {
        LOG.debug("Adding value type {}", resolvedTypeSignature);
        dependencies.add(valueType);
      }
      LOG.debug("Recursively resolving dependencies for value type {}", resolvedTypeSignature);
      dependencies.addAll(resolvedDependencies(ModelContext.fromParent(modelContext, valueType)));
    }
    return dependencies;
  }

  private List<ModelProperty> propertiesFor(ModelContext modelContext, ResolvedType resolvedType) {
    return propertiesProvider.propertiesFor(resolvedType, modelContext);
  }


}


File: springfox-schema/src/main/java/springfox/documentation/schema/property/bean/BeanModelPropertyProvider.java
/*
 *
 *  Copyright 2015 the original author or authors.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *
 */

package springfox.documentation.schema.property.bean;

import com.fasterxml.classmate.ResolvedType;
import com.fasterxml.classmate.TypeResolver;
import com.fasterxml.classmate.members.ResolvedMethod;
import com.fasterxml.jackson.databind.BeanDescription;
import com.fasterxml.jackson.databind.DeserializationConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationConfig;
import com.fasterxml.jackson.databind.introspect.AnnotatedMember;
import com.fasterxml.jackson.databind.introspect.AnnotatedMethod;
import com.fasterxml.jackson.databind.introspect.BeanPropertyDefinition;
import com.fasterxml.jackson.databind.type.TypeFactory;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Optional;
import com.google.common.base.Predicate;
import com.google.common.collect.Iterables;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import springfox.documentation.builders.ModelPropertyBuilder;
import springfox.documentation.schema.Annotations;
import springfox.documentation.schema.ModelProperty;
import springfox.documentation.schema.TypeNameExtractor;
import springfox.documentation.schema.configuration.ObjectMapperConfigured;
import springfox.documentation.schema.plugins.SchemaPluginsManager;
import springfox.documentation.schema.property.BeanPropertyDefinitions;
import springfox.documentation.schema.property.BeanPropertyNamingStrategy;
import springfox.documentation.schema.property.provider.ModelPropertiesProvider;
import springfox.documentation.spi.schema.contexts.ModelContext;
import springfox.documentation.spi.schema.contexts.ModelPropertyContext;

import java.util.List;
import java.util.Map;

import static com.google.common.base.Predicates.*;
import static com.google.common.collect.FluentIterable.*;
import static com.google.common.collect.Lists.*;
import static com.google.common.collect.Maps.*;
import static springfox.documentation.schema.ResolvedTypes.*;
import static springfox.documentation.schema.property.BeanPropertyDefinitions.*;
import static springfox.documentation.spi.schema.contexts.ModelContext.*;

@Component
public class BeanModelPropertyProvider implements ModelPropertiesProvider {
  private static final Logger LOG = LoggerFactory.getLogger(BeanModelPropertyProvider.class);

  private final AccessorsProvider accessors;
  private final BeanPropertyNamingStrategy namingStrategy;
  private ObjectMapper objectMapper;
  private final TypeResolver typeResolver;
  private final SchemaPluginsManager schemaPluginsManager;
  private final TypeNameExtractor typeNameExtractor;

  @Autowired
  public BeanModelPropertyProvider(
      AccessorsProvider accessors,
      TypeResolver typeResolver,
      BeanPropertyNamingStrategy namingStrategy,
      SchemaPluginsManager schemaPluginsManager,
      TypeNameExtractor typeNameExtractor) {

    this.typeResolver = typeResolver;
    this.accessors = accessors;
    this.namingStrategy = namingStrategy;
    this.schemaPluginsManager = schemaPluginsManager;
    this.typeNameExtractor = typeNameExtractor;
  }

  @Override
  public void onApplicationEvent(ObjectMapperConfigured event) {
    this.objectMapper = event.getObjectMapper();
  }

  @Override
  public List<ModelProperty> propertiesFor(ResolvedType type, ModelContext givenContext) {

    List<ModelProperty> serializationCandidates = newArrayList();
    BeanDescription beanDescription = beanDescription(type, givenContext);
    Map<String, BeanPropertyDefinition> propertyLookup = uniqueIndex(beanDescription.findProperties(),
        BeanPropertyDefinitions.beanPropertyByInternalName());
    for (Map.Entry<String, BeanPropertyDefinition> each : propertyLookup.entrySet()) {
      LOG.debug("Reading property {}", each.getKey());
      BeanPropertyDefinition propertyDefinition = each.getValue();
      Optional<BeanPropertyDefinition> jacksonProperty
          = jacksonPropertyWithSameInternalName(beanDescription, propertyDefinition);
      AnnotatedMember member = propertyDefinition.getPrimaryMember();

      Optional<ResolvedMethod> accessor = findAccessorMethod(type, each.getKey(), member);
      if (accessor.isPresent()) {
        LOG.debug("Accessor selected {}", accessor.get().getName());
        serializationCandidates
            .addAll(candidateProperties(member, accessor.get(), jacksonProperty, givenContext));
      }
    }
    return serializationCandidates;
  }

  @VisibleForTesting
  List<ModelProperty> candidateProperties(AnnotatedMember member,
        ResolvedMethod childProperty,
        Optional<BeanPropertyDefinition> jacksonProperty,
        ModelContext givenContext) {

    if (member instanceof AnnotatedMethod && Annotations.memberIsUnwrapped(member)) {
      if (Accessors.isGetter(((AnnotatedMethod) member).getMember())) {
        LOG.debug("Evaluating unwrapped getter for member {}", ((AnnotatedMethod) member).getMember().getName());
        return propertiesFor(childProperty.getReturnType(), fromParent(givenContext, childProperty.getReturnType()));
      } else {
        LOG.debug("Evaluating unwrapped setter for member {}", ((AnnotatedMethod) member).getMember().getName());
        return propertiesFor(childProperty.getArgumentType(0),
            fromParent(givenContext, childProperty.getArgumentType(0)));
      }
    } else {
      LOG.debug("Evaluating property of {}", childProperty);
      return from(newArrayList(beanModelProperty(childProperty, jacksonProperty, givenContext)))
          .filter(not(ignorable(givenContext)))
          .toList();
    }
  }

  private BeanDescription beanDescription(ResolvedType type, ModelContext context) {
    if (context.isReturnType()) {
      SerializationConfig serializationConfig = objectMapper.getSerializationConfig();
      return serializationConfig.introspect(TypeFactory.defaultInstance()
          .constructType(type.getErasedType()));
    } else {
      DeserializationConfig serializationConfig = objectMapper.getDeserializationConfig();
      return serializationConfig.introspect(TypeFactory.defaultInstance()
          .constructType(type.getErasedType()));
    }
  }

  private Optional<ResolvedMethod> findAccessorMethod(ResolvedType resolvedType,
                                                      final String propertyName,
                                                      final AnnotatedMember member) {
    return Iterables.tryFind(accessors.in(resolvedType), new Predicate<ResolvedMethod>() {
      public boolean apply(ResolvedMethod accessorMethod) {
        return BeanModelProperty.accessorMemberIs(accessorMethod, Annotations.memberName(member))
            && propertyName.equals(Accessors.propertyName(accessorMethod.getRawMember()));
      }
    });
  }

  private ModelProperty beanModelProperty(ResolvedMethod childProperty, Optional<BeanPropertyDefinition>
      jacksonProperty, ModelContext modelContext) {

    BeanPropertyDefinition beanPropertyDefinition = jacksonProperty.get();
    String propertyName = BeanPropertyDefinitions.name(beanPropertyDefinition, modelContext.isReturnType(),
        namingStrategy);
    BeanModelProperty beanModelProperty
        = new BeanModelProperty(propertyName, childProperty, Accessors.isGetter(childProperty.getRawMember()),
        typeResolver, modelContext.getAlternateTypeProvider());

    LOG.debug("Adding property {} to model", propertyName);
    ModelPropertyBuilder propertyBuilder = new ModelPropertyBuilder()
        .name(beanModelProperty.getName())
        .type(beanModelProperty.getType())
        .qualifiedType(beanModelProperty.qualifiedTypeName())
        .position(beanModelProperty.position())
        .required(beanModelProperty.isRequired())
        .isHidden(false)
        .description(beanModelProperty.propertyDescription())
        .allowableValues(beanModelProperty.allowableValues());
    return schemaPluginsManager.property(
        new ModelPropertyContext(propertyBuilder,
            beanPropertyDefinition,
            typeResolver,
            modelContext.getDocumentationType()))
        .updateModelRef(modelRefFactory(modelContext, typeNameExtractor));
  }


}


File: springfox-schema/src/main/java/springfox/documentation/schema/property/constructor/ConstructorModelPropertyProvider.java
/*
 *
 *  Copyright 2015 the original author or authors.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *
 */

package springfox.documentation.schema.property.constructor;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import springfox.documentation.schema.TypeNameExtractor;
import springfox.documentation.schema.plugins.SchemaPluginsManager;
import springfox.documentation.schema.property.BeanPropertyNamingStrategy;
import springfox.documentation.schema.property.field.FieldModelPropertyProvider;
import springfox.documentation.schema.property.field.FieldProvider;
import springfox.documentation.schema.property.provider.ModelPropertiesProvider;

@Component
public class ConstructorModelPropertyProvider extends FieldModelPropertyProvider implements ModelPropertiesProvider {

  @Autowired
  public ConstructorModelPropertyProvider(
          FieldProvider fieldProvider,
          BeanPropertyNamingStrategy namingStrategy,
          SchemaPluginsManager schemaPluginsManager,
          TypeNameExtractor extractor) {

    super(fieldProvider, namingStrategy, schemaPluginsManager, extractor);
  }
}


File: springfox-schema/src/main/java/springfox/documentation/schema/property/field/FieldModelPropertyProvider.java
/*
 *
 *  Copyright 2015 the original author or authors.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *
 */

package springfox.documentation.schema.property.field;

import com.fasterxml.classmate.ResolvedType;
import com.fasterxml.classmate.TypeResolver;
import com.fasterxml.classmate.members.ResolvedField;
import com.fasterxml.jackson.databind.BeanDescription;
import com.fasterxml.jackson.databind.DeserializationConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationConfig;
import com.fasterxml.jackson.databind.introspect.AnnotatedMember;
import com.fasterxml.jackson.databind.introspect.BeanPropertyDefinition;
import com.fasterxml.jackson.databind.type.TypeFactory;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Optional;
import com.google.common.collect.Maps;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import springfox.documentation.builders.ModelPropertyBuilder;
import springfox.documentation.schema.Annotations;
import springfox.documentation.schema.ModelProperty;
import springfox.documentation.schema.TypeNameExtractor;
import springfox.documentation.schema.configuration.ObjectMapperConfigured;
import springfox.documentation.schema.plugins.SchemaPluginsManager;
import springfox.documentation.schema.property.BeanPropertyDefinitions;
import springfox.documentation.schema.property.BeanPropertyNamingStrategy;
import springfox.documentation.schema.property.provider.ModelPropertiesProvider;
import springfox.documentation.spi.schema.contexts.ModelContext;
import springfox.documentation.spi.schema.contexts.ModelPropertyContext;

import java.util.List;
import java.util.Map;

import static com.google.common.base.Predicates.*;
import static com.google.common.collect.FluentIterable.*;
import static com.google.common.collect.Lists.*;
import static springfox.documentation.schema.ResolvedTypes.*;
import static springfox.documentation.schema.property.BeanPropertyDefinitions.*;

@Component
public class FieldModelPropertyProvider implements ModelPropertiesProvider {
  private static final Logger LOG = LoggerFactory.getLogger(FieldModelPropertyProvider.class);

  private final FieldProvider fieldProvider;
  private final BeanPropertyNamingStrategy namingStrategy;
  private final SchemaPluginsManager schemaPluginsManager;
  private final TypeNameExtractor typeNameExtractor;
  protected ObjectMapper objectMapper;

  @Autowired
  public FieldModelPropertyProvider(
      FieldProvider fieldProvider,
      BeanPropertyNamingStrategy namingStrategy,
      SchemaPluginsManager schemaPluginsManager,
      TypeNameExtractor typeNameExtractor) {

    this.fieldProvider = fieldProvider;
    this.namingStrategy = namingStrategy;
    this.schemaPluginsManager = schemaPluginsManager;
    this.typeNameExtractor = typeNameExtractor;
  }

  @VisibleForTesting
  List<ModelProperty> serializationCandidates(AnnotatedMember member, ResolvedField
      childField, Optional<BeanPropertyDefinition> jacksonProperty, ModelContext givenContext) {
    if (Annotations.memberIsUnwrapped(member)) {
      LOG.debug("Evaluating unwrapped member");
      return propertiesFor(childField.getType(), ModelContext.fromParent(givenContext, childField.getType()));
    } else {
      String fieldName = BeanPropertyDefinitions.name(jacksonProperty.get(), true, namingStrategy);
      return from(newArrayList(modelPropertyFrom(childField, fieldName, givenContext)))
          .filter(not(ignorable(givenContext)))
          .toList();
    }
  }

  private ModelProperty modelPropertyFrom(ResolvedField childField, String fieldName,
      ModelContext modelContext) {
    FieldModelProperty fieldModelProperty = new FieldModelProperty(fieldName, childField,
        modelContext.getAlternateTypeProvider());
    ModelPropertyBuilder propertyBuilder = new ModelPropertyBuilder()
        .name(fieldModelProperty.getName())
        .type(fieldModelProperty.getType())
        .qualifiedType(fieldModelProperty.qualifiedTypeName())
        .position(fieldModelProperty.position())
        .required(fieldModelProperty.isRequired())
        .description(fieldModelProperty.propertyDescription())
        .allowableValues(fieldModelProperty.allowableValues());
    return schemaPluginsManager.property(
        new ModelPropertyContext(propertyBuilder,
            childField.getRawMember(),
            new TypeResolver(),
            modelContext.getDocumentationType()))
        .updateModelRef(modelRefFactory(modelContext, typeNameExtractor));
  }

  @Override
  public List<ModelProperty> propertiesFor(ResolvedType type, ModelContext givenContext) {

    List<ModelProperty> serializationCandidates = newArrayList();
    BeanDescription beanDescription = beanDescription(type, givenContext);
    Map<String, BeanPropertyDefinition> propertyLookup = Maps.uniqueIndex(beanDescription.findProperties(),
        BeanPropertyDefinitions.beanPropertyByInternalName());

    for (ResolvedField childField : fieldProvider.in(type)) {
      LOG.debug("Reading property {}", childField.getName());
      if (propertyLookup.containsKey(childField.getName())) {
        BeanPropertyDefinition propertyDefinition = propertyLookup.get(childField.getName());
        Optional<BeanPropertyDefinition> jacksonProperty
            = BeanPropertyDefinitions.jacksonPropertyWithSameInternalName(beanDescription, propertyDefinition);
        AnnotatedMember member = propertyDefinition.getField();
        serializationCandidates.addAll(
              newArrayList(serializationCandidates(member, childField, jacksonProperty, givenContext)));
      }
    }
    return serializationCandidates;
  }

  private BeanDescription beanDescription(ResolvedType type, ModelContext context) {
    if (context.isReturnType()) {
      SerializationConfig serializationConfig = objectMapper.getSerializationConfig();
      return serializationConfig.introspect(TypeFactory.defaultInstance()
          .constructType(type.getErasedType()));
    } else {
      DeserializationConfig serializationConfig = objectMapper.getDeserializationConfig();
      return serializationConfig.introspect(TypeFactory.defaultInstance()
          .constructType(type.getErasedType()));
    }
  }

  public void onApplicationEvent(ObjectMapperConfigured event) {
    this.objectMapper = event.getObjectMapper();
  }
}
