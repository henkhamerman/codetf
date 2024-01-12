Refactoring Types: ['Move Class']
ain/java/org/infinispan/client/hotrod/impl/query/RemoteQuery.java
package org.infinispan.client.hotrod.impl.query;

import org.infinispan.client.hotrod.exceptions.HotRodClientException;
import org.infinispan.client.hotrod.impl.RemoteCacheImpl;
import org.infinispan.client.hotrod.impl.operations.QueryOperation;
import org.infinispan.protostream.ProtobufUtil;
import org.infinispan.protostream.SerializationContext;
import org.infinispan.protostream.WrappedMessage;
import org.infinispan.query.dsl.QueryFactory;
import org.infinispan.query.dsl.impl.BaseQuery;
import org.infinispan.query.remote.client.QueryResponse;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/**
 * @author anistor@redhat.com
 * @since 6.0
 */
public final class RemoteQuery extends BaseQuery {

   private final RemoteCacheImpl cache;
   private final SerializationContext serializationContext;

   private final long startOffset; //todo can this really be long or it has to be int due to limitations in query module?
   private final int maxResults;

   private List results = null;
   private int totalResults;

   RemoteQuery(QueryFactory queryFactory, RemoteCacheImpl cache, SerializationContext serializationContext,
                      String jpaQuery, long startOffset, int maxResults) {
      super(queryFactory, jpaQuery);
      this.cache = cache;
      this.serializationContext = serializationContext;
      this.startOffset = startOffset;
      this.maxResults = maxResults;
   }

   public RemoteCacheImpl getCache() {
      return cache;
   }

   public long getStartOffset() {
      return startOffset;
   }

   public int getMaxResults() {
      return maxResults;
   }

   @Override
   @SuppressWarnings("unchecked")
   public <T> List<T> list() {
      if (results == null) {
         results = executeQuery();
      }

      return (List<T>) results;
   }

   private List<Object> executeQuery() {
      List<Object> results;

      QueryOperation op = cache.getOperationsFactory().newQueryOperation(this);
      QueryResponse response = op.execute();
      totalResults = (int) response.getTotalResults();
      if (response.getProjectionSize() > 0) {
         results = new ArrayList<Object>(response.getResults().size() / response.getProjectionSize());
         Iterator<WrappedMessage> it = response.getResults().iterator();
         while (it.hasNext()) {
            Object[] row = new Object[response.getProjectionSize()];
            for (int i = 0; i < response.getProjectionSize(); i++) {
               row[i] = it.next().getValue();
            }
            results.add(row);
         }
      } else {
         results = new ArrayList<Object>(response.getResults().size());
         for (WrappedMessage r : response.getResults()) {
            try {
               byte[] bytes = (byte[]) r.getValue();
               Object o = ProtobufUtil.fromWrappedByteArray(serializationContext, bytes);
               results.add(o);
            } catch (IOException e) {
               throw new HotRodClientException(e);
            }
         }
      }

      return results;
   }

   @Override
   public int getResultSize() {
      list();
      return totalResults;
   }

   public SerializationContext getSerializationContext() {
      return serializationContext;
   }

   @Override
   public String toString() {
      return "RemoteQuery{" +
            "jpaQuery=" + jpaQuery +
            ", startOffset=" + startOffset +
            ", maxResults=" + maxResults +
            '}';
   }
}


File: client/hotrod-client/src/main/java/org/infinispan/client/hotrod/impl/query/RemoteQueryBuilder.java
package org.infinispan.client.hotrod.impl.query;

import org.infinispan.client.hotrod.impl.RemoteCacheImpl;
import org.infinispan.client.hotrod.logging.Log;
import org.infinispan.client.hotrod.logging.LogFactory;
import org.infinispan.protostream.SerializationContext;
import org.infinispan.query.dsl.Query;
import org.infinispan.query.dsl.impl.BaseQueryBuilder;

/**
 * @author anistor@redhat.com
 * @since 6.0
 */
public final class RemoteQueryBuilder extends BaseQueryBuilder<Query> {

   private static final Log log = LogFactory.getLog(RemoteQueryBuilder.class);

   private final RemoteCacheImpl cache;
   private final SerializationContext serializationContext;

   public RemoteQueryBuilder(RemoteQueryFactory queryFactory, RemoteCacheImpl cache, SerializationContext serializationContext, String rootType) {
      super(queryFactory, rootType);
      this.cache = cache;
      this.serializationContext = serializationContext;
   }

   @Override
   public Query build() {
      String jpqlString = accept(new RemoteJPAQueryGenerator(serializationContext));
      if (log.isTraceEnabled()) {
         log.tracef("JPQL string : %s", jpqlString);
      }
      return new RemoteQuery(queryFactory, cache, serializationContext, jpqlString, startOffset, maxResults);
   }
}


File: client/hotrod-client/src/test/java/org/infinispan/client/hotrod/marshall/EmbeddedCompatTest.java
package org.infinispan.client.hotrod.marshall;

import org.infinispan.client.hotrod.RemoteCache;
import org.infinispan.client.hotrod.RemoteCacheManager;
import org.infinispan.client.hotrod.Search;
import org.infinispan.client.hotrod.configuration.ConfigurationBuilder;
import org.infinispan.client.hotrod.query.testdomain.protobuf.AccountPB;
import org.infinispan.client.hotrod.query.testdomain.protobuf.UserPB;
import org.infinispan.client.hotrod.query.testdomain.protobuf.marshallers.MarshallerRegistration;
import org.infinispan.client.hotrod.query.testdomain.protobuf.marshallers.NotIndexedMarshaller;
import org.infinispan.client.hotrod.test.HotRodClientTestingUtil;
import org.infinispan.commons.equivalence.AnyEquivalence;
import org.infinispan.commons.util.CloseableIterator;
import org.infinispan.commons.util.Util;
import org.infinispan.configuration.cache.Index;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.filter.AbstractKeyValueFilterConverter;
import org.infinispan.filter.KeyValueFilterConverterFactory;
import org.infinispan.iteration.impl.EntryRetriever;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.protostream.FileDescriptorSource;
import org.infinispan.protostream.SerializationContext;
import org.infinispan.metadata.Metadata;
import org.infinispan.query.CacheQuery;
import org.infinispan.query.SearchManager;
import org.infinispan.query.dsl.Query;
import org.infinispan.query.dsl.QueryFactory;
import org.infinispan.query.dsl.embedded.testdomain.Account;
import org.infinispan.query.dsl.embedded.testdomain.NotIndexed;
import org.infinispan.query.dsl.embedded.testdomain.hsearch.AccountHS;
import org.infinispan.query.dsl.embedded.testdomain.hsearch.UserHS;
import org.infinispan.query.remote.CompatibilityProtoStreamMarshaller;
import org.infinispan.query.remote.ProtobufMetadataManager;
import org.infinispan.server.hotrod.HotRodServer;
import org.infinispan.test.SingleCacheManagerTest;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.testng.annotations.AfterTest;
import org.testng.annotations.Test;

import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.stream.IntStream;

import static org.infinispan.client.hotrod.test.HotRodClientTestingUtil.killRemoteCacheManager;
import static org.infinispan.client.hotrod.test.HotRodClientTestingUtil.killServers;
import static org.infinispan.server.hotrod.test.HotRodTestingUtil.hotRodCacheConfiguration;
import static org.junit.Assert.*;

/**
 * Tests compatibility between remote query and embedded mode.
 *
 * @author anistor@redhat.com
 * @since 6.0
 */
@Test(testName = "client.hotrod.marshall.EmbeddedCompatTest", groups = "functional")
@CleanupAfterMethod
public class EmbeddedCompatTest extends SingleCacheManagerTest {

   private static final String NOT_INDEXED_PROTO_SCHEMA = "package sample_bank_account;\n" +
         "/* @Indexed(false) */\n" +
         "message NotIndexed {\n" +
         "\toptional string notIndexedField = 1;\n" +
         "}\n";

   private HotRodServer hotRodServer;
   private RemoteCacheManager remoteCacheManager;
   private RemoteCache<Integer, Account> remoteCache;

   @Override
   protected EmbeddedCacheManager createCacheManager() throws Exception {
      org.infinispan.configuration.cache.ConfigurationBuilder builder = createConfigBuilder();
      // the default key equivalence works only for byte[] so we need to override it with one that works for Object
      builder.dataContainer().keyEquivalence(AnyEquivalence.getInstance());

      cacheManager = TestCacheManagerFactory.createCacheManager(builder);
      cache = cacheManager.getCache();

      hotRodServer = HotRodClientTestingUtil.startHotRodServer(cacheManager);

      ConfigurationBuilder clientBuilder = new ConfigurationBuilder();
      clientBuilder.addServer().host("127.0.0.1").port(hotRodServer.getPort());
      clientBuilder.marshaller(new ProtoStreamMarshaller());
      remoteCacheManager = new RemoteCacheManager(clientBuilder.build());

      remoteCache = remoteCacheManager.getCache();

      //initialize client-side serialization context
      SerializationContext clientSerCtx = ProtoStreamMarshaller.getSerializationContext(remoteCacheManager);
      MarshallerRegistration.registerMarshallers(clientSerCtx);
      clientSerCtx.registerProtoFiles(FileDescriptorSource.fromString("not_indexed.proto", NOT_INDEXED_PROTO_SCHEMA));
      clientSerCtx.registerMarshaller(new NotIndexedMarshaller());

      //initialize server-side serialization context
      ProtobufMetadataManager protobufMetadataManager = cacheManager.getGlobalComponentRegistry().getComponent(ProtobufMetadataManager.class);
      protobufMetadataManager.registerProtofile("sample_bank_account/bank.proto", Util.read(Util.getResourceAsStream("/sample_bank_account/bank.proto", getClass().getClassLoader())));
      protobufMetadataManager.registerProtofile("not_indexed.proto", NOT_INDEXED_PROTO_SCHEMA);
      assertNull(protobufMetadataManager.getFileErrors("sample_bank_account/bank.proto"));
      assertNull(protobufMetadataManager.getFileErrors("not_indexed.proto"));
      assertNull(protobufMetadataManager.getFilesWithErrors());

      protobufMetadataManager.registerMarshaller(new EmbeddedAccountMarshaller());
      protobufMetadataManager.registerMarshaller(new EmbeddedUserMarshaller());
      protobufMetadataManager.registerMarshaller(new NotIndexedMarshaller());

      return cacheManager;
   }

   protected org.infinispan.configuration.cache.ConfigurationBuilder createConfigBuilder() {
      org.infinispan.configuration.cache.ConfigurationBuilder builder = hotRodCacheConfiguration();
      builder.compatibility().enable().marshaller(new CompatibilityProtoStreamMarshaller());
      builder.indexing().index(Index.ALL)
            .addProperty("default.directory_provider", "ram")
            .addProperty("lucene_version", "LUCENE_CURRENT");
      return builder;
   }

   @AfterTest
   public void release() {
      killRemoteCacheManager(remoteCacheManager);
      killServers(hotRodServer);
   }

   public void testPutAndGet() throws Exception {
      Account account = createAccountPB();
      remoteCache.put(1, account);

      // try to get the object through the local cache interface and check it's the same object we put
      assertEquals(1, cache.keySet().size());
      Object key = cache.keySet().iterator().next();
      Object localObject = cache.get(key);
      assertAccount((Account) localObject, AccountHS.class);

      // get the object through the remote cache interface and check it's the same object we put
      Account fromRemoteCache = remoteCache.get(1);
      assertAccount(fromRemoteCache, AccountPB.class);
   }

   public void testPutAndGetForEmbeddedEntry() throws Exception {
      AccountHS account = new AccountHS();
      account.setId(1);
      account.setDescription("test description");
      account.setCreationDate(new Date(42));
      cache.put(1, account);

      // try to get the object through the local cache interface and check it's the same object we put
      assertEquals(1, remoteCache.keySet().size());
      Object key = remoteCache.keySet().iterator().next();
      Object remoteObject = remoteCache.get(key);
      assertAccount((Account) remoteObject, AccountPB.class);

      // get the object through the embedded cache interface and check it's the same object we put
      Account fromEmbeddedCache = (Account) cache.get(1);
      assertAccount(fromEmbeddedCache, AccountHS.class);
   }

   public void testRemoteQuery() throws Exception {
      Account account = createAccountPB();
      remoteCache.put(1, account);

      // get account back from remote cache via query and check its attributes
      QueryFactory qf = Search.getQueryFactory(remoteCache);
      Query query = qf.from(AccountPB.class)
            .having("description").like("%test%").toBuilder()
            .build();
      List<Account> list = query.list();

      assertNotNull(list);
      assertEquals(1, list.size());
      assertAccount(list.get(0), AccountPB.class);
   }

   public void testRemoteQueryForEmbeddedEntry() throws Exception {
      AccountHS account = new AccountHS();
      account.setId(1);
      account.setDescription("test description");
      account.setCreationDate(new Date(42));
      cache.put(1, account);

      // get account back from remote cache via query and check its attributes
      QueryFactory qf = Search.getQueryFactory(remoteCache);
      Query query = qf.from(AccountPB.class)
            .having("description").like("%test%").toBuilder()
            .build();
      List<AccountPB> list = query.list();

      assertNotNull(list);
      assertEquals(1, list.size());
      assertAccount(list.get(0), AccountPB.class);
   }

   public void testRemoteQueryForEmbeddedEntryOnNonIndexedField() throws Exception {
      UserHS user = new UserHS();
      user.setId(1);
      user.setName("test name");
      user.setSurname("test surname");
      user.setNotes("1234567890");
      cache.put(1, user);

      // get user back from remote cache via query and check its attributes
      QueryFactory qf = Search.getQueryFactory(remoteCache);
      Query query = qf.from(UserPB.class)
            .having("notes").like("%567%").toBuilder()
            .build();
      List<UserPB> list = query.list();

      assertNotNull(list);
      assertEquals(1, list.size());
      assertNotNull(list.get(0));
      assertEquals(UserPB.class, list.get(0).getClass());
      assertEquals(1, list.get(0).getId());
      assertEquals("1234567890", list.get(0).getNotes());
   }

   public void testRemoteQueryForEmbeddedEntryOnNonIndexedType() throws Exception {
      cache.put(1, new NotIndexed("testing 123"));

      // get user back from remote cache via query and check its attributes
      QueryFactory qf = Search.getQueryFactory(remoteCache);
      Query query = qf.from("sample_bank_account.NotIndexed")
            .having("notIndexedField").like("%123%").toBuilder()
            .build();
      List<NotIndexed> list = query.list();

      assertNotNull(list);
      assertEquals(1, list.size());
      assertNotNull(list.get(0));
      assertEquals("testing 123", list.get(0).notIndexedField);
   }

   public void testRemoteQueryWithProjectionsForEmbeddedEntry() throws Exception {
      AccountHS account = new AccountHS();
      account.setId(1);
      account.setDescription("test description");
      account.setCreationDate(new Date(42));
      cache.put(1, account);

      // get account back from remote cache via query and check its attributes
      QueryFactory qf = Search.getQueryFactory(remoteCache);
      Query query = qf.from(AccountPB.class)
            .setProjection("description", "id")
            .having("description").like("%test%").toBuilder()
            .build();
      List<Object[]> list = query.list();

      assertNotNull(list);
      assertEquals(1, list.size());
      assertEquals("test description", list.get(0)[0]);
      assertEquals(1, list.get(0)[1]);
   }

   public void testEmbeddedQuery() throws Exception {
      Account account = createAccountPB();
      remoteCache.put(1, account);

      // get account back from local cache via query and check its attributes
      SearchManager searchManager = org.infinispan.query.Search.getSearchManager(cache);
      org.apache.lucene.search.Query query = searchManager
            .buildQueryBuilderForClass(AccountHS.class).get()
            .keyword().wildcard().onField("description").matching("*test*").createQuery();
      CacheQuery cacheQuery = searchManager.getQuery(query);
      List<Object> list = cacheQuery.list();

      assertNotNull(list);
      assertEquals(1, list.size());
      assertAccount((Account) list.get(0), AccountHS.class);
   }

   public void testIterationForRemote() throws Exception {
      IntStream.range(0, 10).forEach(id -> remoteCache.put(id, createAccount(id)));

      // Remote unfiltered iteration
      CloseableIterator<Map.Entry<Object, Object>> remoteUnfilteredIterator = remoteCache.retrieveEntries(null, null, 10);
      remoteUnfilteredIterator.forEachRemaining(e -> {
         Integer key = (Integer) e.getKey();
         AccountPB value = (AccountPB) e.getValue();
         assertTrue(key < 10);
         assertTrue(value.getId() == key);
      });

      // Remote filtered iteration
      KeyValueFilterConverterFactory<Integer, Account,String> filterConverterFactory = () ->
            new AbstractKeyValueFilterConverter<Integer, Account, String>() {
               @Override
               public String filterAndConvert(Integer key, Account value, Metadata metadata) {
                  if (key % 2 == 0) {
                     return value.toString();
                  }
                  return null;
               }
            };

      hotRodServer.addKeyValueFilterConverterFactory("filterConverterFactory", filterConverterFactory);

      CloseableIterator<Map.Entry<Object, Object>> remoteFilteredIterator = remoteCache.retrieveEntries("filterConverterFactory", null, 10);
      remoteFilteredIterator.forEachRemaining(e -> {
         Integer key = (Integer) e.getKey();
         String value = (String) e.getValue();
         assertTrue(key < 10);
         assertTrue(value.equals(createAccountHS(key).toString()));
      });

      // Embedded  iteration
      EntryRetriever<Integer, Account> localRetriever = cache.getAdvancedCache().getComponentRegistry().getComponent(EntryRetriever.class);
      CloseableIterator<CacheEntry<Integer, AccountHS>> localUnfilteredIterator = localRetriever.retrieveEntries(null, null, null, null);
      localUnfilteredIterator.forEachRemaining(e -> {
         Integer key = e.getKey();
         AccountHS value = e.getValue();
         assertTrue(key < 10);
         assertTrue(value.getId() == key);
      });
   }

   private AccountPB createAccountPB() {
      return createAccount(1);
   }

   private AccountPB createAccount(int id) {
      AccountPB account = new AccountPB();
      account.setId(id);
      account.setDescription("test description");
      account.setCreationDate(new Date(42));
      return account;
   }

   private AccountHS createAccountHS(int id) {
      AccountHS account = new AccountHS();
      account.setId(id);
      account.setDescription("test description");
      account.setCreationDate(new Date(42));
      return account;
   }

   private void assertAccount(Account account, Class<?> cls) {
      assertNotNull(account);
      assertEquals(cls, account.getClass());
      assertEquals(1, account.getId());
      assertEquals("test description", account.getDescription());
      assertEquals(42, account.getCreationDate().getTime());
   }
}


File: client/hotrod-client/src/test/java/org/infinispan/client/hotrod/marshall/NonIndexedEmbeddedCompatTest.java
package org.infinispan.client.hotrod.marshall;

import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.query.remote.CompatibilityProtoStreamMarshaller;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.testng.annotations.Test;

import static org.infinispan.server.hotrod.test.HotRodTestingUtil.hotRodCacheConfiguration;

/**
 * Tests compatibility between remote query and embedded mode. Do not enable indexing for query.
 *
 * @author anistor@redhat.com
 * @since 7.0
 */
@Test(testName = "client.hotrod.marshall.NonIndexedEmbeddedCompatTest", groups = "functional")
@CleanupAfterMethod
public class NonIndexedEmbeddedCompatTest extends EmbeddedCompatTest {

   @Override
   protected ConfigurationBuilder createConfigBuilder() {
      ConfigurationBuilder builder = hotRodCacheConfiguration();
      builder.compatibility().enable().marshaller(new CompatibilityProtoStreamMarshaller());
      return builder;
   }

   @Test(expectedExceptions = IllegalArgumentException.class, expectedExceptionsMessageRegExp = "Indexing was not enabled on this cache.*")
   @Override
   public void testEmbeddedQuery() throws Exception {
      // this would only make sense for Lucene based query
      super.testEmbeddedQuery();
   }
}


