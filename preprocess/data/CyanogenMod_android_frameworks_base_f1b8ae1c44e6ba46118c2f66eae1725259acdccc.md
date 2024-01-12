Refactoring Types: ['Extract Method']
/widget/LockPatternUtils.java
/*
 * Copyright (C) 2007 The Android Open Source Project
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

package com.android.internal.widget;

import android.Manifest;
import android.app.ActivityManagerNative;
import android.app.AlarmManager;
import android.app.Profile;
import android.app.ProfileManager;
import android.app.admin.DevicePolicyManager;
import android.app.trust.TrustManager;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.UserInfo;
import android.os.AsyncTask;
import android.os.IBinder;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.os.SystemClock;
import android.os.SystemProperties;
import android.os.UserHandle;
import android.os.UserManager;
import android.os.storage.IMountService;
import android.os.storage.StorageManager;
import android.provider.Settings;
import android.telecom.TelecomManager;
import android.text.TextUtils;
import android.util.Log;
import android.view.IWindowManager;
import android.view.View;
import android.widget.Button;

import com.android.internal.R;
import com.google.android.collect.Lists;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * Utilities for the lock pattern and its settings.
 */
public class LockPatternUtils {

    private static final String TAG = "LockPatternUtils";
    private static final boolean DEBUG = false;

    /**
     * The maximum number of incorrect attempts before the user is prevented
     * from trying again for {@link #FAILED_ATTEMPT_TIMEOUT_MS}.
     */
    public static final int FAILED_ATTEMPTS_BEFORE_TIMEOUT = 5;

    /**
     * The number of incorrect attempts before which we fall back on an alternative
     * method of verifying the user, and resetting their lock pattern.
     */
    public static final int FAILED_ATTEMPTS_BEFORE_RESET = 20;

    /**
     * How long the user is prevented from trying again after entering the
     * wrong pattern too many times.
     */
    public static final long FAILED_ATTEMPT_TIMEOUT_MS = 30000L;

    /**
     * The interval of the countdown for showing progress of the lockout.
     */
    public static final long FAILED_ATTEMPT_COUNTDOWN_INTERVAL_MS = 1000L;


    /**
     * This dictates when we start telling the user that continued failed attempts will wipe
     * their device.
     */
    public static final int FAILED_ATTEMPTS_BEFORE_WIPE_GRACE = 5;

    /**
     * The minimum number of dots in a valid pattern.
     */
    public static final int MIN_LOCK_PATTERN_SIZE = 4;

    /**
     * The default size of the pattern lockscreen. Ex: 3x3
     */
    public static final byte PATTERN_SIZE_DEFAULT = 3;

    /**
     * The minimum number of dots the user must include in a wrong pattern
     * attempt for it to be counted against the counts that affect
     * {@link #FAILED_ATTEMPTS_BEFORE_TIMEOUT} and {@link #FAILED_ATTEMPTS_BEFORE_RESET}
     */
    public static final int MIN_PATTERN_REGISTER_FAIL = MIN_LOCK_PATTERN_SIZE;

    /**
     * Tells the keyguard to show the user switcher when the keyguard is created.
     */
    public static final String KEYGUARD_SHOW_USER_SWITCHER = "showuserswitcher";

    /**
     * Tells the keyguard to show the security challenge when the keyguard is created.
     */
    public static final String KEYGUARD_SHOW_SECURITY_CHALLENGE = "showsecuritychallenge";

    /**
     * Tells the keyguard to show the widget with the specified id when the keyguard is created.
     */
    public static final String KEYGUARD_SHOW_APPWIDGET = "showappwidget";

    /**
     * The bit in LOCK_BIOMETRIC_WEAK_FLAGS to be used to indicate whether liveliness should
     * be used
     */
    public static final int FLAG_BIOMETRIC_WEAK_LIVELINESS = 0x1;

    /**
     * Pseudo-appwidget id we use to represent the default clock status widget
     */
    public static final int ID_DEFAULT_STATUS_WIDGET = -2;

    public final static String LOCKOUT_PERMANENT_KEY = "lockscreen.lockedoutpermanently";
    public final static String LOCKOUT_ATTEMPT_DEADLINE = "lockscreen.lockoutattemptdeadline";
    public final static String PATTERN_EVER_CHOSEN_KEY = "lockscreen.patterneverchosen";
    public final static String PASSWORD_TYPE_KEY = "lockscreen.password_type";
    public static final String PASSWORD_TYPE_ALTERNATE_KEY = "lockscreen.password_type_alternate";
    // More precisely defines the lock method when the password type is set to biometric_weak
    public static final String PASSWORD_BIOMETRIC_EXACT_TYPE = "lockscreen.password_biometric_type";

    public final static String LOCK_PASSWORD_SALT_KEY = "lockscreen.password_salt";
    public final static String DISABLE_LOCKSCREEN_KEY = "lockscreen.disabled";
    public final static String LOCKSCREEN_OPTIONS = "lockscreen.options";
    public final static String LOCKSCREEN_BIOMETRIC_WEAK_FALLBACK
            = "lockscreen.biometric_weak_fallback";
    public static final String LOCKSCREEN_FINGERPRINT_FALLBACK = "lockscreen.fingerprint_fallback";
    public final static String BIOMETRIC_WEAK_EVER_CHOSEN_KEY
            = "lockscreen.biometricweakeverchosen";
    public final static String LOCKSCREEN_POWER_BUTTON_INSTANTLY_LOCKS
            = "lockscreen.power_button_instantly_locks";
    public final static String LOCKSCREEN_WIDGETS_ENABLED = "lockscreen.widgets_enabled";

    public final static String PASSWORD_HISTORY_KEY = "lockscreen.passwordhistory";

    private static final String LOCK_SCREEN_OWNER_INFO = Settings.Secure.LOCK_SCREEN_OWNER_INFO;
    private static final String LOCK_SCREEN_OWNER_INFO_ENABLED =
            Settings.Secure.LOCK_SCREEN_OWNER_INFO_ENABLED;

    private static final String ENABLED_TRUST_AGENTS = "lockscreen.enabledtrustagents";

    // Maximum allowed number of repeated or ordered characters in a sequence before we'll
    // consider it a complex PIN/password.
    public static final int MAX_ALLOWED_SEQUENCE = 3;

    // Types of weak biometric lock types
    public static final int BIOMETRIC_WEAK_UNKNOWN = -1;
    public static final int BIOMETRIC_WEAK_FACE = 0;
    public static final int BIOMETRIC_WEAK_FINGERPRINT = 1;

    private final Context mContext;
    private final ContentResolver mContentResolver;
    private DevicePolicyManager mDevicePolicyManager;
    private ILockSettings mLockSettingsService;
    private ProfileManager mProfileManager;

    private final boolean mMultiUserMode;

    // The current user is set by KeyguardViewMediator and shared by all LockPatternUtils.
    private static volatile int sCurrentUserId = UserHandle.USER_NULL;

    public DevicePolicyManager getDevicePolicyManager() {
        if (mDevicePolicyManager == null) {
            mDevicePolicyManager =
                (DevicePolicyManager)mContext.getSystemService(Context.DEVICE_POLICY_SERVICE);
            if (mDevicePolicyManager == null) {
                Log.e(TAG, "Can't get DevicePolicyManagerService: is it running?",
                        new IllegalStateException("Stack trace:"));
            }
        }
        return mDevicePolicyManager;
    }

    private TrustManager getTrustManager() {
        TrustManager trust = (TrustManager) mContext.getSystemService(Context.TRUST_SERVICE);
        if (trust == null) {
            Log.e(TAG, "Can't get TrustManagerService: is it running?",
                    new IllegalStateException("Stack trace:"));
        }
        return trust;
    }

    public LockPatternUtils(Context context) {
        mContext = context;
        mContentResolver = context.getContentResolver();
        mProfileManager = (ProfileManager) context.getSystemService(Context.PROFILE_SERVICE);

        // If this is being called by the system or by an application like keyguard that
        // has permision INTERACT_ACROSS_USERS, then LockPatternUtils will operate in multi-user
        // mode where calls are for the current user rather than the user of the calling process.
        mMultiUserMode = context.checkCallingOrSelfPermission(
            Manifest.permission.INTERACT_ACROSS_USERS_FULL) == PackageManager.PERMISSION_GRANTED;
    }

    private ILockSettings getLockSettings() {
        if (mLockSettingsService == null) {
            ILockSettings service = ILockSettings.Stub.asInterface(
                    ServiceManager.getService("lock_settings"));
            mLockSettingsService = service;
        }
        return mLockSettingsService;
    }

    public int getRequestedMinimumPasswordLength() {
        return getDevicePolicyManager().getPasswordMinimumLength(null, getCurrentOrCallingUserId());
    }

    /**
     * Gets the device policy password mode. If the mode is non-specific, returns
     * MODE_PATTERN which allows the user to choose anything.
     */
    public int getRequestedPasswordQuality() {
        return getDevicePolicyManager().getPasswordQuality(null, getCurrentOrCallingUserId());
    }

    public int getRequestedPasswordHistoryLength() {
        return getDevicePolicyManager().getPasswordHistoryLength(null, getCurrentOrCallingUserId());
    }

    public int getRequestedPasswordMinimumLetters() {
        return getDevicePolicyManager().getPasswordMinimumLetters(null,
                getCurrentOrCallingUserId());
    }

    public int getRequestedPasswordMinimumUpperCase() {
        return getDevicePolicyManager().getPasswordMinimumUpperCase(null,
                getCurrentOrCallingUserId());
    }

    public int getRequestedPasswordMinimumLowerCase() {
        return getDevicePolicyManager().getPasswordMinimumLowerCase(null,
                getCurrentOrCallingUserId());
    }

    public int getRequestedPasswordMinimumNumeric() {
        return getDevicePolicyManager().getPasswordMinimumNumeric(null,
                getCurrentOrCallingUserId());
    }

    public int getRequestedPasswordMinimumSymbols() {
        return getDevicePolicyManager().getPasswordMinimumSymbols(null,
                getCurrentOrCallingUserId());
    }

    public int getRequestedPasswordMinimumNonLetter() {
        return getDevicePolicyManager().getPasswordMinimumNonLetter(null,
                getCurrentOrCallingUserId());
    }

    public void reportFailedPasswordAttempt() {
        int userId = getCurrentOrCallingUserId();
        getDevicePolicyManager().reportFailedPasswordAttempt(userId);
        getTrustManager().reportUnlockAttempt(false /* authenticated */, userId);
        getTrustManager().reportRequireCredentialEntry(userId);
    }

    public void reportSuccessfulPasswordAttempt() {
        getDevicePolicyManager().reportSuccessfulPasswordAttempt(getCurrentOrCallingUserId());
        getTrustManager().reportUnlockAttempt(true /* authenticated */,
                getCurrentOrCallingUserId());
    }

    public void setCurrentUser(int userId) {
        sCurrentUserId = userId;
    }

    public int getCurrentUser() {
        if (sCurrentUserId != UserHandle.USER_NULL) {
            // Someone is regularly updating using setCurrentUser() use that value.
            return sCurrentUserId;
        }
        try {
            return ActivityManagerNative.getDefault().getCurrentUser().id;
        } catch (RemoteException re) {
            return UserHandle.USER_OWNER;
        }
    }

    public void removeUser(int userId) {
        try {
            getLockSettings().removeUser(userId);
        } catch (RemoteException re) {
            Log.e(TAG, "Couldn't remove lock settings for user " + userId);
        }
    }

    private int getCurrentOrCallingUserId() {
        if (mMultiUserMode) {
            // TODO: This is a little inefficient. See if all users of this are able to
            // handle USER_CURRENT and pass that instead.
            return getCurrentUser();
        } else {
            return UserHandle.getCallingUserId();
        }
    }

    /**
     * Check to see if a pattern matches the saved pattern.  If no pattern exists,
     * always returns true.
     * @param pattern The pattern to check.
     * @return Whether the pattern matches the stored one.
     */
    public boolean checkPattern(List<LockPatternView.Cell> pattern) {
        final int userId = getCurrentOrCallingUserId();
        try {
            return getLockSettings().checkPattern(patternToString(pattern), userId);
        } catch (RemoteException re) {
            return true;
        }
    }

    /**
     * Check to see if a password matches the saved password.  If no password exists,
     * always returns true.
     * @param password The password to check.
     * @return Whether the password matches the stored one.
     */
    public boolean checkPassword(String password) {
        final int userId = getCurrentOrCallingUserId();
        try {
            return getLockSettings().checkPassword(password, userId);
        } catch (RemoteException re) {
            return true;
        }
    }

    /**
     * Check to see if vold already has the password.
     * Note that this also clears vold's copy of the password.
     * @return Whether the vold password matches or not.
     */
    public boolean checkVoldPassword() {
        final int userId = getCurrentOrCallingUserId();
        try {
            return getLockSettings().checkVoldPassword(userId);
        } catch (RemoteException re) {
            return false;
        }
    }

