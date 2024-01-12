Refactoring Types: ['Extract Method']
ava/org/infinispan/cli/interpreter/session/SessionImpl.java
package org.infinispan.cli.interpreter.session;

import java.util.Collection;

import javax.transaction.TransactionManager;

import org.infinispan.AdvancedCache;
import org.infinispan.Cache;
import org.infinispan.commons.api.BasicCacheContainer;
import org.infinispan.cli.interpreter.codec.Codec;
import org.infinispan.cli.interpreter.codec.CodecException;
import org.infinispan.cli.interpreter.codec.CodecRegistry;
import org.infinispan.cli.interpreter.logging.Log;
import org.infinispan.commands.CommandsFactory;
import org.infinispan.commands.CreateCacheCommand;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.statetransfer.StateTransferManager;
import org.infinispan.util.TimeService;
import org.infinispan.util.logging.LogFactory;

public class SessionImpl implements Session {
   public static final Log log = LogFactory.getLog(SessionImpl.class, Log.class);
   private final EmbeddedCacheManager cacheManager;
   private final CodecRegistry codecRegistry;
   private final String id;
   private final TimeService timeService;
   private Cache<?, ?> cache = null;
   private String cacheName = null;
   private long timestamp;
   private Codec codec;

   public SessionImpl(final CodecRegistry codecRegistry, final EmbeddedCacheManager cacheManager, final String id,
                      TimeService timeService) {
      if (timeService == null) {
         throw new IllegalArgumentException("TimeService cannot be null");
      }
      this.codecRegistry = codecRegistry;
      this.cacheManager = cacheManager;
      this.timeService = timeService;
      this.id = id;
      timestamp = timeService.time();
      codec = this.codecRegistry.getCodec("none");
   }

   @Override
   public EmbeddedCacheManager getCacheManager() {
      return cacheManager;
   }

   @Override
   public String getId() {
      return id;
   }

   @Override
   public <K, V> Cache<K, V> getCurrentCache() {
      return (Cache<K, V>) cache;
   }

   @Override
   public String getCurrentCacheName() {
      return cacheName;
   }

   @Override
   public <K, V> Cache<K, V> getCache(final String cacheName) {
      Cache<K, V> c;
      if (cacheName != null) {
         c = cacheManager.getCache(cacheName, false);
      } else {
         c = getCurrentCache();
      }
      if (c == null) {
         throw log.nonExistentCache(cacheName);
      }
      return c;
   }

   @Override
   public void setCurrentCache(final String cacheName) {
      cache = getCache(cacheName);
      this.cacheName = cacheName;
   }

   @Override
   public void createCache(String cacheName, String baseCacheName) {
      Configuration configuration;
      if (baseCacheName != null) {
         configuration = cacheManager.getCacheConfiguration(baseCacheName);
         if (configuration == null) {
            throw log.nonExistentCache(baseCacheName);
         }
      } else {
         configuration = cacheManager.getDefaultCacheConfiguration();
         baseCacheName = BasicCacheContainer.DEFAULT_CACHE_NAME;
      }
      if (cacheManager.cacheExists(cacheName)) {
         throw log.cacheAlreadyExists(cacheName);
      }
      if (configuration.clustering().cacheMode().isClustered()) {
         AdvancedCache<?, ?> clusteredCache = cacheManager.getCache(baseCacheName).getAdvancedCache();
         RpcManager rpc = clusteredCache.getRpcManager();
         CommandsFactory factory = clusteredCache.getComponentRegistry().getComponent(CommandsFactory.class);

         CreateCacheCommand ccc = factory.buildCreateCacheCommand(cacheName, baseCacheName);
         StateTransferManager transferManager = clusteredCache.getComponentRegistry().getComponent(StateTransferManager.class);
         try {
            rpc.invokeRemotely(null, ccc, rpc.getDefaultRpcOptions(true));
            ccc.init(cacheManager, transferManager);
            ccc.perform(null);
         } catch (Throwable e) {
            throw log.cannotCreateClusteredCaches(e, cacheName);
         }
      } else {
         ConfigurationBuilder b = new ConfigurationBuilder();
         b.read(configuration);
         cacheManager.defineConfiguration(cacheName, b.build());
         cacheManager.getCache(cacheName);
      }
   }

   @Override
   public void reset() {
      resetCache(cacheManager.getCache());
      for (String cacheName : cacheManager.getCacheNames()) {
         resetCache(cacheManager.getCache(cacheName));
      }
      timestamp = timeService.time();
   }

   private void resetCache(final Cache<Object, Object> cache) {
      Configuration configuration = SecurityActions.getCacheConfiguration(cache.getAdvancedCache());
      if (configuration.invocationBatching().enabled()) {
         cache.endBatch(false);
      }
      TransactionManager tm = cache.getAdvancedCache().getTransactionManager();
      try {
         if (tm.getTransaction() != null) {
            tm.rollback();
         }
      } catch (Exception e) {
      }
   }

   @Override
   public long getTimestamp() {
      return timestamp;
   }

   @Override
   public void setCodec(String codec) throws CodecException {
      this.codec = getCodec(codec);
   }

   @Override
   public Collection<Codec> getCodecs() {
      return codecRegistry.getCodecs();
   }

   @Override
   public Codec getCodec() {
      return codec;
   }

   @Override
   public Codec getCodec(String codec) throws CodecException {
      Codec c = codecRegistry.getCodec(codec);
      if (c == null) {
         throw log.noSuchCodec(codec);
      } else {
         return c;
      }
   }

}


File: core/src/main/java/org/infinispan/commands/CommandsFactoryImpl.java
package org.infinispan.commands;

import org.infinispan.Cache;
import org.infinispan.commands.read.EntryRetrievalCommand;
import org.infinispan.container.entries.CacheEntry;
import org.infinispan.commands.remote.GetKeysInGroupCommand;
import org.infinispan.context.InvocationContextFactory;
import org.infinispan.distribution.group.GroupManager;
import org.infinispan.iteration.impl.EntryRequestCommand;
import org.infinispan.iteration.impl.EntryResponseCommand;
import org.infinispan.iteration.impl.EntryRetriever;
import org.infinispan.metadata.Metadata;
import org.infinispan.atomic.Delta;
import org.infinispan.commands.control.LockControlCommand;
import org.infinispan.commands.module.ModuleCommandInitializer;
import org.infinispan.commands.read.DistributedExecuteCommand;
import org.infinispan.commands.read.EntrySetCommand;
import org.infinispan.commands.read.GetCacheEntryCommand;
import org.infinispan.commands.read.GetKeyValueCommand;
import org.infinispan.commands.read.GetAllCommand;
import org.infinispan.commands.read.KeySetCommand;
import org.infinispan.commands.read.MapCombineCommand;
import org.infinispan.commands.read.ReduceCommand;
import org.infinispan.commands.read.SizeCommand;
import org.infinispan.commands.read.ValuesCommand;
import org.infinispan.commands.remote.ClusteredGetCommand;
import org.infinispan.commands.remote.ClusteredGetAllCommand;
import org.infinispan.commands.remote.MultipleRpcCommand;
import org.infinispan.commands.remote.SingleRpcCommand;
import org.infinispan.commands.remote.recovery.CompleteTransactionCommand;
import org.infinispan.commands.remote.recovery.GetInDoubtTransactionsCommand;
import org.infinispan.commands.remote.recovery.GetInDoubtTxInfoCommand;
import org.infinispan.commands.remote.recovery.TxCompletionNotificationCommand;
import org.infinispan.commands.tx.CommitCommand;
import org.infinispan.commands.tx.PrepareCommand;
import org.infinispan.commands.tx.RollbackCommand;
import org.infinispan.commands.tx.totalorder.TotalOrderCommitCommand;
import org.infinispan.commands.tx.totalorder.TotalOrderNonVersionedPrepareCommand;
import org.infinispan.commands.tx.VersionedCommitCommand;
import org.infinispan.commands.tx.VersionedPrepareCommand;
import org.infinispan.commands.tx.totalorder.TotalOrderRollbackCommand;
import org.infinispan.commands.tx.totalorder.TotalOrderVersionedCommitCommand;
import org.infinispan.commands.tx.totalorder.TotalOrderVersionedPrepareCommand;
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
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.container.DataContainer;
import org.infinispan.container.InternalEntryFactory;
import org.infinispan.context.Flag;
import org.infinispan.distexec.mapreduce.MapReduceManager;
import org.infinispan.distexec.mapreduce.Mapper;
import org.infinispan.distexec.mapreduce.Reducer;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.factories.KnownComponentNames;
import org.infinispan.factories.annotations.ComponentName;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.factories.annotations.Start;
import org.infinispan.interceptors.InterceptorChain;
import org.infinispan.filter.Converter;
import org.infinispan.filter.KeyValueFilter;
import org.infinispan.partitionhandling.impl.PartitionHandlingManager;
import org.infinispan.statetransfer.StateProvider;
import org.infinispan.statetransfer.StateConsumer;
import org.infinispan.statetransfer.StateRequestCommand;
import org.infinispan.statetransfer.StateResponseCommand;
import org.infinispan.statetransfer.StateChunk;
import org.infinispan.notifications.cachelistener.CacheNotifier;
import org.infinispan.remoting.transport.Address;
import org.infinispan.statetransfer.StateTransferManager;
import org.infinispan.transaction.impl.RemoteTransaction;
import org.infinispan.transaction.impl.TransactionTable;
import org.infinispan.transaction.xa.DldGlobalTransaction;
import org.infinispan.transaction.xa.GlobalTransaction;
import org.infinispan.transaction.xa.recovery.RecoveryManager;
import org.infinispan.util.TimeService;
import org.infinispan.util.concurrent.locks.LockManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;
import org.infinispan.xsite.BackupSender;
import org.infinispan.xsite.SingleXSiteRpcCommand;
import org.infinispan.xsite.XSiteAdminCommand;
import org.infinispan.xsite.statetransfer.XSiteState;
import org.infinispan.xsite.statetransfer.XSiteStateConsumer;
import org.infinispan.xsite.statetransfer.XSiteStateProvider;
import org.infinispan.xsite.statetransfer.XSiteStatePushCommand;
import org.infinispan.xsite.statetransfer.XSiteStateTransferControlCommand;
import org.infinispan.xsite.statetransfer.XSiteStateTransferManager;

import javax.transaction.xa.Xid;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Callable;

import static org.infinispan.xsite.XSiteAdminCommand.*;
import static org.infinispan.xsite.statetransfer.XSiteStateTransferControlCommand.*;

/**
 * @author Mircea.Markus@jboss.com
 * @author Galder Zamarreño
 * @author Sanne Grinovero <sanne@hibernate.org> (C) 2011 Red Hat Inc.
 * @since 4.0
 */
public class CommandsFactoryImpl implements CommandsFactory {

   private static final Log log = LogFactory.getLog(CommandsFactoryImpl.class);
   private static final boolean trace = log.isTraceEnabled();


   private DataContainer dataContainer;
   private CacheNotifier<Object, Object> notifier;
   private Cache<Object, Object> cache;
   private String cacheName;
   private boolean totalOrderProtocol;

   private InterceptorChain interceptorChain;
   private DistributionManager distributionManager;
   private InvocationContextFactory icf;
   private TransactionTable txTable;
   private Configuration configuration;
   private RecoveryManager recoveryManager;
   private StateProvider stateProvider;
   private StateConsumer stateConsumer;
   private LockManager lockManager;
   private InternalEntryFactory entryFactory;
   private MapReduceManager mapReduceManager;
   private StateTransferManager stateTransferManager;
   private BackupSender backupSender;
   private CancellationService cancellationService;
   private XSiteStateProvider xSiteStateProvider;
   private XSiteStateConsumer xSiteStateConsumer;
   private XSiteStateTransferManager xSiteStateTransferManager;
   private EntryRetriever entryRetriever;
   private GroupManager groupManager;

   private Map<Byte, ModuleCommandInitializer> moduleCommandInitializers;

   @Inject
   public void setupDependencies(DataContainer container, CacheNotifier<Object, Object> notifier, Cache<Object, Object> cache,
                                 InterceptorChain interceptorChain, DistributionManager distributionManager,
                                 InvocationContextFactory icf, TransactionTable txTable, Configuration configuration,
                                 @ComponentName(KnownComponentNames.MODULE_COMMAND_INITIALIZERS) Map<Byte, ModuleCommandInitializer> moduleCommandInitializers,
                                 RecoveryManager recoveryManager, StateProvider stateProvider, StateConsumer stateConsumer,
                                 LockManager lockManager, InternalEntryFactory entryFactory, MapReduceManager mapReduceManager, 
                                 StateTransferManager stm, BackupSender backupSender, CancellationService cancellationService,
                                 TimeService timeService, XSiteStateProvider xSiteStateProvider, XSiteStateConsumer xSiteStateConsumer,
                                 XSiteStateTransferManager xSiteStateTransferManager, EntryRetriever entryRetriever, GroupManager groupManager, PartitionHandlingManager partitionHandlingManager) {
      this.dataContainer = container;
      this.notifier = notifier;
      this.cache = cache;
      this.interceptorChain = interceptorChain;
      this.distributionManager = distributionManager;
      this.icf = icf;
      this.txTable = txTable;
      this.configuration = configuration;
      this.moduleCommandInitializers = moduleCommandInitializers;
      this.recoveryManager = recoveryManager;
      this.stateProvider = stateProvider;
      this.stateConsumer = stateConsumer;
      this.lockManager = lockManager;
      this.entryFactory = entryFactory;
      this.mapReduceManager = mapReduceManager;
      this.stateTransferManager = stm;
      this.backupSender = backupSender;
      this.cancellationService = cancellationService;
      this.xSiteStateConsumer = xSiteStateConsumer;
      this.xSiteStateProvider = xSiteStateProvider;
      this.xSiteStateTransferManager = xSiteStateTransferManager;
      this.entryRetriever = entryRetriever;
      this.groupManager = groupManager;
   }

   @Start(priority = 1)
   // needs to happen early on
   public void start() {
      cacheName = cache.getName();
      this.totalOrderProtocol = configuration.transaction().transactionProtocol().isTotalOrder();
   }

   @Override
   public PutKeyValueCommand buildPutKeyValueCommand(Object key, Object value, Metadata metadata, Set<Flag> flags) {
      return new PutKeyValueCommand(key, value, false, notifier, metadata, flags,
            configuration.dataContainer().valueEquivalence());
   }

   @Override
   public RemoveCommand buildRemoveCommand(Object key, Object value, Set<Flag> flags) {
      return new RemoveCommand(key, value, notifier, flags, configuration.dataContainer().valueEquivalence());
   }

