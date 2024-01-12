Refactoring Types: ['Extract Method']
/sufficientlysecure/keychain/ui/DecryptFilesActivity.java
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

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.Toast;

import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.intents.OpenKeychainIntents;
import org.sufficientlysecure.keychain.ui.base.BaseActivity;


public class DecryptFilesActivity extends BaseActivity {

    /* Intents */
    public static final String ACTION_DECRYPT_DATA = OpenKeychainIntents.DECRYPT_DATA;

    // intern
    public static final String ACTION_DECRYPT_DATA_OPEN = Constants.INTENT_PREFIX + "DECRYPT_DATA_OPEN";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setFullScreenDialogClose(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                setResult(Activity.RESULT_CANCELED);
                finish();
            }
        }, false);

        // Handle intent actions
        handleActions(savedInstanceState, getIntent());
    }

    @Override
    protected void initLayout() {
        setContentView(R.layout.decrypt_files_activity);
    }

    /**
     * Handles all actions with this intent
     */
    private void handleActions(Bundle savedInstanceState, Intent intent) {
        String action = intent.getAction();
        String type = intent.getType();
        Uri uri = intent.getData();

        if (Intent.ACTION_SEND.equals(action) && type != null) {
            // When sending to Keychain Decrypt via share menu
            // Binary via content provider (could also be files)
            // override uri to get stream from send
            uri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
            action = ACTION_DECRYPT_DATA;
        } else if (Intent.ACTION_VIEW.equals(action)) {
            // Android's Action when opening file associated to Keychain (see AndroidManifest.xml)

            // override action
            action = ACTION_DECRYPT_DATA;
        }

        // No need to initialize fragments if we are being restored
        if (savedInstanceState != null) {
            return;
        }

        // Definitely need a data uri with the decrypt_data intent
        if (ACTION_DECRYPT_DATA.equals(action) && uri == null) {
            Toast.makeText(this, "No data to decrypt!", Toast.LENGTH_LONG).show();
            setResult(Activity.RESULT_CANCELED);
            finish();
        }

        boolean showOpenDialog = ACTION_DECRYPT_DATA_OPEN.equals(action);
        DecryptFilesInputFragment frag = DecryptFilesInputFragment.newInstance(uri, showOpenDialog);

        // Add the fragment to the 'fragment_container' FrameLayout
        // NOTE: We use commitAllowingStateLoss() to prevent weird crashes!
        getSupportFragmentManager().beginTransaction()
                .replace(R.id.decrypt_files_fragment_container, frag)
                .commit();

    }

    public void displayListFragment(Uri inputUri) {

        ArrayList<Uri> uris = new ArrayList<>();
        uris.add(inputUri);
        DecryptFilesListFragment frag = DecryptFilesListFragment.newInstance(uris);

        getSupportFragmentManager().beginTransaction()
                .replace(R.id.decrypt_files_fragment_container, frag)
                .addToBackStack("list")
                .commit();

    }

}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/DecryptFilesInputFragment.java
/*
 * Copyright (C) 2014 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2015 Vincent Breitmoser <look@my.amazin.horse>
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
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.ui.util.Notify;
import org.sufficientlysecure.keychain.util.FileHelper;

public class DecryptFilesInputFragment extends Fragment {
    public static final String ARG_URI = "uri";
    public static final String ARG_OPEN_DIRECTLY = "open_directly";

    private static final int REQUEST_CODE_INPUT = 0x00007003;

    private TextView mFilename;
    private View mDecryptButton;

    private Uri mInputUri = null;

    public static DecryptFilesInputFragment newInstance(Uri uri, boolean openDirectly) {
        DecryptFilesInputFragment frag = new DecryptFilesInputFragment();

        Bundle args = new Bundle();
        args.putParcelable(ARG_URI, uri);
        args.putBoolean(ARG_OPEN_DIRECTLY, openDirectly);

        frag.setArguments(args);

        return frag;
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.decrypt_files_input_fragment, container, false);

        // hide result view for this fragment
        getActivity().findViewById(R.id.result_main_layout).setVisibility(View.GONE);

        mFilename = (TextView) view.findViewById(R.id.decrypt_files_filename);
        mDecryptButton = view.findViewById(R.id.decrypt_files_action_decrypt);
        view.findViewById(R.id.decrypt_files_browse).setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                    FileHelper.openDocument(DecryptFilesInputFragment.this, "*/*", REQUEST_CODE_INPUT);
                } else {
                    FileHelper.openFile(DecryptFilesInputFragment.this, mInputUri, "*/*",
                            REQUEST_CODE_INPUT);
                }
            }
        });
        mDecryptButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                decryptAction();
            }
        });

        return view;
    }

    @Override
    public void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);

        outState.putParcelable(ARG_URI, mInputUri);
    }

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);

        Bundle state = savedInstanceState != null ? savedInstanceState : getArguments();
        setInputUri(state.<Uri>getParcelable(ARG_URI));

        // should only come from args
        if (state.getBoolean(ARG_OPEN_DIRECTLY, false)) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                FileHelper.openDocument(DecryptFilesInputFragment.this, "*/*", REQUEST_CODE_INPUT);
            } else {
                FileHelper.openFile(DecryptFilesInputFragment.this, mInputUri, "*/*", REQUEST_CODE_INPUT);
            }
        }
    }

    private void setInputUri(Uri inputUri) {
        if (inputUri == null) {
            mInputUri = null;
            mFilename.setText("");
            return;
        }

        mInputUri = inputUri;
        mFilename.setText(FileHelper.getFilename(getActivity(), mInputUri));
    }

    private void decryptAction() {
        if (mInputUri == null) {
            Notify.create(getActivity(), R.string.no_file_selected, Notify.Style.ERROR).show();
            return;
        }

        DecryptFilesActivity activity = (DecryptFilesActivity) getActivity();
        activity.displayListFragment(mInputUri);
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode != REQUEST_CODE_INPUT) {
            return;
        }

        if (resultCode == Activity.RESULT_OK && data != null) {
            setInputUri(data.getData());
        }
    }

}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/DecryptFilesListFragment.java
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


