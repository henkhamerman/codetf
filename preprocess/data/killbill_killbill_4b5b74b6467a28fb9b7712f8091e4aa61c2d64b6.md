Refactoring Types: ['Push Down Attribute', 'Extract Method']
re/PaymentProcessor.java
/*
 * Copyright 2010-2013 Ning, Inc.
 * Copyright 2014-2015 Groupon, Inc
 * Copyright 2014-2015 The Billing Project, LLC
 *
 * The Billing Project licenses this file to you under the Apache License, version 2.0
 * (the "License"); you may not use this file except in compliance with the
 * License.  You may obtain a copy of the License at:
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package org.killbill.billing.payment.core;

import java.math.BigDecimal;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;

import javax.annotation.Nullable;
import javax.inject.Inject;

import org.killbill.automaton.OperationResult;
import org.killbill.billing.ErrorCode;
import org.killbill.billing.account.api.Account;
import org.killbill.billing.account.api.AccountInternalApi;
import org.killbill.billing.callcontext.InternalCallContext;
import org.killbill.billing.callcontext.InternalTenantContext;
import org.killbill.billing.catalog.api.Currency;
import org.killbill.billing.invoice.api.InvoiceInternalApi;
import org.killbill.billing.osgi.api.OSGIServiceRegistration;
import org.killbill.billing.payment.api.DefaultPayment;
import org.killbill.billing.payment.api.DefaultPaymentTransaction;
import org.killbill.billing.payment.api.Payment;
import org.killbill.billing.payment.api.PaymentApiException;
import org.killbill.billing.payment.api.PaymentTransaction;
import org.killbill.billing.payment.api.PluginProperty;
import org.killbill.billing.payment.api.TransactionStatus;
import org.killbill.billing.payment.api.TransactionType;
import org.killbill.billing.payment.core.sm.PaymentAutomatonRunner;
import org.killbill.billing.payment.dao.PaymentDao;
import org.killbill.billing.payment.dao.PaymentModelDao;
import org.killbill.billing.payment.dao.PaymentTransactionModelDao;
import org.killbill.billing.payment.plugin.api.PaymentPluginApi;
import org.killbill.billing.payment.plugin.api.PaymentPluginApiException;
import org.killbill.billing.payment.plugin.api.PaymentTransactionInfoPlugin;
import org.killbill.billing.tag.TagInternalApi;
import org.killbill.billing.util.callcontext.CallContext;
import org.killbill.billing.util.callcontext.InternalCallContextFactory;
import org.killbill.billing.util.callcontext.TenantContext;
import org.killbill.billing.util.entity.Pagination;
import org.killbill.billing.util.entity.dao.DefaultPaginationHelper.EntityPaginationBuilder;
import org.killbill.billing.util.entity.dao.DefaultPaginationHelper.SourcePaginationBuilder;
import org.killbill.clock.Clock;
import org.killbill.commons.locker.GlobalLocker;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.common.base.Function;
import com.google.common.base.Predicate;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Ordering;
import com.google.inject.name.Named;

import static org.killbill.billing.payment.glue.PaymentModule.PLUGIN_EXECUTOR_NAMED;
import static org.killbill.billing.util.entity.dao.DefaultPaginationHelper.getEntityPagination;
import static org.killbill.billing.util.entity.dao.DefaultPaginationHelper.getEntityPaginationFromPlugins;

public class PaymentProcessor extends ProcessorBase {

    private static final ImmutableList<PluginProperty> PLUGIN_PROPERTIES = ImmutableList.<PluginProperty>of();

    private final PaymentAutomatonRunner paymentAutomatonRunner;

    private static final Logger log = LoggerFactory.getLogger(PaymentProcessor.class);

    @Inject
    public PaymentProcessor(final OSGIServiceRegistration<PaymentPluginApi> pluginRegistry,
                            final AccountInternalApi accountUserApi,
                            final InvoiceInternalApi invoiceApi,
                            final TagInternalApi tagUserApi,
                            final PaymentDao paymentDao,
                            final InternalCallContextFactory internalCallContextFactory,
                            final GlobalLocker locker,
                            @Named(PLUGIN_EXECUTOR_NAMED) final ExecutorService executor,
                            final PaymentAutomatonRunner paymentAutomatonRunner,
                            final Clock clock) {
        super(pluginRegistry, accountUserApi, paymentDao, tagUserApi, locker, executor, internalCallContextFactory, invoiceApi, clock);
        this.paymentAutomatonRunner = paymentAutomatonRunner;
    }

    public Payment createAuthorization(final boolean isApiPayment, @Nullable final UUID attemptId, final Account account, @Nullable final UUID paymentMethodId, @Nullable final UUID paymentId, final BigDecimal amount, final Currency currency,
                                       @Nullable final String paymentExternalKey, @Nullable final String paymentTransactionExternalKey, final boolean shouldLockAccountAndDispatch,
                                       final Iterable<PluginProperty> properties, final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        return performOperation(isApiPayment, attemptId, TransactionType.AUTHORIZE, account, paymentMethodId, paymentId, null, amount, currency, paymentExternalKey, paymentTransactionExternalKey, shouldLockAccountAndDispatch, null, properties, callContext, internalCallContext);
    }

    public Payment createCapture(final boolean isApiPayment, @Nullable final UUID attemptId, final Account account, final UUID paymentId, final BigDecimal amount, final Currency currency,
                                 @Nullable final String paymentTransactionExternalKey, final boolean shouldLockAccountAndDispatch,
                                 final Iterable<PluginProperty> properties, final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        return performOperation(isApiPayment, attemptId, TransactionType.CAPTURE, account, null, paymentId, null, amount, currency, null, paymentTransactionExternalKey, shouldLockAccountAndDispatch, null, properties, callContext, internalCallContext);
    }

    public Payment createPurchase(final boolean isApiPayment, @Nullable final UUID attemptId, final Account account, @Nullable final UUID paymentMethodId, @Nullable final UUID paymentId, final BigDecimal amount, final Currency currency,
                                  @Nullable final String paymentExternalKey, @Nullable final String paymentTransactionExternalKey, final boolean shouldLockAccountAndDispatch,
                                  final Iterable<PluginProperty> properties, final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        return performOperation(isApiPayment, attemptId, TransactionType.PURCHASE, account, paymentMethodId, paymentId, null, amount, currency, paymentExternalKey, paymentTransactionExternalKey, shouldLockAccountAndDispatch, null, properties, callContext, internalCallContext);
    }

    public Payment createVoid(final boolean isApiPayment, @Nullable final UUID attemptId, final Account account, final UUID paymentId, @Nullable final String paymentTransactionExternalKey, final boolean shouldLockAccountAndDispatch,
                              final Iterable<PluginProperty> properties, final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        return performOperation(isApiPayment, attemptId, TransactionType.VOID, account, null, paymentId, null, null, null, null, paymentTransactionExternalKey, shouldLockAccountAndDispatch, null, properties, callContext, internalCallContext);
    }

    public Payment createRefund(final boolean isApiPayment, @Nullable final UUID attemptId, final Account account, final UUID paymentId, final BigDecimal amount, final Currency currency,
                                final String paymentTransactionExternalKey, final boolean shouldLockAccountAndDispatch,
                                final Iterable<PluginProperty> properties, final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        return performOperation(isApiPayment, attemptId, TransactionType.REFUND, account, null, paymentId, null, amount, currency, null, paymentTransactionExternalKey, shouldLockAccountAndDispatch, null, properties, callContext, internalCallContext);
    }

    public Payment createCredit(final boolean isApiPayment, @Nullable final UUID attemptId, final Account account, @Nullable final UUID paymentMethodId, @Nullable final UUID paymentId, final BigDecimal amount, final Currency currency,
                                @Nullable final String paymentExternalKey, @Nullable final String paymentTransactionExternalKey, final boolean shouldLockAccountAndDispatch,
                                final Iterable<PluginProperty> properties, final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        return performOperation(isApiPayment, attemptId, TransactionType.CREDIT, account, paymentMethodId, paymentId, null, amount, currency, paymentExternalKey, paymentTransactionExternalKey, shouldLockAccountAndDispatch, null, properties, callContext, internalCallContext);
    }

    public Payment createChargeback(final boolean isApiPayment, @Nullable final UUID attemptId, final Account account, final UUID paymentId, @Nullable final String paymentTransactionExternalKey, final BigDecimal amount, final Currency currency, final boolean shouldLockAccountAndDispatch,
                                    final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        return performOperation(isApiPayment, attemptId, TransactionType.CHARGEBACK, account, null, paymentId, null, amount, currency, null, paymentTransactionExternalKey, shouldLockAccountAndDispatch, null, PLUGIN_PROPERTIES, callContext, internalCallContext);
    }

    public Payment notifyPendingPaymentOfStateChanged(final Account account, final UUID transactionId, final boolean isSuccess, final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        final PaymentTransactionModelDao transactionModelDao = paymentDao.getPaymentTransaction(transactionId, internalCallContext);
        if (transactionModelDao.getTransactionStatus() != TransactionStatus.PENDING) {
            throw new PaymentApiException(ErrorCode.PAYMENT_NO_SUCH_SUCCESS_PAYMENT, transactionModelDao.getPaymentId());
        }

        final OperationResult overridePluginResult = isSuccess ? OperationResult.SUCCESS : OperationResult.FAILURE;

        return performOperation(true, null, transactionModelDao.getTransactionType(), account, null, transactionModelDao.getPaymentId(),
                                transactionModelDao.getId(), transactionModelDao.getAmount(), transactionModelDao.getCurrency(), null, transactionModelDao.getTransactionExternalKey(), true,
                                overridePluginResult, PLUGIN_PROPERTIES, callContext, internalCallContext);
    }

    public List<Payment> getAccountPayments(final UUID accountId, final boolean withPluginInfo, final TenantContext context, final InternalTenantContext tenantContext) throws PaymentApiException {
        final List<PaymentModelDao> paymentsModelDao = paymentDao.getPaymentsForAccount(accountId, tenantContext);
        final List<PaymentTransactionModelDao> transactionsModelDao = paymentDao.getTransactionsForAccount(accountId, tenantContext);

        final Map<UUID, PaymentPluginApi> paymentPluginByPaymentMethodId = new HashMap<UUID, PaymentPluginApi>();
        final Collection<UUID> absentPlugins = new HashSet<UUID>();
        return Lists.<PaymentModelDao, Payment>transform(paymentsModelDao,
                                                         new Function<PaymentModelDao, Payment>() {
                                                             @Override
                                                             public Payment apply(final PaymentModelDao paymentModelDao) {
                                                                 List<PaymentTransactionInfoPlugin> pluginInfo = null;

                                                                 if (withPluginInfo) {
                                                                     PaymentPluginApi pluginApi = paymentPluginByPaymentMethodId.get(paymentModelDao.getPaymentMethodId());
                                                                     if (pluginApi == null && !absentPlugins.contains(paymentModelDao.getPaymentMethodId())) {
                                                                         try {
                                                                             pluginApi = getPaymentProviderPlugin(paymentModelDao.getPaymentMethodId(), tenantContext);
                                                                             paymentPluginByPaymentMethodId.put(paymentModelDao.getPaymentMethodId(), pluginApi);
                                                                         } catch (final PaymentApiException e) {
                                                                             log.warn("Unable to retrieve pluginApi for payment method " + paymentModelDao.getPaymentMethodId());
                                                                             absentPlugins.add(paymentModelDao.getPaymentMethodId());
                                                                         }
                                                                     }

                                                                     pluginInfo = getPaymentTransactionInfoPluginsIfNeeded(pluginApi, paymentModelDao, context);
                                                                 }

                                                                 return toPayment(paymentModelDao, transactionsModelDao, pluginInfo);
                                                             }
                                                         });
    }

    public Payment getPayment(final UUID paymentId, final boolean withPluginInfo, final Iterable<PluginProperty> properties, final TenantContext tenantContext, final InternalTenantContext internalTenantContext) throws PaymentApiException {
        final PaymentModelDao paymentModelDao = paymentDao.getPayment(paymentId, internalTenantContext);
        if (paymentModelDao == null) {
            return null;
        }
        return toPayment(paymentModelDao, withPluginInfo, properties, tenantContext, internalTenantContext);
    }

    public Payment getPaymentByExternalKey(final String paymentExternalKey, final boolean withPluginInfo, final Iterable<PluginProperty> properties, final TenantContext tenantContext, final InternalTenantContext internalTenantContext) throws PaymentApiException {
        final PaymentModelDao paymentModelDao = paymentDao.getPaymentByExternalKey(paymentExternalKey, internalTenantContext);
        if (paymentModelDao == null) {
            return null;
        }
        return toPayment(paymentModelDao, withPluginInfo, properties, tenantContext, internalTenantContext);
    }

    public Pagination<Payment> getPayments(final Long offset, final Long limit, final boolean withPluginInfo, final Iterable<PluginProperty> properties,
                                           final TenantContext tenantContext, final InternalTenantContext internalTenantContext) {
        return getEntityPaginationFromPlugins(getAvailablePlugins(),
                                              offset,
                                              limit,
                                              new EntityPaginationBuilder<Payment, PaymentApiException>() {
                                                  @Override
                                                  public Pagination<Payment> build(final Long offset, final Long limit, final String pluginName) throws PaymentApiException {
                                                      return getPayments(offset, limit, pluginName, withPluginInfo, properties, tenantContext, internalTenantContext);
                                                  }
                                              }
                                             );
    }

    public Pagination<Payment> getPayments(final Long offset, final Long limit, final String pluginName, final boolean withPluginInfo, final Iterable<PluginProperty> properties, final TenantContext tenantContext, final InternalTenantContext internalTenantContext) throws PaymentApiException {
        final PaymentPluginApi pluginApi = withPluginInfo ? getPaymentPluginApi(pluginName) : null;

        return getEntityPagination(limit,
                                   new SourcePaginationBuilder<PaymentModelDao, PaymentApiException>() {
                                       @Override
                                       public Pagination<PaymentModelDao> build() {
                                           // Find all payments for all accounts
                                           return paymentDao.getPayments(pluginName, offset, limit, internalTenantContext);
                                       }
                                   },
                                   new Function<PaymentModelDao, Payment>() {
                                       @Override
                                       public Payment apply(final PaymentModelDao paymentModelDao) {
                                           final List<PaymentTransactionInfoPlugin> pluginInfo = getPaymentTransactionInfoPluginsIfNeeded(pluginApi, paymentModelDao, tenantContext);
                                           return toPayment(paymentModelDao.getId(), pluginInfo, internalTenantContext);
                                       }
                                   }
                                  );
    }

    public Pagination<Payment> searchPayments(final String searchKey, final Long offset, final Long limit, final boolean withPluginInfo, final Iterable<PluginProperty> properties, final TenantContext tenantContext, final InternalTenantContext internalTenantContext) {
        return getEntityPaginationFromPlugins(getAvailablePlugins(),
                                              offset,
                                              limit,
                                              new EntityPaginationBuilder<Payment, PaymentApiException>() {
                                                  @Override
                                                  public Pagination<Payment> build(final Long offset, final Long limit, final String pluginName) throws PaymentApiException {
                                                      return searchPayments(searchKey, offset, limit, pluginName, withPluginInfo, properties, tenantContext, internalTenantContext);
                                                  }
                                              }
                                             );
    }

    public Pagination<Payment> searchPayments(final String searchKey, final Long offset, final Long limit, final String pluginName, final boolean withPluginInfo, final Iterable<PluginProperty> properties, final TenantContext tenantContext, final InternalTenantContext internalTenantContext) throws PaymentApiException {
        if (withPluginInfo) {
            final PaymentPluginApi pluginApi = getPaymentPluginApi(pluginName);

            return getEntityPagination(limit,
                                       new SourcePaginationBuilder<PaymentTransactionInfoPlugin, PaymentApiException>() {
                                           @Override
                                           public Pagination<PaymentTransactionInfoPlugin> build() throws PaymentApiException {
                                               try {
                                                   return pluginApi.searchPayments(searchKey, offset, limit, properties, tenantContext);
                                               } catch (final PaymentPluginApiException e) {
                                                   throw new PaymentApiException(e, ErrorCode.PAYMENT_PLUGIN_SEARCH_PAYMENTS, pluginName, searchKey);
                                               }
                                           }

                                       },
                                       new Function<PaymentTransactionInfoPlugin, Payment>() {
                                           final List<PaymentTransactionInfoPlugin> cachedPaymentTransactions = new LinkedList<PaymentTransactionInfoPlugin>();

                                           @Override
                                           public Payment apply(final PaymentTransactionInfoPlugin pluginTransaction) {
                                               if (pluginTransaction.getKbPaymentId() == null) {
                                                   // Garbage from the plugin?
                                                   log.debug("Plugin {} returned a payment without a kbPaymentId for searchKey {}", pluginName, searchKey);
                                                   return null;
                                               }

                                               if (cachedPaymentTransactions.isEmpty() ||
                                                   (cachedPaymentTransactions.get(0).getKbPaymentId().equals(pluginTransaction.getKbPaymentId()))) {
                                                   cachedPaymentTransactions.add(pluginTransaction);
                                                   return null;
                                               } else {
                                                   final Payment result = toPayment(pluginTransaction.getKbPaymentId(), ImmutableList.<PaymentTransactionInfoPlugin>copyOf(cachedPaymentTransactions), internalTenantContext);
                                                   cachedPaymentTransactions.clear();
                                                   cachedPaymentTransactions.add(pluginTransaction);
                                                   return result;
                                               }
                                           }
                                       }
                                      );
        } else {
            return getEntityPagination(limit,
                                       new SourcePaginationBuilder<PaymentModelDao, PaymentApiException>() {
                                           @Override
                                           public Pagination<PaymentModelDao> build() {
                                               return paymentDao.searchPayments(searchKey, offset, limit, internalTenantContext);
                                           }
                                       },
                                       new Function<PaymentModelDao, Payment>() {
                                           @Override
                                           public Payment apply(final PaymentModelDao paymentModelDao) {
                                               return toPayment(paymentModelDao.getId(), null, internalTenantContext);
                                           }
                                       }
                                      );
        }
    }

    private Payment performOperation(final boolean isApiPayment, @Nullable final UUID attemptId,
                                     final TransactionType transactionType, final Account account,
                                     @Nullable final UUID paymentMethodId, @Nullable final UUID paymentId, @Nullable final UUID transactionId,
                                     @Nullable final BigDecimal amount, @Nullable final Currency currency,
                                     @Nullable final String paymentExternalKey, @Nullable final String paymentTransactionExternalKey,
                                     final boolean shouldLockAccountAndDispatch, @Nullable final OperationResult overridePluginOperationResult,
                                     final Iterable<PluginProperty> properties,
                                     final CallContext callContext, final InternalCallContext internalCallContext) throws PaymentApiException {
        validateUniqueTransactionExternalKey(paymentTransactionExternalKey, internalCallContext);
        final UUID nonNullPaymentId = paymentAutomatonRunner.run(isApiPayment,
                                                                 transactionType,
                                                                 account,
                                                                 attemptId,
                                                                 paymentMethodId,
                                                                 paymentId,
                                                                 transactionId,
                                                                 paymentExternalKey,
                                                                 paymentTransactionExternalKey,
                                                                 amount,
                                                                 currency,
                                                                 shouldLockAccountAndDispatch,
                                                                 overridePluginOperationResult,
                                                                 properties,
                                                                 callContext,
                                                                 internalCallContext);
        return getPayment(nonNullPaymentId, true, properties, callContext, internalCallContext);
    }

    // Used in bulk get API (getAccountPayments / getPayments)
    private List<PaymentTransactionInfoPlugin> getPaymentTransactionInfoPluginsIfNeeded(@Nullable final PaymentPluginApi pluginApi, final PaymentModelDao paymentModelDao, final TenantContext context) {
        if (pluginApi == null) {
            return null;
        }

        try {
            return getPaymentTransactionInfoPlugins(pluginApi, paymentModelDao, PLUGIN_PROPERTIES, context);
        } catch (final PaymentApiException e) {
            log.warn("Unable to retrieve plugin info for payment " + paymentModelDao.getId());
            return null;
        }
    }

    private List<PaymentTransactionInfoPlugin> getPaymentTransactionInfoPlugins(final PaymentPluginApi plugin, final PaymentModelDao paymentModelDao, final Iterable<PluginProperty> properties, final TenantContext context) throws PaymentApiException {
        try {
            return plugin.getPaymentInfo(paymentModelDao.getAccountId(), paymentModelDao.getId(), properties, context);
        } catch (final PaymentPluginApiException e) {
            throw new PaymentApiException(ErrorCode.PAYMENT_PLUGIN_GET_PAYMENT_INFO, paymentModelDao.getId(), e.toString());
        }
    }

    // Used in bulk get APIs (getPayments / searchPayments)
    private Payment toPayment(final UUID paymentId, @Nullable final Iterable<PaymentTransactionInfoPlugin> pluginTransactions, final InternalTenantContext tenantContext) {
        final PaymentModelDao paymentModelDao = paymentDao.getPayment(paymentId, tenantContext);
        if (paymentModelDao == null) {
            log.warn("Unable to find payment id " + paymentId);
            return null;
        }

        return toPayment(paymentModelDao, pluginTransactions, tenantContext);
    }

    // Used in single get APIs (getPayment / getPaymentByExternalKey)
    private Payment toPayment(final PaymentModelDao paymentModelDao, final boolean withPluginInfo, final Iterable<PluginProperty> properties, final TenantContext context, final InternalTenantContext tenantContext) throws PaymentApiException {
        final PaymentPluginApi plugin = getPaymentProviderPlugin(paymentModelDao.getPaymentMethodId(), tenantContext);
        final List<PaymentTransactionInfoPlugin> pluginTransactions = withPluginInfo ? getPaymentTransactionInfoPlugins(plugin, paymentModelDao, properties, context) : null;

        return toPayment(paymentModelDao, pluginTransactions, tenantContext);
    }

    private Payment toPayment(final PaymentModelDao paymentModelDao, @Nullable final Iterable<PaymentTransactionInfoPlugin> pluginTransactions, final InternalTenantContext tenantContext) {
        final InternalTenantContext tenantContextWithAccountRecordId = getInternalTenantContextWithAccountRecordId(paymentModelDao.getAccountId(), tenantContext);
        final List<PaymentTransactionModelDao> transactionsForPayment = paymentDao.getTransactionsForPayment(paymentModelDao.getId(), tenantContextWithAccountRecordId);

        return toPayment(paymentModelDao, transactionsForPayment, pluginTransactions);
    }

    // Used in bulk get API (getAccountPayments)
    private Payment toPayment(final PaymentModelDao curPaymentModelDao, final Iterable<PaymentTransactionModelDao> transactionsModelDao, @Nullable final Iterable<PaymentTransactionInfoPlugin> pluginTransactions) {
        final Ordering<PaymentTransaction> perPaymentTransactionOrdering = Ordering.<PaymentTransaction>from(new Comparator<PaymentTransaction>() {
            @Override
            public int compare(final PaymentTransaction o1, final PaymentTransaction o2) {
                return o1.getEffectiveDate().compareTo(o2.getEffectiveDate());
            }
        });

        // Need to filter for optimized codepaths looking up by account_record_id
        final Iterable<PaymentTransactionModelDao> filteredTransactions = Iterables.filter(transactionsModelDao, new Predicate<PaymentTransactionModelDao>() {
            @Override
            public boolean apply(final PaymentTransactionModelDao curPaymentTransactionModelDao) {
                return curPaymentTransactionModelDao.getPaymentId().equals(curPaymentModelDao.getId());
            }
        });

        final Iterable<PaymentTransaction> transactions = Iterables.transform(filteredTransactions, new Function<PaymentTransactionModelDao, PaymentTransaction>() {
            @Override
            public PaymentTransaction apply(final PaymentTransactionModelDao paymentTransactionModelDao) {
                final PaymentTransactionInfoPlugin paymentTransactionInfoPlugin = pluginTransactions != null ?
                                                                                  Iterables.tryFind(pluginTransactions, new Predicate<PaymentTransactionInfoPlugin>() {
                                                                                      @Override
                                                                                      public boolean apply(final PaymentTransactionInfoPlugin paymentTransactionInfoPlugin) {
                                                                                          return paymentTransactionModelDao.getId().equals(paymentTransactionInfoPlugin.getKbTransactionPaymentId());
                                                                                      }
                                                                                  }).orNull() : null;

                return new DefaultPaymentTransaction(paymentTransactionModelDao.getId(), paymentTransactionModelDao.getAttemptId(), paymentTransactionModelDao.getTransactionExternalKey(), paymentTransactionModelDao.getCreatedDate(), paymentTransactionModelDao.getUpdatedDate(), paymentTransactionModelDao.getPaymentId(),
                                                     paymentTransactionModelDao.getTransactionType(), paymentTransactionModelDao.getEffectiveDate(), paymentTransactionModelDao.getTransactionStatus(), paymentTransactionModelDao.getAmount(), paymentTransactionModelDao.getCurrency(),
                                                     paymentTransactionModelDao.getProcessedAmount(), paymentTransactionModelDao.getProcessedCurrency(),
                                                     paymentTransactionModelDao.getGatewayErrorCode(), paymentTransactionModelDao.getGatewayErrorMsg(), paymentTransactionInfoPlugin);
            }
        });

        final List<PaymentTransaction> sortedTransactions = perPaymentTransactionOrdering.immutableSortedCopy(transactions);
        return new DefaultPayment(curPaymentModelDao.getId(), curPaymentModelDao.getCreatedDate(), curPaymentModelDao.getUpdatedDate(), curPaymentModelDao.getAccountId(),
                                  curPaymentModelDao.getPaymentMethodId(), curPaymentModelDao.getPaymentNumber(), curPaymentModelDao.getExternalKey(), sortedTransactions);
    }

    private InternalTenantContext getInternalTenantContextWithAccountRecordId(final UUID accountId, final InternalTenantContext tenantContext) {
        final InternalTenantContext tenantContextWithAccountRecordId;
        if (tenantContext.getAccountRecordId() == null) {
            tenantContextWithAccountRecordId = internalCallContextFactory.createInternalTenantContext(accountId, tenantContext);
        } else {
            tenantContextWithAccountRecordId = tenantContext;
        }
        return tenantContextWithAccountRecordId;
    }
}


File: payment/src/main/java/org/killbill/billing/payment/core/janitor/CompletionTaskBase.java
/*
 * Copyright 2014-2015 Groupon, Inc
 * Copyright 2014-2015 The Billing Project, LLC
 *
 * The Billing Project licenses this file to you under the Apache License, version 2.0
 * (the "License"); you may not use this file except in compliance with the
 * License.  You may obtain a copy of the License at:
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package org.killbill.billing.payment.core.janitor;

import java.util.List;

import org.joda.time.DateTime;
import org.killbill.billing.account.api.AccountInternalApi;
import org.killbill.billing.callcontext.DefaultCallContext;
import org.killbill.billing.callcontext.InternalTenantContext;
import org.killbill.billing.osgi.api.OSGIServiceRegistration;
import org.killbill.billing.payment.core.sm.PaymentStateMachineHelper;
import org.killbill.billing.payment.core.sm.PluginRoutingPaymentAutomatonRunner;
import org.killbill.billing.payment.core.sm.PaymentControlStateMachineHelper;
import org.killbill.billing.payment.dao.PaymentDao;
import org.killbill.billing.payment.plugin.api.PaymentPluginApi;
import org.killbill.billing.util.UUIDs;
import org.killbill.billing.util.callcontext.CallContext;
import org.killbill.billing.util.callcontext.CallOrigin;
import org.killbill.billing.util.callcontext.InternalCallContextFactory;
import org.killbill.billing.util.callcontext.TenantContext;
import org.killbill.billing.util.callcontext.UserType;
import org.killbill.billing.util.config.PaymentConfig;
import org.killbill.clock.Clock;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

abstract class CompletionTaskBase<T> implements Runnable {

    protected Logger log = LoggerFactory.getLogger(CompletionTaskBase.class);

    private final Janitor janitor;
    private final String taskName;

    protected final PaymentConfig paymentConfig;
    protected final Clock clock;
    protected final PaymentDao paymentDao;
    protected final InternalCallContextFactory internalCallContextFactory;
    protected final PaymentStateMachineHelper paymentStateMachineHelper;
    protected final PaymentControlStateMachineHelper retrySMHelper;
    protected final AccountInternalApi accountInternalApi;
    protected final PluginRoutingPaymentAutomatonRunner pluginControlledPaymentAutomatonRunner;
    protected final OSGIServiceRegistration<PaymentPluginApi> pluginRegistry;

    public CompletionTaskBase(final Janitor janitor, final InternalCallContextFactory internalCallContextFactory, final PaymentConfig paymentConfig,
                              final PaymentDao paymentDao, final Clock clock, final PaymentStateMachineHelper paymentStateMachineHelper,
                              final PaymentControlStateMachineHelper retrySMHelper, final AccountInternalApi accountInternalApi,
                              final PluginRoutingPaymentAutomatonRunner pluginControlledPaymentAutomatonRunner, final OSGIServiceRegistration<PaymentPluginApi> pluginRegistry) {
        this.janitor = janitor;
        this.internalCallContextFactory = internalCallContextFactory;
        this.paymentConfig = paymentConfig;
        this.paymentDao = paymentDao;
        this.clock = clock;
        this.paymentStateMachineHelper = paymentStateMachineHelper;
        this.retrySMHelper = retrySMHelper;
        this.accountInternalApi = accountInternalApi;
        this.pluginControlledPaymentAutomatonRunner = pluginControlledPaymentAutomatonRunner;
        this.pluginRegistry = pluginRegistry;
        // Limit the length of the username in the context (limited to 50 characters)
        this.taskName = this.getClass().getSimpleName();
    }

    @Override
    public void run() {

        if (janitor.isStopped()) {
            log.info("Janitor Task " + taskName + " was requested to stop");
            return;
        }
        final List<T> items = getItemsForIteration();
        for (final T item : items) {
            if (janitor.isStopped()) {
                log.info("Janitor Task " + taskName + " was requested to stop");
                return;
            }
            try {
                doIteration(item);
            } catch (final IllegalStateException e) {
                log.warn(e.getMessage());
            }
        }
    }

    public abstract List<T> getItemsForIteration();

    public abstract void doIteration(final T item);

    protected CallContext createCallContext(final String taskName, final InternalTenantContext internalTenantContext) {
        final TenantContext tenantContext = internalCallContextFactory.createTenantContext(internalTenantContext);
        final CallContext callContext = new DefaultCallContext(tenantContext.getTenantId(), taskName, CallOrigin.INTERNAL, UserType.SYSTEM, UUIDs.randomUUID(), clock);
        return callContext;
    }

}


File: payment/src/main/java/org/killbill/billing/payment/core/janitor/IncompletePaymentAttemptTask.java
/*
 * Copyright 2014-2015 Groupon, Inc
 * Copyright 2014-2015 The Billing Project, LLC
 *
 * The Billing Project licenses this file to you under the Apache License, version 2.0
 * (the "License"); you may not use this file except in compliance with the
 * License.  You may obtain a copy of the License at:
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package org.killbill.billing.payment.core.janitor;

import java.util.List;

import org.joda.time.DateTime;
import org.killbill.billing.account.api.Account;
import org.killbill.billing.account.api.AccountApiException;
import org.killbill.billing.account.api.AccountInternalApi;
import org.killbill.billing.callcontext.InternalCallContext;
import org.killbill.billing.callcontext.InternalTenantContext;
import org.killbill.billing.osgi.api.OSGIServiceRegistration;
import org.killbill.billing.payment.api.PaymentApiException;
import org.killbill.billing.payment.api.TransactionStatus;
import org.killbill.billing.payment.core.sm.PaymentStateMachineHelper;
import org.killbill.billing.payment.core.sm.PluginRoutingPaymentAutomatonRunner;
import org.killbill.billing.payment.core.sm.PaymentControlStateMachineHelper;
import org.killbill.billing.payment.core.sm.control.PaymentStateControlContext;
import org.killbill.billing.payment.dao.PaymentAttemptModelDao;
import org.killbill.billing.payment.dao.PaymentDao;
import org.killbill.billing.payment.dao.PaymentTransactionModelDao;
import org.killbill.billing.payment.dao.PluginPropertySerializer;
import org.killbill.billing.payment.dao.PluginPropertySerializer.PluginPropertySerializerException;
import org.killbill.billing.payment.plugin.api.PaymentPluginApi;
import org.killbill.billing.util.callcontext.CallContext;
import org.killbill.billing.util.callcontext.InternalCallContextFactory;
import org.killbill.billing.util.config.PaymentConfig;
import org.killbill.clock.Clock;

import com.google.common.base.Predicate;
import com.google.common.collect.Iterables;

/**
 * Task to complete 'partially' incomplete payment attempts. Tis only matters for calls that went through PaymentControl apis.
 * <p/>
 * If the state of the transaction associated with the attempt completed, but the attempt state machine did not,
 * we rerun the retry state machine to complete the call and transition the attempt into a terminal state.
 */
