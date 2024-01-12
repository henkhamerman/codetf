Refactoring Types: ['Move Attribute']
r/redreader/activities/CaptchaActivity.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.activities;

import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.*;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.CacheRequest;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.Constants;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.common.RRError;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;
import org.quantumbadger.redreader.views.liststatus.LoadingView;

import java.io.IOException;
import java.net.URI;
import java.util.UUID;

public class CaptchaActivity extends BaseActivity {

	@Override
	protected void onCreate(Bundle savedInstanceState) {

		PrefsUtility.applyTheme(this);
		getActionBar().setTitle(R.string.post_captcha_title);

		super.onCreate(savedInstanceState);

		final LoadingView loadingView = new LoadingView(this, R.string.download_waiting, true, true);
		setContentView(loadingView);

		final RedditAccount selectedAccount = RedditAccountManager.getInstance(this).getAccount(getIntent().getStringExtra("username"));

		final CacheManager cm = CacheManager.getInstance(this);

		RedditAPI.newCaptcha(cm, new APIResponseHandler.NewCaptchaResponseHandler(this) {
			@Override
			protected void onSuccess(final String captchaId) {

				final URI captchaUrl = Constants.Reddit.getUri("/captcha/" + captchaId);

				cm.makeRequest(new CacheRequest(captchaUrl, RedditAccountManager.getAnon(), null, Constants.Priority.CAPTCHA,
						0, CacheRequest.DownloadType.FORCE, Constants.FileType.CAPTCHA, false, false, true, CaptchaActivity.this) {
					@Override
					protected void onCallbackException(Throwable t) {
						BugReportActivity.handleGlobalError(CaptchaActivity.this, t);
					}

					@Override
					protected void onDownloadNecessary() {}

					@Override
					protected void onDownloadStarted() {
						loadingView.setIndeterminate(R.string.download_downloading);
					}

					@Override
					protected void onFailure(RequestFailureType type, Throwable t, StatusLine status, String readableMessage) {
						final RRError error = General.getGeneralErrorForFailure(CaptchaActivity.this, type, t, status, url.toString());
						General.showResultDialog(CaptchaActivity.this, error);
						finish();
					}

					@Override
					protected void onProgress(final boolean authorizationInProgress, long bytesRead, long totalBytes) {
						if(authorizationInProgress) {
							loadingView.setIndeterminate(R.string.download_authorizing);
						} else {
							loadingView.setProgress(R.string.download_downloading, (float)((double)bytesRead / (double)totalBytes));
						}
					}

					@Override
					protected void onSuccess(final CacheManager.ReadableCacheFile cacheFile, long timestamp, UUID session, boolean fromCache, String mimetype) {

						final Bitmap image;
						try {
							image = BitmapFactory.decodeStream(cacheFile.getInputStream());
						} catch(IOException e) {
							BugReportActivity.handleGlobalError(CaptchaActivity.this, e);
							return;
						}

						General.UI_THREAD_HANDLER.post(new Runnable() {
							public void run() {

								final LinearLayout ll = new LinearLayout(CaptchaActivity.this);
								ll.setOrientation(LinearLayout.VERTICAL);

								final ImageView captchaImg = new ImageView(CaptchaActivity.this);
								ll.addView(captchaImg);
								final LinearLayout.LayoutParams layoutParams = (LinearLayout.LayoutParams) captchaImg.getLayoutParams();
								layoutParams.setMargins(20, 20, 20, 20);
								layoutParams.height = General.dpToPixels(context, 100);
								captchaImg.setScaleType(ImageView.ScaleType.FIT_CENTER);


								final EditText captchaText = new EditText(CaptchaActivity.this);
								ll.addView(captchaText);
								((LinearLayout.LayoutParams) captchaText.getLayoutParams()).setMargins(20, 0, 20, 20);
								captchaText.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD | InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);

								captchaImg.setImageBitmap(image);

								final Button submitButton = new Button(CaptchaActivity.this);
								submitButton.setText(R.string.post_captcha_submit_button);
								ll.addView(submitButton);
								((LinearLayout.LayoutParams) submitButton.getLayoutParams()).setMargins(20, 0, 20, 20);
								((LinearLayout.LayoutParams) submitButton.getLayoutParams()).gravity = Gravity.RIGHT;
								((LinearLayout.LayoutParams) submitButton.getLayoutParams()).width = LinearLayout.LayoutParams.WRAP_CONTENT;

								submitButton.setOnClickListener(new View.OnClickListener() {
									public void onClick(View v) {
										final Intent result = new Intent();
										result.putExtra("captchaId", captchaId);
										result.putExtra("captchaText", captchaText.getText().toString());
										setResult(RESULT_OK, result);
										finish();
									}
								});

								final ScrollView sv = new ScrollView(CaptchaActivity.this);
								sv.addView(ll);
								setContentView(sv);
							}
						});

					}
				});
			}

			@Override
			protected void onCallbackException(Throwable t) {
				BugReportActivity.handleGlobalError(CaptchaActivity.this, t);
			}

			@Override
			protected void onFailure(RequestFailureType type, Throwable t, StatusLine status, String readableMessage) {
				final RRError error = General.getGeneralErrorForFailure(CaptchaActivity.this, type, t, status, null);
				General.showResultDialog(CaptchaActivity.this, error);
				finish();
			}

			@Override
			protected void onFailure(APIFailureType type) {
				final RRError error = General.getGeneralErrorForFailure(CaptchaActivity.this, type);
				General.showResultDialog(CaptchaActivity.this, error);
				finish();
			}
		}, selectedAccount, this);
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/CommentEditActivity.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.activities;

import android.app.ProgressDialog;
import android.content.DialogInterface;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.common.RRError;
import org.quantumbadger.redreader.fragments.MarkdownPreviewDialog;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;

public class CommentEditActivity extends BaseActivity {

	private EditText textEdit;

	private String commentIdAndType = null;

	@Override
	protected void onCreate(Bundle savedInstanceState) {

		PrefsUtility.applyTheme(this);

		super.onCreate(savedInstanceState);

		final LinearLayout layout = (LinearLayout) getLayoutInflater().inflate(R.layout.comment_edit, null);

		textEdit = (EditText)layout.findViewById(R.id.comment_reply_text);

		if(getIntent() != null && getIntent().hasExtra("commentIdAndType")) {
			commentIdAndType = getIntent().getStringExtra("commentIdAndType");
			textEdit.setText(getIntent().getStringExtra("commentText"));

		} else if(savedInstanceState != null && savedInstanceState.containsKey("commentIdAndType")) {
			textEdit.setText(savedInstanceState.getString("commentText"));
			commentIdAndType = savedInstanceState.getString("commentIdAndType");
		}

		final ScrollView sv = new ScrollView(this);
		sv.addView(layout);
		setContentView(sv);
	}

	@Override
	protected void onSaveInstanceState(Bundle outState) {
		super.onSaveInstanceState(outState);
		outState.putString("commentText", textEdit.getText().toString());
		outState.putString("commentIdAndType", commentIdAndType);
	}

	@Override
	public boolean onCreateOptionsMenu(Menu menu) {

		final MenuItem send = menu.add(R.string.comment_edit_save);
		send.setIcon(R.drawable.ic_action_save_dark);
		send.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);

		menu.add(R.string.comment_reply_preview);

		return true;
	}

	@Override
	public boolean onOptionsItemSelected(MenuItem item) {

		if(item.getTitle().equals(getString(R.string.comment_edit_save))) {

			final ProgressDialog progressDialog = new ProgressDialog(this);
			progressDialog.setTitle(getString(R.string.comment_reply_submitting_title));
			progressDialog.setMessage(getString(R.string.comment_reply_submitting_message));
			progressDialog.setIndeterminate(true);
			progressDialog.setCancelable(true);
			progressDialog.setCanceledOnTouchOutside(false);

			progressDialog.setOnCancelListener(new DialogInterface.OnCancelListener() {
				public void onCancel(final DialogInterface dialogInterface) {
					General.quickToast(CommentEditActivity.this, R.string.comment_reply_oncancel);
					progressDialog.dismiss();
				}
			});

			progressDialog.setOnKeyListener(new DialogInterface.OnKeyListener() {
				public boolean onKey(final DialogInterface dialogInterface, final int keyCode, final KeyEvent keyEvent) {

					if(keyCode == KeyEvent.KEYCODE_BACK) {
						General.quickToast(CommentEditActivity.this, R.string.comment_reply_oncancel);
						progressDialog.dismiss();
					}

					return true;
				}
			});

			final APIResponseHandler.ActionResponseHandler handler = new APIResponseHandler.ActionResponseHandler(this) {
				@Override
				protected void onSuccess() {
					General.UI_THREAD_HANDLER.post(new Runnable() {
						public void run() {
							if(progressDialog.isShowing()) progressDialog.dismiss();
							General.quickToast(CommentEditActivity.this, R.string.comment_edit_done);
							finish();
						}
					});
				}

				@Override
				protected void onCallbackException(Throwable t) {
					BugReportActivity.handleGlobalError(CommentEditActivity.this, t);
				}

				@Override
				protected void onFailure(RequestFailureType type, Throwable t, StatusLine status, String readableMessage) {

					final RRError error = General.getGeneralErrorForFailure(context, type, t, status, null);

					General.UI_THREAD_HANDLER.post(new Runnable() {
						public void run() {
							General.showResultDialog(CommentEditActivity.this, error);
							if(progressDialog.isShowing()) progressDialog.dismiss();
						}
					});
				}

				@Override
				protected void onFailure(final APIFailureType type) {

					final RRError error = General.getGeneralErrorForFailure(context, type);

					General.UI_THREAD_HANDLER.post(new Runnable() {
						public void run() {
							General.showResultDialog(CommentEditActivity.this, error);
							if(progressDialog.isShowing()) progressDialog.dismiss();
						}
					});
				}
			};

			final CacheManager cm = CacheManager.getInstance(this);
			final RedditAccount selectedAccount = RedditAccountManager.getInstance(this).getDefaultAccount();

			RedditAPI.editComment(cm, handler, selectedAccount, commentIdAndType, textEdit.getText().toString(), this);

			progressDialog.show();

		} else if(item.getTitle().equals(getString(R.string.comment_reply_preview))) {
			MarkdownPreviewDialog.newInstance(textEdit.getText().toString()).show(getFragmentManager(), "MarkdownPreviewDialog");
		}

		return true;
	}

	@Override
	public void onBackPressed() {
		if(General.onBackPressed()) super.onBackPressed();
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/CommentReplyActivity.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.activities;

import android.app.ProgressDialog;
import android.content.DialogInterface;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.*;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.common.RRError;
import org.quantumbadger.redreader.fragments.MarkdownPreviewDialog;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;

import java.util.ArrayList;

public class CommentReplyActivity extends BaseActivity {

	private Spinner usernameSpinner;
	private EditText textEdit;

	private String parentIdAndType = null;

	private static String lastText, lastParentIdAndType;

	@Override
	protected void onCreate(Bundle savedInstanceState) {

		PrefsUtility.applyTheme(this);

		super.onCreate(savedInstanceState);

		final LinearLayout layout = (LinearLayout) getLayoutInflater().inflate(R.layout.comment_reply, null);

		usernameSpinner = (Spinner)layout.findViewById(R.id.comment_reply_username);
		textEdit = (EditText)layout.findViewById(R.id.comment_reply_text);

		if(getIntent() != null && getIntent().hasExtra("parentIdAndType")) {
			parentIdAndType = getIntent().getStringExtra("parentIdAndType");

		} else if(savedInstanceState != null && savedInstanceState.containsKey("comment_text")) {
			textEdit.setText(savedInstanceState.getString("comment_text"));
			parentIdAndType = savedInstanceState.getString("parentIdAndType");

		} else if(lastText != null) {
			textEdit.setText(lastText);
			parentIdAndType = lastParentIdAndType;
		}

		final ArrayList<RedditAccount> accounts = RedditAccountManager.getInstance(this).getAccounts();
		final ArrayList<String> usernames = new ArrayList<String>();

		for(RedditAccount account : accounts) {
			if(!account.isAnonymous()) {
				usernames.add(account.username);
			}
		}

		if(usernames.size() == 0) {
			General.quickToast(this, "You must be logged in to do that.");
			finish();
		}

		usernameSpinner.setAdapter(new ArrayAdapter<String>(this, android.R.layout.simple_list_item_1, usernames));

		final ScrollView sv = new ScrollView(this);
		sv.addView(layout);
		setContentView(sv);
	}

	@Override
	protected void onSaveInstanceState(Bundle outState) {
		super.onSaveInstanceState(outState);
		outState.putString("comment_text", textEdit.getText().toString());
		outState.putString("parentIdAndType", parentIdAndType);
	}

	@Override
	public boolean onCreateOptionsMenu(Menu menu) {

		final MenuItem send = menu.add(R.string.comment_reply_send);
		send.setIcon(R.drawable.ic_action_send_dark);
		send.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);

		menu.add(R.string.comment_reply_preview);

		return true;
	}

	@Override
	public boolean onOptionsItemSelected(MenuItem item) {

		if(item.getTitle().equals(getString(R.string.comment_reply_send))) {

			final ProgressDialog progressDialog = new ProgressDialog(this);
			progressDialog.setTitle(getString(R.string.comment_reply_submitting_title));
			progressDialog.setMessage(getString(R.string.comment_reply_submitting_message));
			progressDialog.setIndeterminate(true);
			progressDialog.setCancelable(true);
			progressDialog.setCanceledOnTouchOutside(false);

			progressDialog.setOnCancelListener(new DialogInterface.OnCancelListener() {
				public void onCancel(final DialogInterface dialogInterface) {
					General.quickToast(CommentReplyActivity.this, getString(R.string.comment_reply_oncancel));
					progressDialog.dismiss();
				}
			});

			progressDialog.setOnKeyListener(new DialogInterface.OnKeyListener() {
				public boolean onKey(final DialogInterface dialogInterface, final int keyCode, final KeyEvent keyEvent) {

					if(keyCode == KeyEvent.KEYCODE_BACK) {
						General.quickToast(CommentReplyActivity.this, getString(R.string.comment_reply_oncancel));
						progressDialog.dismiss();
					}

					return true;
				}
			});

			final APIResponseHandler.ActionResponseHandler handler = new APIResponseHandler.ActionResponseHandler(this) {
				@Override
				protected void onSuccess() {
					General.UI_THREAD_HANDLER.post(new Runnable() {
						public void run() {
							if(progressDialog.isShowing()) progressDialog.dismiss();
							General.quickToast(CommentReplyActivity.this, getString(R.string.comment_reply_done));
							finish();
						}
					});
				}

				@Override
				protected void onCallbackException(Throwable t) {
					BugReportActivity.handleGlobalError(CommentReplyActivity.this, t);
				}

				@Override
				protected void onFailure(RequestFailureType type, Throwable t, StatusLine status, String readableMessage) {

					final RRError error = General.getGeneralErrorForFailure(context, type, t, status, null);

					General.UI_THREAD_HANDLER.post(new Runnable() {
						public void run() {
							General.showResultDialog(CommentReplyActivity.this, error);
							if(progressDialog.isShowing()) progressDialog.dismiss();
						}
					});
				}

				@Override
				protected void onFailure(final APIFailureType type) {

					final RRError error = General.getGeneralErrorForFailure(context, type);

					General.UI_THREAD_HANDLER.post(new Runnable() {
						public void run() {
							General.showResultDialog(CommentReplyActivity.this, error);
							if(progressDialog.isShowing()) progressDialog.dismiss();
						}
					});
				}
			};

			final CacheManager cm = CacheManager.getInstance(this);

			final ArrayList<RedditAccount> accounts = RedditAccountManager.getInstance(this).getAccounts();
			RedditAccount selectedAccount = null;

			for(RedditAccount account : accounts) {
				if(!account.isAnonymous() && account.username.equalsIgnoreCase((String)usernameSpinner.getSelectedItem())) {
					selectedAccount = account;
					break;
				}
			}

			RedditAPI.comment(cm, handler, selectedAccount, parentIdAndType, textEdit.getText().toString(), this);

			progressDialog.show();

		} else if(item.getTitle().equals(getString(R.string.comment_reply_preview))) {
			MarkdownPreviewDialog.newInstance(textEdit.getText().toString()).show(getFragmentManager(), "MarkdownPreviewDialog");
		}

		return true;
	}

	@Override
	protected void onDestroy() {
		super.onDestroy();

		if(textEdit != null) {
			lastText = textEdit.getText().toString();
			lastParentIdAndType = parentIdAndType;
		}
	}

	@Override
	public void onBackPressed() {
		if(General.onBackPressed()) super.onBackPressed();
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/ImageViewActivity.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.activities;

import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.media.MediaPlayer;
import android.net.Uri;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.*;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.CacheRequest;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.*;
import org.quantumbadger.redreader.image.GifDecoderThread;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedPost;
import org.quantumbadger.redreader.reddit.things.RedditPost;
import org.quantumbadger.redreader.reddit.url.PostCommentListingURL;
import org.quantumbadger.redreader.views.GIFView;
import org.quantumbadger.redreader.views.RedditPostView;
import org.quantumbadger.redreader.views.bezelmenu.BezelSwipeOverlay;
import org.quantumbadger.redreader.views.bezelmenu.SideToolbarOverlay;
import org.quantumbadger.redreader.views.glview.RRGLSurfaceView;
import org.quantumbadger.redreader.views.imageview.ImageTileSource;
import org.quantumbadger.redreader.views.imageview.ImageTileSourceWholeBitmap;
import org.quantumbadger.redreader.views.imageview.ImageViewDisplayListManager;
import org.quantumbadger.redreader.views.liststatus.ErrorView;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.util.UUID;

public class ImageViewActivity extends BaseActivity implements RedditPostView.PostSelectionListener, ImageViewDisplayListManager.Listener {

	GLSurfaceView surfaceView;
	private ImageView imageView;
	private GifDecoderThread gifThread;

	private URI mUrl;

	private boolean mIsPaused = true, mIsDestroyed = false;
	private CacheRequest mRequest;

	private boolean mHaveReverted = false;

	private ImageViewDisplayListManager mImageViewDisplayerManager;

	@Override
	protected void onCreate(Bundle savedInstanceState) {

		super.onCreate(savedInstanceState);

		final SharedPreferences sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);
		final boolean solidblack = PrefsUtility.appearance_solidblack(this, sharedPreferences);

		if(solidblack) getWindow().setBackgroundDrawable(new ColorDrawable(Color.BLACK));

		final Intent intent = getIntent();

		mUrl = General.uriFromString(intent.getDataString());
		final RedditPost src_post = intent.getParcelableExtra("post");

		if(mUrl == null) {
			General.quickToast(this, "Invalid URL. Trying web browser.");
			revertToWeb();
			return;
		}

		Log.i("ImageViewActivity", "Loading URL " + mUrl.toString());

		final ProgressBar progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);

		final LinearLayout layout = new LinearLayout(this);
		layout.setOrientation(LinearLayout.VERTICAL);
		layout.addView(progressBar);

		CacheManager.getInstance(this).makeRequest(
				mRequest = new CacheRequest(
						mUrl,
						RedditAccountManager.getAnon(),
						null,
						Constants.Priority.IMAGE_VIEW,
						0,
						CacheRequest.DownloadType.IF_NECESSARY,
						Constants.FileType.IMAGE,
						false, false, false, this) {

					private void setContentView(View v) {
						layout.removeAllViews();
						layout.addView(v);
						v.getLayoutParams().width = ViewGroup.LayoutParams.MATCH_PARENT;
						v.getLayoutParams().height = ViewGroup.LayoutParams.MATCH_PARENT;
					}

					@Override
					protected void onCallbackException(Throwable t) {
						BugReportActivity.handleGlobalError(context.getApplicationContext(), new RRError(null, null, t));
					}

					@Override
					protected void onDownloadNecessary() {
						General.UI_THREAD_HANDLER.post(new Runnable() {
							@Override
							public void run() {
								progressBar.setVisibility(View.VISIBLE);
								progressBar.setIndeterminate(true);
							}
						});
					}

					@Override
					protected void onDownloadStarted() {}

					@Override
					protected void onFailure(final RequestFailureType type, Throwable t, StatusLine status, final String readableMessage) {

						final RRError error = General.getGeneralErrorForFailure(context, type, t, status, url.toString());

						General.UI_THREAD_HANDLER.post(new Runnable() {
							public void run() {
								// TODO handle properly
								mRequest = null;
								progressBar.setVisibility(View.GONE);
								layout.addView(new ErrorView(ImageViewActivity.this, error));
							}
						});
					}

					@Override
					protected void onProgress(final boolean authorizationInProgress, final long bytesRead, final long totalBytes) {
						General.UI_THREAD_HANDLER.post(new Runnable() {
							@Override
							public void run() {
								progressBar.setVisibility(View.VISIBLE);
								progressBar.setIndeterminate(authorizationInProgress);
								progressBar.setProgress((int) ((100 * bytesRead) / totalBytes));
							}
						});
					}

					@Override
					protected void onSuccess(final CacheManager.ReadableCacheFile cacheFile, long timestamp, UUID session, boolean fromCache, final String mimetype) {

						if(mimetype == null || (!Constants.Mime.isImage(mimetype) && !Constants.Mime.isVideo(mimetype))) {
							revertToWeb();
							return;
						}

						final InputStream cacheFileInputStream;
						try {
							cacheFileInputStream = cacheFile.getInputStream();
						} catch(IOException e) {
							notifyFailure(RequestFailureType.PARSE, e, null, "Could not read existing cached image.");
							return;
						}

						if(cacheFileInputStream == null) {
							notifyFailure(RequestFailureType.CACHE_MISS, null, null, "Could not find cached image");
							return;
						}

						if(Constants.Mime.isVideo(mimetype)) {

							General.UI_THREAD_HANDLER.post(new Runnable() {
								public void run() {

									if(mIsDestroyed) return;
									mRequest = null;

									try {
										final RelativeLayout layout = new RelativeLayout(context);
										layout.setGravity(Gravity.CENTER);

										final VideoView videoView = new VideoView(ImageViewActivity.this);

										videoView.setVideoURI(cacheFile.getUri());
										layout.addView(videoView);
										setContentView(layout);

										layout.getLayoutParams().width = ViewGroup.LayoutParams.MATCH_PARENT;
										layout.getLayoutParams().height = ViewGroup.LayoutParams.MATCH_PARENT;
										videoView.setLayoutParams(new RelativeLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

										videoView.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
											@Override
											public void onPrepared(MediaPlayer mp) {
												mp.setLooping(true);
												videoView.start();
											}
										});

										videoView.setOnErrorListener(
												new MediaPlayer.OnErrorListener() {
													@Override
													public boolean onError(final MediaPlayer mediaPlayer, final int i, final int i1) {
														revertToWeb();
														return true;
													}
												});

										videoView.setOnTouchListener(new View.OnTouchListener() {
											@Override
											public boolean onTouch(final View view, final MotionEvent motionEvent) {
												finish();
												return true;
											}
										});

									} catch(OutOfMemoryError e) {
										General.quickToast(context, R.string.imageview_oom);
										revertToWeb();

									} catch(Throwable e) {
										General.quickToast(context, R.string.imageview_invalid_video);
										revertToWeb();
									}
								}
							});

						} else if(Constants.Mime.isImageGif(mimetype)) {

							final PrefsUtility.GifViewMode gifViewMode = PrefsUtility.pref_behaviour_gifview_mode(context, sharedPreferences);

							if(gifViewMode == PrefsUtility.GifViewMode.INTERNAL_BROWSER) {
								revertToWeb();
								return;

							} else if(gifViewMode == PrefsUtility.GifViewMode.EXTERNAL_BROWSER) {
								General.UI_THREAD_HANDLER.post(new Runnable() {
									@Override
									public void run() {
										LinkHandler.openWebBrowser(ImageViewActivity.this, Uri.parse(mUrl.toString()));
										finish();
									}
								});

								return;
							}

							if(AndroidApi.isIceCreamSandwichOrLater()
									&& gifViewMode == PrefsUtility.GifViewMode.INTERNAL_MOVIE) {

								General.UI_THREAD_HANDLER.post(new Runnable() {
									public void run() {

										if(mIsDestroyed) return;
										mRequest = null;

										try {
											final GIFView gifView = new GIFView(ImageViewActivity.this, cacheFileInputStream);
											setContentView(gifView);
											gifView.setOnClickListener(new View.OnClickListener() {
												public void onClick(View v) {
													finish();
												}
											});

										} catch(OutOfMemoryError e) {
											General.quickToast(context, R.string.imageview_oom);
											revertToWeb();

										} catch(Throwable e) {
											General.quickToast(context, R.string.imageview_invalid_gif);
											revertToWeb();
										}
									}
								});

							} else {

								gifThread = new GifDecoderThread(cacheFileInputStream, new GifDecoderThread.OnGifLoadedListener() {

									public void onGifLoaded() {
										General.UI_THREAD_HANDLER.post(new Runnable() {
											public void run() {

												if(mIsDestroyed) return;
												mRequest = null;

												imageView = new ImageView(context);
												imageView.setScaleType(ImageView.ScaleType.FIT_CENTER);
												setContentView(imageView);
												gifThread.setView(imageView);

												imageView.setOnClickListener(new View.OnClickListener() {
													public void onClick(View v) {
														finish();
													}
												});
											}
										});
									}

									public void onOutOfMemory() {
										General.quickToast(context, R.string.imageview_oom);
										revertToWeb();
									}

									public void onGifInvalid() {
										General.quickToast(context, R.string.imageview_invalid_gif);
										revertToWeb();
									}
								});

								gifThread.start();

							}

						} else {

							final ImageTileSource imageTileSource;
							try {

								final long bytes = cacheFile.getSize();
								final byte[] buf = new byte[(int)bytes];

								try {
									new DataInputStream(cacheFileInputStream).readFully(buf);
								} catch(IOException e) {
									throw new RuntimeException(e);
								}

								try {
									imageTileSource = new ImageTileSourceWholeBitmap(buf);

								} catch(Throwable t) {
									Log.e("ImageViewActivity", "Exception when creating ImageTileSource", t);
									General.quickToast(context, R.string.imageview_decode_failed);
									revertToWeb();
									return;
								}

							} catch(OutOfMemoryError e) {
								General.quickToast(context, R.string.imageview_oom);
								revertToWeb();
								return;
							}

							General.UI_THREAD_HANDLER.post(new Runnable() {
								public void run() {

									if(mIsDestroyed) return;
									mRequest = null;
									mImageViewDisplayerManager = new ImageViewDisplayListManager(imageTileSource, ImageViewActivity.this);
									surfaceView = new RRGLSurfaceView(ImageViewActivity.this, mImageViewDisplayerManager);
									setContentView(surfaceView);

									surfaceView.setOnClickListener(new View.OnClickListener() {
										public void onClick(View v) {
											finish();
										}
									});

									if(mIsPaused) {
										surfaceView.onPause();
									} else {
										surfaceView.onResume();
									}
								}
							});
						}
					}
				});

		final RedditPreparedPost post = src_post == null ? null
				: new RedditPreparedPost(this, CacheManager.getInstance(this), 0, src_post, -1, false,
				false, false, false, RedditAccountManager.getInstance(this).getDefaultAccount(), false);

		final FrameLayout outerFrame = new FrameLayout(this);
		outerFrame.addView(layout);

		if(post != null) {

			final SideToolbarOverlay toolbarOverlay = new SideToolbarOverlay(this);

			final BezelSwipeOverlay bezelOverlay = new BezelSwipeOverlay(this, new BezelSwipeOverlay.BezelSwipeListener() {

				public boolean onSwipe(BezelSwipeOverlay.SwipeEdge edge) {

					toolbarOverlay.setContents(post.generateToolbar(ImageViewActivity.this, false, toolbarOverlay));
					toolbarOverlay.show(edge == BezelSwipeOverlay.SwipeEdge.LEFT ?
							SideToolbarOverlay.SideToolbarPosition.LEFT : SideToolbarOverlay.SideToolbarPosition.RIGHT);
					return true;
				}

				public boolean onTap() {

					if(toolbarOverlay.isShown()) {
						toolbarOverlay.hide();
						return true;
					}

					return false;
				}
			});

			outerFrame.addView(bezelOverlay);
			outerFrame.addView(toolbarOverlay);

			bezelOverlay.getLayoutParams().width = android.widget.FrameLayout.LayoutParams.MATCH_PARENT;
			bezelOverlay.getLayoutParams().height = android.widget.FrameLayout.LayoutParams.MATCH_PARENT;

			toolbarOverlay.getLayoutParams().width = android.widget.FrameLayout.LayoutParams.MATCH_PARENT;
			toolbarOverlay.getLayoutParams().height = android.widget.FrameLayout.LayoutParams.MATCH_PARENT;

		}

		setContentView(outerFrame);
	}

