Refactoring Types: ['Inline Method']
lbill/billing/payment/core/PaymentTransactionInfoPluginConverter.java
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

package org.killbill.billing.payment.core;

import javax.annotation.Nullable;

import org.killbill.automaton.OperationResult;
import org.killbill.billing.payment.api.TransactionStatus;
import org.killbill.billing.payment.plugin.api.PaymentTransactionInfoPlugin;

//
// Conversion between the plugin result to the payment state and transaction status
//
public class PaymentTransactionInfoPluginConverter {

    public static TransactionStatus toTransactionStatus(@Nullable final PaymentTransactionInfoPlugin paymentTransactionInfoPlugin) {
        //
        // paymentTransactionInfoPlugin when we got an exception from the plugin, or if the plugin behaves badly
        // and decides to return null; in all cases this is seen as a PLUGIN_FAILURE
        //
        if (paymentTransactionInfoPlugin == null || paymentTransactionInfoPlugin.getStatus() == null) {
            return TransactionStatus.PLUGIN_FAILURE;
        }

        switch (paymentTransactionInfoPlugin.getStatus()) {
            case PROCESSED:
                return TransactionStatus.SUCCESS;
            case PENDING:
                return TransactionStatus.PENDING;
            case ERROR:
                return TransactionStatus.PAYMENT_FAILURE;
            // This will be picked up by Janitor to figure out what really happened and correct the state if needed
            case UNDEFINED:
            default:
                return TransactionStatus.UNKNOWN;
        }
    }

