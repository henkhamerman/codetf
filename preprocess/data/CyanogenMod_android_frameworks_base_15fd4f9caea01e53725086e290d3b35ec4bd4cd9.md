Refactoring Types: ['Extract Method']
oid/keyguard/KeyguardAbsKeyInputView.java
/*
 * Copyright (c) 2014, The Linux Foundation. All rights reserved.
 * Not a Contribution.
 *
 * Copyright (C) 2012 The Android Open Source Project
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

package com.android.keyguard;

import android.content.Context;
import android.graphics.drawable.Drawable;
import android.os.CountDownTimer;
import android.os.SystemClock;
import android.util.AttributeSet;
import android.view.HapticFeedbackConstants;
import android.view.KeyEvent;
import android.view.View;
import android.widget.LinearLayout;

import com.android.internal.widget.LockPatternUtils;

/**
 * Base class for PIN and password unlock screens.
 */
public abstract class KeyguardAbsKeyInputView extends LinearLayout
        implements KeyguardSecurityView {
    protected KeyguardSecurityCallback mCallback;
    protected LockPatternUtils mLockPatternUtils;
    protected SecurityMessageDisplay mSecurityMessageDisplay;
    protected View mEcaView;
    private Drawable mBouncerFrame;
    protected boolean mEnableHaptics;
    protected int mMaxCountdownTimes = 0;

    // To avoid accidental lockout due to events while the device in in the pocket, ignore
    // any passwords with length less than or equal to this length.
    protected static final int MINIMUM_PASSWORD_LENGTH_BEFORE_REPORT = 3;

    public KeyguardAbsKeyInputView(Context context) {
        this(context, null);
    }

    public KeyguardAbsKeyInputView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    public void setKeyguardCallback(KeyguardSecurityCallback callback) {
        mCallback = callback;
    }

    public void setLockPatternUtils(LockPatternUtils utils) {
        mLockPatternUtils = utils;
        mEnableHaptics = mLockPatternUtils.isTactileFeedbackEnabled();
    }

    public void reset() {
        // start fresh
        resetPasswordText(false /* animate */);
        // if the user is currently locked out, enforce it.
        long deadline = mLockPatternUtils.getLockoutAttemptDeadline();
        if (shouldLockout(deadline)) {
            handleAttemptLockout(deadline);
        } else {
            resetState();
        }
    }

    // Allow subclasses to override this behavior
    protected boolean shouldLockout(long deadline) {
        return deadline != 0;
    }

    protected abstract int getPasswordTextViewId();
    protected abstract void resetState();

    @Override
    protected void onFinishInflate() {
        mLockPatternUtils = new LockPatternUtils(mContext);
        mSecurityMessageDisplay = new KeyguardMessageArea.Helper(this);
        mEcaView = findViewById(R.id.keyguard_selector_fade_container);
        View bouncerFrameView = findViewById(R.id.keyguard_bouncer_frame);
        if (bouncerFrameView != null) {
            mBouncerFrame = bouncerFrameView.getBackground();
        }
    }

    /*
     * Override this if you have a different string for "wrong password"
     *
     * Note that PIN/PUK have their own implementation of verifyPasswordAndUnlock and so don't need this
     */
    protected int getWrongPasswordStringId() {
        return R.string.kg_wrong_password;
    }

    protected void verifyPasswordAndUnlock() {
        String entry = getPasswordText();
        if (mLockPatternUtils.checkPassword(entry)) {
            mCallback.reportUnlockAttempt(true);
            mCallback.dismiss(true);
        } else {
            if (entry.length() > MINIMUM_PASSWORD_LENGTH_BEFORE_REPORT ) {
                // to avoid accidental lockout, only count attempts that are long enough to be a
                // real password. This may require some tweaking.
                mCallback.reportUnlockAttempt(false);
                int attempts = KeyguardUpdateMonitor.getInstance(mContext).getFailedUnlockAttempts();
                if (!(mMaxCountdownTimes > 0) && 0 ==
                        (attempts % LockPatternUtils.FAILED_ATTEMPTS_BEFORE_TIMEOUT)) {
                    long deadline = mLockPatternUtils.setLockoutAttemptDeadline();
                    handleAttemptLockout(deadline);
                }
            }
            showWrongPassword();
        }
        resetPasswordText(true /* animate */);
    }

    protected abstract void resetPasswordText(boolean animate);
    protected abstract String getPasswordText();
    protected abstract void setPasswordEntryEnabled(boolean enabled);

    // Prevent user from using the PIN/Password entry until scheduled deadline.
    protected void handleAttemptLockout(long elapsedRealtimeDeadline) {
        setPasswordEntryEnabled(false);
        long elapsedRealtime = SystemClock.elapsedRealtime();
        new CountDownTimer(elapsedRealtimeDeadline - elapsedRealtime, 1000) {

            @Override
            public void onTick(long millisUntilFinished) {
                int secondsRemaining = (int) (millisUntilFinished / 1000);
                mSecurityMessageDisplay.setMessage(
                        R.string.kg_too_many_failed_attempts_countdown, true, secondsRemaining);
            }

            @Override
            public void onFinish() {
                mSecurityMessageDisplay.setMessage("", false);
                resetState();
            }
        }.start();
    }

    protected void showWrongPassword() {
        String msg = getContext().getString(getWrongPasswordStringId());
        if (mMaxCountdownTimes > 0) {
            int remaining = getRemainingCount();
            msg += " - " + getContext().getResources().getString(
                    R.string.kg_remaining_attempts, remaining);
        }
        mSecurityMessageDisplay.setMessage(msg, true);
    }

    protected int getRemainingCount() {
        return mMaxCountdownTimes
                - KeyguardUpdateMonitor.getInstance(mContext).getFailedUnlockAttempts();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        mCallback.userActivity();
        return false;
    }

    @Override
    public boolean needsInput() {
        return false;
    }

    @Override
    public void onPause() {

    }

    @Override
    public void onResume(int reason) {
        reset();
    }

    @Override
    public KeyguardSecurityCallback getCallback() {
        return mCallback;
    }

    // Cause a VIRTUAL_KEY vibration
    public void doHapticKeyClick() {
        if (mEnableHaptics) {
            performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY,
                    HapticFeedbackConstants.FLAG_IGNORE_VIEW_SETTING
                    | HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING);
        }
    }

    @Override
    public void showBouncer(int duration) {
        KeyguardSecurityViewHelper.
                showBouncer(mSecurityMessageDisplay, mEcaView, mBouncerFrame, duration);
    }

    @Override
    public void hideBouncer(int duration) {
        KeyguardSecurityViewHelper.
                hideBouncer(mSecurityMessageDisplay, mEcaView, mBouncerFrame, duration);
    }

    @Override
    public boolean startDisappearAnimation(Runnable finishRunnable) {
        return false;
    }
}