	public void onPostSelected(final RedditPreparedPost post) {
		LinkHandler.onLinkClicked(this, post.url, false, post.src);
	}

	public void onPostCommentsSelected(final RedditPreparedPost post) {
		LinkHandler.onLinkClicked(this, PostCommentListingURL.forPostId(post.idAlone).generateJsonUri().toString(), false);
	}

	@Override
	public void onBackPressed() {
		if(General.onBackPressed()) super.onBackPressed();
	}

	private void revertToWeb() {

		final Runnable r = new Runnable() {
			public void run() {
				if(!mHaveReverted) {
					mHaveReverted = true;
					LinkHandler.onLinkClicked(ImageViewActivity.this, mUrl.toString(), true);
					finish();
				}
			}
		};

		if(General.isThisUIThread()) {
			r.run();
		} else {
			General.UI_THREAD_HANDLER.post(r);
		}
	}

	@Override
	public void onPause() {

		if(mIsPaused) throw new RuntimeException();

		mIsPaused = true;

		Log.i("DEBUG", "ImageViewActivity.onPause()");
		super.onPause();
		if(surfaceView != null) {
			Log.i("DEBUG", "surfaceView.onPause()");
			surfaceView.onPause();
		}
	}

	@Override
	public void onResume() {

		if(!mIsPaused) throw new RuntimeException();

		mIsPaused = false;

		Log.i("DEBUG", "ImageViewActivity.onResume()");
		super.onResume();
		if(surfaceView != null) {
			Log.i("DEBUG", "surfaceView.onResume()");
			surfaceView.onResume();
		}
	}

	@Override
	public void onDestroy() {
		super.onDestroy();
		mIsDestroyed = true;
		if(mRequest != null) mRequest.cancel();
		if(gifThread != null) gifThread.stopPlaying();
	}

	@Override
	public void onSingleTap() {
		finish();
	}

	@Override
	public void onImageViewDLMOutOfMemory() {
		if(!mHaveReverted) {
			General.quickToast(this, R.string.imageview_oom);
			revertToWeb();
		}
	}

	@Override
	public void onImageViewDLMException(Throwable t) {
		if(!mHaveReverted) {
			General.quickToast(this, R.string.imageview_decode_failed);
			revertToWeb();
		}
	}

	@Override
	public void onConfigurationChanged(Configuration newConfig) {
		super.onConfigurationChanged(newConfig);
		if(mImageViewDisplayerManager != null){
			mImageViewDisplayerManager.resetTouchState();
		}
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/InboxListingActivity.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.activities;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.preference.PreferenceManager;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.AdapterView;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.adapters.InboxListingAdapter;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.CacheRequest;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.*;
import org.quantumbadger.redreader.jsonwrap.JsonBufferedArray;
import org.quantumbadger.redreader.jsonwrap.JsonBufferedObject;
import org.quantumbadger.redreader.jsonwrap.JsonValue;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;
import org.quantumbadger.redreader.reddit.RedditPreparedInboxItem;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedComment;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedMessage;
import org.quantumbadger.redreader.reddit.things.RedditMessage;
import org.quantumbadger.redreader.reddit.things.RedditThing;
import org.quantumbadger.redreader.views.liststatus.ErrorView;
import org.quantumbadger.redreader.views.liststatus.LoadingView;

import java.net.URI;
import java.util.EnumSet;
import java.util.UUID;

public final class InboxListingActivity extends BaseActivity {

	private static final int OPTIONS_MENU_MARK_ALL_AS_READ = 0;

	private InboxListingAdapter adapter;

	private LoadingView loadingView;
	private LinearLayout notifications;

	private CacheRequest request;

	private EnumSet<PrefsUtility.AppearanceCommentHeaderItems> headerItems;

	private boolean isModmail = false;

	private final Handler itemHandler = new Handler(Looper.getMainLooper()) {
		@Override
		public void handleMessage(final Message msg) {
			adapter.addItem((RedditPreparedInboxItem)msg.obj);
		}
	};

	// TODO load more on scroll to bottom?

	@Override
	public void onCreate(Bundle savedInstanceState) {

		PrefsUtility.applyTheme(this);
		super.onCreate(savedInstanceState);

		final SharedPreferences sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);

		final boolean solidblack = PrefsUtility.appearance_solidblack(this, sharedPreferences)
				&& PrefsUtility.appearance_theme(this, sharedPreferences) == PrefsUtility.AppearanceTheme.NIGHT;

		getActionBar().setHomeButtonEnabled(true);
		getActionBar().setDisplayHomeAsUpEnabled(true);

		final String title;

		isModmail = getIntent() != null && getIntent().getBooleanExtra("modmail", false);

		if(!isModmail) {
			title = getString(R.string.mainmenu_inbox);
		} else {
			title = getString(R.string.mainmenu_modmail);
		}

		OptionsMenuUtility.fixActionBar(this, title);

		headerItems = PrefsUtility.appearance_comment_header_items(this, sharedPreferences);
		headerItems.remove(PrefsUtility.AppearanceCommentHeaderItems.SCORE);

		final LinearLayout outer = new LinearLayout(this);
		outer.setOrientation(android.widget.LinearLayout.VERTICAL);

		if(solidblack) {
			outer.setBackgroundColor(Color.BLACK);
		}

		loadingView = new LoadingView(this, getString(R.string.download_waiting), true, true);

		notifications = new LinearLayout(this);
		notifications.setOrientation(android.widget.LinearLayout.VERTICAL);
		notifications.addView(loadingView);

		final ListView lv = new ListView(this);

		lv.setSmoothScrollbarEnabled(false);
		lv.setVerticalFadingEdgeEnabled(false);

		lv.setOnItemClickListener(new AdapterView.OnItemClickListener() {
			public void onItemClick(AdapterView<?> parent, View view, int position, long id) {

				final Object item = lv.getAdapter().getItem(position);

				if(item != null && item instanceof RedditPreparedInboxItem) {
					((RedditPreparedInboxItem)item).handleInboxClick(InboxListingActivity.this);
				}
			}
		});

		adapter = new InboxListingAdapter(this, this);
		lv.setAdapter(adapter);

		registerForContextMenu(lv);

		outer.addView(notifications);
		outer.addView(lv);

		makeFirstRequest(this);

		setContentView(outer);
	}

	public void cancel() {
		if(request != null) request.cancel();
	}

	private void makeFirstRequest(final Context context) {

		final RedditAccount user = RedditAccountManager.getInstance(context).getDefaultAccount();
		final CacheManager cm = CacheManager.getInstance(context);

		final URI url;

		if(!isModmail) {
			url = Constants.Reddit.getUri("/message/inbox.json?mark=true&limit=100");
		} else {
			url = Constants.Reddit.getUri("/message/moderator.json?limit=100");
		}

		// TODO parameterise limit
		request = new CacheRequest(url, user, null, Constants.Priority.API_INBOX_LIST, 0, CacheRequest.DownloadType.FORCE, Constants.FileType.INBOX_LIST, true, true, true, context) {

			@Override
			protected void onDownloadNecessary() {}

			@Override
			protected void onDownloadStarted() {}

			@Override
			protected void onCallbackException(final Throwable t) {
				request = null;
				BugReportActivity.handleGlobalError(context, t);
			}

			@Override
			protected void onFailure(final RequestFailureType type, final Throwable t, final StatusLine status, final String readableMessage) {

				request = null;

				if(loadingView != null) loadingView.setDone(R.string.download_failed);

				final RRError error = General.getGeneralErrorForFailure(context, type, t, status, url.toString());
				General.UI_THREAD_HANDLER.post(new Runnable() {
					public void run() {
						notifications.addView(new ErrorView(InboxListingActivity.this, error));
					}
				});

				if(t != null) t.printStackTrace();
			}

			@Override protected void onProgress(final boolean authorizationInProgress, final long bytesRead, final long totalBytes) {}

			@Override
			protected void onSuccess(final CacheManager.ReadableCacheFile cacheFile, final long timestamp, final UUID session, final boolean fromCache, final String mimetype) {
				request = null;
			}

			@Override
			public void onJsonParseStarted(final JsonValue value, final long timestamp, final UUID session, final boolean fromCache) {

				if(loadingView != null) loadingView.setIndeterminate(R.string.download_downloading);

				// TODO pref (currently 10 mins)
				// TODO xml
				if(fromCache && RRTime.since(timestamp) > 10 * 60 * 1000) {
					General.UI_THREAD_HANDLER.post(new Runnable() {
						public void run() {
							final TextView cacheNotif = new TextView(context);
							cacheNotif.setText(context.getString(R.string.listing_cached) + RRTime.formatDateTime(timestamp, context));
							final int paddingPx = General.dpToPixels(context, 6);
							final int sidePaddingPx = General.dpToPixels(context, 10);
							cacheNotif.setPadding(sidePaddingPx, paddingPx, sidePaddingPx, paddingPx);
							cacheNotif.setTextSize(13f);
							notifications.addView(cacheNotif);
							adapter.notifyDataSetChanged();
						}
					});
				}

				// TODO {"error": 403} is received for unauthorized subreddits

				try {

					final JsonBufferedObject root = value.asObject();
					final JsonBufferedObject data = root.getObject("data");
					final JsonBufferedArray children = data.getArray("children");

					for(JsonValue child : children) {

						final RedditThing thing = child.asObject(RedditThing.class);

						switch(thing.getKind()) {
							case COMMENT:
								final RedditPreparedComment comment = new RedditPreparedComment(
										InboxListingActivity.this, thing.asComment(), timestamp, false, null, user, headerItems);
								itemHandler.sendMessage(General.handlerMessage(0, comment));

								break;

							case MESSAGE:
								final RedditPreparedMessage message = new RedditPreparedMessage(
										InboxListingActivity.this, thing.asMessage(), timestamp);
								itemHandler.sendMessage(General.handlerMessage(0, message));

								if(message.src.replies != null && message.src.replies.getType() == JsonValue.Type.OBJECT) {

									final JsonBufferedArray replies = message.src.replies.asObject().getObject("data").getArray("children");

									for(JsonValue childMsgValue : replies) {
										final RedditMessage childMsgRaw = childMsgValue.asObject(RedditThing.class).asMessage();
										final RedditPreparedMessage childMsg = new RedditPreparedMessage(InboxListingActivity.this, childMsgRaw, timestamp);
										itemHandler.sendMessage(General.handlerMessage(0, childMsg));
									}
								}

								break;

							default:
								throw new RuntimeException("Unknown item in list.");
						}
					}

				} catch (Throwable t) {
					notifyFailure(RequestFailureType.PARSE, t, null, "Parse failure");
					return;
				}

				if(loadingView != null) loadingView.setDone(R.string.download_done);
			}
		};

		cm.makeRequest(request);
	}

	@Override
	public void onBackPressed() {
		if(General.onBackPressed()) super.onBackPressed();
	}

	@Override
	public boolean onCreateOptionsMenu(final Menu menu) {
		menu.add(0, OPTIONS_MENU_MARK_ALL_AS_READ, 0, R.string.mark_all_as_read);
		return super.onCreateOptionsMenu(menu);
	}

	@Override
	public boolean onOptionsItemSelected(final MenuItem item) {
		switch(item.getItemId()) {
			case OPTIONS_MENU_MARK_ALL_AS_READ:

				RedditAPI.markAllAsRead(
						CacheManager.getInstance(this),
						new APIResponseHandler.ActionResponseHandler(this) {
							@Override
							protected void onSuccess() {
								General.quickToast(context, R.string.mark_all_as_read_success);
							}

							@Override
							protected void onCallbackException(final Throwable t) {
								BugReportActivity.addGlobalError(new RRError("Mark all as Read failed", "Callback exception", t));
							}

							@Override
							protected void onFailure(final RequestFailureType type, final Throwable t, final StatusLine status, final String readableMessage) {
								final RRError error = General.getGeneralErrorForFailure(context, type, t, status,
										"Reddit API action: Mark all as Read");
								General.UI_THREAD_HANDLER.post(new Runnable() {
									public void run() {
										General.showResultDialog(InboxListingActivity.this, error);
									}
								});
							}

							@Override
							protected void onFailure(final APIFailureType type) {

								final RRError error = General.getGeneralErrorForFailure(context, type);
								General.UI_THREAD_HANDLER.post(new Runnable() {
									public void run() {
										General.showResultDialog(InboxListingActivity.this, error);
									}
								});
							}
						},
						RedditAccountManager.getInstance(this).getDefaultAccount(),
						this);

				return true;
			case android.R.id.home:
				finish();
				return true;
			default:
				return super.onOptionsItemSelected(item);
		}
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/PostSubmitActivity.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.activities;

import android.app.ProgressDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.os.Bundle;
import android.text.InputType;
import android.view.KeyEvent;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.*;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.common.RRError;
import org.quantumbadger.redreader.fragments.MarkdownPreviewDialog;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;

import java.util.ArrayList;

// TODO save draft as static var (as in comments)
public class PostSubmitActivity extends BaseActivity {

	private Spinner typeSpinner, usernameSpinner;
	private EditText subredditEdit, titleEdit, textEdit;

	private static final String[] postTypes = {"Link", "Self"};

	@Override
	protected void onCreate(Bundle savedInstanceState) {

		PrefsUtility.applyTheme(this);

		super.onCreate(savedInstanceState);

		final LinearLayout layout = (LinearLayout) getLayoutInflater().inflate(R.layout.post_submit, null);

		typeSpinner = (Spinner)layout.findViewById(R.id.post_submit_type);
		usernameSpinner = (Spinner)layout.findViewById(R.id.post_submit_username);
		subredditEdit = (EditText)layout.findViewById(R.id.post_submit_subreddit);
		titleEdit = (EditText)layout.findViewById(R.id.post_submit_title);
		textEdit = (EditText)layout.findViewById(R.id.post_submit_body);

        final Intent intent = getIntent();
        if(intent != null) {

			if(intent.hasExtra("subreddit")) {

				final String subreddit = intent.getStringExtra("subreddit");

				if(subreddit != null && subreddit.length() > 0 && !subreddit.matches("/?(r/)?all/?") && subreddit.matches("/?(r/)?\\w+/?")) {
					subredditEdit.setText(subreddit);
				}

			} else if(Intent.ACTION_SEND.equalsIgnoreCase(intent.getAction()) && intent.hasExtra(Intent.EXTRA_TEXT)){
				final String url = intent.getStringExtra(Intent.EXTRA_TEXT);
				textEdit.setText(url);
			}

		} else if(savedInstanceState != null && savedInstanceState.containsKey("post_title")) {
			titleEdit.setText(savedInstanceState.getString("post_title"));
			textEdit.setText(savedInstanceState.getString("post_body"));
			subredditEdit.setText(savedInstanceState.getString("subreddit"));
			typeSpinner.setSelection(savedInstanceState.getInt("post_type"));
		}

		final ArrayList<RedditAccount> accounts = RedditAccountManager.getInstance(this).getAccounts();
		final ArrayList<String> usernames = new ArrayList<String>();

		for(RedditAccount account : accounts) {
			if(!account.isAnonymous()) {
				usernames.add(account.username);
			}
		}

		if(usernames.size() == 0) {
			General.quickToast(this, R.string.error_toast_notloggedin);
			finish();
		}

		usernameSpinner.setAdapter(new ArrayAdapter<String>(this, android.R.layout.simple_list_item_1, usernames));
		typeSpinner.setAdapter(new ArrayAdapter<String>(this, android.R.layout.simple_list_item_1, postTypes));

		// TODO remove the duplicate code here
        setHint();

        typeSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
			public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                setHint();
            }

			public void onNothingSelected(AdapterView<?> parent) {
			}
		});

		final ScrollView sv = new ScrollView(this);
		sv.addView(layout);
		setContentView(sv);
	}

