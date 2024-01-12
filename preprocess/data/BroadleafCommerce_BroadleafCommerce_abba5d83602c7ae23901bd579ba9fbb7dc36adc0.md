Refactoring Types: ['Extract Superclass']
m/src/main/java/org/broadleafcommerce/openadmin/dto/override/FieldMetadataOverride.java
/*
 * #%L
 * BroadleafCommerce Open Admin Platform
 * %%
 * Copyright (C) 2009 - 2013 Broadleaf Commerce
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */
package org.broadleafcommerce.openadmin.dto.override;

import org.broadleafcommerce.common.presentation.client.AddMethodType;
import org.broadleafcommerce.common.presentation.client.LookupType;
import org.broadleafcommerce.common.presentation.client.OperationType;
import org.broadleafcommerce.common.presentation.client.SupportedFieldType;
import org.broadleafcommerce.common.presentation.client.UnspecifiedBooleanType;
import org.broadleafcommerce.common.presentation.client.VisibilityEnum;
import org.broadleafcommerce.openadmin.dto.MergedPropertyType;

import java.io.Serializable;
import java.util.Map;

/**
 * @author Jeff Fischer
 */
public class FieldMetadataOverride {

    //fields everyone depends on
    private Boolean excluded;
    private String friendlyName;
    private String securityLevel;
    private Integer order;

    public Boolean getExcluded() {
        return excluded;
    }

    public void setExcluded(Boolean excluded) {
        this.excluded = excluded;
    }

    public String getFriendlyName() {
        return friendlyName;
    }

    public void setFriendlyName(String friendlyName) {
        this.friendlyName = friendlyName;
    }

    public String getSecurityLevel() {
        return securityLevel;
    }

    public void setSecurityLevel(String securityLevel) {
        this.securityLevel = securityLevel;
    }

    public Integer getOrder() {
        return order;
    }

    public void setOrder(Integer order) {
        this.order = order;
    }

    //basic fields
    private SupportedFieldType fieldType;
    private SupportedFieldType secondaryType = SupportedFieldType.INTEGER;
    private Integer length;
    private Boolean required;
    private Boolean unique;
    private Integer scale;
    private Integer precision;
    private String foreignKeyProperty;
    private String foreignKeyClass;
    private String foreignKeyDisplayValueProperty;
    private Boolean foreignKeyCollection;
    private MergedPropertyType mergedPropertyType;
    private String[][] enumerationValues;
    private String enumerationClass;
    protected Boolean isDerived;

    //@AdminPresentation derived fields
    private String name;
    private VisibilityEnum visibility;
    private String group;
    private Boolean isBorderlessGroup;
    private Integer groupOrder;
    protected Integer gridOrder;
    private String tab;
    private Integer tabOrder;
    private Boolean groupCollapsed;
    private SupportedFieldType explicitFieldType;
    private Boolean largeEntry;
    private Boolean prominent;
    private String columnWidth;
    private String broadleafEnumeration;
    private Boolean readOnly;
    private Map<String, Map<String, String>> validationConfigurations;
    private Boolean requiredOverride;
    private String tooltip;
    private String helpText;
    private String hint;
    private String lookupDisplayProperty;
    private Boolean forcePopulateChildProperties;
    private Boolean enableTypeaheadLookup;
    private String optionListEntity;
    private String optionValueFieldName;
    private String optionDisplayFieldName;
    private Boolean optionCanEditValues;
    private Serializable[][] optionFilterValues;
    private String showIfProperty;
    private String ruleIdentifier;
    private Boolean translatable;
    private LookupType lookupType;
    private String defaultValue;

    //@AdminPresentationMapField derived fields
    private Boolean searchable;
    private String mapFieldValueClass;

    //Not a user definable field
    private Boolean toOneLookupCreatedViaAnnotation;

    public Boolean getToOneLookupCreatedViaAnnotation() {
        return toOneLookupCreatedViaAnnotation;
    }

    public void setToOneLookupCreatedViaAnnotation(Boolean toOneLookupCreatedViaAnnotation) {
        this.toOneLookupCreatedViaAnnotation = toOneLookupCreatedViaAnnotation;
    }

    public SupportedFieldType getFieldType() {
        return fieldType;
    }

    public void setFieldType(SupportedFieldType fieldType) {
        this.fieldType = fieldType;
    }

    public SupportedFieldType getSecondaryType() {
        return secondaryType;
    }

    public void setSecondaryType(SupportedFieldType secondaryType) {
        this.secondaryType = secondaryType;
    }

    public Integer getLength() {
        return length;
    }

    public void setLength(Integer length) {
        this.length = length;
    }

    public Boolean getRequired() {
        return required;
    }

    public void setRequired(Boolean required) {
        this.required = required;
    }

    public Integer getScale() {
        return scale;
    }

    public void setScale(Integer scale) {
        this.scale = scale;
    }

    public Integer getPrecision() {
        return precision;
    }

    public void setPrecision(Integer precision) {
        this.precision = precision;
    }

    public Boolean getUnique() {
        return unique;
    }

    public void setUnique(Boolean unique) {
        this.unique = unique;
    }

    public String getForeignKeyProperty() {
        return foreignKeyProperty;
    }

    public void setForeignKeyProperty(String foreignKeyProperty) {
        this.foreignKeyProperty = foreignKeyProperty;
    }

    public String getForeignKeyClass() {
        return foreignKeyClass;
    }

    public void setForeignKeyClass(String foreignKeyClass) {
        this.foreignKeyClass = foreignKeyClass;
    }

    public Boolean getForeignKeyCollection() {
        return foreignKeyCollection;
    }

    public void setForeignKeyCollection(Boolean foreignKeyCollection) {
        this.foreignKeyCollection = foreignKeyCollection;
    }

    public MergedPropertyType getMergedPropertyType() {
        return mergedPropertyType;
    }

    public void setMergedPropertyType(MergedPropertyType mergedPropertyType) {
        this.mergedPropertyType = mergedPropertyType;
    }

    public String[][] getEnumerationValues() {
        return enumerationValues;
    }

    public void setEnumerationValues(String[][] enumerationValues) {
        this.enumerationValues = enumerationValues;
    }

    public String getForeignKeyDisplayValueProperty() {
        return foreignKeyDisplayValueProperty;
    }

    public void setForeignKeyDisplayValueProperty(String foreignKeyDisplayValueProperty) {
        this.foreignKeyDisplayValueProperty = foreignKeyDisplayValueProperty;
    }

    public String getEnumerationClass() {
        return enumerationClass;
    }

    public void setEnumerationClass(String enumerationClass) {
        this.enumerationClass = enumerationClass;
    }
    
    public Boolean getIsDerived() {
        return isDerived;
    }

    public void setDerived(Boolean isDerived) {
        this.isDerived = isDerived;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public SupportedFieldType getExplicitFieldType() {
        return explicitFieldType;
    }

    public void setExplicitFieldType(SupportedFieldType fieldType) {
        this.explicitFieldType = fieldType;
    }

    public String getGroup() {
        return group;
    }

    public void setGroup(String group) {
        this.group = group;
    }

    public Boolean getIsBorderlessGroup() {
        return isBorderlessGroup;
    }

    public void setIsBorderlessGroup(Boolean isBorderlessGroup) {
        this.isBorderlessGroup = isBorderlessGroup;
    }

    public Boolean isLargeEntry() {
        return largeEntry;
    }

    public void setLargeEntry(Boolean largeEntry) {
        this.largeEntry = largeEntry;
    }

    public Boolean isProminent() {
        return prominent;
    }

    public void setProminent(Boolean prominent) {
        this.prominent = prominent;
    }

    public String getColumnWidth() {
        return columnWidth;
    }

    public void setColumnWidth(String columnWidth) {
        this.columnWidth = columnWidth;
    }

    public String getBroadleafEnumeration() {
        return broadleafEnumeration;
    }

    public void setBroadleafEnumeration(String broadleafEnumeration) {
        this.broadleafEnumeration = broadleafEnumeration;
    }

    public Boolean getReadOnly() {
        return readOnly;
    }
    
    public Boolean getTranslatable() {
        return translatable;
    }
    
    public void setTranslatable(Boolean translatable) {
        this.translatable = translatable;
    }

    public String getDefaultValue() {
        return defaultValue;
    }

    public void setDefaultValue(String defaultValue) {
        this.defaultValue = defaultValue;
    }

    public String getTab() {
        return tab;
    }

    public void setTab(String tab) {
        this.tab = tab;
    }

    public Integer getTabOrder() {
        return tabOrder;
    }

    public void setTabOrder(Integer tabOrder) {
        this.tabOrder = tabOrder;
    }

    public void setReadOnly(Boolean readOnly) {
        this.readOnly = readOnly;
    }

    public Integer getGroupOrder() {
        return groupOrder;
    }

    public void setGroupOrder(Integer groupOrder) {
        this.groupOrder = groupOrder;
    }
    
    public Integer getGridOrder() {
        return gridOrder;
    }

    public void setGridOrder(Integer gridOrder) {
        this.gridOrder = gridOrder;
    }

    public Map<String, Map<String, String>> getValidationConfigurations() {
        return validationConfigurations;
    }

    public void setValidationConfigurations(Map<String, Map<String, String>> validationConfigurations) {
        this.validationConfigurations = validationConfigurations;
    }

    public Boolean getRequiredOverride() {
        return requiredOverride;
    }

    public void setRequiredOverride(Boolean requiredOverride) {
        this.requiredOverride = requiredOverride;
    }

    public Boolean getGroupCollapsed() {
        return groupCollapsed;
    }

    public void setGroupCollapsed(Boolean groupCollapsed) {
        this.groupCollapsed = groupCollapsed;
    }

    public String getTooltip() {
        return tooltip;
    }

    public void setTooltip(String tooltip) {
        this.tooltip = tooltip;
    }

    public String getHelpText() {
        return helpText;
    }

    public void setHelpText(String helpText) {
        this.helpText = helpText;
    }

    public String getHint() {
        return hint;
    }

    public void setHint(String hint) {
        this.hint = hint;
    }

    public VisibilityEnum getVisibility() {
        return visibility;
    }

    public void setVisibility(VisibilityEnum visibility) {
        this.visibility = visibility;
    }

    public String getLookupDisplayProperty() {
        return lookupDisplayProperty;
    }

    public void setLookupDisplayProperty(String lookupDisplayProperty) {
        this.lookupDisplayProperty = lookupDisplayProperty;
    }
    
    public Boolean getForcePopulateChildProperties() {
        return forcePopulateChildProperties;
    }
    
    public void setForcePopulateChildProperties(Boolean forcePopulateChildProperties) {
        this.forcePopulateChildProperties = forcePopulateChildProperties;
    }
    
    public Boolean getEnableTypeaheadLookup() {
        return enableTypeaheadLookup;
    }

    public void setEnableTypeaheadLookup(Boolean enableTypeaheadLookup) {
        this.enableTypeaheadLookup = enableTypeaheadLookup;
    }

    public Boolean getOptionCanEditValues() {
        return optionCanEditValues;
    }

    public void setOptionCanEditValues(Boolean optionCanEditValues) {
        this.optionCanEditValues = optionCanEditValues;
    }

    public String getOptionDisplayFieldName() {
        return optionDisplayFieldName;
    }

    public void setOptionDisplayFieldName(String optionDisplayFieldName) {
        this.optionDisplayFieldName = optionDisplayFieldName;
    }

    public String getOptionListEntity() {
        return optionListEntity;
    }

    public void setOptionListEntity(String optionListEntity) {
        this.optionListEntity = optionListEntity;
    }

    public String getOptionValueFieldName() {
        return optionValueFieldName;
    }

    public void setOptionValueFieldName(String optionValueFieldName) {
        this.optionValueFieldName = optionValueFieldName;
    }

    public Serializable[][] getOptionFilterValues() {
        return optionFilterValues;
    }

    public void setOptionFilterValues(Serializable[][] optionFilterValues) {
        this.optionFilterValues = optionFilterValues;
    }

    public String getRuleIdentifier() {
        return ruleIdentifier;
    }

    public void setRuleIdentifier(String ruleIdentifier) {
        this.ruleIdentifier = ruleIdentifier;
    }

    public Boolean getSearchable() {
        return searchable;
    }

    public void setSearchable(Boolean searchable) {
        this.searchable = searchable;
    }

    public String getMapFieldValueClass() {
        return mapFieldValueClass;
    }

    public void setMapFieldValueClass(String mapFieldValueClass) {
        this.mapFieldValueClass = mapFieldValueClass;
    }

    //collection fields
    private String[] customCriteria;
    private OperationType addType;
    private OperationType removeType;
    private OperationType updateType;
    private OperationType fetchType;
    private OperationType inspectType;
    private Boolean useServerSideInspectionCache;

    public String[] getCustomCriteria() {
        return customCriteria;
    }

    public void setCustomCriteria(String[] customCriteria) {
        this.customCriteria = customCriteria;
    }

    public Boolean getUseServerSideInspectionCache() {
        return useServerSideInspectionCache;
    }

    public void setUseServerSideInspectionCache(Boolean useServerSideInspectionCache) {
        this.useServerSideInspectionCache = useServerSideInspectionCache;
    }

    public OperationType getAddType() {
        return addType;
    }

    public void setAddType(OperationType addType) {
        this.addType = addType;
    }

    public OperationType getFetchType() {
        return fetchType;
    }

    public void setFetchType(OperationType fetchType) {
        this.fetchType = fetchType;
    }

    public OperationType getInspectType() {
        return inspectType;
    }

    public void setInspectType(OperationType inspectType) {
        this.inspectType = inspectType;
    }

    public OperationType getRemoveType() {
        return removeType;
    }

    public void setRemoveType(OperationType removeType) {
        this.removeType = removeType;
    }

    public OperationType getUpdateType() {
        return updateType;
    }

    public void setUpdateType(OperationType updateType) {
        this.updateType = updateType;
    }

    //basic collection fields
    private AddMethodType addMethodType;
    private String manyToField;

    public AddMethodType getAddMethodType() {
        return addMethodType;
    }

    public void setAddMethodType(AddMethodType addMethodType) {
        this.addMethodType = addMethodType;
    }

    public String getManyToField() {
        return manyToField;
    }

    public void setManyToField(String manyToField) {
        this.manyToField = manyToField;
    }

    //Adorned target fields
    private String parentObjectProperty;
    private String parentObjectIdProperty;
    private String targetObjectProperty;
    private String[] maintainedAdornedTargetFields;
    private String[] gridVisibleFields;
    private String targetObjectIdProperty;
    private String joinEntityClass;
    private String sortProperty;
    private Boolean sortAscending;
    private Boolean ignoreAdornedProperties;

    public String[] getGridVisibleFields() {
        return gridVisibleFields;
    }

    public void setGridVisibleFields(String[] gridVisibleFields) {
        this.gridVisibleFields = gridVisibleFields;
    }

    public Boolean isIgnoreAdornedProperties() {
        return ignoreAdornedProperties;
    }

    public void setIgnoreAdornedProperties(Boolean ignoreAdornedProperties) {
        this.ignoreAdornedProperties = ignoreAdornedProperties;
    }

    public String[] getMaintainedAdornedTargetFields() {
        return maintainedAdornedTargetFields;
    }

    public void setMaintainedAdornedTargetFields(String[] maintainedAdornedTargetFields) {
        this.maintainedAdornedTargetFields = maintainedAdornedTargetFields;
    }

    public String getParentObjectIdProperty() {
        return parentObjectIdProperty;
    }

    public void setParentObjectIdProperty(String parentObjectIdProperty) {
        this.parentObjectIdProperty = parentObjectIdProperty;
    }

    public String getParentObjectProperty() {
        return parentObjectProperty;
    }

    public void setParentObjectProperty(String parentObjectProperty) {
        this.parentObjectProperty = parentObjectProperty;
    }

    public Boolean isSortAscending() {
        return sortAscending;
    }

    public void setSortAscending(Boolean sortAscending) {
        this.sortAscending = sortAscending;
    }

    public String getSortProperty() {
        return sortProperty;
    }

    public void setSortProperty(String sortProperty) {
        this.sortProperty = sortProperty;
    }

    public String getTargetObjectIdProperty() {
        return targetObjectIdProperty;
    }

    public void setTargetObjectIdProperty(String targetObjectIdProperty) {
        this.targetObjectIdProperty = targetObjectIdProperty;
    }

    public String getJoinEntityClass() {
        return joinEntityClass;
    }

    public void setJoinEntityClass(String joinEntityClass) {
        this.joinEntityClass = joinEntityClass;
    }

    public String getTargetObjectProperty() {
        return targetObjectProperty;
    }

    public void setTargetObjectProperty(String targetObjectProperty) {
        this.targetObjectProperty = targetObjectProperty;
    }

    //Map fields
    private String keyClass;
    private String keyPropertyFriendlyName;
    private String valueClass;
    private Boolean deleteEntityUponRemove;
    private String valuePropertyFriendlyName;
    private UnspecifiedBooleanType isSimpleValue;
    private String mediaField;
    private String[][] keys;
    private String mapKeyValueProperty;
    private String mapKeyOptionEntityClass;
    private String mapKeyOptionEntityDisplayField;
    private String mapKeyOptionEntityValueField;
    private String currencyCodeField;
    private Boolean forceFreeFormKeys;
    private String toOneTargetProperty;
    private String toOneParentProperty;

    public Boolean isDeleteEntityUponRemove() {
        return deleteEntityUponRemove;
    }

    public void setDeleteEntityUponRemove(Boolean deleteEntityUponRemove) {
        this.deleteEntityUponRemove = deleteEntityUponRemove;
    }

    public UnspecifiedBooleanType getSimpleValue() {
        return isSimpleValue;
    }

    public void setSimpleValue(UnspecifiedBooleanType simpleValue) {
        isSimpleValue = simpleValue;
    }

    public String getKeyClass() {
        return keyClass;
    }

    public void setKeyClass(String keyClass) {
        this.keyClass = keyClass;
    }
    

    public String getKeyPropertyFriendlyName() {
        return keyPropertyFriendlyName;
    }

    public void setKeyPropertyFriendlyName(String keyPropertyFriendlyName) {
        this.keyPropertyFriendlyName = keyPropertyFriendlyName;
    }

    public String[][] getKeys() {
        return keys;
    }

    public void setKeys(String[][] keys) {
        this.keys = keys;
    }

    public String getMapKeyOptionEntityClass() {
        return mapKeyOptionEntityClass;
    }

    public void setMapKeyOptionEntityClass(String mapKeyOptionEntityClass) {
        this.mapKeyOptionEntityClass = mapKeyOptionEntityClass;
    }

    public String getMapKeyOptionEntityDisplayField() {
        return mapKeyOptionEntityDisplayField;
    }

    public void setMapKeyOptionEntityDisplayField(String mapKeyOptionEntityDisplayField) {
        this.mapKeyOptionEntityDisplayField = mapKeyOptionEntityDisplayField;
    }

    public String getMapKeyOptionEntityValueField() {
        return mapKeyOptionEntityValueField;
    }

    public void setMapKeyOptionEntityValueField(String mapKeyOptionEntityValueField) {
        this.mapKeyOptionEntityValueField = mapKeyOptionEntityValueField;
    }

    public String getMediaField() {
        return mediaField;
    }

    public void setMediaField(String mediaField) {
        this.mediaField = mediaField;
    }

    public String getToOneTargetProperty() {
        return toOneTargetProperty;
    }

    public void setToOneTargetProperty(String toOneTargetProperty) {
        this.toOneTargetProperty = toOneTargetProperty;
    }

    public String getToOneParentProperty() {
        return toOneParentProperty;
    }

    public void setToOneParentProperty(String toOneParentProperty) {
        this.toOneParentProperty = toOneParentProperty;
    }

    public String getValueClass() {
        return valueClass;
    }

    public void setValueClass(String valueClass) {
        this.valueClass = valueClass;
    }

    public String getValuePropertyFriendlyName() {
        return valuePropertyFriendlyName;
    }

    public void setValuePropertyFriendlyName(String valuePropertyFriendlyName) {
        this.valuePropertyFriendlyName = valuePropertyFriendlyName;
    }

    public String getShowIfProperty() {
        return showIfProperty;
    }

    public void setShowIfProperty(String showIfProperty) {
        this.showIfProperty = showIfProperty;
    }

    public String getCurrencyCodeField() {
        return currencyCodeField;
    }

    public void setCurrencyCodeField(String currencyCodeField) {
        this.currencyCodeField = currencyCodeField;
    }
    
    public LookupType getLookupType() {
        return lookupType;
    }

    public void setLookupType(LookupType lookupType) {
        this.lookupType = lookupType;
    }

    public Boolean getForceFreeFormKeys() {
        return forceFreeFormKeys;
    }

    public void setForceFreeFormKeys(Boolean forceFreeFormKeys) {
        this.forceFreeFormKeys = forceFreeFormKeys;
    }
    
    public String getMapKeyValueProperty() {
        return mapKeyValueProperty;
    }

    public void setMapKeyValueProperty(String mapKeyValueProperty) {
        this.mapKeyValueProperty = mapKeyValueProperty;
    }
    
}


File: admin/broadleaf-open-admin-platform/src/main/java/org/broadleafcommerce/openadmin/server/dao/provider/metadata/AbstractFieldMetadataProvider.java
/*
 * #%L
 * BroadleafCommerce Open Admin Platform
 * %%
 * Copyright (C) 2009 - 2013 Broadleaf Commerce
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */
package org.broadleafcommerce.openadmin.server.dao.provider.metadata;

import org.apache.commons.lang.StringUtils;
import org.broadleafcommerce.common.persistence.EntityConfiguration;
import org.broadleafcommerce.common.presentation.AdminPresentationClass;
import org.broadleafcommerce.common.presentation.OptionFilterParamType;
import org.broadleafcommerce.common.presentation.client.SupportedFieldType;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeEntry;
import org.broadleafcommerce.common.util.Tuple;
import org.broadleafcommerce.openadmin.dto.BasicFieldMetadata;
import org.broadleafcommerce.openadmin.dto.FieldMetadata;
import org.broadleafcommerce.openadmin.dto.override.FieldMetadataOverride;
import org.broadleafcommerce.openadmin.server.dao.DynamicEntityDao;
import org.broadleafcommerce.openadmin.server.dao.FieldInfo;

import java.lang.reflect.Field;
import java.math.BigDecimal;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;
import javax.persistence.ManyToMany;
import javax.persistence.MapKey;
import javax.persistence.OneToMany;

/**
 * @author Jeff Fischer
 */
public abstract class AbstractFieldMetadataProvider implements FieldMetadataProvider {

    protected Map<String, Map<String, FieldMetadataOverride>> metadataOverrides;

    @Resource(name = "blEntityConfiguration")
    protected EntityConfiguration entityConfiguration;
    
    @Resource(name = "blBroadleafEnumerationUtility")
    protected BroadleafEnumerationUtility enumerationUtility;

