Refactoring Types: ['Extract Method']
j/protocols/channels/PaymentChannelClientState.java
/*
 * Copyright 2013 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.protocols.channels;

import org.bitcoinj.core.*;
import org.bitcoinj.crypto.TransactionSignature;
import org.bitcoinj.script.Script;
import org.bitcoinj.script.ScriptBuilder;
import org.bitcoinj.utils.Threading;
import org.bitcoinj.wallet.AllowUnconfirmedCoinSelector;
import org.spongycastle.crypto.params.KeyParameter;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Throwables;
import com.google.common.collect.Lists;
import com.google.common.util.concurrent.FutureCallback;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Nullable;
import java.util.List;

import static com.google.common.base.Preconditions.*;

/**
 * <p>A payment channel is a method of sending money to someone such that the amount of money you send can be adjusted
 * after the fact, in an efficient manner that does not require broadcasting to the network. This can be used to
 * implement micropayments or other payment schemes in which immediate settlement is not required, but zero trust
 * negotiation is. Note that this class only allows the amount of money sent to be incremented, not decremented.</p>
 *
 * <p>This class implements the core state machine for the client side of the protocol. The server side is implemented
 * by {@link PaymentChannelServerState} and {@link PaymentChannelClientConnection} implements a network protocol
 * suitable for TCP/IP connections which moves this class through each state. We say that the party who is sending funds
 * is the <i>client</i> or <i>initiating party</i>. The party that is receiving the funds is the <i>server</i> or
 * <i>receiving party</i>. Although the underlying Bitcoin protocol is capable of more complex relationships than that,
 * this class implements only the simplest case.</p>
 *
 * <p>A channel has an expiry parameter. If the server halts after the multi-signature contract which locks
 * up the given value is broadcast you could get stuck in a state where you've lost all the money put into the
 * contract. To avoid this, a refund transaction is agreed ahead of time but it may only be used/broadcast after
 * the expiry time. This is specified in terms of block timestamps and once the timestamp of the chain chain approaches
 * the given time (within a few hours), the channel must be closed or else the client will broadcast the refund
 * transaction and take back all the money once the expiry time is reached.</p>
 *
 * <p>To begin, the client calls {@link PaymentChannelClientState#initiate()}, which moves the channel into state
 * INITIATED and creates the initial multi-sig contract and refund transaction. If the wallet has insufficient funds an
 * exception will be thrown at this point. Once this is done, call
 * {@link PaymentChannelClientState#getIncompleteRefundTransaction()} and pass the resultant transaction through to the
 * server. Once you have retrieved the signature, use {@link PaymentChannelClientState#provideRefundSignature(byte[], KeyParameter)}.
 * You must then call {@link PaymentChannelClientState#storeChannelInWallet(Sha256Hash)} to store the refund transaction
 * in the wallet, protecting you against a malicious server attempting to destroy all your coins. At this point, you can
 * provide the server with the multi-sig contract (via {@link PaymentChannelClientState#getMultisigContract()}) safely.
 * </p>
 */
public class PaymentChannelClientState {
    private static final Logger log = LoggerFactory.getLogger(PaymentChannelClientState.class);

    private final Wallet wallet;
    // Both sides need a key (private in our case, public for the server) in order to manage the multisig contract
    // and transactions that spend it.
    private final ECKey myKey, serverMultisigKey;
    // How much value (in satoshis) is locked up into the channel.
    private final Coin totalValue;
    // When the channel will automatically settle in favor of the client, if the server halts before protocol termination
    // specified in terms of block timestamps (so it can off real time by a few hours).
    private final long expiryTime;

    // The refund is a time locked transaction that spends all the money of the channel back to the client.
    private Transaction refundTx;
    private Coin refundFees;
    // The multi-sig contract locks the value of the channel up such that the agreement of both parties is required
    // to spend it.
    private Transaction multisigContract;
    private Script multisigScript;
    // How much value is currently allocated to us. Starts as being same as totalValue.
    private Coin valueToMe;

    /**
     * The different logical states the channel can be in. The channel starts out as NEW, and then steps through the
     * states until it becomes finalized. The server should have already been contacted and asked for a public key
     * by the time the NEW state is reached.
     */
    public enum State {
        NEW,
        INITIATED,
        WAITING_FOR_SIGNED_REFUND,
        SAVE_STATE_IN_WALLET,
        PROVIDE_MULTISIG_CONTRACT_TO_SERVER,
        READY,
        EXPIRED,
        CLOSED
    }
    private State state;

    // The id of this channel in the StoredPaymentChannelClientStates, or null if it is not stored
    private StoredClientChannel storedChannel;

    PaymentChannelClientState(StoredClientChannel storedClientChannel, Wallet wallet) throws VerificationException {
        // The PaymentChannelClientConnection handles storedClientChannel.active and ensures we aren't resuming channels
        this.wallet = checkNotNull(wallet);
        this.multisigContract = checkNotNull(storedClientChannel.contract);
        this.multisigScript = multisigContract.getOutput(0).getScriptPubKey();
        this.refundTx = checkNotNull(storedClientChannel.refund);
        this.refundFees = checkNotNull(storedClientChannel.refundFees);
        this.expiryTime = refundTx.getLockTime();
        this.myKey = checkNotNull(storedClientChannel.myKey);
        this.serverMultisigKey = null;
        this.totalValue = multisigContract.getOutput(0).getValue();
        this.valueToMe = checkNotNull(storedClientChannel.valueToMe);
        this.storedChannel = storedClientChannel;
        this.state = State.READY;
        initWalletListeners();
    }

    /**
     * Returns true if the tx is a valid settlement transaction.
     */
    public synchronized boolean isSettlementTransaction(Transaction tx) {
        try {
            tx.verify();
            tx.getInput(0).verify(multisigContract.getOutput(0));
            return true;
        } catch (VerificationException e) {
            return false;
        }
    }

    /**
     * Creates a state object for a payment channel client. It is expected that you be ready to
     * {@link PaymentChannelClientState#initiate()} after construction (to avoid creating objects for channels which are
     * not going to finish opening) and thus some parameters provided here are only used in
     * {@link PaymentChannelClientState#initiate()} to create the Multisig contract and refund transaction.
     *
     * @param wallet a wallet that contains at least the specified amount of value.
     * @param myKey a freshly generated private key for this channel.
     * @param serverMultisigKey a public key retrieved from the server used for the initial multisig contract
     * @param value how many satoshis to put into this contract. If the channel reaches this limit, it must be closed.
     *              It is suggested you use at least {@link Coin#CENT} to avoid paying fees if you need to spend the refund transaction
     * @param expiryTimeInSeconds At what point (UNIX timestamp +/- a few hours) the channel will expire
     *
     * @throws VerificationException If either myKey's pubkey or serverMultisigKey's pubkey are non-canonical (ie invalid)
     */
    public PaymentChannelClientState(Wallet wallet, ECKey myKey, ECKey serverMultisigKey,
                                     Coin value, long expiryTimeInSeconds) throws VerificationException {
        checkArgument(value.signum() > 0);
        this.wallet = checkNotNull(wallet);
        initWalletListeners();
        this.serverMultisigKey = checkNotNull(serverMultisigKey);
        this.myKey = checkNotNull(myKey);
        this.valueToMe = this.totalValue = checkNotNull(value);
        this.expiryTime = expiryTimeInSeconds;
        this.state = State.NEW;
    }

    private synchronized void initWalletListeners() {
        // Register a listener that watches out for the server closing the channel.
        if (storedChannel != null && storedChannel.close != null) {
            watchCloseConfirmations();
        }
        wallet.addEventListener(new AbstractWalletEventListener() {
            @Override
            public void onCoinsReceived(Wallet wallet, Transaction tx, Coin prevBalance, Coin newBalance) {
                synchronized (PaymentChannelClientState.this) {
                    if (multisigContract == null) return;
                    if (isSettlementTransaction(tx)) {
                        log.info("Close: transaction {} closed contract {}", tx.getHash(), multisigContract.getHash());
                        // Record the fact that it was closed along with the transaction that closed it.
                        state = State.CLOSED;
                        if (storedChannel == null) return;
                        storedChannel.close = tx;
                        updateChannelInWallet();
                        watchCloseConfirmations();
                    }
                }
            }
        }, Threading.SAME_THREAD);
    }

    private void watchCloseConfirmations() {
        // When we see the close transaction get enough confirmations, we can just delete the record
        // of this channel along with the refund tx from the wallet, because we're not going to need
        // any of that any more.
        final TransactionConfidence confidence = storedChannel.close.getConfidence();
        int numConfirms = Context.get().getEventHorizon();
        ListenableFuture<TransactionConfidence> future = confidence.getDepthFuture(numConfirms, Threading.SAME_THREAD);
        Futures.addCallback(future, new FutureCallback<TransactionConfidence>() {
            @Override
            public void onSuccess(TransactionConfidence result) {
                deleteChannelFromWallet();
            }

            @Override
            public void onFailure(Throwable t) {
                Throwables.propagate(t);
            }
        });
    }