    private void setHint() {
        if(typeSpinner.getSelectedItem().equals("Link")) {
            textEdit.setHint("URL"); // TODO string
            textEdit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
            textEdit.setSingleLine(true);
        } else {
            textEdit.setHint("Self Text"); // TODO string
            textEdit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_LONG_MESSAGE | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
            textEdit.setSingleLine(false);
        }
    }

    @Override
	protected void onSaveInstanceState(Bundle outState) {
		super.onSaveInstanceState(outState);
		outState.putString("post_title", titleEdit.getText().toString());
		outState.putString("post_body", textEdit.getText().toString());
		outState.putString("subreddit", subredditEdit.getText().toString());
		outState.putInt("post_type", typeSpinner.getSelectedItemPosition());
	}

	@Override
	public boolean onCreateOptionsMenu(Menu menu) {

		final MenuItem send = menu.add(R.string.comment_reply_send);
		send.setIcon(R.drawable.ic_action_send_dark);
		send.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);

		menu.add(R.string.comment_reply_preview);

		return true;
	}

	@Override
	public boolean onOptionsItemSelected(MenuItem item) {

		if(item.getTitle().equals(getString(R.string.comment_reply_send))) {
			final Intent captchaIntent = new Intent(this, CaptchaActivity.class);
			captchaIntent.putExtra("username", (String)usernameSpinner.getSelectedItem());
			startActivityForResult(captchaIntent, 0);

		} else if(item.getTitle().equals(getString(R.string.comment_reply_preview))) {
			MarkdownPreviewDialog.newInstance(textEdit.getText().toString()).show(getFragmentManager(), null);
		}

		return true;
	}

	@Override
	protected void onActivityResult(int requestCode, int resultCode, final Intent data) {
		super.onActivityResult(requestCode, resultCode, data);

		if(resultCode != RESULT_OK) return;

		final ProgressDialog progressDialog = new ProgressDialog(this);
		progressDialog.setTitle(getString(R.string.comment_reply_submitting_title));
		progressDialog.setMessage(getString(R.string.comment_reply_submitting_message));
		progressDialog.setIndeterminate(true);
		progressDialog.setCancelable(true);
		progressDialog.setCanceledOnTouchOutside(false);

		progressDialog.setOnCancelListener(new DialogInterface.OnCancelListener() {
			public void onCancel(final DialogInterface dialogInterface) {
				General.quickToast(PostSubmitActivity.this, getString(R.string.comment_reply_oncancel));
				progressDialog.dismiss();
			}
		});

		progressDialog.setOnKeyListener(new DialogInterface.OnKeyListener() {
			public boolean onKey(final DialogInterface dialogInterface, final int keyCode, final KeyEvent keyEvent) {

				if(keyCode == KeyEvent.KEYCODE_BACK) {
					General.quickToast(PostSubmitActivity.this, getString(R.string.comment_reply_oncancel));
					progressDialog.dismiss();
				}

				return true;
			}
		});

		final CacheManager cm = CacheManager.getInstance(this);

		final APIResponseHandler.ActionResponseHandler handler = new APIResponseHandler.ActionResponseHandler(this) {
			@Override
			protected void onSuccess() {
				General.UI_THREAD_HANDLER.post(new Runnable() {
					public void run() {
						if(progressDialog.isShowing()) progressDialog.dismiss();
						General.quickToast(PostSubmitActivity.this, getString(R.string.post_submit_done));
						finish();
					}
				});
			}

			@Override
			protected void onCallbackException(Throwable t) {
				BugReportActivity.handleGlobalError(PostSubmitActivity.this, t);
			}

			@Override
			protected void onFailure(RequestFailureType type, Throwable t, StatusLine status, String readableMessage) {

				final RRError error = General.getGeneralErrorForFailure(context, type, t, status, null);

				General.UI_THREAD_HANDLER.post(new Runnable() {
					public void run() {
						General.showResultDialog(PostSubmitActivity.this, error);
						if(progressDialog.isShowing()) progressDialog.dismiss();
					}
				});
			}

			@Override
			protected void onFailure(final APIFailureType type) {

				final RRError error = General.getGeneralErrorForFailure(context, type);

				General.UI_THREAD_HANDLER.post(new Runnable() {
					public void run() {
						General.showResultDialog(PostSubmitActivity.this, error);
						if(progressDialog.isShowing()) progressDialog.dismiss();
					}
				});
			}
		};

		final boolean is_self = !typeSpinner.getSelectedItem().equals("Link");

		final RedditAccount selectedAccount = RedditAccountManager.getInstance(this).getAccount((String) usernameSpinner.getSelectedItem());

		String subreddit = subredditEdit.getText().toString();
		final String title = titleEdit.getText().toString();
		final String text = textEdit.getText().toString();
		final String captchaId = data.getStringExtra("captchaId");
		final String captchaText = data.getStringExtra("captchaText");

		while(subreddit.startsWith("/")) subreddit = subreddit.substring(1);
		while(subreddit.startsWith("r/")) subreddit = subreddit.substring(2);
		while(subreddit.endsWith("/")) subreddit = subreddit.substring(0, subreddit.length() - 1);

		RedditAPI.submit(cm, handler, selectedAccount, is_self, subreddit, title, text, captchaId, captchaText, this);

		progressDialog.show();
	}

	@Override
	public void onBackPressed() {
		if(General.onBackPressed()) super.onBackPressed();
	}
}


File: src/main/java/org/quantumbadger/redreader/adapters/MainMenuAdapter.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.adapters;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.TypedArray;
import android.graphics.drawable.Drawable;
import android.preference.PreferenceManager;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.fragments.MainMenuFragment;
import org.quantumbadger.redreader.reddit.things.RedditSubreddit;
import org.quantumbadger.redreader.reddit.url.PostListingURL;
import org.quantumbadger.redreader.reddit.url.SubredditPostListURL;
import org.quantumbadger.redreader.views.list.ListItemView;
import org.quantumbadger.redreader.views.list.ListSectionHeader;
import org.quantumbadger.redreader.views.list.MainMenuItem;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.EnumSet;

public class MainMenuAdapter extends BaseAdapter {

	private final ArrayList<MainMenuItem> mainItems = new ArrayList<MainMenuItem>(16);
	private final ArrayList<MainMenuItem> subredditItems = new ArrayList<MainMenuItem>(100);
	private final RedditAccount user;
	private final MainMenuSelectionListener selectionListener;

	private final Drawable rrIconPerson, rrIconEnvOpen, rrIconSend, rrIconStarFilled, rrIconCross, rrIconThumbUp, rrIconThumbDown;

	private final Context context;

	public MainMenuAdapter(final Context context, final RedditAccount user, final MainMenuSelectionListener selectionListener) {

		this.user = user;
		this.selectionListener = selectionListener;
		this.context = context;

		final TypedArray attr = context.obtainStyledAttributes(new int[] {
				R.attr.rrIconPerson,
				R.attr.rrIconEnvOpen,
				R.attr.rrIconSend,
				R.attr.rrIconStarFilled,
				R.attr.rrIconCross,
				R.attr.rrIconThumbUp,
				R.attr.rrIconThumbDown
		});

		rrIconPerson = context.getResources().getDrawable(attr.getResourceId(0, 0));
		rrIconEnvOpen = context.getResources().getDrawable(attr.getResourceId(1, 0));
		rrIconSend = context.getResources().getDrawable(attr.getResourceId(2, 0));
		rrIconStarFilled = context.getResources().getDrawable(attr.getResourceId(3, 0));
		rrIconCross = context.getResources().getDrawable(attr.getResourceId(4, 0));
		rrIconThumbUp = context.getResources().getDrawable(attr.getResourceId(5, 0));
		rrIconThumbDown = context.getResources().getDrawable(attr.getResourceId(6, 0));

		build();
	}

	public int getCount() {
		return mainItems.size() + subredditItems.size();
	}

	public Object getItem(final int i) {
		return "item_" + i;
	}

	public long getItemId(final int i) {
		return i;
	}

	private MainMenuItem getItemInternal(final int id) {
		if(id < mainItems.size()) {
			return mainItems.get(id);
		} else {
			return subredditItems.get(id - mainItems.size());
		}
	}

	@Override
	public int getItemViewType(final int position) {
		return getItemInternal(position).isHeader ? 0 : 1;
	}

	@Override
	public int getViewTypeCount() {
		return 2;
	}

	@Override
	public boolean hasStableIds() {
		return true;
	}

	public View getView(final int i, View convertView, final ViewGroup viewGroup) {

		final MainMenuItem item = getItemInternal(i);

		if(convertView == null) {
			if(item.isHeader) {
				convertView = new ListSectionHeader(viewGroup.getContext());
			} else {
				convertView = new ListItemView(viewGroup.getContext());
			}
		}

		if(item.isHeader) {
			((ListSectionHeader)convertView).reset(item.title);
		} else {
			final boolean firstInSection = (i == 0) || getItemInternal(i - 1).isHeader;
			((ListItemView)convertView).reset(item.icon, item.title, firstInSection);
		}

		return convertView;
	}

	// Only run in UI thread
	private void build() {

		//items.add(new MainMenuItem("Reddit"));

		mainItems.add(makeItem(context.getString(R.string.mainmenu_frontpage), MainMenuFragment.MainMenuAction.FRONTPAGE, null, null));
		mainItems.add(makeItem(context.getString(R.string.mainmenu_all), MainMenuFragment.MainMenuAction.ALL, null, null));
		mainItems.add(makeItem(context.getString(R.string.mainmenu_custom), MainMenuFragment.MainMenuAction.CUSTOM, null, null));

		if(!user.isAnonymous()) {

			mainItems.add(new MainMenuItem(user.username));

			final SharedPreferences sharedPreferences = PreferenceManager.getDefaultSharedPreferences(context);
			final EnumSet<MainMenuFragment.MainMenuUserItems> mainMenuUserItems
					= PrefsUtility.pref_menus_mainmenu_useritems(context, sharedPreferences);

			if(mainMenuUserItems.contains(MainMenuFragment.MainMenuUserItems.PROFILE))
				mainItems.add(makeItem(context.getString(R.string.mainmenu_profile), MainMenuFragment.MainMenuAction.PROFILE, null, rrIconPerson));

			if(mainMenuUserItems.contains(MainMenuFragment.MainMenuUserItems.INBOX))
				mainItems.add(makeItem(context.getString(R.string.mainmenu_inbox), MainMenuFragment.MainMenuAction.INBOX, null, rrIconEnvOpen));

			if(mainMenuUserItems.contains(MainMenuFragment.MainMenuUserItems.SUBMITTED))
				mainItems.add(makeItem(context.getString(R.string.mainmenu_submitted), MainMenuFragment.MainMenuAction.SUBMITTED, null, rrIconSend));

			if(mainMenuUserItems.contains(MainMenuFragment.MainMenuUserItems.SAVED))
				mainItems.add(makeItem(context.getString(R.string.mainmenu_saved), MainMenuFragment.MainMenuAction.SAVED, null, rrIconStarFilled));

			if(mainMenuUserItems.contains(MainMenuFragment.MainMenuUserItems.HIDDEN))
				mainItems.add(makeItem(context.getString(R.string.mainmenu_hidden), MainMenuFragment.MainMenuAction.HIDDEN, null, rrIconCross));

			if(mainMenuUserItems.contains(MainMenuFragment.MainMenuUserItems.UPVOTED))
				mainItems.add(makeItem(context.getString(R.string.mainmenu_upvoted), MainMenuFragment.MainMenuAction.UPVOTED, null, rrIconThumbUp));

			if(mainMenuUserItems.contains(MainMenuFragment.MainMenuUserItems.DOWNVOTED))
				mainItems.add(makeItem(context.getString(R.string.mainmenu_downvoted), MainMenuFragment.MainMenuAction.DOWNVOTED, null, rrIconThumbDown));

			if(mainMenuUserItems.contains(MainMenuFragment.MainMenuUserItems.MODMAIL))
				mainItems.add(makeItem(context.getString(R.string.mainmenu_modmail), MainMenuFragment.MainMenuAction.MODMAIL, null, rrIconEnvOpen));
		}

		mainItems.add(new MainMenuItem(context.getString(R.string.mainmenu_header_subreddits)));

		//items.add(makeItem("Add Subreddit", null, null, null)); // TODO

		notifyDataSetChanged();
	}

	private MainMenuItem makeItem(final int nameRes, final MainMenuFragment.MainMenuAction action, final String actionName, final Drawable icon) {
		return makeItem(context.getString(nameRes), action, actionName, icon);
	}

	private MainMenuItem makeItem(final String name, final MainMenuFragment.MainMenuAction action, final String actionName, final Drawable icon) {

		final View.OnClickListener clickListener = new View.OnClickListener() {
			public void onClick(final View view) {
				selectionListener.onSelected(action, actionName);
			}
		};

		return new MainMenuItem(name, icon, clickListener, null);
	}

	private MainMenuItem makeSubredditItem(final String name) {

		final View.OnClickListener clickListener = new View.OnClickListener() {
			public void onClick(final View view) {
				try {
					selectionListener.onSelected((PostListingURL) SubredditPostListURL.getSubreddit(RedditSubreddit.getCanonicalName(name)));
				} catch(RedditSubreddit.InvalidSubredditNameException e) {
					throw new RuntimeException(e);
				}
			}
		};

		return new MainMenuItem(name, null, clickListener, null);
	}

	public void setSubreddits(final Collection<String> subscriptions) {

		final ArrayList<String> subscriptionsSorted = new ArrayList<String>(subscriptions);
		Collections.sort(subscriptionsSorted);

		General.UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {

				subredditItems.clear();

				for(final String subreddit : subscriptionsSorted) {
					try {
						subredditItems.add(makeSubredditItem(RedditSubreddit.stripRPrefix(subreddit)));
					} catch(RedditSubreddit.InvalidSubredditNameException e) {
						subredditItems.add(makeSubredditItem("Invalid: " + subreddit));
					}
				}

				notifyDataSetChanged();
			}
		});
	}

	@Override
	public boolean areAllItemsEnabled() {
		return false;
	}

	@Override
	public boolean isEnabled(final int position) {
		return !getItemInternal(position).isHeader;
	}

	public void clickOn(final int position) {
		if(position < getCount()) {
			getItemInternal(position).onClick(null);
		}
	}
}


File: src/main/java/org/quantumbadger/redreader/common/AndroidApi.java
package org.quantumbadger.redreader.common;

import android.os.Build;

public class AndroidApi {
	private static final int CURRENT_API_VERSION = android.os.Build.VERSION.SDK_INT;

	public static boolean isGreaterThanOrEqualTo(int apiVersion) {
		return CURRENT_API_VERSION >= apiVersion;
	}

	public static boolean isHoneyCombOrLater() {
		return isGreaterThanOrEqualTo(Build.VERSION_CODES.HONEYCOMB);
	}

	public static boolean isIceCreamSandwichOrLater() {
		return isGreaterThanOrEqualTo(Build.VERSION_CODES.ICE_CREAM_SANDWICH);
	}
}


File: src/main/java/org/quantumbadger/redreader/common/General.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.common;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.graphics.Typeface;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.*;
import android.util.Log;
import android.util.TypedValue;
import android.widget.Toast;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.activities.BugReportActivity;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.fragments.ErrorPropertiesDialog;
import org.quantumbadger.redreader.reddit.APIResponseHandler;

import java.io.*;
import java.net.URI;
import java.security.MessageDigest;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class General {

	public static final Handler UI_THREAD_HANDLER = new Handler(Looper.getMainLooper());

	private static long lastBackPress = -1;

	public static boolean onBackPressed() {

		if(lastBackPress < SystemClock.uptimeMillis() - 300) {
			lastBackPress = SystemClock.uptimeMillis();
			return true;
		}

		return false;
	}

	private static Typeface monoTypeface;

	public static Typeface getMonoTypeface(Context context) {

		if(monoTypeface == null) {
			monoTypeface = Typeface.createFromAsset(context.getAssets(), "fonts/VeraMono.ttf");
		}

		return monoTypeface;
	}

	public static Message handlerMessage(int what, Object obj) {
		final Message msg = Message.obtain();
		msg.what = what;
		msg.obj = obj;
		return msg;
	}

	public static void moveFile(final File src, final File dst) throws IOException {

		if(!src.renameTo(dst)) {

			copyFile(src, dst);

			if(!src.delete()) {
				src.deleteOnExit();
			}
		}
	}

	public static void copyFile(final File src, final File dst) throws IOException {

		final FileInputStream fis = new FileInputStream(src);
		final FileOutputStream fos = new FileOutputStream(dst);

		copyFile(fis, fos);
	}

	public static void copyFile(final InputStream fis, final File dst) throws IOException {
		final FileOutputStream fos = new FileOutputStream(dst);
		copyFile(fis, fos);
	}

	public static void copyFile(final InputStream fis, final OutputStream fos) throws IOException {

		final byte[] buf = new byte[32 * 1024];

		int bytesRead;
		while((bytesRead = fis.read(buf)) > 0) {
			fos.write(buf, 0, bytesRead);
		}

		fis.close();
		fos.close();
	}

	public static boolean isCacheDiskFull(final Context context) {
		final StatFs stat = new StatFs(getBestCacheDir(context).getPath());
		return (long)stat.getBlockSize() *(long)stat.getAvailableBlocks() < 128 * 1024 * 1024;
	}

	public static File getBestCacheDir(final Context context) {

		final File externalCacheDir = context.getExternalCacheDir();

		if(externalCacheDir != null) {
			return externalCacheDir;
		}

		return context.getCacheDir();
	}

	public static int dpToPixels(final Context context, final float dp) {
		return Math.round(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, dp, context.getResources().getDisplayMetrics()));
	}

	public static void quickToast(final Context context, final int textRes) {
		quickToast(context, context.getString(textRes));
	}

	public static void quickToast(final Context context, final String text) {
		UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				Toast.makeText(context, text, Toast.LENGTH_LONG).show();
			}
		});
	}

	public static void quickToast(final Context context, final String text, final int duration) {
		UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				Toast.makeText(context, text, duration).show();
			}
		});
	}

	public static boolean isTablet(final Context context, final SharedPreferences sharedPreferences) {

		final PrefsUtility.AppearanceTwopane pref = PrefsUtility.appearance_twopane(context, sharedPreferences);

		switch(pref) {
			case AUTO:
				return (context.getResources().getConfiguration().screenLayout &
						Configuration.SCREENLAYOUT_SIZE_MASK) ==
						Configuration.SCREENLAYOUT_SIZE_XLARGE;
			case NEVER:
				return false;
			case FORCE:
				return true;
			default:
				BugReportActivity.handleGlobalError(context, "Unknown AppearanceTwopane value " + pref.name());
				return false;
		}
	}

	public static boolean isConnectionWifi(final Context context){
		final ConnectivityManager cm = (ConnectivityManager)context.getSystemService(Context.CONNECTIVITY_SERVICE);
		final NetworkInfo info = cm.getNetworkInfo(ConnectivityManager.TYPE_WIFI);
		return info != null && info.getDetailedState() == NetworkInfo.DetailedState.CONNECTED;
	}

	public static RRError getGeneralErrorForFailure(Context context, RequestFailureType type, Throwable t, StatusLine status, String url) {

		final int title, message;

		switch (type) {
			case CANCELLED:
				title = R.string.error_cancelled_title;
				message = R.string.error_cancelled_message;
				break;
			case PARSE:
				title = R.string.error_parse_title;
				message = R.string.error_parse_message;
				break;
			case CACHE_MISS:
				title = R.string.error_unexpected_cache_title;
				message = R.string.error_unexpected_cache_message;
				break;
			case STORAGE:
				title = R.string.error_unexpected_storage_title;
				message = R.string.error_unexpected_storage_message;
				break;
			case CONNECTION:
				// TODO check network and customise message
				title = R.string.error_connection_title;
				message = R.string.error_connection_message;
				break;
			case MALFORMED_URL:
				title = R.string.error_malformed_url_title;
				message = R.string.error_malformed_url_message;
				break;
			case DISK_SPACE:
				title = R.string.error_disk_space_title;
				message = R.string.error_disk_space_message;
				break;
			case REQUEST:

				if(status != null) {
					switch (status.getStatusCode()) {
						case 400:
						case 401:
						case 403:
							title = R.string.error_403_title;
							message = R.string.error_403_message;
							break;
						case 404:
							title = R.string.error_404_title;
							message = R.string.error_404_message;
							break;
						case 502:
						case 503:
						case 504:
							title = R.string.error_redditdown_title;
							message = R.string.error_redditdown_message;
							break;
						default:
							title = R.string.error_unknown_api_title;
							message = R.string.error_unknown_api_message;
							break;
					}
				} else {
					title = R.string.error_unknown_api_title;
					message = R.string.error_unknown_api_message;
				}

				break;
			case REDDIT_REDIRECT:
				title = R.string.error_403_title;
				message = R.string.error_403_message;
				break;

			default:
				title = R.string.error_unknown_title;
				message = R.string.error_unknown_message;
				break;
		}

		return new RRError(context.getString(title), context.getString(message), t, status, url);
	}

	public static RRError getGeneralErrorForFailure(Context context, final APIResponseHandler.APIFailureType type) {

		final int title, message;

		switch(type) {

			case INVALID_USER:
				title = R.string.error_403_title;
				message = R.string.error_403_message;
				break;

			case BAD_CAPTCHA:
				title = R.string.error_bad_captcha_title;
				message = R.string.error_bad_captcha_message;
				break;

			case NOTALLOWED:
				title = R.string.error_403_title;
				message = R.string.error_403_message;
				break;

			case SUBREDDIT_REQUIRED:
				title = R.string.error_subreddit_required_title;
				message = R.string.error_subreddit_required_message;
				break;

			default:
				title = R.string.error_unknown_api_title;
				message = R.string.error_unknown_api_message;
				break;
		}

		return new RRError(context.getString(title), context.getString(message));
	}

	// TODO add button to show more detail
	public static void showResultDialog(final Activity context, final RRError error) {
		UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				final AlertDialog.Builder alertBuilder = new AlertDialog.Builder(context);
				alertBuilder.setNeutralButton(R.string.dialog_close, null);
				alertBuilder.setNegativeButton(R.string.button_moredetail, new DialogInterface.OnClickListener() {
					public void onClick(DialogInterface dialog, int which) {
						ErrorPropertiesDialog.newInstance(error).show(context.getFragmentManager(), "ErrorPropertiesDialog");
					}
				});
				alertBuilder.setTitle(error.title);
				alertBuilder.setMessage(error.message);
				alertBuilder.create().show();
			}
		});
	}

	private static final Pattern urlPattern = Pattern.compile("^(https?)://([^/]+)/+([^\\?#]+)((?:\\?[^#]+)?)((?:#.+)?)$");

	public static URI uriFromString(String url) {

		try {
			return new URI(url);

		} catch(Throwable t1) {
			try {

				Log.i("RR DEBUG uri", "Beginning aggressive parse of '" + url + "'");

				final Matcher urlMatcher = urlPattern.matcher(url);

				if(urlMatcher.find()) {

					final String scheme = urlMatcher.group(1);
					final String authority = urlMatcher.group(2);
					final String path = urlMatcher.group(3).length() == 0 ? null : "/" + urlMatcher.group(3);
					final String query = urlMatcher.group(4).length() == 0 ? null : urlMatcher.group(4);
					final String fragment = urlMatcher.group(5).length() == 0 ? null : urlMatcher.group(5);

					try {
						return new URI(scheme, authority, path, query, fragment);
					} catch(Throwable t3) {

						if(path != null && path.contains(" ")) {
							return new URI(scheme, authority, path.replace(" ", "%20"), query, fragment);
						} else {
							return null;
						}
					}

				} else {
					return null;
				}

			} catch(Throwable t2) {
				return null;
			}
		}
	}

	public static String sha1(final byte[] plaintext) {

		final MessageDigest digest;
		try {
			digest = MessageDigest.getInstance("SHA-1");
		} catch(Exception e) {
			throw new RuntimeException(e);
		}

		digest.update(plaintext, 0, plaintext.length);
		final byte[] hash = digest.digest();
		final StringBuilder result = new StringBuilder(hash.length * 2);
		for(byte b : hash) result.append(String.format("%02X", b));
		return result.toString();
	}

	// Adapted from Android:
	// http://grepcode.com/file/repository.grepcode.com/java/ext/com.google.android/android/4.1.1_r1/android/net/Uri.java?av=f
	public static Set<String> getUriQueryParameterNames(final Uri uri) {

		if(uri.isOpaque()) {
			throw new UnsupportedOperationException("This isn't a hierarchical URI.");
		}

		final String query = uri.getEncodedQuery();
		if(query == null) {
			return Collections.emptySet();
		}

		final Set<String> names = new LinkedHashSet<String>();
		int pos = 0;
		while(pos < query.length()) {
			int next = query.indexOf('&', pos);
			int end = (next == -1) ? query.length() : next;

			int separator = query.indexOf('=', pos);
			if (separator > end || separator == -1) {
				separator = end;
			}

			String name = query.substring(pos, separator);
			names.add(Uri.decode(name));

			// Move start to end of name.
			pos = end + 1;
		}

		return Collections.unmodifiableSet(names);
	}

	public static int divideCeil(int num, int divisor) {
		return (num + divisor - 1) / divisor;
	}

	public static void checkThisIsUIThread() {
		if(!isThisUIThread()) {
			throw new RuntimeException("Called from invalid thread");
		}
	}

	public static boolean isThisUIThread() {
		return Looper.getMainLooper().getThread() == Thread.currentThread();
	}

	public static <E> List<E> listOfOne(E obj) {
		final ArrayList<E> result = new ArrayList<E>(1);
		result.add(obj);
		return result;
	}
}