    /**
     * Check to see if a password matches any of the passwords stored in the
     * password history.
     *
     * @param password The password to check.
     * @return Whether the password matches any in the history.
     */
    public boolean checkPasswordHistory(String password) {
        String passwordHashString = new String(
                passwordToHash(password, getCurrentOrCallingUserId()));
        String passwordHistory = getString(PASSWORD_HISTORY_KEY);
        if (passwordHistory == null) {
            return false;
        }
        // Password History may be too long...
        int passwordHashLength = passwordHashString.length();
        int passwordHistoryLength = getRequestedPasswordHistoryLength();
        if(passwordHistoryLength == 0) {
            return false;
        }
        int neededPasswordHistoryLength = passwordHashLength * passwordHistoryLength
                + passwordHistoryLength - 1;
        if (passwordHistory.length() > neededPasswordHistoryLength) {
            passwordHistory = passwordHistory.substring(0, neededPasswordHistoryLength);
        }
        return passwordHistory.contains(passwordHashString);
    }

    /**
     * Check to see if the user has stored a lock pattern.
     * @return Whether a saved pattern exists.
     */
    public boolean savedPatternExists() {
        return savedPatternExists(getCurrentOrCallingUserId());
    }

    /**
     * Check to see if the user has stored a lock pattern.
     * @return Whether a saved pattern exists.
     */
    public boolean savedPatternExists(int userId) {
        try {
            return getLockSettings().havePattern(userId);
        } catch (RemoteException re) {
            return false;
        }
    }

    /**
     * Check to see if the user has stored a lock pattern.
     * @return Whether a saved pattern exists.
     */
    public boolean savedPasswordExists() {
        return savedPasswordExists(getCurrentOrCallingUserId());
    }

     /**
     * Check to see if the user has stored a lock pattern.
     * @return Whether a saved pattern exists.
     */
    public boolean savedPasswordExists(int userId) {
        try {
            return getLockSettings().havePassword(userId);
        } catch (RemoteException re) {
            return false;
        }
    }

    /**
     * Return true if the user has ever chosen a pattern.  This is true even if the pattern is
     * currently cleared.
     *
     * @return True if the user has ever chosen a pattern.
     */
    public boolean isPatternEverChosen() {
        return getBoolean(PATTERN_EVER_CHOSEN_KEY, false);
    }

    /**
     * Return true if the user has ever chosen biometric weak.  This is true even if biometric
     * weak is not current set.
     *
     * @return True if the user has ever chosen biometric weak.
     */
    public boolean isBiometricWeakEverChosen() {
        return getBoolean(BIOMETRIC_WEAK_EVER_CHOSEN_KEY, false);
    }

    /**
     * Used by device policy manager to validate the current password
     * information it has.
     */
    public int getActivePasswordQuality() {
        int activePasswordQuality = DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED;
        // Note we don't want to use getKeyguardStoredPasswordQuality() because we want this to
        // return biometric_weak if that is being used instead of the backup
        int quality =
                (int) getLong(PASSWORD_TYPE_KEY, DevicePolicyManager.PASSWORD_QUALITY_SOMETHING);
        switch (quality) {
            case DevicePolicyManager.PASSWORD_QUALITY_SOMETHING:
                if (isLockPatternEnabled()) {
                    activePasswordQuality = DevicePolicyManager.PASSWORD_QUALITY_SOMETHING;
                }
                break;
            case DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK:
                if (isBiometricWeakInstalled()) {
                    activePasswordQuality = DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK;
                }
                break;
            case DevicePolicyManager.PASSWORD_QUALITY_NUMERIC:
                if (isLockPasswordEnabled()) {
                    activePasswordQuality = DevicePolicyManager.PASSWORD_QUALITY_NUMERIC;
                }
                break;
            case DevicePolicyManager.PASSWORD_QUALITY_NUMERIC_COMPLEX:
                if (isLockPasswordEnabled()) {
                    activePasswordQuality = DevicePolicyManager.PASSWORD_QUALITY_NUMERIC_COMPLEX;
                }
                break;
            case DevicePolicyManager.PASSWORD_QUALITY_ALPHABETIC:
                if (isLockPasswordEnabled()) {
                    activePasswordQuality = DevicePolicyManager.PASSWORD_QUALITY_ALPHABETIC;
                }
                break;
            case DevicePolicyManager.PASSWORD_QUALITY_ALPHANUMERIC:
                if (isLockPasswordEnabled()) {
                    activePasswordQuality = DevicePolicyManager.PASSWORD_QUALITY_ALPHANUMERIC;
                }
                break;
            case DevicePolicyManager.PASSWORD_QUALITY_COMPLEX:
                if (isLockPasswordEnabled()) {
                    activePasswordQuality = DevicePolicyManager.PASSWORD_QUALITY_COMPLEX;
                }
                break;
        }

        return activePasswordQuality;
    }

    public void clearLock(boolean isFallback) {
        clearLock(isFallback, getCurrentOrCallingUserId());
    }

    /**
     * Clear any lock pattern or password.
     */
    public void clearLock(boolean isFallback, int userHandle) {
        if(!isFallback) deleteGallery(userHandle);
        saveLockPassword(null, DevicePolicyManager.PASSWORD_QUALITY_SOMETHING, isFallback, false,
                userHandle);
        setLockPatternEnabled(false, userHandle);
        saveLockPattern(null, isFallback, false, userHandle);
        setLong(PASSWORD_TYPE_KEY, DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED, userHandle);
        setLong(PASSWORD_TYPE_ALTERNATE_KEY, DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED,
                userHandle);
        onAfterChangingPassword(userHandle);
    }

    /**
     * Disable showing lock screen at all when the DevicePolicyManager allows it.
     * This is only meaningful if pattern, pin or password are not set.
     *
     * @param disable Disables lock screen when true
     */
    public void setLockScreenDisabled(boolean disable) {
        setLong(DISABLE_LOCKSCREEN_KEY, disable ? 1 : 0);
    }

    /**
     * Determine if LockScreen can be disabled. This is used, for example, to tell if we should
     * show LockScreen or go straight to the home screen.
     *
     * @return true if lock screen is can be disabled
     */
    public boolean isLockScreenDisabled() {
        if (!isSecure() && getLong(DISABLE_LOCKSCREEN_KEY, 0) != 0) {
            // Check if the number of switchable users forces the lockscreen.
            final List<UserInfo> users = UserManager.get(mContext).getUsers(true);
            final int userCount = users.size();
            int switchableUsers = 0;
            for (int i = 0; i < userCount; i++) {
                if (users.get(i).supportsSwitchTo()) {
                    switchableUsers++;
                }
            }
            return switchableUsers < 2;
        }
        return false;
    }

    /**
     * Calls back SetupFaceLock to delete the temporary gallery file
     */
    public void deleteTempGallery() {
        Intent intent = new Intent().setAction("com.android.facelock.DELETE_GALLERY");
        intent.putExtra("deleteTempGallery", true);
        mContext.sendBroadcast(intent);
    }

    /**
     * Calls back SetupFaceLock to delete the gallery file when the lock type is changed
    */
    void deleteGallery(int userId) {
        if(usingBiometricWeak(userId)) {
            Intent intent = new Intent().setAction("com.android.facelock.DELETE_GALLERY");
            intent.putExtra("deleteGallery", true);
            mContext.sendBroadcastAsUser(intent, new UserHandle(userId));
        }
    }

    /**
     * Save a lock pattern.
     * @param pattern The new pattern to save.
     */
    public void saveLockPattern(List<LockPatternView.Cell> pattern) {
        this.saveLockPattern(pattern, false, false);
    }

    /**
     * Save a lock pattern.
     * @param pattern The new pattern to save.
     */
    public void saveLockPattern(List<LockPatternView.Cell> pattern, boolean isFallback,
            boolean isFingerprintFallback) {
        this.saveLockPattern(pattern, isFallback, isFingerprintFallback,
                getCurrentOrCallingUserId());
    }

    /**
     * Save a lock pattern.
     * @param pattern The new pattern to save.
     * @param isFallback Specifies if this is a fallback to biometric weak
     * @param userId the user whose pattern is to be saved.
     */
    public void saveLockPattern(List<LockPatternView.Cell> pattern, boolean isFallback,
            boolean isFingerprintFallback, int userId) {
        try {
            getLockSettings().setLockPattern(patternToString(pattern), userId);
            DevicePolicyManager dpm = getDevicePolicyManager();
            if (pattern != null) {
                // Update the device encryption password.
                if (userId == UserHandle.USER_OWNER
                        && LockPatternUtils.isDeviceEncryptionEnabled()) {
                    final boolean required = isCredentialRequiredToDecrypt(true);
                    if (!required) {
                        clearEncryptionPassword();
                    } else {
                        String stringPattern = patternToString(pattern);
                        updateEncryptionPassword(StorageManager.CRYPT_TYPE_PATTERN, stringPattern);
                    }
                }

                setBoolean(PATTERN_EVER_CHOSEN_KEY, true, userId);
                if (!isFallback) {
                    deleteGallery(userId);
                    setLong(PASSWORD_TYPE_KEY,
                            DevicePolicyManager.PASSWORD_QUALITY_SOMETHING, userId);
                    dpm.setActivePasswordState(DevicePolicyManager.PASSWORD_QUALITY_SOMETHING,
                            pattern.size(), 0, 0, 0, 0, 0, 0, userId);
                } else {
                    setLong(PASSWORD_TYPE_ALTERNATE_KEY,
                            DevicePolicyManager.PASSWORD_QUALITY_SOMETHING, userId);
                    if (!isFingerprintFallback) {
                        setLong(PASSWORD_TYPE_KEY,
                                DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK, userId);
                        finishBiometricWeak(userId);
                        dpm.setActivePasswordState(
                                DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK,
                                0, 0, 0, 0, 0, 0, 0, userId);
                    }
                }
            } else {
                dpm.setActivePasswordState(DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED, 0, 0,
                        0, 0, 0, 0, 0, userId);
            }
            onAfterChangingPassword(userId);
        } catch (RemoteException re) {
            Log.e(TAG, "Couldn't save lock pattern " + re);
        }
    }

    private void updateCryptoUserInfo() {
        int userId = getCurrentOrCallingUserId();
        if (userId != UserHandle.USER_OWNER) {
            return;
        }

        final String ownerInfo = isOwnerInfoEnabled() ? getOwnerInfo(userId) : "";

        IBinder service = ServiceManager.getService("mount");
        if (service == null) {
            Log.e(TAG, "Could not find the mount service to update the user info");
            return;
        }

        IMountService mountService = IMountService.Stub.asInterface(service);
        try {
            Log.d(TAG, "Setting owner info");
            mountService.setField(StorageManager.OWNER_INFO_KEY, ownerInfo);
        } catch (RemoteException e) {
            Log.e(TAG, "Error changing user info", e);
        }
    }

    public void setOwnerInfo(String info, int userId) {
        setString(LOCK_SCREEN_OWNER_INFO, info, userId);
        updateCryptoUserInfo();
    }

    public void setOwnerInfoEnabled(boolean enabled) {
        setBoolean(LOCK_SCREEN_OWNER_INFO_ENABLED, enabled);
        updateCryptoUserInfo();
    }

    public String getOwnerInfo(int userId) {
        return getString(LOCK_SCREEN_OWNER_INFO);
    }

    public boolean isOwnerInfoEnabled() {
        return getBoolean(LOCK_SCREEN_OWNER_INFO_ENABLED, false);
    }

    /**
     * Compute the password quality from the given password string.
     */
    static public int computePasswordQuality(String password) {
        boolean hasDigit = false;
        boolean hasNonDigit = false;
        final int len = password.length();
        for (int i = 0; i < len; i++) {
            if (Character.isDigit(password.charAt(i))) {
                hasDigit = true;
            } else {
                hasNonDigit = true;
            }
        }

        if (hasNonDigit && hasDigit) {
            return DevicePolicyManager.PASSWORD_QUALITY_ALPHANUMERIC;
        }
        if (hasNonDigit) {
            return DevicePolicyManager.PASSWORD_QUALITY_ALPHABETIC;
        }
        if (hasDigit) {
            return maxLengthSequence(password) > MAX_ALLOWED_SEQUENCE
                    ? DevicePolicyManager.PASSWORD_QUALITY_NUMERIC
                    : DevicePolicyManager.PASSWORD_QUALITY_NUMERIC_COMPLEX;
        }
        return DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED;
    }

    private static int categoryChar(char c) {
        if ('a' <= c && c <= 'z') return 0;
        if ('A' <= c && c <= 'Z') return 1;
        if ('0' <= c && c <= '9') return 2;
        return 3;
    }

    private static int maxDiffCategory(int category) {
        if (category == 0 || category == 1) return 1;
        else if (category == 2) return 10;
        return 0;
    }

