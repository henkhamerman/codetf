Refactoring Types: ['Pull Up Method']
r/redreader/activities/BaseActivity.java
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

import android.content.pm.ActivityInfo;
import android.os.Bundle;

import org.holoeverywhere.app.Activity;
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.quantumbadger.redreader.common.PrefsUtility;

public class BaseActivity extends Activity {

	private SharedPreferences sharedPreferences;

	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);
		setOrientationFromPrefs();
	}

	@Override
	protected void onResume() {
		super.onResume();
		setOrientationFromPrefs();
	}

	private void setOrientationFromPrefs() {
		PrefsUtility.ScreenOrientation orientation = PrefsUtility.pref_behaviour_screen_orientation(this, sharedPreferences);
		if (orientation == PrefsUtility.ScreenOrientation.AUTO)
			setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
		else if (orientation == PrefsUtility.ScreenOrientation.PORTRAIT)
			setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
		else if (orientation == PrefsUtility.ScreenOrientation.LANDSCAPE)
			setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/CommentListingActivity.java
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
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.support.v4.app.FragmentTransaction;
import android.view.View;
import com.actionbarsherlock.view.Menu;
import com.actionbarsherlock.view.MenuItem;
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccountChangeListener;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.LinkHandler;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.fragments.CommentListingFragment;
import org.quantumbadger.redreader.fragments.SessionListDialog;
import org.quantumbadger.redreader.listingcontrollers.CommentListingController;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedPost;
import org.quantumbadger.redreader.reddit.url.PostCommentListingURL;
import org.quantumbadger.redreader.reddit.url.RedditURLParser;
import org.quantumbadger.redreader.views.RedditPostView;

import java.util.UUID;

public class CommentListingActivity extends RefreshableActivity
		implements RedditAccountChangeListener,
		SharedPreferences.OnSharedPreferenceChangeListener,
		OptionsMenuUtility.OptionsMenuCommentsListener,
		RedditPostView.PostSelectionListener,
		SessionChangeListener {

	private CommentListingController controller;

	private SharedPreferences sharedPreferences;

	public void onCreate(final Bundle savedInstanceState) {

        PrefsUtility.applyTheme(this);

		super.onCreate(savedInstanceState);

		getSupportActionBar().setHomeButtonEnabled(true);
		getSupportActionBar().setDisplayHomeAsUpEnabled(true);

		OptionsMenuUtility.fixActionBar(this, getString(R.string.app_name));

		sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);
		sharedPreferences.registerOnSharedPreferenceChangeListener(this);

		final boolean solidblack = PrefsUtility.appearance_solidblack(this, sharedPreferences)
				&& PrefsUtility.appearance_theme(this, sharedPreferences) == PrefsUtility.AppearanceTheme.NIGHT;

		// TODO load from savedInstanceState

		final View layout = getLayoutInflater().inflate(R.layout.main_single);
		if(solidblack) layout.setBackgroundColor(Color.BLACK);
		setContentView(layout);

		RedditAccountManager.getInstance(this).addUpdateListener(this);

		if(getIntent() != null) {

			final Intent intent = getIntent();

			final String url = intent.getDataString();
            controller = new CommentListingController(RedditURLParser.parseProbableCommentListing(Uri.parse(url)), this);

			doRefresh(RefreshableFragment.COMMENTS, false);

		} else {
			throw new RuntimeException("Nothing to show! (should load from bundle)"); // TODO
		}
	}

	@Override
	protected void onSaveInstanceState(final Bundle outState) {
		super.onSaveInstanceState(outState);
		// TODO save instance state
	}

	@Override
	public boolean onCreateOptionsMenu(final Menu menu) {
		OptionsMenuUtility.prepare(this, menu, false, false, true, false, false, controller.isSortable(), null, false, true);
		return true;
	}

	public void onRedditAccountChanged() {
		requestRefresh(RefreshableFragment.ALL, false);
	}

	@Override
	protected void doRefresh(final RefreshableFragment which, final boolean force) {
		final CommentListingFragment fragment = controller.get(force);
		final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();
		transaction.replace(R.id.main_single_frame, fragment, "comment_listing_fragment");
		transaction.commit();
		OptionsMenuUtility.fixActionBar(this, controller.getCommentListingUrl().humanReadableName(this, false));
	}

	public void onSharedPreferenceChanged(final SharedPreferences prefs, final String key) {

		if(PrefsUtility.isRestartRequired(this, key)) {
			requestRefresh(RefreshableFragment.RESTART, false);
		}

		if(PrefsUtility.isRefreshRequired(this, key)) {
			requestRefresh(RefreshableFragment.ALL, false);
		}
	}

	@Override
	protected void onDestroy() {
		super.onDestroy();
		sharedPreferences.unregisterOnSharedPreferenceChangeListener(this);
	}

	public void onRefreshComments() {
		controller.setSession(null);
		requestRefresh(RefreshableFragment.COMMENTS, true);
	}

	public void onPastComments() {
		final SessionListDialog sessionListDialog = SessionListDialog.newInstance(controller.getUri(), controller.getSession(), SessionChangeListener.SessionChangeType.COMMENTS);
		sessionListDialog.show(this);
	}

	public void onSortSelected(final PostCommentListingURL.Sort order) {
		controller.setSort(order);
		requestRefresh(RefreshableFragment.COMMENTS, false);
	}

	@Override
	public boolean onOptionsItemSelected(final MenuItem item) {
		switch(item.getItemId()) {
			case android.R.id.home:
                finish();
                return true;
			default:
				return super.onOptionsItemSelected(item);
		}
	}

	public void onSessionRefreshSelected(SessionChangeType type) {
		onRefreshComments();
	}

	public void onSessionSelected(UUID session, SessionChangeType type) {
		controller.setSession(session);
		requestRefresh(RefreshableFragment.COMMENTS, false);
	}

	public void onSessionChanged(UUID session, SessionChangeType type, long timestamp) {
		controller.setSession(session);
	}

	public void onPostSelected(final RedditPreparedPost post) {
		LinkHandler.onLinkClicked(this, post.url, false, post.src);
	}

	public void onPostCommentsSelected(final RedditPreparedPost post) {
		LinkHandler.onLinkClicked(this, PostCommentListingURL.forPostId(post.idAlone).toString(), false);
	}

	@Override
	public void onBackPressed() {
		if(General.onBackPressed()) super.onBackPressed();
	}
}

File: src/main/java/org/quantumbadger/redreader/activities/MainActivity.java
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

import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.support.v4.app.FragmentManager;
import android.support.v4.app.FragmentTransaction;
import android.view.View;
import android.view.WindowManager;
import com.actionbarsherlock.view.Menu;
import com.actionbarsherlock.view.MenuItem;
import org.holoeverywhere.app.AlertDialog;
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.holoeverywhere.widget.EditText;
import org.holoeverywhere.widget.LinearLayout;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountChangeListener;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.adapters.MainMenuSelectionListener;
import org.quantumbadger.redreader.cache.CacheManager;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.LinkHandler;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.fragments.*;
import org.quantumbadger.redreader.listingcontrollers.CommentListingController;
import org.quantumbadger.redreader.listingcontrollers.PostListingController;
import org.quantumbadger.redreader.reddit.api.RedditSubredditSubscriptionManager;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedPost;
import org.quantumbadger.redreader.reddit.things.RedditSubreddit;
import org.quantumbadger.redreader.reddit.url.*;
import org.quantumbadger.redreader.views.RedditPostView;

import java.util.Set;
import java.util.UUID;