final class IncompletePaymentAttemptTask extends CompletionTaskBase<PaymentAttemptModelDao> {

    public IncompletePaymentAttemptTask(final Janitor janitor, final InternalCallContextFactory internalCallContextFactory, final PaymentConfig paymentConfig,
                                        final PaymentDao paymentDao, final Clock clock, final PaymentStateMachineHelper paymentStateMachineHelper,
                                        final PaymentControlStateMachineHelper retrySMHelper, final AccountInternalApi accountInternalApi,
                                        final PluginRoutingPaymentAutomatonRunner pluginControlledPaymentAutomatonRunner, final OSGIServiceRegistration<PaymentPluginApi> pluginRegistry) {
        super(janitor, internalCallContextFactory, paymentConfig, paymentDao, clock, paymentStateMachineHelper, retrySMHelper, accountInternalApi, pluginControlledPaymentAutomatonRunner, pluginRegistry);
    }

    @Override
    public List<PaymentAttemptModelDao> getItemsForIteration() {
        final List<PaymentAttemptModelDao> incompleteAttempts = paymentDao.getPaymentAttemptsByStateAcrossTenants(retrySMHelper.getInitialState().getName(), getCreatedDateBefore());
        if (!incompleteAttempts.isEmpty()) {
            log.info("Janitor AttemptCompletionTask start run: found {} incomplete attempts", incompleteAttempts.size());
        }
        return incompleteAttempts;
    }