import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ResolveInfo;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.support.v7.widget.DefaultItemAnimator;
import android.support.v7.widget.LinearLayoutManager;
import android.support.v7.widget.RecyclerView;
import android.view.ContextMenu;
import android.view.ContextMenu.ContextMenuInfo;
import android.view.LayoutInflater;
import android.view.MenuItem;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.PopupMenu;
import android.widget.PopupMenu.OnDismissListener;
import android.widget.PopupMenu.OnMenuItemClickListener;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.ViewAnimator;

import org.openintents.openpgp.OpenPgpMetadata;
import org.openintents.openpgp.OpenPgpSignatureResult;
import org.sufficientlysecure.keychain.Constants;
import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.operations.results.DecryptVerifyResult;
import org.sufficientlysecure.keychain.pgp.PgpDecryptVerifyInputParcel;
import org.sufficientlysecure.keychain.provider.KeychainContract.KeyRings;
import org.sufficientlysecure.keychain.provider.TemporaryStorageProvider;
// this import NEEDS to be above the ViewModel one, or it won't compile! (as of 06/06/15)
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils.StatusHolder;
import org.sufficientlysecure.keychain.ui.DecryptFilesListFragment.DecryptFilesAdapter.ViewModel;
import org.sufficientlysecure.keychain.ui.adapter.SpacesItemDecoration;
import org.sufficientlysecure.keychain.ui.base.CryptoOperationFragment;
import org.sufficientlysecure.keychain.ui.util.FormattingUtils;
import org.sufficientlysecure.keychain.ui.util.KeyFormattingUtils;
import org.sufficientlysecure.keychain.ui.util.Notify;
import org.sufficientlysecure.keychain.ui.util.Notify.Style;
import org.sufficientlysecure.keychain.util.FileHelper;
import org.sufficientlysecure.keychain.util.Log;