    @Resource(name="blMetadataOverrides")
    public void setMetadataOverrides(Map metadataOverrides) {
        try {
            this.metadataOverrides = metadataOverrides;
        } catch (Throwable e) {
            throw new IllegalArgumentException(
                    "Unable to assign metadataOverrides. You are likely using an obsolete spring application context " +
                    "configuration for this value. Please utilize the xmlns:mo=\"http://schema.broadleafcommerce.org/mo\" namespace " +
                    "and http://schema.broadleafcommerce.org/mo http://schema.broadleafcommerce.org/mo/mo.xsd schemaLocation " +
                    "in the xml schema config for your app context. This will allow you to use the appropriate <mo:override> element to configure your overrides.", e);
        }
    }

    protected void setClassOwnership(Class<?> parentClass, Class<?> targetClass, Map<String, FieldMetadata> attributes, FieldInfo field) {
        FieldMetadata metadata = attributes.get(field.getName());
        if (metadata != null) {
            AdminPresentationClass adminPresentationClass;
            if (parentClass != null) {
                metadata.setOwningClass(parentClass.getName());
                adminPresentationClass = parentClass.getAnnotation(AdminPresentationClass.class);
            } else {
                adminPresentationClass = targetClass.getAnnotation(AdminPresentationClass.class);
            }
            if (adminPresentationClass != null) {
                String friendlyName = adminPresentationClass.friendlyName();
                if (!StringUtils.isEmpty(friendlyName) && StringUtils.isEmpty(metadata.getOwningClassFriendlyName())) {
                    metadata.setOwningClassFriendlyName(friendlyName);
                }
            }
        }
    }

    protected FieldInfo buildFieldInfo(Field field) {
        FieldInfo info = new FieldInfo();
        info.setName(field.getName());
        info.setGenericType(field.getGenericType());
        ManyToMany manyToMany = field.getAnnotation(ManyToMany.class);
        if (manyToMany != null) {
            info.setManyToManyMappedBy(manyToMany.mappedBy());
            info.setManyToManyTargetEntity(manyToMany.targetEntity().getName());
        }
        OneToMany oneToMany = field.getAnnotation(OneToMany.class);
        if (oneToMany != null) {
            info.setOneToManyMappedBy(oneToMany.mappedBy());
            info.setOneToManyTargetEntity(oneToMany.targetEntity().getName());
        }
        MapKey mapKey = field.getAnnotation(MapKey.class);
        if (mapKey != null) {
            info.setMapKey(mapKey.name());
        }
        return info;
    }

    /**
     * @deprecated use the overloaded method that takes DynamicEntityDao as well. This version does not always properly detect the override from xml.
     * @param configurationKey
     * @param ceilingEntityFullyQualifiedClassname
     * @return override value
     */
    @Deprecated
    protected Map<String, FieldMetadataOverride> getTargetedOverride(String configurationKey, String ceilingEntityFullyQualifiedClassname) {
        if (metadataOverrides != null && (configurationKey != null || ceilingEntityFullyQualifiedClassname != null)) {
            return metadataOverrides.containsKey(configurationKey)?metadataOverrides.get(configurationKey):metadataOverrides.get(ceilingEntityFullyQualifiedClassname);
        }
        return null;
    }

    protected Map<String, FieldMetadataOverride> getTargetedOverride(DynamicEntityDao dynamicEntityDao, String configurationKey, String ceilingEntityFullyQualifiedClassname) {
        if (metadataOverrides != null && (configurationKey != null || ceilingEntityFullyQualifiedClassname != null)) {
            if (metadataOverrides.containsKey(configurationKey)) {
                return metadataOverrides.get(configurationKey);
            }
            if (metadataOverrides.containsKey(ceilingEntityFullyQualifiedClassname)) {
                return metadataOverrides.get(ceilingEntityFullyQualifiedClassname);
            }
            Class<?> test;
            try {
                test = Class.forName(ceilingEntityFullyQualifiedClassname);
            } catch (ClassNotFoundException e) {
                throw new RuntimeException(e);
            }
            if (test.isInterface()) {
                //if it's an interface, get the least derive polymorphic concrete implementation
                Class<?>[] types = dynamicEntityDao.getAllPolymorphicEntitiesFromCeiling(test);
                return metadataOverrides.get(types[types.length-1].getName());
            } else {
                //if it's a concrete implementation, try the interfaces
                Class<?>[] types = test.getInterfaces();
                for (Class<?> type : types) {
                    if (metadataOverrides.containsKey(type.getName())) {
                        return metadataOverrides.get(type.getName());
                    }
                }
            }
        }
        return null;
    }

    protected Class<?> getBasicJavaType(SupportedFieldType fieldType) {
        Class<?> response;
        switch (fieldType) {
            case BOOLEAN:
                response = Boolean.TYPE;
                break;
            case DATE:
                response = Date.class;
                break;
            case DECIMAL:
                response = BigDecimal.class;
                break;
            case MONEY:
                response = BigDecimal.class;
                break;
            case INTEGER:
                response = Integer.TYPE;
                break;
            case UNKNOWN:
                response = null;
                break;
            default:
                response = String.class;
                break;
        }

        return response;
    }

    protected Object convertType(String value, OptionFilterParamType type) {
        Object response;
        switch (type) {
            case BIGDECIMAL:
               response = new BigDecimal(value);
               break;
            case BOOLEAN:
               response = Boolean.parseBoolean(value);
               break;
            case DOUBLE:
               response = Double.parseDouble(value);
               break;
            case FLOAT:
               response = Float.parseFloat(value);
               break;
            case INTEGER:
               response = Integer.parseInt(value);
               break;
            case LONG:
               response = Long.parseLong(value);
               break;
            default:
               response = value;
               break;
        }

        return response;
    }

    protected void setupBroadleafEnumeration(String broadleafEnumerationClass, BasicFieldMetadata fieldMetadata, DynamicEntityDao dynamicEntityDao) {
        try {
            List<Tuple<String, String>> enumVals = enumerationUtility.getEnumerationValues(broadleafEnumerationClass, dynamicEntityDao);
            
            String[][] enumerationValues = new String[enumVals.size()][2];
            int j = 0;
            for (Tuple<String, String> t : enumVals) {
                enumerationValues[j][0] = t.getFirst();
                enumerationValues[j][1] = t.getSecond();
                j++;
            }
            
            fieldMetadata.setEnumerationValues(enumerationValues);
            fieldMetadata.setEnumerationClass(broadleafEnumerationClass);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    protected Map<String, AdminPresentationMergeEntry> getAdminPresentationEntries(AdminPresentationMergeEntry[] entries) {
        Map<String, AdminPresentationMergeEntry> response = new HashMap<String, AdminPresentationMergeEntry>();
        for (AdminPresentationMergeEntry entry : entries) {
            response.put(entry.propertyType(), entry);
        }
        return response;
    }
}


File: admin/broadleaf-open-admin-platform/src/main/java/org/broadleafcommerce/openadmin/server/dao/provider/metadata/AdornedTargetCollectionFieldMetadataProvider.java
/*
 * #%L
 * BroadleafCommerce Open Admin Platform
 * %%
 * Copyright (C) 2009 - 2013 Broadleaf Commerce
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */
package org.broadleafcommerce.openadmin.server.dao.provider.metadata;

import org.apache.commons.lang.ArrayUtils;
import org.apache.commons.lang.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.broadleafcommerce.common.presentation.AdminPresentationAdornedTargetCollection;
import org.broadleafcommerce.common.presentation.AdminPresentationOperationTypes;
import org.broadleafcommerce.common.presentation.client.OperationType;
import org.broadleafcommerce.common.presentation.client.PersistencePerspectiveItemType;
import org.broadleafcommerce.common.presentation.override.AdminPresentationAdornedTargetCollectionOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeEntry;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeOverrides;
import org.broadleafcommerce.common.presentation.override.AdminPresentationOverrides;
import org.broadleafcommerce.common.presentation.override.PropertyType;
import org.broadleafcommerce.openadmin.dto.AdornedTargetCollectionMetadata;
import org.broadleafcommerce.openadmin.dto.AdornedTargetList;
import org.broadleafcommerce.openadmin.dto.FieldMetadata;
import org.broadleafcommerce.openadmin.dto.ForeignKey;
import org.broadleafcommerce.openadmin.dto.PersistencePerspective;
import org.broadleafcommerce.openadmin.dto.override.FieldMetadataOverride;
import org.broadleafcommerce.openadmin.server.dao.DynamicEntityDao;
import org.broadleafcommerce.openadmin.server.dao.FieldInfo;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataFromFieldTypeRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaAnnotationRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaXmlRequest;
import org.broadleafcommerce.openadmin.server.service.type.MetadataProviderResponse;
import org.springframework.beans.factory.NoSuchBeanDefinitionException;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Component;

import java.lang.reflect.Field;
import java.lang.reflect.ParameterizedType;
import java.util.HashMap;
import java.util.Map;

import javax.persistence.ManyToOne;

/**
 * @author Jeff Fischer
 */
@Component("blAdornedTargetCollectionFieldMetadataProvider")
@Scope("prototype")
public class AdornedTargetCollectionFieldMetadataProvider extends AdvancedCollectionFieldMetadataProvider {

    private static final Log LOG = LogFactory.getLog(AdornedTargetCollectionFieldMetadataProvider.class);

    protected boolean canHandleFieldForConfiguredMetadata(AddMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentationAdornedTargetCollection annot = addMetadataRequest.getRequestedField().getAnnotation(AdminPresentationAdornedTargetCollection.class);
        return annot != null;
    }

    protected boolean canHandleFieldForTypeMetadata(AddMetadataFromFieldTypeRequest addMetadataFromFieldTypeRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentationAdornedTargetCollection annot = addMetadataFromFieldTypeRequest.getRequestedField().getAnnotation(AdminPresentationAdornedTargetCollection.class);
        return annot != null;
    }

    protected boolean canHandleAnnotationOverride(OverrideViaAnnotationRequest overrideViaAnnotationRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentationOverrides myOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationOverrides.class);
        AdminPresentationMergeOverrides myMergeOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationMergeOverrides.class);
        return (myOverrides != null && !ArrayUtils.isEmpty(myOverrides.adornedTargetCollections())) ||
                myMergeOverrides != null;
    }

    @Override
    public MetadataProviderResponse addMetadata(AddFieldMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleFieldForConfiguredMetadata(addMetadataRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        AdminPresentationAdornedTargetCollection annot = addMetadataRequest.getRequestedField().getAnnotation(AdminPresentationAdornedTargetCollection.class);
        FieldInfo info = buildFieldInfo(addMetadataRequest.getRequestedField());
        FieldMetadataOverride override = constructAdornedTargetCollectionMetadataOverride(annot);
        buildAdornedTargetCollectionMetadata(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(), metadata, info, override, addMetadataRequest.getDynamicEntityDao());
        setClassOwnership(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(), metadata, info);
        return MetadataProviderResponse.HANDLED;
    }

    @Override
    public MetadataProviderResponse overrideViaAnnotation(OverrideViaAnnotationRequest overrideViaAnnotationRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleAnnotationOverride(overrideViaAnnotationRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        Map<String, AdminPresentationAdornedTargetCollectionOverride> presentationAdornedTargetCollectionOverrides = new HashMap<String, AdminPresentationAdornedTargetCollectionOverride>();

        AdminPresentationOverrides myOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationOverrides.class);
        if (myOverrides != null) {
            for (AdminPresentationAdornedTargetCollectionOverride myOverride : myOverrides.adornedTargetCollections()) {
                presentationAdornedTargetCollectionOverrides.put(myOverride.name(), myOverride);
            }
        }

        for (String propertyName : presentationAdornedTargetCollectionOverrides.keySet()) {
            for (String key : metadata.keySet()) {
                if (key.startsWith(propertyName)) {
                    buildAdminPresentationAdornedTargetCollectionOverride(overrideViaAnnotationRequest.getPrefix(), overrideViaAnnotationRequest.getParentExcluded(), metadata, presentationAdornedTargetCollectionOverrides, propertyName, key, overrideViaAnnotationRequest.getDynamicEntityDao());
                }
            }
        }

        AdminPresentationMergeOverrides myMergeOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationMergeOverrides.class);
        if (myMergeOverrides != null) {
            for (AdminPresentationMergeOverride override : myMergeOverrides.value()) {
                String propertyName = override.name();
                Map<String, FieldMetadata> loopMap = new HashMap<String, FieldMetadata>();
                loopMap.putAll(metadata);
                for (Map.Entry<String, FieldMetadata> entry : loopMap.entrySet()) {
                    if (entry.getKey().startsWith(propertyName) || StringUtils.isEmpty(propertyName)) {
                        FieldMetadata targetMetadata = entry.getValue();
                        if (targetMetadata instanceof AdornedTargetCollectionMetadata) {
                            AdornedTargetCollectionMetadata serverMetadata = (AdornedTargetCollectionMetadata) targetMetadata;
                            if (serverMetadata.getTargetClass() != null) {
                                try {
                                    Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                                    Class<?> parentClass = null;
                                    if (serverMetadata.getOwningClass() != null) {
                                        parentClass = Class.forName(serverMetadata.getOwningClass());
                                    }
                                    String fieldName = serverMetadata.getFieldName();
                                    Field field = overrideViaAnnotationRequest.getDynamicEntityDao().getFieldManager()
                                                .getField(targetClass, fieldName);
                                    Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                                    temp.put(field.getName(), serverMetadata);
                                    FieldInfo info = buildFieldInfo(field);
                                    FieldMetadataOverride fieldMetadataOverride = overrideAdornedTargetMergeMetadata(override);
                                    if (serverMetadata.getExcluded() != null && serverMetadata.getExcluded() &&
                                            (fieldMetadataOverride.getExcluded() == null || fieldMetadataOverride.getExcluded())) {
                                        continue;
                                    }
                                    buildAdornedTargetCollectionMetadata(parentClass, targetClass, temp, info,
                                            fieldMetadataOverride,
                                            overrideViaAnnotationRequest.getDynamicEntityDao());
                                    serverMetadata = (AdornedTargetCollectionMetadata) temp.get(field.getName());
                                    metadata.put(entry.getKey(), serverMetadata);
                                } catch (Exception e) {
                                    throw new RuntimeException(e);
                                }
                            }
                        }
                    }
                }
            }
        }

        return MetadataProviderResponse.HANDLED;
    }

    @Override
        Map<String, FieldMetadataOverride> overrides = getTargetedOverride(overrideViaXmlRequest.getDynamicEntityDao(), overrideViaXmlRequest.getRequestedConfigKey(), overrideViaXmlRequest.getRequestedCeilingEntity());
    public MetadataProviderResponse overrideViaXml(OverrideViaXmlRequest overrideViaXmlRequest, Map<String, FieldMetadata> metadata) {
        if (overrides != null) {
            for (String propertyName : overrides.keySet()) {
                final FieldMetadataOverride localMetadata = overrides.get(propertyName);
                for (String key : metadata.keySet()) {
                    if (key.equals(propertyName)) {
                        try {
                            if (metadata.get(key) instanceof AdornedTargetCollectionMetadata) {
                                AdornedTargetCollectionMetadata serverMetadata = (AdornedTargetCollectionMetadata) metadata.get(key);
                                if (serverMetadata.getTargetClass() != null) {
                                    Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                                    Class<?> parentClass = null;
                                    if (serverMetadata.getOwningClass() != null) {
                                        parentClass = Class.forName(serverMetadata.getOwningClass());
                                    }
                                    String fieldName = serverMetadata.getFieldName();
                                    Field field = overrideViaXmlRequest.getDynamicEntityDao().getFieldManager().getField(targetClass, fieldName);
                                    Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                                    temp.put(field.getName(), serverMetadata);
                                    FieldInfo info = buildFieldInfo(field);
                                    buildAdornedTargetCollectionMetadata(parentClass, targetClass, temp, info, localMetadata, overrideViaXmlRequest.getDynamicEntityDao());
                                    serverMetadata = (AdornedTargetCollectionMetadata) temp.get(field.getName());
                                    metadata.put(key, serverMetadata);
                                    if (overrideViaXmlRequest.getParentExcluded()) {
                                        if (LOG.isDebugEnabled()) {
                                            LOG.debug("applyAdornedTargetCollectionMetadataOverrides:Excluding " + key + "because parent is marked as excluded.");
                                        }
                                        serverMetadata.setExcluded(true);
                                    }
                                }
                            }
                        } catch (Exception e) {
                            throw new RuntimeException(e);
                        }
                    }
                }
            }
        }
        return MetadataProviderResponse.HANDLED;
    }

    @Override
    public MetadataProviderResponse addMetadataFromFieldType(AddMetadataFromFieldTypeRequest addMetadataFromFieldTypeRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleFieldForTypeMetadata(addMetadataFromFieldTypeRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        super.addMetadataFromFieldType(addMetadataFromFieldTypeRequest, metadata);
        //add additional adorned target support
        AdornedTargetCollectionMetadata fieldMetadata = (AdornedTargetCollectionMetadata) addMetadataFromFieldTypeRequest.getPresentationAttribute();
        if (StringUtils.isEmpty(fieldMetadata.getCollectionCeilingEntity())) {
            fieldMetadata.setCollectionCeilingEntity(addMetadataFromFieldTypeRequest.getType().getReturnedClass().getName());
            AdornedTargetList targetList = ((AdornedTargetList) fieldMetadata.getPersistencePerspective().
                    getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST));
            targetList.setAdornedTargetEntityClassname(fieldMetadata.getCollectionCeilingEntity());
        }
        return MetadataProviderResponse.HANDLED;
    }

