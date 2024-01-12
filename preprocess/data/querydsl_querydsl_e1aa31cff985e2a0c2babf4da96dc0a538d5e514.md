Refactoring Types: ['Move Method']
com/querydsl/jpa/JPQLSerializer.java
/*
 * Copyright 2015, The Querydsl Team (http://www.querydsl.com/team)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.querydsl.jpa;

import java.util.*;

import javax.annotation.Nullable;
import javax.persistence.*;
import javax.persistence.metamodel.EntityType;
import javax.persistence.metamodel.Metamodel;
import javax.persistence.metamodel.SingularAttribute;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Sets;
import com.querydsl.core.JoinExpression;
import com.querydsl.core.JoinType;
import com.querydsl.core.QueryMetadata;
import com.querydsl.core.support.SerializerBase;
import com.querydsl.core.types.*;
import com.querydsl.core.types.dsl.Expressions;
import com.querydsl.core.util.MathUtils;

/**
 * {@code JPQLSerializer} serializes Querydsl expressions into JPQL syntax.
 *
 * @author tiwe
 */
public class JPQLSerializer extends SerializerBase<JPQLSerializer> {

    private static final Set<? extends Operator> NUMERIC = Sets.immutableEnumSet(
            Ops.ADD, Ops.SUB, Ops.MULT, Ops.DIV,
            Ops.LT, Ops.LOE, Ops.GT, Ops.GOE, Ops.BETWEEN);

    private static final Set<? extends Operator> CASE_OPS = Sets.immutableEnumSet(
            Ops.CASE_EQ_ELSE, Ops.CASE_ELSE);

    private static final String COMMA = ", ";

    private static final String DELETE = "delete from ";

    private static final String FROM = "from ";

    private static final String GROUP_BY = "\ngroup by ";

    private static final String HAVING = "\nhaving ";

    private static final String ORDER_BY = "\norder by ";

    private static final String SELECT = "select ";

    private static final String SELECT_COUNT = "select count(";

    private static final String SELECT_COUNT_DISTINCT = "select count(distinct ";

    private static final String SELECT_DISTINCT = "select distinct ";

    private static final String SET = "\nset ";

    private static final String UPDATE = "update ";

    private static final String WHERE = "\nwhere ";

    private static final String WITH = " with ";

    private static final String ON = " on ";

    private static final Map<JoinType, String> joinTypes = new EnumMap<JoinType, String>(JoinType.class);

    private final JPQLTemplates templates;

    private final EntityManager entityManager;

    private boolean inProjection = false;

    private boolean inCaseOperation = false;

    static {
        joinTypes.put(JoinType.DEFAULT, COMMA);
        joinTypes.put(JoinType.FULLJOIN, "\n  full join ");
        joinTypes.put(JoinType.INNERJOIN, "\n  inner join ");
        joinTypes.put(JoinType.JOIN, "\n  inner join ");
        joinTypes.put(JoinType.LEFTJOIN, "\n  left join ");
        joinTypes.put(JoinType.RIGHTJOIN, "\n  right join ");
    }

    private boolean wrapElements = false;

    public JPQLSerializer(JPQLTemplates templates) {
        this(templates, null);
    }

    public JPQLSerializer(JPQLTemplates templates, EntityManager em) {
        super(templates);
        this.templates = templates;
        this.entityManager = em;
    }

    private String getEntityName(Class<?> clazz) {
        final Entity entityAnnotation = clazz.getAnnotation(Entity.class);
        if (entityAnnotation != null && entityAnnotation.name().length() > 0) {
            return entityAnnotation.name();
        } else if (clazz.getPackage() != null) {
            String pn = clazz.getPackage().getName();
            return clazz.getName().substring(pn.length() + 1);
        } else {
            return clazz.getName();
        }
    }

    private void handleJoinTarget(JoinExpression je) {
        // type specifier
        if (je.getTarget() instanceof EntityPath<?>) {
            final EntityPath<?> pe = (EntityPath<?>) je.getTarget();
            if (pe.getMetadata().isRoot()) {
                append(getEntityName(pe.getType()));
                append(" ");
            }
            handle(je.getTarget());
        } else if (je.getTarget() instanceof Operation) {
            Operation<?> op = (Operation) je.getTarget();
            if (op.getOperator() == Ops.ALIAS) {
                boolean treat = false;
                if (Collection.class.isAssignableFrom(op.getArg(0).getType())) {
                    if (op.getArg(0) instanceof CollectionExpression) {
                        Class<?> par = ((CollectionExpression) op.getArg(0)).getParameter(0);
                        treat = !par.equals(op.getArg(1).getType());
                    }
                } else if (Map.class.isAssignableFrom(op.getArg(0).getType())) {
                    if (op.getArg(0) instanceof MapExpression) {
                        Class<?> par = ((MapExpression) op.getArg(0)).getParameter(1);
                        treat = !par.equals(op.getArg(1).getType());
                    }
                } else {
                    treat = !op.getArg(0).getType().equals(op.getArg(1).getType());
                }
                if (treat) {
                    Expression<?> entityName = ConstantImpl.create(getEntityName(op.getArg(1).getType()));
                    Expression<?> t = ExpressionUtils.operation(op.getType(), JPQLOps.TREAT, op.getArg(0), entityName);
                    op = ExpressionUtils.operation(op.getType(), Ops.ALIAS, t, op.getArg(1));
                }
            }
            handle(op);
        } else {
            handle(je.getTarget());
        }
    }

    public void serialize(QueryMetadata metadata, boolean forCountRow, @Nullable String projection) {
        final Expression<?> select = metadata.getProjection();
        final List<JoinExpression> joins = metadata.getJoins();
        final Predicate where = metadata.getWhere();
        final List<? extends Expression<?>> groupBy = metadata.getGroupBy();
        final Predicate having = metadata.getHaving();
        final List<OrderSpecifier<?>> orderBy = metadata.getOrderBy();

        // select
        boolean inProjectionOrig = inProjection;
        inProjection = true;
        if (projection != null) {
            append(SELECT).append(projection).append("\n");

        } else if (forCountRow) {
            if (!metadata.isDistinct()) {
                append(SELECT_COUNT);
            } else {
                append(SELECT_COUNT_DISTINCT);
            }
            if (select != null) {
                if (select instanceof FactoryExpression) {
                    handle(joins.get(0).getTarget());
                } else {
                    // TODO : make sure this works
                    handle(select);
                }
            } else {
                handle(joins.get(0).getTarget());
            }
            append(")\n");

        } else {
            if (!metadata.isDistinct()) {
                append(SELECT);
            } else {
                append(SELECT_DISTINCT);
            }
            if (select != null) {
                handle(select);
            } else {
                handle(metadata.getJoins().get(0).getTarget());
            }
            append("\n");

        }
        inProjection = inProjectionOrig;

        // from
        append(FROM);
        serializeSources(forCountRow, joins);

        // where
        if (where != null) {
            append(WHERE).handle(where);
        }

        // group by
        if (!groupBy.isEmpty()) {
            append(GROUP_BY).handle(COMMA, groupBy);
        }

        // having
        if (having != null) {
            append(HAVING).handle(having);
        }

        // order by
        if (!orderBy.isEmpty() && !forCountRow) {
            append(ORDER_BY);
            boolean first = true;
            for (final OrderSpecifier<?> os : orderBy) {
                if (!first) {
                    append(COMMA);
                }
                handle(os.getTarget());
                append(os.getOrder() == Order.ASC ? " asc" : " desc");
                if (os.getNullHandling() == OrderSpecifier.NullHandling.NullsFirst) {
                    append(" nulls first");
                } else if (os.getNullHandling() == OrderSpecifier.NullHandling.NullsLast) {
                    append(" nulls last");
                }
                first = false;
            }
        }
    }

    public void serializeForDelete(QueryMetadata md) {
        append(DELETE);
        handleJoinTarget(md.getJoins().get(0));
        if (md.getWhere() != null) {
            append(WHERE).handle(md.getWhere());
        }
    }

    public void serializeForUpdate(QueryMetadata md, Map<Path<?>, Expression<?>> updates) {
        append(UPDATE);
        handleJoinTarget(md.getJoins().get(0));
        append(SET);
        boolean first = true;
        for (Map.Entry<Path<?>, Expression<?>> entry : updates.entrySet()) {
            if (!first) {
                append(", ");
            }
            handle(entry.getKey());
            append(" = ");
            handle(entry.getValue());
            first = false;
        }
        if (md.getWhere() != null) {
            append(WHERE).handle(md.getWhere());
        }
    }

    private void serializeSources(boolean forCountRow, List<JoinExpression> joins) {
        for (int i = 0; i < joins.size(); i++) {
            final JoinExpression je = joins.get(i);
            if (i > 0) {
                append(joinTypes.get(je.getType()));
            }
            if (je.hasFlag(JPAQueryMixin.FETCH) && !forCountRow) {
                handle(JPAQueryMixin.FETCH);
            }
            handleJoinTarget(je);
            // XXX Hibernate specific flag
            if (je.hasFlag(JPAQueryMixin.FETCH_ALL_PROPERTIES) && !forCountRow) {
                handle(JPAQueryMixin.FETCH_ALL_PROPERTIES);
            }

            if (je.getCondition() != null) {
                append(templates.isWithForOn() ? WITH : ON);
                handle(je.getCondition());
            }
        }
    }

    @Override
    public void visitConstant(Object constant) {
        if (inCaseOperation && templates.isCaseWithLiterals()) {
            if (constant instanceof Collection) {
                append("(");
                boolean first = true;
                for (Object o : (Collection) constant) {
                    if (!first) {
                        append(", ");
                    }
                    visitLiteral(o);
                    first = false;
                }
                append(")");
            } else {
                visitLiteral(constant);
            }
        } else {
            boolean wrap = templates.wrapConstant(constant);
            if (wrap) {
                append("(");
            }
            append("?");
            if (!getConstantToLabel().containsKey(constant)) {
                final String constLabel = String.valueOf(getConstantToLabel().size() + 1);
                getConstantToLabel().put(constant, constLabel);
                append(constLabel);
            } else {
                append(getConstantToLabel().get(constant));
            }
            if (wrap) {
                append(")");
            }
        }
    }