public class DecryptFilesListFragment
        extends CryptoOperationFragment<PgpDecryptVerifyInputParcel,DecryptVerifyResult>
        implements OnMenuItemClickListener {
    public static final String ARG_URIS = "uris";

    private static final int REQUEST_CODE_OUTPUT = 0x00007007;

    private ArrayList<Uri> mInputUris;
    private HashMap<Uri, Uri> mOutputUris;
    private ArrayList<Uri> mPendingInputUris;

    private Uri mCurrentInputUri;

    private DecryptFilesAdapter mAdapter;

    /**
     * Creates new instance of this fragment
     */
    public static DecryptFilesListFragment newInstance(ArrayList<Uri> uris) {
        DecryptFilesListFragment frag = new DecryptFilesListFragment();

        Bundle args = new Bundle();
        args.putParcelableArrayList(ARG_URIS, uris);
        frag.setArguments(args);

        return frag;
    }

    /**
     * Inflate the layout for this fragment
     */
    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.decrypt_files_list_fragment, container, false);

        RecyclerView vFilesList = (RecyclerView) view.findViewById(R.id.decrypted_files_list);

        vFilesList.addItemDecoration(new SpacesItemDecoration(
                FormattingUtils.dpToPx(getActivity(), 4)));
        vFilesList.setHasFixedSize(true);
        vFilesList.setLayoutManager(new LinearLayoutManager(getActivity()));
        vFilesList.setItemAnimator(new DefaultItemAnimator());

        mAdapter = new DecryptFilesAdapter(getActivity(), this);
        vFilesList.setAdapter(mAdapter);

        return view;
    }

    @Override
    public void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);

        outState.putParcelableArrayList(ARG_URIS, mInputUris);
    }

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);

        displayInputUris(getArguments().<Uri>getParcelableArrayList(ARG_URIS));
    }

    private String removeEncryptedAppend(String name) {
        if (name.endsWith(Constants.FILE_EXTENSION_ASC)
                || name.endsWith(Constants.FILE_EXTENSION_PGP_MAIN)
                || name.endsWith(Constants.FILE_EXTENSION_PGP_ALTERNATE)) {
            return name.substring(0, name.length() - 4);
        }
        return name;
    }

    private void askForOutputFilename(Uri inputUri, String originalFilename, String mimeType) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.KITKAT) {
            File file = new File(inputUri.getPath());
            File parentDir = file.exists() ? file.getParentFile() : Constants.Path.APP_DIR;
            File targetFile = new File(parentDir, originalFilename);
            FileHelper.saveFile(this, getString(R.string.title_decrypt_to_file),
                    getString(R.string.specify_file_to_decrypt_to), targetFile, REQUEST_CODE_OUTPUT);
        } else {
            FileHelper.saveDocument(this, mimeType, originalFilename, REQUEST_CODE_OUTPUT);
        }
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        switch (requestCode) {
            case REQUEST_CODE_OUTPUT: {
                // This happens after output file was selected, so start our operation
                if (resultCode == Activity.RESULT_OK && data != null) {
                    Uri saveUri = data.getData();
                    Uri outputUri = mOutputUris.get(mCurrentInputUri);
                    // TODO save from outputUri to saveUri

                    mCurrentInputUri = null;
                }
                return;
            }

            default: {
                super.onActivityResult(requestCode, resultCode, data);
            }
        }
    }

    private void displayInputUris(ArrayList<Uri> uris) {
        mInputUris = uris;
        mOutputUris = new HashMap<>(uris.size());
        for (Uri uri : uris) {
            mAdapter.add(uri);
            mOutputUris.put(uri, TemporaryStorageProvider.createFile(getActivity()));
        }

        mPendingInputUris = uris;

        cryptoOperation();
    }

    @Override
    protected boolean onCryptoSetProgress(String msg, int progress, int max) {
        mAdapter.setProgress(mCurrentInputUri, progress, max, msg);
        return true;
    }

    @Override
    protected void dismissProgress() {
        // progress shown inline, so never mind
    }

    @Override
    protected void onCryptoOperationError(DecryptVerifyResult result) {
        final Uri uri = mCurrentInputUri;
        mCurrentInputUri = null;

        mAdapter.addResult(uri, result, null, null, null);
    }

    @Override
    protected void onCryptoOperationSuccess(DecryptVerifyResult result) {
        final Uri uri = mCurrentInputUri;
        mCurrentInputUri = null;

        Drawable icon = null;
        OnClickListener onFileClick = null, onKeyClick = null;

        if (result.getDecryptMetadata() != null && result.getDecryptMetadata().getMimeType() != null) {
            icon = loadIcon(result.getDecryptMetadata().getMimeType());
        }

        OpenPgpSignatureResult sigResult = result.getSignatureResult();
        if (sigResult != null) {
            final long keyId = sigResult.getKeyId();
            if (sigResult.getStatus() != OpenPgpSignatureResult.SIGNATURE_KEY_MISSING) {
                onKeyClick = new OnClickListener() {
                    @Override
                    public void onClick(View view) {
                        Activity activity = getActivity();
                        if (activity == null) {
                            return;
                        }
                        Intent intent = new Intent(activity, ViewKeyActivity.class);
                        intent.setData(KeyRings.buildUnifiedKeyRingUri(keyId));
                        activity.startActivity(intent);
                    }
                };
            }
        }

        if (result.success() && result.getDecryptMetadata() != null) {
            final OpenPgpMetadata metadata = result.getDecryptMetadata();
            onFileClick = new OnClickListener() {
                @Override
                public void onClick(View view) {
                    Activity activity = getActivity();
                    if (activity == null || mCurrentInputUri != null) {
                        return;
                    }

                    Uri outputUri = mOutputUris.get(uri);
                    Intent intent = new Intent();
                    intent.setDataAndType(outputUri, metadata.getMimeType());
                    activity.startActivity(intent);
                }
            };
        }

        mAdapter.addResult(uri, result, icon, onFileClick, onKeyClick);

    }

    @Override
    protected PgpDecryptVerifyInputParcel createOperationInput() {

        if (mCurrentInputUri == null) {
            if (mPendingInputUris.isEmpty()) {
                // nothing left to do
                return null;
            }

            mCurrentInputUri = mPendingInputUris.remove(0);
        }

        Uri currentOutputUri = mOutputUris.get(mCurrentInputUri);
        Log.d(Constants.TAG, "mInputUri=" + mCurrentInputUri + ", mOutputUri=" + currentOutputUri);

        return new PgpDecryptVerifyInputParcel(mCurrentInputUri, currentOutputUri)
                .setAllowSymmetricDecryption(true);

    }

    @Override
    public void onCreateContextMenu(ContextMenu menu, View v, ContextMenuInfo menuInfo) {
        super.onCreateContextMenu(menu, v, menuInfo);
    }

    @Override
    public boolean onMenuItemClick(MenuItem menuItem) {
        if (mAdapter.mMenuClickedModel == null || !mAdapter.mMenuClickedModel.hasResult()) {
            return false;
        }
        Activity activity = getActivity();
        if (activity == null) {
            return false;
        }

        ViewModel model = mAdapter.mMenuClickedModel;
        DecryptVerifyResult result = model.mResult;
        switch (menuItem.getItemId()) {
            case R.id.view_log:
                Intent intent = new Intent(activity, LogDisplayActivity.class);
                intent.putExtra(LogDisplayFragment.EXTRA_RESULT, result);
                activity.startActivity(intent);
                return true;
            case R.id.decrypt_save:
                OpenPgpMetadata metadata = result.getDecryptMetadata();
                if (metadata == null) {
                    return true;
                }
                mCurrentInputUri = model.mInputUri;
                askForOutputFilename(model.mInputUri, metadata.getFilename(), metadata.getMimeType());
                return true;
            case R.id.decrypt_delete:
                Notify.create(activity, "decrypt/delete not yet implemented", Style.ERROR).show(this);
                return true;
        }
        return false;
    }

    public static class DecryptFilesAdapter extends RecyclerView.Adapter<ViewHolder> {
        private Context mContext;
        private ArrayList<ViewModel> mDataset;
        private OnMenuItemClickListener mMenuItemClickListener;
        private ViewModel mMenuClickedModel;

        public class ViewModel {
            Context mContext;
            Uri mInputUri;
            DecryptVerifyResult mResult;
            Drawable mIcon;

            OnClickListener mOnFileClickListener;
            OnClickListener mOnKeyClickListener;

            int mProgress, mMax;
            String mProgressMsg;

            ViewModel(Context context, Uri uri) {
                mContext = context;
                mInputUri = uri;
                mProgress = 0;
                mMax = 100;
            }

            void addResult(DecryptVerifyResult result) {
                mResult = result;
            }

            void addIcon(Drawable icon) {
                mIcon = icon;
            }

            void setOnClickListeners(OnClickListener onFileClick, OnClickListener onKeyClick) {
                mOnFileClickListener = onFileClick;
                mOnKeyClickListener = onKeyClick;
            }

            boolean hasResult() {
                return mResult != null;
            }

            void setProgress(int progress, int max, String msg) {
                if (msg != null) {
                    mProgressMsg = msg;
                }
                mProgress = progress;
                mMax = max;
            }

            // Depends on inputUri only
            @Override
            public boolean equals(Object o) {
                if (this == o) return true;
                if (o == null || getClass() != o.getClass()) return false;
                ViewModel viewModel = (ViewModel) o;
                return !(mResult != null ? !mResult.equals(viewModel.mResult)
                        : viewModel.mResult != null);
            }

            // Depends on inputUri only
            @Override
            public int hashCode() {
                return mResult != null ? mResult.hashCode() : 0;
            }

            @Override
            public String toString() {
                return mResult.toString();
            }
        }

        // Provide a suitable constructor (depends on the kind of dataset)
        public DecryptFilesAdapter(Context context, OnMenuItemClickListener menuItemClickListener) {
            mContext = context;
            mMenuItemClickListener = menuItemClickListener;
            mDataset = new ArrayList<>();
        }

        // Create new views (invoked by the layout manager)
        @Override
        public ViewHolder onCreateViewHolder(ViewGroup parent, int viewType) {
            //inflate your layout and pass it to view holder
            View v = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.decrypt_list_entry, parent, false);
            return new ViewHolder(v);
        }

        // Replace the contents of a view (invoked by the layout manager)
        @Override
        public void onBindViewHolder(ViewHolder holder, final int position) {
            // - get element from your dataset at this position
            // - replace the contents of the view with that element
            final ViewModel model = mDataset.get(position);

            if (model.hasResult()) {
                if (holder.vAnimator.getDisplayedChild() != 1) {
                    holder.vAnimator.setDisplayedChild(1);
                }

                KeyFormattingUtils.setStatus(mContext, holder, model.mResult);

                OpenPgpMetadata metadata = model.mResult.getDecryptMetadata();
                holder.vFilename.setText(metadata.getFilename());

                long size = metadata.getOriginalSize();
                if (size == -1 || size == 0) {
                    holder.vFilesize.setText("");
                } else {
                    holder.vFilesize.setText(FileHelper.readableFileSize(size));
                }

                // TODO thumbnail from OpenPgpMetadata
                if (model.mIcon != null) {
                    holder.vThumbnail.setImageDrawable(model.mIcon);
                } else {
                    holder.vThumbnail.setImageResource(R.drawable.ic_doc_generic_am);
                }

                holder.vFile.setOnClickListener(model.mOnFileClickListener);
                holder.vSignatureLayout.setOnClickListener(model.mOnKeyClickListener);

                holder.vContextMenu.setTag(model);
                holder.vContextMenu.setOnClickListener(new OnClickListener() {
                    @Override
                    public void onClick(View view) {
                        mMenuClickedModel = model;
                        PopupMenu menu = new PopupMenu(mContext, view);
                        menu.inflate(R.menu.decrypt_item_context_menu);
                        menu.setOnMenuItemClickListener(mMenuItemClickListener);
                        menu.setOnDismissListener(new OnDismissListener() {
                            @Override
                            public void onDismiss(PopupMenu popupMenu) {
                                mMenuClickedModel = null;
                            }
                        });
                        menu.show();
                    }
                });

            } else {
                if (holder.vAnimator.getDisplayedChild() != 0) {
                    holder.vAnimator.setDisplayedChild(0);
                }

                holder.vProgress.setProgress(model.mProgress);
                holder.vProgress.setMax(model.mMax);
                holder.vProgressMsg.setText(model.mProgressMsg);
            }

        }

        // Return the size of your dataset (invoked by the layout manager)
        @Override
        public int getItemCount() {
            return mDataset.size();
        }

        public void add(Uri uri) {
            ViewModel newModel = new ViewModel(mContext, uri);
            mDataset.add(newModel);
            notifyItemInserted(mDataset.size());
        }

        public void setProgress(Uri uri, int progress, int max, String msg) {
            ViewModel newModel = new ViewModel(mContext, uri);
            int pos = mDataset.indexOf(newModel);
            mDataset.get(pos).setProgress(progress, max, msg);
            notifyItemChanged(pos);
        }

        public void addResult(Uri uri, DecryptVerifyResult result, Drawable icon,
                OnClickListener onFileClick, OnClickListener onKeyClick) {

            ViewModel model = new ViewModel(mContext, uri);
            int pos = mDataset.indexOf(model);
            model = mDataset.get(pos);

            model.addResult(result);
            if (icon != null) {
                model.addIcon(icon);
            }
            model.setOnClickListeners(onFileClick, onKeyClick);

            notifyItemChanged(pos);
        }

    }


    // Provide a reference to the views for each data item
    // Complex data items may need more than one view per item, and
    // you provide access to all the views for a data item in a view holder
    public static class ViewHolder extends RecyclerView.ViewHolder implements StatusHolder {
        public ViewAnimator vAnimator;

        public ProgressBar vProgress;
        public TextView vProgressMsg;

        public View vFile;
        public TextView vFilename;
        public TextView vFilesize;
        public ImageView vThumbnail;

        public ImageView vEncStatusIcon;
        public TextView vEncStatusText;

        public ImageView vSigStatusIcon;
        public TextView vSigStatusText;
        public View vSignatureLayout;
        public TextView vSignatureName;
        public TextView vSignatureMail;
        public TextView vSignatureAction;

        public View vContextMenu;

        public ViewHolder(View itemView) {
            super(itemView);

            vAnimator = (ViewAnimator) itemView.findViewById(R.id.view_animator);

            vProgress = (ProgressBar) itemView.findViewById(R.id.progress);
            vProgressMsg = (TextView) itemView.findViewById(R.id.progress_msg);

            vFile = itemView.findViewById(R.id.file);
            vFilename = (TextView) itemView.findViewById(R.id.filename);
            vFilesize = (TextView) itemView.findViewById(R.id.filesize);
            vThumbnail = (ImageView) itemView.findViewById(R.id.thumbnail);

            vEncStatusIcon = (ImageView) itemView.findViewById(R.id.result_encryption_icon);
            vEncStatusText = (TextView) itemView.findViewById(R.id.result_encryption_text);

            vSigStatusIcon = (ImageView) itemView.findViewById(R.id.result_signature_icon);
            vSigStatusText = (TextView) itemView.findViewById(R.id.result_signature_text);
            vSignatureLayout = itemView.findViewById(R.id.result_signature_layout);
            vSignatureName = (TextView) itemView.findViewById(R.id.result_signature_name);
            vSignatureMail= (TextView) itemView.findViewById(R.id.result_signature_email);
            vSignatureAction = (TextView) itemView.findViewById(R.id.result_signature_action);

            vContextMenu = itemView.findViewById(R.id.context_menu);

        }

        @Override
        public ImageView getEncryptionStatusIcon() {
            return vEncStatusIcon;
        }

        @Override
        public TextView getEncryptionStatusText() {
            return vEncStatusText;
        }

        @Override
        public ImageView getSignatureStatusIcon() {
            return vSigStatusIcon;
        }

        @Override
        public TextView getSignatureStatusText() {
            return vSigStatusText;
        }

        @Override
        public View getSignatureLayout() {
            return vSignatureLayout;
        }

        @Override
        public TextView getSignatureAction() {
            return vSignatureAction;
        }

        @Override
        public TextView getSignatureUserName() {
            return vSignatureName;
        }

        @Override
        public TextView getSignatureUserEmail() {
            return vSignatureMail;
        }

        @Override
        public boolean hasEncrypt() {
            return true;
        }
    }

    private Drawable loadIcon(String mimeType) {
        final Intent intent = new Intent(Intent.ACTION_VIEW);
        intent.setType(mimeType);

        final List<ResolveInfo> matches = getActivity()
                .getPackageManager().queryIntentActivities(intent, 0);
        //noinspection LoopStatementThatDoesntLoop
        for (ResolveInfo match : matches) {
            return match.loadIcon(getActivity().getPackageManager());
        }
        return null;

    }

}