    protected FieldMetadataOverride overrideAdornedTargetMergeMetadata(AdminPresentationMergeOverride merge) {
        FieldMetadataOverride fieldMetadataOverride = new FieldMetadataOverride();
        Map<String, AdminPresentationMergeEntry> overrideValues = getAdminPresentationEntries(merge.mergeEntries());
        for (Map.Entry<String, AdminPresentationMergeEntry> entry : overrideValues.entrySet()) {
            String stringValue = entry.getValue().overrideValue();
            if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.CURRENCYCODEFIELD)) {
                fieldMetadataOverride.setCurrencyCodeField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.CUSTOMCRITERIA)) {
                fieldMetadataOverride.setCustomCriteria(entry.getValue().stringArrayOverrideValue());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.EXCLUDED)) {
                fieldMetadataOverride.setExcluded(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                    Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.FRIENDLYNAME)) {
                fieldMetadataOverride.setFriendlyName(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.GRIDVISIBLEFIELDS)) {
                fieldMetadataOverride.setGridVisibleFields(entry.getValue().stringArrayOverrideValue());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.IGNOREADORNEDPROPERTIES)) {
                fieldMetadataOverride.setIgnoreAdornedProperties(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                    Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.JOINENTITYCLASS)) {
                fieldMetadataOverride.setJoinEntityClass(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.MAINTAINEDADORNEDTARGETFIELDS)) {
                fieldMetadataOverride.setMaintainedAdornedTargetFields(entry.getValue().stringArrayOverrideValue());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.OPERATIONTYPES)) {
                AdminPresentationOperationTypes operationType = entry.getValue().operationTypes();
                fieldMetadataOverride.setAddType(operationType.addType());
                fieldMetadataOverride.setRemoveType(operationType.removeType());
                fieldMetadataOverride.setUpdateType(operationType.updateType());
                fieldMetadataOverride.setFetchType(operationType.fetchType());
                fieldMetadataOverride.setInspectType(operationType.inspectType());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.ORDER)) {
                fieldMetadataOverride.setOrder(StringUtils.isEmpty(stringValue) ? entry.getValue().intOverrideValue() :
                        Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.PARENTOBJECTIDPROPERTY)) {
                fieldMetadataOverride.setParentObjectIdProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.PARENTOBJECTPROPERTY)) {
                fieldMetadataOverride.setParentObjectProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.READONLY)) {
                fieldMetadataOverride.setReadOnly(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .booleanOverrideValue() :
                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.SECURITYLEVEL)) {
                fieldMetadataOverride.setSecurityLevel(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.SHOWIFPROPERTY)) {
                fieldMetadataOverride.setShowIfProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.SORTASCENDING)) {
                fieldMetadataOverride.setSortAscending(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .booleanOverrideValue() :
                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.SORTPROPERTY)) {
                fieldMetadataOverride.setSortProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.TAB)) {
                fieldMetadataOverride.setTab(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.TABORDER)) {
                fieldMetadataOverride.setTabOrder(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .intOverrideValue() : Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.TARGETOBJECTIDPROPERTY)) {
                fieldMetadataOverride.setTargetObjectIdProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.TARGETOBJECTPROPERTY)) {
                fieldMetadataOverride.setTargetObjectProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationAdornedTargetCollection.USESERVERSIDEINSPECTIONCACHE)) {
                fieldMetadataOverride.setUseServerSideInspectionCache(StringUtils.isEmpty(stringValue) ? entry
                        .getValue().booleanOverrideValue() :
                        Boolean.parseBoolean(stringValue));
            } else {
                if (LOG.isDebugEnabled()) {
                    LOG.debug("Unrecognized type: " + entry.getKey() + ". Not setting on adorned target field.");
                }
            }
        }

        return fieldMetadataOverride;
    }

    protected void buildAdminPresentationAdornedTargetCollectionOverride(String prefix, Boolean isParentExcluded, Map<String, FieldMetadata> mergedProperties, Map<String, AdminPresentationAdornedTargetCollectionOverride> presentationAdornedTargetCollectionOverrides, String propertyName, String key, DynamicEntityDao dynamicEntityDao) {
        AdminPresentationAdornedTargetCollectionOverride override = presentationAdornedTargetCollectionOverrides.get(propertyName);
        if (override != null) {
            AdminPresentationAdornedTargetCollection annot = override.value();
            if (annot != null) {
                String testKey = prefix + key;
                if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && annot.excluded()) {
                    FieldMetadata metadata = mergedProperties.get(key);
                    if (LOG.isDebugEnabled()) {
                        LOG.debug("buildAdminPresentationAdornedTargetCollectionOverride:Excluding " + key + "because an override annotation declared " + testKey + "to be excluded");
                    }
                    metadata.setExcluded(true);
                    return;
                }
                if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && !annot.excluded()) {
                    FieldMetadata metadata = mergedProperties.get(key);
                    if (!isParentExcluded) {
                        if (LOG.isDebugEnabled()) {
                            LOG.debug("buildAdminPresentationAdornedTargetCollectionOverride:Showing " + key + "because an override annotation declared " + testKey + " to not be excluded");
                        }
                        metadata.setExcluded(false);
                    }
                }
                if (!(mergedProperties.get(key) instanceof AdornedTargetCollectionMetadata)) {
                    return;
                }
                AdornedTargetCollectionMetadata serverMetadata = (AdornedTargetCollectionMetadata) mergedProperties.get(key);
                if (serverMetadata.getTargetClass() != null) {
                    try {
                        Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                        Class<?> parentClass = null;
                        if (serverMetadata.getOwningClass() != null) {
                            parentClass = Class.forName(serverMetadata.getOwningClass());
                        }
                        String fieldName = serverMetadata.getFieldName();
                        Field field = dynamicEntityDao.getFieldManager().getField(targetClass, fieldName);
                        FieldMetadataOverride localMetadata = constructAdornedTargetCollectionMetadataOverride(annot);
                        //do not include the previous metadata - we want to construct a fresh metadata from the override annotation
                        Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                        FieldInfo info = buildFieldInfo(field);
                        buildAdornedTargetCollectionMetadata(parentClass, targetClass, temp, info, localMetadata, dynamicEntityDao);
                        AdornedTargetCollectionMetadata result = (AdornedTargetCollectionMetadata) temp.get(field.getName());
                        result.setInheritedFromType(serverMetadata.getInheritedFromType());
                        result.setAvailableToTypes(serverMetadata.getAvailableToTypes());
                        mergedProperties.put(key, result);
                        if (isParentExcluded) {
                            if (LOG.isDebugEnabled()) {
                                LOG.debug("buildAdminPresentationAdornedTargetCollectionOverride:Excluding " + key + "because the parent was excluded");
                            }
                            serverMetadata.setExcluded(true);
                        }
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                }
            }
        }
    }

    protected FieldMetadataOverride constructAdornedTargetCollectionMetadataOverride(AdminPresentationAdornedTargetCollection adornedTargetCollection) {
        if (adornedTargetCollection != null) {
            FieldMetadataOverride override = new FieldMetadataOverride();
            override.setGridVisibleFields(adornedTargetCollection.gridVisibleFields());
            override.setIgnoreAdornedProperties(adornedTargetCollection.ignoreAdornedProperties());
            override.setMaintainedAdornedTargetFields(adornedTargetCollection.maintainedAdornedTargetFields());
            override.setParentObjectIdProperty(adornedTargetCollection.parentObjectIdProperty());
            override.setParentObjectProperty(adornedTargetCollection.parentObjectProperty());
            override.setSortAscending(adornedTargetCollection.sortAscending());
            override.setSortProperty(adornedTargetCollection.sortProperty());
            override.setTargetObjectIdProperty(adornedTargetCollection.targetObjectIdProperty());
            override.setTargetObjectProperty(adornedTargetCollection.targetObjectProperty());
            override.setJoinEntityClass(adornedTargetCollection.joinEntityClass());
            override.setCustomCriteria(adornedTargetCollection.customCriteria());
            override.setUseServerSideInspectionCache(adornedTargetCollection.useServerSideInspectionCache());
            override.setExcluded(adornedTargetCollection.excluded());
            override.setFriendlyName(adornedTargetCollection.friendlyName());
            override.setReadOnly(adornedTargetCollection.readOnly());
            override.setOrder(adornedTargetCollection.order());
            override.setTab(adornedTargetCollection.tab());
            override.setTabOrder(adornedTargetCollection.tabOrder());
            override.setSecurityLevel(adornedTargetCollection.securityLevel());
            override.setAddType(adornedTargetCollection.operationTypes().addType());
            override.setFetchType(adornedTargetCollection.operationTypes().fetchType());
            override.setRemoveType(adornedTargetCollection.operationTypes().removeType());
            override.setUpdateType(adornedTargetCollection.operationTypes().updateType());
            override.setInspectType(adornedTargetCollection.operationTypes().inspectType());
            override.setShowIfProperty(adornedTargetCollection.showIfProperty());
            override.setCurrencyCodeField(adornedTargetCollection.currencyCodeField());
            return override;
        }
        throw new IllegalArgumentException("AdminPresentationAdornedTargetCollection annotation not found on field.");
    }

    protected void buildAdornedTargetCollectionMetadata(Class<?> parentClass, Class<?> targetClass, Map<String, FieldMetadata> attributes, FieldInfo field, FieldMetadataOverride adornedTargetCollectionMetadata, DynamicEntityDao dynamicEntityDao) {
        AdornedTargetCollectionMetadata serverMetadata = (AdornedTargetCollectionMetadata) attributes.get(field.getName());

        Class<?> resolvedClass = parentClass==null?targetClass:parentClass;
        AdornedTargetCollectionMetadata metadata;
        if (serverMetadata != null) {
            metadata = serverMetadata;
        } else {
            metadata = new AdornedTargetCollectionMetadata();
        }
        metadata.setTargetClass(targetClass.getName());
        metadata.setFieldName(field.getName());

        if (adornedTargetCollectionMetadata.getReadOnly() != null) {
            metadata.setMutable(!adornedTargetCollectionMetadata.getReadOnly());
        }
        if (adornedTargetCollectionMetadata.getShowIfProperty()!=null) {
            metadata.setShowIfProperty(adornedTargetCollectionMetadata.getShowIfProperty());
        }

        org.broadleafcommerce.openadmin.dto.OperationTypes dtoOperationTypes = new org.broadleafcommerce.openadmin.dto.OperationTypes(OperationType.ADORNEDTARGETLIST, OperationType.ADORNEDTARGETLIST, OperationType.ADORNEDTARGETLIST, OperationType.ADORNEDTARGETLIST, OperationType.BASIC);
        if (adornedTargetCollectionMetadata.getAddType() != null) {
            dtoOperationTypes.setAddType(adornedTargetCollectionMetadata.getAddType());
        }
        if (adornedTargetCollectionMetadata.getRemoveType() != null) {
            dtoOperationTypes.setRemoveType(adornedTargetCollectionMetadata.getRemoveType());
        }
        if (adornedTargetCollectionMetadata.getFetchType() != null) {
            dtoOperationTypes.setFetchType(adornedTargetCollectionMetadata.getFetchType());
        }
        if (adornedTargetCollectionMetadata.getInspectType() != null) {
            dtoOperationTypes.setInspectType(adornedTargetCollectionMetadata.getInspectType());
        }
        if (adornedTargetCollectionMetadata.getUpdateType() != null) {
            dtoOperationTypes.setUpdateType(adornedTargetCollectionMetadata.getUpdateType());
        }

        //don't allow additional non-persistent properties or additional foreign keys for an advanced collection datasource - they don't make sense in this context
        PersistencePerspective persistencePerspective;
        if (serverMetadata != null) {
            persistencePerspective = metadata.getPersistencePerspective();
            persistencePerspective.setOperationTypes(dtoOperationTypes);
        } else {
            persistencePerspective = new PersistencePerspective(dtoOperationTypes, new String[]{}, new ForeignKey[]{});
            metadata.setPersistencePerspective(persistencePerspective);
        }

        String parentObjectProperty = null;
        if (serverMetadata != null) {
            parentObjectProperty = ((AdornedTargetList) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST)).getLinkedObjectPath();
        }
        if (!StringUtils.isEmpty(adornedTargetCollectionMetadata.getParentObjectProperty())) {
            parentObjectProperty = adornedTargetCollectionMetadata.getParentObjectProperty();
        }
        if (parentObjectProperty == null && !StringUtils.isEmpty(field.getOneToManyMappedBy())) {
            parentObjectProperty = field.getOneToManyMappedBy();
        }
        if (parentObjectProperty == null && !StringUtils.isEmpty(field.getManyToManyMappedBy())) {
            parentObjectProperty = field.getManyToManyMappedBy();
        }
        if (StringUtils.isEmpty(parentObjectProperty)) {
            throw new IllegalArgumentException("Unable to infer a parentObjectProperty for the @AdminPresentationAdornedTargetCollection annotated field("+field.getName()+"). If not using the mappedBy property of @OneToMany or @ManyToMany, please make sure to explicitly define the parentObjectProperty property");
        }

        String sortProperty = null;
        if (serverMetadata != null) {
            sortProperty = ((AdornedTargetList) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST)).getSortField();
        }
        if (!StringUtils.isEmpty(adornedTargetCollectionMetadata.getSortProperty())) {
            sortProperty = adornedTargetCollectionMetadata.getSortProperty();
        }

        metadata.setParentObjectClass(resolvedClass.getName());
        if (adornedTargetCollectionMetadata.getMaintainedAdornedTargetFields() != null) {
            metadata.setMaintainedAdornedTargetFields(adornedTargetCollectionMetadata.getMaintainedAdornedTargetFields());
        }
        if (adornedTargetCollectionMetadata.getGridVisibleFields() != null) {
            metadata.setGridVisibleFields(adornedTargetCollectionMetadata.getGridVisibleFields());
        }
        String parentObjectIdProperty = null;
        if (serverMetadata != null) {
            parentObjectIdProperty = ((AdornedTargetList) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST)).getLinkedIdProperty();
        }
        if (adornedTargetCollectionMetadata.getParentObjectIdProperty()!=null) {
            parentObjectIdProperty = adornedTargetCollectionMetadata.getParentObjectIdProperty();
        }
        String targetObjectProperty = null;
        if (serverMetadata != null) {
            targetObjectProperty = ((AdornedTargetList) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST)).getTargetObjectPath();
        }
        if (adornedTargetCollectionMetadata.getTargetObjectProperty()!=null) {
            targetObjectProperty = adornedTargetCollectionMetadata.getTargetObjectProperty();
        }
        if (StringUtils.isEmpty(parentObjectIdProperty)) {
            throw new IllegalArgumentException("targetObjectProperty not defined");
        }

        String joinEntityClass = null;
        if (serverMetadata != null) {
            joinEntityClass = ((AdornedTargetList) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST)).getJoinEntityClass();
        }
        if (adornedTargetCollectionMetadata.getJoinEntityClass() != null) {
            joinEntityClass = adornedTargetCollectionMetadata.getJoinEntityClass();
        }

        Class<?> collectionTarget = null;
        try {
            checkCeiling: {
                try {
                    ParameterizedType pt = (ParameterizedType) field.getGenericType();
                    java.lang.reflect.Type collectionType = pt.getActualTypeArguments()[0];
                    String ceilingEntityName = ((Class<?>) collectionType).getName();
                    collectionTarget = entityConfiguration.lookupEntityClass(ceilingEntityName);
                    break checkCeiling;
                } catch (NoSuchBeanDefinitionException e) {
                    // We weren't successful at looking at entity configuration to find the type of this collection.
                    // We will continue and attempt to find it via the Hibernate annotations
                }
                if (!StringUtils.isEmpty(field.getOneToManyTargetEntity()) && !void.class.getName().equals(field.getOneToManyTargetEntity())) {
                    collectionTarget = Class.forName(field.getOneToManyTargetEntity());
                    break checkCeiling;
                }
                if (!StringUtils.isEmpty(field.getManyToManyTargetEntity()) && !void.class.getName().equals(field.getManyToManyTargetEntity())) {
                    collectionTarget = Class.forName(field.getManyToManyTargetEntity());
                    break checkCeiling;
                }
            }
            if (StringUtils.isNotBlank(joinEntityClass)) {
                collectionTarget = Class.forName(joinEntityClass);
            }
        } catch (ClassNotFoundException e) {
            throw new RuntimeException(e);
        }
        if (collectionTarget == null) {
            throw new IllegalArgumentException("Unable to infer the type of the collection from the targetEntity property of a OneToMany or ManyToMany collection.");
        }
        Field collectionTargetField = dynamicEntityDao.getFieldManager().getField(collectionTarget, targetObjectProperty);
        ManyToOne manyToOne = collectionTargetField.getAnnotation(ManyToOne.class);
        String ceiling = null;
        checkCeiling: {
            if (manyToOne != null && manyToOne.targetEntity() != void.class) {
                ceiling = manyToOne.targetEntity().getName();
                break checkCeiling;
            }
            ceiling = collectionTargetField.getType().getName();
        }
        if (!StringUtils.isEmpty(ceiling)) {
            metadata.setCollectionCeilingEntity(ceiling);
        }

        String targetObjectIdProperty = null;
        if (serverMetadata != null) {
            targetObjectIdProperty = ((AdornedTargetList) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST)).getTargetIdProperty();
        }
        if (adornedTargetCollectionMetadata.getTargetObjectIdProperty()!=null) {
            targetObjectIdProperty = adornedTargetCollectionMetadata.getTargetObjectIdProperty();
        }
        Boolean isAscending = true;
        if (serverMetadata != null) {
            isAscending = ((AdornedTargetList) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST)).getSortAscending();
        }
        if (adornedTargetCollectionMetadata.isSortAscending()!=null) {
            isAscending = adornedTargetCollectionMetadata.isSortAscending();
        }

        if (serverMetadata != null) {
            AdornedTargetList adornedTargetList = (AdornedTargetList) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.ADORNEDTARGETLIST);
            adornedTargetList.setCollectionFieldName(field.getName());
            adornedTargetList.setLinkedObjectPath(parentObjectProperty);
            adornedTargetList.setLinkedIdProperty(parentObjectIdProperty);
            adornedTargetList.setTargetObjectPath(targetObjectProperty);
            adornedTargetList.setTargetIdProperty(targetObjectIdProperty);
            adornedTargetList.setJoinEntityClass(joinEntityClass);
            adornedTargetList.setIdProperty((String) dynamicEntityDao.getIdMetadata(collectionTarget).get("name"));
            adornedTargetList.setAdornedTargetEntityClassname(collectionTarget.getName());
            adornedTargetList.setSortField(sortProperty);
            adornedTargetList.setSortAscending(isAscending);
            adornedTargetList.setMutable(metadata.isMutable());
        } else {
            AdornedTargetList adornedTargetList = new AdornedTargetList(field.getName(), parentObjectProperty, parentObjectIdProperty, targetObjectProperty, targetObjectIdProperty, collectionTarget.getName(), sortProperty, isAscending);
            adornedTargetList.setJoinEntityClass(joinEntityClass);
            adornedTargetList.setIdProperty((String) dynamicEntityDao.getIdMetadata(collectionTarget).get("name"));
            adornedTargetList.setMutable(metadata.isMutable());
            persistencePerspective.addPersistencePerspectiveItem(PersistencePerspectiveItemType.ADORNEDTARGETLIST, adornedTargetList);
        }

        if (adornedTargetCollectionMetadata.getExcluded() != null) {
            if (LOG.isDebugEnabled()) {
                if (adornedTargetCollectionMetadata.getExcluded()) {
                    LOG.debug("buildAdornedTargetCollectionMetadata:Excluding " + field.getName() + " because it was explicitly declared in config");
                } else {
                    LOG.debug("buildAdornedTargetCollectionMetadata:Showing " + field.getName() + " because it was explicitly declared in config");
                }
            }
            metadata.setExcluded(adornedTargetCollectionMetadata.getExcluded());
        }
        if (adornedTargetCollectionMetadata.getFriendlyName() != null) {
            metadata.setFriendlyName(adornedTargetCollectionMetadata.getFriendlyName());
        }
        if (adornedTargetCollectionMetadata.getSecurityLevel() != null) {
            metadata.setSecurityLevel(adornedTargetCollectionMetadata.getSecurityLevel());
        }
        if (adornedTargetCollectionMetadata.getOrder() != null) {
            metadata.setOrder(adornedTargetCollectionMetadata.getOrder());
        }

        if (adornedTargetCollectionMetadata.getTab() != null) {
            metadata.setTab(adornedTargetCollectionMetadata.getTab());
        }
        if (adornedTargetCollectionMetadata.getTabOrder() != null) {
            metadata.setTabOrder(adornedTargetCollectionMetadata.getTabOrder());
        }

        if (adornedTargetCollectionMetadata.getCustomCriteria() != null) {
            metadata.setCustomCriteria(adornedTargetCollectionMetadata.getCustomCriteria());
        }

        if (adornedTargetCollectionMetadata.getUseServerSideInspectionCache() != null) {
            persistencePerspective.setUseServerSideInspectionCache(adornedTargetCollectionMetadata.getUseServerSideInspectionCache());
        }

        if (adornedTargetCollectionMetadata.isIgnoreAdornedProperties() != null) {
            metadata.setIgnoreAdornedProperties(adornedTargetCollectionMetadata.isIgnoreAdornedProperties());
        }
        if (adornedTargetCollectionMetadata.getCurrencyCodeField()!=null) {
            metadata.setCurrencyCodeField(adornedTargetCollectionMetadata.getCurrencyCodeField());
        }

        attributes.put(field.getName(), metadata);
    }

    @Override
    public int getOrder() {
        return FieldMetadataProvider.ADORNED_TARGET;
    }
}


File: admin/broadleaf-open-admin-platform/src/main/java/org/broadleafcommerce/openadmin/server/dao/provider/metadata/BasicFieldMetadataProvider.java
/*
 * #%L
 * BroadleafCommerce Open Admin Platform
 * %%
 * Copyright (C) 2009 - 2013 Broadleaf Commerce
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */
package org.broadleafcommerce.openadmin.server.dao.provider.metadata;

import org.apache.commons.lang.ArrayUtils;
import org.apache.commons.lang.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.broadleafcommerce.common.enumeration.domain.DataDrivenEnumerationValueImpl;
import org.broadleafcommerce.common.presentation.AdminPresentation;
import org.broadleafcommerce.common.presentation.AdminPresentationDataDrivenEnumeration;
import org.broadleafcommerce.common.presentation.AdminPresentationToOneLookup;
import org.broadleafcommerce.common.presentation.ConfigurationItem;
import org.broadleafcommerce.common.presentation.OptionFilterParam;
import org.broadleafcommerce.common.presentation.OptionFilterParamType;
import org.broadleafcommerce.common.presentation.RequiredOverride;
import org.broadleafcommerce.common.presentation.ValidationConfiguration;
import org.broadleafcommerce.common.presentation.client.LookupType;
import org.broadleafcommerce.common.presentation.client.SupportedFieldType;
import org.broadleafcommerce.common.presentation.client.VisibilityEnum;
import org.broadleafcommerce.common.presentation.override.AdminPresentationDataDrivenEnumerationOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeEntry;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeOverrides;
import org.broadleafcommerce.common.presentation.override.AdminPresentationOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationOverrides;
import org.broadleafcommerce.common.presentation.override.AdminPresentationToOneLookupOverride;
import org.broadleafcommerce.common.presentation.override.PropertyType;
import org.broadleafcommerce.openadmin.dto.BasicFieldMetadata;
import org.broadleafcommerce.openadmin.dto.FieldMetadata;
import org.broadleafcommerce.openadmin.dto.override.FieldMetadataOverride;
import org.broadleafcommerce.openadmin.server.dao.DynamicEntityDao;
import org.broadleafcommerce.openadmin.server.dao.FieldInfo;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaAnnotationRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaXmlRequest;
import org.broadleafcommerce.openadmin.server.service.type.MetadataProviderResponse;
import org.hibernate.Criteria;
import org.hibernate.criterion.Restrictions;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.io.Serializable;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * @author Jeff Fischer
 */
@Component("blBasicFieldMetadataProvider")
@Scope("prototype")
public class BasicFieldMetadataProvider extends FieldMetadataProviderAdapter {

    private static final Log LOG = LogFactory.getLog(BasicFieldMetadataProvider.class);

    protected boolean canHandleFieldForConfiguredMetadata(AddMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentation annot = addMetadataRequest.getRequestedField().getAnnotation(AdminPresentation.class);
        return annot != null;
    }