File: integrationtests/all-embedded-query-it/src/test/java/org/infinispan/all/embeddedquery/QueryDslConditionsTest.java
package org.infinispan.all.embeddedquery;

import org.hibernate.hql.ParsingException;
import org.infinispan.all.embeddedquery.testdomain.Account;
import org.infinispan.all.embeddedquery.testdomain.Address;
import org.infinispan.all.embeddedquery.testdomain.ModelFactory;
import org.infinispan.all.embeddedquery.testdomain.NotIndexed;
import org.infinispan.all.embeddedquery.testdomain.Transaction;
import org.infinispan.all.embeddedquery.testdomain.User;
import org.infinispan.all.embeddedquery.testdomain.hsearch.ModelFactoryHS;
import org.infinispan.query.Search;
import org.infinispan.query.dsl.FilterConditionEndContext;
import org.infinispan.query.dsl.Query;
import org.infinispan.query.dsl.QueryBuilder;
import org.infinispan.query.dsl.QueryFactory;
import org.infinispan.query.dsl.SortOrder;
import org.infinispan.query.dsl.embedded.impl.EmbeddedQueryFactory;
import org.junit.BeforeClass;
import org.junit.Test;

import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.TimeZone;

import static org.junit.Assert.*;

/**
 * Clone of QueryDslConditionsTest modified for uber-jars.
 *
 * @author jholusa@redhat.com
 * @author anistor@redhat.com
 * @author rvansa@redhat.com
 * @since 6.0
 */
public class QueryDslConditionsTest extends AbstractQueryTest {

   private static final DateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");

   private static Date makeDate(String dateStr) throws ParseException {
      DATE_FORMAT.setTimeZone(TimeZone.getTimeZone("GMT"));
      return DATE_FORMAT.parse(dateStr);
   }

   @BeforeClass
   public static void populateCache() throws Exception {
      cache = createCacheManager().getCache();

      // create the test objects
      User user1 = getModelFactory().makeUser();
      user1.setId(1);
      user1.setName("John");
      user1.setSurname("Doe");
      user1.setGender(User.Gender.MALE);
      user1.setAge(22);
      user1.setAccountIds(new HashSet<Integer>(Arrays.asList(1, 2)));
      user1.setNotes("Lorem ipsum dolor sit amet");

      Address address1 = getModelFactory().makeAddress();
      address1.setStreet("Main Street");
      address1.setPostCode("X1234");
      user1.setAddresses(Collections.singletonList(address1));

      User user2 = getModelFactory().makeUser();
      user2.setId(2);
      user2.setName("Spider");
      user2.setSurname("Man");
      user2.setGender(User.Gender.MALE);
      user2.setAccountIds(Collections.singleton(3));

      Address address2 = getModelFactory().makeAddress();
      address2.setStreet("Old Street");
      address2.setPostCode("Y12");
      Address address3 = getModelFactory().makeAddress();
      address3.setStreet("Bond Street");
      address3.setPostCode("ZZ");
      user2.setAddresses(Arrays.asList(address2, address3));

      User user3 = getModelFactory().makeUser();
      user3.setId(3);
      user3.setName("Spider");
      user3.setSurname("Woman");
      user3.setGender(User.Gender.FEMALE);
      user3.setAccountIds(Collections.<Integer>emptySet());

      Account account1 = getModelFactory().makeAccount();
      account1.setId(1);
      account1.setDescription("John Doe's first bank account");
      account1.setCreationDate(makeDate("2013-01-03"));

      Account account2 = getModelFactory().makeAccount();
      account2.setId(2);
      account2.setDescription("John Doe's second bank account");
      account2.setCreationDate(makeDate("2013-01-04"));

      Account account3 = getModelFactory().makeAccount();
      account3.setId(3);
      account3.setCreationDate(makeDate("2013-01-20"));

      Transaction transaction0 = getModelFactory().makeTransaction();
      transaction0.setId(0);
      transaction0.setDescription("Birthday present");
      transaction0.setAccountId(1);
      transaction0.setAmount(1800);
      transaction0.setDate(makeDate("2012-09-07"));
      transaction0.setDebit(false);

      Transaction transaction1 = getModelFactory().makeTransaction();
      transaction1.setId(1);
      transaction1.setDescription("Feb. rent payment");
      transaction1.setAccountId(1);
      transaction1.setAmount(1500);
      transaction1.setDate(makeDate("2013-01-05"));
      transaction1.setDebit(true);

      Transaction transaction2 = getModelFactory().makeTransaction();
      transaction2.setId(2);
      transaction2.setDescription("Starbucks");
      transaction2.setAccountId(1);
      transaction2.setAmount(23);
      transaction2.setDate(makeDate("2013-01-09"));
      transaction2.setDebit(true);

      Transaction transaction3 = getModelFactory().makeTransaction();
      transaction3.setId(3);
      transaction3.setDescription("Hotel");
      transaction3.setAccountId(2);
      transaction3.setAmount(45);
      transaction3.setDate(makeDate("2013-02-27"));
      transaction3.setDebit(true);

      Transaction transaction4 = getModelFactory().makeTransaction();
      transaction4.setId(4);
      transaction4.setDescription("Last january");
      transaction4.setAccountId(2);
      transaction4.setAmount(95);
      transaction4.setDate(makeDate("2013-01-31"));
      transaction4.setDebit(true);

      Transaction transaction5 = getModelFactory().makeTransaction();
      transaction5.setId(5);
      transaction5.setDescription("Popcorn");
      transaction5.setAccountId(2);
      transaction5.setAmount(5);
      transaction5.setDate(makeDate("2013-01-01"));
      transaction5.setDebit(true);

      // persist and index the test objects
      // we put all of them in the same cache for the sake of simplicity
      getCacheForWrite().put("user_" + user1.getId(), user1);
      getCacheForWrite().put("user_" + user2.getId(), user2);
      getCacheForWrite().put("user_" + user3.getId(), user3);
      getCacheForWrite().put("account_" + account1.getId(), account1);
      getCacheForWrite().put("account_" + account2.getId(), account2);
      getCacheForWrite().put("account_" + account3.getId(), account3);
      getCacheForWrite().put("transaction_" + transaction0.getId(), transaction0);
      getCacheForWrite().put("transaction_" + transaction1.getId(), transaction1);
      getCacheForWrite().put("transaction_" + transaction2.getId(), transaction2);
      getCacheForWrite().put("transaction_" + transaction3.getId(), transaction3);
      getCacheForWrite().put("transaction_" + transaction4.getId(), transaction4);
      getCacheForWrite().put("transaction_" + transaction5.getId(), transaction5);

      for (int i = 0; i < 50; i++) {
         Transaction transaction = getModelFactory().makeTransaction();
         transaction.setId(50 + i);
         transaction.setDescription("Expensive shoes " + i);
         transaction.setAccountId(2);
         transaction.setAmount(100 + i);
         transaction.setDate(makeDate("2013-08-20"));
         transaction.setDebit(true);
         getCacheForWrite().put("transaction_" + transaction.getId(), transaction);
      }

      // this value should be ignored gracefully
      getCacheForWrite().put("dummy", "a primitive value cannot be queried");

      getCacheForWrite().put("notIndexed1", new NotIndexed("testing 123"));
      getCacheForWrite().put("notIndexed2", new NotIndexed("xyz"));
   }

   @Test
   public void testIndexPresence() {
      assertIndexingKnows(getCacheForQuery(),
                          getModelFactory().getUserImplClass(),
                          getModelFactory().getAccountImplClass(),
                          getModelFactory().getTransactionImplClass());
   }

   @Test
   public void testQueryFactoryType() {
      assertEquals(EmbeddedQueryFactory.class, getQueryFactory().getClass());
   }

   @Test
   public void testEq1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("John")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Doe", list.get(0).getSurname());
   }

   @Test
   public void testEqEmptyString() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("")
            .toBuilder().build();

      List<User> list = q.list();
      assertTrue(list.isEmpty());
   }

   @Test
   public void testEqSentence() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .having("description").eq("John Doe's first bank account")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
   }

   @Test
   public void testEq() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("Jacob")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   @Test
   public void testEqNonIndexedType() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(NotIndexed.class)
            .having("notIndexedField").eq("testing 123")
            .toBuilder().build();

      List<NotIndexed> list = q.list();
      assertEquals(1, list.size());
      assertEquals("testing 123", list.get(0).notIndexedField);
   }

   @Test
   public void testEqNonIndexedField() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("notes").eq("Lorem ipsum dolor sit amet")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   @Test
   public void testEqInNested1() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all users in a given post code
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("addresses.postCode").eq("X1234")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("X1234", list.get(0).getAddresses().get(0).getPostCode());
   }

   @Test
   public void testEqInNested2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("addresses.postCode").eq("Y12")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(2, list.get(0).getAddresses().size());
   }

   @Test
   public void testLike() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all rent payments made from a given account
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("description").like("%rent%")
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getAccountId());
      assertEquals(1500, list.get(0).getAmount(), 0);
   }

   @Test
   public void testBetween1() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31"))
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(4, list.size());
      for (Transaction t : list) {
         assertTrue(t.getDate().compareTo(makeDate("2013-01-31")) <= 0);
         assertTrue(t.getDate().compareTo(makeDate("2013-01-01")) >= 0);
      }
   }

   @Test
   public void testBetween2() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31")).includeUpper(false)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(3, list.size());
      for (Transaction t : list) {
         assertTrue(t.getDate().compareTo(makeDate("2013-01-31")) < 0);
         assertTrue(t.getDate().compareTo(makeDate("2013-01-01")) >= 0);
      }
   }

   @Test
   public void testBetween3() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31")).includeLower(false)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(3, list.size());
      for (Transaction t : list) {
         assertTrue(t.getDate().compareTo(makeDate("2013-01-31")) <= 0);
         assertTrue(t.getDate().compareTo(makeDate("2013-01-01")) > 0);
      }
   }

   @Test
   public void testGt() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions greater than a given amount
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("amount").gt(1500)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(1, list.size());
      assertTrue(list.get(0).getAmount() > 1500);
   }

   @Test
   public void testGte() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("amount").gte(1500)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(2, list.size());
      for (Transaction t : list) {
         assertTrue(t.getAmount() >= 1500);
      }
   }

   @Test
   public void testLt() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("amount").lt(1500)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(54, list.size());
      for (Transaction t : list) {
         assertTrue(t.getAmount() < 1500);
      }
   }

   @Test
   public void testLte() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("amount").lte(1500)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(55, list.size());
      for (Transaction t : list) {
         assertTrue(t.getAmount() <= 1500);
      }
   }

   @Test
   public void testAnd1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("Spider")
            .and().having("surname").eq("Man")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(2, list.get(0).getId());
   }

   @Test
   public void testAnd2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("Spider")
            .and(qf.having("surname").eq("Man"))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(2, list.get(0).getId());
   }

   @Test
   public void testAnd3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(User.Gender.MALE)
            .and().having("gender").eq(User.Gender.FEMALE)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   @Test
   public void testAnd4() throws Exception {
      QueryFactory qf = getQueryFactory();

      //test for parenthesis, "and" should have higher priority
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("Spider")
            .or(qf.having("name").eq("John"))
            .and(qf.having("surname").eq("Man"))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
   }

   @Test
   public void testOr1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("surname").eq("Man")
            .or().having("surname").eq("Woman")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      for (User u : list) {
         assertEquals("Spider", u.getName());
      }
   }

   @Test
   public void testOr2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("surname").eq("Man")
            .or(qf.having("surname").eq("Woman"))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      for (User u : list) {
         assertEquals("Spider", u.getName());
      }
   }

   @Test
   public void testOr3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(User.Gender.MALE)
            .or().having("gender").eq(User.Gender.FEMALE)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(3, list.size());
   }

   @Test
   public void testOr4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("surname", SortOrder.DESC)
            .having("gender").eq(User.Gender.MALE)
            .or().having("name").eq("Spider")
            .and().having("gender").eq(User.Gender.FEMALE)
            .or().having("surname").like("%oe%")
            .toBuilder().build();
      List<User> list = q.list();

      assertEquals(2, list.size());
      assertEquals("Woman", list.get(0).getSurname());
      assertEquals("Doe", list.get(1).getSurname());
   }

   @Test
   public void testOr5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(User.Gender.MALE)
            .or().having("name").eq("Spider")
            .or().having("gender").eq(User.Gender.FEMALE)
            .and().having("surname").like("%oe%")
            .toBuilder().build();
      List<User> list = q.list();

      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
   }

   @Test
   public void testNot1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("name").eq("Spider")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
   }

   @Test
   public void testNot2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().not().having("surname").eq("Doe")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
   }

   @Test
   public void testNot3() throws Exception {
      QueryFactory qf = getQueryFactory();

      // NOT should have higher priority than AND
      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("name").eq("John")
            .and().having("surname").eq("Man")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("Spider", list.get(0).getName());
   }

   @Test
   public void testNot4() throws Exception {
      QueryFactory qf = getQueryFactory();

      // NOT should have higher priority than AND
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("surname").eq("Man")
            .and().not().having("name").eq("John")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("Spider", list.get(0).getName());
   }

   @Test
   public void testNot5() throws Exception {
      QueryFactory qf = getQueryFactory();

      // NOT should have higher priority than OR
      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("name").eq("Spider")
            .or().having("surname").eq("Man")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      for (User u : list) {
         assertFalse("Woman".equals(u.getSurname()));
      }
   }

   @Test
   public void testNot6() throws Exception {
      QueryFactory qf = getQueryFactory();

      // QueryFactory.not() test
      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(qf.not(qf.having("gender").eq(User.Gender.FEMALE)))
            .toBuilder()
            .build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertTrue(list.get(0).getSurname().equals("Woman"));
   }

   @Test
   public void testNot7() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(User.Gender.FEMALE)
            .and().not(qf.having("name").eq("Spider"))
            .toBuilder().build();

      List<User> list = q.list();
      assertTrue(list.isEmpty());
   }

   @Test
   public void testNot8() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(
                  qf.having("name").eq("John")
                        .or(qf.having("surname").eq("Man")))
            .toBuilder()
            .build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("Spider", list.get(0).getName());
      assertEquals("Woman", list.get(0).getSurname());
   }

   @Test
   public void testNot9() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(
                  qf.having("name").eq("John")
                        .and(qf.having("surname").eq("Doe")))
            .toBuilder()
            .orderBy("id", SortOrder.ASC)
            .build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals("Spider", list.get(0).getName());
      assertEquals("Man", list.get(0).getSurname());
      assertEquals("Spider", list.get(1).getName());
      assertEquals("Woman", list.get(1).getSurname());
   }

   @Test
   public void testNot10() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().not(
                  qf.having("name").eq("John")
                        .or(qf.having("surname").eq("Man")))
            .toBuilder()
            .build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertNotEquals("Woman", list.get(0).getSurname());
   }

   @Test
   public void testNot11() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(qf.not(
                  qf.having("name").eq("John")
                        .or(qf.having("surname").eq("Man"))))
            .toBuilder()
            .build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertNotEquals("Woman", list.get(0).getSurname());
   }

   @Test
   public void testEmptyQuery() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass()).build();

      List<User> list = q.list();
      assertEquals(3, list.size());
   }

   @Test(expected = ParsingException.class)
   public void testInvalidEmbeddedAttributeQuery() throws Exception {
      QueryFactory qf = getQueryFactory();

      QueryBuilder queryBuilder = qf.from(getModelFactory().getUserImplClass())
            .setProjection("addresses");

      queryBuilder.build();  // exception expected
   }

   @Test
   public void testIsNull() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("addresses").isNull()
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(3, list.get(0).getId());
   }

   @Test
   public void testContains1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").contains(2)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   @Test
   public void testContains2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").contains(42)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   @Test
   public void testContainsAll1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(1, 2)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   @Test
   public void testContainsAll2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(Collections.singleton(1))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   @Test
   public void testContainsAll3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(1, 2, 3)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   @Test
   public void testContainsAll4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(Collections.emptySet())
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(3, list.size());
   }

   @Test
   public void testContainsAny1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .having("accountIds").containsAny(2, 3)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals(1, list.get(0).getId());
      assertEquals(2, list.get(1).getId());
   }

   @Test
   public void testContainsAny2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAny(4, 5)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   @Test
   public void testContainsAny3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAny(Collections.emptySet())
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(3, list.size());
   }

   @Test
   public void testIn1() throws Exception {
      QueryFactory qf = getQueryFactory();

      List<Integer> ids = Arrays.asList(1, 3);
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("id").in(ids)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      for (User u : list) {
         assertTrue(ids.contains(u.getId()));
      }
   }

   @Test
   public void testIn2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("id").in(4)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   @Test(expected = IllegalArgumentException.class)
   public void testIn3() throws Exception {
      QueryFactory qf = getQueryFactory();

      qf.from(getModelFactory().getUserImplClass()).having("id").in(Collections.emptySet());
   }

   @Test(expected = IllegalArgumentException.class)
   public void testIn4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Collection collection = null;
      qf.from(getModelFactory().getUserImplClass()).having("id").in(collection);
   }

   @Test(expected = IllegalArgumentException.class)
   public void testIn5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Object[] array = null;
      qf.from(getModelFactory().getUserImplClass()).having("id").in(array);
   }

   @Test(expected = IllegalArgumentException.class)
   public void testIn6() throws Exception {
      QueryFactory qf = getQueryFactory();

      Object[] array = new Object[0];
      qf.from(getModelFactory().getUserImplClass()).having("id").in(array);
   }

   @Test
   public void testSampleDomainQuery1() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all male users
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.ASC)
            .having("gender").eq(User.Gender.MALE)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
   }

   @Test
   public void testSampleDomainQuery2() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all male users, but this time retrieved in a twisted manner
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.ASC)
            .not(qf.having("gender").eq(User.Gender.FEMALE))
            .and(qf.not().not(qf.having("gender").eq(User.Gender.MALE)))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
   }

   @Test
   public void testStringLiteralEscape() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all transactions that have a given description. the description contains characters that need to be escaped.
      Query q = qf.from(getModelFactory().getAccountImplClass())
            .having("description").eq("John Doe's first bank account")
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   @Test
   public void testSortByDate() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .orderBy("creationDate", SortOrder.DESC)
            .build();

      List<Account> list = q.list();
      assertEquals(3, list.size());
      assertEquals(3, list.get(0).getId());
      assertEquals(2, list.get(1).getId());
      assertEquals(1, list.get(2).getId());
   }

   @Test
   public void testSampleDomainQuery3() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all male users
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.ASC)
            .having("gender").eq(User.Gender.MALE)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
   }

   @Test
   public void testSampleDomainQuery4() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all users ordered descendingly by name
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.DESC)
            .build();

      List<User> list = q.list();
      assertEquals(3, list.size());
      assertEquals("Spider", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
      assertEquals("John", list.get(2).getName());
   }

   @Test
   public void testSampleDomainQuery4With2SortingOptions() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all users ordered descendingly by name
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.DESC)
            .orderBy("surname", SortOrder.ASC)
            .build();

      List<User> list = q.list();
      assertEquals(3, list.size());

      assertEquals("Spider", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
      assertEquals("John", list.get(2).getName());

      assertEquals("Man", list.get(0).getSurname());
      assertEquals("Woman", list.get(1).getSurname());
      assertEquals("Doe", list.get(2).getSurname());
   }

   @Test
   public void testSampleDomainQuery5() throws Exception {
      QueryFactory qf = getQueryFactory();

      // name projection of all users ordered descendingly by name
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.DESC)
            .setProjection("name")
            .build();

      List<Object[]> list = q.list();
      assertEquals(3, list.size());
      assertEquals(1, list.get(0).length);
      assertEquals(1, list.get(1).length);
      assertEquals(1, list.get(2).length);
      assertEquals("Spider", list.get(0)[0]);
      assertEquals("Spider", list.get(1)[0]);
      assertEquals("John", list.get(2)[0]);
   }

   @Test
   public void testSampleDomainQuery6() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all users with a given name and surname
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("John")
            .and().having("surname").eq("Doe")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Doe", list.get(0).getSurname());
   }

   @Test
   public void testSampleDomainQuery7() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all rent payments made from a given account
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("accountId").eq(1)
            .and().having("description").like("%rent%")
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
      assertEquals(1, list.get(0).getAccountId());
      assertTrue(list.get(0).getDescription().contains("rent"));
   }

   @Test
   public void testSampleDomainQuery8() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31"))
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(4, list.size());
      for (Transaction t : list) {
         assertTrue(t.getDate().compareTo(makeDate("2013-01-31")) <= 0);
         assertTrue(t.getDate().compareTo(makeDate("2013-01-01")) >= 0);
      }
   }

   @Test
   public void testSampleDomainQuery9() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013, projected by date field only
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .setProjection("date")
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31"))
            .toBuilder().build();

      List<Object[]> list = q.list();
      assertEquals(4, list.size());
      assertEquals(1, list.get(0).length);
      assertEquals(1, list.get(1).length);
      assertEquals(1, list.get(2).length);
      assertEquals(1, list.get(3).length);

      for (int i = 0; i < 4; i++) {
         Date d = (Date) list.get(i)[0];
         assertTrue(d.compareTo(makeDate("2013-01-31")) <= 0);
         assertTrue(d.compareTo(makeDate("2013-01-01")) >= 0);
      }
   }

   @Test
   public void testSampleDomainQuery10() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions for a an account having amount greater than a given amount
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("accountId").eq(2)
            .and().having("amount").gt(40)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(52, list.size());
      assertTrue(list.get(0).getAmount() > 40);
      assertTrue(list.get(1).getAmount() > 40);
   }

   @Test
   public void testSampleDomainQuery11() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("John")
            .and().having("addresses.postCode").eq("X1234")
            .and(qf.having("accountIds").eq(1))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("Doe", list.get(0).getSurname());
   }

   @Test
   public void testSampleDomainQuery12() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that represents credits to the account
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("accountId").eq(1)
            .and()
            .not().having("isDebit").eq(true).toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(1, list.size());
      assertFalse(list.get(0).isDebit());
   }

   @Test
   public void testSampleDomainQuery13() throws Exception {
      QueryFactory qf = getQueryFactory();

      // the user that has the bank account with id 3
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").contains(3).toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(2, list.get(0).getId());
      assertTrue(list.get(0).getAccountIds().contains(3));
   }

   @Test
   public void testSampleDomainQuery14() throws Exception {
      QueryFactory qf = getQueryFactory();

      // the user that has all the specified bank accounts
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(2, 1).toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
      assertTrue(list.get(0).getAccountIds().contains(1));
      assertTrue(list.get(0).getAccountIds().contains(2));
   }

   @Test
   public void testSampleDomainQuery15() throws Exception {
      QueryFactory qf = getQueryFactory();

      // the user that has at least one of the specified accounts
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAny(1, 3).toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(1, 2).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(1, 2).contains(list.get(1).getId()));
   }

   @Test
   public void testSampleDomainQuery16() throws Exception {
      QueryFactory qf = getQueryFactory();

      // third batch of 10 transactions for a given account
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .startOffset(20).maxResults(10)
            .orderBy("id", SortOrder.ASC)
            .having("accountId").eq(2).and().having("description").like("Expensive%")
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(50, q.getResultSize());
      assertEquals(10, list.size());
      for (int i = 0; i < 10; i++) {
         assertEquals("Expensive shoes " + (20 + i), list.get(i).getDescription());
      }
   }

   @Test
   public void testSampleDomainQuery17() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all accounts for a user. first get the user by id and then get his account.
      Query q1 = qf.from(getModelFactory().getUserImplClass())
            .having("id").eq(1).toBuilder().build();

      List<User> users = q1.list();
      Query q2 = qf.from(getModelFactory().getAccountImplClass())
            .orderBy("description", SortOrder.ASC)
            .having("id").in(users.get(0).getAccountIds()).toBuilder().build();

      List<Account> list = q2.list();
      assertEquals(2, list.size());
      assertEquals("John Doe's first bank account", list.get(0).getDescription());
      assertEquals("John Doe's second bank account", list.get(1).getDescription());
   }

   @Test
   public void testSampleDomainQuery18() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all transactions of account with id 2 which have an amount larger than 1600 or their description contains the word 'rent'
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .orderBy("description", SortOrder.ASC)
            .having("accountId").eq(1)
            .and(qf.having("amount").gt(1600)
                       .or().having("description").like("%rent%")).toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(2, list.size());
      assertEquals("Birthday present", list.get(0).getDescription());
      assertEquals("Feb. rent payment", list.get(1).getDescription());
   }

   @Test
   public void testProjectionOnOptionalField() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .setProjection("id", "addresses.postCode")
            .orderBy("id", SortOrder.ASC)
            .build();

      List<Object[]> list = q.list();
      assertEquals(3, list.size());
      assertEquals(1, list.get(0)[0]);
      assertEquals(2, list.get(1)[0]);
      assertEquals(3, list.get(2)[0]);
      assertEquals("X1234", list.get(0)[1]);
      assertEquals("Y12", list.get(1)[1]);
      assertNull(list.get(2)[1]);
   }

   @Test
   public void testSampleDomainQuery19() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("addresses.postCode").in("ZZ", "X1234").toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(1, 2).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(1, 2).contains(list.get(1).getId()));
   }

   @Test
   public void testSampleDomainQuery20() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("addresses.postCode").in("X1234").toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(2, 3).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(2, 3).contains(list.get(1).getId()));
   }

   @Test
   public void testSampleDomainQuery21() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("addresses").isNull().toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(1, 2).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(1, 2).contains(list.get(1).getId()));
   }

   @Test
   public void testSampleDomainQuery22() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("addresses.postCode").like("%123%").toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(2, 3).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(2, 3).contains(list.get(1).getId()));
   }

   @Test
   public void testSampleDomainQuery23() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("id").between(1, 2)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(3, list.get(0).getId());
   }

   @Test
   public void testSampleDomainQuery24() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("id").between(1, 2).includeLower(false)
            .toBuilder().build();

      List<User> list = q.list();

      assertEquals(2, list.size());
      assertTrue(Arrays.asList(1, 3).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(1, 3).contains(list.get(1).getId()));
   }

   @Test
   public void testSampleDomainQuery25() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("id").between(1, 2).includeUpper(false)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(2, 3).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(2, 3).contains(list.get(1).getId()));
   }

   @Test
   public void testSampleDomainQuery26() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
          .having("creationDate").eq(makeDate("2013-01-20"))
          .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(1, list.size());
      assertEquals(3, list.get(0).getId());
   }

   @Test
   public void testSampleDomainQuery27() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .orderBy("id", SortOrder.ASC)
            .having("creationDate").lt(makeDate("2013-01-20"))
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(2, list.size());
      assertEquals(1, list.get(0).getId());
      assertEquals(2, list.get(1).getId());
   }

   @Test
   public void testSampleDomainQuery28() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .orderBy("id", SortOrder.ASC)
            .having("creationDate").lte(makeDate("2013-01-20"))
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(3, list.size());
      assertEquals(1, list.get(0).getId());
      assertEquals(2, list.get(1).getId());
      assertEquals(3, list.get(2).getId());
   }

   @Test
   public void testSampleDomainQuery29() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .having("creationDate").gt(makeDate("2013-01-04"))
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(1, list.size());
      assertEquals(3, list.get(0).getId());
   }

   @Test(expected = IllegalStateException.class)
   public void testWrongQueryBuilding1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.not().having("name").eq("John").toBuilder().build();
   }

   @Test(expected = IllegalStateException.class)
   public void testWrongQueryBuilding2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("John").toBuilder()
            .having("surname").eq("Man").toBuilder()
            .build();
   }

   @Test(expected = IllegalStateException.class)
   public void testWrongQueryBuilding3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("name").eq("John").toBuilder()
            .not().having("surname").eq("Man").toBuilder()
            .build();
   }

   @Test(expected = IllegalStateException.class)
   public void testWrongQueryBuilding4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(qf.having("name").eq("John")).toBuilder()
            .not(qf.having("surname").eq("Man")).toBuilder()
            .build();
   }

   @Test(expected = IllegalStateException.class)
   public void testWrongQueryBuilding5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(qf.having("name").eq("John")).toBuilder()
            .not(qf.having("surname").eq("Man")).toBuilder()
            .build();
   }

   @Test(expected = IllegalArgumentException.class)
   public void testWrongQueryBuilding6() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(null)
            .toBuilder().build();
   }

   @Test(expected = IllegalStateException.class)
   public void testWrongQueryBuilding7() throws Exception {
      QueryFactory qf = getQueryFactory();

      FilterConditionEndContext q1 = qf.from(getModelFactory().getUserImplClass())
            .having("gender");

      q1.eq(User.Gender.MALE);
      q1.eq(User.Gender.FEMALE);
   }

   @Test(expected = IllegalArgumentException.class)
   public void testPagination1() throws Exception {
      QueryFactory qf = getQueryFactory();

      qf.from(getModelFactory().getUserImplClass())
            .maxResults(0);
   }

   @Test(expected = IllegalArgumentException.class)
   public void testPagination2() throws Exception {
      QueryFactory qf = getQueryFactory();

      qf.from(getModelFactory().getUserImplClass())
            .maxResults(-4);
   }

   @Test(expected = IllegalArgumentException.class)
   public void testPagination3() throws Exception {
      QueryFactory qf = getQueryFactory();

      qf.from(getModelFactory().getUserImplClass())
            .startOffset(-3);
   }

   @Test
   public void testOrderedPagination4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .maxResults(5)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(3, list.size());
   }

   @Test
   public void testUnorderedPagination4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .maxResults(5)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(3, list.size());
   }

   @Test
   public void testOrderedPagination5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .startOffset(20)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(0, list.size());
   }

   @Test
   public void testUnorderedPagination5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .startOffset(20)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(0, list.size());
   }

   @Test
   public void testOrderedPagination6() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .startOffset(20).maxResults(10)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(0, list.size());
   }

   @Test
   public void testUnorderedPagination6() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .startOffset(20).maxResults(10)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(0, list.size());
   }

   @Test
   public void testOrderedPagination7() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .startOffset(1).maxResults(10)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(2, list.size());
   }

   @Test
   public void testUnorderedPagination7() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .startOffset(1).maxResults(10)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(2, list.size());
   }

   @Test
   public void testOrderedPagination8() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .startOffset(0).maxResults(2)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(2, list.size());
   }

   @Test
   public void testUnorderedPagination8() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .startOffset(0).maxResults(2)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(2, list.size());
   }

   private static ModelFactory getModelFactory() {
      return ModelFactoryHS.INSTANCE;
   }

}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/BaseMatcher.java
package org.infinispan.objectfilter.impl;

