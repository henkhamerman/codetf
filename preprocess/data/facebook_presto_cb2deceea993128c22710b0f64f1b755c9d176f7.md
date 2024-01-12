Refactoring Types: ['Move Method']
om/facebook/presto/sql/ExpressionUtils.java
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

import com.facebook.presto.sql.planner.DependencyExtractor;
import com.facebook.presto.sql.planner.DeterminismEvaluator;
import com.facebook.presto.sql.planner.Symbol;
import com.facebook.presto.sql.tree.Expression;
import com.facebook.presto.sql.tree.IsNullPredicate;
import com.facebook.presto.sql.tree.LogicalBinaryExpression;
import com.facebook.presto.sql.tree.QualifiedNameReference;
import com.google.common.base.Function;
import com.google.common.base.Preconditions;
import com.google.common.base.Predicate;
import com.google.common.base.Predicates;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Iterables;

import java.util.Arrays;
import java.util.Iterator;
import java.util.List;

import static com.facebook.presto.sql.tree.BooleanLiteral.FALSE_LITERAL;
import static com.facebook.presto.sql.tree.BooleanLiteral.TRUE_LITERAL;
import static com.facebook.presto.util.ImmutableCollectors.toImmutableList;
import static com.google.common.base.Predicates.not;
import static com.google.common.collect.Iterables.filter;

public final class ExpressionUtils
{
    private ExpressionUtils() {}

    public static List<Expression> extractConjuncts(Expression expression)
    {
        if (expression instanceof LogicalBinaryExpression && ((LogicalBinaryExpression) expression).getType() == LogicalBinaryExpression.Type.AND) {
            LogicalBinaryExpression and = (LogicalBinaryExpression) expression;
            return ImmutableList.<Expression>builder()
                    .addAll(extractConjuncts(and.getLeft()))
                    .addAll(extractConjuncts(and.getRight()))
                    .build();
        }

        return ImmutableList.of(expression);
    }

    public static List<Expression> extractDisjuncts(Expression expression)
    {
        if (expression instanceof LogicalBinaryExpression && ((LogicalBinaryExpression) expression).getType() == LogicalBinaryExpression.Type.OR) {
            LogicalBinaryExpression or = (LogicalBinaryExpression) expression;
            return ImmutableList.<Expression>builder()
                    .addAll(extractDisjuncts(or.getLeft()))
                    .addAll(extractDisjuncts(or.getRight()))
                    .build();
        }

        return ImmutableList.of(expression);
    }

    public static Expression and(Expression... expressions)
    {
        return and(Arrays.asList(expressions));
    }

    public static Expression and(Iterable<Expression> expressions)
    {
        return binaryExpression(LogicalBinaryExpression.Type.AND, expressions);
    }

    public static Expression or(Expression... expressions)
    {
        return or(Arrays.asList(expressions));
    }

    public static Expression or(Iterable<Expression> expressions)
    {
        return binaryExpression(LogicalBinaryExpression.Type.OR, expressions);
    }

    public static Expression binaryExpression(LogicalBinaryExpression.Type type, Iterable<Expression> expressions)
    {
        Preconditions.checkNotNull(type, "type is null");
        Preconditions.checkNotNull(expressions, "expressions is null");
        Preconditions.checkArgument(!Iterables.isEmpty(expressions), "expressions is empty");

        Iterator<Expression> iterator = expressions.iterator();

        Expression result = iterator.next();
        while (iterator.hasNext()) {
            result = new LogicalBinaryExpression(type, result, iterator.next());
        }

        return result;
    }

    public static Expression combineConjuncts(Expression... expressions)
    {
        return combineConjuncts(Arrays.asList(expressions));
    }

    public static Expression combineConjuncts(Iterable<Expression> expressions)
    {
        return combineConjunctsWithDefault(expressions, TRUE_LITERAL);
    }

    public static Expression combineConjunctsWithDefault(Iterable<Expression> expressions, Expression emptyDefault)
    {
        Preconditions.checkNotNull(expressions, "expressions is null");

        // Flatten all the expressions into their component conjuncts
        expressions = Iterables.concat(Iterables.transform(expressions, ExpressionUtils::extractConjuncts));

        // Strip out all true literal conjuncts
        expressions = Iterables.filter(expressions, not(Predicates.<Expression>equalTo(TRUE_LITERAL)));
        expressions = removeDuplicates(expressions);
        return Iterables.isEmpty(expressions) ? emptyDefault : and(expressions);
    }

    public static Expression combineDisjuncts(Expression... expressions)
    {
        return combineDisjuncts(Arrays.asList(expressions));
    }

    public static Expression combineDisjuncts(Iterable<Expression> expressions)
    {
        return combineDisjunctsWithDefault(expressions, FALSE_LITERAL);
    }

    public static Expression combineDisjunctsWithDefault(Iterable<Expression> expressions, Expression emptyDefault)
    {
        Preconditions.checkNotNull(expressions, "expressions is null");

        // Flatten all the expressions into their component disjuncts
        expressions = Iterables.concat(Iterables.transform(expressions, ExpressionUtils::extractDisjuncts));

        // Strip out all false literal disjuncts
        expressions = Iterables.filter(expressions, not(Predicates.<Expression>equalTo(FALSE_LITERAL)));
        expressions = removeDuplicates(expressions);
        return Iterables.isEmpty(expressions) ? emptyDefault : or(expressions);
    }

    public static Expression stripNonDeterministicConjuncts(Expression expression)
    {
        return combineConjuncts(filter(extractConjuncts(expression), DeterminismEvaluator::isDeterministic));
    }

    public static Expression stripDeterministicConjuncts(Expression expression)
    {
        return combineConjuncts(extractConjuncts(expression)
                .stream()
                .filter((conjunct) -> !DeterminismEvaluator.isDeterministic(conjunct))
                .collect(toImmutableList()));
    }

    public static Function<Expression, Expression> expressionOrNullSymbols(final Predicate<Symbol>... nullSymbolScopes)
    {
        return expression -> {
            ImmutableList.Builder<Expression> resultDisjunct = ImmutableList.builder();
            resultDisjunct.add(expression);

            for (Predicate<Symbol> nullSymbolScope : nullSymbolScopes) {
                Iterable<Symbol> symbols = filter(DependencyExtractor.extractUnique(expression), nullSymbolScope);
                if (Iterables.isEmpty(symbols)) {
                    continue;
                }

                ImmutableList.Builder<Expression> nullConjuncts = ImmutableList.builder();
                for (Symbol symbol : symbols) {
                    nullConjuncts.add(new IsNullPredicate(new QualifiedNameReference(symbol.toQualifiedName())));
                }

                resultDisjunct.add(and(nullConjuncts.build()));
            }

            return or(resultDisjunct.build());
        };
    }

    private static Iterable<Expression> removeDuplicates(Iterable<Expression> expressions)
    {
        // Capture all non-deterministic predicates
        Iterable<Expression> nonDeterministicDisjuncts = Iterables.filter(expressions, not(DeterminismEvaluator::isDeterministic));

        // Capture and de-dupe all deterministic predicates
        Iterable<Expression> deterministicDisjuncts = ImmutableSet.copyOf(Iterables.filter(expressions, DeterminismEvaluator::isDeterministic));

        return Iterables.concat(nonDeterministicDisjuncts, deterministicDisjuncts);
    }
}


File: presto-main/src/main/java/com/facebook/presto/sql/planner/DomainTranslator.java
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
import com.facebook.presto.metadata.Metadata;
import com.facebook.presto.spi.ConnectorSession;
import com.facebook.presto.spi.Domain;
import com.facebook.presto.spi.Marker;
import com.facebook.presto.spi.Range;
import com.facebook.presto.spi.SortedRangeSet;
import com.facebook.presto.spi.TupleDomain;
import com.facebook.presto.spi.type.DoubleType;
import com.facebook.presto.spi.type.Type;
import com.facebook.presto.sql.tree.AstVisitor;
import com.facebook.presto.sql.tree.BetweenPredicate;
import com.facebook.presto.sql.tree.BooleanLiteral;
import com.facebook.presto.sql.tree.ComparisonExpression;
import com.facebook.presto.sql.tree.DoubleLiteral;
import com.facebook.presto.sql.tree.Expression;
import com.facebook.presto.sql.tree.FunctionCall;
import com.facebook.presto.sql.tree.InListExpression;
import com.facebook.presto.sql.tree.InPredicate;
import com.facebook.presto.sql.tree.IsNotNullPredicate;
import com.facebook.presto.sql.tree.IsNullPredicate;
import com.facebook.presto.sql.tree.Literal;
import com.facebook.presto.sql.tree.LogicalBinaryExpression;
import com.facebook.presto.sql.tree.LongLiteral;
import com.facebook.presto.sql.tree.NotExpression;
import com.facebook.presto.sql.tree.NullLiteral;
import com.facebook.presto.sql.tree.QualifiedNameReference;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.math.DoubleMath;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static com.facebook.presto.metadata.FunctionRegistry.getMagicLiteralFunctionSignature;
import static com.facebook.presto.spi.type.BigintType.BIGINT;
import static com.facebook.presto.spi.type.DateType.DATE;
import static com.facebook.presto.spi.type.TimestampType.TIMESTAMP;
import static com.facebook.presto.sql.ExpressionUtils.and;
import static com.facebook.presto.sql.ExpressionUtils.combineConjuncts;
import static com.facebook.presto.sql.ExpressionUtils.combineDisjunctsWithDefault;
import static com.facebook.presto.sql.ExpressionUtils.or;
import static com.facebook.presto.sql.planner.LiteralInterpreter.toExpression;
import static com.facebook.presto.sql.tree.BooleanLiteral.FALSE_LITERAL;
import static com.facebook.presto.sql.tree.BooleanLiteral.TRUE_LITERAL;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.EQUAL;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.GREATER_THAN;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.GREATER_THAN_OR_EQUAL;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.LESS_THAN;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.LESS_THAN_OR_EQUAL;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.NOT_EQUAL;
import static com.google.common.base.Preconditions.checkArgument;
import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.base.Preconditions.checkState;
import static com.google.common.collect.Iterables.getOnlyElement;
import static com.google.common.primitives.Primitives.wrap;
import static java.math.RoundingMode.CEILING;
import static java.math.RoundingMode.FLOOR;