    private synchronized void deleteChannelFromWallet() {
        log.info("Close tx has confirmed, deleting channel from wallet: {}", storedChannel);
        StoredPaymentChannelClientStates channels = (StoredPaymentChannelClientStates)
                wallet.getExtensions().get(StoredPaymentChannelClientStates.EXTENSION_ID);
        channels.removeChannel(storedChannel);
        wallet.addOrUpdateExtension(channels);
        storedChannel = null;
    }

    /**
     * This object implements a state machine, and this accessor returns which state it's currently in.
     */
    public synchronized State getState() {
        return state;
    }

    /**
     * Creates the initial multisig contract and incomplete refund transaction which can be requested at the appropriate
     * time using {@link PaymentChannelClientState#getIncompleteRefundTransaction} and
     * {@link PaymentChannelClientState#getMultisigContract()}. The way the contract is crafted can be adjusted by
     * overriding {@link PaymentChannelClientState#editContractSendRequest(org.bitcoinj.core.Wallet.SendRequest)}.
     * By default unconfirmed coins are allowed to be used, as for micropayments the risk should be relatively low.
     *
     * @throws ValueOutOfRangeException if the value being used is too small to be accepted by the network
     * @throws InsufficientMoneyException if the wallet doesn't contain enough balance to initiate
     */
    public void initiate() throws ValueOutOfRangeException, InsufficientMoneyException {
        initiate(null);
    }

    /**
     * Creates the initial multisig contract and incomplete refund transaction which can be requested at the appropriate
     * time using {@link PaymentChannelClientState#getIncompleteRefundTransaction} and
     * {@link PaymentChannelClientState#getMultisigContract()}. The way the contract is crafted can be adjusted by
     * overriding {@link PaymentChannelClientState#editContractSendRequest(org.bitcoinj.core.Wallet.SendRequest)}.
     * By default unconfirmed coins are allowed to be used, as for micropayments the risk should be relatively low.
     * @param userKey Key derived from a user password, needed for any signing when the wallet is encrypted.
     *                  The wallet KeyCrypter is assumed.
     *
     * @throws ValueOutOfRangeException   if the value being used is too small to be accepted by the network
     * @throws InsufficientMoneyException if the wallet doesn't contain enough balance to initiate
     */
    public synchronized void initiate(@Nullable KeyParameter userKey) throws ValueOutOfRangeException, InsufficientMoneyException {
        final NetworkParameters params = wallet.getParams();
        Transaction template = new Transaction(params);
        // We always place the client key before the server key because, if either side wants some privacy, they can
        // use a fresh key for the the multisig contract and nowhere else
        List<ECKey> keys = Lists.newArrayList(myKey, serverMultisigKey);
        // There is also probably a change output, but we don't bother shuffling them as it's obvious from the
        // format which one is the change. If we start obfuscating the change output better in future this may
        // be worth revisiting.
        TransactionOutput multisigOutput = template.addOutput(totalValue, ScriptBuilder.createMultiSigOutputScript(2, keys));
        if (multisigOutput.getMinNonDustValue().compareTo(totalValue) > 0)
            throw new ValueOutOfRangeException("totalValue too small to use");
        Wallet.SendRequest req = Wallet.SendRequest.forTx(template);
        req.coinSelector = AllowUnconfirmedCoinSelector.get();
        editContractSendRequest(req);
        req.shuffleOutputs = false;   // TODO: Fix things so shuffling is usable.
        req.aesKey = userKey;
        wallet.completeTx(req);
        Coin multisigFee = req.tx.getFee();
        multisigContract = req.tx;
        // Build a refund transaction that protects us in the case of a bad server that's just trying to cause havoc
        // by locking up peoples money (perhaps as a precursor to a ransom attempt). We time lock it so the server
        // has an assurance that we cannot take back our money by claiming a refund before the channel closes - this
        // relies on the fact that since Bitcoin 0.8 time locked transactions are non-final. This will need to change
        // in future as it breaks the intended design of timelocking/tx replacement, but for now it simplifies this
        // specific protocol somewhat.
        refundTx = new Transaction(params);
        refundTx.addInput(multisigOutput).setSequenceNumber(0);   // Allow replacement when it's eventually reactivated.
        refundTx.setLockTime(expiryTime);
        if (totalValue.compareTo(Coin.CENT) < 0) {
            // Must pay min fee.
            final Coin valueAfterFee = totalValue.subtract(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE);
            if (Transaction.MIN_NONDUST_OUTPUT.compareTo(valueAfterFee) > 0)
                throw new ValueOutOfRangeException("totalValue too small to use");
            refundTx.addOutput(valueAfterFee, myKey.toAddress(params));
            refundFees = multisigFee.add(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE);
        } else {
            refundTx.addOutput(totalValue, myKey.toAddress(params));
            refundFees = multisigFee;
        }
        refundTx.getConfidence().setSource(TransactionConfidence.Source.SELF);
        log.info("initiated channel with multi-sig contract {}, refund {}", multisigContract.getHashAsString(),
                refundTx.getHashAsString());
        state = State.INITIATED;
        // Client should now call getIncompleteRefundTransaction() and send it to the server.
    }

    /**
     * You can override this method in order to control the construction of the initial contract that creates the
     * channel. For example if you want it to only use specific coins, you can adjust the coin selector here.
     * The default implementation does nothing.
     */
    protected void editContractSendRequest(Wallet.SendRequest req) {
    }

    /**
     * Returns the transaction that locks the money to the agreement of both parties. Do not mutate the result.
     * Once this step is done, you can use {@link PaymentChannelClientState#incrementPaymentBy(Coin, KeyParameter)} to
     * start paying the server.
     */
    public synchronized Transaction getMultisigContract() {
        checkState(multisigContract != null);
        if (state == State.PROVIDE_MULTISIG_CONTRACT_TO_SERVER)
            state = State.READY;
        return multisigContract;
    }

    /**
     * Returns a partially signed (invalid) refund transaction that should be passed to the server. Once the server
     * has checked it out and provided its own signature, call
     * {@link PaymentChannelClientState#provideRefundSignature(byte[], KeyParameter)} with the result.
     */
    public synchronized Transaction getIncompleteRefundTransaction() {
        checkState(refundTx != null);
        if (state == State.INITIATED)
            state = State.WAITING_FOR_SIGNED_REFUND;
        return refundTx;
    }

    /**
     * <p>When the servers signature for the refund transaction is received, call this to verify it and sign the
     * complete refund ourselves.</p>
     *
     * <p>If this does not throw an exception, we are secure against the loss of funds and can safely provide the server
     * with the multi-sig contract to lock in the agreement. In this case, both the multisig contract and the refund
     * transaction are automatically committed to wallet so that it can handle broadcasting the refund transaction at
     * the appropriate time if necessary.</p>
     */
    public synchronized void provideRefundSignature(byte[] theirSignature, @Nullable KeyParameter userKey)
            throws VerificationException {
        checkNotNull(theirSignature);
        checkState(state == State.WAITING_FOR_SIGNED_REFUND);
        TransactionSignature theirSig = TransactionSignature.decodeFromBitcoin(theirSignature, true);
        if (theirSig.sigHashMode() != Transaction.SigHash.NONE || !theirSig.anyoneCanPay())
            throw new VerificationException("Refund signature was not SIGHASH_NONE|SIGHASH_ANYONECANPAY");
        // Sign the refund transaction ourselves.
        final TransactionOutput multisigContractOutput = multisigContract.getOutput(0);
        try {
            multisigScript = multisigContractOutput.getScriptPubKey();
        } catch (ScriptException e) {
            throw new RuntimeException(e);  // Cannot happen: we built this ourselves.
        }
        TransactionSignature ourSignature =
                refundTx.calculateSignature(0, myKey.maybeDecrypt(userKey),
                        multisigScript, Transaction.SigHash.ALL, false);
        // Insert the signatures.
        Script scriptSig = ScriptBuilder.createMultiSigInputScript(ourSignature, theirSig);
        log.info("Refund scriptSig: {}", scriptSig);
        log.info("Multi-sig contract scriptPubKey: {}", multisigScript);
        TransactionInput refundInput = refundTx.getInput(0);
        refundInput.setScriptSig(scriptSig);
        refundInput.verify(multisigContractOutput);
        state = State.SAVE_STATE_IN_WALLET;
    }

    private synchronized Transaction makeUnsignedChannelContract(Coin valueToMe) throws ValueOutOfRangeException {
        Transaction tx = new Transaction(wallet.getParams());
        tx.addInput(multisigContract.getOutput(0));
        // Our output always comes first.
        // TODO: We should drop myKey in favor of output key + multisig key separation
        // (as its always obvious who the client is based on T2 output order)
        tx.addOutput(valueToMe, myKey.toAddress(wallet.getParams()));
        return tx;
    }

    /**
     * Checks if the channel is expired, setting state to {@link State#EXPIRED}, removing this channel from wallet
     * storage and throwing an {@link IllegalStateException} if it is.
     */
    public synchronized void checkNotExpired() {
        if (Utils.currentTimeSeconds() > expiryTime) {
            state = State.EXPIRED;
            disconnectFromChannel();
            throw new IllegalStateException("Channel expired");
        }
    }

