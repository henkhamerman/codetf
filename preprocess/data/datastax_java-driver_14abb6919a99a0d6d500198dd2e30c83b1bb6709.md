Refactoring Types: ['Extract Method']
om/datastax/driver/mapping/MethodMapper.java
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

import java.lang.reflect.Method;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.nio.ByteBuffer;

import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;

import com.datastax.driver.core.*;

// TODO: we probably should make that an abstract class and move some bit in a "ReflexionMethodMapper"
// subclass for consistency with the rest, but we can see to that later
class MethodMapper {

    public final Method method;
    public final String queryString;
    public final ParamMapper[] paramMappers;

    private final ConsistencyLevel consistency;
    private final int fetchSize;
    private final boolean tracing;

    private Session session;
    private PreparedStatement statement;

    private boolean returnStatement;
    private Mapper<?> returnMapper;
    private boolean mapOne;
    private boolean async;

    MethodMapper(Method method, String queryString, ParamMapper[] paramMappers, ConsistencyLevel consistency, int fetchSize, boolean enableTracing) {
        this.method = method;
        this.queryString = queryString;
        this.paramMappers = paramMappers;
        this.consistency = consistency;
        this.fetchSize = fetchSize;
        this.tracing = enableTracing;
    }

    public void prepare(MappingManager manager, PreparedStatement ps) {
        this.session = manager.getSession();
        this.statement = ps;

        if (method.isVarArgs())
            throw new IllegalArgumentException(String.format("Invalid varargs method %s in @Accessor interface"));
        if (ps.getVariables().size() != method.getParameterTypes().length)
            throw new IllegalArgumentException(String.format("The number of arguments for method %s (%d) does not match the number of bind parameters in the @Query (%d)",
                                                              method.getName(), method.getParameterTypes().length, ps.getVariables().size()));

        // TODO: we should also validate the types of the parameters...

        Class<?> returnType = method.getReturnType();
        if (Void.TYPE.isAssignableFrom(returnType) || ResultSet.class.isAssignableFrom(returnType))
            return;

        if (Statement.class.isAssignableFrom(returnType)) {
            returnStatement = true;
            return;
        }

        if (ResultSetFuture.class.isAssignableFrom(returnType)) {
            this.async = true;
            return;
        }

        if (ListenableFuture.class.isAssignableFrom(returnType)) {
            this.async = true;
            Type k = ((ParameterizedType)method.getGenericReturnType()).getActualTypeArguments()[0];
            if (k instanceof Class && ResultSet.class.isAssignableFrom((Class<?>)k))
                return;

            mapType(manager, returnType, k);
        } else {
            mapType(manager, returnType, method.getGenericReturnType());
        }
    }

    @SuppressWarnings("rawtypes")
    private void mapType(MappingManager manager, Class<?> fullReturnType, Type type) {

        if (type instanceof ParameterizedType) {
            ParameterizedType pt = (ParameterizedType)type;
            Type raw = pt.getRawType();
            if (raw instanceof Class && Result.class.isAssignableFrom((Class)raw)) {
                type = pt.getActualTypeArguments()[0];
            } else {
                mapOne = true;
            }
        } else {
            mapOne = true;
        }

        if (!(type instanceof Class))
            throw new RuntimeException(String.format("Cannot map return of method %s to unsupported type %s", method, type));

        try {
            this.returnMapper = (Mapper<?>)manager.mapper((Class<?>)type);
        } catch (Exception e) {
            throw new RuntimeException("Cannot map return to class " + fullReturnType, e);
        }
    }

