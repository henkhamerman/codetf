Refactoring Types: ['Extract Method']
om/datastax/driver/mapping/AnnotationParser.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.mapping;

import java.lang.annotation.Annotation;
import java.lang.reflect.Field;
import java.lang.reflect.*;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

import com.google.common.base.Strings;

import com.datastax.driver.core.ConsistencyLevel;
import com.datastax.driver.mapping.MethodMapper.EnumParamMapper;
import com.datastax.driver.mapping.MethodMapper.NestedUDTParamMapper;
import com.datastax.driver.mapping.MethodMapper.ParamMapper;
import com.datastax.driver.mapping.MethodMapper.UDTParamMapper;
import com.datastax.driver.mapping.annotations.*;

/**
 * Static metods that facilitates parsing class annotations into the corresponding {@link EntityMapper}.
 */
class AnnotationParser {

    private static final Comparator<Field> fieldComparator = new Comparator<Field>() {
        public int compare(Field f1, Field f2) {
            return position(f1) - position(f2);
        }
    };

    private AnnotationParser() {}

    public static <T> EntityMapper<T> parseEntity(Class<T> entityClass, EntityMapper.Factory factory, MappingManager mappingManager) {
        Table table = AnnotationChecks.getTypeAnnotation(Table.class, entityClass);

        String ksName = table.caseSensitiveKeyspace() ? table.keyspace() : table.keyspace().toLowerCase();
        String tableName = table.caseSensitiveTable() ? table.name() : table.name().toLowerCase();

        ConsistencyLevel writeConsistency = table.writeConsistency().isEmpty() ? null : ConsistencyLevel.valueOf(table.writeConsistency().toUpperCase());
        ConsistencyLevel readConsistency = table.readConsistency().isEmpty() ? null : ConsistencyLevel.valueOf(table.readConsistency().toUpperCase());

        if (Strings.isNullOrEmpty(table.keyspace())) {
            ksName = mappingManager.getSession().getLoggedKeyspace();
            if (Strings.isNullOrEmpty(ksName))
                throw new IllegalArgumentException(String.format(
                    "Error creating mapper for class %s, the @%s annotation declares no default keyspace, and the session is not currently logged to any keyspace",
                    entityClass.getSimpleName(),
                    Table.class.getSimpleName()
                ));
        }

        EntityMapper<T> mapper = factory.create(entityClass, ksName, tableName, writeConsistency, readConsistency);

        List<Field> pks = new ArrayList<Field>();
        List<Field> ccs = new ArrayList<Field>();
        List<Field> rgs = new ArrayList<Field>();

        for (Field field : entityClass.getDeclaredFields()) {
            if(field.isSynthetic() || (field.getModifiers() & Modifier.STATIC) == Modifier.STATIC)
                continue;
            
            AnnotationChecks.validateAnnotations(field, "entity",
                                                 Column.class, ClusteringColumn.class, Enumerated.class, Frozen.class, FrozenKey.class,
                                                 FrozenValue.class, PartitionKey.class, Transient.class);

            if (field.getAnnotation(Transient.class) != null)
                continue;

            switch (kind(field)) {
                case PARTITION_KEY:
                    pks.add(field);
                    break;
                case CLUSTERING_COLUMN:
                    ccs.add(field);
                    break;
                default:
                    rgs.add(field);
                    break;
            }
        }

        Collections.sort(pks, fieldComparator);
        Collections.sort(ccs, fieldComparator);

        validateOrder(pks, "@PartitionKey");
        validateOrder(ccs, "@ClusteringColumn");

        mapper.addColumns(convert(pks, factory, mapper.entityClass, mappingManager),
                          convert(ccs, factory, mapper.entityClass, mappingManager),
                          convert(rgs, factory, mapper.entityClass, mappingManager));
        return mapper;
    }

    public static <T> EntityMapper<T> parseUDT(Class<T> udtClass, EntityMapper.Factory factory, MappingManager mappingManager) {
        UDT udt = AnnotationChecks.getTypeAnnotation(UDT.class, udtClass);

        String ksName = udt.caseSensitiveKeyspace() ? udt.keyspace() : udt.keyspace().toLowerCase();
        String udtName = udt.caseSensitiveType() ? udt.name() : udt.name().toLowerCase();

        if (Strings.isNullOrEmpty(udt.keyspace())) {
            ksName = mappingManager.getSession().getLoggedKeyspace();
            if (Strings.isNullOrEmpty(ksName))
                throw new IllegalArgumentException(String.format(
                    "Error creating UDT mapper for class %s, the @%s annotation declares no default keyspace, and the session is not currently logged to any keyspace",
                    udtClass.getSimpleName(),
                    UDT.class.getSimpleName()
                ));
        }

        EntityMapper<T> mapper = factory.create(udtClass, ksName, udtName, null, null);

        List<Field> columns = new ArrayList<Field>();

        for (Field field : udtClass.getDeclaredFields()) {
            if(field.isSynthetic() || (field.getModifiers() & Modifier.STATIC) == Modifier.STATIC)
                continue;
            
            AnnotationChecks.validateAnnotations(field, "UDT",
                                                 com.datastax.driver.mapping.annotations.Field.class, Frozen.class, FrozenKey.class,
                                                 FrozenValue.class, Enumerated.class, Transient.class);

            if (field.getAnnotation(Transient.class) != null)
                continue;

            switch (kind(field)) {
                case PARTITION_KEY:
                    throw new IllegalArgumentException("Annotation @PartitionKey is not allowed in a class annotated by @UDT");
                case CLUSTERING_COLUMN:
                    throw new IllegalArgumentException("Annotation @ClusteringColumn is not allowed in a class annotated by @UDT");
                default:
                    columns.add(field);
                    break;
            }
        }

        mapper.addColumns(convert(columns, factory, udtClass, mappingManager));
        return mapper;
    }

    private static <T> List<ColumnMapper<T>> convert(List<Field> fields, EntityMapper.Factory factory, Class<T> klass, MappingManager mappingManager) {
        List<ColumnMapper<T>> mappers = new ArrayList<ColumnMapper<T>>(fields.size());
        for (int i = 0; i < fields.size(); i++) {
            Field field = fields.get(i);
            int pos = position(field);
            mappers.add(factory.createColumnMapper(klass, field, pos < 0 ? i : pos, mappingManager));
        }
        return mappers;
    }

    private static void validateOrder(List<Field> fields, String annotation) {
        for (int i = 0; i < fields.size(); i++) {
            Field field = fields.get(i);
            int pos = position(field);
            if (pos != i)
                throw new IllegalArgumentException(String.format("Invalid ordering value %d for annotation %s of column %s, was expecting %d",
                                                                 pos, annotation, field.getName(), i));
        }
    }

    private static int position(Field field) {
        switch (kind(field)) {
            case PARTITION_KEY:
                return field.getAnnotation(PartitionKey.class).value();
            case CLUSTERING_COLUMN:
                return field.getAnnotation(ClusteringColumn.class).value();
            default:
                return -1;
        }
    }

