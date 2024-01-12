Refactoring Types: ['Move Class']
/java/org/springframework/data/neo4j/repository/query/GraphRepositoryQuery.java
/*
 * Copyright (c)  [2011-2015] "Pivotal Software, Inc." / "Neo Technology" / "Graph Aware Ltd."
 *
 * This product is licensed to you under the Apache License, Version 2.0 (the "License").
 * You may not use this product except in compliance with the License.
 *
 * This product may include a number of subcomponents with
 * separate copyright notices and license terms. Your use of the source
 * code for these subcomponents is subject to the terms and
 * conditions of the subcomponent's license, as noted in the LICENSE file.
 */

package org.springframework.data.neo4j.repository.query;

import org.neo4j.ogm.session.Session;
import org.springframework.data.repository.query.Parameter;
import org.springframework.data.repository.query.Parameters;
import org.springframework.data.repository.query.RepositoryQuery;

import java.util.HashMap;
import java.util.Map;


/**
 * Specialisation of {@link RepositoryQuery} that handles mapping to object annotated with <code>&#064;Query</code>.
 *
 * @author Mark Angrish
 * @author Luanne Misquitta
 */
public class GraphRepositoryQuery implements RepositoryQuery {

    private final GraphQueryMethod graphQueryMethod;

    protected final Session session;

    public GraphRepositoryQuery(GraphQueryMethod graphQueryMethod, Session session) {
        this.graphQueryMethod = graphQueryMethod;
        this.session = session;
    }

    @Override
    public final Object execute(Object[] parameters) {
        Class<?> returnType = graphQueryMethod.getMethod().getReturnType();
        Class<?> concreteType = graphQueryMethod.resolveConcreteReturnType();

        Map<String, Object> params = resolveParams(parameters);

        return execute(returnType, concreteType, getQueryString(), params);
    }

    protected Object execute(Class<?> returnType, Class<?> concreteType, String cypherQuery, Map<String, Object> queryParams) {

        if (returnType.equals(Void.class) || returnType.equals(void.class)) {
            session.execute(cypherQuery, queryParams);
            return null;
        }

        if (graphQueryMethod.isModifyingQuery()) {
            return session.execute(cypherQuery, queryParams);
        }

        if (Iterable.class.isAssignableFrom(returnType)) {
            // Special method to handle SDN Iterable<Map<String, Object>> behaviour.
            // TODO: Do we really want this method in an OGM? It's a little too low level and/or doesn't really fit.
            if (Map.class.isAssignableFrom(concreteType)) {
                return session.query(cypherQuery, queryParams);
            }
            return session.query(concreteType, cypherQuery, queryParams);
        }

        return session.queryForObject(returnType, cypherQuery, queryParams);
    }

    private Map<String, Object> resolveParams(Object[] parameters) {
        Map<String, Object> params = new HashMap<>();
        Parameters<?, ?> methodParameters = graphQueryMethod.getParameters();

        for (int i = 0; i < parameters.length; i++) {
            Parameter parameter = methodParameters.getParameter(i);

            if (parameter.isNamedParameter()) {
                params.put(parameter.getName(), parameters[i]);
            } else {
                params.put("" + i, parameters[i]);
            }
        }
        return params;
    }

    @Override
    public GraphQueryMethod getQueryMethod() {
        return graphQueryMethod;
    }

    protected String getQueryString() {
        return getQueryMethod().getQuery();
    }

}

File: spring-data-neo4j/src/test/java/org/springframework/data/neo4j/examples/friends/FriendService.java
/*
 * Copyright (c)  [2011-2015] "Pivotal Software, Inc." / "Neo Technology" / "Graph Aware Ltd."
 *
 * This product is licensed to you under the Apache License, Version 2.0 (the "License").
 * You may not use this product except in compliance with the License.
 *
 * This product may include a number of subcomponents with
 * separate copyright notices and license terms. Your use of the source
 * code for these subcomponents is subject to the terms and
 * conditions of the subcomponent's license, as noted in the LICENSE file.
 */

package org.springframework.data.neo4j.examples.friends;

import org.neo4j.ogm.session.Session;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * @author Luanne Misquitta
 */
@Service
public class FriendService {

	@Autowired
	Session session;

	@Transactional
	public void createPersonAndFriends() {
		Person john = new Person();
		john.setFirstName("John");
		session.save(john);

		Person bob = new Person();
		bob.setFirstName("Bob");
		session.save(bob);

		Person bill = new Person();
		bill.setFirstName("Bill");
		session.save(bill);

		john = session.load(Person.class, john.getId());
		bob = session.load(Person.class, bob.getId());
		Friendship friendship1 = john.addFriend(bob);
		friendship1.setTimestamp(System.currentTimeMillis());
		session.save(john);
		john = session.load(Person.class, john.getId());
		bill = session.load(Person.class, bill.getId());
		Friendship friendship2 = john.addFriend(bill);
		friendship2.setTimestamp(System.currentTimeMillis());
		session.save(john);
	}
}


