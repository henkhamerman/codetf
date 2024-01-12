Refactoring Types: ['Extract Method']
ork/data/jpa/repository/query/PartTreeJpaQuery.java
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

import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.Query;
import javax.persistence.TypedQuery;
import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;

import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.provider.PersistenceProvider;
import org.springframework.data.jpa.repository.query.JpaQueryExecution.DeleteExecution;
import org.springframework.data.jpa.repository.query.ParameterMetadataProvider.ParameterMetadata;
import org.springframework.data.jpa.repository.support.JpaCriteriaQueryContext;
import org.springframework.data.jpa.repository.support.JpaEntityInformation;
import org.springframework.data.jpa.repository.support.JpaEntityInformationSupport;
import org.springframework.data.repository.augment.QueryAugmentationEngine;
import org.springframework.data.repository.augment.QueryContext.QueryMode;
import org.springframework.data.repository.query.ParametersParameterAccessor;
import org.springframework.data.repository.query.parser.PartTree;

/**
 * A {@link AbstractJpaQuery} implementation based on a {@link PartTree}.
 * 
 * @author Oliver Gierke
 * @author Thomas Darimont
 */
public class PartTreeJpaQuery extends AbstractJpaQuery {

	private final Class<?> domainClass;
	private final PartTree tree;
	private final JpaParameters parameters;

	private final QueryPreparer query;
	private final QueryPreparer countQuery;
	private final EntityManager em;

	private final JpaEntityInformation<?, ?> entityInformation;

