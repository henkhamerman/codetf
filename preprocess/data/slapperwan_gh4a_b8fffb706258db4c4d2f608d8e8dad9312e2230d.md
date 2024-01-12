Refactoring Types: ['Move Method', 'Extract Method', 'Move Attribute']
ullah
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.gh4a;

import java.util.Arrays;
import java.util.List;


/**
 * The Interface Constants.
 */
public interface Constants {
    public static final String LOG_TAG = "Gh4a";

    public interface Theme {
        public static final int DARK = 0;
        public static final int LIGHT = 1;
        public static final int LIGHTDARK = 2; /* backwards compat with old settings */
    }

    public interface User {
        public static final String LOGIN = "USER_LOGIN";
        public static final String NAME = "USER_NAME";
        public static final String TYPE_USER = "User";
        public static final String TYPE_ORG = "Organization";
        public static final String TYPE = "Type";
        public static final String AUTH_TOKEN = "Token";
    }

    public interface Repository {
        public static final String NAME = "REPO_NAME";
        public static final String OWNER = "REPO_OWNER";
        public static final String BASE = "BASE";
        public static final String HEAD = "HEAD";
        public static final String SELECTED_REF = "SELECTED_REF";
        public static final String TYPE = "REPO_TYPE";
    }

    public interface Issue {
        public static final String NUMBER = "ISSUE_NUMBER";
        public static final String STATE = "state";
        public static final String STATE_OPEN = "open";
        public static final String STATE_CLOSED = "closed";
    }

    public interface Commit {
        public static final String DIFF = "Commit.DIFF";
        public static final String COMMENTS = "Commit.COMMENTS";
    }

    public interface PullRequest {
        public static final String NUMBER = "PullRequest.NUMBER";
        public static final String STATE = "PullRequest.STATE";
    }

    public interface Object {
        public static final String PATH = "Object.PATH";
        public static final String OBJECT_SHA = "Object.SHA"; // SHA of the commit object
        public static final String REF = "Object.REF"; // SHA or branch/tag name of tree
    }

    public interface Gist {
        public static final String ID = "Gist.id";
        public static final String FILENAME = "Gist.filename";
    }

    public interface Blog {
        public static final String CONTENT = "Blog.content";
        public static final String TITLE = "Blog.title";
        public static final String LINK = "Blog.link";
    }

    public interface Comment {
        public static final String ID = "Comment.id";
        public static final String BODY = "Comment.body";
    }

    public interface Release {
        public static final String RELEASE = "Release.release";
        public static final String RELEASER = "Release.releaser";
    }

    public static final List<String> SKIP_PRETTIFY_EXT = Arrays.asList(
        "txt", "rdoc", "texttile", "org", "creole", "rst",
        "asciidoc", "pod", "");

    public static final List<String> MARKDOWN_EXT = Arrays.asList(
        "markdown", "md", "mdown", "mkdn", "mkd");
}