   @Override
   public InvalidateCommand buildInvalidateCommand(Set<Flag> flags, Object... keys) {
      return new InvalidateCommand(notifier, flags, keys);
   }

   @Override
   public InvalidateCommand buildInvalidateFromL1Command(Set<Flag> flags, Collection<Object> keys) {
      return new InvalidateL1Command(dataContainer, configuration, distributionManager, notifier, flags, keys);
   }

   @Override
   public InvalidateCommand buildInvalidateFromL1Command(Address origin, Set<Flag> flags, Collection<Object> keys) {
      return new InvalidateL1Command(origin, dataContainer, configuration, distributionManager, notifier, flags, keys);
   }

   @Override
   public ReplaceCommand buildReplaceCommand(Object key, Object oldValue, Object newValue, Metadata metadata, Set<Flag> flags) {
      return new ReplaceCommand(key, oldValue, newValue, notifier, metadata, flags, configuration.dataContainer().valueEquivalence());
   }

   @Override
   public SizeCommand buildSizeCommand(Set<Flag> flags) {
      return new SizeCommand(cache, flags);
   }

   @Override
   public KeySetCommand buildKeySetCommand(Set<Flag> flags) {
      return new KeySetCommand(cache, flags);
   }

   @Override
   public ValuesCommand buildValuesCommand(Set<Flag> flags) {
      return new ValuesCommand(cache, flags);
   }

   @Override
   public EntrySetCommand buildEntrySetCommand(Set<Flag> flags) {
      return new EntrySetCommand(cache, flags);
   }

   @Override
   public EntryRetrievalCommand buildEntryRetrievalCommand(Set<Flag> flags, KeyValueFilter filter) {
      return new EntryRetrievalCommand(filter, entryRetriever, flags, cache);
   }

   @Override
   public GetKeyValueCommand buildGetKeyValueCommand(Object key, Set<Flag> flags) {
      return new GetKeyValueCommand(key, flags);
   }

   @Override
   public GetAllCommand buildGetAllCommand(Collection<?> keys,
         Set<Flag> flags, boolean returnEntries) {
      return new GetAllCommand(keys, flags, returnEntries, entryFactory);
   }

   @Override
   public PutMapCommand buildPutMapCommand(Map<?, ?> map, Metadata metadata, Set<Flag> flags) {
      return new PutMapCommand(map, notifier, metadata, flags);
   }

   @Override
   public ClearCommand buildClearCommand(Set<Flag> flags) {
      return new ClearCommand(notifier, dataContainer, flags);
   }

   @Override
   public EvictCommand buildEvictCommand(Object key, Set<Flag> flags) {
      return new EvictCommand(key, notifier, flags);
   }

   @Override
   public PrepareCommand buildPrepareCommand(GlobalTransaction gtx, List<WriteCommand> modifications, boolean onePhaseCommit) {
      return totalOrderProtocol ? new TotalOrderNonVersionedPrepareCommand(cacheName, gtx, modifications) :
            new PrepareCommand(cacheName, gtx, modifications, onePhaseCommit);
   }

   @Override
   public VersionedPrepareCommand buildVersionedPrepareCommand(GlobalTransaction gtx, List<WriteCommand> modifications, boolean onePhase) {
      return totalOrderProtocol ? new TotalOrderVersionedPrepareCommand(cacheName, gtx, modifications, onePhase) :
            new VersionedPrepareCommand(cacheName, gtx, modifications, onePhase);
   }

   @Override
   public CommitCommand buildCommitCommand(GlobalTransaction gtx) {
      return totalOrderProtocol ? new TotalOrderCommitCommand(cacheName, gtx) :
            new CommitCommand(cacheName, gtx);
   }

   @Override
   public VersionedCommitCommand buildVersionedCommitCommand(GlobalTransaction gtx) {
      return totalOrderProtocol ? new TotalOrderVersionedCommitCommand(cacheName, gtx) :
            new VersionedCommitCommand(cacheName, gtx);
   }

   @Override
   public RollbackCommand buildRollbackCommand(GlobalTransaction gtx) {
      return totalOrderProtocol ? new TotalOrderRollbackCommand(cacheName, gtx) : new RollbackCommand(cacheName, gtx);
   }

   @Override
   public MultipleRpcCommand buildReplicateCommand(List<ReplicableCommand> toReplicate) {
      return new MultipleRpcCommand(toReplicate, cacheName);
   }

   @Override
   public SingleRpcCommand buildSingleRpcCommand(ReplicableCommand call) {
      return new SingleRpcCommand(cacheName, call);
   }

   @Override
   public ClusteredGetCommand buildClusteredGetCommand(Object key, Set<Flag> flags, boolean acquireRemoteLock, GlobalTransaction gtx) {
      return new ClusteredGetCommand(key, cacheName, flags, acquireRemoteLock, gtx,
            configuration.dataContainer().keyEquivalence());
   }

   /**
    * @param isRemote true if the command is deserialized and is executed remote.
    */
   @Override
   public void initializeReplicableCommand(ReplicableCommand c, boolean isRemote) {
      if (c == null) return;
      switch (c.getCommandId()) {
         case PutKeyValueCommand.COMMAND_ID:
            ((PutKeyValueCommand) c).init(notifier, configuration);
            break;
         case ReplaceCommand.COMMAND_ID:
            ((ReplaceCommand) c).init(notifier, configuration);
            break;
         case PutMapCommand.COMMAND_ID:
            ((PutMapCommand) c).init(notifier);
            break;
         case RemoveCommand.COMMAND_ID:
            ((RemoveCommand) c).init(notifier, configuration);
            break;
         case MultipleRpcCommand.COMMAND_ID:
            MultipleRpcCommand rc = (MultipleRpcCommand) c;
            rc.init(interceptorChain, icf);
            if (rc.getCommands() != null)
               for (ReplicableCommand nested : rc.getCommands()) {
                  initializeReplicableCommand(nested, false);
               }
            break;
         case SingleRpcCommand.COMMAND_ID:
            SingleRpcCommand src = (SingleRpcCommand) c;
            src.init(interceptorChain, icf);
            if (src.getCommand() != null)
               initializeReplicableCommand(src.getCommand(), false);

            break;
         case InvalidateCommand.COMMAND_ID:
            InvalidateCommand ic = (InvalidateCommand) c;
            ic.init(notifier, configuration);
            break;
         case InvalidateL1Command.COMMAND_ID:
            InvalidateL1Command ilc = (InvalidateL1Command) c;
            ilc.init(configuration, distributionManager, notifier, dataContainer);
            break;
         case PrepareCommand.COMMAND_ID:
         case VersionedPrepareCommand.COMMAND_ID:
         case TotalOrderNonVersionedPrepareCommand.COMMAND_ID:
         case TotalOrderVersionedPrepareCommand.COMMAND_ID:
            PrepareCommand pc = (PrepareCommand) c;
            pc.init(interceptorChain, icf, txTable);
            pc.initialize(notifier, recoveryManager);
            if (pc.getModifications() != null)
               for (ReplicableCommand nested : pc.getModifications())  {
                  initializeReplicableCommand(nested, false);
               }
            pc.markTransactionAsRemote(isRemote);
            if (configuration.deadlockDetection().enabled() && isRemote) {
               DldGlobalTransaction transaction = (DldGlobalTransaction) pc.getGlobalTransaction();
               transaction.setLocksHeldAtOrigin(pc.getAffectedKeys());
            }
            break;
         case CommitCommand.COMMAND_ID:
         case VersionedCommitCommand.COMMAND_ID:
         case TotalOrderCommitCommand.COMMAND_ID:
         case TotalOrderVersionedCommitCommand.COMMAND_ID:
            CommitCommand commitCommand = (CommitCommand) c;
            commitCommand.init(interceptorChain, icf, txTable);
            commitCommand.markTransactionAsRemote(isRemote);
            break;
         case RollbackCommand.COMMAND_ID:
         case TotalOrderRollbackCommand.COMMAND_ID:
            RollbackCommand rollbackCommand = (RollbackCommand) c;
            rollbackCommand.init(interceptorChain, icf, txTable);
            rollbackCommand.markTransactionAsRemote(isRemote);
            break;
         case ClearCommand.COMMAND_ID:
            ClearCommand cc = (ClearCommand) c;
            cc.init(notifier, dataContainer);
            break;
         case ClusteredGetCommand.COMMAND_ID:
            ClusteredGetCommand clusteredGetCommand = (ClusteredGetCommand) c;
            clusteredGetCommand.initialize(icf, this, entryFactory,
                  interceptorChain, distributionManager, txTable,
                  configuration.dataContainer().keyEquivalence());
            break;
         case LockControlCommand.COMMAND_ID:
            LockControlCommand lcc = (LockControlCommand) c;
            lcc.init(interceptorChain, icf, txTable);
            lcc.markTransactionAsRemote(isRemote);
            if (configuration.deadlockDetection().enabled() && isRemote) {
               DldGlobalTransaction gtx = (DldGlobalTransaction) lcc.getGlobalTransaction();
               RemoteTransaction transaction = txTable.getRemoteTransaction(gtx);
               if (transaction != null) {
                  if (!configuration.clustering().cacheMode().isDistributed()) {
                     Set<Object> keys = txTable.getLockedKeysForRemoteTransaction(gtx);
                     GlobalTransaction gtx2 = transaction.getGlobalTransaction();
                     ((DldGlobalTransaction) gtx2).setLocksHeldAtOrigin(keys);
                     gtx.setLocksHeldAtOrigin(keys);
                  } else {
                     GlobalTransaction gtx2 = transaction.getGlobalTransaction();
                     ((DldGlobalTransaction) gtx2).setLocksHeldAtOrigin(gtx.getLocksHeldAtOrigin());
                  }
               }
            }
            break;
         case StateRequestCommand.COMMAND_ID:
            ((StateRequestCommand) c).init(stateProvider);
            break;
         case StateResponseCommand.COMMAND_ID:
            ((StateResponseCommand) c).init(stateConsumer);
            break;
         case GetInDoubtTransactionsCommand.COMMAND_ID:
            GetInDoubtTransactionsCommand gptx = (GetInDoubtTransactionsCommand) c;
            gptx.init(recoveryManager);
            break;
         case TxCompletionNotificationCommand.COMMAND_ID:
            TxCompletionNotificationCommand ftx = (TxCompletionNotificationCommand) c;
            ftx.init(txTable, lockManager, recoveryManager, stateTransferManager);
            break;
         case MapCombineCommand.COMMAND_ID:
            MapCombineCommand mrc = (MapCombineCommand)c;
            mrc.init(mapReduceManager);
            break;
         case ReduceCommand.COMMAND_ID:
            ReduceCommand reduceCommand = (ReduceCommand)c;
            reduceCommand.init(mapReduceManager);
            break;
         case DistributedExecuteCommand.COMMAND_ID:
            DistributedExecuteCommand dec = (DistributedExecuteCommand)c;
            dec.init(cache);
            break;
         case GetInDoubtTxInfoCommand.COMMAND_ID:
            GetInDoubtTxInfoCommand gidTxInfoCommand = (GetInDoubtTxInfoCommand)c;
            gidTxInfoCommand.init(recoveryManager);
            break;
         case CompleteTransactionCommand.COMMAND_ID:
            CompleteTransactionCommand ccc = (CompleteTransactionCommand)c;
            ccc.init(recoveryManager);
            break;
         case ApplyDeltaCommand.COMMAND_ID:
            break;
         case CreateCacheCommand.COMMAND_ID:
            CreateCacheCommand createCacheCommand = (CreateCacheCommand)c;
            createCacheCommand.init(cache.getCacheManager(), stateTransferManager);
            break;
         case XSiteAdminCommand.COMMAND_ID:
            XSiteAdminCommand xSiteAdminCommand = (XSiteAdminCommand)c;
            xSiteAdminCommand.init(backupSender);
            break;
         case CancelCommand.COMMAND_ID:
            CancelCommand cancelCommand = (CancelCommand)c;
            cancelCommand.init(cancellationService);
            break;
         case XSiteStateTransferControlCommand.COMMAND_ID:
            XSiteStateTransferControlCommand xSiteStateTransferControlCommand = (XSiteStateTransferControlCommand) c;
            xSiteStateTransferControlCommand.initialize(xSiteStateProvider, xSiteStateConsumer, xSiteStateTransferManager);
            break;
         case XSiteStatePushCommand.COMMAND_ID:
            XSiteStatePushCommand xSiteStatePushCommand = (XSiteStatePushCommand) c;
            xSiteStatePushCommand.initialize(xSiteStateConsumer);
            break;
         case EntryRequestCommand.COMMAND_ID:
            EntryRequestCommand entryRequestCommand = (EntryRequestCommand) c;
            entryRequestCommand.init(entryRetriever);
            break;
         case EntryResponseCommand.COMMAND_ID:
            EntryResponseCommand entryResponseCommand = (EntryResponseCommand) c;
            entryResponseCommand.init(entryRetriever);
            break;
         case GetKeysInGroupCommand.COMMAND_ID:
            GetKeysInGroupCommand getKeysInGroupCommand = (GetKeysInGroupCommand) c;
            getKeysInGroupCommand.setGroupManager(groupManager);
            break;
         case ClusteredGetAllCommand.COMMAND_ID:
            ClusteredGetAllCommand clusteredGetAllCommand = (ClusteredGetAllCommand) c;
            clusteredGetAllCommand.init(icf, this, entryFactory, interceptorChain, txTable,
                  configuration.dataContainer().keyEquivalence());
            break;
         default:
            ModuleCommandInitializer mci = moduleCommandInitializers.get(c.getCommandId());
            if (mci != null) {
               mci.initializeReplicableCommand(c, isRemote);
            } else {
               if (trace) log.tracef("Nothing to initialize for command: %s", c);
            }
      }
   }

   @Override
   public LockControlCommand buildLockControlCommand(Collection<?> keys, Set<Flag> flags, GlobalTransaction gtx) {
      return new LockControlCommand(keys, cacheName, flags, gtx);
   }

   @Override
   public LockControlCommand buildLockControlCommand(Object key, Set<Flag> flags, GlobalTransaction gtx) {
      return new LockControlCommand(key, cacheName, flags, gtx);
   }

   @Override
   public LockControlCommand buildLockControlCommand(Collection<?> keys, Set<Flag> flags) {
      return new LockControlCommand(keys,  cacheName, flags, null);
   }

   @Override
   public StateRequestCommand buildStateRequestCommand(StateRequestCommand.Type subtype, Address sender, int viewId, Set<Integer> segments) {
      return new StateRequestCommand(cacheName, subtype, sender, viewId, segments);
   }

   @Override
   public StateResponseCommand buildStateResponseCommand(Address sender, int topologyId, Collection<StateChunk> stateChunks) {
      return new StateResponseCommand(cacheName, sender, topologyId, stateChunks);
   }

