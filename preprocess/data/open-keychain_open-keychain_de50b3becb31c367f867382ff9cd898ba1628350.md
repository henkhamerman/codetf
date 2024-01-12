Refactoring Types: ['Extract Method']
/sufficientlysecure/keychain/ui/EditKeyFragment.java
/*
 * Copyright (C) 2014 Dominik Schürmann <dominik@dominikschuermann.de>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.sufficientlysecure.keychain.ui;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Message;
import android.os.Messenger;
import android.support.v4.app.LoaderManager;
import android.support.v4.content.CursorLoader;
import android.support.v4.content.Loader;
import android.view.LayoutInflater;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ListView;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.compatibility.DialogFragmentWorkaround;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult.LogType;
import org.sufficientlysecure.keychain.operations.results.SingletonResult;
import org.sufficientlysecure.keychain.pgp.CanonicalizedSecretKey.SecretKeyType;
import org.sufficientlysecure.keychain.pgp.KeyRing;
import org.sufficientlysecure.keychain.pgp.exception.PgpKeyNotFoundException;
import org.sufficientlysecure.keychain.provider.CachedPublicKeyRing;
import org.sufficientlysecure.keychain.provider.KeychainContract;
import org.sufficientlysecure.keychain.provider.KeychainContract.UserPackets;
import org.sufficientlysecure.keychain.provider.ProviderHelper;
import org.sufficientlysecure.keychain.provider.ProviderHelper.NotFoundException;
import org.sufficientlysecure.keychain.service.SaveKeyringParcel;
import org.sufficientlysecure.keychain.service.SaveKeyringParcel.ChangeUnlockParcel;
import org.sufficientlysecure.keychain.service.SaveKeyringParcel.SubkeyChange;
import org.sufficientlysecure.keychain.service.input.CryptoInputParcel;
import org.sufficientlysecure.keychain.ui.adapter.SubkeysAdapter;
import org.sufficientlysecure.keychain.ui.adapter.SubkeysAddedAdapter;
import org.sufficientlysecure.keychain.ui.adapter.UserIdsAdapter;
import org.sufficientlysecure.keychain.ui.adapter.UserIdsAddedAdapter;
import org.sufficientlysecure.keychain.ui.base.NewCryptoOperationFragment;
import org.sufficientlysecure.keychain.ui.dialog.AddSubkeyDialogFragment;
import org.sufficientlysecure.keychain.ui.dialog.AddUserIdDialogFragment;
import org.sufficientlysecure.keychain.ui.dialog.EditSubkeyDialogFragment;
import org.sufficientlysecure.keychain.ui.dialog.EditSubkeyExpiryDialogFragment;
import org.sufficientlysecure.keychain.ui.dialog.EditUserIdDialogFragment;
import org.sufficientlysecure.keychain.ui.dialog.SetPassphraseDialogFragment;
import org.sufficientlysecure.keychain.ui.util.Notify;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.Passphrase;
import org.sufficientlysecure.keychain.util.operation.OperationHelper;

public class EditKeyFragment extends NewCryptoOperationFragment<SaveKeyringParcel, OperationResult>
        implements LoaderManager.LoaderCallbacks<Cursor> {

    public static final String ARG_DATA_URI = "uri";
    public static final String ARG_SAVE_KEYRING_PARCEL = "save_keyring_parcel";

    private ListView mUserIdsList;
    private ListView mSubkeysList;
    private ListView mUserIdsAddedList;
    private ListView mSubkeysAddedList;
    private View mChangePassphrase;
    private View mAddUserId;
    private View mAddSubkey;

    private static final int LOADER_ID_USER_IDS = 0;
    private static final int LOADER_ID_SUBKEYS = 1;

    // cursor adapter
    private UserIdsAdapter mUserIdsAdapter;
    private SubkeysAdapter mSubkeysAdapter;

    // array adapter
    private UserIdsAddedAdapter mUserIdsAddedAdapter;
    private SubkeysAddedAdapter mSubkeysAddedAdapter;

    private Uri mDataUri;

    private SaveKeyringParcel mSaveKeyringParcel;

    private String mPrimaryUserId;

    /**
     * Creates new instance of this fragment
     */
    public static EditKeyFragment newInstance(Uri dataUri) {
        EditKeyFragment frag = new EditKeyFragment();

        Bundle args = new Bundle();
        args.putParcelable(ARG_DATA_URI, dataUri);

        frag.setArguments(args);

        return frag;
    }

    public static EditKeyFragment newInstance(SaveKeyringParcel saveKeyringParcel) {
        EditKeyFragment frag = new EditKeyFragment();

        Bundle args = new Bundle();
        args.putParcelable(ARG_SAVE_KEYRING_PARCEL, saveKeyringParcel);

        frag.setArguments(args);

        return frag;
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup superContainer, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.edit_key_fragment, null);

        mUserIdsList = (ListView) view.findViewById(R.id.edit_key_user_ids);
        mSubkeysList = (ListView) view.findViewById(R.id.edit_key_keys);
        mUserIdsAddedList = (ListView) view.findViewById(R.id.edit_key_user_ids_added);
        mSubkeysAddedList = (ListView) view.findViewById(R.id.edit_key_subkeys_added);
        mChangePassphrase = view.findViewById(R.id.edit_key_action_change_passphrase);
        mAddUserId = view.findViewById(R.id.edit_key_action_add_user_id);
        mAddSubkey = view.findViewById(R.id.edit_key_action_add_key);

        return view;
    }

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);

        super.setOperationHelper(
                new OperationHelper<SaveKeyringParcel, OperationResult>(this) {

                    @Override
                    public SaveKeyringParcel createOperationInput() {
                        Log.d("PHILIP", "edit key creating operation input " + mSaveKeyringParcel);
                        return mSaveKeyringParcel;
                    }

                    @Override
                    protected void onCryptoOperationSuccess(OperationResult result) {
                        Log.d("PHILIP", "edit key success");
                        // if good -> finish, return result to showkey and display thered!
                        Intent intent = new Intent();
                        intent.putExtra(OperationResult.EXTRA_RESULT, result);
                        getActivity().setResult(EditKeyActivity.RESULT_OK, intent);
                        getActivity().finish();
                    }
                }
        );

        ((EditKeyActivity) getActivity()).setFullScreenDialogDoneClose(
                R.string.btn_save,
                new OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        // if we are working on an Uri, save directly
                        if (mDataUri == null) {
                            returnKeyringParcel();
                        } else {
                            cryptoOperation(new CryptoInputParcel());
                        }
                    }
                }, new OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        getActivity().setResult(Activity.RESULT_CANCELED);
                        getActivity().finish();
                    }
                });

        Uri dataUri = getArguments().getParcelable(ARG_DATA_URI);
        SaveKeyringParcel saveKeyringParcel = getArguments().getParcelable(ARG_SAVE_KEYRING_PARCEL);
        if (dataUri == null && saveKeyringParcel == null) {
            Log.e(Constants.TAG, "Either a key Uri or ARG_SAVE_KEYRING_PARCEL is required!");
            getActivity().finish();
            return;
        }

        initView();
        if (dataUri != null) {
            loadData(dataUri);
        } else {
            loadSaveKeyringParcel(saveKeyringParcel);
        }
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        Log.e("PHILIP","Frament onActivityResult");
        super.onActivityResult(requestCode, resultCode, data);
    }

    private void loadSaveKeyringParcel(SaveKeyringParcel saveKeyringParcel) {
        mSaveKeyringParcel = saveKeyringParcel;
        mPrimaryUserId = saveKeyringParcel.mChangePrimaryUserId;

        mUserIdsAddedAdapter = new UserIdsAddedAdapter(getActivity(), mSaveKeyringParcel.mAddUserIds, true);
        mUserIdsAddedList.setAdapter(mUserIdsAddedAdapter);

        mSubkeysAddedAdapter = new SubkeysAddedAdapter(getActivity(), mSaveKeyringParcel.mAddSubKeys, true);
        mSubkeysAddedList.setAdapter(mSubkeysAddedAdapter);
    }

    private void loadData(Uri dataUri) {
        mDataUri = dataUri;

        Log.i(Constants.TAG, "mDataUri: " + mDataUri.toString());

        // load the secret key ring. we do verify here that the passphrase is correct, so cached won't do
        try {
            Uri secretUri = KeychainContract.KeyRings.buildUnifiedKeyRingUri(mDataUri);
            CachedPublicKeyRing keyRing =
                    new ProviderHelper(getActivity()).getCachedPublicKeyRing(secretUri);
            long masterKeyId = keyRing.getMasterKeyId();

            // check if this is a master secret key we can work with
            switch (keyRing.getSecretKeyType(masterKeyId)) {
                case GNU_DUMMY:
                    finishWithError(LogType.MSG_EK_ERROR_DUMMY);
                    return;
            }

            mSaveKeyringParcel = new SaveKeyringParcel(masterKeyId, keyRing.getFingerprint());
            mPrimaryUserId = keyRing.getPrimaryUserIdWithFallback();

        } catch (PgpKeyNotFoundException | NotFoundException e) {
            finishWithError(LogType.MSG_EK_ERROR_NOT_FOUND);
            return;
        }

        // Prepare the loaders. Either re-connect with an existing ones,
        // or start new ones.
        getLoaderManager().initLoader(LOADER_ID_USER_IDS, null, EditKeyFragment.this);
        getLoaderManager().initLoader(LOADER_ID_SUBKEYS, null, EditKeyFragment.this);

        mUserIdsAdapter = new UserIdsAdapter(getActivity(), null, 0, mSaveKeyringParcel);
        mUserIdsList.setAdapter(mUserIdsAdapter);

        // TODO: SaveParcel from savedInstance?!
        mUserIdsAddedAdapter = new UserIdsAddedAdapter(getActivity(), mSaveKeyringParcel.mAddUserIds, false);
        mUserIdsAddedList.setAdapter(mUserIdsAddedAdapter);

        mSubkeysAdapter = new SubkeysAdapter(getActivity(), null, 0, mSaveKeyringParcel);
        mSubkeysList.setAdapter(mSubkeysAdapter);

        mSubkeysAddedAdapter = new SubkeysAddedAdapter(getActivity(), mSaveKeyringParcel.mAddSubKeys, false);
        mSubkeysAddedList.setAdapter(mSubkeysAddedAdapter);
    }

    private void initView() {
        mChangePassphrase.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                changePassphrase();
            }
        });

        mAddUserId.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                addUserId();
            }
        });

        mAddSubkey.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                addSubkey();
            }
        });

        mSubkeysList.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                editSubkey(position);
            }
        });

        mUserIdsList.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                editUserId(position);
            }
        });
    }

    public Loader<Cursor> onCreateLoader(int id, Bundle args) {

        switch (id) {
            case LOADER_ID_USER_IDS: {
                Uri baseUri = UserPackets.buildUserIdsUri(mDataUri);
                return new CursorLoader(getActivity(), baseUri,
                        UserIdsAdapter.USER_IDS_PROJECTION, null, null, null);
            }

            case LOADER_ID_SUBKEYS: {
                Uri baseUri = KeychainContract.Keys.buildKeysUri(mDataUri);
                return new CursorLoader(getActivity(), baseUri,
                        SubkeysAdapter.SUBKEYS_PROJECTION, null, null, null);
            }

            default:
                return null;
        }
    }

    public void onLoadFinished(Loader<Cursor> loader, Cursor data) {
        // Swap the new cursor in. (The framework will take care of closing the
        // old cursor once we return.)
        switch (loader.getId()) {
            case LOADER_ID_USER_IDS:
                mUserIdsAdapter.swapCursor(data);
                break;

            case LOADER_ID_SUBKEYS:
                mSubkeysAdapter.swapCursor(data);
                break;

        }
    }

    /**
     * This is called when the last Cursor provided to onLoadFinished() above is about to be closed.
     * We need to make sure we are no longer using it.
     */
    public void onLoaderReset(Loader<Cursor> loader) {
        switch (loader.getId()) {
            case LOADER_ID_USER_IDS:
                mUserIdsAdapter.swapCursor(null);
                break;
            case LOADER_ID_SUBKEYS:
                mSubkeysAdapter.swapCursor(null);
                break;
        }
    }

    private void changePassphrase() {
//        Intent passIntent = new Intent(getActivity(), PassphraseWizardActivity.class);
//        passIntent.setAction(PassphraseWizardActivity.CREATE_METHOD);
//        startActivityForResult(passIntent, 12);
        // Message is received after passphrase is cached
        Handler returnHandler = new Handler() {
            @Override
            public void handleMessage(Message message) {
                if (message.what == SetPassphraseDialogFragment.MESSAGE_OKAY) {
                    Bundle data = message.getData();

                    // cache new returned passphrase!
                    mSaveKeyringParcel.mNewUnlock = new ChangeUnlockParcel(
                            (Passphrase) data.getParcelable(SetPassphraseDialogFragment.MESSAGE_NEW_PASSPHRASE),
                            null
                    );
                }
            }
        };

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(returnHandler);

        SetPassphraseDialogFragment setPassphraseDialog = SetPassphraseDialogFragment.newInstance(
                messenger, R.string.title_change_passphrase);

        setPassphraseDialog.show(getActivity().getSupportFragmentManager(), "setPassphraseDialog");
    }

    private void editUserId(final int position) {
        final String userId = mUserIdsAdapter.getUserId(position);
        final boolean isRevoked = mUserIdsAdapter.getIsRevoked(position);
        final boolean isRevokedPending = mUserIdsAdapter.getIsRevokedPending(position);

        Handler returnHandler = new Handler() {
            @Override
            public void handleMessage(Message message) {
                switch (message.what) {
                    case EditUserIdDialogFragment.MESSAGE_CHANGE_PRIMARY_USER_ID:
                        // toggle
                        if (mSaveKeyringParcel.mChangePrimaryUserId != null
                                && mSaveKeyringParcel.mChangePrimaryUserId.equals(userId)) {
                            mSaveKeyringParcel.mChangePrimaryUserId = null;
                        } else {
                            mSaveKeyringParcel.mChangePrimaryUserId = userId;
                        }
                        break;
                    case EditUserIdDialogFragment.MESSAGE_REVOKE:
                        // toggle
                        if (mSaveKeyringParcel.mRevokeUserIds.contains(userId)) {
                            mSaveKeyringParcel.mRevokeUserIds.remove(userId);
                        } else {
                            mSaveKeyringParcel.mRevokeUserIds.add(userId);
                            // not possible to revoke and change to primary user id
                            if (mSaveKeyringParcel.mChangePrimaryUserId != null
                                    && mSaveKeyringParcel.mChangePrimaryUserId.equals(userId)) {
                                mSaveKeyringParcel.mChangePrimaryUserId = null;
                            }
                        }
                        break;
                }
                getLoaderManager().getLoader(LOADER_ID_USER_IDS).forceLoad();
            }
        };

        // Create a new Messenger for the communication back
        final Messenger messenger = new Messenger(returnHandler);

        DialogFragmentWorkaround.INTERFACE.runnableRunDelayed(new Runnable() {
            public void run() {
                EditUserIdDialogFragment dialogFragment =
                        EditUserIdDialogFragment.newInstance(messenger, isRevoked, isRevokedPending);
                dialogFragment.show(getActivity().getSupportFragmentManager(), "editUserIdDialog");
            }
        });
    }

    private void editSubkey(final int position) {
        final long keyId = mSubkeysAdapter.getKeyId(position);

        Handler returnHandler = new Handler() {
            @Override
            public void handleMessage(Message message) {
                switch (message.what) {
                    case EditSubkeyDialogFragment.MESSAGE_CHANGE_EXPIRY:
                        editSubkeyExpiry(position);
                        break;
                    case EditSubkeyDialogFragment.MESSAGE_REVOKE:
                        // toggle
                        if (mSaveKeyringParcel.mRevokeSubKeys.contains(keyId)) {
                            mSaveKeyringParcel.mRevokeSubKeys.remove(keyId);
                        } else {
                            mSaveKeyringParcel.mRevokeSubKeys.add(keyId);
                        }
                        break;
                    case EditSubkeyDialogFragment.MESSAGE_STRIP: {
                        SecretKeyType secretKeyType = mSubkeysAdapter.getSecretKeyType(position);
                        if (secretKeyType == SecretKeyType.GNU_DUMMY) {
                            // Key is already stripped; this is a no-op.
                            break;
                        }

                        SubkeyChange change = mSaveKeyringParcel.getSubkeyChange(keyId);
                        if (change == null) {
                            mSaveKeyringParcel.mChangeSubKeys.add(new SubkeyChange(keyId, true, false));
                            break;
                        }
                        // toggle
                        change.mDummyStrip = !change.mDummyStrip;
                        if (change.mDummyStrip && change.mMoveKeyToCard) {
                            // User had chosen to divert key, but now wants to strip it instead.
                            change.mMoveKeyToCard = false;
                        }
                        break;
                    }
                    case EditSubkeyDialogFragment.MESSAGE_KEYTOCARD: {
                        Activity activity = EditKeyFragment.this.getActivity();
                        SecretKeyType secretKeyType = mSubkeysAdapter.getSecretKeyType(position);
                        if (secretKeyType == SecretKeyType.DIVERT_TO_CARD ||
                            secretKeyType == SecretKeyType.GNU_DUMMY) {
                            Notify.create(activity, R.string.edit_key_error_bad_nfc_stripped, Notify.Style.ERROR)
                                    .show((ViewGroup) activity.findViewById(R.id.import_snackbar));
                            break;
                        }
                        int algorithm = mSubkeysAdapter.getAlgorithm(position);
                        // these are the PGP constants for RSA_GENERAL, RSA_ENCRYPT and RSA_SIGN
                        if (algorithm != 1 && algorithm != 2 && algorithm != 3) {
                            Notify.create(activity, R.string.edit_key_error_bad_nfc_algo, Notify.Style.ERROR)
                                    .show((ViewGroup) activity.findViewById(R.id.import_snackbar));
                            break;
                        }
                        if (mSubkeysAdapter.getKeySize(position) != 2048) {
                            Notify.create(activity, R.string.edit_key_error_bad_nfc_size, Notify.Style.ERROR)
                                    .show((ViewGroup) activity.findViewById(R.id.import_snackbar));
                            break;
                        }


                        SubkeyChange change;
                        change = mSaveKeyringParcel.getSubkeyChange(keyId);
                        if (change == null) {
                            mSaveKeyringParcel.mChangeSubKeys.add(
                                    new SubkeyChange(keyId, false, true)
                            );
                            break;
                        }
                        // toggle
                        change.mMoveKeyToCard = !change.mMoveKeyToCard;
                        if (change.mMoveKeyToCard && change.mDummyStrip) {
                            // User had chosen to strip key, but now wants to divert it.
                            change.mDummyStrip = false;
                        }
                        break;
                    }
                }
                getLoaderManager().getLoader(LOADER_ID_SUBKEYS).forceLoad();
            }
        };

        // Create a new Messenger for the communication back
        final Messenger messenger = new Messenger(returnHandler);

        DialogFragmentWorkaround.INTERFACE.runnableRunDelayed(new Runnable() {
            public void run() {
                EditSubkeyDialogFragment dialogFragment =
                        EditSubkeyDialogFragment.newInstance(messenger);

                dialogFragment.show(getActivity().getSupportFragmentManager(), "editSubkeyDialog");
            }
        });
    }

    private void editSubkeyExpiry(final int position) {
        final long keyId = mSubkeysAdapter.getKeyId(position);
        final Long creationDate = mSubkeysAdapter.getCreationDate(position);
        final Long expiryDate = mSubkeysAdapter.getExpiryDate(position);

        Handler returnHandler = new Handler() {
            @Override
            public void handleMessage(Message message) {
                switch (message.what) {
                    case EditSubkeyExpiryDialogFragment.MESSAGE_NEW_EXPIRY:
                        mSaveKeyringParcel.getOrCreateSubkeyChange(keyId).mExpiry =
                                (Long) message.getData().getSerializable(
                                        EditSubkeyExpiryDialogFragment.MESSAGE_DATA_EXPIRY);
                        break;
                }
                getLoaderManager().getLoader(LOADER_ID_SUBKEYS).forceLoad();
            }
        };

        // Create a new Messenger for the communication back
        final Messenger messenger = new Messenger(returnHandler);

        DialogFragmentWorkaround.INTERFACE.runnableRunDelayed(new Runnable() {
            public void run() {
                EditSubkeyExpiryDialogFragment dialogFragment =
                        EditSubkeyExpiryDialogFragment.newInstance(messenger, creationDate, expiryDate);

                dialogFragment.show(getActivity().getSupportFragmentManager(), "editSubkeyExpiryDialog");
            }
        });
    }

    private void addUserId() {
        Handler returnHandler = new Handler() {
            @Override
            public void handleMessage(Message message) {
                if (message.what == SetPassphraseDialogFragment.MESSAGE_OKAY) {
                    Bundle data = message.getData();

                    // add new user id
                    mUserIdsAddedAdapter.add(data
                            .getString(AddUserIdDialogFragment.MESSAGE_DATA_USER_ID));
                }
            }
        };

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(returnHandler);

        // pre-fill out primary name
        String predefinedName = KeyRing.splitUserId(mPrimaryUserId).name;
        AddUserIdDialogFragment addUserIdDialog = AddUserIdDialogFragment.newInstance(messenger,
                predefinedName);

        addUserIdDialog.show(getActivity().getSupportFragmentManager(), "addUserIdDialog");
    }

    private void addSubkey() {
        boolean willBeMasterKey;
        if (mSubkeysAdapter != null) {
            willBeMasterKey = mSubkeysAdapter.getCount() == 0 && mSubkeysAddedAdapter.getCount() == 0;
        } else {
            willBeMasterKey = mSubkeysAddedAdapter.getCount() == 0;
        }

        AddSubkeyDialogFragment addSubkeyDialogFragment =
                AddSubkeyDialogFragment.newInstance(willBeMasterKey);
        addSubkeyDialogFragment
                .setOnAlgorithmSelectedListener(
                        new AddSubkeyDialogFragment.OnAlgorithmSelectedListener() {
                            @Override
                            public void onAlgorithmSelected(SaveKeyringParcel.SubkeyAdd newSubkey) {
                                mSubkeysAddedAdapter.add(newSubkey);
                            }
                        }
                );
        addSubkeyDialogFragment.show(getActivity().getSupportFragmentManager(), "addSubkeyDialog");
    }

    protected void returnKeyringParcel() {
        if (mSaveKeyringParcel.mAddUserIds.size() == 0) {
            Notify.create(getActivity(), R.string.edit_key_error_add_identity, Notify.Style.ERROR).show();
            return;
        }
        if (mSaveKeyringParcel.mAddSubKeys.size() == 0) {
            Notify.create(getActivity(), R.string.edit_key_error_add_subkey, Notify.Style.ERROR).show();
            return;
        }

        // use first user id as primary
        mSaveKeyringParcel.mChangePrimaryUserId = mSaveKeyringParcel.mAddUserIds.get(0);

        Intent returnIntent = new Intent();
        returnIntent.putExtra(EditKeyActivity.EXTRA_SAVE_KEYRING_PARCEL, mSaveKeyringParcel);
        getActivity().setResult(Activity.RESULT_OK, returnIntent);
        getActivity().finish();
    }

    /**
     * Closes this activity, returning a result parcel with a single error log entry.
     */
    void finishWithError(LogType reason) {
        // Prepare an intent with an EXTRA_RESULT
        Intent intent = new Intent();
        intent.putExtra(OperationResult.EXTRA_RESULT,
                new SingletonResult(SingletonResult.RESULT_ERROR, reason));

        // Finish with result
        getActivity().setResult(EditKeyActivity.RESULT_OK, intent);
        getActivity().finish();
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/ImportKeysActivity.java
/*
 * Copyright (C) 2012-2014 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2011 Senecaso
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

package org.sufficientlysecure.keychain.ui;

import android.app.ProgressDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.support.v4.app.Fragment;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.intents.OpenKeychainIntents;
import org.sufficientlysecure.keychain.keyimport.ImportKeysListEntry;
import org.sufficientlysecure.keychain.keyimport.ParcelableKeyRing;
import org.sufficientlysecure.keychain.operations.results.ImportKeyResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.service.ImportKeyringParcel;
import org.sufficientlysecure.keychain.service.KeychainNewService;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.input.CryptoInputParcel;
import org.sufficientlysecure.keychain.ui.base.BaseNfcActivity;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils;
import org.sufficientlysecure.keychain.ui.util.Notify;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.ParcelableFileCache;
import org.sufficientlysecure.keychain.util.ParcelableFileCache.IteratorWithSize;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

import java.io.IOException;
import java.util.ArrayList;

public class ImportKeysActivity extends BaseNfcActivity {

    public static final String ACTION_IMPORT_KEY = OpenKeychainIntents.IMPORT_KEY;
    public static final String ACTION_IMPORT_KEY_FROM_KEYSERVER = OpenKeychainIntents.IMPORT_KEY_FROM_KEYSERVER;
    public static final String ACTION_IMPORT_KEY_FROM_KEYSERVER_AND_RETURN_RESULT =
            Constants.INTENT_PREFIX + "IMPORT_KEY_FROM_KEY_SERVER_AND_RETURN_RESULT";
    public static final String ACTION_IMPORT_KEY_FROM_KEYSERVER_AND_RETURN_TO_SERVICE = Constants.INTENT_PREFIX
            + "IMPORT_KEY_FROM_KEY_SERVER_AND_RETURN";
    public static final String ACTION_IMPORT_KEY_FROM_FILE_AND_RETURN = Constants.INTENT_PREFIX
            + "IMPORT_KEY_FROM_FILE_AND_RETURN";

    // Actions for internal use only:
    public static final String ACTION_IMPORT_KEY_FROM_FILE = Constants.INTENT_PREFIX
            + "IMPORT_KEY_FROM_FILE";
    public static final String ACTION_SEARCH_KEYSERVER_FROM_URL = Constants.INTENT_PREFIX
            + "SEARCH_KEYSERVER_FROM_URL";
    public static final String EXTRA_RESULT = "result";

    // only used by ACTION_IMPORT_KEY
    public static final String EXTRA_KEY_BYTES = OpenKeychainIntents.IMPORT_EXTRA_KEY_EXTRA_KEY_BYTES;

    // only used by ACTION_IMPORT_KEY_FROM_KEYSERVER
    public static final String EXTRA_QUERY = OpenKeychainIntents.IMPORT_KEY_FROM_KEYSERVER_EXTRA_QUERY;
    public static final String EXTRA_KEY_ID = Constants.EXTRA_PREFIX + "EXTRA_KEY_ID";
    public static final String EXTRA_FINGERPRINT = OpenKeychainIntents.IMPORT_KEY_FROM_KEYSERVER_EXTRA_FINGERPRINT;

    // only used by ACTION_IMPORT_KEY_FROM_KEYSERVER_AND_RETURN_TO_SERVICE when used from OpenPgpService
    public static final String EXTRA_PENDING_INTENT_DATA = "data";
    private Intent mPendingIntentData;

    // view
    private ImportKeysListFragment mListFragment;
    private Fragment mTopFragment;
    private View mImportButton;

    private Preferences.ProxyPrefs mProxyPrefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mProxyPrefs = Preferences.getPreferences(this).getProxyPrefs();

        mImportButton = findViewById(R.id.import_import);
        mImportButton.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                importKeys();
            }
        });

        handleActions(savedInstanceState, getIntent());
    }

    @Override
    protected void initLayout() {
        setContentView(R.layout.import_keys_activity);
    }

    protected void handleActions(Bundle savedInstanceState, Intent intent) {
        String action = intent.getAction();
        Bundle extras = intent.getExtras();
        Uri dataUri = intent.getData();
        String scheme = intent.getScheme();

        if (extras == null) {
            extras = new Bundle();
        }

        if (action == null) {
            startCloudFragment(savedInstanceState, null, false, null);
            startListFragment(savedInstanceState, null, null, null, null);
            return;
        }

        if (Intent.ACTION_VIEW.equals(action)) {
            if (scheme.equals("http") || scheme.equals("https")) {
                action = ACTION_SEARCH_KEYSERVER_FROM_URL;
            } else {
                // Android's Action when opening file associated to Keychain (see AndroidManifest.xml)
                // delegate action to ACTION_IMPORT_KEY
                action = ACTION_IMPORT_KEY;
            }
        }

        switch (action) {
            case ACTION_IMPORT_KEY: {
                /* Keychain's own Actions */
                startFileFragment(savedInstanceState);

                if (dataUri != null) {
                    // action: directly load data
                    startListFragment(savedInstanceState, null, dataUri, null, null);
                } else if (extras.containsKey(EXTRA_KEY_BYTES)) {
                    byte[] importData = extras.getByteArray(EXTRA_KEY_BYTES);

                    // action: directly load data
                    startListFragment(savedInstanceState, importData, null, null, null);
                }
                break;
            }
            case ACTION_IMPORT_KEY_FROM_KEYSERVER:
            case ACTION_IMPORT_KEY_FROM_KEYSERVER_AND_RETURN_TO_SERVICE:
            case ACTION_IMPORT_KEY_FROM_KEYSERVER_AND_RETURN_RESULT: {

                // only used for OpenPgpService
                if (extras.containsKey(EXTRA_PENDING_INTENT_DATA)) {
                    mPendingIntentData = extras.getParcelable(EXTRA_PENDING_INTENT_DATA);
                }
                if (extras.containsKey(EXTRA_QUERY) || extras.containsKey(EXTRA_KEY_ID)) {
                    /* simple search based on query or key id */

                    String query = null;
                    if (extras.containsKey(EXTRA_QUERY)) {
                        query = extras.getString(EXTRA_QUERY);
                    } else if (extras.containsKey(EXTRA_KEY_ID)) {
                        long keyId = extras.getLong(EXTRA_KEY_ID, 0);
                        if (keyId != 0) {
                            query = KeyFormattingUtils.convertKeyIdToHex(keyId);
                        }
                    }

                    if (query != null && query.length() > 0) {
                        // display keyserver fragment with query
                        startCloudFragment(savedInstanceState, query, false, null);

                        // action: search immediately
                        startListFragment(savedInstanceState, null, null, query, null);
                    } else {
                        Log.e(Constants.TAG, "Query is empty!");
                        return;
                    }
                } else if (extras.containsKey(EXTRA_FINGERPRINT)) {
                    /*
                     * search based on fingerprint, here we can enforce a check in the end
                     * if the right key has been downloaded
                     */

                    String fingerprint = extras.getString(EXTRA_FINGERPRINT);
                    if (isFingerprintValid(fingerprint)) {
                        String query = "0x" + fingerprint;

                        // display keyserver fragment with query
                        startCloudFragment(savedInstanceState, query, true, null);

                        // action: search immediately
                        startListFragment(savedInstanceState, null, null, query, null);
                    }
                } else {
                    Log.e(Constants.TAG,
                            "IMPORT_KEY_FROM_KEYSERVER action needs to contain the 'query', 'key_id', or " +
                                    "'fingerprint' extra!"
                    );
                    return;
                }
                break;
            }
            case ACTION_IMPORT_KEY_FROM_FILE: {
                // NOTE: this only displays the appropriate fragment, no actions are taken
                startFileFragment(savedInstanceState);

                // no immediate actions!
                startListFragment(savedInstanceState, null, null, null, null);
                break;
            }
            case ACTION_SEARCH_KEYSERVER_FROM_URL: {
                // need to process URL to get search query and keyserver authority
                String query = dataUri.getQueryParameter("search");
                String keyserver = dataUri.getAuthority();
                // if query not specified, we still allow users to search the keyserver in the link
                if (query == null) {
                    Notify.create(this, R.string.import_url_warn_no_search_parameter, Notify.LENGTH_INDEFINITE,
                            Notify.Style.WARN).show(mTopFragment);
                    // we just set the keyserver
                    startCloudFragment(savedInstanceState, null, false, keyserver);
                    // we don't set the keyserver for ImportKeysListFragment since
                    // it'll be taken care of by ImportKeysCloudFragment when the user clicks
                    // the search button
                    startListFragment(savedInstanceState, null, null, null, null);
                } else {
                    // we allow our users to edit the query if they wish
                    startCloudFragment(savedInstanceState, query, false, keyserver);
                    // search immediately
                    startListFragment(savedInstanceState, null, null, query, keyserver);
                }
                break;
            }
            case ACTION_IMPORT_KEY_FROM_FILE_AND_RETURN: {
                // NOTE: this only displays the appropriate fragment, no actions are taken
                startFileFragment(savedInstanceState);

                // no immediate actions!
                startListFragment(savedInstanceState, null, null, null, null);
                break;
            }
            default: {
                startCloudFragment(savedInstanceState, null, false, null);
                startListFragment(savedInstanceState, null, null, null, null);
                break;
            }
        }
    }


    /**
     * if the fragment is started with non-null bytes/dataUri/serverQuery, it will immediately
     * load content
     *
     * @param savedInstanceState
     * @param bytes              bytes containing list of keyrings to import
     * @param dataUri            uri to file to import keyrings from
     * @param serverQuery        query to search for on the keyserver
     * @param keyserver          keyserver authority to search on. If null will use keyserver from
     *                           user preferences
     */
    private void startListFragment(Bundle savedInstanceState, byte[] bytes, Uri dataUri,
                                   String serverQuery, String keyserver) {
        // However, if we're being restored from a previous state,
        // then we don't need to do anything and should return or else
        // we could end up with overlapping fragments.
        if (mListFragment != null) {
            return;
        }

        mListFragment = ImportKeysListFragment.newInstance(bytes, dataUri, serverQuery, false,
                keyserver);

        // Add the fragment to the 'fragment_container' FrameLayout
        // NOTE: We use commitAllowingStateLoss() to prevent weird crashes!
        getSupportFragmentManager().beginTransaction()
                .replace(R.id.import_keys_list_container, mListFragment)
                .commitAllowingStateLoss();
        // do it immediately!
        getSupportFragmentManager().executePendingTransactions();
    }

    private void startFileFragment(Bundle savedInstanceState) {
        // However, if we're being restored from a previous state,
        // then we don't need to do anything and should return or else
        // we could end up with overlapping fragments.
        if (mTopFragment != null) {
            return;
        }

        // Create an instance of the fragment
        mTopFragment = ImportKeysFileFragment.newInstance();

        // Add the fragment to the 'fragment_container' FrameLayout
        // NOTE: We use commitAllowingStateLoss() to prevent weird crashes!
        getSupportFragmentManager().beginTransaction()
                .replace(R.id.import_keys_top_container, mTopFragment)
                .commitAllowingStateLoss();
        // do it immediately!
        getSupportFragmentManager().executePendingTransactions();
    }

    /**
     * loads the CloudFragment, which consists of the search bar, search button and settings icon.
     *
     * @param savedInstanceState
     * @param query              search query
     * @param disableQueryEdit   if true, user will not be able to edit the search query
     * @param keyserver          keyserver authority to use for search, if null will use keyserver
     *                           specified in user preferences
     */

    private void startCloudFragment(Bundle savedInstanceState, String query, boolean disableQueryEdit, String
            keyserver) {
        // However, if we're being restored from a previous state,
        // then we don't need to do anything and should return or else
        // we could end up with overlapping fragments.
        if (mTopFragment != null) {
            return;
        }

        // Create an instance of the fragment
        mTopFragment = ImportKeysCloudFragment.newInstance(query, disableQueryEdit, keyserver);

        // Add the fragment to the 'fragment_container' FrameLayout
        // NOTE: We use commitAllowingStateLoss() to prevent weird crashes!
        getSupportFragmentManager().beginTransaction()
                .replace(R.id.import_keys_top_container, mTopFragment)
                .commitAllowingStateLoss();
        // do it immediately!
        getSupportFragmentManager().executePendingTransactions();
    }

    private boolean isFingerprintValid(String fingerprint) {
        if (fingerprint == null || fingerprint.length() < 40) {
            Notify.create(this, R.string.import_qr_code_too_short_fingerprint, Notify.Style.ERROR)
                    .show((ViewGroup) findViewById(R.id.import_snackbar));
            return false;
        } else {
            return true;
        }
    }

    public void loadCallback(final ImportKeysListFragment.LoaderState loaderState) {
        if (loaderState instanceof ImportKeysListFragment.CloudLoaderState) {
            // do the tor check
            // this handle will set tor to be ignored whenever a message is received
            Runnable ignoreTor = new Runnable() {
                @Override
                public void run() {
                    // disables Tor until Activity is recreated
                    mProxyPrefs = new Preferences.ProxyPrefs(false, false, null, -1, null);
                    mListFragment.loadNew(loaderState, mProxyPrefs.parcelableProxy);
                }
            };
            if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, mProxyPrefs, this)) {
                mListFragment.loadNew(loaderState, mProxyPrefs.parcelableProxy);
            }
        } else if (loaderState instanceof ImportKeysListFragment.BytesLoaderState) { // must always be true
            mListFragment.loadNew(loaderState, mProxyPrefs.parcelableProxy);
        }
    }

    private void handleMessage(Message message) {
        if (message.arg1 == ServiceProgressHandler.MessageStatus.OKAY.ordinal()) {
            // get returned data bundle
            Bundle returnData = message.getData();
            if (returnData == null) {
                return;
            }
            final ImportKeyResult result = returnData.getParcelable(OperationResult.EXTRA_RESULT);
            if (result == null) {
                Log.e(Constants.TAG, "result == null");
                return;
            }

            if (ACTION_IMPORT_KEY_FROM_KEYSERVER_AND_RETURN_RESULT.equals(getIntent().getAction())
                    || ACTION_IMPORT_KEY_FROM_FILE_AND_RETURN.equals(getIntent().getAction())) {
                Intent intent = new Intent();
                intent.putExtra(ImportKeyResult.EXTRA_RESULT, result);
                ImportKeysActivity.this.setResult(RESULT_OK, intent);
                ImportKeysActivity.this.finish();
                return;
            }
            if (ACTION_IMPORT_KEY_FROM_KEYSERVER_AND_RETURN_TO_SERVICE.equals(getIntent().getAction())) {
                ImportKeysActivity.this.setResult(RESULT_OK, mPendingIntentData);
                ImportKeysActivity.this.finish();
                return;
            }

            result.createNotify(ImportKeysActivity.this)
                    .show((ViewGroup) findViewById(R.id.import_snackbar));
        }
    }

    /**
     * Import keys with mImportData
     */
    public void importKeys() {

        if (mListFragment.getSelectedEntries().size() == 0) {
            Notify.create(this, R.string.error_nothing_import_selected, Notify.Style.ERROR)
                    .show((ViewGroup) findViewById(R.id.import_snackbar));
            return;
        }

        ServiceProgressHandler serviceHandler = new ServiceProgressHandler(this) {
            @Override
            public void handleMessage(Message message) {
                // handle messages by standard KeychainIntentServiceHandler first
                super.handleMessage(message);

                ImportKeysActivity.this.handleMessage(message);
            }
        };

        // Send all information needed to service to import key in other thread
        Intent intent = new Intent(this, KeychainNewService.class);
        ImportKeyringParcel operationInput = null;
        CryptoInputParcel cryptoInput = null;

        ImportKeysListFragment.LoaderState ls = mListFragment.getLoaderState();
        if (ls instanceof ImportKeysListFragment.BytesLoaderState) {
            Log.d(Constants.TAG, "importKeys started");

            // get DATA from selected key entries
            IteratorWithSize<ParcelableKeyRing> selectedEntries = mListFragment.getSelectedData();

            // instead of giving the entries by Intent extra, cache them into a
            // file to prevent Java Binder problems on heavy imports
            // read FileImportCache for more info.
            try {
                // We parcel this iteratively into a file - anything we can
                // display here, we should be able to import.
                ParcelableFileCache<ParcelableKeyRing> cache =
                        new ParcelableFileCache<>(this, "key_import.pcl");
                cache.writeCache(selectedEntries);

                operationInput = new ImportKeyringParcel(null, null);
                cryptoInput = new CryptoInputParcel();

            } catch (IOException e) {
                Log.e(Constants.TAG, "Problem writing cache file", e);
                Notify.create(this, "Problem writing cache file!", Notify.Style.ERROR)
                        .show((ViewGroup) findViewById(R.id.import_snackbar));
            }
        } else if (ls instanceof ImportKeysListFragment.CloudLoaderState) {
            ImportKeysListFragment.CloudLoaderState sls = (ImportKeysListFragment.CloudLoaderState) ls;

            // get selected key entries
            ArrayList<ParcelableKeyRing> keys = new ArrayList<>();
            {
                // change the format into ParcelableKeyRing
                ArrayList<ImportKeysListEntry> entries = mListFragment.getSelectedEntries();
                for (ImportKeysListEntry entry : entries) {
                    keys.add(new ParcelableKeyRing(
                                    entry.getFingerprintHex(), entry.getKeyIdHex(), entry.getExtraData())
                    );
                }
            }

            operationInput = new ImportKeyringParcel(keys, sls.mCloudPrefs.keyserver);
            if (mProxyPrefs != null) { // if not null means we have specified an explicit proxy
                cryptoInput = new CryptoInputParcel(mProxyPrefs.parcelableProxy);
            } else {
                cryptoInput = new CryptoInputParcel();
            }
        }

        intent.putExtra(KeychainNewService.EXTRA_OPERATION_INPUT, operationInput);
        intent.putExtra(KeychainNewService.EXTRA_CRYPTO_INPUT, cryptoInput);

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(serviceHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        // show progress dialog
        serviceHandler.showProgressDialog(
                getString(R.string.progress_importing),
                ProgressDialog.STYLE_HORIZONTAL, true
        );

        // start service with intent
        startService(intent);
    }

    @Override
    protected void onNfcPerform() throws IOException {
        // this displays the key or moves to the yubikey import dialogue.
        super.onNfcPerform();
        // either way, finish afterwards
        finish();
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/OrbotRequiredDialogActivity.java
/*
 * Copyright (C) 2015 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2015 Adithya Abraham Philip <adithyaphilip@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.sufficientlysecure.keychain.ui;

import android.content.Intent;
import android.os.Bundle;
import android.support.v4.app.FragmentActivity;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

/**
 * Simply encapsulates a dialog. If orbot is not installed, it shows an install dialog, else a dialog to enable orbot.
 */
public class OrbotRequiredDialogActivity extends FragmentActivity {

    public final static String RESULT_IGNORE_TOR = "ignore_tor";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        Runnable ignoreTor = new Runnable() {
            @Override
            public void run() {
                Intent data = new Intent();
                data.putExtra(RESULT_IGNORE_TOR, true);
                setResult(RESULT_OK, data);
            }
        };

        if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor,
                Preferences.getPreferences(this).getProxyPrefs(), this)) {
            Intent data = new Intent();
            data.putExtra(RESULT_IGNORE_TOR, false);
            setResult(RESULT_OK, data);
        }
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/dialog/OrbotStartDialogFragment.java
/*
 * Copyright (C) 2012-2014 Dominik Schürmann <dominik@dominikschuermann.de>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */


package org.sufficientlysecure.keychain.ui.dialog;

import android.app.Dialog;
import android.content.DialogInterface;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.os.RemoteException;
import android.support.v4.app.DialogFragment;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

/**
 * displays a dialog asking the user to enable Tor
 */
public class OrbotStartDialogFragment extends DialogFragment {
    private static final String ARG_MESSENGER = "messenger";
    private static final String ARG_TITLE = "title";
    private static final String ARG_MESSAGE = "message";
    private static final String ARG_MIDDLE_BUTTON = "middleButton";

    public static final int MESSAGE_MIDDLE_BUTTON = 1;

    public static OrbotStartDialogFragment newInstance(Messenger messenger, int title, int message, int middleButton) {
        Bundle args = new Bundle();
        args.putParcelable(ARG_MESSENGER, messenger);
        args.putInt(ARG_TITLE, title);
        args.putInt(ARG_MESSAGE, message);
        args.putInt(ARG_MIDDLE_BUTTON, middleButton);

        OrbotStartDialogFragment fragment = new OrbotStartDialogFragment();
        fragment.setArguments(args);

        return fragment;
    }

    @Override
    public Dialog onCreateDialog(Bundle savedInstanceState) {

        final Messenger messenger = getArguments().getParcelable(ARG_MESSENGER);
        int title = getArguments().getInt(ARG_TITLE);
        final int message = getArguments().getInt(ARG_MESSAGE);
        int middleButton = getArguments().getInt(ARG_MIDDLE_BUTTON);

        CustomAlertDialogBuilder builder = new CustomAlertDialogBuilder(getActivity());
        builder.setTitle(title).setMessage(message);

        builder.setNegativeButton(R.string.orbot_start_dialog_cancel, new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {

            }
        });

        builder.setPositiveButton(R.string.orbot_start_dialog_start, new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                getActivity().startActivityForResult(OrbotHelper.getOrbotStartIntent(), 1);
            }
        });

        builder.setNeutralButton(middleButton, new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                Message msg = new Message();
                msg.what = MESSAGE_MIDDLE_BUTTON;
                try {
                    messenger.send(msg);
                } catch (RemoteException e) {
                    Log.w(Constants.TAG, "Exception sending message, Is handler present?", e);
                } catch (NullPointerException e) {
                    Log.w(Constants.TAG, "Messenger is null!", e);
                }
            }
        });

        return builder.show();
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/util/ParcelableProxy.java
/*
 * Copyright (C) 2014 Dominik Schürmann <dominik@dominikschuermann.de>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.sufficientlysecure.keychain.util;

import android.os.Parcel;
import android.os.Parcelable;

import java.net.InetSocketAddress;
import java.net.Proxy;

/**
 * used to simply transport java.net.Proxy objects created using InetSockets between services/activities
 */