File: src/com/gh4a/activities/DiffViewerActivity.java
/*
 * Copyright 2011 Azwan Adli Abdullah
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.gh4a.activities;

import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.graphics.Point;
import android.net.Uri;
import android.os.Bundle;
import android.support.v4.content.Loader;
import android.support.v4.os.AsyncTaskCompat;
import android.support.v4.util.LongSparseArray;
import android.support.v4.view.MenuItemCompat;
import android.support.v7.app.ActionBar;
import android.support.v7.app.AlertDialog;
import android.support.v7.widget.ListPopupWindow;
import android.text.Html;
import android.text.TextUtils;
import android.util.SparseArray;
import android.view.LayoutInflater;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ListAdapter;
import android.widget.TextView;

import com.gh4a.Constants;
import com.gh4a.Gh4Application;
import com.gh4a.ProgressDialogTask;
import com.gh4a.R;
import com.gh4a.loader.LoaderCallbacks;
import com.gh4a.loader.LoaderResult;
import com.gh4a.utils.FileUtils;
import com.gh4a.utils.IntentUtils;
import com.gh4a.utils.StringUtils;
import com.gh4a.utils.ThemeUtils;
import com.gh4a.utils.ToastUtils;

import org.eclipse.egit.github.core.CommitComment;
import org.eclipse.egit.github.core.User;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public abstract class DiffViewerActivity extends WebViewerActivity implements
        View.OnTouchListener {
    protected String mRepoOwner;
    protected String mRepoName;
    protected String mPath;
    protected String mSha;

    private String mDiff;
    private String[] mDiffLines;
    private SparseArray<List<CommitComment>> mCommitCommentsByPos = new SparseArray<>();
    private LongSparseArray<CommitComment> mCommitComments = new LongSparseArray<>();

    private Point mLastTouchDown = new Point();

    private static final int MENU_ITEM_VIEW = 10;

    private LoaderCallbacks<List<CommitComment>> mCommentCallback =
            new LoaderCallbacks<List<CommitComment>>() {
        @Override
        public Loader<LoaderResult<List<CommitComment>>> onCreateLoader(int id, Bundle args) {
            return createCommentLoader();
        }

        @Override
        public void onResultReady(LoaderResult<List<CommitComment>> result) {
            if (result.handleError(DiffViewerActivity.this)) {
                setContentEmpty(true);
                setContentShown(true);
                return;
            }

            addCommentsToMap(result.getData());
            showDiff();
        }
    };

    @Override
    @SuppressWarnings("unchecked")
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        if (hasErrorView()) {
            return;
        }

        Bundle data = getIntent().getExtras();
        mRepoOwner = data.getString(Constants.Repository.OWNER);
        mRepoName = data.getString(Constants.Repository.NAME);
        mPath = data.getString(Constants.Object.PATH);
        mSha = data.getString(Constants.Object.OBJECT_SHA);
        mDiff = data.getString(Constants.Commit.DIFF);

        ActionBar actionBar = getSupportActionBar();
        actionBar.setTitle(FileUtils.getFileName(mPath));
        actionBar.setSubtitle(mRepoOwner + "/" + mRepoName);
        actionBar.setDisplayHomeAsUpEnabled(true);

        mWebView.setOnTouchListener(this);

        List<CommitComment> comments =
                (ArrayList<CommitComment>) data.getSerializable(Constants.Commit.COMMENTS);

        if (comments != null) {
            addCommentsToMap(comments);
            showDiff();
        } else {
            getSupportLoaderManager().initLoader(0, null, mCommentCallback);
        }
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuInflater inflater = getMenuInflater();
        inflater.inflate(R.menu.download_menu, menu);

        menu.removeItem(R.id.download);

        String viewAtTitle = getString(R.string.object_view_file_at, mSha.substring(0, 7));
        MenuItem item = menu.add(0, MENU_ITEM_VIEW, Menu.NONE, viewAtTitle);
        MenuItemCompat.setShowAsAction(item, MenuItemCompat.SHOW_AS_ACTION_NEVER);

        return super.onCreateOptionsMenu(menu);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        String url = "https://github.com/" + mRepoOwner + "/" + mRepoName + "/commit/" + mSha;

        switch (item.getItemId()) {
            case R.id.browser:
                IntentUtils.launchBrowser(this, Uri.parse(url));
                return true;
            case R.id.share:
                Intent shareIntent = new Intent(Intent.ACTION_SEND);
                shareIntent.setType("text/plain");
                shareIntent.putExtra(Intent.EXTRA_SUBJECT, getString(R.string.share_commit_subject,
                        mSha.substring(0, 7), mRepoOwner + "/" + mRepoName));
                shareIntent.putExtra(Intent.EXTRA_TEXT, url);
                shareIntent = Intent.createChooser(shareIntent, getString(R.string.share_title));
                startActivity(shareIntent);
                return true;
            case MENU_ITEM_VIEW:
                startActivity(IntentUtils.getFileViewerActivityIntent(this,
                        mRepoOwner, mRepoName, mSha, mPath));
                return true;
        }
        return super.onOptionsItemSelected(item);
    }

    private void addCommentsToMap(List<CommitComment> comments) {
        for (CommitComment comment : comments) {
            if (!TextUtils.equals(comment.getPath(), mPath)) {
                continue;
            }
            int position = comment.getPosition();
            List<CommitComment> commentsByPos = mCommitCommentsByPos.get(position);
            if (commentsByPos == null) {
                commentsByPos = new ArrayList<>();
                mCommitCommentsByPos.put(position, commentsByPos);
            }
            commentsByPos.add(comment);
        }
    }

    protected void showDiff() {
        StringBuilder content = new StringBuilder();
        boolean authorized = Gh4Application.get().isAuthorized();

        content.append("<html><head><title></title>");
        content.append("<link href='file:///android_asset/text-");
        content.append(ThemeUtils.getCssTheme(Gh4Application.THEME));
        content.append(".css' rel='stylesheet' type='text/css'/>");
        content.append("<script src='file:///android_asset/wraphandler.js' type='text/javascript'></script>");
        content.append("</head><body><pre>");

        String encoded = TextUtils.htmlEncode(mDiff);
        mDiffLines = encoded.split("\n");

        for (int i = 0; i < mDiffLines.length; i++) {
            String line = mDiffLines[i];
            String cssClass = null;
            if (line.startsWith("@@")) {
                cssClass = "change";
            } else if (line.startsWith("+")) {
                cssClass = "add";
            } else if (line.startsWith("-")) {
                cssClass = "remove";
            }

            content.append("<div ");
            if (cssClass != null) {
                content.append("class=\"").append(cssClass).append("\"");
            }
            if (authorized) {
                content.append(" onclick=\"javascript:location.href='comment://add");
                content.append("?position=").append(i).append("'\"");
            }
            content.append(">").append(line).append("</div>");

            List<CommitComment> comments = mCommitCommentsByPos.get(i);
            if (comments != null) {
                for (CommitComment comment : comments) {
                    mCommitComments.put(comment.getId(), comment);
                    content.append("<div class=\"comment\"");
                    if (authorized) {
                        content.append(" onclick=\"javascript:location.href='comment://edit");
                        content.append("?position=").append(i);
                        content.append("&id=").append(comment.getId()).append("'\"");
                    }
                    content.append("><div class=\"change\">");
                    content.append(getString(R.string.commit_comment_header,
                            "<b>" + comment.getUser().getLogin() + "</b>",
                            StringUtils.formatRelativeTime(DiffViewerActivity.this, comment.getCreatedAt(), true)));
                    content.append("</div>").append(comment.getBodyHtml()).append("</div>");
                }
            }
        }
        content.append("</pre></body></html>");
        loadThemedHtml(content.toString());
    }

    private void openCommentDialog(final long id, String line, final int position) {
        final boolean isEdit = id != 0L;
        LayoutInflater inflater = LayoutInflater.from(this);
        View commentDialog = inflater.inflate(R.layout.commit_comment_dialog, null);

        final TextView code = (TextView) commentDialog.findViewById(R.id.line);
        code.setText(line);

        final EditText body = (EditText) commentDialog.findViewById(R.id.body);
        if (isEdit) {
            body.setText(mCommitComments.get(id).getBody());
        }

        final int saveButtonResId = isEdit
                ? R.string.issue_comment_update_title : R.string.issue_comment_title;
        final DialogInterface.OnClickListener saveCb = new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                String text = body.getText().toString();
                if (!StringUtils.isBlank(text)) {
                    AsyncTaskCompat.executeParallel(new CommentTask(id, text, position));
                } else {
                    ToastUtils.showMessage(DiffViewerActivity.this, R.string.commit_comment_error_body);
                }
            }
        };

        AlertDialog.Builder builder = new AlertDialog.Builder(this)
                .setCancelable(true)
                .setTitle(getString(R.string.commit_comment_dialog_title, position))
                .setView(commentDialog)
                .setPositiveButton(saveButtonResId, saveCb)
                .setNegativeButton(R.string.cancel, null);

        builder.show();
    }

    @Override
    protected boolean handleUrlLoad(String url) {
        if (!url.startsWith("comment://")) {
            return false;
        }

        Uri uri = Uri.parse(url);
        int line = Integer.parseInt(uri.getQueryParameter("position"));
        String lineText = Html.fromHtml(mDiffLines[line]).toString();
        String idParam = uri.getQueryParameter("id");
        long id = idParam != null ? Long.parseLong(idParam) : 0L;

        if (idParam == null) {
            openCommentDialog(id, lineText, line);
        } else {
            CommentActionPopup p = new CommentActionPopup(id, line, lineText,
                    mLastTouchDown.x, mLastTouchDown.y);
            p.show();
        }
        return true;
    }

    @Override
    public boolean onTouch(View view, MotionEvent event) {
        if (event.getAction() == MotionEvent.ACTION_DOWN) {
            mLastTouchDown.set((int) event.getX(), (int) event.getY());
        }
        return false;
    }

    protected void refresh() {
        mCommitComments.clear();
        mCommitCommentsByPos.clear();
        getSupportLoaderManager().restartLoader(0, null, mCommentCallback);
        setContentShown(false);
    }

    protected abstract Loader<LoaderResult<List<CommitComment>>> createCommentLoader();
    protected abstract void updateComment(long id, String body, int position) throws IOException;
    protected abstract void deleteComment(long id) throws IOException;

    private class CommentActionPopup extends ListPopupWindow implements
            AdapterView.OnItemClickListener {
        private long mId;
        private int mPosition;
        private String mLineText;

        public CommentActionPopup(long id, int position, String lineText, int x, int y) {
            super(DiffViewerActivity.this, null, R.attr.listPopupWindowStyle);

            mId = id;
            mPosition = position;
            mLineText = lineText;

            ArrayAdapter<String> adapter = new ArrayAdapter<>(DiffViewerActivity.this,
                    R.layout.popup_menu_item, populateChoices(isOwnComment(id)));
            setAdapter(adapter);
            setContentWidth(measureContentWidth(adapter));

            View anchor = findViewById(R.id.popup_helper);
            anchor.layout(x, y, x + 1, y + 1);
            setAnchorView(anchor);

            setOnItemClickListener(this);
            setModal(true);
        }

        @Override
        public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
            if (position == 2) {
                new AlertDialog.Builder(DiffViewerActivity.this)
                        .setTitle(R.string.delete_comment_message)
                        .setMessage(R.string.confirmation)
                        .setPositiveButton(R.string.ok, new DialogInterface.OnClickListener() {
                            @Override
                            public void onClick(DialogInterface dialog, int whichButton) {
                                AsyncTaskCompat.executeParallel(new DeleteCommentTask(mId));
                            }
                        })
                        .setNegativeButton(R.string.cancel, null)
                        .show();
            } else {
                openCommentDialog(position == 0 ? 0 : mId, mLineText, mPosition);
            }
            dismiss();
        }

        private boolean isOwnComment(long id) {
            String login = Gh4Application.get().getAuthLogin();
            CommitComment comment = mCommitComments.get(id);
            User user = comment.getUser();
            return user != null && TextUtils.equals(login, comment.getUser().getLogin());
        }

        private String[] populateChoices(boolean ownComment) {
            String[] choices = new String[ownComment ? 3 : 1];
            choices[0] = getString(R.string.reply);
            if (ownComment) {
                choices[1] = getString(R.string.edit);
                choices[2] = getString(R.string.delete);
            }
            return choices;
        }

        private int measureContentWidth(ListAdapter adapter) {
            Context context = DiffViewerActivity.this;
            ViewGroup measureParent = new FrameLayout(context);
            int measureSpec = View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED);
            int maxWidth = 0, count = adapter.getCount();
            View itemView = null;

            for (int i = 0; i < count; i++) {
                itemView = adapter.getView(i, itemView, measureParent);
                itemView.measure(measureSpec, measureSpec);
                maxWidth = Math.max(maxWidth, itemView.getMeasuredWidth());
            }
            return maxWidth;
        }
    }

    private class CommentTask extends ProgressDialogTask<Void> {
        private String mBody;
        private int mPosition;
        private long mId;

        public CommentTask(long id, String body, int position) {
            super(DiffViewerActivity.this, 0, R.string.saving_msg);
            mBody = body;
            mPosition = position;
            mId = id;
        }

        @Override
        protected Void run() throws IOException {
            updateComment(mId, mBody, mPosition);
            return null;
        }

        @Override
        protected void onSuccess(Void result) {
            refresh();
            setResult(RESULT_OK);
        }
    }

    private class DeleteCommentTask extends ProgressDialogTask<Void> {
        private long mId;

        public DeleteCommentTask(long id) {
            super(DiffViewerActivity.this, 0, R.string.deleting_msg);
            mId = id;
        }

        @Override
        protected Void run() throws IOException {
            deleteComment(mId);
            return null;
        }

        @Override
        protected void onSuccess(Void result) {
            refresh();
            setResult(RESULT_OK);
        }
    }
}


File: src/com/gh4a/activities/FileViewerActivity.java
/*
 * Copyright 2011 Azwan Adli Abdullah
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.gh4a.activities;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.support.v4.content.Loader;
import android.support.v4.view.MenuItemCompat;
import android.support.v7.app.ActionBar;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;

import com.gh4a.Constants;
import com.gh4a.R;
import com.gh4a.loader.ContentLoader;
import com.gh4a.loader.LoaderCallbacks;
import com.gh4a.loader.LoaderResult;
import com.gh4a.utils.FileUtils;
import com.gh4a.utils.IntentUtils;
import com.gh4a.utils.StringUtils;

import org.eclipse.egit.github.core.RepositoryContents;
import org.eclipse.egit.github.core.util.EncodingUtils;

import java.util.List;
import java.util.Locale;

public class FileViewerActivity extends WebViewerActivity {
    private String mRepoName;
    private String mRepoOwner;
    private String mPath;
    private String mRef;

    private static final int MENU_ITEM_HISTORY = 10;

    private LoaderCallbacks<List<RepositoryContents>> mFileCallback =
            new LoaderCallbacks<List<RepositoryContents>>() {
        @Override
        public Loader<LoaderResult<List<RepositoryContents>>> onCreateLoader(int id, Bundle args) {
            return new ContentLoader(FileViewerActivity.this, mRepoOwner, mRepoName, mPath, mRef);
        }

        @Override
        public void onResultReady(LoaderResult<List<RepositoryContents>> result) {
            boolean dataLoaded = false;

            if (!result.handleError(FileViewerActivity.this)) {
                List<RepositoryContents> data = result.getData();
                if (data != null && !data.isEmpty()) {
                    loadContent(data.get(0));
                    dataLoaded = true;
                }
            }
            if (!dataLoaded) {
                setContentEmpty(true);
                setContentShown(true);
            }
        }
    };

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        if (hasErrorView()) {
            return;
        }

        Bundle data = getIntent().getExtras();
        mRepoOwner = data.getString(Constants.Repository.OWNER);
        mRepoName = data.getString(Constants.Repository.NAME);
        mPath = data.getString(Constants.Object.PATH);
        mRef = data.getString(Constants.Object.REF);

        ActionBar actionBar = getSupportActionBar();
        actionBar.setTitle(FileUtils.getFileName(mPath));
        actionBar.setSubtitle(mRepoOwner + "/" + mRepoName);
        actionBar.setDisplayHomeAsUpEnabled(true);

        getSupportLoaderManager().initLoader(0, null, mFileCallback);
    }

    private void loadContent(RepositoryContents content) {
        String base64Data = content.getContent();
        if (base64Data != null && FileUtils.isImage(mPath)) {
            String imageUrl = "data:image/" + FileUtils.getFileExtension(mPath) +
                    ";base64," + base64Data;
            loadThemedHtml(StringUtils.highlightImage(imageUrl));
        } else {
            String data = base64Data != null ? new String(EncodingUtils.fromBase64(base64Data)) : "";
            loadThemedHtml(StringUtils.highlightSyntax(data, mPath, mRepoOwner, mRepoName, mRef));
        }
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuInflater inflater = getMenuInflater();
        inflater.inflate(R.menu.download_menu, menu);

        if (FileUtils.isImage(mPath)) {
            menu.removeItem(R.id.wrap);
        }

        menu.removeItem(R.id.download);
        MenuItem item = menu.add(0, MENU_ITEM_HISTORY, Menu.NONE, R.string.history);
        MenuItemCompat.setShowAsAction(item, MenuItemCompat.SHOW_AS_ACTION_NEVER);

        return super.onCreateOptionsMenu(menu);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        String url = String.format(Locale.US, "https://github.com/%s/%s/blob/%s/%s",
                mRepoOwner, mRepoName, mRef, mPath);

        switch (item.getItemId()) {
            case R.id.browser:
                IntentUtils.launchBrowser(this, Uri.parse(url));
                return true;
            case R.id.share:
                Intent shareIntent = new Intent(Intent.ACTION_SEND);
                shareIntent.setType("text/plain");
                shareIntent.putExtra(Intent.EXTRA_SUBJECT, getString(R.string.share_file_subject,
                        FileUtils.getFileName(mPath), mRepoOwner + "/" + mRepoName));
                shareIntent.putExtra(Intent.EXTRA_TEXT, url);
                shareIntent = Intent.createChooser(shareIntent, getString(R.string.share_title));
                startActivity(shareIntent);
                return true;
            case MENU_ITEM_HISTORY:
                Intent historyIntent = new Intent(this, CommitHistoryActivity.class);
                historyIntent.putExtra(Constants.Repository.OWNER, mRepoOwner);
                historyIntent.putExtra(Constants.Repository.NAME, mRepoName);
                historyIntent.putExtra(Constants.Object.PATH, mPath);
                historyIntent.putExtra(Constants.Object.REF, mRef);
                startActivity(historyIntent);
                return true;
         }
         return super.onOptionsItemSelected(item);
     }

    @Override
    protected Intent navigateUp() {
        return IntentUtils.getRepoActivityIntent(this, mRepoOwner, mRepoName, null);
    }
}


File: src/com/gh4a/activities/GistViewerActivity.java
/*
 * Copyright 2011 Azwan Adli Abdullah
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.gh4a.activities;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.support.v4.content.Loader;
import android.support.v7.app.ActionBar;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;

import com.gh4a.Constants;
import com.gh4a.R;
import com.gh4a.loader.GistLoader;
import com.gh4a.loader.LoaderCallbacks;
import com.gh4a.loader.LoaderResult;
import com.gh4a.utils.IntentUtils;
import com.gh4a.utils.StringUtils;

import org.eclipse.egit.github.core.Gist;
import org.eclipse.egit.github.core.GistFile;

public class GistViewerActivity extends WebViewerActivity {
    private String mUserLogin;
    private String mFileName;
    private String mGistId;
    private GistFile mGistFile;

    private LoaderCallbacks<Gist> mGistCallback = new LoaderCallbacks<Gist>() {
        @Override
        public Loader<LoaderResult<Gist>> onCreateLoader(int id, Bundle args) {
            return new GistLoader(GistViewerActivity.this, mGistId);
        }
        @Override
        public void onResultReady(LoaderResult<Gist> result) {
            boolean success = !result.handleError(GistViewerActivity.this);
            if (success) {
                mGistFile = result.getData().getFiles().get(mFileName);
                loadThemedHtml(StringUtils.highlightSyntax(mGistFile.getContent(),
                        mFileName, null, null, null));
            } else {
                setContentEmpty(true);
                setContentShown(true);
            }
            supportInvalidateOptionsMenu();
        }
    };

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        if (hasErrorView()) {
            return;
        }

        mUserLogin = getIntent().getExtras().getString(Constants.User.LOGIN);
        mFileName = getIntent().getExtras().getString(Constants.Gist.FILENAME);
        mGistId = getIntent().getExtras().getString(Constants.Gist.ID);

        ActionBar actionBar = getSupportActionBar();
        actionBar.setTitle(mFileName);
        actionBar.setDisplayHomeAsUpEnabled(true);

        getSupportLoaderManager().initLoader(0, null, mGistCallback);
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuInflater inflater = getMenuInflater();
        inflater.inflate(R.menu.download_menu, menu);

        menu.removeItem(R.id.download);
        menu.removeItem(R.id.share);
        if (mGistFile == null) {
            menu.removeItem(R.id.browser);
        }

        return super.onCreateOptionsMenu(menu);
    }

    @Override
    protected Intent navigateUp() {
        return IntentUtils.getGistActivityIntent(this, mUserLogin, mGistId);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case R.id.browser:
                IntentUtils.launchBrowser(this, Uri.parse(mGistFile.getRawUrl()));
                return true;
        }
        return super.onOptionsItemSelected(item);
    }
}

File: src/com/gh4a/activities/WebViewerActivity.java
/*
 * Copyright 2011 Azwan Adli Abdullah
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.gh4a.activities;

import android.annotation.SuppressLint;
import android.annotation.TargetApi;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.res.TypedArray;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.support.annotation.NonNull;
import android.util.AttributeSet;
import android.view.ContextThemeWrapper;
import android.view.LayoutInflater;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;

import com.gh4a.BaseActivity;
import com.gh4a.Gh4Application;
import com.gh4a.R;
import com.gh4a.fragment.SettingsFragment;
import com.gh4a.utils.ThemeUtils;

public abstract class WebViewerActivity extends BaseActivity {
    protected WebView mWebView;

    private int[] ZOOM_SIZES = new int[] {
        50, 75, 100, 150, 200
    };
    @SuppressWarnings("deprecation")
    private WebSettings.TextSize[] ZOOM_SIZES_API10 = new WebSettings.TextSize[] {
        WebSettings.TextSize.SMALLEST, WebSettings.TextSize.SMALLER,
        WebSettings.TextSize.NORMAL, WebSettings.TextSize.LARGER,
        WebSettings.TextSize.LARGEST
    };

    private WebViewClient mWebViewClient = new WebViewClient() {
        @Override
        public void onPageFinished(WebView webView, String url) {
            applyLineWrapping(shouldWrapLines());
            setContentShown(true);
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, String url) {
            if (!handleUrlLoad(url)) {
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                } catch (ActivityNotFoundException e) {
                    // ignore
                }
            }
            return true;
        }
    };

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        if (hasErrorView()) {
            return;
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
                WebView.setWebContentsDebuggingEnabled(true);
            }
        }

        // We also use the dark CAB for the light theme, so we have to inflate
        // the WebView using a dark theme
        Context inflateContext = new ContextThemeWrapper(this, R.style.DarkTheme);
        setContentView(LayoutInflater.from(inflateContext).inflate(R.layout.web_viewer, null));

        setContentShown(false);
        setupWebView();
    }

    @Override
    public View onCreateView(String name, @NonNull Context context, @NonNull AttributeSet attrs) {
        View view = super.onCreateView(name, context, attrs);
        // When tinting the views, the support library discards the passed context,
        // thus the search view input box is black-on-black when using the light
        // theme. Fix that by post-processing the EditText instance
        if (view instanceof EditText) {
            applyDefaultDarkColors((EditText) view);
        }
        return view;
    }

    private void applyDefaultDarkColors(EditText view) {
        TypedArray a = getTheme().obtainStyledAttributes(R.style.DarkTheme, new int[] {
            android.R.attr.textColorPrimary, android.R.attr.textColorHint
        });
        view.setTextColor(a.getColor(0, 0));
        view.setHintTextColor(a.getColor(1, 0));
        a.recycle();
    }

    @SuppressWarnings("deprecation")
    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        mWebView = (WebView) findViewById(R.id.web_view);

        WebSettings s = mWebView.getSettings();
        s.setLayoutAlgorithm(WebSettings.LayoutAlgorithm.NORMAL);
        s.setAllowFileAccess(true);
        s.setBuiltInZoomControls(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.HONEYCOMB) {
            s.setDisplayZoomControls(false);
        }
        s.setLightTouchEnabled(true);
        s.setLoadsImagesAutomatically(true);
        s.setSupportZoom(true);
        s.setJavaScriptEnabled(true);
        s.setUseWideViewPort(false);
        applyDefaultTextSize(s);

        mWebView.setBackgroundColor(ThemeUtils.getWebViewBackgroundColor(Gh4Application.THEME));
        mWebView.setWebViewClient(mWebViewClient);
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.HONEYCOMB) {
            menu.removeItem(R.id.search);
        }
        return super.onCreateOptionsMenu(menu);
    }

    @Override
    public boolean onPrepareOptionsMenu(Menu menu) {
        MenuItem wrapItem = menu.findItem(R.id.wrap);
        if (wrapItem != null) {
            wrapItem.setChecked(shouldWrapLines());
        }
        return super.onPrepareOptionsMenu(menu);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        int itemId = item.getItemId();

        if (itemId == R.id.search) {
            doSearch();
            return true;
        } else if (itemId == R.id.wrap) {
            boolean newState = !shouldWrapLines();
            item.setChecked(newState);
            setLineWrapping(newState);
            applyLineWrapping(newState);
            return true;
        }

        return super.onOptionsItemSelected(item);
    }

    @SuppressWarnings("deprecation")
    @TargetApi(11)
    private void doSearch() {
        if (mWebView != null) {
            mWebView.showFindDialog(null, true);
        }
    }

    @SuppressWarnings("deprecation")
    private void applyDefaultTextSize(WebSettings s) {
        SharedPreferences prefs = getSharedPreferences(SettingsFragment.PREF_NAME, MODE_PRIVATE);
        int initialZoomLevel = prefs.getInt(SettingsFragment.KEY_TEXT_SIZE, -1);
        if (initialZoomLevel < 0 || initialZoomLevel >= ZOOM_SIZES.length) {
            return;
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.ICE_CREAM_SANDWICH) {
            s.setTextZoom(ZOOM_SIZES[initialZoomLevel]);
        } else {
            s.setTextSize(ZOOM_SIZES_API10[initialZoomLevel]);
        }
    }

    protected void loadUnthemedHtml(String html) {
        if (Gh4Application.THEME == R.style.DarkTheme) {
            html = "<style type=\"text/css\">" +
                    "body { color: #A3A3A5 !important }" +
                    "a { color: #4183C4 !important }</style><body>" +
                    html + "</body>";
        }
        loadThemedHtml(html);
    }

    protected void loadThemedHtml(String html) {
        mWebView.loadDataWithBaseURL("file:///android_asset/", html, null, "utf-8", null);
    }

    private boolean shouldWrapLines() {
        return getPrefs().getBoolean("line_wrapping", false);
    }

    private void setLineWrapping(boolean enabled) {
        getPrefs().edit().putBoolean("line_wrapping", enabled).apply();
    }

    private SharedPreferences getPrefs() {
        return getSharedPreferences(SettingsFragment.PREF_NAME, MODE_PRIVATE);
    }

    private void applyLineWrapping(boolean enabled) {
        mWebView.loadUrl("javascript:applyLineWrapping(" + enabled + ")");
    }

    protected boolean handleUrlLoad(String url) {
        return false;
    }
}


File: src/com/gh4a/utils/FileUtils.java
package com.gh4a.utils;

import android.util.Log;

import com.gh4a.Constants;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

public class FileUtils {
    private static List<String> imageExts = Arrays.asList(
        "png", "gif", "jpeg", "jpg", "bmp", "ico"
    );

    public static boolean save(File file, InputStream inputStream) {
        OutputStream out = null;
        try {
            out = new FileOutputStream(file);
            int read;
            byte[] bytes = new byte[1024];

            while ((read = inputStream.read(bytes)) != -1) {
                out.write(bytes, 0, read);
            }
            return true;
        } catch (IOException e) {
            Log.e(Constants.LOG_TAG, e.getMessage(), e);
        } finally {
            try {
                if (inputStream != null) {
                    inputStream.close();
                }
                if (out != null) {
                    out.flush();
                    out.close();
                }
            } catch (IOException e) {
                Log.e(Constants.LOG_TAG, e.getMessage(), e);
            }
        }
        return false;
    }

    public static String getFileExtension(String filename) {
        int mid = filename.lastIndexOf(".");
        if (mid == -1) {
            return "";
        }

        return filename.substring(mid + 1, filename.length());
    }

    public static String getFileName(String path) {
        if (StringUtils.isBlank(path)) {
            return "";
        }
        int mid = path.lastIndexOf("/");
        if (mid == -1) {
            return path;
        }
        return path.substring(mid + 1, path.length());
    }

    public static boolean isImage(String filename) {
        if (StringUtils.isBlank(filename)) {
            return false;
        }
        String ext = getFileExtension(filename);
        if (StringUtils.isBlank(ext)) {
            return false;
        }

        return imageExts.contains(ext.toLowerCase(Locale.US));
    }
}


File: src/com/gh4a/utils/StringUtils.java
/*
 * Copyright 2011 Azwan Adli Abdullah
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.gh4a.utils;

import android.content.Context;
import android.graphics.Typeface;
import android.text.SpannableStringBuilder;
import android.text.TextUtils;
import android.text.format.DateUtils;

import com.gh4a.Constants;
import com.gh4a.Gh4Application;
import com.gh4a.widget.CustomTypefaceSpan;
import com.gh4a.widget.StyleableTextView;

import java.util.Date;
import java.util.regex.Pattern;

/**
 * The Class StringUtils.
 */
