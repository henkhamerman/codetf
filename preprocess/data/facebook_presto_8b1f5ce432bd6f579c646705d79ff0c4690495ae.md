Refactoring Types: ['Extract Method']
facebook/presto/operator/scalar/ArraySubscriptOperator.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.facebook.presto.operator.scalar;

import com.facebook.presto.metadata.FunctionInfo;
import com.facebook.presto.metadata.FunctionRegistry;
import com.facebook.presto.metadata.ParametricOperator;
import com.facebook.presto.metadata.Signature;
import com.facebook.presto.spi.PrestoException;
import com.facebook.presto.spi.block.Block;
import com.facebook.presto.spi.type.StandardTypes;
import com.facebook.presto.spi.type.Type;
import com.facebook.presto.spi.type.TypeManager;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.primitives.Ints;
import io.airlift.slice.Slice;

import java.lang.invoke.MethodHandle;
import java.util.Map;

import static com.facebook.presto.metadata.OperatorType.SUBSCRIPT;
import static com.facebook.presto.metadata.Signature.typeParameter;
import static com.facebook.presto.spi.StandardErrorCode.INVALID_FUNCTION_ARGUMENT;
import static com.facebook.presto.type.TypeUtils.readStructuralBlock;
import static com.facebook.presto.spi.type.TypeSignature.parseTypeSignature;
import static com.facebook.presto.type.TypeUtils.parameterizedTypeName;
import static com.facebook.presto.util.Reflection.methodHandle;
import static com.google.common.base.Preconditions.checkArgument;
import static com.google.common.base.Preconditions.checkNotNull;

public class ArraySubscriptOperator
        extends ParametricOperator
{
    public static final ArraySubscriptOperator ARRAY_SUBSCRIPT = new ArraySubscriptOperator();

    private static final Map<Class<?>, MethodHandle> METHOD_HANDLES = ImmutableMap.<Class<?>, MethodHandle>builder()
            .put(boolean.class, methodHandle(ArraySubscriptOperator.class, "booleanSubscript", Type.class, Slice.class, long.class))
            .put(long.class, methodHandle(ArraySubscriptOperator.class, "longSubscript", Type.class, Slice.class, long.class))
            .put(void.class, methodHandle(ArraySubscriptOperator.class, "arrayWithUnknownType", Type.class, Slice.class, long.class))
            .put(double.class, methodHandle(ArraySubscriptOperator.class, "doubleSubscript", Type.class, Slice.class, long.class))
            .put(Slice.class, methodHandle(ArraySubscriptOperator.class, "sliceSubscript", Type.class, Slice.class, long.class))
            .build();

    protected ArraySubscriptOperator()
    {
        super(SUBSCRIPT, ImmutableList.of(typeParameter("E")), "E", ImmutableList.of("array<E>", "bigint"));
    }

    @Override
    public FunctionInfo specialize(Map<String, Type> types, int arity, TypeManager typeManager, FunctionRegistry functionRegistry)
    {
        checkArgument(types.size() == 1, "Expected one type, got %s", types);
        Type elementType = types.get("E");

        MethodHandle methodHandle = METHOD_HANDLES.get(elementType.getJavaType());
        methodHandle = methodHandle.bindTo(elementType);
        checkNotNull(methodHandle, "methodHandle is null");
        return new FunctionInfo(Signature.internalOperator(SUBSCRIPT.name(), elementType.getTypeSignature(), parameterizedTypeName("array", elementType.getTypeSignature()), parseTypeSignature(StandardTypes.BIGINT)), "Array subscript", true, methodHandle, true, true, ImmutableList.of(false, false));
    }

    public static void arrayWithUnknownType(Type elementType, Slice array, long index)
    {
        readBlockAndCheckIndex(array, index);
    }

    public static Long longSubscript(Type elementType, Slice array, long index)
    {
        Block block = readBlockAndCheckIndex(array, index);
        int position = Ints.checkedCast(index - 1);
        if (block.isNull(position)) {
            return null;
        }

        return elementType.getLong(block, position);
    }

    public static Boolean booleanSubscript(Type elementType, Slice array, long index)
    {
        Block block = readBlockAndCheckIndex(array, index);
        int position = Ints.checkedCast(index - 1);
        if (block.isNull(position)) {
            return null;
        }

        return elementType.getBoolean(block, position);
    }

    public static Double doubleSubscript(Type elementType, Slice array, long index)
    {
        Block block = readBlockAndCheckIndex(array, index);
        int position = Ints.checkedCast(index - 1);
        if (block.isNull(position)) {
            return null;
        }

        return elementType.getDouble(block, position);
    }

    public static Slice sliceSubscript(Type elementType, Slice array, long index)
    {
        Block block = readBlockAndCheckIndex(array, index);
        int position = Ints.checkedCast(index - 1);
        if (block.isNull(position)) {
            return null;
        }

        return elementType.getSlice(block, position);
    }

    public static Block readBlockAndCheckIndex(Slice array, long index)
    {
        if (index == 0) {
            throw new PrestoException(INVALID_FUNCTION_ARGUMENT, "SQL array indices start at 1");
        }
        if (index < 0) {
            throw new PrestoException(INVALID_FUNCTION_ARGUMENT, "Array subscript is negative");
        }
        Block block = readStructuralBlock(array);
        if (index > block.getPositionCount()) {
            throw new PrestoException(INVALID_FUNCTION_ARGUMENT, "Array subscript out of bounds");
        }
        return block;
    }
}


File: presto-main/src/main/java/com/facebook/presto/sql/planner/ExpressionInterpreter.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.facebook.presto.sql.planner;

import com.facebook.presto.Session;
import com.facebook.presto.metadata.FunctionInfo;
import com.facebook.presto.metadata.FunctionRegistry;
import com.facebook.presto.metadata.Metadata;
import com.facebook.presto.metadata.OperatorType;
import com.facebook.presto.spi.ConnectorSession;
import com.facebook.presto.spi.PrestoException;
import com.facebook.presto.spi.RecordCursor;
import com.facebook.presto.spi.block.Block;
import com.facebook.presto.spi.type.Type;
import com.facebook.presto.sql.tree.ArithmeticBinaryExpression;
import com.facebook.presto.sql.tree.ArithmeticUnaryExpression;
import com.facebook.presto.sql.tree.ArrayConstructor;
import com.facebook.presto.sql.tree.AstVisitor;
import com.facebook.presto.sql.tree.BetweenPredicate;
import com.facebook.presto.sql.tree.BooleanLiteral;
import com.facebook.presto.sql.tree.Cast;
import com.facebook.presto.sql.tree.CoalesceExpression;
import com.facebook.presto.sql.tree.ComparisonExpression;
import com.facebook.presto.sql.tree.Expression;
import com.facebook.presto.sql.tree.FunctionCall;
import com.facebook.presto.sql.tree.InListExpression;
import com.facebook.presto.sql.tree.InPredicate;
import com.facebook.presto.sql.tree.InputReference;
import com.facebook.presto.sql.tree.IsNotNullPredicate;
import com.facebook.presto.sql.tree.IsNullPredicate;
import com.facebook.presto.sql.tree.LikePredicate;
import com.facebook.presto.sql.tree.Literal;
import com.facebook.presto.sql.tree.LogicalBinaryExpression;
import com.facebook.presto.sql.tree.Node;
import com.facebook.presto.sql.tree.NotExpression;
import com.facebook.presto.sql.tree.NullIfExpression;
import com.facebook.presto.sql.tree.NullLiteral;
import com.facebook.presto.sql.tree.QualifiedName;
import com.facebook.presto.sql.tree.QualifiedNameReference;
import com.facebook.presto.sql.tree.Row;
import com.facebook.presto.sql.tree.SearchedCaseExpression;
import com.facebook.presto.sql.tree.SimpleCaseExpression;
import com.facebook.presto.sql.tree.StringLiteral;
import com.facebook.presto.sql.tree.SubscriptExpression;
import com.facebook.presto.sql.tree.WhenClause;
import com.facebook.presto.type.LikeFunctions;
import com.google.common.base.Functions;
import com.google.common.base.Throwables;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import io.airlift.joni.Regex;
import io.airlift.slice.Slice;

import java.lang.invoke.MethodHandle;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Stream;

import static com.facebook.presto.spi.StandardErrorCode.NOT_SUPPORTED;
import static com.facebook.presto.spi.type.TypeSignature.parseTypeSignature;
import static com.facebook.presto.sql.planner.LiteralInterpreter.toExpression;
import static com.facebook.presto.sql.planner.LiteralInterpreter.toExpressions;
import static com.facebook.presto.util.ImmutableCollectors.toImmutableList;
import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.base.Preconditions.checkState;
import static com.google.common.base.Predicates.instanceOf;
import static com.google.common.collect.Iterables.any;
import static java.nio.charset.StandardCharsets.UTF_8;

public class ExpressionInterpreter
{
    private final Expression expression;
    private final Metadata metadata;
    private final ConnectorSession session;
    private final boolean optimize;
    private final IdentityHashMap<Expression, Type> expressionTypes;

    private final Visitor visitor;

