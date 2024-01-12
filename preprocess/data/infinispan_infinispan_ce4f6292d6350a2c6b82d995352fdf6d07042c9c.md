Refactoring Types: ['Inline Method', 'Extract Method', 'Move Attribute']
ge org.infinispan.cache.impl;

import org.infinispan.AdvancedCache;
import org.infinispan.Version;
import org.infinispan.atomic.Delta;
import org.infinispan.batch.BatchContainer;
import org.infinispan.commands.CommandsFactory;
import org.infinispan.commands.VisitableCommand;
import org.infinispan.commands.control.LockControlCommand;
import org.infinispan.commands.read.EntryRetrievalCommand;
import org.infinispan.commands.read.EntrySetCommand;
import org.infinispan.commands.read.GetCacheEntryCommand;
import org.infinispan.commands.read.GetAllCommand;
import org.infinispan.commands.read.GetKeyValueCommand;
import org.infinispan.commands.read.KeySetCommand;
import org.infinispan.commands.read.SizeCommand;
import org.infinispan.commands.read.ValuesCommand;
import org.infinispan.commands.remote.GetKeysInGroupCommand;
import org.infinispan.commands.write.ApplyDeltaCommand;
import org.infinispan.commands.write.ClearCommand;
import org.infinispan.commands.write.EvictCommand;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.commands.write.PutMapCommand;
import org.infinispan.commands.write.RemoveCommand;
import org.infinispan.commands.write.ReplaceCommand;
import org.infinispan.commands.write.ValueMatcher;
import org.infinispan.commons.CacheConfigurationException;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.api.BasicCacheContainer;
import org.infinispan.commons.marshall.StreamingMarshaller;
import org.infinispan.commons.util.CloseableIterable;
import org.infinispan.commons.util.CloseableIteratorCollection;
import org.infinispan.commons.util.CloseableIteratorSet;
import org.infinispan.commons.util.Util;
import org.infinispan.commons.util.concurrent.AbstractInProcessNotifyingFuture;
import org.infinispan.commons.util.concurrent.NotifyingFuture;
import org.infinispan.commons.util.concurrent.NotifyingFutureImpl;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.format.PropertyFormatter;
import org.infinispan.configuration.global.GlobalConfiguration;
import org.infinispan.container.DataContainer;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.InvocationContextContainer;
import org.infinispan.context.InvocationContextFactory;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.eviction.EvictionManager;
import org.infinispan.expiration.ExpirationManager;
import org.infinispan.factories.ComponentRegistry;
import org.infinispan.factories.annotations.ComponentName;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.factories.annotations.SurvivesRestarts;
import org.infinispan.filter.AcceptAllKeyValueFilter;
import org.infinispan.filter.KeyFilter;
import org.infinispan.filter.KeyValueFilter;
import org.infinispan.filter.NullValueConverter;
import org.infinispan.interceptors.InterceptorChain;
import org.infinispan.interceptors.base.CommandInterceptor;
import org.infinispan.iteration.EntryIterable;
import org.infinispan.jmx.annotations.DataType;
import org.infinispan.jmx.annotations.DisplayType;
import org.infinispan.jmx.annotations.MBean;
import org.infinispan.jmx.annotations.ManagedAttribute;
import org.infinispan.jmx.annotations.ManagedOperation;
import org.infinispan.lifecycle.ComponentStatus;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.metadata.EmbeddedMetadata;
import org.infinispan.metadata.Metadata;
import org.infinispan.notifications.cachelistener.CacheNotifier;
import org.infinispan.notifications.cachelistener.filter.CacheEventConverter;
import org.infinispan.notifications.cachelistener.filter.CacheEventFilter;
import org.infinispan.partitionhandling.AvailabilityMode;
import org.infinispan.partitionhandling.impl.PartitionHandlingManager;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.security.AuthorizationManager;
import org.infinispan.stats.Stats;
import org.infinispan.stats.impl.StatsImpl;
import org.infinispan.topology.LocalTopologyManager;
import org.infinispan.transaction.impl.TransactionCoordinator;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.xa.TransactionXaAdapter;
import org.infinispan.transaction.xa.recovery.RecoveryManager;
import org.infinispan.util.concurrent.locks.LockManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.InvalidTransactionException;
import javax.transaction.SystemException;
import javax.transaction.Transaction;
import javax.transaction.TransactionManager;
import javax.transaction.xa.XAResource;

import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.EnumSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static java.util.concurrent.TimeUnit.MILLISECONDS;
import static org.infinispan.context.Flag.FAIL_SILENTLY;
import static org.infinispan.context.Flag.FORCE_ASYNCHRONOUS;
import static org.infinispan.context.Flag.IGNORE_RETURN_VALUES;
import static org.infinispan.context.Flag.PUT_FOR_EXTERNAL_READ;
import static org.infinispan.context.Flag.ZERO_LOCK_ACQUISITION_TIMEOUT;
import static org.infinispan.context.InvocationContextFactory.UNBOUNDED;
import static org.infinispan.factories.KnownComponentNames.ASYNC_OPERATIONS_EXECUTOR;
import static org.infinispan.factories.KnownComponentNames.CACHE_MARSHALLER;

/**
 * @author Mircea.Markus@jboss.com
 * @author Galder Zamarreño
 * @author Sanne Grinovero
 * @author <a href="http://gleamynode.net/">Trustin Lee</a>
 * @since 4.0
 */
@SurvivesRestarts
@MBean(objectName = CacheImpl.OBJECT_NAME, description = "Component that represents an individual cache instance.")
public class CacheImpl<K, V> implements AdvancedCache<K, V> {
   public static final String OBJECT_NAME = "Cache";
   protected InvocationContextContainer icc;
   protected InvocationContextFactory invocationContextFactory;
   protected CommandsFactory commandsFactory;
   protected InterceptorChain invoker;
   protected Configuration config;
   protected CacheNotifier notifier;
   protected BatchContainer batchContainer;
   protected ComponentRegistry componentRegistry;
   protected TransactionManager transactionManager;
   protected RpcManager rpcManager;
   protected StreamingMarshaller marshaller;
   protected Metadata defaultMetadata;
   private final String name;
   private EvictionManager evictionManager;
   private ExpirationManager<K, V> expirationManager;
   private DataContainer dataContainer;
   private static final Log log = LogFactory.getLog(CacheImpl.class);
   private static final boolean trace = log.isTraceEnabled();
   private EmbeddedCacheManager cacheManager;
   private LockManager lockManager;
   private DistributionManager distributionManager;
   private ExecutorService asyncExecutor;
   private TransactionTable txTable;
   private RecoveryManager recoveryManager;
   private TransactionCoordinator txCoordinator;
   private AuthorizationManager authorizationManager;
   private PartitionHandlingManager partitionHandlingManager;
   private GlobalConfiguration globalCfg;
   private boolean isClassLoaderInContext;
   private LocalTopologyManager localTopologyManager;

   public CacheImpl(String name) {
      this.name = name;
   }

   @Inject
   public void injectDependencies(EvictionManager evictionManager,
                                  ExpirationManager expirationManager,
                                  InvocationContextFactory invocationContextFactory,
                                  InvocationContextContainer icc,
                                  CommandsFactory commandsFactory,
                                  InterceptorChain interceptorChain,
                                  Configuration configuration,
                                  CacheNotifier notifier,
                                  ComponentRegistry componentRegistry,
                                  TransactionManager transactionManager,
                                  BatchContainer batchContainer,
                                  RpcManager rpcManager, DataContainer dataContainer,
                                  @ComponentName(CACHE_MARSHALLER) StreamingMarshaller marshaller,
                                  DistributionManager distributionManager,
                                  EmbeddedCacheManager cacheManager,
                                  @ComponentName(ASYNC_OPERATIONS_EXECUTOR) ExecutorService asyncExecutor,
                                  TransactionTable txTable, RecoveryManager recoveryManager, TransactionCoordinator txCoordinator,
                                  LockManager lockManager,
                                  AuthorizationManager authorizationManager,
                                  GlobalConfiguration globalCfg,
                                  PartitionHandlingManager partitionHandlingManager,
                                  LocalTopologyManager localTopologyManager) {
      this.commandsFactory = commandsFactory;
      this.invoker = interceptorChain;
      this.config = configuration;
      this.notifier = notifier;
      this.componentRegistry = componentRegistry;
      this.transactionManager = transactionManager;
      this.batchContainer = batchContainer;
      this.rpcManager = rpcManager;
      this.evictionManager = evictionManager;
      this.expirationManager = expirationManager;
      this.dataContainer = dataContainer;
      this.marshaller = marshaller;
      this.cacheManager = cacheManager;
      this.invocationContextFactory = invocationContextFactory;
      this.icc = icc;
      this.distributionManager = distributionManager;
      this.asyncExecutor = asyncExecutor;
      this.txTable = txTable;
      this.recoveryManager = recoveryManager;
      this.txCoordinator = txCoordinator;
      this.lockManager = lockManager;
      this.authorizationManager = authorizationManager;
      this.globalCfg = globalCfg;
      this.partitionHandlingManager = partitionHandlingManager;
      this.localTopologyManager = localTopologyManager;
   }

   private void assertKeyNotNull(Object key) {
      if (key == null) {
         throw new NullPointerException("Null keys are not supported!");
      }
   }

   private void assertKeyValueNotNull(Object key, Object value) {
      assertKeyNotNull(key);
      if (value == null) {
         throw new NullPointerException("Null values are not supported!");
      }
   }

   private void assertValueNotNull(Object value) {
      if (value == null) {
         throw new NullPointerException("Null values are not supported!");
      }
   }

   private void assertKeysNotNull(Map<?, ?> data) {
      if (data == null) {
         throw new NullPointerException("Expected map cannot be null");
      }
      for (Object key : data.keySet()) {
         if (key == null) {
            throw new NullPointerException("Null keys are not supported!");
         }
      }
   }

   // CacheSupport does not extend AdvancedCache, so it cannot really call up
   // to the cache methods that take Metadata parameter. Since CacheSupport
   // methods are declared final, the easiest is for CacheImpl to stop
   // extending CacheSupport and implement the base methods directly.

   @Override
   public final V put(K key, V value) {
      return put(key, value, defaultMetadata);
   }

   @Override
   public final V put(K key, V value, long lifespan, TimeUnit unit) {
      return put(key, value, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final V putIfAbsent(K key, V value, long lifespan, TimeUnit unit) {
      return putIfAbsent(key, value, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final void putAll(Map<? extends K, ? extends V> map, long lifespan, TimeUnit unit) {
      putAll(map, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final V replace(K key, V value, long lifespan, TimeUnit unit) {
      return replace(key, value, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final boolean replace(K key, V oldValue, V value, long lifespan, TimeUnit unit) {
      return replace(key, oldValue, value, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final V putIfAbsent(K key, V value) {
      return putIfAbsent(key, value, defaultMetadata);
   }

   @Override
   public final boolean replace(K key, V oldValue, V newValue) {
      return replace(key, oldValue, newValue, defaultMetadata);
   }

   @Override
   public final V replace(K key, V value) {
      return replace(key, value, defaultMetadata);
   }

   @Override
   public final NotifyingFuture<V> putAsync(K key, V value) {
      return putAsync(key, value, defaultMetadata);
   }

   @Override
   public final NotifyingFuture<V> putAsync(K key, V value, long lifespan, TimeUnit unit) {
      return putAsync(key, value, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final NotifyingFuture<Void> putAllAsync(Map<? extends K, ? extends V> data) {
      return putAllAsync(data, defaultMetadata, null, null);
   }

   @Override
   public final NotifyingFuture<Void> putAllAsync(Map<? extends K, ? extends V> data, long lifespan, TimeUnit unit) {
      return putAllAsync(data, lifespan, MILLISECONDS, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final NotifyingFuture<V> putIfAbsentAsync(K key, V value) {
      return putIfAbsentAsync(key, value, defaultMetadata, null, null);
   }

   @Override
   public final NotifyingFuture<V> putIfAbsentAsync(K key, V value, long lifespan, TimeUnit unit) {
      return putIfAbsentAsync(key, value, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final NotifyingFuture<V> replaceAsync(K key, V value) {
      return replaceAsync(key, value, defaultMetadata, null, null);
   }

   @Override
   public final NotifyingFuture<V> replaceAsync(K key, V value, long lifespan, TimeUnit unit) {
      return replaceAsync(key, value, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final NotifyingFuture<Boolean> replaceAsync(K key, V oldValue, V newValue) {
      return replaceAsync(key, oldValue, newValue, defaultMetadata, null, null);
   }

   @Override
   public final NotifyingFuture<Boolean> replaceAsync(K key, V oldValue, V newValue, long lifespan, TimeUnit unit) {
      return replaceAsync(key, oldValue, newValue, lifespan, unit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public final void putAll(Map<? extends K, ? extends V> m) {
      putAll(m, defaultMetadata, null, null);
   }

   @Override
   public final boolean remove(Object key, Object value) {
      return remove(key, value, null, null);
   }

   final boolean remove(Object key, Object value, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextWithImplicitTransaction(false, explicitClassLoader, 1);
      return removeInternal(key, value, explicitFlags, ctx);
   }

   private boolean removeInternal(Object key, Object value, EnumSet<Flag> explicitFlags, InvocationContext ctx) {
      assertKeyValueNotNull(key, value);
      RemoveCommand command = commandsFactory.buildRemoveCommand(key, value, explicitFlags);
      return (Boolean) executeCommandAndCommitIfNeeded(ctx, command);
   }

   @Override
   public final int size() {
      return size(null, null);
   }

   final int size(EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      SizeCommand command = commandsFactory.buildSizeCommand(explicitFlags);
      return (Integer) invoker.invoke(getInvocationContextForRead(explicitClassLoader, UNBOUNDED), command);
   }

   @Override
   public final boolean isEmpty() {
      return isEmpty(null, null);
   }

   final boolean isEmpty(EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      try (CloseableIterable<CacheEntry<K, Void>> iterable = filterEntries(AcceptAllKeyValueFilter.getInstance(),
            explicitFlags, explicitClassLoader).converter(NullValueConverter.getInstance())) {
         return !iterable.iterator().hasNext();
      }
   }

   @Override
   public final boolean containsKey(Object key) {
      return containsKey(key, null, null);
   }

   final boolean containsKey(Object key, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      assertKeyNotNull(key);
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, 1);
      GetKeyValueCommand command = commandsFactory.buildGetKeyValueCommand(key, explicitFlags);
      Object response = invoker.invoke(ctx, command);
      return response != null;
   }

   @Override
   public final boolean containsValue(Object value) {
      return containsValue(value, null, null);
   }

   final boolean containsValue(Object value, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      assertValueNotNull(value);
      try (CloseableIterable<CacheEntry<K, V>> iterable = filterEntries(AcceptAllKeyValueFilter.getInstance(),
                                                                           explicitFlags, explicitClassLoader)) {
         for (CacheEntry<K, V> entry : iterable) {
            if (value.equals(entry.getValue())) {
               return true;
            }
         }
      }
      return false;
   }

   @Override
   public final V get(Object key) {
      return get(key, null, null);
   }

   @SuppressWarnings("unchecked")
   final V get(Object key, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      assertKeyNotNull(key);
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, 1);
      GetKeyValueCommand command = commandsFactory.buildGetKeyValueCommand(key, explicitFlags);
      return (V) invoker.invoke(ctx, command);
   }

   public final CacheEntry getCacheEntry(Object key, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      assertKeyNotNull(key);
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, 1);
      GetCacheEntryCommand command = commandsFactory.buildGetCacheEntryCommand(key, explicitFlags);
      Object ret = invoker.invoke(ctx, command);
      return (CacheEntry) ret;
   }

   @Override
   public final CacheEntry getCacheEntry(K key) {
      return getCacheEntry(key, null, null);
   }

   @Override
   public Map<K, V> getAll(Set<?> keys) {
      return getAll(keys, null, null);
   }

   public final Map<K, V> getAll(Set<?> keys, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, keys.size());
      GetAllCommand command = commandsFactory.buildGetAllCommand(keys, explicitFlags, false);
      Map<K, V> map = (Map<K, V>) invoker.invoke(ctx, command);
      Iterator<Map.Entry<K, V>> entryIterator = map.entrySet().iterator();
      while (entryIterator.hasNext()) {
         Map.Entry<K , V> entry = entryIterator.next();
         if (entry.getValue() == null) {
            entryIterator.remove();
         }
      }
      return map;
   }

   @Override
   public Map<K, CacheEntry<K, V>> getAllCacheEntries(Set<?> keys) {
      return getAllCacheEntries(keys, null, null);
   }

   public final Map<K, CacheEntry<K, V>> getAllCacheEntries(Set<?> keys,
         EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, keys.size());
      GetAllCommand command = commandsFactory.buildGetAllCommand(keys, explicitFlags, true);
      Map<K, CacheEntry<K, V>> map = (Map<K, CacheEntry<K, V>>) invoker.invoke(ctx, command);
      Iterator<Map.Entry<K, CacheEntry<K, V>>> entryIterator = map.entrySet().iterator();
      while (entryIterator.hasNext()) {
         Map.Entry<K , CacheEntry<K, V>> entry = entryIterator.next();
         if (entry.getValue() == null) {
            entryIterator.remove();
         }
      }
      return map;
   }

   @Override
   public EntryIterable<K, V> filterEntries(KeyValueFilter<? super K, ? super V> filter) {
      return filterEntries(filter, null, null);
   }

   protected EntryIterable<K, V> filterEntries(KeyValueFilter<? super K, ? super V> filter, EnumSet<Flag> explicitFlags,
                                               ClassLoader explicitClassLoader) {
      // We need a read invocation context as the remove is done with its own context
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, UNBOUNDED);
      EntryRetrievalCommand<K, V> command = commandsFactory.buildEntryRetrievalCommand(explicitFlags, filter);
      return (EntryIterable<K, V>) invoker.invoke(ctx, command);
   }

   @Override
   public Map<K, V> getGroup(String groupName) {
      return getGroup(groupName, null, null);
   }

   protected final Map<K, V> getGroup(String groupName, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, UNBOUNDED);
      return Collections.unmodifiableMap(internalGetGroup(groupName, explicitFlags, explicitClassLoader, ctx));
   }

   private Map<K, V> internalGetGroup(String groupName, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader,
                                      InvocationContext ctx) {
      GetKeysInGroupCommand command = commandsFactory.buildGetKeysInGroupCommand(explicitFlags, groupName);
      //noinspection unchecked
      return (Map<K, V>) invoker.invoke(ctx, command);
   }

   @Override
   public void removeGroup(String groupName) {
      removeGroup(groupName, null, null);
   }

   protected final void removeGroup(String groupName, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      if (transactionManager == null) {
         nonTransactionalRemoveGroup(groupName, explicitFlags, explicitClassLoader);
      } else {
         transactionalRemoveGroup(groupName, explicitFlags, explicitClassLoader);
      }
   }

   private void transactionalRemoveGroup(String groupName, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      final boolean onGoingTransaction = getOngoingTransaction() != null;
      if (!onGoingTransaction) {
         tryBegin();
      }
      try {
         InvocationContext context = getInvocationContextWithImplicitTransaction(false, explicitClassLoader, UNBOUNDED);
         Map<K, V> keys = internalGetGroup(groupName, explicitFlags, explicitClassLoader, context);
         EnumSet<Flag> removeFlags = explicitFlags == null ? EnumSet.noneOf(Flag.class) : EnumSet.copyOf(explicitFlags);
         removeFlags.add(IGNORE_RETURN_VALUES);
         for (K key : keys.keySet()) {
            removeInternal(key, removeFlags, context);
         }
         if (!onGoingTransaction) {
            tryCommit();
         }
      } catch (RuntimeException e) {
         if (!onGoingTransaction) {
            tryRollback();
         }
         throw e;
      }
   }

   private void nonTransactionalRemoveGroup(String groupName, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext context = getInvocationContextForRead(explicitClassLoader, UNBOUNDED);
      Map<K, V> keys = internalGetGroup(groupName, explicitFlags, explicitClassLoader, context);
      EnumSet<Flag> removeFlags = explicitFlags == null ? EnumSet.noneOf(Flag.class) : EnumSet.copyOf(explicitFlags);
      removeFlags.add(IGNORE_RETURN_VALUES);
      for (K key : keys.keySet()) {
         //a new context is needed for remove since in the non-owners, the command is sent to the primary owner to be
         //executed. If the context is already populated, it throws a ClassCastException because the wrapForRemove is
         //not invoked.
         remove(key, removeFlags, explicitClassLoader);
      }
   }

   @Override
   public final V remove(Object key) {
      return remove(key, null, null);
   }

   final V remove(Object key, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextWithImplicitTransaction(false, explicitClassLoader, 1);
      return removeInternal(key, explicitFlags, ctx);
   }

   @SuppressWarnings("unchecked")
   private V removeInternal(Object key, EnumSet<Flag> explicitFlags, InvocationContext ctx) {
      assertKeyNotNull(key);
      RemoveCommand command = commandsFactory.buildRemoveCommand(key, null, explicitFlags);
      return (V) executeCommandAndCommitIfNeeded(ctx, command);
   }


   @ManagedOperation(
         description = "Clears the cache",
         displayName = "Clears the cache", name = "clear"
   )
   public final void clearOperation() {
      clear(null, null);
   }

   @Override
   public final void clear() {
      clear(null, null);
   }

   final void clear(EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      final Transaction tx = suspendOngoingTransactionIfExists();
      try {
         InvocationContext context = invocationContextFactory.createClearNonTxInvocationContext();
         setInvocationContextClassLoader(context, explicitClassLoader);
         ClearCommand command = commandsFactory.buildClearCommand(explicitFlags);
         invoker.invoke(context, command);
      } finally {
         resumePreviousOngoingTransaction(tx, true, "Had problems trying to resume a transaction after clear()");
      }
   }

   @Override
   public CloseableIteratorSet<K> keySet() {
      return keySet(null, null);
   }

   @SuppressWarnings("unchecked")
   CloseableIteratorSet<K> keySet(EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, UNBOUNDED);
      KeySetCommand command = commandsFactory.buildKeySetCommand(explicitFlags);
      return (CloseableIteratorSet<K>) invoker.invoke(ctx, command);
   }

   @Override
   public CloseableIteratorCollection<V> values() {
      return values(null, null);
   }

   @SuppressWarnings("unchecked")
   CloseableIteratorCollection<V> values(EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, UNBOUNDED);
      ValuesCommand command = commandsFactory.buildValuesCommand(explicitFlags);
      return (CloseableIteratorCollection<V>) invoker.invoke(ctx, command);
   }

   @Override
   public CloseableIteratorSet<Map.Entry<K, V>> entrySet() {
      return entrySet(null, null);
   }

   @SuppressWarnings("unchecked")
   CloseableIteratorSet<Map.Entry<K, V>> entrySet(EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextForRead(explicitClassLoader, UNBOUNDED);
      EntrySetCommand command = commandsFactory.buildEntrySetCommand(explicitFlags);
      return (CloseableIteratorSet<Map.Entry<K, V>>) invoker.invoke(ctx, command);
   }

   @Override
   public final void putForExternalRead(K key, V value) {
      putForExternalRead(key, value, null, null);
   }

   @Override
   public void putForExternalRead(K key, V value, long lifespan, TimeUnit lifespanUnit) {
      putForExternalRead(key, value, lifespan, lifespanUnit, defaultMetadata.maxIdle(), MILLISECONDS);
   }

   @Override
   public void putForExternalRead(K key, V value, long lifespan, TimeUnit lifespanUnit, long maxIdleTime, TimeUnit idleTimeUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
       .lifespan(lifespan, lifespanUnit)
       .maxIdle(maxIdleTime, idleTimeUnit).build();
      putForExternalRead(key, value, metadata);
   }

   @Override
   public void putForExternalRead(K key, V value, Metadata metadata) {
      Metadata merged = applyDefaultMetadata(metadata);
      putForExternalRead(key, value, merged, null, null);
   }

   final void putForExternalRead(K key, V value, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      putForExternalRead(key, value, defaultMetadata, explicitFlags, explicitClassLoader);
   }

   final void putForExternalRead(K key, V value, Metadata metadata, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      Transaction ongoingTransaction = null;
      try {
         ongoingTransaction = suspendOngoingTransactionIfExists();

         EnumSet<Flag> flags = EnumSet.of(FAIL_SILENTLY, FORCE_ASYNCHRONOUS, ZERO_LOCK_ACQUISITION_TIMEOUT, PUT_FOR_EXTERNAL_READ);
         if (explicitFlags != null && !explicitFlags.isEmpty()) {
            flags.addAll(explicitFlags);
         }

         // if the entry exists then this should be a no-op.
         putIfAbsent(key, value, metadata, flags, explicitClassLoader);
      } catch (Exception e) {
         if (log.isDebugEnabled()) log.debug("Caught exception while doing putForExternalRead()", e);
      }
      finally {
         resumePreviousOngoingTransaction(ongoingTransaction, true, "Had problems trying to resume a transaction after putForExternalRead()");
      }
   }

   @Override
   public final void evict(K key) {
      evict(key, null, null);
   }

   final void evict(K key, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      assertKeyNotNull(key);
      InvocationContext ctx = createSingleKeyNonTxInvocationContext(explicitClassLoader);
      EvictCommand command = commandsFactory.buildEvictCommand(key, explicitFlags);
      invoker.invoke(ctx, command);
   }

   private InvocationContext createSingleKeyNonTxInvocationContext(ClassLoader explicitClassLoader) {
      InvocationContext ctx = invocationContextFactory.createSingleKeyNonTxInvocationContext();
      return setInvocationContextClassLoader(ctx, explicitClassLoader);
   }

   @Override
   public Configuration getCacheConfiguration() {
      return config;
   }

   @Override
   public void addListener(Object listener) {
      notifier.addListener(listener);
   }

   @Override
   public void addListener(Object listener, KeyFilter<? super K> filter) {
      notifier.addListener(listener, filter);
   }

   @Override
   public <C> void addListener(Object listener, CacheEventFilter<? super K, ? super V> filter,
                               CacheEventConverter<? super K, ? super V, C> converter) {
      notifier.addListener(listener, filter, converter);
   }

   @Override
   public void removeListener(Object listener) {
      notifier.removeListener(listener);
   }

   @Override
   public Set<Object> getListeners() {
      return notifier.getListeners();
   }

   private InvocationContext getInvocationContextForWrite(ClassLoader explicitClassLoader, int keyCount, boolean isPutForExternalRead) {
      InvocationContext ctx = isPutForExternalRead
            ? invocationContextFactory.createSingleKeyNonTxInvocationContext()
            : invocationContextFactory.createInvocationContext(true, keyCount);
      return setInvocationContextClassLoader(ctx, explicitClassLoader);
   }

   private InvocationContext getInvocationContextForRead(ClassLoader explicitClassLoader, int keyCount) {
      if (config.transaction().transactionMode().isTransactional()) {
         Transaction transaction = getOngoingTransaction();
         //if we are in the scope of a transaction than return a transactional context. This is relevant e.g.
         // FORCE_WRITE_LOCK is used on read operations - in that case, the lock is held for the the transaction's
         // lifespan (when in tx scope) vs. call lifespan (when not in tx scope).
         if (transaction != null)
            return getInvocationContext(transaction, explicitClassLoader, false);
      }
      InvocationContext result = invocationContextFactory.createInvocationContext(false, keyCount);
      setInvocationContextClassLoader(result, explicitClassLoader);
      return result;
   }

   private InvocationContext getInvocationContextWithImplicitTransactionForAsyncOps(boolean isPutForExternalRead, ClassLoader explicitClassLoader, int keyCount) {
      InvocationContext ctx = getInvocationContextWithImplicitTransaction(isPutForExternalRead, explicitClassLoader, keyCount);
      //If the transaction was injected then we should not have it associated to caller's thread, but with the async thread
      try {
         if (isTxInjected(ctx))
            transactionManager.suspend();
      } catch (SystemException e) {
         throw new CacheException(e);
      }
      return ctx;
   }

   /**
    * If this is a transactional cache and autoCommit is set to true then starts a transaction if this is
    * not a transactional call.
    */
   private InvocationContext getInvocationContextWithImplicitTransaction(boolean isPutForExternalRead, ClassLoader explicitClassLoader, int keyCount) {
      InvocationContext invocationContext;
      boolean txInjected = false;
      if (config.transaction().transactionMode().isTransactional() && !isPutForExternalRead) {
         Transaction transaction = getOngoingTransaction();
         if (transaction == null && config.transaction().autoCommit()) {
            transaction = tryBegin();
            txInjected = true;
         }
         invocationContext = getInvocationContext(transaction, explicitClassLoader, txInjected);
      } else {
         invocationContext = getInvocationContextForWrite(explicitClassLoader, keyCount, isPutForExternalRead);
      }
      return invocationContext;
   }

   private boolean isPutForExternalRead(EnumSet<Flag> explicitFlags) {
      return explicitFlags != null && explicitFlags.contains(PUT_FOR_EXTERNAL_READ);
   }

   private InvocationContext getInvocationContext(Transaction tx, ClassLoader explicitClassLoader,
                                                  boolean implicitTransaction) {
      InvocationContext ctx = invocationContextFactory.createInvocationContext(tx, implicitTransaction);
      return setInvocationContextClassLoader(ctx, explicitClassLoader);
   }

   private InvocationContext setInvocationContextClassLoader(InvocationContext ctx, ClassLoader explicitClassLoader) {
      if (isClassLoaderInContext) {
         ctx.setClassLoader(explicitClassLoader != null ?
               explicitClassLoader : getClassLoader());
      }
      return ctx;
   }

   @Override
   public boolean lock(K... keys) {
      assertKeyNotNull(keys);
      return lock(Arrays.asList(keys), null, null);
   }

   @Override
   public boolean lock(Collection<? extends K> keys) {
      return lock(keys, null, null);
   }

   boolean lock(Collection<? extends K> keys, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      if (!config.transaction().transactionMode().isTransactional())
         throw new UnsupportedOperationException("Calling lock() on non-transactional caches is not allowed");

      if (keys == null || keys.isEmpty()) {
         throw new IllegalArgumentException("Cannot lock empty list of keys");
      }
      InvocationContext ctx = getInvocationContextForWrite(explicitClassLoader, UNBOUNDED, false);
      LockControlCommand command = commandsFactory.buildLockControlCommand(keys, explicitFlags);
      return (Boolean) invoker.invoke(ctx, command);
   }

   @Override
   public void applyDelta(K deltaAwareValueKey, Delta delta, Object... locksToAcquire) {
      if (locksToAcquire == null || locksToAcquire.length == 0) {
         throw new IllegalArgumentException("Cannot lock empty list of keys");
      }
      InvocationContext ctx = getInvocationContextForWrite(null, UNBOUNDED, false);
      ApplyDeltaCommand command = commandsFactory.buildApplyDeltaCommand(deltaAwareValueKey, delta, Arrays.asList(locksToAcquire));
      invoker.invoke(ctx, command);
   }

   @Override
   @ManagedOperation(
         description = "Starts the cache.",
         displayName = "Starts cache."
   )
   public void start() {
      componentRegistry.start();
      defaultMetadata = new EmbeddedMetadata.Builder()
            .lifespan(config.expiration().lifespan()).maxIdle(config.expiration().maxIdle()).build();
      // Context only needs to ship ClassLoader if marshalling will be required
      isClassLoaderInContext = config.clustering().cacheMode().isClustered()
            || config.persistence().usingStores()
            || config.storeAsBinary().enabled();

      if (log.isDebugEnabled()) log.debugf("Started cache %s on %s", getName(), getCacheManager().getAddress());
   }

   @Override
   @ManagedOperation(
         description = "Stops the cache.",
         displayName = "Stops cache."
   )
   public void stop() {
      stop(null);
   }

   void stop(ClassLoader explicitClassLoader) {
      if (log.isDebugEnabled()) log.debugf("Stopping cache %s on %s", getName(), getCacheManager().getAddress());
      componentRegistry.stop();
   }

   @Override
   public List<CommandInterceptor> getInterceptorChain() {
      return invoker.asList();
   }

   @Override
   public void addInterceptor(CommandInterceptor i, int position) {
      invoker.addInterceptor(i, position);
   }

   @Override
   public boolean addInterceptorAfter(CommandInterceptor i, Class<? extends CommandInterceptor> afterInterceptor) {
      return invoker.addInterceptorAfter(i, afterInterceptor);
   }

   @Override
   public boolean addInterceptorBefore(CommandInterceptor i, Class<? extends CommandInterceptor> beforeInterceptor) {
      return invoker.addInterceptorBefore(i, beforeInterceptor);
   }

   @Override
   public void removeInterceptor(int position) {
      invoker.removeInterceptor(position);
   }

   @Override
   public void removeInterceptor(Class<? extends CommandInterceptor> interceptorType) {
      invoker.removeInterceptor(interceptorType);
   }

   @Override
   public EvictionManager getEvictionManager() {
      return evictionManager;
   }

   @Override
   public ExpirationManager getExpirationManager() {
      return expirationManager;
   }

   @Override
   public ComponentRegistry getComponentRegistry() {
      return componentRegistry;
   }

   @Override
   public DistributionManager getDistributionManager() {
      return distributionManager;
   }

   @Override
   public AuthorizationManager getAuthorizationManager() {
      return authorizationManager;
   }

   @Override
   public ComponentStatus getStatus() {
      return componentRegistry.getStatus();
   }

   /**
    * Returns String representation of ComponentStatus enumeration in order to avoid class not found exceptions in JMX
    * tools that don't have access to infinispan classes.
    */
   @ManagedAttribute(
         description = "Returns the cache status",
         displayName = "Cache status",
         dataType = DataType.TRAIT,
         displayType = DisplayType.SUMMARY
   )
   public String getCacheStatus() {
      return getStatus().toString();
   }

   @Override
   public AvailabilityMode getAvailability() {
      if (partitionHandlingManager != null) {
         return partitionHandlingManager.getAvailabilityMode();
      } else {
         return AvailabilityMode.AVAILABLE;
      }
   }

   @Override
   public void setAvailability(AvailabilityMode availability) {
      if (localTopologyManager != null) {
         try {
            localTopologyManager.setCacheAvailability(getName(), availability);
         } catch (Exception e) {
            throw new CacheException(e);
         }
      }
   }

   @ManagedAttribute(
         description = "Returns the cache availability",
         displayName = "Cache availability",
         dataType = DataType.TRAIT,
         writable = true
   )
   public String getCacheAvailability() {
      return getAvailability().toString();
   }

   public void setCacheAvailability(String availabilityString) throws Exception {
      setAvailability(AvailabilityMode.valueOf(availabilityString));
   }

   @Override
   public boolean startBatch() {
      if (!config.invocationBatching().enabled()) {
         throw new CacheConfigurationException("Invocation batching not enabled in current configuration! Please enable it.");
      }
      return batchContainer.startBatch();
   }

   @Override
   public void endBatch(boolean successful) {
      if (!config.invocationBatching().enabled()) {
         throw new CacheConfigurationException("Invocation batching not enabled in current configuration! Please enable it.");
      }
      batchContainer.endBatch(successful);
   }

   @Override
   public String getName() {
      return name;
   }

   /**
    * Returns the cache name. If this is the default cache, it returns a more friendly name.
    */
   @ManagedAttribute(
         description = "Returns the cache name",
         displayName = "Cache name",
         dataType = DataType.TRAIT,
         displayType = DisplayType.SUMMARY
   )
   public String getCacheName() {
      String name = getName().equals(BasicCacheContainer.DEFAULT_CACHE_NAME) ? "Default Cache" : getName();
      return name + "(" + getCacheConfiguration().clustering().cacheMode().toString().toLowerCase() + ")";
   }

   /**
    * Returns the version of Infinispan.
    */
   @ManagedAttribute(
         description = "Returns the version of Infinispan",
         displayName = "Infinispan version",
         dataType = DataType.TRAIT,
         displayType = DisplayType.SUMMARY
   )
   @Override
   public String getVersion() {
      return Version.getVersion();
   }

   @Override
   public String toString() {
      return "Cache '" + name + "'@" + (config !=null && config.clustering().cacheMode().isClustered() ? getCacheManager().getAddress() : Util.hexIdHashCode(this));
   }

   @Override
   public BatchContainer getBatchContainer() {
      return batchContainer;
   }

   @Override
   public InvocationContextContainer getInvocationContextContainer() {
      return icc;
   }

   @Override
   public DataContainer getDataContainer() {
      return dataContainer;
   }

   @Override
   public TransactionManager getTransactionManager() {
      return transactionManager;
   }

   @Override
   public LockManager getLockManager() {
      return this.lockManager;
   }

   @Override
   public EmbeddedCacheManager getCacheManager() {
      return cacheManager;
   }

   @Override
   public Stats getStats() {
      return new StatsImpl(invoker);
   }

   @Override
   public XAResource getXAResource() {
      return new TransactionXaAdapter(txTable, recoveryManager, txCoordinator, commandsFactory, rpcManager, null, config, name);
   }

   @Override
   public final V put(K key, V value, long lifespan, TimeUnit lifespanUnit, long maxIdleTime, TimeUnit idleTimeUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdleTime, idleTimeUnit).build();
      return put(key, value, metadata, null, null);
   }

   @SuppressWarnings("unchecked")
   final V put(K key, V value, Metadata metadata,
         EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextWithImplicitTransaction(false, explicitClassLoader, 1);
      return putInternal(key, value, metadata, explicitFlags, ctx);
   }

   @SuppressWarnings("unchecked")
   private V putInternal(K key, V value, Metadata metadata,
         EnumSet<Flag> explicitFlags, InvocationContext ctx) {
      assertKeyValueNotNull(key, value);
      PutKeyValueCommand command = commandsFactory.buildPutKeyValueCommand(key, value, metadata, explicitFlags);
      return (V) executeCommandAndCommitIfNeeded(ctx, command);
   }

   @Override
   public final V putIfAbsent(K key, V value, long lifespan, TimeUnit lifespanUnit, long maxIdleTime, TimeUnit idleTimeUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdleTime, idleTimeUnit).build();
      return putIfAbsent(key, value, metadata, null, null);
   }

   @SuppressWarnings("unchecked")
   final V putIfAbsent(K key, V value, Metadata metadata,
         EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextWithImplicitTransaction(isPutForExternalRead(explicitFlags), explicitClassLoader, 1);
      return putIfAbsentInternal(key, value, metadata, explicitFlags, ctx);
   }

   @SuppressWarnings("unchecked")
   private V putIfAbsentInternal(K key, V value, Metadata metadata,
         EnumSet<Flag> explicitFlags, InvocationContext ctx) {
      assertKeyValueNotNull(key, value);
      PutKeyValueCommand command = commandsFactory.buildPutKeyValueCommand(key, value, metadata, explicitFlags);
      command.setPutIfAbsent(true);
      command.setValueMatcher(ValueMatcher.MATCH_EXPECTED);
      return (V) executeCommandAndCommitIfNeeded(ctx, command);
   }

   @Override
   public final void putAll(Map<? extends K, ? extends V> map, long lifespan, TimeUnit lifespanUnit, long maxIdleTime, TimeUnit idleTimeUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdleTime, idleTimeUnit).build();
      putAll(map, metadata, null, null);
   }

   final void putAll(Map<? extends K, ? extends V> map, Metadata metadata, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextWithImplicitTransaction(false, explicitClassLoader, map.size());
      putAllInternal(map, metadata, explicitFlags, ctx);
   }

   private void putAllInternal(Map<? extends K, ? extends V> map, Metadata metadata, EnumSet<Flag> explicitFlags, InvocationContext ctx) {
      assertKeysNotNull(map);
      PutMapCommand command = commandsFactory.buildPutMapCommand(map, metadata, explicitFlags);
      executeCommandAndCommitIfNeeded(ctx, command);
   }

   @Override
   public final V replace(K key, V value, long lifespan, TimeUnit lifespanUnit, long maxIdleTime, TimeUnit idleTimeUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdleTime, idleTimeUnit).build();
      return replace(key, value, metadata, null, null);
   }

   @SuppressWarnings("unchecked")
   final V replace(K key, V value, Metadata metadata, EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextWithImplicitTransaction(false, explicitClassLoader, 1);
      return replaceInternal(key, value, metadata, explicitFlags, ctx);
   }

   @SuppressWarnings("unchecked")
   private V replaceInternal(K key, V value, Metadata metadata, EnumSet<Flag> explicitFlags, InvocationContext ctx) {
      assertKeyValueNotNull(key, value);
      ReplaceCommand command = commandsFactory.buildReplaceCommand(key, null, value, metadata, explicitFlags);
      return (V) executeCommandAndCommitIfNeeded(ctx, command);
   }

   @Override
   public final boolean replace(K key, V oldValue, V value, long lifespan, TimeUnit lifespanUnit, long maxIdleTime, TimeUnit idleTimeUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdleTime, idleTimeUnit).build();
      return replace(key, oldValue, value, metadata, null, null);
   }

   final boolean replace(K key, V oldValue, V value, Metadata metadata,
         EnumSet<Flag> explicitFlags, ClassLoader explicitClassLoader) {
      InvocationContext ctx = getInvocationContextWithImplicitTransaction(false, explicitClassLoader, 1);
      return replaceInternal(key, oldValue, value, metadata, explicitFlags, ctx);
   }

   private boolean replaceInternal(K key, V oldValue, V value, Metadata metadata,
         EnumSet<Flag> explicitFlags, InvocationContext ctx) {
      assertKeyValueNotNull(key, value);
      assertValueNotNull(oldValue);
      ReplaceCommand command = commandsFactory.buildReplaceCommand(
            key, oldValue, value, metadata, explicitFlags);
      return (Boolean) executeCommandAndCommitIfNeeded(ctx, command);
   }

   /**
    * Wraps a return value as a future, if needed.  Typically, if the stack, operation and configuration support
    * handling of futures, this retval is already a future in which case this method does nothing except cast to
    * future.
    * <p/>
    * Otherwise, a future wrapper is created, which has already completed and simply returns the retval.  This is used
    * for API consistency.
    *
    * @param retval return value to wrap
    * @param <X>    contents of the future
    * @return a future
    */
   @SuppressWarnings("unchecked")
   private <X> NotifyingFuture<X> wrapInFuture(final Object retval) {
      if (retval instanceof NotifyingFuture) {
         return (NotifyingFuture<X>) retval;
      } else {
         return new AbstractInProcessNotifyingFuture<X>() {
            @Override
            @SuppressWarnings("unchecked")
            public X get() throws InterruptedException, ExecutionException {
               return (X) retval;
            }
         };
      }
   }

   @Override
   public final NotifyingFuture<V> putAsync(K key, V value, long lifespan, TimeUnit lifespanUnit, long maxIdle, TimeUnit maxIdleUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdle, maxIdleUnit).build();
      return putAsync(key, value, metadata, null, null);
   }

   final NotifyingFuture<V> putAsync(final K key, final V value, final Metadata metadata, final EnumSet<Flag> explicitFlags, final ClassLoader explicitClassLoader) {
      final NotifyingFutureImpl<V> result = new NotifyingFutureImpl<V>();
      final InvocationContext ctx = getInvocationContextWithImplicitTransactionForAsyncOps(false, explicitClassLoader, 1);
      Future<V> returnValue = asyncExecutor.submit(new Callable<V>() {
         @Override
         public V call() throws Exception {
            try {
               associateImplicitTransactionWithCurrentThread(ctx);
               V retval = putInternal(key, value, metadata, explicitFlags, ctx);
               try {
                  result.notifyDone(retval);
                  log.trace("Finished notifying");
               } catch (Throwable e) {
                  log.trace("Exception while notifying the future", e);
               }
               return retval;
            } catch (Exception e) {
               try {
                  result.notifyException(e);
                  log.trace("Finished notifying");
               } catch (Throwable e2) {
                  log.trace("Exception while notifying the future", e2);
               }
               throw e;
            }
         }
      });
      result.setFuture(returnValue);
      return result;
   }

   @Override
   public final NotifyingFuture<Void> putAllAsync(Map<? extends K, ? extends V> data, long lifespan, TimeUnit lifespanUnit, long maxIdle, TimeUnit maxIdleUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdle, maxIdleUnit).build();
      return putAllAsync(data, metadata, null, null);
   }

   final NotifyingFuture<Void> putAllAsync(final Map<? extends K, ? extends V> data, final Metadata metadata, final EnumSet<Flag> explicitFlags, final ClassLoader explicitClassLoader) {
      final NotifyingFutureImpl<Void> result = new NotifyingFutureImpl<Void>();
      final InvocationContext ctx = getInvocationContextWithImplicitTransactionForAsyncOps(false, explicitClassLoader, data.size());
      Future<Void> returnValue = asyncExecutor.submit(new Callable<Void>() {
         @Override
         public Void call() throws Exception {
            try {
               associateImplicitTransactionWithCurrentThread(ctx);
               putAllInternal(data, metadata, explicitFlags, ctx);
               try {
                  result.notifyDone(null);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               return null;
            } catch (Exception e) {
               try {
                  result.notifyException(e);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               throw e;
            }
         }
      });
      result.setFuture(returnValue);
      return result;
   }

   @Override
   public final NotifyingFuture<Void> clearAsync() {
      return clearAsync(null, null);
   }

   final NotifyingFuture<Void> clearAsync(final EnumSet<Flag> explicitFlags, final ClassLoader explicitClassLoader) {
      final NotifyingFutureImpl<Void> result = new NotifyingFutureImpl<>();
      Future<Void> returnValue = asyncExecutor.submit(new Callable<Void>() {
         @Override
         public Void call() throws Exception {
            try {
               clear(explicitFlags, explicitClassLoader);
               try {
                  result.notifyDone(null);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               return null;
            } catch (Exception e) {
               try {
                  result.notifyException(e);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               throw e;
            }
         }
      });
      result.setFuture(returnValue);
      return result;
   }

   @Override
   public final NotifyingFuture<V> putIfAbsentAsync(K key, V value, long lifespan, TimeUnit lifespanUnit, long maxIdle, TimeUnit maxIdleUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdle, maxIdleUnit).build();
      return putIfAbsentAsync(key, value, metadata, null, null);
   }

   final NotifyingFuture<V> putIfAbsentAsync(final K key, final V value, final Metadata metadata,
         final EnumSet<Flag> explicitFlags,final ClassLoader explicitClassLoader) {
      final NotifyingFutureImpl<V> result = new NotifyingFutureImpl<V>();
      final InvocationContext ctx = getInvocationContextWithImplicitTransactionForAsyncOps(false, explicitClassLoader, 1);
      Future<V> returnValue = asyncExecutor.submit(new Callable<V>() {
         @Override
         public V call() throws Exception {
            try {
               associateImplicitTransactionWithCurrentThread(ctx);
               V retval = putIfAbsentInternal(key, value, metadata, explicitFlags, ctx);
               try {
                  result.notifyDone(retval);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               return retval;
            } catch (Exception e) {
               try {
                  result.notifyException(e);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               throw e;
            }
         }
      });
      result.setFuture(returnValue);
      return result;
   }

   @Override
   public final NotifyingFuture<V> removeAsync(Object key) {
      return removeAsync(key, null, null);
   }

   final NotifyingFuture<V> removeAsync(final Object key, final EnumSet<Flag> explicitFlags, final ClassLoader explicitClassLoader) {
      final NotifyingFutureImpl<V> result = new NotifyingFutureImpl<V>();
      final InvocationContext ctx = getInvocationContextWithImplicitTransactionForAsyncOps(false, explicitClassLoader, 1);
      Future<V> returnValue = asyncExecutor.submit(new Callable<V>() {
         @Override
         public V call() throws Exception {
            try {
               associateImplicitTransactionWithCurrentThread(ctx);
               V retval = removeInternal(key, explicitFlags, ctx);
               try {
                  result.notifyDone(retval);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               return retval;
            } catch (Exception e) {
               try {
                  result.notifyException(e);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               throw e;
            }
         }
      });
      result.setFuture(returnValue);
      return result;
   }

   @Override
   public final NotifyingFuture<Boolean> removeAsync(Object key, Object value) {
      return removeAsync(key, value, null, null);
   }

   final NotifyingFuture<Boolean> removeAsync(final Object key, final Object value, final EnumSet<Flag> explicitFlags, final ClassLoader explicitClassLoader) {
      final NotifyingFutureImpl<Boolean> result = new NotifyingFutureImpl<Boolean>();
      final InvocationContext ctx = getInvocationContextWithImplicitTransactionForAsyncOps(false, explicitClassLoader, 1);
      Future<Boolean> returnValue = asyncExecutor.submit(new Callable<Boolean>() {
         @Override
         public Boolean call() throws Exception {
            try {
               associateImplicitTransactionWithCurrentThread(ctx);
               Boolean retval = removeInternal(key, value, explicitFlags, ctx);
               try {
                  result.notifyDone(retval);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               return retval;
            } catch (Exception e) {
               try {
                  result.notifyException(e);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               throw e;
            }
         }
      });
      result.setFuture(returnValue);
      return result;
   }

   @Override
   public final NotifyingFuture<V> replaceAsync(K key, V value, long lifespan, TimeUnit lifespanUnit, long maxIdle, TimeUnit maxIdleUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdle, maxIdleUnit).build();
      return replaceAsync(key, value, metadata, null, null);
   }

   final NotifyingFuture<V> replaceAsync(final K key, final V value, final Metadata metadata,
         final EnumSet<Flag> explicitFlags, final ClassLoader explicitClassLoader) {
      final NotifyingFutureImpl<V> result = new NotifyingFutureImpl<V>();
      final InvocationContext ctx = getInvocationContextWithImplicitTransactionForAsyncOps(false, explicitClassLoader, 1);
      Future<V> returnValue = asyncExecutor.submit(new Callable<V>() {
         @Override
         public V call() throws Exception {
            try {
               associateImplicitTransactionWithCurrentThread(ctx);
               V retval = replaceInternal(key, value, metadata, explicitFlags, ctx);
               try {
                  result.notifyDone(retval);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               return retval;
            } catch (Exception e) {
               try {
                  result.notifyException(e);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               throw e;
            }
         }
      });
      result.setFuture(returnValue);
      return result;
   }

   @Override
   public final NotifyingFuture<Boolean> replaceAsync(K key, V oldValue, V newValue, long lifespan, TimeUnit lifespanUnit, long maxIdle, TimeUnit maxIdleUnit) {
      Metadata metadata = new EmbeddedMetadata.Builder()
            .lifespan(lifespan, lifespanUnit)
            .maxIdle(maxIdle, maxIdleUnit).build();
      return replaceAsync(key, oldValue, newValue, metadata, null, null);
   }

   final NotifyingFuture<Boolean> replaceAsync(final K key, final V oldValue, final V newValue,
         final Metadata metadata, final EnumSet<Flag> explicitFlags, final ClassLoader explicitClassLoader) {
      final NotifyingFutureImpl<Boolean> result = new NotifyingFutureImpl<Boolean>();
      final InvocationContext ctx = getInvocationContextWithImplicitTransactionForAsyncOps(false, explicitClassLoader, 1);
      Future<Boolean> returnValue = asyncExecutor.submit(new Callable<Boolean>() {
         @Override
         public Boolean call() throws Exception {
            try {
               associateImplicitTransactionWithCurrentThread(ctx);
               Boolean retval = replaceInternal(key, oldValue, newValue, metadata, explicitFlags, ctx);
               try {
                  result.notifyDone(retval);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               return retval;
            } catch (Exception e) {
               try {
                  result.notifyException(e);
               } catch (Throwable t) {
                  log.trace("Error when notifying", t);
               }
               throw e;
            }
         }
      });
      result.setFuture(returnValue);
      return result;
   }

   @Override
   public NotifyingFuture<V> getAsync(K key) {
      return getAsync(key, null, null);
   }

   @SuppressWarnings("unchecked")
   NotifyingFuture<V> getAsync(final K key, final EnumSet<Flag> explicitFlags, final ClassLoader explicitClassLoader) {
      // Optimization to not start a new thread only when the operation is cheap:
      if (asyncSkipsThread(explicitFlags, key)) {
         return wrapInFuture(get(key, explicitFlags, explicitClassLoader));
      } else {
         // Make sure the flags are cleared
         final EnumSet<Flag> appliedFlags;
         if (explicitFlags == null) {
            appliedFlags = null;
         } else {
            appliedFlags = explicitFlags.clone();
            explicitFlags.clear();
         }
         final NotifyingFutureImpl<V> result = new NotifyingFutureImpl<V>();

         Callable<V> c = new Callable<V>() {
            @Override
            public V call() throws Exception {
               try {
                  V retval = get(key, appliedFlags, explicitClassLoader);
                  try {
                     result.notifyDone(retval);
                  } catch (Throwable t) {
                     log.trace("Error when notifying", t);
                  }
                  return retval;
               } catch (Exception e) {
                  try {
                     result.notifyException(e);
                  } catch (Throwable t) {
                     log.trace("Error when notifying", t);
                  }
                  throw e;
               }
            }
         };
         result.setFuture(asyncExecutor.submit(c));
         return result;
      }
   }

   /**
    * Encodes the cases for an asyncGet operation in which it makes sense to actually perform the operation in sync.
    *
    * @return true if we skip the thread (performing it in sync)
    */
   private boolean asyncSkipsThread(EnumSet<Flag> flags, K key) {
      boolean isSkipLoader = isSkipLoader(flags);
      if (!isSkipLoader) {
         // if we can't skip the cacheloader, we really want a thread for async.
         return false;
      }
      if (!config.clustering().cacheMode().isDistributed()) {
         //in these cluster modes we won't RPC for a get, so no need to fork a thread.
         return true;
      } else if (flags != null && (flags.contains(Flag.SKIP_REMOTE_LOOKUP) || flags.contains(Flag.CACHE_MODE_LOCAL))) {
         //with these flags we won't RPC either
         return true;
      }
      //finally, we will skip the thread if the key maps to the local node
      return distributionManager.getLocality(key).isLocal();
   }

   private boolean isSkipLoader(EnumSet<Flag> flags) {
      boolean hasCacheLoaderConfig = !config.persistence().stores().isEmpty();
      return !hasCacheLoaderConfig
            || (flags != null && (flags.contains(Flag.SKIP_CACHE_LOAD) || flags.contains(Flag.SKIP_CACHE_STORE)));
   }

   @Override
   public AdvancedCache<K, V> getAdvancedCache() {
      return this;
   }

   @Override
   public RpcManager getRpcManager() {
      return rpcManager;
   }

   @Override
   public AdvancedCache<K, V> withFlags(final Flag... flags) {
      if (flags == null || flags.length == 0)
         return this;
      else
         return new DecoratedCache<K, V>(this, flags);
   }

   private Transaction getOngoingTransaction() {
      try {
         Transaction transaction = null;
         if (transactionManager != null) {
            transaction = transactionManager.getTransaction();
            if (transaction == null && config.invocationBatching().enabled()) {
               transaction = batchContainer.getBatchTransaction();
            }
         }
         return transaction;
      } catch (SystemException e) {
         throw new CacheException("Unable to get transaction", e);
      }
   }

   private Object executeCommandAndCommitIfNeeded(InvocationContext ctx, VisitableCommand command) {
      final boolean txInjected = isTxInjected(ctx);
      Object result;
      try {
         result = invoker.invoke(ctx, command);
      } catch (RuntimeException e) {
         if (txInjected) tryRollback();
         throw e;
      }

      if (txInjected) {
         tryCommit();
      }

      return result;
   }

   private boolean isTxInjected(InvocationContext ctx) {
      return ctx.isInTxScope() && ((TxInvocationContext) ctx).isImplicitTransaction();
   }

   private Transaction tryBegin() {
      if (transactionManager == null) {
         return null;
      }
      try {
         transactionManager.begin();
         final Transaction transaction = getOngoingTransaction();
         if (log.isTraceEnabled()) {
            log.tracef("Implicit transaction started! Transaction: %s", transaction);
         }
         return transaction;
      } catch (RuntimeException e) {
         throw e;
      } catch (Exception e) {
         throw new CacheException("Unable to begin implicit transaction.", e);
      }
   }

   private void tryRollback() {
      try {
         if (transactionManager != null) transactionManager.rollback();
      } catch (Throwable t) {
         if (trace) log.trace("Could not rollback", t);//best effort
      }
   }

   private void tryCommit() {
      if (transactionManager == null) {
         return;
      }
      if (trace)
         log.tracef("Committing transaction as it was implicit: %s", getOngoingTransaction());
      try {
         transactionManager.commit();
      } catch (Throwable e) {
         log.couldNotCompleteInjectedTransaction(e);
         throw new CacheException("Could not commit implicit transaction", e);
      }
   }

   @Override
   public ClassLoader getClassLoader() {
      ClassLoader classLoader = globalCfg.classLoader();
      return classLoader != null ? classLoader : Thread.currentThread().getContextClassLoader();
   }

   @Override
   public AdvancedCache<K, V> with(ClassLoader classLoader) {
      return new DecoratedCache<K, V>(this, classLoader);
   }

   @Override
   public V put(K key, V value, Metadata metadata) {
      Metadata merged = applyDefaultMetadata(metadata);
      return put(key, value, merged, null, null);
   }

   @Override
   public void putAll(Map<? extends K, ? extends V> map, Metadata metadata) {
      Metadata merged = applyDefaultMetadata(metadata);
      putAll(map, merged, null, null);
   }

   private Metadata applyDefaultMetadata(Metadata metadata) {
      Metadata.Builder builder = metadata.builder();
      return builder != null ? builder.merge(defaultMetadata).build() : metadata;
   }

   @Override
   public V replace(K key, V value, Metadata metadata) {
      Metadata merged = applyDefaultMetadata(metadata);
      return replace(key, value, merged, null, null);
   }

   @Override
   public boolean replace(K key, V oldValue, V value, Metadata metadata) {
      Metadata merged = applyDefaultMetadata(metadata);
      return replace(key, oldValue, value, merged, null, null);
   }

   @Override
   public V putIfAbsent(K key, V value, Metadata metadata) {
      Metadata merged = applyDefaultMetadata(metadata);
      return putIfAbsent(key, value, merged, null, null);
   }

   @Override
   public NotifyingFuture<V> putAsync(K key, V value, Metadata metadata) {
      Metadata merged = applyDefaultMetadata(metadata);
      return putAsync(key, value, merged, null, null);
   }

   private void associateImplicitTransactionWithCurrentThread(InvocationContext ctx) throws InvalidTransactionException, SystemException {
      if (isTxInjected(ctx)) {
         Transaction transaction = ((TxInvocationContext) ctx).getTransaction();
         if (transaction == null)
            throw new IllegalStateException("Null transaction not possible!");
         transactionManager.resume(transaction);
      }
   }

   private Transaction suspendOngoingTransactionIfExists() {
      final Transaction tx = getOngoingTransaction();
      if (tx != null) {
         try {
            transactionManager.suspend();
         } catch (SystemException e) {
            throw new CacheException("Unable to suspend transaction.", e);
         }
      }
      return tx;
   }

   private void resumePreviousOngoingTransaction(Transaction transaction, boolean failSilently, String failMessage) {
      if (transaction != null) {
         try {
            transactionManager.resume(transaction);
         } catch (Exception e) {
            if (failSilently) {
               if (log.isDebugEnabled()) {
                  log.debug(failMessage);
               }
            } else {
               throw new CacheException(failMessage, e);
            }
         }
      }
   }

   @ManagedAttribute(
         description = "Returns the cache configuration in form of properties",
         displayName = "Cache configuration properties",
         dataType = DataType.TRAIT,
         displayType = DisplayType.SUMMARY
   )
   public Properties getConfigurationAsProperties() {
      return new PropertyFormatter().format(config);
   }
}


File: core/src/main/java/org/infinispan/commands/remote/recovery/TxCompletionNotificationCommand.java
package org.infinispan.commands.remote.recovery;

import org.infinispan.commands.TopologyAffectedCommand;
import org.infinispan.context.InvocationContext;
import org.infinispan.statetransfer.StateTransferManager;
import org.infinispan.transaction.impl.RemoteTransaction;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.transaction.xa.recovery.RecoveryManager;
import org.infinispan.util.concurrent.locks.LockManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.xa.Xid;

import java.util.Set;

/**
 * Command for removing recovery related information from the cluster.
 *
 * @author Mircea.Markus@jboss.com
 * @since 5.0
 */
public class TxCompletionNotificationCommand  extends RecoveryCommand implements TopologyAffectedCommand {

   private static Log log = LogFactory.getLog(TxCompletionNotificationCommand.class);

   public static final int COMMAND_ID = 22;

   private Xid xid;
   private long internalId;
   private GlobalTransaction gtx;
   private TransactionTable txTable;
   private LockManager lockManager;
   private StateTransferManager stateTransferManager;
   private int topologyId = -1;

   private TxCompletionNotificationCommand() {
      super(null); // For command id uniqueness test
   }

   public TxCompletionNotificationCommand(Xid xid, GlobalTransaction gtx, String cacheName) {
      super(cacheName);
      this.xid = xid;
      this.gtx = gtx;
   }

   public void init(TransactionTable tt, LockManager lockManager, RecoveryManager rm, StateTransferManager stm) {
      super.init(rm);
      this.txTable = tt;
      this.lockManager = lockManager;
      this.stateTransferManager = stm;
   }


   public TxCompletionNotificationCommand(long internalId, String cacheName) {
      super(cacheName);
      this.internalId = internalId;
   }

   public TxCompletionNotificationCommand(String cacheName) {
      super(cacheName);
   }

   @Override
   public int getTopologyId() {
      return topologyId;
   }

   @Override
   public void setTopologyId(int topologyId) {
      this.topologyId = topologyId;
   }

   @Override
   public boolean isReturnValueExpected() {
      return false;
   }

   @Override
   public Object perform(InvocationContext ctx) throws Throwable {
      log.tracef("Processing completed transaction %s", gtx);
      RemoteTransaction remoteTx = null;
      if (recoveryManager != null) { //recovery in use
         if (xid != null) {
            remoteTx = (RemoteTransaction) recoveryManager.removeRecoveryInformation(xid);
         } else {
            remoteTx = (RemoteTransaction) recoveryManager.removeRecoveryInformation(internalId);
         }
      }
      if (remoteTx == null && gtx != null) {
         remoteTx = txTable.removeRemoteTransaction(gtx);
      }
      boolean successful = remoteTx != null && !remoteTx.isMarkedForRollback();
      if (gtx != null) {
         txTable.markTransactionCompleted(gtx, successful);
      } else if (remoteTx != null) {
         txTable.markTransactionCompleted(remoteTx.getGlobalTransaction(), successful);
      }
      if (remoteTx == null) return null;
      forwardCommandRemotely(remoteTx);

      lockManager.unlock(remoteTx.getLockedKeys(), remoteTx.getGlobalTransaction());
      return null;
   }

   public GlobalTransaction getGlobalTransaction() {
      return gtx;
   }

   /**
    * This only happens during state transfer.
    */
   private void forwardCommandRemotely(RemoteTransaction remoteTx) {
      Set<Object> affectedKeys = remoteTx.getAffectedKeys();
      log.tracef("Invoking forward of TxCompletionNotification for transaction %s. Affected keys: %s", gtx, affectedKeys);
      stateTransferManager.forwardCommandIfNeeded(this, affectedKeys, remoteTx.getGlobalTransaction().getAddress(), false);
   }

   @Override
   public byte getCommandId() {
      return COMMAND_ID;
   }

   @Override
   public Object[] getParameters() {
      return new Object[]{xid != null ? xid : internalId, gtx};
   }

   @Override
   public void setParameters(int commandId, Object[] parameters) {
      if (commandId != COMMAND_ID) {
         throw new IllegalArgumentException("Wrong command id. Received " + commandId + " and expected " + TxCompletionNotificationCommand.COMMAND_ID);
      }
      if (parameters[0] instanceof Xid) {
         xid = (Xid) parameters[0];
      } else {
         internalId = (Long) parameters[0];
      }
      gtx = (GlobalTransaction) parameters[1];
   }

   @Override
   public boolean canBlock() {
      //this command can be forwarded (state transfer)
      return true;
   }

   @Override
   public String toString() {
      return getClass().getSimpleName() +
            "{ xid=" + xid +
            ", internalId=" + internalId +
            ", topologyId=" + topologyId +
            ", gtx=" + gtx +
            ", cacheName=" + cacheName + "} ";
   }
}


File: core/src/main/java/org/infinispan/factories/PartitionHandlingManagerFactory.java
package org.infinispan.factories;


import org.infinispan.factories.annotations.DefaultFactoryFor;
import org.infinispan.partitionhandling.impl.PartitionHandlingManager;
import org.infinispan.partitionhandling.impl.PartitionHandlingManagerImpl;

/**
 * @author Dan Berindei
 * @since 7.0
 */
@DefaultFactoryFor(classes = PartitionHandlingManager.class)
public class PartitionHandlingManagerFactory extends AbstractNamedCacheComponentFactory implements
      AutoInstantiableFactory {
   @Override
   @SuppressWarnings("unchecked")
   public <T> T construct(Class<T> componentType) {
      if (configuration.clustering().partitionHandling().enabled()) {
         if (configuration.clustering().cacheMode().isDistributed() ||
               configuration.clustering().cacheMode().isReplicated()) {
            return (T) new PartitionHandlingManagerImpl();
         }
      }
      return null;
   }
}


File: core/src/main/java/org/infinispan/interceptors/TxInterceptor.java
package org.infinispan.interceptors;

import java.util.concurrent.atomic.AtomicLong;
import javax.transaction.Status;
import javax.transaction.SystemException;
import javax.transaction.Transaction;

import org.infinispan.Cache;
import org.infinispan.commands.CommandsFactory;
import org.infinispan.commands.VisitableCommand;
import org.infinispan.commands.control.LockControlCommand;
import org.infinispan.commands.read.EntryRetrievalCommand;
import org.infinispan.commands.read.EntrySetCommand;
import org.infinispan.commands.read.GetCacheEntryCommand;
import org.infinispan.commands.read.GetKeyValueCommand;
import org.infinispan.commands.read.GetAllCommand;
import org.infinispan.commands.read.KeySetCommand;
import org.infinispan.commands.read.SizeCommand;
import org.infinispan.commands.read.ValuesCommand;
import org.infinispan.commands.tx.AbstractTransactionBoundaryCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.commands.tx.RollbackCommand;
import org.infinispan.commands.write.ApplyDeltaCommand;
import org.infinispan.commands.write.ClearCommand;
import org.infinispan.commands.write.InvalidateCommand;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.commands.write.PutMapCommand;
import org.infinispan.commands.write.RemoveCommand;
import org.infinispan.commands.write.ReplaceCommand;
import org.infinispan.commands.write.WriteCommand;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.interceptors.base.CommandInterceptor;
import org.infinispan.iteration.EntryIterable;
import org.infinispan.iteration.impl.TransactionAwareEntryIterable;
import org.infinispan.jmx.JmxStatisticsExposer;
import org.infinispan.jmx.annotations.DataType;
import org.infinispan.jmx.annotations.DisplayType;
import org.infinispan.jmx.annotations.MBean;
import org.infinispan.jmx.annotations.ManagedAttribute;
import org.infinispan.jmx.annotations.ManagedOperation;
import org.infinispan.jmx.annotations.MeasurementType;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.transport.Address;
import org.infinispan.statetransfer.OutdatedTopologyException;
import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.impl.LocalTransaction;
import org.infinispan.transaction.impl.RemoteTransaction;
import org.infinispan.transaction.impl.TransactionCoordinator;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.transaction.xa.recovery.RecoverableTransactionIdentifier;
import org.infinispan.transaction.xa.recovery.RecoveryManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

/**
 * Interceptor in charge with handling transaction related operations, e.g enlisting cache as an transaction
 * participant, propagating remotely initiated changes.
 *
 * @author <a href="mailto:manik@jboss.org">Manik Surtani (manik@jboss.org)</a>
 * @author Mircea.Markus@jboss.com
 * @see org.infinispan.transaction.xa.TransactionXaAdapter
 * @since 4.0
 */
@MBean(objectName = "Transactions", description = "Component that manages the cache's participation in JTA transactions.")
public class TxInterceptor extends CommandInterceptor implements JmxStatisticsExposer {

   private TransactionTable txTable;

   private final AtomicLong prepares = new AtomicLong(0);
   private final AtomicLong commits = new AtomicLong(0);
   private final AtomicLong rollbacks = new AtomicLong(0);
   private boolean statisticsEnabled;
   protected TransactionCoordinator txCoordinator;
   protected RpcManager rpcManager;

   private static final Log log = LogFactory.getLog(TxInterceptor.class);
   private static final boolean trace = log.isTraceEnabled();
   private RecoveryManager recoveryManager;
   private boolean isTotalOrder;
   private boolean useOnePhaseForAutoCommitTx;
   private boolean useVersioning;
   private CommandsFactory commandsFactory;
   private Cache cache;

   @Override
   protected Log getLog() {
      return log;
   }

   @Inject
   public void init(TransactionTable txTable, Configuration configuration, TransactionCoordinator txCoordinator, RpcManager rpcManager,
                    RecoveryManager recoveryManager, CommandsFactory commandsFactory, Cache cache) {
      this.cacheConfiguration = configuration;
      this.txTable = txTable;
      this.txCoordinator = txCoordinator;
      this.rpcManager = rpcManager;
      this.recoveryManager = recoveryManager;
      this.commandsFactory = commandsFactory;
      this.cache = cache;

      statisticsEnabled = cacheConfiguration.jmxStatistics().enabled();
      isTotalOrder = configuration.transaction().transactionProtocol().isTotalOrder();
      useOnePhaseForAutoCommitTx = cacheConfiguration.transaction().use1PcForAutoCommitTransactions();
      useVersioning = configuration.transaction().transactionMode().isTransactional() && configuration.locking().writeSkewCheck() &&
            configuration.transaction().lockingMode() == LockingMode.OPTIMISTIC && configuration.versioning().enabled();
   }

   @Override
   public Object visitPrepareCommand(TxInvocationContext ctx, PrepareCommand command) throws Throwable {
      //if it is remote and 2PC then first log the tx only after replying mods
      if (this.statisticsEnabled) prepares.incrementAndGet();
      if (!ctx.isOriginLocal()) {
         ((RemoteTransaction) ctx.getCacheTransaction()).setLookedUpEntriesTopology(command.getTopologyId());
      } else {
         if (ctx.getCacheTransaction().hasModification(ClearCommand.class)) {
            throw new IllegalStateException("No ClearCommand is allowed in Transaction.");
         }
      }
      Object result = invokeNextInterceptorAndVerifyTransaction(ctx, command);
      if (!ctx.isOriginLocal()) {
         if (command.isOnePhaseCommit()) {
            txTable.remoteTransactionCommitted(command.getGlobalTransaction(), true);
         } else {
            txTable.remoteTransactionPrepared(command.getGlobalTransaction());
         }
      }
      return result;
   }

   private Object invokeNextInterceptorAndVerifyTransaction(TxInvocationContext ctx, AbstractTransactionBoundaryCommand command) throws Throwable {
      try {
         return invokeNextInterceptor(ctx, command);
      } finally {
         if (!ctx.isOriginLocal()) {
            // command.getOrigin() and ctx.getOrigin() are not reliable for LockControlCommands started by
            // ClusteredGetCommands, or for PrepareCommands started by MultipleRpcCommands (when the replication queue
            // is enabled).
            Address origin = ctx.getGlobalTransaction().getAddress();
            //It is possible to receive a prepare or lock control command from a node that crashed. If that's the case rollback
            //the transaction forcefully in order to cleanup resources.
            boolean originatorMissing = !rpcManager.getTransport().getMembers().contains(origin);
            // It is also possible that the LCC timed out on the originator's end and this node has processed
            // a TxCompletionNotification.  So we need to check the presence of the remote transaction to
            // see if we need to clean up any acquired locks on our end.
            boolean alreadyCompleted = txTable.isTransactionCompleted(command.getGlobalTransaction()) ||
                    !txTable.containRemoteTx(command.getGlobalTransaction());
            // We want to throw an exception if the originator left the cluster and the transaction is not finished
            // and/or it was rolled back by TransactionTable.cleanupLeaverTransactions().
            // We don't want to throw an exception if the originator left the cluster but the transaction already
            // completed successfully. So far, this only seems possible when forcing the commit of an orphaned
            // transaction (with recovery enabled).
            boolean completedSuccessfully = alreadyCompleted && !ctx.getCacheTransaction().isMarkedForRollback();
            if (trace) {
               log.tracef("invokeNextInterceptorAndVerifyTransaction :: originatorMissing=%s, alreadyCompleted=%s",
                       originatorMissing, alreadyCompleted);
            }

            if (alreadyCompleted || originatorMissing) {
               if (trace) {
                  log.tracef("Rolling back remote transaction %s because either already completed (%s) or originator no " +
                          "longer in the cluster (%s).",
                          command.getGlobalTransaction(), alreadyCompleted, originatorMissing);
               }
               RollbackCommand rollback = new RollbackCommand(command.getCacheName(), command.getGlobalTransaction());
               try {
                  invokeNextInterceptor(ctx, rollback);
               } finally {
                  RemoteTransaction remoteTx = (RemoteTransaction) ctx.getCacheTransaction();
                  remoteTx.markForRollback(true);
                  txTable.removeRemoteTransaction(command.getGlobalTransaction());
               }
            }

            if (originatorMissing && !completedSuccessfully) {
               throw log.orphanTransactionRolledBack(ctx.getGlobalTransaction());
            }
         }
      }
   }

   @Override
   public Object visitCommitCommand(TxInvocationContext ctx, CommitCommand command) throws Throwable {
      GlobalTransaction gtx = ctx.getGlobalTransaction();
      // TODO The local origin check is needed for CommitFailsTest, but it doesn't appear correct to roll back an in-doubt tx
      if (!ctx.isOriginLocal()) {
         if (txTable.isTransactionCompleted(gtx)) {
            if (trace) log.tracef("Transaction %s already completed, skipping commit", gtx);
            return null;
         }

         if (!isTotalOrder) {
            // If a commit is received for a transaction that doesn't have its 'lookedUpEntries' populated
            // we know for sure this transaction is 2PC and was received via state transfer but the preceding PrepareCommand
            // was not received by local node because it was executed on the previous key owners. We need to re-prepare
            // the transaction on local node to ensure its locks are acquired and lookedUpEntries is properly populated.
            RemoteTransaction remoteTx = (RemoteTransaction) ctx.getCacheTransaction();
            if (trace) {
               log.tracef("Remote tx topology id %d and command topology is %d", remoteTx.lookedUpEntriesTopology(),
                          command.getTopologyId());
            }
            if (remoteTx.lookedUpEntriesTopology() < command.getTopologyId()) {
               PrepareCommand prepareCommand;
               if (useVersioning) {
                  prepareCommand = commandsFactory.buildVersionedPrepareCommand(ctx.getGlobalTransaction(), ctx.getModifications(), false);
               } else {
                  prepareCommand = commandsFactory.buildPrepareCommand(ctx.getGlobalTransaction(), ctx.getModifications(), false);
               }
               commandsFactory.initializeReplicableCommand(prepareCommand, true);
               prepareCommand.setOrigin(ctx.getOrigin());
               if (trace)
                  log.tracef("Replaying the transactions received as a result of state transfer %s", prepareCommand);
               visitPrepareCommand(ctx, prepareCommand);
            }
         }
      }

      if (this.statisticsEnabled) commits.incrementAndGet();
      Object result = invokeNextInterceptor(ctx, command);
      if (!ctx.isOriginLocal() || isTotalOrder) {
         txTable.remoteTransactionCommitted(gtx, false);
      }
      return result;
   }

   @Override
   public Object visitRollbackCommand(TxInvocationContext ctx, RollbackCommand command) throws Throwable {
      if (this.statisticsEnabled) rollbacks.incrementAndGet();
      // The transaction was marked as completed in RollbackCommand.prepare()
      if (!ctx.isOriginLocal() || isTotalOrder) {
         txTable.remoteTransactionRollback(command.getGlobalTransaction());
      }
      try {
         return invokeNextInterceptor(ctx, command);
      } finally {
         //for tx that rollback we do not send a TxCompletionNotification, so we should cleanup
         // the recovery info here
         if (recoveryManager!=null) {
            GlobalTransaction gtx = command.getGlobalTransaction();
            recoveryManager.removeRecoveryInformation(((RecoverableTransactionIdentifier)gtx).getXid());
         }
      }
   }

   @Override
   public Object visitLockControlCommand(TxInvocationContext ctx, LockControlCommand command) throws Throwable {
      enlistIfNeeded(ctx);

      if (ctx.isOriginLocal()) {
         command.setGlobalTransaction(ctx.getGlobalTransaction());
      }

      return invokeNextInterceptorAndVerifyTransaction(ctx, command);
   }

   @Override
   public Object visitPutKeyValueCommand(InvocationContext ctx, PutKeyValueCommand command) throws Throwable {
      return enlistWriteAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitApplyDeltaCommand(InvocationContext ctx, ApplyDeltaCommand command) throws Throwable {
      return enlistWriteAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitRemoveCommand(InvocationContext ctx, RemoveCommand command) throws Throwable {
      return enlistWriteAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitReplaceCommand(InvocationContext ctx, ReplaceCommand command) throws Throwable {
      return enlistWriteAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitClearCommand(InvocationContext ctx, ClearCommand command) throws Throwable {
      return invokeNextInterceptor(ctx, command);
   }

   @Override
   public Object visitPutMapCommand(InvocationContext ctx, PutMapCommand command) throws Throwable {
      return enlistWriteAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitSizeCommand(InvocationContext ctx, SizeCommand command) throws Throwable {
      return enlistReadAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitKeySetCommand(InvocationContext ctx, KeySetCommand command) throws Throwable {
      return enlistReadAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitValuesCommand(InvocationContext ctx, ValuesCommand command) throws Throwable {
      return enlistReadAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitEntrySetCommand(InvocationContext ctx, EntrySetCommand command) throws Throwable {
      return enlistReadAndInvokeNext(ctx, command);
   }

   @Override
   public Object visitInvalidateCommand(InvocationContext ctx, InvalidateCommand invalidateCommand) throws Throwable {
      return enlistWriteAndInvokeNext(ctx, invalidateCommand);
   }

   @Override
   public Object visitGetKeyValueCommand(InvocationContext ctx, GetKeyValueCommand command) throws Throwable {
      return enlistReadAndInvokeNext(ctx, command);
   }

   @Override
   public final Object visitGetCacheEntryCommand(InvocationContext ctx, GetCacheEntryCommand command) throws Throwable {
      return enlistReadAndInvokeNext(ctx, command);
   }
   
   @Override
   public Object visitGetAllCommand(InvocationContext ctx, GetAllCommand command) throws Throwable {
      return enlistReadAndInvokeNext(ctx, command);
   }

   @Override
   public EntryIterable visitEntryRetrievalCommand(InvocationContext ctx, EntryRetrievalCommand command) throws Throwable {
      // Enlistment shouldn't be needed for this command.  The remove on the iterator will internally make a remove
      // command and the iterator itself does not place read values into the context.
      EntryIterable iterable = (EntryIterable) super.visitEntryRetrievalCommand(ctx, command);
      if (ctx.isInTxScope()) {
         return new TransactionAwareEntryIterable(iterable, command.getFilter(), 
               (TxInvocationContext<LocalTransaction>) ctx, cache);
      } else {
         return iterable;
      }
   }

   private Object enlistReadAndInvokeNext(InvocationContext ctx, VisitableCommand command) throws Throwable {
      enlistIfNeeded(ctx);
      return invokeNextInterceptor(ctx, command);
   }

   private void enlistIfNeeded(InvocationContext ctx) throws SystemException {
      if (shouldEnlist(ctx)) {
         enlist((TxInvocationContext) ctx);
      }
   }

   private Object enlistWriteAndInvokeNext(InvocationContext ctx, WriteCommand command) throws Throwable {
      LocalTransaction localTransaction = null;
      if (shouldEnlist(ctx)) {
         localTransaction = enlist((TxInvocationContext) ctx);
         boolean implicitWith1Pc = useOnePhaseForAutoCommitTx && localTransaction.isImplicitTransaction();
         if (implicitWith1Pc) {
            //in this situation we don't support concurrent updates so skip locking entirely
            command.setFlags(Flag.SKIP_LOCKING);
         }
      }
      Object rv;
      try {
         rv = invokeNextInterceptor(ctx, command);
      } catch (OutdatedTopologyException e) {
         // The command will be retried, so we shouldn't mark the transaction for rollback
         throw e;
      } catch (Throwable throwable) {
         // Don't mark the transaction for rollback if it's fail silent (i.e. putForExternalRead)
         if (ctx.isOriginLocal() && ctx.isInTxScope() && !command.hasFlag(Flag.FAIL_SILENTLY)) {
            TxInvocationContext txCtx = (TxInvocationContext) ctx;
            txCtx.getTransaction().setRollbackOnly();
         }
         throw throwable;
      }
      if (localTransaction != null && command.isSuccessful()) {
         localTransaction.addModification(command);
      }
      return rv;
   }

   public LocalTransaction enlist(TxInvocationContext ctx) throws SystemException {
      Transaction transaction = ctx.getTransaction();
      if (transaction == null) throw new IllegalStateException("This should only be called in an tx scope");
      int status = transaction.getStatus();
      if (isNotValid(status)) throw new IllegalStateException("Transaction " + transaction +
            " is not in a valid state to be invoking cache operations on.");
      LocalTransaction localTransaction = txTable.getLocalTransaction(transaction);
      txTable.enlist(transaction, localTransaction);
      return localTransaction;
   }

   private boolean isNotValid(int status) {
      return status != Status.STATUS_ACTIVE
            && status != Status.STATUS_PREPARING
            && status != Status.STATUS_COMMITTING;
   }

   private static boolean shouldEnlist(InvocationContext ctx) {
      return ctx.isInTxScope() && ctx.isOriginLocal();
   }

   @Override
   public boolean getStatisticsEnabled() {
      return isStatisticsEnabled();
   }

   @Override
   public void setStatisticsEnabled(boolean enabled) {
      statisticsEnabled = enabled;
   }

   @ManagedOperation(
         description = "Resets statistics gathered by this component",
         displayName = "Reset Statistics"
   )
   public void resetStatistics() {
      prepares.set(0);
      commits.set(0);
      rollbacks.set(0);
   }

   @ManagedAttribute(
         displayName = "Statistics enabled",
         dataType = DataType.TRAIT,
         writable = true
   )
   public boolean isStatisticsEnabled() {
      return this.statisticsEnabled;
   }

   @ManagedAttribute(
         description = "Number of transaction prepares performed since last reset",
         displayName = "Prepares",
         measurementType = MeasurementType.TRENDSUP,
         displayType = DisplayType.SUMMARY
   )
   public long getPrepares() {
      return prepares.get();
   }

   @ManagedAttribute(
         description = "Number of transaction commits performed since last reset",
         displayName = "Commits",
         measurementType = MeasurementType.TRENDSUP,
         displayType = DisplayType.SUMMARY
   )
   public long getCommits() {
      return commits.get();
   }

   @ManagedAttribute(
         description = "Number of transaction rollbacks performed since last reset",
         displayName = "Rollbacks",
         measurementType = MeasurementType.TRENDSUP,
         displayType = DisplayType.SUMMARY
   )
   public long getRollbacks() {
      return rollbacks.get();
   }
}


File: core/src/main/java/org/infinispan/interceptors/distribution/BaseDistributionInterceptor.java
package org.infinispan.interceptors.distribution;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.infinispan.commands.FlagAffectedCommand;
import org.infinispan.commands.ReplicableCommand;
import org.infinispan.commands.read.GetAllCommand;
import org.infinispan.commands.remote.ClusteredGetCommand;
import org.infinispan.commands.remote.ClusteredGetAllCommand;
import org.infinispan.commands.remote.GetKeysInGroupCommand;
import org.infinispan.commands.write.ClearCommand;
import org.infinispan.commands.write.DataWriteCommand;
import org.infinispan.commands.write.ValueMatcher;
import org.infinispan.commands.write.WriteCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.container.entries.InternalCacheValue;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.distribution.RemoteValueRetrievedListener;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.distribution.group.GroupManager;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.interceptors.ClusteringInterceptor;
import org.infinispan.interceptors.locking.ClusteringDependentLogic;
import org.infinispan.remoting.RemoteException;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.responses.CacheNotFoundResponse;
import org.infinispan.remoting.responses.ClusteredGetResponseValidityFilter;
import org.infinispan.remoting.responses.ExceptionResponse;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.responses.SuccessfulResponse;
import org.infinispan.remoting.rpc.ResponseFilter;
import org.infinispan.remoting.rpc.ResponseMode;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.rpc.RpcOptions;
import org.infinispan.remoting.rpc.RpcOptionsBuilder;
import org.infinispan.remoting.transport.Address;
import org.infinispan.remoting.transport.jgroups.SuspectException;
import org.infinispan.statetransfer.OutdatedTopologyException;
import org.infinispan.topology.CacheTopology;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import static org.infinispan.commons.util.Util.toStr;

/**
 * Base class for distribution of entries across a cluster.
 *
 * @author Manik Surtani
 * @author Mircea.Markus@jboss.com
 * @author Pete Muir
 * @author Dan Berindei <dan@infinispan.org>
 * @since 4.0
 */
public abstract class BaseDistributionInterceptor extends ClusteringInterceptor {

   protected DistributionManager dm;

   protected ClusteringDependentLogic cdl;
   protected RemoteValueRetrievedListener rvrl;
   private GroupManager groupManager;

   private static final Log log = LogFactory.getLog(BaseDistributionInterceptor.class);
   private static final boolean trace = log.isTraceEnabled();

   @Override
   protected Log getLog() {
      return log;
   }

   @Inject
   public void injectDependencies(DistributionManager distributionManager, ClusteringDependentLogic cdl,
                                  RemoteValueRetrievedListener rvrl, GroupManager groupManager) {
      this.dm = distributionManager;
      this.cdl = cdl;
      this.rvrl = rvrl;
      this.groupManager = groupManager;
   }

   @Override
   public final Object visitGetKeysInGroupCommand(InvocationContext ctx, GetKeysInGroupCommand command) throws Throwable {
      final String groupName = command.getGroupName();
      if (command.isGroupOwner()) {
         //don't go remote if we are an owner.
         return invokeNextInterceptor(ctx, command);
      }
      Map<Address, Response> responseMap = rpcManager.invokeRemotely(Collections.singleton(groupManager.getPrimaryOwner(groupName)), command,
                                                                     rpcManager.getDefaultRpcOptions(true));
      if (!responseMap.isEmpty()) {
         Response response = responseMap.values().iterator().next();
         if (response instanceof SuccessfulResponse) {
            //noinspection unchecked
            List<CacheEntry> cacheEntries = (List<CacheEntry>) ((SuccessfulResponse) response).getResponseValue();
            for (CacheEntry entry : cacheEntries) {
               entryFactory.wrapEntryForReading(ctx, entry.getKey(), entry);
            }
         }
      }
      return invokeNextInterceptor(ctx, command);
   }

   @Override
   public final Object visitClearCommand(InvocationContext ctx, ClearCommand command) throws Throwable {
      if (ctx.isOriginLocal() && !isLocalModeForced(command)) {
         rpcManager.invokeRemotely(null, command, rpcManager.getDefaultRpcOptions(isSynchronous(command)));
      }
      return invokeNextInterceptor(ctx, command);
   }

   @Override
   protected final InternalCacheEntry retrieveFromRemoteSource(Object key, InvocationContext ctx, boolean acquireRemoteLock, FlagAffectedCommand command, boolean isWrite) throws Exception {
      GlobalTransaction gtx = ctx.isInTxScope() ? ((TxInvocationContext)ctx).getGlobalTransaction() : null;
      ClusteredGetCommand get = cf.buildClusteredGetCommand(key, command.getFlags(), acquireRemoteLock, gtx);
      get.setWrite(isWrite);

      RpcOptionsBuilder rpcOptionsBuilder = rpcManager.getRpcOptionsBuilder(ResponseMode.WAIT_FOR_VALID_RESPONSE, DeliverOrder.NONE);
      int lastTopologyId = -1;
      InternalCacheEntry value = null;
      while (value == null) {
         final CacheTopology cacheTopology = stateTransferManager.getCacheTopology();
         final int currentTopologyId = cacheTopology.getTopologyId();

         if (trace) {
            log.tracef("Perform remote get for key %s. topologyId=%s, currentTopologyId=%s",
                       key, lastTopologyId, currentTopologyId);
         }
         List<Address> targets;
         if (lastTopologyId < currentTopologyId) {
            // Cache topology has changed or it is the first time.
            lastTopologyId = currentTopologyId;
            targets = new ArrayList<>(cacheTopology.getReadConsistentHash().locateOwners(key));
         } else if (lastTopologyId == currentTopologyId && cacheTopology.getPendingCH() != null) {
            // Same topologyId, but the owners could have already installed the next topology
            // Lets try with pending consistent owners (the read owners in the next topology)
            lastTopologyId = currentTopologyId + 1;
            targets = new ArrayList<>(cacheTopology.getPendingCH().locateOwners(key));
            // Remove already contacted nodes
            targets.removeAll(cacheTopology.getReadConsistentHash().locateOwners(key));
            if (targets.isEmpty()) {
               if (trace) {
                  log.tracef("No valid values found for key '%s' (topologyId=%s).", key, currentTopologyId);
               }
               break;
            }
         } else { // lastTopologyId > currentTopologyId || cacheTopology.getPendingCH() == null
            // We have not received a valid value from the pending CH owners either, and the topology id hasn't changed
            if (trace) {
               log.tracef("No valid values found for key '%s' (topologyId=%s).", key, currentTopologyId);
            }
            break;
         }

         value = invokeClusterGetCommandRemotely(targets, rpcOptionsBuilder, get, key);
         if (trace) {
            log.tracef("Remote get of key '%s' (topologyId=%s) returns %s", key, currentTopologyId, value);
         }
      }
      return value;
   }

   private InternalCacheEntry invokeClusterGetCommandRemotely(List<Address> targets, RpcOptionsBuilder rpcOptionsBuilder,
                                                      ClusteredGetCommand get, Object key) {
      ResponseFilter filter = new ClusteredGetResponseValidityFilter(targets, rpcManager.getAddress());
      RpcOptions options = rpcOptionsBuilder.responseFilter(filter).build();
      Map<Address, Response> responses = rpcManager.invokeRemotely(targets, get, options);

      if (!responses.isEmpty()) {
         for (Response r : responses.values()) {
            if (r instanceof SuccessfulResponse) {

               // The response value might be null.
               SuccessfulResponse response = (SuccessfulResponse) r;
               Object responseValue = response.getResponseValue();
               if (responseValue == null) {
                  continue;
               }

               InternalCacheValue cacheValue = (InternalCacheValue) responseValue;
               InternalCacheEntry ice = cacheValue.toInternalCacheEntry(key);
               if (rvrl != null) {
                  rvrl.remoteValueFound(ice);
               }
               return ice;
            }
         }
      }
      if (rvrl != null) {
         rvrl.remoteValueNotFound(key);
      }
      return null;
   }

   protected Map<Object, InternalCacheEntry> retrieveFromRemoteSources(Set<?> requestedKeys, InvocationContext ctx, Set<Flag> flags) throws Throwable {
      GlobalTransaction gtx = ctx.isInTxScope() ? ((TxInvocationContext)ctx).getGlobalTransaction() : null;
      CacheTopology cacheTopology = stateTransferManager.getCacheTopology();
      ConsistentHash ch = cacheTopology.getReadConsistentHash();

      Map<Address, List<Object>> ownerKeys = new HashMap<>();
      for (Object key : requestedKeys) {
         Address owner = ch.locatePrimaryOwner(key);
         List<Object> requestedKeysFromNode = ownerKeys.get(owner);
         if (requestedKeysFromNode == null) {
            ownerKeys.put(owner, requestedKeysFromNode = new ArrayList<>());
         }
         requestedKeysFromNode.add(key);
      }

      Map<Address, ReplicableCommand> commands = new HashMap<>();
      for (Map.Entry<Address, List<Object>> entry : ownerKeys.entrySet()) {
         List<Object> keys = entry.getValue();
         ClusteredGetAllCommand remoteGetAll = cf.buildClusteredGetAllCommand(keys, flags, gtx);
         commands.put(entry.getKey(), remoteGetAll);
      }

      RpcOptionsBuilder rpcOptionsBuilder = rpcManager.getRpcOptionsBuilder(
            ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS, DeliverOrder.NONE);
      RpcOptions options = rpcOptionsBuilder.build();
      Map<Address, Response> responses = rpcManager.invokeRemotely(commands, options);

      Map<Object, InternalCacheEntry> entries = new HashMap<>();
      for (Map.Entry<Address, Response> entry : responses.entrySet()) {
         updateWithValues(((ClusteredGetAllCommand) commands.get(entry.getKey())).getKeys(),
               entry.getValue(), entries);
      }

      return entries;
   }

   private void updateWithValues(List<?> keys, Response r, Map<Object, InternalCacheEntry> entries) {
      if (r instanceof SuccessfulResponse) {
         SuccessfulResponse response = (SuccessfulResponse) r;
         List<InternalCacheValue> values = (List<InternalCacheValue>) response.getResponseValue();
         // Only process if we got a return value - this can happen if the node is shutting
         // down when it received the request
         if (values != null) {
            for (int i = 0; i < keys.size(); ++i) {
               InternalCacheValue icv = values.get(i);
               if (icv != null) {
                  Object key = keys.get(i);
                  Object value = icv.getValue();
                  if (value == null) {
                     entries.put(key, null);
                  } else {
                     InternalCacheEntry ice = icv.toInternalCacheEntry(key);
                     entries.put(key, ice);
                  }
               }
            }
         }
      }
   }

   protected final Object handleNonTxWriteCommand(InvocationContext ctx, DataWriteCommand command) throws Throwable {
      if (ctx.isInTxScope()) {
         throw new CacheException("Attempted execution of non-transactional write command in a transactional invocation context");
      }

      RecipientGenerator recipientGenerator = new SingleKeyRecipientGenerator(command.getKey());

      // see if we need to load values from remote sources first
      if (needValuesFromPreviousOwners(ctx, command)) {
         remoteGetBeforeWrite(ctx, command, recipientGenerator);
      }

      // invoke the command locally, we need to know if it's successful or not
      Object localResult = invokeNextInterceptor(ctx, command);

      // if this is local mode then skip distributing
      if (isLocalModeForced(command)) {
         return localResult;
      }


      boolean isSync = isSynchronous(command);
      Address primaryOwner = cdl.getPrimaryOwner(command.getKey());
      int commandTopologyId = command.getTopologyId();
      int currentTopologyId = stateTransferManager.getCacheTopology().getTopologyId();
      // TotalOrderStateTransferInterceptor doesn't set the topology id for PFERs.
      // TODO Shouldn't PFERs be executed in a tx with total order?
      boolean topologyChanged = isSync && currentTopologyId != commandTopologyId && commandTopologyId != -1;
      if (trace) {
         log.tracef("Command topology id is %d, current topology id is %d, successful? %s",
               (Object)commandTopologyId, currentTopologyId, command.isSuccessful());
      }
      // We need to check for topology changes on the origin even if the command was unsuccessful
      // otherwise we execute the command on the correct primary owner, and then we still
      // throw an OutdatedTopologyInterceptor when we return in EntryWrappingInterceptor.
      if (topologyChanged) {
         throw new OutdatedTopologyException("Cache topology changed while the command was executing: expected " +
               commandTopologyId + ", got " + currentTopologyId);
      }

      ValueMatcher valueMatcher = command.getValueMatcher();
      if (!ctx.isOriginLocal()) {
         if (primaryOwner.equals(rpcManager.getAddress())) {
            if (!command.isSuccessful()) {
               log.tracef("Skipping the replication of the conditional command as it did not succeed on primary owner (%s).", command);
               return localResult;
            }
            List<Address> recipients = recipientGenerator.generateRecipients();
            // Ignore the previous value on the backup owners
            command.setValueMatcher(ValueMatcher.MATCH_ALWAYS);
            try {
               rpcManager.invokeRemotely(recipients, command, determineRpcOptionsForBackupReplication(rpcManager,
                                                                                                      isSync, recipients));
            } finally {
               // Switch to the retry policy, in case the primary owner changed and the write already succeeded on the new primary
               command.setValueMatcher(valueMatcher.matcherForRetry());
            }
         }
         return localResult;
      } else {
         if (primaryOwner.equals(rpcManager.getAddress())) {
            if (!command.isSuccessful()) {
               log.tracef("Skipping the replication of the command as it did not succeed on primary owner (%s).", command);
               return localResult;
            }
            List<Address> recipients = recipientGenerator.generateRecipients();
            log.tracef("I'm the primary owner, sending the command to all the backups (%s) in order to be applied.",
                  recipients);
            // check if a single owner has been configured and the target for the key is the local address
            boolean isSingleOwnerAndLocal = cacheConfiguration.clustering().hash().numOwners() == 1;
            if (!isSingleOwnerAndLocal) {
               // Ignore the previous value on the backup owners
               command.setValueMatcher(ValueMatcher.MATCH_ALWAYS);
               try {
                  rpcManager.invokeRemotely(recipients, command, determineRpcOptionsForBackupReplication(rpcManager,
                                                                                                         isSync, recipients));
               } finally {
                  // Switch to the retry policy, in case the primary owner changed and the write already succeeded on the new primary
                  command.setValueMatcher(valueMatcher.matcherForRetry());
               }
            }
            return localResult;
         } else {
            log.tracef("I'm not the primary owner, so sending the command to the primary owner(%s) in order to be forwarded", primaryOwner);
            boolean isSyncForwarding = isSync || isNeedReliableReturnValues(command);

            Map<Address, Response> addressResponseMap;
            try {
               addressResponseMap = rpcManager.invokeRemotely(Collections.singletonList(primaryOwner), command,
                     rpcManager.getDefaultRpcOptions(isSyncForwarding));
            } catch (RemoteException e) {
               Throwable ce = e;
               while (ce instanceof RemoteException) {
                  ce = ce.getCause();
               }
               if (ce instanceof OutdatedTopologyException) {
                  // If the primary owner throws an OutdatedTopologyException, it must be because the command succeeded there
                  if (trace) log.tracef("Changing the value matching policy from %s to %s (original value was %s)",
                        command.getValueMatcher(), valueMatcher.matcherForRetry(), valueMatcher);
                  command.setValueMatcher(valueMatcher.matcherForRetry());
               }
               throw e;
            } catch (SuspectException e) {
               // If the primary owner became suspected, we don't know if it was able to replicate it's data properly
               // to all backup owners and notify all listeners, thus we need to retry with new matcher in case if
               // it had updated the backup owners
               if (trace) log.tracef("Primary owner suspected - Changing the value matching policy from %s to %s " +
                                           "(original value was %s)", command.getValueMatcher(),
                                     valueMatcher.matcherForRetry(), valueMatcher);
               command.setValueMatcher(valueMatcher.matcherForRetry());
               throw e;
            }
            if (!isSyncForwarding) return localResult;

            Object primaryResult = getResponseFromPrimaryOwner(primaryOwner, addressResponseMap);
            command.updateStatusFromRemoteResponse(primaryResult);
            return primaryResult;
         }
      }
   }

   private RpcOptions determineRpcOptionsForBackupReplication(RpcManager rpc, boolean isSync, List<Address> recipients) {
      RpcOptions options;
      if (isSync) {
         // If no recipients, means a broadcast, so we can ignore leavers
         if (recipients == null) {
            options = rpc.getRpcOptionsBuilder(ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS).build();
         } else {
            options = rpc.getDefaultRpcOptions(true);
         }
      } else {
         options = rpc.getDefaultRpcOptions(false);
      }
      return options;
   }

   private Object getResponseFromPrimaryOwner(Address primaryOwner, Map<Address, Response> addressResponseMap) {
      Response fromPrimaryOwner = addressResponseMap.get(primaryOwner);
      if (fromPrimaryOwner == null) {
         log.tracef("Primary owner %s returned null", primaryOwner);
         return null;
      }
      if (fromPrimaryOwner.isSuccessful()) {
         return ((SuccessfulResponse) fromPrimaryOwner).getResponseValue();
      }

      if (addressResponseMap.get(primaryOwner) instanceof CacheNotFoundResponse) {
         // This means the cache wasn't running on the primary owner, so the command wasn't executed.
         // We throw an OutdatedTopologyException, StateTransferInterceptor will catch the exception and
         // it will then retry the command.
         throw new OutdatedTopologyException("Cache is no longer running on primary owner " + primaryOwner);
      }

      Throwable cause = fromPrimaryOwner instanceof ExceptionResponse ? ((ExceptionResponse)fromPrimaryOwner).getException() : null;
      throw new CacheException("Got unsuccessful response from primary owner: " + fromPrimaryOwner, cause);
   }

   @Override
   public Object visitGetAllCommand(InvocationContext ctx, GetAllCommand command) throws Throwable {
      if (command.hasFlag(Flag.CACHE_MODE_LOCAL)
            || command.hasFlag(Flag.SKIP_REMOTE_LOOKUP)
            || command.hasFlag(Flag.IGNORE_RETURN_VALUES)) {
         return invokeNextInterceptor(ctx, command);
      }

      int commandTopologyId = command.getTopologyId();
      if (ctx.isOriginLocal()) {
         int currentTopologyId = stateTransferManager.getCacheTopology().getTopologyId();
         boolean topologyChanged = currentTopologyId != commandTopologyId && commandTopologyId != -1;
         if (trace) {
            log.tracef("Command topology id is %d, current topology id is %d", commandTopologyId, currentTopologyId);
         }
         if (topologyChanged) {
            throw new OutdatedTopologyException("Cache topology changed while the command was executing: expected " +
                  commandTopologyId + ", got " + currentTopologyId);
         }

         // At this point, we know that an entry located on this node that exists in the data container/store
         // must also exist in the context.
         ConsistentHash ch = command.getConsistentHash();
         Set<Object> requestedKeys = new HashSet<>();
         for (Object key : command.getKeys()) {
            CacheEntry entry = ctx.lookupEntry(key);
            if (entry == null) {
               if (!isValueAvailableLocally(ch, key)) {
                  requestedKeys.add(key);
               } else {
                  if (trace) {
                     log.tracef("Not doing a remote get for missing key %s since entry is "
                                 + "mapped to current node (%s). Owners are %s",
                           toStr(key), rpcManager.getAddress(), ch.locateOwners(key));
                  }
                  // Force a map entry to be created, because we know this entry is local
                  entryFactory.wrapEntryForPut(ctx, key, null, false, command, false);
               }
            }
         }

         boolean missingRemoteValues = false;
         if (!requestedKeys.isEmpty()) {
            if (trace) {
               log.tracef("Fetching entries for keys %s from remote nodes", requestedKeys);
            }

            Map<Object, InternalCacheEntry> justRetrieved = retrieveFromRemoteSources(
                  requestedKeys, ctx, command.getFlags());
            Map<Object, InternalCacheEntry> previouslyFetched = command.getRemotelyFetched();
            if (previouslyFetched != null) {
               previouslyFetched.putAll(justRetrieved);
            } else {
               command.setRemotelyFetched(justRetrieved);
            }
            for (Object key : requestedKeys) {
               if (!justRetrieved.containsKey(key)) {
                  missingRemoteValues = true;
               } else {
                  entryFactory.wrapEntryForPut(ctx, key, justRetrieved.get(key), false, command, false);
               }
            }
         }

         if (missingRemoteValues) {
            throw new OutdatedTopologyException("Remote values are missing because of a topology change");
         }
         return invokeNextInterceptor(ctx, command);
      } else { // remote
         int currentTopologyId = stateTransferManager.getCacheTopology().getTopologyId();
         boolean topologyChanged = currentTopologyId != commandTopologyId && commandTopologyId != -1;
         // If the topology changed while invoking, this means we cannot trust any null values
         // so we shouldn't return them
         ConsistentHash ch = command.getConsistentHash();
         for (Object key : command.getKeys()) {
            CacheEntry entry = ctx.lookupEntry(key);
            if (entry == null || entry.isNull()) {
               if (isValueAvailableLocally(ch, key) && !topologyChanged) {
                  if (trace) {
                     log.tracef("Not doing a remote get for missing key %s since entry is "
                                 + "mapped to current node (%s). Owners are %s",
                           toStr(key), rpcManager.getAddress(), ch.locateOwners(key));
                  }
                  // Force a map entry to be created, because we know this entry is local
                  entryFactory.wrapEntryForPut(ctx, key, null, false, command, false);
               }
            }
         }
         Map<Object, Object> values = (Map<Object, Object>) invokeNextInterceptor(ctx, command);
         return values;
      }
   }

   /**
    * @return Whether a remote get is needed to obtain the previous values of the affected entries.
    */
   protected abstract boolean needValuesFromPreviousOwners(InvocationContext ctx, WriteCommand command);

   protected abstract void remoteGetBeforeWrite(InvocationContext ctx, WriteCommand command, RecipientGenerator keygen) throws Throwable;

   interface RecipientGenerator {

      Collection<Object> getKeys();

      List<Address> generateRecipients();
   }

   class SingleKeyRecipientGenerator implements RecipientGenerator {
      private final Object key;
      private final Set<Object> keys;
      private List<Address> recipients = null;

      SingleKeyRecipientGenerator(Object key) {
         this.key = key;
         keys = Collections.singleton(key);
      }

      @Override
      public List<Address> generateRecipients() {
         if (recipients == null) {
            recipients = cdl.getOwners(key);
         }
         return recipients;
      }

      @Override
      public Collection<Object> getKeys() {
         return keys;
      }
   }

   class MultipleKeysRecipientGenerator implements RecipientGenerator {

      private final Collection<Object> keys;
      private List<Address> recipients = null;

      MultipleKeysRecipientGenerator(Collection<Object> keys) {
         this.keys = keys;
      }

      @Override
      public List<Address> generateRecipients() {
         if (recipients == null) {
            recipients = cdl.getOwners(keys);
         }
         return recipients;
      }

      @Override
      public Collection<Object> getKeys() {
         return keys;
      }
   }
}


File: core/src/main/java/org/infinispan/interceptors/distribution/NonTxDistributionInterceptor.java
package org.infinispan.interceptors.distribution;

import org.infinispan.commands.FlagAffectedCommand;
import org.infinispan.commands.read.AbstractDataCommand;
import org.infinispan.commands.read.GetCacheEntryCommand;
import org.infinispan.commands.read.GetKeyValueCommand;
import org.infinispan.commands.read.RemoteFetchingCommand;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.commands.write.PutMapCommand;
import org.infinispan.commands.write.RemoveCommand;
import org.infinispan.commands.write.ReplaceCommand;
import org.infinispan.commands.write.WriteCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.util.concurrent.CompositeNotifyingFuture;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.distribution.util.ReadOnlySegmentAwareMap;
import org.infinispan.remoting.RemoteException;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.rpc.RpcOptions;
import org.infinispan.remoting.transport.Address;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Non-transactional interceptor used by distributed caches that support concurrent writes.
 * It is implemented based on lock forwarding. E.g.
 * - 'k' is written on node A, owners(k)={B,C}
 * - A forwards the given command to B
 * - B acquires a lock on 'k' then it forwards it to the remaining owners: C
 * - C applies the change and returns to B (no lock acquisition is needed)
 * - B applies the result as well, releases the lock and returns the result of the operation to A.
 * <p/>
 * Note that even though this introduces an additional RPC (the forwarding), it behaves very well in conjunction with
 * consistent-hash aware hotrod clients which connect directly to the lock owner.
 *
 * @author Mircea Markus
 * @since 5.2
 */
public class NonTxDistributionInterceptor extends BaseDistributionInterceptor {

   private static Log log = LogFactory.getLog(NonTxDistributionInterceptor.class);
   private static final boolean trace = log.isTraceEnabled();

   @Override
   public Object visitGetKeyValueCommand(InvocationContext ctx, GetKeyValueCommand command) throws Throwable {
      return visitRemoteFetchingCommand(ctx, command, false);
   }

   @Override
   public Object visitGetCacheEntryCommand(InvocationContext ctx, GetCacheEntryCommand command) throws Throwable {
      return visitRemoteFetchingCommand(ctx, command, true);
   }

   private <T extends AbstractDataCommand & RemoteFetchingCommand> Object visitRemoteFetchingCommand(InvocationContext ctx, T command, boolean returnEntry) throws Throwable {
      Object returnValue = invokeNextInterceptor(ctx, command);
      if (returnValue == null) {
         Object key = command.getKey();
         if (needsRemoteGet(ctx, command)) {
            InternalCacheEntry remoteEntry = remoteGetCacheEntry(ctx, key, command);
            returnValue = computeGetReturn(remoteEntry, returnEntry);
         }
         if (returnValue == null) {
            InternalCacheEntry localEntry = fetchValueLocallyIfAvailable(dm.getReadConsistentHash(), key);
            if (localEntry != null) {
               wrapInternalCacheEntry(localEntry, ctx, key, false, command);
            }
            returnValue = computeGetReturn(localEntry, returnEntry);
         }
      }
      return returnValue;
   }

   private Object computeGetReturn(InternalCacheEntry entry, boolean returnEntry) {
      if (!returnEntry && entry != null)
         return entry.getValue();
      return entry;
   }

   @Override
   public Object visitPutKeyValueCommand(InvocationContext ctx, PutKeyValueCommand command) throws Throwable {
      return handleNonTxWriteCommand(ctx, command);
   }

   @Override
   public Object visitPutMapCommand(InvocationContext ctx, PutMapCommand command) throws Throwable {
      Map<Object, Object> originalMap = command.getMap();
      ConsistentHash ch = dm.getConsistentHash();
      Address localAddress = rpcManager.getAddress();
      if (ctx.isOriginLocal()) {
         List<CompletableFuture<Map<Address, Response>>> futures = new ArrayList<>(
               rpcManager.getMembers().size() - 1);
         // TODO: if async we don't need to do futures...
         RpcOptions options = rpcManager.getDefaultRpcOptions(isSynchronous(command));
         for (Address member : rpcManager.getMembers()) {
            if (member.equals(rpcManager.getAddress())) {
               continue;
            }
            Set<Integer> segments = ch.getPrimarySegmentsForOwner(member);
            if (!segments.isEmpty()) {
               Map<Object, Object> segmentEntriesMap =
                     new ReadOnlySegmentAwareMap<>(originalMap, ch, segments);
               if (!segmentEntriesMap.isEmpty()) {
                  PutMapCommand copy = new PutMapCommand(command);
                  copy.setMap(segmentEntriesMap);
                  CompletableFuture<Map<Address, Response>> future = rpcManager.invokeRemotelyAsync(
                        Collections.singletonList(member), copy, options);
                  futures.add(future);
               }
            }
         }
         if (futures.size() > 0) {
            CompletableFuture[] futuresArray = new CompletableFuture[futures.size()];
            CompletableFuture<Void> compFuture = CompletableFuture.allOf(futures.toArray(futuresArray));
            try {
               compFuture.get(options.timeout(), TimeUnit.MILLISECONDS);
            } catch (ExecutionException e) {
               throw new RemoteException("Exception while processing put on primary owner", e.getCause());
            } catch (TimeoutException e) {
               throw new CacheException(e);
            }
         }
      }

      if (!command.isForwarded() && ch.getNumOwners() > 1) {
         // Now we find all the segments that we own and map our backups to those
         Map<Address, Set<Integer>> backupOwnerSegments = new HashMap<>();
         int segmentCount = ch.getNumSegments();
         for (int i = 0; i < segmentCount; ++i) {
            Iterator<Address> iter = ch.locateOwnersForSegment(i).iterator();

            if (iter.next().equals(localAddress)) {
               while (iter.hasNext()) {
                  Address backupOwner = iter.next();
                  Set<Integer> segments = backupOwnerSegments.get(backupOwner);
                  if (segments == null) {
                     backupOwnerSegments.put(backupOwner, (segments = new HashSet<>()));
                  }
                  segments.add(i);
               }
            }
         }

         int backupOwnerSize = backupOwnerSegments.size();
         if (backupOwnerSize > 0) {
            List<CompletableFuture<Map<Address, Response>>> futures = new ArrayList<>(backupOwnerSize);
            RpcOptions options = rpcManager.getDefaultRpcOptions(isSynchronous(command));
            command.setFlags(Flag.SKIP_LOCKING);
            command.setForwarded(true);

            for (Entry<Address, Set<Integer>> entry : backupOwnerSegments.entrySet()) {
               Set<Integer> segments = entry.getValue();
               Map<Object, Object> segmentEntriesMap = 
                     new ReadOnlySegmentAwareMap<>(originalMap, ch, segments);
               if (!segmentEntriesMap.isEmpty()) {
                  PutMapCommand copy = new PutMapCommand(command);
                  copy.setMap(segmentEntriesMap);
                  CompletableFuture<Map<Address, Response>> future = rpcManager.invokeRemotelyAsync(
                        Collections.singletonList(entry.getKey()), copy, options);
                  futures.add(future);
               }
            }
            command.setForwarded(false);
            if (futures.size() > 0) {
               CompletableFuture[] futuresArray = new CompletableFuture[futures.size()];
               CompletableFuture<Void> compFuture = CompletableFuture.allOf(futures.toArray(futuresArray));
               try {
                  compFuture.get(options.timeout(), TimeUnit.MILLISECONDS);
               } catch (ExecutionException e) {
                  throw new RemoteException("Exception while processing put on backup owner", e.getCause());
               } catch (TimeoutException e) {
                  throw new CacheException(e);
               }
            }
         }
      }

      return invokeNextInterceptor(ctx, command);
   }

   @Override
   public Object visitRemoveCommand(InvocationContext ctx, RemoveCommand command) throws Throwable {
      return handleNonTxWriteCommand(ctx, command);
   }

   @Override
   public Object visitReplaceCommand(InvocationContext ctx, ReplaceCommand command) throws Throwable {
      return handleNonTxWriteCommand(ctx, command);
   }

   protected void remoteGetBeforeWrite(InvocationContext ctx, WriteCommand command, RecipientGenerator keygen) throws Throwable {
      for (Object k : keygen.getKeys()) {
         if (cdl.localNodeIsPrimaryOwner(k)) {
            // Then it makes sense to try a local get and wrap again. This will compensate the fact the the entry was not local
            // earlier when the EntryWrappingInterceptor executed during current invocation context but it should be now.
            localGetCacheEntry(ctx, k, true, command);
         }
      }
   }

   private InternalCacheEntry localGetCacheEntry(InvocationContext ctx, Object key, boolean isWrite, FlagAffectedCommand command) throws Throwable {
      InternalCacheEntry ice = dataContainer.get(key);
      if (ice != null) {
         wrapInternalCacheEntry(ice, ctx, key, isWrite, command);
         return ice;
      }
      return null;
   }

   private void wrapInternalCacheEntry(InternalCacheEntry ice, InvocationContext ctx, Object key, boolean isWrite,
                                       FlagAffectedCommand command) {
      if (!ctx.replaceValue(key, ice))  {
         if (isWrite)
            entryFactory.wrapEntryForPut(ctx, key, ice, false, command, true);
         else
            ctx.putLookedUpEntry(key, ice);
      }
   }

   private <T extends FlagAffectedCommand & RemoteFetchingCommand> InternalCacheEntry remoteGetCacheEntry(InvocationContext ctx, Object key, T command) throws Throwable {
      if (trace) log.tracef("Doing a remote get for key %s", key);
      InternalCacheEntry ice = retrieveFromRemoteSource(key, ctx, false, command, false);
      command.setRemotelyFetchedValue(ice);
      return ice;
   }

   protected boolean needValuesFromPreviousOwners(InvocationContext ctx, WriteCommand command) {
      if (command.hasFlag(Flag.PUT_FOR_STATE_TRANSFER)) return false;
      if (command.hasFlag(Flag.DELTA_WRITE) && !command.hasFlag(Flag.CACHE_MODE_LOCAL)) return true;

      // The return value only matters on the primary owner.
      // The conditional commands also check the previous value only on the primary owner.
      // Note: This should not be necessary, as the primary owner always has the previous value
      if (isNeedReliableReturnValues(command) || command.isConditional()) {
         for (Object key : command.getAffectedKeys()) {
            if (cdl.localNodeIsPrimaryOwner(key)) return true;
         }
      }
      return false;
   }
}


File: core/src/main/java/org/infinispan/interceptors/distribution/TxDistributionInterceptor.java
package org.infinispan.interceptors.distribution;

import org.infinispan.commands.FlagAffectedCommand;
import org.infinispan.commands.TopologyAffectedCommand;
import org.infinispan.commands.control.LockControlCommand;
import org.infinispan.commands.read.AbstractDataCommand;
import org.infinispan.commands.read.GetCacheEntryCommand;
import org.infinispan.commands.read.GetKeyValueCommand;
import org.infinispan.commands.read.GetAllCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.commands.tx.RollbackCommand;
import org.infinispan.commands.tx.TransactionBoundaryCommand;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.commands.write.PutMapCommand;
import org.infinispan.commands.write.RemoveCommand;
import org.infinispan.commands.write.ReplaceCommand;
import org.infinispan.commands.write.ValueMatcher;
import org.infinispan.commands.write.WriteCommand;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.impl.LocalTxInvocationContext;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.factories.annotations.Start;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.responses.CacheNotFoundResponse;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.responses.UnsureResponse;
import org.infinispan.remoting.rpc.ResponseMode;
import org.infinispan.remoting.rpc.RpcOptions;
import org.infinispan.remoting.transport.Address;
import org.infinispan.remoting.transport.jgroups.SuspectException;
import org.infinispan.statetransfer.OutdatedTopologyException;
import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.impl.LocalTransaction;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;
import org.jgroups.demos.Topology;

import java.util.Collection;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.concurrent.TimeoutException;

import static org.infinispan.commons.util.Util.toStr;
import static org.infinispan.util.DeltaCompositeKeyUtil.filterDeltaCompositeKey;
import static org.infinispan.util.DeltaCompositeKeyUtil.filterDeltaCompositeKeys;
import static org.infinispan.util.DeltaCompositeKeyUtil.getAffectedKeysFromContext;

/**
 * Handles the distribution of the transactional caches.
 *
 * @author Mircea Markus
 * @since 5.2
 */
public class TxDistributionInterceptor extends BaseDistributionInterceptor {

   private static Log log = LogFactory.getLog(TxDistributionInterceptor.class);
   private static final boolean trace = log.isTraceEnabled();

   private boolean isPessimisticCache;
   private boolean useClusteredWriteSkewCheck;

   @Override
   public Object visitReplaceCommand(InvocationContext ctx, ReplaceCommand command) throws Throwable {
      try {
         return handleTxWriteCommand(ctx, command, new SingleKeyRecipientGenerator(command.getKey()), false);
      } finally {
         if (ctx.isOriginLocal()) {
            // If the state transfer interceptor has to retry the command, it should ignore the previous value.
            command.setValueMatcher(command.isSuccessful() ? ValueMatcher.MATCH_ALWAYS : ValueMatcher.MATCH_NEVER);
         }
      }
   }

   @Override
   public Object visitRemoveCommand(InvocationContext ctx, RemoveCommand command) throws Throwable {
      try {
         return handleTxWriteCommand(ctx, command, new SingleKeyRecipientGenerator(command.getKey()), false);
      } finally {
         if (ctx.isOriginLocal()) {
            // If the state transfer interceptor has to retry the command, it should ignore the previous value.
            command.setValueMatcher(command.isSuccessful() ? ValueMatcher.MATCH_ALWAYS : ValueMatcher.MATCH_NEVER);
         }
      }
   }

   @Start
   public void start() {
      isPessimisticCache = cacheConfiguration.transaction().lockingMode() == LockingMode.PESSIMISTIC;
      useClusteredWriteSkewCheck = !isPessimisticCache &&
            cacheConfiguration.versioning().enabled() && cacheConfiguration.locking().writeSkewCheck();
   }

   @Override
   public Object visitPutKeyValueCommand(InvocationContext ctx, PutKeyValueCommand command) throws Throwable {
      if (command.hasFlag(Flag.PUT_FOR_EXTERNAL_READ)) {
         return handleNonTxWriteCommand(ctx, command);
      }

      SingleKeyRecipientGenerator skrg = new SingleKeyRecipientGenerator(command.getKey());
      Object returnValue = handleTxWriteCommand(ctx, command, skrg, command.hasFlag(Flag.PUT_FOR_STATE_TRANSFER));
      if (ctx.isOriginLocal()) {
         // If the state transfer interceptor has to retry the command, it should ignore the previous value.
         command.setValueMatcher(command.isSuccessful() ? ValueMatcher.MATCH_ALWAYS : ValueMatcher.MATCH_NEVER);
      }
      return returnValue;
   }

   @Override
   public Object visitPutMapCommand(InvocationContext ctx, PutMapCommand command) throws Throwable {
      // don't bother with a remote get for the PutMapCommand!
      return handleTxWriteCommand(ctx, command, new MultipleKeysRecipientGenerator(command.getMap().keySet()), true);
   }

   @Override
   public Object visitGetKeyValueCommand(InvocationContext ctx, GetKeyValueCommand command) throws Throwable {
      try {
         return visitGetCommand(ctx, command, false);
      } catch (SuspectException e) {
         // retry
         return visitGetKeyValueCommand(ctx, command);
      }
   }

   @Override
   public Object visitGetCacheEntryCommand(InvocationContext ctx, GetCacheEntryCommand command) throws Throwable {
      try {
         return visitGetCommand(ctx, command, false);
      } catch (SuspectException e) {
         // retry
         return visitGetCacheEntryCommand(ctx, command);
      }
   }

   private Object visitGetCommand(InvocationContext ctx, AbstractDataCommand command,
      boolean isGetCacheEntry) throws Throwable {
      Object returnValue = invokeNextInterceptor(ctx, command);

      //if the cache entry has the value lock flag set, skip the remote get.
      CacheEntry entry = ctx.lookupEntry(command.getKey());
      boolean skipRemoteGet = entry != null && entry.skipLookup();

      // need to check in the context as well since a null retval is not necessarily an indication of the entry not being
      // available.  It could just have been removed in the same tx beforehand.  Also don't bother with a remote get if
      // the entry is mapped to the local node.
      if (!skipRemoteGet && returnValue == null && ctx.isOriginLocal()) {
         Object key = filterDeltaCompositeKey(command.getKey());
         if (needsRemoteGet(ctx, command)) {
            InternalCacheEntry ice = remoteGet(ctx, key, false, command);
            if (ice != null) {
               returnValue = ice.getValue();
            }
         }
         if (returnValue == null && !ctx.isEntryRemovedInContext(command.getKey())) {
            returnValue = localGet(ctx, key, false, command, isGetCacheEntry);
         }
      }
      return returnValue;
   }

   protected void lockAndWrap(InvocationContext ctx, Object key, InternalCacheEntry ice, FlagAffectedCommand command) throws InterruptedException {
      boolean skipLocking = hasSkipLocking(command);
      long lockTimeout = getLockAcquisitionTimeout(command, skipLocking);
      lockManager.acquireLock(ctx, key, lockTimeout, skipLocking);
      entryFactory.wrapEntryForPut(ctx, key, ice, false, command, false);
   }

   @Override
   public Object visitLockControlCommand(TxInvocationContext ctx, LockControlCommand command) throws Throwable {
      if (ctx.isOriginLocal()) {
         //In Pessimistic mode, the delta composite keys were sent to the wrong owner and never locked.
         final Collection<Address> affectedNodes = cdl.getOwners(filterDeltaCompositeKeys(command.getKeys()));
         ((LocalTxInvocationContext) ctx).remoteLocksAcquired(affectedNodes == null ? dm.getConsistentHash()
               .getMembers() : affectedNodes);
         log.tracef("Registered remote locks acquired %s", affectedNodes);
         RpcOptions rpcOptions = rpcManager.getRpcOptionsBuilder(ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS, DeliverOrder.NONE).build();
         Map<Address, Response> responseMap = rpcManager.invokeRemotely(affectedNodes, command, rpcOptions);
         checkTxCommandResponses(responseMap, command);
      }
      return invokeNextInterceptor(ctx, command);
   }

   // ---- TX boundary commands
   @Override
   public Object visitCommitCommand(TxInvocationContext ctx, CommitCommand command) throws Throwable {
      if (shouldInvokeRemoteTxCommand(ctx)) {
         sendCommitCommand(ctx, command);
      }
      return invokeNextInterceptor(ctx, command);
   }

   @Override
   public Object visitPrepareCommand(TxInvocationContext ctx, PrepareCommand command) throws Throwable {
      Object retVal = invokeNextInterceptor(ctx, command);

      if (shouldInvokeRemoteTxCommand(ctx)) {
         Collection<Address> recipients = cdl.getOwners(getAffectedKeysFromContext(ctx));
         prepareOnAffectedNodes(ctx, command, recipients, defaultSynchronous);
         ((LocalTxInvocationContext) ctx).remoteLocksAcquired(recipients == null ? dm.getWriteConsistentHash()
               .getMembers() : recipients);
      }
      return retVal;
   }

   protected void prepareOnAffectedNodes(TxInvocationContext<?> ctx, PrepareCommand command, Collection<Address> recipients, boolean sync) {
      try {
         // this method will return immediately if we're the only member (because exclude_self=true)
         RpcOptions rpcOptions;
         if (sync) {
            rpcOptions = rpcManager.getRpcOptionsBuilder(ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS, DeliverOrder.NONE).build();
         } else {
            rpcOptions = rpcManager.getDefaultRpcOptions(false);
         }
         Map<Address, Response> responseMap = rpcManager.invokeRemotely(recipients, command, rpcOptions);
         checkTxCommandResponses(responseMap, command);
      } finally {
         transactionRemotelyPrepared(ctx);
      }
   }

   @Override
   public Object visitRollbackCommand(TxInvocationContext ctx, RollbackCommand command) throws Throwable {
      if (shouldInvokeRemoteTxCommand(ctx)) {
         boolean syncRollback = cacheConfiguration.transaction().syncRollbackPhase();
         ResponseMode responseMode = syncRollback ? ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS : ResponseMode.ASYNCHRONOUS;
         RpcOptions rpcOptions = rpcManager.getRpcOptionsBuilder(responseMode, DeliverOrder.NONE).build();
         Collection<Address> recipients = getCommitNodes(ctx);
         Map<Address, Response> responseMap = rpcManager.invokeRemotely(recipients, command, rpcOptions);
         checkTxCommandResponses(responseMap, command);
      }

      return invokeNextInterceptor(ctx, command);
   }

   private Collection<Address> getCommitNodes(TxInvocationContext ctx) {
      LocalTransaction localTx = (LocalTransaction) ctx.getCacheTransaction();
      Collection<Address> affectedNodes = cdl.getOwners(getAffectedKeysFromContext(ctx));
      List<Address> members = dm.getConsistentHash().getMembers();
      return localTx.getCommitNodes(affectedNodes, rpcManager.getTopologyId(), members);
   }

   private void sendCommitCommand(TxInvocationContext ctx, CommitCommand command) throws TimeoutException, InterruptedException {
      Collection<Address> recipients = getCommitNodes(ctx);
      boolean syncCommitPhase = cacheConfiguration.transaction().syncCommitPhase();
      RpcOptions rpcOptions;
      if (syncCommitPhase) {
         rpcOptions = rpcManager.getRpcOptionsBuilder(ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS, DeliverOrder.NONE).build();
      } else {
         rpcOptions = rpcManager.getDefaultRpcOptions(false, DeliverOrder.NONE);
      }
      Map<Address, Response> responseMap = rpcManager.invokeRemotely(recipients, command, rpcOptions);
      checkTxCommandResponses(responseMap, command);
   }

   protected void checkTxCommandResponses(Map<Address, Response> responseMap, TransactionBoundaryCommand command) {
      for (Map.Entry<Address, Response> e : responseMap.entrySet()) {
         Address recipient = e.getKey();
         Response response = e.getValue();
         if (response instanceof CacheNotFoundResponse) {
            // No need to retry if the missing node wasn't a member when the command started.
            if (command.getTopologyId() == stateTransferManager.getCacheTopology().getTopologyId()
                  && !rpcManager.getMembers().contains(recipient)) {
               log.tracef("Ignoring response from node not targeted %s", recipient);
            } else {
               log.tracef("Cache not running on node %s, or the node is missing", recipient);
               throw new OutdatedTopologyException("Cache not running on node " + recipient);
            }
         } else if (response instanceof UnsureResponse) {
            log.tracef("Node %s has a newer topology id", recipient);
            throw new OutdatedTopologyException("Cache not running on node " + recipient);
         }
      }
   }

   private boolean shouldFetchRemoteValuesForWriteSkewCheck(InvocationContext ctx, WriteCommand cmd) {
      // Note: the primary owner always already has the data, so this method is always going to return false
      if (useClusteredWriteSkewCheck && ctx.isInTxScope() && dm.isRehashInProgress()) {
         for (Object key : cmd.getAffectedKeys()) {
            // TODO Dan: Do we need a special check for total order?
            boolean shouldPerformWriteSkewCheck = cdl.localNodeIsPrimaryOwner(key);
            // TODO Dan: remoteGet() already checks if the key is available locally or not
            if (shouldPerformWriteSkewCheck && dm.isAffectedByRehash(key) && !dataContainer.containsKey(key)) return true;
         }
      }
      return false;
   }

   /**
    * If we are within one transaction we won't do any replication as replication would only be performed at commit
    * time. If the operation didn't originate locally we won't do any replication either.
    */
   private Object handleTxWriteCommand(InvocationContext ctx, WriteCommand command, RecipientGenerator recipientGenerator, boolean skipRemoteGet) throws Throwable {
      // see if we need to load values from remote sources first
      if (!skipRemoteGet && needValuesFromPreviousOwners(ctx, command))
         remoteGetBeforeWrite(ctx, command, recipientGenerator);

      // FIRST pass this call up the chain.  Only if it succeeds (no exceptions) locally do we attempt to distribute.
      return invokeNextInterceptor(ctx, command);
   }

   @Override
   protected boolean needValuesFromPreviousOwners(InvocationContext ctx, WriteCommand command) {
      if (ctx.isOriginLocal()) {
         // The return value only matters on the originator.
         // Conditional commands also check the previous value only on the originator.
         if (isNeedReliableReturnValues(command) || command.isConditional())
            return true;
      }
      return !command.hasFlag(Flag.CACHE_MODE_LOCAL) && (shouldFetchRemoteValuesForWriteSkewCheck(ctx, command) || command.hasFlag(Flag.DELTA_WRITE));
   }

   private Object localGet(InvocationContext ctx, Object key, boolean isWrite,
         FlagAffectedCommand command, boolean isGetCacheEntry) throws Throwable {
      InternalCacheEntry ice = fetchValueLocallyIfAvailable(dm.getReadConsistentHash(), key);
      if (ice != null) {
         if (isWrite && isPessimisticCache && ctx.isInTxScope()) {
            ((TxInvocationContext) ctx).addAffectedKey(key);
         }
         if (!ctx.replaceValue(key, ice)) {
            if (isWrite)
               lockAndWrap(ctx, key, ice, command);
            else
               ctx.putLookedUpEntry(key, ice);
         }
         return isGetCacheEntry ? ice : ice.getValue();
      }
      return null;
   }

   protected void remoteGetBeforeWrite(InvocationContext ctx, WriteCommand command, RecipientGenerator keygen) throws Throwable {
      for (Object k : keygen.getKeys()) {
         CacheEntry entry = ctx.lookupEntry(k);
         boolean skipRemoteGet =  entry != null && entry.skipLookup();
         if (skipRemoteGet) {
            continue;
         }
         InternalCacheEntry ice = remoteGet(ctx, k, true, command);
         if (ice == null) {
            localGet(ctx, k, true, command, false);
         }
      }
   }

   private InternalCacheEntry remoteGet(InvocationContext ctx, Object key, boolean isWrite, FlagAffectedCommand command) throws Throwable {
      if (ctx.isOriginLocal() && !isValueAvailableLocally(dm.getReadConsistentHash(), key) || dm.isAffectedByRehash(key) && !dataContainer.containsKey(key)) {
         if (trace) log.tracef("Doing a remote get for key %s", key);

         boolean acquireRemoteLock = false;
         if (ctx.isInTxScope() && ctx.isOriginLocal()) {
            TxInvocationContext txContext = (TxInvocationContext) ctx;
            acquireRemoteLock = isWrite && isPessimisticCache && !txContext.getAffectedKeys().contains(key);
         }
         // attempt a remote lookup
         InternalCacheEntry ice = retrieveFromRemoteSource(key, ctx, acquireRemoteLock, command, isWrite);

         if (acquireRemoteLock) {
            ((TxInvocationContext) ctx).addAffectedKey(key);
         }

         if (ice != null) {
            if (useClusteredWriteSkewCheck && ctx.isInTxScope()) {
               ((TxInvocationContext)ctx).getCacheTransaction().putLookedUpRemoteVersion(key, ice.getMetadata().version());
            }

            if (!ctx.replaceValue(key, ice)) {
               if (isWrite)
                  lockAndWrap(ctx, key, ice, command);
               else {
                  ctx.putLookedUpEntry(key, ice);
                  if (ctx.isInTxScope()) {
                     ((TxInvocationContext) ctx).getCacheTransaction().replaceVersionRead(key, ice.getMetadata().version());
                  }
               }
            }
            return ice;
         }
      } else {
         if (trace) log.tracef("Not doing a remote get for key %s since entry is mapped to current node (%s), or is in L1.  Owners are %s", key, rpcManager.getAddress(), dm.locate(key));
      }
      return null;
   }
}


File: core/src/main/java/org/infinispan/interceptors/distribution/VersionedDistributionInterceptor.java
package org.infinispan.interceptors.distribution;

import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.rpc.ResponseMode;
import org.infinispan.remoting.rpc.RpcOptions;
import org.infinispan.remoting.transport.Address;
import org.infinispan.transaction.xa.CacheTransaction;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.Collection;
import java.util.Map;

import static org.infinispan.transaction.impl.WriteSkewHelper.readVersionsFromResponse;

/**
 * A version of the {@link TxDistributionInterceptor} that adds logic to handling prepares when entries are versioned.
 *
 * @author Manik Surtani
 * @since 5.1
 */
public class VersionedDistributionInterceptor extends TxDistributionInterceptor {

   private static final Log log = LogFactory.getLog(VersionedDistributionInterceptor.class);

   @Override
   protected Log getLog() {
      return log;
   }

   @Override
   protected void prepareOnAffectedNodes(TxInvocationContext<?> ctx, PrepareCommand command, Collection<Address> recipients, boolean ignored) {
      // Perform the RPC
      try {
         RpcOptions rpcOptions = rpcManager.getRpcOptionsBuilder(ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS, DeliverOrder.NONE).build();
         Map<Address, Response> resps = rpcManager.invokeRemotely(recipients, command, rpcOptions);
         checkTxCommandResponses(resps, command);

         // Now store newly generated versions from lock owners for use during the commit phase.
         CacheTransaction ct = ctx.getCacheTransaction();
         for (Response r : resps.values()) readVersionsFromResponse(r, ct);
      } finally {
         transactionRemotelyPrepared(ctx);
      }
   }
}


File: core/src/main/java/org/infinispan/interceptors/locking/AbstractTxLockingInterceptor.java
package org.infinispan.interceptors.locking;

import static org.infinispan.commons.util.Util.toStr;

import java.util.Collection;
import java.util.concurrent.TimeUnit;

import org.infinispan.atomic.DeltaCompositeKey;
import org.infinispan.commands.read.GetCacheEntryCommand;
import org.infinispan.commands.read.GetAllCommand;
import org.infinispan.commands.read.GetKeyValueCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.commands.tx.RollbackCommand;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.configuration.cache.Configurations;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.statetransfer.OutdatedTopologyException;
import org.infinispan.transaction.impl.LocalTransaction;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.xa.CacheTransaction;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.util.TimeService;
import org.infinispan.util.concurrent.TimeoutException;
import org.infinispan.util.logging.Log;

/**
 * Base class for transaction based locking interceptors.
 *
 * @author Mircea.Markus@jboss.com
 * @since 5.1
 */
public abstract class AbstractTxLockingInterceptor extends AbstractLockingInterceptor {

   protected TransactionTable txTable;
   protected RpcManager rpcManager;
   private boolean clustered;
   private TimeService timeService;

   @Inject
   @SuppressWarnings("unused")
   public void setDependencies(TransactionTable txTable, RpcManager rpcManager, TimeService timeService) {
      this.txTable = txTable;
      this.rpcManager = rpcManager;
      clustered = rpcManager != null;
      this.timeService = timeService;
   }

   @Override
   public Object visitRollbackCommand(TxInvocationContext ctx, RollbackCommand command) throws Throwable {
      try {
         return invokeNextInterceptor(ctx, command);
      } finally {
         lockManager.unlockAll(ctx);
      }
   }

   @Override
   public Object visitPutKeyValueCommand(InvocationContext ctx, PutKeyValueCommand command) throws Throwable {
      if (command.hasFlag(Flag.PUT_FOR_EXTERNAL_READ)) {
         // Cache.putForExternalRead() is non-transactional
         return visitNonTxDataWriteCommand(ctx, command);
      }
      return visitDataWriteCommand(ctx, command);
   }

   @Override
   public Object visitGetAllCommand(InvocationContext ctx, GetAllCommand command) throws Throwable {
      try {
         return super.visitGetAllCommand(ctx, command);
      } finally {
         //when not invoked in an explicit tx's scope the get is non-transactional(mainly for efficiency).
         //locks need to be released in this situation as they might have been acquired from L1.
         if (!ctx.isInTxScope()) lockManager.unlockAll(ctx);
      }
   }

   @Override
   public Object visitCommitCommand(TxInvocationContext ctx, CommitCommand command) throws Throwable {
      boolean releaseLocks = releaseLockOnTxCompletion(ctx);
      try {
         return super.visitCommitCommand(ctx, command);
      } catch (OutdatedTopologyException e) {
         releaseLocks = false;
         throw e;
      } finally {
         if (releaseLocks) lockManager.unlockAll(ctx);
      }
   }

   protected final Object invokeNextAndCommitIf1Pc(TxInvocationContext ctx, PrepareCommand command) throws Throwable {
      Object result = invokeNextInterceptor(ctx, command);
      if (command.isOnePhaseCommit() && releaseLockOnTxCompletion(ctx)) {
         lockManager.unlockAll(ctx);
      }
      return result;
   }

   /**
    * The backup (non-primary) owners keep a "backup lock" for each key they received in a lock/prepare command.
    * Normally there can be many transactions holding the backup lock at the same time, but when the secondary owner
    * becomes a primary owner a new transaction trying to obtain the "real" lock will have to wait for all backup
    * locks to be released. The backup lock will be released either by a commit/rollback/unlock command or by
    * the originator leaving the cluster (if recovery is disabled).
    */
   protected final void lockAndRegisterBackupLock(TxInvocationContext ctx, Object key, long lockTimeout, boolean skipLocking) throws InterruptedException {
      //with DeltaCompositeKey, the locks should be acquired in the owner of the delta aware key.
      Object keyToCheck = key instanceof DeltaCompositeKey ?
            ((DeltaCompositeKey) key).getDeltaAwareValueKey() :
            key;
      if (cdl.localNodeIsPrimaryOwner(keyToCheck)) {
         lockKeyAndCheckOwnership(ctx, key, lockTimeout, skipLocking);
      } else if (cdl.localNodeIsOwner(keyToCheck)) {
         ctx.getCacheTransaction().addBackupLockForKey(key);
      }
   }

   /**
    * Besides acquiring a lock, this method also handles the following situation:
    * 1. consistentHash("k") == {A, B}, tx1 prepared on A and B. Then node A crashed (A  == single lock owner)
    * 2. at this point tx2 which also writes "k" tries to prepare on B.
    * 3. tx2 has to determine that "k" is already locked by another tx (i.e. tx1) and it has to wait for that tx to finish before acquiring the lock.
    *
    * The algorithm used at step 3 is:
    * - the transaction table(TT) associates the current topology id with every remote and local transaction it creates
    * - TT also keeps track of the minimal value of all the topology ids of all the transactions still present in the cache (minTopologyId)
    * - when a tx wants to acquire lock "k":
    *    - if tx.topologyId > TT.minTopologyId then "k" might be a key whose owner crashed. If so:
    *       - obtain the list LT of transactions that started in a previous topology (txTable.getTransactionsPreparedBefore)
    *       - for each t in LT:
    *          - if t wants to write "k" then block until t finishes (CacheTransaction.waitForTransactionsToFinishIfItWritesToKey)
    *       - only then try to acquire lock on "k"
    *    - if tx.topologyId == TT.minTopologyId try to acquire lock straight away.
    *
    * Note: The algorithm described below only when nodes leave the cluster, so it doesn't add a performance burden
    * when the cluster is stable.
    */
   protected final void lockKeyAndCheckOwnership(InvocationContext ctx, Object key, long lockTimeout, boolean skipLocking) throws InterruptedException {
      TxInvocationContext txContext = (TxInvocationContext) ctx;
      int transactionTopologyId = -1;
      boolean checkForPendingLocks = false;
      if (clustered) {
         CacheTransaction tx = txContext.getCacheTransaction();
         boolean isFromStateTransfer = txContext.isOriginLocal() && ((LocalTransaction)tx).isFromStateTransfer();
         // if the transaction is from state transfer it should not wait for the backup locks of other transactions
         if (!isFromStateTransfer) {
            transactionTopologyId = tx.getTopologyId();
            if (transactionTopologyId != TransactionTable.CACHE_STOPPED_TOPOLOGY_ID) {
               checkForPendingLocks = txTable.getMinTopologyId() < transactionTopologyId;
            }
         }
      }

      Log log = getLog();
      boolean trace = log.isTraceEnabled();
      if (checkForPendingLocks) {
         if (trace)
            log.tracef("Checking for pending locks and then locking key %s", toStr(key));

         final long expectedEndTime = timeService.expectedEndTime(cacheConfiguration.locking().lockAcquisitionTimeout(),
                                                                  TimeUnit.MILLISECONDS);

         // Check local transactions first
         waitForTransactionsToComplete(txContext, txTable.getLocalTransactions(), key, transactionTopologyId, expectedEndTime);

         // ... then remote ones
         waitForTransactionsToComplete(txContext, txTable.getRemoteTransactions(), key, transactionTopologyId, expectedEndTime);

         // Then try to acquire a lock
         if (trace)
            log.tracef("Finished waiting for other potential lockers, trying to acquire the lock on %s", toStr(key));

         final long remaining = timeService.remainingTime(expectedEndTime, TimeUnit.MILLISECONDS);
         lockManager.acquireLock(ctx, key, remaining, skipLocking);
      } else {
         if (trace)
            log.tracef("Locking key %s, no need to check for pending locks.", toStr(key));

         lockManager.acquireLock(ctx, key, lockTimeout, skipLocking);
      }
   }

   private void waitForTransactionsToComplete(TxInvocationContext txContext, Collection<? extends CacheTransaction> transactions,
                                              Object key, int transactionTopologyId, long expectedEndTime) throws InterruptedException {
      GlobalTransaction thisTransaction = txContext.getGlobalTransaction();
      for (CacheTransaction tx : transactions) {
         if (tx.getTopologyId() < transactionTopologyId) {
            // don't wait for the current transaction
            if (tx.getGlobalTransaction().equals(thisTransaction))
               continue;

            boolean txCompleted = false;

            long remaining;
            while ((remaining = timeService.remainingTime(expectedEndTime, TimeUnit.MILLISECONDS)) > 0) {
               if (tx.waitForLockRelease(key, remaining)) {
                  txCompleted = true;
                  break;
               }
            }

            if (!txCompleted) {
               throw newTimeoutException(key, tx, txContext);
            }
         }
      }
   }

   private TimeoutException newTimeoutException(Object key, TxInvocationContext txContext) {
      return new TimeoutException("Could not acquire lock on " + key + " on behalf of transaction " +
                                       txContext.getGlobalTransaction() + "." + "Lock is being held by " + lockManager.getOwner(key));
   }
   
   private TimeoutException newTimeoutException(Object key, CacheTransaction tx, TxInvocationContext txContext) {                  
      return new TimeoutException("Could not acquire lock on " + key + " on behalf of transaction " +
                                       txContext.getGlobalTransaction() + ". Waiting to complete tx: " + tx + ".");
   }

   private boolean releaseLockOnTxCompletion(TxInvocationContext ctx) {
      return ctx.isOriginLocal() || Configurations.isSecondPhaseAsync(cacheConfiguration);
   }
}


File: core/src/main/java/org/infinispan/interceptors/totalorder/TotalOrderDistributionInterceptor.java
package org.infinispan.interceptors.totalorder;

import org.infinispan.commands.FlagAffectedCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.commands.tx.RollbackCommand;
import org.infinispan.configuration.cache.Configurations;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.interceptors.distribution.TxDistributionInterceptor;
import org.infinispan.remoting.transport.Address;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.Collection;

/**
 * This interceptor handles distribution of entries across a cluster, as well as transparent lookup, when the total
 * order based protocol is enabled
 *
 * @author Pedro Ruivo
 * @since 5.3
 */
public class TotalOrderDistributionInterceptor extends TxDistributionInterceptor {

   private static final Log log = LogFactory.getLog(TotalOrderDistributionInterceptor.class);

   @Override
   public Object visitRollbackCommand(TxInvocationContext ctx, RollbackCommand command) throws Throwable {
      if (Configurations.isOnePhaseTotalOrderCommit(cacheConfiguration) || !ctx.hasModifications() ||
            !shouldTotalOrderRollbackBeInvokedRemotely(ctx)) {
         return invokeNextInterceptor(ctx, command);
      }
      totalOrderTxRollback(ctx);
      return super.visitRollbackCommand(ctx, command);
   }

   @Override
   public Object visitCommitCommand(TxInvocationContext ctx, CommitCommand command) throws Throwable {
      if (Configurations.isOnePhaseTotalOrderCommit(cacheConfiguration) || !ctx.hasModifications()) {
         return invokeNextInterceptor(ctx, command);
      }
      totalOrderTxCommit(ctx);
      return super.visitCommitCommand(ctx, command);
   }

   @Override
   protected void prepareOnAffectedNodes(TxInvocationContext<?> ctx, PrepareCommand command, Collection<Address> recipients,
                                         boolean sync) {
      if (log.isTraceEnabled()) {
         log.tracef("Total Order Anycast transaction %s with Total Order", command.getGlobalTransaction().globalId());
      }

      if (!ctx.hasModifications()) {
         return;
      }

      if (!ctx.isOriginLocal()) {
         throw new IllegalStateException("Expected a local context while TO-Anycast prepare command");
      }

      try {
         totalOrderPrepare(recipients, command, isSyncCommitPhase() ? null : getSelfDeliverFilter());
      } finally {
         transactionRemotelyPrepared(ctx);
      }
   }

   @Override
   protected void lockAndWrap(InvocationContext ctx, Object key, InternalCacheEntry ice, FlagAffectedCommand command) throws InterruptedException {
      entryFactory.wrapEntryForPut(ctx, key, ice, false, command, true);
   }

   @Override
   protected Log getLog() {
      return log;
   }
}


File: core/src/main/java/org/infinispan/interceptors/totalorder/TotalOrderVersionedDistributionInterceptor.java
package org.infinispan.interceptors.totalorder;

import org.infinispan.commands.FlagAffectedCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.commands.tx.RollbackCommand;
import org.infinispan.commands.tx.VersionedPrepareCommand;
import org.infinispan.commands.write.ClearCommand;
import org.infinispan.configuration.cache.Configurations;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.interceptors.distribution.VersionedDistributionInterceptor;
import org.infinispan.remoting.responses.KeysValidateFilter;
import org.infinispan.remoting.transport.Address;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.Collection;

/**
 * This interceptor is used in total order in distributed mode when the write skew check is enabled. After sending the
 * prepare through TOA (Total Order Anycast), it blocks the execution thread until the transaction outcome is known
 * (i.e., the write skew check passes in all keys owners)
 *
 * @author Pedro Ruivo
 * @since 5.3
 */
public class TotalOrderVersionedDistributionInterceptor extends VersionedDistributionInterceptor {

   private static final Log log = LogFactory.getLog(TotalOrderVersionedDistributionInterceptor.class);

   @Override
   public Object visitRollbackCommand(TxInvocationContext ctx, RollbackCommand command) throws Throwable {
      if (Configurations.isOnePhaseTotalOrderCommit(cacheConfiguration) || !ctx.hasModifications() ||
            !shouldTotalOrderRollbackBeInvokedRemotely(ctx)) {
         return invokeNextInterceptor(ctx, command);
      }
      totalOrderTxRollback(ctx);
      return super.visitRollbackCommand(ctx, command);
   }

   @Override
   public Object visitCommitCommand(TxInvocationContext ctx, CommitCommand command) throws Throwable {
      if (Configurations.isOnePhaseTotalOrderCommit(cacheConfiguration) || !ctx.hasModifications()) {
         return invokeNextInterceptor(ctx, command);
      }
      totalOrderTxCommit(ctx);
      return super.visitCommitCommand(ctx, command);
   }

   @Override
   protected void prepareOnAffectedNodes(TxInvocationContext<?> ctx, PrepareCommand command, Collection<Address> recipients, boolean sync) {
      if (log.isTraceEnabled()) {
         log.tracef("Total Order Anycast transaction %s with Total Order", command.getGlobalTransaction().globalId());
      }

      if (!ctx.hasModifications()) {
         return;
      }

      if (!ctx.isOriginLocal()) {
         throw new IllegalStateException("Expected a local context while TO-Anycast prepare command");
      }

      if (!(command instanceof VersionedPrepareCommand)) {
         throw new IllegalStateException("Expected a Versioned Prepare Command in version aware component");
      }

      try {
         KeysValidateFilter responseFilter = ctx.getCacheTransaction().hasModification(ClearCommand.class) || isSyncCommitPhase() ?
               null : new KeysValidateFilter(rpcManager.getAddress(), ctx.getAffectedKeys());

         totalOrderPrepare(recipients, command, responseFilter);
      } finally {
         transactionRemotelyPrepared(ctx);
      }
   }

   @Override
   protected void lockAndWrap(InvocationContext ctx, Object key, InternalCacheEntry ice, FlagAffectedCommand command) throws InterruptedException {
      entryFactory.wrapEntryForPut(ctx, key, ice, false, command, true);
   }

   @Override
   protected Log getLog() {
      return log;
   }
}


File: core/src/main/java/org/infinispan/partitionhandling/impl/PartitionHandlingInterceptor.java
package org.infinispan.partitionhandling.impl;

import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

import org.infinispan.commands.LocalFlagAffectedCommand;
import org.infinispan.commands.read.AbstractDataCommand;
import org.infinispan.commands.read.EntryRetrievalCommand;
import org.infinispan.commands.read.GetCacheEntryCommand;
import org.infinispan.commands.read.GetKeyValueCommand;
import org.infinispan.commands.read.GetAllCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.commands.write.ApplyDeltaCommand;
import org.infinispan.commands.write.ClearCommand;
import org.infinispan.commands.write.DataWriteCommand;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.commands.write.PutMapCommand;
import org.infinispan.commands.write.RemoveCommand;
import org.infinispan.commands.write.ReplaceCommand;
import org.infinispan.commons.util.InfinispanCollections;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.interceptors.base.CommandInterceptor;
import org.infinispan.partitionhandling.AvailabilityMode;
import org.infinispan.remoting.RpcException;
import org.infinispan.remoting.transport.Transport;

public class PartitionHandlingInterceptor extends CommandInterceptor {
   PartitionHandlingManager partitionHandlingManager;
   private Transport transport;
   private DistributionManager distributionManager;

   @Inject
   void init(PartitionHandlingManager partitionHandlingManager, Transport transport, DistributionManager distributionManager) {
      this.partitionHandlingManager = partitionHandlingManager;
      this.transport = transport;
      this.distributionManager = distributionManager;
   }

   private boolean performPartitionCheck(InvocationContext ctx, LocalFlagAffectedCommand command) {
      // We always perform partition check if this is a remote command
      if (!ctx.isOriginLocal()) {
         return true;
      }
      Set<Flag> flags = command.getFlags();
      return flags == null || !flags.contains(Flag.CACHE_MODE_LOCAL);
   }

   @Override
   public Object visitPutKeyValueCommand(InvocationContext ctx, PutKeyValueCommand command) throws Throwable {
      return handleSingleWrite(ctx, command);
   }

   @Override
   public Object visitRemoveCommand(InvocationContext ctx, RemoveCommand command) throws Throwable {
      return handleSingleWrite(ctx, command);
   }

   @Override
   public Object visitReplaceCommand(InvocationContext ctx, ReplaceCommand command) throws Throwable {
      return handleSingleWrite(ctx, command);
   }

   protected Object handleSingleWrite(InvocationContext ctx, DataWriteCommand command) throws Throwable {
      if (performPartitionCheck(ctx, command)) {
         partitionHandlingManager.checkWrite(command.getKey());
      }
      return handleDefault(ctx, command);
   }

   @Override
   public Object visitPutMapCommand(InvocationContext ctx, PutMapCommand command) throws Throwable {
      if (performPartitionCheck(ctx, command)) {
         for (Object k : command.getAffectedKeys())
            partitionHandlingManager.checkWrite(k);
      }
      return handleDefault(ctx, command);
   }

   @Override
   public Object visitClearCommand(InvocationContext ctx, ClearCommand command) throws Throwable {
      if (performPartitionCheck(ctx, command)) {
         partitionHandlingManager.checkClear();
      }
      return handleDefault(ctx, command);
   }

   @Override
   public Object visitApplyDeltaCommand(InvocationContext ctx, ApplyDeltaCommand command) throws Throwable {
      return handleSingleWrite(ctx, command);
   }

   @Override
   public Object visitEntryRetrievalCommand(InvocationContext ctx, EntryRetrievalCommand command) throws Throwable {
      if (performPartitionCheck(ctx, command)) {
         partitionHandlingManager.checkBulkRead();
      }
      return handleDefault(ctx, command);
   }

   @Override
   public final Object visitGetKeyValueCommand(InvocationContext ctx, GetKeyValueCommand command) throws Throwable {
      Object key = command.getKey();
      Object result;
      try {
         result = super.visitGetKeyValueCommand(ctx, command);
      } catch (RpcException e) {
         if (performPartitionCheck(ctx, command)) {
            // We must have received an AvailabilityException from one of the owners.
            // There is no way to verify the cause here, but there isn't any other way to get an invalid get response.
            throw getLog().degradedModeKeyUnavailable(key);
         } else {
            throw e;
         }
      }
      postOperationPartitionCheck(ctx, command, key, result);
      return result;
   }

   @Override
   public final Object visitGetCacheEntryCommand(InvocationContext ctx, GetCacheEntryCommand command) throws Throwable {
      Object key = command.getKey();
      Object result;
      try {
         result = super.visitGetCacheEntryCommand(ctx, command);
      } catch (RpcException e) {
         if (performPartitionCheck(ctx, command)) {
            // We must have received an AvailabilityException from one of the owners.
            // There is no way to verify the cause here, but there isn't any other way to get an invalid get response.
            throw getLog().degradedModeKeyUnavailable(key);
         } else {
            throw e;
         }
      }
      postOperationPartitionCheck(ctx, command, key, result);
      return result;
   }

   @Override
   public Object visitPrepareCommand(TxInvocationContext ctx, PrepareCommand command) throws Throwable {
      Object result = super.visitPrepareCommand(ctx, command);
      if (ctx.isOriginLocal()) {
         postTxCommandCheck(ctx);
      }
      return result;
   }

   @Override
   public Object visitCommitCommand(TxInvocationContext ctx, CommitCommand command) throws Throwable {
      Object result = super.visitCommitCommand(ctx, command);
      if (ctx.isOriginLocal()) {
         postTxCommandCheck(ctx);
      }
      return result;
   }

   protected void postTxCommandCheck(TxInvocationContext ctx) {
      if (ctx.hasModifications() && partitionHandlingManager.getAvailabilityMode() != AvailabilityMode.AVAILABLE) {
         for (Object key : ctx.getAffectedKeys()) {
            partitionHandlingManager.checkWrite(key);
         }
      }
   }

   private Object postOperationPartitionCheck(InvocationContext ctx, AbstractDataCommand command, Object key, Object result) throws Throwable {
      if (performPartitionCheck(ctx, command)) {
         // We do the availability check after the read, because the cache may have entered degraded mode
         // while we were reading from a remote node.
         partitionHandlingManager.checkRead(key);

         // If all owners left and we still haven't received the availability update yet, we could return
         // an incorrect null value. So we need a special check for null results.
         if (result == null) {
            // Unlike in PartitionHandlingManager.checkRead(), here we ignore the availability status
            // and we only fail the operation if _all_ owners have left the cluster.
            // TODO Move this to the availability strategy when implementing ISPN-4624
            if (!InfinispanCollections.containsAny(transport.getMembers(), distributionManager.locate(key))) {
               throw getLog().degradedModeKeyUnavailable(key);
            }
         }
      }
      // TODO We can still return a stale value if the other partition stayed active without us and we haven't entered degraded mode yet.
      return result;
   }

   @Override
   public Object visitGetAllCommand(InvocationContext ctx, GetAllCommand command) throws Throwable {
      Map<Object, Object> result;
      try {
         result = (Map<Object, Object>) super.visitGetAllCommand(ctx, command);
      } catch (RpcException e) {
         if (performPartitionCheck(ctx, command)) {
            // We must have received an AvailabilityException from one of the owners.
            // There is no way to verify the cause here, but there isn't any other way to get an invalid get response.
            throw getLog().degradedModeKeysUnavailable(command.getKeys());
         } else {
            throw e;
         }
      }

      if (performPartitionCheck(ctx, command)) {
         // We do the availability check after the read, because the cache may have entered degraded mode
         // while we were reading from a remote node.
         for (Object key : command.getKeys()) {
            partitionHandlingManager.checkRead(key);
         }

         // If all owners left and we still haven't received the availability update yet, we could return
         // an incorrect value. So we need a special check for missing results.
         if (result.size() != command.getKeys().size()) {
            // Unlike in PartitionHandlingManager.checkRead(), here we ignore the availability status
            // and we only fail the operation if _all_ owners have left the cluster.
            // TODO Move this to the availability strategy when implementing ISPN-4624
            Set<Object> missingKeys = new HashSet<>(command.getKeys());
            missingKeys.removeAll(result.keySet());
            for (Iterator<Object> it = missingKeys.iterator(); it.hasNext();) {
               Object key = it.next();
               if (InfinispanCollections.containsAny(transport.getMembers(), distributionManager.locate(key))) {
                  it.remove();
               }
            }
            if (!missingKeys.isEmpty()) {
               throw getLog().degradedModeKeysUnavailable(missingKeys);
            }
         }
      }

      // TODO We can still return a stale value if the other partition stayed active without us and we haven't entered degraded mode yet.
      return result;
   }
}


File: core/src/main/java/org/infinispan/partitionhandling/impl/PartitionHandlingManager.java
package org.infinispan.partitionhandling.impl;

import org.infinispan.partitionhandling.AvailabilityMode;
import org.infinispan.topology.CacheTopology;

/**
 * @author Dan Berindei
 * @since 7.0
 */
public interface PartitionHandlingManager {
   void setAvailabilityMode(AvailabilityMode availabilityMode);

   AvailabilityMode getAvailabilityMode();

   void checkWrite(Object key);

   void checkRead(Object key);

   void checkClear();

   void checkBulkRead();

   CacheTopology getLastStableTopology();
}


File: core/src/main/java/org/infinispan/partitionhandling/impl/PartitionHandlingManagerImpl.java
package org.infinispan.partitionhandling.impl;

import org.infinispan.Cache;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.factories.annotations.Start;
import org.infinispan.notifications.cachelistener.CacheNotifier;
import org.infinispan.partitionhandling.AvailabilityMode;
import org.infinispan.remoting.transport.Address;
import org.infinispan.statetransfer.StateTransferManager;
import org.infinispan.topology.CacheTopology;
import org.infinispan.topology.LocalTopologyManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.List;

public class PartitionHandlingManagerImpl implements PartitionHandlingManager {
   private static final Log log = LogFactory.getLog(PartitionHandlingManagerImpl.class);
   private static final boolean trace = log.isTraceEnabled();

   private volatile AvailabilityMode availabilityMode = AvailabilityMode.AVAILABLE;

   private DistributionManager distributionManager;
   private LocalTopologyManager localTopologyManager;
   private StateTransferManager stateTransferManager;
   private String cacheName;
   private CacheNotifier notifier;

   @Inject
   void init(DistributionManager distributionManager, LocalTopologyManager localTopologyManager,
         StateTransferManager stateTransferManager, Cache cache, CacheNotifier notifier) {
      this.distributionManager = distributionManager;
      this.localTopologyManager = localTopologyManager;
      this.stateTransferManager = stateTransferManager;
      this.cacheName = cache.getName();
      this.notifier = notifier;
   }

   @Start
   void start() {
   }

   @Override
   public void setAvailabilityMode(AvailabilityMode availabilityMode) {
      if (availabilityMode != this.availabilityMode) {
         log.debugf("Updating availability for cache %s: %s -> %s", cacheName, this.availabilityMode, availabilityMode);
         notifier.notifyPartitionStatusChanged(availabilityMode, true);
         this.availabilityMode = availabilityMode;
         notifier.notifyPartitionStatusChanged(availabilityMode, false);
      }
   }

   @Override
   public AvailabilityMode getAvailabilityMode() {
      return availabilityMode;
   }

   @Override
   public void checkWrite(Object key) {
      doCheck(key);
   }

   @Override
   public void checkRead(Object key) {
      doCheck(key);
   }

   private void doCheck(Object key) {
      if (trace) log.tracef("Checking availability for key=%s, status=%s", key, availabilityMode);
      if (availabilityMode == AvailabilityMode.AVAILABLE)
         return;

      List<Address> owners = distributionManager.locate(key);
      List<Address> actualMembers = stateTransferManager.getCacheTopology().getActualMembers();
      if (!actualMembers.containsAll(owners)) {
         if (trace) log.tracef("Partition is in %s mode, access is not allowed for key %s", availabilityMode, key);
         throw log.degradedModeKeyUnavailable(key);
      } else {
         if (trace) log.tracef("Key %s is available.", key);
      }
   }

   @Override
   public void checkClear() {
      if (availabilityMode != AvailabilityMode.AVAILABLE) {
         throw log.clearDisallowedWhilePartitioned();
      }
   }

   @Override
   public void checkBulkRead() {
      if (availabilityMode != AvailabilityMode.AVAILABLE) {
         throw log.partitionDegraded();
      }
   }

   @Override
   public CacheTopology getLastStableTopology() {
      return localTopologyManager.getStableCacheTopology(cacheName);
   }
}


File: core/src/main/java/org/infinispan/remoting/transport/AbstractDelegatingTransport.java
package org.infinispan.remoting.transport;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.infinispan.commands.ReplicableCommand;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.rpc.ResponseFilter;
import org.infinispan.remoting.rpc.ResponseMode;
import org.infinispan.util.logging.Log;
import org.infinispan.xsite.XSiteBackup;
import org.infinispan.xsite.XSiteReplicateCommand;
import org.jgroups.protocols.tom.DeliveryManager;

/**
 * Designed to be overwrite.
 *
 * @author Pedro Ruivo
 * @since 6.0
 */
public abstract class AbstractDelegatingTransport implements Transport {

   protected final Transport actual;

   protected AbstractDelegatingTransport(Transport actual) {
      this.actual = actual;
   }

   @Override
   public Map<Address, Response> invokeRemotely(Collection<Address> recipients, ReplicableCommand rpcCommand, ResponseMode mode, long timeout, ResponseFilter responseFilter, DeliverOrder deliverOrder, boolean anycast) throws Exception {
      beforeInvokeRemotely(rpcCommand);
      Map<Address, Response> result = actual.invokeRemotely(recipients, rpcCommand, mode, timeout, responseFilter, deliverOrder, anycast);
      return afterInvokeRemotely(rpcCommand, result);
   }

   @Override
   public Map<Address, Response> invokeRemotely(Map<Address, ReplicableCommand> rpcCommands, ResponseMode mode, long timeout, boolean usePriorityQueue, ResponseFilter responseFilter, boolean totalOrder, boolean anycast) throws Exception {
      return actual.invokeRemotely(rpcCommands, mode, timeout, usePriorityQueue, responseFilter, totalOrder, anycast);
   }

   @Override
   public Map<Address, Response> invokeRemotely(Map<Address, ReplicableCommand> rpcCommands, ResponseMode mode, long timeout, ResponseFilter responseFilter, DeliverOrder deliverOrder, boolean anycast) throws Exception {
      return actual.invokeRemotely(rpcCommands, mode, timeout, responseFilter, deliverOrder, anycast);
   }

   @Override
   public CompletableFuture<Map<Address, Response>> invokeRemotelyAsync(Collection<Address> recipients,
                                                                        ReplicableCommand rpcCommand,
                                                                        ResponseMode mode, long timeout,
                                                                        ResponseFilter responseFilter,
                                                                        DeliverOrder deliverOrder,
                                                                        boolean anycast) throws Exception {
      return actual.invokeRemotelyAsync(recipients, rpcCommand, mode, timeout, responseFilter, deliverOrder, anycast);
   }

   @Override
   public BackupResponse backupRemotely(Collection<XSiteBackup> backups, XSiteReplicateCommand rpcCommand) throws Exception {
      beforeBackupRemotely(rpcCommand);
      BackupResponse response = actual.backupRemotely(backups, rpcCommand);
      return afterBackupRemotely(rpcCommand, response);
   }

   @Override
   public boolean isCoordinator() {
      return actual.isCoordinator();
   }

   @Override
   public Address getCoordinator() {
      return actual.getCoordinator();
   }

   @Override
   public Address getAddress() {
      return actual.getAddress();
   }

   @Override
   public List<Address> getPhysicalAddresses() {
      return actual.getPhysicalAddresses();
   }

   @Override
   public List<Address> getMembers() {
      return actual.getMembers();
   }

   @Override
   public boolean isMulticastCapable() {
      return actual.isMulticastCapable();
   }

   @Override
   public void start() {
      actual.start();
   }

   @Override
   public void stop() {
      actual.stop();
   }

   @Override
   public int getViewId() {
      return actual.getViewId();
   }

   @Override
   public void waitForView(int viewId) throws InterruptedException {
      actual.waitForView(viewId);
   }

   @Override
   public void checkTotalOrderSupported() {
      actual.checkTotalOrderSupported();
   }

   @Override
   public Log getLog() {
      return actual.getLog();
   }

   /**
    * method invoked before a remote invocation.
    *
    * @param command the command to be invoked remotely
    */
   protected void beforeInvokeRemotely(ReplicableCommand command) {
      //no-op by default
   }

   /**
    * method invoked after a successful remote invocation.
    *
    * @param command     the command invoked remotely.
    * @param responseMap can be null if not response is expected.
    * @return the new response map
    */
   protected Map<Address, Response> afterInvokeRemotely(ReplicableCommand command, Map<Address, Response> responseMap) {
      return responseMap;
   }

   /**
    * method invoked before a backup remote invocation.
    *
    * @param command the command to be invoked remotely
    */
   protected void beforeBackupRemotely(XSiteReplicateCommand command) {
      //no-op by default
   }

   /**
    * method invoked after a successful backup remote invocation.
    *
    * @param command  the command invoked remotely.
    * @param response can be null if not response is expected.
    * @return the new response map
    */
   protected BackupResponse afterBackupRemotely(ReplicableCommand command, BackupResponse response) {
      return response;
   }
}


File: core/src/main/java/org/infinispan/remoting/transport/jgroups/JGroupsTransport.java
package org.infinispan.remoting.transport.jgroups;

import org.infinispan.commands.ReplicableCommand;
import org.infinispan.commons.CacheConfigurationException;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.marshall.StreamingMarshaller;
import org.infinispan.commons.util.FileLookup;
import org.infinispan.commons.util.FileLookupFactory;
import org.infinispan.commons.util.InfinispanCollections;
import org.infinispan.commons.util.TypedProperties;
import org.infinispan.commons.util.Util;
import org.infinispan.configuration.global.TransportConfiguration;
import org.infinispan.configuration.parsing.XmlConfigHelper;
import org.infinispan.factories.GlobalComponentRegistry;
import org.infinispan.factories.KnownComponentNames;
import org.infinispan.factories.annotations.ComponentName;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.jmx.JmxUtil;
import org.infinispan.notifications.cachemanagerlistener.CacheManagerNotifier;
import org.infinispan.remoting.RpcException;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.inboundhandler.InboundInvocationHandler;
import org.infinispan.remoting.responses.CacheNotFoundResponse;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.rpc.ResponseFilter;
import org.infinispan.remoting.rpc.ResponseMode;
import org.infinispan.remoting.transport.AbstractTransport;
import org.infinispan.remoting.transport.Address;
import org.infinispan.remoting.transport.BackupResponse;
import org.infinispan.util.TimeService;
import org.infinispan.util.concurrent.TimeoutException;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;
import org.infinispan.xsite.XSiteBackup;
import org.infinispan.xsite.XSiteReplicateCommand;
import org.jgroups.Channel;
import org.jgroups.Event;
import org.jgroups.JChannel;
import org.jgroups.MembershipListener;
import org.jgroups.MergeView;
import org.jgroups.Message;
import org.jgroups.UpHandler;
import org.jgroups.View;
import org.jgroups.blocks.RequestOptions;
import org.jgroups.blocks.RspFilter;
import org.jgroups.blocks.mux.Muxer;
import org.jgroups.jmx.JmxConfigurator;
import org.jgroups.protocols.relay.SiteMaster;
import org.jgroups.protocols.tom.TOA;
import org.jgroups.stack.AddressGenerator;
import org.jgroups.util.Buffer;
import org.jgroups.util.Rsp;
import org.jgroups.util.TopologyUUID;

import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.io.IOException;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

import static org.infinispan.factories.KnownComponentNames.GLOBAL_MARSHALLER;

/**
 * An encapsulation of a JGroups transport. JGroups transports can be configured using a variety of
 * methods, usually by passing in one of the following properties:
 * <ul>
 * <li><tt>configurationString</tt> - a JGroups configuration String</li>
 * <li><tt>configurationXml</tt> - JGroups configuration XML as a String</li>
 * <li><tt>configurationFile</tt> - String pointing to a JGroups XML configuration file</li>
 * <li><tt>channelLookup</tt> - Fully qualified class name of a
 * {@link org.infinispan.remoting.transport.jgroups.JGroupsChannelLookup} instance</li>
 * </ul>
 * These are normally passed in as Properties in
 * {@link org.infinispan.configuration.global.TransportConfigurationBuilder#withProperties(java.util.Properties)} or
 * in the Infinispan XML configuration file.
 *
 * @author Manik Surtani
 * @author Galder Zamarreño
 * @since 4.0
 */
public class JGroupsTransport extends AbstractTransport implements MembershipListener {
   public static final String CONFIGURATION_STRING = "configurationString";
   public static final String CONFIGURATION_XML = "configurationXml";
   public static final String CONFIGURATION_FILE = "configurationFile";
   public static final String CHANNEL_LOOKUP = "channelLookup";
   protected static final String DEFAULT_JGROUPS_CONFIGURATION_FILE = "default-configs/default-jgroups-udp.xml";

   static final Log log = LogFactory.getLog(JGroupsTransport.class);
   static final boolean trace = log.isTraceEnabled();

   protected boolean connectChannel = true, disconnectChannel = true, closeChannel = true;
   protected CommandAwareRpcDispatcher dispatcher;
   protected TypedProperties props;
   protected StreamingMarshaller marshaller;
   protected CacheManagerNotifier notifier;
   protected GlobalComponentRegistry gcr;
   private TimeService timeService;
   protected InboundInvocationHandler globalHandler;
   private ScheduledExecutorService timeoutExecutor;

   private boolean globalStatsEnabled;
   private MBeanServer mbeanServer;
   private String domain;

   protected Channel channel;
   protected Address address;
   protected Address physicalAddress;

   // these members are not valid until we have received the first view on a second thread
   // and channelConnectedLatch is signaled
   protected volatile int viewId = -1;
   protected volatile List<Address> members = null;
   protected volatile Address coordinator = null;
   protected volatile boolean isCoordinator = false;
   protected Lock viewUpdateLock = new ReentrantLock();
   protected Condition viewUpdateCondition = viewUpdateLock.newCondition();

   /**
    * This form is used when the transport is created by an external source and passed in to the
    * GlobalConfiguration.
    *
    * @param channel
    *           created and running channel to use
    */
   public JGroupsTransport(Channel channel) {
      this.channel = channel;
      if (channel == null)
         throw new IllegalArgumentException("Cannot deal with a null channel!");
      if (channel.isConnected())
         throw new IllegalArgumentException("Channel passed in cannot already be connected!");
   }

   public JGroupsTransport() {
   }

   @Override
   public Log getLog() {
      return log;
   }

   // ------------------------------------------------------------------------------------------------------------------
   // Lifecycle and setup stuff
   // ------------------------------------------------------------------------------------------------------------------

   /**
    * Initializes the transport with global cache configuration and transport-specific properties.
    *
    * @param marshaller    marshaller to use for marshalling and unmarshalling
    * @param notifier      notifier to use
    * @param gcr           the global component registry
    */
   @Inject
   public void initialize(@ComponentName(GLOBAL_MARSHALLER) StreamingMarshaller marshaller,
                          CacheManagerNotifier notifier, GlobalComponentRegistry gcr,
                          TimeService timeService, InboundInvocationHandler globalHandler,
                          // TODO define a new scheduled executor for the replication timeouts
                          @ComponentName(KnownComponentNames.ASYNC_REPLICATION_QUEUE_EXECUTOR) ScheduledExecutorService timeoutExecutor) {
      this.marshaller = marshaller;
      this.notifier = notifier;
      this.gcr = gcr;
      this.timeService = timeService;
      this.globalHandler = globalHandler;
      this.timeoutExecutor = timeoutExecutor;
   }

   @Override
   public void start() {
      props = TypedProperties.toTypedProperties(configuration.transport().properties());

      if (log.isInfoEnabled())
         log.startingJGroupsChannel(configuration.transport().clusterName());

      initChannelAndRPCDispatcher();
      startJGroupsChannelIfNeeded();

      waitForChannelToConnect();
   }

   protected void startJGroupsChannelIfNeeded() {
      String clusterName = configuration.transport().clusterName();
      if (connectChannel) {
         try {
            channel.connect(clusterName);
         } catch (Exception e) {
            throw new CacheException("Unable to start JGroups Channel", e);
         }

         try {
            // Normally this would be done by CacheManagerJmxRegistration but
            // the channel is not started when the cache manager starts but
            // when first cache starts, so it's safer to do it here.
            globalStatsEnabled = configuration.globalJmxStatistics().enabled();
            if (globalStatsEnabled) {
               String groupName = String.format("type=channel,cluster=%s", ObjectName.quote(clusterName));
               mbeanServer = JmxUtil.lookupMBeanServer(configuration);
               domain = JmxUtil.buildJmxDomain(configuration, mbeanServer, groupName);
               JmxConfigurator.registerChannel((JChannel) channel, mbeanServer, domain, clusterName, true);
            }
         } catch (Exception e) {
            throw new CacheException("Channel connected, but unable to register MBeans", e);
         }
      }
      address = fromJGroupsAddress(channel.getAddress());
      if (!connectChannel) {
         // the channel was already started externally, we need to initialize our member list
         viewAccepted(channel.getView());
      }
      if (log.isInfoEnabled())
         log.localAndPhysicalAddress(clusterName, getAddress(), getPhysicalAddresses());
   }

   @Override
   public int getViewId() {
      if (channel == null)
         throw new CacheException("The cache has been stopped and invocations are not allowed!");
      return viewId;
   }

   @Override
   public void waitForView(int viewId) throws InterruptedException {
      if (channel == null)
         return;
      log.tracef("Waiting on view %d being accepted", viewId);
      viewUpdateLock.lock();
      try {
         while (channel != null && getViewId() < viewId) {
            viewUpdateCondition.await();
         }
      } finally {
         viewUpdateLock.unlock();
      }
   }

   @Override
   public void stop() {
      String clusterName = configuration.transport().clusterName();
      try {
         if (disconnectChannel && channel != null && channel.isConnected()) {
            log.disconnectJGroups(clusterName);

            // Unregistering before disconnecting/closing because
            // after that the cluster name is null
            if (globalStatsEnabled) {
               JmxConfigurator.unregisterChannel((JChannel) channel, mbeanServer, domain, channel.getClusterName());
            }

            channel.disconnect();
         }
         if (closeChannel && channel != null && channel.isOpen()) {
            channel.close();
         }
      } catch (Exception toLog) {
         log.problemClosingChannel(toLog, clusterName);
      }

      if (dispatcher != null) {
         log.stoppingRpcDispatcher(clusterName);
         dispatcher.stop();
         if (channel != null) {
            // Remove reference to up_handler
            UpHandler handler = channel.getUpHandler();
            if (handler instanceof Muxer<?>) {
               @SuppressWarnings("unchecked")
               Muxer<UpHandler> mux = (Muxer<UpHandler>) handler;
               mux.setDefaultHandler(null);
            } else {
               channel.setUpHandler(null);
            }
         }
      }

      channel = null;
      viewId = -1;
      members = InfinispanCollections.emptyList();
      coordinator = null;
      isCoordinator = false;
      dispatcher = null;

      // Wake up any view waiters
      viewUpdateLock.lock();
      try {
         viewUpdateCondition.signalAll();
      } finally {
         viewUpdateLock.unlock();
      }

   }

   protected void initChannel() {
      final TransportConfiguration transportCfg = configuration.transport();
      if (channel == null) {
         buildChannel();
         String transportNodeName = transportCfg.nodeName();
         if (transportNodeName != null && transportNodeName.length() > 0) {
            long range = Short.MAX_VALUE * 2;
            long randomInRange = (long) ((Math.random() * range) % range) + 1;
            transportNodeName = transportNodeName + "-" + randomInRange;
            channel.setName(transportNodeName);
         }
      }

      // Channel.LOCAL *must* be set to false so we don't see our own messages - otherwise
      // invalidations targeted at remote instances will be received by self.
      // NOTE: total order needs to deliver own messages. the invokeRemotely method has a total order boolean
      //       that when it is false, it discard our own messages, maintaining the property needed
      channel.setDiscardOwnMessages(false);

      // if we have a TopologyAwareConsistentHash, we need to set our own address generator in JGroups
      if (transportCfg.hasTopologyInfo()) {
         // We can do this only if the channel hasn't been started already
         if (connectChannel) {
            ((JChannel) channel).setAddressGenerator(new AddressGenerator() {
               @Override
               public org.jgroups.Address generateAddress() {
                  return TopologyUUID.randomUUID(channel.getName(), transportCfg.siteId(),
                        transportCfg.rackId(), transportCfg.machineId());
               }
            });
         } else {
            if (channel.getAddress() instanceof TopologyUUID) {
               TopologyUUID topologyAddress = (TopologyUUID) channel.getAddress();
               if (!transportCfg.siteId().equals(topologyAddress.getSiteId())
                     || !transportCfg.rackId().equals(topologyAddress.getRackId())
                     || !transportCfg.machineId().equals(topologyAddress.getMachineId())) {
                  throw new CacheException("Topology information does not match the one set by the provided JGroups channel");
               }
            } else {
               throw new CacheException("JGroups address does not contain topology coordinates");
            }
         }
      }
   }

   private void initChannelAndRPCDispatcher() throws CacheException {
      initChannel();
      initRPCDispatcher();
   }

   protected void initRPCDispatcher() {
      dispatcher = new CommandAwareRpcDispatcher(channel, this, globalHandler, timeoutExecutor);
      MarshallerAdapter adapter = new MarshallerAdapter(marshaller);
      dispatcher.setRequestMarshaller(adapter);
      dispatcher.setResponseMarshaller(adapter);
      dispatcher.start();
   }

   // This is per CM, so the CL in use should be the CM CL
   private void buildChannel() {
	  FileLookup fileLookup = FileLookupFactory.newInstance();

      // in order of preference - we first look for an external JGroups file, then a set of XML
      // properties, and
      // finally the legacy JGroups String properties.
      String cfg;
      if (props != null) {
         if (props.containsKey(CHANNEL_LOOKUP)) {
            String channelLookupClassName = props.getProperty(CHANNEL_LOOKUP);

            try {
               JGroupsChannelLookup lookup = Util.getInstance(channelLookupClassName, configuration.classLoader());
               channel = lookup.getJGroupsChannel(props);
               connectChannel = lookup.shouldConnect();
               disconnectChannel = lookup.shouldDisconnect();
               closeChannel = lookup.shouldClose();
            } catch (ClassCastException e) {
               log.wrongTypeForJGroupsChannelLookup(channelLookupClassName, e);
               throw new CacheException(e);
            } catch (Exception e) {
               log.errorInstantiatingJGroupsChannelLookup(channelLookupClassName, e);
               throw new CacheException(e);
            }
         }

         if (channel == null && props.containsKey(CONFIGURATION_FILE)) {
            cfg = props.getProperty(CONFIGURATION_FILE);
            Collection<URL> confs = null;
            try {
               confs = fileLookup.lookupFileLocations(cfg, configuration.classLoader());
            } catch (IOException io) {
               //ignore, we check confs later for various states
            }
            if (confs.isEmpty()) {
               throw log.jgroupsConfigurationNotFound(cfg);
            } else if (confs.size() > 1) {
               log.ambiguousConfigurationFiles(Util.toStr(confs));
            }
            try {
               channel = new JChannel(confs.iterator().next());
            } catch (Exception e) {
               throw log.errorCreatingChannelFromConfigFile(cfg, e);
            }
         }

         if (channel == null && props.containsKey(CONFIGURATION_XML)) {
            cfg = props.getProperty(CONFIGURATION_XML);
            try {
               channel = new JChannel(XmlConfigHelper.stringToElement(cfg));
            } catch (Exception e) {
               throw log.errorCreatingChannelFromXML(cfg, e);
            }
         }

         if (channel == null && props.containsKey(CONFIGURATION_STRING)) {
            cfg = props.getProperty(CONFIGURATION_STRING);
            try {
               channel = new JChannel(cfg);
            } catch (Exception e) {
               throw log.errorCreatingChannelFromConfigString(cfg, e);

            }
         }
      }

      if (channel == null) {
         log.unableToUseJGroupsPropertiesProvided(props);
         try {
            channel = new JChannel(fileLookup.lookupFileLocation(DEFAULT_JGROUPS_CONFIGURATION_FILE, configuration.classLoader()));
         } catch (Exception e) {
            throw log.errorCreatingChannelFromConfigFile(DEFAULT_JGROUPS_CONFIGURATION_FILE, e);
         }
      }
   }

   // ------------------------------------------------------------------------------------------------------------------
   // querying cluster status
   // ------------------------------------------------------------------------------------------------------------------

   @Override
   public boolean isCoordinator() {
      return isCoordinator;
   }

   @Override
   public Address getCoordinator() {
      return coordinator;
   }

   public void waitForChannelToConnect() {
      try {
         waitForView(0);
      } catch (InterruptedException e) {
         // The start method can't throw checked exceptions
         log.interruptedWaitingForCoordinator(e);
         Thread.currentThread().interrupt();
      }
   }

   @Override
   public List<Address> getMembers() {
      return members != null ? members : InfinispanCollections.<Address>emptyList();
   }

   @Override
   public boolean isMulticastCapable() {
      return channel.getProtocolStack().getTransport().supportsMulticasting();
   }

   @Override
   public Address getAddress() {
      if (address == null && channel != null) {
         address = fromJGroupsAddress(channel.getAddress());
      }
      return address;
   }

   @Override
   public List<Address> getPhysicalAddresses() {
      if (physicalAddress == null && channel != null) {
         org.jgroups.Address addr = (org.jgroups.Address) channel.down(new Event(Event.GET_PHYSICAL_ADDRESS, channel.getAddress()));
         if (addr == null) {
            return InfinispanCollections.emptyList();
         }
         physicalAddress = new JGroupsAddress(addr);
      }
      return Collections.singletonList(physicalAddress);
   }

   // ------------------------------------------------------------------------------------------------------------------
   // outbound RPC
   // ------------------------------------------------------------------------------------------------------------------

   @Override
   public Map<Address, Response> invokeRemotely(Collection<Address> recipients, ReplicableCommand rpcCommand,
                                                ResponseMode mode, long timeout, ResponseFilter responseFilter,
                                                DeliverOrder deliverOrder, boolean anycast) throws Exception {
      CompletableFuture<Map<Address, Response>> future = invokeRemotelyAsync(recipients, rpcCommand, mode,
            timeout, responseFilter, deliverOrder, anycast);
      try {
         return future.get();
      } catch (ExecutionException e) {
         throw Util.rewrapAsCacheException(e.getCause());
      }
   }

   @Override
   public CompletableFuture<Map<Address, Response>> invokeRemotelyAsync(Collection<Address> recipients,
                                                                        ReplicableCommand rpcCommand,
                                                                        ResponseMode mode, long timeout,
                                                                        ResponseFilter responseFilter,
                                                                        DeliverOrder deliverOrder,
                                                                        boolean anycast) throws Exception {
      if (recipients != null && recipients.isEmpty()) {
         // don't send if recipients list is empty
         log.trace("Destination list is empty: no need to send message");
         return CompletableFuture.completedFuture(InfinispanCollections.emptyMap());
      }
      boolean totalOrder = deliverOrder == DeliverOrder.TOTAL;

      if (trace)
         log.tracef("dests=%s, command=%s, mode=%s, timeout=%s", recipients, rpcCommand, mode, timeout);
      Address self = getAddress();
      boolean ignoreLeavers = mode == ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS || mode == ResponseMode.WAIT_FOR_VALID_RESPONSE;
      if (mode.isSynchronous() && recipients != null && !getMembers().containsAll(recipients)) {
         if (!ignoreLeavers) { // SYNCHRONOUS
            CompletableFuture<Map<Address, Response>> future = new CompletableFuture<>();
            future.completeExceptionally(new SuspectException("One or more nodes have left the cluster while replicating command " + rpcCommand));
            return future;
         }
      }

      List<org.jgroups.Address> jgAddressList = toJGroupsAddressListExcludingSelf(recipients, totalOrder);
      int membersSize = members.size();
      boolean broadcast = jgAddressList == null || recipients.size() == membersSize;
      if (membersSize < 3 || (jgAddressList != null && jgAddressList.size() < 2)) broadcast = false;
      RspListFuture rspListFuture = null;
      SingleResponseFuture singleResponseFuture = null;
      org.jgroups.Address singleJGAddress = null;

      if (broadcast) {
         rspListFuture = dispatcher.invokeRemoteCommands(null, rpcCommand, toJGroupsMode(mode), timeout,
               toJGroupsFilter(responseFilter), deliverOrder);
      } else if (totalOrder) {
         rspListFuture = dispatcher.invokeRemoteCommands(jgAddressList, rpcCommand, toJGroupsMode(mode),
               timeout, toJGroupsFilter(responseFilter), deliverOrder);
      } else {
         if (jgAddressList == null || !jgAddressList.isEmpty()) {
            boolean singleRecipient = !ignoreLeavers && jgAddressList != null && jgAddressList.size() == 1;
            boolean skipRpc = false;
            if (jgAddressList == null) {
               // broadcast with membersSize < 3
               ArrayList<Address> others = new ArrayList<>(members);
               others.remove(self);
               skipRpc = others.isEmpty();
               singleRecipient = !ignoreLeavers && others.size() == 1;
               if (singleRecipient) singleJGAddress = toJGroupsAddress(others.get(0));
            }
            if (skipRpc) {
               return CompletableFuture.completedFuture(InfinispanCollections.emptyMap());
            }

            if (singleRecipient) {
               if (singleJGAddress == null) singleJGAddress = jgAddressList.get(0);
               singleResponseFuture = dispatcher.invokeRemoteCommand(singleJGAddress, rpcCommand,
                     toJGroupsMode(mode), timeout, deliverOrder);
            } else {
               rspListFuture = dispatcher.invokeRemoteCommands(jgAddressList, rpcCommand, toJGroupsMode(
                     mode), timeout, toJGroupsFilter(responseFilter), deliverOrder);

            }
         } else {
            return CompletableFuture.completedFuture(InfinispanCollections.emptyMap());
         }
      }

      if (mode.isAsynchronous()) {
         return CompletableFuture.completedFuture(InfinispanCollections.emptyMap());
      }

      if (singleResponseFuture != null) {
         // Unicast request
         return singleResponseFuture.thenApply(rsp -> {
            if (trace) log.tracef("Response: %s", rsp);
            Address sender = fromJGroupsAddress(rsp.getSender());
            Response response = checkRsp(rsp, sender, responseFilter != null, ignoreLeavers);
            return Collections.singletonMap(sender, response);
         });
      } else if (rspListFuture != null) {
         // Broadcast/anycast request
         return rspListFuture.thenApply(rsps -> {
            if (trace) log.tracef("Responses: %s", rsps);
            Map<Address, Response> retval = new HashMap<>(rsps.size());
            boolean hasResponses = false;
            boolean hasValidResponses = false;
            for (Rsp<Response> rsp : rsps.values()) {
               hasResponses |= rsp.wasReceived();
               Address sender = fromJGroupsAddress(rsp.getSender());
               Response response = checkRsp(rsp, sender, responseFilter != null, ignoreLeavers);
               if (response != null) {
                  hasValidResponses = true;
                  retval.put(sender, response);
               }
            }

            if (!hasValidResponses) {
               // PartitionHandlingInterceptor relies on receiving a RpcException if there are only invalid responses
               // But we still need to throw a TimeoutException if there are no responses at all.
               if (hasResponses) {
                  throw new RpcException(String.format("Received invalid responses from all of %s", recipients));
               } else {
                  throw new TimeoutException("Timed out waiting for valid responses!");
               }
            }
            return retval;
         });
      } else {
         throw new IllegalStateException("Should have one remote invocation future");
      }
   }

   @Override
   public Map<Address, Response> invokeRemotely(Map<Address, ReplicableCommand> rpcCommands, ResponseMode mode,
                                                long timeout, boolean usePriorityQueue, ResponseFilter responseFilter, boolean totalOrder, boolean anycast)
         throws Exception {
      DeliverOrder deliverOrder = DeliverOrder.PER_SENDER;
      if (totalOrder) {
         deliverOrder = DeliverOrder.TOTAL;
      } else if (usePriorityQueue) {
         deliverOrder = DeliverOrder.NONE;
      }
      return invokeRemotely(rpcCommands, mode, timeout, responseFilter, deliverOrder, anycast);
   }

   @Override
   public Map<Address, Response> invokeRemotely(Map<Address, ReplicableCommand> rpcCommands, ResponseMode mode,
         long timeout, ResponseFilter responseFilter, DeliverOrder deliverOrder, boolean anycast)
         throws Exception {
      if (rpcCommands == null || rpcCommands.isEmpty()) {
         // don't send if recipients list is empty
         log.trace("Destination list is empty: no need to send message");
         return InfinispanCollections.emptyMap();
      }

      if (trace)
         log.tracef("commands=%s, mode=%s, timeout=%s", rpcCommands, mode, timeout);
      boolean ignoreLeavers = mode == ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS || mode == ResponseMode.WAIT_FOR_VALID_RESPONSE;

      SingleResponseFuture[] futures = new SingleResponseFuture[rpcCommands.size()];
      int i = 0;
      for (Map.Entry<Address, ReplicableCommand> entry : rpcCommands.entrySet()) {
         org.jgroups.Address recipient = toJGroupsAddress(entry.getKey());
         ReplicableCommand command = entry.getValue();
         SingleResponseFuture future = dispatcher.invokeRemoteCommand(recipient, command, toJGroupsMode(mode),
               timeout, deliverOrder);
         futures[i] = future;
         i++;
      }

      if (mode.isAsynchronous())
         return InfinispanCollections.emptyMap();

      CompletableFuture<Void> bigFuture = CompletableFuture.allOf(futures);
      bigFuture.get();

      List<Rsp<Response>> rsps = new ArrayList<>();
      for (SingleResponseFuture future : futures) {
         rsps.add(future.get());
      }

      Map<Address, Response> retval = new HashMap<>(rsps.size());
      boolean hasResponses = false;
      for (Rsp<Response> rsp : rsps) {
         Address sender = fromJGroupsAddress(rsp.getSender());
         Response response = checkRsp(rsp, sender, responseFilter != null, ignoreLeavers);
         if (response != null) {
            retval.put(sender, response);
            hasResponses = true;
         }
      }

      if (!hasResponses) {
         // It is possible for their to be no valid response if we ignored leavers and
         // all of our targets left
         // If all the targets were suspected we didn't have a timeout
         throw new TimeoutException("Timed out waiting for valid responses!");
      }
      return retval;
   }

   @Override
   public BackupResponse backupRemotely(Collection<XSiteBackup> backups, XSiteReplicateCommand rpcCommand) throws Exception {
      log.tracef("About to send to backups %s, command %s", backups, rpcCommand);
      Buffer buf = dispatcher.marshallCall(dispatcher.getMarshaller(), rpcCommand);
      Map<XSiteBackup, Future<Object>> syncBackupCalls = new HashMap<>(backups.size());
      for (XSiteBackup xsb : backups) {
         SiteMaster recipient = new SiteMaster(xsb.getSiteName());
         if (xsb.isSync()) {
            RequestOptions sync = new RequestOptions(org.jgroups.blocks.ResponseMode.GET_ALL, xsb.getTimeout());
            Message msg = CommandAwareRpcDispatcher.constructMessage(buf, recipient,
                  org.jgroups.blocks.ResponseMode.GET_ALL, false, DeliverOrder.NONE);
            syncBackupCalls.put(xsb, dispatcher.sendMessageWithFuture(msg, sync));
         } else {
            RequestOptions async = new RequestOptions(org.jgroups.blocks.ResponseMode.GET_NONE, xsb.getTimeout());
            Message msg = CommandAwareRpcDispatcher.constructMessage(buf, recipient,
                  org.jgroups.blocks.ResponseMode.GET_NONE, false, DeliverOrder.PER_SENDER);
            dispatcher.sendMessage(msg, async);
         }
      }
      return new JGroupsBackupResponse(syncBackupCalls, timeService);
   }

   private static org.jgroups.blocks.ResponseMode toJGroupsMode(ResponseMode mode) {
      switch (mode) {
         case ASYNCHRONOUS:
            return org.jgroups.blocks.ResponseMode.GET_NONE;
         case SYNCHRONOUS:
         case SYNCHRONOUS_IGNORE_LEAVERS:
         case WAIT_FOR_VALID_RESPONSE:
            return org.jgroups.blocks.ResponseMode.GET_ALL;
      }
      throw new CacheException("Unknown response mode " + mode);
   }

   private RspFilter toJGroupsFilter(ResponseFilter responseFilter) {
      return responseFilter == null ? null : new JGroupsResponseFilterAdapter(responseFilter);
   }

   protected Response checkRsp(Rsp<Response> rsp, Address sender, boolean ignoreTimeout,
                               boolean ignoreLeavers) {
      Response response;
      if (rsp.wasReceived()) {
         if (rsp.hasException()) {
            log.tracef(rsp.getException(), "Unexpected exception from %s", sender);
            throw log.remoteException(sender, rsp.getException());
         } else {
            // TODO We should handle CacheNotFoundResponse exactly the same way as wasSuspected
            response = checkResponse(rsp.getValue(), sender, true);
         }
      } else if (rsp.wasSuspected()) {
         response = checkResponse(CacheNotFoundResponse.INSTANCE, sender, ignoreLeavers);
      } else {
         if (!ignoreTimeout) throw new TimeoutException("Replication timeout for " + sender);
         response = null;
      }

      return response;
   }

   // ------------------------------------------------------------------------------------------------------------------
   // Implementations of JGroups interfaces
   // ------------------------------------------------------------------------------------------------------------------


   private interface Notify {
      void emitNotification(List<Address> oldMembers, View newView);
   }

   private class NotifyViewChange implements Notify {
      @Override
      public void emitNotification(List<Address> oldMembers, View newView) {
         notifier.notifyViewChange(members, oldMembers, getAddress(), (int) newView.getViewId().getId());
      }
   }

   private class NotifyMerge implements Notify {

      @Override
      public void emitNotification(List<Address> oldMembers, View newView) {
         MergeView mv = (MergeView) newView;

         final Address address = getAddress();
         final int viewId = (int) newView.getViewId().getId();
         notifier.notifyMerge(members, oldMembers, address, viewId, getSubgroups(mv.getSubgroups()));
      }

      private List<List<Address>> getSubgroups(List<View> subviews) {
         List<List<Address>> l = new ArrayList<>(subviews.size());
         for (View v : subviews)
            l.add(fromJGroupsAddressList(v.getMembers()));
         return l;
      }
   }

   @Override
   public void viewAccepted(View newView) {
      log.debugf("New view accepted: %s", newView);
      List<org.jgroups.Address> newMembers = newView.getMembers();
      if (newMembers == null || newMembers.isEmpty()) {
         log.debugf("Received null or empty member list from JGroups channel: " + newView);
         return;
      }

      List<Address> oldMembers = members;

      // Update every view-related field while holding the lock so that waitForView only returns
      // after everything was updated.
      viewUpdateLock.lock();
      try {
         viewId = (int) newView.getViewId().getId();

         // we need a defensive copy anyway
         members = fromJGroupsAddressList(newMembers);

         // Delta view debug log for large cluster
         if (log.isDebugEnabled() && oldMembers != null) {
            List<Address> joined = new ArrayList<>(members);
            joined.removeAll(oldMembers);
            List<Address> left = new ArrayList<>(oldMembers);
            left.removeAll(members);
            log.debugf("Joined: %s, Left: %s", joined, left);
         }

         // Now that we have a view, figure out if we are the isCoordinator
         coordinator = fromJGroupsAddress(newView.getCreator());
         isCoordinator = coordinator != null && coordinator.equals(getAddress());

         // Wake up any threads that are waiting to know about who the isCoordinator is
         // do it before the notifications, so if a listener throws an exception we can still start
         viewUpdateCondition.signalAll();
      } finally {
         viewUpdateLock.unlock();
      }

      // now notify listeners - *after* updating the isCoordinator. - JBCACHE-662
      boolean hasNotifier = notifier != null;
      if (hasNotifier) {
         String clusterName = configuration.transport().clusterName();
         Notify n;
         if (newView instanceof MergeView) {
            log.receivedMergedView(clusterName, newView);
            n = new NotifyMerge();
         } else {
            log.receivedClusterView(clusterName, newView);
            n = new NotifyViewChange();
         }

         n.emitNotification(oldMembers, newView);
      }

      JGroupsAddressCache.pruneAddressCache();
   }

   @Override
   public void suspect(org.jgroups.Address suspected_mbr) {
      // no-op
   }

   @Override
   public void block() {
      // no-op since ISPN-83 has been resolved
   }

   @Override
   public void unblock() {
      // no-op since ISPN-83 has been resolved
   }

   // ------------------------------------------------------------------------------------------------------------------
   // Helpers to convert between Address types
   // ------------------------------------------------------------------------------------------------------------------

   protected static org.jgroups.Address toJGroupsAddress(Address a) {
      return ((JGroupsAddress) a).address;
   }

   static Address fromJGroupsAddress(final org.jgroups.Address addr) {
      return JGroupsAddressCache.fromJGroupsAddress(addr);
   }

   private List<org.jgroups.Address> toJGroupsAddressListExcludingSelf(Collection<Address> list, boolean totalOrder) {
      if (list == null)
         return null;
      if (list.isEmpty())
         return InfinispanCollections.emptyList();

      List<org.jgroups.Address> retval = new ArrayList<>(list.size());
      boolean ignoreSelf = !totalOrder; //in total order, we need to send the message to ourselves!
      Address self = getAddress();
      for (Address a : list) {
         if (!ignoreSelf || !a.equals(self)) {
            retval.add(toJGroupsAddress(a));
         } else {
            ignoreSelf = false; // short circuit address equality for future iterations
         }
      }

      return retval;
   }

   private static List<Address> fromJGroupsAddressList(List<org.jgroups.Address> list) {
      if (list == null || list.isEmpty())
         return InfinispanCollections.emptyList();

      List<Address> retval = new ArrayList<>(list.size());
      for (org.jgroups.Address a : list)
         retval.add(fromJGroupsAddress(a));
      return Collections.unmodifiableList(retval);
   }

   // mainly for unit testing

   public CommandAwareRpcDispatcher getCommandAwareRpcDispatcher() {
      return dispatcher;
   }

   public Channel getChannel() {
      return channel;
   }

   @Override
   public final void checkTotalOrderSupported() {
      //For replicated and distributed tx caches, we use TOA as total order protocol.
      if (channel.getProtocolStack().findProtocol(TOA.class) == null) {
         throw new CacheConfigurationException("In order to support total order based transaction, the TOA protocol " +
                                                "must be present in the JGroups's config.");
      }
   }
}


File: core/src/main/java/org/infinispan/statetransfer/StateConsumerImpl.java
package org.infinispan.statetransfer;

import net.jcip.annotations.GuardedBy;
import org.infinispan.Cache;
import org.infinispan.commands.CommandsFactory;
import org.infinispan.commands.write.InvalidateCommand;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.util.InfinispanCollections;
import org.infinispan.commons.util.concurrent.ParallelIterableMap;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.container.DataContainer;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.InvocationContextFactory;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.distexec.DistributedCallable;
import org.infinispan.distribution.L1Manager;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.executors.SemaphoreCompletionService;
import org.infinispan.factories.KnownComponentNames;
import org.infinispan.factories.annotations.ComponentName;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.factories.annotations.Start;
import org.infinispan.factories.annotations.Stop;
import org.infinispan.filter.KeyFilter;
import org.infinispan.interceptors.InterceptorChain;
import org.infinispan.marshall.core.MarshalledEntry;
import org.infinispan.notifications.cachelistener.CacheNotifier;
import org.infinispan.persistence.manager.PersistenceManager;
import org.infinispan.persistence.spi.AdvancedCacheLoader;
import org.infinispan.remoting.responses.CacheNotFoundResponse;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.responses.SuccessfulResponse;
import org.infinispan.remoting.rpc.ResponseMode;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.rpc.RpcOptions;
import org.infinispan.remoting.transport.Address;
import org.infinispan.remoting.transport.jgroups.SuspectException;
import org.infinispan.topology.CacheTopology;
import org.infinispan.transaction.impl.RemoteTransaction;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.totalorder.TotalOrderLatch;
import org.infinispan.transaction.totalorder.TotalOrderManager;
import org.infinispan.transaction.xa.CacheTransaction;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.util.concurrent.BlockingTaskAwareExecutorService;
import org.infinispan.util.concurrent.ConcurrentHashSet;
import org.infinispan.util.concurrent.TimeoutException;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.TransactionManager;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import static org.infinispan.context.Flag.CACHE_MODE_LOCAL;
import static org.infinispan.context.Flag.IGNORE_RETURN_VALUES;
import static org.infinispan.context.Flag.PUT_FOR_STATE_TRANSFER;
import static org.infinispan.context.Flag.SKIP_LOCKING;
import static org.infinispan.context.Flag.SKIP_OWNERSHIP_CHECK;
import static org.infinispan.context.Flag.SKIP_REMOTE_LOOKUP;
import static org.infinispan.context.Flag.SKIP_SHARED_CACHE_STORE;
import static org.infinispan.context.Flag.SKIP_XSITE_BACKUP;
import static org.infinispan.factories.KnownComponentNames.ASYNC_TRANSPORT_EXECUTOR;
import static org.infinispan.factories.KnownComponentNames.STATE_TRANSFER_EXECUTOR;
import static org.infinispan.persistence.manager.PersistenceManager.AccessMode.PRIVATE;

/**
 * {@link StateConsumer} implementation.
 *
 * @author anistor@redhat.com
 * @since 5.2
 */
public class StateConsumerImpl implements StateConsumer {

   private static final Log log = LogFactory.getLog(StateConsumerImpl.class);
   private static final boolean trace = log.isTraceEnabled();
   public static final int NO_REBALANCE_IN_PROGRESS = -1;

   private Cache cache;
   private ExecutorService asyncTransportExecutor;
   private StateTransferManager stateTransferManager;
   private String cacheName;
   private Configuration configuration;
   private RpcManager rpcManager;
   private TransactionManager transactionManager;   // optional
   private CommandsFactory commandsFactory;
   private TransactionTable transactionTable;       // optional
   private DataContainer<Object, Object> dataContainer;
   private PersistenceManager persistenceManager;
   private InterceptorChain interceptorChain;
   private InvocationContextFactory icf;
   private StateTransferLock stateTransferLock;
   private CacheNotifier cacheNotifier;
   private TotalOrderManager totalOrderManager;
   private BlockingTaskAwareExecutorService remoteCommandsExecutor;
   private L1Manager l1Manager;
   private long timeout;
   private boolean isFetchEnabled;
   private boolean isTransactional;
   private boolean isInvalidationMode;
   private boolean isTotalOrder;
   private volatile KeyInvalidationListener keyInvalidationListener; //for test purpose only!
   private CommitManager commitManager;
   private ExecutorService stateTransferExecutor;

   private volatile CacheTopology cacheTopology;

   /**
    * Indicates if there is a state transfer in progress. It is set to the new topology id when onTopologyUpdate with
    * isRebalance==true is called.
    * It is changed back to NO_REBALANCE_IN_PROGRESS when a topology update with a null pending CH is received.
    */
   private final AtomicInteger stateTransferTopologyId = new AtomicInteger(NO_REBALANCE_IN_PROGRESS);

   /**
    * Indicates if there is a rebalance in progress and there the local node has not yet received
    * all the new segments yet. It is set to true when rebalance starts and becomes when all inbound transfers have completed
    * (before stateTransferTopologyId is set back to NO_REBALANCE_IN_PROGRESS).
    */
   private final AtomicBoolean waitingForState = new AtomicBoolean(false);

   private final Object transferMapsLock = new Object();

   /**
    * A map that keeps track of current inbound state transfers by source address. There could be multiple transfers
    * flowing in from the same source (but for different segments) so the values are lists. This works in tandem with
    * transfersBySegment so they always need to be kept in sync and updates to both of them need to be atomic.
    */
   @GuardedBy("transferMapsLock")
   private final Map<Address, List<InboundTransferTask>> transfersBySource = new HashMap<Address, List<InboundTransferTask>>();

   /**
    * A map that keeps track of current inbound state transfers by segment id. There is at most one transfers per segment.
    * This works in tandem with transfersBySource so they always need to be kept in sync and updates to both of them
    * need to be atomic.
    */
   @GuardedBy("transferMapsLock")
   private final Map<Integer, InboundTransferTask> transfersBySegment = new HashMap<Integer, InboundTransferTask>();

   /**
    * Push RPCs on a background thread
    */
   private SemaphoreCompletionService<Void> stateRequestCompletionService;

   private volatile boolean ownsData = false;

   private RpcOptions rpcOptions;

   public StateConsumerImpl() {
   }

   /**
    * Stops applying incoming state. Also stops tracking updated keys. Should be called at the end of state transfer or
    * when a ClearCommand is committed during state transfer.
    */
   @Override
   public void stopApplyingState() {
      if (trace) log.tracef("Stop keeping track of changed keys for state transfer");
      commitManager.stopTrack(PUT_FOR_STATE_TRANSFER);
   }

   @Inject
   public void init(Cache cache,
                    @ComponentName(ASYNC_TRANSPORT_EXECUTOR) ExecutorService asyncTransportExecutor,
                    @ComponentName(STATE_TRANSFER_EXECUTOR) ExecutorService stateTransferExecutor,
                    StateTransferManager stateTransferManager,
                    InterceptorChain interceptorChain,
                    InvocationContextFactory icf,
                    Configuration configuration,
                    RpcManager rpcManager,
                    TransactionManager transactionManager,
                    CommandsFactory commandsFactory,
                    PersistenceManager persistenceManager,
                    DataContainer dataContainer,
                    TransactionTable transactionTable,
                    StateTransferLock stateTransferLock,
                    CacheNotifier cacheNotifier,
                    TotalOrderManager totalOrderManager,
                    @ComponentName(KnownComponentNames.REMOTE_COMMAND_EXECUTOR) BlockingTaskAwareExecutorService remoteCommandsExecutor,
                    L1Manager l1Manager, CommitManager commitManager) {
      this.cache = cache;
      this.asyncTransportExecutor = asyncTransportExecutor;
      this.cacheName = cache.getName();
      this.stateTransferExecutor = stateTransferExecutor;
      this.stateTransferManager = stateTransferManager;
      this.interceptorChain = interceptorChain;
      this.icf = icf;
      this.configuration = configuration;
      this.rpcManager = rpcManager;
      this.transactionManager = transactionManager;
      this.commandsFactory = commandsFactory;
      this.persistenceManager = persistenceManager;
      this.dataContainer = dataContainer;
      this.transactionTable = transactionTable;
      this.stateTransferLock = stateTransferLock;
      this.cacheNotifier = cacheNotifier;
      this.totalOrderManager = totalOrderManager;
      this.remoteCommandsExecutor = remoteCommandsExecutor;
      this.l1Manager = l1Manager;
      this.commitManager = commitManager;

      isInvalidationMode = configuration.clustering().cacheMode().isInvalidation();

      isTransactional = configuration.transaction().transactionMode().isTransactional();
      isTotalOrder = configuration.transaction().transactionProtocol().isTotalOrder();

      timeout = configuration.clustering().stateTransfer().timeout();

      stateRequestCompletionService = new SemaphoreCompletionService<>(stateTransferExecutor, 1);
   }

   public boolean hasActiveTransfers() {
      synchronized (transferMapsLock) {
         return !transfersBySource.isEmpty();
      }
   }

   @Override
   public boolean isStateTransferInProgress() {
      return stateTransferTopologyId.get() != NO_REBALANCE_IN_PROGRESS;
   }

   @Override
   public boolean isStateTransferInProgressForKey(Object key) {
      if (isInvalidationMode) {
         // In invalidation mode it is of not much relevance if the key is actually being transferred right now.
         // A false response to this will just mean the usual remote lookup before a write operation is not
         // performed and a null is assumed. But in invalidation mode the user must expect the data can disappear
         // from cache at any time so this null previous value should not cause any trouble.
         return false;
      }

      CacheTopology localCacheTopology = cacheTopology;
      if (localCacheTopology == null || localCacheTopology.getPendingCH() == null)
         return false;
      Address address = rpcManager.getAddress();
      boolean keyWillBeLocal = localCacheTopology.getPendingCH().isKeyLocalToNode(address, key);
      boolean keyIsLocal = localCacheTopology.getCurrentCH().isKeyLocalToNode(address, key);
      return keyWillBeLocal && !keyIsLocal;
   }

   @Override
   public boolean ownsData() {
      return ownsData;
   }

   @Override
   public void onTopologyUpdate(final CacheTopology cacheTopology, final boolean isRebalance) {
      final boolean isMember = cacheTopology.getMembers().contains(rpcManager.getAddress());
      if (trace) log.tracef("Received new topology for cache %s, isRebalance = %b, isMember = %b, topology = %s", cacheName, isRebalance, isMember, cacheTopology);

      if (!ownsData && isMember) {
         ownsData = true;
      } else if (ownsData && !isMember) {
         // This can happen after a merge, if the local node was in a minority partition.
         ownsData = false;
      }

      if (isRebalance) {
         // Only update the rebalance topology id when starting the rebalance, as we're going to ignore any state
         // response with a smaller topology id
         stateTransferTopologyId.compareAndSet(NO_REBALANCE_IN_PROGRESS, cacheTopology.getTopologyId());
         cacheNotifier.notifyDataRehashed(cacheTopology.getCurrentCH(), cacheTopology.getPendingCH(),
                                          cacheTopology.getUnionCH(), cacheTopology.getTopologyId(), true);
      }

      awaitTotalOrderTransactions(cacheTopology, isRebalance);

      // Make sure we don't send a REBALANCE_CONFIRM command before we've added all the transfer tasks
      // even if some of the tasks are removed and re-added
      waitingForState.set(false);

      final ConsistentHash newReadCh = cacheTopology.getReadConsistentHash();
      final ConsistentHash newWriteCh = cacheTopology.getWriteConsistentHash();
      final ConsistentHash previousReadCh = this.cacheTopology != null ? this.cacheTopology.getReadConsistentHash() : null;
      final ConsistentHash previousWriteCh = this.cacheTopology != null ? this.cacheTopology.getWriteConsistentHash() : null;
      // Ensures writes to the data container use the right consistent hash
      // No need for a try/finally block, since it's just an assignment
      stateTransferLock.acquireExclusiveTopologyLock();
      this.cacheTopology = cacheTopology;
      if (isRebalance) {
         if (trace) log.tracef("Start keeping track of keys for rebalance");
         commitManager.stopTrack(PUT_FOR_STATE_TRANSFER);
         commitManager.startTrack(PUT_FOR_STATE_TRANSFER);
      }
      stateTransferLock.releaseExclusiveTopologyLock();
      stateTransferLock.notifyTopologyInstalled(cacheTopology.getTopologyId());
      remoteCommandsExecutor.submit(new Runnable() {
         @Override
         public void run() {
            remoteCommandsExecutor.checkForReadyTasks();
         }
      });

      try {
         // fetch transactions and data segments from other owners if this is enabled
         if (isTransactional || isFetchEnabled) {
            Set<Integer> addedSegments;
            if (previousWriteCh == null) {
               // we start fresh, without any data, so we need to pull everything we own according to writeCh
               addedSegments = getOwnedSegments(newWriteCh);

               // TODO Perhaps we should only do this once we are a member, as listener installation should happen only on cache members?
               if (configuration.clustering().cacheMode().isDistributed()) {
                  Collection<DistributedCallable> callables = getClusterListeners(cacheTopology);
                  for (DistributedCallable callable : callables) {
                     callable.setEnvironment(cache, null);
                     try {
                        callable.call();
                     } catch (Exception e) {
                        log.clusterListenerInstallationFailure(e);
                     }
                  }
               }

               if (trace) {
                  log.tracef("On cache %s we have: added segments: %s", cacheName, addedSegments);
               }
            } else {
               Set<Integer> previousSegments = getOwnedSegments(previousWriteCh);
               Set<Integer> newSegments = getOwnedSegments(newWriteCh);

               Set<Integer> removedSegments;
               if (newSegments.size() == newWriteCh.getNumSegments()) {
                  // Optimization for replicated caches
                  removedSegments = InfinispanCollections.emptySet();
               } else {
                  removedSegments = new HashSet<Integer>(previousSegments);
                  removedSegments.removeAll(newSegments);
               }

               // This is a rebalance, we need to request the segments we own in the new CH.
               addedSegments = new HashSet<Integer>(newSegments);
               addedSegments.removeAll(previousSegments);

               if (trace) {
                  log.tracef("On cache %s we have: new segments: %s; old segments: %s", cacheName, newSegments, previousSegments);
                  log.tracef("On cache %s we have: added segments: %s; removed segments: %s", cacheName, addedSegments, removedSegments);
               }

               // remove inbound transfers for segments we no longer own
               cancelTransfers(removedSegments);

               // check if any of the existing transfers should be restarted from a different source because the initial source is no longer a member
               restartBrokenTransfers(cacheTopology, addedSegments);
            }

            if (!addedSegments.isEmpty()) {
               addTransfers(addedSegments);  // add transfers for new or restarted segments
            }
         }

         int rebalanceTopologyId = stateTransferTopologyId.get();
         if (trace) log.tracef("Topology update processed, stateTransferTopologyId = %d, isRebalance = %s, pending CH = %s",
               (Object)rebalanceTopologyId, isRebalance, cacheTopology.getPendingCH());
         if (rebalanceTopologyId != NO_REBALANCE_IN_PROGRESS) {
            // there was a rebalance in progress
            if (!isRebalance && cacheTopology.getPendingCH() == null) {
               // we have received a topology update without a pending CH, signalling the end of the rebalance
               boolean changed = stateTransferTopologyId.compareAndSet(rebalanceTopologyId, NO_REBALANCE_IN_PROGRESS);
               if (changed) {
                  stopApplyingState();

                  // if the coordinator changed, we might get two concurrent topology updates,
                  // but we only want to notify the @DataRehashed listeners once
                  cacheNotifier.notifyDataRehashed(previousReadCh, cacheTopology.getCurrentCH(), previousWriteCh,
                        cacheTopology.getTopologyId(), false);
                  if (trace) {
                     log.tracef("Unlock State Transfer in Progress for topology ID %s", cacheTopology.getTopologyId());
                  }
                  if (isTotalOrder) {
                     totalOrderManager.notifyStateTransferEnd();
                  }
               }
            }
         }
      } finally {
         stateTransferLock.notifyTransactionDataReceived(cacheTopology.getTopologyId());
         remoteCommandsExecutor.submit(new Runnable() {
            @Override
            public void run() {
               remoteCommandsExecutor.checkForReadyTasks();
            }
         });

         // Only set the flag here, after all the transfers have been added to the transfersBySource map
         if (stateTransferTopologyId.get() != NO_REBALANCE_IN_PROGRESS && isMember) {
            waitingForState.set(true);
         }

         notifyEndOfRebalanceIfNeeded(cacheTopology.getTopologyId(), cacheTopology.getRebalanceId());

         // Remove the transactions whose originators have left the cache.
         // Need to do it now, after we have applied any transactions from other nodes,
         // and after notifyTransactionDataReceived - otherwise the RollbackCommands would block.
         if (transactionTable != null) {
            transactionTable.cleanupLeaverTransactions(rpcManager.getTransport().getMembers());
         }

         // Any data for segments we do not own should be removed from data container and cache store
         // We need to discard data from all segments we don't own, not just those we previously owned,
         // when we lose membership (e.g. because there was a merge, the local partition was in degraded mode
         // and the other partition was available) or when L1 is enabled.
         Set<Integer> removedSegments;
         boolean wasMember = previousWriteCh != null ? previousWriteCh.getMembers().contains(rpcManager.getAddress()) : false;
         if (isMember || (!isMember && wasMember)) {
            removedSegments = new HashSet<>(newWriteCh.getNumSegments());
            for (int i = 0; i < newWriteCh.getNumSegments(); i++) {
               removedSegments.add(i);
            }
            Set<Integer> newSegments = getOwnedSegments(newWriteCh);
            removedSegments.removeAll(newSegments);

            try {
               removeStaleData(removedSegments);
            } catch (InterruptedException e) {
               Thread.currentThread().interrupt();
               throw new CacheException(e);
            }
         }
      }
   }

   private void awaitTotalOrderTransactions(CacheTopology cacheTopology, boolean isRebalance) {
      //in total order, we should wait for remote transactions before proceeding
      if (isTotalOrder) {
         if (trace) {
            log.trace("State Transfer in Total Order cache. Waiting for remote transactions to finish");
         }
         try {
            for (TotalOrderLatch block : totalOrderManager.notifyStateTransferStart(cacheTopology.getTopologyId(), isRebalance)) {
               block.awaitUntilUnBlock();
            }
         } catch (InterruptedException e) {
            //interrupted...
            Thread.currentThread().interrupt();
            throw new CacheException(e);
         }
         if (trace) {
            log.trace("State Transfer in Total Order cache. All remote transactions are finished. Moving on...");
         }
      }

   }

   private void notifyEndOfRebalanceIfNeeded(int topologyId, int rebalanceId) {
      if (waitingForState.get() && !hasActiveTransfers()) {
         if (waitingForState.compareAndSet(true, false)) {
            log.debugf("Finished receiving of segments for cache %s for topology %d.", cacheName, topologyId);
            stopApplyingState();
            stateTransferManager.notifyEndOfRebalance(topologyId, rebalanceId);
            List<? extends Future<Void>> futures = stateRequestCompletionService.drainCompletionQueue();
            boolean interrupted = false;
            for (Future<Void> future : futures) {
               // These will not block since they are already completed
               try {
                  future.get();
               } catch (InterruptedException e) {
                  // This shouldn't happen as each task is complete
                  interrupted = true;
               } catch (ExecutionException e) {
                  log.topologyUpdateError(topologyId, e.getCause());
               }
            }
            if (interrupted) {
               Thread.currentThread().interrupt();
            }
         }
      }
   }

   private Set<Integer> getOwnedSegments(ConsistentHash consistentHash) {
      Address address = rpcManager.getAddress();
      return consistentHash.getMembers().contains(address) ? consistentHash.getSegmentsForOwner(address)
            : InfinispanCollections.<Integer>emptySet();
   }

   @Override
   public void applyState(final Address sender, int topologyId, Collection<StateChunk> stateChunks) {
      ConsistentHash wCh = cacheTopology.getWriteConsistentHash();
      // Ignore responses received after we are no longer a member
      if (!wCh.getMembers().contains(rpcManager.getAddress())) {
         if (trace) {
            log.tracef("Ignoring received state because we are no longer a member of cache %s", cacheName);
         }
         return;
      }

      // Ignore segments that we requested for a previous rebalance
      // Can happen when the coordinator leaves, and the new coordinator cancels the rebalance in progress
      int rebalanceTopologyId = stateTransferTopologyId.get();
      if (rebalanceTopologyId == NO_REBALANCE_IN_PROGRESS) {
         log.debugf("Discarding state response with topology id %d for cache %s, we don't have a state transfer in progress",
               topologyId, cacheName);
         return;
      }
      if (topologyId < rebalanceTopologyId) {
         log.debugf("Discarding state response with old topology id %d for cache %s, state transfer request topology was %d",
               (Object)topologyId, cacheName, waitingForState.get());
         return;
      }

      if (trace) {
         log.tracef("Before applying the received state the data container of cache %s has %d keys", cacheName,
               dataContainer.size());
      }
      final Set<Integer> mySegments = wCh.getSegmentsForOwner(rpcManager.getAddress());
      final CountDownLatch countDownLatch = new CountDownLatch(stateChunks.size());
      for (final StateChunk stateChunk : stateChunks) {
         stateTransferExecutor.submit(new Callable<Void>() {
            @Override
            public Void call() throws Exception {
               applyChunk(sender, mySegments, stateChunk);
               countDownLatch.countDown();
               return null;
            }
         });
      }
      try {
         boolean await = countDownLatch.await(timeout, TimeUnit.MILLISECONDS);
         if (!await) {
            throw new TimeoutException("Timed out applying state");
         }
      } catch (InterruptedException e) {
         Thread.currentThread().interrupt();
         throw new CacheException(e);
      }

      if (trace) {
         log.tracef("After applying the received state the data container of cache %s has %d keys", cacheName,
               dataContainer.size());
         synchronized (transferMapsLock) {
            log.tracef("Segments not received yet for cache %s: %s", cacheName, transfersBySource);
         }
      }
   }

   private void applyChunk(Address sender, Set<Integer> mySegments, StateChunk stateChunk) {
      if (!mySegments.contains(stateChunk.getSegmentId())) {
         log.warnf("Discarding received cache entries for segment %d of cache %s because they do not belong to this node.", stateChunk.getSegmentId(), cacheName);
         return;
      }

      // Notify the inbound task that a chunk of cache entries was received
      InboundTransferTask inboundTransfer;
      synchronized (transferMapsLock) {
         inboundTransfer = transfersBySegment.get(stateChunk.getSegmentId());
      }
      if (inboundTransfer != null) {
         if (stateChunk.getCacheEntries() != null) {
            doApplyState(sender, stateChunk.getSegmentId(), stateChunk.getCacheEntries());
         }

         inboundTransfer.onStateReceived(stateChunk.getSegmentId(), stateChunk.isLastChunk());
      } else {
         log.warnf("Received unsolicited state from node %s for segment %d of cache %s", sender, stateChunk.getSegmentId(), cacheName);
      }
   }

   private void doApplyState(Address sender, int segmentId, Collection<InternalCacheEntry> cacheEntries) {
      if (trace) log.tracef("Applying new state chunk for segment %d of cache %s from node %s: received %d cache entries",
            segmentId, cacheName, sender, cacheEntries.size());

      // CACHE_MODE_LOCAL avoids handling by StateTransferInterceptor and any potential locks in StateTransferLock
      EnumSet<Flag> flags = EnumSet.of(PUT_FOR_STATE_TRANSFER, CACHE_MODE_LOCAL, IGNORE_RETURN_VALUES, SKIP_REMOTE_LOOKUP, SKIP_SHARED_CACHE_STORE, SKIP_OWNERSHIP_CHECK, SKIP_XSITE_BACKUP);
      for (InternalCacheEntry e : cacheEntries) {
         try {
            InvocationContext ctx;
            if (transactionManager != null) {
               // cache is transactional
               transactionManager.begin();
               ctx = icf.createInvocationContext(transactionManager.getTransaction(), true);
               ((TxInvocationContext) ctx).getCacheTransaction().setStateTransferFlag(PUT_FOR_STATE_TRANSFER);
            } else {
               // non-tx cache
               ctx = icf.createSingleKeyNonTxInvocationContext();
            }

            PutKeyValueCommand put = commandsFactory.buildPutKeyValueCommand(
                  e.getKey(), e.getValue(), e.getMetadata(), flags);

            boolean success = false;
            try {
               interceptorChain.invoke(ctx, put);
               success = true;
            } finally {
               if (ctx.isInTxScope()) {
                  if (success) {
                     try {
                        transactionManager.commit();
                     } catch (Throwable ex) {
                        log.errorf(ex, "Could not commit transaction created by state transfer of key %s", e.getKey());
                        if (transactionManager.getTransaction() != null) {
                           transactionManager.rollback();
                        }
                     }
                  } else {
                     transactionManager.rollback();
                  }
               }
            }
         } catch (Exception ex) {
            log.problemApplyingStateForKey(ex.getMessage(), e.getKey(), ex);
         }
      }
      if (trace) log.tracef("Finished applying chunk of segment %d of cache %s", segmentId, cacheName);
   }

   private void applyTransactions(Address sender, Collection<TransactionInfo> transactions, int topologyId) {
      log.debugf("Applying %d transactions for cache %s transferred from node %s", transactions.size(), cacheName, sender);
      if (isTransactional) {
         for (TransactionInfo transactionInfo : transactions) {
            GlobalTransaction gtx = transactionInfo.getGlobalTransaction();
            // Mark the global transaction as remote. Only used for logging, hashCode/equals ignore it.
            gtx.setRemote(true);

            CacheTransaction tx = transactionTable.getLocalTransaction(gtx);
            if (tx == null) {
               tx = transactionTable.getRemoteTransaction(gtx);
               if (tx == null) {
                  tx = transactionTable.getOrCreateRemoteTransaction(gtx, transactionInfo.getModifications());
                  // Force this node to replay the given transaction data by making it think it is 1 behind
                  ((RemoteTransaction) tx).setLookedUpEntriesTopology(topologyId - 1);
               }
            }
            for (Object key : transactionInfo.getLockedKeys()) {
               tx.addBackupLockForKey(key);
            }
         }
      }
   }

   // Must run after the PersistenceManager
   @Start(priority = 20)
   public void start() {
      isFetchEnabled = configuration.clustering().stateTransfer().fetchInMemoryState() || configuration.persistence().fetchPersistentState();
      //rpc options does not changes in runtime. we can use always the same instance.
      rpcOptions = rpcManager.getRpcOptionsBuilder(ResponseMode.SYNCHRONOUS)
            .timeout(timeout, TimeUnit.MILLISECONDS).build();
   }

   @Stop(priority = 20)
   @Override
   public void stop() {
      if (trace) {
         log.tracef("Shutting down StateConsumer of cache %s on node %s", cacheName, rpcManager.getAddress());
      }

      try {
         synchronized (transferMapsLock) {
            // cancel all inbound transfers
            stateRequestCompletionService.cancelQueuedTasks();
            stateRequestCompletionService.drainCompletionQueue();

            for (Iterator<List<InboundTransferTask>> it = transfersBySource.values().iterator(); it.hasNext(); ) {
               List<InboundTransferTask> inboundTransfers = it.next();
               it.remove();
               for (InboundTransferTask inboundTransfer : inboundTransfers) {
                  inboundTransfer.cancel();
               }
            }
            transfersBySource.clear();
            transfersBySegment.clear();
         }
      } catch (Throwable t) {
         log.errorf(t, "Failed to stop StateConsumer of cache %s on node %s", cacheName, rpcManager.getAddress());
      }
   }

   @Override
   public CacheTopology getCacheTopology() {
      return cacheTopology;
   }

   public void setKeyInvalidationListener(KeyInvalidationListener keyInvalidationListener) {
      this.keyInvalidationListener = keyInvalidationListener;
   }

   private void addTransfers(Set<Integer> segments) {
      log.debugf("Adding inbound state transfer for segments %s of cache %s", segments, cacheName);

      // the set of nodes that reported errors when fetching data from them - these will not be retried in this topology
      Set<Address> excludedSources = new HashSet<Address>();

      // the sources and segments we are going to get from each source
      Map<Address, Set<Integer>> sources = new HashMap<Address, Set<Integer>>();

      if (isTransactional && !isTotalOrder) {
         requestTransactions(segments, sources, excludedSources);
      }

      if (isFetchEnabled) {
         requestSegments(segments, sources, excludedSources);
      }

      if (trace) log.tracef("Finished adding inbound state transfer for segments %s of cache %s", segments, cacheName);
   }

   private void findSources(Set<Integer> segments, Map<Address, Set<Integer>> sources, Set<Address> excludedSources) {
      for (Integer segmentId : segments) {
         Address source = findSource(segmentId, excludedSources);
         // ignore all segments for which there are no other owners to pull data from.
         // these segments are considered empty (or lost) and do not require a state transfer
         if (source != null) {
            Set<Integer> segmentsFromSource = sources.get(source);
            if (segmentsFromSource == null) {
               segmentsFromSource = new HashSet<Integer>();
               sources.put(source, segmentsFromSource);
            }
            segmentsFromSource.add(segmentId);
         }
      }
   }

   private Address findSource(int segmentId, Set<Address> excludedSources) {
      List<Address> owners = cacheTopology.getReadConsistentHash().locateOwnersForSegment(segmentId);
      if (!owners.contains(rpcManager.getAddress())) {
         // We prefer that transactions are sourced from primary owners.
         // Needed in pessimistic mode, if the originator is the primary owner of the key than the lock
         // command is not replicated to the backup owners. See PessimisticDistributionInterceptor.acquireRemoteIfNeeded.
         for (int i = 0; i < owners.size(); i++) {
            Address o = owners.get(i);
            if (!o.equals(rpcManager.getAddress()) && !excludedSources.contains(o)) {
               return o;
            }
         }
         log.noLiveOwnersFoundForSegment(segmentId, cacheName, owners, excludedSources);
      }
      return null;
   }

   private void requestTransactions(Set<Integer> segments, Map<Address, Set<Integer>> sources, Set<Address> excludedSources) {
      findSources(segments, sources, excludedSources);

      boolean seenFailures = false;
      while (true) {
         Set<Integer> failedSegments = new HashSet<Integer>();
         int topologyId = cacheTopology.getTopologyId();
         for (Map.Entry<Address, Set<Integer>> sourceEntry : sources.entrySet()) {
            Address source = sourceEntry.getKey();
            Set<Integer> segmentsFromSource = sourceEntry.getValue();
            boolean failed = false;
            boolean exclude = false;
            try {
               Response response = getTransactions(source, segmentsFromSource, topologyId);
               if (response instanceof SuccessfulResponse) {
                  List<TransactionInfo> transactions = (List<TransactionInfo>) ((SuccessfulResponse) response).getResponseValue();
                  applyTransactions(source, transactions, topologyId);
               } else if (response instanceof CacheNotFoundResponse) {
                  log.debugf("Cache %s was stopped on node %s before sending transaction information", cacheName, source);
                  failed = true;
                  exclude = true;
               } else {
                  log.unsuccessfulResponseRetrievingTransactionsForSegments(source, response);
                  failed = true;
               }
            } catch (SuspectException e) {
               log.debugf("Node %s left the cluster before sending transaction information", source);
               failed = true;
               exclude = true;
            } catch (Exception e) {
               log.failedToRetrieveTransactionsForSegments(segments, cacheName, source, e);
               // The primary owner is still in the cluster, so we can't exclude it - see ISPN-4091
               failed = true;
            }

            // If requesting the transactions failed we need to retry
            if (failed) {
               failedSegments.addAll(segmentsFromSource);
            }
            // If the primary owner is no longer running, we can retry on a backup owner
            if (exclude) {
               excludedSources.add(source);
            }
         }

         if (failedSegments.isEmpty()) {
            break;
         }

         // look for other sources for all failed segments
         seenFailures = true;
         sources.clear();
         findSources(failedSegments, sources, excludedSources);
      }

      if (seenFailures) {
         // start fresh when next step starts (fetching segments)
         sources.clear();
      }
   }

   private Collection<DistributedCallable> getClusterListeners(CacheTopology topology) {
      for (Address source : topology.getMembers()) {
         // Don't send to ourselves
         if (!source.equals(rpcManager.getAddress())) {
            if (trace) {
               log.tracef("Requesting cluster listeners of cache %s from node %s", cacheName, source);
            }
            // get cluster listeners
            try {
               StateRequestCommand cmd = commandsFactory.buildStateRequestCommand(StateRequestCommand.Type.GET_CACHE_LISTENERS,
                                                                                  rpcManager.getAddress(), topology.getTopologyId(), null);
               Map<Address, Response> responses = rpcManager.invokeRemotely(Collections.singleton(source), cmd, rpcOptions);
               Response response = responses.get(source);
               if (response instanceof SuccessfulResponse) {
                  return (Collection<DistributedCallable>) ((SuccessfulResponse) response).getResponseValue();
               } else {
                  log.unsuccessfulResponseForClusterListeners(source, response);
               }
            } catch (CacheException e) {
               log.exceptionDuringClusterListenerRetrieval(source, e);
            }
         }
      }
      if (trace) log.trace("Unable to acquire cluster listeners from other members, assuming none are present");
      return Collections.emptySet();
   }

   private Response getTransactions(Address source, Set<Integer> segments, int topologyId) {
      if (trace) {
         log.tracef("Requesting transactions for segments %s of cache %s from node %s", segments, cacheName, source);
      }
      // get transactions and locks
      StateRequestCommand cmd = commandsFactory.buildStateRequestCommand(StateRequestCommand.Type.GET_TRANSACTIONS, rpcManager.getAddress(), topologyId, segments);
      Map<Address, Response> responses = rpcManager.invokeRemotely(Collections.singleton(source), cmd, rpcOptions);
      return responses.get(source);
   }

   private void requestSegments(Set<Integer> segments, Map<Address, Set<Integer>> sources, Set<Address> excludedSources) {
      if (sources.isEmpty()) {
         findSources(segments, sources, excludedSources);
      }

      for (Map.Entry<Address, Set<Integer>> e : sources.entrySet()) {
         addTransfer(e.getKey(), e.getValue());
      }
   }


   private void retryTransferTask(InboundTransferTask task) {
      if (trace) log.tracef("Retrying failed task: %s", task);
      task.cancel();

      // look for other sources for the failed segments and replace all failed tasks with new tasks to be retried
      // remove+add needs to be atomic
      synchronized (transferMapsLock) {
         Set<Integer> failedSegments = new HashSet<Integer>();
         Set<Address> excludedSources = new HashSet<>();
         if (removeTransfer(task)) {
            excludedSources.add(task.getSource());
            failedSegments.addAll(task.getSegments());
         }

         // should re-add only segments we still own and are not already in
         failedSegments.retainAll(getOwnedSegments(cacheTopology.getWriteConsistentHash()));

         Map<Address, Set<Integer>> sources = new HashMap<Address, Set<Integer>>();
         findSources(failedSegments, sources, excludedSources);
         for (Map.Entry<Address, Set<Integer>> e : sources.entrySet()) {
            addTransfer(e.getKey(), e.getValue());
         }
      }
   }

   /**
    * Cancel transfers for segments we no longer own.
    *
    * @param removedSegments segments to be cancelled
    */
   private void cancelTransfers(Set<Integer> removedSegments) {
      synchronized (transferMapsLock) {
         List<Integer> segmentsToCancel = new ArrayList<Integer>(removedSegments);
         while (!segmentsToCancel.isEmpty()) {
            int segmentId = segmentsToCancel.remove(0);
            InboundTransferTask inboundTransfer = transfersBySegment.get(segmentId);
            if (inboundTransfer != null) { // we need to check the transfer was not already completed
               Set<Integer> cancelledSegments = new HashSet<Integer>(removedSegments);
               cancelledSegments.retainAll(inboundTransfer.getSegments());
               segmentsToCancel.removeAll(cancelledSegments);
               transfersBySegment.keySet().removeAll(cancelledSegments);
               //this will also remove it from transfersBySource if the entire task gets cancelled
               inboundTransfer.cancelSegments(cancelledSegments);
               if (inboundTransfer.isCancelled()) {
                  removeTransfer(inboundTransfer);
               };
            }
         }
      }
   }

   private void removeStaleData(final Set<Integer> removedSegments) throws InterruptedException {
      log.debugf("Removing no longer owned entries for cache %s", cacheName);
      if (keyInvalidationListener != null) {
         keyInvalidationListener.beforeInvalidation(removedSegments, InfinispanCollections.<Integer>emptySet());
      }

      if (removedSegments.isEmpty())
         return;

      // Keys that might have been in L1, and need to be removed from the data container
      final ConcurrentHashSet<Object> keysToInvalidate = new ConcurrentHashSet<Object>();
      // Keys that we used to own, and need to be removed from the data container AND the cache stores
      final ConcurrentHashSet<Object> keysToRemove = new ConcurrentHashSet<Object>();

      dataContainer.executeTask(KeyFilter.ACCEPT_ALL_FILTER, (o, ice) -> {
         Object key = ice.getKey();
         int keySegment = getSegment(key);
         if (removedSegments.contains(keySegment)) {
            keysToRemove.add(key);
         }
      });

      // gather all keys from cache store that belong to the segments that are being removed/moved to L1
      if (!removedSegments.isEmpty()) {
         try {
            KeyFilter filter = new KeyFilter() {
               @Override
               public boolean accept(Object key) {
                  if (dataContainer.containsKey(key))
                     return false;
                  int keySegment = getSegment(key);
                  return (removedSegments.contains(keySegment));
               }
            };
            persistenceManager.processOnAllStores(filter, new AdvancedCacheLoader.CacheLoaderTask() {
               @Override
               public void processEntry(MarshalledEntry marshalledEntry, AdvancedCacheLoader.TaskContext taskContext) throws InterruptedException {
                  keysToRemove.add(marshalledEntry.getKey());
               }
            }, false, false, PRIVATE);
         } catch (CacheException e) {
            log.failedLoadingKeysFromCacheStore(e);
         }
      }

      if (!keysToRemove.isEmpty()) {
         try {
            InvalidateCommand invalidateCmd = commandsFactory.buildInvalidateCommand(EnumSet.of(CACHE_MODE_LOCAL, SKIP_LOCKING), keysToRemove.toArray());
            InvocationContext ctx = icf.createNonTxInvocationContext();
            interceptorChain.invoke(ctx, invalidateCmd);

            if (trace) log.tracef("Removed %d keys, data container now has %d keys", keysToRemove.size(), dataContainer.size());
         } catch (CacheException e) {
            log.failedToInvalidateKeys(e);
         }
      }
   }

   /**
    * Check if any of the existing transfers should be restarted from a different source because the initial source is no longer a member.
    *
    * @param cacheTopology
    * @param addedSegments
    */
   private void restartBrokenTransfers(CacheTopology cacheTopology, Set<Integer> addedSegments) {
      Set<Address> members = new HashSet<Address>(cacheTopology.getReadConsistentHash().getMembers());
      synchronized (transferMapsLock) {
         for (Iterator<Address> it = transfersBySource.keySet().iterator(); it.hasNext(); ) {
            Address source = it.next();
            if (!members.contains(source)) {
               if (trace) {
                  log.tracef("Removing inbound transfers from source %s for cache %s", source, cacheName);
               }
               List<InboundTransferTask> inboundTransfers = transfersBySource.get(source);
               it.remove();
               for (InboundTransferTask inboundTransfer : inboundTransfers) {
                  // these segments will be restarted if they are still in new write CH
                  if (trace) {
                     log.tracef("Removing inbound transfers for segments %s from source %s for cache %s", inboundTransfer.getSegments(), source, cacheName);
                  }
                  inboundTransfer.cancel();
                  transfersBySegment.keySet().removeAll(inboundTransfer.getSegments());
                  addedSegments.addAll(inboundTransfer.getUnfinishedSegments());
               }
            }
         }

         // exclude those that are already in progress from a valid source
         addedSegments.removeAll(transfersBySegment.keySet());
      }
   }

   private int getSegment(Object key) {
      // here we can use any CH version because the routing table is not involved in computing the segment
      return cacheTopology.getReadConsistentHash().getSegment(key);
   }

   private InboundTransferTask addTransfer(Address source, Set<Integer> segmentsFromSource) {
      final InboundTransferTask inboundTransfer;

      synchronized (transferMapsLock) {
         if (trace) {
            log.tracef("Adding transfer from %s for segments %s", source, segmentsFromSource);
         }
         segmentsFromSource.removeAll(transfersBySegment.keySet());  // already in progress segments are excluded
         if (segmentsFromSource.isEmpty()) {
            if (trace) {
               log.tracef("All segments are already in progress, skipping");
            }
            return null;
         }

         inboundTransfer = new InboundTransferTask(segmentsFromSource, source,
               cacheTopology.getTopologyId(), this, rpcManager, commandsFactory, timeout, cacheName);
         for (int segmentId : segmentsFromSource) {
            transfersBySegment.put(segmentId, inboundTransfer);
         }
         List<InboundTransferTask> inboundTransfers = transfersBySource.get(inboundTransfer.getSource());
         if (inboundTransfers == null) {
            inboundTransfers = new ArrayList<InboundTransferTask>();
            transfersBySource.put(inboundTransfer.getSource(), inboundTransfers);
         }
         inboundTransfers.add(inboundTransfer);
      }

      stateRequestCompletionService.submit(new Callable<Void>() {
         @Override
         public Void call() throws Exception {
            inboundTransfer.requestSegments();

            if (trace)
               log.tracef("Waiting for inbound transfer to finish: %s", inboundTransfer);
            stateRequestCompletionService.continueTaskInBackground();
            return null;
         }
      });
      return inboundTransfer;
   }

   private boolean removeTransfer(InboundTransferTask inboundTransfer) {
      synchronized (transferMapsLock) {
         if (trace) log.tracef("Removing inbound transfers for segments %s from source %s for cache %s",
               inboundTransfer.getSegments(), inboundTransfer.getSource(), cacheName);
         List<InboundTransferTask> transfers = transfersBySource.get(inboundTransfer.getSource());
         if (transfers != null) {
            if (transfers.remove(inboundTransfer)) {
               if (transfers.isEmpty()) {
                  transfersBySource.remove(inboundTransfer.getSource());
               }
               transfersBySegment.keySet().removeAll(inboundTransfer.getSegments());
               return true;
            }
         }
      }
      return false;
   }

   void onTaskCompletion(final InboundTransferTask inboundTransfer) {
      // This will execute only after inboundTransfer.requestSegments() finished
      stateRequestCompletionService.backgroundTaskFinished(new Callable<Void>() {
         @Override
         public Void call() throws Exception {
            removeTransfer(inboundTransfer);

            if (!inboundTransfer.isCompletedSuccessfully() && !inboundTransfer.isCancelled()) {
               retryTransferTask(inboundTransfer);
            } else {
               if (trace) log.tracef("Inbound transfer finished: %s", inboundTransfer);
               notifyEndOfRebalanceIfNeeded(cacheTopology.getTopologyId(), cacheTopology.getRebalanceId());
            }
            return null;
         }
      });
   }

   public interface KeyInvalidationListener {
      void beforeInvalidation(Set<Integer> removedSegments, Set<Integer> staleL1Segments);
   }
}


File: core/src/main/java/org/infinispan/statetransfer/StateTransferInterceptor.java
package org.infinispan.statetransfer;

import org.infinispan.commands.FlagAffectedCommand;
import org.infinispan.commands.TopologyAffectedCommand;
import org.infinispan.commands.VisitableCommand;
import org.infinispan.commands.control.LockControlCommand;
import org.infinispan.commands.read.GetAllCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.commands.tx.RollbackCommand;
import org.infinispan.commands.tx.TransactionBoundaryCommand;
import org.infinispan.commands.write.ApplyDeltaCommand;
import org.infinispan.commands.write.ClearCommand;
import org.infinispan.commands.write.EvictCommand;
import org.infinispan.commands.write.InvalidateCommand;
import org.infinispan.commands.write.InvalidateL1Command;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.commands.write.PutMapCommand;
import org.infinispan.commands.write.RemoveCommand;
import org.infinispan.commands.write.ReplaceCommand;
import org.infinispan.commands.write.WriteCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.util.InfinispanCollections;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.context.impl.TxInvocationContext;
import org.infinispan.factories.ComponentRegistry;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.interceptors.base.BaseStateTransferInterceptor;
import org.infinispan.remoting.RemoteException;
import org.infinispan.remoting.responses.UnsureResponse;
import org.infinispan.remoting.transport.Address;
import org.infinispan.remoting.transport.Transport;
import org.infinispan.remoting.transport.jgroups.SuspectException;
import org.infinispan.topology.CacheTopology;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.Set;

//todo [anistor] command forwarding breaks the rule that we have only one originator for a command. this opens now the possibility to have two threads processing incoming remote commands for the same TX
/**
 * This interceptor has two tasks:
 * <ol>
 *    <li>If the command's topology id is higher than the current topology id,
 *    wait for the node to receive transaction data for the new topology id.</li>
 *    <li>If the topology id changed during a command's execution, forward the command to the new owners.</li>
 * </ol>
 *
 * Note that we don't keep track of old cache topologies (yet), so we actually forward the command to all the owners
 * -- not just the ones added in the new topology. Transactional commands are idempotent, so this is fine.
 *
 * In non-transactional mode, the semantic of these tasks changes:
 * <ol>
 *    <li>We don't have transaction data, so the interceptor only waits for the new topology to be installed.</li>
 *    <li>Instead of forwarding commands from any owner, we retry the command on the originator.</li>
 * </ol>
 *
 * @author anistor@redhat.com
 * @since 5.2
 */
public class StateTransferInterceptor extends BaseStateTransferInterceptor {

   private static final Log log = LogFactory.getLog(StateTransferInterceptor.class);
   private static boolean trace = log.isTraceEnabled();

   private StateTransferManager stateTransferManager;
   private Transport transport;
   private ComponentRegistry componentRegistry;

   private final AffectedKeysVisitor affectedKeysVisitor = new AffectedKeysVisitor();

   @Override
   protected Log getLog() {
      return log;
   }

   @Inject
   public void init(StateTransferManager stateTransferManager, Transport transport,
         ComponentRegistry componentRegistry) {
      this.stateTransferManager = stateTransferManager;
      this.transport = transport;
      this.componentRegistry = componentRegistry;
   }

   @Override
   public Object visitPrepareCommand(TxInvocationContext ctx, PrepareCommand command) throws Throwable {
      return handleTxCommand(ctx, command);
   }

   @Override
   public Object visitCommitCommand(TxInvocationContext ctx, CommitCommand command) throws Throwable {
      return handleTxCommand(ctx, command);
   }

   @Override
   public Object visitRollbackCommand(TxInvocationContext ctx, RollbackCommand command) throws Throwable {
      return handleTxCommand(ctx, command);
   }

   @Override
   public Object visitLockControlCommand(TxInvocationContext ctx, LockControlCommand command) throws Throwable {
      return handleTxCommand(ctx, command);
   }

   @Override
   public Object visitPutKeyValueCommand(InvocationContext ctx, PutKeyValueCommand command) throws Throwable {
      return handleWriteCommand(ctx, command);
   }

   @Override
   public Object visitPutMapCommand(InvocationContext ctx, PutMapCommand command) throws Throwable {
      return handleWriteCommand(ctx, command);
   }

   @Override
   public Object visitApplyDeltaCommand(InvocationContext ctx, ApplyDeltaCommand command) throws Throwable {
      return handleWriteCommand(ctx, command);
   }

   @Override
   public Object visitRemoveCommand(InvocationContext ctx, RemoveCommand command) throws Throwable {
      return handleWriteCommand(ctx, command);
   }

   @Override
   public Object visitReplaceCommand(InvocationContext ctx, ReplaceCommand command) throws Throwable {
      return handleWriteCommand(ctx, command);
   }

   @Override
   public Object visitClearCommand(InvocationContext ctx, ClearCommand command) throws Throwable {
      return handleWriteCommand(ctx, command);
   }

   @Override
   public Object visitInvalidateCommand(InvocationContext ctx, InvalidateCommand command) throws Throwable {
      return handleWriteCommand(ctx, command);
   }

   @Override
   public Object visitInvalidateL1Command(InvocationContext ctx, InvalidateL1Command command) throws Throwable {
      // no need to forward this command
      return invokeNextInterceptor(ctx, command);
   }

   @Override
   public Object visitEvictCommand(InvocationContext ctx, EvictCommand command) throws Throwable {
      // it's not necessary to propagate eviction to the new owners in case of state transfer
      return invokeNextInterceptor(ctx, command);
   }

   @Override
   public Object visitGetAllCommand(InvocationContext ctx, GetAllCommand command) throws Throwable {
      if (isLocalOnly(ctx, command)) {
         return invokeNextInterceptor(ctx, command);
      }
      CacheTopology beginTopology = stateTransferManager.getCacheTopology();
      command.setConsistentHashAndAddress(beginTopology.getReadConsistentHash(),
            transport.getAddress());
      updateTopologyId(command);
      try {
         return invokeNextInterceptor(ctx, command);
      } catch (CacheException e) {
         Throwable ce = e;
         while (ce instanceof RemoteException) {
            ce = ce.getCause();
         }
         if (!(ce instanceof OutdatedTopologyException) && !(ce instanceof SuspectException))
            throw e;

         // We increment the topology id so that updateTopologyIdAndWaitForTransactionData waits for the next topology.
         // Without this, we could retry the command too fast and we could get the OutdatedTopologyException again.
         if (trace) log.tracef("Retrying command because of topology change, current topology is %d: %s", command);
         int newTopologyId = Math.max(currentTopologyId(), command.getTopologyId() + 1);
         command.setTopologyId(newTopologyId);
         waitForTopology(newTopologyId);

         return visitGetAllCommand(ctx, command);
      }
   }

   /**
    * Special processing required for transaction commands.
    *
    */
   private Object handleTxCommand(TxInvocationContext ctx, TransactionBoundaryCommand command) throws Throwable {
      // For local commands we may not have a GlobalTransaction yet
      Address origin = ctx.isOriginLocal() ? ctx.getOrigin() : ctx.getGlobalTransaction().getAddress();
      if (trace) log.tracef("handleTxCommand for command %s, origin %s", command, origin);

      if (isLocalOnly(ctx, command)) {
         return invokeNextInterceptor(ctx, command);
      }
      updateTopologyId(command);

      int retryTopologyId = -1;
      Object localResult = null;
      try {
         localResult = invokeNextInterceptor(ctx, command);
      } catch (OutdatedTopologyException e) {
         // This can only happen on the originator
         retryTopologyId = Math.max(currentTopologyId(), command.getTopologyId() + 1);
      }

      // We need to forward the command to the new owners, if the command was asynchronous
      boolean async = isTxCommandAsync(command);
      if (async) {
         stateTransferManager.forwardCommandIfNeeded(command, getAffectedKeys(ctx, command), origin, false);
         return null;
      }

      if (ctx.isOriginLocal()) {
         // On the originator, we only retry if we got an OutdatedTopologyException
         // Which could be caused either by an owner leaving or by an owner having a newer topology
         // No need to retry just because we have a new topology on the originator, all entries were wrapped anyway
         if (retryTopologyId > 0) {
            // Only the originator can retry the command
            command.setTopologyId(retryTopologyId);
            waitForTransactionData(retryTopologyId);

            log.tracef("Retrying command %s for topology %d", command, retryTopologyId);
            localResult = handleTxCommand(ctx, command);
         }
      } else {
         if (currentTopologyId() > command.getTopologyId()) {
            // Signal the originator to retry
            localResult = UnsureResponse.INSTANCE;
         }
      }

      return localResult;
   }

   private boolean isTxCommandAsync(TransactionBoundaryCommand command) {
      boolean async = false;
      if (command instanceof CommitCommand || command instanceof RollbackCommand) {
         async = !cacheConfiguration.transaction().syncCommitPhase();
      } else if (command instanceof PrepareCommand) {
         async = !cacheConfiguration.clustering().cacheMode().isSynchronous();
      }
      return async;
   }

   protected Object handleWriteCommand(InvocationContext ctx, WriteCommand command) throws Throwable {
      if (ctx.isInTxScope()) {
         return handleTxWriteCommand(ctx, command);
      } else {
         return handleNonTxWriteCommand(ctx, command);
      }
   }

   private Object handleTxWriteCommand(InvocationContext ctx, WriteCommand command) throws Throwable {
      Address origin = ctx.getOrigin();
      if (trace) log.tracef("handleTxWriteCommand for command %s, origin %s", command, origin);

      if (isLocalOnly(ctx, command)) {
         return invokeNextInterceptor(ctx, command);
      }
      updateTopologyId(command);

      int retryTopologyId = -1;
      Object localResult = null;
      try {
         localResult = invokeNextInterceptor(ctx, command);
      } catch (OutdatedTopologyException e) {
         // This can only happen on the originator
         retryTopologyId = Math.max(currentTopologyId(), command.getTopologyId() + 1);
      }

      if (ctx.isOriginLocal()) {
         // On the originator, we only retry if we got an OutdatedTopologyException
         // Which could be caused either by an owner leaving or by an owner having a newer topology
         // No need to retry just because we have a new topology on the originator, all entries were wrapped anyway
         if (retryTopologyId > 0) {
            // Only the originator can retry the command
            command.setTopologyId(retryTopologyId);
            waitForTransactionData(retryTopologyId);

            log.tracef("Retrying command %s for topology %d", command, retryTopologyId);
            localResult = handleTxWriteCommand(ctx, command);
         }
      } else {
         if (currentTopologyId() > command.getTopologyId()) {
            // Signal the originator to retry
            return UnsureResponse.INSTANCE;
         }
      }

      // No need to forward tx write commands.
      // Ancillary LockControlCommands will be forwarded by handleTxCommand on the target nodes.
      return localResult;
   }

   /**
    * For non-tx write commands, we retry the command locally if the topology changed, instead of forwarding to the
    * new owners like we do for tx commands. But we only retry on the originator, and only if the command doesn't have
    * the {@code CACHE_MODE_LOCAL} flag.
    */
   private Object handleNonTxWriteCommand(InvocationContext ctx, WriteCommand command) throws Throwable {
      if (trace) log.tracef("handleNonTxWriteCommand for command %s, topology id %d", command, command.getTopologyId());

      if (isLocalOnly(ctx, command)) {
         return invokeNextInterceptor(ctx, command);
      }

      updateTopologyId(command);

      // Only catch OutdatedTopologyExceptions on the originator
      if (!ctx.isOriginLocal()) {
         return invokeNextInterceptor(ctx, command);
      }

      int commandTopologyId = command.getTopologyId();
      Object localResult;
      try {
         localResult = invokeNextInterceptor(ctx, command);
         return localResult;
      } catch (CacheException e) {
         Throwable ce = e;
         while (ce instanceof RemoteException) {
            ce = ce.getCause();
         }
         if (!(ce instanceof OutdatedTopologyException) && !(ce instanceof SuspectException))
            throw e;

         // We increment the topology id so that updateTopologyIdAndWaitForTransactionData waits for the next topology.
         // Without this, we could retry the command too fast and we could get the OutdatedTopologyException again.
         int currentTopologyId = currentTopologyId();
         if (trace) log.tracef("Retrying command because of topology change, current topology is %d: %s",
                 currentTopologyId, command);
         int newTopologyId = Math.max(currentTopologyId, commandTopologyId + 1);
         command.setTopologyId(newTopologyId);
         waitForTransactionData(newTopologyId);

         command.setFlags(Flag.COMMAND_RETRY);
         localResult = handleNonTxWriteCommand(ctx, command);
      }

      // We retry the command every time the topology changes, either in NonTxConcurrentDistributionInterceptor or in
      // EntryWrappingInterceptor. So we don't need to forward the command again here (without holding a lock).
      // stateTransferManager.forwardCommandIfNeeded(command, command.getAffectedKeys(), ctx.getOrigin(), false);
      return localResult;
   }

   @Override
   protected Object handleDefault(InvocationContext ctx, VisitableCommand command) throws Throwable {
      if (command instanceof TopologyAffectedCommand) {
         return handleTopologyAffectedCommand(ctx, command, ctx.getOrigin());
      } else {
         return invokeNextInterceptor(ctx, command);
      }
   }

   private Object handleTopologyAffectedCommand(InvocationContext ctx, VisitableCommand command,
                                                Address origin) throws Throwable {
      if (trace) log.tracef("handleTopologyAffectedCommand for command %s, origin %s", command, origin);

      if (isLocalOnly(ctx, command)) {
         return invokeNextInterceptor(ctx, command);
      }
      updateTopologyId((TopologyAffectedCommand) command);

      return invokeNextInterceptor(ctx, command);
   }

   private boolean isLocalOnly(InvocationContext ctx, VisitableCommand command) {
      boolean cacheModeLocal = false;
      if (command instanceof FlagAffectedCommand) {
         cacheModeLocal = ((FlagAffectedCommand)command).hasFlag(Flag.CACHE_MODE_LOCAL);
      }
      return cacheModeLocal;
   }

   @SuppressWarnings("unchecked")
   private Set<Object> getAffectedKeys(InvocationContext ctx, VisitableCommand command) {
      Set<Object> affectedKeys = null;
      try {
         affectedKeys = (Set<Object>) command.acceptVisitor(ctx, affectedKeysVisitor);
      } catch (Throwable throwable) {
         // impossible to reach this
      }
      if (affectedKeys == null) {
         affectedKeys = InfinispanCollections.emptySet();
      }
      return affectedKeys;
   }
}


File: core/src/main/java/org/infinispan/statetransfer/StateTransferManager.java
package org.infinispan.statetransfer;

import org.infinispan.commands.TopologyAffectedCommand;
import org.infinispan.factories.scopes.Scope;
import org.infinispan.factories.scopes.Scopes;
import org.infinispan.jmx.annotations.DataType;
import org.infinispan.jmx.annotations.MBean;
import org.infinispan.jmx.annotations.ManagedAttribute;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.transport.Address;
import org.infinispan.topology.CacheTopology;

import java.util.Map;
import java.util.Set;

/**
 * A component that manages the state transfer when the topology of the cluster changes.
 *
 * @author Dan Berindei <dan@infinispan.org>
 * @author Mircea Markus
 * @author anistor@redhat.com
 * @since 5.1
 */
@Scope(Scopes.NAMED_CACHE)
@MBean(objectName = "StateTransferManager", description = "Component that handles state transfer")
public interface StateTransferManager {

   //todo [anistor] this is inaccurate. this node does not hold state yet in current implementation
   @ManagedAttribute(description = "If true, the node has successfully joined the grid and is considered to hold state.  If false, the join process is still in progress.", displayName = "Is join completed?", dataType = DataType.TRAIT)
   boolean isJoinComplete();

   /**
    * Checks if an inbound state transfer is in progress.
    */
   @ManagedAttribute(description = "Checks whether there is a pending inbound state transfer on this cluster member.", displayName = "Is state transfer in progress?", dataType = DataType.TRAIT)
   boolean isStateTransferInProgress();

   /**
    * Checks if an inbound state transfer is in progress for a given key.
    *
    * @param key
    * @return
    */
   boolean isStateTransferInProgressForKey(Object key);

   CacheTopology getCacheTopology();

   void start() throws Exception;

   void stop();

   /**
    * If there is an state transfer happening at the moment, this method forwards the supplied
    * command to the nodes that are new owners of the data, in order to assure consistency.
    */
   Map<Address, Response> forwardCommandIfNeeded(TopologyAffectedCommand command, Set<Object> affectedKeys, Address origin, boolean sync);

   void notifyEndOfRebalance(int topologyId, int rebalanceId);

   /**
    * @return  true if this node has already received the first rebalance start
    */
   boolean ownsData();

   /**
    * @return The id of the first cache topology in which the local node was a member
    *    (even if it didn't own any data).
    */
   int getFirstTopologyAsMember();
}


File: core/src/main/java/org/infinispan/statetransfer/StateTransferManagerImpl.java
package org.infinispan.statetransfer;

import org.infinispan.Cache;
import org.infinispan.commands.TopologyAffectedCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.global.GlobalConfiguration;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.distribution.ch.ConsistentHashFactory;
import org.infinispan.distribution.ch.impl.DefaultConsistentHashFactory;
import org.infinispan.distribution.ch.impl.ReplicatedConsistentHashFactory;
import org.infinispan.distribution.ch.impl.TopologyAwareConsistentHashFactory;
import org.infinispan.distribution.group.GroupManager;
import org.infinispan.distribution.group.GroupingConsistentHash;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.factories.annotations.Start;
import org.infinispan.factories.annotations.Stop;
import org.infinispan.notifications.cachelistener.CacheNotifier;
import org.infinispan.partitionhandling.impl.PartitionHandlingManager;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.transport.Address;
import org.infinispan.topology.CacheJoinInfo;
import org.infinispan.topology.CacheTopology;
import org.infinispan.topology.CacheTopologyHandler;
import org.infinispan.topology.LocalTopologyManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * {@link StateTransferManager} implementation.
 *
 * @author anistor@redhat.com
 * @since 5.2
 */
public class StateTransferManagerImpl implements StateTransferManager {

   private static final Log log = LogFactory.getLog(StateTransferManagerImpl.class);
   private static final boolean trace = log.isTraceEnabled();

   private StateConsumer stateConsumer;
   private StateProvider stateProvider;
   private PartitionHandlingManager partitionHandlingManager;
   private String cacheName;
   private CacheNotifier cacheNotifier;
   private Configuration configuration;
   private GlobalConfiguration globalConfiguration;
   private RpcManager rpcManager;
   private GroupManager groupManager;   // optional
   private LocalTopologyManager localTopologyManager;

   private final CountDownLatch initialStateTransferComplete = new CountDownLatch(1);
   // The first topology in which the local node was a member. Any command with a lower
   // topology id will be ignored.
   private volatile int firstTopologyAsMember = Integer.MAX_VALUE;

   public StateTransferManagerImpl() {
   }

   @Inject
   public void init(StateConsumer stateConsumer,
                    StateProvider stateProvider,
                    Cache cache,
                    CacheNotifier cacheNotifier,
                    Configuration configuration,
                    GlobalConfiguration globalConfiguration,
                    RpcManager rpcManager,
                    GroupManager groupManager,
                    LocalTopologyManager localTopologyManager,
                    PartitionHandlingManager partitionHandlingManager) {
      this.stateConsumer = stateConsumer;
      this.stateProvider = stateProvider;
      this.partitionHandlingManager = partitionHandlingManager;
      this.cacheName = cache.getName();
      this.cacheNotifier = cacheNotifier;
      this.configuration = configuration;
      this.globalConfiguration = globalConfiguration;
      this.rpcManager = rpcManager;
      this.groupManager = groupManager;
      this.localTopologyManager = localTopologyManager;
   }

   // needs to be AFTER the DistributionManager and *after* the cache loader manager (if any) inits and preloads
   @Start(priority = 60)
   @Override
   public void start() throws Exception {
      if (trace) {
         log.tracef("Starting StateTransferManager of cache %s on node %s", cacheName, rpcManager.getAddress());
      }

      CacheJoinInfo joinInfo = new CacheJoinInfo(
            pickConsistentHashFactory(),
            configuration.clustering().hash().hash(),
            configuration.clustering().hash().numSegments(),
            configuration.clustering().hash().numOwners(),
            configuration.clustering().stateTransfer().timeout(),
            configuration.transaction().transactionProtocol().isTotalOrder(),
            configuration.clustering().cacheMode().isDistributed(),
            configuration.clustering().hash().capacityFactor());

      CacheTopology initialTopology = localTopologyManager.join(cacheName, joinInfo, new CacheTopologyHandler() {
         @Override
         public void updateConsistentHash(CacheTopology cacheTopology) {
            doTopologyUpdate(cacheTopology, false);
         }

         @Override
         public void rebalance(CacheTopology cacheTopology) {
            doTopologyUpdate(cacheTopology, true);
         }
      }, partitionHandlingManager);

      if (trace) {
         log.tracef("StateTransferManager of cache %s on node %s received initial topology %s", cacheName, rpcManager.getAddress(), initialTopology);
      }
   }

   /**
    * If no ConsistentHashFactory was explicitly configured we choose a suitable one based on cache mode.
    */
   private ConsistentHashFactory pickConsistentHashFactory() {
      ConsistentHashFactory factory = configuration.clustering().hash().consistentHashFactory();
      if (factory == null) {
         CacheMode cacheMode = configuration.clustering().cacheMode();
         if (cacheMode.isClustered()) {
            if (cacheMode.isDistributed()) {
               if (globalConfiguration.transport().hasTopologyInfo()) {
                  factory = new TopologyAwareConsistentHashFactory();
               } else {
                  factory = new DefaultConsistentHashFactory();
               }
            } else {
               // this is also used for invalidation mode
               factory = new ReplicatedConsistentHashFactory();
            }
         }
      }
      return factory;
   }

   /**
    * Decorates the given cache topology to add key grouping. The ConsistentHash objects of the cache topology
    * are wrapped to provide key grouping (if configured).
    *
    * @param cacheTopology the given cache topology
    * @return the decorated topology
    */
   private CacheTopology addGrouping(CacheTopology cacheTopology) {
      if (groupManager == null) {
         return cacheTopology;
      }

      ConsistentHash currentCH = cacheTopology.getCurrentCH();
      currentCH = new GroupingConsistentHash(currentCH, groupManager);
      ConsistentHash pendingCH = cacheTopology.getPendingCH();
      if (pendingCH != null) {
         pendingCH = new GroupingConsistentHash(pendingCH, groupManager);
      }
      ConsistentHash unionCH = cacheTopology.getUnionCH();
      if (unionCH != null) {
         unionCH = new GroupingConsistentHash(unionCH, groupManager);
      }
      return new CacheTopology(cacheTopology.getTopologyId(), cacheTopology.getRebalanceId(), currentCH, pendingCH,
            unionCH, cacheTopology.getActualMembers());
   }

   private void doTopologyUpdate(CacheTopology newCacheTopology, boolean isRebalance) {
      CacheTopology oldCacheTopology = stateConsumer.getCacheTopology();

      if (oldCacheTopology != null && oldCacheTopology.getTopologyId() > newCacheTopology.getTopologyId()) {
         throw new IllegalStateException("Old topology is higher: old=" + oldCacheTopology + ", new=" + newCacheTopology);
      }

      if (trace) {
         log.tracef("Installing new cache topology %s on cache %s", newCacheTopology, cacheName);
      }

      // No need for extra synchronization here, since LocalTopologyManager already serializes topology updates.
      if (firstTopologyAsMember == Integer.MAX_VALUE && newCacheTopology.getMembers().contains(rpcManager.getAddress())) {
         firstTopologyAsMember = newCacheTopology.getTopologyId();
         if (trace) log.tracef("This is the first topology %d in which the local node is a member", firstTopologyAsMember);
      }

      // handle grouping
      newCacheTopology = addGrouping(newCacheTopology);

      cacheNotifier.notifyTopologyChanged(oldCacheTopology, newCacheTopology, newCacheTopology.getTopologyId(), true);

      stateConsumer.onTopologyUpdate(newCacheTopology, isRebalance);
      stateProvider.onTopologyUpdate(newCacheTopology, isRebalance);

      cacheNotifier.notifyTopologyChanged(oldCacheTopology, newCacheTopology, newCacheTopology.getTopologyId(), false);

      if (initialStateTransferComplete.getCount() > 0) {
         boolean isJoined = stateConsumer.getCacheTopology().getReadConsistentHash().getMembers().contains(rpcManager.getAddress());
         if (isJoined) {
            initialStateTransferComplete.countDown();
            log.tracef("Initial state transfer complete for cache %s on node %s", cacheName, rpcManager.getAddress());
         }
      }
   }

   @Start(priority = 1000)
   @SuppressWarnings("unused")
   public void waitForInitialStateTransferToComplete() throws Exception {
      if (configuration.clustering().stateTransfer().awaitInitialTransfer()) {
         if (!localTopologyManager.isRebalancingEnabled()) {
            initialStateTransferComplete.countDown();
         }
         if (trace) log.tracef("Waiting for initial state transfer to finish for cache %s on %s", cacheName, rpcManager.getAddress());
         boolean success = initialStateTransferComplete.await(configuration.clustering().stateTransfer().timeout(), TimeUnit.MILLISECONDS);
         if (!success) {
            throw new CacheException(String.format("Initial state transfer timed out for cache %s on %s",
                  cacheName, rpcManager.getAddress()));
         }
      }
   }

   @Stop(priority = 20)
   @Override
   public void stop() {
      if (trace) {
         log.tracef("Shutting down StateTransferManager of cache %s on node %s", cacheName, rpcManager.getAddress());
      }
      initialStateTransferComplete.countDown();
      localTopologyManager.leave(cacheName);
   }

   @Override
   public boolean isJoinComplete() {
      return stateConsumer.getCacheTopology() != null; // TODO [anistor] this does not mean we have received a topology update or a rebalance yet
   }

   @Override
   public boolean isStateTransferInProgress() {
      return stateConsumer.isStateTransferInProgress();
   }

   @Override
   public boolean isStateTransferInProgressForKey(Object key) {
      return stateConsumer.isStateTransferInProgressForKey(key);
   }

   @Override
   public CacheTopology getCacheTopology() {
      return stateConsumer.getCacheTopology();
   }

   @Override
   public Map<Address, Response> forwardCommandIfNeeded(TopologyAffectedCommand command, Set<Object> affectedKeys,
                                                        Address origin, boolean sync) {
      int cmdTopologyId = command.getTopologyId();
      // forward commands with older topology ids to their new targets
      // but we need to make sure we have the latest topology
      CacheTopology cacheTopology = getCacheTopology();
      int localTopologyId = cacheTopology != null ? cacheTopology.getTopologyId() : -1;
      // if it's a tx/lock/write command, forward it to the new owners
      if (trace) {
         log.tracef("CommandTopologyId=%s, localTopologyId=%s", cmdTopologyId, localTopologyId);
      }

      if (cmdTopologyId < localTopologyId) {
         ConsistentHash writeCh = cacheTopology.getWriteConsistentHash();
         Set<Address> newTargets = new HashSet<Address>(writeCh.locateAllOwners(affectedKeys));
         newTargets.remove(rpcManager.getAddress());
         // Forwarding to the originator would create a cycle
         // TODO This may not be the "real" originator, but one of the original recipients
         // or even one of the nodes that one of the original recipients forwarded the command to.
         // In non-transactional caches, the "real" originator keeps a lock for the duration
         // of the RPC, so this means we could get a deadlock while forwarding to it.
         newTargets.remove(origin);
         if (!newTargets.isEmpty()) {
            // Update the topology id to prevent cycles
            command.setTopologyId(localTopologyId);
            if (trace) {
               log.tracef("Forwarding command %s to new targets %s", command, newTargets);
            }
            // TODO find a way to forward the command async if it was received async
            // TxCompletionNotificationCommands are the only commands forwarded asynchronously, and they must be OOB
            return rpcManager.invokeRemotely(newTargets, command, rpcManager.getDefaultRpcOptions(sync, DeliverOrder.NONE));
         }
      }
      return Collections.emptyMap();
   }

   @Override
   public void notifyEndOfRebalance(int topologyId, int rebalanceId) {
      localTopologyManager.confirmRebalance(cacheName, topologyId, rebalanceId, null);
   }

   // TODO Investigate merging ownsData() and getFirstTopologyAsMember(), as they serve a similar purpose
   @Override
   public boolean ownsData() {
      return stateConsumer.ownsData();
   }

   @Override
   public int getFirstTopologyAsMember() {
      return firstTopologyAsMember;
   }

   @Override

   public String toString() {
      return "StateTransferManagerImpl [" + cacheName + "@" + rpcManager.getAddress() + "]";
   }
}


File: core/src/main/java/org/infinispan/topology/LocalTopologyManagerImpl.java
package org.infinispan.topology;

import org.infinispan.commands.ReplicableCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.executors.SemaphoreCompletionService;
import org.infinispan.factories.GlobalComponentRegistry;
import org.infinispan.factories.annotations.ComponentName;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.factories.annotations.Start;
import org.infinispan.factories.annotations.Stop;
import org.infinispan.jmx.annotations.DataType;
import org.infinispan.jmx.annotations.MBean;
import org.infinispan.jmx.annotations.ManagedAttribute;
import org.infinispan.partitionhandling.AvailabilityMode;
import org.infinispan.partitionhandling.impl.PartitionHandlingManager;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.responses.ExceptionResponse;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.responses.SuccessfulResponse;
import org.infinispan.remoting.rpc.ResponseMode;
import org.infinispan.remoting.transport.Address;
import org.infinispan.remoting.transport.Transport;
import org.infinispan.remoting.transport.jgroups.SuspectException;
import org.infinispan.util.TimeService;
import org.infinispan.util.concurrent.WithinThreadExecutor;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.infinispan.factories.KnownComponentNames.ASYNC_TRANSPORT_EXECUTOR;

/**
 * The {@code LocalTopologyManager} implementation.
 *
 * @author Dan Berindei
 * @since 5.2
 */
@MBean(objectName = "LocalTopologyManager", description = "Controls the cache membership and state transfer")
public class LocalTopologyManagerImpl implements LocalTopologyManager {
   private static Log log = LogFactory.getLog(LocalTopologyManagerImpl.class);
   private static final boolean trace = log.isTraceEnabled();

   private Transport transport;
   private ExecutorService asyncTransportExecutor;
   private GlobalComponentRegistry gcr;
   private TimeService timeService;

   private final WithinThreadExecutor withinThreadExecutor = new WithinThreadExecutor();

   // We synchronize on the entire map while handling a status request, to make sure there are no concurrent topology
   // updates from the old coordinator.
   private final Map<String, LocalCacheStatus> runningCaches =
         Collections.synchronizedMap(new HashMap<String, LocalCacheStatus>());
   private volatile boolean running;


   @Inject
   public void inject(Transport transport,
                      @ComponentName(ASYNC_TRANSPORT_EXECUTOR) ExecutorService asyncTransportExecutor,
                      GlobalComponentRegistry gcr, TimeService timeService) {
      this.transport = transport;
      this.asyncTransportExecutor = asyncTransportExecutor;
      this.gcr = gcr;
      this.timeService = timeService;
   }

   // Arbitrary value, only need to start after JGroupsTransport
   @Start(priority = 100)
   public void start() {
      if (trace) {
         log.tracef("Starting LocalTopologyManager on %s", transport.getAddress());
      }
      running = true;
   }

   // Need to stop before the JGroupsTransport
   @Stop(priority = 9)
   public void stop() {
      if (trace) {
         log.tracef("Stopping LocalTopologyManager on %s", transport.getAddress());
      }
      running = false;
      withinThreadExecutor.shutdown();
   }

   @Override
   public CacheTopology join(String cacheName, CacheJoinInfo joinInfo, CacheTopologyHandler stm,
         PartitionHandlingManager phm) throws Exception {
      log.debugf("Node %s joining cache %s", transport.getAddress(), cacheName);

      // For Total Order caches, we must not move the topology updates to another thread
      ExecutorService topologyUpdatesExecutor = joinInfo.isTotalOrder() ? withinThreadExecutor : asyncTransportExecutor;
      LocalCacheStatus cacheStatus = new LocalCacheStatus(joinInfo, stm, phm, topologyUpdatesExecutor);
      runningCaches.put(cacheName, cacheStatus);

      long timeout = joinInfo.getTimeout();
      long endTime = timeService.expectedEndTime(timeout, TimeUnit.MILLISECONDS);
      // Pretend the join is using up a thread from the topology updates completion service.
      // This ensures that the initial topology and the GET_CACHE_LISTENERS request will happen on this thread,
      // and other topology updates are only handled after we call backgroundTaskFinished(null)
      cacheStatus.getTopologyUpdatesCompletionService().continueTaskInBackground();
      try {
         while (true) {
            int viewId = transport.getViewId();
            try {
               ReplicableCommand command = new CacheTopologyControlCommand(cacheName,
                       CacheTopologyControlCommand.Type.JOIN, transport.getAddress(), joinInfo, viewId);
               CacheStatusResponse initialStatus = (CacheStatusResponse) executeOnCoordinator(command, timeout);
               // Ignore null responses, that's what the current coordinator returns if is shutting down
               if (initialStatus != null) {
                  doHandleTopologyUpdate(cacheName, initialStatus.getCacheTopology(), initialStatus.getAvailabilityMode(),
                        viewId, transport.getCoordinator(), cacheStatus);
                  doHandleStableTopologyUpdate(cacheName, initialStatus.getStableTopology(), viewId, cacheStatus);
                  return initialStatus.getCacheTopology();
               }
            } catch (Exception e) {
               log.debugf(e, "Error sending join request for cache %s to coordinator", cacheName);
               if (timeService.isTimeExpired(endTime)) {
                  throw e;
               }
               // TODO Add some configuration for this, or use a fraction of state transfer timeout
               Thread.sleep(100);
            }
         }
      } finally {
         cacheStatus.getTopologyUpdatesCompletionService().backgroundTaskFinished(null);
      }
   }

   @Override
   public void leave(String cacheName) {
      log.debugf("Node %s leaving cache %s", transport.getAddress(), cacheName);
      LocalCacheStatus cacheStatus = runningCaches.remove(cacheName);

      ReplicableCommand command = new CacheTopologyControlCommand(cacheName,
            CacheTopologyControlCommand.Type.LEAVE, transport.getAddress(), transport.getViewId());
      try {
         executeOnCoordinator(command, cacheStatus.getJoinInfo().getTimeout());
      } catch (Exception e) {
         log.debugf(e, "Error sending the leave request for cache %s to coordinator", cacheName);
      }
   }

   @Override
   public void confirmRebalance(String cacheName, int topologyId, int rebalanceId, Throwable throwable) {
      // Note that if the coordinator changes again after we sent the command, we will get another
      // query for the status of our running caches. So we don't need to retry if the command failed.
      ReplicableCommand command = new CacheTopologyControlCommand(cacheName,
            CacheTopologyControlCommand.Type.REBALANCE_CONFIRM, transport.getAddress(),
            topologyId, rebalanceId, throwable, transport.getViewId());
      try {
         executeOnCoordinatorAsync(command);
      } catch (Exception e) {
         log.debugf(e, "Error sending the rebalance completed notification for cache %s to the coordinator",
               cacheName);
      }
   }

   // called by the coordinator
   @Override
   public ManagerStatusResponse handleStatusRequest(int viewId) {
      Map<String, CacheStatusResponse> caches = new HashMap<String, CacheStatusResponse>();
      synchronized (runningCaches) {
         for (Map.Entry<String, LocalCacheStatus> e : runningCaches.entrySet()) {
            String cacheName = e.getKey();
            LocalCacheStatus cacheStatus = runningCaches.get(cacheName);
            AvailabilityMode availabilityMode = cacheStatus.getPartitionHandlingManager() != null ?
                    cacheStatus.getPartitionHandlingManager().getAvailabilityMode() : null;
            caches.put(e.getKey(), new CacheStatusResponse(cacheStatus.getJoinInfo(),
                    cacheStatus.getCurrentTopology(), cacheStatus.getStableTopology(),
                    availabilityMode));
         }
      }

      boolean rebalancingEnabled = true;
      // Avoid adding a direct dependency to the ClusterTopologyManager
      ReplicableCommand command = new CacheTopologyControlCommand(null,
            CacheTopologyControlCommand.Type.POLICY_GET_STATUS, transport.getAddress(),
            transport.getViewId());
      try {
         gcr.wireDependencies(command);
         rebalancingEnabled = (Boolean) ((SuccessfulResponse) command.perform(null)).getResponseValue();
      } catch (Throwable t) {
         log.warn("Failed to obtain the rebalancing status", t);
      }
      log.debugf("Sending cluster status response for view %d", viewId);
      return new ManagerStatusResponse(caches, rebalancingEnabled);
   }

   @Override
   public void handleTopologyUpdate(final String cacheName, final CacheTopology cacheTopology,
         final AvailabilityMode availabilityMode, final int viewId, final Address sender) throws InterruptedException {
      if (!running) {
         log.tracef("Ignoring consistent hash update %s for cache %s, the local cache manager is not running",
               cacheTopology.getTopologyId(), cacheName);
         return;
      }

      final LocalCacheStatus cacheStatus = runningCaches.get(cacheName);
      if (cacheStatus == null) {
         log.tracef("Ignoring consistent hash update %s for cache %s that doesn't exist locally",
               cacheTopology.getTopologyId(), cacheName);
         return;
      }

      cacheStatus.getTopologyUpdatesCompletionService().submit(new Runnable() {
         @Override
         public void run() {
            doHandleTopologyUpdate(cacheName, cacheTopology, availabilityMode, viewId, sender, cacheStatus);
         }
      }, null);
      // Clear any finished tasks from the completion service's queue to avoid leaks
      List<? extends Future<Void>> futures = cacheStatus.getTopologyUpdatesCompletionService().drainCompletionQueue();
      boolean interrupted = false;
      for (Future<Void> future : futures) {
         // These will not block since they are already completed
         try {
            future.get();
         } catch (InterruptedException e) {
            // This shouldn't happen as each task is complete
            interrupted = true;
         } catch (ExecutionException e) {
            log.topologyUpdateError(cacheTopology.getTopologyId(), e.getCause());
         }
      }
      if (interrupted) {
         Thread.currentThread().interrupt();
      }
   }

   protected void doHandleTopologyUpdate(String cacheName, CacheTopology cacheTopology,
         AvailabilityMode availabilityMode, int viewId, Address sender, LocalCacheStatus cacheStatus) {
      try {
         waitForView(viewId);
      } catch (InterruptedException e) {
         // Shutting down, ignore the exception and the rebalance
         return;
      }

      synchronized (cacheStatus) {
         CacheTopology existingTopology = cacheStatus.getCurrentTopology();
         if (existingTopology != null && cacheTopology.getTopologyId() <= existingTopology.getTopologyId()) {
            log.debugf("Ignoring late consistent hash update for cache %s, current topology is %s: %s",
                  cacheName, existingTopology.getTopologyId(), cacheTopology);
            return;
         }

         CacheTopologyHandler handler = cacheStatus.getHandler();
         resetLocalTopologyBeforeRebalance(cacheName, cacheTopology, existingTopology, handler);

         if (!updateCacheTopology(cacheName, cacheTopology, sender, cacheStatus))
            return;

         ConsistentHash unionCH = null;
         if (cacheTopology.getPendingCH() != null) {
            unionCH = cacheStatus.getJoinInfo().getConsistentHashFactory().union(cacheTopology.getCurrentCH(),
                  cacheTopology.getPendingCH());
         }

         CacheTopology unionTopology = new CacheTopology(cacheTopology.getTopologyId(), cacheTopology.getRebalanceId(),
               cacheTopology.getCurrentCH(), cacheTopology.getPendingCH(), unionCH, cacheTopology.getActualMembers());
         unionTopology.logRoutingTableInformation();

         boolean updateAvailabilityModeFirst = availabilityMode != AvailabilityMode.AVAILABLE;
         if (updateAvailabilityModeFirst) {
            if (cacheStatus.getPartitionHandlingManager() != null && availabilityMode != null) {
               cacheStatus.getPartitionHandlingManager().setAvailabilityMode(availabilityMode);
            }
         }
         if ((existingTopology == null || existingTopology.getRebalanceId() != cacheTopology.getRebalanceId()) && unionCH != null) {
            // This CH_UPDATE command was sent after a REBALANCE_START command, but arrived first.
            // We will start the rebalance now and ignore the REBALANCE_START command when it arrives.
            log.tracef("This topology update has a pending CH, starting the rebalance now");
            handler.rebalance(unionTopology);
         } else {
            handler.updateConsistentHash(unionTopology);
         }

         if (!updateAvailabilityModeFirst) {
            if (cacheStatus.getPartitionHandlingManager() != null && availabilityMode != null) {
               cacheStatus.getPartitionHandlingManager().setAvailabilityMode(availabilityMode);
            }
         }
      }
   }

   private boolean updateCacheTopology(String cacheName, CacheTopology cacheTopology, Address sender,
         LocalCacheStatus cacheStatus) {
      // Block if there is a status request in progress
      // The caller should have already acquired the cacheStatus monitor
      synchronized (runningCaches) {
         if (!sender.equals(transport.getCoordinator())) {
            log.debugf("Ignoring topology %d from old coordinator %s", cacheTopology.getTopologyId(), sender);
            return false;
         }
      }

      log.debugf("Updating local topology for cache %s: %s", cacheName, cacheTopology);
      cacheStatus.setCurrentTopology(cacheTopology);
      return true;
   }

   private void resetLocalTopologyBeforeRebalance(String cacheName, CacheTopology newCacheTopology,
         CacheTopology oldCacheTopology, CacheTopologyHandler handler) {
      boolean newRebalance = newCacheTopology.getPendingCH() != null;
      if (newRebalance) {
         // The initial topology doesn't need a reset because we are guaranteed not to be a member
         if (oldCacheTopology == null)
            return;

         // We only need a reset if we missed a topology update
         if (newCacheTopology.getTopologyId() == oldCacheTopology.getTopologyId() + 1)
            return;

         // We have missed a topology update, and that topology might have removed some of our segments.
         // If this rebalance adds those same segments, we need to remove the old data/inbound transfers first.
         // This can happen when the coordinator changes, either because the old one left or because there was a merge,
         // and the rebalance after merge arrives before the merged topology update.
         if (newCacheTopology.getRebalanceId() != oldCacheTopology.getRebalanceId()) {
            // The currentCH changed, we need to install a "reset" topology with the new currentCH first
            CacheTopology resetTopology = new CacheTopology(newCacheTopology.getTopologyId() - 1,
                  newCacheTopology.getRebalanceId() - 1, newCacheTopology.getCurrentCH(), null, newCacheTopology.getActualMembers());
            log.debugf("Installing fake cache topology %s for cache %s", resetTopology, cacheName);
            handler.updateConsistentHash(resetTopology);
         }
      }
   }

   @Override
   public void handleStableTopologyUpdate(final String cacheName, final CacheTopology newStableTopology,
         final int viewId) {
      final LocalCacheStatus cacheStatus = runningCaches.get(cacheName);
      if (cacheStatus != null) {
         cacheStatus.getTopologyUpdatesCompletionService().submit(new Runnable() {
            @Override
            public void run() {
               doHandleStableTopologyUpdate(cacheName, newStableTopology, viewId, cacheStatus);
            }
         }, null);
      }
   }

   protected void doHandleStableTopologyUpdate(String cacheName, CacheTopology newStableTopology, int viewId,
         LocalCacheStatus cacheStatus) {
      synchronized (cacheStatus) {
         CacheTopology stableTopology = cacheStatus.getStableTopology();
         if (stableTopology == null || stableTopology.getTopologyId() < newStableTopology.getTopologyId()) {
            log.tracef("Updating stable topology for cache %s: %s", cacheName, newStableTopology);
            cacheStatus.setStableTopology(newStableTopology);
         }
      }
   }

   @Override
   public void handleRebalance(final String cacheName, final CacheTopology cacheTopology, final int viewId,
         final Address sender) throws InterruptedException {
      if (!running) {
         log.debugf("Ignoring rebalance request %s for cache %s, the local cache manager is not running",
               cacheTopology.getTopologyId(), cacheName);
         return;
      }

      final LocalCacheStatus cacheStatus = runningCaches.get(cacheName);
      if (cacheStatus == null) {
         log.tracef("Ignoring rebalance %s for cache %s that doesn't exist locally",
               cacheTopology.getTopologyId(), cacheName);
         return;
      }

      cacheStatus.getTopologyUpdatesCompletionService().submit(new Runnable() {
         @Override
         public void run() {
            doHandleRebalance(viewId, cacheStatus, cacheTopology, cacheName, sender);
         }
      }, null);
   }

   protected void doHandleRebalance(int viewId, LocalCacheStatus cacheStatus, CacheTopology cacheTopology, String cacheName, Address sender) {
      try {
         waitForView(viewId);
      } catch (InterruptedException e) {
         // Shutting down, ignore the exception and the rebalance
         return;
      }

      synchronized (cacheStatus) {
         CacheTopology existingTopology = cacheStatus.getCurrentTopology();
         if (existingTopology != null && cacheTopology.getTopologyId() <= existingTopology.getTopologyId()) {
            // Start rebalance commands are sent asynchronously to the entire cluster
            // So it's possible to receive an old one on a joiner after the joiner has already become a member.
            log.debugf("Ignoring old rebalance for cache %s, current topology is %s: %s", cacheName,
                  existingTopology.getTopologyId(), cacheTopology);
            return;
         }

         if (!updateCacheTopology(cacheName, cacheTopology, sender, cacheStatus))
            return;

         log.debugf("Starting local rebalance for cache %s, topology = %s", cacheName, cacheTopology);
         cacheTopology.logRoutingTableInformation();
         cacheStatus.setCurrentTopology(cacheTopology);

         CacheTopologyHandler handler = cacheStatus.getHandler();
         resetLocalTopologyBeforeRebalance(cacheName, cacheTopology, existingTopology, handler);

         ConsistentHash unionCH = cacheStatus.getJoinInfo().getConsistentHashFactory().union(
               cacheTopology.getCurrentCH(), cacheTopology.getPendingCH());
         CacheTopology newTopology = new CacheTopology(cacheTopology.getTopologyId(), cacheTopology
               .getRebalanceId(),
               cacheTopology.getCurrentCH(), cacheTopology.getPendingCH(), unionCH, cacheTopology.getActualMembers());
         handler.rebalance(newTopology);
      }
   }

   @Override
   public CacheTopology getCacheTopology(String cacheName) {
      LocalCacheStatus cacheStatus = runningCaches.get(cacheName);
      return cacheStatus.getCurrentTopology();
   }

   @Override
   public CacheTopology getStableCacheTopology(String cacheName) {
      LocalCacheStatus cacheStatus = runningCaches.get(cacheName);
      return cacheStatus.getCurrentTopology();
   }

   @Override
   public boolean isTotalOrderCache(String cacheName) {
      if (!running) {
         log.tracef("isTotalOrderCache(%s) returning false because the local cache manager is not running", cacheName);
         return false;
      }
      LocalCacheStatus cacheStatus = runningCaches.get(cacheName);
      if (cacheStatus == null) {
         log.tracef("isTotalOrderCache(%s) returning false because the cache doesn't exist locally", cacheName);
         return false;
      }
      boolean totalOrder = cacheStatus.getJoinInfo().isTotalOrder();
      log.tracef("isTotalOrderCache(%s) returning %s", cacheName, totalOrder);
      return totalOrder;
   }

   private void waitForView(int viewId) throws InterruptedException {
      transport.waitForView(viewId);
   }

   @ManagedAttribute(description = "Rebalancing enabled", displayName = "Rebalancing enabled",
         dataType = DataType.TRAIT, writable = true)
   @Override
   public boolean isRebalancingEnabled() throws Exception {
      ReplicableCommand command = new CacheTopologyControlCommand(null,
            CacheTopologyControlCommand.Type.POLICY_GET_STATUS, transport.getAddress(), transport.getViewId());
      while (true) {
         Address coordinator = transport.getCoordinator();
         int nextViewId = transport.getViewId() + 1;
         try {
            return (Boolean) executeOnCoordinator(command, getGlobalTimeout());
         } catch (SuspectException e) {
            if (trace) log.tracef("Coordinator left the cluster while querying rebalancing status, retrying");
            transport.waitForView(nextViewId);
         }
      }
   }

   @Override
   public void setRebalancingEnabled(boolean enabled) throws Exception {
      CacheTopologyControlCommand.Type type = enabled ? CacheTopologyControlCommand.Type.POLICY_ENABLE
            : CacheTopologyControlCommand.Type.POLICY_DISABLE;
      ReplicableCommand command = new CacheTopologyControlCommand(null, type, transport.getAddress(),
            transport.getViewId());
      executeOnClusterSync(command, getGlobalTimeout(), false, false);
   }

   @ManagedAttribute(description = "Cluster availability", displayName = "Cluster availability",
         dataType = DataType.TRAIT, writable = false)
   public String getClusterAvailability() {
      AvailabilityMode clusterAvailability = AvailabilityMode.AVAILABLE;
      synchronized (runningCaches) {
         for (LocalCacheStatus cacheStatus : runningCaches.values()) {
            AvailabilityMode availabilityMode = cacheStatus.getPartitionHandlingManager() != null ?
                  cacheStatus.getPartitionHandlingManager().getAvailabilityMode() : null;
            clusterAvailability = availabilityMode != null ? clusterAvailability.min(availabilityMode) : clusterAvailability;

         }
      }
      return clusterAvailability.toString();
   }

   @Override
   public AvailabilityMode getCacheAvailability(String cacheName) {
      LocalCacheStatus cacheStatus = runningCaches.get(cacheName);
      AvailabilityMode availabilityMode = cacheStatus.getPartitionHandlingManager() != null ?
            cacheStatus.getPartitionHandlingManager().getAvailabilityMode() : AvailabilityMode.AVAILABLE;
      return availabilityMode;
   }

   @Override
   public void setCacheAvailability(String cacheName, AvailabilityMode availabilityMode) throws Exception {
      CacheTopologyControlCommand.Type type = CacheTopologyControlCommand.Type.AVAILABILITY_MODE_CHANGE;
      ReplicableCommand command = new CacheTopologyControlCommand(cacheName, type, transport.getAddress(),
            availabilityMode, transport.getViewId());
      executeOnCoordinator(command, getGlobalTimeout());
   }

   private Object executeOnCoordinator(ReplicableCommand command, long timeout) throws Exception {
      Response response;
      if (transport.isCoordinator()) {
         try {
            if (log.isTraceEnabled()) log.tracef("Attempting to execute command on self: %s", command);
            gcr.wireDependencies(command);
            response = (Response) command.perform(null);
         } catch (Throwable t) {
            throw new CacheException("Error handling join request", t);
         }
      } else {
         // this node is not the coordinator
         Address coordinator = transport.getCoordinator();
         Map<Address, Response> responseMap = transport.invokeRemotely(Collections.singleton(coordinator),
               command, ResponseMode.SYNCHRONOUS, timeout, null, DeliverOrder.NONE, false);
         response = responseMap.get(coordinator);
      }
      if (response == null || !response.isSuccessful()) {
         Throwable exception = response instanceof ExceptionResponse
               ? ((ExceptionResponse)response).getException() : null;
         throw new CacheException("Bad response received from coordinator: " + response, exception);
      }
      return ((SuccessfulResponse) response).getResponseValue();
   }

   private void executeOnCoordinatorAsync(final ReplicableCommand command) throws Exception {
      // if we are the coordinator, the execution is actually synchronous
      if (transport.isCoordinator()) {
         asyncTransportExecutor.submit(new Callable<Object>() {
            @Override
            public Object call() throws Exception {
               if (log.isTraceEnabled()) log.tracef("Attempting to execute command on self: %s", command);
               gcr.wireDependencies(command);
               try {
                  return command.perform(null);
               } catch (Throwable t) {
                  log.errorf(t, "Failed to execute ReplicableCommand %s on coordinator async: %s", command, t.getMessage());
                  throw new Exception(t);
               }
            }
         });
      } else {
         Address coordinator = transport.getCoordinator();
         // ignore the responses
         transport.invokeRemotely(Collections.singleton(coordinator), command,
                                  ResponseMode.ASYNCHRONOUS, 0, null, DeliverOrder.NONE, false);
      }
   }

   private Map<Address, Object> executeOnClusterSync(final ReplicableCommand command, final int timeout,
                                                     boolean totalOrder, boolean distributed)
         throws Exception {
      // first invoke remotely

      if (totalOrder) {
         Map<Address, Response> responseMap = transport.invokeRemotely(null, command,
               ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS,
               timeout, null, DeliverOrder.TOTAL, distributed);
         Map<Address, Object> responseValues = new HashMap<Address, Object>(transport.getMembers().size());
         for (Map.Entry<Address, Response> entry : responseMap.entrySet()) {
            Address address = entry.getKey();
            Response response = entry.getValue();
            if (!response.isSuccessful()) {
               Throwable cause = response instanceof ExceptionResponse ? ((ExceptionResponse) response).getException() : null;
               throw new CacheException("Unsuccessful response received from node " + address + ": " + response, cause);
            }
            responseValues.put(address, ((SuccessfulResponse) response).getResponseValue());
         }
         return responseValues;
      }

      Future<Map<Address, Response>> remoteFuture = asyncTransportExecutor.submit(new Callable<Map<Address, Response>>() {
         @Override
         public Map<Address, Response> call() throws Exception {
            return transport.invokeRemotely(null, command,
                  ResponseMode.SYNCHRONOUS_IGNORE_LEAVERS, timeout, null, DeliverOrder.NONE, false);
         }
      });

      // invoke the command on the local node
      gcr.wireDependencies(command);
      Response localResponse;
      try {
         if (log.isTraceEnabled()) log.tracef("Attempting to execute command on self: %s", command);
         localResponse = (Response) command.perform(null);
      } catch (Throwable throwable) {
         throw new Exception(throwable);
      }
      if (!localResponse.isSuccessful()) {
         throw new CacheException("Unsuccessful local response");
      }

      // wait for the remote commands to finish
      Map<Address, Response> responseMap = remoteFuture.get(timeout, TimeUnit.MILLISECONDS);

      // parse the responses
      Map<Address, Object> responseValues = new HashMap<Address, Object>(transport.getMembers().size());
      for (Map.Entry<Address, Response> entry : responseMap.entrySet()) {
         Address address = entry.getKey();
         Response response = entry.getValue();
         if (!response.isSuccessful()) {
            Throwable cause = response instanceof ExceptionResponse ? ((ExceptionResponse) response).getException() : null;
            throw new CacheException("Unsuccessful response received from node " + address + ": " + response, cause);
         }
         responseValues.put(address, ((SuccessfulResponse) response).getResponseValue());
      }

      responseValues.put(transport.getAddress(), ((SuccessfulResponse) localResponse).getResponseValue());

      return responseValues;
   }

   private int getGlobalTimeout() {
      // TODO Rename setting to something like globalRpcTimeout
      return (int) gcr.getGlobalConfiguration().transport().distributedSyncTimeout();
   }
}

class LocalCacheStatus {
   private final CacheJoinInfo joinInfo;
   private final CacheTopologyHandler handler;
   private final PartitionHandlingManager partitionHandlingManager;
   private volatile CacheTopology currentTopology;
   private volatile CacheTopology stableTopology;
   private final SemaphoreCompletionService<Void> topologyUpdatesCompletionService;

   public LocalCacheStatus(CacheJoinInfo joinInfo, CacheTopologyHandler handler, PartitionHandlingManager phm,
         ExecutorService executor) {
      this.joinInfo = joinInfo;
      this.handler = handler;
      this.partitionHandlingManager = phm;

      this.topologyUpdatesCompletionService = new SemaphoreCompletionService<>(executor, 1);
   }

   public CacheJoinInfo getJoinInfo() {
      return joinInfo;
   }

   public CacheTopologyHandler getHandler() {
      return handler;
   }

   public PartitionHandlingManager getPartitionHandlingManager() {
      return partitionHandlingManager;
   }

   public CacheTopology getCurrentTopology() {
      return currentTopology;
   }

   public void setCurrentTopology(CacheTopology currentTopology) {
      this.currentTopology = currentTopology;
   }

   public CacheTopology getStableTopology() {
      return stableTopology;
   }

   public void setStableTopology(CacheTopology stableTopology) {
      this.stableTopology = stableTopology;
   }

   public SemaphoreCompletionService<Void> getTopologyUpdatesCompletionService() {
      return topologyUpdatesCompletionService;
   }
}


File: core/src/main/java/org/infinispan/transaction/impl/AbstractEnlistmentAdapter.java
package org.infinispan.transaction.impl;

import org.infinispan.commands.CommandsFactory;
import org.infinispan.commands.remote.recovery.TxCompletionNotificationCommand;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.Configurations;
import org.infinispan.interceptors.locking.ClusteringDependentLogic;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.transport.Address;
import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.xa.CacheTransaction;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.Collection;

import static org.infinispan.util.DeltaCompositeKeyUtil.filterDeltaCompositeKeys;

/**
 * Base class for both Sync and XAResource enlistment adapters.
 *
 * @author Mircea Markus
 * @since 5.1
 */
public abstract class AbstractEnlistmentAdapter {

   private static Log log = LogFactory.getLog(AbstractEnlistmentAdapter.class);

   private final CommandsFactory commandsFactory;
   private final RpcManager rpcManager;
   private final TransactionTable txTable;
   private final ClusteringDependentLogic clusteringLogic;
   private final int hashCode;
   private final boolean isSecondPhaseAsync;
   private final boolean isPessimisticLocking;
   private final boolean isTotalOrder;
   protected final TransactionCoordinator txCoordinator;

   public AbstractEnlistmentAdapter(CacheTransaction cacheTransaction,
            CommandsFactory commandsFactory, RpcManager rpcManager,
            TransactionTable txTable, ClusteringDependentLogic clusteringLogic,
            Configuration configuration, TransactionCoordinator txCoordinator) {
      this.commandsFactory = commandsFactory;
      this.rpcManager = rpcManager;
      this.txTable = txTable;
      this.clusteringLogic = clusteringLogic;
      this.isSecondPhaseAsync = Configurations.isSecondPhaseAsync(configuration);
      this.isPessimisticLocking = configuration.transaction().lockingMode() == LockingMode.PESSIMISTIC;
      this.isTotalOrder = configuration.transaction().transactionProtocol().isTotalOrder();
      hashCode = preComputeHashCode(cacheTransaction);
      this.txCoordinator = txCoordinator;
   }

   public AbstractEnlistmentAdapter(CommandsFactory commandsFactory,
            RpcManager rpcManager, TransactionTable txTable,
            ClusteringDependentLogic clusteringLogic, Configuration configuration, TransactionCoordinator txCoordinator) {
      this.commandsFactory = commandsFactory;
      this.rpcManager = rpcManager;
      this.txTable = txTable;
      this.clusteringLogic = clusteringLogic;
      this.isSecondPhaseAsync = Configurations.isSecondPhaseAsync(configuration);
      this.isPessimisticLocking = configuration.transaction().lockingMode() == LockingMode.PESSIMISTIC;
      this.isTotalOrder = configuration.transaction().transactionProtocol().isTotalOrder();
      hashCode = 31;
      this.txCoordinator = txCoordinator;
   }

   protected final void releaseLocksForCompletedTransaction(LocalTransaction localTransaction, boolean committedInOnePhase) {
      final GlobalTransaction gtx = localTransaction.getGlobalTransaction();
      txTable.removeLocalTransaction(localTransaction);
      log.tracef("Committed in onePhase? %s isOptimistic? %s", committedInOnePhase, isOptimisticCache());
      if (committedInOnePhase && isOptimisticCache())
         return;
      if (isClustered()) {
         removeTransactionInfoRemotely(localTransaction, gtx);
      }
   }

   private void removeTransactionInfoRemotely(LocalTransaction localTransaction, GlobalTransaction gtx) {
      if (mayHaveRemoteLocks(localTransaction) && !isSecondPhaseAsync) {
         final TxCompletionNotificationCommand command = commandsFactory.buildTxCompletionNotificationCommand(null, gtx);
         final Collection<Address> owners = clusteringLogic.getOwners(filterDeltaCompositeKeys(localTransaction.getAffectedKeys()));
         Collection<Address> commitNodes = localTransaction.getCommitNodes(owners, rpcManager.getTopologyId(), rpcManager.getMembers());
         log.tracef("About to invoke tx completion notification on commitNodes: %s", commitNodes);
         rpcManager.invokeRemotely(commitNodes, command, rpcManager.getDefaultRpcOptions(false, DeliverOrder.NONE));
      }
   }

   private boolean mayHaveRemoteLocks(LocalTransaction lt) {
      return !isTotalOrder && (lt.getRemoteLocksAcquired() != null && !lt.getRemoteLocksAcquired().isEmpty() ||
            !lt.getModifications().isEmpty() ||
            isPessimisticLocking && lt.getTopologyId() != rpcManager.getTopologyId());
   }

   /**
    * Invoked by TransactionManagers, make sure it's an efficient implementation.
    * System.identityHashCode(x) is NOT an efficient implementation.
    */
   @Override
   public final int hashCode() {
      return this.hashCode;
   }

   private static int preComputeHashCode(final CacheTransaction cacheTx) {
      return 31 + cacheTx.hashCode();
   }

   private boolean isClustered() {
      return rpcManager != null;
   }

   private boolean isOptimisticCache() {
      //a transactional cache that is neither total order nor pessimistic must be optimistic.
      return !isPessimisticLocking && !isTotalOrder;
   }
}


File: core/src/main/java/org/infinispan/transaction/impl/TransactionTable.java
package org.infinispan.transaction.impl;

import net.jcip.annotations.GuardedBy;
import org.infinispan.Cache;
import org.infinispan.commands.CommandsFactory;
import org.infinispan.commands.tx.RollbackCommand;
import org.infinispan.commands.write.WriteCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.equivalence.AnyEquivalence;
import org.infinispan.commons.equivalence.IdentityEquivalence;
import org.infinispan.commons.util.CollectionFactory;
import org.infinispan.commons.util.InfinispanCollections;
import org.infinispan.commons.util.Util;
import org.infinispan.commons.util.concurrent.jdk8backported.EquivalentConcurrentHashMapV8;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.Configurations;
import org.infinispan.context.InvocationContextFactory;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.factories.annotations.Start;
import org.infinispan.factories.annotations.Stop;
import org.infinispan.interceptors.InterceptorChain;
import org.infinispan.interceptors.locking.ClusteringDependentLogic;
import org.infinispan.notifications.Listener;
import org.infinispan.notifications.cachelistener.CacheNotifier;
import org.infinispan.notifications.cachelistener.annotation.TopologyChanged;
import org.infinispan.notifications.cachelistener.event.TopologyChangedEvent;
import org.infinispan.notifications.cachemanagerlistener.CacheManagerNotifier;
import org.infinispan.notifications.cachemanagerlistener.annotation.ViewChanged;
import org.infinispan.notifications.cachemanagerlistener.event.ViewChangedEvent;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.transport.Address;
import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.synchronization.SyncLocalTransaction;
import org.infinispan.transaction.synchronization.SynchronizationAdapter;
import org.infinispan.transaction.xa.CacheTransaction;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.transaction.xa.TransactionFactory;
import org.infinispan.util.TimeService;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.Transaction;
import javax.transaction.TransactionSynchronizationRegistry;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Repository for {@link RemoteTransaction} and {@link org.infinispan.transaction.xa.TransactionXaAdapter}s (locally
 * originated transactions).
 *
 * @author Mircea.Markus@jboss.com
 * @author Galder Zamarreño
 * @since 4.0
 */
@Listener
public class TransactionTable implements org.infinispan.transaction.TransactionTable {
   public enum CompletedTransactionStatus {
      NOT_COMPLETED, COMMITTED, ABORTED, EXPIRED
   }

   private static final Log log = LogFactory.getLog(TransactionTable.class);
   private static final boolean trace = log.isTraceEnabled();

   public static final int CACHE_STOPPED_TOPOLOGY_ID = -1;
   /**
    * minTxTopologyId is the minimum topology ID across all ongoing local and remote transactions.
    */
   private volatile int minTxTopologyId = CACHE_STOPPED_TOPOLOGY_ID;
   private volatile int currentTopologyId = CACHE_STOPPED_TOPOLOGY_ID;
   protected Configuration configuration;
   protected InvocationContextFactory icf;
   protected TransactionCoordinator txCoordinator;
   protected TransactionFactory txFactory;
   protected RpcManager rpcManager;
   protected CommandsFactory commandsFactory;
   protected ClusteringDependentLogic clusteringLogic;
   protected boolean clustered = false;
   private ConcurrentMap<Transaction, LocalTransaction> localTransactions;
   private ConcurrentMap<GlobalTransaction, LocalTransaction> globalToLocalTransactions;
   private ConcurrentMap<GlobalTransaction, RemoteTransaction> remoteTransactions;
   private InterceptorChain invoker;
   private CacheNotifier notifier;
   private TransactionSynchronizationRegistry transactionSynchronizationRegistry;
   private Lock minTopologyRecalculationLock;
   private CompletedTransactionsInfo completedTransactionsInfo;
   private ScheduledExecutorService executorService;
   private String cacheName;
   private TimeService timeService;
   private CacheManagerNotifier cacheManagerNotifier;

   @Inject
   public void initialize(RpcManager rpcManager, Configuration configuration,
                          InvocationContextFactory icf, InterceptorChain invoker, CacheNotifier notifier,
                          TransactionFactory gtf, TransactionCoordinator txCoordinator,
                          TransactionSynchronizationRegistry transactionSynchronizationRegistry,
                          CommandsFactory commandsFactory, ClusteringDependentLogic clusteringDependentLogic, Cache cache,
                          TimeService timeService, CacheManagerNotifier cacheManagerNotifier) {
      this.rpcManager = rpcManager;
      this.configuration = configuration;
      this.icf = icf;
      this.invoker = invoker;
      this.notifier = notifier;
      this.txFactory = gtf;
      this.txCoordinator = txCoordinator;
      this.transactionSynchronizationRegistry = transactionSynchronizationRegistry;
      this.commandsFactory = commandsFactory;
      this.clusteringLogic = clusteringDependentLogic;
      this.cacheManagerNotifier = cacheManagerNotifier;
      this.cacheName = cache.getName();
      this.timeService = timeService;

      this.clustered = configuration.clustering().cacheMode().isClustered();
   }

   @Start(priority = 9) // Start before cache loader manager
   @SuppressWarnings("unused")
   public void start() {
      final int concurrencyLevel = configuration.locking().concurrencyLevel();
      //use the IdentityEquivalence because some Transaction implementation does not have a stable hash code function
      //and it can cause some leaks in the concurrent map.
      localTransactions = CollectionFactory.makeConcurrentMap(concurrencyLevel, 0.75f, concurrencyLevel,
            new IdentityEquivalence<Transaction>(),
            AnyEquivalence.getInstance());
      globalToLocalTransactions = CollectionFactory.makeConcurrentMap(concurrencyLevel, 0.75f, concurrencyLevel);

      boolean transactional = configuration.transaction().transactionMode().isTransactional();
      if (clustered && transactional) {
         minTopologyRecalculationLock = new ReentrantLock();
         remoteTransactions = CollectionFactory.makeConcurrentMap(concurrencyLevel, 0.75f, concurrencyLevel);

         ThreadFactory tf = new ThreadFactory() {
            @Override
            public Thread newThread(Runnable r) {
               String address = rpcManager != null ? rpcManager.getTransport().getAddress().toString() : "local";
               Thread th = new Thread(r, "TxCleanupService," + cacheName + "," + address);
               th.setDaemon(true);
               return th;
            }
         };
         executorService = Executors.newSingleThreadScheduledExecutor(tf);

         notifier.addListener(this);
         cacheManagerNotifier.addListener(this);

         boolean totalOrder = configuration.transaction().transactionProtocol().isTotalOrder();
         if (!totalOrder) {
            completedTransactionsInfo = new CompletedTransactionsInfo();

            // Periodically run a task to cleanup the transaction table of completed transactions.
            long interval = configuration.transaction().reaperWakeUpInterval();
            executorService.scheduleAtFixedRate(new Runnable() {
               @Override
               public void run() {
                  completedTransactionsInfo.cleanupCompletedTransactions();
               }
            }, interval, interval, TimeUnit.MILLISECONDS);

            executorService.scheduleAtFixedRate(new Runnable() {
               @Override
               public void run() {
                  cleanupTimedOutTransactions();
               }
            }, interval, interval, TimeUnit.MILLISECONDS);
         }
      }
   }

   @Override
   public GlobalTransaction getGlobalTransaction(Transaction transaction) {
      if (transaction == null) {
         throw new NullPointerException("Transaction must not be null.");
      }
      LocalTransaction localTransaction = localTransactions.get(transaction);
      return localTransaction != null ? localTransaction.getGlobalTransaction() : null;
   }

   @Override
   public Collection<GlobalTransaction> getLocalGlobalTransaction() {
      return Collections.unmodifiableCollection(globalToLocalTransactions.keySet());
   }

   @Override
   public Collection<GlobalTransaction> getRemoteGlobalTransaction() {
      return Collections.unmodifiableCollection(remoteTransactions.keySet());
   }

   @Stop
   @SuppressWarnings("unused")
   private void stop() {
      cacheManagerNotifier.removeListener(this);
      if (executorService != null)
         executorService.shutdownNow();

      if (clustered) {
         notifier.removeListener(this);
         currentTopologyId = CACHE_STOPPED_TOPOLOGY_ID; // indicate that the cache has stopped
      }
      shutDownGracefully();
   }

   public Set<Object> getLockedKeysForRemoteTransaction(GlobalTransaction gtx) {
      RemoteTransaction transaction = remoteTransactions.get(gtx);
      if (transaction == null) return InfinispanCollections.emptySet();
      return transaction.getLockedKeys();
   }


   public void remoteTransactionPrepared(GlobalTransaction gtx) {
      //do nothing
   }

   public void localTransactionPrepared(LocalTransaction localTransaction) {
      //nothing, only used by recovery
   }

   public void enlist(Transaction transaction, LocalTransaction localTransaction) {
      if (!localTransaction.isEnlisted()) {
         SynchronizationAdapter sync = new SynchronizationAdapter(
                localTransaction, txCoordinator, commandsFactory, rpcManager,
                this, clusteringLogic, configuration);
         if (transactionSynchronizationRegistry != null) {
            try {
               transactionSynchronizationRegistry.registerInterposedSynchronization(sync);
            } catch (Exception e) {
               log.failedSynchronizationRegistration(e);
               throw new CacheException(e);
            }

         } else {

            try {
               transaction.registerSynchronization(sync);
            } catch (Exception e) {
               log.failedSynchronizationRegistration(e);
               throw new CacheException(e);
            }
         }
         ((SyncLocalTransaction) localTransaction).setEnlisted(true);
      }
   }

   public void failureCompletingTransaction(Transaction tx) {
      final LocalTransaction localTransaction = localTransactions.get(tx);
      if (localTransaction != null) {
         removeLocalTransaction(localTransaction);
      }
   }

   /**
    * Returns true if the given transaction is already registered with the transaction table.
    *
    * @param tx if null false is returned
    */
   public boolean containsLocalTx(Transaction tx) {
      return tx != null && localTransactions.containsKey(tx);
   }

   public int getMinTopologyId() {
      return minTxTopologyId;
   }

   public void cleanupLeaverTransactions(List<Address> members) {
      // Can happen if the cache is non-transactional
      if (remoteTransactions == null)
         return;

      if (trace) log.tracef("Checking for transactions originated on leavers. Current cache members are %s, remote transactions: %d",
            members, remoteTransactions.size());
      HashSet<Address> membersSet = new HashSet<>(members);
      List<GlobalTransaction> toKill = new ArrayList<GlobalTransaction>();
      for (Map.Entry<GlobalTransaction, RemoteTransaction> e : remoteTransactions.entrySet()) {
         GlobalTransaction gt = e.getKey();
         RemoteTransaction remoteTx = e.getValue();
         if (trace) log.tracef("Checking transaction %s", gt);
         if (!membersSet.contains(gt.getAddress())) {
            toKill.add(gt);
         }
      }

      if (toKill.isEmpty()) {
         if (trace) log.tracef("No remote transactions pertain to originator(s) who have left the cluster.");
      } else {
         log.debugf("The originating node left the cluster for %d remote transactions", toKill.size());
      }

      for (GlobalTransaction gtx : toKill) {
         log.debugf("Rolling back transaction %s because originator %s left the cluster", gtx, gtx.getAddress());
         killTransaction(gtx);
      }

      if (trace) log.tracef("Completed cleaning transactions originating on leavers. Remote transactions remaining: %d",
            remoteTransactions.size());
   }

   public void cleanupTimedOutTransactions() {
      if (trace) log.tracef("About to cleanup remote transactions older than %d ms", configuration.transaction().completedTxTimeout());
      long beginning = timeService.time();
      long cutoffCreationTime = beginning - TimeUnit.MILLISECONDS.toNanos(configuration.transaction().completedTxTimeout());
      List<GlobalTransaction> toKill = new ArrayList<GlobalTransaction>();

      // Check remote transactions.
      for(Map.Entry<GlobalTransaction, RemoteTransaction> e : remoteTransactions.entrySet()) {
         GlobalTransaction gtx = e.getKey();
         RemoteTransaction remoteTx = e.getValue();
         if(remoteTx != null) {
            if (trace) log.tracef("Checking transaction %s", gtx);
            // Check the time.
            if (remoteTx.getCreationTime() - cutoffCreationTime < 0) {
               long duration = timeService.timeDuration(remoteTx.getCreationTime(), beginning, TimeUnit.MILLISECONDS);
               log.remoteTransactionTimeout(gtx, duration);
               toKill.add(gtx);
            }
         }
      }

      // Rollback the orphaned transactions and release any held locks.
      for (GlobalTransaction gtx : toKill) {
         killTransaction(gtx);
      }
   }

   private void killTransaction(GlobalTransaction gtx) {
      RollbackCommand rc = new RollbackCommand(cacheName, gtx);
      rc.init(invoker, icf, TransactionTable.this);
      try {
         rc.perform(null);
         if (trace) log.tracef("Rollback of transaction %s complete.", gtx);
      } catch (Throwable e) {
         log.unableToRollbackGlobalTx(gtx, e);
      }
   }

   /**
    * Returns the {@link RemoteTransaction} associated with the supplied transaction id. Returns null if no such
    * association exists.
    */
   public RemoteTransaction getRemoteTransaction(GlobalTransaction txId) {
      return remoteTransactions.get(txId);
   }

   public void remoteTransactionRollback(GlobalTransaction gtx) {
      final RemoteTransaction remove = removeRemoteTransaction(gtx);
      if (trace) log.tracef("Removed local transaction %s? %b", gtx, remove);
   }

   /**
    * Returns an existing remote transaction or creates one if none exists.
    * Atomicity: this method supports concurrent invocations, guaranteeing that all threads will see the same
    * transaction object.
    */
   public RemoteTransaction getOrCreateRemoteTransaction(GlobalTransaction globalTx, WriteCommand[] modifications) {
      return getOrCreateRemoteTransaction(globalTx, modifications, currentTopologyId);
   }

   private RemoteTransaction getOrCreateRemoteTransaction(GlobalTransaction globalTx, WriteCommand[] modifications, int topologyId) {
      RemoteTransaction remoteTransaction = remoteTransactions.get(globalTx);
      if (remoteTransaction != null)
         return remoteTransaction;
      remoteTransaction = modifications == null ? txFactory.newRemoteTransaction(globalTx, topologyId)
            : txFactory.newRemoteTransaction(modifications, globalTx, topologyId);
      RemoteTransaction existing = remoteTransactions.putIfAbsent(globalTx, remoteTransaction);
      if (existing != null) {
         if (trace) log.tracef("Remote transaction already registered: %s", existing);
         return existing;
      } else {
         if (trace) log.tracef("Created and registered remote transaction %s", remoteTransaction);
         if (remoteTransaction.getTopologyId() < minTxTopologyId) {
            if (trace) log.tracef("Changing minimum topology ID from %d to %d", minTxTopologyId, remoteTransaction.getTopologyId());
            minTxTopologyId = remoteTransaction.getTopologyId();
         }
         return remoteTransaction;
      }
   }

   /**
    * Returns the {@link org.infinispan.transaction.xa.TransactionXaAdapter} corresponding to the supplied transaction.
    * If none exists, will be created first.
    */
   public LocalTransaction getOrCreateLocalTransaction(Transaction transaction, boolean implicitTransaction) {
      LocalTransaction current = localTransactions.get(transaction);
      if (current == null) {
         Address localAddress = rpcManager != null ? rpcManager.getTransport().getAddress() : null;
         GlobalTransaction tx = txFactory.newGlobalTransaction(localAddress, false);
         current = txFactory.newLocalTransaction(transaction, tx, implicitTransaction, currentTopologyId);
         if (trace) log.tracef("Created a new local transaction: %s", current);
         localTransactions.put(transaction, current);
         globalToLocalTransactions.put(current.getGlobalTransaction(), current);
         notifier.notifyTransactionRegistered(tx, true);
      }
      return current;
   }

   /**
    * Removes the {@link org.infinispan.transaction.xa.TransactionXaAdapter} corresponding to the given tx. Returns true
    * if such an tx exists.
    */
   public boolean removeLocalTransaction(LocalTransaction localTransaction) {
      return localTransaction != null && (removeLocalTransactionInternal(localTransaction.getTransaction()) != null);
   }

   protected final LocalTransaction removeLocalTransactionInternal(Transaction tx) {
      LocalTransaction localTx = localTransactions.get(tx);
      if (localTx != null) {
         globalToLocalTransactions.remove(localTx.getGlobalTransaction());
         localTransactions.remove(tx);
         releaseResources(localTx);
      }
      return localTx;
   }

   private void releaseResources(CacheTransaction cacheTransaction) {
      if (cacheTransaction != null) {
         if (clustered) {
            recalculateMinTopologyIdIfNeeded(cacheTransaction);
         }
         if (trace) log.tracef("Removed %s from transaction table.", cacheTransaction);
         cacheTransaction.notifyOnTransactionFinished();
      }
   }

   /**
    * Removes the {@link RemoteTransaction} corresponding to the given tx.
    */
   public void remoteTransactionCommitted(GlobalTransaction gtx, boolean onePc) {
      boolean optimisticWih1Pc = onePc && (configuration.transaction().lockingMode() == LockingMode.OPTIMISTIC);
      if (Configurations.isSecondPhaseAsync(configuration) || configuration.transaction().transactionProtocol().isTotalOrder() || optimisticWih1Pc) {
         removeRemoteTransaction(gtx);
      }
   }

   public final RemoteTransaction removeRemoteTransaction(GlobalTransaction txId) {
      RemoteTransaction removed = remoteTransactions.remove(txId);
      if (trace) log.tracef("Removed remote transaction %s ? %s", txId, removed);
      releaseResources(removed);
      return removed;
   }

   public int getRemoteTxCount() {
      return remoteTransactions.size();
   }

   public int getLocalTxCount() {
      return localTransactions.size();
   }

   /**
    * Looks up a LocalTransaction given a GlobalTransaction.
    * @param txId the global transaction identifier
    * @return the LocalTransaction or null if not found
    */
   public LocalTransaction getLocalTransaction(GlobalTransaction txId) {
      return globalToLocalTransactions.get(txId);
   }

   public boolean containsLocalTx(GlobalTransaction globalTransaction) {
      return globalToLocalTransactions.containsKey(globalTransaction);
   }

   public LocalTransaction getLocalTransaction(Transaction tx) {
      return localTransactions.get(tx);
   }

   public boolean containRemoteTx(GlobalTransaction globalTransaction) {
      return remoteTransactions.containsKey(globalTransaction);
   }

   public Collection<RemoteTransaction> getRemoteTransactions() {
      return remoteTransactions.values();
   }

   public Collection<LocalTransaction> getLocalTransactions() {
      return localTransactions.values();
   }

   protected final void recalculateMinTopologyIdIfNeeded(CacheTransaction removedTransaction) {
      if (removedTransaction == null) throw new IllegalArgumentException("Transaction cannot be null!");
      if (currentTopologyId != CACHE_STOPPED_TOPOLOGY_ID) {

         // Assume that we only get here if we are clustered.
         int removedTransactionTopologyId = removedTransaction.getTopologyId();
         if (removedTransactionTopologyId < minTxTopologyId) {
            if (trace) log.tracef("A transaction has a topology ID (%s) that is smaller than the smallest transaction topology ID (%s) this node knows about!  This can happen if a concurrent thread recalculates the minimum topology ID after the current transaction has been removed from the transaction table.", removedTransactionTopologyId, minTxTopologyId);
         } else if (removedTransactionTopologyId == minTxTopologyId && removedTransactionTopologyId < currentTopologyId) {
            // We should only need to re-calculate the minimum topology ID if the transaction being completed
            // has the same ID as the smallest known transaction ID, to check what the new smallest is, and this is
            // not the current topology ID.
            calculateMinTopologyId(removedTransactionTopologyId);
         }
      }
   }

   @TopologyChanged
   @SuppressWarnings("unused")
   public void onTopologyChange(TopologyChangedEvent<?, ?> tce) {
      // don't do anything if this cache is not clustered
      if (clustered) {
         if (!tce.isPre()) {
            // The topology id must be updated after the topology was updated in StateConsumerImpl,
            // as state transfer requires transactions not sent to the new owners to have a smaller topology id.
            currentTopologyId = tce.getNewTopologyId();
            log.debugf("Topology changed, recalculating minTopologyId");
            calculateMinTopologyId(-1);
         }
      }
   }

   @ViewChanged
   public void onViewChange(final ViewChangedEvent e) {
      executorService.submit(new Callable<Void>() {
         public Void call() {
            cleanupLeaverTransactions(e.getNewMembers());
            return null;
         }
      });
   }

   /**
    * This method calculates the minimum topology ID known by the current node.  This method is only used in a clustered
    * cache, and only invoked when either a topology change is detected, or a transaction whose topology ID is not the same as
    * the current topology ID.
    * <p/>
    * This method is guarded by minTopologyRecalculationLock to prevent concurrent updates to the minimum topology ID field.
    *
    * @param idOfRemovedTransaction the topology ID associated with the transaction that triggered this recalculation, or -1
    *                               if triggered by a topology change event.
    */
   @GuardedBy("minTopologyRecalculationLock")
   private void calculateMinTopologyId(int idOfRemovedTransaction) {
      minTopologyRecalculationLock.lock();
      try {
         // We should only need to re-calculate the minimum topology ID if the transaction being completed
         // has the same ID as the smallest known transaction ID, to check what the new smallest is.  We do this check
         // again here, since this is now within a synchronized method.
         if (idOfRemovedTransaction == -1 ||
               (idOfRemovedTransaction == minTxTopologyId && idOfRemovedTransaction < currentTopologyId)) {
            int minTopologyIdFound = currentTopologyId;

            for (CacheTransaction ct : localTransactions.values()) {
               int topologyId = ct.getTopologyId();
               if (topologyId < minTopologyIdFound) minTopologyIdFound = topologyId;
            }
            for (CacheTransaction ct : remoteTransactions.values()) {
               int topologyId = ct.getTopologyId();
               if (topologyId < minTopologyIdFound) minTopologyIdFound = topologyId;
            }
            if (minTopologyIdFound != minTxTopologyId) {
               if (trace) log.tracef("Changing minimum topology ID from %s to %s", minTxTopologyId, minTopologyIdFound);
               minTxTopologyId = minTopologyIdFound;
            } else {
               if (trace) log.tracef("Minimum topology ID still is %s; nothing to change", minTopologyIdFound);
            }
         }
      } finally {
         minTopologyRecalculationLock.unlock();
      }
   }

   private boolean areTxsOnGoing() {
      return !localTransactions.isEmpty() || (remoteTransactions != null && !remoteTransactions.isEmpty());
   }

   private void shutDownGracefully() {
      if (log.isDebugEnabled())
         log.debugf("Wait for on-going transactions to finish for %s.", Util.prettyPrintTime(configuration.transaction().cacheStopTimeout(), TimeUnit.MILLISECONDS));
      long failTime = timeService.expectedEndTime(configuration.transaction().cacheStopTimeout(), TimeUnit.MILLISECONDS);
      boolean txsOnGoing = areTxsOnGoing();
      while (txsOnGoing && !timeService.isTimeExpired(failTime)) {
         try {
            Thread.sleep(30);
            txsOnGoing = areTxsOnGoing();
         } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            if (clustered) {
               log.debugf("Interrupted waiting for on-going transactions to finish. %s local transactions and %s remote transactions", localTransactions.size(), remoteTransactions.size());
            } else {
               log.debugf("Interrupted waiting for %s on-going transactions to finish.", localTransactions.size());
            }
         }
      }

      if (txsOnGoing) {
         log.unfinishedTransactionsRemain(localTransactions == null ? 0 : localTransactions.size(),
                                          remoteTransactions == null ? 0 : remoteTransactions.size());
      } else {
         log.debug("All transactions terminated");
      }
   }

   /**
    * With the current state transfer implementation it is possible for a transaction to be prepared several times
    * on a remote node. This might cause leaks, e.g. if the transaction is prepared, committed and prepared again.
    * Once marked as completed (because of commit or rollback) any further prepare received on that transaction are discarded.
    */
   public void markTransactionCompleted(GlobalTransaction gtx, boolean successful) {
      if (completedTransactionsInfo != null) {
         completedTransactionsInfo.markTransactionCompleted(gtx, successful);
      }
   }

   /**
    * @see #markTransactionCompleted(org.infinispan.transaction.xa.GlobalTransaction, boolean)
    */
   public boolean isTransactionCompleted(GlobalTransaction gtx) {
      if (completedTransactionsInfo == null)
         return false;

      return completedTransactionsInfo.isTransactionCompleted(gtx);
   }

   /**
    * @see #markTransactionCompleted(org.infinispan.transaction.xa.GlobalTransaction, boolean)
    */
   public CompletedTransactionStatus getCompletedTransactionStatus(GlobalTransaction gtx) {
      if (completedTransactionsInfo == null)
         return CompletedTransactionStatus.NOT_COMPLETED;

      return completedTransactionsInfo.getTransactionStatus(gtx);
   }

   private class CompletedTransactionsInfo {
      final EquivalentConcurrentHashMapV8<GlobalTransaction, CompletedTransactionInfo> completedTransactions;
      // The highest transaction id previously cleared, one per originator
      final EquivalentConcurrentHashMapV8<Address, Long> nodeMaxPrunedTxIds;
      // The highest transaction id previously cleared, with any originator
      volatile long globalMaxPrunedTxId;

      public CompletedTransactionsInfo() {
         nodeMaxPrunedTxIds = new EquivalentConcurrentHashMapV8<>(AnyEquivalence.getInstance(), AnyEquivalence.getInstance());
         completedTransactions = new EquivalentConcurrentHashMapV8<>(AnyEquivalence.getInstance(), AnyEquivalence.getInstance());
         globalMaxPrunedTxId = -1;
      }


      /**
       * With the current state transfer implementation it is possible for a transaction to be prepared several times
       * on a remote node. This might cause leaks, e.g. if the transaction is prepared, committed and prepared again.
       * Once marked as completed (because of commit or rollback) any further prepare received on that transaction are discarded.
       */
      public void markTransactionCompleted(GlobalTransaction globalTx, boolean successful) {
         if (trace) log.tracef("Marking transaction %s as completed", globalTx);
         completedTransactions.put(globalTx, new CompletedTransactionInfo(timeService.time(), successful));
      }

      /**
       * @see #markTransactionCompleted(GlobalTransaction, boolean)
       */
      public boolean isTransactionCompleted(GlobalTransaction gtx) {
         if (completedTransactions.containsKey(gtx))
            return true;

         // Transaction ids are allocated in sequence, so any transaction with a smaller id must have been started
         // before a transaction that was already removed from the completed transactions map because it was too old.
         // We assume that the transaction was either committed, or it was rolled back (e.g. because the prepare
         // RPC timed out.
         // Note: We must check the id *after* verifying that the tx doesn't exist in the map.
         if (gtx.getId() > globalMaxPrunedTxId)
            return false;
         Long nodeMaxPrunedTxId = nodeMaxPrunedTxIds.get(gtx.getAddress());
         return nodeMaxPrunedTxId != null && gtx.getId() <= nodeMaxPrunedTxId;
      }

      public CompletedTransactionStatus getTransactionStatus(GlobalTransaction gtx) {
         CompletedTransactionInfo completedTx = completedTransactions.get(gtx);
         if (completedTx != null) {
            return completedTx.successful ? CompletedTransactionStatus.COMMITTED : CompletedTransactionStatus.ABORTED;
         }

         // Transaction ids are allocated in sequence, so any transaction with a smaller id must have been started
         // before a transaction that was already removed from the completed transactions map because it was too old.
         // We assume that the transaction was either committed, or it was rolled back (e.g. because the prepare
         // RPC timed out.
         // Note: We must check the id *after* verifying that the tx doesn't exist in the map.
         if (gtx.getId() > globalMaxPrunedTxId)
            return CompletedTransactionStatus.NOT_COMPLETED;
         Long nodeMaxPrunedTxId = nodeMaxPrunedTxIds.get(gtx.getAddress());
         if (nodeMaxPrunedTxId == null) {
            // We haven't removed any transaction for this node
            return CompletedTransactionStatus.NOT_COMPLETED;
         } else if (gtx.getId() > nodeMaxPrunedTxId) {
            // We haven't removed this particular transaction yet
            return CompletedTransactionStatus.NOT_COMPLETED;
         } else {
            // We already removed the status of this transaction from the completed transactions map
            return CompletedTransactionStatus.EXPIRED;
         }
      }

      public void cleanupCompletedTransactions() {
         if (completedTransactions.isEmpty())
            return;

         try {
            if (trace) log.tracef("About to cleanup completed transaction. Initial size is %d", completedTransactions.size());
            long beginning = timeService.time();
            long minCompleteTimestamp = timeService.time() - TimeUnit.MILLISECONDS.toNanos(configuration.transaction().completedTxTimeout());
            int removedEntries = 0;

            // Collect the leavers. They will be removed at the end.
            Set<Address> leavers = new HashSet<>();
            for (Map.Entry<Address, Long> e : nodeMaxPrunedTxIds.entrySet()) {
               if (!rpcManager.getMembers().contains(e.getKey())) {
                  leavers.add(e.getKey());
               }
            }

            // Remove stale completed transactions.
            Iterator<Map.Entry<GlobalTransaction, CompletedTransactionInfo>> txIterator = completedTransactions.entrySet().iterator();
            while (txIterator.hasNext()) {
               Map.Entry<GlobalTransaction, CompletedTransactionInfo> e = txIterator.next();
               CompletedTransactionInfo completedTx = e.getValue();
               if (minCompleteTimestamp - completedTx.timestamp > 0) {
                  // Need to update lastPrunedTxId *before* removing the tx from the map
                  // Don't need atomic operations, there can't be more than one thread updating lastPrunedTxId.
                  final long txId = e.getKey().getId();
                  final Address address = e.getKey().getAddress();
                  updateLastPrunedTxId(txId, address);

                  txIterator.remove();
                  removedEntries++;
               } else {
                  // Nodes with "active" completed transactions are not removed..
                  leavers.remove(e.getKey().getAddress());
               }
            }

            // Finally, remove nodes that are no longer members and don't have any "active" completed transactions.
            for (Address e : leavers) {
               nodeMaxPrunedTxIds.remove(e);
            }

            long duration = timeService.timeDuration(beginning, TimeUnit.MILLISECONDS);

            if (trace) log.tracef("Finished cleaning up completed transactions in %d millis, %d transactions were removed, " +
                  "current number of completed transactions is %d",
                  removedEntries, duration, completedTransactions.size());
            if (trace) log.tracef("Last pruned transaction ids were updated: %d, %s", globalMaxPrunedTxId, nodeMaxPrunedTxIds);
         } catch (Exception e) {
            log.errorf(e, "Failed to cleanup completed transactions: %s", e.getMessage());
         }
      }

      private void updateLastPrunedTxId(final long txId, Address address) {
         if (txId > globalMaxPrunedTxId) {
            globalMaxPrunedTxId = txId;
         }
         nodeMaxPrunedTxIds.compute(address, (a, nodeMaxPrunedTxId) -> {
            if (nodeMaxPrunedTxId != null && txId <= nodeMaxPrunedTxId) {
               return nodeMaxPrunedTxId;
            }
            return txId;
         });
      }
   }
   private static class CompletedTransactionInfo {
      public final long timestamp;
      public final boolean successful;

      private CompletedTransactionInfo(long timestamp, boolean successful) {
         this.timestamp = timestamp;
         this.successful = successful;
      }
   }
}


File: core/src/main/java/org/infinispan/transaction/synchronization/SynchronizationAdapter.java
package org.infinispan.transaction.synchronization;

import org.infinispan.commands.CommandsFactory;
import org.infinispan.commons.CacheException;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.interceptors.locking.ClusteringDependentLogic;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.transaction.impl.AbstractEnlistmentAdapter;
import org.infinispan.transaction.impl.LocalTransaction;
import org.infinispan.transaction.impl.TransactionCoordinator;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.Status;
import javax.transaction.Synchronization;
import javax.transaction.xa.XAException;

/**
 * {@link Synchronization} implementation for integrating with the TM.
 * See <a href="https://issues.jboss.org/browse/ISPN-888">ISPN-888</a> for more information on this.
 *
 * @author Mircea.Markus@jboss.com
 * @since 5.0
 */
public class SynchronizationAdapter extends AbstractEnlistmentAdapter implements Synchronization {

   private static final Log log = LogFactory.getLog(SynchronizationAdapter.class);

   private final LocalTransaction localTransaction;

   public SynchronizationAdapter(LocalTransaction localTransaction, TransactionCoordinator txCoordinator,
                                 CommandsFactory commandsFactory, RpcManager rpcManager,
                                 TransactionTable transactionTable, ClusteringDependentLogic clusteringLogic,
                                 Configuration configuration) {
      super(localTransaction, commandsFactory, rpcManager, transactionTable, clusteringLogic, configuration, txCoordinator);
      this.localTransaction = localTransaction;
   }

   @Override
   public void beforeCompletion() {
      log.tracef("beforeCompletion called for %s", localTransaction);
      try {
         txCoordinator.prepare(localTransaction);
      } catch (XAException e) {
         throw new CacheException("Could not prepare. ", e);//todo shall we just swallow this exception?
      }
   }

   @Override
   public void afterCompletion(int status) {
      if (log.isTraceEnabled()) {
         log.tracef("afterCompletion(%s) called for %s.", status, localTransaction);
      }
      boolean isOnePhase;
      if (status == Status.STATUS_COMMITTED) {
         try {
            isOnePhase = txCoordinator.commit(localTransaction, false);
         } catch (XAException e) {
            throw new CacheException("Could not commit.", e);
         }
         releaseLocksForCompletedTransaction(localTransaction, isOnePhase);
      } else if (status == Status.STATUS_ROLLEDBACK) {
         try {
            txCoordinator.rollback(localTransaction);
         } catch (XAException e) {
            throw new CacheException("Could not commit.", e);
         }
      } else {
         throw new IllegalArgumentException("Unknown status: " + status);
      }
   }

   @Override
   public String toString() {
      return "SynchronizationAdapter{" +
            "localTransaction=" + localTransaction +
            "} " + super.toString();
   }

   @Override
   public boolean equals(Object o) {
      if (this == o) return true;
      if (o == null || getClass() != o.getClass()) return false;

      SynchronizationAdapter that = (SynchronizationAdapter) o;

      if (localTransaction != null ? !localTransaction.equals(that.localTransaction) : that.localTransaction != null)
         return false;

      return true;
   }
}


File: core/src/main/java/org/infinispan/transaction/tm/DummyTransaction.java
package org.infinispan.transaction.tm;


import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.HeuristicMixedException;
import javax.transaction.HeuristicRollbackException;
import javax.transaction.RollbackException;
import javax.transaction.Status;
import javax.transaction.Synchronization;
import javax.transaction.SystemException;
import javax.transaction.Transaction;
import javax.transaction.xa.XAException;
import javax.transaction.xa.XAResource;
import javax.transaction.xa.Xid;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;

import static java.lang.String.format;

/**
 * @author bela
 * @since 4.0
 */
public class DummyTransaction implements Transaction {
   /*
    * Developer notes:
    *
    * => prepare() XA_RDONLY: the resource is finished and we shouldn't invoke the commit() or rollback().
    * => prepare() XA_RB*: the resource is rolled back and we shouldn't invoke the rollback().
    * //note// for both cases above, the commit() or rollback() will return XA_NOTA that we will ignore.
    *
    * => 1PC optimization: if we have a single XaResource, we can skip the prepare() and invoke commit(1PC).
    * => Last Resource Commit optimization: if all the resources (except last) vote XA_OK or XA_RDONLY, we can skip the
    * prepare() on the last resource and invoke commit(1PC).
    * //note// both optimization not supported since we split the commit in 2 phases for debugging
    */

   private static final Log log = LogFactory.getLog(DummyTransaction.class);
   private static boolean trace = log.isTraceEnabled();
   private final Xid xid;
   private volatile int status = Status.STATUS_UNKNOWN;
   private final List<Synchronization> syncs;
   private final List<XAResource> resources;
   private RollbackException firstRollbackException;

   public DummyTransaction(DummyBaseTransactionManager tm) {
      status = Status.STATUS_ACTIVE;
      if (tm.isUseXaXid()) {
         xid = new DummyXid(tm.transactionManagerId);
      } else {
         xid = new DummyNoXaXid();
      }
      if (trace) {
         log.tracef("Created new transaction with Xid=%s", xid);
      }
      syncs = new ArrayList<>(2);
      resources = new ArrayList<>(2);
   }

   private static boolean isRollbackCode(XAException ex) {
      /*
      XA_RBBASE      the inclusive lower bound of the rollback codes
      XA_RBROLLBACK  the rollback was caused by an unspecified reason
      XA_RBCOMMFAIL  the rollback was caused by a communication failure
      XA_RBDEADLOCK  a deadlock was detected
      XA_RBINTEGRITY a condition that violates the integrity of the resources was detected
      XA_RBOTHER     the resource manager rolled back the transaction branch for a reason not on this list
      XA_RBPROTO     a protocol error occurred in the resource manager
      XA_RBTIMEOUT   a transaction branch took too long
      XA_RBTRANSIENT may retry the transaction branch
      XA_RBEND       the inclusive upper bound of the rollback codes
       */
      return ex.errorCode >= XAException.XA_RBBASE && ex.errorCode <= XAException.XA_RBEND;
   }

   private static RollbackException newRollbackException(String message, Throwable cause) {
      RollbackException exception = new RollbackException(message);
      exception.initCause(cause);
      return exception;
   }

   /**
    * Attempt to commit this transaction.
    *
    * @throws RollbackException          If the transaction was marked for rollback only, the transaction is rolled back
    *                                    and this exception is thrown.
    * @throws SystemException            If the transaction service fails in an unexpected way.
    * @throws HeuristicMixedException    If a heuristic decision was made and some some parts of the transaction have
    *                                    been committed while other parts have been rolled back.
    * @throws HeuristicRollbackException If a heuristic decision to roll back the transaction was made.
    * @throws SecurityException          If the caller is not allowed to commit this transaction.
    */
   @Override
   public void commit() throws RollbackException, HeuristicMixedException, HeuristicRollbackException, SecurityException, SystemException {
      if (trace) {
         log.tracef("Transaction.commit() invoked in transaction with Xid=%s", xid);
      }
      checkDone("Cannot commit transaction.");
      runPrepare();
      runCommit(false);
      if (firstRollbackException != null) {
         throw firstRollbackException;
      }
   }

   /**
    * Rolls back this transaction.
    *
    * @throws IllegalStateException If the transaction is in a state where it cannot be rolled back. This could be
    *                               because the transaction is no longer active, or because it is in the {@link
    *                               Status#STATUS_PREPARED prepared state}.
    * @throws SystemException       If the transaction service fails in an unexpected way.
    */
   @Override
   public void rollback() throws IllegalStateException, SystemException {
      if (trace) {
         log.tracef("Transaction.rollback() invoked in transaction with Xid=%s", xid);
      }
      checkDone("Cannot rollback transaction");
      try {
         status = Status.STATUS_MARKED_ROLLBACK;
         endResources();
         runCommit(false);
      } catch (HeuristicMixedException | HeuristicRollbackException e) {
         log.errorRollingBack(e);
         SystemException systemException = new SystemException("Unable to rollback transaction");
         systemException.initCause(e);
         throw systemException;
      }
   }

   /**
    * Mark the transaction so that the only possible outcome is a rollback.
    *
    * @throws IllegalStateException If the transaction is not in an active state.
    * @throws SystemException       If the transaction service fails in an unexpected way.
    */
   @Override
   public void setRollbackOnly() throws IllegalStateException, SystemException {
      if (trace) {
         log.tracef("Transaction.setRollbackOnly() invoked in transaction with Xid=%s", xid);
      }
      checkDone("Cannot change status");
      markRollbackOnly(new RollbackException("Transaction marked as rollback only."));
   }

   /**
    * Get the status of the transaction.
    *
    * @return The status of the transaction. This is one of the {@link Status} constants.
    * @throws SystemException If the transaction service fails in an unexpected way.
    */
   @Override
   public int getStatus() throws SystemException {
      return status;
   }

   /**
    * Enlist an XA resource with this transaction.
    *
    * @return <code>true</code> if the resource could be enlisted with this transaction, otherwise <code>false</code>.
    * @throws RollbackException     If the transaction is marked for rollback only.
    * @throws IllegalStateException If the transaction is in a state where resources cannot be enlisted. This could be
    *                               because the transaction is no longer active, or because it is in the {@link
    *                               Status#STATUS_PREPARED prepared state}.
    * @throws SystemException       If the transaction service fails in an unexpected way.
    */
   @Override
   public boolean enlistResource(XAResource resource) throws RollbackException, IllegalStateException, SystemException {
      if (trace) {
         log.tracef("Transaction.enlistResource(%s) invoked in transaction with Xid=%s", resource, xid);
      }
      checkStatusBeforeRegister("resource");

      //avoid duplicates
      for (XAResource otherResource : resources) {
         try {
            if (otherResource.isSameRM(resource)) {
               log.debug("Ignoring resource. It is already there.");
               return true;
            }
         } catch (XAException e) {
            //ignored
         }
      }

      resources.add(resource);

      try {
         if (trace) {
            log.tracef("XaResource.start() invoked in transaction with Xid=%s", xid);
         }
         resource.start(xid, XAResource.TMNOFLAGS);
      } catch (XAException e) {
         if (isRollbackCode(e)) {
            RollbackException exception = newRollbackException(format("Resource %s rolled back the transaction while XaResource.start()", resource), e);
            markRollbackOnly(exception);
            log.errorEnlistingResource(e);
            throw exception;
         }
         log.errorEnlistingResource(e);
         throw new SystemException(e.getMessage());
      }
      return true;
   }

   /**
    * De-list an XA resource from this transaction.
    *
    * @return <code>true</code> if the resource could be de-listed from this transaction, otherwise <code>false</code>.
    * @throws IllegalStateException If the transaction is in a state where resources cannot be de-listed. This could be
    *                               because the transaction is no longer active.
    * @throws SystemException       If the transaction service fails in an unexpected way.
    */
   @Override
   public boolean delistResource(XAResource xaRes, int flag)
         throws IllegalStateException, SystemException {
      throw new SystemException("not supported");
   }

   /**
    * Register a {@link Synchronization} callback with this transaction.
    *
    * @throws RollbackException     If the transaction is marked for rollback only.
    * @throws IllegalStateException If the transaction is in a state where {@link Synchronization} callbacks cannot be
    *                               registered. This could be because the transaction is no longer active, or because it
    *                               is in the {@link Status#STATUS_PREPARED prepared state}.
    * @throws SystemException       If the transaction service fails in an unexpected way.
    */
   @Override
   public void registerSynchronization(Synchronization sync) throws RollbackException, IllegalStateException, SystemException {
      if (trace) {
         log.tracef("Transaction.registerSynchronization(%s) invoked in transaction with Xid=%s", sync, xid);
      }
      checkStatusBeforeRegister("synchronization");
      if (trace) {
         log.tracef("Registering synchronization handler %s", sync);
      }
      syncs.add(sync);
   }

   public Collection<XAResource> getEnlistedResources() {
      return Collections.unmodifiableList(resources);
   }

   public boolean runPrepare() {
      if (trace) {
         log.tracef("runPrepare() invoked in transaction with Xid=%s", xid);
      }
      notifyBeforeCompletion();
      endResources();

      if (status == Status.STATUS_MARKED_ROLLBACK) {
         return false;
      }

      status = Status.STATUS_PREPARING;

      for (XAResource res : getEnlistedResources()) {
         //note: it is safe to return even if we don't prepare all the resources. rollback will be invoked.
         try {
            if (trace) {
               log.tracef("XaResource.prepare() for %s", res);
            }
            //don't need to check return value. the only possible values are OK or READ_ONLY.
            res.prepare(xid);
         } catch (XAException e) {
            if (trace) {
               log.trace("The resource wants to rollback!", e);
            }
            markRollbackOnly(newRollbackException(format("XaResource.prepare() for %s wants to rollback.", res), e));
            return false;
         } catch (Throwable th) {
            markRollbackOnly(newRollbackException(format("Unexpected error in XaResource.prepare() for %s. Rollback transaction.", res), th));
            log.unexpectedErrorFromResourceManager(th);
            return false;
         }
      }
      status = Status.STATUS_PREPARED;
      return true;
   }

   public void runCommit(boolean forceRollback) throws HeuristicMixedException, HeuristicRollbackException {
      if (trace) {
         log.tracef("runCommit(forceRollback=%b) invoked in transaction with Xid=%s", forceRollback, xid);
      }
      if (forceRollback) {
         markRollbackOnly(new RollbackException("Force rollback invoked. (debug mode)"));
      }

      int notifyAfterStatus = 0;

      try {
         if (status == Status.STATUS_MARKED_ROLLBACK) {
            notifyAfterStatus = Status.STATUS_ROLLEDBACK;
            rollbackResources();
         } else {
            notifyAfterStatus = Status.STATUS_COMMITTED;
            commitResources();
         }
      } finally {
         notifyAfterCompletion(notifyAfterStatus);
         DummyBaseTransactionManager.setTransaction(null);
      }
   }

   @Override
   public String toString() {
      return "DummyTransaction{" +
            "xid=" + xid +
            ", status=" + status +
            '}';
   }

   public XAResource firstEnlistedResource() {
      return getEnlistedResources().iterator().next();
   }

   public Xid getXid() {
      return xid;
   }

   public Collection<Synchronization> getEnlistedSynchronization() {
      return Collections.unmodifiableList(syncs);
   }

   /**
    * Must be defined for increased performance
    */
   @Override
   public final int hashCode() {
      return xid.hashCode();
   }

   @Override
   public final boolean equals(Object obj) {
      return this == obj;
   }

   private void markRollbackOnly(RollbackException e) {
      if (status == Status.STATUS_MARKED_ROLLBACK) {
         return;
      }
      status = Status.STATUS_MARKED_ROLLBACK;
      if (firstRollbackException == null) {
         firstRollbackException = e;
      }
   }

   private void finishResource(boolean commit) throws HeuristicRollbackException, HeuristicMixedException {
      boolean ok = false;
      boolean heuristic = false;
      boolean error = false;
      Exception cause = null;

      for (XAResource res : getEnlistedResources()) {
         try {
            if (commit) {
               if (trace) {
                  log.tracef("XaResource.commit() for %s", res);
               }
               //we only do 2-phase commits
               res.commit(xid, false);
            } else {
               if (trace) {
                  log.tracef("XaResource.rollback() for %s", res);
               }
               res.rollback(xid);
            }
            ok = true;
         } catch (XAException e) {
            cause = e;
            log.errorCommittingTx(e);
            switch (e.errorCode) {
               case XAException.XA_HEURCOM:
               case XAException.XA_HEURRB:
               case XAException.XA_HEURMIX:
                  heuristic = true;
                  break;
               case XAException.XAER_NOTA:
                  //just ignore it...
                  ok = true;
                  break;
               default:
                  error = true;
                  break;
            }
         }
      }

      resources.clear();
      if (heuristic && !ok && !error) {
         //all the resources thrown an heuristic exception
         HeuristicRollbackException exception = new HeuristicRollbackException();
         exception.initCause(cause);
         throw exception;
      } else if (error || heuristic) {
         status = Status.STATUS_UNKNOWN;
         //some resources commits, other rollbacks and others we don't know...
         HeuristicMixedException exception = new HeuristicMixedException();
         exception.initCause(cause);
         throw exception;
      }
   }

   private void commitResources() throws HeuristicRollbackException, HeuristicMixedException {
      status = Status.STATUS_COMMITTING;
      try {
         finishResource(true);
      } catch (HeuristicRollbackException | HeuristicMixedException e) {
         status = Status.STATUS_UNKNOWN;
         throw e;
      }
      status = Status.STATUS_COMMITTED;
   }

   private void rollbackResources() throws HeuristicRollbackException, HeuristicMixedException {
      status = Status.STATUS_ROLLING_BACK;
      try {
         finishResource(false);
      } catch (HeuristicRollbackException | HeuristicMixedException e) {
         status = Status.STATUS_UNKNOWN;
         throw e;
      }
      status = Status.STATUS_ROLLEDBACK;
   }

   private void notifyBeforeCompletion() {
      for (Synchronization s : getEnlistedSynchronization()) {
         if (trace) {
            log.tracef("Synchronization.beforeCompletion() for %s", s);
         }
         try {
            s.beforeCompletion();
         } catch (Throwable t) {
            markRollbackOnly(newRollbackException(format("Synchronization.beforeCompletion() for %s wants to rollback.", s), t));
            log.beforeCompletionFailed(s, t);
         }
      }
   }

   private void notifyAfterCompletion(int status) {
      for (Synchronization s : getEnlistedSynchronization()) {
         if (trace) {
            log.tracef("Synchronization.afterCompletion() for %s", s);
         }
         try {
            s.afterCompletion(status);
         } catch (Throwable t) {
            log.afterCompletionFailed(s, t);
         }
      }
      syncs.clear();
   }

   private void endResources() {
      for (XAResource resource : getEnlistedResources()) {
         if (trace) {
            log.tracef("XAResource.end() for %s", resource);
         }
         try {
            resource.end(xid, XAResource.TMSUCCESS);
         } catch (XAException e) {
            markRollbackOnly(newRollbackException(format("XaResource.end() for %s wants to rollback.", resource), e));
            log.xaResourceEndFailed(resource, e);
         } catch (Throwable t) {
            markRollbackOnly(newRollbackException(format("Unexpected error in XaResource.end() for %s. Marked as rollback", resource), t));
            log.xaResourceEndFailed(resource, t);
         }
      }
   }

   private void checkStatusBeforeRegister(String component) throws RollbackException, IllegalStateException {
      if (status == Status.STATUS_MARKED_ROLLBACK) {
         throw new RollbackException("Transaction has been marked as rollback only");
      }
      checkDone(format("Cannot register any more %s", component));
   }

   private void checkDone(String message) {
      if (isDone()) {
         throw new IllegalStateException(format("Transaction is done. %s", message));
      }
   }

   private boolean isDone() {
      switch (status) {
         case Status.STATUS_PREPARING:
         case Status.STATUS_PREPARED:
         case Status.STATUS_COMMITTING:
         case Status.STATUS_COMMITTED:
         case Status.STATUS_ROLLING_BACK:
         case Status.STATUS_ROLLEDBACK:
         case Status.STATUS_UNKNOWN:
            return true;
      }
      return false;
   }
}


File: core/src/main/java/org/infinispan/transaction/xa/TransactionXaAdapter.java
package org.infinispan.transaction.xa;

import org.infinispan.commands.CommandsFactory;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.interceptors.locking.ClusteringDependentLogic;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.transaction.impl.AbstractEnlistmentAdapter;
import org.infinispan.transaction.impl.TransactionCoordinator;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.xa.recovery.RecoveryManager;
import org.infinispan.transaction.xa.recovery.SerializableXid;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.xa.XAException;
import javax.transaction.xa.XAResource;
import javax.transaction.xa.Xid;

/**
 * This acts both as an local {@link org.infinispan.transaction.xa.CacheTransaction} and implementor of an {@link
 * javax.transaction.xa.XAResource} that will be called by tx manager on various tx stages.
 *
 * @author Mircea.Markus@jboss.com
 * @since 4.0
 */
public class TransactionXaAdapter extends AbstractEnlistmentAdapter implements XAResource {

   private static final Log log = LogFactory.getLog(TransactionXaAdapter.class);
   private static boolean trace = log.isTraceEnabled();

   /**
    * It is really useful only if TM and client are in separate processes and TM fails. This is because a client might
    * call tm.begin and then the TM (running separate process) crashes. In this scenario the TM won't ever call
    * XAResource.rollback, so these resources would be held there forever. By knowing the timeout the RM can proceed
    * releasing the resources associated with given tx.
    */
   private int txTimeout;

   private final XaTransactionTable txTable;


   /**
    * XAResource is associated with a transaction between enlistment (XAResource.start()) XAResource.end(). It's only the
    * boundary methods (prepare, commit, rollback) that need to be "stateless".
    * Reefer to section 3.4.4 from JTA spec v.1.1
    */
   private final LocalXaTransaction localTransaction;
   private final RecoveryManager recoveryManager;
   private volatile RecoveryManager.RecoveryIterator recoveryIterator;
   private boolean recoveryEnabled;
   private String cacheName;
   private boolean onePhaseTotalOrder;

   public TransactionXaAdapter(LocalXaTransaction localTransaction, TransactionTable txTable,
                               RecoveryManager rm, TransactionCoordinator txCoordinator,
                               CommandsFactory commandsFactory, RpcManager rpcManager,
                               ClusteringDependentLogic clusteringDependentLogic,
                               Configuration configuration, String cacheName) {
      super(localTransaction, commandsFactory, rpcManager, txTable, clusteringDependentLogic, configuration, txCoordinator);
      this.localTransaction = localTransaction;
      this.txTable = (XaTransactionTable) txTable;
      this.recoveryManager = rm;
      this.cacheName = cacheName;
      recoveryEnabled = configuration.transaction().recovery().enabled();
      //in distributed mode with write skew check, we only allow 2 phases!!
      this.onePhaseTotalOrder = configuration.transaction().transactionProtocol().isTotalOrder() &&
            !(configuration.clustering().cacheMode().isDistributed() && configuration.locking().writeSkewCheck());
   }
   public TransactionXaAdapter(TransactionTable txTable,
                               RecoveryManager rm, TransactionCoordinator txCoordinator,
                               CommandsFactory commandsFactory, RpcManager rpcManager,
                               ClusteringDependentLogic clusteringDependentLogic,
                               Configuration configuration, String cacheName) {
      super(commandsFactory, rpcManager, txTable, clusteringDependentLogic, configuration, txCoordinator);
      localTransaction = null;
      this.txTable = (XaTransactionTable) txTable;
      this.recoveryManager = rm;
      this.cacheName = cacheName;
      recoveryEnabled = configuration.transaction().recovery().enabled();
      //in distributed mode, we only allow 2 phases!!
      this.onePhaseTotalOrder = configuration.transaction().transactionProtocol().isTotalOrder() &&
            !configuration.clustering().cacheMode().isDistributed();
   }

   /**
    * This can be call for any transaction object. See Section 3.4.6 (Resource Sharing) from JTA spec v1.1.
    */
   @Override
   public int prepare(Xid externalXid) throws XAException {
      Xid xid = convertXid(externalXid);
      LocalXaTransaction localTransaction = getLocalTransactionAndValidate(xid);
      return txCoordinator.prepare(localTransaction);
   }

   /**
    * Same comment as for {@link #prepare(javax.transaction.xa.Xid)} applies for commit.
    */
   @Override
   public void commit(Xid externalXid, boolean isOnePhase) throws XAException {
      Xid xid = convertXid(externalXid);
      LocalXaTransaction localTransaction = getLocalTransactionAndValidate(xid);
      boolean committedInOnePhase;
      if (isOnePhase && onePhaseTotalOrder) {
         committedInOnePhase = txCoordinator.commit(localTransaction, true);
      } else if (isOnePhase) {
         //isOnePhase being true means that we're the only participant in the distributed transaction and TM does the
         //1PC optimization. We run a 2PC though, as running only 1PC has a high chance of leaving the cluster in
         //inconsistent state.
         txCoordinator.prepare(localTransaction);
         committedInOnePhase = txCoordinator.commit(localTransaction, false);
      } else {
         committedInOnePhase = txCoordinator.commit(localTransaction, false);
      }
      forgetSuccessfullyCompletedTransaction(recoveryManager, xid, localTransaction, committedInOnePhase);
   }

   /**
    * Same comment as for {@link #prepare(javax.transaction.xa.Xid)} applies for commit.
    */   
   @Override
   public void rollback(Xid externalXid) throws XAException {
      Xid xid = convertXid(externalXid);
      LocalXaTransaction localTransaction1 = getLocalTransactionAndValidateImpl(xid, txTable);
      localTransaction.markForRollback(true); //ISPN-879 : make sure that locks are no longer associated to this transactions
      txCoordinator.rollback(localTransaction1);
   }

   @Override
   public void start(Xid externalXid, int i) throws XAException {
      Xid xid = convertXid(externalXid);
      //transform in our internal format in order to be able to serialize
      localTransaction.setXid(xid);
      txTable.addLocalTransactionMapping(localTransaction);
      if (trace) log.tracef("start called on tx %s", this.localTransaction.getGlobalTransaction());
   }

   @Override
   public void end(Xid externalXid, int i) throws XAException {
      if (trace) log.tracef("end called on tx %s(%s)", this.localTransaction.getGlobalTransaction(), cacheName);
   }

   @Override
   public void forget(Xid externalXid) throws XAException {
      Xid xid = convertXid(externalXid);
      if (trace) log.tracef("forget called for xid %s", xid);
      try {
         if (recoveryEnabled) {
            recoveryManager.removeRecoveryInformationFromCluster(null, xid, true, null);
         } else {
            if (trace) log.trace("Recovery not enabled");
         }
      } catch (Exception e) {
         log.warnExceptionRemovingRecovery(e);
         XAException xe = new XAException(XAException.XAER_RMERR);
         xe.initCause(e);
         throw xe;
      }
   }

   @Override
   public int getTransactionTimeout() throws XAException {
      if (trace) log.trace("start called");
      return txTimeout;
   }

   /**
    * the only situation in which it returns true is when the other xa resource pertains to the same cache, on
    * the same node.
    */
   @Override
   public boolean isSameRM(XAResource xaResource) throws XAException {
      if (!(xaResource instanceof TransactionXaAdapter)) {
         return false;
      }
      TransactionXaAdapter other = (TransactionXaAdapter) xaResource;
      //there is only one tx table per cache and this is more efficient that equals.
      return this.txTable == other.txTable;
   }

   @Override
   public Xid[] recover(int flag) throws XAException {
      if (!recoveryEnabled) {
         log.recoveryIgnored();
         return RecoveryManager.RecoveryIterator.NOTHING;
      }
      if (trace) log.trace("recover called: " + flag);

      if (isFlag(flag, TMSTARTRSCAN)) {
         recoveryIterator = recoveryManager.getPreparedTransactionsFromCluster();
         if (trace) log.tracef("Fetched a new recovery iterator: %s" , recoveryIterator);
      }
      if (isFlag(flag, TMENDRSCAN)) {
         if (trace) log.trace("Flushing the iterator");
         return recoveryIterator.all();
      } else {
         //as per the spec: "TMNOFLAGS this flag must be used when no other flags are specified."
         if (!isFlag(flag, TMSTARTRSCAN) && !isFlag(flag, TMNOFLAGS))
            throw new IllegalArgumentException("TMNOFLAGS this flag must be used when no other flags are specified." +
                                                     " Received " + flag);
         return recoveryIterator.hasNext() ? recoveryIterator.next() : RecoveryManager.RecoveryIterator.NOTHING;
      }
   }

   private boolean isFlag(int value, int flag) {
      return (value & flag) != 0;
   }

   @Override
   public boolean setTransactionTimeout(int i) throws XAException {
      this.txTimeout = i;
      return true;
   }

   @Override
   public String toString() {
      return "TransactionXaAdapter{" +
            "localTransaction=" + localTransaction +
            '}';
   }

   private void forgetSuccessfullyCompletedTransaction(RecoveryManager recoveryManager, Xid xid, LocalXaTransaction localTransaction, boolean committedInOnePhase) {
      final GlobalTransaction gtx = localTransaction.getGlobalTransaction();
      if (recoveryEnabled) {
         recoveryManager.removeRecoveryInformationFromCluster(localTransaction.getRemoteLocksAcquired(), xid, false, gtx);
         txTable.removeLocalTransaction(localTransaction);
      } else {
         releaseLocksForCompletedTransaction(localTransaction, committedInOnePhase);
      }
   }

   private LocalXaTransaction getLocalTransactionAndValidate(Xid xid) throws XAException {
      return getLocalTransactionAndValidateImpl(xid, txTable);
   }

   private static LocalXaTransaction getLocalTransactionAndValidateImpl(Xid xid, XaTransactionTable txTable) throws XAException {
      LocalXaTransaction localTransaction = txTable.getLocalTransaction(xid);
      if  (localTransaction == null) {
         if (trace) log.tracef("no tx found for %s", xid);
         throw new XAException(XAException.XAER_NOTA);
      }
      return localTransaction;
   }

   public LocalXaTransaction getLocalTransaction() {
      return localTransaction;
   }

   /**
    * Only does the conversion if recovery is enabled.
    */
   private Xid convertXid(Xid externalXid) {
      if (recoveryEnabled && (!(externalXid instanceof SerializableXid))) {
         return new SerializableXid(externalXid);
      } else {
         return externalXid;
      }
   }

   @Override
   public boolean equals(Object o) {
      if (this == o) return true;
      if (o == null || getClass() != o.getClass()) return false;

      TransactionXaAdapter that = (TransactionXaAdapter) o;

      if (localTransaction != null ? !localTransaction.equals(that.localTransaction) : that.localTransaction != null)
         return false;
      //also include the name of the cache in comparison - needed when same tx spans multiple caches.
      return cacheName != null ?
            cacheName.equals(that.cacheName) : that.cacheName == null;
   }
}


File: core/src/main/java/org/infinispan/transaction/xa/XaTransactionTable.java
package org.infinispan.transaction.xa;

import org.infinispan.Cache;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.util.CollectionFactory;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.factories.annotations.Start;
import org.infinispan.transaction.impl.LocalTransaction;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.xa.recovery.RecoveryManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.Transaction;
import javax.transaction.xa.XAException;
import javax.transaction.xa.Xid;

import java.util.concurrent.ConcurrentMap;

/**
 * {@link TransactionTable} to be used with {@link TransactionXaAdapter}.
 *
 * @author Mircea.Markus@jboss.com
 * @since 5.0
 */
public class XaTransactionTable extends TransactionTable {

   private static final Log log = LogFactory.getLog(XaTransactionTable.class);

   protected ConcurrentMap<Xid, LocalXaTransaction> xid2LocalTx;
   private RecoveryManager recoveryManager;
   private String cacheName;

   @Inject
   public void init(RecoveryManager recoveryManager, Cache cache) {
      this.recoveryManager = recoveryManager;
      this.cacheName = cache.getName();
   }

   @Start(priority = 9) // Start before cache loader manager
   @SuppressWarnings("unused")
   public void startXidMapping() {
      final int concurrencyLevel = configuration.locking().concurrencyLevel();
      xid2LocalTx = CollectionFactory.makeConcurrentMap(concurrencyLevel, 0.75f, concurrencyLevel);
   }

   @Override
   public boolean removeLocalTransaction(LocalTransaction localTx) {
      boolean result = false;
      if (localTx.getTransaction() != null) {//this can be null when we force the invocation during recovery, perhaps on a remote node
         result = super.removeLocalTransaction(localTx);
      }
      removeXidTxMapping((LocalXaTransaction) localTx);
      return result;
   }

   private void removeXidTxMapping(LocalXaTransaction localTx) {
      final Xid xid = localTx.getXid();
      xid2LocalTx.remove(xid);
   }

   public LocalXaTransaction getLocalTransaction(Xid xid) {
      return this.xid2LocalTx.get(xid);
   }

   public void addLocalTransactionMapping(LocalXaTransaction localTransaction) {
      if (localTransaction.getXid() == null) throw new IllegalStateException("Initialize xid first!");
      this.xid2LocalTx.put(localTransaction.getXid(), localTransaction);
   }

   @Override
   public void enlist(Transaction transaction, LocalTransaction ltx) {
      LocalXaTransaction localTransaction = (LocalXaTransaction) ltx;
      if (!localTransaction.isEnlisted()) { //make sure that you only enlist it once
         try {
            transaction.enlistResource(new TransactionXaAdapter(
                  localTransaction, this, recoveryManager,
                  txCoordinator, commandsFactory, rpcManager,
                  clusteringLogic, configuration, cacheName));
         } catch (Exception e) {
            Xid xid = localTransaction.getXid();
            if (xid != null && !localTransaction.getLookedUpEntries().isEmpty()) {
               log.debug("Attempting a rollback to clear stale resources!");
               try {
                  txCoordinator.rollback(localTransaction);
               } catch (XAException xae) {
                  log.debug("Caught exception attempting to clean up " + xid, xae);
               }
            }
            log.failedToEnlistTransactionXaAdapter(e);
            throw new CacheException(e);
         }
      }
   }

   public RecoveryManager getRecoveryManager() {
      return recoveryManager;
   }

   public void setRecoveryManager(RecoveryManager recoveryManager) {
      this.recoveryManager = recoveryManager;
   }

   @Override
   public int getLocalTxCount() {
      return xid2LocalTx.size();
   }
}


File: core/src/main/java/org/infinispan/transaction/xa/recovery/RecoveryAdminOperations.java
package org.infinispan.transaction.xa.recovery;

import org.infinispan.factories.annotations.Inject;
import org.infinispan.jmx.annotations.MBean;
import org.infinispan.jmx.annotations.ManagedOperation;
import org.infinispan.jmx.annotations.Parameter;
import org.infinispan.remoting.transport.Address;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.Status;
import javax.transaction.xa.Xid;
import java.util.Set;

/**
 * Admin utility class for allowing management of in-doubt transactions (e.g. transactions for which the
 * originator node crashed after prepare).
 *
 * @author Mircea Markus
 * @since 5.0
 */
@MBean(objectName = "RecoveryAdmin", description = "Exposes tooling for handling transaction recovery.")
public class RecoveryAdminOperations {

   private static final Log log = LogFactory.getLog(RecoveryAdminOperations.class);

   public static final String SEPARATOR = ", ";

   private RecoveryManager recoveryManager;

   @Inject
   public void init(RecoveryManager recoveryManager) {
      this.recoveryManager = recoveryManager;
   }

   @ManagedOperation(description = "Shows all the prepared transactions for which the originating node crashed", displayName="Show in doubt transactions")
   public String showInDoubtTransactions() {
      Set<RecoveryManager.InDoubtTxInfo> info = getRecoveryInfoFromCluster();
      if (log.isTraceEnabled()) {
         log.tracef("Found in doubt transactions: %s", info.size());
      }
      StringBuilder result = new StringBuilder();
      for (RecoveryManager.InDoubtTxInfo i : info) {
         result.append("xid = [").append(i.getXid()).append("], ").append(SEPARATOR)
               .append("internalId = ").append(i.getInternalId()).append(SEPARATOR);
         result.append("status = [ ");
         for (Integer status : i.getStatus()) {
            if (status == Status.STATUS_PREPARED) {
               result.append("_PREPARED_");
            } else if (status == Status.STATUS_COMMITTED) {
               result.append("_COMMITTED_");
            } else if (status == Status.STATUS_ROLLEDBACK) {
               result.append("_ROLLEDBACK_");
            }
         }
         result.append(" ]");
         result.append('\n');
      }
      return result.toString();
   }

   @ManagedOperation(description = "Forces the commit of an in-doubt transaction", displayName="Force commit by internal id")
   public String forceCommit(@Parameter(name = "internalId", description = "The internal identifier of the transaction") long internalId) {
      if (log.isTraceEnabled())
         log.tracef("Forces the commit of an in-doubt transaction: %s", internalId);
      return completeBasedOnInternalId(internalId, true);
   }

   @ManagedOperation(description = "Forces the commit of an in-doubt transaction", displayName="Force commit by Xid", name="forceCommit")
   public String forceCommit(
         @Parameter(name = "formatId", description = "The formatId of the transaction") int formatId,
         @Parameter(name = "globalTxId", description = "The globalTxId of the transaction") byte[] globalTxId,
         @Parameter(name = "branchQualifier", description = "The branchQualifier of the transaction") byte[] branchQualifier) {
      return completeBasedOnXid(formatId, globalTxId, branchQualifier, true);
   }

   @ManagedOperation(description = "Forces the rollback of an in-doubt transaction", displayName="Force rollback by internal id")
   public String forceRollback(@Parameter(name = "internalId", description = "The internal identifier of the transaction") long internalId) {
      return completeBasedOnInternalId(internalId, false);
   }

   @ManagedOperation(description = "Forces the rollback of an in-doubt transaction", displayName="Force rollback by Xid", name="forceRollback")
   public String forceRollback(
         @Parameter(name = "formatId", description = "The formatId of the transaction") int formatId,
         @Parameter(name = "globalTxId", description = "The globalTxId of the transaction") byte[] globalTxId,
         @Parameter(name = "branchQualifier", description = "The branchQualifier of the transaction") byte[] branchQualifier) {
      return completeBasedOnXid(formatId, globalTxId, branchQualifier, false);
   }

   @ManagedOperation(description = "Removes recovery info for the given transaction.", displayName="Remove recovery info by Xid", name="forget")
   public String forget(
         @Parameter(name = "formatId", description = "The formatId of the transaction") int formatId,
         @Parameter(name = "globalTxId", description = "The globalTxId of the transaction") byte[] globalTxId,
         @Parameter(name = "branchQualifier", description = "The branchQualifier of the transaction") byte[] branchQualifier) {
      recoveryManager.removeRecoveryInformationFromCluster(null, new SerializableXid(branchQualifier, globalTxId, formatId), true, null);
      return "Recovery info removed.";
   }

   @ManagedOperation(description = "Removes recovery info for the given transaction.", displayName="Remove recovery info by internal id")
   public String forget(@Parameter(name = "internalId", description = "The internal identifier of the transaction") long internalId) {
      recoveryManager.removeRecoveryInformationFromCluster(null, internalId, true);
      return "Recovery info removed.";
   }


   private String completeBasedOnXid(int formatId, byte[] globalTxId, byte[] branchQualifier, boolean commit) {
      RecoveryManager.InDoubtTxInfo inDoubtTxInfo = lookupRecoveryInfo(formatId, globalTxId, branchQualifier);
      if (inDoubtTxInfo != null) {
         return completeTransaction(inDoubtTxInfo.getXid(), inDoubtTxInfo, commit);
      } else {
         return transactionNotFound(formatId, globalTxId, branchQualifier);
      }
   }

   private String completeBasedOnInternalId(Long internalId, boolean commit) {
      RecoveryManager.InDoubtTxInfo inDoubtTxInfo = lookupRecoveryInfo(internalId);
      if (inDoubtTxInfo != null) {
         return completeTransaction(inDoubtTxInfo.getXid(), inDoubtTxInfo, commit);
      } else {
         return transactionNotFound(internalId);
      }
   }

   private String completeTransaction(Xid xid, RecoveryManager.InDoubtTxInfo i, boolean commit) {
      //try to run it locally at first
      if (i.isLocal()) {
         log.tracef("Forcing completion of local transaction: %s", i);
         return recoveryManager.forceTransactionCompletion(xid, commit);
      } else {
         log.tracef("Forcing completion of remote transaction: %s", i);
         Set<Address> owners = i.getOwners();
         if (owners == null || owners.isEmpty()) throw new IllegalStateException("Owner list cannot be empty for " + i);
         return recoveryManager.forceTransactionCompletionFromCluster(xid, owners.iterator().next(), commit);
      }
   }

   private  RecoveryManager.InDoubtTxInfo lookupRecoveryInfo(int formatId, byte[] globalTxId, byte[] branchQualifier) {
      Set<RecoveryManager.InDoubtTxInfo> info = getRecoveryInfoFromCluster();
      SerializableXid xid = new SerializableXid(branchQualifier, globalTxId, formatId);
      for (RecoveryManager.InDoubtTxInfo i : info) {
         if (i.getXid().equals(xid)) {
            log.tracef("Found matching recovery info: %s", i);
            return i;
         }
      }
      return null;
   }

   private Set<RecoveryManager.InDoubtTxInfo> getRecoveryInfoFromCluster() {
      Set<RecoveryManager.InDoubtTxInfo> info = recoveryManager.getInDoubtTransactionInfoFromCluster();
      log.tracef("Recovery info from cluster is: %s", info);
      return info;
   }

   private RecoveryManager.InDoubtTxInfo lookupRecoveryInfo(Long internalId) {
      Set<RecoveryManager.InDoubtTxInfo> info = getRecoveryInfoFromCluster();
      for (RecoveryManager.InDoubtTxInfo i : info) {
         if (i.getInternalId().equals(internalId)) {
            log.tracef("Found matching recovery info: %s", i);
            return i;
         }
      }
      return null;
   }

   private String transactionNotFound(int formatId, byte[] globalTxId, byte[] branchQualifier) {
      return "Transaction not found: " + new SerializableXid(branchQualifier, globalTxId, formatId);
   }

   private String transactionNotFound(Long internalId) {
      return "Transaction not found for internal id: " + internalId;
   }
}


File: core/src/main/java/org/infinispan/transaction/xa/recovery/RecoveryManager.java
package org.infinispan.transaction.xa.recovery;

import org.infinispan.remoting.transport.Address;
import org.infinispan.transaction.xa.GlobalTransaction;

import javax.transaction.xa.Xid;
import java.util.Collection;
import java.util.Iterator;
import java.util.List;
import java.util.Set;

/**
 * RecoveryManager is the component responsible with managing recovery related information and the functionality
 * associated with it. Refer to <a href="http://community.jboss.org/wiki/Transactionrecoverydesign">this</a> document
 * for details on the design of recovery.
 *
 * @author Mircea.Markus@jboss.com
 * @since 5.0
 */
public interface RecoveryManager {

   /**
    * Returns the list of transactions in prepared state from both local and remote cluster nodes.
    * Implementation can take advantage of several optimisations:
    * <pre>
    * - in order to get all tx from the cluster a broadcast is performed. This can be performed only once (assuming the call
    *   is successful), the first time this method is called. After that a local, cached list of tx prepared on this node is returned.
    * - during the broadcast just return the list of prepared transactions that are not originated on other active nodes of the
    * cluster.
    * </pre>
    */
   RecoveryIterator getPreparedTransactionsFromCluster();

   /**
    * Returns a {@link Set} containing all the in-doubt transactions from the cluster, including the local node. This does
    * not include transactions that are prepared successfully and for which the originator is still in the cluster.
    * @see InDoubtTxInfo
    */
   Set<InDoubtTxInfo> getInDoubtTransactionInfoFromCluster();

   /**
    * Same as {@link #getInDoubtTransactionInfoFromCluster()}, but only returns transactions from the local node.
    */
   Set<InDoubtTxInfo> getInDoubtTransactionInfo();


   /**
    * Removes from the specified nodes (or all nodes if the value of 'where' is null) the recovery information associated with
    * these Xids.
    * @param where on which nodes should this be executed.
    * @param xid the list of xids to be removed.
    * @param sync execute sync or async (false)
    * @param gtx
    */
   void removeRecoveryInformationFromCluster(Collection<Address> where, Xid xid, boolean sync, GlobalTransaction gtx);

   /**
    * Same as {@link #removeRecoveryInformationFromCluster(java.util.Collection} but the transaction
    * is identified by its internal id, and not by its xid.
    */
   void removeRecoveryInformationFromCluster(Collection<Address> where, long internalId, boolean sync);

   /**
    * Local call that returns a list containing:
    * <pre>
    * - all the remote transactions prepared on this node for which the originator(i.e. the node where the tx
    * stared) is no longer part of the cluster.
    * AND
    * - all the locally originated transactions which are prepared and for which the commit failed
    * </pre>
    *
    * @see RecoveryAwareRemoteTransaction#isInDoubt()
    */
   List<Xid> getInDoubtTransactions();

   /**
    * Local call returning the remote transaction identified by the supplied xid or null.
    */
   RecoveryAwareTransaction getPreparedTransaction(Xid xid);

   /**
    * Replays the given transaction by re-running the prepare and commit. This call expects the transaction to exist on
    * this node either as a local or remote transaction.
    * @param xid tx to commit or rollback
    * @param commit if true tx is committed, if false it is rolled back
    */
   String forceTransactionCompletion(Xid xid, boolean commit);

   /**
    * This method invokes {@link #forceTransactionCompletion(javax.transaction.xa.Xid, boolean)} on the specified node.
    */
   String forceTransactionCompletionFromCluster(Xid xid, Address where, boolean commit);

   /**
    * Checks both internal state and transaction table's state for the given tx. If it finds it, returns true if tx
    * is prepared.
    */
   boolean isTransactionPrepared(GlobalTransaction globalTx);

   /**
    * Same as {@link #removeRecoveryInformation(javax.transaction.xa.Xid)} but identifies the tx by its internal id.
    */
   RecoveryAwareTransaction removeRecoveryInformation(Long internalId);

   /**
    * Remove recovery information stored on this node (doesn't involve rpc).
    *
    * @param xid@see  #removeRecoveryInformation(java.util.Collection, javax.transaction.xa.Xid, boolean)
    */
   RecoveryAwareTransaction removeRecoveryInformation(Xid xid);

   /**
   * Stateful structure allowing prepared-tx retrieval in a batch-oriented manner,
    * as required by {@link javax.transaction.xa.XAResource#recover(int)}.
   */
   interface RecoveryIterator extends Iterator<Xid[]> {

      Xid[] NOTHING = new Xid[]{};

      /**
       * Exhaust the iterator. After this call, {@link #hasNext()} returns false.
       */
      Xid[] all();
   }

   /**
    * An object describing in doubt transaction's state. Needed by the transaction recovery process, for displaying
    * transactions to the user.
    */
   interface InDoubtTxInfo {

      /**
       * Transaction's id.
       */
      Xid getXid();

      /**
       * Each xid has a unique long object associated to it. It makes possible the invocation of recovery operations.
       */
      Long getInternalId();

      /**
       * The value represent transaction's state as described by the {@link Status} field. Multiple values are returned
       * as it is possible for an in-doubt transaction to be at the same time e.g. prepared on one node and committed on the other.
       */
      Set<Integer> getStatus();

      /**
       * Returns the set of nodes where this transaction information is maintained.
       */
      Set<Address> getOwners();

      /**
       * Returns true if the transaction information is also present on this node.
       */
      boolean isLocal();
   }
}


File: core/src/main/java/org/infinispan/transaction/xa/recovery/RecoveryManagerImpl.java
package org.infinispan.transaction.xa.recovery;

import org.infinispan.commands.CommandsFactory;
import org.infinispan.commands.remote.recovery.CompleteTransactionCommand;
import org.infinispan.commands.remote.recovery.GetInDoubtTransactionsCommand;
import org.infinispan.commands.remote.recovery.GetInDoubtTxInfoCommand;
import org.infinispan.commands.remote.recovery.TxCompletionNotificationCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.remoting.inboundhandler.DeliverOrder;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.responses.SuccessfulResponse;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.transport.Address;
import org.infinispan.transaction.impl.LocalTransaction;
import org.infinispan.transaction.impl.TransactionCoordinator;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.transaction.xa.LocalXaTransaction;
import org.infinispan.transaction.xa.TransactionFactory;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import javax.transaction.xa.XAException;
import javax.transaction.xa.Xid;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentMap;

/**
 * Default implementation for {@link RecoveryManager}
 *
 * @author Mircea.Markus@jboss.com
 * @since 5.0
 */
public class RecoveryManagerImpl implements RecoveryManager {

   private static final Log log = LogFactory.getLog(RecoveryManagerImpl.class);

   private volatile RpcManager rpcManager;
   private volatile CommandsFactory commandFactory;

   /**
    * This relies on XIDs for different TMs being unique. E.g. for JBossTM this is correct as long as we have the right
    * config for <IP,port/process,sequence number>. This is expected to stand true for all major TM on the market.
    */
   private final ConcurrentMap<RecoveryInfoKey, RecoveryAwareRemoteTransaction> inDoubtTransactions;

   private final String cacheName;


   private volatile RecoveryAwareTransactionTable txTable;

   private TransactionCoordinator txCoordinator;

   private TransactionFactory txFactory;
   /**
    * we only broadcast the first time when node is started, then we just return the local cached prepared
    * transactions.
    */
   private volatile boolean broadcastForPreparedTx = true;

   public RecoveryManagerImpl(ConcurrentMap<RecoveryInfoKey, RecoveryAwareRemoteTransaction> recoveryHolder, String cacheName) {
      this.inDoubtTransactions = recoveryHolder;
      this.cacheName = cacheName;
   }

   @Inject
   public void init(RpcManager rpcManager, CommandsFactory commandsFactory, TransactionTable txTable,
                    TransactionCoordinator txCoordinator, TransactionFactory txFactory) {
      this.rpcManager = rpcManager;
      this.commandFactory = commandsFactory;
      this.txTable = (RecoveryAwareTransactionTable)txTable;
      this.txCoordinator = txCoordinator;
      this.txFactory = txFactory;
   }

   @Override
   public RecoveryIterator getPreparedTransactionsFromCluster() {
      PreparedTxIterator iterator = new PreparedTxIterator();

      //1. get local transactions first
      //add the locally prepared transactions. The list of prepared transactions (even if they are not in-doubt)
      //is mandated by the recovery process according to the JTA spec: "The transaction manager calls this [i.e. recover]
      // method during recovery to obtain the list of transaction branches that are currently in prepared or heuristically
      // completed states."
      iterator.add(txTable.getLocalPreparedXids());

      //2. now also add the in-doubt transactions.
      iterator.add(getInDoubtTransactions());

      //3. then the remote ones
      if (notOnlyMeInTheCluster() && broadcastForPreparedTx) {
         boolean success = true;
         Map<Address, Response> responses = getAllPreparedTxFromCluster();
         for (Map.Entry<Address, Response> rEntry : responses.entrySet()) {
            Response thisResponse = rEntry.getValue();
            if (isSuccessful(thisResponse)) {
               List<Xid> responseValue = (List<Xid>) ((SuccessfulResponse) thisResponse).getResponseValue();
               if (log.isTraceEnabled()) {
                  log.tracef("Received Xid lists %s from node %s", responseValue, rEntry.getKey());
               }
               iterator.add(responseValue);
            } else {
               log.missingListPreparedTransactions(rEntry.getKey(), rEntry.getValue());
               success = false;
            }
         }
         //this makes sure that the broadcast only happens once!
         this.broadcastForPreparedTx = !success;
         if (!broadcastForPreparedTx)
            log.debug("Finished broadcasting for remote prepared transactions. Returning only local values from now on.");
      }
      return iterator;
   }

   @Override
   public void removeRecoveryInformationFromCluster(Collection<Address> lockOwners, Xid xid, boolean sync, GlobalTransaction gtx) {
      log.tracef("Forgetting tx information for %s", gtx);
      //todo make sure this gets broad casted or at least flushed
      if (rpcManager != null) {
         TxCompletionNotificationCommand ftc = commandFactory.buildTxCompletionNotificationCommand(xid, gtx);
         rpcManager.invokeRemotely(lockOwners, ftc, rpcManager.getDefaultRpcOptions(sync, DeliverOrder.NONE));
      }
      removeRecoveryInformation(xid);
   }

   @Override
   public void removeRecoveryInformationFromCluster(Collection<Address> where, long internalId, boolean sync) {
      if (rpcManager != null) {
         TxCompletionNotificationCommand ftc = commandFactory.buildTxCompletionNotificationCommand(internalId);
         rpcManager.invokeRemotely(where, ftc, rpcManager.getDefaultRpcOptions(sync, DeliverOrder.NONE));
      }
      removeRecoveryInformation(internalId);
   }

   @Override
   public RecoveryAwareTransaction removeRecoveryInformation(Xid xid) {
      RecoveryAwareTransaction remove = inDoubtTransactions.remove(new RecoveryInfoKey(xid, cacheName));
      log.tracef("removed in doubt xid: %s", xid);
      if (remove == null) {
         return (RecoveryAwareTransaction) txTable.removeRemoteTransaction(xid);
      }
      return remove;
   }

   @Override
   public RecoveryAwareTransaction removeRecoveryInformation(Long internalId) {
      Xid remoteTransactionXid = txTable.getRemoteTransactionXid(internalId);
      if (remoteTransactionXid != null) {
         return removeRecoveryInformation(remoteTransactionXid);
      } else {
         for (RecoveryAwareRemoteTransaction raRemoteTx : inDoubtTransactions.values()) {
            RecoverableTransactionIdentifier globalTransaction = (RecoverableTransactionIdentifier) raRemoteTx.getGlobalTransaction();
            if (internalId.equals(globalTransaction.getInternalId())) {
               Xid xid = globalTransaction.getXid();
               log.tracef("Found transaction xid %s that maps internal id %s", xid, internalId);
               removeRecoveryInformation(xid);
               return raRemoteTx;
            }
         }
      }
      log.tracef("Could not find tx to map to internal id %s", internalId);
      return null;
   }

   @Override
   public List<Xid> getInDoubtTransactions() {
      List<Xid> result = new ArrayList<Xid>();
      Set<RecoveryInfoKey> recoveryInfoKeys = inDoubtTransactions.keySet();
      for (RecoveryInfoKey key : recoveryInfoKeys) {
         if (key.cacheName.equals(cacheName))
            result.add(key.xid);
      }
      log.tracef("Returning %s ", result);
      return result;
   }

   @Override
   public Set<InDoubtTxInfo> getInDoubtTransactionInfo() {
      List<Xid> txs = getInDoubtTransactions();
      Set<RecoveryAwareLocalTransaction> localTxs = txTable.getLocalTxThatFailedToComplete();
      log.tracef("Local transactions that failed to complete is %s", localTxs);
      Set<InDoubtTxInfo> result = new HashSet<InDoubtTxInfo>();
      for (RecoveryAwareLocalTransaction r : localTxs) {
         long internalId = ((RecoverableTransactionIdentifier) r.getGlobalTransaction()).getInternalId();
         result.add(new InDoubtTxInfoImpl(r.getXid(), internalId));
      }
      for (Xid xid : txs) {
         RecoveryAwareRemoteTransaction pTx = getPreparedTransaction(xid);
         if (pTx == null) continue; //might be removed concurrently, 2check for null
         RecoverableTransactionIdentifier gtx = (RecoverableTransactionIdentifier) pTx.getGlobalTransaction();
         InDoubtTxInfoImpl infoInDoubt = new InDoubtTxInfoImpl(xid, gtx.getInternalId(), pTx.getStatus());
         result.add(infoInDoubt);
      }
      log.tracef("The set of in-doubt txs from this node is %s", result);
      return result;
   }

   @Override
   public Set<InDoubtTxInfo> getInDoubtTransactionInfoFromCluster() {
      Map<Xid, InDoubtTxInfoImpl> result = new HashMap<Xid, InDoubtTxInfoImpl>();
      if (rpcManager != null) {
         GetInDoubtTxInfoCommand inDoubtTxInfoCommand = commandFactory.buildGetInDoubtTxInfoCommand();
         Map<Address, Response> addressResponseMap = rpcManager.invokeRemotely(null, inDoubtTxInfoCommand,
                                                                               rpcManager.getDefaultRpcOptions(true));
         for (Map.Entry<Address, Response> re : addressResponseMap.entrySet()) {
            Response r = re.getValue();
            if (!isSuccessful(r)) {
               throw new CacheException("Could not fetch in doubt transactions: " + r);
            }
            Set<InDoubtTxInfoImpl> infoInDoubtSet = (Set<InDoubtTxInfoImpl>) ((SuccessfulResponse) r).getResponseValue();
            for (InDoubtTxInfoImpl infoInDoubt : infoInDoubtSet) {
               InDoubtTxInfoImpl inDoubtTxInfo = result.get(infoInDoubt.getXid());
               if (inDoubtTxInfo == null) {
                  inDoubtTxInfo = infoInDoubt;
                  result.put(infoInDoubt.getXid(), inDoubtTxInfo);
               } else {
                  inDoubtTxInfo.addStatus(infoInDoubt.getStatus());
               }
               inDoubtTxInfo.addOwner(re.getKey());
            }
         }
      }
      Set<InDoubtTxInfo> onThisNode = getInDoubtTransactionInfo();
      Iterator<InDoubtTxInfo> iterator = onThisNode.iterator();
      while (iterator.hasNext()) {
         InDoubtTxInfo info = iterator.next();
         InDoubtTxInfoImpl inDoubtTxInfo = result.get(info.getXid());
         if (inDoubtTxInfo != null) {
            inDoubtTxInfo.setLocal(true);
            iterator.remove();
         } else {
            ((InDoubtTxInfoImpl)info).setLocal(true);
         }
      }
      HashSet<InDoubtTxInfo> value = new HashSet<InDoubtTxInfo>(result.values());
      value.addAll(onThisNode);
      return value;
   }

   public void registerInDoubtTransaction(RecoveryAwareRemoteTransaction remoteTransaction) {
      Xid xid = ((RecoverableTransactionIdentifier)remoteTransaction.getGlobalTransaction()).getXid();
      RecoveryAwareTransaction previous = inDoubtTransactions.put(new RecoveryInfoKey(xid, cacheName), remoteTransaction);
      if (previous != null) {
         log.preparedTxAlreadyExists(previous, remoteTransaction);
         throw new IllegalStateException("Are there two different transactions having same Xid in the cluster?");
      }
   }


   @Override
   public RecoveryAwareRemoteTransaction getPreparedTransaction(Xid xid) {
      return inDoubtTransactions.get(new RecoveryInfoKey(xid, cacheName));
   }

   @Override
   public String forceTransactionCompletion(Xid xid, boolean commit) {
      //this means that we have this as a local transaction that originated here
      LocalXaTransaction localTransaction = txTable.getLocalTransaction(xid);
      if (localTransaction != null) {
         localTransaction.clearRemoteLocksAcquired();
         return completeTransaction(localTransaction, commit, xid);
      } else {
         RecoveryAwareRemoteTransaction tx = getPreparedTransaction(xid);
         if (tx == null) return "Could not find transaction " + xid;
         GlobalTransaction globalTransaction = tx.getGlobalTransaction();
         globalTransaction.setAddress(rpcManager.getAddress());
         globalTransaction.setRemote(false);
         RecoveryAwareLocalTransaction localTx = (RecoveryAwareLocalTransaction) txFactory.newLocalTransaction(null, globalTransaction, false, tx.getTopologyId());
         localTx.setModifications(tx.getModifications());
         localTx.setXid(xid);
         localTx.addAllAffectedKeys(tx.getAffectedKeys());
         for (Object lk : tx.getLockedKeys()) localTx.registerLockedKey(lk);
         return completeTransaction(localTx, commit, xid);
      }
   }

   private String completeTransaction(LocalTransaction localTx, boolean commit, Xid xid) {
      if (commit) {
         try {
            localTx.clearLookedUpEntries();
            txCoordinator.prepare(localTx, true);
            txCoordinator.commit(localTx, false);
         } catch (XAException e) {
            log.warnCouldNotCommitLocalTx(localTx, e);
            return "Could not commit transaction " + xid + " : " + e.getMessage();
         }
      } else {
         try {
            txCoordinator.rollback(localTx);
         } catch (XAException e) {
            log.warnCouldNotRollbackLocalTx(localTx, e);
            return "Could not commit transaction " + xid + " : " + e.getMessage();
         }
      }
      removeRecoveryInformationFromCluster(null, xid, false, localTx.getGlobalTransaction());
      return commit ? "Commit successful!" : "Rollback successful";
   }

   @Override
   public String forceTransactionCompletionFromCluster(Xid xid, Address where, boolean commit) {
      CompleteTransactionCommand ctc = commandFactory.buildCompleteTransactionCommand(xid, commit);
      Map<Address, Response> responseMap = rpcManager.invokeRemotely(Collections.singleton(where), ctc, rpcManager.getDefaultRpcOptions(true));
      if (responseMap.size() != 1 || responseMap.get(where) == null) {
         log.expectedJustOneResponse(responseMap);
         throw new CacheException("Expected response size is 1, received " + responseMap);
      }
      return (String) ((SuccessfulResponse) responseMap.get(where)).getResponseValue();
   }

   @Override
   public boolean isTransactionPrepared(GlobalTransaction globalTx) {
      Xid xid = ((RecoverableTransactionIdentifier) globalTx).getXid();
      RecoveryAwareRemoteTransaction remoteTransaction = (RecoveryAwareRemoteTransaction) txTable.getRemoteTransaction(globalTx);
      boolean remotePrepared = remoteTransaction != null && remoteTransaction.isPrepared();
      boolean result = inDoubtTransactions.get(new RecoveryInfoKey(xid, cacheName)) != null //if it is in doubt must be prepared
            || txTable.getLocalPreparedXids().contains(xid) || remotePrepared;
      if (log.isTraceEnabled()) log.tracef("Is tx %s prepared? %s", xid, result);
      return result;
   }

   private boolean isSuccessful(Response thisResponse) {
      return thisResponse != null && thisResponse.isValid() && thisResponse.isSuccessful();
   }

   private boolean notOnlyMeInTheCluster() {
      return rpcManager != null && rpcManager.getTransport().getMembers().size() > 1;
   }

   private Map<Address, Response> getAllPreparedTxFromCluster() {
      GetInDoubtTransactionsCommand command = commandFactory.buildGetInDoubtTransactionsCommand();
      Map<Address, Response> addressResponseMap = rpcManager.invokeRemotely(null, command, rpcManager.getDefaultRpcOptions(true));
      if (log.isTraceEnabled()) log.tracef("getAllPreparedTxFromCluster received from cluster: %s", addressResponseMap);
      return addressResponseMap;
   }

   public ConcurrentMap<RecoveryInfoKey, RecoveryAwareRemoteTransaction> getInDoubtTransactionsMap() {
      return inDoubtTransactions;
   }
}


File: core/src/test/java/org/infinispan/api/ForceWriteLockTest.java
package org.infinispan.api;

import org.infinispan.AdvancedCache;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.container.entries.ReadCommittedEntry;
import org.infinispan.context.Flag;
import org.infinispan.context.InvocationContext;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.SingleCacheManagerTest;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.impl.LocalTransaction;
import org.infinispan.transaction.impl.TransactionCoordinator;
import org.infinispan.transaction.impl.TransactionTable;
import org.testng.annotations.Test;

import javax.transaction.TransactionManager;

import static org.testng.AssertJUnit.assertTrue;

/**
 * @author Mircea.Markus@jboss.com
 */
@Test(groups = "functional", testName = "api.ForceWriteLockTest")
public class ForceWriteLockTest extends SingleCacheManagerTest {
   private TransactionManager tm;
   private AdvancedCache advancedCache;

   @Override
   protected EmbeddedCacheManager createCacheManager() throws Exception {
      ConfigurationBuilder cacheConfiguration = TestCacheManagerFactory.getDefaultCacheConfiguration(true);
      cacheConfiguration.transaction().lockingMode(LockingMode.PESSIMISTIC);
      EmbeddedCacheManager cacheManager = TestCacheManagerFactory.createCacheManager(cacheConfiguration);
      advancedCache = cacheManager.getCache().getAdvancedCache();
      tm = TestingUtil.getTransactionManager(advancedCache);
      return cacheManager;
   }

   public void testWriteLockIsAcquired() throws Exception {
      advancedCache.put("k","v");
      assertNotLocked(advancedCache,"k");
      tm.begin();
      advancedCache.withFlags(Flag.FORCE_WRITE_LOCK).get("k");

      TransactionTable txTable = advancedCache.getComponentRegistry().getComponent(TransactionTable.class);
      LocalTransaction tx = txTable.getLocalTransaction(tm.getTransaction());
      assertTrue(tx.ownsLock("k"));
      assertLocked(advancedCache,"k");

      tm.commit();
      assertNotLocked(advancedCache,"k");
   }
}


File: core/src/test/java/org/infinispan/lock/ExplicitUnlockTest.java
package org.infinispan.lock;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.SingleCacheManagerTest;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.transaction.LockingMode;
import org.infinispan.util.concurrent.locks.LockManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;
import org.testng.annotations.Test;

import javax.transaction.TransactionManager;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.ConcurrentModificationException;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static java.lang.String.valueOf;
import static org.testng.AssertJUnit.assertTrue;

/**
 * Contributed by Dmitry Udalov
 *
 * @author Dmitry Udalov
 * @author Pedro Ruivo
 * @since 6.0
 */
@Test(groups = "functional", testName = "lock.ExplicitUnlockTest")
@CleanupAfterMethod
public class ExplicitUnlockTest extends SingleCacheManagerTest {

   private static final Log log = LogFactory.getLog(ExplicitUnlockTest.class);
   private static final int NUMBER_OF_KEYS = 10;

   public void testLock() throws Exception {
      doTestLock(true, 10, 10);
   }

   public void testLockTwoTasks() throws Exception {
      doTestLock(true, 2, 10);
   }

   public void testLockNoExplicitUnlock() throws Exception {
      doTestLock(false, 10, 10);
   }

   public void testLockNoExplicitUnlockTwoTasks() throws Exception {
      doTestLock(false, 10, 10);
   }

   @Override
   protected EmbeddedCacheManager createCacheManager() throws Exception {
      ConfigurationBuilder builder = getDefaultStandaloneCacheConfig(true);
      builder.transaction().lockingMode(LockingMode.PESSIMISTIC);
      return TestCacheManagerFactory.createCacheManager(builder);
   }

   private void doTestLock(boolean withUnlock, int nThreads, long stepDelayMsec) throws Exception {
      for (int key = 1; key <= NUMBER_OF_KEYS; key++) {
         cache.put("" + key, "value");
      }

      List<Future<Boolean>> results = new ArrayList<Future<Boolean>>(nThreads);

      for (int i = 1; i <= nThreads; i++) {
         results.add(fork(new Worker(i, cache, withUnlock, stepDelayMsec)));
      }

      boolean success = true;
      for (Future<Boolean> next : results) {
         success = success && next.get(30, TimeUnit.SECONDS);
      }
      assertTrue("All worker should complete without exceptions", success);
      assertNoTransactions();
      for (int i = 0; i < NUMBER_OF_KEYS; ++i) {
         assertNotLocked(cache, valueOf(i));
      }
   }

   private static class Worker implements Callable<Boolean> {

      private static String lockKey = "0";     // there is no cached Object with such key
      private final Cache<Object, Object> cache;
      private final boolean withUnlock;
      private final long stepDelayMsec;
      private final int index;

      public Worker(int index, final Cache<Object, Object> cache, boolean withUnlock, long stepDelayMsec) {
         this.index = index;
         this.cache = cache;
         this.withUnlock = withUnlock;
         this.stepDelayMsec = stepDelayMsec;
      }

      @Override
      public Boolean call() throws Exception {
         boolean success;
         try {
            doRun();
            success = true;
         } catch (Throwable t) {
            log.errorf(t, "Error in Worker[%s, unlock? %s]", index, withUnlock);
            success = false;
         }
         return success;
      }

      private void log(String method, String msg) {
         log.debugf("Worker[%s, unlock? %s] %s %s", index, withUnlock, method, msg);
      }

      private void doRun() throws Exception {
         final String methodName = "run";
         TransactionManager mgr = cache.getAdvancedCache().getTransactionManager();
         if (null == mgr) {
            throw new UnsupportedOperationException("TransactionManager was not configured for the cache " + cache.getName());
         }
         mgr.begin();

         try {
            if (acquireLock()) {
               log(methodName, "acquired lock");

               // renaming all Objects from 1 to NUMBER_OF_KEYS
               String newName = "value-" + index;
               log(methodName, "Changing value to " + newName);
               for (int key = 1; key <= NUMBER_OF_KEYS; key++) {
                  cache.put(valueOf(key), newName);
                  Thread.sleep(stepDelayMsec);
               }

               validateCache();

               if (withUnlock) {
                  unlock(lockKey);
               }

            } else {
               log(methodName, "Failed to acquired lock");
            }
            mgr.commit();

         } catch (Exception t) {
            mgr.rollback();
            throw t;
         }
      }

      private boolean acquireLock() {
         return cache.getAdvancedCache().lock(lockKey);
      }

      private boolean unlock(String resourceId) {
         LockManager lockManager = cache.getAdvancedCache().getLockManager();
         Object lockOwner = lockManager.getOwner(resourceId);
         Collection<Object> keys = Collections.<Object>singletonList(resourceId);
         lockManager.unlock(keys, lockOwner);
         return true;
      }

      /**
       * Checks if all cache entries are consistent
       *
       * @throws InterruptedException
       */
      private void validateCache() throws InterruptedException {

         String value = getCachedValue(1);
         for (int key = 1; key <= NUMBER_OF_KEYS; key++) {
            String nextValue = getCachedValue(key);
            if (!value.equals(nextValue)) {
               String msg = String.format("Cache inconsistent: value=%s, nextValue=%s", value, nextValue);
               log("validate_cache", msg);
               throw new ConcurrentModificationException(msg);
            }
            Thread.sleep(stepDelayMsec);
         }
         log("validate_cache", "passed: " + value);
      }

      private String getCachedValue(int index) {
         String value = (String) cache.get(valueOf(index));
         if (null == value) {
            throw new ConcurrentModificationException("Missed entry for " + index);
         }
         return value;
      }
   }


}


File: core/src/test/java/org/infinispan/lock/OptimisticTxFailureAfterLockingTest.java
package org.infinispan.lock;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.cache.VersioningScheme;
import org.infinispan.distribution.MagicKey;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.transaction.LockingMode;
import org.infinispan.util.concurrent.IsolationLevel;
import org.testng.AssertJUnit;
import org.testng.annotations.Test;

import javax.transaction.RollbackException;
import javax.transaction.Transaction;

/**
 * Test the failures after lock acquired for Optimistic transactional caches.
 *
 * @author Pedro Ruivo
 * @since 6.0
 */
@Test(groups = "functional", testName = "lock.OptimisticTxFailureAfterLockingTest")
@CleanupAfterMethod
public class OptimisticTxFailureAfterLockingTest extends MultipleCacheManagersTest {

   /**
    * ISPN-3556
    */
   public void testInOwner() throws Exception {
      //primary owner is cache(0) and the failure is executed in cache(0)
      doTest(0, 0);
   }

   /**
    * ISPN-3556
    */
   public void testInNonOwner() throws Exception {
      //primary owner is cache(1) and the failure is executed in cache(0)
      doTest(1, 0);
   }

   @Override
   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder builder = getDefaultClusteredCacheConfig(CacheMode.DIST_SYNC, true);
      builder.locking()
            .isolationLevel(IsolationLevel.REPEATABLE_READ)
            .writeSkewCheck(true);
      builder.transaction()
            .lockingMode(LockingMode.OPTIMISTIC);
      builder.clustering().hash()
            .numOwners(2);
      builder.versioning()
            .enable()
            .scheme(VersioningScheme.SIMPLE);
      createClusteredCaches(3, builder);
   }

   private void doTest(int primaryOwnerIndex, int execIndex) throws Exception {
      final Object key = new MagicKey(cache(primaryOwnerIndex), cache(2));

      cache(primaryOwnerIndex).put(key, "v1");

      tm(execIndex).begin();
      AssertJUnit.assertEquals("v1", cache(execIndex).get(key));
      final Transaction transaction = tm(execIndex).suspend();

      cache(primaryOwnerIndex).put(key, "v2");

      tm(execIndex).resume(transaction);
      AssertJUnit.assertEquals("v1", cache(execIndex).put(key, "v3"));
      try {
         tm(execIndex).commit();
         AssertJUnit.fail("Exception expected!");
      } catch (RollbackException e) {
         //expected
      }

      assertNoTransactions();
      assertNotLocked(cache(primaryOwnerIndex), key);
   }
}


File: core/src/test/java/org/infinispan/lock/PessimistTxFailureAfterLockingTest.java
package org.infinispan.lock;

import org.infinispan.Cache;
import org.infinispan.commands.ReplicableCommand;
import org.infinispan.commands.control.LockControlCommand;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.distribution.MagicKey;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.transport.Address;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.transaction.LockingMode;
import org.infinispan.util.AbstractControlledRpcManager;
import org.infinispan.util.concurrent.IsolationLevel;
import org.infinispan.util.concurrent.TimeoutException;
import org.testng.annotations.Test;

import java.util.Map;

import static org.testng.AssertJUnit.assertTrue;

/**
 * Test the failures after lock acquired for Pessimistic transactional caches.
 *
 * @author Pedro Ruivo
 * @since 6.0
 */
@Test(groups = "functional", testName = "lock.PessimistTxFailureAfterLockingTest")
@CleanupAfterMethod
public class PessimistTxFailureAfterLockingTest extends MultipleCacheManagersTest {

   /**
    * ISPN-3556
    */
   public void testReplyLostWithImplicitLocking() throws Exception {
      doTest(false);
   }

   /**
    * ISPN-3556
    */
   public void testReplyLostWithExplicitLocking() throws Exception {
      doTest(true);
   }

   private void doTest(boolean explicitLocking) throws Exception {
      final Object key = new MagicKey(cache(1), cache(2));
      replaceRpcManagerInCache(cache(0));

      boolean failed = false;
      tm(0).begin();
      try {
         if (explicitLocking) {
            cache(0).getAdvancedCache().lock(key);
         } else {
            cache(0).put(key, "value");
         }
      } catch (Exception e) {
         failed = true;
         //expected
      }
      tm(0).rollback();

      assertTrue("Expected an exception", failed);
      assertNoTransactions();
      assertNotLocked(cache(1), key);
   }

   @Override
   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder builder = getDefaultClusteredCacheConfig(CacheMode.DIST_SYNC, true);
      builder.locking()
            .isolationLevel(IsolationLevel.READ_COMMITTED); //read committed is enough
      builder.transaction()
            .lockingMode(LockingMode.PESSIMISTIC);
      builder.clustering().hash()
            .numOwners(2);
      createClusteredCaches(3, builder);
   }

   private void replaceRpcManagerInCache(Cache cache) {
      RpcManager rpcManager = TestingUtil.extractComponent(cache, RpcManager.class);
      TestControllerRpcManager testControllerRpcManager = new TestControllerRpcManager(rpcManager);
      TestingUtil.replaceComponent(cache, RpcManager.class, testControllerRpcManager, true);
   }

   /**
    * this RpcManager simulates a reply lost from LockControlCommand by throwing a TimeoutException. However, it is
    * expected the command to acquire the remote lock.
    */
   private class TestControllerRpcManager extends AbstractControlledRpcManager {

      public TestControllerRpcManager(RpcManager realOne) {
         super(realOne);
      }

      @Override
      protected Map<Address, Response> afterInvokeRemotely(ReplicableCommand command, Map<Address, Response> responseMap) {
         if (command instanceof LockControlCommand) {
            throw new TimeoutException("Exception expected!");
         }
         return responseMap;
      }
   }
}


File: core/src/test/java/org/infinispan/lock/StaleEagerLocksOnPrepareFailureTest.java
package org.infinispan.lock;

import org.infinispan.Cache;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.distribution.MagicKey;
import org.infinispan.interceptors.InterceptorChain;
import org.infinispan.interceptors.distribution.TxDistributionInterceptor;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.transaction.LockingMode;
import org.testng.annotations.Test;

import static org.testng.Assert.assertNull;

@Test(testName = "lock.StaleEagerLocksOnPrepareFailureTest", groups = "functional")
@CleanupAfterMethod
public class StaleEagerLocksOnPrepareFailureTest extends MultipleCacheManagersTest {

   Cache<MagicKey, String> c1, c2;

   @Override
   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder cfg = getDefaultClusteredCacheConfig(CacheMode.DIST_SYNC, true);
      cfg
         .transaction()
            .lockingMode(LockingMode.PESSIMISTIC)
            .useSynchronization(false)
            .recovery()
               .disable()
         .locking()
            .lockAcquisitionTimeout(100);
      EmbeddedCacheManager cm1 = TestCacheManagerFactory.createClusteredCacheManager(cfg);
      EmbeddedCacheManager cm2 = TestCacheManagerFactory.createClusteredCacheManager(cfg);
      registerCacheManager(cm1, cm2);
      c1 = cm1.getCache();
      c2 = cm2.getCache();
      waitForClusterToForm();
   }

   public void testNoModsCommit() throws Exception {
      doTest(false);
   }

   public void testModsCommit() throws Exception {
      doTest(true);
   }

   private void doTest(boolean mods) throws Exception {
      // force the prepare command to fail on c2
      FailInterceptor interceptor = new FailInterceptor();
      interceptor.failFor(PrepareCommand.class);
      InterceptorChain ic = TestingUtil.extractComponent(c2, InterceptorChain.class);
      ic.addInterceptorBefore(interceptor, TxDistributionInterceptor.class);

      MagicKey k1 = new MagicKey("k1", c1);
      MagicKey k2 = new MagicKey("k2", c2);

      tm(c1).begin();
      if (mods) {
         c1.put(k1, "v1");
         c1.put(k2, "v2");

         assertKeyLockedCorrectly(k1);
         assertKeyLockedCorrectly(k2);
      } else {
         c1.getAdvancedCache().lock(k1);
         c1.getAdvancedCache().lock(k2);

         assertNull(c1.get(k1));
         assertNull(c1.get(k2));

         assertKeyLockedCorrectly(k1);
         assertKeyLockedCorrectly(k2);
      }

      try {
         tm(c1).commit();
         assert false : "Commit should have failed";
      } catch (Exception e) {
         // expected
      }

      assertNotLocked(c1, k1);
      assertNotLocked(c2, k1);
      assertNotLocked(c1, k2);
      assertNotLocked(c2, k2);
   }
}



File: core/src/test/java/org/infinispan/lock/StaleLocksOnPrepareFailureTest.java
package org.infinispan.lock;

import org.infinispan.Cache;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.distribution.MagicKey;
import org.infinispan.interceptors.InterceptorChain;
import org.infinispan.interceptors.distribution.TxDistributionInterceptor;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.testng.annotations.Test;

@Test(testName = "lock.StaleLocksOnPrepareFailureTest", groups = "functional")
@CleanupAfterMethod
public class StaleLocksOnPrepareFailureTest extends MultipleCacheManagersTest {

   public static final int NUM_CACHES = 10;

   @Override
   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder cfg = getDefaultClusteredCacheConfig(CacheMode.DIST_SYNC, true);
      cfg.clustering().hash().numOwners(NUM_CACHES).locking().lockAcquisitionTimeout(100);
      for (int i = 0; i < NUM_CACHES; i++) {
         EmbeddedCacheManager cm = TestCacheManagerFactory.createClusteredCacheManager(cfg);
         registerCacheManager(cm);
      }
      waitForClusterToForm();
   }

   public void testModsCommit() throws Exception {
      doTest(true);
   }

   private void doTest(boolean mods) throws Exception {
      Cache<Object, Object> c1 = cache(0);
      Cache<Object, Object> c2 = cache(NUM_CACHES /2);

      // force the prepare command to fail on c2
      FailInterceptor interceptor = new FailInterceptor();
      interceptor.failFor(PrepareCommand.class);
      InterceptorChain ic = TestingUtil.extractComponent(c2, InterceptorChain.class);
      ic.addInterceptorBefore(interceptor, TxDistributionInterceptor.class);

      MagicKey k1 = new MagicKey("k1", c1);

      tm(c1).begin();
      c1.put(k1, "v1");

      try {
         tm(c1).commit();
         assert false : "Commit should have failed";
      } catch (Exception e) {
         // expected
      }

      for (int i = 0; i < NUM_CACHES; i++) {
        assertNotLocked(cache(i), k1);
      }
   }
}



File: core/src/test/java/org/infinispan/lock/StaleLocksTransactionTest.java
package org.infinispan.lock;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.transaction.LockingMode;
import org.testng.annotations.Test;

@Test(testName = "lock.StaleLocksTransactionTest", groups = "functional")
@CleanupAfterMethod
public class StaleLocksTransactionTest extends MultipleCacheManagersTest {

   Cache<String, String> c1, c2;

   @Override
   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder cfg = getDefaultClusteredCacheConfig(CacheMode.DIST_SYNC, true);
      cfg
         .locking().lockAcquisitionTimeout(100)
         .transaction().lockingMode(LockingMode.PESSIMISTIC);
      EmbeddedCacheManager cm1 = TestCacheManagerFactory.createClusteredCacheManager(cfg);
      EmbeddedCacheManager cm2 = TestCacheManagerFactory.createClusteredCacheManager(cfg);
      registerCacheManager(cm1, cm2);
      c1 = cm1.getCache();
      c2 = cm2.getCache();
   }

   public void testNoModsCommit() throws Exception {
      doTest(false, true);
   }

   public void testModsRollback() throws Exception {
      doTest(true, false);
   }

   public void testNoModsRollback() throws Exception {
      doTest(false, false);
   }

   public void testModsCommit() throws Exception {
      doTest(true, true);
   }

   private void doTest(boolean mods, boolean commit) throws Exception {
      tm(c1).begin();
      c1.getAdvancedCache().lock("k");
      assert c1.get("k") == null;
      if (mods) c1.put("k", "v");
      if (commit)
         tm(c1).commit();
      else
         tm(c1).rollback();

      assertNotLocked(c1, "k");
      assertNotLocked(c2, "k");
   }
}


File: core/src/test/java/org/infinispan/lock/singlelock/AbstractInitiatorCrashTest.java
package org.infinispan.lock.singlelock;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.tm.DummyTransaction;
import org.testng.annotations.Test;

import java.util.concurrent.CountDownLatch;

/**
 * @author Mircea Markus
 * @since 5.1
 */
@Test(groups = "functional")
public abstract class AbstractInitiatorCrashTest extends AbstractCrashTest {

   public AbstractInitiatorCrashTest(CacheMode cacheMode, LockingMode lockingMode, Boolean useSynchronization) {
      super(cacheMode, lockingMode, useSynchronization);
   }

   public void testInitiatorCrashesBeforeReleasingLock() throws Exception {
      final CountDownLatch releaseLocksLatch = new CountDownLatch(1);

      prepareCache(releaseLocksLatch);

      Object k = getKeyForCache(2);
      beginAndCommitTx(k, 1);
      releaseLocksLatch.await();

      assert checkTxCount(0, 0, 1);
      assert checkTxCount(1, 0, 0);
      assert checkTxCount(2, 0, 1);

      assertNotLocked(cache(0), k);
      assertNotLocked(cache(1), k);
      assertLocked(cache(2), k);

      killMember(1);

      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
      assertNotLocked(k);
   }

   public void testInitiatorNodeCrashesBeforeCommit() throws Exception {

      Object k = getKeyForCache(2);
      
      tm(1).begin();
      cache(1).put(k,"v");
      final DummyTransaction transaction = (DummyTransaction) tm(1).getTransaction();
      transaction.runPrepare();
      tm(1).suspend();

      assertNotLocked(cache(0), k);
      assertNotLocked(cache(1), k);
      assertLocked(cache(2), k);

      checkTxCount(0, 0, 1);
      checkTxCount(1, 1, 0);
      checkTxCount(2, 0, 1);

      killMember(1);

      assertNotLocked(k);
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
   }
}


File: core/src/test/java/org/infinispan/lock/singlelock/MainOwnerChangesPessimisticLockTest.java
package org.infinispan.lock.singlelock;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.distribution.ch.ConsistentHash;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.lookup.DummyTransactionManagerLookup;
import org.infinispan.transaction.tm.DummyTransaction;
import org.testng.annotations.Test;

import javax.transaction.Transaction;
import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.assertEquals;

/**
 * Main owner changes due to state transfer in a distributed cluster using pessimistic locking.
 *
 * @since 5.2
 */
@Test(groups = "functional", testName = "lock.singlelock.MainOwnerChangesPessimisticLockTest")
@CleanupAfterMethod
public class MainOwnerChangesPessimisticLockTest extends MultipleCacheManagersTest {

   public static final int NUM_KEYS = 10;
   private ConfigurationBuilder dccc;

   @Override
   protected void createCacheManagers() throws Throwable {
      dccc = getDefaultClusteredCacheConfig(CacheMode.DIST_SYNC, true, true);
      dccc.transaction()
            .transactionManagerLookup(new DummyTransactionManagerLookup())
            .lockingMode(LockingMode.PESSIMISTIC)
            .syncCommitPhase(true)
            .syncRollbackPhase(true)
            .locking().lockAcquisitionTimeout(1000l)
            .clustering().hash().numOwners(1).numSegments(3)
            .l1().disable()
            .stateTransfer().fetchInMemoryState(true);
      createCluster(dccc, 2);
      waitForClusterToForm();
   }

   public void testLocalLockMigrationTxCommit() throws Exception {
      testLockMigration(0, true);
   }

   public void testLocalLockMigrationTxRollback() throws Exception {
      testLockMigration(0, false);
   }

   public void testRemoteLockMigrationTxCommit() throws Exception {
      testLockMigration(1, true);
   }

   public void testRemoteLockMigrationTxRollback() throws Exception {
      testLockMigration(1, false);
   }

   private void testLockMigration(int nodeThatPuts, boolean commit) throws Exception {
      Map<Object, Transaction> key2Tx = new HashMap<Object, Transaction>();
      for (int i = 0; i < NUM_KEYS; i++) {
         Object key = getKeyForCache(0);
         if (key2Tx.containsKey(key)) continue;

         // put a key to have some data in cache
         cache(nodeThatPuts).put(key, key);

         // start a TX that locks the key and then we suspend it
         tm(nodeThatPuts).begin();
         Transaction tx = tm(nodeThatPuts).getTransaction();
         advancedCache(nodeThatPuts).lock(key);
         tm(nodeThatPuts).suspend();
         key2Tx.put(key, tx);

         assertLocked(0, key);
      }

      log.trace("Lock transfer happens here");

      // add a third node hoping that some of the previously created keys will be migrated to it
      addClusterEnabledCacheManager(dccc);
      waitForClusterToForm();

      // search for a key that was migrated to third node and the suspended TX that locked it
      Object migratedKey = null;
      Transaction migratedTransaction = null;
      ConsistentHash consistentHash = advancedCache(2).getDistributionManager().getConsistentHash();
      for (Object key : key2Tx.keySet()) {
         if (consistentHash.locatePrimaryOwner(key).equals(address(2))) {
            migratedKey = key;
            migratedTransaction = key2Tx.get(key);
            log.trace("Migrated key = " + migratedKey);
            log.trace("Migrated transaction = " + ((DummyTransaction) migratedTransaction).getEnlistedResources());
            break;
         }
      }

      // we do not focus on the other transactions so we commit them now
      log.trace("Committing all transactions except the migrated one.");
      for (Object key : key2Tx.keySet()) {
         if (!key.equals(migratedKey)) {
            Transaction tx = key2Tx.get(key);
            tm(nodeThatPuts).resume(tx);
            tm(nodeThatPuts).commit();
         }
      }

      if (migratedKey == null) {
         // this could happen in extreme cases
         log.trace("No key migrated to new owner - test cannot be performed!");
      } else {
         // the migrated TX is resumed and committed or rolled back. we expect the migrated key to be unlocked now
         tm(nodeThatPuts).resume(migratedTransaction);
         if (commit) {
            tm(nodeThatPuts).commit();
         } else {
            tm(nodeThatPuts).rollback();
         }

         // there should not be any locks
         assertNotLocked(cache(0), migratedKey);
         assertNotLocked(cache(1), migratedKey);
         assertNotLocked(cache(2), migratedKey);

         // if a new TX tries to write to the migrated key this should not fail, the key should not be locked
         tm(nodeThatPuts).begin();
         cache(nodeThatPuts).put(migratedKey, "someValue"); // this should not result in TimeoutException due to key still locked
         tm(nodeThatPuts).commit();
      }

      log.trace("Checking the values from caches...");
      for (Object key : key2Tx.keySet()) {
         log.tracef("Checking key: %s", key);
         Object expectedValue = key;
         if (key.equals(migratedKey)) {
            expectedValue = "someValue";
         }
         // check them directly in data container
         InternalCacheEntry d0 = advancedCache(0).getDataContainer().get(key);
         InternalCacheEntry d1 = advancedCache(1).getDataContainer().get(key);
         InternalCacheEntry d2 = advancedCache(2).getDataContainer().get(key);
         int c = 0;
         if (d0 != null && !d0.isExpired(TIME_SERVICE.wallClockTime())) {
            assertEquals(expectedValue, d0.getValue());
            c++;
         }
         if (d1 != null && !d1.isExpired(TIME_SERVICE.wallClockTime())) {
            assertEquals(expectedValue, d1.getValue());
            c++;
         }
         if (d2 != null && !d2.isExpired(TIME_SERVICE.wallClockTime())) {
            assertEquals(expectedValue, d2.getValue());
            c++;
         }
         assertEquals(1, c);

         // look at them also via cache API
         assertEquals(expectedValue, cache(0).get(key));
         assertEquals(expectedValue, cache(1).get(key));
         assertEquals(expectedValue, cache(2).get(key));
      }
   }
}


File: core/src/test/java/org/infinispan/lock/singlelock/OriginatorBecomesOwnerLockTest.java
package org.infinispan.lock.singlelock;

import java.util.concurrent.Callable;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import javax.transaction.HeuristicMixedException;
import javax.transaction.HeuristicRollbackException;
import javax.transaction.NotSupportedException;
import javax.transaction.RollbackException;
import javax.transaction.SystemException;

import org.infinispan.Cache;
import org.infinispan.commands.VisitableCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.distribution.MagicKey;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.lookup.DummyTransactionManagerLookup;
import org.infinispan.transaction.tm.DummyTransaction;
import org.infinispan.transaction.tm.DummyTransactionManager;
import org.infinispan.tx.dld.ControlledRpcManager;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;
import static org.testng.Assert.fail;


/**
 * Test what happens if the originator becomes an owner during a prepare or commit RPC.
 * @since 5.2
 */
@Test(groups = "functional", testName = "lock.singlelock.OriginatorBecomesOwnerLockTest")
@CleanupAfterMethod
public class OriginatorBecomesOwnerLockTest extends MultipleCacheManagersTest {

   private ConfigurationBuilder configurationBuilder;
   private static final int ORIGINATOR_INDEX = 0;
   private static final int OTHER_INDEX = 1;
   private static final int KILLED_INDEX = 2;
   private Cache<Object, String> originatorCache;
   private Cache<Object, String> killedCache;
   private Cache<Object, String> otherCache;

   // Pseudo-configuration
   // TODO Test fails (expected RollbackException isn't raised) if waitForStateTransfer == false because of https://issues.jboss.org/browse/ISPN-2510
   private boolean waitForStateTransfer = true;
   // TODO Tests fails with SuspectException if stopCacheOnly == false because of https://issues.jboss.org/browse/ISPN-2402
   private boolean stopCacheOnly = true;

   @Override
   protected void createCacheManagers() throws Throwable {
      configurationBuilder = getDefaultClusteredCacheConfig(CacheMode.DIST_SYNC, true, true);
      configurationBuilder.transaction().transactionManagerLookup(new DummyTransactionManagerLookup());
      configurationBuilder.clustering().sync().replTimeout(30000, TimeUnit.MILLISECONDS);
      configurationBuilder.clustering().hash().l1().disable().locking().lockAcquisitionTimeout(1000);
      configurationBuilder.clustering().stateTransfer().fetchInMemoryState(true);
      createCluster(configurationBuilder, 3);
      waitForClusterToForm();

      originatorCache = cache(ORIGINATOR_INDEX);
      killedCache = cache(KILLED_INDEX);
      otherCache = cache(OTHER_INDEX);
   }


   public void testOriginatorBecomesPrimaryOwnerDuringPrepare() throws Exception {
      Object key = new MagicKey("primary", cache(KILLED_INDEX), cache(ORIGINATOR_INDEX));
      testLockMigrationDuringPrepare(key);
   }

   public void testOriginatorBecomesBackupOwnerDuringPrepare() throws Exception {
      Object key = new MagicKey("backup", cache(KILLED_INDEX), cache(OTHER_INDEX));
      testLockMigrationDuringPrepare(key);
   }

   private void testLockMigrationDuringPrepare(final Object key) throws Exception {
      ControlledRpcManager controlledRpcManager = installControlledRpcManager(PrepareCommand.class);
      final DummyTransactionManager tm = dummyTm(ORIGINATOR_INDEX);

      Future<DummyTransaction> f = fork(new Callable<DummyTransaction>() {
         @Override
         public DummyTransaction call() throws Exception {
            tm.begin();
            originatorCache.put(key, "value");
            DummyTransaction tx = tm.getTransaction();

            boolean success = tx.runPrepare();
            assertTrue(success);
            tm.suspend();
            return tx;
         }
      });

      // Allow the tx thread to send the prepare command to the owners
      Thread.sleep(2000);

      log.trace("Lock transfer happens here");
      killCache();

      log.trace("Allow the prepare RPC to proceed");
      controlledRpcManager.stopBlocking();
      // Ensure the prepare finished on the other node
      DummyTransaction tx = f.get();
      log.tracef("Prepare finished");

      checkNewTransactionFails(key);

      log.trace("About to commit existing transactions.");
      tm.resume(tx);
      tx.runCommit(false);

      // read the data from the container, just to make sure all replicas are correctly set
      checkValue(key, "value");
   }


   public void testOriginatorBecomesPrimaryOwnerAfterPrepare() throws Exception {
      Object key = new MagicKey("primary", cache(KILLED_INDEX), cache(ORIGINATOR_INDEX));
      testLockMigrationAfterPrepare(key);
   }

   public void testOriginatorBecomesBackupOwnerAfterPrepare() throws Exception {
      Object key = new MagicKey("backup", cache(KILLED_INDEX), cache(OTHER_INDEX));
      testLockMigrationAfterPrepare(key);
   }

   private void testLockMigrationAfterPrepare(Object key) throws Exception {
      final DummyTransactionManager tm = dummyTm(ORIGINATOR_INDEX);

      tm.begin();
      originatorCache.put(key, "value");
      DummyTransaction tx = tm.getTransaction();

      boolean prepareSuccess = tx.runPrepare();
      assert prepareSuccess;

      tm.suspend();

      log.trace("Lock transfer happens here");
      killCache();

      checkNewTransactionFails(key);

      log.trace("About to commit existing transaction.");
      tm.resume(tx);
      tx.runCommit(false);

      // read the data from the container, just to make sure all replicas are correctly set
      checkValue(key, "value");
   }


   public void testOriginatorBecomesPrimaryOwnerDuringCommit() throws Exception {
      Object key = new MagicKey("primary", cache(KILLED_INDEX), cache(ORIGINATOR_INDEX));
      testLockMigrationDuringCommit(key);
   }

   public void testOriginatorBecomesBackupOwnerDuringCommit() throws Exception {
      Object key = new MagicKey("backup", cache(KILLED_INDEX), cache(OTHER_INDEX));
      testLockMigrationDuringCommit(key);
   }

   private void testLockMigrationDuringCommit(final Object key) throws Exception {
      ControlledRpcManager controlledRpcManager = installControlledRpcManager(CommitCommand.class);
      final DummyTransactionManager tm = dummyTm(ORIGINATOR_INDEX);

      Future<DummyTransaction> f = fork(new Callable<DummyTransaction>() {
         @Override
         public DummyTransaction call() throws Exception {
            tm.begin();
            originatorCache.put(key, "value");
            final DummyTransaction tx = tm.getTransaction();
            final boolean success = tx.runPrepare();
            assert success;

            log.trace("About to commit transaction.");
            tx.runCommit(false);
            return null;
         }
      });

      // Allow the tx thread to send the commit to the owners
      Thread.sleep(2000);

      log.trace("Lock transfer happens here");
      killCache();

      log.trace("Allow the commit RPC to proceed");
      controlledRpcManager.stopBlocking();
      // Ensure the commit finished on the other node
      f.get();
      log.tracef("Commit finished");

      // read the data from the container, just to make sure all replicas are correctly set
      checkValue(key, "value");

      assertNoLocksOrTxs(key, originatorCache);
      assertNoLocksOrTxs(key, otherCache);
   }


   private void assertNoLocksOrTxs(Object key, Cache<Object, String> cache) {
      assertNotLocked(originatorCache, key);

      final TransactionTable transactionTable = TestingUtil.extractComponent(cache, TransactionTable.class);

      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return transactionTable.getLocalTxCount() == 0 && transactionTable.getRemoteTxCount() == 0;
         }
      });
   }

   private ControlledRpcManager installControlledRpcManager(Class<? extends VisitableCommand> commandClass) {
      ControlledRpcManager controlledRpcManager = new ControlledRpcManager(
            originatorCache.getAdvancedCache().getRpcManager());
      controlledRpcManager.blockBefore(commandClass);
      TestingUtil.replaceComponent(originatorCache, RpcManager.class, controlledRpcManager, true);
      return controlledRpcManager;
   }

   private void killCache() {
      if (stopCacheOnly) {
         killedCache.stop();
      } else {
         manager(KILLED_INDEX).stop();
      }
      if (waitForStateTransfer) {
         TestingUtil.waitForRehashToComplete(originatorCache, otherCache);
      }
   }

   private void checkValue(Object key, String value) {
      if (!waitForStateTransfer) {
         TestingUtil.waitForRehashToComplete(originatorCache, otherCache);
      }
      log.tracef("Checking key: %s", key);
      InternalCacheEntry d0 = advancedCache(ORIGINATOR_INDEX).getDataContainer().get(key);
      InternalCacheEntry d1 = advancedCache(OTHER_INDEX).getDataContainer().get(key);
      assertEquals(d0.getValue(), value);
      assertEquals(d1.getValue(), value);
   }

   private void checkNewTransactionFails(Object key) throws NotSupportedException, SystemException, HeuristicMixedException, HeuristicRollbackException {
      DummyTransactionManager otherTM = dummyTm(OTHER_INDEX);
      otherTM.begin();
      otherCache.put(key, "should fail");
      try {
         otherTM.commit();
         fail("RollbackException should have been thrown here.");
      } catch (RollbackException e) {
         //expected
      }
   }


   private DummyTransactionManager dummyTm(int cacheIndex) {
      return (DummyTransactionManager) tm(cacheIndex);
   }
}


File: core/src/test/java/org/infinispan/lock/singlelock/pessimistic/InitiatorCrashPessimisticTest.java
package org.infinispan.lock.singlelock.pessimistic;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.lock.singlelock.AbstractInitiatorCrashTest;
import org.infinispan.test.AbstractInfinispanTest;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.transaction.LockingMode;
import org.testng.annotations.Test;

/**
 * @author Mircea Markus
 * @since 5.1
 */
@Test(groups = "functional", testName = "lock.singlelock.pessimistic.InitiatorCrashPessimisticTest")
@CleanupAfterMethod
public class InitiatorCrashPessimisticTest extends AbstractInitiatorCrashTest {

   public InitiatorCrashPessimisticTest() {
      super(CacheMode.DIST_SYNC, LockingMode.PESSIMISTIC, false);
   }

 public void testInitiatorNodeCrashesBeforePrepare2() throws Exception {

      Object k0 = getKeyForCache(0);
      Object k1 = getKeyForCache(1);
      Object k2 = getKeyForCache(2);

      tm(1).begin();
      cache(1).put(k0, "v0");
      cache(1).put(k1, "v1");
      cache(1).put(k2, "v2");

      assertLocked(cache(0), k0);
      assertNotLocked(cache(1), k0);
      assertNotLocked(cache(2), k0);

      assertNotLocked(cache(0), k1);
      assertLocked(cache(1), k1);
      assertNotLocked(cache(2), k1);

      assertNotLocked(cache(0), k2);
      assertNotLocked(cache(1), k2);
      assertLocked(cache(2), k2);

      assert checkTxCount(0, 0, 1);
      assert checkTxCount(1, 1, 0);
      assert checkTxCount(2, 0, 1);

      killMember(1);

      assert caches().size() == 2;

      assertNotLocked(k0);
      assertNotLocked(k1);
      assertNotLocked(k2);
      eventually(new AbstractInfinispanTest.Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
   }
}


File: core/src/test/java/org/infinispan/lock/singlelock/replicated/optimistic/InitiatorCrashOptimisticReplTest.java
package org.infinispan.lock.singlelock.replicated.optimistic;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.lock.singlelock.AbstractCrashTest;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.transaction.LockingMode;
import org.testng.annotations.Test;

import java.util.concurrent.CountDownLatch;

/**
 * @author Mircea Markus
 * @since 5.1
 */
@Test(groups = "unstable", testName = "lock.singlelock.replicated.optimistic.InitiatorCrashOptimisticReplTest", description = "See ISPN-2161 -- original group: functional")
@CleanupAfterMethod
public class InitiatorCrashOptimisticReplTest extends AbstractCrashTest {

   public InitiatorCrashOptimisticReplTest() {
      super(CacheMode.REPL_SYNC, LockingMode.OPTIMISTIC, false);
   }

   public InitiatorCrashOptimisticReplTest(CacheMode mode, LockingMode locking, boolean useSync) {
      super(mode, locking, useSync);
   }

   public void testInitiatorNodeCrashesBeforeCommit() throws Exception {

      TxControlInterceptor txControlInterceptor = new TxControlInterceptor();
      txControlInterceptor.prepareProgress.countDown();
      advancedCache(1).addInterceptor(txControlInterceptor, 1);

      beginAndCommitTx("k", 1);
      txControlInterceptor.commitReceived.await();

      assertLocked(cache(0), "k");
      assertNotLocked(cache(1), "k");
      assertNotLocked(cache(2), "k");

      checkTxCount(0, 0, 1);
      checkTxCount(1, 1, 0);
      checkTxCount(2, 0, 1);

      killMember(1);

      assertNotLocked("k");
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
   }

   public void testInitiatorCrashesBeforeReleasingLock() throws Exception {
      final CountDownLatch releaseLocksLatch = new CountDownLatch(1);

      prepareCache(releaseLocksLatch);

      beginAndCommitTx("k", 1);
      releaseLocksLatch.await();

      assert checkTxCount(0, 0, 1);
      assert checkTxCount(1, 0, 0);
      assert checkTxCount(2, 0, 1);

      assertLocked(cache(0), "k");
      assertNotLocked(cache(1), "k");
      assertNotLocked(cache(2), "k");

      killMember(1);

      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
      assertNotLocked("k");
      assert cache(0).get("k").equals("v");
      assert cache(1).get("k").equals("v");
   }

   public void testInitiatorNodeCrashesBeforePrepare() throws Exception {

      TxControlInterceptor txControlInterceptor = new TxControlInterceptor();
      advancedCache(1).addInterceptor(txControlInterceptor, 1);

      //prepare is sent, but is not precessed on other nodes because of the txControlInterceptor.preparedReceived
      beginAndPrepareTx("k", 1);

      txControlInterceptor.preparedReceived.await();
      assert checkTxCount(0, 0, 1);
      assert checkTxCount(1, 1, 0);
      assert checkTxCount(2, 0, 1);

      killMember(1);

      assert caches().size() == 2;
      txControlInterceptor.prepareProgress.countDown();

      assertNotLocked("k");
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
   }
}


File: core/src/test/java/org/infinispan/lock/singlelock/replicated/pessimistic/InitiatorCrashPessimisticReplTest.java
package org.infinispan.lock.singlelock.replicated.pessimistic;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.distribution.MagicKey;
import org.infinispan.lock.singlelock.replicated.optimistic.InitiatorCrashOptimisticReplTest;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.transaction.LockingMode;
import org.testng.annotations.Test;

import java.util.concurrent.CountDownLatch;

/**
 * @author Mircea Markus
 * @since 5.1
 */
@Test(groups = "unstable", testName = "lock.singlelock.replicated.pessimistic.InitiatorCrashPessimisticReplTest", description = "See ISPN-2161 -- original group: functional")
@CleanupAfterMethod
public class InitiatorCrashPessimisticReplTest extends InitiatorCrashOptimisticReplTest {

   public InitiatorCrashPessimisticReplTest() {
      super(CacheMode.REPL_SYNC, LockingMode.PESSIMISTIC, false);
   }

   public void testInitiatorNodeCrashesBeforeCommit() throws Exception {
      TxControlInterceptor txControlInterceptor = new TxControlInterceptor();
      txControlInterceptor.prepareProgress.countDown();
      advancedCache(1).addInterceptor(txControlInterceptor, 1);

      MagicKey key = new MagicKey("k", cache(0));
      beginAndCommitTx(key, 1);
      txControlInterceptor.preparedReceived.await();

      assertLocked(cache(0), key);
      assertNotLocked(cache(1), key);
      assertNotLocked(cache(2), key);

      checkTxCount(0, 0, 1);
      checkTxCount(1, 1, 0);
      checkTxCount(2, 0, 1);

      killMember(1);

      assertNotLocked(key);
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
   }

   public void testInitiatorCrashesBeforeReleasingLock() throws Exception {
      final CountDownLatch releaseLocksLatch = new CountDownLatch(1);

      prepareCache(releaseLocksLatch);

      MagicKey key = new MagicKey("k", cache(0));
      beginAndCommitTx(key, 1);
      releaseLocksLatch.await();

      assert checkTxCount(0, 0, 1);
      assert checkTxCount(1, 0, 0);
      assert checkTxCount(2, 0, 1);

      assertLocked(cache(0), key);
      assertNotLocked(cache(1), key);
      assertNotLocked(cache(2), key);

      killMember(1);

      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
      assertNotLocked(key);
      assert cache(0).get(key).equals("v");
      assert cache(1).get(key).equals("v");
   }

   public void testInitiatorNodeCrashesBeforePrepare() throws Exception {
      MagicKey key = new MagicKey("a", cache(0));
      cache(0).put(key, "b");
      assert cache(0).get(key).equals("b");
      assert cache(1).get(key).equals("b");
      assert cache(2).get(key).equals("b");

      TxControlInterceptor txControlInterceptor = new TxControlInterceptor();
      advancedCache(1).addInterceptor(txControlInterceptor, 1);

      //prepare is sent, but is not precessed on other nodes because of the txControlInterceptor.preparedReceived
      beginAndPrepareTx("k", 1);

      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return  checkTxCount(0, 0, 1) &&  checkTxCount(1, 1, 0) && checkTxCount(2, 0, 1);
         }
      });

      killMember(1);

      assert caches().size() == 2;
      txControlInterceptor.prepareProgress.countDown();

      assertNotLocked("k");
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return checkTxCount(0, 0, 0) && checkTxCount(1, 0, 0);
         }
      });
   }
}


File: core/src/test/java/org/infinispan/partitionhandling/BasePartitionHandlingTest.java
package org.infinispan.partitionhandling;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.notifications.Listener;
import org.infinispan.notifications.cachemanagerlistener.annotation.ViewChanged;
import org.infinispan.notifications.cachemanagerlistener.event.ViewChangedEvent;
import org.infinispan.partitionhandling.impl.PartitionHandlingManager;
import org.infinispan.remoting.transport.jgroups.JGroupsTransport;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.TEST_PING;
import org.infinispan.test.fwk.TransportFlags;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;
import org.jgroups.Address;
import org.jgroups.Channel;
import org.jgroups.MergeView;
import org.jgroups.View;
import org.jgroups.protocols.DISCARD;
import org.jgroups.protocols.Discovery;
import org.jgroups.protocols.TP;
import org.jgroups.protocols.pbcast.GMS;
import org.jgroups.stack.Protocol;
import org.jgroups.stack.ProtocolStack;
import org.testng.annotations.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.fail;

@Test(groups = "functional", testName = "partitionhandling.BasePartitionHandlingTest")
public class BasePartitionHandlingTest extends MultipleCacheManagersTest {


   private static Log log = LogFactory.getLog(BasePartitionHandlingTest.class);

   private final AtomicInteger viewId = new AtomicInteger(5);
   protected int numMembersInCluster = 4;
   protected CacheMode cacheMode = CacheMode.DIST_SYNC;
   protected volatile Partition[] partitions;
   protected boolean partitionHandling = true;

   public BasePartitionHandlingTest() {
      this.cleanup = CleanupPhase.AFTER_METHOD;
   }

   @Override
   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder dcc = new ConfigurationBuilder();
      dcc.clustering().cacheMode(cacheMode).partitionHandling().enabled(partitionHandling);
      createClusteredCaches(numMembersInCluster, dcc, new TransportFlags().withFD(true).withMerge(true));
      waitForClusterToForm();
   }


   @Listener
   static class ViewChangedHandler {

      volatile boolean notified = false;

      @ViewChanged
      public void viewChanged(ViewChangedEvent vce) {
         notified = true;
      }
   }

   public static class PartitionDescriptor {
      int[] nodes;

      PartitionDescriptor(int... nodes) {
         this.nodes = nodes;
      }

      public int[] getNodes() {
         return nodes;
      }

      public int node(int i) {
         return nodes[i];
      }
   }

   class Partition {

      private final List<Address> allMembers;
      List<Channel> channels = new ArrayList<>();

      public Partition(List<Address> allMembers) {
         this.allMembers = allMembers;
      }

      public void addNode(Channel c) {
         channels.add(c);
      }

      public void partition() {
         discardOtherMembers();

         log.trace("Partition forming");
         disableDiscovery();
         installNewView();
         assertPartitionFormed();
         log.trace("New views installed");
      }

      private void disableDiscovery() {
         for (Channel c : channels) {
            for (Protocol p : c.getProtocolStack().getProtocols()) {
               if (p instanceof Discovery) {
                  if (!(p instanceof TEST_PING)) throw new IllegalStateException("TEST_PING required for this test.");
                  ((TEST_PING) p).suspend();
               }
            }
         }
      }

      private void assertPartitionFormed() {
         final List<Address> viewMembers = new ArrayList<>();
         for (Channel ac : channels) viewMembers.add(ac.getAddress());
         for (Channel c : channels) {
            List<Address> members = c.getView().getMembers();
            if (!members.equals(viewMembers)) throw new AssertionError();
         }
      }

      private List<Address> installNewView() {
         final List<Address> viewMembers = new ArrayList<>();
         for (Channel c : channels) viewMembers.add(c.getAddress());
         View view = View.create(channels.get(0).getAddress(), viewId.incrementAndGet(), (Address[]) viewMembers.toArray(new Address[viewMembers.size()]));

         log.trace("Before installing new view...");
         for (Channel c : channels)
            ((GMS) c.getProtocolStack().findProtocol(GMS.class)).installView(view);
         return viewMembers;
      }

      private List<Address> installMergeView(ArrayList<Channel> view1, ArrayList<Channel> view2) {
         List<Address> allAddresses = new ArrayList<>();
         for (Channel c: view1) allAddresses.add(c.getAddress());
         for (Channel c: view2) allAddresses.add(c.getAddress());

         View v1 = toView(view1);
         View v2 = toView(view2);
         List<View> allViews = new ArrayList<>();
         allViews.add(v1);
         allViews.add(v2);

//         log.trace("Before installing new view: " + viewMembers);
//         System.out.println("Before installing new view: " + viewMembers);
         MergeView mv = new MergeView(view1.get(0).getAddress(), (long)viewId.incrementAndGet(), allAddresses, allViews);
         for (Channel c : channels)
            ((GMS) c.getProtocolStack().findProtocol(GMS.class)).installView(mv);
         return allMembers;
      }

      private View toView(ArrayList<Channel> channels) {
         final List<Address> viewMembers = new ArrayList<>();
         for (Channel c : channels) viewMembers.add(c.getAddress());
         return View.create(channels.get(0).getAddress(), viewId.incrementAndGet(), (Address[]) viewMembers.toArray(new Address[viewMembers.size()]));
      }

      private void discardOtherMembers() {
         List<Address> outsideMembers = new ArrayList<Address>();
         for (Address a : allMembers) {
            boolean inThisPartition = false;
            for (Channel c : channels) {
               if (c.getAddress().equals(a)) inThisPartition = true;
            }
            if (!inThisPartition) outsideMembers.add(a);
         }
         for (Channel c : channels) {
            DISCARD discard = new DISCARD();
            for (Address a : outsideMembers) discard.addIgnoreMember(a);
            try {
               c.getProtocolStack().insertProtocol(discard, ProtocolStack.ABOVE, TP.class);
            } catch (Exception e) {
               throw new RuntimeException(e);
            }
         }
      }

      @Override
      public String toString() {
         String addresses = "";
         for (Channel c : channels) addresses += c.getAddress() + " ";
         return "Partition{" + addresses + '}';
      }

      public void merge(Partition partition) {
         observeMembers(partition);
         partition.observeMembers(this);
         ArrayList<Channel> view1 = new ArrayList<>(channels);
         ArrayList<Channel> view2 = new ArrayList<>(partition.channels);
//         System.out.println("view1 = " + printView(view1));
//         System.out.println("view2 = " + printView(view2));
         channels.addAll(partition.channels);
         installMergeView(view1, view2);
         waitForPartitionToForm();
         List<Partition> tmp = new ArrayList<>(Arrays.asList(BasePartitionHandlingTest.this.partitions));
         if (!tmp.remove(partition)) throw new AssertionError();
         BasePartitionHandlingTest.this.partitions = tmp.toArray(new Partition[tmp.size()]);
      }

      private String printView(ArrayList<Channel> view1) {
         StringBuilder sb = new StringBuilder();
         for (Channel c: view1) sb.append(c.getAddress()).append(" ");
         return sb.insert(0, "[ ").append(" ]").toString();
      }

      private void waitForPartitionToForm() {
         List<Cache<Object, Object>> caches = new ArrayList<>(getCaches(null));
         Iterator<Cache<Object, Object>> i = caches.iterator();
         while (i.hasNext()) {
            if (!channels.contains(channel(i.next())))
               i.remove();
         }
         Cache<Object, Object> cache = caches.get(0);
         TestingUtil.blockUntilViewsReceived(10000, caches);
         if (cache.getCacheConfiguration().clustering().cacheMode().isClustered()) {
            TestingUtil.waitForRehashToComplete(caches);
         }
      }

      public void enableDiscovery() {
         for (Channel c : channels) {
            for (Protocol p : c.getProtocolStack().getProtocols()) {
               if (p instanceof Discovery) {
                  try {
                     log.tracef("About to start discovery: %s", p);
                     p.start();
                  } catch (Exception e) {
                     throw new RuntimeException(e);
                  }
               }
            }
         }
         log.trace("Discovery started.");
      }

      private void observeMembers(Partition partition) {
         for (Channel c : channels) {
            List<Protocol> protocols = c.getProtocolStack().getProtocols();
            for (Protocol p : protocols) {
               if (p instanceof DISCARD) {
                  for (Channel oc : partition.channels) {
                     ((DISCARD) p).removeIgnoredMember(oc.getAddress());
                  }
               }
            }
         }
      }

      public void assertDegradedMode() {
         if (partitionHandling) {
            assertAvailabilityMode(AvailabilityMode.DEGRADED_MODE);
         }
      }

      public void assertKeyAvailableForRead(Object k, Object expectedValue) {
         for (Cache c : cachesInThisPartition()) {
            assertEquals(c.get(k), expectedValue, "Cache " + c.getAdvancedCache().getRpcManager().getAddress() + " doesn't see the right value: ");
         }
      }

      public void assertKeyAvailableForWrite(Object k, Object newValue) {
         for (Cache c : cachesInThisPartition()) {
            c.put(k, newValue);
            assertEquals(c.get(k), newValue, "Cache " + c.getAdvancedCache().getRpcManager().getAddress() + " doesn't see the right value");
         }
      }

      protected void assertKeysNotAvailableForRead(Object... keys) {
         for (Object k : keys)
            assertKeyNotAvailableForRead(k);
      }

      protected void assertKeyNotAvailableForRead(Object key) {
         for (Cache c : cachesInThisPartition()) {
            try {
               c.get(key);
               fail("Key " + key + " available in cache " + address(c));
            } catch (AvailabilityException ae) {}
         }
      }


      private List<Cache> cachesInThisPartition() {
         List<Cache> caches = new ArrayList<Cache>();
         for (final Cache c : caches()) {
            if (channels.contains(channel(c))) {
               caches.add(c);
            }
         }
         return caches;
      }

      public void assertKeyNotAvailableForWrite(Object key) {
         for (Cache c : cachesInThisPartition()) {
            try {
               c.put(key, key);
               fail();
            } catch (AvailabilityException ae) {}
         }
      }

      public void assertKeysNotAvailableForWrite(Object ... keys) {
         for (Object k : keys) {
            assertKeyNotAvailableForWrite(k);
         }
      }

      public void assertAvailabilityMode(final AvailabilityMode state) {
         for (final Cache c : cachesInThisPartition()) {
            eventually(new Condition() {
               @Override
               public boolean isSatisfied() throws Exception {
                  return partitionHandlingManager(c).getAvailabilityMode() == state;
               }
            });
         }
      }
   }

   protected void splitCluster(int[]... parts) {
      List<Address> allMembers = channel(0).getView().getMembers();
      partitions = new Partition[parts.length];
      for (int i = 0; i < parts.length; i++) {
         Partition p = new Partition(allMembers);
         for (int j : parts[i]) {
            p.addNode(channel(j));
         }
         partitions[i] = p;
         p.partition();
      }
   }

   private Channel channel(int i) {
      Cache<Object, Object> cache = cache(i);
      return channel(cache);
   }

   private Channel channel(Cache<Object, Object> cache) {
      JGroupsTransport t = (JGroupsTransport) cache.getAdvancedCache().getRpcManager().getTransport();
      return t.getChannel();
   }

   protected Partition partition(int i) {
      if (partitions == null)
         throw new IllegalStateException("splitCluster(..) must be invoked before this method!");
      return partitions[i];
   }

   protected PartitionHandlingManager partitionHandlingManager(int index) {
      return partitionHandlingManager(advancedCache(index));
   }

   private PartitionHandlingManager partitionHandlingManager(Cache cache) {
      return cache.getAdvancedCache().getComponentRegistry().getComponent(PartitionHandlingManager.class);
   }

   protected void assertExpectedValue(Object expectedVal, Object key) {
      for (int i = 0; i < numMembersInCluster; i++) {
         assertEquals(cache(i).get(key), expectedVal);
      }
   }

}


File: core/src/test/java/org/infinispan/replication/AsyncReplTest.java
package org.infinispan.replication;

import org.infinispan.Cache;
import org.infinispan.commands.write.PutKeyValueCommand;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.TestingUtil;
import org.testng.annotations.Test;

import javax.transaction.TransactionManager;

import static org.testng.AssertJUnit.assertEquals;

@Test(groups = "functional", testName = "replication.AsyncReplTest")
public class AsyncReplTest extends MultipleCacheManagersTest {

   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder asyncConfiguration = getDefaultClusteredCacheConfig(CacheMode.REPL_ASYNC, true);
      createClusteredCaches(2, "asyncRepl", asyncConfiguration);   
   }

   public void testWithNoTx() throws Exception {

      Cache cache1 = cache(0,"asyncRepl");
      Cache cache2 = cache(1,"asyncRepl");
      String key = "key";

      replListener(cache2).expect(PutKeyValueCommand.class);
      cache1.put(key, "value1");
      // allow for replication
      replListener(cache2).waitForRpc();
      assertEquals("value1", cache1.get(key));
      assertEquals("value1", cache2.get(key));

      replListener(cache2).expect(PutKeyValueCommand.class);
      cache1.put(key, "value2");
      assertEquals("value2", cache1.get(key));

      replListener(cache2).waitForRpc();

      assertEquals("value2", cache1.get(key));
      assertEquals("value2", cache2.get(key));
   }

   public void testWithTx() throws Exception {
      Cache cache1 = cache(0,"asyncRepl");
      Cache cache2 = cache(1,"asyncRepl");
      
      String key = "key";
      replListener(cache2).expect(PutKeyValueCommand.class);
      cache1.put(key, "value1");
      // allow for replication
      replListener(cache2).waitForRpc();
      assertNotLocked(cache1, key);

      assertEquals("value1", cache1.get(key));
      assertEquals("value1", cache2.get(key));

      TransactionManager mgr = TestingUtil.getTransactionManager(cache1);
      mgr.begin();
      replListener(cache2).expectWithTx(PutKeyValueCommand.class);
      cache1.put(key, "value2");
      assertEquals("value2", cache1.get(key));
      assertEquals("value1", cache2.get(key));
      mgr.commit();
      replListener(cache2).waitForRpc();
      assertNotLocked(cache1, key);

      assertEquals("value2", cache1.get(key));
      assertEquals("value2", cache2.get(key));

      mgr.begin();
      cache1.put(key, "value3");
      assertEquals("value3", cache1.get(key));
      assertEquals("value2", cache2.get(key));

      mgr.rollback();

      assertEquals("value2", cache1.get(key));
      assertEquals("value2", cache2.get(key));

      assertNotLocked(cache1, key);

   }

   public void simpleTest() throws Exception {
      Cache cache1 = cache(0,"asyncRepl");
      Cache cache2 = cache(1,"asyncRepl");
      
      String key = "key";
      TransactionManager mgr = TestingUtil.getTransactionManager(cache1);

      mgr.begin();
      cache1.put(key, "value3");
      mgr.rollback();

      assertNotLocked(cache1, key);

   }
}


File: core/src/test/java/org/infinispan/replication/SyncReplLockingTest.java
package org.infinispan.replication;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.TestingUtil;

import static org.testng.AssertJUnit.assertEquals;
import static org.testng.AssertJUnit.assertNull;

import org.infinispan.transaction.LockingMode;
import org.infinispan.transaction.lookup.DummyTransactionManagerLookup;
import org.infinispan.transaction.tm.DummyTransactionManager;
import org.testng.annotations.Test;

import javax.transaction.TransactionManager;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * Tests for lock API
 * <p/>
 * Introduce lock() API methods https://jira.jboss.org/jira/browse/ISPN-48
 *
 * @author Manik Surtani
 * @author Vladimir Blagojevic
 */
@Test(groups = "functional", testName = "replication.SyncReplLockingTest")
public class SyncReplLockingTest extends MultipleCacheManagersTest {
   private String k = "key", v = "value";

   public SyncReplLockingTest() {
      cleanup = CleanupPhase.AFTER_METHOD;
   }

   protected CacheMode getCacheMode() {
      return CacheMode.REPL_SYNC;
   }

   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder cfg = getDefaultClusteredCacheConfig(getCacheMode(), true);
      cfg.transaction().transactionManagerLookup(new DummyTransactionManagerLookup())
            .lockingMode(LockingMode.PESSIMISTIC)
            .locking().lockAcquisitionTimeout(500);
      createClusteredCaches(2, "testcache", cfg);
      waitForClusterToForm("testcache");
   }

   public void testLocksReleasedWithoutExplicitUnlock() throws Exception {
      locksReleasedWithoutExplicitUnlockHelper(false, false);
      locksReleasedWithoutExplicitUnlockHelper(true, false);
      locksReleasedWithoutExplicitUnlockHelper(false, true);
      locksReleasedWithoutExplicitUnlockHelper(true, true);
   }

   public void testConcurrentNonTxLocking() throws Exception {
      concurrentLockingHelper(false, false);
      concurrentLockingHelper(true, false);
   }

   public void testConcurrentTxLocking() throws Exception {
      concurrentLockingHelper(false, true);
      concurrentLockingHelper(true, true);
   }

   public void testLocksReleasedWithNoMods() throws Exception {
      Cache cache1 = cache(0, "testcache");
      Cache cache2 = cache(1, "testcache");
      assertClusterSize("Should only be 2  caches in the cluster!!!", 2);

      assertNull("Should be null", cache1.get(k));
      assertNull("Should be null", cache2.get(k));

      TransactionManager mgr = TestingUtil.getTransactionManager(cache1);
      mgr.begin();

      cache1.getAdvancedCache().lock(k);

      //do a dummy read
      cache1.get(k);
      mgr.commit();

      assertNotLocked(cache1, "testcache");
      assertNotLocked(cache2, "testcache");

      assert cache1.isEmpty();
      assert cache2.isEmpty();
      cache1.clear();
      cache2.clear();
   }
   
   public void testReplaceNonExistentKey() throws Exception {
      Cache cache1 = cache(0, "testcache");
      Cache cache2 = cache(1, "testcache");
      assertClusterSize("Should only be 2  caches in the cluster!!!", 2);
     
		TransactionManager mgr = TestingUtil.getTransactionManager(cache1);
		mgr.begin();

		cache1.getAdvancedCache().lock(k);

		// do a replace on empty key
		// https://jira.jboss.org/browse/ISPN-514
		Object old = cache1.replace(k, "blah");
		assertNull("Should be null", cache1.get(k));

		boolean replaced = cache1.replace(k, "Vladimir", "Blagojevic");
		assert !replaced;

		assertNull("Should be null", cache1.get(k));
		mgr.commit();

		assertNotLocked(cache1, "testcache");
		assertNotLocked(cache2, "testcache");

		assert cache1.isEmpty();
		assert cache2.isEmpty();
		cache1.clear();
		cache2.clear();
	}
   
   private void concurrentLockingHelper(final boolean sameNode, final boolean useTx) throws Exception {
      final Cache cache1 = cache(0, "testcache");
      final Cache cache2 = cache(1, "testcache");
      assertClusterSize("Should only be 2  caches in the cluster!!!", 2);

      assertNull("Should be null", cache1.get(k));
      assertNull("Should be null", cache2.get(k));
      final CountDownLatch latch = new CountDownLatch(1);

      Thread t = new Thread() {
         @Override
         public void run() {
            log.info("Concurrent " + (useTx ? "tx" : "non-tx") + " write started "
                  + (sameNode ? "on same node..." : "on a different node..."));
            DummyTransactionManager mgr = null;
            try {
               if (useTx) {
                  mgr = (DummyTransactionManager) TestingUtil.getTransactionManager(sameNode ? cache1 : cache2);
                  mgr.begin();
               }
               if (sameNode) {
                  cache1.put(k, "JBC");
               } else {
                  cache2.put(k, "JBC");
               }
               if (useTx) {
                  if (!mgr.getTransaction().runPrepare()) { //couldn't prepare
                     latch.countDown();
                     mgr.rollback();
                  }
               }
            } catch (Exception e) {
               if (useTx) {
                  try {
                     mgr.commit();
                  } catch (Exception e1) {
                  }
               }
               latch.countDown();
            }
         }
      };

      String name = "Infinispan";
      TransactionManager mgr = TestingUtil.getTransactionManager(cache1);
      mgr.begin();

      log.trace("Here is where the fun starts...Here is where the fun starts...");

      // lock node and start other thread whose write should now block
      cache1.getAdvancedCache().lock(k);
      t.start();

      // wait till the put in thread t times out
      assert latch.await(10, TimeUnit.SECONDS) : "Concurrent put didn't time out!";

      cache1.put(k, name);
      mgr.commit();

      assertNotLocked("testcache", k);
      t.join();


      cache2.remove(k);
      assert cache1.isEmpty();
      assert cache2.isEmpty();
      cache1.clear();
      cache2.clear();
   }

   private void locksReleasedWithoutExplicitUnlockHelper(boolean lockPriorToPut, boolean useCommit)
         throws Exception {
      
      Cache cache1 = cache(0, "testcache");
      Cache cache2 = cache(1, "testcache");
      
      assertClusterSize("Should only be 2  caches in the cluster!!!", 2);

      assertNull("Should be null", cache1.get(k));
      assertNull("Should be null", cache2.get(k));

      String name = "Infinispan";
      TransactionManager mgr = TestingUtil.getTransactionManager(cache1);
      mgr.begin();
      if (lockPriorToPut)
         cache1.getAdvancedCache().lock(k);
      cache1.put(k, name);
      if (!lockPriorToPut)
         cache1.getAdvancedCache().lock(k);

      if (useCommit)
         mgr.commit();
      else
         mgr.rollback();

      if (useCommit) {
         assertEquals(name, cache1.get(k));
         assertEquals("Should have replicated", name, cache2.get(k));
      } else {
         assertEquals(null, cache1.get(k));
         assertEquals("Should not have replicated", null, cache2.get(k));
      }

      cache2.remove(k);
      assert cache1.isEmpty();
      assert cache2.isEmpty();
      cache1.clear();
      cache2.clear();
   }

}


File: core/src/test/java/org/infinispan/statetransfer/StaleLocksWithCommitDuringStateTransferTest.java
package org.infinispan.statetransfer;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import org.infinispan.Cache;
import org.infinispan.commands.VisitableCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.context.InvocationContext;
import org.infinispan.distribution.MagicKey;
import org.infinispan.interceptors.InterceptorChain;
import org.infinispan.interceptors.base.CommandInterceptor;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.transaction.TransactionMode;
import org.infinispan.transaction.impl.LocalTransaction;
import org.infinispan.transaction.impl.TransactionCoordinator;
import org.infinispan.transaction.impl.TransactionTable;
import org.testng.annotations.Test;

@Test(testName = "statetransfer.StaleLocksWithCommitDuringStateTransferTest", groups = "functional")
@CleanupAfterMethod
public class StaleLocksWithCommitDuringStateTransferTest extends MultipleCacheManagersTest {

   Cache<MagicKey, String> c1, c2;

   @Override
   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder cb = new ConfigurationBuilder();
      cb.clustering().cacheMode(CacheMode.DIST_SYNC)
            .sync().replTimeout(5000)
            .transaction().transactionMode(TransactionMode.TRANSACTIONAL).cacheStopTimeout(100);
      EmbeddedCacheManager cm1 = TestCacheManagerFactory.createClusteredCacheManager(cb);
      EmbeddedCacheManager cm2 = TestCacheManagerFactory.createClusteredCacheManager(cb);
      registerCacheManager(cm1, cm2);
      c1 = cm1.getCache();
      c2 = cm2.getCache();
      waitForClusterToForm();
   }

   public void testRollbackLocalFailure() throws Exception {
      doStateTransferInProgressTest(false, true);
   }

   public void testCommitLocalFailure() throws Exception {
      doStateTransferInProgressTest(true, true);
   }

   public void testRollbackRemoteFailure() throws Exception {
      doStateTransferInProgressTest(false, false);
   }

   public void testCommitRemoteFailure() throws Exception {
      doStateTransferInProgressTest(true, false);
   }

   /**
    * Check that the transaction commit/rollback recovers if we receive a StateTransferInProgressException from the remote node
    */
   private void doStateTransferInProgressTest(boolean commit, final boolean failOnOriginator) throws Exception {
      MagicKey k1 = new MagicKey("k1", c1);
      MagicKey k2 = new MagicKey("k2", c2);

      tm(c1).begin();
      c1.put(k1, "v1");
      c1.put(k2, "v2");

      // We split the transaction commit in two phases by calling the TransactionCoordinator methods directly
      TransactionTable txTable = TestingUtil.extractComponent(c1, TransactionTable.class);
      TransactionCoordinator txCoordinator = TestingUtil.extractComponent(c1, TransactionCoordinator.class);

      // Execute the prepare on both nodes
      LocalTransaction localTx = txTable.getLocalTransaction(tm(c1).getTransaction());
      txCoordinator.prepare(localTx);

      final CountDownLatch commitLatch = new CountDownLatch(1);
      Thread worker = new Thread("RehasherSim,StaleLocksWithCommitDuringStateTransferTest") {
         @Override
         public void run() {
            try {
               // Before calling commit we block transactions on one of the nodes to simulate a state transfer
               final StateTransferLock blockFirst = TestingUtil.extractComponent(failOnOriginator ? c1 : c2, StateTransferLock.class);
               final StateTransferLock blockSecond = TestingUtil.extractComponent(failOnOriginator ? c2 : c1, StateTransferLock.class);

               try {
                  blockFirst.acquireExclusiveTopologyLock();
                  blockSecond.acquireExclusiveTopologyLock();

                  commitLatch.countDown();

                  // should be much larger than the lock acquisition timeout
                  Thread.sleep(1000);
               } finally {
                  blockSecond.releaseExclusiveTopologyLock();
                  blockFirst.releaseExclusiveTopologyLock();
               }
            } catch (Throwable t) {
               log.errorf(t, "Error blocking/unblocking transactions");
            }
         }
      };
      worker.start();

      commitLatch.await(10, TimeUnit.SECONDS);

      try {
         // finally commit or rollback the transaction
         if (commit) {
            tm(c1).commit();
         } else {
            tm(c1).rollback();
         }

         // make the transaction manager forget about our tx so that we don't get rollback exceptions in the log
         tm(c1).suspend();
      } finally {
         // don't leak threads
         worker.join();
      }

      // test that we don't leak locks
      assertNotLocked(c1, k1);
      assertNotLocked(c2, k1);
      assertNotLocked(c1, k2);
      assertNotLocked(c2, k2);
   }

   public void testRollbackSuspectFailure() throws Exception {
      doTestSuspect(false);
   }

   public void testCommitSuspectFailure() throws Exception {
      doTestSuspect(true);
   }

   /**
    * Check that the transaction commit/rollback recovers if the remote node dies during the RPC
    */
   private void doTestSuspect(boolean commit) throws Exception {
      MagicKey k1 = new MagicKey("k1", c1);
      MagicKey k2 = new MagicKey("k2", c2);

      tm(c1).begin();
      c1.put(k1, "v1");
      c1.put(k2, "v2");

      // We split the transaction commit in two phases by calling the TransactionCoordinator methods directly
      TransactionTable txTable = TestingUtil.extractComponent(c1, TransactionTable.class);
      TransactionCoordinator txCoordinator = TestingUtil.extractComponent(c1, TransactionCoordinator.class);

      // Execute the prepare on both nodes
      LocalTransaction localTx = txTable.getLocalTransaction(tm(c1).getTransaction());
      txCoordinator.prepare(localTx);

      // Delay the commit on the remote node. Can't used blockNewTransactions because we don't want a StateTransferInProgressException
      InterceptorChain c2ic = TestingUtil.extractComponent(c2, InterceptorChain.class);
      c2ic.addInterceptorBefore(new CommandInterceptor() {
         @Override
         protected Object handleDefault(InvocationContext ctx, VisitableCommand command) throws Throwable {
            if (command instanceof CommitCommand) {
               Thread.sleep(3000);
            }
            return super.handleDefault(ctx, command);
         }
      }, StateTransferInterceptor.class);

      // Schedule the remote node to stop on another thread since the main thread will be busy with the commit call
      Thread worker = new Thread("RehasherSim,StaleLocksWithCommitDuringStateTransferTest") {
         @Override
         public void run() {
            try {
               // should be much larger than the lock acquisition timeout
               Thread.sleep(1000);
               manager(c2).stop();
               // stLock.unblockNewTransactions(1000);
            } catch (InterruptedException e) {
               log.errorf(e, "Error stopping cache");
            }
         }
      };
      worker.start();

      try {
         // finally commit or rollback the transaction
         if (commit) {
            txCoordinator.commit(localTx, false);
         } else {
            txCoordinator.rollback(localTx);
         }

         // make the transaction manager forget about our tx so that we don't get rollback exceptions in the log
         tm(c1).suspend();
      } finally {
         // don't leak threads
         worker.join();
      }

      // test that we don't leak locks
      assertNotLocked(c1, k1);
      assertNotLocked(c1, k2);
   }
}


File: core/src/test/java/org/infinispan/test/AbstractCacheTest.java
package org.infinispan.test;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.fwk.CleanupAfterMethod;
import org.infinispan.test.fwk.CleanupAfterTest;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.util.concurrent.locks.LockManager;

/**
 * Base class for {@link org.infinispan.test.SingleCacheManagerTest} and {@link org.infinispan.test.MultipleCacheManagersTest}.
 *
 * @author Mircea.Markus@jboss.com
 */
public class AbstractCacheTest extends AbstractInfinispanTest {

   public static enum CleanupPhase {
      AFTER_METHOD, AFTER_TEST
   }

   protected CleanupPhase cleanup = CleanupPhase.AFTER_TEST;

   protected boolean cleanupAfterTest() {
      return getClass().getAnnotation(CleanupAfterTest.class) != null || (
              getClass().getAnnotation(CleanupAfterMethod.class) == null &&
                      cleanup == CleanupPhase.AFTER_TEST
      );
   }

   protected boolean cleanupAfterMethod() {
      return getClass().getAnnotation(CleanupAfterMethod.class) != null || (
              getClass().getAnnotation(CleanupAfterTest.class) == null &&
                      cleanup == CleanupPhase.AFTER_METHOD
      );
   }

   public static ConfigurationBuilder getDefaultClusteredCacheConfig(CacheMode mode) {
      return getDefaultClusteredCacheConfig(mode, false, false);
   }

   public static ConfigurationBuilder getDefaultClusteredCacheConfig(CacheMode mode, boolean transactional) {
      return getDefaultClusteredCacheConfig(mode, transactional, false);
   }

   public static ConfigurationBuilder getDefaultClusteredCacheConfig(CacheMode mode, boolean transactional, boolean useCustomTxLookup) {
      ConfigurationBuilder builder = TestCacheManagerFactory.getDefaultCacheConfiguration(transactional, useCustomTxLookup);
      builder.
         clustering()
            .cacheMode(mode)
            .stateTransfer().fetchInMemoryState(mode.isClustered())
         .transaction().syncCommitPhase(true).syncRollbackPhase(true)
         .cacheStopTimeout(0L);

      if (mode.isSynchronous())
         builder.clustering().sync();
      else
         builder.clustering().async();

      if (mode.isReplicated()) {
         // only one segment is supported for REPL tests now because some old tests still expect a single primary owner
         builder.clustering().hash().numSegments(1);
      }

      return builder;
   }

   protected boolean xor(boolean b1, boolean b2) {
      return (b1 || b2) && !(b1 && b2);
   }

   protected void assertNotLocked(final Cache cache, final Object key) {
      //lock release happens async, hence the eventually...
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return !checkLocked(cache, key);
         }
      });
   }

   protected void assertLocked(Cache cache, Object key) {
      assert checkLocked(cache, key) : "expected key '" + key + "' to be locked on cache " + cache + ", but it is not";
   }

   protected boolean checkLocked(Cache cache, Object key) {
      LockManager lockManager = TestingUtil.extractLockManager(cache);
      return lockManager.isLocked(key);
   }

   public EmbeddedCacheManager manager(Cache c) {
      return c.getCacheManager();
   }
}


File: core/src/test/java/org/infinispan/test/AbstractInfinispanTest.java
package org.infinispan.test;

import org.infinispan.util.DefaultTimeService;
import org.infinispan.util.TimeService;
import org.infinispan.util.concurrent.ConcurrentHashSet;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.AfterTest;

import javax.transaction.TransactionManager;
import java.util.List;
import java.util.Set;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import static org.testng.AssertJUnit.assertTrue;


/**
 * AbstractInfinispanTest is a superclass of all Infinispan tests.
 *
 * @author Vladimir Blagojevic
 * @author Mircea.Markus@jboss.com
 * @since 4.0
 */
public class AbstractInfinispanTest {

   protected final Log log = LogFactory.getLog(getClass());

   private final Set<TrackingThreadFactory> requestedThreadFactories = new ConcurrentHashSet<>();

   private final TrackingThreadFactory defaultThreadFactory = (TrackingThreadFactory)getTestThreadFactory("ForkThread");
   private final ThreadPoolExecutor defaultExecutorService = new ThreadPoolExecutor(0, Integer.MAX_VALUE,
                                                                                 60L, TimeUnit.SECONDS,
                                                                                 new SynchronousQueue<Runnable>(),
                                                                                 defaultThreadFactory);

   public static final TimeService TIME_SERVICE = new DefaultTimeService();

   @AfterTest(alwaysRun = true)
   protected void killSpawnedThreads() {
      List<Runnable> runnables = defaultExecutorService.shutdownNow();
      if (!runnables.isEmpty()) {
         log.errorf("There were runnables %s left uncompleted in test %s", runnables, getClass().getSimpleName());
      }

      for (TrackingThreadFactory factory : requestedThreadFactories) {
         checkFactoryForLeaks(factory);
      }
   }

   @AfterMethod
   protected void checkThreads() {
      int activeTasks = defaultExecutorService.getActiveCount();
      if (activeTasks != 0) {
         log.errorf("There were %i active tasks found in the test executor service for class %s", activeTasks,
                    getClass().getSimpleName());
      }
   }

   private void checkFactoryForLeaks(TrackingThreadFactory factory) {
      Set<Thread> threads = factory.getCreatedThreads();
      for (Thread t : threads) {
         if (t.isAlive() && !t.isInterrupted()) {
            log.warnf("There was a thread % still alive after test completion - interrupted it", t);
            t.interrupt();
         }
      }
   }

   protected void eventually(Condition ec, long timeoutMillis) {
      eventually(ec, timeoutMillis, TimeUnit.MILLISECONDS);
   }

   /**
    * @deprecated Use {@link #eventually(Condition, long, long, TimeUnit)} instead.
    */
   @Deprecated
   protected void eventually(Condition ec, long timeoutMillis, int loops) {
      if (loops <= 0) {
         throw new IllegalArgumentException("Number of loops must be positive");
      }
      long sleepDuration = timeoutMillis / loops + 1;
      eventually(ec, timeoutMillis, sleepDuration, TimeUnit.MILLISECONDS);
   }

   protected void eventually(Condition ec, long timeout, TimeUnit unit) {
      eventually(ec, timeout, 500, unit);
   }

   protected void eventually(Condition ec, long timeout, long pollInterval, TimeUnit unit) {
      if (pollInterval <= 0) {
         throw new IllegalArgumentException("Check interval must be positive");
      }
      try {
         long expectedEndTime = System.nanoTime() + TimeUnit.NANOSECONDS.convert(timeout, unit);
         long sleepMillis = TimeUnit.MILLISECONDS.convert(pollInterval, unit);
         while (expectedEndTime - System.nanoTime() > 0) {
            if (ec.isSatisfied()) return;
            Thread.sleep(sleepMillis);
         }
         assertTrue(ec.isSatisfied());
      } catch (Exception e) {
         throw new RuntimeException("Unexpected!", e);
      }
   }

   /**
    * This method will actually spawn a fresh thread and will not use underlying pool.  The
    * {@link org.infinispan.test.AbstractInfinispanTest#fork(Runnable)} should be preferred
    * unless you require explicit access to the thread.
    * @param r The runnable to run
    * @return The created thread
    */
   protected Thread inNewThread(Runnable r) {
      final Thread t = defaultThreadFactory.newThread(new RunnableWrapper(r));
      log.tracef("About to start thread '%s' as child of thread '%s'", t.getName(), Thread.currentThread().getName());
      t.start();
      return t;
   }

   protected Future<?> fork(Runnable r) {
      return defaultExecutorService.submit(new RunnableWrapper(r));
   }

   protected <T> Future<T> fork(Runnable r, T result) {
      return defaultExecutorService.submit(new RunnableWrapper(r), result);
   }

   protected <T> Future<T> fork(Callable<T> c) {
      return defaultExecutorService.submit(new LoggingCallable<>(c));
   }

   /**
    * Returns an executor service that can  be used by tests which has it's lifecycle handled
    * by the test container itself.
    * @param <V> The desired type provided by the user of the CompletionService
    * @return The completion service that should be used by tests
    */
   protected <V> CompletionService<V> completionService() {
      return new ExecutorCompletionService<>(defaultExecutorService);
   }

   /**
    * This should normally not be used, use the {@link AbstractInfinispanTest#completionService()}
    * method when an executor is required.  Although if you want a limited set of threads this could
    * still be useful for something like {@link java.util.concurrent.Executors#newFixedThreadPool(int, java.util.concurrent.ThreadFactory)} or
    * {@link java.util.concurrent.Executors#newSingleThreadExecutor(java.util.concurrent.ThreadFactory)}
    * @param prefix The prefix starting for the thread factory
    * @return A thread factory that will use the same naming schema as the other methods
    */
   protected ThreadFactory getTestThreadFactory(final String prefix) {
      TrackingThreadFactory ttf = new TrackingThreadFactory(getRealThreadFactory(prefix));
      requestedThreadFactories.add(ttf);
      return ttf;
   }

   private ThreadFactory getRealThreadFactory(final String prefix) {
      final String className = getClass().getSimpleName();

      return new ThreadFactory() {
         private final AtomicInteger counter = new AtomicInteger(0);

         @Override
         public Thread newThread(Runnable r) {
            String threadName = prefix + "-" + counter.incrementAndGet() + "," + className;
            return new Thread(r, threadName);
         }
      };
   }

   /**
    * This will run the various callables at approximately the same time by ensuring they all start before
    * allowing the callables to proceed.  The callables may not be running yet at the offset of the return of
    * the completion service.
    *
    * This method doesn't allow distinction between which Future applies to which Callable.  If that is required
    * it is suggested to use {@link AbstractInfinispanTest#completionService()} and retrieve the future
    * directly when submitting the Callable while also wrapping your callables in something like
    * {@link org.infinispan.test.AbstractInfinispanTest.ConcurrentCallable} to ensure your callables will be invoked
    * at approximately the same time.
    * @param task1 First task to add - required to ensure at least 2 callables are provided
    * @param task2 Second task to add - required to ensure at least 2 callables are provided
    * @param tasks The callables to run
    * @param <V> The type of callables
    * @return The completion service that can be used to query when a callable completes
    */
   protected <V> CompletionService<V> runConcurrentlyWithCompletionService(Callable<? extends V> task1,
                                                                           Callable<? extends V> task2,
                                                                           Callable<? extends V>... tasks) {
      if (task1 == null) {
         throw new NullPointerException("Task1 was not provided!");
      }
      if (task2 == null) {
         throw new NullPointerException("Task2 was not provided!");
      }
      Callable[] callables = new Callable[tasks.length + 2];
      int i = 0;
      callables[i++] = task1;
      callables[i++] = task2;
      for (Callable<? extends V> callable : tasks) {
         callables[i++] = callable;
      }
      return runConcurrentlyWithCompletionService(callables);
   }

   /**
    * This will run the various callables at approximately the same time by ensuring they all start before
    * allowing the callables to proceed.  The callables may not be running yet at the offset of the return of
    * the completion service.
    *
    * This method doesn't allow distinction between which Future applies to which Callable.  If that is required
    * it is suggested to use {@link AbstractInfinispanTest#completionService()} and retrieve the future
    * directly when submitting the Callable while also wrapping your callables in something like
    * {@link org.infinispan.test.AbstractInfinispanTest.ConcurrentCallable} to ensure your callables will be invoked
    * at approximately the same time.
    * @param tasks The callables to run.  Note the type isn't provided since it is difficult
    * @param <V> The type of callables
    * @return The completion service that can be used to query when a callable completes
    */
   protected <V> CompletionService<V> runConcurrentlyWithCompletionService(Callable[] tasks) {
      if (tasks.length == 0) {
         throw new IllegalArgumentException("Provided tasks array was empty");
      }
      CompletionService<V> completionService = completionService();
      CyclicBarrier barrier = new CyclicBarrier(tasks.length);
      for (int i = 0; i < tasks.length; i++) {
         completionService.submit(new ConcurrentCallable<V>(new LoggingCallable<V>(tasks[i]), barrier));
      }

      return completionService;
   }

   /**
    * This will run the various callables at approximately the same time by ensuring they all start before
    * allowing the callables to proceed.  All callables will be ensure to completion else a TimeoutException will be thrown
    * @param task1 First task to add - required to ensure at least 2 callables are provided
    * @param task2 Second task to add - required to ensure at least 2 callables are provided
    * @param tasks The callables to run
    * @param <V> The type of callabels
    * @throws InterruptedException Thrown if this thread is interrupted
    * @throws ExecutionException Thrown if one of the callables throws any kind of Throwable.  The
    *         thrown Throwable will be wrapped by this exception
    * @throws TimeoutException If one of the callables doesn't complete within 10 seconds
    */
   protected <V> void runConcurrently(Callable<? extends V> task1, Callable<? extends V> task2,
                                      Callable<? extends V>... tasks) throws InterruptedException,ExecutionException,
                                                                             TimeoutException {
      CompletionService<V> completionService = runConcurrentlyWithCompletionService(task1, task2, tasks);

      waitForCompletionServiceTasks(completionService, tasks.length + 2);
   }

   /**
    * This will run the various callables at approximately the same time by ensuring they all start before
    * allowing the callables to proceed.  All callables will be ensure to completion else a TimeoutException will be thrown
    * @param tasks The callables to run
    * @param <V> The type of callables
    * @throws InterruptedException Thrown if this thread is interrupted
    * @throws ExecutionException Thrown if one of the callables throws any kind of Throwable.  The
    *         thrown Throwable will be wrapped by this exception
    * @throws TimeoutException If one of the callables doesn't complete within 10 seconds
    */
   protected <V> void runConcurrently(Callable<? extends V>[] tasks) throws InterruptedException,ExecutionException,
                                                                             TimeoutException {
      CompletionService<V> completionService = runConcurrentlyWithCompletionService(tasks);

      waitForCompletionServiceTasks(completionService, tasks.length);
   }

   /**
    * Waits for the desired numberOfTasks in the completion service to complete one at a time polling for each up to
    * 10 seconds.  If one of the tasks produces an exception, the first one is rethrown wrapped in a ExecutionException
    * after all tasks have completed.
    * @param completionService The completion service that had tasks submitted to that total numberOfTasks
    * @param numberOfTasks How many tasks have been sent to the service
    * @throws InterruptedException If this thread is interruped while waiting for the tasks to complete
    * @throws ExecutionException Thrown if one of the tasks produces an exception.  The first encounted exception will
    *         be thrown
    * @throws TimeoutException If a task is not found to complete within 10 seconds of the previously completed or the
    *         first task.
    */
   protected void waitForCompletionServiceTasks(CompletionService<?> completionService, int numberOfTasks)
         throws InterruptedException,ExecutionException, TimeoutException {
      if (completionService == null) {
         throw new NullPointerException("Provided completionService cannot be null");
      }
      if (numberOfTasks <= 0) {
         throw new IllegalArgumentException("Provided numberOfTasks cannot be less than or equal to 0");
      }
      // check for any errors
      ExecutionException exception = null;
      for (int i = 0; i < numberOfTasks; i++) {
         try {
            Future<?> future = completionService.poll(10, TimeUnit.SECONDS);
            if (future == null) {
               throw new TimeoutException("Concurrent task didn't complete within 10 seconds!");
            }
            // No timeout since it is guaranteed to be done
            future.get();
         } catch (ExecutionException e) {
            log.debug("Exception in concurrent task", e);
            if (exception == null) {
               exception = e;
            }
         }
      }

      // If there was an exception throw the last one
      if (exception != null) {
         throw exception;
      }
   }

   /**
    * This will run the callable at approximately the same time in different thrads by ensuring they all start before
    * allowing the callables to proceed.  All callables will be ensure to completion else a TimeoutException will be thrown
    *
    * The callable itself should be thread safe since it will be invoked from multiple threads.
    * @param callable The callable to run multiple times
    * @param <V> The type of callable
    * @throws InterruptedException Thrown if this thread is interrupted
    * @throws ExecutionException Thrown if one of the callables throws any kind of Throwable.  The
    *         thrown Throwable will be wrapped by this exception
    * @throws TimeoutException If one of the callables doesn't complete within 10 seconds
    */
   protected <V> void runConcurrently(Callable<V> callable, int invocationCount) throws InterruptedException,
                                                                                        ExecutionException,
                                                                                        TimeoutException {
      if (callable == null) {
         throw new NullPointerException("Provided callable cannot be null");
      }
      if (invocationCount <= 0) {
         throw new IllegalArgumentException("Provided invocationCount cannot be less than or equal to 0");
      }
      CompletionService<V> completionService = completionService();
      CyclicBarrier barrier = new CyclicBarrier(invocationCount);

      for (int i = 0; i < invocationCount; ++i) {
         completionService.submit(new ConcurrentCallable<>(new LoggingCallable<>(callable), barrier));
      }

      waitForCompletionServiceTasks(completionService, invocationCount);
   }

   private final class TrackingThreadFactory implements ThreadFactory {
      private final ThreadFactory realFactory;
      private final Set<Thread> createdThreads = new ConcurrentHashSet<>();

      public TrackingThreadFactory(ThreadFactory factory) {
         this.realFactory = factory;
      }

      @Override
      public Thread newThread(Runnable r) {
         Thread thread = realFactory.newThread(r);
         createdThreads.add(thread);
         return thread;
      }

      public Set<Thread> getCreatedThreads() {
         return createdThreads;
      }
   }

   /**
    * A callable that will first await on the provided barrier before calling the provided callable.
    * This is useful to have a better attempt at multiple threads ran at the same time, but still is
    * no guarantee since this is controlled by the thread scheduler.
    * @param <V>
    */
   public final class ConcurrentCallable<V> implements Callable<V> {
      private final Callable<? extends V> callable;
      private final CyclicBarrier barrier;

      public ConcurrentCallable(Callable<? extends V> callable, CyclicBarrier barrier) {
         this.callable = callable;
         this.barrier = barrier;
      }

      @Override
      public V call() throws Exception {
         log.trace("About to wait on provided barrier");
         try {
            barrier.await(10, TimeUnit.SECONDS);
            log.trace("Completed await on provided barrier");
         } catch (InterruptedException | TimeoutException | BrokenBarrierException e) {
            log.tracef("Barrier await was broken due to exception", e);
         }
         return callable.call();
      }
   }

   public final class RunnableWrapper implements Runnable {

      final Runnable realOne;

      public RunnableWrapper(Runnable realOne) {
         this.realOne = realOne;
      }

      @Override
      public void run() {
         try {
            log.trace("Started fork runnable..");
            realOne.run();
            log.debug("Exiting fork runnable.");
         } catch (Throwable e) {
            log.debug("Exiting fork runnable due to exception", e);
         }
      }
   }


   protected void eventually(Condition ec) {
      eventually(ec, 10000);
   }

   protected interface Condition {
      public boolean isSatisfied() throws Exception;
   }

   private class LoggingCallable<T> implements Callable<T> {
      private final Callable<? extends T> c;

      public LoggingCallable(Callable<? extends T> c) {
         this.c = c;
      }

      @Override
      public T call() throws Exception {
         try {
            log.trace("Started fork callable..");
            T result = c.call();
            log.debug("Exiting fork callable.");
            return result;
         } catch (Exception e) {
            log.debug("Exiting fork callable due to exception", e);
            throw e;
         }
      }
   }

   public void safeRollback(TransactionManager transactionManager) {
      try {
         transactionManager.rollback();
      } catch (Exception e) {
         //ignored
      }
   }
}


File: core/src/test/java/org/infinispan/test/MultipleCacheManagersTest.java
package org.infinispan.test;

import org.infinispan.AdvancedCache;
import org.infinispan.Cache;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.configuration.global.GlobalConfigurationBuilder;
import org.infinispan.container.DataContainer;
import org.infinispan.distribution.MagicKey;
import org.infinispan.distribution.rehash.XAResourceAdapter;
import org.infinispan.manager.CacheContainer;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.remoting.transport.Address;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.test.fwk.TransportFlags;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.util.concurrent.locks.LockManager;
import org.testng.annotations.AfterClass;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;

import javax.transaction.RollbackException;
import javax.transaction.SystemException;
import javax.transaction.Transaction;
import javax.transaction.TransactionManager;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;


/**
 * Base class for tests that operates on clusters of caches. The way tests extending this class operates is:
 * <pre>
 *    1) created cache managers before tests start. The cache managers are only created once
 *    2) after each test method runs, the cache instances are being cleared
 *    3) next test method will run on same cacheManager instance. This way the test is much faster, as CacheManagers
 *       are expensive to create.
 * </pre>
 * If, however, you would like your cache managers destroyed after every <i>test method</i> instead of the </i>test
 * class</i>, you could set the <tt>cleanup</tt> field to {@link MultipleCacheManagersTest.CleanupPhase#AFTER_METHOD} in
 * your test's constructor.  E.g.:
 * <pre>
 * <p/>
 * public void MyTest extends MultipleCacheManagersTest {
 *    public MyTest() {
 *       cleanup =  CleanupPhase.AFTER_METHOD;
 *    }
 * }
 * <p/>
 * </pre>
 * <p/>
 * Note that this will cause {@link #createCacheManagers()}  to be called before each method.
 *
 * @author Mircea.Markus@jboss.com
 */
public abstract class MultipleCacheManagersTest extends AbstractCacheTest {

   protected List<EmbeddedCacheManager> cacheManagers = Collections.synchronizedList(new ArrayList<EmbeddedCacheManager>());
   protected IdentityHashMap<Cache<?, ?>, ReplListener> listeners = new IdentityHashMap<Cache<?, ?>, ReplListener>();

   @BeforeClass(alwaysRun = true)
   public void createBeforeClass() throws Throwable {
      if (cleanupAfterTest()) callCreateCacheManagers();
   }

   private void callCreateCacheManagers() throws Throwable {
      try {
         log.debug("Creating cache managers");
         createCacheManagers();
         log.debug("Cache managers created, ready to start the test");
      } catch (Throwable th) {
         log.error("Error in test setup: ", th);
         throw th;
      }
   }

   @BeforeMethod(alwaysRun = true)
   public void createBeforeMethod() throws Throwable {
      if (cleanupAfterMethod()) callCreateCacheManagers();
   }

   @AfterClass(alwaysRun = true)
   protected void destroy() {
      if (cleanupAfterTest()) TestingUtil.killCacheManagers(cacheManagers);
      cacheManagers.clear();
      listeners.clear();
   }

   @AfterMethod(alwaysRun=true)
   protected void clearContent() throws Throwable {
      if (cleanupAfterTest()) {
//         assertSupportedConfig();
         log.debug("*** Test method complete; clearing contents on all caches.");
         if (cacheManagers.isEmpty())
            throw new IllegalStateException("No caches registered! Use registerCacheManager(Cache... caches) to do that!");
         TestingUtil.clearContent(cacheManagers);
      } else {
         TestingUtil.killCacheManagers(cacheManagers);
         cacheManagers.clear();
      }
   }

   /**
    * Reason: after a tm.commit is run, multiple tests assert that the new value (as within the committing transaction)
    * is present on a remote cache (i.e. not on the cache on which tx originated). If we don't use sync commit,
    * than this (i.e. actual commit of the tx on the remote cache) might happen after the tm.commit() returns,
    * and result in an intermittent failure for the assertion
    */
   protected void assertSupportedConfig() {
      for (EmbeddedCacheManager cm : cacheManagers) {
         for (Cache<?, ?> cache : TestingUtil.getRunningCaches(cm)) {
            Configuration config = cache.getCacheConfiguration();
            try {
               assert config.transaction().syncCommitPhase() : "Must use a sync commit phase!";
               assert config.transaction().syncRollbackPhase(): "Must use a sync rollback phase!";
            } catch (AssertionError e) {
               log.error("Invalid config for cache in test: " + getClass().getName());
               throw e;
            }
         }
      }
   }

   final protected void registerCacheManager(CacheContainer... cacheContainers) {
      for (CacheContainer ecm : cacheContainers) {
         this.cacheManagers.add((EmbeddedCacheManager) ecm);
      }
   }

   /**
    * Creates a new cache manager, starts it, and adds it to the list of known cache managers on the current thread.
    * Uses a default clustered cache manager global config.
    *
    * @return the new CacheManager
    */
   protected EmbeddedCacheManager addClusterEnabledCacheManager() {
      return addClusterEnabledCacheManager(new TransportFlags());
   }

   /**
    * Creates a new cache manager, starts it, and adds it to the list of known
    * cache managers on the current thread. Uses a default clustered cache
    * manager global config.
    *
    * @param flags properties that allow transport stack to be tweaked
    * @return the new CacheManager
    */
   protected EmbeddedCacheManager addClusterEnabledCacheManager(TransportFlags flags) {
      EmbeddedCacheManager cm = TestCacheManagerFactory.createClusteredCacheManager(new ConfigurationBuilder(), flags);
      cacheManagers.add(cm);
      return cm;
   }

   /**
    * Creates a new non-transactional cache manager, starts it, and adds it to the list of known cache managers on the
    * current thread.  Uses a default clustered cache manager global config.
    *
    * @param defaultConfig default cfg to use
    * @return the new CacheManager
    */
   protected EmbeddedCacheManager addClusterEnabledCacheManager(ConfigurationBuilder defaultConfig) {
      return addClusterEnabledCacheManager(defaultConfig, new TransportFlags());
   }

   protected EmbeddedCacheManager addClusterEnabledCacheManager(GlobalConfigurationBuilder globalBuilder, ConfigurationBuilder defaultConfig) {
      return addClusterEnabledCacheManager(globalBuilder, defaultConfig, new TransportFlags());
   }

   /**
    * Creates a new optionally transactional cache manager, starts it, and adds it to the list of known cache managers on
    * the current thread.  Uses a default clustered cache manager global config.
    *
    * @param defaultConfig default cfg to use
    * @return the new CacheManager
    */
   protected EmbeddedCacheManager addClusterEnabledCacheManager(ConfigurationBuilder builder, TransportFlags flags) {
      EmbeddedCacheManager cm = TestCacheManagerFactory.createClusteredCacheManager(builder, flags);
      cacheManagers.add(cm);
      return cm;
   }

   protected EmbeddedCacheManager addClusterEnabledCacheManager(GlobalConfigurationBuilder globalBuilder, ConfigurationBuilder builder, TransportFlags flags) {
      EmbeddedCacheManager cm = TestCacheManagerFactory.createClusteredCacheManager(globalBuilder, builder, flags);
      cacheManagers.add(cm);
      return cm;
   }

   /**
    * Creates a new cache manager, starts it, and adds it to the list of known cache managers on the current thread.
    * @param mode cache mode to use
    * @param transactional if true, the configuration will be decorated with necessary transactional settings
    * @return an embedded cache manager
    */

   protected void createCluster(ConfigurationBuilder builder, int count) {
      for (int i = 0; i < count; i++) addClusterEnabledCacheManager(builder);
   }

   protected void createCluster(GlobalConfigurationBuilder globalBuilder, ConfigurationBuilder builder, int count) {
      for (int i = 0; i < count; i++) addClusterEnabledCacheManager(new GlobalConfigurationBuilder().read(globalBuilder.build()), builder);
   }

   protected void defineConfigurationOnAllManagers(String cacheName, ConfigurationBuilder b) {
      for (EmbeddedCacheManager cm : cacheManagers) {
         cm.defineConfiguration(cacheName, b.build());
      }
   }

   protected  <K, V> List<Cache<K, V>> getCaches(String cacheName) {
      List<Cache<K, V>> caches = new ArrayList<Cache<K, V>>();
      List<EmbeddedCacheManager> managers = new ArrayList<>(cacheManagers);
      for (EmbeddedCacheManager cm : managers) {
         Cache<K, V> c;
         if (cacheName == null)
            c = cm.getCache();
         else
            c = cm.getCache(cacheName);
         caches.add(c);
      }
      return caches;
   }

   protected void waitForClusterToForm(String cacheName) {
      List<Cache<Object, Object>> caches = getCaches(cacheName);
      Cache<Object, Object> cache = caches.get(0);
      TestingUtil.blockUntilViewsReceived(30000, caches);
      if (cache.getCacheConfiguration().clustering().cacheMode().isClustered()) {
         TestingUtil.waitForRehashToComplete(caches);
      }
   }

   protected void waitForClusterToForm() {
      waitForClusterToForm((String) null);
   }

   protected void waitForClusterToForm(String... names) {
      for (String name : names) {
         waitForClusterToForm(name);
      }
   }

   protected TransactionManager tm(Cache<?, ?> c) {
      return c.getAdvancedCache().getTransactionManager();
   }

   protected TransactionManager tm(int i, String cacheName) {
      return cache(i, cacheName ).getAdvancedCache().getTransactionManager();
   }

   protected TransactionManager tm(int i) {
      return cache(i).getAdvancedCache().getTransactionManager();
   }

   protected Transaction tx(int i) {
      try {
         return cache(i).getAdvancedCache().getTransactionManager().getTransaction();
      } catch (SystemException e) {
         throw new RuntimeException(e);
      }
   }

   protected <K, V> List<Cache<K, V>> createClusteredCaches(
         int numMembersInCluster, String cacheName, ConfigurationBuilder builder) {
      return createClusteredCaches(numMembersInCluster, cacheName, builder, new TransportFlags());
   }

   protected <K, V> List<Cache<K, V>> createClusteredCaches(
         int numMembersInCluster, String cacheName, ConfigurationBuilder builder, TransportFlags flags) {
      List<Cache<K, V>> caches = new ArrayList<Cache<K, V>>(numMembersInCluster);
      for (int i = 0; i < numMembersInCluster; i++) {
         EmbeddedCacheManager cm = addClusterEnabledCacheManager(flags);
         cm.defineConfiguration(cacheName, builder.build());
         Cache<K, V> cache = cm.getCache(cacheName);
         caches.add(cache);
      }
      waitForClusterToForm(cacheName);
      return caches;
   }

   protected <K, V> List<Cache<K, V>> createClusteredCaches(int numMembersInCluster,
                                                            ConfigurationBuilder defaultConfigBuilder) {
      List<Cache<K, V>> caches = new ArrayList<Cache<K, V>>(numMembersInCluster);
      for (int i = 0; i < numMembersInCluster; i++) {
         EmbeddedCacheManager cm = addClusterEnabledCacheManager(defaultConfigBuilder);
         Cache<K, V> cache = cm.getCache();
         caches.add(cache);

      }
      waitForClusterToForm();
      return caches;
   }

   protected <K, V> List<Cache<K, V>> createClusteredCaches(int numMembersInCluster,
                                                            ConfigurationBuilder defaultConfig,
                                                            TransportFlags flags) {
      List<Cache<K, V>> caches = new ArrayList<Cache<K, V>>(numMembersInCluster);
      for (int i = 0; i < numMembersInCluster; i++) {
         EmbeddedCacheManager cm = addClusterEnabledCacheManager(defaultConfig, flags);
         Cache<K, V> cache = cm.getCache();
         caches.add(cache);
      }
      waitForClusterToForm();
      return caches;
   }

   /**
    * Create cacheNames.lenght in each CacheManager (numMembersInCluster cacheManagers).
    *
    * @param numMembersInCluster
    * @param defaultConfigBuilder
    * @param cacheNames
    * @return A list with size numMembersInCluster containing a list of cacheNames.length caches
    */
   protected <K, V> List<List<Cache<K, V>>> createClusteredCaches(int numMembersInCluster,
         ConfigurationBuilder defaultConfigBuilder, String[] cacheNames) {
      List<List<Cache<K, V>>> allCaches = new ArrayList<List<Cache<K, V>>>(numMembersInCluster);
      for (int i = 0; i < numMembersInCluster; i++) {
         EmbeddedCacheManager cm = addClusterEnabledCacheManager(defaultConfigBuilder);
         List<Cache<K, V>> currentCacheManagerCaches = new ArrayList<Cache<K, V>>(cacheNames.length);

         for (String cacheName : cacheNames) {
            Cache<K, V> cache = cm.getCache(cacheName);
            currentCacheManagerCaches.add(cache);
         }
         allCaches.add(currentCacheManagerCaches);
      }
      waitForClusterToForm(cacheNames);
      return allCaches;
   }

   protected ReplListener replListener(Cache<?, ?> cache) {
      ReplListener listener = listeners.get(cache);
      if (listener == null) {
         listener = new ReplListener(cache);
         listeners.put(cache, listener);
      }
      return listener;
   }

   protected EmbeddedCacheManager manager(int i) {
      return cacheManagers.get(i);
   }

   public EmbeddedCacheManager manager(Address a) {
      for (EmbeddedCacheManager cm : cacheManagers) {
         if (cm.getAddress().equals(a)) {
            return cm;
         }
      }
      throw new IllegalArgumentException(a + " is not a valid cache manager address!");
   }

   public int managerIndex(Address a) {
      for (int i = 0; i < cacheManagers.size(); i++) {
         EmbeddedCacheManager cm = cacheManagers.get(i);
         if (cm.getAddress().equals(a)) {
            return i;
         }
      }
      throw new IllegalArgumentException(a + " is not a valid cache manager address!");
   }

   protected <K, V> Cache<K, V> cache(int managerIndex, String cacheName) {
      return manager(managerIndex).getCache(cacheName);
   }

   protected void assertClusterSize(String message, int size) {
      for (EmbeddedCacheManager cm : cacheManagers) {
         assert cm.getMembers() != null && cm.getMembers().size() == size : message;
      }
   }

   protected void removeCacheFromCluster(String cacheName) {
      for (EmbeddedCacheManager cm : cacheManagers) {
         TestingUtil.killCaches(cm.getCache(cacheName));
      }
   }

   /**
    * Returns the default cache from that manager.
    */
   protected <A, B> Cache<A, B> cache(int index) {
      return manager(index).getCache();
   }

   protected DataContainer dataContainer(int index) {
      return advancedCache(index).getDataContainer();
   }


   /**
    * Create the cache managers you need for your test.  Note that the cache managers you create *must* be created using
    * {@link #addClusterEnabledCacheManager()}
    */
   protected abstract void createCacheManagers() throws Throwable;

   protected Address address(int cacheIndex) {
      return manager(cacheIndex).getAddress();
   }

   protected <A, B> AdvancedCache<A, B> advancedCache(int i) {
      return this.<A,B>cache(i).getAdvancedCache();
   }

   protected <A, B> AdvancedCache<A, B> advancedCache(int i, String cacheName) {
      return this.<A, B>cache(i, cacheName).getAdvancedCache();
   }

   protected <K, V> List<Cache<K, V>> caches(String name) {
      return getCaches(name);
   }

   protected <K, V> List<Cache<K, V>> caches() {
      return caches(null);
   }

   protected Address address(Cache<?, ?> c) {
      return c.getAdvancedCache().getRpcManager().getAddress();
   }

   protected LockManager lockManager(int i) {
      return TestingUtil.extractLockManager(cache(i));
   }

   protected LockManager lockManager(int i, String cacheName) {
      return TestingUtil.extractLockManager(getCache(i, cacheName));
   }

   public List<EmbeddedCacheManager> getCacheManagers() {
      return cacheManagers;
   }

   /**
    * Kills the cache manager with the given index and waits for the new cluster to form.
    */
   protected void killMember(int cacheIndex) {
      killMember(cacheIndex, null);
   }

   /**
    * Kills the cache manager with the given index and waits for the new cluster to form using the provided cache
    */
   protected void killMember(int cacheIndex, String cacheName) {
      List<Cache<Object, Object>> caches = caches(cacheName);
      caches.remove(cacheIndex);
      manager(cacheIndex).stop();
      cacheManagers.remove(cacheIndex);
      if (caches.size() > 0) {
         TestingUtil.blockUntilViewsReceived(60000, false, caches);
         TestingUtil.waitForRehashToComplete(caches);
      }
   }

   /**
    * Creates a {@link org.infinispan.affinity.KeyAffinityService} and uses it for generating a key that maps to the given address.
    * @param nodeIndex the index of tha cache where to be the main data owner of the returned key
    */
   protected Object getKeyForCache(int nodeIndex) {
      final Cache<Object, Object> cache = cache(nodeIndex);
      return getKeyForCache(cache);
   }

   protected Object getKeyForCache(int nodeIndex, String cacheName) {
      final Cache<Object, Object> cache = cache(nodeIndex, cacheName);
      return getKeyForCache(cache);
   }

   protected Object getKeyForCache(Cache<?, ?> cache) {
      return new MagicKey(cache);
   }

   protected void assertNotLocked(final String cacheName, final Object key) {
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            boolean aNodeIsLocked = false;
            for (int i = 0; i < caches(cacheName).size(); i++) {
               final boolean isLocked = lockManager(i, cacheName).isLocked(key);
               if (isLocked) log.trace(key + " is locked on cache index " + i + " by " + lockManager(i, cacheName).getOwner(key));
               aNodeIsLocked = aNodeIsLocked || isLocked;
            }
            return !aNodeIsLocked;
         }
      });
   }

   protected void assertNotLocked(final Object key) {
      assertNotLocked((String)null, key);
   }

   protected boolean checkTxCount(int cacheIndex, int localTx, int remoteTx) {
      final int localTxCount = TestingUtil.getTransactionTable(cache(cacheIndex)).getLocalTxCount();
      final int remoteTxCount = TestingUtil.getTransactionTable(cache(cacheIndex)).getRemoteTxCount();
      log.tracef("Cache index %s, local tx %4s, remote tx %4s \n", cacheIndex, localTxCount, remoteTxCount);
      return localTxCount == localTx && remoteTxCount == remoteTx;
   }

   protected void assertNotLocked(int cacheIndex, Object key) {
      assertNotLocked(cache(cacheIndex), key);
   }

   protected void assertLocked(int cacheIndex, Object key) {
      assertLocked(cache(cacheIndex), key);
   }

   protected boolean checkLocked(int index, Object key) {
      return checkLocked(cache(index), key);
   }

   protected <K, V> Cache<K, V> getLockOwner(Object key) {
      return getLockOwner(key, null);
   }

   protected <K, V> Cache<K, V> getLockOwner(Object key, String cacheName) {
      Configuration c = getCache(0, cacheName).getCacheConfiguration();
      if (c.clustering().cacheMode().isReplicated() || c.clustering().cacheMode().isInvalidation()) {
         return (Cache<K, V>) getCache(0, cacheName); //for replicated caches only the coordinator acquires lock
      }  else {
         if (!c.clustering().cacheMode().isDistributed()) throw new IllegalStateException("This is not a clustered cache!");
         final Address address = getCache(0, cacheName).getAdvancedCache().getDistributionManager().locate(key).get(0);
         for (Cache<?, ?> cache : caches(cacheName)) {
            if (cache.getAdvancedCache().getRpcManager().getTransport().getAddress().equals(address)) {
               return (Cache<K, V>) cache;
            }
         }
         throw new IllegalStateException();
      }
   }

   protected void assertKeyLockedCorrectly(Object key) {
      assertKeyLockedCorrectly(key, null);
   }

   protected void assertKeyLockedCorrectly(Object key, String cacheName) {
      final Cache<?, ?> lockOwner = getLockOwner(key, cacheName);
      assert checkLocked(lockOwner, key);
      for (Cache<?, ?> c : caches(cacheName)) {
         if (c != lockOwner)
            assert !checkLocked(c, key) : "Key " + key + " is locked on cache " + c + " (" + cacheName
                  + ") and it shouldn't";
      }
   }

   private Cache<?, ?> getCache(int index, String name) {
      return name == null ? cache(index) : cache(index, name);
   }

   protected void forceTwoPhase(int cacheIndex) throws SystemException, RollbackException {
      TransactionManager tm = tm(cacheIndex);
      Transaction tx = tm.getTransaction();
      tx.enlistResource(new XAResourceAdapter());
   }

   protected void assertNoTransactions() {
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            for (int i = 0; i < caches().size(); i++) {
               int localTxCount = transactionTable(i).getLocalTxCount();
               int remoteTxCount = transactionTable(i).getRemoteTxCount();
               if (localTxCount != 0 || remoteTxCount != 0) {
                  log.tracef("Local tx=%s, remote tx=%s, for cache %s ",
                        localTxCount, remoteTxCount, i);
                  return false;
               }
            }
            return true;
         }
      });
   }

   protected TransactionTable transactionTable(int cacheIndex) {
      return advancedCache(cacheIndex).getComponentRegistry()
            .getComponent(TransactionTable.class);
   }

   protected void assertEventuallyEquals(
         final int cacheIndex, final Object key, final Object value) {
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            return value == null
                  ? value == cache(cacheIndex).get(key)
                  : value.equals(cache(cacheIndex).get(key));
         }
      });
   }

}


File: core/src/test/java/org/infinispan/test/arquillian/DatagridManager.java
package org.infinispan.test.arquillian;

import java.util.List;
import java.util.concurrent.Future;

import javax.transaction.RollbackException;
import javax.transaction.SystemException;
import javax.transaction.Transaction;
import javax.transaction.TransactionManager;
import org.infinispan.AdvancedCache;
import org.infinispan.Cache;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.manager.CacheContainer;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.AbstractCacheTest;
import org.infinispan.test.AbstractInfinispanTest;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.test.ReplListener;
import org.infinispan.test.TestingUtil;
import org.infinispan.test.fwk.TransportFlags;
import org.infinispan.remoting.transport.Address;
import org.infinispan.util.concurrent.locks.LockManager;

/**
 * An adapter class that enables users to call all important methods from
 * {@link MultipleCacheManagersTest}, {@link AbstractCacheTest} and
 * {@link AbstractInfinispanTest}, changing their visibility to public.
 * Usage of this class is in infinispan-arquillian-container project which
 * enables injecting of this class into a test case and forming a cluster
 * of cache managers/caches.
 *
 * A few methods from super-classes changed their names, mostly because
 * they cannot be overridden. All such methods have comments on them which
 * say "name change".
 *
 *
 * @author <a href="mailto:mgencur@redhat.com">Martin Gencur</a>
 *
 */
public class DatagridManager extends MultipleCacheManagersTest
{

   @Override
   public void destroy() {
      TestingUtil.killCacheManagers(cacheManagers);
      cacheManagers.clear();
      listeners.clear();
      killSpawnedThreads();
   }

   @Override
   protected void createCacheManagers() throws Throwable {
      //empty implementation
   }

   /* ========================= AbstractInfinispanTest methods ================== */

   //name change
   public void waitForCondition(Condition ec, long timeout) {
      eventually(ec, timeout);
   }

   //name change
   public Future<?> forkThread(Runnable r) {
      return fork(r);
   }

   //name change
   public void waitForCondition(Condition ec) {
      eventually(ec);
   }

   /* =========================== AbstractCacheTest methods ====================== */

   //name change
   public boolean xorOp(boolean b1, boolean b2) {
      return xor(b1, b2);
   }

   //name change
   public void assertKeyNotLocked(Cache cache, Object key) {
      assertNotLocked(cache, key);
   }

   //name change
   public void assertKeyLocked(Cache cache, Object key) {
      assertLocked(cache, key);
   }

   //name change
   public boolean checkKeyLocked(Cache cache, Object key) {
      return checkLocked(cache, key);
   }

   /* ===================== MultipleCacheManagersTest methods ==================== */

   @Override
   public void assertSupportedConfig() {
      super.assertSupportedConfig();
   }

   //name change
   public void registerCacheManagers(CacheContainer... cacheContainers) {
      registerCacheManager(cacheContainers);
   }

   @Override
   public EmbeddedCacheManager addClusterEnabledCacheManager() {
      return super.addClusterEnabledCacheManager();
   }

   @Override
   public EmbeddedCacheManager addClusterEnabledCacheManager(TransportFlags flags) {
      return super.addClusterEnabledCacheManager(flags);
   }

   @Override
   public EmbeddedCacheManager addClusterEnabledCacheManager(ConfigurationBuilder defaultConfig) {
      return super.addClusterEnabledCacheManager(defaultConfig);
   }

   @Override
   public EmbeddedCacheManager addClusterEnabledCacheManager(ConfigurationBuilder builder, TransportFlags flags) {
      return super.addClusterEnabledCacheManager(builder, flags);
   }

   @Override
   public void defineConfigurationOnAllManagers(String cacheName, ConfigurationBuilder b) {
      super.defineConfigurationOnAllManagers(cacheName, b);
   }

   @Override
   public void waitForClusterToForm(String cacheName) {
      super.waitForClusterToForm(cacheName);
   }

   @Override
   public void waitForClusterToForm() {
      super.waitForClusterToForm();
   }

   @Override
   public void waitForClusterToForm(String... names) {
      super.waitForClusterToForm(names);
   }

   @Override
   public TransactionManager tm(Cache<?, ?> c) {
      return super.tm(c);
   }

   @Override
   public TransactionManager tm(int i, String cacheName) {
      return super.tm(i, cacheName);
   }

   @Override
   public TransactionManager tm(int i) {
      return super.tm(i);
   }

   @Override
   public Transaction tx(int i) {
      return super.tx(i);
   }

   @Override
   public <K, V> List<Cache<K, V>> createClusteredCaches(
         int numMembersInCluster, String cacheName, ConfigurationBuilder builder) {
      return super.createClusteredCaches(numMembersInCluster, cacheName, builder);
   }

   @Override
   public <K, V> List<Cache<K, V>> createClusteredCaches(
         int numMembersInCluster, String cacheName, ConfigurationBuilder builder, TransportFlags flags) {
      return super.createClusteredCaches(numMembersInCluster, cacheName, builder, flags);
   }

   @Override
   public ReplListener replListener(Cache cache) {
      return super.replListener(cache);
   }

   @Override
   public EmbeddedCacheManager manager(int i) {
      return super.manager(i);
   }

   @Override
   public Cache cache(int managerIndex, String cacheName) {
      return super.cache(managerIndex, cacheName);
   }

   @Override
   public void assertClusterSize(String message, int size) {
      super.assertClusterSize(message, size);
   }

   @Override
   public void removeCacheFromCluster(String cacheName) {
      super.removeCacheFromCluster(cacheName);
   }

   @Override
   public <A, B> Cache<A, B> cache(int index) {
      return super.cache(index);
   }

   @Override
   public Address address(int cacheIndex) {
      return super.address(cacheIndex);
   }

   @Override
   public AdvancedCache advancedCache(int i) {
      return super.advancedCache(i);
   }

   @Override
   public AdvancedCache advancedCache(int i, String cacheName) {
      return super.advancedCache(i, cacheName);
   }

   @Override
   public <K, V> List<Cache<K, V>> caches(String name) {
      return super.caches(name);
   }

   @Override
   public <K, V> List<Cache<K, V>> caches() {
      return super.caches();
   }

   @Override
   public Address address(Cache c) {
      return super.address(c);
   }

   @Override
   public LockManager lockManager(int i) {
      return super.lockManager(i);
   }

   @Override
   public LockManager lockManager(int i, String cacheName) {
      return super.lockManager(i, cacheName);
   }

   @Override
   public List<EmbeddedCacheManager> getCacheManagers() {
      return super.getCacheManagers();
   }

   @Override
   public void killMember(int cacheIndex) {
      super.killMember(cacheIndex);
   }

   @Override
   public Object getKeyForCache(int nodeIndex) {
      return super.getKeyForCache(nodeIndex);
   }

   @Override
   public Object getKeyForCache(int nodeIndex, String cacheName) {
      return super.getKeyForCache(nodeIndex, cacheName);
   }

   @Override
   public Object getKeyForCache(Cache cache) {
      return super.getKeyForCache(cache);
   }

   @Override
   public void assertNotLocked(final String cacheName, final Object key) {
      super.assertNotLocked(cacheName, key);
   }

   @Override
   public void assertNotLocked(final Object key) {
      super.assertNotLocked(key);
   }

   @Override
   public boolean checkTxCount(int cacheIndex, int localTx, int remoteTx) {
      return super.checkTxCount(cacheIndex, localTx, remoteTx);
   }

   @Override
   public void assertNotLocked(int cacheIndex, Object key) {
      super.assertNotLocked(cacheIndex, key);
   }

   @Override
   public void assertLocked(int cacheIndex, Object key) {
      super.assertLocked(cacheIndex, key);
   }

   @Override
   public boolean checkLocked(int index, Object key) {
      return super.checkLocked(index, key);
   }

   @Override
   public Cache getLockOwner(Object key) {
      return super.getLockOwner(key);
   }

   @Override
   public Cache getLockOwner(Object key, String cacheName) {
      return super.getLockOwner(key, cacheName);
   }

   @Override
   public void assertKeyLockedCorrectly(Object key) {
      super.assertKeyLockedCorrectly(key);
   }

   @Override
   public void assertKeyLockedCorrectly(Object key, String cacheName) {
      super.assertKeyLockedCorrectly(key, cacheName);
   }

   @Override
   public void forceTwoPhase(int cacheIndex) throws SystemException, RollbackException {
      super.forceTwoPhase(cacheIndex);
   }

   /* ========== methods simulating those from SingleCacheManagerTest ========== */

   public EmbeddedCacheManager manager() {
      return super.manager(0);
   }

   public <A, B> Cache<A, B> cache() {
      return super.cache(0);
   }

   public TransactionManager tm() {
      return super.cache(0).getAdvancedCache().getTransactionManager();
   }

   public Transaction tx() {
      try {
         return super.cache(0).getAdvancedCache().getTransactionManager().getTransaction();
      } catch (SystemException e) {
         throw new RuntimeException(e);
      }
   }

   public LockManager lockManager(String cacheName) {
      return super.lockManager(0, cacheName);
   }

   public LockManager lockManager() {
      return super.lockManager(0);
   }
}


File: core/src/test/java/org/infinispan/tx/StaleLockAfterTxAbortTest.java
package org.infinispan.tx;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.test.SingleCacheManagerTest;
import org.infinispan.test.fwk.TestCacheManagerFactory;
import org.infinispan.transaction.lookup.DummyTransactionManagerLookup;
import org.infinispan.transaction.tm.DummyTransaction;
import org.infinispan.transaction.tm.DummyTransactionManager;
import org.testng.annotations.Test;

import javax.transaction.Transaction;
import javax.transaction.TransactionManager;
import java.util.concurrent.CountDownLatch;

/**
 * This tests the following pattern:
 * <p/>
 * Thread T1 holds lock for key K. TX1 attempts to lock a key K.  Waits for lock. TM times out the tx and aborts the tx
 * (calls XA.end, XA.rollback). T1 releases lock. Wait a few seconds. Make sure there are no stale locks (i.e., when the
 * thread for TX1 wakes up and gets the lock on K, it then releases and aborts).
 *
 * @author manik
 */
@Test (testName = "tx.StaleLockAfterTxAbortTest", groups = "unit")
public class StaleLockAfterTxAbortTest extends SingleCacheManagerTest {
   final String k = "key";

   @Override
   protected EmbeddedCacheManager createCacheManager() throws Exception {
      ConfigurationBuilder c = getDefaultStandaloneCacheConfig(true);
      c.transaction().transactionManagerLookup(new DummyTransactionManagerLookup()).useSynchronization(false).recovery().disable();
      return TestCacheManagerFactory.createCacheManager(c);
   }

   public void doTest() throws Throwable {
      cache.put(k, "value"); // init value

      assertNotLocked(cache, k);

//      InvocationContextContainerImpl icc = (InvocationContextContainerImpl) TestingUtil.extractComponent(cache, InvocationContextContainer.class);
//      InvocationContext ctx = icc.getInvocationContext();
//      LockManager lockManager = TestingUtil.extractComponent(cache, LockManager.class);
//      lockManager.lockAndRecord(k, ctx);
//      ctx.putLookedUpEntry(k, null);

      DummyTransactionManager dtm = (DummyTransactionManager) tm();
      tm().begin();
      cache.put(k, "some");
      final DummyTransaction transaction = dtm.getTransaction();
      transaction.runPrepare();
      tm().suspend();

      // test that the key is indeed locked.
      assertLocked(cache, k);
      final CountDownLatch txStartedLatch = new CountDownLatch(1);

      TxThread transactionThread = new TxThread(cache, txStartedLatch);

      transactionThread.start();
      txStartedLatch.countDown();
      Thread.sleep(500); // in case the thread needs some time to get to the locking code

      // now abort the tx.
      transactionThread.tm.resume(transactionThread.tx);
      transactionThread.tm.rollback();

      // now release the lock
      tm().resume(transaction);
      transaction.runCommit(true);
      transactionThread.join();

      assertNotLocked(cache, k);
   }

   private class TxThread extends Thread {
      final Cache<Object, Object> cache;
      volatile Transaction tx;
      volatile Exception exception;
      final TransactionManager tm;
      final CountDownLatch txStartedLatch;

      private TxThread(Cache<Object, Object> cache, CountDownLatch txStartedLatch) {
         this.cache = cache;
         this.tx = null;
         this.tm = cache.getAdvancedCache().getTransactionManager();
         this.txStartedLatch = txStartedLatch;
      }

      @Override
      public void run() {
         try {
            // Now start a new tx.
            tm.begin();
            tx = tm.getTransaction();
            log.trace("Started transaction " + tx);
            txStartedLatch.countDown();
            cache.put(k, "v2"); // this should block.
         } catch (Exception e) {
            exception = e;
         }
      }
   }

}


File: core/src/test/java/org/infinispan/tx/TransactionXaAdapterTmIntegrationTest.java
package org.infinispan.tx;

import org.infinispan.Cache;
import org.infinispan.commands.CommandsFactory;
import org.infinispan.commons.equivalence.AnyEquivalence;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.context.InvocationContextFactory;
import org.infinispan.context.TransactionalInvocationContextFactory;
import org.infinispan.interceptors.InterceptorChain;
import org.infinispan.interceptors.locking.ClusteringDependentLogic;
import org.infinispan.transaction.impl.TransactionCoordinator;
import org.infinispan.transaction.tm.DummyBaseTransactionManager;
import org.infinispan.transaction.tm.DummyTransaction;
import org.infinispan.transaction.tm.DummyXid;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.transaction.xa.LocalXaTransaction;
import org.infinispan.transaction.xa.TransactionFactory;
import org.infinispan.transaction.xa.TransactionXaAdapter;
import org.infinispan.transaction.xa.XaTransactionTable;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import javax.transaction.xa.XAException;
import javax.transaction.xa.XAResource;
import java.util.UUID;

import static org.mockito.Mockito.mock;
import static org.testng.AssertJUnit.assertEquals;

/**
 * @author Mircea.Markus@jboss.com
 * @since 4.2
 */
@Test(testName = "tx.TransactionXaAdapterTmIntegrationTest", groups = "unstable", description = "Disabled due to instability - see ISPN-1123 -- original group: unit")
public class TransactionXaAdapterTmIntegrationTest {
   private Configuration configuration;
   private XaTransactionTable txTable;
   private GlobalTransaction globalTransaction;
   private LocalXaTransaction localTx;
   private TransactionXaAdapter xaAdapter;
   private DummyXid xid;
   private UUID uuid = UUID.randomUUID();
   private TransactionCoordinator txCoordinator;

   @BeforeMethod
   public void setUp() throws XAException {
      Cache mockCache = mock(Cache.class);
      configuration = new ConfigurationBuilder().build();
      txTable = new XaTransactionTable();
      txTable.initialize(null, configuration, null, null, null, null,
            null, null, null, null, mockCache, null, null);
      txTable.start();
      txTable.startXidMapping();
      TransactionFactory gtf = new TransactionFactory();
      gtf.init(false, false, true, false);
      globalTransaction = gtf.newGlobalTransaction(null, false);
      DummyBaseTransactionManager tm = new DummyBaseTransactionManager();
      localTx = new LocalXaTransaction(new DummyTransaction(tm), globalTransaction, false, 1, AnyEquivalence.getInstance(), 0);
      xid = new DummyXid(uuid);

      InvocationContextFactory icf = new TransactionalInvocationContextFactory();
      CommandsFactory commandsFactory = mock(CommandsFactory.class);
      InterceptorChain invoker = mock(InterceptorChain.class);
      txCoordinator = new TransactionCoordinator();
      txCoordinator.init(commandsFactory, icf, invoker, txTable, null, configuration);
      xaAdapter = new TransactionXaAdapter(localTx, txTable, null, txCoordinator, null, null,
                                           new ClusteringDependentLogic.InvalidationLogic(), configuration, "");

      xaAdapter.start(xid, 0);
   }

   public void testPrepareOnNonexistentXid() {
      DummyXid xid = new DummyXid(uuid);
      try {
         xaAdapter.prepare(xid);
         assert false;
      } catch (XAException e) {
         assertEquals(XAException.XAER_NOTA, e.errorCode);
      }
   }

   public void testCommitOnNonexistentXid() {
      DummyXid xid = new DummyXid(uuid);
      try {
         xaAdapter.commit(xid, false);
         assert false;
      } catch (XAException e) {
         assertEquals(XAException.XAER_NOTA, e.errorCode);
      }
   }

   public void testRollabckOnNonexistentXid() {
      DummyXid xid = new DummyXid(uuid);
      try {
         xaAdapter.rollback(xid);
         assert false;
      } catch (XAException e) {
         assertEquals(XAException.XAER_NOTA, e.errorCode);
      }
   }

   public void testPrepareTxMarkedForRollback() {
      localTx.markForRollback(true);
      try {
         xaAdapter.prepare(xid);
         assert false;
      } catch (XAException e) {
         assertEquals(XAException.XA_RBROLLBACK, e.errorCode);
      }
   }

   public void testOnePhaseCommitConfigured() throws XAException {
      Configuration configuration = new ConfigurationBuilder().clustering().cacheMode(CacheMode.INVALIDATION_ASYNC).build();
      txCoordinator.init(null, null, null, null, null, configuration);
      assert XAResource.XA_OK == xaAdapter.prepare(xid);
   }

   public void test1PcAndNonExistentXid() {
      Configuration configuration = new ConfigurationBuilder().clustering().cacheMode(CacheMode.INVALIDATION_ASYNC).build();
      txCoordinator.init(null, null, null, null, null, configuration);
      try {
         DummyXid doesNotExists = new DummyXid(uuid);
         xaAdapter.commit(doesNotExists, false);
         assert false;
      } catch (XAException e) {
         assertEquals(XAException.XAER_NOTA, e.errorCode);
      }
   }

   public void test1PcAndNonExistentXid2() {
      Configuration configuration = new ConfigurationBuilder().clustering().cacheMode(CacheMode.DIST_SYNC).build();
      txCoordinator.init(null, null, null, null, null, configuration);
      try {
         DummyXid doesNotExists = new DummyXid(uuid);
         xaAdapter.commit(doesNotExists, true);
         assert false;
      } catch (XAException e) {
         assertEquals(XAException.XAER_NOTA, e.errorCode);
      }
   }
}


File: core/src/test/java/org/infinispan/tx/recovery/PostCommitRecoveryStateTest.java
package org.infinispan.tx.recovery;

import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.factories.ComponentRegistry;
import org.infinispan.remoting.transport.Address;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.tm.DummyTransaction;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.transaction.xa.XaTransactionTable;
import org.infinispan.transaction.xa.recovery.RecoveryAwareTransaction;
import org.infinispan.transaction.xa.recovery.RecoveryManager;
import org.infinispan.transaction.xa.recovery.RecoveryManagerImpl;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;
import org.testng.annotations.Test;

import javax.transaction.xa.Xid;

import java.util.Collection;
import java.util.List;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.infinispan.tx.recovery.RecoveryTestUtil.beginAndSuspendTx;
import static org.infinispan.tx.recovery.RecoveryTestUtil.commitTransaction;
import static org.infinispan.tx.recovery.RecoveryTestUtil.prepareTransaction;


/**
 * @author Mircea Markus
 * @since 5.0
 */
@Test (groups = "functional", testName = "tx.recovery.PostCommitRecoveryStateTest")
public class PostCommitRecoveryStateTest extends MultipleCacheManagersTest {

   private static Log log = LogFactory.getLog(PostCommitRecoveryStateTest.class);

   @Override
   protected void createCacheManagers() throws Throwable {
      ConfigurationBuilder configuration = getDefaultClusteredCacheConfig(CacheMode.DIST_SYNC, true);
      configuration
         .locking().useLockStriping(false)
         .transaction()
            .transactionManagerLookup(new RecoveryDummyTransactionManagerLookup())
            .useSynchronization(false)
            .recovery().enable()
         .clustering().stateTransfer().fetchInMemoryState(false);
      createCluster(configuration, 2);
      waitForClusterToForm();
      ComponentRegistry componentRegistry = this.cache(0).getAdvancedCache().getComponentRegistry();
      XaTransactionTable txTable = (XaTransactionTable) componentRegistry.getComponent(TransactionTable.class);
      txTable.setRecoveryManager(new RecoveryManagerDelegate(txTable.getRecoveryManager()));
   }

   public void testState() throws Exception {

      RecoveryManagerImpl rm1 = (RecoveryManagerImpl) advancedCache(1).getComponentRegistry().getComponent(RecoveryManager.class);
      TransactionTable tt1 = advancedCache(1).getComponentRegistry().getComponent(TransactionTable.class);
      assertEquals(rm1.getInDoubtTransactionsMap().size(), 0);
      assertEquals(tt1.getRemoteTxCount(), 0);

      DummyTransaction t0 = beginAndSuspendTx(cache(0));
      assertEquals(rm1.getInDoubtTransactionsMap().size(),0);
      assertEquals(tt1.getRemoteTxCount(), 0);

      prepareTransaction(t0);
      assertEquals(rm1.getInDoubtTransactionsMap().size(),0);
      assertEquals(tt1.getRemoteTxCount(), 1);

      commitTransaction(t0);
      assertEquals(tt1.getRemoteTxCount(), 1);
      assertEquals(rm1.getInDoubtTransactionsMap().size(), 0);
   }

   public static class RecoveryManagerDelegate implements RecoveryManager {
      volatile RecoveryManager rm;

      public boolean swallowRemoveRecoveryInfoCalls = true;

      public RecoveryManagerDelegate(RecoveryManager recoveryManager) {
         this.rm = recoveryManager;
      }

      @Override
      public RecoveryIterator getPreparedTransactionsFromCluster() {
         return rm.getPreparedTransactionsFromCluster();
      }

      @Override
      public void removeRecoveryInformationFromCluster(Collection<Address> where, Xid xid, boolean sync, GlobalTransaction gtx) {
         if (swallowRemoveRecoveryInfoCalls){
            log.trace("PostCommitRecoveryStateTest$RecoveryManagerDelegate.removeRecoveryInformation");
         } else {
            this.rm.removeRecoveryInformationFromCluster(where, xid, sync, null);
         }
      }

      @Override
      public void removeRecoveryInformationFromCluster(Collection<Address> where, long internalId, boolean sync) {
         rm.removeRecoveryInformationFromCluster(where, internalId, sync);
      }

      @Override
      public RecoveryAwareTransaction removeRecoveryInformation(Xid xid) {
         rm.removeRecoveryInformation(xid);
         return null;
      }

      @Override
      public Set<InDoubtTxInfo> getInDoubtTransactionInfoFromCluster() {
         return rm.getInDoubtTransactionInfoFromCluster();
      }

      @Override
      public Set<InDoubtTxInfo> getInDoubtTransactionInfo() {
         return rm.getInDoubtTransactionInfo();
      }

      @Override
      public List<Xid> getInDoubtTransactions() {
         return rm.getInDoubtTransactions();
      }

      @Override
      public RecoveryAwareTransaction getPreparedTransaction(Xid xid) {
         return rm.getPreparedTransaction(xid);
      }

      @Override
      public String forceTransactionCompletion(Xid xid, boolean commit) {
         return rm.forceTransactionCompletion(xid, commit);
      }

      @Override
      public String forceTransactionCompletionFromCluster(Xid xid, Address where, boolean commit) {
         return rm.forceTransactionCompletionFromCluster(xid, where, commit);
      }

      @Override
      public boolean isTransactionPrepared(GlobalTransaction globalTx) {
         return rm.isTransactionPrepared(globalTx);
      }

      @Override
      public RecoveryAwareTransaction removeRecoveryInformation(Long internalId) {
         rm.removeRecoveryInformation(internalId);
         return null;
      }
   }
}


File: extended-statistics/src/test/java/org/infinispan/stats/BaseTxClusterExtendedStatisticLogicTest.java
package org.infinispan.stats;

import org.infinispan.Cache;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.distribution.DistributionTestHelper;
import org.infinispan.distribution.MagicKey;
import org.infinispan.interceptors.TxInterceptor;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.stats.container.ConcurrentGlobalContainer;
import org.infinispan.stats.container.ExtendedStatistic;
import org.infinispan.stats.wrappers.ExtendedStatisticInterceptor;
import org.infinispan.stats.wrappers.ExtendedStatisticLockManager;
import org.infinispan.stats.wrappers.ExtendedStatisticRpcManager;
import org.infinispan.test.MultipleCacheManagersTest;
import org.infinispan.transaction.TransactionProtocol;
import org.infinispan.util.DefaultTimeService;
import org.infinispan.util.TimeService;
import org.infinispan.util.TransactionTrackInterceptor;
import org.infinispan.util.concurrent.IsolationLevel;
import org.infinispan.util.concurrent.locks.LockManager;
import org.testng.annotations.Test;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static java.util.concurrent.TimeUnit.NANOSECONDS;
import static org.infinispan.stats.CacheStatisticCollector.convertNanosToMicro;
import static org.infinispan.stats.CacheStatisticCollector.convertNanosToSeconds;
import static org.infinispan.stats.container.ExtendedStatistic.*;
import static org.infinispan.test.TestingUtil.*;
import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/**
 * @author Pedro Ruivo
 * @since 6.0
 */
@Test(groups = "functional")
public abstract class BaseTxClusterExtendedStatisticLogicTest extends MultipleCacheManagersTest {

   private static final int NUM_NODES = 2;
   private static final int TX_TIMEOUT = 60;
   private static final TimeService TEST_TIME_SERVICE = new DefaultTimeService() {
      @Override
      public long time() {
         return 0;
      }

      @Override
      public long timeDuration(long startTime, TimeUnit outputTimeUnit) {
         assertEquals(startTime, 0, "Start timestamp must be zero!");
         assertEquals(outputTimeUnit, NANOSECONDS, "TimeUnit is different from expected");
         return 1;
      }

      @Override
      public long timeDuration(long startTime, long endTime, TimeUnit outputTimeUnit) {
         assertEquals(startTime, 0, "Start timestamp must be zero!");
         assertEquals(endTime, 0, "End timestamp must be zero!");
         assertEquals(outputTimeUnit, NANOSECONDS, "TimeUnit is different from expected");
         return 1;
      }
   };
   private static final double MICROSECONDS = convertNanosToMicro(TEST_TIME_SERVICE.timeDuration(0, NANOSECONDS));
   private static final double SECONDS = convertNanosToSeconds(TEST_TIME_SERVICE.timeDuration(0, NANOSECONDS));
   private final TransactionTrackInterceptor[] transactionTrackInterceptors = new TransactionTrackInterceptor[NUM_NODES];
   private final ExtendedStatisticInterceptor[] extendedStatisticInterceptors = new ExtendedStatisticInterceptor[NUM_NODES];
   private final LockManager[] lockManagers = new LockManager[NUM_NODES];
   private final boolean sync;
   private final boolean replicated;
   private final boolean sync2ndPhase;
   private final boolean totalOrder;
   private final CacheMode cacheMode;
   private final List<Object> keys = new ArrayList<Object>(128);

   protected BaseTxClusterExtendedStatisticLogicTest(CacheMode cacheMode, boolean sync2ndPhase, boolean totalOrder) {
      this.sync = cacheMode.isSynchronous();
      this.replicated = cacheMode.isReplicated();
      this.cacheMode = cacheMode;
      this.sync2ndPhase = sync2ndPhase;
      this.totalOrder = totalOrder;
   }

   public final void testPutTxAndReadOnlyTx() throws Exception {
      testStats(WriteOperation.PUT, 2, 7, 3, 4, 5, false, true);
   }

   public final void testPutTxAndReadOnlyTxRollback() throws Exception {
      testStats(WriteOperation.PUT, 3, 6, 2, 5, 4, true, true);
   }

   public final void testPutTxAndReadOnlyTxNonCoordinator() throws Exception {
      testStats(WriteOperation.PUT, 4, 5, 4, 6, 3, false, false);
   }

   public final void testPutTxAndReadOnlyTxRollbackNonCoordinator() throws Exception {
      testStats(WriteOperation.PUT, 5, 4, 5, 7, 2, true, false);
   }

   public final void testConditionalPutTxAndReadOnlyTx() throws Exception {
      testStats(WriteOperation.PUT_IF, 2, 7, 3, 4, 5, false, true);
   }

   public final void testConditionalPutTxAndReadOnlyTxRollback() throws Exception {
      testStats(WriteOperation.PUT_IF, 3, 6, 2, 5, 4, true, true);
   }

   public final void testConditionalPutTxAndReadOnlyTxNonCoordinator() throws Exception {
      testStats(WriteOperation.PUT_IF, 4, 5, 4, 6, 3, false, false);
   }

   public final void testConditionalPutTxAndReadOnlyTxRollbackNonCoordinator() throws Exception {
      testStats(WriteOperation.PUT_IF, 5, 4, 5, 7, 2, true, false);
   }

   public final void testReplaceTxAndReadOnlyTx() throws Exception {
      testStats(WriteOperation.REPLACE, 2, 7, 3, 4, 5, false, true);
   }

   public final void testReplaceTxAndReadOnlyTxRollback() throws Exception {
      testStats(WriteOperation.REPLACE, 3, 6, 2, 5, 4, true, true);
   }

   public final void testReplaceTxAndReadOnlyTxNonCoordinator() throws Exception {
      testStats(WriteOperation.REPLACE, 4, 5, 4, 6, 3, false, false);
   }

   public final void testReplaceTxAndReadOnlyTxRollbackNonCoordinator() throws Exception {
      testStats(WriteOperation.REPLACE, 5, 4, 5, 7, 2, true, false);
   }

   public final void testConditionalReplaceTxAndReadOnlyTx() throws Exception {
      testStats(WriteOperation.REPLACE_IF, 2, 7, 3, 4, 5, false, true);
   }

   public final void testConditionalReplaceTxAndReadOnlyTxRollback() throws Exception {
      testStats(WriteOperation.REPLACE_IF, 3, 6, 2, 5, 4, true, true);
   }

   public final void testConditionalReplaceTxAndReadOnlyTxNonCoordinator() throws Exception {
      testStats(WriteOperation.REPLACE_IF, 4, 5, 4, 6, 3, false, false);
   }

   public final void testConditionalReplaceTxAndReadOnlyTxRollbackNonCoordinator() throws Exception {
      testStats(WriteOperation.REPLACE_IF, 5, 4, 5, 7, 2, true, false);
   }

   public final void testRemoveTxAndReadOnlyTx() throws Exception {
      testStats(WriteOperation.REMOVE, 2, 7, 3, 4, 5, false, true);
   }

   public final void testRemoveTxAndReadOnlyTxRollback() throws Exception {
      testStats(WriteOperation.REMOVE, 3, 6, 2, 5, 4, true, true);
   }

   public final void testRemoveTxAndReadOnlyTxNonCoordinator() throws Exception {
      testStats(WriteOperation.REMOVE, 4, 5, 4, 6, 3, false, false);
   }

   public final void testRemoveTxAndReadOnlyTxRollbackNonCoordinator() throws Exception {
      testStats(WriteOperation.REMOVE, 5, 4, 5, 7, 2, true, false);
   }

   public final void testConditionalRemoveTxAndReadOnlyTx() throws Exception {
      testStats(WriteOperation.REMOVE_IF, 2, 7, 3, 4, 5, false, true);
   }

   public final void testConditionalRemoveTxAndReadOnlyTxRollback() throws Exception {
      testStats(WriteOperation.REMOVE_IF, 3, 6, 2, 5, 4, true, true);
   }

   public final void testConditionalRemoveTxAndReadOnlyTxNonCoordinator() throws Exception {
      testStats(WriteOperation.REMOVE_IF, 4, 5, 4, 6, 3, false, false);
   }

   public final void testConditionalRemoveTxAndReadOnlyTxRollbackNonCoordinator() throws Exception {
      testStats(WriteOperation.REMOVE_IF, 5, 4, 5, 7, 2, true, false);
   }

   @Override
   protected void createCacheManagers() throws Throwable {
      for (int i = 0; i < NUM_NODES; ++i) {
         ConfigurationBuilder builder = getDefaultClusteredCacheConfig(cacheMode, true);
         builder.transaction().syncCommitPhase(sync2ndPhase).syncRollbackPhase(sync2ndPhase);
         if (totalOrder) {
            builder.transaction().transactionProtocol(TransactionProtocol.TOTAL_ORDER);
         }
         builder.locking().isolationLevel(IsolationLevel.REPEATABLE_READ).writeSkewCheck(false)
               .lockAcquisitionTimeout(0);
         builder.clustering().hash().numOwners(1);
         builder.transaction().recovery().disable();
         extendedStatisticInterceptors[i] = new ExtendedStatisticInterceptor();
         builder.customInterceptors().addInterceptor().interceptor(extendedStatisticInterceptors[i])
               .after(TxInterceptor.class);
         addClusterEnabledCacheManager(builder);
      }
      waitForClusterToForm();
      for (int i = 0; i < NUM_NODES; ++i) {
         lockManagers[i] = extractLockManager(cache(i));
         ExtendedStatisticInterceptor interceptor = extendedStatisticInterceptors[i];
         CacheStatisticManager manager = (CacheStatisticManager) extractField(interceptor, "cacheStatisticManager");
         CacheStatisticCollector collector = (CacheStatisticCollector) extractField(manager, "cacheStatisticCollector");
         ConcurrentGlobalContainer globalContainer = (ConcurrentGlobalContainer) extractField(collector, "globalContainer");
         replaceField(TEST_TIME_SERVICE, "timeService", manager, CacheStatisticManager.class);
         replaceField(TEST_TIME_SERVICE, "timeService", collector, CacheStatisticCollector.class);
         replaceField(TEST_TIME_SERVICE, "timeService", globalContainer, ConcurrentGlobalContainer.class);
         replaceField(TEST_TIME_SERVICE, "timeService", interceptor, ExtendedStatisticInterceptor.class);
         replaceField(TEST_TIME_SERVICE, "timeService", lockManagers[i], ExtendedStatisticLockManager.class);
         replaceField(TEST_TIME_SERVICE, "timeService", extractComponent(cache(i), RpcManager.class), ExtendedStatisticRpcManager.class);
         transactionTrackInterceptors[i] = TransactionTrackInterceptor.injectInCache(cache(i));
      }
   }

   private void testStats(WriteOperation operation, int numOfWriteTx, int numOfWrites, int numOfReadsPerWriteTx,
                          int numOfReadOnlyTx, int numOfReadPerReadTx, boolean abort, boolean executeOnCoordinator)
         throws Exception {
      final int txExecutor = executeOnCoordinator ? 0 : 1;

      int localGetsReadTx = 0;
      int localGetsWriteTx = 0;
      int localPuts = 0;
      int remoteGetsReadTx = 0;
      int remoteGetsWriteTx = 0;
      int remotePuts = 0;
      int localLocks = 0;
      int remoteLocks = 0;
      int numOfLocalWriteTx = 0;
      int numOfRemoteWriteTx = 0; //no. transaction that involves the second node too.

      resetTxCounters();
      boolean remote = false;
      tm(txExecutor).begin();
      for (int i = 1; i <= (numOfReadsPerWriteTx + numOfWrites) * numOfWriteTx + numOfReadPerReadTx * numOfReadOnlyTx; ++i) {
         cache(txExecutor).put(getKey(i), getInitValue(i));
         if (isRemote(getKey(i), cache(txExecutor))) {
            remote = true;
         }
      }
      tm(txExecutor).commit();
      assertTxSeen(txExecutor, 1, replicated || remote ? 1 : 0, 0, false);
      resetStats();
      resetTxCounters();

      int keyIndex = 0;
      //write tx
      for (int tx = 1; tx <= numOfWriteTx; ++tx) {
         boolean involvesRemoteNode = cacheMode.isReplicated();
         tm(txExecutor).begin();
         for (int i = 1; i <= numOfReadsPerWriteTx; ++i) {
            keyIndex++;
            Object key = getKey(keyIndex);
            if (isRemote(key, cache(txExecutor))) {
               remoteGetsWriteTx++;
            } else {
               localGetsWriteTx++;
            }
            assertEquals(cache(txExecutor).get(key), getInitValue(keyIndex));
         }
         for (int i = 1; i <= numOfWrites; ++i) {
            keyIndex++;
            Object key = operation == WriteOperation.PUT_IF ? getKey(-keyIndex) : getKey(keyIndex);
            switch (operation) {
               case PUT:
                  cache(txExecutor).put(key, getValue(keyIndex));
                  break;
               case PUT_IF:
                  cache(txExecutor).putIfAbsent(key, getValue(keyIndex));
                  break;
               case REPLACE:
                  cache(txExecutor).replace(key, getValue(keyIndex));
                  break;
               case REPLACE_IF:
                  cache(txExecutor).replace(key, getInitValue(keyIndex), getValue(keyIndex));
                  break;
               case REMOVE:
                  cache(txExecutor).remove(key);
                  break;
               case REMOVE_IF:
                  cache(txExecutor).remove(key, getInitValue(keyIndex));
                  break;
               default:
                  //nothing
            }
            if (isRemote(key, cache(txExecutor))) {
               remotePuts++;
               involvesRemoteNode = true;
               //remote puts always acquires local locks
               if (operation == WriteOperation.REPLACE) {
                  localLocks++;
               }
            } else {
               localPuts++;
            }
            if (isLockOwner(key, cache(txExecutor))) {
               if (!abort) {
                  localLocks++;
               }
            } else {
               if (!abort) {
                  remoteLocks++;
               }
            }

         }
         if (involvesRemoteNode) {
            numOfRemoteWriteTx++;
         }
         numOfLocalWriteTx++;
         if (abort) {
            tm(txExecutor).rollback();
         } else {
            tm(txExecutor).commit();

         }
      }

      //read tx
      for (int tx = 1; tx <= numOfReadOnlyTx; ++tx) {
         tm(txExecutor).begin();
         for (int i = 1; i <= numOfReadPerReadTx; ++i) {
            keyIndex++;
            Object key = getKey(keyIndex);
            if (isRemote(key, cache(txExecutor))) {
               remoteGetsReadTx++;
            } else {
               localGetsReadTx++;
            }
            assertEquals(cache(txExecutor).get(key), getInitValue(keyIndex));
         }
         if (abort) {
            tm(txExecutor).rollback();
         } else {
            tm(txExecutor).commit();

         }
      }
      assertTxSeen(txExecutor, numOfLocalWriteTx, replicated ? numOfLocalWriteTx : numOfRemoteWriteTx, numOfReadOnlyTx, abort);

      EnumSet<ExtendedStatistic> statsToValidate = getStatsToValidate();

      assertTxValues(statsToValidate, numOfLocalWriteTx, numOfRemoteWriteTx, numOfReadOnlyTx, txExecutor, abort);
      assertLockingValues(statsToValidate, localLocks, remoteLocks, numOfLocalWriteTx, numOfRemoteWriteTx, txExecutor, abort);
      assertAccessesValues(statsToValidate, localGetsReadTx, remoteGetsReadTx, localGetsWriteTx, remoteGetsWriteTx,
                           localPuts, remotePuts, numOfWriteTx, numOfReadOnlyTx, txExecutor, abort);

      assertAttributeValue(NUM_WRITE_SKEW, statsToValidate, 0, 0, txExecutor);
      assertAttributeValue(WRITE_SKEW_PROBABILITY, statsToValidate, 0, 0, txExecutor);

      assertAllStatsValidated(statsToValidate);
      resetStats();
   }

   private void assertTxSeen(int txExecutor, int localTx, int remoteTx, int readOnlyTx, boolean abort) throws InterruptedException {
      for (int i = 0; i < NUM_NODES; ++i) {
         if (i == txExecutor) {
            assertTrue(transactionTrackInterceptors[i].awaitForLocalCompletion(localTx + readOnlyTx, TX_TIMEOUT, TimeUnit.SECONDS));
            if (totalOrder && !abort) {
               assertTrue(transactionTrackInterceptors[i].awaitForRemoteCompletion(localTx, TX_TIMEOUT, TimeUnit.SECONDS));
            }
         } else if (!abort) {
            assertTrue(transactionTrackInterceptors[i].awaitForRemoteCompletion(remoteTx, TX_TIMEOUT, TimeUnit.SECONDS));
         }
      }
      eventually(new Condition() {
         @Override
         public boolean isSatisfied() throws Exception {
            for (LockManager lockManager : lockManagers) {
               if (lockManager.getNumberOfLocksHeld() != 0) {
                  return false;
               }
            }
            return true;
         }
      });
   }

   private void resetTxCounters() {
      for (TransactionTrackInterceptor interceptor : transactionTrackInterceptors) {
         interceptor.reset();
      }
   }

   private boolean isRemote(Object key, Cache cache) {
      return !replicated && !DistributionTestHelper.isOwner(cache, key);
   }

   private boolean isLockOwner(Object key, Cache cache) {
      return replicated ? address(0).equals(address(cache)) : DistributionTestHelper.isFirstOwner(cache, key);
   }

   private Object getKey(int i) {
      if (i < 0) {
         return replicated ? "KEY_" + i : new MagicKey("KEY_" + i, cache(0));
      }
      for (int j = keys.size(); j < i; ++j) {
         keys.add(replicated ? "KEY_" + (j + 1) : new MagicKey("KEY_" + (j + 1), cache(0)));
      }
      return keys.get(i - 1);
   }

   private Object getInitValue(int i) {
      return "INIT_" + i;
   }

   private Object getValue(int i) {
      return "VALUE_" + i;
   }

   private void assertTxValues(EnumSet<ExtendedStatistic> statsToValidate, int numOfLocalWriteTx, int numOfRemoteWriteTx,
                               int numOfReadTx, int txExecutor, boolean abort) {
      log.infof("Check Tx value: localWriteTx=%s, remoteWriteTx=%s, readTx=%s, txExecutor=%s, abort?=%s",
                numOfLocalWriteTx, numOfRemoteWriteTx, numOfReadTx, txExecutor, abort);
      if (abort) {
         assertAttributeValue(NUM_COMMITTED_RO_TX, statsToValidate, 0, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(NUM_COMMITTED_WR_TX, statsToValidate, 0, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(NUM_ABORTED_WR_TX, statsToValidate, numOfLocalWriteTx, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(NUM_ABORTED_RO_TX, statsToValidate, numOfReadTx, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(NUM_COMMITTED_TX, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_LOCAL_COMMITTED_TX, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(LOCAL_EXEC_NO_CONT, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(WRITE_TX_PERCENTAGE, statsToValidate, numOfLocalWriteTx * 1.0 / (numOfLocalWriteTx + numOfReadTx), 0, txExecutor);
         assertAttributeValue(SUCCESSFUL_WRITE_TX_PERCENTAGE, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(WR_TX_ABORTED_EXECUTION_TIME, statsToValidate, numOfLocalWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(RO_TX_ABORTED_EXECUTION_TIME, statsToValidate, numOfReadTx, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(WR_TX_SUCCESSFUL_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(RO_TX_SUCCESSFUL_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(ABORT_RATE, statsToValidate, 1, 0, txExecutor);
         assertAttributeValue(ARRIVAL_RATE, statsToValidate, (numOfLocalWriteTx + numOfReadTx) / SECONDS, 0, txExecutor);
         assertAttributeValue(THROUGHPUT, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(ROLLBACK_EXECUTION_TIME, statsToValidate, numOfReadTx != 0 || numOfLocalWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(NUM_ROLLBACK_COMMAND, statsToValidate, numOfReadTx + numOfLocalWriteTx, 0, txExecutor);
         assertAttributeValue(LOCAL_ROLLBACK_EXECUTION_TIME, statsToValidate, numOfReadTx != 0 || numOfLocalWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(REMOTE_ROLLBACK_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(COMMIT_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_COMMIT_COMMAND, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(LOCAL_COMMIT_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(REMOTE_COMMIT_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(PREPARE_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor); // //not exposed via JMX
         assertAttributeValue(NUM_PREPARE_COMMAND, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(LOCAL_PREPARE_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(REMOTE_PREPARE_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_SYNC_PREPARE, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(SYNC_PREPARE_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_SYNC_COMMIT, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(SYNC_COMMIT_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_SYNC_ROLLBACK, statsToValidate, sync2ndPhase && !totalOrder ? numOfLocalWriteTx : 0, 0, txExecutor);
         assertAttributeValue(SYNC_ROLLBACK_TIME, statsToValidate, sync2ndPhase && numOfLocalWriteTx != 0 && !totalOrder ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(ASYNC_PREPARE_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_ASYNC_PREPARE, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(ASYNC_COMMIT_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_ASYNC_COMMIT, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(ASYNC_ROLLBACK_TIME, statsToValidate, (sync && sync2ndPhase) || numOfLocalWriteTx == 0 || totalOrder ? 0 : MICROSECONDS, 0, txExecutor);
         assertAttributeValue(NUM_ASYNC_ROLLBACK, statsToValidate, (sync && sync2ndPhase) || totalOrder ? 0 : numOfLocalWriteTx, 0, txExecutor);
         assertAttributeValue(ASYNC_COMPLETE_NOTIFY_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_ASYNC_COMPLETE_NOTIFY, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_NODES_PREPARE, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_NODES_COMMIT, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_NODES_ROLLBACK, statsToValidate, !totalOrder && numOfLocalWriteTx != 0 && replicated ? NUM_NODES : 0, 0, txExecutor);
         assertAttributeValue(NUM_NODES_COMPLETE_NOTIFY, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(RESPONSE_TIME, statsToValidate, 0, 0, txExecutor);
      } else {
         assertAttributeValue(NUM_COMMITTED_RO_TX, statsToValidate, numOfReadTx, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(NUM_COMMITTED_WR_TX, statsToValidate, (totalOrder ? 2 * numOfLocalWriteTx : numOfLocalWriteTx),
                              numOfRemoteWriteTx, txExecutor); //not exposed via JMX
         assertAttributeValue(NUM_ABORTED_WR_TX, statsToValidate, 0, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(NUM_ABORTED_RO_TX, statsToValidate, 0, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(NUM_COMMITTED_TX, statsToValidate, (totalOrder ? 2 * numOfLocalWriteTx : numOfLocalWriteTx) + numOfReadTx,
                              numOfRemoteWriteTx, txExecutor);
         assertAttributeValue(NUM_LOCAL_COMMITTED_TX, statsToValidate, numOfReadTx + numOfLocalWriteTx, 0, txExecutor);
         assertAttributeValue(LOCAL_EXEC_NO_CONT, statsToValidate, numOfLocalWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(WRITE_TX_PERCENTAGE, statsToValidate, (numOfLocalWriteTx * 1.0) / (numOfReadTx + numOfLocalWriteTx), 0, txExecutor);
         assertAttributeValue(SUCCESSFUL_WRITE_TX_PERCENTAGE, statsToValidate, (numOfReadTx + numOfLocalWriteTx) > 0 ? (numOfLocalWriteTx * 1.0) / (numOfReadTx + numOfLocalWriteTx) : 0, 0, txExecutor);
         assertAttributeValue(WR_TX_ABORTED_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(RO_TX_ABORTED_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor); //not exposed via JMX
         assertAttributeValue(WR_TX_SUCCESSFUL_EXECUTION_TIME, statsToValidate, numOfLocalWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(RO_TX_SUCCESSFUL_EXECUTION_TIME, statsToValidate, numOfReadTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(ABORT_RATE, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(ARRIVAL_RATE, statsToValidate, ((totalOrder ? 2 * numOfLocalWriteTx : numOfLocalWriteTx) + numOfReadTx) / SECONDS, numOfRemoteWriteTx / SECONDS, txExecutor);
         assertAttributeValue(THROUGHPUT, statsToValidate, (numOfLocalWriteTx + numOfReadTx) / SECONDS, 0, txExecutor);
         assertAttributeValue(ROLLBACK_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_ROLLBACK_COMMAND, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(LOCAL_ROLLBACK_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(REMOTE_ROLLBACK_EXECUTION_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(COMMIT_EXECUTION_TIME, statsToValidate, sync && (numOfReadTx != 0 || numOfLocalWriteTx != 0) && !totalOrder ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(NUM_COMMIT_COMMAND, statsToValidate, sync && !totalOrder ? (numOfReadTx + numOfLocalWriteTx) : 0, sync && !totalOrder ? numOfRemoteWriteTx : 0, txExecutor);
         assertAttributeValue(LOCAL_COMMIT_EXECUTION_TIME, statsToValidate, sync && (numOfReadTx != 0 || numOfLocalWriteTx != 0) && !totalOrder ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(REMOTE_COMMIT_EXECUTION_TIME, statsToValidate, 0, sync && numOfRemoteWriteTx != 0 && !totalOrder ? MICROSECONDS : 0, txExecutor);
         assertAttributeValue(PREPARE_EXECUTION_TIME, statsToValidate, numOfReadTx + (totalOrder ? 2 * numOfLocalWriteTx : numOfLocalWriteTx), numOfRemoteWriteTx, txExecutor); // //not exposed via JMX
         assertAttributeValue(NUM_PREPARE_COMMAND, statsToValidate, numOfReadTx + (totalOrder ? 2 * numOfLocalWriteTx : numOfLocalWriteTx), numOfRemoteWriteTx, txExecutor);
         assertAttributeValue(LOCAL_PREPARE_EXECUTION_TIME, statsToValidate, (numOfReadTx != 0 || numOfLocalWriteTx != 0) ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(REMOTE_PREPARE_EXECUTION_TIME, statsToValidate, totalOrder && numOfLocalWriteTx != 0 ? MICROSECONDS : 0, numOfRemoteWriteTx != 0 ? MICROSECONDS : 0, txExecutor);
         assertAttributeValue(NUM_SYNC_PREPARE, statsToValidate, sync ? numOfLocalWriteTx : 0, 0, txExecutor);
         assertAttributeValue(SYNC_PREPARE_TIME, statsToValidate, sync && numOfLocalWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(NUM_SYNC_COMMIT, statsToValidate, sync2ndPhase && !totalOrder ? numOfLocalWriteTx : 0, 0, txExecutor);
         assertAttributeValue(SYNC_COMMIT_TIME, statsToValidate, sync2ndPhase && numOfLocalWriteTx != 0 && !totalOrder ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(NUM_SYNC_ROLLBACK, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(SYNC_ROLLBACK_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(ASYNC_PREPARE_TIME, statsToValidate, !sync && numOfLocalWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(NUM_ASYNC_PREPARE, statsToValidate, sync ? 0 : numOfLocalWriteTx, 0, txExecutor);
         assertAttributeValue(ASYNC_COMMIT_TIME, statsToValidate, (!sync || sync2ndPhase) || numOfLocalWriteTx == 0 || totalOrder ? 0 : MICROSECONDS, 0, txExecutor);
         assertAttributeValue(NUM_ASYNC_COMMIT, statsToValidate, (!sync || sync2ndPhase) || totalOrder ? 0 : numOfLocalWriteTx, 0, txExecutor);
         assertAttributeValue(ASYNC_ROLLBACK_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_ASYNC_ROLLBACK, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(ASYNC_COMPLETE_NOTIFY_TIME, statsToValidate, sync2ndPhase && numOfLocalWriteTx != 0 && !totalOrder ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(NUM_ASYNC_COMPLETE_NOTIFY, statsToValidate, sync2ndPhase && !totalOrder ? numOfLocalWriteTx : 0, 0, txExecutor);
         assertAttributeValue(NUM_NODES_PREPARE, statsToValidate, replicated ? NUM_NODES : totalOrder && txExecutor == 1 ? 2 : 1, 0, txExecutor);
         assertAttributeValue(NUM_NODES_COMMIT, statsToValidate, sync && !totalOrder ? (replicated ? NUM_NODES : 1) : 0, 0, txExecutor);
         assertAttributeValue(NUM_NODES_ROLLBACK, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_NODES_COMPLETE_NOTIFY, statsToValidate, sync2ndPhase && !totalOrder ? (replicated ? NUM_NODES : 1) : 0, 0, txExecutor);
         assertAttributeValue(RESPONSE_TIME, statsToValidate, numOfReadTx != 0 || numOfLocalWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
      }
   }

   private void assertLockingValues(EnumSet<ExtendedStatistic> statsToValidate, int numOfLocalLocks, int numOfRemoteLocks,
                                    int numOfLocalWriteTx, int numOfRemoteWriteTx, int txExecutor, boolean abort) {
      log.infof("Check Locking value. localLocks=%s, remoteLocks=%s, localWriteTx=%s, remoteWriteTx=%s, txExecutor=%s, abort?=%s",
                numOfLocalLocks, numOfRemoteLocks, numOfLocalWriteTx, numOfRemoteWriteTx, txExecutor, abort);
      if (totalOrder) {
         assertAttributeValue(LOCK_HOLD_TIME_LOCAL, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(LOCK_HOLD_TIME_REMOTE, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_LOCK_PER_LOCAL_TX, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_LOCK_PER_REMOTE_TX, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_HELD_LOCKS_SUCCESS_LOCAL_TX, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(LOCK_HOLD_TIME_SUCCESS_LOCAL_TX, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(LOCK_HOLD_TIME, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(NUM_HELD_LOCKS, statsToValidate, 0, 0, txExecutor);
      } else {
         //remote puts always acquire locks
         assertAttributeValue(LOCK_HOLD_TIME_LOCAL, statsToValidate, numOfLocalLocks != 0 ? MICROSECONDS : 0, 0, txExecutor);
         assertAttributeValue(LOCK_HOLD_TIME_REMOTE, statsToValidate, 0, numOfRemoteLocks != 0 ? MICROSECONDS : 0, txExecutor);
         assertAttributeValue(NUM_LOCK_PER_LOCAL_TX, statsToValidate, numOfLocalWriteTx != 0 ? numOfLocalLocks * 1.0 / numOfLocalWriteTx : 0, 0, txExecutor);
         assertAttributeValue(NUM_LOCK_PER_REMOTE_TX, statsToValidate, 0, numOfRemoteWriteTx != 0 ? numOfRemoteLocks * 1.0 / numOfRemoteWriteTx : 0, txExecutor);
         assertAttributeValue(NUM_HELD_LOCKS_SUCCESS_LOCAL_TX, statsToValidate, !abort && numOfLocalWriteTx != 0 ? numOfLocalLocks * 1.0 / numOfLocalWriteTx : 0, 0, txExecutor);
         assertAttributeValue(LOCK_HOLD_TIME_SUCCESS_LOCAL_TX, statsToValidate, 0, 0, txExecutor);
         assertAttributeValue(LOCK_HOLD_TIME, statsToValidate, numOfLocalLocks != 0 ? MICROSECONDS : 0, numOfRemoteLocks != 0 ? MICROSECONDS : 0, txExecutor);
         assertAttributeValue(NUM_HELD_LOCKS, statsToValidate, numOfLocalLocks, numOfRemoteLocks, txExecutor);
      }
      assertAttributeValue(NUM_WAITED_FOR_LOCKS, statsToValidate, 0, 0, txExecutor);
      assertAttributeValue(LOCK_WAITING_TIME, statsToValidate, 0, 0, txExecutor);
      assertAttributeValue(NUM_LOCK_FAILED_TIMEOUT, statsToValidate, 0, 0, txExecutor);
      assertAttributeValue(NUM_LOCK_FAILED_DEADLOCK, statsToValidate, 0, 0, txExecutor);
   }

   private void assertAccessesValues(EnumSet<ExtendedStatistic> statsToValidate, int localGetsReadTx, int remoteGetsReadTx, int localGetsWriteTx, int remoteGetsWriteTx, int localPuts,
                                     int remotePuts, int numOfWriteTx, int numOfReadTx, int txExecutor, boolean abort) {
      log.infof("Check accesses values. localGetsReadTx=%s, remoteGetsReadTx=%s, localGetsWriteTx=%s, remoteGetsWriteTx=%s, " +
                      "localPuts=%s, remotePuts=%s, writeTx=%s, readTx=%s, txExecutor=%s, abort?=%s",
                localGetsReadTx, remoteGetsReadTx, localGetsWriteTx, remoteGetsWriteTx, localPuts, remotePuts,
                numOfWriteTx, numOfReadTx, txExecutor, abort);
      assertAttributeValue(NUM_REMOTE_PUT, statsToValidate, remotePuts, 0, txExecutor);
      assertAttributeValue(LOCAL_PUT_EXECUTION, statsToValidate, 0, 0, txExecutor);
      assertAttributeValue(REMOTE_PUT_EXECUTION, statsToValidate, remotePuts != 0 ? MICROSECONDS : 0, 0, txExecutor);
      assertAttributeValue(NUM_PUT, statsToValidate, remotePuts + localPuts, 0, txExecutor);
      assertAttributeValue(NUM_PUTS_WR_TX, statsToValidate, !abort && numOfWriteTx != 0 ? (localPuts + remotePuts * 1.0) / numOfWriteTx : 0, 0, txExecutor);
      assertAttributeValue(NUM_REMOTE_PUTS_WR_TX, statsToValidate, !abort && numOfWriteTx != 0 ? (remotePuts * 1.0) / numOfWriteTx : 0, 0, txExecutor);

      assertAttributeValue(NUM_REMOTE_GET, statsToValidate, remoteGetsReadTx + remoteGetsWriteTx, 0, txExecutor);
      assertAttributeValue(NUM_GET, statsToValidate, localGetsReadTx + localGetsWriteTx + remoteGetsReadTx + remoteGetsWriteTx, 0, txExecutor);
      assertAttributeValue(NUM_GETS_RO_TX, statsToValidate, !abort && numOfReadTx != 0 ? (localGetsReadTx + remoteGetsReadTx * 1.0) / numOfReadTx : 0, 0, txExecutor);
      assertAttributeValue(NUM_GETS_WR_TX, statsToValidate, !abort && numOfWriteTx != 0 ? (localGetsWriteTx + remoteGetsWriteTx * 1.0) / numOfWriteTx : 0, 0, txExecutor);
      assertAttributeValue(NUM_REMOTE_GETS_WR_TX, statsToValidate, !abort && numOfWriteTx != 0 ? remoteGetsWriteTx * 1.0 / numOfWriteTx : 0, 0, txExecutor);
      assertAttributeValue(NUM_REMOTE_GETS_RO_TX, statsToValidate, !abort && numOfReadTx != 0 ? remoteGetsReadTx * 1.0 / numOfReadTx : 0, 0, txExecutor);
      assertAttributeValue(ALL_GET_EXECUTION, statsToValidate, remoteGetsReadTx + localGetsReadTx + localGetsWriteTx + remoteGetsWriteTx, 0, txExecutor);
      //always zero because the all get execution and the rtt is always 1 (all get execution - rtt == 0)
      assertAttributeValue(LOCAL_GET_EXECUTION, statsToValidate, (remoteGetsReadTx + remoteGetsWriteTx) < (localGetsReadTx + localGetsWriteTx) ? MICROSECONDS : 0, 0, txExecutor);
      assertAttributeValue(REMOTE_GET_EXECUTION, statsToValidate, remoteGetsReadTx != 0 || remoteGetsWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
      assertAttributeValue(NUM_SYNC_GET, statsToValidate, remoteGetsReadTx + remoteGetsWriteTx, 0, txExecutor);
      assertAttributeValue(SYNC_GET_TIME, statsToValidate, remoteGetsReadTx != 0 || remoteGetsWriteTx != 0 ? MICROSECONDS : 0, 0, txExecutor);
      assertAttributeValue(NUM_NODES_GET, statsToValidate, remoteGetsReadTx != 0 || remoteGetsWriteTx != 0 ? 1 : 0, 0, txExecutor);
   }

   private void resetStats() {
      for (ExtendedStatisticInterceptor interceptor : extendedStatisticInterceptors) {
         interceptor.resetStatistics();
         for (ExtendedStatistic extendedStatistic : values()) {
            assertEquals(interceptor.getAttribute(extendedStatistic), 0.0, "Attribute " + extendedStatistic +
                  " is not zero after reset");
         }
      }
   }

   private void assertAttributeValue(ExtendedStatistic attr, EnumSet<ExtendedStatistic> statsToValidate,
                                     double txExecutorValue, double nonTxExecutorValue, int txExecutorIndex) {
      assertTrue(statsToValidate.contains(attr), "Attribute " + attr + " already validated");
      for (int i = 0; i < NUM_NODES; ++i) {
         assertEquals(extendedStatisticInterceptors[i].getAttribute(attr), i == txExecutorIndex ? txExecutorValue : nonTxExecutorValue,
                      "Attribute " + attr + " has wrong value for cache " + i + ".");
      }
      statsToValidate.remove(attr);
   }

   private EnumSet<ExtendedStatistic> getStatsToValidate() {
      EnumSet<ExtendedStatistic> statsToValidate = EnumSet.allOf(ExtendedStatistic.class);
      //this stats are not validated.
      statsToValidate.removeAll(EnumSet.of(PREPARE_COMMAND_SIZE, COMMIT_COMMAND_SIZE, CLUSTERED_GET_COMMAND_SIZE));
      return statsToValidate;
   }

   private void assertAllStatsValidated(EnumSet<ExtendedStatistic> statsToValidate) {
      assertTrue(statsToValidate.isEmpty(), "Stats not validated: " + statsToValidate + ".");
   }

   private enum WriteOperation {
      PUT,
      PUT_IF,
      REPLACE,
      REPLACE_IF,
      REMOVE,
      REMOVE_IF
   }
}