public final class DomainTranslator
{
    private static final String DATE_LITERAL = getMagicLiteralFunctionSignature(DATE).getName();
    private static final String TIMESTAMP_LITERAL = getMagicLiteralFunctionSignature(TIMESTAMP).getName();

    private DomainTranslator()
    {
    }

    public static Expression toPredicate(TupleDomain<Symbol> tupleDomain, Map<Symbol, Type> symbolTypes)
    {
        if (tupleDomain.isNone()) {
            return FALSE_LITERAL;
        }
        ImmutableList.Builder<Expression> conjunctBuilder = ImmutableList.builder();
        for (Map.Entry<Symbol, Domain> entry : tupleDomain.getDomains().entrySet()) {
            Symbol symbol = entry.getKey();
            QualifiedNameReference reference = new QualifiedNameReference(symbol.toQualifiedName());
            Type type = symbolTypes.get(symbol);
            conjunctBuilder.add(toPredicate(entry.getValue(), reference, type));
        }
        return combineConjuncts(conjunctBuilder.build());
    }

    private static Expression toPredicate(Domain domain, QualifiedNameReference reference, Type type)
    {
        if (domain.getRanges().isNone()) {
            return domain.isNullAllowed() ? new IsNullPredicate(reference) : FALSE_LITERAL;
        }

        if (domain.getRanges().isAll()) {
            return domain.isNullAllowed() ? TRUE_LITERAL : new NotExpression(new IsNullPredicate(reference));
        }

        // Add disjuncts for ranges
        List<Expression> disjuncts = new ArrayList<>();
        List<Expression> singleValues = new ArrayList<>();
        for (Range range : domain.getRanges()) {
            checkState(!range.isAll()); // Already checked
            if (range.isSingleValue()) {
                singleValues.add(toExpression(range.getLow().getValue(), type));
            }
            else if (isBetween(range)) {
                // Specialize the range with BETWEEN expression if possible b/c it is currently more efficient
                disjuncts.add(new BetweenPredicate(reference, toExpression(range.getLow().getValue(), type), toExpression(range.getHigh().getValue(), type)));
            }
            else {
                List<Expression> rangeConjuncts = new ArrayList<>();
                if (!range.getLow().isLowerUnbounded()) {
                    switch (range.getLow().getBound()) {
                        case ABOVE:
                            rangeConjuncts.add(new ComparisonExpression(GREATER_THAN, reference, toExpression(range.getLow().getValue(), type)));
                            break;
                        case EXACTLY:
                            rangeConjuncts.add(new ComparisonExpression(GREATER_THAN_OR_EQUAL, reference, toExpression(range.getLow().getValue(),
                                    type)));
                            break;
                        case BELOW:
                            throw new IllegalStateException("Low Marker should never use BELOW bound: " + range);
                        default:
                            throw new AssertionError("Unhandled bound: " + range.getLow().getBound());
                    }
                }
                if (!range.getHigh().isUpperUnbounded()) {
                    switch (range.getHigh().getBound()) {
                        case ABOVE:
                            throw new IllegalStateException("High Marker should never use ABOVE bound: " + range);
                        case EXACTLY:
                            rangeConjuncts.add(new ComparisonExpression(LESS_THAN_OR_EQUAL, reference, toExpression(range.getHigh().getValue(), type)));
                            break;
                        case BELOW:
                            rangeConjuncts.add(new ComparisonExpression(LESS_THAN, reference, toExpression(range.getHigh().getValue(), type)));
                            break;
                        default:
                            throw new AssertionError("Unhandled bound: " + range.getHigh().getBound());
                    }
                }
                // If rangeConjuncts is null, then the range was ALL, which should already have been checked for
                checkState(!rangeConjuncts.isEmpty());
                disjuncts.add(combineConjuncts(rangeConjuncts));
            }
        }

        // Add back all of the possible single values either as an equality or an IN predicate
        if (singleValues.size() == 1) {
            disjuncts.add(new ComparisonExpression(EQUAL, reference, getOnlyElement(singleValues)));
        }
        else if (singleValues.size() > 1) {
            disjuncts.add(new InPredicate(reference, new InListExpression(singleValues)));
        }

        // Add nullability disjuncts
        checkState(!disjuncts.isEmpty());
        if (domain.isNullAllowed()) {
            disjuncts.add(new IsNullPredicate(reference));
        }
        return combineDisjunctsWithDefault(disjuncts, TRUE_LITERAL);
    }

    private static boolean isBetween(Range range)
    {
        return !range.getLow().isLowerUnbounded() && range.getLow().getBound() == Marker.Bound.EXACTLY
                && !range.getHigh().isUpperUnbounded() && range.getHigh().getBound() == Marker.Bound.EXACTLY;
    }

    /**
     * Convert an Expression predicate into an ExtractionResult consisting of:
     * 1) A successfully extracted TupleDomain
     * 2) An Expression fragment which represents the part of the original Expression that will need to be re-evaluated
     * after filtering with the TupleDomain.
     */
    public static ExtractionResult fromPredicate(
            Metadata metadata,
            Session session,
            Expression predicate,
            Map<Symbol, Type> types)
    {
        return new Visitor(metadata, session, types).process(predicate, false);
    }