    public static ColumnMapper.Kind kind(Field field) {
        PartitionKey pk = field.getAnnotation(PartitionKey.class);
        ClusteringColumn cc = field.getAnnotation(ClusteringColumn.class);
        if (pk != null && cc != null)
            throw new IllegalArgumentException("Field " + field.getName() + " cannot have both the @PartitionKey and @ClusteringColumn annotations");

        return pk != null
             ? ColumnMapper.Kind.PARTITION_KEY
             : (cc != null ? ColumnMapper.Kind.CLUSTERING_COLUMN : ColumnMapper.Kind.REGULAR);
    }

    public static EnumType enumType(Field field) {
        Class<?> type = field.getType();
        if (!type.isEnum())
            return null;

        Enumerated enumerated = field.getAnnotation(Enumerated.class);
        return (enumerated == null) ? EnumType.STRING : enumerated.value();
    }

    public static String columnName(Field field) {
        Column column = field.getAnnotation(Column.class);
        if (column != null && !column.name().isEmpty()) {
            return column.caseSensitive() ? column.name() : column.name().toLowerCase();
        }

        com.datastax.driver.mapping.annotations.Field udtField = field.getAnnotation(com.datastax.driver.mapping.annotations.Field.class);
        if (udtField != null && !udtField.name().isEmpty()) {
            return udtField.caseSensitive() ? udtField.name() : udtField.name().toLowerCase();
        }

        return field.getName().toLowerCase();
    }

    public static <T> AccessorMapper<T> parseAccessor(Class<T> accClass, AccessorMapper.Factory factory, MappingManager mappingManager) {
        if (!accClass.isInterface())
            throw new IllegalArgumentException("@Accessor annotation is only allowed on interfaces");

        AnnotationChecks.getTypeAnnotation(Accessor.class, accClass);

        List<MethodMapper> methods = new ArrayList<MethodMapper>();
        for (Method m : accClass.getDeclaredMethods()) {
            Query query = m.getAnnotation(Query.class);
            if (query == null)
                continue;

            String queryString = query.value();

            Annotation[][] paramAnnotations = m.getParameterAnnotations();
            Type[] paramTypes = m.getGenericParameterTypes();
            ParamMapper[] paramMappers = new ParamMapper[paramAnnotations.length];
            Boolean hasParamAnnotation = null;
            for (int i = 0; i < paramMappers.length; i++) {
                String paramName = null;
                for (Annotation a : paramAnnotations[i]) {
                    if (a.annotationType().equals(Param.class)) {
                        paramName = ((Param) a).value();
                        break;
                    }
                }
                if (hasParamAnnotation == null)
                    hasParamAnnotation = (paramName != null);
                if (hasParamAnnotation != (paramName != null))
                    throw new IllegalArgumentException(String.format("For method '%s', either all or none of the paramaters of a method must have a @Param annotation", m.getName()));

                paramMappers[i] = newParamMapper(accClass.getName(), m.getName(), i, paramName, paramTypes[i], paramAnnotations[i], mappingManager);
            }

            ConsistencyLevel cl = null;
            int fetchSize = -1;
            boolean tracing = false;

            QueryParameters options = m.getAnnotation(QueryParameters.class);
            if (options != null) {
                cl = options.consistency().isEmpty() ? null : ConsistencyLevel.valueOf(options.consistency().toUpperCase());
                fetchSize = options.fetchSize();
                tracing = options.tracing();
            }

            methods.add(new MethodMapper(m, queryString, paramMappers, cl, fetchSize, tracing));
        }

        return factory.create(accClass, methods);
    }

    @SuppressWarnings({ "unchecked", "rawtypes" })
    private static ParamMapper newParamMapper(String className, String methodName, int idx, String paramName, Type paramType, Annotation[] paramAnnotations, MappingManager mappingManager) {
        if (paramType instanceof Class) {
            Class<?> paramClass = (Class<?>) paramType;
            if (paramClass.isAnnotationPresent(UDT.class)) {
                UDTMapper<?> udtMapper = mappingManager.getUDTMapper(paramClass);
                return new UDTParamMapper(paramName, idx, udtMapper);
            } else if (paramClass.isEnum()) {
                EnumType enumType = EnumType.STRING;
                for (Annotation annotation : paramAnnotations) {
                    if (annotation instanceof Enumerated) {
                        enumType = ((Enumerated) annotation).value();
                    }
                }
                return new EnumParamMapper(paramName, idx, enumType);
            }
            return new ParamMapper(paramName, idx);
        } if (paramType instanceof ParameterizedType) {
            InferredCQLType inferredCQLType = InferredCQLType.from(className, methodName, idx, paramName, paramType, mappingManager);
            if (inferredCQLType.containsMappedUDT) {
                // We need a specialized mapper to convert UDT instances in the hierarchy.
                return new NestedUDTParamMapper(paramName, idx, inferredCQLType);
            } else {
                // Use the default mapper but provide the extracted type
                return new ParamMapper(paramName, idx, inferredCQLType.dataType);
            }
        } else {
            throw new IllegalArgumentException(String.format("Cannot map class %s for parameter %s of %s.%s", paramType, paramName, className, methodName));
        }
    }
}


File: driver-mapping/src/main/java/com/datastax/driver/mapping/EntityMapper.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.mapping;

import java.lang.reflect.Field;
import java.util.*;

import com.datastax.driver.core.ConsistencyLevel;
import static com.datastax.driver.core.querybuilder.QueryBuilder.quote;

abstract class EntityMapper<T> {

    public final Class<T> entityClass;
    private final String keyspace;
    private final String table;

    public final ConsistencyLevel writeConsistency;
    public final ConsistencyLevel readConsistency;

    public final List<ColumnMapper<T>> partitionKeys = new ArrayList<ColumnMapper<T>>();
    public final List<ColumnMapper<T>> clusteringColumns = new ArrayList<ColumnMapper<T>>();
    public final List<ColumnMapper<T>> regularColumns = new ArrayList<ColumnMapper<T>>();

    private final List<ColumnMapper<T>> allColumns = new ArrayList<ColumnMapper<T>>();

    protected EntityMapper(Class<T> entityClass, String keyspace, String table, ConsistencyLevel writeConsistency, ConsistencyLevel readConsistency) {
        this.entityClass = entityClass;
        this.keyspace = keyspace;
        this.table = table;
        this.writeConsistency = writeConsistency;
        this.readConsistency = readConsistency;
    }

    public String getKeyspace() {
        return quote(keyspace);
    }

    public String getTable() {
        return quote(table);
    }

    public int primaryKeySize() {
        return partitionKeys.size() + clusteringColumns.size();
    }

    public ColumnMapper<T> getPrimaryKeyColumn(int i) {
        return i < partitionKeys.size() ? partitionKeys.get(i) : clusteringColumns.get(i - partitionKeys.size());
    }

    public void addColumns(List<ColumnMapper<T>> pks, List<ColumnMapper<T>> ccs, List<ColumnMapper<T>> rgs) {
        partitionKeys.addAll(pks);
        allColumns.addAll(pks);

        clusteringColumns.addAll(ccs);
        allColumns.addAll(ccs);

        addColumns(rgs);
    }

