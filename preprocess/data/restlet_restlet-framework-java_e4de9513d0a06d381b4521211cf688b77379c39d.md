Refactoring Types: ['Move Method']
spark/src/org/restlet/ext/apispark/internal/conversion/raml/RamlUtils.java
/**
 * Copyright 2005-2014 Restlet
 * 
 * The contents of this file are subject to the terms of one of the following
 * open source licenses: Apache 2.0 or or EPL 1.0 (the "Licenses"). You can
 * select the license that you prefer but you may not use this file except in
 * compliance with one of these Licenses.
 * 
 * You can obtain a copy of the Apache 2.0 license at
 * http://www.opensource.org/licenses/apache-2.0
 * 
 * You can obtain a copy of the EPL 1.0 license at
 * http://www.opensource.org/licenses/eclipse-1.0
 * 
 * See the Licenses for the specific language governing permissions and
 * limitations under the Licenses.
 * 
 * Alternatively, you can obtain a royalty free commercial license with less
 * limitations, transferable or non-transferable, directly at
 * http://restlet.com/products/restlet-framework
 * 
 * Restlet is a registered trademark of Restlet S.A.S.
 */

package org.restlet.ext.apispark.internal.conversion.raml;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import org.raml.model.ActionType;
import org.raml.model.ParamType;
import org.raml.model.Raml;
import org.raml.model.Resource;
import org.raml.parser.rule.ValidationResult;
import org.raml.parser.visitor.RamlValidationService;
import org.restlet.engine.util.StringUtils;
import org.restlet.ext.apispark.internal.conversion.TranslationException;
import org.restlet.ext.apispark.internal.introspection.util.Types;
import org.restlet.ext.apispark.internal.model.Property;
import org.restlet.ext.apispark.internal.model.Representation;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.module.jsonSchema.JsonSchema;
import com.fasterxml.jackson.module.jsonSchema.types.ArraySchema;
import com.fasterxml.jackson.module.jsonSchema.types.BooleanSchema;
import com.fasterxml.jackson.module.jsonSchema.types.IntegerSchema;
import com.fasterxml.jackson.module.jsonSchema.types.NumberSchema;
import com.fasterxml.jackson.module.jsonSchema.types.ObjectSchema;
import com.fasterxml.jackson.module.jsonSchema.types.SimpleTypeSchema;
import com.fasterxml.jackson.module.jsonSchema.types.StringSchema;

/**
 * Utility class for RAML java beans.
 * 
 * @author Cyprien Quilici
 */
public class RamlUtils {
    /**
     * The list of java types that correspond to RAML's integer type.
     */
    private static final List<String> integerTypesList = Arrays.asList(
            "integer", "int");

    /**
     * The list of java types that correspond to RAML's number type.
     */
    private static final List<String> numericTypesList = Arrays.asList(
            "integer", "int", "double", "long", "float");

    /**
     * Generates the JsonSchema of a Representation's Property of primitive
     * type.
     * 
     * @param property
     *            The Property from which the JsonSchema is generated.
     * @return The JsonSchema of the given Property.
     */
    protected static SimpleTypeSchema generatePrimitiveSchema(Property property) {
        SimpleTypeSchema result = null;

        String name = property.getName();
        String type = (property.getType() != null) ? property.getType()
                .toLowerCase() : null;
        if (RamlUtils.integerTypesList.contains(type)) {
            IntegerSchema integerSchema = new IntegerSchema();
            integerSchema.setTitle(name);
            if (property.getMin() != null) {
                integerSchema.setMinimum(Double.parseDouble(property.getMin()));
            }
            if (property.getMax() != null) {
                integerSchema.setMaximum(Double.parseDouble(property.getMax()));
            }
            result = integerSchema;
        } else if (RamlUtils.numericTypesList.contains(type)) {
            NumberSchema numberSchema = new NumberSchema();
            numberSchema.setTitle(name);
            if (property.getMin() != null) {
                numberSchema.setMinimum(Double.parseDouble(property.getMin()));
            }
            if (property.getMax() != null) {
                numberSchema.setMaximum(Double.parseDouble(property.getMax()));
            }
            result = numberSchema;
        } else if ("boolean".equals(type)) {
            BooleanSchema booleanSchema = new BooleanSchema();
            booleanSchema.setTitle(name);
            result = booleanSchema;
        } else if ("string".equals(type) || "date".equals(type)) {
            StringSchema stringSchema = new StringSchema();
            stringSchema.setTitle(name);
            result = stringSchema;
        }

        return result;
    }

    /**
     * Generates the JsonSchema of a Representation.
     * 
     * @param representation
     *            The representation.
     * @param schemas
     * @param m
     * @throws JsonProcessingException
     */
    public static void fillSchemas(Representation representation,
            Map<String, String> schemas, ObjectMapper m)
            throws JsonProcessingException {
        fillSchemas(representation.getName(), representation.getDescription(),
                representation.isRaw(), representation.getExtendedType(),
                representation.getProperties(), schemas, m);
    }

    public static void fillSchemas(String name, String description,
            boolean isRaw, String extendedType, List<Property> properties,
            Map<String, String> schemas, ObjectMapper m)
            throws JsonProcessingException {
        ObjectSchema objectSchema = new ObjectSchema();
        objectSchema.setTitle(name);
        objectSchema.setDescription(description);
        if (!isRaw) {
            if (extendedType != null) {
                JsonSchema[] extended = new JsonSchema[1];
                SimpleTypeSchema typeExtended = new ObjectSchema();
                typeExtended.set$ref(extendedType);
                extended[0] = typeExtended;
                objectSchema.setExtends(extended);
            }
            objectSchema.setProperties(new HashMap<String, JsonSchema>());
            for (Property property : properties) {
                String type = property.getType();

                if (property.isList()) {
                    ArraySchema array = new ArraySchema();
                    array.setTitle(property.getName());
                    array.setRequired(property.isRequired());
                    array.setUniqueItems(property.isUniqueItems());
                    if (isPrimitiveType(type)) {
                        Property prop = new Property();
                        prop.setName(property.getName());
                        prop.setType(type);
                        array.setItemsSchema(generatePrimitiveSchema(prop));
                    } else {
                        if (Types.isCompositeType(type)) {
                            type = name + StringUtils.firstUpper(property.getName());
                            // add the new schema
                            fillSchemas(type, null, false, null,
                                    property.getProperties(), schemas, m);
                        }

                        SimpleTypeSchema reference = new ObjectSchema();
                        reference.set$ref("#/schemas/" + type);
                        array.setItemsSchema(reference);
                        // array.setItemsSchema(generateSchema(RamlTranslator
                        // .getRepresentationByName(representations,
                        // property.getType()), representations));
                    }
                    objectSchema.getProperties().put(array.getTitle(), array);
                } else if (isPrimitiveType(type)) {
                    SimpleTypeSchema primitive = generatePrimitiveSchema(property);
                    primitive.setRequired(property.getMinOccurs() > 0);
                    if (property.getDefaultValue() != null) {
                        primitive.setDefault(property.getDefaultValue());
                    }
                    objectSchema.getProperties().put(property.getName(),
                            primitive);
                } else {
                    if (Types.isCompositeType(type)) {
                        type = name + StringUtils.firstUpper(property.getName());
                        // add the new schema
                        fillSchemas(type, null, false, null,
                                property.getProperties(), schemas, m);
                    }

                    SimpleTypeSchema propertySchema = new ObjectSchema();
                    propertySchema.setTitle(property.getName());
                    propertySchema.set$ref("#/schemas/" + type);
                    propertySchema.setRequired(property.getMinOccurs() > 0);
                    objectSchema.getProperties().put(propertySchema.getTitle(),
                            propertySchema);
                }
            }

        }

        schemas.put(name, m.writeValueAsString(objectSchema));
    }

    /**
     * Returns the RAML {@link org.raml.model.ActionType} given an HTTP method
     * name.
     * 
     * @param method
     *            The HTTP method name as String.
     * @return The corresponding {@link org.raml.model.ActionType}.
     */
    public static ActionType getActionType(String method) {
        String m = (method != null) ? method.toLowerCase() : null;
        if ("post".equals(m)) {
            return ActionType.POST;
        } else if ("get".equals(m)) {
            return ActionType.GET;
        } else if ("put".equals(m)) {
            return ActionType.PUT;
        } else if ("patch".equals(m)) {
            return ActionType.PATCH;
        } else if ("delete".equals(m)) {
            return ActionType.DELETE;
        } else if ("head".equals(m)) {
            return ActionType.HEAD;
        } else if ("options".equals(m)) {
            return ActionType.OPTIONS;
        } else if ("trace".equals(m)) {
            return ActionType.TRACE;
        }
        return null;
    }