    private static class Visitor
            extends AstVisitor<ExtractionResult, Boolean>
    {
        private final Metadata metadata;
        private final ConnectorSession session;
        private final Map<Symbol, Type> types;

        private Visitor(Metadata metadata, Session session, Map<Symbol, Type> types)
        {
            this.metadata = checkNotNull(metadata, "metadata is null");
            this.session = checkNotNull(session, "session is null").toConnectorSession();
            this.types = ImmutableMap.copyOf(checkNotNull(types, "types is null"));
        }

        private Type checkedTypeLookup(Symbol symbol)
        {
            Type type = types.get(symbol);
            checkArgument(type != null, "Types is missing info for symbol: %s", symbol);
            return type;
        }

        private static SortedRangeSet complementIfNecessary(SortedRangeSet range, boolean complement)
        {
            return complement ? range.complement() : range;
        }

        private static Domain complementIfNecessary(Domain domain, boolean complement)
        {
            return complement ? domain.complement() : domain;
        }

        private static Expression complementIfNecessary(Expression expression, boolean complement)
        {
            return complement ? new NotExpression(expression) : expression;
        }

        @Override
        protected ExtractionResult visitExpression(Expression node, Boolean complement)
        {
            // If we don't know how to process this node, the default response is to say that the TupleDomain is "all"
            return new ExtractionResult(TupleDomain.all(), complementIfNecessary(node, complement));
        }

        @Override
        protected ExtractionResult visitLogicalBinaryExpression(LogicalBinaryExpression node, Boolean complement)
        {
            ExtractionResult leftResult = process(node.getLeft(), complement);
            ExtractionResult rightResult = process(node.getRight(), complement);

            LogicalBinaryExpression.Type type = complement ? flipLogicalBinaryType(node.getType()) : node.getType();
            switch (type) {
                case AND:
                    return new ExtractionResult(
                            leftResult.getTupleDomain().intersect(rightResult.getTupleDomain()),
                            combineConjuncts(leftResult.getRemainingExpression(), rightResult.getRemainingExpression()));

                case OR:
                    TupleDomain<Symbol> columnUnionedTupleDomain = TupleDomain.columnWiseUnion(leftResult.getTupleDomain(), rightResult.getTupleDomain());

                    // In most cases, the columnUnionedTupleDomain is only a superset of the actual strict union
                    // and so we can return the current node as the remainingExpression so that all bounds will be double checked again at execution time.
                    Expression remainingExpression = complementIfNecessary(node, complement);

                    // However, there are a few cases where the column-wise union is actually equivalent to the strict union, so we if can detect
                    // some of these cases, we won't have to double check the bounds unnecessarily at execution time.

                    // We can only make inferences if the remaining expressions on both side are equal and deterministic
                    if (leftResult.getRemainingExpression().equals(rightResult.getRemainingExpression()) &&
                            DeterminismEvaluator.isDeterministic(leftResult.getRemainingExpression())) {
                        // The column-wise union is equivalent to the strict union if
                        // 1) If both TupleDomains consist of the same exact single column (e.g. left TupleDomain => (a > 0), right TupleDomain => (a < 10))
                        // 2) If one TupleDomain is a superset of the other (e.g. left TupleDomain => (a > 0, b > 0 && b < 10), right TupleDomain => (a > 5, b = 5))
                        boolean matchingSingleSymbolDomains = !leftResult.getTupleDomain().isNone()
                                && !rightResult.getTupleDomain().isNone()
                                && leftResult.getTupleDomain().getDomains().size() == 1
                                && rightResult.getTupleDomain().getDomains().size() == 1
                                && leftResult.getTupleDomain().getDomains().keySet().equals(rightResult.getTupleDomain().getDomains().keySet());
                        boolean oneSideIsSuperSet = leftResult.getTupleDomain().contains(rightResult.getTupleDomain()) || rightResult.getTupleDomain().contains(leftResult.getTupleDomain());

                        if (matchingSingleSymbolDomains || oneSideIsSuperSet) {
                            remainingExpression = leftResult.getRemainingExpression();
                        }
                    }

                    return new ExtractionResult(columnUnionedTupleDomain, remainingExpression);

                default:
                    throw new AssertionError("Unknown type: " + node.getType());
            }
        }

        private static LogicalBinaryExpression.Type flipLogicalBinaryType(LogicalBinaryExpression.Type type)
        {
            switch (type) {
                case AND:
                    return LogicalBinaryExpression.Type.OR;
                case OR:
                    return LogicalBinaryExpression.Type.AND;
                default:
                    throw new AssertionError("Unknown type: " + type);
            }
        }

        @Override
        protected ExtractionResult visitNotExpression(NotExpression node, Boolean complement)
        {
            return process(node.getValue(), !complement);
        }

        @Override
        protected ExtractionResult visitComparisonExpression(ComparisonExpression node, Boolean complement)
        {
            if (isSimpleMagicLiteralComparison(node)) {
                node = normalizeSimpleComparison(node);
                node = convertMagicLiteralComparison(node);
            }
            else if (isSimpleComparison(node)) {
                node = normalizeSimpleComparison(node);
            }
            else {
                return super.visitComparisonExpression(node, complement);
            }

            Symbol symbol = Symbol.fromQualifiedName(((QualifiedNameReference) node.getLeft()).getName());
            Type columnType = checkedTypeLookup(symbol);
            Object value = LiteralInterpreter.evaluate(metadata, session, node.getRight());

            // Handle the cases where implicit coercions can happen in comparisons
            // TODO: how to abstract this out
            if (value instanceof Double && columnType.equals(BIGINT)) {
                return process(coerceDoubleToLongComparison(node), complement);
            }
            if (value instanceof Long && columnType.equals(DoubleType.DOUBLE)) {
                value = ((Long) value).doubleValue();
            }
            verifyType(columnType, value);
            return createComparisonExtractionResult(node.getType(), symbol, columnType, objectToComparable(value), complement);
        }

        private ExtractionResult createComparisonExtractionResult(ComparisonExpression.Type comparisonType, Symbol column, Type columnType, Comparable<?> value, boolean complement)
        {
            if (value == null) {
                switch (comparisonType) {
                    case EQUAL:
                    case GREATER_THAN:
                    case GREATER_THAN_OR_EQUAL:
                    case LESS_THAN:
                    case LESS_THAN_OR_EQUAL:
                    case NOT_EQUAL:
                        return new ExtractionResult(TupleDomain.none(), TRUE_LITERAL);

                    case IS_DISTINCT_FROM:
                        Domain domain = complementIfNecessary(Domain.notNull(wrap(columnType.getJavaType())), complement);
                        return new ExtractionResult(
                                TupleDomain.withColumnDomains(ImmutableMap.of(column, domain)),
                                TRUE_LITERAL);

                    default:
                        throw new AssertionError("Unhandled type: " + comparisonType);
                }
            }

            Domain domain;
            switch (comparisonType) {
                case EQUAL:
                    domain = Domain.create(complementIfNecessary(SortedRangeSet.of(Range.equal(value)), complement), false);
                    break;
                case GREATER_THAN:
                    domain = Domain.create(complementIfNecessary(SortedRangeSet.of(Range.greaterThan(value)), complement), false);
                    break;
                case GREATER_THAN_OR_EQUAL:
                    domain = Domain.create(complementIfNecessary(SortedRangeSet.of(Range.greaterThanOrEqual(value)), complement), false);
                    break;
                case LESS_THAN:
                    domain = Domain.create(complementIfNecessary(SortedRangeSet.of(Range.lessThan(value)), complement), false);
                    break;
                case LESS_THAN_OR_EQUAL:
                    domain = Domain.create(complementIfNecessary(SortedRangeSet.of(Range.lessThanOrEqual(value)), complement), false);
                    break;
                case NOT_EQUAL:
                    domain = Domain.create(complementIfNecessary(SortedRangeSet.of(Range.lessThan(value), Range.greaterThan(value)), complement), false);
                    break;
                case IS_DISTINCT_FROM:
                    // Need to potential complement the whole domain for IS_DISTINCT_FROM since it is null-aware
                    domain = complementIfNecessary(Domain.create(SortedRangeSet.of(Range.lessThan(value), Range.greaterThan(value)), true), complement);
                    break;
                default:
                    throw new AssertionError("Unhandled type: " + comparisonType);
            }

            return new ExtractionResult(
                    TupleDomain.withColumnDomains(ImmutableMap.of(column, domain)),
                    TRUE_LITERAL);
        }

        private static void verifyType(Type type, Object value)
        {
            checkState(value == null || wrap(type.getJavaType()).isInstance(value), "Value %s is not of expected type %s", value, type);
        }

        private static Comparable<?> objectToComparable(Object value)
        {
            return (Comparable<?>) value;
        }

        @Override
        protected ExtractionResult visitInPredicate(InPredicate node, Boolean complement)
        {
            if (!(node.getValue() instanceof QualifiedNameReference) || !(node.getValueList() instanceof InListExpression)) {
                return super.visitInPredicate(node, complement);
            }

            InListExpression valueList = (InListExpression) node.getValueList();
            checkState(!valueList.getValues().isEmpty(), "InListExpression should never be empty");

            ImmutableList.Builder<Expression> disjuncts = ImmutableList.builder();
            for (Expression expression : valueList.getValues()) {
                disjuncts.add(new ComparisonExpression(EQUAL, node.getValue(), expression));
            }
            return process(or(disjuncts.build()), complement);
        }

        @Override
        protected ExtractionResult visitBetweenPredicate(BetweenPredicate node, Boolean complement)
        {
            // Re-write as two comparison expressions
            return process(and(
                    new ComparisonExpression(GREATER_THAN_OR_EQUAL, node.getValue(), node.getMin()),
                    new ComparisonExpression(LESS_THAN_OR_EQUAL, node.getValue(), node.getMax())), complement);
        }

        @Override
        protected ExtractionResult visitIsNullPredicate(IsNullPredicate node, Boolean complement)
        {
            if (!(node.getValue() instanceof QualifiedNameReference)) {
                return super.visitIsNullPredicate(node, complement);
            }

            Symbol symbol = Symbol.fromQualifiedName(((QualifiedNameReference) node.getValue()).getName());
            Type columnType = checkedTypeLookup(symbol);
            Domain domain = complementIfNecessary(Domain.onlyNull(wrap(columnType.getJavaType())), complement);
            return new ExtractionResult(
                    TupleDomain.withColumnDomains(ImmutableMap.of(symbol, domain)),
                    TRUE_LITERAL);
        }

        @Override
        protected ExtractionResult visitIsNotNullPredicate(IsNotNullPredicate node, Boolean complement)
        {
            if (!(node.getValue() instanceof QualifiedNameReference)) {
                return super.visitIsNotNullPredicate(node, complement);
            }

            Symbol symbol = Symbol.fromQualifiedName(((QualifiedNameReference) node.getValue()).getName());
            Type columnType = checkedTypeLookup(symbol);

            Domain domain = complementIfNecessary(Domain.notNull(wrap(columnType.getJavaType())), complement);
            return new ExtractionResult(
                    TupleDomain.withColumnDomains(ImmutableMap.of(symbol, domain)),
                    TRUE_LITERAL);
        }

        @Override
        protected ExtractionResult visitBooleanLiteral(BooleanLiteral node, Boolean complement)
        {
            boolean value = complement ? !node.getValue() : node.getValue();
            return new ExtractionResult(value ? TupleDomain.all() : TupleDomain.none(), TRUE_LITERAL);
        }

        @Override
        protected ExtractionResult visitNullLiteral(NullLiteral node, Boolean complement)
        {
            return new ExtractionResult(TupleDomain.none(), TRUE_LITERAL);
        }
    }