File: OpenKeychain/src/main/java/org/sufficientlysecure/keychain/ui/base/CryptoOperationFragment.java
/*
 * Copyright (C) 2015 Dominik Schürmann <dominik@dominikschuermann.de>
 * Copyright (C) 2015 Vincent Breitmoser <v.breitmoser@mugenguild.com>
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

package org.sufficientlysecure.keychain.ui.base;

import android.app.Activity;
import android.app.ProgressDialog;
import android.content.Intent;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.os.Parcelable;
import android.support.v4.app.Fragment;

import org.sufficientlysecure.keychain.R;
import org.sufficientlysecure.keychain.operations.results.InputPendingResult;
import org.sufficientlysecure.keychain.operations.results.OperationResult;
import org.sufficientlysecure.keychain.service.KeychainNewService;
import org.sufficientlysecure.keychain.service.KeychainService;
import org.sufficientlysecure.keychain.service.ServiceProgressHandler;
import org.sufficientlysecure.keychain.service.input.CryptoInputParcel;
import org.sufficientlysecure.keychain.service.input.RequiredInputParcel;
import org.sufficientlysecure.keychain.ui.NfcOperationActivity;
import org.sufficientlysecure.keychain.ui.PassphraseDialogActivity;
import org.sufficientlysecure.keychain.ui.dialog.ProgressDialogFragment;


/**
 * All fragments executing crypto operations need to extend this class.
 */