    public void addColumns(List<ColumnMapper<T>> rgs) {
        regularColumns.addAll(rgs);
        allColumns.addAll(rgs);
    }

    public abstract T newEntity();

    public List<ColumnMapper<T>> allColumns() {
        return allColumns;
    }

    interface Factory {
        public <T> EntityMapper<T> create(Class<T> entityClass, String keyspace, String table, ConsistencyLevel writeConsistency, ConsistencyLevel readConsistency);
        public <T> ColumnMapper<T> createColumnMapper(Class<T> componentClass, Field field, int position, MappingManager mappingManager);
    }
}


File: driver-mapping/src/main/java/com/datastax/driver/mapping/Mapper.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.mapping;

import java.util.*;

import com.google.common.base.Function;
import com.google.common.base.Functions;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.datastax.driver.core.*;

/**
 * An object handling the mapping of a particular class.
 * <p/>
 * A {@code Mapper} object is obtained from a {@code MappingManager} using the
 * {@link MappingManager#mapper} method.
 */
public class Mapper<T> {

    private static final Logger logger = LoggerFactory.getLogger(EntityMapper.class);

    final MappingManager manager;
    final ProtocolVersion protocolVersion;
    final Class<T> klass;
    final EntityMapper<T> mapper;
    final TableMetadata tableMetadata;

    // Cache prepared statements for each type of query we use.
    private volatile Map<String, PreparedStatement> preparedQueries = Collections.<String, PreparedStatement>emptyMap();

    private static final Function<Object, Void> NOOP = Functions.<Void>constant(null);

    private volatile Option[] defaultSaveOptions;
    private volatile Option[] defaultDeleteOptions;

    final Function<ResultSet, T> mapOneFunction;
    final Function<ResultSet, Result<T>> mapAllFunction;

    Mapper(MappingManager manager, Class<T> klass, EntityMapper<T> mapper) {
        this.manager = manager;
        this.klass = klass;
        this.mapper = mapper;

        KeyspaceMetadata keyspace = session().getCluster().getMetadata().getKeyspace(mapper.getKeyspace());
        this.tableMetadata = keyspace == null ? null : keyspace.getTable(Metadata.quote(mapper.getTable()));

        this.protocolVersion = manager.getSession().getCluster().getConfiguration().getProtocolOptions().getProtocolVersionEnum();
        this.mapOneFunction = new Function<ResultSet, T>() {
            public T apply(ResultSet rs) {
                return Mapper.this.map(rs).one();
            }
        };
        this.mapAllFunction = new Function<ResultSet, Result<T>>() {
            public Result<T> apply(ResultSet rs) {
                return Mapper.this.map(rs);
            }
        };
    }

    Session session() {
        return manager.getSession();
    }

    PreparedStatement getPreparedQuery(QueryType type, Option... options) {
        String queryString;
        queryString = type.makePreparedQueryString(tableMetadata, mapper, options);
        PreparedStatement stmt = preparedQueries.get(queryString);
        if (stmt == null) {
            synchronized (preparedQueries) {
                stmt = preparedQueries.get(queryString);
                if (stmt == null) {
                    logger.debug("Preparing query {}", queryString);
                    stmt = session().prepare(queryString);
                    Map<String, PreparedStatement> newQueries = new HashMap<String, PreparedStatement>(preparedQueries);
                    newQueries.put(queryString, stmt);
                    preparedQueries = newQueries;
                }
            }
        }
        return stmt;
    }

    /**
     * The {@code TableMetadata} for this mapper.
     *
     * @return the {@code TableMetadata} for this mapper or {@code null} if keyspace is not set.
     */
    public TableMetadata getTableMetadata() {
        return tableMetadata;
    }

    /**
     * The {@code MappingManager} managing this mapper.
     *
     * @return the {@code MappingManager} managing this mapper.
     */
    public MappingManager getManager() {
        return manager;
    }

    /**
     * Creates a query that can be used to save the provided entity.
     * <p/>
     * This method is useful if you want to setup a number of options (tracing,
     * conistency level, ...) of the returned statement before executing it manually
     * or need access to the {@code ResultSet} object after execution (to get the
     * trace, the execution info, ...), but in other cases, calling {@link #save}
     * or {@link #saveAsync} is shorter.
     *
     * @param entity the entity to save.
     * @return a query that saves {@code entity} (based on it's defined mapping).
     */
    public Statement saveQuery(T entity) {
        PreparedStatement ps;
        if (this.defaultSaveOptions != null)
            ps = getPreparedQuery(QueryType.SAVE, this.defaultSaveOptions);
        else
            ps = getPreparedQuery(QueryType.SAVE);

        BoundStatement bs = ps.bind();
        int i = 0;
        for (ColumnMapper<T> cm : mapper.allColumns()) {
            Object value = cm.getValue(entity);
            bs.setBytesUnsafe(i++, value == null ? null : cm.getDataType().serialize(value, protocolVersion));
        }

        if (mapper.writeConsistency != null)
            bs.setConsistencyLevel(mapper.writeConsistency);
        return bs;
    }

    /**
     * Creates a query that can be used to save the provided entity.
     * <p/>
     * This method is useful if you want to setup a number of options (tracing,
     * conistency level, ...) of the returned statement before executing it manually
     * or need access to the {@code ResultSet} object after execution (to get the
     * trace, the execution info, ...), but in other cases, calling {@link #save}
     * or {@link #saveAsync} is shorter.
     *
     * @param entity the entity to save.
     * @return a query that saves {@code entity} (based on it's defined mapping).
     */
    public Statement saveQuery(T entity, Option... options) {
        PreparedStatement ps = getPreparedQuery(QueryType.SAVE, options);

        BoundStatement bs = ps.bind();
        int i = 0;
        for (ColumnMapper<T> cm : mapper.allColumns()) {
            Object value = cm.getValue(entity);
            bs.setBytesUnsafe(i++, value == null ? null : cm.getDataType().serialize(value, protocolVersion));
        }

        if (options != null) {
            for (Option opt : options) {
                if (opt instanceof Option.Ttl) {
                    Option.Ttl ttlOption = (Option.Ttl)opt;
                    bs.setInt(i++, ttlOption.getValue());
                }
                if (opt instanceof Option.Timestamp) {
                    Option.Timestamp tsOption = (Option.Timestamp)opt;
                    bs.setLong(i++, tsOption.getValue());
                }
            }
        }
        if (mapper.writeConsistency != null)
            bs.setConsistencyLevel(mapper.writeConsistency);
        return bs;
    }

    /**
     * Save an entity mapped by this mapper.
     * <p/>
     * This method is basically equivalent to: {@code getManager().getSession().execute(saveQuery(entity))}.
     *
     * @param entity the entity to save.
     */
    public void save(T entity) {
        session().execute(saveQuery(entity));
    }

    /**
     * Save an entity mapped by this mapper and using special options for save.
     * <p/>
     *
     * @param entity  the entity to save.
     * @param options the options object specified defining special options when saving.
     */
    public void save(T entity, Option... options) {
        session().execute(saveQuery(entity, options));
    }