File: packages/Keyguard/src/com/android/keyguard/KeyguardSimPinView.java
/*
 * Copyright (c) 2014 The Linux Foundation. All rights reserved.
 * Not a Contribution.
 * Copyright (C) 2012 The Android Open Source Project
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

package com.android.keyguard;

import android.content.Context;
import android.app.AlertDialog;
import android.app.AlertDialog.Builder;
import android.app.Dialog;
import android.app.ProgressDialog;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.util.AttributeSet;
import android.util.Log;
import android.view.View;
import android.view.WindowManager;
import android.telephony.SubscriptionManager;
import android.telephony.SubscriptionInfo;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.TextView.OnEditorActionListener;

import com.android.internal.telephony.ITelephony;
import com.android.internal.telephony.PhoneConstants;
import com.android.internal.telephony.IccCardConstants;


/**
 * Displays a PIN pad for unlocking.
 */
public class KeyguardSimPinView extends KeyguardPinBasedInputView {
    private static final String LOG_TAG = "KeyguardSimPinView";
    private static final boolean DEBUG = KeyguardConstants.DEBUG;
    public static final String TAG = "KeyguardSimPinView";

    private ProgressDialog mSimUnlockProgressDialog = null;
    private CheckSimPin mCheckSimPinThread;
    private boolean mShowDefaultMessage = true;
    private int mRemainingAttempts = -1;
    private AlertDialog mRemainingAttemptsDialog;
    KeyguardUpdateMonitor mKgUpdateMonitor;
    private int mSubId = SubscriptionManager.INVALID_SUBSCRIPTION_ID;
    private TextView mSubNameView;
    private ImageView mSimImageView;