    /**
     * Returns the RAML parameter type given a java primitive type.
     * 
     * @param type
     *            The Java type.
     * @return The RAML parameter type.
     */
    public static ParamType getParamType(String type) {
        String t = (type != null) ? type.toLowerCase() : null;

        if (integerTypesList.contains(t)) {
            return ParamType.INTEGER;
        } else if (numericTypesList.contains(t)) {
            return ParamType.NUMBER;
        } else if ("boolean".equals(t)) {
            return ParamType.BOOLEAN;
        } else if ("date".equals(t)) {
            return ParamType.DATE;
        }

        // TODO add files
        // else if () {
        // return ParamType.FILE;
        // }
        return ParamType.STRING;
    }

    /**
     * Gets the parent resource of a Resource given its path and the list of
     * paths available on the API.
     * 
     * @param paths
     *            The list of paths available on the API.
     * @param resourcePath
     *            The path of the resource the parent resource is searched for.
     * @param raml
     *            The RAML representing the API.
     * @return The parent resource.
     */
    public static Resource getParentResource(List<String> paths,
            String resourcePath, Raml raml) {
        List<String> parentPaths = new ArrayList<String>();
        parentPaths.addAll(paths);
        parentPaths.add(resourcePath);
        Collections.sort(parentPaths);
        int index = parentPaths.indexOf(resourcePath);
        if (index != 0) {
            String parentPath = parentPaths.get(index - 1);
            if (resourcePath.startsWith(parentPath)) {
                return getResourceByCompletePath(raml, parentPath);
            }
        }
        return null;
    }

    /**
     * Returns a RAML Resource given its complete path.
     * 
     * @param raml
     *            The RAML in which the Resource is searched for.
     * @param path
     *            The complete path of the resource.
     * @return The Resource.
     */
    private static Resource getResourceByCompletePath(Raml raml, String path) {
        for (Entry<String, Resource> entry : raml.getResources().entrySet()) {
            if (path.equals(entry.getValue().getParentUri()
                    + entry.getValue().getRelativeUri())) {
                return entry.getValue();
            }
        }
        return null;
    }

    /**
     * Indicates if the given type is a primitive type.
     * 
     * @param type
     *            The type to check.
     * @return True if the given type is primitive, false otherwise.
     */
    public static boolean isPrimitiveType(String type) {
        String t = (type != null) ? type.toLowerCase() : null;
        return ("string".equals(t) || "int".equals(t) || "integer".equals(t)
                || "long".equals(t) || "float".equals(t) || "double".equals(t)
                || "date".equals(t) || "boolean".equals(t) || "bool".equals(t));
    }

    /**
     * Returns the primitive type as RAML expects them.
     * 
     * @param type
     *            The Java primitive type.
     * @return The primitive type expected by RAML.
     */
    public static String toRamlType(String type) {
        if ("Integer".equals(type)) {
            return "int";
        } else if ("String".equals(type)) {
            return "string";
        } else if ("Boolean".equals(type)) {
            return "boolean";
        }

        return type;
    }

    /**
     * Indicates if the given RAML definition is valid according to RAML
     * specifications.
     * 
     * @param location
     *            The RAML definition.
     * @throws TranslationException
     */
    public static List<ValidationResult> validate(String location)
            throws TranslationException {
        // TODO see if needed as it requires lots of dependencies.
        return RamlValidationService.createDefault().validate(location);
    }
}


File: modules/org.restlet.ext.apispark/src/org/restlet/ext/apispark/internal/conversion/swagger/v1_2/SwaggerReader.java
/**
 * Copyright 2005-2014 Restlet
 * 
 * The contents of this file are subject to the terms of one of the following
 * open source licenses: Apache 2.0 or or EPL 1.0 (the "Licenses"). You can
 * select the license that you prefer but you may not use this file except in
 * compliance with one of these Licenses.
 * 
 * You can obtain a copy of the Apache 2.0 license at
 * http://www.opensource.org/licenses/apache-2.0
 * 
 * You can obtain a copy of the EPL 1.0 license at
 * http://www.opensource.org/licenses/eclipse-1.0
 * 
 * See the Licenses for the specific language governing permissions and
 * limitations under the Licenses.
 * 
 * Alternatively, you can obtain a royalty free commercial license with less
 * limitations, transferable or non-transferable, directly at
 * http://restlet.com/products/restlet-framework
 * 
 * Restlet is a registered trademark of Restlet S.A.S.
 */

package org.restlet.ext.apispark.internal.conversion.swagger.v1_2;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.restlet.data.ChallengeScheme;
import org.restlet.data.Status;
import org.restlet.engine.util.StringUtils;
import org.restlet.ext.apispark.internal.conversion.TranslationException;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ApiDeclaration;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.AuthorizationsDeclaration;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ModelDeclaration;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ResourceDeclaration;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ResourceListing;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ResourceListingApi;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ResourceOperationDeclaration;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ResourceOperationParameterDeclaration;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ResponseMessageDeclaration;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.TypePropertyDeclaration;
import org.restlet.ext.apispark.internal.model.Contact;
import org.restlet.ext.apispark.internal.model.Contract;
import org.restlet.ext.apispark.internal.model.Definition;
import org.restlet.ext.apispark.internal.model.Endpoint;
import org.restlet.ext.apispark.internal.model.License;
import org.restlet.ext.apispark.internal.model.Operation;
import org.restlet.ext.apispark.internal.model.PathVariable;
import org.restlet.ext.apispark.internal.model.PayLoad;
import org.restlet.ext.apispark.internal.model.Property;
import org.restlet.ext.apispark.internal.model.QueryParameter;
import org.restlet.ext.apispark.internal.model.Representation;
import org.restlet.ext.apispark.internal.model.Resource;
import org.restlet.ext.apispark.internal.model.Response;
import org.restlet.ext.apispark.internal.model.Section;

/**
 * Tool library for converting Restlet Web API Definition from Swagger
 * documentation.
 * 
 * @author Cyprien Quilici
 */
public class SwaggerReader {

    /** Internal logger. */
    protected static Logger LOGGER = Logger.getLogger(SwaggerReader.class
            .getName());

    /**
     * Private constructor to ensure that the class acts as a true utility class
     * i.e. it isn't instantiable and extensible.
     */
    private SwaggerReader() {
    }

    /**
     * Fills Restlet Web API definition's Contract from Swagger 1.2 {@link ApiDeclaration}.
     * 
     * @param contract
     *            The Restlet Web API definition's Contract
     * @param apiDeclaration
     *            The Swagger ApiDeclaration
     * @param declaredTypes
     *            The names of the representations already imported into the {@link Contract}.
     * @param sectionName
     *            Optional name of the section in which to import the {@link ApiDeclaration}.
     * @param sectionDescription
     *            Optional description of the section in which to import the {@link ApiDeclaration}.
     */
    private static void fillContract(Contract contract, ApiDeclaration apiDeclaration,
            List<String> declaredTypes, String sectionName, String sectionDescription) {
        Resource resource;
        Section section = null;

        if (!StringUtils.isNullOrEmpty(sectionName)) {
            section = new Section(sectionName);
            section.setDescription(sectionDescription);
            contract.getSections().add(section);
        }

        for (ResourceDeclaration api : apiDeclaration.getApis()) {
            resource = new Resource();
            resource.setResourcePath(api.getPath());

            List<String> declaredPathVariables = new ArrayList<>();
            fillOperations(resource, apiDeclaration, api, contract, section,
                    declaredPathVariables, declaredTypes);

            if (section != null) {
                resource.getSections().add(section.getName());
            }

            contract.getResources().add(resource);
            LOGGER.log(Level.FINE, "Resource " + api.getPath() + " added.");
        }
    }

    /**
     * Fills Restlet Web API definition's Contract from Swagger 1.2 definition
     * 
     * @param contract
     *            The Restlet Web API definition's Contract
     * @param listing
     *            The Swagger ResourceListing
     * @param apiDeclarations
     *            The Swagger ApiDeclaration
     */
    private static void fillContract(Contract contract,
            ResourceListing listing, Map<String, ApiDeclaration> apiDeclarations) {

        List<String> declaredTypes = new ArrayList<>();
        for (Entry<String, ApiDeclaration> entry : apiDeclarations.entrySet()) {
            ApiDeclaration apiDeclaration = entry.getValue();

            String sectionName = entry.getKey();
            if (!StringUtils.isNullOrEmpty(sectionName)) {
                fillContract(contract, apiDeclaration, declaredTypes,
                        sectionName.startsWith("/") ? sectionName.substring(1) : sectionName,
                        listing.getApi(sectionName).getDescription());
            } else {
                fillContract(contract, apiDeclaration, declaredTypes, null, null);
            }
        }
    }