    /**
     * Save an entity mapped by this mapper asynchonously.
     * <p/>
     * This method is basically equivalent to: {@code getManager().getSession().executeAsync(saveQuery(entity))}.
     *
     * @param entity the entity to save.
     * @return a future on the completion of the save operation.
     */
    public ListenableFuture<Void> saveAsync(T entity) {
        return Futures.transform(session().executeAsync(saveQuery(entity)), NOOP);
    }

    /**
     * Save an entity mapped by this mapper asynchonously and using special options for save.
     * <p/>
     *
     * @param entity the entity to save.
     * @return a future on the completion of the save operation.
     */
    public ListenableFuture<Void> saveAsync(T entity, Option... options) {
        return Futures.transform(session().executeAsync(saveQuery(entity, options)), NOOP);
    }

    /**
     * Creates a query that can be used to delete the provided entity.
     * <p/>
     * This method is a shortcut that extract the PRIMARY KEY from the
     * provided entity and call {@link #deleteQuery(Object...)} with it.
     * This method allows you to provide a suite of {@link Option} to include in
     * the DELETE query. Note : currently, only {@link com.datastax.driver.mapping.Mapper.Option.Timestamp}
     * is supported for DELETE queries.
     * <p/>
     * This method is useful if you want to setup a number of options (tracing,
     * conistency level, ...) of the returned statement before executing it manually
     * or need access to the {@code ResultSet} object after execution (to get the
     * trace, the execution info, ...), but in other cases, calling {@link #delete}
     * or {@link #deleteAsync} is shorter.
     *
     * @param entity  the entity to delete.
     * @param options the options to add to the DELETE query.
     * @return a query that delete {@code entity} (based on it's defined mapping) with
     * provided USING options.
     */
    public Statement deleteQuery(T entity, Option... options) {
        Object[] pks = new Object[mapper.primaryKeySize()];
        for (int i = 0; i < pks.length; i++)
            pks[i] = mapper.getPrimaryKeyColumn(i).getValue(entity);

        return deleteQuery(pks, Arrays.asList(options));
    }

    /**
     * Creates a query that can be used to delete the provided entity.
     * <p/>
     * This method is a shortcut that extract the PRIMARY KEY from the
     * provided entity and call {@link #deleteQuery(Object...)} with it.
     * <p/>
     * This method is useful if you want to setup a number of options (tracing,
     * conistency level, ...) of the returned statement before executing it manually
     * or need access to the {@code ResultSet} object after execution (to get the
     * trace, the execution info, ...), but in other cases, calling {@link #delete}
     * or {@link #deleteAsync} is shorter.
     *
     * @param entity the entity to delete.
     * @return a query that delete {@code entity} (based on it's defined mapping).
     */
    public Statement deleteQuery(T entity) {
        Object[] pks = new Object[mapper.primaryKeySize()];
        for (int i = 0; i < pks.length; i++)
            pks[i] = mapper.getPrimaryKeyColumn(i).getValue(entity);

        return deleteQuery(pks);
    }

    /**
     * Creates a query that can be used to delete an entity given its PRIMARY KEY.
     * <p/>
     * The values provided must correspond to the columns composing the PRIMARY
     * KEY (in the order of said primary key). The values can also contain, after
     * specifying the primary keys columns, a suite of {@link Option} to include in
     * the DELETE query. Note : currently, only {@link com.datastax.driver.mapping.Mapper.Option.Timestamp}
     * is supported for DELETE queries.
     * <p/>
     * <p/>
     * This method is useful if you want to setup a number of options (tracing,
     * conistency level, ...) of the returned statement before executing it manually
     * or need access to the {@code ResultSet} object after execution (to get the
     * trace, the execution info, ...), but in other cases, calling {@link #delete}
     * or {@link #deleteAsync} is shorter.
     * <p/>
     *
     * @param args the primary key of the entity to delete, or more precisely
     *             the values for the columns of said primary key in the order of the primary key.
     *             Can be followed by {@link Option} to include in the DELETE
     *             query.
     * @return a query that delete the entity of PRIMARY KEY {@code primaryKey}.
     * @throws IllegalArgumentException if the number of value provided differ from
     *                                  the number of columns composing the PRIMARY KEY of the mapped class, or if
     *                                  at least one of those values is {@code null}.
     */
    public Statement deleteQuery(Object... args) {
        List<Object> pks = new ArrayList<Object>();
        List<Option> options = new ArrayList<Option>();
        for (Object o : args) {
            if (o instanceof Option) {
                options.add((Option)o);
            } else {
                pks.add(o);
            }
        }
        return deleteQuery(pks.toArray(), options);
    }

    private Statement deleteQuery(Object[] primaryKey, List<Option> options) {
        if (primaryKey.length != mapper.primaryKeySize())
            throw new IllegalArgumentException(String.format("Invalid number of PRIMARY KEY columns provided, %d expected but got %d", mapper.primaryKeySize(), primaryKey.length));

        PreparedStatement ps;
        if (options.size() != 0){
            ps = getPreparedQuery(QueryType.DEL, options.toArray(new Option[options.size()]));
        }
        else {
            ps = getPreparedQuery(QueryType.DEL, this.defaultDeleteOptions);
        }

        BoundStatement bs = ps.bind();
        int i;
        for (i = 0; i < primaryKey.length; i++) {
            ColumnMapper<T> column = mapper.getPrimaryKeyColumn(i);
            Object value = primaryKey[i];
            if (value == null)
                throw new IllegalArgumentException(String.format("Invalid null value for PRIMARY KEY column %s (argument %d)", column.getColumnName(), i));
            bs.setBytesUnsafe(i, column.getDataType().serialize(value, protocolVersion));
        }

        for (Option opt : options) {
            if (opt instanceof Option.Ttl) {
                Option.Ttl ttlOption = (Option.Ttl)opt;
                bs.setInt(i++, ttlOption.getValue());
            }
        }

        if (mapper.writeConsistency != null)
            bs.setConsistencyLevel(mapper.writeConsistency);
        return bs;
    }

    /**
     * Deletes an entity mapped by this mapper.
     * <p/>
     * This method is basically equivalent to: {@code getManager().getSession().execute(deleteQuery(entity))}.
     *
     * @param entity the entity to delete.
     */
    public void delete(T entity) {
        session().execute(deleteQuery(entity));
    }

    /**
     * Deletes an entity mapped by this mapper.
     * <p/>
     * This method is basically equivalent to: {@code getManager().getSession().execute(deleteQuery(entity, options))}.
     *
     * @param entity the entity to delete.
     */
    public void delete(T entity, Option... options) {
        session().execute(deleteQuery(entity, options));
    }

    /**
     * Deletes an entity mapped by this mapper asynchronously.
     * <p/>
     * This method is basically equivalent to: {@code getManager().getSession().executeAsync(deleteQuery(entity))}.
     *
     * @param entity the entity to delete.
     * @return a future on the completion of the deletion.
     */
    public ListenableFuture<Void> deleteAsync(T entity) {
        return Futures.transform(session().executeAsync(deleteQuery(entity)), NOOP);
    }