    private static boolean isSimpleComparison(ComparisonExpression comparison)
    {
        return (comparison.getLeft() instanceof QualifiedNameReference && comparison.getRight() instanceof Literal) ||
                (comparison.getLeft() instanceof Literal && comparison.getRight() instanceof QualifiedNameReference);
    }

    /**
     * Normalize a simple comparison between a QualifiedNameReference and a Literal such that the QualifiedNameReference will always be on the left and the Literal on the right.
     */
    private static ComparisonExpression normalizeSimpleComparison(ComparisonExpression comparison)
    {
        if (comparison.getLeft() instanceof QualifiedNameReference) {
            return comparison;
        }
        if (comparison.getRight() instanceof QualifiedNameReference) {
            return new ComparisonExpression(flipComparisonDirection(comparison.getType()), comparison.getRight(), comparison.getLeft());
        }
        throw new IllegalArgumentException("ComparisonExpression not a simple literal comparison: " + comparison);
    }

    private static ComparisonExpression.Type flipComparisonDirection(ComparisonExpression.Type type)
    {
        switch (type) {
            case LESS_THAN_OR_EQUAL:
                return GREATER_THAN_OR_EQUAL;
            case LESS_THAN:
                return GREATER_THAN;
            case GREATER_THAN_OR_EQUAL:
                return LESS_THAN_OR_EQUAL;
            case GREATER_THAN:
                return LESS_THAN;
            default:
                // The remaining types have no direction association
                return type;
        }
    }

    private static Expression coerceDoubleToLongComparison(ComparisonExpression comparison)
    {
        comparison = normalizeSimpleComparison(comparison);

        checkArgument(comparison.getLeft() instanceof QualifiedNameReference, "Left must be a QualifiedNameReference");
        checkArgument(comparison.getRight() instanceof DoubleLiteral, "Right must be a DoubleLiteral");

        QualifiedNameReference reference = (QualifiedNameReference) comparison.getLeft();
        Double value = ((DoubleLiteral) comparison.getRight()).getValue();

        switch (comparison.getType()) {
            case GREATER_THAN_OR_EQUAL:
            case LESS_THAN:
                return new ComparisonExpression(comparison.getType(), reference, toExpression(DoubleMath.roundToLong(value, CEILING), BIGINT));

            case GREATER_THAN:
            case LESS_THAN_OR_EQUAL:
                return new ComparisonExpression(comparison.getType(), reference, toExpression(DoubleMath.roundToLong(value, FLOOR), BIGINT));

            case EQUAL:
                Long equalValue = DoubleMath.roundToLong(value, FLOOR);
                if (equalValue.doubleValue() != value) {
                    // Return something that is false for all non-null values
                    return and(new ComparisonExpression(EQUAL, reference, new LongLiteral("0")),
                            new ComparisonExpression(NOT_EQUAL, reference, new LongLiteral("0")));
                }
                return new ComparisonExpression(comparison.getType(), reference, toExpression(equalValue, BIGINT));

            case NOT_EQUAL:
                Long notEqualValue = DoubleMath.roundToLong(value, FLOOR);
                if (notEqualValue.doubleValue() != value) {
                    // Return something that is true for all non-null values
                    return or(new ComparisonExpression(EQUAL, reference, new LongLiteral("0")),
                            new ComparisonExpression(NOT_EQUAL, reference, new LongLiteral("0")));
                }
                return new ComparisonExpression(comparison.getType(), reference, toExpression(notEqualValue, BIGINT));

            case IS_DISTINCT_FROM:
                Long distinctValue = DoubleMath.roundToLong(value, FLOOR);
                if (distinctValue.doubleValue() != value) {
                    return TRUE_LITERAL;
                }
                return new ComparisonExpression(comparison.getType(), reference, toExpression(distinctValue, BIGINT));

            default:
                throw new AssertionError("Unhandled type: " + comparison.getType());
        }
    }

    public static class ExtractionResult
    {
        private final TupleDomain<Symbol> tupleDomain;
        private final Expression remainingExpression;

        public ExtractionResult(TupleDomain<Symbol> tupleDomain, Expression remainingExpression)
        {
            this.tupleDomain = checkNotNull(tupleDomain, "tupleDomain is null");
            this.remainingExpression = checkNotNull(remainingExpression, "remainingExpression is null");
        }

        public TupleDomain<Symbol> getTupleDomain()
        {
            return tupleDomain;
        }

        public Expression getRemainingExpression()
        {
            return remainingExpression;
        }
    }

    // TODO: remove this horrible hack
    private static boolean isSimpleMagicLiteralComparison(ComparisonExpression node)
    {
        FunctionCall call;
        if ((node.getLeft() instanceof QualifiedNameReference) && (node.getRight() instanceof FunctionCall)) {
            call = (FunctionCall) node.getRight();
        }
        else if ((node.getLeft() instanceof FunctionCall) && (node.getRight() instanceof QualifiedNameReference)) {
            call = (FunctionCall) node.getLeft();
        }
        else {
            return false;
        }

        if (call.getName().getPrefix().isPresent()) {
            return false;
        }
        String name = call.getName().getSuffix();

        return name.equals(DATE_LITERAL) || name.equals(TIMESTAMP_LITERAL);
    }

    private static ComparisonExpression convertMagicLiteralComparison(ComparisonExpression node)
    {
        // "magic literal" functions use the stack type value for the argument
        checkArgument(isSimpleMagicLiteralComparison(node), "not a simple magic literal comparison");
        FunctionCall call = (FunctionCall) node.getRight();
        Expression value = call.getArguments().get(0);
        return new ComparisonExpression(node.getType(), node.getLeft(), value);
    }
}


File: presto-main/src/main/java/com/facebook/presto/sql/planner/RelationPlanner.java
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
import com.facebook.presto.metadata.Metadata;
import com.facebook.presto.metadata.Signature;
import com.facebook.presto.metadata.TableHandle;
import com.facebook.presto.spi.ColumnHandle;
import com.facebook.presto.spi.TupleDomain;
import com.facebook.presto.spi.type.Type;
import com.facebook.presto.sql.ExpressionUtils;
import com.facebook.presto.sql.analyzer.Analysis;
import com.facebook.presto.sql.analyzer.AnalysisContext;
import com.facebook.presto.sql.analyzer.ExpressionAnalyzer;
import com.facebook.presto.sql.analyzer.Field;
import com.facebook.presto.sql.analyzer.FieldOrExpression;
import com.facebook.presto.sql.analyzer.SemanticException;
import com.facebook.presto.sql.analyzer.TupleAnalyzer;
import com.facebook.presto.sql.analyzer.TupleDescriptor;
import com.facebook.presto.sql.planner.optimizations.CanonicalizeExpressions;
import com.facebook.presto.sql.planner.plan.AggregationNode;
import com.facebook.presto.sql.planner.plan.FilterNode;
import com.facebook.presto.sql.planner.plan.JoinNode;
import com.facebook.presto.sql.planner.plan.PlanNode;
import com.facebook.presto.sql.planner.plan.ProjectNode;
import com.facebook.presto.sql.planner.plan.SampleNode;
import com.facebook.presto.sql.planner.plan.SemiJoinNode;
import com.facebook.presto.sql.planner.plan.TableScanNode;
import com.facebook.presto.sql.planner.plan.UnionNode;
import com.facebook.presto.sql.planner.plan.UnnestNode;
import com.facebook.presto.sql.planner.plan.ValuesNode;
import com.facebook.presto.sql.tree.AliasedRelation;
import com.facebook.presto.sql.tree.ArithmeticBinaryExpression;
import com.facebook.presto.sql.tree.BooleanLiteral;
import com.facebook.presto.sql.tree.Cast;
import com.facebook.presto.sql.tree.CoalesceExpression;
import com.facebook.presto.sql.tree.ComparisonExpression;
import com.facebook.presto.sql.tree.DefaultTraversalVisitor;
import com.facebook.presto.sql.tree.Expression;
import com.facebook.presto.sql.tree.ExpressionRewriter;
import com.facebook.presto.sql.tree.ExpressionTreeRewriter;
import com.facebook.presto.sql.tree.FunctionCall;
import com.facebook.presto.sql.tree.InPredicate;
import com.facebook.presto.sql.tree.InputReference;
import com.facebook.presto.sql.tree.Join;
import com.facebook.presto.sql.tree.LongLiteral;
import com.facebook.presto.sql.tree.QualifiedName;
import com.facebook.presto.sql.tree.QualifiedNameReference;
import com.facebook.presto.sql.tree.Query;
import com.facebook.presto.sql.tree.QuerySpecification;
import com.facebook.presto.sql.tree.Relation;
import com.facebook.presto.sql.tree.Row;
import com.facebook.presto.sql.tree.SampledRelation;
import com.facebook.presto.sql.tree.SubqueryExpression;
import com.facebook.presto.sql.tree.Table;
import com.facebook.presto.sql.tree.TableSubquery;
import com.facebook.presto.sql.tree.Union;
import com.facebook.presto.sql.tree.Unnest;
import com.facebook.presto.sql.tree.Values;
import com.facebook.presto.type.ArrayType;
import com.facebook.presto.type.MapType;
import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableListMultimap;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Iterables;
import com.google.common.collect.UnmodifiableIterator;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import static com.facebook.presto.spi.type.BigintType.BIGINT;
import static com.facebook.presto.spi.type.BooleanType.BOOLEAN;
import static com.facebook.presto.sql.analyzer.SemanticErrorCode.EXPRESSION_NOT_CONSTANT;
import static com.facebook.presto.sql.analyzer.SemanticErrorCode.NOT_SUPPORTED;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.EQUAL;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.GREATER_THAN;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.GREATER_THAN_OR_EQUAL;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.IS_DISTINCT_FROM;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.LESS_THAN;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.LESS_THAN_OR_EQUAL;
import static com.facebook.presto.sql.tree.ComparisonExpression.Type.NOT_EQUAL;
import static com.facebook.presto.sql.tree.Join.Type.INNER;
import static com.facebook.presto.util.ImmutableCollectors.toImmutableList;
import static com.facebook.presto.util.Types.checkType;
import static com.google.common.base.Preconditions.checkArgument;
import static com.google.common.base.Preconditions.checkState;

