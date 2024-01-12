Refactoring Types: ['Rename Package']
/sufficientlysecure/keychain/ui/CertifyKeyFragment.java
/*
 * Copyright (C) 2013-2014 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2014 Vincent Breitmoser <v.breitmoser@mugenguild.com>
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
import android.app.ProgressDialog;
import android.content.Intent;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.graphics.PorterDuff;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Message;
import android.os.Messenger;
import android.os.Parcel;
import android.support.v4.app.LoaderManager;
import android.support.v4.content.CursorLoader;
import android.support.v4.content.Loader;
import android.view.LayoutInflater;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.widget.CheckBox;
import android.widget.ImageView;
import android.widget.ListView;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.operations.results.CertifyResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.pgp.KeyRing;
import org.sufficientlysecure.keychain.pgp.exception.PgpKeyNotFoundException;
import org.sufficientlysecure.keychain.provider.CachedPublicKeyRing;
import org.sufficientlysecure.keychain.provider.KeychainContract.UserPackets;
import org.sufficientlysecure.keychain.provider.KeychainDatabase.Tables;
import org.sufficientlysecure.keychain.provider.ProviderHelper;
import org.sufficientlysecure.keychain.service.CertifyActionsParcel;
import org.sufficientlysecure.keychain.service.CertifyActionsParcel.CertifyAction;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.service.input.CryptoInputParcel;
import org.sufficientlysecure.keychain.ui.adapter.MultiUserIdsAdapter;
import org.sufficientlysecure.keychain.ui.base.CachingCryptoOperationFragment;
import org.sufficientlysecure.keychain.ui.util.Notify;
import org.sufficientlysecure.keychain.ui.widget.CertifyKeySpinner;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

import java.util.ArrayList;

public class CertifyKeyFragment
        extends CachingCryptoOperationFragment<CertifyActionsParcel, CertifyResult>
        implements LoaderManager.LoaderCallbacks<Cursor> {

    public static final String ARG_CHECK_STATES = "check_states";

    private CheckBox mUploadKeyCheckbox;
    ListView mUserIds;

    private CertifyKeySpinner mCertifyKeySpinner;

    private long[] mPubMasterKeyIds;

    public static final String[] USER_IDS_PROJECTION = new String[]{
            UserPackets._ID,
            UserPackets.MASTER_KEY_ID,
            UserPackets.USER_ID,
            UserPackets.IS_PRIMARY,
            UserPackets.IS_REVOKED
    };
    private static final int INDEX_MASTER_KEY_ID = 1;
    private static final int INDEX_USER_ID = 2;
    private static final int INDEX_IS_PRIMARY = 3;
    private static final int INDEX_IS_REVOKED = 4;

    private MultiUserIdsAdapter mUserIdsAdapter;
    private Preferences.ProxyPrefs mProxyPrefs;

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);

        mProxyPrefs = Preferences.getPreferences(getActivity()).getProxyPrefs();

        mPubMasterKeyIds = getActivity().getIntent().getLongArrayExtra(CertifyKeyActivity.EXTRA_KEY_IDS);
        if (mPubMasterKeyIds == null) {
            Log.e(Constants.TAG, "List of key ids to certify missing!");
            getActivity().finish();
            return;
        }

        ArrayList<Boolean> checkedStates;
        if (savedInstanceState != null) {
            checkedStates = (ArrayList<Boolean>) savedInstanceState.getSerializable(ARG_CHECK_STATES);
            // key spinner and the checkbox keep their own state
        } else {
            checkedStates = null;

            // preselect certify key id if given
            long certifyKeyId = getActivity().getIntent()
                    .getLongExtra(CertifyKeyActivity.EXTRA_CERTIFY_KEY_ID, Constants.key.none);
            if (certifyKeyId != Constants.key.none) {
                try {
                    CachedPublicKeyRing key = (new ProviderHelper(getActivity())).getCachedPublicKeyRing(certifyKeyId);
                    if (key.canCertify()) {
                        mCertifyKeySpinner.setPreSelectedKeyId(certifyKeyId);
                    }
                } catch (PgpKeyNotFoundException e) {
                    Log.e(Constants.TAG, "certify certify check failed", e);
                }
            }

        }

        mUserIdsAdapter = new MultiUserIdsAdapter(getActivity(), null, 0, checkedStates);
        mUserIds.setAdapter(mUserIdsAdapter);
        mUserIds.setDividerHeight(0);

        getLoaderManager().initLoader(0, null, this);

        OperationResult result = getActivity().getIntent().getParcelableExtra(CertifyKeyActivity.EXTRA_RESULT);
        if (result != null) {
            // display result from import
            result.createNotify(getActivity()).show();
        }
    }

    @Override
    public void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);

        ArrayList<Boolean> states = mUserIdsAdapter.getCheckStates();
        // no proper parceling method available :(
        outState.putSerializable(ARG_CHECK_STATES, states);
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup superContainer, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.certify_key_fragment, null);

        mCertifyKeySpinner = (CertifyKeySpinner) view.findViewById(R.id.certify_key_spinner);
        mUploadKeyCheckbox = (CheckBox) view.findViewById(R.id.sign_key_upload_checkbox);
        mUserIds = (ListView) view.findViewById(R.id.view_key_user_ids);

        // make certify image gray, like action icons
        ImageView vActionCertifyImage =
                (ImageView) view.findViewById(R.id.certify_key_action_certify_image);
        vActionCertifyImage.setColorFilter(getResources().getColor(R.color.tertiary_text_light),
                PorterDuff.Mode.SRC_IN);

        View vCertifyButton = view.findViewById(R.id.certify_key_certify_button);
        vCertifyButton.setOnClickListener(new OnClickListener() {

            @Override
            public void onClick(View v) {
                long selectedKeyId = mCertifyKeySpinner.getSelectedKeyId();
                if (selectedKeyId == Constants.key.none) {
                    Notify.create(getActivity(), getString(R.string.select_key_to_certify),
                            Notify.Style.ERROR).show();
                } else {

                    if (mUploadKeyCheckbox.isChecked() && mProxyPrefs.torEnabled) {
                        Handler ignoreTorHandler = new Handler() {
                            @Override
                            public void handleMessage(Message msg) {
                                mProxyPrefs = new Preferences.ProxyPrefs(false, false, null, -1, null);
                                cryptoOperation();
                            }
                        };
                        if (!OrbotHelper.isOrbotInstalled(getActivity())) {
                            OrbotHelper.getInstallDialogFragmentWithThirdButton(new Messenger(ignoreTorHandler),
                                    R.string.orbot_install_dialog_ignore_tor).show(getActivity()
                                    .getSupportFragmentManager(), "installOrbot");
                        } else if (!OrbotHelper.isOrbotRunning()) {
                            OrbotHelper.getOrbotStartDialogFragment(new Messenger(ignoreTorHandler),
                                    R.string.orbot_install_dialog_ignore_tor).show(getActivity()
                                    .getSupportFragmentManager(), "startOrbot");
                        } else {
                            cryptoOperation();
                        }
                    }
                }
            }
        });

        // If this is a debug build, don't upload by default
        if (Constants.DEBUG) {
            mUploadKeyCheckbox.setChecked(false);
        }

        return view;
    }

    @Override
    public Loader<Cursor> onCreateLoader(int id, Bundle args) {
        Uri uri = UserPackets.buildUserIdsUri();

        String selection, ids[];
        {
            // generate placeholders and string selection args
            ids = new String[mPubMasterKeyIds.length];
            StringBuilder placeholders = new StringBuilder("?");
            for (int i = 0; i < mPubMasterKeyIds.length; i++) {
                ids[i] = Long.toString(mPubMasterKeyIds[i]);
                if (i != 0) {
                    placeholders.append(",?");
                }
            }
            // put together selection string
            selection = UserPackets.IS_REVOKED + " = 0" + " AND "
                    + Tables.USER_PACKETS + "." + UserPackets.MASTER_KEY_ID
                    + " IN (" + placeholders + ")";
        }

        return new CursorLoader(getActivity(), uri,
                USER_IDS_PROJECTION, selection, ids,
                Tables.USER_PACKETS + "." + UserPackets.MASTER_KEY_ID + " ASC"
                        + ", " + Tables.USER_PACKETS + "." + UserPackets.USER_ID + " ASC"
        );
    }

    @Override
    public void onLoadFinished(Loader<Cursor> loader, Cursor data) {

        MatrixCursor matrix = new MatrixCursor(new String[]{
                "_id", "user_data", "grouped"
        }) {
            @Override
            public byte[] getBlob(int column) {
                return super.getBlob(column);
            }
        };
        data.moveToFirst();

        long lastMasterKeyId = 0;
        String lastName = "";
        ArrayList<String> uids = new ArrayList<>();

        boolean header = true;

        // Iterate over all rows
        while (!data.isAfterLast()) {
            long masterKeyId = data.getLong(INDEX_MASTER_KEY_ID);
            String userId = data.getString(INDEX_USER_ID);
            KeyRing.UserId pieces = KeyRing.splitUserId(userId);

            // Two cases:

            boolean grouped = masterKeyId == lastMasterKeyId;
            boolean subGrouped = data.isFirst() || grouped && lastName.equals(pieces.name);
            // Remember for next loop
            lastName = pieces.name;

            Log.d(Constants.TAG, Long.toString(masterKeyId, 16) + (grouped ? "grouped" : "not grouped"));

            if (!subGrouped) {
                // 1. This name should NOT be grouped with the previous, so we flush the buffer

                Parcel p = Parcel.obtain();
                p.writeStringList(uids);
                byte[] d = p.marshall();
                p.recycle();

                matrix.addRow(new Object[]{
                        lastMasterKeyId, d, header ? 1 : 0
                });
                // indicate that we have a header for this masterKeyId
                header = false;

                // Now clear the buffer, and add the new user id, for the next round
                uids.clear();

            }

            // 2. This name should be grouped with the previous, just add to buffer
            uids.add(userId);
            lastMasterKeyId = masterKeyId;

            // If this one wasn't grouped, the next one's gotta be a header
            if (!grouped) {
                header = true;
            }

            // Regardless of the outcome, move to next entry
            data.moveToNext();

        }

        // If there is anything left in the buffer, flush it one last time
        if (!uids.isEmpty()) {

            Parcel p = Parcel.obtain();
            p.writeStringList(uids);
            byte[] d = p.marshall();
            p.recycle();

            matrix.addRow(new Object[]{
                    lastMasterKeyId, d, header ? 1 : 0
            });

        }

        mUserIdsAdapter.swapCursor(matrix);
    }

    @Override
    public void onLoaderReset(Loader<Cursor> loader) {
        mUserIdsAdapter.swapCursor(null);
    }

    @Override
    protected CertifyActionsParcel createOperationInput() {

        // Bail out if there is not at least one user id selected
        ArrayList<CertifyAction> certifyActions = mUserIdsAdapter.getSelectedCertifyActions();
        if (certifyActions.isEmpty()) {
            Notify.create(getActivity(), "No identities selected!",
                    Notify.Style.ERROR).show();
            return null;
        }

        long selectedKeyId = mCertifyKeySpinner.getSelectedKeyId();

        // fill values for this action
        CertifyActionsParcel actionsParcel = new CertifyActionsParcel(selectedKeyId);
        actionsParcel.mCertifyActions.addAll(certifyActions);

        if (mUploadKeyCheckbox.isChecked()) {
            actionsParcel.keyServerUri = Preferences.getPreferences(getActivity()).getPreferredKeyserver();
            actionsParcel.parcelableProxy = mProxyPrefs.parcelableProxy;
        }

        // cached for next cryptoOperation loop
        cacheActionsParcel(actionsParcel);

        return actionsParcel;
    }

    @Override
    protected void onCryptoOperationSuccess(CertifyResult result) {
        Intent intent = new Intent();
        intent.putExtra(CertifyResult.EXTRA_RESULT, result);
        getActivity().setResult(Activity.RESULT_OK, intent);
        getActivity().finish();
    }

    @Override
    protected void onCryptoOperationCancelled() {
        super.onCryptoOperationCancelled();
    }

}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/CreateKeyYubiKeyImportFragment.java
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

import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;

import android.app.Activity;
import android.app.ProgressDialog;
import android.content.Intent;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.support.v4.app.Fragment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.widget.TextView;

import org.spongycastle.util.encoders.Hex;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.keyimport.ParcelableKeyRing;
import org.sufficientlysecure.keychain.operations.results.DecryptVerifyResult;
import org.sufficientlysecure.keychain.operations.results.ImportKeyResult;
import org.sufficientlysecure.keychain.provider.KeychainContract.KeyRings;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.ui.CreateKeyActivity.FragAction;
import org.sufficientlysecure.keychain.ui.CreateKeyActivity.NfcListenerFragment;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils;
import org.sufficientlysecure.keychain.util.ParcelableProxy;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;


public class CreateKeyYubiKeyImportFragment extends Fragment implements NfcListenerFragment {

    private static final String ARG_FINGERPRINT = "fingerprint";
    public static final String ARG_AID = "aid";
    public static final String ARG_USER_ID = "user_ids";

    CreateKeyActivity mCreateKeyActivity;

    private byte[] mNfcFingerprints;
    private byte[] mNfcAid;
    private String mNfcUserId;
    private String mNfcFingerprint;
    private ImportKeysListFragment mListFragment;
    private TextView vSerNo;
    private TextView vUserId;

    public static Fragment createInstance(byte[] scannedFingerprints, byte[] nfcAid, String userId) {

        CreateKeyYubiKeyImportFragment frag = new CreateKeyYubiKeyImportFragment();

        Bundle args = new Bundle();
        args.putByteArray(ARG_FINGERPRINT, scannedFingerprints);
        args.putByteArray(ARG_AID, nfcAid);
        args.putString(ARG_USER_ID, userId);
        frag.setArguments(args);

        return frag;
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Bundle args = savedInstanceState != null ? savedInstanceState : getArguments();

        mNfcFingerprints = args.getByteArray(ARG_FINGERPRINT);
        mNfcAid = args.getByteArray(ARG_AID);
        mNfcUserId = args.getString(ARG_USER_ID);

        byte[] fp = new byte[20];
        ByteBuffer.wrap(fp).put(mNfcFingerprints, 0, 20);
        mNfcFingerprint = KeyFormattingUtils.convertFingerprintToHex(fp);

    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.create_yubikey_import_fragment, container, false);

        vSerNo = (TextView) view.findViewById(R.id.yubikey_serno);
        vUserId = (TextView) view.findViewById(R.id.yubikey_userid);

        {
            View mBackButton = view.findViewById(R.id.create_key_back_button);
            mBackButton.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    if (getFragmentManager().getBackStackEntryCount() == 0) {
                        getActivity().setResult(Activity.RESULT_CANCELED);
                        getActivity().finish();
                    } else {
                        mCreateKeyActivity.loadFragment(null, FragAction.TO_LEFT);
                    }
                }
            });

            View mNextButton = view.findViewById(R.id.create_key_next_button);
            mNextButton.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {

                    final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(getActivity()).getProxyPrefs();
                    Runnable ignoreTor = new Runnable() {
                        @Override
                        public void run() {
                            importKey(new ParcelableProxy(null, -1, null));
                        }
                    };

                    if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                            getActivity())) {
                        importKey(proxyPrefs.parcelableProxy);
                    }
                }
            });
        }

        mListFragment = ImportKeysListFragment.newInstance(null, null,
                "0x" + mNfcFingerprint, true, null);

        view.findViewById(R.id.button_search).setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(getActivity()).getProxyPrefs();
                Runnable ignoreTor = new Runnable() {
                    @Override
                    public void run() {
                        refreshSearch(new ParcelableProxy(null, -1, null));
                    }
                };

                if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                        getActivity())) {
                    refreshSearch(proxyPrefs.parcelableProxy);
                }
            }
        });

        setData();

        getFragmentManager().beginTransaction()
                .replace(R.id.yubikey_import_fragment, mListFragment, "yubikey_import")
                .commit();

        return view;
    }

    @Override
    public void onSaveInstanceState(Bundle args) {
        super.onSaveInstanceState(args);

        args.putByteArray(ARG_FINGERPRINT, mNfcFingerprints);
        args.putByteArray(ARG_AID, mNfcAid);
        args.putString(ARG_USER_ID, mNfcUserId);
    }

    @Override
    public void onAttach(Activity activity) {
        super.onAttach(activity);
        mCreateKeyActivity = (CreateKeyActivity) getActivity();
    }

    public void setData() {
        String serno = Hex.toHexString(mNfcAid, 10, 4);
        vSerNo.setText(getString(R.string.yubikey_serno, serno));

        if (!mNfcUserId.isEmpty()) {
            vUserId.setText(getString(R.string.yubikey_key_holder, mNfcUserId));
        } else {
            vUserId.setText(getString(R.string.yubikey_key_holder_not_set));
        }
    }

    public void refreshSearch(ParcelableProxy parcelableProxy) {
        // TODO: PHILIP verify proxy implementation in YubiKey parts
        mListFragment.loadNew(new ImportKeysListFragment.CloudLoaderState("0x" + mNfcFingerprint,
                Preferences.getPreferences(getActivity()).getCloudSearchPrefs()), parcelableProxy);
    }

    public void importKey(ParcelableProxy parcelableProxy) {

        // Message is received after decrypting is done in KeychainService
        ServiceProgressHandler saveHandler = new ServiceProgressHandler(getActivity()) {
            @Override
            public void handleMessage(Message message) {
                // handle messages by standard KeychainIntentServiceHandler first
                super.handleMessage(message);

                if (message.arg1 == MessageStatus.OKAY.ordinal()) {
                    // get returned data bundle
                    Bundle returnData = message.getData();

                    ImportKeyResult result =
                            returnData.getParcelable(DecryptVerifyResult.EXTRA_RESULT);

                    long[] masterKeyIds = result.getImportedMasterKeyIds();

                    // TODO handle masterKeyIds.length != 1...? sorta outlandish scenario

                    if (!result.success() || masterKeyIds.length == 0) {
                        result.createNotify(getActivity()).show();
                        return;
                    }

                    Intent intent = new Intent(getActivity(), ViewKeyActivity.class);
                    // use the imported masterKeyId, not the one from the yubikey, because
                    // that one might* just have been a subkey of the imported key
                    intent.setData(KeyRings.buildGenericKeyRingUri(masterKeyIds[0]));
                    intent.putExtra(ViewKeyActivity.EXTRA_DISPLAY_RESULT, result);
                    intent.putExtra(ViewKeyActivity.EXTRA_NFC_AID, mNfcAid);
                    intent.putExtra(ViewKeyActivity.EXTRA_NFC_USER_ID, mNfcUserId);
                    intent.putExtra(ViewKeyActivity.EXTRA_NFC_FINGERPRINTS, mNfcFingerprints);
                    startActivity(intent);
                    getActivity().finish();

                }

            }
        };

        // Send all information needed to service to decrypt in other thread
        Intent intent = new Intent(getActivity(), KeychainService.class);

        // fill values for this action
        Bundle data = new Bundle();

        intent.setAction(KeychainService.ACTION_IMPORT_KEYRING);

        ArrayList<ParcelableKeyRing> keyList = new ArrayList<>();
        keyList.add(new ParcelableKeyRing(mNfcFingerprint, null, null));
        data.putParcelableArrayList(KeychainService.IMPORT_KEY_LIST, keyList);

        {
            Preferences prefs = Preferences.getPreferences(getActivity());
            Preferences.CloudSearchPrefs cloudPrefs =
                    new Preferences.CloudSearchPrefs(true, true, prefs.getPreferredKeyserver());
            data.putString(KeychainService.IMPORT_KEY_SERVER, cloudPrefs.keyserver);
        }

        data.putParcelable(KeychainService.EXTRA_PARCELABLE_PROXY, parcelableProxy);

        intent.putExtra(KeychainService.EXTRA_DATA, data);

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(saveHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        saveHandler.showProgressDialog(
                getString(R.string.progress_importing),
                ProgressDialog.STYLE_HORIZONTAL, false
        );

        // start service with intent
        getActivity().startService(intent);

    }

    @Override
    public void onNfcPerform() throws IOException {

        mNfcFingerprints = mCreateKeyActivity.nfcGetFingerprints();
        mNfcAid = mCreateKeyActivity.nfcGetAid();
        mNfcUserId = mCreateKeyActivity.nfcGetUserId();

        byte[] fp = new byte[20];
        ByteBuffer.wrap(fp).put(mNfcFingerprints, 0, 20);
        mNfcFingerprint = KeyFormattingUtils.convertFingerprintToHex(fp);

        setData();

        Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(getActivity()).getProxyPrefs();
        Runnable ignoreTor = new Runnable() {
            @Override
            public void run() {
                refreshSearch(new ParcelableProxy(null, -1, null));
            }
        };

        if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                getActivity())) {
            refreshSearch(proxyPrefs.parcelableProxy);
        }

    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/DecryptFragment.java
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

import java.util.ArrayList;

import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.support.v4.app.LoaderManager;
import android.support.v4.content.CursorLoader;
import android.support.v4.content.Loader;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.openintents.openpgp.OpenPgpSignatureResult;
import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.keyimport.ParcelableKeyRing;
import org.sufficientlysecure.keychain.operations.results.DecryptVerifyResult;
import org.sufficientlysecure.keychain.operations.results.ImportKeyResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.pgp.KeyRing;
import org.sufficientlysecure.keychain.pgp.PgpDecryptVerifyInputParcel;
import org.sufficientlysecure.keychain.pgp.exception.PgpKeyNotFoundException;
import org.sufficientlysecure.keychain.provider.KeychainContract;
import org.sufficientlysecure.keychain.provider.KeychainContract.KeyRings;
import org.sufficientlysecure.keychain.provider.ProviderHelper;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.ui.base.CachingCryptoOperationFragment;
import org.sufficientlysecure.keychain.ui.base.CryptoOperationFragment;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils.State;
import org.sufficientlysecure.keychain.ui.util.Notify;
import org.sufficientlysecure.keychain.ui.util.Notify.Style;
import org.sufficientlysecure.keychain.util.ParcelableProxy;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

public abstract class DecryptFragment
        extends CachingCryptoOperationFragment<PgpDecryptVerifyInputParcel, DecryptVerifyResult>
        implements LoaderManager.LoaderCallbacks<Cursor> {

    public static final int LOADER_ID_UNIFIED = 0;
    public static final String ARG_DECRYPT_VERIFY_RESULT = "decrypt_verify_result";

    protected LinearLayout mResultLayout;
    protected ImageView mEncryptionIcon;
    protected TextView mEncryptionText;
    protected ImageView mSignatureIcon;
    protected TextView mSignatureText;
    protected View mSignatureLayout;
    protected TextView mSignatureName;
    protected TextView mSignatureEmail;
    protected TextView mSignatureAction;

    private LinearLayout mContentLayout;
    private LinearLayout mErrorOverlayLayout;

    private OpenPgpSignatureResult mSignatureResult;
    private DecryptVerifyResult mDecryptVerifyResult;

    @Override
    public void onViewCreated(View view, Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        // NOTE: These views are inside the activity!
        mResultLayout = (LinearLayout) getActivity().findViewById(R.id.result_main_layout);
        mResultLayout.setVisibility(View.GONE);
        mEncryptionIcon = (ImageView) getActivity().findViewById(R.id.result_encryption_icon);
        mEncryptionText = (TextView) getActivity().findViewById(R.id.result_encryption_text);
        mSignatureIcon = (ImageView) getActivity().findViewById(R.id.result_signature_icon);
        mSignatureText = (TextView) getActivity().findViewById(R.id.result_signature_text);
        mSignatureLayout = getActivity().findViewById(R.id.result_signature_layout);
        mSignatureName = (TextView) getActivity().findViewById(R.id.result_signature_name);
        mSignatureEmail = (TextView) getActivity().findViewById(R.id.result_signature_email);
        mSignatureAction = (TextView) getActivity().findViewById(R.id.result_signature_action);

        // Overlay
        mContentLayout = (LinearLayout) view.findViewById(R.id.decrypt_content);
        mErrorOverlayLayout = (LinearLayout) view.findViewById(R.id.decrypt_error_overlay);
        Button vErrorOverlayButton = (Button) view.findViewById(R.id.decrypt_error_overlay_button);
        vErrorOverlayButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mErrorOverlayLayout.setVisibility(View.GONE);
                mContentLayout.setVisibility(View.VISIBLE);
            }
        });
    }

    @Override
    public void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);

        outState.putParcelable(ARG_DECRYPT_VERIFY_RESULT, mDecryptVerifyResult);
    }

    @Override
    public void onViewStateRestored(Bundle savedInstanceState) {
        super.onViewStateRestored(savedInstanceState);

        if (savedInstanceState == null) {
            return;
        }

        DecryptVerifyResult result = savedInstanceState.getParcelable(ARG_DECRYPT_VERIFY_RESULT);
        if (result != null) {
            loadVerifyResult(result);
        }
    }

    private void lookupUnknownKey(long unknownKeyId, ParcelableProxy parcelableProxy) {

        // Message is received after importing is done in KeychainService
        ServiceProgressHandler serviceHandler = new ServiceProgressHandler(getActivity()) {
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

                    final ImportKeyResult result =
                            returnData.getParcelable(OperationResult.EXTRA_RESULT);

                    result.createNotify(getActivity()).show();

                    getLoaderManager().restartLoader(LOADER_ID_UNIFIED, null, DecryptFragment.this);
                }
            }
        };

        // fill values for this action
        Bundle data = new Bundle();

        // search config
        {
            Preferences prefs = Preferences.getPreferences(getActivity());
            Preferences.CloudSearchPrefs cloudPrefs =
                    new Preferences.CloudSearchPrefs(true, true, prefs.getPreferredKeyserver());
            data.putString(KeychainService.IMPORT_KEY_SERVER, cloudPrefs.keyserver);
        }

        {
            ParcelableKeyRing keyEntry = new ParcelableKeyRing(null,
                    KeyFormattingUtils.convertKeyIdToHex(unknownKeyId), null);
            ArrayList<ParcelableKeyRing> selectedEntries = new ArrayList<>();
            selectedEntries.add(keyEntry);

            data.putParcelableArrayList(KeychainService.IMPORT_KEY_LIST, selectedEntries);
        }

        data.putParcelable(KeychainService.EXTRA_PARCELABLE_PROXY, parcelableProxy);

        // Send all information needed to service to query keys in other thread
        Intent intent = new Intent(getActivity(), KeychainService.class);
        intent.setAction(KeychainService.ACTION_IMPORT_KEYRING);
        intent.putExtra(KeychainService.EXTRA_DATA, data);

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(serviceHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        getActivity().startService(intent);
    }

    private void showKey(long keyId) {
        try {

            Intent viewKeyIntent = new Intent(getActivity(), ViewKeyActivity.class);
            long masterKeyId = new ProviderHelper(getActivity()).getCachedPublicKeyRing(
                    KeyRings.buildUnifiedKeyRingsFindBySubkeyUri(keyId)
            ).getMasterKeyId();
            viewKeyIntent.setData(KeyRings.buildGenericKeyRingUri(masterKeyId));
            startActivity(viewKeyIntent);

        } catch (PgpKeyNotFoundException e) {
            Notify.create(getActivity(), R.string.error_key_not_found, Style.ERROR);
        }
    }

    /**
     * @return returns false if signature is invalid, key is revoked or expired.
     */
    protected void loadVerifyResult(DecryptVerifyResult decryptVerifyResult) {

        mDecryptVerifyResult = decryptVerifyResult;
        mSignatureResult = decryptVerifyResult.getSignatureResult();

        mResultLayout.setVisibility(View.VISIBLE);

        // unsigned data
        if (mSignatureResult == null) {

            setSignatureLayoutVisibility(View.GONE);

            mSignatureText.setText(R.string.decrypt_result_no_signature);
            KeyFormattingUtils.setStatusImage(getActivity(), mSignatureIcon, mSignatureText, State.NOT_SIGNED);
            mEncryptionText.setText(R.string.decrypt_result_encrypted);
            KeyFormattingUtils.setStatusImage(getActivity(), mEncryptionIcon, mEncryptionText, State.ENCRYPTED);

            getLoaderManager().destroyLoader(LOADER_ID_UNIFIED);

            mErrorOverlayLayout.setVisibility(View.GONE);
            mContentLayout.setVisibility(View.VISIBLE);

            onVerifyLoaded(true);

            return;
        }

        if (mSignatureResult.isSignatureOnly()) {
            mEncryptionText.setText(R.string.decrypt_result_not_encrypted);
            KeyFormattingUtils.setStatusImage(getActivity(), mEncryptionIcon, mEncryptionText, State.NOT_ENCRYPTED);
        } else {
            mEncryptionText.setText(R.string.decrypt_result_encrypted);
            KeyFormattingUtils.setStatusImage(getActivity(), mEncryptionIcon, mEncryptionText, State.ENCRYPTED);
        }

        getLoaderManager().restartLoader(LOADER_ID_UNIFIED, null, this);
    }

    private void setSignatureLayoutVisibility(int visibility) {
        mSignatureLayout.setVisibility(visibility);
    }

    private void setShowAction(final long signatureKeyId) {
        mSignatureAction.setText(R.string.decrypt_result_action_show);
        mSignatureAction.setCompoundDrawablesWithIntrinsicBounds(0, 0, R.drawable.ic_vpn_key_grey_24dp, 0);
        mSignatureLayout.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showKey(signatureKeyId);
            }
        });
    }

    // These are the rows that we will retrieve.
    static final String[] UNIFIED_PROJECTION = new String[]{
            KeychainContract.KeyRings._ID,
            KeychainContract.KeyRings.MASTER_KEY_ID,
            KeychainContract.KeyRings.USER_ID,
            KeychainContract.KeyRings.VERIFIED,
            KeychainContract.KeyRings.HAS_ANY_SECRET,
    };

    @SuppressWarnings("unused")
    static final int INDEX_MASTER_KEY_ID = 1;
    static final int INDEX_USER_ID = 2;
    static final int INDEX_VERIFIED = 3;
    static final int INDEX_HAS_ANY_SECRET = 4;

    @Override
    public Loader<Cursor> onCreateLoader(int id, Bundle args) {
        if (id != LOADER_ID_UNIFIED) {
            return null;
        }

        Uri baseUri = KeychainContract.KeyRings.buildUnifiedKeyRingsFindBySubkeyUri(
                mSignatureResult.getKeyId());
        return new CursorLoader(getActivity(), baseUri, UNIFIED_PROJECTION, null, null, null);
    }

    @Override
    public void onLoadFinished(Loader<Cursor> loader, Cursor data) {

        if (loader.getId() != LOADER_ID_UNIFIED) {
            return;
        }

        // If the key is unknown, show it as such
        if (data.getCount() == 0 || !data.moveToFirst()) {
            showUnknownKeyStatus();
            return;
        }

        long signatureKeyId = mSignatureResult.getKeyId();

        String userId = data.getString(INDEX_USER_ID);
        KeyRing.UserId userIdSplit = KeyRing.splitUserId(userId);
        if (userIdSplit.name != null) {
            mSignatureName.setText(userIdSplit.name);
        } else {
            mSignatureName.setText(R.string.user_id_no_name);
        }
        if (userIdSplit.email != null) {
            mSignatureEmail.setText(userIdSplit.email);
        } else {
            mSignatureEmail.setText(KeyFormattingUtils.beautifyKeyIdWithPrefix(
                    getActivity(), mSignatureResult.getKeyId()));
        }

        // NOTE: Don't use revoked and expired fields from database, they don't show
        // revoked/expired subkeys
        boolean isRevoked = mSignatureResult.getStatus() == OpenPgpSignatureResult.SIGNATURE_KEY_REVOKED;
        boolean isExpired = mSignatureResult.getStatus() == OpenPgpSignatureResult.SIGNATURE_KEY_EXPIRED;
        boolean isVerified = data.getInt(INDEX_VERIFIED) > 0;
        boolean isYours = data.getInt(INDEX_HAS_ANY_SECRET) != 0;

        if (isRevoked) {
            mSignatureText.setText(R.string.decrypt_result_signature_revoked_key);
            KeyFormattingUtils.setStatusImage(getActivity(), mSignatureIcon, mSignatureText, State.REVOKED);

            setSignatureLayoutVisibility(View.VISIBLE);
            setShowAction(signatureKeyId);

            mErrorOverlayLayout.setVisibility(View.VISIBLE);
            mContentLayout.setVisibility(View.GONE);

            onVerifyLoaded(false);

        } else if (isExpired) {
            mSignatureText.setText(R.string.decrypt_result_signature_expired_key);
            KeyFormattingUtils.setStatusImage(getActivity(), mSignatureIcon, mSignatureText, State.EXPIRED);

            setSignatureLayoutVisibility(View.VISIBLE);
            setShowAction(signatureKeyId);

            mErrorOverlayLayout.setVisibility(View.GONE);
            mContentLayout.setVisibility(View.VISIBLE);

            onVerifyLoaded(true);

        } else if (isYours) {

            mSignatureText.setText(R.string.decrypt_result_signature_secret);
            KeyFormattingUtils.setStatusImage(getActivity(), mSignatureIcon, mSignatureText, State.VERIFIED);

            setSignatureLayoutVisibility(View.VISIBLE);
            setShowAction(signatureKeyId);

            mErrorOverlayLayout.setVisibility(View.GONE);
            mContentLayout.setVisibility(View.VISIBLE);

            onVerifyLoaded(true);

        } else if (isVerified) {
            mSignatureText.setText(R.string.decrypt_result_signature_certified);
            KeyFormattingUtils.setStatusImage(getActivity(), mSignatureIcon, mSignatureText, State.VERIFIED);

            setSignatureLayoutVisibility(View.VISIBLE);
            setShowAction(signatureKeyId);

            mErrorOverlayLayout.setVisibility(View.GONE);
            mContentLayout.setVisibility(View.VISIBLE);

            onVerifyLoaded(true);

        } else {
            mSignatureText.setText(R.string.decrypt_result_signature_uncertified);
            KeyFormattingUtils.setStatusImage(getActivity(), mSignatureIcon, mSignatureText, State.UNVERIFIED);

            setSignatureLayoutVisibility(View.VISIBLE);
            setShowAction(signatureKeyId);

            mErrorOverlayLayout.setVisibility(View.GONE);
            mContentLayout.setVisibility(View.VISIBLE);

            onVerifyLoaded(true);
        }

    }

    @Override
    public void onLoaderReset(Loader<Cursor> loader) {

        if (loader.getId() != LOADER_ID_UNIFIED) {
            return;
        }

        setSignatureLayoutVisibility(View.GONE);
    }

    private void showUnknownKeyStatus() {

        final long signatureKeyId = mSignatureResult.getKeyId();

        int result = mSignatureResult.getStatus();
        if (result != OpenPgpSignatureResult.SIGNATURE_KEY_MISSING
                && result != OpenPgpSignatureResult.SIGNATURE_ERROR) {
            Log.e(Constants.TAG, "got missing status for non-missing key, shouldn't happen!");
        }

        String userId = mSignatureResult.getPrimaryUserId();
        KeyRing.UserId userIdSplit = KeyRing.splitUserId(userId);
        if (userIdSplit.name != null) {
            mSignatureName.setText(userIdSplit.name);
        } else {
            mSignatureName.setText(R.string.user_id_no_name);
        }
        if (userIdSplit.email != null) {
            mSignatureEmail.setText(userIdSplit.email);
        } else {
            mSignatureEmail.setText(KeyFormattingUtils.beautifyKeyIdWithPrefix(
                    getActivity(), mSignatureResult.getKeyId()));
        }

        switch (mSignatureResult.getStatus()) {

            case OpenPgpSignatureResult.SIGNATURE_KEY_MISSING: {
                mSignatureText.setText(R.string.decrypt_result_signature_missing_key);
                KeyFormattingUtils.setStatusImage(getActivity(), mSignatureIcon, mSignatureText, State.UNKNOWN_KEY);

                setSignatureLayoutVisibility(View.VISIBLE);
                mSignatureAction.setText(R.string.decrypt_result_action_Lookup);
                mSignatureAction
                        .setCompoundDrawablesWithIntrinsicBounds(0, 0, R.drawable.ic_file_download_grey_24dp, 0);
                mSignatureLayout.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(getActivity())
                                .getProxyPrefs();
                        Runnable ignoreTor = new Runnable() {
                            @Override
                            public void run() {
                                lookupUnknownKey(signatureKeyId, new ParcelableProxy(null, -1, null));
                            }
                        };

                        if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                                getActivity())) {
                            lookupUnknownKey(signatureKeyId, proxyPrefs.parcelableProxy);
                        }
                    }
                });

                mErrorOverlayLayout.setVisibility(View.GONE);
                mContentLayout.setVisibility(View.VISIBLE);

                onVerifyLoaded(true);

                break;
            }

            case OpenPgpSignatureResult.SIGNATURE_ERROR: {
                mSignatureText.setText(R.string.decrypt_result_invalid_signature);
                KeyFormattingUtils.setStatusImage(getActivity(), mSignatureIcon, mSignatureText, State.INVALID);

                setSignatureLayoutVisibility(View.GONE);

                mErrorOverlayLayout.setVisibility(View.VISIBLE);
                mContentLayout.setVisibility(View.GONE);

                onVerifyLoaded(false);
                break;
            }

        }

    }

    protected abstract void onVerifyLoaded(boolean hideErrorOverlay);

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
import org.sufficientlysecure.keychain.service.KeychainService;
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
     * loads the CloudFragment, which consists of the search bar, search button and settings icon
     * visually.
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
            final ImportKeyResult result =
                    returnData.getParcelable(OperationResult.EXTRA_RESULT);
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
        Intent intent = new Intent(this, KeychainService.class);

        intent.setAction(KeychainService.ACTION_IMPORT_KEYRING);

        // fill values for this action
        Bundle data = new Bundle();

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

                intent.putExtra(KeychainService.EXTRA_DATA, data);

                // Create a new Messenger for the communication back
                Messenger messenger = new Messenger(serviceHandler);
                intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

                // show progress dialog
                serviceHandler.showProgressDialog(
                        getString(R.string.progress_importing),
                        ProgressDialog.STYLE_HORIZONTAL,
                        true
                );

                // start service with intent
                startService(intent);
            } catch (IOException e) {
                Log.e(Constants.TAG, "Problem writing cache file", e);
                Notify.create(this, "Problem writing cache file!", Notify.Style.ERROR)
                        .show((ViewGroup) findViewById(R.id.import_snackbar));
            }
        } else if (ls instanceof ImportKeysListFragment.CloudLoaderState) {
            ImportKeysListFragment.CloudLoaderState sls = (ImportKeysListFragment.CloudLoaderState) ls;

            data.putString(KeychainService.IMPORT_KEY_SERVER, sls.mCloudPrefs.keyserver);

            data.putParcelable(KeychainService.EXTRA_PARCELABLE_PROXY, mProxyPrefs.parcelableProxy);

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
            data.putParcelableArrayList(KeychainService.IMPORT_KEY_LIST, keys);

            intent.putExtra(KeychainService.EXTRA_DATA, data);

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
    }

    @Override
    protected void onNfcPerform() throws IOException {
        // this displays the key or moves to the yubikey import dialogue.
        super.onNfcPerform();
        // either way, finish afterwards
        finish();
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/ImportKeysProxyActivity.java
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

import android.annotation.TargetApi;
import android.app.ProgressDialog;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.net.Uri;
import android.nfc.NdefMessage;
import android.nfc.NfcAdapter;
import android.os.Build;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.os.Parcelable;
import android.support.v4.app.FragmentActivity;
import android.widget.Toast;

import com.google.zxing.integration.android.IntentIntegrator;
import com.google.zxing.integration.android.IntentResult;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.intents.OpenKeychainIntents;
import org.sufficientlysecure.keychain.keyimport.ParcelableKeyRing;
import org.sufficientlysecure.keychain.operations.results.ImportKeyResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult.LogType;
import org.sufficientlysecure.keychain.operations.results.SingletonResult;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.util.IntentIntegratorSupportV4;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.ParcelableProxy;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

import java.util.ArrayList;
import java.util.Locale;

/**
 * Proxy activity (just a transparent content view) to scan QR Codes using the Barcode Scanner app
 */
public class ImportKeysProxyActivity extends FragmentActivity {

    public static final String ACTION_QR_CODE_API = OpenKeychainIntents.IMPORT_KEY_FROM_QR_CODE;
    // implies activity returns scanned fingerprint as extra and does not import
    public static final String ACTION_SCAN_WITH_RESULT = Constants.INTENT_PREFIX + "SCAN_QR_CODE_WITH_RESULT";
    public static final String ACTION_SCAN_IMPORT = Constants.INTENT_PREFIX + "SCAN_QR_CODE_IMPORT";

    public static final String EXTRA_FINGERPRINT = "fingerprint";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // this activity itself has no content view (see manifest)

        handleActions(getIntent());
    }

    protected void handleActions(Intent intent) {
        String action = intent.getAction();
        Uri dataUri = intent.getData();
        String scheme = intent.getScheme();

        if (scheme != null && scheme.toLowerCase(Locale.ENGLISH).equals(Constants.FINGERPRINT_SCHEME)) {
            // Scanning a fingerprint directly with Barcode Scanner, thus we already have scanned

            processScannedContent(dataUri);
        } else if (ACTION_SCAN_WITH_RESULT.equals(action)
                || ACTION_SCAN_IMPORT.equals(action) || ACTION_QR_CODE_API.equals(action)) {
            IntentIntegrator integrator = new IntentIntegrator(this);
            integrator.setDesiredBarcodeFormats(IntentIntegrator.QR_CODE_TYPES)
                    .setPrompt(getString(R.string.import_qr_code_text))
                    .setResultDisplayDuration(0);
            integrator.setOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
            integrator.initiateScan();
        } else if (NfcAdapter.ACTION_NDEF_DISCOVERED.equals(getIntent().getAction())) {
            // Check to see if the Activity started due to an Android Beam
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN) {
                handleActionNdefDiscovered(getIntent());
            } else {
                Log.e(Constants.TAG, "Android Beam not supported by Android < 4.1");
                finish();
            }
        } else {
            Log.e(Constants.TAG, "No valid scheme or action given!");
            finish();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == IntentIntegratorSupportV4.REQUEST_CODE) {
            IntentResult scanResult = IntentIntegratorSupportV4.parseActivityResult(requestCode,
                    resultCode, data);

            if (scanResult == null || scanResult.getFormatName() == null) {
                Log.e(Constants.TAG, "scanResult or formatName null! Should not happen!");
                finish();
                return;
            }

            String scannedContent = scanResult.getContents();
            processScannedContent(scannedContent);

            return;
        }
        // if a result has been returned, return it down to other activity
        if (data != null && data.hasExtra(OperationResult.EXTRA_RESULT)) {
            returnResult(data);
        } else {
            super.onActivityResult(requestCode, resultCode, data);
            finish();
        }
    }

    private void processScannedContent(String content) {
        Uri uri = Uri.parse(content);
        processScannedContent(uri);
    }

    private void processScannedContent(Uri uri) {
        String action = getIntent().getAction();

        Log.d(Constants.TAG, "scanned: " + uri);

        // example: openpgp4fpr:73EE2314F65FA92EC2390D3A718C070100012282
        if (uri == null || uri.getScheme() == null ||
                !uri.getScheme().toLowerCase(Locale.ENGLISH).equals(Constants.FINGERPRINT_SCHEME)) {
            SingletonResult result = new SingletonResult(
                    SingletonResult.RESULT_ERROR, LogType.MSG_WRONG_QR_CODE);
            Intent intent = new Intent();
            intent.putExtra(SingletonResult.EXTRA_RESULT, result);
            returnResult(intent);
            return;
        }
        final String fingerprint = uri.getEncodedSchemeSpecificPart().toLowerCase(Locale.ENGLISH);
        if (!fingerprint.matches("[a-fA-F0-9]{40}")) {
            SingletonResult result = new SingletonResult(
                    SingletonResult.RESULT_ERROR, LogType.MSG_WRONG_QR_CODE_FP);
            Intent intent = new Intent();
            intent.putExtra(SingletonResult.EXTRA_RESULT, result);
            returnResult(intent);
            return;
        }

        if (ACTION_SCAN_WITH_RESULT.equals(action)) {
            Intent result = new Intent();
            result.putExtra(EXTRA_FINGERPRINT, fingerprint);
            setResult(RESULT_OK, result);
            finish();
        } else {
            final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(this).getProxyPrefs();
            Runnable ignoreTor = new Runnable() {
                @Override
                public void run() {
                    importKeys(fingerprint, new ParcelableProxy(null, -1, null));
                }
            };

            if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                    this)) {
                importKeys(fingerprint, proxyPrefs.parcelableProxy);
            }
        }

    }

    public void returnResult(Intent data) {
        String action = getIntent().getAction();

        if (ACTION_QR_CODE_API.equals(action)) {
            // display last log message but as Toast for calls from outside OpenKeychain
            OperationResult result = data.getParcelableExtra(OperationResult.EXTRA_RESULT);
            String str = getString(result.getLog().getLast().mType.getMsgId());
            Toast.makeText(this, str, Toast.LENGTH_LONG).show();
            finish();
        } else {
            setResult(RESULT_OK, data);
            finish();
        }
    }

    public void importKeys(byte[] keyringData, ParcelableProxy parcelableProxy) {
        ParcelableKeyRing keyEntry = new ParcelableKeyRing(keyringData);
        ArrayList<ParcelableKeyRing> selectedEntries = new ArrayList<>();
        selectedEntries.add(keyEntry);

        startImportService(selectedEntries, parcelableProxy);
    }

    public void importKeys(String fingerprint, ParcelableProxy parcelableProxy) {
        ParcelableKeyRing keyEntry = new ParcelableKeyRing(fingerprint, null, null);
        ArrayList<ParcelableKeyRing> selectedEntries = new ArrayList<>();
        selectedEntries.add(keyEntry);

        startImportService(selectedEntries, parcelableProxy);
    }

    private void startImportService(ArrayList<ParcelableKeyRing> keyRings, ParcelableProxy parcelableProxy) {

        // Message is received after importing is done in KeychainService
        ServiceProgressHandler serviceHandler = new ServiceProgressHandler(this) {
            @Override
            public void handleMessage(Message message) {
                // handle messages by standard KeychainIntentServiceHandler first
                super.handleMessage(message);

                if (message.arg1 == MessageStatus.OKAY.ordinal()) {
                    // get returned data bundle
                    Bundle returnData = message.getData();
                    if (returnData == null) {
                        finish();
                        return;
                    }
                    final ImportKeyResult result =
                            returnData.getParcelable(OperationResult.EXTRA_RESULT);
                    if (result == null) {
                        Log.e(Constants.TAG, "result == null");
                        finish();
                        return;
                    }

                    if (!result.success()) {
                        // only return if no success...
                        Intent data = new Intent();
                        data.putExtras(returnData);
                        returnResult(data);
                        return;
                    }

                    Intent certifyIntent = new Intent(ImportKeysProxyActivity.this,
                            CertifyKeyActivity.class);
                    certifyIntent.putExtra(CertifyKeyActivity.EXTRA_RESULT, result);
                    certifyIntent.putExtra(CertifyKeyActivity.EXTRA_KEY_IDS,
                            result.getImportedMasterKeyIds());
                    startActivityForResult(certifyIntent, 0);
                }
            }
        };

        // fill values for this action
        Bundle data = new Bundle();

        // search config
        {
            Preferences prefs = Preferences.getPreferences(this);
            Preferences.CloudSearchPrefs cloudPrefs =
                    new Preferences.CloudSearchPrefs(true, true, prefs.getPreferredKeyserver());
            data.putString(KeychainService.IMPORT_KEY_SERVER, cloudPrefs.keyserver);
        }

        data.putParcelableArrayList(KeychainService.IMPORT_KEY_LIST, keyRings);

        data.putParcelable(KeychainService.EXTRA_PARCELABLE_PROXY, parcelableProxy);

        // Send all information needed to service to query keys in other thread
        Intent intent = new Intent(this, KeychainService.class);
        intent.setAction(KeychainService.ACTION_IMPORT_KEYRING);
        intent.putExtra(KeychainService.EXTRA_DATA, data);

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(serviceHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        // show progress dialog
        serviceHandler.showProgressDialog(
                getString(R.string.progress_importing),
                ProgressDialog.STYLE_HORIZONTAL, true);

        // start service with intent
        startService(intent);
    }

    /**
     * NFC: Parses the NDEF Message from the intent and prints to the TextView
     */
    @TargetApi(Build.VERSION_CODES.JELLY_BEAN)
    void handleActionNdefDiscovered(Intent intent) {
        Parcelable[] rawMsgs = intent.getParcelableArrayExtra(NfcAdapter.EXTRA_NDEF_MESSAGES);
        // only one message sent during the beam
        NdefMessage msg = (NdefMessage) rawMsgs[0];
        // record 0 contains the MIME type, record 1 is the AAR, if present
        final byte[] receivedKeyringBytes = msg.getRecords()[0].getPayload();
        final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(this)
                .getProxyPrefs();
        Runnable ignoreTor = new Runnable() {
            @Override
            public void run() {
                importKeys(receivedKeyringBytes, new ParcelableProxy(null, -1, null));
            }
        };

        if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs, this)) {
            importKeys(receivedKeyringBytes, proxyPrefs.parcelableProxy);
        }
    }

}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/KeyListFragment.java
/*
 * Copyright (C) 2013-2015 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2014-2015 Vincent Breitmoser <v.breitmoser@mugenguild.com>
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

import android.animation.ObjectAnimator;
import android.annotation.TargetApi;
import android.app.Activity;
import android.app.ProgressDialog;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Message;
import android.os.Messenger;
import android.support.v4.app.LoaderManager;
import android.support.v4.content.CursorLoader;
import android.support.v4.content.Loader;
import android.support.v4.view.MenuItemCompat;
import android.support.v7.widget.SearchView;
import android.view.ActionMode;
import android.view.LayoutInflater;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.widget.AbsListView.MultiChoiceModeListener;
import android.widget.AdapterView;
import android.widget.ListView;
import android.widget.TextView;

import com.getbase.floatingactionbutton.FloatingActionButton;
import com.getbase.floatingactionbutton.FloatingActionsMenu;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.keyimport.ParcelableKeyRing;
import org.sufficientlysecure.keychain.operations.results.ConsolidateResult;
import org.sufficientlysecure.keychain.operations.results.DeleteResult;
import org.sufficientlysecure.keychain.operations.results.ImportKeyResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.provider.KeychainContract;
import org.sufficientlysecure.keychain.provider.KeychainContract.KeyRings;
import org.sufficientlysecure.keychain.provider.KeychainDatabase;
import org.sufficientlysecure.keychain.provider.ProviderHelper;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.service.PassphraseCacheService;
import org.sufficientlysecure.keychain.ui.dialog.DeleteKeyDialogFragment;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils;
import org.sufficientlysecure.keychain.ui.adapter.KeyAdapter;
import org.sufficientlysecure.keychain.ui.util.Notify;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;

import org.sufficientlysecure.keychain.util.ExportHelper;
import org.sufficientlysecure.keychain.util.FabContainer;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.ParcelableProxy;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;
import se.emilsjolander.stickylistheaders.StickyListHeadersAdapter;
import se.emilsjolander.stickylistheaders.StickyListHeadersListView;

/**
 * Public key list with sticky list headers. It does _not_ extend ListFragment because it uses
 * StickyListHeaders library which does not extend upon ListView.
 */