    private KeyguardUpdateMonitorCallback mUpdateCallback = new KeyguardUpdateMonitorCallback() {
        @Override
        public void onSubIdUpdated(int oldSubId, int newSubId) {
            if (mSubId == oldSubId) {
                mSubId = newSubId;
                //subId updated, handle sub info changed.
                handleSubInfoChange();
            }
        }

        @Override
        public void onSubInfoContentChanged(int subId, String column,
                                String sValue, int iValue) {
            if (column != null && column.equals(SubscriptionManager.DISPLAY_NAME)
                    && mSubId == subId) {
                //display name changed, handle sub info changed.
                handleSubInfoChange();
            }
        }

        @Override
        public void onSimStateChanged(int subId, IccCardConstants.State simState) {
            if (DEBUG) Log.d(TAG, "onSimStateChangedUsingSubId: " + simState + ", subId=" + subId);
            if (subId != mSubId) return;
            switch (simState) {
                case NOT_READY:
                case ABSENT:
                        closeKeyGuard();
                    break;
            }
        }
    };

    public KeyguardSimPinView(Context context) {
        this(context, null);
    }

    public KeyguardSimPinView(Context context, AttributeSet attrs) {
        super(context, attrs);
        mKgUpdateMonitor = KeyguardUpdateMonitor.getInstance(getContext());
    }

    public void resetState() {
        super.resetState();
        handleSubInfoChangeIfNeeded();
        if (mShowDefaultMessage) {
            showDefaultMessage();
        }
        mPasswordEntry.setEnabled(true);
    }

    private String getPinPasswordErrorMessage(int attemptsRemaining, boolean isDefault) {
        String displayMessage;

        if (attemptsRemaining == 0) {
            displayMessage = getContext().getString(R.string.kg_password_wrong_pin_code_pukked);
        } else if (attemptsRemaining > 0) {
            int msgId = isDefault ? R.plurals.kg_password_default_pin_message :
                    R.plurals.kg_password_wrong_pin_code;
            displayMessage = getContext().getResources()
                    .getQuantityString(msgId, attemptsRemaining, attemptsRemaining);
        } else {
            int msgId = isDefault ? R.string.kg_sim_pin_instructions :
                    R.string.kg_password_pin_failed;
            displayMessage = getContext().getString(msgId);
        }
        if (DEBUG) Log.d(LOG_TAG, "getPinPasswordErrorMessage:"
                + " attemptsRemaining=" + attemptsRemaining + " displayMessage=" + displayMessage);
        return displayMessage;
    }

    @Override
    protected boolean shouldLockout(long deadline) {
        // SIM PIN doesn't have a timed lockout
        return false;
    }

    @Override
    protected int getPasswordTextViewId() {
        return R.id.simPinEntry;
    }

    @Override
    protected void onFinishInflate() {
        super.onFinishInflate();

        mSubNameView = (TextView) findViewById(R.id.sim_name);
        mSimImageView = (ImageView) findViewById(R.id.keyguard_sim);
        mSubId = mKgUpdateMonitor.getSimPinLockSubId();
        if (mKgUpdateMonitor.getNumPhones() > 1) {
            mSubNameView.setVisibility(View.VISIBLE);
            handleSubInfoChange();
        }

        mSecurityMessageDisplay.setTimeout(0); // don't show ownerinfo/charging status by default
        if (mEcaView instanceof EmergencyCarrierArea) {
            ((EmergencyCarrierArea) mEcaView).setCarrierTextVisible(true);
        }

        mPasswordEntry.setQuickUnlockListener(null);
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        if (mShowDefaultMessage) {
            showDefaultMessage();
        }
        mKgUpdateMonitor.registerCallback(mUpdateCallback);
    }