    public Object invoke(Object[] args) {

        BoundStatement bs = statement.bind();

        ProtocolVersion protocolVersion = session.getCluster().getConfiguration().getProtocolOptions().getProtocolVersionEnum();
        for (int i = 0; i < args.length; i++) {
            paramMappers[i].setValue(bs, args[i], protocolVersion);
        }

        if (consistency != null)
            bs.setConsistencyLevel(consistency);
        if (fetchSize > 0)
            bs.setFetchSize(fetchSize);
        if (tracing)
            bs.enableTracing();

        if (returnStatement)
            return bs;

        if (async) {
            ListenableFuture<ResultSet> future = session.executeAsync(bs);
            if (returnMapper == null)
                return future;

            return mapOne
                 ? Futures.transform(future, returnMapper.mapOneFunctionWithoutAliases)
                 : Futures.transform(future, returnMapper.mapAllFunctionWithoutAliases);
        } else {
            ResultSet rs = session.execute(bs);
            if (returnMapper == null)
                return rs;

            Result<?> result = returnMapper.map(rs);
            return mapOne ? result.one() : result;
        }
    }

    static class ParamMapper {
        // We'll only set one of the other. If paramName is null, then paramIdx is used.
        private final String paramName;
        private final int paramIdx;
        private final DataType dataType;

        public ParamMapper(String paramName, int paramIdx, DataType dataType) {
            this.paramName = paramName;
            this.paramIdx = paramIdx;
            this.dataType = dataType;
        }

        public ParamMapper(String paramName, int paramIdx) {
            this(paramName, paramIdx, null);
        }

        void setValue(BoundStatement boundStatement, Object arg, ProtocolVersion protocolVersion) {
            ByteBuffer serializedArg = (dataType == null)
                ? DataType.serializeValue(arg, protocolVersion)
                : dataType.serialize(arg, protocolVersion);
            if (paramName == null) {
                if (arg == null)
                    boundStatement.setToNull(paramIdx);
                else
                    boundStatement.setBytesUnsafe(paramIdx, serializedArg);
            } else {
                if (arg == null)
                    boundStatement.setToNull(paramName);
                else
                    boundStatement.setBytesUnsafe(paramName, serializedArg);
            }
        }
    }

    static class UDTParamMapper<V> extends ParamMapper {
        private final UDTMapper<V> udtMapper;

        UDTParamMapper(String paramName, int paramIdx, UDTMapper<V> udtMapper) {
            super(paramName, paramIdx);
            this.udtMapper = udtMapper;
        }

        @Override
        void setValue(BoundStatement boundStatement, Object arg, ProtocolVersion protocolVersion) {
            @SuppressWarnings("unchecked")
            V entity = (V) arg;
            UDTValue udtArg = arg != null ? udtMapper.toUDT(entity) : null;
            super.setValue(boundStatement, udtArg, protocolVersion);
        }
    }

    /**
     * Maps a nested collection which has a mapped UDT somewhere in the hierarchy.
     */
    static class NestedUDTParamMapper extends ParamMapper {
        private final InferredCQLType inferredCQLType;

        NestedUDTParamMapper(String paramName, int paramIdx, InferredCQLType inferredCQLType) {
            super(paramName, paramIdx);
            this.inferredCQLType = inferredCQLType;
        }

        @Override
        void setValue(BoundStatement boundStatement, Object arg, ProtocolVersion protocolVersion) {
            super.setValue(boundStatement,
                UDTMapper.convertEntitiesToUDTs(arg, inferredCQLType),
                protocolVersion);
        }
    }

    static class EnumParamMapper extends ParamMapper {

        private final EnumType enumType;

        public EnumParamMapper(String paramName, int paramIdx, EnumType enumType) {
            super(paramName, paramIdx);
            this.enumType = enumType;
        }

        @Override
        void setValue(BoundStatement boundStatement, Object arg, ProtocolVersion protocolVersion) {
            super.setValue(boundStatement, convert(arg), protocolVersion);
        }

        @SuppressWarnings("rawtypes")
        private Object convert(Object arg) {
            if(arg == null)
                return arg;

            switch (enumType) {
            case STRING:
                return arg.toString();
            case ORDINAL:
                return ((Enum) arg).ordinal();
            }
            throw new AssertionError();
        }
    }
}


