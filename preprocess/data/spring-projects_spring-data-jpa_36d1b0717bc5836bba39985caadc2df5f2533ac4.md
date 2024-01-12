Refactoring Types: ['Move Class']
amework/data/jpa/repository/augment/JpaSoftDeleteQueryAugmentor.java
/*
 * Copyright 2013 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.springframework.data.jpa.repository.augment;

import java.lang.reflect.Method;

import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.Predicate;

import org.springframework.beans.BeanWrapper;
import org.springframework.data.jpa.repository.support.JpaCriteriaQueryContext;
import org.springframework.data.jpa.repository.support.JpaQueryContext;
import org.springframework.data.jpa.repository.support.JpaUpdateContext;
import org.springframework.data.repository.SoftDelete;
import org.springframework.data.repository.augment.AbstractSoftDeleteQueryAugmentor;
import org.springframework.data.repository.augment.QueryContext.QueryMode;
import org.springframework.data.util.DirectFieldAccessFallbackBeanWrapper;
import org.springframework.util.ReflectionUtils;

/**
 * JPA implementation of {@link AbstractSoftDeleteQueryAugmentor} to transparently turn delete calls into entity
 * updates. Also filters queries accordingly.
 * 
 * @author Oliver Gierke
 */
public class JpaSoftDeleteQueryAugmentor extends
		AbstractSoftDeleteQueryAugmentor<JpaCriteriaQueryContext<?, ?>, JpaQueryContext, JpaUpdateContext<?>> {

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.augment.AnnotationBasedQueryAugmentor#prepareNativeQuery(org.springframework.data.repository.augment.QueryContext, java.lang.annotation.Annotation)
	 */
	@Override
	protected JpaQueryContext prepareNativeQuery(JpaQueryContext context, SoftDelete expression) {

		if (!context.getMode().in(QueryMode.FIND)) {
			return context;
		}

		String string = context.getQueryString();
		// TODO: Augment query;

		return context.withQuery(string);
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.sample.JpaSoftDeleteQueryAugmentor#prepareQuery(org.springframework.data.jpa.repository.support.JpaCriteriaQueryContext, org.springframework.data.jpa.repository.support.GlobalFilter)
	 */
	@Override
	protected JpaCriteriaQueryContext<?, ?> prepareQuery(JpaCriteriaQueryContext<?, ?> context, SoftDelete expression) {

		CriteriaQuery<?> criteriaQuery = context.getQuery();
		CriteriaBuilder builder = context.getCriteriaBuilder();

		Predicate predicate = builder.equal(context.getRoot().get(expression.value()), expression.flagMode().activeValue());
		Predicate restriction = criteriaQuery.getRestriction();

		criteriaQuery.where(restriction == null ? predicate : builder.and(restriction, predicate));

		return context;
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.augment.AbstractSoftDeleteQueryAugmentor#updateDeletedState(java.lang.Object)
	 */
	@Override
	public void updateDeletedState(Object entity, JpaUpdateContext<?> context) {
		context.getEntityManager().merge(entity);
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.augment.AbstractSoftDeleteQueryAugmentor#prepareBeanWrapper(org.springframework.data.repository.augment.UpdateContext)
	 */
	@Override
	protected BeanWrapper createBeanWrapper(JpaUpdateContext<?> context) {
		return new PropertyChangeEnsuringBeanWrapper(context.getEntity());
	}

	/**
	 * Custom {@link DirectFieldAccessFallbackBeanWrapper} to hook in additional functionality when setting a property by
	 * field access.
	 * 
	 * @author Oliver Gierke
	 */
	private static class PropertyChangeEnsuringBeanWrapper extends DirectFieldAccessFallbackBeanWrapper {

		public PropertyChangeEnsuringBeanWrapper(Object entity) {
			super(entity);
		}

		/**
		 * We in case of setting the value using field access, we need to make sure that EclipseLink detects the change.
		 * Hence we check for an EclipseLink specific generated method that is used to record the changes and invoke it if
		 * available.
		 * 
		 * @see org.springframework.data.support.DirectFieldAccessFallbackBeanWrapper#setPropertyUsingFieldAccess(java.lang.String,
		 *      java.lang.Object)
		 */
		@Override
		public void setPropertyValue(String propertyName, Object value) {

			Object oldValue = getPropertyValue(propertyName);
			super.setPropertyValue(propertyName, value);
			triggerPropertyChangeMethodIfAvailable(propertyName, oldValue, value);
		}

		private void triggerPropertyChangeMethodIfAvailable(String propertyName, Object oldValue, Object value) {

			Method method = ReflectionUtils.findMethod(getWrappedClass(), "_persistence_propertyChange", String.class,
					Object.class, Object.class);

			if (method == null) {
				return;
			}

			ReflectionUtils.invokeMethod(method, getWrappedInstance(), propertyName, oldValue, value);
		}
	}
}


File: src/main/java/org/springframework/data/jpa/repository/query/AbstractStringBasedJpaQuery.java
/*
 * Copyright 2008-2014 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.springframework.data.jpa.repository.query;

import javax.persistence.EntityManager;
import javax.persistence.Query;

import org.springframework.data.jpa.repository.support.JpaQueryContext;
import org.springframework.data.repository.augment.QueryAugmentationEngine;
import org.springframework.data.repository.augment.QueryContext.QueryMode;
import org.springframework.data.repository.query.EvaluationContextProvider;
import org.springframework.data.repository.query.ParameterAccessor;
import org.springframework.data.repository.query.ParametersParameterAccessor;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.util.Assert;

/**
 * Base class for {@link String} based JPA queries.
 * 
 * @author Oliver Gierke
 * @author Thomas Darimont
 */
abstract class AbstractStringBasedJpaQuery extends AbstractJpaQuery {

	private final StringQuery query;
	private final StringQuery countQuery;
	private final EvaluationContextProvider evaluationContextProvider;
	private final SpelExpressionParser parser;

	/**
	 * Creates a new {@link AbstractStringBasedJpaQuery} from the given {@link JpaQueryMethod}, {@link EntityManager} and
	 * query {@link String}.
	 * 
	 * @param method must not be {@literal null}.
	 * @param em must not be {@literal null}.
	 * @param queryString must not be {@literal null}.
	 * @param evaluationContextProvider must not be {@literal null}.
	 * @param parser must not be {@literal null}.
	 */
	public AbstractStringBasedJpaQuery(JpaQueryMethod method, EntityManager em, String queryString,
			EvaluationContextProvider evaluationContextProvider, SpelExpressionParser parser) {

		super(method, em);

		Assert.hasText(queryString, "Query string must not be null or empty!");
		Assert.notNull(evaluationContextProvider, "ExpressionEvaluationContextProvider must not be null!");
		Assert.notNull(parser, "Parser must not be null or empty!");

		this.evaluationContextProvider = evaluationContextProvider;
		this.query = new ExpressionBasedStringQuery(queryString, method.getEntityInformation(), parser);
		this.countQuery = new StringQuery(method.getCountQuery() != null ? method.getCountQuery()
				: QueryUtils.createCountQueryFor(this.query.getQueryString(), method.getCountQueryProjection()));
		this.parser = parser;
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.query.AbstractJpaQuery#doCreateQuery(java.lang.Object[])
	 */
	@Override
	public Query doCreateQuery(Object[] values) {

		ParameterAccessor accessor = new ParametersParameterAccessor(getQueryMethod().getParameters(), values);
		String sortedQueryString = QueryUtils.applySorting(query.getQueryString(), accessor.getSort(), query.getAlias());

		Query query = createJpaQuery(sortedQueryString);

		return createBinder(values).bindAndPrepare(query);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.query.AbstractJpaQuery#createBinder(java.lang.Object[])
	 */
	@Override
	protected ParameterBinder createBinder(Object[] values) {
		return new SpelExpressionStringQueryParameterBinder(getQueryMethod().getParameters(), values, query,
				evaluationContextProvider, parser);
	}

	/**
	 * Creates an appropriate JPA query from an {@link EntityManager} according to the current {@link AbstractJpaQuery}
	 * type.
	 * 
	 * @param queryString
	 * @return
	 */
	public Query createJpaQuery(String queryString) {
		Query query = getEntityManager().createQuery(queryString);
		query = potentiallyAugment(query);
		return query;
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.query.AbstractJpaQuery#doCreateCountQuery(java.lang.Object[])
	 */
	@Override
	protected Query doCreateCountQuery(Object[] values) {

		String queryString = countQuery.getQueryString();
		EntityManager em = getEntityManager();

		return createBinder(values).bind(
				getQueryMethod().isNativeQuery() ? em.createNativeQuery(queryString) : em.createQuery(queryString, Long.class));
	}

	/**
	 * @return the query
	 */
	public StringQuery getQuery() {
		return query;
	}

	/**
	 * @return the countQuery
	 */
	public StringQuery getCountQuery() {
		return countQuery;
	}

	protected Query potentiallyAugment(Query query) {
		return potentiallyAugment(query, QueryMode.FIND);
	}

	private Query potentiallyAugment(Query query, QueryMode mode) {

		QueryAugmentationEngine engine = getAugmentationEngine();

		if (engine.augmentationNeeded(JpaQueryContext.class, mode, getQueryMethod().getEntityInformation())) {
			JpaQueryContext context = new JpaQueryContext(mode, getEntityManager(), query);
			return engine.invokeAugmentors(context).getQuery();
		} else {
			return query;
		}
	}
}


File: src/main/java/org/springframework/data/jpa/repository/support/JpaQueryContext.java
/*
 * Copyright 2013 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.springframework.data.jpa.repository.support;

import javax.persistence.EntityManager;
import javax.persistence.Query;

import org.springframework.data.jpa.repository.query.QueryExtractor;
import org.springframework.data.repository.augment.QueryContext;

/**
 * @author Oliver Gierke
 */
public class JpaQueryContext extends QueryContext<Query> {

	private final EntityManager entityManager;
	private final QueryExtractor extractor;

	/**
	 * @param query
	 * @param queryMode
	 */
	public JpaQueryContext(QueryMode queryMode, EntityManager entityManager, Query query) {

		super(query, queryMode);
		this.entityManager = entityManager;
		this.extractor = PersistenceProvider.fromEntityManager(entityManager);
	}

	/**
	 * @return the entityManager
	 */
	public EntityManager getEntityManager() {
		return entityManager;
	}

	public String getQueryString() {
		return extractor.extractQueryString(getQuery());
	}

	@SuppressWarnings("unchecked")
	public JpaQueryContext withQuery(String query) {

		Query createQuery = entityManager.createQuery(query);
		return new JpaQueryContext(getMode(), entityManager, createQuery);
	}
}


File: src/main/java/org/springframework/data/jpa/repository/support/QueryDslJpaRepository.java
/*
 * Copyright 2008-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.springframework.data.jpa.repository.support;

import java.io.Serializable;
import java.util.Collections;
import java.util.List;
import java.util.Map.Entry;

import javax.persistence.EntityManager;
import javax.persistence.LockModeType;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.querydsl.EntityPathResolver;
import org.springframework.data.querydsl.QSort;
import org.springframework.data.querydsl.QueryDslPredicateExecutor;
import org.springframework.data.querydsl.SimpleEntityPathResolver;

import com.mysema.query.jpa.JPQLQuery;
import com.mysema.query.jpa.impl.JPAQuery;
import com.mysema.query.types.EntityPath;
import com.mysema.query.types.OrderSpecifier;
import com.mysema.query.types.Predicate;
import com.mysema.query.types.path.PathBuilder;

/**
 * QueryDsl specific extension of {@link SimpleJpaRepository} which adds implementation for
 * {@link QueryDslPredicateExecutor}.
 * 
 * @author Oliver Gierke
 * @author Thomas Darimont
 */
public class QueryDslJpaRepository<T, ID extends Serializable> extends SimpleJpaRepository<T, ID> implements
		QueryDslPredicateExecutor<T> {

	private static final EntityPathResolver DEFAULT_ENTITY_PATH_RESOLVER = SimpleEntityPathResolver.INSTANCE;

	private final EntityPath<T> path;
	private final PathBuilder<T> builder;
	private final Querydsl querydsl;

	/**
	 * Creates a new {@link QueryDslJpaRepository} from the given domain class and {@link EntityManager}. This will use
	 * the {@link SimpleEntityPathResolver} to translate the given domain class into an {@link EntityPath}.
	 * 
	 * @param entityInformation must not be {@literal null}.
	 * @param entityManager must not be {@literal null}.
	 */
	public QueryDslJpaRepository(JpaEntityInformation<T, ID> entityInformation, EntityManager entityManager) {
		this(entityInformation, entityManager, DEFAULT_ENTITY_PATH_RESOLVER);
	}

	/**
	 * Creates a new {@link QueryDslJpaRepository} from the given domain class and {@link EntityManager} and uses the
	 * given {@link EntityPathResolver} to translate the domain class into an {@link EntityPath}.
	 * 
	 * @param entityInformation must not be {@literal null}.
	 * @param entityManager must not be {@literal null}.
	 * @param resolver must not be {@literal null}.
	 */
	public QueryDslJpaRepository(JpaEntityInformation<T, ID> entityInformation, EntityManager entityManager,
			EntityPathResolver resolver) {

		super(entityInformation, entityManager);
		this.path = resolver.createPath(entityInformation.getJavaType());
		this.builder = new PathBuilder<T>(path.getType(), path.getMetadata());
		this.querydsl = new Querydsl(entityManager, builder);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.querydsl.QueryDslPredicateExecutor#findOne(com.mysema.query.types.Predicate)
	 */
	@Override
	public T findOne(Predicate predicate) {
		return createQuery(predicate).uniqueResult(path);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.querydsl.QueryDslPredicateExecutor#findAll(com.mysema.query.types.Predicate)
	 */
	@Override
	public List<T> findAll(Predicate predicate) {
		return createQuery(predicate).list(path);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.querydsl.QueryDslPredicateExecutor#findAll(com.mysema.query.types.Predicate, com.mysema.query.types.OrderSpecifier<?>[])
	 */
	@Override
	public List<T> findAll(Predicate predicate, OrderSpecifier<?>... orders) {
		return executeSorted(createQuery(predicate), orders);
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.querydsl.QueryDslPredicateExecutor#findAll(com.mysema.query.types.Predicate, org.springframework.data.domain.Sort)
	 */
	@Override
	public List<T> findAll(Predicate predicate, Sort sort) {
		return executeSorted(createQuery(predicate), sort);
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.querydsl.QueryDslPredicateExecutor#findAll(com.mysema.query.types.OrderSpecifier[])
	 */
	@Override
	public List<T> findAll(OrderSpecifier<?>... orders) {
		return executeSorted(createQuery(new Predicate[0]), orders);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.querydsl.QueryDslPredicateExecutor#findAll(com.mysema.query.types.Predicate, org.springframework.data.domain.Pageable)
	 */
	@Override
	public Page<T> findAll(Predicate predicate, Pageable pageable) {

		JPQLQuery countQuery = createQuery(predicate);
		JPQLQuery query = querydsl.applyPagination(pageable, createQuery(predicate));

		Long total = countQuery.count();
		List<T> content = total > pageable.getOffset() ? query.list(path) : Collections.<T> emptyList();

		return new PageImpl<T>(content, pageable, total);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.querydsl.QueryDslPredicateExecutor#count(com.mysema.query.types.Predicate)
	 */
	@Override
	public long count(Predicate predicate) {
		return createQuery(predicate).count();
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.querydsl.QueryDslPredicateExecutor#exists(com.mysema.query.types.Predicate)
	 */
	@Override
	public boolean exists(Predicate predicate) {
		return createQuery(predicate).exists();
	}

	/**
	 * Creates a new {@link JPQLQuery} for the given {@link Predicate}.
	 * 
	 * @param predicate
	 * @return the Querydsl {@link JPQLQuery}.
	 */
	protected JPQLQuery createQuery(Predicate... predicate) {

		JPAQuery query = querydsl.createQuery(path).where(predicate);
		CrudMethodMetadata metadata = getRepositoryMethodMetadata();

		if (metadata == null) {
			return query;
		}

		LockModeType type = metadata.getLockModeType();
		query = type == null ? query : query.setLockMode(type);

		for (Entry<String, Object> hint : getQueryHints().entrySet()) {
			query.setHint(hint.getKey(), hint.getValue());
		}

		return query;
	}

	/**
	 * Executes the given {@link JPQLQuery} after applying the given {@link OrderSpecifier}s.
	 * 
	 * @param query must not be {@literal null}.
	 * @param orders must not be {@literal null}.
	 * @return
	 */
	private List<T> executeSorted(JPQLQuery query, OrderSpecifier<?>... orders) {
		return executeSorted(query, new QSort(orders));
	}

	/**
	 * Executes the given {@link JPQLQuery} after applying the given {@link Sort}.
	 * 
	 * @param query must not be {@literal null}.
	 * @param sort must not be {@literal null}.
	 * @return
	 */
	private List<T> executeSorted(JPQLQuery query, Sort sort) {
		return querydsl.applySorting(sort, query).list(path);
	}
}


File: src/main/java/org/springframework/data/jpa/repository/support/SimpleJpaRepository.java
/*
 * Copyright 2008-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.springframework.data.jpa.repository.support;

import static org.springframework.data.jpa.repository.query.QueryUtils.*;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import javax.persistence.EntityManager;
import javax.persistence.LockModeType;
import javax.persistence.NoResultException;
import javax.persistence.Parameter;
import javax.persistence.Query;
import javax.persistence.TypedQuery;
import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.ParameterExpression;
import javax.persistence.criteria.Path;
import javax.persistence.criteria.Predicate;
import javax.persistence.criteria.Root;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.data.jpa.provider.PersistenceProvider;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.query.Jpa21Utils;
import org.springframework.data.jpa.repository.query.JpaEntityGraph;
import org.springframework.data.jpa.repository.query.QueryUtils;
import org.springframework.data.repository.augment.QueryAugmentationEngine;
import org.springframework.data.repository.augment.QueryAugmentationEngineAware;
import org.springframework.data.repository.augment.QueryContext.QueryMode;
import org.springframework.data.repository.augment.UpdateContext.UpdateMode;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.Assert;

/**
 * Default implementation of the {@link org.springframework.data.repository.CrudRepository} interface. This will offer
 * you a more sophisticated interface than the plain {@link EntityManager} .
 * 
 * @author Oliver Gierke
 * @author Eberhard Wolff
 * @author Thomas Darimont
 * @param <T> the type of the entity to handle
 * @param <ID> the type of the entity's identifier
 */
@Repository
@Transactional(readOnly = true)
public class SimpleJpaRepository<T, ID extends Serializable> implements JpaRepository<T, ID>,
		JpaSpecificationExecutor<T>, QueryAugmentationEngineAware {

	private static final String ID_MUST_NOT_BE_NULL = "The given id must not be null!";

	private final JpaEntityInformation<T, ?> entityInformation;
	private final EntityManager em;
	private final PersistenceProvider provider;

	private CrudMethodMetadata metadata;
	private QueryAugmentationEngine engine = QueryAugmentationEngine.NONE;

	/**
	 * Creates a new {@link SimpleJpaRepository} to manage objects of the given {@link JpaEntityInformation}.
	 * 
	 * @param entityInformation must not be {@literal null}.
	 * @param entityManager must not be {@literal null}.
	 */
	public SimpleJpaRepository(JpaEntityInformation<T, ?> entityInformation, EntityManager entityManager) {

		Assert.notNull(entityInformation);
		Assert.notNull(entityManager);

		this.entityInformation = entityInformation;
		this.em = entityManager;
		this.provider = PersistenceProvider.fromEntityManager(entityManager);
	}

	/**
	 * Creates a new {@link SimpleJpaRepository} to manage objects of the given domain type.
	 * 
	 * @param domainClass must not be {@literal null}.
	 * @param em must not be {@literal null}.
	 */
	public SimpleJpaRepository(Class<T> domainClass, EntityManager em) {
		this(JpaEntityInformationSupport.getEntityInformation(domainClass, em), em);
	}

	/**
	 * Configures a custom {@link CrudMethodMetadata} to be used to detect {@link LockModeType}s and query hints to be
	 * applied to queries.
	 * 
	 * @param crudMethodMetadata
	 */
	public void setRepositoryMethodMetadata(CrudMethodMetadata crudMethodMetadata) {
		this.metadata = crudMethodMetadata;
	}

	protected CrudMethodMetadata getRepositoryMethodMetadata() {
		return metadata;
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.core.support.QueryAugmentationEngineAware#setQueryAugmentationEngine(org.springframework.data.repository.core.support.QueryAugmentationEngine)
	 */
	public void setQueryAugmentationEngine(QueryAugmentationEngine engine) {
		this.engine = engine;
	}

	private Class<T> getDomainClass() {
		return entityInformation.getJavaType();
	}

	private String getDeleteAllQueryString() {
		return getQueryString(DELETE_ALL_QUERY_STRING, entityInformation.getEntityName());
	}

	private String getCountQueryString() {

		String countQuery = String.format(COUNT_QUERY_STRING, provider.getCountQueryPlaceholder(), "%s");
		return getQueryString(countQuery, entityInformation.getEntityName());
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.CrudRepository#delete(java.io.Serializable)
	 */
	@Transactional
	public void delete(ID id) {

		Assert.notNull(id, ID_MUST_NOT_BE_NULL);

		T entity = findOne(id);

		if (entity == null) {
			throw new EmptyResultDataAccessException(String.format("No %s entity with id %s exists!",
					entityInformation.getJavaType(), id), 1);
		}

		delete(entity);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.CrudRepository#delete(java.lang.Object)
	 */
	@Transactional
	public void delete(T entity) {

		Assert.notNull(entity, "The entity must not be null!");

		entity = em.contains(entity) ? entity : em.merge(entity);

		if (engine.augmentationNeeded(JpaUpdateContext.class, null, entityInformation)) {

			JpaUpdateContext<T> context = new JpaUpdateContext<T>(entity, UpdateMode.DELETE, em);
			context = engine.invokeAugmentors(context);

			if (context == null) {
				return;
			}
		}

		em.remove(entity);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.CrudRepository#delete(java.lang.Iterable)
	 */
	@Transactional
	public void delete(Iterable<? extends T> entities) {

		Assert.notNull(entities, "The given Iterable of entities not be null!");

		for (T entity : entities) {
			delete(entity);
		}
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaRepository#deleteInBatch(java.lang.Iterable)
	 */
	@Transactional
	public void deleteInBatch(Iterable<T> entities) {

		Assert.notNull(entities, "The given Iterable of entities not be null!");

		if (!entities.iterator().hasNext()) {
			return;
		}

		applyAndBind(getQueryString(DELETE_ALL_QUERY_STRING, entityInformation.getEntityName()), entities, em)
				.executeUpdate();
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.Repository#deleteAll()
	 */
	@Transactional
	public void deleteAll() {

		for (T element : findAll()) {
			delete(element);
		}
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaRepository#deleteAllInBatch()
	 */
	@Transactional
	public void deleteAllInBatch() {
		em.createQuery(getDeleteAllQueryString()).executeUpdate();
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.CrudRepository#findOne(java.io.Serializable)
	 */
	public T findOne(ID id) {

		Assert.notNull(id, ID_MUST_NOT_BE_NULL);

		Class<T> domainType = getDomainClass();

		if (engine.augmentationNeeded(JpaCriteriaQueryContext.class, QueryMode.FIND, entityInformation)) {

			CriteriaBuilder builder = em.getCriteriaBuilder();
			CriteriaQuery<T> query = builder.createQuery(domainType);
			Root<T> root = query.from(domainType);

			JpaCriteriaQueryContext<T, T> context = potentiallyAugment(query, root, QueryMode.FIND);
			try {

				return em.createQuery(context.getQuery()).getSingleResult();
			} catch (NoResultException e) {
				return null;
			}
		}

		if (metadata == null) {
			return em.find(domainType, id);
		}

		LockModeType type = metadata.getLockModeType();

		Map<String, Object> hints = getQueryHints();

		return type == null ? em.find(domainType, id, hints) : em.find(domainType, id, type, hints);
	}

	/**
	 * Returns a {@link Map} with the query hints based on the current {@link CrudMethodMetadata} and potential
	 * {@link EntityGraph} information.
	 * 
	 * @return
	 */
	protected Map<String, Object> getQueryHints() {

		if (metadata.getEntityGraph() == null) {
			return metadata.getQueryHints();
		}

		Map<String, Object> hints = new HashMap<String, Object>();
		hints.putAll(metadata.getQueryHints());

		hints.putAll(Jpa21Utils.tryGetFetchGraphHints(em, getEntityGraph(), getDomainClass()));

		return hints;
	}

	private JpaEntityGraph getEntityGraph() {

		String fallbackName = this.entityInformation.getEntityName() + "." + metadata.getMethod().getName();
		return new JpaEntityGraph(metadata.getEntityGraph(), fallbackName);
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaRepository#getOne(java.io.Serializable)
	 */
	@Override
	public T getOne(ID id) {

		Assert.notNull(id, ID_MUST_NOT_BE_NULL);
		return em.getReference(getDomainClass(), id);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.CrudRepository#exists(java.io.Serializable)
	 */
	public boolean exists(ID id) {

		Assert.notNull(id, ID_MUST_NOT_BE_NULL);

		if (entityInformation.getIdAttribute() == null) {
			return findOne(id) != null;
		}

		String placeholder = provider.getCountQueryPlaceholder();
		String entityName = entityInformation.getEntityName();
		Iterable<String> idAttributeNames = entityInformation.getIdAttributeNames();
		String existsQuery = QueryUtils.getExistsQueryString(entityName, placeholder, idAttributeNames);

		TypedQuery<Long> query = em.createQuery(existsQuery, Long.class);

		if (!entityInformation.hasCompositeId()) {
			query.setParameter(idAttributeNames.iterator().next(), id);
			return query.getSingleResult() == 1L;
		}

		for (String idAttributeName : idAttributeNames) {

			Object idAttributeValue = entityInformation.getCompositeIdAttributeValue(id, idAttributeName);

			boolean complexIdParameterValueDiscovered = idAttributeValue != null
					&& !query.getParameter(idAttributeName).getParameterType().isAssignableFrom(idAttributeValue.getClass());

			if (complexIdParameterValueDiscovered) {

				// fall-back to findOne(id) which does the proper mapping for the parameter.
				return findOne(id) != null;
			}

			query.setParameter(idAttributeName, idAttributeValue);
		}

		return query.getSingleResult() == 1L;
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaRepository#findAll()
	 */
	public List<T> findAll() {
		return getQuery(null, (Sort) null).getResultList();
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.CrudRepository#findAll(ID[])
	 */
	public List<T> findAll(Iterable<ID> ids) {

		if (ids == null || !ids.iterator().hasNext()) {
			return Collections.emptyList();
		}

		if (entityInformation.hasCompositeId()) {

			List<T> results = new ArrayList<T>();

			for (ID id : ids) {
				results.add(findOne(id));
			}

			return results;
		}

		ByIdsSpecification<T> specification = new ByIdsSpecification<T>(entityInformation);
		TypedQuery<T> query = getQuery(specification, (Sort) null);

		return query.setParameter(specification.parameter, ids).getResultList();
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaRepository#findAll(org.springframework.data.domain.Sort)
	 */
	public List<T> findAll(Sort sort) {
		return getQuery(null, sort).getResultList();
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.PagingAndSortingRepository#findAll(org.springframework.data.domain.Pageable)
	 */
	public Page<T> findAll(Pageable pageable) {

		if (null == pageable) {
			return new PageImpl<T>(findAll());
		}

		return findAll(null, pageable);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaSpecificationExecutor#findOne(org.springframework.data.jpa.domain.Specification)
	 */
	public T findOne(Specification<T> spec) {

		try {
			return getQuery(spec, (Sort) null).getSingleResult();
		} catch (NoResultException e) {
			return null;
		}
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaSpecificationExecutor#findAll(org.springframework.data.jpa.domain.Specification)
	 */
	public List<T> findAll(Specification<T> spec) {
		return getQuery(spec, (Sort) null).getResultList();
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaSpecificationExecutor#findAll(org.springframework.data.jpa.domain.Specification, org.springframework.data.domain.Pageable)
	 */
	public Page<T> findAll(Specification<T> spec, Pageable pageable) {

		TypedQuery<T> query = getQuery(spec, pageable);
		return pageable == null ? new PageImpl<T>(query.getResultList()) : readPage(query, pageable, spec);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaSpecificationExecutor#findAll(org.springframework.data.jpa.domain.Specification, org.springframework.data.domain.Sort)
	 */
	public List<T> findAll(Specification<T> spec, Sort sort) {

		return getQuery(spec, sort).getResultList();
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.CrudRepository#count()
	 */
	public long count() {
		return count(null);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaSpecificationExecutor#count(org.springframework.data.jpa.domain.Specification)
	 */
	public long count(Specification<T> spec) {
		return executeCountQuery(getCountQuery(spec));
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.repository.CrudRepository#save(java.lang.Object)
	 */
	@Transactional
	public <S extends T> S save(S entity) {

		if (entityInformation.isNew(entity)) {
			em.persist(entity);
			return entity;
		} else {
			return em.merge(entity);
		}
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaRepository#saveAndFlush(java.lang.Object)
	 */
	@Transactional
	public <S extends T> S saveAndFlush(S entity) {

		S result = save(entity);
		flush();

		return result;
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaRepository#save(java.lang.Iterable)
	 */
	@Transactional
	public <S extends T> List<S> save(Iterable<S> entities) {

		List<S> result = new ArrayList<S>();

		if (entities == null) {
			return result;
		}

		for (S entity : entities) {
			result.add(save(entity));
		}

		return result;
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.JpaRepository#flush()
	 */
	@Transactional
	public void flush() {

		em.flush();
	}

	/**
	 * Reads the given {@link TypedQuery} into a {@link Page} applying the given {@link Pageable} and
	 * {@link Specification}.
	 * 
	 * @param query must not be {@literal null}.
	 * @param spec can be {@literal null}.
	 * @param pageable can be {@literal null}.
	 * @return
	 */
	protected Page<T> readPage(TypedQuery<T> query, Pageable pageable, Specification<T> spec) {

		query.setFirstResult(pageable.getOffset());
		query.setMaxResults(pageable.getPageSize());

		Long total = executeCountQuery(getCountQuery(spec));
		List<T> content = total > pageable.getOffset() ? query.getResultList() : Collections.<T> emptyList();

		return new PageImpl<T>(content, pageable, total);
	}

	/**
	 * Creates a new {@link TypedQuery} from the given {@link Specification}.
	 * 
	 * @param spec can be {@literal null}.
	 * @param pageable can be {@literal null}.
	 * @return
	 */
	protected TypedQuery<T> getQuery(Specification<T> spec, Pageable pageable) {

		Sort sort = pageable == null ? null : pageable.getSort();
		return getQuery(spec, sort);
	}

	/**
	 * Creates a {@link TypedQuery} for the given {@link Specification} and {@link Sort}.
	 * 
	 * @param spec can be {@literal null}.
	 * @param sort can be {@literal null}.
	 * @return
	 */
	protected TypedQuery<T> getQuery(Specification<T> spec, Sort sort) {

		CriteriaBuilder builder = em.getCriteriaBuilder();
		CriteriaQuery<T> query = builder.createQuery(getDomainClass());

		Root<T> root = applySpecificationToCriteria(spec, query);

		JpaCriteriaQueryContext<T, T> context = potentiallyAugment(query, root, QueryMode.FIND);
		query = context.getQuery();
		root = context.getRoot();

		query.select(root);

		if (sort != null) {
			query.orderBy(toOrders(sort, root, builder));
		}

		return applyRepositoryMethodMetadata(em.createQuery(query));
	}

	/**
	 * Creates a new count query for the given {@link Specification}.
	 * 
	 * @param spec can be {@literal null}.
	 * @return
	 */
	protected TypedQuery<Long> getCountQuery(Specification<T> spec) {

		CriteriaBuilder builder = em.getCriteriaBuilder();
		CriteriaQuery<Long> query = builder.createQuery(Long.class);

		Root<T> root = applySpecificationToCriteria(spec, query);

		JpaCriteriaQueryContext<Long, T> context = potentiallyAugment(query, root, QueryMode.COUNT);
		query = context.getQuery();
		root = context.getRoot();

		if (query.isDistinct()) {
			query.select(builder.countDistinct(root));
		} else {
			query.select(builder.count(root));
		}

		return em.createQuery(query);
	}

	/**
	 * Applies the given {@link Specification} to the given {@link CriteriaQuery}.
	 * 
	 * @param spec can be {@literal null}.
	 * @param query must not be {@literal null}.
	 * @return
	 */
	private <S> Root<T> applySpecificationToCriteria(Specification<T> spec, CriteriaQuery<S> query) {

		Assert.notNull(query);
		Root<T> root = query.from(getDomainClass());

		if (spec == null) {
			return root;
		}

		CriteriaBuilder builder = em.getCriteriaBuilder();
		Predicate predicate = spec.toPredicate(root, query, builder);

		if (predicate != null) {
			query.where(predicate);
		}

		return root;
	}

	private TypedQuery<T> applyRepositoryMethodMetadata(TypedQuery<T> query) {

		if (metadata == null) {
			return query;
		}

		LockModeType type = metadata.getLockModeType();
		TypedQuery<T> toReturn = type == null ? query : query.setLockMode(type);

		applyQueryHints(toReturn);

		return toReturn;
	}

	private void applyQueryHints(Query query) {

		for (Entry<String, Object> hint : getQueryHints().entrySet()) {
			query.setHint(hint.getKey(), hint.getValue());
		}
	}

	/**
	 * Executes a count query and transparently sums up all values returned.
	 * 
	 * @param query must not be {@literal null}.
	 * @return
	 */
	private static Long executeCountQuery(TypedQuery<Long> query) {

		Assert.notNull(query);

		List<Long> totals = query.getResultList();
		Long total = 0L;

		for (Long element : totals) {
			total += element == null ? 0 : element;
		}

		return total;
	}

	/**
	 * Specification that gives access to the {@link Parameter} instance used to bind the ids for
	 * {@link SimpleJpaRepository#findAll(Iterable)}. Workaround for OpenJPA not binding collections to in-clauses
	 * correctly when using by-name binding.
	 * 
	 * @see https://issues.apache.org/jira/browse/OPENJPA-2018?focusedCommentId=13924055
	 * @author Oliver Gierke
	 */
	@SuppressWarnings("rawtypes")
	private static final class ByIdsSpecification<T> implements Specification<T> {

		private final JpaEntityInformation<T, ?> entityInformation;

		ParameterExpression<Iterable> parameter;

		public ByIdsSpecification(JpaEntityInformation<T, ?> entityInformation) {
			this.entityInformation = entityInformation;
		}

		/*
		 * (non-Javadoc)
		 * @see org.springframework.data.jpa.domain.Specification#toPredicate(javax.persistence.criteria.Root, javax.persistence.criteria.CriteriaQuery, javax.persistence.criteria.CriteriaBuilder)
		 */
		public Predicate toPredicate(Root<T> root, CriteriaQuery<?> query, CriteriaBuilder cb) {

			Path<?> path = root.get(entityInformation.getIdAttribute());
			parameter = cb.parameter(Iterable.class);
			return path.in(parameter);
		}
	}

	private <S> JpaCriteriaQueryContext<S, T> potentiallyAugment(CriteriaQuery<S> query, Root<T> root, QueryMode mode) {

		JpaCriteriaQueryContext<S, T> context = new JpaCriteriaQueryContext<S, T>(mode, em, query, root);

		if (engine.augmentationNeeded(JpaCriteriaQueryContext.class, mode, entityInformation)) {
			context = engine.invokeAugmentors(context);
		}

		return context;
	}
}


File: src/test/java/org/springframework/data/jpa/repository/support/SoftDeleteIntegrationTests.java
/*
 * Copyright 2013 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.springframework.data.jpa.repository.support;

import static org.hamcrest.Matchers.*;
import static org.junit.Assert.*;

import java.util.ArrayList;
import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.data.jpa.domain.sample.User;
import org.springframework.data.jpa.repository.augment.JpaSoftDeleteQueryAugmentor;
import org.springframework.data.repository.CrudRepository;
import org.springframework.data.repository.SoftDelete;
import org.springframework.data.repository.SoftDelete.FlagMode;
import org.springframework.data.repository.augment.QueryAugmentor;
import org.springframework.data.repository.augment.QueryContext;
import org.springframework.data.repository.augment.UpdateContext;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import org.springframework.transaction.annotation.Transactional;

/**
 * @author Oliver Gierke
 */
@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration("classpath:infrastructure.xml")
@Transactional
public class SoftDeleteIntegrationTests {

	@PersistenceContext
	EntityManager em;

	SoftUserRepository softRepository;
	SpecialUserRepository repository;

	@Before
	public void setUp() {

		JpaRepositoryFactory factory = new JpaRepositoryFactory(em);
		JpaSoftDeleteQueryAugmentor augmentor = new JpaSoftDeleteQueryAugmentor();

		List<QueryAugmentor<? extends QueryContext<?>, ? extends QueryContext<?>, ? extends UpdateContext<?>>> augmentors = new ArrayList<QueryAugmentor<? extends QueryContext<?>, ? extends QueryContext<?>, ? extends UpdateContext<?>>>();
		augmentors.add(augmentor);

		factory.setQueryAugmentors(augmentors);

		softRepository = factory.getRepository(SoftUserRepository.class);
		repository = factory.getRepository(SpecialUserRepository.class);
	}

	@Test
	public void basicSaveAndDelete() {

		User user = new User("Foo", "Bar", "foo@bar.de");
		user = softRepository.save(user);

		assertThat(repository.findAll(), hasItem(user));
		assertThat(softRepository.findAll(), hasItem(user));

		softRepository.delete(user);

		assertThat(softRepository.findAll(), is(emptyIterable()));
		assertThat(softRepository.count(), is(0L));
		assertThat(softRepository.findOne(user.getId()), is(nullValue()));

		assertThat(repository.count(), is(1L));
		assertThat(repository.findAll(), hasItem(user));
		assertThat(repository.findOne(user.getId()), is(notNullValue()));
	}

	@SoftDelete(value = "active", flagMode = FlagMode.ACTIVE)
	interface SoftUserRepository extends CrudRepository<User, Integer> {

		List<User> findByLastname();
	}

	interface SpecialUserRepository extends CrudRepository<User, Integer> {

		List<User> findAll();
	}
}