    /*
     * Returns the maximum length of a sequential characters.  A sequence is defined as
     * monotonically increasing characters with a constant interval or the same character repeated.
     *
     * For example:
     * maxLengthSequence("1234") == 4
     * maxLengthSequence("1234abc") == 4
     * maxLengthSequence("aabc") == 3
     * maxLengthSequence("qwertyuio") == 1
     * maxLengthSequence("@ABC") == 3
     * maxLengthSequence(";;;;") == 4 (anything that repeats)
     * maxLengthSequence(":;<=>") == 1  (ordered, but not composed of alphas or digits)
     *
     * @param string the pass
     * @return the number of sequential letters or digits
     */
    public static int maxLengthSequence(String string) {
        if (string.length() == 0) return 0;
        char previousChar = string.charAt(0);
        int category = categoryChar(previousChar); //current category of the sequence
        int diff = 0; //difference between two consecutive characters
        boolean hasDiff = false; //if we are currently targeting a sequence
        int maxLength = 0; //maximum length of a sequence already found
        int startSequence = 0; //where the current sequence started
        for (int current = 1; current < string.length(); current++) {
            char currentChar = string.charAt(current);
            int categoryCurrent = categoryChar(currentChar);
            int currentDiff = (int) currentChar - (int) previousChar;
            if (categoryCurrent != category || Math.abs(currentDiff) > maxDiffCategory(category)) {
                maxLength = Math.max(maxLength, current - startSequence);
                startSequence = current;
                hasDiff = false;
                category = categoryCurrent;
            }
            else {
                if(hasDiff && currentDiff != diff) {
                    maxLength = Math.max(maxLength, current - startSequence);
                    startSequence = current - 1;
                }
                diff = currentDiff;
                hasDiff = true;
            }
            previousChar = currentChar;
        }
        maxLength = Math.max(maxLength, string.length() - startSequence);
        return maxLength;
    }

    /** Update the encryption password if it is enabled **/
    private void updateEncryptionPassword(final int type, final String password) {
        if (!isDeviceEncryptionEnabled()) {
            return;
        }
        final IBinder service = ServiceManager.getService("mount");
        if (service == null) {
            Log.e(TAG, "Could not find the mount service to update the encryption password");
            return;
        }

        new AsyncTask<Void, Void, Void>() {
            @Override
            protected Void doInBackground(Void... dummy) {
                IMountService mountService = IMountService.Stub.asInterface(service);
                try {
                    mountService.changeEncryptionPassword(type, password);
                } catch (RemoteException e) {
                    Log.e(TAG, "Error changing encryption password", e);
                }
                return null;
            }
        }.execute();
    }

    /**
     * Save a lock password.  Does not ensure that the password is as good
     * as the requested mode, but will adjust the mode to be as good as the
     * pattern.
     * @param password The password to save
     * @param quality {@see DevicePolicyManager#getPasswordQuality(android.content.ComponentName)}
     */
    public void saveLockPassword(String password, int quality) {
        this.saveLockPassword(password, quality, false);
    }

    /**
     * Save a lock password.  Does not ensure that the password is as good
     * as the requested mode, but will adjust the mode to be as good as the
     * pattern.
     * @param password The password to save
     * @param quality {@see DevicePolicyManager#getPasswordQuality(android.content.ComponentName)}
     * @param isFallback Specifies if this is a fallback to biometric weak
     */
    public void saveLockPassword(String password, int quality, boolean isFallback) {
        saveLockPassword(password, quality, isFallback, false);
    }

    /**
     * Save a lock password.  Does not ensure that the password is as good
     * as the requested mode, but will adjust the mode to be as good as the
     * pattern.
     * @param password The password to save
     * @param quality {@see DevicePolicyManager#getPasswordQuality(android.content.ComponentName)}
     * @param isFallback Specifies if this is a fallback to biometric weak
     * @param isFingerprintFallback Specifies if this is a fallback for fingerprint
     */
    public void saveLockPassword(String password, int quality, boolean isFallback,
                                 boolean isFingerprintFallback) {
        saveLockPassword(password, quality, isFallback, isFingerprintFallback,
                getCurrentOrCallingUserId());
    }

    /**
     * Save a lock password.  Does not ensure that the password is as good
     * as the requested mode, but will adjust the mode to be as good as the
     * pattern.
     * @param password The password to save
     * @param quality {@see DevicePolicyManager#getPasswordQuality(android.content.ComponentName)}
     * @param isFallback Specifies if this is a fallback to biometric weak
     * @param userHandle The userId of the user to change the password for
     */
    public void saveLockPassword(String password, int quality, boolean isFallback, boolean isFingerprintPassword, int userHandle) {
        try {
            DevicePolicyManager dpm = getDevicePolicyManager();
            if (!TextUtils.isEmpty(password)) {
                getLockSettings().setLockPassword(password, userHandle);
                int computedQuality = computePasswordQuality(password);

                // Update the device encryption password.
                if (userHandle == UserHandle.USER_OWNER
                        && LockPatternUtils.isDeviceEncryptionEnabled()) {
                    if (!isCredentialRequiredToDecrypt(true)) {
                        clearEncryptionPassword();
                    } else {
                        boolean numeric = computedQuality
                                == DevicePolicyManager.PASSWORD_QUALITY_NUMERIC;
                        boolean numericComplex = computedQuality
                                == DevicePolicyManager.PASSWORD_QUALITY_NUMERIC_COMPLEX;
                        int type = numeric || numericComplex ? StorageManager.CRYPT_TYPE_PIN
                                : StorageManager.CRYPT_TYPE_PASSWORD;
                        updateEncryptionPassword(type, password);
                    }
                }

                if (!isFallback) {
                    deleteGallery(userHandle);
                    setLong(PASSWORD_TYPE_KEY, Math.max(quality, computedQuality), userHandle);
                    if (computedQuality != DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED) {
                        int letters = 0;
                        int uppercase = 0;
                        int lowercase = 0;
                        int numbers = 0;
                        int symbols = 0;
                        int nonletter = 0;
                        for (int i = 0; i < password.length(); i++) {
                            char c = password.charAt(i);
                            if (c >= 'A' && c <= 'Z') {
                                letters++;
                                uppercase++;
                            } else if (c >= 'a' && c <= 'z') {
                                letters++;
                                lowercase++;
                            } else if (c >= '0' && c <= '9') {
                                numbers++;
                                nonletter++;
                            } else {
                                symbols++;
                                nonletter++;
                            }
                        }
                        dpm.setActivePasswordState(Math.max(quality, computedQuality),
                                password.length(), letters, uppercase, lowercase,
                                numbers, symbols, nonletter, userHandle);
                    } else {
                        // The password is not anything.
                        dpm.setActivePasswordState(
                                DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED,
                                0, 0, 0, 0, 0, 0, 0, userHandle);
                    }
                } else {
                    setLong(PASSWORD_TYPE_ALTERNATE_KEY, Math.max(quality, computedQuality),
                            userHandle);
                    if (!isFingerprintPassword) {
                        // Case where it's a fallback for biometric weak
                        setLong(PASSWORD_TYPE_KEY,
                                DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK, userHandle);
                        finishBiometricWeak(userHandle);
                        dpm.setActivePasswordState(
                                DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK,
                                0, 0, 0, 0, 0, 0, 0, userHandle);
                    }
                }
                // Add the password to the password history. We assume all
                // password hashes have the same length for simplicity of implementation.
                String passwordHistory = getString(PASSWORD_HISTORY_KEY, userHandle);
                if (passwordHistory == null) {
                    passwordHistory = "";
                }
                int passwordHistoryLength = getRequestedPasswordHistoryLength();
                if (passwordHistoryLength == 0) {
                    passwordHistory = "";
                } else {
                    byte[] hash = passwordToHash(password, userHandle);
                    passwordHistory = new String(hash) + "," + passwordHistory;
                    // Cut it to contain passwordHistoryLength hashes
                    // and passwordHistoryLength -1 commas.
                    passwordHistory = passwordHistory.substring(0, Math.min(hash.length
                            * passwordHistoryLength + passwordHistoryLength - 1, passwordHistory
                            .length()));
                }
                setString(PASSWORD_HISTORY_KEY, passwordHistory, userHandle);
            } else {
                // Empty password
                getLockSettings().setLockPassword(null, userHandle);
                if (userHandle == UserHandle.USER_OWNER) {
                    // Set the encryption password to default.
                    updateEncryptionPassword(StorageManager.CRYPT_TYPE_DEFAULT, null);
                }

                dpm.setActivePasswordState(
                        DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED, 0, 0, 0, 0, 0, 0, 0,
                        userHandle);
            }
            onAfterChangingPassword(userHandle);
        } catch (RemoteException re) {
            // Cant do much
            Log.e(TAG, "Unable to save lock password " + re);
        }
    }

    /**
     * Gets whether the device is encrypted.
     *
     * @return Whether the device is encrypted.
     */
    public static boolean isDeviceEncrypted() {
        IMountService mountService = IMountService.Stub.asInterface(
                ServiceManager.getService("mount"));
        try {
            return mountService.getEncryptionState() != IMountService.ENCRYPTION_STATE_NONE
                    && mountService.getPasswordType() != StorageManager.CRYPT_TYPE_DEFAULT;
        } catch (RemoteException re) {
            Log.e(TAG, "Error getting encryption state", re);
        }
        return true;
    }

    /**
     * Determine if the device supports encryption, even if it's set to default. This
     * differs from isDeviceEncrypted() in that it returns true even if the device is
     * encrypted with the default password.
     * @return true if device encryption is enabled
     */
    public static boolean isDeviceEncryptionEnabled() {
        final String status = SystemProperties.get("ro.crypto.state", "unsupported");
        return "encrypted".equalsIgnoreCase(status);
    }

    /**
     * Clears the encryption password.
     */
    public void clearEncryptionPassword() {
        updateEncryptionPassword(StorageManager.CRYPT_TYPE_DEFAULT, null);
    }

    /**
     * Retrieves the quality mode we're in.
     * {@see DevicePolicyManager#getPasswordQuality(android.content.ComponentName)}
     *
     * @return stored password quality
     */
    public int getKeyguardStoredPasswordQuality() {
        return getKeyguardStoredPasswordQuality(getCurrentOrCallingUserId());
    }

    /**
     * Retrieves the quality mode for {@param userHandle}.
     * {@see DevicePolicyManager#getPasswordQuality(android.content.ComponentName)}
     *
     * @return stored password quality
     */
    public int getKeyguardStoredPasswordQuality(int userHandle) {
        int quality = (int) getLong(PASSWORD_TYPE_KEY,
                DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED, userHandle);
        // If the user has chosen to use weak biometric sensor, then return the backup locking
        // method and treat biometric as a special case.
        if (quality == DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK) {
            quality = (int) getLong(PASSWORD_TYPE_ALTERNATE_KEY,
                        DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED, userHandle);
        }
        return quality;
    }

    /**
     * @return true if the lockscreen method is set to biometric weak
     */
    public boolean usingBiometricWeak() {
        return usingBiometricWeak(getCurrentOrCallingUserId());
    }

    /**
     * @return true if the lockscreen method is set to biometric weak
     */
    public boolean usingBiometricWeak(int userId) {
        int quality = (int) getLong(
                PASSWORD_TYPE_KEY, DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED, userId);
        return quality == DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK;
    }

    /**
     * @return true if the lockscreen method is set to fingerprint
     * @hide
     */
    public boolean usingFingerprint() {
        return usingFingerprint(getCurrentOrCallingUserId());
    }

    /**
     * @return true if the lockscreen method is set to fingerprint
     * @hide
     */
    public boolean usingFingerprint(int userId) {
        int quality = (int) getLong(
                PASSWORD_TYPE_KEY, DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED, userId);
        int exactType = (int) getLong(PASSWORD_BIOMETRIC_EXACT_TYPE, BIOMETRIC_WEAK_UNKNOWN);
        return quality == DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK &&
                exactType == BIOMETRIC_WEAK_FINGERPRINT;
    }

    /**
     * @hide
     */
    public void setUseFingerprint() {
        setUseFingerprint(getCurrentUser());
    }

    /**
     * @hide
     */
    public void setUseFingerprint(int userId) {
        DevicePolicyManager dpm = getDevicePolicyManager();
        setLong(PASSWORD_TYPE_KEY, DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK, userId);
        setLong(PASSWORD_BIOMETRIC_EXACT_TYPE, BIOMETRIC_WEAK_FINGERPRINT, userId);
        dpm.setActivePasswordState(DevicePolicyManager.PASSWORD_QUALITY_BIOMETRIC_WEAK,
                0, 0, 0, 0, 0, 0, 0, userId);
    }

    /**
     * @return whether fingerprint is installed
     * @hide
     */
    public boolean isFingerprintInstalled(Context context) {
        return context.getPackageManager().hasSystemFeature(PackageManager.FEATURE_FINGERPRINT);
    }

    /**
     * Deserialize a pattern.
     * @param string The pattern serialized with {@link #patternToString}
     * @return The pattern.
     */
    public List<LockPatternView.Cell> stringToPattern(String string) {
        List<LockPatternView.Cell> result = Lists.newArrayList();

        final byte size = getLockPatternSize();
        LockPatternView.Cell.updateSize(size);

        final byte[] bytes = string.getBytes();
        for (int i = 0; i < bytes.length; i++) {
            byte b = bytes[i];
            result.add(LockPatternView.Cell.of(b / size, b % size, size));
        }
        return result;
    }

    /**
     * Serialize a pattern.
     * @param pattern The pattern.
     * @return The pattern in string form.
     */
    public String patternToString(List<LockPatternView.Cell> pattern) {
        return patternToString(pattern, getLockPatternSize());
    }