    // identity-based cache for LIKE expressions with constant pattern and escape char
    private final IdentityHashMap<LikePredicate, Regex> likePatternCache = new IdentityHashMap<>();
    private final IdentityHashMap<InListExpression, Set<Object>> inListCache = new IdentityHashMap<>();

    public static ExpressionInterpreter expressionInterpreter(Expression expression, Metadata metadata, Session session, IdentityHashMap<Expression, Type> expressionTypes)
    {
        checkNotNull(expression, "expression is null");
        checkNotNull(metadata, "metadata is null");
        checkNotNull(session, "session is null");

        return new ExpressionInterpreter(expression, metadata, session, expressionTypes, false);
    }

    public static ExpressionInterpreter expressionOptimizer(Expression expression, Metadata metadata, Session session, IdentityHashMap<Expression, Type> expressionTypes)
    {
        checkNotNull(expression, "expression is null");
        checkNotNull(metadata, "metadata is null");
        checkNotNull(session, "session is null");

        return new ExpressionInterpreter(expression, metadata, session, expressionTypes, true);
    }

    private ExpressionInterpreter(Expression expression, Metadata metadata, Session session, IdentityHashMap<Expression, Type> expressionTypes, boolean optimize)
    {
        this.expression = expression;
        this.metadata = metadata;
        this.session = session.toConnectorSession();
        this.expressionTypes = expressionTypes;
        this.optimize = optimize;

        this.visitor = new Visitor();
    }

    public Object evaluate(RecordCursor inputs)
    {
        checkState(!optimize, "evaluate(RecordCursor) not allowed for optimizer");
        return visitor.process(expression, inputs);
    }

    public Object evaluate(int position, Block... inputs)
    {
        checkState(!optimize, "evaluate(int, Block...) not allowed for optimizer");
        return visitor.process(expression, new PagePositionContext(position, inputs));
    }

    public Object optimize(SymbolResolver inputs)
    {
        checkState(optimize, "evaluate(SymbolResolver) not allowed for interpreter");
        return visitor.process(expression, inputs);
    }