    protected boolean canHandleAnnotationOverride(OverrideViaAnnotationRequest overrideViaAnnotationRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentationOverrides myOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationOverrides.class);
        AdminPresentationMergeOverrides myMergeOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationMergeOverrides.class);
        return (myOverrides != null && (!ArrayUtils.isEmpty(myOverrides.value()) || !ArrayUtils.isEmpty(myOverrides
                .toOneLookups()) || !ArrayUtils.isEmpty(myOverrides.dataDrivenEnums()))) ||
                myMergeOverrides != null;
    }

    @Override
    public MetadataProviderResponse addMetadata(AddFieldMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleFieldForConfiguredMetadata(addMetadataRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        AdminPresentation annot = addMetadataRequest.getRequestedField().getAnnotation(AdminPresentation.class);
        FieldInfo info = buildFieldInfo(addMetadataRequest.getRequestedField());
        FieldMetadataOverride override = constructBasicMetadataOverride(annot, addMetadataRequest.getRequestedField().getAnnotation(AdminPresentationToOneLookup.class),
                addMetadataRequest.getRequestedField().getAnnotation(AdminPresentationDataDrivenEnumeration.class));
        buildBasicMetadata(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(), metadata, info, override, addMetadataRequest.getDynamicEntityDao());
        setClassOwnership(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(), metadata, info);
        return MetadataProviderResponse.HANDLED;
    }

    @Override
    public MetadataProviderResponse overrideViaAnnotation(OverrideViaAnnotationRequest overrideViaAnnotationRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleAnnotationOverride(overrideViaAnnotationRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        Map<String, AdminPresentationOverride> presentationOverrides = new LinkedHashMap<String, AdminPresentationOverride>();
        Map<String, AdminPresentationToOneLookupOverride> presentationToOneLookupOverrides = new LinkedHashMap<String, AdminPresentationToOneLookupOverride>();
        Map<String, AdminPresentationDataDrivenEnumerationOverride> presentationDataDrivenEnumerationOverrides = new LinkedHashMap<String, AdminPresentationDataDrivenEnumerationOverride>();

        AdminPresentationOverrides myOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationOverrides.class);
        if (myOverrides != null) {
            for (AdminPresentationOverride myOverride : myOverrides.value()) {
                presentationOverrides.put(myOverride.name(), myOverride);
            }
            for (AdminPresentationToOneLookupOverride myOverride : myOverrides.toOneLookups()) {
                presentationToOneLookupOverrides.put(myOverride.name(), myOverride);
            }
            for (AdminPresentationDataDrivenEnumerationOverride myOverride : myOverrides.dataDrivenEnums()) {
                presentationDataDrivenEnumerationOverrides.put(myOverride.name(), myOverride);
            }
        }

        for (String propertyName : presentationOverrides.keySet()) {
            for (String key : metadata.keySet()) {
                if (StringUtils.isEmpty(propertyName) || key.startsWith(propertyName)) {
                    buildAdminPresentationOverride(overrideViaAnnotationRequest.getPrefix(), overrideViaAnnotationRequest.getParentExcluded(), metadata, presentationOverrides, propertyName, key, overrideViaAnnotationRequest.getDynamicEntityDao());
                }
            }
        }
        for (String propertyName : presentationToOneLookupOverrides.keySet()) {
            for (String key : metadata.keySet()) {
                if (key.startsWith(propertyName)) {
                    buildAdminPresentationToOneLookupOverride(metadata, presentationToOneLookupOverrides, propertyName, key);
                }
            }
        }
        for (String propertyName : presentationDataDrivenEnumerationOverrides.keySet()) {
            for (String key : metadata.keySet()) {
                if (key.startsWith(propertyName)) {
                    buildAdminPresentationDataDrivenEnumerationOverride(metadata, presentationDataDrivenEnumerationOverrides, propertyName, key,
                            overrideViaAnnotationRequest.getDynamicEntityDao());
                }
            }
        }

        AdminPresentationMergeOverrides myMergeOverrides = overrideViaAnnotationRequest.getRequestedEntity().
                getAnnotation(AdminPresentationMergeOverrides.class);
        if (myMergeOverrides != null) {
            for (AdminPresentationMergeOverride override : myMergeOverrides.value()) {
                String propertyName = override.name();
                Map<String, FieldMetadata> loopMap = new HashMap<String, FieldMetadata>();
                loopMap.putAll(metadata);
                for (Map.Entry<String, FieldMetadata> entry : loopMap.entrySet()) {
                    if (entry.getKey().startsWith(propertyName) || StringUtils.isEmpty(propertyName)) {
                        FieldMetadata targetMetadata = entry.getValue();
                        if (targetMetadata instanceof BasicFieldMetadata) {
                            BasicFieldMetadata serverMetadata = (BasicFieldMetadata) targetMetadata;
                            if (serverMetadata.getTargetClass() != null) {
                                try {
                                    Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                                    Class<?> parentClass = null;
                                    if (serverMetadata.getOwningClass() != null) {
                                        parentClass = Class.forName(serverMetadata.getOwningClass());
                                    }
                                    String fieldName = serverMetadata.getFieldName();
                                    Field field = overrideViaAnnotationRequest.getDynamicEntityDao().getFieldManager()
                                                .getField(targetClass, fieldName);
                                    Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                                    temp.put(fieldName, serverMetadata);
                                    FieldInfo info;
                                    if (field != null) {
                                        info = buildFieldInfo(field);
                                    } else {
                                        info = new FieldInfo();
                                        info.setName(fieldName);
                                    }
                                    FieldMetadataOverride fieldMetadataOverride = overrideMergeMetadata(override);
                                    if (serverMetadata.getExcluded() != null && serverMetadata.getExcluded() &&
                                            (fieldMetadataOverride.getExcluded() == null || fieldMetadataOverride.getExcluded())) {
                                        continue;
                                    }
                                    buildBasicMetadata(parentClass, targetClass, temp, info, fieldMetadataOverride,
                                            overrideViaAnnotationRequest.getDynamicEntityDao());
                                    serverMetadata = (BasicFieldMetadata) temp.get(fieldName);
                                    metadata.put(entry.getKey(), serverMetadata);
                                } catch (Exception e) {
                                    throw new RuntimeException(e);
                                }
                            }
                        }
                    }
                }
            }
        }

        return MetadataProviderResponse.HANDLED;
    }

    @Override
        Map<String, FieldMetadataOverride> overrides = getTargetedOverride(overrideViaXmlRequest.getDynamicEntityDao(), overrideViaXmlRequest.getRequestedConfigKey(), overrideViaXmlRequest.getRequestedCeilingEntity());
    public MetadataProviderResponse overrideViaXml(OverrideViaXmlRequest overrideViaXmlRequest, Map<String, FieldMetadata> metadata) {
        if (overrides != null) {
            for (String propertyName : overrides.keySet()) {
                final FieldMetadataOverride localMetadata = overrides.get(propertyName);
                for (String key : metadata.keySet()) {
                    if (key.equals(propertyName)) {
                        try {
                            if (metadata.get(key) instanceof BasicFieldMetadata) {
                                BasicFieldMetadata serverMetadata = (BasicFieldMetadata) metadata.get(key);
                                if (serverMetadata.getTargetClass() != null) {
                                    Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                                    Class<?> parentClass = null;
                                    if (serverMetadata.getOwningClass() != null) {
                                        parentClass = Class.forName(serverMetadata.getOwningClass());
                                    }
                                    String fieldName = serverMetadata.getFieldName();
                                    Field field = overrideViaXmlRequest.getDynamicEntityDao().getFieldManager().getField(targetClass, fieldName);
                                    Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                                    temp.put(field.getName(), serverMetadata);
                                    FieldInfo info = buildFieldInfo(field);
                                    buildBasicMetadata(parentClass, targetClass, temp, info, localMetadata,
                                            overrideViaXmlRequest.getDynamicEntityDao());
                                    serverMetadata = (BasicFieldMetadata) temp.get(field.getName());
                                    metadata.put(key, serverMetadata);
                                    if (overrideViaXmlRequest.getParentExcluded()) {
                                        if (LOG.isDebugEnabled()) {
                                            LOG.debug("applyMetadataOverrides:Excluding " + key + "because the parent was excluded");
                                        }
                                        serverMetadata.setExcluded(true);
                                    }
                                }
                            }
                        } catch (Exception e) {
                            throw new RuntimeException(e);
                        }
                    }
                }
            }
        }
        return MetadataProviderResponse.HANDLED;
    }

    protected void buildAdminPresentationToOneLookupOverride(Map<String, FieldMetadata> mergedProperties, Map<String, AdminPresentationToOneLookupOverride> presentationOverrides, String propertyName, String key) {
        AdminPresentationToOneLookupOverride override = presentationOverrides.get(propertyName);
        if (override != null) {
            AdminPresentationToOneLookup annot = override.value();
            if (annot != null) {
                if (!(mergedProperties.get(key) instanceof BasicFieldMetadata)) {
                    return;
                }
                BasicFieldMetadata metadata = (BasicFieldMetadata) mergedProperties.get(key);
                metadata.setFieldType(SupportedFieldType.ADDITIONAL_FOREIGN_KEY);
                metadata.setExplicitFieldType(SupportedFieldType.ADDITIONAL_FOREIGN_KEY);
                metadata.setLookupDisplayProperty(annot.lookupDisplayProperty());
                metadata.setForcePopulateChildProperties(annot.forcePopulateChildProperties());
                metadata.setEnableTypeaheadLookup(annot.enableTypeaheadLookup());
                if (!StringUtils.isEmpty(annot.lookupDisplayProperty())) {
                    metadata.setForeignKeyDisplayValueProperty(annot.lookupDisplayProperty());
                }
                metadata.setCustomCriteria(annot.customCriteria());
                metadata.setUseServerSideInspectionCache(annot.useServerSideInspectionCache());
            }
        }
    }

    protected void buildAdminPresentationDataDrivenEnumerationOverride(Map<String, FieldMetadata> mergedProperties, Map<String, AdminPresentationDataDrivenEnumerationOverride> presentationOverrides, String propertyName, String key, DynamicEntityDao dynamicEntityDao) {
        AdminPresentationDataDrivenEnumerationOverride override = presentationOverrides.get(propertyName);
        if (override != null) {
            AdminPresentationDataDrivenEnumeration annot = override.value();
            if (annot != null) {
                if (!(mergedProperties.get(key) instanceof BasicFieldMetadata)) {
                    return;
                }
                BasicFieldMetadata metadata = (BasicFieldMetadata) mergedProperties.get(key);
                metadata.setFieldType(SupportedFieldType.DATA_DRIVEN_ENUMERATION);
                metadata.setExplicitFieldType(SupportedFieldType.DATA_DRIVEN_ENUMERATION);
                metadata.setOptionListEntity(annot.optionListEntity().getName());
                if (metadata.getOptionListEntity().equals(DataDrivenEnumerationValueImpl.class.getName())) {
                    metadata.setOptionValueFieldName("key");
                    metadata.setOptionDisplayFieldName("display");
                } else if (metadata.getOptionListEntity() == null && (StringUtils.isEmpty(metadata.getOptionValueFieldName()) || StringUtils.isEmpty(metadata.getOptionDisplayFieldName()))) {
                    throw new IllegalArgumentException("Problem setting up data driven enumeration for ("+propertyName+"). The optionListEntity, optionValueFieldName and optionDisplayFieldName properties must all be included if not using DataDrivenEnumerationValueImpl as the optionListEntity.");
                } else {
                    metadata.setOptionValueFieldName(annot.optionValueFieldName());
                    metadata.setOptionDisplayFieldName(annot.optionDisplayFieldName());
                }
                if (!ArrayUtils.isEmpty(annot.optionFilterParams())) {
                    String[][] params = new String[annot.optionFilterParams().length][3];
                    for (int j=0;j<params.length;j++) {
                        params[j][0] = annot.optionFilterParams()[j].param();
                        params[j][1] = annot.optionFilterParams()[j].value();
                        params[j][2] = String.valueOf(annot.optionFilterParams()[j].paramType());
                    }
                    metadata.setOptionFilterParams(params);
                } else {
                    metadata.setOptionFilterParams(new String[][]{});
                }
                if (!StringUtils.isEmpty(metadata.getOptionListEntity())) {
                    buildDataDrivenList(metadata, dynamicEntityDao);
                }
            }
        }
    }

    protected void buildAdminPresentationOverride(String prefix, Boolean isParentExcluded, Map<String, FieldMetadata> mergedProperties, Map<String, AdminPresentationOverride> presentationOverrides, String propertyName, String key, DynamicEntityDao dynamicEntityDao) {
        AdminPresentationOverride override = presentationOverrides.get(propertyName);
        if (override != null) {
            AdminPresentation annot = override.value();
            if (annot != null) {
                String testKey = prefix + key;
                if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && annot.excluded()) {
                    FieldMetadata metadata = mergedProperties.get(key);
                    if (LOG.isDebugEnabled()) {
                        LOG.debug("buildAdminPresentationOverride:Excluding " + key + "because an override annotation declared "+ testKey + " to be excluded");
                    }
                    metadata.setExcluded(true);
                    return;
                }
                if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && !annot.excluded()) {
                    FieldMetadata metadata = mergedProperties.get(key);
                    if (!isParentExcluded) {
                        if (LOG.isDebugEnabled()) {
                            LOG.debug("buildAdminPresentationOverride:Showing " + key + "because an override annotation declared " + testKey + " to not be excluded");
                        }
                        metadata.setExcluded(false);
                    }
                }
                if (!(mergedProperties.get(key) instanceof BasicFieldMetadata)) {
                    return;
                }
                BasicFieldMetadata serverMetadata = (BasicFieldMetadata) mergedProperties.get(key);
                if (serverMetadata.getTargetClass() != null) {
                    try {
                        Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                        Class<?> parentClass = null;
                        if (serverMetadata.getOwningClass() != null) {
                            parentClass = Class.forName(serverMetadata.getOwningClass());
                        }
                        String fieldName = serverMetadata.getFieldName();
                        Field field = dynamicEntityDao.getFieldManager().getField(targetClass, fieldName);
                        FieldMetadataOverride localMetadata = constructBasicMetadataOverride(annot, null, null);
                        //do not include the previous metadata - we want to construct a fresh metadata from the override annotation
                        Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                        FieldInfo info = buildFieldInfo(field);
                        buildBasicMetadata(parentClass, targetClass, temp, info, localMetadata, dynamicEntityDao);
                        BasicFieldMetadata result = (BasicFieldMetadata) temp.get(field.getName());
                        result.setInheritedFromType(serverMetadata.getInheritedFromType());
                        result.setAvailableToTypes(serverMetadata.getAvailableToTypes());

                        result.setFieldType(serverMetadata.getFieldType());
                        result.setSecondaryType(serverMetadata.getSecondaryType());
                        result.setLength(serverMetadata.getLength());
                        result.setScale(serverMetadata.getScale());
                        result.setPrecision(serverMetadata.getPrecision());
                        result.setRequired(serverMetadata.getRequired());
                        result.setUnique(serverMetadata.getUnique());
                        result.setForeignKeyCollection(serverMetadata.getForeignKeyCollection());
                        result.setMutable(serverMetadata.getMutable());
                        result.setMergedPropertyType(serverMetadata.getMergedPropertyType());
                        mergedProperties.put(key, result);
                        if (isParentExcluded) {
                            if (LOG.isDebugEnabled()) {
                                LOG.debug("buildAdminPresentationOverride:Excluding " + key + "because the parent was excluded");
                            }
                            serverMetadata.setExcluded(true);
                        }
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                }
            }
        }
    }

    protected FieldMetadataOverride overrideMergeMetadata(AdminPresentationMergeOverride merge) {
        FieldMetadataOverride fieldMetadataOverride = new FieldMetadataOverride();
        Map<String, AdminPresentationMergeEntry> overrideValues = getAdminPresentationEntries(merge.mergeEntries());
        for (Map.Entry<String, AdminPresentationMergeEntry> entry : overrideValues.entrySet()) {
            String stringValue = entry.getValue().overrideValue();
            if (entry.getKey().equals(PropertyType.AdminPresentation.FRIENDLYNAME)) {
                fieldMetadataOverride.setFriendlyName(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.SECURITYLEVEL)) {
                fieldMetadataOverride.setSecurityLevel(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.GROUP)) {
                fieldMetadataOverride.setGroup(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.TAB)) {
                fieldMetadataOverride.setTab(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.COLUMNWIDTH)) {
                fieldMetadataOverride.setColumnWidth(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.BROADLEAFENUMERATION)) {
                fieldMetadataOverride.setBroadleafEnumeration(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.TOOLTIP)) {
                fieldMetadataOverride.setTooltip(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.HELPTEXT)) {
                fieldMetadataOverride.setHelpText(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.HINT)) {
                fieldMetadataOverride.setHint(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.SHOWIFPROPERTY)) {
                fieldMetadataOverride.setShowIfProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.CURRENCYCODEFIELD)) {
                fieldMetadataOverride.setCurrencyCodeField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.RULEIDENTIFIER)) {
                fieldMetadataOverride.setRuleIdentifier(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.ORDER)) {
                fieldMetadataOverride.setOrder(StringUtils.isEmpty(stringValue)?entry.getValue().intOverrideValue():
                                        Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.GRIDORDER)) {
                fieldMetadataOverride.setGridOrder(StringUtils.isEmpty(stringValue)?entry.getValue().intOverrideValue():
                                        Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.VISIBILITY)) {
                fieldMetadataOverride.setVisibility(VisibilityEnum.valueOf(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.FIELDTYPE)) {
                fieldMetadataOverride.setFieldType(SupportedFieldType.valueOf(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.GROUPORDER)) {
                fieldMetadataOverride.setGroupOrder(StringUtils.isEmpty(stringValue)?entry.getValue().intOverrideValue():
                                        Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.GROUPCOLLAPSED)) {
                fieldMetadataOverride.setGroupCollapsed(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.TABORDER)) {
                fieldMetadataOverride.setTabOrder(StringUtils.isEmpty(stringValue)?entry.getValue().intOverrideValue():
                                        Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.LARGEENTRY)) {
                fieldMetadataOverride.setLargeEntry(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.PROMINENT)) {
                fieldMetadataOverride.setProminent(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.READONLY)) {
                fieldMetadataOverride.setReadOnly(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.REQUIREDOVERRIDE)) {
                if (RequiredOverride.IGNORED!=RequiredOverride.valueOf(stringValue)) {
                    fieldMetadataOverride.setRequiredOverride(RequiredOverride.REQUIRED==RequiredOverride.valueOf(stringValue));
                }
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.EXCLUDED)) {
                fieldMetadataOverride.setExcluded(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.DEFAULTVALUE)) {
                fieldMetadataOverride.setDefaultValue(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentation.VALIDATIONCONFIGURATIONS)) {
                processValidationAnnotations(entry.getValue().validationConfigurations(), fieldMetadataOverride);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationToOneLookup.LOOKUPDISPLAYPROPERTY)) {
                fieldMetadataOverride.setLookupDisplayProperty(stringValue);
                fieldMetadataOverride.setForeignKeyDisplayValueProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationToOneLookup.FORCEPOPULATECHILDPROPERTIES)) {
                fieldMetadataOverride.setForcePopulateChildProperties(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationToOneLookup.ENABLETYPEAHEADLOOKUP)) {
                fieldMetadataOverride.setEnableTypeaheadLookup(StringUtils.isEmpty(stringValue)?entry.getValue().booleanOverrideValue():
                                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationToOneLookup.USESERVERSIDEINSPECTIONCACHE)) {
                fieldMetadataOverride.setUseServerSideInspectionCache(StringUtils.isEmpty(stringValue)?
                                        entry.getValue().booleanOverrideValue():Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationToOneLookup.LOOKUPTYPE)) {
                fieldMetadataOverride.setLookupType(LookupType.valueOf(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationToOneLookup.CUSTOMCRITERIA)) {
                fieldMetadataOverride.setCustomCriteria(entry.getValue().stringArrayOverrideValue());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationDataDrivenEnumeration.OPTIONLISTENTITY)) {
                fieldMetadataOverride.setOptionListEntity(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationDataDrivenEnumeration.OPTIONVALUEFIELDNAME)) {
                fieldMetadataOverride.setOptionValueFieldName(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationDataDrivenEnumeration.OPTIONDISPLAYFIELDNAME)) {
                fieldMetadataOverride.setOptionDisplayFieldName(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationDataDrivenEnumeration.OPTIONCANEDITVALUES)) {
                fieldMetadataOverride.setOptionCanEditValues(StringUtils.isEmpty(stringValue) ? entry.getValue()
                                        .booleanOverrideValue() : Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationDataDrivenEnumeration.OPTIONFILTERPARAMS)) {
                OptionFilterParam[] optionFilterParams = entry.getValue().optionFilterParams();
                String[][] params = new String[optionFilterParams.length][3];
                for (int j=0;j<params.length;j++) {
                    params[j][0] = optionFilterParams[j].param();
                    params[j][1] = optionFilterParams[j].value();
                    params[j][2] = String.valueOf(optionFilterParams[j].paramType());
                }
                fieldMetadataOverride.setOptionFilterValues(params);
            } else {
                if (LOG.isDebugEnabled()) {
                    LOG.debug("Unrecognized type: " + entry.getKey() + ". Not setting on basic field.");
                }
            }
        }

        return fieldMetadataOverride;
    }

    protected FieldMetadataOverride constructBasicMetadataOverride(AdminPresentation annot, AdminPresentationToOneLookup toOneLookup,
                                                                   AdminPresentationDataDrivenEnumeration dataDrivenEnumeration) {
        if (annot != null) {
            FieldMetadataOverride override = new FieldMetadataOverride();
            override.setBroadleafEnumeration(annot.broadleafEnumeration());
            override.setColumnWidth(annot.columnWidth());
            override.setExplicitFieldType(annot.fieldType());
            override.setFieldType(annot.fieldType());
            override.setGroup(annot.group());
            override.setGroupCollapsed(annot.groupCollapsed());
            override.setGroupOrder(annot.groupOrder());
            override.setTab(annot.tab());
            override.setRuleIdentifier(annot.ruleIdentifier());
            override.setTabOrder(annot.tabOrder());
            override.setHelpText(annot.helpText());
            override.setHint(annot.hint());
            override.setLargeEntry(annot.largeEntry());
            override.setFriendlyName(annot.friendlyName());
            override.setSecurityLevel(annot.securityLevel());
            override.setOrder(annot.order());
            override.setGridOrder(annot.gridOrder());
            override.setVisibility(annot.visibility());
            override.setProminent(annot.prominent());
            override.setReadOnly(annot.readOnly());
            override.setShowIfProperty(annot.showIfProperty());
            override.setCurrencyCodeField(annot.currencyCodeField());
            override.setRuleIdentifier(annot.ruleIdentifier());
            override.setTranslatable(annot.translatable());
            override.setDefaultValue(annot.defaultValue());

            if (annot.validationConfigurations().length != 0) {
                processValidationAnnotations(annot.validationConfigurations(), override);
            }
            if (annot.requiredOverride()!= RequiredOverride.IGNORED) {
                override.setRequiredOverride(annot.requiredOverride()==RequiredOverride.REQUIRED);
            }
            override.setExcluded(annot.excluded());
            override.setTooltip(annot.tooltip());

            //the following annotations are complimentary to AdminPresentation
            if (toOneLookup != null) {
                override.setExplicitFieldType(SupportedFieldType.ADDITIONAL_FOREIGN_KEY);
                override.setFieldType(SupportedFieldType.ADDITIONAL_FOREIGN_KEY);
                override.setLookupDisplayProperty(toOneLookup.lookupDisplayProperty());
                override.setForcePopulateChildProperties(toOneLookup.forcePopulateChildProperties());
                override.setEnableTypeaheadLookup(toOneLookup.enableTypeaheadLookup());
                override.setCustomCriteria(toOneLookup.customCriteria());
                override.setUseServerSideInspectionCache(toOneLookup.useServerSideInspectionCache());
                override.setToOneLookupCreatedViaAnnotation(true);
                override.setLookupType(toOneLookup.lookupType());
            }

            if (dataDrivenEnumeration != null) {
                override.setExplicitFieldType(SupportedFieldType.DATA_DRIVEN_ENUMERATION);
                override.setFieldType(SupportedFieldType.DATA_DRIVEN_ENUMERATION);
                override.setOptionCanEditValues(dataDrivenEnumeration.optionCanEditValues());
                override.setOptionDisplayFieldName(dataDrivenEnumeration.optionDisplayFieldName());
                if (!ArrayUtils.isEmpty(dataDrivenEnumeration.optionFilterParams())) {
                    Serializable[][] params = new Serializable[dataDrivenEnumeration.optionFilterParams().length][3];
                    for (int j=0;j<params.length;j++) {
                        params[j][0] = dataDrivenEnumeration.optionFilterParams()[j].param();
                        params[j][1] = dataDrivenEnumeration.optionFilterParams()[j].value();
                        params[j][2] = dataDrivenEnumeration.optionFilterParams()[j].paramType();
                    }
                    override.setOptionFilterValues(params);
                }
                override.setOptionListEntity(dataDrivenEnumeration.optionListEntity().getName());
                override.setOptionValueFieldName(dataDrivenEnumeration.optionValueFieldName());
            }


            return override;
        }
        throw new IllegalArgumentException("AdminPresentation annotation not found on field");
    }

    protected void processValidationAnnotations(ValidationConfiguration[] configurations, FieldMetadataOverride override) {
        for (ValidationConfiguration configuration : configurations) {
            ConfigurationItem[] items = configuration.configurationItems();
            Map<String, String> itemMap = new HashMap<String, String>();
            for (ConfigurationItem item : items) {
                itemMap.put(item.itemName(), item.itemValue());
            }
            if (override.getValidationConfigurations() == null) {
                override.setValidationConfigurations(new LinkedHashMap<String, Map<String, String>>(5));
            }
            override.getValidationConfigurations().put(configuration.validationImplementation(), itemMap);
        }
    }

    protected void buildBasicMetadata(Class<?> parentClass, Class<?> targetClass, Map<String, FieldMetadata> attributes,
                                      FieldInfo field, FieldMetadataOverride basicFieldMetadata, DynamicEntityDao dynamicEntityDao) {
        BasicFieldMetadata serverMetadata = (BasicFieldMetadata) attributes.get(field.getName());

        BasicFieldMetadata metadata;
        if (serverMetadata != null) {
            metadata = serverMetadata;
        } else {
            metadata = new BasicFieldMetadata();
        }

        metadata.setName(field.getName());
        metadata.setTargetClass(targetClass.getName());
        metadata.setFieldName(field.getName());

        if (basicFieldMetadata.getFieldType() != null) {
            metadata.setFieldType(basicFieldMetadata.getFieldType());
        }
        if (basicFieldMetadata.getFriendlyName() != null) {
            metadata.setFriendlyName(basicFieldMetadata.getFriendlyName());
        }
        if (basicFieldMetadata.getSecurityLevel() != null) {
            metadata.setSecurityLevel(basicFieldMetadata.getSecurityLevel());
        }
        if (basicFieldMetadata.getVisibility() != null) {
            metadata.setVisibility(basicFieldMetadata.getVisibility());
        }
        if (basicFieldMetadata.getOrder() != null) {
            metadata.setOrder(basicFieldMetadata.getOrder());
        }
        if (basicFieldMetadata.getGridOrder() != null) {
            metadata.setGridOrder(basicFieldMetadata.getGridOrder());
        }
        if (basicFieldMetadata.getExplicitFieldType() != null) {
            metadata.setExplicitFieldType(basicFieldMetadata.getExplicitFieldType());
        }
        if (metadata.getExplicitFieldType()==SupportedFieldType.ADDITIONAL_FOREIGN_KEY) {
            //this is a lookup - exclude the fields on this OneToOne or ManyToOne field
            //metadata.setExcluded(true);
            if (basicFieldMetadata.getForcePopulateChildProperties() == null || !basicFieldMetadata.getForcePopulateChildProperties()) {
                metadata.setChildrenExcluded(true);
            }
            //metadata.setVisibility(VisibilityEnum.GRID_HIDDEN);
        } else {
            if (basicFieldMetadata.getExcluded()!=null) {
                if (LOG.isDebugEnabled()) {
                    if (basicFieldMetadata.getExcluded()) {
                        LOG.debug("buildBasicMetadata:Excluding " + field.getName() + " because it was explicitly declared in config");
                    } else {
                        LOG.debug("buildBasicMetadata:Showing " + field.getName() + " because it was explicitly declared in config");
                    }
                }
                metadata.setExcluded(basicFieldMetadata.getExcluded());
            }
        }
        if (basicFieldMetadata.getGroup()!=null) {
            metadata.setGroup(basicFieldMetadata.getGroup());
        }
        if (basicFieldMetadata.getIsBorderlessGroup()!=null) {
            metadata.setIsBorderlessGroup(basicFieldMetadata.getIsBorderlessGroup());
        }
        if (basicFieldMetadata.getGroupOrder()!=null) {
            metadata.setGroupOrder(basicFieldMetadata.getGroupOrder());
        }
        if (basicFieldMetadata.getGroupCollapsed()!=null) {
            metadata.setGroupCollapsed(basicFieldMetadata.getGroupCollapsed());
        }
        if (basicFieldMetadata.getTab() != null) {
            metadata.setTab(basicFieldMetadata.getTab());
        }
        if (basicFieldMetadata.getTabOrder() != null) {
            metadata.setTabOrder(basicFieldMetadata.getTabOrder());
        }
        if (basicFieldMetadata.isLargeEntry()!=null) {
            metadata.setLargeEntry(basicFieldMetadata.isLargeEntry());
        }
        if (basicFieldMetadata.isProminent()!=null) {
            metadata.setProminent(basicFieldMetadata.isProminent());
        }
        if (basicFieldMetadata.getColumnWidth()!=null) {
            metadata.setColumnWidth(basicFieldMetadata.getColumnWidth());
        }
        if (basicFieldMetadata.getBroadleafEnumeration()!=null) {
            metadata.setBroadleafEnumeration(basicFieldMetadata.getBroadleafEnumeration());
        }
        if (!StringUtils.isEmpty(metadata.getBroadleafEnumeration()) && metadata.getFieldType()==SupportedFieldType.BROADLEAF_ENUMERATION) {
            try {
                setupBroadleafEnumeration(metadata.getBroadleafEnumeration(), metadata, dynamicEntityDao);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
        if (basicFieldMetadata.getReadOnly()!=null) {
            metadata.setReadOnly(basicFieldMetadata.getReadOnly());
        }
        if (basicFieldMetadata.getTooltip()!=null) {
            metadata.setTooltip(basicFieldMetadata.getTooltip());
        }
        if (basicFieldMetadata.getHelpText()!=null) {
            metadata.setHelpText(basicFieldMetadata.getHelpText());
        }
        if (basicFieldMetadata.getHint()!=null) {
            metadata.setHint(basicFieldMetadata.getHint());
        }
        if (basicFieldMetadata.getShowIfProperty()!=null) {
            metadata.setShowIfProperty(basicFieldMetadata.getShowIfProperty());
        }
        if (basicFieldMetadata.getCurrencyCodeField()!=null) {
            metadata.setCurrencyCodeField(basicFieldMetadata.getCurrencyCodeField());
        }
        if (basicFieldMetadata.getLookupDisplayProperty()!=null) {
            metadata.setLookupDisplayProperty(basicFieldMetadata.getLookupDisplayProperty());
            metadata.setForeignKeyDisplayValueProperty(basicFieldMetadata.getLookupDisplayProperty());
        }
        if (basicFieldMetadata.getForcePopulateChildProperties()!=null) {
            metadata.setForcePopulateChildProperties(basicFieldMetadata.getForcePopulateChildProperties());
        }
        if (basicFieldMetadata.getEnableTypeaheadLookup()!=null) {
            metadata.setEnableTypeaheadLookup(basicFieldMetadata.getEnableTypeaheadLookup());
        }
        if (basicFieldMetadata.getCustomCriteria() != null) {
            metadata.setCustomCriteria(basicFieldMetadata.getCustomCriteria());
        }
        if (basicFieldMetadata.getUseServerSideInspectionCache() != null) {
            metadata.setUseServerSideInspectionCache(basicFieldMetadata.getUseServerSideInspectionCache());
        }
        if (basicFieldMetadata.getToOneLookupCreatedViaAnnotation()!=null) {
            metadata.setToOneLookupCreatedViaAnnotation(basicFieldMetadata.getToOneLookupCreatedViaAnnotation());
        }
        if (basicFieldMetadata.getOptionListEntity()!=null) {
            metadata.setOptionListEntity(basicFieldMetadata.getOptionListEntity());
        }
        if (metadata.getOptionListEntity() != null && metadata.getOptionListEntity().equals(DataDrivenEnumerationValueImpl.class.getName())) {
            metadata.setOptionValueFieldName("key");
            metadata.setOptionDisplayFieldName("display");
        } else {
            if (basicFieldMetadata.getOptionValueFieldName()!=null) {
                metadata.setOptionValueFieldName(basicFieldMetadata.getOptionValueFieldName());
            }
            if (basicFieldMetadata.getOptionDisplayFieldName()!=null) {
                metadata.setOptionDisplayFieldName(basicFieldMetadata.getOptionDisplayFieldName());
            }
        }
        if (!StringUtils.isEmpty(metadata.getOptionListEntity()) && (StringUtils.isEmpty(metadata.getOptionValueFieldName()) || StringUtils.isEmpty(metadata.getOptionDisplayFieldName()))) {
            throw new IllegalArgumentException("Problem setting up data driven enumeration for ("+field.getName()+"). The optionListEntity, optionValueFieldName and optionDisplayFieldName properties must all be included if not using DataDrivenEnumerationValueImpl as the optionListEntity.");
        }
        if (basicFieldMetadata.getOptionFilterValues() != null) {
            String[][] options = new String[basicFieldMetadata.getOptionFilterValues().length][3];
            int j = 0;
            for (Serializable[] option : basicFieldMetadata.getOptionFilterValues()) {
                options[j][0] = String.valueOf(option[0]);
                options[j][1] = String.valueOf(option[1]);
                options[j][2] = String.valueOf(option[2]);
            }
            metadata.setOptionFilterParams(options);
        }
        if (!StringUtils.isEmpty(metadata.getOptionListEntity())) {
            buildDataDrivenList(metadata, dynamicEntityDao);
        }
        if (basicFieldMetadata.getRequiredOverride()!=null) {
            metadata.setRequiredOverride(basicFieldMetadata.getRequiredOverride());
        }
        if (basicFieldMetadata.getValidationConfigurations()!=null) {
            metadata.setValidationConfigurations(basicFieldMetadata.getValidationConfigurations());
        }
        if ((basicFieldMetadata.getFieldType() == SupportedFieldType.RULE_SIMPLE ||
                basicFieldMetadata.getFieldType() == SupportedFieldType.RULE_WITH_QUANTITY)
                && basicFieldMetadata.getRuleIdentifier() == null) {
            throw new IllegalArgumentException("ruleIdentifier property must be set on AdminPresentation when the fieldType is RULE_SIMPLE or RULE_WITH_QUANTITY");
        }
        if (basicFieldMetadata.getRuleIdentifier()!=null) {
            metadata.setRuleIdentifier(basicFieldMetadata.getRuleIdentifier());
        }
        if (basicFieldMetadata.getLookupType()!=null) {
            metadata.setLookupType(basicFieldMetadata.getLookupType());
        }
        if (basicFieldMetadata.getTranslatable() != null) {
            metadata.setTranslatable(basicFieldMetadata.getTranslatable());
        }
        if (basicFieldMetadata.getIsDerived() != null) {
            metadata.setDerived(basicFieldMetadata.getIsDerived());
        }
        if (basicFieldMetadata.getDefaultValue() != null) {
            metadata.setDefaultValue(basicFieldMetadata.getDefaultValue());
        }

        attributes.put(field.getName(), metadata);
    }

    protected void buildDataDrivenList(BasicFieldMetadata metadata, DynamicEntityDao dynamicEntityDao) {
        try {
            Criteria criteria = dynamicEntityDao.createCriteria(Class.forName(metadata.getOptionListEntity()));
            if (metadata.getOptionListEntity().equals(DataDrivenEnumerationValueImpl.class.getName())) {
                criteria.add(Restrictions.eq("hidden", false));
            }
            if (metadata.getOptionFilterParams() != null) {
                for (String[] param : metadata.getOptionFilterParams()) {
                    Criteria current = criteria;
                    String key = param[0];
                    if (!key.equals(".ignore")) {
                        if (key.contains(".")) {
                            String[] parts = key.split("\\.");
                            for (int j = 0; j < parts.length - 1; j++) {
                                current = current.createCriteria(parts[j], parts[j]);
                            }
                        }
                        current.add(Restrictions.eq(key, convertType(param[1], OptionFilterParamType.valueOf(param[2]))));
                    }
                }
            }
            List results = criteria.list();
            String[][] enumerationValues = new String[results.size()][2];
            int j = 0;
            for (Object param : results) {
                enumerationValues[j][1] = String.valueOf(dynamicEntityDao.getFieldManager().getFieldValue(param, metadata.getOptionDisplayFieldName()));
                enumerationValues[j][0] = String.valueOf(dynamicEntityDao.getFieldManager().getFieldValue(param, metadata.getOptionValueFieldName()));
                j++;
            }
            if (!CollectionUtils.isEmpty(results) && metadata.getOptionListEntity().equals(DataDrivenEnumerationValueImpl.class.getName())) {
                metadata.setOptionCanEditValues((Boolean) dynamicEntityDao.getFieldManager().getFieldValue(results.get(0), "type.modifiable"));
            }
            metadata.setEnumerationValues(enumerationValues);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public int getOrder() {
        return FieldMetadataProvider.BASIC;
    }
}


File: admin/broadleaf-open-admin-platform/src/main/java/org/broadleafcommerce/openadmin/server/dao/provider/metadata/CollectionFieldMetadataProvider.java
/*
 * #%L
 * BroadleafCommerce Open Admin Platform
 * %%
 * Copyright (C) 2009 - 2013 Broadleaf Commerce
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */
package org.broadleafcommerce.openadmin.server.dao.provider.metadata;

import org.apache.commons.lang.ArrayUtils;
import org.apache.commons.lang.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.broadleafcommerce.common.presentation.AdminPresentationCollection;
import org.broadleafcommerce.common.presentation.AdminPresentationOperationTypes;
import org.broadleafcommerce.common.presentation.client.AddMethodType;
import org.broadleafcommerce.common.presentation.client.ForeignKeyRestrictionType;
import org.broadleafcommerce.common.presentation.client.OperationType;
import org.broadleafcommerce.common.presentation.client.PersistencePerspectiveItemType;
import org.broadleafcommerce.common.presentation.override.AdminPresentationCollectionOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeEntry;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeOverrides;
import org.broadleafcommerce.common.presentation.override.AdminPresentationOverrides;
import org.broadleafcommerce.common.presentation.override.PropertyType;
import org.broadleafcommerce.openadmin.dto.BasicCollectionMetadata;
import org.broadleafcommerce.openadmin.dto.FieldMetadata;
import org.broadleafcommerce.openadmin.dto.ForeignKey;
import org.broadleafcommerce.openadmin.dto.PersistencePerspective;
import org.broadleafcommerce.openadmin.dto.override.FieldMetadataOverride;
import org.broadleafcommerce.openadmin.server.dao.DynamicEntityDao;
import org.broadleafcommerce.openadmin.server.dao.FieldInfo;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaAnnotationRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaXmlRequest;
import org.broadleafcommerce.openadmin.server.service.type.MetadataProviderResponse;
import org.springframework.beans.factory.NoSuchBeanDefinitionException;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Component;

import java.lang.reflect.Field;
import java.lang.reflect.ParameterizedType;
import java.util.HashMap;
import java.util.Map;

/**
 * @author Jeff Fischer
 */
@Component("blCollectionFieldMetadataProvider")
@Scope("prototype")
public class CollectionFieldMetadataProvider extends AdvancedCollectionFieldMetadataProvider {

    private static final Log LOG = LogFactory.getLog(CollectionFieldMetadataProvider.class);

    protected boolean canHandleFieldForConfiguredMetadata(AddMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentationCollection annot = addMetadataRequest.getRequestedField().getAnnotation(AdminPresentationCollection.class);
        return annot != null;
    }

    protected boolean canHandleAnnotationOverride(OverrideViaAnnotationRequest overrideViaAnnotationRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentationOverrides myOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationOverrides.class);
        AdminPresentationMergeOverrides myMergeOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationMergeOverrides.class);
        return (myOverrides != null && !ArrayUtils.isEmpty(myOverrides.collections()) || myMergeOverrides != null);
    }

    @Override
    public MetadataProviderResponse addMetadata(AddFieldMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleFieldForConfiguredMetadata(addMetadataRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        AdminPresentationCollection annot = addMetadataRequest.getRequestedField().getAnnotation(AdminPresentationCollection
                .class);
        FieldInfo info = buildFieldInfo(addMetadataRequest.getRequestedField());
        FieldMetadataOverride override = constructBasicCollectionMetadataOverride(annot);
        buildCollectionMetadata(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(),
                metadata, info, override, addMetadataRequest.getPrefix());
        setClassOwnership(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(), metadata, info);
        return MetadataProviderResponse.HANDLED;
    }

    @Override
    public MetadataProviderResponse overrideViaAnnotation(OverrideViaAnnotationRequest overrideViaAnnotationRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleAnnotationOverride(overrideViaAnnotationRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        Map<String, AdminPresentationCollectionOverride> presentationCollectionOverrides = new HashMap<String, AdminPresentationCollectionOverride>();

        AdminPresentationOverrides myOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationOverrides.class);
        if (myOverrides != null) {
            for (AdminPresentationCollectionOverride myOverride : myOverrides.collections()) {
                presentationCollectionOverrides.put(myOverride.name(), myOverride);
            }
        }

        for (String propertyName : presentationCollectionOverrides.keySet()) {
            for (String key : metadata.keySet()) {
                if (key.startsWith(propertyName)) {
                    buildAdminPresentationCollectionOverride(overrideViaAnnotationRequest.getPrefix(), overrideViaAnnotationRequest.getParentExcluded(), metadata, presentationCollectionOverrides, propertyName, key, overrideViaAnnotationRequest.getDynamicEntityDao());
                }
            }
        }

        AdminPresentationMergeOverrides myMergeOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationMergeOverrides.class);
        if (myMergeOverrides != null) {
            for (AdminPresentationMergeOverride override : myMergeOverrides.value()) {
                String propertyName = override.name();
                Map<String, FieldMetadata> loopMap = new HashMap<String, FieldMetadata>();
                loopMap.putAll(metadata);
                for (Map.Entry<String, FieldMetadata> entry : loopMap.entrySet()) {
                    if (entry.getKey().startsWith(propertyName) || StringUtils.isEmpty(propertyName)) {
                        FieldMetadata targetMetadata = entry.getValue();
                        if (targetMetadata instanceof BasicCollectionMetadata) {
                            BasicCollectionMetadata serverMetadata = (BasicCollectionMetadata) targetMetadata;
                            if (serverMetadata.getTargetClass() != null) {
                                try {
                                    Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                                    Class<?> parentClass = null;
                                    if (serverMetadata.getOwningClass() != null) {
                                        parentClass = Class.forName(serverMetadata.getOwningClass());
                                    }
                                    String fieldName = serverMetadata.getFieldName();
                                    Field field = overrideViaAnnotationRequest.getDynamicEntityDao().getFieldManager()
                                                .getField(targetClass, fieldName);
                                    Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                                    temp.put(field.getName(), serverMetadata);
                                    FieldInfo info = buildFieldInfo(field);
                                    FieldMetadataOverride fieldMetadataOverride = overrideCollectionMergeMetadata(override);
                                    if (serverMetadata.getExcluded() != null && serverMetadata.getExcluded() &&
                                            (fieldMetadataOverride.getExcluded() == null || fieldMetadataOverride.getExcluded())) {
                                        continue;
                                    }
                                    buildCollectionMetadata(parentClass, targetClass, temp, info, fieldMetadataOverride, overrideViaAnnotationRequest.getPrefix());
                                    serverMetadata = (BasicCollectionMetadata) temp.get(field.getName());
                                    metadata.put(entry.getKey(), serverMetadata);
                                } catch (Exception e) {
                                    throw new RuntimeException(e);
                                }
                            }
                        }
                    }
                }
            }
        }

        return MetadataProviderResponse.HANDLED;
    }

    @Override
        Map<String, FieldMetadataOverride> overrides = getTargetedOverride(overrideViaXmlRequest.getDynamicEntityDao(), overrideViaXmlRequest.getRequestedConfigKey(), overrideViaXmlRequest.getRequestedCeilingEntity());
    public MetadataProviderResponse overrideViaXml(OverrideViaXmlRequest overrideViaXmlRequest, Map<String, FieldMetadata> metadata) {
        if (overrides != null) {
            for (String propertyName : overrides.keySet()) {
                final FieldMetadataOverride localMetadata = overrides.get(propertyName);
                for (String key : metadata.keySet()) {
                    if (key.equals(propertyName)) {
                        try {
                            if (metadata.get(key) instanceof BasicCollectionMetadata) {
                                BasicCollectionMetadata serverMetadata = (BasicCollectionMetadata) metadata.get(key);
                                if (serverMetadata.getTargetClass() != null)  {
                                    Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                                    Class<?> parentClass = null;
                                    if (serverMetadata.getOwningClass() != null) {
                                        parentClass = Class.forName(serverMetadata.getOwningClass());
                                    }
                                    String fieldName = serverMetadata.getFieldName();
                                    Field field = overrideViaXmlRequest.getDynamicEntityDao().getFieldManager().getField(targetClass, fieldName);
                                    Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                                    temp.put(field.getName(), serverMetadata);
                                    FieldInfo info = buildFieldInfo(field);
                                    buildCollectionMetadata(parentClass, targetClass, temp, info, localMetadata, overrideViaXmlRequest.getPrefix());
                                    serverMetadata = (BasicCollectionMetadata) temp.get(field.getName());
                                    metadata.put(key, serverMetadata);
                                    if (overrideViaXmlRequest.getParentExcluded()) {
                                        if (LOG.isDebugEnabled()) {
                                            LOG.debug("applyCollectionMetadataOverrides:Excluding " + key + "because parent is marked as excluded.");
                                        }
                                        serverMetadata.setExcluded(true);
                                    }
                                }
                            }
                        } catch (Exception e) {
                            throw new RuntimeException(e);
                        }
                    }
                }
            }
        }
        return MetadataProviderResponse.HANDLED;
    }

    protected void buildAdminPresentationCollectionOverride(String prefix, Boolean isParentExcluded, Map<String, FieldMetadata> mergedProperties, Map<String, AdminPresentationCollectionOverride> presentationCollectionOverrides, String propertyName, String key, DynamicEntityDao dynamicEntityDao) {
        AdminPresentationCollectionOverride override = presentationCollectionOverrides.get(propertyName);
        if (override != null) {
            AdminPresentationCollection annot = override.value();
            if (annot != null) {
                String testKey = prefix + key;
                if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && annot.excluded()) {
                    FieldMetadata metadata = mergedProperties.get(key);
                    if (LOG.isDebugEnabled()) {
                        LOG.debug("buildAdminPresentationCollectionOverride:Excluding " + key + "because an override annotation declared " + testKey + "to be excluded");
                    }
                    metadata.setExcluded(true);
                    return;
                }
                if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && !annot.excluded()) {
                    FieldMetadata metadata = mergedProperties.get(key);
                    if (!isParentExcluded) {
                        if (LOG.isDebugEnabled()) {
                            LOG.debug("buildAdminPresentationCollectionOverride:Showing " + key + "because an override annotation declared " + testKey + " to not be excluded");
                        }
                        metadata.setExcluded(false);
                    }
                }
                if (!(mergedProperties.get(key) instanceof BasicCollectionMetadata)) {
                    return;
                }
                BasicCollectionMetadata serverMetadata = (BasicCollectionMetadata) mergedProperties.get(key);
                if (serverMetadata.getTargetClass() != null) {
                    try {
                        Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                        Class<?> parentClass = null;
                        if (serverMetadata.getOwningClass() != null) {
                            parentClass = Class.forName(serverMetadata.getOwningClass());
                        }
                        String fieldName = serverMetadata.getFieldName();
                        Field field = dynamicEntityDao.getFieldManager().getField(targetClass, fieldName);
                        FieldMetadataOverride localMetadata = constructBasicCollectionMetadataOverride(annot);
                        //do not include the previous metadata - we want to construct a fresh metadata from the override annotation
                        Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                        FieldInfo info = buildFieldInfo(field);
                        buildCollectionMetadata(parentClass, targetClass, temp, info, localMetadata, prefix);
                        BasicCollectionMetadata result = (BasicCollectionMetadata) temp.get(field.getName());
                        result.setInheritedFromType(serverMetadata.getInheritedFromType());
                        result.setAvailableToTypes(serverMetadata.getAvailableToTypes());
                        mergedProperties.put(key, result);
                        if (isParentExcluded) {
                            if (LOG.isDebugEnabled()) {
                                LOG.debug("buildAdminPresentationCollectionOverride:Excluding " + key + "because the parent was excluded");
                            }
                            serverMetadata.setExcluded(true);
                        }
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                }
            }
        }
    }

    protected FieldMetadataOverride overrideCollectionMergeMetadata(AdminPresentationMergeOverride merge) {
        FieldMetadataOverride fieldMetadataOverride = new FieldMetadataOverride();
        Map<String, AdminPresentationMergeEntry> overrideValues = getAdminPresentationEntries(merge.mergeEntries());
        for (Map.Entry<String, AdminPresentationMergeEntry> entry : overrideValues.entrySet()) {
            String stringValue = entry.getValue().overrideValue();
            if (entry.getKey().equals(PropertyType.AdminPresentationCollection.ADDTYPE)) {
                fieldMetadataOverride.setAddType(OperationType.valueOf(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.CURRENCYCODEFIELD)) {
                fieldMetadataOverride.setCurrencyCodeField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.CUSTOMCRITERIA)) {
                fieldMetadataOverride.setCustomCriteria(entry.getValue().stringArrayOverrideValue());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.EXCLUDED)) {
                fieldMetadataOverride.setExcluded(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .booleanOverrideValue() :
                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.FRIENDLYNAME)) {
                fieldMetadataOverride.setFriendlyName(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.MANYTOFIELD)) {
                fieldMetadataOverride.setManyToField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.OPERATIONTYPES)) {
                AdminPresentationOperationTypes operationType = entry.getValue().operationTypes();
                fieldMetadataOverride.setAddType(operationType.addType());
                fieldMetadataOverride.setRemoveType(operationType.removeType());
                fieldMetadataOverride.setUpdateType(operationType.updateType());
                fieldMetadataOverride.setFetchType(operationType.fetchType());
                fieldMetadataOverride.setInspectType(operationType.inspectType());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.ORDER)) {
                fieldMetadataOverride.setOrder(StringUtils.isEmpty(stringValue) ? entry.getValue().intOverrideValue() :
                        Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.MANYTOFIELD)) {
                fieldMetadataOverride.setManyToField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.READONLY)) {
                fieldMetadataOverride.setReadOnly(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .booleanOverrideValue() :
                        Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.SECURITYLEVEL)) {
                fieldMetadataOverride.setSecurityLevel(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.SHOWIFPROPERTY)) {
                fieldMetadataOverride.setShowIfProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.SORTASCENDING)) {
                fieldMetadataOverride.setSortAscending(StringUtils.isEmpty(stringValue) ? entry.getValue()
                            .booleanOverrideValue() :
                            Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.SORTPROPERTY)) {
                fieldMetadataOverride.setSortProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.TAB)) {
                fieldMetadataOverride.setTab(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.TABORDER)) {
                fieldMetadataOverride.setTabOrder(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .intOverrideValue() :
                        Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationCollection.USESERVERSIDEINSPECTIONCACHE)) {
                fieldMetadataOverride.setUseServerSideInspectionCache(StringUtils.isEmpty(stringValue) ? entry
                        .getValue().booleanOverrideValue() :
                        Boolean.parseBoolean(stringValue));
            } else {
                if (LOG.isDebugEnabled()) {
                    LOG.debug("Unrecognized type: " + entry.getKey() + ". Not setting on collection field.");
                }
            }
        }

        return fieldMetadataOverride;
    }

    protected FieldMetadataOverride constructBasicCollectionMetadataOverride(AdminPresentationCollection annotColl) {
        if (annotColl != null) {
            FieldMetadataOverride override = new FieldMetadataOverride();
            override.setAddMethodType(annotColl.addType());
            override.setManyToField(annotColl.manyToField());
            override.setCustomCriteria(annotColl.customCriteria());
            override.setUseServerSideInspectionCache(annotColl.useServerSideInspectionCache());
            override.setExcluded(annotColl.excluded());
            override.setFriendlyName(annotColl.friendlyName());
            override.setReadOnly(annotColl.readOnly());
            override.setSortProperty(annotColl.sortProperty());
            override.setSortAscending(annotColl.sortAscending());
            override.setOrder(annotColl.order());
            override.setTab(annotColl.tab());
            override.setTabOrder(annotColl.tabOrder());
            override.setSecurityLevel(annotColl.securityLevel());
            override.setAddType(annotColl.operationTypes().addType());
            override.setFetchType(annotColl.operationTypes().fetchType());
            override.setRemoveType(annotColl.operationTypes().removeType());
            override.setUpdateType(annotColl.operationTypes().updateType());
            override.setInspectType(annotColl.operationTypes().inspectType());
            override.setShowIfProperty(annotColl.showIfProperty());
            override.setCurrencyCodeField(annotColl.currencyCodeField());
            return override;
        }
        throw new IllegalArgumentException("AdminPresentationCollection annotation not found on Field");
    }

    protected void buildCollectionMetadata(Class<?> parentClass, 
            Class<?> targetClass,
            Map<String, FieldMetadata> attributes,
            FieldInfo field,
            FieldMetadataOverride collectionMetadata,
            String prefix) {
        BasicCollectionMetadata serverMetadata = (BasicCollectionMetadata) attributes.get(field.getName());

        Class<?> resolvedClass = parentClass==null?targetClass:parentClass;
        BasicCollectionMetadata metadata;
        if (serverMetadata != null) {
            metadata = serverMetadata;
        } else {
            metadata = new BasicCollectionMetadata();
        }
        metadata.setTargetClass(targetClass.getName());
        metadata.setFieldName(field.getName());
        if (collectionMetadata.getReadOnly() != null) {
            metadata.setMutable(!collectionMetadata.getReadOnly());
        }
        if (collectionMetadata.getAddMethodType() != null) {
            metadata.setAddMethodType(collectionMetadata.getAddMethodType());
        }
        if (collectionMetadata.getShowIfProperty()!=null) {
            metadata.setShowIfProperty(collectionMetadata.getShowIfProperty());
        }

        org.broadleafcommerce.openadmin.dto.OperationTypes dtoOperationTypes = new org.broadleafcommerce.openadmin.dto.OperationTypes(OperationType.BASIC, OperationType.BASIC, OperationType.BASIC, OperationType.BASIC, OperationType.BASIC);
        if (collectionMetadata.getAddType() != null) {
            dtoOperationTypes.setAddType(collectionMetadata.getAddType());
        }
        if (collectionMetadata.getRemoveType() != null) {
            dtoOperationTypes.setRemoveType(collectionMetadata.getRemoveType());
        }
        if (collectionMetadata.getFetchType() != null) {
            dtoOperationTypes.setFetchType(collectionMetadata.getFetchType());
        }
        if (collectionMetadata.getInspectType() != null) {
            dtoOperationTypes.setInspectType(collectionMetadata.getInspectType());
        }
        if (collectionMetadata.getUpdateType() != null) {
            dtoOperationTypes.setUpdateType(collectionMetadata.getUpdateType());
        }

        if (AddMethodType.LOOKUP == metadata.getAddMethodType()
                || AddMethodType.SELECTIZE_LOOKUP == metadata.getAddMethodType()) {
            dtoOperationTypes.setRemoveType(OperationType.NONDESTRUCTIVEREMOVE);
        }

        //don't allow additional non-persistent properties or additional foreign keys for an advanced collection datasource - they don't make sense in this context
        PersistencePerspective persistencePerspective;
        if (serverMetadata != null) {
            persistencePerspective = metadata.getPersistencePerspective();
            persistencePerspective.setOperationTypes(dtoOperationTypes);
        } else {
            persistencePerspective = new PersistencePerspective(dtoOperationTypes, new String[]{}, new ForeignKey[]{});
            metadata.setPersistencePerspective(persistencePerspective);
        }

        String foreignKeyName = null;
        if (serverMetadata != null) {
            foreignKeyName = ((ForeignKey) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems
                    ().get(PersistencePerspectiveItemType.FOREIGNKEY)).getManyToField();
        }
        if (!StringUtils.isEmpty(collectionMetadata.getManyToField())) {
            foreignKeyName = collectionMetadata.getManyToField();
        }
        if (foreignKeyName == null && !StringUtils.isEmpty(field.getOneToManyMappedBy())) {
            foreignKeyName = field.getOneToManyMappedBy();
        }
        if (foreignKeyName == null && !StringUtils.isEmpty(field.getManyToManyMappedBy())) {
            foreignKeyName = field.getManyToManyMappedBy();
        }
        if (StringUtils.isEmpty(foreignKeyName)) {
            throw new IllegalArgumentException("Unable to infer a ManyToOne field name for the @AdminPresentationCollection annotated field("+field.getName()+"). If not using the mappedBy property of @OneToMany or @ManyToMany, please make sure to explicitly define the manyToField property");
        }

        String sortProperty = null;
        if (serverMetadata != null) {
            sortProperty = ((ForeignKey) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.FOREIGNKEY)).getSortField();
        }
        if (!StringUtils.isEmpty(collectionMetadata.getSortProperty())) {
            sortProperty = collectionMetadata.getSortProperty();
        }

        Boolean isAscending = true;
        if (serverMetadata != null) {
            isAscending = ((ForeignKey) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.FOREIGNKEY)).getSortAscending();
        }
        if (collectionMetadata.isSortAscending()!=null) {
            isAscending = collectionMetadata.isSortAscending();
        }

        if (serverMetadata != null) {
            ForeignKey foreignKey = (ForeignKey) metadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.FOREIGNKEY);
            foreignKey.setManyToField(foreignKeyName);
            foreignKey.setForeignKeyClass(resolvedClass.getName());
            foreignKey.setMutable(metadata.isMutable());
            foreignKey.setOriginatingField(prefix + field.getName());
            foreignKey.setSortField(sortProperty);
            foreignKey.setSortAscending(isAscending);
        } else {
            ForeignKey foreignKey = new ForeignKey(foreignKeyName, resolvedClass.getName(), null, ForeignKeyRestrictionType.ID_EQ);
            foreignKey.setMutable(metadata.isMutable());
            foreignKey.setOriginatingField(prefix + field.getName());
            foreignKey.setSortField(sortProperty);
            foreignKey.setSortAscending(isAscending);
            persistencePerspective.addPersistencePerspectiveItem(PersistencePerspectiveItemType.FOREIGNKEY, foreignKey);
        }

        String ceiling = null;
        checkCeiling: {
            if (field.getGenericType() instanceof ParameterizedType) {
                try {
                    ParameterizedType pt = (ParameterizedType) field.getGenericType();
                    java.lang.reflect.Type collectionType = pt.getActualTypeArguments()[0];
                    String ceilingEntityName = ((Class<?>) collectionType).getName();
                    ceiling = entityConfiguration.lookupEntityClass(ceilingEntityName).getName();
                    break checkCeiling;
                } catch (NoSuchBeanDefinitionException e) {
                    // We weren't successful at looking at entity configuration to find the type of this collection.
                    // We will continue and attempt to find it via the Hibernate annotations
                }
            }
            if (!StringUtils.isEmpty(field.getOneToManyTargetEntity()) && !void.class.getName().equals(field.getOneToManyTargetEntity())) {
                ceiling = field.getOneToManyTargetEntity();
                break checkCeiling;
            }
            if (!StringUtils.isEmpty(field.getManyToManyTargetEntity()) && !void.class.getName().equals(field.getManyToManyTargetEntity())) {
                ceiling = field.getManyToManyTargetEntity();
                break checkCeiling;
            }
        }
        if (!StringUtils.isEmpty(ceiling)) {
            metadata.setCollectionCeilingEntity(ceiling);
        }

        if (collectionMetadata.getExcluded() != null) {
            if (LOG.isDebugEnabled()) {
                if (collectionMetadata.getExcluded()) {
                    LOG.debug("buildCollectionMetadata:Excluding " + field.getName() + " because it was explicitly declared in config");
                } else {
                    LOG.debug("buildCollectionMetadata:Showing " + field.getName() + " because it was explicitly declared in config");
                }
            }
            metadata.setExcluded(collectionMetadata.getExcluded());
        }
        if (collectionMetadata.getFriendlyName() != null) {
            metadata.setFriendlyName(collectionMetadata.getFriendlyName());
        }
        if (collectionMetadata.getSecurityLevel() != null) {
            metadata.setSecurityLevel(collectionMetadata.getSecurityLevel());
        }
        if (collectionMetadata.getOrder() != null) {
            metadata.setOrder(collectionMetadata.getOrder());
        }

        if (collectionMetadata.getTab() != null) {
            metadata.setTab(collectionMetadata.getTab());
        }
        if (collectionMetadata.getTabOrder() != null) {
            metadata.setTabOrder(collectionMetadata.getTabOrder());
        }

        if (collectionMetadata.getSortProperty() != null) {
            metadata.setSortProperty(collectionMetadata.getSortProperty());
        }

        if (collectionMetadata.getCustomCriteria() != null) {
            metadata.setCustomCriteria(collectionMetadata.getCustomCriteria());
        }

        if (collectionMetadata.getUseServerSideInspectionCache() != null) {
            persistencePerspective.setUseServerSideInspectionCache(collectionMetadata.getUseServerSideInspectionCache());
        }

        if (collectionMetadata.getCurrencyCodeField()!=null) {
            metadata.setCurrencyCodeField(collectionMetadata.getCurrencyCodeField());
        }

        attributes.put(field.getName(), metadata);
    }

    @Override
    public int getOrder() {
        return FieldMetadataProvider.COLLECTION;
    }
}