public class MainActivity extends RefreshableActivity
		implements MainMenuSelectionListener,
		RedditAccountChangeListener,
		RedditPostView.PostSelectionListener,
		SharedPreferences.OnSharedPreferenceChangeListener,
		OptionsMenuUtility.OptionsMenuSubredditsListener,
		OptionsMenuUtility.OptionsMenuPostsListener,
		OptionsMenuUtility.OptionsMenuCommentsListener,
		SessionChangeListener, RedditSubredditSubscriptionManager.SubredditSubscriptionStateChangeListener {

	private boolean twoPane;

	private MainMenuFragment mainMenuFragment;

	private PostListingController postListingController;
	private PostListingFragment postListingFragment;

	private CommentListingController commentListingController;
	private CommentListingFragment commentListingFragment;

	private boolean isMenuShown = true;

	private SharedPreferences sharedPreferences;

	@Override
	protected void onCreate(final Bundle savedInstanceState) {

		sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);
		if (savedInstanceState == null) {
			if(PrefsUtility.pref_behaviour_skiptofrontpage(this, sharedPreferences))
				onSelected(SubredditPostListURL.getFrontPage());
		}

		PrefsUtility.applyTheme(this);

		OptionsMenuUtility.fixActionBar(this, getString(R.string.app_name));

		sharedPreferences.registerOnSharedPreferenceChangeListener(this);

		final boolean solidblack = PrefsUtility.appearance_solidblack(this, sharedPreferences)
				&& PrefsUtility.appearance_theme(this, sharedPreferences) == PrefsUtility.AppearanceTheme.NIGHT;

		super.onCreate(savedInstanceState);

		twoPane = General.isTablet(this, sharedPreferences);

		final View layout;

		if(twoPane)
			layout = getLayoutInflater().inflate(R.layout.main_double);
		else
			layout = getLayoutInflater().inflate(R.layout.main_single);

		if(solidblack) layout.setBackgroundColor(Color.BLACK);

		setContentView(layout);

		doRefresh(RefreshableFragment.MAIN, false);

		RedditAccountManager.getInstance(this).addUpdateListener(this);

		final PackageInfo pInfo;
		try {
			pInfo = getPackageManager().getPackageInfo(getPackageName(), 0);
		} catch(PackageManager.NameNotFoundException e) {
			throw new RuntimeException(e);
		}

		final int appVersion = pInfo.versionCode;

		if(!sharedPreferences.contains("firstRunMessageShown")) {

			new AlertDialog.Builder(this)
					.setTitle(R.string.firstrun_login_title)
					.setMessage(R.string.firstrun_login_message)
					.setPositiveButton(R.string.firstrun_login_button_now,
							new DialogInterface.OnClickListener() {
								public void onClick(final DialogInterface dialog, final int which) {
									new AccountListDialog().show(MainActivity.this);
								}
							})
					.setNegativeButton(R.string.firstrun_login_button_later, null)
					.show();

			final SharedPreferences.Editor edit = sharedPreferences.edit();
			edit.putString("firstRunMessageShown", "true");
			edit.commit();

		} else if(sharedPreferences.contains("lastVersion")) {

			final int lastVersion = sharedPreferences.getInt("lastVersion", 0);

			if(lastVersion != appVersion) {

				General.quickToast(this, "Updated to version " + pInfo.versionName);

				sharedPreferences.edit().putInt("lastVersion", appVersion).commit();
				ChangelogDialog.newInstance().show(this);

				if(lastVersion <= 51) {
					// Upgrading from v1.8.6.3 or lower

					final Set<String> existingCommentHeaderItems = PrefsUtility.getStringSet(
							R.string.pref_appearance_comment_header_items_key,
							R.array.pref_appearance_comment_header_items_default,
							this,
							sharedPreferences
					);

					existingCommentHeaderItems.add("gold");

					sharedPreferences.edit().putStringSet(
							R.string.pref_appearance_comment_header_items_key,
							existingCommentHeaderItems
					).commit();

					new Thread() {
						@Override
						public void run() {
							CacheManager.getInstance(MainActivity.this).emptyTheWholeCache();
						}
					}.start();
				}
			}

		} else {
			sharedPreferences.edit().putInt("lastVersion", appVersion).commit();
			ChangelogDialog.newInstance().show(this);
		}

		addSubscriptionListener();

		Boolean startInbox = getIntent().getBooleanExtra("isNewMessage", false);
		if(startInbox) {
			startActivity(new Intent(this, InboxListingActivity.class));
		}
	}

	private void addSubscriptionListener() {
		RedditSubredditSubscriptionManager
				.getSingleton(this, RedditAccountManager.getInstance(this).getDefaultAccount())
				.addListener(this);
	}

	public void onSelected(final MainMenuFragment.MainMenuAction type, final String name) {

		final String username = RedditAccountManager.getInstance(this).getDefaultAccount().username;

		switch(type) {

			case FRONTPAGE:
				onSelected(SubredditPostListURL.getFrontPage());
				break;

			case ALL:
				onSelected(SubredditPostListURL.getAll());
				break;

			case SUBMITTED:
				onSelected(UserPostListingURL.getSubmitted(username));
				break;

			case SAVED:
				onSelected(UserPostListingURL.getSaved(username));
				break;

			case HIDDEN:
				onSelected(UserPostListingURL.getHidden(username));
				break;

			case UPVOTED:
				onSelected(UserPostListingURL.getLiked(username));
				break;

			case DOWNVOTED:
				onSelected(UserPostListingURL.getDisliked(username));
				break;

			case PROFILE:
				LinkHandler.onLinkClicked(this, new UserProfileURL(RedditAccountManager.getInstance(this).getDefaultAccount().username).toString());
				break;

			case CUSTOM: {

				final AlertDialog.Builder alertBuilder = new AlertDialog.Builder(this);
				final LinearLayout layout = (LinearLayout) getLayoutInflater().inflate(R.layout.dialog_editbox);
				final EditText editText = (EditText)layout.findViewById(R.id.dialog_editbox_edittext);

				editText.requestFocus();

				alertBuilder.setView(layout);
				alertBuilder.setTitle(R.string.mainmenu_custom);

				alertBuilder.setPositiveButton(R.string.dialog_go, new DialogInterface.OnClickListener() {
					public void onClick(DialogInterface dialog, int which) {

						final String subredditInput = editText.getText().toString().trim();

						try {
							final String normalizedName = RedditSubreddit.stripRPrefix(subredditInput);
							final RedditURLParser.RedditURL redditURL = SubredditPostListURL.getSubreddit(normalizedName);
							if(redditURL == null || redditURL.pathType() != RedditURLParser.PathType.SubredditPostListingURL) {
								General.quickToast(MainActivity.this, R.string.mainmenu_custom_invalid_name);
							} else {
								onSelected(redditURL.asSubredditPostListURL());
							}
						} catch(RedditSubreddit.InvalidSubredditNameException e){
							General.quickToast(MainActivity.this, R.string.mainmenu_custom_invalid_name);
						}
					}
				});

				alertBuilder.setNegativeButton(R.string.dialog_cancel, null);

				final AlertDialog alertDialog = alertBuilder.create();
				alertDialog.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE);
				alertDialog.show();

				break;
			}

			case INBOX:
				startActivity(new Intent(this, InboxListingActivity.class));
				break;

			case MODMAIL: {
				final Intent intent = new Intent(this, InboxListingActivity.class);
				intent.putExtra("modmail", true);
				startActivity(intent);
				break;
			}
		}
	}

	public void onSelected(final PostListingURL url) {

		if(url == null) {
			return;
		}

		if(twoPane) {

			postListingController = new PostListingController(url);
			requestRefresh(RefreshableFragment.POSTS, false);

		} else {
			final Intent intent = new Intent(this, PostListingActivity.class);
			intent.setData(url.generateJsonUri());
			startActivityForResult(intent, 1);
		}
	}

	public void onRedditAccountChanged() {
		addSubscriptionListener();
		postInvalidateOptionsMenu();
		requestRefresh(RefreshableFragment.ALL, false);
	}

	@Override
	protected void doRefresh(final RefreshableFragment which, final boolean force) {

		if(which == RefreshableFragment.MAIN_RELAYOUT) {

			final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();

			if(postListingFragment != null) {
				postListingFragment.cancel();
				transaction.remove(postListingFragment);
			}

			if(commentListingFragment != null) {
				transaction.remove(commentListingFragment);
			}

			transaction.commit();
			getSupportFragmentManager().executePendingTransactions(); // may not be necessary...

			mainMenuFragment = null;
			postListingFragment = null;
			commentListingFragment = null;

			twoPane = General.isTablet(this, sharedPreferences);

			if(twoPane)
				setContentView(R.layout.main_double);
			else
				setContentView(R.layout.main_single);

			invalidateOptionsMenu();
			requestRefresh(RefreshableFragment.MAIN, false);

			return;
		}

		if(twoPane) {

			final int postContainer = isMenuShown ? R.id.main_right_frame : R.id.main_left_frame;

			if(isMenuShown && (which == RefreshableFragment.ALL || which == RefreshableFragment.MAIN)) {
				mainMenuFragment = MainMenuFragment.newInstance(force);
				final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();
				transaction.replace(R.id.main_left_frame, mainMenuFragment, "main_fragment");
				transaction.commit();
			}

			if(postListingController != null && (which == RefreshableFragment.ALL || which == RefreshableFragment.POSTS)) {
				if(force && postListingFragment != null) postListingFragment.cancel();
				postListingFragment = postListingController.get(force);
				final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();
				transaction.replace(postContainer, postListingFragment, "posts_fragment");
				transaction.commit();
			}

			if(commentListingController != null && (which == RefreshableFragment.ALL || which == RefreshableFragment.COMMENTS)) {
				commentListingFragment = commentListingController.get(force);
				final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();
				transaction.replace(R.id.main_right_frame, commentListingFragment, "comments_fragment");
				transaction.commit();
			}

		} else {

			if(which == RefreshableFragment.ALL || which == RefreshableFragment.MAIN) {
				mainMenuFragment = MainMenuFragment.newInstance(force);
				final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();
				transaction.replace(R.id.main_single_frame, mainMenuFragment, "main_fragment");
				transaction.commit();
			}
		}

		invalidateOptionsMenu();
	}

	@Override
	public void onBackPressed() {

		if(!General.onBackPressed()) return;

		if(!twoPane || isMenuShown) {
			super.onBackPressed();
			return;
		}

		isMenuShown = true;

		final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();

		mainMenuFragment = MainMenuFragment.newInstance(false); // TODO preserve position
		postListingFragment = postListingController.get(false); // TODO preserve position

		transaction.replace(R.id.main_left_frame, mainMenuFragment);
		transaction.replace(R.id.main_right_frame, postListingFragment);
		commentListingFragment = null;

		transaction.commit();

		invalidateOptionsMenu();
	}

	public void onPostCommentsSelected(final RedditPreparedPost post) {

		if(twoPane) {

			commentListingController = new CommentListingController(PostCommentListingURL.forPostId(post.idAlone), this);

			if(isMenuShown) {

				final FragmentManager fm = getSupportFragmentManager();

				fm.beginTransaction().remove(postListingFragment).commit();
				fm.executePendingTransactions();

				final FragmentTransaction transaction = fm.beginTransaction();
				commentListingFragment = commentListingController.get(false);
				transaction.replace(R.id.main_left_frame, postListingFragment); // TODO fix this...
				transaction.replace(R.id.main_right_frame, commentListingFragment);

				mainMenuFragment = null;
				isMenuShown = false;

				transaction.commit();

				invalidateOptionsMenu();

			} else {
				requestRefresh(RefreshableFragment.COMMENTS, false);
			}

		} else {
			LinkHandler.onLinkClicked(this, PostCommentListingURL.forPostId(post.idAlone).toString(), false);
		}
	}

	public void onPostSelected(final RedditPreparedPost post) {
		if(post.isSelf()) {
			onPostCommentsSelected(post);
		} else {
			LinkHandler.onLinkClicked(this, post.url, false, post.src);
		}
	}

	public void onSharedPreferenceChanged(final SharedPreferences prefs, final String key) {

		if(PrefsUtility.isRestartRequired(this, key)) {
			requestRefresh(RefreshableFragment.RESTART, false);
		}

		if(PrefsUtility.isReLayoutRequired(this, key)) {
			requestRefresh(RefreshableFragment.MAIN_RELAYOUT, false);

		} else if(PrefsUtility.isRefreshRequired(this, key)) {
			requestRefresh(RefreshableFragment.ALL, false);
		}
	}

	@Override
	protected void onDestroy() {
		super.onDestroy();
		sharedPreferences.unregisterOnSharedPreferenceChangeListener(this);
	}

	@Override
	public boolean onCreateOptionsMenu(final Menu menu) {

		final boolean postsVisible = postListingFragment != null;
		final boolean commentsVisible = commentListingFragment != null;

		final boolean postsSortable = postListingController != null && postListingController.isSortable();
		final boolean commentsSortable = commentListingController != null && commentListingController.isSortable();

		final RedditAccount user = RedditAccountManager.getInstance(this).getDefaultAccount();
		final RedditSubredditSubscriptionManager.SubredditSubscriptionState subredditSubscriptionState;
		final RedditSubredditSubscriptionManager subredditSubscriptionManager
				= RedditSubredditSubscriptionManager.getSingleton(this, user);

		if(postsVisible
				&& !user.isAnonymous()
				&& postListingController.isSubreddit()
				&& subredditSubscriptionManager.areSubscriptionsReady()
				&& postListingFragment != null
				&& postListingFragment.getSubreddit() != null) {

			subredditSubscriptionState = subredditSubscriptionManager.getSubscriptionState(
					postListingController.subredditCanonicalName());

		} else {
			subredditSubscriptionState = null;
		}

		final String subredditDescription = postListingFragment != null && postListingFragment.getSubreddit() != null
				? postListingFragment.getSubreddit().description_html : null;

		OptionsMenuUtility.prepare(
				this,
				menu,
				isMenuShown,
				postsVisible,
				commentsVisible,
				false,
				postsSortable,
				commentsSortable,
				subredditSubscriptionState,
				postsVisible && subredditDescription != null && subredditDescription.length() > 0,
				true);

		getSupportActionBar().setHomeButtonEnabled(!isMenuShown);
		getSupportActionBar().setDisplayHomeAsUpEnabled(!isMenuShown);

		return true;
	}

	public void onRefreshComments() {
		commentListingController.setSession(null);
		requestRefresh(RefreshableFragment.COMMENTS, true);
	}

	public void onPastComments() {
		final SessionListDialog sessionListDialog = SessionListDialog.newInstance(commentListingController.getUri(), commentListingController.getSession(), SessionChangeListener.SessionChangeType.COMMENTS);
		sessionListDialog.show(this);
	}

	public void onSortSelected(final PostCommentListingURL.Sort order) {
		commentListingController.setSort(order);
		requestRefresh(RefreshableFragment.COMMENTS, false);
	}

	public void onRefreshPosts() {
		postListingController.setSession(null);
		requestRefresh(RefreshableFragment.POSTS, true);
	}

	public void onPastPosts() {
		final SessionListDialog sessionListDialog = SessionListDialog.newInstance(postListingController.getUri(), postListingController.getSession(), SessionChangeListener.SessionChangeType.POSTS);
		sessionListDialog.show(this);
	}

	public void onSubmitPost() {
		final Intent intent = new Intent(this, PostSubmitActivity.class);
		if(postListingController.isSubreddit()) {
			intent.putExtra("subreddit", postListingController.subredditCanonicalName());
		}
		startActivity(intent);
	}

	public void onSortSelected(final PostListingController.Sort order) {
		postListingController.setSort(order);
		requestRefresh(RefreshableFragment.POSTS, false);
	}

	public void onSearchPosts() {
		PostListingActivity.onSearchPosts(postListingController, this);
	}

	@Override
	public void onSubscribe() {
		if(postListingFragment != null) postListingFragment.onSubscribe();
	}

	@Override
	public void onUnsubscribe() {
		if(postListingFragment != null) postListingFragment.onUnsubscribe();
	}

	@Override
	public void onSidebar() {
		final Intent intent = new Intent(this, HtmlViewActivity.class);
		intent.putExtra("html", postListingFragment.getSubreddit().getSidebarHtml(PrefsUtility.isNightMode(this)));
		intent.putExtra("title", String.format("%s: %s",
				getString(R.string.sidebar_activity_title),
				postListingFragment.getSubreddit().url));
		startActivityForResult(intent, 1);
	}

	public void onRefreshSubreddits() {
		requestRefresh(RefreshableFragment.MAIN, true);
	}

	@Override
	public boolean onOptionsItemSelected(final MenuItem item) {
		switch(item.getItemId()) {
			case android.R.id.home:
				onBackPressed();
				return true;
			default:
				return super.onOptionsItemSelected(item);
		}
	}

	public void onSessionSelected(UUID session, SessionChangeType type) {

		switch(type) {
			case POSTS:
				postListingController.setSession(session);
				requestRefresh(RefreshableFragment.POSTS, false);
				break;
			case COMMENTS:
				commentListingController.setSession(session);
				requestRefresh(RefreshableFragment.COMMENTS, false);
				break;
		}
	}

	public void onSessionRefreshSelected(SessionChangeType type) {
		switch(type) {
			case POSTS:
				onRefreshPosts();
				break;
			case COMMENTS:
				onRefreshComments();
				break;
		}
	}

	public void onSessionChanged(UUID session, SessionChangeType type, long timestamp) {

		switch(type) {
			case POSTS:
				if(postListingController != null) postListingController.setSession(session);
				break;
			case COMMENTS:
				if(commentListingController != null) commentListingController.setSession(session);
				break;
		}
	}

	@Override
	public void onSubredditSubscriptionListUpdated(RedditSubredditSubscriptionManager subredditSubscriptionManager) {
		postInvalidateOptionsMenu();
	}

	@Override
	public void onSubredditSubscriptionAttempted(RedditSubredditSubscriptionManager subredditSubscriptionManager) {
		postInvalidateOptionsMenu();
	}

	@Override
	public void onSubredditUnsubscriptionAttempted(RedditSubredditSubscriptionManager subredditSubscriptionManager) {
		postInvalidateOptionsMenu();
	}

	private void postInvalidateOptionsMenu() {
		runOnUiThread(new Runnable() {
			@Override
			public void run() {
				invalidateOptionsMenu();
			}
		});
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/MoreCommentsListingActivity.java
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
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.support.v4.app.FragmentTransaction;
import android.view.View;
import com.actionbarsherlock.view.Menu;
import com.actionbarsherlock.view.MenuItem;
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccountChangeListener;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.cache.CacheRequest;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.LinkHandler;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.fragments.CommentListingFragment;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedPost;
import org.quantumbadger.redreader.reddit.url.PostCommentListingURL;
import org.quantumbadger.redreader.reddit.url.RedditURLParser;
import org.quantumbadger.redreader.views.RedditPostView;

import java.util.ArrayList;

public class MoreCommentsListingActivity extends RefreshableActivity
		implements RedditAccountChangeListener,
		SharedPreferences.OnSharedPreferenceChangeListener,
		OptionsMenuUtility.OptionsMenuCommentsListener,
		RedditPostView.PostSelectionListener {

	private SharedPreferences sharedPreferences;
	private final ArrayList<RedditURLParser.RedditURL> mUrls = new ArrayList<RedditURLParser.RedditURL>(32);

	public void onCreate(final Bundle savedInstanceState) {

        PrefsUtility.applyTheme(this);

		super.onCreate(savedInstanceState);

		getSupportActionBar().setHomeButtonEnabled(true);
		getSupportActionBar().setDisplayHomeAsUpEnabled(true);

		OptionsMenuUtility.fixActionBar(this, getString(R.string.app_name));

		sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);
		sharedPreferences.registerOnSharedPreferenceChangeListener(this);

		final boolean solidblack = PrefsUtility.appearance_solidblack(this, sharedPreferences)
				&& PrefsUtility.appearance_theme(this, sharedPreferences) == PrefsUtility.AppearanceTheme.NIGHT;

		// TODO load from savedInstanceState

		final View layout = getLayoutInflater().inflate(R.layout.main_single);
		if(solidblack) layout.setBackgroundColor(Color.BLACK);
		setContentView(layout);

		RedditAccountManager.getInstance(this).addUpdateListener(this);

		if(getIntent() != null) {

			final Intent intent = getIntent();

			final ArrayList<String> urls = intent.getStringArrayListExtra("urls");

			for(final String url : urls) {
				final RedditURLParser.RedditURL redditURL = RedditURLParser.parseProbableCommentListing(Uri.parse(url));
				if(redditURL != null) {
					mUrls.add(redditURL);
				}
			}

			doRefresh(RefreshableFragment.COMMENTS, false);

		} else {
			throw new RuntimeException("Nothing to show! (should load from bundle)"); // TODO
		}
	}

	@Override
	protected void onSaveInstanceState(final Bundle outState) {
		super.onSaveInstanceState(outState);
		// TODO save instance state
	}

	@Override
	public boolean onCreateOptionsMenu(final Menu menu) {
		OptionsMenuUtility.prepare(this, menu, false, false, true, false, false, false, null, false, false);
		return true;
	}

	public void onRedditAccountChanged() {
		requestRefresh(RefreshableFragment.ALL, false);
	}

	@Override
	protected void doRefresh(final RefreshableFragment which, final boolean force) {

		final CommentListingFragment fragment = CommentListingFragment.newInstance(
				mUrls,
				null,
				force ? CacheRequest.DownloadType.FORCE : CacheRequest.DownloadType.IF_NECESSARY);

		final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();
		transaction.replace(R.id.main_single_frame, fragment, "comment_listing_fragment");
		transaction.commit();
		OptionsMenuUtility.fixActionBar(this, "More Comments"); // TODO string
	}

	public void onSharedPreferenceChanged(final SharedPreferences prefs, final String key) {

		if(PrefsUtility.isRestartRequired(this, key)) {
			requestRefresh(RefreshableFragment.RESTART, false);
		}

		if(PrefsUtility.isRefreshRequired(this, key)) {
			requestRefresh(RefreshableFragment.ALL, false);
		}
	}

	@Override
	protected void onDestroy() {
		super.onDestroy();
		sharedPreferences.unregisterOnSharedPreferenceChangeListener(this);
	}

	public void onRefreshComments() {
		requestRefresh(RefreshableFragment.COMMENTS, true);
	}

	@Override
	public void onPastComments() {}

	@Override
	public void onSortSelected(final PostCommentListingURL.Sort order) {}

	@Override
	public boolean onOptionsItemSelected(final MenuItem item) {
		switch(item.getItemId()) {
			case android.R.id.home:
                finish();
                return true;
			default:
				return super.onOptionsItemSelected(item);
		}
	}

	public void onPostSelected(final RedditPreparedPost post) {
		LinkHandler.onLinkClicked(this, post.url, false, post.src);
	}

	public void onPostCommentsSelected(final RedditPreparedPost post) {
		LinkHandler.onLinkClicked(this, PostCommentListingURL.forPostId(post.idAlone).toString(), false);
	}

	@Override
	public void onBackPressed() {
		if(General.onBackPressed()) super.onBackPressed();
	}
}