    /**
     * Deletes an entity mapped by this mapper asynchronously.
     * <p/>
     * This method is basically equivalent to: {@code getManager().getSession().executeAsync(deleteQuery(entity, options))}.
     *
     * @param entity the entity to delete.
     * @return a future on the completion of the deletion.
     */
    public ListenableFuture<Void> deleteAsync(T entity, Option... options) {
        return Futures.transform(session().executeAsync(deleteQuery(entity, options)), NOOP);
    }

    /**
     * Deletes an entity based on its primary key.
     * <p/>
     * This method is basically equivalent to: {@code getManager().getSession().execute(deleteQuery(objects))}.
     *
     * @param objects the primary key of the entity to delete, or more precisely
     *                the values for the columns of said primary key in the order
     *                of the primary key.Can be followed by {@link Option} to include
     *                in the DELETE query.
     * @throws IllegalArgumentException if the number of value provided differ from
     *                                  the number of columns composing the PRIMARY KEY of the mapped class, or if
     *                                  at least one of those values is {@code null}.
     */
    public void delete(Object... objects) {
        session().execute(deleteQuery(objects));
    }

    /**
     * Deletes an entity based on its primary key asynchronously.
     * <p/>
     * This method is basically equivalent to: {@code getManager().getSession().executeAsync(deleteQuery(objects))}.
     *
     * @param objects the primary key of the entity to delete, or more precisely
     *                the values for the columns of said primary key in the order
     *                of the primary key.Can be followed by {@link Option} to include
     *                in the DELETE query.
     * @throws IllegalArgumentException if the number of value provided differ from
     *                                  the number of columns composing the PRIMARY KEY of the mapped class, or if
     *                                  at least one of those values is {@code null}.
     */
    public ListenableFuture<Void> deleteAsync(Object... objects) {
        return Futures.transform(session().executeAsync(deleteQuery(objects)), NOOP);
    }

    /**
     * Map the rows from a {@code ResultSet} into the class this is mapper of.
     *
     * @param resultSet the {@code ResultSet} to map.
     * @return the mapped result set. Note that the returned mapped result set
     * will encapsulate {@code resultSet} and so consuming results from this
     * returned mapped result set will consume results from {@code resultSet}
     * and vice-versa.
     */
    public Result<T> map(ResultSet resultSet) {
        return new Result<T>(resultSet, mapper, protocolVersion);
    }

    /**
     * Creates a query to fetch entity given its PRIMARY KEY.
     * <p/>
     * The values provided must correspond to the columns composing the PRIMARY
     * KEY (in the order of said primary key).
     * <p/>
     * This method is useful if you want to setup a number of options (tracing,
     * conistency level, ...) of the returned statement before executing it manually,
     * but in other cases, calling {@link #get} or {@link #getAsync} is shorter.
     *
     * @param primaryKey the primary key of the entity to fetch, or more precisely
     *                   the values for the columns of said primary key in the order of the primary key.
     * @return a query that fetch the entity of PRIMARY KEY {@code primaryKey}.
     * @throws IllegalArgumentException if the number of value provided differ from
     *                                  the number of columns composing the PRIMARY KEY of the mapped class, or if
     *                                  at least one of those values is {@code null}.
     */
    public Statement getQuery(Object... primaryKey) {
        if (primaryKey.length != mapper.primaryKeySize())
            throw new IllegalArgumentException(String.format("Invalid number of PRIMARY KEY columns provided, %d expected but got %d", mapper.primaryKeySize(), primaryKey.length));

        PreparedStatement ps = getPreparedQuery(QueryType.GET);

        BoundStatement bs = ps.bind();
        for (int i = 0; i < primaryKey.length; i++) {
            ColumnMapper<T> column = mapper.getPrimaryKeyColumn(i);
            Object value = primaryKey[i];
            if (value == null)
                throw new IllegalArgumentException(String.format("Invalid null value for PRIMARY KEY column %s (argument %d)", column.getColumnName(), i));
            bs.setBytesUnsafe(i, column.getDataType().serialize(value, protocolVersion));
        }

        if (mapper.readConsistency != null)
            bs.setConsistencyLevel(mapper.readConsistency);
        return bs;
    }

    /**
     * Fetch an entity based on its primary key.
     * <p/>
     * This method is basically equivalent to: {@code map(getManager().getSession().execute(getQuery(primaryKey))).one()}.
     *
     * @param primaryKey the primary key of the entity to fetch, or more precisely
     *                   the values for the columns of said primary key in the order of the primary key.
     * @return the entity fetched or {@code null} if it doesn't exist.
     * @throws IllegalArgumentException if the number of value provided differ from
     *                                  the number of columns composing the PRIMARY KEY of the mapped class, or if
     *                                  at least one of those values is {@code null}.
     */
    public T get(Object... primaryKey) {
        return map(session().execute(getQuery(primaryKey))).one();
    }

    /**
     * Fetch an entity based on its primary key asynchronously.
     * <p/>
     * This method is basically equivalent to mapping the result of: {@code getManager().getSession().executeAsync(getQuery(primaryKey))}.
     *
     * @param primaryKey the primary key of the entity to fetch, or more precisely
     *                   the values for the columns of said primary key in the order of the primary key.
     * @return a future on the fetched entity. The return future will yield
     * {@code null} if said entity doesn't exist.
     * @throws IllegalArgumentException if the number of value provided differ from
     *                                  the number of columns composing the PRIMARY KEY of the mapped class, or if
     *                                  at least one of those values is {@code null}.
     */
    public ListenableFuture<T> getAsync(Object... primaryKey) {
        return Futures.transform(session().executeAsync(getQuery(primaryKey)), mapOneFunction);
    }

    /**
     * Set the default save {@link Option} for this object mapper, that will be used
     * in all save operations. Refer to {@link Mapper#save)} with Option argument
     * to check available save options.
     *
     * @param options the options to set. To reset, use {@link Mapper#resetDefaultSaveOptions}
     *                instead of putting null argument here.
     */
    public void setDefaultSaveOptions(Option... options) {
        this.defaultSaveOptions = Arrays.copyOf(options, options.length);
    }

    /**
     * Reset the default save options for this object mapper.
     */
    public void resetDefaultSaveOptions() {
        this.defaultSaveOptions = null;
    }

    /**
     * Set the default delete {@link Option} for this object mapper, that will be used
     * in all delete operations. Refer to {@link Mapper#delete)} with Option argument
     * to check available delete options.
     *
     * @param options the options to set. To reset, use {@link Mapper#resetDefaultDeleteOptions}
     *                instead of putting null argument here.
     */
    public void setDefaultDeleteOptions(Option... options) {
        this.defaultDeleteOptions = Arrays.copyOf(options, options.length);
    }

    /**
     * Reset the default delete options for this object mapper.
     */
    public void resetDefaultDeleteOptions() {
        this.defaultDeleteOptions = null;
    }