File: admin/broadleaf-open-admin-platform/src/main/java/org/broadleafcommerce/openadmin/server/dao/provider/metadata/DefaultFieldMetadataProvider.java
/*
 * #%L
 * BroadleafCommerce Open Admin Platform
 * %%
 * Copyright (C) 2009 - 2013 Broadleaf Commerce
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */
package org.broadleafcommerce.openadmin.server.dao.provider.metadata;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Map;

import org.apache.commons.collections.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.broadleafcommerce.common.admin.domain.AdminMainEntity;
import org.broadleafcommerce.common.money.Money;
import org.broadleafcommerce.common.presentation.client.SupportedFieldType;
import org.broadleafcommerce.openadmin.dto.BasicFieldMetadata;
import org.broadleafcommerce.openadmin.dto.FieldMetadata;
import org.broadleafcommerce.openadmin.dto.override.FieldMetadataOverride;
import org.broadleafcommerce.openadmin.server.dao.FieldInfo;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataFromFieldTypeRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataFromMappingDataRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaXmlRequest;
import org.broadleafcommerce.openadmin.server.service.type.MetadataProviderResponse;
import org.hibernate.mapping.Column;
import org.hibernate.mapping.Property;
import org.hibernate.metadata.ClassMetadata;
import org.hibernate.type.Type;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Component;