    /**
     * Serialize a pattern.
     * @param pattern The pattern.
     * @param patternGridSize the pattern size
     * @return The pattern in string form.
     */
    public static String patternToString(List<LockPatternView.Cell> pattern, int patternGridSize) {
        if (pattern == null) {
            return "";
        }
        final int patternSize = pattern.size();

        byte[] res = new byte[patternSize];
        for (int i = 0; i < patternSize; i++) {
            LockPatternView.Cell cell = pattern.get(i);
            res[i] = (byte) (cell.getRow() * patternGridSize + cell.getColumn());
        }
        return new String(res);
    }

    /*
     * Generate an SHA-1 hash for the pattern. Not the most secure, but it is
     * at least a second level of protection. First level is that the file
     * is in a location only readable by the system process.
     * @param pattern the gesture pattern.
     * @return the hash of the pattern in a byte array.
     */
    public byte[] patternToHash(List<LockPatternView.Cell> pattern) {
        if (pattern == null) {
            return null;
        }

        final int patternSize = pattern.size();
        byte[] res = new byte[patternSize];
        for (int i = 0; i < patternSize; i++) {
            LockPatternView.Cell cell = pattern.get(i);
            res[i] = (byte) (cell.getRow() * getLockPatternSize() + cell.getColumn());
        }
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-1");
            byte[] hash = md.digest(res);
            return hash;
        } catch (NoSuchAlgorithmException nsa) {
            return res;
        }
    }

    private String getSalt(int userId) {
        long salt = getLong(LOCK_PASSWORD_SALT_KEY, 0, userId);
        if (salt == 0) {
            try {
                salt = SecureRandom.getInstance("SHA1PRNG").nextLong();
                setLong(LOCK_PASSWORD_SALT_KEY, salt, userId);
                Log.v(TAG, "Initialized lock password salt for user: " + userId);
            } catch (NoSuchAlgorithmException e) {
                // Throw an exception rather than storing a password we'll never be able to recover
                throw new IllegalStateException("Couldn't get SecureRandom number", e);
            }
        }
        return Long.toHexString(salt);
    }

    /*
     * Generate a hash for the given password. To avoid brute force attacks, we use a salted hash.
     * Not the most secure, but it is at least a second level of protection. First level is that
     * the file is in a location only readable by the system process.
     * @param password the gesture pattern.
     * @return the hash of the pattern in a byte array.
     */
    public byte[] passwordToHash(String password, int userId) {
        if (password == null) {
            return null;
        }
        String algo = null;
        byte[] hashed = null;
        try {
            byte[] saltedPassword = (password + getSalt(userId)).getBytes();
            byte[] sha1 = MessageDigest.getInstance(algo = "SHA-1").digest(saltedPassword);
            byte[] md5 = MessageDigest.getInstance(algo = "MD5").digest(saltedPassword);
            hashed = (toHex(sha1) + toHex(md5)).getBytes();
        } catch (NoSuchAlgorithmException e) {
            Log.w(TAG, "Failed to encode string because of missing algorithm: " + algo);
        }
        return hashed;
    }

    private static String toHex(byte[] ary) {
        final String hex = "0123456789ABCDEF";
        String ret = "";
        for (int i = 0; i < ary.length; i++) {
            ret += hex.charAt((ary[i] >> 4) & 0xf);
            ret += hex.charAt(ary[i] & 0xf);
        }
        return ret;
    }

    /**
     * @return Whether the lock password is enabled, or if it is set as a backup for biometric weak
     */
    public boolean isLockPasswordEnabled() {
        long mode = getLong(PASSWORD_TYPE_KEY, 0);
        long backupMode = getLong(PASSWORD_TYPE_ALTERNATE_KEY, 0);
        final boolean passwordEnabled = mode == DevicePolicyManager.PASSWORD_QUALITY_ALPHABETIC
                || mode == DevicePolicyManager.PASSWORD_QUALITY_NUMERIC
                || mode == DevicePolicyManager.PASSWORD_QUALITY_NUMERIC_COMPLEX
                || mode == DevicePolicyManager.PASSWORD_QUALITY_ALPHANUMERIC
                || mode == DevicePolicyManager.PASSWORD_QUALITY_COMPLEX;
        final boolean backupEnabled = backupMode == DevicePolicyManager.PASSWORD_QUALITY_ALPHABETIC
                || backupMode == DevicePolicyManager.PASSWORD_QUALITY_NUMERIC
                || backupMode == DevicePolicyManager.PASSWORD_QUALITY_NUMERIC_COMPLEX
                || backupMode == DevicePolicyManager.PASSWORD_QUALITY_ALPHANUMERIC
                || backupMode == DevicePolicyManager.PASSWORD_QUALITY_COMPLEX;

        return savedPasswordExists() && (passwordEnabled ||
                (usingBiometricWeak() && backupEnabled));
    }

    /**
     * @return Whether the lock pattern is enabled, or if it is set as a backup for biometric weak
     */
    public boolean isLockPatternEnabled() {
        return isLockPatternEnabled(getCurrentOrCallingUserId());
    }

    /**
     * @return Whether the lock pattern is enabled, or if it is set as a backup for biometric weak
     */
    public boolean isLockPatternEnabled(int userId) {
        final boolean backupEnabled =
                getLong(PASSWORD_TYPE_ALTERNATE_KEY,
                        DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED, userId)
                                == DevicePolicyManager.PASSWORD_QUALITY_SOMETHING;

        return getBoolean(Settings.Secure.LOCK_PATTERN_ENABLED, false, userId)
                && (getLong(PASSWORD_TYPE_KEY, DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED,
                        userId) == DevicePolicyManager.PASSWORD_QUALITY_SOMETHING
                        || (usingBiometricWeak(userId) && backupEnabled));
    }

    /**
     * @return Whether biometric weak lock is installed and that the front facing camera exists
     */
    public boolean isBiometricWeakInstalled() {
        // Check that it's installed
        PackageManager pm = mContext.getPackageManager();
        try {
            pm.getPackageInfo("com.android.facelock", PackageManager.GET_ACTIVITIES);
        } catch (PackageManager.NameNotFoundException e) {
            return false;
        }

        // Check that the camera is enabled
        if (!pm.hasSystemFeature(PackageManager.FEATURE_CAMERA_FRONT)) {
            return false;
        }
        if (getDevicePolicyManager().getCameraDisabled(null, getCurrentOrCallingUserId())) {
            return false;
        }

        // TODO: If we decide not to proceed with Face Unlock as a trustlet, this must be changed
        // back to returning true.  If we become certain that Face Unlock will be a trustlet, this
        // entire function and a lot of other code can be removed.
        if (DEBUG) Log.d(TAG, "Forcing isBiometricWeakInstalled() to return false to disable it");
        return false;
    }

    /**
     * Set whether biometric weak liveliness is enabled.
     */
    public void setBiometricWeakLivelinessEnabled(boolean enabled) {
        long currentFlag = getLong(Settings.Secure.LOCK_BIOMETRIC_WEAK_FLAGS, 0L);
        long newFlag;
        if (enabled) {
            newFlag = currentFlag | FLAG_BIOMETRIC_WEAK_LIVELINESS;
        } else {
            newFlag = currentFlag & ~FLAG_BIOMETRIC_WEAK_LIVELINESS;
        }
        setLong(Settings.Secure.LOCK_BIOMETRIC_WEAK_FLAGS, newFlag);
    }

    /**
     * @return Whether the biometric weak liveliness is enabled.
     */
    public boolean isBiometricWeakLivelinessEnabled() {
        long currentFlag = getLong(Settings.Secure.LOCK_BIOMETRIC_WEAK_FLAGS, 0L);
        return ((currentFlag & FLAG_BIOMETRIC_WEAK_LIVELINESS) != 0);
    }

    /**
     * Set whether the lock pattern is enabled.
     */
    public void setLockPatternEnabled(boolean enabled) {
        setLockPatternEnabled(enabled, getCurrentOrCallingUserId());
    }

    /**
     * Set whether the lock pattern is enabled.
     */
    public void setLockPatternEnabled(boolean enabled, int userHandle) {
        setBoolean(Settings.Secure.LOCK_PATTERN_ENABLED, enabled, userHandle);
    }

    /**
     * @return Whether the visible pattern is enabled.
     */
    public boolean isVisiblePatternEnabled() {
        return getBoolean(Settings.Secure.LOCK_PATTERN_VISIBLE, false);
    }

    /**
     * Set whether the visible pattern is enabled.
     */
    public void setVisiblePatternEnabled(boolean enabled) {
        setBoolean(Settings.Secure.LOCK_PATTERN_VISIBLE, enabled);

        // Update for crypto if owner
        int userId = getCurrentOrCallingUserId();
        if (userId != UserHandle.USER_OWNER) {
            return;
        }

        IBinder service = ServiceManager.getService("mount");
        if (service == null) {
            Log.e(TAG, "Could not find the mount service to update the user info");
            return;
        }

        IMountService mountService = IMountService.Stub.asInterface(service);
        try {
            mountService.setField(StorageManager.PATTERN_VISIBLE_KEY, enabled ? "1" : "0");
        } catch (RemoteException e) {
            Log.e(TAG, "Error changing pattern visible state", e);
        }
    }

    /**
     * @return Whether tactile feedback for the pattern is enabled.
     */
    public boolean isTactileFeedbackEnabled() {
        return Settings.System.getIntForUser(mContentResolver,
                Settings.System.HAPTIC_FEEDBACK_ENABLED, 1, UserHandle.USER_CURRENT) != 0;
    }

    /**
     * @return the pattern lockscreen size
     */
    public byte getLockPatternSize() {
        long size = getLong(Settings.Secure.LOCK_PATTERN_SIZE, -1);
        if (size > 0 && size < 128) {
            return (byte) size;
        }
        return LockPatternUtils.PATTERN_SIZE_DEFAULT;
    }

    /**
     * Set the pattern lockscreen size
     */
    public void setLockPatternSize(long size) {
        setLong(Settings.Secure.LOCK_PATTERN_SIZE, size);
    }

    public void setVisibleDotsEnabled(boolean enabled) {
        setBoolean(Settings.Secure.LOCK_DOTS_VISIBLE, enabled);
    }

    public boolean isVisibleDotsEnabled() {
        return getBoolean(Settings.Secure.LOCK_DOTS_VISIBLE, true);
    }

    public void setShowErrorPath(boolean enabled) {
        setBoolean(Settings.Secure.LOCK_SHOW_ERROR_PATH, enabled);
    }

    public boolean isShowErrorPath() {
        return getBoolean(Settings.Secure.LOCK_SHOW_ERROR_PATH, true);
    }

    /**
     * Set and store the lockout deadline, meaning the user can't attempt his/her unlock
     * pattern until the deadline has passed.
     * @return the chosen deadline.
     */
    public long setLockoutAttemptDeadline() {
        final long deadline = SystemClock.elapsedRealtime() + FAILED_ATTEMPT_TIMEOUT_MS;
        setLong(LOCKOUT_ATTEMPT_DEADLINE, deadline);
        return deadline;
    }

    /**
     * @return The elapsed time in millis in the future when the user is allowed to
     *   attempt to enter his/her lock pattern, or 0 if the user is welcome to
     *   enter a pattern.
     */
    public long getLockoutAttemptDeadline() {
        final long deadline = getLong(LOCKOUT_ATTEMPT_DEADLINE, 0L);
        final long now = SystemClock.elapsedRealtime();
        if (deadline < now || deadline > (now + FAILED_ATTEMPT_TIMEOUT_MS)) {
            return 0L;
        }
        return deadline;
    }

    /**
     * @return Whether the user is permanently locked out until they verify their
     *   credentials.  Occurs after {@link #FAILED_ATTEMPTS_BEFORE_RESET} failed
     *   attempts.
     */
    public boolean isPermanentlyLocked() {
        return getBoolean(LOCKOUT_PERMANENT_KEY, false);
    }

    /**
     * Set the state of whether the device is permanently locked, meaning the user
     * must authenticate via other means.
     *
     * @param locked Whether the user is permanently locked out until they verify their
     *   credentials.  Occurs after {@link #FAILED_ATTEMPTS_BEFORE_RESET} failed
     *   attempts.
     */
    public void setPermanentlyLocked(boolean locked) {
        setBoolean(LOCKOUT_PERMANENT_KEY, locked);
    }

    public boolean isEmergencyCallCapable() {
        return mContext.getResources().getBoolean(
                com.android.internal.R.bool.config_voice_capable);
    }

    public boolean isPukUnlockScreenEnable() {
        return mContext.getResources().getBoolean(
                com.android.internal.R.bool.config_enable_puk_unlock_screen);
    }

    public boolean isEmergencyCallEnabledWhileSimLocked() {
        return mContext.getResources().getBoolean(
                com.android.internal.R.bool.config_enable_emergency_call_while_sim_locked);
    }

    /**
     * @return A formatted string of the next alarm (for showing on the lock screen),
     *   or null if there is no next alarm.
     */
    public AlarmManager.AlarmClockInfo getNextAlarm() {
        AlarmManager alarmManager = (AlarmManager) mContext.getSystemService(Context.ALARM_SERVICE);
        return alarmManager.getNextAlarmClock(UserHandle.USER_CURRENT);
    }

    private boolean getBoolean(String secureSettingKey, boolean defaultValue, int userId) {
        try {
            return getLockSettings().getBoolean(secureSettingKey, defaultValue, userId);
        } catch (RemoteException re) {
            return defaultValue;
        }
    }

    private boolean getBoolean(String secureSettingKey, boolean defaultValue) {
        return getBoolean(secureSettingKey, defaultValue, getCurrentOrCallingUserId());
    }

    private void setBoolean(String secureSettingKey, boolean enabled, int userId) {
        try {
            getLockSettings().setBoolean(secureSettingKey, enabled, userId);
        } catch (RemoteException re) {
            // What can we do?
            Log.e(TAG, "Couldn't write boolean " + secureSettingKey + re);
        }
    }

    private void setBoolean(String secureSettingKey, boolean enabled) {
        setBoolean(secureSettingKey, enabled, getCurrentOrCallingUserId());
    }

    public int[] getAppWidgets() {
        return getAppWidgets(UserHandle.USER_CURRENT);
    }

    private int[] getAppWidgets(int userId) {
        String appWidgetIdString = Settings.Secure.getStringForUser(
                mContentResolver, Settings.Secure.LOCK_SCREEN_APPWIDGET_IDS, userId);
        String delims = ",";
        if (appWidgetIdString != null && appWidgetIdString.length() > 0) {
            String[] appWidgetStringIds = appWidgetIdString.split(delims);
            int[] appWidgetIds = new int[appWidgetStringIds.length];
            for (int i = 0; i < appWidgetStringIds.length; i++) {
                String appWidget = appWidgetStringIds[i];
                try {
                    appWidgetIds[i] = Integer.decode(appWidget);
                } catch (NumberFormatException e) {
                    Log.d(TAG, "Error when parsing widget id " + appWidget);
                    return null;
                }
            }
            return appWidgetIds;
        }
        return new int[0];
    }

    private static String combineStrings(int[] list, String separator) {
        int listLength = list.length;

        switch (listLength) {
            case 0: {
                return "";
            }
            case 1: {
                return Integer.toString(list[0]);
            }
        }

        int strLength = 0;
        int separatorLength = separator.length();

        String[] stringList = new String[list.length];
        for (int i = 0; i < listLength; i++) {
            stringList[i] = Integer.toString(list[i]);
            strLength += stringList[i].length();
            if (i < listLength - 1) {
                strLength += separatorLength;
            }
        }

        StringBuilder sb = new StringBuilder(strLength);

        for (int i = 0; i < listLength; i++) {
            sb.append(list[i]);
            if (i < listLength - 1) {
                sb.append(separator);
            }
        }

        return sb.toString();
    }

    // appwidget used when appwidgets are disabled (we make an exception for
    // default clock widget)
    public void writeFallbackAppWidgetId(int appWidgetId) {
        Settings.Secure.putIntForUser(mContentResolver,
                Settings.Secure.LOCK_SCREEN_FALLBACK_APPWIDGET_ID,
                appWidgetId,
                UserHandle.USER_CURRENT);
    }

    // appwidget used when appwidgets are disabled (we make an exception for
    // default clock widget)
    public int getFallbackAppWidgetId() {
        return Settings.Secure.getIntForUser(
                mContentResolver,
                Settings.Secure.LOCK_SCREEN_FALLBACK_APPWIDGET_ID,
                AppWidgetManager.INVALID_APPWIDGET_ID,
                UserHandle.USER_CURRENT);
    }

    private void writeAppWidgets(int[] appWidgetIds) {
        Settings.Secure.putStringForUser(mContentResolver,
                        Settings.Secure.LOCK_SCREEN_APPWIDGET_IDS,
                        combineStrings(appWidgetIds, ","),
                        UserHandle.USER_CURRENT);
    }

    // TODO: log an error if this returns false
    public boolean addAppWidget(int widgetId, int index) {
        int[] widgets = getAppWidgets();
        if (widgets == null) {
            return false;
        }
        if (index < 0 || index > widgets.length) {
            return false;
        }
        int[] newWidgets = new int[widgets.length + 1];
        for (int i = 0, j = 0; i < newWidgets.length; i++) {
            if (index == i) {
                newWidgets[i] = widgetId;
                i++;
            }
            if (i < newWidgets.length) {
                newWidgets[i] = widgets[j];
                j++;
            }
        }
        writeAppWidgets(newWidgets);
        return true;
    }

    public boolean removeAppWidget(int widgetId) {
        int[] widgets = getAppWidgets();

        if (widgets.length == 0) {
            return false;
        }

        int[] newWidgets = new int[widgets.length - 1];
        for (int i = 0, j = 0; i < widgets.length; i++) {
            if (widgets[i] == widgetId) {
                // continue...
            } else if (j >= newWidgets.length) {
                // we couldn't find the widget
                return false;
            } else {
                newWidgets[j] = widgets[i];
                j++;
            }
        }
        writeAppWidgets(newWidgets);
        return true;
    }

    private long getLong(String secureSettingKey, long defaultValue, int userHandle) {
        try {
            return getLockSettings().getLong(secureSettingKey, defaultValue, userHandle);
        } catch (RemoteException re) {
            return defaultValue;
        }
    }

    private long getLong(String secureSettingKey, long defaultValue) {
        try {
            return getLockSettings().getLong(secureSettingKey, defaultValue,
                    getCurrentOrCallingUserId());
        } catch (RemoteException re) {
            return defaultValue;
        }
    }

    private void setLong(String secureSettingKey, long value) {
        setLong(secureSettingKey, value, getCurrentOrCallingUserId());
    }

    private void setLong(String secureSettingKey, long value, int userHandle) {
        try {
            getLockSettings().setLong(secureSettingKey, value, userHandle);
        } catch (RemoteException re) {
            // What can we do?
            Log.e(TAG, "Couldn't write long " + secureSettingKey + re);
        }
    }

    private String getString(String secureSettingKey) {
        return getString(secureSettingKey, getCurrentOrCallingUserId());
    }

    private String getString(String secureSettingKey, int userHandle) {
        try {
            return getLockSettings().getString(secureSettingKey, null, userHandle);
        } catch (RemoteException re) {
            return null;
        }
    }

    private void setString(String secureSettingKey, String value, int userHandle) {
        try {
            getLockSettings().setString(secureSettingKey, value, userHandle);
        } catch (RemoteException re) {
            // What can we do?
            Log.e(TAG, "Couldn't write string " + secureSettingKey + re);
        }
    }

    public boolean isSecure() {
        return isSecure(getCurrentOrCallingUserId());
    }

    public boolean isSecure(int userId) {
        long mode = getKeyguardStoredPasswordQuality(userId);
        final boolean isPattern = mode == DevicePolicyManager.PASSWORD_QUALITY_SOMETHING;
        final boolean isPassword = mode == DevicePolicyManager.PASSWORD_QUALITY_NUMERIC
                || mode == DevicePolicyManager.PASSWORD_QUALITY_NUMERIC_COMPLEX
                || mode == DevicePolicyManager.PASSWORD_QUALITY_ALPHABETIC
                || mode == DevicePolicyManager.PASSWORD_QUALITY_ALPHANUMERIC
                || mode == DevicePolicyManager.PASSWORD_QUALITY_COMPLEX;
        final boolean secure =
                isPattern && isLockPatternEnabled(userId) && savedPatternExists(userId)
                || isPassword && savedPasswordExists(userId);
        return secure && getActiveProfileLockMode() != Profile.LockMode.DISABLE;
    }

    public int getActiveProfileLockMode() {
        // Check device policy
        DevicePolicyManager dpm = getDevicePolicyManager();
        if (dpm.requireSecureKeyguard(getCurrentOrCallingUserId())) {
            // Always enforce lock screen
            return Profile.LockMode.DEFAULT;
        }
        final Profile profile = mProfileManager.getActiveProfile();
        return profile == null ? Profile.LockMode.DEFAULT : profile.getScreenLockMode();
    }

    /**
     * Sets the emergency button visibility based on isEmergencyCallCapable().
     *
     * If the emergency button is visible, sets the text on the emergency button
     * to indicate what action will be taken.
     *
     * If there's currently a call in progress, the button will take them to the call
     * @param button The button to update
     * @param shown Indicates whether the given screen wants the emergency button to show at all
     * @param showIcon Indicates whether to show a phone icon for the button.
     */
    public void updateEmergencyCallButtonState(Button button, boolean shown, boolean showIcon) {
        if (isEmergencyCallCapable() && shown) {
            button.setVisibility(View.VISIBLE);
        } else {
            button.setVisibility(View.GONE);
            return;
        }

        int textId;
        if (isInCall()) {
            // show "return to call" text and show phone icon
            textId = R.string.lockscreen_return_to_call;
            int phoneCallIcon = showIcon ? R.drawable.stat_sys_phone_call : 0;
            button.setCompoundDrawablesWithIntrinsicBounds(phoneCallIcon, 0, 0, 0);
        } else {
            textId = R.string.lockscreen_emergency_call;
            int emergencyIcon = showIcon ? R.drawable.ic_emergency : 0;
            button.setCompoundDrawablesWithIntrinsicBounds(emergencyIcon, 0, 0, 0);
        }
        button.setText(textId);
    }

    /**
     * Resumes a call in progress. Typically launched from the EmergencyCall button
     * on various lockscreens.
     */
    public void resumeCall() {
        getTelecommManager().showInCallScreen(false);
    }

    /**
     * @return {@code true} if there is a call currently in progress, {@code false} otherwise.
     */
    public boolean isInCall() {
        return getTelecommManager().isInCall();
    }

    private TelecomManager getTelecommManager() {
        return (TelecomManager) mContext.getSystemService(Context.TELECOM_SERVICE);
    }

    private void finishBiometricWeak(int userId) {
        setBoolean(BIOMETRIC_WEAK_EVER_CHOSEN_KEY, true, userId);

        // Launch intent to show final screen, this also
        // moves the temporary gallery to the actual gallery
        Intent intent = new Intent();
        intent.setClassName("com.android.facelock",
                "com.android.facelock.SetupEndScreen");
        mContext.startActivityAsUser(intent, new UserHandle(userId));
    }

    public void setPowerButtonInstantlyLocks(boolean enabled) {
        setBoolean(LOCKSCREEN_POWER_BUTTON_INSTANTLY_LOCKS, enabled);
    }

    public boolean getPowerButtonInstantlyLocks() {
        return getBoolean(LOCKSCREEN_POWER_BUTTON_INSTANTLY_LOCKS, true);
    }

    public static boolean isSafeModeEnabled() {
        try {
            return IWindowManager.Stub.asInterface(
                    ServiceManager.getService("window")).isSafeModeEnabled();
        } catch (RemoteException e) {
            // Shouldn't happen!
        }
        return false;
    }

    /**
     * Determine whether the user has selected any non-system widgets in keyguard
     *
     * @return true if widgets have been selected
     */
    public boolean hasWidgetsEnabledInKeyguard(int userid) {
        int widgets[] = getAppWidgets(userid);
        for (int i = 0; i < widgets.length; i++) {
            if (widgets[i] > 0) {
                return true;
            }
        }
        return false;
    }

    public boolean getWidgetsEnabled() {
        return getWidgetsEnabled(getCurrentOrCallingUserId());
    }

    public boolean getWidgetsEnabled(int userId) {
        return getBoolean(LOCKSCREEN_WIDGETS_ENABLED, false, userId);
    }

    public void setWidgetsEnabled(boolean enabled) {
        setWidgetsEnabled(enabled, getCurrentOrCallingUserId());
    }

    public void setWidgetsEnabled(boolean enabled, int userId) {
        setBoolean(LOCKSCREEN_WIDGETS_ENABLED, enabled, userId);
    }

    public void setEnabledTrustAgents(Collection<ComponentName> activeTrustAgents) {
        setEnabledTrustAgents(activeTrustAgents, getCurrentOrCallingUserId());
    }

    public List<ComponentName> getEnabledTrustAgents() {
        return getEnabledTrustAgents(getCurrentOrCallingUserId());
    }

    public void setEnabledTrustAgents(Collection<ComponentName> activeTrustAgents, int userId) {
        StringBuilder sb = new StringBuilder();
        for (ComponentName cn : activeTrustAgents) {
            if (sb.length() > 0) {
                sb.append(',');
            }
            sb.append(cn.flattenToShortString());
        }
        setString(ENABLED_TRUST_AGENTS, sb.toString(), userId);
        getTrustManager().reportEnabledTrustAgentsChanged(getCurrentOrCallingUserId());
    }

    public List<ComponentName> getEnabledTrustAgents(int userId) {
        String serialized = getString(ENABLED_TRUST_AGENTS, userId);
        if (TextUtils.isEmpty(serialized)) {
            return null;
        }
        String[] split = serialized.split(",");
        ArrayList<ComponentName> activeTrustAgents = new ArrayList<ComponentName>(split.length);
        for (String s : split) {
            if (!TextUtils.isEmpty(s)) {
                activeTrustAgents.add(ComponentName.unflattenFromString(s));
            }
        }
        return activeTrustAgents;
    }

    /**
     * @see android.app.trust.TrustManager#reportRequireCredentialEntry(int)
     */
    public void requireCredentialEntry(int userId) {
        getTrustManager().reportRequireCredentialEntry(userId);
    }

    private void onAfterChangingPassword(int userHandle) {
        getTrustManager().reportEnabledTrustAgentsChanged(userHandle);
    }

    public boolean isCredentialRequiredToDecrypt(boolean defaultValue) {
        final int value = Settings.Global.getInt(mContentResolver,
                Settings.Global.REQUIRE_PASSWORD_TO_DECRYPT, -1);
        return value == -1 ? defaultValue : (value != 0);
    }

    public void setCredentialRequiredToDecrypt(boolean required) {
        if (getCurrentUser() != UserHandle.USER_OWNER) {
            Log.w(TAG, "Only device owner may call setCredentialRequiredForDecrypt()");
            return;
        }
        Settings.Global.putInt(mContext.getContentResolver(),
                Settings.Global.REQUIRE_PASSWORD_TO_DECRYPT, required ? 1 : 0);
    }
}