    /**
     * Fills Restlet Web API definition's main attributes from Swagger 1.2
     * definition
     * 
     * @param definition
     *            The Restlet Web API definition
     * @param listing
     *            The Swagger 1.2 resource listing
     * @param basePath
     *            The basePath of the described Web API
     */
    private static void fillMainAttributes(Definition definition,
            ResourceListing listing, String basePath) {
        definition.setVersion(listing.getApiVersion());

        Contract contract = new Contract();
        if (listing.getInfo() != null) {
            Contact contact = new Contact();
            contact.setEmail(listing.getInfo().getContact());
            definition.setContact(contact);

            License license = new License();
            license.setName(listing.getInfo().getLicense());
            license.setUrl(listing.getInfo().getLicenseUrl());
            definition.setLicense(license);

            contract.setName(listing.getInfo().getTitle());
            contract.setDescription(listing.getInfo().getDescription());
        }

        LOGGER.log(Level.FINE, "Contract " + contract.getName() + " added.");
        definition.setContract(contract);

        if (definition.getEndpoints().isEmpty() && basePath != null) {
            // TODO verify how to deal with API key auth + oauth
            Endpoint endpoint = new Endpoint(basePath);
            definition.getEndpoints().add(endpoint);
            fillEndpointAuthorization(listing.getAuthorizations(), endpoint);
        }
    }

    private static void fillEndpointAuthorization(AuthorizationsDeclaration authorizations, Endpoint endpoint) {
        if (authorizations != null) {
            if (authorizations.getBasicAuth() != null) {
                endpoint.setAuthenticationProtocol(ChallengeScheme.HTTP_BASIC
                        .getName());
            } else if (authorizations.getOauth2() != null) {
                endpoint.setAuthenticationProtocol(ChallengeScheme.HTTP_OAUTH
                        .getName());
            } else if (authorizations.getApiKey() != null) {
                endpoint.setAuthenticationProtocol(ChallengeScheme.CUSTOM
                        .getName());
            }
        }
    }

    /**
     * Fills Restlet Web API definition's Operations from Swagger ApiDeclaration
     * 
     * @param resource
     *            The Restlet Web API definition's Resource
     * @param apiDeclaration
     *            The Swagger ApiDeclaration
     * @param api
     *            The Swagger ResourceDeclaration
     * @param contract
     *            The Restlet Web API definition's Contract
     * @param section
     *            The Restlet Web API definition's current Section
     * @param declaredPathVariables
     *            The list of all declared path variables for the Resource
     * @param declaredTypes
     *            The list of all declared types for the Contract
     */
    private static void fillOperations(Resource resource,
            ApiDeclaration apiDeclaration, ResourceDeclaration api,
            Contract contract, Section section,
            List<String> declaredPathVariables, List<String> declaredTypes) {

        List<String> apiProduces = apiDeclaration.getProduces();
        List<String> apiConsumes = apiDeclaration.getConsumes();
        Map<String, List<String>> subtypes = new LinkedHashMap<>();
        Representation representation;

        // Operations listing
        Operation operation;
        for (ResourceOperationDeclaration swaggerOperation : api
                .getOperations()) {
            String methodName = swaggerOperation.getMethod();
            operation = new Operation();
            operation.setMethod(swaggerOperation.getMethod());
            operation.setName(swaggerOperation.getNickname());
            operation.setDescription(swaggerOperation.getSummary());

            // fill produced and consumed variants
            fillVariants(operation, swaggerOperation,
                    apiProduces, apiConsumes);

            // Extract success response message
            Response success = new Response();
            success.setCode(Status.SUCCESS_OK.getCode());
            success.setDescription("Success");
            success.setMessage(Status.SUCCESS_OK.getDescription());
            success.setName("Success");

            // fill output payload
            fillOutPayLoad(success, swaggerOperation);
            operation.getResponses().add(success);

            // fill parameters
            fillParameters(resource, operation, swaggerOperation,
                    declaredPathVariables);

            // fill responses
            fillResponseMessages(operation, swaggerOperation);

            resource.getOperations().add(operation);
            LOGGER.log(Level.FINE, "Method " + methodName + " added.");

            // fill representations
            fillRepresentations(contract, section, apiDeclaration, subtypes,
                    declaredTypes);

            // Deal with subtyping
            for (Entry<String, List<String>> subtypesPair : subtypes.entrySet()) {
                List<String> subtypesOf = subtypesPair.getValue();
                for (String subtypeOf : subtypesOf) {
                    representation = contract.getRepresentation(subtypeOf);
                    representation.setExtendedType(subtypesPair.getKey());
                }
            }
        }
    }

    /**
     * Fills Restlet Web API definition's operation output payload from Swagger
     * ResourceOperationDeclaration
     * 
     * @param success
     *            The Restlet Web API definition's operation success Response
     * @param swaggerOperation
     *            The Swagger ResourceOperationDeclaration
     */
    private static void fillOutPayLoad(Response success,
            ResourceOperationDeclaration swaggerOperation) {
        // Set response's entity
        PayLoad rwadOutRepr = new PayLoad();
        if ("array".equals(swaggerOperation.getType())) {
            LOGGER.log(Level.FINER,
                    "Operation: " + swaggerOperation.getNickname()
                            + " returns an array");
            rwadOutRepr.setArray(true);
            if (swaggerOperation.getItems().getType() != null) {
                rwadOutRepr.setType(swaggerOperation.getItems().getType());
            } else {
                rwadOutRepr.setType(swaggerOperation.getItems().getRef());
            }
        } else {
            LOGGER.log(Level.FINER,
                    "Operation: " + swaggerOperation.getNickname()
                            + " returns a single Representation");
            rwadOutRepr.setArray(false);
            if (swaggerOperation.getType() != null
                    && !"void".equals(swaggerOperation.getType())) {
                rwadOutRepr.setType(swaggerOperation.getType());
            } else {
                rwadOutRepr.setType(swaggerOperation.getRef());
            }
        }
        success.setOutputPayLoad(rwadOutRepr);
    }

    /**
     * Fills Restlet Web API definition's operation parameter from Swagger
     * ResourceOperationDeclaration
     * 
     * @param resource
     *            The Restlet Web API definition's Resource to which the
     *            operation is attached
     * @param operation
     *            The Restlet Web API definition's Operation
     * @param swaggerOperation
     *            The Swagger ResourceOperationDeclaration
     * @param declaredPathVariables
     *            The list of declared pathVariable on the resource
     */
    private static void fillParameters(Resource resource, Operation operation,
            ResourceOperationDeclaration swaggerOperation,
            List<String> declaredPathVariables) {
        // Loop over Swagger parameters.
        for (ResourceOperationParameterDeclaration param : swaggerOperation
                .getParameters()) {
            if ("path".equals(param.getParamType())) {
                if (!declaredPathVariables.contains(param.getName())) {
                    declaredPathVariables.add(param.getName());
                    PathVariable pathVariable = toPathVariable(param);
                    resource.getPathVariables().add(pathVariable);
                }
            } else if ("body".equals(param.getParamType())) {
                if (operation.getInputPayLoad() == null) {
                    PayLoad rwadInRepr = toEntity(param);
                    operation.setInputPayLoad(rwadInRepr);
                }
            } else if ("query".equals(param.getParamType())) {
                QueryParameter rwadQueryParam = toQueryParameter(param);
                operation.getQueryParameters().add(rwadQueryParam);
            }
        }
    }

    /**
     * Fills Restlet Web API definition's Representations from Swagger
     * ApiDeclaration
     * 
     * @param contract
     *            The Restlet Web API definition's Contract
     * @param section
     *            The Restlet Web API definition's current Section
     * @param apiDeclaration
     *            The Swagger ApiDeclaration
     * @param subtypes
     *            The list of this Representation's subtypes
     * @param declaredTypes
     *            The list of all declared types for the Contract
     */
    private static void fillRepresentations(Contract contract, Section section,
            ApiDeclaration apiDeclaration, Map<String, List<String>> subtypes,
            List<String> declaredTypes) {
        // Add representations
        Representation representation;
        for (Entry<String, ModelDeclaration> modelEntry : apiDeclaration
                .getModels().entrySet()) {
            ModelDeclaration model = modelEntry.getValue();
            if (model.getSubTypes() != null && !model.getSubTypes().isEmpty()) {
                subtypes.put(model.getId(), model.getSubTypes());
            }
            if (!declaredTypes.contains(modelEntry.getKey())) {
                declaredTypes.add(modelEntry.getKey());
                representation = toRepresentation(model, modelEntry.getKey());

                if (section != null) {
                    representation.addSection(section.getName());
                }

                contract.getRepresentations().add(representation);
                LOGGER.log(Level.FINE, "Representation " + modelEntry.getKey()
                        + " added.");
            }
        }
    }