/**
 * @author Jeff Fischer
 */
@Component("blDefaultFieldMetadataProvider")
@Scope("prototype")
public class DefaultFieldMetadataProvider extends BasicFieldMetadataProvider {

    private static final Log LOG = LogFactory.getLog(DefaultFieldMetadataProvider.class);

    @Override
    public MetadataProviderResponse addMetadata(AddFieldMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        Map<String, Object> idMetadata = addMetadataRequest.getDynamicEntityDao().getIdMetadata(addMetadataRequest.getTargetClass());
        if (idMetadata != null) {
            String idField = (String) idMetadata.get("name");
            boolean processField;
            //allow id fields without AdminPresentation annotation to pass through
            processField = idField.equals(addMetadataRequest.getRequestedField().getName());
            if (!processField) {
                List<String> propertyNames = addMetadataRequest.getDynamicEntityDao().getPropertyNames(
                        addMetadataRequest.getTargetClass());
                if (!CollectionUtils.isEmpty(propertyNames)) {
                    List<org.hibernate.type.Type> propertyTypes = addMetadataRequest.getDynamicEntityDao().getPropertyTypes(
                            addMetadataRequest.getTargetClass());
                    int index = propertyNames.indexOf(addMetadataRequest.getRequestedField().getName());
                    if (index >= 0) {
                        Type myType = propertyTypes.get(index);
                        //allow OneToOne, ManyToOne and Embeddable fields to pass through
                        processField =  myType.isCollectionType() || myType.isAssociationType() ||
                                myType.isComponentType() || myType.isEntityType();
                    }
                }
            }
            if (processField) {
                FieldInfo info = buildFieldInfo(addMetadataRequest.getRequestedField());
                BasicFieldMetadata basicMetadata = new BasicFieldMetadata();
                basicMetadata.setName(addMetadataRequest.getRequestedField().getName());
                basicMetadata.setExcluded(false);
                metadata.put(addMetadataRequest.getRequestedField().getName(), basicMetadata);
                setClassOwnership(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(), metadata, info);
                return MetadataProviderResponse.HANDLED;
            }
        }
        return MetadataProviderResponse.NOT_HANDLED;
    }