File: src/main/java/org/quantumbadger/redreader/activities/OptionsMenuUtility.java
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

import android.content.DialogInterface;
import android.content.Intent;
import android.content.res.TypedArray;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import com.actionbarsherlock.view.Menu;
import com.actionbarsherlock.view.MenuItem;
import com.actionbarsherlock.view.SubMenu;
import org.holoeverywhere.app.Activity;
import org.holoeverywhere.app.AlertDialog;
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.common.BetterSSB;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.common.UnexpectedInternalStateException;
import org.quantumbadger.redreader.fragments.AccountListDialog;
import org.quantumbadger.redreader.listingcontrollers.PostListingController;
import org.quantumbadger.redreader.reddit.api.RedditSubredditSubscriptionManager;
import org.quantumbadger.redreader.reddit.url.PostCommentListingURL;
import org.quantumbadger.redreader.settings.SettingsActivity;

public final class OptionsMenuUtility {

	private static enum Option {
		ACCOUNTS,
		SETTINGS,
		SUBMIT_POST,
		SEARCH,
		REFRESH_SUBREDDITS,
		REFRESH_POSTS,
		REFRESH_COMMENTS,
		PAST_POSTS,
		THEMES,
		PAST_COMMENTS,
		SUBSCRIBE,
		SUBSCRIBING,
		UNSUBSCRIBING,
		UNSUBSCRIBE,
		SIDEBAR
	}