    /**
     * An object to allow defining specific options during a
     * {@link Mapper#save(Object)} or {@link Mapper#delete(Object...)} operation.
     * <p/>
     * The options will be added as : 'INSERT [...] USING option-name option-value [AND option-name option value... ].
     */
    public static abstract class Option {

        static class Ttl extends Option {

            private int ttlValue;

            Ttl(int value) {
                this.ttlValue = value;
            }

            /**
             * Get the TTL value configured in the object.
             *
             * @return the TTL value.
             */
            public int getValue() {
                return this.ttlValue;
            }
        }

        static class Timestamp extends Option {

            private long tsValue;

            Timestamp(long value) {
                this.tsValue = value;
            }

            /**
             * Get the TIMESTAMP value configured in the object.
             *
             * @return the TIMESTAMP value.
             */
            public long getValue() {
                return this.tsValue;
            }
        }

        /**
         * Creates a new SaveOptions object for adding a TTL value in a save
         * or delete operation.
         *
         * @param value the value to use for the operation.
         * @return the SaveOptions object configured to set a TTL value to a
         * save or delete operation.
         */
        public static Option ttl(int value) {
            return new Ttl(value);
        }

        /**
         * Creates a new SaveOptions object for adding a TIMESTAMP value in a save
         * or delete operation.
         *
         * @param value the value to use for the operation.
         * @return the SaveOptions object configured to set a TIMESTAMP value to a
         * save or delete operation.
         */
        public static Option timestamp(long value) {
            return new Timestamp(value);
        }
    }

}


File: driver-mapping/src/main/java/com/datastax/driver/mapping/QueryType.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.mapping;

import java.util.ArrayList;
import java.util.List;

import com.google.common.base.Objects;

import com.datastax.driver.core.TableMetadata;
import com.datastax.driver.core.querybuilder.Delete;
import com.datastax.driver.core.querybuilder.Insert;
import com.datastax.driver.core.querybuilder.Select;

import static com.datastax.driver.core.querybuilder.QueryBuilder.*;

class QueryType {

    private enum Kind {SAVE, GET, DEL, SLICE, REVERSED_SLICE}

    ;
    private final Kind kind;

    // For slices
    private final int startBoundSize;
    private final boolean startInclusive;
    private final int endBoundSize;
    private final boolean endInclusive;

    public static final QueryType SAVE = new QueryType(Kind.SAVE);
    public static final QueryType DEL = new QueryType(Kind.DEL);
    public static final QueryType GET = new QueryType(Kind.GET);

    private QueryType(Kind kind) {
        this(kind, 0, false, 0, false);
    }

    private QueryType(Kind kind, int startBoundSize, boolean startInclusive, int endBoundSize, boolean endInclusive) {
        this.kind = kind;
        this.startBoundSize = startBoundSize;
        this.startInclusive = startInclusive;
        this.endBoundSize = endBoundSize;
        this.endInclusive = endInclusive;
    }

    public static QueryType slice(int startBoundSize, boolean startInclusive, int endBoundSize, boolean endInclusive, boolean reversed) {
        return new QueryType(reversed ? Kind.REVERSED_SLICE : Kind.SLICE, startBoundSize, startInclusive, endBoundSize, endInclusive);
    }

    String makePreparedQueryString(TableMetadata table, EntityMapper<?> mapper, Mapper.Option... options) {
        switch (kind) {
            case SAVE: {
                Insert insert = table == null
                    ? insertInto(mapper.getKeyspace(), mapper.getTable())
                    : insertInto(table);
                for (ColumnMapper<?> cm : mapper.allColumns())
                    insert.value(cm.getColumnName(), bindMarker());
                if (options != null) {
                    Insert.Options usings = insert.using();
                    for (Mapper.Option opt : options) {
                        if (opt instanceof Mapper.Option.Ttl)
                            // Use Bind Marker here so we don't re-prepare statements for different options values
                            usings.and(ttl(bindMarker()));
                        else
                            usings.and(timestamp(bindMarker()));
                    }
                }
                return insert.toString();
            }
            case GET: {
                Select select = table == null
                    ? select().all().from(mapper.getKeyspace(), mapper.getTable())
                    : select().all().from(table);
                Select.Where where = select.where();
                for (int i = 0; i < mapper.primaryKeySize(); i++)
                    where.and(eq(mapper.getPrimaryKeyColumn(i).getColumnName(), bindMarker()));
                return select.toString();
            }
            case DEL: {
                Delete delete = table == null
                    ? delete().all().from(mapper.getKeyspace(), mapper.getTable())
                    : delete().all().from(table);
                Delete.Where where = delete.where();
                for (int i = 0; i < mapper.primaryKeySize(); i++)
                    where.and(eq(mapper.getPrimaryKeyColumn(i).getColumnName(), bindMarker()));
                Delete.Options usings = delete.using();
                if (options != null){
                    for (Mapper.Option opt : options) {
                        if (opt instanceof Mapper.Option.Timestamp) {
                            usings.and(timestamp(bindMarker()));
                        } else {
                            throw new UnsupportedOperationException("Cannot use another option than TIMESTAMP for DELETE operations");
                        }
                    }
                }
                return delete.toString();
            }
            case SLICE:
            case REVERSED_SLICE: {
                Select select = table == null
                    ? select().all().from(mapper.getKeyspace(), mapper.getTable())
                    : select().all().from(table);
                Select.Where where = select.where();
                for (int i = 0; i < mapper.partitionKeys.size(); i++)
                    where.and(eq(mapper.partitionKeys.get(i).getColumnName(), bindMarker()));

                if (startBoundSize > 0) {
                    if (startBoundSize == 1) {
                        String name = mapper.clusteringColumns.get(0).getColumnName();
                        where.and(startInclusive ? gte(name, bindMarker()) : gt(name, bindMarker()));
                    } else {
                        List<String> names = new ArrayList<String>(startBoundSize);
                        List<Object> values = new ArrayList<Object>(startBoundSize);
                        for (int i = 0; i < startBoundSize; i++) {
                            names.add(mapper.clusteringColumns.get(i).getColumnName());
                            values.add(bindMarker());
                        }
                        where.and(startInclusive ? gte(names, values) : gt(names, values));
                    }
                }

                if (endBoundSize > 0) {
                    if (endBoundSize == 1) {
                        String name = mapper.clusteringColumns.get(0).getColumnName();
                        where.and(endInclusive ? gte(name, bindMarker()) : gt(name, bindMarker()));
                    } else {
                        List<String> names = new ArrayList<String>(endBoundSize);
                        List<Object> values = new ArrayList<Object>(endBoundSize);
                        for (int i = 0; i < endBoundSize; i++) {
                            names.add(mapper.clusteringColumns.get(i).getColumnName());
                            values.add(bindMarker());
                        }
                        where.and(endInclusive ? lte(names, values) : lt(names, values));
                    }
                }

                select = select.limit(bindMarker());

                if (kind == Kind.REVERSED_SLICE)
                    select = select.orderBy(desc(mapper.clusteringColumns.get(0).getColumnName()));

                return select.toString();
            }
        }
        throw new AssertionError();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null || this.getClass() != obj.getClass())
            return false;