   @Override
   public String getCacheName() {
      return cacheName;
   }

   @Override
   public GetInDoubtTransactionsCommand buildGetInDoubtTransactionsCommand() {
      return new GetInDoubtTransactionsCommand(cacheName);
   }

   @Override
   public TxCompletionNotificationCommand buildTxCompletionNotificationCommand(Xid xid, GlobalTransaction globalTransaction) {
      return new TxCompletionNotificationCommand(xid, globalTransaction, cacheName);
   }

   @Override
   public TxCompletionNotificationCommand buildTxCompletionNotificationCommand(long internalId) {
      return new TxCompletionNotificationCommand(internalId, cacheName);
   }

   @Override
   public <T> DistributedExecuteCommand<T> buildDistributedExecuteCommand(Callable<T> callable, Address sender, Collection keys) {
      return new DistributedExecuteCommand<T>(cacheName, keys, callable);
   }

   @Override
   public <KIn, VIn, KOut, VOut> MapCombineCommand<KIn, VIn, KOut, VOut> buildMapCombineCommand(
            String taskId, Mapper<KIn, VIn, KOut, VOut> m, Reducer<KOut, VOut> r,
            Collection<KIn> keys) {
      return new MapCombineCommand<KIn, VIn, KOut, VOut>(taskId, m, r, cacheName, keys);
   }

   @Override
   public GetInDoubtTxInfoCommand buildGetInDoubtTxInfoCommand() {
      return new GetInDoubtTxInfoCommand(cacheName);
   }

   @Override
   public CompleteTransactionCommand buildCompleteTransactionCommand(Xid xid, boolean commit) {
      return new CompleteTransactionCommand(cacheName, xid, commit);
   }

   @Override
   public ApplyDeltaCommand buildApplyDeltaCommand(Object deltaAwareValueKey, Delta delta, Collection keys) {
      return new ApplyDeltaCommand(deltaAwareValueKey, delta, keys);
   }

   @Override
   public CreateCacheCommand buildCreateCacheCommand(String cacheNameToCreate, String cacheConfigurationName) {
      return new CreateCacheCommand(cacheName, cacheNameToCreate, cacheConfigurationName);
   }

   @Override
   public CreateCacheCommand buildCreateCacheCommand(String cacheNameToCreate, String cacheConfigurationName, boolean start, int size) {
      return new CreateCacheCommand(cacheName, cacheNameToCreate, cacheConfigurationName, start, size);
   }

   @Override
   public <KOut, VOut> ReduceCommand<KOut, VOut> buildReduceCommand(String taskId,
            String destintationCache, Reducer<KOut, VOut> r, Collection<KOut> keys) {
      return new ReduceCommand<KOut, VOut>(taskId, r, destintationCache, keys);
   }

   @Override
   public CancelCommand buildCancelCommandCommand(UUID commandUUID) {
      return new CancelCommand(cacheName, commandUUID);
   }

   @Override
   public XSiteStateTransferControlCommand buildXSiteStateTransferControlCommand(StateTransferControl control,
                                                                                 String siteName) {
      return new XSiteStateTransferControlCommand(cacheName, control, siteName);
   }

   @Override
   public XSiteAdminCommand buildXSiteAdminCommand(String siteName, AdminOperation op, Integer afterFailures,
                                                   Long minTimeToWait) {
      return new XSiteAdminCommand(cacheName, siteName, op, afterFailures, minTimeToWait);
   }

   @Override
   public XSiteStatePushCommand buildXSiteStatePushCommand(XSiteState[] chunk, long timeoutMillis) {
      return new XSiteStatePushCommand(cacheName, chunk, timeoutMillis);
   }

   @Override
   public SingleXSiteRpcCommand buildSingleXSiteRpcCommand(VisitableCommand command) {
      return new SingleXSiteRpcCommand(cacheName, command);
   }

   @Override
   public <K, V, C> EntryRequestCommand<K, V, C> buildEntryRequestCommand(UUID identifier, Set<Integer> segments,
                                                                    Set<K> keysToFilter,
                                                                    KeyValueFilter<? super K, ? super V> filter,
                                                                    Converter<? super K, ? super V, C> converter,
                                                                    Set<Flag> flags) {
      return new EntryRequestCommand<K, V, C>(cacheName, identifier, cache.getCacheManager().getAddress(), segments,
                                              keysToFilter, filter, converter, flags);
   }

   @Override
   public <K, C> EntryResponseCommand<K, C> buildEntryResponseCommand(UUID identifier, Set<Integer> completedSegments,
                                                                Set<Integer> inDoubtSegments,
                                                                Collection<CacheEntry<K, C>> values, CacheException e) {
      return new EntryResponseCommand<>(cache.getCacheManager().getAddress(), cacheName, identifier, completedSegments,
                                      inDoubtSegments, values, e);
   }

   @Override
   public GetKeysInGroupCommand buildGetKeysInGroupCommand(Set<Flag> flags, String groupName) {
      return new GetKeysInGroupCommand(flags, groupName).setGroupManager(groupManager);
   }

   @Override
   public GetCacheEntryCommand buildGetCacheEntryCommand(Object key, Set<Flag> explicitFlags) {
      return new GetCacheEntryCommand(key, explicitFlags, entryFactory);
   }

   @Override
   public ClusteredGetAllCommand buildClusteredGetAllCommand(List<?> keys, Set<Flag> flags, GlobalTransaction gtx) {
      return new ClusteredGetAllCommand(cacheName, keys, flags, gtx, configuration.dataContainer().keyEquivalence());
   }

}


File: core/src/main/java/org/infinispan/commands/CreateCacheCommand.java
package org.infinispan.commands;

import java.util.concurrent.TimeUnit;

import org.infinispan.commands.remote.BaseRpcCommand;
import org.infinispan.configuration.cache.CacheMode;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.configuration.cache.ConfigurationBuilder;
import org.infinispan.context.InvocationContext;
import org.infinispan.distexec.mapreduce.MapReduceTask;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.statetransfer.StateTransferManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

/**
 * Command to create/start a cache on a subset of Infinispan cluster nodes
 * @author Vladimir Blagojevic
 * @since 5.2
 */
public class CreateCacheCommand extends BaseRpcCommand {

   private static final Log log = LogFactory.getLog(CreateCacheCommand.class);
   public static final byte COMMAND_ID = 29;

   private EmbeddedCacheManager cacheManager;
   private StateTransferManager stm;
   private String cacheNameToCreate;
   private String cacheConfigurationName;
   private boolean start;
   private int size;

   private CreateCacheCommand() {
      super(null);
   }

   public CreateCacheCommand(String ownerCacheName) {
      super(ownerCacheName);
   }

   public CreateCacheCommand(String ownerCacheName, String cacheNameToCreate, String cacheConfigurationName) {
      this(ownerCacheName, cacheNameToCreate, cacheConfigurationName, false, 0);
   }

   public CreateCacheCommand(String cacheName, String cacheNameToCreate, String cacheConfigurationName, boolean start, int size) {
      super(cacheName);
      this.cacheNameToCreate = cacheNameToCreate;
      this.cacheConfigurationName = cacheConfigurationName;
      this.start = start;
      this.size = size;
   }

   public void init(EmbeddedCacheManager cacheManager, StateTransferManager stateTransferManager){
      this.cacheManager = cacheManager;
      this.stm = stateTransferManager;
   }

   @Override
   public Object perform(InvocationContext ctx) throws Throwable {
      Configuration cacheConfig = null;
      if (cacheConfigurationName != null) {
         cacheConfig = cacheManager.getCacheConfiguration(cacheConfigurationName);
         if (cacheConfig == null) {
            // Special case for the default temporary cache, which may or may not have been defined by the user
            if (MapReduceTask.DEFAULT_TMP_CACHE_CONFIGURATION_NAME.equals(cacheConfigurationName)) {
               cacheConfig = new ConfigurationBuilder().unsafe().unreliableReturnValues(true).clustering()
                     .cacheMode(CacheMode.DIST_SYNC).hash().numOwners(2).sync().build();
               log.debugf("Using default tmp cache configuration, defined as ", cacheNameToCreate);
            } else {
               throw new IllegalStateException("Cache configuration " + cacheConfigurationName
                     + " is not defined on node " + this.cacheManager.getAddress());
            }
         }
      }

      cacheManager.defineConfiguration(cacheNameToCreate, cacheConfig);
      cacheManager.getCache(cacheNameToCreate);
      final long startTime = System.nanoTime();
      final long maxRunTime = TimeUnit.MILLISECONDS.toNanos(cacheConfig.clustering().stateTransfer().timeout());
      int expectedSize = cacheManager.getTransport().getMembers().size();
      while (stm.getCacheTopology().getMembers().size() != expectedSize && stm.getCacheTopology().getPendingCH() != null) {
         Thread.sleep(50);
         long estimatedRunTime = System.nanoTime() - startTime;
         if (estimatedRunTime > maxRunTime) {
            throw log.creatingTmpCacheTimedOut(cacheNameToCreate, cacheManager.getAddress());
         }
      }
      log.debugf("Defined and started cache %s", cacheNameToCreate);
      return true;
   }

   @Override
   public byte getCommandId() {
      return COMMAND_ID;
   }

   @Override
   public Object[] getParameters() {
      return new Object[] {cacheNameToCreate, cacheConfigurationName, start, size};
   }

   @Override
   public void setParameters(int commandId, Object[] parameters) {
      if (commandId != COMMAND_ID)
         throw new IllegalStateException("Invalid method id " + commandId + " but " +
                                               this.getClass() + " has id " + getCommandId());
      int i = 0;
      cacheNameToCreate = (String) parameters[i++];
      cacheConfigurationName = (String) parameters[i++];
      start = (Boolean) parameters[i++];
      size = (Integer) parameters[i];
   }

   @Override
   public int hashCode() {
      final int prime = 31;
      int result = 1;
      result = prime * result
               + ((cacheConfigurationName == null) ? 0 : cacheConfigurationName.hashCode());
      result = prime * result + ((cacheNameToCreate == null) ? 0 : cacheNameToCreate.hashCode());
      return result;
   }

   @Override
   public boolean equals(Object obj) {
      if (this == obj) {
         return true;
      }
      if (obj == null) {
         return false;
      }
      if (!(obj instanceof CreateCacheCommand)) {
         return false;
      }
      CreateCacheCommand other = (CreateCacheCommand) obj;
      if (cacheConfigurationName == null) {
         if (other.cacheConfigurationName != null) {
            return false;
         }
      } else if (!cacheConfigurationName.equals(other.cacheConfigurationName)) {
         return false;
      }
      if (cacheNameToCreate == null) {
         if (other.cacheNameToCreate != null) {
            return false;
         }
      } else if (!cacheNameToCreate.equals(other.cacheNameToCreate)) {
         return false;
      }
      return this.start == other.start && this.size == other.size;
   }

   @Override
   public String toString() {
      return "CreateCacheCommand{" +
            "cacheManager=" + cacheManager +
            ", cacheNameToCreate='" + cacheNameToCreate + '\'' +
            ", cacheConfigurationName='" + cacheConfigurationName + '\'' +
            ", start=" + start + '\'' +
            ", size=" + size +
            '}';
   }

   @Override
   public boolean isReturnValueExpected() {
      return true;
   }

   @Override
   public boolean canBlock() {
      return true;
   }
}


File: core/src/main/java/org/infinispan/distexec/mapreduce/MapReduceManagerImpl.java
package org.infinispan.distexec.mapreduce;

import org.infinispan.Cache;
import org.infinispan.atomic.Delta;
import org.infinispan.atomic.DeltaAware;
import org.infinispan.commands.read.MapCombineCommand;
import org.infinispan.commands.read.ReduceCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.marshall.AbstractExternalizer;
import org.infinispan.commons.util.CollectionFactory;
import org.infinispan.commons.util.Util;
import org.infinispan.configuration.cache.Configuration;
import org.infinispan.container.DataContainer;
import org.infinispan.container.entries.InternalCacheEntry;
import org.infinispan.context.Flag;
import org.infinispan.distexec.mapreduce.spi.MapReduceTaskLifecycleService;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.factories.annotations.ComponentName;
import org.infinispan.factories.annotations.Inject;
import org.infinispan.filter.CollectionKeyFilter;
import org.infinispan.filter.CompositeKeyFilter;
import org.infinispan.filter.KeyFilter;
import org.infinispan.interceptors.locking.ClusteringDependentLogic;
import org.infinispan.persistence.manager.PersistenceManager;
import org.infinispan.persistence.PrimaryOwnerFilter;
import org.infinispan.persistence.spi.AdvancedCacheLoader;
import org.infinispan.persistence.spi.AdvancedCacheLoader.TaskContext;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.marshall.core.Ids;
import org.infinispan.marshall.core.MarshalledEntry;
import org.infinispan.marshall.core.MarshalledValue;
import org.infinispan.remoting.transport.Address;
import org.infinispan.util.TimeService;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.io.IOException;
import java.io.ObjectInput;
import java.io.ObjectOutput;
import java.io.Serializable;
import java.util.*;
import java.util.Map.Entry;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BiConsumer;

import static org.infinispan.factories.KnownComponentNames.ASYNC_TRANSPORT_EXECUTOR;

/**
 * Default implementation of {@link MapReduceManager}.
 * <p>
 *
 *
 * This is an internal class, not intended to be used by clients.
 * @author Vladimir Blagojevic
 * @since 5.2
 */
public class MapReduceManagerImpl implements MapReduceManager {

   private static final Log log = LogFactory.getLog(MapReduceManagerImpl.class);
   private ClusteringDependentLogic cdl;
   private EmbeddedCacheManager cacheManager;
   private PersistenceManager persistenceManager;
   private ExecutorService executorService;
   private TimeService timeService;
   private int chunkSize;

   MapReduceManagerImpl() {
   }

   @Inject
   public void init(EmbeddedCacheManager cacheManager, PersistenceManager persistenceManager,
            @ComponentName(ASYNC_TRANSPORT_EXECUTOR) ExecutorService asyncTransportExecutor,
            ClusteringDependentLogic cdl, TimeService timeService, Configuration configuration) {
      this.cacheManager = cacheManager;
      this.persistenceManager = persistenceManager;
      this.cdl = cdl;
      this.executorService = asyncTransportExecutor;
      this.timeService = timeService;
      this.chunkSize = configuration.clustering().stateTransfer().chunkSize();
   }

   @Override
   public ExecutorService getExecutorService() {
      return executorService;
   }