    /** Container for a signature and an amount that was sent. */
    public static class IncrementedPayment {
        public TransactionSignature signature;
        public Coin amount;
    }

    /**
     * <p>Updates the outputs on the payment contract transaction and re-signs it. The state must be READY in order to
     * call this method. The signature that is returned should be sent to the server so it has the ability to broadcast
     * the best seen payment when the channel closes or times out.</p>
     *
     * <p>The returned signature is over the payment transaction, which we never have a valid copy of and thus there
     * is no accessor for it on this object.</p>
     *
     * <p>To spend the whole channel increment by {@link PaymentChannelClientState#getTotalValue()} -
     * {@link PaymentChannelClientState#getValueRefunded()}</p>
     *
     * @param size How many satoshis to increment the payment by (note: not the new total).
     * @throws ValueOutOfRangeException If size is negative or the channel does not have sufficient money in it to
     *                                  complete this payment.
     */
    public synchronized IncrementedPayment incrementPaymentBy(Coin size, @Nullable KeyParameter userKey)
            throws ValueOutOfRangeException {
        checkState(state == State.READY);
        checkNotExpired();
        checkNotNull(size);  // Validity of size will be checked by makeUnsignedChannelContract.
        if (size.signum() < 0)
            throw new ValueOutOfRangeException("Tried to decrement payment");
        Coin newValueToMe = valueToMe.subtract(size);
        if (newValueToMe.compareTo(Transaction.MIN_NONDUST_OUTPUT) < 0 && newValueToMe.signum() > 0) {
            log.info("New value being sent back as change was smaller than minimum nondust output, sending all");
            size = valueToMe;
            newValueToMe = Coin.ZERO;
        }
        if (newValueToMe.signum() < 0)
            throw new ValueOutOfRangeException("Channel has too little money to pay " + size + " satoshis");
        Transaction tx = makeUnsignedChannelContract(newValueToMe);
        log.info("Signing new payment tx {}", tx);
        Transaction.SigHash mode;
        // If we spent all the money we put into this channel, we (by definition) don't care what the outputs are, so
        // we sign with SIGHASH_NONE to let the server do what it wants.
        if (newValueToMe.equals(Coin.ZERO))
            mode = Transaction.SigHash.NONE;
        else
            mode = Transaction.SigHash.SINGLE;
        TransactionSignature sig = tx.calculateSignature(0, myKey.maybeDecrypt(userKey), multisigScript, mode, true);
        valueToMe = newValueToMe;
        updateChannelInWallet();
        IncrementedPayment payment = new IncrementedPayment();
        payment.signature = sig;
        payment.amount = size;
        return payment;
    }

    private synchronized void updateChannelInWallet() {
        if (storedChannel == null)
            return;
        storedChannel.valueToMe = valueToMe;
        StoredPaymentChannelClientStates channels = (StoredPaymentChannelClientStates)
                wallet.getExtensions().get(StoredPaymentChannelClientStates.EXTENSION_ID);
        wallet.addOrUpdateExtension(channels);
    }

    /**
     * Sets this channel's state in {@link StoredPaymentChannelClientStates} to unopened so this channel can be reopened
     * later.
     *
     * @see PaymentChannelClientState#storeChannelInWallet(Sha256Hash)
     */
    public synchronized void disconnectFromChannel() {
        if (storedChannel == null)
            return;
        synchronized (storedChannel) {
            storedChannel.active = false;
        }
    }

    /**
     * Skips saving state in the wallet for testing
     */
    @VisibleForTesting synchronized void fakeSave() {
        try {
            wallet.commitTx(multisigContract);
        } catch (VerificationException e) {
            throw new RuntimeException(e); // We created it
        }
        state = State.PROVIDE_MULTISIG_CONTRACT_TO_SERVER;
    }

    @VisibleForTesting synchronized void doStoreChannelInWallet(Sha256Hash id) {
        StoredPaymentChannelClientStates channels = (StoredPaymentChannelClientStates)
                wallet.getExtensions().get(StoredPaymentChannelClientStates.EXTENSION_ID);
        checkNotNull(channels, "You have not added the StoredPaymentChannelClientStates extension to the wallet.");
        checkState(channels.getChannel(id, multisigContract.getHash()) == null);
        storedChannel = new StoredClientChannel(id, multisigContract, refundTx, myKey, valueToMe, refundFees, true);
        channels.putChannel(storedChannel);
        wallet.addOrUpdateExtension(channels);
    }

    /**
     * <p>Stores this channel's state in the wallet as a part of a {@link StoredPaymentChannelClientStates} wallet
     * extension and keeps it up-to-date each time payment is incremented. This allows the
     * {@link StoredPaymentChannelClientStates} object to keep track of timeouts and broadcast the refund transaction
     * when the channel expires.</p>
     *
     * <p>A channel may only be stored after it has fully opened (ie state == State.READY). The wallet provided in the
     * constructor must already have a {@link StoredPaymentChannelClientStates} object in its extensions set.</p>
     *
     * @param id A hash providing this channel with an id which uniquely identifies this server. It does not have to be
     *           unique.
     */
    public synchronized void storeChannelInWallet(Sha256Hash id) {
        checkState(state == State.SAVE_STATE_IN_WALLET && id != null);
        if (storedChannel != null) {
            checkState(storedChannel.id.equals(id));
            return;
        }
        doStoreChannelInWallet(id);

        try {
            wallet.commitTx(multisigContract);
        } catch (VerificationException e) {
            throw new RuntimeException(e); // We created it
        }
        state = State.PROVIDE_MULTISIG_CONTRACT_TO_SERVER;
    }

    /**
     * Returns the fees that will be paid if the refund transaction has to be claimed because the server failed to settle
     * the channel properly. May only be called after {@link PaymentChannelClientState#initiate()}
     */
    public synchronized Coin getRefundTxFees() {
        checkState(state.compareTo(State.NEW) > 0);
        return refundFees;
    }

    /**
     * Once the servers signature over the refund transaction has been received and provided using
     * {@link PaymentChannelClientState#provideRefundSignature(byte[], KeyParameter)} then this
     * method can be called to receive the now valid and broadcastable refund transaction.
     */
    public synchronized Transaction getCompletedRefundTransaction() {
        checkState(state.compareTo(State.WAITING_FOR_SIGNED_REFUND) > 0);
        return refundTx;
    }

    /**
     * Gets the total value of this channel (ie the maximum payment possible)
     */
    public Coin getTotalValue() {
        return totalValue;
    }

    /**
     * Gets the current amount refunded to us from the multisig contract (ie totalValue-valueSentToServer)
     */
    public synchronized Coin getValueRefunded() {
        checkState(state == State.READY);
        return valueToMe;
    }

    /**
     * Returns the amount of money sent on this channel so far.
     */
    public synchronized Coin getValueSpent() {
        return getTotalValue().subtract(getValueRefunded());
    }
}


File: core/src/main/java/org/bitcoinj/protocols/channels/PaymentChannelServerState.java
/*
 * Copyright 2013 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.protocols.channels;

import org.bitcoinj.core.*;
import org.bitcoinj.crypto.TransactionSignature;
import org.bitcoinj.script.Script;
import org.bitcoinj.script.ScriptBuilder;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import com.google.common.util.concurrent.FutureCallback;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.SettableFuture;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Nullable;
import java.util.Arrays;

import static com.google.common.base.Preconditions.*;

/**
 * <p>A payment channel is a method of sending money to someone such that the amount of money you send can be adjusted
 * after the fact, in an efficient manner that does not require broadcasting to the network. This can be used to
 * implement micropayments or other payment schemes in which immediate settlement is not required, but zero trust
 * negotiation is. Note that this class only allows the amount of money received to be incremented, not decremented.</p>
 *
 * <p>This class implements the core state machine for the server side of the protocol. The client side is implemented
 * by {@link PaymentChannelClientState} and {@link PaymentChannelServerListener} implements the server-side network
 * protocol listening for TCP/IP connections and moving this class through each state. We say that the party who is
 * sending funds is the <i>client</i> or <i>initiating party</i>. The party that is receiving the funds is the
 * <i>server</i> or <i>receiving party</i>. Although the underlying Bitcoin protocol is capable of more complex
 * relationships than that, this class implements only the simplest case.</p>
 *
 * <p>To protect clients from malicious servers, a channel has an expiry parameter. When this expiration is reached, the
 * client will broadcast the created refund  transaction and take back all the money in this channel. Because this is
 * specified in terms of block timestamps, it is fairly fuzzy and it is possible to spend the refund transaction up to a
 * few hours before the actual timestamp. Thus, it is very important that the channel be closed with plenty of time left
 * to get the highest value payment transaction confirmed before the expire time (minimum 3-4 hours is suggested if the
 * payment transaction has enough fee to be confirmed in the next block or two).</p>
 *
 * <p>To begin, we must provide the client with a pubkey which we wish to use for the multi-sig contract which locks in
 * the channel. The client will then provide us with an incomplete refund transaction and the pubkey which they used in
 * the multi-sig contract. We use this pubkey to recreate the multi-sig output and then sign that to the refund
 * transaction. We provide that signature to the client and they then have the ability to spend the refund transaction
 * at the specified expire time. The client then provides us with the full, signed multi-sig contract which we verify
 * and broadcast, locking in their funds until we spend a payment transaction or the expire time is reached. The client
 * can then begin paying by providing us with signatures for the multi-sig contract which pay some amount back to the
 * client, and the rest is ours to do with as we wish.</p>
 */