File: spring-data-neo4j/src/test/java/org/springframework/data/neo4j/examples/friends/FriendTest.java
/*
 * Copyright (c)  [2011-2015] "Pivotal Software, Inc." / "Neo Technology" / "Graph Aware Ltd."
 *
 * This product is licensed to you under the Apache License, Version 2.0 (the "License").
 * You may not use this product except in compliance with the License.
 *
 * This product may include a number of subcomponents with
 * separate copyright notices and license terms. Your use of the source
 * code for these subcomponents is subject to the terms and
 * conditions of the subcomponent's license, as noted in the LICENSE file.
 */

package org.springframework.data.neo4j.examples.friends;

import static org.junit.Assert.*;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.neo4j.ogm.cypher.Filter;
import org.neo4j.ogm.session.Session;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;

/**
 * @author Luanne Misquitta
 */
@ContextConfiguration(classes = {FriendContext.class})
@RunWith(SpringJUnit4ClassRunner.class)
public class FriendTest {

	@Autowired Session session;
	@Autowired FriendService friendService;

	/**
	 * DATAGRAPH-703
	 */
	@Test
	public void savingPersonWhenTransactionalShouldWork() {
		friendService.createPersonAndFriends();

		session.clear();
		Person john = session.loadAll(Person.class, new Filter("firstName", "John")).iterator().next();
		assertNotNull(john);
		assertEquals(2, john.getFriendships().size());;
	}
}


File: spring-data-neo4j/src/test/java/org/springframework/data/neo4j/examples/movies/repo/UserRepository.java
/*
 * Copyright (c)  [2011-2015] "Pivotal Software, Inc." / "Neo Technology" / "Graph Aware Ltd."
 *
 * This product is licensed to you under the Apache License, Version 2.0 (the "License").
 * You may not use this product except in compliance with the License.
 *
 * This product may include a number of subcomponents with
 * separate copyright notices and license terms. Your use of the source
 * code for these subcomponents is subject to the terms and
 * conditions of the subcomponent's license, as noted in the LICENSE file.
 */

package org.springframework.data.neo4j.examples.movies.repo;

import java.util.Collection;
import java.util.List;
import java.util.Map;

import org.springframework.data.neo4j.annotation.Query;
import org.springframework.data.neo4j.examples.movies.domain.User;
import org.springframework.data.neo4j.examples.movies.domain.queryresult.*;
import org.springframework.data.neo4j.repository.GraphRepository;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/**
 * @author Michal Bachman
 * @author Luanne Misquitta
 */
@Repository
public interface UserRepository extends GraphRepository<User> {

    Collection<User> findByName(String name);

    Collection<User> findByMiddleName(String middleName);

    List<User> findByRatingsStars(int stars);

    List<User> findByRatingsStarsAndInterestedName(int stars, String name);

    @Query("MATCH (user:User) RETURN COUNT(user)")
    int findTotalUsers();

    @Query("MATCH (user:User) RETURN user.id")
    List<Integer> getUserIds();

    @Query("MATCH (user:User) RETURN user.name, user.id")
    Iterable<Map<String,Object>> getUsersAsProperties();

    @Query("MATCH (user:User) RETURN user")
    Collection<User> getAllUsers();

    @Query("MATCH (m:Movie)<-[:ACTED_IN]-(a:User) RETURN m.name as movie, collect(a.name) as cast")
    List<Map<String, Object>> getGraph();

    @Query("MATCH (user:User{name:{name}}) RETURN user")
    User findUserByNameWithNamedParam(@Param("name") String name);

    @Query("MATCH (user:User{name:{0}}) RETURN user")
    User findUserByName(String name);

    @Query("MATCH (user:User) RETURN id(user) AS userId, user.name AS userName, user.age ORDER BY user.age")
    Iterable<UserQueryResult> retrieveAllUsersAndTheirAges();

    @Query("MATCH (user:User{name:{0}}) RETURN user.name AS name")
    UnmanagedUserPojo findIndividualUserAsDifferentObject(String name);

    @Query("MATCH (user:User) WHERE user.name={0} RETURN user.name, user.age AS ageOfUser")
    UserQueryResultInterface findIndividualUserAsProxiedObject(String name);

    @Query("MATCH (user:User) WHERE user.gender={0} RETURN user.name AS UserName, user.gender AS UserGender, user.account as UserAccount, user.deposits as UserDeposits")
    Iterable<RichUserQueryResult> findUsersByGender(Gender gender);