    @SuppressWarnings("FloatingPointEquality")
    private class Visitor
            extends AstVisitor<Object, Object>
    {
        @Override
        public Object visitInputReference(InputReference node, Object context)
        {
            Type type = expressionTypes.get(node);

            int channel = node.getChannel();
            if (context instanceof PagePositionContext) {
                PagePositionContext pagePositionContext = (PagePositionContext) context;
                int position = pagePositionContext.getPosition();
                Block block = pagePositionContext.getBlock(channel);

                if (block.isNull(position)) {
                    return null;
                }

                Class<?> javaType = type.getJavaType();
                if (javaType == boolean.class) {
                    return type.getBoolean(block, position);
                }
                else if (javaType == long.class) {
                    return type.getLong(block, position);
                }
                else if (javaType == double.class) {
                    return type.getDouble(block, position);
                }
                else if (javaType == Slice.class) {
                    return type.getSlice(block, position);
                }
                else {
                    throw new UnsupportedOperationException("not yet implemented");
                }
            }
            else if (context instanceof RecordCursor) {
                RecordCursor cursor = (RecordCursor) context;
                if (cursor.isNull(channel)) {
                    return null;
                }

                Class<?> javaType = type.getJavaType();
                if (javaType == boolean.class) {
                    return cursor.getBoolean(channel);
                }
                else if (javaType == long.class) {
                    return cursor.getLong(channel);
                }
                else if (javaType == double.class) {
                    return cursor.getDouble(channel);
                }
                else if (javaType == Slice.class) {
                    return cursor.getSlice(channel);
                }
                else {
                    throw new UnsupportedOperationException("not yet implemented");
                }
            }
            throw new UnsupportedOperationException("Inputs or cursor myst be set");
        }

        @Override
        protected Object visitQualifiedNameReference(QualifiedNameReference node, Object context)
        {
            if (node.getName().getPrefix().isPresent()) {
                // not a symbol
                return node;
            }

            Symbol symbol = Symbol.fromQualifiedName(node.getName());
            return ((SymbolResolver) context).getValue(symbol);
        }

        @Override
        protected Object visitLiteral(Literal node, Object context)
        {
            return LiteralInterpreter.evaluate(metadata, session, node);
        }

        @Override
        protected Object visitIsNullPredicate(IsNullPredicate node, Object context)
        {
            Object value = process(node.getValue(), context);

            if (value instanceof Expression) {
                return new IsNullPredicate(toExpression(value, expressionTypes.get(node.getValue())));
            }

            return value == null;
        }

        @Override
        protected Object visitIsNotNullPredicate(IsNotNullPredicate node, Object context)
        {
            Object value = process(node.getValue(), context);

            if (value instanceof Expression) {
                return new IsNotNullPredicate(toExpression(value, expressionTypes.get(node.getValue())));
            }

            return value != null;
        }

        @Override
        protected Object visitSearchedCaseExpression(SearchedCaseExpression node, Object context)
        {
            Expression resultClause = node.getDefaultValue().orElse(null);
            for (WhenClause whenClause : node.getWhenClauses()) {
                Object value = process(whenClause.getOperand(), context);
                if (value instanceof Expression) {
                    // TODO: optimize this case
                    return node;
                }

                if (Boolean.TRUE.equals(value)) {
                    resultClause = whenClause.getResult();
                    break;
                }
            }

            if (resultClause == null) {
                return null;
            }

            Object result = process(resultClause, context);
            if (result instanceof Expression) {
                return node;
            }
            return result;
        }

        @Override
        protected Object visitSimpleCaseExpression(SimpleCaseExpression node, Object context)
        {
            Object operand = process(node.getOperand(), context);
            if (operand == null) {
                return node.getDefaultValue().map(defaultValue -> process(defaultValue, context)).orElse(null);
            }
            else if (operand instanceof Expression) {
                return node;
            }

            List<WhenClause> whenClauses = new ArrayList<>();
            Expression defaultClause = node.getDefaultValue().orElse(null);
            for (WhenClause whenClause : node.getWhenClauses()) {
                Object value = process(whenClause.getOperand(), context);
                if (value != null) {
                    if (value instanceof Expression) {
                        whenClauses.add(whenClause);
                    }
                    else if ((Boolean) invokeOperator(OperatorType.EQUAL, types(node.getOperand(), whenClause.getOperand()), ImmutableList.of(operand, value))) {
                        defaultClause = whenClause.getResult();
                        break;
                    }
                }
            }

            if (whenClauses.isEmpty()) {
                return defaultClause == null ? null : process(defaultClause, context);
            }
            else {
                return new SimpleCaseExpression(node.getOperand(), whenClauses, Optional.ofNullable(defaultClause));
            }
        }

        @Override
        protected Object visitCoalesceExpression(CoalesceExpression node, Object context)
        {
            for (Expression expression : node.getOperands()) {
                Object value = process(expression, context);

                if (value instanceof Expression) {
                    // TODO: optimize this case
                    return node;
                }

                if (value != null) {
                    return value;
                }
            }
            return null;
        }

        @Override
        protected Object visitInPredicate(InPredicate node, Object context)
        {
            Object value = process(node.getValue(), context);
            if (value == null) {
                return null;
            }

            Expression valueListExpression = node.getValueList();
            if (!(valueListExpression instanceof InListExpression)) {
                if (!optimize) {
                    throw new UnsupportedOperationException("IN predicate value list type not yet implemented: " + valueListExpression.getClass().getName());
                }
                return node;
            }
            InListExpression valueList = (InListExpression) valueListExpression;

            Set<Object> set = inListCache.get(valueList);

            // We use the presence of the node in the map to indicate that we've already done
            // the analysis below. If the value is null, it means that we can't apply the HashSet
            // optimization
            if (!inListCache.containsKey(valueList)) {
                if (Iterables.all(valueList.getValues(), ExpressionInterpreter::isNullLiteral)) {
                    // if all elements are constant, create a set with them
                    set = new HashSet<>();
                    for (Expression expression : valueList.getValues()) {
                        set.add(process(expression, context));
                    }
                }
                inListCache.put(valueList, set);
            }

            if (set != null && !(value instanceof Expression)) {
                return set.contains(value);
            }

            boolean hasUnresolvedValue = false;
            if (value instanceof Expression) {
                hasUnresolvedValue = true;
            }

            boolean hasNullValue = false;
            boolean found = false;
            List<Object> values = new ArrayList<>(valueList.getValues().size());
            List<Type> types = new ArrayList<>(valueList.getValues().size());
            for (Expression expression : valueList.getValues()) {
                Object inValue = process(expression, context);
                if (value instanceof Expression || inValue instanceof Expression) {
                    hasUnresolvedValue = true;
                    values.add(inValue);
                    types.add(expressionTypes.get(expression));
                    continue;
                }

                if (inValue == null) {
                    hasNullValue = true;
                }
                else if (!found && (Boolean) invokeOperator(OperatorType.EQUAL, types(node.getValue(), expression), ImmutableList.of(value, inValue))) {
                    // in does not short-circuit so we must evaluate all value in the list
                    found = true;
                }
            }
            if (found) {
                return true;
            }

            if (hasUnresolvedValue) {
                Type type = expressionTypes.get(node.getValue());
                List<Expression> expressionValues = toExpressions(values, types);
                List<Expression> simplifiedExpressionValues = Stream.concat(
                        expressionValues.stream()
                                .filter(DeterminismEvaluator::isDeterministic)
                                .distinct(),
                        expressionValues.stream()
                                .filter((expression -> !DeterminismEvaluator.isDeterministic(expression))))
                        .collect(toImmutableList());
                return new InPredicate(toExpression(value, type), new InListExpression(simplifiedExpressionValues));
            }
            if (hasNullValue) {
                return null;
            }
            return false;
        }

        @Override
        protected Object visitArithmeticUnary(ArithmeticUnaryExpression node, Object context)
        {
            Object value = process(node.getValue(), context);
            if (value == null) {
                return null;
            }
            if (value instanceof Expression) {
                return new ArithmeticUnaryExpression(node.getSign(), toExpression(value, expressionTypes.get(node.getValue())));
            }

            switch (node.getSign()) {
                case PLUS:
                    return value;
                case MINUS:
                    FunctionInfo operatorInfo = metadata.resolveOperator(OperatorType.NEGATION, types(node.getValue()));

                    MethodHandle handle = operatorInfo.getMethodHandle();
                    if (handle.type().parameterCount() > 0 && handle.type().parameterType(0) == ConnectorSession.class) {
                        handle = handle.bindTo(session);
                    }
                    try {
                        return handle.invokeWithArguments(value);
                    }
                    catch (Throwable throwable) {
                        Throwables.propagateIfInstanceOf(throwable, RuntimeException.class);
                        Throwables.propagateIfInstanceOf(throwable, Error.class);
                        throw new RuntimeException(throwable.getMessage(), throwable);
                    }
            }

            throw new UnsupportedOperationException("Unsupported unary operator: " + node.getSign());
        }

        @Override
        protected Object visitArithmeticBinary(ArithmeticBinaryExpression node, Object context)
        {
            Object left = process(node.getLeft(), context);
            if (left == null) {
                return null;
            }
            Object right = process(node.getRight(), context);
            if (right == null) {
                return null;
            }

            if (hasUnresolvedValue(left, right)) {
                return new ArithmeticBinaryExpression(node.getType(), toExpression(left, expressionTypes.get(node.getLeft())), toExpression(right, expressionTypes.get(node.getRight())));
            }

            return invokeOperator(OperatorType.valueOf(node.getType().name()), types(node.getLeft(), node.getRight()), ImmutableList.of(left, right));
        }

        @Override
        protected Object visitComparisonExpression(ComparisonExpression node, Object context)
        {
            ComparisonExpression.Type type = node.getType();

            Object left = process(node.getLeft(), context);
            if (left == null && type != ComparisonExpression.Type.IS_DISTINCT_FROM) {
                return null;
            }

            Object right = process(node.getRight(), context);
            if (type == ComparisonExpression.Type.IS_DISTINCT_FROM) {
                if (left == null && right == null) {
                    return false;
                }
                else if (left == null || right == null) {
                    return true;
                }
            }
            else if (right == null) {
                return null;
            }

            if (hasUnresolvedValue(left, right)) {
                return new ComparisonExpression(type, toExpression(left, expressionTypes.get(node.getLeft())), toExpression(right, expressionTypes.get(node.getRight())));
            }

            if (type == ComparisonExpression.Type.IS_DISTINCT_FROM) {
                type = ComparisonExpression.Type.NOT_EQUAL;
            }

            return invokeOperator(OperatorType.valueOf(type.name()), types(node.getLeft(), node.getRight()), ImmutableList.of(left, right));
        }

        @Override
        protected Object visitBetweenPredicate(BetweenPredicate node, Object context)
        {
            Object value = process(node.getValue(), context);
            if (value == null) {
                return null;
            }
            Object min = process(node.getMin(), context);
            if (min == null) {
                return null;
            }
            Object max = process(node.getMax(), context);
            if (max == null) {
                return null;
            }

            if (hasUnresolvedValue(value, min, max)) {
                return new BetweenPredicate(
                        toExpression(value, expressionTypes.get(node.getValue())),
                        toExpression(min, expressionTypes.get(node.getMin())),
                        toExpression(max, expressionTypes.get(node.getMax())));
            }

            return invokeOperator(OperatorType.BETWEEN, types(node.getValue(), node.getMin(), node.getMax()), ImmutableList.of(value, min, max));
        }

        @Override
        protected Object visitNullIfExpression(NullIfExpression node, Object context)
        {
            Object first = process(node.getFirst(), context);
            if (first == null) {
                return null;
            }
            Object second = process(node.getSecond(), context);
            if (second == null) {
                return first;
            }

            Type firstType = expressionTypes.get(node.getFirst());
            Type secondType = expressionTypes.get(node.getSecond());

            if (hasUnresolvedValue(first, second)) {
                return new NullIfExpression(toExpression(first, firstType), toExpression(second, secondType));
            }

            Type commonType = FunctionRegistry.getCommonSuperType(firstType, secondType).get();

            FunctionInfo firstCast = metadata.getFunctionRegistry().getCoercion(firstType, commonType);
            FunctionInfo secondCast = metadata.getFunctionRegistry().getCoercion(secondType, commonType);

            // cast(first as <common type>) == cast(second as <common type>)
            boolean equal = (Boolean) invokeOperator(
                    OperatorType.EQUAL,
                    ImmutableList.of(commonType, commonType),
                    ImmutableList.of(
                            invoke(session, firstCast.getMethodHandle(), ImmutableList.of(first)),
                            invoke(session, secondCast.getMethodHandle(), ImmutableList.of(second))));

            if (equal) {
                return null;
            }
            else {
                return first;
            }
        }

        @Override
        protected Object visitNotExpression(NotExpression node, Object context)
        {
            Object value = process(node.getValue(), context);
            if (value == null) {
                return null;
            }

            if (value instanceof Expression) {
                return new NotExpression(toExpression(value, expressionTypes.get(node.getValue())));
            }

            return !(Boolean) value;
        }

        @Override
        protected Object visitLogicalBinaryExpression(LogicalBinaryExpression node, Object context)
        {
            Object left = process(node.getLeft(), context);
            Object right = process(node.getRight(), context);

            switch (node.getType()) {
                case AND: {
                    // if either left or right is false, result is always false regardless of nulls
                    if (Boolean.FALSE.equals(left) || Boolean.TRUE.equals(right)) {
                        return left;
                    }

                    if (Boolean.FALSE.equals(right) || Boolean.TRUE.equals(left)) {
                        return right;
                    }
                    break;
                }
                case OR: {
                    // if either left or right is true, result is always true regardless of nulls
                    if (Boolean.TRUE.equals(left) || Boolean.FALSE.equals(right)) {
                        return left;
                    }

                    if (Boolean.TRUE.equals(right) || Boolean.FALSE.equals(left)) {
                        return right;
                    }
                    break;
                }
            }

            if (left == null && right == null) {
                return null;
            }

            return new LogicalBinaryExpression(node.getType(),
                    toExpression(left, expressionTypes.get(node.getLeft())),
                    toExpression(right, expressionTypes.get(node.getRight())));
        }

        @Override
        protected Object visitBooleanLiteral(BooleanLiteral node, Object context)
        {
            return node.equals(BooleanLiteral.TRUE_LITERAL);
        }

        @Override
        protected Object visitFunctionCall(FunctionCall node, Object context)
        {
            List<Type> argumentTypes = new ArrayList<>();
            List<Object> argumentValues = new ArrayList<>();
            for (Expression expression : node.getArguments()) {
                Object value = process(expression, context);
                Type type = expressionTypes.get(expression);
                argumentValues.add(value);
                argumentTypes.add(type);
            }
            FunctionInfo function = metadata.resolveFunction(node.getName(), Lists.transform(argumentTypes, Type::getTypeSignature), false);
            for (int i = 0; i < argumentValues.size(); i++) {
                Object value = argumentValues.get(i);
                if (value == null && !function.getNullableArguments().get(i)) {
                    return null;
                }
            }

            // do not optimize non-deterministic functions
            if (optimize && (!function.isDeterministic() || hasUnresolvedValue(argumentValues))) {
                return new FunctionCall(node.getName(), node.getWindow(), node.isDistinct(), toExpressions(argumentValues, argumentTypes));
            }
            return invoke(session, function.getMethodHandle(), argumentValues);
        }

        @Override
        protected Object visitLikePredicate(LikePredicate node, Object context)
        {
            Object value = process(node.getValue(), context);

            if (value == null) {
                return null;
            }

            if (value instanceof Slice &&
                    node.getPattern() instanceof StringLiteral &&
                    (node.getEscape() instanceof StringLiteral || node.getEscape() == null)) {
                // fast path when we know the pattern and escape are constant
                return LikeFunctions.like((Slice) value, getConstantPattern(node));
            }

            Object pattern = process(node.getPattern(), context);

            if (pattern == null) {
                return null;
            }

            Object escape = null;
            if (node.getEscape() != null) {
                escape = process(node.getEscape(), context);

                if (escape == null) {
                    return null;
                }
            }

            if (value instanceof Slice &&
                    pattern instanceof Slice &&
                    (escape == null || escape instanceof Slice)) {
                Regex regex;
                if (escape == null) {
                    regex = LikeFunctions.likePattern((Slice) pattern);
                }
                else {
                    regex = LikeFunctions.likePattern((Slice) pattern, (Slice) escape);
                }

                return LikeFunctions.like((Slice) value, regex);
            }

            // if pattern is a constant without % or _ replace with a comparison
            if (pattern instanceof Slice && escape == null) {
                String stringPattern = ((Slice) pattern).toString(UTF_8);
                if (!stringPattern.contains("%") && !stringPattern.contains("_")) {
                    return new ComparisonExpression(ComparisonExpression.Type.EQUAL,
                            toExpression(value, expressionTypes.get(node.getValue())),
                            toExpression(pattern, expressionTypes.get(node.getPattern())));
                }
            }

            Expression optimizedEscape = null;
            if (node.getEscape() != null) {
                optimizedEscape = toExpression(escape, expressionTypes.get(node.getEscape()));
            }

            return new LikePredicate(
                    toExpression(value, expressionTypes.get(node.getValue())),
                    toExpression(pattern, expressionTypes.get(node.getPattern())),
                    optimizedEscape);
        }

        private Regex getConstantPattern(LikePredicate node)
        {
            Regex result = likePatternCache.get(node);

            if (result == null) {
                StringLiteral pattern = (StringLiteral) node.getPattern();
                StringLiteral escape = (StringLiteral) node.getEscape();

                if (escape == null) {
                    result = LikeFunctions.likePattern(pattern.getSlice());
                }
                else {
                    result = LikeFunctions.likePattern(pattern.getSlice(), escape.getSlice());
                }

                likePatternCache.put(node, result);
            }

            return result;
        }

        @Override
        public Object visitCast(Cast node, Object context)
        {
            Object value = process(node.getExpression(), context);

            if (value instanceof Expression) {
                return new Cast((Expression) value, node.getType(), node.isSafe());
            }

            // hack!!! don't optimize CASTs for types that cannot be represented in the SQL AST
            // TODO: this will not be an issue when we migrate to RowExpression tree for this, which allows arbitrary literals.
            if (optimize && !FunctionRegistry.isSupportedLiteralType(expressionTypes.get(node))) {
                return new Cast(toExpression(value, expressionTypes.get(node.getExpression())), node.getType(), node.isSafe());
            }

            if (value == null) {
                return null;
            }

            Type type = metadata.getType(parseTypeSignature(node.getType()));
            if (type == null) {
                throw new IllegalArgumentException("Unsupported type: " + node.getType());
            }

            FunctionInfo operatorInfo = metadata.getFunctionRegistry().getCoercion(expressionTypes.get(node.getExpression()), type);

            try {
                return invoke(session, operatorInfo.getMethodHandle(), ImmutableList.of(value));
            }
            catch (RuntimeException e) {
                if (node.isSafe()) {
                    return null;
                }
                throw e;
            }
        }

        @Override
        protected Object visitArrayConstructor(ArrayConstructor node, Object context)
        {
            return visitFunctionCall(new FunctionCall(QualifiedName.of(ArrayConstructor.ARRAY_CONSTRUCTOR), node.getValues()), context);
        }

        @Override
        protected Object visitRow(Row node, Object context)
        {
            throw new PrestoException(NOT_SUPPORTED, "Row expressions not yet supported");
        }

        @Override
        protected Object visitSubscriptExpression(SubscriptExpression node, Object context)
        {
            Object base = process(node.getBase(), context);
            if (base == null) {
                return null;
            }
            Object index = process(node.getIndex(), context);
            if (index == null) {
                return null;
            }

            if (hasUnresolvedValue(base, index)) {
                return new SubscriptExpression(toExpression(base, expressionTypes.get(node.getBase())), toExpression(index, expressionTypes.get(node.getIndex())));
            }

            return invokeOperator(OperatorType.SUBSCRIPT, types(node.getBase(), node.getIndex()), ImmutableList.of(base, index));
        }

        @Override
        protected Object visitExpression(Expression node, Object context)
        {
            throw new PrestoException(NOT_SUPPORTED, "not yet implemented: " + node.getClass().getName());
        }

        @Override
        protected Object visitNode(Node node, Object context)
        {
            throw new UnsupportedOperationException("Evaluator visitor can only handle Expression nodes");
        }

        private List<Type> types(Expression... types)
        {
            return ImmutableList.copyOf(Iterables.transform(ImmutableList.copyOf(types), Functions.forMap(expressionTypes)));
        }

        private boolean hasUnresolvedValue(Object... values)
        {
            return hasUnresolvedValue(ImmutableList.copyOf(values));
        }

        private boolean hasUnresolvedValue(List<Object> values)
        {
            return any(values, instanceOf(Expression.class));
        }

        private Object invokeOperator(OperatorType operatorType, List<? extends Type> argumentTypes, List<Object> argumentValues)
        {
            FunctionInfo operatorInfo = metadata.resolveOperator(operatorType, argumentTypes);
            return invoke(session, operatorInfo.getMethodHandle(), argumentValues);
        }
    }