    public void visitLiteral(Object constant) {
        if (constant instanceof Boolean) {
            append(constant.toString());
        } else if (constant instanceof Number) {
            append(constant.toString());
        } else if (constant instanceof String) {
            append("'");
            append(escapeLiteral(constant.toString()));
            append("'");
        } else if (constant instanceof Enum<?>) {
            append(constant.getClass().getName());
            append(".");
            append(((Enum<?>) constant).name());
        } else {
            // TODO date time literals
            throw new IllegalArgumentException("Unsupported constant " + constant);
        }
    }

    private String escapeLiteral(String str) {
        StringBuilder builder = new StringBuilder();
        for (char ch : str.toCharArray()) {
            if (ch == '\n') {
                builder.append("\\n");
                continue;
            } else if (ch == '\r') {
                builder.append("\\r");
                continue;
            } else if (ch == '\'') {
                builder.append("''");
                continue;
            }
            builder.append(ch);
        }
        return builder.toString();
    }

    @Override
    public Void visit(ParamExpression<?> param, Void context) {
        append("?");
        if (!getConstantToLabel().containsKey(param)) {
            final String paramLabel = String.valueOf(getConstantToLabel().size() + 1);
            getConstantToLabel().put(param, paramLabel);
            append(paramLabel);
        } else {
            append(getConstantToLabel().get(param));
        }
        return null;
    }

    @Override
    public Void visit(SubQueryExpression<?> query, Void context) {
        append("(");
        serialize(query.getMetadata(), false, null);
        append(")");
        return null;
    }

    @Override
    public Void visit(Path<?> expr, Void context) {
        // only wrap a PathCollection, if it the pathType is PROPERTY
        boolean wrap = wrapElements
        && (Collection.class.isAssignableFrom(expr.getType()) || Map.class.isAssignableFrom(expr.getType()))
        && expr.getMetadata().getPathType().equals(PathType.PROPERTY);
        if (wrap) {
            append("elements(");
        }
        super.visit(expr, context);
        if (wrap) {
            append(")");
        }
        return null;
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void visitOperation(Class<?> type, Operator operator, List<? extends Expression<?>> args) {
        boolean oldInCaseOperation = inCaseOperation;
        inCaseOperation = CASE_OPS.contains(operator);
        boolean oldWrapElements = wrapElements;
        wrapElements = templates.wrapElements(operator);

        if (operator == Ops.EQ && args.get(1) instanceof Operation &&
                ((Operation) args.get(1)).getOperator() == Ops.QuantOps.ANY) {
            args = ImmutableList.<Expression<?>>of(args.get(0), ((Operation) args.get(1)).getArg(0));
            visitOperation(type, Ops.IN, args);

        } else if (operator == Ops.NE && args.get(1) instanceof Operation &&
                ((Operation) args.get(1)).getOperator() == Ops.QuantOps.ANY) {
            args = ImmutableList.<Expression<?>>of(args.get(0), ((Operation) args.get(1)).getArg(0));
            visitOperation(type, Ops.NOT_IN, args);

        } else if (operator == Ops.IN || operator == Ops.NOT_IN) {
            if (args.get(1) instanceof Path) {
                visitAnyInPath(type, operator, args);
            } else if (args.get(0) instanceof Path && args.get(1) instanceof Constant<?>) {
                visitPathInCollection(type, operator, args);
            } else {
                super.visitOperation(type, operator, args);
            }

        } else if (operator == Ops.NUMCAST) {
            visitNumCast(args);

        } else if (operator == Ops.EXISTS && args.get(0) instanceof SubQueryExpression) {
            final SubQueryExpression subQuery = (SubQueryExpression) args.get(0);
            append("exists (");
            serialize(subQuery.getMetadata(), false, templates.getExistsProjection());
            append(")");

        } else if (operator == Ops.MATCHES || operator == Ops.MATCHES_IC) {
            super.visitOperation(type, Ops.LIKE,
                    ImmutableList.of(args.get(0), ExpressionUtils.regexToLike((Expression<String>) args.get(1))));

        } else if (operator == Ops.LIKE && args.get(1) instanceof Constant<?>) {
            final String escape = String.valueOf(templates.getEscapeChar());
            final String escaped = args.get(1).toString().replace(escape, escape + escape);
            super.visitOperation(String.class, Ops.LIKE,
                    ImmutableList.of(args.get(0), ConstantImpl.create(escaped)));

        } else if (NUMERIC.contains(operator)) {
            super.visitOperation(type, operator, normalizeNumericArgs(args));

        } else {
            super.visitOperation(type, operator, args);
        }

        inCaseOperation = oldInCaseOperation;
        wrapElements = oldWrapElements;
    }

    private void visitNumCast(List<? extends Expression<?>> args) {
        @SuppressWarnings("unchecked") //this is the second argument's type
        Constant<Class<?>> rightArg = (Constant<Class<?>>) args.get(1);

        final Class<?> targetType = rightArg.getConstant();
        final String typeName = templates.getTypeForCast(targetType);
        visitOperation(targetType, JPQLOps.CAST, ImmutableList.of(args.get(0), ConstantImpl.create(typeName)));
    }

    private void visitPathInCollection(Class<?> type, Operator operator,
            List<? extends Expression<?>> args) {
        Path<?> lhs = (Path<?>) args.get(0);
        @SuppressWarnings("unchecked")
        Constant<? extends Collection<?>> rhs = (Constant<? extends Collection<?>>) args.get(1);
        if (rhs.getConstant().isEmpty()) {
            operator = operator == Ops.IN ? Ops.EQ : Ops.NE;
            args = ImmutableList.of(Expressions.ONE, Expressions.TWO);
        } else if (entityManager != null && !templates.isPathInEntitiesSupported() && args.get(0).getType().isAnnotationPresent(Entity.class)) {
            final Metamodel metamodel = entityManager.getMetamodel();
            final PersistenceUnitUtil util = entityManager.getEntityManagerFactory().getPersistenceUnitUtil();
            final EntityType<?> entityType = metamodel.entity(args.get(0).getType());
            if (entityType.hasSingleIdAttribute()) {
                SingularAttribute<?,?> id = getIdProperty(entityType);
                // turn lhs into id path
                lhs = ExpressionUtils.path(id.getJavaType(), lhs, id.getName());
                // turn rhs into id collection
                Set<Object> ids = new HashSet<Object>();
                for (Object entity : rhs.getConstant()) {
                    ids.add(util.getIdentifier(entity));
                }
                rhs = ConstantImpl.create(ids);
                args = ImmutableList.of(lhs, rhs);
            }
        }

        super.visitOperation(type, operator, args);
    }

    @SuppressWarnings("rawtypes")
    private SingularAttribute<?,?> getIdProperty(EntityType entity) {
        final Set<SingularAttribute> singularAttributes = entity.getSingularAttributes();
        for (final SingularAttribute singularAttribute : singularAttributes) {
            if (singularAttribute.isId()) {
                return singularAttribute;
            }
        }
        return null;
    }

    private void visitAnyInPath(Class<?> type, Operator operator, List<? extends Expression<?>> args) {
        if (!templates.isEnumInPathSupported() && args.get(0) instanceof Constant<?> && Enum.class.isAssignableFrom(args.get(0).getType())) {
            @SuppressWarnings("unchecked") //guarded by previous check
            Constant<? extends Enum<?>> expectedConstant = (Constant<? extends Enum<?>>) args.get(0);

            final Enum<?> constant = expectedConstant.getConstant();
            final Enumerated enumerated = ((Path<?>) args.get(1)).getAnnotatedElement().getAnnotation(Enumerated.class);
            if (enumerated == null || enumerated.value() == EnumType.ORDINAL) {
                args = ImmutableList.of(ConstantImpl.create(constant.ordinal()), args.get(1));
            } else {
                args = ImmutableList.of(ConstantImpl.create(constant.name()), args.get(1));
            }
        }
        super.visitOperation(type,
                operator == Ops.IN ? JPQLOps.MEMBER_OF : JPQLOps.NOT_MEMBER_OF,
                args);
    }

    private List<? extends Expression<?>> normalizeNumericArgs(List<? extends Expression<?>> args) {
        //we do not yet let it produce these types
        //we verify the types with isAssignableFrom()
        @SuppressWarnings("unchecked")
        List<? extends Expression<? extends Number>> potentialArgs =
                (List<? extends Expression<? extends Number>>) args;
        boolean hasConstants = false;
        Class<? extends Number> numType = null;
        for (Expression<? extends Number> arg : potentialArgs) {
            if (Number.class.isAssignableFrom(arg.getType())) {
                if (arg instanceof Constant<?>) {
                    hasConstants = true;
                } else {
                    numType = arg.getType();
                }
            }
        }
        if (hasConstants && numType != null) {
            //now we do let the potentialArgs help us
            final List<Expression<?>> newArgs = new ArrayList<Expression<?>>(args.size());
            for (final Expression<? extends Number> arg : potentialArgs) {
                if (arg instanceof Constant<?> && Number.class.isAssignableFrom(arg.getType())
                        && !arg.getType().equals(numType)) {
                    final Number number = ((Constant<? extends Number>) arg).getConstant();
                    newArgs.add(ConstantImpl.create(MathUtils.cast(number, numType)));
                } else {
                    newArgs.add(arg);
                }
            }
            return newArgs;
        } else {
            //the types are all non-constants, or not Number expressions
            return potentialArgs;
        }
    }

}


File: querydsl-jpa/src/main/java/com/querydsl/jpa/JPQLTemplates.java
/*
 * Copyright 2015, The Querydsl Team (http://www.querydsl.com/team)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.querydsl.jpa;

import javax.annotation.Nullable;

import com.querydsl.core.types.Operator;
import com.querydsl.core.types.Ops;
import com.querydsl.core.types.PathType;
import com.querydsl.core.types.Templates;

/**
 * {@code JPQLTemplates} extends {@link Templates} to provide operator patterns for JPQL
 * serialization
 *
 * @author tiwe
 * @see HQLTemplates
 * @see EclipseLinkTemplates
 */
public class JPQLTemplates extends Templates {

    public static final char DEFAULT_ESCAPE = '!';

    public static final JPQLTemplates DEFAULT = new JPQLTemplates();

    private final QueryHandler queryHandler;

    protected JPQLTemplates() {
        this(DEFAULT_ESCAPE, DefaultQueryHandler.DEFAULT);
    }

    protected JPQLTemplates(char escape) {
        this(escape, DefaultQueryHandler.DEFAULT);
    }