   @Override
   public <KIn, VIn, KOut, VOut> Map<KOut, List<VOut>> mapAndCombineForLocalReduction(
            MapCombineCommand<KIn, VIn, KOut, VOut> mcc) throws InterruptedException {
      CollectableCollector<KOut, VOut> collector = map(mcc);
      combine(mcc, collector);
      return collector.collectedValues();
   }

   @Override
   public <KIn, VIn, KOut, VOut> Set<KOut> mapAndCombineForDistributedReduction(
            MapCombineCommand<KIn, VIn, KOut, VOut> mcc) throws InterruptedException {
      try {
         return mapAndCombine(mcc);
      } catch (Exception e) {
         throw new CacheException(e);
      }
   }

   @Override
   public <KOut, VOut> Map<KOut, VOut> reduce(ReduceCommand<KOut, VOut> reduceCommand) throws InterruptedException {
      final Map<KOut, VOut> result = CollectionFactory.makeConcurrentMap(256);
      reduce(reduceCommand, result);
      return result;
   }

   @Override
   public <KOut, VOut> void reduce(ReduceCommand<KOut, VOut> reduceCommand, String resultCache) throws InterruptedException{
      Cache<KOut, VOut> cache = cacheManager.getCache(resultCache);
      reduce(reduceCommand, cache);
   }

   protected <KOut, VOut> void reduce(ReduceCommand<KOut, VOut> reduceCommand, final Map<KOut, VOut> result)
         throws InterruptedException {
      final Set<KOut> keys = reduceCommand.getKeys();
      final String taskId = reduceCommand.getTaskId();
      boolean noInputKeys = keys == null || keys.isEmpty();

      if (noInputKeys) {
         //illegal state, raise exception
         throw new IllegalStateException("Reduce phase of MapReduceTask " + taskId + " on node " + cdl.getAddress()
               + " executed with empty input keys");
      } else {
         final Reducer<KOut, VOut> reducer = reduceCommand.getReducer();
         final boolean sharedTmpCacheUsed = reduceCommand.isUseIntermediateSharedCache();
         MapReduceTaskLifecycleService taskLifecycleService = MapReduceTaskLifecycleService.getInstance();
         log.tracef("For m/r task %s invoking %s at %s", taskId, reduceCommand, cdl.getAddress());
         long start = log.isTraceEnabled() ? timeService.time() : 0;
         try {
            Cache<IntermediateKey<KOut>, List<VOut>> cache = cacheManager.getCache(reduceCommand.getCacheName());
            taskLifecycleService.onPreExecute(reducer, cache);
            KeyFilter<IntermediateKey<KOut>> filter = new IntermediateKeyFilter<KOut>(taskId, !sharedTmpCacheUsed);
            //iterate all tmp cache entries in memory, do it in parallel
            DataContainer<IntermediateKey<KOut>, List<VOut>> dc = cache.getAdvancedCache().getDataContainer();
            dc.executeTask(filter, new DataContainerTask<IntermediateKey<KOut>, List<VOut>>() {
               @Override
               public void accept(IntermediateKey<KOut> k, InternalCacheEntry<IntermediateKey<KOut>, List<VOut>> v) {
                  KOut key = k.getKey();
                  //resolve Iterable<VOut> for iterated key stored in tmp cache
                  Iterable<VOut> value = getValue(v);
                  if (value == null) {
                     throw new IllegalStateException("Found invalid value in intermediate cache, for key " + key
                           + " during reduce phase execution on " + cacheManager.getAddress() + " for M/R task "
                           + taskId);
                  }
                  // and reduce it
                  VOut reduced = reducer.reduce(key, value.iterator());
                  result.put(key, reduced);
                  log.tracef("For m/r task %s reduced %s to %s at %s ", taskId, key, reduced, cdl.getAddress());
               }
            });

         } finally {
            if (log.isTraceEnabled()) {
               log.tracef("Reduce for task %s took %s milliseconds", reduceCommand.getTaskId(),
                     timeService.timeDuration(start, TimeUnit.MILLISECONDS));
            }
            taskLifecycleService.onPostExecute(reducer);
         }
      }
   }

   @SuppressWarnings("unchecked")
   protected <KIn, VIn, KOut, VOut> CollectableCollector<KOut, VOut> map(
            MapCombineCommand<KIn, VIn, KOut, VOut> mcc) throws InterruptedException {
      final Cache<KIn, VIn> cache = cacheManager.getCache(mcc.getCacheName());
      Set<KIn> keys = mcc.getKeys();
      int maxCSize = mcc.getMaxCollectorSize();
      final Mapper<KIn, VIn, KOut, VOut> mapper = mcc.getMapper();
      final boolean inputKeysSpecified = keys != null && !keys.isEmpty();

      // hook map function into lifecycle and execute it
      MapReduceTaskLifecycleService taskLifecycleService = MapReduceTaskLifecycleService.getInstance();
      final CollectableCollector<KOut, VOut> collector = new SynchronizedCollector<KOut, VOut>(
            new DefaultCollector<KIn, VIn, KOut, VOut>(mcc, maxCSize));
      DataContainer<KIn, VIn> dc = cache.getAdvancedCache().getDataContainer();
      log.tracef("For m/r task %s invoking %s with input keys %s",  mcc.getTaskId(), mcc, keys);
      long start = log.isTraceEnabled() ? timeService.time() : 0;
      try {
         taskLifecycleService.onPreExecute(mapper, cache);
         //User specified input taks keys, most likely a short list of input keys (<10^3), iterate serially
         if (inputKeysSpecified) {
            for (KIn key : keys) {
               VIn value = cache.get(key);
               if (value != null) {
                  mapper.map(key, value, collector);
               }
            }
         } else {
            // here we have to iterate all entries in memory, do it in parallel
            dc.executeTask(new PrimaryOwnerFilter<KIn>(cdl), new DataContainerTask<KIn, VIn>() {
               @Override
               public void accept(KIn key , InternalCacheEntry<KIn, VIn> v) {
                  VIn value = getValue(v);
                  if (value != null) {
                     mapper.map(key, value, collector);
                  }
               }
            });
         }
         // in case we have stores, we have to process key/values from there as well
         if (persistenceManager != null && !inputKeysSpecified) {
               KeyFilter<?> keyFilter = new CompositeKeyFilter<KIn>(new PrimaryOwnerFilter<KIn>(cdl), new CollectionKeyFilter<KIn>(dc.keySet()));
               persistenceManager.processOnAllStores(keyFilter, new MapReduceCacheLoaderTask<KIn, VIn, KOut, VOut>(mapper, collector),
                     true, false);
         }
      } finally {
         if (log.isTraceEnabled()) {
            log.tracef("Map phase for task %s took %s milliseconds",
                       mcc.getTaskId(), timeService.timeDuration(start, TimeUnit.MILLISECONDS));
         }
         taskLifecycleService.onPostExecute(mapper);
      }
      return collector;
   }

   @SuppressWarnings("unchecked")
   protected <KIn, VIn, KOut, VOut> Set<KOut> mapAndCombine(final MapCombineCommand<KIn, VIn, KOut, VOut> mcc)
         throws Exception {

      final Cache<KIn, VIn> cache = cacheManager.getCache(mcc.getCacheName());
      Set<KIn> keys = mcc.getKeys();
      int maxCSize = mcc.getMaxCollectorSize();
      final Mapper<KIn, VIn, KOut, VOut> mapper = mcc.getMapper();
      final boolean inputKeysSpecified = keys != null && !keys.isEmpty();
      // hook map function into lifecycle and execute it
      MapReduceTaskLifecycleService taskLifecycleService = MapReduceTaskLifecycleService.getInstance();
      DataContainer<KIn, VIn>  dc = cache.getAdvancedCache().getDataContainer();
      log.tracef("For m/r task %s invoking %s with input keys %s", mcc.getTaskId(), mcc, mcc.getKeys());
      long start = log.isTraceEnabled() ? timeService.time() : 0;
      final Set<KOut> intermediateKeys = new HashSet<KOut>();
      try {
         taskLifecycleService.onPreExecute(mapper, cache);
         if (inputKeysSpecified) {
            DefaultCollector<KIn, VIn, KOut, VOut> c = new DefaultCollector<KIn, VIn, KOut, VOut>(mcc, maxCSize);
            for (KIn key : keys) {
               VIn value = cache.get(key);
               if (value != null) {
                  mapper.map(key, value, c);
               }
            }
            combine(mcc, c);
            Set<KOut> s = migrateIntermediateKeysAndValues(mcc, c.collectedValues());
            intermediateKeys.addAll(s);
         } else {
            MapCombineTask<KIn, VIn, KOut, VOut> task = new MapCombineTask<KIn, VIn, KOut, VOut>(mcc, maxCSize);
            dc.executeTask(new PrimaryOwnerFilter<KIn>(cdl), task);
            intermediateKeys.addAll(task.getMigratedIntermediateKeys());
            //the last chunk of remaining keys/values to migrate
            Map<KOut, List<VOut>> combinedValues = task.collectedValues();
            Set<KOut> lastOne = migrateIntermediateKeysAndValues(mcc, combinedValues);
            intermediateKeys.addAll(lastOne);
         }

         // in case we have stores, we have to process key/values from there as well
         if (persistenceManager != null && !inputKeysSpecified) {
            KeyFilter<KIn> keyFilter = new CompositeKeyFilter<KIn>(new PrimaryOwnerFilter<KIn>(cdl),
                  new CollectionKeyFilter<KIn>(dc.keySet()));

            MapCombineTask<KIn, VIn, KOut, VOut> task = new MapCombineTask<KIn, VIn, KOut, VOut>(mcc, maxCSize);
            persistenceManager.processOnAllStores(keyFilter, task, true, false);
            intermediateKeys.addAll(task.getMigratedIntermediateKeys());
            //the last chunk of remaining keys/values to migrate
            Map<KOut, List<VOut>> combinedValues =  task.collectedValues();
            Set<KOut> lastOne = migrateIntermediateKeysAndValues(mcc, combinedValues);
            intermediateKeys.addAll(lastOne);
         }
      } finally {
         if (log.isTraceEnabled()) {
            log.tracef("Map phase for task %s took %s milliseconds", mcc.getTaskId(),
                  timeService.timeDuration(start, TimeUnit.MILLISECONDS));
         }
         taskLifecycleService.onPostExecute(mapper);
      }
      return intermediateKeys;
   }

   protected <KIn, VIn, KOut, VOut> void combine(MapCombineCommand<KIn, VIn, KOut, VOut> mcc,
         CollectableCollector<KOut, VOut> c) {
      if (mcc.hasCombiner()) {
         Reducer<KOut, VOut> combiner = mcc.getCombiner();
         Cache<?, ?> cache = cacheManager.getCache(mcc.getCacheName());
         log.tracef("For m/r task %s invoking combiner %s at %s", mcc.getTaskId(), mcc, cdl.getAddress());
         MapReduceTaskLifecycleService taskLifecycleService = MapReduceTaskLifecycleService.getInstance();
         long start = log.isTraceEnabled() ? timeService.time() : 0;
         try {
            taskLifecycleService.onPreExecute(combiner, cache);
            for (Entry<KOut, List<VOut>> e : c.collectedValues().entrySet()) {
               List<VOut> mapped = e.getValue();
               if (mapped.size() > 1) {
                   VOut reduced = combiner.reduce(e.getKey(), mapped.iterator());
                   c.emitReduced(e.getKey(), reduced);
               }
            }
         } finally {
            if (log.isTraceEnabled()) {
               log.tracef("Combine for task %s took %s milliseconds", mcc.getTaskId(),
                     timeService.timeDuration(start, TimeUnit.MILLISECONDS));
            }
            taskLifecycleService.onPostExecute(combiner);
         }
      }
   }

   private <KIn, VIn, KOut, VOut> Set<KOut> migrateIntermediateKeysAndValues(
         MapCombineCommand<KIn, VIn, KOut, VOut> mcc, Map<KOut, List<VOut>> collectedValues) {

      String taskId =  mcc.getTaskId();
      String tmpCacheName = mcc.getIntermediateCacheName();
      Cache<IntermediateKey<KOut>, DeltaList<VOut>> tmpCache = cacheManager.getCache(tmpCacheName);
      if (tmpCache == null) {
         throw new IllegalStateException("Temporary cache for MapReduceTask " + taskId
                  + " named " + tmpCacheName + " not found on " + cdl.getAddress());
      }

      Set<KOut> mapPhaseKeys = new HashSet<KOut>();
      DistributionManager dm = tmpCache.getAdvancedCache().getDistributionManager();
      Map<Address, List<KOut>> keysToNodes = mapKeysToNodes(dm, taskId, collectedValues.keySet());
      long start = log.isTraceEnabled() ? timeService.time() : 0;
      tmpCache = tmpCache.getAdvancedCache().withFlags(Flag.IGNORE_RETURN_VALUES);
      try {
         for (Entry<Address, List<KOut>> entry : keysToNodes.entrySet()) {
            List<KOut> keysHashedToAddress = entry.getValue();
            try {
               log.tracef("For m/r task %s migrating intermediate keys %s to %s", taskId, keysHashedToAddress, entry.getKey());
               for (KOut key : keysHashedToAddress) {
                  List<VOut> values = collectedValues.get(key);
                  int entryTransferCount = chunkSize;
                  for (int i = 0; i < values.size(); i += entryTransferCount) {
                     List<VOut> chunk = values.subList(i, Math.min(values.size(), i + entryTransferCount));
                     DeltaList<VOut> delta = new DeltaList<VOut>(chunk);
                     tmpCache.put(new IntermediateKey<KOut>(taskId, key), delta);
                  }
                  mapPhaseKeys.add(key);
               }
            } catch (Exception e) {
               throw new CacheException("Could not move intermediate keys/values for M/R task " + taskId, e);
            }
         }
      } finally {
         if (log.isTraceEnabled()) {
            log.tracef("Migrating keys for task %s took %s milliseconds (Migrated %s keys)",
                  mcc.getTaskId(), timeService.timeDuration(start, TimeUnit.MILLISECONDS), mapPhaseKeys.size());
         }
      }
      return mapPhaseKeys;
   }

   @Override
   public <T> Map<Address, List<T>> mapKeysToNodes(DistributionManager dm, String taskId,
            Collection<T> keysToMap) {
      Map<Address, List<T>> addressToKey = new HashMap<Address, List<T>>();
      for (T key : keysToMap) {
         Address ownerOfKey = dm.getPrimaryLocation(new IntermediateKey<T>(taskId, key));
         List<T> keysAtNode = addressToKey.get(ownerOfKey);
         if (keysAtNode == null) {
            keysAtNode = new ArrayList<T>();
            addressToKey.put(ownerOfKey, keysAtNode);
         }
         keysAtNode.add(key);
      }
      return addressToKey;
   }