    private static class PagePositionContext
    {
        private final int position;
        private final Block[] blocks;

        private PagePositionContext(int position, Block[] blocks)
        {
            this.position = position;
            this.blocks = blocks;
        }

        public Block getBlock(int channel)
        {
            return blocks[channel];
        }

        public int getPosition()
        {
            return position;
        }
    }

    public static Object invoke(ConnectorSession session, MethodHandle handle, List<Object> argumentValues)
    {
        if (handle.type().parameterCount() > 0 && handle.type().parameterType(0) == ConnectorSession.class) {
            handle = handle.bindTo(session);
        }
        try {
            return handle.invokeWithArguments(argumentValues);
        }
        catch (Throwable throwable) {
            if (throwable instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw Throwables.propagate(throwable);
        }
    }

    private static boolean isNullLiteral(Expression entry)
    {
        return entry instanceof Literal && !(entry instanceof NullLiteral);
    }
}


File: presto-main/src/test/java/com/facebook/presto/sql/TestExpressionInterpreter.java
/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.facebook.presto.sql;

import com.facebook.presto.metadata.Metadata;
import com.facebook.presto.metadata.MetadataManager;
import com.facebook.presto.operator.scalar.FunctionAssertions;
import com.facebook.presto.spi.PrestoException;
import com.facebook.presto.spi.RecordCursor;
import com.facebook.presto.spi.type.Type;
import com.facebook.presto.sql.parser.SqlParser;
import com.facebook.presto.sql.planner.ExpressionInterpreter;
import com.facebook.presto.sql.planner.Symbol;
import com.facebook.presto.sql.planner.SymbolResolver;
import com.facebook.presto.sql.tree.Expression;
import com.facebook.presto.sql.tree.LikePredicate;
import com.facebook.presto.sql.tree.QualifiedNameReference;
import com.facebook.presto.sql.tree.StringLiteral;
import com.google.common.collect.ImmutableMap;
import io.airlift.slice.Slice;
import io.airlift.slice.Slices;
import org.intellij.lang.annotations.Language;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.joda.time.LocalDate;
import org.joda.time.LocalTime;
import org.testng.Assert;
import org.testng.annotations.Test;

import java.util.IdentityHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static com.facebook.presto.SessionTestUtils.TEST_SESSION;
import static com.facebook.presto.spi.type.BigintType.BIGINT;
import static com.facebook.presto.spi.type.BooleanType.BOOLEAN;
import static com.facebook.presto.spi.type.DateType.DATE;
import static com.facebook.presto.spi.type.DoubleType.DOUBLE;
import static com.facebook.presto.spi.type.IntervalDayTimeType.INTERVAL_DAY_TIME;
import static com.facebook.presto.spi.type.TimeType.TIME;
import static com.facebook.presto.spi.type.TimestampType.TIMESTAMP;
import static com.facebook.presto.spi.type.VarcharType.VARCHAR;
import static com.facebook.presto.sql.ExpressionFormatter.formatExpression;
import static com.facebook.presto.sql.analyzer.ExpressionAnalyzer.getExpressionTypes;
import static com.facebook.presto.sql.planner.ExpressionInterpreter.expressionInterpreter;
import static com.facebook.presto.sql.planner.ExpressionInterpreter.expressionOptimizer;
import static java.nio.charset.StandardCharsets.UTF_8;
import static java.util.Locale.ENGLISH;
import static org.testng.Assert.assertEquals;

public class TestExpressionInterpreter
{
    private static final Map<Symbol, Type> SYMBOL_TYPES = ImmutableMap.<Symbol, Type>builder()
            .put(new Symbol("bound_long"), BIGINT)
            .put(new Symbol("bound_string"), VARCHAR)
            .put(new Symbol("bound_double"), DOUBLE)
            .put(new Symbol("bound_boolean"), BOOLEAN)
            .put(new Symbol("bound_date"), DATE)
            .put(new Symbol("bound_time"), TIME)
            .put(new Symbol("bound_timestamp"), TIMESTAMP)
            .put(new Symbol("bound_pattern"), VARCHAR)
            .put(new Symbol("bound_null_string"), VARCHAR)
            .put(new Symbol("time"), BIGINT) // for testing reserved identifiers
            .put(new Symbol("unbound_long"), BIGINT)
            .put(new Symbol("unbound_long2"), BIGINT)
            .put(new Symbol("unbound_string"), VARCHAR)
            .put(new Symbol("unbound_double"), DOUBLE)
            .put(new Symbol("unbound_boolean"), BOOLEAN)
            .put(new Symbol("unbound_date"), DATE)
            .put(new Symbol("unbound_time"), TIME)
            .put(new Symbol("unbound_timestamp"), TIMESTAMP)
            .put(new Symbol("unbound_interval"), INTERVAL_DAY_TIME)
            .put(new Symbol("unbound_pattern"), VARCHAR)
            .put(new Symbol("unbound_null_string"), VARCHAR)
            .build();