public class ParcelableProxy implements Parcelable {
    private String mProxyHost;
    private int mProxyPort;
    private int mProxyType;

    private final int TYPE_HTTP = 1;
    private final int TYPE_SOCKS = 2;

    public ParcelableProxy(String hostName, int port, Proxy.Type type) {
        mProxyHost = hostName;

        if (hostName == null) return; // represents a null proxy

        mProxyPort = port;

        switch (type) {
            case HTTP: {
                mProxyType = TYPE_HTTP;
                break;
            }
            case SOCKS: {
                mProxyType = TYPE_SOCKS;
                break;
            }
        }
    }

    public Proxy getProxy() {
        if (mProxyHost == null) return null;

        Proxy.Type type = null;
        switch (mProxyType) {
            case TYPE_HTTP:
                type = Proxy.Type.HTTP;
                break;
            case TYPE_SOCKS:
                type = Proxy.Type.SOCKS;
                break;
        }
        return new Proxy(type, new InetSocketAddress(mProxyHost, mProxyPort));
    }

    protected ParcelableProxy(Parcel in) {
        mProxyHost = in.readString();
        mProxyPort = in.readInt();
        mProxyType = in.readInt();
    }

    @Override
    public int describeContents() {
        return 0;
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeString(mProxyHost);
        dest.writeInt(mProxyPort);
        dest.writeInt(mProxyType);
    }