        QueryType that = (QueryType)obj;
        return kind == that.kind
            && startBoundSize == that.startBoundSize
            && startInclusive == that.startInclusive
            && endBoundSize == that.endBoundSize
            && endInclusive == that.endInclusive;
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(kind, startBoundSize, startInclusive, endBoundSize, endInclusive);
    }

}


File: driver-mapping/src/main/java/com/datastax/driver/mapping/ReflectionMapper.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.mapping;

import java.beans.IntrospectionException;
import java.beans.PropertyDescriptor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.HashMap;
import java.util.Map;

import com.datastax.driver.core.ConsistencyLevel;
import com.datastax.driver.core.DataType;
import com.datastax.driver.core.UDTValue;

/**
 * An {@link EntityMapper} implementation that use reflection to read and write fields
 * of an entity.
 */
class ReflectionMapper<T> extends EntityMapper<T> {

    private static ReflectionFactory factory = new ReflectionFactory();

    private ReflectionMapper(Class<T> entityClass, String keyspace, String table, ConsistencyLevel writeConsistency, ConsistencyLevel readConsistency) {
        super(entityClass, keyspace, table, writeConsistency, readConsistency);
    }

    public static Factory factory() {
        return factory;
    }

    @Override
    public T newEntity() {
        try {
            return entityClass.newInstance();
        } catch (Exception e) {
            throw new RuntimeException("Can't create an instance of " + entityClass.getName());
        }
    }

    private static class LiteralMapper<T> extends ColumnMapper<T> {

        private final Method readMethod;
        private final Method writeMethod;

        private LiteralMapper(Field field, int position, PropertyDescriptor pd) {
            this(field, extractSimpleType(field), position, pd);
        }

        private LiteralMapper(Field field, DataType type, int position, PropertyDescriptor pd) {
            super(field, type, position);
            this.readMethod = pd.getReadMethod();
            this.writeMethod = pd.getWriteMethod();
        }

        @Override
        public Object getValue(T entity) {
            try {
                return readMethod.invoke(entity);
            } catch (IllegalArgumentException e) {
                throw new IllegalArgumentException("Could not get field '" + fieldName + "'");
            } catch (Exception e) {
                throw new IllegalStateException("Unable to access getter for '" + fieldName + "' in " + entity.getClass().getName(), e);
            }
        }

        @Override
        public void setValue(Object entity, Object value) {
            try {
                writeMethod.invoke(entity, value);
            } catch (IllegalArgumentException e) {
                throw new IllegalArgumentException("Could not set field '" + fieldName + "' to value '" + value + "'");
            } catch (Exception e) {
                throw new IllegalStateException("Unable to access setter for '" + fieldName + "' in " + entity.getClass().getName(), e);
            }
        }
    }

    private static class EnumMapper<T> extends LiteralMapper<T> {

        private final EnumType enumType;
        private final Map<String, Object> fromString;

        private EnumMapper(Field field, int position, PropertyDescriptor pd, EnumType enumType) {
            super(field, enumType == EnumType.STRING ? DataType.text() : DataType.cint(), position, pd);
            this.enumType = enumType;

            if (enumType == EnumType.STRING) {
                fromString = new HashMap<String, Object>(javaType.getEnumConstants().length);
                for (Object constant : javaType.getEnumConstants())
                    fromString.put(constant.toString().toLowerCase(), constant);

            } else {
                fromString = null;
            }
        }

        @SuppressWarnings("rawtypes")
        @Override
        public Object getValue(T entity) {
            Object value = super.getValue(entity);
            switch (enumType) {
                case STRING:
                    return (value == null) ? null : value.toString();
                case ORDINAL:
                    return (value == null) ? null : ((Enum)value).ordinal();
            }
            throw new AssertionError();
        }

        @Override
        public void setValue(Object entity, Object value) {
            Object converted = null;
            switch (enumType) {
                case STRING:
                    converted = fromString.get(value.toString().toLowerCase());
                    break;
                case ORDINAL:
                    converted = javaType.getEnumConstants()[(Integer)value];
                    break;
            }
            super.setValue(entity, converted);
        }
    }

    private static class UDTColumnMapper<T, U> extends LiteralMapper<T> {
        private final UDTMapper<U> udtMapper;

        private UDTColumnMapper(Field field, int position, PropertyDescriptor pd, UDTMapper<U> udtMapper) {
            super(field, udtMapper.getUserType(), position, pd);
            this.udtMapper = udtMapper;
        }

        @Override
        public Object getValue(T entity) {
            @SuppressWarnings("unchecked")
            U udtEntity = (U)super.getValue(entity);
            return udtEntity == null ? null : udtMapper.toUDT(udtEntity);
        }

        @Override
        public void setValue(Object entity, Object value) {
            assert value instanceof UDTValue;
            UDTValue udtValue = (UDTValue)value;
            assert udtValue.getType().equals(udtMapper.getUserType());

            super.setValue(entity, udtMapper.toEntity((udtValue)));
        }
    }

    private static class NestedUDTMapper<T> extends LiteralMapper<T> {
        private final InferredCQLType inferredCQLType;

        public NestedUDTMapper(Field field, int position, PropertyDescriptor pd, InferredCQLType inferredCQLType) {
            super(field, inferredCQLType.dataType, position, pd);
            this.inferredCQLType = inferredCQLType;
        }

        @Override
        @SuppressWarnings("unchecked")
        public Object getValue(T entity) {
            Object valueWithEntities = super.getValue(entity);
            return (T)UDTMapper.convertEntitiesToUDTs(valueWithEntities, inferredCQLType);
        }

        @Override
        public void setValue(Object entity, Object valueWithUDTValues) {
            super.setValue(entity, UDTMapper.convertUDTsToEntities(valueWithUDTValues, inferredCQLType));
        }
    }

    static DataType extractSimpleType(Field f) {
        Type type = f.getGenericType();

        assert !(type instanceof ParameterizedType);

        if (!(type instanceof Class))
            throw new IllegalArgumentException(String.format("Cannot map class %s for field %s", type, f.getName()));

        return TypeMappings.getSimpleType((Class<?>)type, f.getName());
    }

    private static class ReflectionFactory implements Factory {

        public <T> EntityMapper<T> create(Class<T> entityClass, String keyspace, String table, ConsistencyLevel writeConsistency, ConsistencyLevel readConsistency) {
            return new ReflectionMapper<T>(entityClass, keyspace, table, writeConsistency, readConsistency);
        }