    private static final SqlParser SQL_PARSER = new SqlParser();
    private static final Metadata METADATA = MetadataManager.createTestMetadataManager();

    @Test
    public void testAnd()
            throws Exception
    {
        assertOptimizedEquals("true and false", "false");
        assertOptimizedEquals("false and true", "false");
        assertOptimizedEquals("false and false", "false");

        assertOptimizedEquals("true and null", "null");
        assertOptimizedEquals("false and null", "false");
        assertOptimizedEquals("null and true", "null");
        assertOptimizedEquals("null and false", "false");
        assertOptimizedEquals("null and null", "null");

        assertOptimizedEquals("unbound_string='z' and true", "unbound_string='z'");
        assertOptimizedEquals("unbound_string='z' and false", "false");
        assertOptimizedEquals("true and unbound_string='z'", "unbound_string='z'");
        assertOptimizedEquals("false and unbound_string='z'", "false");

        assertOptimizedEquals("bound_string='z' and bound_long=1+1", "bound_string='z' and bound_long=2");
    }

    @Test
    public void testOr()
            throws Exception
    {
        assertOptimizedEquals("true or true", "true");
        assertOptimizedEquals("true or false", "true");
        assertOptimizedEquals("false or true", "true");
        assertOptimizedEquals("false or false", "false");

        assertOptimizedEquals("true or null", "true");
        assertOptimizedEquals("null or true", "true");
        assertOptimizedEquals("null or null", "null");

        assertOptimizedEquals("false or null", "null");
        assertOptimizedEquals("null or false", "null");

        assertOptimizedEquals("bound_string='z' or true", "true");
        assertOptimizedEquals("bound_string='z' or false", "bound_string='z'");
        assertOptimizedEquals("true or bound_string='z'", "true");
        assertOptimizedEquals("false or bound_string='z'", "bound_string='z'");

        assertOptimizedEquals("bound_string='z' or bound_long=1+1", "bound_string='z' or bound_long=2");
    }

    @Test
    public void testComparison()
            throws Exception
    {
        assertOptimizedEquals("null = null", "null");

        assertOptimizedEquals("'a' = 'b'", "false");
        assertOptimizedEquals("'a' = 'a'", "true");
        assertOptimizedEquals("'a' = null", "null");
        assertOptimizedEquals("null = 'a'", "null");

        assertOptimizedEquals("bound_long = 1234", "true");
        assertOptimizedEquals("bound_double = 12.34", "true");
        assertOptimizedEquals("bound_string = 'hello'", "true");
        assertOptimizedEquals("bound_long = unbound_long", "1234 = unbound_long");

        assertOptimizedEquals("10151082135029368 = 10151082135029369", "false");
    }

    @Test
    public void testIsDistinctFrom()
            throws Exception
    {
        assertOptimizedEquals("null is distinct from null", "false");

        assertOptimizedEquals("3 is distinct from 4", "true");
        assertOptimizedEquals("3 is distinct from 3", "false");
        assertOptimizedEquals("3 is distinct from null", "true");
        assertOptimizedEquals("null is distinct from 3", "true");

        assertOptimizedEquals("10151082135029368 is distinct from 10151082135029369", "true");
    }

    @Test
    public void testIsNull()
            throws Exception
    {
        assertOptimizedEquals("null is null", "true");
        assertOptimizedEquals("1 is null", "false");
        assertOptimizedEquals("1.0 is null", "false");
        assertOptimizedEquals("'a' is null", "false");
        assertOptimizedEquals("true is null", "false");
        assertOptimizedEquals("null+1 is null", "true");
        assertOptimizedEquals("unbound_string is null", "unbound_string is null");
        assertOptimizedEquals("unbound_long+(1+1) is null", "unbound_long+2 is null");
    }

    @Test
    public void testIsNotNull()
            throws Exception
    {
        assertOptimizedEquals("null is not null", "false");
        assertOptimizedEquals("1 is not null", "true");
        assertOptimizedEquals("1.0 is not null", "true");
        assertOptimizedEquals("'a' is not null", "true");
        assertOptimizedEquals("true is not null", "true");
        assertOptimizedEquals("null+1 is not null", "false");
        assertOptimizedEquals("unbound_string is not null", "unbound_string is not null");
        assertOptimizedEquals("unbound_long+(1+1) is not null", "unbound_long+2 is not null");
    }

    @Test
    public void testNullIf()
            throws Exception
    {
        assertOptimizedEquals("nullif(true, true)", "null");
        assertOptimizedEquals("nullif(true, false)", "true");
        assertOptimizedEquals("nullif(null, false)", "null");
        assertOptimizedEquals("nullif(true, null)", "true");

        assertOptimizedEquals("nullif('a', 'a')", "null");
        assertOptimizedEquals("nullif('a', 'b')", "'a'");
        assertOptimizedEquals("nullif(null, 'b')", "null");
        assertOptimizedEquals("nullif('a', null)", "'a'");

        assertOptimizedEquals("nullif(1, 1)", "null");
        assertOptimizedEquals("nullif(1, 2)", "1");
        assertOptimizedEquals("nullif(1.0, 1)", "null");
        assertOptimizedEquals("nullif(1.1, 1)", "1.1");
        assertOptimizedEquals("nullif(1.1, 1.1)", "null");
        assertOptimizedEquals("nullif(1, 2-1)", "null");
        assertOptimizedEquals("nullif(null, null)", "null");
        assertOptimizedEquals("nullif(1, null)", "1");
        assertOptimizedEquals("nullif(unbound_long, 1)", "nullif(unbound_long, 1)");
        assertOptimizedEquals("nullif(unbound_long, unbound_long2)", "nullif(unbound_long, unbound_long2)");
        assertOptimizedEquals("nullif(unbound_long, unbound_long2+(1+1))", "nullif(unbound_long, unbound_long2+2)");
    }

    @Test
    public void testNegative()
            throws Exception
    {
        assertOptimizedEquals("-(1)", "-1");
        assertOptimizedEquals("-(unbound_long+1)", "-(unbound_long+1)");
        assertOptimizedEquals("-(1+1)", "-2");
        assertOptimizedEquals("-(null)", "null");
        assertOptimizedEquals("-(unbound_long+(1+1))", "-(unbound_long+2)");
    }

    @Test
    public void testNot()
            throws Exception
    {
        assertOptimizedEquals("not true", "false");
        assertOptimizedEquals("not false", "true");
        assertOptimizedEquals("not null", "null");
        assertOptimizedEquals("not 1=1", "false");
        assertOptimizedEquals("not 1!=1", "true");
        assertOptimizedEquals("not unbound_long=1", "not unbound_long=1");
        assertOptimizedEquals("not unbound_long=(1+1)", "not unbound_long=2");
    }

    @Test
    public void testFunctionCall()
            throws Exception
    {
        assertOptimizedEquals("abs(-5)", "5");
        assertOptimizedEquals("abs(-10-5)", "15");
        assertOptimizedEquals("abs(-bound_long + 1)", "1233");
        assertOptimizedEquals("abs(-bound_long)", "1234");
        assertOptimizedEquals("abs(unbound_long)", "abs(unbound_long)");
        assertOptimizedEquals("abs(unbound_long + 1)", "abs(unbound_long + 1)");
    }

    @Test
    public void testNonDeterministicFunctionCall()
            throws Exception
    {
        // optimize should do nothing
        assertOptimizedEquals("random()", "random()");

        // evaluate should execute
        Object value = evaluate("random()");
        Assert.assertTrue(value instanceof Double);
        double randomValue = (double) value;
        Assert.assertTrue(0 <= randomValue && randomValue < 1);
    }

    @Test
    public void testBetween()
            throws Exception
    {
        assertOptimizedEquals("3 between 2 and 4", "true");
        assertOptimizedEquals("2 between 3 and 4", "false");
        assertOptimizedEquals("null between 2 and 4", "null");
        assertOptimizedEquals("3 between null and 4", "null");
        assertOptimizedEquals("3 between 2 and null", "null");

        assertOptimizedEquals("'c' between 'b' and 'd'", "true");
        assertOptimizedEquals("'b' between 'c' and 'd'", "false");
        assertOptimizedEquals("null between 'b' and 'd'", "null");
        assertOptimizedEquals("'c' between null and 'd'", "null");
        assertOptimizedEquals("'c' between 'b' and null", "null");

        assertOptimizedEquals("bound_long between 1000 and 2000", "true");
        assertOptimizedEquals("bound_long between 3 and 4", "false");
        assertOptimizedEquals("bound_string between 'e' and 'i'", "true");
        assertOptimizedEquals("bound_string between 'a' and 'b'", "false");

        assertOptimizedEquals("bound_long between unbound_long and 2000 + 1", "1234 between unbound_long and 2001");
        assertOptimizedEquals("bound_string between unbound_string and 'bar'", "'hello' between unbound_string and 'bar'");
    }