    @Query("MATCH (user:User) WHERE user.name={0} RETURN user")
    EntityWrappingQueryResult findWrappedUserByName(String userName);

    @Query("MATCH (user:User) RETURN ID(user)")
    List<Long> getUserNodeIds();

}


File: spring-data-neo4j/src/test/java/org/springframework/data/neo4j/queries/QueryIntegrationTest.java
/*
 * Copyright (c)  [2011-2015] "Pivotal Software, Inc." / "Neo Technology" / "Graph Aware Ltd."
 *
 * This product is licensed to you under the Apache License, Version 2.0 (the "License").
 * You may not use this product except in compliance with the License.
 *
 * This product may include a number of subcomponents with
 * separate copyright notices and license terms. Your use of the source
 * code for these subcomponents is subject to the terms and
 * conditions of the subcomponent's license, as noted in the LICENSE file.
 */

package org.springframework.data.neo4j.queries;

import static org.junit.Assert.*;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.*;

import org.junit.After;
import org.junit.ClassRule;
import org.junit.Ignore;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.neo4j.cypher.javacompat.ExecutionEngine;
import org.neo4j.ogm.metadata.MappingException;
import org.neo4j.ogm.testutil.Neo4jIntegrationTestRule;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.neo4j.examples.movies.context.MoviesContext;
import org.springframework.data.neo4j.examples.movies.domain.User;
import org.springframework.data.neo4j.examples.movies.domain.queryresult.*;
import org.springframework.data.neo4j.examples.movies.repo.CinemaRepository;
import org.springframework.data.neo4j.examples.movies.repo.UnmanagedUserPojo;
import org.springframework.data.neo4j.examples.movies.repo.UserRepository;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;

/**
 * @author Vince Bickers
 * @author Luanne Misquitta
 */
@ContextConfiguration(classes = {MoviesContext.class})
@RunWith(SpringJUnit4ClassRunner.class)
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_EACH_TEST_METHOD)
public class QueryIntegrationTest {

    @ClassRule
    public static Neo4jIntegrationTestRule neo4jRule = new Neo4jIntegrationTestRule(7879);

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private CinemaRepository cinemaRepository;

    @After
    public void clearDatabase() {
        neo4jRule.clearDatabase();
    }

    private void executeUpdate(String cypher) {
        new ExecutionEngine(neo4jRule.getGraphDatabaseService()).execute(cypher);
    }

    @Test
    public void shouldFindArbitraryGraph() {
        executeUpdate(
                "CREATE " +
                        "(dh:Movie {name:'Die Hard'}), " +
                        "(fe:Movie {name: 'The Fifth Element'}), " +
                        "(bw:User {name: 'Bruce Willis'}), " +
                        "(ar:User {name: 'Alan Rickman'}), " +
                        "(mj:User {name: 'Milla Jovovich'}), " +
                        "(mj)-[:ACTED_IN]->(fe), " +
                        "(ar)-[:ACTED_IN]->(dh), " +
                        "(bw)-[:ACTED_IN]->(dh), " +
                        "(bw)-[:ACTED_IN]->(fe)");

        List<Map<String, Object>> graph = userRepository.getGraph();
        assertNotNull(graph);
        int i = 0;
        for (Map<String,Object> properties: graph) {
            i++;
            assertNotNull(properties);
        }
        assertEquals(2, i);
    }

    @Test
    public void shouldFindScalarValues() {
        executeUpdate("CREATE (m:User {name:'Michal'})<-[:FRIEND_OF]-(a:User {name:'Adam'})");
        List<Integer> ids = userRepository.getUserIds();
        assertEquals(2, ids.size());

        List<Long> nodeIds = userRepository.getUserNodeIds();
        assertEquals(2, nodeIds.size());
    }

    @Test
    public void shouldFindUserByName() {
        executeUpdate("CREATE (m:User {name:'Michal'})<-[:FRIEND_OF]-(a:User {name:'Adam'})");

        User user = userRepository.findUserByName("Michal");
        assertEquals("Michal",user.getName());
    }

    @Test
    public void shouldFindTotalUsers() {
        executeUpdate("CREATE (m:User {name:'Michal'})<-[:FRIEND_OF]-(a:User {name:'Adam'})");

        int users = userRepository.findTotalUsers();
        assertEquals(users, 2);
    }

    @Test
    public void shouldFindUsers() {
        executeUpdate("CREATE (m:User {name:'Michal'})<-[:FRIEND_OF]-(a:User {name:'Adam'})");

        Collection<User> users = userRepository.getAllUsers();
        assertEquals(users.size(), 2);
    }