public class PaymentChannelServerState {
    private static final Logger log = LoggerFactory.getLogger(PaymentChannelServerState.class);

    /**
     * The different logical states the channel can be in. Because the first action we need to track is the client
     * providing the refund transaction, we begin in WAITING_FOR_REFUND_TRANSACTION. We then step through the states
     * until READY, at which time the client can increase payment incrementally.
     */
    public enum State {
        WAITING_FOR_REFUND_TRANSACTION,
        WAITING_FOR_MULTISIG_CONTRACT,
        WAITING_FOR_MULTISIG_ACCEPTANCE,
        READY,
        CLOSING,
        CLOSED,
        ERROR,
    }
    private State state;

    // The client and server keys for the multi-sig contract
    // We currently also use the serverKey for payouts, but this is not required
    private ECKey clientKey, serverKey;

    // Package-local for checkArguments in StoredServerChannel
    final Wallet wallet;

    // The object that will broadcast transactions for us - usually a peer group.
    private final TransactionBroadcaster broadcaster;

    // The multi-sig contract and the output script from it
    private Transaction multisigContract = null;
    private Script multisigScript;

    // The last signature the client provided for a payment transaction.
    private byte[] bestValueSignature;

    // The total value locked into the multi-sig output and the value to us in the last signature the client provided
    private Coin totalValue;
    private Coin bestValueToMe = Coin.ZERO;
    private Coin feePaidForPayment;

    // The refund/change transaction output that goes back to the client
    private TransactionOutput clientOutput;
    private long refundTransactionUnlockTimeSecs;

    private long minExpireTime;

    private StoredServerChannel storedServerChannel = null;

    PaymentChannelServerState(StoredServerChannel storedServerChannel, Wallet wallet, TransactionBroadcaster broadcaster) throws VerificationException {
        synchronized (storedServerChannel) {
            this.wallet = checkNotNull(wallet);
            this.broadcaster = checkNotNull(broadcaster);
            this.multisigContract = checkNotNull(storedServerChannel.contract);
            this.multisigScript = multisigContract.getOutput(0).getScriptPubKey();
            this.clientKey = ECKey.fromPublicOnly(multisigScript.getChunks().get(1).data);
            this.clientOutput = checkNotNull(storedServerChannel.clientOutput);
            this.refundTransactionUnlockTimeSecs = storedServerChannel.refundTransactionUnlockTimeSecs;
            this.serverKey = checkNotNull(storedServerChannel.myKey);
            this.totalValue = multisigContract.getOutput(0).getValue();
            this.bestValueToMe = checkNotNull(storedServerChannel.bestValueToMe);
            this.bestValueSignature = storedServerChannel.bestValueSignature;
            checkArgument(bestValueToMe.equals(Coin.ZERO) || bestValueSignature != null);
            this.storedServerChannel = storedServerChannel;
            storedServerChannel.state = this;
            this.state = State.READY;
        }
    }

    /**
     * Creates a new state object to track the server side of a payment channel.
     *
     * @param broadcaster The peer group which we will broadcast transactions to, this should have multiple peers
     * @param wallet The wallet which will be used to complete transactions
     * @param serverKey The private key which we use for our part of the multi-sig contract
     *                  (this MUST be fresh and CANNOT be used elsewhere)
     * @param minExpireTime The earliest time at which the client can claim the refund transaction (UNIX timestamp of block)
     */
    public PaymentChannelServerState(TransactionBroadcaster broadcaster, Wallet wallet, ECKey serverKey, long minExpireTime) {
        this.state = State.WAITING_FOR_REFUND_TRANSACTION;
        this.serverKey = checkNotNull(serverKey);
        this.wallet = checkNotNull(wallet);
        this.broadcaster = checkNotNull(broadcaster);
        this.minExpireTime = minExpireTime;
    }

    /**
     * This object implements a state machine, and this accessor returns which state it's currently in.
     */
    public synchronized State getState() {
        return state;
    }

    /**
     * Called when the client provides the refund transaction.
     * The refund transaction must have one input from the multisig contract (that we don't have yet) and one output
     * that the client creates to themselves. This object will later be modified when we start getting paid.
     *
     * @param refundTx The refund transaction, this object will be mutated when payment is incremented.
     * @param clientMultiSigPubKey The client's pubkey which is required for the multisig output
     * @return Our signature that makes the refund transaction valid
     * @throws VerificationException If the transaction isnt valid or did not meet the requirements of a refund transaction.
     */
    public synchronized byte[] provideRefundTransaction(Transaction refundTx, byte[] clientMultiSigPubKey) throws VerificationException {
        checkNotNull(refundTx);
        checkNotNull(clientMultiSigPubKey);
        checkState(state == State.WAITING_FOR_REFUND_TRANSACTION);
        log.info("Provided with refund transaction: {}", refundTx);
        // Do a few very basic syntax sanity checks.
        refundTx.verify();
        // Verify that the refund transaction has a single input (that we can fill to sign the multisig output).
        if (refundTx.getInputs().size() != 1)
            throw new VerificationException("Refund transaction does not have exactly one input");
        // Verify that the refund transaction has a time lock on it and a sequence number of zero.
        if (refundTx.getInput(0).getSequenceNumber() != 0)
            throw new VerificationException("Refund transaction's input's sequence number is non-0");
        if (refundTx.getLockTime() < minExpireTime)
            throw new VerificationException("Refund transaction has a lock time too soon");
        // Verify the transaction has one output (we don't care about its contents, its up to the client)
        // Note that because we sign with SIGHASH_NONE|SIGHASH_ANYOENCANPAY the client can later add more outputs and
        // inputs, but we will need only one output later to create the paying transactions
        if (refundTx.getOutputs().size() != 1)
            throw new VerificationException("Refund transaction does not have exactly one output");

        refundTransactionUnlockTimeSecs = refundTx.getLockTime();

        // Sign the refund tx with the scriptPubKey and return the signature. We don't have the spending transaction
        // so do the steps individually.
        clientKey = ECKey.fromPublicOnly(clientMultiSigPubKey);
        Script multisigPubKey = ScriptBuilder.createMultiSigOutputScript(2, ImmutableList.of(clientKey, serverKey));
        // We are really only signing the fact that the transaction has a proper lock time and don't care about anything
        // else, so we sign SIGHASH_NONE and SIGHASH_ANYONECANPAY.
        TransactionSignature sig = refundTx.calculateSignature(0, serverKey, multisigPubKey, Transaction.SigHash.NONE, true);
        log.info("Signed refund transaction.");
        this.clientOutput = refundTx.getOutput(0);
        state = State.WAITING_FOR_MULTISIG_CONTRACT;
        return sig.encodeToBitcoin();
    }

    /**
     * Called when the client provides the multi-sig contract.  Checks that the previously-provided refund transaction
     * spends this transaction (because we will use it as a base to create payment transactions) as well as output value
     * and form (ie it is a 2-of-2 multisig to the correct keys).
     *
     * @param multisigContract The provided multisig contract. Do not mutate this object after this call.
     * @return A future which completes when the provided multisig contract successfully broadcasts, or throws if the broadcast fails for some reason
     *         Note that if the network simply rejects the transaction, this future will never complete, a timeout should be used.
     * @throws VerificationException If the provided multisig contract is not well-formed or does not meet previously-specified parameters
     */
    public synchronized ListenableFuture<PaymentChannelServerState> provideMultiSigContract(final Transaction multisigContract) throws VerificationException {
        checkNotNull(multisigContract);
        checkState(state == State.WAITING_FOR_MULTISIG_CONTRACT);
        try {
            multisigContract.verify();
            this.multisigContract = multisigContract;
            this.multisigScript = multisigContract.getOutput(0).getScriptPubKey();

            // Check that multisigContract's first output is a 2-of-2 multisig to the correct pubkeys in the correct order
            final Script expectedScript = ScriptBuilder.createMultiSigOutputScript(2, Lists.newArrayList(clientKey, serverKey));
            if (!Arrays.equals(multisigScript.getProgram(), expectedScript.getProgram()))
                throw new VerificationException("Multisig contract's first output was not a standard 2-of-2 multisig to client and server in that order.");

            this.totalValue = multisigContract.getOutput(0).getValue();
            if (this.totalValue.signum() <= 0)
                throw new VerificationException("Not accepting an attempt to open a contract with zero value.");
        } catch (VerificationException e) {
            // We couldn't parse the multisig transaction or its output.
            log.error("Provided multisig contract did not verify: {}", multisigContract.toString());
            throw e;
        }
        log.info("Broadcasting multisig contract: {}", multisigContract);
        state = State.WAITING_FOR_MULTISIG_ACCEPTANCE;
        final SettableFuture<PaymentChannelServerState> future = SettableFuture.create();
        Futures.addCallback(broadcaster.broadcastTransaction(multisigContract).future(), new FutureCallback<Transaction>() {
            @Override public void onSuccess(Transaction transaction) {
                log.info("Successfully broadcast multisig contract {}. Channel now open.", transaction.getHashAsString());
                try {
                    // Manually add the multisigContract to the wallet, overriding the isRelevant checks so we can track
                    // it and check for double-spends later
                    wallet.receivePending(multisigContract, null, true);
                } catch (VerificationException e) {
                    throw new RuntimeException(e); // Cannot happen, we already called multisigContract.verify()
                }
                state = State.READY;
                future.set(PaymentChannelServerState.this);
            }

            @Override public void onFailure(Throwable throwable) {
                // Couldn't broadcast the transaction for some reason.
                log.error(throwable.toString());
                throwable.printStackTrace();
                state = State.ERROR;
                future.setException(throwable);
            }
        });
        return future;
    }