File: core/java/com/android/internal/widget/LockPatternView.java
/*
 * Copyright (C) 2007 The Android Open Source Project
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

package com.android.internal.widget;


import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.ValueAnimator;
import android.content.Context;
import android.content.res.TypedArray;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Debug;
import android.os.Parcel;
import android.os.Parcelable;
import android.os.SystemClock;
import android.util.AttributeSet;
import android.view.HapticFeedbackConstants;
import android.view.MotionEvent;
import android.view.View;
import android.view.accessibility.AccessibilityManager;
import android.view.animation.AnimationUtils;
import android.view.animation.Interpolator;

import com.android.internal.R;
import com.android.internal.widget.LockPatternUtils;

import java.util.ArrayList;
import java.util.List;

/**
 * Displays and detects the user's unlock attempt, which is a drag of a finger
 * across regions of the screen.
 *
 * Is also capable of displaying a static pattern in "in progress", "wrong" or
 * "correct" states.
 */
public class LockPatternView extends View {
    // Aspect to use when rendering this view
    private static final int ASPECT_SQUARE = 0; // View will be the minimum of width/height
    private static final int ASPECT_LOCK_WIDTH = 1; // Fixed width; height will be minimum of (w,h)
    private static final int ASPECT_LOCK_HEIGHT = 2; // Fixed height; width will be minimum of (w,h)