   protected <KIn> Set<KIn> filterLocalPrimaryOwner(Set<KIn> nodeLocalKeys, DistributionManager dm) {
      Set<KIn> selectedKeys = new HashSet<KIn>();
      for (KIn key : nodeLocalKeys) {
         Address primaryLocation = dm != null ? dm.getPrimaryLocation(key) : cdl.getAddress();
         if (primaryLocation != null && primaryLocation.equals(cdl.getAddress())) {
            selectedKeys.add(key);
         }
      }
      return selectedKeys;
   }

   private abstract class DataContainerTask<K,V> implements BiConsumer<K, InternalCacheEntry<K,V>> {

      @SuppressWarnings("unchecked")
      protected V getValue(InternalCacheEntry<K,V> entry){
         if (entry != null && !entry.isExpired(timeService.wallClockTime())) {
            Object value = entry.getValue();
            if (value instanceof MarshalledValue) {
               value = ((MarshalledValue) value).get();
            }
            return  (V)value;
         } else {
            return null;
         }
      }
   }

   /**
    * This is the parallel staggered map/combine algorithm. Threads from the default fork/join pool
    * traverse container and store key/value pairs in parallel. As one of the threads hits the
    * maxCollectorSize threshold, it takes the snapshot of the current state of the collector and
    * invokes combine on it all while others threads continue to fill up collector up to the point
    * where the threshold is reached again. The thread that broke the collector threshold invokes
    * combine and the algorithm repeats. The benefit of staggered parallel map/combine is manyfold.
    * First, we never exhaust working memory of a node as we batch map/combine execution all while
    * traversal of key/value pairs is in progress. Second, such a staggered combine execution does
    * not cause underlying transport to be completely saturated by intermediate cache put commands;
    * intermediate key/value pairs of map/reduce algorithm are transferred across the cluster
    * smoothly as parallel traversal of container's key/value pairs is progress.
    *
    */
   private final class MapCombineTask<K,V, KOut,VOut> extends DataContainerTask<K, V> implements AdvancedCacheLoader.CacheLoaderTask<K,V> {

      private final MapCombineCommand<K, V, KOut, VOut> mcc;
      private final Set<KOut> intermediateKeys;
      private final int queueLimit;
      private final BlockingQueue<DefaultCollector<K, V, KOut, VOut>> queue;

      public MapCombineTask(MapCombineCommand<K, V, KOut, VOut> mcc, int maxCollectorSize) throws Exception {
         super();
         this.queueLimit = Runtime.getRuntime().availableProcessors() * 2;
         this.queue = new ArrayBlockingQueue<DefaultCollector<K, V, KOut, VOut>>(queueLimit + 1);
         this.mcc = mcc;
         this.intermediateKeys = Collections.synchronizedSet(new HashSet<KOut>());
         //fill up queue with collectors
         for (int i = 0; i < queueLimit; i++){
            queue.put(new DefaultCollector<K, V, KOut, VOut>(mcc, maxCollectorSize));
         }
      }

      @Override
      public void accept(K key, InternalCacheEntry<K, V> v) {
         V value = getValue(v);
         if (value != null) {
            try {
               executeMapWithCollector(key, value);
            } catch (InterruptedException e) {
              //reset signal
              Thread.currentThread().interrupt();
            }
         }
      }

      @Override
      public void processEntry(MarshalledEntry<K, V> marshalledEntry, TaskContext taskContext) throws InterruptedException {
         executeMapWithCollector(marshalledEntry.getKey(), getValue(marshalledEntry));
      }

      @Override
      @SuppressWarnings("unchecked")
      protected V getValue(InternalCacheEntry<K, V> entry){
         if (entry != null) {
            Object value = entry.getValue();
            if (value instanceof MarshalledValue) {
               value = ((MarshalledValue) value).get();
            }
            return  (V)value;
         } else {
            return null;
         }
      }

      private Set<KOut> getMigratedIntermediateKeys() {
         return intermediateKeys;
      }

      private Map<KOut, List<VOut>> collectedValues() {
         //combine all collectors from the queue into one
         DefaultCollector<K, V, KOut, VOut> finalCollector = new DefaultCollector<K, V, KOut, VOut>(mcc, Integer.MAX_VALUE);
         for (DefaultCollector<K, V, KOut, VOut> collector : queue) {
            if (!collector.isEmpty()) {
               finalCollector.emit(collector.collectedValues());
               collector.reset();
            }
         }
         combine(mcc, finalCollector);
         return finalCollector.collectedValues();
      }

      private void executeMapWithCollector(K key, V value) throws InterruptedException {
         DefaultCollector<K, V, KOut, VOut> c = null;
         try {
            // grab collector C from the bounded queue
            c = queue.take();
            //invoke mapper with collector C
            mcc.getMapper().map(key, value, c);
            migrate(c);
         } finally {
            queue.put(c);
         }
      }

      private void migrate(final DefaultCollector<K, V, KOut, VOut> c) {
         // if overflow even after combine then migrate these keys/values
         if (c.isOverflown()) {
            Set<KOut> migratedKeys = migrateIntermediateKeysAndValues(mcc, c.collectedValues());
            intermediateKeys.addAll(migratedKeys);
            c.reset();
         }
      }

      @SuppressWarnings("unchecked")
      private V getValue(MarshalledEntry<K, V> marshalledEntry) {
         Object loadedValue = marshalledEntry.getValue();
         if (loadedValue instanceof MarshalledValue) {
            return  (V) ((MarshalledValue) loadedValue).get();
         } else {
            return (V) loadedValue;
         }
      }
   }

   private static final class IntermediateKeyFilter<T> implements KeyFilter<IntermediateKey<T>> {

      private final String taskId;
      private final boolean acceptAll;

      public IntermediateKeyFilter(String taskId, boolean acceptAll) {
         if (taskId == null || taskId.isEmpty()) {
            throw new IllegalArgumentException("Invalid task Id " + taskId);
         }
         this.taskId = taskId;
         this.acceptAll = acceptAll;
      }

     @Override
      public boolean accept(IntermediateKey<T> key) {
         if (acceptAll) {
            return true;
         } else {
            if (key != null) {
               return taskId.equals(key.getTaskId());
            } else {
               return false;
            }
         }
      }
   }

   /**
    * @author Sanne Grinovero <sanne@hibernate.org> (C) 2011 Red Hat Inc.
    * @author Dan Berindei
    * @author William Burns
    * @author Vladimir Blagojevic
    */
   private final class DefaultCollector<K, V, KOut, VOut> implements CollectableCollector<KOut, VOut> {

      private Map<KOut, List<VOut>> store;
      private final AtomicInteger emitCount;
      private final int maxCollectorSize;
      private MapCombineCommand<K, V, KOut, VOut> mcc;

      public DefaultCollector(MapCombineCommand<K, V, KOut, VOut> mcc, int maxCollectorSize) {
         store = new HashMap<KOut, List<VOut>>(1024, 0.75f);
         emitCount = new AtomicInteger();
         this.maxCollectorSize = maxCollectorSize;
         this.mcc = mcc;
      }

      @Override
      public void emit(KOut key, VOut value) {
         List<VOut> list = store.get(key);
         if (list == null) {
            list = new ArrayList<VOut>(128);
            store.put(key, list);
         }
         list.add(value);
         emitCount.incrementAndGet();
         if (isOverflown() && mcc.hasCombiner()) {
            combine(mcc, this);
         }
      }

      @Override
      public void emitReduced(KOut key, VOut value) {
         List<VOut> list = store.get(key);
         int prevSize = list.size();
         list.clear();
         list.add(value);
         //we remove prevSize elements and replace it with one (the reduced value)
         emitCount.addAndGet(-prevSize + 1);
      }

      @Override
      public Map<KOut, List<VOut>> collectedValues() {
         return store;
      }

      public void reset(){
         store.clear();
         emitCount.set(0);
      }

      public boolean isEmpty() {
         return store.isEmpty();
      }

      public void emit(Map<KOut, List<VOut>> combined) {
         for (Entry<KOut, List<VOut>> e : combined.entrySet()) {
            KOut k = e.getKey();
            List<VOut> values = e.getValue();
            for (VOut v : values) {
               emit(k, v);
            }
         }
      }

      public boolean isOverflown() {
         return emitCount.get() > maxCollectorSize;
      }
   }

   private interface CollectableCollector<K,V> extends Collector<K, V>{
      Map<K, List<V>> collectedValues();
      void emitReduced(K key, V value);
   }

   private final class SynchronizedCollector<KOut, VOut> implements CollectableCollector<KOut, VOut> {

      private CollectableCollector<KOut, VOut> delegate;

      public SynchronizedCollector(CollectableCollector<KOut, VOut> delegate) {
         this.delegate = delegate;
      }

      @Override
      public synchronized void emit(KOut key, VOut value) {
         delegate.emit(key, value);
      }

      @Override
      public synchronized void emitReduced(KOut key, VOut value) {
         delegate.emitReduced(key, value);
      }

      @Override
      public synchronized Map<KOut, List<VOut>> collectedValues() {
         return delegate.collectedValues();
      }
   }

   private static class DeltaAwareList<E> implements Iterable<E>, DeltaAware {

      private final List<E> list;

      public DeltaAwareList(List<E> list) {
         this.list = list;
      }

      @Override
      public Delta delta() {
         return new DeltaList<E>(list);
      }

      @Override
      public void commit() {
         list.clear();
      }

      @Override
      public Iterator<E> iterator(){
         return list.iterator();
      }
   }

   private static class DeltaList<E> implements Delta {

      private final List<E> deltas;

      public DeltaList(List<E> list) {
         deltas = new ArrayList<E>(list);
      }

      @SuppressWarnings("unchecked")
      @Override
      public DeltaAware merge(DeltaAware d) {
         DeltaAwareList<E> other = null;
         if (d instanceof DeltaAwareList) {
            other = (DeltaAwareList<E>) d;
            other.list.addAll(deltas);
         } else {
            other = new DeltaAwareList<E>(deltas);
         }
         return other;
      }
   }

   @SuppressWarnings("rawtypes")
   public static class DeltaListExternalizer extends AbstractExternalizer<DeltaList> {

      private static final long serialVersionUID = 5859147782602054109L;

      @Override
      public void writeObject(ObjectOutput output, DeltaList list) throws IOException {
         output.writeObject(list.deltas);
      }

      @Override
      @SuppressWarnings("unchecked")
      public DeltaList readObject(ObjectInput input) throws IOException, ClassNotFoundException {
         return new DeltaList((List) input.readObject());
      }

      @Override
      public Integer getId() {
         return Ids.DELTA_MAPREDUCE_LIST_ID;
      }

      @Override
      @SuppressWarnings("unchecked")
      public Set<Class<? extends DeltaList>> getTypeClasses() {
         return Util.<Class<? extends DeltaList>>asSet(DeltaList.class);
      }
   }

   @SuppressWarnings("rawtypes")
   public static class DeltaAwareListExternalizer extends AbstractExternalizer<DeltaAwareList> {

      private static final long serialVersionUID = -8956663669844107351L;

      @Override
      public void writeObject(ObjectOutput output, DeltaAwareList deltaAwareList) throws IOException {
         output.writeObject(deltaAwareList.list);
      }

      @Override
      @SuppressWarnings("unchecked")
      public DeltaAwareList readObject(ObjectInput input) throws IOException, ClassNotFoundException {
         return new DeltaAwareList((List) input.readObject());
      }

      @Override
      public Integer getId() {
         return Ids.DELTA_AWARE_MAPREDUCE_LIST_ID;
      }

      @Override
      @SuppressWarnings("unchecked")
      public Set<Class<? extends DeltaAwareList>> getTypeClasses() {
         return Util.<Class<? extends DeltaAwareList>>asSet(DeltaAwareList.class);
      }
   }

   /**
    * IntermediateCompositeKey
    */
   public static final class IntermediateKey<V> implements Serializable {

      /** The serialVersionUID */
      private static final long serialVersionUID = 4434717760740027918L;

      private final String taskId;
      private final V key;

      public IntermediateKey(String taskId, V key) {
         this.taskId = taskId;
         this.key = key;
      }

      public String getTaskId() {
         return taskId;
      }

      public V getKey(){
         return key;
      }

      @Override
      public int hashCode() {
         final int prime = 31;
         int result = 1;
         result = prime * result + ((key == null) ? 0 : key.hashCode());
         result = prime * result + ((taskId == null) ? 0 : taskId.hashCode());
         return result;
      }

      @SuppressWarnings("unchecked")
      @Override
      public boolean equals(Object obj) {
         if (obj == null) {
            return false;
         }
         if (!(obj instanceof IntermediateKey)) {
            return false;
         }
         IntermediateKey<V> other = (IntermediateKey<V>) obj;
         if (key == null) {
            if (other.key != null) {
               return false;
            }
         } else if (!key.equals(other.key)) {
            return false;
         }
         if (taskId == null) {
            if (other.taskId != null) {
               return false;
            }
         } else if (!taskId.equals(other.taskId)) {
            return false;
         }
         return true;
      }

      @Override
      public String toString() {
         return "IntermediateCompositeKey [taskId=" + taskId + ", key=" + key + "]";
      }
   }
}


File: core/src/main/java/org/infinispan/distexec/mapreduce/MapReduceTask.java
package org.infinispan.distexec.mapreduce;

import org.infinispan.AdvancedCache;
import org.infinispan.Cache;
import org.infinispan.commands.CancelCommand;
import org.infinispan.commands.CancellationService;
import org.infinispan.commands.CommandsFactory;
import org.infinispan.commands.CreateCacheCommand;
import org.infinispan.commands.read.MapCombineCommand;
import org.infinispan.commands.read.ReduceCommand;
import org.infinispan.commons.CacheException;
import org.infinispan.commons.marshall.Marshaller;
import org.infinispan.commons.marshall.StreamingMarshaller;
import org.infinispan.commons.util.Util;
import org.infinispan.commons.util.concurrent.NotifyingFutureImpl;
import org.infinispan.distexec.mapreduce.MapReduceManagerImpl.IntermediateKey;
import org.infinispan.distexec.mapreduce.spi.MapReduceTaskLifecycleService;
import org.infinispan.distribution.DistributionManager;
import org.infinispan.factories.ComponentRegistry;
import org.infinispan.interceptors.locking.ClusteringDependentLogic;
import org.infinispan.lifecycle.ComponentStatus;
import org.infinispan.manager.EmbeddedCacheManager;
import org.infinispan.remoting.responses.Response;
import org.infinispan.remoting.responses.SuccessfulResponse;
import org.infinispan.remoting.rpc.RpcManager;
import org.infinispan.remoting.rpc.RpcOptionsBuilder;
import org.infinispan.remoting.transport.Address;
import org.infinispan.security.AuthorizationManager;
import org.infinispan.security.AuthorizationPermission;
import org.infinispan.statetransfer.StateTransferManager;
import org.infinispan.util.logging.Log;
import org.infinispan.util.logging.LogFactory;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import static org.infinispan.factories.KnownComponentNames.CACHE_MARSHALLER;