    /**
     * Fills Restlet Web API definition's operation Responses from Swagger
     * ResourceOperationDeclaration
     * 
     * @param operation
     *            The Restlet Web API definition's Operation
     * @param swaggerOperation
     *            The Swagger ResourceOperationDeclaration
     */
    private static void fillResponseMessages(Operation operation,
            ResourceOperationDeclaration swaggerOperation) {
        // Set error response messages
        if (swaggerOperation.getResponseMessages() != null) {
            for (ResponseMessageDeclaration swagResponse : swaggerOperation
                    .getResponseMessages()) {
                Response response = new Response();
                PayLoad outputPayLoad = new PayLoad();
                outputPayLoad.setType(swagResponse.getResponseModel());
                response.setOutputPayLoad(outputPayLoad);
                response.setName("Error " + swagResponse.getCode());
                response.setCode(swagResponse.getCode());
                response.setMessage(swagResponse.getMessage());
                operation.getResponses().add(response);
            }
        }
    }

    /**
     * Fills Restlet Web API definition's variants from Swagger 1.2 definition
     * 
     * @param operation
     *            The Restlet Web API definition's Operation
     * @param swaggerOperation
     *            The Swagger ResourceOperationDeclaration
     * @param apiProduces
     *            The list of media types produced by the operation
     * @param apiConsumes
     *            The list of media types consumed by the operation
     */
    private static void fillVariants(Operation operation, ResourceOperationDeclaration swaggerOperation,
            List<String> apiProduces, List<String> apiConsumes) {
        // Set variants
        for (String produced : apiProduces.isEmpty() ? swaggerOperation
                .getProduces() : apiProduces) {
            operation.getProduces().add(produced);
        }

        for (String consumed : apiConsumes.isEmpty() ? swaggerOperation
                .getConsumes() : apiConsumes) {
            operation.getConsumes().add(consumed);
        }
    }

    /**
     * Converts a Swagger parameter to an instance of
     * {@link org.restlet.ext.apispark.internal.model.PayLoad}.
     * 
     * @param parameter
     *            The Swagger parameter.
     * @return An instance of
     *         {@link org.restlet.ext.apispark.internal.model.PayLoad}.
     */
    private static PayLoad toEntity(
            ResourceOperationParameterDeclaration parameter) {
        PayLoad result = new PayLoad();
        if ("array".equals(parameter.getType())) {
            result.setArray(true);
            if (parameter.getItems() != null
                    && parameter.getItems().getType() != null) {
                result.setType(parameter.getItems().getType());
            } else if (parameter.getItems() != null) {
                result.setType(parameter.getItems().getRef());
            }
        } else {
            result.setArray(false);
            result.setType(parameter.getType());
        }
        return result;
    }

    /**
     * Converts a Swagger parameter to an instance of
     * {@link org.restlet.ext.apispark.internal.model.PathVariable}.
     * 
     * @param parameter
     *            The Swagger parameter.
     * @return An instance of
     *         {@link org.restlet.ext.apispark.internal.model.PathVariable}.
     */
    private static PathVariable toPathVariable(
            ResourceOperationParameterDeclaration parameter) {
        PathVariable result = new PathVariable();
        result.setName(parameter.getName());
        result.setDescription(parameter.getDescription());
        result.setType(SwaggerTypes.toDefinitionType(new SwaggerTypeFormat(
                parameter.getType(), parameter.getFormat())));
        return result;
    }

    /**
     * Converts a Swagger parameter to an instance of
     * {@link org.restlet.ext.apispark.internal.model.QueryParameter}.
     * 
     * @param parameter
     *            The Swagger parameter.
     * @return An instance of
     *         {@link org.restlet.ext.apispark.internal.model.QueryParameter}.
     */
    private static QueryParameter toQueryParameter(
            ResourceOperationParameterDeclaration parameter) {
        QueryParameter result = new QueryParameter();
        result.setName(parameter.getName());
        result.setDescription(parameter.getDescription());
        result.setRequired(parameter.isRequired());
        result.setAllowMultiple(parameter.isAllowMultiple());
        result.setDefaultValue(parameter.getDefaultValue());
        if (parameter.getEnum_() != null && !parameter.getEnum_().isEmpty()) {
            result.setEnumeration(new ArrayList<String>());
            for (String value : parameter.getEnum_()) {
                result.getEnumeration().add(value);
            }
        }
        return result;
    }

    /**
     * Converts a Swagger model to an instance of
     * {@link org.restlet.ext.apispark.internal.model.Representation}.
     * 
     * @param model
     *            The Swagger model.
     * @param name
     *            The name of the representation.
     * @return An instance of
     *         {@link org.restlet.ext.apispark.internal.model.Representation}.
     */
    private static Representation toRepresentation(ModelDeclaration model,
            String name) {
        Representation result = new Representation();
        result.setName(name);
        result.setDescription(model.getDescription());

        // Set properties
        for (Entry<String, TypePropertyDeclaration> swagProperties : model
                .getProperties().entrySet()) {
            TypePropertyDeclaration swagProperty = swagProperties.getValue();
            Property property = new Property();
            property.setName(swagProperties.getKey());

            // Set property's type
            boolean isArray = "array".equals(swagProperty.getType());
            if (isArray) {
                property.setType(swagProperty.getItems().getType() != null ? swagProperty
                        .getItems().getType() : swagProperty.getItems()
                        .getRef());
            } else if (swagProperty.getType() != null) {
                property.setType(swagProperty.getType());
            } else if (swagProperty.getRef() != null) {
                property.setType(swagProperty.getRef());
            }

            if (model.getRequired() != null) {
                boolean required = model.getRequired().contains(swagProperties.getKey());
                property.setRequired(required);
            } else {
                property.setRequired(false);
            }
            property.setList(isArray);
            property.setDescription(swagProperty.getDescription());
            property.setUniqueItems(swagProperty.isUniqueItems());

            result.getProperties().add(property);
            LOGGER.log(Level.FINE, "Property " + property.getName() + " added.");
        }
        return result;
    }

    /**
     * Translates a Swagger API declaration to a Restlet Web API definition.
     * 
     * @param apiDeclaration
     *            The Swagger API declaration
     * @param sectionName
     *            Optional name of the section to add to the contract
     * @return the Restlet Web API definition
     * @throws TranslationException
     */
    public static Definition translate(ApiDeclaration apiDeclaration, String sectionName)
            throws TranslationException {
        try {
            Definition definition = new Definition();
            definition.setContract(new Contract());
            Endpoint endpoint = new Endpoint(apiDeclaration.getBasePath());
            definition.getEndpoints().add(endpoint);
            fillEndpointAuthorization(apiDeclaration.getAuthorizations(), endpoint);

            Contract contract = definition.getContract();
            fillContract(contract, apiDeclaration, new ArrayList<String>(), null, null);

            for (Representation representation : contract.getRepresentations()) {
                representation.addSectionsToProperties(contract);
            }

            LOGGER.log(Level.FINE,
                    "Definition successfully retrieved from Swagger definition");
            return definition;
        } catch (Exception e) {
            throw new TranslationException(
                    "compliance",
                    "Impossible to read your API definition, check your Swagger specs compliance",
                    e);
        }
    }

    /**
     * Translates a Swagger documentation to a Restlet definition.
     * 
     * @param listing
     *            The Swagger resource listing.
     * @param apiDeclarations
     *            The list of Swagger API declarations.
     * @return The Restlet definition.
     * @throws org.restlet.ext.apispark.internal.conversion.TranslationException
     */
    public static Definition translate(ResourceListing listing, Map<String, ApiDeclaration> apiDeclarations)
            throws TranslationException {

        validate(listing, apiDeclarations);

        try {
            Definition definition = new Definition();

            // fill main attributes of the Restlet Web API definition
            String basePath = null;

            List<ResourceListingApi> apis = listing.getApis();
            if (apis != null && !apis.isEmpty()) {
                String key = apis.get(0).getPath();
                ApiDeclaration firstApiDeclaration = apiDeclarations.get(key);
                basePath = firstApiDeclaration.getBasePath();
            }

            fillMainAttributes(definition, listing, basePath);

            Contract contract = definition.getContract();
            fillContract(contract, listing, apiDeclarations);

            for (Representation representation : contract.getRepresentations()) {
                representation.addSectionsToProperties(contract);
            }

            LOGGER.log(Level.FINE,
                    "Definition successfully retrieved from Swagger definition");
            return definition;
        } catch (Exception e) {
            throw new TranslationException(
                    "compliance",
                    "Impossible to read your API definition, check your Swagger specs compliance",
                    e);
        }
    }
    