    private static final boolean PROFILE_DRAWING = false;
    private CellState[][] mCellStates;

    private final int mDotSize;
    private final int mDotSizeActivated;
    private final int mPathWidth;

    private boolean mDrawingProfilingStarted = false;

    private Paint mPaint = new Paint();
    private Paint mPathPaint = new Paint();

    /**
     * How many milliseconds we spend animating each circle of a lock pattern
     * if the animating mode is set.  The entire animation should take this
     * constant * the length of the pattern to complete.
     */
    private static final int MILLIS_PER_CIRCLE_ANIMATING = 700;

    private byte mPatternSize = LockPatternUtils.PATTERN_SIZE_DEFAULT;

    /**
     * This can be used to avoid updating the display for very small motions or noisy panels.
     * It didn't seem to have much impact on the devices tested, so currently set to 0.
     */
    private static final float DRAG_THRESHHOLD = 0.0f;

    private OnPatternListener mOnPatternListener;
    private ArrayList<Cell> mPattern = new ArrayList<Cell>(mPatternSize * mPatternSize);

    /**
     * Lookup table for the circles of the pattern we are currently drawing.
     * This will be the cells of the complete pattern unless we are animating,
     * in which case we use this to hold the cells we are drawing for the in
     * progress animation.
     */
    private boolean[][] mPatternDrawLookup = new boolean[mPatternSize][mPatternSize];

    /**
     * the in progress point:
     * - during interaction: where the user's finger is
     * - during animation: the current tip of the animating line
     */
    private float mInProgressX = -1;
    private float mInProgressY = -1;

    private long mAnimatingPeriodStart;

    private DisplayMode mPatternDisplayMode = DisplayMode.Correct;
    private boolean mInputEnabled = true;
    private boolean mInStealthMode = false;
    private boolean mEnableHapticFeedback = true;
    private boolean mPatternInProgress = false;
    private boolean mVisibleDots = true;
    private boolean mShowErrorPath = true;

    private float mHitFactor = 0.6f;

    private float mSquareWidth;
    private float mSquareHeight;

    private final Path mCurrentPath = new Path();
    private final Rect mInvalidate = new Rect();
    private final Rect mTmpInvalidateRect = new Rect();

    private int mAspect;
    private int mRegularColor;
    private int mErrorColor;
    private int mSuccessColor;

    private Interpolator mFastOutSlowInInterpolator;
    private Interpolator mLinearOutSlowInInterpolator;

    private LockPatternUtils mLockPatternUtils;

    /**
     * Represents a cell in the matrix of the unlock pattern view.
     */
    public static class Cell {
        int row;
        int column;

        // keep # objects limited
        static Cell[][] sCells;
        static {
            updateSize(LockPatternUtils.PATTERN_SIZE_DEFAULT);
        }

        /**
         * @param row The row of the cell.
         * @param column The column of the cell.
         */
        private Cell(int row, int column, byte size) {
            checkRange(row, column, size);
            this.row = row;
            this.column = column;
        }

        public int getRow() {
            return row;
        }

        public int getColumn() {
            return column;
        }

        /**
         * @param row The row of the cell.
         * @param column The column of the cell.
         */
        public static synchronized Cell of(int row, int column, byte size) {
            checkRange(row, column, size);
            return sCells[row][column];
        }

        public static void updateSize(byte size) {
            sCells = new Cell[size][size];
            for (int i = 0; i < size; i++) {
                for (int j = 0; j < size; j++) {
                    sCells[i][j] = new Cell(i, j, size);
                }
            }
        }

        private static void checkRange(int row, int column, byte size) {
            if (row < 0 || row > size - 1) {
                throw new IllegalArgumentException("row must be in range 0-" + (size - 1));
            }
            if (column < 0 || column > size - 1) {
                throw new IllegalArgumentException("column must be in range 0-" + (size - 1));
            }
        }

        public String toString() {
            return "(row=" + row + ",clmn=" + column + ")";
        }
    }

    public static class CellState {
        public float scale = 1.0f;
        public float translateY = 0.0f;
        public float alpha = 1.0f;
        public float size;
        public float lineEndX = Float.MIN_VALUE;
        public float lineEndY = Float.MIN_VALUE;
        public ValueAnimator lineAnimator;
     }

    /**
     * How to display the current pattern.
     */
    public enum DisplayMode {

        /**
         * The pattern drawn is correct (i.e draw it in a friendly color)
         */
        Correct,

        /**
         * Animate the pattern (for demo, and help).
         */
        Animate,

        /**
         * The pattern is wrong (i.e draw a foreboding color)
         */
        Wrong
    }

    /**
     * The call back interface for detecting patterns entered by the user.
     */
    public static interface OnPatternListener {

        /**
         * A new pattern has begun.
         */
        void onPatternStart();

        /**
         * The pattern was cleared.
         */
        void onPatternCleared();

        /**
         * The user extended the pattern currently being drawn by one cell.
         * @param pattern The pattern with newly added cell.
         */
        void onPatternCellAdded(List<Cell> pattern);

        /**
         * A pattern was detected from the user.
         * @param pattern The pattern.
         */
        void onPatternDetected(List<Cell> pattern);
    }

    public LockPatternView(Context context) {
        this(context, null);
    }

    public LockPatternView(Context context, AttributeSet attrs) {
        super(context, attrs);

        TypedArray a = context.obtainStyledAttributes(attrs, R.styleable.LockPatternView);

        final String aspect = a.getString(R.styleable.LockPatternView_aspect);

        if ("square".equals(aspect)) {
            mAspect = ASPECT_SQUARE;
        } else if ("lock_width".equals(aspect)) {
            mAspect = ASPECT_LOCK_WIDTH;
        } else if ("lock_height".equals(aspect)) {
            mAspect = ASPECT_LOCK_HEIGHT;
        } else {
            mAspect = ASPECT_SQUARE;
        }

        setClickable(true);


        mPathPaint.setAntiAlias(true);
        mPathPaint.setDither(true);

        mRegularColor = getResources().getColor(R.color.lock_pattern_view_regular_color);
        mErrorColor = getResources().getColor(R.color.lock_pattern_view_error_color);
        mSuccessColor = getResources().getColor(R.color.lock_pattern_view_success_color);
        mRegularColor = a.getColor(R.styleable.LockPatternView_regularColor, mRegularColor);
        mErrorColor = a.getColor(R.styleable.LockPatternView_errorColor, mErrorColor);
        mSuccessColor = a.getColor(R.styleable.LockPatternView_successColor, mSuccessColor);

        int pathColor = a.getColor(R.styleable.LockPatternView_pathColor, mRegularColor);
        mPathPaint.setColor(pathColor);

        mPathPaint.setStyle(Paint.Style.STROKE);
        mPathPaint.setStrokeJoin(Paint.Join.ROUND);
        mPathPaint.setStrokeCap(Paint.Cap.ROUND);

        mPathWidth = getResources().getDimensionPixelSize(R.dimen.lock_pattern_dot_line_width);
        mPathPaint.setStrokeWidth(mPathWidth);

        mDotSize = getResources().getDimensionPixelSize(R.dimen.lock_pattern_dot_size);
        mDotSizeActivated = getResources().getDimensionPixelSize(
                R.dimen.lock_pattern_dot_size_activated);

        mPaint.setAntiAlias(true);
        mPaint.setDither(true);

        mCellStates = new CellState[mPatternSize][mPatternSize];
        for (int i = 0; i < mPatternSize; i++) {
            for (int j = 0; j < mPatternSize; j++) {
                mCellStates[i][j] = new CellState();
                mCellStates[i][j].size = mDotSize;
            }
        }

        mFastOutSlowInInterpolator =
                AnimationUtils.loadInterpolator(context, android.R.interpolator.fast_out_slow_in);
        mLinearOutSlowInInterpolator =
                AnimationUtils.loadInterpolator(context, android.R.interpolator.linear_out_slow_in);
    }

    public CellState[][] getCellStates() {
        return mCellStates;
    }

    /**
     * @return Whether the view is in stealth mode.
     */
    public boolean isInStealthMode() {
        return mInStealthMode;
    }

    /**
     * @return Whether the view has tactile feedback enabled.
     */
    public boolean isTactileFeedbackEnabled() {
        return mEnableHapticFeedback;
    }

    /**
     * @return the current pattern lockscreen size.
     */
    public int getLockPatternSize() {
        return mPatternSize;
    }

    /**
     * Set whether the view is in stealth mode.  If true, there will be no
     * visible feedback as the user enters the pattern.
     *
     * @param inStealthMode Whether in stealth mode.
     */
    public void setInStealthMode(boolean inStealthMode) {
        mInStealthMode = inStealthMode;
    }

    public void setVisibleDots(boolean visibleDots) {
        mVisibleDots = visibleDots;
    }

    public boolean isVisibleDots() {
        return mVisibleDots;
    }

    public void setShowErrorPath(boolean showErrorPath) {
        mShowErrorPath = showErrorPath;
    }

    public boolean isShowErrorPath() {
        return mShowErrorPath;
    }

    /**
     * Set whether the view will use tactile feedback.  If true, there will be
     * tactile feedback as the user enters the pattern.
     *
     * @param tactileFeedbackEnabled Whether tactile feedback is enabled
     */
    public void setTactileFeedbackEnabled(boolean tactileFeedbackEnabled) {
        mEnableHapticFeedback = tactileFeedbackEnabled;
    }

    /**
     * Set the pattern size of the lockscreen
     *
     * @param size The pattern size.
     */
    public void setLockPatternSize(byte size) {
        mPatternSize = size;
        Cell.updateSize(size);
        mCellStates = new CellState[mPatternSize][mPatternSize];
        for (int i = 0; i < mPatternSize; i++) {
            for (int j = 0; j < mPatternSize; j++) {
                mCellStates[i][j] = new CellState();
                mCellStates[i][j].size = mDotSize;
            }
        }
        mPattern = new ArrayList<Cell>(size * size);
        mPatternDrawLookup = new boolean[size][size];
    }

    /**
     * Set the LockPatternUtil instance used to encode a pattern to a string
     * @param utils The instance.
     */
    public void setLockPatternUtils(LockPatternUtils utils) {
        mLockPatternUtils = utils;
    }

    /**
     * Set the call back for pattern detection.
     * @param onPatternListener The call back.
     */
    public void setOnPatternListener(
            OnPatternListener onPatternListener) {
        mOnPatternListener = onPatternListener;
    }

    /**
     * Set the pattern explicitely (rather than waiting for the user to input
     * a pattern).
     * @param displayMode How to display the pattern.
     * @param pattern The pattern.
     */
    public void setPattern(DisplayMode displayMode, List<Cell> pattern) {
        mPattern.clear();
        mPattern.addAll(pattern);
        clearPatternDrawLookup();
        for (Cell cell : pattern) {
            mPatternDrawLookup[cell.getRow()][cell.getColumn()] = true;
        }

        setDisplayMode(displayMode);
    }