    protected JPQLTemplates(char escape, QueryHandler queryHandler) {
        super(escape);
        this.queryHandler = queryHandler;

        setPrecedence(Precedence.COMPARISON, Ops.EQ, Ops.NE, Ops.EQ_IGNORE_CASE,
                Ops.BETWEEN, Ops.COL_IS_EMPTY);

        // other like cases
        setPrecedence(Precedence.COMPARISON, Ops.MATCHES, Ops.MATCHES_IC,
                Ops.ENDS_WITH, Ops.ENDS_WITH_IC,
                Ops.STARTS_WITH, Ops.STARTS_WITH_IC,
                Ops.STRING_CONTAINS, Ops.STRING_CONTAINS_IC);

        add(Ops.CASE, "case {0} end");
        add(Ops.CASE_WHEN,  "when {0} then {1} {2}", 0);
        add(Ops.CASE_ELSE,  "else {0}", 0);

        //CHECKSTYLE:OFF
        // boolean
        add(Ops.AND, "{0} and {1}");
        add(Ops.NOT, "not {0}", Precedence.NOT);
        add(Ops.OR, "{0} or {1}");
        add(Ops.XNOR, "{0} xnor {1}");
        add(Ops.XOR, "{0} xor {1}");

        // comparison
        add(Ops.BETWEEN, "{0} between {1} and {2}");

        // numeric
        add(Ops.MathOps.SQRT, "sqrt({0})");
        add(Ops.MOD, "mod({0},{1})", -1);

        // various
        add(Ops.NE, "{0} <> {1}");
        add(Ops.IS_NULL, "{0} is null");
        add(Ops.IS_NOT_NULL, "{0} is not null");
        add(JPQLOps.CAST, "cast({0} as {1s})");
        add(Ops.NUMCAST, "cast({0} as {1s})");

        // collection
        add(JPQLOps.MEMBER_OF, "{0} member of {1}", Precedence.COMPARISON);
        add(JPQLOps.NOT_MEMBER_OF, "{0} not member of {1}", Precedence.COMPARISON);

        add(Ops.IN, "{0} in {1}");
        add(Ops.NOT_IN, "{0} not in {1}");
        add(Ops.COL_IS_EMPTY, "{0} is empty");
        add(Ops.COL_SIZE, "size({0})");
        add(Ops.ARRAY_SIZE, "size({0})");

        // string
        add(Ops.LIKE, "{0} like {1} escape '" + escape + "'");
        add(Ops.CONCAT, "concat({0},{1})", -1);
        add(Ops.MATCHES, "{0} like {1}  escape '" + escape + "'"); // TODO : support real regexes
        add(Ops.MATCHES_IC, "{0} like {1} escape '" + escape + "'"); // TODO : support real regexes
        add(Ops.LOWER, "lower({0})");
        add(Ops.SUBSTR_1ARG, "substring({0},{1s}+1)", Precedence.ARITH_LOW);
        add(Ops.SUBSTR_2ARGS, "substring({0},{1s}+1,{2s}-{1s})", Precedence.ARITH_LOW);
        add(Ops.TRIM, "trim({0})");
        add(Ops.UPPER, "upper({0})");
        add(Ops.EQ_IGNORE_CASE, "{0l} = {1l}");
        add(Ops.CHAR_AT, "cast(substring({0},{1s}+1,1) as char)", Precedence.ARITH_LOW);
        add(Ops.STRING_IS_EMPTY, "length({0}) = 0");

        add(Ops.STRING_CONTAINS, "{0} like {%1%} escape '" + escape + "'");
        add(Ops.STRING_CONTAINS_IC, "{0l} like {%%1%%} escape '" + escape + "'");
        add(Ops.ENDS_WITH, "{0} like {%1} escape '" + escape + "'");
        add(Ops.ENDS_WITH_IC, "{0l} like {%%1} escape '" + escape + "'");
        add(Ops.STARTS_WITH, "{0} like {1%} escape '" + escape + "'");
        add(Ops.STARTS_WITH_IC, "{0l} like {1%%} escape '" + escape + "'");
        add(Ops.INDEX_OF, "locate({1},{0})-1", Precedence.ARITH_LOW);
        add(Ops.INDEX_OF_2ARGS, "locate({1},{0},{2s}+1)-1", Precedence.ARITH_LOW);

        // date time
        add(Ops.DateTimeOps.SYSDATE, "sysdate");
        add(Ops.DateTimeOps.CURRENT_DATE, "current_date");
        add(Ops.DateTimeOps.CURRENT_TIME, "current_time");
        add(Ops.DateTimeOps.CURRENT_TIMESTAMP, "current_timestamp");

        add(Ops.DateTimeOps.MILLISECOND, "0"); // NOT supported in HQL
        add(Ops.DateTimeOps.SECOND, "second({0})");
        add(Ops.DateTimeOps.MINUTE, "minute({0})");
        add(Ops.DateTimeOps.HOUR, "hour({0})");
        add(Ops.DateTimeOps.DAY_OF_MONTH, "day({0})");
        add(Ops.DateTimeOps.MONTH, "month({0})");
        add(Ops.DateTimeOps.YEAR, "year({0})");

        add(Ops.DateTimeOps.YEAR_MONTH, "year({0}) * 100 + month({0})", Precedence.ARITH_LOW);

        // path types
        add(PathType.PROPERTY, "{0}.{1s}");
        add(PathType.VARIABLE, "{0s}");

        // case for eq
        add(Ops.CASE_EQ, "case {1} end");
        add(Ops.CASE_EQ_WHEN,  "when {0} = {1} then {2} {3}", 0);
        add(Ops.CASE_EQ_ELSE,  "else {0}", 0);

        add(Ops.INSTANCE_OF, "type({0}) = {1}");
        add(JPQLOps.TYPE, "type({0})");
        add(JPQLOps.INDEX, "index({0})");
        add(JPQLOps.TREAT, "treat({0} as {1s})");
        add(JPQLOps.KEY, "key({0})");
        add(JPQLOps.VALUE, "value({0})");

        //CHECKSTYLE:ON
    }

    public boolean wrapElements(Operator operator) {
        return false;
    }

    public String getTypeForCast(Class<?> cl) {
        return cl.getSimpleName().toLowerCase();
    }

    public boolean isEnumInPathSupported() {
        return true;
    }

    public boolean isPathInEntitiesSupported() {
        return true;
    }

    @Nullable
    public String getExistsProjection() {
        return null;
    }

    public boolean wrapConstant(Object constant) {
        // related : https://hibernate.onjira.com/browse/HHH-6913
        return false;
    }

    public boolean isWithForOn() {
        return false;
    }

    public QueryHandler getQueryHandler() {
        return queryHandler;
    }

    public boolean isCaseWithLiterals() {
        return false;
    }

}


File: querydsl-jpa/src/test/java/com/querydsl/jpa/AbstractJPATest.java
/*
 * Copyright 2015, The Querydsl Team (http://www.querydsl.com/team)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.querydsl.jpa;

import static com.querydsl.core.Target.*;
import static com.querydsl.jpa.JPAExpressions.select;
import static org.junit.Assert.*;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.*;
import java.util.Calendar;
import java.util.Map.Entry;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import com.mysema.commons.lang.Pair;
import com.querydsl.core.*;
import com.querydsl.core.group.Group;
import com.querydsl.core.group.GroupBy;
import com.querydsl.core.group.QPair;
import com.querydsl.core.testutil.ExcludeIn;
import com.querydsl.core.types.*;
import com.querydsl.core.types.dsl.*;
import com.querydsl.jpa.domain.*;
import com.querydsl.jpa.domain.Company.Rating;
import com.querydsl.jpa.domain4.QBookMark;
import com.querydsl.jpa.domain4.QBookVersion;

import antlr.RecognitionException;
import antlr.TokenStreamException;

/**
 * @author tiwe
 *
 */
public abstract class AbstractJPATest {

    private static final Expression<?>[] NO_EXPRESSIONS = new Expression[0];

    private static final QCompany company = QCompany.company;

    private static final QAnimal animal = QAnimal.animal;

    private static final QCat cat = QCat.cat;

    private static final QCat otherCat = new QCat("otherCat");

    private static final BooleanExpression cond1 = cat.name.length().gt(0);

    private static final BooleanExpression cond2 = otherCat.name.length().gt(0);

    private static final Predicate condition = ExpressionUtils.and(
            (Predicate) ExpressionUtils.extract(cond1),
            (Predicate) ExpressionUtils.extract(cond2));

    private static final Date birthDate;

    private static final java.sql.Date date;

    private static final java.sql.Time time;

    private final List<Cat> savedCats = new ArrayList<Cat>();

    static {
        Calendar cal = Calendar.getInstance();
        cal.set(2000, 1, 2, 3, 4);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        birthDate = cal.getTime();
        date = new java.sql.Date(cal.getTimeInMillis());
        time = new java.sql.Time(cal.getTimeInMillis());
    }

    protected Target getTarget() {
        return Mode.target.get();
    }

    protected abstract JPQLQuery<?> query();

    protected abstract JPQLQuery<?> testQuery();

    protected abstract void save(Object entity);

    @Before
    public void setUp() {
        if (query().from(cat).fetchCount() > 0) {
            savedCats.addAll(query().from(cat).orderBy(cat.id.asc()).select(cat).fetch());
            return;
        }

        Cat prev = null;
        for (Cat cat : Arrays.asList(
                new Cat("Bob123", 1, 1.0),
                new Cat("Ruth123", 2, 2.0),
                new Cat("Felix123", 3, 3.0),
                new Cat("Allen123", 4, 4.0),
                new Cat("Mary_123", 5, 5.0))) {
            if (prev != null) {
                cat.addKitten(prev);
            }
            cat.setBirthdate(birthDate);
            cat.setDateField(date);
            cat.setTimeField(time);
            cat.setColor(Color.BLACK);
            cat.setMate(prev);
            save(cat);
            savedCats.add(cat);
            prev = cat;
        }

        Animal animal = new Animal(10);
        animal.setBodyWeight(10.5);
        save(animal);

        Cat cat = new Cat("Some", 6, 6.0);
        cat.setBirthdate(birthDate);
        save(cat);
        savedCats.add(cat);

        Show show = new Show(1);
        show.acts = new HashMap<String,String>();
        show.acts.put("a","A");
        show.acts.put("b","B");
        save(show);

        Company company = new Company();
        company.name = "1234567890123456789012345678901234567890"; // 40
        company.id = 1;
        company.ratingOrdinal = Company.Rating.A;
        company.ratingString = Company.Rating.AA;
        save(company);

        Employee employee = new Employee();
        employee.id = 1;
        employee.lastName = "Smith";
        employee.jobFunctions.add(JobFunction.CODER);
        save(employee);

        Employee employee2 = new Employee();
        employee2.id = 2;
        employee2.lastName = "Doe";
        employee2.jobFunctions.add(JobFunction.CODER);
        employee2.jobFunctions.add(JobFunction.CONSULTANT);
        employee2.jobFunctions.add(JobFunction.CONTROLLER);
        save(employee2);

        save(new Entity1(1));
        save(new Entity1(2));
        save(new Entity2(3));

        Foo foo = new Foo();
        foo.id = 1;
        foo.names = Arrays.asList("a","b");
        foo.bar = "München";
        save(foo);

        Numeric numeric = new Numeric();
        numeric.setValue(BigDecimal.valueOf(26.9));
        save(numeric);
    }