	public static <E extends Activity & OptionsMenuListener> void prepare(
			final E activity, final Menu menu,
			final boolean subredditsVisible, final boolean postsVisible, final boolean commentsVisible,
			final boolean areSearchResults,
			final boolean postsSortable, final boolean commentsSortable,
			final RedditSubredditSubscriptionManager.SubredditSubscriptionState subredditSubscriptionState,
			final boolean subredditHasSidebar,
			final boolean pastCommentsSupported) {

		if(subredditsVisible && !postsVisible && !commentsVisible) {
			add(activity, menu, Option.REFRESH_SUBREDDITS, false);

		} else if(!subredditsVisible && postsVisible && !commentsVisible) {
			if(postsSortable) {
				if (areSearchResults)
					addAllSearchSorts(activity, menu, true);
				else
					addAllPostSorts(activity, menu, true);
			}
			add(activity, menu, Option.REFRESH_POSTS, false);
			add(activity, menu, Option.PAST_POSTS, false);
			add(activity, menu, Option.SUBMIT_POST, false);
			add(activity, menu, Option.SEARCH, false);
			if(subredditSubscriptionState != null) {
				addSubscriptionItem(activity, menu, subredditSubscriptionState);
				if(subredditHasSidebar) add(activity, menu, Option.SIDEBAR, false);
			}

		} else if(!subredditsVisible && !postsVisible && commentsVisible) {
			if(commentsSortable) addAllCommentSorts(activity, menu, true);
			add(activity, menu, Option.REFRESH_COMMENTS, false);
			if(pastCommentsSupported) {
				add(activity, menu, Option.PAST_COMMENTS, false);
			}

		} else {

			if(postsVisible && commentsVisible) {

				final SubMenu sortMenu = menu.addSubMenu(R.string.options_sort);
				sortMenu.getItem().setIcon(R.drawable.ic_action_sort);
				sortMenu.getItem().setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);

				if(postsSortable) {
					if (areSearchResults)
						addAllSearchSorts(activity, sortMenu, false);
					else
						addAllPostSorts(activity, sortMenu, false);
				}
				if(commentsSortable) addAllCommentSorts(activity, sortMenu, false);

				final SubMenu pastMenu = menu.addSubMenu(R.string.options_past);
				add(activity, pastMenu, Option.PAST_POSTS, true);
				if(pastCommentsSupported) {
					add(activity, pastMenu, Option.PAST_COMMENTS, true);
				}

			} else if(postsVisible) {
				if(postsSortable) {
					if (areSearchResults)
						addAllSearchSorts(activity, menu, true);
					else
						addAllPostSorts(activity, menu, true);
				}
				add(activity, menu, Option.PAST_POSTS, false);
			}

			final SubMenu refreshMenu = menu.addSubMenu(R.string.options_refresh);
			refreshMenu.getItem().setIcon(R.drawable.ic_navigation_refresh);
			refreshMenu.getItem().setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);