    /**
     * Set the display mode of the current pattern.  This can be useful, for
     * instance, after detecting a pattern to tell this view whether change the
     * in progress result to correct or wrong.
     * @param displayMode The display mode.
     */
    public void setDisplayMode(DisplayMode displayMode) {
        mPatternDisplayMode = displayMode;
        if (displayMode == DisplayMode.Animate) {
            if (mPattern.size() == 0) {
                throw new IllegalStateException("you must have a pattern to "
                        + "animate if you want to set the display mode to animate");
            }
            mAnimatingPeriodStart = SystemClock.elapsedRealtime();
            final Cell first = mPattern.get(0);
            mInProgressX = getCenterXForColumn(first.getColumn());
            mInProgressY = getCenterYForRow(first.getRow());
            clearPatternDrawLookup();
        }
        invalidate();
    }

    private void notifyCellAdded() {
        sendAccessEvent(R.string.lockscreen_access_pattern_cell_added);
        if (mOnPatternListener != null) {
            mOnPatternListener.onPatternCellAdded(mPattern);
        }
    }

    private void notifyPatternStarted() {
        sendAccessEvent(R.string.lockscreen_access_pattern_start);
        if (mOnPatternListener != null) {
            mOnPatternListener.onPatternStart();
        }
    }

    private void notifyPatternDetected() {
        sendAccessEvent(R.string.lockscreen_access_pattern_detected);
        if (mOnPatternListener != null) {
            mOnPatternListener.onPatternDetected(mPattern);
        }
    }

    private void notifyPatternCleared() {
        sendAccessEvent(R.string.lockscreen_access_pattern_cleared);
        if (mOnPatternListener != null) {
            mOnPatternListener.onPatternCleared();
        }
    }

    /**
     * Clear the pattern.
     */
    public void clearPattern() {
        resetPattern();
    }

    /**
     * Reset all pattern state.
     */
    private void resetPattern() {
        mPattern.clear();
        clearPatternDrawLookup();
        mPatternDisplayMode = DisplayMode.Correct;
        invalidate();
    }

    /**
     * Clear the pattern lookup table.
     */
    private void clearPatternDrawLookup() {
        for (int i = 0; i < mPatternSize; i++) {
            for (int j = 0; j < mPatternSize; j++) {
                mPatternDrawLookup[i][j] = false;
            }
        }
    }

    /**
     * Disable input (for instance when displaying a message that will
     * timeout so user doesn't get view into messy state).
     */
    public void disableInput() {
        mInputEnabled = false;
    }

    /**
     * Enable input.
     */
    public void enableInput() {
        mInputEnabled = true;
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        final int width = w - mPaddingLeft - mPaddingRight;
        mSquareWidth = width / (float) mPatternSize;

        final int height = h - mPaddingTop - mPaddingBottom;
        mSquareHeight = height / (float) mPatternSize;
    }

    private int resolveMeasured(int measureSpec, int desired)
    {
        int result = 0;
        int specSize = MeasureSpec.getSize(measureSpec);
        switch (MeasureSpec.getMode(measureSpec)) {
            case MeasureSpec.UNSPECIFIED:
                result = desired;
                break;
            case MeasureSpec.AT_MOST:
                result = Math.max(specSize, desired);
                break;
            case MeasureSpec.EXACTLY:
            default:
                result = specSize;
        }
        return result;
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        final int minimumWidth = getSuggestedMinimumWidth();
        final int minimumHeight = getSuggestedMinimumHeight();
        int viewWidth = resolveMeasured(widthMeasureSpec, minimumWidth);
        int viewHeight = resolveMeasured(heightMeasureSpec, minimumHeight);

        switch (mAspect) {
            case ASPECT_SQUARE:
                viewWidth = viewHeight = Math.min(viewWidth, viewHeight);
                break;
            case ASPECT_LOCK_WIDTH:
                viewHeight = Math.min(viewWidth, viewHeight);
                break;
            case ASPECT_LOCK_HEIGHT:
                viewWidth = Math.min(viewWidth, viewHeight);
                break;
        }
        // Log.v(TAG, "LockPatternView dimensions: " + viewWidth + "x" + viewHeight);
        setMeasuredDimension(viewWidth, viewHeight);
    }