/**
 * MapReduceTask is a distributed task allowing a large scale computation to be transparently
 * parallelized across Infinispan cluster nodes.
 * <p>
 *
 * Users should instantiate MapReduceTask with a reference to a cache whose data is used as input for this
 * task. Infinispan execution environment will migrate and execute instances of provided {@link Mapper}
 * and {@link Reducer} seamlessly across Infinispan nodes.
 * <p>
 *
 * Unless otherwise specified using {@link MapReduceTask#onKeys(Object...)} filter all available
 * key/value pairs of a specified cache will be used as input data for this task.
 *
 * For example, MapReduceTask that counts number of word occurrences in a particular cache where
 * keys and values are String instances could be written as follows:
 *
 * <pre>
 * MapReduceTask&lt;String, String, String, Integer&gt; task = new MapReduceTask&lt;String, String, String, Integer&gt;(cache);
 * task.mappedWith(new WordCountMapper()).reducedWith(new WordCountReducer());
 * Map&lt;String, Integer&gt; results = task.execute();
 * </pre>
 *
 * The final result is a map where key is a word and value is a word count for that particular word.
 * <p>
 *
 * Accompanying {@link Mapper} and {@link Reducer} are defined as follows:
 *
 * <pre>
 *    private static class WordCountMapper implements Mapper&lt;String, String, String,Integer&gt; {
 *
 *     public void map(String key, String value, Collector&lt;String, Integer&gt; collector) {
 *        StringTokenizer tokens = new StringTokenizer(value);
 *       while (tokens.hasMoreElements()) {
 *           String s = (String) tokens.nextElement();
 *           collector.emit(s, 1);
 *        }
 *     }
 *  }
 *
 *   private static class WordCountReducer implements Reducer&lt;String, Integer&gt; {
 *
 *      public Integer reduce(String key, Iterator&lt;Integer&gt; iter) {
 *         int sum = 0;
 *         while (iter.hasNext()) {
 *            Integer i = (Integer) iter.next();
 *            sum += i;
 *        }
 *         return sum;
 *      }
 *   }
 * </pre>
 *
 * <p>
 *
 * Finally, as of Infinispan 5.2 release, MapReduceTask can also specify a Combiner function. The Combiner
 * is executed on each node after the Mapper and before the global reduce phase. The Combiner receives input from
 * the Mapper's output and the output from the Combiner is then sent to the reducers. It is useful to think
 * of the Combiner as a node local reduce phase before global reduce phase is executed.
 * <p>
 *
 * Combiners are especially useful when reduce function is both commutative and associative! In such cases
 * we can use the Reducer itself as the Combiner; all one needs to do is to specify the Combiner:
 * <pre>
 * MapReduceTask&lt;String, String, String, Integer&gt; task = new MapReduceTask&lt;String, String, String, Integer&gt;(cache);
 * task.mappedWith(new WordCountMapper()).reducedWith(new WordCountReducer()).combineWith(new WordCountReducer());
 * Map&lt;String, Integer&gt; results = task.execute();
 * </pre>
 *
 * Note that {@link Mapper} and {@link Reducer} should not be specified as inner classes. Inner classes
 * declared in non-static contexts contain implicit non-transient references to enclosing class instances,
 * serializing such an inner class instance will result in serialization of its associated outer class instance as well.
 *
 * <p>
 *
 * If you are not familiar with concept of map reduce distributed execution model
 * start with Google's MapReduce research <a href="http://labs.google.com/papers/mapreduce.html">paper</a>.
 *
 *
 * @author Manik Surtani
 * @author Vladimir Blagojevic
 * @author Sanne Grinovero
 *
 * @since 5.0
 */
public class MapReduceTask<KIn, VIn, KOut, VOut> {

   private static final Log log = LogFactory.getLog(MapReduceTask.class);
   public static final String DEFAULT_TMP_CACHE_CONFIGURATION_NAME= "__tmpMapReduce";

   protected Mapper<KIn, VIn, KOut, VOut> mapper;
   protected Reducer<KOut, VOut> reducer;
   protected Reducer<KOut, VOut> combiner;
   protected final boolean distributeReducePhase;
   protected boolean useIntermediateSharedCache;

   protected final Collection<KIn> keys;
   protected final AdvancedCache<KIn, VIn> cache;
   protected final Marshaller marshaller;
   protected final MapReduceManager mapReduceManager;
   protected final CancellationService cancellationService;
   protected final List<CancellableTaskPart> cancellableTasks;
   protected final UUID taskId;
   protected final ClusteringDependentLogic clusteringDependentLogic;
   protected final boolean isLocalOnly;
   protected RpcOptionsBuilder rpcOptionsBuilder;
   protected String customIntermediateCacheName;
   protected String intermediateCacheConfigurationName = DEFAULT_TMP_CACHE_CONFIGURATION_NAME;
   private StateTransferManager stateTransferManager;
   private static final int MAX_COLLECTOR_SIZE = 1000;

   /**
    * Create a new MapReduceTask given a master cache node. All distributed task executions will be
    * initiated from this cache node. This task will by default only use distributed map phase while
    * reduction will be executed on task originating Infinispan node.
    * <p>
    *
    * Large and data intensive tasks whose reduction phase would exceed working memory of one
    * Infinispan node should use distributed reduce phase
    *
    * @param masterCacheNode
    *           cache node initiating map reduce task
    */
   public MapReduceTask(Cache<KIn, VIn> masterCacheNode) {
      this(masterCacheNode, false, false);
   }

   /**
    * Create a new MapReduceTask given a master cache node. All distributed task executions will be
    * initiated from this cache node.
    *
    * @param masterCacheNode
    *           cache node initiating map reduce task
    * @param distributeReducePhase
    *           if true this task will use distributed reduce phase execution
    *
    */
   public MapReduceTask(Cache<KIn, VIn> masterCacheNode, boolean distributeReducePhase) {
      this(masterCacheNode, distributeReducePhase, true);
   }


   /**
    * Create a new MapReduceTask given a master cache node. All distributed task executions will be
    * initiated from this cache node.
    *
    * @param masterCacheNode
    *           cache node initiating map reduce task
    * @param distributeReducePhase
    *           if true this task will use distributed reduce phase execution
    * @param useIntermediateSharedCache
    *           if true this tasks will share intermediate value cache with other executing
    *           MapReduceTasks on the grid. Otherwise, if false, this task will use its own
    *           dedicated cache for intermediate values
    *
    */
   public MapReduceTask(Cache<KIn, VIn> masterCacheNode, boolean distributeReducePhase, boolean useIntermediateSharedCache) {
      if (masterCacheNode == null)
         throw new IllegalArgumentException("Can not use null cache for MapReduceTask");
      ensureAccessPermissions(masterCacheNode.getAdvancedCache());
      ensureProperCacheState(masterCacheNode.getAdvancedCache());
      this.cache = masterCacheNode.getAdvancedCache();
      this.keys = new LinkedList<KIn>();
      ComponentRegistry componentRegistry = SecurityActions.getCacheComponentRegistry(cache);
      this.marshaller = componentRegistry.getComponent(StreamingMarshaller.class, CACHE_MARSHALLER);
      this.mapReduceManager = componentRegistry.getComponent(MapReduceManager.class);
      this.cancellationService = componentRegistry.getComponent(CancellationService.class);
      this.stateTransferManager = componentRegistry.getComponent(StateTransferManager.class);
      this.taskId = UUID.randomUUID();
      if (useIntermediateSharedCache) {
         this.customIntermediateCacheName = DEFAULT_TMP_CACHE_CONFIGURATION_NAME;
      } else {
         this.customIntermediateCacheName = taskId.toString();
      }
      this.distributeReducePhase = distributeReducePhase;
      this.useIntermediateSharedCache = useIntermediateSharedCache;
      this.cancellableTasks = Collections.synchronizedList(new ArrayList<CancellableTaskPart>());
      this.clusteringDependentLogic = componentRegistry.getComponent(ClusteringDependentLogic.class);
      this.isLocalOnly = SecurityActions.getCacheRpcManager(cache) == null;
      this.rpcOptionsBuilder = isLocalOnly ? null : new RpcOptionsBuilder(SecurityActions.getCacheRpcManager(cache).getDefaultRpcOptions(true));
      if (!isLocalOnly) {
         this.rpcOptionsBuilder.timeout(0, TimeUnit.MILLISECONDS);
      }
   }

   /**
    * Rather than use all available keys as input <code>onKeys</code> allows users to specify a
    * subset of keys as input to this task
    *
    * @param input
    *           input keys for this task
    * @return this task
    */
   public MapReduceTask<KIn, VIn, KOut, VOut> onKeys(KIn... input) {
      Collections.addAll(keys, input);
      return this;
   }

   /**
    * Specifies Mapper to use for this MapReduceTask
    * <p>
    * Note that {@link Mapper} should not be specified as inner class. Inner classes declared in
    * non-static contexts contain implicit non-transient references to enclosing class instances,
    * serializing such an inner class instance will result in serialization of its associated outer
    * class instance as well.
    *
    * @param mapper used to execute map phase of MapReduceTask
    * @return this MapReduceTask itself
    */
   public MapReduceTask<KIn, VIn, KOut, VOut> mappedWith(Mapper<KIn, VIn, KOut, VOut> mapper) {
      if (mapper == null)
         throw new IllegalArgumentException("A valid reference of Mapper is needed");
      this.mapper = mapper;
      return this;
   }

   /**
    * Specifies Reducer to use for this MapReduceTask
    *
    * <p>
    * Note that {@link Reducer} should not be specified as inner class. Inner classes declared in
    * non-static contexts contain implicit non-transient references to enclosing class instances,
    * serializing such an inner class instance will result in serialization of its associated outer
    * class instance as well.
    *
    * @param reducer used to reduce results of map phase
    * @return this MapReduceTask itself
    */
   public MapReduceTask<KIn, VIn, KOut, VOut> reducedWith(Reducer<KOut, VOut> reducer) {
      if (reducer == null)
         throw new IllegalArgumentException("A valid reference of Reducer is needed");
      this.reducer = reducer;
      return this;
   }

   /**
    * Specifies Combiner to use for this MapReduceTask
    *
    * <p>
    * Note that {@link Reducer} should not be specified as inner class. Inner classes declared in
    * non-static contexts contain implicit non-transient references to enclosing class instances,
    * serializing such an inner class instance will result in serialization of its associated outer
    * class instance as well.
    *
    * @param combiner used to immediately combine results of map phase before reduce phase is invoked
    * @return this MapReduceTask itself
    * @since 5.2
    */
   public MapReduceTask<KIn, VIn, KOut, VOut> combinedWith(Reducer<KOut, VOut> combiner) {
      if (combiner == null)
         throw new IllegalArgumentException("A valid reference of Reducer/Combiner is needed");
      this.combiner = combiner;
      return this;
   }

   /**
    * See {@link #timeout(TimeUnit)}.
    *
    * Note: the timeout value will be converted to milliseconds and a value less or equal than zero means wait forever.
    * The default timeout for this task is 0. The task will wait indefinitely for its completion.
    *
    * @param timeout
    * @param unit
    * @return this MapReduceTask itself
    */
   public final MapReduceTask<KIn, VIn, KOut, VOut> timeout(long timeout, TimeUnit unit) {
      rpcOptionsBuilder.timeout(timeout, unit);
      return this;
   }

   /**
    * @return the timeout value in {@link TimeUnit} to wait for the remote map/reduce task to finish. The default
    * timeout is 0, the task will wait indefinitely for its completion.
    */
   public final long timeout(TimeUnit outputTimeUnit) {
      return rpcOptionsBuilder.timeout(outputTimeUnit);
   }

   /**
    *
    * Allows this MapReduceTask to use specific intermediate custom defined cache for storage of
    * intermediate <KOut, List<VOut>> key/values pairs. Intermediate cache is used to store output
    * of map phase and it is not shared with other M/R tasks. Upon completion of M/R task this intermediate
    * cache is destroyed.
    *
    * @param cacheConfigurationName
    *           name of the cache configuration to use for the intermediate cache
    * @return this MapReduceTask iteself
    * @since 7.0
    */
   public MapReduceTask<KIn, VIn, KOut, VOut> usingIntermediateCache(String cacheConfigurationName) {
      if (cacheConfigurationName == null || cacheConfigurationName.isEmpty()) {
         throw new IllegalArgumentException("Invalid configuration name " + cacheConfigurationName
               + ", cacheConfigurationName cannot be null or empty");
      }
      this.intermediateCacheConfigurationName = cacheConfigurationName;
      this.useIntermediateSharedCache = false;
      return this;
   }

   /**
    * Allows this MapReduceTask to use a specific shared intermediate cache for storage of
    * intermediate <KOut, List<VOut>> key/values pairs. Intermediate shared cache is used to store
    * output of map phase and it is shared with other M/R tasks that also specify a shared
    * intermediate cache with the same name.
    *
    * @param cacheName
    *           name of the custom cache
    * @return this MapReduceTask iteself
    * @since 7.0
    */
   public MapReduceTask<KIn, VIn, KOut, VOut> usingSharedIntermediateCache(String cacheName) {
      if (cacheName == null || cacheName.isEmpty()) {
         throw new IllegalArgumentException("Invalid cache name" + cacheName + ", cache name cannot be null or empty");
      }
      this.customIntermediateCacheName = cacheName;
      this.useIntermediateSharedCache = true;
      return this;
   }

   /**
    * Allows this MapReduceTask to use a specific shared intermediate cache for storage of
    * intermediate <KOut, List<VOut>> key/values pairs. Intermediate shared cache is used to store
    * output of map phase and it is shared with other M/R tasks that also specify a shared
    * intermediate cache with the same name.
    * <p>
    * Rather than using MapReduceTask default configuration for intermediate cache this method
    * allows clients to specify custom shared cache configuration.
    *
    *
    * @param cacheName
    *           name of the custom cache
    * @param cacheConfigurationName
    *           name of the cache configuration to use for the intermediate cache
    * @return this MapReduceTask iteself
    * @since 7.0
    */
   public MapReduceTask<KIn, VIn, KOut, VOut> usingSharedIntermediateCache(String cacheName, String cacheConfigurationName) {
      if (cacheConfigurationName == null || cacheConfigurationName.isEmpty()) {
         throw new IllegalArgumentException("Invalid configuration name " + cacheConfigurationName
               + ", cacheConfigurationName cannot be null or empty");
      }
      if (cacheName == null || cacheName.isEmpty()) {
         throw new IllegalArgumentException("Invalid cache name" + cacheName + ", cache name cannot be null or empty");
      }
      this.customIntermediateCacheName = cacheName;
      this.intermediateCacheConfigurationName = cacheConfigurationName;
      this.useIntermediateSharedCache = true;
      return this;
   }