import org.hibernate.hql.QueryParser;
import org.infinispan.objectfilter.FilterCallback;
import org.infinispan.objectfilter.FilterSubscription;
import org.infinispan.objectfilter.Matcher;
import org.infinispan.objectfilter.ObjectFilter;
import org.infinispan.objectfilter.impl.hql.FilterParsingResult;
import org.infinispan.objectfilter.impl.hql.FilterProcessingChain;
import org.infinispan.objectfilter.impl.predicateindex.MatcherEvalContext;
import org.infinispan.objectfilter.impl.syntax.BooleanExpr;
import org.infinispan.objectfilter.impl.syntax.BooleanFilterNormalizer;
import org.infinispan.query.dsl.Query;
import org.infinispan.query.dsl.impl.BaseQuery;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
abstract class BaseMatcher<TypeMetadata, AttributeMetadata, AttributeId extends Comparable<AttributeId>> implements Matcher {

   private final ReentrantReadWriteLock readWriteLock = new ReentrantReadWriteLock();

   private final Lock read = readWriteLock.readLock();

   private final Lock write = readWriteLock.writeLock();

   private final QueryParser queryParser = new QueryParser();

   private final BooleanFilterNormalizer booleanFilterNormalizer = new BooleanFilterNormalizer();

   protected final Map<String, FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId>> filtersByTypeName = new HashMap<String, FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId>>();

   protected final Map<TypeMetadata, FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId>> filtersByType = new HashMap<TypeMetadata, FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId>>();

   /**
    * Executes the registered filters and notifies each one of them whether it was satisfied or not by the given
    * instance.
    *
    * @param userContext an optional user provided object to be passed to matching subscribers along with the matching
    *                    instance; can be {@code null}
    * @param instance    the object to test against the registered filters; never {@code null}
    * @param eventType   on optional event type discriminator that is matched against the even type specified when the
    *                    filter was registered; can be {@code null}
    */
   @Override
   public void match(Object userContext, Object instance, Object eventType) {
      if (instance == null) {
         throw new IllegalArgumentException("argument cannot be null");
      }

      read.lock();
      try {
         MatcherEvalContext<TypeMetadata, AttributeMetadata, AttributeId> ctx = startContext(userContext, instance, eventType);
         if (ctx != null) {
            ctx.match();
         }
      } finally {
         read.unlock();
      }
   }

   @Override
   public ObjectFilter getObjectFilter(Query query) {
      BaseQuery baseQuery = (BaseQuery) query;
      return getObjectFilter(baseQuery.getJPAQuery());
   }

   @Override
   public ObjectFilter getObjectFilter(String jpaQuery) {
      FilterParsingResult<TypeMetadata> parsingResult = parse(jpaQuery);
      BooleanExpr normalizedFilter = booleanFilterNormalizer.normalize(parsingResult.getQuery());
      return new ObjectFilterImpl<TypeMetadata, AttributeMetadata, AttributeId>(this, createMetadataAdapter(parsingResult.getTargetEntityMetadata()), jpaQuery, parsingResult, normalizedFilter);
   }

   @Override
   public ObjectFilter getObjectFilter(FilterSubscription filterSubscription) {
      FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId> filterSubscriptionImpl = (FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId>) filterSubscription;
      return getObjectFilter(filterSubscriptionImpl.getQueryString());
   }

   @Override
   public FilterSubscription registerFilter(Query query, FilterCallback callback, Object... eventType) {
      BaseQuery baseQuery = (BaseQuery) query;
      return registerFilter(baseQuery.getJPAQuery(), callback);
   }

   @Override
   public FilterSubscription registerFilter(String jpaQuery, FilterCallback callback, Object... eventType) {
      FilterParsingResult<TypeMetadata> parsingResult = parse(jpaQuery);
      BooleanExpr normalizedFilter = booleanFilterNormalizer.normalize(parsingResult.getQuery());

      write.lock();
      try {
         FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId> filterRegistry = filtersByTypeName.get(parsingResult.getTargetEntityName());
         if (filterRegistry == null) {
            filterRegistry = new FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId>(createMetadataAdapter(parsingResult.getTargetEntityMetadata()), true);
            filtersByTypeName.put(parsingResult.getTargetEntityName(), filterRegistry);
            filtersByType.put(filterRegistry.getMetadataAdapter().getTypeMetadata(), filterRegistry);
         }
         return filterRegistry.addFilter(jpaQuery, normalizedFilter, parsingResult.getProjections(), parsingResult.getSortFields(), callback, eventType);
      } finally {
         write.unlock();
      }
   }

   private FilterParsingResult<TypeMetadata> parse(String jpaQuery) {
      //todo [anistor] query params not yet fully supported by HQL parser. to be added later.
      return queryParser.parseQuery(jpaQuery, createFilterProcessingChain(null));
   }

   @Override
   public void unregisterFilter(FilterSubscription filterSubscription) {
      FilterSubscriptionImpl filterSubscriptionImpl = (FilterSubscriptionImpl) filterSubscription;
      write.lock();
      try {
         FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId> filterRegistry = filtersByTypeName.get(filterSubscriptionImpl.getEntityTypeName());
         if (filterRegistry != null) {
            filterRegistry.removeFilter(filterSubscription);
         } else {
            throw new IllegalStateException("Reached illegal state");
         }
         if (filterRegistry.getNumFilters() == 0) {
            filtersByTypeName.remove(filterRegistry.getMetadataAdapter().getTypeName());
            filtersByType.remove(filterRegistry.getMetadataAdapter().getTypeMetadata());
         }
      } finally {
         write.unlock();
      }
   }

   /**
    * Creates a new MatcherEvalContext only if the given instance is of a type that has some filters registered. This
    * method is called while holding the internal write lock.
    *
    * @param instance the instance to filter; never null
    * @return the context or null if no filter was registered for the instance
    */
   protected abstract MatcherEvalContext<TypeMetadata, AttributeMetadata, AttributeId> startContext(Object userContext, Object instance, Object eventType);

   protected abstract MatcherEvalContext<TypeMetadata, AttributeMetadata, AttributeId> startContext(Object userContext, Object instance, FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId> filterSubscription, Object eventType);

   protected abstract MatcherEvalContext<TypeMetadata, AttributeMetadata, AttributeId> createContext(Object userContext, Object instance, Object eventType);

   protected abstract FilterProcessingChain<TypeMetadata> createFilterProcessingChain(Map<String, Object> namedParameters);

   protected abstract MetadataAdapter<TypeMetadata, AttributeMetadata, AttributeId> createMetadataAdapter(TypeMetadata typeMetadata);

   protected abstract FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId> getFilterRegistryForType(TypeMetadata entityType);
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/FilterRegistry.java
package org.infinispan.objectfilter.impl;

import org.infinispan.objectfilter.FilterCallback;
import org.infinispan.objectfilter.FilterSubscription;
import org.infinispan.objectfilter.SortField;
import org.infinispan.objectfilter.impl.predicateindex.FilterEvalContext;
import org.infinispan.objectfilter.impl.predicateindex.MatcherEvalContext;
import org.infinispan.objectfilter.impl.predicateindex.PredicateIndex;
import org.infinispan.objectfilter.impl.predicateindex.be.BETree;
import org.infinispan.objectfilter.impl.predicateindex.be.BETreeMaker;
import org.infinispan.objectfilter.impl.syntax.BooleanExpr;
import org.infinispan.objectfilter.impl.util.StringHelper;

import java.util.ArrayList;
import java.util.List;

/**
 * A registry for filters on the same type of entity.
 *
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId extends Comparable<AttributeId>> {

   private final PredicateIndex<AttributeMetadata, AttributeId> predicateIndex;

   private final List<FilterSubscriptionImpl> filterSubscriptions = new ArrayList<FilterSubscriptionImpl>();

   private final BETreeMaker<AttributeId> treeMaker;

   private final MetadataAdapter<TypeMetadata, AttributeMetadata, AttributeId> metadataAdapter;

   private final boolean useIntervals;

   public FilterRegistry(MetadataAdapter<TypeMetadata, AttributeMetadata, AttributeId> metadataAdapter, boolean useIntervals) {
      this.metadataAdapter = metadataAdapter;
      this.useIntervals = useIntervals;
      treeMaker = new BETreeMaker<AttributeId>(metadataAdapter, useIntervals);
      predicateIndex = new PredicateIndex<AttributeMetadata, AttributeId>(metadataAdapter);
   }

   public MetadataAdapter<TypeMetadata, AttributeMetadata, AttributeId> getMetadataAdapter() {
      return metadataAdapter;
   }

   public PredicateIndex<AttributeMetadata, AttributeId> getPredicateIndex() {
      return predicateIndex;
   }

   public int getNumFilters() {
      return filterSubscriptions.size();
   }

   /**
    * Executes the registered filters and notifies each one of them whether it was satisfied or not by the given
    * instance.
    *
    * @param ctx
    */
   public void match(MatcherEvalContext<?, AttributeMetadata, AttributeId> ctx) {
      // try to match
      ctx.process(predicateIndex.getRoot());

      // notify subscribers
      for (FilterSubscriptionImpl s : filterSubscriptions) {
         FilterEvalContext filterEvalContext = ctx.getFilterEvalContext(s);
         if (filterEvalContext.getMatchResult()) {
            // check if event type is matching
            s.getCallback().onFilterResult(ctx.getUserContext(), ctx.getInstance(), ctx.getEventType(), filterEvalContext.getProjection(), filterEvalContext.getSortProjection());
         }
      }
   }