class RelationPlanner
        extends DefaultTraversalVisitor<RelationPlan, Void>
{
    private final Analysis analysis;
    private final SymbolAllocator symbolAllocator;
    private final PlanNodeIdAllocator idAllocator;
    private final Metadata metadata;
    private final Session session;

    RelationPlanner(Analysis analysis, SymbolAllocator symbolAllocator, PlanNodeIdAllocator idAllocator, Metadata metadata, Session session)
    {
        Preconditions.checkNotNull(analysis, "analysis is null");
        Preconditions.checkNotNull(symbolAllocator, "symbolAllocator is null");
        Preconditions.checkNotNull(idAllocator, "idAllocator is null");
        Preconditions.checkNotNull(metadata, "metadata is null");
        Preconditions.checkNotNull(session, "session is null");

        this.analysis = analysis;
        this.symbolAllocator = symbolAllocator;
        this.idAllocator = idAllocator;
        this.metadata = metadata;
        this.session = session;
    }

    @Override
    protected RelationPlan visitTable(Table node, Void context)
    {
        Query namedQuery = analysis.getNamedQuery(node);
        if (namedQuery != null) {
            RelationPlan subPlan = process(namedQuery, null);
            return new RelationPlan(subPlan.getRoot(), analysis.getOutputDescriptor(node), subPlan.getOutputSymbols(), subPlan.getSampleWeight());
        }

        TupleDescriptor descriptor = analysis.getOutputDescriptor(node);
        TableHandle handle = analysis.getTableHandle(node);

        ImmutableList.Builder<Symbol> outputSymbolsBuilder = ImmutableList.builder();
        ImmutableMap.Builder<Symbol, ColumnHandle> columns = ImmutableMap.builder();
        for (Field field : descriptor.getAllFields()) {
            Symbol symbol = symbolAllocator.newSymbol(field.getName().get(), field.getType());

            outputSymbolsBuilder.add(symbol);
            columns.put(symbol, analysis.getColumn(field));
        }

        List<Symbol> planOutputSymbols = outputSymbolsBuilder.build();
        Optional<ColumnHandle> sampleWeightColumn = metadata.getSampleWeightColumnHandle(handle);
        Symbol sampleWeightSymbol = null;
        if (sampleWeightColumn.isPresent()) {
            sampleWeightSymbol = symbolAllocator.newSymbol("$sampleWeight", BIGINT);
            outputSymbolsBuilder.add(sampleWeightSymbol);
            columns.put(sampleWeightSymbol, sampleWeightColumn.get());
        }

        List<Symbol> nodeOutputSymbols = outputSymbolsBuilder.build();
        PlanNode root = new TableScanNode(idAllocator.getNextId(), handle, nodeOutputSymbols, columns.build(), Optional.empty(), TupleDomain.all(), null);
        return new RelationPlan(root, descriptor, planOutputSymbols, Optional.ofNullable(sampleWeightSymbol));
    }

    @Override
    protected RelationPlan visitAliasedRelation(AliasedRelation node, Void context)
    {
        RelationPlan subPlan = process(node.getRelation(), context);

        TupleDescriptor outputDescriptor = analysis.getOutputDescriptor(node);

        return new RelationPlan(subPlan.getRoot(), outputDescriptor, subPlan.getOutputSymbols(), subPlan.getSampleWeight());
    }

    @Override
    protected RelationPlan visitSampledRelation(SampledRelation node, Void context)
    {
        if (node.getColumnsToStratifyOn().isPresent()) {
            throw new UnsupportedOperationException("STRATIFY ON is not yet implemented");
        }

        RelationPlan subPlan = process(node.getRelation(), context);

        TupleDescriptor outputDescriptor = analysis.getOutputDescriptor(node);
        double ratio = analysis.getSampleRatio(node);
        Symbol sampleWeightSymbol = null;
        if (node.getType() == SampledRelation.Type.POISSONIZED) {
            sampleWeightSymbol = symbolAllocator.newSymbol("$sampleWeight", BIGINT);
        }
        PlanNode planNode = new SampleNode(idAllocator.getNextId(),
                subPlan.getRoot(),
                ratio,
                SampleNode.Type.fromType(node.getType()),
                node.isRescaled(),
                Optional.ofNullable(sampleWeightSymbol));
        return new RelationPlan(planNode, outputDescriptor, subPlan.getOutputSymbols(), Optional.ofNullable(sampleWeightSymbol));
    }

    @Override
    protected RelationPlan visitJoin(Join node, Void context)
    {
        // TODO: translate the RIGHT join into a mirrored LEFT join when we refactor (@martint)
        RelationPlan leftPlan = process(node.getLeft(), context);

        // Convert CROSS JOIN UNNEST to an UnnestNode
        if (node.getRight() instanceof Unnest || (node.getRight() instanceof AliasedRelation && ((AliasedRelation) node.getRight()).getRelation() instanceof Unnest)) {
            Unnest unnest;
            if (node.getRight() instanceof AliasedRelation) {
                unnest = (Unnest) ((AliasedRelation) node.getRight()).getRelation();
            }
            else {
                unnest = (Unnest) node.getRight();
            }
            if (node.getType() != Join.Type.CROSS && node.getType() != Join.Type.IMPLICIT) {
                throw new SemanticException(NOT_SUPPORTED, unnest, "UNNEST only supported on the right side of CROSS JOIN");
            }
            return planCrossJoinUnnest(leftPlan, node, unnest);
        }

        RelationPlan rightPlan = process(node.getRight(), context);

        PlanBuilder leftPlanBuilder = initializePlanBuilder(leftPlan);
        PlanBuilder rightPlanBuilder = initializePlanBuilder(rightPlan);

        TupleDescriptor outputDescriptor = analysis.getOutputDescriptor(node);

        // NOTE: symbols must be in the same order as the outputDescriptor
        List<Symbol> outputSymbols = ImmutableList.<Symbol>builder()
                .addAll(leftPlan.getOutputSymbols())
                .addAll(rightPlan.getOutputSymbols())
                .build();

        ImmutableList.Builder<JoinNode.EquiJoinClause> equiClauses = ImmutableList.builder();
        Expression postInnerJoinCriteria = new BooleanLiteral("TRUE");
        if (node.getType() != Join.Type.CROSS && node.getType() != Join.Type.IMPLICIT) {
            Expression criteria = analysis.getJoinCriteria(node);

            TupleDescriptor left = analysis.getOutputDescriptor(node.getLeft());
            TupleDescriptor right = analysis.getOutputDescriptor(node.getRight());
            List<Expression> leftExpressions = new ArrayList<>();
            List<Expression> rightExpressions = new ArrayList<>();
            List<ComparisonExpression.Type> comparisonTypes = new ArrayList<>();
            for (Expression conjunct : ExpressionUtils.extractConjuncts(criteria)) {
                if (!(conjunct instanceof ComparisonExpression)) {
                    throw new SemanticException(NOT_SUPPORTED, node, "Unsupported non-equi join form: %s", conjunct);
                }

                ComparisonExpression comparison = (ComparisonExpression) conjunct;
                ComparisonExpression.Type comparisonType = comparison.getType();
                if (comparison.getType() != EQUAL && node.getType() != INNER) {
                    throw new SemanticException(NOT_SUPPORTED, node, "Non-equi joins only supported for inner join: %s", conjunct);
                }
                Set<QualifiedName> firstDependencies = TupleAnalyzer.DependencyExtractor.extract(comparison.getLeft());
                Set<QualifiedName> secondDependencies = TupleAnalyzer.DependencyExtractor.extract(comparison.getRight());

                Expression leftExpression;
                Expression rightExpression;
                if (Iterables.all(firstDependencies, left.canResolvePredicate()) && Iterables.all(secondDependencies, right.canResolvePredicate())) {
                    leftExpression = comparison.getLeft();
                    rightExpression = comparison.getRight();
                }
                else if (Iterables.all(firstDependencies, right.canResolvePredicate()) && Iterables.all(secondDependencies, left.canResolvePredicate())) {
                    leftExpression = comparison.getRight();
                    rightExpression = comparison.getLeft();
                    comparisonType = flipComparison(comparisonType);
                }
                else {
                    // must have a complex expression that involves both tuples on one side of the comparison expression (e.g., coalesce(left.x, right.x) = 1)
                    throw new SemanticException(NOT_SUPPORTED, node, "Unsupported non-equi join form: %s", conjunct);
                }
                leftExpressions.add(leftExpression);
                rightExpressions.add(rightExpression);
                comparisonTypes.add(comparisonType);
            }

            Analysis.JoinInPredicates joinInPredicates = analysis.getJoinInPredicates(node);

            // Add semi joins if necessary
            if (joinInPredicates != null) {
                leftPlanBuilder = appendSemiJoins(leftPlanBuilder, joinInPredicates.getLeftInPredicates());
                rightPlanBuilder = appendSemiJoins(rightPlanBuilder, joinInPredicates.getRightInPredicates());
            }

            // Add projections for join criteria
            leftPlanBuilder = appendProjections(leftPlanBuilder, leftExpressions);
            rightPlanBuilder = appendProjections(rightPlanBuilder, rightExpressions);

            List<Expression> postInnerJoinComparisons = new ArrayList<>();
            for (int i = 0; i < comparisonTypes.size(); i++) {
                Symbol leftSymbol = leftPlanBuilder.translate(leftExpressions.get(i));
                Symbol rightSymbol = rightPlanBuilder.translate(rightExpressions.get(i));

                equiClauses.add(new JoinNode.EquiJoinClause(leftSymbol, rightSymbol));

                Expression leftExpression = leftPlanBuilder.rewrite(leftExpressions.get(i));
                Expression rightExpression = rightPlanBuilder.rewrite(rightExpressions.get(i));
                postInnerJoinComparisons.add(new ComparisonExpression(comparisonTypes.get(i), leftExpression, rightExpression));
            }
            postInnerJoinCriteria = ExpressionUtils.and(postInnerJoinComparisons);
        }

        PlanNode root;
        if (node.getType() == INNER) {
            root = new JoinNode(idAllocator.getNextId(),
                    JoinNode.Type.CROSS,
                    leftPlanBuilder.getRoot(),
                    rightPlanBuilder.getRoot(),
                    ImmutableList.<JoinNode.EquiJoinClause>of(),
                    Optional.empty(),
                    Optional.empty());
            root = new FilterNode(idAllocator.getNextId(), root, postInnerJoinCriteria);
        }
        else {
            root = new JoinNode(idAllocator.getNextId(),
                    JoinNode.Type.typeConvert(node.getType()),
                    leftPlanBuilder.getRoot(),
                    rightPlanBuilder.getRoot(),
                    equiClauses.build(),
                    Optional.empty(),
                    Optional.empty());
        }
        Optional<Symbol> sampleWeight = Optional.empty();
        if (leftPlanBuilder.getSampleWeight().isPresent() || rightPlanBuilder.getSampleWeight().isPresent()) {
            Expression expression = new ArithmeticBinaryExpression(ArithmeticBinaryExpression.Type.MULTIPLY,
                    oneIfNull(leftPlanBuilder.getSampleWeight()),
                    oneIfNull(rightPlanBuilder.getSampleWeight()));
            sampleWeight = Optional.of(symbolAllocator.newSymbol(expression, BIGINT));
            ImmutableMap.Builder<Symbol, Expression> projections = ImmutableMap.builder();
            projections.put(sampleWeight.get(), expression);
            for (Symbol symbol : root.getOutputSymbols()) {
                projections.put(symbol, new QualifiedNameReference(symbol.toQualifiedName()));
            }
            root = new ProjectNode(idAllocator.getNextId(), root, projections.build());
        }

        return new RelationPlan(root, outputDescriptor, outputSymbols, sampleWeight);
    }

    private static ComparisonExpression.Type flipComparison(ComparisonExpression.Type type)
    {
        switch (type) {
            case EQUAL:
                return EQUAL;
            case NOT_EQUAL:
                return NOT_EQUAL;
            case LESS_THAN:
                return GREATER_THAN;
            case LESS_THAN_OR_EQUAL:
                return GREATER_THAN_OR_EQUAL;
            case GREATER_THAN:
                return LESS_THAN;
            case GREATER_THAN_OR_EQUAL:
                return LESS_THAN_OR_EQUAL;
            case IS_DISTINCT_FROM:
                return IS_DISTINCT_FROM;
            default:
                throw new IllegalArgumentException("Unsupported comparison: " + type);
        }
    }

    private RelationPlan planCrossJoinUnnest(RelationPlan leftPlan, Join joinNode, Unnest node)
    {
        TupleDescriptor outputDescriptor = analysis.getOutputDescriptor(joinNode);
        TupleDescriptor unnestOutputDescriptor = analysis.getOutputDescriptor(node);
        // Create symbols for the result of unnesting
        ImmutableList.Builder<Symbol> unnestedSymbolsBuilder = ImmutableList.builder();
        for (Field field : unnestOutputDescriptor.getVisibleFields()) {
            Symbol symbol = symbolAllocator.newSymbol(field);
            unnestedSymbolsBuilder.add(symbol);
        }
        ImmutableList<Symbol> unnestedSymbols = unnestedSymbolsBuilder.build();

        // Add a projection for all the unnest arguments
        PlanBuilder planBuilder = initializePlanBuilder(leftPlan);
        planBuilder = appendProjections(planBuilder, node.getExpressions());
        TranslationMap translations = planBuilder.getTranslations();
        ProjectNode projectNode = checkType(planBuilder.getRoot(), ProjectNode.class, "planBuilder.getRoot()");

        ImmutableMap.Builder<Symbol, List<Symbol>> unnestSymbols = ImmutableMap.builder();
        UnmodifiableIterator<Symbol> unnestedSymbolsIterator = unnestedSymbols.iterator();
        for (Expression expression : node.getExpressions()) {
            Type type = analysis.getType(expression);
            Symbol inputSymbol = translations.get(expression);
            if (type instanceof ArrayType) {
                unnestSymbols.put(inputSymbol, ImmutableList.of(unnestedSymbolsIterator.next()));
            }
            else if (type instanceof MapType) {
                unnestSymbols.put(inputSymbol, ImmutableList.of(unnestedSymbolsIterator.next(), unnestedSymbolsIterator.next()));
            }
            else {
                throw new IllegalArgumentException("Unsupported type for UNNEST: " + type);
            }
        }
        Optional<Symbol> ordinalitySymbol = node.isWithOrdinality() ? Optional.of(unnestedSymbolsIterator.next()) : Optional.empty();
        checkState(!unnestedSymbolsIterator.hasNext(), "Not all output symbols were matched with input symbols");

        UnnestNode unnestNode = new UnnestNode(idAllocator.getNextId(), projectNode, leftPlan.getOutputSymbols(), unnestSymbols.build(), ordinalitySymbol);
        return new RelationPlan(unnestNode, outputDescriptor, unnestNode.getOutputSymbols(), Optional.empty());
    }

    private static Expression oneIfNull(Optional<Symbol> symbol)
    {
        if (symbol.isPresent()) {
            return new CoalesceExpression(new QualifiedNameReference(symbol.get().toQualifiedName()), new LongLiteral("1"));
        }
        else {
            return new LongLiteral("1");
        }
    }

    @Override
    protected RelationPlan visitTableSubquery(TableSubquery node, Void context)
    {
        return process(node.getQuery(), context);
    }

    @Override
    protected RelationPlan visitQuery(Query node, Void context)
    {
        PlanBuilder subPlan = new QueryPlanner(analysis, symbolAllocator, idAllocator, metadata, session).process(node, null);

        ImmutableList.Builder<Symbol> outputSymbols = ImmutableList.builder();
        for (FieldOrExpression fieldOrExpression : analysis.getOutputExpressions(node)) {
            outputSymbols.add(subPlan.translate(fieldOrExpression));
        }

        return new RelationPlan(subPlan.getRoot(), analysis.getOutputDescriptor(node), outputSymbols.build(), subPlan.getSampleWeight());
    }

    @Override
    protected RelationPlan visitQuerySpecification(QuerySpecification node, Void context)
    {
        PlanBuilder subPlan = new QueryPlanner(analysis, symbolAllocator, idAllocator, metadata, session).process(node, null);

        ImmutableList.Builder<Symbol> outputSymbols = ImmutableList.builder();
        for (FieldOrExpression fieldOrExpression : analysis.getOutputExpressions(node)) {
            outputSymbols.add(subPlan.translate(fieldOrExpression));
        }

        return new RelationPlan(subPlan.getRoot(), analysis.getOutputDescriptor(node), outputSymbols.build(), subPlan.getSampleWeight());
    }

    @Override
    protected RelationPlan visitValues(Values node, Void context)
    {
        TupleDescriptor descriptor = analysis.getOutputDescriptor(node);
        ImmutableList.Builder<Symbol> outputSymbolsBuilder = ImmutableList.builder();
        for (Field field : descriptor.getVisibleFields()) {
            Symbol symbol = symbolAllocator.newSymbol(field);
            outputSymbolsBuilder.add(symbol);
        }

        ImmutableList.Builder<List<Expression>> rows = ImmutableList.builder();
        for (Expression row : node.getRows()) {
            ImmutableList.Builder<Expression> values = ImmutableList.builder();
            if (row instanceof Row) {
                List<Expression> items = ((Row) row).getItems();
                for (int i = 0; i < items.size(); i++) {
                    Expression expression = items.get(i);
                    Object constantValue = evaluateConstantExpression(expression);
                    values.add(LiteralInterpreter.toExpression(constantValue, descriptor.getFieldByIndex(i).getType()));
                }
            }
            else {
                Object constantValue = evaluateConstantExpression(row);
                values.add(LiteralInterpreter.toExpression(constantValue, descriptor.getFieldByIndex(0).getType()));
            }

            rows.add(values.build());
        }

        ValuesNode valuesNode = new ValuesNode(idAllocator.getNextId(), outputSymbolsBuilder.build(), rows.build());
        return new RelationPlan(valuesNode, descriptor, outputSymbolsBuilder.build(), Optional.empty());
    }

    @Override
    protected RelationPlan visitUnnest(Unnest node, Void context)
    {
        TupleDescriptor descriptor = analysis.getOutputDescriptor(node);
        ImmutableList.Builder<Symbol> outputSymbolsBuilder = ImmutableList.builder();
        for (Field field : descriptor.getVisibleFields()) {
            Symbol symbol = symbolAllocator.newSymbol(field);
            outputSymbolsBuilder.add(symbol);
        }
        List<Symbol> unnestedSymbols = outputSymbolsBuilder.build();

        // If we got here, then we must be unnesting a constant, and not be in a join (where there could be column references)
        ImmutableList.Builder<Symbol> argumentSymbols = ImmutableList.builder();
        ImmutableList.Builder<Expression> values = ImmutableList.builder();
        ImmutableMap.Builder<Symbol, List<Symbol>> unnestSymbols = ImmutableMap.builder();
        Iterator<Symbol> unnestedSymbolsIterator = unnestedSymbols.iterator();
        for (Expression expression : node.getExpressions()) {
            Object constantValue = evaluateConstantExpression(expression);
            Type type = analysis.getType(expression);
            values.add(LiteralInterpreter.toExpression(constantValue, type));
            Symbol inputSymbol = symbolAllocator.newSymbol(expression, type);
            argumentSymbols.add(inputSymbol);
            if (type instanceof ArrayType) {
                unnestSymbols.put(inputSymbol, ImmutableList.of(unnestedSymbolsIterator.next()));
            }
            else if (type instanceof MapType) {
                unnestSymbols.put(inputSymbol, ImmutableList.of(unnestedSymbolsIterator.next(), unnestedSymbolsIterator.next()));
            }
            else {
                throw new IllegalArgumentException("Unsupported type for UNNEST: " + type);
            }
        }
        Optional<Symbol> ordinalitySymbol = node.isWithOrdinality() ? Optional.of(unnestedSymbolsIterator.next()) : Optional.empty();
        checkState(!unnestedSymbolsIterator.hasNext(), "Not all output symbols were matched with input symbols");
        ValuesNode valuesNode = new ValuesNode(idAllocator.getNextId(), argumentSymbols.build(), ImmutableList.<List<Expression>>of(values.build()));

        UnnestNode unnestNode = new UnnestNode(idAllocator.getNextId(), valuesNode, ImmutableList.<Symbol>of(), unnestSymbols.build(), ordinalitySymbol);
        return new RelationPlan(unnestNode, descriptor, unnestedSymbols, Optional.empty());
    }

    private Object evaluateConstantExpression(Expression expression)
    {
        // verify expression is constant
        expression.accept(new DefaultTraversalVisitor<Void, Void>()
        {
            @Override
            protected Void visitQualifiedNameReference(QualifiedNameReference node, Void context)
            {
                throw new SemanticException(EXPRESSION_NOT_CONSTANT, expression, "Constant expression cannot contain column references");
            }

            @Override
            protected Void visitInputReference(InputReference node, Void context)
            {
                throw new SemanticException(EXPRESSION_NOT_CONSTANT, expression, "Constant expression cannot contain input references");
            }
        }, null);

        // add coercions
        Expression rewrite = ExpressionTreeRewriter.rewriteWith(new ExpressionRewriter<Void>()
        {
            @Override
            public Expression rewriteExpression(Expression node, Void context, ExpressionTreeRewriter<Void> treeRewriter)
            {
                Expression rewrittenExpression = treeRewriter.defaultRewrite(node, context);

                // cast expression if coercion is registered
                Type coercion = analysis.getCoercion(node);
                if (coercion != null) {
                    rewrittenExpression = new Cast(rewrittenExpression, coercion.getTypeSignature().toString());
                }

                return rewrittenExpression;
            }
        }, expression);

        try {
            // expressionInterpreter/optimizer only understands a subset of expression types
            // TODO: remove this when the new expression tree is implemented
            Expression canonicalized = CanonicalizeExpressions.canonicalizeExpression(rewrite);

            // The optimization above may have rewritten the expression tree which breaks all the identity maps, so redo the analysis
            // to re-analyze coercions that might be necessary
            ExpressionAnalyzer analyzer = ExpressionAnalyzer.createWithoutSubqueries(
                    metadata.getFunctionRegistry(),
                    metadata.getTypeManager(),
                    session,
                    EXPRESSION_NOT_CONSTANT,
                    "Constant expression cannot contain as sub-query");
            analyzer.analyze(canonicalized, new TupleDescriptor(), new AnalysisContext());

            // evaluate the expression
            Object result = ExpressionInterpreter.expressionInterpreter(canonicalized, metadata, session, analyzer.getExpressionTypes()).evaluate(0);
            checkState(!(result instanceof Expression), "Expression interpreter returned an unresolved expression");

            return result;
        }
        catch (Exception e) {
            throw new SemanticException(EXPRESSION_NOT_CONSTANT, expression, "Error evaluating constant expression: %s", e.getMessage());
        }
    }

    private RelationPlan processAndCoerceIfNecessary(Relation node, Void context)
    {
        Type[] coerceToTypes = analysis.getRelationCoercion(node);

        RelationPlan plan = node.accept(this, context);

        if (coerceToTypes == null) {
            return plan;
        }

        List<Symbol> oldSymbols = plan.getRoot().getOutputSymbols();
        TupleDescriptor oldDescriptor = plan.getDescriptor().withOnlyVisibleFields();
        checkArgument(coerceToTypes.length == oldSymbols.size());
        ImmutableList.Builder<Symbol> newSymbols = new ImmutableList.Builder<>();
        Field[] newFields = new Field[coerceToTypes.length];
        ImmutableMap.Builder<Symbol, Expression> assignments = new ImmutableMap.Builder<>();
        for (int i = 0; i < coerceToTypes.length; i++) {
            Symbol inputSymbol = oldSymbols.get(i);
            Type inputType = symbolAllocator.getTypes().get(inputSymbol);
            Type outputType = coerceToTypes[i];
            if (outputType != inputType) {
                Cast cast = new Cast(new QualifiedNameReference(inputSymbol.toQualifiedName()), outputType.getTypeSignature().toString());
                Symbol outputSymbol = symbolAllocator.newSymbol(cast, outputType);
                assignments.put(outputSymbol, cast);
                newSymbols.add(outputSymbol);
            }
            else {
                assignments.put(inputSymbol, new QualifiedNameReference(inputSymbol.toQualifiedName()));
                newSymbols.add(inputSymbol);
            }
            Field oldField = oldDescriptor.getFieldByIndex(i);
            newFields[i] = new Field(oldField.getRelationAlias(), oldField.getName(), coerceToTypes[i], oldField.isHidden());
        }
        ProjectNode projectNode = new ProjectNode(idAllocator.getNextId(), plan.getRoot(), assignments.build());
        return new RelationPlan(projectNode, new TupleDescriptor(newFields), newSymbols.build(), plan.getSampleWeight());
    }

    @Override
    protected RelationPlan visitUnion(Union node, Void context)
    {
        checkArgument(!node.getRelations().isEmpty(), "No relations specified for UNION");

        List<Symbol> unionOutputSymbols = null;
        ImmutableList.Builder<PlanNode> sources = ImmutableList.builder();
        ImmutableListMultimap.Builder<Symbol, Symbol> symbolMapping = ImmutableListMultimap.builder();
        List<RelationPlan> subPlans = node.getRelations().stream()
                .map(relation -> processAndCoerceIfNecessary(relation, context))
                .collect(toImmutableList());

        boolean hasSampleWeight = false;
        for (RelationPlan subPlan : subPlans) {
            if (subPlan.getSampleWeight().isPresent()) {
                hasSampleWeight = true;
                break;
            }
        }

        Optional<Symbol> outputSampleWeight = Optional.empty();
        for (RelationPlan relationPlan : subPlans) {
            if (hasSampleWeight && !relationPlan.getSampleWeight().isPresent()) {
                relationPlan = addConstantSampleWeight(relationPlan);
            }

            List<Symbol> childOutputSymbols = relationPlan.getOutputSymbols();
            if (unionOutputSymbols == null) {
                // Use the first Relation to derive output symbol names
                TupleDescriptor descriptor = relationPlan.getDescriptor();
                ImmutableList.Builder<Symbol> outputSymbolBuilder = ImmutableList.builder();
                for (Field field : descriptor.getVisibleFields()) {
                    int fieldIndex = descriptor.indexOf(field);
                    Symbol symbol = childOutputSymbols.get(fieldIndex);
                    outputSymbolBuilder.add(symbolAllocator.newSymbol(symbol.getName(), symbolAllocator.getTypes().get(symbol)));
                }
                unionOutputSymbols = outputSymbolBuilder.build();
                outputSampleWeight = relationPlan.getSampleWeight();
            }

            TupleDescriptor descriptor = relationPlan.getDescriptor();
            checkArgument(descriptor.getVisibleFieldCount() == unionOutputSymbols.size(),
                    "Expected relation to have %s symbols but has %s symbols",
                    descriptor.getVisibleFieldCount(),
                    unionOutputSymbols.size());

            int unionFieldId = 0;
            for (Field field : descriptor.getVisibleFields()) {
                int fieldIndex = descriptor.indexOf(field);
                symbolMapping.put(unionOutputSymbols.get(unionFieldId), childOutputSymbols.get(fieldIndex));
                unionFieldId++;
            }

            sources.add(relationPlan.getRoot());
        }

        PlanNode planNode = new UnionNode(idAllocator.getNextId(), sources.build(), symbolMapping.build());
        if (node.isDistinct()) {
            planNode = distinct(planNode);
        }
        return new RelationPlan(planNode, analysis.getOutputDescriptor(node), planNode.getOutputSymbols(), outputSampleWeight);
    }

    private RelationPlan addConstantSampleWeight(RelationPlan subPlan)
    {
        ImmutableMap.Builder<Symbol, Expression> projections = ImmutableMap.builder();
        for (Symbol symbol : subPlan.getOutputSymbols()) {
            Expression expression = new QualifiedNameReference(symbol.toQualifiedName());
            projections.put(symbol, expression);
        }
        Expression one = new LongLiteral("1");

        Symbol sampleWeightSymbol = symbolAllocator.newSymbol("$sampleWeight", BIGINT);
        projections.put(sampleWeightSymbol, one);
        ProjectNode projectNode = new ProjectNode(idAllocator.getNextId(), subPlan.getRoot(), projections.build());
        return new RelationPlan(projectNode, subPlan.getDescriptor(), projectNode.getOutputSymbols(), Optional.of(sampleWeightSymbol));
    }

    private PlanBuilder initializePlanBuilder(RelationPlan relationPlan)
    {
        TranslationMap translations = new TranslationMap(relationPlan, analysis);

        // Make field->symbol mapping from underlying relation plan available for translations
        // This makes it possible to rewrite FieldOrExpressions that reference fields from the underlying tuple directly
        translations.setFieldMappings(relationPlan.getOutputSymbols());

        return new PlanBuilder(translations, relationPlan.getRoot(), relationPlan.getSampleWeight());
    }

    private PlanBuilder appendProjections(PlanBuilder subPlan, Iterable<Expression> expressions)
    {
        TranslationMap translations = new TranslationMap(subPlan.getRelationPlan(), analysis);

        // Carry over the translations from the source because we are appending projections
        translations.copyMappingsFrom(subPlan.getTranslations());

        ImmutableMap.Builder<Symbol, Expression> projections = ImmutableMap.builder();

        // add an identity projection for underlying plan
        for (Symbol symbol : subPlan.getRoot().getOutputSymbols()) {
            Expression expression = new QualifiedNameReference(symbol.toQualifiedName());
            projections.put(symbol, expression);
        }

        ImmutableMap.Builder<Symbol, Expression> newTranslations = ImmutableMap.builder();
        for (Expression expression : expressions) {
            Symbol symbol = symbolAllocator.newSymbol(expression, analysis.getType(expression));

            // TODO: CHECK IF THE REWRITE OF A SEMI JOINED EXPRESSION WILL WORK!!!!!!!

            projections.put(symbol, translations.rewrite(expression));
            newTranslations.put(symbol, expression);
        }
        // Now append the new translations into the TranslationMap
        for (Map.Entry<Symbol, Expression> entry : newTranslations.build().entrySet()) {
            translations.put(entry.getValue(), entry.getKey());
        }

        return new PlanBuilder(translations, new ProjectNode(idAllocator.getNextId(), subPlan.getRoot(), projections.build()), subPlan.getSampleWeight());
    }

    private PlanBuilder appendSemiJoins(PlanBuilder subPlan, Set<InPredicate> inPredicates)
    {
        for (InPredicate inPredicate : inPredicates) {
            subPlan = appendSemiJoin(subPlan, inPredicate);
        }
        return subPlan;
    }

    private PlanBuilder appendSemiJoin(PlanBuilder subPlan, InPredicate inPredicate)
    {
        TranslationMap translations = new TranslationMap(subPlan.getRelationPlan(), analysis);
        translations.copyMappingsFrom(subPlan.getTranslations());

        subPlan = appendProjections(subPlan, ImmutableList.of(inPredicate.getValue()));
        Symbol sourceJoinSymbol = subPlan.translate(inPredicate.getValue());

        checkState(inPredicate.getValueList() instanceof SubqueryExpression);
        SubqueryExpression subqueryExpression = (SubqueryExpression) inPredicate.getValueList();
        RelationPlanner relationPlanner = new RelationPlanner(analysis, symbolAllocator, idAllocator, metadata, session);
        RelationPlan valueListRelation = relationPlanner.process(subqueryExpression.getQuery(), null);
        Symbol filteringSourceJoinSymbol = Iterables.getOnlyElement(valueListRelation.getRoot().getOutputSymbols());

        Symbol semiJoinOutputSymbol = symbolAllocator.newSymbol("semijoinresult", BOOLEAN);

        translations.put(inPredicate, semiJoinOutputSymbol);

        return new PlanBuilder(translations,
                new SemiJoinNode(idAllocator.getNextId(),
                        subPlan.getRoot(),
                        valueListRelation.getRoot(),
                        sourceJoinSymbol,
                        filteringSourceJoinSymbol,
                        semiJoinOutputSymbol,
                        Optional.empty(),
                        Optional.empty()),
                subPlan.getSampleWeight());
    }

    private PlanNode distinct(PlanNode node)
    {
        return new AggregationNode(idAllocator.getNextId(),
                node,
                node.getOutputSymbols(),
                ImmutableMap.<Symbol, FunctionCall>of(),
                ImmutableMap.<Symbol, Signature>of(),
                ImmutableMap.<Symbol, Symbol>of(),
                AggregationNode.Step.SINGLE,
                Optional.empty(),
                1.0,
                Optional.empty());
    }
}