   /**
    * Executes this task across Infinispan cluster nodes.
    *
    * @return a Map where each key is an output key and value is reduced value for that output key
    */
   public Map<KOut, VOut> execute() throws CacheException {
      return executeHelper(null);
   }

   /**
    * Executes this task and stores results in the provided results cache. The results can be
    * obtained once the execute method completes i.e., execute method is synchronous.
    *
    * This variant of execute method minimizes the possibility of the master JVM node exceeding
    * its allowed maximum heap, especially if objects that are results of the reduce phase have a
    * large memory footprint and/or multiple MapReduceTasks are executed concurrently on the master
    * task node.
    *
    * @param resultsCache
    *           application provided results cache
    * @throws CacheException
    *
    * @since 7.0
    */
   public void execute(Cache<KOut, VOut> resultsCache) throws CacheException {
      executeHelper(resultsCache.getName());
   }

   /**
    * Executes this task and stores results in the provided results cache. The results can be
    * obtained once the execute method completes i.e., execute method is synchronous.
    *
    * This variant of execute method minimizes the possibility of the master JVM node exceeding its
    * allowed maximum heap, especially if objects that are results of the reduce phase have a large
    * memory footprint and/or multiple MapReduceTasks are executed concurrently on the master task
    * node.
    *
    * @param resultsCache
    *           application provided results cache represented by its name
    * @throws CacheException
    *
    * @since 7.0
    */
   public void execute(String resultsCache) throws CacheException {
      if (resultsCache == null || resultsCache.isEmpty()) {
         throw new IllegalArgumentException("Results cache can not be " + resultsCache);
      }
      executeHelper(resultsCache);
   }