   public FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId> addFilter(String queryString, BooleanExpr normalizedFilter, List<String> projection, List<SortField> sortFields, FilterCallback callback, Object[] eventTypes) {
      if (eventTypes != null) {
         if (eventTypes.length == 0) {
            eventTypes = null;
         } else {
            for (Object et : eventTypes) {
               if (et == null) {
                  eventTypes = null;
                  break;
               }
            }
         }
      }

      List<List<AttributeId>> translatedProjections = null;
      if (projection != null && !projection.isEmpty()) {
         translatedProjections = new ArrayList<List<AttributeId>>(projection.size());
         for (String projectionPath : projection) {
            translatedProjections.add(metadataAdapter.translatePropertyPath(StringHelper.splitPropertyPath(projectionPath)));
         }
      }

      List<List<AttributeId>> translatedSortFields = null;
      if (sortFields != null && !sortFields.isEmpty()) {
         translatedSortFields = new ArrayList<List<AttributeId>>(sortFields.size());
         for (SortField sortField : sortFields) {
            translatedSortFields.add(metadataAdapter.translatePropertyPath(StringHelper.splitPropertyPath(sortField.getPath())));
         }
      }

      BETree beTree = treeMaker.make(normalizedFilter);
      FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId> filterSubscription = new FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId>(queryString, useIntervals, metadataAdapter, beTree, callback, projection, translatedProjections, sortFields, translatedSortFields, eventTypes);
      filterSubscription.registerProjection(predicateIndex);
      filterSubscription.subscribe(predicateIndex);
      filterSubscription.index = filterSubscriptions.size();
      filterSubscriptions.add(filterSubscription);
      return filterSubscription;
   }