    @Override
    public void doIteration(final PaymentAttemptModelDao attempt) {
        final InternalTenantContext tenantContext = internalCallContextFactory.createInternalTenantContext(attempt.getTenantRecordId(), attempt.getAccountRecordId());
        final CallContext callContext = createCallContext("AttemptCompletionJanitorTask", tenantContext);
        final InternalCallContext internalCallContext = internalCallContextFactory.createInternalCallContext(attempt.getAccountId(), callContext);

        final List<PaymentTransactionModelDao> transactions = paymentDao.getPaymentTransactionsByExternalKey(attempt.getTransactionExternalKey(), tenantContext);
        final PaymentTransactionModelDao transaction = Iterables.tryFind(transactions, new Predicate<PaymentTransactionModelDao>() {
            @Override
            public boolean apply(final PaymentTransactionModelDao input) {
                return input.getAttemptId().equals(attempt.getId()) &&
                       input.getTransactionStatus() == TransactionStatus.SUCCESS;
            }
        }).orNull();

        if (transaction == null) {
            log.info("Janitor AttemptCompletionTask moving attempt " + attempt.getId() + " -> ABORTED");
            paymentDao.updatePaymentAttempt(attempt.getId(), attempt.getTransactionId(), "ABORTED", internalCallContext);
            return;
        }

        try {
            log.info("Janitor AttemptCompletionTask completing attempt " + attempt.getId() + " -> SUCCESS");

            final Account account = accountInternalApi.getAccountById(attempt.getAccountId(), tenantContext);
            final boolean isApiPayment = true; // unclear
            final PaymentStateControlContext paymentStateContext = new PaymentStateControlContext(attempt.toPaymentControlPluginNames(),
                                                                                                      isApiPayment,
                                                                                                      transaction.getPaymentId(),
                                                                                                      attempt.getPaymentExternalKey(),
                                                                                                      transaction.getTransactionExternalKey(),
                                                                                                      transaction.getTransactionType(),
                                                                                                      account,
                                                                                                      attempt.getPaymentMethodId(),
                                                                                                      transaction.getAmount(),
                                                                                                      transaction.getCurrency(),
                                                                                                      PluginPropertySerializer.deserialize(attempt.getPluginProperties()),
                                                                                                      internalCallContext,
                                                                                                      callContext);

            paymentStateContext.setAttemptId(attempt.getId()); // Normally set by leavingState Callback
            paymentStateContext.setPaymentTransactionModelDao(transaction); // Normally set by raw state machine
            //
            // Will rerun the state machine with special callbacks to only make the executePluginOnSuccessCalls call
            // to the PaymentControlPluginApi plugin and transition the state.
            //
            pluginControlledPaymentAutomatonRunner.completeRun(paymentStateContext);
        } catch (final AccountApiException e) {
            log.warn("Janitor AttemptCompletionTask failed to complete payment attempt " + attempt.getId(), e);
        } catch (final PluginPropertySerializerException e) {
            log.warn("Janitor AttemptCompletionTask failed to complete payment attempt " + attempt.getId(), e);
        } catch (final PaymentApiException e) {
            log.warn("Janitor AttemptCompletionTask failed to complete payment attempt " + attempt.getId(), e);
        }
    }