    // Create a payment transaction with valueToMe going back to us
    private synchronized Wallet.SendRequest makeUnsignedChannelContract(Coin valueToMe) {
        Transaction tx = new Transaction(wallet.getParams());
        if (!totalValue.subtract(valueToMe).equals(Coin.ZERO)) {
            clientOutput.setValue(totalValue.subtract(valueToMe));
            tx.addOutput(clientOutput);
        }
        tx.addInput(multisigContract.getOutput(0));
        return Wallet.SendRequest.forTx(tx);
    }

    /**
     * Called when the client provides us with a new signature and wishes to increment total payment by size.
     * Verifies the provided signature and only updates values if everything checks out.
     * If the new refundSize is not the lowest we have seen, it is simply ignored.
     *
     * @param refundSize How many satoshis of the original contract are refunded to the client (the rest are ours)
     * @param signatureBytes The new signature spending the multi-sig contract to a new payment transaction
     * @throws VerificationException If the signature does not verify or size is out of range (incl being rejected by the network as dust).
     * @return true if there is more value left on the channel, false if it is now fully used up.
     */
    public synchronized boolean incrementPayment(Coin refundSize, byte[] signatureBytes) throws VerificationException, ValueOutOfRangeException, InsufficientMoneyException {
        checkState(state == State.READY);
        checkNotNull(refundSize);
        checkNotNull(signatureBytes);
        TransactionSignature signature = TransactionSignature.decodeFromBitcoin(signatureBytes, true);
        // We allow snapping to zero for the payment amount because it's treated specially later, but not less than
        // the dust level because that would prevent the transaction from being relayed/mined.
        final boolean fullyUsedUp = refundSize.equals(Coin.ZERO);
        if (refundSize.compareTo(clientOutput.getMinNonDustValue()) < 0 && !fullyUsedUp)
            throw new ValueOutOfRangeException("Attempt to refund negative value or value too small to be accepted by the network");
        Coin newValueToMe = totalValue.subtract(refundSize);
        if (newValueToMe.signum() < 0)
            throw new ValueOutOfRangeException("Attempt to refund more than the contract allows.");
        if (newValueToMe.compareTo(bestValueToMe) < 0)
            throw new ValueOutOfRangeException("Attempt to roll back payment on the channel.");

        // Get the wallet's copy of the multisigContract (ie with confidence information), if this is null, the wallet
        // was not connected to the peergroup when the contract was broadcast (which may cause issues down the road, and
        // disables our double-spend check next)
        Transaction walletContract = wallet.getTransaction(multisigContract.getHash());
        checkNotNull(walletContract, "Wallet did not contain multisig contract {} after state was marked READY", multisigContract.getHash());

        // Note that we check for DEAD state here, but this test is essentially useless in production because we will
        // miss most double-spends due to bloom filtering right now anyway. This will eventually fixed by network-wide
        // double-spend notifications, so we just wait instead of attempting to add all dependant outpoints to our bloom
        // filters (and probably missing lots of edge-cases).
        if (walletContract.getConfidence().getConfidenceType() == TransactionConfidence.ConfidenceType.DEAD) {
            close();
            throw new VerificationException("Multisig contract was double-spent");
        }

        Transaction.SigHash mode;
        // If the client doesn't want anything back, they shouldn't sign any outputs at all.
        if (fullyUsedUp)
            mode = Transaction.SigHash.NONE;
        else
            mode = Transaction.SigHash.SINGLE;

        if (signature.sigHashMode() != mode || !signature.anyoneCanPay())
            throw new VerificationException("New payment signature was not signed with the right SIGHASH flags.");

        Wallet.SendRequest req = makeUnsignedChannelContract(newValueToMe);
        // Now check the signature is correct.
        // Note that the client must sign with SIGHASH_{SINGLE/NONE} | SIGHASH_ANYONECANPAY to allow us to add additional
        // inputs (in case we need to add significant fee, or something...) and any outputs we want to pay to.
        Sha256Hash sighash = req.tx.hashForSignature(0, multisigScript, mode, true);

        if (!clientKey.verify(sighash, signature))
            throw new VerificationException("Signature does not verify on tx\n" + req.tx);
        bestValueToMe = newValueToMe;
        bestValueSignature = signatureBytes;
        updateChannelInWallet();
        return !fullyUsedUp;
    }

    // Signs the first input of the transaction which must spend the multisig contract.
    private void signMultisigInput(Transaction tx, Transaction.SigHash hashType, boolean anyoneCanPay) {
        TransactionSignature signature = tx.calculateSignature(0, serverKey, multisigScript, hashType, anyoneCanPay);
        byte[] mySig = signature.encodeToBitcoin();
        Script scriptSig = ScriptBuilder.createMultiSigInputScriptBytes(ImmutableList.of(bestValueSignature, mySig));
        tx.getInput(0).setScriptSig(scriptSig);
    }

    final SettableFuture<Transaction> closedFuture = SettableFuture.create();
    /**
     * <p>Closes this channel and broadcasts the highest value payment transaction on the network.</p>
     *
     * <p>This will set the state to {@link State#CLOSED} if the transaction is successfully broadcast on the network.
     * If we fail to broadcast for some reason, the state is set to {@link State#ERROR}.</p>
     *
     * <p>If the current state is before {@link State#READY} (ie we have not finished initializing the channel), we
     * simply set the state to {@link State#CLOSED} and let the client handle getting its refund transaction confirmed.
     * </p>
     *
     * @return a future which completes when the provided multisig contract successfully broadcasts, or throws if the
     *         broadcast fails for some reason. Note that if the network simply rejects the transaction, this future
     *         will never complete, a timeout should be used.
     * @throws InsufficientMoneyException If the payment tx would have cost more in fees to spend than it is worth.
     */
    public synchronized ListenableFuture<Transaction> close() throws InsufficientMoneyException {
        if (storedServerChannel != null) {
            StoredServerChannel temp = storedServerChannel;
            storedServerChannel = null;
            StoredPaymentChannelServerStates channels = (StoredPaymentChannelServerStates)
                    wallet.getExtensions().get(StoredPaymentChannelServerStates.EXTENSION_ID);
            channels.closeChannel(temp); // May call this method again for us (if it wasn't the original caller)
            if (state.compareTo(State.CLOSING) >= 0)
                return closedFuture;
        }

        if (state.ordinal() < State.READY.ordinal()) {
            log.error("Attempt to settle channel in state " + state);
            state = State.CLOSED;
            closedFuture.set(null);
            return closedFuture;
        }
        if (state != State.READY) {
            // TODO: What is this codepath for?
            log.warn("Failed attempt to settle a channel in state " + state);
            return closedFuture;
        }
        Transaction tx = null;
        try {
            Wallet.SendRequest req = makeUnsignedChannelContract(bestValueToMe);
            tx = req.tx;
            // Provide a throwaway signature so that completeTx won't complain out about unsigned inputs it doesn't
            // know how to sign. Note that this signature does actually have to be valid, so we can't use a dummy
            // signature to save time, because otherwise completeTx will try to re-sign it to make it valid and then
            // die. We could probably add features to the SendRequest API to make this a bit more efficient.
            signMultisigInput(tx, Transaction.SigHash.NONE, true);
            // Let wallet handle adding additional inputs/fee as necessary.
            req.shuffleOutputs = false;
            req.missingSigsMode = Wallet.MissingSigsMode.USE_DUMMY_SIG;
            wallet.completeTx(req);  // TODO: Fix things so shuffling is usable.
            feePaidForPayment = req.tx.getFee();
            log.info("Calculated fee is {}", feePaidForPayment);
            if (feePaidForPayment.compareTo(bestValueToMe) >= 0) {
                final String msg = String.format("Had to pay more in fees (%s) than the channel was worth (%s)",
                        feePaidForPayment, bestValueToMe);
                throw new InsufficientMoneyException(feePaidForPayment.subtract(bestValueToMe), msg);
            }
            // Now really sign the multisig input.
            signMultisigInput(tx, Transaction.SigHash.ALL, false);
            // Some checks that shouldn't be necessary but it can't hurt to check.
            tx.verify();  // Sanity check syntax.
            for (TransactionInput input : tx.getInputs())
                input.verify();  // Run scripts and ensure it is valid.
        } catch (InsufficientMoneyException e) {
            throw e;  // Don't fall through.
        } catch (Exception e) {
            log.error("Could not verify self-built tx\nMULTISIG {}\nCLOSE {}", multisigContract, tx != null ? tx : "");
            throw new RuntimeException(e);  // Should never happen.
        }
        state = State.CLOSING;
        log.info("Closing channel, broadcasting tx {}", tx);
        // The act of broadcasting the transaction will add it to the wallet.
        ListenableFuture<Transaction> future = broadcaster.broadcastTransaction(tx).future();
        Futures.addCallback(future, new FutureCallback<Transaction>() {
            @Override public void onSuccess(Transaction transaction) {
                log.info("TX {} propagated, channel successfully closed.", transaction.getHash());
                state = State.CLOSED;
                closedFuture.set(transaction);
            }

            @Override public void onFailure(Throwable throwable) {
                log.error("Failed to settle channel, could not broadcast: {}", throwable.toString());
                throwable.printStackTrace();
                state = State.ERROR;
                closedFuture.setException(throwable);
            }
        });
        return closedFuture;
    }