    @Test
    @ExcludeIn(ORACLE)
    public void Add_BigDecimal() {
        QSimpleTypes entity = new QSimpleTypes("entity1");
        QSimpleTypes entity2 = new QSimpleTypes("entity2");
        NumberPath<BigDecimal> bigd1 = entity.bigDecimal;
        NumberPath<BigDecimal> bigd2 = entity2.bigDecimal;

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                        .where(bigd1.add(bigd2).loe(new BigDecimal("1.00")))
                        .select(entity).fetch());
    }

    @Test
    public void Aggregates_List_Max() {
        assertEquals(Integer.valueOf(6), query().from(cat).select(cat.id.max()).fetchFirst());
    }

    @Test
    public void Aggregates_List_Min() {
        assertEquals(Integer.valueOf(1), query().from(cat).select(cat.id.min()).fetchFirst());
    }

    @Test
    public void Aggregates_UniqueResult_Max() {
        assertEquals(Integer.valueOf(6), query().from(cat).select(cat.id.max()).fetchFirst());
    }

    @Test
    public void Aggregates_UniqueResult_Min() {
        assertEquals(Integer.valueOf(1), query().from(cat).select(cat.id.min()).fetchFirst());
    }

    @Test
    public void Any_And_Gt() {
        assertEquals(0, query().from(cat).where(
                cat.kittens.any().name.eq("Ruth123"),
                cat.kittens.any().bodyWeight.gt(10.0)).fetchCount());
    }

    @Test
    public void Any_And_Lt() {
        assertEquals(1, query().from(cat).where(
                cat.kittens.any().name.eq("Ruth123"),
                cat.kittens.any().bodyWeight.lt(10.0)).fetchCount());
    }

    @Test
    public void Any_In_Order() {
        assertFalse(query().from(cat).orderBy(cat.kittens.any().name.asc()).select(cat).fetch().isEmpty());
    }

    @Test
    public void Any_In_Projection() {
        assertFalse(query().from(cat).select(cat.kittens.any()).fetch().isEmpty());
    }

    @Test
    public void Any_In_Projection2() {
        assertFalse(query().from(cat).select(cat.kittens.any().name).fetch().isEmpty());
    }

    @Test
    public void Any_In_Projection3() {
        assertFalse(query().from(cat).select(cat.kittens.any().name, cat.kittens.any().bodyWeight).fetch().isEmpty());
    }

    @Test
    public void Any_In1() {
        //select cat from Cat cat where exists (
        //  select cat_kittens from Cat cat_kittens where cat_kittens member of cat.kittens and cat_kittens in ?1)
        assertFalse(query().from(cat).where(cat.kittens.any().in(savedCats)).select(cat).fetch().isEmpty());
    }

    @Test
    public void Any_In11() {
        List<Integer> ids = Lists.newArrayList();
        for (Cat cat : savedCats) {
            ids.add(cat.getId());
        }
        assertFalse(query().from(cat).where(cat.kittens.any().id.in(ids)).select(cat).fetch().isEmpty());
    }

    @Test
    public void Any_In2() {
        assertFalse(query().from(cat).where(
                cat.kittens.any().in(savedCats),
                cat.kittens.any().in(savedCats.subList(0, 1)).not())
                .select(cat).fetch().isEmpty());
    }

    @Test
    @NoBatooJPA
    public void Any_In3() {
        QEmployee employee = QEmployee.employee;
        assertFalse(query().from(employee).where(
                employee.jobFunctions.any().in(JobFunction.CODER, JobFunction.CONSULTANT))
                .select(employee).fetch().isEmpty());
    }

    @Test
    public void Any_Simple() {
        assertEquals(1, query().from(cat).where(cat.kittens.any().name.eq("Ruth123")).fetchCount());
    }

    @SuppressWarnings("unchecked")
    @Test
    public void ArrayProjection() {
        List<String[]> results = query().from(cat)
                .select(new ArrayConstructorExpression<String>(String[].class, cat.name)).fetch();
        assertFalse(results.isEmpty());
        for (String[] result : results) {
            assertNotNull(result[0]);
        }
    }

    @Test
    public void As() {
        assertTrue(query().from(QAnimal.animal.as(QCat.class)).fetchCount() > 0);
    }

    @Test
    @NoBatooJPA
    public void Case() {
        assertEquals(ImmutableList.of(1, 2, 2, 2, 2, 2),
                query().from(cat).orderBy(cat.id.asc())
                        .select(cat.name.when("Bob123").then(1).otherwise(2)).fetch());
    }

    @Test
    @NoBatooJPA
    public void Case_Long() {
        assertEquals(ImmutableList.of(1L, 2L, 2L, 2L, 2L, 2L),
                query().from(cat).orderBy(cat.id.asc())
                        .select(cat.name.when("Bob123").then(1L).otherwise(2L)).fetch());
    }

    @Test
    public void Case2() {
        assertEquals(ImmutableList.of(4, 4, 4, 4, 4, 4),
                query().from(cat)
                        .select(Expressions.cases().when(cat.toes.eq(2)).then(cat.id.multiply(2))
                                .when(cat.toes.eq(3)).then(cat.id.multiply(3))
                                .otherwise(4)).fetch());
    }

    @Test
    public void Case3() {
        assertEquals(ImmutableList.of(4, 4, 4, 4, 4, 4),
                query().from(cat).select(Expressions.cases()
                        .when(cat.toes.in(2, 3)).then(cat.id.multiply(cat.toes))
                        .otherwise(4)).fetch());
    }

    @Test
    @ExcludeIn(MYSQL) // doesn't work in Eclipselink
    public void Case4() {
        NumberExpression<Float> numExpression = cat.bodyWeight.floatValue().divide(otherCat.bodyWeight.floatValue()).multiply(100);
        NumberExpression<Float> numExpression2 = cat.id.when(0).then(0.0F).otherwise(numExpression);
        assertEquals(ImmutableList.of(200, 150, 133, 125, 120),
                query().from(cat, otherCat)
                        .where(cat.id.eq(otherCat.id.add(1)))
                        .orderBy(cat.id.asc(), otherCat.id.asc())
                        .select(numExpression2.intValue()).fetch());
    }

    @Test
    @NoEclipseLink // EclipseLink uses a left join for cat.mate
    public void Case5() {
        assertEquals(ImmutableList.of(0, 1, 1, 1),
                query().from(cat).orderBy(cat.id.asc())
                       .select(cat.mate.when(savedCats.get(0)).then(0).otherwise(1)).fetch());
    }

    @Test
    public void CaseBuilder() {
        QCat cat2 = new QCat("cat2");
        NumberExpression<Integer> casex = new CaseBuilder()
                .when(cat.weight.isNull().and(cat.weight.isNull())).then(0)
                .when(cat.weight.isNull()).then(cat2.weight)
                .when(cat2.weight.isNull()).then(cat.weight)
                .otherwise(cat.weight.add(cat2.weight));

        query().from(cat, cat2).orderBy(casex.asc()).select(cat.id, cat2.id).fetch();
        query().from(cat, cat2).orderBy(casex.desc()).select(cat.id, cat2.id).fetch();
    }

    @Test
    public void Cast() {
        List<Cat> cats = query().from(cat).select(cat).fetch();
        List<Integer> weights = query().from(cat).select(cat.bodyWeight.castToNum(Integer.class)).fetch();
        for (int i = 0; i < cats.size(); i++) {
            assertEquals(Integer.valueOf((int) (cats.get(i).getBodyWeight())), weights.get(i));
        }
    }

    @Test
    public void Cast_ToString() {
        for (Tuple tuple : query().from(cat).select(cat.breed, cat.breed.stringValue()).fetch()) {
            assertEquals(
                    tuple.get(cat.breed).toString(),
                    tuple.get(cat.breed.stringValue()));
        }
    }

    @Test
    public void Cast_ToString_Append() {
        for (Tuple tuple : query().from(cat).select(cat.breed, cat.breed.stringValue().append("test")).fetch()) {
            assertEquals(
                    tuple.get(cat.breed).toString() + "test",
                    tuple.get(cat.breed.stringValue().append("test")));
        }
    }

    @Test
    public void Collection_Predicates() {
        ListPath<Cat, QCat> path = cat.kittens;
        List<Predicate> predicates = Arrays.asList(
//            path.eq(savedCats),
//            path.in(savedCats),
//            path.isNotNull(),
//            path.isNull(),
//            path.ne(savedCats),
//            path.notIn(savedCats)
//            path.when(other)
        );
        for (Predicate pred : predicates) {
            System.err.println(pred);
            query().from(cat).where(pred).select(cat).fetch();
        }
    }

    @Test
    public void Collection_Projections() {
        ListPath<Cat, QCat> path = cat.kittens;
        List<Expression<?>> projections = Arrays.asList(
//            path.fetchCount(),
//            path.countDistinct()
        );
        for (Expression<?> proj : projections) {
            System.err.println(proj);
            query().from(cat).select(proj).fetch();
        }
    }

    @Test
    @NoHibernate // https://github.com/querydsl/querydsl/issues/290
    public void Constant() {
        //select cat.id, ?1 as const from Cat cat
        List<Cat> cats = query().from(cat).select(cat).fetch();
        Path<String> path = Expressions.stringPath("const");
        List<Tuple> tuples = query().from(cat).select(cat.id, Expressions.constantAs("abc", path)).fetch();
        for (int i = 0; i < cats.size(); i++) {
            assertEquals(Integer.valueOf(cats.get(i).getId()), tuples.get(i).get(cat.id));
            assertEquals("abc", tuples.get(i).get(path));
        }
    }