    /**
     * Translates a Swagger Resource Listing to a Restlet definition.
     * 
     * @param listing
     *            The Swagger resource listing.
     * @return The Restlet definition.
     * @throws org.restlet.ext.apispark.internal.conversion.TranslationException
     */
    public static Definition translate(ResourceListing listing) {
        Definition definition = new Definition();
        fillMainAttributes(definition, listing, null);

        Contract contract = definition.getContract();
        fillSections(contract, listing);

        LOGGER.log(Level.FINE,
                "Main attributes successfully retrieved from Swagger resource listing.");
        return definition;
    }
            

    private static void fillSections(Contract contract, ResourceListing listing) {
        for (ResourceListingApi api : listing.getApis()) {
            Section section = new Section();
            String sectionName = computeSectionName(api.getPath());
            section.setName(sectionName);
            section.setDescription(api.getDescription());

            contract.getSections().add(section);
        }
    }

    private static String computeSectionName(String apiDeclarationPath) {
        String result = apiDeclarationPath;
        if (result.startsWith("/")) {
            result = result.substring(1);
        }

        return result.replaceAll("/", "_");
    }

    /**
     * Indicates if the given resource listing and list of API declarations
     * match.
     * 
     * @param resourceListing
     *            The Swagger resource listing.
     * @param apiDeclarations
     *            The list of Swagger API declarations.
     * @throws org.restlet.ext.apispark.internal.conversion.TranslationException
     */
    private static void validate(ResourceListing resourceListing,
            Map<String, ApiDeclaration> apiDeclarations)
            throws TranslationException {
        int rlSize = resourceListing.getApis().size();
        int adSize = apiDeclarations.size();
        if (rlSize < adSize) {
            throw new TranslationException("file",
                    "Some API declarations are not mapped in your resource listing");
        } else if (rlSize > adSize) {
            throw new TranslationException("file",
                    "Some API declarations are missing");
        }
    }
}


File: modules/org.restlet.ext.apispark/src/org/restlet/ext/apispark/internal/conversion/swagger/v1_2/SwaggerUtils.java
/**
 * Copyright 2005-2014 Restlet
 * 
 * The contents of this file are subject to the terms of one of the following
 * open source licenses: Apache 2.0 or or EPL 1.0 (the "Licenses"). You can
 * select the license that you prefer but you may not use this file except in
 * compliance with one of these Licenses.
 * 
 * You can obtain a copy of the Apache 2.0 license at
 * http://www.opensource.org/licenses/apache-2.0
 * 
 * You can obtain a copy of the EPL 1.0 license at
 * http://www.opensource.org/licenses/eclipse-1.0
 * 
 * See the Licenses for the specific language governing permissions and
 * limitations under the Licenses.
 * 
 * Alternatively, you can obtain a royalty free commercial license with less
 * limitations, transferable or non-transferable, directly at
 * http://restlet.com/products/restlet-framework
 * 
 * Restlet is a registered trademark of Restlet S.A.S.
 */

package org.restlet.ext.apispark.internal.conversion.swagger.v1_2;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.restlet.ext.apispark.internal.conversion.ImportUtils;
import org.restlet.ext.apispark.internal.conversion.TranslationException;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ApiDeclaration;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ResourceListing;
import org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model.ResourceListingApi;
import org.restlet.ext.apispark.internal.model.Definition;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Tools library for Swagger 1.2.
 * 
 * @author Cyprien Quilici
 */
public abstract class SwaggerUtils {

    /** Internal logger. */
    protected static Logger LOGGER = Logger.getLogger(SwaggerUtils.class.getName());

    /**
     * Private constructor to ensure that the class acts as a true utility class
     * i.e. it isn't instantiable and extensible.
     */
    private SwaggerUtils() {
    }

    /**
     * Returns the {@link Definition} by reading the Swagger definition URL.
     * 
     * @param swaggerUrl
     *            The URl of the Swagger definition service.
     * @param userName
     *            The user name for service authentication.
     * @param password
     *            The paswword for service authentication.
     * @return A {@link Definition}.
     * @throws org.restlet.ext.apispark.internal.conversion.TranslationException
     * @throws IOException
     */
    public static Definition getDefinition(String swaggerUrl, String userName,
            String password) throws TranslationException {

        // Check that URL is non empty and well formed
        if (swaggerUrl == null) {
            throw new TranslationException("url", "You did not provide any URL");
        }

        ResourceListing resourceListing;
        Map<String, ApiDeclaration> apis = new HashMap<String, ApiDeclaration>();
        if (ImportUtils.isRemoteUrl(swaggerUrl)) {
            LOGGER.log(Level.FINE, "Reading file: " + swaggerUrl);
            resourceListing = ImportUtils.getAndDeserialize(swaggerUrl, userName, password, ResourceListing.class);
            for (ResourceListingApi api : resourceListing.getApis()) {
                LOGGER.log(Level.FINE,
                        "Reading file: " + swaggerUrl + api.getPath());
                apis.put(
                        api.getPath(),
                        ImportUtils.getAndDeserialize(swaggerUrl + api.getPath(), userName, password,
                                ApiDeclaration.class));
            }
        } else {
            File resourceListingFile = new File(swaggerUrl);
            ObjectMapper om = new ObjectMapper();
            try {
                resourceListing = om.readValue(resourceListingFile,
                        ResourceListing.class);
                String basePath = resourceListingFile.getParent();
                LOGGER.log(Level.FINE, "Base path: " + basePath);
                for (ResourceListingApi api : resourceListing.getApis()) {
                    LOGGER.log(Level.FINE,
                            "Reading file " + basePath + api.getPath());
                    apis.put(api.getPath(), om.readValue(new File(basePath
                            + api.getPath()), ApiDeclaration.class));
                }
            } catch (Exception e) {
                throw new TranslationException("file", e.getMessage());
            }
        }
        return SwaggerReader.translate(resourceListing, apis);
    }
}

File: modules/org.restlet.ext.apispark/src/org/restlet/ext/apispark/internal/conversion/swagger/v1_2/model/ApiDeclaration.java
/**
 * Copyright 2005-2014 Restlet
 * 
 * The contents of this file are subject to the terms of one of the following
 * open source licenses: Apache 2.0 or or EPL 1.0 (the "Licenses"). You can
 * select the license that you prefer but you may not use this file except in
 * compliance with one of these Licenses.
 * 
 * You can obtain a copy of the Apache 2.0 license at
 * http://www.opensource.org/licenses/apache-2.0
 * 
 * You can obtain a copy of the EPL 1.0 license at
 * http://www.opensource.org/licenses/eclipse-1.0
 * 
 * See the Licenses for the specific language governing permissions and
 * limitations under the Licenses.
 * 
 * Alternatively, you can obtain a royalty free commercial license with less
 * limitations, transferable or non-transferable, directly at
 * http://restlet.com/products/restlet-framework
 * 
 * Restlet is a registered trademark of Restlet S.A.S.
 */

package org.restlet.ext.apispark.internal.conversion.swagger.v1_2.model;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;

@JsonInclude(Include.NON_NULL)
public class ApiDeclaration {
    // private String resourcePath";
    private List<ResourceDeclaration> apis;

    private String apiVersion;

    private AuthorizationsDeclaration authorizations;

    private String basePath;

    private List<String> consumes;

    private Map<String, ModelDeclaration> models;

    private List<String> produces;

    private String resourcePath;

    private String swaggerVersion;

    public List<ResourceDeclaration> getApis() {
        if (apis == null) {
            apis = new ArrayList<ResourceDeclaration>();
        }
        return apis;
    }

    public String getApiVersion() {
        return apiVersion;
    }

    public AuthorizationsDeclaration getAuthorizations() {
        return authorizations;
    }

    public String getBasePath() {
        return basePath;
    }

    public List<String> getConsumes() {
        if (consumes == null) {
            consumes = new ArrayList<String>();
        }
        return consumes;
    }

    public Map<String, ModelDeclaration> getModels() {
        if (models == null) {
            models = new HashMap<String, ModelDeclaration>();
        }
        return models;
    }

    public List<String> getProduces() {
        if (produces == null) {
            produces = new ArrayList<String>();
        }
        return produces;
    }