public abstract class CryptoOperationFragment <T extends Parcelable, S extends OperationResult>
        extends Fragment {

    public static final int REQUEST_CODE_PASSPHRASE = 0x00008001;
    public static final int REQUEST_CODE_NFC = 0x00008002;

    private void initiateInputActivity(RequiredInputParcel requiredInput) {

        switch (requiredInput.mType) {
            case NFC_KEYTOCARD:
            case NFC_DECRYPT:
            case NFC_SIGN: {
                Intent intent = new Intent(getActivity(), NfcOperationActivity.class);
                intent.putExtra(NfcOperationActivity.EXTRA_REQUIRED_INPUT, requiredInput);
                startActivityForResult(intent, REQUEST_CODE_NFC);
                return;
            }

            case PASSPHRASE:
            case PASSPHRASE_SYMMETRIC: {
                Intent intent = new Intent(getActivity(), PassphraseDialogActivity.class);
                intent.putExtra(PassphraseDialogActivity.EXTRA_REQUIRED_INPUT, requiredInput);
                startActivityForResult(intent, REQUEST_CODE_PASSPHRASE);
                return;
            }
        }

        throw new RuntimeException("Unhandled pending result!");
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (resultCode == Activity.RESULT_CANCELED) {
            onCryptoOperationCancelled();
            return;
        }

        switch (requestCode) {
            case REQUEST_CODE_PASSPHRASE: {
                if (resultCode == Activity.RESULT_OK && data != null) {
                    CryptoInputParcel cryptoInput =
                            data.getParcelableExtra(PassphraseDialogActivity.RESULT_CRYPTO_INPUT);
                    cryptoOperation(cryptoInput);
                    return;
                }
                break;
            }

            case REQUEST_CODE_NFC: {
                if (resultCode == Activity.RESULT_OK && data != null) {
                    CryptoInputParcel cryptoInput =
                            data.getParcelableExtra(NfcOperationActivity.RESULT_DATA);
                    cryptoOperation(cryptoInput);
                    return;
                }
                break;
            }

            default: {
                super.onActivityResult(requestCode, resultCode, data);
            }
        }
    }

    protected void dismissProgress() {

        ProgressDialogFragment progressDialogFragment =
                (ProgressDialogFragment) getFragmentManager().findFragmentByTag("progressDialog");

        if (progressDialogFragment == null) {
            return;
        }

        progressDialogFragment.dismissAllowingStateLoss();

    }

    protected abstract T createOperationInput();

    protected void cryptoOperation(CryptoInputParcel cryptoInput) {

        T operationInput = createOperationInput();
        if (operationInput == null) {
            return;
        }

        // Send all information needed to service to edit key in other thread
        Intent intent = new Intent(getActivity(), KeychainNewService.class);

        intent.putExtra(KeychainNewService.EXTRA_OPERATION_INPUT, operationInput);
        intent.putExtra(KeychainNewService.EXTRA_CRYPTO_INPUT, cryptoInput);

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

                    final OperationResult result =
                            returnData.getParcelable(OperationResult.EXTRA_RESULT);

                    onHandleResult(result);
                }
            }

            @Override
            protected void onSetProgress(String msg, int progress, int max) {
                // allow handling of progress in fragment, or delegate upwards
                if ( ! onCryptoSetProgress(msg, progress, max)) {
                    super.onSetProgress(msg, progress, max);
                }
            }
        };

        // Create a new Messenger for the communication back
        Messenger messenger = new Messenger(saveHandler);
        intent.putExtra(KeychainService.EXTRA_MESSENGER, messenger);

        saveHandler.showProgressDialog(
                getString(R.string.progress_building_key),
                ProgressDialog.STYLE_HORIZONTAL, false);

        getActivity().startService(intent);

    }

    protected void cryptoOperation() {
        cryptoOperation(new CryptoInputParcel());
    }

    protected void onCryptoOperationResult(S result) {
        if (result.success()) {
            onCryptoOperationSuccess(result);
        } else {
            onCryptoOperationError(result);
        }
    }

    abstract protected void onCryptoOperationSuccess(S result);

    protected void onCryptoOperationError(S result) {
        result.createNotify(getActivity()).show();
    }

    protected void onCryptoOperationCancelled() {
    }

    public void onHandleResult(OperationResult result) {

        if (result instanceof InputPendingResult) {
            InputPendingResult pendingResult = (InputPendingResult) result;
            if (pendingResult.isPending()) {
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

    protected boolean onCryptoSetProgress(String msg, int progress, int max) {
        return false;
    }

}