    /**
     * Determines whether the point x, y will add a new point to the current
     * pattern (in addition to finding the cell, also makes heuristic choices
     * such as filling in gaps based on current pattern).
     * @param x The x coordinate.
     * @param y The y coordinate.
     */
    private Cell detectAndAddHit(float x, float y) {
        final Cell cell = checkForNewHit(x, y);
        if (cell != null) {

            // check for gaps in existing pattern
            final ArrayList<Cell> pattern = mPattern;
            if (!pattern.isEmpty()) {
                final Cell lastCell = pattern.get(pattern.size() - 1);
                int dRow = cell.row - lastCell.row;
                int dColumn = cell.column - lastCell.column;

                int fillInRow = lastCell.row;
                int fillInColumn = lastCell.column;

                if (dRow == 0 || dColumn == 0 || Math.abs(dRow) == Math.abs(dColumn)) {
                    while (true) {
                        fillInRow += Integer.signum(dRow);
                        fillInColumn += Integer.signum(dColumn);
                        if (fillInRow == cell.row && fillInColumn == cell.column) break;
                        Cell fillInGapCell = Cell.of(fillInRow, fillInColumn, mPatternSize);
                        if (!mPatternDrawLookup[fillInGapCell.row][fillInGapCell.column]) {
                            addCellToPattern(fillInGapCell);
                        }
                    }
                }
            }

            addCellToPattern(cell);
            if (mEnableHapticFeedback) {
                performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY,
                        HapticFeedbackConstants.FLAG_IGNORE_VIEW_SETTING
                        | HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING);
            }
            return cell;
        }
        return null;
    }

    private void addCellToPattern(Cell newCell) {
        mPatternDrawLookup[newCell.getRow()][newCell.getColumn()] = true;
        mPattern.add(newCell);
        if (!mInStealthMode) {
            startCellActivatedAnimation(newCell);
        }
        notifyCellAdded();
    }

    private void startCellActivatedAnimation(Cell cell) {
        final CellState cellState = mCellStates[cell.row][cell.column];
        startSizeAnimation(mDotSize, mDotSizeActivated, 96, mLinearOutSlowInInterpolator,
                cellState, new Runnable() {
            @Override
            public void run() {
                startSizeAnimation(mDotSizeActivated, mDotSize, 192, mFastOutSlowInInterpolator,
                        cellState, null);
            }
        });
        startLineEndAnimation(cellState, mInProgressX, mInProgressY,
                getCenterXForColumn(cell.column), getCenterYForRow(cell.row));
    }

    private void startLineEndAnimation(final CellState state,
            final float startX, final float startY, final float targetX, final float targetY) {
        ValueAnimator valueAnimator = ValueAnimator.ofFloat(0, 1);
        valueAnimator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override
            public void onAnimationUpdate(ValueAnimator animation) {
                float t = (float) animation.getAnimatedValue();
                state.lineEndX = (1 - t) * startX + t * targetX;
                state.lineEndY = (1 - t) * startY + t * targetY;
                invalidate();
            }
        });
        valueAnimator.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator animation) {
                state.lineAnimator = null;
            }
        });
        valueAnimator.setInterpolator(mFastOutSlowInInterpolator);
        valueAnimator.setDuration(100);
        valueAnimator.start();
        state.lineAnimator = valueAnimator;
    }

    private void startSizeAnimation(float start, float end, long duration, Interpolator interpolator,
            final CellState state, final Runnable endRunnable) {
        ValueAnimator valueAnimator = ValueAnimator.ofFloat(start, end);
        valueAnimator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override
            public void onAnimationUpdate(ValueAnimator animation) {
                state.size = (float) animation.getAnimatedValue();
                invalidate();
            }
        });
        if (endRunnable != null) {
            valueAnimator.addListener(new AnimatorListenerAdapter() {
                @Override
                public void onAnimationEnd(Animator animation) {
                    endRunnable.run();
                }
            });
        }
        valueAnimator.setInterpolator(interpolator);
        valueAnimator.setDuration(duration);
        valueAnimator.start();
    }

    // helper method to find which cell a point maps to
    private Cell checkForNewHit(float x, float y) {

        final int rowHit = getRowHit(y);
        if (rowHit < 0) {
            return null;
        }
        final int columnHit = getColumnHit(x);
        if (columnHit < 0) {
            return null;
        }

        if (mPatternDrawLookup[rowHit][columnHit]) {
            return null;
        }
        return Cell.of(rowHit, columnHit, mPatternSize);
    }

    /**
     * Helper method to find the row that y falls into.
     * @param y The y coordinate
     * @return The row that y falls in, or -1 if it falls in no row.
     */
    private int getRowHit(float y) {

        final float squareHeight = mSquareHeight;
        float hitSize = squareHeight * mHitFactor;

        float offset = mPaddingTop + (squareHeight - hitSize) / 2f;
        for (int i = 0; i < mPatternSize; i++) {

            final float hitTop = offset + squareHeight * i;
            if (y >= hitTop && y <= hitTop + hitSize) {
                return i;
            }
        }
        return -1;
    }

    /**
     * Helper method to find the column x fallis into.
     * @param x The x coordinate.
     * @return The column that x falls in, or -1 if it falls in no column.
     */
    private int getColumnHit(float x) {
        final float squareWidth = mSquareWidth;
        float hitSize = squareWidth * mHitFactor;

        float offset = mPaddingLeft + (squareWidth - hitSize) / 2f;
        for (int i = 0; i < mPatternSize; i++) {

            final float hitLeft = offset + squareWidth * i;
            if (x >= hitLeft && x <= hitLeft + hitSize) {
                return i;
            }
        }
        return -1;
    }

    @Override
    public boolean onHoverEvent(MotionEvent event) {
        if (AccessibilityManager.getInstance(mContext).isTouchExplorationEnabled()) {
            final int action = event.getAction();
            switch (action) {
                case MotionEvent.ACTION_HOVER_ENTER:
                    event.setAction(MotionEvent.ACTION_DOWN);
                    break;
                case MotionEvent.ACTION_HOVER_MOVE:
                    event.setAction(MotionEvent.ACTION_MOVE);
                    break;
                case MotionEvent.ACTION_HOVER_EXIT:
                    event.setAction(MotionEvent.ACTION_UP);
                    break;
            }
            onTouchEvent(event);
            event.setAction(action);
        }
        return super.onHoverEvent(event);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (!mInputEnabled || !isEnabled()) {
            return false;
        }

        switch(event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                handleActionDown(event);
                return true;
            case MotionEvent.ACTION_UP:
                handleActionUp(event);
                return true;
            case MotionEvent.ACTION_MOVE:
                handleActionMove(event);
                return true;
            case MotionEvent.ACTION_CANCEL:
                if (mPatternInProgress) {
                    mPatternInProgress = false;
                    resetPattern();
                    notifyPatternCleared();
                }
                if (PROFILE_DRAWING) {
                    if (mDrawingProfilingStarted) {
                        Debug.stopMethodTracing();
                        mDrawingProfilingStarted = false;
                    }
                }
                return true;
        }
        return false;
    }

    private void handleActionMove(MotionEvent event) {
        // Handle all recent motion events so we don't skip any cells even when the device
        // is busy...
        final float radius = mPathWidth;
        final int historySize = event.getHistorySize();
        mTmpInvalidateRect.setEmpty();
        boolean invalidateNow = false;
        for (int i = 0; i < historySize + 1; i++) {
            final float x = i < historySize ? event.getHistoricalX(i) : event.getX();
            final float y = i < historySize ? event.getHistoricalY(i) : event.getY();
            Cell hitCell = detectAndAddHit(x, y);
            final int patternSize = mPattern.size();
            if (hitCell != null && patternSize == 1) {
                mPatternInProgress = true;
                notifyPatternStarted();
            }
            // note current x and y for rubber banding of in progress patterns
            final float dx = Math.abs(x - mInProgressX);
            final float dy = Math.abs(y - mInProgressY);
            if (dx > DRAG_THRESHHOLD || dy > DRAG_THRESHHOLD) {
                invalidateNow = true;
            }

            if (mPatternInProgress && patternSize > 0) {
                final ArrayList<Cell> pattern = mPattern;
                final Cell lastCell = pattern.get(patternSize - 1);
                float lastCellCenterX = getCenterXForColumn(lastCell.column);
                float lastCellCenterY = getCenterYForRow(lastCell.row);

                // Adjust for drawn segment from last cell to (x,y). Radius accounts for line width.
                float left = Math.min(lastCellCenterX, x) - radius;
                float right = Math.max(lastCellCenterX, x) + radius;
                float top = Math.min(lastCellCenterY, y) - radius;
                float bottom = Math.max(lastCellCenterY, y) + radius;

                // Invalidate between the pattern's new cell and the pattern's previous cell
                if (hitCell != null) {
                    final float width = mSquareWidth * 0.5f;
                    final float height = mSquareHeight * 0.5f;
                    final float hitCellCenterX = getCenterXForColumn(hitCell.column);
                    final float hitCellCenterY = getCenterYForRow(hitCell.row);

                    left = Math.min(hitCellCenterX - width, left);
                    right = Math.max(hitCellCenterX + width, right);
                    top = Math.min(hitCellCenterY - height, top);
                    bottom = Math.max(hitCellCenterY + height, bottom);
                }

                // Invalidate between the pattern's last cell and the previous location
                mTmpInvalidateRect.union(Math.round(left), Math.round(top),
                        Math.round(right), Math.round(bottom));
            }
        }
        mInProgressX = event.getX();
        mInProgressY = event.getY();

        // To save updates, we only invalidate if the user moved beyond a certain amount.
        if (invalidateNow) {
            mInvalidate.union(mTmpInvalidateRect);
            invalidate(mInvalidate);
            mInvalidate.set(mTmpInvalidateRect);
        }
    }

    private void sendAccessEvent(int resId) {
        announceForAccessibility(mContext.getString(resId));
    }

    private void handleActionUp(MotionEvent event) {
        // report pattern detected
        if (!mPattern.isEmpty()) {
            mPatternInProgress = false;
            cancelLineAnimations();
            notifyPatternDetected();
            invalidate();
        }
        if (PROFILE_DRAWING) {
            if (mDrawingProfilingStarted) {
                Debug.stopMethodTracing();
                mDrawingProfilingStarted = false;
            }
        }
    }

    private void cancelLineAnimations() {
        for (int i = 0; i < mPatternSize; i++) {
            for (int j = 0; j < mPatternSize; j++) {
                CellState state = mCellStates[i][j];
                if (state.lineAnimator != null) {
                    state.lineAnimator.cancel();
                    state.lineEndX = Float.MIN_VALUE;
                    state.lineEndY = Float.MIN_VALUE;
                }
            }
        }
    }
    private void handleActionDown(MotionEvent event) {
        resetPattern();
        final float x = event.getX();
        final float y = event.getY();
        final Cell hitCell = detectAndAddHit(x, y);
        if (hitCell != null) {
            mPatternInProgress = true;
            mPatternDisplayMode = DisplayMode.Correct;
            notifyPatternStarted();
        } else if (mPatternInProgress) {
            mPatternInProgress = false;
            notifyPatternCleared();
        }
        if (hitCell != null) {
            final float startX = getCenterXForColumn(hitCell.column);
            final float startY = getCenterYForRow(hitCell.row);

            final float widthOffset = mSquareWidth / 2f;
            final float heightOffset = mSquareHeight / 2f;

            invalidate((int) (startX - widthOffset), (int) (startY - heightOffset),
                    (int) (startX + widthOffset), (int) (startY + heightOffset));
        }
        mInProgressX = x;
        mInProgressY = y;
        if (PROFILE_DRAWING) {
            if (!mDrawingProfilingStarted) {
                Debug.startMethodTracing("LockPatternDrawing");
                mDrawingProfilingStarted = true;
            }
        }
    }

    private float getCenterXForColumn(int column) {
        return mPaddingLeft + column * mSquareWidth + mSquareWidth / 2f;
    }

    private float getCenterYForRow(int row) {
        return mPaddingTop + row * mSquareHeight + mSquareHeight / 2f;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        final ArrayList<Cell> pattern = mPattern;
        final int count = pattern.size();
        final boolean[][] drawLookup = mPatternDrawLookup;

        if (mPatternDisplayMode == DisplayMode.Animate) {

            // figure out which circles to draw

            // + 1 so we pause on complete pattern
            final int oneCycle = (count + 1) * MILLIS_PER_CIRCLE_ANIMATING;
            final int spotInCycle = (int) (SystemClock.elapsedRealtime() -
                    mAnimatingPeriodStart) % oneCycle;
            final int numCircles = spotInCycle / MILLIS_PER_CIRCLE_ANIMATING;

            clearPatternDrawLookup();
            for (int i = 0; i < numCircles; i++) {
                final Cell cell = pattern.get(i);
                drawLookup[cell.getRow()][cell.getColumn()] = true;
            }

            // figure out in progress portion of ghosting line

            final boolean needToUpdateInProgressPoint = numCircles > 0
                    && numCircles < count;

            if (needToUpdateInProgressPoint) {
                final float percentageOfNextCircle =
                        ((float) (spotInCycle % MILLIS_PER_CIRCLE_ANIMATING)) /
                                MILLIS_PER_CIRCLE_ANIMATING;

                final Cell currentCell = pattern.get(numCircles - 1);
                final float centerX = getCenterXForColumn(currentCell.column);
                final float centerY = getCenterYForRow(currentCell.row);

                final Cell nextCell = pattern.get(numCircles);
                final float dx = percentageOfNextCircle *
                        (getCenterXForColumn(nextCell.column) - centerX);
                final float dy = percentageOfNextCircle *
                        (getCenterYForRow(nextCell.row) - centerY);
                mInProgressX = centerX + dx;
                mInProgressY = centerY + dy;
            }
            // TODO: Infinite loop here...
            invalidate();
        }

        final Path currentPath = mCurrentPath;
        currentPath.rewind();

        // draw the circles
        for (int i = 0; i < mPatternSize; i++) {
            float centerY = getCenterYForRow(i);
            for (int j = 0; j < mPatternSize; j++) {
                CellState cellState = mCellStates[i][j];
                float centerX = getCenterXForColumn(j);
                float size = cellState.size * cellState.scale;
                float translationY = cellState.translateY;
                drawCircle(canvas, (int) centerX, (int) centerY + translationY,
                        size, drawLookup[i][j], cellState.alpha);
            }
        }

        // TODO: the path should be created and cached every time we hit-detect a cell
        // only the last segment of the path should be computed here
        // draw the path of the pattern (unless we are in stealth mode)
        final boolean drawPath = ((!mInStealthMode && mPatternDisplayMode != DisplayMode.Wrong)
                || (mPatternDisplayMode == DisplayMode.Wrong && mShowErrorPath));
        if (drawPath) {
            mPathPaint.setColor(getCurrentColor(true /* partOfPattern */));

            boolean anyCircles = false;
            float lastX = 0f;
            float lastY = 0f;
            for (int i = 0; i < count; i++) {
                Cell cell = pattern.get(i);

                // only draw the part of the pattern stored in
                // the lookup table (this is only different in the case
                // of animation).
                if (!drawLookup[cell.row][cell.column]) {
                    break;
                }
                anyCircles = true;

                float centerX = getCenterXForColumn(cell.column);
                float centerY = getCenterYForRow(cell.row);
                if (i != 0) {
                    CellState state = mCellStates[cell.row][cell.column];
                    currentPath.rewind();
                    currentPath.moveTo(lastX, lastY);
                    if (state.lineEndX != Float.MIN_VALUE && state.lineEndY != Float.MIN_VALUE) {
                        currentPath.lineTo(state.lineEndX, state.lineEndY);
                    } else {
                        currentPath.lineTo(centerX, centerY);
                    }
                    canvas.drawPath(currentPath, mPathPaint);
                }
                lastX = centerX;
                lastY = centerY;
            }

            // draw last in progress section
            if ((mPatternInProgress || mPatternDisplayMode == DisplayMode.Animate)
                    && anyCircles) {
                currentPath.rewind();
                currentPath.moveTo(lastX, lastY);
                currentPath.lineTo(mInProgressX, mInProgressY);

                mPathPaint.setAlpha((int) (calculateLastSegmentAlpha(
                        mInProgressX, mInProgressY, lastX, lastY) * 255f));
                canvas.drawPath(currentPath, mPathPaint);
            }
        }
    }

    private float calculateLastSegmentAlpha(float x, float y, float lastX, float lastY) {
        float diffX = x - lastX;
        float diffY = y - lastY;
        float dist = (float) Math.sqrt(diffX*diffX + diffY*diffY);
        float frac = dist/mSquareWidth;
        return Math.min(1f, Math.max(0f, (frac - 0.3f) * 4f));
    }

    private int getCurrentColor(boolean partOfPattern) {
        if (!partOfPattern || (mInStealthMode && mPatternDisplayMode != DisplayMode.Wrong)
                || (mPatternDisplayMode == DisplayMode.Wrong && !mShowErrorPath)
                || mPatternInProgress) {
            // unselected circle
            return mRegularColor;
        } else if (mPatternDisplayMode == DisplayMode.Wrong) {
            // the pattern is wrong
            return mErrorColor;
        } else if (mPatternDisplayMode == DisplayMode.Correct ||
                mPatternDisplayMode == DisplayMode.Animate) {
            return mSuccessColor;
        } else {
            throw new IllegalStateException("unknown display mode " + mPatternDisplayMode);
        }
    }

    /**
     * @param partOfPattern Whether this circle is part of the pattern.
     */
    private void drawCircle(Canvas canvas, float centerX, float centerY, float size,
            boolean partOfPattern, float alpha) {
        if (!mVisibleDots) {
            return;
        }
        mPaint.setColor(getCurrentColor(partOfPattern));
        mPaint.setAlpha((int) (alpha * 255));
        canvas.drawCircle(centerX, centerY, size/2, mPaint);
    }

    @Override
    protected Parcelable onSaveInstanceState() {
        Parcelable superState = super.onSaveInstanceState();
        return new SavedState(superState,
                LockPatternUtils.patternToString(mPattern, mPatternSize),
                mPatternDisplayMode.ordinal(), mPatternSize,
                mInputEnabled, mInStealthMode, mEnableHapticFeedback, mVisibleDots, mShowErrorPath);
    }

    @Override
    protected void onRestoreInstanceState(Parcelable state) {
        final SavedState ss = (SavedState) state;
        super.onRestoreInstanceState(ss.getSuperState());
        setPattern(
                DisplayMode.Correct,
                mLockPatternUtils.stringToPattern(ss.getSerializedPattern()));
        mPatternDisplayMode = DisplayMode.values()[ss.getDisplayMode()];
        mPatternSize = ss.getPatternSize();
        mInputEnabled = ss.isInputEnabled();
        mInStealthMode = ss.isInStealthMode();
        mEnableHapticFeedback = ss.isTactileFeedbackEnabled();
        mVisibleDots = ss.isVisibleDots();
        mShowErrorPath = ss.isShowErrorPath();
    }

    /**
     * The parecelable for saving and restoring a lock pattern view.
     */
    private static class SavedState extends BaseSavedState {

        private final String mSerializedPattern;
        private final int mDisplayMode;
        private final byte mPatternSize;
        private final boolean mInputEnabled;
        private final boolean mInStealthMode;
        private final boolean mTactileFeedbackEnabled;
        private final boolean mVisibleDots;
        private final boolean mShowErrorPath;

        /**
         * Constructor called from {@link LockPatternView#onSaveInstanceState()}
         */
        private SavedState(Parcelable superState, String serializedPattern, int displayMode,
                byte patternSize, boolean inputEnabled, boolean inStealthMode,
                boolean tactileFeedbackEnabled, boolean visibleDots, boolean showErrorPath) {
            super(superState);
            mSerializedPattern = serializedPattern;
            mDisplayMode = displayMode;
            mPatternSize = patternSize;
            mInputEnabled = inputEnabled;
            mInStealthMode = inStealthMode;
            mTactileFeedbackEnabled = tactileFeedbackEnabled;
            mVisibleDots = visibleDots;
            mShowErrorPath = showErrorPath;
        }

        /**
         * Constructor called from {@link #CREATOR}
         */
        private SavedState(Parcel in) {
            super(in);
            mSerializedPattern = in.readString();
            mDisplayMode = in.readInt();
            mPatternSize = (byte) in.readByte();
            mInputEnabled = (Boolean) in.readValue(null);
            mInStealthMode = (Boolean) in.readValue(null);
            mTactileFeedbackEnabled = (Boolean) in.readValue(null);
            mVisibleDots = (Boolean) in.readValue(null);
            mShowErrorPath = (Boolean) in.readValue(null);
        }

        public String getSerializedPattern() {
            return mSerializedPattern;
        }

        public int getDisplayMode() {
            return mDisplayMode;
        }

        public byte getPatternSize() {
            return mPatternSize;
        }

        public boolean isInputEnabled() {
            return mInputEnabled;
        }

        public boolean isInStealthMode() {
            return mInStealthMode;
        }

        public boolean isTactileFeedbackEnabled(){
            return mTactileFeedbackEnabled;
        }

        public boolean isVisibleDots() {
            return mVisibleDots;
        }

        public boolean isShowErrorPath() {
            return mShowErrorPath;
        }

        @Override
        public void writeToParcel(Parcel dest, int flags) {
            super.writeToParcel(dest, flags);
            dest.writeString(mSerializedPattern);
            dest.writeInt(mDisplayMode);
            dest.writeByte(mPatternSize);
            dest.writeValue(mInputEnabled);
            dest.writeValue(mInStealthMode);
            dest.writeValue(mTactileFeedbackEnabled);
            dest.writeValue(mVisibleDots);
            dest.writeValue(mShowErrorPath);
        }

        public static final Parcelable.Creator<SavedState> CREATOR =
                new Creator<SavedState>() {
                    public SavedState createFromParcel(Parcel in) {
                        return new SavedState(in);
                    }

                    public SavedState[] newArray(int size) {
                        return new SavedState[size];
                    }
                };
    }
}