    private DateTime getCreatedDateBefore() {
        final long delayBeforeNowMs = paymentConfig.getIncompleteAttemptsTimeSpanDelay().getMillis();
        return clock.getUTCNow().minusMillis((int) delayBeforeNowMs);
    }

}


File: payment/src/main/java/org/killbill/billing/payment/core/janitor/IncompletePaymentTransactionTask.java
/*
 * Copyright 2014-2015 Groupon, Inc
 * Copyright 2014-2015 The Billing Project, LLC
 *
 * The Billing Project licenses this file to you under the Apache License, version 2.0
 * (the "License"); you may not use this file except in compliance with the
 * License.  You may obtain a copy of the License at:
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package org.killbill.billing.payment.core.janitor;

import java.math.BigDecimal;
import java.util.List;

import org.joda.time.DateTime;
import org.killbill.billing.account.api.AccountInternalApi;
import org.killbill.billing.callcontext.InternalCallContext;
import org.killbill.billing.callcontext.InternalTenantContext;
import org.killbill.billing.catalog.api.Currency;
import org.killbill.billing.osgi.api.OSGIServiceRegistration;
import org.killbill.billing.payment.api.PluginProperty;
import org.killbill.billing.payment.api.TransactionStatus;
import org.killbill.billing.payment.core.PaymentTransactionInfoPluginConverter;
import org.killbill.billing.payment.core.sm.PaymentControlStateMachineHelper;
import org.killbill.billing.payment.core.sm.PaymentStateMachineHelper;
import org.killbill.billing.payment.core.sm.PluginRoutingPaymentAutomatonRunner;
import org.killbill.billing.payment.dao.PaymentDao;
import org.killbill.billing.payment.dao.PaymentMethodModelDao;
import org.killbill.billing.payment.dao.PaymentModelDao;
import org.killbill.billing.payment.dao.PaymentTransactionModelDao;
import org.killbill.billing.payment.plugin.api.PaymentPluginApi;
import org.killbill.billing.payment.plugin.api.PaymentPluginStatus;
import org.killbill.billing.payment.plugin.api.PaymentTransactionInfoPlugin;
import org.killbill.billing.payment.provider.DefaultNoOpPaymentInfoPlugin;
import org.killbill.billing.util.callcontext.CallContext;
import org.killbill.billing.util.callcontext.InternalCallContextFactory;
import org.killbill.billing.util.config.PaymentConfig;
import org.killbill.clock.Clock;

import com.google.common.base.Preconditions;
import com.google.common.base.Predicate;
import com.google.common.base.Supplier;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;

public class IncompletePaymentTransactionTask extends CompletionTaskBase<PaymentTransactionModelDao> {

    private static final ImmutableList<TransactionStatus> TRANSACTION_STATUSES_TO_CONSIDER = ImmutableList.<TransactionStatus>builder()
                                                                                                          .add(TransactionStatus.PENDING)
                                                                                                          .add(TransactionStatus.UNKNOWN)
                                                                                                          .build();
    private static final int MAX_ITEMS_PER_LOOP = 100;

    public IncompletePaymentTransactionTask(final Janitor janitor, final InternalCallContextFactory internalCallContextFactory, final PaymentConfig paymentConfig,
                                            final PaymentDao paymentDao, final Clock clock,
                                            final PaymentStateMachineHelper paymentStateMachineHelper, final PaymentControlStateMachineHelper retrySMHelper, final AccountInternalApi accountInternalApi,
                                            final PluginRoutingPaymentAutomatonRunner pluginControlledPaymentAutomatonRunner, final OSGIServiceRegistration<PaymentPluginApi> pluginRegistry) {
        super(janitor, internalCallContextFactory, paymentConfig, paymentDao, clock, paymentStateMachineHelper, retrySMHelper, accountInternalApi, pluginControlledPaymentAutomatonRunner, pluginRegistry);
    }

    @Override
    public List<PaymentTransactionModelDao> getItemsForIteration() {
        final List<PaymentTransactionModelDao> result = paymentDao.getByTransactionStatusAcrossTenants(TRANSACTION_STATUSES_TO_CONSIDER, getCreatedDateBefore(), getCreatedDateAfter(), MAX_ITEMS_PER_LOOP);
        if (!result.isEmpty()) {
            log.info("Janitor IncompletePaymentTransactionTask start run: found {} pending/unknown payments", result.size());
        }
        return result;
    }

    @Override
    public void doIteration(final PaymentTransactionModelDao paymentTransaction) {
        final InternalTenantContext internalTenantContext = internalCallContextFactory.createInternalTenantContext(paymentTransaction.getTenantRecordId(), paymentTransaction.getAccountRecordId());
        final CallContext callContext = createCallContext("IncompletePaymentTransactionTask", internalTenantContext);
        final PaymentModelDao payment = paymentDao.getPayment(paymentTransaction.getPaymentId(), internalTenantContext);

        final PaymentMethodModelDao paymentMethod = paymentDao.getPaymentMethod(payment.getPaymentMethodId(), internalTenantContext);
        final PaymentPluginApi paymentPluginApi = getPaymentPluginApi(payment, paymentMethod.getPluginName());

        final PaymentTransactionInfoPlugin undefinedPaymentTransaction = new DefaultNoOpPaymentInfoPlugin(payment.getId(),
                                                                                                          paymentTransaction.getId(),
                                                                                                          paymentTransaction.getTransactionType(),
                                                                                                          paymentTransaction.getAmount(),
                                                                                                          paymentTransaction.getCurrency(),
                                                                                                          paymentTransaction.getCreatedDate(),
                                                                                                          paymentTransaction.getCreatedDate(),
                                                                                                          PaymentPluginStatus.UNDEFINED,
                                                                                                          null);
        PaymentTransactionInfoPlugin paymentTransactionInfoPlugin;
        try {
            final List<PaymentTransactionInfoPlugin> result = paymentPluginApi.getPaymentInfo(payment.getAccountId(), payment.getId(), ImmutableList.<PluginProperty>of(), callContext);
            paymentTransactionInfoPlugin = Iterables.tryFind(result, new Predicate<PaymentTransactionInfoPlugin>() {
                @Override
                public boolean apply(final PaymentTransactionInfoPlugin input) {
                    return input.getKbTransactionPaymentId().equals(paymentTransaction.getId());
                }
            }).or(new Supplier<PaymentTransactionInfoPlugin>() {
                @Override
                public PaymentTransactionInfoPlugin get() {
                    return undefinedPaymentTransaction;
                }
            });
        } catch (final Exception e) {
            paymentTransactionInfoPlugin = undefinedPaymentTransaction;
        }

        //
        // First obtain the new transactionStatus,
        // Then compute the new paymentState; this one is mostly interesting in case of success (to compute the lastSuccessPaymentState below)
        //
        final TransactionStatus transactionStatus = computeNewTransactionStatusFromPaymentTransactionInfoPlugin(paymentTransactionInfoPlugin, paymentTransaction.getTransactionStatus());
        final String newPaymentState;
        switch (transactionStatus) {
            case PENDING:
                newPaymentState = paymentStateMachineHelper.getPendingStateForTransaction(paymentTransaction.getTransactionType());
                break;
            case SUCCESS:
                newPaymentState = paymentStateMachineHelper.getSuccessfulStateForTransaction(paymentTransaction.getTransactionType());
                break;
            case PAYMENT_FAILURE:
                newPaymentState = paymentStateMachineHelper.getFailureStateForTransaction(paymentTransaction.getTransactionType());
                break;
            case PLUGIN_FAILURE:
            case UNKNOWN:
            default:
                log.info("Janitor IncompletePaymentTransactionTask unable to repair payment {}, transaction {}: {} -> {}",
                         payment.getId(), paymentTransaction.getId(), paymentTransaction.getTransactionStatus(), transactionStatus);
                // We can't get anything interesting from the plugin...
                return;
        }

        // Recompute new lastSuccessPaymentState. This is important to be able to allow new operations on the state machine (for e.g an AUTH_SUCCESS would now allow a CAPTURE operation)
        final String lastSuccessPaymentState = paymentStateMachineHelper.isSuccessState(newPaymentState) ? newPaymentState : null;

        // Update the processedAmount, processedCurrency if we got a paymentTransactionInfoPlugin from the plugin and if this is a non error state
        final BigDecimal processedAmount = (paymentTransactionInfoPlugin != null && isPendingOrFinalTransactionStatus(transactionStatus)) ?
                                           paymentTransactionInfoPlugin.getAmount() : paymentTransaction.getProcessedAmount();
        final Currency processedCurrency = (paymentTransactionInfoPlugin != null && isPendingOrFinalTransactionStatus(transactionStatus)) ?
                                           paymentTransactionInfoPlugin.getCurrency() : paymentTransaction.getProcessedCurrency();

        // Update the gatewayErrorCode, gatewayError if we got a paymentTransactionInfoPlugin
        final String gatewayErrorCode = paymentTransactionInfoPlugin != null ? paymentTransactionInfoPlugin.getGatewayErrorCode() : paymentTransaction.getGatewayErrorCode();
        final String gatewayError = paymentTransactionInfoPlugin != null ? paymentTransactionInfoPlugin.getGatewayError() : paymentTransaction.getGatewayErrorMsg();

        log.info("Janitor IncompletePaymentTransactionTask repairing payment {}, transaction {}, transitioning transactionStatus from {} -> {}",
                 payment.getId(), paymentTransaction.getId(), paymentTransaction.getTransactionStatus(), transactionStatus);

        final InternalCallContext internalCallContext = internalCallContextFactory.createInternalCallContext(payment.getAccountId(), callContext);
        paymentDao.updatePaymentAndTransactionOnCompletion(payment.getAccountId(), payment.getId(), paymentTransaction.getTransactionType(), newPaymentState, lastSuccessPaymentState,
                                                           paymentTransaction.getId(), transactionStatus, processedAmount, processedCurrency, gatewayErrorCode, gatewayError, internalCallContext);
    }

    // Keep the existing currentTransactionStatus if we can't obtain a better answer from the plugin; if not, return the newTransactionStatus
    private TransactionStatus computeNewTransactionStatusFromPaymentTransactionInfoPlugin(final PaymentTransactionInfoPlugin input, final TransactionStatus currentTransactionStatus) {
        final TransactionStatus newTransactionStatus = PaymentTransactionInfoPluginConverter.toTransactionStatus(input);
        return (newTransactionStatus != TransactionStatus.UNKNOWN) ? newTransactionStatus : currentTransactionStatus;
    }

    private boolean isPendingOrFinalTransactionStatus(final TransactionStatus transactionStatus) {
        return (transactionStatus == TransactionStatus.PENDING ||
                transactionStatus == TransactionStatus.SUCCESS ||
                transactionStatus == TransactionStatus.PAYMENT_FAILURE);
    }

    private PaymentPluginApi getPaymentPluginApi(final PaymentModelDao item, final String pluginName) {
        final PaymentPluginApi pluginApi = pluginRegistry.getServiceForName(pluginName);
        Preconditions.checkState(pluginApi != null, "Janitor IncompletePaymentTransactionTask cannot retrieve PaymentPluginApi " + item.getId() + ", skipping");
        return pluginApi;
    }

    private DateTime getCreatedDateBefore() {
        final long delayBeforeNowMs = paymentConfig.getIncompleteTransactionsTimeSpanDelay().getMillis();
        return clock.getUTCNow().minusMillis((int) delayBeforeNowMs);
    }

    private DateTime getCreatedDateAfter() {
        final long delayBeforeNowMs = paymentConfig.getIncompleteTransactionsTimeSpanGiveup().getMillis();
        return clock.getUTCNow().minusMillis((int) delayBeforeNowMs);
    }
}


File: payment/src/main/java/org/killbill/billing/payment/core/janitor/Janitor.java
/*
 * Copyright 2014-2015 Groupon, Inc
 * Copyright 2014-2015 The Billing Project, LLC
 *
 * The Billing Project licenses this file to you under the Apache License, version 2.0
 * (the "License"); you may not use this file except in compliance with the
 * License.  You may obtain a copy of the License at:
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package org.killbill.billing.payment.core.janitor;

import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import javax.inject.Inject;
import javax.inject.Named;

import org.killbill.billing.account.api.AccountInternalApi;
import org.killbill.billing.osgi.api.OSGIServiceRegistration;
import org.killbill.billing.payment.core.sm.PaymentControlStateMachineHelper;
import org.killbill.billing.payment.core.sm.PaymentStateMachineHelper;
import org.killbill.billing.payment.core.sm.PluginRoutingPaymentAutomatonRunner;
import org.killbill.billing.payment.dao.PaymentDao;
import org.killbill.billing.payment.glue.PaymentModule;
import org.killbill.billing.payment.plugin.api.PaymentPluginApi;
import org.killbill.billing.util.callcontext.InternalCallContextFactory;
import org.killbill.billing.util.config.PaymentConfig;
import org.killbill.clock.Clock;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Takes care of incomplete payment/transactions.
 */