    /**
     * Gets the highest payment to ourselves (which we will receive on settle(), not including fees)
     */
    public synchronized Coin getBestValueToMe() {
        return bestValueToMe;
    }

    /**
     * Gets the fee paid in the final payment transaction (only available if settle() did not throw an exception)
     */
    public synchronized Coin getFeePaid() {
        checkState(state == State.CLOSED || state == State.CLOSING);
        return feePaidForPayment;
    }

    /**
     * Gets the multisig contract which was used to initialize this channel
     */
    public synchronized Transaction getMultisigContract() {
        checkState(multisigContract != null);
        return multisigContract;
    }

    /**
     * Gets the client's refund transaction which they can spend to get the entire channel value back if it reaches its
     * lock time.
     */
    public synchronized long getRefundTransactionUnlockTime() {
        checkState(state.compareTo(State.WAITING_FOR_MULTISIG_CONTRACT) > 0 && state != State.ERROR);
        return refundTransactionUnlockTimeSecs;
    }

    private synchronized void updateChannelInWallet() {
        if (storedServerChannel != null) {
            storedServerChannel.updateValueToMe(bestValueToMe, bestValueSignature);
            StoredPaymentChannelServerStates channels = (StoredPaymentChannelServerStates)
                    wallet.getExtensions().get(StoredPaymentChannelServerStates.EXTENSION_ID);
            wallet.addOrUpdateExtension(channels);
        }
    }

    /**
     * Stores this channel's state in the wallet as a part of a {@link StoredPaymentChannelServerStates} wallet
     * extension and keeps it up-to-date each time payment is incremented. This will be automatically removed when
     * a call to {@link PaymentChannelServerState#close()} completes successfully. A channel may only be stored after it
     * has fully opened (ie state == State.READY).
     *
     * @param connectedHandler Optional {@link PaymentChannelServer} object that manages this object. This will
     *                         set the appropriate pointer in the newly created {@link StoredServerChannel} before it is
     *                         committed to wallet. If set, closing the state object will propagate the close to the
     *                         handler which can then do a TCP disconnect.
     */
    public synchronized void storeChannelInWallet(@Nullable PaymentChannelServer connectedHandler) {
        checkState(state == State.READY);
        if (storedServerChannel != null)
            return;

        log.info("Storing state with contract hash {}.", multisigContract.getHash());
        StoredPaymentChannelServerStates channels = (StoredPaymentChannelServerStates)
                wallet.addOrGetExistingExtension(new StoredPaymentChannelServerStates(wallet, broadcaster));
        storedServerChannel = new StoredServerChannel(this, multisigContract, clientOutput, refundTransactionUnlockTimeSecs, serverKey, bestValueToMe, bestValueSignature);
        if (connectedHandler != null)
            checkState(storedServerChannel.setConnectedHandler(connectedHandler, false) == connectedHandler);
        channels.putChannel(storedServerChannel);
        wallet.addOrUpdateExtension(channels);
    }
}


File: core/src/main/java/org/bitcoinj/protocols/channels/StoredPaymentChannelClientStates.java
/*
 * Copyright 2013 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.protocols.channels;

import org.bitcoinj.core.*;
import org.bitcoinj.utils.Threading;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.collect.HashMultimap;
import com.google.common.util.concurrent.SettableFuture;
import com.google.protobuf.ByteString;
import net.jcip.annotations.GuardedBy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Nullable;
import java.util.Date;
import java.util.Set;
import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.locks.ReentrantLock;

import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.base.Preconditions.checkState;

/**
 * This class maintains a set of {@link StoredClientChannel}s, automatically (re)broadcasting the contract transaction
 * and broadcasting the refund transaction over the given {@link TransactionBroadcaster}.
 */
public class StoredPaymentChannelClientStates implements WalletExtension {
    private static final Logger log = LoggerFactory.getLogger(StoredPaymentChannelClientStates.class);
    static final String EXTENSION_ID = StoredPaymentChannelClientStates.class.getName();
    static final int MAX_SECONDS_TO_WAIT_FOR_BROADCASTER_TO_BE_SET = 10;

    @GuardedBy("lock") @VisibleForTesting final HashMultimap<Sha256Hash, StoredClientChannel> mapChannels = HashMultimap.create();
    @VisibleForTesting final Timer channelTimeoutHandler = new Timer(true);

    private Wallet containingWallet;
    private final SettableFuture<TransactionBroadcaster> announcePeerGroupFuture = SettableFuture.create();

    protected final ReentrantLock lock = Threading.lock("StoredPaymentChannelClientStates");

    /**
     * Creates a new StoredPaymentChannelClientStates and associates it with the given {@link Wallet} and
     * {@link TransactionBroadcaster} which are used to complete and announce contract and refund
     * transactions.
     */
    public StoredPaymentChannelClientStates(@Nullable Wallet containingWallet, TransactionBroadcaster announcePeerGroup) {
        setTransactionBroadcaster(announcePeerGroup);
        this.containingWallet = containingWallet;
    }

    /**
     * Creates a new StoredPaymentChannelClientStates and associates it with the given {@link Wallet}
     *
     * Use this constructor if you use WalletAppKit, it will provide the broadcaster for you (no need to call the setter)
     */
    public StoredPaymentChannelClientStates(@Nullable Wallet containingWallet) {
        this.containingWallet = containingWallet;
    }

    /**
     * Use this setter if the broadcaster is not available during instantiation and you're not using WalletAppKit.
     * This setter will let you delay the setting of the broadcaster until the Bitcoin network is ready.
     *
     * @param transactionBroadcaster which is used to complete and announce contract and refund transactions.
     */
    public void setTransactionBroadcaster(TransactionBroadcaster transactionBroadcaster) {
        this.announcePeerGroupFuture.set(checkNotNull(transactionBroadcaster));
    }

    /** Returns this extension from the given wallet, or null if no such extension was added. */
    @Nullable
    public static StoredPaymentChannelClientStates getFromWallet(Wallet wallet) {
        return (StoredPaymentChannelClientStates) wallet.getExtensions().get(EXTENSION_ID);
    }

    /** Returns the outstanding amount of money sent back to us for all channels to this server added together. */
    public Coin getBalanceForServer(Sha256Hash id) {
        Coin balance = Coin.ZERO;
        lock.lock();
        try {
            Set<StoredClientChannel> setChannels = mapChannels.get(id);
            for (StoredClientChannel channel : setChannels) {
                synchronized (channel) {
                    if (channel.close != null) continue;
                    balance = balance.add(channel.valueToMe);
                }
            }
            return balance;
        } finally {
            lock.unlock();
        }
    }

    /**
     * Returns the number of seconds from now until this servers next channel will expire, or zero if no unexpired
     * channels found.
     */
    public long getSecondsUntilExpiry(Sha256Hash id) {
        lock.lock();
        try {
            final Set<StoredClientChannel> setChannels = mapChannels.get(id);
            final long nowSeconds = Utils.currentTimeSeconds();
            int earliestTime = Integer.MAX_VALUE;
            for (StoredClientChannel channel : setChannels) {
                synchronized (channel) {
                    if (channel.expiryTimeSeconds() > nowSeconds)
                        earliestTime = Math.min(earliestTime, (int) channel.expiryTimeSeconds());
                }
            }
            return earliestTime == Integer.MAX_VALUE ? 0 : earliestTime - nowSeconds;
        } finally {
            lock.unlock();
        }
    }

    /**
     * Finds an inactive channel with the given id and returns it, or returns null.
     */
    @Nullable
    StoredClientChannel getUsableChannelForServerID(Sha256Hash id) {
        lock.lock();
        try {
            Set<StoredClientChannel> setChannels = mapChannels.get(id);
            for (StoredClientChannel channel : setChannels) {
                synchronized (channel) {
                    // Check if the channel is usable (has money, inactive) and if so, activate it.
                    log.info("Considering channel {} contract {}", channel.hashCode(), channel.contract.getHash());
                    if (channel.close != null || channel.valueToMe.equals(Coin.ZERO)) {
                        log.info("  ... but is closed or empty");
                        continue;
                    }
                    if (!channel.active) {
                        log.info("  ... activating");
                        channel.active = true;
                        return channel;
                    }
                    log.info("  ... but is already active");
                }
            }
        } finally {
            lock.unlock();
        }
        return null;
    }