File: src/main/java/org/quantumbadger/redreader/common/PrefsUtility.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.common;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.Resources;
import android.preference.PreferenceManager;
import android.util.DisplayMetrics;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.activities.OptionsMenuUtility;
import org.quantumbadger.redreader.fragments.MainMenuFragment;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedPost;
import org.quantumbadger.redreader.reddit.url.PostCommentListingURL;

import java.util.*;

public final class PrefsUtility {

	private static <E> Set<E> setFromArray(E[] data) {
		final HashSet<E> result = new HashSet<E>(data.length);
		Collections.addAll(result, data);
		return result;
	}

	private static String getString(final int id, final String defaultValue, final Context context, final SharedPreferences sharedPreferences) {
		return sharedPreferences.getString(context.getString(id), defaultValue);
	}

	public static Set<String> getStringSet(final int id, final int defaultArrayRes, final Context context, final SharedPreferences sharedPreferences) {
		return sharedPreferences.getStringSet(context.getString(id), setFromArray(context.getResources().getStringArray(defaultArrayRes)));
	}

	private static boolean getBoolean(final int id, final boolean defaultValue, final Context context, final SharedPreferences sharedPreferences) {
		return sharedPreferences.getBoolean(context.getString(id), defaultValue);
	}

	private static long getLong(final int id, final long defaultValue, final Context context, final SharedPreferences sharedPreferences) {
		return sharedPreferences.getLong(context.getString(id), defaultValue);
	}

	public static boolean isReLayoutRequired(final Context context, final String key) {
		return context.getString(R.string.pref_appearance_twopane_key).equals(key)
				|| context.getString(R.string.pref_appearance_theme_key).equals(key)
				|| context.getString(R.string.pref_appearance_solidblack_2_key).equals(key)
				|| context.getString(R.string.pref_menus_mainmenu_useritems_key).equals(key);
	}

	public static boolean isRefreshRequired(final Context context, final String key) {
		return key.startsWith("pref_appearance")
				|| key.equals(context.getString(R.string.pref_behaviour_fling_post_left_key))
				|| key.equals(context.getString(R.string.pref_behaviour_fling_post_right_key))
				|| key.equals(context.getString(R.string.pref_behaviour_nsfw_key))
				|| key.equals(context.getString(R.string.pref_behaviour_postcount_key));
	}

	public static boolean isRestartRequired(Context context, String key) {
		return context.getString(R.string.pref_appearance_theme_key).equals(key)
				|| context.getString(R.string.pref_appearance_solidblack_2_key).equals(key)
				|| context.getString(R.string.pref_appearance_langforce_key).equals(key)
				|| context.getString(R.string.pref_behaviour_bezel_toolbar_swipezone_key).equals(key);
	}

	///////////////////////////////
	// pref_appearance
	///////////////////////////////

	// pref_appearance_twopane

	public static enum AppearanceTwopane {
		NEVER, AUTO, FORCE
	}

	public static AppearanceTwopane appearance_twopane(final Context context, final SharedPreferences sharedPreferences) {
		return AppearanceTwopane.valueOf(getString(R.string.pref_appearance_twopane_key, "auto", context, sharedPreferences).toUpperCase());
	}

	public static enum AppearanceTheme {
		RED, GREEN, BLUE, LTBLUE, ORANGE, GRAY, NIGHT
	}

	public static boolean isNightMode(final Context context) {
		return appearance_theme(context, PreferenceManager.getDefaultSharedPreferences(context)) == AppearanceTheme.NIGHT;
	}

	public static AppearanceTheme appearance_theme(final Context context, final SharedPreferences sharedPreferences) {
		return AppearanceTheme.valueOf(getString(R.string.pref_appearance_theme_key, "red", context, sharedPreferences).toUpperCase());
	}

	public static void applyTheme(Activity activity) {

		final SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(activity);

		final AppearanceTheme theme = appearance_theme(activity, prefs);

		switch(theme) {
			case RED:
				activity.setTheme(R.style.RR_Light_Red);
				break;

			case GREEN:
				activity.setTheme(R.style.RR_Light_Green);
				break;

			case BLUE:
				activity.setTheme(R.style.RR_Light_Blue);
				break;

			case LTBLUE:
				activity.setTheme(R.style.RR_Light_LtBlue);
				break;

			case ORANGE:
				activity.setTheme(R.style.RR_Light_Orange);
				break;

			case GRAY:
				activity.setTheme(R.style.RR_Light_DarkActionBar);
				break;

			case NIGHT:
				activity.setTheme(R.style.RR_Dark);
				break;
		}

		final String lang = getString(R.string.pref_appearance_langforce_key, "auto", activity, prefs);

		final Resources res = activity.getResources();
		final DisplayMetrics dm = res.getDisplayMetrics();
		final android.content.res.Configuration conf = res.getConfiguration();

		if(!lang.equals("auto")) {
			conf.locale = new Locale(lang);
		} else {
			conf.locale = Locale.getDefault();
		}

		res.updateConfiguration(conf, dm);
	}

	public static boolean appearance_solidblack(final Context context, final SharedPreferences sharedPreferences) {
		return getBoolean(R.string.pref_appearance_solidblack_2_key, true, context, sharedPreferences);
	}

	public static enum AppearanceThumbnailsShow {
		NEVER, WIFIONLY, ALWAYS
	}

	public static AppearanceThumbnailsShow appearance_thumbnails_show(final Context context, final SharedPreferences sharedPreferences) {

		if(!getBoolean(R.string.pref_appearance_thumbnails_show_key, true, context,  sharedPreferences)) {
			return AppearanceThumbnailsShow.NEVER;
		} else if(getBoolean(R.string.pref_appearance_thumbnails_wifionly_key, false, context, sharedPreferences)) {
			return AppearanceThumbnailsShow.WIFIONLY;
		} else {
			return AppearanceThumbnailsShow.ALWAYS;
		}
	}

	public static boolean appearance_thumbnails_nsfw_show(final Context context, final SharedPreferences sharedPreferences) {
		return getBoolean(R.string.pref_appearance_thumbnails_nsfw_show_key, false, context, sharedPreferences);
	}

	public static float appearance_fontscale_comments(final Context context, final SharedPreferences sharedPreferences) {
		return Float.valueOf(getString(R.string.pref_appearance_fontscale_comments_key, "1", context,  sharedPreferences));
	}

	public static float appearance_fontscale_posts(final Context context, final SharedPreferences sharedPreferences) {
		return Float.valueOf(getString(R.string.pref_appearance_fontscale_posts_key, "1", context,  sharedPreferences));
	}

	public static boolean pref_appearance_linkbuttons(final Context context, final SharedPreferences sharedPreferences) {
		return getBoolean(R.string.pref_appearance_linkbuttons_key, true, context, sharedPreferences);
	}

	public static boolean pref_appearance_indentlines(final Context context, final SharedPreferences sharedPreferences) {
		return getBoolean(R.string.pref_appearance_indentlines_key, false, context, sharedPreferences);
	}

	public static enum AppearanceCommentHeaderItems {
		AUTHOR, FLAIR, SCORE, AGE, GOLD
	}

	public static EnumSet<AppearanceCommentHeaderItems> appearance_comment_header_items(final Context context, final SharedPreferences sharedPreferences) {

		final Set<String> strings = getStringSet(R.string.pref_appearance_comment_header_items_key, R.array.pref_appearance_comment_header_items_default, context, sharedPreferences);

		final EnumSet<AppearanceCommentHeaderItems> result = EnumSet.noneOf(AppearanceCommentHeaderItems.class);
		for(String s : strings) {

			if(s.equalsIgnoreCase("ups_downs")) continue;

			try {
				result.add(AppearanceCommentHeaderItems.valueOf(s.toUpperCase()));
			} catch(IllegalArgumentException e) {
				// Ignore -- this option no longer exists
			}
		}

		return result;
	}

	///////////////////////////////
	// pref_behaviour
	///////////////////////////////

	public static boolean pref_behaviour_skiptofrontpage(final Context context, final SharedPreferences sharedPreferences) {
		return getBoolean(R.string.pref_behaviour_skiptofrontpage_key, false, context, sharedPreferences);
	}

	public static boolean pref_behaviour_useinternalbrowser(final Context context, final SharedPreferences sharedPreferences) {
		return getBoolean(R.string.pref_behaviour_useinternalbrowser_key, true, context, sharedPreferences);
	}

    public static boolean pref_behaviour_notifications(final Context context, final SharedPreferences sharedPreferences) {
        return getBoolean(R.string.pref_behaviour_notifications_key, true, context, sharedPreferences);
    }

	public static int pref_behaviour_bezel_toolbar_swipezone_dp(final Context context, final SharedPreferences sharedPreferences) {
		try {
			return Integer.parseInt(getString(R.string.pref_behaviour_bezel_toolbar_swipezone_key, "10", context, sharedPreferences));
		} catch(Throwable _) {
			return 10;
		}
	}

	// pref_behaviour_gifview_mode

	public enum GifViewMode {
		INTERNAL_MOVIE,
		INTERNAL_LEGACY,
		INTERNAL_BROWSER,
		EXTERNAL_BROWSER
	}

	public static GifViewMode pref_behaviour_gifview_mode(final Context context, final SharedPreferences sharedPreferences) {
		return GifViewMode.valueOf(getString(R.string.pref_behaviour_gifview_mode_key, "internal_movie", context, sharedPreferences).toUpperCase());
	}

	// pref_behaviour_fling_post

	public enum PostFlingAction {
		UPVOTE, DOWNVOTE, SAVE, HIDE, COMMENTS, LINK, ACTION_MENU, BROWSER, DISABLED
	}

	public static PostFlingAction pref_behaviour_fling_post_left(final Context context, final SharedPreferences sharedPreferences) {
		return PostFlingAction.valueOf(getString(R.string.pref_behaviour_fling_post_left_key, "downvote", context, sharedPreferences).toUpperCase());
	}

	public static PostFlingAction pref_behaviour_fling_post_right(final Context context, final SharedPreferences sharedPreferences) {
		return PostFlingAction.valueOf(getString(R.string.pref_behaviour_fling_post_right_key, "upvote", context, sharedPreferences).toUpperCase());
	}

	public static enum CommentAction {
		COLLAPSE, ACTION_MENU, NOTHING
	}

	public static CommentAction pref_behaviour_actions_comment_tap(final Context context, final SharedPreferences sharedPreferences) {
		return CommentAction.valueOf(getString(R.string.pref_behaviour_actions_comment_tap_key, "action_menu", context, sharedPreferences).toUpperCase());
	}

	public static PostCommentListingURL.Sort pref_behaviour_commentsort(final Context context, final SharedPreferences sharedPreferences) {
		return PostCommentListingURL.Sort.valueOf(getString(R.string.pref_behaviour_commentsort_key, "best", context, sharedPreferences).toUpperCase());
	}

	public static boolean pref_behaviour_nsfw(final Context context, final SharedPreferences sharedPreferences) {
		return getBoolean(R.string.pref_behaviour_nsfw_key, false, context, sharedPreferences);
	}

	public static enum PostCount {
		R25, R50, R100, ALL
	}

	public static PostCount pref_behaviour_post_count(final Context context, final SharedPreferences sharedPreferences) {
		return PostCount.valueOf(getString(R.string.pref_behaviour_postcount_key, "ALL", context, sharedPreferences));
	}

	public static enum ScreenOrientation {
		AUTO, PORTRAIT, LANDSCAPE
	}

	public static ScreenOrientation pref_behaviour_screen_orientation(final Context context, final SharedPreferences sharedPreferences) {
		return ScreenOrientation.valueOf(getString(R.string.pref_behaviour_screenorientation_key, ScreenOrientation.AUTO.name(), context, sharedPreferences).toUpperCase());
	}

	///////////////////////////////
	// pref_cache
	///////////////////////////////

	// pref_cache_maxage

	public static HashMap<Integer, Long> pref_cache_maxage(final Context context, final SharedPreferences sharedPreferences) {

		final HashMap<Integer, Long> result = new HashMap<Integer, Long>();

		final long maxAgeListing = 1000L * 60L * 60L * Long.valueOf(getString(R.string.pref_cache_maxage_listing_key, "168", context, sharedPreferences));
		final long maxAgeThumb = 1000L * 60L * 60L * Long.valueOf(getString(R.string.pref_cache_maxage_thumb_key, "168", context, sharedPreferences));
		final long maxAgeImage = 1000L * 60L * 60L * Long.valueOf(getString(R.string.pref_cache_maxage_image_key, "72", context, sharedPreferences));

		result.put(Constants.FileType.POST_LIST, maxAgeListing);
		result.put(Constants.FileType.COMMENT_LIST, maxAgeListing);
		result.put(Constants.FileType.SUBREDDIT_LIST, maxAgeListing);
		result.put(Constants.FileType.USER_ABOUT, maxAgeListing);
		result.put(Constants.FileType.INBOX_LIST, maxAgeListing);
		result.put(Constants.FileType.THUMBNAIL, maxAgeThumb);
		result.put(Constants.FileType.IMAGE, maxAgeImage);

		return result;
	}

	// pref_cache_precache_images

	public static enum CachePrecacheImages {
		NEVER, WIFIONLY, ALWAYS
	}

	public static CachePrecacheImages cache_precache_images(final Context context, final SharedPreferences sharedPreferences) {

		if(!getBoolean(R.string.pref_cache_precache_images_key, true, context,  sharedPreferences)) {
			return CachePrecacheImages.NEVER;
		} else if(getBoolean(R.string.pref_cache_precache_images_wifionly_key, false, context, sharedPreferences)) {
			return CachePrecacheImages.WIFIONLY;
		} else {
			return CachePrecacheImages.ALWAYS;
		}
	}

	///////////////////////////////
	// pref_network
	///////////////////////////////

	// pref_network_https

	public static boolean httpsEnabled = true;

	public static boolean network_https(final Context context, final SharedPreferences sharedPreferences) {
		httpsEnabled = getBoolean(R.string.pref_network_https_key, true, context, sharedPreferences);
		return httpsEnabled;
	}

	///////////////////////////////
	// pref_menus
	///////////////////////////////

	public static EnumSet<RedditPreparedPost.Action> pref_menus_post_context_items(final Context context, final SharedPreferences sharedPreferences) {

		final Set<String> strings = getStringSet(R.string.pref_menus_post_context_items_key, R.array.pref_menus_post_context_items_return, context, sharedPreferences);

		final EnumSet<RedditPreparedPost.Action> result = EnumSet.noneOf(RedditPreparedPost.Action.class);
		for(String s : strings) result.add(RedditPreparedPost.Action.valueOf(s.toUpperCase()));

		return result;
	}

	public static EnumSet<RedditPreparedPost.Action> pref_menus_post_toolbar_items(final Context context, final SharedPreferences sharedPreferences) {

		final Set<String> strings = getStringSet(R.string.pref_menus_post_toolbar_items_key, R.array.pref_menus_post_toolbar_items_return, context, sharedPreferences);

		final EnumSet<RedditPreparedPost.Action> result = EnumSet.noneOf(RedditPreparedPost.Action.class);
		for(String s : strings) result.add(RedditPreparedPost.Action.valueOf(s.toUpperCase()));

		return result;
	}

	public static EnumSet<MainMenuFragment.MainMenuUserItems> pref_menus_mainmenu_useritems(final Context context, final SharedPreferences sharedPreferences) {

		final Set<String> strings = getStringSet(R.string.pref_menus_mainmenu_useritems_key, R.array.pref_menus_mainmenu_useritems_items_default, context, sharedPreferences);

		final EnumSet<MainMenuFragment.MainMenuUserItems> result = EnumSet.noneOf(MainMenuFragment.MainMenuUserItems.class);
		for(String s : strings) result.add(MainMenuFragment.MainMenuUserItems.valueOf(s.toUpperCase()));

		return result;
	}

	public static EnumSet<OptionsMenuUtility.OptionsMenuItemsPref> pref_menus_optionsmenu_items(final Context context, final SharedPreferences sharedPreferences) {

		final Set<String> strings = getStringSet(R.string.pref_menus_optionsmenu_items_key, R.array.pref_menus_optionsmenu_items_items_default, context, sharedPreferences);

		final EnumSet<OptionsMenuUtility.OptionsMenuItemsPref> result = EnumSet.noneOf(OptionsMenuUtility.OptionsMenuItemsPref.class);
		for(String s : strings) result.add(OptionsMenuUtility.OptionsMenuItemsPref.valueOf(s.toUpperCase()));

		return result;
	}
}


File: src/main/java/org/quantumbadger/redreader/fragments/AccountListDialog.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.fragments;

import android.app.AlertDialog;
import android.app.Dialog;
import android.app.DialogFragment;
import android.app.ProgressDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ListView;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountChangeListener;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.activities.OAuthLoginActivity;
import org.quantumbadger.redreader.adapters.AccountListAdapter;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.RRError;
import org.quantumbadger.redreader.reddit.api.RedditOAuth;

import java.util.concurrent.atomic.AtomicBoolean;