    @Test
    public void shouldFindUserByNameWithNamedParam() {
        executeUpdate("CREATE (m:User {name:'Michal'})<-[:FRIEND_OF]-(a:User {name:'Adam'})");

        User user = userRepository.findUserByNameWithNamedParam("Michal");
        assertEquals("Michal",user.getName());
    }

    @Test
    public void shouldFindUsersAsProperties() {
        executeUpdate("CREATE (m:User {name:'Michal'})<-[:FRIEND_OF]-(a:User {name:'Adam'})");

        Iterable<Map<String, Object>> users = userRepository.getUsersAsProperties();
        assertNotNull(users);
        int i = 0;
        for (Map<String,Object> properties: users) {
            i++;
            assertNotNull(properties);
        }
        assertEquals(2, i);
    }

    /**
     * @see DATAGRAPH-698
     */
    @Test
    public void shouldFindUsersAndMapThemToConcreteQueryResultObjectCollection() {
        executeUpdate("CREATE (g:User {name:'Gary', age:32}), (s:User {name:'Sheila', age:29}), (v:User {name:'Vince', age:66})");
        assertEquals("There should be some users in the database", 3, userRepository.findTotalUsers());

        Iterable<UserQueryResult> expected = Arrays.asList(new UserQueryResult("Sheila", 29),
                new UserQueryResult("Gary", 32), new UserQueryResult("Vince", 66));

        Iterable<UserQueryResult> queryResult = userRepository.retrieveAllUsersAndTheirAges();
        assertNotNull("The query result shouldn't be null", queryResult);
        assertEquals(expected, queryResult);
        for(UserQueryResult userQueryResult : queryResult) {
            assertNotNull(userQueryResult.getUserId());
        }
    }

    /**
     * This limitation about not handling unmanaged types may be addressed after M2 if there's demand for it.
     */
    @Test(expected = MappingException.class)
    public void shouldThrowMappingExceptionIfQueryResultTypeIsNotManagedInMappingMetadata() {
        executeUpdate("CREATE (:User {name:'Colin'}), (:User {name:'Jeff'})");

        // NB: UnmanagedUserPojo is not scanned with the other domain classes
        UnmanagedUserPojo queryResult = userRepository.findIndividualUserAsDifferentObject("Jeff");
        assertNotNull("The query result shouldn't be null", queryResult);
        assertEquals("Jeff", queryResult.getName());
    }

    @Test
    public void shouldFindUsersAndMapThemToProxiedQueryResultInterface() {
        executeUpdate("CREATE (:User {name:'Morne', age:30}), (:User {name:'Abraham', age:31}), (:User {name:'Virat', age:27})");

        UserQueryResultInterface result = userRepository.findIndividualUserAsProxiedObject("Abraham");
        assertNotNull("The query result shouldn't be null", result);
        assertEquals("The wrong user was returned", "Abraham", result.getNameOfUser());
        assertEquals("The wrong user was returned", 31, result.getAgeOfUser());
    }

    @Test
    public void shouldRetrieveUsersByGenderAndConvertToCorrectTypes() {
        executeUpdate("CREATE (:User {name:'David Warner', gender:'MALE'}), (:User {name:'Shikhar Dhawan', gender:'MALE'}), "
                + "(:User {name:'Sarah Taylor', gender:'FEMALE', account: '3456789', deposits:['12345.6','45678.9']})");

        Iterable<RichUserQueryResult> usersByGender = userRepository.findUsersByGender(Gender.FEMALE);
        assertNotNull("The resultant users list shouldn't be null", usersByGender);

        Iterator<RichUserQueryResult> userIterator = usersByGender.iterator();
        assertTrue(userIterator.hasNext());
        RichUserQueryResult userQueryResult = userIterator.next();
        assertEquals(Gender.FEMALE, userQueryResult.getUserGender());
        assertEquals("Sarah Taylor", userQueryResult.getUserName());
        assertEquals(BigInteger.valueOf(3456789), userQueryResult.getUserAccount());
        assertArrayEquals(new BigDecimal[]{BigDecimal.valueOf(12345.6), BigDecimal.valueOf(45678.9)}, userQueryResult.getUserDeposits());
        assertFalse(userIterator.hasNext());
    }

    /**
     * I'm not sure whether we should actually support this because you could just return an entity!
     */
    @Ignore
    @Test
    public void shouldMapNodeEntitiesIntoQueryResultObjects() {
        executeUpdate("CREATE (:User {name:'Abraham'}), (:User {name:'Barry'}), (:User {name:'Colin'})");

        EntityWrappingQueryResult wrappedUser = userRepository.findWrappedUserByName("Barry");
        assertNotNull("The loaded wrapper object shouldn't be null", wrappedUser);
        assertNotNull("The enclosed user shouldn't be null", wrappedUser.getUser());
        assertEquals("Barry", wrappedUser.getUser().getName());
    }



}