    @Test(expected = ClassCastException.class)
    @NoEclipseLink
    @NoBatooJPA
    public void Constant_Hibernate() {
        //select cat.id, ?1 as const from Cat cat
        query().from(cat).select(cat.id, Expressions.constantAs("abc", Expressions.stringPath("const"))).fetch();
    }

    @Test
    @NoHibernate // https://github.com/querydsl/querydsl/issues/290
    public void Constant2() {
        assertFalse(query().from(cat).select(cat.id, Expressions.constant("name")).fetch().isEmpty());
    }

    @Test
    public void ConstructorProjection() {
        List<Projection> projections = query().from(cat)
                .select(Projections.constructor(Projection.class, cat.name, cat)).fetch();
        assertFalse(projections.isEmpty());
        for (Projection projection : projections) {
            assertNotNull(projection);
        }
    }

    @Test
    public void ConstructorProjection2() {
        List<Projection> projections = query().from(cat).select(new QProjection(cat.name, cat)).fetch();
        assertFalse(projections.isEmpty());
        for (Projection projection : projections) {
            assertNotNull(projection);
        }
    }

    @Test
    public void Contains_Ic() {
        QFoo foo = QFoo.foo;
        assertEquals(1, query().from(foo).where(foo.bar.containsIgnoreCase("München")).fetchCount());
    }

    @Test
    public void Contains1() {
        assertEquals(1, query().from(cat).where(cat.name.contains("eli")).fetchCount());
    }

    @Test
    public void Contains2() {
        assertEquals(1L, query().from(cat).where(cat.kittens.contains(savedCats.get(0))).fetchCount());
    }

    @Test
    public void Contains3() {
        assertEquals(1L, query().from(cat).where(cat.name.contains("_")).fetchCount());
    }

    @Test
    public void Contains4() {
        QEmployee employee = QEmployee.employee;
        assertEquals(Arrays.asList(),
                query().from(employee)
                        .where(
                                employee.jobFunctions.contains(JobFunction.CODER),
                                employee.jobFunctions.contains(JobFunction.CONSULTANT),
                                employee.jobFunctions.size().eq(2))
                        .select(employee).fetch());
    }

    @Test
    public void Count() {
        QShow show = QShow.show;
        assertTrue(query().from(show).fetchCount() > 0);
    }

    @Test
    public void Count_Distinct() {
        QCat cat = QCat.cat;
        query().from(cat)
               .groupBy(cat.id)
               .select(cat.id, cat.breed.countDistinct()).fetch();
    }

    @Test
    @NoBatooJPA
    @NoHibernate
    public void Count_Distinct2() {
        QCat cat = QCat.cat;
        query().from(cat)
               .groupBy(cat.id)
               .select(cat.id, cat.birthdate.dayOfMonth().countDistinct()).fetch();
    }

    @Test
    public void DistinctResults() {
        System.out.println("-- fetch results");
        QueryResults<Date> res = query().from(cat).limit(2).select(cat.birthdate).fetchResults();
        assertEquals(2, res.getResults().size());
        assertEquals(6L, res.getTotal());
        System.out.println();

        System.out.println("-- fetch distinct results");
        res = query().from(cat).limit(2).distinct().select(cat.birthdate).fetchResults();
        assertEquals(1, res.getResults().size());
        assertEquals(1L, res.getTotal());
        System.out.println();

        System.out.println("-- fetch distinct");
        assertEquals(1, query().from(cat).distinct().select(cat.birthdate).fetch().size());
    }

    @Test
    public void Date() {
        assertEquals(2000,   query().from(cat).select(cat.birthdate.year()).fetchFirst().intValue());
        assertEquals(200002, query().from(cat).select(cat.birthdate.yearMonth()).fetchFirst().intValue());
        assertEquals(2,      query().from(cat).select(cat.birthdate.month()).fetchFirst().intValue());
        //query().from(cat).select(cat.birthdate.week());
        assertEquals(2,      query().from(cat).select(cat.birthdate.dayOfMonth()).fetchFirst().intValue());
        assertEquals(3,      query().from(cat).select(cat.birthdate.hour()).fetchFirst().intValue());
        assertEquals(4,      query().from(cat).select(cat.birthdate.minute()).fetchFirst().intValue());
        assertEquals(0,      query().from(cat).select(cat.birthdate.second()).fetchFirst().intValue());
    }