        @SuppressWarnings({ "unchecked", "rawtypes" })
        public <T> ColumnMapper<T> createColumnMapper(Class<T> entityClass, Field field, int position, MappingManager mappingManager) {
            String fieldName = field.getName();
            try {
                PropertyDescriptor pd = new PropertyDescriptor(fieldName, field.getDeclaringClass());

                if (field.getType().isEnum()) {
                    return new EnumMapper<T>(field, position, pd, AnnotationParser.enumType(field));
                }

                if (TypeMappings.isMappedUDT(field.getType())) {
                    UDTMapper<?> udtMapper = mappingManager.getUDTMapper(field.getType());
                    return (ColumnMapper<T>)new UDTColumnMapper(field, position, pd, udtMapper);
                }

                if (field.getGenericType() instanceof ParameterizedType) {
                    InferredCQLType inferredCQLType = InferredCQLType.from(field, mappingManager);
                    if (inferredCQLType.containsMappedUDT) {
                        // We need a specialized mapper to convert UDT instances in the hierarchy.
                        return (ColumnMapper<T>)new NestedUDTMapper(field, position, pd, inferredCQLType);
                    } else {
                        // The default codecs will know how to handle the extracted datatype.
                        return new LiteralMapper<T>(field, inferredCQLType.dataType, position, pd);
                    }
                }

                return new LiteralMapper<T>(field, position, pd);

            } catch (IntrospectionException e) {
                throw new IllegalArgumentException("Cannot find matching getter and setter for field '" + fieldName + "'");
            }
        }
    }
}


File: driver-mapping/src/main/java/com/datastax/driver/mapping/annotations/Table.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.mapping.annotations;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

import com.datastax.driver.mapping.Mapper;

/**
 * Defines to which table a class must be mapped to.
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
public @interface Table {
    /**
     * The name of the keyspace the table is part of.
     *
     * @return the name of the keyspace.
     */
    String keyspace() default "";
    /**
     * The name of the table.
     *
     * @return the name of the table.
     */
    String name();

    /**
     * Whether the keyspace name is a case sensitive one.
     *
     * @return whether the keyspace name is a case sensitive one.
     */
    boolean caseSensitiveKeyspace() default false;
    /**
     * Whether the table name is a case sensitive one.
     *
     * @return whether the table name is a case sensitive one.
     */
    boolean caseSensitiveTable() default false;

    /**
     * The consistency level to use for the write operations provded by the {@link Mapper} class.
     *
     * @return the consistency level to use for the write operations provded by the {@link Mapper} class.
     */
    String writeConsistency() default "";

    /**
     * The consistency level to use for the read operations provded by the {@link Mapper} class.
     *
     * @return the consistency level to use for the read operations provded by the {@link Mapper} class.
     */
    String readConsistency() default "";
}


File: driver-mapping/src/main/java/com/datastax/driver/mapping/annotations/UDT.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.mapping.annotations;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Defines to which User Defined Type a class must be mapped to.
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
public @interface UDT {
    /**
     * The name of the keyspace the type is part of.
     *
     * @return the name of the keyspace.
     */
    String keyspace() default "";
    /**
     * The name of the type.
     *
     * @return the name of the type.
     */
    String name();

    /**
     * Whether the keyspace name is a case sensitive one.
     *
     * @return whether the keyspace name is a case sensitive one.
     */
    boolean caseSensitiveKeyspace() default false;
    /**
     * Whether the type name is a case sensitive one.
     *
     * @return whether the type name is a case sensitive one.
     */
    boolean caseSensitiveType() default false;
}


File: driver-mapping/src/test/java/com/datastax/driver/mapping/MapperOptionTest.java
/*
 *      Copyright (C) 2012-2015 DataStax Inc.
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */
package com.datastax.driver.mapping;

import java.util.Collection;

import com.google.common.collect.Lists;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

import com.datastax.driver.core.BoundStatement;
import com.datastax.driver.core.CCMBridge;
import com.datastax.driver.core.PreparedStatement;
import com.datastax.driver.mapping.annotations.PartitionKey;
import com.datastax.driver.mapping.annotations.Table;

import static com.datastax.driver.mapping.Mapper.Option;

public class MapperOptionTest extends CCMBridge.PerClassSingleNodeCluster {

    @Override
    protected Collection<String> getTableDefinitions() {
        return Lists.newArrayList("CREATE TABLE user (key int primary key, v text)");
    }

    @Test(groups = "short")
    void should_use_using_options_to_save() {
        Long tsValue = 906L;
        Mapper<User> mapper = new MappingManager(session).mapper(User.class);
        mapper.saveAsync(new User(42, "helloworld"), Option.timestamp(tsValue));
        assertThat(mapper.get(42).getV()).isEqualTo("helloworld");
        Long tsReturned = session.execute("SELECT writetime(v) FROM user WHERE key=" + 42).one().getLong(0);
        assertThat(tsReturned).isEqualTo(tsValue);
    }

    @Test(groups = "short")
    void should_use_using_options_only_once() {
        Long tsValue = 1L;
        Mapper<User> mapper = new MappingManager(session).mapper(User.class);
        mapper.save(new User(43, "helloworld"), Option.timestamp(tsValue));
        mapper.save(new User(44, "test"));
        Long tsReturned = session.execute("SELECT writetime(v) FROM user WHERE key=" + 44).one().getLong(0);
        // Assuming we cannot go back in time (yet) and execute the write at ts=1
        assertThat(tsReturned).isNotEqualTo(tsValue);
    }

    @Test(groups = "short")
    void should_allow_setting_default_options() {
        Mapper<User> mapper = new MappingManager(session).mapper(User.class);
        mapper.setDefaultSaveOptions(Option.timestamp(644746L), Option.ttl(76324));
        BoundStatement bs = (BoundStatement)mapper.saveQuery(new User(46, "rjhrgce"));
        assertThat(bs.preparedStatement().getQueryString()).contains("USING TIMESTAMP");
        mapper.resetDefaultSaveOptions();
        bs = (BoundStatement)mapper.saveQuery(new User(47, "rjhrgce"));
        assertThat(bs.preparedStatement().getQueryString()).doesNotContain("USING TIMESTAMP");
        mapper.setDefaultDeleteOptions(Option.timestamp(3245L));
        bs = (BoundStatement)mapper.deleteQuery(47);
        assertThat(bs.preparedStatement().getQueryString()).contains("USING TIMESTAMP");
        mapper.resetDefaultDeleteOptions();
        bs = (BoundStatement)mapper.deleteQuery(47);
        assertThat(bs.preparedStatement().getQueryString()).doesNotContain("USING TIMESTAMP");
    }

    @Test(groups = "short")
    void should_use_using_options_for_delete() {
        Mapper<User> mapper = new MappingManager(session).mapper(User.class);
        User todelete = new User(45, "todelete");
        mapper.save(todelete);
        Option opt = Option.timestamp(35);
        BoundStatement bs = (BoundStatement)mapper.deleteQuery(45, opt);
        assertThat(bs.preparedStatement().getQueryString()).contains("USING TIMESTAMP");
    }

    @Table(name = "user")
    public static class User {
        @PartitionKey
        private int key;
        private String v;

        public User() {
        }

        public User(int k, String val) {
            this.key = k;
            this.v = val;
        }

        public int getKey() {
            return this.key;
        }

        public void setKey(int pk) {
            this.key = pk;
        }

        public String getV() {
            return this.v;
        }

        public void setV(String val) {
            this.v = val;
        }
    }
}