    public String getResourcePath() {
        return resourcePath;
    }

    public String getSwaggerVersion() {
        return swaggerVersion;
    }

    public void setApis(List<ResourceDeclaration> apis) {
        this.apis = apis;
    }

    public void setApiVersion(String apiVersion) {
        this.apiVersion = apiVersion;
    }

    public void setAuthorizations(AuthorizationsDeclaration authorizations) {
        this.authorizations = authorizations;
    }

    public void setBasePath(String basePath) {
        this.basePath = basePath;
    }

    public void setConsumes(List<String> consumes) {
        this.consumes = consumes;
    }

    public void setModels(Map<String, ModelDeclaration> models) {
        this.models = models;
    }

    public void setProduces(List<String> produces) {
        this.produces = produces;
    }

    public void setResourcePath(String resourcePath) {
        this.resourcePath = resourcePath;
    }

    public void setSwaggerVersion(String swaggerVersion) {
        this.swaggerVersion = swaggerVersion;
    }
}


File: modules/org.restlet.ext.apispark/src/org/restlet/ext/apispark/internal/conversion/swagger/v2_0/Swagger2Reader.java
package org.restlet.ext.apispark.internal.conversion.swagger.v2_0;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

import org.restlet.data.ChallengeScheme;
import org.restlet.data.Method;
import org.restlet.ext.apispark.internal.conversion.ConversionUtils;
import org.restlet.ext.apispark.internal.model.Contract;
import org.restlet.ext.apispark.internal.model.Definition;
import org.restlet.ext.apispark.internal.model.Endpoint;
import org.restlet.ext.apispark.internal.model.Header;
import org.restlet.ext.apispark.internal.model.PathVariable;
import org.restlet.ext.apispark.internal.model.PayLoad;
import org.restlet.ext.apispark.internal.model.Representation;
import org.restlet.ext.apispark.internal.model.Resource;
import org.restlet.ext.apispark.internal.model.Section;

import com.wordnik.swagger.models.ArrayModel;
import com.wordnik.swagger.models.Info;
import com.wordnik.swagger.models.Model;
import com.wordnik.swagger.models.Operation;
import com.wordnik.swagger.models.Path;
import com.wordnik.swagger.models.RefModel;
import com.wordnik.swagger.models.Response;
import com.wordnik.swagger.models.Scheme;
import com.wordnik.swagger.models.Swagger;
import com.wordnik.swagger.models.Tag;
import com.wordnik.swagger.models.auth.ApiKeyAuthDefinition;
import com.wordnik.swagger.models.auth.BasicAuthDefinition;
import com.wordnik.swagger.models.auth.OAuth2Definition;
import com.wordnik.swagger.models.auth.SecuritySchemeDefinition;
import com.wordnik.swagger.models.parameters.BodyParameter;
import com.wordnik.swagger.models.parameters.HeaderParameter;
import com.wordnik.swagger.models.parameters.Parameter;
import com.wordnik.swagger.models.parameters.PathParameter;
import com.wordnik.swagger.models.parameters.QueryParameter;
import com.wordnik.swagger.models.parameters.RefParameter;
import com.wordnik.swagger.models.properties.ArrayProperty;
import com.wordnik.swagger.models.properties.Property;
import com.wordnik.swagger.models.properties.RefProperty;

/**
 * Translator : RWADef <- Swagger 2.0.
 */
public class Swagger2Reader {

    /** Internal logger. */
    protected static Logger LOGGER = Logger.getLogger(Swagger2Reader.class.getName());

    private static void fillDeclaredParameters(Swagger swagger, Definition definition,
            Map<String, Object> parameters) {
        if (swagger.getParameters() == null) {
            return;
        }

        for (String key : swagger.getParameters().keySet()) {
            Parameter swaggerParameter = swagger.getParameters().get(key);
            if (swaggerParameter instanceof QueryParameter) {
                org.restlet.ext.apispark.internal.model.QueryParameter queryParameter =
                        new org.restlet.ext.apispark.internal.model.QueryParameter();
                fillRwadefQueryParameter(queryParameter, (QueryParameter) swaggerParameter);
                parameters.put(key, queryParameter);

            } else if (swaggerParameter instanceof PathParameter) {
                org.restlet.ext.apispark.internal.model.PathVariable pathVariable =
                        new org.restlet.ext.apispark.internal.model.PathVariable();
                fillRwadefPathVariable(pathVariable, (PathParameter) swaggerParameter);
                parameters.put(key, pathVariable);

            } else if (swaggerParameter instanceof HeaderParameter) {
                Header header = new Header();
                fillRwadefHeader(header, (HeaderParameter) swaggerParameter);
                parameters.put(key, header);

            } else if (swaggerParameter instanceof BodyParameter) {
                PayLoad payload = new PayLoad();
                fillPayload((BodyParameter) swaggerParameter, payload);
                parameters.put(key, payload);
            } else {
                LOGGER.warning("The type of the parameter " + key + " was not recognized: "
                        + swaggerParameter.getClass().getName());
            }
        }
    }

    private static void fillInputPayload(Operation swaggerOperation,
            org.restlet.ext.apispark.internal.model.Operation operation,
            Contract contract) {
        BodyParameter bodyParameter = SwaggerUtils.getInputPayload(swaggerOperation);

        if (bodyParameter != null) {
            PayLoad payload = new PayLoad();
            fillPayload(bodyParameter, payload);

            Representation representation = contract.getRepresentation(payload.getType());
            if (representation != null) {
                representation.addSections(swaggerOperation.getTags());
            }
            operation.setInputPayLoad(payload);
        }
    }

    private static void fillOutputPayload(Response swaggerResponse,
            org.restlet.ext.apispark.internal.model.Response response,
            Operation swaggerOperation, Contract contract, 
            Map<String, Object> parameters) {
        Property property = swaggerResponse.getSchema();
        if (property == null) {
            return;
        }

        PayLoad payload = null;
        
        if (property instanceof RefProperty) {
            RefProperty refProperty = (RefProperty) property;
            Object declaredPayload = parameters.get(refProperty.get$ref());
            if (declaredPayload != null
                    && declaredPayload instanceof PayLoad) {
                payload = (PayLoad) declaredPayload;
            }

        }

        if (payload == null) {
            payload = new PayLoad();
            payload.setDescription(property.getDescription());
            payload.setArray(property instanceof ArrayProperty);
            payload.setType(SwaggerTypes.toDefinitionType(property));

        }

        Representation representation = contract.getRepresentation(payload.getType());
        if (representation != null) {
            representation.addSections(swaggerOperation.getTags());
        }

        response.setOutputPayLoad(payload);
    }

    private static void fillPayload(BodyParameter bodyParameter, PayLoad payload) {
        Model model = bodyParameter.getSchema();
        payload.setDescription(model.getDescription());

        if (model instanceof ArrayModel) {
            ArrayModel arrayModel = (ArrayModel) model;
            payload.setArray(true);
            payload.setType(SwaggerTypes.toDefinitionType(arrayModel.getItems()));

        } else if (model instanceof RefModel) {
            RefModel refModel = (RefModel) model;
            payload.setType(refModel.getSimpleRef());

        } else {
            // FIXME: should we fail ?
            LOGGER.warning("Unsupported input payload type: " + model.getClass().getSimpleName());
        }
    }

    private static void fillRepresentations(Swagger swagger, Contract contract) {
        if (swagger.getDefinitions() == null) {
            return;
        }

        for (String key : swagger.getDefinitions().keySet()) {
            Model model = swagger.getDefinitions().get(key);
            Representation representation = new Representation();
            representation.setDescription(model.getDescription());
            representation.setName(key);
            representation.setRaw(false);
            // TODO: example not implemented in RWADef (built from properties examples)
            fillRwadefProperties(model, representation);
            contract.getRepresentations().add(representation);
        }
    }

    private static void fillResources(Swagger swagger, Contract contract,
            List<String> produces, List<String> consumes,
            Map<String, Object> parameters) {
        if (swagger.getPaths() == null) {
            return;
        }

        for (String key : swagger.getPaths().keySet()) {
            Resource resource = new Resource();
            Path path = swagger.getPath(key);

            // TODO: description not implemented in Swagger 2.0
            resource.setName(ConversionUtils.processResourceName(key));
            resource.setResourcePath(key);
            for (Operation operation : path.getOperations()) {
                resource.addSections(operation.getTags());
            }

            if (path.getParameters() != null) {
                for (Parameter parameter : path.getParameters()) {
                    PathVariable pathVariable = null;
                    if (parameter instanceof PathParameter) {
                        pathVariable = new PathVariable();
                        fillRwadefPathVariable(pathVariable, (PathParameter) parameter);
                    } else if (parameter instanceof RefParameter) {
                        RefParameter refParameter = (RefParameter) parameter;
                        Object savedParameter = parameters.get(refParameter.getSimpleRef());
                        if (savedParameter instanceof PathVariable) {
                            pathVariable = (PathVariable) savedParameter;
                        }
                    }

                    if (pathVariable != null) {
                        resource.getPathVariables().add(pathVariable);
                    }
                }
            }
            fillRwadefOperations(path, resource, contract, produces, consumes, parameters);

            contract.getResources().add(resource);
        }

    }