public class Janitor {

    private static final Logger log = LoggerFactory.getLogger(Janitor.class);

    private static final int TERMINATION_TIMEOUT_SEC = 5;

    private final ScheduledExecutorService janitorExecutor;
    private final PaymentConfig paymentConfig;
    private final IncompletePaymentAttemptTask incompletePaymentAttemptTask;
    private final IncompletePaymentTransactionTask incompletePaymentTransactionTask;

    private volatile boolean isStopped;

    @Inject
    public Janitor(final AccountInternalApi accountInternalApi,
                   final PaymentDao paymentDao,
                   final PaymentConfig paymentConfig,
                   final Clock clock,
                   final InternalCallContextFactory internalCallContextFactory,
                   final PluginRoutingPaymentAutomatonRunner pluginControlledPaymentAutomatonRunner,
                   @Named(PaymentModule.JANITOR_EXECUTOR_NAMED) final ScheduledExecutorService janitorExecutor,
                   final PaymentStateMachineHelper paymentSMHelper,
                   final PaymentControlStateMachineHelper retrySMHelper,
                   final OSGIServiceRegistration<PaymentPluginApi> pluginRegistry) {
        this.janitorExecutor = janitorExecutor;
        this.paymentConfig = paymentConfig;
        this.incompletePaymentAttemptTask = new IncompletePaymentAttemptTask(this, internalCallContextFactory, paymentConfig, paymentDao, clock, paymentSMHelper, retrySMHelper,
                                                                             accountInternalApi, pluginControlledPaymentAutomatonRunner, pluginRegistry);
        this.incompletePaymentTransactionTask = new IncompletePaymentTransactionTask(this, internalCallContextFactory, paymentConfig, paymentDao, clock, paymentSMHelper, retrySMHelper,
                                                                                     accountInternalApi, pluginControlledPaymentAutomatonRunner, pluginRegistry);
        this.isStopped = false;
    }