    @Test
    @ExcludeIn(ORACLE)
    public void Divide() {
        QSimpleTypes entity = new QSimpleTypes("entity1");
        QSimpleTypes entity2 = new QSimpleTypes("entity2");

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                .where(entity.ddouble.divide(entity2.ddouble).loe(2.0))
                .select(entity).fetch());

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                .where(entity.ddouble.divide(entity2.iint).loe(2.0))
                .select(entity).fetch());

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                .where(entity.iint.divide(entity2.ddouble).loe(2.0))
                .select(entity).fetch());

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                .where(entity.iint.divide(entity2.iint).loe(2))
                .select(entity).fetch());
    }

    @Test
    @ExcludeIn(ORACLE)
    public void Divide_BigDecimal() {
        QSimpleTypes entity = new QSimpleTypes("entity1");
        QSimpleTypes entity2 = new QSimpleTypes("entity2");
        NumberPath<BigDecimal> bigd1 = entity.bigDecimal;
        NumberPath<BigDecimal> bigd2 = entity2.bigDecimal;

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                        .where(bigd1.divide(bigd2).loe(new BigDecimal("1.00")))
                        .select(entity).fetch());

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                .where(entity.ddouble.divide(bigd2).loe(new BigDecimal("1.00")))
                .select(entity).fetch());

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                .where(bigd1.divide(entity.ddouble).loe(new BigDecimal("1.00")))
                .select(entity).fetch());
    }

    @Test
    public void EndsWith() {
        assertEquals(1, query().from(cat).where(cat.name.endsWith("h123")).fetchCount());
    }

    @Test
    public void EndsWith_IgnoreCase() {
        assertEquals(1, query().from(cat).where(cat.name.endsWithIgnoreCase("H123")).fetchCount());
    }

    @Test
    public void EndsWith2() {
        assertEquals(0, query().from(cat).where(cat.name.endsWith("X")).fetchCount());
    }

    @Test
    public void EndsWith3() {
        assertEquals(1, query().from(cat).where(cat.name.endsWith("_123")).fetchCount());
    }

    @Test
    @NoBatooJPA
    public void Enum_Eq() {
        assertEquals(1, query().from(company).where(company.ratingOrdinal.eq(Rating.A)).fetchCount());
        assertEquals(1, query().from(company).where(company.ratingString.eq(Rating.AA)).fetchCount());
    }

    @Test
    @NoBatooJPA
    public void Enum_In() {
        assertEquals(1, query().from(company).where(company.ratingOrdinal.in(Rating.A, Rating.AA)).fetchCount());
        assertEquals(1, query().from(company).where(company.ratingString.in(Rating.A, Rating.AA)).fetchCount());
    }

    @Test
    @NoBatooJPA
    public void Enum_In2() {
        QEmployee employee = QEmployee.employee;

        JPQLQuery<?> query = query();
        query.from(employee).where(employee.lastName.eq("Smith"), employee.jobFunctions
                .contains(JobFunction.CODER));
        assertEquals(1L, query.fetchCount());
    }

    @Test
    public void Enum_StartsWith() {
        assertEquals(1, query().from(company).where(company.ratingString.stringValue().startsWith("A")).fetchCount());
    }

    @Test
    @NoEclipseLink @NoOpenJPA @NoBatooJPA
    public void Fetch() {
        QMammal mammal = QMammal.mammal;
        QHuman human = new QHuman("mammal");
        query().from(mammal)
            .leftJoin(human.hairs).fetchJoin()
            .select(mammal).fetch();
    }

    @Test
    @NoEclipseLink @NoOpenJPA @NoBatooJPA
    public void Fetch2() {
        QWorld world = QWorld.world;
        QMammal mammal = QMammal.mammal;
        QHuman human = new QHuman("mammal");
        query().from(world)
            .leftJoin(world.mammals, mammal).fetchJoin()
            .leftJoin(human.hairs).fetchJoin()
            .select(world).fetch();
    }

    @Test
    @ExcludeIn({MYSQL, DERBY})
    @NoBatooJPA
    public void GroupBy() {
        QAuthor author = QAuthor.author;
        QBook book = QBook.book;

        for (int i = 0; i < 10; i++) {
            Author a = new Author();
            a.setName(String.valueOf(i));
            save(a);
            for (int j = 0; j < 2; j++) {
                Book b = new Book();
                b.setTitle(String.valueOf(i) + " " + String.valueOf(j));
                b.setAuthor(a);
                save(b);
            }
        }

        Map<Long, List<Pair<Long, String>>> map = query()
            .from(author)
            .join(author.books, book)
            .transform(GroupBy
                .groupBy(author.id)
                .as(GroupBy.list(QPair.create(book.id, book.title))));

        for (Entry<Long, List<Pair<Long, String>>> entry : map.entrySet()) {
            System.out.println("author = " + entry.getKey());

            for (Pair<Long,String> pair : entry.getValue()) {
                System.out.println("  book = " + pair.getFirst() + "," + pair.getSecond());
            }
        }
    }

    @Test
    public void GroupBy2() {
//        select cat0_.name as col_0_0_, cat0_.breed as col_1_0_, sum(cat0_.bodyWeight) as col_2_0_
//        from animal_ cat0_ where cat0_.DTYPE in ('C', 'DC') and cat0_.bodyWeight>?
//        group by cat0_.name , cat0_.breed
        query().from(cat)
            .where(cat.bodyWeight.gt(0))
            .groupBy(cat.name, cat.breed)
            .select(cat.name, cat.breed, cat.bodyWeight.sum()).fetch();
    }

    @Test
    @NoEclipseLink
    public void GroupBy_YearMonth() {
        query().from(cat)
               .groupBy(cat.birthdate.yearMonth())
               .orderBy(cat.birthdate.yearMonth().asc())
               .select(cat.id.count()).fetch();
    }

    @Test
    @Ignore // FIXME
    public void GroupBy_Count() {
        List<Integer> ids = query().from(cat).groupBy(cat.id).select(cat.id).fetch();
        long count = query().from(cat).groupBy(cat.id).fetchCount();
        QueryResults<Integer> results = query().from(cat).groupBy(cat.id)
                .limit(1).select(cat.id).fetchResults();

        long catCount = query().from(cat).fetchCount();
        assertEquals(catCount, ids.size());
        assertEquals(catCount, count);
        assertEquals(catCount, results.getResults().size());
        assertEquals(catCount, results.getTotal());
    }

    @Test
    @Ignore // FIXME
    public void GroupBy_Distinct_Count() {
        List<Integer> ids = query().from(cat).groupBy(cat.id).distinct().select(Expressions.ONE).fetch();
        QueryResults<Integer> results = query().from(cat).groupBy(cat.id)
                .limit(1).distinct().select(Expressions.ONE).fetchResults();

        assertEquals(1, ids.size());
        assertEquals(1, results.getResults().size());
        assertEquals(1, results.getTotal());
    }

    @Test
    public void In() {
        assertEquals(3L, query().from(cat).where(cat.name.in("Bob123", "Ruth123", "Felix123")).fetchCount());
        assertEquals(3L, query().from(cat).where(cat.id.in(Arrays.asList(1, 2, 3))).fetchCount());
        assertEquals(0L, query().from(cat).where(cat.name.in(Arrays.asList("A", "B", "C"))).fetchCount());
    }

    @Test
    public void In2() {
        assertEquals(3L, query().from(cat).where(cat.id.in(1, 2, 3)).fetchCount());
        assertEquals(0L, query().from(cat).where(cat.name.in("A", "B", "C")).fetchCount());
    }

    @Test
    public void In3() {
        assertEquals(0, query().from(cat).where(cat.name.in("A,B,C".split(","))).fetchCount());
    }

    @Test
    public void In4() {
        //$.parameterRelease.id.eq(releaseId).and($.parameterGroups.any().id.in(filter.getGroups()));
        assertEquals(Arrays.asList(),
                query().from(cat).where(cat.id.eq(1), cat.kittens.any().id.in(1, 2, 3)).select(cat).fetch());
    }

    @Test
    public void In5() {
        assertEquals(4L, query().from(cat).where(cat.mate.in(savedCats)).fetchCount());
    }

    @Test
    @Ignore
    public void In6() {
        //query().from(cat).where(cat.kittens.in(savedCats)).fetchCount();
    }

    @Test
    public void In7() {
        assertEquals(4L, query().from(cat).where(cat.kittens.any().in(savedCats)).fetchCount());
    }

    @Test
    public void In_Empty() {
        assertEquals(0, query().from(cat).where(cat.name.in(ImmutableList.<String>of())).fetchCount());
    }

    @Test
    @NoOpenJPA
    public void IndexOf() {
        assertEquals(Integer.valueOf(0), query().from(cat).where(cat.name.eq("Bob123"))
                .select(cat.name.indexOf("B")).fetchFirst());
    }

    @Test
    @NoOpenJPA
    public void IndexOf2() {
        assertEquals(Integer.valueOf(1), query().from(cat).where(cat.name.eq("Bob123"))
                .select(cat.name.indexOf("o")).fetchFirst());
    }

    @Test
    public void InstanceOf_Cat() {
        assertEquals(6L, query().from(cat).where(cat.instanceOf(Cat.class)).fetchCount());
    }

    @Test
    public void InstanceOf_DomesticCat() {
        assertEquals(0L, query().from(cat).where(cat.instanceOf(DomesticCat.class)).fetchCount());
    }

    @Test
    public void InstanceOf_Entity1() {
        QEntity1 entity1 = QEntity1.entity1;
        assertEquals(2L, query().from(entity1).where(entity1.instanceOf(Entity1.class)).fetchCount());
    }

    @Test
    public void InstanceOf_Entity2() {
        QEntity1 entity1 = QEntity1.entity1;
        assertEquals(1L, query().from(entity1).where(entity1.instanceOf(Entity2.class)).fetchCount());
    }

    @Test
    @NoHibernate // https://hibernate.atlassian.net/browse/HHH-6686
    public void IsEmpty_ElementCollection() {
        QEmployee employee = QEmployee.employee;
        assertEquals(0, query().from(employee).where(employee.jobFunctions.isEmpty()).fetchCount());
    }

    @Test
    public void IsEmpty_Relation() {
        assertEquals(6L, query().from(cat).where(cat.kittensSet.isEmpty()).fetchCount());
    }

    @Test
    @NoEclipseLink
    @ExcludeIn({ORACLE, TERADATA})
    public void JoinEmbeddable() {
        QBookVersion bookVersion = QBookVersion.bookVersion;
        QBookMark bookMark = QBookMark.bookMark;

        assertEquals(Arrays.asList(),
                query().from(bookVersion)
                        .join(bookVersion.definition.bookMarks, bookMark)
                        .where(
                                bookVersion.definition.bookMarks.size().eq(1),
                                bookMark.page.eq(2357L).or(bookMark.page.eq(2356L)))
                        .select(bookVersion).fetch());
    }

    @Test
    public void Length() {
        assertEquals(6, query().from(cat).where(cat.name.length().gt(0)).fetchCount());
    }

    @Test
    public void Like() {
        assertEquals(0, query().from(cat).where(cat.name.like("!")).fetchCount());
        assertEquals(0, query().from(cat).where(cat.name.like("\\")).fetchCount());
    }

    @Test
    public void Limit() {
        List<String> names1 = Arrays.asList("Allen123","Bob123");
        assertEquals(names1, query().from(cat).orderBy(cat.name.asc()).limit(2).select(cat.name).fetch());
    }

    @Test
    public void Limit_and_offset() {
        List<String> names3 = Arrays.asList("Felix123","Mary_123");
        assertEquals(names3, query().from(cat).orderBy(cat.name.asc()).limit(2).offset(2).select(cat.name).fetch());
    }

    @Test
    public void Limit2() {
        assertEquals(Collections.singletonList("Allen123"),
                query().from(cat).orderBy(cat.name.asc()).limit(1).select(cat.name).fetch());
    }

    @Test
    public void Limit3() {
        assertEquals(6, query().from(cat).limit(Long.MAX_VALUE).select(cat).fetch().size());
    }

    @Test
    public void List_ElementCollection_Of_Enum() {
        QEmployee employee = QEmployee.employee;
        //QJobFunction jobFunction = QJobFunction.jobFunction;
        EnumPath<JobFunction> jobFunction = Expressions.enumPath(JobFunction.class, "jf");

        List<JobFunction> jobFunctions = query().from(employee)
                .innerJoin(employee.jobFunctions, jobFunction).select(jobFunction).fetch();
        assertEquals(4, jobFunctions.size());
    }

    @Test
    @NoBatooJPA
    public void List_ElementCollection_Of_String() {
        QFoo foo = QFoo.foo;
        StringPath str = Expressions.stringPath("str");

        List<String> strings = query().from(foo).innerJoin(foo.names, str).select(str).fetch();
        assertEquals(2, strings.size());
        assertTrue(strings.contains("a"));
        assertTrue(strings.contains("b"));
    }

    @Test
    public void Map_Get() {
        QShow show = QShow.show;
        assertEquals(Arrays.asList("A"), query().from(show).select(show.acts.get("a")).fetch());
    }

    @Test
    @NoHibernate
    public void Map_Get2() {
        QShow show = QShow.show;
        assertEquals(1, query().from(show).where(show.acts.get("a").eq("A")).fetchCount());
    }

    @Test
    public void Map_ContainsKey() {
        QShow show = QShow.show;
        assertEquals(1L, query().from(show).where(show.acts.containsKey("a")).fetchCount());
    }

    @Test
    public void Map_ContainsKey2() {
        QShow show = QShow.show;
        assertEquals(1L, query().from(show).where(show.acts.containsKey("b")).fetchCount());
    }

    @Test
    public void Map_ContainsKey3() {
        QShow show = QShow.show;
        assertEquals(0L, query().from(show).where(show.acts.containsKey("c")).fetchCount());
    }

    @Test
    public void Map_ContainsValue() {
        QShow show = QShow.show;
        assertEquals(1L, query().from(show).where(show.acts.containsValue("A")).fetchCount());
    }

    @Test
    public void Map_ContainsValue2() {
        QShow show = QShow.show;
        assertEquals(1L, query().from(show).where(show.acts.containsValue("B")).fetchCount());
    }

    @Test
    public void Map_ContainsValue3() {
        QShow show = QShow.show;
        assertEquals(0L, query().from(show).where(show.acts.containsValue("C")).fetchCount());
    }

    @Test
    @Ignore
    public void Map_Join() {
        //select m.text from Show s join s.acts a where key(a) = 'B'
        QShow show = QShow.show;
        StringPath act = Expressions.stringPath("act");
        assertEquals(Arrays.asList(), query().from(show).join(show.acts, act).select(act).fetch());
    }

    @Test
    public void Max() {
        assertEquals(6.0, query().from(cat).select(cat.bodyWeight.max()).fetchFirst().doubleValue(), 0.0001);
    }

    @Test
    public void Min() {
        assertEquals(1.0, query().from(cat).select(cat.bodyWeight.min()).fetchFirst().doubleValue(), 0.0001);
    }

    @Test
    @ExcludeIn(ORACLE)
    public void Multiply() {
        QSimpleTypes entity = new QSimpleTypes("entity1");
        QSimpleTypes entity2 = new QSimpleTypes("entity2");

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                        .where(entity.ddouble.multiply(entity2.ddouble).loe(2.0))
                        .select(entity).fetch());
    }

    @Test
    @ExcludeIn(ORACLE)
    public void Multiply_BigDecimal() {
        QSimpleTypes entity = new QSimpleTypes("entity1");
        QSimpleTypes entity2 = new QSimpleTypes("entity2");
        NumberPath<BigDecimal> bigd1 = entity.bigDecimal;
        NumberPath<BigDecimal> bigd2 = entity2.bigDecimal;

        assertEquals(Arrays.asList(),
                query().from(entity, entity2)
                        .where(bigd1.multiply(bigd2).loe(new BigDecimal("1.00")))
                        .select(entity).fetch());
    }

    @Test
    public void NestedProjection() {
        Concatenation concat = new Concatenation(cat.name, cat.name);
        List<Tuple> tuples = query().from(cat).select(cat.name, concat).fetch();
        assertFalse(tuples.isEmpty());
        for (Tuple tuple : tuples) {
            assertEquals(
                tuple.get(concat),
                tuple.get(cat.name) + tuple.get(cat.name));
        }
    }

    @Test
    public void Not_In() {
        long all = query().from(cat).fetchCount();
        assertEquals(all - 3L, query().from(cat).where(cat.name.notIn("Bob123", "Ruth123", "Felix123")).fetchCount());

        assertEquals(3L, query().from(cat).where(cat.id.notIn(1, 2, 3)).fetchCount());
        assertEquals(6L, query().from(cat).where(cat.name.notIn("A", "B", "C")).fetchCount());
    }

    @Test
    @NoBatooJPA
    public void Not_In_Empty() {
        long count = query().from(cat).fetchCount();
        assertEquals(count, query().from(cat).where(cat.name.notIn(Collections.<String>emptyList())).fetchCount());
    }

    @Test
    public void Null_as_uniqueResult() {
        assertNull(query().from(cat).where(cat.name.eq(UUID.randomUUID().toString()))
                .select(cat).fetchFirst());
    }

    @Test
    @NoEclipseLink
    public void Numeric() {
        QNumeric numeric = QNumeric.numeric;
        BigDecimal singleResult = query().from(numeric).select(numeric.value).fetchFirst();
        assertEquals(26.9, singleResult.doubleValue(), 0.001);
    }

    @Test
    @NoOpenJPA
    @NoBatooJPA // FIXME
    public void Offset1() {
        List<String> names2 = Arrays.asList("Bob123", "Felix123", "Mary_123", "Ruth123", "Some");
        assertEquals(names2, query().from(cat).orderBy(cat.name.asc()).offset(1).select(cat.name).fetch());
    }

    @Test
    @NoOpenJPA
    @NoBatooJPA // FIXME
    public void Offset2() {
        List<String> names2 = Arrays.asList("Felix123", "Mary_123", "Ruth123", "Some");
        assertEquals(names2, query().from(cat).orderBy(cat.name.asc()).offset(2).select(cat.name).fetch());
    }

    @Test
    public void One_To_One() {
        QEmployee employee = QEmployee.employee;
        QUser user = QUser.user;

        JPQLQuery<?> query = query();
        query.from(employee);
        query.innerJoin(employee.user, user);
        query.select(employee).fetch();
    }

    @Test
    public void Order() {
        NumberPath<Double> weight = Expressions.numberPath(Double.class, "weight");
        assertEquals(Arrays.asList(1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
                query().from(cat).orderBy(weight.asc()).select(cat.bodyWeight.as(weight)).fetch());
    }

    @Test
    public void Order_By_Count() {
        NumberPath<Long> count = Expressions.numberPath(Long.class, "c");
        query().from(cat)
            .groupBy(cat.id)
            .orderBy(count.asc())
            .select(cat.id, cat.id.count().as(count)).fetch();
    }

    @Test
    public void Order_StringValue() {
        int count = (int) query().from(cat).fetchCount();
        assertEquals(count, query().from(cat).orderBy(cat.id.stringValue().asc()).select(cat).fetch().size());
    }

    @Test
    @NoBatooJPA // can't be parsed
    public void Order_StringValue_To_Integer() {
        int count = (int) query().from(cat).fetchCount();
        assertEquals(count, query().from(cat).orderBy(cat.id.stringValue().castToNum(Integer.class).asc()).select(cat).fetch().size());
    }

    @Test
    @NoBatooJPA // can't be parsed
    public void Order_StringValue_ToLong() {
        int count = (int) query().from(cat).fetchCount();
        assertEquals(count, query().from(cat).orderBy(cat.id.stringValue().castToNum(Long.class).asc()).select(cat).fetch().size());
    }

    @Test
    @NoBatooJPA // can't be parsed
    public void Order_StringValue_ToBigInteger() {
        int count = (int) query().from(cat).fetchCount();
        assertEquals(count, query().from(cat).orderBy(cat.id.stringValue().castToNum(BigInteger.class).asc()).select(cat).fetch().size());
    }

    @Test
    @NoBatooJPA
    public void Order_NullsFirst() {
        assertNull(query().from(cat)
            .orderBy(cat.dateField.asc().nullsFirst())
            .select(cat.dateField).fetchFirst());
    }

    @Test
    @NoBatooJPA
    public void Order_NullsLast() {
        assertNotNull(query().from(cat)
            .orderBy(cat.dateField.asc().nullsLast())
            .select(cat.dateField).fetchFirst());
    }

    @Test
    public void Params() {
        Param<String> name = new Param<String>(String.class,"name");
        assertEquals("Bob123",query().from(cat).where(cat.name.eq(name)).set(name, "Bob123")
                .select(cat.name).fetchFirst());
    }

    @Test
    public void Params_anon() {
        Param<String> name = new Param<String>(String.class);
        assertEquals("Bob123",query().from(cat).where(cat.name.eq(name)).set(name, "Bob123")
                .select(cat.name).fetchFirst());
    }

    @Test(expected = ParamNotSetException.class)
    public void Params_not_set() {
        Param<String> name = new Param<String>(String.class,"name");
        assertEquals("Bob123", query().from(cat).where(cat.name.eq(name)).select(cat.name).fetchFirst());
    }

    @Test
    public void Precedence() {
        StringPath str = cat.name;
        Predicate where = str.like("Bob%").and(str.like("%ob123"))
                      .or(str.like("Ruth%").and(str.like("%uth123")));
        assertEquals(2L, query().from(cat).where(where).fetchCount());
    }

    @Test
    public void Precedence2() {
        StringPath str = cat.name;
        Predicate where = str.like("Bob%").and(str.like("%ob123")
                      .or(str.like("Ruth%"))).and(str.like("%uth123"));
        assertEquals(0L, query().from(cat).where(where).fetchCount());
    }

    @Test
    public void Precedence3() {
        Predicate where = cat.name.eq("Bob123").and(cat.id.eq(1))
                      .or(cat.name.eq("Ruth123").and(cat.id.eq(2)));
        assertEquals(2L, query().from(cat).where(where).fetchCount());
    }

    @Test
    public void FactoryExpression_In_GroupBy() {
        Expression<Cat> catBean = Projections.bean(Cat.class, cat.id, cat.name);
        assertFalse(query().from(cat).groupBy(catBean).select(catBean).fetch().isEmpty());
    }

    @Test
    @Ignore
    public void Size() {
        // NOT SUPPORTED
        query().from(cat).select(cat, cat.kittens.size()).fetch();
    }

    @Test
    public void StartsWith() {
        assertEquals(1, query().from(cat).where(cat.name.startsWith("R")).fetchCount());
    }

    @Test
    public void StartsWith_IgnoreCase() {
        assertEquals(1, query().from(cat).where(cat.name.startsWithIgnoreCase("r")).fetchCount());
    }

    @Test
    public void StartsWith2() {
        assertEquals(0, query().from(cat).where(cat.name.startsWith("X")).fetchCount());
    }

    @Test
    public void StartsWith3() {
        assertEquals(1, query().from(cat).where(cat.name.startsWith("Mary_")).fetchCount());
    }

    @Test
    @ExcludeIn({MYSQL, TERADATA})
    @NoOpenJPA
    public void StringOperations() {
        // NOTE : locate in MYSQL is case-insensitive
        assertEquals(0, query().from(cat).where(cat.name.startsWith("r")).fetchCount());
        assertEquals(0, query().from(cat).where(cat.name.endsWith("H123")).fetchCount());
        assertEquals(Integer.valueOf(2), query().from(cat).where(cat.name.eq("Bob123"))
                .select(cat.name.indexOf("b")).fetchFirst());
    }

    @Test
    public void SubQuery() {
        QShow show = QShow.show;
        QShow show2 = new QShow("show2");
        assertEquals(0,
                query().from(show).where(select(show2.count()).from(show2)
                        .where(show2.id.ne(show.id)).gt(0L)).fetchCount());
    }

    @Test
    public void SubQuery2() {
        QCat cat = QCat.cat;
        QCat other = new QCat("other");
        assertEquals(savedCats, query().from(cat)
                .where(cat.name.in(select(other.name).from(other)
                        .groupBy(other.name)))
                .orderBy(cat.id.asc())
                .select(cat).fetch());
    }

    @Test
    public void SubQuery3() {
        QCat cat = QCat.cat;
        QCat other = new QCat("other");
        assertEquals(savedCats.subList(0, 1), query().from(cat)
                .where(cat.name.eq(select(other.name).from(other)
                        .where(other.name.indexOf("B").eq(0))))
                .select(cat).fetch());
    }

    @Test
    public void SubQuery4() {
        QCat cat = QCat.cat;
        QCat other = new QCat("other");
        query().from(cat)
                .select(cat.name, select(other.count()).from(other).where(other.name.eq(cat.name))).fetch();
    }

    @Test
    public void SubQuery5() {
        QEmployee employee = QEmployee.employee;
        QEmployee employee2 = new QEmployee("e2");
        assertEquals(2, query().from(employee)
                .where(select(employee2.id.count()).from(employee2).gt(1L))
                .fetchCount());
    }

    @Test
    public void Substring() {
        for (String str : query().from(cat).select(cat.name.substring(1,2)).fetch()) {
            assertEquals(1, str.length());
        }
    }

    @Test
    @NoBatooJPA
    @ExcludeIn(ORACLE)
    public void Substring2() {
        QCompany company = QCompany.company;
        StringExpression name = company.name;
        Integer companyId = query().from(company).select(company.id).fetchFirst();
        JPQLQuery<?> query = query().from(company).where(company.id.eq(companyId));
        String str = query.select(company.name).fetchFirst();

        assertEquals(Integer.valueOf(29),
                query.select(name.length().subtract(11)).fetchFirst());

        assertEquals(str.substring(0, 7),
                query.select(name.substring(0, 7)).fetchFirst());

        assertEquals(str.substring(15),
                query.select(name.substring(15)).fetchFirst());

        assertEquals(str.substring(str.length()),
                query.select(name.substring(name.length())).fetchFirst());

        assertEquals(str.substring(str.length() - 11),
                query.select(name.substring(name.length().subtract(11))).fetchFirst());
    }

    @Test
    @Ignore // FIXME
    @ExcludeIn(DERBY)
    public void Substring_From_Right() {
        assertEquals(Arrays.asList(), query().from(cat)
                .where(cat.name.substring(-1, 1).eq(cat.name.substring(-2, 1)))
                .select(cat).fetch());
    }

    @Test
    @ExcludeIn({HSQLDB, DERBY})
    public void Substring_From_Right2() {
        assertEquals(Arrays.asList(), query().from(cat)
                .where(cat.name.substring(cat.name.length().subtract(1), cat.name.length())
                        .eq(cat.name.substring(cat.name.length().subtract(2), cat.name.length().subtract(1))))
                .select(cat).fetch());
    }

    @Test
    @ExcludeIn(ORACLE)
    public void Subtract_BigDecimal() {
        QSimpleTypes entity = new QSimpleTypes("entity1");
        QSimpleTypes entity2 = new QSimpleTypes("entity2");
        NumberPath<BigDecimal> bigd1 = entity.bigDecimal;
        NumberPath<BigDecimal> bigd2 = entity2.bigDecimal;

        assertEquals(Arrays.asList(), query().from(entity, entity2)
                .where(bigd1.subtract(bigd2).loe(new BigDecimal("1.00")))
                .select(entity).fetch());
    }

    @Test
    @Ignore
    public void Sum() throws RecognitionException, TokenStreamException {
        // NOT SUPPORTED
        query().from(cat).select(cat.kittens.size().sum()).fetch();
    }

    @Test
    @Ignore
    public void Sum_2() throws RecognitionException, TokenStreamException {
        // NOT SUPPORTED
        query().from(cat).where(cat.kittens.size().sum().gt(0)).select(cat).fetch();
    }

    @Test
    public void Sum_3() {
        assertEquals(21.0, query().from(cat).select(cat.bodyWeight.sum()).fetchFirst().doubleValue(), 0.0001);
    }

    @Test
    public void Sum_3_Projected() {
        double val = query().from(cat).select(cat.bodyWeight.sum()).fetchFirst();
        DoubleProjection projection = query().from(cat)
                .select(new QDoubleProjection(cat.bodyWeight.sum())).fetchFirst();
        assertEquals(val, projection.val, 0.001);
    }

    @Test
    public void Sum_4() {
        Double dbl = query().from(cat).select(cat.bodyWeight.sum().negate()).fetchFirst();
        assertNotNull(dbl);
    }

    @Test
    public void Sum_5() {
        QShow show = QShow.show;
        Long lng = query().from(show).select(show.id.sum()).fetchFirst();
        assertNotNull(lng);
    }

    @Test
    public void Sum_of_Integer() {
        QCat cat2 = new QCat("cat2");
        assertEquals(Arrays.asList(), query().from(cat)
                .where(select(cat2.breed.sum())
                        .from(cat2).where(cat2.eq(cat.mate)).gt(0))
                .select(cat).fetch());
    }

    @Test
    public void Sum_of_Float() {
        QCat cat2 = new QCat("cat2");
        query().from(cat)
               .where(select(cat2.floatProperty.sum())
                      .from(cat2).where(cat2.eq(cat.mate)).gt(0.0f))
               .select(cat).fetch();
    }

    @Test
    public void Sum_of_Double() {
        QCat cat2 = new QCat("cat2");
        query().from(cat)
               .where(select(cat2.bodyWeight.sum())
                      .from(cat2).where(cat2.eq(cat.mate)).gt(0.0))
               .select(cat).fetch();
    }

    @Test
    public void Sum_as_Float() {
        float val = query().from(cat).select(cat.floatProperty.sum()).fetchFirst();
        assertTrue(val > 0);
    }

    @Test
    public void Sum_as_Float_Projected() {
        float val = query().from(cat).select(cat.floatProperty.sum()).fetchFirst();
        FloatProjection projection = query().from(cat)
                .select(new QFloatProjection(cat.floatProperty.sum())).fetchFirst();
        assertEquals(val, projection.val, 0.001);
    }

    @Test
    public void Sum_as_Float2() {
        float val = query().from(cat).select(cat.floatProperty.sum().negate()).fetchFirst();
        assertTrue(val < 0);
    }

    @Test
    public void Sum_Coalesce() {
        int val = query().from(cat).select(cat.weight.sum().coalesce(0)).fetchFirst();
        assertTrue(val == 0);
    }

    @Test
    public void Sum_NoRows_Double() {
        assertEquals(null, query().from(cat)
                .where(cat.name.eq(UUID.randomUUID().toString()))
                .select(cat.bodyWeight.sum()).fetchFirst());
    }

    @Test
    public void Sum_NoRows_Float() {
        assertEquals(null, query().from(cat)
                .where(cat.name.eq(UUID.randomUUID().toString()))
                .select(cat.floatProperty.sum()).fetchFirst());
    }

    @Test
    @NoEclipseLink @NoOpenJPA @NoBatooJPA
    public void test() {
        Cat kitten = savedCats.get(0);
        Cat noKitten = savedCats.get(savedCats.size() - 1);

        ProjectionsFactory projections = new ProjectionsFactory(Module.JPA, getTarget()) {
            @Override
            public <A,Q extends SimpleExpression<A>> Collection<Expression<?>> list(ListPath<A,Q> expr,
                    ListExpression<A,Q> other, A knownElement) {
                // NOTE : expr.get(0) is only supported in the where clause
                return Collections.<Expression<?>>singleton(expr.size());
            }
        };

        final EntityPath<?>[] sources = new EntityPath[]{cat, otherCat};
        final Predicate[] conditions = new Predicate[]{condition};
        final Expression<?>[] projection = new Expression[]{cat.name, otherCat.name};

        QueryExecution standardTest = new QueryExecution(
                projections,
                new FilterFactory(projections, Module.JPA, getTarget()),
                new MatchingFiltersFactory(Module.JPA, getTarget())) {

            @Override
            protected Fetchable createQuery() {
                // NOTE : EclipseLink needs extra conditions cond1 and code2
                return testQuery().from(sources).where(conditions);
            }

            @Override
            protected Fetchable createQuery(Predicate filter) {
                // NOTE : EclipseLink needs extra conditions cond1 and code2
                return testQuery().from(sources).where(condition, filter).select(projection);
            }
        };

        // standardTest.runArrayTests(cat.kittensArray, otherCat.kittensArray, kitten, noKitten);
        standardTest.runBooleanTests(cat.name.isNull(), otherCat.kittens.isEmpty());
        standardTest.runCollectionTests(cat.kittens, otherCat.kittens, kitten, noKitten);
        standardTest.runDateTests(cat.dateField, otherCat.dateField, date);
        standardTest.runDateTimeTests(cat.birthdate, otherCat.birthdate, birthDate);
        standardTest.runListTests(cat.kittens, otherCat.kittens, kitten, noKitten);
        // standardTest.mapTests(cat.kittensByName, otherCat.kittensByName, "Kitty", kitten);

        // int
        standardTest.runNumericCasts(cat.id, otherCat.id, 1);
        standardTest.runNumericTests(cat.id, otherCat.id, 1);

        // double
        standardTest.runNumericCasts(cat.bodyWeight, otherCat.bodyWeight, 1.0);
        standardTest.runNumericTests(cat.bodyWeight, otherCat.bodyWeight, 1.0);

        standardTest.runStringTests(cat.name, otherCat.name, kitten.getName());
        standardTest.runTimeTests(cat.timeField, otherCat.timeField, time);

        standardTest.report();
    }

    @Test
    public void TupleProjection() {
        List<Tuple> tuples = query().from(cat).select(cat.name, cat).fetch();
        assertFalse(tuples.isEmpty());
        for (Tuple tuple : tuples) {
            assertNotNull(tuple.get(cat.name));
            assertNotNull(tuple.get(cat));
        }
    }

    @Test
    public void TupleProjection_As_QueryResults() {
        QueryResults<Tuple> tuples = query().from(cat).limit(1)
                .select(cat.name, cat).fetchResults();
        assertEquals(1, tuples.getResults().size());
        assertTrue(tuples.getTotal() > 0);
    }

    @Test
    @ExcludeIn(DERBY)
    public void Transform_GroupBy() {
        QCat kitten = new QCat("kitten");
        Map<Integer, Cat> result = query().from(cat).innerJoin(cat.kittens, kitten)
            .transform(GroupBy.groupBy(cat.id)
                    .as(Projections.constructor(Cat.class, cat.name, cat.id,
                            GroupBy.list(Projections.constructor(Cat.class, kitten.name, kitten.id)))));

        for (Cat entry : result.values()) {
            assertEquals(1, entry.getKittens().size());
        }
    }

    @Test
    @ExcludeIn(DERBY)
    public void Transform_GroupBy2() {
        QCat kitten = new QCat("kitten");
        Map<List<?>, Group> result = query().from(cat).innerJoin(cat.kittens, kitten)
            .transform(GroupBy.groupBy(cat.id, kitten.id)
                    .as(cat, kitten));

        assertFalse(result.isEmpty());
        for (Tuple row : query().from(cat).innerJoin(cat.kittens, kitten)
                .select(cat, kitten).fetch()) {
            assertNotNull(result.get(Arrays.asList(row.get(cat).getId(), row.get(kitten).getId())));
        }
    }

    @Test
    @ExcludeIn(DERBY)
    public void Transform_GroupBy_Alias() {
        QCat kitten = new QCat("kitten");
        SimplePath<Cat> k = Expressions.path(Cat.class, "k");
        Map<Integer, Group> result = query().from(cat).innerJoin(cat.kittens, kitten)
            .transform(GroupBy.groupBy(cat.id)
                    .as(cat.name, cat.id,
                        GroupBy.list(Projections.constructor(Cat.class, kitten.name, kitten.id).as(k))));

        for (Group entry : result.values()) {
            assertNotNull(entry.getOne(cat.id));
            assertNotNull(entry.getOne(cat.name));
            assertFalse(entry.getList(k).isEmpty());
        }
    }

    @Test
    @NoBatooJPA
    public void Treat() {
        QDomesticCat domesticCat = QDomesticCat.domesticCat;
        assertEquals(0, query().from(cat)
                .innerJoin(cat.mate, domesticCat._super)
                .where(domesticCat.name.eq("Bobby"))
                .fetchCount());
    }

    @Test
    @Ignore
    public void Type() {
        assertEquals(Arrays.asList("C","C","C","C","C","C","A"),
                query().from(animal).orderBy(animal.id.asc()).select(JPAExpressions.type(animal)).fetch());
    }

    @Test
    @NoOpenJPA
    public void Type_Order() {
        assertEquals(Arrays.asList(10,1,2,3,4,5,6),
                query().from(animal).orderBy(JPAExpressions.type(animal).asc(), animal.id.asc())
                        .select(animal.id).fetch());
    }
}