public class AccountListDialog extends DialogFragment
		implements RedditAccountChangeListener {

	// Workaround for HoloEverywhere bug?
	private volatile boolean alreadyCreated = false;

	private ListView lv;

	@Override
	public void onActivityResult(final int requestCode, final int resultCode, final Intent data) {

		if(requestCode == 123 && requestCode == resultCode && data.hasExtra("url")) {

			final ProgressDialog progressDialog = new ProgressDialog(getActivity());
			progressDialog.setTitle(R.string.accounts_loggingin);
			progressDialog.setMessage(getString(R.string.accounts_loggingin_msg));
			progressDialog.setIndeterminate(true);
			progressDialog.setCancelable(true);
			progressDialog.setCanceledOnTouchOutside(false);

			final AtomicBoolean cancelled = new AtomicBoolean(false);

			progressDialog.setOnCancelListener(new DialogInterface.OnCancelListener() {
				public void onCancel(final DialogInterface dialogInterface) {
					cancelled.set(true);
					progressDialog.dismiss();
				}
			});

			progressDialog.setOnKeyListener(new DialogInterface.OnKeyListener() {
				public boolean onKey(final DialogInterface dialogInterface, final int keyCode, final KeyEvent keyEvent) {

					if(keyCode == KeyEvent.KEYCODE_BACK) {
						cancelled.set(true);
						progressDialog.dismiss();
					}

					return true;
				}
			});

			progressDialog.show();

			RedditOAuth.loginAsynchronous(
					getActivity().getApplicationContext(),
					Uri.parse(data.getStringExtra("url")),

					new RedditOAuth.LoginListener() {
						@Override
						public void onLoginSuccess(final RedditAccount account) {
							General.UI_THREAD_HANDLER.post(new Runnable() {
								@Override
								public void run() {
									progressDialog.dismiss();
									if(cancelled.get()) return;

									final AlertDialog.Builder alertBuilder = new AlertDialog.Builder(getActivity());
									alertBuilder.setNeutralButton(R.string.dialog_close, new DialogInterface.OnClickListener() {
										public void onClick(DialogInterface dialog, int which) {}
									});

									final Context context = getActivity().getApplicationContext();
									alertBuilder.setTitle(context.getString(R.string.general_success));
									alertBuilder.setMessage(context.getString(R.string.message_nowloggedin));

									final AlertDialog alertDialog = alertBuilder.create();
									alertDialog.show();
								}
							});
						}

						@Override
						public void onLoginFailure(final RedditOAuth.LoginError error, final RRError details) {
							General.UI_THREAD_HANDLER.post(new Runnable() {
								@Override
								public void run() {
									progressDialog.dismiss();
									if(cancelled.get()) return;
									General.showResultDialog(getActivity(), details);
								}
							});
						}
					});
		}
	}

	@Override
	public Dialog onCreateDialog(final Bundle savedInstanceState) {

		super.onCreateDialog(savedInstanceState);

		if(alreadyCreated) return getDialog();
		alreadyCreated = true;

		final Context context = getActivity();

		final AlertDialog.Builder builder = new AlertDialog.Builder(getActivity());
		builder.setTitle(context.getString(R.string.options_accounts_long));

		lv = new ListView(context);
		builder.setView(lv);

		lv.setAdapter(new AccountListAdapter(context));

		RedditAccountManager.getInstance(context).addUpdateListener(this);

		lv.setOnItemClickListener(new AdapterView.OnItemClickListener() {
			public void onItemClick(AdapterView<?> adapterView, View view, int position, final long id) {

				if(position == 0) {

					final Intent loginIntent = new Intent(context, OAuthLoginActivity.class);
					startActivityForResult(loginIntent, 123);

				} else {

					final RedditAccount account = (RedditAccount)lv.getAdapter().getItem(position);

					final String[] items = account.isAnonymous()
							? new String[] {getString(R.string.accounts_setactive)}
							: new String[] {
								getString(R.string.accounts_setactive),
								getString(R.string.accounts_delete)
							};

					final AlertDialog.Builder builder = new AlertDialog.Builder(context);

					builder.setItems(items, new DialogInterface.OnClickListener() {
						public void onClick(DialogInterface dialog, int which) {

							final String selected = items[which];

							if(selected.equals(getString(R.string.accounts_setactive))) {
								RedditAccountManager.getInstance(context).setDefaultAccount(account);

							} else if(selected.equals(getString(R.string.accounts_delete))) {
								new AlertDialog.Builder(context)
										.setTitle(R.string.accounts_delete)
										.setMessage(R.string.accounts_delete_sure)
										.setPositiveButton(R.string.accounts_delete,
												new DialogInterface.OnClickListener() {
													public void onClick(final DialogInterface dialog, final int which) {
														RedditAccountManager.getInstance(context).deleteAccount(account);
													}
												})
										.setNegativeButton(R.string.dialog_cancel, null)
										.show();

							}
						}
					});

					builder.setNeutralButton(R.string.dialog_cancel, null);

					final AlertDialog alert = builder.create();
					alert.setTitle(account.isAnonymous() ? getString(R.string.accounts_anon) : account.username);
					alert.setCanceledOnTouchOutside(true);
					alert.show();

				}
			}
		});

		builder.setNeutralButton(getActivity().getString(R.string.dialog_close), null);

		return builder.create();
	}

	public void onRedditAccountChanged() {
		General.UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				lv.setAdapter(new AccountListAdapter(getActivity()));
			}
		});
	}
}


File: src/main/java/org/quantumbadger/redreader/fragments/MainMenuFragment.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.fragments;

import android.app.Fragment;
import android.content.Context;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.LinearLayout;
import android.widget.ListView;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.adapters.MainMenuAdapter;
import org.quantumbadger.redreader.adapters.MainMenuSelectionListener;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.RRError;
import org.quantumbadger.redreader.common.TimestampBound;
import org.quantumbadger.redreader.io.RequestResponseHandler;
import org.quantumbadger.redreader.reddit.api.RedditSubredditSubscriptionManager;
import org.quantumbadger.redreader.reddit.api.SubredditRequestFailure;
import org.quantumbadger.redreader.reddit.url.PostListingURL;
import org.quantumbadger.redreader.views.liststatus.ErrorView;
import org.quantumbadger.redreader.views.liststatus.LoadingView;

import java.util.Collection;
import java.util.HashSet;

public class MainMenuFragment extends Fragment implements MainMenuSelectionListener, RedditSubredditSubscriptionManager.SubredditSubscriptionStateChangeListener {

	private MainMenuAdapter adapter;

	private LinearLayout notifications;
	private LoadingView loadingView;

	private RedditAccount user;
	private Context context;

	private boolean force;

	public enum MainMenuAction {
		FRONTPAGE, PROFILE, INBOX, SUBMITTED, UPVOTED, DOWNVOTED, SAVED, MODMAIL, HIDDEN, CUSTOM, ALL
	}

	public enum MainMenuUserItems {
		PROFILE, INBOX, SUBMITTED, SAVED, HIDDEN, UPVOTED, DOWNVOTED, MODMAIL
	}

	public static MainMenuFragment newInstance(final boolean force) {

		final MainMenuFragment f = new MainMenuFragment();

		final Bundle bundle = new Bundle(1);
		bundle.putBoolean("force", force);
		f.setArguments(bundle);

		return f;
	}

	@Override
	public void onCreate(final Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		force = getArguments().getBoolean("force");
	}

	@Override
	public View onCreateView(final LayoutInflater inflater, final ViewGroup container, final Bundle savedInstanceState) {

		if(container != null) {
			context = container.getContext(); // TODO just use the inflater's context in every case?
		} else {
			context = inflater.getContext();
		}

		user = RedditAccountManager.getInstance(context).getDefaultAccount();

		final LinearLayout outer = new LinearLayout(context);
		outer.setOrientation(LinearLayout.VERTICAL);

		notifications = new LinearLayout(context);
		notifications.setOrientation(LinearLayout.VERTICAL);

		loadingView = new LoadingView(context, R.string.download_waiting, true, true);

		final ListView lv = new ListView(context);
		lv.setDivider(null);

		lv.addFooterView(notifications);

		final int paddingPx = General.dpToPixels(context, 8);
		lv.setPadding(paddingPx, 0, paddingPx, 0);

		adapter = new MainMenuAdapter(context, user, this);
		lv.setAdapter(adapter);

		lv.setOnItemClickListener(new AdapterView.OnItemClickListener() {
			public void onItemClick(final AdapterView<?> adapterView, final View view, final int position, final long id) {
				adapter.clickOn(position);
			}
		});

		General.UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				notifications.addView(loadingView);
				loadingView.setIndeterminate(R.string.download_subreddits);
			}
		});

		final RedditSubredditSubscriptionManager subredditSubscriptionManager
				= RedditSubredditSubscriptionManager.getSingleton(context, user);

		if(force) {
			subredditSubscriptionManager.triggerUpdate(new RequestResponseHandler<HashSet<String>, SubredditRequestFailure>() {
				@Override
				public void onRequestFailed(SubredditRequestFailure failureReason) {
					onError(failureReason.asError(context));
				}

				@Override
				public void onRequestSuccess(HashSet<String> result, long timeCached) {
					subredditSubscriptionManager.addListener(MainMenuFragment.this);
					onSubscriptionsChanged(result);
				}
			}, TimestampBound.NONE);

		} else {

			subredditSubscriptionManager.addListener(MainMenuFragment.this);

			if(subredditSubscriptionManager.areSubscriptionsReady()) {
				onSubscriptionsChanged(subredditSubscriptionManager.getSubscriptionList());
			}
		}

		outer.addView(lv);
		lv.getLayoutParams().height = ViewGroup.LayoutParams.MATCH_PARENT;

		return outer;
	}

	public void onSubscriptionsChanged(final Collection<String> subscriptions) {

		adapter.setSubreddits(subscriptions);
		if(loadingView != null) loadingView.setDone(R.string.download_done);
	}

	private void onError(final RRError error) {
		if(loadingView != null) loadingView.setDone(R.string.download_failed);
		General.UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				notifications.addView(new ErrorView(getActivity(), error));
			}
		});
	}

	@Override
	public void onSaveInstanceState(final Bundle outState) {
		// TODO save menu position?
	}

	public void onSelected(final MainMenuAction type, final String name) {
		((MainMenuSelectionListener)getActivity()).onSelected(type, name);
	}

	public void onSelected(final PostListingURL postListingURL) {
		((MainMenuSelectionListener)getActivity()).onSelected(postListingURL);
	}

	@Override
	public void onSubredditSubscriptionListUpdated(RedditSubredditSubscriptionManager subredditSubscriptionManager) {
		onSubscriptionsChanged(subredditSubscriptionManager.getSubscriptionList());
	}

	@Override
	public void onSubredditSubscriptionAttempted(RedditSubredditSubscriptionManager subredditSubscriptionManager) {}

	@Override
	public void onSubredditUnsubscriptionAttempted(RedditSubredditSubscriptionManager subredditSubscriptionManager) {}
}


File: src/main/java/org/quantumbadger/redreader/fragments/SessionListDialog.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.fragments;

import android.app.AlertDialog;
import android.app.Dialog;
import android.app.DialogFragment;
import android.content.Context;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ListView;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccountChangeListener;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.activities.SessionChangeListener;
import org.quantumbadger.redreader.adapters.SessionListAdapter;
import org.quantumbadger.redreader.cache.CacheEntry;
import org.quantumbadger.redreader.common.General;

import java.net.URI;
import java.util.UUID;

public class SessionListDialog extends DialogFragment implements RedditAccountChangeListener {

	private URI url;
	private UUID current;
	private SessionChangeListener.SessionChangeType type;

	private ListView lv;

	// Workaround for HoloEverywhere bug?
	private volatile boolean alreadyCreated = false;

	public static SessionListDialog newInstance(final Uri url, final UUID current, final SessionChangeListener.SessionChangeType type) {

		final SessionListDialog dialog = new SessionListDialog();

		final Bundle args = new Bundle(3);
		args.putString("url", url.toString());
		if(current != null) args.putString("current", current.toString());
		args.putString("type", type.name());
		dialog.setArguments(args);

		return dialog;
	}

	@Override
	public void onCreate(final Bundle savedInstanceState) {

		super.onCreate(savedInstanceState);

		url = General.uriFromString(getArguments().getString("url"));

		if(getArguments().containsKey("current")) {
			current = UUID.fromString(getArguments().getString("current"));
		} else {
			current = null;
		}

		type = SessionChangeListener.SessionChangeType.valueOf(getArguments().getString("type"));
	}

	@Override
	public Dialog onCreateDialog(final Bundle savedInstanceState) {

		if(alreadyCreated) return getDialog();
		alreadyCreated = true;

		super.onCreateDialog(savedInstanceState);

		final AlertDialog.Builder builder = new AlertDialog.Builder(getActivity());
		builder.setTitle(getActivity().getString(R.string.options_past));

		final Context context = getActivity();

		lv = new ListView(context);
		builder.setView(lv);

		lv.setAdapter(new SessionListAdapter(context, url, current));

		RedditAccountManager.getInstance(context).addUpdateListener(this);

		lv.setOnItemClickListener(new AdapterView.OnItemClickListener() {
			public void onItemClick(AdapterView<?> adapterView, View view, int position, final long id) {

				final CacheEntry ce = (CacheEntry) lv.getItemAtPosition(position);

				if(ce == null) {
					((SessionChangeListener) getActivity()).onSessionRefreshSelected(type);

				} else {
					((SessionChangeListener) getActivity()).onSessionSelected(ce.session, type);
				}

				dismiss();
			}
		});

		builder.setNeutralButton(getActivity().getString(R.string.dialog_close), null);

		return builder.create();
	}

	public void onRedditAccountChanged() {
		General.UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				lv.setAdapter(new SessionListAdapter(getActivity(), url, current));
			}
		});
	}
}


File: src/main/java/org/quantumbadger/redreader/fragments/UserProfileDialog.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.fragments;

import android.app.Activity;
import android.content.Context;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.activities.BugReportActivity;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.CacheRequest;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.*;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;
import org.quantumbadger.redreader.reddit.things.RedditUser;
import org.quantumbadger.redreader.reddit.url.UserPostListingURL;
import org.quantumbadger.redreader.views.liststatus.ErrorView;
import org.quantumbadger.redreader.views.liststatus.LoadingView;

public class UserProfileDialog extends PropertiesDialog {

	private String username;
	private boolean active = true;

	public static UserProfileDialog newInstance(final String user) {

		final UserProfileDialog dialog = new UserProfileDialog();

		final Bundle args = new Bundle();
		args.putString("user", user);
		dialog.setArguments(args);

		return dialog;
	}

	@Override
	public void onDestroy() {
		super.onDestroy();
		active = false;
	}

	@Override
	protected String getTitle(Context context) {
		return username;
	}

	@Override
	public final void prepare(final Activity context, final LinearLayout items) {

		final LoadingView loadingView = new LoadingView(context, R.string.download_waiting, true, true);
		items.addView(loadingView);

		username = getArguments().getString("user");
		final CacheManager cm = CacheManager.getInstance(context);

		RedditAPI.getUser(cm, username, new APIResponseHandler.UserResponseHandler(context) {
			@Override
			protected void onDownloadStarted() {
				if(!active) return;
				loadingView.setIndeterminate(R.string.download_connecting);
			}

			@Override
			protected void onSuccess(final RedditUser user, long timestamp) {

				General.UI_THREAD_HANDLER.post(new Runnable() {
					public void run() {

						if(!active) return;

						loadingView.setDone(R.string.download_done);

						final LinearLayout karmaLayout = (LinearLayout) getActivity().getLayoutInflater().inflate(R.layout.karma, null);
						items.addView(karmaLayout);

						final TextView linkKarma = (TextView) karmaLayout.findViewById(R.id.layout_karma_text_link);
						final TextView commentKarma = (TextView) karmaLayout.findViewById(R.id.layout_karma_text_comment);

						linkKarma.setText(String.valueOf(user.link_karma));
						commentKarma.setText(String.valueOf(user.comment_karma));

						items.addView(propView(context, R.string.userprofile_created, RRTime.formatDateTime(user.created_utc * 1000, context), false));

						if(user.has_mail != null) {
							items.addView(propView(context, R.string.userprofile_hasmail, user.has_mail ? R.string.general_true : R.string.general_false, false));
						}

						if(user.has_mod_mail != null) {
							items.addView(propView(context, R.string.userprofile_hasmodmail, user.has_mod_mail ? R.string.general_true : R.string.general_false, false));
						}

						if(user.is_friend) {
							items.addView(propView(context, R.string.userprofile_isfriend, R.string.general_true, false));
						}

						if(user.is_gold) {
							items.addView(propView(context, R.string.userprofile_isgold, R.string.general_true, false));
						}

						if(user.is_mod) {
							items.addView(propView(context, R.string.userprofile_moderator, R.string.general_true, false));
						}

						final Button commentsButton = new Button(context);
						commentsButton.setText(R.string.userprofile_viewcomments);
						commentsButton.setOnClickListener(new View.OnClickListener() {
							public void onClick(View v) {
								LinkHandler.onLinkClicked(getActivity(), Constants.Reddit.getUri("/user/" + username + "/comments.json").toString(), false);
							}
						});
						items.addView(commentsButton);
						// TODO use margin? or framelayout? scale padding dp
						// TODO change button color
						commentsButton.setPadding(20, 20, 20, 20);

						final Button postsButton = new Button(context);
						postsButton.setText(R.string.userprofile_viewposts);
						postsButton.setOnClickListener(new View.OnClickListener() {
							public void onClick(View v) {
								LinkHandler.onLinkClicked(getActivity(), UserPostListingURL.getSubmitted(username).generateJsonUri().toString(), false);
							}
						});
						items.addView(postsButton);
						// TODO use margin? or framelayout? scale padding dp
						postsButton.setPadding(20, 20, 20, 20);

					}
				});
			}

			@Override
			protected void onCallbackException(Throwable t) {
				BugReportActivity.handleGlobalError(context, t);
			}

			@Override
			protected void onFailure(final RequestFailureType type, final Throwable t, final StatusLine status, final String readableMessage) {

				General.UI_THREAD_HANDLER.post(new Runnable() {
					public void run() {

						if(!active) return;

						loadingView.setDone(R.string.download_failed);

						final RRError error = General.getGeneralErrorForFailure(context, type, t, status, null);
						items.addView(new ErrorView(getActivity(), error));
					}
				});
			}

			@Override
			protected void onFailure(final APIFailureType type) {

				General.UI_THREAD_HANDLER.post(new Runnable() {
					public void run() {

						if(!active) return;

						loadingView.setDone(R.string.download_failed);

						final RRError error = General.getGeneralErrorForFailure(context, type);
						items.addView(new ErrorView(getActivity(), error));
					}
				});
			}

		}, RedditAccountManager.getInstance(context).getDefaultAccount(), CacheRequest.DownloadType.FORCE, true, context);
	}
}


File: src/main/java/org/quantumbadger/redreader/fragments/WebViewFragment.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.fragments;

import android.annotation.SuppressLint;
import android.app.Fragment;
import android.content.Context;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.*;
import android.widget.FrameLayout;
import android.widget.ProgressBar;
import android.widget.Toast;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.common.AndroidApi;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.LinkHandler;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedPost;
import org.quantumbadger.redreader.reddit.things.RedditPost;
import org.quantumbadger.redreader.reddit.url.RedditURLParser;
import org.quantumbadger.redreader.views.RedditPostView;
import org.quantumbadger.redreader.views.WebViewFixed;
import org.quantumbadger.redreader.views.bezelmenu.BezelSwipeOverlay;
import org.quantumbadger.redreader.views.bezelmenu.SideToolbarOverlay;

import java.util.Timer;
import java.util.TimerTask;

public class WebViewFragment extends Fragment implements RedditPostView.PostSelectionListener {

	private String url, html;
    private volatile String currentUrl;
    private volatile boolean goingBack;
	private volatile int lastBackDepthAttempt;

	private WebViewFixed webView;
	private ProgressBar progressView;
	private FrameLayout outer;

	public static WebViewFragment newInstance(final String url, final RedditPost post) {

		final WebViewFragment f = new WebViewFragment();

		final Bundle bundle = new Bundle(1);
		bundle.putString("url", url);
		if(post != null) bundle.putParcelable("post", post);
		f.setArguments(bundle);

		return f;
	}

	public static WebViewFragment newInstanceHtml(final String html) {

		final WebViewFragment f = new WebViewFragment();

		final Bundle bundle = new Bundle(1);
		bundle.putString("html", html);
		f.setArguments(bundle);

		return f;
	}

	@Override
	public void onCreate(final Bundle savedInstanceState) {
		// TODO load position/etc?
		super.onCreate(savedInstanceState);
		url = getArguments().getString("url");
		html = getArguments().getString("html");
	}