   public void removeFilter(FilterSubscription filterSubscription) {
      FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId> filterSubscriptionImpl = (FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId>) filterSubscription;
      filterSubscriptionImpl.unregisterProjection(predicateIndex);
      filterSubscriptionImpl.unsubscribe(predicateIndex);
      filterSubscriptions.remove(filterSubscriptionImpl);
      for (int i = filterSubscriptionImpl.index; i < filterSubscriptions.size(); i++) {
         filterSubscriptions.get(i).index--;
      }
      filterSubscriptionImpl.index = -1;
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/ObjectFilterImpl.java
package org.infinispan.objectfilter.impl;

import org.infinispan.objectfilter.FilterCallback;
import org.infinispan.objectfilter.ObjectFilter;
import org.infinispan.objectfilter.SortField;
import org.infinispan.objectfilter.impl.hql.FilterParsingResult;
import org.infinispan.objectfilter.impl.predicateindex.AttributeNode;
import org.infinispan.objectfilter.impl.predicateindex.FilterEvalContext;
import org.infinispan.objectfilter.impl.predicateindex.MatcherEvalContext;
import org.infinispan.objectfilter.impl.syntax.BooleanExpr;

import java.util.Comparator;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
final class ObjectFilterImpl<TypeMetadata, AttributeMetadata, AttributeId extends Comparable<AttributeId>> implements ObjectFilter {

   private final BaseMatcher<TypeMetadata, AttributeMetadata, AttributeId> matcher;

   private final FilterSubscriptionImpl<TypeMetadata, AttributeMetadata, AttributeId> filterSubscription;

   private final AttributeNode<AttributeMetadata, AttributeId> root;

   private static final FilterCallback emptyCallback = new FilterCallback() {
      @Override
      public void onFilterResult(Object userContext, Object instance, Object eventType, Object[] projection, Comparable[] sortProjection) {
         // do nothing
      }
   };

   public ObjectFilterImpl(BaseMatcher<TypeMetadata, AttributeMetadata, AttributeId> matcher,
                           MetadataAdapter<TypeMetadata, AttributeMetadata, AttributeId> metadataAdapter,
                           String jpaQuery, FilterParsingResult<TypeMetadata> parsingResult, BooleanExpr normalizedFilter) {
      this.matcher = matcher;

      //todo [anistor] we need an efficient single-filter registry
      FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId> filterRegistry = new FilterRegistry<TypeMetadata, AttributeMetadata, AttributeId>(metadataAdapter, false);
      filterSubscription = filterRegistry.addFilter(jpaQuery, normalizedFilter, parsingResult.getProjections(), parsingResult.getSortFields(), emptyCallback, null);
      root = filterRegistry.getPredicateIndex().getRoot();
   }

   @Override
   public String getEntityTypeName() {
      return filterSubscription.getEntityTypeName();
   }

   @Override
   public String[] getProjection() {
      return filterSubscription.getProjection();
   }

   @Override
   public SortField[] getSortFields() {
      return filterSubscription.getSortFields();
   }

   @Override
   public Comparator<Comparable[]> getComparator() {
      return filterSubscription.getComparator();
   }

   @Override
   public FilterResult filter(Object instance) {
      if (instance == null) {
         throw new IllegalArgumentException("argument cannot be null");
      }

      MatcherEvalContext<TypeMetadata, AttributeMetadata, AttributeId> matcherEvalContext = matcher.startContext(null, instance, filterSubscription, null);
      if (matcherEvalContext != null) {
         FilterEvalContext filterEvalContext = matcherEvalContext.initSingleFilterContext(filterSubscription);
         matcherEvalContext.process(root);

         if (filterEvalContext.getMatchResult()) {
            return new FilterResultImpl(instance, filterEvalContext.getProjection(), filterEvalContext.getSortProjection());
         }
      }

      return null;
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/hql/ReflectionEntityNamesResolver.java
package org.infinispan.objectfilter.impl.hql;

import org.hibernate.hql.ast.spi.EntityNamesResolver;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class ReflectionEntityNamesResolver implements EntityNamesResolver {

   private final ClassLoader classLoader;

   public ReflectionEntityNamesResolver(ClassLoader classLoader) {
      this.classLoader = classLoader;
   }

   @Override
   public Class<?> getClassFromName(String entityName) {
      if (classLoader != null) {
         try {
            return classLoader.loadClass(entityName);
         } catch (ClassNotFoundException e) {
            return null;
         }
      }

      try {
         return Class.forName(entityName);
      } catch (ClassNotFoundException e) {
         return null;
      }
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/AndExpr.java
package org.infinispan.objectfilter.impl.syntax;

import java.util.List;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class AndExpr extends BooleanOperatorExpr {

   public AndExpr(BooleanExpr... children) {
      super(children);
   }

   public AndExpr(List<BooleanExpr> children) {
      super(children);
   }

   @Override
   public BooleanExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public String toString() {
      StringBuilder sb = new StringBuilder();
      sb.append("AND(");
      boolean isFirst = true;
      for (BooleanExpr c : children) {
         if (isFirst) {
            isFirst = false;
         } else {
            sb.append(", ");
         }
         sb.append(c);
      }
      sb.append(")");
      return sb.toString();
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/BooleanExpr.java
package org.infinispan.objectfilter.impl.syntax;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public interface BooleanExpr extends Visitable<BooleanExpr> {
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/BooleanFilterNormalizer.java
package org.infinispan.objectfilter.impl.syntax;

import java.util.ArrayList;
import java.util.List;

/**
 * Applies some optimisations to a boolean expression. Most notably, it brings it to NNF (Negation normal form, see
 * http://en.wikipedia.org/wiki/Negation_normal_form). Moves negation directly near the variable by repeatedly applying
 * the De Morgan's laws (see http://en.wikipedia.org/wiki/De_Morgan%27s_laws). Eliminates double negation. Normalizes
 * comparison operators by replacing 'greater' with 'less'. Detects sub-expressions that are boolean constants.
 * Simplifies boolean constants by applying boolean short-circuiting. Eliminates resulting trivial conjunctions or
 * disjunctions that have only one child. Ensures all paths from root to leafs contain an alternation of conjunction and
 * disjunction. This is achieved by absorbing the children whenever a boolean sub-expression if of the same kind as the
 * parent.
 *
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class BooleanFilterNormalizer {

   /**
    * A visitor that removes constant boolean expressions, absorbs sub-expressions (removes needless parentheses) and
    * swaps comparison operand sides to ensure the constant is always on the right side.
    */
   private final Visitor simplifierVisitor = new NoOpVisitor() {

      @Override
      public BooleanExpr visit(NotExpr notExpr) {
         // push the negation down the tree until it reaches a PrimaryPredicateExpr
         return notExpr.getChild().acceptVisitor(deMorganVisitor);
      }

      @Override
      public BooleanExpr visit(OrExpr orExpr) {
         List<BooleanExpr> children = new ArrayList<BooleanExpr>(orExpr.getChildren().size());

         for (BooleanExpr child : orExpr.getChildren()) {
            child = child.acceptVisitor(this);

            if (child instanceof ConstantBooleanExpr) {
               // remove boolean constants or shortcircuit entirely
               if (((ConstantBooleanExpr) child).getValue()) {
                  return ConstantBooleanExpr.TRUE;
               }
            } else if (child instanceof OrExpr) {
               // absorb sub-expressions of the same kind
               children.addAll(((OrExpr) child).getChildren());
            } else {
               children.add(child);
            }
         }

         optimizePredicates(children, false);

         // simplify trivial expressions
         if (children.size() == 1) {
            return children.get(0);
         }

         return new OrExpr(children);
      }

      @Override
      public BooleanExpr visit(AndExpr andExpr) {
         List<BooleanExpr> children = new ArrayList<BooleanExpr>(andExpr.getChildren().size());

         for (BooleanExpr child : andExpr.getChildren()) {
            child = child.acceptVisitor(this);

            if (child instanceof ConstantBooleanExpr) {
               // remove boolean constants or shortcircuit entirely
               if (!((ConstantBooleanExpr) child).getValue()) {
                  return ConstantBooleanExpr.FALSE;
               }
            } else if (child instanceof AndExpr) {
               // absorb sub-expressions of the same kind
               children.addAll(((AndExpr) child).getChildren());
            } else {
               children.add(child);
            }
         }

         optimizePredicates(children, true);

         // simplify trivial expressions
         if (children.size() == 1) {
            return children.get(0);
         }

         return new AndExpr(children);
      }

      private void optimizePredicates(List<BooleanExpr> children, boolean isConjunction) {
         removeRedundantPredicates(children, isConjunction);
         optimizeOverlappingIntervalPredicates(children, isConjunction);
      }

      /**
       * Removes duplicate occurrences of same predicate in a conjunction or disjunction. Also detects and removes tautology and contradiction.
       * The following translation rules are applied:
       * <ul>
       * <li>X || X => X</li>
       * <li>X && X => X</li>
       * <li>!X || !X => !X</li>
       * <li>!X && !X => !X</li>
       * <li>X || !X => TRUE (tautology)</li>
       * <li>X && !X => FALSE (contradiction)</li>
       * </ul>
       * @param children the list of children expressions
       * @param isConjunction is the parent boolean expression a conjunction or a disjunction?
       */
      private void removeRedundantPredicates(List<BooleanExpr> children, boolean isConjunction) {
         for (int i = 0; i < children.size(); i++) {
            BooleanExpr ci = children.get(i);
            if (ci instanceof BooleanOperatorExpr) {
               // we may encounter non-predicate expressions, just ignore them
               continue;
            }
            boolean isCiNegated = ci instanceof NotExpr;
            if (isCiNegated) {
               ci = ((NotExpr) ci).getChild();
            }
            assert ci instanceof PrimaryPredicateExpr;
            PrimaryPredicateExpr ci1 = (PrimaryPredicateExpr) ci;
            assert ci1.getChild() instanceof PropertyValueExpr;
            PropertyValueExpr pve = (PropertyValueExpr) ci1.getChild();
            if (pve.isRepeated()) {
               // do not optimize repeated predicates
               continue;
            }
            int j = i + 1;
            while (j < children.size()) {
               BooleanExpr cj = children.get(j);
               // we may encounter non-predicate expressions, just ignore them
               if (!(cj instanceof BooleanOperatorExpr)) {
                  boolean isCjNegated = cj instanceof NotExpr;
                  if (isCjNegated) {
                     cj = ((NotExpr) cj).getChild();
                  }
                  PrimaryPredicateExpr cj1 = (PrimaryPredicateExpr) cj;
                  assert cj1.getChild() instanceof PropertyValueExpr;
                  PropertyValueExpr pve2 = (PropertyValueExpr) cj1.getChild();
                  // do not optimize repeated predicates
                  if (!pve2.isRepeated()) {
                     int res = comparePrimaryPredicateExpr(isCiNegated, ci1, isCjNegated, cj1);
                     if (res == 0) {
                        // found duplication
                        children.remove(j);
                        continue;
                     } else if (res == 1) {
                        // found tautology or contradiction
                        children.clear();
                        children.add(ConstantBooleanExpr.forBoolean(!isConjunction));
                        return;
                     }
                  }
               }
               j++;
            }
         }
      }

      /**
       * Checks if two predicates are identical or opposite.
       *
       * @param isFirstNegated is first predicate negated?
       * @param first the first predicate expression
       * @param isSecondNegated is second predicate negated?
       * @param second the second predicate expression
       * @return -1 if unrelated predicates, 0 if identical predicates, 1 if opposite predicates
       */
      private int comparePrimaryPredicateExpr(boolean isFirstNegated, PrimaryPredicateExpr first, boolean isSecondNegated, PrimaryPredicateExpr second) {
         if (first.getClass() == second.getClass()) {
            if (first instanceof ComparisonExpr) {
               ComparisonExpr comparison1 = (ComparisonExpr) first;
               ComparisonExpr comparison2 = (ComparisonExpr) second;
               assert comparison1.getLeftChild() instanceof PropertyValueExpr;
               assert comparison1.getRightChild() instanceof ConstantValueExpr;
               assert comparison2.getLeftChild() instanceof PropertyValueExpr;
               assert comparison2.getRightChild() instanceof ConstantValueExpr;
               assert !isFirstNegated;
               assert !isSecondNegated;
               if (comparison1.getLeftChild().equals(comparison2.getLeftChild()) && comparison1.getRightChild().equals(comparison2.getRightChild())) {
                  ComparisonExpr.Type cmpType1 = comparison1.getComparisonType();
                  ComparisonExpr.Type cmpType2 = comparison2.getComparisonType();
                  return cmpType1 == cmpType2 ? 0 : (cmpType1 == cmpType2.negate() ? 1 : -1);
               }
            } else if (first.equals(second)) {
               return isFirstNegated == isSecondNegated ? 0 : 1;
            }
         }
         return -1;
      }

      private void optimizeOverlappingIntervalPredicates(List<BooleanExpr> children, boolean isConjunction) {
         for (int i = 0; i < children.size(); i++) {
            BooleanExpr ci = children.get(i);
            if (ci instanceof ComparisonExpr) {
               ComparisonExpr first = (ComparisonExpr) ci;
               assert first.getLeftChild() instanceof PropertyValueExpr;
               assert first.getRightChild() instanceof ConstantValueExpr;

               PropertyValueExpr pve = (PropertyValueExpr) first.getLeftChild();
               if (pve.isRepeated()) {
                  // do not optimize repeated predicates
                  continue;
               }

               int j = i + 1;
               while (j < children.size()) {
                  BooleanExpr cj = children.get(j);
                  if (cj instanceof ComparisonExpr) {
                     ComparisonExpr second = (ComparisonExpr) cj;
                     assert second.getLeftChild() instanceof PropertyValueExpr;
                     assert second.getRightChild() instanceof ConstantValueExpr;

                     PropertyValueExpr pve2 = (PropertyValueExpr) second.getLeftChild();
                     // do not optimize repeated predicates
                     if (!pve2.isRepeated()) {
                        if (first.getLeftChild().equals(second.getLeftChild())) {
                           BooleanExpr res = optimizeOverlappingIntervalPredicates(first, second, isConjunction);
                           if (res != null) {
                              if (res instanceof ConstantBooleanExpr) {
                                 children.clear();
                                 children.add(res);
                                 return;
                              }
                              children.remove(j);
                              if (res != first) {
                                 first = (ComparisonExpr) res;
                                 children.set(i, first);
                              }
                              continue;
                           }
                        }
                     }
                  }
                  j++;
               }
            }
         }
      }

      /**
       * @param first
       * @param second
       * @param isConjunction
       * @return null or a replacement BooleanExpr
       */
      private BooleanExpr optimizeOverlappingIntervalPredicates(ComparisonExpr first, ComparisonExpr second, boolean isConjunction) {
         Comparable firstValue = ((ConstantValueExpr) first.getRightChild()).getConstantValue();
         Comparable secondValue = ((ConstantValueExpr) second.getRightChild()).getConstantValue();
         int cmp = firstValue.compareTo(secondValue);

         if (first.getComparisonType() == ComparisonExpr.Type.EQUAL) {
            return eqAndInterval(first, second, isConjunction, cmp);
         } else if (second.getComparisonType() == ComparisonExpr.Type.EQUAL) {
            return eqAndInterval(second, first, isConjunction, -cmp);
         } else if (first.getComparisonType() == ComparisonExpr.Type.NOT_EQUAL) {
            return notEqAndInterval(first, second, isConjunction, cmp);
         } else if (second.getComparisonType() == ComparisonExpr.Type.NOT_EQUAL) {
            return notEqAndInterval(second, first, isConjunction, -cmp);
         }

         if (cmp == 0) {
            if (first.getComparisonType() == second.getComparisonType()) {
               // identical intervals
               return first;
            }
            if (first.getComparisonType() == second.getComparisonType().negate()) {
               // opposite directions, disjoint, union is full coverage
               return isConjunction ? ConstantBooleanExpr.FALSE : ConstantBooleanExpr.TRUE;
            }
            if (first.getComparisonType() == ComparisonExpr.Type.LESS_OR_EQUAL || first.getComparisonType() == ComparisonExpr.Type.GREATER_OR_EQUAL) {
               // opposite directions, overlapping in one point, union is full coverage
               return isConjunction ? new ComparisonExpr(first.getLeftChild(), first.getRightChild(), ComparisonExpr.Type.EQUAL) : ConstantBooleanExpr.TRUE;
            } else {
               // opposite directions, disjoint in one point, union is not full coverage
               return isConjunction ? ConstantBooleanExpr.FALSE : new ComparisonExpr(first.getLeftChild(), first.getRightChild(), ComparisonExpr.Type.NOT_EQUAL);
            }
         }

         // opposite direction intervals
         if (first.getComparisonType() == second.getComparisonType().negate() || first.getComparisonType() == second.getComparisonType().reverse()) {
            if (cmp < 0) {
               if (first.getComparisonType() == ComparisonExpr.Type.LESS || first.getComparisonType() == ComparisonExpr.Type.LESS_OR_EQUAL) {
                  if (isConjunction) {
                     return ConstantBooleanExpr.FALSE;
                  }
               } else if (!isConjunction) {
                  return ConstantBooleanExpr.TRUE;
               }
            } else {
               if (first.getComparisonType() == ComparisonExpr.Type.GREATER || first.getComparisonType() == ComparisonExpr.Type.GREATER_OR_EQUAL) {
                  if (isConjunction) {
                     return ConstantBooleanExpr.FALSE;
                  }
               } else if (!isConjunction) {
                  return ConstantBooleanExpr.TRUE;
               }
            }
            return null;
         }

         // same direction intervals
         if (first.getComparisonType() == ComparisonExpr.Type.LESS || first.getComparisonType() == ComparisonExpr.Type.LESS_OR_EQUAL) {
            // less than
            if (isConjunction) {
               return cmp < 0 ? first : second;
            } else {
               return cmp < 0 ? second : first;
            }
         } else {
            // greater than
            if (isConjunction) {
               return cmp < 0 ? second : first;
            } else {
               return cmp < 0 ? first : second;
            }
         }
      }

      @Override
      public BooleanExpr visit(ComparisonExpr comparisonExpr) {
         // start moving the constant to the right side of the comparison if it's not already there
         ValueExpr leftChild = comparisonExpr.getLeftChild();
         leftChild = leftChild.acceptVisitor(this);

         ValueExpr rightChild = comparisonExpr.getRightChild();
         rightChild = rightChild.acceptVisitor(this);

         ComparisonExpr.Type comparisonType = comparisonExpr.getComparisonType();

         // handle constant expressions
         if (leftChild instanceof ConstantValueExpr) {
            if (rightChild instanceof ConstantValueExpr) {
               // replace the comparison of the two constants with the actual result
               Comparable leftValue = ((ConstantValueExpr) leftChild).getConstantValue();
               Comparable rightValue = ((ConstantValueExpr) rightChild).getConstantValue();
               int compRes = leftValue.compareTo(rightValue);
               switch (comparisonType) {
                  case LESS:
                     return ConstantBooleanExpr.forBoolean(compRes < 0);
                  case LESS_OR_EQUAL:
                     return ConstantBooleanExpr.forBoolean(compRes <= 0);
                  case EQUAL:
                     return ConstantBooleanExpr.forBoolean(compRes == 0);
                  case NOT_EQUAL:
                     return ConstantBooleanExpr.forBoolean(compRes != 0);
                  case GREATER_OR_EQUAL:
                     return ConstantBooleanExpr.forBoolean(compRes >= 0);
                  case GREATER:
                     return ConstantBooleanExpr.forBoolean(compRes > 0);
                  default:
                     throw new IllegalStateException("Unexpected comparison type: " + comparisonType);
               }
            }

            // swap operand sides to ensure the constant is always on the right side
            ValueExpr temp = rightChild;
            rightChild = leftChild;
            leftChild = temp;

            // now reverse the operator too to restore the semantics
            comparisonType = comparisonType.reverse();
         }

         // comparison operators are never negated using NotExpr
         return new ComparisonExpr(leftChild, rightChild, comparisonType);
      }
   };

   private BooleanExpr eqAndInterval(ComparisonExpr first, ComparisonExpr second, boolean isConjunction, int cmp) {
      switch (second.getComparisonType()) {
         case EQUAL:
            if (cmp == 0) {
               return first;
            }
            return isConjunction ? ConstantBooleanExpr.FALSE : null;
         case NOT_EQUAL:
            if (cmp == 0) {
               return ConstantBooleanExpr.forBoolean(!isConjunction);
            }
            return isConjunction ? first : null;
         case LESS:
            if (cmp == 0) {
               return isConjunction ? ConstantBooleanExpr.FALSE : new ComparisonExpr(first.getLeftChild(), first.getRightChild(), ComparisonExpr.Type.LESS_OR_EQUAL);
            }
            if (cmp < 0) {
               return isConjunction ? first : second;
            }
            return isConjunction ? ConstantBooleanExpr.FALSE : null;
         case LESS_OR_EQUAL:
            if (cmp <= 0) {
               return isConjunction ? first : second;
            }
            return isConjunction ? ConstantBooleanExpr.FALSE : null;
         case GREATER:
            if (cmp == 0) {
               return isConjunction ? ConstantBooleanExpr.FALSE : new ComparisonExpr(first.getLeftChild(), first.getRightChild(), ComparisonExpr.Type.GREATER_OR_EQUAL);
            }
            if (cmp > 0) {
               return isConjunction ? first : second;
            }
            return isConjunction ? ConstantBooleanExpr.FALSE : null;
         case GREATER_OR_EQUAL:
            if (cmp >= 0) {
               return isConjunction ? first : second;
            }
            return isConjunction ? ConstantBooleanExpr.FALSE : null;
         default:
            return null;
      }
   }

   private BooleanExpr notEqAndInterval(ComparisonExpr first, ComparisonExpr second, boolean isConjunction, int cmp) {
      switch (second.getComparisonType()) {
         case EQUAL:
            if (cmp == 0) {
               return ConstantBooleanExpr.FALSE;
            }
            return isConjunction ? second : first;
         case NOT_EQUAL:
            if (cmp == 0) {
               return first;
            }
            return isConjunction ? null : ConstantBooleanExpr.TRUE;
         case LESS:
            if (cmp >= 0) {
               return isConjunction ? second : first;
            }
            return isConjunction ? null : ConstantBooleanExpr.TRUE;
         case LESS_OR_EQUAL:
            if (cmp < 0) {
               return isConjunction ? null : ConstantBooleanExpr.TRUE;
            }
            if (cmp > 0) {
               return isConjunction ? second : first;
            }
            return isConjunction ? new ComparisonExpr(first.getLeftChild(), first.getRightChild(), ComparisonExpr.Type.LESS) : ConstantBooleanExpr.TRUE;
         case GREATER:
            if (cmp > 0) {
               return isConjunction ? null : ConstantBooleanExpr.TRUE;
            }
            return isConjunction ? second : first;
         case GREATER_OR_EQUAL:
            if (cmp < 0) {
               return isConjunction ? second : first;
            }
            if (cmp > 0) {
               return isConjunction ? new ComparisonExpr(first.getLeftChild(), first.getRightChild(), ComparisonExpr.Type.GREATER) : ConstantBooleanExpr.TRUE;
            }
            return isConjunction ? ConstantBooleanExpr.FALSE : null;
         default:
            return null;
      }
   }

   /**
    * Handles negation by applying De Morgan laws.
    */
   private final Visitor deMorganVisitor = new NoOpVisitor() {

      @Override
      public BooleanExpr visit(ConstantBooleanExpr constantBooleanExpr) {
         // negated constants are simplified immediately
         return constantBooleanExpr.negate();
      }

      @Override
      public BooleanExpr visit(NotExpr notExpr) {
         // double negation is eliminated, child is simplified
         return notExpr.getChild().acceptVisitor(simplifierVisitor);
      }

      @Override
      public BooleanExpr visit(OrExpr orExpr) {
         List<BooleanExpr> children = new ArrayList<BooleanExpr>(orExpr.getChildren().size());

         for (BooleanExpr child : orExpr.getChildren()) {
            child = child.acceptVisitor(this);

            if (child instanceof ConstantBooleanExpr) {
               // remove boolean constants
               if (!((ConstantBooleanExpr) child).getValue()) {
                  return ConstantBooleanExpr.FALSE;
               }
            } else if (child instanceof AndExpr) {
               // absorb sub-expressions of the same kind
               children.addAll(((AndExpr) child).getChildren());
            } else {
               children.add(child);
            }
         }

         // simplify trivial expressions
         if (children.size() == 1) {
            return children.get(0);
         }

         return new AndExpr(children);
      }

      @Override
      public BooleanExpr visit(AndExpr andExpr) {
         List<BooleanExpr> children = new ArrayList<BooleanExpr>(andExpr.getChildren().size());

         for (BooleanExpr child : andExpr.getChildren()) {
            child = child.acceptVisitor(this);

            if (child instanceof ConstantBooleanExpr) {
               // remove boolean constants
               if (((ConstantBooleanExpr) child).getValue()) {
                  return ConstantBooleanExpr.TRUE;
               }
            } else if (child instanceof OrExpr) {
               // absorb sub-expressions of the same kind
               children.addAll(((OrExpr) child).getChildren());
            } else {
               children.add(child);
            }
         }

         // simplify trivial expressions
         if (children.size() == 1) {
            return children.get(0);
         }

         return new OrExpr(children);
      }

      @Override
      public BooleanExpr visit(ComparisonExpr comparisonExpr) {
         BooleanExpr booleanExpr = comparisonExpr.acceptVisitor(simplifierVisitor);

         // simplify negated constants immediately
         if (booleanExpr instanceof ConstantBooleanExpr) {
            return ((ConstantBooleanExpr) booleanExpr).negate();
         }

         // eliminate double negation
         if (booleanExpr instanceof NotExpr) {
            return ((NotExpr) booleanExpr).getChild();
         }

         // interval predicates are never negated, they are converted instead into the opposite interval
         if (booleanExpr instanceof ComparisonExpr) {
            ComparisonExpr c = (ComparisonExpr) booleanExpr;
            return new ComparisonExpr(c.getLeftChild(), c.getRightChild(), c.getComparisonType().negate());
         }

         return new NotExpr(booleanExpr);
      }

      @Override
      public BooleanExpr visit(IsNullExpr isNullExpr) {
         return new NotExpr(isNullExpr);
      }

      @Override
      public BooleanExpr visit(LikeExpr likeExpr) {
         return new NotExpr(likeExpr);
      }
   };

   public BooleanExpr normalize(BooleanExpr booleanExpr) {
      return booleanExpr.acceptVisitor(simplifierVisitor);
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/ComparisonExpr.java
package org.infinispan.objectfilter.impl.syntax;

/**
 * An expression that represents a comparison of Comparable values.
 *
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class ComparisonExpr implements PrimaryPredicateExpr {

   private final ValueExpr leftChild;
   private final ValueExpr rightChild;
   private final Type type;

   public enum Type {
      LESS,
      LESS_OR_EQUAL,
      EQUAL,
      NOT_EQUAL,
      GREATER_OR_EQUAL,
      GREATER;

      public Type negate() {
         switch (this) {
            case LESS:
               return GREATER_OR_EQUAL;
            case LESS_OR_EQUAL:
               return GREATER;
            case EQUAL:
               return NOT_EQUAL;
            case NOT_EQUAL:
               return EQUAL;
            case GREATER_OR_EQUAL:
               return LESS;
            case GREATER:
               return LESS_OR_EQUAL;
            default:
               return this;
         }
      }

      public Type reverse() {
         switch (this) {
            case LESS:
               return GREATER;
            case GREATER:
               return LESS;
            case LESS_OR_EQUAL:
               return GREATER_OR_EQUAL;
            case GREATER_OR_EQUAL:
               return LESS_OR_EQUAL;
            default:
               return this;
         }
      }
   }

   public ComparisonExpr(ValueExpr leftChild, ValueExpr rightChild, Type type) {
      this.leftChild = leftChild;
      this.rightChild = rightChild;
      this.type = type;
   }

   public ValueExpr getLeftChild() {
      return leftChild;
   }

   public ValueExpr getRightChild() {
      return rightChild;
   }

   public Type getComparisonType() {
      return type;
   }

   @Override
   public ValueExpr getChild() {
      return leftChild;
   }

   @Override
   public BooleanExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public boolean equals(Object o) {
      if (this == o) return true;
      if (o == null || getClass() != o.getClass()) return false;
      ComparisonExpr other = (ComparisonExpr) o;
      return type == other.type && leftChild.equals(other.leftChild) && rightChild.equals(other.rightChild);
   }

   @Override
   public int hashCode() {
      int result = 31 * leftChild.hashCode() + rightChild.hashCode();
      return 31 * result + type.hashCode();
   }

   @Override
   public String toString() {
      return type + "(" + leftChild + ", " + rightChild + ')';
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/ConstantBooleanExpr.java
package org.infinispan.objectfilter.impl.syntax;

/**
 * A constant boolean expression (tautology or contradiction).
 *
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class ConstantBooleanExpr implements PrimaryPredicateExpr {

   public static final ConstantBooleanExpr TRUE = new ConstantBooleanExpr(true);

   public static final ConstantBooleanExpr FALSE = new ConstantBooleanExpr(false);

   public static ConstantBooleanExpr forBoolean(boolean value) {
      return value ? TRUE : FALSE;
   }

   private final boolean constantValue;

   private ConstantBooleanExpr(boolean constantValue) {
      this.constantValue = constantValue;
   }

   @Override
   public ValueExpr getChild() {
      return null;
   }

   public boolean getValue() {
      return constantValue;
   }

   public ConstantBooleanExpr negate() {
      return constantValue ? FALSE : TRUE;
   }

   @Override
   public BooleanExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public boolean equals(Object o) {
      if (this == o) return true;
      if (o == null || getClass() != o.getClass()) return false;
      ConstantBooleanExpr other = (ConstantBooleanExpr) o;
      return constantValue == other.constantValue;
   }

   @Override
   public int hashCode() {
      return constantValue ? 1 : 0;
   }

   @Override
   public String toString() {
      return constantValue ? "CONST_TRUE" : "CONST_FALSE";
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/ConstantValueExpr.java
package org.infinispan.objectfilter.impl.syntax;

/**
 * A constant comparable value, to be used as right or left side in a comparison expression.
 *
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class ConstantValueExpr implements ValueExpr {

   private final Comparable constantValue;

   public ConstantValueExpr(Comparable constantValue) {
      this.constantValue = constantValue;
   }

   public Comparable getConstantValue() {
      return constantValue;
   }

   @Override
   public ValueExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public boolean equals(Object o) {
      if (this == o) return true;
      if (o == null || getClass() != o.getClass()) return false;
      ConstantValueExpr other = (ConstantValueExpr) o;
      return constantValue.equals(other.constantValue);
   }

   @Override
   public int hashCode() {
      return constantValue.hashCode();
   }

   @Override
   public String toString() {
      return "CONST(" + constantValue + ')';
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/IsNullExpr.java
package org.infinispan.objectfilter.impl.syntax;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public class IsNullExpr implements PrimaryPredicateExpr {

   private final ValueExpr child;

   public IsNullExpr(ValueExpr child) {
      this.child = child;
   }

   @Override
   public ValueExpr getChild() {
      return child;
   }

   @Override
   public BooleanExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public boolean equals(Object o) {
      if (this == o) return true;
      if (o == null || getClass() != o.getClass()) return false;
      IsNullExpr other = (IsNullExpr) o;
      return child.equals(other.child);
   }

   @Override
   public int hashCode() {
      return child.hashCode();
   }

   @Override
   public String toString() {
      return "IS_NULL(" + child + ')';
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/LikeExpr.java
package org.infinispan.objectfilter.impl.syntax;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class LikeExpr implements PrimaryPredicateExpr {

   private final ValueExpr child;
   private final String pattern;

   public LikeExpr(ValueExpr child, String pattern) {
      this.child = child;
      this.pattern = pattern;
   }

   @Override
   public ValueExpr getChild() {
      return child;
   }

   public String getPattern() {
      return pattern;
   }

   @Override
   public BooleanExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public boolean equals(Object o) {
      if (this == o) return true;
      if (o == null || getClass() != o.getClass()) return false;
      LikeExpr likeExpr = (LikeExpr) o;
      return pattern.equals(likeExpr.pattern) && child.equals(likeExpr.child);
   }

   @Override
   public int hashCode() {
      return 31 * child.hashCode() + pattern.hashCode();
   }

   @Override
   public String toString() {
      return "LIKE(" + child + ", " + pattern + ')';
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/NotExpr.java
package org.infinispan.objectfilter.impl.syntax;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class NotExpr implements BooleanExpr {

   private BooleanExpr child;

   public NotExpr(BooleanExpr child) {
      this.child = child;
   }


   public BooleanExpr getChild() {
      return child;
   }

   @Override
   public BooleanExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public String toString() {
      return "NOT(" + child + ')';
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/OrExpr.java
package org.infinispan.objectfilter.impl.syntax;

import java.util.List;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class OrExpr extends BooleanOperatorExpr {

   public OrExpr(BooleanExpr... children) {
      super(children);
   }

   public OrExpr(List<BooleanExpr> children) {
      super(children);
   }

   @Override
   public BooleanExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public String toString() {
      StringBuilder sb = new StringBuilder();
      sb.append("OR(");
      boolean isFirst = true;
      for (BooleanExpr c : children) {
         if (isFirst) {
            isFirst = false;
         } else {
            sb.append(", ");
         }
         sb.append(c);
      }
      sb.append(")");
      return sb.toString();
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/PropertyValueExpr.java
package org.infinispan.objectfilter.impl.syntax;

import org.infinispan.objectfilter.impl.util.StringHelper;

import java.util.List;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public final class PropertyValueExpr implements ValueExpr {

   private final List<String> propertyPath;

   private final boolean isRepeated;

   public PropertyValueExpr(List<String> propertyPath, boolean isRepeated) {
      this.propertyPath = propertyPath;
      this.isRepeated = isRepeated;
   }

   public PropertyValueExpr(String propertyPath, boolean isRepeated) {
      this(StringHelper.splitPropertyPath(propertyPath), isRepeated);
   }

   public List<String> getPropertyPath() {
      return propertyPath;
   }

   public boolean isRepeated() {
      return isRepeated;
   }

   @Override
   public ValueExpr acceptVisitor(Visitor visitor) {
      return visitor.visit(this);
   }

   @Override
   public boolean equals(Object o) {
      if (this == o) return true;
      if (o == null || getClass() != o.getClass()) return false;
      PropertyValueExpr other = (PropertyValueExpr) o;
      return propertyPath.equals(other.propertyPath);
   }

   @Override
   public int hashCode() {
      return propertyPath.hashCode();
   }

   @Override
   public String toString() {
      StringBuilder sb = new StringBuilder();
      sb.append("PROP(");
      boolean isFirst = true;
      for (String p : propertyPath) {
         if (isFirst) {
            isFirst = false;
         } else {
            sb.append(',');
         }
         sb.append(p);
      }
      if (isRepeated) {
         sb.append('*');
      }
      sb.append(")");
      return sb.toString();
   }
}


File: object-filter/src/main/java/org/infinispan/objectfilter/impl/syntax/ValueExpr.java
package org.infinispan.objectfilter.impl.syntax;

/**
 * @author anistor@redhat.com
 * @since 7.0
 */
public interface ValueExpr extends Visitable<ValueExpr> {
}


File: object-filter/src/test/java/org/infinispan/objectfilter/test/FilterQueryFactory.java
package org.infinispan.objectfilter.test;

import org.infinispan.objectfilter.impl.logging.Log;
import org.infinispan.protostream.SerializationContext;
import org.infinispan.query.dsl.Query;
import org.infinispan.query.dsl.QueryBuilder;
import org.infinispan.query.dsl.QueryFactory;
import org.infinispan.query.dsl.impl.BaseQuery;
import org.infinispan.query.dsl.impl.BaseQueryBuilder;
import org.infinispan.query.dsl.impl.BaseQueryFactory;
import org.infinispan.query.dsl.impl.JPAQueryGenerator;
import org.jboss.logging.Logger;

import java.util.List;

/**
 * @author anistor@redhat.com
 * @since 7.2
 */
public final class FilterQueryFactory extends BaseQueryFactory<Query> {

   private final SerializationContext serializationContext;

   public FilterQueryFactory(SerializationContext serializationContext) {
      this.serializationContext = serializationContext;
   }

   public FilterQueryFactory() {
      this(null);
   }

   @Override
   public QueryBuilder<Query> from(Class entityType) {
      if (serializationContext != null) {
         serializationContext.getMarshaller(entityType);
      }
      return new FilterQueryBuilder(this, entityType.getCanonicalName());
   }

   @Override
   public QueryBuilder<Query> from(String entityType) {
      if (serializationContext != null) {
         serializationContext.getMarshaller(entityType);
      }
      return new FilterQueryBuilder(this, entityType);
   }

   private static final class FilterQueryBuilder extends BaseQueryBuilder<Query> {

      private static final Log log = Logger.getMessageLogger(Log.class, FilterQueryBuilder.class.getName());

      FilterQueryBuilder(FilterQueryFactory queryFactory, String rootType) {
         super(queryFactory, rootType);
      }

      @Override
      public Query build() {
         String jpqlString = accept(new JPAQueryGenerator());
         if (log.isTraceEnabled()) {
            log.tracef("JPQL string : %s", jpqlString);
         }
         return new FilterQuery(queryFactory, jpqlString);
      }
   }

   private static final class FilterQuery extends BaseQuery {

      FilterQuery(QueryFactory queryFactory, String jpaQuery) {
         super(queryFactory, jpaQuery);
      }

      // TODO [anistor] need to rethink the dsl Query/QueryBuilder interfaces to accommodate the filtering scenario ...
      @Override
      public <T> List<T> list() {
         throw new UnsupportedOperationException();
      }

      @Override
      public int getResultSize() {
         throw new UnsupportedOperationException();
      }
   }
}



File: query-dsl/src/main/java/org/infinispan/query/dsl/impl/BaseQuery.java
package org.infinispan.query.dsl.impl;

import org.infinispan.query.dsl.Query;
import org.infinispan.query.dsl.QueryFactory;

/**
 * @author anistor@redhat.com
 * @since 7.2
 */
public abstract class BaseQuery implements Query {

   protected final QueryFactory queryFactory;

   protected final String jpaQuery;

   public BaseQuery(QueryFactory queryFactory, String jpaQuery) {
      this.queryFactory = queryFactory;
      this.jpaQuery = jpaQuery;
   }

   public QueryFactory getQueryFactory() {
      return queryFactory;
   }

   public String getJPAQuery() {
      return jpaQuery;
   }
}


File: query/src/main/java/org/infinispan/query/dsl/embedded/impl/EmbeddedLuceneQuery.java
package org.infinispan.query.dsl.embedded.impl;

import org.infinispan.query.CacheQuery;
import org.infinispan.query.FetchOptions;
import org.infinispan.query.ResultIterator;
import org.infinispan.query.dsl.QueryFactory;
import org.infinispan.query.dsl.embedded.LuceneQuery;
import org.infinispan.query.dsl.impl.BaseQuery;

import java.util.List;


/**
 * A query implementation based on Lucene.
 *
 * @author anistor@redhat.com
 * @since 6.0
 */
final class EmbeddedLuceneQuery extends BaseQuery implements LuceneQuery {

   private final CacheQuery cacheQuery;

   EmbeddedLuceneQuery(QueryFactory queryFactory, String jpaQuery, CacheQuery cacheQuery) {
      super(queryFactory, jpaQuery);
      this.cacheQuery = cacheQuery;
   }

   @Override
   @SuppressWarnings("unchecked")
   public <T> List<T> list() {
      return (List<T>) cacheQuery.list();
   }

   @Override
   public ResultIterator iterator(FetchOptions fetchOptions) {
      return cacheQuery.iterator(fetchOptions);
   }

   @Override
   public ResultIterator iterator() {
      return cacheQuery.iterator();
   }

   @Override
   public int getResultSize() {
      return cacheQuery.getResultSize();
   }

   @Override
   public String toString() {
      return "EmbeddedLuceneQuery{" +
            "jpaQuery=" + jpaQuery +
            ", cacheQuery=" + cacheQuery +
            '}';
   }
}


File: query/src/main/java/org/infinispan/query/dsl/embedded/impl/EmbeddedQuery.java
package org.infinispan.query.dsl.embedded.impl;

import org.infinispan.AdvancedCache;
import org.infinispan.commons.util.CloseableIterable;
import org.infinispan.objectfilter.ObjectFilter;
import org.infinispan.query.dsl.QueryFactory;
import org.infinispan.query.dsl.impl.BaseQuery;
import org.infinispan.security.AuthorizationManager;
import org.infinispan.security.AuthorizationPermission;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;


/**
 * Non-indexed embedded-mode query.
 *
 * @author anistor@redhat,com
 * @since 7.0
 */
public final class EmbeddedQuery extends BaseQuery {

   private static final int INITIAL_CAPACITY = 1000;

   private final AdvancedCache<?, ?> cache;

   private final JPAFilterAndConverter filter;

   private List results;

   private int resultSize;

   private final String[] projection;

   private final int startOffset;

   private final int maxResults;

   public EmbeddedQuery(QueryFactory queryFactory, AdvancedCache<?, ?> cache, JPAFilterAndConverter filter,
                        long startOffset, int maxResults) {
      super(queryFactory, filter.getJPAQuery());

      ensureAccessPermissions(cache);

      this.cache = cache;
      this.startOffset = startOffset < 0 ? 0 : (int) startOffset;
      this.maxResults = maxResults;
      this.filter = filter;
      this.projection = filter.getObjectFilter().getProjection();
   }

   private void ensureAccessPermissions(AdvancedCache<?, ?> cache) {
      AuthorizationManager authorizationManager = SecurityActions.getCacheAuthorizationManager(cache);
      if (authorizationManager != null) {
         authorizationManager.checkPermission(AuthorizationPermission.BULK_READ);
      }
   }

   public String[] getProjection() {
      return projection;
   }

   @Override
   public <T> List<T> list() {
      if (results == null) {
         results = listInternal();
      }
      return results;
   }

   private List listInternal() {
      List results;

      CloseableIterable<Map.Entry<?, ObjectFilter.FilterResult>> iterable = cache.filterEntries(filter).converter(filter);
      Comparator<Comparable[]> comparator = filter.getObjectFilter().getComparator();
      if (comparator == null) {
         // collect unsorted results and get the requested page if any was specified
         results = new ArrayList(INITIAL_CAPACITY);
         try {
            for (Map.Entry<?, ObjectFilter.FilterResult> entry : iterable) {
               resultSize++;
               if (resultSize > startOffset && (maxResults == -1 || results.size() < maxResults)) {
                  ObjectFilter.FilterResult r = entry.getValue();
                  results.add(projection != null ? r.getProjection() : r.getInstance());
               }
            }
         } finally {
            try {
               iterable.close();
            } catch (Exception e) {
               // exception ignored
            }
         }
      } else {
         // collect and sort results, in reverse order for now
         PriorityQueue<ObjectFilter.FilterResult> filterResults = new PriorityQueue<ObjectFilter.FilterResult>(INITIAL_CAPACITY, new ReverseFilterResultComparator(comparator));
         try {
            for (Map.Entry<?, ObjectFilter.FilterResult> entry : iterable) {
               resultSize++;
               filterResults.add(entry.getValue());
               if (maxResults != -1 && filterResults.size() > startOffset + maxResults) {
                  // remove the head, which is actually the highest result
                  filterResults.remove();
               }
            }
         } finally {
            try {
               iterable.close();
            } catch (Exception e) {
               // exception ignored
            }
         }

         // collect and reverse
         if (filterResults.size() > startOffset) {
            Object[] res = new Object[filterResults.size() - startOffset];
            int i = filterResults.size();
            while (i-- > startOffset) {
               ObjectFilter.FilterResult r = filterResults.remove();
               res[i - startOffset] = projection != null ? r.getProjection() : r.getInstance();
            }
            results = Arrays.asList(res);
         } else {
            results = Collections.emptyList();
         }
      }

      return results;
   }

   @Override
   public int getResultSize() {
      list();
      return resultSize;
   }

   @Override
   public String toString() {
      return "EmbeddedQuery{" +
            "jpaQuery=" + jpaQuery +
            ", projection=" + Arrays.toString(projection) +
            ", startOffset=" + startOffset +
            ", maxResults=" + maxResults +
            '}';
   }

   private static class ReverseFilterResultComparator implements Comparator<ObjectFilter.FilterResult> {

      private final Comparator<Comparable[]> comparator;

      private ReverseFilterResultComparator(Comparator<Comparable[]> comparator) {
         this.comparator = comparator;
      }

      @Override
      public int compare(ObjectFilter.FilterResult o1, ObjectFilter.FilterResult o2) {
         return -comparator.compare(o1.getSortProjection(), o2.getSortProjection());
      }
   }
}


File: query/src/main/java/org/infinispan/query/dsl/embedded/impl/QueryEngine.java
package org.infinispan.query.dsl.embedded.impl;

import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.BooleanQuery;
import org.hibernate.hql.ParsingException;
import org.hibernate.hql.QueryParser;
import org.hibernate.hql.ast.spi.EntityNamesResolver;
import org.hibernate.hql.lucene.LuceneProcessingChain;
import org.hibernate.hql.lucene.LuceneQueryParsingResult;
import org.hibernate.hql.lucene.internal.builder.ClassBasedLucenePropertyHelper;
import org.hibernate.hql.lucene.spi.FieldBridgeProvider;
import org.hibernate.search.bridge.FieldBridge;
import org.hibernate.search.spi.SearchIntegrator;
import org.infinispan.AdvancedCache;
import org.infinispan.commons.util.Util;
import org.infinispan.objectfilter.Matcher;
import org.infinispan.objectfilter.impl.ReflectionMatcher;
import org.infinispan.query.CacheQuery;
import org.infinispan.query.SearchManager;
import org.infinispan.query.dsl.Query;
import org.infinispan.query.dsl.QueryFactory;
import org.infinispan.query.dsl.embedded.LuceneQuery;
import org.infinispan.query.impl.ComponentRegistryUtils;
import org.infinispan.util.KeyValuePair;

import java.security.PrivilegedAction;
import java.util.Arrays;

/**
 * @author anistor@redhat.com
 * @since 7.2
 */
public class QueryEngine {

   private final AdvancedCache<?, ?> cache;

   /**
    * Optional cache for query objects.
    */
   private final QueryCache queryCache;

   private final SearchManager searchManager;

   private final SearchIntegrator searchFactory;

   private final QueryParser queryParser = new QueryParser();

   private final EntityNamesResolver entityNamesResolver = new EntityNamesResolver() {
      @Override
      public Class<?> getClassFromName(String entityName) {
         try {
            return Util.loadClassStrict(entityName, null);
         } catch (ClassNotFoundException e) {
            return null;
         }
      }
   };

   public QueryEngine(AdvancedCache<?, ?> cache, SearchManager searchManager) {
      this.cache = cache;
      this.queryCache = ComponentRegistryUtils.getQueryCache(cache);
      this.searchManager = searchManager;
      searchFactory = searchManager != null ? searchManager.unwrap(SearchIntegrator.class) : null;
   }

   public Query buildQuery(QueryFactory queryFactory, String jpqlString, long startOffset, int maxResults) {
      if (searchManager != null) {
         try {
            return buildLuceneQuery(queryFactory, jpqlString, startOffset, maxResults, null);
         } catch (ParsingException e) {
            // if the exception was due a non-indexed field we will try to execute it again with the non-indexed engine
            if (!e.getMessage().startsWith("HQL100002")) {
               throw e;
            }
         } catch (IllegalArgumentException e) {
            // if the exception was due a non-indexed entity we will try to execute it again with the non-indexed engine
            if (!e.getMessage().startsWith("HQL100001")) {
               throw e;
            }
         }
      }

      return new EmbeddedQuery(queryFactory, cache, makeFilter(cache, jpqlString, ReflectionMatcher.class), startOffset, maxResults);
   }

   private JPAFilterAndConverter makeFilter(final AdvancedCache<?, ?> cache, final String jpaQuery, final Class<? extends Matcher> matcherImplClass) {
      return SecurityActions.doPrivileged(new PrivilegedAction<JPAFilterAndConverter>() {
         @Override
         public JPAFilterAndConverter run() {
            JPAFilterAndConverter filter = new JPAFilterAndConverter(jpaQuery, matcherImplClass);
            filter.injectDependencies(cache);

            // force early validation!
            filter.getObjectFilter();
            return filter;
         }
      });
   }

   public LuceneQuery buildLuceneQuery(QueryFactory queryFactory, String jpqlString, long startOffset, int maxResults, org.apache.lucene.search.Query additionalLuceneQuery) {
      if (searchManager == null) {
         throw new IllegalStateException("Cannot run Lucene queries on a cache that does not have indexing enabled");
      }
      LuceneQueryParsingResult parsingResult;
      if (queryCache != null) {
         KeyValuePair<String, Class> queryCacheKey = new KeyValuePair<String, Class>(jpqlString, LuceneQueryParsingResult.class);
         parsingResult = queryCache.get(queryCacheKey);
         if (parsingResult == null) {
            parsingResult = transformJpaToLucene(jpqlString);
            queryCache.put(queryCacheKey, parsingResult);
         }
      } else {
         parsingResult = transformJpaToLucene(jpqlString);
      }

      org.apache.lucene.search.Query luceneQuery = parsingResult.getQuery();
      if (additionalLuceneQuery != null) {
         BooleanQuery booleanQuery = new BooleanQuery();
         booleanQuery.add(new BooleanClause(additionalLuceneQuery, BooleanClause.Occur.MUST));
         booleanQuery.add(new BooleanClause(luceneQuery, BooleanClause.Occur.MUST));
         luceneQuery = booleanQuery;
      }

      CacheQuery cacheQuery = searchManager.getQuery(luceneQuery, parsingResult.getTargetEntity());

      if (parsingResult.getSort() != null) {
         cacheQuery = cacheQuery.sort(parsingResult.getSort());
      }
      if (parsingResult.getProjections() != null && !parsingResult.getProjections().isEmpty()) {
         int projSize = parsingResult.getProjections().size();
         cacheQuery = cacheQuery.projection(parsingResult.getProjections().toArray(new String[projSize]));
      }
      if (startOffset >= 0) {
         cacheQuery = cacheQuery.firstResult((int) startOffset);
      }
      if (maxResults >= 0) {
         cacheQuery = cacheQuery.maxResults(maxResults);
      }

      return new EmbeddedLuceneQuery(queryFactory, jpqlString, cacheQuery);
   }

   private LuceneQueryParsingResult transformJpaToLucene(String jpqlString) {
      FieldBridgeProvider fieldBridgeProvider = new FieldBridgeProvider() {

         private final ClassBasedLucenePropertyHelper propertyHelper = new ClassBasedLucenePropertyHelper(searchFactory, entityNamesResolver);

         @Override
         public FieldBridge getFieldBridge(String type, String propertyPath) {
            return propertyHelper.getFieldBridge(type, Arrays.asList(propertyPath.split("[.]")));
         }
      };
      LuceneProcessingChain processingChain = new LuceneProcessingChain.Builder(searchFactory, entityNamesResolver)
            .buildProcessingChainForClassBasedEntities(fieldBridgeProvider);
      return queryParser.parseQuery(jpqlString, processingChain);
   }
}


File: query/src/test/java/org/infinispan/query/dsl/embedded/QueryDslConditionsTest.java
package org.infinispan.query.dsl.embedded;

import static org.junit.Assert.*;
import static org.testng.Assert.assertNotEquals;

import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.HashSet;
import java.util.List;

import org.hibernate.hql.ParsingException;
import org.hibernate.search.spi.SearchIntegrator;
import org.infinispan.Cache;
import org.infinispan.query.Search;
import org.infinispan.query.dsl.FilterConditionEndContext;
import org.infinispan.query.dsl.Query;
import org.infinispan.query.dsl.QueryBuilder;
import org.infinispan.query.dsl.QueryFactory;
import org.infinispan.query.dsl.SortOrder;
import org.infinispan.query.dsl.embedded.impl.EmbeddedQueryFactory;
import org.infinispan.query.dsl.embedded.testdomain.Account;
import org.infinispan.query.dsl.embedded.testdomain.Address;
import org.infinispan.query.dsl.embedded.testdomain.NotIndexed;
import org.infinispan.query.dsl.embedded.testdomain.Transaction;
import org.infinispan.query.dsl.embedded.testdomain.User;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

/**
 * Test for query conditions (filtering). Exercises the whole query DSL on the sample domain model.
 *
 * @author anistor@redhat.com
 * @author rvansa@redhat.com
 * @since 6.0
 */
@Test(groups = {"functional", "smoke"}, testName = "query.dsl.QueryDslConditionsTest")
public class QueryDslConditionsTest extends AbstractQueryDslTest {

   @BeforeClass(alwaysRun = true)
   protected void populateCache() throws Exception {
      // create the test objects
      User user1 = getModelFactory().makeUser();
      user1.setId(1);
      user1.setName("John");
      user1.setSurname("Doe");
      user1.setGender(User.Gender.MALE);
      user1.setAge(22);
      user1.setAccountIds(new HashSet<Integer>(Arrays.asList(1, 2)));
      user1.setNotes("Lorem ipsum dolor sit amet");

      Address address1 = getModelFactory().makeAddress();
      address1.setStreet("Main Street");
      address1.setPostCode("X1234");
      user1.setAddresses(Collections.singletonList(address1));

      User user2 = getModelFactory().makeUser();
      user2.setId(2);
      user2.setName("Spider");
      user2.setSurname("Man");
      user2.setGender(User.Gender.MALE);
      user2.setAccountIds(Collections.singleton(3));

      Address address2 = getModelFactory().makeAddress();
      address2.setStreet("Old Street");
      address2.setPostCode("Y12");
      Address address3 = getModelFactory().makeAddress();
      address3.setStreet("Bond Street");
      address3.setPostCode("ZZ");
      user2.setAddresses(Arrays.asList(address2, address3));

      User user3 = getModelFactory().makeUser();
      user3.setId(3);
      user3.setName("Spider");
      user3.setSurname("Woman");
      user3.setGender(User.Gender.FEMALE);
      user3.setAccountIds(Collections.<Integer>emptySet());

      Account account1 = getModelFactory().makeAccount();
      account1.setId(1);
      account1.setDescription("John Doe's first bank account");
      account1.setCreationDate(makeDate("2013-01-03"));

      Account account2 = getModelFactory().makeAccount();
      account2.setId(2);
      account2.setDescription("John Doe's second bank account");
      account2.setCreationDate(makeDate("2013-01-04"));

      Account account3 = getModelFactory().makeAccount();
      account3.setId(3);
      account3.setCreationDate(makeDate("2013-01-20"));

      Transaction transaction0 = getModelFactory().makeTransaction();
      transaction0.setId(0);
      transaction0.setDescription("Birthday present");
      transaction0.setAccountId(1);
      transaction0.setAmount(1800);
      transaction0.setDate(makeDate("2012-09-07"));
      transaction0.setDebit(false);

      Transaction transaction1 = getModelFactory().makeTransaction();
      transaction1.setId(1);
      transaction1.setDescription("Feb. rent payment");
      transaction1.setAccountId(1);
      transaction1.setAmount(1500);
      transaction1.setDate(makeDate("2013-01-05"));
      transaction1.setDebit(true);

      Transaction transaction2 = getModelFactory().makeTransaction();
      transaction2.setId(2);
      transaction2.setDescription("Starbucks");
      transaction2.setAccountId(1);
      transaction2.setAmount(23);
      transaction2.setDate(makeDate("2013-01-09"));
      transaction2.setDebit(true);

      Transaction transaction3 = getModelFactory().makeTransaction();
      transaction3.setId(3);
      transaction3.setDescription("Hotel");
      transaction3.setAccountId(2);
      transaction3.setAmount(45);
      transaction3.setDate(makeDate("2013-02-27"));
      transaction3.setDebit(true);

      Transaction transaction4 = getModelFactory().makeTransaction();
      transaction4.setId(4);
      transaction4.setDescription("Last january");
      transaction4.setAccountId(2);
      transaction4.setAmount(95);
      transaction4.setDate(makeDate("2013-01-31"));
      transaction4.setDebit(true);

      Transaction transaction5 = getModelFactory().makeTransaction();
      transaction5.setId(5);
      transaction5.setDescription("Popcorn");
      transaction5.setAccountId(2);
      transaction5.setAmount(5);
      transaction5.setDate(makeDate("2013-01-01"));
      transaction5.setDebit(true);

      // persist and index the test objects
      // we put all of them in the same cache for the sake of simplicity
      getCacheForWrite().put("user_" + user1.getId(), user1);
      getCacheForWrite().put("user_" + user2.getId(), user2);
      getCacheForWrite().put("user_" + user3.getId(), user3);
      getCacheForWrite().put("account_" + account1.getId(), account1);
      getCacheForWrite().put("account_" + account2.getId(), account2);
      getCacheForWrite().put("account_" + account3.getId(), account3);
      getCacheForWrite().put("transaction_" + transaction0.getId(), transaction0);
      getCacheForWrite().put("transaction_" + transaction1.getId(), transaction1);
      getCacheForWrite().put("transaction_" + transaction2.getId(), transaction2);
      getCacheForWrite().put("transaction_" + transaction3.getId(), transaction3);
      getCacheForWrite().put("transaction_" + transaction4.getId(), transaction4);
      getCacheForWrite().put("transaction_" + transaction5.getId(), transaction5);

      for (int i = 0; i < 50; i++) {
         Transaction transaction = getModelFactory().makeTransaction();
         transaction.setId(50 + i);
         transaction.setDescription("Expensive shoes " + i);
         transaction.setAccountId(2);
         transaction.setAmount(100 + i);
         transaction.setDate(makeDate("2013-08-20"));
         transaction.setDebit(true);
         getCacheForWrite().put("transaction_" + transaction.getId(), transaction);
      }

      // this value should be ignored gracefully
      getCacheForWrite().put("dummy", "a primitive value cannot be queried");

      getCacheForWrite().put("notIndexed1", new NotIndexed("testing 123"));
      getCacheForWrite().put("notIndexed2", new NotIndexed("xyz"));
   }

   public void testIndexPresence() {
      SearchIntegrator searchIntegrator = Search.getSearchManager((Cache) getCacheForQuery()).unwrap(SearchIntegrator.class);

      assertTrue(searchIntegrator.getIndexedTypes().contains(getModelFactory().getUserImplClass()));
      assertNotNull(searchIntegrator.getIndexManager(getModelFactory().getUserImplClass().getName()));

      assertTrue(searchIntegrator.getIndexedTypes().contains(getModelFactory().getAccountImplClass()));
      assertNotNull(searchIntegrator.getIndexManager(getModelFactory().getAccountImplClass().getName()));

      assertTrue(searchIntegrator.getIndexedTypes().contains(getModelFactory().getTransactionImplClass()));
      assertNotNull(searchIntegrator.getIndexManager(getModelFactory().getTransactionImplClass().getName()));

      assertFalse(searchIntegrator.getIndexedTypes().contains(getModelFactory().getAddressImplClass()));
      assertNull(searchIntegrator.getIndexManager(getModelFactory().getAddressImplClass().getName()));
   }

   public void testQueryFactoryType() {
      assertEquals(EmbeddedQueryFactory.class, getQueryFactory().getClass());
   }

   public void testEq1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("John")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Doe", list.get(0).getSurname());
   }

   public void testEqEmptyString() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("")
            .toBuilder().build();

      List<User> list = q.list();
      assertTrue(list.isEmpty());
   }

   public void testEqSentence() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .having("description").eq("John Doe's first bank account")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
   }

   public void testEq() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("Jacob")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   public void testEqNonIndexedType() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(NotIndexed.class)
            .having("notIndexedField").eq("testing 123")
            .toBuilder().build();

      List<NotIndexed> list = q.list();
      assertEquals(1, list.size());
      assertEquals("testing 123", list.get(0).notIndexedField);
   }

   public void testEqNonIndexedField() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("notes").eq("Lorem ipsum dolor sit amet")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   public void testEqInNested1() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all users in a given post code
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("addresses.postCode").eq("X1234")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("X1234", list.get(0).getAddresses().get(0).getPostCode());
   }

   public void testEqInNested2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("addresses.postCode").eq("Y12")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(2, list.get(0).getAddresses().size());
   }

   public void testLike() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all rent payments made from a given account
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("description").like("%rent%")
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getAccountId());
      assertEquals(1500, list.get(0).getAmount(), 0);
   }

   public void testBetween1() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31"))
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(4, list.size());
      for (Transaction t : list) {
         assertTrue(t.getDate().compareTo(makeDate("2013-01-31")) <= 0);
         assertTrue(t.getDate().compareTo(makeDate("2013-01-01")) >= 0);
      }
   }

   public void testBetween2() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31")).includeUpper(false)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(3, list.size());
      for (Transaction t : list) {
         assertTrue(t.getDate().compareTo(makeDate("2013-01-31")) < 0);
         assertTrue(t.getDate().compareTo(makeDate("2013-01-01")) >= 0);
      }
   }