    private static void fillRwadefEndpoints(Swagger swagger, Definition definition) {
        String authenticationProtocol = null;

        if (swagger.getSecurityDefinitions() != null) {
            for (String key : swagger.getSecurityDefinitions().keySet()) {
                SecuritySchemeDefinition securityDefinition = swagger.getSecurityDefinitions().get(key);
                if (securityDefinition instanceof BasicAuthDefinition) {
                    authenticationProtocol = ChallengeScheme.HTTP_BASIC.getName();
                } else if (securityDefinition instanceof OAuth2Definition) {
                    authenticationProtocol = ChallengeScheme.HTTP_OAUTH.getName();
                } else if (securityDefinition instanceof ApiKeyAuthDefinition) {
                    authenticationProtocol = ChallengeScheme.CUSTOM.getName();
                }
            }
        }

        if (swagger.getSchemes() != null
            && swagger.getHost() != null) {
            for (Scheme scheme : swagger.getSchemes()) {
                Endpoint endpoint = new Endpoint(scheme.toString().toLowerCase() + "://" + swagger.getHost()
                        + (swagger.getBasePath() == null ? "" : swagger.getBasePath()));
                endpoint.setAuthenticationProtocol(authenticationProtocol);
                definition.getEndpoints().add(endpoint);
            }
        }
    }

    private static void fillRwadefGeneralInformation(Swagger swagger, Definition definition,
            List<String> produces, List<String> consumes) {

        Info info = swagger.getInfo();

        // Contact
        if (info.getContact() != null) {
            org.restlet.ext.apispark.internal.model.Contact contact = new org.restlet.ext.apispark.internal.model.Contact();
            contact.setEmail(info.getContact().getEmail());
            contact.setName(info.getContact().getName());
            contact.setUrl(info.getContact().getUrl());
            definition.setContact(contact);
        }

        if (info.getLicense() != null) {
            // License
            org.restlet.ext.apispark.internal.model.License license = new org.restlet.ext.apispark.internal.model.License();
            license.setName(info.getLicense().getName());
            license.setUrl(info.getLicense().getUrl());
            definition.setLicense(license);
        }

        // Contract
        Contract contract = new Contract();
        contract.setDescription(info.getDescription());
        contract.setName(info.getTitle());
        definition.setContract(contract);

        // Media types
        if (swagger.getProduces() != null) {
            produces.addAll(swagger.getProduces());
        }
        if (swagger.getConsumes() != null) {
            consumes.addAll(swagger.getConsumes());
        }

        // General
        definition.setVersion(info.getVersion());
        definition.setTermsOfService(info.getTermsOfService());
        // TODO: attribution and keywords not implemented in Swagger 2.0
        definition.setAttribution(null);
    }

    private static void fillRwadefHeader(Header header, HeaderParameter swaggerHeader) {
        header.setName(swaggerHeader.getName());
        header.setRequired(swaggerHeader.getRequired());
        header.setDescription(swaggerHeader.getDescription());
        header.setAllowMultiple(true);
        header.setDefaultValue(swaggerHeader.getDefaultValue());
        // TODO: example not implemented in Swagger 2.0

        SwaggerTypeFormat swaggerTypeFormat = new SwaggerTypeFormat(
                swaggerHeader.getType(),
                swaggerHeader.getFormat(),
                swaggerHeader.getItems());
        header.setType(SwaggerTypes.toDefinitionPrimitiveType(swaggerTypeFormat));
    }

    private static void fillRwadefOperation(Operation swaggerOperation, Resource resource,
            Contract contract, String methodName,
            List<String> produces, List<String> consumes,
            Map<String, Object> parameters) {
        if (swaggerOperation == null) {
            return;
        }

        org.restlet.ext.apispark.internal.model.Operation operation =
                new org.restlet.ext.apispark.internal.model.Operation();

        operation.addProduces(produces);
        operation.addProduces(swaggerOperation.getProduces());

        operation.addConsumes(consumes);
        operation.addConsumes(swaggerOperation.getConsumes());

        operation.setDescription(swaggerOperation.getDescription());
        operation.setMethod(methodName);
        operation.setName(swaggerOperation.getOperationId());

        fillRwadefParameters(swaggerOperation, operation, resource, parameters);
        fillRwadefResponses(swaggerOperation, operation, contract, parameters);
        fillInputPayload(swaggerOperation, operation, contract);

        resource.getOperations().add(operation);
    }

    private static void fillRwadefOperations(Path path, Resource resource,
            Contract contract, List<String> produces, List<String> consumes,
            Map<String, Object> parameters) {

        fillRwadefOperation(path.getGet(), resource, contract, Method.GET.getName(),
                produces, consumes, parameters);
        fillRwadefOperation(path.getPost(), resource, contract, Method.POST.getName(),
                produces, consumes, parameters);
        fillRwadefOperation(path.getPut(), resource, contract, Method.PUT.getName(),
                produces, consumes, parameters);
        fillRwadefOperation(path.getDelete(), resource, contract, Method.DELETE.getName(),
                produces, consumes, parameters);
        fillRwadefOperation(path.getOptions(), resource, contract, Method.OPTIONS.getName(),
                produces, consumes, parameters);
        fillRwadefOperation(path.getPatch(), resource, contract, Method.PATCH.getName(),
                produces, consumes, parameters);
    }

    private static void fillRwadefParameters(Operation swaggerOperation,
            org.restlet.ext.apispark.internal.model.Operation operation, Resource resource,
            Map<String, Object> parameters) {
        if (swaggerOperation.getParameters() == null) {
            return;
        }

        for (Parameter swaggerParameter : swaggerOperation.getParameters()) {
            if (swaggerParameter instanceof QueryParameter) {
                org.restlet.ext.apispark.internal.model.QueryParameter queryParameter =
                        new org.restlet.ext.apispark.internal.model.QueryParameter();
                QueryParameter swaggerQueryParameter = (QueryParameter) swaggerParameter;

                fillRwadefQueryParameter(queryParameter, swaggerQueryParameter);
                operation.getQueryParameters().add(queryParameter);
            } else if (swaggerParameter instanceof PathParameter) {
                org.restlet.ext.apispark.internal.model.PathVariable pathVariable =
                        new org.restlet.ext.apispark.internal.model.PathVariable();
                PathParameter swaggerPathVariable = (PathParameter) swaggerParameter;

                fillRwadefPathVariable(pathVariable, swaggerPathVariable);
                if (resource.getPathVariable(pathVariable.getName()) == null) {
                    resource.getPathVariables().add(pathVariable);
                }
            } else if (swaggerParameter instanceof HeaderParameter) {
                Header header = new Header();
                HeaderParameter swaggerHeader = new HeaderParameter();

                fillRwadefHeader(header, swaggerHeader);
                operation.getHeaders().add(header);
            } else {
                if (!(swaggerParameter instanceof BodyParameter)) {
                    LOGGER.warning("Unsupported parameter type for " + swaggerParameter.getName() +
                            " of type " + swaggerParameter.getClass().getName());
                }
            }
        }
    }

    private static void fillRwadefPathVariable(PathVariable pathVariable, PathParameter swaggerPathVariable) {
        pathVariable.setName(swaggerPathVariable.getName());
        pathVariable.setRequired(swaggerPathVariable.getRequired());
        pathVariable.setDescription(swaggerPathVariable.getDescription());
        // TODO: example not implemented in Swagger 2.0

        SwaggerTypeFormat swaggerTypeFormat = new SwaggerTypeFormat(
                swaggerPathVariable.getType(),
                swaggerPathVariable.getFormat(),
                swaggerPathVariable.getItems());
        pathVariable.setType(SwaggerTypes.toDefinitionPrimitiveType(swaggerTypeFormat));
    }