			if(subredditsVisible) add(activity, refreshMenu, Option.REFRESH_SUBREDDITS, true);
			if(postsVisible) {
				add(activity, refreshMenu, Option.REFRESH_POSTS, true);
				add(activity, menu, Option.SUBMIT_POST, false);
				add(activity, menu, Option.SEARCH, false);
				if(subredditSubscriptionState != null) {
					addSubscriptionItem(activity, menu, subredditSubscriptionState);
					if(subredditHasSidebar) add(activity, menu, Option.SIDEBAR, false);
				}
			}
			if(commentsVisible) add(activity, refreshMenu, Option.REFRESH_COMMENTS, true);
		}

		add(activity, menu, Option.ACCOUNTS, false);
		add(activity, menu, Option.THEMES, false);
		add(activity, menu, Option.SETTINGS, false);
	}

	private static void addSubscriptionItem(final Activity activity, final Menu menu,
			final RedditSubredditSubscriptionManager.SubredditSubscriptionState subredditSubscriptionState) {

		if(subredditSubscriptionState == null) return;

		switch(subredditSubscriptionState) {
			case NOT_SUBSCRIBED:
				add(activity, menu, Option.SUBSCRIBE, false);
				return;
			case SUBSCRIBED:
				add(activity, menu, Option.UNSUBSCRIBE, false);
				return;
			case SUBSCRIBING:
				add(activity, menu, Option.SUBSCRIBING, false);
				return;
			case UNSUBSCRIBING:
				add(activity, menu, Option.UNSUBSCRIBING, false);
				return;
			default:
				throw new UnexpectedInternalStateException("Unknown subscription state");
		}

	}

	private static void add(final Activity activity, final Menu menu, final Option option, final boolean longText) {

		switch(option) {

			case ACCOUNTS:
				menu.add(activity.getString(R.string.options_accounts)).setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
					public boolean onMenuItemClick(final MenuItem item) {
						new AccountListDialog().show(activity);
						return true;
					}
				});
				break;

			case SETTINGS:
				menu.add(activity.getString(R.string.options_settings)).setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
					public boolean onMenuItemClick(final MenuItem item) {
						final Intent intent = new Intent(activity, SettingsActivity.class);
						activity.startActivityForResult(intent, 1);
						return true;
					}
				});
				break;

			case THEMES:
				menu.add(activity.getString(R.string.options_theme)).setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
					public boolean onMenuItemClick(final MenuItem item) {

						final SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(activity);
						final PrefsUtility.AppearanceTheme currentTheme = PrefsUtility.appearance_theme(activity, prefs);

						final String[] themeNames = activity.getResources().getStringArray(R.array.pref_appearance_theme);
						final String[] themeValues = activity.getResources().getStringArray(R.array.pref_appearance_theme_return);

						int selectedPos = -1;
						for(int i = 0; i < themeValues.length; i++) {
							if(PrefsUtility.AppearanceTheme.valueOf(themeValues[i].toUpperCase()).equals(currentTheme)) {
								selectedPos = i;
								break;
							}
						}

						final AlertDialog.Builder dialog = new AlertDialog.Builder(activity);
						dialog.setTitle(R.string.pref_appearance_theme_title);

						dialog.setSingleChoiceItems(themeNames, selectedPos, new DialogInterface.OnClickListener() {
							public void onClick(DialogInterface dialog, int item) {
								final SharedPreferences.Editor editor = prefs.edit();
								editor.putString(activity.getString(R.string.pref_appearance_theme_key), themeValues[item]);
								editor.commit();
								dialog.dismiss();
							}
						});

						final AlertDialog alert = dialog.create();
						alert.show();
						return true;
					}
				});
				break;

			case REFRESH_SUBREDDITS:
				final MenuItem refreshSubreddits = menu.add(activity.getString(R.string.options_refresh_subreddits))
						.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
							public boolean onMenuItemClick(final MenuItem item) {
								((OptionsMenuSubredditsListener) activity).onRefreshSubreddits();
								return true;
							}
						});

				refreshSubreddits.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
				if(!longText) refreshSubreddits.setIcon(R.drawable.ic_navigation_refresh);

				break;

			case REFRESH_POSTS:
				final MenuItem refreshPosts = menu.add(activity.getString(R.string.options_refresh_posts))
						.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
							public boolean onMenuItemClick(final MenuItem item) {
								((OptionsMenuPostsListener) activity).onRefreshPosts();
								return true;
							}
						});

				refreshPosts.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
				if(!longText) refreshPosts.setIcon(R.drawable.ic_navigation_refresh);

				break;

			case SUBMIT_POST:
				menu.add(activity.getString(R.string.options_submit_post))
						.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
							public boolean onMenuItemClick(final MenuItem item) {
								((OptionsMenuPostsListener) activity).onSubmitPost();
								return true;
							}
						});

				break;

			case SEARCH:
				menu.add(activity.getString(R.string.action_search))
						.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
							public boolean onMenuItemClick(final MenuItem item) {
								((OptionsMenuPostsListener) activity).onSearchPosts();
								return true;
							}
						});

				break;

			case REFRESH_COMMENTS:
				final MenuItem refreshComments = menu.add(activity.getString(R.string.options_refresh_comments))
						.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
							public boolean onMenuItemClick(final MenuItem item) {
								((OptionsMenuCommentsListener) activity).onRefreshComments();
								return true;
							}
						});

				refreshComments.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
				if(!longText) refreshComments.setIcon(R.drawable.ic_navigation_refresh);

				break;

			case PAST_POSTS:
				menu.add(activity.getString(longText ? R.string.options_past_posts : R.string.options_past))
						.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
							public boolean onMenuItemClick(final MenuItem item) {
								((OptionsMenuPostsListener)activity).onPastPosts();
								return true;
							}
						});
				break;

			case PAST_COMMENTS:
				menu.add(activity.getString(longText ? R.string.options_past_comments : R.string.options_past))
						.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
							public boolean onMenuItemClick(final MenuItem item) {
								((OptionsMenuCommentsListener)activity).onPastComments();
								return true;
							}
						});
				break;

			case SUBSCRIBE:
				menu.add(activity.getString(R.string.options_subscribe))
						.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
							public boolean onMenuItemClick(final MenuItem item) {
								((OptionsMenuPostsListener)activity).onSubscribe();
								return true;
							}
						});
				break;

			case UNSUBSCRIBE:
				menu.add(activity.getString(R.string.options_unsubscribe))
					.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
						public boolean onMenuItemClick(final MenuItem item) {
							((OptionsMenuPostsListener)activity).onUnsubscribe();
							return true;
						}
					});
			break;

			case UNSUBSCRIBING:
				menu.add(activity.getString(R.string.options_unsubscribing)).setEnabled(false);
				break;

			case SUBSCRIBING:
				menu.add(activity.getString(R.string.options_subscribing)).setEnabled(false);
				break;

			case SIDEBAR:
				menu.add(activity.getString(R.string.options_sidebar)).setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
					public boolean onMenuItemClick(final MenuItem item) {
						((OptionsMenuPostsListener)activity).onSidebar();
						return true;
					}
				});
				break;

			default:
				BugReportActivity.handleGlobalError(activity, "Unknown menu option added");
		}
	}

	private static void addAllPostSorts(final Activity activity, final Menu menu, final boolean icon) {

		final SubMenu sortPosts = menu.addSubMenu(R.string.options_sort_posts);

		if(icon) {
			sortPosts.getItem().setIcon(R.drawable.ic_action_sort);
			sortPosts.getItem().setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
		}

		addSort(activity, sortPosts, R.string.sort_posts_hot, PostListingController.Sort.HOT);
		addSort(activity, sortPosts, R.string.sort_posts_new, PostListingController.Sort.NEW);
		addSort(activity, sortPosts, R.string.sort_posts_rising, PostListingController.Sort.RISING);
		addSort(activity, sortPosts, R.string.sort_posts_controversial, PostListingController.Sort.CONTROVERSIAL);

		final SubMenu sortPostsTop = sortPosts.addSubMenu(R.string.sort_posts_top);

		addSort(activity, sortPostsTop, R.string.sort_posts_top_hour, PostListingController.Sort.TOP_HOUR);
		addSort(activity, sortPostsTop, R.string.sort_posts_top_today, PostListingController.Sort.TOP_DAY);
		addSort(activity, sortPostsTop, R.string.sort_posts_top_week, PostListingController.Sort.TOP_WEEK);
		addSort(activity, sortPostsTop, R.string.sort_posts_top_month, PostListingController.Sort.TOP_MONTH);
		addSort(activity, sortPostsTop, R.string.sort_posts_top_year, PostListingController.Sort.TOP_YEAR);
		addSort(activity, sortPostsTop, R.string.sort_posts_top_all, PostListingController.Sort.TOP_ALL);
	}

	private static void addAllSearchSorts(final Activity activity, final Menu menu, final boolean icon) {

		final SubMenu sortPosts = menu.addSubMenu(R.string.options_sort_posts);

		if(icon) {
			sortPosts.getItem().setIcon(R.drawable.ic_action_sort);
			sortPosts.getItem().setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
		}

		addSort(activity, sortPosts, R.string.sort_posts_relevance, PostListingController.Sort.RELEVANCE);
		addSort(activity, sortPosts, R.string.sort_posts_new, PostListingController.Sort.NEW);
		addSort(activity, sortPosts, R.string.sort_posts_hot, PostListingController.Sort.HOT);
		addSort(activity, sortPosts, R.string.sort_posts_top, PostListingController.Sort.TOP);
		addSort(activity, sortPosts, R.string.sort_posts_comments, PostListingController.Sort.COMMENTS);
	}

	private static void addSort(final Activity activity, final Menu menu, final int name, final PostListingController.Sort order) {

		menu.add(activity.getString(name)).setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
			public boolean onMenuItemClick(final MenuItem item) {
				((OptionsMenuPostsListener)activity).onSortSelected(order);
				return true;
			}
		});
	}

	private static void addAllCommentSorts(final Activity activity, final Menu menu, final boolean icon) {

		final SubMenu sortComments = menu.addSubMenu(R.string.options_sort_comments);

		if(icon) {
			sortComments.getItem().setIcon(R.drawable.ic_action_sort);
			sortComments.getItem().setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
		}

		addSort(activity, sortComments, R.string.sort_comments_best, PostCommentListingURL.Sort.BEST);
		addSort(activity, sortComments, R.string.sort_comments_hot, PostCommentListingURL.Sort.HOT);
		addSort(activity, sortComments, R.string.sort_comments_new, PostCommentListingURL.Sort.NEW);
		addSort(activity, sortComments, R.string.sort_comments_old, PostCommentListingURL.Sort.OLD);
		addSort(activity, sortComments, R.string.sort_comments_controversial, PostCommentListingURL.Sort.CONTROVERSIAL);
		addSort(activity, sortComments, R.string.sort_comments_top, PostCommentListingURL.Sort.TOP);
	}

	private static void addSort(final Activity activity, final Menu menu, final int name, final PostCommentListingURL.Sort order) {

		menu.add(activity.getString(name)).setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
			public boolean onMenuItemClick(final MenuItem item) {
				((OptionsMenuCommentsListener)activity).onSortSelected(order);
				return true;
			}
		});
	}

	private static interface OptionsMenuListener {}

	public static interface OptionsMenuSubredditsListener extends OptionsMenuListener {
		public void onRefreshSubreddits();
	}

	public static interface OptionsMenuPostsListener extends OptionsMenuListener {
		public void onRefreshPosts();
		public void onPastPosts();
		public void onSubmitPost();
		public void onSortSelected(PostListingController.Sort order);
		public void onSearchPosts();
		public void onSubscribe();
		public void onUnsubscribe();
		public void onSidebar();
	}

	public static interface OptionsMenuCommentsListener extends OptionsMenuListener {
		public void onRefreshComments();
		public void onPastComments();
		public void onSortSelected(PostCommentListingURL.Sort order);
	}

	public static void fixActionBar(final Activity activity, final String title) {
		final TypedArray attr = activity.obtainStyledAttributes(new int[] {R.attr.rrActionBarCol});
		final int actionbarCol = attr.getColor(0, 0);
		activity.getSupportActionBar().setBackgroundDrawable(new ColorDrawable(actionbarCol));

		final BetterSSB sb = new BetterSSB();
		sb.append(title, BetterSSB.FOREGROUND_COLOR, Color.WHITE, 0, 1f);
		activity.getSupportActionBar().setTitle(sb.get());
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/PostListingActivity.java
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


import android.content.DialogInterface;
import android.content.Intent;
import android.graphics.drawable.ColorDrawable;
import android.os.Bundle;
import android.support.v4.app.FragmentTransaction;
import android.view.WindowManager;
import com.actionbarsherlock.view.Menu;
import com.actionbarsherlock.view.MenuItem;
import org.holoeverywhere.app.Activity;
import org.holoeverywhere.app.AlertDialog;
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.holoeverywhere.widget.EditText;
import org.holoeverywhere.widget.LinearLayout;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.account.RedditAccount;
import org.quantumbadger.redreader.account.RedditAccountChangeListener;
import org.quantumbadger.redreader.account.RedditAccountManager;
import org.quantumbadger.redreader.common.General;
import org.quantumbadger.redreader.common.LinkHandler;
import org.quantumbadger.redreader.common.PrefsUtility;
import org.quantumbadger.redreader.fragments.PostListingFragment;
import org.quantumbadger.redreader.fragments.SessionListDialog;
import org.quantumbadger.redreader.listingcontrollers.PostListingController;
import org.quantumbadger.redreader.reddit.api.RedditSubredditSubscriptionManager;
import org.quantumbadger.redreader.reddit.prepared.RedditPreparedPost;
import org.quantumbadger.redreader.reddit.url.PostCommentListingURL;
import org.quantumbadger.redreader.reddit.url.PostListingURL;
import org.quantumbadger.redreader.reddit.url.RedditURLParser;
import org.quantumbadger.redreader.reddit.url.SearchPostListURL;
import org.quantumbadger.redreader.views.RedditPostView;

import java.util.UUID;

public class PostListingActivity extends RefreshableActivity
		implements RedditAccountChangeListener,
		RedditPostView.PostSelectionListener,
		SharedPreferences.OnSharedPreferenceChangeListener,
		OptionsMenuUtility.OptionsMenuPostsListener,
		SessionChangeListener,
		RedditSubredditSubscriptionManager.SubredditSubscriptionStateChangeListener {

	private PostListingFragment fragment;
	private PostListingController controller;

	private SharedPreferences sharedPreferences;

	public void onCreate(final Bundle savedInstanceState) {

		PrefsUtility.applyTheme(this);

		// TODO load from savedInstanceState

		getSupportActionBar().setHomeButtonEnabled(true);
		getSupportActionBar().setDisplayHomeAsUpEnabled(true);

        getWindow().setBackgroundDrawable(new ColorDrawable(getSupportActionBarContext().obtainStyledAttributes(new int[] {R.attr.rrListBackgroundCol}).getColor(0,0)));

		sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);
		sharedPreferences.registerOnSharedPreferenceChangeListener(this);

		RedditAccountManager.getInstance(this).addUpdateListener(this);

		if(getIntent() != null) {

			final Intent intent = getIntent();

			final RedditURLParser.RedditURL url = RedditURLParser.parseProbablePostListing(intent.getData());

			if(!(url instanceof PostListingURL)) {
				throw new RuntimeException(String.format("'%s' is not a post listing URL!", url.generateJsonUri()));
			}

			controller = new PostListingController((PostListingURL)url);

			OptionsMenuUtility.fixActionBar(this, url.humanReadableName(this, false));

			super.onCreate(savedInstanceState);

			setContentView(R.layout.main_single);
			requestRefresh(RefreshableFragment.POSTS, false);

		} else {
			throw new RuntimeException("Nothing to show! (should load from bundle)"); // TODO
		}

		addSubscriptionListener();
	}

	@Override
	protected void onSaveInstanceState(final Bundle outState) {
		super.onSaveInstanceState(outState);
		// TODO save instance state
	}

	@Override
	public boolean onCreateOptionsMenu(final Menu menu) {

		final RedditAccount user = RedditAccountManager.getInstance(this).getDefaultAccount();
		final RedditSubredditSubscriptionManager.SubredditSubscriptionState subredditSubscriptionState;
		final RedditSubredditSubscriptionManager subredditSubscriptionManager
				= RedditSubredditSubscriptionManager.getSingleton(this, user);

		if(!user.isAnonymous()
				&& controller.isSubreddit()
				&& subredditSubscriptionManager.areSubscriptionsReady()
				&& fragment != null
				&& fragment.getSubreddit() != null) {

			subredditSubscriptionState = subredditSubscriptionManager.getSubscriptionState(controller.subredditCanonicalName());

		} else {
			subredditSubscriptionState = null;
		}

		final String subredditDescription = fragment != null && fragment.getSubreddit() != null
				? fragment.getSubreddit().description_html : null;

		OptionsMenuUtility.prepare(
				this,
				menu,
				false,
				true,
				false,
				controller.isSearchResults(),
				controller.isSortable(),
				true,
				subredditSubscriptionState,
				subredditDescription != null && subredditDescription.length() > 0,
				false);

		return true;
	}

	private void addSubscriptionListener() {
		RedditSubredditSubscriptionManager
				.getSingleton(this, RedditAccountManager.getInstance(this).getDefaultAccount())
				.addListener(this);
	}

	public void onRedditAccountChanged() {
		addSubscriptionListener();
		postInvalidateOptionsMenu();
		requestRefresh(RefreshableFragment.ALL, false);
	}

	@Override
	protected void doRefresh(final RefreshableFragment which, final boolean force) {
		if(fragment != null) fragment.cancel();
		fragment = controller.get(force);
		final FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();
		transaction.replace(R.id.main_single_frame, fragment, "post_listing_fragment");
		transaction.commit();
	}

	public void onPostSelected(final RedditPreparedPost post) {
		LinkHandler.onLinkClicked(this, post.url, false, post.src);
	}

	public void onPostCommentsSelected(final RedditPreparedPost post) {
		LinkHandler.onLinkClicked(this, PostCommentListingURL.forPostId(post.idAlone).toString(), false);
	}

	public void onRefreshPosts() {
		controller.setSession(null);
		requestRefresh(RefreshableFragment.POSTS, true);
	}

	public void onPastPosts() {
		final SessionListDialog sessionListDialog = SessionListDialog.newInstance(controller.getUri(), controller.getSession(), SessionChangeType.POSTS);
		sessionListDialog.show(this);
	}

	public void onSubmitPost() {
		final Intent intent = new Intent(this, PostSubmitActivity.class);
		if(controller.isSubreddit()) {
			intent.putExtra("subreddit", controller.subredditCanonicalName());
		}
		startActivity(intent);
	}

	public void onSortSelected(final PostListingController.Sort order) {
		controller.setSort(order);
		requestRefresh(RefreshableFragment.POSTS, false);
	}

	@Override
	public void onSearchPosts() {
		onSearchPosts(controller, this);
	}

	public static void onSearchPosts(final PostListingController controller, final Activity activity) {

		final AlertDialog.Builder alertBuilder = new AlertDialog.Builder(activity);
		final LinearLayout layout = (LinearLayout) activity.getLayoutInflater().inflate(R.layout.dialog_editbox);
		final EditText editText = (EditText)layout.findViewById(R.id.dialog_editbox_edittext);

		editText.requestFocus();

		alertBuilder.setView(layout);
		alertBuilder.setTitle(R.string.action_search);

		alertBuilder.setPositiveButton(R.string.action_search, new DialogInterface.OnClickListener() {
			public void onClick(DialogInterface dialog, int which) {

				final String query = editText.getText().toString().toLowerCase().trim();

				final SearchPostListURL url;

				if(controller != null && (controller.isSubreddit() || controller.isSubredditSearchResults())) {
					url = SearchPostListURL.build(controller.subredditCanonicalName(), query);
				} else {
					url = SearchPostListURL.build(null, query);
				}

				final Intent intent = new Intent(activity, PostListingActivity.class);
				intent.setData(url.generateJsonUri());
				activity.startActivity(intent);
			}
		});

		alertBuilder.setNegativeButton(R.string.dialog_cancel, null);

		final AlertDialog alertDialog = alertBuilder.create();
		alertDialog.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE);
		alertDialog.show();
	}

	@Override
	public void onSubscribe() {
		fragment.onSubscribe();
	}

	@Override
	public void onUnsubscribe() {
		fragment.onUnsubscribe();
	}

	@Override
	public void onSidebar() {
		final Intent intent = new Intent(this, HtmlViewActivity.class);
		intent.putExtra("html", fragment.getSubreddit().getSidebarHtml(PrefsUtility.isNightMode(this)));
		intent.putExtra("title", String.format("%s: %s",
				getString(R.string.sidebar_activity_title),
				fragment.getSubreddit().url));
		startActivityForResult(intent, 1);
	}

	public void onSharedPreferenceChanged(final SharedPreferences prefs, final String key) {

		if(PrefsUtility.isRestartRequired(this, key)) {
			requestRefresh(RefreshableFragment.RESTART, false);
		}

		if(PrefsUtility.isRefreshRequired(this, key)) {
			requestRefresh(RefreshableFragment.ALL, false);
		}
	}

	@Override
	protected void onDestroy() {
		super.onDestroy();
		sharedPreferences.unregisterOnSharedPreferenceChangeListener(this);
	}

	@Override
	public boolean onOptionsItemSelected(final MenuItem item) {
		switch(item.getItemId()) {
			case android.R.id.home:
				finish();
                return true;
			default:
				return super.onOptionsItemSelected(item);
		}
	}

	public void onSessionSelected(UUID session, SessionChangeType type) {
		controller.setSession(session);
		requestRefresh(RefreshableFragment.POSTS, false);
	}

	public void onSessionRefreshSelected(SessionChangeType type) {
		onRefreshPosts();
	}

	public void onSessionChanged(UUID session, SessionChangeType type, long timestamp) {
		controller.setSession(session);
	}

	@Override
	public void onBackPressed() {
		if(General.onBackPressed()) super.onBackPressed();
	}

	@Override
	public void onSubredditSubscriptionListUpdated(RedditSubredditSubscriptionManager subredditSubscriptionManager) {
		postInvalidateOptionsMenu();
	}

	@Override
	public void onSubredditSubscriptionAttempted(RedditSubredditSubscriptionManager subredditSubscriptionManager) {
		postInvalidateOptionsMenu();
	}

	@Override
	public void onSubredditUnsubscriptionAttempted(RedditSubredditSubscriptionManager subredditSubscriptionManager) {
		postInvalidateOptionsMenu();
	}

	private void postInvalidateOptionsMenu() {
		runOnUiThread(new Runnable() {
			@Override
			public void run() {
				invalidateOptionsMenu();
			}
		});
	}
}