    @SuppressWarnings("unused")
    public static final Parcelable.Creator<ParcelableProxy> CREATOR = new Parcelable.Creator<ParcelableProxy>() {
        @Override
        public ParcelableProxy createFromParcel(Parcel in) {
            return new ParcelableProxy(in);
        }

        @Override
        public ParcelableProxy[] newArray(int size) {
            return new ParcelableProxy[size];
        }
    };
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/util/operation/ImportOperationHelper.java
/*
 * Copyright (C) 2015 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2015 Adithya Abraham Philip <adithyaphilip@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.sufficientlysecure.keychain.util.operation;

import android.support.v4.app.FragmentActivity;
import org.sufficientlysecure.keychain.keyimport.ParcelableKeyRing;
import org.sufficientlysecure.keychain.operations.results.ImportKeyResult;
import org.sufficientlysecure.keychain.service.ImportKeyringParcel;

import java.util.ArrayList;

public abstract class ImportOperationHelper extends OperationHelper<ImportKeyringParcel, ImportKeyResult> {
    private ArrayList<ParcelableKeyRing> mKeyList;
    private String mKeyserver;

    public ImportOperationHelper(FragmentActivity activity, ArrayList<ParcelableKeyRing> keyList, String keyserver) {
        super(activity);
        mKeyList = keyList;
        mKeyserver = keyserver;
    }
    @Override
    public ImportKeyringParcel createOperationInput() {
        return new ImportKeyringParcel(mKeyList, mKeyserver);
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/util/operation/OperationHelper.java
/*
 * Copyright (C) 2015 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2015 Vincent Breitmoser <v.breitmoser@mugenguild.com>
 * Copyright (C) 2015 Adithya Abraham Philip <adithyaphilip@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

package org.sufficientlysecure.keychain.util.operation;

import android.app.Activity;
import android.app.ProgressDialog;
import android.content.Intent;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.os.Parcelable;
import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentActivity;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.operations.results.InputPendingResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.service.KeychainNewService;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.service.input.CryptoInputParcel;
import org.sufficientlysecure.keychain.service.input.RequiredInputParcel;
import org.sufficientlysecure.keychain.ui.NfcOperationActivity;
import org.sufficientlysecure.keychain.ui.OrbotRequiredDialogActivity;
import org.sufficientlysecure.keychain.ui.PassphraseDialogActivity;
import org.sufficientlysecure.keychain.ui.dialog.ProgressDialogFragment;
import org.sufficientlysecure.keychain.util.Log;

/**
 * Designed to be intergrated into activities or fragments used for CryptoOperations.
 * Encapsulates the execution of a crypto operation and handling of input pending cases.s
 *
 * @param <T> The type of input parcel sent to the operation
 * @param <S> The type of result retruend by the operation
 */
public abstract class OperationHelper<T extends Parcelable, S extends OperationResult> {
    public static final int REQUEST_CODE_PASSPHRASE = 0x00008001;
    public static final int REQUEST_CODE_NFC = 0x00008002;
    public static final int REQUEST_ENABLE_ORBOT = 0x00008004;