public class StringUtils {
    private static final Pattern EMAIL_ADDRESS_PATTERN = Pattern.compile(
            "[a-zA-Z0-9\\+\\._%\\-\\+]{1,256}" +
            "@" +
            "[a-zA-Z0-9][a-zA-Z0-9\\-]{0,64}" +
            "(" +
            "\\." +
            "[a-zA-Z0-9][a-zA-Z0-9\\-]{0,25}" +
            ")+");

    /**
     * Checks if is blank.
     *
     * @param val the val
     * @return true, if is blank
     */
    public static boolean isBlank(String val) {
        return val == null || val.trim().isEmpty();
    }

    /**
     * Do teaser.
     *
     * @param text the text
     * @return the string
     */
    public static String doTeaser(String text) {
        if (isBlank(text)) {
            return "";
        }

        int indexNewLine = text.indexOf("\n");
        int indexDot = text.indexOf(". ");

        if (indexDot != -1 && indexNewLine != -1) {
            if (indexDot > indexNewLine) {
                text = text.substring(0, indexNewLine);
            } else {
                text = text.substring(0, indexDot + 1);
            }
        } else if (indexDot != -1) {
            text = text.substring(0, indexDot + 1);
        } else if (indexNewLine != -1) {
            text = text.substring(0, indexNewLine);
        }

        return text;
    }