    @Override
    protected void onDetachedFromWindow() {
        super.onDetachedFromWindow();
        mKgUpdateMonitor.removeCallback(mUpdateCallback);
        // dismiss the dialog.
        if (mSimUnlockProgressDialog != null) {
            mSimUnlockProgressDialog.dismiss();
            mSimUnlockProgressDialog = null;
        }
    }

    @Override
    public void showUsabilityHint() {
    }

    @Override
    public void onPause() {
        // dismiss the dialog.
        if (mSimUnlockProgressDialog != null) {
            mSimUnlockProgressDialog.dismiss();
            mSimUnlockProgressDialog = null;
        }
    }

    /**
     * Since the IPC can block, we want to run the request in a separate thread
     * with a callback.
     */
    private abstract class CheckSimPin extends Thread {
        private final String mPin;

        protected CheckSimPin(String pin) {
            mPin = pin;
        }

        abstract void onSimCheckResponse(final int result, final int attemptsRemaining);

        @Override
        public void run() {
            try {
                Log.v(TAG, "call supplyPinReportResultUsingSubId() mSubId = " + mSubId);
                final int[] result = ITelephony.Stub.asInterface(ServiceManager
                    .checkService("phone")).supplyPinReportResultForSubscriber(mSubId, mPin);
                Log.v(TAG, "supplyPinReportResultUsingSubId returned: " + result[0] +
                        " " + result[1]);
                post(new Runnable() {
                    public void run() {
                        onSimCheckResponse(result[0], result[1]);
                    }
                });
            } catch (RemoteException e) {
                Log.e(TAG, "RemoteException for supplyPinReportResultUsingSubId:", e);
                post(new Runnable() {
                    public void run() {
                        onSimCheckResponse(PhoneConstants.PIN_GENERAL_FAILURE, -1);
                    }
                });
            }
        }
    }

    private Dialog getSimUnlockProgressDialog() {
        if (mSimUnlockProgressDialog == null) {
            mSimUnlockProgressDialog = new ProgressDialog(mContext);
            mSimUnlockProgressDialog.setMessage(
                    getContext().getString(R.string.kg_sim_unlock_progress_dialog_message));
            mSimUnlockProgressDialog.setIndeterminate(true);
            mSimUnlockProgressDialog.setCancelable(false);
            mSimUnlockProgressDialog.getWindow().setType(
                    WindowManager.LayoutParams.TYPE_KEYGUARD_DIALOG);
        }
        return mSimUnlockProgressDialog;
    }

    private Dialog getPinRemainingAttemptsDialog(int remaining) {
        String msg = getPinPasswordErrorMessage(remaining, false);
        if (mRemainingAttemptsDialog == null) {
            Builder builder = new AlertDialog.Builder(mContext);
            builder.setMessage(msg);
            builder.setCancelable(false);
            builder.setNeutralButton(R.string.ok, null);
            mRemainingAttemptsDialog = builder.create();
            mRemainingAttemptsDialog.getWindow().setType(
                    WindowManager.LayoutParams.TYPE_KEYGUARD_DIALOG);
        } else {
            mRemainingAttemptsDialog.setMessage(msg);
        }
        return mRemainingAttemptsDialog;
    }

    private void closeKeyGuard() {
        if (DEBUG) Log.d(TAG, "closeKeyGuard: Verification Completed, closing Keyguard.");
        mRemainingAttempts = -1;
        mKgUpdateMonitor.reportSimUnlocked(mSubId);
        mCallback.dismiss(true);
        mShowDefaultMessage = true;
        reset();
    }