    @Test
    public void testExtract()
    {
        DateTime dateTime = new DateTime(2001, 8, 22, 3, 4, 5, 321, DateTimeZone.UTC);
        double seconds = dateTime.getMillis() / 1000.0;

        assertOptimizedEquals("extract (YEAR from from_unixtime(" + seconds + "))", "2001");
        assertOptimizedEquals("extract (QUARTER from from_unixtime(" + seconds + "))", "3");
        assertOptimizedEquals("extract (MONTH from from_unixtime(" + seconds + "))", "8");
        assertOptimizedEquals("extract (WEEK from from_unixtime(" + seconds + "))", "34");
        assertOptimizedEquals("extract (DOW from from_unixtime(" + seconds + "))", "3");
        assertOptimizedEquals("extract (DOY from from_unixtime(" + seconds + "))", "234");
        assertOptimizedEquals("extract (DAY from from_unixtime(" + seconds + "))", "22");
        assertOptimizedEquals("extract (HOUR from from_unixtime(" + seconds + "))", "3");
        assertOptimizedEquals("extract (MINUTE from from_unixtime(" + seconds + "))", "4");
        assertOptimizedEquals("extract (SECOND from from_unixtime(" + seconds + "))", "5");
        assertOptimizedEquals("extract (TIMEZONE_HOUR from from_unixtime(" + seconds + ", 7, 9))", "7");
        assertOptimizedEquals("extract (TIMEZONE_MINUTE from from_unixtime(" + seconds + ", 7, 9))", "9");

        assertOptimizedEquals("extract (YEAR from bound_timestamp)", "2001");
        assertOptimizedEquals("extract (QUARTER from bound_timestamp)", "3");
        assertOptimizedEquals("extract (MONTH from bound_timestamp)", "8");
        assertOptimizedEquals("extract (WEEK from bound_timestamp)", "34");
        assertOptimizedEquals("extract (DOW from bound_timestamp)", "3");
        assertOptimizedEquals("extract (DOY from bound_timestamp)", "234");
        assertOptimizedEquals("extract (DAY from bound_timestamp)", "22");
        assertOptimizedEquals("extract (HOUR from bound_timestamp)", "3");
        assertOptimizedEquals("extract (MINUTE from bound_timestamp)", "4");
        assertOptimizedEquals("extract (SECOND from bound_timestamp)", "5");
        // todo reenable when cast as timestamp with time zone is implemented
        // todo add bound timestamp with time zone
        //assertOptimizedEquals("extract (TIMEZONE_HOUR from bound_timestamp)", "0");
        //assertOptimizedEquals("extract (TIMEZONE_MINUTE from bound_timestamp)", "0");

        assertOptimizedEquals("extract (YEAR from unbound_timestamp)", "extract (YEAR from unbound_timestamp)");
        assertOptimizedEquals("extract (SECOND from bound_timestamp + INTERVAL '3' SECOND)", "8");
    }

    @Test
    public void testIn()
            throws Exception
    {
        assertOptimizedEquals("3 in (2, 4, 3, 5)", "true");
        assertOptimizedEquals("3 in (2, 4, 9, 5)", "false");
        assertOptimizedEquals("3 in (2, null, 3, 5)", "true");

        assertOptimizedEquals("'foo' in ('bar', 'baz', 'foo', 'blah')", "true");
        assertOptimizedEquals("'foo' in ('bar', 'baz', 'buz', 'blah')", "false");
        assertOptimizedEquals("'foo' in ('bar', null, 'foo', 'blah')", "true");

        assertOptimizedEquals("null in (2, null, 3, 5)", "null");
        assertOptimizedEquals("3 in (2, null)", "null");

        assertOptimizedEquals("bound_long in (2, 1234, 3, 5)", "true");
        assertOptimizedEquals("bound_long in (2, 4, 3, 5)", "false");
        assertOptimizedEquals("1234 in (2, bound_long, 3, 5)", "true");
        assertOptimizedEquals("99 in (2, bound_long, 3, 5)", "false");
        assertOptimizedEquals("bound_long in (2, bound_long, 3, 5)", "true");

        assertOptimizedEquals("bound_string in ('bar', 'hello', 'foo', 'blah')", "true");
        assertOptimizedEquals("bound_string in ('bar', 'baz', 'foo', 'blah')", "false");
        assertOptimizedEquals("'hello' in ('bar', bound_string, 'foo', 'blah')", "true");
        assertOptimizedEquals("'baz' in ('bar', bound_string, 'foo', 'blah')", "false");

        assertOptimizedEquals("bound_long in (2, 1234, unbound_long, 5)", "true");
        assertOptimizedEquals("bound_string in ('bar', 'hello', unbound_string, 'blah')", "true");

        assertOptimizedEquals("bound_long in (2, 4, unbound_long, unbound_long2, 9)", "1234 in (unbound_long, unbound_long2)");
        assertOptimizedEquals("unbound_long in (2, 4, bound_long, unbound_long2, 5)", "unbound_long in (2, 4, 1234, unbound_long2, 5)");
    }

    @Test
    public void testCurrentTimestamp()
            throws Exception
    {
        double current = TEST_SESSION.getStartTime() / 1000.0;
        assertOptimizedEquals("current_timestamp = from_unixtime(" + current + ")", "true");
        double future = current + TimeUnit.MINUTES.toSeconds(1);
        assertOptimizedEquals("current_timestamp > from_unixtime(" + future + ")", "false");
    }

    @Test
    public void testCastToString()
            throws Exception
    {
        // long
        assertOptimizedEquals("cast(123 as VARCHAR)", "'123'");
        assertOptimizedEquals("cast(-123 as VARCHAR)", "'-123'");

        // double
        assertOptimizedEquals("cast(123.0 as VARCHAR)", "'123.0'");
        assertOptimizedEquals("cast(-123.0 as VARCHAR)", "'-123.0'");
        assertOptimizedEquals("cast(123.456 as VARCHAR)", "'123.456'");
        assertOptimizedEquals("cast(-123.456 as VARCHAR)", "'-123.456'");

        // boolean
        assertOptimizedEquals("cast(true as VARCHAR)", "'true'");
        assertOptimizedEquals("cast(false as VARCHAR)", "'false'");

        // string
        assertOptimizedEquals("cast('xyz' as VARCHAR)", "'xyz'");

        // null
        assertOptimizedEquals("cast(null as VARCHAR)", "null");
    }

    @Test
    public void testCastToBoolean()
            throws Exception
    {
        // long
        assertOptimizedEquals("cast(123 as BOOLEAN)", "true");
        assertOptimizedEquals("cast(-123 as BOOLEAN)", "true");
        assertOptimizedEquals("cast(0 as BOOLEAN)", "false");

        // boolean
        assertOptimizedEquals("cast(true as BOOLEAN)", "true");
        assertOptimizedEquals("cast(false as BOOLEAN)", "false");

        // string
        assertOptimizedEquals("cast('true' as BOOLEAN)", "true");
        assertOptimizedEquals("cast('false' as BOOLEAN)", "false");
        assertOptimizedEquals("cast('t' as BOOLEAN)", "true");
        assertOptimizedEquals("cast('f' as BOOLEAN)", "false");
        assertOptimizedEquals("cast('1' as BOOLEAN)", "true");
        assertOptimizedEquals("cast('0' as BOOLEAN)", "false");

        // null
        assertOptimizedEquals("cast(null as BOOLEAN)", "null");

        // double
        assertOptimizedEquals("cast(123.45 as BOOLEAN)", "true");
        assertOptimizedEquals("cast(-123.45 as BOOLEAN)", "true");
        assertOptimizedEquals("cast(0.0 as BOOLEAN)", "false");
    }

    @Test
    public void testCastToLong()
            throws Exception
    {
        // long
        assertOptimizedEquals("cast(0 as BIGINT)", "0");
        assertOptimizedEquals("cast(123 as BIGINT)", "123");
        assertOptimizedEquals("cast(-123 as BIGINT)", "-123");

        // double
        assertOptimizedEquals("cast(123.0 as BIGINT)", "123");
        assertOptimizedEquals("cast(-123.0 as BIGINT)", "-123");
        assertOptimizedEquals("cast(123.456 as BIGINT)", "123");
        assertOptimizedEquals("cast(-123.456 as BIGINT)", "-123");

        // boolean
        assertOptimizedEquals("cast(true as BIGINT)", "1");
        assertOptimizedEquals("cast(false as BIGINT)", "0");

        // string
        assertOptimizedEquals("cast('123' as BIGINT)", "123");
        assertOptimizedEquals("cast('-123' as BIGINT)", "-123");

        // null
        assertOptimizedEquals("cast(null as BIGINT)", "null");
    }