   public void testBetween3() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31")).includeLower(false)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(3, list.size());
      for (Transaction t : list) {
         assertTrue(t.getDate().compareTo(makeDate("2013-01-31")) <= 0);
         assertTrue(t.getDate().compareTo(makeDate("2013-01-01")) > 0);
      }
   }

   public void testGt() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions greater than a given amount
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("amount").gt(1500)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(1, list.size());
      assertTrue(list.get(0).getAmount() > 1500);
   }

   public void testGte() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("amount").gte(1500)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(2, list.size());
      for (Transaction t : list) {
         assertTrue(t.getAmount() >= 1500);
      }
   }

   public void testLt() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("amount").lt(1500)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(54, list.size());
      for (Transaction t : list) {
         assertTrue(t.getAmount() < 1500);
      }
   }

   public void testLte() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("amount").lte(1500)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(55, list.size());
      for (Transaction t : list) {
         assertTrue(t.getAmount() <= 1500);
      }
   }

   public void testAnd1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("Spider")
            .and().having("surname").eq("Man")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(2, list.get(0).getId());
   }

   public void testAnd2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("Spider")
            .and(qf.having("surname").eq("Man"))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(2, list.get(0).getId());
   }

   public void testAnd3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(User.Gender.MALE)
            .and().having("gender").eq(User.Gender.FEMALE)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   public void testAnd4() throws Exception {
      QueryFactory qf = getQueryFactory();

      //test for parenthesis, "and" should have higher priority
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("Spider")
            .or(qf.having("name").eq("John"))
            .and(qf.having("surname").eq("Man"))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
   }

   public void testOr1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("surname").eq("Man")
            .or().having("surname").eq("Woman")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      for (User u : list) {
         assertEquals("Spider", u.getName());
      }
   }

   public void testOr2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("surname").eq("Man")
            .or(qf.having("surname").eq("Woman"))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      for (User u : list) {
         assertEquals("Spider", u.getName());
      }
   }

   public void testOr3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(User.Gender.MALE)
            .or().having("gender").eq(User.Gender.FEMALE)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(3, list.size());
   }

   public void testOr4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("surname", SortOrder.DESC)
            .having("gender").eq(User.Gender.MALE)
            .or().having("name").eq("Spider")
            .and().having("gender").eq(User.Gender.FEMALE)
            .or().having("surname").like("%oe%")
            .toBuilder().build();
      List<User> list = q.list();

      assertEquals(2, list.size());
      assertEquals("Woman", list.get(0).getSurname());
      assertEquals("Doe", list.get(1).getSurname());
   }

   public void testOr5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(User.Gender.MALE)
            .or().having("name").eq("Spider")
            .or().having("gender").eq(User.Gender.FEMALE)
            .and().having("surname").like("%oe%")
            .toBuilder().build();
      List<User> list = q.list();

      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
   }

   public void testNot1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("name").eq("Spider")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
   }

   public void testNot2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().not().having("surname").eq("Doe")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
   }

   public void testNot3() throws Exception {
      QueryFactory qf = getQueryFactory();

      // NOT should have higher priority than AND
      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("name").eq("John")
            .and().having("surname").eq("Man")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("Spider", list.get(0).getName());
   }

   public void testNot4() throws Exception {
      QueryFactory qf = getQueryFactory();

      // NOT should have higher priority than AND
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("surname").eq("Man")
            .and().not().having("name").eq("John")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("Spider", list.get(0).getName());
   }

   public void testNot5() throws Exception {
      QueryFactory qf = getQueryFactory();

      // NOT should have higher priority than OR
      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("name").eq("Spider")
            .or().having("surname").eq("Man")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      for (User u : list) {
         assertFalse("Woman".equals(u.getSurname()));
      }
   }

   public void testNot6() throws Exception {
      QueryFactory qf = getQueryFactory();

      // QueryFactory.not() test
      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(qf.not(qf.having("gender").eq(User.Gender.FEMALE)))
            .toBuilder()
            .build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertTrue(list.get(0).getSurname().equals("Woman"));
   }

   public void testNot7() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(User.Gender.FEMALE)
            .and().not(qf.having("name").eq("Spider"))
            .toBuilder().build();

      List<User> list = q.list();
      assertTrue(list.isEmpty());
   }

   public void testNot8() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(
                  qf.having("name").eq("John")
                        .or(qf.having("surname").eq("Man")))
            .toBuilder()
            .build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("Spider", list.get(0).getName());
      assertEquals("Woman", list.get(0).getSurname());
   }

   public void testNot9() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(
                  qf.having("name").eq("John")
                        .and(qf.having("surname").eq("Doe")))
            .toBuilder()
            .orderBy("id", SortOrder.ASC)
            .build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals("Spider", list.get(0).getName());
      assertEquals("Man", list.get(0).getSurname());
      assertEquals("Spider", list.get(1).getName());
      assertEquals("Woman", list.get(1).getSurname());
   }

   public void testNot10() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().not(
                  qf.having("name").eq("John")
                        .or(qf.having("surname").eq("Man")))
            .toBuilder()
            .build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertNotEquals("Woman", list.get(0).getSurname());
   }

   public void testNot11() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(qf.not(
                  qf.having("name").eq("John")
                        .or(qf.having("surname").eq("Man"))))
            .toBuilder()
            .build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertNotEquals("Woman", list.get(0).getSurname());
   }

   public void testEmptyQuery() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass()).build();

      List<User> list = q.list();
      assertEquals(3, list.size());
   }

   @Test(expectedExceptions = ParsingException.class, expectedExceptionsMessageRegExp = "HQL100005:.*")
   public void testInvalidEmbeddedAttributeQuery() throws Exception {
      QueryFactory qf = getQueryFactory();

      QueryBuilder queryBuilder = qf.from(getModelFactory().getUserImplClass())
            .setProjection("addresses");

      queryBuilder.build();  // exception expected
   }

   public void testIsNull() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("addresses").isNull()
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(3, list.get(0).getId());
   }

   public void testContains1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").contains(2)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   public void testContains2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").contains(42)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   public void testContainsAll1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(1, 2)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   public void testContainsAll2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(Collections.singleton(1))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   public void testContainsAll3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(1, 2, 3)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   public void testContainsAll4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(Collections.emptySet())
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(3, list.size());
   }

   public void testContainsAny1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .having("accountIds").containsAny(2, 3)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals(1, list.get(0).getId());
      assertEquals(2, list.get(1).getId());
   }

   public void testContainsAny2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAny(4, 5)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   public void testContainsAny3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAny(Collections.emptySet())
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(3, list.size());
   }

   public void testIn1() throws Exception {
      QueryFactory qf = getQueryFactory();

      List<Integer> ids = Arrays.asList(1, 3);
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("id").in(ids)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      for (User u : list) {
         assertTrue(ids.contains(u.getId()));
      }
   }

   public void testIn2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("id").in(4)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(0, list.size());
   }

   @Test(expectedExceptions = IllegalArgumentException.class)
   public void testIn3() throws Exception {
      QueryFactory qf = getQueryFactory();

      qf.from(getModelFactory().getUserImplClass()).having("id").in(Collections.emptySet());
   }

   @Test(expectedExceptions = IllegalArgumentException.class)
   public void testIn4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Collection collection = null;
      qf.from(getModelFactory().getUserImplClass()).having("id").in(collection);
   }

   @Test(expectedExceptions = IllegalArgumentException.class)
   public void testIn5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Object[] array = null;
      qf.from(getModelFactory().getUserImplClass()).having("id").in(array);
   }

   @Test(expectedExceptions = IllegalArgumentException.class)
   public void testIn6() throws Exception {
      QueryFactory qf = getQueryFactory();

      Object[] array = new Object[0];
      qf.from(getModelFactory().getUserImplClass()).having("id").in(array);
   }

   public void testSampleDomainQuery1() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all male users
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.ASC)
            .having("gender").eq(User.Gender.MALE)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
   }

   public void testSampleDomainQuery2() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all male users, but this time retrieved in a twisted manner
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.ASC)
            .not(qf.having("gender").eq(User.Gender.FEMALE))
            .and(qf.not().not(qf.having("gender").eq(User.Gender.MALE)))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
   }

   public void testStringLiteralEscape() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all transactions that have a given description. the description contains characters that need to be escaped.
      Query q = qf.from(getModelFactory().getAccountImplClass())
            .having("description").eq("John Doe's first bank account")
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
   }

   public void testSortByDate() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .orderBy("creationDate", SortOrder.DESC)
            .build();

      List<Account> list = q.list();
      assertEquals(3, list.size());
      assertEquals(3, list.get(0).getId());
      assertEquals(2, list.get(1).getId());
      assertEquals(1, list.get(2).getId());
   }

   public void testSampleDomainQuery3() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all male users
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.ASC)
            .having("gender").eq(User.Gender.MALE)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
   }

   public void testSampleDomainQuery4() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all users ordered descendingly by name
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.DESC)
            .build();

      List<User> list = q.list();
      assertEquals(3, list.size());
      assertEquals("Spider", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
      assertEquals("John", list.get(2).getName());
   }

   public void testSampleDomainQuery4With2SortingOptions() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all users ordered descendingly by name
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.DESC)
            .orderBy("surname", SortOrder.ASC)
            .build();

      List<User> list = q.list();
      assertEquals(3, list.size());

      assertEquals("Spider", list.get(0).getName());
      assertEquals("Spider", list.get(1).getName());
      assertEquals("John", list.get(2).getName());

      assertEquals("Man", list.get(0).getSurname());
      assertEquals("Woman", list.get(1).getSurname());
      assertEquals("Doe", list.get(2).getSurname());
   }

   public void testSampleDomainQuery5() throws Exception {
      QueryFactory qf = getQueryFactory();

      // name projection of all users ordered descendingly by name
      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("name", SortOrder.DESC)
            .setProjection("name")
            .build();

      List<Object[]> list = q.list();
      assertEquals(3, list.size());
      assertEquals(1, list.get(0).length);
      assertEquals(1, list.get(1).length);
      assertEquals(1, list.get(2).length);
      assertEquals("Spider", list.get(0)[0]);
      assertEquals("Spider", list.get(1)[0]);
      assertEquals("John", list.get(2)[0]);
   }

   public void testSampleDomainQuery6() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all users with a given name and surname
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("John")
            .and().having("surname").eq("Doe")
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("John", list.get(0).getName());
      assertEquals("Doe", list.get(0).getSurname());
   }

   public void testSampleDomainQuery7() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all rent payments made from a given account
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("accountId").eq(1)
            .and().having("description").like("%rent%")
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
      assertEquals(1, list.get(0).getAccountId());
      assertTrue(list.get(0).getDescription().contains("rent"));
   }

   public void testSampleDomainQuery8() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31"))
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(4, list.size());
      for (Transaction t : list) {
         assertTrue(t.getDate().compareTo(makeDate("2013-01-31")) <= 0);
         assertTrue(t.getDate().compareTo(makeDate("2013-01-01")) >= 0);
      }
   }

   public void testSampleDomainQuery9() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that happened in January 2013, projected by date field only
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .setProjection("date")
            .having("date").between(makeDate("2013-01-01"), makeDate("2013-01-31"))
            .toBuilder().build();

      List<Object[]> list = q.list();
      assertEquals(4, list.size());
      assertEquals(1, list.get(0).length);
      assertEquals(1, list.get(1).length);
      assertEquals(1, list.get(2).length);
      assertEquals(1, list.get(3).length);

      for (int i = 0; i < 4; i++) {
         Date d = (Date) list.get(i)[0];
         assertTrue(d.compareTo(makeDate("2013-01-31")) <= 0);
         assertTrue(d.compareTo(makeDate("2013-01-01")) >= 0);
      }
   }

   public void testSampleDomainQuery10() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions for a an account having amount greater than a given amount
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("accountId").eq(2)
            .and().having("amount").gt(40)
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(52, list.size());
      assertTrue(list.get(0).getAmount() > 40);
      assertTrue(list.get(1).getAmount() > 40);
   }

   public void testSampleDomainQuery11() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("John")
            .and().having("addresses.postCode").eq("X1234")
            .and(qf.having("accountIds").eq(1))
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals("Doe", list.get(0).getSurname());
   }

   public void testSampleDomainQuery12() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all the transactions that represents credits to the account
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .having("accountId").eq(1)
            .and()
            .not().having("isDebit").eq(true).toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(1, list.size());
      assertFalse(list.get(0).isDebit());
   }

   public void testSampleDomainQuery13() throws Exception {
      QueryFactory qf = getQueryFactory();

      // the user that has the bank account with id 3
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").contains(3).toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(2, list.get(0).getId());
      assertTrue(list.get(0).getAccountIds().contains(3));
   }

   public void testSampleDomainQuery14() throws Exception {
      QueryFactory qf = getQueryFactory();

      // the user that has all the specified bank accounts
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAll(2, 1).toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(1, list.get(0).getId());
      assertTrue(list.get(0).getAccountIds().contains(1));
      assertTrue(list.get(0).getAccountIds().contains(2));
   }

   public void testSampleDomainQuery15() throws Exception {
      QueryFactory qf = getQueryFactory();

      // the user that has at least one of the specified accounts
      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("accountIds").containsAny(1, 3).toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(1, 2).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(1, 2).contains(list.get(1).getId()));
   }

   public void testSampleDomainQuery16() throws Exception {
      QueryFactory qf = getQueryFactory();

      // third batch of 10 transactions for a given account
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .startOffset(20).maxResults(10)
            .orderBy("id", SortOrder.ASC)
            .having("accountId").eq(2).and().having("description").like("Expensive%")
            .toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(50, q.getResultSize());
      assertEquals(10, list.size());
      for (int i = 0; i < 10; i++) {
         assertEquals("Expensive shoes " + (20 + i), list.get(i).getDescription());
      }
   }

   public void testSampleDomainQuery17() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all accounts for a user. first get the user by id and then get his account.
      Query q1 = qf.from(getModelFactory().getUserImplClass())
            .having("id").eq(1).toBuilder().build();

      List<User> users = q1.list();
      Query q2 = qf.from(getModelFactory().getAccountImplClass())
            .orderBy("description", SortOrder.ASC)
            .having("id").in(users.get(0).getAccountIds()).toBuilder().build();

      List<Account> list = q2.list();
      assertEquals(2, list.size());
      assertEquals("John Doe's first bank account", list.get(0).getDescription());
      assertEquals("John Doe's second bank account", list.get(1).getDescription());
   }

   public void testSampleDomainQuery18() throws Exception {
      QueryFactory qf = getQueryFactory();

      // all transactions of account with id 2 which have an amount larger than 1600 or their description contains the word 'rent'
      Query q = qf.from(getModelFactory().getTransactionImplClass())
            .orderBy("description", SortOrder.ASC)
            .having("accountId").eq(1)
            .and(qf.having("amount").gt(1600)
                       .or().having("description").like("%rent%")).toBuilder().build();

      List<Transaction> list = q.list();
      assertEquals(2, list.size());
      assertEquals("Birthday present", list.get(0).getDescription());
      assertEquals("Feb. rent payment", list.get(1).getDescription());
   }

   public void testProjectionOnOptionalField() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .setProjection("id", "addresses.postCode")
            .orderBy("id", SortOrder.ASC)
            .build();

      List<Object[]> list = q.list();
      assertEquals(3, list.size());
      assertEquals(1, list.get(0)[0]);
      assertEquals(2, list.get(1)[0]);
      assertEquals(3, list.get(2)[0]);
      assertEquals("X1234", list.get(0)[1]);
      assertEquals("Y12", list.get(1)[1]);
      assertNull(list.get(2)[1]);
   }

   //todo [anistor] fix disabled test
   @Test(enabled = false, description = "Nulls not correctly indexed for numeric properties, see ISPN-4046")
   public void testNullOnIntegerField() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("age").isNull()
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
   }

   public void testSampleDomainQuery19() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("addresses.postCode").in("ZZ", "X1234").toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(1, 2).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(1, 2).contains(list.get(1).getId()));
   }

   public void testSampleDomainQuery20() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("addresses.postCode").in("X1234").toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(2, 3).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(2, 3).contains(list.get(1).getId()));
   }

   public void testSampleDomainQuery21() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("addresses").isNull().toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(1, 2).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(1, 2).contains(list.get(1).getId()));
   }

   public void testSampleDomainQuery22() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("addresses.postCode").like("%123%").toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(2, 3).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(2, 3).contains(list.get(1).getId()));
   }

   public void testSampleDomainQuery23() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("id").between(1, 2)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(1, list.size());
      assertEquals(3, list.get(0).getId());
   }

   public void testSampleDomainQuery24() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("id").between(1, 2).includeLower(false)
            .toBuilder().build();

      List<User> list = q.list();

      assertEquals(2, list.size());
      assertTrue(Arrays.asList(1, 3).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(1, 3).contains(list.get(1).getId()));
   }

   public void testSampleDomainQuery25() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("id").between(1, 2).includeUpper(false)
            .toBuilder().build();

      List<User> list = q.list();
      assertEquals(2, list.size());
      assertTrue(Arrays.asList(2, 3).contains(list.get(0).getId()));
      assertTrue(Arrays.asList(2, 3).contains(list.get(1).getId()));
   }

   public void testSampleDomainQuery26() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .having("creationDate").eq(makeDate("2013-01-20"))
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(1, list.size());
      assertEquals(3, list.get(0).getId());
   }

   public void testSampleDomainQuery27() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .orderBy("id", SortOrder.ASC)
            .having("creationDate").lt(makeDate("2013-01-20"))
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(2, list.size());
      assertEquals(1, list.get(0).getId());
      assertEquals(2, list.get(1).getId());
   }

   public void testSampleDomainQuery28() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .orderBy("id", SortOrder.ASC)
            .having("creationDate").lte(makeDate("2013-01-20"))
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(3, list.size());
      assertEquals(1, list.get(0).getId());
      assertEquals(2, list.get(1).getId());
      assertEquals(3, list.get(2).getId());
   }

   public void testSampleDomainQuery29() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getAccountImplClass())
            .having("creationDate").gt(makeDate("2013-01-04"))
            .toBuilder().build();

      List<Account> list = q.list();
      assertEquals(1, list.size());
      assertEquals(3, list.get(0).getId());
   }

   @Test(expectedExceptions = IllegalStateException.class)
   public void testWrongQueryBuilding1() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.not().having("name").eq("John").toBuilder().build();
   }

   @Test(expectedExceptions = IllegalStateException.class)
   public void testWrongQueryBuilding2() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("name").eq("John").toBuilder()
            .having("surname").eq("Man").toBuilder()
            .build();
   }

   @Test(expectedExceptions = IllegalStateException.class)
   public void testWrongQueryBuilding3() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not().having("name").eq("John").toBuilder()
            .not().having("surname").eq("Man").toBuilder()
            .build();
   }

   @Test(expectedExceptions = IllegalStateException.class)
   public void testWrongQueryBuilding4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(qf.having("name").eq("John")).toBuilder()
            .not(qf.having("surname").eq("Man")).toBuilder()
            .build();
   }

   @Test(expectedExceptions = IllegalStateException.class)
   public void testWrongQueryBuilding5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .not(qf.having("name").eq("John")).toBuilder()
            .not(qf.having("surname").eq("Man")).toBuilder()
            .build();
   }

   @Test(expectedExceptions = IllegalArgumentException.class)
   public void testWrongQueryBuilding6() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .having("gender").eq(null)
            .toBuilder().build();
   }

   @Test(expectedExceptions = IllegalStateException.class)
   public void testWrongQueryBuilding7() throws Exception {
      QueryFactory qf = getQueryFactory();

      FilterConditionEndContext q1 = qf.from(getModelFactory().getUserImplClass())
            .having("gender");

      q1.eq(User.Gender.MALE);
      q1.eq(User.Gender.FEMALE);
   }

   @Test(expectedExceptions = IllegalArgumentException.class, expectedExceptionsMessageRegExp = "maxResults must be greater than 0")
   public void testPagination1() throws Exception {
      QueryFactory qf = getQueryFactory();

      qf.from(getModelFactory().getUserImplClass())
            .maxResults(0);
   }

   @Test(expectedExceptions = IllegalArgumentException.class, expectedExceptionsMessageRegExp = "maxResults must be greater than 0")
   public void testPagination2() throws Exception {
      QueryFactory qf = getQueryFactory();

      qf.from(getModelFactory().getUserImplClass())
            .maxResults(-4);
   }

   @Test(expectedExceptions = IllegalArgumentException.class, expectedExceptionsMessageRegExp = "startOffset cannot be less than 0")
   public void testPagination3() throws Exception {
      QueryFactory qf = getQueryFactory();

      qf.from(getModelFactory().getUserImplClass())
            .startOffset(-3);
   }

   public void testOrderedPagination4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .maxResults(5)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(3, list.size());
   }

   public void testUnorderedPagination4() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .maxResults(5)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(3, list.size());
   }

   public void testOrderedPagination5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .startOffset(20)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(0, list.size());
   }

   public void testUnorderedPagination5() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .startOffset(20)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(0, list.size());
   }

   public void testOrderedPagination6() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .startOffset(20).maxResults(10)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(0, list.size());
   }

   public void testUnorderedPagination6() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .startOffset(20).maxResults(10)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(0, list.size());
   }

   public void testOrderedPagination7() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .startOffset(1).maxResults(10)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(2, list.size());
   }

   public void testUnorderedPagination7() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .startOffset(1).maxResults(10)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(2, list.size());
   }

   public void testOrderedPagination8() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .orderBy("id", SortOrder.ASC)
            .startOffset(0).maxResults(2)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(2, list.size());
   }

   public void testUnorderedPagination8() throws Exception {
      QueryFactory qf = getQueryFactory();

      Query q = qf.from(getModelFactory().getUserImplClass())
            .startOffset(0).maxResults(2)
            .build();

      List<User> list = q.list();
      assertEquals(3, q.getResultSize());
      assertEquals(2, list.size());
   }
}