    public void overrideExclusionsFromXml(OverrideViaXmlRequest overrideViaXmlRequest, Map<String, FieldMetadata> metadata) {
        //override any and all exclusions derived from xml
        Map<String, FieldMetadataOverride> overrides = getTargetedOverride(overrideViaXmlRequest.getDynamicEntityDao(), overrideViaXmlRequest.getRequestedConfigKey(),
                overrideViaXmlRequest.getRequestedCeilingEntity());
        if (overrides != null) {
            for (String propertyName : overrides.keySet()) {
                final FieldMetadataOverride localMetadata = overrides.get(propertyName);
                Boolean excluded = localMetadata.getExcluded();
                for (String key : metadata.keySet()) {
                    String testKey = overrideViaXmlRequest.getPrefix() + key;
                    if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && excluded != null &&
                            excluded) {
                        FieldMetadata fieldMetadata = metadata.get(key);
                        if (LOG.isDebugEnabled()) {
                            LOG.debug("setExclusionsBasedOnParents:Excluding " + key +
                                    "because an override annotation declared "+ testKey + " to be excluded");
                        }
                        fieldMetadata.setExcluded(true);
                        continue;
                    }
                    if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && excluded != null &&
                            !excluded) {
                        FieldMetadata fieldMetadata = metadata.get(key);
                        if (!overrideViaXmlRequest.getParentExcluded()) {
                            if (LOG.isDebugEnabled()) {
                                LOG.debug("setExclusionsBasedOnParents:Showing " + key +
                                        "because an override annotation declared " + testKey + " to not be excluded");
                            }
                            fieldMetadata.setExcluded(false);
                        }
                    }
                }
            }
        }
    }

    @Override
    public MetadataProviderResponse addMetadataFromMappingData(AddMetadataFromMappingDataRequest addMetadataFromMappingDataRequest,
                                                            FieldMetadata metadata) {
        BasicFieldMetadata fieldMetadata = (BasicFieldMetadata) metadata;
        fieldMetadata.setFieldType(addMetadataFromMappingDataRequest.getType());
        fieldMetadata.setSecondaryType(addMetadataFromMappingDataRequest.getSecondaryType());
        if (addMetadataFromMappingDataRequest.getRequestedEntityType() != null &&
                !addMetadataFromMappingDataRequest.getRequestedEntityType().isCollectionType()) {
            Column column = null;
            for (Property property : addMetadataFromMappingDataRequest.getComponentProperties()) {
                if (property.getName().equals(addMetadataFromMappingDataRequest.getPropertyName())) {
                    Object columnObject = property.getColumnIterator().next();
                    if (columnObject instanceof Column) {
                        column = (Column) columnObject;
                    }
                    break;
                }
            }
            if (column != null) {
                fieldMetadata.setLength(column.getLength());
                fieldMetadata.setScale(column.getScale());
                fieldMetadata.setPrecision(column.getPrecision());
                fieldMetadata.setRequired(!column.isNullable());
                fieldMetadata.setUnique(column.isUnique());
            }
            fieldMetadata.setForeignKeyCollection(false);
        } else {
            fieldMetadata.setForeignKeyCollection(true);
        }
        fieldMetadata.setMutable(true);
        fieldMetadata.setMergedPropertyType(addMetadataFromMappingDataRequest.getMergedPropertyType());
        if (SupportedFieldType.BROADLEAF_ENUMERATION.equals(addMetadataFromMappingDataRequest.getType())) {
            try {
                setupBroadleafEnumeration(fieldMetadata.getBroadleafEnumeration(), fieldMetadata,
                        addMetadataFromMappingDataRequest.getDynamicEntityDao());
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
        return MetadataProviderResponse.HANDLED;
    }

    @Override
    public MetadataProviderResponse addMetadataFromFieldType(AddMetadataFromFieldTypeRequest addMetadataFromFieldTypeRequest,
                                                          Map<String, FieldMetadata> metadata) {
        if (addMetadataFromFieldTypeRequest.getPresentationAttribute() != null) {
            if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.UNKNOWN &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.BOOLEAN &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.INTEGER &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.DATE &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.STRING &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.MONEY &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.DECIMAL &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.FOREIGN_KEY &&
                            addMetadataFromFieldTypeRequest.getExplicitType() != SupportedFieldType.ADDITIONAL_FOREIGN_KEY
                    ) {
                metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                        .getMetadata().getFieldMetadata(addMetadataFromFieldTypeRequest.getPrefix(),
                                addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                                addMetadataFromFieldTypeRequest.getComponentProperties(),
                                addMetadataFromFieldTypeRequest.getExplicitType(), addMetadataFromFieldTypeRequest.getType(),
                                addMetadataFromFieldTypeRequest.getTargetClass(),
                                addMetadataFromFieldTypeRequest.getPresentationAttribute(), addMetadataFromFieldTypeRequest.
                                getMergedPropertyType(), addMetadataFromFieldTypeRequest.getDynamicEntityDao()));
            } else if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                            addMetadataFromFieldTypeRequest.getExplicitType() == SupportedFieldType.BOOLEAN
                            ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(Boolean.class) ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(Character.class)
                    ) {
                metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                        .getMetadata().getFieldMetadata(addMetadataFromFieldTypeRequest.getPrefix(),
                                addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                                addMetadataFromFieldTypeRequest.getComponentProperties(),
                                SupportedFieldType.BOOLEAN, addMetadataFromFieldTypeRequest.getType(),
                                addMetadataFromFieldTypeRequest.getTargetClass(),
                                addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                                addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                                addMetadataFromFieldTypeRequest.getDynamicEntityDao()));
            } else if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                        addMetadataFromFieldTypeRequest.getExplicitType() == SupportedFieldType.INTEGER
                        ||
                        addMetadataFromFieldTypeRequest.getReturnedClass().equals(Byte.class) ||
                        addMetadataFromFieldTypeRequest.getReturnedClass().equals(Short.class) ||
                        addMetadataFromFieldTypeRequest.getReturnedClass().equals(Integer.class) ||
                        addMetadataFromFieldTypeRequest.getReturnedClass().equals(Long.class)
                    ) {
                if (addMetadataFromFieldTypeRequest.getRequestedPropertyName().equals(addMetadataFromFieldTypeRequest.getIdProperty())) {
                    metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().getFieldMetadata(
                            addMetadataFromFieldTypeRequest.getPrefix(), addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                            addMetadataFromFieldTypeRequest.getComponentProperties(),
                            SupportedFieldType.ID, SupportedFieldType.INTEGER, addMetadataFromFieldTypeRequest.getType(),
                            addMetadataFromFieldTypeRequest.getTargetClass(), addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                            addMetadataFromFieldTypeRequest.getMergedPropertyType(), addMetadataFromFieldTypeRequest.getDynamicEntityDao()));
                } else {
                    metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().getFieldMetadata(addMetadataFromFieldTypeRequest
                            .getPrefix(), addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                            addMetadataFromFieldTypeRequest.getComponentProperties(),
                            SupportedFieldType.INTEGER, addMetadataFromFieldTypeRequest.getType(),
                            addMetadataFromFieldTypeRequest.getTargetClass(), addMetadataFromFieldTypeRequest.
                            getPresentationAttribute(), addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                            addMetadataFromFieldTypeRequest.getDynamicEntityDao()));
                }
            } else if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                            addMetadataFromFieldTypeRequest.getExplicitType() == SupportedFieldType.DATE
                            ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(Calendar.class) ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(Date.class) ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(Timestamp.class)
                    ) {
                metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                    addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                    .getMetadata().getFieldMetadata(addMetadataFromFieldTypeRequest.getPrefix(),
                        addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getComponentProperties(),
                        SupportedFieldType.DATE, addMetadataFromFieldTypeRequest.getType(),
                        addMetadataFromFieldTypeRequest.getTargetClass(),
                        addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                        addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                    )
                );
            } else if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                            addMetadataFromFieldTypeRequest.getExplicitType() == SupportedFieldType.STRING
                            ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(String.class)
                    ) {
                if (addMetadataFromFieldTypeRequest.getRequestedPropertyName().equals(addMetadataFromFieldTypeRequest.getIdProperty())) {
                    metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().getFieldMetadata(
                            addMetadataFromFieldTypeRequest.getPrefix(),
                            addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                            addMetadataFromFieldTypeRequest.getComponentProperties(),
                            SupportedFieldType.ID, SupportedFieldType.STRING,
                            addMetadataFromFieldTypeRequest.getType(),
                            addMetadataFromFieldTypeRequest.getTargetClass(),
                            addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                            addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                            addMetadataFromFieldTypeRequest.getDynamicEntityDao()));
                } else {
                    metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().getFieldMetadata(
                            addMetadataFromFieldTypeRequest.getPrefix(),
                            addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                            addMetadataFromFieldTypeRequest.getComponentProperties(),
                            SupportedFieldType.STRING, addMetadataFromFieldTypeRequest.getType(),
                            addMetadataFromFieldTypeRequest.getTargetClass(),
                            addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                            addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                            addMetadataFromFieldTypeRequest.getDynamicEntityDao()));
                }
            } else if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                            addMetadataFromFieldTypeRequest.getExplicitType() == SupportedFieldType.MONEY
                            ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(Money.class)
                    ) {
                metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                    addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().getFieldMetadata(
                        addMetadataFromFieldTypeRequest.getPrefix(),
                        addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getComponentProperties(),
                        SupportedFieldType.MONEY, addMetadataFromFieldTypeRequest.getType(),
                        addMetadataFromFieldTypeRequest.getTargetClass(),
                        addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                        addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                    )
                );
            } else if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                            addMetadataFromFieldTypeRequest.getExplicitType() == SupportedFieldType.DECIMAL
                            ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(Double.class) ||
                            addMetadataFromFieldTypeRequest.getReturnedClass().equals(BigDecimal.class)
                    ) {
                metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                    addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().getFieldMetadata(
                        addMetadataFromFieldTypeRequest.getPrefix(),
                        addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getComponentProperties(),
                        SupportedFieldType.DECIMAL, addMetadataFromFieldTypeRequest.getType(),
                        addMetadataFromFieldTypeRequest.getTargetClass(),
                        addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                        addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                    )
                );
            } else if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                            addMetadataFromFieldTypeRequest.getExplicitType() == SupportedFieldType.FOREIGN_KEY
                            ||
                            addMetadataFromFieldTypeRequest.getForeignField() != null &&
                                    addMetadataFromFieldTypeRequest.isPropertyForeignKey()
                    ) {
                ClassMetadata foreignMetadata;
                String foreignKeyClass;
                String lookupDisplayProperty;
                if (addMetadataFromFieldTypeRequest.getForeignField() == null) {
                    Class<?>[] entities = addMetadataFromFieldTypeRequest.getDynamicEntityDao().
                            getAllPolymorphicEntitiesFromCeiling(addMetadataFromFieldTypeRequest.getType().getReturnedClass());
                    foreignMetadata = addMetadataFromFieldTypeRequest.getDynamicEntityDao().getSessionFactory().getClassMetadata(entities
                            [entities.length - 1]);
                    foreignKeyClass = entities[entities.length - 1].getName();
                    lookupDisplayProperty = ((BasicFieldMetadata) addMetadataFromFieldTypeRequest.
                            getPresentationAttribute()).getLookupDisplayProperty();
                    if (StringUtils.isEmpty(lookupDisplayProperty) &&
                            AdminMainEntity.class.isAssignableFrom(entities[entities.length - 1])) {
                        lookupDisplayProperty = AdminMainEntity.MAIN_ENTITY_NAME_PROPERTY;
                    }
                    if (StringUtils.isEmpty(lookupDisplayProperty)) {
                        lookupDisplayProperty = "name";
                    }
                } else {
                    try {
                        foreignMetadata = addMetadataFromFieldTypeRequest.getDynamicEntityDao().getSessionFactory().
                                getClassMetadata(Class.forName(addMetadataFromFieldTypeRequest.getForeignField()
                                .getForeignKeyClass()));
                        foreignKeyClass = addMetadataFromFieldTypeRequest.getForeignField().getForeignKeyClass();
                        lookupDisplayProperty = addMetadataFromFieldTypeRequest.getForeignField().getDisplayValueProperty();
                        if (StringUtils.isEmpty(lookupDisplayProperty) &&
                                AdminMainEntity.class.isAssignableFrom(Class.forName(foreignKeyClass))) {
                            lookupDisplayProperty = AdminMainEntity.MAIN_ENTITY_NAME_PROPERTY;
                        }
                        if (StringUtils.isEmpty(lookupDisplayProperty)) {
                            lookupDisplayProperty = "name";
                        }
                    } catch (ClassNotFoundException e) {
                        throw new RuntimeException(e);
                    }
                }
                Class<?> foreignResponseType = foreignMetadata.getIdentifierType().getReturnedClass();
                if (foreignResponseType.equals(String.class)) {
                    metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().
                            getFieldMetadata(addMetadataFromFieldTypeRequest.getPrefix(),
                                addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                                addMetadataFromFieldTypeRequest.getComponentProperties(),
                                SupportedFieldType.FOREIGN_KEY, SupportedFieldType.STRING,
                                addMetadataFromFieldTypeRequest.getType(),
                                addMetadataFromFieldTypeRequest.getTargetClass(),
                                addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                                addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                                addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                            )
                    );
                } else {
                    metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(), addMetadataFromFieldTypeRequest
                        .getDynamicEntityDao().getMetadata().getFieldMetadata(addMetadataFromFieldTypeRequest.getPrefix(),
                                addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                                addMetadataFromFieldTypeRequest.getComponentProperties(),
                                SupportedFieldType.FOREIGN_KEY, SupportedFieldType.INTEGER,
                                addMetadataFromFieldTypeRequest.getType(),
                                addMetadataFromFieldTypeRequest.getTargetClass(),
                                addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                                addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                                addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                        )
                    );
                }
                ((BasicFieldMetadata) metadata.get(addMetadataFromFieldTypeRequest.getRequestedPropertyName())).
                        setForeignKeyProperty(foreignMetadata.getIdentifierPropertyName());
                ((BasicFieldMetadata) metadata.get(addMetadataFromFieldTypeRequest.getRequestedPropertyName()))
                        .setForeignKeyClass(foreignKeyClass);
                ((BasicFieldMetadata) metadata.get(addMetadataFromFieldTypeRequest.getRequestedPropertyName())).
                        setForeignKeyDisplayValueProperty(lookupDisplayProperty);
            } else if (
                    addMetadataFromFieldTypeRequest.getExplicitType() != null &&
                            addMetadataFromFieldTypeRequest.getExplicitType() == SupportedFieldType.ADDITIONAL_FOREIGN_KEY
                            ||
                            addMetadataFromFieldTypeRequest.getAdditionalForeignFields() != null &&
                                    addMetadataFromFieldTypeRequest.getAdditionalForeignKeyIndexPosition() >= 0
                    ) {
                if (!addMetadataFromFieldTypeRequest.getType().isEntityType()) {
                    throw new IllegalArgumentException("Only ManyToOne and OneToOne fields can be marked as a " +
                            "SupportedFieldType of ADDITIONAL_FOREIGN_KEY");
                }
                ClassMetadata foreignMetadata;
                String foreignKeyClass;
                String lookupDisplayProperty;
                if (addMetadataFromFieldTypeRequest.getAdditionalForeignKeyIndexPosition() < 0) {
                    Class<?>[] entities = addMetadataFromFieldTypeRequest.getDynamicEntityDao().getAllPolymorphicEntitiesFromCeiling
                            (addMetadataFromFieldTypeRequest.getType().getReturnedClass());
                    foreignMetadata = addMetadataFromFieldTypeRequest.getDynamicEntityDao().getSessionFactory().
                            getClassMetadata(entities[entities.length - 1]);
                    foreignKeyClass = entities[entities.length - 1].getName();
                    lookupDisplayProperty = ((BasicFieldMetadata) addMetadataFromFieldTypeRequest.getPresentationAttribute()).
                            getLookupDisplayProperty();
                    if (StringUtils.isEmpty(lookupDisplayProperty) &&
                            AdminMainEntity.class.isAssignableFrom(entities[entities.length - 1])) {
                        lookupDisplayProperty = AdminMainEntity.MAIN_ENTITY_NAME_PROPERTY;
                    }
                    if (StringUtils.isEmpty(lookupDisplayProperty)) {
                        lookupDisplayProperty = "name";
                    }
                } else {
                    try {
                        foreignMetadata = addMetadataFromFieldTypeRequest.getDynamicEntityDao().getSessionFactory().
                                getClassMetadata(Class.forName(addMetadataFromFieldTypeRequest.getAdditionalForeignFields()
                                        [addMetadataFromFieldTypeRequest.getAdditionalForeignKeyIndexPosition()].getForeignKeyClass()));
                        foreignKeyClass = addMetadataFromFieldTypeRequest.getAdditionalForeignFields()[
                                addMetadataFromFieldTypeRequest.getAdditionalForeignKeyIndexPosition()].getForeignKeyClass();
                        lookupDisplayProperty = addMetadataFromFieldTypeRequest.getAdditionalForeignFields()[
                                addMetadataFromFieldTypeRequest.getAdditionalForeignKeyIndexPosition()].getDisplayValueProperty();
                        if (StringUtils.isEmpty(lookupDisplayProperty) && AdminMainEntity.class.isAssignableFrom(Class.forName(foreignKeyClass))) {
                            lookupDisplayProperty = AdminMainEntity.MAIN_ENTITY_NAME_PROPERTY;
                        }
                        if (StringUtils.isEmpty(lookupDisplayProperty)) {
                            lookupDisplayProperty = "name";
                        }
                    } catch (ClassNotFoundException e) {
                        throw new RuntimeException(e);
                    }
                }
                Class<?> foreignResponseType = foreignMetadata.getIdentifierType().getReturnedClass();
                if (foreignResponseType.equals(String.class)) {
                    metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().getFieldMetadata(
                            addMetadataFromFieldTypeRequest.getPrefix(),
                            addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                            addMetadataFromFieldTypeRequest.getComponentProperties(),
                            SupportedFieldType.ADDITIONAL_FOREIGN_KEY,
                            SupportedFieldType.STRING,
                            addMetadataFromFieldTypeRequest.getType(),
                            addMetadataFromFieldTypeRequest.getTargetClass(),
                            addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                            addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                            addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                        )
                    );
                } else {
                    metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                        addMetadataFromFieldTypeRequest.getDynamicEntityDao().getMetadata().
                            getFieldMetadata(addMetadataFromFieldTypeRequest.getPrefix(),
                                addMetadataFromFieldTypeRequest.getRequestedPropertyName(),
                                addMetadataFromFieldTypeRequest.getComponentProperties(),
                                SupportedFieldType.ADDITIONAL_FOREIGN_KEY, SupportedFieldType.INTEGER,
                                addMetadataFromFieldTypeRequest.getType(),
                                addMetadataFromFieldTypeRequest.getTargetClass(),
                                addMetadataFromFieldTypeRequest.getPresentationAttribute(),
                                addMetadataFromFieldTypeRequest.getMergedPropertyType(),
                                addMetadataFromFieldTypeRequest.getDynamicEntityDao()
                            )
                    );
                }
                ((BasicFieldMetadata) metadata.get(addMetadataFromFieldTypeRequest.getRequestedPropertyName())).
                        setForeignKeyProperty(foreignMetadata.getIdentifierPropertyName());
                ((BasicFieldMetadata) metadata.get(addMetadataFromFieldTypeRequest.getRequestedPropertyName())).
                        setForeignKeyClass(foreignKeyClass);
                ((BasicFieldMetadata) metadata.get(addMetadataFromFieldTypeRequest.getRequestedPropertyName())).
                        setForeignKeyDisplayValueProperty(lookupDisplayProperty);
            }
            //return type not supported - just skip this property
            return MetadataProviderResponse.HANDLED;
        }
        return MetadataProviderResponse.NOT_HANDLED;
    }

}


File: admin/broadleaf-open-admin-platform/src/main/java/org/broadleafcommerce/openadmin/server/dao/provider/metadata/MapFieldMetadataProvider.java
/*
 * #%L
 * BroadleafCommerce Open Admin Platform
 * %%
 * Copyright (C) 2009 - 2013 Broadleaf Commerce
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */
package org.broadleafcommerce.openadmin.server.dao.provider.metadata;

import org.apache.commons.lang.ArrayUtils;
import org.apache.commons.lang.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.broadleafcommerce.common.presentation.AdminPresentationMap;
import org.broadleafcommerce.common.presentation.AdminPresentationOperationTypes;
import org.broadleafcommerce.common.presentation.client.OperationType;
import org.broadleafcommerce.common.presentation.client.PersistencePerspectiveItemType;
import org.broadleafcommerce.common.presentation.client.UnspecifiedBooleanType;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMapOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeEntry;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeOverride;
import org.broadleafcommerce.common.presentation.override.AdminPresentationMergeOverrides;
import org.broadleafcommerce.common.presentation.override.AdminPresentationOverrides;
import org.broadleafcommerce.common.presentation.override.PropertyType;
import org.broadleafcommerce.openadmin.dto.FieldMetadata;
import org.broadleafcommerce.openadmin.dto.ForeignKey;
import org.broadleafcommerce.openadmin.dto.MapMetadata;
import org.broadleafcommerce.openadmin.dto.MapStructure;
import org.broadleafcommerce.openadmin.dto.PersistencePerspective;
import org.broadleafcommerce.openadmin.dto.SimpleValueMapStructure;
import org.broadleafcommerce.openadmin.dto.override.FieldMetadataOverride;
import org.broadleafcommerce.openadmin.server.dao.DynamicEntityDao;
import org.broadleafcommerce.openadmin.server.dao.FieldInfo;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataFromFieldTypeRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.AddMetadataRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaAnnotationRequest;
import org.broadleafcommerce.openadmin.server.dao.provider.metadata.request.OverrideViaXmlRequest;
import org.broadleafcommerce.openadmin.server.service.type.MetadataProviderResponse;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Component;

import java.lang.reflect.Field;
import java.lang.reflect.ParameterizedType;
import java.util.HashMap;
import java.util.Map;

/**
 * @author Jeff Fischer
 */
@Component("blMapFieldMetadataProvider")
@Scope("prototype")
public class MapFieldMetadataProvider extends AdvancedCollectionFieldMetadataProvider {

    private static final Log LOG = LogFactory.getLog(MapFieldMetadataProvider.class);

    protected boolean canHandleFieldForConfiguredMetadata(AddMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentationMap annot = addMetadataRequest.getRequestedField().getAnnotation(AdminPresentationMap.class);
        return annot != null;
    }