    public static OperationResult toOperationResult(@Nullable final PaymentTransactionInfoPlugin paymentTransactionInfoPlugin) {
        if (paymentTransactionInfoPlugin == null || paymentTransactionInfoPlugin.getStatus() == null) {
            return OperationResult.EXCEPTION;
        }

        switch (paymentTransactionInfoPlugin.getStatus()) {
            case PROCESSED:
                return OperationResult.SUCCESS;
            case PENDING:
                return OperationResult.PENDING;
            case ERROR:
                return OperationResult.FAILURE;
            // Might change later if Janitor fixes the state
            case UNDEFINED:
            default:
                return OperationResult.EXCEPTION;
        }
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

import javax.annotation.Nullable;

import org.joda.time.DateTime;
import org.killbill.billing.account.api.AccountInternalApi;
import org.killbill.billing.callcontext.InternalCallContext;
import org.killbill.billing.callcontext.InternalTenantContext;
import org.killbill.billing.catalog.api.Currency;
import org.killbill.billing.osgi.api.OSGIServiceRegistration;
import org.killbill.billing.payment.api.PluginProperty;
import org.killbill.billing.payment.api.TransactionStatus;
import org.killbill.billing.payment.core.PaymentTransactionInfoPluginConverter;
import org.killbill.billing.payment.core.sm.PaymentStateMachineHelper;
import org.killbill.billing.payment.core.sm.PluginRoutingPaymentAutomatonRunner;
import org.killbill.billing.payment.core.sm.PaymentControlStateMachineHelper;
import org.killbill.billing.payment.dao.PaymentDao;
import org.killbill.billing.payment.dao.PaymentMethodModelDao;
import org.killbill.billing.payment.dao.PaymentModelDao;
import org.killbill.billing.payment.dao.PaymentTransactionModelDao;
import org.killbill.billing.payment.plugin.api.PaymentPluginApi;
import org.killbill.billing.payment.plugin.api.PaymentPluginApiException;
import org.killbill.billing.payment.plugin.api.PaymentTransactionInfoPlugin;
import org.killbill.billing.util.callcontext.CallContext;
import org.killbill.billing.util.callcontext.InternalCallContextFactory;
import org.killbill.billing.util.config.PaymentConfig;
import org.killbill.clock.Clock;

import com.google.common.base.Preconditions;
import com.google.common.base.Predicate;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;

public class IncompletePaymentTransactionTask extends CompletionTaskBase<PaymentTransactionModelDao> {

    private final static ImmutableList<TransactionStatus> TRANSACTION_STATUSES_TO_CONSIDER = ImmutableList.<TransactionStatus>builder()
                                                                                                          .add(TransactionStatus.PENDING)
                                                                                                          .add(TransactionStatus.UNKNOWN)
                                                                                                          .build();
    private final static int MAX_ITEMS_PER_LOOP = 100;


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

        PaymentTransactionInfoPlugin paymentTransactionInfoPlugin;
        try {
            final List<PaymentTransactionInfoPlugin> result = paymentPluginApi.getPaymentInfo(payment.getAccountId(), payment.getId(), ImmutableList.<PluginProperty>of(), callContext);
            paymentTransactionInfoPlugin = Iterables.tryFind(result, new Predicate<PaymentTransactionInfoPlugin>() {
                @Override
                public boolean apply(final PaymentTransactionInfoPlugin input) {
                    return input.getKbTransactionPaymentId().equals(paymentTransaction.getId());
                }
            }).orNull();
        } catch (final PaymentPluginApiException ignored) {
            // The paymentTransactionInfoPlugin will be null and handled below as if the plugin did not know about that transaction
            paymentTransactionInfoPlugin = null;
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
                log.info("Janitor IncompletePaymentTransactionTask repairing payment {}, transaction {}, bail early...",
                         new Object[] {payment.getId(), paymentTransaction.getId(), paymentTransaction.getTransactionStatus(), transactionStatus});
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
                 new Object[] {payment.getId(), paymentTransaction.getId(), paymentTransaction.getTransactionStatus(), transactionStatus});

        final InternalCallContext internalCallContext = internalCallContextFactory.createInternalCallContext(payment.getAccountId(), callContext);
        paymentDao.updatePaymentAndTransactionOnCompletion(payment.getAccountId(), payment.getId(), paymentTransaction.getTransactionType(), newPaymentState, lastSuccessPaymentState,
                                                           paymentTransaction.getId(), transactionStatus, processedAmount, processedCurrency, gatewayErrorCode, gatewayError, internalCallContext);

    }

    // Keep the existing currentTransactionStatus if we can't obtain a better answer from the plugin; if not, return the newTransactionStatus
    private TransactionStatus computeNewTransactionStatusFromPaymentTransactionInfoPlugin(@Nullable PaymentTransactionInfoPlugin input, final TransactionStatus currentTransactionStatus) {
        final TransactionStatus newTransactionStatus = PaymentTransactionInfoPluginConverter.toTransactionStatus(input);
        if (newTransactionStatus == TransactionStatus.PLUGIN_FAILURE || newTransactionStatus ==  TransactionStatus.UNKNOWN) {
            return currentTransactionStatus;
        } else {
            return newTransactionStatus;
        }
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


File: payment/src/main/java/org/killbill/billing/payment/core/sm/payments/PaymentOperation.java
/*
 * Copyright 2014 Groupon, Inc
 * Copyright 2014 The Billing Project, LLC
 *
 * Groupon licenses this file to you under the Apache License, version 2.0
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

package org.killbill.billing.payment.core.sm.payments;

import java.math.BigDecimal;
import java.util.Iterator;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeoutException;

import org.killbill.automaton.Operation.OperationCallback;
import org.killbill.automaton.OperationException;
import org.killbill.automaton.OperationResult;
import org.killbill.billing.ErrorCode;
import org.killbill.billing.payment.api.PaymentApiException;
import org.killbill.billing.payment.api.TransactionStatus;
import org.killbill.billing.payment.api.TransactionType;
import org.killbill.billing.payment.core.PaymentTransactionInfoPluginConverter;
import org.killbill.billing.payment.core.ProcessorBase.WithAccountLockCallback;
import org.killbill.billing.payment.core.sm.OperationCallbackBase;
import org.killbill.billing.payment.core.sm.PaymentAutomatonDAOHelper;
import org.killbill.billing.payment.core.sm.PaymentStateContext;
import org.killbill.billing.payment.dao.PaymentTransactionModelDao;
import org.killbill.billing.payment.dispatcher.PluginDispatcher;
import org.killbill.billing.payment.dispatcher.PluginDispatcher.PluginDispatcherReturnType;
import org.killbill.billing.payment.plugin.api.PaymentPluginApi;
import org.killbill.billing.payment.plugin.api.PaymentPluginApiException;
import org.killbill.billing.payment.plugin.api.PaymentPluginStatus;
import org.killbill.billing.payment.plugin.api.PaymentTransactionInfoPlugin;
import org.killbill.billing.payment.provider.DefaultNoOpPaymentInfoPlugin;
import org.killbill.commons.locker.GlobalLocker;
import org.killbill.commons.locker.LockFailedException;

import com.google.common.base.Objects;
import com.google.common.base.Predicate;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;

// Encapsulates the payment specific logic
public abstract class PaymentOperation extends OperationCallbackBase<PaymentTransactionInfoPlugin, PaymentPluginApiException> implements OperationCallback {

    protected final PaymentAutomatonDAOHelper daoHelper;
    protected PaymentPluginApi plugin;

    protected PaymentOperation(final GlobalLocker locker,
                               final PaymentAutomatonDAOHelper daoHelper,
                               final PluginDispatcher<OperationResult> paymentPluginDispatcher,
                               final PaymentStateContext paymentStateContext) {
        super(locker, paymentPluginDispatcher, paymentStateContext);
        this.daoHelper = daoHelper;
    }

    @Override
    public OperationResult doOperationCallback() throws OperationException {
        try {
            this.plugin = daoHelper.getPaymentProviderPlugin();

            if (paymentStateContext.shouldLockAccountAndDispatch()) {
                return doOperationCallbackWithDispatchAndAccountLock();
            } else {
                return doSimpleOperationCallback();
            }
        } catch (final PaymentApiException e) {
            throw new OperationException(e, OperationResult.EXCEPTION);
        }
    }

    @Override
    protected OperationException rewrapExecutionException(final PaymentStateContext paymentStateContext, final ExecutionException e) {
        final Throwable realException = Objects.firstNonNull(e.getCause(), e);
        if (e.getCause() instanceof PaymentApiException) {
            logger.warn("Unsuccessful plugin call for account {}", paymentStateContext.getAccount().getExternalKey(), realException);
            return convertToUnknownTransactionStatusAndErroredPaymentState(realException);
        } else if (e.getCause() instanceof LockFailedException) {
            final String format = String.format("Failed to lock account %s", paymentStateContext.getAccount().getExternalKey());
            logger.error(String.format(format));
            return new OperationException(realException, OperationResult.EXCEPTION);
        } else /* if (e instanceof RuntimeException) */ {
            logger.warn("Plugin call threw an exception for account {}", paymentStateContext.getAccount().getExternalKey(), e);
            return new OperationException(realException, OperationResult.EXCEPTION);
        }
    }

    @Override
    protected OperationException wrapTimeoutException(final PaymentStateContext paymentStateContext, final TimeoutException e) {
        logger.error("Plugin call TIMEOUT for account {}", paymentStateContext.getAccount().getExternalKey());
        return convertToUnknownTransactionStatusAndErroredPaymentState(e);
    }

    //
    // In the case we don't know exactly what happen (Timeout or PluginApiException):
    // - Return an OperationResult.EXCEPTION to transition Payment State to Errored (see PaymentTransactionInfoPluginConverter#toOperationResult)
    // - Construct a PaymentTransactionInfoPlugin whose PaymentPluginStatus = UNDEFINED to end up with a paymentTransactionStatus = UNKNOWN and have a chance to
    //   be fixed by Janitor.
    //
    private OperationException convertToUnknownTransactionStatusAndErroredPaymentState(final Throwable e) {

        final PaymentTransactionInfoPlugin paymentInfoPlugin = new DefaultNoOpPaymentInfoPlugin(paymentStateContext.getPaymentId(),
                                                                                                paymentStateContext.getTransactionId(),
                                                                                                paymentStateContext.getTransactionType(),
                                                                                                paymentStateContext.getAmount(),
                                                                                                paymentStateContext.getCurrency(),
                                                                                                paymentStateContext.getCallContext().getCreatedDate(),
                                                                                                paymentStateContext.getCallContext().getCreatedDate(),
                                                                                                PaymentPluginStatus.UNDEFINED,
                                                                                                null);

        paymentStateContext.setPaymentTransactionInfoPlugin(paymentInfoPlugin);
        return new OperationException(e, OperationResult.EXCEPTION);
    }

    @Override
    protected OperationException wrapInterruptedException(final PaymentStateContext paymentStateContext, final InterruptedException e) {
        logger.error("Plugin call was interrupted for account {}", paymentStateContext.getAccount().getExternalKey());
        return new OperationException(e, OperationResult.EXCEPTION);
    }

    @Override
    protected abstract PaymentTransactionInfoPlugin doCallSpecificOperationCallback() throws PaymentPluginApiException;

    protected Iterable<PaymentTransactionModelDao> getOnLeavingStateExistingTransactionsForType(final TransactionType transactionType) {
        if (paymentStateContext.getOnLeavingStateExistingTransactions() == null || paymentStateContext.getOnLeavingStateExistingTransactions().isEmpty()) {
            return ImmutableList.of();
        }
        return Iterables.filter(paymentStateContext.getOnLeavingStateExistingTransactions(), new Predicate<PaymentTransactionModelDao>() {
            @Override
            public boolean apply(final PaymentTransactionModelDao input) {
                return input.getTransactionStatus() == TransactionStatus.SUCCESS && input.getTransactionType() == transactionType;
            }
        });
    }

    protected BigDecimal getSumAmount(final Iterable<PaymentTransactionModelDao> transactions) {
        BigDecimal result = BigDecimal.ZERO;
        final Iterator<PaymentTransactionModelDao> iterator = transactions.iterator();
        while (iterator.hasNext()) {
            result = result.add(iterator.next().getAmount());
        }
        return result;
    }

    private OperationResult doOperationCallbackWithDispatchAndAccountLock() throws OperationException {
        return dispatchWithAccountLockAndTimeout(new WithAccountLockCallback<PluginDispatcherReturnType<OperationResult>, OperationException>() {
            @Override
            public PluginDispatcherReturnType<OperationResult> doOperation() throws OperationException {
                final OperationResult result = doSimpleOperationCallback();
                return PluginDispatcher.createPluginDispatcherReturnType(result);
            }
        });
    }

    private OperationResult doSimpleOperationCallback() throws OperationException {
        try {
            return doOperation();
        } catch (final PaymentApiException e) {
            throw new OperationException(e, OperationResult.EXCEPTION);
        } catch (final RuntimeException e) {
            throw new OperationException(e, OperationResult.EXCEPTION);
        }
    }

    private OperationResult doOperation() throws PaymentApiException {
        try {
            //
            // If the OperationResult was specified in the plugin, it means we want to bypass the plugin and just care
            // about running through the state machine to bring the transaction/payment into a new state.
            //
            if (paymentStateContext.getOverridePluginOperationResult() == null) {
                final PaymentTransactionInfoPlugin paymentInfoPlugin = doCallSpecificOperationCallback();
                // Throws if plugin is  ot correctly implemented (e.g returns null result, values,..)
                sanityOnPaymentInfoPlugin(paymentInfoPlugin);

                paymentStateContext.setPaymentTransactionInfoPlugin(paymentInfoPlugin);
                return PaymentTransactionInfoPluginConverter.toOperationResult(paymentStateContext.getPaymentTransactionInfoPlugin());
            } else {
                final PaymentTransactionInfoPlugin paymentInfoPlugin = new DefaultNoOpPaymentInfoPlugin(paymentStateContext.getPaymentId(),
                                                                                                        paymentStateContext.getTransactionId(),
                                                                                                        paymentStateContext.getTransactionType(),
                                                                                                        paymentStateContext.getPaymentTransactionModelDao().getProcessedAmount(),
                                                                                                        paymentStateContext.getPaymentTransactionModelDao().getProcessedCurrency(),
                                                                                                        paymentStateContext.getPaymentTransactionModelDao().getEffectiveDate(),
                                                                                                        paymentStateContext.getPaymentTransactionModelDao().getCreatedDate(),
                                                                                                        buildPaymentPluginStatusFromOperationResult(paymentStateContext.getOverridePluginOperationResult()),
                                                                                                        null);
                paymentStateContext.setPaymentTransactionInfoPlugin(paymentInfoPlugin);
                return paymentStateContext.getOverridePluginOperationResult();
            }
        } catch (final PaymentPluginApiException e) {
            throw new PaymentApiException(ErrorCode.PAYMENT_PLUGIN_EXCEPTION, e.getErrorMessage());
        }
    }

    private PaymentPluginStatus buildPaymentPluginStatusFromOperationResult(final OperationResult operationResult) {
        switch (operationResult) {
            case PENDING:
                return PaymentPluginStatus.PENDING;
            case SUCCESS:
                return PaymentPluginStatus.PROCESSED;
            case FAILURE:
                return PaymentPluginStatus.ERROR;
            case EXCEPTION:
            default:
                return PaymentPluginStatus.UNDEFINED;
        }
    }

    private void sanityOnPaymentInfoPlugin(final PaymentTransactionInfoPlugin paymentInfoPlugin) throws PaymentApiException {
        if (paymentInfoPlugin == null) {
            throw new PaymentApiException(ErrorCode.PAYMENT_PLUGIN_EXCEPTION, "Payment plugin returned a null result");
        }
        /*
        TODO this breaks our tests so test would have to be fixed
        if (paymentTransactionInfoPlugin.getKbTransactionPaymentId() == null || !paymentTransactionInfoPlugin.getKbTransactionPaymentId().equals(paymentStateContext.getTransactionId())) {
            throw new PaymentApiException(ErrorCode.PAYMENT_PLUGIN_EXCEPTION, "Payment plugin returned invalid kbTransactionId");
        }
        if (paymentTransactionInfoPlugin.getKbPaymentId() == null || !paymentTransactionInfoPlugin.getKbPaymentId().equals(paymentStateContext.getPaymentId())) {
            throw new PaymentApiException(ErrorCode.PAYMENT_PLUGIN_EXCEPTION, "Payment plugin returned invalid kbPaymentId");
        }
        if (paymentTransactionInfoPlugin.getTransactionType() == null || !paymentTransactionInfoPlugin.getKbPaymentId().equals(paymentStateContext.getTransactionType())) {
            throw new PaymentApiException(ErrorCode.PAYMENT_PLUGIN_EXCEPTION, "Payment plugin returned invalid transaction type");
        }
        */
    }
}