    /**
     * Finds a channel with the given id and contract hash and returns it, or returns null.
     */
    @Nullable
    StoredClientChannel getChannel(Sha256Hash id, Sha256Hash contractHash) {
        lock.lock();
        try {
            Set<StoredClientChannel> setChannels = mapChannels.get(id);
            for (StoredClientChannel channel : setChannels) {
                if (channel.contract.getHash().equals(contractHash))
                    return channel;
            }
            return null;
        } finally {
            lock.unlock();
        }
    }

    /**
     * Adds the given channel to this set of stored states, broadcasting the contract and refund transactions when the
     * channel expires and notifies the wallet of an update to this wallet extension
     */
    void putChannel(final StoredClientChannel channel) {
        putChannel(channel, true);
    }

    // Adds this channel and optionally notifies the wallet of an update to this extension (used during deserialize)
    private void putChannel(final StoredClientChannel channel, boolean updateWallet) {
        lock.lock();
        try {
            mapChannels.put(channel.id, channel);
            channelTimeoutHandler.schedule(new TimerTask() {
                @Override
                public void run() {
                    TransactionBroadcaster announcePeerGroup = getAnnouncePeerGroup();
                    removeChannel(channel);
                    announcePeerGroup.broadcastTransaction(channel.contract);
                    announcePeerGroup.broadcastTransaction(channel.refund);
                }
                // Add the difference between real time and Utils.now() so that test-cases can use a mock clock.
            }, new Date(channel.expiryTimeSeconds() * 1000 + (System.currentTimeMillis() - Utils.currentTimeMillis())));
        } finally {
            lock.unlock();
        }
        if (updateWallet)
            containingWallet.addOrUpdateExtension(this);
    }

    /**
     * If the peer group has not been set for MAX_SECONDS_TO_WAIT_FOR_BROADCASTER_TO_BE_SET seconds, then
     * the programmer probably forgot to set it and we should throw exception.
     */
    private TransactionBroadcaster getAnnouncePeerGroup() {
        try {
            return announcePeerGroupFuture.get(MAX_SECONDS_TO_WAIT_FOR_BROADCASTER_TO_BE_SET, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        } catch (ExecutionException e) {
            throw new RuntimeException(e);
        } catch (TimeoutException e) {
            String err = "Transaction broadcaster not set";
            log.error(err);
            throw new RuntimeException(err, e);
        }
    }

    /**
     * <p>Removes the channel with the given id from this set of stored states and notifies the wallet of an update to
     * this wallet extension.</p>
     *
     * <p>Note that the channel will still have its contract and refund transactions broadcast via the connected
     * {@link TransactionBroadcaster} as long as this {@link StoredPaymentChannelClientStates} continues to
     * exist in memory.</p>
     */
    void removeChannel(StoredClientChannel channel) {
        lock.lock();
        try {
            mapChannels.remove(channel.id, channel);
        } finally {
            lock.unlock();
        }
        containingWallet.addOrUpdateExtension(this);
    }

    @Override
    public String getWalletExtensionID() {
        return EXTENSION_ID;
    }

    @Override
    public boolean isWalletExtensionMandatory() {
        return false;
    }

    @Override
    public byte[] serializeWalletExtension() {
        lock.lock();
        try {
            ClientState.StoredClientPaymentChannels.Builder builder = ClientState.StoredClientPaymentChannels.newBuilder();
            for (StoredClientChannel channel : mapChannels.values()) {
                // First a few asserts to make sure things won't break
                checkState(channel.valueToMe.signum() >= 0 && channel.valueToMe.compareTo(NetworkParameters.MAX_MONEY) < 0);
                checkState(channel.refundFees.signum() >= 0 && channel.refundFees.compareTo(NetworkParameters.MAX_MONEY) < 0);
                checkNotNull(channel.myKey.getPubKey());
                checkState(channel.refund.getConfidence().getSource() == TransactionConfidence.Source.SELF);
                final ClientState.StoredClientPaymentChannel.Builder value = ClientState.StoredClientPaymentChannel.newBuilder()
                        .setId(ByteString.copyFrom(channel.id.getBytes()))
                        .setContractTransaction(ByteString.copyFrom(channel.contract.bitcoinSerialize()))
                        .setRefundTransaction(ByteString.copyFrom(channel.refund.bitcoinSerialize()))
                        .setMyKey(ByteString.copyFrom(new byte[0])) // Not  used, but protobuf message requires
                        .setMyPublicKey(ByteString.copyFrom(channel.myKey.getPubKey()))
                        .setValueToMe(channel.valueToMe.value)
                        .setRefundFees(channel.refundFees.value);
                if (channel.close != null)
                    value.setCloseTransactionHash(ByteString.copyFrom(channel.close.getHash().getBytes()));
                builder.addChannels(value);
            }
            return builder.build().toByteArray();
        } finally {
            lock.unlock();
        }
    }

    @Override
    public void deserializeWalletExtension(Wallet containingWallet, byte[] data) throws Exception {
        lock.lock();
        try {
            checkState(this.containingWallet == null || this.containingWallet == containingWallet);
            this.containingWallet = containingWallet;
            NetworkParameters params = containingWallet.getParams();
            ClientState.StoredClientPaymentChannels states = ClientState.StoredClientPaymentChannels.parseFrom(data);
            for (ClientState.StoredClientPaymentChannel storedState : states.getChannelsList()) {
                Transaction refundTransaction = new Transaction(params, storedState.getRefundTransaction().toByteArray());
                refundTransaction.getConfidence().setSource(TransactionConfidence.Source.SELF);
                ECKey myKey = (storedState.getMyKey().isEmpty()) ?
                        containingWallet.findKeyFromPubKey(storedState.getMyPublicKey().toByteArray()) :
                        ECKey.fromPrivate(storedState.getMyKey().toByteArray());
                StoredClientChannel channel = new StoredClientChannel(Sha256Hash.wrap(storedState.getId().toByteArray()),
                        new Transaction(params, storedState.getContractTransaction().toByteArray()),
                        refundTransaction,
                        myKey,
                        Coin.valueOf(storedState.getValueToMe()),
                        Coin.valueOf(storedState.getRefundFees()), false);
                if (storedState.hasCloseTransactionHash()) {
                    Sha256Hash closeTxHash = Sha256Hash.wrap(storedState.getCloseTransactionHash().toByteArray());
                    channel.close = containingWallet.getTransaction(closeTxHash);
                }
                putChannel(channel, false);
            }
        } finally {
            lock.unlock();
        }
    }

    @Override
    public String toString() {
        lock.lock();
        try {
            StringBuilder buf = new StringBuilder("Client payment channel states:\n");
            for (StoredClientChannel channel : mapChannels.values())
                buf.append("  ").append(channel).append("\n");
            return buf.toString();
        } finally {
            lock.unlock();
        }
    }
}

/**
 * Represents the state of a channel once it has been opened in such a way that it can be stored and used to resume a
 * channel which was interrupted (eg on connection failure) or keep track of refund transactions which need broadcast
 * when they expire.
 */
class StoredClientChannel {
    Sha256Hash id;
    Transaction contract, refund;
    // The transaction that closed the channel (generated by the server)
    Transaction close;
    ECKey myKey;
    Coin valueToMe, refundFees;

    // In-memory flag to indicate intent to resume this channel (or that the channel is already in use)
    boolean active = false;

    StoredClientChannel(Sha256Hash id, Transaction contract, Transaction refund, ECKey myKey, Coin valueToMe,
                        Coin refundFees, boolean active) {
        this.id = id;
        this.contract = contract;
        this.refund = refund;
        this.myKey = myKey;
        this.valueToMe = valueToMe;
        this.refundFees = refundFees;
        this.active = active;
    }

    long expiryTimeSeconds() {
        return refund.getLockTime() + 60 * 5;
    }

    @Override
    public String toString() {
        final String newline = String.format("%n");
        final String closeStr = close == null ? "still open" : close.toString().replaceAll(newline, newline + "   ");
        return String.format("Stored client channel for server ID %s (%s)%n" +
                "    Key:         %s%n" +
                "    Value left:  %s%n" +
                "    Refund fees: %s%n" +
                "    Contract:  %s" +
                "Refund:    %s" +
                "Close:     %s",
                id, active ? "active" : "inactive", myKey, valueToMe, refundFees,
                contract.toString().replaceAll(newline, newline + "    "),
                refund.toString().replaceAll(newline, newline + "    "),
                closeStr);
    }
}


File: core/src/main/java/org/bitcoinj/protocols/channels/StoredPaymentChannelServerStates.java
/*
 * Copyright 2013 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.protocols.channels;

import org.bitcoinj.core.*;
import org.bitcoinj.utils.Threading;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.util.concurrent.SettableFuture;
import com.google.protobuf.ByteString;
import net.jcip.annotations.GuardedBy;
import org.slf4j.LoggerFactory;

import javax.annotation.Nullable;
import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.locks.ReentrantLock;

import static com.google.common.base.Preconditions.*;

/**
 * Keeps track of a set of {@link StoredServerChannel}s and expires them 2 hours before their refund transactions
 * unlock.
 */
public class StoredPaymentChannelServerStates implements WalletExtension {
    private static final org.slf4j.Logger log = LoggerFactory.getLogger(StoredPaymentChannelServerStates.class);