File: src/main/java/org/quantumbadger/redreader/activities/RefreshableActivity.java
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
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.common.PrefsUtility;

import java.util.EnumSet;

public abstract class RefreshableActivity extends BaseActivity {

	private boolean paused = false;
	private final EnumSet<RefreshableFragment> refreshOnResume = EnumSet.noneOf(RefreshableFragment.class);

	private final SharedPreferences.OnSharedPreferenceChangeListener changeListener
			= new SharedPreferences.OnSharedPreferenceChangeListener() {
		public void onSharedPreferenceChanged(SharedPreferences prefs, String key) {
			if(key.equals(getString(R.string.pref_network_https_key))) {
				PrefsUtility.network_https(RefreshableActivity.this, prefs);
			}
		}
	};

	public enum RefreshableFragment {
		MAIN, MAIN_RELAYOUT, POSTS, COMMENTS, RESTART, ALL
	}

	@Override
	protected void onPause() {
		super.onPause();
		paused = true;
		PreferenceManager.getDefaultSharedPreferences(this).unregisterOnSharedPreferenceChangeListener(changeListener);
	}

	@Override
	protected void onResume() {

		super.onResume();

		final SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(this);
		PrefsUtility.network_https(this, prefs);
		prefs.registerOnSharedPreferenceChangeListener(changeListener);

		paused = false;

		for(final RefreshableFragment f : refreshOnResume) {
			doRefreshNow(f, false);
		}

		refreshOnResume.clear();
	}