    private FragmentActivity mActivity;
    private Fragment mFragment;

    private boolean mUseFragment;

    /**
     * If OperationHelper is being integrated into an activity
     *
     * @param activity
     */
    public OperationHelper(FragmentActivity activity) {
        mActivity = activity;
        mUseFragment = false;
    }

    /**
     * if OperationHelper is being integrated into a fragment
     *
     * @param fragment
     */
    public OperationHelper(Fragment fragment) {
        mFragment = fragment;
        mActivity = fragment.getActivity();
        mUseFragment = true;
    }

    private void initiateInputActivity(RequiredInputParcel requiredInput) {

        Log.d("PHILIP", "Initating input " + requiredInput.mType);
        switch (requiredInput.mType) {
            case NFC_KEYTOCARD:
            case NFC_DECRYPT:
            case NFC_SIGN: {
                Intent intent = new Intent(mActivity, NfcOperationActivity.class);
                intent.putExtra(NfcOperationActivity.EXTRA_REQUIRED_INPUT, requiredInput);
                if (mUseFragment) {
                    mFragment.startActivityForResult(intent, REQUEST_CODE_NFC);
                } else {
                    mActivity.startActivityForResult(intent, REQUEST_CODE_NFC);
                }
                return;
            }

            case PASSPHRASE:
            case PASSPHRASE_SYMMETRIC: {
                Intent intent = new Intent(mActivity, PassphraseDialogActivity.class);
                intent.putExtra(PassphraseDialogActivity.EXTRA_REQUIRED_INPUT, requiredInput);
                if (mUseFragment) {
                    mFragment.startActivityForResult(intent, REQUEST_CODE_PASSPHRASE);
                } else {
                    mActivity.startActivityForResult(intent, REQUEST_CODE_PASSPHRASE);
                }
                return;
            }

            case ENABLE_ORBOT: {
                Intent intent = new Intent(mActivity, OrbotRequiredDialogActivity.class);
                if (mUseFragment) {
                    mFragment.startActivityForResult(intent, REQUEST_ENABLE_ORBOT);
                } else {
                    mActivity.startActivityForResult(intent, REQUEST_ENABLE_ORBOT);
                }
                return;
            }
        }

        throw new RuntimeException("Unhandled pending result!");
    }