    protected boolean canHandleAnnotationOverride(OverrideViaAnnotationRequest overrideViaAnnotationRequest, Map<String, FieldMetadata> metadata) {
        AdminPresentationOverrides myOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationOverrides.class);
        AdminPresentationMergeOverrides myMergeOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationMergeOverrides.class);
        return (myOverrides != null && !ArrayUtils.isEmpty(myOverrides.maps())) || myMergeOverrides != null;
    }

    @Override
    public MetadataProviderResponse addMetadata(AddFieldMetadataRequest addMetadataRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleFieldForConfiguredMetadata(addMetadataRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        AdminPresentationMap annot = addMetadataRequest.getRequestedField().getAnnotation(AdminPresentationMap.class);
        FieldInfo info = buildFieldInfo(addMetadataRequest.getRequestedField());
        FieldMetadataOverride override = constructMapMetadataOverride(annot);
        buildMapMetadata(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(),
        metadata, info, override, addMetadataRequest.getDynamicEntityDao(), addMetadataRequest.getPrefix());
        setClassOwnership(addMetadataRequest.getParentClass(), addMetadataRequest.getTargetClass(), metadata, info);
        return MetadataProviderResponse.HANDLED;
    }

    @Override
    public MetadataProviderResponse overrideViaAnnotation(OverrideViaAnnotationRequest overrideViaAnnotationRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleAnnotationOverride(overrideViaAnnotationRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        Map<String, AdminPresentationMapOverride> presentationMapOverrides = new HashMap<String, AdminPresentationMapOverride>();

        AdminPresentationOverrides myOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationOverrides.class);
        if (myOverrides != null) {
            for (AdminPresentationMapOverride myOverride : myOverrides.maps()) {
                presentationMapOverrides.put(myOverride.name(), myOverride);
            }
        }

        for (String propertyName : presentationMapOverrides.keySet()) {
            for (String key : metadata.keySet()) {
                if (key.startsWith(propertyName)) {
                    buildAdminPresentationMapOverride(overrideViaAnnotationRequest.getPrefix(), overrideViaAnnotationRequest.getParentExcluded(), metadata, presentationMapOverrides,
                            propertyName, key, overrideViaAnnotationRequest.getDynamicEntityDao());
                }
            }
        }

        AdminPresentationMergeOverrides myMergeOverrides = overrideViaAnnotationRequest.getRequestedEntity().getAnnotation(AdminPresentationMergeOverrides.class);
        if (myMergeOverrides != null) {
            for (AdminPresentationMergeOverride override : myMergeOverrides.value()) {
                String propertyName = override.name();
                Map<String, FieldMetadata> loopMap = new HashMap<String, FieldMetadata>();
                loopMap.putAll(metadata);
                for (Map.Entry<String, FieldMetadata> entry : loopMap.entrySet()) {
                    if (entry.getKey().startsWith(propertyName) || StringUtils.isEmpty(propertyName)) {
                        FieldMetadata targetMetadata = entry.getValue();
                        if (targetMetadata instanceof MapMetadata) {
                            MapMetadata serverMetadata = (MapMetadata) targetMetadata;
                            if (serverMetadata.getTargetClass() != null) {
                                try {
                                    Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                                    Class<?> parentClass = null;
                                    if (serverMetadata.getOwningClass() != null) {
                                        parentClass = Class.forName(serverMetadata.getOwningClass());
                                    }
                                    String fieldName = serverMetadata.getFieldName();
                                    Field field = overrideViaAnnotationRequest.getDynamicEntityDao().getFieldManager()
                                                .getField(targetClass, fieldName);
                                    Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                                    temp.put(field.getName(), serverMetadata);
                                    FieldInfo info = buildFieldInfo(field);
                                    FieldMetadataOverride fieldMetadataOverride = overrideMapMergeMetadata(override);
                                    if (serverMetadata.getExcluded() != null && serverMetadata.getExcluded() &&
                                            (fieldMetadataOverride.getExcluded() == null || fieldMetadataOverride.getExcluded())) {
                                        continue;
                                    }
                                    buildMapMetadata(parentClass, targetClass, temp, info, fieldMetadataOverride,
                                            overrideViaAnnotationRequest.getDynamicEntityDao(), serverMetadata.getPrefix());
                                    serverMetadata = (MapMetadata) temp.get(field.getName());
                                    metadata.put(entry.getKey(), serverMetadata);
                                } catch (Exception e) {
                                    throw new RuntimeException(e);
                                }
                            }
                        }
                    }
                }
            }
        }

        return MetadataProviderResponse.HANDLED;
    }

    @Override
        Map<String, FieldMetadataOverride> overrides = getTargetedOverride(overrideViaXmlRequest.getDynamicEntityDao(), overrideViaXmlRequest.getRequestedConfigKey(), overrideViaXmlRequest.getRequestedCeilingEntity());
    public MetadataProviderResponse overrideViaXml(OverrideViaXmlRequest overrideViaXmlRequest, Map<String, FieldMetadata> metadata) {
        if (overrides != null) {
            for (String propertyName : overrides.keySet()) {
                final FieldMetadataOverride localMetadata = overrides.get(propertyName);
                for (String key : metadata.keySet()) {
                    if (key.equals(propertyName)) {
                        try {
                            if (metadata.get(key) instanceof MapMetadata) {
                                MapMetadata serverMetadata = (MapMetadata) metadata.get(key);
                                if (serverMetadata.getTargetClass() != null) {
                                    Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                                    Class<?> parentClass = null;
                                    if (serverMetadata.getOwningClass() != null) {
                                        parentClass = Class.forName(serverMetadata.getOwningClass());
                                    }
                                    String fieldName = serverMetadata.getFieldName();
                                    Field field = overrideViaXmlRequest.getDynamicEntityDao().getFieldManager().getField(targetClass, fieldName);
                                    Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                                    temp.put(field.getName(), serverMetadata);
                                    FieldInfo info = buildFieldInfo(field);
                                    buildMapMetadata(parentClass, targetClass, temp, info, localMetadata, overrideViaXmlRequest.getDynamicEntityDao(), serverMetadata.getPrefix());
                                    serverMetadata = (MapMetadata) temp.get(field.getName());
                                    metadata.put(key, serverMetadata);
                                    if (overrideViaXmlRequest.getParentExcluded()) {
                                        if (LOG.isDebugEnabled()) {
                                            LOG.debug("applyMapMetadataOverrides:Excluding " + key + "because parent is marked as excluded.");
                                        }
                                        serverMetadata.setExcluded(true);
                                    }
                                }
                            }
                        } catch (Exception e) {
                            throw new RuntimeException(e);
                        }
                    }
                }
            }
        }
        return MetadataProviderResponse.HANDLED;
    }

    @Override
    public MetadataProviderResponse addMetadataFromFieldType(AddMetadataFromFieldTypeRequest addMetadataFromFieldTypeRequest, Map<String, FieldMetadata> metadata) {
        if (!canHandleFieldForTypeMetadata(addMetadataFromFieldTypeRequest, metadata)) {
            return MetadataProviderResponse.NOT_HANDLED;
        }
        //do nothing but add the property without manipulation
        metadata.put(addMetadataFromFieldTypeRequest.getRequestedPropertyName(), addMetadataFromFieldTypeRequest.getPresentationAttribute());
        return MetadataProviderResponse.HANDLED;
    }

    protected void buildAdminPresentationMapOverride(String prefix, Boolean isParentExcluded, Map<String, FieldMetadata> mergedProperties,
             Map<String, AdminPresentationMapOverride> presentationMapOverrides, String propertyName, String key, DynamicEntityDao dynamicEntityDao) {
        AdminPresentationMapOverride override = presentationMapOverrides.get(propertyName);
        if (override != null) {
            AdminPresentationMap annot = override.value();
            if (annot != null) {
                String testKey = prefix + key;
                if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && annot.excluded()) {
                    FieldMetadata metadata = mergedProperties.get(key);
                    if (LOG.isDebugEnabled()) {
                        LOG.debug("buildAdminPresentationMapOverride:Excluding " + key + "because an override annotation declared " + testKey + "to be excluded");
                    }
                    metadata.setExcluded(true);
                    return;
                }
                if ((testKey.startsWith(propertyName + ".") || testKey.equals(propertyName)) && !annot.excluded()) {
                    FieldMetadata metadata = mergedProperties.get(key);
                    if (!isParentExcluded) {
                        if (LOG.isDebugEnabled()) {
                            LOG.debug("buildAdminPresentationMapOverride:Showing " + key + "because an override annotation declared " + testKey + " to not be excluded");
                        }
                        metadata.setExcluded(false);
                    }
                }
                if (!(mergedProperties.get(key) instanceof MapMetadata)) {
                    return;
                }
                MapMetadata serverMetadata = (MapMetadata) mergedProperties.get(key);
                if (serverMetadata.getTargetClass() != null) {
                    try {
                        Class<?> targetClass = Class.forName(serverMetadata.getTargetClass());
                        Class<?> parentClass = null;
                        if (serverMetadata.getOwningClass() != null) {
                            parentClass = Class.forName(serverMetadata.getOwningClass());
                        }
                        String fieldName = serverMetadata.getFieldName();
                        Field field = dynamicEntityDao.getFieldManager().getField(targetClass, fieldName);
                        FieldMetadataOverride localMetadata = constructMapMetadataOverride(annot);
                        //do not include the previous metadata - we want to construct a fresh metadata from the override annotation
                        Map<String, FieldMetadata> temp = new HashMap<String, FieldMetadata>(1);
                        FieldInfo info = buildFieldInfo(field);
                        buildMapMetadata(parentClass, targetClass, temp, info, localMetadata, dynamicEntityDao, serverMetadata.getPrefix());
                        MapMetadata result = (MapMetadata) temp.get(field.getName());
                        result.setInheritedFromType(serverMetadata.getInheritedFromType());
                        result.setAvailableToTypes(serverMetadata.getAvailableToTypes());
                        mergedProperties.put(key, result);
                        if (isParentExcluded) {
                            if (LOG.isDebugEnabled()) {
                                LOG.debug("buildAdminPresentationMapOverride:Excluding " + key + "because the parent was excluded");
                            }
                            serverMetadata.setExcluded(true);
                        }
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                }
            }
        }
    }

    protected FieldMetadataOverride overrideMapMergeMetadata(AdminPresentationMergeOverride merge) {
        FieldMetadataOverride fieldMetadataOverride = new FieldMetadataOverride();
        Map<String, AdminPresentationMergeEntry> overrideValues = getAdminPresentationEntries(merge.mergeEntries());
        for (Map.Entry<String, AdminPresentationMergeEntry> entry : overrideValues.entrySet()) {
            String stringValue = entry.getValue().overrideValue();
            if (entry.getKey().equals(PropertyType.AdminPresentationMap.CURRENCYCODEFIELD)) {
                fieldMetadataOverride.setCurrencyCodeField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.CUSTOMCRITERIA)) {
                fieldMetadataOverride.setCustomCriteria(entry.getValue().stringArrayOverrideValue());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.DELETEENTITYUPONREMOVE)) {
                fieldMetadataOverride.setDeleteEntityUponRemove(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .booleanOverrideValue() : Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.EXCLUDED)) {
                fieldMetadataOverride.setExcluded(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .booleanOverrideValue() : Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.FORCEFREEFORMKEYS)) {
                fieldMetadataOverride.setForceFreeFormKeys(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .booleanOverrideValue() : Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.FRIENDLYNAME)) {
                fieldMetadataOverride.setFriendlyName(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.ISSIMPLEVALUE)) {
                fieldMetadataOverride.setSimpleValue(UnspecifiedBooleanType.valueOf(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.KEYCLASS)) {
                fieldMetadataOverride.setKeyClass(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.KEYPROPERTYFRIENDLYNAME)) {
                fieldMetadataOverride.setKeyPropertyFriendlyName(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.MAPKEYVALUEPROPERTY)) {
                fieldMetadataOverride.setMapKeyValueProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.KEYS)) {
                if (!ArrayUtils.isEmpty(entry.getValue().keys())) {
                    String[][] keys = new String[entry.getValue().keys().length][2];
                    for (int j=0;j<keys.length;j++){
                        keys[j][0] = entry.getValue().keys()[j].keyName();
                        keys[j][1] = entry.getValue().keys()[j].friendlyKeyName();
                    }
                    fieldMetadataOverride.setKeys(keys);
                }
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.MANYTOFIELD)) {
                fieldMetadataOverride.setManyToField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.MAPKEYOPTIONENTITYCLASS)) {
                fieldMetadataOverride.setMapKeyOptionEntityClass(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.MAPKEYOPTIONENTITYDISPLAYFIELD)) {
                fieldMetadataOverride.setMapKeyOptionEntityDisplayField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.MAPKEYOPTIONENTITYVALUEFIELD)) {
                fieldMetadataOverride.setMapKeyOptionEntityValueField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.MEDIAFIELD)) {
                fieldMetadataOverride.setMediaField(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.OPERATIONTYPES)) {
                AdminPresentationOperationTypes operationType = entry.getValue().operationTypes();
                fieldMetadataOverride.setAddType(operationType.addType());
                fieldMetadataOverride.setRemoveType(operationType.removeType());
                fieldMetadataOverride.setUpdateType(operationType.updateType());
                fieldMetadataOverride.setFetchType(operationType.fetchType());
                fieldMetadataOverride.setInspectType(operationType.inspectType());
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.ORDER)) {
                fieldMetadataOverride.setOrder(StringUtils.isEmpty(stringValue) ? entry.getValue().intOverrideValue() :
                        Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.READONLY)) {
                fieldMetadataOverride.setReadOnly(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .booleanOverrideValue() : Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.SECURITYLEVEL)) {
                fieldMetadataOverride.setSecurityLevel(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.SHOWIFPROPERTY)) {
                fieldMetadataOverride.setShowIfProperty(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.TAB)) {
                fieldMetadataOverride.setTab(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.TABORDER)) {
                fieldMetadataOverride.setTabOrder(StringUtils.isEmpty(stringValue) ? entry.getValue()
                        .intOverrideValue() : Integer.parseInt(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.USESERVERSIDEINSPECTIONCACHE)) {
                fieldMetadataOverride.setUseServerSideInspectionCache(StringUtils.isEmpty(stringValue) ? entry
                        .getValue().booleanOverrideValue() : Boolean.parseBoolean(stringValue));
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.VALUECLASS)) {
                fieldMetadataOverride.setValueClass(stringValue);
            } else if (entry.getKey().equals(PropertyType.AdminPresentationMap.VALUEPROPERTYFRIENDLYNAME)) {
                fieldMetadataOverride.setValuePropertyFriendlyName(stringValue);
            } else {
                if (LOG.isDebugEnabled()) {
                    LOG.debug("Unrecognized type: " + entry.getKey() + ". Not setting on map field.");
                }
            }
        }

        return fieldMetadataOverride;
    }

    protected FieldMetadataOverride constructMapMetadataOverride(AdminPresentationMap map) {
        if (map != null) {
            FieldMetadataOverride override = new FieldMetadataOverride();
            override.setDeleteEntityUponRemove(map.deleteEntityUponRemove());
            override.setKeyClass(map.keyClass().getName());
            override.setMapKeyValueProperty(map.mapKeyValueProperty());
            override.setKeyPropertyFriendlyName(map.keyPropertyFriendlyName());
            if (!ArrayUtils.isEmpty(map.keys())) {
                String[][] keys = new String[map.keys().length][2];
                for (int j=0;j<keys.length;j++){
                    keys[j][0] = map.keys()[j].keyName();
                    keys[j][1] = map.keys()[j].friendlyKeyName();
                }
                override.setKeys(keys);
            }
            override.setMapKeyOptionEntityClass(map.mapKeyOptionEntityClass().getName());
            override.setMapKeyOptionEntityDisplayField(map.mapKeyOptionEntityDisplayField());
            override.setMapKeyOptionEntityValueField(map.mapKeyOptionEntityValueField());
            override.setMediaField(map.mediaField());
            override.setToOneTargetProperty(map.toOneTargetProperty());
            override.setSimpleValue(map.isSimpleValue());
            override.setValueClass(map.valueClass().getName());
            override.setValuePropertyFriendlyName(map.valuePropertyFriendlyName());
            override.setCustomCriteria(map.customCriteria());
            override.setUseServerSideInspectionCache(map.useServerSideInspectionCache());
            override.setExcluded(map.excluded());
            override.setFriendlyName(map.friendlyName());
            override.setReadOnly(map.readOnly());
            override.setOrder(map.order());
            override.setTab(map.tab());
            override.setTabOrder(map.tabOrder());
            override.setSecurityLevel(map.securityLevel());
            override.setAddType(map.operationTypes().addType());
            override.setFetchType(map.operationTypes().fetchType());
            override.setRemoveType(map.operationTypes().removeType());
            override.setUpdateType(map.operationTypes().updateType());
            override.setInspectType(map.operationTypes().inspectType());
            override.setShowIfProperty(map.showIfProperty());
            override.setCurrencyCodeField(map.currencyCodeField());
            override.setForceFreeFormKeys(map.forceFreeFormKeys());
            override.setManyToField(map.manyToField());
            return override;
        }
        throw new IllegalArgumentException("AdminPresentationMap annotation not found on field");
    }

    protected void buildMapMetadata(Class<?> parentClass, Class<?> targetClass, Map<String, FieldMetadata> attributes,
                                    FieldInfo field, FieldMetadataOverride map, DynamicEntityDao dynamicEntityDao, String prefix) {
        MapMetadata serverMetadata = (MapMetadata) attributes.get(field.getName());

        Class<?> resolvedClass = parentClass==null?targetClass:parentClass;
        MapMetadata metadata;
        if (serverMetadata != null) {
            metadata = serverMetadata;
        } else {
            metadata = new MapMetadata();
        }
        if (map.getReadOnly() != null) {
            metadata.setMutable(!map.getReadOnly());
        }
        if (map.getShowIfProperty()!=null) {
            metadata.setShowIfProperty(map.getShowIfProperty());
        }
        metadata.setPrefix(prefix);

        metadata.setTargetClass(targetClass.getName());
        metadata.setFieldName(field.getName());
        org.broadleafcommerce.openadmin.dto.OperationTypes dtoOperationTypes = new org.broadleafcommerce.openadmin.dto.OperationTypes(OperationType.MAP, OperationType.MAP, OperationType.MAP, OperationType.MAP, OperationType.MAP);
        if (map.getAddType() != null) {
            dtoOperationTypes.setAddType(map.getAddType());
        }
        if (map.getRemoveType() != null) {
            dtoOperationTypes.setRemoveType(map.getRemoveType());
        }
        if (map.getFetchType() != null) {
            dtoOperationTypes.setFetchType(map.getFetchType());
        }
        if (map.getInspectType() != null) {
            dtoOperationTypes.setInspectType(map.getInspectType());
        }
        if (map.getUpdateType() != null) {
            dtoOperationTypes.setUpdateType(map.getUpdateType());
        }

        //don't allow additional non-persistent properties or additional foreign keys for an advanced collection datasource - they don't make sense in this context
        PersistencePerspective persistencePerspective;
        if (serverMetadata != null) {
            persistencePerspective = metadata.getPersistencePerspective();
            persistencePerspective.setOperationTypes(dtoOperationTypes);
        } else {
            persistencePerspective = new PersistencePerspective(dtoOperationTypes, new String[]{}, new ForeignKey[]{});
            metadata.setPersistencePerspective(persistencePerspective);
        }

        String parentObjectClass = resolvedClass.getName();
        Map idMetadata;
        if(parentClass!=null) {
            idMetadata=dynamicEntityDao.getIdMetadata(parentClass);
        } else {
             idMetadata=dynamicEntityDao.getIdMetadata(targetClass);
        }
        String parentObjectIdField = (String) idMetadata.get("name");

        String keyClassName = null;
        if (serverMetadata != null) {
            keyClassName = ((MapStructure) metadata.getPersistencePerspective().getPersistencePerspectiveItems().get
                    (PersistencePerspectiveItemType.MAPSTRUCTURE)).getKeyClassName();
        }
        if (map.getKeyClass() != null && !void.class.getName().equals(map.getKeyClass())) {
            keyClassName = map.getKeyClass();
        }
        if (keyClassName == null) {
            java.lang.reflect.Type type = field.getGenericType();
            if (type instanceof ParameterizedType) {
                ParameterizedType pType = (ParameterizedType) type;
                Class<?> clazz = (Class<?>) pType.getActualTypeArguments()[0];
                if (!ArrayUtils.isEmpty(dynamicEntityDao.getAllPolymorphicEntitiesFromCeiling(clazz))) {
                    throw new IllegalArgumentException("Key class for AdminPresentationMap was determined to be a JPA managed type. Only primitive types for the key type are currently supported.");
                }
                keyClassName = clazz.getName();
            }
        }
        if (keyClassName == null) {
            keyClassName = String.class.getName();
        }

        String keyPropertyName = "key";
        String mapKeyValueProperty = "";
        if (StringUtils.isNotBlank(field.getMapKey())) {
            mapKeyValueProperty = field.getMapKey();
        }
        if (StringUtils.isNotBlank(map.getMapKeyValueProperty())) {
            mapKeyValueProperty = map.getMapKeyValueProperty();
        }
        
        String keyPropertyFriendlyName = null;
        if (serverMetadata != null) {
            keyPropertyFriendlyName = ((MapStructure) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.MAPSTRUCTURE)).getKeyPropertyFriendlyName();
        }
        if (map.getKeyPropertyFriendlyName() != null) {
            keyPropertyFriendlyName = map.getKeyPropertyFriendlyName();
        }
        Boolean deleteEntityUponRemove = null;
        if (serverMetadata != null) {
            deleteEntityUponRemove = ((MapStructure) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.MAPSTRUCTURE)).getDeleteValueEntity();
        }
        if (map.isDeleteEntityUponRemove() != null) {
            deleteEntityUponRemove = map.isDeleteEntityUponRemove();
        }
        String valuePropertyName = "value";
        String valuePropertyFriendlyName = null;
        if (serverMetadata != null) {
            MapStructure structure = (MapStructure) serverMetadata.getPersistencePerspective().getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.MAPSTRUCTURE);
            if (structure instanceof SimpleValueMapStructure) {
                valuePropertyFriendlyName = ((SimpleValueMapStructure) structure).getValuePropertyFriendlyName();
            } else {
                valuePropertyFriendlyName = "";
            }
        }
        if (map.getValuePropertyFriendlyName()!=null) {
            valuePropertyFriendlyName = map.getValuePropertyFriendlyName();
        }
        if (map.getMediaField() != null) {
            metadata.setMediaField(map.getMediaField());
        }
        if (map.getToOneTargetProperty() != null) {
            metadata.setToOneTargetProperty(map.getToOneTargetProperty());
        }
        if (map.getToOneParentProperty() != null) {
            metadata.setToOneParentProperty((map.getToOneParentProperty()));
        }

        if (map.getValueClass() != null && !void.class.getName().equals(map.getValueClass())) {
            metadata.setValueClassName(map.getValueClass());
        }
        if (metadata.getValueClassName() == null) {
            java.lang.reflect.Type type = field.getGenericType();
            if (type instanceof ParameterizedType) {
                ParameterizedType pType = (ParameterizedType) type;
                Class<?> clazz = (Class<?>) pType.getActualTypeArguments()[1];
                Class<?>[] entities = dynamicEntityDao.getAllPolymorphicEntitiesFromCeiling(clazz);
                if (!ArrayUtils.isEmpty(entities)) {
                    metadata.setValueClassName(entities[entities.length-1].getName());
                }
            }
        }
        if (metadata.getValueClassName() == null) {
            if (!StringUtils.isEmpty(field.getManyToManyTargetEntity())) {
                metadata.setValueClassName(field.getManyToManyTargetEntity());
            }
        }
        if (metadata.getValueClassName() == null) {
            metadata.setValueClassName(String.class.getName());
        }

        Boolean simpleValue = null;
        if (map.getSimpleValue()!= null && map.getSimpleValue()!= UnspecifiedBooleanType.UNSPECIFIED) {
            simpleValue = map.getSimpleValue()==UnspecifiedBooleanType.TRUE;
        }
        if (simpleValue==null) {
            java.lang.reflect.Type type = field.getGenericType();
            if (type instanceof ParameterizedType) {
                ParameterizedType pType = (ParameterizedType) type;
                Class<?> clazz = (Class<?>) pType.getActualTypeArguments()[1];
                Class<?>[] entities = dynamicEntityDao.getAllPolymorphicEntitiesFromCeiling(clazz);
                simpleValue = ArrayUtils.isEmpty(entities);
            }
        }
        if (simpleValue==null) {
            //ManyToMany manyToMany = field.getAnnotation(ManyToMany.class);
            if (!StringUtils.isEmpty(field.getManyToManyTargetEntity())) {
                simpleValue = false;
            }
        }
        if (simpleValue == null) {
            throw new IllegalArgumentException("Unable to infer if the value for the map is of a complex or simple type based on any parameterized type or ManyToMany annotation. Please explicitly set the isSimpleValue property.");
        }
        metadata.setSimpleValue(simpleValue);

        if (map.getKeys() != null) {
            metadata.setKeys(map.getKeys());
        }
        
        metadata.setMapKeyValueProperty(mapKeyValueProperty);

        if (map.getMapKeyOptionEntityClass()!=null) {
            if (!void.class.getName().equals(map.getMapKeyOptionEntityClass())) {
                metadata.setMapKeyOptionEntityClass(map.getMapKeyOptionEntityClass());
            } else {
                metadata.setMapKeyOptionEntityClass("");
            }
        }

        if (map.getMapKeyOptionEntityDisplayField() != null) {
            metadata.setMapKeyOptionEntityDisplayField(map.getMapKeyOptionEntityDisplayField());
        }

        if (map.getMapKeyOptionEntityValueField()!=null) {
            metadata.setMapKeyOptionEntityValueField(map.getMapKeyOptionEntityValueField());
        }

        if (map.getForceFreeFormKeys() != null) {
            if (!map.getForceFreeFormKeys() && ArrayUtils.isEmpty(metadata.getKeys()) && (StringUtils.isEmpty(metadata.getMapKeyOptionEntityClass()) || StringUtils.isEmpty(metadata.getMapKeyOptionEntityValueField()) || StringUtils.isEmpty(metadata.getMapKeyOptionEntityDisplayField()))) {
                throw new IllegalArgumentException("Could not ascertain method for generating key options for the annotated map ("+field.getName()+"). Must specify either an array of AdminPresentationMapKey values for the keys property, or utilize the mapOptionKeyClass, mapOptionKeyDisplayField and mapOptionKeyValueField properties. If you wish to allow free form entry for key values, then set forceFreeFormKeys on AdminPresentationMap.");
            }
        }

        MapStructure mapStructure;
        if (serverMetadata != null) {
            ForeignKey foreignKey = (ForeignKey) persistencePerspective.getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.FOREIGNKEY);
            foreignKey.setManyToField(parentObjectIdField);
            foreignKey.setForeignKeyClass(parentObjectClass);
            if (metadata.isSimpleValue()) {
                mapStructure = (SimpleValueMapStructure) persistencePerspective.getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.MAPSTRUCTURE);
                mapStructure.setKeyClassName(keyClassName);
                mapStructure.setKeyPropertyName(keyPropertyName);
                mapStructure.setKeyPropertyFriendlyName(keyPropertyFriendlyName);
                mapStructure.setValueClassName(metadata.getValueClassName());
                ((SimpleValueMapStructure) mapStructure).setValuePropertyName(valuePropertyName);
                ((SimpleValueMapStructure) mapStructure).setValuePropertyFriendlyName(valuePropertyFriendlyName);
                mapStructure.setMapProperty(prefix + field.getName());
                mapStructure.setMutable(metadata.isMutable());
            } else {
                mapStructure = (MapStructure) persistencePerspective.getPersistencePerspectiveItems().get(PersistencePerspectiveItemType.MAPSTRUCTURE);
                mapStructure.setKeyClassName(keyClassName);
                mapStructure.setKeyPropertyName(keyPropertyName);
                mapStructure.setKeyPropertyFriendlyName(keyPropertyFriendlyName);
                mapStructure.setValueClassName(metadata.getValueClassName());
                mapStructure.setMapProperty(prefix + field.getName());
                mapStructure.setDeleteValueEntity(deleteEntityUponRemove);
                mapStructure.setMutable(metadata.isMutable());
            }
        } else {
            ForeignKey foreignKey = new ForeignKey(parentObjectIdField, parentObjectClass);
            persistencePerspective.addPersistencePerspectiveItem(PersistencePerspectiveItemType.FOREIGNKEY, foreignKey);
            if (metadata.isSimpleValue()) {
                mapStructure = new SimpleValueMapStructure(keyClassName, keyPropertyName, keyPropertyFriendlyName, metadata.getValueClassName(), valuePropertyName, valuePropertyFriendlyName, prefix + field.getName(), mapKeyValueProperty);
                mapStructure.setMutable(metadata.isMutable());
            } else {
                mapStructure = new MapStructure(keyClassName, keyPropertyName, keyPropertyFriendlyName, metadata.getValueClassName(), prefix + field.getName(), deleteEntityUponRemove, mapKeyValueProperty);
                mapStructure.setMutable(metadata.isMutable());
            }
            persistencePerspective.addPersistencePerspectiveItem(PersistencePerspectiveItemType.MAPSTRUCTURE, mapStructure);
        }

        if (!StringUtils.isEmpty(map.getManyToField())) {
            mapStructure.setManyToField(map.getManyToField());
        }
        if (mapStructure.getManyToField() == null) {
            //try to infer the value
            if (field.getManyToManyMappedBy() != null) {
                mapStructure.setManyToField(field.getManyToManyMappedBy());
            }
        }
        if (mapStructure.getManyToField() == null) {
            //try to infer the value
            if (field.getOneToManyMappedBy() != null) {
                mapStructure.setManyToField(field.getOneToManyMappedBy());
            }
        }

        if (map.getExcluded() != null) {
            if (LOG.isDebugEnabled()) {
                if (map.getExcluded()) {
                    LOG.debug("buildMapMetadata:Excluding " + field.getName() + " because it was explicitly declared in config");
                } else {
                    LOG.debug("buildMapMetadata:Showing " + field.getName() + " because it was explicitly declared in config");
                }
            }
            metadata.setExcluded(map.getExcluded());
        }
        if (map.getFriendlyName() != null) {
            metadata.setFriendlyName(map.getFriendlyName());
        }
        if (map.getSecurityLevel() != null) {
            metadata.setSecurityLevel(map.getSecurityLevel());
        }
        if (map.getOrder() != null) {
            metadata.setOrder(map.getOrder());
        }

        if (map.getTab() != null) {
            metadata.setTab(map.getTab());
        }
        if (map.getTabOrder() != null) {
            metadata.setTabOrder(map.getTabOrder());
        }

        if (map.getCustomCriteria() != null) {
            metadata.setCustomCriteria(map.getCustomCriteria());
        }

        if (map.getUseServerSideInspectionCache() != null) {
            persistencePerspective.setUseServerSideInspectionCache(map.getUseServerSideInspectionCache());
        }

        if (map.getCurrencyCodeField()!=null) {
            metadata.setCurrencyCodeField(map.getCurrencyCodeField());
        }

        if (map.getForceFreeFormKeys()!=null) {
            metadata.setForceFreeFormKeys(map.getForceFreeFormKeys());
        }

        attributes.put(field.getName(), metadata);
    }

    @Override
    public int getOrder() {
        return FieldMetadataProvider.MAP;
    }
}