    static final String EXTENSION_ID = StoredPaymentChannelServerStates.class.getName();
    static final int MAX_SECONDS_TO_WAIT_FOR_BROADCASTER_TO_BE_SET = 10;

    @GuardedBy("lock") @VisibleForTesting final Map<Sha256Hash, StoredServerChannel> mapChannels = new HashMap<Sha256Hash, StoredServerChannel>();
    private Wallet wallet;
    private final SettableFuture<TransactionBroadcaster> broadcasterFuture = SettableFuture.create();

    private final Timer channelTimeoutHandler = new Timer(true);

    private final ReentrantLock lock = Threading.lock("StoredPaymentChannelServerStates");

    /**
     * The offset between the refund transaction's lock time and the time channels will be automatically closed.
     * This defines a window during which we must get the last payment transaction verified, ie it should allow time for
     * network propagation and for the payment transaction to be included in a block. Note that the channel expire time
     * is measured in terms of our local clock, and the refund transaction's lock time is measured in terms of Bitcoin
     * block header timestamps, which are allowed to drift up to two hours in the future, as measured by relaying nodes.
     */
    public static final long CHANNEL_EXPIRE_OFFSET = -2*60*60;

    /**
     * Creates a new PaymentChannelServerStateManager and associates it with the given {@link Wallet} and
     * {@link TransactionBroadcaster} which are used to complete and announce payment transactions.
     */
    public StoredPaymentChannelServerStates(@Nullable Wallet wallet, TransactionBroadcaster broadcaster) {
        setTransactionBroadcaster(broadcaster);
        this.wallet = wallet;
    }

    /**
     * Creates a new PaymentChannelServerStateManager and associates it with the given {@link Wallet}
     *
     * Use this constructor if you use WalletAppKit, it will provide the broadcaster for you (no need to call the setter)
     */
    public StoredPaymentChannelServerStates(@Nullable Wallet wallet) {
        this.wallet = wallet;
    }

    /**
     * Use this setter if the broadcaster is not available during instantiation and you're not using WalletAppKit.
     * This setter will let you delay the setting of the broadcaster until the Bitcoin network is ready.
     *
     * @param broadcaster Used when the payment channels are closed
     */
    public void setTransactionBroadcaster(TransactionBroadcaster broadcaster) {
        this.broadcasterFuture.set(checkNotNull(broadcaster));
    }

    /**
     * <p>Closes the given channel using {@link ServerConnectionEventHandler#closeChannel()} and
     * {@link PaymentChannelServerState#close()} to notify any connected client of channel closure and to complete and
     * broadcast the latest payment transaction.</p>
     *
     * <p>Removes the given channel from this set of {@link StoredServerChannel}s and notifies the wallet of a change to
     * this wallet extension.</p>
     */
    public void closeChannel(StoredServerChannel channel) {
        lock.lock();
        try {
            if (mapChannels.remove(channel.contract.getHash()) == null)
                return;
        } finally {
            lock.unlock();
        }
        synchronized (channel) {
            channel.closeConnectedHandler();
            try {
                TransactionBroadcaster broadcaster = getBroadcaster();
                channel.getOrCreateState(wallet, broadcaster).close();
            } catch (InsufficientMoneyException e) {
                e.printStackTrace();
            } catch (VerificationException e) {
                e.printStackTrace();
            }
            channel.state = null;
        }
        wallet.addOrUpdateExtension(this);
    }

    /**
     * If the broadcaster has not been set for MAX_SECONDS_TO_WAIT_FOR_BROADCASTER_TO_BE_SET seconds, then
     * the programmer probably forgot to set it and we should throw exception.
     */
    private TransactionBroadcaster getBroadcaster() {
        try {
            return broadcasterFuture.get(MAX_SECONDS_TO_WAIT_FOR_BROADCASTER_TO_BE_SET, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        } catch (ExecutionException e) {
            throw new RuntimeException(e);
        } catch (TimeoutException e) {
            String err = "Transaction broadcaster not set";
            log.error(err);
            throw new RuntimeException(err,e);
        }
    }

    /**
     * Gets the {@link StoredServerChannel} with the given channel id (ie contract transaction hash).
     */
    public StoredServerChannel getChannel(Sha256Hash id) {
        lock.lock();
        try {
            return mapChannels.get(id);
        } finally {
            lock.unlock();
        }
    }

    /**
     * <p>Puts the given channel in the channels map and automatically closes it 2 hours before its refund transaction
     * becomes spendable.</p>
     *
     * <p>Because there must be only one, canonical {@link StoredServerChannel} per channel, this method throws if the
     * channel is already present in the set of channels.</p>
     */
    public void putChannel(final StoredServerChannel channel) {
        lock.lock();
        try {
            checkArgument(mapChannels.put(channel.contract.getHash(), checkNotNull(channel)) == null);
            // Add the difference between real time and Utils.now() so that test-cases can use a mock clock.
            Date autocloseTime = new Date((channel.refundTransactionUnlockTimeSecs + CHANNEL_EXPIRE_OFFSET) * 1000L
                    + (System.currentTimeMillis() - Utils.currentTimeMillis()));
            log.info("Scheduling channel for automatic closure at {}: {}", autocloseTime, channel);
            channelTimeoutHandler.schedule(new TimerTask() {
                @Override
                public void run() {
                    log.info("Auto-closing channel: {}", channel);
                    closeChannel(channel);
                }
            }, autocloseTime);
        } finally {
            lock.unlock();
        }
    }

    @Override
    public String getWalletExtensionID() {
        return EXTENSION_ID;
    }

    @Override
    public boolean isWalletExtensionMandatory() {
        return false;
    }

    @Override
    public byte[] serializeWalletExtension() {
        lock.lock();
        try {
            ServerState.StoredServerPaymentChannels.Builder builder = ServerState.StoredServerPaymentChannels.newBuilder();
            for (StoredServerChannel channel : mapChannels.values()) {
                // First a few asserts to make sure things won't break
                // TODO: Pull MAX_MONEY from network parameters
                checkState(channel.bestValueToMe.signum() >= 0 && channel.bestValueToMe.compareTo(NetworkParameters.MAX_MONEY) < 0);
                checkState(channel.refundTransactionUnlockTimeSecs > 0);
                checkNotNull(channel.myKey.getPrivKeyBytes());
                ServerState.StoredServerPaymentChannel.Builder channelBuilder = ServerState.StoredServerPaymentChannel.newBuilder()
                        .setBestValueToMe(channel.bestValueToMe.value)
                        .setRefundTransactionUnlockTimeSecs(channel.refundTransactionUnlockTimeSecs)
                        .setContractTransaction(ByteString.copyFrom(channel.contract.bitcoinSerialize()))
                        .setClientOutput(ByteString.copyFrom(channel.clientOutput.bitcoinSerialize()))
                        .setMyKey(ByteString.copyFrom(channel.myKey.getPrivKeyBytes()));
                if (channel.bestValueSignature != null)
                    channelBuilder.setBestValueSignature(ByteString.copyFrom(channel.bestValueSignature));
                builder.addChannels(channelBuilder);
            }
            return builder.build().toByteArray();
        } finally {
            lock.unlock();
        }
    }

    @Override
    public void deserializeWalletExtension(Wallet containingWallet, byte[] data) throws Exception {
        lock.lock();
        try {
            this.wallet = containingWallet;
            ServerState.StoredServerPaymentChannels states = ServerState.StoredServerPaymentChannels.parseFrom(data);
            NetworkParameters params = containingWallet.getParams();
            for (ServerState.StoredServerPaymentChannel storedState : states.getChannelsList()) {
                StoredServerChannel channel = new StoredServerChannel(null,
                        new Transaction(params, storedState.getContractTransaction().toByteArray()),
                        new TransactionOutput(params, null, storedState.getClientOutput().toByteArray(), 0),
                        storedState.getRefundTransactionUnlockTimeSecs(),
                        ECKey.fromPrivate(storedState.getMyKey().toByteArray()),
                        Coin.valueOf(storedState.getBestValueToMe()),
                        storedState.hasBestValueSignature() ? storedState.getBestValueSignature().toByteArray() : null);
                putChannel(channel);
            }
        } finally {
            lock.unlock();
        }
    }

    @Override
    public String toString() {
        lock.lock();
        try {
            StringBuilder buf = new StringBuilder();
            for (StoredServerChannel stored : mapChannels.values()) {
                buf.append(stored);
            }
            return buf.toString();
        } finally {
            lock.unlock();
        }
    }
}