    /**
     * Attempts the result of an activity started by this helper. Returns true if request code is recognized,
     * false otherwise.
     *
     * @param requestCode
     * @param resultCode
     * @param data
     * @return true if requestCode was recognized, false otherwise
     */
    public boolean handleActivityResult(int requestCode, int resultCode, Intent data) {
        Log.d("PHILIP", "received activity result in OperationHelper");
        if (resultCode == Activity.RESULT_CANCELED) {
            onCryptoOperationCancelled();
            return true;
        }

        switch (requestCode) {
            case REQUEST_CODE_PASSPHRASE: {
                if (resultCode == Activity.RESULT_OK && data != null) {
                    CryptoInputParcel cryptoInput =
                            data.getParcelableExtra(PassphraseDialogActivity.RESULT_CRYPTO_INPUT);
                    cryptoOperation(cryptoInput);
                    return true;
                }
                break;
            }

            case REQUEST_CODE_NFC: {
                if (resultCode == Activity.RESULT_OK && data != null) {
                    CryptoInputParcel cryptoInput =
                            data.getParcelableExtra(NfcOperationActivity.RESULT_DATA);
                    cryptoOperation(cryptoInput);
                    return true;
                }
                break;
            }

            case REQUEST_ENABLE_ORBOT: {
                if (resultCode == Activity.RESULT_OK && data != null) {
                    if (data.getBooleanExtra(OrbotRequiredDialogActivity.RESULT_IGNORE_TOR, false)) {
                        cryptoOperation(new CryptoInputParcel());
                    }
                    return true;
                }
                break;
            }

            default: {
                return false;
            }
        }
        return true;
    }