    private static void fillRwadefProperties(Model model, Representation representation) {
        if (model.getProperties() == null) {
            return;
        }

        for (String key : model.getProperties().keySet()) {
            org.restlet.ext.apispark.internal.model.Property property =
                    new org.restlet.ext.apispark.internal.model.Property();
            Property swaggerProperty = model.getProperties().get(key);

            property.setDefaultValue(swaggerProperty.getDefault());
            property.setDescription(swaggerProperty.getDescription());
            // TODO: enumeration not implemented in Swagger 2.0
            property.setExample(swaggerProperty.getExample());
            property.setRequired(swaggerProperty.getRequired());
            property.setList(swaggerProperty instanceof ArrayProperty);
            property.setName(key);
            // TODO: sub-properties not implemented in Swagger 2.0
            // TODO: uniqueItems not implemented in Swagger 2.0
            property.setUniqueItems(false);

            if (swaggerProperty instanceof ArrayProperty) {
                ArrayProperty arrayProperty = (ArrayProperty) swaggerProperty;
                property.setExample(arrayProperty.getItems().getExample());
            }

            property.setType(SwaggerTypes.toDefinitionType(swaggerProperty));

            representation.getProperties().add(property);
        }
    }

    /**
     * Fills the given RWADef query parameter information from the given Swagger query parameter.
     * 
     * @param queryParameter
     *            The RWADef query parameter.
     * @param swaggerQueryParameter
     *            The Swagger query parameter.
     */
    private static void fillRwadefQueryParameter(org.restlet.ext.apispark.internal.model.QueryParameter queryParameter,
            QueryParameter swaggerQueryParameter) {

        // TODO: allowMultiple not implemented in Swagger 2.0
        queryParameter.setAllowMultiple(true);
        queryParameter.setDefaultValue(swaggerQueryParameter.getDefaultValue());
        queryParameter.setDescription(swaggerQueryParameter.getDescription());
        queryParameter.setEnumeration(swaggerQueryParameter.getEnum());
        // TODO: example not implemented in Swagger 2.0
        queryParameter.setName(swaggerQueryParameter.getName());
        queryParameter.setRequired(swaggerQueryParameter.getRequired());
        queryParameter.setSeparator(SwaggerUtils.getSeparator(swaggerQueryParameter.getCollectionFormat()));

        SwaggerTypeFormat swaggerTypeFormat = new SwaggerTypeFormat(
                swaggerQueryParameter.getType(),
                swaggerQueryParameter.getFormat(),
                swaggerQueryParameter.getItems());
        queryParameter.setType(SwaggerTypes.toDefinitionPrimitiveType(swaggerTypeFormat));
    }

    private static void fillRwadefResponses(Operation swaggerOperation,
            org.restlet.ext.apispark.internal.model.Operation operation,
            Contract contract, Map<String, Object> parameters) {
        if (swaggerOperation == null) {
            return;
        }

        for (String key : swaggerOperation.getResponses().keySet()) {
            Response swaggerResponse = swaggerOperation.getResponses().get(key);
            org.restlet.ext.apispark.internal.model.Response response =
                    new org.restlet.ext.apispark.internal.model.Response();

            int statusCode;
            try {
                statusCode = Integer.parseInt(key);
                response.setCode(statusCode);
            } catch (Exception e) {
                // TODO: what to do with "Default" responses ?
                LOGGER.warning("Response " + key + " for operation " + swaggerOperation.getOperationId() +
                        " could not be retrieved because its key is not a valid status code.");
                continue;
            }

            response.setMessage(swaggerResponse.getDescription());
            response.setName(ConversionUtils.generateResponseName(statusCode));

            fillOutputPayload(swaggerResponse, response, swaggerOperation, contract, parameters);

            operation.getResponses().add(response);
        }
    }

    private static void fillSections(Swagger swagger, Contract contract) {
        if (swagger.getTags() == null) {
            return;
        }

        for (Tag tag : swagger.getTags()) {
            Section section = new Section();
            section.setName(tag.getName());
            section.setDescription(tag.getDescription());
            contract.getSections().add(section);
        }
    }

    /**
     * Translates a Swagger definition to a Restlet Web API Definition
     * 
     * @param Swagger
     *            The translated Swagger 2.0 definition
     * 
     * @return The Restlet Web API definition
     */
    public static Definition translate(Swagger swagger) {

        // conversion
        Definition definition = new Definition();

        // fill RWADef main attributes
        fillRwadefEndpoints(swagger, definition);

        List<String> produces = new ArrayList<>();
        List<String> consumes = new ArrayList<>();
        fillRwadefGeneralInformation(swagger, definition, produces, consumes);

        // fill definition.sections
        Contract contract = definition.getContract();
        fillSections(swagger, contract);

        // Get declared parameters
        Map<String, Object> parameters = new LinkedHashMap<>();
        fillDeclaredParameters(swagger, definition, parameters);

        // fill definition.representations
        fillRepresentations(swagger, contract);

        // fill definition.resources
        fillResources(swagger, contract, produces, consumes, parameters);

        for (Representation representation : contract.getRepresentations()) {
            representation.addSectionsToProperties(contract);
        }

        return definition;
    }
}


File: modules/org.restlet.ext.apispark/src/org/restlet/ext/apispark/internal/model/Endpoint.java
/**
 * Copyright 2005-2014 Restlet
 * 
 * The contents of this file are subject to the terms of one of the following
 * open source licenses: Apache 2.0 or or EPL 1.0 (the "Licenses"). You can
 * select the license that you prefer but you may not use this file except in
 * compliance with one of these Licenses.
 * 
 * You can obtain a copy of the Apache 2.0 license at
 * http://www.opensource.org/licenses/apache-2.0
 * 
 * You can obtain a copy of the EPL 1.0 license at
 * http://www.opensource.org/licenses/eclipse-1.0
 * 
 * See the Licenses for the specific language governing permissions and
 * limitations under the Licenses.
 * 
 * Alternatively, you can obtain a royalty free commercial license with less
 * limitations, transferable or non-transferable, directly at
 * http://restlet.com/products/restlet-framework
 * 
 * Restlet is a registered trademark of Restlet S.A.S.
 */

package org.restlet.ext.apispark.internal.model;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Represents a Web API endpoint. Declares the authentication protocol
 * associated
 * 
 * @author Cyprien Quilici
 */
public class Endpoint {

    /** Authentication protocol used for this endpoint */
    private String authenticationProtocol;

    /**
     * Base path for this endpoint.
     * 
     * Ex: http://example.com:8555/v1/admin => basePath = /v1/admin
     */
    private String basePath;

    /** The domain's name. */
    private String domain;

    /** The endpoint's port. */
    private Integer port;

    /** Protocol used for this endpoint. */
    private String protocol;

    public Endpoint() {
    }

    public Endpoint(String url) {
        Pattern p = Pattern
                .compile("([a-zA-Z]*)://([^:^/]*)(:([0-9]*))?([a-zA-Z0-9+&@#/%=~_|]*)");
        Matcher m = p.matcher(url);
        if (m.matches()) {
            domain = m.group(2);
            protocol = m.group(1);
            basePath = m.group(5);
            if (m.group(4) != null) {
                port = Integer.parseInt(m.group(4));
            }
        } else {
            throw new RuntimeException("url does not match URL pattern: " + url);
        }
    }

    /**
     * 
     * @param domain
     *            Domain of the endpoint
     * @param port
     *            Port of the endpoint. Value -1 is considered as null.
     * @param protocol
     *            Protocol of the endpoint
     * @param basePath
     *            Base path of the endpoint
     * @param authenticationProtocol
     *            Authentication scheme of the endpoint
     */
    public Endpoint(String domain, Integer port, String protocol,
            String basePath, String authenticationProtocol) {
        this.domain = domain;
        setPort(port);
        this.protocol = protocol;
        this.basePath = basePath;
        this.authenticationProtocol = authenticationProtocol;
    }

    public String computeUrl() {
        return protocol + "://" + domain + (port != null ? ":" + port : "")
                + (basePath != null ? basePath : "");
    }

    public String getAuthenticationProtocol() {
        return authenticationProtocol;
    }

    public String getBasePath() {
        return basePath;
    }

    public String getDomain() {
        return domain;
    }

    public Integer getPort() {
        return port;
    }

    public String getProtocol() {
        return protocol;
    }

    public void setAuthenticationProtocol(String authenticationProtocol) {
        this.authenticationProtocol = authenticationProtocol;
    }

    public void setBasePath(String basePath) {
        this.basePath = basePath;
    }

    public void setDomain(String domain) {
        this.domain = domain;
    }

    public void setPort(Integer port) {
        if (port != null && port != -1) {
            this.port = port;
        } else {
            port = null;
        }
    }

    public void setProtocol(String protocol) {
        this.protocol = protocol;
    }
}