	@SuppressLint("NewApi")
	@Override
	public View onCreateView(final LayoutInflater inflater, final ViewGroup container, final Bundle savedInstanceState) {

		final Context context = inflater.getContext();

		CookieSyncManager.createInstance(getActivity());

		outer = (FrameLayout)inflater.inflate(R.layout.web_view_fragment, null);

		final RedditPost src_post = getArguments().getParcelable("post");
		final RedditPreparedPost post = src_post == null ? null
				: new RedditPreparedPost(context, CacheManager.getInstance(context), 0, src_post, -1, false,
				false, false, false, RedditAccountManager.getInstance(context).getDefaultAccount(), false);

		webView = (WebViewFixed)outer.findViewById(R.id.web_view_fragment_webviewfixed);
		final FrameLayout loadingViewFrame = (FrameLayout)outer.findViewById(R.id.web_view_fragment_loadingview_frame);

		progressView = new ProgressBar(context, null, android.R.attr.progressBarStyleHorizontal);
		loadingViewFrame.addView(progressView);
		loadingViewFrame.setPadding(General.dpToPixels(context, 10), 0,  General.dpToPixels(context, 10), 0);

		final WebSettings settings = webView.getSettings();

		settings.setBuiltInZoomControls(true);
		settings.setJavaScriptEnabled(true);
		settings.setJavaScriptCanOpenWindowsAutomatically(false);
		settings.setUseWideViewPort(true);
		settings.setLoadWithOverviewMode(true);
		settings.setDomStorageEnabled(true);

		if (AndroidApi.isHoneyCombOrLater()) {
			settings.setDisplayZoomControls(false);
		}

		// TODO handle long clicks

		webView.setWebChromeClient(new WebChromeClient() {
			@Override
			public void onProgressChanged(WebView view, final int newProgress) {

				super.onProgressChanged(view, newProgress);

				General.UI_THREAD_HANDLER.post(new Runnable() {
					@Override
					public void run() {
						progressView.setProgress(newProgress);
						progressView.setVisibility(newProgress == 100 ? View.GONE : View.VISIBLE);
					}
				});
			}
		});


		if(url != null) {

			webView.loadUrl(url);

			webView.setWebViewClient(new WebViewClient() {
				@Override
				public boolean shouldOverrideUrlLoading(final WebView view, final String url) {

					if(url == null) return false;

					if(url.startsWith("data:")) {
						// Prevent imgur bug where we're directed to some random data URI
						return true;
					}

					// Go back if loading same page to prevent redirect loops.
					if(goingBack && currentUrl != null && url.equals(currentUrl)) {

						General.quickToast(context,
								String.format("Handling redirect loop (level %d)", -lastBackDepthAttempt), Toast.LENGTH_SHORT);

						lastBackDepthAttempt--;

						if (webView.canGoBackOrForward(lastBackDepthAttempt)) {
							webView.goBackOrForward(lastBackDepthAttempt);
						} else {
							getActivity().finish();
						}
					} else  {

						if(RedditURLParser.parse(Uri.parse(url)) != null) {
							LinkHandler.onLinkClicked(getActivity(), url, false);
						} else {
							webView.loadUrl(url);
							currentUrl = url;
						}
					}

					return true;
				}

				@Override
				public void onPageStarted(WebView view, String url, Bitmap favicon) {
					super.onPageStarted(view, url, favicon);
					getActivity().setTitle(url);
				}

				@Override
				public void onPageFinished(final WebView view, final String url) {
					super.onPageFinished(view, url);

					new Timer().schedule(new TimerTask() {
						@Override
						public void run() {

							General.UI_THREAD_HANDLER.post(new Runnable() {
								public void run() {

									if(currentUrl == null || url == null) return;

									if(!url.equals(view.getUrl())) return;

									if(goingBack && url.equals(currentUrl)) {

										General.quickToast(context,
												String.format("Handling redirect loop (level %d)", -lastBackDepthAttempt));

										lastBackDepthAttempt--;

										if(webView.canGoBackOrForward(lastBackDepthAttempt)) {
											webView.goBackOrForward(lastBackDepthAttempt);
										} else {
											getActivity().finish();
										}

									} else {
										goingBack = false;
									}
								}
							});
						}
					}, 1000);
				}

				@Override
				public void doUpdateVisitedHistory(WebView view, String url, boolean isReload) {
					super.doUpdateVisitedHistory(view, url, isReload);
				}
			});

		} else {
			webView.loadData(html, "text/html; charset=UTF-8", null);
		}

		final FrameLayout outerFrame = new FrameLayout(context);
		outerFrame.addView(outer);

		if(post != null) {

			final SideToolbarOverlay toolbarOverlay = new SideToolbarOverlay(context);

			final BezelSwipeOverlay bezelOverlay = new BezelSwipeOverlay(context, new BezelSwipeOverlay.BezelSwipeListener() {

				public boolean onSwipe(BezelSwipeOverlay.SwipeEdge edge) {

					toolbarOverlay.setContents(post.generateToolbar(getActivity(), false, toolbarOverlay));
					toolbarOverlay.show(edge == BezelSwipeOverlay.SwipeEdge.LEFT ?
							SideToolbarOverlay.SideToolbarPosition.LEFT : SideToolbarOverlay.SideToolbarPosition.RIGHT);
					return true;
				}

				public boolean onTap() {

					if(toolbarOverlay.isShown()) {
						toolbarOverlay.hide();
						return true;
					}

					return false;
				}
			});

			outerFrame.addView(bezelOverlay);
			outerFrame.addView(toolbarOverlay);

			bezelOverlay.getLayoutParams().width = android.widget.FrameLayout.LayoutParams.MATCH_PARENT;
			bezelOverlay.getLayoutParams().height = android.widget.FrameLayout.LayoutParams.MATCH_PARENT;

			toolbarOverlay.getLayoutParams().width = android.widget.FrameLayout.LayoutParams.MATCH_PARENT;
			toolbarOverlay.getLayoutParams().height = android.widget.FrameLayout.LayoutParams.MATCH_PARENT;
		}

		return outerFrame;
	}

	@Override
	public void onDestroyView() {

		webView.stopLoading();
		webView.loadData("<html></html>", "text/plain", "UTF-8");
		webView.reload();
		webView.loadUrl("about:blank");
		outer.removeAllViews();
		webView.destroy();

		final CookieManager cookieManager = CookieManager.getInstance();
		cookieManager.removeAllCookie();

		super.onDestroyView();
	}

	public boolean onBackButtonPressed() {

		if(webView.canGoBack()) {
            goingBack = true;
			lastBackDepthAttempt = -1;
			webView.goBack();
			return true;
		}

		return false;
	}

	public void onPostSelected(final RedditPreparedPost post) {
		((RedditPostView.PostSelectionListener)getActivity()).onPostSelected(post);
	}

	public void onPostCommentsSelected(final RedditPreparedPost post) {
		((RedditPostView.PostSelectionListener)getActivity()).onPostCommentsSelected(post);
	}

    public String getCurrentUrl() {
        return (currentUrl != null) ? currentUrl : url;
    }

	@Override
	@SuppressLint("NewApi")
	public void onPause() {
		super.onPause();

		if (AndroidApi.isHoneyCombOrLater()) {
			webView.onPause();
		}

		webView.pauseTimers();
	}

	@Override
	@SuppressLint("NewApi")
	public void onResume() {
		super.onResume();
		webView.resumeTimers();

		if (AndroidApi.isHoneyCombOrLater()) {
			webView.onResume();
		}
	}

	public void clearCache() {
		webView.clearCache(true);
		webView.clearHistory();
		webView.clearFormData();

		final CookieManager cookieManager = CookieManager.getInstance();
		cookieManager.removeAllCookie();
	}
}


File: src/main/java/org/quantumbadger/redreader/reddit/api/RedditSubredditSubscriptionManager.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.reddit.api;

import android.app.Activity;
import android.content.Context;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.activities.BugReportActivity;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.RRError;
import org.quantumbadger.redreader.common.TimestampBound;
import org.quantumbadger.redreader.common.UnexpectedInternalStateException;
import org.quantumbadger.redreader.common.collections.WeakReferenceListManager;
import org.quantumbadger.redreader.io.RawObjectDB;
import org.quantumbadger.redreader.io.RequestResponseHandler;
import org.quantumbadger.redreader.io.WritableHashSet;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;
import org.quantumbadger.redreader.reddit.RedditSubredditManager;

import java.util.ArrayList;
import java.util.HashSet;

public class RedditSubredditSubscriptionManager {

	public static enum SubredditSubscriptionState { SUBSCRIBED, SUBSCRIBING, UNSUBSCRIBING, NOT_SUBSCRIBED }

	private final SubredditSubscriptionStateChangeNotifier notifier = new SubredditSubscriptionStateChangeNotifier();
	private final WeakReferenceListManager<SubredditSubscriptionStateChangeListener> listeners
			= new WeakReferenceListManager<SubredditSubscriptionStateChangeListener>();

	private static RedditSubredditSubscriptionManager singleton;
	private static RedditAccount singletonAccount;

	private final RedditAccount user;
	private final Context context;

	private static RawObjectDB<String, WritableHashSet> db = null;

	private WritableHashSet subscriptions;
	private HashSet<String> pendingSubscriptions = new HashSet<String>(), pendingUnsubscriptions = new HashSet<String>();

	public static synchronized RedditSubredditSubscriptionManager getSingleton(final Context context, final RedditAccount account) {

		if(db == null) {
			db = new RawObjectDB<String, WritableHashSet>(context, "rr_subscriptions.db", WritableHashSet.class);
		}

		if(singleton == null || !account.equals(RedditSubredditSubscriptionManager.singletonAccount)) {
			singleton = new RedditSubredditSubscriptionManager(account, context);
			RedditSubredditSubscriptionManager.singletonAccount = account;
		}

		return singleton;
	}

	private RedditSubredditSubscriptionManager(RedditAccount user, Context context) {

		this.user = user;
		this.context = context;

		subscriptions = db.getById(user.getCanonicalUsername());

		triggerUpdate(null, TimestampBound.notOlderThan(1000 * 60 * 60 * 24)); // Max age, 24 hours
	}

	public void addListener(SubredditSubscriptionStateChangeListener listener) {
		listeners.add(listener);
	}

	public synchronized boolean areSubscriptionsReady() {
		return subscriptions != null;
	}

	public synchronized SubredditSubscriptionState getSubscriptionState(final String subredditCanonicalId) {

		if(pendingSubscriptions.contains(subredditCanonicalId)) return SubredditSubscriptionState.SUBSCRIBING;
		else if(pendingUnsubscriptions.contains(subredditCanonicalId)) return SubredditSubscriptionState.UNSUBSCRIBING;
		else if(subscriptions.toHashset().contains(subredditCanonicalId)) return SubredditSubscriptionState.SUBSCRIBED;
		else return SubredditSubscriptionState.NOT_SUBSCRIBED;
	}

	private synchronized void onSubscriptionAttempt(final String subredditCanonicalId) {
		pendingSubscriptions.add(subredditCanonicalId);
		listeners.map(notifier, SubredditSubscriptionChangeType.SUBSCRIPTION_ATTEMPTED);
	}

	private synchronized void onUnsubscriptionAttempt(final String subredditCanonicalId) {
		pendingUnsubscriptions.add(subredditCanonicalId);
		listeners.map(notifier, SubredditSubscriptionChangeType.UNSUBSCRIPTION_ATTEMPTED);
	}

	private synchronized void onSubscriptionChangeAttemptFailed(final String subredditCanonicalId) {
		pendingUnsubscriptions.remove(subredditCanonicalId);
		pendingSubscriptions.remove(subredditCanonicalId);
		listeners.map(notifier, SubredditSubscriptionChangeType.LIST_UPDATED);
	}

	private synchronized void onSubscriptionAttemptSuccess(final String subredditCanonicalId) {
		pendingSubscriptions.remove(subredditCanonicalId);
		subscriptions.toHashset().add(subredditCanonicalId);
		listeners.map(notifier, SubredditSubscriptionChangeType.LIST_UPDATED);
	}

	private synchronized void onUnsubscriptionAttemptSuccess(final String subredditCanonicalId) {
		pendingUnsubscriptions.remove(subredditCanonicalId);
		subscriptions.toHashset().remove(subredditCanonicalId);
		listeners.map(notifier, SubredditSubscriptionChangeType.LIST_UPDATED);
	}

	private synchronized void onNewSubscriptionListReceived(HashSet<String> newSubscriptions, long timestamp) {

		pendingSubscriptions.clear();
		pendingUnsubscriptions.clear();

		subscriptions = new WritableHashSet(newSubscriptions, timestamp, user.getCanonicalUsername());

		// TODO threaded? or already threaded due to cache manager
		db.put(subscriptions);

		listeners.map(notifier, SubredditSubscriptionChangeType.LIST_UPDATED);
	}

	public synchronized ArrayList<String> getSubscriptionList() {
		return new ArrayList<String>(subscriptions.toHashset());
	}

	public void triggerUpdate(final RequestResponseHandler<HashSet<String>, SubredditRequestFailure> handler, TimestampBound timestampBound) {

		if(subscriptions != null && timestampBound.verifyTimestamp(subscriptions.getTimestamp())) {
			return;
		}

		new RedditAPIIndividualSubredditListRequester(context, user).performRequest(
				RedditSubredditManager.SubredditListType.SUBSCRIBED,
				timestampBound,
				new RequestResponseHandler<WritableHashSet, SubredditRequestFailure>() {

					// TODO handle failed requests properly -- retry? then notify listeners
					@Override
					public void onRequestFailed(SubredditRequestFailure failureReason) {
						if(handler != null) handler.onRequestFailed(failureReason);
					}

					@Override
					public void onRequestSuccess(WritableHashSet result, long timeCached) {
						final HashSet<String> newSubscriptions = result.toHashset();
						onNewSubscriptionListReceived(newSubscriptions, timeCached);
						if(handler != null) handler.onRequestSuccess(newSubscriptions, timeCached);
					}
				}
		);

	}

	public void subscribe(final String subredditCanonicalId, final Activity activity) {

		RedditAPI.action(
				CacheManager.getInstance(context),
				new SubredditActionResponseHandler(activity, RedditAPI.RedditSubredditAction.SUBSCRIBE, subredditCanonicalId),
				user,
				subredditCanonicalId,
				RedditAPI.RedditSubredditAction.SUBSCRIBE,
				context
		);

		onSubscriptionAttempt(subredditCanonicalId);
	}

	public void unsubscribe(final String subredditCanonicalId, final Activity activity) {

		RedditAPI.action(
				CacheManager.getInstance(context),
				new SubredditActionResponseHandler(activity, RedditAPI.RedditSubredditAction.UNSUBSCRIBE, subredditCanonicalId),
				user,
				subredditCanonicalId,
				RedditAPI.RedditSubredditAction.UNSUBSCRIBE,
				context
		);

		onUnsubscriptionAttempt(subredditCanonicalId);
	}

	private class SubredditActionResponseHandler extends APIResponseHandler.ActionResponseHandler {

		private final RedditAPI.RedditSubredditAction action;
		private final Activity activity;
		private final String canonicalName;

		protected SubredditActionResponseHandler(Activity activity,
												 RedditAPI.RedditSubredditAction action,
												 String canonicalName) {
			super(activity);
			this.activity = activity;
			this.action = action;
			this.canonicalName = canonicalName;
		}

		@Override
		protected void onSuccess() {

			switch(action) {
				case SUBSCRIBE:
					onSubscriptionAttemptSuccess(canonicalName);
					break;
				case UNSUBSCRIBE:
					onUnsubscriptionAttemptSuccess(canonicalName);
					break;
			}

			triggerUpdate(null, TimestampBound.NONE);
		}

		@Override
		protected void onCallbackException(Throwable t) {
			BugReportActivity.handleGlobalError(context, t);
		}

		@Override
		protected void onFailure(RequestFailureType type, Throwable t, StatusLine status, String readableMessage) {
			onSubscriptionChangeAttemptFailed(canonicalName);
			if(t != null) t.printStackTrace();

			final RRError error = General.getGeneralErrorForFailure(context, type, t, status, null);
			General.UI_THREAD_HANDLER.post(new Runnable() {
				public void run() {
					General.showResultDialog(activity, error);
				}
			});
		}

		@Override
		protected void onFailure(APIFailureType type) {
			onSubscriptionChangeAttemptFailed(canonicalName);
			final RRError error = General.getGeneralErrorForFailure(context, type);
			General.UI_THREAD_HANDLER.post(new Runnable() {
				public void run() {
					General.showResultDialog(activity, error);
				}
			});
		}
	}

	public Long getSubscriptionListTimestamp() {
		return subscriptions != null ? subscriptions.getTimestamp() : null;
	}

	public interface SubredditSubscriptionStateChangeListener {
		public void onSubredditSubscriptionListUpdated(RedditSubredditSubscriptionManager subredditSubscriptionManager);
		public void onSubredditSubscriptionAttempted(RedditSubredditSubscriptionManager subredditSubscriptionManager);
		public void onSubredditUnsubscriptionAttempted(RedditSubredditSubscriptionManager subredditSubscriptionManager);
	}

	private static enum SubredditSubscriptionChangeType {LIST_UPDATED, SUBSCRIPTION_ATTEMPTED, UNSUBSCRIPTION_ATTEMPTED}

	private class SubredditSubscriptionStateChangeNotifier
			implements WeakReferenceListManager.ArgOperator<SubredditSubscriptionStateChangeListener, SubredditSubscriptionChangeType> {

		public void operate(SubredditSubscriptionStateChangeListener listener, SubredditSubscriptionChangeType changeType) {

			switch(changeType) {
				case LIST_UPDATED:
					listener.onSubredditSubscriptionListUpdated(RedditSubredditSubscriptionManager.this);
					break;
				case SUBSCRIPTION_ATTEMPTED:
					listener.onSubredditSubscriptionAttempted(RedditSubredditSubscriptionManager.this);
					break;
				case UNSUBSCRIPTION_ATTEMPTED:
					listener.onSubredditUnsubscriptionAttempted(RedditSubredditSubscriptionManager.this);
					break;
				default:
					throw new UnexpectedInternalStateException("Invalid SubredditSubscriptionChangeType " + changeType.toString());
			}
		}
	}
}


File: src/main/java/org/quantumbadger/redreader/reddit/prepared/RedditPreparedComment.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.reddit.prepared;

import android.app.Activity;
import android.content.Context;
import android.content.res.TypedArray;
import android.graphics.Color;
import android.text.SpannableStringBuilder;
import android.view.ViewGroup;
import android.widget.Toast;
import org.apache.commons.lang3.StringEscapeUtils;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.*;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;
import org.quantumbadger.redreader.reddit.RedditPreparedInboxItem;
import org.quantumbadger.redreader.reddit.prepared.markdown.MarkdownParagraphGroup;
import org.quantumbadger.redreader.reddit.prepared.markdown.MarkdownParser;
import org.quantumbadger.redreader.reddit.things.RedditComment;
import org.quantumbadger.redreader.views.RedditCommentView;

import java.net.URI;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.LinkedList;

public final class RedditPreparedComment implements RedditPreparedInboxItem {

	public SpannableStringBuilder header;

	private final MarkdownParagraphGroup body;

	private final LinkedList<RedditPreparedComment> directReplies = new LinkedList<RedditPreparedComment>();

	private boolean collapsed = false;

	public final String idAlone, idAndType, flair;

	private int voteDirection;
	private boolean saved;
	public long lastChange;
	public final RedditComment src;

	private RedditCommentView boundView;

	private final int
			rrCommentHeaderBoldCol,
			rrCommentHeaderAuthorCol,
			rrPostSubtitleUpvoteCol,
			rrPostSubtitleDownvoteCol,
			rrFlairBackCol,
			rrFlairTextCol,
			rrGoldBackCol,
			rrGoldTextCol;
	private final EnumSet<PrefsUtility.AppearanceCommentHeaderItems> headerItems;

	private final RedditPreparedPost parentPost;

	public RedditPreparedComment(final Context context,
								 final RedditComment comment,
								 final long timestamp,
								 final boolean needsUpdating,
								 final RedditPreparedPost parentPost,
								 final RedditAccount user,
								 final EnumSet<PrefsUtility.AppearanceCommentHeaderItems> headerItems) {

		this.src = comment;
		this.parentPost = parentPost;
		this.headerItems = headerItems;

		// TODO custom time

		// TODO don't fetch these every time
		final TypedArray appearance = context.obtainStyledAttributes(new int[]{
				R.attr.rrCommentHeaderBoldCol,
				R.attr.rrCommentHeaderAuthorCol,
				R.attr.rrPostSubtitleUpvoteCol,
				R.attr.rrPostSubtitleDownvoteCol,
				R.attr.rrFlairBackCol,
				R.attr.rrFlairTextCol,
				R.attr.rrGoldBackCol,
				R.attr.rrGoldTextCol
		});

		rrCommentHeaderBoldCol = appearance.getColor(0, 255);
		rrCommentHeaderAuthorCol = appearance.getColor(1, 255);
		rrPostSubtitleUpvoteCol = appearance.getColor(2, 255);
		rrPostSubtitleDownvoteCol = appearance.getColor(3, 255);
		rrFlairBackCol = appearance.getColor(4, 0);
		rrFlairTextCol = appearance.getColor(5, 255);
		rrGoldBackCol = appearance.getColor(6, 0);
		rrGoldTextCol = appearance.getColor(7, 255);

		body = MarkdownParser.parse(StringEscapeUtils.unescapeHtml4(comment.body).toCharArray());
		if(comment.author_flair_text != null) {
			flair = StringEscapeUtils.unescapeHtml4(comment.author_flair_text);
		} else {
			flair = null;
		}

		idAlone = comment.id;
		idAndType = comment.name;

		if(comment.likes == null) {
			voteDirection = 0;
		} else {
			voteDirection = Boolean.TRUE.equals(comment.likes) ? 1 : -1;
		}

		saved = Boolean.TRUE.equals(comment.saved);

		lastChange = timestamp;
		if(src.likes != null) {
			RedditChangeDataManager.getInstance(context).update(src.link_id, user, this, true);
		} else if(needsUpdating) {
			RedditChangeDataManager.getInstance(context).update(src.link_id, user, this, false);
		}

		rebuildHeader(context);
	}