    public void start() {
        if (isStopped) {
            log.warn("Janitor is not a restartable service, and was already started, aborting");
            return;
        }

        // Start task for completing incomplete payment attempts
        final TimeUnit attemptCompletionRateUnit = paymentConfig.getJanitorRunningRate().getUnit();
        final long attemptCompletionPeriod = paymentConfig.getJanitorRunningRate().getPeriod();
        janitorExecutor.scheduleAtFixedRate(incompletePaymentAttemptTask, attemptCompletionPeriod, attemptCompletionPeriod, attemptCompletionRateUnit);

        // Start task for completing incomplete payment attempts
        final TimeUnit erroredCompletionRateUnit = paymentConfig.getJanitorRunningRate().getUnit();
        final long erroredCompletionPeriod = paymentConfig.getJanitorRunningRate().getPeriod();
        janitorExecutor.scheduleAtFixedRate(incompletePaymentTransactionTask, erroredCompletionPeriod, erroredCompletionPeriod, erroredCompletionRateUnit);
    }

    public void stop() {
        if (isStopped) {
            log.warn("Janitor is already in a stopped state");
            return;
        }
        try {
            /* Previously submitted tasks will be executed with shutdown(); when task executes as a result of shutdown being called
             * or because it was already in its execution loop, it will check for the volatile boolean isStopped flag and
             * return immediately.
             * Then, awaitTermination with a timeout is required to ensure tasks completed.
             */
            janitorExecutor.shutdown();
            final boolean success = janitorExecutor.awaitTermination(TERMINATION_TIMEOUT_SEC, TimeUnit.SECONDS);
            if (!success) {
                log.warn("Janitor failed to complete termination within " + TERMINATION_TIMEOUT_SEC + "sec");
            }
        } catch (final InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("Janitor stop sequence got interrupted");
        } finally {
            isStopped = true;
        }
    }