    /**
     * Format name.
     *
     * @param userLogin the user login
     * @param name the name
     * @return the string
     */
    public static String formatName(String userLogin, String name) {
        if (StringUtils.isBlank(userLogin)) {
            return name;
        }

        return userLogin + (!StringUtils.isBlank(name) ? " - " + name : "");
    }

    public static String highlightSyntax(String data, String fileName,
            String repoOwner, String repoName, String ref) {
        String ext = FileUtils.getFileExtension(fileName);

        StringBuilder content = new StringBuilder();
        content.append("<html><head><title></title>");
        writeScriptInclude(content, "wraphandler");

        if (Constants.MARKDOWN_EXT.contains(ext)) {
            writeScriptInclude(content, "showdown");
            writeCssInclude(content, "markdown");
            content.append("</head>");
            content.append("<body>");
            content.append("<div id='content'>");
        } else if (!Constants.SKIP_PRETTIFY_EXT.contains(ext)) {
            writeCssInclude(content, "prettify");
            writeScriptInclude(content, "prettify");
            // Try to load the language extension file.
            // If there's none, this will fail silently
            writeScriptInclude(content, "lang-" + ext);
            content.append("</head>");
            content.append("<body onload='prettyPrint()'>");
            content.append("<pre class='prettyprint linenums lang-").append(ext).append("'>");
        } else{
            writeCssInclude(content, "text");
            content.append("</head>");
            content.append("<body>");
            content.append("<pre>");
        }

        content.append(TextUtils.htmlEncode(data));

        if (Constants.MARKDOWN_EXT.contains(ext)) {
            content.append("</div>");

            content.append("<script>");
            if (repoOwner != null && repoName != null) {
                content.append("var GitHub = new Object();");
                content.append("GitHub.nameWithOwner = \"");
                content.append(repoOwner).append("/").append(repoName).append("\";");
                if (ref != null) {
                    content.append("GitHub.branch = \"").append(ref).append("\";");
                }
            }
            content.append("var text = document.getElementById('content').innerHTML;");
            content.append("var converter = new Showdown.converter();");
            content.append("var html = converter.makeHtml(text);");
            content.append("document.getElementById('content').innerHTML = html;");
            content.append("</script>");
        } else {
            content.append("</pre>");
        }

        content.append("</body></html>");

        return content.toString();
    }