	private void rebuildHeader(final Context context) {

		final BetterSSB sb = new BetterSSB();

		final int pointsCol;
		int score = src.ups - src.downs;

		if(Boolean.TRUE.equals(src.likes)) score--;
		if(Boolean.FALSE.equals(src.likes)) score++;

		if(isUpvoted()) {
			pointsCol = rrPostSubtitleUpvoteCol;
			score++;
		} else if(isDownvoted()) {
			pointsCol = rrPostSubtitleDownvoteCol;
			score--;
		} else {
			pointsCol = rrCommentHeaderBoldCol;
		}

		if(headerItems.contains(PrefsUtility.AppearanceCommentHeaderItems.AUTHOR)) {
			if(parentPost != null
					&& src.author.equalsIgnoreCase(parentPost.src.author)
					&& !src.author.equals("[deleted]")) {
				sb.append(" " + src.author + " ", BetterSSB.BACKGROUND_COLOR | BetterSSB.FOREGROUND_COLOR | BetterSSB.BOLD,
						Color.WHITE, Color.rgb(0, 126, 168), 1f); // TODO color
			} else {
				sb.append(src.author, BetterSSB.FOREGROUND_COLOR | BetterSSB.BOLD, rrCommentHeaderAuthorCol, 0, 1f);
			}
		}

		if(headerItems.contains(PrefsUtility.AppearanceCommentHeaderItems.FLAIR)
				&& flair != null && flair.length() > 0) {

			if(headerItems.contains(PrefsUtility.AppearanceCommentHeaderItems.AUTHOR)) {
				sb.append("  ", 0);
			}

			sb.append(" " + flair + " ", BetterSSB.FOREGROUND_COLOR | BetterSSB.BACKGROUND_COLOR, rrFlairTextCol, rrFlairBackCol, 1f);
		}

		if(headerItems.contains(PrefsUtility.AppearanceCommentHeaderItems.AUTHOR)
				|| headerItems.contains(PrefsUtility.AppearanceCommentHeaderItems.FLAIR)) {
			sb.append("   ", 0);
		}

		if(headerItems.contains(PrefsUtility.AppearanceCommentHeaderItems.SCORE)) {

			if(!Boolean.TRUE.equals(src.score_hidden)) {
				sb.append(String.valueOf(score), BetterSSB.FOREGROUND_COLOR | BetterSSB.BOLD, pointsCol, 0, 1f);
			} else {
				sb.append("??", BetterSSB.FOREGROUND_COLOR | BetterSSB.BOLD, pointsCol, 0, 1f);
			}

			sb.append(" " + context.getString(R.string.subtitle_points) +  " ", 0);
		}

		if(headerItems.contains(PrefsUtility.AppearanceCommentHeaderItems.GOLD)) {

			if(src.gilded > 0) {

				sb.append(" ", 0);

				sb.append(" "
								+ context.getString(R.string.gold)
								+ " x"
								+ src.gilded
								+ " ",
						BetterSSB.FOREGROUND_COLOR | BetterSSB.BACKGROUND_COLOR,
						rrGoldTextCol,
						rrGoldBackCol,
						1f);

				sb.append("  ", 0);
			}
		}

		if(headerItems.contains(PrefsUtility.AppearanceCommentHeaderItems.AGE)) {
			sb.append(RRTime.formatDurationFrom(context, src.created_utc * 1000L), BetterSSB.FOREGROUND_COLOR | BetterSSB.BOLD, rrCommentHeaderBoldCol, 0, 1f);

			if(src.edited != null && src.edited instanceof Long) {
				sb.append("*", BetterSSB.FOREGROUND_COLOR | BetterSSB.BOLD, rrCommentHeaderBoldCol, 0, 1f);
			}
		}

		header = sb.get();
	}

	public void bind(RedditCommentView view) {
		boundView = view;
	}

	public void unbind(RedditCommentView view) {
		if(boundView == view) boundView = null;
	}

	public void addChild(final RedditPreparedComment child) {
		directReplies.add(child);
	}

	public void toggleVisibility() {
		collapsed = !collapsed;
	}

	public boolean isCollapsed() {
		return collapsed;
	}

	public void refreshView(final Context context) {
		General.UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				rebuildHeader(context);
				if(boundView != null) {
					boundView.updateAppearance();
					boundView.requestLayout();
					boundView.invalidate();
				}
			}
		});
	}

	public void action(final Activity activity, final RedditAPI.RedditAction action) {

		final RedditAccount user = RedditAccountManager.getInstance(activity).getDefaultAccount();

		if(user.isAnonymous()) {
			General.quickToast(activity, "You must be logged in to do that.");
			return;
		}

		final int lastVoteDirection = voteDirection;

		switch(action) {
			case DOWNVOTE:
				if(!src.archived) {
					voteDirection = -1;
				}
				break;
			case UNVOTE:
				if(!src.archived) {
					voteDirection = 0;
				}
				break;
			case UPVOTE:
				if(!src.archived) {
					voteDirection = 1;
				}
				break;
			case SAVE: saved = true; break;
			case UNSAVE: saved = false; break;
		}

		refreshView(activity);

		boolean vote = (action == RedditAPI.RedditAction.DOWNVOTE
				| action == RedditAPI.RedditAction.UPVOTE
				| action == RedditAPI.RedditAction.UNVOTE);

		if(src.archived && vote){
			Toast.makeText(activity, R.string.error_archived_vote, Toast.LENGTH_SHORT)
					.show();
			return;
		}

		RedditAPI.action(CacheManager.getInstance(activity),
				new APIResponseHandler.ActionResponseHandler(activity) {
					@Override
					protected void onCallbackException(final Throwable t) {
						throw new RuntimeException(t);
					}

					@Override
					protected void onFailure(final RequestFailureType type, final Throwable t, final StatusLine status, final String readableMessage) {
						revertOnFailure();
						if(t != null) t.printStackTrace();

						final RRError error = General.getGeneralErrorForFailure(context, type, t, status, null);
						General.UI_THREAD_HANDLER.post(new Runnable() {
							public void run() {
								General.showResultDialog(activity, error);
							}
						});
					}

					@Override
					protected void onFailure(final APIFailureType type) {
						revertOnFailure();

						final RRError error = General.getGeneralErrorForFailure(context, type);
						General.UI_THREAD_HANDLER.post(new Runnable() {
							public void run() {
								General.showResultDialog(activity, error);
							}
						});
					}

					@Override
					protected void onSuccess() {
						lastChange = RRTime.utcCurrentTimeMillis();
						RedditChangeDataManager.getInstance(context).update(src.link_id, user, RedditPreparedComment.this, true);
						refreshView(activity);
					}

					private void revertOnFailure() {

						switch(action) {
							case DOWNVOTE:
							case UNVOTE:
							case UPVOTE:
								voteDirection = lastVoteDirection; break;
							case SAVE:
								saved = false; break;
							case UNSAVE:
								saved = true; break;
						}

						refreshView(context);
					}

				}, user, idAndType, action, activity);

	}

	public int getVoteDirection() {
		return voteDirection;
	}

	public boolean isUpvoted() {
		return voteDirection == 1;
	}

	public boolean isDownvoted() {
		return voteDirection == -1;
	}

	public void updateFromChangeDb(final long timestamp, final int voteDirection, final boolean saved) {
		this.lastChange = timestamp;
		this.voteDirection = voteDirection;
		this.saved = saved;
	}

	public int replyCount() {
		return directReplies.size();
	}

	@Override
	public boolean equals(Object o) {
		return o instanceof RedditPreparedComment
				&& (o == this || ((RedditPreparedComment) o).idAlone.equals(idAlone));
	}

	public HashSet<String> computeAllLinks() {
		return LinkHandler.computeAllLinks(StringEscapeUtils.unescapeHtml4(src.body_html));
	}

	public SpannableStringBuilder getHeader() {
		return header;
	}

	public ViewGroup getBody(Activity activity, float textSize, Integer textCol, boolean showLinkButtons) {
		return body.buildView(activity, textCol, textSize, showLinkButtons);
	}

	public RedditCommentView getBoundView() {
		return boundView;
	}

	public void handleInboxClick(Activity activity) {
		final URI commentContext = Constants.Reddit.getUri(src.context);
		LinkHandler.onLinkClicked(activity, commentContext.toString());
	}

	public boolean isSaved() {
		return saved;
	}
}


File: src/main/java/org/quantumbadger/redreader/reddit/prepared/RedditPreparedPost.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.reddit.prepared;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.res.TypedArray;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.net.Uri;
import android.os.Environment;
import android.preference.PreferenceManager;
import android.text.ClipboardManager;
import android.text.SpannableStringBuilder;
import android.util.Log;
import android.view.View;
import android.widget.Toast;
import org.apache.commons.lang3.StringEscapeUtils;
import org.apache.http.StatusLine;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.activities.*;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.cache.CacheRequest;
import org.quantumbadger.redreader.cache.RequestFailureType;
import org.quantumbadger.redreader.common.*;
import org.quantumbadger.redreader.fragments.PostPropertiesDialog;
import org.quantumbadger.redreader.image.ThumbnailScaler;
import org.quantumbadger.redreader.reddit.APIResponseHandler;
import org.quantumbadger.redreader.reddit.RedditAPI;
import org.quantumbadger.redreader.reddit.prepared.markdown.MarkdownParagraphGroup;
import org.quantumbadger.redreader.reddit.prepared.markdown.MarkdownParser;
import org.quantumbadger.redreader.reddit.things.RedditPost;
import org.quantumbadger.redreader.reddit.things.RedditSubreddit;
import org.quantumbadger.redreader.reddit.url.SubredditPostListURL;
import org.quantumbadger.redreader.reddit.url.UserProfileURL;
import org.quantumbadger.redreader.views.FlatImageButton;
import org.quantumbadger.redreader.views.RedditPostView;
import org.quantumbadger.redreader.views.bezelmenu.SideToolbarOverlay;
import org.quantumbadger.redreader.views.bezelmenu.VerticalToolbar;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.util.*;

public final class RedditPreparedPost {

	public final RedditPost src;

	public final String title;
	public SpannableStringBuilder postListDescription;
	public final String url;

	public final String idAlone, idAndType;

	private int voteDirection;
	private boolean saved, hidden, read, stickied;

	public final boolean hasThumbnail;
	private boolean gotHighResThumb = false;

	// TODO make it possible to turn off in-memory caching when out of memory
	private volatile Bitmap thumbnailCache = null;
	public final String imageUrl, thumbnailUrl;

	private static final Object singleImageDecodeLock = new Object();

	private ThumbnailLoadedCallback thumbnailCallback;
	private int usageId = -1;

	public long lastChange = Long.MIN_VALUE;
	public final int commentCount;

	private final boolean showSubreddit;

	private RedditPostView boundView = null;

	public final MarkdownParagraphGroup parsedSelfText;

	public static enum Action {
		UPVOTE, UNVOTE, DOWNVOTE, SAVE, HIDE, UNSAVE, UNHIDE, REPORT, SHARE, REPLY, USER_PROFILE, EXTERNAL, PROPERTIES, COMMENTS, LINK, COMMENTS_SWITCH, LINK_SWITCH, SHARE_COMMENTS, GOTO_SUBREDDIT, ACTION_MENU, SAVE_IMAGE, COPY, SELFTEXT_LINKS
	}

	// TODO too many parameters
	public RedditPreparedPost(final Context context, final CacheManager cm, final int listId, final RedditPost post,
							  final long timestamp, final boolean showSubreddit, final boolean updateNeeded,
							  final boolean showThumbnails, final boolean precacheImages, final RedditAccount user,
							  final boolean parseSelfText) {

		this.src = post;
		this.showSubreddit = showSubreddit;

		if(post.title == null) {
			title = "[null]";
		} else {
			title = StringEscapeUtils.unescapeHtml4(post.title.replace('\n', ' ')).trim();
		}

		idAlone = post.id;
		idAndType = post.name;
		url = StringEscapeUtils.unescapeHtml4(post.url);
		commentCount = post.num_comments;

		if(post.likes == null) {
			voteDirection = 0;
		} else {
			voteDirection = Boolean.TRUE.equals(post.likes) ? 1 : -1;
		}

		this.saved = post.saved;
		this.hidden = post.hidden;
		this.stickied = post.stickied;

		imageUrl = LinkHandler.getImageUrl(url);
		thumbnailUrl = post.thumbnail;
		hasThumbnail = showThumbnails && (hasThumbnail(post) || imageUrl != null);

		// TODO parameterise
		final int thumbnailWidth = General.dpToPixels(context, 64);

		if(hasThumbnail && hasThumbnail(post)) {
			downloadThumbnail(context, thumbnailWidth, cm, listId, false);
		}

		if(imageUrl != null && precacheImages) {
			downloadThumbnail(context, thumbnailWidth, cm, listId, true);
		}

		// TODO precache comments (respect settings)

		lastChange = timestamp;
		if(voteDirection != 0 || saved || hidden) {
			RedditChangeDataManager.getInstance(context).update("posts", user, this, true);
		} else if(updateNeeded) {
			RedditChangeDataManager.getInstance(context).update("posts", user, this, false);
		}

		rebuildSubtitle(context);

		if(parseSelfText && src.is_self && src.selftext != null && src.selftext.trim().length() > 0) {
			parsedSelfText = MarkdownParser.parse(StringEscapeUtils.unescapeHtml4(post.selftext).toCharArray());
		} else {
			parsedSelfText = null;
		}
	}

	public static void showActionMenu(final Activity activity, final RedditPreparedPost post) {

		final EnumSet<Action> itemPref = PrefsUtility.pref_menus_post_context_items(activity, PreferenceManager.getDefaultSharedPreferences(activity));

		if(itemPref.isEmpty()) return;

		final ArrayList<RPVMenuItem> menu = new ArrayList<RPVMenuItem>();

		if(!RedditAccountManager.getInstance(activity).getDefaultAccount().isAnonymous()) {

			if(itemPref.contains(Action.UPVOTE)) {
				if(!post.isUpvoted()) {
					menu.add(new RPVMenuItem(activity, R.string.action_upvote, Action.UPVOTE));
				} else {
					menu.add(new RPVMenuItem(activity, R.string.action_upvote_remove, Action.UNVOTE));
				}
			}

			if(itemPref.contains(Action.DOWNVOTE)) {
				if(!post.isDownvoted()) {
					menu.add(new RPVMenuItem(activity, R.string.action_downvote, Action.DOWNVOTE));
				} else {
					menu.add(new RPVMenuItem(activity, R.string.action_downvote_remove, Action.UNVOTE));
				}
			}

			if(itemPref.contains(Action.SAVE)) {
				if(!post.isSaved()) {
					menu.add(new RPVMenuItem(activity, R.string.action_save, Action.SAVE));
				} else {
					menu.add(new RPVMenuItem(activity, R.string.action_unsave, Action.UNSAVE));
				}
			}

			if(itemPref.contains(Action.HIDE)) {
				if(!post.isHidden()) {
					menu.add(new RPVMenuItem(activity, R.string.action_hide, Action.HIDE));
				} else {
					menu.add(new RPVMenuItem(activity, R.string.action_unhide, Action.UNHIDE));
				}
			}

			if(itemPref.contains(Action.REPORT)) menu.add(new RPVMenuItem(activity, R.string.action_report, Action.REPORT));
		}

		if(itemPref.contains(Action.EXTERNAL)) menu.add(new RPVMenuItem(activity, R.string.action_external, Action.EXTERNAL));
		if(itemPref.contains(Action.SELFTEXT_LINKS) && post.src.selftext != null && post.src.selftext.length() > 1) menu.add(new RPVMenuItem(activity, R.string.action_selftext_links, Action.SELFTEXT_LINKS));
		if(itemPref.contains(Action.SAVE_IMAGE) && post.imageUrl != null) menu.add(new RPVMenuItem(activity, R.string.action_save_image, Action.SAVE_IMAGE));
		if(itemPref.contains(Action.GOTO_SUBREDDIT)) menu.add(new RPVMenuItem(activity, R.string.action_gotosubreddit, Action.GOTO_SUBREDDIT));
		if(itemPref.contains(Action.SHARE)) menu.add(new RPVMenuItem(activity, R.string.action_share, Action.SHARE));
		if(itemPref.contains(Action.SHARE_COMMENTS)) menu.add(new RPVMenuItem(activity, R.string.action_share_comments, Action.SHARE_COMMENTS));
		if(itemPref.contains(Action.COPY)) menu.add(new RPVMenuItem(activity, R.string.action_copy, Action.COPY));
		if(itemPref.contains(Action.USER_PROFILE)) menu.add(new RPVMenuItem(activity, R.string.action_user_profile, Action.USER_PROFILE));
		if(itemPref.contains(Action.PROPERTIES)) menu.add(new RPVMenuItem(activity, R.string.action_properties, Action.PROPERTIES));

		final String[] menuText = new String[menu.size()];

		for(int i = 0; i < menuText.length; i++) {
			menuText[i] = menu.get(i).title;
		}

		final AlertDialog.Builder builder = new AlertDialog.Builder(activity);

		builder.setItems(menuText, new DialogInterface.OnClickListener() {
			public void onClick(DialogInterface dialog, int which) {
				onActionMenuItemSelected(post, activity, menu.get(which).action);
			}
		});

		//builder.setNeutralButton(R.string.dialog_cancel, null);

		final AlertDialog alert = builder.create();
		alert.setTitle(R.string.action_menu_post_title);
		alert.setCanceledOnTouchOutside(true);
		alert.show();
	}