   protected Map<KOut, VOut> executeHelper(String resultCache) throws NullPointerException, MapReduceException {
      ensureAccessPermissions(cache);
      if (mapper == null)
         throw new NullPointerException("A valid reference of Mapper is not set " + mapper);

      if (reducer == null)
         throw new NullPointerException("A valid reference of Reducer is not set " + reducer);

      Map<KOut,VOut> result = null;
      if(!isLocalOnly && distributeReducePhase()){
         // init and create tmp caches
         executeTaskInit(getIntermediateCacheName());
         Set<KOut> allMapPhasesResponses = null;
         try {
            // map
            allMapPhasesResponses = executeMapPhase();

            // reduce
            result = executeReducePhase(resultCache, allMapPhasesResponses, useIntermediateSharedCache());
         } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            throw new MapReduceException(ie);
         }
         finally {
            // cleanup tmp caches across cluster
            EmbeddedCacheManager cm = cache.getCacheManager();
            String intermediateCache = getIntermediateCacheName();
            if (useIntermediatePerTaskCache()) {
               cm.removeCache(intermediateCache);
            } else {
               //let's make sure shared cache is not destroyed and that we have keys to remove
               Cache<KOut, VOut> sharedTmpCache = cm.getCache(intermediateCache);
               if (sharedTmpCache != null && allMapPhasesResponses != null) {
                  for (KOut k : allMapPhasesResponses) {
                     sharedTmpCache.removeAsync(new IntermediateKey<KOut>(taskId.toString(), k));
                  }
               }
            }
         }
      } else {
         try {
            if (resultCache == null || resultCache.isEmpty()) {
               result = new HashMap<KOut, VOut>();
               executeMapPhaseWithLocalReduction(result);
            } else {
               EmbeddedCacheManager cm = cache.getCacheManager();
               Cache<KOut, VOut> c = cm.getCache(resultCache);
               executeMapPhaseWithLocalReduction(c);
            }
         } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            throw new MapReduceException(ie);
         }
      }
      return result;
   }

   protected String getIntermediateCacheName() {
      return customIntermediateCacheName;
   }

   protected boolean distributeReducePhase(){
      return distributeReducePhase;
   }

   protected boolean useIntermediateSharedCache() {
      return useIntermediateSharedCache;
   }

   protected boolean useIntermediatePerTaskCache() {
      return !useIntermediateSharedCache();
   }


   protected void executeTaskInit(String tmpCacheName) throws MapReduceException {
      RpcManager rpc = cache.getRpcManager();
      CommandsFactory factory = cache.getComponentRegistry().getComponent(CommandsFactory.class);

      //first create tmp caches on all nodes
      final CreateCacheCommand ccc = factory.buildCreateCacheCommand(tmpCacheName, intermediateCacheConfigurationName, true, rpc.getMembers().size());
      log.debugf("Invoking %s across members %s ", ccc, cache.getRpcManager().getMembers());

      // invoke remotely
      CompletableFuture<Map<Address, Response>> remoteFuture = rpc.invokeRemotelyAsync(
            cache.getRpcManager().getMembers(), ccc, rpcOptionsBuilder.build());

      // invoke locally
      try {
         ccc.init(cache.getCacheManager(), stateTransferManager);
         try {
            ccc.perform(null);
         } catch (Throwable e) {
            throw new MapReduceException("Could not initialize temporary caches for MapReduce task on remote nodes ", e);
         }
      } catch (Exception e) {
         throw new MapReduceException(e);
      }

      // process remote responses
      try {
         Map<Address, Response> map = remoteFuture.get();
         for (Entry<Address, Response> e : map.entrySet()) {
            if (!e.getValue().isSuccessful()) {
               throw new MapReduceException(
                     "Could not initialize tmp cache " + tmpCacheName + " at " + e.getKey() + " for  " +
                     this);
            }
         }
      } catch (InterruptedException | ExecutionException e) {
         throw new MapReduceException(
               "Could not initialize temporary caches for MapReduce task on remote nodes ", e);
      }
   }

   protected Set<KOut> executeMapPhase() throws MapReduceException, InterruptedException {
      RpcManager rpc = cache.getRpcManager();
      MapCombineCommand<KIn, VIn, KOut, VOut> cmd = null;
      Set<KOut> mapPhasesResult = new HashSet<KOut>();
      List<MapTaskPart<Set<KOut>>> futures = new ArrayList<MapTaskPart<Set<KOut>>>();
      if (inputTaskKeysEmpty()) {
         for (Address target : rpc.getMembers()) {
            if (target.equals(rpc.getAddress())) {
               cmd = buildMapCombineCommand(taskId.toString(), clone(mapper), clone(combiner),
                     getIntermediateCacheName(), null, true, useIntermediateSharedCache());
            } else {
               cmd = buildMapCombineCommand(taskId.toString(), mapper, combiner, getIntermediateCacheName(), null,
                     true, useIntermediateSharedCache());
            }
            MapTaskPart<Set<KOut>> part = createTaskMapPart(cmd, target, true);
            part.execute();
            futures.add(part);
         }
      } else {
         Map<Address, ? extends Collection<KIn>> keysToNodes = mapKeysToNodes(keys);
         for (Entry<Address, ? extends Collection<KIn>> e : keysToNodes.entrySet()) {
            Address address = e.getKey();
            Collection<KIn> keys = e.getValue();
            if (address.equals(rpc.getAddress())) {
               cmd = buildMapCombineCommand(taskId.toString(), clone(mapper), clone(combiner),
                     getIntermediateCacheName(), keys, true, useIntermediateSharedCache());
            } else {
               cmd = buildMapCombineCommand(taskId.toString(), mapper, combiner, getIntermediateCacheName(), keys,
                     true, useIntermediateSharedCache());
            }
            MapTaskPart<Set<KOut>> part = createTaskMapPart(cmd, address, true);
            part.execute();
            futures.add(part);
         }
      }
      try {
         for (MapTaskPart<Set<KOut>> mapTaskPart : futures) {
            Set<KOut> result = null;
            try {
               result = mapTaskPart.get();
            } catch (ExecutionException ee) {
               throw new MapReduceException("Map phase failed ", ee.getCause());
            }
            mapPhasesResult.addAll(result);
         }
      } finally {
         cancellableTasks.clear();
      }
      return mapPhasesResult;
   }

   protected void executeMapPhaseWithLocalReduction(Map<KOut, VOut> reducedResult) throws MapReduceException, InterruptedException {
      RpcManager rpc = SecurityActions.getCacheRpcManager(cache);
      MapCombineCommand<KIn, VIn, KOut, VOut> cmd = null;
      Map<KOut, List<VOut>> mapPhasesResult = new HashMap<KOut, List<VOut>>();
      List<MapTaskPart<Map<KOut, List<VOut>>>> futures = new ArrayList<MapTaskPart<Map<KOut, List<VOut>>>>();
      Address localAddress = clusteringDependentLogic.getAddress();
      if (inputTaskKeysEmpty()) {
         List<Address> targets;
         if (isLocalOnly) {
            targets = Collections.singletonList(localAddress);
         } else {
            targets = rpc.getMembers();
         }
         for (Address target : targets) {
            if (target.equals(localAddress)) {
               cmd = buildMapCombineCommand(taskId.toString(), clone(mapper), clone(combiner),
                     getIntermediateCacheName(), null, false, false);
            } else {
               cmd = buildMapCombineCommand(taskId.toString(), mapper, combiner, getIntermediateCacheName(), null,
                     false, false);
            }
            MapTaskPart<Map<KOut, List<VOut>>> part = createTaskMapPart(cmd, target, false);
            part.execute();
            futures.add(part);
         }
      } else {
         Map<Address, ? extends Collection<KIn>> keysToNodes = mapKeysToNodes(keys);
         for (Entry<Address, ? extends Collection<KIn>> e : keysToNodes.entrySet()) {
            Address address = e.getKey();
            Collection<KIn> keys = e.getValue();
            if (address.equals(localAddress)) {
               cmd = buildMapCombineCommand(taskId.toString(), clone(mapper), clone(combiner),
                     getIntermediateCacheName(), keys, false, false);
            } else {
               cmd = buildMapCombineCommand(taskId.toString(), mapper, combiner, getIntermediateCacheName(), keys,
                     false, false);
            }
            MapTaskPart<Map<KOut, List<VOut>>> part = createTaskMapPart(cmd, address, false);
            part.execute();
            futures.add(part);
         }
      }
      try {
         for (MapTaskPart<Map<KOut, List<VOut>>> mapTaskPart : futures) {
            Map<KOut, List<VOut>> result = null;
            try {
               result = mapTaskPart.get();
            } catch (ExecutionException ee) {
               throw new MapReduceException("Map phase failed ", ee.getCause());
            }
            mergeResponse(mapPhasesResult, result);
         }
      } finally {
         cancellableTasks.clear();
      }

      // hook into lifecycle
      MapReduceTaskLifecycleService taskLifecycleService = MapReduceTaskLifecycleService
               .getInstance();
      log.tracef("For m/r task %s invoking %s locally", taskId, reducer);
      try {
         taskLifecycleService.onPreExecute(reducer, cache);
         for (Entry<KOut, List<VOut>> e : mapPhasesResult.entrySet()) {
            // TODO in parallel with futures
            reducedResult.put(e.getKey(), reducer.reduce(e.getKey(), e.getValue().iterator()));
         }
      } finally {
         taskLifecycleService.onPostExecute(reducer);
      }
   }

   protected <V> MapTaskPart<V> createTaskMapPart(MapCombineCommand<KIn, VIn, KOut, VOut> cmd,
            Address target, boolean distributedReduce) {
      MapTaskPart<V> mapTaskPart = new MapTaskPart<V>(target, cmd, distributedReduce);
      cancellableTasks.add(mapTaskPart);
      return mapTaskPart;
   }

   protected Map<KOut, VOut> executeReducePhase(String resultCache, Set<KOut> allMapPhasesResponses,
            boolean useIntermediateSharedCache) throws MapReduceException, InterruptedException {
      RpcManager rpc = cache.getRpcManager();
      String destCache = getIntermediateCacheName();

      Cache<Object, Object> dstCache = cache.getCacheManager().getCache(destCache);
      Map<Address, ? extends Collection<KOut>> keysToNodes = mapKeysToNodes(dstCache.getAdvancedCache()
               .getDistributionManager(), allMapPhasesResponses, useIntermediateSharedCache);
      Map<KOut, VOut> reduceResult = new HashMap<KOut, VOut>();
      List<ReduceTaskPart<Map<KOut, VOut>>> reduceTasks = new ArrayList<ReduceTaskPart<Map<KOut, VOut>>>();
      ReduceCommand<KOut, VOut> reduceCommand = null;
      for (Entry<Address, ? extends Collection<KOut>> e : keysToNodes.entrySet()) {
         Address address = e.getKey();
         Collection<KOut> keys = e.getValue();
         if (address.equals(rpc.getAddress())) {
            reduceCommand = buildReduceCommand(resultCache, taskId.toString(), destCache, clone(reducer), keys,
                     useIntermediateSharedCache);
         } else {
            reduceCommand = buildReduceCommand(resultCache, taskId.toString(), destCache, reducer, keys,
                     useIntermediateSharedCache);
         }
         ReduceTaskPart<Map<KOut, VOut>> part = createReducePart(reduceCommand, address, destCache);
         part.execute();
         reduceTasks.add(part);
      }
      try {
         for (ReduceTaskPart<Map<KOut, VOut>> reduceTaskPart : reduceTasks) {
            Map<KOut, VOut> result = null;
            try {
               result = reduceTaskPart.get();
            } catch (ExecutionException ee) {
               throw new MapReduceException("Reduce phase failed", ee.getCause());
            }
            reduceResult.putAll(result);
         }
      } finally {
         cancellableTasks.clear();
      }
      return reduceResult;
   }

   protected <V> ReduceTaskPart<V> createReducePart(ReduceCommand<KOut, VOut> cmd, Address target,
            String destCacheName) {
      ReduceTaskPart<V> part = new ReduceTaskPart<V>(target, cmd, destCacheName);
      cancellableTasks.add(part);
      return part;
   }

   private <K, V> void mergeResponse(Map<K, List<V>> result, Map<K, List<V>> m) {
      for (Entry<K, List<V>> entry : m.entrySet()) {
         synchronized (result) {
            List<V> list = result.get(entry.getKey());
            if (list != null) {
               list.addAll(entry.getValue());
            } else {
               list = new ArrayList<V>();
               list.addAll(entry.getValue());
            }
            result.put(entry.getKey(), list);
         }
      }
   }

   private MapCombineCommand<KIn, VIn, KOut, VOut> buildMapCombineCommand(
            String taskId, Mapper<KIn, VIn, KOut, VOut> m, Reducer<KOut, VOut> r, String intermediateCacheName,
            Collection<KIn> keys, boolean reducePhaseDistributed, boolean useIntermediateSharedCache){
      ComponentRegistry registry = SecurityActions.getCacheComponentRegistry(cache);
      CommandsFactory factory = registry.getComponent(CommandsFactory.class);
      MapCombineCommand<KIn, VIn, KOut, VOut> c = factory.buildMapCombineCommand(taskId, m, r, keys);
      c.setReducePhaseDistributed(reducePhaseDistributed);
      c.setUseIntermediateSharedCache(useIntermediateSharedCache);
      c.setIntermediateCacheName(intermediateCacheName);
      c.setMaxCollectorSize(MAX_COLLECTOR_SIZE);
      return c;
   }

   private ReduceCommand<KOut, VOut> buildReduceCommand(String resultCacheName, String taskId, String destinationCache,
         Reducer<KOut, VOut> r, Collection<KOut> keys, boolean useIntermediateSharedCache) {
      ComponentRegistry registry = cache.getComponentRegistry();
      CommandsFactory factory = registry.getComponent(CommandsFactory.class);
      ReduceCommand<KOut, VOut> reduceCommand = factory.buildReduceCommand(taskId, destinationCache, r, keys);
      reduceCommand.setUseIntermediateSharedCache(useIntermediateSharedCache);
      reduceCommand.setResultCacheName(resultCacheName);
      return reduceCommand;
   }

   private CancelCommand buildCancelCommand(CancellableTaskPart taskPart){
      ComponentRegistry registry = cache.getComponentRegistry();
      CommandsFactory factory = registry.getComponent(CommandsFactory.class);
      return factory.buildCancelCommandCommand(taskPart.getUUID());
   }

   /**
    * Executes this task across Infinispan cluster nodes asynchronously.
    *
    * @return a Future wrapping a Map where each key is an output key and value is reduced value for
    *         that output key
    */
   public Future<Map<KOut, VOut>> executeAsynchronously() {
      final MapReduceTaskFuture<Map<KOut, VOut>> result = new MapReduceTaskFuture<Map<KOut, VOut>>();
      ExecutorService executor = mapReduceManager.getExecutorService();
      Future<Map<KOut, VOut>> returnValue = executor.submit(new Callable<Map<KOut, VOut>>() {
         @Override
         public Map<KOut, VOut> call() throws Exception {
            try {
               Map<KOut, VOut> retval = execute();
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
                  log.trace("Finished notifying exception");
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

   /**
    * Executes this task across Infinispan cluster but the final result is collated using specified
    * {@link Collator}
    *
    * @param collator
    *           a Collator to use
    *
    * @return collated result
    */
   public <R> R execute(Collator<KOut, VOut, R> collator) {
      Map<KOut, VOut> execute = execute();
      return collator.collate(execute);
   }

   /**
    * Executes this task asynchronously across Infinispan cluster; final result is collated using
    * specified {@link Collator} and wrapped by Future
    *
    * @param collator
    *           a Collator to use
    *
    * @return collated result
    */
   public <R> Future<R> executeAsynchronously(final Collator<KOut, VOut, R> collator) {
      final MapReduceTaskFuture<R> result = new MapReduceTaskFuture<R>();
      ExecutorService executor = mapReduceManager.getExecutorService();
      Future<R> returnValue = executor.submit(new Callable<R>() {
         @Override
         public R call() throws Exception {
            try {
               R retval = execute(collator);
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

   protected <T> Map<Address, ? extends Collection<T>> mapKeysToNodes(DistributionManager dm, Collection<T> keysToMap, boolean useIntermediateCompositeKey) {
      if (isLocalOnly) {
         return Collections.singletonMap(clusteringDependentLogic.getAddress(), keysToMap);
      } else {
         return mapReduceManager.mapKeysToNodes(dm, taskId.toString(), keysToMap);
      }
   }

   protected <T> Map<Address, ? extends Collection<T>> mapKeysToNodes(Collection<T> keysToMap, boolean useIntermediateCompositeKey) {
      return mapKeysToNodes(cache.getDistributionManager(), keysToMap, useIntermediateCompositeKey);
   }

   protected <T> Map<Address, ? extends Collection<T>> mapKeysToNodes(Collection<T> keysToMap) {
      return mapKeysToNodes(keysToMap, false);
   }

   protected Mapper<KIn, VIn, KOut, VOut> clone(Mapper<KIn, VIn, KOut, VOut> mapper){
      return Util.cloneWithMarshaller(marshaller, mapper);
   }

   protected Reducer<KOut, VOut> clone(Reducer<KOut, VOut> reducer){
      return Util.cloneWithMarshaller(marshaller, reducer);
   }

   private void ensureAccessPermissions(final AdvancedCache<?, ?> cache) {
      AuthorizationManager authorizationManager = SecurityActions.getCacheAuthorizationManager(cache);
      if (authorizationManager != null) {
         authorizationManager.checkPermission(AuthorizationPermission.EXEC);
      }
   }

   private void ensureProperCacheState(AdvancedCache<KIn, VIn> cache) throws NullPointerException,
            IllegalStateException {
      if (cache.getStatus() != ComponentStatus.RUNNING)
         throw log.invalidCacheState(cache.getStatus().toString());

      if (SecurityActions.getCacheRpcManager(cache) != null && SecurityActions.getCacheDistributionManager(cache) == null) {
         throw log.requireDistOrReplCache(cache.getCacheConfiguration().clustering().cacheModeString());
      }
   }

   protected boolean inputTaskKeysEmpty() {
      return keys == null || keys.isEmpty();
   }
   @Override
   public int hashCode() {
      final int prime = 31;
      int result = 1;
      result = prime * result + ((taskId == null) ? 0 : taskId.hashCode());
      return result;
   }

   @SuppressWarnings("rawtypes")
   @Override
   public boolean equals(Object obj) {
      if (this == obj) {
         return true;
      }
      if (obj == null) {
         return false;
      }
      if (!(obj instanceof MapReduceTask)) {
         return false;
      }
      MapReduceTask other = (MapReduceTask) obj;
      if (taskId == null) {
         if (other.taskId != null) {
            return false;
         }
      } else if (!taskId.equals(other.taskId)) {
         return false;
      }
      return true;
   }

   @Override
   public String toString() {
      return "MapReduceTask [mapper=" + mapper + ", reducer=" + reducer + ", combiner=" + combiner
               + ", keys=" + keys + ", taskId=" + taskId + "]";
   }

   private class MapReduceTaskFuture<R> extends NotifyingFutureImpl<R> {

      private volatile boolean cancelled = false;

      public MapReduceTaskFuture() {
      }

      @Override
      public boolean cancel(boolean mayInterruptIfRunning) {
         if (!isCancelled()) {
            RpcManager rpc = cache.getRpcManager();
            synchronized (cancellableTasks) {
               for (CancellableTaskPart task : cancellableTasks) {
                  boolean sendingToSelf = task.getExecutionTarget().equals(
                           rpc.getTransport().getAddress());
                  CancelCommand cc = buildCancelCommand(task);
                  if (sendingToSelf) {
                     cc.init(cancellationService);
                     try {
                        cc.perform(null);
                     } catch (Throwable e) {
                        log.couldNotExecuteCancellationLocally(e.getLocalizedMessage());
                     }
                  } else {
                     rpc.invokeRemotely(Collections.singletonList(task.getExecutionTarget()), cc, rpcOptionsBuilder.build());
                  }
                  cancelled = true;
               }
            }
            return cancelled;
         } else {
            //already cancelled
            return false;
         }
      }

      @Override
      public boolean isCancelled() {
         return cancelled;
      }
   }

   private abstract class TaskPart<V> implements Future<V>, CancellableTaskPart {

      private Future<Map<Address, Response>> f;
      private final Address executionTarget;

      public TaskPart(Address executionTarget) {
         this.executionTarget = executionTarget;
      }

      @Override
      public Address getExecutionTarget() {
         return executionTarget;
      }

      @Override
      public boolean cancel(boolean mayInterruptIfRunning) {
         return false;
      }

      @Override
      public boolean isCancelled() {
         return false;
      }

      @Override
      public boolean isDone() {
         return false;
      }

      @Override
      public V get() throws InterruptedException, ExecutionException {
         return retrieveResult(f.get());
      }

      protected Address getAddress() {
         return clusteringDependentLogic.getAddress();
      }

      protected boolean locallyExecuted(){
         return getAddress().equals(getExecutionTarget());
      }

      public abstract void execute();

      @SuppressWarnings("unchecked")
      private V retrieveResult(Object response) throws ExecutionException {
         if (response == null) {
            throw new ExecutionException("Execution returned null value",
                     new NullPointerException());
         }
         if (response instanceof Exception) {
            throw new ExecutionException((Exception) response);
         }

         Map<Address, Response> mapResult = (Map<Address, Response>) response;
         assert mapResult.size() == 1;
         for (Entry<Address, Response> e : mapResult.entrySet()) {
            if (e.getValue() instanceof SuccessfulResponse) {
               return (V) ((SuccessfulResponse) e.getValue()).getResponseValue();
            }
         }
         throw new ExecutionException(new IllegalStateException("Invalid response " + response));
      }

      @Override
      public V get(long timeout, TimeUnit unit) throws InterruptedException, ExecutionException,
               TimeoutException {
         return retrieveResult(f.get(timeout, unit));
      }

      public void setFuture(Future<Map<Address, Response>> future) {
         this.f = future;
      }
   }

   private class MapTaskPart<V> extends TaskPart<V> {

      private final MapCombineCommand<KIn, VIn, KOut, VOut> mcc;
      private final boolean distributedReduce;

      public MapTaskPart(Address executionTarget, MapCombineCommand<KIn, VIn, KOut, VOut> command,
               boolean distributedReduce) {
         super(executionTarget);
         this.mcc = command;
         this.distributedReduce = distributedReduce;
      }

      @Override
      @SuppressWarnings("unchecked")
      public void execute() {
         if (locallyExecuted()) {
            Callable<Map<Address, Response>> callable;
            if (distributedReduce) {
               callable = () -> {
                  Set<KOut> result = invokeMapCombineLocally();
                  return Collections.singletonMap(getAddress(), SuccessfulResponse.create(result));
               };
            } else {
               callable = () -> {
                  Map<KOut, List<VOut>> result = invokeMapCombineLocallyForLocalReduction();
                  return Collections.singletonMap(getAddress(), SuccessfulResponse.create(result));
               };
            }
            Future<Map<Address, Response>> localFuture = mapReduceManager.getExecutorService().submit(
                  callable);
            setFuture(localFuture);
         } else {
            RpcManager rpc = SecurityActions.getCacheRpcManager(cache);
            try {
               log.debugf("Invoking %s on %s", mcc, getExecutionTarget());
               CompletableFuture<Map<Address, Response>> remoteFuture = rpc.invokeRemotelyAsync(
                     Collections.singleton(getExecutionTarget()), mcc, rpcOptionsBuilder.build());
               setFuture(remoteFuture);
               log.debugf("Invoked %s on %s ", mcc, getExecutionTarget());
            } catch (Exception ex) {
               throw new MapReduceException(
                        "Could not invoke map phase of MapReduceTask on remote node "
                                 + getExecutionTarget(), ex);
            }
         }
      }

      private Map<KOut, List<VOut>> invokeMapCombineLocallyForLocalReduction() throws InterruptedException {
         log.debugf("Invoking %s locally", mcc);
         try {
            cancellationService.register(Thread.currentThread(), mcc.getUUID());
            mcc.init(mapReduceManager);
            return mapReduceManager.mapAndCombineForLocalReduction(mcc);
         } finally {
            cancellationService.unregister(mcc.getUUID());
            log.debugf("Invoked %s locally", mcc);
         }
      }

      private Set<KOut> invokeMapCombineLocally() throws InterruptedException {
         log.debugf("Invoking %s locally", mcc);
         try {
            cancellationService.register(Thread.currentThread(), mcc.getUUID());
            mcc.init(mapReduceManager);
            return mapReduceManager.mapAndCombineForDistributedReduction(mcc);
         } finally {
            cancellationService.unregister(mcc.getUUID());
            log.debugf("Invoked %s locally", mcc);
         }
      }

      @Override
      public UUID getUUID() {
         return mcc.getUUID();
      }
   }

   private class ReduceTaskPart<V> extends TaskPart<V> {

      private final ReduceCommand<KOut, VOut> rc;
      private final String cacheName;

      public ReduceTaskPart(Address executionTarget, ReduceCommand<KOut, VOut> command,
               String destinationCacheName) {
         super(executionTarget);
         this.rc = command;
         this.cacheName = destinationCacheName;
      }

      @Override
      @SuppressWarnings("unchecked")
      public void execute() {
         if (locallyExecuted()) {
            Callable<Map<Address, Response>> callable = () -> {
               Cache<Object, Object> dstCache = cache.getCacheManager().getCache(cacheName);
               Map<KOut, VOut> result = invokeReduceLocally(dstCache);
               return Collections.singletonMap(getAddress(), SuccessfulResponse.create(result));
            };
            Future<Map<Address, Response>> future = mapReduceManager.getExecutorService().submit(callable);
            setFuture(future);
         } else {
            RpcManager rpc = cache.getRpcManager();
            try {
               log.debugf("Invoking %s on %s", rc, getExecutionTarget());
               CompletableFuture<Map<Address, Response>> future = rpc.invokeRemotelyAsync(
                     Collections.singleton(getExecutionTarget()), rc, rpcOptionsBuilder.build());
               setFuture(future);
               log.debugf("Invoked %s on %s ", rc, getExecutionTarget());
            } catch (Exception ex) {
               throw new MapReduceException(
                        "Could not invoke map phase of MapReduceTask on remote node "
                                 + getExecutionTarget(), ex);
            }
         }
      }

      private Map<KOut, VOut> invokeReduceLocally(Cache<Object, Object> dstCache) {
         rc.init(mapReduceManager);
         Map<KOut, VOut> localReduceResult = null;
         try {
            log.debugf("Invoking %s locally ", rc);
            if(rc.emitsIntoResultingCache()){
               mapReduceManager.reduce(rc, rc.getResultCacheName());
               localReduceResult = Collections.emptyMap();
            } else {
               localReduceResult = mapReduceManager.reduce(rc);
            }
            log.debugf("Invoked %s locally", rc);
         } catch (Throwable e1) {
            throw new MapReduceException("Could not invoke MapReduce task locally ", e1);
         }
         return localReduceResult;
      }

      @Override
      public UUID getUUID() {
         return rc.getUUID();
      }
   }

   private interface CancellableTaskPart {
      UUID getUUID();
      Address getExecutionTarget();
   }
}