File: remote-query/remote-query-server/src/main/java/org/infinispan/query/remote/QueryFacadeImpl.java
package org.infinispan.query.remote;

import org.apache.lucene.index.Term;
import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.TermQuery;
import org.hibernate.hql.ParsingException;
import org.hibernate.hql.QueryParser;
import org.hibernate.hql.ast.spi.EntityNamesResolver;
import org.hibernate.hql.lucene.LuceneProcessingChain;
import org.hibernate.hql.lucene.LuceneQueryParsingResult;
import org.hibernate.hql.lucene.spi.FieldBridgeProvider;
import org.hibernate.search.bridge.FieldBridge;
import org.hibernate.search.bridge.builtin.NumericFieldBridge;
import org.hibernate.search.bridge.builtin.StringBridge;
import org.hibernate.search.bridge.builtin.impl.NullEncodingTwoWayFieldBridge;
import org.hibernate.search.bridge.builtin.impl.TwoWayString2FieldBridgeAdaptor;
import org.hibernate.search.spi.SearchIntegrator;
import org.infinispan.AdvancedCache;
import org.infinispan.commons.logging.LogFactory;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.objectfilter.impl.ProtobufMatcher;
import org.infinispan.protostream.ProtobufUtil;
import org.infinispan.protostream.SerializationContext;
import org.infinispan.protostream.WrappedMessage;
import org.infinispan.protostream.descriptors.Descriptor;
import org.infinispan.protostream.descriptors.FieldDescriptor;
import org.infinispan.query.CacheQuery;
import org.infinispan.query.Search;
import org.infinispan.query.SearchManager;
import org.infinispan.query.dsl.embedded.impl.EmbeddedQuery;
import org.infinispan.query.dsl.embedded.impl.JPAFilterAndConverter;
import org.infinispan.query.dsl.embedded.impl.QueryCache;
import org.infinispan.query.impl.ComponentRegistryUtils;
import org.infinispan.query.remote.client.QueryRequest;
import org.infinispan.query.remote.client.QueryResponse;
import org.infinispan.query.remote.filter.JPAProtobufFilterAndConverter;
import org.infinispan.query.remote.indexing.IndexingMetadata;
import org.infinispan.query.remote.indexing.ProtobufValueWrapper;
import org.infinispan.query.remote.logging.Log;
import org.infinispan.server.core.QueryFacade;
import org.infinispan.util.KeyValuePair;
import org.kohsuke.MetaInfServices;