	public static void onActionMenuItemSelected(final RedditPreparedPost post, final Activity activity, final Action action) {

		switch(action) {

			case UPVOTE:
				post.action(activity, RedditAPI.RedditAction.UPVOTE);
				break;

			case DOWNVOTE:
				post.action(activity, RedditAPI.RedditAction.DOWNVOTE);
				break;

			case UNVOTE:
				post.action(activity, RedditAPI.RedditAction.UNVOTE);
				break;

			case SAVE:
				post.action(activity, RedditAPI.RedditAction.SAVE);
				break;

			case UNSAVE:
				post.action(activity, RedditAPI.RedditAction.UNSAVE);
				break;

			case HIDE:
				post.action(activity, RedditAPI.RedditAction.HIDE);
				break;

			case UNHIDE:
				post.action(activity, RedditAPI.RedditAction.UNHIDE);
				break;

			case REPORT:

				new AlertDialog.Builder(activity)
						.setTitle(R.string.action_report)
						.setMessage(R.string.action_report_sure)
						.setPositiveButton(R.string.action_report,
								new DialogInterface.OnClickListener() {
									public void onClick(final DialogInterface dialog, final int which) {
										post.action(activity, RedditAPI.RedditAction.REPORT);
										// TODO update the view to show the result
										// TODO don't forget, this also hides
									}
								})
						.setNegativeButton(R.string.dialog_cancel, null)
						.show();

				break;

			case EXTERNAL: {
				final Intent intent = new Intent(Intent.ACTION_VIEW);
                String url = (activity instanceof WebViewActivity) ? ((WebViewActivity) activity).getCurrentUrl() : post.url;
				intent.setData(Uri.parse(url));
				activity.startActivity(intent);
				break;
			}

			case SELFTEXT_LINKS: {

				final HashSet<String> linksInComment = LinkHandler.computeAllLinks(StringEscapeUtils.unescapeHtml4(post.src.selftext));

				if(linksInComment.isEmpty()) {
					General.quickToast(activity, R.string.error_toast_no_urls_in_self);

				} else {

					final String[] linksArr = linksInComment.toArray(new String[linksInComment.size()]);

					final AlertDialog.Builder builder = new AlertDialog.Builder(activity);
					builder.setItems(linksArr, new DialogInterface.OnClickListener() {
						public void onClick(DialogInterface dialog, int which) {
							LinkHandler.onLinkClicked(activity, linksArr[which], false, post.src);
							dialog.dismiss();
						}
					});

					final AlertDialog alert = builder.create();
					alert.setTitle(R.string.action_selftext_links);
					alert.setCanceledOnTouchOutside(true);
					alert.show();
				}

				break;
			}

			case SAVE_IMAGE: {

				final RedditAccount anon = RedditAccountManager.getAnon();

				CacheManager.getInstance(activity).makeRequest(new CacheRequest(General.uriFromString(post.imageUrl), anon, null,
						Constants.Priority.IMAGE_VIEW, 0, CacheRequest.DownloadType.IF_NECESSARY,
						Constants.FileType.IMAGE, false, false, false, activity) {

					@Override
					protected void onCallbackException(Throwable t) {
						BugReportActivity.handleGlobalError(context, t);
					}

					@Override
					protected void onDownloadNecessary() {
						General.quickToast(context, R.string.download_downloading);
					}

					@Override
					protected void onDownloadStarted() {}

					@Override
					protected void onFailure(RequestFailureType type, Throwable t, StatusLine status, String readableMessage) {
						final RRError error = General.getGeneralErrorForFailure(context, type, t, status, url.toString());
						General.showResultDialog(activity, error);
					}

					@Override
					protected void onProgress(boolean authorizationInProgress, long bytesRead, long totalBytes) {}

					@Override
					protected void onSuccess(CacheManager.ReadableCacheFile cacheFile, long timestamp, UUID session, boolean fromCache, String mimetype) {

						File dst = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), General.uriFromString(post.imageUrl).getPath());

						if(dst.exists()) {
							int count = 0;

							while(dst.exists()) {
								count++;
								dst = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), count + "_" + General.uriFromString(post.imageUrl).getPath().substring(1));
							}
						}

						try {
							final InputStream cacheFileInputStream = cacheFile.getInputStream();

							if(cacheFileInputStream == null) {
								notifyFailure(RequestFailureType.CACHE_MISS, null, null, "Could not find cached image");
								return;
							}

							General.copyFile(cacheFileInputStream, dst);

						} catch(IOException e) {
							notifyFailure(RequestFailureType.STORAGE, e, null, "Could not copy file");
							return;
						}

						activity.sendBroadcast(new Intent(Intent.ACTION_MEDIA_SCANNER_SCAN_FILE,
								Uri.parse("file://" + dst.getAbsolutePath()))
						);

						General.quickToast(context, context.getString(R.string.action_save_image_success) + " " + dst.getAbsolutePath());
					}
				});

				break;
			}

			case SHARE: {

				final Intent mailer = new Intent(Intent.ACTION_SEND);
				mailer.setType("text/plain");
				mailer.putExtra(Intent.EXTRA_SUBJECT, post.title);
				mailer.putExtra(Intent.EXTRA_TEXT, post.url);
				activity.startActivity(Intent.createChooser(mailer, activity.getString(R.string.action_share)));
				break;
			}

			case SHARE_COMMENTS: {

				final Intent mailer = new Intent(Intent.ACTION_SEND);
				mailer.setType("text/plain");
				mailer.putExtra(Intent.EXTRA_SUBJECT, "Comments for " + post.title);
				mailer.putExtra(Intent.EXTRA_TEXT, Constants.Reddit.getUri(Constants.Reddit.PATH_COMMENTS + post.idAlone).toString());
				activity.startActivity(Intent.createChooser(mailer, activity.getString(R.string.action_share_comments)));
				break;
			}

			case COPY: {

				ClipboardManager manager = (ClipboardManager) activity.getSystemService(Context.CLIPBOARD_SERVICE);
				manager.setText(post.url);
				break;
			}

			case GOTO_SUBREDDIT: {

				try {
					final Intent intent = new Intent(activity, PostListingActivity.class);
					intent.setData(SubredditPostListURL.getSubreddit(post.src.subreddit).generateJsonUri());
					activity.startActivityForResult(intent, 1);

				} catch(RedditSubreddit.InvalidSubredditNameException e) {
					Toast.makeText(activity, R.string.invalid_subreddit_name, Toast.LENGTH_LONG).show();
				}

				break;
			}

			case USER_PROFILE:
				LinkHandler.onLinkClicked(activity, new UserProfileURL(post.src.author).toString());
				break;

			case PROPERTIES:
				PostPropertiesDialog.newInstance(post.src).show(activity.getFragmentManager(), null);
				break;

			case COMMENTS:
				((RedditPostView.PostSelectionListener)activity).onPostCommentsSelected(post);
				break;

			case LINK:
				((RedditPostView.PostSelectionListener)activity).onPostSelected(post);
				break;

			case COMMENTS_SWITCH:
				if(!(activity instanceof MainActivity)) activity.finish();
				((RedditPostView.PostSelectionListener)activity).onPostCommentsSelected(post);
				break;

			case LINK_SWITCH:
				if(!(activity instanceof MainActivity)) activity.finish();
				((RedditPostView.PostSelectionListener)activity).onPostSelected(post);
				break;

			case ACTION_MENU:
				showActionMenu(activity, post);
				break;

			case REPLY:
				final Intent intent = new Intent(activity, CommentReplyActivity.class);
				intent.putExtra("parentIdAndType", post.idAndType);
				activity.startActivity(intent);
				break;
		}
	}

	private void rebuildSubtitle(Context context) {

		// TODO customise display
		// TODO preference for the X days, X hours thing

		final TypedArray appearance = context.obtainStyledAttributes(new int[]{
				R.attr.rrPostSubtitleBoldCol,
				R.attr.rrPostSubtitleUpvoteCol,
				R.attr.rrPostSubtitleDownvoteCol,
				R.attr.rrFlairBackCol,
				R.attr.rrFlairTextCol
		});

		final int boldCol = appearance.getColor(0, 255),
				rrPostSubtitleUpvoteCol = appearance.getColor(1, 255),
				rrPostSubtitleDownvoteCol = appearance.getColor(2, 255),
				rrFlairBackCol = appearance.getColor(3, 255),
				rrFlairTextCol = appearance.getColor(4, 255);

		final BetterSSB postListDescSb = new BetterSSB();

		final int pointsCol;
		int score = src.score;

		if(Boolean.TRUE.equals(src.likes)) score--;
		if(Boolean.FALSE.equals(src.likes)) score++;

		if(isUpvoted()) {
			pointsCol = rrPostSubtitleUpvoteCol;
			score++;
		} else if(isDownvoted()) {
			pointsCol = rrPostSubtitleDownvoteCol;
			score--;
		} else {
			pointsCol = boldCol;
		}

		if(src.over_18) {
			postListDescSb.append(" NSFW ", BetterSSB.BOLD | BetterSSB.FOREGROUND_COLOR | BetterSSB.BACKGROUND_COLOR,
					Color.WHITE, Color.RED, 1f); // TODO color?
			postListDescSb.append("  ", 0);
		}

		if(src.link_flair_text != null && src.link_flair_text.length() > 0) {
			postListDescSb.append(" " + StringEscapeUtils.unescapeHtml4(src.link_flair_text) + " ", BetterSSB.BOLD | BetterSSB.FOREGROUND_COLOR | BetterSSB.BACKGROUND_COLOR,
					rrFlairTextCol, rrFlairBackCol, 1f);
			postListDescSb.append("  ", 0);
		}

		postListDescSb.append(String.valueOf(score), BetterSSB.BOLD | BetterSSB.FOREGROUND_COLOR, pointsCol, 0, 1f);
		postListDescSb.append(" " + context.getString(R.string.subtitle_points) + " ", 0);
		postListDescSb.append(RRTime.formatDurationFrom(context, src.created_utc * 1000), BetterSSB.BOLD | BetterSSB.FOREGROUND_COLOR, boldCol, 0, 1f);
		postListDescSb.append(" " + context.getString(R.string.subtitle_by) + " ", 0);
		postListDescSb.append(src.author, BetterSSB.BOLD | BetterSSB.FOREGROUND_COLOR, boldCol, 0, 1f);

		if(showSubreddit) {
			postListDescSb.append(" " + context.getString(R.string.subtitle_to) + " ", 0);
			postListDescSb.append(src.subreddit, BetterSSB.BOLD | BetterSSB.FOREGROUND_COLOR, boldCol, 0, 1f);
		}

		postListDescSb.append(" (" + src.domain + ")", 0);

		postListDescription = postListDescSb.get();
	}

	// lol, reddit api
	private static boolean hasThumbnail(final RedditPost post) {
		return post.thumbnail != null
				&& post.thumbnail.length() != 0
				&& !post.thumbnail.equalsIgnoreCase("nsfw")
				&& !post.thumbnail.equalsIgnoreCase("self")
				&& !post.thumbnail.equalsIgnoreCase("default");
	}

	private void downloadThumbnail(final Context context, final int widthPixels, final CacheManager cm, final int listId, final boolean highRes) {

		final String uriStr = highRes ? imageUrl : thumbnailUrl;
		final URI uri = General.uriFromString(uriStr);

		final int priority = highRes ? Constants.Priority.IMAGE_PRECACHE : Constants.Priority.THUMBNAIL;
		final int fileType = highRes ? Constants.FileType.IMAGE : Constants.FileType.THUMBNAIL;

		final RedditAccount anon = RedditAccountManager.getAnon();

		cm.makeRequest(new CacheRequest(uri, anon, null, priority, listId, CacheRequest.DownloadType.IF_NECESSARY, fileType, false, false, false, context) {

			@Override
			protected void onDownloadNecessary() {}

			@Override
			protected void onDownloadStarted() {}

			@Override
			protected void onCallbackException(final Throwable t) {
				// TODO handle -- internal error
				throw new RuntimeException(t);
			}

			@Override
			protected void onFailure(final RequestFailureType type, final Throwable t, final StatusLine status, final String readableMessage) {}

			@Override
			protected void onProgress(final boolean authorizationInProgress, final long bytesRead, final long totalBytes) {}

			@Override
			protected void onSuccess(final CacheManager.ReadableCacheFile cacheFile, final long timestamp, final UUID session, final boolean fromCache, final String mimetype) {

				if(gotHighResThumb && !highRes) return;
				try {

					synchronized(singleImageDecodeLock) {

						BitmapFactory.Options justDecodeBounds = new BitmapFactory.Options();
						justDecodeBounds.inJustDecodeBounds = true;
						BitmapFactory.decodeStream(cacheFile.getInputStream(), null, justDecodeBounds);
						final int width = justDecodeBounds.outWidth;
						final int height = justDecodeBounds.outHeight;

						int factor = 1;

						while(width / (factor + 1) > widthPixels
								&& height / (factor + 1) > widthPixels) factor *= 2;

						BitmapFactory.Options scaledOptions = new BitmapFactory.Options();
						scaledOptions.inSampleSize = factor;

						final Bitmap data = BitmapFactory.decodeStream(cacheFile.getInputStream(), null, scaledOptions);

						if(data == null) return;
						thumbnailCache = ThumbnailScaler.scale(data, widthPixels);
						if(thumbnailCache != data) data.recycle();
					}

					if(highRes) gotHighResThumb = true;

					if(thumbnailCallback != null) thumbnailCallback.betterThumbnailAvailable(thumbnailCache, usageId);

				} catch (OutOfMemoryError e) {
					// TODO handle this better - disable caching of images
					Log.e("RedditPreparedPost", "Out of memory trying to download image");
					e.printStackTrace();
				} catch(Throwable t) {
					// Just ignore it.
				}
			}
		});
	}

	// These operations are ordered so as to avoid race conditions
	public Bitmap getThumbnail(final ThumbnailLoadedCallback callback, final int usageId) {
		this.thumbnailCallback = callback;
		this.usageId = usageId;
		return thumbnailCache;
	}

	public boolean isSelf() {
		return src.is_self;
	}

	public void setRead(boolean read) {
		this.read = read;
	}

	public boolean isRead() {
		return read;
	}

	public boolean isSticky() { return stickied; }

	public void bind(RedditPostView boundView) {
		this.boundView = boundView;
	}

	public void unbind(RedditPostView boundView) {
		if(this.boundView == boundView) this.boundView = null;
	}

	// TODO handle download failure - show red "X" or something
	public static interface ThumbnailLoadedCallback {
		public void betterThumbnailAvailable(Bitmap thumbnail, int usageId);
	}

	public void markAsRead(final Context context) {
		setRead(true);
		refreshView(context);
		final RedditAccount user = RedditAccountManager.getInstance(context).getDefaultAccount();
		RedditChangeDataManager.getInstance(context).update("posts", user, RedditPreparedPost.this, true);
	}

	public void refreshView(final Context context) {
		General.UI_THREAD_HANDLER.post(new Runnable() {
			public void run() {
				rebuildSubtitle(context);
				if(boundView != null) {
					boundView.updateAppearance();
					boundView.requestLayout();
					boundView.invalidate();
				}
			}
		});
	}

	public void action(final Activity activity, final RedditAPI.RedditAction action) {

		if(RedditAccountManager.getInstance(activity).getDefaultAccount().isAnonymous()) {

			General.UI_THREAD_HANDLER.post(new Runnable() {
				public void run() {
					Toast.makeText(activity, "You must be logged in to do that.", Toast.LENGTH_SHORT).show();
				}
			});

			return;
		}

		final int lastVoteDirection = voteDirection;

		switch(action) {
			case DOWNVOTE:
				if(!src.archived) {
					voteDirection = -1;
				}
				break;
			case UNVOTE:
				if(!src.archived) {
					voteDirection = 0;
				}
				break;
			case UPVOTE:
				if(!src.archived) {
					voteDirection = 1;
				}
				break;

			case SAVE: saved = true; break;
			case UNSAVE: saved = false; break;

			case HIDE: hidden = true; break;
			case UNHIDE: hidden = false; break;

			case REPORT: hidden = true; break;

			default:
				throw new RuntimeException("Unknown post action");
		}

		refreshView(activity);

		boolean vote = (action == RedditAPI.RedditAction.DOWNVOTE
				| action == RedditAPI.RedditAction.UPVOTE
				| action == RedditAPI.RedditAction.UNVOTE);

		if(src.archived && vote){
			Toast.makeText(activity, R.string.error_archived_vote, Toast.LENGTH_SHORT)
					.show();
			return;
		}

		final RedditAccount user = RedditAccountManager.getInstance(activity).getDefaultAccount();

		RedditAPI.action(CacheManager.getInstance(activity),
				new APIResponseHandler.ActionResponseHandler(activity) {
					@Override
					protected void onCallbackException(final Throwable t) {
						BugReportActivity.handleGlobalError(context, t);
					}

					@Override
					protected void onFailure(final RequestFailureType type, final Throwable t, final StatusLine status, final String readableMessage) {
						revertOnFailure();
						if(t != null) t.printStackTrace();

						final RRError error = General.getGeneralErrorForFailure(context, type, t, status,
								"Reddit API action: " + action.toString() + " " + url);
						General.UI_THREAD_HANDLER.post(new Runnable() {
							public void run() {
								General.showResultDialog(activity, error);
							}
						});
					}

					@Override
					protected void onFailure(final APIFailureType type) {
						revertOnFailure();

						final RRError error = General.getGeneralErrorForFailure(context, type);
						General.UI_THREAD_HANDLER.post(new Runnable() {
							public void run() {
								General.showResultDialog(activity, error);
							}
						});
					}

					@Override
					protected void onSuccess() {
						lastChange = RRTime.utcCurrentTimeMillis();
						RedditChangeDataManager.getInstance(context).update("posts", user, RedditPreparedPost.this, true);
					}

					private void revertOnFailure() {

						switch(action) {
							case DOWNVOTE:
							case UNVOTE:
							case UPVOTE:
								voteDirection = lastVoteDirection; break;

							case SAVE: saved = false; break;
							case UNSAVE: saved = true; break;

							case HIDE: hidden = false; break;
							case UNHIDE: hidden = true; break;

							case REPORT: hidden = false; break;

							default:
								throw new RuntimeException("Unknown post action");
						}

						refreshView(context);
					}

				}, user, idAndType, action, activity);
	}

	public boolean isUpvoted() {
		return voteDirection == 1;
	}

	public boolean isDownvoted() {
		return voteDirection == -1;
	}

	public boolean isSaved() {
		return saved;
	}

	public boolean isHidden() {
		return hidden;
	}

	public int getVoteDirection() {
		return voteDirection;
	}

	public void updateFromChangeDb(final long dbTimestamp, final int voteDirection, final boolean saved, final boolean hidden, final boolean read) {
		this.lastChange = dbTimestamp;
		this.voteDirection = voteDirection;
		this.saved = saved;
		this.hidden = hidden;
		this.read = read;
	}

	private static class RPVMenuItem {
		public final String title;
		public final Action action;

		private RPVMenuItem(Context context, int titleRes, Action action) {
			this.title = context.getString(titleRes);
			this.action = action;
		}
	}

	public VerticalToolbar generateToolbar(final Activity activity, boolean isComments, final SideToolbarOverlay overlay) {

		final VerticalToolbar toolbar = new VerticalToolbar(activity);
		final EnumSet<Action> itemsPref = PrefsUtility.pref_menus_post_toolbar_items(activity, PreferenceManager.getDefaultSharedPreferences(activity));

		final Action[] possibleItems = {
				Action.ACTION_MENU,
				isComments ? Action.LINK_SWITCH : Action.COMMENTS_SWITCH,
				Action.UPVOTE,
				Action.DOWNVOTE,
				Action.SAVE,
				Action.HIDE,
				Action.REPLY,
				Action.EXTERNAL,
				Action.SAVE_IMAGE,
				Action.SHARE,
				Action.COPY,
				Action.USER_PROFILE,
				Action.PROPERTIES
		};

		// TODO make static
		final EnumMap<Action, Integer> iconsDark = new EnumMap<Action, Integer>(Action.class);
		iconsDark.put(Action.ACTION_MENU, R.drawable.ic_action_overflow);
		iconsDark.put(Action.COMMENTS_SWITCH, R.drawable.ic_action_comments_dark);
		iconsDark.put(Action.LINK_SWITCH, imageUrl != null ? R.drawable.ic_action_image_dark : R.drawable.ic_action_page_dark);
		iconsDark.put(Action.UPVOTE, R.drawable.action_upvote_dark);
		iconsDark.put(Action.DOWNVOTE, R.drawable.action_downvote_dark);
		iconsDark.put(Action.SAVE, R.drawable.ic_action_star_filled_dark);
		iconsDark.put(Action.HIDE, R.drawable.ic_action_cross_dark);
		iconsDark.put(Action.REPLY, R.drawable.ic_action_reply_dark);
		iconsDark.put(Action.EXTERNAL, R.drawable.ic_action_globe_dark);
		iconsDark.put(Action.SAVE_IMAGE, R.drawable.ic_action_save_dark);
		iconsDark.put(Action.SHARE, R.drawable.ic_action_share_dark);
		iconsDark.put(Action.COPY, R.drawable.ic_action_copy_dark);
		iconsDark.put(Action.USER_PROFILE, R.drawable.ic_action_person_dark);
		iconsDark.put(Action.PROPERTIES, R.drawable.ic_action_info_dark);

		final EnumMap<Action, Integer> iconsLight = new EnumMap<Action, Integer>(Action.class);
		iconsLight.put(Action.ACTION_MENU, R.drawable.ic_action_overflow);
		iconsLight.put(Action.COMMENTS_SWITCH, R.drawable.ic_action_comments_light);
		iconsLight.put(Action.LINK_SWITCH, imageUrl != null ? R.drawable.ic_action_image_light : R.drawable.ic_action_page_light);
		iconsLight.put(Action.UPVOTE, R.drawable.action_upvote_light);
		iconsLight.put(Action.DOWNVOTE, R.drawable.action_downvote_light);
		iconsLight.put(Action.SAVE, R.drawable.ic_action_star_filled_light);
		iconsLight.put(Action.HIDE, R.drawable.ic_action_cross_light);
		iconsLight.put(Action.REPLY, R.drawable.ic_action_reply_light);
		iconsLight.put(Action.EXTERNAL, R.drawable.ic_action_globe_light);
		iconsLight.put(Action.SAVE_IMAGE, R.drawable.ic_action_save_light);
		iconsLight.put(Action.SHARE, R.drawable.ic_action_share_light);
		iconsLight.put(Action.COPY, R.drawable.ic_action_copy_light);
		iconsLight.put(Action.USER_PROFILE, R.drawable.ic_action_person_light);
		iconsLight.put(Action.PROPERTIES, R.drawable.ic_action_info_light);

		for(final Action action : possibleItems) {

			if(action == Action.SAVE_IMAGE && imageUrl == null) continue;

			if(itemsPref.contains(action)) {

				final FlatImageButton ib = new FlatImageButton(activity);

				final int buttonPadding = General.dpToPixels(activity, 10);
				ib.setPadding(buttonPadding, buttonPadding, buttonPadding, buttonPadding);

				if(action == Action.UPVOTE && isUpvoted()
						|| action == Action.DOWNVOTE && isDownvoted()
						|| action == Action.SAVE && isSaved()
						|| action == Action.HIDE && isHidden()) {

					ib.setBackgroundColor(Color.WHITE);
					ib.setImageResource(iconsLight.get(action));

				} else {
					ib.setImageResource(iconsDark.get(action));
					// TODO highlight on click
				}

				ib.setOnClickListener(new View.OnClickListener() {
					public void onClick(View v) {

						final Action actionToTake;

						switch(action) {
							case UPVOTE:
								actionToTake = isUpvoted() ? Action.UNVOTE : Action.UPVOTE;
								break;

							case DOWNVOTE:
								actionToTake = isDownvoted() ? Action.UNVOTE : Action.DOWNVOTE;
								break;

							case SAVE:
								actionToTake = isSaved() ? Action.UNSAVE : Action.SAVE;
								break;

							case HIDE:
								actionToTake = isHidden() ? Action.UNHIDE : Action.HIDE;
								break;

							default:
								actionToTake = action;
								break;
						}

						onActionMenuItemSelected(RedditPreparedPost.this, activity, actionToTake);
						overlay.hide();
					}
				});

				toolbar.addItem(ib);
			}
		}

		return toolbar;
	}
}


File: src/main/java/org/quantumbadger/redreader/views/imageview/ImageViewTileLoader.java
/*******************************************************************************
 * This file is part of RedReader.
 *
 * RedReader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * RedReader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with RedReader.  If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

package org.quantumbadger.redreader.views.imageview;

import android.graphics.Bitmap;
import android.util.Log;
import org.quantumbadger.redreader.common.General;

public class ImageViewTileLoader {

	public static interface Listener {
		// All called from UI thread
		public void onTileLoaded(int x, int y, int sampleSize);
		public void onTileLoaderOutOfMemory();
		public void onTileLoaderException(Throwable t);
	}

	private final ImageTileSource mSource;
	private final ImageViewTileLoaderThread mThread;
	private final int mX, mY, mSampleSize;

	private boolean mWanted;

	private Bitmap mResult;

	private final Listener mListener;

	private final Runnable mNotifyRunnable;

	private final Object mLock;

	public ImageViewTileLoader(
			ImageTileSource source,
			ImageViewTileLoaderThread thread,
			int x,
			int y,
			int sampleSize,
			Listener listener,
			final Object lock) {

		mSource = source;
		mThread = thread;
		mX = x;
		mY = y;
		mSampleSize = sampleSize;
		mListener = listener;
		mLock = lock;

		mNotifyRunnable = new Runnable() {
			@Override
			public void run() {
				mListener.onTileLoaded(mX, mY, mSampleSize);
			}
		};
	}

	// Caller must synchronize on mLock
	public void markAsWanted() {

		if(mWanted) {
			return;
		}

		if(mResult != null) {
			throw new RuntimeException("Not wanted, but the image is loaded anyway!");
		}

		mThread.enqueue(this);
		mWanted = true;
	}

	public void doPrepare() {

		synchronized(mLock) {

			if(!mWanted) {
				return;
			}

			if(mResult != null) {
				return;
			}
		}

		final Bitmap tile;

		try {
			tile = mSource.getTile(mSampleSize, mX, mY);

		} catch(OutOfMemoryError e) {
			General.UI_THREAD_HANDLER.post(new NotifyOOMRunnable());
			return;

		} catch(Throwable t) {
			Log.e("ImageViewTileLoader", "Exception in getTile()", t);
			General.UI_THREAD_HANDLER.post(new NotifyErrorRunnable(t));
			return;
		}

		synchronized(mLock) {
			if(mWanted) {
				mResult = tile;
			} else if(tile != null) {
				tile.recycle();
			}
		}

		General.UI_THREAD_HANDLER.post(mNotifyRunnable);
	}

	public Bitmap get() {

		synchronized(mLock) {

			if(!mWanted) {
				throw new RuntimeException("Attempted to get unwanted image!");
			}

			return mResult;
		}
	}

	// Caller must synchronize on mLock
	public void markAsUnwanted() {

		mWanted = false;

		if(mResult != null) {
			mResult.recycle();
			mResult = null;
		}
	}

	private class NotifyOOMRunnable implements Runnable {
		@Override
		public void run() {
			mListener.onTileLoaderOutOfMemory();
		}
	}

	private class NotifyErrorRunnable implements Runnable {

		private final Throwable mError;

		private NotifyErrorRunnable(Throwable mError) {
			this.mError = mError;
		}

		@Override
		public void run() {
			mListener.onTileLoaderException(mError);
		}
	}
}