    public boolean isStopped() {
        return isStopped;
    }
}


File: payment/src/main/java/org/killbill/billing/payment/glue/PaymentModule.java
/*
 * Copyright 2010-2013 Ning, Inc.
 * Copyright 2014 Groupon, Inc
 * Copyright 2014 The Billing Project, LLC
 *
 * The Billing Project licenses this file to you under the Apache License, version 2.0
 * (the "License"); you may not use this file except in compliance with the
 * License.  You may obtain a copy of the License at:
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package org.killbill.billing.payment.glue;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;

import javax.inject.Provider;

import org.killbill.automaton.DefaultStateMachineConfig;
import org.killbill.automaton.StateMachineConfig;
import org.killbill.billing.osgi.api.OSGIServiceRegistration;
import org.killbill.billing.payment.api.AdminPaymentApi;
import org.killbill.billing.payment.api.DefaultAdminPaymentApi;
import org.killbill.billing.payment.api.DefaultPaymentApi;
import org.killbill.billing.payment.api.DefaultPaymentGatewayApi;
import org.killbill.billing.payment.api.PaymentApi;
import org.killbill.billing.payment.api.PaymentGatewayApi;
import org.killbill.billing.payment.api.PaymentService;
import org.killbill.billing.payment.bus.InvoiceHandler;
import org.killbill.billing.payment.invoice.PaymentTagHandler;
import org.killbill.billing.payment.invoice.dao.InvoicePaymentRoutingDao;
import org.killbill.billing.payment.core.janitor.Janitor;
import org.killbill.billing.payment.core.PaymentGatewayProcessor;
import org.killbill.billing.payment.core.PaymentMethodProcessor;
import org.killbill.billing.payment.core.PaymentProcessor;
import org.killbill.billing.payment.core.PluginRoutingPaymentProcessor;
import org.killbill.billing.payment.core.sm.PaymentStateMachineHelper;
import org.killbill.billing.payment.core.sm.PluginRoutingPaymentAutomatonRunner;
import org.killbill.billing.payment.core.sm.PaymentControlStateMachineHelper;
import org.killbill.billing.payment.dao.DefaultPaymentDao;
import org.killbill.billing.payment.dao.PaymentDao;
import org.killbill.billing.payment.plugin.api.PaymentPluginApi;
import org.killbill.billing.payment.retry.BaseRetryService.RetryServiceScheduler;
import org.killbill.billing.payment.retry.DefaultRetryService;
import org.killbill.billing.payment.retry.DefaultRetryService.DefaultRetryServiceScheduler;
import org.killbill.billing.payment.retry.RetryService;
import org.killbill.billing.platform.api.KillbillConfigSource;
import org.killbill.billing.routing.plugin.api.PaymentRoutingPluginApi;
import org.killbill.billing.util.config.PaymentConfig;
import org.killbill.billing.util.glue.KillBillModule;
import org.killbill.commons.concurrent.WithProfilingThreadPoolExecutor;
import org.killbill.xmlloader.XMLLoader;
import org.skife.config.ConfigurationObjectFactory;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.io.Resources;
import com.google.inject.Key;
import com.google.inject.TypeLiteral;
import com.google.inject.name.Names;

public class PaymentModule extends KillBillModule {

    private static final String PLUGIN_THREAD_PREFIX = "Plugin-th-";

    public static final String JANITOR_EXECUTOR_NAMED = "JanitorExecutor";
    public static final String PLUGIN_EXECUTOR_NAMED = "PluginExecutor";
    public static final String RETRYABLE_NAMED = "Retryable";

    public static final String STATE_MACHINE_RETRY = "RetryStateMachine";
    public static final String STATE_MACHINE_PAYMENT = "PaymentStateMachine";

    @VisibleForTesting
    static final String DEFAULT_STATE_MACHINE_RETRY_XML = "org/killbill/billing/payment/retry/RetryStates.xml";
    @VisibleForTesting
    static final String DEFAULT_STATE_MACHINE_PAYMENT_XML = "org/killbill/billing/payment/PaymentStates.xml";

    public PaymentModule(final KillbillConfigSource configSource) {
        super(configSource);
    }

    protected void installPaymentDao() {
        bind(PaymentDao.class).to(DefaultPaymentDao.class).asEagerSingleton();
        // Payment Control Plugin Dao
        bind(InvoicePaymentRoutingDao.class).asEagerSingleton();
    }

    protected void installPaymentProviderPlugins(final PaymentConfig config) {
    }

    protected void installJanitor() {
        final ScheduledExecutorService janitorExecutor = org.killbill.commons.concurrent.Executors.newSingleThreadScheduledExecutor("PaymentJanitor");
        bind(ScheduledExecutorService.class).annotatedWith(Names.named(JANITOR_EXECUTOR_NAMED)).toInstance(janitorExecutor);

        bind(Janitor.class).asEagerSingleton();
    }

    protected void installRetryEngines() {
        bind(DefaultRetryService.class).asEagerSingleton();
        bind(RetryService.class).annotatedWith(Names.named(RETRYABLE_NAMED)).to(DefaultRetryService.class);

        bind(DefaultRetryServiceScheduler.class).asEagerSingleton();
        bind(RetryServiceScheduler.class).annotatedWith(Names.named(RETRYABLE_NAMED)).to(DefaultRetryServiceScheduler.class);
    }

    protected void installStateMachines() {

        bind(StateMachineProvider.class).annotatedWith(Names.named(STATE_MACHINE_RETRY)).toInstance(new StateMachineProvider(DEFAULT_STATE_MACHINE_RETRY_XML));
        bind(StateMachineConfig.class).annotatedWith(Names.named(STATE_MACHINE_RETRY)).toProvider(Key.get(StateMachineProvider.class, Names.named(STATE_MACHINE_RETRY)));
        bind(PaymentControlStateMachineHelper.class).asEagerSingleton();

        bind(StateMachineProvider.class).annotatedWith(Names.named(STATE_MACHINE_PAYMENT)).toInstance(new StateMachineProvider(DEFAULT_STATE_MACHINE_PAYMENT_XML));
        bind(StateMachineConfig.class).annotatedWith(Names.named(STATE_MACHINE_PAYMENT)).toProvider(Key.get(StateMachineProvider.class, Names.named(STATE_MACHINE_PAYMENT)));
        bind(PaymentStateMachineHelper.class).asEagerSingleton();
    }

    public static final class StateMachineProvider implements Provider<StateMachineConfig> {

        private final String stateMachineConfig;

        public StateMachineProvider(final String stateMachineConfig) {
            this.stateMachineConfig = stateMachineConfig;
        }

        @Override
        public StateMachineConfig get() {
            try {
                return XMLLoader.getObjectFromString(Resources.getResource(stateMachineConfig).toExternalForm(), DefaultStateMachineConfig.class);
            } catch (final Exception e) {
                throw new IllegalStateException(e);
            }
        }
    }

    protected void installAutomatonRunner() {
        bind(PluginRoutingPaymentAutomatonRunner.class).asEagerSingleton();
    }

    protected void installProcessors(final PaymentConfig paymentConfig) {

        final ExecutorService pluginExecutorService = new WithProfilingThreadPoolExecutor(paymentConfig.getPaymentPluginThreadNb(), paymentConfig.getPaymentPluginThreadNb(),
                                                                                          0L, TimeUnit.MILLISECONDS,
                                                                                          new LinkedBlockingQueue<Runnable>(),
                                                                                          new ThreadFactory() {

                                                                                              @Override
                                                                                              public Thread newThread(final Runnable r) {
                                                                                                  final Thread th = new Thread(r);
                                                                                                  th.setName(PLUGIN_THREAD_PREFIX + th.getId());
                                                                                                  return th;
                                                                                              }
                                                                                          });
        bind(ExecutorService.class).annotatedWith(Names.named(PLUGIN_EXECUTOR_NAMED)).toInstance(pluginExecutorService);
        bind(PaymentProcessor.class).asEagerSingleton();
        bind(PluginRoutingPaymentProcessor.class).asEagerSingleton();
        bind(PaymentGatewayProcessor.class).asEagerSingleton();
        bind(PaymentMethodProcessor.class).asEagerSingleton();
    }

    @Override
    protected void configure() {
        final ConfigurationObjectFactory factory = new ConfigurationObjectFactory(skifeConfigSource);
        final PaymentConfig paymentConfig = factory.build(PaymentConfig.class);

        bind(PaymentConfig.class).toInstance(paymentConfig);
        bind(new TypeLiteral<OSGIServiceRegistration<PaymentPluginApi>>() {}).toProvider(DefaultPaymentProviderPluginRegistryProvider.class).asEagerSingleton();
        bind(new TypeLiteral<OSGIServiceRegistration<PaymentRoutingPluginApi>>() {}).toProvider(DefaultPaymentRoutingProviderPluginRegistryProvider.class).asEagerSingleton();

        bind(PaymentApi.class).to(DefaultPaymentApi.class).asEagerSingleton();
        bind(PaymentGatewayApi.class).to(DefaultPaymentGatewayApi.class).asEagerSingleton();
        bind(AdminPaymentApi.class).to(DefaultAdminPaymentApi.class).asEagerSingleton();
        bind(InvoiceHandler.class).asEagerSingleton();
        bind(PaymentTagHandler.class).asEagerSingleton();
        bind(PaymentService.class).to(DefaultPaymentService.class).asEagerSingleton();
        installPaymentProviderPlugins(paymentConfig);
        installPaymentDao();
        installProcessors(paymentConfig);
        installStateMachines();
        installAutomatonRunner();
        installRetryEngines();
        installJanitor();
    }
}