import java.io.IOException;
import java.security.PrivilegedAction;
import java.util.ArrayList;
import java.util.List;

/**
 * A query facade implementation for both Lucene based queries and non-indexed queries.
 *
 * @author anistor@redhat.com
 * @since 6.0
 */
@MetaInfServices
public final class QueryFacadeImpl implements QueryFacade {

   private static final Log log = LogFactory.getLog(QueryFacadeImpl.class, Log.class);

   /**
    * A special hidden Lucene document field that holds the actual protobuf type name.
    */
   public static final String TYPE_FIELD_NAME = "$type$";

   /**
    * A special placeholder value that is indexed if the actual field value is null. This placeholder is needed because
    * Lucene does not index null values.
    */
   public static final String NULL_TOKEN = "_null_";

   private final QueryParser queryParser = new QueryParser();

   @Override
   public byte[] query(AdvancedCache<byte[], byte[]> cache, byte[] query) {
      try {
         SerializationContext serCtx = ProtobufMetadataManager.getSerializationContextInternal(cache.getCacheManager());
         QueryRequest request = ProtobufUtil.fromByteArray(serCtx, query, 0, query.length, QueryRequest.class);

         Configuration cacheConfiguration = SecurityActions.getCacheConfiguration(cache);
         QueryResponse response;
         if (cacheConfiguration.indexing().index().isEnabled()) {
            try {
               response = executeIndexedQuery(cache, cacheConfiguration, serCtx, request);
            } catch (IllegalArgumentException e) {
               if (e.getMessage().contains("ISPN018002:") || e.getMessage().contains("HQL100001:")) {
                  response = executeNonIndexedQuery(cache, cacheConfiguration, serCtx, request);
               } else {
                  throw e;
               }
            } catch (ParsingException e) {
               if (e.getMessage().contains("HQL100002:")) {
                  response = executeNonIndexedQuery(cache, cacheConfiguration, serCtx, request);
               } else {
                  throw e;
               }
            }
         } else {
            response = executeNonIndexedQuery(cache, cacheConfiguration, serCtx, request);
         }

         return ProtobufUtil.toByteArray(serCtx, response);
      } catch (IOException e) {
         throw log.errorExecutingQuery(e);
      }
   }

   private QueryResponse executeNonIndexedQuery(AdvancedCache<byte[], byte[]> cache, Configuration cacheConfiguration, SerializationContext serCtx, QueryRequest request) throws IOException {
      final boolean isIndexed = cacheConfiguration.indexing().index().isEnabled();
      final boolean isCompatMode = cacheConfiguration.compatibility().enabled();

      EmbeddedQuery eq = new EmbeddedQuery(null, cache, makeFilter(cache, isIndexed, isCompatMode, request.getJpqlString()), request.getStartOffset(), request.getMaxResults());
      List<?> list = eq.list();

      int projSize = eq.getProjection() != null && eq.getProjection().length > 0 ? eq.getProjection().length : 0;

      return makeResponse(isCompatMode, serCtx, list, projSize, eq.getResultSize(), list.size());
   }

   private JPAFilterAndConverter makeFilter(final AdvancedCache<?, ?> cache, final boolean isIndexed, final boolean isCompatMode, final String jpaQuery) {
      return SecurityActions.doPrivileged(new PrivilegedAction<JPAFilterAndConverter>() {
         @Override
         public JPAFilterAndConverter run() {
            JPAFilterAndConverter filter = isIndexed && !isCompatMode ? new JPAProtobufFilterAndConverter(jpaQuery) :
                  new JPAFilterAndConverter(jpaQuery, isCompatMode ? CompatibilityReflectionMatcher.class : ProtobufMatcher.class);
            filter.injectDependencies(cache);

            // force early validation!
            filter.getObjectFilter();
            return filter;
         }
      });
   }

   /**
    * Execute Lucene index query.
    */
   private QueryResponse executeIndexedQuery(AdvancedCache<byte[], byte[]> cache, Configuration cacheConfiguration, SerializationContext serCtx, QueryRequest request) throws IOException {
      final SearchManager searchManager = Search.getSearchManager(cache);
      final SearchIntegrator searchFactory = searchManager.unwrap(SearchIntegrator.class);
      final QueryCache queryCache = ComponentRegistryUtils.getQueryCache(cache);  // optional component

      LuceneQueryParsingResult parsingResult;
      Query luceneQuery;

      if (queryCache != null) {
         KeyValuePair<String, Class> queryCacheKey = new KeyValuePair<String, Class>(request.getJpqlString(), LuceneQueryParsingResult.class);
         parsingResult = queryCache.get(queryCacheKey);
         if (parsingResult == null) {
            parsingResult = parseQuery(cacheConfiguration, serCtx, request.getJpqlString(), searchFactory);
            queryCache.put(queryCacheKey, parsingResult);
         }
      } else {
         parsingResult = parseQuery(cacheConfiguration, serCtx, request.getJpqlString(), searchFactory);
      }

      luceneQuery = parsingResult.getQuery();

      boolean isCompatMode = cacheConfiguration.compatibility().enabled();
      if (!isCompatMode) {
         // restrict on entity type
         BooleanQuery booleanQuery = new BooleanQuery();
         booleanQuery.add(new BooleanClause(new TermQuery(new Term(TYPE_FIELD_NAME, parsingResult.getTargetEntityName())), BooleanClause.Occur.MUST));
         booleanQuery.add(new BooleanClause(luceneQuery, BooleanClause.Occur.MUST));
         luceneQuery = booleanQuery;
      }

      CacheQuery cacheQuery = searchManager.getQuery(luceneQuery, parsingResult.getTargetEntity());

      if (parsingResult.getSort() != null) {
         cacheQuery = cacheQuery.sort(parsingResult.getSort());
      }

      int projSize = 0;
      if (parsingResult.getProjections() != null && !parsingResult.getProjections().isEmpty()) {
         projSize = parsingResult.getProjections().size();
         cacheQuery = cacheQuery.projection(parsingResult.getProjections().toArray(new String[projSize]));
      }
      if (request.getStartOffset() > 0) {
         cacheQuery = cacheQuery.firstResult((int) request.getStartOffset());
      }
      if (request.getMaxResults() > 0) {
         cacheQuery = cacheQuery.maxResults(request.getMaxResults());
      }

      List<?> list = cacheQuery.list();

      return makeResponse(false, serCtx, list, projSize, cacheQuery.getResultSize(), list.size());
   }

   private LuceneQueryParsingResult parseQuery(Configuration cacheConfiguration, final SerializationContext serCtx, String queryString, SearchIntegrator searchFactory) {
      LuceneProcessingChain processingChain;
      if (cacheConfiguration.compatibility().enabled()) {
         EntityNamesResolver entityNamesResolver = new EntityNamesResolver() {
            @Override
            public Class<?> getClassFromName(String entityName) {
               return serCtx.canMarshall(entityName) ? serCtx.getMarshaller(entityName).getJavaClass() : null;
            }
         };

         processingChain = new LuceneProcessingChain.Builder(searchFactory, entityNamesResolver)
               .buildProcessingChainForClassBasedEntities();
      } else {
         EntityNamesResolver entityNamesResolver = new EntityNamesResolver() {
            @Override
            public Class<?> getClassFromName(String entityName) {
               return serCtx.canMarshall(entityName) ? ProtobufValueWrapper.class : null;
            }
         };

         FieldBridgeProvider fieldBridgeProvider = new FieldBridgeProvider() {
            @Override
            public FieldBridge getFieldBridge(String type, String propertyPath) {
               Descriptor md = serCtx.getMessageDescriptor(type);
               FieldDescriptor fd = getFieldDescriptor(md, propertyPath);
               switch (fd.getType()) {
                  case DOUBLE:
                     return NumericFieldBridge.DOUBLE_FIELD_BRIDGE;
                  case FLOAT:
                     return NumericFieldBridge.FLOAT_FIELD_BRIDGE;
                  case INT64:
                  case UINT64:
                  case FIXED64:
                  case SFIXED64:
                  case SINT64:
                     return NumericFieldBridge.LONG_FIELD_BRIDGE;
                  case INT32:
                  case FIXED32:
                  case UINT32:
                  case SFIXED32:
                  case SINT32:
                  case BOOL:
                  case ENUM:
                     return NumericFieldBridge.INT_FIELD_BRIDGE;
                  case STRING:
                  case BYTES:
                  case GROUP:
                  case MESSAGE:
                     return new NullEncodingTwoWayFieldBridge(new TwoWayString2FieldBridgeAdaptor(StringBridge.INSTANCE), NULL_TOKEN);
               }
               return null;
            }
         };

         processingChain = new LuceneProcessingChain.Builder(searchFactory, entityNamesResolver)
               .buildProcessingChainForDynamicEntities(fieldBridgeProvider);
      }

      return queryParser.parseQuery(queryString, processingChain);
   }

   private FieldDescriptor getFieldDescriptor(Descriptor messageDescriptor, String attributePath) {
      FieldDescriptor fd = null;
      String[] split = attributePath.split("[.]");
      for (int i = 0; i < split.length; i++) {
         String name = split[i];
         fd = messageDescriptor.findFieldByName(name);
         if (fd == null) {
            throw log.unknownField(name, messageDescriptor.getFullName());
         }
         IndexingMetadata indexingMetadata = messageDescriptor.getProcessedAnnotation(IndexingMetadata.INDEXED_ANNOTATION);
         if (indexingMetadata != null && !indexingMetadata.isFieldIndexed(fd.getNumber())) {
            throw log.fieldIsNotIndexed(name, messageDescriptor.getFullName());
         }
         if (i < split.length - 1) {
            messageDescriptor = fd.getMessageType();
         }
      }
      return fd;
   }

   private QueryResponse makeResponse(boolean isCompatMode, SerializationContext serCtx, List<?> list, int projSize, long totalResults, int numResults) throws IOException {
      List<WrappedMessage> results = new ArrayList<WrappedMessage>(projSize == 0 ? numResults : numResults * projSize);
      for (Object o : list) {
         if (projSize == 0) {
            if (isCompatMode) {
               // if we are in compat mode then this is the real object so need to marshall it first
               o = ProtobufUtil.toWrappedByteArray(serCtx, o);
            }
            results.add(new WrappedMessage(o));
         } else {
            Object[] row = (Object[]) o;
            for (int j = 0; j < projSize; j++) {
               results.add(new WrappedMessage(row[j]));
            }
         }
      }

      QueryResponse response = new QueryResponse();
      response.setTotalResults(totalResults);
      response.setNumResults(numResults);
      response.setProjectionSize(projSize);
      response.setResults(results);
      return response;
   }
}


File: remote-query/remote-query-server/src/main/java/org/infinispan/query/remote/SecurityActions.java
package org.infinispan.query.remote;

import org.infinispan.AdvancedCache;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.security.Security;
import org.infinispan.security.actions.GetCacheConfigurationAction;

import java.security.AccessController;
import java.security.PrivilegedAction;

/**
 * SecurityActions for the org.infinispan.query.remote package. Do not move and do not change class and method
 * visibility!
 *
 * @author anistor@redhat.com
 * @since 7.2
 */
final class SecurityActions {

   static <T> T doPrivileged(PrivilegedAction<T> action) {
      return System.getSecurityManager() != null ?
            AccessController.doPrivileged(action) : Security.doPrivileged(action);
   }

   static Configuration getCacheConfiguration(AdvancedCache<?, ?> cache) {
      return doPrivileged(new GetCacheConfigurationAction(cache));
   }
}