    @Override
    protected void verifyPasswordAndUnlock() {
        String entry = mPasswordEntry.getText();

        if (entry.length() < 4) {
            // otherwise, display a message to the user, and don't submit.
            mSecurityMessageDisplay.setMessage(R.string.kg_invalid_sim_pin_hint, true);
            resetPasswordText(true);
            mCallback.userActivity();
            return;
        }

        getSimUnlockProgressDialog().show();

        if (mCheckSimPinThread == null) {
            mCheckSimPinThread = new CheckSimPin(mPasswordEntry.getText()) {
                void onSimCheckResponse(final int result, final int attemptsRemaining) {
                    post(new Runnable() {
                        public void run() {
                            mRemainingAttempts = attemptsRemaining;
                            if (mSimUnlockProgressDialog != null) {
                                mSimUnlockProgressDialog.hide();
                            }
                            if (result == PhoneConstants.PIN_RESULT_SUCCESS) {
                                closeKeyGuard();
                            } else {
                                mShowDefaultMessage = false;
                                if (result == PhoneConstants.PIN_PASSWORD_INCORRECT) {
                                    // show message
                                    mSecurityMessageDisplay.setMessage(getPinPasswordErrorMessage(
                                            attemptsRemaining, false), true);
                                    if (attemptsRemaining <= 2) {
                                        // this is getting critical - show dialog
                                        getPinRemainingAttemptsDialog(attemptsRemaining).show();
                                    } else {
                                        // show message
                                        mSecurityMessageDisplay.setMessage(
                                                getPinPasswordErrorMessage(
                                                attemptsRemaining, false), true);
                                    }
                                } else {
                                    // "PIN operation failed!" - no idea what this was and no way to
                                    // find out. :/
                                    mSecurityMessageDisplay.setMessage(getContext().getString(
                                            R.string.kg_password_pin_failed), true);
                                }
                                if (DEBUG) Log.d(LOG_TAG, "verifyPasswordAndUnlock "
                                        + " CheckSimPin.onSimCheckResponse: " + result
                                        + " attemptsRemaining=" + attemptsRemaining);
                                resetPasswordText(true /* animate */);
                            }
                            mCallback.userActivity();
                            mCheckSimPinThread = null;
                        }
                    });
                }
            };
            mCheckSimPinThread.start();
        }
    }

    @Override
    public void startAppearAnimation() {
        // noop.
    }

    @Override
    public boolean startDisappearAnimation(Runnable finishRunnable) {
        return false;
    }

    private void handleSubInfoChangeIfNeeded() {
        int subId = mKgUpdateMonitor.getSimPinLockSubId();
        if (subId != mSubId && SubscriptionManager.isValidSubscriptionId(subId)) {
            mSubId = subId;
            handleSubInfoChange();
            mRemainingAttempts = -1;
            mShowDefaultMessage = true;
        }
    }

    private void handleSubInfoChange() {
        SubscriptionInfo info =
            SubscriptionManager.from(mContext).getActiveSubscriptionInfo(mSubId);
        CharSequence displayName = null;

        if (info != null) {
            displayName = info.getDisplayName();
        }
        if (displayName == null) {
            displayName = mContext.getString(R.string.kg_slot_name,
                    SubscriptionManager.getSlotId(mSubId) + 1);
        }

        if (DEBUG) Log.i(TAG, "handleSubInfoChange, mSubId=" + mSubId +
                ", displayName=" + displayName);
        mSubNameView.setText(displayName);

        if (mKgUpdateMonitor.getNumPhones() > 1) {
            final int color = info != null && info.getIconTint() != 0
                    ? info.getIconTint() : Color.WHITE;
            mSimImageView.setImageTintList(ColorStateList.valueOf(color));
        }
    }

    private void showDefaultMessage() {
        if (mRemainingAttempts >= 0) {
            mSecurityMessageDisplay.setMessage(getPinPasswordErrorMessage(
                    mRemainingAttempts, true), true);
            return;
        } else {
            mSecurityMessageDisplay.setMessage(R.string.kg_sim_pin_instructions, true);
        }
    }
}