    @Test
    public void testCastToDouble()
            throws Exception
    {
        // long
        assertOptimizedEquals("cast(0 as DOUBLE)", "0.0");
        assertOptimizedEquals("cast(123 as DOUBLE)", "123.0");
        assertOptimizedEquals("cast(-123 as DOUBLE)", "-123.0");

        // double
        assertOptimizedEquals("cast(123.0 as DOUBLE)", "123.0");
        assertOptimizedEquals("cast(-123.0 as DOUBLE)", "-123.0");
        assertOptimizedEquals("cast(123.456 as DOUBLE)", "123.456");
        assertOptimizedEquals("cast(-123.456 as DOUBLE)", "-123.456");

        // string
        assertOptimizedEquals("cast('0' as DOUBLE)", "0.0");
        assertOptimizedEquals("cast('123' as DOUBLE)", "123.0");
        assertOptimizedEquals("cast('-123' as DOUBLE)", "-123.0");
        assertOptimizedEquals("cast('123.0' as DOUBLE)", "123.0");
        assertOptimizedEquals("cast('-123.0' as DOUBLE)", "-123.0");
        assertOptimizedEquals("cast('123.456' as DOUBLE)", "123.456");
        assertOptimizedEquals("cast('-123.456' as DOUBLE)", "-123.456");

        // null
        assertOptimizedEquals("cast(null as DOUBLE)", "null");

        // boolean
        assertOptimizedEquals("cast(true as DOUBLE)", "1.0");
        assertOptimizedEquals("cast(false as DOUBLE)", "0.0");
    }

    @Test
    public void testCastOptimization()
            throws Exception
    {
        assertOptimizedEquals("cast(bound_long as VARCHAR)", "'1234'");
        assertOptimizedEquals("cast(bound_long + 1 as VARCHAR)", "'1235'");
        assertOptimizedEquals("cast(unbound_string as VARCHAR)", "cast(unbound_string as VARCHAR)");
    }

    @Test
    public void testTryCast()
    {
        assertOptimizedEquals("try_cast(null as BIGINT)", "null");
        assertOptimizedEquals("try_cast(123 as BIGINT)", "123");
        assertOptimizedEquals("try_cast('foo' as VARCHAR)", "'foo'");
        assertOptimizedEquals("try_cast('foo' as BIGINT)", "null");
        assertOptimizedEquals("try_cast(unbound_string as BIGINT)", "try_cast(unbound_string as BIGINT)");
    }

    @Test
    public void testReservedWithDoubleQuotes()
            throws Exception
    {
        assertOptimizedEquals("\"time\"", "\"time\"");
    }

    @Test
    public void testSearchCase()
            throws Exception
    {
        assertOptimizedEquals("case " +
                "when true then 33 " +
                "end",
                "33");
        assertOptimizedEquals("case " +
                "when false then 1 " +
                "else 33 " +
                "end",
                "33");

        assertOptimizedEquals("case " +
                "when bound_long = 1234 then 33 " +
                "end",
                "33");
        assertOptimizedEquals("case " +
                "when true then bound_long " +
                "end",
                "1234");
        assertOptimizedEquals("case " +
                "when false then 1 " +
                "else bound_long " +
                "end",
                "1234");

        assertOptimizedEquals("case " +
                "when bound_long = 1234 then 33 " +
                "else unbound_long " +
                "end",
                "33");
        assertOptimizedEquals("case " +
                "when true then bound_long " +
                "else unbound_long " +
                "end",
                "1234");
        assertOptimizedEquals("case " +
                "when false then unbound_long " +
                "else bound_long " +
                "end",
                "1234");

        assertOptimizedEquals("case " +
                "when unbound_long = 1234 then 33 " +
                "else 1 " +
                "end",
                "" +
                        "case " +
                        "when unbound_long = 1234 then 33 " +
                        "else 1 " +
                        "end");
    }

    @Test
    public void testSimpleCase()
            throws Exception
    {
        assertOptimizedEquals("case 1 " +
                "when 1 then 33 " +
                "when 1 then 34 " +
                "end",
                "33");

        assertOptimizedEquals("case null " +
                "when true then 33 " +
                "end",
                "null");
        assertOptimizedEquals("case null " +
                "when true then 33 " +
                "else 33 " +
                "end",
                "33");
        assertOptimizedEquals("case 33 " +
                "when null then 1 " +
                "else 33 " +
                "end",
                "33");

        assertOptimizedEquals("case true " +
                "when true then 33 " +
                "end",
                "33");
        assertOptimizedEquals("case true " +
                "when false then 1 " +
                "else 33 end",
                "33");

        assertOptimizedEquals("case bound_long " +
                "when 1234 then 33 " +
                "end",
                "33");
        assertOptimizedEquals("case 1234 " +
                "when bound_long then 33 " +
                "end",
                "33");
        assertOptimizedEquals("case true " +
                "when true then bound_long " +
                "end",
                "1234");
        assertOptimizedEquals("case true " +
                "when false then 1 " +
                "else bound_long " +
                "end",
                "1234");

        assertOptimizedEquals("case bound_long " +
                "when 1234 then 33 " +
                "else unbound_long " +
                "end",
                "33");
        assertOptimizedEquals("case true " +
                "when true then bound_long " +
                "else unbound_long " +
                "end",
                "1234");
        assertOptimizedEquals("case true " +
                "when false then unbound_long " +
                "else bound_long " +
                "end",
                "1234");

        assertOptimizedEquals("case unbound_long " +
                "when 1234 then 33 " +
                "else 1 " +
                "end",
                "" +
                        "case unbound_long " +
                        "when 1234 then 33 " +
                        "else 1 " +
                        "end");

        assertOptimizedEquals("case 33 " +
                        "when 0 then 0 " +
                        "when 33 then unbound_long " +
                        "else 1 " +
                        "end",
                        "unbound_long");
        assertOptimizedEquals("case 33 " +
                        "when 0 then 0 " +
                        "when 33 then 1 " +
                        "when unbound_long then 2 " +
                        "else 1 " +
                        "end",
                        "1");
        assertOptimizedEquals("case 33 " +
                        "when unbound_long then 0 " +
                        "when 1 then 1 " +
                        "when 33 then 2 " +
                        "else 0 " +
                        "end",
                        "case 33 " +
                        "when unbound_long then 0 " +
                        "else 2 " +
                        "end");
        assertOptimizedEquals("case 33 " +
                        "when 0 then 0 " +
                        "when 1 then 1 " +
                        "else unbound_long " +
                        "end",
                        "unbound_long");
        assertOptimizedEquals("case 33 " +
                        "when unbound_long then 0 " +
                        "when 1 then 1 " +
                        "when unbound_long2 then 2 " +
                        "else 3 " +
                        "end",
                        "case 33 " +
                        "when unbound_long then 0 " +
                        "when unbound_long2 then 2 " +
                        "else 3 " +
                        "end");
    }

    @Test
    public void testIf()
            throws Exception
    {
        assertOptimizedEquals("IF(2 = 2, 3, 4)", "3");
        assertOptimizedEquals("IF(1 = 2, 3, 4)", "4");

        assertOptimizedEquals("IF(true, 3, 4)", "3");
        assertOptimizedEquals("IF(false, 3, 4)", "4");
        assertOptimizedEquals("IF(null, 3, 4)", "4");

        assertOptimizedEquals("IF(true, 3, null)", "3");
        assertOptimizedEquals("IF(false, 3, null)", "null");
        assertOptimizedEquals("IF(true, null, 4)", "null");
        assertOptimizedEquals("IF(false, null, 4)", "4");
        assertOptimizedEquals("IF(true, null, null)", "null");
        assertOptimizedEquals("IF(false, null, null)", "null");

        assertOptimizedEquals("IF(true, 3.5, 4.2)", "3.5");
        assertOptimizedEquals("IF(false, 3.5, 4.2)", "4.2");

        assertOptimizedEquals("IF(true, 'foo', 'bar')", "'foo'");
        assertOptimizedEquals("IF(false, 'foo', 'bar')", "'bar'");

        // todo optimize case statement
        assertOptimizedEquals("IF(unbound_boolean, 1 + 2, 3 + 4)", "CASE WHEN unbound_boolean THEN (1 + 2) ELSE (3 + 4) END");
    }