    protected void dismissProgress() {
        ProgressDialogFragment progressDialogFragment =
                (ProgressDialogFragment) mActivity.getSupportFragmentManager().findFragmentByTag("progressDialog");

        if (progressDialogFragment == null) {
            return;
        }

        progressDialogFragment.dismissAllowingStateLoss();

    }

    public abstract T createOperationInput();

    public void cryptoOperation(CryptoInputParcel cryptoInput) {

        T operationInput = createOperationInput();
        if (operationInput == null) {
            return;
        }

        // Send all information needed to service to edit key in other thread
        Intent intent = new Intent(mActivity, KeychainNewService.class);

        intent.putExtra(KeychainNewService.EXTRA_OPERATION_INPUT, operationInput);
        intent.putExtra(KeychainNewService.EXTRA_CRYPTO_INPUT, cryptoInput);

        ServiceProgressHandler saveHandler = new ServiceProgressHandler(mActivity) {
            @Override
            public void handleMessage(Message message) {
                // handle messages by standard KeychainIntentServiceHandler first
                super.handleMessage(message);

                if (message.arg1 == MessageStatus.OKAY.ordinal()) {

                    // get returned data bundle
                    Bundle returnData = message.getData();
                    if (returnData == null) {
                        return;
                    }

                    final OperationResult result =
                            returnData.getParcelable(OperationResult.EXTRA_RESULT);

                    onHandleResult(result);
                }
            }
        };

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(saveHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        saveHandler.showProgressDialog(
                mActivity.getString(R.string.progress_building_key),
                ProgressDialog.STYLE_HORIZONTAL, false);

        mActivity.startService(intent);

    }

    public void cryptoOperation() {
        cryptoOperation(new CryptoInputParcel());
    }

    protected void onCryptoOperationResult(S result) {
        Log.d("PHILIP", "cryptoResult " + result.success());
        if (result.success()) {
            onCryptoOperationSuccess(result);
        } else {
            onCryptoOperationError(result);
        }
    }

    abstract protected void onCryptoOperationSuccess(S result);

    protected void onCryptoOperationError(S result) {
        result.createNotify(mActivity).show();
    }

    protected void onCryptoOperationCancelled() {
    }

    public void onHandleResult(OperationResult result) {
        Log.d("PHILIP", "Handling result in OperationHelper");

        if (result instanceof InputPendingResult) {
            Log.d("PHILIP", "is pending result");
            InputPendingResult pendingResult = (InputPendingResult) result;
            if (pendingResult.isPending()) {

                Log.d("PHILIP", "Is pending");
                RequiredInputParcel requiredInput = pendingResult.getRequiredInputParcel();
                initiateInputActivity(requiredInput);
                return;
            }
        }

        dismissProgress();

        try {
            // noinspection unchecked, because type erasure :(
            onCryptoOperationResult((S) result);
        } catch (ClassCastException e) {
            throw new AssertionError("bad return class ("
                    + result.getClass().getSimpleName() + "), this is a programming error!");
        }

    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/util/orbot/OrbotHelper.java
/* This is the license for Orlib, a free software project to
        provide anonymity on the Internet from a Google Android smartphone.

        For more information about Orlib, see https://guardianproject.info/

        If you got this file as a part of a larger bundle, there may be other
        license terms that you should be aware of.
        ===============================================================================
        Orlib is distributed under this license (aka the 3-clause BSD license)

        Copyright (c) 2009-2010, Nathan Freitas, The Guardian Project

        Redistribution and use in source and binary forms, with or without
        modification, are permitted provided that the following conditions are
        met:

        * Redistributions of source code must retain the above copyright
        notice, this list of conditions and the following disclaimer.

        * Redistributions in binary form must reproduce the above
        copyright notice, this list of conditions and the following disclaimer
        in the documentation and/or other materials provided with the
        distribution.

        * Neither the names of the copyright owners nor the names of its
        contributors may be used to endorse or promote products derived from
        this software without specific prior written permission.

        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
        "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
        LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
        A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
        OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
        SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
        LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
        DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
        THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
        (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
        OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

        *****
        Orlib contains a binary distribution of the JSocks library:
        http://code.google.com/p/jsocks-mirror/
        which is licensed under the GNU Lesser General Public License:
        http://www.gnu.org/licenses/lgpl.html

        *****
*/

package org.sufficientlysecure.keychain.util.orbot;

import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.Message;
import android.os.Messenger;
import android.support.v4.app.DialogFragment;
import android.support.v4.app.FragmentActivity;

import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.ui.dialog.SupportInstallDialogFragment;
import org.sufficientlysecure.keychain.ui.dialog.OrbotStartDialogFragment;
import org.sufficientlysecure.keychain.ui.dialog.PreferenceInstallDialogFragment;
import org.sufficientlysecure.keychain.util.Preferences;

/**
 * This class is taken from the NetCipher library: https://github.com/guardianproject/NetCipher/
 */
public class OrbotHelper {

    public final static String ORBOT_PACKAGE_NAME = "org.torproject.android";
    public final static String TOR_BIN_PATH = "/data/data/org.torproject.android/app_bin/tor";

    public final static String ACTION_START_TOR = "org.torproject.android.START_TOR";

    public static boolean isOrbotRunning() {
        int procId = TorServiceUtils.findProcessId(TOR_BIN_PATH);

        return (procId != -1);
    }

    public static boolean isOrbotInstalled(Context context) {
        return isAppInstalled(ORBOT_PACKAGE_NAME, context);
    }

    public static boolean isOrbotInstalledAndRunning(Context context) {
        return isOrbotRunning() && isOrbotInstalled(context);
    }

    private static boolean isAppInstalled(String uri, Context context) {
        PackageManager pm = context.getPackageManager();

        boolean installed;
        try {
            pm.getPackageInfo(uri, PackageManager.GET_ACTIVITIES);
            installed = true;
        } catch (PackageManager.NameNotFoundException e) {
            installed = false;
        }
        return installed;
    }

    /**
     * hack to get around the fact that PreferenceActivity still supports only android.app.DialogFragment
     *
     * @return
     */
    public static android.app.DialogFragment getPreferenceInstallDialogFragment() {
        return PreferenceInstallDialogFragment.newInstance(R.string.orbot_install_dialog_title,
                R.string.orbot_install_dialog_content, ORBOT_PACKAGE_NAME);
    }

    public static DialogFragment getInstallDialogFragment() {
        return SupportInstallDialogFragment.newInstance(R.string.orbot_install_dialog_title,
                R.string.orbot_install_dialog_content, ORBOT_PACKAGE_NAME);
    }

    public static DialogFragment getInstallDialogFragmentWithThirdButton(Messenger messenger, int middleButton) {
        return SupportInstallDialogFragment.newInstance(messenger, R.string.orbot_install_dialog_title,
                R.string.orbot_install_dialog_content, ORBOT_PACKAGE_NAME, middleButton, true);
    }

    public static DialogFragment getOrbotStartDialogFragment(Messenger messenger, int middleButton) {
        return OrbotStartDialogFragment.newInstance(messenger, R.string.orbot_start_dialog_title, R.string
                        .orbot_start_dialog_content,
                middleButton);
    }

    public static Intent getOrbotStartIntent() {
        Intent intent = new Intent(ACTION_START_TOR);
        intent.setPackage(ORBOT_PACKAGE_NAME);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        return intent;
    }

    /**
     * checks if Tor is enabled and if it is, that Orbot is installed and runnign. Generates appropriate dialogs.
     *
     * @param middleButton         resourceId of string to display as the middle button of install and enable dialogs
     * @param middleButtonRunnable runnable to be executed if the user clicks on the middle button
     * @param proxyPrefs
     * @param fragmentActivity
     * @return true if Tor is not enabled or Tor is enabled and Orbot is installed and running, else false
     */
    public static boolean isOrbotInRequiredState(int middleButton, final Runnable middleButtonRunnable,
                                                 Preferences.ProxyPrefs proxyPrefs, FragmentActivity fragmentActivity) {
        Handler ignoreTorHandler = new Handler() {
            @Override
            public void handleMessage(Message msg) {
                // every message received by this handler will mean  the middle button was pressed
                middleButtonRunnable.run();
            }
        };

        if (!proxyPrefs.torEnabled) {
            return true;
        }

        if (!OrbotHelper.isOrbotInstalled(fragmentActivity)) {

            OrbotHelper.getInstallDialogFragmentWithThirdButton(
                    new Messenger(ignoreTorHandler),
                    middleButton
            ).show(fragmentActivity.getSupportFragmentManager(), "OrbotHelperOrbotInstallDialog");

            return false;
        } else if (!OrbotHelper.isOrbotRunning()) {

            OrbotHelper.getOrbotStartDialogFragment(new Messenger(ignoreTorHandler),
                    middleButton)
                    .show(fragmentActivity.getSupportFragmentManager(), "OrbotHelperOrbotStartDialog");

            return false;
        } else {
            return true;
        }
    }

    // TODO: PHILIP return an Intent to required dialog activity
    public static Intent getRequiredIntent(Context context) {
        if (!isOrbotInstalled(context)) {

        }
        if (!isOrbotRunning()) {

        }
        return null;
    }
}