public class KeyListFragment extends LoaderFragment
        implements SearchView.OnQueryTextListener, AdapterView.OnItemClickListener,
        LoaderManager.LoaderCallbacks<Cursor>, FabContainer {

    static final int REQUEST_REPEAT_PASSPHRASE = 1;
    static final int REQUEST_ACTION = 2;

    ExportHelper mExportHelper;

    private KeyListAdapter mAdapter;
    private StickyListHeadersListView mStickyList;

    // saves the mode object for multiselect, needed for reset at some point
    private ActionMode mActionMode = null;

    private String mQuery;

    private FloatingActionsMenu mFab;

    // This ids for multiple key export.
    private ArrayList<Long> mIdsForRepeatAskPassphrase;
    // This index for remembering the number of master key.
    private int mIndex;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mExportHelper = new ExportHelper(getActivity());
    }

    /**
     * Load custom layout with StickyListView from library
     */
    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup superContainer, Bundle savedInstanceState) {
        View root = super.onCreateView(inflater, superContainer, savedInstanceState);
        View view = inflater.inflate(R.layout.key_list_fragment, getContainer());

        mStickyList = (StickyListHeadersListView) view.findViewById(R.id.key_list_list);
        mStickyList.setOnItemClickListener(this);

        mFab = (FloatingActionsMenu) view.findViewById(R.id.fab_main);

        FloatingActionButton fabQrCode = (FloatingActionButton) view.findViewById(R.id.fab_add_qr_code);
        FloatingActionButton fabCloud = (FloatingActionButton) view.findViewById(R.id.fab_add_cloud);
        FloatingActionButton fabFile = (FloatingActionButton) view.findViewById(R.id.fab_add_file);

        fabQrCode.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                mFab.collapse();
                scanQrCode();
            }
        });
        fabCloud.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                mFab.collapse();
                searchCloud();
            }
        });
        fabFile.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                mFab.collapse();
                importFile();
            }
        });


        return root;
    }

    /**
     * Define Adapter and Loader on create of Activity
     */
    @TargetApi(Build.VERSION_CODES.HONEYCOMB)
    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);

        // show app name instead of "keys" from nav drawer
        getActivity().setTitle(R.string.app_name);

        mStickyList.setOnItemClickListener(this);
        mStickyList.setAreHeadersSticky(true);
        mStickyList.setDrawingListUnderStickyHeader(false);
        mStickyList.setFastScrollEnabled(true);

        // Adds an empty footer view so that the Floating Action Button won't block content
        // in last few rows.
        View footer = new View(getActivity());

        int spacing = (int) android.util.TypedValue.applyDimension(
                android.util.TypedValue.COMPLEX_UNIT_DIP, 72, getResources().getDisplayMetrics()
        );

        android.widget.AbsListView.LayoutParams params = new android.widget.AbsListView.LayoutParams(
                android.widget.AbsListView.LayoutParams.MATCH_PARENT,
                spacing
        );

        footer.setLayoutParams(params);
        mStickyList.addFooterView(footer, null, false);

        /*
         * Multi-selection
         */
        mStickyList.setFastScrollAlwaysVisible(true);

        mStickyList.setChoiceMode(ListView.CHOICE_MODE_MULTIPLE_MODAL);
        mStickyList.getWrappedList().setMultiChoiceModeListener(new MultiChoiceModeListener() {

            @Override
            public boolean onCreateActionMode(ActionMode mode, Menu menu) {
                android.view.MenuInflater inflater = getActivity().getMenuInflater();
                inflater.inflate(R.menu.key_list_multi, menu);
                mActionMode = mode;
                return true;
            }

            @Override
            public boolean onPrepareActionMode(ActionMode mode, Menu menu) {
                return false;
            }

            @Override
            public boolean onActionItemClicked(ActionMode mode, MenuItem item) {

                // get IDs for checked positions as long array
                long[] ids;

                switch (item.getItemId()) {
                    case R.id.menu_key_list_multi_encrypt: {
                        ids = mAdapter.getCurrentSelectedMasterKeyIds();
                        encrypt(mode, ids);
                        break;
                    }
                    case R.id.menu_key_list_multi_delete: {
                        ids = mAdapter.getCurrentSelectedMasterKeyIds();
                        showDeleteKeyDialog(mode, ids, mAdapter.isAnySecretSelected());
                        break;
                    }
                    case R.id.menu_key_list_multi_export: {
                        ids = mAdapter.getCurrentSelectedMasterKeyIds();
                        showMultiExportDialog(ids);
                        break;
                    }
                    case R.id.menu_key_list_multi_select_all: {
                        // select all
                        for (int i = 0; i < mAdapter.getCount(); i++) {
                            mStickyList.setItemChecked(i, true);
                        }
                        break;
                    }
                }
                return true;
            }

            @Override
            public void onDestroyActionMode(ActionMode mode) {
                mActionMode = null;
                mAdapter.clearSelection();
            }

            @Override
            public void onItemCheckedStateChanged(ActionMode mode, int position, long id,
                                                  boolean checked) {
                if (checked) {
                    mAdapter.setNewSelection(position, true);
                } else {
                    mAdapter.removeSelection(position);
                }
                int count = mStickyList.getCheckedItemCount();
                String keysSelected = getResources().getQuantityString(
                        R.plurals.key_list_selected_keys, count, count);
                mode.setTitle(keysSelected);
            }

        });

        // We have a menu item to show in action bar.
        setHasOptionsMenu(true);

        // Start out with a progress indicator.
        setContentShown(false);

        // Create an empty adapter we will use to display the loaded data.
        mAdapter = new KeyListAdapter(getActivity(), null, 0);
        mStickyList.setAdapter(mAdapter);

        // Prepare the loader. Either re-connect with an existing one,
        // or start a new one.
        getLoaderManager().initLoader(0, null, this);
    }

    static final String ORDER =
            KeyRings.HAS_ANY_SECRET + " DESC, UPPER(" + KeyRings.USER_ID + ") ASC";


    @Override
    public Loader<Cursor> onCreateLoader(int id, Bundle args) {
        // This is called when a new Loader needs to be created. This
        // sample only has one Loader, so we don't care about the ID.
        Uri baseUri = KeyRings.buildUnifiedKeyRingsUri();
        String where = null;
        String whereArgs[] = null;
        if (mQuery != null) {
            String[] words = mQuery.trim().split("\\s+");
            whereArgs = new String[words.length];
            for (int i = 0; i < words.length; ++i) {
                if (where == null) {
                    where = "";
                } else {
                    where += " AND ";
                }
                where += KeyRings.USER_ID + " LIKE ?";
                whereArgs[i] = "%" + words[i] + "%";
            }
        }

        // Now create and return a CursorLoader that will take care of
        // creating a Cursor for the data being displayed.
        return new CursorLoader(getActivity(), baseUri,
                KeyListAdapter.PROJECTION, where, whereArgs, ORDER);
    }

    @Override
    public void onLoadFinished(Loader<Cursor> loader, Cursor data) {
        // Swap the new cursor in. (The framework will take care of closing the
        // old cursor once we return.)
        mAdapter.setSearchQuery(mQuery);
        mAdapter.swapCursor(data);

        mStickyList.setAdapter(mAdapter);

        // this view is made visible if no data is available
        mStickyList.setEmptyView(getActivity().findViewById(R.id.key_list_empty));

        // end action mode, if any
        if (mActionMode != null) {
            mActionMode.finish();
        }

        // The list should now be shown.
        if (isResumed()) {
            setContentShown(true);
        } else {
            setContentShownNoAnimation(true);
        }
    }

    @Override
    public void onLoaderReset(Loader<Cursor> loader) {
        // This is called when the last Cursor provided to onLoadFinished()
        // above is about to be closed. We need to make sure we are no
        // longer using it.
        mAdapter.swapCursor(null);
    }

    /**
     * On click on item, start key view activity
     */
    @Override
    public void onItemClick(AdapterView<?> adapterView, View view, int position, long id) {
        Intent viewIntent = new Intent(getActivity(), ViewKeyActivity.class);
        viewIntent.setData(
                KeyRings.buildGenericKeyRingUri(mAdapter.getMasterKeyId(position)));
        startActivity(viewIntent);
    }

    protected void encrypt(ActionMode mode, long[] masterKeyIds) {
        Intent intent = new Intent(getActivity(), EncryptFilesActivity.class);
        intent.setAction(EncryptFilesActivity.ACTION_ENCRYPT_DATA);
        intent.putExtra(EncryptFilesActivity.EXTRA_ENCRYPTION_KEY_IDS, masterKeyIds);
        // used instead of startActivity set actionbar based on callingPackage
        startActivityForResult(intent, REQUEST_ACTION);

        mode.finish();
    }

    /**
     * Show dialog to delete key
     *
     * @param hasSecret must contain whether the list of masterKeyIds contains a secret key or not
     */
    public void showDeleteKeyDialog(final ActionMode mode, long[] masterKeyIds, boolean hasSecret) {
        // Can only work on singular secret keys
        if (hasSecret && masterKeyIds.length > 1) {
            Notify.create(getActivity(), R.string.secret_cannot_multiple,
                    Notify.Style.ERROR).show();
            return;
        }

        // Message is received after key is deleted
        Handler returnHandler = new Handler() {
            @Override
            public void handleMessage(Message message) {
                if (message.arg1 == DeleteKeyDialogFragment.MESSAGE_OKAY) {
                    Bundle data = message.getData();
                    if (data != null) {
                        DeleteResult result = data.getParcelable(DeleteResult.EXTRA_RESULT);
                        if (result != null) {
                            result.createNotify(getActivity()).show();
                        }
                    }
                    mode.finish();
                }
            }
        };

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(returnHandler);

        DeleteKeyDialogFragment deleteKeyDialog = DeleteKeyDialogFragment.newInstance(messenger,
                masterKeyIds);

        deleteKeyDialog.show(getActivity().getSupportFragmentManager(), "deleteKeyDialog");
    }


    @Override
    public void onCreateOptionsMenu(final Menu menu, final MenuInflater inflater) {
        inflater.inflate(R.menu.key_list, menu);

        if (Constants.DEBUG) {
            menu.findItem(R.id.menu_key_list_debug_cons).setVisible(true);
            menu.findItem(R.id.menu_key_list_debug_read).setVisible(true);
            menu.findItem(R.id.menu_key_list_debug_write).setVisible(true);
            menu.findItem(R.id.menu_key_list_debug_first_time).setVisible(true);
        }

        // Get the searchview
        MenuItem searchItem = menu.findItem(R.id.menu_key_list_search);

        SearchView searchView = (SearchView) MenuItemCompat.getActionView(searchItem);

        // Execute this when searching
        searchView.setOnQueryTextListener(this);

        // Erase search result without focus
        MenuItemCompat.setOnActionExpandListener(searchItem, new MenuItemCompat.OnActionExpandListener() {
            @Override
            public boolean onMenuItemActionExpand(MenuItem item) {

                // disable swipe-to-refresh
                // mSwipeRefreshLayout.setIsLocked(true);
                return true;
            }

            @Override
            public boolean onMenuItemActionCollapse(MenuItem item) {
                mQuery = null;
                getLoaderManager().restartLoader(0, null, KeyListFragment.this);

                // enable swipe-to-refresh
                // mSwipeRefreshLayout.setIsLocked(false);
                return true;
            }
        });

        super.onCreateOptionsMenu(menu, inflater);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {

            case R.id.menu_key_list_create:
                createKey();
                return true;

            case R.id.menu_key_list_export:
                mExportHelper.showExportKeysDialog(null, Constants.Path.APP_DIR_FILE, true);
                return true;

            case R.id.menu_key_list_update_all_keys:
                final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(getActivity())
                        .getProxyPrefs();
                Runnable ignoreTor = new Runnable() {
                    @Override
                    public void run() {
                        updateAllKeys(new ParcelableProxy(null, -1, null));
                    }
                };

                if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                        getActivity())) {
                    updateAllKeys(proxyPrefs.parcelableProxy);
                }
                return true;

            case R.id.menu_key_list_debug_cons:
                consolidate();
                return true;

            case R.id.menu_key_list_debug_read:
                try {
                    KeychainDatabase.debugBackup(getActivity(), true);
                    Notify.create(getActivity(), "Restored debug_backup.db", Notify.Style.OK).show();
                    getActivity().getContentResolver().notifyChange(KeychainContract.KeyRings.CONTENT_URI, null);
                } catch (IOException e) {
                    Log.e(Constants.TAG, "IO Error", e);
                    Notify.create(getActivity(), "IO Error " + e.getMessage(), Notify.Style.ERROR).show();
                }
                return true;

            case R.id.menu_key_list_debug_write:
                try {
                    KeychainDatabase.debugBackup(getActivity(), false);
                    Notify.create(getActivity(), "Backup to debug_backup.db completed", Notify.Style.OK).show();
                } catch (IOException e) {
                    Log.e(Constants.TAG, "IO Error", e);
                    Notify.create(getActivity(), "IO Error: " + e.getMessage(), Notify.Style.ERROR).show();
                }
                return true;

            case R.id.menu_key_list_debug_first_time:
                Preferences prefs = Preferences.getPreferences(getActivity());
                prefs.setFirstTime(true);
                Intent intent = new Intent(getActivity(), CreateKeyActivity.class);
                intent.putExtra(CreateKeyActivity.EXTRA_FIRST_TIME, true);
                startActivity(intent);
                getActivity().finish();
                return true;

            default:
                return super.onOptionsItemSelected(item);
        }
    }

    @Override
    public boolean onQueryTextSubmit(String s) {
        return true;
    }

    @Override
    public boolean onQueryTextChange(String s) {
        Log.d(Constants.TAG, "onQueryTextChange s:" + s);
        // Called when the action bar search text has changed.  Update
        // the search filter, and restart the loader to do a new query
        // with this filter.
        // If the nav drawer is opened, onQueryTextChange("") is executed.
        // This hack prevents restarting the loader.
        // TODO: better way to fix this?
        String tmp = (mQuery == null) ? "" : mQuery;
        if (!s.equals(tmp)) {
            mQuery = s;
            getLoaderManager().restartLoader(0, null, this);
        }
        return true;
    }

    private void searchCloud() {
        Intent importIntent = new Intent(getActivity(), ImportKeysActivity.class);
        importIntent.putExtra(ImportKeysActivity.EXTRA_QUERY, (String) null); // hack to show only cloud tab
        startActivity(importIntent);
    }

    private void scanQrCode() {
        Intent scanQrCode = new Intent(getActivity(), ImportKeysProxyActivity.class);
        scanQrCode.setAction(ImportKeysProxyActivity.ACTION_SCAN_IMPORT);
        startActivityForResult(scanQrCode, REQUEST_ACTION);
    }

    private void importFile() {
        Intent intentImportExisting = new Intent(getActivity(), ImportKeysActivity.class);
        intentImportExisting.setAction(ImportKeysActivity.ACTION_IMPORT_KEY_FROM_FILE_AND_RETURN);
        startActivityForResult(intentImportExisting, REQUEST_ACTION);
    }

    private void createKey() {
        Intent intent = new Intent(getActivity(), CreateKeyActivity.class);
        startActivityForResult(intent, REQUEST_ACTION);
    }

    private void updateAllKeys(ParcelableProxy parcelableProxy) {
        Context context = getActivity();

        ProviderHelper providerHelper = new ProviderHelper(context);

        Cursor cursor = providerHelper.getContentResolver().query(
                KeyRings.buildUnifiedKeyRingsUri(), new String[]{
                        KeyRings.FINGERPRINT
                }, null, null, null
        );

        ArrayList<ParcelableKeyRing> keyList = new ArrayList<>();

        while (cursor.moveToNext()) {
            byte[] blob = cursor.getBlob(0);//fingerprint column is 0
            String fingerprint = KeyFormattingUtils.convertFingerprintToHex(blob);
            ParcelableKeyRing keyEntry = new ParcelableKeyRing(fingerprint, null, null);
            keyList.add(keyEntry);
        }

        ServiceProgressHandler serviceHandler = new ServiceProgressHandler(getActivity()) {
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
                    final ImportKeyResult result =
                            returnData.getParcelable(OperationResult.EXTRA_RESULT);
                    if (result == null) {
                        Log.e(Constants.TAG, "result == null");
                        return;
                    }

                    result.createNotify(getActivity()).show();
                }
            }
        };

        // Send all information needed to service to query keys in other thread
        Intent intent = new Intent(getActivity(), KeychainService.class);
        intent.setAction(KeychainService.ACTION_IMPORT_KEYRING);

        // fill values for this action
        Bundle data = new Bundle();

        // search config
        {
            Preferences prefs = Preferences.getPreferences(getActivity());
            Preferences.CloudSearchPrefs cloudPrefs =
                    new Preferences.CloudSearchPrefs(true, true, prefs.getPreferredKeyserver());
            data.putString(KeychainService.IMPORT_KEY_SERVER, cloudPrefs.keyserver);
        }

        data.putParcelableArrayList(KeychainService.IMPORT_KEY_LIST, keyList);

        data.putParcelable(KeychainService.EXTRA_PARCELABLE_PROXY, parcelableProxy);

        intent.putExtra(KeychainService.EXTRA_DATA, data);

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(serviceHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        // show progress dialog
        serviceHandler.showProgressDialog(
                getString(R.string.progress_updating),
                ProgressDialog.STYLE_HORIZONTAL, true);

        // start service with intent
        getActivity().startService(intent);
    }

    private void consolidate() {
        // Message is received after importing is done in KeychainService
        ServiceProgressHandler saveHandler = new ServiceProgressHandler(getActivity()) {
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
                    final ConsolidateResult result =
                            returnData.getParcelable(OperationResult.EXTRA_RESULT);
                    if (result == null) {
                        return;
                    }

                    result.createNotify(getActivity()).show();
                }
            }
        };

        // Send all information needed to service to import key in other thread
        Intent intent = new Intent(getActivity(), KeychainService.class);

        intent.setAction(KeychainService.ACTION_CONSOLIDATE);

        // fill values for this action
        Bundle data = new Bundle();

        intent.putExtra(KeychainService.EXTRA_DATA, data);

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(saveHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        // show progress dialog
        saveHandler.showProgressDialog(
                getString(R.string.progress_importing),
                ProgressDialog.STYLE_HORIZONTAL, false);

        // start service with intent
        getActivity().startService(intent);
    }

    private void showMultiExportDialog(long[] masterKeyIds) {
        mIdsForRepeatAskPassphrase = new ArrayList<>();
        for (long id : masterKeyIds) {
            try {
                if (PassphraseCacheService.getCachedPassphrase(
                        getActivity(), id, id) == null) {
                    mIdsForRepeatAskPassphrase.add(id);
                }
            } catch (PassphraseCacheService.KeyNotFoundException e) {
                // This happens when the master key is stripped
                // and ignore this key.
            }
        }
        mIndex = 0;
        if (mIdsForRepeatAskPassphrase.size() != 0) {
            startPassphraseActivity();
            return;
        }
        long[] idsForMultiExport = new long[mIdsForRepeatAskPassphrase.size()];
        for (int i = 0; i < mIdsForRepeatAskPassphrase.size(); ++i) {
            idsForMultiExport[i] = mIdsForRepeatAskPassphrase.get(i);
        }
        mExportHelper.showExportKeysDialog(idsForMultiExport,
                Constants.Path.APP_DIR_FILE,
                mAdapter.isAnySecretSelected());
    }

    private void startPassphraseActivity() {
        Intent intent = new Intent(getActivity(), PassphraseDialogActivity.class);
        long masterKeyId = mIdsForRepeatAskPassphrase.get(mIndex++);
        intent.putExtra(PassphraseDialogActivity.EXTRA_SUBKEY_ID, masterKeyId);
        startActivityForResult(intent, REQUEST_REPEAT_PASSPHRASE);
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQUEST_REPEAT_PASSPHRASE) {
            if (resultCode != Activity.RESULT_OK) {
                return;
            }
            if (mIndex < mIdsForRepeatAskPassphrase.size()) {
                startPassphraseActivity();
                return;
            }
            long[] idsForMultiExport = new long[mIdsForRepeatAskPassphrase.size()];
            for (int i = 0; i < mIdsForRepeatAskPassphrase.size(); ++i) {
                idsForMultiExport[i] = mIdsForRepeatAskPassphrase.get(i);
            }
            mExportHelper.showExportKeysDialog(idsForMultiExport,
                    Constants.Path.APP_DIR_FILE,
                    mAdapter.isAnySecretSelected());
        }

        if (requestCode == REQUEST_ACTION) {
            // if a result has been returned, display a notify
            if (data != null && data.hasExtra(OperationResult.EXTRA_RESULT)) {
                OperationResult result = data.getParcelableExtra(OperationResult.EXTRA_RESULT);
                result.createNotify(getActivity()).show();
            } else {
                super.onActivityResult(requestCode, resultCode, data);
            }
        }
    }

    @Override
    public void fabMoveUp(int height) {
        ObjectAnimator anim = ObjectAnimator.ofFloat(mFab, "translationY", 0, -height);
        // we're a little behind, so skip 1/10 of the time
        anim.setDuration(270);
        anim.start();
    }

    @Override
    public void fabRestorePosition() {
        ObjectAnimator anim = ObjectAnimator.ofFloat(mFab, "translationY", 0);
        // we're a little ahead, so wait a few ms
        anim.setStartDelay(70);
        anim.setDuration(300);
        anim.start();
    }

    public class KeyListAdapter extends KeyAdapter implements StickyListHeadersAdapter {

        private HashMap<Integer, Boolean> mSelection = new HashMap<>();

        public KeyListAdapter(Context context, Cursor c, int flags) {
            super(context, c, flags);
        }

        @Override
        public View newView(Context context, Cursor cursor, ViewGroup parent) {
            View view = super.newView(context, cursor, parent);

            final KeyItemViewHolder holder = (KeyItemViewHolder) view.getTag();

            holder.mSlinger.setVisibility(View.VISIBLE);
            holder.mSlingerButton.setOnClickListener(new OnClickListener() {
                @Override
                public void onClick(View v) {
                    if (holder.mMasterKeyId != null) {
                        Intent safeSlingerIntent = new Intent(mContext, SafeSlingerActivity.class);
                        safeSlingerIntent.putExtra(SafeSlingerActivity.EXTRA_MASTER_KEY_ID, holder.mMasterKeyId);
                        startActivityForResult(safeSlingerIntent, REQUEST_ACTION);
                    }
                }
            });

            return view;
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            // let the adapter handle setting up the row views
            View v = super.getView(position, convertView, parent);

            if (mSelection.get(position) != null) {
                // selected position color
                v.setBackgroundColor(parent.getResources().getColor(R.color.emphasis));
            } else {
                // default color
                v.setBackgroundColor(Color.TRANSPARENT);
            }

            return v;
        }

        private class HeaderViewHolder {
            TextView mText;
            TextView mCount;
        }

        /**
         * Creates a new header view and binds the section headers to it. It uses the ViewHolder
         * pattern. Most functionality is similar to getView() from Android's CursorAdapter.
         * <p/>
         * NOTE: The variables mDataValid and mCursor are available due to the super class
         * CursorAdapter.
         */
        @Override
        public View getHeaderView(int position, View convertView, ViewGroup parent) {
            HeaderViewHolder holder;
            if (convertView == null) {
                holder = new HeaderViewHolder();
                convertView = mInflater.inflate(R.layout.key_list_header, parent, false);
                holder.mText = (TextView) convertView.findViewById(R.id.stickylist_header_text);
                holder.mCount = (TextView) convertView.findViewById(R.id.contacts_num);
                convertView.setTag(holder);
            } else {
                holder = (HeaderViewHolder) convertView.getTag();
            }

            if (!mDataValid) {
                // no data available at this point
                Log.d(Constants.TAG, "getHeaderView: No data available at this point!");
                return convertView;
            }

            if (!mCursor.moveToPosition(position)) {
                throw new IllegalStateException("couldn't move cursor to position " + position);
            }

            if (mCursor.getInt(INDEX_HAS_ANY_SECRET) != 0) {
                { // set contact count
                    int num = mCursor.getCount();
                    String contactsTotal = mContext.getResources().getQuantityString(R.plurals.n_keys, num, num);
                    holder.mCount.setText(contactsTotal);
                    holder.mCount.setVisibility(View.VISIBLE);
                }

                holder.mText.setText(convertView.getResources().getString(R.string.my_keys));
                return convertView;
            }

            // set header text as first char in user id
            String userId = mCursor.getString(INDEX_USER_ID);
            String headerText = convertView.getResources().getString(R.string.user_id_no_name);
            if (userId != null && userId.length() > 0) {
                headerText = "" + userId.charAt(0);
            }
            holder.mText.setText(headerText);
            holder.mCount.setVisibility(View.GONE);
            return convertView;
        }

        /**
         * Header IDs should be static, position=1 should always return the same Id that is.
         */
        @Override
        public long getHeaderId(int position) {
            if (!mDataValid) {
                // no data available at this point
                Log.d(Constants.TAG, "getHeaderView: No data available at this point!");
                return -1;
            }

            if (!mCursor.moveToPosition(position)) {
                throw new IllegalStateException("couldn't move cursor to position " + position);
            }

            // early breakout: all secret keys are assigned id 0
            if (mCursor.getInt(INDEX_HAS_ANY_SECRET) != 0) {
                return 1L;
            }
            // otherwise, return the first character of the name as ID
            String userId = mCursor.getString(INDEX_USER_ID);
            if (userId != null && userId.length() > 0) {
                return Character.toUpperCase(userId.charAt(0));
            } else {
                return Long.MAX_VALUE;
            }
        }

        /**
         * -------------------------- MULTI-SELECTION METHODS --------------
         */
        public void setNewSelection(int position, boolean value) {
            mSelection.put(position, value);
            notifyDataSetChanged();
        }

        public boolean isAnySecretSelected() {
            for (int pos : mSelection.keySet()) {
                if (isSecretAvailable(pos))
                    return true;
            }
            return false;
        }

        public long[] getCurrentSelectedMasterKeyIds() {
            long[] ids = new long[mSelection.size()];
            int i = 0;
            // get master key ids
            for (int pos : mSelection.keySet()) {
                ids[i++] = getMasterKeyId(pos);
            }
            return ids;
        }

        public void removeSelection(int position) {
            mSelection.remove(position);
            notifyDataSetChanged();
        }

        public void clearSelection() {
            mSelection.clear();
            notifyDataSetChanged();
        }

    }

}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/SettingsActivity.java
/*
 * Copyright (C) 2010-2014 Thialfihar <thi@thialfihar.org>
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

import android.annotation.TargetApi;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.preference.CheckBoxPreference;
import android.preference.EditTextPreference;
import android.preference.ListPreference;
import android.preference.Preference;
import android.preference.PreferenceActivity;
import android.preference.PreferenceFragment;
import android.preference.PreferenceScreen;
import android.support.v7.widget.Toolbar;
import android.text.TextUtils;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;

import org.spongycastle.bcpg.CompressionAlgorithmTags;
import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.ui.util.Notify;
import org.sufficientlysecure.keychain.ui.widget.IntegerListPreference;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

import java.util.List;

public class SettingsActivity extends PreferenceActivity {

    public static final String ACTION_PREFS_CLOUD = "org.sufficientlysecure.keychain.ui.PREFS_CLOUD";
    public static final String ACTION_PREFS_ADV = "org.sufficientlysecure.keychain.ui.PREFS_ADV";
    public static final String ACTION_PREFS_PROXY = "org.sufficientlysecure.keychain.ui.PREFS_PROXY";

    public static final int REQUEST_CODE_KEYSERVER_PREF = 0x00007005;

    private PreferenceScreen mKeyServerPreference = null;
    private static Preferences sPreferences;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        sPreferences = Preferences.getPreferences(this);
        super.onCreate(savedInstanceState);

        setupToolbar();

        String action = getIntent().getAction();
        if (action == null) return;

        switch (action) {
            case ACTION_PREFS_CLOUD: {
                addPreferencesFromResource(R.xml.cloud_search_prefs);

                mKeyServerPreference = (PreferenceScreen) findPreference(Constants.Pref.KEY_SERVERS);
                mKeyServerPreference.setSummary(keyserverSummary(this));
                mKeyServerPreference
                        .setOnPreferenceClickListener(new Preference.OnPreferenceClickListener() {
                            public boolean onPreferenceClick(Preference preference) {
                                Intent intent = new Intent(SettingsActivity.this,
                                        SettingsKeyServerActivity.class);
                                intent.putExtra(SettingsKeyServerActivity.EXTRA_KEY_SERVERS,
                                        sPreferences.getKeyServers());
                                startActivityForResult(intent, REQUEST_CODE_KEYSERVER_PREF);
                                return false;
                            }
                        });
                initializeSearchKeyserver(
                        (CheckBoxPreference) findPreference(Constants.Pref.SEARCH_KEYSERVER)
                );
                initializeSearchKeybase(
                        (CheckBoxPreference) findPreference(Constants.Pref.SEARCH_KEYBASE)
                );

                break;
            }

            case ACTION_PREFS_ADV: {
                addPreferencesFromResource(R.xml.adv_preferences);

                initializePassphraseCacheSubs(
                        (CheckBoxPreference) findPreference(Constants.Pref.PASSPHRASE_CACHE_SUBS));

                initializePassphraseCacheTtl(
                        (IntegerListPreference) findPreference(Constants.Pref.PASSPHRASE_CACHE_TTL));

                int[] valueIds = new int[]{
                        CompressionAlgorithmTags.UNCOMPRESSED,
                        CompressionAlgorithmTags.ZIP,
                        CompressionAlgorithmTags.ZLIB,
                        CompressionAlgorithmTags.BZIP2,
                };
                String[] entries = new String[]{
                        getString(R.string.choice_none) + " (" + getString(R.string.compression_fast) + ")",
                        "ZIP (" + getString(R.string.compression_fast) + ")",
                        "ZLIB (" + getString(R.string.compression_fast) + ")",
                        "BZIP2 (" + getString(R.string.compression_very_slow) + ")",};
                String[] values = new String[valueIds.length];
                for (int i = 0; i < values.length; ++i) {
                    values[i] = "" + valueIds[i];
                }

                initializeUseDefaultYubiKeyPin(
                        (CheckBoxPreference) findPreference(Constants.Pref.USE_DEFAULT_YUBIKEY_PIN));

                initializeUseNumKeypadForYubiKeyPin(
                        (CheckBoxPreference) findPreference(Constants.Pref.USE_NUMKEYPAD_FOR_YUBIKEY_PIN));

                break;
            }

            case ACTION_PREFS_PROXY: {
                new ProxyPrefsFragment.Initializer(this).initialize();

                break;
            }
        }
    }

    /**
     * Hack to get Toolbar in PreferenceActivity. See http://stackoverflow.com/a/26614696
     */
    private void setupToolbar() {
        ViewGroup root = (ViewGroup) findViewById(android.R.id.content);
        LinearLayout content = (LinearLayout) root.getChildAt(0);
        LinearLayout toolbarContainer = (LinearLayout) View.inflate(this, R.layout.preference_toolbar_activity, null);

        root.removeAllViews();
        toolbarContainer.addView(content);
        root.addView(toolbarContainer);

        Toolbar toolbar = (Toolbar) toolbarContainer.findViewById(R.id.toolbar);
        toolbar.setTitle(R.string.title_preferences);
        toolbar.setNavigationIcon(getResources().getDrawable(R.drawable.ic_arrow_back_white_24dp));
        toolbar.setNavigationOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                //What to do on back clicked
                finish();
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        switch (requestCode) {
            case REQUEST_CODE_KEYSERVER_PREF: {
                if (resultCode == RESULT_CANCELED || data == null) {
                    return;
                }
                String servers[] = data
                        .getStringArrayExtra(SettingsKeyServerActivity.EXTRA_KEY_SERVERS);
                sPreferences.setKeyServers(servers);
                mKeyServerPreference.setSummary(keyserverSummary(this));
                break;
            }

            default: {
                super.onActivityResult(requestCode, resultCode, data);
                break;
            }
        }
    }

    @Override
    public void onBuildHeaders(List<Header> target) {
        super.onBuildHeaders(target);
        loadHeadersFromResource(R.xml.preference_headers, target);
    }

    /**
     * This fragment shows the Cloud Search preferences in android 3.0+
     */
    public static class CloudSearchPrefsFragment extends PreferenceFragment {

        private PreferenceScreen mKeyServerPreference = null;

        @Override
        public void onCreate(Bundle savedInstanceState) {
            super.onCreate(savedInstanceState);

            // Load the preferences from an XML resource
            addPreferencesFromResource(R.xml.cloud_search_prefs);

            mKeyServerPreference = (PreferenceScreen) findPreference(Constants.Pref.KEY_SERVERS);
            mKeyServerPreference.setSummary(keyserverSummary(getActivity()));

            mKeyServerPreference
                    .setOnPreferenceClickListener(new Preference.OnPreferenceClickListener() {
                        public boolean onPreferenceClick(Preference preference) {
                            Intent intent = new Intent(getActivity(),
                                    SettingsKeyServerActivity.class);
                            intent.putExtra(SettingsKeyServerActivity.EXTRA_KEY_SERVERS,
                                    sPreferences.getKeyServers());
                            startActivityForResult(intent, REQUEST_CODE_KEYSERVER_PREF);
                            return false;
                        }
                    });
            initializeSearchKeyserver(
                    (CheckBoxPreference) findPreference(Constants.Pref.SEARCH_KEYSERVER)
            );
            initializeSearchKeybase(
                    (CheckBoxPreference) findPreference(Constants.Pref.SEARCH_KEYBASE)
            );
        }

        @Override
        public void onActivityResult(int requestCode, int resultCode, Intent data) {
            switch (requestCode) {
                case REQUEST_CODE_KEYSERVER_PREF: {
                    if (resultCode == RESULT_CANCELED || data == null) {
                        return;
                    }
                    String servers[] = data
                            .getStringArrayExtra(SettingsKeyServerActivity.EXTRA_KEY_SERVERS);
                    sPreferences.setKeyServers(servers);
                    mKeyServerPreference.setSummary(keyserverSummary(getActivity()));
                    break;
                }

                default: {
                    super.onActivityResult(requestCode, resultCode, data);
                    break;
                }
            }
        }
    }

    /**
     * This fragment shows the advanced preferences in android 3.0+
     */
    public static class AdvancedPrefsFragment extends PreferenceFragment {

        @Override
        public void onCreate(Bundle savedInstanceState) {
            super.onCreate(savedInstanceState);

            // Load the preferences from an XML resource
            addPreferencesFromResource(R.xml.adv_preferences);

            initializePassphraseCacheSubs(
                    (CheckBoxPreference) findPreference(Constants.Pref.PASSPHRASE_CACHE_SUBS));

            initializePassphraseCacheTtl(
                    (IntegerListPreference) findPreference(Constants.Pref.PASSPHRASE_CACHE_TTL));

            int[] valueIds = new int[]{
                    CompressionAlgorithmTags.UNCOMPRESSED,
                    CompressionAlgorithmTags.ZIP,
                    CompressionAlgorithmTags.ZLIB,
                    CompressionAlgorithmTags.BZIP2,
            };

            String[] entries = new String[]{
                    getString(R.string.choice_none) + " (" + getString(R.string.compression_fast) + ")",
                    "ZIP (" + getString(R.string.compression_fast) + ")",
                    "ZLIB (" + getString(R.string.compression_fast) + ")",
                    "BZIP2 (" + getString(R.string.compression_very_slow) + ")",
            };

            String[] values = new String[valueIds.length];
            for (int i = 0; i < values.length; ++i) {
                values[i] = "" + valueIds[i];
            }

            initializeUseDefaultYubiKeyPin(
                    (CheckBoxPreference) findPreference(Constants.Pref.USE_DEFAULT_YUBIKEY_PIN));

            initializeUseNumKeypadForYubiKeyPin(
                    (CheckBoxPreference) findPreference(Constants.Pref.USE_NUMKEYPAD_FOR_YUBIKEY_PIN));
        }
    }

    public static class ProxyPrefsFragment extends PreferenceFragment {

        @Override
        public void onCreate(Bundle savedInstanceState) {
            super.onCreate(savedInstanceState);

            new Initializer(this).initialize();

        }

        public static class Initializer {
            private CheckBoxPreference mUseTor;
            private CheckBoxPreference mUseNormalProxy;
            private EditTextPreference mProxyHost;
            private EditTextPreference mProxyPort;
            private ListPreference mProxyType;
            private PreferenceActivity mActivity;
            private PreferenceFragment mFragment;

            public Initializer(PreferenceFragment fragment) {
                mFragment = fragment;
            }

            public Initializer(PreferenceActivity activity) {
                mActivity = activity;
            }

            public Preference automaticallyFindPreference(String key) {
                if (mFragment != null) {
                    return mFragment.findPreference(key);
                } else {
                    return mActivity.findPreference(key);
                }
            }

            public void initialize() {
                // makes android's preference framework write to our file instead of default
                // This allows us to use the "persistent" attribute to simplify code
                if (mFragment != null) {
                    Preferences.setPreferenceManagerFileAndMode(mFragment.getPreferenceManager());
                    // Load the preferences from an XML resource
                    mFragment.addPreferencesFromResource(R.xml.proxy_prefs);
                } else {
                    Preferences.setPreferenceManagerFileAndMode(mActivity.getPreferenceManager());
                    // Load the preferences from an XML resource
                    mActivity.addPreferencesFromResource(R.xml.proxy_prefs);
                }

                mUseTor = (CheckBoxPreference) automaticallyFindPreference(Constants.Pref.USE_TOR_PROXY);
                mUseNormalProxy = (CheckBoxPreference) automaticallyFindPreference(Constants.Pref.USE_NORMAL_PROXY);
                mProxyHost = (EditTextPreference) automaticallyFindPreference(Constants.Pref.PROXY_HOST);
                mProxyPort = (EditTextPreference) automaticallyFindPreference(Constants.Pref.PROXY_PORT);
                mProxyType = (ListPreference) automaticallyFindPreference(Constants.Pref.PROXY_TYPE);
                initializeUseTorPref();
                initializeUseNormalProxyPref();
                initializeEditTextPreferences();
                initializeProxyTypePreference();

                if (mUseTor.isChecked()) disableNormalProxyPrefs();
                else if (mUseNormalProxy.isChecked()) disableUseTorPrefs();
            }

            private void initializeUseTorPref() {
                mUseTor.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
                    @Override
                    public boolean onPreferenceChange(Preference preference, Object newValue) {
                        Activity activity = mFragment != null ? mFragment.getActivity() : mActivity;
                        if ((Boolean) newValue) {
                            boolean installed = OrbotHelper.isOrbotInstalled(activity);
                            if (!installed) {
                                Log.d(Constants.TAG, "Prompting to install Tor");
                                OrbotHelper.getPreferenceInstallDialogFragment().show(activity.getFragmentManager(),
                                        "installDialog");
                                // don't let the user check the box until he's installed orbot
                                return false;
                            } else {
                                disableNormalProxyPrefs();
                                // let the enable tor box be checked
                                return true;
                            }
                        } else {
                            // we're unchecking Tor, so enable other proxy
                            enableNormalProxyPrefs();
                            return true;
                        }
                    }
                });
            }

            private void initializeUseNormalProxyPref() {
                mUseNormalProxy.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
                    @Override
                    public boolean onPreferenceChange(Preference preference, Object newValue) {
                        if ((Boolean) newValue) {
                            disableUseTorPrefs();
                        } else {
                            enableUseTorPrefs();
                        }
                        return true;
                    }
                });
            }

            private void initializeEditTextPreferences() {
                mProxyHost.setSummary(mProxyHost.getText());
                mProxyPort.setSummary(mProxyPort.getText());

                mProxyHost.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
                    @Override
                    public boolean onPreferenceChange(Preference preference, Object newValue) {
                        Activity activity = mFragment != null ? mFragment.getActivity() : mActivity;
                        if (TextUtils.isEmpty((String) newValue)) {
                            Notify.create(
                                    activity,
                                    R.string.pref_proxy_host_err_invalid,
                                    Notify.Style.ERROR
                            ).show();
                            return false;
                        } else {
                            mProxyHost.setSummary((CharSequence) newValue);
                            return true;
                        }
                    }
                });

                mProxyPort.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
                    @Override
                    public boolean onPreferenceChange(Preference preference, Object newValue) {
                        Activity activity = mFragment != null ? mFragment.getActivity() : mActivity;
                        try {
                            int port = Integer.parseInt((String) newValue);
                            if (port < 0 || port > 65535) {
                                Notify.create(
                                        activity,
                                        R.string.pref_proxy_port_err_invalid,
                                        Notify.Style.ERROR
                                ).show();
                                return false;
                            }
                            // no issues, save port
                            mProxyPort.setSummary("" + port);
                            return true;
                        } catch (NumberFormatException e) {
                            Notify.create(
                                    activity,
                                    R.string.pref_proxy_port_err_invalid,
                                    Notify.Style.ERROR
                            ).show();
                            return false;
                        }
                    }
                });
            }

            private void initializeProxyTypePreference() {
                mProxyType.setSummary(mProxyType.getEntry());

                mProxyType.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
                    @Override
                    public boolean onPreferenceChange(Preference preference, Object newValue) {
                        CharSequence entry = mProxyType.getEntries()[mProxyType.findIndexOfValue((String) newValue)];
                        mProxyType.setSummary(entry);
                        return true;
                    }
                });
            }

            private void disableNormalProxyPrefs() {
                mUseNormalProxy.setChecked(false);
                mUseNormalProxy.setEnabled(false);
                mProxyHost.setEnabled(false);
                mProxyPort.setEnabled(false);
                mProxyType.setEnabled(false);
            }

            private void enableNormalProxyPrefs() {
                mUseNormalProxy.setEnabled(true);
                mProxyHost.setEnabled(true);
                mProxyPort.setEnabled(true);
                mProxyType.setEnabled(true);
            }

            private void disableUseTorPrefs() {
                mUseTor.setChecked(false);
                mUseTor.setEnabled(false);
            }

            private void enableUseTorPrefs() {
                mUseTor.setEnabled(true);
            }
        }

    }

    @TargetApi(Build.VERSION_CODES.KITKAT)
    protected boolean isValidFragment(String fragmentName) {
        return AdvancedPrefsFragment.class.getName().equals(fragmentName)
                || CloudSearchPrefsFragment.class.getName().equals(fragmentName)
                || ProxyPrefsFragment.class.getName().equals(fragmentName)
                || super.isValidFragment(fragmentName);
    }

    private static void initializePassphraseCacheSubs(final CheckBoxPreference mPassphraseCacheSubs) {
        mPassphraseCacheSubs.setChecked(sPreferences.getPassphraseCacheSubs());
        mPassphraseCacheSubs.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
            public boolean onPreferenceChange(Preference preference, Object newValue) {
                mPassphraseCacheSubs.setChecked((Boolean) newValue);
                sPreferences.setPassphraseCacheSubs((Boolean) newValue);
                return false;
            }
        });
    }

    private static void initializePassphraseCacheTtl(final IntegerListPreference mPassphraseCacheTtl) {
        mPassphraseCacheTtl.setValue("" + sPreferences.getPassphraseCacheTtl());
        mPassphraseCacheTtl.setSummary(mPassphraseCacheTtl.getEntry());
        mPassphraseCacheTtl
                .setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
                    public boolean onPreferenceChange(Preference preference, Object newValue) {
                        mPassphraseCacheTtl.setValue(newValue.toString());
                        mPassphraseCacheTtl.setSummary(mPassphraseCacheTtl.getEntry());
                        sPreferences.setPassphraseCacheTtl(Integer.parseInt(newValue.toString()));
                        return false;
                    }
                });
    }

    private static void initializeSearchKeyserver(final CheckBoxPreference mSearchKeyserver) {
        Preferences.CloudSearchPrefs prefs = sPreferences.getCloudSearchPrefs();
        mSearchKeyserver.setChecked(prefs.searchKeyserver);
        mSearchKeyserver.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
            @Override
            public boolean onPreferenceChange(Preference preference, Object newValue) {
                mSearchKeyserver.setChecked((Boolean) newValue);
                sPreferences.setSearchKeyserver((Boolean) newValue);
                return false;
            }
        });
    }

    private static void initializeSearchKeybase(final CheckBoxPreference mSearchKeybase) {
        Preferences.CloudSearchPrefs prefs = sPreferences.getCloudSearchPrefs();
        mSearchKeybase.setChecked(prefs.searchKeybase);
        mSearchKeybase.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
            @Override
            public boolean onPreferenceChange(Preference preference, Object newValue) {
                mSearchKeybase.setChecked((Boolean) newValue);
                sPreferences.setSearchKeybase((Boolean) newValue);
                return false;
            }
        });
    }

    public static String keyserverSummary(Context context) {
        String[] servers = sPreferences.getKeyServers();
        String serverSummary = context.getResources().getQuantityString(
                R.plurals.n_keyservers, servers.length, servers.length);
        return serverSummary + "; " + context.getString(R.string.label_preferred) + ": " + sPreferences
                .getPreferredKeyserver();
    }

    private static void initializeUseDefaultYubiKeyPin(final CheckBoxPreference mUseDefaultYubiKeyPin) {
        mUseDefaultYubiKeyPin.setChecked(sPreferences.useDefaultYubiKeyPin());
        mUseDefaultYubiKeyPin.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
            public boolean onPreferenceChange(Preference preference, Object newValue) {
                mUseDefaultYubiKeyPin.setChecked((Boolean) newValue);
                sPreferences.setUseDefaultYubiKeyPin((Boolean) newValue);
                return false;
            }
        });
    }

    private static void initializeUseNumKeypadForYubiKeyPin(final CheckBoxPreference mUseNumKeypadForYubiKeyPin) {
        mUseNumKeypadForYubiKeyPin.setChecked(sPreferences.useNumKeypadForYubiKeyPin());
        mUseNumKeypadForYubiKeyPin.setOnPreferenceChangeListener(new Preference.OnPreferenceChangeListener() {
            public boolean onPreferenceChange(Preference preference, Object newValue) {
                mUseNumKeypadForYubiKeyPin.setChecked((Boolean) newValue);
                sPreferences.setUseNumKeypadForYubiKeyPin((Boolean) newValue);
                return false;
            }
        });
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/UploadKeyActivity.java
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
import android.support.v4.app.NavUtils;
import android.view.MenuItem;
import android.view.View;
import android.view.View.OnClickListener;
import android.widget.ArrayAdapter;
import android.widget.Spinner;
import android.widget.Toast;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.provider.KeychainContract;
import org.sufficientlysecure.keychain.provider.KeychainContract.KeyRings;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.ui.base.BaseActivity;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.ParcelableProxy;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

/**
 * Sends the selected public key to a keyserver
 */
public class UploadKeyActivity extends BaseActivity {
    private View mUploadButton;
    private Spinner mKeyServerSpinner;

    private Uri mDataUri;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mUploadButton = findViewById(R.id.upload_key_action_upload);
        mKeyServerSpinner = (Spinner) findViewById(R.id.upload_key_keyserver);

        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, Preferences.getPreferences(this)
                .getKeyServers()
        );
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        mKeyServerSpinner.setAdapter(adapter);
        if (adapter.getCount() > 0) {
            mKeyServerSpinner.setSelection(0);
        } else {
            mUploadButton.setEnabled(false);
        }

        mUploadButton.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(UploadKeyActivity.this)
                        .getProxyPrefs();
                Runnable ignoreTor = new Runnable() {
                    @Override
                    public void run() {
                        uploadKey(proxyPrefs.parcelableProxy);
                    }
                };

                if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                        UploadKeyActivity.this)) {
                    uploadKey(proxyPrefs.parcelableProxy);
                }
            }
        });

        mDataUri = getIntent().getData();
        if (mDataUri == null) {
            Log.e(Constants.TAG, "Intent data missing. Should be Uri of key!");
            finish();
            return;
        }
    }

    @Override
    protected void initLayout() {
        setContentView(R.layout.upload_key_activity);
    }

    private void uploadKey(ParcelableProxy parcelableProxy) {
        // Send all information needed to service to upload key in other thread
        Intent intent = new Intent(this, KeychainService.class);

        intent.setAction(KeychainService.ACTION_UPLOAD_KEYRING);

        // set data uri as path to keyring
        Uri blobUri = KeyRings.buildUnifiedKeyRingUri(mDataUri);
        intent.setData(blobUri);

        // fill values for this action
        Bundle data = new Bundle();

        String server = (String) mKeyServerSpinner.getSelectedItem();
        data.putString(KeychainService.UPLOAD_KEY_SERVER, server);

        intent.putExtra(KeychainService.EXTRA_DATA, data);
        intent.putExtra(KeychainService.EXTRA_PARCELABLE_PROXY, parcelableProxy);

        // Message is received after uploading is done in KeychainService
        ServiceProgressHandler saveHandler = new ServiceProgressHandler(this) {
            @Override
            public void handleMessage(Message message) {
                // handle messages by standard KeychainIntentServiceHandler first
                super.handleMessage(message);

                if (message.arg1 == MessageStatus.OKAY.ordinal()) {

                    Toast.makeText(UploadKeyActivity.this, R.string.msg_crt_upload_success,
                            Toast.LENGTH_SHORT).show();
                    finish();
                }
            }
        };

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(saveHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        // show progress dialog
        saveHandler.showProgressDialog(
                getString(R.string.progress_uploading),
                ProgressDialog.STYLE_HORIZONTAL, false);

        // start service with intent
        startService(intent);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case android.R.id.home: {
                Intent viewIntent = NavUtils.getParentActivityIntent(this);
                viewIntent.setData(KeychainContract.KeyRings.buildGenericKeyRingUri(mDataUri));
                NavUtils.navigateUpTo(this, viewIntent);
                return true;
            }
        }
        return super.onOptionsItemSelected(item);
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/ViewKeyActivity.java
/*
 * Copyright (C) 2013-2014 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2013 Bahtiar 'kalkin' Gadimov
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

import android.animation.ArgbEvaluator;
import android.animation.ObjectAnimator;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.ActivityOptions;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Message;
import android.os.Messenger;
import android.provider.ContactsContract;
import android.support.v4.app.ActivityCompat;
import android.support.v4.app.FragmentManager;
import android.support.v4.app.LoaderManager;
import android.support.v4.content.CursorLoader;
import android.support.v4.content.Loader;
import android.support.v7.widget.CardView;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.animation.AlphaAnimation;
import android.view.animation.Animation;
import android.view.animation.Animation.AnimationListener;
import android.view.animation.AnimationUtils;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.RelativeLayout;
import android.widget.TextView;
import android.widget.Toast;
import com.getbase.floatingactionbutton.FloatingActionButton;
import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.keyimport.ParcelableKeyRing;
import org.sufficientlysecure.keychain.operations.results.CertifyResult;
import org.sufficientlysecure.keychain.operations.results.ImportKeyResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.pgp.KeyRing;
import org.sufficientlysecure.keychain.pgp.exception.PgpKeyNotFoundException;
import org.sufficientlysecure.keychain.provider.CachedPublicKeyRing;
import org.sufficientlysecure.keychain.provider.KeychainContract;
import org.sufficientlysecure.keychain.provider.KeychainContract.KeyRings;
import org.sufficientlysecure.keychain.provider.ProviderHelper;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler.MessageStatus;
import org.sufficientlysecure.keychain.service.PassphraseCacheService;
import org.sufficientlysecure.keychain.ui.base.BaseNfcActivity;
import org.sufficientlysecure.keychain.ui.dialog.DeleteKeyDialogFragment;
import org.sufficientlysecure.keychain.ui.util.FormattingUtils;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils.State;
import org.sufficientlysecure.keychain.ui.util.Notify;
import org.sufficientlysecure.keychain.ui.util.Notify.ActionListener;
import org.sufficientlysecure.keychain.ui.util.Notify.Style;
import org.sufficientlysecure.keychain.ui.util.QrCodeUtils;
import org.sufficientlysecure.keychain.util.ContactHelper;
import org.sufficientlysecure.keychain.util.ExportHelper;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.NfcHelper;
import org.sufficientlysecure.keychain.util.ParcelableProxy;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;

public class ViewKeyActivity extends BaseNfcActivity implements
        LoaderManager.LoaderCallbacks<Cursor> {

    public static final String EXTRA_NFC_USER_ID = "nfc_user_id";
    public static final String EXTRA_NFC_AID = "nfc_aid";
    public static final String EXTRA_NFC_FINGERPRINTS = "nfc_fingerprints";

    static final int REQUEST_QR_FINGERPRINT = 1;
    static final int REQUEST_DELETE = 2;
    static final int REQUEST_EXPORT = 3;
    public static final String EXTRA_DISPLAY_RESULT = "display_result";

    ExportHelper mExportHelper;
    ProviderHelper mProviderHelper;

    protected Uri mDataUri;

    private TextView mName;
    private TextView mStatusText;
    private ImageView mStatusImage;
    private RelativeLayout mBigToolbar;

    private ImageButton mActionEncryptFile;
    private ImageButton mActionEncryptText;
    private ImageButton mActionNfc;
    private FloatingActionButton mFab;
    private ImageView mPhoto;
    private ImageView mQrCode;
    private CardView mQrCodeLayout;

    private String mQrCodeLoaded;

    // NFC
    private NfcHelper mNfcHelper;

    private static final int LOADER_ID_UNIFIED = 0;

    private boolean mIsSecret = false;
    private boolean mHasEncrypt = false;
    private boolean mIsVerified = false;
    private boolean mIsRevoked = false;
    private boolean mIsExpired = false;

    private boolean mShowYubikeyAfterCreation = false;

    private MenuItem mRefreshItem;
    private boolean mIsRefreshing;
    private Animation mRotate, mRotateSpin;
    private View mRefresh;
    private String mFingerprint;
    private long mMasterKeyId;

    @SuppressLint("InflateParams")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mExportHelper = new ExportHelper(this);
        mProviderHelper = new ProviderHelper(this);

        setTitle(null);

        mName = (TextView) findViewById(R.id.view_key_name);
        mStatusText = (TextView) findViewById(R.id.view_key_status);
        mStatusImage = (ImageView) findViewById(R.id.view_key_status_image);
        mBigToolbar = (RelativeLayout) findViewById(R.id.toolbar_big);

        mActionEncryptFile = (ImageButton) findViewById(R.id.view_key_action_encrypt_files);
        mActionEncryptText = (ImageButton) findViewById(R.id.view_key_action_encrypt_text);
        mActionNfc = (ImageButton) findViewById(R.id.view_key_action_nfc);
        mFab = (FloatingActionButton) findViewById(R.id.fab);
        mPhoto = (ImageView) findViewById(R.id.view_key_photo);
        mQrCode = (ImageView) findViewById(R.id.view_key_qr_code);
        mQrCodeLayout = (CardView) findViewById(R.id.view_key_qr_code_layout);

        mRotateSpin = AnimationUtils.loadAnimation(this, R.anim.rotate_spin);
        mRotateSpin.setAnimationListener(new AnimationListener() {
            @Override
            public void onAnimationStart(Animation animation) {

            }

            @Override
            public void onAnimationEnd(Animation animation) {
                mRefreshItem.getActionView().clearAnimation();
                mRefreshItem.setActionView(null);
                mRefreshItem.setEnabled(true);

                // this is a deferred call
                supportInvalidateOptionsMenu();
            }

            @Override
            public void onAnimationRepeat(Animation animation) {

            }
        });
        mRotate = AnimationUtils.loadAnimation(this, R.anim.rotate);
        mRotate.setRepeatCount(Animation.INFINITE);
        mRotate.setAnimationListener(new Animation.AnimationListener() {
            @Override
            public void onAnimationStart(Animation animation) {

            }

            @Override
            public void onAnimationEnd(Animation animation) {

            }

            @Override
            public void onAnimationRepeat(Animation animation) {
                if (!mIsRefreshing) {
                    mRefreshItem.getActionView().clearAnimation();
                    mRefreshItem.getActionView().startAnimation(mRotateSpin);
                }
            }
        });
        mRefresh = getLayoutInflater().inflate(R.layout.indeterminate_progress, null);

        mDataUri = getIntent().getData();
        if (mDataUri == null) {
            Log.e(Constants.TAG, "Data missing. Should be uri of key!");
            finish();
            return;
        }
        if (mDataUri.getHost().equals(ContactsContract.AUTHORITY)) {
            mDataUri = ContactHelper.dataUriFromContactUri(this, mDataUri);
            if (mDataUri == null) {
                Log.e(Constants.TAG, "Contact Data missing. Should be uri of key!");
                Toast.makeText(this, R.string.error_contacts_key_id_missing, Toast.LENGTH_LONG).show();
                finish();
                return;
            }
        }

        Log.i(Constants.TAG, "mDataUri: " + mDataUri);

        mActionEncryptFile.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                encrypt(mDataUri, false);
            }
        });
        mActionEncryptText.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                encrypt(mDataUri, true);
            }
        });

        mFab.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (mIsSecret) {
                    startSafeSlinger(mDataUri);
                } else {
                    scanQrCode();
                }
            }
        });

        mQrCodeLayout.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showQrCodeDialog();
            }
        });

        mActionNfc.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mNfcHelper.invokeNfcBeam();
            }
        });

        // Prepare the loaders. Either re-connect with an existing ones,
        // or start new ones.
        getSupportLoaderManager().initLoader(LOADER_ID_UNIFIED, null, this);

        mNfcHelper = new NfcHelper(this, mProviderHelper);
        mNfcHelper.initNfc(mDataUri);

        if (savedInstanceState == null && getIntent().hasExtra(EXTRA_DISPLAY_RESULT)) {
            OperationResult result = getIntent().getParcelableExtra(EXTRA_DISPLAY_RESULT);
            result.createNotify(this).show();
        }

        // Fragments are stored, no need to recreate those
        if (savedInstanceState != null) {
            return;
        }

        FragmentManager manager = getSupportFragmentManager();
        // Create an instance of the fragment
        final ViewKeyFragment frag = ViewKeyFragment.newInstance(mDataUri);
        manager.beginTransaction()
                .replace(R.id.view_key_fragment, frag)
                .commit();

        // need to postpone loading of the yubikey fragment until after mMasterKeyId
        // is available, but we mark here that this should be done
        mShowYubikeyAfterCreation = true;

    }

    @Override
    protected void initLayout() {
        setContentView(R.layout.view_key_activity);
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        super.onCreateOptionsMenu(menu);
        getMenuInflater().inflate(R.menu.key_view, menu);
        mRefreshItem = menu.findItem(R.id.menu_key_view_refresh);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case android.R.id.home: {
                Intent homeIntent = new Intent(this, MainActivity.class);
                homeIntent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                startActivity(homeIntent);
                return true;
            }
            case R.id.menu_key_view_export_file: {
                try {
                    if (PassphraseCacheService.getCachedPassphrase(this, mMasterKeyId, mMasterKeyId) != null) {
                        exportToFile(mDataUri, mExportHelper, mProviderHelper);
                        return true;
                    }

                    startPassphraseActivity(REQUEST_EXPORT);
                } catch (PassphraseCacheService.KeyNotFoundException e) {
                    // This happens when the master key is stripped
                    exportToFile(mDataUri, mExportHelper, mProviderHelper);
                }
                return true;
            }
            case R.id.menu_key_view_delete: {
                try {
                    if (PassphraseCacheService.getCachedPassphrase(this, mMasterKeyId, mMasterKeyId) != null) {
                        deleteKey();
                        return true;
                    }

                    startPassphraseActivity(REQUEST_DELETE);
                } catch (PassphraseCacheService.KeyNotFoundException e) {
                    // This happens when the master key is stripped
                    deleteKey();
                }
                return true;
            }
            case R.id.menu_key_view_advanced: {
                Intent advancedIntent = new Intent(this, ViewKeyAdvActivity.class);
                advancedIntent.setData(mDataUri);
                startActivity(advancedIntent);
                return true;
            }
            case R.id.menu_key_view_refresh: {
                try {
                    final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(this).getProxyPrefs();
                    Runnable ignoreTor = new Runnable() {
                        @Override
                        public void run() {
                            try {
                                updateFromKeyserver(mDataUri, mProviderHelper, new ParcelableProxy(null, -1, null));
                            } catch (ProviderHelper.NotFoundException e) {
                                Notify.create(ViewKeyActivity.this, R.string.error_key_not_found, Notify.Style.ERROR)
                                        .show();
                            }
                        }
                    };

                    if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs, this)) {
                        updateFromKeyserver(mDataUri, mProviderHelper, proxyPrefs.parcelableProxy);
                    }
                } catch (ProviderHelper.NotFoundException e) {
                    Notify.create(this, R.string.error_key_not_found, Notify.Style.ERROR).show();
                }
                return true;
            }
            case R.id.menu_key_view_edit: {
                editKey(mDataUri);
                return true;
            }
            case R.id.menu_key_view_certify_fingerprint: {
                certifyFingeprint(mDataUri);
                return true;
            }
        }
        return super.onOptionsItemSelected(item);
    }

    @Override
    public boolean onPrepareOptionsMenu(Menu menu) {
        MenuItem editKey = menu.findItem(R.id.menu_key_view_edit);
        editKey.setVisible(mIsSecret);
        MenuItem certifyFingerprint = menu.findItem(R.id.menu_key_view_certify_fingerprint);
        certifyFingerprint.setVisible(!mIsSecret && !mIsVerified && !mIsExpired && !mIsRevoked);

        return true;
    }


    private void scanQrCode() {
        Intent scanQrCode = new Intent(this, ImportKeysProxyActivity.class);
        scanQrCode.setAction(ImportKeysProxyActivity.ACTION_SCAN_WITH_RESULT);
        startActivityForResult(scanQrCode, REQUEST_QR_FINGERPRINT);
    }

    private void certifyFingeprint(Uri dataUri) {
        Intent intent = new Intent(this, CertifyFingerprintActivity.class);
        intent.setData(dataUri);

        startCertifyIntent(intent);
    }

    private void certifyImmediate() {
        Intent intent = new Intent(this, CertifyKeyActivity.class);
        intent.putExtra(CertifyKeyActivity.EXTRA_KEY_IDS, new long[]{mMasterKeyId});

        startCertifyIntent(intent);
    }

    private void startCertifyIntent(Intent intent) {
        // Message is received after signing is done in KeychainService
        ServiceProgressHandler saveHandler = new ServiceProgressHandler(this) {
            @Override
            public void handleMessage(Message message) {
                // handle messages by standard KeychainIntentServiceHandler first
                super.handleMessage(message);

                if (message.arg1 == MessageStatus.OKAY.ordinal()) {
                    Bundle data = message.getData();
                    CertifyResult result = data.getParcelable(CertifyResult.EXTRA_RESULT);

                    result.createNotify(ViewKeyActivity.this).show();
                }
            }
        };
        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(saveHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        startActivityForResult(intent, 0);
    }

    private void showQrCodeDialog() {
        Intent qrCodeIntent = new Intent(this, QrCodeViewActivity.class);

        // create the transition animation - the images in the layouts
        // of both activities are defined with android:transitionName="qr_code"
        Bundle opts = null;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            ActivityOptions options = ActivityOptions
                    .makeSceneTransitionAnimation(this, mQrCodeLayout, "qr_code");
            opts = options.toBundle();
        }

        qrCodeIntent.setData(mDataUri);
        ActivityCompat.startActivity(this, qrCodeIntent, opts);
    }

    private void startPassphraseActivity(int requestCode) {
        Intent intent = new Intent(this, PassphraseDialogActivity.class);
        intent.putExtra(PassphraseDialogActivity.EXTRA_SUBKEY_ID, mMasterKeyId);
        startActivityForResult(intent, requestCode);
    }

    private void exportToFile(Uri dataUri, ExportHelper exportHelper, ProviderHelper providerHelper) {
        try {
            Uri baseUri = KeychainContract.KeyRings.buildUnifiedKeyRingUri(dataUri);

            HashMap<String, Object> data = providerHelper.getGenericData(
                    baseUri,
                    new String[]{KeychainContract.Keys.MASTER_KEY_ID, KeychainContract.KeyRings.HAS_SECRET},
                    new int[]{ProviderHelper.FIELD_TYPE_INTEGER, ProviderHelper.FIELD_TYPE_INTEGER});

            exportHelper.showExportKeysDialog(
                    new long[]{(Long) data.get(KeychainContract.KeyRings.MASTER_KEY_ID)},
                    Constants.Path.APP_DIR_FILE, ((Long) data.get(KeychainContract.KeyRings.HAS_SECRET) != 0)
            );
        } catch (ProviderHelper.NotFoundException e) {
            Notify.create(this, R.string.error_key_not_found, Notify.Style.ERROR).show();
            Log.e(Constants.TAG, "Key not found", e);
        }
    }

    private void deleteKey() {
        // Message is received after key is deleted
        Handler returnHandler = new Handler() {
            @Override
            public void handleMessage(Message message) {
                if (message.arg1 == MessageStatus.OKAY.ordinal()) {
                    setResult(RESULT_CANCELED);
                    finish();
                }
            }
        };

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(returnHandler);
        DeleteKeyDialogFragment deleteKeyDialog = DeleteKeyDialogFragment.newInstance(messenger,
                new long[]{mMasterKeyId});
        deleteKeyDialog.show(getSupportFragmentManager(), "deleteKeyDialog");
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQUEST_QR_FINGERPRINT && resultCode == Activity.RESULT_OK) {

            // If there is an EXTRA_RESULT, that's an error. Just show it.
            if (data.hasExtra(OperationResult.EXTRA_RESULT)) {
                OperationResult result = data.getParcelableExtra(OperationResult.EXTRA_RESULT);
                result.createNotify(this).show();
                return;
            }

            String fp = data.getStringExtra(ImportKeysProxyActivity.EXTRA_FINGERPRINT);
            if (fp == null) {
                Notify.create(this, "Error scanning fingerprint!",
                        Notify.LENGTH_LONG, Notify.Style.ERROR).show();
                return;
            }
            if (mFingerprint.equalsIgnoreCase(fp)) {
                certifyImmediate();
            } else {
                Notify.create(this, "Fingerprints did not match!",
                        Notify.LENGTH_LONG, Notify.Style.ERROR).show();
            }

            return;
        }

        if (requestCode == REQUEST_DELETE && resultCode == Activity.RESULT_OK) {
            deleteKey();
        }

        if (requestCode == REQUEST_EXPORT && resultCode == Activity.RESULT_OK) {
            exportToFile(mDataUri, mExportHelper, mProviderHelper);
        }

        if (data != null && data.hasExtra(OperationResult.EXTRA_RESULT)) {
            OperationResult result = data.getParcelableExtra(OperationResult.EXTRA_RESULT);
            result.createNotify(this).show();
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }

    @Override
    protected void onNfcPerform() throws IOException {

        final byte[] nfcFingerprints = nfcGetFingerprints();
        final String nfcUserId = nfcGetUserId();
        final byte[] nfcAid = nfcGetAid();

        long yubiKeyId = KeyFormattingUtils.getKeyIdFromFingerprint(nfcFingerprints);

        try {

            // if the yubikey matches a subkey in any key
            CachedPublicKeyRing ring = mProviderHelper.getCachedPublicKeyRing(
                    KeyRings.buildUnifiedKeyRingsFindBySubkeyUri(yubiKeyId));
            byte[] candidateFp = ring.getFingerprint();

            // if the master key of that key matches this one, just show the yubikey dialog
            if (KeyFormattingUtils.convertFingerprintToHex(candidateFp).equals(mFingerprint)) {
                showYubiKeyFragment(nfcFingerprints, nfcUserId, nfcAid);
                return;
            }

            // otherwise, offer to go to that key
            final long masterKeyId = KeyFormattingUtils.getKeyIdFromFingerprint(candidateFp);
            Notify.create(this, R.string.snack_yubi_other, Notify.LENGTH_LONG,
                    Style.WARN, new ActionListener() {
                        @Override
                        public void onAction() {
                            Intent intent = new Intent(
                                    ViewKeyActivity.this, ViewKeyActivity.class);
                            intent.setData(KeyRings.buildGenericKeyRingUri(masterKeyId));
                            intent.putExtra(ViewKeyActivity.EXTRA_NFC_AID, nfcAid);
                            intent.putExtra(ViewKeyActivity.EXTRA_NFC_USER_ID, nfcUserId);
                            intent.putExtra(ViewKeyActivity.EXTRA_NFC_FINGERPRINTS, nfcFingerprints);
                            startActivity(intent);
                            finish();
                        }
                    }, R.string.snack_yubikey_view).show();

            // and if it's not found, offer import
        } catch (PgpKeyNotFoundException e) {
            Notify.create(this, R.string.snack_yubi_other, Notify.LENGTH_LONG,
                    Style.WARN, new ActionListener() {
                        @Override
                        public void onAction() {
                            Intent intent = new Intent(
                                    ViewKeyActivity.this, CreateKeyActivity.class);
                            intent.putExtra(ViewKeyActivity.EXTRA_NFC_AID, nfcAid);
                            intent.putExtra(ViewKeyActivity.EXTRA_NFC_USER_ID, nfcUserId);
                            intent.putExtra(ViewKeyActivity.EXTRA_NFC_FINGERPRINTS, nfcFingerprints);
                            startActivity(intent);
                            finish();
                        }
                    }, R.string.snack_yubikey_import).show();
        }

    }

    public void showYubiKeyFragment(
            final byte[] nfcFingerprints, final String nfcUserId, final byte[] nfcAid) {

        new Handler().post(new Runnable() {
            @Override
            public void run() {
                ViewKeyYubiKeyFragment frag = ViewKeyYubiKeyFragment.newInstance(
                        mMasterKeyId, nfcFingerprints, nfcUserId, nfcAid);

                FragmentManager manager = getSupportFragmentManager();

                manager.popBackStack("yubikey", FragmentManager.POP_BACK_STACK_INCLUSIVE);
                manager.beginTransaction()
                        .addToBackStack("yubikey")
                        .replace(R.id.view_key_fragment, frag)
                                // if this is called while the activity wasn't resumed, just forget it happened
                        .commitAllowingStateLoss();
            }
        });

    }

    private void encrypt(Uri dataUri, boolean text) {
        // If there is no encryption key, don't bother.
        if (!mHasEncrypt) {
            Notify.create(this, R.string.error_no_encrypt_subkey, Notify.Style.ERROR).show();
            return;
        }
        try {
            long keyId = new ProviderHelper(this)
                    .getCachedPublicKeyRing(dataUri)
                    .extractOrGetMasterKeyId();
            long[] encryptionKeyIds = new long[]{keyId};
            Intent intent;
            if (text) {
                intent = new Intent(this, EncryptTextActivity.class);
                intent.setAction(EncryptTextActivity.ACTION_ENCRYPT_TEXT);
                intent.putExtra(EncryptTextActivity.EXTRA_ENCRYPTION_KEY_IDS, encryptionKeyIds);
            } else {
                intent = new Intent(this, EncryptFilesActivity.class);
                intent.setAction(EncryptFilesActivity.ACTION_ENCRYPT_DATA);
                intent.putExtra(EncryptFilesActivity.EXTRA_ENCRYPTION_KEY_IDS, encryptionKeyIds);
            }
            // used instead of startActivity set actionbar based on callingPackage
            startActivityForResult(intent, 0);
        } catch (PgpKeyNotFoundException e) {
            Log.e(Constants.TAG, "key not found!", e);
        }
    }

    private void updateFromKeyserver(Uri dataUri, ProviderHelper providerHelper, ParcelableProxy parcelableProxy)
            throws ProviderHelper.NotFoundException {

        mIsRefreshing = true;
        mRefreshItem.setEnabled(false);
        mRefreshItem.setActionView(mRefresh);
        mRefresh.startAnimation(mRotate);

        byte[] blob = (byte[]) providerHelper.getGenericData(
                KeychainContract.KeyRings.buildUnifiedKeyRingUri(dataUri),
                KeychainContract.Keys.FINGERPRINT, ProviderHelper.FIELD_TYPE_BLOB);
        String fingerprint = KeyFormattingUtils.convertFingerprintToHex(blob);

        ParcelableKeyRing keyEntry = new ParcelableKeyRing(fingerprint, null, null);
        ArrayList<ParcelableKeyRing> entries = new ArrayList<>();
        entries.add(keyEntry);

        // Message is received after importing is done in KeychainService
        ServiceProgressHandler serviceHandler = new ServiceProgressHandler(this) {
            @Override
            public void handleMessage(Message message) {
                // handle messages by standard KeychainIntentServiceHandler first
                super.handleMessage(message);

                if (message.arg1 == MessageStatus.OKAY.ordinal()) {
                    // get returned data bundle
                    Bundle returnData = message.getData();

                    mIsRefreshing = false;

                    if (returnData == null) {
                        finish();
                        return;
                    }
                    final ImportKeyResult result =
                            returnData.getParcelable(OperationResult.EXTRA_RESULT);
                    result.createNotify(ViewKeyActivity.this).show();
                }
            }
        };

        // fill values for this action
        Bundle data = new Bundle();

        // search config
        {
            Preferences prefs = Preferences.getPreferences(this);
            Preferences.CloudSearchPrefs cloudPrefs =
                    new Preferences.CloudSearchPrefs(true, true, prefs.getPreferredKeyserver());
            data.putString(KeychainService.IMPORT_KEY_SERVER, cloudPrefs.keyserver);
        }

        data.putParcelableArrayList(KeychainService.IMPORT_KEY_LIST, entries);

        data.putParcelable(KeychainService.EXTRA_PARCELABLE_PROXY, parcelableProxy);

        // Send all information needed to service to query keys in other thread
        Intent intent = new Intent(this, KeychainService.class);
        intent.setAction(KeychainService.ACTION_IMPORT_KEYRING);
        intent.putExtra(KeychainService.EXTRA_DATA, data);

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(serviceHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        // start service with intent
        startService(intent);

    }

    private void editKey(Uri dataUri) {
        Intent editIntent = new Intent(this, EditKeyActivity.class);
        editIntent.setData(KeychainContract.KeyRingData.buildSecretKeyRingUri(dataUri));
        startActivityForResult(editIntent, 0);
    }

    private void startSafeSlinger(Uri dataUri) {
        long keyId = 0;
        try {
            keyId = new ProviderHelper(this)
                    .getCachedPublicKeyRing(dataUri)
                    .extractOrGetMasterKeyId();
        } catch (PgpKeyNotFoundException e) {
            Log.e(Constants.TAG, "key not found!", e);
        }
        Intent safeSlingerIntent = new Intent(this, SafeSlingerActivity.class);
        safeSlingerIntent.putExtra(SafeSlingerActivity.EXTRA_MASTER_KEY_ID, keyId);
        startActivityForResult(safeSlingerIntent, 0);
    }

    /**
     * Load QR Code asynchronously and with a fade in animation
     */
    private void loadQrCode(final String fingerprint) {
        AsyncTask<Void, Void, Bitmap> loadTask =
                new AsyncTask<Void, Void, Bitmap>() {
                    protected Bitmap doInBackground(Void... unused) {
                        Uri uri = new Uri.Builder()
                                .scheme(Constants.FINGERPRINT_SCHEME)
                                .opaquePart(fingerprint)
                                .build();
                        // render with minimal size
                        return QrCodeUtils.getQRCodeBitmap(uri, 0);
                    }

                    protected void onPostExecute(Bitmap qrCode) {
                        mQrCodeLoaded = fingerprint;
                        // scale the image up to our actual size. we do this in code rather
                        // than let the ImageView do this because we don't require filtering.
                        Bitmap scaled = Bitmap.createScaledBitmap(qrCode,
                                mQrCode.getHeight(), mQrCode.getHeight(),
                                false);
                        mQrCode.setImageBitmap(scaled);

                        // simple fade-in animation
                        AlphaAnimation anim = new AlphaAnimation(0.0f, 1.0f);
                        anim.setDuration(200);
                        mQrCode.startAnimation(anim);
                    }
                };

        loadTask.execute();
    }


    // These are the rows that we will retrieve.
    static final String[] PROJECTION = new String[]{
            KeychainContract.KeyRings._ID,
            KeychainContract.KeyRings.MASTER_KEY_ID,
            KeychainContract.KeyRings.USER_ID,
            KeychainContract.KeyRings.IS_REVOKED,
            KeychainContract.KeyRings.IS_EXPIRED,
            KeychainContract.KeyRings.VERIFIED,
            KeychainContract.KeyRings.HAS_ANY_SECRET,
            KeychainContract.KeyRings.FINGERPRINT,
            KeychainContract.KeyRings.HAS_ENCRYPT
    };

    static final int INDEX_MASTER_KEY_ID = 1;
    static final int INDEX_USER_ID = 2;
    static final int INDEX_IS_REVOKED = 3;
    static final int INDEX_IS_EXPIRED = 4;
    static final int INDEX_VERIFIED = 5;
    static final int INDEX_HAS_ANY_SECRET = 6;
    static final int INDEX_FINGERPRINT = 7;
    static final int INDEX_HAS_ENCRYPT = 8;

    @Override
    public Loader<Cursor> onCreateLoader(int id, Bundle args) {
        switch (id) {
            case LOADER_ID_UNIFIED: {
                Uri baseUri = KeychainContract.KeyRings.buildUnifiedKeyRingUri(mDataUri);
                return new CursorLoader(this, baseUri, PROJECTION, null, null, null);
            }

            default:
                return null;
        }
    }

    int mPreviousColor = 0;

    @Override
    public void onLoadFinished(Loader<Cursor> loader, Cursor data) {
        /* TODO better error handling? May cause problems when a key is deleted,
         * because the notification triggers faster than the activity closes.
         */
        // Avoid NullPointerExceptions...
        if (data.getCount() == 0) {
            return;
        }
        // Swap the new cursor in. (The framework will take care of closing the
        // old cursor once we return.)
        switch (loader.getId()) {
            case LOADER_ID_UNIFIED: {

                if (data.moveToFirst()) {
                    // get name, email, and comment from USER_ID
                    KeyRing.UserId mainUserId = KeyRing.splitUserId(data.getString(INDEX_USER_ID));
                    if (mainUserId.name != null) {
                        mName.setText(mainUserId.name);
                    } else {
                        mName.setText(R.string.user_id_no_name);
                    }

                    mMasterKeyId = data.getLong(INDEX_MASTER_KEY_ID);
                    mFingerprint = KeyFormattingUtils.convertFingerprintToHex(data.getBlob(INDEX_FINGERPRINT));

                    // if it wasn't shown yet, display yubikey fragment
                    if (mShowYubikeyAfterCreation && getIntent().hasExtra(EXTRA_NFC_AID)) {
                        mShowYubikeyAfterCreation = false;
                        Intent intent = getIntent();
                        byte[] nfcFingerprints = intent.getByteArrayExtra(EXTRA_NFC_FINGERPRINTS);
                        String nfcUserId = intent.getStringExtra(EXTRA_NFC_USER_ID);
                        byte[] nfcAid = intent.getByteArrayExtra(EXTRA_NFC_AID);
                        showYubiKeyFragment(nfcFingerprints, nfcUserId, nfcAid);
                    }

                    mIsSecret = data.getInt(INDEX_HAS_ANY_SECRET) != 0;
                    mHasEncrypt = data.getInt(INDEX_HAS_ENCRYPT) != 0;
                    mIsRevoked = data.getInt(INDEX_IS_REVOKED) > 0;
                    mIsExpired = data.getInt(INDEX_IS_EXPIRED) != 0;
                    mIsVerified = data.getInt(INDEX_VERIFIED) > 0;

                    // if the refresh animation isn't playing
                    if (!mRotate.hasStarted() && !mRotateSpin.hasStarted()) {
                        // re-create options menu based on mIsSecret, mIsVerified
                        supportInvalidateOptionsMenu();
                        // this is done at the end of the animation otherwise
                    }

                    AsyncTask<Long, Void, Bitmap> photoTask =
                            new AsyncTask<Long, Void, Bitmap>() {
                                protected Bitmap doInBackground(Long... mMasterKeyId) {
                                    return ContactHelper.loadPhotoByMasterKeyId(getContentResolver(),
                                            mMasterKeyId[0], true);
                                }

                                protected void onPostExecute(Bitmap photo) {
                                    mPhoto.setImageBitmap(photo);
                                    mPhoto.setVisibility(View.VISIBLE);
                                }
                            };

                    // Note: order is important
                    int color;
                    if (mIsRevoked) {
                        mStatusText.setText(R.string.view_key_revoked);
                        mStatusImage.setVisibility(View.VISIBLE);
                        KeyFormattingUtils.setStatusImage(this, mStatusImage, mStatusText,
                                State.REVOKED, R.color.icons, true);
                        color = getResources().getColor(R.color.android_red_light);

                        mActionEncryptFile.setVisibility(View.GONE);
                        mActionEncryptText.setVisibility(View.GONE);
                        mActionNfc.setVisibility(View.GONE);
                        mFab.setVisibility(View.GONE);
                        mQrCodeLayout.setVisibility(View.GONE);
                    } else if (mIsExpired) {
                        if (mIsSecret) {
                            mStatusText.setText(R.string.view_key_expired_secret);
                        } else {
                            mStatusText.setText(R.string.view_key_expired);
                        }
                        mStatusImage.setVisibility(View.VISIBLE);
                        KeyFormattingUtils.setStatusImage(this, mStatusImage, mStatusText,
                                State.EXPIRED, R.color.icons, true);
                        color = getResources().getColor(R.color.android_red_light);

                        mActionEncryptFile.setVisibility(View.GONE);
                        mActionEncryptText.setVisibility(View.GONE);
                        mActionNfc.setVisibility(View.GONE);
                        mFab.setVisibility(View.GONE);
                        mQrCodeLayout.setVisibility(View.GONE);
                    } else if (mIsSecret) {
                        mStatusText.setText(R.string.view_key_my_key);
                        mStatusImage.setVisibility(View.GONE);
                        color = getResources().getColor(R.color.primary);
                        // reload qr code only if the fingerprint changed
                        if (!mFingerprint.equals(mQrCodeLoaded)) {
                            loadQrCode(mFingerprint);
                        }
                        photoTask.execute(mMasterKeyId);
                        mQrCodeLayout.setVisibility(View.VISIBLE);

                        // and place leftOf qr code
                        RelativeLayout.LayoutParams nameParams = (RelativeLayout.LayoutParams)
                                mName.getLayoutParams();
                        // remove right margin
                        nameParams.setMargins(FormattingUtils.dpToPx(this, 48), 0, 0, 0);
                        if (android.os.Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1) {
                            nameParams.setMarginEnd(0);
                        }
                        nameParams.addRule(RelativeLayout.LEFT_OF, R.id.view_key_qr_code_layout);
                        mName.setLayoutParams(nameParams);

                        RelativeLayout.LayoutParams statusParams = (RelativeLayout.LayoutParams)
                                mStatusText.getLayoutParams();
                        statusParams.setMargins(FormattingUtils.dpToPx(this, 48), 0, 0, 0);
                        if (android.os.Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1) {
                            statusParams.setMarginEnd(0);
                        }
                        statusParams.addRule(RelativeLayout.LEFT_OF, R.id.view_key_qr_code_layout);
                        mStatusText.setLayoutParams(statusParams);

                        mActionEncryptFile.setVisibility(View.VISIBLE);
                        mActionEncryptText.setVisibility(View.VISIBLE);

                        // invokeBeam is available from API 21
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                            mActionNfc.setVisibility(View.VISIBLE);
                        } else {
                            mActionNfc.setVisibility(View.GONE);
                        }
                        mFab.setVisibility(View.VISIBLE);
                        mFab.setIconDrawable(getResources().getDrawable(R.drawable.ic_repeat_white_24dp));
                    } else {
                        mActionEncryptFile.setVisibility(View.VISIBLE);
                        mActionEncryptText.setVisibility(View.VISIBLE);
                        mQrCodeLayout.setVisibility(View.GONE);
                        mActionNfc.setVisibility(View.GONE);

                        if (mIsVerified) {
                            mStatusText.setText(R.string.view_key_verified);
                            mStatusImage.setVisibility(View.VISIBLE);
                            KeyFormattingUtils.setStatusImage(this, mStatusImage, mStatusText,
                                    State.VERIFIED, R.color.icons, true);
                            color = getResources().getColor(R.color.primary);
                            photoTask.execute(mMasterKeyId);

                            mFab.setVisibility(View.GONE);
                        } else {
                            mStatusText.setText(R.string.view_key_unverified);
                            mStatusImage.setVisibility(View.VISIBLE);
                            KeyFormattingUtils.setStatusImage(this, mStatusImage, mStatusText,
                                    State.UNVERIFIED, R.color.icons, true);
                            color = getResources().getColor(R.color.android_orange_light);

                            mFab.setVisibility(View.VISIBLE);
                        }
                    }

                    if (mPreviousColor == 0 || mPreviousColor == color) {
                        mStatusBar.setBackgroundColor(color);
                        mBigToolbar.setBackgroundColor(color);
                        mPreviousColor = color;
                    } else {
                        ObjectAnimator colorFade1 =
                                ObjectAnimator.ofObject(mStatusBar, "backgroundColor",
                                        new ArgbEvaluator(), mPreviousColor, color);
                        ObjectAnimator colorFade2 =
                                ObjectAnimator.ofObject(mBigToolbar, "backgroundColor",
                                        new ArgbEvaluator(), mPreviousColor, color);

                        colorFade1.setDuration(1200);
                        colorFade2.setDuration(1200);
                        colorFade1.start();
                        colorFade2.start();
                        mPreviousColor = color;
                    }

                    //noinspection deprecation
                    mStatusImage.setAlpha(80);

                    break;
                }
            }
        }
    }

    @Override
    public void onLoaderReset(Loader<Cursor> loader) {

    }
}