	/**
	 * Creates a new {@link PartTreeJpaQuery}.
	 * 
	 * @param method must not be {@literal null}.
	 * @param em must not be {@literal null}.
	 */
	public PartTreeJpaQuery(JpaQueryMethod method, EntityManager em) {

		super(method, em);
		this.em = em;

		this.domainClass = method.getEntityInformation().getJavaType();
		this.tree = new PartTree(method.getName(), domainClass);
		this.parameters = method.getParameters();

		this.countQuery = new CountQueryPreparer(parameters.potentiallySortsDynamically());
		this.query = tree.isCountProjection() ? countQuery : new QueryPreparer(parameters.potentiallySortsDynamically());

		this.entityInformation = JpaEntityInformationSupport.getEntityInformation(method.getReturnedObjectType(), em);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.query.AbstractJpaQuery#doCreateQuery(java.lang.Object[])
	 */
	@Override
	public Query doCreateQuery(Object[] values) {
		return query.createQuery(values);
	}

	/*
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.query.AbstractJpaQuery#doCreateCountQuery(java.lang.Object[])
	 */
	@Override
	@SuppressWarnings("unchecked")
	public TypedQuery<Long> doCreateCountQuery(Object[] values) {
		return (TypedQuery<Long>) countQuery.createQuery(values);
	}

	/* 
	 * (non-Javadoc)
	 * @see org.springframework.data.jpa.repository.query.AbstractJpaQuery#getExecution()
	 */
	@Override
	protected JpaQueryExecution getExecution() {
		return this.tree.isDelete() ? new DeleteExecution(em) : super.getExecution();
	}

	/**
	 * Query preparer to create {@link CriteriaQuery} instances and potentially cache them.
	 * 
	 * @author Oliver Gierke
	 * @author Thomas Darimont
	 */
	private class QueryPreparer {

		private final CriteriaQuery<?> cachedCriteriaQuery;
		private final List<ParameterMetadata<?>> expressions;

		public QueryPreparer(boolean recreateQueries) {

			JpaQueryCreator creator = createCreator(null);
			this.cachedCriteriaQuery = recreateQueries ? null : creator.createQuery();
			this.expressions = recreateQueries ? null : creator.getParameterExpressions();
		}

		/**
		 * Creates a new {@link Query} for the given parameter values.
		 * 
		 * @param values
		 * @return
		 */
		public Query createQuery(Object[] values) {

			CriteriaQuery<?> criteriaQuery = cachedCriteriaQuery;
			List<ParameterMetadata<?>> expressions = this.expressions;
			ParametersParameterAccessor accessor = new ParametersParameterAccessor(parameters, values);

			if (cachedCriteriaQuery == null || accessor.hasBindableNullValue()) {
				JpaQueryCreator creator = createCreator(accessor);
				criteriaQuery = potentiallyAugment(creator.createQuery(getDynamicSort(values)));
				expressions = creator.getParameterExpressions();
			}

			TypedQuery<?> jpaQuery = createQuery(criteriaQuery);

			return restrictMaxResultsIfNecessary(invokeBinding(getBinder(values, expressions), jpaQuery));
		}

		/**
		 * Restricts the max results of the given {@link Query} if the current {@code tree} marks this {@code query} as
		 * limited.
		 * 
		 * @param query
		 * @return
		 */
		private Query restrictMaxResultsIfNecessary(Query query) {

			if (tree.isLimiting()) {

				if (query.getMaxResults() != Integer.MAX_VALUE) {
					/*
					 * In order to return the correct results, we have to adjust the first result offset to be returned if:
					 * - a Pageable parameter is present 
					 * - AND the requested page number > 0
					 * - AND the requested page size was bigger than the derived result limitation via the First/Top keyword.
					 */
					if (query.getMaxResults() > tree.getMaxResults() && query.getFirstResult() > 0) {
						query.setFirstResult(query.getFirstResult() - (query.getMaxResults() - tree.getMaxResults()));
					}
				}

				query.setMaxResults(tree.getMaxResults());
			}

			return query;
		}

		/**
		 * Checks whether we are working with a cached {@link CriteriaQuery} and snychronizes the creation of a
		 * {@link TypedQuery} instance from it. This is due to non-thread-safety in the {@link CriteriaQuery} implementation
		 * of some persistence providers (i.e. Hibernate in this case).
		 * 
		 * @see DATAJPA-396
		 * @param criteriaQuery must not be {@literal null}.
		 * @return
		 */
		private TypedQuery<?> createQuery(CriteriaQuery<?> criteriaQuery) {

			if (this.cachedCriteriaQuery != null) {
				synchronized (this.cachedCriteriaQuery) {
					return getEntityManager().createQuery(criteriaQuery);
				}
			}

			return getEntityManager().createQuery(criteriaQuery);
		}

		protected <T> CriteriaQuery<T> potentiallyAugment(CriteriaQuery<T> query) {
			return potentiallyAugment(query, QueryMode.FIND);
		}

		private <T> CriteriaQuery<T> potentiallyAugment(CriteriaQuery<T> query, QueryMode mode) {

			QueryAugmentationEngine engine = getAugmentationEngine();

			if (engine.augmentationNeeded(JpaCriteriaQueryContext.class, mode, entityInformation)) {
				JpaCriteriaQueryContext<T, T> context = new JpaCriteriaQueryContext<T, T>(mode, getEntityManager(), query,
						entityInformation, null);
				return engine.invokeAugmentors(context).getQuery();
			} else {
				return query;
			}
		}

		protected JpaQueryCreator createCreator(ParametersParameterAccessor accessor) {

			EntityManager entityManager = getEntityManager();
			CriteriaBuilder builder = entityManager.getCriteriaBuilder();
			PersistenceProvider persistenceProvider = PersistenceProvider.fromEntityManager(entityManager);

			ParameterMetadataProvider provider = accessor == null ? new ParameterMetadataProvider(builder, parameters,
					persistenceProvider) : new ParameterMetadataProvider(builder, accessor, persistenceProvider);

			return new JpaQueryCreator(tree, domainClass, builder, provider);
		}

		/**
		 * Invokes parameter binding on the given {@link TypedQuery}.
		 * 
		 * @param binder
		 * @param query
		 * @return
		 */
		protected Query invokeBinding(ParameterBinder binder, TypedQuery<?> query) {

			return binder.bindAndPrepare(query);
		}

		private ParameterBinder getBinder(Object[] values, List<ParameterMetadata<?>> expressions) {
			return new CriteriaQueryParameterBinder(parameters, values, expressions);
		}

		private Sort getDynamicSort(Object[] values) {

			return parameters.potentiallySortsDynamically() ? new ParametersParameterAccessor(parameters, values).getSort()
					: null;
		}
	}

	/**
	 * Special {@link QueryPreparer} to create count queries.
	 * 
	 * @author Oliver Gierke
	 * @author Thomas Darimont
	 */
	private class CountQueryPreparer extends QueryPreparer {

		public CountQueryPreparer(boolean recreateQueries) {
			super(recreateQueries);
		}

		/*
		 * (non-Javadoc)
		 * @see org.springframework.data.jpa.repository.query.PartTreeJpaQuery.QueryPreparer#createCreator(org.springframework.data.repository.query.ParametersParameterAccessor)
		 */
		@Override
		protected JpaQueryCreator createCreator(ParametersParameterAccessor accessor) {

			EntityManager entityManager = getEntityManager();
			CriteriaBuilder builder = entityManager.getCriteriaBuilder();
			PersistenceProvider persistenceProvider = PersistenceProvider.fromEntityManager(entityManager);

			ParameterMetadataProvider provider = accessor == null ? new ParameterMetadataProvider(builder, parameters,
					persistenceProvider) : new ParameterMetadataProvider(builder, accessor, persistenceProvider);

			return new JpaCountQueryCreator(tree, domainClass, builder, provider);
		}

		/* 
		 * (non-Javadoc)
		 * @see org.springframework.data.jpa.repository.query.PartTreeJpaQuery.QueryPreparer#potentiallyAugment(javax.persistence.criteria.CriteriaQuery)
		 */
		@Override
		protected <T> CriteriaQuery<T> potentiallyAugment(CriteriaQuery<T> query) {
			return super.potentiallyAugment(query, QueryMode.COUNT_FOR_PAGING);
		}

		/**
		 * Customizes binding by skipping the pagination.
		 * 
		 * @see org.springframework.data.jpa.repository.query.PartTreeJpaQuery.QueryPreparer#invokeBinding(org.springframework.data.jpa.repository.query.ParameterBinder,
		 *      javax.persistence.TypedQuery)
		 */
		@Override
		protected Query invokeBinding(ParameterBinder binder, javax.persistence.TypedQuery<?> query) {
			return binder.bind(query);
		}
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

	private final JpaEntityInformation<T, ID> entityInformation;
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
	public SimpleJpaRepository(JpaEntityInformation<T, ID> entityInformation, EntityManager entityManager) {

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
		this((JpaEntityInformation<T, ID>) JpaEntityInformationSupport.getEntityInformation(domainClass, em), em);
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

	/**
	 * @return the engine
	 */
	protected QueryAugmentationEngine getAugmentationEngine() {
		return engine;
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

			ParameterExpression<ID> idParameter = builder.parameter(entityInformation.getIdType(), "id");
			query.select(root).where(builder.equal(root.get(entityInformation.getIdAttribute()), idParameter));

			JpaCriteriaQueryContext<T, T> context = potentiallyAugment(query, root, QueryMode.FIND);

			try {

				TypedQuery<T> jpaQuery = em.createQuery(context.getQuery());
				jpaQuery.setParameter(idParameter, id);

				return jpaQuery.getSingleResult();

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

		JpaCriteriaQueryContext<S, T> context = new JpaCriteriaQueryContext<S, T>(mode, em, query, entityInformation, root);

		if (engine.augmentationNeeded(JpaCriteriaQueryContext.class, mode, entityInformation)) {
			context = engine.invokeAugmentors(context);
		}

		return context;
	}
}


File: src/test/java/org/springframework/data/jpa/repository/support/JpaRepositoryFactoryUnitTests.java
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

import static org.hamcrest.CoreMatchers.*;
import static org.junit.Assert.*;
import static org.mockito.Mockito.*;

import java.io.IOException;
import java.io.Serializable;

import javax.persistence.EntityManager;
import javax.persistence.EntityManagerFactory;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.runners.MockitoJUnitRunner;
import org.springframework.aop.framework.Advised;
import org.springframework.data.jpa.domain.sample.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.custom.CustomGenericJpaRepositoryFactory;
import org.springframework.data.jpa.repository.custom.UserCustomExtendedRepository;
import org.springframework.data.querydsl.QueryDslPredicateExecutor;
import org.springframework.data.repository.core.support.DefaultRepositoryMetadata;
import org.springframework.data.repository.query.QueryLookupStrategy.Key;
import org.springframework.transaction.annotation.Transactional;

/**
 * Unit test for {@code JpaRepositoryFactory}.
 * 
 * @author Oliver Gierke
 * @author Thomas Darimont
 */
@RunWith(MockitoJUnitRunner.class)
public class JpaRepositoryFactoryUnitTests {

	JpaRepositoryFactory factory;

	@Mock EntityManager entityManager;
	@Mock @SuppressWarnings("rawtypes") JpaEntityInformation entityInformation;
	@Mock EntityManagerFactory emf;

	@Before
	public void setUp() {

		when(entityManager.getEntityManagerFactory()).thenReturn(emf);
		when(entityManager.getDelegate()).thenReturn(entityManager);
		when(emf.createEntityManager()).thenReturn(entityManager);

		// Setup standard factory configuration
		factory = new JpaRepositoryFactory(entityManager) {

			@Override
			@SuppressWarnings("unchecked")
			public <T, ID extends Serializable> JpaEntityInformation<T, ID> getEntityInformation(Class<T> domainClass) {
				return entityInformation;
			};
		};

		factory.setQueryLookupStrategyKey(Key.CREATE_IF_NOT_FOUND);
	}

	/**
	 * Assert that the instance created for the standard configuration is a valid {@code UserRepository}.
	 * 
	 * @throws Exception
	 */
	@Test
	public void setsUpBasicInstanceCorrectly() throws Exception {

		assertNotNull(factory.getRepository(SimpleSampleRepository.class));
	}

	@Test
	public void allowsCallingOfObjectMethods() {

		SimpleSampleRepository repository = factory.getRepository(SimpleSampleRepository.class);

		repository.hashCode();
		repository.toString();
		repository.equals(repository);
	}

	/**
	 * Asserts that the factory recognized configured repository classes that contain custom method but no custom
	 * implementation could be found. Furthremore the exception has to contain the name of the repository interface as for
	 * a large repository configuration it's hard to find out where this error occured.
	 * 
	 * @throws Exception
	 */
	@Test
	public void capturesMissingCustomImplementationAndProvidesInterfacename() throws Exception {

		try {
			factory.getRepository(SampleRepository.class);
		} catch (IllegalArgumentException e) {
			assertTrue(e.getMessage().contains(SampleRepository.class.getName()));
		}
	}

	@Test(expected = IllegalArgumentException.class)
	public void handlesRuntimeExceptionsCorrectly() {

		SampleRepository repository = factory.getRepository(SampleRepository.class, new SampleCustomRepositoryImpl());
		repository.throwingRuntimeException();
	}

	@Test(expected = IOException.class)
	public void handlesCheckedExceptionsCorrectly() throws Exception {

		SampleRepository repository = factory.getRepository(SampleRepository.class, new SampleCustomRepositoryImpl());
		repository.throwingCheckedException();
	}

	@Test(expected = UnsupportedOperationException.class)
	public void createsProxyWithCustomBaseClass() {

		JpaRepositoryFactory factory = new CustomGenericJpaRepositoryFactory(entityManager);
		factory.setQueryLookupStrategyKey(Key.CREATE_IF_NOT_FOUND);
		UserCustomExtendedRepository repository = factory.getRepository(UserCustomExtendedRepository.class);

		repository.customMethod(1);
	}

	@Test
	public void usesQueryDslRepositoryIfInterfaceImplementsExecutor() {

		when(entityInformation.getJavaType()).thenReturn(User.class);
		assertEquals(QueryDslJpaRepository.class,
				factory.getRepositoryBaseClass(new DefaultRepositoryMetadata(QueryDslSampleRepository.class)));

		try {
			QueryDslSampleRepository repository = factory.getRepository(QueryDslSampleRepository.class);
			assertEquals(QueryDslJpaRepository.class, ((Advised) repository).getTargetClass());
		} catch (IllegalArgumentException e) {
			assertThat(e.getStackTrace()[0].getClassName(), is("org.springframework.data.querydsl.SimpleEntityPathResolver"));
		}
	}

	/**
	 * @see DATAJPA-710, DATACMNS-542
	 */
	@Test
	public void usesConfiguredRepositoryBaseClass() {

		factory.setRepositoryBaseClass(CustomJpaRepository.class);

		SampleRepository repository = factory.getRepository(SampleRepository.class);
		assertEquals(CustomJpaRepository.class, ((Advised) repository).getTargetClass());
	}

	private interface SimpleSampleRepository extends JpaRepository<User, Integer> {

		@Transactional
		User findOne(Integer id);
	}

	/**
	 * Sample interface to contain a custom method.
	 * 
	 * @author Oliver Gierke
	 */
	public interface SampleCustomRepository {

		void throwingRuntimeException();

		void throwingCheckedException() throws IOException;
	}

	/**
	 * Implementation of the custom repository interface.
	 * 
	 * @author Oliver Gierke
	 */
	private class SampleCustomRepositoryImpl implements SampleCustomRepository {

		public void throwingRuntimeException() {

			throw new IllegalArgumentException("You lose!");
		}

		public void throwingCheckedException() throws IOException {

			throw new IOException("You lose!");
		}
	}

	private interface SampleRepository extends JpaRepository<User, Integer>, SampleCustomRepository {

	}

	private interface QueryDslSampleRepository extends SimpleSampleRepository, QueryDslPredicateExecutor<User> {

	}

	static class CustomJpaRepository<T, ID extends Serializable> extends SimpleJpaRepository<T, ID> {

		public CustomJpaRepository(JpaEntityInformation<T, ?> entityInformation, EntityManager entityManager) {
			super(entityInformation, entityManager);
		}
	};
}


File: src/test/java/org/springframework/data/jpa/repository/support/SimpleJpaRepositoryUnitTests.java
/*
 * Copyright 2011-2015 the original author or authors.
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

import static java.util.Collections.singletonMap;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.io.Serializable;

import javax.persistence.EntityGraph;
import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;
import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.runners.MockitoJUnitRunner;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.jpa.domain.sample.User;
import org.springframework.data.jpa.repository.EntityGraph.EntityGraphType;
import org.springframework.data.repository.CrudRepository;

/**
 * Unit tests for {@link SimpleJpaRepository}.
 * 
 * @author Oliver Gierke
 * @author Thomas Darimont
 */
@RunWith(MockitoJUnitRunner.class)
public class SimpleJpaRepositoryUnitTests {

	SimpleJpaRepository<User, Integer> repo;

	@Mock EntityManager em;
	@Mock CriteriaBuilder builder;
	@Mock CriteriaQuery<User> criteriaQuery;
	@Mock CriteriaQuery<Long> countCriteriaQuery;
	@Mock TypedQuery<User> query;
	@Mock TypedQuery<Long> countQuery;
	@Mock JpaEntityInformation<User, Long> information;
	@Mock CrudMethodMetadata metadata;
	@Mock EntityGraph<User> entityGraph;
	@Mock org.springframework.data.jpa.repository.EntityGraph entityGraphAnnotation;

	@Before
	public void setUp() {

		when(em.getDelegate()).thenReturn(em);

		when(information.getJavaType()).thenReturn(User.class);
		when(em.getCriteriaBuilder()).thenReturn(builder);

		when(builder.createQuery(User.class)).thenReturn(criteriaQuery);
		when(builder.createQuery(Long.class)).thenReturn(countCriteriaQuery);

		when(em.createQuery(criteriaQuery)).thenReturn(query);
		when(em.createQuery(countCriteriaQuery)).thenReturn(countQuery);

		repo = new SimpleJpaRepository<User, Integer>(information, em);
		repo.setRepositoryMethodMetadata(metadata);
	}

	/**
	 * @see DATAJPA-124
	 */
	@Test
	public void doesNotActuallyRetrieveObjectsForPageableOutOfRange() {

		when(countQuery.getSingleResult()).thenReturn(20L);
		repo.findAll(new PageRequest(2, 10));

		verify(query, times(0)).getResultList();
	}

	/**
	 * @see DATAJPA-177
	 */
	@Test(expected = EmptyResultDataAccessException.class)
	public void throwsExceptionIfEntityToDeleteDoesNotExist() {

		repo.delete(4711);
	}

	/**
	 * @see DATAJPA-689
	 * @see DATAJPA-696
	 */
	@Test
	@SuppressWarnings({ "rawtypes", "unchecked" })
	public void shouldPropagateConfiguredEntityGraphToFindOne() throws Exception{

		String entityGraphName = "User.detail";
		when(entityGraphAnnotation.value()).thenReturn(entityGraphName);
		when(entityGraphAnnotation.type()).thenReturn(EntityGraphType.LOAD);
		when(metadata.getEntityGraph()).thenReturn(entityGraphAnnotation);
		when(em.getEntityGraph(entityGraphName)).thenReturn((EntityGraph) entityGraph);
		when(information.getEntityName()).thenReturn("User");
		when(metadata.getMethod()).thenReturn(CrudRepository.class.getMethod("findOne", Serializable.class));
		
		Integer id = 0;
		repo.findOne(id);

		verify(em).find(User.class, id, singletonMap(EntityGraphType.LOAD.getKey(), (Object) entityGraph));
	}
}