	protected void doRefreshNow(RefreshableFragment which, boolean force) {

		if(which == RefreshableFragment.RESTART) {

			// http://stackoverflow.com/a/3419987/1526861
			final Intent intent = getIntent();
			overridePendingTransition(0, 0);
			intent.addFlags(Intent.FLAG_ACTIVITY_NO_ANIMATION);
			finish();
			overridePendingTransition(0, 0);
			startActivity(intent);

		} else {
			doRefresh(which, force);
		}
	}

	protected abstract void doRefresh(RefreshableFragment which, boolean force);

	public final void requestRefresh(final RefreshableFragment which, final boolean force) {
		runOnUiThread(new Runnable() {
			public void run() {
				if(!paused) {
					doRefreshNow(which, force);
				} else {
					refreshOnResume.add(which); // TODO this doesn't remember "force" (but it doesn't really matter...)
				}
			}}
		);
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

import android.content.Context;
import android.content.res.Resources;
import android.util.DisplayMetrics;
import org.holoeverywhere.app.Activity;
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.quantumbadger.redreader.R;
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
				|| context.getString(R.string.pref_appearance_langforce_key).equals(key);
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

	// pref_behaviour_fling_post

	public static enum PostFlingAction {
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

import android.content.Context;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import org.holoeverywhere.LayoutInflater;
import org.holoeverywhere.app.Fragment;
import org.holoeverywhere.widget.LinearLayout;
import org.holoeverywhere.widget.ListView;
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

	public static enum MainMenuAction {
		FRONTPAGE, PROFILE, INBOX, SUBMITTED, UPVOTED, DOWNVOTED, SAVED, MODMAIL, HIDDEN, CUSTOM, ALL
	}

	public static enum MainMenuUserItems {
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
				notifications.addView(new ErrorView(getSupportActivity(), error));
			}
		});
	}

	@Override
	public void onSaveInstanceState(final Bundle outState) {
		// TODO save menu position?
	}

	public void onSelected(final MainMenuAction type, final String name) {
		((MainMenuSelectionListener)getSupportActivity()).onSelected(type, name);
	}

	public void onSelected(final PostListingURL postListingURL) {
		((MainMenuSelectionListener)getSupportActivity()).onSelected(postListingURL);
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


File: src/main/java/org/quantumbadger/redreader/settings/SettingsActivity.java
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

package org.quantumbadger.redreader.settings;

import android.content.pm.ActivityInfo;
import android.os.Bundle;
import com.actionbarsherlock.view.MenuItem;
import org.holoeverywhere.preference.PreferenceActivity;
import org.holoeverywhere.preference.PreferenceManager;
import org.holoeverywhere.preference.SharedPreferences;
import org.quantumbadger.redreader.R;
import org.quantumbadger.redreader.common.PrefsUtility;

import java.util.List;

public final class SettingsActivity extends PreferenceActivity {
	private SharedPreferences sharedPreferences;

	@Override
	protected void onCreate(final Bundle savedInstanceState) {
		PrefsUtility.applyTheme(this);
		super.onCreate(savedInstanceState);
		sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);
		setOrientationFromPrefs();

		getSupportActionBar().setHomeButtonEnabled(true);
		getSupportActionBar().setDisplayHomeAsUpEnabled(true);
	}

	@Override
	protected void onResume() {
		super.onResume();
		setOrientationFromPrefs();
	}

	@Override
	public void onBuildHeaders(final List<Header> target) {

		loadHeadersFromResource(R.xml.prefheaders, target);
	}

	@Override
	public boolean onOptionsItemSelected(final MenuItem item) {
		switch(item.getItemId()) {
			case android.R.id.home:
				finish();
				return true;
			default:
				return false;
		}
	}

	private void setOrientationFromPrefs() {
		PrefsUtility.ScreenOrientation orientation = PrefsUtility.pref_behaviour_screen_orientation(this, sharedPreferences);
		if (orientation == PrefsUtility.ScreenOrientation.AUTO)
			setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
		else if (orientation == PrefsUtility.ScreenOrientation.PORTRAIT)
			setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
		else if (orientation == PrefsUtility.ScreenOrientation.LANDSCAPE)
			setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
	}
}