    @Test
    public void testLike()
            throws Exception
    {
        assertOptimizedEquals("'a' LIKE 'a'", "true");
        assertOptimizedEquals("'' LIKE 'a'", "false");
        assertOptimizedEquals("'abc' LIKE 'a'", "false");

        assertOptimizedEquals("'a' LIKE '_'", "true");
        assertOptimizedEquals("'' LIKE '_'", "false");
        assertOptimizedEquals("'abc' LIKE '_'", "false");

        assertOptimizedEquals("'a' LIKE '%'", "true");
        assertOptimizedEquals("'' LIKE '%'", "true");
        assertOptimizedEquals("'abc' LIKE '%'", "true");

        assertOptimizedEquals("'abc' LIKE '___'", "true");
        assertOptimizedEquals("'ab' LIKE '___'", "false");
        assertOptimizedEquals("'abcd' LIKE '___'", "false");

        assertOptimizedEquals("'abc' LIKE 'abc'", "true");
        assertOptimizedEquals("'xyz' LIKE 'abc'", "false");
        assertOptimizedEquals("'abc0' LIKE 'abc'", "false");
        assertOptimizedEquals("'0abc' LIKE 'abc'", "false");

        assertOptimizedEquals("'abc' LIKE 'abc%'", "true");
        assertOptimizedEquals("'abc0' LIKE 'abc%'", "true");
        assertOptimizedEquals("'0abc' LIKE 'abc%'", "false");

        assertOptimizedEquals("'abc' LIKE '%abc'", "true");
        assertOptimizedEquals("'0abc' LIKE '%abc'", "true");
        assertOptimizedEquals("'abc0' LIKE '%abc'", "false");

        assertOptimizedEquals("'abc' LIKE '%abc%'", "true");
        assertOptimizedEquals("'0abc' LIKE '%abc%'", "true");
        assertOptimizedEquals("'abc0' LIKE '%abc%'", "true");
        assertOptimizedEquals("'0abc0' LIKE '%abc%'", "true");
        assertOptimizedEquals("'xyzw' LIKE '%abc%'", "false");

        assertOptimizedEquals("'abc' LIKE '%ab%c%'", "true");
        assertOptimizedEquals("'0abc' LIKE '%ab%c%'", "true");
        assertOptimizedEquals("'abc0' LIKE '%ab%c%'", "true");
        assertOptimizedEquals("'0abc0' LIKE '%ab%c%'", "true");
        assertOptimizedEquals("'ab01c' LIKE '%ab%c%'", "true");
        assertOptimizedEquals("'0ab01c' LIKE '%ab%c%'", "true");
        assertOptimizedEquals("'ab01c0' LIKE '%ab%c%'", "true");
        assertOptimizedEquals("'0ab01c0' LIKE '%ab%c%'", "true");

        assertOptimizedEquals("'xyzw' LIKE '%ab%c%'", "false");

        // ensure regex chars are escaped
        assertOptimizedEquals("'\' LIKE '\'", "true");
        assertOptimizedEquals("'.*' LIKE '.*'", "true");
        assertOptimizedEquals("'[' LIKE '['", "true");
        assertOptimizedEquals("']' LIKE ']'", "true");
        assertOptimizedEquals("'{' LIKE '{'", "true");
        assertOptimizedEquals("'}' LIKE '}'", "true");
        assertOptimizedEquals("'?' LIKE '?'", "true");
        assertOptimizedEquals("'+' LIKE '+'", "true");
        assertOptimizedEquals("'(' LIKE '('", "true");
        assertOptimizedEquals("')' LIKE ')'", "true");
        assertOptimizedEquals("'|' LIKE '|'", "true");
        assertOptimizedEquals("'^' LIKE '^'", "true");
        assertOptimizedEquals("'$' LIKE '$'", "true");

        assertOptimizedEquals("null like '%'", "null");
        assertOptimizedEquals("'a' like null", "null");
        assertOptimizedEquals("'a' like '%' escape null", "null");

        assertOptimizedEquals("'%' like 'z%' escape 'z'", "true");
    }

    @Test
    public void testLikeOptimization()
            throws Exception
    {
        assertOptimizedEquals("unbound_string like 'abc'", "unbound_string = 'abc'");

        assertOptimizedEquals("bound_string like bound_pattern", "true");
        assertOptimizedEquals("'abc' like bound_pattern", "false");

        assertOptimizedEquals("unbound_string like bound_pattern", "unbound_string like bound_pattern");

        assertOptimizedEquals("unbound_string like unbound_pattern escape unbound_string", "unbound_string like unbound_pattern escape unbound_string");
    }

    @Test
    public void testFailedExpressionOptimization()
            throws Exception
    {
        assertOptimizedEquals("if(unbound_boolean, 1, 0 / 0)", "CASE WHEN unbound_boolean THEN 1 ELSE 0 / 0 END");
        assertOptimizedEquals("if(unbound_boolean, 0 / 0, 1)", "CASE WHEN unbound_boolean THEN 0 / 0 ELSE 1 END");
        assertOptimizedEqualsSelf("case unbound_long when 1 then 1 when 0 / 0 then 2 end");
        assertOptimizedEqualsSelf("case unbound_boolean when true then 1 else 0 / 0 end");
        assertOptimizedEqualsSelf("case unbound_boolean when true then 0 / 0 else 1 end");
        assertOptimizedEqualsSelf("case when unbound_boolean then 1 when 0 / 0 = 0 then 2 end");
        assertOptimizedEqualsSelf("case when unbound_boolean then 1 else 0 / 0  end");
        assertOptimizedEqualsSelf("case when unbound_boolean then 0 / 0 else 1 end");
        assertOptimizedEqualsSelf("coalesce(unbound_boolean, 0 / 0 = 0)");
    }

    @Test(expectedExceptions = PrestoException.class)
    public void testOptimizeDivideByZero()
            throws Exception
    {
        optimize("0 / 0");
    }

    @Test(expectedExceptions = PrestoException.class)
    public void testOptimizeConstantIfDivideByZero()
            throws Exception
    {
        optimize("if(false, 1, 0 / 0)");
    }

    @Test(expectedExceptions = PrestoException.class)
    public void testOptimizeConstantSearchedCaseDivideByZero()
            throws Exception
    {
        optimize("case when 0 / 0 = 0 then 1 end");
    }

    @Test(timeOut = 60000)
    public void testLikeInvalidUtf8()
    {
        assertLike(new byte[] {'a', 'b', 'c'}, "%b%", true);
        assertLike(new byte[] {'a', 'b', 'c', (byte) 0xFF, 'x', 'y'}, "%b%", true);
    }

    @Test
    public void testLiterals()
    {
        optimize("date '2013-04-03' + unbound_interval");
        optimize("time '03:04:05.321' + unbound_interval");
        optimize("time '03:04:05.321 UTC' + unbound_interval");
        optimize("timestamp '2013-04-03 03:04:05.321' + unbound_interval");
        optimize("timestamp '2013-04-03 03:04:05.321 UTC' + unbound_interval");

        optimize("interval '3' day * unbound_long");
        optimize("interval '3' year * unbound_long");
    }

    private static void assertLike(byte[] value, String pattern, boolean expected)
    {
        Expression predicate = new LikePredicate(
                rawStringLiteral(Slices.wrappedBuffer(value)),
                new StringLiteral(pattern),
                null);
        assertEquals(evaluate(predicate), expected);
    }

    private static StringLiteral rawStringLiteral(final Slice slice)
    {
        return new StringLiteral(slice.toString(UTF_8))
        {
            @Override
            public Slice getSlice()
            {
                return slice;
            }
        };
    }

    private static void assertOptimizedEquals(@Language("SQL") String actual, @Language("SQL") String expected)
    {
        assertEquals(optimize(actual), optimize(expected));
    }

    private static void assertOptimizedEqualsSelf(@Language("SQL") String expression)
    {
        assertEquals(optimize(expression), SQL_PARSER.createExpression(expression));
    }

    private static Object optimize(@Language("SQL") String expression)
    {
        assertRoundTrip(expression);

        Expression parsedExpression = FunctionAssertions.createExpression(expression, METADATA, SYMBOL_TYPES);

        IdentityHashMap<Expression, Type> expressionTypes = getExpressionTypes(TEST_SESSION, METADATA, SQL_PARSER, SYMBOL_TYPES, parsedExpression);
        ExpressionInterpreter interpreter = expressionOptimizer(parsedExpression, METADATA, TEST_SESSION, expressionTypes);
        return interpreter.optimize(new SymbolResolver()
        {
            @Override
            public Object getValue(Symbol symbol)
            {
                switch (symbol.getName().toLowerCase(ENGLISH)) {
                    case "bound_long":
                        return 1234L;
                    case "bound_string":
                        return Slices.wrappedBuffer("hello".getBytes(UTF_8));
                    case "bound_double":
                        return 12.34;
                    case "bound_date":
                        return new LocalDate(2001, 8, 22).toDateMidnight(DateTimeZone.UTC).getMillis();
                    case "bound_time":
                        return new LocalTime(3, 4, 5, 321).toDateTime(new DateTime(0, DateTimeZone.UTC)).getMillis();
                    case "bound_timestamp":
                        return new DateTime(2001, 8, 22, 3, 4, 5, 321, DateTimeZone.UTC).getMillis();
                    case "bound_pattern":
                        return Slices.wrappedBuffer("%el%".getBytes(UTF_8));
                }

                return new QualifiedNameReference(symbol.toQualifiedName());
            }
        });
    }

    private static Object evaluate(String expression)
    {
        assertRoundTrip(expression);

        Expression parsedExpression = FunctionAssertions.createExpression(expression, METADATA, SYMBOL_TYPES);

        return evaluate(parsedExpression);
    }

    private static void assertRoundTrip(String expression)
    {
        assertEquals(SQL_PARSER.createExpression(expression),
                SQL_PARSER.createExpression(formatExpression(SQL_PARSER.createExpression(expression))));
    }

    private static Object evaluate(Expression expression)
    {
        IdentityHashMap<Expression, Type> expressionTypes = getExpressionTypes(TEST_SESSION, METADATA, SQL_PARSER, SYMBOL_TYPES, expression);
        ExpressionInterpreter interpreter = expressionInterpreter(expression, METADATA, TEST_SESSION, expressionTypes);

        return interpreter.evaluate((RecordCursor) null);
    }
}