File: driver-mapping/src/test/java/com/datastax/driver/mapping/MapperAccessorParamsTest.java
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

import com.datastax.driver.core.ResultSet;
import com.google.common.collect.Lists;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

import com.datastax.driver.core.CCMBridge;
import com.datastax.driver.mapping.annotations.*;

public class MapperAccessorParamsTest extends CCMBridge.PerClassSingleNodeCluster {
    @Override
    protected Collection<String> getTableDefinitions() {
        return Lists.newArrayList(
                "CREATE TABLE user ( key int primary key, gender int)",
                "CREATE INDEX on user(gender)",
                "CREATE TABLE user_str ( key int primary key, gender text)",
                "CREATE INDEX on user_str(gender)");
    }

    @Test(groups = "short")
    void should_include_enumtype_in_accessor_ordinal() {
        UserAccessor accessor = new MappingManager(session)
                .createAccessor(UserAccessor.class);

        accessor.addUser(0, Enum.FEMALE);
        accessor.addUser(1, Enum.MALE);

        assertThat(accessor.getUser(Enum.MALE).one().getGender()).isEqualTo(Enum.MALE);
        assertThat(accessor.getUser(Enum.MALE).one().getKey()).isEqualTo(1);

        assertThat(accessor.getUser(Enum.FEMALE).one().getGender()).isEqualTo(Enum.FEMALE);
        assertThat(accessor.getUser(Enum.FEMALE).one().getKey()).isEqualTo(0);
    }

    @Test(groups = "short")
    void should_include_enumtype_in_accessor_string() {
        UserAccessor accessor = new MappingManager(session)
                .createAccessor(UserAccessor.class);

        accessor.addUserStr(0, Enum.FEMALE);
        accessor.addUserStr(1, Enum.MALE);

        assertThat(accessor.getUserStr(Enum.MALE).one().getGender()).isEqualTo(Enum.MALE);
        assertThat(accessor.getUserStr(Enum.MALE).one().getKey()).isEqualTo(1);

        assertThat(accessor.getUserStr(Enum.FEMALE).one().getGender()).isEqualTo(Enum.FEMALE);
        assertThat(accessor.getUserStr(Enum.FEMALE).one().getKey()).isEqualTo(0);
    }

    enum Enum {
        MALE, FEMALE
    }

    @Accessor
    public interface UserAccessor {
        @Query("select * from user where gender=?")
        Result<User> getUser(@Enumerated(EnumType.ORDINAL) Enum value);

        @Query("select * from user_str where gender=?")
        Result<UserStr> getUserStr(@Enumerated(EnumType.STRING) Enum value);

        @Query("insert into user (key, gender) values (?,?)")
        ResultSet addUser(int key, @Enumerated(EnumType.ORDINAL) Enum value);

        @Query("insert into user_str (key, gender) values (?,?)")
        ResultSet addUserStr(int key, @Enumerated(EnumType.STRING) Enum value);
    }

    @Table(name = "user")
    public static class User {
        @PartitionKey
        private int key;

        @Enumerated(EnumType.ORDINAL)
        private Enum gender;

        public User() {
        }

        public User(int k, Enum val) {
            this.key = k;
            this.gender = val;
        }

        public int getKey() {
            return this.key;
        }

        public void setKey(int pk) {
            this.key = pk;
        }

        public Enum getGender() {
            return this.gender;
        }

        public void setGender(Enum val) {
            this.gender = val;
        }
    }

    @Table(name = "user")
    public static class UserStr {
        @PartitionKey
        private int key;

        private Enum gender;

        public UserStr() {
        }

        public UserStr(int k, Enum val) {
            this.key = k;
            this.gender = val;
        }

        public int getKey() {
            return this.key;
        }

        public void setKey(int pk) {
            this.key = pk;
        }

        public Enum getGender() {
            return this.gender;
        }

        public void setGender(Enum val) {
            this.gender = val;
        }
    }
}