File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/ViewKeyTrustFragment.java
/*
 * Copyright (C) 2014 Tim Bray <tbray@textuality.com>
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

import android.app.ProgressDialog;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.support.v4.app.LoaderManager;
import android.support.v4.content.CursorLoader;
import android.support.v4.content.Loader;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.method.LinkMovementMethod;
import android.text.style.ClickableSpan;
import android.text.style.StyleSpan;
import android.text.style.URLSpan;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TableLayout;
import android.widget.TableRow;
import android.widget.TextView;

import com.textuality.keybase.lib.KeybaseException;
import com.textuality.keybase.lib.Proof;
import com.textuality.keybase.lib.User;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.provider.KeychainContract.KeyRings;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.ParcelableProxy;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

import java.util.ArrayList;
import java.util.Hashtable;
import java.util.List;

public class ViewKeyTrustFragment extends LoaderFragment implements
        LoaderManager.LoaderCallbacks<Cursor> {

    public static final String ARG_DATA_URI = "uri";

    private View mStartSearch;
    private TextView mTrustReadout;
    private TextView mReportHeader;
    private TableLayout mProofListing;
    private LayoutInflater mInflater;
    private View mProofVerifyHeader;
    private TextView mProofVerifyDetail;

    private static final int LOADER_ID_DATABASE = 1;

    // for retrieving the key we’re working on
    private Uri mDataUri;

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup superContainer, Bundle savedInstanceState) {
        View root = super.onCreateView(inflater, superContainer, savedInstanceState);
        View view = inflater.inflate(R.layout.view_key_adv_keybase_fragment, getContainer());
        mInflater = inflater;

        mTrustReadout = (TextView) view.findViewById(R.id.view_key_trust_readout);
        mStartSearch = view.findViewById(R.id.view_key_trust_search_cloud);
        mStartSearch.setEnabled(false);
        mReportHeader = (TextView) view.findViewById(R.id.view_key_trust_cloud_narrative);
        mProofListing = (TableLayout) view.findViewById(R.id.view_key_proof_list);
        mProofVerifyHeader = view.findViewById(R.id.view_key_proof_verify_header);
        mProofVerifyDetail = (TextView) view.findViewById(R.id.view_key_proof_verify_detail);
        mReportHeader.setVisibility(View.GONE);
        mProofListing.setVisibility(View.GONE);
        mProofVerifyHeader.setVisibility(View.GONE);
        mProofVerifyDetail.setVisibility(View.GONE);

        return root;
    }

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);

        Uri dataUri = getArguments().getParcelable(ARG_DATA_URI);
        if (dataUri == null) {
            Log.e(Constants.TAG, "Data missing. Should be Uri of key!");
            getActivity().finish();
            return;
        }
        mDataUri = dataUri;

        // retrieve the key from the database
        getLoaderManager().initLoader(LOADER_ID_DATABASE, null, this);
    }

    static final String[] TRUST_PROJECTION = new String[]{
            KeyRings._ID, KeyRings.FINGERPRINT, KeyRings.IS_REVOKED, KeyRings.IS_EXPIRED,
            KeyRings.HAS_ANY_SECRET, KeyRings.VERIFIED
    };
    static final int INDEX_TRUST_FINGERPRINT = 1;
    static final int INDEX_TRUST_IS_REVOKED = 2;
    static final int INDEX_TRUST_IS_EXPIRED = 3;
    static final int INDEX_UNIFIED_HAS_ANY_SECRET = 4;
    static final int INDEX_VERIFIED = 5;

    public Loader<Cursor> onCreateLoader(int id, Bundle args) {
        setContentShown(false);

        switch (id) {
            case LOADER_ID_DATABASE: {
                Uri baseUri = KeyRings.buildUnifiedKeyRingUri(mDataUri);
                return new CursorLoader(getActivity(), baseUri, TRUST_PROJECTION, null, null, null);
            }
            // decided to just use an AsyncTask for keybase, but maybe later
            default:
                return null;
        }
    }

    public void onLoadFinished(Loader<Cursor> loader, Cursor data) {
        /* TODO better error handling? May cause problems when a key is deleted,
         * because the notification triggers faster than the activity closes.
         */
        // Avoid NullPointerExceptions...
        if (data.getCount() == 0) {
            return;
        }

        boolean nothingSpecial = true;
        StringBuilder message = new StringBuilder();

        // Swap the new cursor in. (The framework will take care of closing the
        // old cursor once we return.)
        if (data.moveToFirst()) {

            if (data.getInt(INDEX_UNIFIED_HAS_ANY_SECRET) != 0) {
                message.append(getString(R.string.key_trust_it_is_yours)).append("\n");
                nothingSpecial = false;
            } else if (data.getInt(INDEX_VERIFIED) != 0) {
                message.append(getString(R.string.key_trust_already_verified)).append("\n");
                nothingSpecial = false;
            }

            // If this key is revoked, don’t trust it!
            if (data.getInt(INDEX_TRUST_IS_REVOKED) != 0) {
                message.append(getString(R.string.key_trust_revoked)).
                        append(getString(R.string.key_trust_old_keys));

                nothingSpecial = false;
            } else {
                if (data.getInt(INDEX_TRUST_IS_EXPIRED) != 0) {

                    // if expired, don’t trust it!
                    message.append(getString(R.string.key_trust_expired)).
                            append(getString(R.string.key_trust_old_keys));

                    nothingSpecial = false;
                }
            }

            if (nothingSpecial) {
                message.append(getString(R.string.key_trust_maybe));
            }

            final byte[] fp = data.getBlob(INDEX_TRUST_FINGERPRINT);
            final String fingerprint = KeyFormattingUtils.convertFingerprintToHex(fp);
            if (fingerprint != null) {

                mStartSearch.setEnabled(true);
                mStartSearch.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View view) {
                        final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(getActivity())
                                .getProxyPrefs();

                        Runnable ignoreTor = new Runnable() {
                            @Override
                            public void run() {
                                mStartSearch.setEnabled(false);
                                new DescribeKey(proxyPrefs.parcelableProxy).execute(fingerprint);
                            }
                        };

                        if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                                getActivity())) {
                            mStartSearch.setEnabled(false);
                            new DescribeKey(proxyPrefs.parcelableProxy).execute(fingerprint);
                        }
                    }
                });
            }
        }

        mTrustReadout.setText(message);
        setContentShown(true);
    }

    /**
     * This is called when the last Cursor provided to onLoadFinished() above is about to be closed.
     * We need to make sure we are no longer using it.
     */
    public void onLoaderReset(Loader<Cursor> loader) {
        // no-op in this case I think
    }

    class ResultPage {
        String mHeader;
        final List<CharSequence> mProofs;

        public ResultPage(String header, List<CharSequence> proofs) {
            mHeader = header;
            mProofs = proofs;
        }
    }

    // look for evidence from keybase in the background, make tabular version of result
    //
    private class DescribeKey extends AsyncTask<String, Void, ResultPage> {
        ParcelableProxy mParcelableProxy;

        public DescribeKey(ParcelableProxy parcelableProxy) {
            mParcelableProxy = parcelableProxy;
        }

        @Override
        protected ResultPage doInBackground(String... args) {
            String fingerprint = args[0];

            final ArrayList<CharSequence> proofList = new ArrayList<CharSequence>();
            final Hashtable<Integer, ArrayList<Proof>> proofs = new Hashtable<Integer, ArrayList<Proof>>();
            try {
                User keybaseUser = User.findByFingerprint(fingerprint, mParcelableProxy.getProxy());
                for (Proof proof : keybaseUser.getProofs()) {
                    Integer proofType = proof.getType();
                    appendIfOK(proofs, proofType, proof);
                }

                // a one-liner in a modern programming language
                for (Integer proofType : proofs.keySet()) {
                    Proof[] x = {};
                    Proof[] proofsFor = proofs.get(proofType).toArray(x);
                    if (proofsFor.length > 0) {
                        SpannableStringBuilder ssb = new SpannableStringBuilder();
                        ssb.append(getProofNarrative(proofType)).append(" ");

                        int i = 0;
                        while (i < proofsFor.length - 1) {
                            appendProofLinks(ssb, fingerprint, proofsFor[i]);
                            ssb.append(", ");
                            i++;
                        }
                        appendProofLinks(ssb, fingerprint, proofsFor[i]);
                        proofList.add(ssb);
                    }
                }

            } catch (KeybaseException ignored) {
            }

            return new ResultPage(getString(R.string.key_trust_results_prefix), proofList);
        }

        private SpannableStringBuilder appendProofLinks(SpannableStringBuilder ssb, final String fingerprint, final
        Proof proof) throws KeybaseException {
            int startAt = ssb.length();
            String handle = proof.getHandle();
            ssb.append(handle);
            ssb.setSpan(new URLSpan(proof.getServiceUrl()), startAt, startAt + handle.length(), Spanned
                    .SPAN_EXCLUSIVE_EXCLUSIVE);
            if (haveProofFor(proof.getType())) {
                ssb.append("\u00a0[");
                startAt = ssb.length();
                String verify = getString(R.string.keybase_verify);
                ssb.append(verify);
                ClickableSpan clicker = new ClickableSpan() {
                    @Override
                    public void onClick(View view) {
                        final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(getActivity())
                                .getProxyPrefs();

                        Runnable ignoreTor = new Runnable() {
                            @Override
                            public void run() {
                                mStartSearch.setEnabled(false);
                                verify(proof, fingerprint, new ParcelableProxy(null, -1, null));
                            }
                        };

                        if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                                getActivity())) {
                            mStartSearch.setEnabled(false);
                            verify(proof, fingerprint, mParcelableProxy);
                        }
                    }
                };
                ssb.setSpan(clicker, startAt, startAt + verify.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                ssb.append("]");
            }
            return ssb;
        }

        @Override
        protected void onPostExecute(ResultPage result) {
            super.onPostExecute(result);
            if (result.mProofs.isEmpty()) {
                result.mHeader = getActivity().getString(R.string.key_trust_no_cloud_evidence);
            }

            mStartSearch.setVisibility(View.GONE);
            mReportHeader.setVisibility(View.VISIBLE);
            mProofListing.setVisibility(View.VISIBLE);
            mReportHeader.setText(result.mHeader);

            int rowNumber = 1;
            for (CharSequence s : result.mProofs) {
                TableRow row = (TableRow) mInflater.inflate(R.layout.view_key_adv_keybase_proof, null);
                TextView number = (TextView) row.findViewById(R.id.proof_number);
                TextView text = (TextView) row.findViewById(R.id.proof_text);
                number.setText(Integer.toString(rowNumber++) + ". ");
                text.setText(s);
                text.setMovementMethod(LinkMovementMethod.getInstance());
                mProofListing.addView(row);
            }

            // mSearchReport.loadDataWithBaseURL("file:///android_res/drawable/", s, "text/html", "UTF-8", null);
        }
    }

    private String getProofNarrative(int proofType) {
        int stringIndex;
        switch (proofType) {
            case Proof.PROOF_TYPE_TWITTER:
                stringIndex = R.string.keybase_narrative_twitter;
                break;
            case Proof.PROOF_TYPE_GITHUB:
                stringIndex = R.string.keybase_narrative_github;
                break;
            case Proof.PROOF_TYPE_DNS:
                stringIndex = R.string.keybase_narrative_dns;
                break;
            case Proof.PROOF_TYPE_WEB_SITE:
                stringIndex = R.string.keybase_narrative_web_site;
                break;
            case Proof.PROOF_TYPE_HACKERNEWS:
                stringIndex = R.string.keybase_narrative_hackernews;
                break;
            case Proof.PROOF_TYPE_COINBASE:
                stringIndex = R.string.keybase_narrative_coinbase;
                break;
            case Proof.PROOF_TYPE_REDDIT:
                stringIndex = R.string.keybase_narrative_reddit;
                break;
            default:
                stringIndex = R.string.keybase_narrative_unknown;
        }
        return getActivity().getString(stringIndex);
    }

    private void appendIfOK(Hashtable<Integer, ArrayList<Proof>> table, Integer proofType, Proof proof) throws
            KeybaseException {
        ArrayList<Proof> list = table.get(proofType);
        if (list == null) {
            list = new ArrayList<Proof>();
            table.put(proofType, list);
        }
        list.add(proof);
    }

    // which proofs do we have working verifiers for?
    private boolean haveProofFor(int proofType) {
        switch (proofType) {
            case Proof.PROOF_TYPE_TWITTER:
                return true;
            case Proof.PROOF_TYPE_GITHUB:
                return true;
            case Proof.PROOF_TYPE_DNS:
                return true;
            case Proof.PROOF_TYPE_WEB_SITE:
                return true;
            case Proof.PROOF_TYPE_HACKERNEWS:
                return true;
            case Proof.PROOF_TYPE_COINBASE:
                return true;
            case Proof.PROOF_TYPE_REDDIT:
                return true;
            default:
                return false;
        }
    }

    private void verify(final Proof proof, final String fingerprint, ParcelableProxy parcelableProxy) {
        Intent intent = new Intent(getActivity(), KeychainService.class);
        Bundle data = new Bundle();
        intent.setAction(KeychainService.ACTION_VERIFY_KEYBASE_PROOF);

        data.putString(KeychainService.KEYBASE_PROOF, proof.toString());
        data.putString(KeychainService.KEYBASE_REQUIRED_FINGERPRINT, fingerprint);

        data.putParcelable(KeychainService.EXTRA_PARCELABLE_PROXY, parcelableProxy);

        intent.putExtra(KeychainService.EXTRA_DATA, data);

        mProofVerifyDetail.setVisibility(View.GONE);

        // Create a new Messenger for the communication back after proof work is done
        ServiceProgressHandler handler = new ServiceProgressHandler(getActivity()) {
            @Override
            public void handleMessage(Message message) {
                // handle messages by standard KeychainIntentServiceHandler first
                super.handleMessage(message);

                if (message.arg1 == MessageStatus.OKAY.ordinal()) {
                    Bundle returnData = message.getData();
                    String msg = returnData.getString(ServiceProgressHandler.DATA_MESSAGE);
                    SpannableStringBuilder ssb = new SpannableStringBuilder();

                    if ((msg != null) && msg.equals("OK")) {

                        //yay
                        String proofUrl = returnData.getString(ServiceProgressHandler.KEYBASE_PROOF_URL);
                        String presenceUrl = returnData.getString(ServiceProgressHandler.KEYBASE_PRESENCE_URL);
                        String presenceLabel = returnData.getString(ServiceProgressHandler.KEYBASE_PRESENCE_LABEL);

                        String proofLabel;
                        switch (proof.getType()) {
                            case Proof.PROOF_TYPE_TWITTER:
                                proofLabel = getString(R.string.keybase_twitter_proof);
                                break;
                            case Proof.PROOF_TYPE_DNS:
                                proofLabel = getString(R.string.keybase_dns_proof);
                                break;
                            case Proof.PROOF_TYPE_WEB_SITE:
                                proofLabel = getString(R.string.keybase_web_site_proof);
                                break;
                            case Proof.PROOF_TYPE_GITHUB:
                                proofLabel = getString(R.string.keybase_github_proof);
                                break;
                            case Proof.PROOF_TYPE_REDDIT:
                                proofLabel = getString(R.string.keybase_reddit_proof);
                                break;
                            default:
                                proofLabel = getString(R.string.keybase_a_post);
                                break;
                        }

                        ssb.append(getString(R.string.keybase_proof_succeeded));
                        StyleSpan bold = new StyleSpan(Typeface.BOLD);
                        ssb.setSpan(bold, 0, ssb.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                        ssb.append("\n\n");
                        int length = ssb.length();
                        ssb.append(proofLabel);
                        if (proofUrl != null) {
                            URLSpan postLink = new URLSpan(proofUrl);
                            ssb.setSpan(postLink, length, length + proofLabel.length(), Spanned
                                    .SPAN_EXCLUSIVE_EXCLUSIVE);
                        }
                        if (Proof.PROOF_TYPE_DNS == proof.getType()) {
                            ssb.append(" ").append(getString(R.string.keybase_for_the_domain)).append(" ");
                        } else {
                            ssb.append(" ").append(getString(R.string.keybase_fetched_from)).append(" ");
                        }
                        length = ssb.length();
                        URLSpan presenceLink = new URLSpan(presenceUrl);
                        ssb.append(presenceLabel);
                        ssb.setSpan(presenceLink, length, length + presenceLabel.length(), Spanned
                                .SPAN_EXCLUSIVE_EXCLUSIVE);
                        if (Proof.PROOF_TYPE_REDDIT == proof.getType()) {
                            ssb.append(", ").
                                    append(getString(R.string.keybase_reddit_attribution)).
                                    append(" “").append(proof.getHandle()).append("”, ");
                        }
                        ssb.append(" ").append(getString(R.string.keybase_contained_signature));
                    } else {
                        // verification failed!
                        msg = returnData.getString(ServiceProgressHandler.DATA_ERROR);
                        ssb.append(getString(R.string.keybase_proof_failure));
                        if (msg == null) {
                            msg = getString(R.string.keybase_unknown_proof_failure);
                        }
                        StyleSpan bold = new StyleSpan(Typeface.BOLD);
                        ssb.setSpan(bold, 0, ssb.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                        ssb.append("\n\n").append(msg);
                    }
                    mProofVerifyHeader.setVisibility(View.VISIBLE);
                    mProofVerifyDetail.setVisibility(View.VISIBLE);
                    mProofVerifyDetail.setMovementMethod(LinkMovementMethod.getInstance());
                    mProofVerifyDetail.setText(ssb);
                }
            }
        };

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(handler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        // show progress dialog
        handler.showProgressDialog(
                getString(R.string.progress_verifying_signature),
                ProgressDialog.STYLE_HORIZONTAL, false
        );

        // start service with intent
        getActivity().startService(intent);
    }
}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/dialog/AddKeyserverDialogFragment.java
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

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.app.ProgressDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.os.RemoteException;
import android.support.v4.app.DialogFragment;
import android.view.KeyEvent;
import android.view.LayoutInflater;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.TextView.OnEditorActionListener;

import com.squareup.okhttp.OkHttpClient;
import com.squareup.okhttp.Request;
import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.keyimport.HkpKeyserver;
import org.sufficientlysecure.keychain.util.Log;
import org.sufficientlysecure.keychain.util.Preferences;
import org.sufficientlysecure.keychain.util.TlsHelper;
import org.sufficientlysecure.keychain.util.orbot.OrbotHelper;

import java.io.IOException;
import java.net.MalformedURLException;
import java.net.Proxy;
import java.net.URI;
import java.net.URISyntaxException;

public class AddKeyserverDialogFragment extends DialogFragment implements OnEditorActionListener {
    private static final String ARG_MESSENGER = "messenger";

    public static final int MESSAGE_OKAY = 1;
    public static final int MESSAGE_VERIFICATION_FAILED = 2;

    public static final String MESSAGE_KEYSERVER = "new_keyserver";
    public static final String MESSAGE_VERIFIED = "verified";
    public static final String MESSAGE_FAILURE_REASON = "failure_reason";

    private Messenger mMessenger;
    private EditText mKeyserverEditText;
    private CheckBox mVerifyKeyserverCheckBox;

    public static enum FailureReason {
        INVALID_URL,
        CONNECTION_FAILED
    }

    ;

    /**
     * Creates new instance of this dialog fragment
     *
     * @param messenger to communicate back after setting the passphrase
     * @return
     */
    public static AddKeyserverDialogFragment newInstance(Messenger messenger) {
        AddKeyserverDialogFragment frag = new AddKeyserverDialogFragment();
        Bundle args = new Bundle();
        args.putParcelable(ARG_MESSENGER, messenger);

        frag.setArguments(args);

        return frag;
    }

    /**
     * Creates dialog
     */
    @Override
    public Dialog onCreateDialog(Bundle savedInstanceState) {
        final Activity activity = getActivity();

        mMessenger = getArguments().getParcelable(ARG_MESSENGER);

        CustomAlertDialogBuilder alert = new CustomAlertDialogBuilder(activity);

        alert.setTitle(R.string.add_keyserver_dialog_title);

        LayoutInflater inflater = activity.getLayoutInflater();
        View view = inflater.inflate(R.layout.add_keyserver_dialog, null);
        alert.setView(view);

        mKeyserverEditText = (EditText) view.findViewById(R.id.keyserver_url_edit_text);
        mVerifyKeyserverCheckBox = (CheckBox) view.findViewById(R.id.verify_keyserver_checkbox);

        // we don't want dialog to be dismissed on click, thereby requiring the hack seen below
        // and in onStart
        alert.setPositiveButton(android.R.string.ok, new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int id) {
                // we need to have an empty listener to prevent errors on some devices as mentioned
                // at http://stackoverflow.com/q/13746412/3000919
                // actual listener set in onStart
            }
        });

        alert.setNegativeButton(android.R.string.cancel, new DialogInterface.OnClickListener() {

            @Override
            public void onClick(DialogInterface dialog, int id) {
                dismiss();
            }
        });

        // Hack to open keyboard.
        // This is the only method that I found to work across all Android versions
        // http://turbomanage.wordpress.com/2012/05/02/show-soft-keyboard-automatically-when-edittext-receives-focus/
        // Notes: * onCreateView can't be used because we want to add buttons to the dialog
        //        * opening in onActivityCreated does not work on Android 4.4
        mKeyserverEditText.setOnFocusChangeListener(new View.OnFocusChangeListener() {
            @Override
            public void onFocusChange(View v, boolean hasFocus) {
                mKeyserverEditText.post(new Runnable() {
                    @Override
                    public void run() {
                        InputMethodManager imm = (InputMethodManager) getActivity()
                                .getSystemService(Context.INPUT_METHOD_SERVICE);
                        imm.showSoftInput(mKeyserverEditText, InputMethodManager.SHOW_IMPLICIT);
                    }
                });
            }
        });
        mKeyserverEditText.requestFocus();

        mKeyserverEditText.setImeActionLabel(getString(android.R.string.ok),
                EditorInfo.IME_ACTION_DONE);
        mKeyserverEditText.setOnEditorActionListener(this);

        return alert.show();
    }

    @Override
    public void onStart() {
        super.onStart();
        AlertDialog addKeyserverDialog = (AlertDialog) getDialog();
        if (addKeyserverDialog != null) {
            Button positiveButton = addKeyserverDialog.getButton(Dialog.BUTTON_POSITIVE);
            positiveButton.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    final String keyserverUrl = mKeyserverEditText.getText().toString();
                    if (mVerifyKeyserverCheckBox.isChecked()) {
                        final Preferences.ProxyPrefs proxyPrefs = Preferences.getPreferences(getActivity())
                                .getProxyPrefs();
                        Runnable ignoreTor = new Runnable() {
                            @Override
                            public void run() {
                                verifyConnection(keyserverUrl, null);
                            }
                        };

                        if (OrbotHelper.isOrbotInRequiredState(R.string.orbot_ignore_tor, ignoreTor, proxyPrefs,
                                getActivity())) {
                            verifyConnection(keyserverUrl, proxyPrefs.parcelableProxy.getProxy());
                        }
                    } else {
                        dismiss();
                        // return unverified keyserver back to activity
                        addKeyserver(keyserverUrl, false);
                    }
                }
            });
        }
    }

    public void addKeyserver(String keyserver, boolean verified) {
        dismiss();
        Bundle data = new Bundle();
        data.putString(MESSAGE_KEYSERVER, keyserver);
        data.putBoolean(MESSAGE_VERIFIED, verified);

        sendMessageToHandler(MESSAGE_OKAY, data);
    }

    public void verificationFailed(FailureReason reason) {
        Bundle data = new Bundle();
        data.putSerializable(MESSAGE_FAILURE_REASON, reason);

        sendMessageToHandler(MESSAGE_VERIFICATION_FAILED, data);
    }

    public void verifyConnection(String keyserver, final Proxy proxy) {

        new AsyncTask<String, Void, FailureReason>() {
            ProgressDialog mProgressDialog;
            String mKeyserver;

            @Override
            protected void onPreExecute() {
                mProgressDialog = new ProgressDialog(getActivity());
                mProgressDialog.setMessage(getString(R.string.progress_verifying_keyserver_url));
                mProgressDialog.setCancelable(false);
                mProgressDialog.show();
            }

            @Override
            protected FailureReason doInBackground(String... keyservers) {
                mKeyserver = keyservers[0];
                FailureReason reason = null;
                try {
                    // replace hkps/hkp scheme and reconstruct Uri
                    Uri keyserverUri = Uri.parse(mKeyserver);
                    String scheme = keyserverUri.getScheme();
                    String schemeSpecificPart = keyserverUri.getSchemeSpecificPart();
                    String fragment = keyserverUri.getFragment();
                    if (scheme == null) throw new MalformedURLException();
                    if (scheme.equalsIgnoreCase("hkps")) scheme = "https";
                    else if (scheme.equalsIgnoreCase("hkp")) scheme = "http";
                    URI newKeyserver = new URI(scheme, schemeSpecificPart, fragment);

                    Log.d("Converted URL", newKeyserver.toString());

                    OkHttpClient client = HkpKeyserver.getClient(newKeyserver.toURL(), proxy);
                    TlsHelper.pinCertificateIfNecessary(client, newKeyserver.toURL());
                    client.newCall(new Request.Builder().url(newKeyserver.toURL()).build()).execute();
                } catch (TlsHelper.TlsHelperException e) {
                    reason = FailureReason.CONNECTION_FAILED;
                } catch (MalformedURLException e) {
                    Log.w(Constants.TAG, "Invalid keyserver URL entered by user.");
                    reason = FailureReason.INVALID_URL;
                } catch (URISyntaxException e) {
                    Log.w(Constants.TAG, "Invalid keyserver URL entered by user.");
                    reason = FailureReason.INVALID_URL;
                } catch (IOException e) {
                    Log.w(Constants.TAG, "Could not connect to entered keyserver url");
                    reason = FailureReason.CONNECTION_FAILED;
                }
                return reason;
            }

            @Override
            protected void onPostExecute(FailureReason failureReason) {
                mProgressDialog.dismiss();
                if (failureReason == null) {
                    addKeyserver(mKeyserver, true);
                } else {
                    verificationFailed(failureReason);
                }
            }
        }.execute(keyserver);
    }

    @Override
    public void onDismiss(DialogInterface dialog) {
        super.onDismiss(dialog);

        // hide keyboard on dismiss
        hideKeyboard();
    }

    private void hideKeyboard() {
        if (getActivity() == null) {
            return;
        }
        InputMethodManager inputManager = (InputMethodManager) getActivity()
                .getSystemService(Context.INPUT_METHOD_SERVICE);

        //check if no view has focus:
        View v = getActivity().getCurrentFocus();
        if (v == null)
            return;

        inputManager.hideSoftInputFromWindow(v.getWindowToken(), 0);
    }

    /**
     * Associate the "done" button on the soft keyboard with the okay button in the view
     */
    @Override
    public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
        if (EditorInfo.IME_ACTION_DONE == actionId) {
            AlertDialog dialog = ((AlertDialog) getDialog());
            Button bt = dialog.getButton(AlertDialog.BUTTON_POSITIVE);

            bt.performClick();
            return true;
        }
        return false;
    }

    /**
     * Send message back to handler which is initialized in a activity
     *
     * @param what Message integer you want to send
     */
    private void sendMessageToHandler(Integer what, Bundle data) {
        Message msg = Message.obtain();
        msg.what = what;
        if (data != null) {
            msg.setData(data);
        }

        try {
            mMessenger.send(msg);
        } catch (RemoteException e) {
            Log.w(Constants.TAG, "Exception sending message, Is handler present?", e);
        } catch (NullPointerException e) {
            Log.w(Constants.TAG, "Messenger is null!", e);
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