    private static void writeScriptInclude(StringBuilder builder, String scriptName) {
        builder.append("<script src='file:///android_asset/");
        builder.append(scriptName);
        builder.append(".js' type='text/javascript'></script>");
    }

    private static void writeCssInclude(StringBuilder builder, String cssType) {
        builder.append("<link href='file:///android_asset/");
        builder.append(cssType);
        builder.append("-");
        builder.append(ThemeUtils.getCssTheme(Gh4Application.THEME));
        builder.append(".css' rel='stylesheet' type='text/css'/>");
    }

    public static String highlightImage(String imageUrl) {
        StringBuilder content = new StringBuilder();
        content.append("<html><head>");
        writeCssInclude(content, "text");
        content.append("</head><body><div class='image'>");
        content.append("<img src='").append(imageUrl).append("' />");
        content.append("</div></body></html>");
        return content.toString();
    }

    public static boolean checkEmail(String email) {
        return EMAIL_ADDRESS_PATTERN.matcher(email).matches();
    }

    public static CharSequence formatRelativeTime(Context context, Date date, boolean showDateIfLongAgo) {
        long now = System.currentTimeMillis();
        long time = date.getTime();
        long duration = Math.abs(now - time);

        if (showDateIfLongAgo && duration >= DateUtils.WEEK_IN_MILLIS) {
            return DateUtils.getRelativeTimeSpanString(context, time, true);
        }
        return Gh4Application.get().getPrettyTimeInstance().format(date);
    }

    public static void applyBoldTagsAndSetText(StyleableTextView view, String input) {
        SpannableStringBuilder text = applyBoldTags(view.getContext(),
                input, view.getTypefaceValue());
        view.setText(text);
    }

    public static SpannableStringBuilder applyBoldTags(Context context,
            String input, int baseTypefaceValue) {
        SpannableStringBuilder ssb = new SpannableStringBuilder();
        int pos = 0;

        while (pos >= 0) {
            int start = input.indexOf("[b]", pos);
            int end = input.indexOf("[/b]", pos);
            if (start >= 0 && end >= 0) {
                int tokenLength = end - start - 3 /* length of [b] */;
                ssb.append(input.substring(pos, start));
                ssb.append(input.substring(start + 3, end));

                Object span = new CustomTypefaceSpan(context, baseTypefaceValue, Typeface.BOLD);
                ssb.setSpan(span, ssb.length() - tokenLength, ssb.length(), 0);

                pos = end + 4;
            } else {
                ssb.append(input.substring(pos, input.length()));
                pos = -1;
            }
        }
        return ssb;
    }
}